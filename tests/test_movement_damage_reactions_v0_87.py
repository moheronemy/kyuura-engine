"""v0.87（docs/movement-damage-reactions-v0.87.md）: 場への登場・バトル場とベンチの移動・被ダメージに反応する特殊能力と、控えの保護・「にげる」の禁止のポケモン 14 枚
（14 ワザ・14 特殊能力）と、その共通の処理（``kyuura_engine/movement.py``・``reactions.py`` の段・解決の基盤の被ダメージの窓）。

根拠は kyuura データの採用（kyuura ``7d3f4ca`` の data/cards.json の日本語の印刷の文面）と、既存の規定・記録の再利用（GR-2000-P325-SAME-TIMING・CR-ENERGY-TRANS-NOT-ATTACHMENT・
v0.10 の読取記録 docs/counterattack-v0.10.md 2 章の p.20（［どくのたいえき］）・p.138（［ショックボム］）など。docs 各章）。公式ガイドブックの新しい読み直し・カードの画像・
pcg-search.com との照合はしていない。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import unittest

from kyuura_engine import (
    EvolvePokemon,
    PlayBasicToBench,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.continuous import power_suppressed
from kyuura_engine.decisions import (
    BENCH_FROM_DECK,
    MAGMA_POOL_ENERGY,
    REACTION_ORDER,
    SPLIT_FROM_DECK,
)
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.observation import (
    HIDDEN_COUNT_KINDS,
    OPTION_MEANINGS,
    PUBLIC_EVENTS,
    observe,
)
from kyuura_engine.serialize import state_to_dict
from kyuura_engine.state import OPPONENT_POWER_SUPPRESSION
from tests import helpers as H
from tests.helpers import apply_kernel, build_test_state, with_coin_results
from tests.test_neo_trainer_components_v0_80 import (
    audited,
    mon,
    new_events,
    rejects,
    snapshot,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "movement-damage-reactions-v0.87.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, F, G, L, P, FT = H.WATER, H.FIRE, H.GRASS, H.LIGHTNING, H.PSYCHIC, H.FIGHTING
DCE, METAL = H.DOUBLE_COLORLESS_ENERGY, H.METAL_ENERGY_NEO1
TURN = 7  # 番のプレイヤー 0 の番（奇数の番が 0、偶数の番が 1）
Z9 = "UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE"
Z23 = "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE"


def board(active, *, bench=(H.RATTATA,), opponent=None, opponent_bench=(H.RATTATA,), hand=(), opponent_hand=(), deck=None, opponent_deck=None,
          current=0, turn=TURN):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": list(deck if deck is not None else [W] * 10), "discard": [], "prizes": 6}
    them = {"active": opponent or mon(H.RATTATA), "bench": list(opponent_bench), "hand": list(opponent_hand),
            "deck": list(opponent_deck if opponent_deck is not None else [W] * 10), "discard": [], "prizes": 6}
    return build_test_state([me, them], turn_number=turn, current_player=current)


def evolved(card, base, energy=(), *, player=0, **extra):
    """進化した場のポケモン（進化した番は持ち主の番。プレイヤー 0 は 3 番、1 は 4 番）。"""
    return mon(card, energy, evolved_from=base, played_turn=1 + player, evolved_turn=3 + player, **extra)


def forretress(energy=(), player=1):
    return evolved(H.FORRETRESS_NEO2, H.PINECO_NEO4, energy, player=player)


def magcargo(energy=(), player=0):
    return evolved(H.MAGCARGO_NEO3, H.SLUGMA_NEO4, energy, player=player)


def dark_magcargo(energy=(), player=1):
    return evolved(H.DARK_MAGCARGO, H.SLUGMA_NEO4, energy, player=player)


def electrode(energy=(), player=1):
    return evolved(H.LT_SURGES_ELECTRODE, H.LT_SURGES_VOLTORB, energy, player=player)


def kakuna(energy=(), player=1):
    return evolved(H.KAKUNA_ES1, H.WEEDLE, energy, player=player)


def dugtrio(energy=(), player=0):
    return evolved(H.DUGTRIO_PR1, H.DIGLETT, energy, player=player)


def uid(state, card_id, player=0, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def kinds(before, after):
    return [e["kind"] for e in new_events(before, after)]


def answer(state, choices, player=None):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player if player is None else player, d.id, tuple(choices)))


def play(state, card_id, player=0):
    return apply_kernel(state, PlayTrainer(player, uid(state, card_id, player)))


def attack(state, index=0, coins=()):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, UseAttack(state.current_player, index))


def retreat(state, count, player=0, bench_index=0):
    active = state.players[player].active
    return apply_kernel(state, Retreat(player, tuple(active.energy[:count]), state.players[player].bench[bench_index].card))


# ---------------------------------------------------------------- 1 章: 登録と数


class RegistrationTest(unittest.TestCase):
    def test_counts(self):
        pool = load_card_pool()
        categories = {"pokemon": 0, "trainer": 0, "energy": 0}
        for card_id in pool.playable_ids:
            categories[pool.get(card_id).category] += 1
        self.assertEqual((len(pool.playable_ids), categories["pokemon"], categories["trainer"], categories["energy"]), (1080, 783, 260, 37))
        registry = E.DEFAULT_EFFECTS
        self.assertEqual((len(registry.attack_keys()), len(registry._powers)), (1312, 114))
        stadiums = sum(1 for c in pool.playable_ids if pool.get(c).category == "trainer" and "stadium" in (pool.get(c).trainer_kinds or ()))
        self.assertEqual(stadiums, 41)
        self.assertEqual(tuple(read_extract()["pool_v0_87"]), H.V0_87_CARDS)

    def test_without_v0_87_registrations_gives_back_1066(self):
        registry = E.DEFAULT_EFFECTS
        attacks = {k: v for k, v in registry._attacks.items() if k.card_id not in H.V0_87_CARDS}
        powers = {k: v for k, v in registry._powers.items() if k.card_id not in H.V0_87_CARDS}
        before = E.EffectRegistry(registry.id, attacks, registry._trainers, powers, registry._energies)
        pool = pool_from_extract(read_extract(), before)
        self.assertEqual(len(pool.playable_ids), 1066)
        self.assertTrue(all(card not in pool.playable_ids for card in H.V0_87_CARDS))
        # 特殊能力を持つカードは、ワザだけの登録では対応にならない（14 枚どれも特殊能力を持つ）
        attacks_only = E.EffectRegistry(registry.id, registry._attacks, registry._trainers, powers, registry._energies)
        self.assertEqual(sorted(set(H.V0_87_CARDS) & set(pool_from_extract(read_extract(), attacks_only).playable_ids)), [])

    def test_every_attack_and_power_is_registered_and_shared(self):
        pool = load_card_pool()
        for card_id in H.V0_87_POKEMON:
            definition = pool.get(card_id)
            self.assertTrue(definition.supported, (card_id, definition.unsupported_reasons))
            self.assertEqual((len(definition.attacks), len(definition.powers)), (1, 1))
            self.assertIn(E.AttackKey(card_id, 0), E.DEFAULT_EFFECTS._attacks)
            self.assertIn(E.PowerKey(card_id, 0), E.DEFAULT_EFFECTS._powers)
        self.assertEqual((len(E.V0_87_ATTACKS), len(E.V0_87_POWERS)), (14, 14))
        registry = E.DEFAULT_EFFECTS
        for copy_id, original in E.SAME_DATA_CARDS_V0_87.items():
            self.assertIs(registry._attacks[E.AttackKey(copy_id, 0)], registry._attacks[E.AttackKey(original, 0)])
            self.assertIs(registry._powers[E.PowerKey(copy_id, 0)], registry._powers[E.PowerKey(original, 0)])
        # 同じ名前の別の版とはまとめない（第1弾のコイル・カビゴン（ジャングル）は別の登録）
        self.assertIsNot(registry._attacks.get(E.AttackKey(H.MAGNEMITE, 0)), registry._attacks[E.AttackKey(H.MAGNEMITE_ES2, 0)])
        texts = {registry._powers[E.PowerKey(c, 0)].text_ja for c in H.V0_87_POKEMON}
        self.assertEqual(len(texts), 11)

    def test_evolution_lines_use_exact_names(self):
        pool = load_card_pool()
        for card, base in ((H.FORRETRESS_NEO2, "クヌギダマ"), (H.MAGCARGO_NEO3, "マグマッグ"), (H.DARK_MAGCARGO, "マグマッグ"),
                           (H.LT_SURGES_ELECTRODE, "マチスのビリリダマ"), (H.KAKUNA_ES1, "ビードル"), (H.GENGAR_PR1, "ゴースト"), (H.DUGTRIO_PR1, "ディグダ")):
            self.assertEqual(pool.get(card).evolves_from, base)
        self.assertEqual(pool.get(H.GENGAR_PR1).stage, "stage2")

    def test_unsupported_quiz_names_and_identity_candidates(self):
        """未対応（kyuura data/engine_targets.json（7d3f4ca）の対象 1,377 件から今の登録を差し引く。../kyuura がなければ確かめない）・カツラのクイズの名前の候補
        （新しい名前は 4 つ）・マチスの秘策の試すカード（docs 10 章）。"""
        import subprocess

        from kyuura_engine import engine
        pool = load_card_pool()
        names = {pool.get(c).name_ja for c in pool.playable_ids if pool.get(c).category == "pokemon"}
        self.assertEqual(len(names), 415)
        self.assertTrue({"フォレトス", "マグカルゴ", "わるいマグカルゴ", "マチスのマルマイン"} <= names)
        candidates = engine._identity_candidates(pool)
        basics = [c for c in candidates if pool.get(c).category == "pokemon" and pool.get(c).stage == "basic"]
        self.assertEqual((len(candidates), len(basics)), IDENTITY_CANDIDATES)
        kyuura = ROOT.parent / "kyuura"
        if (kyuura / ".git").exists():
            extract = read_extract()
            targets = json.loads(subprocess.check_output(["git", "-C", str(kyuura), "show", f"{extract['source']['commit']}:data/engine_targets.json"]))
            missing = [c for c in targets["cards"] if c["id"] not in pool.playable_ids]
            self.assertEqual((len(targets["cards"]), len(missing), sum(1 for c in missing if c["id"].startswith("neo")),
                              sum(1 for c in missing if c["product_group"] != "expansion_pack")), (1377, 297, 137, 160))

    def test_new_public_events_and_decisions(self):
        for kind in ("spikes_damage", "hot_plate_damage", "movement_damage_skipped", "magma_pool", "magma_pool_none", "shock_blast_check",
                     "shock_blast_damage", "shock_blast_skipped", "poison_fluid", "poison_fluid_skipped", "split_skipped", "split_declined"):
            self.assertIn(kind, PUBLIC_EVENTS)
        for kind in (MAGMA_POOL_ENERGY, SPLIT_FROM_DECK):
            self.assertIn(kind, OPTION_MEANINGS)
        self.assertIn(SPLIT_FROM_DECK, HIDDEN_COUNT_KINDS)
        self.assertIn(BENCH_FROM_DECK, HIDDEN_COUNT_KINDS)


# 試すカード（処理の同じカードを 1 枚で代表）とそのうちのたねポケモン（docs 10 章で実測した値）
IDENTITY_CANDIDATES = (885, 401)


# ---------------------------------------------------------------- 2 章: 型の検査の修正


class TextCheckTest(unittest.TestCase):
    def attack(self, card_id, text):
        from dataclasses import replace

        definition = load_card_pool().get(card_id)
        return replace(definition.attacks[0], text_ja=text)

    def test_damage_and_self_sleep_rejects_the_other_effects(self):
        effect = E.DamageAndSelfSleep()
        for card_id in ("PMCG6-073", "PMCG6-044"):
            self.assertEqual(effect.check(load_card_pool().get(card_id).attacks[0]), [], card_id)
        snorlax = load_card_pool().get(H.SNORLAX_ES1).attacks[0]
        self.assertNotEqual(effect.check(snorlax), [])  # ねころぶ（相手もねむり）は受け付けない
        self.assertNotEqual(effect.check(self.attack("PMCG6-073", "ダメージを与えた後、相手を「ねむり」状態にする。")), [])
        self.assertEqual(E.DamageThenSelfSleepThenSleepOpponentOnHeads().check(snorlax), [])
        self.assertNotEqual(E.DamageThenSelfSleepThenSleepOpponentOnHeads().check(load_card_pool().get("PMCG6-073").attacks[0]), [])

    def test_new_text_tables_are_exact(self):
        pool = load_card_pool()
        self.assertEqual(E.ChooseOpponentPokemonDamage(10).check(pool.get(H.MAGNEMITE_ES2).attacks[0]), [])
        self.assertEqual(E.CoinsHeadsTimesBonusDamage(3, 10).check(pool.get(H.LT_SURGES_ELECTRODE).attacks[0]), [])
        self.assertNotEqual(E.CoinsHeadsTimesBonusDamage(2, 10).check(pool.get(H.LT_SURGES_ELECTRODE).attacks[0]), [])
        self.assertEqual(E.OptionalDiscardEnergyBonusDamage(E.EnergyType.FIRE, 20, False, None).check(pool.get(H.MAGCARGO_NEO3).attacks[0]), [])
        self.assertNotEqual(E.OptionalDiscardEnergyBonusDamage(E.EnergyType.WATER, 20, False, None).check(pool.get(H.MAGCARGO_NEO3).attacks[0]), [])
        self.assertEqual(E.DamageThenChosenBenchTargets(2, 10).check(pool.get(H.DUGTRIO_PR1).attacks[0]), [])
        self.assertNotEqual(E.DamageThenChosenBenchTargets(3, 10).check(pool.get(H.DUGTRIO_PR1).attacks[0]), [])

    def test_guard_text_variant_is_accepted_without_correcting_the_copy(self):
        pool = load_card_pool()
        printed = {pool.get(c).powers[0].text_ja for c in (H.SNORLAX_ES1, H.SNORLAX_QSG)}
        self.assertTrue(all(text in E.GUARD_TEXTS for text in printed))
        self.assertEqual(E.OpponentActiveCannotRetreat().check(pool.get(H.SNORLAX_ES1).powers[0]), [])


# ---------------------------------------------------------------- 4 章: 移動と登場への反応


class SpikesTest(unittest.TestCase):
    def test_switch_on_the_opponents_turn(self):
        state = board(mon(H.RATTATA), opponent=forretress(), hand=(H.SWITCH,))
        after = play(state, H.SWITCH)
        if after.decision is not None:
            after = answer(after, (after.decision.options[0],))
        damages = new_events(state, after, "spikes_damage")
        self.assertEqual(len(damages), 1)
        self.assertEqual(after.players[0].active.damage, 10)
        audited(self, after)

    def test_own_turn_movement_and_gust_do_not_trigger(self):
        state = board(forretress(player=0), opponent=mon(H.SNORLAX), hand=(H.GUST, H.SWITCH))
        after = play(state, H.GUST)
        after = answer(after, (after.decision.options[0],))
        self.assertEqual(new_events(state, after, "spikes_damage"), [])
        audited(self, after)

    def test_retreat_and_two_sources(self):
        # 発生源 2 匹（バトル場とベンチ）。どちらも 10（1 匹に限らない）。にげる（エネルギー 1）
        state = board(mon(H.RATTATA), opponent=forretress(), opponent_bench=(forretress(),))
        after = retreat(state, 0)
        while after.decision is not None and after.decision.kind == REACTION_ORDER:
            after = answer(after, (after.decision.options[0],))
        self.assertEqual(after.players[0].active.damage, 20)
        audited(self, after)

    def test_asleep_source_does_not_work(self):
        state = board(mon(H.RATTATA), opponent=dict(forretress(), sleep=True))
        after = retreat(state, 0)
        self.assertEqual(new_events(state, after, "spikes_damage"), [])

    def test_failed_confused_retreat_does_not_trigger(self):
        state = board(mon(H.RATTATA, confusion=True), opponent=forretress())
        after = with_coin_results(state, TL)
        after = retreat(after, 0)
        self.assertIn("retreat_failed", kinds(state, after))
        self.assertEqual(new_events(state, after, "spikes_damage"), [])

    def test_promotion_after_knock_out_on_own_turn(self):
        # 自分の番（0）のワザのあとの相手（1）のバトル場に出す決定は、1 の番ではないのではたらかない。0 のフォレトスの相手は 1
        state = board(mon(H.HITMONCHAN, (FT, FT, FT)), opponent=mon(H.RATTATA), opponent_bench=(forretress(player=1),))
        after = attack(state, 1)
        while after.decision is not None:
            after = answer(after, (after.decision.options[0],))
        self.assertEqual(new_events(state, after, "spikes_damage"), [])


class MagmaPoolTest(unittest.TestCase):
    def test_retreat_moves_one_fire_card(self):
        state = board(magcargo((F, F, F, F)), bench=(H.CHARMANDER,))
        after = retreat(state, 3)
        events = new_events(state, after, "magma_pool")
        self.assertEqual(len(events), 1)
        self.assertEqual(len(after.players[0].active.energy), 1)
        self.assertEqual(after.energy_attachments_this_turn, state.energy_attachments_this_turn)
        audited(self, after)

    def test_several_cards_ask_and_answer_is_validated(self):
        state = board(magcargo((F, F, F, F, F)), bench=(H.CHARMANDER,))
        after = retreat(state, 3)
        self.assertEqual(after.decision.kind, MAGMA_POOL_ENERGY)
        self.assertEqual(len(after.decision.options), 2)
        before = snapshot(after)
        with self.assertRaises(IllegalActionError):
            apply_kernel(after, ResolveDecision(0, after.decision.id, (999,)))
        self.assertEqual(snapshot(after), before)
        # 決定待ちの状態の複製・pickle で同じ続きになる
        for clone in (copy.deepcopy(after), pickle.loads(pickle.dumps(after))):
            done = answer(clone, (clone.decision.options[0],))
            self.assertEqual(state_to_dict(done, format_version=22), state_to_dict(answer(after, (after.decision.options[0],)), format_version=22))
        audited(self, answer(after, (after.decision.options[0],)))

    def test_no_fire_card_left(self):
        state = board(magcargo((F, F, F)), bench=(H.CHARMANDER,))
        after = retreat(state, 3)
        self.assertEqual([e["kind"] for e in new_events(state, after, "magma_pool_none")], ["magma_pool_none"])

    def test_switch_moves_and_spikes_on_the_new_active(self):
        # 相手の番（1）に 1 のマグカルゴがポケモンいれかえでベンチへ。0 のフォレトスの［まきびし］は新しい対戦ポケモンに 10。同じ時点（番のプレイヤーが順番を決める）
        state = board(forretress(player=0), opponent=magcargo((F, F), player=1), opponent_bench=(H.CHARMANDER,), opponent_hand=(H.SWITCH,), current=1, turn=8)
        after = play(state, H.SWITCH, player=1)
        if after.decision is not None and after.decision.kind != REACTION_ORDER:
            after = answer(after, (after.decision.options[0],))
        seen = []
        while after.decision is not None:
            seen.append(after.decision.kind)
            after = answer(after, (after.decision.options[0],))
        self.assertEqual(seen, [REACTION_ORDER, MAGMA_POOL_ENERGY])  # 同じ時点の順番（番のプレイヤー 1）→ つけ替える「炎」のカード（2 枚から）
        self.assertEqual(len(new_events(state, after, "spikes_damage")), 1)
        self.assertEqual(len(new_events(state, after, "magma_pool")), 1)
        self.assertEqual(len(new_events(state, after, "discard_trainer")), 1)  # トレーナーは 1 度だけ使い終える
        audited(self, after)


class HotPlateTest(unittest.TestCase):
    def test_face_down_secret_plan_is_hp1(self):
        """HP1: マチスの秘策でうらにしてベンチに出すことが「手札から出すたび」に当たるかは決まらないので、［ヒートプレート］がはたらいているときは、出すカードを選ぶ答えを
        受け付けない（状態を変えない）。出さない答え（0 枚）はいつも受け付ける。［ヒートプレート］がなければ同じ答えを受け付ける（docs/movement-damage-reactions-v0.87.md 9 章）。"""
        state = board(mon(H.RATTATA), hand=(H.LT_SURGES_SECRET_PLAN, H.SPEAROW), opponent=dark_magcargo())
        asked = play(state, H.LT_SURGES_SECRET_PLAN)
        self.assertEqual(asked.decision.kind, "secret_plan_card")
        rejects(self, asked, ResolveDecision(0, asked.decision.id, (asked.decision.options[0],)), E.HOT_PLATE_FACE_DOWN_CODE)
        audited(self, answer(asked, ()))
        plain = board(mon(H.RATTATA), hand=(H.LT_SURGES_SECRET_PLAN, H.SPEAROW), opponent=mon(H.RATTATA))
        asked = play(plain, H.LT_SURGES_SECRET_PLAN)
        audited(self, answer(asked, (asked.decision.options[0],)))

    def test_both_players_hand_play(self):
        state = board(mon(H.RATTATA), hand=(H.RATTATA,), opponent=dark_magcargo())
        after = apply_kernel(state, PlayBasicToBench(0, uid(state, H.RATTATA)))
        self.assertEqual(len(new_events(state, after, "hot_plate_damage")), 1)
        self.assertEqual(after.players[0].bench[-1].damage, 10)
        audited(self, after)
        own = board(dark_magcargo(player=0), hand=(H.RATTATA,))
        own_after = apply_kernel(own, PlayBasicToBench(0, uid(own, H.RATTATA)))
        self.assertEqual(own_after.players[0].bench[-1].damage, 10)  # 自分の手札から出したたねポケモンにも（「おたがい」）

    def test_asleep_source_and_evolution_and_deck(self):
        asleep = board(mon(H.RATTATA), hand=(H.RATTATA,), opponent=dict(dark_magcargo(), sleep=True))
        after = apply_kernel(asleep, PlayBasicToBench(0, uid(asleep, H.RATTATA)))
        self.assertEqual(new_events(asleep, after, "hot_plate_damage"), [])
        # 進化は手札からたねポケモンを出すことではない
        evo = board(mon(H.PINECO_NEO4, played_turn=1), hand=(H.FORRETRESS_NEO2,), opponent=dark_magcargo())
        after = apply_kernel(evo, EvolvePokemon(0, uid(evo, H.FORRETRESS_NEO2), evo.players[0].active.pokemon_id))
        self.assertEqual(new_events(evo, after, "hot_plate_damage"), [])

    def test_magnet_from_deck_is_not_from_hand(self):
        state = with_coin_results(board(mon(H.MAGNEMITE_ES2), deck=[H.MAGNEMITE_ES2, W, W], opponent=dark_magcargo()), HD)
        after = apply_kernel(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        after = answer(after, (after.decision.options[0],))
        self.assertEqual(len(new_events(state, after, "bench_from_deck")), 1)
        self.assertEqual(new_events(state, after, "hot_plate_damage"), [])
        audited(self, after)

    def test_minefield_and_heat_plate_knock_out_hp30(self):
        """ヒートプレートの 10 と爆発ジムの 20（「うら」）は同じ時点の反応で、番のプレイヤーが順番を決める。HP 30 のディグダはどちらの順でも最後のダメージできぜつし、
        先の反応で HP 以上にならないので、どちらの順番でも続けられる（RA1 に当たらない）。"""
        for order in (0, 1):
            state = board(mon(H.RATTATA), hand=(H.DIGLETT, H.ROCKETS_MINEFIELD_GYM), opponent=dark_magcargo())
            state = play(state, H.ROCKETS_MINEFIELD_GYM)
            after = apply_kernel(with_coin_results(state, TL), PlayBasicToBench(0, uid(state, H.DIGLETT)))
            self.assertEqual(after.decision.kind, REACTION_ORDER)
            after = answer(after, (after.decision.options[order],))
            while after.decision is not None:
                after = answer(after, (after.decision.options[0],))
            knocked = new_events(state, after, "knock_out")
            self.assertEqual(len(knocked), 1)
            self.assertEqual(len(after.players[0].bench), 1)
            audited(self, after)

    def test_minefield_alone_keeps_the_v0_86_path(self):
        state = board(mon(H.RATTATA), hand=(H.DIGLETT, H.ROCKETS_MINEFIELD_GYM))
        state = play(state, H.ROCKETS_MINEFIELD_GYM)
        after = apply_kernel(with_coin_results(state, TL), PlayBasicToBench(0, uid(state, H.DIGLETT)))
        self.assertEqual(new_events(state, after, "hot_plate_damage"), [])
        self.assertEqual(after.decision, None)
        audited(self, after)


# ---------------------------------------------------------------- 5 章: 被ダメージの反応


class ShockBlastTest(unittest.TestCase):
    def test_tails_both_actives_and_heads_nothing(self):
        state = board(mon(H.SNORLAX, (DCE, DCE)), opponent=electrode())
        tails = attack(state, 0, (TL,))
        damages = new_events(state, tails, "shock_blast_damage")
        self.assertEqual([e["target_player"] for e in damages], [0, 1])
        self.assertEqual([e["amount"] for e in damages], [20, 20])
        audited(self, tails)
        heads = attack(state, 0, (HD,))
        self.assertEqual(new_events(state, heads, "shock_blast_damage"), [])

    def test_works_while_asleep_and_not_on_bench(self):
        asleep = board(mon(H.SNORLAX, (DCE, DCE)), opponent=dict(electrode(), sleep=True))
        self.assertEqual(len(new_events(asleep, attack(asleep, 0, (TL,)), "shock_blast_check")), 1)
        bench = board(dugtrio((FT, FT, FT)), opponent=mon(H.SNORLAX), opponent_bench=(electrode(), H.RATTATA))
        after = attack(bench, 0)
        after = answer(after, tuple(after.decision.options[:2]))
        self.assertEqual(new_events(bench, after, "shock_blast_check"), [])

    def test_sb1_damage_prevented_receiver_stops_before_the_coin(self):
        """SB1: 「ダメージを受けない」状態（かたまる）のマチスのマルマインが、受けるポケモン自身の効果を計算しないダメージ（ヒノアラシの「スピードスター」。v0.60）を受けた
        ［ショックボム］で、自分が 20 を受けるかは決まらないので、コインの前に止める（状態・乱数・ログを変えない）。「ダメージを受けない」状態でなければ進む。"""
        prevented = board(mon(H.CYNDAQUIL_PF1, (F, W)), opponent=dict(electrode(), prevent_damage=TURN - 1))
        rejects(self, prevented, UseAttack(0, 1), "UNRESOLVED_POWER_DAMAGE_PREVENTED")
        state = board(mon(H.CYNDAQUIL_PF1, (F, W)), opponent=electrode())
        self.assertEqual(len(new_events(state, attack(state, 1, (TL,)), "shock_blast_damage")), 2)

    def test_z9_only_when_the_reading_matters(self):
        # 闘に弱い相手（弱点 雷）: ヒトデマン（弱点 雷）がダメージを与えれば Z9。弱点・抵抗力が雷でないラッタなら進む
        state = board(mon(H.STARYU, (W,)), opponent=electrode())
        rejects(self, state, UseAttack(0, 0), Z9)
        other = board(mon(H.RATTATA, (DCE,)), opponent=electrode())
        self.assertEqual(attack(other, 0, (TL,)).phase.value != "halted", True)


class PoisonFluidTest(unittest.TestCase):
    def test_poisons_the_attacker_even_if_knocked_out(self):
        state = board(mon(H.SNORLAX, (DCE, DCE)), opponent=kakuna())
        after = attack(state, 0)
        self.assertEqual(len(new_events(state, after, "poison_fluid")), 1)
        audited(self, after)

    def test_already_asleep_does_not_work_and_bench_works(self):
        asleep = board(mon(H.SNORLAX, (DCE, DCE)), opponent=dict(kakuna(), sleep=True))
        self.assertEqual(new_events(asleep, attack(asleep, 0), "poison_fluid"), [])
        bench = board(dugtrio((FT, FT, FT)), opponent=mon(H.SNORLAX), opponent_bench=(kakuna(), H.RATTATA))
        after = attack(bench, 0)
        after = answer(after, tuple(after.decision.options[:2]))
        self.assertEqual(len(new_events(bench, after, "poison_fluid")), 1)
        audited(self, after)


class SplitTest(unittest.TestCase):
    def test_optional_use_and_decline(self):
        state = board(mon(H.RATTATA, (DCE,)), opponent=mon(H.KOFFING_ES2), opponent_deck=[H.KOFFING_ES2, W, W])
        asked = attack(state, 0)
        self.assertEqual((asked.decision.kind, asked.decision.player, asked.decision.max_choices), (SPLIT_FROM_DECK, 1, 1))
        used = answer(asked, (asked.decision.options[0],))
        self.assertEqual(len(used.players[1].bench), 2)
        self.assertIn("shuffle", kinds(asked, used))
        audited(self, used)
        declined = answer(asked, ())
        self.assertEqual(len(declined.players[1].bench), 1)
        self.assertNotIn("shuffle", kinds(asked, declined))

    def test_no_candidate_still_asks_and_full_bench_skips(self):
        state = board(mon(H.RATTATA, (DCE,)), opponent=mon(H.KOFFING_ES2), opponent_deck=[W, W, W])
        asked = attack(state, 0)
        self.assertEqual((asked.decision.kind, asked.decision.options, asked.decision.max_choices), (SPLIT_FROM_DECK, (), 0))
        # 相手には、選べるものの数を見せない
        self.assertNotIn("options", observe(asked, 0)["decision"])
        full = board(mon(H.RATTATA, (DCE,)), opponent=mon(H.KOFFING_ES2), opponent_bench=(H.RATTATA,) * 5, opponent_deck=[H.KOFFING_ES2])
        after = attack(full, 0)
        self.assertEqual([e["reason"] for e in new_events(full, after, "split_skipped")], ["bench_full"])

    def test_effect_after_damage_reads_the_carried_damage_result(self):
        """［ぶんれつ］の決定（要素のあいだの決定）のあとの「ダメージを与えたあと」の効果（R団のカビゴンの「たおれこむ」）は、決定の前のダメージの結果を続きの
        情報（``damage_results``）で運んで読む（v0.87 の対戦の検証で見つけた内部エラー。``KeyError: 'damage'``）。"""
        state = board(mon(H.ROCKETS_SNORLAX, (DCE, W)), opponent=mon(H.KOFFING_ES2), opponent_deck=[H.KOFFING_ES2, W, W])
        asked = attack(state, 0)
        self.assertEqual(asked.decision.kind, SPLIT_FROM_DECK)
        self.assertIn("damage_results", dict(asked.decision.context))
        for choices in ((asked.decision.options[0],), ()):
            after = answer(asked, choices)
            slept = [e for e in new_events(asked, after, "special_condition") if e["pokemon_id"] == state.players[0].active.pokemon_id]
            self.assertEqual([e["condition"] for e in slept], ["sleep"])
            audited(self, after)


# ---------------------------------------------------------------- 6 章: コイルとゲンガー


class MagnetTest(unittest.TestCase):
    def test_heads_tails_and_once_per_turn(self):
        state = board(mon(H.MAGNEMITE_ES2), deck=[H.MAGNEMITE_ES2, H.LT_SURGES_MAGNEMITE_30, W])
        heads = apply_kernel(with_coin_results(state, HD), UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        self.assertEqual(len(heads.decision.options), 1)  # 「マチスのコイル」は別の名前
        heads = answer(heads, (heads.decision.options[0],))
        rejects(self, heads, UsePokemonPower(0, heads.players[0].active.pokemon_id, 0), "POWER_ALREADY_USED", IllegalActionError)
        tails = apply_kernel(with_coin_results(state, TL), UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        self.assertEqual(tails.decision, None)
        audited(self, heads)

    def test_full_bench_and_asleep_reject(self):
        full = board(mon(H.MAGNEMITE_ES2), bench=(H.RATTATA,) * 5, deck=[H.MAGNEMITE_ES2])
        rejects(self, full, UsePokemonPower(0, full.players[0].active.pokemon_id, 0), "BENCH_FULL", IllegalActionError)
        asleep = board(mon(H.MAGNEMITE_ES2, sleep=True), deck=[H.MAGNEMITE_ES2])
        with self.assertRaises(IllegalActionError):
            apply_kernel(asleep, UsePokemonPower(0, asleep.players[0].active.pokemon_id, 0))


class DarkPowerTest(unittest.TestCase):
    def test_breeder_returns_the_opponents_pokemon_to_hand(self):
        state = board(mon(H.GASTLY), hand=(H.GENGAR_PR1, H.POKEMON_BREEDER), opponent=mon(H.SNORLAX, (W,)), opponent_bench=(H.RATTATA,))
        after = play(state, H.POKEMON_BREEDER)
        after = answer(after, (after.decision.options[0],))
        after = answer(after, (after.decision.options[0],))
        self.assertEqual(after.decision.kind, "entry_power")
        after = answer(with_coin_results(after, HD), (after.decision.options[0],))
        active = after.players[1].active.pokemon_id
        after = answer(after, (active,))
        # 相手のバトル場が空いたので、相手がバトル場に出す（ポケモン育て屋さんは、そのあとに 1 度だけ使い終える）
        self.assertEqual((after.decision.kind, after.decision.player), ("promote_active", 1))
        self.assertIn(uid(state, H.SNORLAX, 1, "deck") if False else state.players[1].active.card, after.players[1].hand)
        after = answer(after, (after.decision.options[0],))
        self.assertEqual(len(new_events(state, after, "knock_out")), 0)
        self.assertEqual(len(new_events(state, after, "discard_trainer")), 1)
        self.assertEqual(after.decision, None)
        audited(self, after)


# ---------------------------------------------------------------- 7 章: 保護と禁止


class AuroraVeilTest(unittest.TestCase):
    def test_own_and_opponent_bench(self):
        state = board(dugtrio((FT, FT, FT)), opponent=mon(H.ARTICUNO_ES2), opponent_bench=(H.RATTATA, H.RATTATA))
        after = attack(state, 0)
        after = answer(after, tuple(after.decision.options[:2]))
        self.assertEqual([p.damage for p in after.players[1].bench], [0, 0])
        self.assertEqual(len(new_events(state, after, "damage")), 1)  # 発生源自身への対戦ポケモンのダメージは守らない（抵抗力 闘で 0 でも、ダメージの要素は計算する）
        audited(self, after)

    def test_asleep_source_stops(self):
        state = board(dugtrio((FT, FT, FT)), opponent=dict(mon(H.ARTICUNO_ES2), sleep=True), opponent_bench=(H.RATTATA, H.RATTATA))
        after = attack(state, 0)
        after = answer(after, tuple(after.decision.options[:2]))
        self.assertEqual([p.damage for p in after.players[1].bench], [10, 10])


class DigUnderTest(unittest.TestCase):
    def test_bench_dugtrio_takes_no_attack_damage(self):
        state = board(dugtrio((FT, FT, FT)), opponent=mon(H.SNORLAX), opponent_bench=(dugtrio(player=1), H.RATTATA))
        after = attack(state, 0)
        after = answer(after, tuple(after.decision.options[:2]))
        self.assertEqual([p.damage for p in after.players[1].bench], [0, 10])
        audited(self, after)


class GuardTest(unittest.TestCase):
    def test_retreat_rejected_before_discard_and_switch_allowed(self):
        state = board(mon(H.RATTATA), opponent=mon(H.SNORLAX_ES1), hand=(H.SWITCH,))
        rejects(self, state, Retreat(0, tuple(state.players[0].active.energy), state.players[0].bench[0].card), "RETREAT_PREVENTED", IllegalActionError)
        after = play(state, H.SWITCH)
        if after.decision is not None:
            after = answer(after, (after.decision.options[0],))
        self.assertIn("switch", kinds(state, after))

    def test_asleep_guard_does_not_stop(self):
        state = board(mon(H.RATTATA), opponent=dict(mon(H.SNORLAX_ES1), sleep=True))
        self.assertIn("retreat", kinds(state, retreat(state, 0)))


# ---------------------------------------------------------------- 8 章: ワザ


class AttackTest(unittest.TestCase):
    def test_rapid_spin_both_switch_with_spikes(self):
        state = board(forretress((METAL, W, W), player=0), opponent=forretress(), opponent_bench=(H.RATTATA,))
        after = attack(state, 0)
        order = []
        while after.decision is not None:
            order.append((after.decision.kind, after.decision.player))
            after = answer(after, (after.decision.options[0],))
        self.assertEqual(order, [("forced_switch", 1), ("select_pokemon", 0)])
        self.assertEqual(len(new_events(state, after, "spikes_damage")), 1)  # 自分の入れ替えは、相手の［まきびし］（今の番は 0 の番）
        audited(self, after)

    def test_rapid_spin_while_shock_blast_knocked_out_its_holder(self):
        """［ショックボム］の「うら」で持つポケモン自身（マチスのマルマイン）が HP 以上になったあと、こうそくスピンの自分の入れ替えの決定を待つ間、そのポケモンは場に
        残り、ワザの要素をすべて処理したあとにきぜつする（v0.87 の対戦の検証で見つけた不変条件の違反。``engine._attack_damage_awaiting``）。"""
        state = board(forretress((METAL, W, W), player=0), opponent=dict(electrode(), damage=30))
        waiting = attack(state, 0, (TL,))
        self.assertEqual((waiting.decision.kind, waiting.decision.player), ("select_pokemon", 0))
        self.assertGreaterEqual(waiting.players[1].active.damage, 80)
        self.assertEqual([e["reason"] for e in new_events(state, waiting, "forced_switch_skipped")], ["knocked_out"])
        after = answer(waiting, (waiting.decision.options[0],))
        self.assertEqual(len([e for e in new_events(waiting, after, "knock_out") if e["player"] == 1]), 1)
        audited(self, after)

    def test_rapid_spin_spikes_knock_out_then_promotion_spikes_again(self):
        """こうそくスピンの自分の入れ替えで出たダメージ 20 のラッタが［まきびし］できぜつ → 相手がサイドを取る → 自分がバトル場に出す（控えから出るので、もう一度［まきびし］）→
        ワザのあとの番の終わり。トレーナー・ワザの残りを二重に処理しない。"""
        state = board(forretress((METAL, W, W), player=0), bench=(mon(H.RATTATA, damage=20), H.RATTATA), opponent=forretress(), opponent_bench=(H.RATTATA,))
        after = attack(state, 0)
        seen = []
        while after.decision is not None:
            seen.append((after.decision.kind, after.decision.player))
            after = answer(after, (after.decision.options[0],))
        self.assertEqual(seen, [("forced_switch", 1), ("select_pokemon", 0), ("take_prize", 1), ("promote_active", 0)])
        self.assertEqual(kinds(state, after).count("spikes_damage"), 2)
        self.assertEqual(kinds(state, after).count("turn_end"), 1)
        self.assertEqual(after.current_player, 1)
        audited(self, after)

    def test_strange_gas_stops_only_the_opponents_side(self):
        state = board(mon(H.KOFFING_ES2, (G, G)), opponent=mon(H.SNORLAX))
        after = attack(state, 0, (HD,))
        records = [r for r in after.trainer_effects if r.kind == OPPONENT_POWER_SUPPRESSION]
        self.assertEqual(len(records), 1)
        snorlax_power = after.players[1].active
        self.assertTrue(power_suppressed(after, load_card_pool().get(H.SNORLAX).powers[0], snorlax_power))
        self.assertFalse(power_suppressed(after, load_card_pool().get(H.KOFFING_ES2).powers[0], after.players[0].active))
        audited(self, after)

    def test_strange_gas_protected_pokemon_is_mg2(self):
        """MG2: 相手の場にワザの効果を受けないポケモン（［オーロラヴェール］で守られた控え）がいれば、その特殊能力もふしぎなガスで止まるかが決まらないので、コインの前に止める。"""
        protected = board(mon(H.KOFFING_ES2, (G, G)), opponent=mon(H.ARTICUNO_ES2), opponent_bench=(H.RATTATA,))
        rejects(self, protected, UseAttack(0, 0), E.STRANGE_GAS_PROTECTED_CODE)
        asleep = board(mon(H.KOFFING_ES2, (G, G)), opponent=mon(H.ARTICUNO_ES2, sleep=True), opponent_bench=(H.RATTATA,))
        audited(self, attack(asleep, 0, (HD,)))  # ねむりのフリーザーの［オーロラヴェール］ははたらかない

    def test_strange_gas_new_pokemon_with_power_stops(self):
        state = board(mon(H.KOFFING_ES2, (G, G)), opponent=mon(H.SNORLAX), opponent_hand=(H.MAGNEMITE_ES2, H.RATTATA))
        after = attack(state, 0, (HD,))
        rejects(self, after, PlayBasicToBench(1, uid(after, H.MAGNEMITE_ES2, 1)), E.STRANGE_GAS_SCOPE_CODE)
        ok = apply_kernel(after, PlayBasicToBench(1, uid(after, H.RATTATA, 1)))  # 特殊能力のないポケモンは出せる
        audited(self, ok)

    def test_lazy_sleep_and_psychic_horror(self):
        # 番の終わりのポケモンチェックでねむりのコインを投げるので、与えた特殊状態はログで確かめる（ねころぶ: 自分 → コインの「おもて」なら相手）
        def given(before, after):
            return [(e["player"], e["condition"]) for e in new_events(before, after, "special_condition")]

        state = board(mon(H.SNORLAX_ES1, (DCE, DCE)), opponent=mon(H.HITMONCHAN))
        self.assertEqual(given(state, attack(state, 0, (HD,))), [(0, "sleep"), (1, "sleep")])
        self.assertEqual(given(state, attack(state, 0, (TL,))), [(0, "sleep")])
        horror = board(mon(H.GENGAR_PR1, (P, P, P), evolved_from=[H.GASTLY, H.HAUNTER], played_turn=1, evolved_turn=5), opponent=mon(H.HITMONCHAN))
        self.assertEqual(given(horror, attack(horror, 0, (HD,))), [(1, "sleep")])
        self.assertEqual(given(horror, attack(horror, 0, (TL,))), [(1, "confusion")])

    def test_power_up_ball_heads_count(self):
        for heads in range(4):
            state = board(electrode((L, L, W), player=0), opponent=mon(H.SNORLAX))
            after = attack(state, 0, (HD,) * heads + (TL,) * (3 - heads))
            self.assertEqual(after.players[1].active.damage, 30 + 10 * heads)

    def test_lava_flow_any_number(self):
        for count in (0, 1, 2):
            state = board(magcargo((F, F, F, F, F, F)), opponent=mon(H.SNORLAX))
            after = attack(state, 0)
            fires = tuple(after.players[0].active.energy[:count])
            after = answer(after, fires)
            self.assertEqual(after.players[1].active.damage, 40 + 20 * count)


class DocumentTest(unittest.TestCase):
    def test_document_exists_and_mentions_the_cards(self):
        text = DOC.read_text(encoding="utf-8")
        for card_id in H.V0_87_POKEMON:
            self.assertIn(card_id, text)


if __name__ == "__main__":
    unittest.main()
