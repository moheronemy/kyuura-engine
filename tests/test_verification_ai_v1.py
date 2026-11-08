"""検証用 AI の V1 のテスト（docs/verification-ai-v1.md 7 章）。

- StageProcedureTest: 段ごとの方式（V0 と同じ）の選択の手順（選ぶ数 → 重ならない順の選択。任意の段を省くのは選ぶ数 0 の 1 つ）
- TupleTest: uniform-tuple の列挙が、既知の入力の組を過不足なく返す（options_by_choice・upstream_stages/after・options_by_path・options_from_stage・
  total_units・choose_value・並びの扱い）。上限を超えたら段ごとの方式に戻し、戻した理由を記録する。実際の盤面（カツラの 2 枚目）の組の数
- MetricsTest: 計測の数の関係（選んだ = 作れた + 作れなかった など）・範囲の外の理由・保存した記録からの数え直しとの一致・check を経ない送信がない
- ReproduceTest: 保存した実行との単独の比べ（同じ条件なら一致・意味の列を変えたら不一致）

確率は、固定の seed での具体的な選択と小さな既知の集合だけで確かめる（揺れる統計の検定・大量の抽選を合格の条件にしない）。対戦はどれも上限の小さな対戦。
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from tests.test_legal_actions_u7_5g_energy2 import blaine
from tools.verification_ai import actions as B
from tools.verification_ai import metrics as M
from tools.verification_ai import records as R
from tools.verification_ai import run_v1
from tools.verification_ai import runner as V
from tools.verification_ai.policies import STAGE, TUPLE, UniformPolicy

REQ = {"contract": "kyuura-client-api", "format": 1}


def opt(oid, **kw):
    return {"id": oid, "eligible": True, "processability": "supported", **kw}


class Log:
    """呼ばれた場面と選べる数を記録し、決まった位置を選ぶ方策（テスト用）。"""

    distribution = STAGE

    def __init__(self, indexes):
        self.indexes, self.calls = list(indexes), []

    def choose(self, purpose, items, context):
        self.calls.append((purpose, len(items)))
        return self.indexes.pop(0) % len(items), f"log:{purpose}"


def small(distribution=STAGE, **limits):
    return V.Config(distribution=distribution, limits=V.Limits(**{"operations": 30, "seconds": 60, **limits}))


SET3 = [opt("o1"), opt("o2"), opt("o3")]


def tuples(stages, **kw):
    return [tuple(c) for c, _m in B.enumerate_inputs(stages, **kw)]


class StageProcedureTest(unittest.TestCase):
    def test_count_then_ordered_picks(self):
        """選ぶ数が 0〜2 の段: まず選ぶ数を [0, 1, 2] から 1 つ、次に残りの選べるものから 1 つずつ（並びの区分によらず、選んだ順が送る並び）。"""
        stage = {"stage": 1, "input": "choose_option", "count": {"min": 0, "max": 2}, "order": "not_significant", "options": SET3}
        policy = Log([2, 2, 0])
        choices, picks, _m = B.build_choices([stage], policy, {})
        self.assertEqual(policy.calls, [("count", 3), ("option", 3), ("option", 2)])
        self.assertEqual(choices, ["o3", "o1"])  # not_significant でも並びは選んだ順（段ごとの方式は並びを数えない区別をしない）
        self.assertEqual([p["purpose"] for p in picks], ["count", "option", "option"])

    def test_decline_is_count_zero(self):
        stage = {"stage": 1, "input": "choose_option", "count": {"min": 0, "max": 1}, "options": [opt("o1")], "decline": True}
        policy = Log([0])
        self.assertEqual(B.build_choices([stage], policy, {})[0], [])
        self.assertEqual(policy.calls, [("count", 2)])  # 省く（0 個）と 1 個を同じ重みで選ぶ

    def test_single_option_uses_no_draw(self):
        stage = {"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1")]}
        policy = Log([0])
        B.build_choices([stage], policy, {})
        self.assertEqual(policy.calls, [("option", 1)])

    def test_fixed_seed_concrete_pick(self):
        stage = {"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": SET3}
        self.assertEqual(B.build_choices([stage], UniformPolicy("fixed-seed-1"), {})[0], B.build_choices([stage], UniformPolicy("fixed-seed-1"), {})[0])


class TupleTest(unittest.TestCase):
    def test_order_kept_or_not(self):
        base = {"stage": 1, "input": "choose_option", "count": {"min": 0, "max": 2}, "options": SET3}
        keep = tuples([{**base, "order": "significant"}])
        self.assertEqual(len(keep), 1 + 3 + 6)
        self.assertIn(("o2", "o1"), keep)
        same = tuples([{**base, "order": "not_significant"}])
        self.assertEqual(same, [(), ("o1",), ("o2",), ("o3",), ("o1", "o2"), ("o1", "o3"), ("o2", "o3")])
        self.assertEqual(len(tuples([{k: v for k, v in base.items()}])), 10)  # order がない 2 個以上の段は並びを数える（推測で捨てない）

    def test_options_by_choice(self):
        stages = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1"), opt("o2")]},
                  {"stage": 2, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o3"), opt("o4")], "depends_on_stage": 1,
                   "options_by_choice": {"o1": [{"option": "o3"}, {"option": "o4"}], "o2": [{"option": "o4", "eligible": False}]}}]
        self.assertEqual(tuples(stages), [("o1", "o3"), ("o1", "o4")])

    def test_upstream_after(self):
        stages = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1"), opt("o2")]},
                  {"stage": 2, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o3", after="o1"), opt("o4", after="o2"), opt("o5", after="o2")],
                   "depends_on_stage": 1, "upstream_stages": [1], "options_by_choice": {"o1": [{"option": "o3"}], "o2": [{"option": "o4"}, {"option": "o5"}]}}]
        self.assertEqual(tuples(stages), [("o1", "o3"), ("o2", "o4"), ("o2", "o5")])

    def test_options_by_path(self):
        stages = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1"), opt("o2")]},
                  {"stage": 2, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o3")], "depends_on_stage": 1,
                   "options_by_choice": {"o1": [{"option": "o3"}], "o2": [{"option": "o3"}]}},
                  {"stage": 3, "input": "choose_option", "count": {"min": 0, "max": 1}, "options": [opt("o4")], "decline": True, "path_stages": [1, 2],
                   "options_by_path": {"o1/o3": [{"option": "o4"}]}, "order": "not_applicable"}]
        self.assertEqual(tuples(stages), [("o1", "o3"), ("o1", "o3", "o4"), ("o2", "o3")])

    def test_options_from_stage(self):
        stages = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1"), opt("o2"), opt("o3", eligible=False)]},
                  {"stage": 2, "input": "choose_option", "count": {"min": 0, "max": 5}, "options_from_stage": 1, "distinct_across_stages": True, "order": "significant"}]
        self.assertEqual(tuples(stages), [("o1",), ("o1", "o2"), ("o2",), ("o2", "o1")])

    def test_total_units_keeps_order(self):
        stages = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1")]},
                  {"stage": 2, "input": "choose_option", "count": {"min": 0, "max": 3}, "total_units": {"min": 2, "max": 2}, "order": "significant",
                   "options": [opt("o2", units=2), opt("o3", units=1), opt("o4", units=1)]}]
        self.assertEqual(tuples(stages), [("o1", "o2"), ("o1", "o3", "o4"), ("o1", "o4", "o3")])

    def test_choose_value(self):
        self.assertEqual(tuples([{"stage": 1, "input": "choose_value", "range": {"min": 0, "max": 2}, "count": {"min": 1, "max": 1}}]), [(0,), (1,), (2,)])

    def test_limits_and_fallback(self):
        big = [{"stage": 1, "input": "choose_option", "count": {"min": 0, "max": 6}, "order": "significant", "options": [opt(f"o{i}") for i in range(1, 9)]}]
        with self.assertRaises(B.TupleLimit) as caught:
            B.enumerate_inputs(big)
        self.assertEqual(caught.exception.reason, "tuple_limit")
        with self.assertRaises(B.TupleLimit) as caught:
            B.enumerate_inputs(big, limit=10**9, node_limit=100)
        self.assertEqual(caught.exception.reason, "node_limit")
        policy = UniformPolicy("fallback", TUPLE)
        choices, picks, _m, method = B.build_choices_tuple(big, policy, {})
        self.assertEqual((method["method"], method["reason"]), ("stage_fallback", "tuple_limit"))
        self.assertEqual(picks[0]["purpose"], "count")  # 段ごとの方式の手順で選んだ
        self.assertEqual(len(set(choices)), len(choices))

    def test_tuple_choice_gets_all_tuples(self):
        stages = [{"stage": 1, "input": "choose_option", "count": {"min": 0, "max": 2}, "order": "significant", "options": SET3}]
        policy = Log([7])
        choices, picks, meaning, method = B.build_choices_tuple(stages, policy, {})
        self.assertEqual(policy.calls, [("tuple", 10)])  # 方策は完成した組の全体から 1 回だけ選ぶ
        self.assertEqual((method, picks[0]["items"]), ({"method": "tuple", "tuples": 10}, 10))
        self.assertEqual(choices, list(tuples(stages)[7]))
        with self.assertRaises(B.Unbuildable):
            B.build_choices_tuple([{"stage": 1, "input": "choose_option", "count": {"min": 2, "max": 2}, "options": [opt("o1")]}], policy, {})

    def test_unknown_order_stops(self):
        with self.assertRaises(B.ContractUnknown):
            B.enumerate_inputs([{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": SET3, "order": "maybe"}])

    def test_real_energy2_count(self):
        """実際の盤面（カツラの 2 枚目）: 組の数が、段の契約から別に数えた数と同じで、どの組も check を通る（テストで確かめる。列挙そのものは check を呼ばない）。"""
        hub = ClientHub.from_state(blaine())
        me = hub.player(0)
        r = me.handle({**REQ, "type": "candidates"})["response"]
        c = next(x for x in r["candidates"] if x["kind"] == L.KIND_ATTACH_ENERGY)
        stages = me.handle({**REQ, "type": "inputs", "game": r["game"], "revision": r["revision"], "candidate": c["id"]})["response"]["stages"]
        found = B.enumerate_inputs(stages, B.FALLBACK_PROCESSABILITY)
        allowed = lambda o: B.option_allowed(o, B.FALLBACK_PROCESSABILITY)
        stage2 = {o["id"]: o for o in stages[1]["options"]}
        stage3 = {o["id"]: o for o in stages[2]["options"]}
        expected = 0
        for first in (o for o in stages[0]["options"] if allowed(o)):
            for ref in stages[1]["options_by_choice"].get(first["id"], []):
                if allowed(ref) and allowed(stage2[ref["option"]]):
                    refs = stages[2]["options_by_path"].get(f"{first['id']}/{ref['option']}", [])
                    expected += 1 + sum(1 for x in refs if allowed(x) and allowed(stage3[x["option"]]))
        self.assertEqual(len(found), expected)
        for choices, _m in found:
            checked = me.handle({**REQ, "type": "check", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": choices})
            self.assertTrue(checked["response"]["valid"], choices)


class MetricsTest(unittest.TestCase):
    def test_fetch_counts_and_reasons(self):
        m = M.Metrics()
        cands = {"situation": "actor_to_act", "empty_reason": None, "coverage": {"residual": {"present": [{"id": "R-5"}]}},
                 "candidates": [{"id": "c1", "kind": "end_turn", "processability": "may_stop_later", "input_disclosure": "no_input"},
                                {"id": "c2", "kind": "use_power", "processability": "not_implemented", "input_disclosure": "unconfirmed"},
                                {"id": "c3", "kind": "use_power", "processability": "may_stop_later", "input_disclosure": "confirmed"}]}
        in_scope = [cands["candidates"][0], cands["candidates"][2]]
        for _ in range(2):
            m.fetch(4, cands, in_scope, {"c2": "input_withheld"})
        d = m.to_dict()
        power = d["kinds"]["use_power"]
        self.assertEqual((d["fetches"], d["states"]), (2, 1))  # 同じ状態の 2 回の取得
        self.assertEqual((power["offered_fetches"], power["offered_states"], power["in_scope_fetches"], power["in_scope_states"]), (4, 1, 2, 1))
        self.assertEqual((power["excluded"], power["selection_opportunities"], power["expected_selections"]), ({"input_withheld": 2}, 2, 1.0))
        self.assertEqual(d["axes"]["residual_present"], {"R-5": 2})

    def assert_consistent(self, result):
        for kind, k in result["metrics"]["kinds"].items():
            with self.subTest(kind=kind):
                self.assertEqual(k["selected"], k["build_ok"] + sum(k["build_failed"].values()))
                self.assertEqual(k["check_valid"] + k["check_invalid"], k["build_ok"] - k["already_tried"])
                self.assertEqual(k["submitted"], k["check_valid"])  # check を通った入力だけを送る
                self.assertEqual(sum(k["outcome"].values()), k["submitted"])
                self.assertEqual(sum(k["after_accept"].values()), k["outcome"].get("accepted", 0))
                self.assertLessEqual(k["offered_states"], k["offered_fetches"])
        self.assertLessEqual(result["metrics"]["states"], result["metrics"]["fetches"])
        self.assertIn(result["metrics"]["fetches"] - result["counters"]["attempts"], (0, 1))
        for entry in result["trace"]:
            if entry.get("submit"):
                self.assertTrue(entry["check"]["response"]["valid"])
                self.assertEqual(entry["check"]["response"]["refusal"], None)

    def test_small_games_both_distributions(self):
        for dist in (STAGE, TUPLE):
            with self.subTest(dist):
                result = V.run_game(small(dist))
                self.assertEqual(result["distribution"], dist)
                self.assert_consistent(result)
                if dist == TUPLE:
                    methods = [e["build_method"]["method"] for e in result["trace"] if e.get("build_method")]
                    self.assertTrue(methods)
                    self.assertTrue(all(m in ("tuple", "stage_fallback") for m in methods))

    def test_offline_recount_matches(self):
        result = V.run_game(small(operations=60))
        logs = [row for rows in result["actor_logs"].values() for row in rows]
        for kind, k in result["metrics"]["kinds"].items():
            with self.subTest(kind=kind):
                again = M.kind_opportunities(result["trace"], logs, kind)
                self.assertEqual((again["offered_fetches"], again["offered_states"], again["in_scope_fetches"], again["selected"]),
                                 (k["offered_fetches"], k["offered_states"], k["in_scope_fetches"], k["selected"]))
                self.assertAlmostEqual(again["expected_selections"], k["expected_selections"], places=3)


class ReproduceTest(unittest.TestCase):
    def test_against_saved_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = V.Config(limits=V.Limits(operations=40, seconds=60), run_id="base-a")
            result = V.run_game(config)
            base = root / "verifier" / "runs" / "base" / "a"
            header = run_v1.game_header(config, R.identity(None), [], result, "t0", "t1")
            run_v1.write_game(base, header, result, {})
            self.assertEqual(run_v1.reproduce(base, root, "test", []), 0)
            got = json.loads((root / "verifier" / "runs" / "v1-repro-of-base-a" / "verification.json").read_text(encoding="utf-8"))
            self.assertTrue(got["reproduced"] and got["engine_commands_equal"] and got["meaning_comparison"]["full_match"])
            rows = run_v1.read_jsonl(base / "meaning.jsonl")
            rows[3]["meaning"] = [{"changed": True}]
            R.write_jsonl(base / "meaning.jsonl", rows)
            self.assertEqual(run_v1.reproduce(base, root, "test", []), 1)  # 違いを隠さない
            got = json.loads((root / "verifier" / "runs" / "v1-repro-of-base-a" / "verification.json").read_text(encoding="utf-8"))
            self.assertEqual(got["meaning_comparison"]["first_difference"], 3)


if __name__ == "__main__":
    unittest.main()
