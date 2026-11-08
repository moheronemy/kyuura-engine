"""検証用 AI の V3-1（通常の進行の中の negative）のテスト（docs/verification-ai-v3-1.md 6 章）。

小さな JSON の例と偽物で、変異が 1 条件だけを変えること・前提がなければ not_applicable・変異の乱数が方策とゲームに影響しないこと・refused と rejected の判定の違い・
正当な取っ手の失効を誤って疑わないこと・既にある更新と新しい更新の区別・状態・乱数・ログ・配信の変化の検出・元の入力の check への復帰と通常の送信が 1 回だけのこと・副作用の
疑いで止めて証跡を残すことを確かめる。対戦はどれも上限の小さな対戦。
"""

from __future__ import annotations

import ast
import pathlib
import random
import unittest
from unittest import mock

from kyuura_engine import diagnostics as D
from kyuura_engine import preset_deck
from kyuura_engine.client_api import ClientHub
from tools.verification_ai import judge as J
from tools.verification_ai import negative as N
from tools.verification_ai import records as R
from tools.verification_ai import runner as V
from tools.verification_ai.records import RecordingGame
from tools.verification_ai.run_v1 import engine_commands
from tools.verification_ai.run_v3 import NegativeSession

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQ = {"contract": "kyuura-client-api", "format": 1}


def opt(oid, **kw):
    return {"id": oid, "eligible": True, "processability": "may_stop_later", **kw}


PAIR = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1"), opt("o2")]},
        {"stage": 2, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o3"), opt("o4")], "depends_on_stage": 1,
         "options_by_choice": {"o1": [{"option": "o3", "eligible": True, "processability": "may_stop_later"},
                                      {"option": "o4", "eligible": False, "processability": "unresolved_ruling"}],
                               "o2": [{"option": "o4", "eligible": True, "processability": "may_stop_later"}]}}]
MULTI = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1")]},
         {"stage": 2, "input": "choose_option", "count": {"min": 0, "max": 3}, "options": [opt("o2"), opt("o3"), opt("o4")]}]


def rng():
    return random.Random("t")


class MutationTest(unittest.TestCase):
    def check_single(self, kind, stages, choices):
        mutated, change = N.mutate(kind, stages, choices, rng())
        self.assertIsNotNone(mutated, change)
        self.assertTrue(N.single_difference(choices, mutated), (kind, choices, mutated))
        return mutated, change

    def test_unknown_option(self):
        mutated, change = self.check_single("unknown_option", PAIR, ["o1", "o3"])
        self.assertNotIn(change["after"], {"o1", "o2", "o3", "o4"})

    def test_duplicate_and_count(self):
        mutated, _ = self.check_single("duplicate", MULTI, ["o1", "o2"])
        self.assertEqual(mutated, ["o1", "o2", "o2"])
        self.assertIsNone(N.mutate("duplicate", PAIR, ["o1", "o3"], rng())[0])  # どの段も上限が 1
        at_max = [MULTI[0], {**MULTI[1], "count": {"min": 0, "max": 2}}]
        self.assertEqual(self.check_single("count_over", at_max, ["o1", "o2", "o3"])[0], ["o1", "o2", "o3", "o4"])
        self.assertEqual(N.mutate("count_over", MULTI, ["o1", "o2", "o3", "o4"], rng())[1], {"not_applicable": "no_extra_option"})  # 足せるものがない
        self.assertIsNone(N.mutate("count_over", MULTI, ["o1", "o2"], rng())[0])  # 上限でない: not_applicable
        self.assertEqual(self.check_single("count_under", PAIR, ["o1", "o3"])[0], ["o1"])
        self.assertEqual(N.mutate("count_under", MULTI, ["o1"], rng())[1], {"not_applicable": "last_stage_not_at_min"})

    def test_path_mix_uses_option_of_other_path_only(self):
        mutated, change = self.check_single("path_mix", PAIR, ["o2", "o4"])
        self.assertEqual(mutated, ["o2", "o3"])  # o3 は o1 の参照にだけある
        self.assertIsNone(N.mutate("path_mix", PAIR, ["o1", "o3"], rng())[0])  # o4 は o1 の参照にもある: 別の経路だけの選ぶものがない
        three = [PAIR[0], PAIR[1], {"stage": 3, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o5")], "depends_on_stage": 2,
                                    "options_by_choice": {"o3": [{"option": "o5"}], "o4": [{"option": "o5"}]}}]
        self.assertIsNone(N.mutate("path_mix", three, ["o2", "o4", "o5"], rng())[0])  # 後の段が依存する段は変えない（条件が重なる）

    def test_non_executable(self):
        mutated, _ = self.check_single("non_executable", PAIR, ["o1", "o3"])
        self.assertEqual(mutated, ["o1", "o4"])  # 同じ経路（o1）の参照で、実行できない区分
        self.assertIsNone(N.mutate("non_executable", PAIR, ["o2", "o4"], rng())[0])

    def test_not_applicable_layouts(self):
        self.assertEqual(N.mutate("unknown_option", [], [], rng())[1], {"not_applicable": "no_input"})
        value = [{"stage": 1, "input": "choose_value", "range": {"min": 0, "max": 2}, "count": {"min": 1, "max": 1}}]
        self.assertEqual(N.mutate("unknown_option", value, [1], rng())[1], {"not_applicable": "value_stage"})
        placement = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1"), opt("o2")]},
                     {"stage": 2, "input": "choose_option", "count": {"min": 0, "max": 5}, "options_from_stage": 1, "distinct_across_stages": True}]
        self.assertEqual(N.mutate("unknown_option", placement, ["o1", "o2"], rng())[1], {"not_applicable": "stage_layout_not_mapped"})

    def test_single_difference(self):
        self.assertTrue(N.single_difference(["a", "b"], ["a", "c"]))
        self.assertFalse(N.single_difference(["a", "b"], ["c", "d"]))
        self.assertTrue(N.single_difference(["a"], ["a", "a"]))
        self.assertFalse(N.single_difference(["a"], ["b", "c"]))

    def test_negative_module_does_not_import_engine(self):
        tree = ast.parse((ROOT / "tools" / "verification_ai" / "negative.py").read_text(encoding="utf-8"))
        imported = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)] + [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        self.assertFalse([m for m in imported if "kyuura" in m or m.startswith(".")])


class JudgeTest(unittest.TestCase):
    def test_normal_refused_vs_rejected(self):
        basic = {"kind": "play_basic", "processability": "may_stop_later", "reasons": []}
        meaning = [{"stage": 1, "option": {"eligible": True}}]
        self.assertEqual(J.judge_normal(basic, meaning, {"ok": True, "outcome": "refused", "refusal": {"code": "CANDIDATE_INPUT_INVALID"}})[0], J.SUSPECT)
        rejected = lambda cat, did="X": {"ok": True, "outcome": D.REJECTED, "verifier": {"category": cat, "diagnostic_id": did}}
        self.assertEqual(J.judge_normal(basic, meaning, rejected(D.INVALID_INPUT))[0], J.SUSPECT)  # 前の確かめを満たす種類の invalid_input
        self.assertEqual(J.judge_normal(basic, meaning, rejected(D.RULING_UNRESOLVED))[0], J.KNOWN_STOP)
        self.assertEqual(J.judge_normal({**basic, "processability": "supported"}, meaning, rejected(D.RULING_UNRESOLVED))[0], J.SUSPECT)
        self.assertEqual(J.judge_normal({**basic, "processability": "unverified"}, meaning, rejected(D.INVALID_INPUT))[0], J.NORMAL_REJECTION)
        attack = {"kind": "use_attack", "processability": "may_stop_later"}
        self.assertEqual(J.judge_normal(attack, [], rejected(D.INVALID_INPUT))[0], J.NORMAL_REJECTION)  # 受理を保証しない種類
        self.assertEqual(J.judge_normal(attack, [], rejected(D.UNMAPPED, "DIAGNOSTIC_UNMAPPED"))[0], J.SUSPECT)  # コード表にない
        self.assertEqual(J.judge_normal(basic, meaning, {"ok": True, "outcome": D.ACCEPTED})[0], J.EXPECTED)

    def test_negative_verdicts(self):
        refused = lambda code, refetch: {"ok": True, "outcome": "refused", "refusal": {"code": code}, "refetch_required": refetch}
        check = lambda code, refetch: {"ok": True, "response": {"valid": False, "refusal": {"code": code}}, "refetch_required": refetch}
        ok = [("check", check("CANDIDATES_STALE", True)), ("submit", refused("CANDIDATES_STALE", True))]
        self.assertEqual(J.judge_negative("CANDIDATES_STALE", True, ok, []), (J.EXPECTED, []))  # 受理のあとの正当な失効は疑わない
        self.assertEqual(J.judge_negative("CANDIDATE_INPUT_INVALID", False, [("check", check("CANDIDATE_NOT_EXECUTABLE", False))], [])[0], J.UNDETERMINED)
        self.assertEqual(J.judge_negative("CANDIDATE_INPUT_INVALID", False, [("submit", {"ok": True, "outcome": D.ACCEPTED})], [])[0], J.SUSPECT)
        self.assertEqual(J.judge_negative("CANDIDATE_INPUT_INVALID", False, [("check", {"ok": True, "response": {"valid": True}})], [])[0], J.SUSPECT)
        self.assertEqual(J.judge_negative("CANDIDATES_STALE", True, [("check", check("CANDIDATES_STALE", False))], [])[0], J.SUSPECT)
        self.assertEqual(J.judge_negative("CANDIDATES_STALE", True, ok, ["checks.rng"])[0], J.SUSPECT)
        self.assertEqual(J.judge_recovery({"response": {"valid": False, "refusal": {"code": "CANDIDATES_STALE"}}}, [])[0], J.SUSPECT)
        self.assertEqual(J.judge_recovery({"response": {"valid": True}}, []), (J.EXPECTED, []))

    def test_termination(self):
        self.assertEqual(J.judge_termination("halted_known", "may_stop_later")[0], J.KNOWN_STOP)
        self.assertEqual(J.judge_termination("halted_known", "supported")[0], J.UNDETERMINED)
        self.assertEqual(J.judge_termination("halted_unclassified", None)[0], J.SUSPECT)
        self.assertEqual(J.judge_termination("limit_accepted", None), (J.EXPECTED, ["tool_limit"]))


class SnapshotTest(unittest.TestCase):
    def test_existing_vs_new_updates_and_state_changes(self):
        decks = (preset_deck("hitmonchan-dewgong").cards(), preset_deck("venusaur-parasect").cards())
        game, _ = RecordingGame.start(*decks, 12)
        hub = ClientHub(game)
        me = hub.player(0)
        r = me.handle({**REQ, "type": "candidates"})["response"]
        c = r["candidates"][0]
        stage = me.handle({**REQ, "type": "inputs", "game": r["game"], "revision": r["revision"], "candidate": c["id"]})["response"]["stages"][0]
        choice = [next(o["id"] for o in stage["options"] if o["eligible"])]
        accepted = me.handle({**REQ, "type": "submit", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": choice})
        self.assertEqual(accepted["outcome"], D.ACCEPTED)  # 更新を取り出していない（既にある未取得の更新）
        before = J.snapshot(game, hub)
        self.assertGreater(before["outbox"]["1"], 0)
        self.assertEqual(J.compare(before, J.snapshot(game, hub)), [])  # 既にある更新を新しい更新として数えない・数えても取り出さない
        self.assertEqual(J.snapshot(game, hub)["outbox"], before["outbox"])
        hub._outbox[1].append({"fake": True})
        self.assertEqual(J.compare(before, J.snapshot(game, hub)), ["new_update:1"])
        hub._outbox[1].pop()
        r = hub.player(1).handle({**REQ, "type": "candidates"})["response"]
        c = r["candidates"][0]
        stage = hub.player(1).handle({**REQ, "type": "inputs", "game": r["game"], "revision": r["revision"], "candidate": c["id"]})["response"]["stages"][0]
        choice = [next(o["id"] for o in stage["options"] if o["eligible"])]
        hub.player(1).handle({**REQ, "type": "submit", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": choice})
        changed = J.compare(before, J.snapshot(game, hub))
        for name in ("state_object_replaced", "checks.state", "update_number", "new_update:0"):
            self.assertIn(name, changed)

    def test_same_object_with_changed_checks_is_detected(self):
        before = {"state_object": 1, "checks": {"state": "a", "rng": "r", "log_length": 3}, "outbox": {"0": 0}, "update_number": 4, "failure": False}
        after = {**before, "checks": {"state": "a", "rng": "r2", "log_length": 4}}
        self.assertEqual(J.compare(before, after), ["checks.log_length", "checks.rng"])  # 同じオブジェクトでも確認値で見つける


def small(seed=12, ops=60):
    return V.Config(game_seed=seed, policy_seed=seed, host_seed=seed, limits=V.Limits(operations=ops, seconds=60))


class SessionTest(unittest.TestCase):
    def run_with(self, seed=12, positions=(2, 3, 5, 8, 13, 21, 30), negative_seed=None):
        session = NegativeSession(negative_seed or seed, list(positions))
        return V.Runner(small(seed), negative=session).run(), session

    def test_rng_isolation_and_same_normal_progress(self):
        plain = V.Runner(small()).run()
        a, _ = self.run_with()
        b, _ = self.run_with(negative_seed=99, positions=(4, 6, 9))
        for r in (a, b):
            self.assertEqual(R.meaning_sequence(r["trace"]), R.meaning_sequence(plain["trace"]))
            self.assertEqual(engine_commands(r["record"].data), engine_commands(plain["record"].data))
            self.assertEqual({k: v["draws"] for k, v in r["policies"].items()}, {k: v["draws"] for k, v in plain["policies"].items()})

    def test_recovery_then_single_submit_and_stale_after_accept(self):
        result, session = self.run_with()
        self.assertEqual(result["termination"]["class"], V.LIMIT_OPERATIONS)
        trace = result["trace"]
        recoveries = [i for i, e in enumerate(trace) if e.get("type") == "negative_recovery"]
        self.assertTrue(recoveries)
        for i in recoveries:
            n = trace[i]["attempt"]
            self.assertEqual(trace[i]["verdict"], J.EXPECTED)
            submits = [e for e in trace if e.get("type") == "attempt" and e["n"] == n and e.get("submit")]
            self.assertEqual(len(submits), 1)  # 通常の送信は 1 回だけ（復帰の確かめは check）
            attempt_index = next(j for j, e in enumerate(trace) if e.get("type") == "attempt" and e["n"] == n)
            self.assertLess(attempt_index, i)
        for i, e in enumerate(trace):
            if e.get("type") == "negative" and e.get("mutation") == "stale_after_accept" and e.get("status") == "run":
                attempt = next(x for x in trace if x.get("type") == "attempt" and x["n"] == e["attempt"])
                self.assertEqual(attempt["submit"]["outcome"], D.ACCEPTED)  # 受理のあとに試した
                self.assertEqual([r["response"].get("refusal", (r["response"].get("response") or {}).get("refusal"))["code"] for r in e["responses"]],
                                 ["CANDIDATES_STALE", "CANDIDATES_STALE"])
        summary = result["negative"]
        self.assertLessEqual(summary["requests"]["check"] + summary["requests"]["submit"], 60)
        self.assertTrue(all(key.endswith(":expected") for key in summary["verdicts"]), summary["verdicts"])

    def test_side_effect_stops_and_keeps_evidence(self):
        with mock.patch("tools.verification_ai.judge.compare", return_value=["checks.rng"]):
            result, session = self.run_with(positions=(2,))
        self.assertEqual(result["termination"]["class"], V.NEGATIVE_SIDE_EFFECT)
        rows = [e for e in result["trace"] if e.get("type") == "negative" and e.get("status") == "run"]
        self.assertEqual(len(rows), 1)  # 同じ不正な要求を繰り返さない
        self.assertEqual((rows[0]["verdict"], rows[0]["changed"]), (J.SUSPECT, ["checks.rng"]))
        self.assertIn("before", rows[0])
        self.assertIsNotNone(result["record"])
        self.assertEqual(result["judge_termination"]["verdict"], J.SUSPECT)


if __name__ == "__main__":
    unittest.main()
