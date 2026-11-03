"""正規化の成立条件の再検証（docs/normalization-revalidation.json）の不変条件。

件数は写さない。確かめるのは、台帳の内部の整合（``scripts/check_normalization_revalidation.py`` の ``check``）と、
検査が対応の漏れ・不整合を見つけること（台帳を壊した写しで確かめる）。
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_normalization_revalidation as R


def _copy(value):
    return json.loads(json.dumps(value))


class RevalidationLedgerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = R.load(R.LEDGER)
        cls.source = R.load(R.SOURCE)

    def problems(self, ledger, source=None):
        return R.check(ledger, source if source is not None else self.source)

    def test_invariants(self):
        self.assertEqual(self.problems(self.ledger), [])

    def test_detects_missing_primary_item(self):
        broken = _copy(self.ledger)
        primary = R.primary_ids(self.source)
        broken["items"] = [i for i in broken["items"] if i["item_id"] != primary[0]]
        self.assertTrue(any(f"主対象 {primary[0]}" in p for p in self.problems(broken)))

    def test_detects_new_premise_discrepancy_in_source(self):
        source = _copy(self.source)
        source["discrepancies"].append({"id": "DISC-NEW-PREMISE", "kind": "premise_changed", "item_ids": [source["items"][0]["id"]], "summary": "x"})
        self.assertTrue(any("DISC-NEW-PREMISE の対応がない" in p for p in self.problems(self.ledger, source)))

    def test_detects_mapping_that_differs_from_source(self):
        broken = _copy(self.ledger)
        row = next(m for m in broken["discrepancy_mapping"] if m["item_ids"])
        row["item_ids"] = row["item_ids"] + ["IA-SOMETHING-ELSE"]
        self.assertTrue(any("項目の対応が元の一覧と違う" in p for p in self.problems(broken)))

    def test_detects_extended_without_reason(self):
        broken = _copy(self.ledger)
        item = next(i for i in broken["items"] if i["scope"] == "extended")
        item.pop("scope_reason", None)
        self.assertTrue(any("範囲を広げた理由がない" in p for p in self.problems(broken)))

    def test_detects_classification_inconsistent_with_axes(self):
        broken = _copy(self.ledger)
        item = next(i for i in broken["items"] if any(a["verdict"] == "differs" for a in i["axes"].values()))
        item["classification"] = "A"
        self.assertTrue(any("分類 A なのに違う軸がある" in p for p in self.problems(broken)))
        for axis in item["axes"].values():
            if axis["verdict"] == "differs":
                axis["verdict"] = "same"
        item["classification"] = "C"
        self.assertTrue(any("分類 C なのに違う軸がない" in p for p in self.problems(broken)))

    def test_detects_missing_axis(self):
        broken = _copy(self.ledger)
        broken["items"][0]["axes"].pop("visible_info")
        self.assertTrue(any("軸 visible_info がない" in p for p in self.problems(broken)))

    def test_detects_legal_reach_claim_without_legal_repro(self):
        broken = _copy(self.ledger)
        item = broken["items"][0]
        item["reachability"]["status"] = "reached_legal_ops"
        item["reachability_level"] = "legal_play_confirmed"
        item["repro"] = [r for r in item.get("repro", []) if r["kind"] != "legal_ops"]
        problems = self.problems(broken)
        self.assertTrue(any("その種類の再現がない" in p for p in problems))
        self.assertTrue(any("合法な操作列の再現がない" in p for p in problems))

    def test_detects_run_claim_not_in_execution_record(self):
        broken = _copy(self.ledger)
        item = next(i for i in broken["items"] if i.get("test_refs"))
        ref = item["test_refs"][0]
        ref["run"] = True
        broken["tests_executed"] = []
        self.assertTrue(any("実行の記録にない" in p for p in self.problems(broken)))

    def test_detects_unscoped_claim(self):
        broken = _copy(self.ledger)
        broken["items"][0]["classification_reason"] = "到達不能"
        self.assertTrue(any("範囲を添えない「到達不能」" in p for p in self.problems(broken)))
        broken["items"][0]["classification_reason"] = "到達不能とはしない（未再現）"
        self.assertFalse(any("範囲を添えない" in p for p in self.problems(broken)))
        broken["items"][0]["unconfirmed"] = ["網羅"]  # 未確認の事項の欄は、確かめた範囲の主張ではない
        self.assertFalse(any("範囲を添えない" in p for p in self.problems(broken)))

    def test_detects_missing_code_symbol(self):
        broken = _copy(self.ledger)
        item = next(i for i in broken["items"] if any(r["path"].endswith(".py") and r.get("symbol") for r in i["code_refs"]))
        next(r for r in item["code_refs"] if r["path"].endswith(".py") and r.get("symbol"))["symbol"] = "NoSuchSymbolInThisModule"
        self.assertTrue(any("見つからない" in p for p in self.problems(broken)))

    def test_approval_scope_is_only_the_three_cards(self):
        broken = _copy(self.ledger)
        comp = next(c for c in broken["approval_supplement"]["components"] if c["class"] == "quote_missing")
        comp["cards"] = comp["cards"] + ["PMCG1-001"]
        self.assertTrue(any("3 枚の移管の外に及ぶ" in p for p in self.problems(broken)))
        broken = _copy(self.ledger)
        broken["approval_supplement"]["cards"][0]["name_ja"] = "違う名前"
        self.assertTrue(any("写しの" in p for p in self.problems(broken)))

    def test_source_addendum_must_match(self):
        source = _copy(self.source)
        source["addenda"] = [a for a in source.get("addenda", []) if a.get("ref") != "docs/normalization-revalidation.json"]
        self.assertTrue(any("addenda" in p for p in self.problems(self.ledger, source)))

    def test_followup_must_match_the_source_addendum(self):
        """後の修正の追記（種類 fix）は、直したコミット（40 桁）と再検証の項目を持ち、元の一覧の同じ ID の追記と一致する。"""
        broken = _copy(self.ledger)
        broken["addenda"] = [{"id": "ADD-NOT-IN-SOURCE", "kind": "fix", "on": "2026-01-01", "commits": ["0" * 40], "ref": "docs/normalization-revalidation.md",
                              "item_ids": [broken["items"][0]["item_id"]], "summary": "x"}]
        self.assertTrue(any("ADD-NOT-IN-SOURCE: 元の一覧の addenda に" in p for p in self.problems(broken)))
        broken["addenda"][0].update(commits=["abc"], item_ids=["IA-NOT-REVALIDATED"])
        problems = self.problems(broken)
        self.assertTrue(any("直したコミット（40 桁）" in p for p in problems))
        self.assertTrue(any("項目 IA-NOT-REVALIDATED が再検証にない" in p for p in problems))

    def test_followup_kinds_must_match_the_source_addendum(self):
        """後の追加の検証（followup）・後の版の仮定（assumption）の追記は、元の一覧の同じ ID・同じ種類の追記と一致する（commits は fix だけが要る）。"""
        ledger, source = _copy(self.ledger), _copy(self.source)
        row = {"id": "ADD-SYNTHETIC-FOLLOWUP", "kind": "followup", "on": "2026-01-01", "ref": "docs/normalization-revalidation.md",
               "item_ids": [ledger["items"][0]["item_id"]], "summary": "x"}
        ledger.setdefault("addenda", []).append(dict(row))
        source.setdefault("addenda", []).append(dict(row, base_commit="0" * 40))
        self.assertFalse(any("ADD-SYNTHETIC-FOLLOWUP" in p for p in self.problems(ledger, source)))
        ledger["addenda"][-1]["kind"] = "assumption"
        self.assertTrue(any("ADD-SYNTHETIC-FOLLOWUP: 元の一覧の addenda に、同じ種類" in p for p in self.problems(ledger, source)))
        ledger["addenda"][-1]["kind"] = "guess"
        self.assertTrue(any("ADD-SYNTHETIC-FOLLOWUP: 追記の種類 guess" in p for p in self.problems(ledger, source)))

    def test_detects_stale_counts(self):
        broken = _copy(self.ledger)
        broken["counts"]["items"] += 1
        self.assertTrue(any("集計" in p for p in self.problems(broken)))


if __name__ == "__main__":
    unittest.main()
