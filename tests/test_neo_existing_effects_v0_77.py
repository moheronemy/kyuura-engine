"""v0.77: neo 期の拡張パック（neo1〜neo4）の、既存の効果の型で表せるカード 52 枚（ポケモン 50 枚・ワザ 77、トレーナー 2 枚）（docs/neo-existing-effects-v0.77.md）。

どれも kyuura データの採用（採用したデータのコミット 7d3f4ca。処理に使う文面は kyuura の印刷の文面。id は kyuura の小文字の id のまま）。ガイドブックは読んでいない。
kyuura の日本語の文面は nazonobasho.com・ポケモンWiki の転記で、外部照合はしていない。新しい型・要素・決定・状態はない。処理の根拠は、流用した既存の型の
規定と記録（kyuura の GR-2000-P309-ATTACK-PROCEDURE・GR-2000-P321-DAMAGE-ORDER・GR-2000-P322-PERSISTENT-EFFECTS・GR-2000-P310-EVOLUTION と、エンジンの過去の版の処理）。
新しい型を作っていないので、既存の境界のテストはカードごとに複製せず、流用した仕組みを代表するカードで確かめる。
"""

from __future__ import annotations

import copy
import importlib
import json
import pathlib
import pickle
import subprocess
import unittest
from collections import Counter

from kyuura_engine import (
    EndTurn,
    EvolvePokemon,
    IllegalActionError,
    Phase,
    PlayTrainer,
    ResolveDecision,
    UseAttack,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine import engine as engine_module
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import FORCED_SWITCH, SELECT_OPPONENT_ATTACK
from kyuura_engine.effects import EffectRegistry, EnergyType
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import (
    AttackBarrier,
    CannotAttackWhileSourceActive,
    CannotUseAttack,
)
from tests.helpers import (
    BILLS_TELEPORTER_NEO1,
    FIGHTING,
    FIRE,
    GRASS,
    HITMONCHAN,
    HITMONLEE_NEO4,
    HORSEA,
    KINGDRA_NEO1,
    LIGHTNING,
    POKEMON_BREEDER,
    POLIWHIRL,
    POLIWRATH_NEO2,
    QUAGSIRE_NEO1,
    RATTATA,
    SEADRA,
    SENTRET_NEO1,
    SKIPLOOM_NEO1,
    SKIPLOOM_NEO3,
    SUDOWOODO_NEO1,
    SUPER_SCOOP_UP_NEO1,
    TOTODILE_NEO1,
    V0_77_CARDS,
    V0_77_POKEMON,
    V0_77_TRAINERS,
    WATER,
    WOOPER_NEO1,
    WOOPER_PRN,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import observation_problems, serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "neo-existing-effects-v0.77.md"
H, T = CoinSide.HEADS, CoinSide.TAILS
TURN = 7
DECK = [WATER] * 12
KYUURA_COMMIT = "7d3f4ca76c084774efb4ac6a1d3a943387e183c3"
V076_COMMIT = "749b629196810484745d4071ec9de241fcae2377"
FURRET_NEO1 = "neo1-064"
ELECTABUZZ_NEO1 = "neo1-039"

# 前の版で登録したカードと日本語のゲーム用データが同じ 7 枚（新しい id → まとめる先の前の版のカード。同じデータのほかの id は括弧）
SAME_DATA = {"neo1-006": "PRN-032", "neo1-024": "PRN-008", "neo1-083": "IP1-009", "neo1-084": "IP1-020", "neo2-004": "PRN-047", "neo2-020": "NIP2-018",
             "neo3-002": "NIP1-022"}

# 77 のワザの型（カード → ワザの位置の順の型）。新しい型はない
TYPES = {
    "neo1-006": (E.AttachEnergyFromHandOnHeads, E.DamageAndDrain), "neo1-012": (E.PoisonOpponent, E.ParalyzeOnHeads),
    "neo1-019": (E.DamageOnly, E.DamageOnly), "neo1-024": (E.AttackLockWhileSourceActiveOnHeads, E.CoinFlipDamage),
    "neo1-026": (E.LockOpponentAttack, E.CoinFlipDamage), "neo1-027": (E.SleepOpponent,), "neo1-028": (E.DamageThenSelfBarrierOnHeads,),
    "neo1-031": (E.DamageOnly, E.DamageAndOwnBenchDamage), "neo1-035": (E.DamageThenSelfBarrierOnHeads, E.DamageThenSwitchOpponentIfNotKnockedOut),
    "neo1-039": (E.DamageOnly, E.DamageIgnoringDefenderEffects), "neo1-047": (E.DamageThenSelfBarrierOnHeads, E.ConfuseOnHeads),
    "neo1-051": (E.DamageTimesOwnCounters, E.DamageOnly), "neo1-052": (E.PoisonOnHeads, E.DamageOnly), "neo1-059": (E.CoinFlipDamage,),
    "neo1-060": (E.PutToSleep, E.DamageOnly), "neo1-062": (E.CoinBonusDamage, E.ConfuseOnHeads), "neo1-064": (E.CoinBonusDamage, E.CoinFlipDamage),
    "neo1-066": (E.PoisonOpponent,), "neo2-001": (E.DamageAndSelfDamage,), "neo2-003": (E.PoisonOnHeads,), "neo2-004": (E.DamageOnly,),
    "neo2-013": (E.DamageOnly, E.PutToSleep), "neo2-020": (E.SelfDamageOnTails,), "neo2-034": (E.DamageOnly,),
    "neo2-037": (E.DamageOnly, E.DamageAndSelfDamage), "neo2-047": (E.ParalyzeOnHeads,), "neo3-001": (E.DamageOnly, E.PoisonWithoutDamage),
    "neo3-002": (E.DamageThenSleepOnHeads, E.DamageOnly), "neo3-003": (E.DamageOnly, E.ConfuseOnHeads), "neo3-012": (E.CoinFlipDamage,),
    "neo3-013": (E.DamageOnly, E.ParalyzeOnHeads), "neo3-037": (E.DamageOnly,), "neo3-038": (E.DamageOnly, E.DamageAndSelfDamage),
    "neo4-001": (E.DamageOnly, E.PoisonOpponent), "neo4-005": (E.DamageOnly,), "neo4-007": (E.DamageThenSelfBarrierOnHeads, E.DamageOnly),
    "neo4-009": (E.DamageOnly, E.CoinBonusDamage), "neo4-015": (E.DamageOnly,), "neo4-017": (E.DamageOnly,), "neo4-027": (E.DamageAndSelfDamage,),
    "neo4-028": (E.ExtraEnergyDamage,), "neo4-029": (E.ParalyzeOnHeads,), "neo4-030": (E.CoinFlipDamage,), "neo4-042": (E.DamageOnly,),
    "neo4-048": (E.SleepOpponent,), "neo4-049": (E.SleepOpponent, E.ParalyzeOnHeads), "neo4-069": (E.DamageOnly, E.DamageOnly),
    "neo4-072": (E.CoinBonusDamage,), "neo4-075": (E.CoinFlipDamage, E.FailOnTailsDamage), "neo4-086": (E.DamageOnly,),
}


def snapshot(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log], repr(state.rng.getstate())


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def mon(card, energy=(), **extra):
    return {"card": card, "energy": list(energy), **extra}


def board(hand=(), *, active, bench=(RATTATA,), opponent_active=None, opponent_bench=(RATTATA,), deck=DECK, opponent_hand=()):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": list(deck)}
    them = {"active": opponent_active or mon(HITMONCHAN, (FIGHTING, FIGHTING)), "bench": list(opponent_bench), "hand": list(opponent_hand), "deck": list(DECK)}
    return build_test_state([me, them], turn_number=TURN, current_player=0)


def attack(state, index, *coins, player=None, **options):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, UseAttack(state.current_player if player is None else player, index), **options)


def answer(state, choices):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)))


def last_damage(state):
    return [e for e in state.log if e["kind"] == "damage"][-1]


def without_v0_77(registry: EffectRegistry) -> EffectRegistry:
    """v0.77 で加えた登録（ワザ 77・トレーナー 2）だけを除いた登録表。"""
    attacks = {k: registry.attack_entry(k.card_id, k.attack_index) for k in registry.attack_keys() if k.card_id not in V0_77_CARDS}
    trainers = {c: registry.trainer_entry(c) for c in registry.trainer_ids() if c not in V0_77_CARDS}
    return EffectRegistry(registry.id, attacks, trainers, registry._powers, registry._energies)


def kyuura_targets():
    raw = subprocess.run(["git", "-C", str(ROOT.parent / "kyuura"), "show", f"{KYUURA_COMMIT}:data/engine_targets.json"],
                         capture_output=True, text=True, check=False)
    if raw.returncode != 0:
        return None
    data = json.loads(raw.stdout)
    return data["cards"] if isinstance(data, dict) else data


class RegistrationTest(unittest.TestCase):
    def test_registered_and_classified(self):
        """52 枚とも写しの組 pool_v0_77 にあり（id は kyuura の小文字の id のまま）、どのワザも（77）、2 枚のトレーナーも登録した。たね 44・1 進化 4・2 進化 2・特殊能力なし。"""
        extract = read_extract()
        self.assertEqual(tuple(extract["pool_v0_77"]), V0_77_CARDS)
        self.assertTrue(all(card.startswith(("neo1-", "neo2-", "neo3-", "neo4-")) and card == card.lower() for card in V0_77_CARDS))
        pool = load_card_pool()
        registry = E.DEFAULT_EFFECTS
        count = 0
        stages = Counter()
        for card_id in V0_77_POKEMON:
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertIn(card_id, pool.playable_ids)
                self.assertEqual(definition.powers, ())
                stages[definition.stage] += 1
                self.assertEqual(tuple(type(registry.attack_entry(card_id, i).effect) for i in range(len(definition.attacks))), TYPES[card_id])
                for index, attack_def in enumerate(definition.attacks):
                    entry = registry.attack_entry(card_id, index)
                    self.assertEqual(entry.name_ja, attack_def.name_ja)
                    self.assertEqual(entry.effect.check(attack_def), [])
                    self.assertEqual(entry.effect.card_problems(attack_def, definition.attacks), [])
                    count += 1
                    if attack_def.text_ja is None:
                        self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (None, None, None))
                    else:
                        self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (attack_def.text_ja, attack_def.text_ja, "kyuura data/cards.json"))
        self.assertEqual(count, 77)
        self.assertEqual(dict(stages), {"basic": 44, "stage1": 4, "stage2": 2})
        self.assertEqual(set(TYPES), set(V0_77_POKEMON))
        for card_id, effect_type in ((SUPER_SCOOP_UP_NEO1, E.CoinReturnOwnPokemonWithAttachedToHand), (BILLS_TELEPORTER_NEO1, E.CoinDrawTrainer)):
            entry = registry.trainer_entry(card_id)
            self.assertIs(type(entry.effect), effect_type)
            self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (pool.get(card_id).trainer_text_ja,) * 2 + ("kyuura data/cards.json",))
        self.assertEqual(registry.trainer_entry(BILLS_TELEPORTER_NEO1).effect.count, 4)

    def test_parameters_are_the_cards_own(self):
        """枚数・追加の量・自分へのダメージ・控えへのダメージ・水の追加は、それぞれのカードの印刷の値（既存のカードの値を写さない）。"""
        r = E.DEFAULT_EFFECTS
        flips = {(c, i): (r.attack_entry(c, i).effect.coins, r.attack_entry(c, i).effect.damage_per_heads)
                 for c, types in TYPES.items() for i, t in enumerate(types) if t is E.CoinFlipDamage}
        self.assertEqual(flips, {("neo1-024", 1): (3, 10), ("neo1-026", 1): (2, 20), ("neo1-059", 0): (3, 10), ("neo1-064", 1): (2, 30),
                                 ("neo3-012", 0): (2, 10), ("neo4-030", 0): (3, 10), ("neo4-075", 0): (2, 20)})
        bonuses = {(c, i): r.attack_entry(c, i).effect.bonus for c, types in TYPES.items() for i, t in enumerate(types) if t is E.CoinBonusDamage}
        self.assertEqual(bonuses, {("neo1-062", 0): 10, ("neo1-064", 0): 10, ("neo4-009", 1): 30, ("neo4-072", 0): 10})
        selfs = {(c, i): r.attack_entry(c, i).effect.self_damage for c, types in TYPES.items() for i, t in enumerate(types)
                 if t in (E.DamageAndSelfDamage, E.SelfDamageOnTails)}
        self.assertEqual(selfs, {("neo2-001", 0): 10, ("neo2-020", 0): 10, ("neo2-037", 1): 20, ("neo3-038", 1): 10, ("neo4-027", 0): 10})
        self.assertEqual(r.attack_entry(QUAGSIRE_NEO1, 1).effect, E.DamageAndOwnBenchDamage(10, True))
        self.assertEqual(r.attack_entry("neo4-028", 0).effect, E.ExtraEnergyDamage(EnergyType.WATER, 10, 2))
        self.assertEqual(r.attack_entry(HITMONLEE_NEO4, 1).effect, E.FailOnTailsDamage(1))
        self.assertEqual(r.attack_entry("neo1-006", 0).effect, E.AttachEnergyFromHandOnHeads(EnergyType.GRASS, 2))
        self.assertEqual(r.attack_entry(SUDOWOODO_NEO1, 0).effect, E.DamageTimesOwnCounters(10))
        self.assertEqual(r.attack_entry("neo3-001", 1).effect, E.PoisonWithoutDamage())  # ダメージのないどく（ダメージのある PoisonOpponent ではない）
        # 文面の確かめは一律に緩めていない: 違う値・違う型は受け付けない
        pool = load_card_pool()
        quagsire = pool.get(QUAGSIRE_NEO1).attacks[1]
        self.assertNotEqual(E.DamageAndOwnBenchDamage(10, False).check(quagsire), [])  # JS1 の書かれていない型にしない
        self.assertNotEqual(E.DamageAndOwnBenchDamage(20, True).check(quagsire), [])
        self.assertNotEqual(E.CoinBonusDamage(10).check(pool.get("neo4-009").attacks[1]), [])
        self.assertNotEqual(E.CoinFlipDamage(coins=2, damage_per_heads=10).check(pool.get("neo4-030").attacks[0]), [])
        self.assertNotEqual(E.PoisonOpponent().check(pool.get("neo3-001").attacks[1]), [])
        self.assertNotEqual(E.SelfBarrierOnHeads().check(pool.get(KINGDRA_NEO1).attacks[0]), [])

    def test_unregistered_before_and_without_the_v0_77_entries(self):
        """v0.77 の登録だけを除くと、52 枚とも未対応にもどり、ほかのカードの対応は変わらない（追加前は未登録だった）。"""
        reduced = without_v0_77(E.DEFAULT_EFFECTS)
        self.assertFalse([k for k in reduced.attack_keys() if k.card_id in V0_77_CARDS])
        self.assertFalse(set(reduced.trainer_ids()) & set(V0_77_CARDS))
        before = pool_from_extract(read_extract(), reduced)
        after = load_card_pool()
        self.assertFalse(before.playable_ids & set(V0_77_CARDS))
        self.assertEqual(after.playable_ids - before.playable_ids, frozenset(V0_77_CARDS))
        self.assertEqual(len(before.playable_ids), 1028)  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚（ワザ 14・特殊能力 12）を加えた  # v0.85 でポケモン 13 枚（ワザ 17・特殊能力 9）・ミラクルエネルギーを加えた  # v0.84 でポケモン 12 枚・ポケモン育て屋夫婦を加えた  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.78 の 13 枚・v0.79 の 52 枚・v0.80 の 30 枚を含む（v0.77 では 826）  # v0.83 でポケモン 18 枚（ワザ 33）を加えた
        for card in V0_77_CARDS:
            self.assertFalse(before.get(card).supported)
        self.assertFalse(set(E.EQUIVALENT_CARDS) & set(V0_77_CARDS))
        self.assertFalse(set(E.REPRINT_CARDS) & set(V0_77_CARDS))

    def test_same_data_cards_share_one_registration(self):
        """前の版のカードと日本語のゲーム用データ（名前・HP・タイプ・弱点・抵抗力・にげる・段階・進化元・ワザ・トレーナーの文面）が同じ 7 枚は、登録の値を共有する（id は消さない）。
        52 枚どうしに同じデータのカードはなく、名前が同じだけのカード（ワニノコ neo4-028・ウリムー 3 枚・ポポッコ 2 枚・メリープ neo4-042 など）はまとめない。"""
        pool = load_card_pool()
        registry = E.DEFAULT_EFFECTS

        def view(card):
            d = pool.get(card)
            if d.category == "trainer":
                return d.name_ja, d.category, d.trainer_text_ja
            return (d.name_ja, d.hp, d.pokemon_type, d.weakness, d.resistance, d.resistance_value, d.retreat_cost, d.stage, d.evolves_from,
                    tuple((a.name_ja, a.cost, a.damage, a.damage_modifier, a.text_ja) for a in d.attacks))

        self.assertEqual({**E.SAME_DATA_CARDS_V0_77, **E.SAME_DATA_TRAINERS_V0_77}, SAME_DATA)
        others = [c for c in pool.playable_ids if c not in V0_77_CARDS]
        for card in V0_77_CARDS:
            with self.subTest(card=card):
                same = sorted(o for o in others if view(o) == view(card))
                self.assertEqual(bool(same), card in SAME_DATA)
                if card in SAME_DATA:
                    self.assertIn(SAME_DATA[card], same)
        self.assertEqual(len({view(c) for c in V0_77_CARDS}), 52)  # 52 枚どうしは 52 通り
        for new, original in E.SAME_DATA_CARDS_V0_77.items():
            for index in range(len(pool.get(new).attacks)):
                self.assertIs(registry.attack_entry(new, index), registry.attack_entry(original, index))
        for new, original in E.SAME_DATA_TRAINERS_V0_77.items():
            self.assertIs(registry.trainer_entry(new), registry.trainer_entry(original))
        # 同じデータのほかの id（PRN-011・IP2-029・IP2-021）も同じ値
        self.assertIs(registry.attack_entry(TOTODILE_NEO1, 0), registry.attack_entry("PRN-011", 0))
        self.assertIs(registry.trainer_entry(SUPER_SCOOP_UP_NEO1), registry.trainer_entry("IP2-029"))
        self.assertIs(registry.trainer_entry(BILLS_TELEPORTER_NEO1), registry.trainer_entry("IP2-021"))

    def test_counts_from_the_registry(self):
        """対応するカード 878（ポケモン 635・トレーナー 213・エネルギー 30）、ワザ 1,072・特殊能力 74・トレーナー 213・特殊エネルギー 12（登録から数える）。v0.78 で悪・鋼
        エネルギー 5 枚とポケモン 8 枚（ワザ 16）、v0.79 でポケモン 52 枚（ワザ 94）を加えたので、今の数は 943（695・213・35）、ワザ 1,182・特殊エネルギー 17。"""
        pool = load_card_pool()
        categories = Counter(pool.get(card).category for card in pool.playable_ids)
        self.assertEqual((len(pool.playable_ids), categories["pokemon"], categories["trainer"], categories["energy"]), (1080, 783, 260, 37))  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚（ワザ 14・特殊能力 12）を加えた  # v0.85 でポケモン 13 枚（ワザ 17・特殊能力 9）・ミラクルエネルギーを加えた  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚）・停止コード 9 件を加えた  # v0.83 でポケモン 18 枚（ワザ 33）を加えた  # v0.84 でポケモン 12 枚（ワザ 19・特殊能力 5）・ポケモン育て屋夫婦を加えた
        registry = E.DEFAULT_EFFECTS
        self.assertEqual((len(registry.attack_keys()), len(registry.power_keys()), len(registry.trainer_ids()), len(registry.energy_ids())), (1312, 114, 260, 19))  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚（ワザ 14・特殊能力 12）を加えた  # v0.85 でポケモン 13 枚（ワザ 17・特殊能力 9）・ミラクルエネルギーを加えた  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚を含む）を加えた  # v0.83 でポケモン 18 枚（ワザ 33）を加えた  # v0.84 でポケモン 12 枚（ワザ 19・特殊能力 5）・ポケモン育て屋夫婦を加えた
        self.assertEqual(len(read_extract()["cards"]), 1080)  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚（ワザ 14・特殊能力 12）を加えた  # v0.85 でポケモン 13 枚（ワザ 17・特殊能力 9）・ミラクルエネルギーを加えた  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚）・停止コード 9 件を加えた  # v0.83 でポケモン 18 枚（ワザ 33）を加えた  # v0.84 でポケモン 12 枚（ワザ 19・特殊能力 5）・ポケモン育て屋夫婦を加えた

    def test_unsupported_counts_with_neo_in_scope(self):
        """kyuura data/engine_targets.json（7d3f4ca）の対象 1,377 件（PMCG1〜6 の 457・拡張パック以外の 597・neo の 323）から登録を差し引く。全対象の未対応 499・
        neo の未対応 271・拡張パック以外の未対応 228（v0.76 は 551・323・228）。engine_targets.json の分類（engine_status）は v0.68 の時点の索引なので使わない。
        v0.78 で 13 枚（neo 8・拡張パック以外 5）、v0.79 で 52 枚（neo 36・拡張パック以外 16）を加えたので、今の数は 434・227・207。"""
        targets = kyuura_targets()
        if targets is None:
            self.skipTest("../kyuura がない")
        pool = load_card_pool()
        ids = [x["id"] for x in targets]
        neo = [x["id"] for x in targets if x["id"].startswith("neo")]
        non_pack = [x["id"] for x in targets if x["product_group"] != "expansion_pack"]
        pmcg = [x["id"] for x in targets if x["id"].startswith("PMCG")]
        self.assertEqual((len(ids), len(pmcg), len(non_pack), len(neo)), (1377, 457, 597, 323))
        self.assertTrue(pool.playable_ids <= set(ids))
        self.assertEqual(sum(1 for c in ids if c not in pool.playable_ids), 297)  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚（ワザ 14・特殊能力 12）を加えた  # v0.85 でポケモン 13 枚（ワザ 17・特殊能力 9）・ミラクルエネルギーを加えた  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚）・停止コード 9 件を加えた  # v0.79 で 52 枚を加えた  # v0.78 で 13 枚を加えた（v0.77 は 499）  # v0.83 でポケモン 18 枚（ワザ 33）を加えた  # v0.84 でポケモン 12 枚（ワザ 19・特殊能力 5）・ポケモン育て屋夫婦を加えた
        self.assertEqual(sum(1 for c in neo if c not in pool.playable_ids), 137)  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚（ワザ 14・特殊能力 12）を加えた  # v0.85 でポケモン 13 枚（ワザ 17・特殊能力 9）・ミラクルエネルギーを加えた  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.81 で neo のトレーナー 11 枚（ポケモンのどうぐ・スタジアム）を加えた  # v0.80 で neo のトレーナー 25 枚を加えた  # v0.79 で neo 36 枚を加えた  # v0.77 は 271  # v0.83 でポケモン 18 枚（ワザ 33）を加えた  # v0.84 でポケモン 12 枚（ワザ 19・特殊能力 5）・ポケモン育て屋夫婦を加えた
        self.assertEqual(sum(1 for c in non_pack if c not in pool.playable_ids), 160)  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚（ワザ 14・特殊能力 12）を加えた  # v0.85 でポケモン 13 枚（ワザ 17・特殊能力 9）・ミラクルエネルギーを加えた  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.81 でトレーナー 15 枚（拡張パック以外 4 枚）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚）・停止コード 9 件を加えた  # v0.79 で拡張パック以外 16 枚を加えた  # v0.77 は 228  # v0.83 でポケモン 18 枚（ワザ 33）を加えた
        self.assertEqual(Counter(x["jp_set"] for x in targets if x["id"].startswith("neo")), Counter({"neo1": 96, "neo2": 57, "neo3": 57, "neo4": 113}))

    def test_other_cards_in_the_copy_are_unchanged(self):
        """写しの作り直しで、v0.76 の 826 枚の記録は変わっていない（v0.77 の 52 枚を加えただけ）。"""
        raw = subprocess.run(["git", "-C", str(ROOT), "show", f"{V076_COMMIT}:kyuura_engine/data/kyuura_cards.json"], capture_output=True, text=True, check=False)
        if raw.returncode != 0:
            self.skipTest("v0.76 のコミットがない")
        old = json.loads(raw.stdout)
        new = read_extract()
        old_cards = {c["id"]: c for c in old["cards"]}
        new_cards = {c["id"]: c for c in new["cards"]}
        self.assertEqual(set(new_cards) - set(old_cards), set(V0_77_CARDS) | set(read_extract()["pool_v0_78"]) | set(read_extract()["pool_v0_79"]) | set(read_extract()["pool_v0_80"]) | set(read_extract()["pool_v0_81"]) | set(read_extract()["pool_v0_82"]) | set(read_extract()["pool_v0_83"]) | set(read_extract()["pool_v0_84"]) | set(read_extract()["pool_v0_85"]) | set(read_extract()["pool_v0_86"]) | set(read_extract()["pool_v0_87"]))  # v0.78 の 13 枚・v0.79 の 52 枚も加えた
        self.assertEqual({k: v for k, v in new_cards.items() if k in old_cards}, old_cards)
        self.assertEqual(new["source"], old["source"])
        for key in old:
            if key.startswith("pool_"):
                self.assertEqual(new[key], old[key])

    def test_records(self):
        """採用の記録（52 件。外部照合なし。kyuura の記録の id なし。ガイドブックの項目なし）と、研究の対応表の印刷の文面の一覧（説明文のあるワザ 50）。照合の記録には加えない。"""
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        verification = json.loads((ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8"))
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        adopted = set(links["latest_descriptions"]["adopted_printed_text"])
        pool = load_card_pool()
        texts = 0
        for card in V0_77_CARDS:
            with self.subTest(card=card):
                record = sources[card]
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["external_checks"], record["kyuura_records"]),
                                 ("kyuura_data", "adopted", KYUURA_COMMIT, [], []))
                self.assertNotIn("P43", record["notes"].replace("「P43 p.xx」", ""))
                self.assertNotIn(card, json.dumps(verification, ensure_ascii=False))
                if card in V0_77_TRAINERS:
                    self.assertEqual(record["play_text"], {"trainer": "kyuura_printed_text"})
                    continue
                for index, attack_def in enumerate(pool.get(card).attacks):
                    key = f"attack/{index}"
                    self.assertEqual(key in record["play_text"], attack_def.text_ja is not None)
                    self.assertEqual(f"{card}/{key}" in adopted, attack_def.text_ja is not None)
                    texts += attack_def.text_ja is not None
        self.assertEqual(texts, 50)
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (197, 199))  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚（ワザ 14・特殊能力 12）を加えた  # v0.85 でポケモン 13 枚（ワザ 17・特殊能力 9）・ミラクルエネルギーを加えた  # v0.84 で RF1・WD1・WD2 を加えた  # v0.83 で RS1・LT1 を加えた  # v0.81a で MH2 を加えた  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚）・停止コード 9 件を加えた  # v0.79 で PK1 を加えた  # v0.78 で MT1・DE1 を加えた（v0.77 は 163・165）

    def test_rule_base_and_release_dates_are_kept(self):
        """発売日は写しの欄のまま（neo1 は 2000.02.14 版の前、neo2〜neo4 はあと）。ルールの基準は 2000.02.14 版のまま（カードの範囲を広げただけ）。"""
        targets = kyuura_targets()
        if targets is None:
            self.skipTest("../kyuura がない")
        by_id = {x["id"]: x for x in targets}
        for card in V0_77_CARDS:
            self.assertEqual(by_id[card]["released_after_rule_base"], not card.startswith("neo1-"))
            self.assertEqual((by_id[card]["product_group"], by_id[card]["play_scope"]), ("expansion_pack", "standard"))


class EvolutionLineTest(unittest.TestCase):
    """進化は名前の完全一致と段階で決まる（カード id・商品で限らない）。通常の進化の制限は変えない。"""

    def evolve(self, card, below, stack=None):
        base = mon(below, evolved_from=stack) if stack else mon(below)
        state = build_test_state([{"active": base, "bench": [RATTATA], "hand": [card], "deck": DECK},
                                  {"active": mon(HITMONCHAN), "bench": [RATTATA], "deck": DECK}], turn_number=TURN, current_player=0)
        uid = state.players[0].hand[0]
        return apply_kernel(state, EvolvePokemon(0, uid, state.players[0].active.pokemon_id))

    def test_lines_across_products(self):
        cases = ((SKIPLOOM_NEO1, "PRN-047", None), (SKIPLOOM_NEO1, "neo2-004", None), (SKIPLOOM_NEO3, "neo2-004", None), (SKIPLOOM_NEO3, "PRN-047", None),
                 (QUAGSIRE_NEO1, WOOPER_PRN, None), (QUAGSIRE_NEO1, WOOPER_NEO1, None), (FURRET_NEO1, SENTRET_NEO1, None),
                 (KINGDRA_NEO1, SEADRA, HORSEA), (POLIWRATH_NEO2, POLIWHIRL, "PMCG1-024"), (POLIWRATH_NEO2, "ES1-017", "ES1-016"),
                 (POLIWRATH_NEO2, "QSG-015", "QSG-014"))
        for card, below, stack in cases:
            with self.subTest(card=card, below=below):
                state = self.evolve(card, below, stack)
                self.assertEqual(state.cards[state.players[0].active.card].card_id, card)
                audited(self, state)

    def test_wrong_lines_and_turn_restriction(self):
        with self.assertRaises(IllegalActionError):
            self.evolve(FURRET_NEO1, RATTATA)
        with self.assertRaises(IllegalActionError):
            self.evolve(KINGDRA_NEO1, HORSEA)  # 1 進化を飛ばす通常の進化はしない
        state = build_test_state([{"active": mon(WOOPER_NEO1), "bench": [RATTATA], "hand": [QUAGSIRE_NEO1], "deck": DECK},
                                  {"active": mon(HITMONCHAN), "bench": [RATTATA], "deck": DECK}], turn_number=1, current_player=0)
        with self.assertRaises(IllegalActionError):
            apply_kernel(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].active.pokemon_id))  # おたがいの最初の番

    def test_breeder_lineage_and_stages(self):
        pool = load_card_pool()
        self.assertEqual(pool.get(KINGDRA_NEO1).stage1_evolves_from, ("タッツー",))
        self.assertEqual(pool.get(POLIWRATH_NEO2).stage1_evolves_from, ("ニョロモ",))
        self.assertEqual(pool.get("neo1-066").stage, "basic")  # トゲピーはたねポケモンのまま（ベイビィの規定を加えない）
        state = build_test_state([{"active": mon(HORSEA), "bench": [RATTATA], "hand": [POKEMON_BREEDER, KINGDRA_NEO1], "deck": DECK},
                                  {"active": mon(HITMONCHAN), "bench": [RATTATA], "deck": DECK}], turn_number=TURN, current_player=0)
        breeder = next(u for u in state.players[0].hand if state.cards[u].card_id == POKEMON_BREEDER)
        state = apply_kernel(state, PlayTrainer(0, breeder))
        while state.decision is not None:
            state = answer(state, (state.decision.options[0],))
        self.assertEqual(state.cards[state.players[0].active.card].card_id, KINGDRA_NEO1)
        audited(self, state)


class LeerAndAmnesiaTest(unittest.TestCase):
    """にらみつける（ワニノコ neo1-024）・ドわすれ（ウパー neo1-026）: v0.76・v0.35 と同じ型。"""

    def test_leer_heads_locks_until_end_of_next_opponent_turn(self):
        before = board(active=mon(TOTODILE_NEO1, (WATER,)))
        heads = attack(before, 0, H)
        self.assertEqual([type(e) for e in heads.players[1].active.persistent_effects], [CannotAttackWhileSourceActive])
        with self.assertRaises(IllegalActionError):
            apply_kernel(heads, UseAttack(1, 0))
        ended = apply_kernel(heads, EndTurn(1))
        self.assertEqual(ended.players[1].active.persistent_effects, ())  # 次の相手の番の終わりに消える
        audited(self, ended)
        tails = attack(before, 0, T)
        self.assertEqual(tails.players[1].active.persistent_effects, ())
        self.assertEqual(attack(tails, 0, player=1).turn_number, TURN + 2)

    def test_amnesia_chooses_one_attack(self):
        state = attack(board(active=mon(WOOPER_NEO1, (WATER,))), 0)
        d = state.decision
        self.assertEqual((d.kind, d.player, d.options), (SELECT_OPPONENT_ATTACK, 0, (0, 1)))
        before = snapshot(state)
        for bad in (ResolveDecision(0, d.id, (5,)), ResolveDecision(1, d.id, (0,)), ResolveDecision(0, d.id, (0, 1))):
            with self.assertRaises(IllegalActionError):
                apply_kernel(state, bad)
        self.assertEqual(snapshot(state), before)  # 不正な答えで状態・ログ・乱数は変わらない
        locked = answer(state, (1,))
        effect = next(e for e in locked.players[1].active.persistent_effects if isinstance(e, CannotUseAttack))
        self.assertEqual((effect.target_attack_index, effect.active_turn), (1, TURN + 1))
        with self.assertRaises(IllegalActionError):
            apply_kernel(locked, UseAttack(1, 1))
        self.assertEqual(attack(locked, 0, player=1).turn_number, TURN + 2)  # ほかのワザは使える
        expected = snapshot(locked)
        for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            self.assertEqual(snapshot(answer(copied, (1,))), expected)
        audited(self, locked)


class TwisterTest(unittest.TestCase):
    """りゅうのたつまき（キングドラ neo1-035）: ダメージのあと、相手が「きぜつ」しなければ、ワザを使ったプレイヤーが相手の控えを選んで入れ替える。"""

    def kingdra(self, **extra):
        return board(active=mon(KINGDRA_NEO1, (WATER,) * 4, evolved_from=[HORSEA, SEADRA]), opponent_bench=(RATTATA, "PMCG1-061"), **extra)

    def test_attacker_chooses_and_switches(self):
        state = attack(self.kingdra(), 1)
        d = state.decision
        bench = [p.pokemon_id for p in state.players[1].bench]
        self.assertEqual((d.kind, d.player, d.options), (FORCED_SWITCH, 0, tuple(bench)))
        self.assertEqual(last_damage(state)["amount"], 50)
        with self.assertRaises(IllegalActionError):
            apply_kernel(state, ResolveDecision(1, d.id, (bench[0],)))  # 相手には選ばせない（ふきとばしではない）
        switched = answer(state, (bench[1],))
        self.assertEqual(switched.players[1].active.pokemon_id, bench[1])
        expected = snapshot(switched)
        for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            self.assertEqual(snapshot(answer(copied, (bench[1],))), expected)
        audited(self, switched)

    def test_no_switch_when_knocked_out_or_without_bench(self):
        knocked = attack(self.kingdra(opponent_active=mon(RATTATA)), 1)
        self.assertNotEqual(getattr(knocked.decision, "kind", None), FORCED_SWITCH)
        self.assertIn("forced_switch_skipped", [e["kind"] for e in knocked.log])
        alone = attack(board(active=mon(KINGDRA_NEO1, (WATER,) * 4, evolved_from=[HORSEA, SEADRA]), opponent_bench=()), 1)
        self.assertIsNone(alone.decision)
        audited(self, alone)

    def test_agility_barrier(self):
        heads = attack(self.kingdra(), 0, H)
        self.assertEqual([type(e) for e in heads.players[0].active.persistent_effects], [AttackBarrier])
        tails = attack(self.kingdra(), 0, T)
        self.assertEqual(tails.players[0].active.persistent_effects, ())


class OtherRepresentativesTest(unittest.TestCase):
    def test_earthquake_hits_own_bench_without_weakness(self):
        """じしん（ヌオー）: 相手に 60、自分の控え全員に「弱点・抵抗力」に関係なく 10（相手の控えにはない）。"""
        state = board(active=mon(QUAGSIRE_NEO1, (FIGHTING, FIGHTING, WATER, WATER), evolved_from=WOOPER_NEO1), bench=(RATTATA, "PMCG2-021"))
        done = attack(state, 1)
        damages = [e for e in done.log if e["kind"] == "damage"]
        self.assertEqual([(e.get("target", "opponent_active"), e["amount"]) for e in damages], [("opponent_active", 60), ("self_bench", 10), ("self_bench", 10)])
        self.assertEqual([p.damage for p in done.players[1].bench], [0])
        self.assertTrue(all(e.get("ignore_weakness_resistance") for e in damages[1:]))
        audited(self, done)

    def test_flail_and_hi_jump_kick_and_speed_star(self):
        """じたばた（0 個なら 0）・かかとおとし（「うら」はワザの失敗で、0 ダメージとは別）・スピードスター（相手の弱点を計算しない）。"""
        zero = attack(board(active=mon(SUDOWOODO_NEO1, (FIGHTING,))), 0)
        self.assertEqual(last_damage(zero)["steps"][0], ("1 基本となる計算", 0))
        two = attack(board(active=mon(SUDOWOODO_NEO1, (FIGHTING,), damage=20)), 0)
        self.assertEqual(last_damage(two)["steps"][0], ("1 基本となる計算", 20))
        failed = attack(board(active=mon(HITMONLEE_NEO4, (FIGHTING,) * 3)), 1, T)
        self.assertIn("attack_failed", [e["kind"] for e in failed.log])
        self.assertFalse([e for e in failed.log if e["kind"] == "damage"])
        hit = attack(board(active=mon(HITMONLEE_NEO4, (FIGHTING,) * 3)), 1, H)
        self.assertEqual(last_damage(hit)["amount"], 60)
        # 相手の弱点 雷（第2弾のトサキント PMCG2-021 は弱点 雷）: スピードスターは 30 のまま、パンチは弱点を計算する
        star = attack(board(active=mon(ELECTABUZZ_NEO1, (LIGHTNING,) * 3), opponent_active=mon("PMCG2-021")), 1)
        self.assertEqual(last_damage(star)["amount"], 30)
        punch = attack(board(active=mon(ELECTABUZZ_NEO1, (LIGHTNING,) * 2), opponent_active=mon("PMCG2-021")), 0)
        self.assertEqual(last_damage(punch)["amount"], 40)

    def test_water_gun_counts_extra_water_up_to_two(self):
        three = attack(board(active=mon("neo4-028", (WATER,) * 3)), 0)
        self.assertEqual(last_damage(three)["steps"][0], ("1 基本となる計算", 30))
        five = attack(board(active=mon("neo4-028", (WATER,) * 5)), 0)
        self.assertEqual(last_damage(five)["steps"][0], ("1 基本となる計算", 30))
        mixed = attack(board(active=mon("neo4-028", (WATER, FIRE, GRASS))), 0)
        self.assertEqual(last_damage(mixed)["steps"][0], ("1 基本となる計算", 10))

    def test_preflight_modes_agree(self):
        cases = ((board(active=mon(TOTODILE_NEO1, (WATER,))), 0, (H,)), (board(active=mon(WOOPER_NEO1, (WATER, WATER))), 1, (H, T)),
                 (board(active=mon(KINGDRA_NEO1, (WATER,) * 4, evolved_from=[HORSEA, SEADRA])), 1, ()),
                 (board(active=mon(HITMONLEE_NEO4, (FIGHTING,) * 3)), 1, (T,)), (board(active=mon("neo1-006", (GRASS,)), hand=[GRASS, GRASS]), 0, (H,)))
        for state, index, coins in cases:
            with self.subTest(card=state.cards[state.players[0].active.card].card_id):
                results = {mode: repr(snapshot(attack(state, index, *coins, preflight=mode))) for mode in PREFLIGHT_MODES}
                self.assertEqual(len(set(results.values())), 1)


class TrainerTest(unittest.TestCase):
    """スーパーポケモン回収・マサキの転送装置（neo1）: v0.73 の同じ文面の登録と同じ型・同じ値。v0.73 の動きのテストを、カードの定数だけを neo1 の id に置きかえて走らせる
    （下の ScoopUpAndTeleporterNeoTest）。ここでは山札 0 枚のマサキの転送装置を確かめる。"""

    def test_teleporter_with_empty_deck_draws_nothing_and_does_not_lose(self):
        state = build_test_state([{"active": mon(HITMONCHAN), "bench": [RATTATA], "hand": [BILLS_TELEPORTER_NEO1], "deck": []},
                                  {"active": mon(HITMONCHAN), "bench": [RATTATA], "deck": DECK}], turn_number=TURN, current_player=0)
        done = apply_kernel(with_coin_results(state, H), PlayTrainer(0, state.players[0].hand[0]))
        self.assertEqual((len(done.players[0].hand), done.phase), (0, Phase.MAIN))
        audited(self, done)


def substituted(module_name: str, class_name: str, names: dict[str, str]):
    """``module_name`` のテストのクラスを、モジュールのカードの定数（``names``: 定数の名前 → 同じデータの v0.77 の id）だけを置きかえて走らせるクラス（v0.69 の
    ``substituted`` と同じ考え方。テストの中身・期待は変えない）。"""
    module = importlib.import_module(module_name)
    base = getattr(module, class_name)

    class Substituted(base):
        @classmethod
        def setUpClass(cls):
            cls._saved = {name: getattr(module, name) for name in names}
            for name, value in names.items():
                if SAME_DATA.get(value) != cls._saved[name]:
                    raise AssertionError(f"{value} は {name}（{cls._saved[name]}）と同じデータの v0.77 のカードではない")
                setattr(module, name, value)
            super().setUpClass()

        @classmethod
        def tearDownClass(cls):
            try:
                super().tearDownClass()
            finally:
                for name, value in cls._saved.items():
                    setattr(module, name, value)

    Substituted.__name__ = Substituted.__qualname__ = f"{class_name}Neo"
    return Substituted


ScoopUpAndTeleporterNeoTest = substituted("tests.test_search_recovery_trainers_v0_73", "ScoopUpAndTeleporterTest",
                                          {"SUPER_SCOOP_UP": SUPER_SCOOP_UP_NEO1, "BILLS_TELEPORTER": BILLS_TELEPORTER_NEO1})


class SecretPlanAndQuizTest(unittest.TestCase):
    """マチスの秘策の試すカードは公開の情報（対応しているカードの一覧）だけから作る。カツラのクイズの答えの候補に新しい名前 17 が加わる。"""

    def test_secret_plan_candidates(self):
        pool = load_card_pool()
        candidates = engine_module._identity_candidates(pool)
        new = set(candidates) & set(V0_77_CARDS)
        self.assertFalse(new & set(SAME_DATA))  # 同じデータの 7 枚は前の版のカードで代表する
        self.assertEqual(new, set(V0_77_CARDS) - set(SAME_DATA))
        basics = [c for c in candidates if pool.get(c).is_basic_pokemon]
        self.assertEqual(engine_module._IDENTITY_TRIAL_LIMIT, 512)
        self.assertLessEqual(1 + len(basics) + 1, engine_module._IDENTITY_TRIAL_LIMIT)

    def test_quiz_names(self):
        extract = read_extract()
        cards = {c["id"]: c for c in extract["cards"]}
        earlier = {cards[c]["name"]["ja"] for c in cards if c not in V0_77_CARDS and c not in extract["pool_v0_79"] and c not in extract["pool_v0_82"] and c not in extract["pool_v0_83"] and c not in extract["pool_v0_84"] and c not in extract["pool_v0_85"] and c not in extract["pool_v0_86"] and cards[c]["category"] == "pokemon"}  # v0.79・v0.82 で同じ名前のカードを加えた
        new = sorted({cards[c]["name"]["ja"] for c in V0_77_POKEMON} - earlier)
        # トゲピー・ノコッチ・ホーホーは拡張パック以外の商品のカードで前からある名前
        self.assertEqual(new, sorted(["マンタイン", "ヌオー", "キングドラ", "キリンリキ", "ウソッキー", "グライガー", "オタチ", "オドシシ", "オオタチ", "ウリムー",
                                      "ポポッコ", "イトマル", "ヨーギラス", "ゴマゾウ", "ヘラクロス", "クヌギダマ", "マグマッグ"]))
        self.assertEqual(len(new), 17)
        state = build_test_state([{"active": "PMCG1-018"}, {"active": "PMCG1-018"}])
        names = E.quiz_answer_names(state)
        self.assertEqual(len(names), len(set(names)))
        for name in new:
            self.assertIn(name, names)


class DocumentTest(unittest.TestCase):
    def test_document_exists_and_names_the_cards(self):
        text = DOC.read_text(encoding="utf-8")
        for card in V0_77_CARDS:
            self.assertIn(card, text)
        for word in ("1,377", "499", "271", "228", "DamageAndOwnBenchDamage", "DamageThenSwitchOpponentIfNotKnockedOut", "CoinReturnOwnPokemonWithAttachedToHand",
                     "CoinDrawTrainer", "書き出しの形式は 22", "neo1-057"):
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()
