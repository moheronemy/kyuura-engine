"""v0.72（docs/status-coins-effect-reuse-v0.72.md）: 拡張パック以外の商品のポケモン 43 枚（kyuura data/engine_targets.json の new_effect_needed。写しの組 pool_v0_72）。

- 既存の効果の型の登録（説明の書き方を、型の登録の引数と結びつけて 1 通りずつ加えた）と、新しい小さな型 8 つ（CoinsHeadsTimesBonusDamage・
  DamageThenStatusSelfAndOpponent・PoisonAndSleepWithoutDamage・DamageThenWakeOpponent・DamageAndOptionalFullDrain・DamageThenMoveOneEnergyToBench・
  RevealBasicEnergyFromDeck・DamageThenForceSwitchAfterDamage）。処理に使う文面は kyuura の印刷の文面（kyuura データの採用。研究の基準のコミット 7d3f4ca に、
  これらのカードを指す LD-・CC-・CR-・UQ-・エラッタはない）
- 43 枚のうち 10 枚は、ほかの v0.72 のカードと処理に使う欄が同じ（effects.SAME_DATA_CARDS_V0_72。登録の値を共有する）
- 再録のなんでもなおし（対象を「あなたの対戦ポケモン」と書く）・ポケモン図鑑（「最大5枚」）の扱いは tests/test_reprint_text_variants_v0_71.py

盤面を直接作るテスト（build_test_state）は 1 か所の規定を確かめるためだけに使い、正式な対戦開始からの対戦は GameTest（tools/existing_effect_games.py の
--batch v0.72）が確かめる。
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pickle
import re
import unittest
from pathlib import Path

from kyuura_engine import (
    IllegalActionError,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine import engine as engine_module
from kyuura_engine.cards import (
    EnergyType,
    load_card_pool,
    pool_from_extract,
    read_extract,
)
from kyuura_engine.coins import CoinSide
from kyuura_engine.conditions import CONFUSION, PARALYSIS, POISON, SLEEP
from kyuura_engine.decisions import (
    ATTACH_TO_BENCH,
    FORCED_SWITCH,
    MOVE_ENERGY,
    OPTIONAL_DRAIN,
    SEARCH_DECK,
)
from kyuura_engine.deck import deck_problems
from kyuura_engine.effects import AttackKey
from kyuura_engine.resolution import PREFLIGHT_MODES, programs, v013_checks
from kyuura_engine.state import (
    AttackBarrier,
    CannotAttack,
    CannotRetreat,
    CannotUseOwnAttack,
)
from scripts import check_card_sources as cs
from tests.helpers import (
    ATTACK_TYPES_SINCE_V0_17,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import serialization_problems

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "status-coins-effect-reuse-v0.72.md"
EXTRACT = read_extract()
CARDS = {c["id"]: c for c in EXTRACT["cards"]}
POOL_V0_72 = tuple(EXTRACT["pool_v0_72"])
H, T = CoinSide.HEADS, CoinSide.TAILS
W, L, G, P, F, R = "PMCG1-099", "PMCG1-100", "PMCG1-097", "PMCG1-101", "PMCG1-102", "PMCG1-098"
DCE, RAINBOW = "PMCG1-096", "PMCG4-065"
HITMONCHAN, RATTATA, DITTO, HAUNTER = "PMCG1-058", "PMCG1-060", "PMCG3-042", "PMCG3-030"
TURN = 5
# 依頼の 43 枚（版を id で決める）
REQUESTED = ("GD1-003", "GD1-012", "GD2-002", "GD3-010", "GD4-003", "GD4-007", "GD4-009", "GD4-012", "GD5-005", "GD6-012",
             "ES1-006", "ES1-009", "ES1-011", "ES1-019", "ES1-020", "ES1-025", "ES1-029", "ES1-031", "ES2-023", "ES2-024", "ES2-027", "ES2-030",
             "ES3-003", "ES3-005", "ES3-008", "ES3-013", "QSG-004", "QSG-020", "QSG-026", "QSG-037", "QSG-038", "QSG-039", "QSG-043", "QSG-054",
             "IP1-022", "PR1-036", "PR1-037", "PR1-040", "PR1-059", "PF3-009", "NIP2-010", "NIP2X-003", "PRN-042")
SAME = {"PR1-040": "GD3-010", "PR1-059": "GD5-005", "QSG-004": "ES1-006", "QSG-020": "ES1-019", "QSG-026": "ES1-020", "QSG-039": "ES1-025",
        "QSG-043": "ES1-031", "QSG-037": "ES2-024", "QSG-038": "ES2-027", "QSG-054": "ES3-008"}
WATER = EnergyType.WATER
EXPECTED = {
    ("GD1-003", 0): (E.PreventDamageOnHeads, {}),
    ("GD1-012", 0): (E.DamageThenForceSwitchAfterDamage, {}),
    ("GD1-012", 1): (E.DamageAndSelfDamage, {"self_damage": 10}),
    ("GD2-002", 0): (E.StatusByCoinWithoutDamage, {"heads": PARALYSIS, "tails": SLEEP}),
    ("GD2-002", 1): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 20}),
    ("GD3-010", 0): (E.AttachDiscardEnergyToSelf, {"energy_type": EnergyType.LIGHTNING, "max_cards": 2}),
    ("GD3-010", 1): (E.DamageThenMoveOneEnergyToBench, {"energy_type": EnergyType.LIGHTNING}),
    ("GD4-003", 0): (E.DamageThenStatusSelfAndOpponent, {"condition": SLEEP}),
    ("GD4-003", 1): (E.DamageThenStatusSelfAndOpponent, {"condition": CONFUSION}),
    ("GD4-007", 0): (E.PoisonAndSleepWithoutDamage, {}),
    ("GD4-009", 0): (E.CoinsPerAttachedEnergyDamage, {"per": 10}),
    ("GD4-009", 1): (E.DamagePlusDefenderEnergy, {"per": 10}),
    ("GD4-012", 0): (E.RevealBasicEnergyFromDeck, {}),
    ("GD4-012", 1): (E.CoinFlipDamage, {"coins": 3, "damage_per_heads": 10}),
    ("GD5-005", 0): (E.DamageAndForceSwitch, {}),
    ("GD5-005", 1): (E.DamageAndSelfDamage, {"self_damage": 10}),
    ("GD6-012", 0): (E.SleepOpponent, {}),
    ("GD6-012", 1): (E.DamageThenWakeOpponent, {}),
    ("ES1-006", 0): (E.CannotAttackOnHeads, {}),
    ("ES1-006", 1): (E.PoisonOnHeads, {}),
    ("ES1-009", 0): (E.DamageAndOptionalFullDrain, {}),
    ("ES1-009", 1): (E.SelfDamageOnTails, {"self_damage": 40}),
    ("ES1-011", 0): (E.PoisonOpponent, {}),
    ("ES1-011", 1): (E.DamageAndOptionalFullDrain, {}),
    ("ES1-019", 0): (E.ParalyzeOnHeads, {}),
    ("ES1-019", 1): (E.DamageThenSelfBarrierOnHeads, {}),
    ("ES1-020", 0): (E.ChooseOpponentPokemonDamage, {"damage": 10}),
    ("ES1-025", 1): (E.CannotAttackOnHeads, {}),
    ("ES1-029", 1): (E.CoinFlipDamage, {"coins": 3, "damage_per_heads": 20}),
    ("ES1-031", 0): (E.SleepOnHeadsWithoutDamage, {}),
    ("ES1-031", 1): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 20}),
    ("ES2-023", 0): (E.CoinsUntilTailsDamage, {"per": 20}),
    ("ES2-023", 1): (E.DamageAndOwnBenchDamage, {"bench_damage": 10, "weakness_resistance_stated": True}),
    ("ES2-024", 0): (E.ParalyzeOnHeads, {}),
    ("ES2-024", 1): (E.DamageThenRetreatLockOnHeads, {}),
    ("ES2-027", 0): (E.DamageThenCoinBenchDamage, {"bench_damage": 10}),
    ("ES2-030", 0): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 10}),
    ("ES3-003", 0): (E.SelfDamageInsteadOnTails, {"self_damage": 20}),
    ("ES3-005", 0): (E.PreventDamageOnHeads, {}),
    ("ES3-005", 1): (E.ParalyzeOnHeads, {}),
    ("ES3-008", 0): (E.DamageThenLockSelf, {}),
    ("ES3-013", 0): (E.DamagePlusDefenderEnergy, {"per": 10}),
    ("IP1-022", 0): (E.DamageAndRemoveCounters, {"counters": 1}),
    ("PR1-036", 0): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 10}),
    ("PR1-036", 1): (E.FailOnTailsDamage, {"coins": 2}),
    ("PR1-037", 0): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 10}),
    ("PF3-009", 0): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 10}),
    ("PF3-009", 1): (E.DamageThenSelfBarrierOnHeads, {}),
    ("NIP2-010", 0): (E.ExtraEnergyDamage, {"energy_type": WATER, "per_energy": 10, "max_extra": 2}),
    ("NIP2X-003", 1): (E.DamageThenDiscardOpponentEnergy, {"on_heads": True}),
    ("PRN-042", 0): (E.CoinsHeadsTimesBonusDamage, {"coins": 2, "per": 20}),
}
for _new, _original in SAME.items():
    for (_card, _index), _value in list(EXPECTED.items()):
        if _card == _original:
            EXPECTED[(_new, _index)] = _value
DAMAGE_ONLY_ATTACKS = (("GD1-003", 1), ("GD4-007", 1), ("ES1-025", 0), ("ES1-029", 0), ("ES2-030", 1), ("ES3-013", 1), ("QSG-039", 0),
                       ("IP1-022", 1), ("PR1-037", 1), ("NIP2X-003", 0))
NEW_TYPES = (E.CoinsHeadsTimesBonusDamage, E.DamageThenStatusSelfAndOpponent, E.PoisonAndSleepWithoutDamage, E.DamageThenWakeOpponent,
             E.DamageAndOptionalFullDrain, E.DamageThenMoveOneEnergyToBench, E.RevealBasicEnergyFromDeck, E.DamageThenForceSwitchAfterDamage)
BELOW = {"GD4-003": "PMCG5-002", "GD4-007": "GD4-006", "ES1-009": "ES1-008", "ES1-011": "NIP1-022", "ES1-029": "IP1-030", "ES2-023": "PMCG3-034",
         "ES3-003": "PMCG1-005", "ES3-013": "PMCG3-010", "IP1-022": "IP1-001"}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), discard=(), deck=None, turn=TURN):
    me = {"active": active, "bench": list(bench), "discard": list(discard)}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent or mon(HITMONCHAN, (F,)), "bench": list(opponent_bench)}
    return build_test_state([me, them], turn_number=turn)


def full(state):
    return state_to_dict(state, format_version=22)


def snapshot(state):
    return full(state), [dict(e) for e in state.log], repr(state.rng.getstate())


def events(state, since, kind=None):
    return [dict(e) for e in state.log[since:] if kind is None or e["kind"] == kind]


def attack(state, index, *sides, player=0, mode="derived"):
    return apply_kernel(with_coin_results(state, *sides) if sides else state, UseAttack(player, index), preflight=mode)


def answer(state, choices, *, mode="derived"):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)), preflight=mode)


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    return state


def assert_stops(test, state, command, code):
    """どの先読みの方法でも code で拒否し、状態・乱数・ログが変わらない（コインの前に止める）。"""
    before = snapshot(state)
    for mode in PREFLIGHT_MODES:
        with test.subTest(mode=mode), test.assertRaises(UnsupportedError) as raised:
            apply_kernel(state, command, preflight=mode)
        test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def same_in_every_mode(test, state, index, sides):
    results = {mode: full(attack(state, index, *sides, mode=mode)) for mode in PREFLIGHT_MODES}
    test.assertEqual(len({repr(r) for r in results.values()}), 1)


def modified_pool(card_id, change):
    """写しの card_id のカードを change（カードの記録を書きかえる関数）で変えた写しで分類した組（製品の写しは変えない）。"""
    extract = copy.deepcopy(read_extract())
    card = next(c for c in extract["cards"] if c["id"] == card_id)
    change(card)
    return pool_from_extract(extract)


def prevented(card=HITMONCHAN, energy=(F,)):
    """「ダメージを受けない」状態（v0.4b の PreventDamage。前の相手の番に与えた）の相手の対戦ポケモン。"""
    return mon(card, energy, prevent_damage=TURN - 1)


# ---------------------------------------------------------------- 対象・登録・数


class TargetTest(unittest.TestCase):

    def test_targets_are_the_requested_43_cards(self):
        self.assertEqual(POOL_V0_72, REQUESTED)
        self.assertEqual(len(set(POOL_V0_72)), 43)
        earlier = {card_id for key, pool in EXTRACT.items() if key.startswith("pool_v0_") and key not in ("pool_v0_72", "pool_v0_73", "pool_v0_74", "pool_v0_75", "pool_v0_76", "pool_v0_77", "pool_v0_78", "pool_v0_79", "pool_v0_80", "pool_v0_81", "pool_v0_82", "pool_v0_83", "pool_v0_84", "pool_v0_85", "pool_v0_86", "pool_v0_87", "pool_v0_88") for card_id in pool}  # v0.73 の組はあとの版
        self.assertFalse(set(POOL_V0_72) & earlier)
        self.assertEqual(len(earlier), 713)
        self.assertFalse(set(POOL_V0_72) & set(E.EQUIVALENT_CARDS))
        self.assertFalse(set(POOL_V0_72) & set(E.REPRINT_CARDS))
        pool = load_card_pool()
        for card_id in POOL_V0_72:
            with self.subTest(card=card_id):
                self.assertTrue(pool.get(card_id).supported)
                self.assertEqual(CARDS[card_id]["category"], "pokemon")
                self.assertEqual(CARDS[card_id]["play_scope"], "standard")
                self.assertFalse(CARDS[card_id]["pokemon"]["powers"])

    def test_counts_from_the_registry(self):
        pool = load_card_pool()
        registry = E.DEFAULT_EFFECTS
        later = set(EXTRACT["pool_v0_73"]) | set(EXTRACT["pool_v0_74"]) | set(EXTRACT["pool_v0_75"]) | set(EXTRACT["pool_v0_76"]) | set(EXTRACT["pool_v0_77"]) | set(EXTRACT["pool_v0_78"]) | set(EXTRACT["pool_v0_79"]) | set(EXTRACT["pool_v0_80"]) | set(EXTRACT["pool_v0_81"]) | set(EXTRACT["pool_v0_82"]) | set(EXTRACT["pool_v0_83"]) | set(EXTRACT["pool_v0_84"]) | set(EXTRACT["pool_v0_85"]) | set(EXTRACT["pool_v0_86"]) | set(EXTRACT["pool_v0_87"]) | set(EXTRACT["pool_v0_88"])  # v0.78 の 13 枚も除く。 v0.76 の 24 枚も除く。 v0.75 の 15 枚も除く。 v0.73 の 18 枚・v0.74 の 13 枚（トレーナー）を除いて比べる
        playable = pool.playable_ids - later
        categories = [pool.get(c).category for c in playable]
        self.assertEqual(len(playable), 756)
        self.assertEqual(len(EXTRACT["cards"]) - len(later), 756)
        self.assertEqual((categories.count("pokemon"), categories.count("trainer"), categories.count("energy")), (546, 180, 30))
        self.assertEqual((len(registry.attack_keys()), len(registry.power_keys()), len([c for c in registry.trainer_ids() if c not in later]), len(registry.energy_ids())),
                         (1327, 119, 180, 19))  # v0.88 でポケモン 11 枚（ワザ 15・特殊能力 5）を加えた  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚（ワザ 14・特殊能力 12）を加えた  # v0.85 でポケモン 13 枚（ワザ 17・特殊能力 9）・ミラクルエネルギーを加えた  # v0.83 でポケモン 18 枚（ワザ 33）を加えた  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックのポケモン 50 枚（ワザ 77）を加えた（トレーナー 2 枚はあとの版として除く）  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.84 でポケモン 12 枚（ワザ 19・特殊能力 5）・ポケモン育て屋夫婦を加えた
        new = [k for k in registry.attack_keys() if k.card_id in POOL_V0_72]
        self.assertEqual(len(new), 77)
        self.assertEqual(len(new), sum(len(CARDS[c]["pokemon"]["attacks"]) for c in POOL_V0_72))

    def test_every_attack_is_registered_with_the_expected_implementation(self):
        registry = E.DEFAULT_EFFECTS
        seen = set()
        for (card_id, index), (cls, params) in EXPECTED.items():
            with self.subTest(card=card_id, attack=index):
                entry = registry.attack_entry(card_id, index)
                self.assertIs(type(entry.effect), cls)
                self.assertEqual({f.name: getattr(entry.effect, f.name) for f in dataclasses.fields(entry.effect)}, params)
                printed = CARDS[card_id]["pokemon"]["attacks"][index]
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                                 (printed["name"]["ja"], printed["text"]["ja"], printed["text"]["ja"], "kyuura data/cards.json"))
                seen.add((card_id, index))
        for card_id, index in DAMAGE_ONLY_ATTACKS:
            with self.subTest(card=card_id, attack=index):
                entry = registry.attack_entry(card_id, index)
                self.assertIs(entry.effect, E.DAMAGE_ONLY)
                self.assertIsNone(CARDS[card_id]["pokemon"]["attacks"][index]["text"]["ja"])
                seen.add((card_id, index))
        self.assertEqual(seen, {(k.card_id, k.attack_index) for k in registry.attack_keys() if k.card_id in POOL_V0_72})

    def test_new_types_are_kernel_programs_outside_the_v013_contract(self):
        for cls in NEW_TYPES:
            with self.subTest(cls=cls.__name__):
                self.assertIn(cls, programs.BUILDERS)
                self.assertIn(cls, ATTACK_TYPES_SINCE_V0_17)
                self.assertNotIn(cls, v013_checks.VERIFIED)
                self.assertIs(cls.resolve, E.AttackEffect.resolve)
        # おつきみは「おつかい」と同じ要素の、選べるカードの種類を変えたもの（コインなし）
        self.assertEqual(programs.BUILDERS[E.RevealBasicEnergyFromDeck](E.RevealBasicEnergyFromDeck()),
                         (programs.RevealTrainerFromDeck(local_coin=None, category="basic_energy"),))
        self.assertEqual(programs.BUILDERS[E.DamageAndOptionalFullDrain](E.DamageAndOptionalFullDrain())[1],
                         programs.Drain("damage", full=True, optional=True))

    def test_no_card_specific_branch_in_the_engine(self):
        sources = [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]
        for path in sources:
            text = path.read_text(encoding="utf-8")
            for card_id in POOL_V0_72:
                self.assertNotIn(f'"{card_id}"', text, path.name)

    def test_cards_released_after_the_rule_base_keep_their_dates(self):
        """PF3-009・NIP2-010・NIP2X-003・PRN-042 は 2000.02.14 版のあとに発売したカード（kyuura の released_after_rule_base）。発売日を変えずに持ち、のちのルール・
        ベイビィのルールを持ち込まない（v0.69 のイントロパック（neo）と同じ）。エアームドのタイプは「鋼」で、写しに「鋼」の基本エネルギーカードはない。"""
        sources = cs.load_sources()["cards"]
        for card_id in ("PF3-009", "NIP2-010", "NIP2X-003", "PRN-042"):
            self.assertIn("2000.02.14 版のあとに発売したカード", sources[card_id]["notes"])
        pool = load_card_pool()
        self.assertEqual(pool.get("PF3-009").pokemon_type, EnergyType.METAL)
        self.assertEqual(pool.get("PF3-009").attacks[1].cost, (EnergyType.METAL, EnergyType.COLORLESS, EnergyType.COLORLESS))
        metal = [c for c in pool.playable_ids if pool.get(c).category == "energy" and pool.get(c).is_basic_energy and pool.get(c).provides is EnergyType.METAL]
        self.assertEqual(metal, [])


class UnsupportedWithoutRegistrationTest(unittest.TestCase):
    """登録を除けば未対応にもどる。データ（文面・ダメージの形・コインの枚数）が登録と合わなければ未対応。"""

    def test_without_the_v072_registrations_the_cards_are_unsupported(self):
        keys = [k for k in E.DEFAULT_EFFECTS.attack_keys() if k.card_id in POOL_V0_72]
        registry = E.DEFAULT_EFFECTS.without_attacks("test-no-v072", keys)
        pool = pool_from_extract(read_extract(), registry)
        self.assertEqual([c for c in POOL_V0_72 if pool.get(c).supported], [])
        self.assertEqual(len(pool.playable_ids - set(EXTRACT["pool_v0_73"]) - set(EXTRACT["pool_v0_74"]) - set(EXTRACT["pool_v0_75"]) - set(EXTRACT["pool_v0_76"]) - set(EXTRACT["pool_v0_77"]) - set(EXTRACT["pool_v0_78"]) - set(EXTRACT["pool_v0_79"]) - set(EXTRACT["pool_v0_80"]) - set(EXTRACT["pool_v0_81"]) - set(EXTRACT["pool_v0_82"]) - set(EXTRACT["pool_v0_83"]) - set(EXTRACT["pool_v0_84"]) - set(EXTRACT["pool_v0_85"]) - set(EXTRACT["pool_v0_86"]) - set(EXTRACT["pool_v0_87"]) - set(EXTRACT["pool_v0_88"])), 713)  # v0.73 の 18 枚・v0.74 の 13 枚は除いて比べる

    def test_data_mismatch_makes_the_card_unsupported(self):
        def text(card_id, index, value):
            return card_id, lambda c: c["pokemon"]["attacks"][index]["text"].__setitem__("ja", value)

        def damage(card_id, index, value):
            return card_id, lambda c: c["pokemon"]["attacks"][index].__setitem__("damage", value)

        cases = [
            text("PRN-042", 0, "コインを3枚投げ、「おもて」の数×20のダメージを追加する。"),
            text("PRN-042", 0, "コインを2枚投げ、「おもて」の数×20のダメージ。"),
            text("GD4-003", 0, "相手を「ねむり」状態にする。その後、自分も「ねむり」状態になる。"),
            text("GD4-003", 1, "ダメージを与えた後、相手を「こんらん」状態にする。"),
            text("GD4-007", 0, "相手を「どく」状態にする。"),
            damage("GD4-007", 0, {"base": 10, "modifier": None, "display": "10"}),
            text("GD6-012", 1, "相手を「マヒ」状態から、回復させる。"),
            text("ES1-009", 0, "相手にダメージを与えたら、与えたぶんのダメージカウンターを、このカードから取りのぞく。"),
            text("GD3-010", 1, "自分についている「雷」エネルギーカードを1枚選んではがす。その後、自分に控えポケモンがいれば1匹を選び、はがしたエネルギーをそれにつける。"),
            text("GD4-012", 0, "自分の山札から「エネルギーカード」1枚を選び出し、相手に見せてから、手札に加えてよい。その後、その山札をよく切る。"),
            text("GD1-012", 0, "相手の対戦ポケモンを控えポケモンと入れ替える。入れ替わるポケモンは相手が選ぶ。"),
            # 書き方を加えた既存の型（引数と結びつけた書き方だけ）
            text("ES1-006", 0, "コインを投げて「おもて」なら、このワザを受けた相手は、次の自分の番にワザを使えない。"),
            text("ES2-023", 0, "「うら」が出るまでコインを投げ続け、その間に出た「おもて」の数×10ダメージ。"),
            text("ES2-023", 1, "自分の控えポケモン全員にも、(「弱点・抵抗力」に関係なく)それぞれ20ダメージ。"),
            text("ES2-024", 1, "コインを投げて「おもて」なら、このワザを受けた相手は、次の相手の番で「にげる」ことができる。"),
            text("ES2-027", 0, "コインを投げて「おもて」なら、相手の控えポケモンから1匹を選び、そのポケモンにも(「弱点・抵抗力」に関係なく)20ダメージ。"),
            text("ES1-019", 1, "コインを投げて「おもて」なら、このカードは次の相手の番で、ワザによるダメージを受けない。"),
            text("GD4-009", 0, "自分についているエネルギーの数だけコインを投げ、「おもて」の数×20のダメージ。"),
        ]
        for card_id, change in cases:
            with self.subTest(card=card_id, change=change):
                self.assertTrue(load_card_pool().get(card_id).supported)
                self.assertFalse(modified_pool(card_id, change).get(card_id).supported)

    def test_new_types_reject_other_forms(self):
        pool = load_card_pool()
        self.assertTrue(E.CoinsHeadsTimesBonusDamage(3, 20).check(pool.get("PRN-042").attacks[0]))
        self.assertTrue(E.CoinFlipDamage(2, 20).check(pool.get("PRN-042").attacks[0]))  # 目安が「+」
        self.assertTrue(E.DamageThenConfuseBoth().check(pool.get("GD4-003").attacks[1]))  # 「ダメージを与えた後」の書き方は別の型
        self.assertTrue(E.DamageThenStatusSelfAndOpponent(SLEEP).check(pool.get("GD4-003").attacks[1]))
        self.assertTrue(E.DamageAndFullDrain().check(pool.get("ES1-009").attacks[0]) == [])  # v0.32 の型は形だけを確かめる（使わない。いつも取りのぞく）
        self.assertTrue(E.DamageAndOptionalFullDrain().check(pool.get("PMCG2-004").attacks[1]))  # 「…自分からとりのぞく。」は取りのぞいてよいではない
        self.assertTrue(E.DamageAndForceSwitch().check(pool.get("GD1-012").attacks[0]) == [])  # 形だけを確かめる型（Z23 を見落とすので使わない）
        self.assertTrue(E.DamageThenForceSwitchAfterDamage().check(pool.get("GD5-005").attacks[0]))
        self.assertTrue(E.DamageThenMoveOneEnergyToBench(EnergyType.WATER).check(pool.get("GD3-010").attacks[1]))
        self.assertTrue(E.SearchTrainerOnHeads().check(pool.get("GD4-012").attacks[0]))
        with self.assertRaises(ValueError):
            E.CoinsHeadsTimesBonusDamage(1, 20)
        with self.assertRaises(ValueError):
            E.DamageThenStatusSelfAndOpponent("burn")


class SharedEntriesTest(unittest.TestCase):
    """処理に使う欄が同じ v0.72 のカード（SAME_DATA_CARDS_V0_72。10 枚）は、登録の値を共有する（マチスの秘策の確かめでは 1 枚で代表する）。"""

    def test_twins_have_the_same_data_and_share_entries(self):
        pool = load_card_pool()
        self.assertEqual(dict(E.SAME_DATA_CARDS_V0_72), SAME)
        self.assertFalse(set(E.SAME_DATA_CARDS_V0_72) & set(E.SAME_DATA_CARDS_V0_70))
        for new, original in E.SAME_DATA_CARDS_V0_72.items():
            with self.subTest(card=new):
                self.assertEqual(cs.engine_view(CARDS[new]), cs.engine_view(CARDS[original]))
                self.assertEqual(engine_module._behavior_key(pool, new), engine_module._behavior_key(pool, original))
                for a in pool.get(new).attacks:
                    self.assertIs(E.DEFAULT_EFFECTS.attack_entry(new, a.index), E.DEFAULT_EFFECTS.attack_entry(original, a.index))
        others = [c for c in POOL_V0_72 if c not in E.SAME_DATA_CARDS_V0_72]
        views = [repr(cs.engine_view(CARDS[c])) for c in others]
        self.assertEqual(len(views), len(set(views)))  # ほかに同じデータの組はない


# ---------------------------------------------------------------- エアロブラスト（CoinsHeadsTimesBonusDamage）


class AeroblastTest(unittest.TestCase):

    def test_two_coins_add_20_per_heads(self):
        for sides, amount in (((T, T), 20), ((H, T), 40), ((T, H), 40), ((H, H), 60)):
            with self.subTest(sides=sides):
                state = board(mon("PRN-042", (W, W, W)), mon(RATTATA, (W,)))
                done = audited(self, attack(state, 0, *sides))
                since = len(state.log)
                self.assertEqual([e["amount"] for e in events(done, since, "damage")], [amount])
                self.assertEqual(len(events(done, since, "coin_flip")), 2)
                self.assertEqual(events(done, since, "attack_failed"), [])

    def test_damage_profile_and_preflight(self):
        state = board(mon("PRN-042", (W, W, W)))
        effect = E.DEFAULT_EFFECTS.attack_entry("PRN-042", 0).effect
        use = E.AttackUse(0, state.players[0].active.pokemon_id, AttackKey("PRN-042", 0))
        self.assertEqual(effect.damage_profile(state, use).opponent, (20, 40, 60))
        for sides in ((H, H), (T, H), (T, T)):
            same_in_every_mode(self, state, 0, sides)

    def test_prevented_damage_stops_before_the_coins(self):
        state = board(mon("PRN-042", (W, W, W)), prevented())
        assert_stops(self, state, UseAttack(0, 0), "UNRESOLVED_PREVENTED_COIN_DAMAGE")


# ---------------------------------------------------------------- ゆめみのまい・くさいにおい（DamageThenStatusSelfAndOpponent）


class SelfAndOpponentStatusTest(unittest.TestCase):

    def test_both_get_the_condition_after_damage(self):
        for index, condition in ((0, SLEEP), (1, CONFUSION)):
            with self.subTest(condition=condition):
                state = board(mon("GD4-003", (G, G, G)))
                done = audited(self, attack(state, index))
                since = len(state.log)
                kinds = [e["kind"] for e in done.log[since:]]
                self.assertLess(kinds.index("damage"), kinds.index("special_condition"))
                applied = [(e["player"], e["condition"]) for e in events(done, since, "special_condition")]
                self.assertEqual(applied, [(0, condition), (1, condition)])  # 説明の「自分と相手」の順

    def test_dream_dance_makes_both_actives_asleep_and_the_pokemon_check_halts(self):
        """ゆめみのまいで両方の対戦ポケモンがねむりになると、そのあとのポケモンチェックのねむりのコインを投げる順番が決まらない（v0.3b の既存の未解決
        UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER）。コインの前に対戦を止める（v0.72 で新しく決めたことではない）。"""
        state = board(mon("GD4-003", (G, G, G)))
        done = audited(self, attack(state, 0))
        self.assertEqual(done.phase.name, "HALTED")
        self.assertEqual([e["code"] for e in events(done, len(state.log), "halted")], ["UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER"])
        self.assertEqual(events(done, len(state.log), "coin_flip"), [])

    def test_no_damage_stops_as_z23(self):
        state = board(mon("GD4-003", (G, G, G)), prevented())
        assert_stops(self, state, UseAttack(0, 0), "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE")

    def test_knocked_out_opponent_gets_nothing_but_the_attacker_does(self):
        state = board(mon("GD4-003", (G, G, G)), mon(RATTATA, (W,), damage=30))
        done = audited(self, attack(state, 1))
        applied = [(e["player"], e["condition"]) for e in events(done, len(state.log), "special_condition")]
        self.assertEqual(applied, [(0, CONFUSION)])

    def test_every_preflight_mode_gives_the_same_result(self):
        same_in_every_mode(self, board(mon("GD4-003", (G, G, G)), mon(RATTATA, (W,))), 1, ())


# ---------------------------------------------------------------- ねむけどく（PoisonAndSleepWithoutDamage）


class PoisonAndSleepTest(unittest.TestCase):

    def test_poison_and_sleep_without_damage(self):
        state = board(mon("GD4-007", (G, G)))
        done = audited(self, attack(state, 0, T))  # 番の終わりのポケモンチェックのねむりのコインは「うら」
        since = len(state.log)
        self.assertEqual(events(done, since, "damage"), [])
        self.assertEqual([e["condition"] for e in events(done, since, "special_condition")], [POISON, SLEEP])
        target = done.players[1].active
        self.assertIsNotNone(target.conditions.poison)
        self.assertTrue(target.conditions.asleep)

    def test_barrier_blocks_both(self):
        state = build_test_state([{"active": mon("PMCG1-050", (P, P, P)), "bench": [RATTATA]}, {"active": mon("GD4-007", (G, G)), "bench": [RATTATA]}],
                                 turn_number=TURN)
        state = apply_kernel(state, UseAttack(0, 1))
        if state.decision is not None:
            state = answer(state, state.decision.options[:1])
        self.assertTrue(any(type(e) is AttackBarrier for e in state.players[0].active.persistent_effects))
        done = audited(self, attack(state, 0, player=1))
        self.assertEqual(events(done, len(state.log), "special_condition"), [])


# ---------------------------------------------------------------- めざめのキッス（DamageThenWakeOpponent）


class WakeUpKissTest(unittest.TestCase):

    def test_sleep_is_removed_and_poison_stays(self):
        state = board(mon("GD6-012", (P, P)), mon(RATTATA, (W,), sleep=True, poison=10))
        done = audited(self, attack(state, 1))
        target = done.players[1].active
        self.assertFalse(target.conditions.asleep)
        self.assertIsNotNone(target.conditions.poison)
        removed = events(done, len(state.log), "special_conditions_removed")
        self.assertEqual([(e["conditions"], e["reason"], e["effect"]) for e in removed], [(("sleep",), "cured", "GD6-012#1")])

    def test_not_asleep_means_nothing_to_do(self):
        for extra in ({}, {"confusion": True}):
            with self.subTest(extra=extra):
                state = board(mon("GD6-012", (P, P)), mon(RATTATA, (W,), **extra))
                done = audited(self, attack(state, 1))
                self.assertEqual(events(done, len(state.log), "special_conditions_removed"), [])
                self.assertEqual(done.players[1].active.conditions, state.players[1].active.conditions)

    def test_knocked_out_target_is_not_woken(self):
        state = board(mon("GD6-012", (P, P)), mon(RATTATA, (W,), sleep=True, damage=30))
        done = audited(self, attack(state, 1))
        self.assertEqual(events(done, len(state.log), "special_conditions_removed"), [])


# ---------------------------------------------------------------- きゅうけつ（DamageAndOptionalFullDrain）


class OptionalDrainTest(unittest.TestCase):

    def waiting(self):
        state = board(mon("ES1-009", (G, G, G), damage=30), mon(RATTATA, (W,)))
        return state, attack(state, 0)

    def test_attacker_chooses_whether_to_remove(self):
        state, waiting = self.waiting()
        d = waiting.decision
        attacker = state.players[0].active.pokemon_id
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices, d.options, d.resume), (OPTIONAL_DRAIN, 0, 0, 1, (attacker,), "attack"))
        self.assertEqual((d.context_value("dealt"), d.context_value("counters")), (20, 2))
        audited(self, waiting)
        yes = audited(self, answer(waiting, (attacker,)))
        self.assertEqual(yes.players[0].active.damage, 10)
        self.assertEqual([e["counters"] for e in events(yes, len(waiting.log), "drain_heal")], [2])
        no = audited(self, answer(waiting, ()))
        self.assertEqual(no.players[0].active.damage, 30)
        self.assertEqual([(e["dealt"], e["drain_counters"]) for e in events(no, len(waiting.log), "drain_heal_declined")], [(20, 2)])
        self.assertEqual(events(no, len(waiting.log), "drain_heal"), [])
        self.assertEqual(yes.current_player, 1)

    def test_no_counters_on_the_attacker_means_no_decision(self):
        state = board(mon("ES1-009", (G, G, G)), mon(RATTATA, (W,)))
        done = audited(self, attack(state, 0))
        self.assertIsNone(done.decision)
        self.assertEqual([e["counters"] for e in events(done, len(state.log), "drain_heal")], [0])

    def test_no_damage_dealt_means_no_decision(self):
        state = board(mon("ES1-011", (G, G, G), damage=30), prevented())
        done = audited(self, attack(state, 1))
        self.assertIsNone(done.decision)
        self.assertEqual(done.players[0].active.damage, 30)

    def test_invalid_answers_change_nothing(self):
        _, waiting = self.waiting()
        before = snapshot(waiting)
        for choice in ((waiting.players[0].bench[0].pokemon_id,), tuple(waiting.decision.options) * 2):
            with self.subTest(choice=choice), self.assertRaises(IllegalActionError):
                answer(waiting, choice)
            self.assertEqual(snapshot(waiting), before)
        with self.assertRaises(IllegalActionError):
            apply_kernel(waiting, ResolveDecision(1, waiting.decision.id, ()))
        self.assertEqual(snapshot(waiting), before)

    def test_save_and_restore_while_waiting(self):
        _, waiting = self.waiting()
        data = full(waiting)
        for copied in (waiting.clone(), copy.deepcopy(waiting), pickle.loads(pickle.dumps(waiting))):
            self.assertEqual(full(copied), data)
            for choice in ((), waiting.decision.options):
                self.assertEqual(full(answer(copied, choice)), full(answer(waiting, choice)))
        self.assertEqual(serialization_problems(waiting), [])

    def test_every_preflight_mode_gives_the_same_result(self):
        state = board(mon("ES1-009", (G, G, G), damage=30), mon(RATTATA, (W,)))
        results = {mode: full(answer(attack(state, 0, mode=mode), (), mode=mode)) for mode in PREFLIGHT_MODES}
        self.assertEqual(len({repr(r) for r in results.values()}), 1)


# ---------------------------------------------------------------- デンキとばし（DamageThenMoveOneEnergyToBench）


class MoveOneEnergyTest(unittest.TestCase):

    def test_choose_a_card_then_a_bench_pokemon(self):
        state = board(mon("GD3-010", (L, L, W)), bench=(RATTATA, "PMCG1-035"))
        first = audited(self, attack(state, 1))
        lightning = tuple(u for u in state.players[0].active.energy if state.cards[u].card_id == L)
        d = first.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices, d.context_value("stage")), (MOVE_ENERGY, 0, lightning, 1, 1, "energy"))
        self.assertEqual([e["amount"] for e in events(first, len(state.log), "damage")], [20])
        second = audited(self, answer(first, (lightning[1],)))
        d = second.decision
        bench = tuple(p.pokemon_id for p in state.players[0].bench)
        self.assertEqual((d.kind, d.player, d.options, d.context_value("stage"), d.context_value("energy")), (ATTACH_TO_BENCH, 0, bench, "bench", lightning[1]))
        self.assertIn(lightning[1], second.players[0].active.energy)  # 決定のあいだはついたまま
        done = audited(self, answer(second, (bench[1],)))
        self.assertNotIn(lightning[1], done.players[0].active.energy)
        self.assertEqual(done.players[0].bench[1].energy, [lightning[1]])
        self.assertEqual(done.energy_attachments_this_turn, state.energy_attachments_this_turn)
        self.assertEqual([e["energy"] for e in events(done, len(state.log), "attack_attach_energy")], [lightning[1]])

    def test_without_bench_the_card_is_discarded(self):
        state = board(mon("GD3-010", (L, L)), bench=())
        first = attack(state, 1)
        card = first.decision.options[0]
        done = audited(self, answer(first, (card,)))
        self.assertIn(card, done.players[0].discard)
        self.assertEqual([e["reason"] for e in events(done, len(state.log), "discard_energy")], ["no_bench"])

    def test_transparent_bench_pokemon_sends_the_card_to_the_discard(self):
        state = board(mon("GD3-010", (L, L)), bench=(mon(HAUNTER, evolved_from="PMCG3-029"),))
        second = answer(attack(state, 1), (state.players[0].active.energy[0],))
        done = audited(self, answer(with_coin_results(second, H), second.decision.options))
        self.assertEqual(done.players[0].bench[0].energy, [])
        self.assertEqual([e["reason"] for e in events(done, len(second.log), "discard_energy")], ["evaded"])

    def test_rainbow_energy_stops_before_choosing(self):
        state = board(mon("GD3-010", (L, RAINBOW)))
        assert_stops(self, state, UseAttack(0, 1), "UNRESOLVED_RAINBOW_ENERGY_TYPE")

    def test_invalid_answers_change_nothing(self):
        state = board(mon("GD3-010", (L, L, W)))
        first = attack(state, 1)
        water = next(u for u in state.players[0].active.energy if state.cards[u].card_id == W)
        before = snapshot(first)
        for choice in ((water,), (), tuple(first.decision.options)):
            with self.subTest(choice=choice), self.assertRaises(IllegalActionError):
                answer(first, choice)
            self.assertEqual(snapshot(first), before)
        second = answer(first, first.decision.options[:1])
        before = snapshot(second)
        with self.assertRaises(IllegalActionError):
            answer(second, (second.players[0].active.pokemon_id,))
        self.assertEqual(snapshot(second), before)

    def test_save_and_restore_between_the_decisions(self):
        state = board(mon("GD3-010", (L, L)))
        second = answer(attack(state, 1), state.players[0].active.energy[:1])
        data = full(second)
        for copied in (second.clone(), copy.deepcopy(second), pickle.loads(pickle.dumps(second))):
            self.assertEqual(full(copied), data)
            self.assertEqual(full(answer(copied, second.decision.options)), full(answer(second, second.decision.options)))
        self.assertEqual(serialization_problems(second), [])


# ---------------------------------------------------------------- おつきみ（RevealBasicEnergyFromDeck）


class MoonGazeTest(unittest.TestCase):

    def test_reveal_a_basic_energy_card_or_decline(self):
        state = board(mon("GD4-012", (W,)), deck=[RATTATA, W, G, DCE, "PMCG1-073"])
        waiting = audited(self, attack(state, 0))
        d = waiting.decision
        basics = tuple(sorted(u for u in state.players[0].deck if state.cards[u].card_id in (W, G)))
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices, d.options), (SEARCH_DECK, 0, 0, 1, basics))
        took = audited(self, answer(waiting, basics[:1]))
        self.assertIn(basics[0], took.players[0].hand)
        since = len(waiting.log)
        self.assertEqual([e["card"] for e in events(took, since, "reveal_from_deck")], [basics[0]])
        self.assertEqual(len(events(took, since, "shuffle")), 1)
        none = audited(self, answer(waiting, ()))
        self.assertEqual([e["category"] for e in events(none, since, "reveal_from_deck_declined")], ["basic_energy"])
        self.assertEqual(len(events(none, since, "shuffle")), 1)

    def test_no_basic_energy_in_the_deck(self):
        state = board(mon("GD4-012", (W,)), deck=[RATTATA, DCE])
        done = audited(self, attack(state, 0))
        self.assertIsNone(done.decision)
        since = len(state.log)
        self.assertEqual([e["category"] for e in events(done, since, "reveal_from_deck_none")], ["basic_energy"])
        self.assertEqual(len(events(done, since, "shuffle")), 1)


# ---------------------------------------------------------------- つのでなげる・ふりとばす（入れ替えるポケモンは相手が選ぶ）


class SwitchTest(unittest.TestCase):

    def test_opponent_chooses_after_damage(self):
        for card_id, index, energy in (("GD1-012", 0, (F, F)), ("GD5-005", 0, (R,))):
            with self.subTest(card=card_id):
                state = board(mon(card_id, energy), opponent_bench=(RATTATA, "PMCG1-035"))
                waiting = audited(self, attack(state, index))
                d = waiting.decision
                self.assertEqual((d.kind, d.player), (FORCED_SWITCH, 1))
                done = audited(self, answer(waiting, d.options[1:]))
                self.assertEqual(done.players[1].active.pokemon_id, d.options[1])

    def test_no_damage_stops_only_the_after_damage_wording(self):
        state = board(mon("GD1-012", (F, F)), prevented())
        assert_stops(self, state, UseAttack(0, 0), "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE")
        state = board(mon("GD1-012", (F, F)), prevented(), opponent_bench=())
        done = audited(self, attack(state, 0))  # 控えがいなければ、どちらの読み方でも入れ替えない
        self.assertIsNone(done.decision)
        state = board(mon("GD5-005", (R,)), prevented())
        self.assertEqual(attack(state, 0).decision.kind, FORCED_SWITCH)  # ふりとばすは「ダメージを与えた後」と書かない


# ---------------------------------------------------------------- 書き方を加えた既存の型・そのほかの再利用


class ReusedTypeTest(unittest.TestCase):

    def test_continuous_rock_throw_first_tails_is_zero_not_a_failure(self):
        state = board(mon("ES2-023", (F, F)))
        done = audited(self, attack(state, 0, T))
        since = len(state.log)
        self.assertEqual(events(done, since, "attack_failed"), [])
        self.assertEqual(len(events(done, since, "coin_flip")), 1)
        state = board(mon("ES2-023", (F, F)))
        done = audited(self, attack(state, 0, H, H, T))
        self.assertEqual([e["amount"] for e in events(done, len(state.log), "damage")], [40])

    def test_earthquake_states_weakness_resistance_and_does_not_ask_js1(self):
        weak = "PMCG1-035"  # ピカチュウ（弱点 闘）
        state = board(mon("ES2-023", (F, F, F)), mon(RATTATA, (W,)), bench=(weak,))
        done = audited(self, attack(state, 1))
        bench = [e for e in events(done, len(state.log), "damage") if e.get("target") == E.SELF_BENCH]
        self.assertEqual([e["amount"] for e in bench], [10])

    def test_self_damage_on_tails_and_no_damage_to_the_opponent(self):
        state = board(mon("ES1-009", (G, G, G, G)), mon(RATTATA, (W,)))
        done = audited(self, attack(state, 1, T))
        self.assertEqual([(e["player"], e["amount"]) for e in events(done, len(state.log), "damage")], [(1, 60), (0, 40)])
        state = board(mon("ES3-003", (G, G)), mon(RATTATA, (W,)))
        done = audited(self, attack(state, 0, T))
        self.assertEqual([(e["player"], e["amount"]) for e in events(done, len(state.log), "damage")], [(0, 20)])
        self.assertEqual(events(done, len(state.log), "attack_failed"), [])

    def test_dizzy_heads_paralyzes_and_tails_sleeps(self):
        for side, condition in ((H, PARALYSIS), (T, SLEEP)):
            with self.subTest(side=side):
                state = board(mon("GD2-002", (W,)))
                done = audited(self, attack(state, 0, side))
                self.assertEqual([e["condition"] for e in events(done, len(state.log), "special_condition")], [condition])
                self.assertEqual(events(done, len(state.log), "damage"), [])

    def test_locks_reuse_existing_persistent_effects(self):
        state = board(mon("ES1-025", (W,)))
        done = audited(self, attack(state, 1, H))
        self.assertTrue(any(type(e) is CannotAttack for e in done.players[1].active.persistent_effects))
        state = board(mon("ES2-024", (F, F)))
        done = audited(self, attack(state, 1, H))
        self.assertTrue(any(type(e) is CannotRetreat for e in done.players[1].active.persistent_effects))
        state = board(mon("ES3-008", (G, G)))
        done = audited(self, attack(state, 0))
        self.assertTrue(any(type(e) is CannotUseOwnAttack for e in done.players[0].active.persistent_effects))

    def test_dragon_rage_fails_unless_both_heads(self):
        for sides, amount in (((H, H), [50]), ((H, T), []), ((T, T), [])):
            with self.subTest(sides=sides):
                state = board(mon("PR1-036", (W, W)))
                done = audited(self, attack(state, 1, *sides))
                self.assertEqual([e["amount"] for e in events(done, len(state.log), "damage")], amount)
                self.assertEqual(bool(events(done, len(state.log), "attack_failed")), not amount)

    def test_egg_toss_counts_energy_units(self):
        """たまなげ: コインの数はついているエネルギーの個数（無色2個エネルギーは 2 個。v0.35 の「おもて」の数でまとめる先読み）。"""
        state = board(mon("GD4-009", (DCE, G)), mon(RATTATA, (W,)))
        done = audited(self, attack(state, 0, H, H, T))
        since = len(state.log)
        self.assertEqual(len(events(done, since, "coin_flip")), 3)
        self.assertEqual([e["amount"] for e in events(done, since, "damage")], [20])

    def test_agility_needs_metal_energy_and_works_through_transform(self):
        """エアームドの「こうそくいどう」の必要なエネルギーの「鋼」を出す基本エネルギーカードは写しにない。［へんしん］のメタモン（どの色のエネルギーとしても使える）が
        写したときに使える。"""
        state = build_test_state([{"active": mon(DITTO, (W, W, W)), "bench": [RATTATA]}, {"active": mon("PF3-009", (W,)), "bench": [RATTATA]}],
                                 turn_number=TURN)
        done = audited(self, attack(state, 1, H))
        self.assertTrue(any(type(e) is AttackBarrier for e in done.players[0].active.persistent_effects))

    def test_every_preflight_mode_gives_the_same_result(self):
        cases = [(board(mon("ES2-027", (F,)), mon(RATTATA, (W,))), 0), (board(mon("GD2-002", (W,))), 0), (board(mon("PR1-036", (W, W))), 1),
                 (board(mon("ES1-009", (G, G, G, G)), mon(RATTATA, (W,))), 1), (board(mon("GD4-009", (DCE, G)), mon(RATTATA, (W,))), 0)]
        for state, index in cases:
            for sides in ((H, H, H), (T, T, T), (H, T, H)):
                with self.subTest(card=state.cards[state.players[0].active.card].card_id, sides=sides):
                    same_in_every_mode(self, state, index, sides)


# ---------------------------------------------------------------- 記録・マチスの秘策・カツラのクイズ


class RecordTest(unittest.TestCase):

    def test_adoption_records(self):
        sources = cs.load_sources()["cards"]
        links = cs.load_links()
        printed = set(links["latest_descriptions"]["adopted_printed_text"])
        for card_id in POOL_V0_72:
            with self.subTest(card=card_id):
                record = sources[card_id]
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["recorded_on"], record["kyuura_records"], record["issues"]),
                                 ("kyuura_data", "adopted", EXTRACT["source"]["commit"], "2026-10-19", [], []))
                self.assertEqual(record["external_checks"], [])  # 日本語の文面は pcg-search.com の転記。新しい外部照合はしていない
                targets = {f"attack/{i}" for i, a in enumerate(CARDS[card_id]["pokemon"]["attacks"]) if a["text"]["ja"] is not None}
                self.assertEqual(set(record["play_text"]), targets)
                self.assertTrue(all(v == "kyuura_printed_text" for v in record["play_text"].values()))
                self.assertTrue({f"{card_id}/{t}" for t in targets} <= printed)
        self.assertEqual(cs.problems(), [])


class SecretPlanCandidatesTest(unittest.TestCase):
    """マチスの秘策の受け付けるかの確かめで試すカード: 公開の情報（対応しているカードの一覧）だけから作る。v0.72 のカードが加わり、ありうるカードの種類が増えた
    （同じデータの 10 枚は 1 枚で代表する）。数は固定しない（カードを加えるたびに変わる）。上限（512）は変えていない。"""

    def test_candidates(self):
        pool = load_card_pool()
        candidates = engine_module._identity_candidates(pool)
        self.assertEqual(set(candidates) & set(POOL_V0_72), set(POOL_V0_72) - set(E.SAME_DATA_CARDS_V0_72))
        self.assertFalse(set(candidates) & set(E.EQUIVALENT_CARDS))
        self.assertFalse(set(candidates) & set(E.SAME_DATA_CARDS_V0_70))
        basics = [c for c in candidates if pool.get(c).is_basic_pokemon]
        self.assertEqual(engine_module._IDENTITY_TRIAL_LIMIT, 512)
        # 1 枚を指定するコマンドの試す回数: 割り当てる前 1 回 + たねポケモン + 「たねポケモンでない」1（トラッシュしたあとに項目を読まなければ）
        self.assertLessEqual(1 + len(basics) + 1, engine_module._IDENTITY_TRIAL_LIMIT)


class QuizNamesTest(unittest.TestCase):
    """カツラのクイズ その3の答えの候補（同梱のカードのデータのポケモンの名前）に、v0.72 で新しい名前 3 つ（エアームド・テッポウオ・ルギア）が加わった。"""

    def test_new_names(self):
        state = build_test_state([{"active": "PMCG1-018"}, {"active": "PMCG1-018"}])
        names = E.quiz_answer_names(state)
        self.assertEqual(len(names), len(set(names)))
        earlier = {CARDS[c]["name"]["ja"] for c in CARDS if c not in POOL_V0_72 and c not in EXTRACT["pool_v0_77"] and c not in EXTRACT["pool_v0_78"] and c not in EXTRACT["pool_v0_79"] and c not in EXTRACT["pool_v0_82"] and c not in EXTRACT["pool_v0_83"] and c not in EXTRACT["pool_v0_84"] and c not in EXTRACT["pool_v0_85"] and c not in EXTRACT["pool_v0_86"] and CARDS[c]["category"] == "pokemon"}  # v0.79 のテッポウオ（neo3-016）・v0.77 のテッポウオ（neo4-030）・v0.78 のエアームド（neo1-058・NIP1X-005）はあとの版
        new = sorted({CARDS[c]["name"]["ja"] for c in POOL_V0_72} - earlier)
        self.assertEqual(new, ["エアームド", "テッポウオ", "ルギア"])
        for name in new:
            self.assertIn(name, names)


# ---------------------------------------------------------------- 正式な対戦開始からの対戦


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）から、v0.72 のカードと前の版のカードを混ぜたデッキ（tools/existing_effect_games.py の F72・G72・C72）。
    決まった seed・席の入れかえ。勝敗は判断に使わない。"""

    @classmethod
    def setUpClass(cls):
        from tools import existing_effect_games as games

        cls.games = games
        cls.results = games.run(range(2), pairings=games.PAIRINGS_V0_72)

    def test_games_finish_without_audit_failures(self):
        total = 0
        for name, run in self.results.items():
            for game in run["games"]:
                total += 1
                with self.subTest(run=name, seed=game["seed"]):
                    self.assertIn(game["outcome"], ("game_over", "sudden_death", "halted"), game.get("error"))
                    self.assertEqual(game["audit"], {})
        self.assertGreaterEqual(total, 12)
        self.assertLessEqual(total, 24)

    def test_decks_mix_new_and_earlier_ids(self):
        for label in ("F72", "G72", "C72"):
            deck = self.games.deck_cards(label)
            self.assertTrue(set(deck) & set(POOL_V0_72))
            self.assertTrue(set(deck) - set(POOL_V0_72))
            self.assertEqual(deck_problems(deck), [])

    def test_new_attacks_are_used(self):
        used = set()
        for run in self.results.values():
            for game in run["games"]:
                for card, uses in game.get("card_uses", {}).items():
                    used |= {(card, int(k.split("#")[1])) for k in uses if re.fullmatch(r"attack#\d", k)}
        self.assertTrue({k for k in used if k[0] in POOL_V0_72})


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = DOC.read_text(encoding="utf-8")
        for card_id in POOL_V0_72:
            self.assertIn(card_id, text)
        for cls in NEW_TYPES:
            self.assertIn(cls.__name__, text)
        for word in ("SAME_DATA_CARDS_V0_72", "FH2", "PD2", "UNRESOLVED_FULL_HEAL_WITHOUT_CONDITION", "UNRESOLVED_POKEDEX_UP_TO_ZERO"):
            self.assertIn(word, text)
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        self.assertIn("UNRESOLVED_POKEDEX_UP_TO_ZERO", links["stop_codes"])


if __name__ == "__main__":
    unittest.main()
