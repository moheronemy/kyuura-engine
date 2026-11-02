"""停止の方針の分類台帳（docs/stop-policy-classification.json）の不変条件。

分類の件数は写さない。確かめるのは、現行コードのコードの集合と台帳の一致・ID の一意性と参照・方針の状態（承認済みにしない）・到達可能性の証拠
（``scripts/build_stop_policy_classification.py`` の ``check``。作り直した台帳との比べは、リポジトリの外の証拠に依存するので ``--check`` だけで行う）。
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_stop_policy_classification as B


class LedgerInvariantTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(B.OUTPUT.read_text(encoding="utf-8"))

    def test_invariants(self):
        self.assertEqual(B.check(self.ledger, None), [])

    def test_no_approved_mode_policy(self):
        statuses = {e.get("mode_policy_status") for e in self.ledger["entries"]} | {c["mode_policy_status"] for c in self.ledger["conventions"]} \
            | {f["mode_policy_status"] for f in self.ledger["families"].values()}
        self.assertLessEqual(statuses - {None}, set(B.MODE_POLICY_STATUS))

    def test_check_detects_missing_code(self):
        broken = json.loads(json.dumps(self.ledger))
        broken["entries"] = [e for e in broken["entries"] if e["id"] != "UNRESOLVED_MULLIGAN_COMPENSATION"]
        self.assertTrue(any("UNRESOLVED_MULLIGAN_COMPENSATION" in p for p in B.check(broken, None)))

    def test_check_detects_approved_status(self):
        broken = json.loads(json.dumps(self.ledger))
        broken["conventions"][0]["mode_policy_status"] = "approved"
        self.assertTrue(any("decision_required" in p for p in B.check(broken, None)))

    def test_check_detects_unsupported_reachability(self):
        broken = json.loads(json.dumps(self.ledger))
        entry = next(e for e in broken["entries"] if e["entry_kind"] == "research_stop_code")
        entry["reachability"] = {"status": "legal_sequence", "evidence": []}
        self.assertTrue(any("証拠がない" in p for p in B.check(broken, None)))


if __name__ == "__main__":
    unittest.main()
