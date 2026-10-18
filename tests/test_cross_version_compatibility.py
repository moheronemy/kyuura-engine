"""前の版との互換性の軽い回帰テストと、比べる道具のセルフテスト（v0.4e。docs/compatibility-v0.4e.md）。

- 参照データ tests/fixtures/compat_base_4bd97bf.json は、基準の版（v0.4d の 4bd97bf）で tools/compare_engine_versions.py
  ``--write-fixture`` が作った、1 手ごとの記録の指紋（操作・結果・形式 8 の状態（ログ・乱数の指紋・決定を含む）・形式 1〜8 の
  書き出し）。今の版で同じ駆動を動かし、すべての手で同じになることを確かめる（4 局・約 480 手。数秒）。参照データは今の版から
  作り直さない（作り直すと前の版との比較ではなくなる）。駆動（tools/compat_driver.py）を変えたら、基準の版から作り直す。
- 大きな比較（すべての組・多くの seed を、版ごとに別のプロセスで動かす）は、ふだんのテストでは走らせない。
  ``python3 tools/compare_engine_versions.py --base 4bd97bf`` で明示的に実行する（環境変数 ``KYUURA_COMPAT_BASE`` を
  設定すると、このファイルの ``FullComparisonTest`` も走る）。
"""

import importlib.util
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

import kyuura_engine

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "compat_base_4bd97bf.json"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


driver = _load("compat_driver")
compare = _load("compare_engine_versions")


class FixtureComparisonTest(unittest.TestCase):
    """基準の版（4bd97bf）の記録と、今の版の記録が、すべての手で同じ。"""

    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text())

    def test_fixture_was_made_by_this_driver_from_the_base(self):
        self.assertEqual(self.fixture["base_commit"], "4bd97bfe7906e2c5c37515e6ec6b2b81e36000c6")
        self.assertEqual(self.fixture["driver_sha256"], compare.driver_hash(),
                         "駆動を変えたら、基準の版から参照データを作り直す（fixture の how）")
        self.assertEqual(self.fixture["excluded"], ["effects"])

    def test_current_version_matches_the_base_at_every_step(self):
        for game in self.fixture["games"]:
            scenario = driver.SCENARIOS_BY_NAME[game["scenario"]]
            steps = max(step[0] for step in game["steps"])
            scenario = driver.Scenario(**{**scenario.__dict__, "steps": max(steps, 1)})
            with self.subTest(scenario=scenario.name, seed=game["seed"]):
                records = driver.run_scenario(kyuura_engine, scenario, game["seed"])
                current = [[r["i"], r["res"], driver.record_digest(r)] for r in records]
                for expected, actual in zip(game["steps"], current):
                    if expected != actual:
                        record = records[actual[0]]
                        self.fail(
                            f"{scenario.name} seed {game['seed']} の {actual[0]} 手目が基準と違う: 操作 {record['cmd']}、結果 {record['res']}"
                            f"（基準 {expected[1]}）。診断: python3 tools/compare_engine_versions.py --base 4bd97bf --scenario "
                            f"{scenario.name} --seeds {game['seed'] + 1} --steps {steps} --report report.json"
                        )
                self.assertEqual(len(current), len(game["steps"]))


class DriverTest(unittest.TestCase):
    def test_driver_is_deterministic_and_uses_only_the_given_engine(self):
        scenario = driver.Scenario(**{**driver.SCENARIOS_BY_NAME["butterfree"].__dict__, "steps": 60})
        first = driver.run_scenario(kyuura_engine, scenario, 3)
        self.assertEqual(first, driver.run_scenario(kyuura_engine, scenario, 3))
        self.assertGreater(len({r["res"] for r in first}), 1)  # 受け付けた操作と拒否された操作の両方がある
        self.assertTrue(all(len(r["formats"]) == 8 for r in first))

    def test_scenarios_cover_the_required_cards(self):
        """比べる組（docs/compatibility-v0.4e.md 2 章）: たねだけ・トレーナー・特殊状態・1 進化・かたまる・2 進化・バタフリー・すべて。"""
        cards = set()
        for scenario in driver.SCENARIOS:
            kyuura_engine.validate_deck(driver._deck(scenario.deck0))
            kyuura_engine.validate_deck(driver._deck(scenario.deck1))
            cards |= set(scenario.deck0) | set(scenario.deck1)
        for card_id in (driver.PARASECT, driver.DEWGONG, driver.METAPOD, driver.KAKUNA, driver.BEEDRILL, driver.BUTTERFREE,
                        driver.WEEDLE, driver.CATERPIE, driver.PARAS, driver.VULPIX, driver.POTION, driver.SWITCH, driver.BILL,
                        driver.PLUSPOWER, driver.DEFENDER, driver.DODUO, driver.PIKACHU):
            self.assertIn(card_id, cards)


class ComparisonLogicTest(unittest.TestCase):
    """比べる道具のセルフテスト（作った記録の並び。エンジンは動かさない）。"""

    def test_first_difference(self):
        base = [{"i": 0, "res": "ok", "state": "a"}, {"i": 1, "res": "ok", "state": "b"}, {"i": 2, "res": "ok", "state": "c"}]
        self.assertIsNone(compare.first_difference(base, [dict(r) for r in base]))
        changed = [dict(r) for r in base]
        changed[1] = {**changed[1], "res": "IllegalActionError:X", "state": "a"}
        self.assertEqual(compare.first_difference(base, changed), (1, ["res", "state"]))
        self.assertEqual(compare.first_difference(base, base[:2]), (2, ["(記録がない)"]))

    def test_dict_differences(self):
        old = {"players": [{"active": {"damage": 10}}], "log": [1, 2]}
        new = {"players": [{"active": {"damage": 20}}], "log": [1, 2, 3]}
        self.assertEqual(compare.dict_differences(old, new), [".log: [1, 2] → [1, 2, 3]", ".players[0].active.damage: 10 → 20"])

    def test_summary_counts(self):
        games = [{"records": [{"i": 0, "res": "ok", "formats": ["x"] * 8, "phase": "setup_placement"},
                              {"i": 1, "res": "IllegalActionError:WRONG_PHASE", "formats": ["x"] * 8, "phase": "setup_placement"},
                              {"i": 2, "res": "UnsupportedError:UNRESOLVED_X", "formats": ["x"] * 8, "phase": "halted"}]}]
        counted = compare.summarize(games)
        self.assertEqual((counted["games"], counted["records"], counted["rejected"], counted["rejected_unresolved"], counted["formats_compared"]),
                         (1, 3, 2, 1, 24))


class IsolationTest(unittest.TestCase):
    """版ごとに別のプロセスで、指定した木の kyuura_engine だけを読み込む。わざと動きを変えた写しとの食い違いを見つける。"""

    def test_mutated_copy_is_detected_in_a_separate_process(self):
        workdir = pathlib.Path(tempfile.mkdtemp(prefix="kyuura-compat-test-"))
        try:
            mutated = workdir / "mutated"
            shutil.copytree(ROOT / "kyuura_engine", mutated / "kyuura_engine", ignore=shutil.ignore_patterns("__pycache__"))
            engine_py = mutated / "kyuura_engine" / "engine.py"
            source = engine_py.read_text(encoding="utf-8")
            # v0.46: にげるエネルギーの数の確かめ（v0.45 までは ``if len(discard) != cost:``）。v0.58 から、トラッシュするカードの出すエネルギーの個数で数える
            needle = "    if not cost.allows(units):"
            self.assertIn(needle, source)
            engine_py.write_text(source.replace(needle, "    if not cost.allows(units) and False:"), encoding="utf-8")
            args = type("Args", (), {"scenario": ["basics"], "seeds": 1, "steps": 120})()
            outputs = []
            for tree in (ROOT, mutated):
                out = workdir / f"{tree.name}.json"
                compare.run_driver(tree, out, args)
                outputs.append(json.loads(out.read_text()))
            self.assertTrue(pathlib.Path(outputs[0]["engine_file"]).is_relative_to(ROOT))
            self.assertTrue(pathlib.Path(outputs[1]["engine_file"]).is_relative_to(mutated))
            found = [compare.first_difference(a["records"], b["records"]) for a, b in zip(outputs[0]["games"], outputs[1]["games"])]
            self.assertTrue(any(f is not None and "res" in f[1] for f in found), found)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)


@unittest.skipUnless(os.environ.get("KYUURA_COMPAT_BASE"), "大きな比較は KYUURA_COMPAT_BASE=4bd97bf を設定したときだけ")
class FullComparisonTest(unittest.TestCase):
    def test_no_differences(self):
        self.assertEqual(compare.main(["--base", os.environ["KYUURA_COMPAT_BASE"]]), 0)


if __name__ == "__main__":
    unittest.main()
