"""U7-5 の仕様と実装計画（docs/legal-actions-u7-5-design.json・設計と実装計画の文書）の整合の検査と、検査を壊して確かめるテスト（調査と仕様だけ。候補の実装はない）。"""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("build_legal_actions_u7_5_design", ROOT / "scripts" / "build_legal_actions_u7_5_design.py")
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)


def written() -> dict:
    return json.loads(G.OUTPUT.read_text(encoding="utf-8"))


def texts() -> tuple[str, str]:
    return G.DESIGN.read_text(encoding="utf-8"), G.PLAN.read_text(encoding="utf-8")


class CheckTest(unittest.TestCase):
    def test_written_spec_and_documents_pass(self):
        design, plan = texts()
        self.assertEqual(G.check(written(), design, plan), [])

    def test_seven_commands_and_implemented_kinds(self):
        """7 種類のうち、v0.167 で実装したのは U7-5a・U7-5b の 3 種類だけ。ほかの 4 種類は候補の種類がない。"""
        from kyuura_engine import commands, legal_actions

        spec = written()
        done = {c for u in spec["units"] if u.get("status") == "implemented" for c in u["commands"]}
        self.assertEqual(done, {"RemoveDisguise", "DiscardFromPlay", "RevealFaceDown"})
        self.assertEqual(len(spec["commands"]), 7)
        for c in spec["commands"]:
            self.assertEqual(c["kind"] in legal_actions.IMPLEMENTED_KINDS, c["command"] in done, c["command"])
            self.assertIn(c["command"], {cls.__name__ for cls in commands.COMMAND_TYPES.values()})

    def test_only_adopted_units_are_implemented(self):
        spec = written()
        self.assertEqual([u["id"] for u in spec["units"] if u.get("status") == "implemented"], ["U7-5a", "U7-5b"])
        self.assertEqual(spec["adoption_record"]["implemented_units"], ["U7-5a", "U7-5b"])
        self.assertEqual([u["id"] for u in spec["units"] if u["first"]], ["U7-5a"])
        self.assertEqual(spec["adoption"]["approval"], "not_approved")
        self.assertIn("T-F1", next(u for u in spec["units"] if u["id"] == "U7-5c")["depends"])  # F-1 はトレーナーの前に直す
        self.assertEqual({c["id"] for c in spec["adoption_record"]["corrections"]}, {"CORR-1", "CORR-2"})
        self.assertNotEqual(spec["gui_ref"]["commit"], spec["gui_ref"]["pinned_engine"])  # GUI のコミットと固定するエンジンを分ける


class BrokenSpecTest(unittest.TestCase):
    """検査が、壊した仕様を見つける（検査そのものの確かめ）。"""

    def problems(self, mutate) -> list[str]:
        spec = copy.deepcopy(written())
        mutate(spec)
        return G.spec_problems(spec) + G.code_problems(spec)

    def assert_found(self, mutate, fragment: str):
        found = self.problems(mutate)
        self.assertTrue(any(fragment in p for p in found), found)

    def test_secret_check_used_by_candidates(self):
        def mutate(spec):
            next(c for c in spec["checks"] if c["source"] == "D")["use"] = "candidates"
        self.assert_found(mutate, "候補・inputs・check に使う")

    def test_unconfirmed_check_used_by_candidates(self):
        def mutate(spec):
            next(c for c in spec["checks"] if c["source"] == "E")["use"] = "inputs"
        self.assert_found(mutate, "候補・inputs・check に使う")

    def test_unknown_source_class(self):
        def mutate(spec):
            spec["checks"][0]["source"] = "F"
        self.assert_found(mutate, "A〜E でない")

    def test_unit_counted_as_implemented(self):
        def mutate(spec):
            next(u for u in spec["units"] if u["id"] == "U7-5c")["status"] = "implemented"
        self.assert_found(mutate, "採用の記録にない単位")

    def test_implemented_unit_without_kind(self):
        def mutate(spec):
            next(u for u in spec["units"] if u["id"] == "U7-5f")["status"] = "implemented"
            spec["adoption_record"]["implemented_units"].append("U7-5f")
        self.assert_found(mutate, "IMPLEMENTED_KINDS")

    def test_unknown_unit_status(self):
        def mutate(spec):
            spec["units"][0]["status"] = "done"
        self.assert_found(mutate, "planned・implemented でない")

    def test_unit_without_required_verification(self):
        def mutate(spec):
            spec["units"][0]["tests"] = [t for t in spec["units"][0]["tests"] if t[0] != "V-TWIN" and t[0] != "V-HANDLE"]
        self.assert_found(mutate, "V-HANDLE")

    def test_unit_without_legal_sequence(self):
        def mutate(spec):
            spec["units"][0]["tests"] = [[t[0], "board" if t[1] == "sequence" else t[1]] for t in spec["units"][0]["tests"]]
        self.assert_found(mutate, "new_game からの列")

    def test_unconfirmed_path_counted_as_closed(self):
        def mutate(spec):
            next(u for u in spec["units"] if "PlayTrainer" in u["commands"])["open"] = []
        self.assert_found(mutate, "残る事項")

    def test_finding_without_evidence(self):
        def mutate(spec):
            spec["findings"][0]["evidence"] = ""
        self.assert_found(mutate, "再現・根拠・影響範囲")

    def test_two_first_units(self):
        def mutate(spec):
            spec["units"][1]["first"] = True
        self.assert_found(mutate, "最初に実装する単位")

    def test_missing_reference(self):
        def mutate(spec):
            spec["checks"][0]["ref"] = "kyuura_engine/engine.py::no_such_function"
        self.assert_found(mutate, "コードにない")

    def test_line_number_reference(self):
        def mutate(spec):
            spec["checks"][0]["ref"] = "kyuura_engine/engine.py::2548"
        self.assert_found(mutate, "ファイル::名前")

    def test_field_order_differs_from_code(self):
        def mutate(spec):
            fields = spec["commands"][1]["fields"]
            fields[2], fields[3] = fields[3], fields[2]
        self.assert_found(mutate, "項目の並び")

    def test_dropped_command(self):
        def mutate(spec):
            spec["commands"] = spec["commands"][:-1]
        self.assert_found(mutate, "調べた 7 種類")

    def test_scan_record_differs(self):
        def mutate(spec):
            spec["scan"]["check_playable"]["trials"] = spec["scan"]["check_playable"]["trials"][1:]
        self.assert_found(mutate, "静的な走査")

    def test_registry_count_differs(self):
        def mutate(spec):
            spec["registry"]["trainers"] += 1
        self.assert_found(mutate, "登録の数")

    def test_power_shape_table_misses_a_class(self):
        def mutate(spec):
            spec["power_shapes"]["none"] = spec["power_shapes"]["none"][1:]
        self.assert_found(mutate, "特殊能力の形の表")

    def test_missing_board_file(self):
        def mutate(spec):
            spec["units"][0]["boards"] = ["tests/no_such_test.py（なし）"]
        self.assert_found(mutate, "代表の盤面のファイルがない")


class BrokenDocumentTest(unittest.TestCase):
    def test_edited_generated_block(self):
        design, plan = texts()
        broken = design.replace("| `PlayTrainer` | `card` |", "| `PlayTrainer` | `cards` |", 1)
        self.assertNotEqual(broken, design)
        self.assertTrue(any("生成区画" in p for p in G.check(written(), broken, plan)))

    def test_removed_block_marker(self):
        design, plan = texts()
        broken = plan.replace("<!-- generated:rest-first begin -->", "", 1)
        self.assertTrue(any("rest-first" in p for p in G.check(written(), design, broken)))

    def test_assumption_keyword_in_text(self):
        design, plan = texts()
        keyword = G._SCAN.KEYWORDS[0]
        self.assertTrue(any("抽出の語" in p for p in G.check(written(), design + "\n" + keyword + "\n", plan)))


class LinkTest(unittest.TestCase):
    def test_existing_specs_link_to_u7_5_design(self):
        for name in ("legal-actions-api-design.md", "legal-actions-api-implementation-plan.md"):
            text = (ROOT / "docs" / name).read_text(encoding="utf-8")
            self.assertIn("legal-actions-u7-5-design.md", text, name)
            self.assertIn("legal-actions-u7-5-implementation-plan.md", text, name)

    def test_design_links_plan_and_json(self):
        design, plan = texts()
        self.assertIn("legal-actions-u7-5-implementation-plan.md", design)
        self.assertIn("legal-actions-u7-5-design.json", design)
        self.assertIn("legal-actions-u7-5-design.md", plan)


if __name__ == "__main__":
    unittest.main()
