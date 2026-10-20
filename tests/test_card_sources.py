"""2026-10-15 からのカードデータの方針（docs/card-data-policy.md）の記録 kyuura_engine/data/card_sources.json と、その検査
scripts/check_card_sources.py。

kyuura の data/cards.json を基本データとして採用したカード（``basis: kyuura_data``）は、ガイドブック（『オフィシャルブック2000』）の
ページ・画像の照合の記録がなくても登録できる。過去の原典照合の記録（card_verification.json）は履歴として残し、ここでは書き換えない。
検査は、新しい方針の記録を受け付け、読んでいない原典を確かめたことにする記録・形の崩れた記録を拒否する。

ここで作る記録（``valid_case``）はテストのための記録で、pcg-search.com を照合した記録ではない（同梱の card_sources.json には入れない）。
過去の原典照合で登録したカードを、写しを変えずに「採用の記録で登録したカード」に見立てる（登録表・照合の記録・研究の対応表の写しを
テストの中だけで変える）。
"""

from __future__ import annotations

import copy
import dataclasses
import datetime
import io
import json
import pathlib
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from kyuura_engine.cards import read_extract, read_verification
from kyuura_engine.effects import DAMAGE_ONLY, DEFAULT_EFFECTS, AttackEntry, AttackKey
from scripts import check_card_sources as cs
from tests.helpers import (
    BASE_HAUNTER,
    BLANK_CHANSEY,
    BROCKS_GEODUDE_40,
    BROCKS_ONIX,
    DARK_BLASTOISE,
    DARK_MAGNETON,
    DARK_MUK,
    DARK_PRIMEAPE,
    ERIKAS_IVYSAUR,
    FOSSIL_GRIMER,
    GIOVANNI,
    IMAKUNI_DODUO,
    KANGASKHAN,
    KOGAS_MUK,
    MISTYS_STARYU,
    MR_MIME,
    NO_BASE_HAUNTER_EFFECTS,
    NO_CHARIZARD_EFFECTS,
    PERSIAN,
    RATICATE,
    ROCKETS_HITMONCHAN,
    SNORLAX,
    V0_29_POKEMON,
    V0_30_POKEMON,
    V0_31_POKEMON,
    V0_32_POKEMON,
    V0_33_POKEMON,
    V0_34_POKEMON,
    V0_35_POKEMON,
    V0_36_POKEMON,
    V0_37_ADOPTED,
    V0_37_POKEMON,
    V0_38_POKEMON,
    V0_39_POKEMON,
    V0_40_POKEMON,
    V0_41_POKEMON,
    V0_42_POKEMON,
    V0_43_POKEMON,
    V0_44_CARDS,
    V0_45_ADOPTED,
    V0_46_POKEMON,
    V0_47_CARDS,
    V0_48_POKEMON,
    V0_49_CARDS,
    V0_50_CARDS,
    V0_51_CARDS,
    V0_52_CARDS,
    V0_53_CARDS,
    V0_54_CARDS,
    V0_55_CARDS,
    V0_56_CARDS,
    V0_57_CARDS,
    V0_58_CARDS,
    V0_59_CARDS,
    V0_60_CARDS,
    V0_61_CARDS,
    V0_62_CARDS,
    V0_63_CARDS,
    V0_64_CARDS,
    V0_65_CARDS,
    V0_66_CARDS,
    V0_67_CARDS,
    V0_69_CARDS,
    V0_70_CARDS,
    V0_71_CARDS,
    V0_72_CARDS,
)

TODAY = datetime.date(2026, 10, 20)
COMMIT = read_extract()["source"]["commit"]
# v0.69: 写しの元を上げた（7d3f4ca）。v0.68 までの同梱の採用の記録は、採用したときのデータのコミット（ecb2d69）のまま（書き換えない。card_sources.json の data_migrations）
ADOPTED_COMMIT = read_extract()["previous_source"]["commit"]
TANGELA = "PMCG1-007"      # モンジャラ: 説明文のあるワザ 2 つ。処理に使う文面は印刷の文面と同じ（kyuura の印刷の文面を根拠にする場面）
BUTTERFREE = "PMCG2-007"   # バタフリー: ワザ 2 つとも kyuura の最新の説明（LD-）がある（LD- を根拠にする場面）
CHARIZARD = "PMCG1-021"    # リザードン: 保留の場面（v0.31 で採用・登録したので、テストの記録の組では登録と研究の対応表の区分から外す）
CHARMANDER = "PMCG1-014"   # ヒトカゲ: 過去の原典照合の記録のあるカード。v0.30 の「ひのこ」の文面の根拠を guidebook_record の play_text に書いた
CHARMELEON = "PMCG1-017"   # リザード: v0.30 の採用の記録。処理に使う文面は kyuura のエラッタ（RUL-ENERGY-DISCARD-ATTACKS。記録の範囲の当てはめ）
RUL = "RUL-ENERGY-DISCARD-ATTACKS"
V0_30_ADOPTED = tuple(card for card in V0_30_POKEMON if card != CHARMANDER)
STARMIE = "PMCG1-026"      # スターミー: 過去の原典照合の記録で登録したカード（外部照合だけを加える場面）
OAK = "PMCG1-077"          # オーキドはかせ: トレーナー（ポケモンの欄を照合できない場面）


def pcg_check(**changes) -> dict:
    check = {
        "site": "pcg-search.com",
        "url": "https://pcg-search.com/card/1st/1st1013.php",
        "checked_on": "2026-10-16",
        "kyuura_commit": COMMIT,
        "edition": {"expansion": "第1弾 拡張パック", "list_number": "013/096"},
        "result": "match",
        "checked_fields": ["name.ja", "pokemon.hp", "pokemon.attacks[0].text.ja", "pokemon.attacks[1].text.ja"],
        "differences": [],
    }
    check.update(changes)
    return check


def valid_case():
    """方針どおりの記録の組: (sources, registry, verification, links)。"""
    verification = copy.deepcopy(read_verification())
    links = copy.deepcopy(cs.load_links())
    # v0.31 でリザードンを採用・登録した。このテストの記録の組では保留の場面に使うので、その登録（エナジーバーン・ほのおのうず）を除いた
    # 登録表（tests/helpers.py の NO_CHARIZARD_EFFECTS）にし、研究の対応表の区分からも外す
    registry = NO_CHARIZARD_EFFECTS
    section = links["latest_descriptions"]
    section["adopted_printed_text"].remove(f"{CHARIZARD}/attack/0")
    del section["errata_text"][f"{CHARIZARD}/power/0"]
    # v0.71: リザードンの再録の版（PR1-030）の登録・記録・研究の対応表の区分も外す（NO_CHARIZARD_EFFECTS は PR1-030 の登録も除く）
    section["adopted_printed_text"].remove("PR1-030/attack/0")
    del section["reprint_registrations"]["PR1-030/power/0"]
    # モンジャラ: 過去の原典照合の記録を外し、出典を kyuura の印刷の文面にした登録にする
    del verification["cards"][TANGELA]
    changed = {}
    for index in (0, 1):
        entry = registry.attack_entry(TANGELA, index)
        changed[AttackKey(TANGELA, index)] = dataclasses.replace(entry, source=cs.PRINTED_TEXT_SOURCE)
        del section["recorded_in_card_checks"][f"{TANGELA}/attack/{index}"]
        section["adopted_printed_text"].append(f"{TANGELA}/attack/{index}")
    # バタフリー: 過去の原典照合の記録を外し、出典を kyuura の最新の説明（LD-）の id にした登録にする
    del verification["cards"][BUTTERFREE]
    for index in (0, 1):
        entry = registry.attack_entry(BUTTERFREE, index)
        changed[AttackKey(BUTTERFREE, index)] = dataclasses.replace(entry, source=f"LD-{BUTTERFREE}-ATK{index}")
    registry = registry.with_attacks("test-card-sources", changed)
    sources = {
        "format": cs.FORMAT,
        "description": "テストのための記録",
        "policy": dict(cs.POLICY),
        "data_migrations": copy.deepcopy(cs.load_sources()["data_migrations"]),
        "cards": {
            **{k: v for k, v in copy.deepcopy(cs.load_sources()["cards"]).items() if k != "PR1-030"},  # 同梱の採用の記録はそのまま（v0.71: PR1-030 を除く）
            TANGELA: {
                "basis": "kyuura_data",
                "name_ja": "モンジャラ",
                "status": "adopted",
                "kyuura_commit": COMMIT,
                "recorded_on": "2026-10-16",
                "kyuura_records": ["CC-PMCG1-007-P55"],
                "play_text": {"attack/0": cs.PRINTED_TEXT, "attack/1": cs.PRINTED_TEXT},
                "external_checks": [
                    pcg_check(),
                    pcg_check(edition={"expansion": "第1弾 スターターパック", "list_number": "013/096"}, result="differences",
                              checked_on="2026-10-17", checked_fields=["pokemon.attacks[0].name.ja"],
                              differences=[{"field": "pokemon.attacks[0].name.ja", "kyuura": "しめつける", "pcg_search": "しめつけ",
                                            "affects_behavior": False}]),
                    pcg_check(edition={"expansion": "拡張シート", "list_number": None}, result="edition_not_listed",
                              url="https://pcg-search.com/card/card_list.php", checked_fields=[], differences=[],
                              note="一覧に対象の版がない"),
                    pcg_check(result="inaccessible", checked_on="2026-10-18", checked_fields=[], differences=[]),
                ],
                "issues": [{"question": "ワザ名の表記の違いは処理に関係しない", "fields": ["pokemon.attacks[0].name.ja"],
                            "affects_behavior": False}],
            },
            BUTTERFREE: {
                "basis": "kyuura_data",
                "name_ja": "バタフリー",
                "status": "adopted",
                "kyuura_commit": COMMIT,
                "recorded_on": "2026-10-16",
                "kyuura_records": ["CC-PMCG2-007-P19", "LD-PMCG2-007-ATK0", "LD-PMCG2-007-ATK1"],
                "play_text": {"attack/0": "LD-PMCG2-007-ATK0", "attack/1": "LD-PMCG2-007-ATK1"},
                "external_checks": [],
                "issues": [],
            },
            CHARIZARD: {
                "basis": "kyuura_data",
                "name_ja": "リザードン",
                "status": "on_hold",
                "kyuura_commit": COMMIT,
                "recorded_on": "2026-10-16",
                "kyuura_records": ["TXT-CHARIZARD"],
                "play_text": {},
                "external_checks": [],
                "issues": [{"question": "ほのおのうずのエネルギーの扱いが資料で食い違う", "fields": ["pokemon.attacks[0].text.ja"],
                            "affects_behavior": True}],
                "notes": "テストのための保留の記録",
            },
            STARMIE: {
                "basis": "guidebook_record",
                "name_ja": "スターミー",
                "external_checks": [pcg_check(url="https://pcg-search.com/card/1st/1st1032.php",
                                              edition={"expansion": "第1弾 拡張パック", "list_number": "032/096"})],
            },
        },
    }
    return sources, registry, verification, links


def run(case) -> list[str]:
    sources, registry, verification, links = case
    return cs.problems(sources, verification=verification, registry=registry, links=links, today=TODAY)


class ShippedRecordTest(unittest.TestCase):
    def test_shipped_records_follow_the_policy(self):
        """同梱の記録は方針と合う。2026-10-14 までに登録したカードは、どれも過去の原典照合の記録で登録した。採用の記録は v0.29 の 14 枚
        （docs/existing-effect-pokemon-v0.29.md）と v0.30 の 4 枚（docs/discard-energy-attacks-v0.30.md）と v0.31 の 29 枚（対象 22 枚・進化元 7 枚。
        docs/held-cards-v0.31.md）と v0.32 の 13 枚（docs/bench-search-counter-drain-v0.32.md）と v0.33 の 15 枚（docs/cd4-opponent-energy-coins-v0.33.md）と v0.34 の 14 枚（docs/barrier-resume-coin-bonus-v0.34.md）と v0.35 の 5 枚と v0.36 の 11 枚（docs/sand-attack-retreat-lock-v0.36.md）と v0.37 の 14 枚（docs/fifteen-reused-effects-v0.37.md）で、どれも pcg-search.com の同じ版のページと照合した（違いは書き方・表記だけで、処理に影響しない）。v0.30 の
        ヒトカゲは過去の原典照合の記録のあるカードで、照合の記録に文面のない「ひのこ」の根拠を guidebook_record の play_text に書いた。"""
        self.assertEqual(cs.problems(), [])
        sources = cs.load_sources()
        self.assertEqual(sources["format"], cs.FORMAT)
        self.assertEqual(sources["policy"]["since"], "2026-10-15")
        # v0.34: 採用 14 枚と保留のガルーラ（docs/barrier-resume-coin-bonus-v0.34.md）。v0.35: 採用 5 枚（docs/coin-groups-damage-order-v0.35.md）。
        # v0.36: 採用 11 枚（docs/sand-attack-retreat-lock-v0.36.md）。v0.37: 採用 14 枚と、過去の原典照合の記録のある化石の秘密のベトベター
        # （pcg-search.com の照合だけを書く guidebook_record。docs/fifteen-reused-effects-v0.37.md）。v0.38: 採用 15 枚（docs/bench-switch-combined-v0.38.md）。
        # v0.39: 採用 15 枚（docs/selfdestruct-spread-count-v0.39.md）。v0.40: 採用 15 枚（docs/count-condition-switch-return-v0.40.md）。
        # v0.41: 採用 15 枚（docs/heal-counter-status-v0.41.md）。v0.42: 採用 15 枚（docs/power-decisions-v0.42.md）。v0.43: 採用 9 枚
        # （docs/declared-entry-powers-v0.43.md）。v0.44: 採用 15 枚（ポケモン 14 枚とトレーナーのサカキ。docs/search-evolution-once-attacks-v0.44.md）。
        # v0.45: 採用 14 枚と、過去の原典照合の記録のある第1弾のゴースト（pcg-search.com の照合だけを書く guidebook_record。
        # docs/conditional-damage-energy-v0.45.md）。v0.46: 採用 11 枚（docs/continuous-powers-v0.46.md）。v0.47: 採用 13 枚（ポケモン 11 枚とトレーナーの
        # なにかの化石・ピッピ人形。記録の中身は tests/test_fossil_hidden_info_v0_47.py の CardDataTest が確かめる。docs/fossil-hidden-info-v0.47.md）。
        # v0.48: 採用 7 枚（記録の中身は tests/test_effective_pokemon_properties_v0_48.py の CardDataTest が確かめる。docs/effective-pokemon-properties-v0.48.md）。
        # v0.49: 採用 4 枚（ポケモン 3 枚とトレーナーの思い出させる。記録の中身は tests/test_virtual_attacks_transformation_v0_49.py の CardDataTest が確かめる。
        # docs/virtual-attacks-transformation-v0.49.md）。v0.50: 採用 2 枚（ミュウとトレーナーの退化スプレー。記録の中身は tests/test_mew_devolution_v0_50.py の
        # CardDataTest が確かめる。docs/mew-devolution-spray-v0.50.md）。v0.51: 採用 3 枚（ナツメのスリーパーとトレーナーの元気のかけら・ポケモンの笛。記録の中身は
        # tests/test_discard_to_bench_v0_51.py の CardDataTest が確かめる。docs/discard-to-bench-v0.51.md）
        self.assertEqual(sorted(sources["cards"]), sorted(V0_29_POKEMON + V0_30_POKEMON + V0_31_POKEMON + V0_32_POKEMON + V0_33_POKEMON + V0_34_POKEMON
                                                          + (KANGASKHAN,) + V0_35_POKEMON + V0_36_POKEMON + V0_37_POKEMON + V0_38_POKEMON
                                                          + V0_39_POKEMON + V0_40_POKEMON + V0_41_POKEMON + V0_42_POKEMON + V0_43_POKEMON
                                                          + V0_44_CARDS + (BASE_HAUNTER,) + V0_45_ADOPTED + V0_46_POKEMON + V0_47_CARDS
                                                          + V0_48_POKEMON + V0_49_CARDS + V0_50_CARDS + V0_51_CARDS + V0_52_CARDS + V0_53_CARDS
                                                          + V0_54_CARDS + V0_55_CARDS + V0_56_CARDS + V0_57_CARDS + V0_58_CARDS + V0_59_CARDS + V0_60_CARDS + V0_61_CARDS + V0_62_CARDS + V0_63_CARDS + V0_64_CARDS + V0_65_CARDS + V0_66_CARDS + V0_67_CARDS + (KOGAS_MUK, IMAKUNI_DODUO) + V0_69_CARDS + V0_70_CARDS + V0_71_CARDS + V0_72_CARDS))  # v0.72: 拡張パック以外の商品のポケモン 43 枚（kyuura データの採用。外部照合なし）。v0.71: 拡張パック以外の商品の再録 78 枚（reprint_of のある採用の記録。外部照合なし）。v0.70: 拡張パック以外の商品のポケモン 82 枚（kyuura データの採用。外部照合なし）。v0.69: 拡張パック以外の商品の同じカード 84 枚（元のカードの登録を写した採用の記録）。v0.68: キョウのベトベトン（v0.17c の照合の記録のある guidebook_record）・イマクニ？のドードー（ガルーラは v0.34 から記録がある）。v0.67: 1 枚。v0.65: 3 枚。v0.57: スタジアム 14 枚、v0.58: 7 枚、v0.59: 6 枚、v0.60・v0.61: 4 枚ずつ、v0.62: 6 枚、v0.63: 4 枚、v0.64: 3 枚
        # v0.46: 採用の 11 枚は 2026-10-17 に記録し、pcg-search.com の同じ版のページと照合した。違いは 5 枚とも処理に影響しない（バリヤード・カビゴンの特殊能力の
        # 説明文の読点、エリカのフシギソウの「いる限り」と「いるかぎり」、わるいベトベトンの「2ぶん」と「2つぶん」、わるいオコリザルのワザの名前の「あばれくるう」と
        # 「あれくるう」（kyuura への報告事項））。処理に使う文面はどれも kyuura の印刷の文面
        v046_differences = {MR_MIME: "pokemon.powers[0].text.ja", ERIKAS_IVYSAUR: "pokemon.powers[0].text.ja", DARK_PRIMEAPE: "pokemon.attacks[0].name.ja",
                            DARK_MUK: "pokemon.powers[0].text.ja", SNORLAX: "pokemon.powers[0].text.ja"}
        # v0.69: 研究の基準のコミット（7d3f4ca）でこれらのカードを指す kyuura の論点（エンジンの停止コードに対応する論点。kyuura が v0.68 までの記録を取り込んだ）
        V046_KYUURA_RECORDS = {ERIKAS_IVYSAUR: ["UQ-CALMING-AROMA-RETALIATION"], "PMCG2-040": ["UQ-RETREAT-COST-PAYMENT"]}
        for card_id in V0_46_POKEMON:
            record = sources["cards"][card_id]
            with self.subTest(card=card_id):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["recorded_on"], record["kyuura_records"]),
                                 (cs.KYUURA_DATA, cs.ADOPTED, ADOPTED_COMMIT, "2026-10-17", V046_KYUURA_RECORDS.get(card_id, [])))
                self.assertEqual(set(record["play_text"].values()), {cs.PRINTED_TEXT})
                [check] = record["external_checks"]
                self.assertEqual(check["checked_on"], "2026-10-17")
                self.assertEqual(check["result"], "differences" if card_id in v046_differences else "match")
                self.assertEqual([d["field"] for d in check["differences"]], [v046_differences[card_id]] if card_id in v046_differences else [])
                self.assertTrue(all(not d["affects_behavior"] for d in check["differences"]))
                self.assertEqual(record["issues"], [])
        for card_id in V0_44_CARDS:
            record = sources["cards"][card_id]
            with self.subTest(card=card_id):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["recorded_on"]),
                                 (cs.KYUURA_DATA, cs.ADOPTED, ADOPTED_COMMIT, "2026-10-16"))
                [check] = record["external_checks"]
                self.assertEqual(check["checked_on"], "2026-10-16")
                # _____のラッキーの名前の空欄の下線の数だけが違う（処理に影響しない）。ほかはどれも一致
                self.assertEqual(check["result"], "differences" if card_id == BLANK_CHANSEY else "match")
                self.assertTrue(all(not d["affects_behavior"] for d in check["differences"]))
        # トレーナーのサカキの処理に使う文面は kyuura の印刷の文面、カスミのヒトデマンの「スターブーメラン」は kyuura の最新の説明（LD-PMCG5-027-ATK0）
        self.assertEqual(sources["cards"][GIOVANNI]["play_text"], {"trainer": cs.PRINTED_TEXT})
        self.assertEqual(sources["cards"][MISTYS_STARYU]["play_text"], {"attack/0": "LD-PMCG5-027-ATK0"})
        # v0.45: 採用の 14 枚は 2026-10-16 に記録し、pcg-search.com の同じ版のページと照合した。違いは 4 枚とも処理に影響しない（わるいカメックス・
        # タケシのイシツブテ（HP 40）の説明文の表記、わるいレアコイルの「特殊エネルギーカード」と「特殊エネルギー」、ラッタのダメージの表示の「?」）
        with_differences = {DARK_BLASTOISE: "pokemon.attacks[0].text.ja", DARK_MAGNETON: "pokemon.attacks[1].text.ja",
                            RATICATE: "pokemon.attacks[1].damage", BROCKS_GEODUDE_40: "pokemon.attacks[0].text.ja"}
        for card_id in V0_45_ADOPTED:
            record = sources["cards"][card_id]
            with self.subTest(card=card_id):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["recorded_on"]),
                                 (cs.KYUURA_DATA, cs.ADOPTED, ADOPTED_COMMIT, "2026-10-16"))
                [check] = record["external_checks"]
                self.assertEqual(check["checked_on"], "2026-10-16")
                self.assertEqual(check["result"], "differences" if card_id in with_differences else "match")
                self.assertEqual([d["field"] for d in check["differences"]], [with_differences[card_id]] if card_id in with_differences else [])
                self.assertTrue(all(not d["affects_behavior"] for d in check["differences"]))
                self.assertEqual(record["issues"], [])
        # R団のエビワラーの「クロスカウンター」の処理に使う文面は kyuura の最新の説明（LD-PMCG5-054-ATK0）。ほかは kyuura の印刷の文面
        self.assertEqual(sources["cards"][ROCKETS_HITMONCHAN]["play_text"], {"attack/0": "LD-PMCG5-054-ATK0"})
        self.assertTrue(all(set(sources["cards"][c]["play_text"].values()) == {cs.PRINTED_TEXT} for c in V0_45_ADOPTED if c != ROCKETS_HITMONCHAN))
        # 第1弾のゴーストは v0.9 の過去の原典照合の記録で登録した（化石の秘密のベトベターと同じ。pcg-search.com の照合だけを書く）
        haunter = sources["cards"][BASE_HAUNTER]
        self.assertEqual((haunter["basis"], [c["result"] for c in haunter["external_checks"]]), (cs.GUIDEBOOK_RECORD, ["match"]))
        self.assertNotIn("play_text", haunter)
        for card_id in V0_29_POKEMON:
            record = sources["cards"][card_id]
            with self.subTest(card=card_id):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]), (cs.KYUURA_DATA, cs.ADOPTED, ADOPTED_COMMIT))
                self.assertEqual(record["kyuura_records"], [])  # 研究の基準のコミットに、このカードを指す kyuura の記録はない
                self.assertEqual(set(record["play_text"].values()) - {cs.PRINTED_TEXT}, set())
                [check] = record["external_checks"]
                self.assertEqual((check["result"], check["differences"], check["checked_on"]), ("match", [], "2026-10-15"))
        for card_id in V0_30_ADOPTED:
            record = sources["cards"][card_id]
            with self.subTest(card=card_id):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]), (cs.KYUURA_DATA, cs.ADOPTED, ADOPTED_COMMIT))
                # 炎エネルギーをトラッシュするワザの文面は kyuura のエラッタ（RUL-）。第4弾ロケット団のポニータは印刷の文面（記録の文と違う）
                self.assertEqual(record["kyuura_records"], [] if card_id == "PMCG4-013" else [RUL])
                self.assertLessEqual(set(record["play_text"].values()), {cs.PRINTED_TEXT, RUL})
                [check] = record["external_checks"]
                self.assertEqual(check["checked_on"], "2026-10-15")
                self.assertFalse(any(d["affects_behavior"] for d in check["differences"]))
        record = sources["cards"][CHARMANDER]
        self.assertEqual((record["basis"], record["play_text"], record["kyuura_records"]),
                         (cs.GUIDEBOOK_RECORD, {"attack/1": RUL}, ["CC-PMCG1-014-P63", RUL]))
        for card_id in V0_31_POKEMON:
            record = sources["cards"][card_id]
            with self.subTest(card=card_id):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]), (cs.KYUURA_DATA, cs.ADOPTED, ADOPTED_COMMIT))
                [check] = record["external_checks"]
                self.assertEqual((check["checked_on"], check["result"] in ("match", "differences")), ("2026-10-15", True))
                self.assertFalse(any(d["affects_behavior"] for d in check["differences"]))
                self.assertFalse(any(issue["affects_behavior"] for issue in record["issues"]))
        for card_id in V0_32_POKEMON + V0_33_POKEMON + V0_34_POKEMON + V0_35_POKEMON + V0_36_POKEMON + V0_37_ADOPTED:  # v0.32〜v0.37。2026-10-16 に照合
            record = sources["cards"][card_id]
            with self.subTest(card=card_id):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]), (cs.KYUURA_DATA, cs.ADOPTED, ADOPTED_COMMIT))
                [check] = record["external_checks"]
                self.assertEqual((check["checked_on"], check["result"] in ("match", "differences")), ("2026-10-16", True))
                self.assertFalse(any(d["affects_behavior"] for d in check["differences"]))
                self.assertFalse(any(issue["affects_behavior"] for issue in record["issues"]))
        # v0.31: 処理に使う文面が kyuura の記録のもの（キュウコンのだいもんじは RUL- の範囲、リザードンのエナジーバーンは TXT-CHARIZARD、ピッピの
        # ゆびをふるは日英の違いの記録が引く最新の説明）。ほかは印刷の文面
        self.assertEqual(sources["cards"]["PMCG1-022"]["play_text"]["attack/1"], RUL)
        self.assertEqual(sources["cards"]["PMCG1-021"]["play_text"]["power/0"], "TXT-CHARIZARD")
        self.assertEqual(sources["cards"]["PMCG1-067"]["play_text"]["attack/1"], f"{cs.DIFFERENCE_TEXT_SOURCE}#PMCG1-067")
        # v0.34: ガルーラ（PMCG2-046）は pcg-search.com との照合で挙動に影響する違い（こどものおつかいのコイン）があるので保留した。v0.68 で、利用者が示した訂正
        # （写しの作り直しの USER_PROVIDED_CORRECTIONS）を当てはめて採用した（論点はなくなった。docs/final-pmcg-cards-v0.68.md 2 章）
        kangaskhan = sources["cards"][KANGASKHAN]
        self.assertEqual((kangaskhan["status"], kangaskhan["play_text"]),
                         (cs.ADOPTED, {"attack/0": cs.USER_CORRECTION, "attack/1": "kyuura_printed_text"}))
        self.assertEqual(kangaskhan["issues"], [])
        self.assertIn(KANGASKHAN, cs.registered_cards(DEFAULT_EFFECTS))
        section = cs.load_links()["latest_descriptions"]
        # v0.29 の 14・v0.30 のとっしん・第4弾のポニータのひのこ（16）と、v0.31 の 45（特殊能力 2 を含む）と、v0.32 の 19 と、v0.33 の 25 と、
        # v0.34 の 26（ブースターのかえんほうしゃも印刷の文面。トラッシュの時点だけを RUL-ENERGY-DISCARD-ATTACKS の範囲とした）と、v0.35 の 10 と、
        # v0.36 の 16（説明文のあるワザ。サンドパンのきりさく・カスミのタッツーのたいあたり・キョウのポッポのつつくは説明文なし）と、v0.37 の 19
        # （採用の 14 枚の説明文のあるワザ。化石の秘密のベトベターの 2 つは照合の記録の文面で、LD-・CC- の区分）と、v0.38 の 21（15 枚の説明文の
        # あるワザ。kyuura に LD-・エラッタ・裁定の記録がない）と、v0.39 の 21（15 枚の説明文のあるワザ。kyuura に LD-・エラッタの記録がない。
        # 第1弾のレアコイルを指す kyuura の記録は「とうめい」の裁定（CR-）だけ）と、v0.40 の 22（15 枚の説明文のあるワザ。kyuura に LD-・エラッタ・
        # 裁定の記録がない）と、v0.41 の 26（15 枚の説明文のあるワザ。kyuura に LD-・エラッタ・裁定の記録がない）と、v0.42 の 23（15 枚の説明文の
        # あるワザ 16 と特殊能力 7。カイリューの［かけつける］は card_differences の最新の説明なので difference_text）と、v0.43 の 17（9 枚の説明文の
        # あるワザ 8 と特殊能力 9。kyuura に LD-・エラッタ・裁定・card_differences の記録がない）と、v0.44 の 21（14 枚の説明文のあるワザ 19 と特殊能力 2。
        # カスミのヒトデマンの「スターブーメラン」は kyuura の最新の説明（LD-PMCG5-027-ATK0）があるので registered。トレーナーのサカキは対応表の区分の外）と、
        # v0.45 の 21（採用の 14 枚の説明文のあるワザ 22 から、kyuura の最新の説明（LD-PMCG5-054-ATK0）のある R団のエビワラーの「クロスカウンター」
        # を除く（registered）。第1弾のゴーストの 2 つは照合の記録の文面で、LD-・CC- の区分）と、v0.46 の 22（11 枚の説明文のあるワザ 14 と特殊能力 8。
        # kyuura に LD-・エラッタ・裁定・card_differences の記録がない）と、v0.47 の 17（ポケモン 11 枚の説明文のあるワザ 12 と特殊能力 5。トレーナーの
        # なにかの化石・ピッピ人形はワザ・特殊能力の区分の外。kyuura に LD-・エラッタ・裁定・card_differences の記録がない）と、v0.48 の 12（7 枚の説明文のある
        # ワザ 10 と特殊能力 2。kyuura に LD-・エラッタ・裁定・card_differences の記録がない）と、v0.49 の 4（メガバーンと特殊能力 3（［サイコリンク］・［へんしん］・
        # 「ばける」）。説明文のないおにびと、トレーナーの思い出させるは区分の外。kyuura に LD-・エラッタ・裁定・card_differences の記録がない。タケシのキュウコンの
        # ERR-BROCK-NINETALES は 2000年5月の変更なので処理に使う文面にしていない。docs/virtual-attacks-transformation-v0.49.md）と、v0.50 の 2（ミュウの
        # サイコウェーブ・たいかビーム。トレーナーの退化スプレーは区分の外。kyuura に LD-・エラッタ・裁定・card_differences の記録がない。docs/mew-devolution-spray-v0.50.md）
        # v0.51 の 2（ナツメのスリーパーのよみがえらせる・ふりこののろい。トレーナーの元気のかけら・ポケモンの笛は区分の外。kyuura に LD-・エラッタ・裁定・
        # card_differences の記録がない。docs/discard-to-bench-v0.51.md）
        self.assertEqual(len(section["adopted_printed_text"]), 606)  # v0.72: 拡張パック以外の商品のポケモン 43 枚の説明文のあるワザ 67 を加えた。v0.71: 再録のポケモンの、この版の印刷の文面にしたワザ・特殊能力 11 を加えた。v0.70: 拡張パック以外の商品のポケモン 82 枚の説明文のあるワザ 85 を加えた。v0.68: ガルーラのれんぞくパンチを加えた。v0.65: クラゲどく・ラリアット・［ベンチガード］を加えた  # v0.52: ふぶき・つれさるを加えた。v0.58: ばくれつ・いわなだれを加えた。v0.59: エネエネ・でんげき・クリスタルビーム・ショックアイ・どくのきりを加えた。v0.60: サンダーストーム・かげぶんしん・はんこう・スピードスター・とげボールを加えた。v0.61: ［ファイナルビーム］・れいとうビーム・［おとしあな］・つきおとす・［ずらかる］・おおあばれを加えた。v0.62: ふきとばし・オウムがえし 2・こうそくいどう・ハリケーン・あながくれ・ドリルホール・まきつくベロ・ちょうおんぱを加えた。v0.64: れんぞくいしなげ・かたくなる・じばくを加えた
        self.assertNotIn(f"{ROCKETS_HITMONCHAN}/attack/0", section["adopted_printed_text"])
        self.assertEqual(section["registered"][f"{ROCKETS_HITMONCHAN}/attack/0"], "LD-PMCG5-054-ATK0")
        self.assertEqual((section["registered"][f"{BASE_HAUNTER}/attack/1"], section["recorded_in_card_checks"][f"{BASE_HAUNTER}/attack/0"]),
                         ("LD-PMCG1-047-ATK1", "CC-PMCG1-047-P160"))
        # v0.37: 化石の秘密のベトベター（過去の原典照合の記録のあるカード）は pcg-search.com の照合だけを書く。タケシのイワークは kyuura が読んだ
        # 照合の記録（CC-）がある。ペルシアンは kyuura の文面の【】だけがサイトと違う（処理に影響しない）
        grimer = sources["cards"][FOSSIL_GRIMER]
        self.assertEqual((grimer["basis"], [c["result"] for c in grimer["external_checks"]]), (cs.GUIDEBOOK_RECORD, ["match"]))
        self.assertNotIn("play_text", grimer)
        self.assertEqual(sources["cards"][BROCKS_ONIX]["kyuura_records"], ["CC-PMCG5-048-P200"])
        [check] = sources["cards"][PERSIAN]["external_checks"]
        self.assertEqual([d["field"] for d in check["differences"]], ["pokemon.attacks[1].text.ja"])
        self.assertEqual(section["registered"]["PMCG3-003/attack/1"], "LD-PMCG3-003-ATK1")
        self.assertEqual(section["recorded_in_card_checks"]["PMCG3-003/attack/0"], "CC-PMCG3-003-P47")
        self.assertEqual(sorted(section["errata_text"]), ["PMCG1-014/attack/1", "PMCG1-017/attack/1", "PMCG1-019/attack/0", "PMCG1-020/attack/1",
                                                          "PMCG1-021/power/0", "PMCG1-022/attack/1"])
        # v0.42: カイリュー（PMCG3-043）の［かけつける］も、kyuura の data/curation/card_differences.json の PMCG3-043（確度: 確実）の最新の説明
        # （LD- はない。v0.31 のピッピのゆびをふると同じ区分）
        self.assertEqual(sources["cards"]["PMCG3-043"]["play_text"]["power/0"], f"{cs.DIFFERENCE_TEXT_SOURCE}#PMCG3-043")
        self.assertEqual(section["difference_text"], {"PMCG1-067/attack/1": f"{cs.DIFFERENCE_TEXT_SOURCE}#PMCG1-067",
                                                      "PMCG3-043/power/0": f"{cs.DIFFERENCE_TEXT_SOURCE}#PMCG3-043"})

    def test_guidebook_record_covers_only_targets_without_verified_text(self):
        """過去の原典照合の記録のあるカードの play_text は、照合の記録に処理に使う文面のない登録だけに書く（v0.30）。ヒトカゲの照合の記録
        （v0.2a）は「ひっかく」のために作ったので「ひのこ」の文面がない。スターミー（v0.28）は照合の記録にどちらのワザの文面もある。"""
        verification = read_verification()
        self.assertEqual(cs.uncovered_play_text_targets(CHARMANDER, verification, DEFAULT_EFFECTS), {"attack/1"})
        self.assertEqual(cs.uncovered_play_text_targets(STARMIE, verification, DEFAULT_EFFECTS), set())
        for card_id in cs.registered_cards(DEFAULT_EFFECTS) & set(verification["cards"]):
            with self.subTest(card=card_id):
                expected = {"attack/1"} if card_id == CHARMANDER else set()
                self.assertEqual(cs.uncovered_play_text_targets(card_id, verification, DEFAULT_EFFECTS), expected)

    def test_history_is_kept(self):
        """過去の原典照合の記録（card_verification.json）は、2026-10-14 までに登録したカードの記録をそのまま持つ（履歴。新しい方針で書き換えない）。
        v0.29〜v0.54 の採用の記録で登録したカードは、過去の原典照合の記録に入れない（v0.30 のヒトカゲは v0.2a、v0.37 の化石の秘密のベトベターは
        v0.8、v0.45 の第1弾のゴーストは v0.9 の記録のあるカード）。"""
        verification = read_verification()
        sources = cs.load_sources()
        registered = cs.registered_cards(DEFAULT_EFFECTS)
        adopted = (set(V0_29_POKEMON) | set(V0_30_ADOPTED) | set(V0_31_POKEMON) | set(V0_32_POKEMON) | set(V0_33_POKEMON) | set(V0_34_POKEMON)
                   | set(V0_35_POKEMON) | set(V0_36_POKEMON) | set(V0_37_ADOPTED) | set(V0_38_POKEMON) | set(V0_39_POKEMON)
                   | set(V0_40_POKEMON) | set(V0_41_POKEMON) | set(V0_42_POKEMON) | set(V0_43_POKEMON)
                   | set(V0_44_CARDS) | set(V0_45_ADOPTED) | set(V0_46_POKEMON) | set(V0_47_CARDS) | set(V0_48_POKEMON)
                   | set(V0_49_CARDS) | set(V0_50_CARDS) | set(V0_51_CARDS) | set(V0_52_CARDS) | set(V0_53_CARDS)
                   | set(V0_54_CARDS) | set(V0_55_CARDS) | set(V0_56_CARDS) | set(V0_57_CARDS) | set(V0_58_CARDS) | set(V0_59_CARDS) | set(V0_60_CARDS) | set(V0_61_CARDS) | set(V0_62_CARDS) | set(V0_63_CARDS) | set(V0_64_CARDS) | set(V0_65_CARDS) | set(V0_66_CARDS) | set(V0_67_CARDS) | {KANGASKHAN, IMAKUNI_DODUO} | set(V0_69_CARDS) | set(V0_70_CARDS) | set(V0_71_CARDS) | set(V0_72_CARDS))  # v0.35〜v0.72（v0.68 のキョウのベトベトンは v0.17c の照合の記録）
        self.assertIn(FOSSIL_GRIMER, verification["cards"])  # v0.37 で登録した化石の秘密のベトベターは v0.8 の照合の記録で登録した
        self.assertIn(BASE_HAUNTER, verification["cards"])  # v0.45 で登録した第1弾のゴーストは v0.9 の照合の記録で登録した
        self.assertIn(KOGAS_MUK, verification["cards"])  # v0.68 で登録したキョウのベトベトンは v0.17c の照合の記録で登録した
        self.assertLessEqual(registered - adopted, set(verification["cards"]))
        self.assertFalse(adopted & set(verification["cards"]))
        self.assertIn(CHARMANDER, verification["cards"])
        for card_id in registered:
            expected = cs.KYUURA_DATA if card_id in adopted else cs.GUIDEBOOK_RECORD
            self.assertEqual(cs.registration_basis(card_id, verification, sources), expected, card_id)

    def test_command_line(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(cs.main([]), 0)
        self.assertIn("方針と合っています", out.getvalue())

    def test_command_line_rejects_a_false_record(self):
        """ガイドブックのページを書いた採用の記録（読んでいない原典を確かめたことにする記録）を置くと、検査は終了コード 1 で失敗する。"""
        sources = cs.load_sources()
        sources["cards"]["PMCG1-021"] = {
            "basis": "kyuura_data", "name_ja": "リザードン", "status": "on_hold", "kyuura_commit": COMMIT, "recorded_on": "2026-10-15",
            "kyuura_records": ["TXT-CHARIZARD"], "play_text": {}, "external_checks": [], "page": 66,
            "issues": [{"question": "q", "fields": [], "affects_behavior": True}]}
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "card_sources.json"
            path.write_text(json.dumps(sources, ensure_ascii=False), encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(cs, "SOURCES", path), redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(cs.main([]), 1)
        self.assertIn("ガイドブックの照合の項目 ['page']", err.getvalue())


class AcceptTest(unittest.TestCase):
    def test_policy_records_are_accepted(self):
        """ガイドブックのページ・画像の照合の記録がなくても、kyuura データの採用の記録で登録できる（印刷の文面・LD- のどちらの根拠も）。
        保留のカード、対象の版がない・アクセスできなかった外部照合、過去の原典照合で登録したカードへの外部照合も受け付ける。"""
        case = valid_case()
        self.assertEqual(run(case), [])
        sources, registry, verification, _ = case
        self.assertEqual(cs.registration_basis(TANGELA, verification, sources), cs.KYUURA_DATA)
        self.assertEqual(cs.registration_basis(BUTTERFREE, verification, sources), cs.KYUURA_DATA)
        self.assertEqual(cs.registration_basis(STARMIE, verification, sources), cs.GUIDEBOOK_RECORD)
        self.assertIsNone(cs.registration_basis(CHARIZARD, verification, sources))
        self.assertNotIn(TANGELA, verification["cards"])

    def test_adoption_without_external_check(self):
        """外部照合がない（できなかった）ことだけでは、採用を妨げない。"""
        sources, *rest = valid_case()
        sources["cards"][TANGELA]["external_checks"] = []
        self.assertEqual(run((sources, *rest)), [])

    def test_numeric_check_of_a_card_transcribed_from_the_site(self):
        """kyuura の日本語の文面が pcg-search.com の転記のカード（プリン PMCG2-035。写しの ja_text_source）も、日本語でない欄（HP など。
        kyuura は英語版のデータから入れた）は照合を記録できる。"""
        sources, *rest = valid_case()
        sources["cards"]["PMCG2-035"] = {"basis": "guidebook_record", "name_ja": "プリン", "external_checks": [
            pcg_check(url="https://pcg-search.com/card/1st/1stintro2014.php", edition={"expansion": "イントロパック", "list_number": "014"},
                      checked_fields=["pokemon.hp", "pokemon.retreat_cost"])]}
        self.assertEqual(run((sources, *rest)), [])

    def test_recheck_after_inaccessible_is_allowed(self):
        """アクセスできなかった版を、あとで照合し直すことはできる（終わった照合だけを、同じ版・同じデータで調べ直さない）。"""
        sources, *rest = valid_case()
        checks = sources["cards"][TANGELA]["external_checks"]
        checks[:] = [pcg_check(result="inaccessible", checked_fields=[], differences=[]), pcg_check(checked_on="2026-10-17")]
        self.assertEqual(run((sources, *rest)), [])


def mutate(path, value=None, *, delete=False):
    """記録の中の 1 か所を変える（``path`` は sources の中のキーの並び）。"""
    def apply(case):
        sources = case[0]
        target = sources
        for key in path[:-1]:
            target = target[key]
        if delete:
            del target[path[-1]]
        else:
            target[path[-1]] = value
        return case
    return apply


def check_of(card, index, **changes):
    def apply(case):
        case[0]["cards"][card]["external_checks"][index].update(changes)
        return case
    return apply


def with_registry(change):
    def apply(case):
        sources, registry, verification, links = case
        return sources, change(registry), verification, links
    return apply


def with_links(change):
    def apply(case):
        change(case[3])
        return case
    return apply


def with_verification(change):
    def apply(case):
        change(case[2])
        return case
    return apply


TANGELA_CHECKS = ("cards", TANGELA, "external_checks")
DIFFERENCE = [{"field": "pokemon.attacks[0].name.ja", "kyuura": "しめつける", "pcg_search": "しめつけ", "affects_behavior": True}]

# (場面, 記録を変える関数, 問題の文に含まれる語)
REJECTED = [
    ("採用の記録にガイドブックのページ", mutate(("cards", TANGELA, "page"), 55), "ガイドブックの照合の項目"),
    ("採用の記録にガイドブックの最新の説明", mutate(("cards", TANGELA, "latest_description_ja"), "…"), "ガイドブックの照合の項目"),
    ("外部照合に PDF のページ", check_of(TANGELA, 0, pdf_page=57), "ガイドブックの照合の項目"),
    ("ガイドブックを外部照合のサイトにする", check_of(TANGELA, 0, site="オフィシャルブック2000"), "外部照合のサイト"),
    ("kyuura の cards.csv を外部照合のサイトにする", check_of(TANGELA, 0, site="kyuura data/cards.csv"), "外部照合のサイト"),
    ("ほかのサイトの URL", check_of(TANGELA, 0, url="https://example.com/card/1st/1st1013.php"), "https の pcg-search.com のページではない"),
    ("似た名前のホスト", check_of(TANGELA, 0, url="https://pcg-search.com.example.net/card/1st/1st1013.php"), "pcg-search.com のページではない"),
    ("http の URL", check_of(TANGELA, 0, url="http://pcg-search.com/card/1st/1st1013.php"), "pcg-search.com のページではない"),
    ("URL がない", mutate(TANGELA_CHECKS + (0, "url"), delete=True), "['url'] がない"),
    ("確認日がない", mutate(TANGELA_CHECKS + (0, "checked_on"), delete=True), "['checked_on'] がない"),
    ("版がない", mutate(TANGELA_CHECKS + (0, "edition"), delete=True), "['edition'] がない"),
    ("確認日が今日より後", check_of(TANGELA, 0, checked_on="2026-10-21"), "より後"),
    ("確認日が方針の開始日より前", check_of(TANGELA, 0, checked_on="2026-10-14"), "より前"),
    ("確認日の形が違う", check_of(TANGELA, 0, checked_on="2026/10/16"), "日付ではない"),
    ("照合した版の一覧の番号がない", check_of(TANGELA, 0, edition={"expansion": "第1弾 拡張パック", "list_number": None}), "一覧の番号（list_number）がない"),
    ("版の収録がない", check_of(TANGELA, 0, edition={"expansion": "", "list_number": "013/096"}), "収録"),
    ("版の項目が足りない", check_of(TANGELA, 0, edition={"list_number": "013/096"}), "収録（expansion）と一覧の番号"),
    ("照らしたコミットが SHA でない", check_of(TANGELA, 0, kyuura_commit="ecb2d69"), "40 桁"),
    ("知らない結果", check_of(TANGELA, 0, result="ok"), "結果 'ok'"),
    ("対象の版がないのに照合した欄", check_of(TANGELA, 2, checked_fields=["name.ja"]), "照合した欄・違いを書けない"),
    ("アクセスできないのに違い", check_of(TANGELA, 3, differences=DIFFERENCE), "照合した欄・違いを書けない"),
    ("一致なのに違い", check_of(TANGELA, 0, differences=[dict(DIFFERENCE[0], affects_behavior=False)]), "違いがある"),
    ("一致なのに照合した欄がない", check_of(TANGELA, 0, checked_fields=[]), "照合した欄がない"),
    ("違いの結果なのに違いがない", check_of(TANGELA, 1, differences=[]), "違いがない"),
    ("違いの欄が照合した欄にない", check_of(TANGELA, 1, checked_fields=["name.ja"]), "照合した欄にない"),
    ("違いの kyuura の値を作る", check_of(TANGELA, 1, differences=[dict(DIFFERENCE[0], kyuura="からみつく", affects_behavior=False)]),
     "写しの値と違う"),
    ("違いの値が同じ", check_of(TANGELA, 1, differences=[dict(DIFFERENCE[0], pcg_search="しめつける", affects_behavior=False)]),
     "違いではない"),
    ("知らない欄", check_of(TANGELA, 0, checked_fields=["pokemon.illustrator"]), "照合できる欄ではない"),
    ("ない位置のワザの欄", check_of(TANGELA, 0, checked_fields=["pokemon.attacks[5].text.ja"]), "写しのカードにない"),
    ("同じ版を同じデータで調べ直す", mutate(TANGELA_CHECKS, [pcg_check(), pcg_check(checked_on="2026-10-19")]), "調べ直している"),
    ("採用のコミットが写しと違う", mutate(("cards", TANGELA, "kyuura_commit"), "3f349085645f47d0649a6cacece3680caeae50bf"),
     "採用したデータのコミット"),
    ("記録した日が今日より後", mutate(("cards", TANGELA, "recorded_on"), "2027-01-01"), "記録した日"),
    ("写しにないカード", mutate(("cards", "PMCG9-999"), {"basis": "kyuura_data"}), "写し（kyuura_cards.json）にないカード"),
    ("名前が写しと違う", mutate(("cards", TANGELA, "name_ja"), "モンジャラX"), "名前"),
    ("知らない項目", mutate(("cards", TANGELA, "verified_by_guidebook"), True), "知らない項目"),
    ("知らない basis", mutate(("cards", TANGELA, "basis"), "pcg_search"), "basis"),
    ("知らない status", mutate(("cards", TANGELA, "status"), "verified"), "status"),
    ("kyuura の記録の id でないもの", mutate(("cards", TANGELA, "kyuura_records"), ["P43 p.55"]), "kyuura_records は"),
    ("採用したカードに挙動に影響する違い", check_of(TANGELA, 1, differences=DIFFERENCE), "保留にする"),
    ("採用したカードに挙動に影響する論点", mutate(("cards", TANGELA, "issues"),
                                                  [{"question": "q", "fields": [], "affects_behavior": True}]), "保留にする"),
    ("論点の問いがない", mutate(("cards", TANGELA, "issues"), [{"question": "", "fields": [], "affects_behavior": False}]), "問い"),
    ("保留の理由がない", mutate(("cards", CHARIZARD, "issues"), []), "保留の理由"),
    ("保留のカードを登録する", with_registry(lambda r: r.with_attacks("t", {AttackKey(CHARIZARD, 0): AttackEntry(DAMAGE_ONLY, "ほのおのうず")})),
     "保留のカードが登録されている"),
    ("採用したカードを登録しない", mutate(("cards", CHARIZARD, "status"), "adopted"), "採用したカードが登録されていない"),
    ("過去の原典照合の記録と採用の記録が両方ある", with_verification(lambda v: v["cards"].__setitem__(TANGELA, read_verification()["cards"][TANGELA])),
     "card_verification.json（過去の原典照合）にも記録がある"),
    ("過去の原典照合の記録のないカードを guidebook_record にする",
     mutate(("cards", TANGELA), {"basis": "guidebook_record", "name_ja": "モンジャラ", "external_checks": [pcg_check()]}),
     "card_verification.json に記録がない"),
    ("guidebook_record に採用の項目", mutate(("cards", STARMIE, "status"), "adopted"), "知らない項目"),
    ("guidebook_record の照合の記録に文面のある登録を play_text に書く", mutate(("cards", CHARMANDER, "play_text", "attack/0"), cs.PRINTED_TEXT),
     "根拠を書くべき登録の文面"),
    ("guidebook_record の照合の記録に文面のない登録の根拠がない", mutate(("cards", CHARMANDER, "play_text"), delete=True),
     "の根拠（card_sources.json の play_text）がない"),
    ("guidebook_record の kyuura_records だけ", mutate(("cards", CHARMANDER, "play_text"), delete=True), "play_text といっしょに書く"),
    ("guidebook_record の根拠のエラッタが kyuura_records にない", mutate(("cards", CHARMANDER, "kyuura_records"), ["CC-PMCG1-014-P63"]),
     "kyuura_records にない"),
    ("エラッタの根拠が研究の対応表の errata_text にない", with_links(lambda l: l["latest_descriptions"]["errata_text"].pop(f"{CHARMELEON}/attack/1")),
     "errata_text にない"),
    ("エラッタの根拠と出典が違う", mutate(("cards", CHARMELEON, "play_text", "attack/1"), "RUL-OTHER"), "出典が"),
    ("過去の原典照合の記録がない guidebook_record", with_verification(lambda v: v["cards"].pop(STARMIE)), "card_verification.json に記録がない"),
    ("外部照合のない guidebook_record", mutate(("cards", STARMIE, "external_checks"), []), "外部照合か、照合の記録に文面のない登録の根拠"),
    ("文面が pcg-search.com の転記のカードの日本語の欄", mutate(("cards", "PMCG2-035"), {
        "basis": "guidebook_record", "name_ja": "プリン", "external_checks": [
            pcg_check(url="https://pcg-search.com/card/1st/1stintro2014.php",
                      edition={"expansion": "イントロパック", "list_number": "014"},
                      checked_fields=["pokemon.hp", "pokemon.attacks[0].text.ja"])]}), "独立した照合にならない"),
    ("トレーナーにポケモンの欄", mutate(("cards", OAK), {"basis": "guidebook_record", "name_ja": "オーキドはかせ", "external_checks": [
        pcg_check(url="https://pcg-search.com/card/1st/1st1073.php", edition={"expansion": "第1弾 拡張パック", "list_number": "073/096"},
                  checked_fields=["pokemon.hp"])]}), "このカード（trainer）にない"),
    ("印刷の文面が根拠なのに処理の文面が違う",
     with_registry(lambda r: r.with_attacks("t", {AttackKey(TANGELA, 0): dataclasses.replace(r.attack_entry(TANGELA, 0), play_text_ja="別の文面")})),
     "play_text_ja が写しの文面と違う"),
    ("印刷の文面が根拠なのにガイドブックのページを出典にする",
     with_registry(lambda r: r.with_attacks("t", {AttackKey(TANGELA, 0): dataclasses.replace(r.attack_entry(TANGELA, 0), source="P43 p.55")})),
     "出典が 'P43 p.55'"),
    ("研究の対応表の adopted_printed_text にない", with_links(lambda l: l["latest_descriptions"]["adopted_printed_text"].remove(f"{TANGELA}/attack/0")),
     "adopted_printed_text にない"),
    ("adopted_printed_text に採用の記録のない登録", with_links(lambda l: l["latest_descriptions"]["adopted_printed_text"].append("PMCG1-002/attack/0")),
     "採用の記録がない"),
    ("LD- の根拠が kyuura_records にない", mutate(("cards", BUTTERFREE, "kyuura_records"), ["CC-PMCG2-007-P19"]), "kyuura_records にない"),
    ("LD- の根拠が研究の対応表と違う", with_links(lambda l: l["latest_descriptions"]["registered"].pop(f"{BUTTERFREE}/attack/1")),
     "registered にない"),
    ("LD- の根拠と出典が違う", mutate(("cards", BUTTERFREE, "play_text", "attack/0"), "LD-PMCG2-007-ATK1"), "出典が"),
    ("登録の文面の対象が足りない", mutate(("cards", TANGELA, "play_text"), {"attack/0": cs.PRINTED_TEXT}), "play_text の対象"),
    ("知らない根拠", mutate(("cards", TANGELA, "play_text", "attack/0"), "pcg_search"), "根拠 'pcg_search'"),
    ("登録したカードに根拠の記録がない", mutate(("cards", TANGELA), delete=True), "ちょうど一方がない"),
    ("形式が違う", mutate(("format",), "kyuura-engine card sources 0"), "形式"),
    ("方針の値が違う", mutate(("policy", "external_site"), "example.com"), "方針の値"),
]


class RejectTest(unittest.TestCase):
    def test_false_or_invalid_records_are_rejected(self):
        """読んでいない原典を確かめたことにする記録・方針と合わない記録・形の崩れた記録は、どれも拒否する（場面ごとに、問題の文で確かめる）。"""
        for name, change, expected in REJECTED:
            with self.subTest(name=name):
                found = run(change(valid_case()))
                self.assertTrue(any(expected in p for p in found), (expected, found))

    def test_each_case_changes_the_valid_records(self):
        """どの場面も、変える前の記録は受け付ける（拒否は変えたところによる）。"""
        self.assertEqual(run(valid_case()), [])
        self.assertEqual(len({name for name, _, _ in REJECTED}), len(REJECTED))


KYUURA = pathlib.Path(__file__).resolve().parent.parent.parent / "kyuura"
HAUNTER = "PMCG1-047"   # 第1弾のゴースト: さいみんじゅつは kyuura の LD- なし、ゆめくいは LD-PMCG1-047-ATK1 がある（v0.44 まで参照カード。v0.45 で登録した）
ABRA = "PMCG1-043"      # ケーシィ: kyuura の CC-PMCG1-043-P43 に、ねんりきの文面のデータの誤り（読点）の記録がある


@unittest.skipUnless((KYUURA / ".git").exists(), "../kyuura がない")
class ResearchCommitTest(unittest.TestCase):
    """scripts/check_research_links.py の 4c・7（kyuura データの採用の記録を、研究の基準のコミットの kyuura の記録と照らす）。

    登録していない参照カード（第1弾のゴースト）を、テストの中だけで採用の記録で登録したことにする（効果の実装は確かめない。記録の照らし方だけ。
    同梱の記録・登録表は変えない）。v0.45 で第1弾のゴーストを v0.9 の過去の原典照合の記録で登録したので、テストの中では、その登録を除いた
    登録表（``NO_BASE_HAUNTER_EFFECTS``）・対応表（研究の対応表の区分から外し、LD- を登録していない記録にもどす）・記録の組（同梱の
    guidebook_record を除く）から始める。
    """

    @classmethod
    def setUpClass(cls):
        from scripts import check_research_links as research

        cls.research = research
        cls.links = cs.load_links()
        commit = cls.links["research_commit"]
        cls.ld = {x["id"]: x for x in research.git_show(KYUURA, commit, "data/sidecar/latest_descriptions.json")["records"]}
        cls.cards = {c["id"]: c for c in read_extract()["cards"]}

    def unregistered(self):
        """第1弾のゴーストを登録していない対応表・記録の組（v0.44 までの同梱の状態と同じ扱い）。"""
        links = copy.deepcopy(self.links)
        section = links["latest_descriptions"]
        ld_id = f"LD-{HAUNTER}-ATK1"
        self.assertEqual(section["registered"].pop(f"{HAUNTER}/attack/1"), ld_id)
        self.assertEqual(section["recorded_in_card_checks"].pop(f"{HAUNTER}/attack/0"), f"CC-{HAUNTER}-P160")
        section["kyuura_records_not_registered"].append(ld_id)
        cards = copy.deepcopy(cs.load_sources()["cards"])
        self.assertEqual(cards.pop(HAUNTER)["basis"], cs.GUIDEBOOK_RECORD)
        return links, cards

    def test_unregistered_starting_point_is_accepted(self):
        """テストの始まりの状態（第1弾のゴーストの登録・対応表の区分・記録を除いたもの）は、研究の基準のコミットの記録と照らして受け付ける。"""
        links, cards = self.unregistered()
        self.assertEqual(self.check({"cards": cards}, NO_BASE_HAUNTER_EFFECTS, links), [])

    def case(self):
        links, cards = self.unregistered()
        section = links["latest_descriptions"]
        attacks = self.cards[HAUNTER]["pokemon"]["attacks"]
        ld_id = f"LD-{HAUNTER}-ATK1"
        registry = NO_BASE_HAUNTER_EFFECTS.with_attacks("test-research-commit", {
            AttackKey(HAUNTER, 0): AttackEntry(DAMAGE_ONLY, attacks[0]["name"]["ja"], text_ja=attacks[0]["text"]["ja"],
                                               play_text_ja=attacks[0]["text"]["ja"], source=cs.PRINTED_TEXT_SOURCE),
            AttackKey(HAUNTER, 1): AttackEntry(DAMAGE_ONLY, attacks[1]["name"]["ja"], text_ja=attacks[1]["text"]["ja"],
                                               play_text_ja=self.ld[ld_id]["latest_description"]["text_ja"], source=ld_id),
        })
        section["adopted_printed_text"].append(f"{HAUNTER}/attack/0")
        section["registered"][f"{HAUNTER}/attack/1"] = ld_id
        section["kyuura_records_not_registered"].remove(ld_id)
        sources = {"format": cs.FORMAT, "description": "テストのための記録", "policy": dict(cs.POLICY),
                   "data_migrations": copy.deepcopy(cs.load_sources()["data_migrations"]), "cards": {
            **cards, HAUNTER: {
            "basis": "kyuura_data", "name_ja": "ゴースト", "status": "adopted", "kyuura_commit": COMMIT, "recorded_on": "2026-10-16",
            "kyuura_records": [f"CC-{HAUNTER}-P160", ld_id], "play_text": {"attack/0": cs.PRINTED_TEXT, "attack/1": ld_id},
            "external_checks": [], "issues": []}}}
        return sources, registry, links

    def check(self, sources, registry, links):
        return self.research.check(KYUURA, links=links, sources=sources["cards"], registry=registry)

    def test_adoption_is_accepted(self):
        """採用の記録で登録したカード（印刷の文面を根拠にしたワザ・LD- を根拠にしたワザ）は、どちらの検査も受け付ける。"""
        sources, registry, links = self.case()
        self.assertEqual(self.check(sources, registry, links), [])
        # 第1弾のゴーストには v0.9 の過去の原典照合の記録（参照カード）がある。登録の根拠は 1 つなので、テストの中だけで外す
        verification = copy.deepcopy(read_verification())
        del verification["cards"][HAUNTER]
        self.assertEqual(cs.problems(sources, verification=verification, registry=registry, links=links, today=TODAY), [])

    def assertProblem(self, found, expected):
        self.assertTrue(any(expected in p for p in found), (expected, found))

    def test_missing_kyuura_record_is_rejected(self):
        """確かめた kyuura の記録の一覧に、研究の基準のコミットにある記録が足りない（既存の記録を見落とした）。"""
        sources, registry, links = self.case()
        sources["cards"][HAUNTER]["kyuura_records"] = [f"CC-{HAUNTER}-P160"]
        self.assertProblem(self.check(sources, registry, links), f"kyuura だけ ['LD-{HAUNTER}-ATK1']")

    def test_printed_text_over_latest_description_is_rejected(self):
        """kyuura に最新の説明（LD-）がある対象を、印刷の文面で処理する（既存の最新の説明を取り消す）。"""
        sources, registry, links = self.case()
        section = links["latest_descriptions"]
        attack = self.cards[HAUNTER]["pokemon"]["attacks"][1]
        registry = registry.with_attacks("t", {AttackKey(HAUNTER, 1): AttackEntry(
            DAMAGE_ONLY, attack["name"]["ja"], text_ja=attack["text"]["ja"], play_text_ja=attack["text"]["ja"], source=cs.PRINTED_TEXT_SOURCE)})
        del section["registered"][f"{HAUNTER}/attack/1"]
        section["adopted_printed_text"].append(f"{HAUNTER}/attack/1")
        sources["cards"][HAUNTER]["play_text"]["attack/1"] = cs.PRINTED_TEXT
        self.assertProblem(self.check(sources, registry, links), f"kyuura に最新の説明の記録 LD-{HAUNTER}-ATK1 がある")

    def test_text_other_than_the_printed_text_is_rejected(self):
        sources, registry, links = self.case()
        entry = registry.attack_entry(HAUNTER, 0)
        registry = registry.with_attacks("t", {AttackKey(HAUNTER, 0): dataclasses.replace(entry, play_text_ja=entry.play_text_ja + "（変えた）")})
        self.assertProblem(self.check(sources, registry, links), "研究の基準のコミットの印刷の文面と違う")

    def test_known_data_error_is_rejected(self):
        """kyuura の照合の記録にデータの誤りの記録がある文面を、印刷の文面のまま採用する（ケーシィのねんりき）。論点にも挙げていない。"""
        links = copy.deepcopy(self.links)
        section = links["latest_descriptions"]
        del section["recorded_in_card_checks"][f"{ABRA}/attack/0"]
        section["adopted_printed_text"].append(f"{ABRA}/attack/0")
        entry = DEFAULT_EFFECTS.attack_entry(ABRA, 0)
        registry = DEFAULT_EFFECTS.with_attacks("t", {AttackKey(ABRA, 0): dataclasses.replace(
            entry, play_text_ja=entry.text_ja, source=cs.PRINTED_TEXT_SOURCE)})
        sources = {"cards": {ABRA: {
            "basis": "kyuura_data", "name_ja": "ケーシィ", "status": "adopted", "kyuura_commit": COMMIT, "recorded_on": "2026-10-16",
            "kyuura_records": [f"CC-{ABRA}-P43", "CR-EFFECTS-AFTER-KO", "CR-STATUS-AFTER-DAMAGE"],
            "play_text": {"attack/0": cs.PRINTED_TEXT}, "external_checks": [], "issues": []}}}
        found = self.check(sources, registry, links)
        self.assertProblem(found, "この文面のデータの誤りの記録がある")
        self.assertProblem(found, "データの誤りの欄 pokemon.attacks[0].text.ja が、採用の記録の論点にない")

    def test_errata_must_be_listed(self):
        """エラッタ（rule_history.json の errata）があるカード（リザードン。TXT-CHARIZARD）は、確かめた記録の一覧に挙げる。根拠にした
        エラッタは、そのカードを指す。"""
        sources = {"cards": {"PMCG1-021": {
            "basis": "kyuura_data", "name_ja": "リザードン", "status": "on_hold", "kyuura_commit": COMMIT, "recorded_on": "2026-10-16",
            "kyuura_records": [], "play_text": {}, "external_checks": [],
            "issues": [{"question": "q", "fields": [], "affects_behavior": True}]}}}
        # v0.69: 研究の基準のコミット（7d3f4ca）では、kyuura の論点 UQ-ENERGY-BURN-TRANSFER もリザードンを指す
        self.assertProblem(self.check(sources, DEFAULT_EFFECTS, self.links), "kyuura だけ ['TXT-CHARIZARD', 'UQ-ENERGY-BURN-TRANSFER']")
        sources, registry, links = self.case()
        sources["cards"][HAUNTER]["play_text"]["attack/0"] = "ERR-PLUSPOWER"
        self.assertProblem(self.check(sources, registry, links), "根拠のエラッタ ERR-PLUSPOWER が、研究の基準のコミットでこのカードを指していない")

    def scope_case(self):
        links = copy.deepcopy(self.links)
        return links, links["latest_descriptions"]

    def test_errata_scope_is_accepted(self):
        """v0.30: 炎エネルギーをトラッシュするワザ（ヒトカゲ・リザード・ブーバー）に、記録の cards にないが記録の範囲として RUL- の文面を
        当てはめた対応表（errata_scope）を、研究の基準のコミットの記録と照らして受け付ける。"""
        links, section = self.scope_case()
        self.assertEqual(self.check({"cards": cs.load_sources()["cards"]}, DEFAULT_EFFECTS, links), [])
        # v0.31 でキュウコン（第1弾）のだいもんじ（同じ印刷の文面）を加えた
        self.assertEqual(section["errata_scope"][0]["targets"], [f"{CHARMANDER}/attack/1", f"{CHARMELEON}/attack/1", "PMCG1-020/attack/1",
                                                                 "PMCG1-022/attack/1"])

    def test_errata_scope_problems(self):
        """記録の範囲の当てはめ（errata_scope）は、記録の文の引用・記録が挙げるカードの同じ印刷の文面・対象の印刷の文面で確かめる。
        範囲に書かずに、記録が挙げていないカードにエラッタの文面を使うことは拒否する。"""
        sources = {"cards": cs.load_sources()["cards"]}
        cases = [
            ("範囲に書かない", lambda s: s["errata_scope"][0]["targets"].remove(f"{CHARMELEON}/attack/1"),
             f"{CHARMELEON}/attack/1: エラッタの記録 {RUL} がこのカードを挙げていない"),
            ("記録にない文を引く", lambda s: s["errata_scope"][0].__setitem__("scope_quote", "炎エネルギーをトラッシュするワザは同じ処理。"),
             "scope_quote が記録の notes にない"),
            ("記録の挙げるカードにない印刷の文面", lambda s: s["errata_scope"][0].__setitem__("printed_text", "自分の「炎」エネルギーをすてる。"),
             "印刷の文面 '自分の「炎」エネルギーをすてる。' のワザがない"),
            ("印刷の文面の違うワザに当てはめる（第4弾ロケット団のポニータ）",
             lambda s: (s["errata_scope"][0]["targets"].append("PMCG4-013/attack/0"),
                        s["errata_text"].__setitem__("PMCG4-013/attack/0", RUL),
                        s["adopted_printed_text"].remove("PMCG4-013/attack/0")),
             "PMCG4-013/attack/0 の印刷の文面が、研究の基準のコミットで printed_text と違う"),
            ("記録が挙げるカードを範囲に書く", lambda s: s["errata_scope"][0]["targets"].append("PMCG1-019/attack/0"), "記録の cards にある"),
            ("errata_text に挙げない", lambda s: s["errata_text"].pop("PMCG1-020/attack/1"), "errata_text に"),
            ("ほかの区分と重なる", lambda s: s["adopted_printed_text"].append(f"{CHARMELEON}/attack/1"), "ほかの区分にも入っている"),
        ]
        for name, change, expected in cases:
            with self.subTest(name=name):
                links, section = self.scope_case()
                change(section)
                self.assertProblem(self.check(sources, DEFAULT_EFFECTS, links), expected)


if __name__ == "__main__":
    unittest.main()
