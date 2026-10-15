"""v0.18e: 版管理した変異試験の定義（tools/mutants.py）が今のコードに入ること。docs/verification-reproducibility-v0.18e.md。

変異そのもの（写しの木でテストを走らせる）は C 段階で、ここでは走らせない（``python3 tools/run_mutants.py witness``・``full``）。ここでは、
定義が今のコードとずれていないこと（置きかえる前の文字列がちょうど 1 か所・置きかえたあとが構文として正しい・証人のテストがある）を確かめる。
コードを変えてこのテストが失敗したら、同じ誤りを今のコードに入れるように定義を直す（変異を消して数を減らさない）。
"""

from __future__ import annotations

import importlib
import pathlib
import unittest

from tools import mutants as M
from tools.run_mutants import mutated_text

ROOT = pathlib.Path(__file__).resolve().parent.parent
ORIGINS = {"v0.15d", "v0.16e", "v0.17d", "v0.18e"}


class MutantDefinitionTest(unittest.TestCase):
    def test_ids_and_origins(self):
        ids = [m.id for m in M.MUTANTS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(m.origin in ORIGINS for m in M.MUTANTS))
        self.assertTrue(all(m.title and m.old != m.new for m in M.MUTANTS))
        self.assertEqual(len(M.MODULES), len(set(M.MODULES)))

    def test_every_mutant_applies_once_and_is_valid(self):
        """置きかえる前の文字列がちょうど 1 か所にあり、置きかえたあとがコンパイルできる（JSON は読める）。構文の誤りの変異を作らない。"""
        for mutant in M.MUTANTS:
            with self.subTest(mutant=mutant.id):
                _, status = mutated_text(ROOT, mutant)
                self.assertEqual(status, "ok")

    def test_every_mutant_has_witnesses_that_exist(self):
        """どの変異にも証人のテストがあり、テストの id が今のテストのメソッドを指す。証人のモジュールは全体の実行のモジュールに入っている。"""
        for mutant in M.MUTANTS:
            with self.subTest(mutant=mutant.id):
                self.assertTrue(mutant.witnesses, "証人のテストがない")
                for test_id in mutant.witnesses:
                    module_name, class_name, method = test_id.rsplit(".", 2)
                    self.assertIn(module_name, M.MODULES)
                    module = importlib.import_module(module_name)
                    self.assertTrue(hasattr(getattr(module, class_name), method), test_id)
        self.assertEqual(set(M.WITNESSES), {m.id for m in M.MUTANTS})

    def test_modules_exist(self):
        for name in M.MODULES:
            with self.subTest(module=name):
                self.assertTrue((ROOT / (name.replace(".", "/") + ".py")).exists())


if __name__ == "__main__":
    unittest.main()
