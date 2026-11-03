"""v0.139 のサイドを取る順番の追加検証（docs/prize-order-followup.md・.json）の再現と台帳の形。

このテストは調査の記録が再現することを確かめる。新しく提案する仕様（順番の決定を出す条件を広げる・単位を変える・保存の確かめを加える）を、今の契約として
固定するテストではない。記録した evidence には、比較用の改変（``forced_order``・``_unknown_resume``）で作った結果を含む。エンジンの動きを変えたら、記録を
``scripts/prize_order_followup.py --write`` で作り直し、文書の結論を見直す（過去の基点・結果は上書きせず追記する）。
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import prize_order_followup as F

from kyuura_engine import resolution
from kyuura_engine.resolution import flow

CONCLUSIONS = {"maintainable", "condition_needed", "unconfirmed", "within_contract_with_gap"}


class FollowupEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(F.LEDGER.read_text(encoding="utf-8"))
        cls.evidence = F.evidence()

    def test_evidence_reproduces(self):
        """記録の evidence（3 章ぶん）が、今のエンジンと比べる旧版（v0.138。git archive の読み取り用の木）で同じに再現する。"""
        for part in ("knowledge", "units", "compat"):
            with self.subTest(part=part):
                self.assertEqual(self.evidence[part], self.ledger["evidence"][part])

    def test_key_findings(self):
        """文書の結論が依る事実（記録の値を写さず、意味で確かめる）。"""
        k = self.evidence["knowledge"]
        for name in ("K1-none", "K2-spy-own", "K3-spy-opponent", "K4-omanyte", "K4L-omanyte-legal", "K5-omanyte-spy-own"):
            self.assertEqual(k[name]["v0139_first_decision"][0], "take_prize", name)  # どのサイドもうらなので、v0.139 は順番を聞かない
        for name in ("K1-none", "K2-spy-own", "K3-spy-opponent"):
            self.assertFalse(any(any(v.values()) for v in k[name]["information_differs_by_order"].values()), name)
        for name in ("K4-omanyte", "K4L-omanyte-legal", "K5-omanyte-spy-own"):
            self.assertTrue(k[name]["information_differs_by_order"]["1"]["seen_opponent_cards"], name)
        self.assertEqual(k["K4L-omanyte-legal"]["repro"], "legal_ops_from_new_game")
        self.assertTrue(k["K5-omanyte-spy-own"]["choice_differs_by_order"]["1"])
        u = self.evidence["units"]
        self.assertEqual(u["2v1"]["B_only"], [[0, 1, 0]])
        self.assertEqual(len(u["2v2"]["B_sequences"]), 6)
        self.assertTrue(all(u[c]["boards_identical"] and u[c]["result_before_each_take"] == ["None"] for c in u))
        c = self.evidence["compat"]
        self.assertEqual(c["old_version_seen"], F.OLD_VERSION)
        old = c["old_reads_new"]["prize_order"]
        self.assertEqual(old["unpickle"], "ok")
        self.assertEqual({a["type"] for key, a in old["answers"].items() if key in ("0", "1")}, {"RuntimeError"})
        self.assertEqual(old["unchanged_after_answers"], [True, True, True])
        self.assertEqual(c["old_reads_new"]["take_prize"]["invariants"], [])
        self.assertTrue(c["new_reads_old"]["export34_equal_to_new_game"])
        self.assertTrue(all(same and rng for _, same, rng in c["current"]["prize_order"]["restore_same_version"]))

    def test_forced_order_is_local(self):
        """比較用の改変は、使い終えたらもとの関数にもどる（エンジンの動きを残して変えない）。"""
        original = flow.prize_order_matters
        with F.forced_order():
            self.assertIsNot(flow.prize_order_matters, original)
        self.assertIs(flow.prize_order_matters, original)
        self.assertIs(resolution.prize_order_matters, original)


class FollowupLedgerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(F.LEDGER.read_text(encoding="utf-8"))

    def test_base_and_old_commits(self):
        self.assertRegex(self.ledger["base"]["commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(self.ledger["compared_old"]["commit"], F.OLD_COMMIT)
        self.assertEqual(self.ledger["compared_old"]["version"], F.OLD_VERSION)

    def test_conclusions_and_evidence_refs(self):
        names = set(self.ledger["evidence"]["knowledge"])
        for q in self.ledger["questions"]:
            with self.subTest(q=q["id"]):
                self.assertIn(q["conclusion"], CONCLUSIONS)
                self.assertTrue(q["conclusion_text"])
                self.assertNotIn("同等である", q["conclusion_text"])
        for row in self.ledger["questions"][0]["comparison_table"]:
            for ref in row["evidence"].split("・"):
                if not ref.startswith("docs/"):
                    self.assertIn(ref, names)

    def test_user_decisions_have_one_recommendation(self):
        for decision in self.ledger["user_decisions"]:
            with self.subTest(decision=decision["id"]):
                self.assertGreaterEqual(len(decision["options"]), 2)
                self.assertEqual(sum(1 for o in decision["options"] if o["recommended"]), 1)
                self.assertTrue(decision["recommendation_reason"])

    def test_not_recorded_as_approval(self):
        """この調査は規約の承認・公式裁定として記録しない: 単位の仮定の追記は承認なし（"none"）。"""
        ia = json.loads((ROOT / "docs" / "implementation-assumptions.json").read_text(encoding="utf-8"))
        rows = [a for a in ia["addenda"] if a.get("ref") == "docs/prize-order-followup.json"]
        self.assertTrue(rows)
        self.assertTrue(all(a["approval"] == "none" for a in rows if a["kind"] == "assumption"))


if __name__ == "__main__":
    unittest.main()
