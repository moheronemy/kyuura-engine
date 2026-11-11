"""検証用 AI の判定の規則 6（docs/verification-ai-batch-plan3.md 11 章）: エネルギー回収の 0 枚の答えの拒否（UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE。ER9）を、
記録した送信の API の値で代表の条件をすべて確かめたときだけ known_stop にする。対戦はしない（人工の例と、あれば保存済みの C1・99 局の記録を読むだけ）。"""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from kyuura_engine import diagnostics as D

from tools.verification_ai import batch as B
from tools.verification_ai import judge as J

ER9 = "UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE"
EVIDENCE = Path("C:/dev/kyuura-engine-verification-vai/verifier/runs")
REPO = Path(__file__).resolve().parent.parent


def candidate() -> dict:
    return {"id": "c1", "kind": "answer_decision", "processability": "may_stop_later", "reasons": ["continuation_not_evaluated"],
            "input_stages": [{"input": "choose_option", "stage": 1}], "input_disclosure": "confirmed"}


def stages(decision_kind="retrieve_energy", minimum=0, maximum=2, options=2) -> list:
    return [{"stage": 1, "input": "choose_option", "decision_kind": decision_kind, "meaning": "card", "count": {"min": minimum, "max": maximum},
             "distinct": True, "decline": minimum == 0, "order": "not_applicable", "order_preserved": True,
             "options": [{"id": f"o{i + 1}", "card": 40 + i, "card_id": "PMCG1-102", "processability": "may_stop_later"} for i in range(options)]}]


def rejected(code=ER9, *, status="awaiting_decision", next_=None, viewer=0, refetch=False, public_code=None, category=None) -> dict:
    entry = D.default_catalog().get(code)
    category = category or (entry.category if entry is not None else D.RULING_UNRESOLVED)
    return {"ok": True, "outcome": D.REJECTED, "refetch_required": refetch, "refusal": None,
            "result": {"outcome": D.REJECTED, "status": status, "viewer": viewer, "role": "actor", "diagnostic_id": public_code or code, "category": category,
                       "next": [{"kind": "answer_decision", "player": viewer}] if next_ is None else next_},
            "verifier": {"diagnostic_id": code, "category": category, "engine_code": code}}


class RecordedConditionTest(unittest.TestCase):
    def test_all_conditions_make_known_stop(self):
        evidence = J.recorded_stop_evidence(candidate(), [], stages(), rejected())
        self.assertEqual(evidence, ER9)
        verdict, why = J.judge_normal(candidate(), [], rejected(), stages=stages(), evidence=evidence)
        self.assertEqual(verdict, J.KNOWN_STOP)
        self.assertEqual(why[:2], [D.RULING_UNRESOLVED, ER9])

    def test_code_alone_is_not_evidence(self):
        """コードが同じでも、条件のどれかを満たさなければ根拠にしない（規則 5 と同じ undetermined）。"""
        picked = [{"stage": 1, "option": {"card": 40, "card_id": "PMCG1-102", "processability": "may_stop_later"}}]
        cases = {
            "other_candidate_kind": (dict(candidate(), kind="play_trainer"), [], stages(), rejected()),
            "other_decision_kind": (candidate(), [], stages("search_deck"), rejected()),
            "min_not_zero": (candidate(), [], stages(minimum=1), rejected()),
            "max_zero": (candidate(), [], stages(maximum=0), rejected()),
            "no_options": (candidate(), [], stages(options=0), rejected()),
            "chose_cards": (candidate(), picked, stages(), rejected()),
            "two_stages": (candidate(), [], stages() + stages(), rejected()),
            "no_stages": (candidate(), [], None, rejected()),
            "decision_not_pending": (candidate(), [], stages(), rejected(status="in_progress")),
            "next_other_player": (candidate(), [], stages(), rejected(next_=[{"kind": "answer_decision", "player": 1}])),
            "refetch_required": (candidate(), [], stages(), rejected(refetch=True)),
            "public_code_differs": (candidate(), [], stages(), rejected(public_code="UNRESOLVED_OTHER")),
        }
        for label, (cand, meaning, st, submit) in cases.items():
            with self.subTest(label):
                self.assertIsNone(J.recorded_stop_evidence(cand, meaning, st, submit))
                verdict, why = J.judge_normal(cand, meaning, submit, stages=st, evidence=J.recorded_stop_evidence(cand, meaning, st, submit))
                self.assertNotEqual(verdict, J.KNOWN_STOP)
        accepted = {"ok": True, "outcome": D.ACCEPTED, "result": {"status": "in_progress"}}
        self.assertIsNone(J.recorded_stop_evidence(candidate(), [], stages(), accepted))

    def test_other_codes_of_the_same_shape_are_not_registered(self):
        """同じ形（最小 0・0 枚で止まる）のほかのコード・規則 3 の DU1 は、記録の条件では根拠にしない。"""
        for code in ("UNRESOLVED_SUPER_ENERGY_RETRIEVAL_ZERO_CHOICE", "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE", "UNRESOLVED_TRAINER_UP_TO_ZERO_CHOICE",
                     "UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT"):
            with self.subTest(code):
                submit = rejected(code)
                self.assertIsNone(J.recorded_stop_evidence(candidate(), [], stages(), submit))
                self.assertEqual(J.judge_normal(candidate(), [], submit, stages=stages())[0], J.UNDETERMINED)
        self.assertEqual(set(J.RECORDED_STOP_CONDITIONS), {ER9})
        self.assertLessEqual(set(J.RECORDED_STOP_CONDITIONS), set(J.KNOWN_STOP_EVIDENCE))

    def test_without_evidence_unchanged(self):
        """evidence を渡さない呼び出し（単局の runner の判定）は規則 5 と同じ: undetermined。"""
        self.assertEqual(J.judge_normal(candidate(), [], rejected(), stages=stages()),
                         (J.UNDETERMINED, [f"stop_condition_not_evidenced:{ER9}"]))
        self.assertEqual(J.JUDGE_RULES_VERSION, 6)
        self.assertEqual(B.TOOL_VERSION, 4)

    def test_policy_and_input_generation_do_not_use_it(self):
        """方策・行動生成・runner は規則 6 の部品を使わない（判定は保存する trace にあとから当てるだけ。乱数・入力の作り方は変わらない）。"""
        for name in ("policies.py", "actions.py", "runner.py", "negative.py", "metrics.py", "records.py"):
            text = (REPO / "tools/verification_ai" / name).read_text(encoding="utf-8")
            with self.subTest(name):
                self.assertNotIn("recorded_stop_evidence", text)
                self.assertNotIn("RECORDED_STOP_CONDITIONS", text)


def jl(p: Path) -> list:
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@unittest.skipUnless((EVIDENCE / "vai-batch-c1").is_dir() and (EVIDENCE / "vai-batch-b2").is_dir(), "保存済みの証跡がない")
class SavedRecordTest(unittest.TestCase):
    """保存済みの局の記録に当て直す（元のファイルを書かない）。"""

    def rejudge(self, gdir: Path):
        files = [gdir / n for n in ("trace.jsonl", "result.json", "judge.json")]
        before = [sha(f) for f in files]
        trace = jl(gdir / "trace.jsonl")
        result = json.loads((gdir / "result.json").read_bytes())
        original = copy.deepcopy(trace)
        new = B.judge_trace({"trace": trace, "termination": result["termination"]})
        self.assertEqual(trace, original)  # 当て直しは記録を書きかえない
        self.assertEqual([sha(f) for f in files], before)
        return json.loads((gdir / "judge.json").read_bytes()), new

    def test_c1_er9_rows_change_and_nothing_else(self):
        gdir = EVIDENCE / "vai-batch-c1/games/g001-uniform-stage-s3001/attempt-001"
        saved, new = self.rejudge(gdir)
        changed = [(o["attempt"], o["verdict"], n["verdict"]) for o, n in zip(saved["rows"], new["rows"]) if o != n]
        self.assertEqual(changed, [(35, J.UNDETERMINED, J.KNOWN_STOP)])
        self.assertEqual(new["termination"], saved["termination"])
        self.assertEqual(new["accepted_content"], saved["accepted_content"])
        self.assertEqual([u for u in new["undetermined"]], [u for u in saved["undetermined"] if u["attempt"] != 35])
        self.assertEqual(new["known_stop"], [35])
        self.assertEqual(new["rules_version"], 6)

    def test_b2_halt_is_still_undetermined(self):
        """99 局の seed 2025 の準備の停止（UNRESOLVED_MULLIGAN_COMPENSATION。受理のあとの停止）は、規則 6 では変わらない。"""
        gdir = EVIDENCE / "vai-batch-b2/games/g073-uniform-stage-s2025/attempt-001"
        if not gdir.is_dir():
            self.skipTest("seed 2025 の局の記録がない")
        saved, new = self.rejudge(gdir)
        self.assertEqual(new["rows"], saved["rows"])
        self.assertEqual(new["termination"], saved["termination"])
        self.assertEqual(new["undetermined"], saved["undetermined"])


if __name__ == "__main__":
    unittest.main()
