"""未決場面の共通規約の設計案（docs/play-policy-family-plan.json）の不変条件。

件数は写さない。確かめるのは、``scripts/build_play_policy_family_plan.py`` の ``check`` が、書き出した設計案で問題 0 であることと、わざと壊した設計案
（対応先のない場面・規約の対象に機能不足や不具合を入れる・2 つの規約案の重なり・適用条件の欠け・承認済みにする・不具合のある場面を続けられるとする・
参照切れ・集計の食い違い・名前だけで A にする）を見つけること。
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_play_policy_family_plan as P


def _copy(plan):
    return json.loads(json.dumps(plan))


class PlanInvariantTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = P.load_json(P.OUTPUT)
        cls.ledger = P.load_json(P.LEDGER)

    def problems(self, plan):
        return P.check(plan, self.ledger, None)

    def assert_detects(self, plan, fragment):
        found = self.problems(plan)
        self.assertTrue(any(fragment in p for p in found), found)

    def candidate(self, plan, cid):
        return next(c for c in plan["candidates"] if c["id"] == cid)

    def test_written_plan_has_no_problems(self):
        self.assertEqual(self.problems(self.plan), [])

    def test_rebuilt_plan_matches_written(self):
        fresh = P.build()
        if fresh.get("observation") is None:
            fresh = dict(fresh, observation=self.plan.get("observation"))
            fresh["priority"] = self.plan["priority"]  # 道具の記録がない環境では、記録に依存する項目を比べない
        self.assertEqual(P.stable(fresh), P.stable(self.plan))

    def test_all_proposals(self):
        # v0.143: S2a の 5 つの案だけが採用（adopted）。ほかは案のまま
        self.assertEqual({c["id"] for c in self.plan["candidates"] if c["status"] == P.ADOPTED}, set(P.ADOPTIONS))
        self.assertEqual({c["status"] for c in self.plan["candidates"] if c["id"] not in P.ADOPTIONS}, {P.STATUS})
        broken = _copy(self.plan)
        broken["candidates"][0]["status"] = "approved"
        self.assert_detects(broken, "案だけ")

    def test_detects_scene_without_destination(self):
        broken = _copy(self.plan)
        removed = next(s for s in broken["scenes"] if s["plan_class"] == "A" and not s.get("candidate"))
        broken["scenes"].remove(removed)
        self.assert_detects(broken, "対応先がない")

    def test_detects_unclassified_a_scene(self):
        broken = _copy(self.plan)
        s = next(s for s in broken["scenes"] if s["plan_class"] == "A" and not s.get("candidate"))
        s["individual_reason"] = ""
        self.assert_detects(broken, "未分類")

    def test_detects_engine_gap_in_rule_targets(self):
        broken = _copy(self.plan)
        gap = next(s for s in broken["scenes"] if s["plan_class"] == "B")
        self.candidate(broken, "PC-USE-WITHOUT-TARGET")["targets"].append({"scene": gap["id"], "coverage": "unverified"})
        self.assert_detects(broken, "規約の対象にしない")

    def test_detects_safety_stop_in_rule_targets(self):
        broken = _copy(self.plan)
        limit = next(s for s in broken["scenes"] if s["plan_class"] == "C")
        self.candidate(broken, "PC-ORDER-OVERLAP")["targets"].append({"scene": limit["id"], "coverage": "unverified"})
        self.assert_detects(broken, "規約の対象にしない")

    def test_detects_two_rules_on_one_scene(self):
        broken = _copy(self.plan)
        scene = self.candidate(broken, "PC-UP-TO-ZERO")["targets"][0]["scene"]
        self.candidate(broken, "PC-USE-WITHOUT-TARGET")["targets"].append({"scene": scene, "coverage": "unverified"})
        self.assert_detects(broken, "2 つ以上の規約案")

    def test_detects_missing_applicability_and_exclusions(self):
        for field in ("applies_when", "excludes", "unverified", "basis"):
            broken = _copy(self.plan)
            self.candidate(broken, "PC-SETUP-MULLIGAN-COUNT")[field] = [] if isinstance(self.candidate(broken, "PC-SETUP-MULLIGAN-COUNT")[field], list) else ""
            self.assert_detects(broken, f"項目 {field} が空")

    def test_detects_vague_statement(self):
        broken = _copy(self.plan)
        self.candidate(broken, "PC-STATED-COUNT-SHORT")["statement"] = "足りなければできるだけ処理する"
        self.assert_detects(broken, "範囲の分からない言い方")

    def test_detects_missing_alternative(self):
        broken = _copy(self.plan)
        self.candidate(broken, "PC-CHECK-SIDE-ORDER")["alternatives"] = []
        self.assert_detects(broken, "代替案")

    def test_detects_continuable_scene_with_open_defect(self):
        broken = _copy(self.plan)
        # 停止コードの名前は書かない（停止の方針の台帳がテストの中の停止コードの文字列を数えるので、設計案のデータから引く）
        # v0.148: 未修正の不具合と組になる場面がなくなった（DEFECT_COUPLING が空）ので、壊した設計案に組を 1 つ加えてから確かめる（今の設計案に組があるかによらず、
        # 「不具合のある場面を続けられるとする」設計案を見つけることを確かめる）
        target = next((t for c in broken["candidates"] for t in c["targets"] if t["scene"] in broken["defect_coupling"]), None)
        if target is None:
            target = next(t for c in broken["candidates"] for t in c["targets"])
            broken["defect_coupling"][target["scene"]] = "PSP-TEST-OPEN-DEFECT"
        target["coverage"] = "full"
        self.assert_detects(broken, "blocked_by_defect でない")

    def test_detects_broken_references(self):
        broken = _copy(self.plan)
        self.candidate(broken, "PC-CHECK-DOUBLE-KNOCKOUT")["depends_on"] = ["PC-NOT-DEFINED"]
        self.assert_detects(broken, "依存・関係の PC-NOT-DEFINED がない")
        broken = _copy(self.plan)
        self.candidate(broken, "PC-UP-TO-ZERO")["decision_refs"] = ["DEC-NOT-DEFINED"]
        self.assert_detects(broken, "判断事項 DEC-NOT-DEFINED")
        broken = _copy(self.plan)
        broken["whole_game_channels"][0]["scenes"].append("SCENE-NOT-IN-LEDGER")
        self.assert_detects(broken, "場面 SCENE-NOT-IN-LEDGER がない")

    def test_detects_whole_game_flag_mismatch(self):
        # 対戦全体を止める場面を対象に持つ規約案を、全体停止の規約にしないと、優先の付け方がずれる
        broken = _copy(self.plan)
        scenes = {s["id"]: s for s in broken["scenes"]}
        c = next(c for c in broken["candidates"] if c.get("whole_game") and any(scenes[t["scene"]]["whole_game"] for t in c["targets"]))
        c["whole_game"] = False
        self.assert_detects(broken, "対戦全体を止める規約にしていない")

    def test_detects_count_drift(self):
        broken = _copy(self.plan)
        broken["counts"]["candidate_scenes_unique"] += 1
        self.assert_detects(broken, "集計")

    def test_detects_generic_code_as_research_question(self):
        broken = _copy(self.plan)
        s = next(s for s in broken["scenes"] if s["family"] == "PF-RUNTIME-GENERIC")
        s["plan_class"] = "A"
        s["individual_reason"] = "x"
        self.assert_detects(broken, "名前が UNRESOLVED だけ")

    def test_detects_code_level_target_for_split_code(self):
        broken = _copy(self.plan)
        parent = next(s["parent"] for s in broken["scenes"] if s["parent"])  # 事例を分けたコード（コードそのものは場面ではない）
        self.candidate(broken, "PC-USE-WITHOUT-TARGET")["targets"].append({"scene": parent, "coverage": "unverified"})
        self.assert_detects(broken, f"対象 {parent} が場面にない")

    def test_rule_targets_are_research_codes_only(self):
        scenes = {s["id"]: s for s in self.plan["scenes"]}
        for c in self.plan["candidates"]:
            for t in c["targets"]:
                self.assertEqual(scenes[t["scene"]]["entry_kind"], "research_stop_code", (c["id"], t["scene"]))

    def test_existing_user_specs_not_generalized(self):
        # ひかるバンギラス neo4-082 の指定を、数の不足の規約の対象・根拠にしない（除外に明記する）
        for cid in ("PC-COIN-COUNT-SHORT", "PC-STATED-COUNT-SHORT"):
            self.assertTrue(any("neo4-082" in e for e in self.candidate(self.plan, cid)["excludes"]), cid)
        # サイドを取る順番の利用者指定を、ポケモンチェックへ自動で広げない
        side = self.candidate(self.plan, "PC-CHECK-SIDE-ORDER")
        self.assertTrue(any("USER-PRIZE-ORDER-ALWAYS-CHOSEN" in e and "広げない" in e for e in side["excludes"]))


if __name__ == "__main__":
    unittest.main()
