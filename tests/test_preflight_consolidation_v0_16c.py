"""v0.16c: 宣言の前の確認の整理（docs/preflight-consolidation-v0.16c.md）。

- 依存（2 章）: v0.13 の止める関数（``effects`` の ``counterattack_double_knockout_problem``・``ko_prevention_attack_effect_problem``・
  ``retaliation_double_knockout_problem`` と、ワザの実装の ``problem``）を呼ぶのは、限定的な互換の部品 ``resolution/v013_checks.py``
  だけ。先読み（``preflight``）・解決の基盤の処理（``kernel``・``programs``）・アダプタ（``contract``）は呼ばない。``v013_checks`` を使う所は
  ``flow._use_attack`` の 3 か所（アダプタの実装・上限を超えたとき・比べるための方法 ``legacy``）だけ。

原典で決められない場合の根拠は各裁定の文書（C18: docs/counterattack-v0.10.md・p.324、W24: docs/rocket-moltres-v0.12.md・p.82、
G37: docs/guts-v0.11.md・p.100。kyuura の NEO-2000-OFFICIAL-RULES）。この整理は裁定を変えない。
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from kyuura_engine.resolution import v013_checks

from tests.test_kernel_integration_v0_15 import imports_of

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "kyuura_engine"

# v0.13 の止める関数（v0.13 の engine._use_attack が宣言の前に呼んでいたもの。effects で定義する）
V013_PREDICATES = ("counterattack_double_knockout_problem", "ko_prevention_attack_effect_problem", "retaliation_double_knockout_problem")


def names_used(path: Path) -> set[str]:
    """モジュールの中で使う名前（変数・属性・読み込む名前）。"""
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            found.update(alias.name for alias in node.names)
    return found


def problem_calls(path: Path) -> int:
    """``<何か>.problem(...)`` の呼び出しの数（ワザの実装の宣言の前の確認）。"""
    return sum(
        1 for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "problem"
    )


def check_modes_in_flow() -> list[str]:
    """``flow.py`` の ``v013_checks.check(..., mode=...)`` の呼び出しの方法（並びの順番）。"""
    modes = []
    for node in ast.walk(ast.parse((PACKAGE / "resolution" / "flow.py").read_text(encoding="utf-8"))):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "check"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "v013_checks"):
            (mode,) = [keyword.value for keyword in node.keywords if keyword.arg == "mode"]
            modes.append(mode.value)
    return modes


class DependencyTest(unittest.TestCase):
    def test_only_the_compatibility_module_calls_the_v0_13_predicates(self):
        """v0.13 の止める関数を使う（呼ぶ・読み込む）のは、互換の部品 ``resolution/v013_checks.py`` だけ（定義する ``effects.py`` の中でも
        呼ばない。ほかの本番のコードは、先読み・解決の基盤の問いで確かめる）。"""
        users = {
            path.relative_to(PACKAGE).as_posix()
            for path in PACKAGE.rglob("*.py")
            if names_used(path) & set(V013_PREDICATES)
        }
        self.assertEqual(users, {"resolution/v013_checks.py"})

    def test_only_the_compatibility_module_asks_the_implementation_problem(self):
        """ワザの実装の ``problem``（v0.3c の宣言の前の確認）を呼ぶのも、``effects.py`` の中（実装どうし）と ``v013_checks`` だけ。"""
        users = {path.relative_to(PACKAGE).as_posix() for path in PACKAGE.rglob("*.py") if problem_calls(path)}
        self.assertEqual(users - {"effects.py"}, {"resolution/v013_checks.py"})
        self.assertEqual(problem_calls(PACKAGE / "resolution" / "v013_checks.py"), 1)

    def test_preflight_and_kernel_do_not_use_the_compatibility_module(self):
        """先読み・解決の基盤の処理・アダプタは ``v013_checks`` を読み込まない。読み込むのは振り分け（``flow.py``）だけ。"""
        module = "kyuura_engine.resolution.v013_checks"
        users = {
            path.name for path in (PACKAGE / "resolution").glob("*.py")
            if any(name == module or name.startswith(module + ".") for name in imports_of(path))
        }
        self.assertEqual(users, {"flow.py"})
        engine_imports = imports_of(PACKAGE / "engine.py")
        self.assertFalse([name for name in engine_imports if "v013_checks" in name])

    def test_the_three_uses_are_the_documented_ones(self):
        """``flow._use_attack`` の 3 か所が、それぞれ別の方法（上限を超えたとき・アダプタの実装・比べるための ``legacy``）で使う。"""
        self.assertEqual(sorted(check_modes_in_flow()), sorted(v013_checks.MODES))
        self.assertEqual(len(v013_checks.MODES), 3)

    def test_unknown_mode_is_refused(self):
        """方法の名前を間違えたら、黙って確かめずに進まない。"""
        with self.assertRaises(ValueError):
            v013_checks.check(None, None, None, None, None, mode="derived")


if __name__ == "__main__":
    unittest.main()
