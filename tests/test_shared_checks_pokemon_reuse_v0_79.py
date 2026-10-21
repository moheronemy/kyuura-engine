"""v0.79: v0.78 の共通処理の修正（ポケモンチェックの途中のきぜつ・ワザでないダメージの止める確かめ）と、ポケモン 52 枚・ワザ 94（docs/shared-checks-pokemon-reuse-v0.79.md）。

A（PK1）: ポケモンチェックの 1（悪エネルギー）でポケモンが HP 以上になり、1 と 2 のあいだにきぜつの判定をするかで 2 の「どく」・きぜつの判定の問い合わせが変わるなら止める
（GR-2000-P323-POKEMON-CHECK の順番だけでは決まらない）。変わらないなら v0.78 と同じに処理する。
B: DE1・KA1・RB4・TD1・EX1 は、鋼エネルギー（NIP1X-010）の「-10」を含めた最終の量で比べる（どの読み方でも同じ量なら止めない）。
カードはどれも kyuura データの採用（採用したデータのコミット 7d3f4ca。処理に使う文面は kyuura の印刷の文面）。ガイドブックは読んでいない。
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy,
    EndTurn,
    IllegalActionError,
    Phase,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    DISCARD_ENERGY,
    SEARCH_DECK,
    SELECT_ATTACK,
    SELECT_POKEMON,
)
from kyuura_engine.effects import EffectRegistry
from kyuura_engine.observation import HIDDEN_COUNT_KINDS, observe
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import (
    CannotAttackNextOwnTurn,
    PreventAttackDamage,
    PreventDamage,
)
from tests import helpers as H_
from tests.helpers import (
    CLEFAIRY,
    DEFENDER,
    DIGGER,
    DITTO,
    FIGHTING,
    FIRE,
    GRIMER,
    HITMONCHAN,
    KABUTO,
    LIGHTNING,
    MAREEP_NEO2,
    MUK,
    MYSTERIOUS_FOSSIL,
    ONIX,
    PLUSPOWER,
    PSYCHIC,
    RAINBOW_ENERGY,
    RATTATA,
    SABRINAS_GASTLY,
    SLOWPOKE,
    V0_79_CARDS,
    V0_79_POKEMON,
    WATER,
    apply_kernel,
    with_coin_results,
)
from tests.test_darkness_metal_energy_v0_78 import (
    DC,
    DK,
    MT,
    MX,
    TURN,
    audited,
    board,
    mon,
    new_events,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "shared-checks-pokemon-reuse-v0.79.md"

H, T = CoinSide.HEADS, CoinSide.TAILS
MID = "UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT"


def kabuto(**extra):
    return {"card": KABUTO, "evolved_from": MYSTERIOUS_FOSSIL, "evolved_turn": TURN - 1, "played_turn": TURN - 3, **extra}


def gas_muk(**extra):
    return {"card": MUK, "evolved_from": GRIMER, "evolved_turn": TURN - 2, "played_turn": TURN - 4, **extra}


def end(state):
    return apply_kernel(state, EndTurn(state.current_player))


class MidCheckKnockoutTest(unittest.TestCase):
    """A（PK1）: 1 と 2 のあいだのきぜつの判定の時点で、2 の問い合わせが変わるか。"""

    def test_gas_source_knocked_out_by_darkness_changes_kabuto_poison(self):
        """v0.78 は TAKE_PRIZE に進んでいた盤面（ベトベトンが悪エネルギーで HP 以上 → 場をはなれるとかがくへんかガスが消え、カブトのどくに KA1 が当てはまる）。"""
        state = board(active=gas_muk(energy=[DK], damage=60), opponent_active=kabuto(poison=10))
        after = end(state)
        self.assertIs(after.phase, Phase.HALTED)
        self.assertEqual(after.halt.code, MID)
        self.assertEqual(new_events(state, after, "darkness_energy_damage", "poison_damage", "knock_out"), [])
        self.assertEqual(after.players[0].active.damage, 60)
        audited(self, after)

    def test_controls_where_nothing_changes(self):
        """同じベトベトンのきぜつでも、カブトがどく状態でなければ 2 で何も変わらないので、v0.78 と同じに進む。どく状態のポケモンが受ける量の変わらない場合も同じ。"""
        cases = {
            "no_poison": board(active=gas_muk(energy=[DK], damage=60), opponent_active=kabuto()),
            "plain_poison": board(active=gas_muk(energy=[DK], damage=60), opponent_active=mon(HITMONCHAN, poison=10)),
            "no_gas": board(active=mon(HITMONCHAN, (DK,), damage=60), opponent_active=mon(HITMONCHAN, poison=10)),
        }
        for name, state in cases.items():
            with self.subTest(name):
                after = end(state)
                self.assertIs(after.phase, Phase.TAKE_PRIZE)
                self.assertEqual([e["pokemon"] for e in new_events(state, after, "knock_out")], [state.players[0].active.card])
                audited(self, after)

    def test_special_condition_and_metal_versions(self):
        """ベトベトンがこんらん状態（かがくへんかガスは 1 の前から消えている）なら、どちらの読み方でもカブトアーマーがはたらくので PK1 ではなく KA1。カブトに
        鋼エネルギー（NIP1X-010）がついていれば、どちらの読み方でもどくの最終の量が 0 なので止めずに進む。"""
        confused = board(active=gas_muk(energy=[DK], damage=60, confusion=True), opponent_active=kabuto(poison=10))
        after = end(confused)
        self.assertEqual((after.phase, after.halt.code), (Phase.HALTED, "UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER"))
        metal = board(active=gas_muk(energy=[DK], damage=60), opponent_active=kabuto(poison=10, energy=[MX]))
        after = end(metal)
        self.assertIs(after.phase, Phase.TAKE_PRIZE)
        self.assertEqual(new_events(metal, after, "poison_damage")[0]["amount"], 0)

    def test_transform_changes_knock_out(self):
        """［へんしん］のメタモン: 写しているバトル場のポケモンが 1 で HP 以上になり場をはなれると、メタモンの最大HPが変わって 2 のあとにきぜつするかが変わる。"""
        changes = board(active=mon(HITMONCHAN, (DK,), damage=60), opponent_active=mon(DITTO, damage=50, poison=10))
        after = end(changes)
        self.assertEqual((after.phase, after.halt.code), (Phase.HALTED, MID))
        same = board(active=mon(HITMONCHAN, (DK,), damage=60), opponent_active=mon(DITTO))
        after = end(same)
        self.assertIs(after.phase, Phase.TAKE_PRIZE)

    def test_without_darkness_unchanged(self):
        state = board(active=mon(HITMONCHAN, damage=60), opponent_active=mon(HITMONCHAN, poison=10, damage=60))
        after = end(state)
        self.assertIs(after.phase, Phase.TAKE_PRIZE)
        self.assertEqual(len(new_events(state, after, "poison_damage")), 1)


class FinalAmountTest(unittest.TestCase):
    """B: 鋼エネルギー（NIP1X-010）を含めた最終の量で比べる。"""

    def test_darkness_with_metal_reaches_zero_either_way(self):
        state = board(active=mon(HITMONCHAN), opponent_active=kabuto(energy=[DK, MX]))
        after = end(state)
        self.assertIs(after.phase, Phase.MAIN)
        event = new_events(state, after, "darkness_energy_damage")[0]
        self.assertEqual((event["amount"], event["amount_before"]), (0, 10))
        audited(self, after)

    def test_poison_with_metal_reaches_zero_either_way(self):
        state = board(active=mon(HITMONCHAN), opponent_active=kabuto(energy=[MX], poison=10))
        after = end(state)
        self.assertIs(after.phase, Phase.MAIN)
        self.assertEqual(new_events(state, after, "poison_damage")[0]["amount"], 0)

    def test_adjacent_cases_still_stop(self):
        cases = {
            "attack_only_metal": (kabuto(energy=[DK, MT]), "UNRESOLVED_DARKNESS_DAMAGE_RECEIVED_POWER"),
            "no_metal": (kabuto(energy=[DK]), "UNRESOLVED_DARKNESS_DAMAGE_RECEIVED_POWER"),
            "special_poison": (kabuto(energy=[MX], poison=20), "UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER"),
            "plain_poison_no_metal": (kabuto(poison=10), "UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER"),
        }
        for name, (defender, code) in cases.items():
            with self.subTest(name):
                after = end(board(active=mon(HITMONCHAN), opponent_active=defender))
                self.assertEqual((after.phase, after.halt.code), (Phase.HALTED, code))

    def test_counters_are_not_damage(self):
        state = board(active=mon(HITMONCHAN), opponent_active=kabuto(energy=[DC, MX]))
        after = end(state)
        self.assertEqual(new_events(state, after, "darkness_energy_counters")[0]["counters"], 1)
        self.assertEqual(after.players[1].active.damage, 10)

    def test_gas_and_special_conditions_turn_the_power_off(self):
        gas = board(active=gas_muk(), opponent_active=kabuto(energy=[DK], poison=10))
        after = end(gas)
        self.assertIs(after.phase, Phase.MAIN)
        self.assertEqual([e["amount"] for e in new_events(gas, after, "darkness_energy_damage", "poison_damage")], [10, 10])
        confused = board(active=mon(HITMONCHAN), opponent_active=kabuto(energy=[DK], confusion=True))
        after = end(confused)
        self.assertNotEqual(after.phase, Phase.HALTED)

    def test_rainbow_energy_rb4(self):
        zero = board(active=kabuto(energy=[MX], evolved_turn=TURN - 2, played_turn=TURN - 4), opponent_active=mon(RATTATA), hand=(RAINBOW_ENERGY,))
        after = apply_kernel(zero, AttachEnergy(0, zero.players[0].hand[0], zero.players[0].active.card))
        self.assertEqual(new_events(zero, after, "energy_damage")[0]["amount"], 0)
        stop = board(active=kabuto(energy=[MT], evolved_turn=TURN - 2, played_turn=TURN - 4), opponent_active=mon(RATTATA), hand=(RAINBOW_ENERGY,))
        with self.assertRaises(Exception) as caught:
            apply_kernel(stop, AttachEnergy(0, stop.players[0].hand[0], stop.players[0].active.card))
        self.assertEqual(caught.exception.code, "UNRESOLVED_RAINBOW_DAMAGE_RECEIVED_POWER")

    def test_trainer_damage_td1(self):
        zero = board(active=mon(HITMONCHAN, (FIGHTING,)), opponent_active=kabuto(energy=[MX]), hand=(DIGGER,))
        after = apply_kernel(with_coin_results(zero, H, T), PlayTrainer(0, zero.players[0].hand[0]))
        self.assertEqual(new_events(zero, after, "trainer_damage")[0]["amount"], 0)
        stop = board(active=mon(HITMONCHAN, (FIGHTING,)), opponent_active=kabuto(energy=[MT]), hand=(DIGGER,))
        with self.assertRaises(Exception) as caught:
            apply_kernel(with_coin_results(stop, H, T), PlayTrainer(0, stop.players[0].hand[0]))
        self.assertEqual(caught.exception.code, "UNRESOLVED_TRAINER_DAMAGE_REDUCTION")

    def test_minefield_ex1_function(self):
        """EX1: 手札から出したばかりのたねポケモンにはエネルギーがないので対戦では起こらない。関数を直接呼んで、同じ比べ方であることを確かめる。"""
        state = board(active=mon(HITMONCHAN), opponent_active=kabuto(energy=[MX]))
        self.assertIsNone(E.minefield_received_power_problem(state, 1, state.players[1].active, 10))
        self.assertIsNotNone(E.minefield_received_power_problem(state, 1, state.players[1].active, 20))
        bare = board(active=mon(HITMONCHAN), opponent_active=kabuto())
        self.assertIsNotNone(E.minefield_received_power_problem(bare, 1, bare.players[1].active, 10))


def attack(state, index, *coins, card=None, **options):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, UseAttack(state.current_player, index, card), **options)


def answer(state, choices, **options):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)), **options)


def snapshot(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log], repr(state.rng.getstate())


def rejects(test, state, command, code, error=UnsupportedError):
    before = snapshot(state)
    with test.assertRaises(error) as caught:
        apply_kernel(state, command)
    test.assertEqual(caught.exception.code, code)
    test.assertEqual(snapshot(state), before)
    return caught.exception


def coins(before, after):
    return [e["result"] for e in new_events(before, after, "coin_flip")]


def evolved(card, below, **extra):
    return {"card": card, "evolved_from": below, "evolved_turn": TURN - 2, "played_turn": TURN - 4, **extra}


def without_v0_79(registry: EffectRegistry) -> EffectRegistry:
    """v0.79 で加えた登録（ワザ 94）だけを除いた登録表。"""
    attacks = {k: registry.attack_entry(k.card_id, k.attack_index) for k in registry.attack_keys() if k.card_id not in V0_79_CARDS}
    return EffectRegistry(registry.id, attacks, registry._trainers, registry._powers, registry._energies)


NEW_TYPES = {
    (H_.ARTICUNO_PR1, 0): E.DamageThenParalyzeAndOpponentBenchOnHeads, (H_.AZUMARILL_NEO1, 1): E.DamageThenParalyzeAndOpponentBenchOnHeads,
    (H_.AMPHAROS_NEO1, 0): E.DamageThenParalyzeAndOpponentBenchOnHeads, (H_.PIKACHU_NEO1, 1): E.DamageThenPreventAttackDamageOnHeads,
    (H_.FLAAFFY_NEO3, 1): E.DamageThenOpponentBenchOnHeads, (H_.JYNX_NEO3, 1): E.CoinBonusDamageAndConfuse, (H_.SNUBBULL_NEO3, 1): E.CoinBonusPerOwnCounter,
    (H_.DRATINI_NEO4, 0): E.HealSelfWithoutDamage, (H_.BLAINES_CHARMANDER_GD5, 0): E.DamageThenDiscardOneOnTails,
    (H_.SABRINAS_HAUNTER_GD6, 1): E.CoinChooseOpponentBenchDamage, (H_.SLOWKING_SI, 0): E.SearchTrainerRequiredOnHeads,
    (H_.SNEASEL_PF3, 0): E.CoinDiscardAllOpponentTrainers, (H_.STEELIX_PRN, 0): E.FailOnTailsDamageThenSelfCannotAttack,
}


class RegistrationTest(unittest.TestCase):
    def test_registered_and_classified(self):
        """52 枚とも写しの組 pool_v0_79 にあり、ワザ 94 を登録した。処理に使う文面は kyuura の印刷の文面。新しい組の型は 13 のワザだけ。"""
        extract = read_extract()
        self.assertEqual(tuple(extract["pool_v0_79"]), V0_79_CARDS)
        pool = load_card_pool()
        registry = E.DEFAULT_EFFECTS
        count = new = 0
        for card_id in V0_79_POKEMON:
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertIn(card_id, pool.playable_ids)
                self.assertEqual(definition.powers, ())
                for index, attack_def in enumerate(definition.attacks):
                    entry = registry.attack_entry(card_id, index)
                    self.assertEqual(entry.name_ja, attack_def.name_ja)
                    self.assertEqual(entry.effect.check(attack_def), [])
                    count += 1
                    if (card_id, index) in NEW_TYPES:
                        self.assertIs(type(entry.effect), NEW_TYPES[card_id, index])
                        new += 1
                    else:
                        self.assertNotIn(type(entry.effect), set(NEW_TYPES.values()))
                    if attack_def.text_ja is None:
                        self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (None, None, None))
                    else:
                        self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (attack_def.text_ja, attack_def.text_ja, "kyuura data/cards.json"))
        self.assertEqual((count, new), (94, 13))
        for new_id, original in (("QSG-033", "ES2-020"), ("QSG-028", "ES3-022")):
            for index in (0, 1):
                self.assertIs(registry.attack_entry(new_id, index), registry.attack_entry(original, index))
        self.assertEqual(dict(E.SAME_DATA_CARDS_V0_79), {"QSG-033": "ES2-020", "QSG-028": "ES3-022"})

    def test_records(self):
        """採用の記録（52 件。外部照合なし・kyuura の記録の id なし・照合の記録には加えない）と、研究の対応表（説明文のあるワザ 83）。停止コード・未解決の裁定は PK1 を加えた。"""
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        verification = (ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8")
        adopted = set(links["latest_descriptions"]["adopted_printed_text"])
        pool = load_card_pool()
        texts = 0
        for card in V0_79_CARDS:
            with self.subTest(card=card):
                record = sources[card]
                self.assertEqual((record["basis"], record["status"], record["external_checks"], record["kyuura_records"], record["kyuura_commit"]),
                                 ("kyuura_data", "adopted", [], [], "7d3f4ca76c084774efb4ac6a1d3a943387e183c3"))
                self.assertNotIn(card, verification)
                for index, attack_def in enumerate(pool.get(card).attacks):
                    key = f"attack/{index}"
                    self.assertEqual(key in record["play_text"], attack_def.text_ja is not None)
                    self.assertEqual(f"{card}/{key}" in adopted, attack_def.text_ja is not None)
                    texts += attack_def.text_ja is not None
        self.assertEqual(texts, 83)
        entry = links["stop_codes"]["UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT"]
        self.assertEqual((entry["kyuura_disposition"], entry["engine_rulings"][0]["ruling_id"]), ("not_in_kyuura", "PK1"))
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (178, 180))  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚）・停止コード 9 件を加えた

    def test_counts(self):
        """写し・対応するカード 943、ポケモン 695・トレーナー 213・エネルギー 35、ワザ 1,182・特殊能力 74・特殊エネルギー 17。"""
        pool = load_card_pool()
        registry = E.DEFAULT_EFFECTS
        self.assertEqual(len(read_extract()["cards"]), 988)  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚）・停止コード 9 件を加えた
        self.assertEqual(len(pool.playable_ids), 988)  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚を含む）を加えた
        self.assertEqual(dict(Counter(pool.get(c).category for c in pool.playable_ids)), {"pokemon": 695, "trainer": 258, "energy": 35})  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚を含む）を加えた
        self.assertEqual((len(registry.attack_keys()), len(registry.power_keys()), len(registry.energy_ids())), (1182, 74, 17))

    def test_unsupported_counts(self):
        """kyuura data/engine_targets.json（7d3f4ca）の対象 1,377 件から登録を差し引く。全対象の未対応 434・neo 227・拡張パック以外 207（v0.78 は 486・263・223）。"""
        raw = subprocess.run(["git", "-C", str(ROOT.parent / "kyuura"), "show", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3:data/engine_targets.json"],
                             capture_output=True, text=True, check=False)
        if raw.returncode != 0:
            self.skipTest("../kyuura がない")
        data = json.loads(raw.stdout)
        targets = data["cards"] if isinstance(data, dict) else data
        pool = load_card_pool()
        ids = [x["id"] for x in targets]
        self.assertTrue(set(V0_79_CARDS) <= set(ids))
        self.assertEqual(len(ids), 1377)
        self.assertEqual(sum(1 for c in ids if c not in pool.playable_ids), 389)  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚）・停止コード 9 件を加えた
        self.assertEqual(sum(1 for x in targets if x["id"].startswith("neo") and x["id"] not in pool.playable_ids), 191)  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 で neo のトレーナー 25 枚を加えた
        self.assertEqual(sum(1 for x in targets if x["product_group"] != "expansion_pack" and x["id"] not in pool.playable_ids), 198)  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚）・停止コード 9 件を加えた
        self.assertEqual((sum(1 for c in V0_79_CARDS if c.startswith("neo")), sum(1 for c in V0_79_CARDS if not c.startswith("neo"))), (36, 16))

    def test_unregistered_without_the_v0_79_entries(self):
        """v0.79 の登録だけを除くと、52 枚とも未対応にもどり（v0.78 の 891 枚。v0.80 の 30 枚を加えて 921 枚）、ほかのカードの対応は変わらない。写しの v0.78 までの組も変わらない。"""
        before = pool_from_extract(read_extract(), without_v0_79(E.DEFAULT_EFFECTS))
        after = load_card_pool()
        self.assertFalse(before.playable_ids & set(V0_79_CARDS))
        self.assertEqual(after.playable_ids - before.playable_ids, frozenset(V0_79_CARDS))
        self.assertEqual(len(before.playable_ids), 936)  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 の 30 枚を含む
        self.assertFalse((set(E.EQUIVALENT_CARDS) | set(E.REPRINT_CARDS)) & set(V0_79_CARDS))

    def test_wrong_reuses_are_rejected(self):
        """G・J: v0.78 までは形だけを確かめていた型が、違う意味の文面を受け付けない（あやしいおどりはマヒの型、ファイヤーテールはすべてトラッシュする型にならない）。
        もとのカードの文面は今までどおり受け付ける。ほかの組の型も、値・面・対象が違えば受け付けない。"""
        pool = load_card_pool()
        attack = lambda card, i: pool.get(card).attacks[i]
        self.assertNotEqual(E.CoinBonusDamageAndParalyze(20).check(attack(H_.JYNX_NEO3, 1)), [])
        self.assertEqual(E.CoinBonusDamageAndParalyze(20).check(attack("PMCG4-004", 1)), [])
        self.assertEqual(E.CoinBonusDamageAndParalyze(20).check(attack("neo2-035", 0)), [])
        self.assertNotEqual(E.CoinBonusDamageAndParalyze(10).check(attack("neo2-035", 0)), [])
        self.assertNotEqual(E.DamageThenDiscardAllOnTails(E.EnergyType.FIRE).check(attack(H_.BLAINES_CHARMANDER_GD5, 0)), [])
        self.assertEqual(E.DamageThenDiscardAllOnTails(E.EnergyType.FIRE).check(attack("GD5-004", 0)), [])
        self.assertEqual(E.DamageThenDiscardAllOnTails(None).check(attack("PMCG5-032", 0)), [])
        self.assertNotEqual(E.DamageThenDiscardOneOnTails(E.EnergyType.FIRE).check(attack("GD5-004", 0)), [])
        self.assertNotEqual(E.DamageThenDiscardOneOnTails(E.EnergyType.WATER).check(attack(H_.BLAINES_CHARMANDER_GD5, 0)), [])
        self.assertNotEqual(E.CoinBonusDamageAndConfuse(10).check(attack(H_.JYNX_NEO3, 1)), [])
        self.assertNotEqual(E.CoinBonusDamageAndConfuse(20).check(attack("PMCG4-004", 1)), [])
        self.assertNotEqual(E.DamageThenParalyzeAndOpponentBenchOnHeads(20).check(attack(H_.ARTICUNO_PR1, 0)), [])
        self.assertNotEqual(E.DamageThenOpponentBenchOnHeads(10).check(attack(H_.ARTICUNO_PR1, 0)), [])
        self.assertNotEqual(E.DamageThenParalyzeAndOpponentBenchOnHeads(10).check(attack(H_.FLAAFFY_NEO3, 1)), [])
        self.assertNotEqual(E.DamageThenCoinBenchDamageBothSides(10).check(attack(H_.FLAAFFY_NEO3, 1)), [])  # お互いの控えではない
        self.assertNotEqual(E.SelfBarrierOnHeads().check(attack(H_.PIKACHU_NEO1, 1)), [])
        self.assertNotEqual(E.DamageThenSelfBarrierOnHeads().check(attack(H_.PIKACHU_NEO1, 1)), [])
        self.assertNotEqual(E.CoinHeadsDamagePerOwnCounter(10).check(attack(H_.SNUBBULL_NEO3, 1)), [])
        self.assertNotEqual(E.CoinHealSelf(1).check(attack(H_.DRATINI_NEO4, 0)), [])
        self.assertNotEqual(E.HealSelfWithoutDamage(2).check(attack(H_.DRATINI_NEO4, 0)), [])
        self.assertNotEqual(E.ChooseOpponentBenchDamage(30, False).check(attack(H_.SABRINAS_HAUNTER_GD6, 1)), [])
        self.assertNotEqual(E.CoinChooseOpponentPokemonDamage(30).check(attack(H_.SABRINAS_HAUNTER_GD6, 1)), [])  # 相手の場全体ではない
        self.assertNotEqual(E.SearchTrainerOnHeads().check(attack(H_.SLOWKING_SI, 0)), [])  # 「加えてよい」ではない
        self.assertNotEqual(E.SearchTrainerRequiredOnHeads().check(attack("PMCG5-007", 1)), [])
        self.assertNotEqual(E.DiscardOpponentTrainersThenDamage().check(attack(H_.SNEASEL_PF3, 0)), [])
        self.assertNotEqual(E.FailOnTailsDamage(1).check(attack(H_.STEELIX_PRN, 0)), [])
        self.assertNotEqual(E.DamageThenSelfCannotAttack().check(attack(H_.STEELIX_PRN, 0)), [])
        self.assertNotEqual(E.FailOnTailsDamageThenSelfCannotAttack().check(attack(H_.SKARMORY_NEO1 if hasattr(H_, "SKARMORY_NEO1") else "neo1-058", 0)), [])

    def test_existing_type_boundaries(self):
        """既存の型で登録したワザの境界: 相手の場全体を選ぶ（neo3-011・neo3-016）、弱点・抵抗力だけを計算しない（neo1-046・SI-017）と相手の効果も受けない（サンド）、
        切り上げ（GD3-012）、10 ダメージのある軽減（neo4-085）、「うら」が出るまで（neo3-015）。数の値は文面の値と照らす。"""
        pool = load_card_pool()
        attack = lambda card, i: pool.get(card).attacks[i]
        reg = E.DEFAULT_EFFECTS
        self.assertIsInstance(reg.attack_entry("neo3-011", 1).effect, E.CoinChooseOpponentPokemonDamage)
        self.assertIsInstance(reg.attack_entry("neo3-016", 0).effect, E.CoinChooseOpponentPokemonDamage)
        self.assertIsInstance(reg.attack_entry("neo1-046", 1).effect, E.ChooseOpponentPokemonDamage)
        self.assertIsInstance(reg.attack_entry("ES2-020", 1).effect, E.DamageIgnoringDefenderEffects)
        self.assertEqual(reg.attack_entry("GD3-012", 0).effect, E.HalfRemainingHpDamage(round_down=False))
        self.assertNotEqual(E.HalfRemainingHpDamage(round_down=True).check(attack("GD3-012", 0)), [])
        self.assertEqual(reg.attack_entry("neo4-085", 0).effect, E.DamageThenReduceDamageNextTurn(10))
        self.assertNotEqual(E.ReduceDamageNextTurn(10).check(attack("neo4-085", 0)), [])
        self.assertIsInstance(reg.attack_entry("neo3-015", 1).effect, E.CoinsUntilTailsDamage)
        self.assertNotEqual(E.CoinsUntilTailsDamage(10).check(attack("neo3-015", 1)), [])
        self.assertNotEqual(E.CoinFlipDamage(coins=3, damage_per_heads=10).check(attack("neo1-003", 1)), [])
        self.assertNotEqual(E.ChooseOpponentPokemonDamage(10).check(attack("neo1-046", 1)), [])
        self.assertNotEqual(E.FailOnTailsDamage(1).check(attack("neo4-092", 1)), [])
        # サンドの「抵抗カ」は写しのまま（写しを直していない）
        self.assertIn("抵抗カ", attack("ES2-020", 1).text_ja)

    def test_evolution_lines(self):
        """進化は名前の完全一致と段階で決まり、商品をまたぐ。"""
        pool = load_card_pool()
        for card, below in ((H_.AZUMARILL_NEO1, "マリル"), (H_.AMPHAROS_NEO1, "モココ"), (H_.FLAAFFY_NEO3, "メリープ"), (H_.STEELIX_PRN, "イワーク"),
                            (H_.SLOWKING_SI, "ヤドン"), (H_.SABRINAS_HAUNTER_GD6, "ナツメのゴース"), (H_.LT_SURGES_RATICATE_GD3, "マチスのコラッタ")):
            self.assertEqual(pool.get(card).evolves_from, below)


class ParalyzeAndBenchTest(unittest.TestCase):
    """D: 「おもて」でマヒと相手の控え全員に 10（1 枚のコイン）。"""

    def articuno(self, **opponent):
        return board(active=mon(H_.ARTICUNO_PR1, (WATER,) * 3), bench=(mon(RATTATA),),
                     opponent_active=mon(HITMONCHAN, **opponent), opponent_bench=(mon(RATTATA), mon(H_.PIKACHU_NEO1)))

    def test_heads_and_tails(self):
        state = self.articuno()
        heads = attack(state, 0, H)
        self.assertEqual(coins(state, heads), ["heads"])
        self.assertEqual([e["amount"] for e in new_events(state, heads, "damage")], [20, 10, 10])
        self.assertTrue(heads.players[1].active.conditions.paralyzed)
        self.assertEqual([p.damage for p in heads.players[1].bench], [10, 10])
        self.assertEqual(heads.players[0].bench[0].damage, 0)
        audited(self, heads)
        tails = attack(state, 0, T)
        self.assertEqual([e["amount"] for e in new_events(state, tails, "damage")], [20])
        self.assertFalse(tails.players[1].active.conditions.paralyzed)

    def test_bench_damage_stays_when_the_active_is_knocked_out_or_prevented(self):
        knocked = attack(self.articuno(damage=60), 0, H)
        self.assertEqual([p.damage for p in knocked.players[1].bench], [10, 10])
        self.assertFalse(any(e.get("condition") == "paralysis" for e in new_events(self.articuno(damage=60), knocked, "special_condition")))
        prevented = self.articuno(prevent_damage=TURN - 1)
        after = attack(prevented, 0, H)
        self.assertEqual(new_events(prevented, after, "damage_prevented")[0]["pokemon_id"], prevented.players[1].active.pokemon_id)
        self.assertEqual([p.damage for p in after.players[1].bench], [10, 10])
        self.assertTrue(after.players[1].active.conditions.paralyzed)  # 「ダメージを受けない」状態でも効果は受ける

    def test_without_bench_only_paralysis_decides_the_coin(self):
        state = board(active=mon(H_.ARTICUNO_PR1, (WATER,) * 3), opponent_active=mon(HITMONCHAN), opponent_bench=())
        after = attack(state, 0, H)
        self.assertEqual(coins(state, after), ["heads"])
        self.assertTrue(after.players[1].active.conditions.paralyzed)

    def test_preflight_modes_agree(self):
        state = self.articuno()
        results = {mode: snapshot(attack(state, 0, H, preflight=mode)) for mode in PREFLIGHT_MODES}
        self.assertEqual(len({repr(v) for v in results.values()}), 1)


class PreventAttackDamageTest(unittest.TestCase):
    """E: ピカチュウの「こうそくいどう」（「おもて」なら次の相手の番、ワザによるダメージだけを受けない）と「でんこうせっか」（+10）。"""

    def pikachu(self):
        return board(active=mon(H_.PIKACHU_NEO1, (LIGHTNING,) * 3), opponent_active=mon(HITMONCHAN, (FIGHTING,) * 3), hand=())

    def test_heads_gives_attack_damage_prevention(self):
        state = self.pikachu()
        after = attack(state, 1, H)
        effects = after.players[0].active.persistent_effects
        self.assertEqual([type(e) for e in effects], [PreventAttackDamage])
        self.assertEqual(new_events(state, after, "persistent_effect_added")[0]["persistent_effect"], "prevent_attack_damage")
        self.assertEqual(attack(state, 1, T).players[0].active.persistent_effects, ())
        audited(self, after)
        # 次の相手の番、ワザのダメージを受けない
        hit = attack(after, 0)
        self.assertEqual(len(new_events(after, hit, "damage_prevented")), 1)
        self.assertEqual(hit.players[0].active.damage, 0)

    def test_quick_attack_bonus_is_ten(self):
        state = self.pikachu()
        self.assertEqual([e["amount"] for e in new_events(state, attack(state, 0, H), "damage")], [20])
        self.assertEqual([e["amount"] for e in new_events(state, attack(state, 0, T), "damage")], [10])

    def test_trainer_damage_is_not_prevented(self):
        """ワザによるダメージだけ（バトル場は穴だらけ! のダメージは受ける）。「かたまる」（PreventDamage）は防ぐ（v0.61）。"""
        effect = PreventAttackDamage(source_card=0, source_player=1, created_turn=TURN - 1, active_turn=TURN)
        self.assertTrue(effect.attack_only)
        self.assertFalse(PreventDamage.attack_only)
        self.assertIsInstance(effect, PreventDamage)
        self.assertNotEqual(PreventAttackDamage.kind, PreventDamage.kind)


class OpponentBenchOnHeadsTest(unittest.TestCase):
    """F: モココの「エレキテール」（「おもて」なら相手の控え全員に 10 だけ）。"""

    def flaaffy(self, opponent_bench=(RATTATA, RATTATA)):
        return board(active=evolved(H_.FLAAFFY_NEO3, MAREEP_NEO2, energy=[LIGHTNING] * 3), opponent_active=mon(HITMONCHAN),
                     opponent_bench=tuple(mon(c) for c in opponent_bench))

    def test_heads_tails_and_no_bench(self):
        state = self.flaaffy()
        heads = attack(state, 1, H)
        self.assertEqual([e["amount"] for e in new_events(state, heads, "damage")], [30, 10, 10])
        self.assertEqual(heads.players[1].active.conditions, state.players[1].active.conditions)
        tails = attack(state, 1, T)
        self.assertEqual([e["amount"] for e in new_events(state, tails, "damage")], [30])
        none = self.flaaffy(())
        after = attack(none, 1)
        self.assertEqual(coins(none, after), [])  # 処理の対象がないので投げない
        self.assertEqual([e["amount"] for e in new_events(none, after, "damage")], [30])
        audited(self, heads)


class CoinBonusConfuseTest(unittest.TestCase):
    """G: ルージュラの「あやしいおどり」（「おもて」なら 40 とこんらん、「うら」なら 20）。"""

    def test_heads_and_tails(self):
        state = board(active=mon(H_.JYNX_NEO3, (PSYCHIC, PSYCHIC, WATER)), opponent_active=mon(HITMONCHAN))
        heads = attack(state, 1, H)
        self.assertEqual([e["amount"] for e in new_events(state, heads, "damage")], [40])
        self.assertTrue(heads.players[1].active.conditions.confused)
        tails = attack(state, 1, T)
        self.assertEqual([e["amount"] for e in new_events(state, tails, "damage")], [20])
        self.assertFalse(tails.players[1].active.conditions.confused)
        self.assertEqual(coins(state, heads), ["heads"])
        audited(self, heads)


class CoinBonusPerCounterTest(unittest.TestCase):
    """H: ブルーの「いかりのずつき」（「おもて」なら 10 + 自分のカウンター × 10、「うら」なら 10）。"""

    def test_values(self):
        for damage, side, expected in ((30, H, 40), (30, T, 10), (0, H, 10)):
            with self.subTest(damage=damage, side=side):
                state = board(active=mon(H_.SNUBBULL_NEO3, (WATER, WATER), damage=damage), opponent_active=mon(ONIX))
                after = attack(state, 1, side)
                self.assertEqual([e["amount"] for e in new_events(state, after, "damage")], [expected])


class HealOneTest(unittest.TestCase):
    """I: ミニリュウの「だっぴ」（ダメージなし。自分のカウンターを 1 個とりのぞく）。"""

    def test_heal(self):
        state = board(active=mon(H_.DRATINI_NEO4, (WATER,), damage=20), opponent_active=mon(HITMONCHAN))
        after = attack(state, 0)
        self.assertEqual(after.players[0].active.damage, 10)
        self.assertEqual(new_events(state, after, "damage"), [])
        self.assertEqual(coins(state, after), [])
        zero = board(active=mon(H_.DRATINI_NEO4, (WATER,)), opponent_active=mon(HITMONCHAN))
        self.assertEqual(attack(zero, 0).players[0].active.damage, 0)
        audited(self, after)


class DiscardOneOnTailsTest(unittest.TestCase):
    """J: カツラのヒトカゲの「ファイヤーテール」（20 のあと「うら」なら炎エネルギーカードを 1 枚選んでトラッシュ。すべてではない）。"""

    def charmander(self, fires=2):
        return board(active=mon(H_.BLAINES_CHARMANDER_GD5, (FIRE,) * fires), opponent_active=mon(HITMONCHAN))

    def test_tails_offers_one_card(self):
        state = self.charmander(2)
        waiting = attack(state, 0, T)
        self.assertEqual((waiting.decision.kind, waiting.decision.player, waiting.decision.min_choices, waiting.decision.max_choices),
                         (DISCARD_ENERGY, 0, 1, 1))
        self.assertEqual(waiting.players[1].active.damage, 20)  # ダメージはトラッシュの前
        rejects(self, waiting, ResolveDecision(0, waiting.decision.id, tuple(waiting.decision.options)), "INVALID_CHOICE_COUNT", IllegalActionError)
        done = answer(waiting, (waiting.decision.options[1],))
        self.assertEqual(len(done.players[0].active.energy), 1)
        self.assertEqual(done.players[1].active.damage, 20)
        audited(self, done)
        one = self.charmander(1)
        self.assertEqual(attack(one, 0, T).decision.kind, DISCARD_ENERGY)  # 1 枚でも決定を出す（K2）
        heads = attack(state, 0, H)
        self.assertEqual(len(heads.players[0].active.energy), 2)
        self.assertIsNone(heads.decision)

    def test_lacking_card_keeps_the_damage(self):
        """選べるカードがない（ピッピの「ゆびをふる」で使う）: トラッシュせずコインも投げない。与えたダメージは残る。"""
        state = board(active=mon(CLEFAIRY, (FIGHTING,) * 3), opponent_active=mon(H_.BLAINES_CHARMANDER_GD5, (FIRE,)))
        waiting = attack(state, 1)
        self.assertEqual(waiting.decision.kind, SELECT_ATTACK)
        after = answer(waiting, (0,))
        self.assertIsNone(after.decision)
        self.assertEqual(after.players[1].active.damage, 20)
        self.assertEqual(new_events(waiting, after, "discard_energy_failed")[0]["outcome"], "skip")
        self.assertEqual(coins(waiting, after), [])


class ChooseBenchOnHeadsTest(unittest.TestCase):
    """K: ナツメのゴーストの「かげからおそう」（「おもて」なら相手の控え 1 匹に、弱点・抵抗力に関係なく 30。対戦ポケモンにはダメージを与えない）。"""

    def haunter(self, bench=(H_.ELECTABUZZ_PR1, RATTATA)):
        return board(active=evolved(H_.SABRINAS_HAUNTER_GD6, SABRINAS_GASTLY, energy=[PSYCHIC] * 3), opponent_active=mon(HITMONCHAN),
                     opponent_bench=tuple(mon(c) for c in bench))

    def test_heads_choose(self):
        state = self.haunter()
        waiting = attack(state, 1, H)
        self.assertEqual((waiting.decision.kind, waiting.decision.player), (SELECT_POKEMON, 0))
        target = waiting.decision.options[1]
        after = answer(waiting, (target,))
        self.assertEqual([(e["pokemon_id"], e["amount"]) for e in new_events(state, after, "damage")], [(target, 30)])
        self.assertEqual(after.players[1].active.damage, 0)
        audited(self, after)
        tails = attack(state, 1, T)
        self.assertIsNone(tails.decision)
        self.assertEqual(new_events(state, tails, "damage"), [])

    def test_no_bench(self):
        state = self.haunter(())
        after = attack(state, 1)
        self.assertEqual((coins(state, after), new_events(state, after, "damage")), ([], []))


class RequiredTrainerSearchTest(unittest.TestCase):
    """L: ヤドキングの「ひらめく」（「おもて」なら山札のトレーナーカード 1 枚を必ず見せて手札に加え、切る）。"""

    def test_search(self):
        state = board(active=evolved(H_.SLOWKING_SI, SLOWPOKE, energy=[PSYCHIC]), opponent_active=mon(HITMONCHAN))
        state = _with_deck(state, 0, [PLUSPOWER, WATER, DEFENDER, WATER])
        waiting = attack(state, 0, H)
        self.assertEqual((waiting.decision.kind, waiting.decision.min_choices, waiting.decision.max_choices), (SEARCH_DECK, 1, 1))
        self.assertIn(SEARCH_DECK, HIDDEN_COUNT_KINDS)
        rejects(self, waiting, ResolveDecision(0, waiting.decision.id, ()), "INVALID_CHOICE_COUNT", IllegalActionError)
        opponent_view = observe(waiting, 1)["decision"]
        self.assertNotIn("options", opponent_view)
        card = waiting.decision.options[0]
        after = answer(waiting, (card,))
        self.assertIn(card, after.players[0].hand)
        kinds = [e["kind"] for e in new_events(waiting, after)]
        self.assertLess(kinds.index("reveal_from_deck"), kinds.index("shuffle"))
        audited(self, after)

    def test_no_trainer_and_tails(self):
        state = _with_deck(board(active=evolved(H_.SLOWKING_SI, SLOWPOKE, energy=[PSYCHIC]), opponent_active=mon(HITMONCHAN)), 0, [WATER] * 4)
        after = attack(state, 0, H)
        self.assertIsNone(after.decision)
        self.assertEqual([e["kind"] for e in new_events(state, after, "reveal_from_deck_none", "shuffle")], ["reveal_from_deck_none", "shuffle"])
        tails = attack(state, 0, T)
        self.assertEqual(new_events(state, tails, "reveal_from_deck_none", "shuffle", "reveal_from_deck"), [])


def _with_deck(state, player, cards):
    """テストの盤面の山札を ``cards`` に置きかえた状態（build_test_state の "deck" で作り直す）。"""
    from tests.helpers import build_test_state

    specs = []
    for index in (0, 1):
        p = state.players[index]
        spec = {"active": _spec(state, p.active), "bench": [_spec(state, b) for b in p.bench], "hand": [state.cards[u].card_id for u in p.hand],
                "deck": cards if index == player else [state.cards[u].card_id for u in p.deck]}
        specs.append(spec)
    return build_test_state(specs, turn_number=state.turn_number, current_player=state.current_player)


def _spec(state, pokemon):
    spec = {"card": state.cards[pokemon.card].card_id, "energy": [state.cards[u].card_id for u in pokemon.energy], "damage": pokemon.damage}
    if pokemon.evolution_stack:
        spec.update(evolved_from=[state.cards[u].card_id for u in pokemon.evolution_stack] if len(pokemon.evolution_stack) > 1
                    else state.cards[pokemon.evolution_stack[0]].card_id, evolved_turn=pokemon.evolved_turn, played_turn=pokemon.played_turn)
    return spec


class DiscardAllOpponentTrainersTest(unittest.TestCase):
    """M: ニューラの「だましとる」（「おもて」なら相手の場のポケモン全員のトレーナーカードをすべてトラッシュ）。"""

    def sneasel(self, active_trainers=((DEFENDER, TURN),), bench_trainers=((DEFENDER, TURN),), **active):
        return board(active={"card": H_.SNEASEL_PF3, "energy": [DK], "trainers": [(PLUSPOWER, TURN)]},
                     opponent_active={"card": HITMONCHAN, "trainers": list(active_trainers), **active},
                     opponent_bench=({"card": RATTATA, "trainers": list(bench_trainers)}, mon(RATTATA)))

    def test_heads_and_tails(self):
        state = self.sneasel()
        heads = attack(state, 0, H)
        discarded = [(e["pokemon_id"], e["reason"]) for e in new_events(state, heads, "discard_attached_trainer")]
        opponent = [state.players[1].active.pokemon_id, state.players[1].bench[0].pokemon_id]
        self.assertEqual([pid for pid, reason in discarded if reason == "attack"], opponent)
        self.assertNotIn((state.players[0].active.pokemon_id, "attack"), discarded)  # 自分のカードは変えない（番の終わりの期限でトラッシュ）
        self.assertEqual(sorted(state.cards[u].card_id for u in heads.players[1].discard), [DEFENDER, DEFENDER])
        self.assertEqual(new_events(state, heads, "damage"), [])
        audited(self, heads)
        tails = attack(state, 0, T)
        self.assertFalse([e for e in new_events(state, tails, "discard_attached_trainer") if e["reason"] == "attack"])

    def test_no_trainers_no_coin(self):
        state = self.sneasel((), ())
        after = attack(state, 0)
        self.assertEqual(coins(state, after), [])


class MetalCrushTest(unittest.TestCase):
    """N: ハガネールの「メタルクラッシュ」（「うら」なら失敗。どちらでも次の自分の番はワザを使えない）。"""

    def steelix(self):
        return board(active=evolved(H_.STEELIX_PRN, ONIX, energy=[MT, FIGHTING, WATER]), opponent_active=mon(HITMONCHAN))

    def test_heads_and_tails_both_lock(self):
        state = self.steelix()
        for side, damage in ((H, 50), (T, 0)):
            with self.subTest(side=side):
                after = attack(state, 0, side)
                self.assertEqual(after.players[1].active.damage, damage)
                self.assertEqual([type(e) for e in after.players[0].active.persistent_effects], [CannotAttackNextOwnTurn])
                self.assertEqual(len(new_events(state, after, "persistent_effect_added")), 1)
                self.assertEqual(bool(new_events(state, after, "attack_failed")), side is T)
                audited(self, after)
                # 次の相手の番を終えると、次の自分の番はどちらのワザも使えない。「にげる」は止めない
                mine = apply_kernel(after, EndTurn(1))
                for index in (0, 1):
                    rejects(self, mine, UseAttack(0, index), "ATTACK_PREVENTED", IllegalActionError)
                self.assertNotEqual(mine.players[0].active.persistent_effects, ())

    def test_expires_after_the_next_own_turn(self):
        after = attack(self.steelix(), 0, H)
        mine = apply_kernel(after, EndTurn(1))
        later = apply_kernel(apply_kernel(mine, EndTurn(0)), EndTurn(1))
        self.assertEqual(later.players[0].active.persistent_effects, ())

    def test_copied_metal_crush_locks_the_copier(self):
        state = board(active=mon(CLEFAIRY, (FIGHTING,) * 3), opponent_active={**evolved(H_.STEELIX_PRN, ONIX, energy=[MT]), "evolved_turn": TURN - 1, "played_turn": TURN - 3})
        waiting = attack(state, 1)
        after = answer(with_coin_results(waiting, T), (0,))
        self.assertEqual([type(e) for e in after.players[0].active.persistent_effects], [CannotAttackNextOwnTurn])
        self.assertTrue(new_events(waiting, after, "attack_failed"))


class DecisionsAndPreflightTest(unittest.TestCase):
    """決定を出す組み合わせ（J・K・L）: 決めるのはワザを使ったプレイヤー、待っている状態の書き出しと観測、答えのあとにコインを投げ直さない、カードの保存則（不変条件）。
    先読みの 3 つの方法で、代表の盤面の結果が同じ。"""

    def boards(self):
        charmander = board(active=mon(H_.BLAINES_CHARMANDER_GD5, (FIRE, FIRE)), opponent_active=mon(HITMONCHAN))
        haunter = board(active=evolved(H_.SABRINAS_HAUNTER_GD6, SABRINAS_GASTLY, energy=[PSYCHIC] * 3), opponent_active=mon(HITMONCHAN),
                        opponent_bench=(mon(RATTATA), mon(H_.ELECTABUZZ_PR1)))
        slowking = _with_deck(board(active=evolved(H_.SLOWKING_SI, SLOWPOKE, energy=[PSYCHIC]), opponent_active=mon(HITMONCHAN)), 0,
                              [PLUSPOWER, WATER, DEFENDER, WATER])
        return {"J": (charmander, 0, T), "K": (haunter, 1, H), "L": (slowking, 0, H)}

    def test_waiting_states_and_no_reflip(self):
        for name, (state, index, side) in self.boards().items():
            with self.subTest(name):
                waiting = attack(state, index, side)
                self.assertEqual(waiting.decision.player, 0)
                audited(self, waiting)
                done = answer(waiting, waiting.decision.options[:1])
                self.assertEqual(coins(waiting, done), [])
                audited(self, done)

    def test_preflight_modes_agree(self):
        for name, (state, index, side) in self.boards().items():
            with self.subTest(name):
                results = set()
                for mode in PREFLIGHT_MODES:
                    waiting = attack(state, index, side, preflight=mode)
                    done = answer(waiting, waiting.decision.options[:1], preflight=mode)
                    results.add(repr(snapshot(done)))
                self.assertEqual(len(results), 1)


class DocumentTest(unittest.TestCase):
    def test_document_exists_and_names_the_cards(self):
        text = DOC.read_text(encoding="utf-8")
        for word in ("943", "434", "227", "207", "UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT", "PK1", "書き出しの形式は 22", "抵抗カ"):
            self.assertIn(word, text)
        for card in V0_79_CARDS:
            self.assertIn(card, text)


if __name__ == "__main__":
    unittest.main()
