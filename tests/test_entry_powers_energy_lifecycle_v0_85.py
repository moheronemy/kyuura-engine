"""v0.85（docs/entry-powers-energy-lifecycle-v0.85.md）: 進化したときの特殊能力・エネルギーを動かすポケモン 13 枚とミラクルエネルギー。

根拠は kyuura データの採用（kyuura ``7d3f4ca`` の data/cards.json の日本語の印刷の文面）と、既存の規定の記録（GR-2000-P310-EVOLUTION・GR-2000-P312-DECK-HAND-DISCARD・
GR-2000-P320-RECOVERY・RUL-ENERGY-DISCARD-ATTACKS・CR-ENERGY-TRANS-NOT-ATTACHMENT など。docs 各章）。公式ガイドブックの新しい読み直し・カードの画像・pcg-search.com との
照合はしていない。
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
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.deck import deck_problems
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import HIDDEN_COUNT_KINDS, PUBLIC_EVENTS, observe
from kyuura_engine.persistent import status_immunity_next_turn
from kyuura_engine.state import Phase, StatusImmunityNextTurn
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.release_catalog import cards_before
from tests.test_neo_trainer_components_v0_80 import audited, mon, new_events, rejects
from tests.test_shining_gentle_v0_83 import answer, attack, board, play

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "entry-powers-energy-lifecycle-v0.85.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, F, G, L, P, FT = H.WATER, H.FIRE, H.GRASS, H.LIGHTNING, H.PSYCHIC, H.FIGHTING
MIR, RAINBOW, ECO, RE, DCE = H.MIRACLE_ENERGY, H.RAINBOW_ENERGY, H.ECOGYM, H.RECYCLE_ENERGY, H.DOUBLE_COLORLESS_ENERGY
HC6 = "UNRESOLVED_DISCARD_DECK_SHORT"
PW3 = "UNRESOLVED_POWER_ZERO_CARDS"
MEC1 = "UNRESOLVED_MIRACLE_ENERGY_AS_TYPE"
MEW1 = "UNRESOLVED_MIRACLE_ENERGY_UNDER_WIND"


def stage1(card, energy=(), *, base, **extra):
    return mon(card, energy, played_turn=1, evolved_from=base, evolved_turn=3, **extra)


def stage2(card, energy=(), *, line, **extra):
    return mon(card, energy, played_turn=1, evolved_from=list(line), evolved_turn=5, **extra)


def croconaw(**extra):
    return stage1(H.CROCONAW_PF1, (W, W), base=H.TOTODILE_NEO1, **extra)


def meganium(**extra):
    return stage2(H.MEGANIUM_NEO1, extra.pop("energy", ()), line=(H.CHIKORITA_NEO1, H.BAYLEEF_NEO1), **extra)


def togetic(energy=(), **extra):
    return mon(H.LIGHT_TOGETIC, energy, evolved_from=H.TOGEPI_NEO1, **extra)


def light_dragonite(energy=(), **extra):
    return mon(H.LIGHT_DRAGONITE, energy, evolved_from=[H.DRATINI, H.LIGHT_DRAGONAIR], **extra)


def evolve(state, card_id, target=None, player=0):
    uid = next(u for u in state.players[player].hand if state.cards[u].card_id == card_id)
    target = state.players[player].active if target is None else target
    return apply_kernel(state, EvolvePokemon(player, uid, target.pokemon_id))


def kinds(before, after):
    return [e["kind"] for e in new_events(before, after)]


def power(state, pokemon=None, *, coins=(), player=0, **choices):
    pokemon = state.players[player].active if pokemon is None else pokemon
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, UsePokemonPower(player, pokemon.pokemon_id, 0, **choices))


def logged(test, state):
    """盤面を直接作ったテストの確かめ（不変条件・書き出し・観測）。ログの組み立て直し（``log_audit.log_problems``）は、正式な開始からの対戦で確かめる（ログに対戦の始めがない）。"""
    audited(test, state)


# ---------------------------------------------------------------- 1 章: 登録と数


class RegistrationTest(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(tuple(read_extract()['pool_v0_85']), H.V0_85_CARDS)
        pool = load_card_pool()
        self.assertLessEqual(set(H.V0_85_CARDS), pool.playable_ids)

    def test_without_v0_85_registrations_gives_back_1039(self):
        registry = E.DEFAULT_EFFECTS
        attacks = {k: v for k, v in registry._attacks.items() if k not in E.V0_85_ATTACKS}
        powers = {k: v for k, v in registry._powers.items() if k not in E.V0_85_POWERS}
        energies = {k: v for k, v in registry._energies.items() if k not in E.V0_85_ENERGIES}
        before = E.EffectRegistry(registry.id, attacks, registry._trainers, powers, energies)
        pool = pool_from_extract(read_extract(), before)
        self.assertEqual(load_card_pool().playable_ids - pool.playable_ids, frozenset(H.V0_85_CARDS))  # ほかのカードの対応は変わらない
        self.assertTrue(all(card not in pool.playable_ids for card in H.V0_85_CARDS))

    def test_quiz_names_and_identity_trials(self):
        """カツラのクイズの名前の候補（新しい名前はメガニウム・バクフーン・オーダイル。v0.85 までの写しで 404）・マチスの秘策の試す回数が上限の中（docs 1 章・9 章）。
        今の未対応の数・名前の候補の数・試すカードの数は tests/test_catalog_contract.py。"""
        from kyuura_engine import engine
        pool = load_card_pool()
        names = {pool.get(c).name_ja for c in pool.playable_ids if pool.get(c).category == "pokemon"}
        self.assertEqual(len({pool.get(c).name_ja for c in cards_before(read_extract(), "0.86") if pool.get(c).category == "pokemon"}), 404)  # この版までの写しのポケモンの名前（今の総数は tests/test_catalog_contract.py）
        self.assertTrue({"メガニウム", "バクフーン", "オーダイル"} <= names)
        candidates = engine._identity_candidates(pool)
        basics = [c for c in candidates if pool.get(c).category == "pokemon" and pool.get(c).stage == "basic"]
        # v0.118: 1 枚を指定するコマンドの試す回数は、v0.117 から上限 512 ではなく分岐の作りから決まる回数（``_single_identity_budget``。たねが 511 枚になり、
        # 1 + 511 + 1 = 513 が 512 を超えた。その回数どおりに確かめることは tests/test_secret_plan_single_identity_v0_117.py）。上限 512 は 2 枚目の割り当てが要るコマンドだけ
        self.assertLessEqual(1 + len(basics) + 1, engine._single_identity_budget(basics, [c for c in candidates if c not in basics]))

    def test_every_attack_and_power_is_registered(self):
        pool = load_card_pool()
        for card_id in H.V0_85_POKEMON:
            definition = pool.get(card_id)
            self.assertTrue(definition.supported, (card_id, definition.unsupported_reasons))
            for index in range(len(definition.attacks)):
                self.assertIn(E.AttackKey(card_id, index), E.V0_85_ATTACKS)
            for index in range(len(definition.powers)):
                self.assertIn(E.PowerKey(card_id, index), E.V0_85_POWERS)
        self.assertEqual((len(E.V0_85_ATTACKS), len(E.V0_85_POWERS), len(E.V0_85_ENERGIES)), (17, 9, 1))

    def test_miracle_has_no_one_copy_limit(self):
        # 「デッキに1枚まで」は英語の文面だけ。日本語の文面にないので、4 枚入れてよい
        deck = H.expand_decklist({MIR: 4, H.LIGHT_TOGETIC: 4, H.TOGEPI_NEO1: 4, W: 48})
        self.assertNotIn("TOO_MANY_COPIES", {p.code for p in deck_problems(deck, load_card_pool())})

    def test_new_public_events(self):
        for kind in ("power_discard_deck", "power_attach_from_deck", "power_attach_from_discard", "miracle_energy_discarded", "attack_discard_to_deck"):
            self.assertIn(kind, PUBLIC_EVENTS)
        self.assertIn("attach_from_deck", HIDDEN_COUNT_KINDS)


# ---------------------------------------------------------------- 2 章: 進化したときの特殊能力


class BerserkTest(unittest.TestCase):
    """［あばれんぼう］: 手札から進化させたときにかならずはたらく。コインで相手か自分の山札の上 5 枚。どちらかが 5 枚より少なければ HC6（進化させる前）。"""

    def board(self, **extra):
        return board(croconaw(), hand=(H.FERALIGATR_NEO1,), **extra)

    def test_heads_mills_opponent_tails_mills_self(self):
        for side, owner in ((HD, 1), (TL, 0)):
            state = self.board()
            done = evolve(with_coin_results(state, side), H.FERALIGATR_NEO1)
            self.assertIsNone(done.decision)
            milled = new_events(state, done, "power_discard_deck")
            self.assertEqual(len(milled), 1)
            self.assertEqual((milled[0]["player"], len(milled[0]["cards"])), (owner, 5))
            self.assertEqual(len(done.players[owner].deck), 5)
            power_event = new_events(state, done, "pokemon_power")[0]
            self.assertTrue(power_event["forced"])
            logged(self, done)

    def test_reaching_zero_cards_is_not_a_loss(self):
        state = board(croconaw(), hand=(H.FERALIGATR_NEO1,), deck=[W] * 5)
        done = evolve(with_coin_results(state, TL), H.FERALIGATR_NEO1)
        self.assertEqual(len(done.players[0].deck), 0)
        self.assertNotEqual(done.phase, Phase.GAME_OVER)

    def test_short_deck_stops_before_evolving(self):
        for deck, opponent_deck in (([W] * 4, None), (None, [W] * 4)):
            state = board(croconaw(), hand=(H.FERALIGATR_NEO1,), deck=deck, opponent_deck=opponent_deck)
            uid = state.players[0].hand[0]
            rejects(self, state, EvolvePokemon(0, uid, state.players[0].active.pokemon_id), HC6)

    def test_not_declarable_and_no_opportunity(self):
        state = self.board()
        done = evolve(with_coin_results(state, HD), H.FERALIGATR_NEO1)
        self.assertEqual(new_events(state, done, "entry_power_declined"), [])
        rejects(self, done, UsePokemonPower(0, done.players[0].active.pokemon_id, 0), "POWER_NOT_DECLARABLE", error=IllegalActionError)

    def test_gas_suppresses(self):
        state = board(croconaw(), hand=(H.FERALIGATR_NEO1,), opponent=mon(H.MUK, played_turn=2, evolved_from=H.FOSSIL_GRIMER, evolved_turn=4))
        done = evolve(state, H.FERALIGATR_NEO1)
        self.assertEqual(new_events(state, done, "power_discard_deck"), [])
        self.assertEqual(new_events(state, done, "coin_flip"), [])

    def test_breeder_route_triggers(self):
        state = board(mon(H.TOTODILE_NEO1, played_turn=1), hand=(H.FERALIGATR_NEO1, H.POKEMON_BREEDER))
        choosing = play(state, H.POKEMON_BREEDER)
        card = answer(choosing, (state.players[0].active.pokemon_id,))
        done = answer(with_coin_results(card, HD), card.decision.options[:1])
        self.assertEqual(len(new_events(state, done, "power_discard_deck")), 1)
        logged(self, done)
        short = board(mon(H.TOTODILE_NEO1, played_turn=1), hand=(H.FERALIGATR_NEO1, H.POKEMON_BREEDER), deck=[W] * 3)
        breeder = next(u for u in short.players[0].hand if short.cards[u].card_id == H.POKEMON_BREEDER)
        rejects(self, short, PlayTrainer(0, breeder), HC6)  # 進化させられる組がほかにないので、使う前に止まる


class HerbalScentTest(unittest.TestCase):
    def board(self, card=H.MEGANIUM_PF1):
        return board(stage1(H.BAYLEEF_PF1, (G,), base=H.CHIKORITA_NEO1, damage=40), hand=(card,),
                     bench=(mon(H.CHIKORITA_NEO1, damage=10), mon(H.RATTATA, damage=10)), opponent=mon(H.CHIKORITA_NEO1, damage=20))

    def test_heads_heals_every_grass_pokemon_on_both_sides(self):
        for card in (H.MEGANIUM_PF1, H.MEGANIUM_NIP1X):
            state = self.board(card)
            asking = evolve(state, card)
            self.assertEqual(asking.decision.kind, "entry_power")
            done = answer(with_coin_results(asking, HD), asking.decision.options)
            self.assertEqual([p.damage for p in done.players[0].in_play()], [0, 0, 10])  # ラッタ（無色）はそのまま
            self.assertEqual(done.players[1].active.damage, 0)
            self.assertEqual(len(new_events(asking, done, "coin_flip")), 1)
            logged(self, done)

    def test_tails_and_decline(self):
        state = self.board()
        asking = evolve(state, H.MEGANIUM_PF1)
        tails = answer(with_coin_results(asking, TL), asking.decision.options)
        self.assertEqual([p.damage for p in tails.players[0].in_play()], [40, 10, 10])
        declined = answer(asking, ())
        self.assertEqual(kinds(asking, declined), ["entry_power_declined"])


class FireBoostTest(unittest.TestCase):
    def board(self, deck):
        return board(stage1(H.QUILAVA_PF1, (F,), base=H.CYNDAQUIL_NEO1), hand=(H.TYPHLOSION_PF1,), deck=deck)

    def boosted(self, deck=None):
        state = self.board([F] * 3 + [W] * 5 if deck is None else deck)
        asking = evolve(state, H.TYPHLOSION_PF1)
        return state, answer(with_coin_results(asking, HD), asking.decision.options)

    def test_heads_attaches_up_to_four_and_shuffles(self):
        _, choosing = self.boosted()
        self.assertEqual((choosing.decision.kind, choosing.decision.max_choices, len(choosing.decision.options)), ("attach_from_deck", 4, 3))
        done = answer(choosing, choosing.decision.options)
        self.assertEqual(len(done.players[0].active.energy), 4)
        self.assertEqual(kinds(choosing, done), ["power_attach_from_deck"] * 3 + ["shuffle"])
        self.assertEqual(done.energy_attachments_this_turn, 0)  # 手札からつける通常の操作ではない
        logged(self, done)

    def test_zero_with_candidates_is_pw3_and_empty_deck_decision_waits(self):
        _, choosing = self.boosted()
        rejects(self, choosing, lambda s: ResolveDecision(0, s.decision.id, ()), PW3)
        _, empty = self.boosted([W] * 8)
        self.assertEqual((empty.decision.options, empty.decision.max_choices), ((), 4))  # 選べるものの数で最大の枚数を変えない
        done = answer(empty, ())
        self.assertEqual(kinds(empty, done), ["shuffle"])

    def test_hidden_from_opponent_and_continuation_survives_copies(self):
        _, choosing = self.boosted()
        shown = observe(choosing, 1)["decision"]
        self.assertNotIn("options", shown)
        expected = answer(choosing, choosing.decision.options[:1])
        for copied in (choosing.clone(), copy.deepcopy(choosing), pickle.loads(pickle.dumps(choosing))):
            self.assertEqual(kinds(choosing, answer(copied, copied.decision.options[:1])), kinds(choosing, expected))

    def test_tails_does_not_shuffle(self):
        state = self.board([F] * 3 + [W] * 5)
        asking = evolve(state, H.TYPHLOSION_PF1)
        done = answer(with_coin_results(asking, TL), asking.decision.options)
        self.assertEqual(new_events(asking, done, "shuffle"), [])

    def test_rainbow_in_deck_stops_only_when_used(self):
        state = self.board([F, RAINBOW] + [W] * 5)
        asking = evolve(state, H.TYPHLOSION_PF1)
        self.assertEqual(asking.decision.context_value("unresolved_code"), "UNRESOLVED_RAINBOW_ATTACH_AS_TYPE")
        answer(asking, ())  # 使わないことはいつも答えになる


# ---------------------------------------------------------------- 3 章: おいしげる


class WildGrowthTest(unittest.TestCase):
    def test_grass_energy_cards_on_own_grass_pokemon_give_two(self):
        state = board(mon(H.CHIKORITA_NEO1, (G, W)), bench=(meganium(),), opponent=mon(H.CHIKORITA_NEO1, (G,)))
        own, other = state.players[0].active, state.players[1].active
        self.assertEqual(len(E.attached_units(state, own)), 3)  # 「草」1 枚が 2 個・「水」は 1 個
        self.assertEqual(len(E.attached_units(state, other)), 1)  # 相手のポケモンには当てはまらない
        self.assertEqual(len(own.energy), 2)  # カードの枚数は変わらない

    def test_non_grass_pokemon_and_status(self):
        state = board(mon(H.RATTATA, (G,)), bench=(meganium(),))
        self.assertEqual(len(E.attached_units(state, state.players[0].active)), 1)
        asleep = board(meganium(energy=(G,), sleep=True))
        self.assertEqual(len(E.attached_units(asleep, asleep.players[0].active)), 1)

    def test_retreat_uses_units(self):
        state = board(mon(H.BAYLEEF_NEO1, (G,), played_turn=1, evolved_from=H.CHIKORITA_NEO1, evolved_turn=3), bench=(meganium(),))
        bench = state.players[0].bench[0]
        done = apply_kernel(state, Retreat(0, tuple(state.players[0].active.energy), bench.card))  # にげる 2 を「草」1 枚（2 個）で払う
        self.assertEqual(done.players[0].active.pokemon_id, bench.pokemon_id)
        logged(self, done)

    def test_rainbow_ambiguity_stops_only_when_payment_changes(self):
        state = board(mon(H.CHIKORITA_NEO1, (RAINBOW,)), bench=(meganium(),))
        active = state.players[0].active
        attacks = state.card_def(active.card).attacks
        self.assertEqual(E.wild_growth_ambiguities(state, active), [(active.energy[0], "rb1")])
        for attack_def in attacks:
            problem = E.attack_cost_problem(state, active, attack_def)
            if len(attack_def.cost) <= 1:
                self.assertIsNone(problem)
            else:
                self.assertEqual(problem.code, "UNRESOLVED_RAINBOW_ENERGY_TYPE")

    def test_wind_neutralized_special_is_not_grass(self):
        state = board(mon(H.CHIKORITA_NEO1, (RAINBOW,)), bench=(meganium(),), opponent=light_dragonite())
        active = state.players[0].active
        self.assertEqual(E.wild_growth_ambiguities(state, active), [])
        self.assertEqual(E.attached_units(state, active), [E.COLORLESS_UNIT])


# ---------------------------------------------------------------- 4 章: エネルギーを動かす特殊能力とワザ


class FireRechargeTest(unittest.TestCase):
    def board(self, **extra):
        return board(stage2(H.TYPHLOSION_NEO1, line=(H.CYNDAQUIL_NEO1, H.QUILAVA_PF1)), bench=(mon(H.CHARMANDER), mon(H.RATTATA)), **extra)

    def test_heads_card_then_target(self):
        state = self.board(discard=(F, W))
        card = power(state, coins=(HD,))
        self.assertEqual((card.decision.kind, card.decision.min_choices), ("attach_from_discard", 1))
        target = answer(card, card.decision.options)
        self.assertEqual(target.decision.options, (state.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id))  # ラッタは「炎」でない
        done = answer(target, target.decision.options[1:])
        self.assertEqual(len(done.players[0].bench[0].energy), 1)
        logged(self, done)
        rejects(self, done, UsePokemonPower(0, done.players[0].active.pokemon_id, 0), "POWER_ALREADY_USED", error=IllegalActionError)

    def test_tails_uses_the_turn_and_no_card_is_pw3(self):
        state = self.board(discard=(F,))
        done = power(state, coins=(TL,))
        self.assertIsNone(done.decision)
        rejects(self, done, UsePokemonPower(0, done.players[0].active.pokemon_id, 0), "POWER_ALREADY_USED", error=IllegalActionError)
        rejects(self, self.board(discard=(W,)), UsePokemonPower(0, 1, 0), PW3)


class DownpourTest(unittest.TestCase):
    def board(self, card=H.FERALIGATR_PF1):
        return board(stage2(card, line=(H.TOTODILE_NEO1, H.CROCONAW_PF1)), hand=(W, W, F, RE))

    def test_any_number_of_times_one_water_card_each(self):
        for card in (H.FERALIGATR_PF1, H.FERALIGATR_NIP2X):
            state = self.board(card)
            waters = [u for u in state.players[0].hand if state.cards[u].card_id == W]
            once = power(state, energy=waters[0])
            twice = power(once, energy=waters[1])
            self.assertEqual([e["cards"] for e in new_events(state, twice, "discard_from_hand")], [(waters[0],), (waters[1],)])
            self.assertEqual(new_events(state, twice, "energy_returned_to_hand"), [])
            logged(self, twice)

    def test_needs_a_water_card(self):
        state = self.board()
        fire = next(u for u in state.players[0].hand if state.cards[u].card_id == F)
        recycle = next(u for u in state.players[0].hand if state.cards[u].card_id == RE)
        rejects(self, state, UsePokemonPower(0, 1, 0), "POWER_CHOICE_MISSING", error=IllegalActionError)
        rejects(self, state, UsePokemonPower(0, 1, 0, energy=fire), "WRONG_ENERGY_TYPE", error=IllegalActionError)
        rejects(self, state, UsePokemonPower(0, 1, 0, energy=recycle), "WRONG_ENERGY_TYPE", error=IllegalActionError)


class FireRaiseTest(unittest.TestCase):
    def board(self, bench_energy, **extra):
        return board(stage2(H.CHARIZARD_PF2, (F,), line=(H.CHARMANDER, H.CHARMELEON_BASE)), bench=(mon(H.RATTATA, bench_energy),), **extra)

    def test_up_to_two_from_other_pokemon(self):
        state = self.board((F, F, F, W))
        choosing = power(state)
        self.assertEqual((len(choosing.decision.options), choosing.decision.max_choices), (3, 2))
        self.assertNotIn(state.players[0].active.energy[0], choosing.decision.options)  # このカードについているカードは選べない
        done = answer(choosing, choosing.decision.options[:2])
        self.assertEqual(len(done.players[0].active.energy), 3)
        logged(self, done)
        rejects(self, choosing, lambda s: ResolveDecision(0, s.decision.id, ()), PW3)

    def test_no_fire_card_is_pw3_and_miracle_on_shining_stops_per_card(self):
        rejects(self, self.board((W,)), UsePokemonPower(0, 1, 0), PW3)
        state = board(stage2(H.CHARIZARD_PF2, (F,), line=(H.CHARMANDER, H.CHARMELEON_BASE)), bench=(mon(H.SHINING_MAGIKARP, (F, MIR)),))
        choosing = power(state)
        miracle = next(u for u in state.players[0].bench[0].energy if state.cards[u].card_id == MIR)
        rejects(self, choosing, lambda s: ResolveDecision(0, s.decision.id, (miracle,)), MEC1)
        logged(self, answer(choosing, (state.players[0].bench[0].energy[0],)))


class StaticElectricityTest(unittest.TestCase):
    def test_up_to_mareep_count_hidden_and_shuffled(self):
        state = board(mon(H.MAREEP_NEO1, (L,)), bench=(H.MAREEP_NEO2,), opponent=mon("neo4-042"), deck=[L] * 4 + [W] * 4)
        choosing = attack(state, 0)
        self.assertEqual((choosing.decision.max_choices, len(choosing.decision.options)), (3, 4))
        self.assertNotIn("options", observe(choosing, 1)["decision"])
        done = answer(choosing, choosing.decision.options[:3])
        self.assertEqual(len(done.players[0].active.energy), 4)
        self.assertEqual(len([e for e in new_events(choosing, done, "shuffle")]), 1)
        logged(self, done)
        zero = answer(choosing, ())
        self.assertEqual([e.get("reason") for e in new_events(choosing, zero, "attach_energy_from_deck_none")], ["declined"])

    def test_empty_deck_still_waits_for_an_answer(self):
        state = board(mon(H.MAREEP_NEO1, (L,)), deck=[W] * 6)
        choosing = attack(state, 0)
        self.assertEqual((choosing.decision.options, choosing.decision.max_choices), ((), 1))


# ---------------------------------------------------------------- 5 章: ミラクルエネルギー


class MiracleEnergyTest(unittest.TestCase):
    def attached(self, holder=None, **extra):
        state = board(holder or togetic(), hand=(MIR,), **extra)
        return apply_kernel(state, AttachEnergy(0, state.players[0].hand[0], state.players[0].active.card))

    def test_two_all_color_units_and_payment(self):
        state = self.attached()
        units = E.attached_units(state, state.players[0].active)
        self.assertEqual(units, [E.ALL_COLOR_UNIT, E.ALL_COLOR_UNIT])
        self.assertNotIn(E.EnergyType.COLORLESS, E.ALL_COLOR_UNIT)
        self.assertEqual(len(E.ALL_COLOR_UNIT), 8)
        logged(self, state)

    def test_only_shining_or_light(self):
        state = board(mon(H.RATTATA), hand=(MIR,))
        rejects(self, state, AttachEnergy(0, state.players[0].hand[0], state.players[0].active.card), "ENERGY_TARGET_NOT_ALLOWED", error=IllegalActionError)

    def test_discarded_at_end_of_turn(self):
        state = self.attached()
        done = apply_kernel(state, EndTurn(0))
        events = new_events(state, done, "miracle_energy_discarded")
        self.assertEqual([e["reason"] for e in events], ["end_of_turn"])
        self.assertEqual(done.players[0].active.energy, [])
        logged(self, done)

    def test_discarded_when_holder_stops_being_light(self):
        state = board(togetic(), hand=(MIR, H.DEVOLUTION_SPRAY))
        state = apply_kernel(state, AttachEnergy(0, state.players[0].hand[0], state.players[0].active.card))
        choosing = play(state, H.DEVOLUTION_SPRAY)
        count = answer(choosing, choosing.decision.options[:1])
        done = answer(count, (1,))
        self.assertEqual([e["reason"] for e in new_events(count, done, "miracle_energy_discarded")], ["not_shining_or_light"])
        self.assertEqual(new_events(count, done, "energy_returned_to_hand"), [])
        logged(self, done)

    def test_typed_count_is_mec1(self):
        state = self.attached(holder=mon(H.SHINING_MAGIKARP))
        holder = state.players[0].active
        with self.assertRaises(UnsupportedError) as caught:
            E.require_energy_type_determined(state, holder, E.EnergyType.WATER)
        self.assertEqual(caught.exception.code, MEC1)

    def test_wind(self):
        # つけること（MEW1）・番の終わり（対戦を止める）・場にあるあいだの個数（「無色」1 個）
        state = board(togetic(), hand=(MIR,), opponent=light_dragonite())
        rejects(self, state, AttachEnergy(0, state.players[0].hand[0], state.players[0].active.card), MEW1)
        mine = board(togetic(), hand=(MIR,), bench=(light_dragonite(),))
        mine = apply_kernel(mine, AttachEnergy(0, mine.players[0].hand[0], mine.players[0].active.card))
        swapped = apply_kernel(mine, Retreat(0, (), mine.players[0].bench[0].card))
        holder = next(p for p in swapped.players[0].bench if p.energy)
        self.assertEqual(E.attached_units(swapped, holder), [E.COLORLESS_UNIT])
        halted = apply_kernel(swapped, EndTurn(0))
        self.assertEqual((halted.phase, halted.halt.code), (Phase.HALTED, MEW1))

    def test_ecogym_is_mec1_but_own_discard_is_not_ecogym(self):
        state = self.attached(opponent_hand=(H.ENERGY_REMOVAL,))
        state = apply_kernel(state, EndTurn(0))  # 番の終わりのトラッシュはこのカード自身の効果（エコロジムは当たらない）
        self.assertEqual([e.get("reasons") for e in new_events(state, state, "energy_returned_to_hand")], [])
        holder = togetic((MIR,))
        eco = board(holder, opponent=mon(H.RATTATA), hand=(ECO,), opponent_hand=(H.ENERGY_REMOVAL,))
        eco = play(eco, ECO)
        uid = eco.players[0].active.energy[0]
        self.assertEqual(E.energy_discard_problem(eco, eco.players[0].active, uid, cause=E.DISCARD_BY_TRAINER, by_player=1)[0], MEC1)
        self.assertIsNone(E.energy_discard_problem(eco, eco.players[0].active, uid, cause=E.DISCARD_BY_ENERGY, by_player=None))


# ---------------------------------------------------------------- 6 章: ワザ


class AttackTest(unittest.TestCase):
    def test_sweet_scent_chooses_side_by_coin(self):
        state = board(stage1(H.BAYLEEF_NEO1, (G,), base=H.CHIKORITA_NEO1, damage=30), bench=(mon(H.RATTATA, damage=10),),
                      opponent=mon(H.RATTATA, damage=20), opponent_bench=(H.RATTATA,))
        own = attack(state, 0, (HD,))
        self.assertEqual(own.decision.options, tuple(p.pokemon_id for p in state.players[0].in_play()))
        done = answer(own, own.decision.options[1:])
        self.assertEqual(done.players[0].bench[0].damage, 0)  # 1 個しかなければ 1 個
        logged(self, done)
        other = attack(state, 0, (TL,))
        self.assertEqual(other.decision.options, (state.players[1].active.pokemon_id,))  # ダメージカウンターののっているポケモンだけ

    def test_chomp_flips_per_own_counter(self):
        state = board(stage2(H.FERALIGATR_NEO1, (W,) * 4, line=(H.TOTODILE_NEO1, H.CROCONAW_PF1), damage=30), opponent=mon(H.CHANSEY))
        done = attack(state, 0, (HD, TL, HD))
        self.assertEqual(len(new_events(state, done, "coin_flip")), 3)
        self.assertEqual(new_events(state, done, "damage")[0]["amount"], 70)

    def test_pollen_shield_next_opponent_turn(self):
        state = board(stage1(H.BAYLEEF_PF1, (G, G, W), base=H.CHIKORITA_NEO1), opponent=mon(H.CHANSEY))
        done = attack(state, 1)
        effect = next(e for e in done.players[0].active.persistent_effects if isinstance(e, StatusImmunityNextTurn))
        self.assertEqual(effect.active_turn, effect.created_turn + 1)
        self.assertIsNotNone(status_immunity_next_turn(done, done.players[0].active))
        logged(self, done)

    def test_flame_wheel_and_spiral_flame(self):
        state = board(stage2(H.TYPHLOSION_PF1, (F,) * 4, line=(H.CYNDAQUIL_NEO1, H.QUILAVA_PF1)), bench=(H.RATTATA,), opponent=mon(H.CHANSEY),
                      opponent_bench=(H.RATTATA, H.RATTATA))
        choosing = attack(state, 0)
        self.assertEqual((choosing.decision.kind, choosing.decision.min_choices), ("discard_energy", 3))
        done = answer(choosing, choosing.decision.options[:3])
        self.assertEqual([(e.get("target"), e["amount"]) for e in new_events(choosing, done, "damage")],
                         [(None, 80), ("opponent_bench", 20), ("opponent_bench", 20), ("self_bench", 20)])
        logged(self, done)
        spiral = board(stage2(H.CHARIZARD_PF2, (F, F, F, F, DCE), line=(H.CHARMANDER, H.CHARMELEON_BASE)), opponent=mon(H.CHANSEY))
        choosing = attack(spiral, 0)
        self.assertEqual((choosing.decision.min_choices, len(choosing.decision.options)), (2, 5))  # 「エネルギーカード」（無色2個エネルギーも 1 枚）
        logged(self, answer(choosing, choosing.decision.options[3:]))

    def test_sweep_away_and_riptide(self):
        state = board(stage1(H.CROCONAW_PF1, (W, W, W), base=H.TOTODILE_NEO1), opponent=mon(H.CHANSEY), deck=[W] * 2)
        rejects(self, state, UseAttack(0, 1), HC6)
        for card in (H.FERALIGATR_PF1, H.FERALIGATR_NIP2X):
            riptide = board(stage2(card, (W, W, W), line=(H.TOTODILE_NEO1, H.CROCONAW_PF1)), discard=(W, W, F, W), opponent=mon(H.CHANSEY), deck=[F] * 5)
            done = attack(riptide, 0)
            self.assertEqual(new_events(riptide, done, "damage")[0]["amount"], 40)
            self.assertEqual(len(done.players[0].deck), 8)
            self.assertEqual([done.cards[u].card_id for u in done.players[0].discard], [F])
            logged(self, done)


class DocumentTest(unittest.TestCase):
    def test_doc_and_research_links(self):
        self.assertTrue(DOC.exists())
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        for code in (MEC1, MEW1):
            self.assertEqual(links["stop_codes"][code]["kyuura_disposition"], "not_in_kyuura")


if __name__ == "__main__":
    unittest.main()
