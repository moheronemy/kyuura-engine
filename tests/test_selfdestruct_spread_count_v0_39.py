"""v0.39: じばく・控えへのダメージ・場のポケモンの数でダメージが決まるワザを中心とする 15 枚（docs/selfdestruct-spread-count-v0.39.md）。

カードの登録と記録（``CardDataTest``）、説明の文面の受け付けと拒否（``TextTest``）、進化（``EvolutionTest``）、じばく（``SelfDestructTest``）、ソニックブーム
（``SonicBoomTest``）、相手の控えを 1 匹選ぶスパーク（``SparkTest``）、最大 3 匹を選ぶギガスパーク（``GigaSparkTest``）、タイプでしぼる控えへのダメージ
（``TypeFilteredBenchTest``）、コインで両方の控えへのダメージ（``FartGasTest``）、場のポケモンの数（``CountDamageTest``）、同じコインのダメージと自分へのダメージ
（``SuddenExplosionTest``）、特殊などく（``ToxicGasTest``）、同じコインのどくと控えへのダメージ（``DangerousSporeTest``）、相手が選ぶ入れ替え（``GustTest``）、
まねるワザ（``CopyTest``）、不変条件・書き出し・保存と再開・拒否で状態が変わらない（``IntegrityTest``）、先読みの方法ごとの一致（``PreflightParityTest``）に分けた。

根拠は kyuura データの採用（kyuura の印刷の文面。``card_sources.json``）と、既存の記録の再利用（p.309 のワザの手順と「処理の対象がない」・p.310 の進化・
p.320 の要素の順番とダメージの (1)〜(4)・p.321 のダメージの計算の段階・p.257 の自分へのダメージとプラスパワー・ディフェンダー・p.311 と p.323〜p.325 の
きぜつ・サイド・勝ち負け・v0.3a の特殊などく・CR-COUNTERATTACK-TIMING・CR-TRANSPARENCY-BENCH・v0.37 の JS1・v0.34 の TP3・v0.31 の HC3）。ガイドブックは読んで
いない。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import unittest
from typing import ClassVar

from kyuura_engine import (
    EngineError,
    EvolvePokemon,
    IllegalActionError,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    check_invariants,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, read_extract
from kyuura_engine.decisions import FORCED_SWITCH, PROMOTE_ACTIVE, SELECT_ATTACK, SELECT_POKEMON, TAKE_PRIZE
from kyuura_engine.resolution import PREFLIGHT_MODES, programs, v013_checks
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.rng import rng_fingerprint
from scripts import check_card_sources as cs
from scripts.extract_kyuura_cards import PREVIOUS_KYUURA_COMMIT as ADOPTED_COMMIT  # v0.69: 採用したときのデータのコミット（採用の記録は書き換えない）
from tests.helpers import (
    V0_69_STOP_CODE_ISSUES,
    kyuura_records_since_v0_69,
    ATTACK_TYPES_SINCE_V0_17,
    BULBASAUR,
    CATERPIE,
    CLEFABLE,
    CLEFAIRY,
    DEFENDER,
    DIGLETT,
    ELECTRODE,
    ERIKAS_PARAS,
    FIGHTING,
    FOSSIL_MAGNETON,
    FOSSIL_RAICHU,
    FOSSIL_WEEZING,
    GASTLY,
    GIOVANNIS_NIDORAN_F,
    GIOVANNIS_NIDORINA,
    GRASS,
    HAUNTER,
    HITMONCHAN,
    JIGGLYPUFF,
    JUNGLE_PIKACHU,
    KOFFING,
    KOGAS_KOFFING,
    KOGAS_KOFFING_40,
    KOGAS_WEEZING,
    LIGHTNING,
    LT_SURGES_MAGNEMITE,
    LT_SURGES_MAGNEMITE_30,
    LT_SURGES_PIKACHU,
    LT_SURGES_VOLTORB,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MAGNEMITE,
    MAGNETON,
    METAPOD,
    MEWTWO,
    MISTYS_POLIWAG,
    MISTYS_POLIWHIRL,
    MISTYS_POLIWRATH,
    MISTYS_PSYDUCK,
    NIDOKING,
    NIDOQUEEN,
    NIDORAN_F,
    NIDORAN_M,
    NIDORINA,
    NIDORINO,
    PARAS,
    PIDGEY,
    PIKACHU,
    PLUSPOWER,
    POLIWAG,
    POLIWHIRL,
    PSYCHIC,
    RAICHU,
    RATTATA,
    ROCKET_KOFFING,
    ROCKET_MAGNEMITE,
    ROCKET_VOLTORB,
    SANDSHREW,
    SQUIRTLE,
    V0_39_POKEMON,
    VOLTORB,
    WATER,
    WIGGLYTUFF,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.test_barrier_resume_coin_bonus_v0_34 import assert_stops, coins, events, first, full, kinds, play

ROOT = pathlib.Path(__file__).resolve().parent.parent
TURN = 7
DOC = ROOT / "docs" / "selfdestruct-spread-count-v0.39.md"
L, F, W, G, P = LIGHTNING, FIGHTING, WATER, GRASS, PSYCHIC
BELOW = {MAGNETON: MAGNEMITE, FOSSIL_MAGNETON: MAGNEMITE, FOSSIL_WEEZING: KOFFING, FOSSIL_RAICHU: PIKACHU, ELECTRODE: VOLTORB,
         MISTYS_POLIWRATH: [MISTYS_POLIWAG, MISTYS_POLIWHIRL], WIGGLYTUFF: JIGGLYPUFF, NIDOQUEEN: [NIDORAN_F, NIDORINA], KOGAS_WEEZING: KOGAS_KOFFING,
         METAPOD: CATERPIE, MACHAMP: [MACHOP, MACHOKE], HAUNTER: GASTLY, NIDOKING: [NIDORAN_M, NIDORINO], CLEFABLE: CLEFAIRY, NIDORINA: NIDORAN_F,
         MISTYS_POLIWHIRL: MISTYS_POLIWAG, RAICHU: PIKACHU}
# ワザを使うのに足りるエネルギー（無色は別のタイプで払う）
ENERGY = {MAGNEMITE: (L, L), MAGNETON: (L, L, L, L), FOSSIL_WEEZING: (G, G, G), FOSSIL_MAGNETON: (L, L, L, L), JUNGLE_PIKACHU: (L, L),
          FOSSIL_RAICHU: (L, L, L, L), ELECTRODE: (L, L, L), KOGAS_KOFFING_40: (G,), MISTYS_POLIWRATH: (W, W, W, W), ROCKET_MAGNEMITE: (L, L),
          WIGGLYTUFF: (W, W, W), NIDOQUEEN: (G, G, G, G), KOGAS_WEEZING: (G, G, G), PIDGEY: (W, W), ERIKAS_PARAS: (G, G)}
# 登録の実装の型と値（カード id, ワザの位置）
EXPECTED = {
    (MAGNEMITE, 0): (E.ParalyzeOnHeads, {}),
    (MAGNEMITE, 1): (E.SelfDestruct, {"self_damage": 40, "bench_damage": 10, "weakness_resistance_stated": False}),
    (MAGNETON, 0): (E.ParalyzeOnHeads, {}),
    (MAGNETON, 1): (E.SelfDestruct, {"self_damage": 80, "bench_damage": 20, "weakness_resistance_stated": False}),
    (FOSSIL_WEEZING, 0): (E.PoisonOnHeads, {}),
    (FOSSIL_WEEZING, 1): (E.SelfDestruct, {"self_damage": 60, "bench_damage": 10, "weakness_resistance_stated": True}),
    (FOSSIL_MAGNETON, 0): (E.DamageIgnoringWeaknessResistance, {}),
    (FOSSIL_MAGNETON, 1): (E.SelfDestruct, {"self_damage": 100, "bench_damage": 20, "weakness_resistance_stated": True}),
    (JUNGLE_PIKACHU, 0): (E.DamageThenChosenBenchDamage, {"bench_damage": 10, "weakness_resistance_stated": False}),
    (FOSSIL_RAICHU, 0): (E.DamageThenChosenBenchTargets, {"max_targets": 3, "bench_damage": 10}),
    (ELECTRODE, 0): (E.DamageOnly, {}),
    (ELECTRODE, 1): (E.DamageThenSameTypeBenchDamage, {"bench_damage": 10}),
    (KOGAS_KOFFING_40, 0): (E.DamageThenCoinBenchDamageBothSides, {"bench_damage": 10}),
    (MISTYS_POLIWRATH, 0): (E.DamageThenOtherTypeBenchDamageBothSides, {"excluded_type": EnergyType.WATER, "bench_damage": 10}),
    (ROCKET_MAGNEMITE, 0): (E.DamageOnly, {}),
    (ROCKET_MAGNEMITE, 1): (E.DamagePlusPokemonCount, {"per": 10, "scope": "own_bench", "names": ("コイル", "レアコイル", "わるいレアコイル")}),
    (WIGGLYTUFF, 0): (E.PutToSleep, {}),
    (WIGGLYTUFF, 1): (E.DamagePlusPokemonCount, {"per": 10, "scope": "own_bench", "names": None}),
    (NIDOQUEEN, 0): (E.DamagePlusPokemonCount, {"per": 20, "scope": "own_in_play", "names": ("ニドキング",)}),
    (NIDOQUEEN, 1): (E.DamageOnly, {}),
    (KOGAS_WEEZING, 0): (E.CoinBonusDamageAndSelfDamage, {"bonus": 30, "self_damage": 30}),
    (KOGAS_WEEZING, 1): (E.DamageThenSpecialPoisonOnHeads, {"poison_damage": 20}),
    (PIDGEY, 0): (E.DamageAndForceSwitch, {}),
    (ERIKAS_PARAS, 0): (E.DamageOnly, {}),
    (ERIKAS_PARAS, 1): (E.CoinPoisonAndBenchDamage, {"bench_damage": 10}),
}
NEW_TYPES = {E.SelfDestruct, E.DamageIgnoringWeaknessResistance, E.DamageThenChosenBenchTargets, E.DamageThenSameTypeBenchDamage,
             E.DamageThenCoinBenchDamageBothSides, E.DamageThenOtherTypeBenchDamageBothSides, E.DamagePlusPokemonCount, E.CoinBonusDamageAndSelfDamage,
             E.DamageThenSpecialPoisonOnHeads, E.CoinPoisonAndBenchDamage}
# pcg-search.com の対象の版（サイトの一覧の番号。kyuura の id の番号とは違うことがある）と、違いのあった欄
EDITIONS = {MAGNEMITE: "037/096", MAGNETON: "038/096", FOSSIL_WEEZING: "007/048", FOSSIL_MAGNETON: "025/048", JUNGLE_PIKACHU: "024/048",
            FOSSIL_RAICHU: "024/048", ELECTRODE: "025/048", KOGAS_KOFFING_40: "014/098", MISTYS_POLIWRATH: "036/098", ROCKET_MAGNEMITE: "026/065",
            WIGGLYTUFF: "039/048", NIDOQUEEN: "004/048", KOGAS_WEEZING: "016/098", PIDGEY: "059/096", ERIKAS_PARAS: "009/096"}
DIFFERENCES = {FOSSIL_MAGNETON: "pokemon.attacks[0].text.ja", MISTYS_POLIWRATH: "pokemon.attacks[0].text.ja", PIDGEY: "pokemon.attacks[0].name.ja"}


def mon(card, energy=None, **extra):
    spec = {"card": card, "energy": list(ENERGY.get(card, ()) if energy is None else energy), **extra}
    if BELOW.get(card) is not None and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), deck=None, turn=TURN):
    me = {"active": active, "bench": [mon(b, ()) if isinstance(b, str) and b in BELOW else b for b in bench]}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent or mon(HITMONCHAN, (F, F)), "bench": [mon(b, ()) if isinstance(b, str) and b in BELOW else b for b in opponent_bench]}
    return build_test_state([me, them], turn_number=turn)


def snapshot(state):
    return full(state), rng_fingerprint(state.rng), [dict(e) for e in state.log]


def attack(state, index, *sides, answers=(), player=0, mode="derived"):
    return play(with_coin_results(state, *sides), UseAttack(player, index), answers, mode=mode)


def pid_of(state, player, card):
    """プレイヤー ``player`` の場の ``card``（カード id）のポケモンの番号（最初の 1 匹）。"""
    return next(p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card)


def damage_of(state, since, target):
    """ログのワザのダメージ（``target`` の種類ごと）を、受けたポケモンの番号 → 量で返す（相手の対戦ポケモンは番号がないので None）。"""
    return {e.get("pokemon_id"): e["amount"] for e in events(state, since, "damage") if e.get("target") == target and not e.get("retaliation")}


def opponent_damage(state, since):
    return [e["amount"] for e in events(state, since, "damage") if e.get("target") is None and not e.get("retaliation")]


def assert_rejected(test, state, command, code, exception=EngineError):
    before = snapshot(state)
    with test.assertRaises(exception) as raised:
        apply_kernel(state, command)
    test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def card_count(state, player):
    """プレイヤーのカードの枚数（ゾーンのすべて。カードの保存則）。"""
    p = state.players[player]
    in_play = sum(len(x.cards()) + len(x.energy) + len(x.trainers) for x in p.in_play())
    return len(p.hand) + len(p.deck) + len(p.discard) + len(p.prizes) + in_play


class CardDataTest(unittest.TestCase):
    """15 枚の登録・写し・採用の記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_fifteen_requested_cards(self):
        """対象は依頼の 15 枚（ほかの候補に広げていない）。写しの組 pool_v0_39 は 15 枚で、どれも対戦に使える。同じ名前の別のカード（コイル 2 種類・レアコイル
        2 種類・ピカチュウ PMCG1-035・ライチュウ PMCG1-038・キョウのドガース PMCG6-015）とは別の id で、HP かワザが違う。"""
        self.assertEqual(len(V0_39_POKEMON), 15)
        self.assertEqual(list(read_extract()["pool_v0_39"]), list(V0_39_POKEMON))
        for card in V0_39_POKEMON:
            with self.subTest(card=card):
                self.assertTrue(self.pool.is_playable(card))
        for ours, other in ((MAGNEMITE, ROCKET_MAGNEMITE), (MAGNETON, FOSSIL_MAGNETON), (JUNGLE_PIKACHU, PIKACHU), (FOSSIL_RAICHU, RAICHU),
                            (KOGAS_KOFFING_40, KOGAS_KOFFING)):
            with self.subTest(card=ours):
                a, b = self.pool.get(ours), self.pool.get(other)
                self.assertEqual(a.name_ja, b.name_ja)
                self.assertNotEqual((a.hp, [x.name_ja for x in a.attacks]), (b.hp, [x.name_ja for x in b.attacks]))
        # 名前の違う似たカード（マタドガス と キョウのマタドガス・パラス と エリカのパラス・コイル と マチスのコイル）は別の名前
        for ours, other in ((FOSSIL_WEEZING, KOGAS_WEEZING), (ERIKAS_PARAS, PARAS), (MAGNEMITE, LT_SURGES_MAGNEMITE)):
            with self.subTest(card=ours):
                self.assertNotEqual(self.pool.get(ours).name_ja, self.pool.get(other).name_ja)

    def test_every_attack_is_registered_with_the_expected_implementation(self):
        """25 のワザがどれも登録され、型と値が説明に合う（特殊能力を持つカードはない）。説明文のあるワザは、写しの文面（照合用）と処理に使う文面（kyuura の
        印刷の文面）が同じ。"""
        attacks = [(card, a.index) for card in V0_39_POKEMON for a in self.pool.get(card).attacks]
        self.assertEqual(sorted(attacks), sorted(EXPECTED))
        self.assertEqual(len(attacks), 25)
        for card in V0_39_POKEMON:
            self.assertEqual(self.pool.get(card).powers, ())
        for (card, index), (cls, values) in EXPECTED.items():
            with self.subTest(card=card, index=index):
                entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
                self.assertIs(type(entry.effect), cls)
                for name, value in values.items():
                    self.assertEqual(getattr(entry.effect, name), value)
                printed = self.pool.get(card).attacks[index]
                self.assertEqual(entry.name_ja, printed.name_ja)
                self.assertEqual(entry.text_ja, printed.text_ja)
                if printed.text_ja:
                    self.assertEqual(entry.play_text_ja, printed.text_ja)
                self.assertEqual(entry.effect.check(printed), [])

    def test_new_types_are_kernel_programs_outside_the_v013_contract(self):
        """v0.39 の型は解決の基盤の要素の並び（``programs.BUILDERS``）で処理し、v0.13 の約束（``resolve``・``resume``）を上書きしない。``v013_checks.VERIFIED`` に
        入れない（tests/helpers.py の ``ATTACK_TYPES_SINCE_V0_17`` に加えた）。"""
        self.assertEqual(len(NEW_TYPES), 10)
        for cls in NEW_TYPES:
            with self.subTest(cls=cls.__name__):
                self.assertIn(cls, programs.BUILDERS)
                self.assertIn(cls, ATTACK_TYPES_SINCE_V0_17)
                self.assertNotIn(cls, v013_checks.VERIFIED)
                self.assertIs(cls.resolve, E.AttackEffect.resolve)
                self.assertIs(cls.resume, E.AttackEffect.resume)

    def test_adoption_records_and_external_checks(self):
        """15 枚はどれも kyuura データの採用の記録（写しの元のコミット・説明文のあるワザの処理に使う文面の根拠）を持ち、pcg-search.com の同じ版のページと
        照合した。違いは 3 件で、どれも処理に影響しない（ソニックブーム・ウォーターリングの「弱点・抵抗カ」（サイトの文字の違い）、ポッポのワザの名前
        「ふきとばし」と「かぜおこし」。kyuura への報告事項）。kyuura の記録は、研究の基準のコミットでレアコイル（PMCG1-039）を指す CR-TRANSPARENCY の 2 件だけ。
        過去の原典照合の記録（card_verification.json）には入れない。"""
        sources = cs.load_sources()["cards"]
        verification = json.loads((ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8"))["cards"]
        links = cs.load_links()["latest_descriptions"]["adopted_printed_text"]
        for card in V0_39_POKEMON:
            with self.subTest(card=card):
                record = sources[card]
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]), ("kyuura_data", "adopted", ADOPTED_COMMIT))
                expected_records = ["CR-TRANSPARENCY-BENCH", "CR-TRANSPARENCY-MULTIPLE-TARGETS"] if card == MAGNETON else []
                self.assertEqual(record["kyuura_records"], kyuura_records_since_v0_69(card, expected_records))  # v0.69: 研究の基準を上げて加わった kyuura の記録（tests/helpers.py の V0_69_KYUURA_RECORDS_ADDED）
                with_text = {f"attack/{a.index}" for a in self.pool.get(card).attacks if a.text_ja}
                self.assertEqual(set(record["play_text"]), with_text)
                self.assertTrue(all(v == "kyuura_printed_text" for v in record["play_text"].values()))
                self.assertTrue(with_text <= {k.split("/", 1)[1] for k in links if k.startswith(card + "/")})
                [check] = record["external_checks"]
                self.assertEqual(check["site"], "pcg-search.com")
                self.assertEqual(check["edition"]["list_number"], EDITIONS[card])
                if card in DIFFERENCES:
                    self.assertEqual(check["result"], "differences")
                    self.assertEqual([d["field"] for d in check["differences"]], [DIFFERENCES[card]])
                    self.assertFalse(any(d["affects_behavior"] for d in check["differences"]))
                else:
                    self.assertEqual((check["result"], check["differences"]), ("match", []))
                self.assertNotIn(card, verification)

    def test_no_card_specific_branch_in_the_engine(self):
        """engine.py・resolution/ に v0.39 のカード id での分岐を加えていない（効果の型と要素の項目で表す）。"""
        for path in [ROOT / "kyuura_engine" / "engine.py", *(ROOT / "kyuura_engine" / "resolution").glob("*.py")]:
            text = path.read_text(encoding="utf-8")
            for card in V0_39_POKEMON:
                with self.subTest(path=path.name, card=card):
                    self.assertNotIn(card, text)

    def test_gs1_is_one_new_stop_code_and_js1_is_reused(self):
        """GS1（ギガスパークの 0 匹）は新しい停止コード 1 つで、決定の答えのときに止める（H4・ER9 と同じ止め方。宣言の前の問い ``QUESTIONS`` には入れない）。
        研究の対応表では kyuura の未解決の一覧にない（not_in_kyuura）。説明に「弱点・抵抗力」のない控えへのダメージ（第1弾のじばく・スパーク・ビリビリ）は
        v0.37 の JS1 の同じ問い・同じコードで、新しい問いを加えていない。"""
        self.assertNotIn("UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE", {q.code for q in QUESTIONS.values()})
        self.assertEqual([q.key for q in QUESTIONS.values() if q.code == "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE"],
                         ["bench_damage_weakness_resistance"])
        links = cs.load_links()
        entry = links["stop_codes"]["UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE"]
        self.assertEqual((entry["kyuura_disposition"], entry["kyuura_issue"]), ("issue", V0_69_STOP_CODE_ISSUES["UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE"]))  # v0.69: kyuura が論点に結んだ（v0.68 までは not_in_kyuura。tests/helpers.py の V0_69_STOP_CODE_ISSUES）
        self.assertIn("GS1", DOC.read_text(encoding="utf-8"))


class TextTest(unittest.TestCase):
    """型の ``check`` は、登録したワザの印刷の文面と同じ書き方だけを受け付ける（似たワザの文面を推測で同じ型にしない）。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def printed(self, card, index):
        return self.pool.get(card).attacks[index]

    def test_first_set_and_fossil_self_destruct_are_told_apart(self):
        """第1弾のじばく（「自分と相手に…お互いの控えポケモン全員にも」。弱点・抵抗力の記述なし）と第3弾のじばく（「自分にも…「弱点・抵抗力」に関係なく」）は、
        ``weakness_resistance_stated`` の違う値で、もう一方の文面は受け付けない。量の違う値も受け付けない。"""
        first_set, fossil = self.printed(MAGNEMITE, 1), self.printed(FOSSIL_WEEZING, 1)
        self.assertEqual(E.SelfDestruct(40, 10, False).check(first_set), [])
        self.assertNotEqual(E.SelfDestruct(40, 10, True).check(first_set), [])
        self.assertEqual(E.SelfDestruct(60, 10, True).check(fossil), [])
        self.assertNotEqual(E.SelfDestruct(60, 10, False).check(fossil), [])
        self.assertNotEqual(E.SelfDestruct(40, 20, False).check(first_set), [])
        self.assertNotEqual(E.SelfDestruct(30, 10, False).check(first_set), [])
        self.assertNotEqual(E.SelfDestruct(100, 10, True).check(self.printed(FOSSIL_MAGNETON, 1)), [])

    def test_spark_and_fire_ring_texts(self):
        """スパーク（弱点・抵抗力の記述なし）と v0.38 のほのおのわ（「「弱点・抵抗力」に関係なく」）は、同じ型の別の値で、もう一方の文面は受け付けない。"""
        from tests.helpers import BROCKS_VULPIX_50

        spark, ring = self.printed(JUNGLE_PIKACHU, 0), self.printed(BROCKS_VULPIX_50, 1)
        self.assertEqual(E.DamageThenChosenBenchDamage(10, weakness_resistance_stated=False).check(spark), [])
        self.assertNotEqual(E.DamageThenChosenBenchDamage(10).check(spark), [])
        self.assertEqual(E.DamageThenChosenBenchDamage(10).check(ring), [])
        self.assertNotEqual(E.DamageThenChosenBenchDamage(10, weakness_resistance_stated=False).check(ring), [])

    def test_other_values_and_texts_are_rejected(self):
        """量・数・タイプ・名前の違う値は受け付けない（ギガスパークの最大の数・ウォーターリングのタイプ・数える名前・とつぜんばくはつの量・どくの量）。
        ソニックブームの型は、文面のワザの名前と登録のワザの名前が同じものだけ。"""
        import dataclasses

        self.assertNotEqual(E.DamageThenChosenBenchTargets(2, 10).check(self.printed(FOSSIL_RAICHU, 0)), [])
        self.assertNotEqual(E.DamageThenChosenBenchTargets(3, 20).check(self.printed(FOSSIL_RAICHU, 0)), [])
        self.assertNotEqual(E.DamageThenOtherTypeBenchDamageBothSides(EnergyType.FIRE, 10).check(self.printed(MISTYS_POLIWRATH, 0)), [])
        self.assertNotEqual(E.DamagePlusPokemonCount(20, "own_bench").check(self.printed(WIGGLYTUFF, 1)), [])
        self.assertNotEqual(E.DamagePlusPokemonCount(10, "own_bench").check(self.printed(ROCKET_MAGNEMITE, 1)), [])
        self.assertNotEqual(E.DamagePlusPokemonCount(10, "own_in_play", ("ニドキング",)).check(self.printed(NIDOQUEEN, 0)), [])
        with self.assertRaises(ValueError):
            E.DamagePlusPokemonCount(10, "own_bench", ("コイル", "レアコイル"))
        self.assertNotEqual(E.CoinBonusDamageAndSelfDamage(30, 20).check(self.printed(KOGAS_WEEZING, 0)), [])
        self.assertNotEqual(E.DamageThenSpecialPoisonOnHeads(30).check(self.printed(KOGAS_WEEZING, 1)), [])
        self.assertNotEqual(E.CoinPoisonAndBenchDamage(20).check(self.printed(ERIKAS_PARAS, 1)), [])
        sonic = self.printed(FOSSIL_MAGNETON, 0)
        self.assertNotEqual(E.DamageIgnoringWeaknessResistance().check(dataclasses.replace(sonic, name_ja="ちがうワザ")), [])
        # 似たワザ: ふぶき（v0.38。片方の控え）の文面を、両方の控えのおならガスの型では受け付けない。両方の控えのワザの文面を片方の型で受け付けない
        from tests.helpers import ARTICUNO

        self.assertNotEqual(E.DamageThenCoinBenchDamageBothSides(10).check(self.printed(ARTICUNO, 1)), [])
        self.assertNotEqual(E.DamageThenCoinBenchDamageEitherSide(10).check(self.printed(KOGAS_KOFFING_40, 0)), [])


class EvolutionTest(unittest.TestCase):
    """進化元は名前の完全一致（収録の弾で制限しない）。名前の一部・形容詞で比べない。"""

    def evolve(self, below, card):
        if isinstance(below, list):
            active = {"card": below[-1], "evolved_from": below[0] if len(below) == 2 else below[:-1], "played_turn": 1, "evolved_turn": 3}
        else:
            active = {"card": below, "played_turn": 1}
        state = build_test_state([{"active": active, "bench": [RATTATA], "hand": [card]},
                                  {"active": mon(HITMONCHAN, ()), "bench": [RATTATA]}], turn_number=TURN)
        return apply_kernel(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].active.pokemon_id))

    def test_evolves_from_every_card_with_the_exact_name(self):
        """レアコイル 2 種類は第1弾とロケット団のコイルから、マタドガスは第1弾とロケット団のドガースから、ライチュウは 2 種類のピカチュウから、マルマインは
        2 種類のビリリダマから、キョウのマタドガスは 2 種類のキョウのドガースから進化する。2 進化のカスミのニョロボン・ニドクインは、カスミのニョロゾ・ニドリーナ
        から。"""
        for below, card in ((MAGNEMITE, MAGNETON), (ROCKET_MAGNEMITE, MAGNETON), (MAGNEMITE, FOSSIL_MAGNETON), (ROCKET_MAGNEMITE, FOSSIL_MAGNETON),
                            (KOFFING, FOSSIL_WEEZING), (ROCKET_KOFFING, FOSSIL_WEEZING), (PIKACHU, FOSSIL_RAICHU), (JUNGLE_PIKACHU, FOSSIL_RAICHU),
                            (VOLTORB, ELECTRODE), (ROCKET_VOLTORB, ELECTRODE), (KOGAS_KOFFING, KOGAS_WEEZING), (KOGAS_KOFFING_40, KOGAS_WEEZING),
                            (JIGGLYPUFF, WIGGLYTUFF), ([MISTYS_POLIWAG, MISTYS_POLIWHIRL], MISTYS_POLIWRATH), ([NIDORAN_F, NIDORINA], NIDOQUEEN)):
            with self.subTest(below=below, card=card):
                state = self.evolve(below, card)
                self.assertEqual(state.cards[state.players[0].active.card].card_id, card)
                self.assertEqual(check_invariants(state), [])

    def test_names_that_only_look_alike_are_rejected(self):
        """名前が違えば進化しない（マチスのコイル → レアコイル・キョウのドガース → マタドガス・ドガース → キョウのマタドガス・マチスのピカチュウ → ライチュウ・
        マチスのビリリダマ → マルマイン・ニョロゾ → カスミのニョロボン・サカキのニドリーナ → ニドクイン）。"""
        for below, card in ((LT_SURGES_MAGNEMITE, MAGNETON), (LT_SURGES_MAGNEMITE_30, FOSSIL_MAGNETON), (KOGAS_KOFFING, FOSSIL_WEEZING),
                            (KOFFING, KOGAS_WEEZING), (ROCKET_KOFFING, KOGAS_WEEZING), (LT_SURGES_PIKACHU, FOSSIL_RAICHU), (LT_SURGES_VOLTORB, ELECTRODE),
                            ([POLIWAG, POLIWHIRL], MISTYS_POLIWRATH), ([GIOVANNIS_NIDORAN_F, GIOVANNIS_NIDORINA], NIDOQUEEN)):
            with self.subTest(below=below, card=card), self.assertRaises(IllegalActionError) as raised:
                self.evolve(below, card)
            self.assertEqual(raised.exception.code, "EVOLUTION_NAME_MISMATCH")


class SelfDestructTest(unittest.TestCase):
    """じばく（第1弾のコイル・レアコイル、第3弾のマタドガス・レアコイル）: 相手の対戦ポケモン → 自分 → 相手の控えの全員 → 自分の控えの全員。きぜつ・サイド・
    勝ち負け・バトル場に出すのは、すべての要素のあと（p.309・p.324）。"""

    def test_order_amounts_and_targets(self):
        """第1弾のコイル: 相手に 40・自分に 40（ワザによる自分へのダメージ。p.320 の (3)）・相手の控えの全員と自分の控えの全員に 10。ワザの途中ではきぜつの処理を
        しない（ダメージのログ 4 つのあとに knock_out）。"""
        state = board(mon(MAGNEMITE), bench=(RATTATA, PIKACHU), opponent_bench=(RATTATA, BULBASAUR))
        since = len(state.log)
        done = attack(state, 1)
        damage = [(e.get("target"), e["amount"]) for e in events(done, since, "damage")]
        self.assertEqual(damage, [(None, 40), ("self", 40), ("opponent_bench", 10), ("opponent_bench", 10), ("self_bench", 10), ("self_bench", 10)])
        log = kinds(done, since)
        self.assertLess(max(i for i, k in enumerate(log) if k == "damage"), log.index("knock_out"))
        self.assertEqual(coins(done, since), [])

    def test_each_registration_deals_its_printed_amounts(self):
        """4 つのじばくの量（相手・自分・控え）は、登録の値のまま（レアコイル 80・80・20、マタドガス 60・60・10、化石の秘密のレアコイル 100・100・20）。"""
        for card, amounts in ((MAGNETON, (80, 80, 20)), (FOSSIL_WEEZING, (60, 60, 10)), (FOSSIL_MAGNETON, (100, 100, 20))):
            with self.subTest(card=card):
                state = board(mon(card), mon(MACHAMP, (F,), sleep=True), bench=(RATTATA,), opponent_bench=(RATTATA,))
                done = attack(state, 1)
                since = len(state.log)
                self.assertEqual([e["amount"] for e in events(done, since, "damage")], list(amounts[:2]) + [amounts[2]] * 2)

    def test_self_damage_is_calculated_not_an_automatic_knock_out(self):
        """自分へのダメージは、のっているダメージに加えるワザによるダメージ（p.257 の解説のとおりプラスパワー・ディフェンダーを計算する。v0.2f・v0.3d）。HP に
        関係なく自分をきぜつさせる処理ではない: ディフェンダーをつけたコイルは 20 を受けて残る（HP 40）。プラスパワーをつけていれば 50 を受ける。"""
        defended = board(mon(MAGNEMITE, trainers=[(DEFENDER, TURN + 1)]))
        done = attack(defended, 1)
        self.assertEqual(damage_of(done, len(defended.log), "self"), {defended.players[0].active.pokemon_id: 20})
        self.assertEqual(done.players[0].active.damage, 20)
        self.assertNotIn(0, [e["player"] for e in events(done, len(defended.log), "knock_out")])
        self.assertEqual(check_invariants(done), [])
        powered = board(mon(MAGNEMITE, trainers=[(PLUSPOWER, TURN)]))
        after = attack(powered, 1)
        self.assertEqual(list(damage_of(after, len(powered.log), "self").values()), [50])
        self.assertEqual(opponent_damage(after, len(powered.log)), [50])

    def test_first_set_bench_damage_follows_js1(self):
        """第1弾のじばくの控えへのダメージは、説明に弱点・抵抗力の記述がない（v0.37 の JS1 と同じ問い）。どちらかの控えに、計算するかどうかで受けるダメージの
        変わるポケモン（雷に弱点のゼニガメ・雷に抵抗力のサンド）がいれば、宣言の前に止める（相手の控え・自分の控えのどちらでも）。いなければ止めない。"""
        for bench, opponent_bench in (((RATTATA,), (SQUIRTLE,)), ((SQUIRTLE,), (RATTATA,)), ((RATTATA,), (SANDSHREW,)), ((SANDSHREW,), ())):
            with self.subTest(bench=bench, opponent_bench=opponent_bench):
                assert_stops(self, board(mon(MAGNEMITE), bench=bench, opponent_bench=opponent_bench), UseAttack(0, 1),
                             "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE")
        done = attack(board(mon(MAGNEMITE), bench=(RATTATA, BULBASAUR), opponent_bench=(PIKACHU,)), 1)
        self.assertEqual(len(events(done, 0, "damage")), 5)

    def test_fossil_bench_damage_ignores_weakness_and_resistance(self):
        """第3弾のじばく（「弱点・抵抗力」に関係なく）: 控えの弱点・抵抗力を計算しないので止めない（雷に弱点のゼニガメ・抵抗力のサンドにも 20）。相手の対戦
        ポケモンへのダメージは弱点を計算する（説明が控えのダメージだけに書く）。"""
        state = board(mon(FOSSIL_MAGNETON), mon(SQUIRTLE, (W,)), bench=(SQUIRTLE, SANDSHREW), opponent_bench=(SANDSHREW,))
        done = attack(state, 1)
        since = len(state.log)
        self.assertEqual(opponent_damage(done, since), [200])
        self.assertEqual(sorted(damage_of(done, since, "self_bench").values()), [20, 20])
        self.assertEqual(list(damage_of(done, since, "opponent_bench").values()), [20])

    def test_double_knock_out_prizes_and_promotion_order(self):
        """両方の対戦ポケモンがきぜつ（同時のきぜつ。p.324）: サイドを取るのは番のプレイヤーから（v0.2f の正規化）、バトル場に出すのは番でないプレイヤーから
        （pp.323〜324）。控えのきぜつもいっしょに数える。"""
        state = board(mon(MAGNEMITE), mon(RATTATA, ()), bench=({"card": RATTATA, "damage": 20}, PIKACHU), opponent_bench=(RATTATA,))
        current = attack(state, 1)
        since = len(state.log)
        self.assertEqual(kinds(current, since).count("knock_out"), 3)
        seen = []
        while current.decision is not None:
            d = current.decision
            seen.append((d.kind, d.player))
            current = apply_kernel(current, ResolveDecision(d.player, d.id, first(d)))
        self.assertEqual(seen, [(TAKE_PRIZE, 0), (TAKE_PRIZE, 1), (TAKE_PRIZE, 1), (PROMOTE_ACTIVE, 1), (PROMOTE_ACTIVE, 0)])
        self.assertIsNone(current.result)
        self.assertEqual(current.current_player, 1)
        self.assertEqual(check_invariants(current), [])
        self.assertEqual(card_count(current, 0), card_count(state, 0))

    def test_attacker_without_bench_loses_after_the_prizes(self):
        """自分に控えがいなければ、サイドを取ったあとの勝ち負けの判定で負ける（p.311）。勝ち負けを、ワザの途中で判定しない。"""
        state = board(mon(MAGNEMITE), mon(RATTATA, ()), bench=(), opponent_bench=(RATTATA,))
        current = attack(state, 1)
        while current.decision is not None:
            d = current.decision
            current = apply_kernel(current, ResolveDecision(d.player, d.id, first(d)))
        self.assertEqual(current.result.winner, 1)

    def test_prevented_or_barrier_opponent_still_takes_self_and_bench_damage(self):
        """相手の対戦ポケモンが「ダメージを受けない」状態（かたまる）なら、そのポケモンへの要素だけが無効で、自分へのダメージと控えへのダメージは処理する（p.321）。"""
        state = board(mon(MAGNEMITE), mon(METAPOD, (G,), prevent_damage=TURN - 1))
        done = attack(state, 1)
        since = len(state.log)
        self.assertEqual(kinds(done, since)[:2], ["attack", "damage_prevented"])
        self.assertEqual([e.get("target") for e in events(done, since, "damage")], ["self", "opponent_bench", "self_bench"])

    def test_counterattack_is_skipped_when_the_attacker_is_already_knocked_out(self):
        """相手のカイリキーの「はんげき」はダメージの要素をすべて処理したあと（CR-COUNTERATTACK-TIMING）。じばくで自分がすでに HP 以上なら与えない（v0.10 の C15。
        ``counterattack_skipped``）。控えのカイリキーも、相手のワザで控えへのダメージを受けたので判定する（場所を見ない）。どちらも GK1（ダメージ → 入れ替え →
        自分にも）の並びではないので止めない。"""
        for active, bench in ((mon(MACHAMP, (F,)), (RATTATA,)), (mon(HITMONCHAN, (F, F)), (MACHAMP,))):
            with self.subTest(active=active["card"]):
                state = board(mon(MAGNEMITE), active, opponent_bench=bench)
                done = attack(state, 1)
                log = kinds(done, len(state.log))
                self.assertIn("counterattack_skipped", log)
                self.assertNotIn("counterattack", log)
                self.assertLess(max(i for i, k in enumerate(log) if k == "damage"), log.index("counterattack_skipped"))

    def test_transparency_on_bench_is_judged(self):
        """控えのゴースト（化石の秘密。「とうめい」）も、相手のワザのダメージを受けるときに判定する（CR-TRANSPARENCY-BENCH）。コインはゴーストの持ち主が投げる。"""
        state = board(mon(FOSSIL_WEEZING), opponent_bench=(HAUNTER,))
        haunter = pid_of(state, 1, HAUNTER)
        evaded = attack(state, 1, H)
        since = len(state.log)
        self.assertEqual([e["pokemon_id"] for e in events(evaded, since, "evade_check")], [haunter])
        self.assertNotIn(haunter, damage_of(evaded, since, "opponent_bench"))
        hit = attack(state, 1, T)
        self.assertEqual(damage_of(hit, since, "opponent_bench"), {haunter: 10})


class SonicBoomTest(unittest.TestCase):
    """ソニックブーム（化石の秘密のレアコイル）: 相手の弱点・抵抗力（p.321 の 3・4 段階）だけを計算しない。ほかの段階・防ぐ効果・特殊能力はそのまま。"""

    def damage_steps(self, opponent, **extra):
        state = board(mon(FOSSIL_MAGNETON, **extra), opponent)
        done = attack(state, 0)
        return [dict(e) for e in events(done, len(state.log), "damage")], kinds(done, len(state.log))

    def test_weakness_and_resistance_are_ignored(self):
        """雷に弱点のゼニガメにも 20（40 にならない）、雷に抵抗力のサンドにも 20（0 にならない）。ダメージのログの計算の段階に 3・4 がない。"""
        for opponent in (mon(SQUIRTLE, (W,)), mon(SANDSHREW, (F,))):
            with self.subTest(opponent=opponent["card"]):
                [damage], _ = self.damage_steps(opponent)
                self.assertEqual(damage["amount"], 20)
                self.assertEqual([s[0][0] for s in damage["steps"]], ["1"])

    def test_other_modifiers_still_apply(self):
        """プラスパワー（5 段階）は加える（30）、相手のディフェンダー（7 段階）はへらす（0）。「ダメージを受けない」状態は無効にする（damage_prevented）。"""
        [powered], _ = self.damage_steps(mon(SQUIRTLE, (W,)), trainers=[(PLUSPOWER, TURN)])
        self.assertEqual(powered["amount"], 30)
        [defended], _ = self.damage_steps(mon(SQUIRTLE, (W,), trainers=[(DEFENDER, TURN)]))
        self.assertEqual(defended["amount"], 0)
        damage, log = self.damage_steps(mon(METAPOD, (G,), prevent_damage=TURN - 1))
        self.assertEqual(damage, [])
        self.assertIn("damage_prevented", log)

    def test_transparency_is_still_judged(self):
        """相手のゴーストの「とうめい」は判定する（特殊能力を無視するワザではない）。「おもて」なら受けない。"""
        state = board(mon(FOSSIL_MAGNETON), mon(HAUNTER, (P,)))
        evaded = attack(state, 0, H)
        self.assertEqual(kinds(evaded, len(state.log))[1:4], ["coin_flip", "evade_check", "attack_evaded"])
        hit = attack(state, 0, T)
        self.assertEqual(opponent_damage(hit, len(state.log)), [20])


class SparkTest(unittest.TestCase):
    """スパーク（第2弾のピカチュウ）: 相手の対戦ポケモンに 20 → 相手の控えを 1 匹選んで 10。説明に弱点・抵抗力の記述がないので、選んだ控えで計算するかどうかで
    結果が変わるときだけ JS1。"""

    def test_chooser_options_and_amounts(self):
        """選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。1 匹ちょうど）、選べるものは相手の控えの全員。対戦ポケモンへの 20 のあと、選んだ控えに 10。"""
        state = board(mon(JUNGLE_PIKACHU), opponent_bench=(RATTATA, PIKACHU))
        after = attack(state, 0)
        d = after.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices),
                         (SELECT_POKEMON, 0, tuple(p.pokemon_id for p in after.players[1].bench), 1, 1))
        self.assertIsNone(d.context_value("unresolved_choices"))
        pikachu = pid_of(after, 1, PIKACHU)
        done = apply_kernel(after, ResolveDecision(0, d.id, (pikachu,)))
        since = len(state.log)
        self.assertEqual(opponent_damage(done, since), [20])
        self.assertEqual(damage_of(done, since, "opponent_bench"), {pikachu: 10})

    def test_js1_only_for_the_choices_whose_result_differs(self):
        """雷に弱点のゼニガメは選べるが、選ぶと JS1（決定は待ったまま。状態・乱数・ログは変わらない）。ほかの控え（コラッタ）を選べば処理する。"""
        state = board(mon(JUNGLE_PIKACHU), opponent_bench=(RATTATA, SQUIRTLE))
        after = attack(state, 0)
        d = after.decision
        squirtle, rattata = pid_of(after, 1, SQUIRTLE), pid_of(after, 1, RATTATA)
        self.assertEqual(d.context_value("unresolved_choices"), (squirtle,))
        assert_rejected(self, after, ResolveDecision(0, d.id, (squirtle,)), "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE", UnsupportedError)
        done = apply_kernel(after, ResolveDecision(0, d.id, (rattata,)))
        self.assertEqual(damage_of(done, len(state.log), "opponent_bench"), {rattata: 10})

    def test_every_choice_differs_stops_before_the_declaration(self):
        """選べるどの控えでも結果が変わるなら（控えがゼニガメ・サンドだけ）、宣言の前に止める（どの先読みの方法でも）。"""
        assert_stops(self, board(mon(JUNGLE_PIKACHU), opponent_bench=(SQUIRTLE, SANDSHREW)), UseAttack(0, 0), "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE")

    def test_without_opponent_bench_only_the_active_takes_damage(self):
        """相手に控えがいなければ「この効果はない」: 決定を出さず、対戦ポケモンへの 20 だけ。"""
        state = board(mon(JUNGLE_PIKACHU), opponent_bench=())
        done = attack(state, 0)
        self.assertIsNone(done.decision)
        self.assertEqual(opponent_damage(done, len(state.log)), [20])

    def test_invalid_answers_are_rejected(self):
        """0 匹・2 匹・控えでないポケモン・相手でないプレイヤーの答えは拒否し、状態・乱数・ログは変わらない。"""
        after = attack(board(mon(JUNGLE_PIKACHU), opponent_bench=(RATTATA, PIKACHU)), 0)
        d = after.decision
        assert_rejected(self, after, ResolveDecision(0, d.id, ()), "INVALID_CHOICE_COUNT", IllegalActionError)
        assert_rejected(self, after, ResolveDecision(0, d.id, d.options), "INVALID_CHOICE_COUNT", IllegalActionError)
        assert_rejected(self, after, ResolveDecision(0, d.id, (after.players[0].active.pokemon_id,)), "INVALID_CHOICE", IllegalActionError)
        assert_rejected(self, after, ResolveDecision(1, d.id, first(d)), "NOT_YOUR_DECISION", IllegalActionError)


class GigaSparkTest(unittest.TestCase):
    """ギガスパーク（化石の秘密のライチュウ）: 相手の対戦ポケモンに 30 → 相手の控えから最大 3 匹を選び、弱点・抵抗力に関係なく 10 ずつ。0 匹は GS1。"""

    def waiting(self, opponent_bench=(RATTATA, SQUIRTLE, PIKACHU, BULBASAUR), opponent=None):
        state = board(mon(FOSSIL_RAICHU), opponent, opponent_bench=opponent_bench)
        return state, attack(state, 0)

    def test_decision_shape(self):
        """選ぶのはワザを使ったプレイヤー、選べるものは相手の控えの全員、選ぶ数は 0〜min(3, 控えの数)。対戦ポケモンへの 30 は決定の前にすんでいる。"""
        for bench, maximum in (((RATTATA, SQUIRTLE, PIKACHU, BULBASAUR), 3), ((RATTATA, SQUIRTLE, PIKACHU), 3), ((RATTATA, SQUIRTLE), 2), ((RATTATA,), 1)):
            with self.subTest(bench=len(bench)):
                state, after = self.waiting(bench)
                d = after.decision
                self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices),
                                 (SELECT_POKEMON, 0, tuple(p.pokemon_id for p in after.players[1].bench), 0, maximum))
                self.assertEqual(opponent_damage(after, len(state.log)), [30])
                self.assertEqual(check_invariants(after), [])

    def test_one_two_or_three_targets(self):
        """1・2・3 匹を選べる（説明の「最大」）。選んだ控えだけが 10 を受ける（雷に弱点のゼニガメも 10。弱点・抵抗力に関係なく）。答えの並びの順に受ける。"""
        _, after = self.waiting()
        d = after.decision
        squirtle = pid_of(after, 1, SQUIRTLE)
        for count in (1, 2, 3):
            with self.subTest(count=count):
                choice = tuple(reversed(d.options))[:count]
                done = apply_kernel(after, ResolveDecision(0, d.id, choice))
                bench = [(e["pokemon_id"], e["amount"]) for e in events(done, len(after.log), "damage")]
                self.assertEqual(bench, [(c, 10) for c in choice])
                self.assertEqual(check_invariants(done), [])
        done = apply_kernel(after, ResolveDecision(0, d.id, (squirtle,)))
        self.assertEqual(damage_of(done, len(after.log), "opponent_bench"), {squirtle: 10})

    def test_zero_targets_is_gs1_and_the_decision_waits(self):
        """0 匹の答えは GS1（``UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE``）で止め、状態・乱数・ログは変わらない（決定は待ったまま。1 匹以上を選び直せる）。H4・ER9 と
        同じ止め方の別の問い。"""
        _, after = self.waiting()
        d = after.decision
        assert_rejected(self, after, ResolveDecision(0, d.id, ()), "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE", UnsupportedError)
        done = apply_kernel(after, ResolveDecision(0, d.id, first(d)))
        self.assertIsNone(done.decision)

    def test_invalid_answers_are_rejected(self):
        """同じポケモンを 2 回・4 匹・控えでないポケモン・相手のプレイヤーの答えは拒否する（状態は変わらない）。"""
        _, after = self.waiting()
        d = after.decision
        assert_rejected(self, after, ResolveDecision(0, d.id, (d.options[0], d.options[0])), "DUPLICATE_CHOICE", IllegalActionError)
        assert_rejected(self, after, ResolveDecision(0, d.id, d.options), "INVALID_CHOICE_COUNT", IllegalActionError)
        assert_rejected(self, after, ResolveDecision(0, d.id, (999,)), "INVALID_CHOICE", IllegalActionError)
        assert_rejected(self, after, ResolveDecision(1, d.id, first(d)), "NOT_YOUR_DECISION", IllegalActionError)

    def test_without_opponent_bench_there_is_no_decision(self):
        """相手に控えがいなければ、処理の対象がないので決定を出さない（p.309）。GS1 は起こらない。"""
        state, after = self.waiting(())
        self.assertIsNone(after.decision)
        self.assertEqual(opponent_damage(after, len(state.log)), [30])

    def test_each_choice_is_checked_separately_in_the_preflight(self):
        """選ぶ控えで結果が違えば、先読みは同じものとみなさない: 控えのカイリキー（HP 100・ダメージ 90）を選ぶと、カイリキーがきぜつし、「はんげき」の 10 で
        ライチュウ（HP 90・ダメージ 80）もきぜつしうる（C18）ので、宣言の前に止める。カイリキーのいない控えなら止めない。"""
        machamp = {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE], "damage": 90}
        state = board(mon(FOSSIL_RAICHU, damage=80), opponent_bench=(RATTATA, machamp))
        assert_stops(self, state, UseAttack(0, 0), "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")
        fine = board(mon(FOSSIL_RAICHU, damage=80), opponent_bench=(RATTATA, PIKACHU))
        self.assertEqual(attack(fine, 0).decision.kind, SELECT_POKEMON)

    def test_counterattack_from_a_chosen_bench_machamp_follows_the_bench_damage(self):
        """控えのカイリキーを選ぶと、「はんげき」は控えへのダメージ（決定のあと）のあとに処理する（v0.34 の続きの情報で運ぶ）。"""
        machamp = {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE]}
        state = board(mon(FOSSIL_RAICHU), opponent_bench=(RATTATA, machamp))
        after = attack(state, 0)
        done = apply_kernel(after, ResolveDecision(0, after.decision.id, (pid_of(after, 1, MACHAMP),)))
        order = [k for k in kinds(done, len(state.log)) if k in ("damage", "counterattack")]
        self.assertEqual(order, ["damage", "damage", "counterattack"])
        self.assertEqual(done.players[0].active.damage, 10)

    def test_save_and_restore_at_the_decision(self):
        """決定を待つ状態を pickle でもどしてから答えても、同じ結果。"""
        _, after = self.waiting()
        restored = pickle.loads(pickle.dumps(after))
        self.assertEqual(full(restored), full(after))
        a = apply_kernel(after, ResolveDecision(0, after.decision.id, after.decision.options[:2]))
        b = apply_kernel(restored, ResolveDecision(0, restored.decision.id, restored.decision.options[:2]))
        self.assertEqual(snapshot(a), snapshot(b))


class TypeFilteredBenchTest(unittest.TestCase):
    """ビリビリ（マルマイン。相手の対戦ポケモンと同じタイプの控え全員。お互い）とウォーターリング（カスミのニョロボン。「水」以外の控え全員。お互い）。タイプは
    その時点のいちばん上のカードのタイプ。"""

    def test_thunder_jolt_hits_same_type_bench_on_both_sides(self):
        """相手の対戦ポケモンが闘（エビワラー）なら、お互いの控えの闘ポケモンだけに 10（ワンリキー）。コラッタ・ピカチュウは受けない。弱点・抵抗力の記述がない
        （JS1）が、ワンリキーは雷に弱点・抵抗力を持たないので止めない。"""
        state = board(mon(ELECTRODE), bench=(MACHOP, RATTATA), opponent_bench=(MACHOP, PIKACHU))
        done = attack(state, 1)
        since = len(state.log)
        self.assertEqual(damage_of(done, since, "opponent_bench"), {pid_of(done, 1, MACHOP): 10})
        self.assertEqual(damage_of(done, since, "self_bench"), {pid_of(done, 0, MACHOP): 10})

    def test_type_is_the_current_top_card_type(self):
        """相手の対戦ポケモンが進化していれば、いちばん上のカードのタイプ（カイリキーなら闘）。ワザのダメージで HP 以上になっても、きぜつの処理の前なので、その
        ポケモンのタイプで決める。進化した控えのポケモンも、いちばん上のカードのタイプで選ぶ。"""
        state = board(mon(ELECTRODE), mon(MACHAMP, (F,), damage=90, sleep=True), bench=({"card": NIDOKING, "evolved_from": [NIDORAN_M, NIDORINO]},),
                      opponent_bench=(MACHOP, {"card": MACHOKE, "evolved_from": MACHOP}, PIKACHU))
        done = attack(state, 1)
        since = len(state.log)
        self.assertEqual(sorted(damage_of(done, since, "opponent_bench")), sorted([pid_of(done, 1, MACHOP), pid_of(done, 1, MACHOKE)]))
        self.assertEqual(damage_of(done, since, "self_bench"), {})
        self.assertIn("knock_out", kinds(done, since))

    def test_thunder_jolt_js1(self):
        """相手の対戦ポケモンが水（ゼニガメ）で、同じタイプの控えに雷に弱点のゼニガメがいれば JS1（宣言の前）。相手の対戦ポケモンが闘で、控えに雷に抵抗力の
        ディグダ（闘）がいても JS1（自分の控えでも同じ）。同じタイプの控えがいなければ何もしない。"""
        assert_stops(self, board(mon(ELECTRODE), mon(SQUIRTLE, (W,)), opponent_bench=(SQUIRTLE,)), UseAttack(0, 1),
                     "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE")
        assert_stops(self, board(mon(ELECTRODE), opponent_bench=(MACHOP, DIGLETT)), UseAttack(0, 1), "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE")
        assert_stops(self, board(mon(ELECTRODE), bench=(DIGLETT,), opponent_bench=()), UseAttack(0, 1), "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE")
        state = board(mon(ELECTRODE), mon(SQUIRTLE, (W,)), bench=(PIKACHU,), opponent_bench=(RATTATA,))
        done = attack(state, 1)
        self.assertEqual([e.get("target") for e in events(done, len(state.log), "damage")], [None])

    def test_water_ring_hits_every_non_water_bench(self):
        """ウォーターリング: お互いの控えの「水」以外のポケモンに、弱点・抵抗力に関係なく 10。水のポケモン（ゼニガメ・カスミのニョロモ）は受けない。
        相手の対戦ポケモンへの 30 は弱点を計算する。"""
        state = board(mon(MISTYS_POLIWRATH), mon(SQUIRTLE, (W,)), bench=(SQUIRTLE, BULBASAUR), opponent_bench=(MISTYS_POLIWAG, RATTATA, POLIWAG))
        done = attack(state, 0)
        since = len(state.log)
        self.assertEqual(opponent_damage(done, since), [30])
        self.assertEqual(damage_of(done, since, "opponent_bench"), {pid_of(done, 1, RATTATA): 10})
        self.assertEqual(damage_of(done, since, "self_bench"), {pid_of(done, 0, BULBASAUR): 10})


class FartGasTest(unittest.TestCase):
    """おならガス（キョウのドガース PMCG6-008）: 1 枚のコイン。「おもて」なら、お互いの控え全員に弱点・抵抗力に関係なく 10。"""

    def test_heads_both_benches_tails_none(self):
        state = board(mon(KOGAS_KOFFING_40), bench=(RATTATA, SQUIRTLE), opponent_bench=(PIKACHU,))
        since = len(state.log)
        heads = attack(state, 0, H)
        self.assertEqual(coins(heads, since), ["heads"])
        self.assertEqual(sorted(damage_of(heads, since, "self_bench").values()), [10, 10])
        self.assertEqual(list(damage_of(heads, since, "opponent_bench").values()), [10])
        tails = attack(state, 0, T)
        self.assertEqual([e.get("target") for e in events(tails, since, "damage")], [None])
        self.assertEqual(opponent_damage(heads, since), opponent_damage(tails, since))

    def test_no_coin_without_any_bench(self):
        """お互いに控えがいなければ、コインが決める要素に処理の対象がないので投げない（v0.38 の ``has_target``）。どちらかにいれば投げる。"""
        state = board(mon(KOGAS_KOFFING_40), bench=(), opponent_bench=())
        done = attack(state, 0)
        self.assertEqual(coins(done, len(state.log)), [])
        self.assertEqual(opponent_damage(done, len(state.log)), [10])
        own_only = board(mon(KOGAS_KOFFING_40), bench=(RATTATA,), opponent_bench=())
        self.assertEqual(coins(attack(own_only, 0, H), len(own_only.log)), ["heads"])


class CountDamageTest(unittest.TestCase):
    """場のポケモンの数でダメージが決まるワザ（p.321 の 1 段階の基本となるダメージ）。数えるのは場のポケモン（進化して重なったカードは 1 匹）で、名前は
    いちばん上のカードの名前の完全一致。"""

    def test_magnemite_chain_counts_only_the_named_bench_pokemon(self):
        """ちょくれつじりょく: 自分のベンチの「コイル」（第1弾・ロケット団）と「レアコイル」（進化したもの。1 匹）を数え、マチスのコイル（名前が違う）・コラッタ・
        相手のベンチのコイル・バトル場のこのカードは数えない。10 + 3 × 10 = 40。"""
        state = board(mon(ROCKET_MAGNEMITE), bench=(MAGNEMITE, {"card": MAGNETON, "evolved_from": MAGNEMITE}, ROCKET_MAGNEMITE, LT_SURGES_MAGNEMITE, RATTATA),
                      opponent_bench=(MAGNEMITE,))
        self.assertEqual(opponent_damage(attack(state, 1), len(state.log)), [40])
        alone = board(mon(ROCKET_MAGNEMITE), bench=(LT_SURGES_MAGNEMITE,))
        self.assertEqual(opponent_damage(attack(alone, 1), len(alone.log)), [10])

    def test_friendship_ring_counts_every_own_bench_pokemon(self):
        """ともだちのわ: 自分の控えポケモンの数 × 10（0〜5 匹）。相手の控えは数えない。"""
        for bench in ((), (RATTATA,), (RATTATA, PIKACHU, BULBASAUR), (RATTATA, PIKACHU, BULBASAUR, SQUIRTLE, MACHOP)):
            with self.subTest(bench=len(bench)):
                state = board(mon(WIGGLYTUFF), bench=bench, opponent_bench=(RATTATA, PIKACHU))
                self.assertEqual(opponent_damage(attack(state, 1), len(state.log)), [10 + 10 * len(bench)])

    def test_lovely_attack_counts_own_nidoking_in_play(self):
        """ラブラブアタック: 自分の場（バトル場とベンチ）の「ニドキング」の数 × 20。ニドリーノ・相手のニドキングは数えない。ニドクイン自身は名前が違う。"""
        nidoking = {"card": NIDOKING, "evolved_from": [NIDORAN_M, NIDORINO]}
        state = board(mon(NIDOQUEEN), mon(NIDOKING, (G,)), bench=(nidoking, nidoking, {"card": NIDORINO, "evolved_from": NIDORAN_M}),
                      opponent_bench=(nidoking,))
        self.assertEqual(opponent_damage(attack(state, 0), len(state.log)), [60])
        none = board(mon(NIDOQUEEN), mon(NIDOKING, (G,)), bench=(RATTATA,))
        self.assertEqual(opponent_damage(attack(none, 0), len(none.log)), [20])

    def test_count_is_the_base_damage_before_weakness_and_pluspower(self):
        """数えた値は基本となるダメージ（1 段階）で、弱点（3 段階）・プラスパワー（5 段階）はそのあと: 雷に弱点のゼニガメに (10 + 20) × 2 = 60、プラスパワーで 70。"""
        state = board(mon(ROCKET_MAGNEMITE, trainers=[(PLUSPOWER, TURN)]), mon(SQUIRTLE, (W,)), bench=(MAGNEMITE, ROCKET_MAGNEMITE))
        [damage] = events(attack(state, 1), len(state.log), "damage")
        self.assertEqual(damage["amount"], 70)
        self.assertEqual([s[1] for s in damage["steps"]], [30, 60, 70])

    def test_preflight_uses_the_same_count(self):
        """先読み（C18）も同じ数で求める: 控え 3 匹のともだちのわ（40）は、相手のカイリキー（ダメージ 60）をきぜつさせ、「はんげき」でプクリン（ダメージ 70）も
        きぜつしうるので止める。控え 2 匹（30）ならカイリキーはきぜつしないので止めない。"""
        machamp = mon(MACHAMP, (F,), damage=60)
        assert_stops(self, board(mon(WIGGLYTUFF, damage=70), machamp, bench=(RATTATA, PIKACHU, BULBASAUR)), UseAttack(0, 1),
                     "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")
        state = board(mon(WIGGLYTUFF, damage=70), machamp, bench=(RATTATA, PIKACHU))
        self.assertEqual(opponent_damage(attack(state, 1), len(state.log)), [30])


class SuddenExplosionTest(unittest.TestCase):
    """とつぜんばくはつ（キョウのマタドガス）: 1 枚のコインで、「おもて」なら 30 を追加して自分にも 30（要素ごとに投げ直さない）。"""

    def test_heads_and_tails(self):
        state = board(mon(KOGAS_WEEZING))
        since = len(state.log)
        heads = attack(state, 0, H)
        self.assertEqual(coins(heads, since), ["heads"])
        self.assertEqual([(e.get("target"), e["amount"]) for e in events(heads, since, "damage")], [(None, 40), ("self", 30)])
        tails = attack(state, 0, T)
        self.assertEqual(coins(tails, since), ["tails"])
        self.assertEqual([(e.get("target"), e["amount"]) for e in events(tails, since, "damage")], [(None, 10)])

    def test_prevented_opponent_still_flips_for_the_self_damage(self):
        """相手が「ダメージを受けない」状態でも、コインは自分へのダメージ（有効な要素）も決めるので投げる（v0.34 の ``void_coin_question``）。"""
        state = board(mon(KOGAS_WEEZING), mon(METAPOD, (G,), prevent_damage=TURN - 1))
        done = attack(state, 0, H)
        since = len(state.log)
        self.assertEqual(coins(done, since), ["heads"])
        self.assertEqual([e.get("target") for e in events(done, since, "damage")], ["self"])

    def test_counterattack_after_both_damage_elements(self):
        """相手のカイリキーの「はんげき」は、自分への 30 のあと（ダメージの処理をすべてのせたあと）。"""
        state = board(mon(KOGAS_WEEZING), mon(MACHAMP, (F,)))
        done = attack(state, 0, H)
        order = [k for k in kinds(done, len(state.log)) if k in ("damage", "counterattack")]
        self.assertEqual(order, ["damage", "damage", "counterattack"])
        self.assertEqual(done.players[0].active.damage, 40)


class ToxicGasTest(unittest.TestCase):
    """どくどくガス（キョウのマタドガス）: 20 のあとコインで「おもて」なら、ポケモンチェックで 20 を受ける特殊などく（v0.3a。``Poison(20)``。通常のどくを 2 回に
    しない）。"""

    def test_heads_special_poison_and_pokemon_check(self):
        """「おもて」ならどく状態の量は 20（ワザのあとのポケモンチェックで 20 を受ける）。どく状態にするのは 1 回。「うら」ならどくにしない。"""
        state = board(mon(KOGAS_WEEZING))
        done = attack(state, 1, H)
        self.assertEqual(done.players[1].active.conditions.poison.damage, 20)
        self.assertEqual(len(events(done, len(state.log), "special_condition")), 1)
        check = [e["amount"] for e in events(done, len(state.log), "poison_damage")]
        self.assertEqual(check, [20])
        tails = attack(state, 1, T)
        self.assertIsNone(tails.players[1].active.conditions.poison)

    def test_tp3_and_hc3_are_reused(self):
        """通常のどく状態のポケモンへは v0.34 の TP3（``UNRESOLVED_SPECIAL_POISON_OVERWRITE``）、「ワザをうけない」状態（バリアー）へは v0.31 の HC3 で、コインの前に
        止める。"""
        assert_stops(self, board(mon(KOGAS_WEEZING), mon(HITMONCHAN, (F, F), poison=10)), UseAttack(0, 1), "UNRESOLVED_SPECIAL_POISON_OVERWRITE")
        from tests.test_barrier_resume_coin_bonus_v0_34 import with_barrier

        assert_stops(self, with_barrier(mon(KOGAS_WEEZING)), UseAttack(1, 1), "UNRESOLVED_PREVENTED_EFFECT_COIN")


class DangerousSporeTest(unittest.TestCase):
    """きけんなほうし（エリカのパラス）: 1 枚のコインで、「おもて」なら相手の控え全員に弱点・抵抗力に関係なく 10、相手の対戦ポケモンをどく（ダメージのあとに効果。
    p.309 の手順 6）。"""

    def test_heads_bench_then_poison_tails_nothing(self):
        state = board(mon(ERIKAS_PARAS), opponent_bench=(RATTATA, BULBASAUR))
        since = len(state.log)
        heads = attack(state, 1, H)
        self.assertEqual(coins(heads, since), ["heads"])
        log = [k for k in kinds(heads, since) if k in ("damage", "special_condition")]
        self.assertEqual(log, ["damage", "damage", "special_condition"])
        self.assertEqual(heads.players[1].active.conditions.poison.damage, 10)
        tails = attack(state, 1, T)
        self.assertEqual([k for k in kinds(tails, since) if k in ("damage", "special_condition")], [])

    def test_one_side_without_target_or_void(self):
        """控えがいなくても、どくに処理の対象があるのでコインを投げ、「おもて」ならどくだけ。相手がバリアーでも、控えへのダメージ（有効）があるので投げ、控えに 10、
        どくは受けない。相手が「ダメージを受けない」状態でも、どく（ダメージ以外の効果）は受ける。バリアーで控えもいなければ HC3。"""
        from tests.test_barrier_resume_coin_bonus_v0_34 import with_barrier

        alone = board(mon(ERIKAS_PARAS), opponent_bench=())
        done = attack(alone, 1, H)
        self.assertEqual(coins(done, len(alone.log)), ["heads"])
        self.assertEqual(events(done, len(alone.log), "damage"), [])
        self.assertIsNotNone(done.players[1].active.conditions.poison)
        barrier = with_barrier(mon(ERIKAS_PARAS))
        hit = play(with_coin_results(barrier, H), UseAttack(1, 1))
        since = len(barrier.log)
        self.assertEqual(coins(hit, since), ["heads"])
        self.assertEqual([e.get("target") for e in events(hit, since, "damage")], ["opponent_bench"])
        self.assertIsNone(hit.players[0].active.conditions.poison)
        prevented = board(mon(ERIKAS_PARAS), mon(METAPOD, (G,), prevent_damage=TURN - 1))
        self.assertIsNotNone(attack(prevented, 1, H).players[1].active.conditions.poison)
        lonely = build_test_state([{"active": {"card": MEWTWO, "energy": [P, P, P]}, "bench": []},
                                   {"active": mon(ERIKAS_PARAS), "bench": [RATTATA]}], turn_number=TURN)
        lonely = play(lonely, UseAttack(0, 1), [first])
        assert_stops(self, lonely, UseAttack(1, 1), "UNRESOLVED_PREVENTED_EFFECT_COIN")


class GustTest(unittest.TestCase):
    """かぜおこし（ポッポ）: 10 のあと、相手が選ぶ控えと入れ替える（v0.4d のふきとばしと同じ処理。写しのワザの名前は「かぜおこし」、サイトは「ふきとばし」）。"""

    def test_opponent_chooses_and_no_bench_is_damage_only(self):
        state = board(mon(PIDGEY), opponent_bench=(RATTATA, PIKACHU))
        after = attack(state, 0)
        d = after.decision
        self.assertEqual((d.kind, d.player, d.options), (FORCED_SWITCH, 1, tuple(p.pokemon_id for p in after.players[1].bench)))
        done = apply_kernel(after, ResolveDecision(1, d.id, (d.options[1],)))
        self.assertEqual(done.players[1].active.pokemon_id, d.options[1])
        self.assertIn("forced_switch", kinds(done, len(state.log)))
        alone = board(mon(PIDGEY), opponent_bench=())
        lone = attack(alone, 0)
        self.assertIsNone(lone.decision)
        self.assertEqual(opponent_damage(lone, len(alone.log)), [10])
        self.assertIn("forced_switch_skipped", kinds(lone, len(alone.log)))


class CopyTest(unittest.TestCase):
    """相手のワザを自分のワザとして使う効果（ピクシー・ピッピの「ゆびをふる」・カスミのコダックの「ちょうのうりょく」）での v0.39 のワザ。"""

    # まねるポケモン → (エネルギー, まねるワザの位置, まねる前に投げるコイン)
    COPIERS: ClassVar[dict] = {CLEFABLE: ((P,), 0, ()), CLEFAIRY: ((P, P, P), 1, ()), MISTYS_PSYDUCK: ((P,), 0, (H, H, H))}

    def copier(self, card, target, *, bench=(RATTATA,), opponent_bench=(RATTATA,)):
        energy = self.COPIERS[card][0]
        return board(mon(card, energy), mon(target, ()), bench=bench, opponent_bench=opponent_bench)

    def test_every_attack_can_be_copied_without_internal_errors(self):
        """25 のワザのどれをまねても、エンジンの内部のエラーにならない（処理するか、決まったコードで拒否する）。まねたワザの処理のあとも不変条件が通る。"""
        for (card, index) in EXPECTED:
            for copier, (energy, attack_index, sides) in self.COPIERS.items():
                with self.subTest(card=card, index=index, copier=copier):
                    state = self.copier(copier, card, bench=(RATTATA, PIKACHU), opponent_bench=(RATTATA, BULBASAUR))
                    try:
                        current = play(with_coin_results(state, *sides, H, H, H), UseAttack(0, attack_index), [])
                        if current.decision is not None and current.decision.kind == SELECT_ATTACK:
                            self.assertIn(index, current.decision.options)
                            current = apply_kernel(current, ResolveDecision(0, current.decision.id, (index,)))
                        while current.decision is not None and current.decision.resume == "attack":
                            d = current.decision
                            current = apply_kernel(current, ResolveDecision(d.player, d.id, first(d)))
                    except EngineError as error:
                        self.assertTrue(error.code.startswith(("UNRESOLVED_", "UNSUPPORTED_")), error.code)
                        continue
                    self.assertEqual(check_invariants(current), [])

    def test_self_destruct_copied_hurts_the_copier(self):
        """ピクシーがじばくをまねると、自分へのダメージ・自分の控えへのダメージはまねたポケモンの側。ピクシー（HP 70）は 40 を受けて残る（自分へのダメージは
        計算した量で、自分をきぜつさせる処理ではない）。"""
        state = self.copier(CLEFABLE, MAGNEMITE, bench=(RATTATA,), opponent_bench=(RATTATA,))
        done = play(state, UseAttack(0, 0), [(1,)])
        since = len(state.log)
        clefable = done.players[0].active
        self.assertEqual(damage_of(done, since, "self"), {clefable.pokemon_id: 40})
        self.assertEqual(list(damage_of(done, since, "self_bench")), [pid_of(done, 0, RATTATA)])
        self.assertEqual(clefable.damage, 40)

    def test_counts_are_taken_on_the_copier_side(self):
        """ピクシーがちょくれつじりょくをまねると、数えるのはピクシーの側のベンチのコイル（自分のベンチ）。"""
        state = self.copier(CLEFABLE, ROCKET_MAGNEMITE, bench=(MAGNEMITE, MAGNEMITE), opponent_bench=(MAGNEMITE,))
        done = play(state, UseAttack(0, 0), [(1,)])
        self.assertEqual(opponent_damage(done, len(state.log)), [30])

    def test_giga_spark_copied_keeps_gs1(self):
        """ギガスパークをまねても、0 匹の答えは GS1。"""
        state = self.copier(CLEFABLE, FOSSIL_RAICHU, opponent_bench=(RATTATA, PIKACHU))
        after = play(state, UseAttack(0, 0), [(0,)])
        d = after.decision
        self.assertEqual((d.kind, d.max_choices), (SELECT_POKEMON, 2))
        assert_rejected(self, after, ResolveDecision(0, d.id, ()), "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE", UnsupportedError)


class IntegrityTest(unittest.TestCase):
    """不変条件・書き出し・拒否で状態が変わらないこと・渡した状態を変えないこと。"""

    CASES = (
        (MAGNEMITE, 0, (H,), ()), (MAGNEMITE, 1, (), ()), (MAGNETON, 0, (H,), ()), (MAGNETON, 1, (), ()), (FOSSIL_WEEZING, 0, (H,), ()),
        (FOSSIL_WEEZING, 1, (), ()), (FOSSIL_MAGNETON, 0, (), ()), (FOSSIL_MAGNETON, 1, (), ()), (JUNGLE_PIKACHU, 0, (), (first,)),
        (FOSSIL_RAICHU, 0, (), (first,)), (ELECTRODE, 0, (), ()), (ELECTRODE, 1, (), ()), (KOGAS_KOFFING_40, 0, (H,), ()),
        (MISTYS_POLIWRATH, 0, (), ()), (ROCKET_MAGNEMITE, 0, (), ()), (ROCKET_MAGNEMITE, 1, (), ()), (WIGGLYTUFF, 0, (), ()), (WIGGLYTUFF, 1, (), ()),
        (NIDOQUEEN, 0, (), ()), (NIDOQUEEN, 1, (), ()), (KOGAS_WEEZING, 0, (H,), ()), (KOGAS_WEEZING, 1, (H,), ()), (PIDGEY, 0, (), (first,)),
        (ERIKAS_PARAS, 0, (), ()), (ERIKAS_PARAS, 1, (H,), ()),
    )

    def test_cases_cover_every_attack(self):
        self.assertEqual(sorted((card, index) for card, index, _, _ in self.CASES), sorted(EXPECTED))

    def test_every_step_keeps_invariants_and_does_not_mutate_the_input(self):
        """どのワザも、途中の決定ごとに不変条件が通り、書き出し（形式 10）と pickle で同じ状態にもどる。``apply_command`` は渡した状態を変えない。"""
        for card, index, sides, answers in self.CASES:
            with self.subTest(card=card, index=index):
                state = board(mon(card), bench=(RATTATA, MAGNEMITE), opponent_bench=(RATTATA, PIKACHU))
                before = copy.deepcopy(full(state))
                current = apply_kernel(with_coin_results(state, *sides), UseAttack(0, index))
                self.assertEqual(full(state), before)
                for answer in answers:
                    self.assertEqual(check_invariants(current), [])
                    self.assertEqual(full(pickle.loads(pickle.dumps(current))), full(current))
                    d = current.decision
                    current = apply_kernel(current, ResolveDecision(d.player, d.id, answer(d)))
                self.assertEqual(check_invariants(current), [])
                self.assertTrue(current.decision is None or current.decision.resume != "attack")

    def test_rejections_keep_the_state(self):
        """拒否（JS1・GS1・TP3）で状態・乱数・ログが変わらない。"""
        assert_rejected(self, board(mon(MAGNEMITE), opponent_bench=(SQUIRTLE,)), UseAttack(0, 1), "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE",
                        UnsupportedError)
        after = attack(board(mon(FOSSIL_RAICHU)), 0)
        assert_rejected(self, after, ResolveDecision(0, after.decision.id, ()), "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE", UnsupportedError)
        assert_rejected(self, board(mon(KOGAS_WEEZING), mon(HITMONCHAN, (F, F), poison=10)), UseAttack(0, 1), "UNRESOLVED_SPECIAL_POISON_OVERWRITE",
                        UnsupportedError)


class PreflightParityTest(unittest.TestCase):
    """先読みの方法（derived・derived_full・legacy）によらず、同じコインの結果で同じ結果になる（v0.39 の型はどれも ``VERIFIED`` に入れていないので、legacy も
    すべての結果を試す方法）。"""

    def test_same_result_in_every_mode(self):
        for card, index, sides, answers in IntegrityTest.CASES:
            with self.subTest(card=card, index=index):
                state = board(mon(card), mon(MACHAMP, (F,), sleep=True), bench=(RATTATA, MAGNEMITE), opponent_bench=(RATTATA, PIKACHU))
                results = set()
                for mode in PREFLIGHT_MODES:
                    done = play(with_coin_results(state, *sides), UseAttack(0, index), answers, mode=mode)
                    results.add(repr(snapshot(done)))
                self.assertEqual(len(results), 1)

    def test_coin_count_matches_the_text(self):
        """要素ごとにコインを投げ直さない: でんじは・スモッグ・おならガス・とつぜんばくはつ・どくどくガス・きけんなほうしのコインは 1 枚。"""
        for card, index, sides, answers in IntegrityTest.CASES:
            if not sides:
                continue
            with self.subTest(card=card, index=index):
                state = board(mon(card), opponent_bench=(RATTATA, PIKACHU))
                done = play(with_coin_results(state, *sides), UseAttack(0, index), answers)
                self.assertEqual(len([e for e in events(done, len(state.log), "coin_flip") if e["source"] == "attack"]), 1)


class DocumentTest(unittest.TestCase):
    def test_document_records_the_decisions(self):
        """文書に、カードごとの結果・GS1 の根拠と影響の範囲・JS1 の再利用・第1弾と第3弾のじばくの違い・ソニックブームの範囲・照合の違いを書いた。"""
        text = DOC.read_text(encoding="utf-8")
        for needle in ("GS1", "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE", "JS1", "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE", "GK1", "TP3", "HC3",
                       "ソニックブーム", "ともだちのわ", "かぜおこし", "ふきとばし", "抵抗カ", "pcg-search.com", "CR-COUNTERATTACK-TIMING"):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
