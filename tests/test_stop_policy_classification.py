"""停止の方針の分類台帳（docs/stop-policy-classification.json）の不変条件。

分類の件数は写さない。確かめるのは、現行コードのコードの集合と台帳の一致・ID の一意性と参照・方針の状態（承認済みにしない。規約の利用者指定だけは合意による user_agreed）・到達可能性の証拠・合意と規約と判断事項と設計文書の生成した表の整合
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
        statuses = {e.get("mode_policy_status") for e in self.ledger["entries"]} | {f["mode_policy_status"] for f in self.ledger["families"].values()}
        self.assertLessEqual(statuses - {None}, set(B.MODE_POLICY_STATUS))
        # 規約（conventions）だけは、合意 AGR-MODE-BASELINE-USER で基礎集合に入れた利用者指定を user_agreed にできる（docs/ruleset-mode-design.md 4 章）。ほかの区分は decision_required
        for c in self.ledger["conventions"]:
            expected = B.AGREED_CONVENTION_STATUS if c["baseline_category"] == "user_specified" else "decision_required"
            self.assertEqual(c["mode_policy_status"], expected, c["id"])

    def test_check_detects_agreed_non_user_convention(self):
        broken = json.loads(json.dumps(self.ledger))
        next(c for c in broken["conventions"] if c["baseline_category"] == "implementation_assumption")["mode_policy_status"] = B.AGREED_CONVENTION_STATUS
        self.assertTrue(any("利用者指定（user_specified）だけ" in p for p in B.check(broken, None)))

    def test_check_detects_user_id_not_in_registry(self):
        broken = json.loads(json.dumps(self.ledger))
        target = next(c for c in broken["conventions"] if c["id"] == "POLICY:user_simplified_text:PR1-044/attack/0")
        target["user_ids"] = ["USER-BIRTHDAY-COIN-ONLY", "USER-SPOKEN-CONDITION-IGNORED"]
        self.assertTrue(any("登録の規則" in p for p in B.check(broken, None)))

    def test_check_detects_missing_registered_spec(self):
        broken = json.loads(json.dumps(self.ledger))
        broken["conventions"] = [c for c in broken["conventions"] if c["id"] != "POLICY:user_specified_rules:neo1-049/power/0"]
        self.assertTrue(any("neo1-049/power/0" in p for p in B.check(broken, None)))

    def test_check_detects_display_only_name(self):
        broken = json.loads(json.dumps(self.ledger))
        next(c for c in broken["conventions"] if c["kind"] == "user_specified_names")["display_only"] = True
        self.assertTrue(any("表示だけにしない" in p for p in B.check(broken, None)))

    def test_check_detects_instruction_not_in_document(self):
        broken = json.loads(json.dumps(self.ledger))
        next(c for c in broken["conventions"] if c["baseline_category"] == "user_specified")["approval"]["instruction"] = "根拠の文書にない文"
        self.assertTrue(any("指定の文が根拠の文書" in p for p in B.check(broken, None)))

    def test_check_detects_agreement_recorded_as_official(self):
        broken = json.loads(json.dumps(self.ledger))
        broken["mode_agreements"]["source"]["not_recorded_as"] = ""
        self.assertTrue(any("公式の裁定" in p for p in B.check(broken, None)))

    def test_check_detects_decision_in_wrong_document(self):
        broken = json.loads(json.dumps(self.ledger))
        broken["decision_status"]["DEC-LEGACY-STATES"]["document"] = B.STOP_DECISIONS_DOC
        self.assertTrue(any("DEC-LEGACY-STATES" in p for p in B.check(broken, None)))

    def test_check_detects_stale_generated_block(self):
        broken = json.loads(json.dumps(self.ledger))
        broken["conventions"][-1]["effect"] = "台帳だけ変えた効果"
        self.assertTrue(any("生成した表" in p for p in B.check(broken, None)))

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
