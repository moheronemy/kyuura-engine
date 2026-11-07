"""合法手 API（U7）の仕様案の確かめ（docs/legal-actions-api-design.md 10 章）。

仕様案の JSON・文書の生成区画が同じ元から作ったものであることと、コードの語彙（コマンドの型・段階・next・状態の区分・決定の意味）の対応の欠けと、契約の原則に反する値を、
わざと壊した値で見つけることを確かめる。件数を期待値に写さない。
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("build_legal_actions_api_design", ROOT / "scripts" / "build_legal_actions_api_design.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)


def written() -> dict:
    return json.loads(B.OUTPUT.read_text(encoding="utf-8"))


def texts() -> tuple[str, str]:
    return B.DESIGN.read_text(encoding="utf-8"), B.PLAN.read_text(encoding="utf-8")


class GeneratedTest(unittest.TestCase):
    def test_written_files_match_the_source(self):
        self.assertEqual(B.check(written(), *texts()), [])

    def test_edited_tables_are_detected(self):
        design, plan = texts()
        edited = design.replace("| `main` | in_progress |", "| `main` | awaiting_decision |", 1)
        self.assertNotEqual(edited, design)
        self.assertTrue(any("設計の文書の生成区画" in p for p in B.check(written(), edited, plan)))
        edited_plan = plan.replace("| `U7-1` |", "| `U7-9` |", 1)
        self.assertNotEqual(edited_plan, plan)
        self.assertTrue(any("実装計画の文書の生成区画" in p for p in B.check(written(), design, edited_plan)))


class CoverageTest(unittest.TestCase):
    def test_new_code_vocabulary_is_detected(self):
        code = B.code_vocabulary()
        code["commands"].append("FutureCommandForTest")
        code["phases"].append("future_phase_for_test")
        code["next"].append("future_next_for_test")
        code["meanings"].append("future_meaning_for_test")
        problems = B.coverage_problems(written(), code)
        self.assertIn("コマンドの型 FutureCommandForTest に候補の種類がない（コードに加わった型）", problems)
        self.assertIn("段階 future_phase_for_test の行がない（コードに加わった段階）", problems)
        self.assertIn("next の種類 future_next_for_test の対応がない", problems)
        self.assertIn("決定の選べるものの意味 future_meaning_for_test に入力の種類の対応がない", problems)

    def test_removed_code_vocabulary_is_detected(self):
        code = B.code_vocabulary()
        code["commands"].remove("EndTurn")
        self.assertIn("候補の種類のコマンド EndTurn がコードにない", B.coverage_problems(written(), code))


class ContractTest(unittest.TestCase):
    def test_hidden_processability_is_detected(self):
        spec = written()
        p = next(x for x in spec["processability"] if x["id"] == "not_implemented")
        p["display"] = "候補から外す"
        problems = B.spec_problems(spec)
        self.assertIn("処理可能性 not_implemented の候補を表示しない（候補から黙って消さない）", problems)
        self.assertIn("処理可能性 not_implemented の表示が、ゲーム上の禁止と区別されていない", problems)

    def test_missing_processability_kind_is_detected(self):
        spec = written()
        spec["processability"] = [x for x in spec["processability"] if x["id"] != "unverified"]
        self.assertIn("処理可能性の区分 unverified がない", B.spec_problems(spec))

    def test_main_claimed_complete_is_detected(self):
        spec = written()
        next(p for p in spec["phases"] if p["phase"] == "main")["complete_v1"] = True
        self.assertIn("初版で main の候補を complete と称している（保証できない完全性は保証しない）", B.spec_problems(spec))

    def test_state_hash_revision_is_detected(self):
        spec = written()
        spec["revision"]["source"] = "state_hash"
        self.assertIn("revision の元が、状態のハッシュ・乱数の確認値など使わない元になっている", B.spec_problems(spec))

    def test_missing_boundary_channel_is_detected(self):
        spec = written()
        spec["info_boundary"] = [b for b in spec["info_boundary"] if b["channel"] != "invalid_query"]
        self.assertIn("情報境界の経路 invalid_query の規則がない", B.spec_problems(spec))

    def test_secret_knowledge_allowed_is_detected(self):
        spec = written()
        next(k for k in spec["knowledge"] if k["id"] == "secret")["allowed"] = "いつも"
        self.assertIn("秘密の情報を使わないことが情報の元の表にない", B.spec_problems(spec))

    def test_units_order_and_tests(self):
        spec = written()
        spec["units"][0]["depends"] = ["U7-3"]
        spec["units"][1]["tests"].append("T-UNKNOWN-FOR-TEST")
        problems = B.spec_problems(spec)
        self.assertIn("単位 U7-1 があとの単位 U7-3 に依存する", problems)
        self.assertIn("単位 U7-2 のテスト T-UNKNOWN-FOR-TEST が漏れの回帰テストの一覧にない", problems)

    def test_unknown_input_kind_is_detected(self):
        spec = written()
        spec["operations"][0]["inputs"].append("choose_everything")
        self.assertTrue(any("入力の種類の語彙にない" in p for p in B.spec_problems(spec)))


class PlanDocumentTest(unittest.TestCase):
    def test_plan_names_the_first_unit_and_the_identity_dependency(self):
        _, plan = texts()
        for phrase in ("U7-1", "implementation-identity-design.md", "legal_actions", "trainer_policy_command"):
            self.assertTrue(phrase in plan, phrase)


if __name__ == "__main__":
    unittest.main()
