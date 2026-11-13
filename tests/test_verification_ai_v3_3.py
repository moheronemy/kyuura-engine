"""検証用 AI の V3-3（変異の結果の分類・判定の規則 3・構築盤面の代表例）のテスト（docs/verification-ai-v3-3.md 7 章）。

小さな JSON の例と偽物で確かめ、構築盤面のケースはメモリの中で動かす（証跡のケースとは別）。
"""

from __future__ import annotations

import random
import unittest

from kyuura_engine import diagnostics as D
from tools.verification_ai import fixtures_v3_3 as F
from tools.verification_ai import judge as J
from tools.verification_ai import negative as N
from tools.verification_ai import runner as V
from tools.verification_ai.run_v3 import NegativeSession
from tools.verification_ai.run_v3_3 import CASES, DU1, run_case


def opt(oid, **kw):
    return {"id": oid, "eligible": True, "processability": "may_stop_later", **kw}


class ClassificationTest(unittest.TestCase):
    def test_not_applicable_vs_unsupported_contract(self):
        rng = random.Random("c")
        self.assertEqual(N.mutate("unknown_option", [], [], rng), (None, {"not_applicable": "no_input"}))
        value = [{"stage": 1, "input": "choose_value", "range": {"min": 0, "max": 2}, "count": {"min": 1, "max": 1}}]
        self.assertEqual(N.mutate("unknown_option", value, [1], rng)[1], {"unsupported_contract": "value_stage"})
        placement = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1"), opt("o2")]},
                     {"stage": 2, "input": "choose_option", "count": {"min": 0, "max": 5}, "options_from_stage": 1, "distinct_across_stages": True}]
        self.assertEqual(N.mutate("unknown_option", placement, ["o1"], rng)[1], {"unsupported_contract": "stage_layout_not_mapped"})
        path = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1")]},
                {"stage": 2, "input": "choose_option", "count": {"min": 0, "max": 1}, "path_stages": [1], "options": [opt("o2"), opt("o3")],
                 "options_by_path": {"o1": [{"option": "o2"}, {"option": "o3"}]}}]
        self.assertEqual(N.mutate("count_over", path, ["o1", "o2"], rng)[1], {"unsupported_contract": "path_stage_references_not_read"})
        self.assertEqual(N.mutate("non_executable", path, ["o1", "o2"], rng)[1], {"unsupported_contract": "path_stage_references_not_read"})
        self.assertEqual(N.mutate("count_over", path, ["o1"], rng)[1], {"not_applicable": "last_stage_not_at_max"})
        self.assertEqual((N.outcome_status({"unsupported_contract": "x"}), N.outcome_status({"not_applicable": "x"})), (N.UNSUPPORTED_CONTRACT, N.NOT_APPLICABLE))

    def test_per_position_limit_is_recorded_as_not_run(self):
        session = NegativeSession(12, [3, 5])
        V.Runner(V.Config(game_seed=12, policy_seed=12, host_seed=12, limits=V.Limits(operations=20, seconds=60)), negative=session).run()
        rows = [r for r in session.records if r.get("status") == N.NOT_RUN]
        self.assertTrue(rows and all(r["reason"] == "per_position_limit" and "responses" not in r for r in rows))  # 要求は送らない


def rejected(category, code):
    return {"ok": True, "outcome": D.REJECTED, "verifier": {"category": category, "diagnostic_id": code, "engine_code": code}}


class JudgeV3Test(unittest.TestCase):
    def test_stop_needs_evidence(self):
        attack = {"kind": "use_attack", "processability": "may_stop_later", "reasons": ["continuation_not_evaluated", "preflight_not_evaluated"]}
        self.assertEqual(J.judge_normal(attack, [], rejected(D.RULING_UNRESOLVED, DU1))[0], J.UNDETERMINED)  # コード表・未評価の理由だけでは足りない
        self.assertEqual(J.judge_normal(attack, [], rejected(D.RULING_UNRESOLVED, DU1), evidence=DU1)[0], J.KNOWN_STOP)
        self.assertEqual(J.judge_normal(attack, [], rejected(D.RULING_UNRESOLVED, "UNRESOLVED_MULLIGAN_COMPENSATION"), evidence=DU1)[0], J.UNDETERMINED)
        self.assertEqual(J.JUDGE_RULES_VERSION, 7)  # P6 の追従で規則 4、U-R3a の追従で規則 5（docs/verification-ai-u-r3a.md 3 章）、C1 の確認で規則 6、LOST_TARGET の P1 で規則 7。known_stop の規則 3 の中身（上の 3 つ）は変えていない

    def test_halt_after_accept(self):
        halt = {"category": D.RULING_UNRESOLVED, "diagnostic_id": DU1}
        self.assertEqual(J.judge_halt_after_accept(halt, evidence=DU1)[0], J.KNOWN_STOP)
        self.assertEqual(J.judge_halt_after_accept(halt)[0], J.UNDETERMINED)
        self.assertEqual(J.judge_halt_after_accept({"category": D.UNMAPPED, "diagnostic_id": "DIAGNOSTIC_UNMAPPED"})[0], J.SUSPECT)
        self.assertEqual(J.judge_halt_after_accept({"category": D.INVALID_INPUT, "diagnostic_id": "X"})[0], J.SUSPECT)
        self.assertEqual(J.judge_termination("halted_known", "may_stop_later")[0], J.UNDETERMINED)  # 規則 3: 停止の公開の診断と根拠がなければ判定しない

    def test_refused_rejected_and_accepted_halt_are_separate(self):
        cand = {"kind": "use_power", "processability": "unverified", "reasons": ["face_down_reveal_not_evaluated"]}
        self.assertEqual(J.judge_normal(cand, [], {"ok": True, "outcome": "refused", "refusal": {"code": "CANDIDATE_INPUT_INVALID"}})[0], J.SUSPECT)
        self.assertEqual(J.judge_normal(cand, [], rejected(D.INVALID_INPUT, "X"))[0], J.NORMAL_REJECTION)
        self.assertEqual(J.judge_normal(cand, [], {"ok": True, "outcome": D.ACCEPTED})[0], J.EXPECTED)  # 受理（あとの停止は judge_halt_after_accept が別に判定）

    def test_effects_differ_for_rejection_and_acceptance(self):
        self.assertEqual(J.judge_effects(D.REJECTED, [])[0], J.EXPECTED)
        self.assertEqual(J.judge_effects(D.REJECTED, ["checks.rng"])[0], J.SUSPECT)
        self.assertEqual(J.judge_effects("refused", ["new_update:1"])[0], J.SUSPECT)
        self.assertEqual(J.judge_effects(D.ACCEPTED, ["state_object_replaced", "checks.state", "update_number", "new_update:1"])[0], J.EXPECTED)
        self.assertEqual(J.judge_effects(D.ACCEPTED, [])[0], J.UNDETERMINED)  # 受理なのに状態が置きかわらない


class FixtureTest(unittest.TestCase):
    def test_fixtures_are_consistent_and_labelled(self):
        for fid in F.FIXTURES:
            with self.subTest(fid):
                state, record = F.build(fid)
                self.assertEqual((record["origin"], record["new_game"]), ("constructed_fixture", False))  # 記録の元を偽らない
                self.assertEqual(record["integrity"]["check_invariants"], [])
                self.assertTrue(record["integrity"]["state_usable"])
                self.assertTrue(all(len(s["sha256"]) == 64 for s in record["source"]))
                text, why = F.snapshot_text(state, fid)
                self.assertIsNone(why)
                game, status = F.restore(text)
                self.assertEqual(status, "restored")
                self.assertIsNone(game.full_record)  # 復元した対戦は完全な再現用記録を持たない


class CaseTest(unittest.TestCase):
    def run_spec(self, case_id):
        spec = next(c for c in CASES if c["case"] == case_id)
        state, _record = F.build(spec["fixture"])
        text, _ = F.snapshot_text(state, spec["fixture"])
        return spec, text, run_case(spec, text)

    def test_cases_meet_expectations(self):
        for case_id in ("C1", "C2", "C3", "C4"):
            with self.subTest(case_id):
                _spec, _text, result = self.run_spec(case_id)
                self.assertEqual(result["status"], "run")
                self.assertLessEqual(result["requests"], 20)
                self.assertTrue(all(s["expectation_met"] for s in result["steps"]), [(s["step"], s.get("submit"), s.get("check")) for s in result["steps"]])
                if case_id == "C2":
                    step = result["steps"][0]
                    self.assertEqual((step["changed"], step["effects_verdict"][0]), ([], J.EXPECTED))
                    self.assertEqual(step["disclosure"]["before"], step["disclosure"]["after"])  # 拒否では本当のカードが公開されない
                    self.assertEqual(step["recovery_verdict"][0], J.EXPECTED)
                if case_id == "C1":
                    step = result["steps"][0]
                    self.assertEqual(step["effects_verdict"][0], J.EXPECTED)  # 受理の状態の変化・公開の更新は正当
                    self.assertGreater(step["disclosure"]["before"]["opponent"]["face_down"], step["disclosure"]["after"]["opponent"]["face_down"])
                    self.assertEqual(step["disclosure"]["before"]["opponent"]["face_down_with_card_id"], 0)
                if case_id == "C3":
                    self.assertEqual(result["steps"][1]["halt_verdict"][0], J.KNOWN_STOP)
                if case_id == "C4":
                    step = result["steps"][0]
                    self.assertEqual((step["verdict"], step["reached_engine"], step["recovery_verdict"][0]), (J.EXPECTED, False, J.EXPECTED))

    def test_restore_twice_gives_same_steps_with_new_handles(self):
        spec, text, first = self.run_spec("C3")
        second = run_case(spec, text)
        self.assertEqual(second["final"], first["final"])
        handles = [(s["check"]["response"], s["candidate"]["id"]) for s in first["steps"]]
        self.assertTrue(handles)


if __name__ == "__main__":
    unittest.main()
