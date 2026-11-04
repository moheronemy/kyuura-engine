"""S2a の続行規約 5 件の仕様案（docs/play-policy-s2a-spec.json）の不変条件。

件数・停止コードの名前は写さない（停止の方針の台帳の作り直しが、テストの中のコードの名前を数えるため。値は書き出した仕様案から引く）。確かめるのは、
``scripts/build_play_policy_s2a_spec.py`` の ``check`` が、書き出した仕様案で問題 0 であることと、わざと壊した仕様案（存在しない場面・対象の漏れ・2 つの規約の重なり・
同じ規約の対象を除外にする・存在しないテスト・実装箇所・研究の記録・判断事項・観測の数の食い違い・具体的な仕様を承認済みにする・規約を案でなくする）を見つけること。
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_play_policy_s2a_spec as S


def _copy(spec):
    return json.loads(json.dumps(spec))


class SpecInvariantTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = S.load(S.OUTPUT)
        cls.document = S.DOCUMENT.read_text(encoding="utf-8")

    def problems(self, spec):
        return S.check(spec, self.document)

    def assert_detects(self, spec, fragment):
        found = self.problems(spec)
        self.assertTrue(any(fragment in p for p in found), found)

    def test_written_spec_has_no_problems(self):
        self.assertEqual(self.problems(self.spec), [])

    def test_document_is_generated_from_the_same_source(self):
        self.assertEqual(S.render(S.build()), self.document)
        self.assertEqual(S.build(), self.spec)

    def test_process_and_specification_approvals_are_separate(self):
        self.assertEqual(self.spec["approvals"]["process"]["status"], "user_agreed")
        self.assertEqual(self.spec["approvals"]["specification"]["status"], "not_approved")
        self.assertEqual({(c["status"], c["approval"]) for c in self.spec["conventions"]}, {(S.SPEC_STATUS, S.SPEC_APPROVAL)})
        broken = _copy(self.spec)
        broken["approvals"]["specification"]["status"] = "user_agreed"
        self.assert_detects(broken, "承認済み")
        broken = _copy(self.spec)
        broken["conventions"][0]["approval"] = "user_agreed"
        self.assert_detects(broken, "案のまま")

    def test_detects_unknown_scene_and_missing_target(self):
        broken = _copy(self.spec)
        target = broken["conventions"][0]["targets"][0]
        target["scene"] = target["scene"] + "-unknown"
        self.assert_detects(broken, "場面の一覧にも事例の案にもない")
        broken = _copy(self.spec)
        broken["conventions"][0]["targets"].pop()
        self.assert_detects(broken, "対応の漏れ")

    def test_detects_overlap_and_exclusion_conflicts(self):
        broken = _copy(self.spec)
        first, second = broken["conventions"][0], broken["conventions"][1]
        second["targets"].append(dict(first["targets"][0]))
        second["codes"].append(first["codes"][0])
        self.assert_detects(broken, "2 つ以上の規約")
        broken = _copy(self.spec)
        conv = broken["conventions"][-1]
        conv["excludes"].append({"what": "x", "scene": conv["targets"][0]["scene"], "reason": "y"})
        self.assert_detects(broken, "同じ規約の対象")
        broken = _copy(self.spec)
        conv = next(c for c in broken["conventions"] if any(x.get("scene") and any(x["scene"] == t["scene"] for o in broken["conventions"] for t in o["targets"])
                                                              for x in c["excludes"]))
        exclusion = next(x for x in conv["excludes"] if x.get("scene") and any(x["scene"] == t["scene"] for o in broken["conventions"] for t in o["targets"]))
        exclusion["reason"] = "理由"
        self.assert_detects(broken, "理由にその規約を書いていない")

    def test_detects_broken_references(self):
        cases = [
            (lambda c: c["tests_existing"].append(c["tests_existing"][0] + "_missing"), "既存のテスト"),
            (lambda c: c["sites"].append(c["sites"][0] + "_missing"), "実装箇所"),
            (lambda c: c["decision_refs"].append("DEC-NOT-A-DECISION"), "判断事項"),
            (lambda c: c["ruling_ids"].append("NOT-A-RULING"), "研究の記録"),
            (lambda c: c["depends_on"].append("PC-NOT-IN-SPEC"), "依存・競合"),
            (lambda c: c.update(observed_games=c["observed_games"] + 1), "観測の局"),
            (lambda c: c.update(candidate="PC-NOT-A-CANDIDATE"), "設計案の候補"),
        ]
        for mutate, fragment in cases:
            with self.subTest(fragment=fragment):
                broken = _copy(self.spec)
                mutate(next(c for c in broken["conventions"] if c["ruling_ids"] and c["observed_games"]))
                self.assert_detects(broken, fragment)

    def test_measurement_counts_match_the_plan(self):
        broken = _copy(self.spec)
        broken["measurement"]["matched_games"] += 1
        self.assert_detects(broken, "対応する局の数")

    def test_every_convention_has_a_stage(self):
        broken = _copy(self.spec)
        for stage in broken["stages"]:
            stage["targets"] = [t for t in stage["targets"] if t != broken["conventions"][0]["id"]]
        self.assert_detects(broken, "どの実装の段階にもない")


if __name__ == "__main__":
    unittest.main()
