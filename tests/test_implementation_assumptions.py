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

    def test_merged_duplicates_point_to_live_items(self):
        by_id = {i["id"]: i for i in self.ledger["items"]}
        for item in self.ledger["items"]:
            if item["status"] == "merged_duplicate":
                self.assertNotEqual(by_id[item["merged_into"]]["status"], "merged_duplicate", item["id"])


if __name__ == "__main__":
    unittest.main()
