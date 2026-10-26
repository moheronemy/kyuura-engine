"""v0.86（docs/entry-energy-evolution-reactions-v0.86.md）: 登場・エネルギー・進化への反応 13 枚（14 ワザ・12 特殊能力）と、その共通の進行（``kyuura_engine/reactions.py``）。

根拠は kyuura データの採用（kyuura ``7d3f4ca`` の data/cards.json の日本語の印刷の文面）と、既存の規定の記録（GR-2000-P325-SAME-TIMING・GR-2000-P310-EVOLUTION・
GR-2000-P310-ATTACH-ENERGY・GR-2000-P320-RECOVERY・GR-2000-P321-DAMAGE-ORDER・CR-COUNTERATTACK-IS-POWER-DAMAGE・CR-ENERGY-TRANS-NOT-ATTACHMENT など。docs 各章）。公式ガイドブックの
新しい読み直し・カードの画像・pcg-search.com との照合はしていない。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import unittest

from kyuura_engine import (
    AttachEnergy,
    EndTurn,
    EvolvePokemon,
    PlayBasicToBench,
    PlayTrainer,
    ResolveDecision,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine import reactions as R
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.deck import deck_problems
from kyuura_engine.engine import check_invariants
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import (
    HIDDEN_COUNT_KINDS,
    OPTION_MEANINGS,
    PUBLIC_EVENTS,
    observe,
)
from kyuura_engine.persistent import powers_stopped
from kyuura_engine.serialize import state_to_dict
from kyuura_engine.state import BenchProtection, Phase, PowersStopped
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.release_catalog import cards_before
from tests.test_neo_trainer_components_v0_80 import audited, mon, new_events, rejects
from tests.test_shining_gentle_v0_83 import answer, board

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "entry-energy-evolution-reactions-v0.86.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, F, G, L, P, FT = H.WATER, H.FIRE, H.GRASS, H.LIGHTNING, H.PSYCHIC, H.FIGHTING
RAINBOW, FULL_HEAL_E = H.RAINBOW_ENERGY, H.FULL_HEAL_ENERGY
HC6 = "UNRESOLVED_DISCARD_DECK_SHORT"
RB1 = "UNRESOLVED_RAINBOW_ENERGY_TYPE"
RA1, RA2 = R.REACTION_AFTER_KNOCKOUT_CODE, R.REACTION_CONDITION_CHANGED_CODE
CV1, OT1, SO1 = E.CONDUCTIVITY_SOURCES_CODE, E.HOWL_OUTSIDE_TURN_CODE, E.SOLAR_POWER_NOTHING_CODE
BT1, PL1 = "UNRESOLVED_BOLT_DURING_OWN_ATTACK", "UNRESOLVED_PROTECTIVE_FLAME_SCOPE"
NEW_CODES = (RA1, RA2, CV1, OT1, BT1, PL1, SO1)


def uid(state, card_id, player=0, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def kinds(before, after):
    return [e["kind"] for e in new_events(before, after)]


def attach(state, card_id, target=None, player=0):
    target = state.players[player].active if target is None else target
    return apply_kernel(state, AttachEnergy(player, uid(state, card_id, player), target.card))


def evolve(state, card_id, target=None, player=0):
    target = state.players[player].active if target is None else target
    return apply_kernel(state, EvolvePokemon(player, uid(state, card_id, player), target.pokemon_id))


def logged(test, state):
    audited(test, state)
    test.assertEqual(check_invariants(state), [])


def copies_answer_alike(test, state, choices):
    """待っている決定のある状態を clone・deepcopy・pickle しても、同じ答えで同じ結果になる（続きを明示的なデータで持つ。docs 2.1 節）。"""
    expected = answer(state, choices)
    for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
        test.assertEqual(state_to_dict(answer(other, choices), format_version=22), state_to_dict(expected, format_version=22))
    return expected


def mareep_line(card, energy=(), *, player=0, **extra):
    """わるいモココ・わるいデンリュウ（盤面を直接作る。プレイヤー 0 は奇数の番、1 は偶数の番に進化した）。"""
    two = card == H.DARK_AMPHAROS
    turn = (5 if two else 3) + player
    return mon(card, energy, played_turn=player, evolved_from=[H.MAREEP_NEO1, H.DARK_FLAAFFY] if two else H.MAREEP_NEO1, evolved_turn=turn, **extra)


def ampharos(energy=(), **extra):
    return mareep_line(H.DARK_AMPHAROS, energy, player=1, **extra)


# ---------------------------------------------------------------- 1 章: 登録と数


class RegistrationTest(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(tuple(read_extract()['pool_v0_86']), H.V0_86_CARDS)
        pool = load_card_pool()
        self.assertLessEqual(set(H.V0_86_CARDS), pool.playable_ids)

    def test_without_v0_86_registrations_gives_back_1053(self):
        registry = E.DEFAULT_EFFECTS
        attacks = {k: v for k, v in registry._attacks.items() if k.card_id not in H.V0_86_CARDS}
        powers = {k: v for k, v in registry._powers.items() if k.card_id not in H.V0_86_CARDS}
        before = E.EffectRegistry(registry.id, attacks, registry._trainers, powers, registry._energies)
        pool = pool_from_extract(read_extract(), before)
        self.assertEqual(load_card_pool().playable_ids - pool.playable_ids, frozenset(H.V0_86_CARDS))  # ほかのカードの対応は変わらない
        self.assertTrue(all(card not in pool.playable_ids for card in H.V0_86_CARDS))
        # 特殊能力を持つカードは、ワザだけの登録では対応にならない
        attacks_only = E.EffectRegistry(registry.id, registry._attacks, registry._trainers,
                                        {k: v for k, v in registry._powers.items() if k.card_id not in H.V0_86_CARDS}, registry._energies)
        partial = pool_from_extract(read_extract(), attacks_only)
        self.assertEqual(sorted(set(H.V0_86_CARDS) & set(partial.playable_ids)), [H.DARK_FLAAFFY])

    def test_every_attack_and_power_is_registered_and_shared(self):
        pool = load_card_pool()
        for card_id in H.V0_86_POKEMON:
            definition = pool.get(card_id)
            self.assertTrue(definition.supported, (card_id, definition.unsupported_reasons))
            for index in range(len(definition.attacks)):
                self.assertIn(E.AttackKey(card_id, index), E.DEFAULT_EFFECTS._attacks)
            for index in range(len(definition.powers)):
                self.assertIn(E.PowerKey(card_id, index), E.DEFAULT_EFFECTS._powers)
        self.assertEqual((len(E.V0_86_ATTACKS), len(E.V0_86_POWERS)), (14, 12))
        registry = E.DEFAULT_EFFECTS
        self.assertIs(registry._attacks[E.AttackKey(H.EEVEE_PF2, 0)], registry._attacks[E.AttackKey(H.EEVEE_NEO2, 0)])
        self.assertIs(registry._powers[E.PowerKey(H.EEVEE_PF2, 0)], registry._powers[E.PowerKey(H.EEVEE_NEO2, 0)])
        self.assertIsNot(registry._powers[E.PowerKey(H.EEVEE_PRN, 0)], registry._powers[E.PowerKey(H.EEVEE_NEO2, 0)])

    def test_eevee_copies_are_counted_by_name(self):
        # 同じ名前のイーブイは、別の特殊能力・別の版でも合わせて 4 枚まで（GR-2000-P308-SAME-NAME）
        deck = [H.EEVEE_NEO2] * 2 + [H.EEVEE_PF2] * 2 + [H.EEVEE_PRN] + [W] * 55
        self.assertTrue(any(p.startswith("TOO_MANY_COPIES") for p in deck_problems(deck, load_card_pool())))
        ok = [H.EEVEE_NEO2] * 2 + [H.EEVEE_PF2] + [H.EEVEE_PRN] + [W] * 56
        self.assertEqual(deck_problems(ok, load_card_pool()), [])

    def test_evolution_lines_use_exact_names(self):
        pool = load_card_pool()
        self.assertEqual(pool.get(H.DARK_CROBAT).evolves_from, "わるいゴルバット")
        self.assertEqual(pool.get(H.DARK_AMPHAROS).evolves_from, "わるいモココ")
        self.assertEqual(pool.get(H.DARK_FLAAFFY).evolves_from, "メリープ")
        self.assertEqual(pool.get(H.BLISSEY_NEO3).evolves_from, "ラッキー")
        self.assertEqual(pool.get(H.DRAGONITE_PR1).evolves_from, "ハクリュー")
        self.assertEqual(pool.get(H.VENUSAUR_PR1).evolves_from, "フシギソウ")

    def test_quiz_names_and_identity_trials(self):
        """カツラのクイズの名前の候補（新しい名前は 7 つ。v0.86 までの写しで 411）・マチスの秘策の試す回数が上限の中（docs 1 章・10 章）。今の未対応の数・名前の候補の数・試すカードの数は tests/test_catalog_contract.py。"""
        from kyuura_engine import engine
        pool = load_card_pool()
        names = {pool.get(c).name_ja for c in pool.playable_ids if pool.get(c).category == "pokemon"}
        new_names = {"わるいクロバット", "わるいデンリュウ", "わるいモココ", "エンテイ", "スイクン", "ハピナス", "ライコウ"}
        self.assertEqual(len({pool.get(c).name_ja for c in cards_before(read_extract(), "0.87") if pool.get(c).category == "pokemon"}), 411)  # この版までの写しのポケモンの名前（今の総数は tests/test_catalog_contract.py）
        self.assertTrue(new_names <= names)
        candidates = engine._identity_candidates(pool)
        basics = [c for c in candidates if pool.get(c).category == "pokemon" and pool.get(c).stage == "basic"]
        self.assertLessEqual(1 + len(basics) + 1, engine._IDENTITY_TRIAL_LIMIT)  # 1 枚を指定するコマンドの試す回数（今の総数は tests/test_catalog_contract.py）

    def test_new_public_events_and_decisions(self):
        for kind in ("conductivity", "lightning_burst_skipped", "reaction_power_declined", "bolt_check", "bolt_skipped", "pokemon_coin_results",
                     "power_turn_end"):
            self.assertIn(kind, PUBLIC_EVENTS)
        for kind in ("reaction_order", "reaction_power"):
            self.assertIn(kind, OPTION_MEANINGS)
        self.assertIn("search_deck", HIDDEN_COUNT_KINDS)


class TextCheckTest(unittest.TestCase):
    """新しい型・今回広げる型は、日本語の全文と引数を結びつけて検査する（意味が違う枚数・時点・対象・不足時・範囲の文面を拒否する。docs 7 章）。"""

    def problems(self, effect, name, text, card_id):
        definition = load_card_pool().get(card_id)
        attack = dataclass_replace(definition.attacks[0], name_ja=name, text_ja=text)
        return effect.check(attack) if hasattr(effect, "check") else []

    def test_registered_texts_pass_and_variants_fail(self):
        pool = load_card_pool()
        for key, entry in E.V0_86_ATTACKS.items():
            attack = pool.get(key.card_id).attacks[key.attack_index]
            self.assertEqual(entry.effect.check(attack), [], key)
        flaaffy = pool.get(H.DARK_FLAAFFY).attacks[0]
        # 既存のこうしゅうは（相手は「トレーナーカード」を使えない）の型は、手札からという範囲のこの文面を拒否する
        self.assertNotEqual(E.DamageThenLockOpponentTrainersOnHeads().check(flaaffy), [])
        ampharos_attack = pool.get(H.DARK_AMPHAROS).attacks[0]
        self.assertNotEqual(E.DiscardTypeCardsThenDamageNoneIfLacking(E.EnergyType.FIRE, None).check(ampharos_attack), [])
        self.assertNotEqual(E.DiscardTypeCardsThenDamageNoneIfLacking(E.EnergyType.LIGHTNING, 2).check(ampharos_attack), [])
        entei_attack = pool.get(H.ENTEI_NEO3).attacks[0]
        self.assertNotEqual(E.DiscardTypeCardsThenDamageNoneIfLacking(E.EnergyType.FIRE, None).check(entei_attack), [])
        self.assertNotEqual(E.DiscardTypeCardsThenDamageNoneIfLacking(E.EnergyType.FIRE, 1).check(entei_attack), [])
        # v0.30 の炎 1 枚の型・v0.31 の「はがしてすてる」の型で、この文面を受け付けない
        self.assertNotEqual(E.DiscardEnergyThenDamage(E.EnergyType.FIRE).check(entei_attack), [])
        drain = pool.get(H.DARK_CROBAT).attacks[0]
        self.assertNotEqual(E.CoinPerOpponentPokemonDamageThenHealDealt(20).check(drain), [])

    def test_power_texts(self):
        pool = load_card_pool()
        for key, entry in E.V0_86_POWERS.items():
            power = pool.get(key.card_id).powers[key.power_index]
            self.assertEqual(entry.effect.check(power), [], key)
        bite = pool.get(H.DARK_CROBAT).powers[0]
        self.assertNotEqual(E.DamageOpponentPokemonOnEvolve(10).check(bite), [])
        conductivity = pool.get(H.DARK_AMPHAROS).powers[0]
        self.assertNotEqual(E.DamageOnOpponentHandEnergyAttach(20, "わるいデンリュウ", "かんでん").check(conductivity), [])
        burst = pool.get(H.RAIKOU_NEO3).powers[0]
        self.assertNotEqual(E.SwitchOpponentOnTypeEnergyAttach(E.EnergyType.FIRE).check(burst), [])
        # こっそりかみつく（v0.43）の型は、手札から進化させたときの 20 の文面を受け付けない
        self.assertNotEqual(E.DamageOpponentPokemonOnEntry(20).check(bite), [])


def dataclass_replace(value, **changes):
    import dataclasses

    return dataclasses.replace(value, **changes)


# ---------------------------------------------------------------- 2 章: 共通の進行（同じ時点の順番・続き）


class SameTimingTest(unittest.TestCase):
    """同じ時点に起こる反応は、その時に番を行っているプレイヤーが順番を決める（GR-2000-P325-SAME-TIMING。決定 ``reaction_order``）。"""

    def raikou_vs_ampharos(self):
        return board(mon(H.RAIKOU_NEO3), hand=(L,), opponent=ampharos(), opponent_bench=(H.RATTATA, H.RATTATA))

    def test_order_is_chosen_by_the_turn_player(self):
        state = self.raikou_vs_ampharos()
        waiting = attach(state, L)
        self.assertEqual((waiting.decision.kind, waiting.decision.player, waiting.decision.options), ("reaction_order", 0, (0, 1)))
        self.assertEqual(kinds(state, waiting), ["attach_energy"])
        logged(self, waiting)
        live = waiting.decision.context_value(R.REACTION)[2]
        self.assertEqual({r[0] for r in live}, {R.LIGHTNING_BURST, R.CONDUCTIVITY})
        burst_first = live.index(next(r for r in live if r[0] == R.LIGHTNING_BURST))
        switching = copies_answer_alike(self, waiting, (burst_first,))
        self.assertEqual((switching.decision.kind, switching.decision.player), ("select_pokemon", 1))
        done = answer(switching, switching.decision.options[:1])
        self.assertEqual(kinds(waiting, done), ["pokemon_power", "switch", "conductivity"])
        self.assertEqual(done.players[0].active.damage, 10)
        self.assertEqual(done.phase, Phase.MAIN)
        self.assertEqual(done.energy_attachments_this_turn, 1)
        logged(self, done)
        conductivity_first = answer(waiting, (1 - burst_first,))
        self.assertEqual(kinds(waiting, conductivity_first), ["conductivity", "pokemon_power"])
        self.assertEqual(conductivity_first.decision.kind, "select_pokemon")

    def test_illegal_answers_change_nothing(self):
        state = self.raikou_vs_ampharos()
        waiting = attach(state, L)
        for player, choices in ((1, (0,)), (0, (2,)), (0, (0, 1)), (0, ())):
            with self.assertRaises((IllegalActionError, UnsupportedError)):
                apply_kernel(waiting, ResolveDecision(player, waiting.decision.id, choices))
        live = waiting.decision.context_value(R.REACTION)[2]
        switching = answer(waiting, (next(i for i, r in enumerate(live) if r[0] == R.LIGHTNING_BURST),))
        before = state_to_dict(switching, format_version=22)
        with self.assertRaises(IllegalActionError):
            apply_kernel(switching, ResolveDecision(0, switching.decision.id, switching.decision.options[:1]))  # 選ぶのは相手
        self.assertEqual(state_to_dict(switching, format_version=22), before)

    def test_one_reaction_needs_no_order(self):
        state = board(mon(H.RAIKOU_NEO3), hand=(L,), opponent_bench=(H.RATTATA,))
        waiting = attach(state, L)
        self.assertEqual(waiting.decision.kind, "select_pokemon")

    def test_knockout_before_the_remaining_reactions_is_ra1(self):
        """［かんでん］で先に HP 以上になったあと、残りの［いなびかり］の処理（RA1。順番を変えれば止まらない）。"""
        state = board(mon(H.RAIKOU_NEO3, damage=50), hand=(L,), opponent=ampharos(), opponent_bench=(H.RATTATA,))
        hp = E.max_hp(state, state.players[0].active)
        state = board(mon(H.RAIKOU_NEO3, damage=hp - 10), hand=(L,), opponent=ampharos(), opponent_bench=(H.RATTATA,))
        waiting = attach(state, L)
        live = waiting.decision.context_value(R.REACTION)[2]
        conductivity_first = next(i for i, r in enumerate(live) if r[0] == R.CONDUCTIVITY)
        rejects(self, waiting, ResolveDecision(0, waiting.decision.id, (conductivity_first,)), RA1)
        burst_first = answer(waiting, (1 - conductivity_first,))
        done = answer(burst_first, burst_first.decision.options[:1])
        self.assertEqual(new_events(waiting, done, "knock_out")[0]["pokemon"], state.players[0].active.card)
        logged(self, done)

    def test_condition_changed_by_the_first_reaction_is_ra2(self):
        """なんでもなおし配合エネルギーの回復で、あとの［エナジーしんか］がはたらくか（ねむり）が変わる（RA2）。"""
        state = board(mon(H.EEVEE_NEO2, sleep=True), hand=(FULL_HEAL_E,), deck=[H.VAPOREON, W, W])
        waiting = attach(state, FULL_HEAL_E)
        self.assertEqual(waiting.decision.kind, "reaction_order")
        live = waiting.decision.context_value(R.REACTION)[2]
        energy_first = next(i for i, r in enumerate(live) if r[0] == R.ENERGY)
        rejects(self, waiting, ResolveDecision(0, waiting.decision.id, (energy_first,)), RA2)
        self.assertEqual(waiting.decision.context_value("unresolved_choices"), (energy_first,))
        evolution_first = answer(waiting, (1 - energy_first,))
        # ねむりなので［エナジーしんか］ははたらかない（どちらの時点で決めても同じ）→ なんでもなおし配合エネルギーの回復。使う機会は出ない
        self.assertIsNone(evolution_first.decision)
        self.assertEqual(len(new_events(waiting, evolution_first, "special_conditions_removed")), 1)
        self.assertFalse(evolution_first.players[0].active.conditions.asleep)
        logged(self, evolution_first)


# ---------------------------------------------------------------- 3 章: イーブイ


class EnergyEvolutionTest(unittest.TestCase):
    """［エナジーしんか］: 手札からこのカードにエネルギーカードをつけたときに使える。コインの「おもて」で、山札のつけたカードと同じ色の進化カードを重ね、山札を切る。"""

    def test_use_heads_evolves_into_matching_color(self):
        state = board(mon(H.EEVEE_NEO2), hand=(W,), deck=[H.FLAREON, H.VAPOREON, W, W])
        waiting = attach(state, W)
        self.assertEqual((waiting.decision.kind, waiting.decision.player, waiting.decision.options), ("reaction_power", 0, (state.players[0].active.pokemon_id,)))
        searching = copies_answer_alike(self, with_coin_results(waiting, HD), waiting.decision.options)
        self.assertEqual(searching.decision.kind, "search_deck")
        self.assertEqual([searching.card_def(u).name_ja for u in searching.decision.options], ["シャワーズ"])
        done = answer(searching, searching.decision.options)
        self.assertEqual(done.card_def(done.players[0].active.card).name_ja, "シャワーズ")
        self.assertEqual(kinds(searching, done), ["evolve", "shuffle"])
        self.assertEqual(done.energy_attachments_this_turn, 1)
        logged(self, done)

    def test_tails_and_decline(self):
        state = board(mon(H.EEVEE_PF2), hand=(W,), deck=[H.VAPOREON, W, W])
        waiting = attach(state, W)
        tails = answer(with_coin_results(waiting, TL), waiting.decision.options)
        self.assertIsNone(tails.decision)
        self.assertEqual(kinds(waiting, tails), ["pokemon_power", "coin_flip"])
        declined = answer(waiting, ())
        self.assertEqual(kinds(waiting, declined), ["reaction_power_declined"])
        self.assertEqual(new_events(waiting, declined, "coin_flip"), [])
        rejects(self, declined, UsePokemonPower(0, declined.players[0].active.pokemon_id, 0), "POWER_NOT_USABLE_NOW", error=IllegalActionError)

    def test_no_candidate_still_waits_and_hides_the_count(self):
        """山札に重ねられるカードがなくても、選ぶ決定を出して答えを待つ（候補 0 対 1 で相手に見える決定の有無・人が変わらない）。"""
        shapes = []
        for deck in ([W, W, W], [H.VAPOREON, W, W]):
            state = board(mon(H.EEVEE_NEO2), hand=(W,), deck=deck)
            waiting = attach(state, W)
            searching = answer(with_coin_results(waiting, HD), waiting.decision.options)
            self.assertEqual((searching.decision.kind, searching.decision.player), ("search_deck", 0))
            seen = observe(searching, 1)["decision"]
            shapes.append(seen)
            choice = searching.decision.options[:1]
            done = answer(searching, choice)
            self.assertIsNone(done.decision)
            self.assertIn("shuffle", kinds(searching, done))
        self.assertEqual(shapes[0], shapes[1])

    def test_not_from_deck_or_discard_or_move(self):
        state = board(mon(H.EEVEE_NEO2), bench=(mon(H.VENUSAUR, (G,), played_turn=1, evolved_from=[H.BULBASAUR, H.IVYSAUR], evolved_turn=5),),
                      deck=[H.VAPOREON, W])
        venusaur = state.players[0].bench[0]
        moved = apply_kernel(state, UsePokemonPower(0, venusaur.pokemon_id, 0, energy=venusaur.energy[0], source=venusaur.pokemon_id,
                                                   target=state.players[0].active.pokemon_id))
        self.assertIsNone(moved.decision)  # エナジートランス（場のつけかえ）は手札からつけたことではない
        self.assertEqual(kinds(state, moved), ["pokemon_power", "move_energy"])

    def test_asleep_holder_has_no_opportunity(self):
        state = board(mon(H.EEVEE_NEO2, sleep=True), hand=(W,), deck=[H.VAPOREON, W])
        done = attach(state, W)
        self.assertIsNone(done.decision)
        self.assertEqual(kinds(state, done), ["attach_energy"])

    def test_rainbow_color_is_rb1_only_when_used(self):
        state = board(mon(H.EEVEE_NEO2), hand=(RAINBOW,), deck=[H.VAPOREON, W])
        waiting = attach(state, RAINBOW)
        decision = waiting.decision
        if decision.kind == "reaction_order":
            live = decision.context_value(R.REACTION)[2]
            waiting = answer(waiting, (next(i for i, r in enumerate(live) if r[0] == R.ENERGY_EVOLUTION),))
        self.assertEqual(waiting.decision.kind, "reaction_power")
        self.assertEqual(waiting.decision.context_value("unresolved_code"), RB1)
        rejects(self, waiting, ResolveDecision(0, waiting.decision.id, waiting.decision.options), RB1)
        declined = answer(waiting, ())
        self.assertIsNone(declined.decision)


class ChainReactionTest(unittest.TestCase):
    """［れんさしんか］: 自分の場のほかのポケモンが実際に進化したとき、使うかを持ち主が決め、山札からこのカードの進化カードを重ねる。"""

    def board(self, **extra):
        return board(mon(H.RATTATA), bench=(mon(H.EEVEE_PRN, played_turn=1), mon(H.ZUBAT_NEO3, played_turn=1)), hand=(H.GOLBAT,),
                     deck=[H.VAPOREON, H.JOLTEON, W, W], **extra)

    def test_hand_evolution_triggers_and_any_eevee_evolution_can_be_chosen(self):
        state = self.board()
        zubat = state.players[0].bench[1]
        waiting = evolve(state, H.GOLBAT, zubat)
        self.assertEqual((waiting.decision.kind, waiting.decision.player), ("reaction_power", 0))
        searching = copies_answer_alike(self, waiting, waiting.decision.options)
        self.assertEqual(sorted(searching.card_def(u).name_ja for u in searching.decision.options), ["サンダース", "シャワーズ"])
        self.assertEqual(new_events(waiting, searching, "coin_flip"), [])  # コインはない
        done = answer(searching, searching.decision.options[:1])
        self.assertIn(done.card_def(done.players[0].bench[0].card).name_ja, ("サンダース", "シャワーズ"))
        logged(self, done)

    def test_two_eevees_each_get_one_opportunity_ordered_by_the_turn_player(self):
        state = board(mon(H.RATTATA), bench=(mon(H.EEVEE_PRN, played_turn=1), mon(H.EEVEE_PRN, played_turn=1), mon(H.ZUBAT_NEO3, played_turn=1)),
                      hand=(H.GOLBAT,), deck=[H.VAPOREON, H.JOLTEON, W, W])
        zubat = state.players[0].bench[2]
        waiting = evolve(state, H.GOLBAT, zubat)
        self.assertEqual(waiting.decision.kind, "reaction_order")
        first = answer(waiting, (0,))
        self.assertEqual(first.decision.kind, "reaction_power")
        declined = answer(first, ())
        self.assertEqual(declined.decision.kind, "reaction_power")
        self.assertNotEqual(declined.decision.options, first.decision.options)
        used = answer(declined, declined.decision.options)
        evolved = answer(used, used.decision.options[:1])
        # 重ねたイーブイの進化は、もう 1 匹のイーブイには事実だが、そのイーブイはすでに答えた（1 つの事実で二重に機会を出さない。新しい事実への機会は出る）
        self.assertIsNotNone(evolved.decision)
        self.assertEqual(evolved.decision.kind, "reaction_power")
        self.assertEqual(evolved.decision.options, first.decision.options)
        finished = answer(evolved, ())
        self.assertIsNone(finished.decision)
        logged(self, finished)

    def test_placement_and_opponent_evolution_are_not_evolution(self):
        state = board(mon(H.RATTATA), bench=(mon(H.EEVEE_PRN, played_turn=1),), hand=(H.ZUBAT_NEO3,), deck=[H.VAPOREON, W])
        placed = apply_kernel(state, PlayBasicToBench(0, uid(state, H.ZUBAT_NEO3)))
        self.assertIsNone(placed.decision)
        state = board(mon(H.RATTATA), opponent=mon(H.ZUBAT_NEO3, played_turn=1), opponent_bench=(mon(H.EEVEE_PRN, played_turn=1),),
                      opponent_hand=(H.GOLBAT,), current=1, turn=8, opponent_deck=[H.VAPOREON, W])
        evolved = apply_kernel(state, EvolvePokemon(1, uid(state, H.GOLBAT, 1), state.players[1].active.pokemon_id))
        # 相手の場（プレイヤー 1）のイーブイは、自分（プレイヤー 1）の場のほかのポケモンの進化に反応する
        self.assertEqual((evolved.decision.kind, evolved.decision.player), ("reaction_power", 1))
        mine = board(mon(H.ZUBAT_NEO3, played_turn=1), hand=(H.GOLBAT,), opponent_bench=(mon(H.EEVEE_PRN, played_turn=1),))
        self.assertIsNone(evolve(mine, H.GOLBAT).decision)  # 相手のポケモンの進化には反応しない

    def test_gas_and_stun_stop_the_opportunity(self):
        gas = self.board(opponent=mon(H.MUK, played_turn=2, evolved_from=H.FOSSIL_GRIMER, evolved_turn=4))
        self.assertIsNone(evolve(gas, H.GOLBAT, gas.players[0].bench[1]).decision)
        # スタンウェーブを受けたライコウ（バトル場）は、次の相手の番が終わるまで［いなびかり］がはたらかない（かならずはたらく反応も止まる）
        mine = board(mon(H.RAIKOU_NEO3), hand=(L,), opponent=mareep_line(H.DARK_FLAAFFY, (L, L, L), player=1), opponent_bench=(H.RATTATA,), current=1, turn=8)
        stunned = apply_kernel(mine, UseAttack(1, 1))
        self.assertEqual(stunned.current_player, 0)
        self.assertIsNotNone(powers_stopped(stunned, stunned.players[0].active))
        done = attach(stunned, L)
        self.assertIsNone(done.decision)
        self.assertEqual(kinds(stunned, done), ["attach_energy"])


# ---------------------------------------------------------------- 4 章: 場に出たときの特殊能力


class HowlTest(unittest.TestCase):
    """［おたけび］: 手札から場に出したとき 1 回だけ。山札の上 5 枚をトラッシュし、その中の「炎」エネルギーカードをすべて自分の場の「炎」ポケモンにつけ、自分の番を終える。"""

    def board(self, deck=None, **extra):
        return board(mon(H.RATTATA), bench=(mon(H.CHARMANDER, played_turn=1),), hand=(H.ENTEI_NEO3,),
                     deck=deck if deck is not None else [F, W, F, W, W, W, W], discard=(F,), **extra)

    def test_use_distributes_only_the_milled_fire_then_ends_the_turn(self):
        state = self.board()
        offered = apply_kernel(state, PlayBasicToBench(0, uid(state, H.ENTEI_NEO3)))
        self.assertEqual(offered.decision.kind, "entry_power")
        first = copies_answer_alike(self, offered, offered.decision.options)
        milled = new_events(offered, first, "deck_top_to_discard")
        self.assertEqual(len(milled[0]["cards"]), 5)
        fire = [u for u in milled[0]["cards"] if first.cards[u].card_id == F]
        self.assertEqual(len(fire), 2)
        self.assertEqual(first.decision.context_value("card"), fire[0])
        old_fire = state.players[0].discard[0]
        self.assertNotIn(old_fire, fire)  # 前からトラッシュにあった炎は使わない
        targets = first.decision.options
        self.assertEqual(len(targets), 2)  # エンテイ・ヒトカゲ（ラッタは炎でない）
        second = answer(first, targets[-1:])
        done = answer(second, second.decision.options[:1])
        tail = kinds(second, done)
        self.assertEqual(tail[:3], ["power_attach_from_discard", "power_turn_end", "turn_end"])
        self.assertEqual((done.turn_number, done.current_player), (state.turn_number + 1, 1))
        self.assertEqual(tail.count("turn_end"), 1)
        self.assertEqual(tail.count("pokemon_check"), 1)
        self.assertNotIn("attack", tail)
        logged(self, done)

    def test_decline_keeps_the_turn(self):
        state = self.board()
        offered = apply_kernel(state, PlayBasicToBench(0, uid(state, H.ENTEI_NEO3)))
        declined = answer(offered, ())
        self.assertEqual(kinds(offered, declined), ["entry_power_declined"])
        self.assertEqual((declined.phase, declined.current_player, declined.turn_number), (Phase.MAIN, 0, state.turn_number))

    def test_no_fire_still_ends_the_turn(self):
        state = self.board(deck=[W] * 7)
        offered = apply_kernel(state, PlayBasicToBench(0, uid(state, H.ENTEI_NEO3)))
        done = answer(offered, offered.decision.options)
        self.assertEqual(done.current_player, 1)
        self.assertIn("power_turn_end", kinds(offered, done))

    def test_short_deck_is_hc6_when_used_only(self):
        state = self.board(deck=[F, W, W, W])
        offered = apply_kernel(state, PlayBasicToBench(0, uid(state, H.ENTEI_NEO3)))
        self.assertEqual(offered.decision.context_value("unresolved_code"), HC6)
        rejects(self, offered, ResolveDecision(0, offered.decision.id, offered.decision.options), HC6)
        self.assertEqual(answer(offered, ()).phase, Phase.MAIN)

    def test_lt_surge_entei_howl_finishes_the_trainer_then_ends_the_turn(self):
        """マチス（自分の番に手札のたねポケモンをバトル場に出す）で出したエンテイの［おたけび］: 分けてつけ終え、トレーナーを使い終えてから、番を終える。"""
        state = board(mon(H.RATTATA), hand=(H.LT_SURGE_TRAINER, H.ENTEI_NEO3), deck=[F, W, W, W, W, W, W])
        surge = uid(state, H.LT_SURGE_TRAINER)
        step = apply_kernel(state, PlayTrainer(0, surge))
        while step.decision is not None and step.decision.kind != "entry_power":
            step = answer(step, step.decision.options[-1:])
        self.assertEqual((step.decision.kind, step.decision.player), ("entry_power", 0))
        self.assertIsNotNone(step.trainer_in_use)
        used = answer(step, step.decision.options)
        while used.decision is not None:
            used = answer(used, used.decision.options[:1])
        tail = kinds(step, used)
        self.assertLess(tail.index("discard_trainer"), tail.index("power_turn_end"))
        self.assertEqual(tail.count("turn_end"), 1)
        self.assertIn(surge, used.players[0].discard)
        self.assertEqual(used.current_player, 1)
        logged(self, used)

    def test_erikas_perfume_opponent_entei_is_ot1_when_used(self):
        """エリカの香水（相手の手札のたねポケモンを相手のベンチに出させる）で、自分の番に相手の場に出たエンテイの［おたけび］の「自分の番を終える」は決まらない（OT1）。
        使わないなら、トレーナーを使い終えて自分の番が続く。"""
        state = board(mon(H.RATTATA), hand=(H.ERIKAS_PERFUME,), opponent_hand=(H.ENTEI_NEO3,))
        perfume = uid(state, H.ERIKAS_PERFUME)
        step = apply_kernel(state, PlayTrainer(0, perfume))
        while step.decision is not None and step.decision.kind != "entry_power":
            step = answer(step, step.decision.options[:1])
        self.assertEqual((step.decision.kind, step.decision.player), ("entry_power", 1))
        self.assertEqual(step.decision.context_value("unresolved_code"), OT1)
        rejects(self, step, ResolveDecision(1, step.decision.id, step.decision.options), OT1)
        done = answer(step, ())
        self.assertIsNone(done.trainer_in_use)
        self.assertIn(perfume, done.players[0].discard)
        self.assertEqual((done.phase, done.current_player), (Phase.MAIN, 0))
        logged(self, done)


class EntryHealDamageTest(unittest.TestCase):
    def test_softboiled_four_then_coin_four(self):
        for damage, side, left in ((70, HD, 0), (70, TL, 30), (30, TL, 0), (100, HD, 20)):
            state = board(mon(H.CHANSEY, damage=damage, played_turn=1), hand=(H.BLISSEY_NEO3,))
            offered = evolve(state, H.BLISSEY_NEO3)
            done = answer(with_coin_results(offered, side), offered.decision.options)
            self.assertEqual(done.players[0].active.damage, left, (damage, side))
            removed = new_events(offered, done, "remove_damage_counters")
            self.assertEqual(removed[0]["count"] if "count" in removed[0] else removed[0].get("counters"), min(4, damage // 10))
            logged(self, done)

    def test_softboiled_only_from_hand_evolution(self):
        state = board(mon(H.CHANSEY, damage=40, played_turn=1), hand=(H.BLISSEY_NEO3,))
        offered = evolve(state, H.BLISSEY_NEO3)
        declined = answer(offered, ())
        self.assertEqual(declined.players[0].active.damage, 40)

    def test_healing_wind_two_from_each_own(self):
        state = board(mon(H.DRAGONAIR, damage=30, played_turn=1, evolved_from=H.DRATINI, evolved_turn=3),
                      bench=(mon(H.RATTATA, damage=10), mon(H.RATTATA)), hand=(H.DRAGONITE_PR1,), opponent=mon(H.RATTATA, damage=20))
        offered = evolve(state, H.DRAGONITE_PR1)
        done = answer(offered, offered.decision.options)
        self.assertEqual([p.damage for p in done.players[0].in_play()], [10, 0, 0])
        self.assertEqual(done.players[1].active.damage, 20)
        logged(self, done)

    def test_surprise_bite_twenty_power_damage_no_weakness(self):
        state = board(mon(H.DARK_GOLBAT, played_turn=1, evolved_from=H.ZUBAT_NEO3, evolved_turn=3), hand=(H.DARK_CROBAT,),
                      opponent=mon(H.HITMONCHAN), opponent_bench=(H.RATTATA,))
        offered = evolve(state, H.DARK_CROBAT)
        choosing = answer(offered, offered.decision.options)
        self.assertEqual(choosing.decision.kind, "select_pokemon")
        done = answer(choosing, (state.players[1].active.pokemon_id,))
        events = new_events(choosing, done, "power_damage")
        self.assertEqual(events[0]["amount"], 20)
        self.assertEqual(done.players[1].active.damage, 20)
        logged(self, done)

    def test_breeder_crobat_knockout_returns_to_the_trainer(self):
        state = board(mon(H.RATTATA), bench=(mon(H.ZUBAT_NEO3, played_turn=1),), hand=(H.POKEMON_BREEDER, H.DARK_CROBAT),
                      opponent=mon(H.RATTATA, damage=20), opponent_bench=(H.RATTATA,))
        breeder = uid(state, H.POKEMON_BREEDER)
        step = apply_kernel(state, PlayTrainer(0, breeder))
        step = answer(step, step.decision.options[:1])
        step = answer(step, step.decision.options[:1])
        self.assertEqual(step.decision.kind, "entry_power")
        step = answer(step, step.decision.options)
        step = answer(step, (step.players[1].active.pokemon_id,))
        self.assertEqual((step.decision.kind, step.decision.player), ("take_prize", 0))
        self.assertIsNotNone(step.trainer_in_use)
        while step.decision is not None:
            step = answer(step, step.decision.options[:1])
        self.assertIsNone(step.trainer_in_use)
        self.assertIn(breeder, step.players[0].discard)
        self.assertEqual((step.phase, step.current_player), (Phase.MAIN, 0))
        logged(self, step)


# ---------------------------------------------------------------- 5 章: エネルギーに反応する特殊能力


class LightningBurstTest(unittest.TestCase):
    def test_forced_opponent_chooses(self):
        state = board(mon(H.RAIKOU_NEO3), hand=(L,), opponent_bench=(H.RATTATA, H.PIDGEY))
        waiting = attach(state, L)
        self.assertEqual((waiting.decision.kind, waiting.decision.player), ("select_pokemon", 1))
        self.assertTrue(new_events(state, waiting, "pokemon_power")[0]["forced"])
        done = copies_answer_alike(self, waiting, waiting.decision.options[1:])
        self.assertEqual(done.players[1].active.pokemon_id, waiting.decision.options[1])
        logged(self, done)

    def test_not_for_other_colors_status_or_no_bench(self):
        self.assertIsNone(attach(board(mon(H.RAIKOU_NEO3), hand=(W,)), W).decision)
        self.assertIsNone(attach(board(mon(H.RAIKOU_NEO3, confusion=True), hand=(L,)), L).decision)
        skipped = attach(board(mon(H.RAIKOU_NEO3), hand=(L,), opponent_bench=()), L)
        self.assertEqual(kinds(board(mon(H.RAIKOU_NEO3), hand=(L,), opponent_bench=()), skipped), ["attach_energy", "lightning_burst_skipped"])

    def test_already_asleep_with_full_heal_energy_is_not_lost(self):
        """つけるときすでにねむりなら、なんでもなおし配合エネルギーで回復してもはたらかない（説明が時点を書く。RA2 にしない）。"""
        rainbowless = board(mon(H.RAIKOU_NEO3, sleep=True), hand=(FULL_HEAL_E,), opponent_bench=(H.RATTATA,))
        done = attach(rainbowless, FULL_HEAL_E)
        self.assertNotIn("pokemon_power", kinds(rainbowless, done))


class ConductivityTest(unittest.TestCase):
    def test_ten_power_damage_once(self):
        state = board(mon(H.HITMONCHAN), hand=(W,), opponent=ampharos())
        done = attach(state, W)
        self.assertEqual(done.players[0].active.damage, 10)  # 弱点（超）があっても 10
        self.assertEqual(new_events(state, done, "conductivity")[0]["amount"], 10)
        logged(self, done)

    def test_only_the_opponent_and_only_from_hand(self):
        state = board(mareep_line(H.DARK_AMPHAROS), hand=(L,))
        self.assertEqual(attach(state, L).players[0].active.damage, 0)
        moved = board(mon(H.RATTATA), bench=(mon(H.VENUSAUR, (G,), played_turn=1, evolved_from=[H.BULBASAUR, H.IVYSAUR], evolved_turn=5),), opponent=ampharos())
        venusaur = moved.players[0].bench[0]
        done = apply_kernel(moved, UsePokemonPower(0, venusaur.pokemon_id, 0, energy=venusaur.energy[0], source=venusaur.pokemon_id,
                                                   target=moved.players[0].active.pokemon_id))
        self.assertEqual(done.players[0].active.damage, 0)  # 場のつけかえは手札からつけたことではない

    def test_multiple_working_sources_is_cv1_and_disabled_ones_do_not_count(self):
        two = board(mon(H.RATTATA), hand=(W,), opponent=ampharos(), opponent_bench=(ampharos(),))
        rejects(self, two, AttachEnergy(0, uid(two, W), two.players[0].active.card), CV1)
        one_asleep = board(mon(H.HITMONCHAN), hand=(W,), opponent=ampharos(sleep=True), opponent_bench=(ampharos(),))
        done = attach(one_asleep, W)
        self.assertEqual(done.players[0].active.damage, 10)

    def test_knockout_by_conductivity_then_promote(self):
        state = board(mon(H.RATTATA, damage=20), hand=(W,), opponent=ampharos())
        done = attach(state, W)
        self.assertEqual(new_events(state, done, "knock_out")[0]["timing"], "energy")
        while done.decision is not None:
            done = answer(done, done.decision.options[:1])
        self.assertEqual(done.phase, Phase.MAIN)
        self.assertEqual(done.energy_attachments_this_turn, 1)
        logged(self, done)


# ---------------------------------------------------------------- 6 章: ダメージを受けたあと・防止・回復


class BoltTest(unittest.TestCase):
    def test_heads_returns_to_deck_tails_stays(self):
        for side in (HD, TL):
            state = board(mon(H.RATTATA, (W, W, W)), opponent=mon(H.ENTEI_PF2, (F,)), current=0)
            done = apply_kernel(with_coin_results(state, side), UseAttack(0, 0))
            returned = new_events(state, done, "return_in_play_to_deck")
            self.assertEqual(bool(returned), side is HD)
            self.assertEqual(new_events(state, done, "bolt_check")[0]["player"], 1)
            if side is HD:
                self.assertEqual(done.decision.kind, "promote_active")
                self.assertEqual(done.players[0].prizes_taken if hasattr(done.players[0], "prizes_taken") else len(done.players[0].prizes), 6)
            logged(self, done)

    def test_not_when_knocked_out_or_no_damage_or_bench(self):
        hp = load_card_pool().get(H.ENTEI_PF2).hp
        state = board(mon(H.HITMONCHAN, (FT, FT, FT)), opponent=mon(H.ENTEI_PF2, damage=hp - 20))
        done = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual(new_events(state, done, "bolt_check"), [])
        bench = board(mon(H.RATTATA, (W,)), opponent_bench=(mon(H.ENTEI_PF2),))
        self.assertEqual(new_events(bench, apply_kernel(bench, UseAttack(0, 0)), "bolt_check"), [])

    def test_already_asleep_does_not_work(self):
        state = board(mon(H.RATTATA, (W,)), opponent=mon(H.ENTEI_PF2, sleep=True))
        done = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(new_events(state, done, "bolt_check"), [])


class ProtectiveFlameTest(unittest.TestCase):
    def test_bench_protected_next_opponent_turn(self):
        state = board(mon(H.ENTEI_PF2, (F, F, F)), bench=(H.RATTATA,), opponent=mon(H.CHANSEY))
        done = apply_kernel(state, UseAttack(0, 0))
        bench = done.players[0].bench[0]
        self.assertTrue(any(isinstance(e, BenchProtection) for e in bench.persistent_effects))
        logged(self, done)


class CrystalBodyTest(unittest.TestCase):
    def test_effects_blocked_damage_received(self):
        state = board(mon(H.TANGELA, (G, G, G)), opponent=mon(H.SUICUNE_NEO3))
        done = apply_kernel(state, UseAttack(0, 1))  # どくのこな（ダメージのあと、コインなしでどく）
        self.assertGreater(done.players[1].active.damage, 0)
        self.assertIsNone(done.players[1].active.conditions.poison)
        prevented = new_events(state, done, "effect_prevented")
        self.assertEqual((prevented[0]["persistent_effect"], prevented[0]["source_card"]), ("crystal_body", state.players[1].active.card))
        logged(self, done)
        # 効果だけを決めるコインは、効果が無効なら投げるかが決まらない（v0.31 の HC3。バリアー・ひかりのはどうと同じ問い）
        rejects(self, state, UseAttack(0, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")

    def test_status_stops_the_power(self):
        state = board(mon(H.TANGELA, (G, G, G)), opponent=mon(H.SUICUNE_NEO3, confusion=True))
        done = apply_kernel(state, UseAttack(0, 1))
        self.assertIsNotNone(done.players[1].active.conditions.poison)

    def test_gas_stops_it(self):
        state = board(mon(H.TANGELA, (G, G, G)), opponent=mon(H.SUICUNE_NEO3), bench=(mon(H.MUK, played_turn=1, evolved_from=H.FOSSIL_GRIMER, evolved_turn=3),))
        done = apply_kernel(state, UseAttack(0, 1))
        self.assertIsNotNone(done.players[1].active.conditions.poison)

    def test_own_attack_effects_and_trainers_are_not_blocked(self):
        state = board(mon(H.SUICUNE_NEO3, (W, W, W)), opponent=mon(H.CHANSEY))
        done = apply_kernel(with_coin_results(state, HD, HD), UseAttack(0, 0))
        self.assertTrue(done.players[1].active.conditions.paralyzed)


class SolarPowerTest(unittest.TestCase):
    def venusaur(self, **extra):
        return mon(H.VENUSAUR_PR1, played_turn=1, evolved_from=[H.BULBASAUR, H.IVYSAUR], evolved_turn=5, **extra)

    def test_cures_both_actives_once_per_turn(self):
        state = board(mon(H.RATTATA, poison=10), bench=(self.venusaur(),), opponent=mon(H.RATTATA, sleep=True))
        venusaur = state.players[0].bench[0]
        done = apply_kernel(state, UsePokemonPower(0, venusaur.pokemon_id, 0))
        self.assertIsNone(done.players[0].active.conditions.poison)
        self.assertFalse(done.players[1].active.conditions.asleep)
        rejects(self, done, UsePokemonPower(0, venusaur.pokemon_id, 0), "POWER_ALREADY_USED", error=IllegalActionError)

    def test_nothing_to_cure_is_so1_and_own_status_blocks(self):
        state = board(self.venusaur())
        rejects(self, state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0), SO1)
        asleep = board(self.venusaur(sleep=True))
        rejects(self, asleep, UsePokemonPower(0, asleep.players[0].active.pokemon_id, 0), "POKEMON_ASLEEP", error=IllegalActionError)


# ---------------------------------------------------------------- 7 章: ワザ


class AttackTest(unittest.TestCase):
    def test_dark_drain_per_pokemon_coins_and_dealt_total(self):
        state = board(mon(H.DARK_CROBAT, (G, G, G), evolved_from=[H.ZUBAT_NEO3, H.DARK_GOLBAT], played_turn=1, evolved_turn=5, damage=30),
                      opponent_bench=(H.RATTATA, H.RATTATA))
        done = apply_kernel(with_coin_results(state, HD, TL, HD), UseAttack(0, 0))
        coins = new_events(state, done, "pokemon_coin_results")[0]
        heads = [r[0] for r in coins["results"] if r[1] == "heads"] if isinstance(coins["results"][0], (list, tuple)) else None
        damaged = [e["pokemon_id"] if "pokemon_id" in e else e.get("target_pokemon_id") for e in new_events(state, done, "damage")]
        self.assertEqual(len(damaged), 2)
        if heads is not None:
            self.assertEqual(sorted(heads), sorted(damaged))
        self.assertEqual(new_events(state, done, "drain_heal")[0]["counters"], 2)
        self.assertEqual(done.players[0].active.damage, 10)
        logged(self, done)

    def test_hand_trainer_lock_only(self):
        state = board(mareep_line(H.DARK_FLAAFFY, (L, L, L)))
        done = apply_kernel(with_coin_results(state, HD), UseAttack(0, 0))
        self.assertEqual([l.origin for l in done.trainer_locks], ["attack_hand"])

    def test_stun_wave_until_end_of_next_own_turn(self):
        state = board(mareep_line(H.DARK_FLAAFFY, (L, L, L)), opponent=mon(H.DARK_GOLBAT, evolved_from=H.ZUBAT_NEO3, played_turn=0, evolved_turn=4))
        done = apply_kernel(state, UseAttack(0, 1))
        effects = [e for e in done.players[1].active.persistent_effects if isinstance(e, PowersStopped)]
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0].active_turn, state.turn_number + 2)

    def test_shock_bolt_discards_all_lightning_cards(self):
        state = board(ampharos(energy=(L, L, L, W)) if False else mareep_line(H.DARK_AMPHAROS, (L, L, W)), opponent=mon(H.CHANSEY))
        done = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(len(new_events(state, done, "discard_energy")), 2)
        self.assertEqual(done.players[1].active.damage, 50)

    def test_aurora_wave_two_coins(self):
        for coins, expected in (((HD, HD), "paralyzed"), ((HD, TL), "asleep"), ((TL, TL), None)):
            state = board(mon(H.SUICUNE_NEO3, (W, W, W)), opponent=mon(H.CHANSEY))
            done = apply_kernel(with_coin_results(state, *coins, TL), UseAttack(0, 0))  # 最後の「うら」はポケモンチェックのねむりのコイン
            c = done.players[1].active.conditions
            self.assertEqual((c.paralyzed, c.asleep), (expected == "paralyzed", expected == "asleep"), coins)
            attack_coins = [e for e in new_events(state, done, "coin_flip") if e.get("source") != "pokemon_check"]
            self.assertEqual(len(attack_coins), 2)

    def test_crimson_flame_two_fire_cards_or_no_damage(self):
        state = board(mon(H.ENTEI_NEO3, (F, F, F)), opponent=mon(H.CHANSEY))
        waiting = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual((waiting.decision.kind, waiting.decision.min_choices), ("discard_energy", 2))


class MoreRoutesTest(unittest.TestCase):
    """docs 9 章の検証の残り（実際の操作列で届く経路）。"""

    def test_rain_dance_is_a_hand_attach_and_triggers_conductivity(self):
        """あまごい（手札から「水」エネルギーカードをつける特殊能力）も手札からつけたことなので、相手の［かんでん］がはたらく（GR-2000-P310-ATTACH-ENERGY）。
        手札からつける通常の操作の回数は変えない。"""
        state = board(mon(H.SQUIRTLE), bench=(mon(H.BLASTOISE, played_turn=1, evolved_from=[H.SQUIRTLE, H.WARTORTLE], evolved_turn=5),), hand=(W,),
                      opponent=ampharos())
        blastoise = state.players[0].bench[0]
        done = apply_kernel(state, UsePokemonPower(0, blastoise.pokemon_id, 0, energy=uid(state, W), target=state.players[0].active.pokemon_id))
        self.assertEqual(new_events(state, done, "conductivity")[0]["amount"], 10)
        self.assertEqual(done.players[0].active.damage, 10)
        self.assertEqual(done.energy_attachments_this_turn, 0)
        self.assertEqual((done.phase, done.current_player), (Phase.MAIN, 0))
        logged(self, done)

    def test_energy_evolution_keeps_the_normal_evolution_limits(self):
        """その番に場に出したイーブイは、「おもて」でも山札から重ねられない（通常の進化の制限。選べるカードのない決定を出して答えを待つ）。"""
        state = board(mon(H.RATTATA), bench=(mon(H.EEVEE_NEO2, played_turn=7),), hand=(W,), deck=[H.VAPOREON, W])
        eevee = state.players[0].bench[0]
        waiting = attach(state, W, eevee)
        searching = answer(with_coin_results(waiting, HD), waiting.decision.options)
        self.assertEqual((searching.decision.kind, searching.decision.options), ("search_deck", ()))
        done = answer(searching, ())
        self.assertEqual(kinds(searching, done), ["evolve_from_deck_none", "shuffle"])
        self.assertEqual(done.card_def(done.players[0].bench[0].card).name_ja, "イーブイ")

    def test_breeder_evolution_offers_chain_reaction_then_finishes_the_trainer(self):
        state = board(mon(H.BULBASAUR, played_turn=1), bench=(mon(H.EEVEE_PRN, played_turn=1),), hand=(H.POKEMON_BREEDER, H.VENUSAUR_PR1),
                      deck=[H.VAPOREON, W, W])
        breeder = uid(state, H.POKEMON_BREEDER)
        step = apply_kernel(state, PlayTrainer(0, breeder))
        step = answer(step, (state.players[0].active.pokemon_id,))
        step = answer(step, step.decision.options[:1])
        self.assertEqual((step.decision.kind, step.decision.player), ("reaction_power", 0))
        self.assertIsNotNone(step.trainer_in_use)
        step = answer(step, step.decision.options)
        done = answer(step, step.decision.options[:1])
        self.assertIsNone(done.trainer_in_use)
        self.assertIn(breeder, done.players[0].discard)
        self.assertEqual(done.card_def(done.players[0].bench[0].card).name_ja, "シャワーズ")
        logged(self, done)

    def test_hand_trainer_lock_blocks_only_trainers_from_hand(self):
        state = board(mareep_line(H.DARK_FLAAFFY, (L, L, L)), opponent_hand=(H.POTION, H.PLUSPOWER))
        locked = apply_kernel(with_coin_results(state, HD), UseAttack(0, 0))
        self.assertEqual(locked.current_player, 1)
        rejects(self, locked, PlayTrainer(1, uid(locked, H.POTION, 1)), "TRAINER_PREVENTED", error=IllegalActionError)
        ended = apply_kernel(locked, EndTurn(1))
        self.assertEqual([lock.origin for lock in ended.trainer_locks], [])

    def test_stun_wave_expires_at_the_end_of_the_next_own_turn(self):
        state = board(mareep_line(H.DARK_FLAAFFY, (L, L, L)), opponent=mon(H.RAIKOU_NEO3))
        stunned = apply_kernel(state, UseAttack(0, 1))
        raikou = stunned.players[1].active
        self.assertIsNotNone(powers_stopped(stunned, raikou))
        after_opponent = apply_kernel(stunned, EndTurn(1))
        self.assertIsNotNone(powers_stopped(after_opponent, after_opponent.players[1].active))
        after_own = apply_kernel(after_opponent, EndTurn(0))
        self.assertIsNone(powers_stopped(after_own, after_own.players[1].active))

    def test_metronome_copies_new_attacks_without_internal_errors(self):
        """ゆびをふる（必要なエネルギーを払わない）でオーロラウェーブ・ショックボルト・ダークドレインを使っても内部エラーにならない。"""
        # ショックボルト: ついている「雷」エネルギーカードがなければトラッシュできず、ダメージはなくなる（ゆびをふるは必要なエネルギーを払わない）
        state = board(mon(H.CLEFAIRY, (W, W, W)), opponent=mareep_line(H.DARK_AMPHAROS, player=1))
        choosing = apply_kernel(state, UseAttack(0, 1))
        done = answer(choosing, choosing.decision.options[:1])
        self.assertEqual(done.players[1].active.damage, 0)
        self.assertEqual(new_events(state, done, "discard_energy"), [])
        logged(self, done)
        # ダークドレイン: ピッピがワザを使ったポケモンとして、相手の場のポケモンごとにコイン・与えた合計ぶん回復
        state = board(mon(H.CLEFAIRY, (W, W, W), damage=20), opponent=mon(H.DARK_CROBAT, evolved_from=[H.ZUBAT_NEO3, H.DARK_GOLBAT], played_turn=0, evolved_turn=6))
        choosing = apply_kernel(state, UseAttack(0, 1))
        done = answer(with_coin_results(choosing, HD, HD), choosing.decision.options[:1])
        self.assertEqual(new_events(choosing, done, "drain_heal")[0]["counters"], 2)
        logged(self, done)
        # オーロラウェーブを［クリスタルボディ］のスイクンに: 効果だけを決めるコインは HC3（v0.31 の問い。内部エラーにしない）。選べるワザがそれだけなので、どの答えも
        # 止まる決定を残さず、ゆびをふるの宣言の前に止める
        state = board(mon(H.CLEFAIRY, (W, W, W)), opponent=mon(H.SUICUNE_NEO3))
        rejects(self, state, UseAttack(0, 1), "UNRESOLVED_PREVENTED_EFFECT_COIN")


class DocumentTest(unittest.TestCase):
    def test_doc_and_research_links(self):
        self.assertTrue(DOC.exists())
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        for code in NEW_CODES:
            # v0.97: 研究の基準を kyuura 73a1690 に上げた。CV1 は kyuura の論点 UQ-SELF-EXCLUDING-POWER-COPIES の事例と同じ問いだが、kyuura の未解決の一覧（v0.68 までの取り込み）に
            # CV1 の行がない（docs/unown-research-idfnj-v0.97.md 3 章）
            expected = "issue_not_in_index" if code == CV1 else "not_in_kyuura"
            self.assertEqual(links["stop_codes"][code]["kyuura_disposition"], expected, code)


if __name__ == "__main__":
    unittest.main()
