"""v0.128（docs/catalog-scope-migration-v0.128.md）: 写しの元・研究の基準の移行（kyuura 57d01f4 → 71d1728）と、目録の分類から求める通常対戦の対象。

2 章: 移行だけの段。kyuura の data/cards.json は既存の欄の値が全件同じで、目録の分類の 3 つの欄が加わっただけ。3 章: 分類の欄はカードの写す欄に入れず、
書き出しの ``catalog_scope`` に対象の数と対象外の記録を残す。カードは登録せず、処理も変えない。
"""

from __future__ import annotations

import copy
import csv
import io
import json
import pathlib
import subprocess
import unittest

from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.deck import deck_problems
from kyuura_engine.engine import new_game
from kyuura_engine.errors import DeckValidationError
from scripts import check_card_sources as cs
from tests import helpers as HP
from tests.release_catalog import cards_after
from tests.test_baby_rules_evolution_v0_114 import extract_module

ROOT = pathlib.Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
LINKS_PATH = ROOT / "kyuura_engine" / "data" / "research_links.json"
NOW, V0126 = "71d1728938fb4c8fefde9b82779cdef74beb612d", "57d01f45cfb8b086d03dc0525b329cf6adeff69b"
BASE_ENGINE = "355589d432b39f8c985aafd55b8f9712ac1e9c91"  # この版の基点（v0.127 の最後のコミット。main cdde860 の木と同じ）
SCOPE_FIELDS = ["catalog_class", "engine_scope", "engine_scope_reason"]
EXCLUDED = {"PR1-038": ("タッチ交代！", "special_rule", "kangaskhan_rule"),
            "PRN-048": ("タッチ世代交代！", "special_rule", "kangaskhan_rule"),
            "PR1-079": ("カードトレーナー認定証", "award", "standard")}


def needs_kyuura(test):
    return unittest.skipUnless((KYUURA / ".git").exists(), "../kyuura がない")(test)


def needs_history(test):
    return unittest.skipUnless((ROOT / ".git").exists(), "このリポジトリの git の履歴がない（取り出した木）")(test)


def kyuura_json(commit: str, path: str):
    return json.loads(subprocess.check_output(["git", "-C", str(KYUURA), "show", f"{commit}:{path}"]))


def engine_json(commit: str, path: str):
    return json.loads(subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"]))


# ---------------------------------------------------------------- 2 章: 移行
class MigrationChainTest(unittest.TestCase):
    """2.1 節: 段 v0.128（57d01f4 → 71d1728）。過去の段の値・採用の記録の移行は書き換えない。この段に訂正はない。"""

    def test_chain(self):
        module = extract_module()
        self.assertEqual((module.KYUURA_COMMIT, module.V0_126_KYUURA_COMMIT), (NOW, V0126))
        self.assertEqual(module.migration_problems(), [])
        self.assertEqual([(s["id"], s["from"], s["to"]) for s in module.KYUURA_MIGRATIONS][-2:],
                         [("v0.126", module.V0_125_KYUURA_COMMIT, V0126), ("v0.128", V0126, NOW)])
        extract = read_extract()
        self.assertEqual(extract["source"]["commit"], NOW)
        self.assertEqual(extract["source_migrations"][-1],
                         {"id": "v0.128", "from": V0126, "to": NOW, "document": "docs/catalog-scope-migration-v0.128.md", "corrections": []})
        self.assertFalse([c for c in extract["kyuura_corrections"] if c["migration"] == "v0.128"])
        self.assertEqual(HP.CARD_DATA_MIGRATIONS[-1], (V0126, NOW))
        self.assertEqual([(c["card_id"], c["source_commit"]) for c in extract["engine_user_corrections"]], [("PR1-069", NOW)])

    def test_adoption_migrations_are_appended(self):
        sources = cs.load_sources()
        last = sources["data_migrations"][-1]
        self.assertEqual((last["from"], last["to"], last["on"], last["document"]),
                         (V0126, NOW, "2026-11-01", "docs/catalog-scope-migration-v0.128.md"))
        self.assertEqual(len(sources["data_migrations"]), 9)
        self.assertEqual(cs.data_migrations(sources, read_extract())[1], [])
        # 移行の段では採用し直していない（採用したときのデータのコミットが 71d1728 の記録はない）
        # v0.129: 写しの元を変えずに pool_v0_129 のカツラのクイズ その1を 71d1728 で採用した（tests/test_blaines_quiz_heights_v0_129.py）
        self.assertEqual({card for card, record in sources["cards"].items() if record.get("kyuura_commit") == NOW}, cards_after(read_extract(), "0.128"))
        # 対象外の 3 件は登録しておらず、採用の記録もない
        self.assertFalse(set(EXCLUDED) & set(sources["cards"]))

    def test_research_links(self):
        links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
        self.assertEqual((links["research_commit"], links["card_data_commit"], links["research_branch"]), (NOW, NOW, "main"))

    @needs_history
    def test_extract_cards_are_unchanged(self):
        """基点の写しのカード（1,368 枚）は全欄が同じ。変わったのは写しの元の記録・移行の段・利用者の訂正の写しの元のコミットと、新しい catalog_scope だけ。"""
        before = engine_json(BASE_ENGINE, "kyuura_engine/data/kyuura_cards.json")
        after = read_extract()
        # v0.129: 後の版で写しに加えたカード（pool_v0_129）は除いて比べる
        later = cards_after(after, "0.128")
        self.assertEqual(before["cards"], [card for card in after["cards"] if card["id"] not in later])
        self.assertEqual(len(after["cards"]) - len(later), 1368)
        # v0.129: エンジンが処理に使う欄の一覧に pokemon.dex を加えた（docs/blaines-quiz-heights-v0.129.md 2 章。カードの写す欄・値は変えていない）
        self.assertEqual(after["fields_used_by_engine"], before["fields_used_by_engine"] + ["pokemon.dex"])
        self.assertEqual(sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key)),
                         # v0.129: cards（pool_v0_129 の 1 枚を加えた）と pool_v0_129 も変わる。v0.130: pool_v0_130（とりかえっこプリーズ）も
                         ["cards", "catalog_scope", "engine_user_corrections", "fields_used_by_engine", "pool_v0_129", "pool_v0_130", "source", "source_migrations"])
        self.assertEqual(before["source_migrations"], after["source_migrations"][:-1])
        self.assertEqual(after["fields_copied"], before["fields_copied"])  # 分類の 3 つの欄はカードの写す欄に加えていない
        self.assertFalse(set(SCOPE_FIELDS) & set(after["fields_copied"] + after["fields_copied_when_present"]))

    @needs_kyuura
    def test_kyuura_cards_differ_only_by_scope_fields(self):
        """57d01f4 → 71d1728 の data/cards.json: 記録の集合・並び・既存の欄の値は全件同じで、全件に 3 つの欄が加わった。"""
        old, new = kyuura_json(V0126, "data/cards.json"), kyuura_json(NOW, "data/cards.json")
        self.assertEqual({k: v for k, v in old.items() if k != "cards"}, {k: v for k, v in new.items() if k != "cards"})
        self.assertEqual([c["id"] for c in old["cards"]], [c["id"] for c in new["cards"]])
        for a, b in zip(old["cards"], new["cards"]):
            self.assertEqual(sorted(set(b) - set(a)), sorted(SCOPE_FIELDS), a["id"])
            self.assertEqual(a, {k: v for k, v in b.items() if k not in SCOPE_FIELDS}, a["id"])


# ---------------------------------------------------------------- 3 章: 分類から求める対象
class CatalogScopeTest(unittest.TestCase):
    """3 章: 対象外の記録は kyuura の明示の分類から求める（カード id ごとの例外の表を持たない）。"""

    def test_extract_catalog_scope(self):
        scope = read_extract()["catalog_scope"]
        self.assertEqual((scope["commit"], scope["fields"], scope["target_rule"]),
                         (NOW, SCOPE_FIELDS, {"catalog_class": "battle", "engine_scope": "target"}))
        self.assertEqual(scope["counts"], {"records": 1377, "target": 1374, "excluded": 3})
        records = {r["id"]: r for r in scope["excluded_records"]}
        self.assertEqual({card: (r["name_ja"], r["catalog_class"], r["play_scope"]) for card, r in records.items()}, EXCLUDED)
        for card, record in records.items():
            self.assertEqual(record["engine_scope"], "excluded", card)
            self.assertTrue(record["engine_scope_reason"], card)  # 理由がある
            self.assertEqual(record["product_group"], "promo", card)
        # タッチ系の 2 枚は専用ルールで使うカード（理由に専用ルールのことが残る。使用禁止とは書かない）
        for card in ("PR1-038", "PRN-048"):
            self.assertIn("専用ルールで使う", records[card]["engine_scope_reason"])
            self.assertNotIn("禁止", records[card]["engine_scope_reason"])

    def test_scope_is_not_a_card_id_table(self):
        module = extract_module()
        self.assertFalse([name for name in dir(module) if "EXCLUDED_IDS" in name or "SCOPE_EXCEPTIONS" in name])
        source_text = (ROOT / "scripts" / "extract_kyuura_cards.py").read_text(encoding="utf-8")
        for card in EXCLUDED:
            self.assertNotIn(f'"{card}"', source_text)

    @needs_kyuura
    def test_problems_are_reported(self):
        """分類の欠け・知らない値・理由の食い違い・対象外のカードを写しに入れること・engine_targets.json との食い違いを、書き出しの前に止める。"""
        module = extract_module()
        source = kyuura_json(NOW, "data/cards.json")
        pool = module.all_pool_cards() + module.REFERENCE_ONLY
        self.assertEqual(module.catalog_scope_problems(KYUURA, source, pool), [])

        def problems(change, cards=pool):
            changed = copy.deepcopy(source)
            change({c["id"]: c for c in changed["cards"]})
            return module.catalog_scope_problems(KYUURA, changed, cards)

        self.assertTrue(problems(lambda by: by["PMCG1-016"].pop("engine_scope")))
        self.assertTrue(problems(lambda by: by["PMCG1-016"].update(catalog_class="jumbo")))
        self.assertTrue(problems(lambda by: by["PR1-079"].update(engine_scope_reason=None)))
        self.assertTrue(problems(lambda by: by["PMCG1-016"].update(engine_scope_reason="理由")))
        self.assertTrue(problems(lambda by: by["PR1-079"].update(engine_scope="target", engine_scope_reason=None)))
        # 未判断（undecided）の記録も対象ではない（engine_targets.json の cards と食い違うので止まる）
        self.assertTrue(problems(lambda by: by["PMCG1-016"].update(engine_scope="undecided", engine_scope_reason="未判断")))
        # 対象外の記録を写しのカードに入れると止まる
        self.assertTrue(any("PR1-038" in p for p in problems(lambda by: None, pool + ["PR1-038"])))


# ---------------------------------------------------------------- 4 章: 数
class CountTest(unittest.TestCase):
    def test_supported_count_is_unchanged(self):
        pool = load_card_pool()
        # v0.129: 後の版で加えたカード（pool_v0_129）を外すと 1,368 枚
        self.assertEqual(len(pool.playable_ids - cards_after(read_extract(), "0.128")), 1368)
        self.assertFalse(set(EXCLUDED) & set(pool.definitions))
        self.assertNotIn("PR1-015", pool.definitions)  # 目録だけの行（non_game_items）は写しにない


# ---------------------------------------------------------------- 4 章: デッキの検査・対象外の記録の混入の防止
FILLER = ["PMCG1-016"] * 4 + ["PMCG1-097"] * 55  # ポニータ 4・草エネルギー 55（あと 1 枚で 60 枚）


class DeckScopeTest(unittest.TestCase):
    """4 章: 対象外の記録は、知らないカード・未対応のカードと分けて、分類と理由を示して拒否する（公式の使用禁止とは書かない）。"""

    def test_excluded_records_are_rejected_with_reason(self):
        pool = load_card_pool()
        for card, (name, catalog_class, play_scope) in EXCLUDED.items():
            problems = deck_problems(FILLER + [card], pool)
            self.assertEqual(len(problems), 1, problems)
            problem = problems[0]
            self.assertTrue(problem.startswith(f"OUT_OF_ENGINE_SCOPE: {card} {name}（"), problem)
            self.assertIn(f"目録の分類 {catalog_class}", problem)
            self.assertIn(f"使用範囲 {play_scope}", problem)
            self.assertIn(pool.excluded[card].reason, problem)
            self.assertNotIn("禁止", problem)
        self.assertEqual(deck_problems(FILLER + ["PMCG1-016"], pool), ["TOO_MANY_COPIES: 「ポニータ」が 5 枚（同じ名前は 4 枚まで）"])

    def test_new_game_refuses_excluded_records(self):
        deck = FILLER + ["PR1-038"]
        with self.assertRaises(DeckValidationError) as caught:
            new_game(deck, FILLER + ["PMCG1-097"], seed=1)
        self.assertEqual(len(caught.exception.problems), 1)
        self.assertTrue(caught.exception.problems[0].startswith("player 0: OUT_OF_ENGINE_SCOPE: PR1-038 タッチ交代！"))

    def test_catalog_only_rows_stay_unknown(self):
        # 目録だけの行（data/cards.json にない non_game_items・KC-）は写しにも対象外の記録にもない（知らないカード）
        pool = load_card_pool()
        for card in ("PR1-015", "KC-0001"):
            self.assertNotIn(card, pool.excluded)
            self.assertEqual(deck_problems(FILLER + [card], pool), [f"UNKNOWN_CARD: このエンジンのカードデータにないカード {[card]}"])

    def test_excluded_is_separate_from_definitions(self):
        extract = read_extract()
        pool = load_card_pool()
        self.assertEqual(set(pool.excluded), set(EXCLUDED))
        self.assertFalse(set(pool.excluded) & set(pool.definitions))
        broken = dict(extract, catalog_scope=dict(extract["catalog_scope"], excluded_records=[
            *extract["catalog_scope"]["excluded_records"], dict(extract["catalog_scope"]["excluded_records"][0], id="PMCG1-016")]))
        with self.assertRaises(ValueError):
            pool_from_extract(broken)


class CatalogMixingTest(unittest.TestCase):
    """4 章: 対戦で使える集合・クイズの名前の候補・マチスの秘策の試すカードに、対象外の記録・目録だけの行が入らない。"""

    @needs_kyuura
    def test_playable_cards_are_catalog_targets(self):
        records = kyuura_json(NOW, "data/cards.json")["cards"]
        targets = {c["id"] for c in records if c["catalog_class"] == "battle" and c["engine_scope"] == "target"}
        pool = load_card_pool()
        self.assertLessEqual(set(pool.definitions), targets)
        # kyuura の目録の一覧（CSV）の、対象でない行（非対戦の項目・目録だけの行・対象外の 3 件）はどれも写しにない
        rows = list(csv.DictReader(io.StringIO(subprocess.check_output(
            ["git", "-C", str(KYUURA), "show", f"{NOW}:data/cards.csv"]).decode("utf-8"))))
        outside = {row["id"] for row in rows if (row["catalog_class"], row["engine_scope"]) != ("battle", "target")}
        self.assertEqual(len(outside), 45)  # 対象外の記録 3・non_game_items 18・KC- 24
        self.assertFalse(outside & set(pool.definitions))
        self.assertEqual(outside & {c["id"] for c in records}, set(EXCLUDED))

    def test_identity_candidates_and_quiz_names(self):
        from kyuura_engine import engine
        from kyuura_engine.effects import quiz_answer_names

        pool = load_card_pool()
        candidates = engine._identity_candidates(pool)
        self.assertFalse(set(candidates) & (set(EXCLUDED) | {"PR1-015"}))
        self.assertLessEqual(set(candidates), pool.playable_ids)
        state = new_game(FILLER + ["PMCG1-097"], FILLER + ["PMCG1-097"], seed=1)
        names = set(quiz_answer_names(state))
        self.assertFalse(names & ({name for name, _, _ in EXCLUDED.values()} | {"ポケモンイラストレーター"}))



class DocumentTest(unittest.TestCase):
    """版の文書・対応状況・裁定・データの来歴・README の v0.128。"""

    def test_documents(self):
        doc = (ROOT / "docs" / "catalog-scope-migration-v0.128.md").read_text(encoding="utf-8")
        for heading in ("## 1. 開始点と範囲", "## 2. 写しの元・研究の基準の移行（57d01f4 → 71d1728）", "## 3. 分類の欄の扱い（写しに入れない理由）",
                        "## 4. エンジン: 対象外の記録のデッキの拒否と、混入の防止", "## 5. 数", "## 6. 保持した v0.127 の仕様", "## 7. 検証",
                        "## 8. 制限・行っていない検証・kyuura への報告事項"):
            self.assertIn(heading + "\n", doc)
        self.assertIn("公式の使用禁止・裁定の変更・エラッタではありません", doc)
        self.assertRegex((ROOT / "README.md").read_text(encoding="utf-8"), r"\n- v0\.128（(今のエンジンの版。)?`kyuura_engine` の版は 0\.128\.0）: kyuura の目録の分類")
        self.assertIn("## v0.128: kyuura の目録の分類の取り込みと、通常対戦の対象の整理\n", (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8"))
        self.assertIn("### v0.128: 目録の分類と通常対戦の対象", (ROOT / "docs" / "rules-2000-02-14.md").read_text(encoding="utf-8"))
        self.assertIn("## v0.128: 写しの元・研究の基準を kyuura 71d1728 に上げる移行\n", (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
