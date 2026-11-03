"""実装上の仮定の一覧（docs/implementation-assumptions.json）の不変条件。

件数は写さない。確かめるのは、台帳の内部の整合（ID の一意性と参照・承認の根拠・停止の方針の台帳との対応・集計と文書の表）と、検査が誤りを見つけること
（``scripts/check_implementation_assumptions.py`` の ``check``）。候補箇所の網羅（今の木の走査との比べ）は、後の正当な文書の変更で変わるので ``--sites`` だけで行う。
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_implementation_assumptions as C


def _copy(ledger):
    return json.loads(json.dumps(ledger))


class LedgerInvariantTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(C.LEDGER.read_text(encoding="utf-8"))

    def test_invariants(self):
        self.assertEqual(C.check(self.ledger), [])

    def _first(self, ledger, pred):
        return next(i for i in ledger["items"] if pred(i))

    def test_detects_duplicate_id(self):
        broken = _copy(self.ledger)
        broken["items"].append(_copy(self._first(broken, lambda i: i["status"] != "merged_duplicate")))
        self.assertTrue(any("ID が重複" in p for p in C.check(broken)))

    def test_detects_dangling_site_item(self):
        broken = _copy(self.ledger)
        next(s for s in broken["site_dispositions"] if s["disposition"] == "merged")["item_id"] = "IA-NOT-IN-THE-LEDGER"
        self.assertTrue(any("一覧にない" in p for p in C.check(broken)))

    def test_detects_unexplained_exclusion(self):
        broken = _copy(self.ledger)
        next(s for s in broken["site_dispositions"] if s["disposition"] == "excluded").pop("reason", None)
        self.assertTrue(any("除外の理由がない" in p for p in C.check(broken)))

    def test_detects_approval_without_evidence(self):
        broken = _copy(self.ledger)
        item = self._first(broken, lambda i: i["status"] != "merged_duplicate" and i["category"] == "engine_adopted")
        item["approval"] = {"status": "user_approved"}
        problems = C.check(broken)
        self.assertTrue(any("利用者承認の根拠に" in p for p in problems))
        self.assertTrue(any("利用者指定・利用者が示したデータの訂正だけ" in p for p in problems))

    def test_detects_instruction_not_in_document(self):
        broken = _copy(self.ledger)
        item = self._first(broken, lambda i: i.get("category") == "user_specified")
        item["approval"]["evidence"]["instruction"] = "根拠の文書にない文"
        self.assertTrue(any("指定の文が根拠の文書" in p for p in C.check(broken)))

    def test_detects_non_user_mapped_as_user(self):
        broken = _copy(self.ledger)
        item = next(i for i in broken["items"] if "POLICY:implementation_assumption:1" in i.get("ledger_refs", {}).get("stop_policy_conventions", []))
        item["category"] = "user_specified"
        self.assertTrue(any("利用者指定でないのに" in p for p in C.check(broken)))

    def test_detects_unmapped_existing_convention(self):
        broken = _copy(self.ledger)
        for item in broken["items"]:
            convs = item.get("ledger_refs", {}).get("stop_policy_conventions", [])
            if "POLICY:user_specified_rules:neo1-049/power/0" in convs:
                convs.remove("POLICY:user_specified_rules:neo1-049/power/0")
        self.assertTrue(any("neo1-049/power/0" in p for p in C.check(broken)))

    def test_detects_normalization_without_equivalence(self):
        broken = _copy(self.ledger)
        self._first(broken, lambda i: i["status"] != "merged_duplicate" and i["category"] == "normalization").pop("equivalence", None)
        self.assertTrue(any("正規化の" in p for p in C.check(broken)))

    def test_detects_resolved_research_claim(self):
        broken = _copy(self.ledger)
        item = self._first(broken, lambda i: i["status"] != "merged_duplicate" and any(r.startswith("UQ-") for r in i.get("research_refs", [])))
        item["statement"] += " この論点は解決済み。"
        self.assertTrue(any("解決済みにしない" in p for p in C.check(broken)))

    def test_detects_stale_counts(self):
        broken = _copy(self.ledger)
        broken["counts"]["sites"] += 1
        self.assertTrue(any("集計" in p for p in C.check(broken)))

    def test_detects_missing_code_symbol(self):
        broken = _copy(self.ledger)
        item = self._first(broken, lambda i: i["status"] != "merged_duplicate" and any(r["path"].endswith(".py") for r in i.get("code_refs", [])))
        ref = next(r for r in item["code_refs"] if r["path"].endswith(".py"))
        ref["symbol"] = "NoSuchSymbolInThisModule"
        self.assertTrue(any("見つからない" in p for p in C.check(broken)))

    def test_detects_addendum_with_unknown_item(self):
        broken = _copy(self.ledger)
        broken.setdefault("addenda", []).append({"id": "ADD-BROKEN", "kind": "revalidation", "on": "2026-01-01", "base_commit": "0" * 40,
                                                 "ref": "docs/implementation-assumptions.md", "summary": "x", "item_ids": ["IA-NOT-IN-THE-LEDGER"]})
        self.assertTrue(any("ADD-BROKEN: 項目 IA-NOT-IN-THE-LEDGER" in p for p in C.check(broken)))

    def test_detects_fix_addendum_without_commits(self):
        broken = _copy(self.ledger)
        item = broken["items"][0]["id"]
        broken.setdefault("addenda", []).append({"id": "ADD-BROKEN-FIX", "kind": "fix", "on": "2026-01-01", "base_commit": "0" * 40,
                                                 "ref": "docs/implementation-assumptions.md", "summary": "x", "item_ids": [item], "commits": ["abc"]})
        self.assertTrue(any("ADD-BROKEN-FIX: 修正の追記に、直したコミット" in p for p in C.check(broken)))

    def test_detects_assumption_addendum_without_statement_or_approval(self):
        """後の版の実装上の仮定の追記（種類 assumption）は、仮定の文・根拠の種類・承認（なければ "none"）を持つ。承認を推測で書かない。"""
        broken = _copy(self.ledger)
        item = broken["items"][0]["id"]
        broken.setdefault("addenda", []).append({"id": "ADD-BROKEN-ASSUMPTION", "kind": "assumption", "on": "2026-01-01", "base_commit": "0" * 40,
                                                 "ref": "docs/implementation-assumptions.md", "summary": "x", "item_ids": [item], "basis": ["guess"],
                                                 "approval": "approved"})
        problems = C.check(broken)
        self.assertTrue(any("ADD-BROKEN-ASSUMPTION: 仮定の追記に statement がない" in p for p in problems))
        self.assertTrue(any("ADD-BROKEN-ASSUMPTION: 仮定の追記の根拠の種類" in p for p in problems))
        self.assertTrue(any("ADD-BROKEN-ASSUMPTION: 仮定の追記の承認" in p for p in problems))

    def test_detects_user_rule_addendum_without_quote_or_convention(self):
        """v0.140: 後の版で採った利用者の指定の追記（種類 user_rule）は、指定の文（文書にそのまま）・停止の方針の台帳の利用者指定の規約を持つ。規約は追記で対応付けてよい
        （項目の記載は書き換えない）が、どこにも対応付けない規約は見つける。"""
        broken = _copy(self.ledger)
        row = next(a for a in broken["addenda"] if a["kind"] == "user_rule")
        self.assertEqual(C.check(broken), [])
        row["approval"]["quote"] = ["文書にない指定の文"]
        row["supersedes"] = ["ADD-NOT-THERE"]
        problems = C.check(broken)
        self.assertTrue(any(f"{row['id']}: 指定の文が文書" in p for p in problems))
        self.assertTrue(any(f"{row['id']}: 置きかえた追記 ADD-NOT-THERE がない" in p for p in problems))
        broken = _copy(self.ledger)
        broken["addenda"] = [a for a in broken["addenda"] if a["kind"] != "user_rule"]
        self.assertTrue(any("CONV:USER-PRIZE-ORDER-ALWAYS-CHOSEN が、どの項目にも対応付けられていない" in p for p in C.check(broken)))

    def test_merged_duplicates_point_to_live_items(self):
        by_id = {i["id"]: i for i in self.ledger["items"]}
        for item in self.ledger["items"]:
            if item["status"] == "merged_duplicate":
                self.assertNotEqual(by_id[item["merged_into"]]["status"], "merged_duplicate", item["id"])


if __name__ == "__main__":
    unittest.main()
