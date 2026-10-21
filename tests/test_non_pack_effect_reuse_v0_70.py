"""v0.70（docs/non-pack-effect-reuse-v0.70.md）: 拡張パック以外の商品のポケモン 82 枚（kyuura data/engine_targets.json の reuse_candidate。写しの組 pool_v0_70）。

- どのワザも既存の効果の型の登録（同じ文面の既存の登録と、ダメージの目安の有無・コインの枚数・追加の量・必要なエネルギーで型とパラメーターを選ぶ）と、ダメージのない
  小さな型 2 つ（StatusByCoinWithoutDamage。ニョロゾの「ぐるぐる」・AttachEnergyFromDiscardToSelf。マチスのピカチュウの「たいでん」）。こうそくいどう（カツラの
  ポニータ・レディバ）は DamageThenSelfBarrierOnHeads に説明の書き方を 1 通り加えた。処理に使う文面は kyuura の印刷の文面（kyuura データの採用。研究の基準のコミット
  7d3f4ca に、これらのカードを指す LD-・CC-・CR-・UQ-・エラッタはない）
- 必要なエネルギーが「水」だけのみずでっぽう・ハイドロポンプ 6 つは v0.6 の ExtraEnergyDamage（第4弾のコダックの同じ文面の ExtraEnergyDamageMixed を写さない）
- PR1-069 の名前は、写しの作り直しで利用者が示した訂正「？？？」→「ミュウ」を当てはめる（scripts/extract_kyuura_cards.py の ENGINE_USER_CORRECTIONS。kyuura の記録ではない。
  訂正したのは名前だけ）。同じ名前 4 枚の制限で、ほかのミュウと同じ名前として数える
- 82 枚のうち 12 枚は、ほかの v0.70 のカードと処理に使う欄が同じ（effects.SAME_DATA_CARDS_V0_70。登録の値を共有する）。v0.69 の EQUIVALENT_CARDS には入れない

盤面を直接作るテスト（build_test_state）は 1 か所の規定を確かめるためだけに使い、正式な対戦開始からの対戦は GameTest（tools/existing_effect_games.py の
--batch v0.70）が確かめる。
"""

from __future__ import annotations

import copy
import dataclasses
import importlib.util
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
from kyuura_engine.conditions import CONFUSION, SLEEP
from kyuura_engine.decisions import ATTACH_FROM_DISCARD
from kyuura_engine.deck import DeckValidationError, deck_problems, validate_deck
from kyuura_engine.effects import AttackKey
from kyuura_engine.resolution import PREFLIGHT_MODES, programs, v013_checks
from kyuura_engine.state import AttackBarrier
from scripts import check_card_sources as cs
from tests.helpers import (
    ATTACK_TYPES_SINCE_V0_17,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import serialization_problems

ROOT = Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
DOC = ROOT / "docs" / "non-pack-effect-reuse-v0.70.md"
EXTRACT = read_extract()
CARDS = {c["id"]: c for c in EXTRACT["cards"]}
POOL_V0_70 = tuple(EXTRACT["pool_v0_70"])
H, T = CoinSide.HEADS, CoinSide.TAILS
W, L, G, P, F, R = "PMCG1-099", "PMCG1-100", "PMCG1-097", "PMCG1-101", "PMCG1-102", "PMCG1-098"
RAINBOW, DCE = "PMCG4-065", "PMCG1-096"
HITMONCHAN, MEWTWO, RATTATA, MISTYS_TENTACOOL = "PMCG1-058", "PMCG1-050", "PMCG1-060", "PMCG5-030"
MEW = "PMCG3-033"
ANCIENT_MEW = "PR1-069"
POLIWAG, POLIWHIRL, POLIWRATH = "ES1-016", "ES1-017", "ES1-018"
QSG_POLIWHIRL = "QSG-015"
LT_SURGES_PIKACHU = "GD3-002"
BLAINES_PONYTA, LEDYBA = "GD5-008", "SI-001"
HORSEA = "ES3-015"
KANGASKHAN = "ES3-033"
MISTYS_STARMIE, MISTYS_STARYU = "GD2-014", "GD2-013"
PURE_WATER = (("GD2-014", 0), ("ES1-018", 1), ("ES3-015", 1), ("QSG-016", 1), ("SI-015", 0), ("PR1-066", 0))
# 拡張パック以外の商品の進化カードと進化元（名前の完全一致。どれも対応しているカードにある）
BELOW = {POLIWHIRL: POLIWAG, QSG_POLIWHIRL: POLIWAG, POLIWRATH: [POLIWAG, POLIWHIRL], "QSG-016": [POLIWAG, POLIWHIRL], MISTYS_STARMIE: MISTYS_STARYU,
         "SI-015": "IP2-016", "IP2-003": "IP2-016"}
TURN = 5
# 依頼の 82 枚（版を id で決める）
REQUESTED = ("GD1-004", "GD1-008", "GD2-005", "GD2-009", "GD2-013", "GD2-014", "GD3-002", "GD3-008", "GD3-013", "GD4-005", "GD5-008", "GD5-013", "GD6-006",
             "ES1-004", "ES1-008", "ES1-012", "ES1-016", "ES1-017", "ES1-018", "ES1-024", "ES1-030", "ES1-032", "ES2-008", "ES2-009", "ES2-010", "ES2-019",
             "ES2-022", "ES2-026", "ES2-031", "ES3-015", "ES3-033", "QSG-006", "QSG-014", "QSG-015", "QSG-016", "QSG-019", "QSG-031", "QSG-036", "QSG-042",
             "QSG-044", "SI-001", "SI-005", "SI-006", "SI-007", "SI-009", "SI-015", "IP1-001", "IP1-016", "IP1-026", "IP1-030", "IP1-037", "IP1-039", "IP2-003",
             "IP2-013", "IP2-016", "IP2-039", "PF1-007", "PF2-004", "NIP1-001", "NIP1-002", "NIP1-008", "NIP1-016", "NIP1-022", "NIP1-024", "NIP2-002", "NIP2-003",
             "NIP2-004", "NIP2-016", "NIP2-018", "NIP2-024", "NIP2-026", "NIP2X-004", "PR1-011", "PR1-014", "PR1-045", "PR1-066", "PR1-069", "PRN-006", "PRN-009",
             "PRN-013", "PRN-038", "PRN-047")

EXPECTED = {
    ("GD1-004", 0): (E.DamageThenPoisonAndParalyzeOnHeads, {}),
    ("GD1-004", 1): (E.DamageThenAttackCoinCheck, {"single_use": False}),
    ("GD1-008", 0): (E.CoinFlipDamage, {"coins": 3, "damage_per_heads": 20}),
    ("GD2-009", 0): (E.FailOnTailsDamage, {"coins": 1}),
    ("GD2-013", 0): (E.DamageIgnoringDefenderEffects, {}),
    ("GD2-014", 0): (E.ExtraEnergyDamage, {"energy_type": EnergyType.WATER, "per_energy": 10, "max_extra": 2}),
    ("GD2-014", 1): (E.ParalyzeOnHeads, {}),
    ("GD3-002", 0): (E.AttachEnergyFromDiscardToSelf, {"energy_type": EnergyType.LIGHTNING}),
    ("GD3-002", 1): (E.ParalyzeOnHeads, {}),
    ("GD3-008", 0): (E.SelfDamageOnTails, {"self_damage": 10}),
    ("GD4-005", 0): (E.PoisonOnHeads, {}),
    ("GD5-008", 0): (E.DamageThenSelfBarrierOnHeads, {}),
    ("GD5-013", 0): (E.FailOnTailsDamage, {"coins": 1}),
    ("GD6-006", 0): (E.DamageThenRetreatLock, {}),
    ("ES1-004", 1): (E.PoisonWithoutDamage, {}),
    ("ES1-008", 1): (E.ConfuseOnHeads, {}),
    ("ES1-012", 0): (E.CoinBonusDamage, {"bonus": 10}),
    ("ES1-016", 0): (E.ParalyzeOnHeads, {}),
    ("ES1-017", 0): (E.StatusByCoinWithoutDamage, {"heads": 'confusion', "tails": 'sleep'}),
    ("ES1-017", 1): (E.ParalyzeOnHeads, {}),
    ("ES1-018", 1): (E.ExtraEnergyDamage, {"energy_type": EnergyType.WATER, "per_energy": 10, "max_extra": 2}),
    ("ES1-024", 1): (E.CoinBonusDamage, {"bonus": 20}),
    ("ES1-030", 0): (E.ParalyzeOnHeadsWithoutDamage, {}),
    ("ES1-030", 1): (E.CoinBonusDamage, {"bonus": 10}),
    ("ES1-032", 1): (E.FailOnTailsDamage, {"coins": 1}),
    ("ES2-008", 0): (E.ExtraEnergyDamageMixed, {"energy_type": EnergyType.WATER, "per_energy": 10, "max_extra": 2}),
    ("ES2-009", 0): (E.ParalyzeOnHeads, {}),
    ("ES2-010", 0): (E.SleepOnHeadsWithoutDamage, {}),
    ("ES2-019", 0): (E.ParalyzeOnHeads, {}),
    ("ES2-019", 1): (E.DamageThenSleepOnHeads, {}),
    ("ES2-022", 1): (E.CoinBonusDamage, {"bonus": 20}),
    ("ES2-026", 0): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 30}),
    ("ES2-026", 1): (E.ParalyzeOnHeads, {}),
    ("ES2-031", 0): (E.CoinBonusDamage, {"bonus": 20}),
    ("ES2-031", 1): (E.FailOnTailsDamage, {"coins": 1}),
    ("ES3-015", 0): (E.SelfBarrierOnHeads, {}),
    ("ES3-015", 1): (E.ExtraEnergyDamage, {"energy_type": EnergyType.WATER, "per_energy": 10, "max_extra": 2}),
    ("ES3-033", 1): (E.FailOnTailsDamage, {"coins": 2}),
    ("QSG-006", 0): (E.CoinBonusDamage, {"bonus": 10}),
    ("QSG-014", 0): (E.ParalyzeOnHeads, {}),
    ("QSG-015", 0): (E.StatusByCoinWithoutDamage, {"heads": 'confusion', "tails": 'sleep'}),
    ("QSG-015", 1): (E.ParalyzeOnHeads, {}),
    ("QSG-016", 1): (E.ExtraEnergyDamage, {"energy_type": EnergyType.WATER, "per_energy": 10, "max_extra": 2}),
    ("QSG-019", 0): (E.SleepOnHeadsWithoutDamage, {}),
    ("QSG-031", 0): (E.ParalyzeOnHeads, {}),
    ("QSG-031", 1): (E.DamageThenSleepOnHeads, {}),
    ("QSG-036", 1): (E.CoinBonusDamage, {"bonus": 20}),
    ("QSG-042", 0): (E.ParalyzeOnHeadsWithoutDamage, {}),
    ("QSG-042", 1): (E.CoinBonusDamage, {"bonus": 10}),
    ("QSG-044", 1): (E.FailOnTailsDamage, {"coins": 2}),
    ("SI-001", 1): (E.DamageThenSelfBarrierOnHeads, {}),
    ("SI-005", 0): (E.FailOnTailsDamage, {"coins": 1}),
    ("SI-006", 0): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 20}),
    ("SI-006", 1): (E.ParalyzeOnHeads, {}),
    ("SI-007", 0): (E.ConfuseOnHeads, {}),
    ("SI-009", 0): (E.CoinBonusDamage, {"bonus": 30}),
    ("SI-015", 0): (E.ExtraEnergyDamage, {"energy_type": EnergyType.WATER, "per_energy": 10, "max_extra": 2}),
    ("IP1-016", 1): (E.CoinFlipDamage, {"coins": 3, "damage_per_heads": 10}),
    ("IP1-026", 0): (E.ParalyzeOnHeads, {}),
    ("IP1-030", 0): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 10}),
    ("IP1-037", 1): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 20}),
    ("IP1-039", 0): (E.PoisonOnHeads, {}),
    ("IP1-039", 1): (E.ConfuseOnHeads, {}),
    ("IP2-003", 0): (E.ParalyzeOnHeads, {}),
    ("IP2-039", 1): (E.PoisonOnHeads, {}),
    ("PF1-007", 1): (E.DamagePlusOwnCounters, {"per": 10}),
    ("PF2-004", 0): (E.CoinBonusDamage, {"bonus": 20}),
    ("PF2-004", 1): (E.ConfuseOnHeads, {}),
    ("NIP1-008", 1): (E.CoinFlipDamage, {"coins": 3, "damage_per_heads": 10}),
    ("NIP1-016", 0): (E.CoinBonusDamage, {"bonus": 10}),
    ("NIP1-022", 0): (E.DamageThenSleepOnHeads, {}),
    ("NIP1-024", 1): (E.SleepOpponent, {}),
    ("NIP2-003", 0): (E.FailOnTailsDamage, {"coins": 1}),
    ("NIP2-018", 0): (E.SelfDamageOnTails, {"self_damage": 10}),
    ("NIP2-024", 0): (E.PoisonOnHeads, {}),
    ("NIP2-026", 1): (E.ParalyzeOnHeads, {}),
    ("NIP2X-004", 0): (E.ConfuseOnHeads, {}),
    ("PR1-045", 1): (E.CoinBonusDamage, {"bonus": 10}),
    ("PR1-066", 0): (E.ExtraEnergyDamage, {"energy_type": EnergyType.WATER, "per_energy": 10, "max_extra": 2}),
    ("PRN-006", 1): (E.HalveDamageNextTurn, {}),
    ("PRN-009", 1): (E.HalveDamageNextTurn, {}),
    ("PRN-013", 0): (E.ParalyzeOnHeads, {}),
    ("PRN-013", 1): (E.DamageThenSleepOnHeads, {}),
    ("PRN-038", 0): (E.ParalyzeOnHeadsWithoutDamage, {}),
    ("PRN-038", 1): (E.CoinBonusDamage, {"bonus": 20}),
}
DAMAGE_ONLY_ATTACKS = (("GD2-005", 0), ("GD3-013", 0), ("GD4-005", 1), ("ES1-004", 0), ("ES1-008", 0), ("ES1-012", 1), ("ES1-018", 0), ("ES1-024", 0), ("ES1-032", 0), ("ES2-009", 1), ("ES2-010", 1), ("ES2-022", 0), ("ES3-033", 0), ("QSG-006", 1), ("QSG-016", 0), ("QSG-019", 1), ("QSG-036", 0), ("QSG-044", 0), ("SI-001", 0), ("SI-005", 1), ("IP1-001", 0), ("IP1-001", 1), ("IP1-016", 0), ("IP1-037", 0), ("IP2-003", 1), ("IP2-013", 0), ("IP2-013", 1), ("IP2-016", 0), ("IP2-016", 1), ("IP2-039", 0), ("PF1-007", 0), ("NIP1-001", 0), ("NIP1-001", 1), ("NIP1-002", 0), ("NIP1-008", 0), ("NIP1-022", 1), ("NIP1-024", 0), ("NIP2-002", 0), ("NIP2-002", 1), ("NIP2-004", 0), ("NIP2-004", 1), ("NIP2-016", 0), ("NIP2-016", 1), ("NIP2-026", 0), ("PR1-011", 0), ("PR1-014", 0), ("PR1-045", 0), ("PR1-069", 0), ("PRN-006", 0), ("PRN-009", 0), ("PRN-047", 0),)

# 正式な対戦（--batch v0.70 の 2 seed・席の入れかえ。16 局）で使われた、仕組みの代表のワザ（どれも決まった seed で使われる）。たいでんは使われたが、トラッシュに「雷」
# エネルギーカードがなく何もつけなかった。テールドロップは 4 回とも失敗した（つける場合・成功する場合は単体テストで確かめる。docs 6 章）
USED_IN_GAMES = (("GD3-002", 0), ("ES1-017", 0), ("SI-001", 1), ("GD2-014", 0), ("ES1-018", 1), ("PR1-066", 0), ("ES3-033", 1), ("PR1-069", 0),
                 ("GD1-004", 0), ("GD1-004", 1), ("GD6-006", 0), ("NIP1-024", 1), ("NIP2-026", 1), ("NIP2X-004", 0), ("PF2-004", 1))


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), discard=(), turn=TURN):
    me = {"active": active, "bench": list(bench), "discard": list(discard)}
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


def with_barrier(attacker):
    """相手（プレイヤー 0）のミュウツーが「バリアー」（AttackBarrier。「ワザをうけない」状態）を使ったあと、プレイヤー 1 の attacker がワザを使う番。"""
    state = build_test_state([{"active": mon(MEWTWO, (P, P, P)), "bench": [RATTATA]}, {"active": attacker, "bench": [RATTATA]}], turn_number=TURN)
    state = apply_kernel(state, UseAttack(0, 1))
    if state.decision is not None:
        state = answer(state, state.decision.options[:1])
    assert any(type(e) is AttackBarrier for e in state.players[0].active.persistent_effects)
    return state


def modified_pool(card_id, change):
    """写しの card_id のカードを change（カードの記録を書きかえる関数）で変えた写しで分類した組（製品の写しは変えない）。"""
    extract = copy.deepcopy(read_extract())
    card = next(c for c in extract["cards"] if c["id"] == card_id)
    change(card)
    return pool_from_extract(extract)


# ---------------------------------------------------------------- 対象・登録・数


class TargetTest(unittest.TestCase):

    def test_targets_are_the_requested_82_cards(self):
        self.assertEqual(POOL_V0_70, tuple(REQUESTED))
        self.assertEqual(len(set(POOL_V0_70)), 82)
        earlier = {card_id for key, pool in EXTRACT.items() if key.startswith("pool_v0_") and key not in ("pool_v0_70", "pool_v0_71", "pool_v0_72", "pool_v0_73", "pool_v0_74", "pool_v0_75", "pool_v0_76", "pool_v0_77", "pool_v0_78", "pool_v0_79", "pool_v0_80") for card_id in pool}
        self.assertFalse(set(POOL_V0_70) & earlier)  # v0.69 までの 553 枚に入っていない
        self.assertEqual(len(earlier), 553)
        self.assertFalse(set(POOL_V0_70) & set(E.EQUIVALENT_CARDS))
        pool = load_card_pool()
        for card_id in POOL_V0_70:
            with self.subTest(card=card_id):
                self.assertTrue(pool.get(card_id).supported)
                self.assertEqual(CARDS[card_id]["category"], "pokemon")
                self.assertEqual(CARDS[card_id]["play_scope"], "standard")
                self.assertFalse(CARDS[card_id]["pokemon"]["powers"])

    def test_counts_from_the_registry(self):
        pool = load_card_pool()
        registry = E.DEFAULT_EFFECTS
        categories = [pool.get(c).category for c in pool.playable_ids]
        # v0.71 で拡張パック以外の商品の再録 78 枚（ポケモン 11・トレーナー 67。ワザ 15・特殊能力 6・トレーナー 67）を加えた。
        # v0.72 で拡張パック以外の商品のポケモン 43 枚（ワザ 77）を加えた。v0.73 で拡張パック以外の商品のトレーナー 18 枚を加えた。v0.74 で拡張パック以外の商品のスタジアム 13 枚を加えた。
        self.assertEqual(len(pool.playable_ids), 973)  # v0.80 でトレーナー 30 枚（スタジアム 4 枚を含む）を加えた  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた
        self.assertEqual(len(EXTRACT["cards"]), 973)  # v0.80 でトレーナー 30 枚（スタジアム 4 枚）を加えた  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた
        self.assertEqual((categories.count("pokemon"), categories.count("trainer"), categories.count("energy")), (695, 243, 35))  # v0.80 でトレーナー 30 枚（スタジアム 4 枚を含む）を加えた  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた
        self.assertEqual((len(registry.attack_keys()), len(registry.power_keys()), len(registry.trainer_ids()), len(registry.energy_ids())),
                         (1182, 74, 243, 17))  # v0.80 でトレーナー 30 枚（スタジアム 4 枚を含む）を加えた  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた
        new = [k for k in registry.attack_keys() if k.card_id in POOL_V0_70]
        self.assertEqual(len(new), 136)
        self.assertEqual(len(new), sum(len(CARDS[c]["pokemon"]["attacks"]) for c in POOL_V0_70))

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
                self.assertEqual(entry.name_ja, CARDS[card_id]["pokemon"]["attacks"][index]["name"]["ja"])
                seen.add((card_id, index))
        self.assertEqual(seen, {(k.card_id, k.attack_index) for k in registry.attack_keys() if k.card_id in POOL_V0_70})

    def test_pure_water_attacks_use_extra_energy_damage(self):
        """必要なエネルギーが「水」だけのみずでっぽう・ハイドロポンプは ExtraEnergyDamage（ExtraEnergyDamageMixed の check は無色のないワザを拒否する）。無色のまざる
        シェルダーの「しおふき」は ExtraEnergyDamageMixed（HC4 のまま）。"""
        pool = load_card_pool()
        for card_id, index in PURE_WATER:
            with self.subTest(card=card_id):
                effect = E.DEFAULT_EFFECTS.attack_entry(card_id, index).effect
                self.assertEqual(effect, E.ExtraEnergyDamage(EnergyType.WATER, 10, 2))
                attack_def = pool.get(card_id).attacks[index]
                self.assertEqual(set(attack_def.cost), {EnergyType.WATER})
                self.assertTrue(E.ExtraEnergyDamageMixed(EnergyType.WATER, 10, 2).check(attack_def))
        self.assertEqual(E.DEFAULT_EFFECTS.attack_entry("ES2-008", 0).effect, E.ExtraEnergyDamageMixed(EnergyType.WATER, 10, 2))

    def test_new_types_are_kernel_programs_outside_the_v013_contract(self):
        for cls in (E.StatusByCoinWithoutDamage, E.AttachEnergyFromDiscardToSelf):
            with self.subTest(cls=cls.__name__):
                self.assertIn(cls, programs.BUILDERS)
                self.assertIn(cls, ATTACK_TYPES_SINCE_V0_17)
                self.assertNotIn(cls, v013_checks.VERIFIED)
                self.assertIs(cls.resolve, E.AttackEffect.resolve)
        self.assertEqual(programs.BUILDERS[E.StatusByCoinWithoutDamage](E.StatusByCoinWithoutDamage(CONFUSION, SLEEP)),
                         programs.BUILDERS[E.DamageThenStatusByCoin](E.DamageThenStatusByCoin(CONFUSION, SLEEP))[1:])
        self.assertEqual(programs.BUILDERS[E.AttachEnergyFromDiscardToSelf](E.AttachEnergyFromDiscardToSelf(EnergyType.LIGHTNING)),
                         programs.BUILDERS[E.DamageThenAttachEnergyFromDiscardToSelf](E.DamageThenAttachEnergyFromDiscardToSelf(EnergyType.LIGHTNING))[1:])

    def test_no_card_specific_branch_in_the_engine(self):
        sources = [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]
        for path in sources:
            text = path.read_text(encoding="utf-8")
            for card_id in POOL_V0_70:
                self.assertNotIn(f'"{card_id}"', text, path.name)


class UnsupportedWithoutRegistrationTest(unittest.TestCase):
    """登録を除けば未対応にもどる。データ（文面・コインの枚数・ダメージの形・必要なエネルギー）が登録と合わなければ未対応。"""

    def test_without_the_v070_registrations_the_cards_are_unsupported(self):
        keys = [k for k in E.DEFAULT_EFFECTS.attack_keys() if k.card_id in POOL_V0_70]
        registry = E.DEFAULT_EFFECTS.without_attacks("test-no-v070", keys)
        pool = pool_from_extract(read_extract(), registry)
        self.assertEqual([c for c in POOL_V0_70 if pool.get(c).supported], [])
        self.assertEqual(len(pool.playable_ids), 891)  # v0.80 の 30 枚・v0.79 の 52 枚・v0.78 の 13 枚も含む。 v0.71 の再録 78 枚・v0.72 の 43 枚・v0.73 の 18 枚・v0.74 の 13 枚・v0.75 の 15 枚・v0.76 の 24 枚・v0.77 の 52 枚を含む（v0.70 の時点は 553）
        one = E.DEFAULT_EFFECTS.without_attacks("test-no-tail-drop", [AttackKey(KANGASKHAN, 1)])
        pool = pool_from_extract(read_extract(), one)
        self.assertFalse(pool.get(KANGASKHAN).supported)
        self.assertTrue(pool.get("QSG-044").supported)  # 同じデータの別の id は別の登録

    def test_data_mismatch_makes_the_card_unsupported(self):
        def text(card_id, index, value):
            return card_id, lambda c: c["pokemon"]["attacks"][index]["text"].__setitem__("ja", value)

        def damage(card_id, index, value):
            return card_id, lambda c: c["pokemon"]["attacks"][index].__setitem__("damage", value)

        def cost(card_id, index, value):
            def change(c):
                c["pokemon"]["attacks"][index]["cost"] = value
                c["pokemon"]["attacks"][index]["cost_total"] = len(value)
            return card_id, change

        cases = [
            # ぐるぐる: 「おもて」と「うら」の特殊状態の入れかえ・ダメージの目安を加える
            text(POLIWHIRL, 0, "コインを投げて「おもて」なら、相手を「ねむり」状態に、「うら」なら「こんらん」状態にする。"),
            damage(POLIWHIRL, 0, {"base": 10, "modifier": None, "display": "10"}),
            # たいでん: 「最大2枚」・ダメージの目安を加える
            text(LT_SURGES_PIKACHU, 0, "自分のトラッシュに「雷」エネルギーカードがあれば、最大2枚取り出して、自分につける。"),
            damage(LT_SURGES_PIKACHU, 0, {"base": 10, "modifier": None, "display": "10"}),
            # テールドロップ: コインの枚数
            text(KANGASKHAN, 1, "コインを3枚投げ、1つでも「うら」なら、このワザは失敗する。"),
            # こうそくいどう: ダメージをなくす・別の書き方
            damage(BLAINES_PONYTA, 0, None),
            text(LEDYBA, 1, "コインを投げて「おもて」なら、次の相手の番、このカードはダメージを受けない。"),
            # みずでっぽう: 必要なエネルギーに無色をまぜる（ExtraEnergyDamage の check）
            cost(MISTYS_STARMIE, 0, ["water", "colorless"]),
            # コインの枚数・追加の量
            text("GD1-008", 0, "コインを2枚投げて「おもて」の数×20のダメージ。"),
            text("ES1-024", 1, "コインを投げて「おもて」なら、30ダメージを追加する。"),
        ]
        for card_id, change in cases:
            with self.subTest(card=card_id):
                self.assertTrue(load_card_pool().get(card_id).supported)
                self.assertFalse(modified_pool(card_id, change).get(card_id).supported)

    def test_new_types_and_the_added_wording_reject_other_texts(self):
        pool = load_card_pool()
        swirl = pool.get(POLIWHIRL).attacks[0]
        self.assertEqual(E.StatusByCoinWithoutDamage(CONFUSION, SLEEP).check(swirl), [])
        self.assertTrue(E.StatusByCoinWithoutDamage(SLEEP, CONFUSION).check(swirl))
        self.assertTrue(E.DamageThenStatusByCoin(CONFUSION, SLEEP).check(swirl))  # ダメージの目安がない
        static = pool.get(LT_SURGES_PIKACHU).attacks[0]
        self.assertEqual(E.AttachEnergyFromDiscardToSelf(EnergyType.LIGHTNING).check(static), [])
        self.assertTrue(E.AttachEnergyFromDiscardToSelf(EnergyType.WATER).check(static))
        self.assertTrue(E.DamageThenAttachEnergyFromDiscardToSelf(EnergyType.LIGHTNING).check(static))
        self.assertTrue(E.AttachDiscardEnergyToSelf(EnergyType.LIGHTNING, 1).check(static) == [])  # v0.31 の型は文面を確かめない（使わない。HC7 が入る）
        for card_id, index in ((BLAINES_PONYTA, 0), (LEDYBA, 1)):
            agility = pool.get(card_id).attacks[index]
            self.assertEqual(E.DamageThenSelfBarrierOnHeads().check(agility), [])
            self.assertTrue(E.SelfBarrierOnHeads().check(agility))  # ダメージがある
        hide = pool.get(HORSEA).attacks[0]
        self.assertEqual(E.SelfBarrierOnHeads().check(hide), [])
        self.assertTrue(E.DamageThenSelfBarrierOnHeads().check(hide))
        self.assertIn("コインを投げて「おもて」なら、次の相手の番、このカードはワザによるダメージや効果を受けない。", E.SELF_BARRIER_ON_HEADS_TEXTS)
        self.assertEqual(len(E.SELF_BARRIER_ON_HEADS_TEXTS), 5)  # v0.72 でピカチュウ（ES1-019・QSG-020）の書き方を加えた
        with self.assertRaises(ValueError):
            E.StatusByCoinWithoutDamage(SLEEP, SLEEP)

    def test_evolution_lines_by_exact_name_and_stage(self):
        pool = load_card_pool()
        names = {}
        for card_id in pool.playable_ids:
            d = pool.get(card_id)
            if d.category == "pokemon":
                names.setdefault(d.name_ja, set()).add(d.stage)
        stages = {"stage1": "basic", "stage2": "stage1"}
        for card_id in POOL_V0_70:
            d = pool.get(card_id)
            with self.subTest(card=card_id):
                if d.stage == "basic":
                    self.assertIsNone(d.evolves_from)
                else:
                    self.assertIn(stages[d.stage], names.get(d.evolves_from, set()))
        for stage1, basic in (("NIP1-024", "チコリータ"), ("NIP2-004", "ワニノコ"), ("NIP2-026", "メリープ")):
            self.assertEqual(pool.get(stage1).evolves_from, basic)
            self.assertTrue(all(pool.get(c).name_ja != basic or c in POOL_V0_70 + tuple(EXTRACT["pool_v0_76"]) + tuple(EXTRACT["pool_v0_77"]) + tuple(EXTRACT["pool_v0_78"]) + tuple(EXTRACT["pool_v0_79"]) for c in pool.playable_ids))  # v0.77: ワニノコ neo1-024・neo4-028・ウパー neo1-026。v0.76: チコリータ PF1-001・ワニノコ PRN-008・PRN-011


class SharedEntriesTest(unittest.TestCase):
    """処理に使う欄が同じ v0.70 のカード（SAME_DATA_CARDS_V0_70。12 枚）は、登録の値を共有する（マチスの秘策の確かめでは 1 枚で代表する）。"""

    def test_twins_have_the_same_data_and_share_entries(self):
        pool = load_card_pool()
        self.assertEqual(len(E.SAME_DATA_CARDS_V0_70), 12)
        self.assertFalse(set(E.SAME_DATA_CARDS_V0_70) & set(E.EQUIVALENT_CARDS))
        for new, original in E.SAME_DATA_CARDS_V0_70.items():
            with self.subTest(card=new):
                self.assertIn(new, POOL_V0_70)
                self.assertIn(original, POOL_V0_70)
                self.assertEqual(cs.engine_view(CARDS[new]), cs.engine_view(CARDS[original]))
                self.assertEqual(CARDS[new]["same_card_group"], CARDS[original]["same_card_group"])
                self.assertEqual(engine_module._behavior_key(pool, new), engine_module._behavior_key(pool, original))
                for a in pool.get(new).attacks:
                    self.assertIs(E.DEFAULT_EFFECTS.attack_entry(new, a.index), E.DEFAULT_EFFECTS.attack_entry(original, a.index))
        others = [c for c in POOL_V0_70 if c not in E.SAME_DATA_CARDS_V0_70]
        views = [repr(cs.engine_view(CARDS[c])) for c in others]
        self.assertEqual(len(views), len(set(views)))  # ほかに同じデータの組はない

    def test_helper_rejects_different_registrations(self):
        with self.assertRaises(RuntimeError):
            E._with_shared_entries(E.DEFAULT_EFFECTS, {"ES1-016": "ES1-017"})
        with self.assertRaises(RuntimeError):
            E._with_shared_entries(E.DEFAULT_EFFECTS, {"QSG-014": "QSG-015", "QSG-015": "ES1-017"})


# ---------------------------------------------------------------- ぐるぐる（StatusByCoinWithoutDamage）


class SwirlTest(unittest.TestCase):

    def test_heads_confuses_and_tails_puts_to_sleep_without_damage(self):
        for side, condition in ((H, CONFUSION), (T, SLEEP)):
            with self.subTest(side=side):
                state = board(mon(POLIWHIRL, (W, W)))
                done = audited(self, attack(state, 0, side))
                since = len(state.log)
                # ワザのコインは 1 枚（番の終わりのポケモンチェックのねむりのコインは数えない）
                self.assertEqual(len([e for e in events(done, since, "coin_flip") if e["source"] != "pokemon_check"]), 1)
                self.assertEqual(events(done, since, "damage"), [])
                # 相手を特殊状態にしたログ（ねむりは番の終わりのポケモンチェックで回復しうるので、状態ではなくログで確かめる）
                given = [e for e in events(done, since, "special_condition") if e["player"] == 1]
                self.assertEqual([e["condition"] for e in given], [condition])
                self.assertFalse(events(done, since, "attack_failed"))
                self.assertEqual(done.players[1].active.damage, 0)

    def test_same_coin_decides_and_is_not_flipped_again(self):
        state = board(mon(QSG_POLIWHIRL, (W, W)))
        done = attack(state, 0, T, H)
        self.assertEqual([e["result"] for e in events(done, len(state.log), "coin_flip") if e["source"] != "pokemon_check"], ["tails"])
        self.assertEqual([e["condition"] for e in events(done, len(state.log), "special_condition")], [SLEEP])

    def test_protection_stops_before_the_coin(self):
        """相手が「ワザをうけない」状態なら、コインが決めるのは相手への効果だけなので HC3（v0.34 の void_coin_question）。状態・乱数・ログは変わらない。"""
        state = with_barrier(mon(POLIWHIRL, (W, W)))
        assert_stops(self, state, UseAttack(1, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")

    def test_every_preflight_mode_gives_the_same_result(self):
        for side in (H, T):
            state = board(mon(POLIWHIRL, (W, W)))
            results = {mode: full(attack(state, 0, side, mode=mode)) for mode in PREFLIGHT_MODES}
            self.assertEqual(len({repr(r) for r in results.values()}), 1)

    def test_illegal_command_does_not_flip(self):
        state = board(mon(POLIWHIRL, (W,)))
        before = snapshot(state)
        with self.assertRaises(IllegalActionError):
            apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(snapshot(state), before)


# ---------------------------------------------------------------- たいでん（AttachEnergyFromDiscardToSelf）


class StaticChargeTest(unittest.TestCase):

    def test_one_lightning_card_is_attached_from_the_discard(self):
        state = board(mon(LT_SURGES_PIKACHU, (L,)), discard=[L, W, L])
        waiting = attack(state, 0)
        d = waiting.decision
        lightning = tuple(u for u in state.players[0].discard if state.cards[u].card_id == L)
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices, d.options, d.resume), (ATTACH_FROM_DISCARD, 0, 1, 1, lightning, "attack"))
        self.assertEqual(check_invariants(waiting), [])
        done = audited(self, answer(waiting, (lightning[1],)))
        self.assertEqual(done.players[0].active.energy, [state.players[0].active.energy[0], lightning[1]])
        self.assertEqual(done.energy_attachments_this_turn, state.energy_attachments_this_turn)
        self.assertEqual(events(done, len(state.log), "damage"), [])
        self.assertEqual([e["cards"] for e in events(done, len(state.log), "attach_energy_from_discard")], [(lightning[1],)])
        self.assertEqual(done.current_player, 1)  # ワザを使ったので番は終わる

    def test_nothing_to_attach(self):
        state = board(mon(LT_SURGES_PIKACHU, (L,)), discard=[W, G])
        done = audited(self, attack(state, 0))
        self.assertIsNone(done.decision)
        self.assertEqual(done.players[0].active.energy, state.players[0].active.energy)
        self.assertEqual(done.players[0].discard, state.players[0].discard)

    def test_wrong_and_zero_choices_are_rejected_without_changes(self):
        state = board(mon(LT_SURGES_PIKACHU, (L,)), discard=[L, W])
        waiting = attack(state, 0)
        water = next(u for u in state.players[0].discard if state.cards[u].card_id == W)
        before = snapshot(waiting)
        for choice in ((water,), (), tuple(waiting.decision.options) * 2):
            with self.subTest(choice=choice), self.assertRaises(IllegalActionError):
                answer(waiting, choice)
            self.assertEqual(snapshot(waiting), before)
        with self.assertRaises(IllegalActionError):
            apply_kernel(waiting, ResolveDecision(1, waiting.decision.id, waiting.decision.options))  # 決めるのはワザを使ったプレイヤー
        self.assertEqual(snapshot(waiting), before)

    def test_save_and_restore_while_waiting(self):
        state = board(mon(LT_SURGES_PIKACHU, (L,)), discard=[L, L])
        waiting = attack(state, 0)
        data = full(waiting)
        for copied in (waiting.clone(), copy.deepcopy(waiting), pickle.loads(pickle.dumps(waiting))):
            self.assertEqual(full(copied), data)
            self.assertEqual(full(answer(copied, waiting.decision.options[:1])), full(answer(waiting, waiting.decision.options[:1])))
        self.assertEqual(serialization_problems(waiting), [])

    def test_rainbow_energy_in_the_discard_stops_before_choosing(self):
        """トラッシュのレインボーエネルギーが「「雷」エネルギーカード」に当たるかは決まらない（v0.58 の RB2）。"""
        state = board(mon(LT_SURGES_PIKACHU, (L,)), discard=[L, RAINBOW])
        assert_stops(self, state, UseAttack(0, 0), "UNRESOLVED_RAINBOW_ATTACH_AS_TYPE")

    def test_crystal_beam_prevents_attaching(self):
        """相手のカスミのメノクラゲの「クリスタルビーム」を受けた次の番は、エネルギーカードをつけられない（v0.59 の共通の処理）。決定を出さずに番を終える。"""
        state = build_test_state([{"active": mon(MISTYS_TENTACOOL, (W, W)), "bench": [RATTATA]},
                                  {"active": mon(LT_SURGES_PIKACHU, (L,)), "bench": [RATTATA], "discard": [L]}], turn_number=TURN)
        state = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(state.current_player, 1)
        done = audited(self, attack(state, 0, player=1))
        self.assertIsNone(done.decision)
        self.assertEqual(len(done.players[1].active.energy), 1)

    def test_every_preflight_mode_gives_the_same_result(self):
        state = board(mon(LT_SURGES_PIKACHU, (L,)), discard=[L, L])
        results = {mode: full(answer(attack(state, 0, mode=mode), state.players[0].discard[:1], mode=mode)) for mode in PREFLIGHT_MODES}
        self.assertEqual(len({repr(r) for r in results.values()}), 1)


# ---------------------------------------------------------------- こうそくいどう・かくれる・みずでっぽう・テールドロップ


class ReusedTypeTest(unittest.TestCase):

    def test_agility_gives_the_attack_barrier_on_heads_after_the_damage(self):
        for card_id, index, energy in ((BLAINES_PONYTA, 0, (R, R)), (LEDYBA, 1, (G, G))):
            for side, barrier in ((H, True), (T, False)):
                with self.subTest(card=card_id, side=side):
                    state = board(mon(card_id, energy))
                    done = audited(self, attack(state, index, side))
                    since = len(state.log)
                    self.assertEqual([e["amount"] for e in events(done, since, "damage")], [20])
                    kinds = [e["kind"] for e in done.log[since:]]
                    self.assertLess(kinds.index("damage"), kinds.index("coin_flip"))
                    self.assertEqual(any(type(e) is AttackBarrier for e in done.players[0].active.persistent_effects), barrier)

    def test_hide_has_no_damage(self):
        state = board(mon(HORSEA, (W,)))
        done = audited(self, attack(state, 0, H))
        self.assertEqual(events(done, len(state.log), "damage"), [])
        self.assertTrue(any(type(e) is AttackBarrier for e in done.players[0].active.persistent_effects))

    def test_water_gun_counts_water_beyond_the_cost(self):
        for energy, amount in (((W,), 10), ((W, W), 20), ((W, W, W), 30), ((W, W, W, W), 30), ((DCE, W), 10)):
            with self.subTest(energy=energy):
                state = board(mon(MISTYS_STARMIE, energy))
                done = audited(self, attack(state, 0))
                self.assertEqual([e["amount"] for e in events(done, len(state.log), "damage")], [amount])
        state = board(mon(POLIWRATH, (W,) * 5))
        done = audited(self, attack(state, 1))
        self.assertEqual([e["amount"] for e in events(done, len(state.log), "damage")], [60])

    def test_rainbow_energy_on_a_water_gun_stops(self):
        """ついているレインボーエネルギーが「水」エネルギーに当たるかは決まらない（v0.58 の RB1。ExtraEnergyDamage の共通の処理）。"""
        state = board(mon(MISTYS_STARMIE, (W, RAINBOW)))
        assert_stops(self, state, UseAttack(0, 0), "UNRESOLVED_RAINBOW_ENERGY_TYPE")

    def test_tail_drop_needs_both_heads(self):
        for sides, amount in (((H, H), [80]), ((H, T), []), ((T, H), []), ((T, T), [])):
            with self.subTest(sides=sides):
                state = board(mon(KANGASKHAN, (W, W, W)))
                done = audited(self, attack(state, 1, *sides))
                self.assertEqual([e["amount"] for e in events(done, len(state.log), "damage")], amount)
                self.assertEqual(len(events(done, len(state.log), "coin_flip")), 2)
                self.assertEqual(bool(events(done, len(state.log), "attack_failed")), not amount)
        names = [a["name"]["ja"] for a in CARDS[KANGASKHAN]["pokemon"]["attacks"]]
        self.assertEqual(names, ["かみつく", "テールドロップ"])

    def test_every_preflight_mode_gives_the_same_result(self):
        cases = [(board(mon(BLAINES_PONYTA, (R, R))), 0), (board(mon(KANGASKHAN, (W, W, W))), 1), (board(mon(MISTYS_STARMIE, (W, W, W))), 0),
                 (board(mon("GD1-008", (F, F, F), evolved_from="PMCG5-046")), 0)]
        for state, index in cases:
            for sides in ((H, H, H), (T, T, T), (H, T, H)):
                with self.subTest(card=state.cards[state.players[0].active.card].card_id, sides=sides):
                    results = {mode: full(attack(state, index, *sides, mode=mode)) for mode in PREFLIGHT_MODES}
                    self.assertEqual(len({repr(r) for r in results.values()}), 1)


# ---------------------------------------------------------------- PR1-069 の名前（利用者が示した訂正）


class AncientMewTest(unittest.TestCase):

    def test_name_is_corrected_and_other_fields_are_kyuura_data(self):
        card = CARDS[ANCIENT_MEW]
        self.assertEqual(card["name"]["ja"], "ミュウ")
        pokemon = card["pokemon"]
        self.assertEqual((pokemon["hp"], pokemon["types"], pokemon["weaknesses"], pokemon["resistances"], pokemon["retreat_cost"]),
                         (30, ["psychic"], [{"type": "psychic", "operator": "×", "value": 2}], [], 2))
        self.assertEqual([(a["name"]["ja"], a["cost"], a["damage"]["display"], a["text"]["ja"]) for a in pokemon["attacks"]],
                         [("Psyche(サイケ)", ["psychic", "psychic"], "40", None)])
        (correction,) = EXTRACT["engine_user_corrections"]
        self.assertEqual((correction["card_id"], correction["field"], correction["before"], correction["after"], correction["basis"], correction["engine_saw_image"],
                          correction["source_commit"]), (ANCIENT_MEW, "name.ja", "？？？", "ミュウ", "user_provided", False, EXTRACT["source"]["commit"]))
        self.assertNotIn("record", correction)
        self.assertNotIn("commit", correction)
        self.assertFalse([c for c in EXTRACT["kyuura_corrections"] if c["card_id"] == ANCIENT_MEW])  # kyuura が当てはめた修正の表には入れない
        self.assertIs(E.DEFAULT_EFFECTS.attack_entry(ANCIENT_MEW, 0).effect, E.DAMAGE_ONLY)
        self.assertEqual(load_card_pool().get(MEW).name_ja, "ミュウ")  # ほかのミュウの定義は変えない

    def test_same_name_limit_counts_both_mews(self):
        filler = ["PMCG1-101"] * 56
        self.assertEqual(deck_problems([ANCIENT_MEW] * 2 + [MEW] * 2 + filler), [])
        self.assertEqual(deck_problems([ANCIENT_MEW] * 4 + filler), [])
        for deck in ([ANCIENT_MEW] * 3 + [MEW] * 2 + filler[:55], [ANCIENT_MEW] * 1 + [MEW] * 4 + filler[:55], [ANCIENT_MEW] * 5 + filler[:55]):
            with self.subTest(deck=sorted(set(deck))):
                problems = deck_problems(deck)
                self.assertEqual(len(problems), 1)
                self.assertTrue(problems[0].startswith("TOO_MANY_COPIES: 「ミュウ」が 5 枚"), problems)
                with self.assertRaises(DeckValidationError) as raised:
                    validate_deck(deck)
                self.assertEqual(raised.exception.problems, problems)

    def test_quiz_names_have_no_new_entry_for_this_card(self):
        state = build_test_state([{"active": "PMCG1-018"}, {"active": "PMCG1-018"}])
        names = E.quiz_answer_names(state)
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names.count("ミュウ"), 1)
        self.assertNotIn("？？？", names)


class ExtractionCorrectionTest(unittest.TestCase):
    """写しの作り直しの、利用者が示した訂正の確かめ（scripts/extract_kyuura_cards.py の engine_user_correction_problems）。"""

    @classmethod
    def setUpClass(cls):
        if not (KYUURA / ".git").exists():
            raise unittest.SkipTest("../kyuura がない")
        spec = importlib.util.spec_from_file_location("extract_v070", ROOT / "scripts" / "extract_kyuura_cards.py")
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.source = cls.module.read_kyuura_cards(KYUURA)
        cls.pool = cls.module.all_pool_cards() + cls.module.REFERENCE_ONLY

    def problems(self, corrections, source=None):
        saved = self.module.ENGINE_USER_CORRECTIONS
        self.module.ENGINE_USER_CORRECTIONS = corrections
        try:
            return self.module.engine_user_correction_problems(KYUURA, source or self.source, self.pool)
        finally:
            self.module.ENGINE_USER_CORRECTIONS = saved

    def test_current_correction_is_accepted(self):
        self.assertEqual(self.module.engine_user_correction_problems(KYUURA, self.source, self.pool), [])
        (c,) = self.module.ENGINE_USER_CORRECTIONS
        self.assertEqual((c["card_id"], c["field"], c["before"], c["after"]), (ANCIENT_MEW, "name.ja", "？？？", "ミュウ"))

    def test_bad_corrections_are_rejected(self):
        (c,) = self.module.ENGINE_USER_CORRECTIONS
        for bad in (dict(c, before="ちがう名前"), dict(c, basis="kyuura_source_check"), dict(c, engine_saw_image=True), dict(c, record="CC-PR1-069"),
                    dict(c, id="FIX-PR1-069-NAME"), dict(c, field="pokemon.hp", before=30, after=40), dict(c, card_id="PMCG3-033", before="ミュウ")):
            with self.subTest(bad={k: v for k, v in bad.items() if c.get(k) != v}):
                self.assertTrue(self.problems([bad]))
        self.assertTrue(self.problems([c, c]))

    def test_upstream_value_is_not_corrected_twice(self):
        """kyuura がすでに同じ値にしていたら当てはめず（二重に当てはめない）、表を移すよう知らせる。前後のどちらでもない値なら知らせる。"""
        for value, word in (("ミュウ", "すでに"), ("ミュウ（古代）", "想定した前の値")):
            source = copy.deepcopy(self.source)
            card = next(x for x in source["cards"] if x["id"] == ANCIENT_MEW)
            card["name"]["ja"] = value
            problems = self.problems(self.module.ENGINE_USER_CORRECTIONS, source)
            self.assertTrue(any(word in p for p in problems), problems)
        cards = [copy.deepcopy(next(x for x in self.source["cards"] if x["id"] == ANCIENT_MEW))]
        cards[0]["name"]["ja"] = "ミュウ"
        with self.assertRaises(SystemExit):
            self.module.apply_engine_user_corrections(cards)

    def test_research_links_check_is_narrow(self):
        """check_research_links は、対応表の engine_user_corrections がなければ PR1-069 の名前の違いを問題にする（一般の比べ方は弱めていない）。"""
        spec = importlib.util.spec_from_file_location("links_v070", ROOT / "scripts" / "check_research_links.py")
        links_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(links_module)
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        self.assertEqual(links_module.check(KYUURA, links=links), [])
        missing = dict(links, engine_user_corrections=[])
        problems = links_module.check(KYUURA, links=missing)
        self.assertTrue(any("PR1-069 の name" in p for p in problems), problems)
        wrong = dict(links, engine_user_corrections=[dict(links["engine_user_corrections"][0], engine_value="ミュウツー")])
        self.assertTrue(links_module.check(KYUURA, links=wrong))


class RecordTest(unittest.TestCase):

    def test_adoption_records(self):
        sources = cs.load_sources()["cards"]
        links = cs.load_links()
        printed = set(links["latest_descriptions"]["adopted_printed_text"])
        for card_id in POOL_V0_70:
            with self.subTest(card=card_id):
                record = sources[card_id]
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["recorded_on"], record["kyuura_records"], record["issues"]),
                                 ("kyuura_data", "adopted", EXTRACT["source"]["commit"], "2026-10-19", [], []))
                self.assertEqual(record["external_checks"], [])  # 日本語の文面は pcg-search.com の転記。新しい外部照合はしていない
                self.assertNotIn("equivalent_to", record)
                targets = {f"attack/{i}" for i, a in enumerate(CARDS[card_id]["pokemon"]["attacks"]) if a["text"]["ja"] is not None}
                self.assertEqual(set(record["play_text"]), targets)
                self.assertTrue(all(v == "kyuura_printed_text" for v in record["play_text"].values()))
                self.assertTrue({f"{card_id}/{t}" for t in targets} <= printed)
                self.assertEqual("user_name_correction" in record, card_id == ANCIENT_MEW)
        self.assertEqual(cs.problems(), [])

    def test_name_correction_record_is_checked(self):
        sources = copy.deepcopy(cs.load_sources())
        del sources["cards"][ANCIENT_MEW]["user_name_correction"]
        self.assertTrue(any("user_name_correction" in p for p in cs.problems(sources)))
        sources = copy.deepcopy(cs.load_sources())
        sources["cards"][ANCIENT_MEW]["user_name_correction"]["kyuura"] = "ミュウ"
        self.assertTrue(cs.problems(sources))
        sources = copy.deepcopy(cs.load_sources())
        sources["cards"]["ES1-016"]["user_name_correction"] = dict(sources["cards"][ANCIENT_MEW]["user_name_correction"])
        self.assertTrue(any("ES1-016" in p for p in cs.problems(sources)))


class SecretPlanCandidatesTest(unittest.TestCase):
    """マチスの秘策の受け付けるかの確かめで試すカード: 公開の情報（対応しているカードの一覧）だけから作る。v0.70 のカードが加わり、ありうるカードの種類が増えた
    （v0.69 の 457 → 527。同じデータの 12 枚は 1 枚で代表する）。上限（512）は変えていない。"""

    def test_candidates(self):
        pool = load_card_pool()
        candidates = engine_module._identity_candidates(pool)
        v072 = set(EXTRACT["pool_v0_72"]) | set(EXTRACT["pool_v0_73"]) | set(EXTRACT["pool_v0_74"]) | set(EXTRACT["pool_v0_75"]) | set(EXTRACT["pool_v0_76"]) | set(EXTRACT["pool_v0_77"]) | set(EXTRACT["pool_v0_78"]) | set(EXTRACT["pool_v0_79"]) | set(EXTRACT["pool_v0_80"])  # v0.76 の 24 枚も除く。 v0.72: 試すカードの数は固定しない（v0.72 の 43 枚・v0.73 の 18 枚・v0.74 の 13 枚を除いて比べる）
        self.assertEqual(len(set(candidates) - v072), 572)  # v0.71 で再録のカード（処理の違う 45 種類）が加わった（v0.70 の時点は 527）
        self.assertEqual(set(candidates) & set(POOL_V0_70), set(POOL_V0_70) - set(E.SAME_DATA_CARDS_V0_70))
        self.assertFalse(set(candidates) & set(E.EQUIVALENT_CARDS))
        basics = [c for c in candidates if pool.get(c).is_basic_pokemon]
        self.assertEqual(len(set(basics) - v072), 245)  # v0.71 で再録のたねポケモン 4（v0.70 の時点は 241）
        self.assertEqual(engine_module._IDENTITY_TRIAL_LIMIT, 512)
        # 1 枚を指定するコマンドの試す回数: 割り当てる前 1 回 + たねポケモン + 「たねポケモンでない」1（v0.70 は 243、v0.71 は 247。トラッシュしたあとに項目を読まなければ）
        self.assertLessEqual(1 + len(basics) + 1, engine_module._IDENTITY_TRIAL_LIMIT)


# ---------------------------------------------------------------- 正式な対戦開始からの対戦


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）から、v0.70 のカードと前の版のカードを混ぜたデッキ（tools/existing_effect_games.py の W70・L70・C70・B70）。
    決まった seed・席の入れかえ。勝敗は判断に使わない。"""

    @classmethod
    def setUpClass(cls):
        from tools import existing_effect_games as games

        cls.games = games
        cls.results = games.run(range(2), pairings=games.PAIRINGS_V0_70)

    def test_games_finish_without_audit_failures(self):
        for name, run in self.results.items():
            for game in run["games"]:
                with self.subTest(run=name, seed=game["seed"]):
                    self.assertIn(game["outcome"], ("game_over", "sudden_death", "halted"), game.get("error"))
                    self.assertEqual(game["audit"], {})

    def test_decks_mix_new_and_earlier_ids(self):
        for label in ("W70", "L70", "C70", "B70"):
            deck = self.games.deck_cards(label)
            self.assertTrue(set(deck) & set(POOL_V0_70))
            self.assertTrue(set(deck) - set(POOL_V0_70))
            self.assertEqual(deck_problems(deck), [])
        c70 = self.games.deck_cards("C70")
        self.assertEqual((c70.count(ANCIENT_MEW), c70.count(MEW)), (2, 2))

    def test_representative_attacks_are_used(self):
        used = set()
        for run in self.results.values():
            for game in run["games"]:
                for card, uses in game.get("card_uses", {}).items():
                    used |= {(card, int(k.split("#")[1])) for k in uses if re.fullmatch(r"attack#\d", k)}
        for key in USED_IN_GAMES:
            with self.subTest(attack=key):
                self.assertIn(key, used)


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = DOC.read_text(encoding="utf-8")
        for card_id in POOL_V0_70:
            self.assertIn(card_id, text)
        for word in ("StatusByCoinWithoutDamage", "AttachEnergyFromDiscardToSelf", "ENGINE_USER_CORRECTIONS", "SAME_DATA_CARDS_V0_70", "527"):
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()
