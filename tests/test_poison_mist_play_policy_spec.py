"""［ポイズンミスト］とどくの量（PO1〜PO3）の続行規約の仕様案（docs/poison-mist-play-policy-spec.json）の不変条件。

``scripts/build_poison_mist_play_policy_spec.py`` の ``check`` が、書き出した仕様案で問題 0 であることと、わざと壊した仕様案（存在しない場面・対象の漏れ・2 つの規約の重なり・
同じ規約の対象を除外にする・存在しないテスト・実装箇所・研究の記録・判断事項・観測の局の数の食い違い・仕様を承認済みにする・規約を案でなくする・登録と採用の記録の食い違い（v0.145 の採用のあと））を見つけること。
件数・停止コードの名前は写さない（値は書き出した仕様案から引く）。
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_poison_mist_play_policy_spec as S

from kyuura_engine import conventions as C


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

    def test_work_approval_is_not_a_specification_approval(self):
        self.assertEqual(self.spec["status"], "proposal")
        self.assertEqual(self.spec["approvals"]["specification"]["status"], "not_approved")
        self.assertEqual({(c["status"], c["approval"]) for c in self.spec["conventions"]}, {("proposal", "not_approved")})
        broken = _copy(self.spec)
        broken["approvals"]["specification"]["status"] = "user_agreed"
        self.assert_detects(broken, "承認済み")
        broken = _copy(self.spec)
        broken["conventions"][0]["approval"] = "user_agreed"
        self.assert_detects(broken, "案のまま")
        broken = _copy(self.spec)
        broken["approvals"]["work"]["scope"] = "作業"
        self.assert_detects(broken, "作業の承認の範囲")

    def test_adopted_conventions_are_registered_as_adopted(self):
        """v0.145: 採用のあとは、仕様の 3 規約が採用した続行規約として登録され、採用の記録が利用者の指示（公式の裁定ではない）。登録と食い違えば --check が見つける。
        提案の時点の記録（1〜12 章・仕様の承認 not_approved）は書き換えない（test_work_approval_is_not_a_specification_approval）。"""
        for c in self.spec["conventions"]:
            self.assertEqual([key for key in C.CONVENTIONS if key[0] == c["id"]], [(c["id"], c["version"])])
        self.assertEqual(self.spec["adoption"]["status"], "user_agreed")
        fake = dict(C.CONVENTIONS)
        first = self.spec["conventions"][0]
        fake[(first["id"], first["version"])] = next(iter(C.CONVENTIONS.values()))  # 違う中身（今の挙動の記録）を同じ ID で登録した
        with mock.patch.object(C, "CONVENTIONS", fake):
            self.assert_detects(self.spec, "ちょうど 1 つ登録されていない")
        broken = _copy(self.spec)
        broken["adoption"]["scope"] = "採用"
        self.assert_detects(broken, "採用の記録")
        broken = _copy(self.spec)
        broken["adoption"]["set"] = ["CS-KYUURA-PLAY-S2A", 1]
        self.assert_detects(broken, "開発用の部分的な集合")

    def test_detects_unknown_scene_and_missing_target(self):
        broken = _copy(self.spec)
        target = broken["conventions"][0]["targets"][0]
        target["scene"] = target["scene"] + "-unknown"
        self.assert_detects(broken, "場面の一覧にも事例の案にもない")
        broken = _copy(self.spec)
        broken["conventions"][0]["targets"].pop()
        self.assert_detects(broken, "対応の漏れ")
        broken = _copy(self.spec)
        split = next(c for c in broken["conventions"] if c["proposed_cases"])
        split["excludes"] = [x for x in split["excludes"] if not x.get("scene", "").startswith(split["codes"][0] + "#")]
        self.assert_detects(broken, "対応の漏れ")  # 分けた事例（#power-lost）を対象にも除外にも書かない

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
        targets = {t["scene"] for o in broken["conventions"] for t in o["targets"]}
        conv = next(c for c in broken["conventions"] if any(x.get("scene") in targets for x in c["excludes"]))
        next(x for x in conv["excludes"] if x.get("scene") in targets)["reason"] = "理由"
        self.assert_detects(broken, "理由にその規約を書いていない")
        broken = _copy(self.spec)
        broken["separated_questions"].append({"question": "q", "scene": broken["conventions"][0]["targets"][0]["scene"], "reason": "r"})
        self.assert_detects(broken, "共通化しない問いの場面")

    def test_detects_broken_references(self):
        cases = [
            (lambda c: c["tests_existing"].append(c["tests_existing"][0] + "_missing"), "既存のテスト"),
            (lambda c: c["sites"].append(c["sites"][0] + "_missing"), "実装箇所"),
            (lambda c: c["decision_refs"].append("DEC-NOT-A-DECISION"), "判断事項"),
            (lambda c: c["ruling_ids"].append("NOT-A-RULING"), "研究の記録"),
            (lambda c: c["depends_on"].append("PC-NOT-IN-SPEC"), "依存・競合"),
            (lambda c: c["related"].append("PC-NOT-A-CANDIDATE"), "関係の"),
            (lambda c: c.update(observed_games=c["observed_games"] + 1), "観測の局"),
            (lambda c: c.update(principle="P-NOT-A-PRINCIPLE"), "原則"),
        ]
        for mutate, fragment in cases:
            with self.subTest(fragment=fragment):
                broken = _copy(self.spec)
                mutate(broken["conventions"][0])
                self.assert_detects(broken, fragment)

    def test_observed_cases_match_the_measurement(self):
        rows = self.spec["observed_cases"]
        self.assertEqual(len(rows), self.spec["measurement"]["covered_by_this_spec"])
        self.assertEqual(sum(c["observed_games"] for c in self.spec["conventions"]), len(rows))
        broken = _copy(self.spec)
        broken["observed_cases"].append(dict(broken["observed_cases"][0]))
        self.assert_detects(broken, "同じ局が 2 回")
        broken = _copy(self.spec)
        broken["observed_cases"].pop()
        self.assert_detects(broken, "設計案の計測の数")

    def test_every_convention_has_a_stage(self):
        broken = _copy(self.spec)
        for stage in broken["stages"]:
            stage["targets"] = [t for t in stage["targets"] if t != broken["conventions"][0]["id"]]
        self.assert_detects(broken, "どの実装の段階にもない")


if __name__ == "__main__":
    unittest.main()
