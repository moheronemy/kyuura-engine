"""v0.46: 常にはたらく特殊能力を持つポケモン 8 枚と関連する 3 枚（docs/continuous-powers-v0.46.md）。

常にはたらく特殊能力（どれも宣言しない）: バリヤード（PMCG2-027）の［なぞのかべ］・エリカのミニリュウ（PMCG5-063）の［ふしぎなバリアー］・エリカのフシギソウ（PMCG6-010）の
［くつろぐかおり］・わるいオコリザル（PMCG4-041）の［きょうぼう］・ドードリオ（PMCG2-040）の［にげるサポート］・わるいベトベトン（PMCG4-007）の［ねんちゃくえき］・
わるいラフレシア（PMCG4-010）の［アレルギーかふん］・カビゴン（PMCG2-047）の［めんえき］。関連する 3 枚: エリカのフシギバナ（PMCG6-017。せいちょう・かくさん
ソーラービーム）・エリカのタマタマ（PMCG5-012。リフレクター・タマゴばくだん）・エリカのナッシー（PMCG5-013。サイコエクスチェンジ・ふみつけ）。どれも kyuura データの
採用（処理に使う文面は kyuura の印刷の文面。採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合。ガイドブックは読んでいない。

根拠にした既存の記録: GR-2000-P321-DAMAGE-ORDER（p.321 のダメージの計算の段階。2 段階はワザを使うポケモンの効果、6 段階はそれ以外（控えポケモンの特殊能力など）、
8 段階はワザを受けるポケモンの効果。8 段階の例が「かたくなる」「なぞのかべ」）・GR-2000-P321-ATTACK-DAMAGE（返す効果のダメージはワザによるダメージ）・
GR-2000-P319-HP-AND-DAMAGE・GR-2000-P320-COUNTER-MOVE・GR-2000-P309-ATTACK-PROCEDURE・p.311（「にげる」・特殊能力の宣言）・p.322（特殊状態）と、エンジンの
v0.3c（こんらんの 20 の読み方）・v0.4d（メガドレインの「半分（切り上げ）」はダメージカウンターの単位）・v0.8（かがくへんかガス）・v0.10（はんげき）・
v0.12/v0.13（返す効果）・v0.17b（わるいねぞう）・v0.31（HC7）・v0.34（なきつく）・v0.35（計算の順番の決定）・v0.44（FC1）・v0.45（かたくなる）の記録。

新しい停止コードは 2 つ: CP1（``UNRESOLVED_CALMING_AROMA_RETALIATION``）・CP2（``UNRESOLVED_RETREAT_COST_FLOOR``）。
"""

from __future__ import annotations

import copy
import dataclasses
import pathlib
import pickle
import re
import unittest
from types import MappingProxyType

from kyuura_engine import (
    EngineError,
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, pool_from_extract, read_extract
from kyuura_engine.damage import HALVE_DOWN, HALVE_UP, SET_IF_AT_LEAST, ZERO_IF_AT_LEAST, DamageModifier, calculate_attack_damage
from kyuura_engine.decisions import ATTACH_FROM_HAND, DAMAGE_STEP_ORDER, SELECT_ATTACK, SELECT_POKEMON
from kyuura_engine.resolution import PREFLIGHT_MODES, contract, programs, v013_checks
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.rules import RULES_2000_02_14
from kyuura_engine.state import Asleep, HalvedDamage
from scripts import check_card_sources as cs
from tests.helpers import (
    ATTACK_TYPES_SINCE_V0_17,
    CLEFAIRY,
    CUBONE,
    DARK_GLOOM,
    DARK_MUK,
    DARK_PRIMEAPE,
    DARK_VILEPLUME,
    DARK_WARTORTLE,
    DEFENDER,
    DODRIO,
    DODUO,
    ERIKAS_BULBASAUR,
    ERIKAS_DRATINI,
    ERIKAS_EXEGGCUTE,
    ERIKAS_EXEGGUTOR,
    ERIKAS_IVYSAUR,
    ERIKAS_VENUSAUR,
    FIGHTING,
    FIRE,
    GRASS,
    GRIMER,
    HITMONCHAN,
    MACHOP,
    MANKEY,
    MR_MIME,
    MUK,
    NIDOKING,
    NIDORAN_M,
    NIDORINO,
    PLUSPOWER,
    POKEMON_BREEDER,
    POTION,
    PSYCHIC,
    RATICATE,
    RATTATA,
    ROCKET_ODDISH,
    ROCKET_SQUIRTLE,
    ROCKETS_MOLTRES,
    ROCKETS_SNORLAX,
    SNORLAX,
    SWITCH,
    V0_46_POKEMON,
    V0_46_POWER_POKEMON,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "continuous-powers-v0.46.md"
TURN = 7
F, W, G, P, R = FIGHTING, WATER, GRASS, PSYCHIC, FIRE
CP1 = "UNRESOLVED_CALMING_AROMA_RETALIATION"
CP2 = "UNRESOLVED_RETREAT_COST_FLOOR"
FC1 = "UNRESOLVED_STATED_CARDS_SHORT"
HC7 = "UNRESOLVED_ATTACH_FROM_DISCARD_ZERO"
Z23 = "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE"
CONFUSION_MODIFIERS = "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS"

# 登録の実装の型と値
ATTACKS = {
    (MR_MIME, 0): (E.DamagePlusDefenderCounters, {"per": 10, "scope_ambiguous": False}),
    (ERIKAS_DRATINI, 0): (E.CoinBonusDamage, {"bonus": 20}),
    (ERIKAS_IVYSAUR, 0): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 40}),
    (DARK_PRIMEAPE, 0): (E.DamageThenSelfConfuse, {}),
    (DODRIO, 0): (E.DamagePlusOwnCounters, {"per": 10}),
    (DARK_MUK, 0): (E.PoisonOpponent, {}),
    (DARK_VILEPLUME, 0): (E.CoinsTimesDamageSelfConfuse, {"coins": 3, "per": 30, "at_least": 2}),
    (SNORLAX, 0): (E.ParalyzeOnHeads, {}),
    (ERIKAS_VENUSAUR, 0): (E.AttachEnergyFromHandOnHeads, {"energy_type": EnergyType.GRASS, "max_cards": 2}),
    (ERIKAS_VENUSAUR, 1): (E.DamageThenExactBenchTargets, {"targets": 2, "bench_damage": 20}),
    (ERIKAS_EXEGGCUTE, 0): (E.HalveDamageNextTurn, {}),
    (ERIKAS_EXEGGCUTE, 1): (E.SelfDamageInsteadOnTails, {"self_damage": 20}),
    (ERIKAS_EXEGGUTOR, 0): (E.ShuffleHandIntoDeckThenDraw, {"count": 5}),
    (ERIKAS_EXEGGUTOR, 1): (E.CoinBonusDamage, {"bonus": 10}),
}
POWERS = {
    MR_MIME: E.ZeroLargeDamageReceived(30),
    ERIKAS_DRATINI: E.CapDamageFromBasic(20, 10),
    ERIKAS_IVYSAUR: E.HalveActiveAttackDamage(),
    DARK_PRIMEAPE: E.BonusDamageWhileConfused(30),
    DODRIO: E.ReduceOwnActiveRetreatCost(1),
    DARK_MUK: E.IncreaseOpponentActiveRetreatCost(2),
    DARK_VILEPLUME: E.PreventTrainerUse(),
    SNORLAX: E.SpecialConditionImmunity(),
}
# v0.46 で加えたワザの型（tests/helpers.py の ATTACK_TYPES_SINCE_V0_17 の最後の 6）
NEW_TYPES = (E.DamageThenSelfConfuse, E.CoinsTimesDamageSelfConfuse, E.AttachEnergyFromHandOnHeads, E.DamageThenExactBenchTargets,
             E.HalveDamageNextTurn, E.ShuffleHandIntoDeckThenDraw)
# pcg-search.com の対象の版（サイトの一覧の番号）
EDITIONS = {MR_MIME: "027/048", ERIKAS_DRATINI: "065/096", ERIKAS_IVYSAUR: "001/098", DARK_PRIMEAPE: "041/065", DODRIO: "042/048",
            DARK_MUK: "009/065", DARK_VILEPLUME: "007/065", SNORLAX: "047/048", ERIKAS_VENUSAUR: "002/098", ERIKAS_EXEGGCUTE: "014/096",
            ERIKAS_EXEGGUTOR: "015/096"}
# 進化しているポケモンの下のカード（build_test_state の "evolved_from"）
BELOW = {ERIKAS_IVYSAUR: ERIKAS_BULBASAUR, DARK_PRIMEAPE: MANKEY, DODRIO: DODUO, DARK_MUK: GRIMER, DARK_VILEPLUME: [ROCKET_ODDISH, DARK_GLOOM],
         ERIKAS_VENUSAUR: [ERIKAS_BULBASAUR, ERIKAS_IVYSAUR], ERIKAS_EXEGGUTOR: ERIKAS_EXEGGCUTE, RATICATE: RATTATA, DARK_WARTORTLE: ROCKET_SQUIRTLE,
         NIDOKING: [NIDORAN_M, NIDORINO], MUK: GRIMER}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def bench_spec(b):
    return mon(b) if isinstance(b, str) and b in BELOW else b


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), deck=None, hand=(), opponent_hand=(), turn=TURN):
    me = {"active": active, "bench": [bench_spec(b) for b in bench], "hand": list(hand)}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent or mon(HITMONCHAN, (F, F, F)), "bench": [bench_spec(b) for b in opponent_bench], "hand": list(opponent_hand)}
    return build_test_state([me, them], turn_number=turn)


def full(state):
    return state_to_dict(state, format_version=11)


def snapshot(state):
    return full(state), [dict(e) for e in state.log], repr(state.rng.getstate())


def audited(test, state):
    """不変条件と書き出しの監査（盤面を直接作ったテスト。ログの監査は正式な対戦のテストで確かめる）。"""
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    return state


def events(state, since, kind=None):
    return [dict(e) for e in state.log[since:] if kind is None or e["kind"] == kind]


def answer(state, choices, *, mode="derived"):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)), preflight=mode)


def attack(state, index, *sides, player=0, mode="derived"):
    return apply_kernel(with_coin_results(state, *sides) if sides else state, UseAttack(player, index), preflight=mode)


def damage_events(state, since):
    return [(e.get("target", "opponent"), e["amount"], [tuple(s) for s in e["steps"]]) for e in events(state, since, "damage")]


def assert_stops(test, state, command, code, *, exception=UnsupportedError):
    """どの先読みの方法でも ``code`` で拒否し、状態・乱数・ログが変わらない。"""
    before = snapshot(state)
    for mode in PREFLIGHT_MODES:
        with test.subTest(mode=mode), test.assertRaises(exception) as raised:
            apply_kernel(state, command, preflight=mode)
        test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def assert_rejected(test, state, command, code, exception=EngineError):
    before = snapshot(state)
    with test.assertRaises(exception) as raised:
        apply_kernel(state, command)
    test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def card_of(state, player, card, zone="hand", nth=0):
    return [u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card][nth]


def pid_of(state, player, card, nth=0):
    return [p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card][nth]


# ---------------------------------------------------------------- 登録・写し・記録


class CardDataTest(unittest.TestCase):
    """11 枚の写し・登録・記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_eleven_requested_cards(self):
        """写しの組 pool_v0_46 は依頼の 11 枚（並び）。どれも対応で、どのワザも、どの特殊能力も登録した（ワザだけの登録で特殊能力を持つカードを対応と数えない）。"""
        self.assertEqual(read_extract()["pool_v0_46"], list(V0_46_POKEMON))
        names = {MR_MIME: "バリヤード", ERIKAS_DRATINI: "エリカのミニリュウ", ERIKAS_IVYSAUR: "エリカのフシギソウ", DARK_PRIMEAPE: "わるいオコリザル",
                 DODRIO: "ドードリオ", DARK_MUK: "わるいベトベトン", DARK_VILEPLUME: "わるいラフレシア", SNORLAX: "カビゴン",
                 ERIKAS_VENUSAUR: "エリカのフシギバナ", ERIKAS_EXEGGCUTE: "エリカのタマタマ", ERIKAS_EXEGGUTOR: "エリカのナッシー"}
        for card in V0_46_POKEMON:
            with self.subTest(card=card):
                definition = self.pool.get(card)
                self.assertEqual(definition.name_ja, names[card])
                self.assertTrue(self.pool.is_playable(card))
                self.assertTrue(all(a.supported for a in definition.attacks))
                self.assertEqual(len(definition.powers), 1 if card in V0_46_POWER_POKEMON else 0)
        # 特殊能力の登録を除くと、ワザの登録があっても対応にならない（特殊能力を持つカードを一括で対応にしない）
        for card in V0_46_POWER_POKEMON:
            effects = E.DEFAULT_EFFECTS.without_powers(f"test-no-{card}", [E.PowerKey(card, 0)])
            with self.subTest(card=card):
                self.assertIsNone(effects.power_entry(card, 0))
                self.assertFalse(pool_from_extract(read_extract(), effects).is_playable(card))

    def test_evolution_names(self):
        """進化カードは「○○から進化」の名前の完全一致で進化元が決まり、進化元はどれも対応のカード（既存と今回）。"""
        expected = {ERIKAS_IVYSAUR: "エリカのフシギダネ", DARK_PRIMEAPE: "マンキー", DODRIO: "ドードー", DARK_MUK: "ベトベター",
                    DARK_VILEPLUME: "わるいクサイハナ", ERIKAS_VENUSAUR: "エリカのフシギソウ", ERIKAS_EXEGGUTOR: "エリカのタマタマ"}
        names = {self.pool.get(c).name_ja for c in self.pool.playable_ids if self.pool.get(c).category == "pokemon"}
        for card in V0_46_POKEMON:
            with self.subTest(card=card):
                definition = self.pool.get(card)
                self.assertEqual(definition.evolves_from, expected.get(card))
                self.assertEqual(definition.is_basic_pokemon, card not in expected)
                if card in expected:
                    self.assertIn(expected[card], names)
        # 似た名前の別のカード（ミニリュウ・オコリザル・ベトベトン・ラフレシア・R団のカビゴン）と取りちがえない
        for ours, other in ((ERIKAS_DRATINI, "PMCG1-065"), (DARK_PRIMEAPE, "PMCG2-031"), (DARK_MUK, MUK), (DARK_VILEPLUME, "PMCG2-014"),
                            (SNORLAX, ROCKETS_SNORLAX)):
            with self.subTest(pair=(ours, other)):
                self.assertNotEqual(self.pool.get(ours).name_ja, self.pool.get(other).name_ja)

    def test_every_attack_and_power_is_registered_with_the_expected_implementation(self):
        for card in V0_46_POKEMON:
            definition = self.pool.get(card)
            for index, attack_def in enumerate(definition.attacks):
                with self.subTest(card=card, index=index):
                    entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
                    kind, values = ATTACKS[(card, index)]
                    self.assertIs(type(entry.effect), kind)
                    self.assertEqual(entry.effect, kind(**values))
                    self.assertEqual((entry.name_ja, entry.text_ja), (attack_def.name_ja, attack_def.text_ja))
                    self.assertEqual(entry.effect.check(attack_def), [])
                    self.assertEqual((entry.play_text_ja, entry.source), (attack_def.text_ja, cs.PRINTED_TEXT_SOURCE))
            for index, power in enumerate(definition.powers):
                with self.subTest(card=card, power=index):
                    entry = E.DEFAULT_EFFECTS.power_entry(card, index)
                    self.assertEqual(entry.effect, POWERS[card])
                    self.assertIsInstance(entry.effect, E.ContinuousPower)
                    self.assertFalse(entry.effect.declared)
                    self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                                     (power.name_ja, power.text_ja, power.text_ja, cs.PRINTED_TEXT_SOURCE))
                    self.assertEqual(entry.effect.check(power), [])
        self.assertEqual(len([k for k in E.DEFAULT_EFFECTS.attack_keys() if k.card_id in V0_46_POKEMON]), len(ATTACKS))
        self.assertEqual(len([k for k in E.DEFAULT_EFFECTS.power_keys() if k.card_id in V0_46_POKEMON]), len(POWERS))

    def test_text_checks_reject_other_wording(self):
        """型の ``check`` は登録した文面と完全に同じものだけを受け付ける。1 文字変えた文面は拒否する（ワザ・特殊能力とも）。"""
        for (card, index), (kind, _) in ATTACKS.items():
            if kind not in NEW_TYPES:
                continue
            attack_def = self.pool.get(card).attacks[index]
            effect = E.DEFAULT_EFFECTS.attack_entry(card, index).effect
            with self.subTest(card=card, index=index):
                changed = dataclasses.replace(attack_def, text_ja=attack_def.text_ja + "あ")
                self.assertTrue(effect.check(changed))
        for card, effect in POWERS.items():
            power = self.pool.get(card).powers[0]
            with self.subTest(card=card):
                self.assertTrue(effect.check(dataclasses.replace(power, text_ja=power.text_ja + "あ")))
        # ヨガのポーズは「相手にのっている…」（バリヤード）と「相手のポケモンにのっている…」（ルージュラ。CD4）を書き方で分ける
        mime = self.pool.get(MR_MIME).attacks[0]
        self.assertEqual(E.DamagePlusDefenderCounters(10, scope_ambiguous=False).check(mime), [])
        self.assertTrue(E.DamagePlusDefenderCounters(10).check(mime))

    def test_new_types_are_kernel_programs_outside_the_v013_contract(self):
        """v0.46 の型は解決の基盤の要素の並びで処理し（v0.13 の約束のアダプタでない）、v0.13 の止める関数で確かめる型（VERIFIED）に入れない。"""
        start = ATTACK_TYPES_SINCE_V0_17.index(NEW_TYPES[0])  # v0.47 からは、このあとに v0.47 の型が続く
        self.assertEqual(ATTACK_TYPES_SINCE_V0_17[start:start + len(NEW_TYPES)], NEW_TYPES)
        for kind in NEW_TYPES:
            with self.subTest(kind=kind.__name__):
                self.assertNotIn(kind, v013_checks.VERIFIED)
                self.assertIn(kind, programs.BUILDERS)
                effect = next(E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect for k in E.DEFAULT_EFFECTS.attack_keys()
                              if type(E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect) is kind)
                self.assertFalse(contract.is_contract(contract.program_for(effect)))
                self.assertNotIn("resolve", vars(kind))

    def test_records_and_external_checks(self):
        """採用の記録は 11 枚（kyuura データ。写しの元のコミット）。照合は pcg-search.com の同じ版のページ（一覧の番号）で、違いは処理に影響しない。"""
        sources = cs.load_sources()
        self.assertEqual(cs.problems(), [])
        for card in V0_46_POKEMON:
            record = sources["cards"][card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"]), (cs.KYUURA_DATA, cs.ADOPTED))
                [check] = record["external_checks"]
                self.assertEqual((check["site"], check["edition"]["list_number"], check["checked_on"]), ("pcg-search.com", EDITIONS[card], "2026-10-17"))
                self.assertFalse(any(d["affects_behavior"] for d in check["differences"]))
                for key in ("page", "pdf_page", "latest_description_ja", "card_image_text_ja"):
                    self.assertNotIn(key, record)

    def test_no_card_specific_branch_in_the_engine(self):
        """engine.py・resolution/ にカード id での分岐を加えていない。"""
        sources = [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]
        for path in sources:
            text = path.read_text(encoding="utf-8")
            for card in V0_46_POKEMON:
                with self.subTest(path=path.name, card=card):
                    self.assertNotIn(card, text)

    def test_new_and_reused_questions(self):
        """新しい停止コードは CP1・CP2 の 2 つ。ほかは既存の問い・コード（こんらんの 20・HC7・FC1・Z23）。"""
        self.assertEqual((QUESTIONS["calming_retaliation"].code, QUESTIONS["calming_retaliation"].rulings), (CP1, ("CP1",)))
        self.assertEqual(QUESTIONS["stated_cards_short"].code, FC1)
        text = DOC.read_text(encoding="utf-8")
        for word in (CP1, CP2, "CP1", "CP2", *V0_46_POKEMON):
            self.assertIn(word, text)


# ---------------------------------------------------------------- ダメージの計算の操作（damage.py）


class DamageOperationTest(unittest.TestCase):
    """しきい値（以上なら 0・以上ならその数）と半分（切り上げ・切りすて。ダメージカウンターの単位）の計算。境界は 1 つ手前・ちょうど・1 つ先。"""

    def test_zero_if_at_least(self):
        m = DamageModifier(step=8, amount=30, label="w", source=0, operation=ZERO_IF_AT_LEAST)
        self.assertEqual([m.apply(v) for v in (0, 10, 20, 30, 40, 80)], [0, 10, 20, 0, 0, 0])

    def test_set_if_at_least(self):
        m = DamageModifier(step=8, amount=10, label="b", source=0, operation=SET_IF_AT_LEAST, threshold=20)
        self.assertEqual([m.apply(v) for v in (0, 10, 20, 30, 120)], [0, 10, 10, 10, 10])
        with self.assertRaises(ValueError):
            DamageModifier(step=8, amount=10, label="b", source=0, operation=SET_IF_AT_LEAST)

    def test_halve_rounding_in_counters(self):
        up = DamageModifier(step=8, amount=2, label="u", source=0, operation=HALVE_UP)
        down = DamageModifier(step=8, amount=2, label="d", source=0, operation=HALVE_DOWN)
        self.assertEqual([up.apply(v) for v in (0, 10, 20, 30, 40, 50, 70)], [0, 10, 10, 20, 20, 30, 40])
        self.assertEqual([down.apply(v) for v in (0, 10, 20, 30, 40, 50, 70)], [0, 0, 10, 10, 20, 20, 30])
        self.assertEqual(up.apply(-10), -10)  # 0 以下はそのまま（途中の段階で 0 以下になったら計算を終える）
        with self.assertRaises(ValueError):
            DamageModifier(step=8, amount=3, label="u", source=0, operation=HALVE_UP)

    def test_steps_are_the_ones_of_the_holder(self):
        """p.321 の段階の中の位置（受けるポケモンの効果は 8 段階）。ディフェンダー（7 段階）のあとで、しきい値と比べる。"""
        pool = load_card_pool()
        rattata, mime = pool.get(RATTATA), pool.get(MR_MIME)
        wall = DamageModifier(step=8, amount=30, label="w", source=0, operation=ZERO_IF_AT_LEAST)
        defender = DamageModifier(step=7, amount=-20, label="d", source=1)
        self.assertEqual(calculate_attack_damage(40, rattata, mime, RULES_2000_02_14, (wall,)).final, 0)
        self.assertEqual(calculate_attack_damage(40, rattata, mime, RULES_2000_02_14, (wall, defender)).final, 20)


# ---------------------------------------------------------------- なぞのかべ・ふしぎなバリアー


class MysteriousWallTest(unittest.TestCase):
    """バリヤードの［なぞのかべ］: 受ける 30 以上のダメージは 0（8 段階）、30 より小さいダメージはそのまま。ダメージ以外の効果は受ける。"""

    def test_threshold_boundary(self):
        for active, index, expected in ((mon(HITMONCHAN, (F, F, F)), 0, 20), (mon(HITMONCHAN, (F, F, F)), 1, 0),
                                        (mon(HITMONCHAN, (F,), trainers=[(PLUSPOWER, TURN)]), 0, 0)):
            state = board(active, mon(MR_MIME, (P,)))
            new = audited(self, attack(state, index))
            [(_, amount, steps)] = damage_events(new, len(state.log))
            with self.subTest(index=index, steps=steps):
                self.assertEqual(amount, expected)
                self.assertEqual(steps[-1][0], "8 バリヤード［なぞのかべ］")
                self.assertEqual(events(new, len(state.log), "damage")[0]["damage_zero_at_least"], ((8, state.players[1].active.card, 30),))

    def test_defender_before_the_wall(self):
        """ディフェンダー（7 段階）で 20 になったダメージは、30 より小さいのでそのまま受ける。"""
        state = board(mon(HITMONCHAN, (F, F, F)), mon(MR_MIME, (P,), trainers=[(DEFENDER, TURN)]))  # 相手が前の番に使った
        new = audited(self, attack(state, 1))
        self.assertEqual(damage_events(new, len(state.log))[0][1], 20)

    def test_effects_other_than_damage_are_received(self):
        """ダメージが 0 になってもダメージ以外の効果（どく）は受ける（ワザの要素を無効にしない）。"""
        state = board(mon(HITMONCHAN, (F, F, F)), mon(MR_MIME, (P,)))
        new = audited(self, attack(state, 1))
        self.assertEqual(damage_events(new, len(state.log))[0][1], 0)
        state = board(mon(NIDOKING, (G, G, G)), mon(MR_MIME, (P,)))
        new = audited(self, attack(state, 1))  # どくどく 20（30 より小さいのでそのまま）→ 特殊などく（ポケモンチェックの 20 できぜつ）
        self.assertEqual([e["amount"] for e in events(new, len(state.log), "damage")], [20])
        self.assertEqual([(e["condition"], e["damage"]) for e in events(new, len(state.log), "special_condition")], [("poison", 20)])
        # 0 になったダメージのあとのダメージ以外の効果: ヘドロパンチ（20。そのまま）ではなく、40 の要素のあとに特殊状態を与えるワザで確かめる（ナッシーのふみつけ
        # はダメージだけなので、わるいラフレシアの「はなびらのうず」の自分のこんらんで確かめる。60 → 0 でも自分はこんらん）
        state = board(mon(DARK_VILEPLUME, (G, G, G)), mon(MR_MIME, (P,)))
        new = audited(self, attack(state, 0, H, H, T))
        self.assertEqual((damage_events(new, len(state.log))[0][1], new.players[0].active.conditions.confused), (0, True))

    def test_status_gas_and_bench(self):
        """ねむり・マヒ・こんらんのとき・かがくへんかガスがはたらいているときは使えない。ベンチでもはたらく（どこでも）。"""
        for spec in (mon(MR_MIME, (P,), sleep=True), mon(MR_MIME, (P,), confusion=True)):
            state = board(mon(HITMONCHAN, (F, F, F)), spec)
            new = audited(self, attack(state, 1))
            self.assertEqual(damage_events(new, len(state.log))[0][1], 40)
        state = board(mon(HITMONCHAN, (F, F, F)), mon(MR_MIME, (P,)), opponent_bench=(mon(MUK),))
        self.assertEqual(damage_events(audited(self, attack(state, 1)), len(state.log))[0][1], 40)
        state = board(mon(ERIKAS_VENUSAUR, (G, G, G, G)), opponent_bench=(MR_MIME, RATTATA))
        new = attack(state, 1)
        new = audited(self, answer(new, new.decision.options[:2]))
        bench = [e for e in events(new, len(state.log), "damage") if e.get("target") == "opponent_bench" and e["pokemon_id"] == pid_of(state, 1, MR_MIME)]
        self.assertEqual([tuple(s[0] for s in e["steps"]) for e in bench], [("1 基本となる計算", "8 バリヤード［なぞのかべ］")])

    def test_yoga_pose_uses_the_defending_pokemon_only(self):
        """ヨガのポーズ（「相手にのっているダメージカウンター」）は相手の対戦ポケモンのカウンターだけ。CD4（ルージュラの「相手のポケモン」）にならない。"""
        state = board(mon(MR_MIME, (P, P)), mon(HITMONCHAN, (F,), damage=30), opponent_bench=({"card": RATTATA, "damage": 10},))
        new = audited(self, attack(state, 0))
        self.assertEqual(damage_events(new, len(state.log))[0][2][0], ("1 基本となる計算", 40))


class StrangeBarrierTest(unittest.TestCase):
    """エリカのミニリュウの［ふしぎなバリアー］: たねポケモンから受ける 20 以上のダメージは 10（8 段階）。進化したポケモン・ポケモン以外からのダメージは変えない。"""

    def test_from_basic_and_from_evolved(self):
        for active, index, expected in ((mon(HITMONCHAN, (F, F, F)), 0, 10), (mon(HITMONCHAN, (F, F, F)), 1, 10), (mon(RATICATE, (P,)), 0, 20)):
            state = board(active, mon(ERIKAS_DRATINI, (P,)))
            new = audited(self, attack(state, index))
            with self.subTest(active=active["card"], index=index):
                self.assertEqual(damage_events(new, len(state.log))[0][1], expected)

    def test_power_damage_from_a_basic(self):
        """R団のカビゴン（たねポケモン）の［わるいねぞう］の 20（特殊能力のダメージ）も「受けるダメージ」なので 10。記録は amount_before・received_modifiers。"""
        state = build_test_state([{"active": mon(ERIKAS_DRATINI, (P, P)), "bench": [RATTATA]},
                                  {"active": mon(ROCKETS_SNORLAX, (P,), sleep=True), "bench": [RATTATA]}], turn_number=TURN)
        new = audited(self, attack(state, 0, T))
        [counter] = events(new, len(state.log), "counterattack")
        self.assertEqual((counter["amount"], counter["amount_before"]), (10, 20))
        self.assertEqual(counter["received_modifiers"], ((state.players[0].active.card, SET_IF_AT_LEAST, 20, 10),))

    def test_status_at_damage_time(self):
        """ダメージを受ける時、すでにねむり・マヒ・こんらんなら使えない。"""
        state = board(mon(HITMONCHAN, (F, F, F)), mon(ERIKAS_DRATINI, (P,), confusion=True))
        self.assertEqual(damage_events(audited(self, attack(state, 1)), len(state.log))[0][1], 40)


# ---------------------------------------------------------------- くつろぐかおり


def calming_board(*, holder=None, opponent=None, holder_bench=(RATTATA,), opponent_bench=(RATTATA,)):
    return build_test_state([{"active": holder or mon(ERIKAS_IVYSAUR, (G, G, G)), "bench": [bench_spec(b) for b in holder_bench]},
                             {"active": opponent or mon(HITMONCHAN, (F, F, F)), "bench": [bench_spec(b) for b in opponent_bench]}], turn_number=TURN)


class CalmingAromaTest(unittest.TestCase):
    """エリカのフシギソウの［くつろぐかおり］: バトル場にいる限り、お互いの対戦ポケモンのワザのダメージは半分（切り上げ）。段階は持ち主の区別（2・6・8）。"""

    def test_both_sides_and_rounding_up(self):
        state = calming_board()
        new = audited(self, attack(state, 0, H, H))
        self.assertEqual(damage_events(new, len(state.log)), [("opponent", 40, [("1 基本となる計算", 80), ("2 エリカのフシギソウ［くつろぐかおり］", 40)])])
        # 相手のワザ（受けるのはフシギソウ。8 段階）。30 は 2 カウンター（切り上げ）
        for active, index, expected in ((mon(HITMONCHAN, (F, F, F)), 0, 10), (mon(HITMONCHAN, (F, F, F)), 1, 20),
                                        (mon(HITMONCHAN, (F,), trainers=[(PLUSPOWER, TURN)]), 0, 20)):
            state = board(active, mon(ERIKAS_IVYSAUR, (G,)))
            new = audited(self, attack(state, index))
            with self.subTest(index=index):
                self.assertEqual(damage_events(new, len(state.log))[0][1], expected)
                self.assertEqual(events(new, len(state.log), "damage")[0]["damage_halved"], ((8, state.players[1].active.card, "up"),))

    def test_third_party_bench_and_self_damage_at_step_6(self):
        """相手の控えへのダメージ・ワザを使うポケモンの自分へのダメージは、くつろぐかおりの持ち主がどちらでもないので 6 段階。1 つのダメージに 1 回。"""
        state = board(mon(ERIKAS_VENUSAUR, (G, G, G, G)), mon(ERIKAS_IVYSAUR, (G,)), opponent_bench=(RATTATA, MACHOP))
        new = attack(state, 1)
        new = audited(self, answer(new, new.decision.options[:2]))
        damages = events(new, len(state.log), "damage")
        self.assertEqual([(e.get("target", "opponent"), e["amount"], e["damage_halved"]) for e in damages],
                         [("opponent", 10, ((8, state.players[1].active.card, "up"),)),
                          ("opponent_bench", 10, ((6, state.players[1].active.card, "up"),)),
                          ("opponent_bench", 10, ((6, state.players[1].active.card, "up"),))])
        state = board(mon(ERIKAS_EXEGGCUTE, (G, G)), mon(ERIKAS_IVYSAUR, (G,)))
        new = audited(self, attack(state, 1, T))  # タマゴばくだんの「うら」: 自分に 20 → 6 段階で 10
        self.assertEqual([(e["target"], e["amount"], e["damage_halved"]) for e in events(new, len(state.log), "damage")],
                         [("self", 10, ((6, state.players[1].active.card, "up"),))])

    def test_bench_status_gas(self):
        """ベンチのフシギソウ・ワザが使われた時にねむり・マヒ・こんらんのフシギソウ・かがくへんかガスのときははたらかない。"""
        cases = (board(mon(HITMONCHAN, (F, F, F)), mon(RATTATA), opponent_bench=(ERIKAS_IVYSAUR,)),
                 board(mon(HITMONCHAN, (F, F, F)), mon(ERIKAS_IVYSAUR, (G,), sleep=True)),
                 board(mon(HITMONCHAN, (F, F, F)), mon(ERIKAS_IVYSAUR, (G,)), opponent_bench=(mon(MUK),)))
        for state in cases:
            new = audited(self, attack(state, 1))
            self.assertNotIn("damage_halved", events(new, len(state.log), "damage")[0])

    def test_status_is_the_one_when_the_attack_was_used(self):
        """「ワザが使われた時」の特殊状態（宣言の時点）で決め、ワザの途中で変わっても、そのワザでは変わらない（決定をまたいでも続きの情報で運ぶ）。
        盤面を直接書きかえて確かめる（自然な対戦では、決定を待つ間にフシギソウの特殊状態は変わらない）。"""
        for asleep in (False, True):
            state = board(mon(ERIKAS_VENUSAUR, (G, G, G, G)), mon(ERIKAS_IVYSAUR, (G,), sleep=asleep), opponent_bench=(RATTATA, MACHOP))
            waiting = attack(state, 1)
            self.assertEqual(dict(waiting.decision.context).get("attack_status") is not None, asleep)
            changed = waiting.clone()
            ivysaur = changed.players[1].active
            ivysaur.conditions = dataclasses.replace(ivysaur.conditions, exclusive=None if asleep else Asleep())
            new = answer(changed, changed.decision.options[:2])
            bench = [e for e in events(new, len(waiting.log), "damage") if e.get("target") == "opponent_bench"]
            with self.subTest(asleep=asleep):
                self.assertEqual([e["amount"] for e in bench], [20, 20] if asleep else [10, 10])

    def test_order_decision_with_growl(self):
        """カラカラの「なきつく」（2 段階の -20）を受けたフシギソウがカラカラにワザを使うと、2 段階に加算と半分が重なり順番で結果が変わるので、ワザを使うプレイヤーが
        順番を選ぶ（v0.35 の決定）。選んだ順番で計算する（コインは投げ直さない）。"""
        state = build_test_state([{"active": mon(ERIKAS_IVYSAUR, (G, G, G)), "bench": [RATTATA]},
                                  {"active": mon(CUBONE, (F,)), "bench": [RATTATA]}], turn_number=TURN + 1, current_player=1)
        growled = attack(state, 0, player=1)
        waiting = attack(growled, 0, H, H)
        self.assertEqual((waiting.decision.kind, waiting.decision.player, waiting.decision.options), (DAMAGE_STEP_ORDER, 0, (0, 1)))
        results = {o: damage_events(audited(self, answer(waiting, (o,))), len(waiting.log))[0][1] for o in waiting.decision.options}
        self.assertEqual(results, {0: 60, 1: 40})  # (80 - 20) / 2 × 2（弱点 草）= 60、80 / 2 - 20 = 20 × 2 = 40

    def test_retaliation_stops_when_halving_changes_the_return(self):
        """CP1: 返す効果のダメージに「ワザが使われた時」の特殊状態を当てはめるかが決まらない（前の番のワザか、きっかけのワザか）。半分にするかで結果が変わるなら、
        ワザの宣言の前に止める（こうらがえし。ほのおのかべも、フシギソウの弱点 炎で 20 が 10 になるので止まる）。"""
        for holder in (mon(DARK_WARTORTLE, (W, W), retaliation_received=TURN - 1), mon(ROCKETS_MOLTRES, (R, R, R), retaliation=TURN - 1)):
            with self.subTest(holder=holder["card"]):
                assert_stops(self, with_coin_results(calming_board(opponent=holder), H, H), UseAttack(0, 0), CP1)

    def test_retaliation_proceeds_without_an_active_calming_aroma(self):
        """CP1 の隣: フシギソウがベンチなら（バトル場のフシギソウがいない）、返すダメージは半分にしない。"""
        state = calming_board(holder=mon(HITMONCHAN, (F, F, F)), opponent=mon(DARK_WARTORTLE, (W, W), retaliation_received=TURN - 1),
                              holder_bench=(ERIKAS_IVYSAUR,))
        new = audited(self, attack(state, 1))
        returned = [e for e in events(new, len(state.log), "damage") if e.get("retaliation")]
        self.assertEqual([(e["amount"], "damage_halved" in e) for e in returned], [(40, False)])

    def test_confused_attacker_stops_before_the_coin(self):
        """こんらんの 20 にくつろぐかおりを当てはめるかは決まらない（v0.3c）ので、はたらいていれば、こんらんのコインの前に既存の問いで止める。"""
        assert_stops(self, board(mon(HITMONCHAN, (F, F, F), confusion=True), mon(ERIKAS_IVYSAUR, (G,))), UseAttack(0, 0), CONFUSION_MODIFIERS)
        # 隣: フシギソウがベンチならはたらかないので止めない
        state = board(mon(HITMONCHAN, (F, F, F), confusion=True), mon(RATTATA), opponent_bench=(ERIKAS_IVYSAUR,))
        audited(self, attack(state, 0, T))

    def test_power_damage_is_not_halved(self):
        """特殊能力のダメージ（わるいねぞう）はワザのダメージではないので半分にしない。"""
        state = build_test_state([{"active": mon(ERIKAS_IVYSAUR, (G, G, G)), "bench": [RATTATA]},
                                  {"active": mon(ROCKETS_SNORLAX, (P,), sleep=True), "bench": [RATTATA]}], turn_number=TURN)
        new = audited(self, attack(state, 0, H, T))
        [counter] = events(new, len(state.log), "counterattack")
        self.assertEqual((counter["amount"], "amount_before" in counter), (20, False))


# ---------------------------------------------------------------- きょうぼう


class FrenzyTest(unittest.TestCase):
    """わるいオコリザルの［きょうぼう］: こんらん状態の時、このカードがポケモンに与えるダメージは +30（2 段階）。こんらんで消えない（こんらんがはたらく条件）。"""

    def test_bonus_only_while_confused(self):
        state = board(mon(DARK_PRIMEAPE, (F, F)))
        primeape, defender = state.players[0].active, state.players[1].active
        key = E.AttackKey(DARK_PRIMEAPE, 0)
        self.assertEqual(E.attack_damage_modifiers(state, primeape, defender, attack=key), ())
        confused = board(mon(DARK_PRIMEAPE, (F, F), confusion=True))
        primeape, defender = confused.players[0].active, confused.players[1].active
        self.assertEqual(E.attack_damage_modifiers(confused, primeape, defender, attack=key),
                         (DamageModifier(step=2, amount=30, label="わるいオコリザル［きょうぼう］", source=primeape.card),))
        gassed = board(mon(DARK_PRIMEAPE, (F, F), confusion=True), opponent_bench=(mon(MUK),))
        self.assertEqual(E.attack_damage_modifiers(gassed, gassed.players[0].active, gassed.players[1].active, attack=key), ())

    def test_confused_primeape_cannot_attack(self):
        """こんらんの 20 が「このカードがポケモンに与えるダメージ」かは決まらない（v0.3c）ので、こんらんのわるいオコリザルのワザは、コインの前に止まる（どの先読みでも）。
        +30 は、こんらん状態の時だけはたらくので、対戦では起こらない（docs 4.4）。"""
        assert_stops(self, board(mon(DARK_PRIMEAPE, (F, F), confusion=True)), UseAttack(0, 0), CONFUSION_MODIFIERS)

    def test_rampage_damages_then_confuses_itself(self):
        state = board(mon(DARK_PRIMEAPE, (F, F)))
        new = audited(self, attack(state, 0))
        self.assertEqual(damage_events(new, len(state.log)), [("opponent", 40, [("1 基本となる計算", 40)])])
        self.assertTrue(new.players[0].active.conditions.confused)
        self.assertEqual([e["kind"] for e in events(new, len(state.log)) if e["kind"] in ("damage", "special_condition")], ["damage", "special_condition"])

    def test_rampage_against_the_wall_is_z23(self):
        """なぞのかべで 0 になると「ダメージを与えた後」の自分のこんらんは Z23（既存の問い）。"""
        assert_stops(self, board(mon(DARK_PRIMEAPE, (F, F)), mon(MR_MIME, (P,))), UseAttack(0, 0), Z23)


# ---------------------------------------------------------------- にげるサポート・ねんちゃくえき


class RetreatCostTest(unittest.TestCase):
    """「にげる」のエネルギーの数（``effects.retreat_cost``）: 印刷の数 + ［ねんちゃくえき］（相手のバトル場。決まって +2）− ［にげるサポート］（自分のベンチ。
    少なくできる。−1）、最後に 0 で下限。"""

    def assert_counts(self, state, allowed, *, rejected=(), stopped=()):
        p = state.players[0]
        for count in sorted({*allowed, *rejected, *stopped}):
            command = Retreat(0, tuple(p.active.energy[:count]), p.bench[-1].card)
            with self.subTest(count=count):
                if count in allowed:
                    new = audited(self, apply_kernel(state, command))
                    self.assertEqual(new.players[0].active.card, p.bench[-1].card)
                elif count in stopped:
                    assert_rejected(self, state, command, CP2)
                else:
                    assert_rejected(self, state, command, "WRONG_RETREAT_COST")

    def test_sticky_goo_and_retreat_aid(self):
        self.assertEqual(E.retreat_cost(board(mon(HITMONCHAN, (F,) * 4)), 0), E.RetreatCost(2))
        self.assert_counts(board(mon(HITMONCHAN, (F,) * 4), mon(DARK_MUK, (G,))), {4}, rejected={2, 3})
        self.assert_counts(board(mon(HITMONCHAN, (F,) * 4), bench=(mon(DODRIO), RATTATA)), {1, 2}, rejected={0, 3})
        self.assert_counts(board(mon(HITMONCHAN, (F,) * 4), mon(DARK_MUK, (G,)), bench=(mon(DODRIO), RATTATA)), {3, 4}, rejected={2})
        self.assert_counts(board(mon(HITMONCHAN, (F,) * 4), bench=(mon(DODRIO), mon(DODRIO), RATTATA)), {0, 1, 2}, rejected={3})

    def test_floor_reading_stops(self):
        """CP2: 少なくする数が印刷の数より多く、増やす数もある（にげる 0 のドードーのベンチにドードリオ、相手のバトル場にわるいベトベトン）。先に 0 で止めて増やす読み方では
        2、合わせてから 0 で止める読み方では 1。1 枚の「にげる」は読み方で答えが変わるので止め、2 枚はどちらでも足りるので受け付ける。"""
        state = board(mon(DODUO, (F, F, F)), mon(DARK_MUK, (G,)), bench=(mon(DODRIO), RATTATA))
        cost = E.retreat_cost(state, 0)
        self.assertEqual((cost.minimum, cost.floor_first_minimum, cost.maximum), (1, 2, 2))
        self.assert_counts(state, {2}, rejected={0, 3}, stopped={1})

    def test_conditions_location_and_gas(self):
        """ねんちゃくえきは、わるいベトベトンがねむり・マヒ・こんらん・ベンチ・かがくへんかガスのとき消える。にげるサポートはベンチのときだけ（バトル場のドードリオ自身には
        当てはめない）・かがくへんかガスで消える。"""
        for opponent, bench in ((mon(DARK_MUK, (G,), sleep=True), (RATTATA,)), (mon(HITMONCHAN, (F,)), (mon(DARK_MUK),)),
                                (mon(DARK_MUK, (G,)), (mon(MUK),))):
            state = board(mon(HITMONCHAN, (F,) * 4), opponent, opponent_bench=bench)
            with self.subTest(opponent=opponent["card"], bench=bench):
                self.assertFalse(E.retreat_cost(state, 0).modified)
        self.assertFalse(E.retreat_cost(board(mon(DODRIO, (F,))), 0).modified)
        self.assertFalse(E.retreat_cost(board(mon(HITMONCHAN, (F,) * 4), bench=(mon(DODRIO), RATTATA), opponent_bench=(mon(MUK),)), 0).modified)

    def test_other_switches_are_not_affected(self):
        """ポケモンいれかえ（エネルギーをトラッシュしない）は、ねんちゃくえきに関係なく使える。"""
        state = board(mon(HITMONCHAN, (F,)), mon(DARK_MUK, (G,)), hand=(SWITCH,))
        new = apply_kernel(state, PlayTrainer(0, card_of(state, 0, SWITCH)))
        new = audited(self, answer(new, (new.decision.options[0],)))
        self.assertEqual(state.card_def(new.players[0].active.card).id, RATTATA)

    def test_logs_and_public_query(self):
        state = board(mon(HITMONCHAN, (F,) * 4), mon(DARK_MUK, (G,)), bench=(mon(DODRIO), RATTATA))
        p = state.players[0]
        new = apply_kernel(state, Retreat(0, tuple(p.active.energy[:3]), p.bench[-1].card))
        [retreat] = events(new, len(state.log), "retreat")
        muk, dodrio = state.players[1].active.pokemon_id, p.bench[0].pokemon_id
        self.assertEqual((retreat["retreat_cost"], retreat["retreat_cost_printed"], retreat["retreat_cost_increases"], retreat["retreat_cost_reductions"]),
                         ((3, 4), 2, ((muk, f"{DARK_MUK}@power0", 2),), ((dodrio, f"{DODRIO}@power0", 1),)))
        plain = board(mon(HITMONCHAN, (F, F)))
        new = apply_kernel(plain, Retreat(0, tuple(plain.players[0].active.energy), plain.players[0].bench[0].card))
        self.assertNotIn("retreat_cost", events(new, len(plain.log), "retreat")[0])  # 特殊能力がなければ v0.45 と同じ形
        with self.assertRaises(ValueError):
            broken = state.clone()
            broken.players[0].active = None
            E.retreat_cost(broken, 0)


# ---------------------------------------------------------------- アレルギーかふん


class AllergicPollenTest(unittest.TestCase):
    """わるいラフレシアの［アレルギーかふん］: 場にいる限り、誰もトレーナーカードを使えない（手札から出す前に拒否。状態・乱数・ログは変わらない）。"""

    def test_both_players_are_locked(self):
        state = board(mon(HITMONCHAN, (F,)), hand=(POTION, SWITCH), opponent_bench=(mon(DARK_VILEPLUME),))
        self.assertEqual(E.trainer_lock_sources(state), ((1, pid_of(state, 1, DARK_VILEPLUME), f"{DARK_VILEPLUME}@power0"),))
        for card in (POTION, SWITCH):
            assert_rejected(self, state, PlayTrainer(0, card_of(state, 0, card)), "TRAINER_PREVENTED", IllegalActionError)
        mine = board(mon(DARK_VILEPLUME, (G,)), hand=(SWITCH,))
        assert_rejected(self, mine, PlayTrainer(0, card_of(mine, 0, SWITCH)), "TRAINER_PREVENTED", IllegalActionError)

    def test_lock_ends_with_status_gas_or_leaving(self):
        for state in (board(mon(HITMONCHAN, (F,)), mon(DARK_VILEPLUME, (G,), sleep=True), hand=(SWITCH,)),
                      board(mon(HITMONCHAN, (F,)), hand=(SWITCH,), opponent_bench=(mon(DARK_VILEPLUME), mon(MUK)))):
            self.assertEqual(E.trainer_lock_sources(state), ())
            new = apply_kernel(state, PlayTrainer(0, card_of(state, 0, SWITCH)))
            audited(self, answer(new, (new.decision.options[0],)))

    def test_attached_pluspower_still_works(self):
        """すでについているプラスパワーは使い終わっているので、効果は続く。"""
        state = board(mon(HITMONCHAN, (F,), trainers=[(PLUSPOWER, TURN)]), opponent_bench=(mon(DARK_VILEPLUME),))
        new = audited(self, attack(state, 0))
        self.assertEqual(damage_events(new, len(state.log))[0][1], 30)

    def test_breeder_into_dark_vileplume_finishes(self):
        """ポケモン育て屋さんでわるいラフレシアを場に出しても、使っている最中のトレーナーは使い終える。そのあとは使えない。"""
        state = board(mon(HITMONCHAN, (F,)), bench=(ROCKET_ODDISH, RATTATA), hand=(POKEMON_BREEDER, DARK_VILEPLUME, POTION))
        new = apply_kernel(state, PlayTrainer(0, card_of(state, 0, POKEMON_BREEDER)))
        new = answer(new, (pid_of(new, 0, ROCKET_ODDISH),))
        new = audited(self, answer(new, (card_of(new, 0, DARK_VILEPLUME),)))
        self.assertIn(card_of(state, 0, POKEMON_BREEDER), new.players[0].discard)
        self.assertTrue(E.trainer_lock_sources(new))
        assert_rejected(self, new, PlayTrainer(0, card_of(new, 0, POTION)), "TRAINER_PREVENTED", IllegalActionError)

    def test_petal_whirlwind(self):
        """はなびらのうず: 同じ 3 枚のコインの「おもて」の数 × 30、2 枚以上「おもて」なら自分がこんらん（投げ直さない）。"""
        for sides, damage, confused in (((H, H, T), 60, True), ((H, T, T), 30, False), ((T, T, T), 0, False), ((H, H, H), 90, True)):
            state = board(mon(DARK_VILEPLUME, (G, G, G)), mon(SNORLAX, (P,)))
            new = audited(self, attack(state, 0, *sides))
            with self.subTest(sides=sides):
                self.assertEqual(len(events(new, len(state.log), "coin_flip")), 3)
                self.assertEqual(sum(e["amount"] for e in events(new, len(state.log), "damage")), damage)
                self.assertEqual(new.players[0].active.conditions.confused, confused)


# ---------------------------------------------------------------- めんえき


class ImmunityTest(unittest.TestCase):
    """カビゴンの［めんえき］: どく・ねむり・マヒ・こんらんにならない（付ける処理の共通の入口で防ぐ。ログ special_condition_prevented）。回復ではない。"""

    def prevented(self, state, since):
        return [e["condition"] for e in events(state, since, "special_condition_prevented")]

    def test_every_condition_is_prevented_and_coins_are_flipped(self):
        state = board(mon(DARK_MUK, (G, G)), mon(SNORLAX, (P,)))
        new = audited(self, attack(state, 0))
        self.assertEqual((self.prevented(new, len(state.log)), new.players[1].active.conditions.names()), (["poison"], ()))
        state = board(mon(SNORLAX, (P,) * 4), mon(SNORLAX, (P,)))
        new = audited(self, attack(state, 0, H))
        self.assertEqual([e["kind"] for e in events(new, len(state.log)) if e["kind"] in ("coin_flip", "special_condition_prevented")],
                         ["coin_flip", "special_condition_prevented"])
        state = board(mon(ROCKET_ODDISH, (G,)), mon(SNORLAX, (P,)))
        self.assertEqual(self.prevented(audited(self, attack(state, 0)), len(state.log)), ["sleep"])
        state = board(mon(DARK_PRIMEAPE, (F, F)), mon(SNORLAX, (P,)))
        self.assertEqual(self.prevented(audited(self, attack(state, 0)), len(state.log)), [])  # あばれくるうのこんらんは自分（オコリザル）

    def test_poisoned_snorlax_keeps_the_power_and_does_not_stop_on_tp3(self):
        """どく状態だけなら使える。特殊などくの上書き（TP3）は防がれて結果が変わらないので止めない。どくは残る（回復しない）。"""
        state = board(mon(NIDOKING, (G, G, G)), mon(SNORLAX, (P,), poison=10))
        new = audited(self, attack(state, 1))
        self.assertEqual((self.prevented(new, len(state.log)), new.players[1].active.conditions.poison.damage), (["poison"], 10))

    def test_confused_snorlax_and_gas(self):
        """なんらかの原因でねむり・マヒ・こんらんならこの力は使えない。かがくへんかガスで消える。"""
        state = board(mon(NIDOKING, (G, G, G)), mon(SNORLAX, (P,), confusion=True))
        self.assertEqual(audited(self, attack(state, 1)).players[1].active.conditions.poison.damage, 20)
        state = board(mon(DARK_MUK, (G, G)), mon(SNORLAX, (P,)), opponent_bench=(mon(MUK),))
        self.assertIsNotNone(audited(self, attack(state, 0)).players[1].active.conditions.poison)

    def test_power_applied_status_is_prevented(self):
        """特殊能力で付けようとしても防ぐ（わるいクサイハナの［くさいかふん］の「おもて」）。"""
        state = board(mon(DARK_GLOOM, (G,), evolved_from=ROCKET_ODDISH, played_turn=1, evolved_turn=TURN - 2), mon(SNORLAX, (P,)))
        new = apply_kernel(with_coin_results(state, H), UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        self.assertEqual(self.prevented(audited(self, new), len(state.log)), ["confusion"])


# ---------------------------------------------------------------- 関連する 3 枚


class GrowthAndSpreadTest(unittest.TestCase):
    """エリカのフシギバナ: せいちょう（コインの「おもて」で手札の草エネルギーを最大 2 枚つける）・かくさんソーラービーム（控えポケモン 2 匹に 20 ずつ）。"""

    def test_growth_attaches_from_hand_without_using_the_attachment(self):
        state = board(mon(ERIKAS_VENUSAUR, (G,)), hand=(G, G, G, F))
        waiting = attack(state, 0, H)
        self.assertEqual((waiting.decision.kind, waiting.decision.min_choices, waiting.decision.max_choices, len(waiting.decision.options)),
                         (ATTACH_FROM_HAND, 0, 2, 3))
        new = audited(self, answer(waiting, waiting.decision.options[:2]))
        [attached] = events(new, len(state.log), "attach_energy_from_hand")
        self.assertEqual(attached["cards"], waiting.decision.options[:2])
        self.assertEqual((len(new.players[0].active.energy), new.energy_attachments_this_turn, new.energy_attached_by_powers_this_turn), (3, 0, 0))

    def test_growth_zero_and_no_target(self):
        """手札に草エネルギーがあるときの 0 枚は HC7（決定は待ったまま）。手札になければコインを投げない（処理の対象がない）。「うら」なら何もしない。"""
        waiting = attack(board(mon(ERIKAS_VENUSAUR, (G,)), hand=(G,)), 0, H)
        assert_rejected(self, waiting, ResolveDecision(0, waiting.decision.id, ()), HC7, UnsupportedError)
        state = board(mon(ERIKAS_VENUSAUR, (G,)), hand=(F,))
        self.assertEqual(events(audited(self, attack(state, 0)), len(state.log), "coin_flip"), [])
        state = board(mon(ERIKAS_VENUSAUR, (G,)), hand=(G,))
        self.assertEqual(events(audited(self, attack(state, 0, T)), len(state.log), "attach_energy_from_hand"), [])

    def test_spread_needs_exactly_two(self):
        state = board(mon(ERIKAS_VENUSAUR, (G,) * 4), opponent_bench=(RATTATA, MACHOP, RATTATA))
        waiting = attack(state, 1)
        self.assertEqual((waiting.decision.kind, waiting.decision.min_choices, waiting.decision.max_choices), (SELECT_POKEMON, 2, 2))
        assert_rejected(self, waiting, ResolveDecision(0, waiting.decision.id, waiting.decision.options[:1]), "INVALID_CHOICE_COUNT")
        new = audited(self, answer(waiting, waiting.decision.options[:2]))
        self.assertEqual([(e.get("target", "opponent"), e["amount"]) for e in events(new, len(state.log), "damage")],
                         [("opponent", 20), ("opponent_bench", 20), ("opponent_bench", 20)])

    def test_spread_with_one_or_no_bench(self):
        """控えが 1 匹（「2匹」に足りない）は FC1、0 匹なら対戦ポケモンへのダメージだけ。"""
        assert_stops(self, board(mon(ERIKAS_VENUSAUR, (G,) * 4), opponent_bench=(RATTATA,)), UseAttack(0, 1), FC1)
        state = board(mon(ERIKAS_VENUSAUR, (G,) * 4), opponent_bench=())
        new = audited(self, attack(state, 1))
        self.assertEqual(([e["amount"] for e in events(new, len(state.log), "damage")], new.decision), ([20], None))


class ExeggcuteTest(unittest.TestCase):
    """エリカのタマタマ: リフレクター（次の相手の番に受けるワザのダメージは半分（切りすて））・タマゴばくだん（「うら」なら相手にダメージを与えず自分に 20）。"""

    def test_reflector_halves_down_and_expires(self):
        state = board(mon(ERIKAS_EXEGGCUTE, (P,)), mon(HITMONCHAN, (F, F, F), trainers=[(PLUSPOWER, TURN + 1)]))
        reflected = audited(self, attack(state, 0))
        [effect] = reflected.players[0].active.persistent_effects
        self.assertEqual((type(effect), effect.active_turn), (HalvedDamage, TURN + 1))
        new = audited(self, attack(reflected, 0, player=1))  # 20 + 10 = 30 → 1 カウンター半（切りすて）= 10
        self.assertEqual(damage_events(new, len(reflected.log))[0][1:], (10, [("1 基本となる計算", 20), ("5 プラスパワー", 30),
                                                                           ("8 エリカのタマタマ（halved_damage）", 10)]))
        self.assertEqual(new.players[0].active.persistent_effects, ())  # 次の相手の番の終わりに消える

    def test_reflector_and_calming_aroma(self):
        """フシギソウ（相手。ワザを使うポケモン）のくつろぐかおり（2 段階・切り上げ）とリフレクター（8 段階・切りすて）は別の段階で、どちらも当てはまる。"""
        state = build_test_state([{"active": mon(ERIKAS_EXEGGCUTE, (P,)), "bench": [RATTATA]},
                                  {"active": mon(ERIKAS_IVYSAUR, (G, G, G)), "bench": [RATTATA]}], turn_number=TURN)
        reflected = attack(state, 0)
        new = audited(self, attack(reflected, 0, H, H, player=1))
        self.assertEqual(damage_events(new, len(reflected.log))[0][2][1:], [("2 エリカのフシギソウ［くつろぐかおり］", 40), ("8 エリカのタマタマ（halved_damage）", 20)])

    def test_egg_bomb_tails_is_not_a_failure(self):
        for side, expected in ((H, [("opponent", 40)]), (T, [("self", 20)])):
            state = board(mon(ERIKAS_EXEGGCUTE, (G, G)))
            new = audited(self, attack(state, 1, side))
            with self.subTest(side=side):
                self.assertEqual([(e.get("target", "opponent"), e["amount"]) for e in events(new, len(state.log), "damage")], expected)
                self.assertEqual(events(new, len(state.log), "attack_failed"), [])


class PsychicExchangeTest(unittest.TestCase):
    """エリカのナッシーのサイコエクスチェンジ: 手札をすべて山札にもどし（見せない）、山札を切ってから 5 枚引く（足りなければ引けるだけ）。"""

    def test_returns_shuffles_then_draws(self):
        state = board(mon(ERIKAS_EXEGGUTOR, (P,)), hand=(G, F, POTION), deck=[RATTATA] * 10)
        new = audited(self, attack(state, 0))
        kinds = [e["kind"] for e in events(new, len(state.log)) if e["kind"] in ("hand_to_deck", "shuffle", "draw")]
        self.assertEqual(kinds[:3], ["hand_to_deck", "shuffle", "draw"])
        [returned] = events(new, len(state.log), "hand_to_deck")
        self.assertEqual(sorted(returned["cards"]), sorted(state.players[0].hand))
        self.assertEqual(len(events(new, len(state.log), "draw")[0]["cards"]), 5)
        self.assertEqual((len(new.players[0].hand), len(new.players[0].deck)), (5, 8))

    def test_small_deck_and_empty_hand(self):
        state = board(mon(ERIKAS_EXEGGUTOR, (P,)), hand=(G, F), deck=[RATTATA] * 2)
        self.assertEqual((len(audited(self, attack(state, 0)).players[0].hand)), 4)
        state = board(mon(ERIKAS_EXEGGUTOR, (P,)), hand=(), deck=[RATTATA] * 6)
        new = audited(self, attack(state, 0))
        self.assertEqual((events(new, len(state.log), "hand_to_deck"), len(new.players[0].hand)), ([], 5))


# ---------------------------------------------------------------- 相手のワザとして使う・先読み・書き出し・不変条件


class CopyTest(unittest.TestCase):
    """ピッピ（ゆびをふる）が v0.46 のワザを自分のワザとして使う。"""

    def test_copy_reflector_and_spread(self):
        state = board(mon(CLEFAIRY, (P, P, P)), mon(ERIKAS_EXEGGCUTE, (P,)))
        waiting = attack(state, 1)
        self.assertEqual(waiting.decision.kind, SELECT_ATTACK)
        new = audited(self, answer(waiting, (0,)))
        self.assertEqual([type(e) for e in new.players[0].active.persistent_effects], [HalvedDamage])
        state = board(mon(CLEFAIRY, (P, P, P)), mon(ERIKAS_VENUSAUR, (G,)), opponent_bench=(RATTATA, MACHOP))
        waiting = answer(attack(state, 1), (1,))
        self.assertEqual((waiting.decision.kind, waiting.decision.min_choices), (SELECT_POKEMON, 2))
        audited(self, answer(waiting, waiting.decision.options[:2]))


class PreflightAndFormatTest(unittest.TestCase):

    def test_every_preflight_mode_gives_the_same_result(self):
        cases = [
            (board(mon(HITMONCHAN, (F, F, F)), mon(MR_MIME, (P,))), 1), (board(mon(ERIKAS_IVYSAUR, (G, G, G))), 0),
            (board(mon(DARK_VILEPLUME, (G, G, G)), mon(SNORLAX, (P,))), 0), (board(mon(ERIKAS_VENUSAUR, (G,)), hand=(G, G)), 0),
            (board(mon(ERIKAS_EXEGGCUTE, (G, G))), 1), (board(mon(ERIKAS_EXEGGUTOR, (G, G, G))), 1), (board(mon(ERIKAS_DRATINI, (P, P))), 0),
            (board(mon(SNORLAX, (P,) * 4), mon(SNORLAX, (P,))), 0),
        ]
        for state, index in cases:
            for sides in ((H, H, H), (T, T, T), (H, T, H)):
                with self.subTest(card=state.cards[state.players[0].active.card].card_id, sides=sides):
                    results = {mode: repr(full(attack(state, index, *sides, mode=mode))) for mode in PREFLIGHT_MODES}
                    self.assertEqual(len(set(results.values())), 1)

    def test_reflector_is_written_in_format_8_and_later(self):
        state = audited(self, attack(board(mon(ERIKAS_EXEGGCUTE, (P,))), 0))
        written = state_to_dict(state, format_version=8)["players"][0]["active"]["persistent_effects"]
        self.assertEqual([e["effect"] for e in written], [HalvedDamage.kind])
        with self.assertRaises(ValueError):
            state_to_dict(state, format_version=7)
        for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            self.assertEqual(full(copied), full(state))

    def test_decision_context_carries_the_attack_status_only_when_needed(self):
        """ワザが使われた時の特殊状態は、くつろぐかおりを持つ場のポケモンがねむり・マヒ・こんらんのときだけ続きの情報に書く（v0.45 までの決定の形は変えない）。"""
        waiting = attack(board(mon(ERIKAS_VENUSAUR, (G,) * 4), opponent_bench=(RATTATA, MACHOP)), 1)
        self.assertNotIn("attack_status", dict(waiting.decision.context))
        for copied in (waiting.clone(), pickle.loads(pickle.dumps(waiting))):
            self.assertEqual(full(copied), full(waiting))

    def test_invariant_checks_the_reflector_registration(self):
        state = attack(board(mon(ERIKAS_EXEGGCUTE, (P,))), 0)
        broken = state.clone()
        added = next(e for e in broken.log if e["kind"] == "persistent_effect_added")
        broken.log = tuple(MappingProxyType({**dict(e), "effect": f"{ERIKAS_EXEGGCUTE}#1"}) if e is added else e for e in broken.log)
        self.assertTrue(check_invariants(broken))  # タマゴばくだん（効果を与えないワザ）に書きかえると違反


# ---------------------------------------------------------------- 正式な対戦開始からの対戦


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.46 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.46 の 4 組を 3 seed ずつ（席を入れかえて 24 局）。どれも監査の失敗（やり直し・不変条件・ログ・書き出し）・想定外の拒否・内部エラーがなく、11 枚のどのワザも
        1 度は使われ、常にはたらく特殊能力がはたらいた場面（なぞのかべの 0・しきい値より小さいダメージ、くつろぐかおりの 2 段階・8 段階、ねんちゃくえき・にげるサポートで
        数が変わった「にげる」、アレルギーかふんの拒否、めんえきで防いだ特殊状態、リフレクター）が起こる（勝敗は判断に使わない）。きょうぼうの +30 は、こんらんの
        わるいオコリザルのワザが止まるので対戦では起こらない（こんらんの拒否が起こることを確かめる）。"""
        from tools import existing_effect_games as games

        results = games.run(range(3), pairings=games.PAIRINGS_V0_46)
        used, totals, observed = set(), {}, {}
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"))
                for key, count in game["observed"].items():
                    observed[key] = observed.get(key, 0) + count
                for card, uses in game.get("card_uses", {}).items():
                    used |= {(card, int(k.split("#")[1])) for k in uses if re.fullmatch(r"attack#\d", k)}
                    for key, count in uses.items():
                        totals[(card, key)] = totals.get((card, key), 0) + count
        self.assertEqual(set(ATTACKS) - used, set())
        for card, key in ((MR_MIME, "wall_zeroed"), (MR_MIME, "wall_kept"), (ERIKAS_IVYSAUR, "halved_opponent_step2"),
                          (ERIKAS_IVYSAUR, "halved_opponent_step8"), (DARK_MUK, "retreat_increased"), (DODRIO, "retreat_reduced"),
                          (SNORLAX, "immunity_prevented_poison"), (ERIKAS_EXEGGCUTE, "reflector_halved"), (ERIKAS_EXEGGUTOR, "hand_to_deck#0")):
            with self.subTest(card=card, key=key):
                self.assertGreater(totals.get((card, key), 0), 0)
        self.assertGreater(observed.get("stopped_trainer_TRAINER_PREVENTED", 0), 0)
        self.assertGreater(observed.get(f"rejected_attack_{CONFUSION_MODIFIERS}", 0), 0)
        self.assertEqual(totals.get((DARK_PRIMEAPE, "frenzy_bonus"), 0), 0)


if __name__ == "__main__":
    unittest.main()
