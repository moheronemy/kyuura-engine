"""配布物の構成の確かめ（v0.165。docs/installation.md）。

v0.164 の ``pyproject.toml`` は ``packages = ["kyuura_engine"]`` だけで、サブパッケージ ``kyuura_engine.resolution`` が wheel・sdist に入らず、通常のインストールで
``import kyuura_engine`` が失敗した。ここでは、パッケージの設定がすべての実行時のサブパッケージと同梱のデータを入れることと、配布物の照合（scripts/check_distribution.py）が
欠け・余りをファイル名で見つけることを確かめる。件数を期待値にしない。実際の配布物の照合は、ビルドしたものに scripts/check_distribution.py を使う（このテストはビルドしない）。
"""

from __future__ import annotations

import fnmatch
import importlib.util
import pathlib
import tomllib
import unittest

from kyuura_engine import replay_record

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("check_distribution", ROOT / "scripts" / "check_distribution.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

# 名前で必ず確かめる実行時のファイル（v0.164 の欠けと、実行時に読むデータ）
NAMED_RUNTIME_FILES = (
    "kyuura_engine/__init__.py",
    "kyuura_engine/engine.py",
    "kyuura_engine/client_api.py",
    "kyuura_engine/legal_actions.py",
    "kyuura_engine/replay_record.py",
    "kyuura_engine/resolution/__init__.py",
    "kyuura_engine/resolution/kernel.py",
    "kyuura_engine/resolution/preflight.py",
    "kyuura_engine/data/kyuura_cards.json",
    "kyuura_engine/data/card_verification.json",
    "kyuura_engine/data/convention_records.json",
    "kyuura_engine/data/diagnostic_catalog.json",
    "kyuura_engine/data/species_heights.json",
)


def pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def python_dirs() -> list[pathlib.Path]:
    """.py を持つ kyuura_engine の下のディレクトリ（``__pycache__`` を除く）。"""
    package = ROOT / "kyuura_engine"
    return sorted({p.parent for p in package.rglob("*.py") if "__pycache__" not in p.parts})


def dotted(path: pathlib.Path) -> str:
    return ".".join(path.relative_to(ROOT).parts)


class RequiredFilesTest(unittest.TestCase):
    def test_required_files_are_the_identity_files(self):
        # 配布物に入るべき一覧は、実装の識別が数えるファイルと同じ（欠ければ識別も違う）
        expected = [f"kyuura_engine/{name}" for name in replay_record.package_files(ROOT / "kyuura_engine")]
        self.assertEqual(C.required_files(), expected)

    def test_named_runtime_files_are_required(self):
        required = set(C.required_files())
        for name in NAMED_RUNTIME_FILES:
            self.assertIn(name, required)


class PackageConfigTest(unittest.TestCase):
    def test_packages_are_discovered_not_listed(self):
        setuptools = pyproject()["tool"]["setuptools"]
        self.assertIsInstance(setuptools["packages"], dict)  # 固定の一覧（v0.164 の欠けの原因）にしない
        find = setuptools["packages"]["find"]
        self.assertFalse(find["namespaces"])
        self.assertEqual(find.get("where", ["."]), ["."])
        self.assertEqual(find.get("exclude", []), [])

    def test_every_python_directory_is_a_discovered_package(self):
        include = pyproject()["tool"]["setuptools"]["packages"]["find"]["include"]
        names = []
        for directory in python_dirs():
            name = dotted(directory)
            names.append(name)
            self.assertTrue((directory / "__init__.py").is_file(), name)  # namespaces = false なので __init__.py のないディレクトリは入らない
            self.assertTrue(any(fnmatch.fnmatchcase(name, pattern) for pattern in include), name)
        self.assertIn("kyuura_engine.resolution", names)
        for other in ("tests", "scripts", "tools", "examples"):
            self.assertFalse(any(fnmatch.fnmatchcase(other, pattern) for pattern in include), other)

    def test_bundled_data_is_package_data(self):
        patterns = pyproject()["tool"]["setuptools"]["package-data"]["kyuura_engine"]
        data = sorted(p.relative_to(ROOT / "kyuura_engine").as_posix() for p in (ROOT / "kyuura_engine" / "data").iterdir() if p.is_file())
        for name in data:
            self.assertTrue(any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns), name)

    def test_sdist_prunes_tests(self):
        lines = [line.strip() for line in (ROOT / "MANIFEST.in").read_text(encoding="utf-8").splitlines()]
        self.assertIn("prune tests", lines)

    def test_runtime_has_no_dependencies(self):
        project = pyproject()["project"]
        self.assertEqual(project["dependencies"], [])
        self.assertEqual(project["requires-python"], ">=3.11")


class DistributionCheckTest(unittest.TestCase):
    """照合の関数を、わざと欠けさせた・余計なものを入れた名前の一覧で確かめる。"""

    def setUp(self):
        self.required = C.required_files()
        self.wheel = [*self.required, "kyuura_engine/data/", "kyuura_engine-0.0.0.dist-info/METADATA", "kyuura_engine-0.0.0.dist-info/RECORD"]
        self.sdist = [f"kyuura_engine-0.0.0/{name}" for name in (*self.required, "PKG-INFO", "README.md", "pyproject.toml", "setup.cfg", "MANIFEST.in",
                                                                   "kyuura_engine.egg-info/SOURCES.txt")]

    def test_complete_distributions_pass(self):
        self.assertEqual(C.wheel_problems(self.wheel, self.required), [])
        self.assertEqual(C.sdist_problems(self.sdist, self.required), [])

    def test_missing_subpackage_is_named(self):
        # v0.164 の形: resolution の下がない
        wheel = [n for n in self.wheel if not n.startswith("kyuura_engine/resolution/")]
        problems = C.wheel_problems(wheel, self.required)
        self.assertIn("wheel: 欠けている kyuura_engine/resolution/__init__.py", problems)
        self.assertIn("wheel: 欠けている kyuura_engine/resolution/kernel.py", problems)
        sdist = [n for n in self.sdist if "/kyuura_engine/resolution/" not in n]
        self.assertIn("sdist: 欠けている kyuura_engine/resolution/preflight.py", C.sdist_problems(sdist, self.required))

    def test_missing_data_is_named(self):
        wheel = [n for n in self.wheel if n != "kyuura_engine/data/kyuura_cards.json"]
        self.assertEqual(C.wheel_problems(wheel, self.required), ["wheel: 欠けている kyuura_engine/data/kyuura_cards.json"])

    def test_files_outside_the_package_are_named(self):
        self.assertEqual(C.wheel_problems([*self.wheel, "tests/test_cards.py"], self.required), ["wheel: パッケージの外のファイル tests/test_cards.py"])
        self.assertEqual(C.sdist_problems([*self.sdist, "kyuura_engine-0.0.0/tests/test_cards.py", "kyuura_engine-0.0.0/.claude/settings.json"], self.required),
                         ["sdist: パッケージの外のファイル .claude/settings.json", "sdist: パッケージの外のファイル tests/test_cards.py"])

    def test_unlisted_package_files_are_named(self):
        problems = C.wheel_problems([*self.wheel, "kyuura_engine/scratch.txt"], self.required)
        self.assertEqual(problems, ["wheel: 一覧にないパッケージのファイル kyuura_engine/scratch.txt"])


if __name__ == "__main__":
    unittest.main()
