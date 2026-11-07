"""実装の識別と互換性の判定の設計案の確かめ（docs/implementation-identity-design.md 10 章）。

設計案の JSON・文書の生成区画が同じ元から作ったものであることと、ファイルの分類の漏れ・依存の向き・公開の入口・識別子の値・機能ごとの判定の欠けを、わざと壊した値で見つけることを
確かめる。件数を期待値に写さない。現行の識別・判定は変えない（この設計は読むだけ）。
"""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("build_implementation_identity_design", ROOT / "scripts" / "build_implementation_identity_design.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)


def written() -> dict:
    return json.loads(B.OUTPUT.read_text(encoding="utf-8"))


class GeneratedTest(unittest.TestCase):
    def test_written_files_match_the_source(self):
        self.assertEqual(B.check(written(), B.DESIGN.read_text(encoding="utf-8")), [])

    def test_edited_table_is_detected(self):
        design = B.DESIGN.read_text(encoding="utf-8").replace("| `view_record.py` | view_record |", "| `view_record.py` | game_behavior |", 1)
        self.assertNotEqual(design, B.DESIGN.read_text(encoding="utf-8"))
        self.assertTrue(any("生成区画" in p for p in B.check(written(), design)))


class CoverageTest(unittest.TestCase):
    def test_added_and_removed_files_are_detected(self):
        files = B.package_files() + ["legal_actions.py"]
        files.remove("snapshot.py")
        problems = B.coverage_problems(written(), files)
        self.assertIn("legal_actions.py に分類がない（パッケージに加わったファイル）", problems)
        self.assertIn("snapshot.py の分類があるが、パッケージにない", problems)

    def test_file_in_two_components_is_detected(self):
        spec = written()
        spec["components"][1]["files"].append("engine.py")
        self.assertTrue(any(p.startswith("engine.py が 2 つ以上の部品にある") for p in B.coverage_problems(spec)))


class DependencyTest(unittest.TestCase):
    def test_game_file_importing_another_layer_is_detected(self):
        imports = B.code_imports()
        imports["engine.py"] = set(imports["engine.py"]) | {"view_record.py"}
        self.assertIn("ゲームの挙動のファイル engine.py が、ほかの層の view_record.py（view_record）を読み込む", B.dependency_problems(written(), imports))

    def test_unused_exception_is_detected(self):
        imports = B.code_imports()
        imports["serialize.py"] = set(imports["serialize.py"]) - {"__init__.py"}
        self.assertIn("依存の例外 serialize.py → __init__.py は、もう使われていない（例外から消す）", B.dependency_problems(written(), imports))

    def test_relative_imports_are_resolved(self):
        imports = B.code_imports()
        self.assertIn("observation.py", imports["engine.py"])  # from .observation import ...
        self.assertIn("serialize.py", imports["observation.py"])
        self.assertIn("resolution/codec.py", imports["resolution/flow.py"])  # from . import codec
        self.assertIn("__init__.py", imports["serialize.py"])  # from . import __version__（名前を読む）
        self.assertNotIn("__init__.py", imports["observation.py"])  # from . import faceup（モジュールを読む）


class FacadeAndIdentifierTest(unittest.TestCase):
    def test_logic_in_facade_is_detected(self):
        source = (B.PACKAGE / "__init__.py").read_text(encoding="utf-8") + "\n\ndef helper():\n    return 1\n"
        problems = B.facade_problems(written(), {"__init__.py": source})
        self.assertTrue(any("FunctionDef" in p for p in problems), problems)

    def test_changed_identifier_value_is_detected(self):
        problems = B.identifier_problems(written(), {"state_check_method": "state-export-35-sha256/2"})
        self.assertTrue(any(p.startswith("識別子 state_check_method") for p in problems), problems)


class FeatureTest(unittest.TestCase):
    def test_component_not_handled_by_a_feature_is_detected(self):
        spec = written()
        u4 = next(f for f in spec["features"] if f["id"] == "U4")
        u4["unused"].remove("view_record")
        self.assertTrue(any("機能 U4 が部品 ['view_record'] を扱っていない" in p for p in B.spec_problems(spec)))

    def test_engine_version_as_condition_is_detected(self):
        spec = written()
        spec["features"][0]["formats"].append("engine_version")
        self.assertTrue(any("エンジンの版を互換の条件" in p for p in B.spec_problems(spec)))

    def test_view_read_requiring_implementation_is_detected(self):
        spec = written()
        next(f for f in spec["features"] if f["id"] == "VIEW_READ")["required"].append("game_behavior")
        next(f for f in spec["features"] if f["id"] == "VIEW_READ")["unused"].remove("game_behavior")
        self.assertIn("閲覧用記録の読み取りが実装の一致を求めている（表示用の記録。今と同じく形式で読む）", B.spec_problems(spec))

    def test_s5_must_cover_u4_and_snapshot(self):
        spec = written()
        s5 = next(f for f in spec["features"] if f["id"] == "S5")
        s5["required"].remove("snapshot")
        s5["unused"].append("snapshot")
        self.assertIn("S5 が U4 とスナップショットの条件の和を求めていない", B.spec_problems(spec))

    def test_principles_and_migration(self):
        spec = written()
        broken = copy.deepcopy(spec)
        broken["principles"] = [p for p in broken["principles"] if p["id"] != "P-NO-REINTERPRET"]
        broken["migration"][2]["changes_current"] = True
        broken["new_method"]["name"] = broken["current"]["method"]
        problems = B.spec_problems(broken)
        self.assertIn("原則 P-NO-REINTERPRET がない", problems)
        self.assertIn("移行の段が現行の判定を変える（現行の方式は残す）", problems)
        self.assertIn("新しい方式が現行の方式と同じ名前（意味を変えずに名前を分ける）", problems)


if __name__ == "__main__":
    unittest.main()
