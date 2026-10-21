"""v0.78: 悪・鋼エネルギー（特殊エネルギー 5 枚）と、「悪」「鋼」エネルギーを使うポケモン 8 枚・ワザ 16（docs/darkness-metal-energy-v0.78.md）。

どれも kyuura データの採用（採用したデータのコミット 7d3f4ca。処理に使う文面は kyuura の印刷の文面。id は kyuura の id のまま）。ガイドブックは読んでいない。
ダメージの段階は kyuura の GR-2000-P321-DAMAGE-ORDER（ワザを使うポケモンについているカードは 5 段階、受けるポケモンについているカードは 7 段階）、ポケモンチェックの順番は
GR-2000-P323-POKEMON-CHECK（指示されたこと → どく → ねむり → マヒ）、ダメージカウンターをのせることはダメージではない（GR-2000-P320-COUNTER-MOVE）。鋼エネルギーの
受けるダメージの範囲の日英の違いは kyuura data/curation/card_differences.json の neo1-095（確実。日本語にしたがう）。
"""

from __future__ import annotations

import pathlib
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy,
    EndTurn,
    IllegalActionError,
    Phase,
    PlayTrainer,
    Retreat,
    UnsupportedError,
    UseAttack,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine import engine as engine_module
from kyuura_engine.cards import (
    can_pay_with_units,
    load_card_pool,
    pool_from_extract,
    read_extract,
)
from kyuura_engine.coins import CoinSide
from kyuura_engine.deck import validate_deck
from kyuura_engine.effects import EffectRegistry, EnergyType
from kyuura_engine.errors import DeckValidationError
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import CannotAttackNextOwnTurn, CannotRetreat, DamageReduction
from tests.helpers import (
    BROCKS_MANKEY,
    BROCKS_PRIMEAPE,
    BROCKS_RHYDON,
    BROCKS_RHYHORN,
    DARKNESS_ENERGY_NEO1,
    DARKNESS_ENERGY_NIP2X,
    DARKNESS_ENERGY_PRN,
    DEFENDER,
    DIGGER,
    ELECTABUZZ_NEO1,
    FIGHTING,
    GRIMER,
    HITMONCHAN,
    HOUNDOUR_NEO2,
    HOUNDOUR_NEO4,
    HOUNDOUR_NIP2X,
    KABUTO,
    LIGHTNING,
    MACHAMP,
    MACHOKE,
    MACHOP,
    METAL_ENERGY_NEO1,
    METAL_ENERGY_NIP1X,
    MR_MIME,
    MUK,
    MYSTERIOUS_FOSSIL,
    ONIX,
    PLUSPOWER,
    POLIWAG,
    POLIWHIRL,
    POLIWRATH_NEO2,
    QUAGSIRE_NEO1,
    RAINBOW_ENERGY,
    RATTATA,
    SCIZOR_NEO2,
    SCYTHER,
    SKARMORY_NEO1,
    SKARMORY_NIP1X,
    SNEASEL_NEO1,
    STEELIX_NEO1,
    V0_78_CARDS,
    V0_78_ENERGIES,
    V0_78_POKEMON,
    WATER,
    WOOPER_NEO1,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import observation_problems, serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "darkness-metal-energy-v0.78.md"
H, T = CoinSide.HEADS, CoinSide.TAILS
TURN = 7
DECK = [WATER] * 12
DK, MT, MX, DC, DP = DARKNESS_ENERGY_NEO1, METAL_ENERGY_NEO1, METAL_ENERGY_NIP1X, DARKNESS_ENERGY_NIP2X, DARKNESS_ENERGY_PRN
DARK_RATICATE = "PMCG4-046"  # わるいラッタ（コラッタから進化。無色。「わるい」ポケモン）
SKARMORY_PF3 = "PF3-009"  # エアームド（こうそくいどう（鋼無無）。v0.72 で登録。鋼エネルギーがなく使えなかった）

TYPES = {
    SNEASEL_NEO1: (E.CoinFlipDamage, E.CoinsPerOwnPokemonDamage),
    STEELIX_NEO1: (E.DamageOnly, E.CoinBonusDamage),
    SKARMORY_NEO1: (E.FailOnTailsDamage, E.DamageThenReduceDamageNextTurn),
    HOUNDOUR_NEO2: (E.DamageOnly, E.DiscardOpponentTrainersThenDamage),
    SCIZOR_NEO2: (E.HalfRemainingHpDamage, E.CoinsHeadsTimesBonusDamage),
    HOUNDOUR_NEO4: (E.RetreatLockWithoutDamage, E.FailOnTailsDamage),
    SKARMORY_NIP1X: (E.DamageOnly, E.DamageThenSelfCannotAttack),
    HOUNDOUR_NIP2X: (E.DamageOnly, E.DiscardOpponentTrainersThenDamage),
}
ENERGY_TYPES = {DK: (E.DarknessEnergy, E.PENALTY_DAMAGE), DP: (E.DarknessEnergy, E.PENALTY_DAMAGE), DC: (E.DarknessEnergy, E.PENALTY_COUNTER),
                MT: (E.MetalEnergy, False), MX: (E.MetalEnergy, True)}


def mon(card, energy=(), **extra):
    return {"card": card, "energy": list(energy), **extra}


def board(*, active, opponent_active, bench=(RATTATA,), opponent_bench=(RATTATA,), hand=(), current=0):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": list(DECK)}
    them = {"active": opponent_active, "bench": list(opponent_bench), "hand": [], "deck": list(DECK)}
    return build_test_state([me, them], turn_number=TURN, current_player=current)


def attack(state, index, *coins, **options):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, UseAttack(state.current_player, index), **options)


def new_events(before, after, *kinds):
    return [e for e in after.log[len(before.log):] if not kinds or e["kind"] in kinds]


def damages(before, after):
    return [(e.get("target", "opponent_active"), e["amount"], tuple(label for label, _ in e["steps"])) for e in new_events(before, after, "damage")]


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def without_v0_78(registry: EffectRegistry) -> EffectRegistry:
    """v0.78 で加えた登録（ワザ 16・特殊エネルギー 5）だけを除いた登録表。"""
    attacks = {k: registry.attack_entry(k.card_id, k.attack_index) for k in registry.attack_keys() if k.card_id not in V0_78_CARDS}
    energies = {c: registry.energy_entry(c) for c in registry.energy_ids() if c not in V0_78_CARDS}
    return EffectRegistry(registry.id, attacks, registry._trainers, registry._powers, energies)


class RegistrationTest(unittest.TestCase):
    def test_registered_and_classified(self):
        """13 枚とも写しの組 pool_v0_78 にあり、ワザ 16 と特殊エネルギー 5 を登録した。処理に使う文面は kyuura の印刷の文面。"""
        extract = read_extract()
        self.assertEqual(tuple(extract["pool_v0_78"]), V0_78_CARDS)
        pool = load_card_pool()
        registry = E.DEFAULT_EFFECTS
        count = 0
        for card_id in V0_78_POKEMON:
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertIn(card_id, pool.playable_ids)
                self.assertEqual(definition.powers, ())
                self.assertEqual(tuple(type(registry.attack_entry(card_id, i).effect) for i in range(len(definition.attacks))), TYPES[card_id])
                for index, attack_def in enumerate(definition.attacks):
                    entry = registry.attack_entry(card_id, index)
                    self.assertEqual(entry.name_ja, attack_def.name_ja)
                    self.assertEqual(entry.effect.check(attack_def), [])
                    count += 1
                    if attack_def.text_ja is None:
                        self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (None, None, None))
                    else:
                        self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (attack_def.text_ja, attack_def.text_ja, "kyuura data/cards.json"))
        self.assertEqual(count, 16)
        for card_id in V0_78_ENERGIES:
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertIn(card_id, pool.playable_ids)
                self.assertTrue(definition.is_special_energy)
                self.assertFalse(definition.is_basic_energy)
                entry = registry.energy_entry(card_id)
                kind, value = ENERGY_TYPES[card_id]
                self.assertIs(type(entry.effect), kind)
                self.assertEqual(entry.effect.penalty if kind is E.DarknessEnergy else entry.effect.any_damage, value)
                self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (definition.energy_text_ja,) * 2 + ("kyuura data/cards.json",))
                self.assertEqual(registry.energy_problem(definition), None)
        # NIP2X-005 のデルビルは neo2-039 と同じ登録の値（id は消さない）
        for index in (0, 1):
            self.assertIs(registry.attack_entry(HOUNDOUR_NIP2X, index), registry.attack_entry(HOUNDOUR_NEO2, index))

    def test_records(self):
        """採用の記録（13 件。外部照合なし。kyuura の記録の id なし。ガイドブックの項目なし。照合の記録には加えない）と、研究の対応表（説明文のあるワザ 12・停止コード MT1・DE1）。"""
        import json

        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        verification = json.loads((ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8"))
        adopted = set(links["latest_descriptions"]["adopted_printed_text"])
        pool = load_card_pool()
        texts = 0
        for card in V0_78_CARDS:
            with self.subTest(card=card):
                record = sources[card]
                self.assertEqual((record["basis"], record["status"], record["external_checks"], record["kyuura_records"], record["kyuura_commit"]),
                                 ("kyuura_data", "adopted", [], [], "7d3f4ca76c084774efb4ac6a1d3a943387e183c3"))
                self.assertNotIn(card, json.dumps(verification))
                if card in V0_78_ENERGIES:
                    self.assertEqual(record["play_text"], {"energy": "kyuura_printed_text"})
                    continue
                for index, attack_def in enumerate(pool.get(card).attacks):
                    key = f"attack/{index}"
                    self.assertEqual(key in record["play_text"], attack_def.text_ja is not None)
                    self.assertEqual(f"{card}/{key}" in adopted, attack_def.text_ja is not None)
                    texts += attack_def.text_ja is not None
        self.assertEqual(texts, 12)
        for code, ruling in (("UNRESOLVED_METAL_ENERGY_POWER_ORDER", "MT1"), ("UNRESOLVED_DARKNESS_DAMAGE_RECEIVED_POWER", "DE1")):
            entry = links["stop_codes"][code]
            self.assertEqual((entry["kyuura_disposition"], entry["engine_rulings"][0]["ruling_id"]), ("not_in_kyuura", ruling))
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (166, 168))  # v0.79 で PK1 を加えた（v0.78 は 165・167）

    def test_counts(self):
        """写し・対応するカード 891、ポケモン 643・トレーナー 213・エネルギー 35、ワザ 1,088・特殊能力 74・特殊エネルギー 17。v0.79 でポケモン 52 枚（ワザ 94）を
        加えたので、今の数は 943（695・213・35）、ワザ 1,182。"""
        pool = load_card_pool()
        registry = E.DEFAULT_EFFECTS
        self.assertEqual(len(read_extract()["cards"]), 943)
        self.assertEqual(len(pool.playable_ids), 943)
        categories = Counter(pool.get(c).category for c in pool.playable_ids)
        self.assertEqual(dict(categories), {"pokemon": 695, "trainer": 213, "energy": 35})
        self.assertEqual((len(registry.attack_keys()), len(registry.power_keys()), len(registry.energy_ids())), (1182, 74, 17))

    def test_unsupported_counts(self):
        """kyuura data/engine_targets.json（7d3f4ca）の対象 1,377 件から登録を差し引く（engine_status は v0.68 の時点の索引なので使わない）。全対象の未対応 486・neo 263・
        拡張パック以外 223（v0.77 は 499・271・228）。v0.79 で 52 枚（neo 36・拡張パック以外 16）を加えたので、今の数は 434・227・207。"""
        import json
        import subprocess

        raw = subprocess.run(["git", "-C", str(ROOT.parent / "kyuura"), "show", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3:data/engine_targets.json"],
                             capture_output=True, text=True, check=False)
        if raw.returncode != 0:
            self.skipTest("../kyuura がない")
        data = json.loads(raw.stdout)
        targets = data["cards"] if isinstance(data, dict) else data
        pool = load_card_pool()
        ids = [x["id"] for x in targets]
        self.assertTrue(set(V0_78_CARDS) <= set(ids))
        self.assertEqual(sum(1 for c in ids if c not in pool.playable_ids), 434)  # v0.79 で 52 枚を加えた
        self.assertEqual(sum(1 for x in targets if x["id"].startswith("neo") and x["id"] not in pool.playable_ids), 227)  # v0.79 で neo 36 枚を加えた
        self.assertEqual(sum(1 for x in targets if x["product_group"] != "expansion_pack" and x["id"] not in pool.playable_ids), 207)  # v0.79 で拡張パック以外 16 枚を加えた

    def test_unregistered_without_the_v0_78_entries(self):
        """v0.78 の登録だけを除くと、13 枚とも未対応にもどり（v0.78 の時点では v0.77 の 878 枚。v0.79 の 52 枚を加えて 930 枚）、ほかのカードの対応は変わらない。"""
        reduced = without_v0_78(E.DEFAULT_EFFECTS)
        before = pool_from_extract(read_extract(), reduced)
        after = load_card_pool()
        self.assertFalse(before.playable_ids & set(V0_78_CARDS))
        self.assertEqual(after.playable_ids - before.playable_ids, frozenset(V0_78_CARDS))
        self.assertEqual(len(before.playable_ids), 930)  # v0.79 の 52 枚を含む（v0.78 では 878）
        self.assertFalse(set(E.EQUIVALENT_CARDS) & set(V0_78_CARDS))
        self.assertFalse(set(E.REPRINT_CARDS) & set(V0_78_CARDS))

    def test_texts_are_checked(self):
        """文面・値の確かめは一律に緩めていない: 版の違う文面・違う値は受け付けない（neo1-095 と NIP1X-010 は受けるダメージの範囲が違う）。"""
        pool = load_card_pool()
        self.assertNotEqual(E.MetalEnergy(any_damage=True).check(pool.get(MT)), [])
        self.assertNotEqual(E.MetalEnergy(any_damage=False).check(pool.get(MX)), [])
        self.assertNotEqual(E.DarknessEnergy(E.PENALTY_COUNTER).check(pool.get(DK)), [])
        self.assertNotEqual(E.DarknessEnergy(E.PENALTY_DAMAGE).check(pool.get(DC)), [])
        self.assertNotEqual(E.HalfRemainingHpDamage().check(pool.get(SCIZOR_NEO2).attacks[0]), [])  # 切り上げの型ではない
        self.assertNotEqual(E.DamageThenReduceDamageNextTurn(20).check(pool.get(SKARMORY_NEO1).attacks[1]), [])  # コインのない型ではない
        self.assertNotEqual(E.CoinsPerOwnPokemonDamage(10).check(pool.get(SNEASEL_NEO1).attacks[1]), [])
        self.assertNotEqual(E.DamageThenLockSelf().check(pool.get(SKARMORY_NIP1X).attacks[1]), [])  # 1 つのワザだけの型ではない
        with self.assertRaises(ValueError):
            E.DarknessEnergy("other")

    def test_same_name_limit_and_not_basic(self):
        """同じ名前（悪エネルギー・鋼エネルギー）は id をまたいで 4 枚まで（基本エネルギーではない）。"""
        pool = load_card_pool()
        deck = [DK] * 3 + [DP] * 2 + [WATER] * 15 + [RATTATA] * 4 + [HITMONCHAN] * 4 + [FIGHTING] * 32
        with self.assertRaises(DeckValidationError) as caught:
            validate_deck(deck, pool)
        self.assertIn("悪エネルギー", str(caught.exception))
        ok = [DK] * 2 + [DP] + [DC] + [MT] * 2 + [MX] * 2 + [WATER] * 12 + [RATTATA] * 4 + [HITMONCHAN] * 4 + [FIGHTING] * 32
        validate_deck(ok, pool)


class UnitsAndPaymentTest(unittest.TestCase):
    def test_units(self):
        """悪エネルギーは「悪」1 個、鋼エネルギーは「鋼」1 個。どちらも「無色」の記号を払える。レインボーエネルギーは鋼・悪にならない（8 色に広げていない）。"""
        state = board(active=mon(SNEASEL_NEO1, (DK, DC)), opponent_active=mon(SKARMORY_NEO1, (MT, MX)))
        me, them = state.players[0].active, state.players[1].active
        self.assertEqual(E.attached_units(state, me), [frozenset({EnergyType.DARKNESS})] * 2)
        self.assertEqual(E.attached_units(state, them), [frozenset({EnergyType.METAL})] * 2)
        self.assertTrue(can_pay_with_units([EnergyType.COLORLESS, EnergyType.COLORLESS], E.attached_units(state, me)))
        self.assertTrue(E.attack_cost_payable(state, me, state.card_def(me.card).attacks[1]))  # ふくろだたき（悪悪）
        self.assertNotIn(EnergyType.METAL, E.BASIC_ENERGY_COLORS)
        self.assertNotIn(EnergyType.DARKNESS, E.BASIC_ENERGY_COLORS)
        rainbow = board(active=mon(SKARMORY_PF3, (RAINBOW_ENERGY, WATER, WATER)), opponent_active=mon(HITMONCHAN))
        self.assertFalse(E.attack_cost_payable(rainbow, rainbow.players[0].active, rainbow.card_def(rainbow.players[0].active.card).attacks[1]))

    def test_pf3_skarmory_can_now_pay_metal(self):
        """v0.72 で登録した PF3-009 のエアームドの「こうそくいどう」（鋼無無）は、鋼エネルギーで払える（ワザを使える）。"""
        state = board(active=mon(SKARMORY_PF3, (MT, WATER, WATER)), opponent_active=mon(HITMONCHAN))
        after = attack(state, 1, T)
        self.assertEqual(damages(state, after), [("opponent_active", 20, ("1 基本となる計算",))])
        audited(self, after)

    def test_special_energy_is_not_basic_for_search(self):
        """場の外の悪・鋼エネルギーは「基本エネルギーカード」ではない（基本エネルギーを選ぶ効果に入らない）。"""
        state = board(active=mon(SNEASEL_NEO1, (DK, WATER)), opponent_active=mon(HITMONCHAN))
        self.assertEqual(E.attached_basic_energy(state, state.players[0].active, EnergyType.WATER), [state.players[0].active.energy[1]])
        for card_id in V0_78_ENERGIES:
            self.assertFalse(load_card_pool().get(card_id).is_basic_energy)


class AttackDamageTest(unittest.TestCase):
    """ワザのダメージ: 悪エネルギーは 5 段階 +10（対戦ポケモンにだけ）、鋼エネルギーは 7 段階 -10（受けるポケモンについているカードごと）と、「鋼」でないポケモンの与える
    ダメージの 5 段階 -10。"""

    def test_darkness_bonus_only_to_the_defending_pokemon(self):
        state = board(active=mon(HOUNDOUR_NEO2, (DK,)), opponent_active=mon(HITMONCHAN))
        after = attack(state, 0)
        self.assertEqual(damages(state, after), [("opponent_active", 20, ("1 基本となる計算", "5 悪エネルギー"))])
        # 2 枚なら +20（カードごと）
        two = board(active=mon(HOUNDOUR_NEO2, (DK, DP)), opponent_active=mon(HITMONCHAN))
        self.assertEqual(damages(two, attack(two, 0))[0][1], 30)

    def test_darkness_not_applied_to_bench_or_self(self):
        """ヌオーの「じしん」（自分の控えにも 10）・ニョロボンの「じごくぐるま」（自分にも 20）: 悪エネルギーは控え・自分へのダメージに当てはめない。"""
        state = board(active=mon(QUAGSIRE_NEO1, (DK, FIGHTING, FIGHTING, FIGHTING), evolved_from=WOOPER_NEO1, evolved_turn=TURN - 2, played_turn=TURN - 4),
                      opponent_active=mon(HITMONCHAN))
        after = attack(state, 1)
        result = damages(state, after)
        self.assertEqual(result[0], ("opponent_active", 70, ("1 基本となる計算", "5 悪エネルギー")))
        self.assertEqual([r[1] for r in result[1:]], [10])
        wrath = board(active=mon(POLIWRATH_NEO2, (DK, FIGHTING, FIGHTING, FIGHTING), evolved_from=[POLIWAG, POLIWHIRL], evolved_turn=TURN - 2, played_turn=TURN - 6),
                      opponent_active=mon(HITMONCHAN))
        after = attack(wrath, 1)
        result = damages(wrath, after)
        self.assertEqual(result[-1], ("self", 20, ("1 基本となる計算",)))

    def test_metal_reduces_received_attack_damage_per_card(self):
        state = board(active=mon(HITMONCHAN, (FIGHTING,)), opponent_active=mon(SKARMORY_NEO1, (MT,)))
        after = attack(state, 0)
        self.assertEqual(damages(state, after), [("opponent_active", 10, ("1 基本となる計算", "7 鋼エネルギー"))])
        two = board(active=mon(HITMONCHAN, (FIGHTING,)), opponent_active=mon(SKARMORY_NEO1, (MT, MX)))
        self.assertEqual(damages(two, attack(two, 0))[0][1], 0)

    def test_non_metal_attacker_with_metal_deals_less(self):
        """「鋼」でないポケモンに鋼エネルギーがついていると、与えるワザのダメージも 5 段階で -10。「鋼」ポケモン（ハッサム）なら変えない。"""
        state = board(active=mon(HITMONCHAN, (FIGHTING, MT)), opponent_active=mon(HITMONCHAN))
        self.assertEqual(damages(state, attack(state, 0)), [("opponent_active", 10, ("1 基本となる計算", "5 鋼エネルギー"))])
        scizor = board(active=mon(SCIZOR_NEO2, (MT, WATER, WATER), evolved_from=SCYTHER, evolved_turn=TURN - 2, played_turn=TURN - 4),
                       opponent_active=mon(HITMONCHAN))
        self.assertEqual(damages(scizor, attack(scizor, 1, T, T)), [("opponent_active", 20, ("1 基本となる計算",))])

    def test_darkness_and_metal_together(self):
        """悪エネルギー +10 と鋼エネルギー -10（「鋼」でないワザを使うポケモン）は同じ 5 段階で、受ける側の鋼エネルギーは 7 段階。"""
        state = board(active=mon(HOUNDOUR_NEO2, (DK, MT)), opponent_active=mon(SKARMORY_NEO1, (MX,)))
        self.assertEqual(damages(state, attack(state, 0)), [("opponent_active", 0, ("1 基本となる計算", "5 悪エネルギー", "5 鋼エネルギー", "7 鋼エネルギー"))])

    def test_self_damage_applies_each_metal_clause_once(self):
        """自分へのダメージ（じごくぐるまの自分にも 20）: 「鋼」でないポケモンの鋼エネルギーは、与えるダメージの -10（5 段階）と受けるダメージの -10（7 段階）を 1 回ずつ。"""
        state = board(active=mon(POLIWRATH_NEO2, (MT, FIGHTING, FIGHTING, FIGHTING), evolved_from=[POLIWAG, POLIWHIRL], evolved_turn=TURN - 2, played_turn=TURN - 6),
                      opponent_active=mon(HITMONCHAN))
        result = damages(state, attack(state, 1))
        self.assertEqual(result[0][1:], (60, ("1 基本となる計算", "5 鋼エネルギー")))
        self.assertEqual(result[-1], ("self", 0, ("1 基本となる計算", "5 鋼エネルギー", "7 鋼エネルギー")))

    def test_bench_damage_metal_on_the_bench(self):
        """控えへのダメージでも、受けるポケモンについている鋼エネルギーは 7 段階（受けるポケモンごと）。"""
        state = board(active=mon(QUAGSIRE_NEO1, (FIGHTING, FIGHTING, FIGHTING, FIGHTING), evolved_from=WOOPER_NEO1, evolved_turn=TURN - 2, played_turn=TURN - 4),
                      bench=(mon(RATTATA, (MT,)),), opponent_active=mon(HITMONCHAN))
        result = damages(state, attack(state, 1))
        self.assertEqual(result[1][1:], (0, ("1 基本となる計算", "7 鋼エネルギー")))

    def test_speed_star_ignores_the_defenders_metal_but_keeps_the_attackers_darkness(self):
        """エレブーの「スピードスター」: 受けるポケモン自身の効果（鋼エネルギー）は計算しない。ワザを使うポケモンの悪エネルギーは計算する。"""
        state = board(active=mon(ELECTABUZZ_NEO1, (DK, LIGHTNING, LIGHTNING, LIGHTNING)), opponent_active=mon(SKARMORY_NEO1, (MT,)))
        self.assertEqual(damages(state, attack(state, 1)), [("opponent_active", 40, ("1 基本となる計算", "5 悪エネルギー"))])

    def test_zero_at_step_2_ends_the_calculation(self):
        """ふくろだたきで「おもて」が 0（2 段階で 0）なら、悪エネルギーの 5 段階は計算しない（ダメージを与えない）。"""
        state = board(active=mon(SNEASEL_NEO1, (DK, DP)), bench=(), opponent_active=mon(HITMONCHAN))
        result = damages(state, attack(state, 1, T))
        self.assertEqual(result, [("opponent_active", 0, ("1 基本となる計算",))])

    def test_plunder_discards_trainers_before_damage(self):
        """ごうだつ: 相手についているトレーナー（ディフェンダー・プラスパワー）をトラッシュしてからダメージ（ディフェンダーの 7 段階は計算しない）。"""
        state = board(active=mon(HOUNDOUR_NEO2, (DK, WATER)), opponent_active=mon(HITMONCHAN, trainers=[(DEFENDER, TURN), (PLUSPOWER, TURN - 1)]))
        after = attack(state, 1)
        self.assertEqual(damages(state, after), [("opponent_active", 30, ("1 基本となる計算", "5 悪エネルギー"))])
        discarded = new_events(state, after, "discard_attached_trainer")
        self.assertEqual([(e["reason"], e["effect"]) for e in discarded], [("attack", f"{HOUNDOUR_NEO2}#1")] * 2)
        self.assertEqual(after.players[1].active.trainers, [])
        self.assertEqual(sorted(after.cards[u].card_id for u in after.players[1].discard), sorted([DEFENDER, PLUSPOWER]))
        audited(self, after)

    def test_preflight_modes_agree(self):
        for mode in PREFLIGHT_MODES:
            with self.subTest(mode=mode):
                state = board(active=mon(HOUNDOUR_NEO2, (DK, MT)), opponent_active=mon(SKARMORY_NEO1, (MX,)))
                after = attack(state, 1, preflight=mode)
                self.assertEqual(damages(state, after)[0][1], 10)

    def test_confused_attacker_with_metal_stops_before_the_coin(self):
        """こんらん状態のポケモンに鋼エネルギーがつくと、こんらんの 20 にその効果を計算するかは決まらないので、コインの前に止める（既存の問い）。悪エネルギーだけなら止めない。"""
        state = board(active=mon(HITMONCHAN, (FIGHTING, MT), confusion=True), opponent_active=mon(RATTATA))
        with self.assertRaises(UnsupportedError) as caught:
            attack(state, 0)
        self.assertEqual(caught.exception.code, "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS")
        dark = board(active=mon(HITMONCHAN, (FIGHTING, DK), confusion=True), opponent_active=mon(RATTATA))
        attack(dark, 0, T)


class NonAttackDamageTest(unittest.TestCase):
    """ワザでないダメージ: NIP1X-010 の鋼エネルギーは -10（ダメージカウンターは変えない）。neo1-095 はワザによるダメージだけ。"""

    def test_counterattack_power_damage(self):
        machamp = mon(MACHAMP, (FIGHTING,), evolved_from=[MACHOP, MACHOKE], evolved_turn=TURN - 1, played_turn=TURN - 5)
        for energy, expected in ((MX, 0), (MT, 10)):
            with self.subTest(energy=energy):
                state = board(active=mon(HITMONCHAN, (FIGHTING, energy)), opponent_active=machamp)
                after = attack(state, 0)
                event = new_events(state, after, "counterattack")[0]
                self.assertEqual(event["amount"], expected)
                audited(self, after)

    def test_metal_and_received_power_order_is_unresolved(self):
        """MT1: ワザでないダメージに、受けるダメージを変える特殊能力と NIP1X-010 の両方が当てはまり、順番で量が変わるなら止める（直接呼ぶ。今の写しで 30 の特殊能力の
        ダメージはない）。"""
        state = board(active=mon(HITMONCHAN), opponent_active=mon(MR_MIME, (MX,)))
        receiver = state.players[1].active
        with self.assertRaises(UnsupportedError) as caught:
            E.received_power_damage(state, 1, receiver, state.players[0].active, 30)
        self.assertEqual(caught.exception.code, "UNRESOLVED_METAL_ENERGY_POWER_ORDER")
        self.assertEqual(E.received_power_damage(state, 1, receiver, state.players[0].active, 20)[0], 10)

    def test_trainer_damage(self):
        for energy, expected in ((MX, 0), (MT, 10)):
            with self.subTest(energy=energy):
                state = board(active=mon(HITMONCHAN, (energy,)), opponent_active=mon(HITMONCHAN, (energy,)), hand=(DIGGER,))
                after = apply_kernel(with_coin_results(state, T), PlayTrainer(0, state.players[0].hand[0]))
                event = new_events(state, after, "trainer_damage")[0]
                self.assertEqual(event["amount"], expected)

    def test_rainbow_energy_damage(self):
        state = board(active=mon(HITMONCHAN, (MX,)), opponent_active=mon(RATTATA), hand=(RAINBOW_ENERGY,))
        after = apply_kernel(state, AttachEnergy(0, state.players[0].hand[0], state.players[0].active.card))
        event = new_events(state, after, "energy_damage")[0]
        self.assertEqual((event["amount"], event["amount_before"]), (0, 10))
        audited(self, after)


class PokemonCheckTest(unittest.TestCase):
    """ポケモンチェック（指示されたこと → どく → ねむり → マヒ）の悪エネルギー。両方のプレイヤーの場のすべてのポケモン・特殊状態に関係なく。"""

    def end(self, state):
        return apply_kernel(state, EndTurn(state.current_player))

    def test_damage_and_counters(self):
        state = board(active=mon(HITMONCHAN, (DK, DC, FIGHTING)), bench=(mon(RATTATA, (DP,)),),
                      opponent_active=mon(HITMONCHAN, (FIGHTING, MX, DK), poison=10, sleep=True), opponent_bench=(mon(SNEASEL_NEO1, (DK,)),))
        after = self.end(state)
        events = [(e["kind"], e["pokemon_id"], e.get("amount", e.get("counters")), e.get("energy_reduction")) for e in
                  new_events(state, after, "darkness_energy_damage", "darkness_energy_counters", "poison_damage")]
        me, bench, them = state.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id, state.players[1].active.pokemon_id
        mx = state.players[1].active.energy[1]
        self.assertEqual(events, [("darkness_energy_damage", me, 10, None), ("darkness_energy_counters", me, 1, None), ("darkness_energy_damage", bench, 10, None),
                                  ("darkness_energy_damage", them, 0, (mx,)), ("poison_damage", them, 0, (mx,))])
        kinds = [e["kind"] for e in after.log[len(state.log):]]
        self.assertLess(kinds.index("darkness_energy_damage"), kinds.index("poison_damage"))
        self.assertLess(kinds.index("poison_damage"), kinds.index("sleep_check"))
        self.assertEqual(after.players[0].active.damage, 20)
        audited(self, after)

    def test_darkness_and_dark_pokemon_are_exempt(self):
        """「悪」タイプ（ニューラ）・「わるい」ポケモン（わるいラッタ。名前が「わるい」ではじまる）は受けない。"""
        state = board(active=mon(SNEASEL_NEO1, (DK,)), bench=(mon(DARK_RATICATE, (DC,), evolved_from=RATTATA, evolved_turn=TURN - 2, played_turn=TURN - 4),),
                      opponent_active=mon(HITMONCHAN))
        after = self.end(state)
        self.assertEqual(new_events(state, after, "darkness_energy_damage", "darkness_energy_counters"), [])

    def test_chemical_gas_does_not_stop_energy(self):
        state = board(active=mon(HITMONCHAN, (DK,)), opponent_active=mon(MUK, evolved_from=GRIMER, evolved_turn=TURN - 1, played_turn=TURN - 3))
        after = self.end(state)
        self.assertEqual(len(new_events(state, after, "darkness_energy_damage")), 1)

    def test_knock_out_by_darkness(self):
        state = board(active=mon(HITMONCHAN, (DK,), damage=60), bench=(RATTATA,), opponent_active=mon(HITMONCHAN))
        after = self.end(state)
        knocked = new_events(state, after, "knock_out")
        self.assertEqual([e["pokemon"] for e in knocked], [state.players[0].active.card])
        audited(self, after)

    def test_double_knock_out_halts(self):
        state = board(active=mon(HITMONCHAN, (DK,), damage=60), opponent_active=mon(HITMONCHAN, (DC,), damage=60))
        after = self.end(state)
        self.assertIs(after.phase, Phase.HALTED)
        self.assertEqual(after.halt.code, "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT")

    def test_kabuto_armor_is_unresolved(self):
        """DE1: カブトアーマー（受けるダメージは半分）を悪エネルギーの 10 ダメージに当てはめるかは決まらない。ダメージカウンター（NIP2X-010）は止めない。"""
        kabuto = {"card": KABUTO, "evolved_from": MYSTERIOUS_FOSSIL, "evolved_turn": TURN - 1, "played_turn": TURN - 3}
        state = board(active=mon(HITMONCHAN), opponent_active={**kabuto, "energy": [DK]})
        after = self.end(state)
        self.assertIs(after.phase, Phase.HALTED)
        self.assertEqual(after.halt.code, "UNRESOLVED_DARKNESS_DAMAGE_RECEIVED_POWER")
        counter = board(active=mon(HITMONCHAN), opponent_active={**kabuto, "energy": [DC]})
        after = self.end(counter)
        self.assertNotEqual(after.phase, Phase.HALTED)
        self.assertEqual(len(new_events(counter, after, "darkness_energy_counters")), 1)

    def test_bench_guard_is_unsupported(self):
        rhydon = mon(BROCKS_RHYDON, evolved_from=BROCKS_RHYHORN, evolved_turn=TURN - 2, played_turn=TURN - 4)
        state = board(active=mon(HITMONCHAN), bench=(rhydon, mon(RATTATA, (DK,))), opponent_active=mon(HITMONCHAN))
        after = self.end(state)
        self.assertIs(after.phase, Phase.HALTED)
        self.assertEqual(after.halt.code, "UNSUPPORTED_BENCH_GUARD_OUTSIDE_ATTACK")

    def test_scram(self):
        """タケシのオコリザルの［ずらかる］: 悪エネルギーで残りHPがちょうど 10 になれば山札にもどる。2 枚で「10」を通ったら（そのあときぜつする）SC1。"""
        primeape = {"card": BROCKS_PRIMEAPE, "evolved_from": BROCKS_MANKEY, "evolved_turn": TURN - 1, "played_turn": TURN - 3}
        one = board(active=mon(HITMONCHAN), opponent_active=mon(HITMONCHAN), opponent_bench=({**primeape, "energy": [DK], "damage": 50},))
        after = self.end(one)
        self.assertEqual(len(new_events(one, after, "scram")), 1)
        two = board(active=mon(HITMONCHAN), opponent_active=mon(HITMONCHAN), opponent_bench=({**primeape, "energy": [DK, DC], "damage": 50},))
        after = self.end(two)
        self.assertIs(after.phase, Phase.HALTED)
        self.assertEqual(after.halt.code, "UNRESOLVED_SCRAM_TIMING")


class AttackEffectTest(unittest.TestCase):
    def test_beat_up_coins_per_pokemon(self):
        """ふくろだたき: 自分の場のポケモンの数（バトル場とベンチ）だけコインを投げる。"""
        state = board(active=mon(SNEASEL_NEO1, (DK, DP)), bench=(RATTATA, HITMONCHAN), opponent_active=mon(HITMONCHAN))
        after = attack(state, 1, H, T, H)
        coins = new_events(state, after, "coin_flip")
        self.assertEqual(len(coins), 3)
        self.assertEqual(damages(state, after)[0][1], 60)  # 2 × 20 + 悪エネルギー 2 枚

    def test_false_swipe_rounds_down(self):
        """みねうち: 相手の残りHPの半分（切りすて）。70 → 30、50 → 20、30 → 10、10 → 0。"""
        for damage, expected in ((0, 30), (20, 20), (40, 10), (60, 0)):
            with self.subTest(remaining=70 - damage):
                state = board(active=mon(SCIZOR_NEO2, (MT,), evolved_from=SCYTHER, evolved_turn=TURN - 2, played_turn=TURN - 4),
                              opponent_active=mon(HITMONCHAN, damage=damage))
                self.assertEqual(damages(state, attack(state, 0))[0][1], expected)
        self.assertEqual(E.half_remaining_hp(state, state.players[1].active), 10)  # 既定は切り上げ（いかりのまえば）

    def test_steel_wing(self):
        state = board(active=mon(SKARMORY_NEO1, (MT, WATER, WATER)), opponent_active=mon(HITMONCHAN, (FIGHTING,)))
        heads = attack(state, 1, H)
        effects = [e for e in heads.players[0].active.persistent_effects if isinstance(e, DamageReduction)]
        self.assertEqual([(e.amount, e.active_turn) for e in effects], [(20, TURN + 1)])
        tails = attack(state, 1, T)
        self.assertEqual(tails.players[0].active.persistent_effects, ())
        # 次の相手の番のワザのダメージは 8 段階で -20（受けるワザのダメージ。鋼エネルギーの 7 段階のあと）
        self.assertEqual(heads.current_player, 1)
        hit = apply_kernel(heads, UseAttack(1, 0))
        self.assertEqual(damages(heads, hit), [("opponent_active", 0, ("1 基本となる計算", "7 鋼エネルギー", "8 エアームド（damage_reduction）"))])
        audited(self, heads)

    def test_corner_prevents_retreat(self):
        state = board(active=mon(HOUNDOUR_NEO4, (DK,)), opponent_active=mon(HITMONCHAN, (FIGHTING,)))
        after = attack(state, 0)
        self.assertEqual(damages(state, after), [])
        self.assertTrue(any(isinstance(e, CannotRetreat) for e in after.players[1].active.persistent_effects))
        self.assertEqual(after.current_player, 1)
        with self.assertRaises(IllegalActionError) as caught:
            apply_kernel(after, Retreat(1, (after.players[1].active.energy[0],), after.players[1].bench[0].card))
        self.assertEqual(caught.exception.code, "RETREAT_PREVENTED")

    def test_metal_slash_locks_every_attack_next_own_turn(self):
        state = board(active=mon(SKARMORY_NIP1X, (MT, WATER)), opponent_active=mon(HITMONCHAN))
        after = attack(state, 1)
        effects = [e for e in after.players[0].active.persistent_effects if isinstance(e, CannotAttackNextOwnTurn)]
        self.assertEqual([(e.created_turn, e.active_turn) for e in effects], [(TURN, TURN + 2)])
        opp = apply_kernel(after, EndTurn(1))
        self.assertEqual(opp.current_player, 0)
        for index in (0, 1):
            with self.assertRaises(IllegalActionError) as caught:
                apply_kernel(opp, UseAttack(0, index))
            self.assertEqual(caught.exception.code, "ATTACK_PREVENTED")
        later = apply_kernel(apply_kernel(opp, EndTurn(0)), EndTurn(1))
        apply_kernel(later, UseAttack(0, 0))
        dumped = state_to_dict(after, format_version=max(FORMAT_VERSIONS))
        self.assertIn("cannot_attack_next_own_turn", repr(dumped))
        audited(self, after)

    def test_evolution_lines(self):
        pool = load_card_pool()
        self.assertEqual(pool.get(STEELIX_NEO1).evolves_from, pool.get(ONIX).name_ja)
        self.assertEqual(pool.get(SCIZOR_NEO2).evolves_from, pool.get(SCYTHER).name_ja)


class SecretPlanAndQuizTest(unittest.TestCase):
    def test_secret_plan_candidates(self):
        pool = load_card_pool()
        candidates = engine_module._identity_candidates(pool)
        basics = [c for c in candidates if pool.get(c).is_basic_pokemon]
        self.assertEqual(engine_module._IDENTITY_TRIAL_LIMIT, 512)
        self.assertLessEqual(1 + len(basics) + 1, engine_module._IDENTITY_TRIAL_LIMIT)
        self.assertEqual(len({HOUNDOUR_NIP2X, HOUNDOUR_NEO2} & set(candidates)), 1)  # 同じデータの 2 枚は 1 枚で代表する

    def test_quiz_names(self):
        extract = read_extract()
        cards = {c["id"]: c for c in extract["cards"]}
        earlier = {cards[c]["name"]["ja"] for c in cards if c not in V0_78_CARDS and c not in extract["pool_v0_79"] and cards[c]["category"] == "pokemon"}  # v0.79 で同じ名前のカードを加えた
        new = sorted({cards[c]["name"]["ja"] for c in V0_78_POKEMON} - earlier)
        self.assertEqual(new, sorted(["ニューラ", "ハガネール", "デルビル", "ハッサム"]))
        state = build_test_state([{"active": "PMCG1-018"}, {"active": "PMCG1-018"}])
        names = E.quiz_answer_names(state)
        for name in new:
            self.assertIn(name, names)


class DocumentTest(unittest.TestCase):
    def test_document_exists_and_names_the_cards(self):
        text = DOC.read_text(encoding="utf-8")
        for card in V0_78_CARDS:
            self.assertIn(card, text)
        for word in ("891", "486", "263", "223", "UNRESOLVED_METAL_ENERGY_POWER_ORDER", "UNRESOLVED_DARKNESS_DAMAGE_RECEIVED_POWER", "書き出しの形式は 22",
                     "GR-2000-P321-DAMAGE-ORDER", "GR-2000-P323-POKEMON-CHECK"):
            self.assertIn(word, text)


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.78 の組の手順）。"""

    def test_batch_seed_zero_runs_without_audit_failures(self):
        """v0.78 の 3 組を seed 0 で（席を入れかえて 6 局）。どれも監査の失敗（やり直し・不変条件・ログ・書き出し）・想定外の拒否・内部エラーがない。
        メタルスラッシュの効果（次の自分の番。与えた番 + 2）のログを監査が確かめる局を含む（v0.78 の確かめで、監査がこの効果の番を知らなかった）。"""
        from tools import existing_effect_games as games

        results = games.run(range(1), pairings=games.PAIRINGS_V0_78)
        metal_slash = 0
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, (game["decks"], game["seed"]))
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"))
                metal_slash += game.get("card_uses", {}).get(SKARMORY_NIP1X, {}).get("attack#1", 0)
        self.assertGreater(metal_slash, 0)


if __name__ == "__main__":
    unittest.main()
