"""v0.123（docs/arcanine-name-migration-v0.123.md）: 写しの元・研究の基準の移行（kyuura 2fe0bc0 → 74b3ceb。登録済みのウィンディ 2 枚の名前の訂正）。

2 章: 移行だけの段。kyuura が同じカードの画像で確かめて直した PMCG1-019「ウインディ」→「ウィンディ」・PMCG6-034「カツラのウインディ」→「カツラのウィンディ」（訂正の種類は
生成の値の誤り ``generated_value_error``）を写しの移行の段 v0.123 で受け付け、採用の記録・研究の対応表をそろえる。エンジンは画像を見ていない（kyuura の画像の照合を再利用しただけ）。
"""

from __future__ import annotations

import copy
import datetime
import json
import pathlib
import subprocess
import unittest

from kyuura_engine import deck
from kyuura_engine.cards import load_card_pool, read_extract
from scripts import check_card_sources as cs
from scripts import check_research_links as rl
from tests import helpers as H
from tests.test_baby_rules_evolution_v0_114 import extract_module

ROOT = pathlib.Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
LINKS_PATH = ROOT / "kyuura_engine" / "data" / "research_links.json"
NOW, V0121 = "74b3ceb883dd815495d13b9987433fb14b36e44d", "2fe0bc042ce187d191843819262f8036abbb343d"
ECB, V069, V097, V0114 = ("ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3", "73a169063463bbf7bcaa3137d70cbf9721d11534",
                          "e519b99e2adcc6c2cd0998569ae5ee1101de6e89")
BASE_ENGINE = "e080c9e34989fc94ad4add1e8e579738b237fd6f"  # v0.122（この版の基点）
ARCANINE, BLAINES_ARCANINE, KIND_ARCANINE = "PMCG1-019", "PMCG6-034", "neo4-021"
RENAMED = {ARCANINE: ("FIX-PMCG1-019-NAME-JA", "IMG-PMCG1-019", "ウインディ", "ウィンディ"),
           BLAINES_ARCANINE: ("FIX-PMCG6-034-NAME-JA", "IMG-PMCG6-034", "カツラのウインディ", "カツラのウィンディ")}
NEW_TARGETS = ("GD5-007", "IP2-032", "PR1-016")  # 4 章で登録するカード（移行の段では値が変わらない）
NEW_ISSUES = ("UQ-BILINGUAL-NAME-GLOSS", "UQ-MIND-GAMES-OPTIONAL", "UQ-MIND-GAMES-TRAINER-STEP", "UQ-FLASH-FACE-UP-DECK", "UQ-SWAP-PLEASE-OWNERSHIP")


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
    """2.1 節: 段 v0.123（2fe0bc0 → 74b3ceb）。過去の段の値・採用の記録の移行は書き換えない。"""

    def test_chain(self):
        module = extract_module()
        self.assertEqual((module.KYUURA_COMMIT, module.V0_121_KYUURA_COMMIT, module.V0_114_KYUURA_COMMIT), (NOW, V0121, V0114))
        self.assertEqual(module.migration_problems(), [])
        self.assertEqual([(s["id"], s["from"], s["to"], s["document"]) for s in module.KYUURA_MIGRATIONS],
                         [("v0.69", ECB, V069, "docs/equivalent-non-pack-cards-v0.69.md"), ("v0.97", V069, V097, "docs/unown-research-idfnj-v0.97.md"),
                          ("v0.114", V097, V0114, "docs/baby-rules-evolution-v0.114.md"), ("v0.121", V0114, V0121, "docs/hand-bench-attack-conditions-v0.121.md"),
                          ("v0.123", V0121, NOW, "docs/arcanine-name-migration-v0.123.md")])
        extract = read_extract()
        self.assertEqual((extract["source"]["commit"], extract["previous_source"]["commit"]), (NOW, ECB))
        self.assertEqual(extract["source_migrations"][-1]["corrections"], ["FIX-PMCG1-019-NAME-JA", "FIX-PMCG6-034-NAME-JA"])
        # v0.121 の段のあとを写しの元の定数にもどすと、写しの元を上げたときに過去の段のあとまで変わる（連鎖が切れて止まる）
        steps = module.KYUURA_MIGRATIONS
        try:
            module.KYUURA_MIGRATIONS = (*steps[:3], {**steps[3], "to": module.KYUURA_COMMIT}, steps[4])
            self.assertTrue(any("その前の段のあと" in p for p in module.migration_problems()))
        finally:
            module.KYUURA_MIGRATIONS = steps
        # 利用者が示した PR1-069 の名前の訂正（kyuura はまだ直していない）は、今の写しの元でも同じ
        self.assertEqual([(c["card_id"], c["before"], c["after"], c["source_commit"]) for c in extract["engine_user_corrections"]],
                         [("PR1-069", "？？？", "ミュウ", NOW)])

    def test_adoption_migrations_are_appended(self):
        sources = cs.load_sources()
        self.assertEqual([(m["from"], m["to"], m["on"], m["document"]) for m in sources["data_migrations"]],
                         [(ECB, V069, "2026-10-19", "docs/equivalent-non-pack-cards-v0.69.md"), (V069, V097, "2026-10-25", "docs/unown-research-idfnj-v0.97.md"),
                          (V097, V0114, "2026-10-28", "docs/baby-rules-evolution-v0.114.md"), (V0114, V0121, "2026-10-30", "docs/hand-bench-attack-conditions-v0.121.md"),
                          (V0121, NOW, "2026-10-31", "docs/arcanine-name-migration-v0.123.md")])
        self.assertEqual(cs.data_migrations(sources, read_extract())[1], [])
        # 採用したときのデータのコミットが 74b3ceb の記録は、この版で写しに加えたカード（pool_v0_123）だけ（移行の段では採用し直していない）
        self.assertEqual({card for card, record in sources["cards"].items() if record.get("kyuura_commit") == NOW}, set(read_extract().get("pool_v0_123", ())))

    def test_corrections_in_the_extract(self):
        corrections = {c["id"]: c for c in read_extract()["kyuura_corrections"] if c["migration"] == "v0.123"}
        self.assertEqual(sorted(corrections), sorted(fix for fix, *_ in RENAMED.values()))
        for card_id, (fix, image, before, after) in RENAMED.items():
            c = corrections[fix]
            self.assertEqual((c["card_id"], c["field"], c["before"], c["after"], c["basis"], c["kind"], c["image_check"], c["decided_on"]),
                             (card_id, "name.ja", before, after, "card_image_check", "generated_value_error", image, "2026-10-30"))
            self.assertEqual((c["kyuura_saw_image"], c["engine_saw_image"], c["applied_in_source"], c["previous_source"]), (True, False, NOW, V0121))
            self.assertFalse({"record", "commit", "kyuura_record"} & set(c))  # CC-・LD- の照合の記録ではない
        self.assertEqual(len(corrections[RENAMED[ARCANINE][0]]["evidence"]), 2)  # pcg-search.com となぞのばしょ（独立した 2 枚には数えない。kyuura の independence）
        self.assertEqual(len(corrections[RENAMED[BLAINES_ARCANINE][0]]["evidence"]), 1)

    @needs_history
    def test_extract_changes_only_the_two_names(self):
        """基点 v0.122 の写しの 1,355 枚のうち、変わったのは 2 枚の名前と、付随する notes・corrections だけ。"""
        before = {card["id"]: card for card in engine_json(BASE_ENGINE, "kyuura_engine/data/kyuura_cards.json")["cards"]}
        now = {card["id"]: card for card in read_extract()["cards"]}
        self.assertEqual(len(before), 1355)
        self.assertLessEqual(set(before), set(now))
        changed = {card for card in before if before[card] != now[card]}
        self.assertEqual(changed, set(RENAMED))
        for card_id, (fix, _, old, new) in RENAMED.items():
            self.assertEqual((before[card_id]["name"]["ja"], now[card_id]["name"]["ja"], now[card_id]["name"]["en"]), (old, new, before[card_id]["name"]["en"]))
            self.assertEqual(now[card_id]["pokemon"], before[card_id]["pokemon"])  # ワザ・HP など処理に使うほかの欄は同じ（ワザの文面も同じ）
            self.assertEqual([x["id"] for x in now[card_id]["corrections"]], [fix])
            self.assertNotIn("corrections", before[card_id])
        # やさしいウインディは今回の訂正の外（名前は変えていない。部分文字列で置きかえない）
        self.assertEqual((before[KIND_ARCANINE]["name"]["ja"], now[KIND_ARCANINE]["name"]["ja"]), ("やさしいウインディ", "やさしいウインディ"))

    @needs_kyuura
    def test_kyuura_difference_is_two_names(self):
        """2fe0bc0 → 74b3ceb の data/cards.json 全 1,377 件: 値が変わったのは登録済みの 2 枚の name・notes・corrections だけ。エンジンが使う欄は name.ja だけが違う。"""
        old, new = (kyuura_json(commit, "data/cards.json") for commit in (V0121, NOW))
        self.assertEqual({k: v for k, v in old.items() if k != "cards"}, {k: v for k, v in new.items() if k != "cards"})
        self.assertEqual([c["id"] for c in old["cards"]], [c["id"] for c in new["cards"]])
        self.assertEqual(len(new["cards"]), 1377)
        before = {c["id"]: c for c in old["cards"]}
        changed = {c["id"]: {k for k in set(c) | set(before[c["id"]]) if c.get(k) != before[c["id"]].get(k)} for c in new["cards"] if c != before[c["id"]]}
        self.assertEqual(changed, {ARCANINE: {"name", "notes", "corrections"}, BLAINES_ARCANINE: {"name", "notes", "corrections"}})
        module = extract_module()
        after = {c["id"]: c for c in new["cards"]}
        for card_id in RENAMED:
            used = [f for f in module.FIELDS_USED_BY_ENGINE if "[" not in f and module.field_or_absent(before[card_id], f) != module.field_or_absent(after[card_id], f)]
            self.assertEqual(used, ["name.ja"])
        for card_id in NEW_TARGETS:
            self.assertEqual(before[card_id], after[card_id], card_id)


class GeneratedValueKindTest(unittest.TestCase):
    """2.2 節: 生成の値の誤り（``generated_value_error``）の受け付け。根拠・欄・前後の値を確かめ、未知の種類・ほかの種類への書きかえ・画像の根拠の違いを受け付けない。"""

    def test_kind_rules_without_kyuura(self):
        module = extract_module()
        self.assertIn("generated_value_error", module.CORRECTION_KINDS)
        self.assertEqual(module.GENERATED_VALUE_FIELDS, ("name.ja",))
        good = next(c for c in module.KYUURA_CORRECTIONS if c["id"] == "FIX-PMCG1-019-NAME-JA")
        self.assertEqual(module.generated_value_problems("x", good), [])
        self.assertTrue(module.generated_value_problems("x", {**good, "basis": "user_provided"}))
        self.assertTrue(module.generated_value_problems("x", {**good, "field": "pokemon.hp"}))
        self.assertTrue(module.generated_value_problems("x", {**good, "before": None}))  # 欠けを埋める修正ではない
        self.assertTrue(module.generated_value_problems("x", {**good, "after": good["before"]}))
        self.assertEqual(module.generated_value_problems("x", {**good, "kind": "transcription_error"}), [])  # ほかの種類はこの確かめの外（台帳と照らす）

    @needs_kyuura
    def test_ledger_and_image_checks(self):
        module = extract_module()
        source = module.read_kyuura_cards(KYUURA)
        previous = json.loads(module._show(KYUURA, module.PREVIOUS_KYUURA_COMMIT, module.KYUURA_PATH).decode("utf-8"))
        pool = module.all_pool_cards() + module.REFERENCE_ONLY
        self.assertEqual(module.kyuura_correction_problems(KYUURA, source, previous, pool), [])
        self.assertEqual(module.migration_copy_problems(KYUURA, source, previous, pool), [])
        original = list(module.KYUURA_CORRECTIONS)
        index = next(i for i, c in enumerate(original) if c["id"] == "FIX-PMCG1-019-NAME-JA")

        def problems_with(**changes):
            module.KYUURA_CORRECTIONS[:] = [*original[:index], {**original[index], **changes}, *original[index + 1:]]
            try:
                return module.kyuura_correction_problems(KYUURA, source, previous, pool)
            finally:
                module.KYUURA_CORRECTIONS[:] = original

        # 種類を転記の誤りに書きかえると台帳と合わない。未知の種類は扱えない
        self.assertTrue(any("台帳の kind" in p for p in problems_with(kind="transcription_error")))
        unknown = problems_with(kind="unknown_error")
        self.assertTrue(any("台帳の kind" in p for p in unknown) and any("扱えない" in p for p in unknown))
        # 画像の根拠（URL・sha256・取得日）・画像の照合の記録が台帳と違えば受け付けない
        evidence = [dict(original[index]["evidence"][0], image_sha256="0" * 64), original[index]["evidence"][1]]
        self.assertTrue(any("evidence" in p for p in problems_with(evidence=evidence)))
        self.assertTrue(any("evidence" in p for p in problems_with(evidence=original[index]["evidence"][:1])))
        self.assertTrue(any("画像の照合の記録" in p for p in problems_with(image_check="IMG-PMCG6-034")))
        # 段の前後の値・段が合わなければ受け付けない（v0.121 の段の訂正にしない）
        self.assertTrue(any("移行の段 v0.123 の前の写しの元（2fe0bc0）の値が 'ウインデイ' ではない" in p for p in problems_with(before="ウインデイ")))
        self.assertTrue(any("移行の段 v0.121 のあと（2fe0bc0）の値が 'ウィンディ' ではない" in p for p in problems_with(migration="v0.121")))
        # 台帳の訂正を挙げていなければ、知らない修正として書き出さない
        module.KYUURA_CORRECTIONS[:] = [c for c in original if c["id"] != "FIX-PMCG1-019-NAME-JA"]
        try:
            missing = module.kyuura_correction_problems(KYUURA, source, previous, pool)
            self.assertTrue(any("FIX-PMCG1-019-NAME-JA" in p and "挙げていない" in p for p in missing))
            self.assertTrue(any("PMCG1-019" in p for p in module.migration_copy_problems(KYUURA, source, previous, pool)))  # 名前の違いを見落とさない
        finally:
            module.KYUURA_CORRECTIONS[:] = original


class AdoptionRecordTest(unittest.TestCase):
    """2.3 節: 採用の記録。名前を写しにそろえ、報告事項の解決を日付つきで追記した。当時の外部照合の値・日付・コミットは書き換えない。"""

    def test_names_issues_and_external_checks(self):
        cards = cs.load_sources()["cards"]
        for card_id, (fix, image, old, new) in RENAMED.items():
            record = cards[card_id]
            self.assertEqual((record["name_ja"], record["kyuura_commit"], record["recorded_on"]), (new, ECB, "2026-10-15"))
            [check] = record["external_checks"]
            self.assertEqual((check["kyuura_commit"], check["checked_on"], check["result"]), (ECB, "2026-10-15", "differences"))
            self.assertEqual([(d["field"], d["kyuura"], d["pcg_search"], d["affects_behavior"]) for d in check["differences"]], [("name.ja", old, new, False)])
            [issue] = record["issues"]
            self.assertIn("どちらが印刷の表記か", issue["question"])
            self.assertIn("2026-10-31（v0.123", issue["note"])
            self.assertTrue(all(text in issue["note"] for text in (fix, image, "解決した", "画像を読んでおらず", "エンジンは今回も画像を見ていない")))
            self.assertEqual(record["kyuura_records"], H.kyuura_records_since_v0_69(card_id, ["RUL-ENERGY-DISCARD-ATTACKS"] if card_id == ARCANINE else []))

    def test_check_before_the_correction_uses_the_before_value(self):
        """2026-10-15 に ecb2d69 と照らした違いの kyuura の値は、訂正の前の値（段 v0.123 の前）なので受け付ける。今の写しの元と照らしたことにすると受け付けない。"""
        sources = cs.load_sources()
        extract = read_extract()
        earlier, _ = cs.data_migrations(sources, extract)
        cards = {c["id"]: c for c in extract["cards"]}
        corrections = {(c["card_id"], c["field"]): c for c in extract["kyuura_corrections"]}
        today = datetime.date(2026, 10, 31)
        check = sources["cards"][ARCANINE]["external_checks"][0]
        found = cs.check_problems("x", check, cards[ARCANINE], extract["source"]["commit"], today, corrections, earlier)
        self.assertEqual(found, [])
        moved = dict(check, kyuura_commit=NOW)
        self.assertTrue(any("kyuura の値が写しの値と違う" in p for p in cs.check_problems("x", moved, cards[ARCANINE], extract["source"]["commit"], today, corrections, earlier)))
        other = copy.deepcopy(check)
        other["differences"][0]["kyuura"] = "ウインデイ"
        self.assertTrue(any("kyuura の値が写しの値と違う" in p for p in cs.check_problems("x", other, cards[ARCANINE], extract["source"]["commit"], today, corrections, earlier)))

    def test_records_added_by_the_research_commit(self):
        cards = cs.load_sources()["cards"]
        for card_id, added in H.V0_123_KYUURA_RECORDS_ADDED.items():
            self.assertLessEqual(set(added), set(cards[card_id]["kyuura_records"]), card_id)
        # やさしいウインディ（neo4-021）は裁定の related_cards（名前の数え方には関わらない別の名前）。名前・処理は変えていない
        self.assertEqual(cards[KIND_ARCANINE]["name_ja"], "やさしいウインディ")


class ResearchLinksTest(unittest.TestCase):
    """2.4 節: 研究の対応表。論点 74 → 79。新しい 5 論点と、既存の 2 論点に加わった事例。kyuura の 79 件を停止コード・未解決の数にそろえない。"""

    @classmethod
    def setUpClass(cls):
        cls.links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))

    def test_commits_and_counts(self):
        links = self.links
        self.assertEqual((links["research_commit"], links["card_data_commit"], links["research_branch"]), (NOW, NOW, "claude/v0122-names-text-trainer-procedures"))
        self.assertEqual((links["counts"]["kyuura_issues"], links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (79, 292, 293))
        self.assertEqual(links["engine_import_id"], "ENGINE-46A3E2E")

    def test_new_cases(self):
        added = [c for c in self.links["kyuura_cases_without_engine_ruling"]["cases"] if "v0.123 で研究の基準を 74b3ceb に上げて結んだ" in c.get("note", "")]
        self.assertEqual(len(added), 25)
        self.assertEqual({c["kyuura_issue"] for c in added}, {*NEW_ISSUES, "UQ-STATED-COUNT-SHORT", "UQ-CHAOS-GYM-BORROWED-TURN"})
        unregistered = {(c["kyuura_issue"], c["card_id"]) for c in added if c["engine"] == {"unregistered": True}}
        self.assertEqual({card for _, card in unregistered}, {"PR1-075", "PR1-077", "PR1-027", "ES2-035", "neo1-049"})
        self.assertEqual(len(unregistered), 10)
        required = {(c["kyuura_issue"], c["card_id"]): tuple(c["engine"]["requires_unregistered"]) for c in added if "requires_unregistered" in c["engine"]}
        self.assertEqual(len(required) + len(unregistered), 25)
        self.assertEqual(set(required.values()), {("PR1-075", "PR1-077"), ("ES2-035", "neo1-049"), ("neo1-049",), ("PR1-027",)})
        self.assertFalse([c for c in added if "stop_codes" in c["engine"] or "codeless_question" in c["engine"]])  # 新しい停止コード・問いを作っていない
        pool = load_card_pool()
        for (_, card), others in required.items():
            self.assertIn(card, pool.playable_ids, card)
            self.assertFalse(set(others) & pool.playable_ids, card)

    def test_requires_unregistered_is_checked(self):
        """``requires_unregistered``: 挙げたカードは、同じ論点の事例のカードで、登録していない。事例のカードは登録している。"""
        from kyuura_engine.effects import DEFAULT_EFFECTS

        issues = {"UQ-X": {"cases": [{"card_id": "PMCG5-087", "target": {"kind": "trainer"}}, {"card_id": "PR1-027", "target": {"kind": "trainer"}}]}}

        def problems(engine, card="PMCG5-087"):
            links = {"stop_codes": {}, "codeless_questions": {}, "kyuura_cases_without_engine_ruling": {"cases": [
                {"kyuura_issue": "UQ-X", "card_id": card, "target": "trainer", "engine": engine},
                {"kyuura_issue": "UQ-X", "card_id": "PR1-027" if card != "PR1-027" else "PMCG5-087", "target": "trainer",
                 "engine": {"unregistered": True} if card != "PR1-027" else {"requires_unregistered": ["PR1-027"]}}]}}
            return rl.unlinked_case_problems(links, issues, DEFAULT_EFFECTS)

        self.assertEqual(problems({"requires_unregistered": ["PR1-027"]}), [])
        self.assertTrue(any("登録されている" in p for p in problems({"requires_unregistered": ["PMCG1-019"]})))  # 登録したカード（同じ論点の事例でもない）
        self.assertTrue(any("事例のカードではない" in p for p in problems({"requires_unregistered": ["neo1-049"]})))
        self.assertTrue(any("重ならないリスト" in p for p in problems({"requires_unregistered": []})))
        self.assertTrue(any("重ならないリスト" in p for p in problems({"requires_unregistered": ["PMCG5-087"]})))  # 事例のカードそのもの
        self.assertTrue(any("ちょうど 1 つ" in p for p in problems({"requires_unregistered": ["PR1-027"], "unregistered": True})))

    @needs_kyuura
    def test_links_agree_with_kyuura(self):
        self.assertEqual(rl.check(KYUURA), [])


class NameTest(unittest.TestCase):
    """2.5 節: 移行のあとの名前。新しい名前を別名として足さず、2 枚の名前が置きかわる（読み替えの表・正規化は加えない）。"""

    def test_names_in_the_pool(self):
        pool = load_card_pool()
        self.assertEqual((pool.get(ARCANINE).name_ja, pool.get(BLAINES_ARCANINE).name_ja, pool.get(KIND_ARCANINE).name_ja),
                         ("ウィンディ", "カツラのウィンディ", "やさしいウインディ"))
        self.assertEqual(dict(deck.SAME_NAME_SPELLINGS), {"ポケモン図鑑HANDY505": "ポケモン図鑑 HANDY505"})
        names = {pool.get(card).name_ja for card in pool.playable_ids if pool.get(card).category == "pokemon"}
        self.assertTrue({"ウィンディ", "カツラのウィンディ", "やさしいウインディ"} <= names)
        self.assertFalse({"ウインディ", "カツラのウインディ"} & names)
        self.assertEqual(len(names), 509)
        self.assertEqual(deck.same_name("ウィンディ"), "ウィンディ")
        self.assertNotEqual(deck.same_name("ウィンディ"), deck.same_name("カツラのウィンディ"))
