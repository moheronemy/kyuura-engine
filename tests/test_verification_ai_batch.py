"""検証用 AI の上限つき逐次バッチのテスト（docs/verification-ai-batch.md 7 章）。

小さな偽物の adapter と一時ディレクトリで、計画の照合・完了局の再開時の飛ばし・破損と不一致の検出・書き込みの途中や完了マーカーの前の中断・未完了の attempt の保持・
二重起動と残ったロック・全体の時間・局数・証跡の量の上限・停止方針・集計だけの再実行・局のあとに結果を持ち続けないことを確かめる。OS のプロセスの終了・本当のメモリの
枯渇は使わない（例外を偽物から投げる）。最後に本物の adapter で、計画の設定の経路が既存の方策の行動の指紋（v2_repeat の ACTION_GOLDEN）を変えないことを確かめる。
"""

from __future__ import annotations

import gc
import json
import shutil
import tempfile
import unittest
import weakref
from pathlib import Path

from tools.verification_ai import batch as B


def summary(termination="game_over", submits=None, term_verdict="expected", anomalies=(), replay_ok=True, correspondence=0, undetermined=(), known_stop=0,
            content=None, term_reasons=()):
    return {"termination": termination, "termination_detail": {}, "counters": {"turns": 2, "accepted": 3, "operations": 4},
            "anomalies": list(anomalies), "judge": {"submits": submits or {"expected": 3}, "accepted_content": content or {},
                                                    "termination": {"verdict": term_verdict, "reasons": list(term_reasons), "class": termination, "halt": None},
                                                    "undetermined": [dict(u) for u in undetermined], "known_stop": known_stop},
            "replay_run": {"expected": "succeeded", "status": "succeeded" if replay_ok else "mismatch", "matches_expectation": replay_ok},
            "correspondence_problems": correspondence, "elapsed_seconds": 0.5, "sequences": {"action": {"sha256": "a"}, "contract": {"sha256": "c"}}}


RESULT = {"coverage": {"chosen_kind": {"end_turn": 2}, "input": {"choose_option": 1}}, "metrics": {"axes": {"decision_kind": {"x": 1}}, "kinds": {
    "end_turn": {**{f: 1 for f in B.FUNNEL}, "outcome": {"accepted": 1}, "build_failed": {}, "excluded": {}}}}}


EVIDENCE_MISSING = {"source": "termination", "attempt": None, "kind": None, "reasons": ["halt_condition_not_evidenced:UNRESOLVED_X"],
                    "category": "evidence_missing_stop"}


class Heavy:
    """局の結果の代わり（局のあとに参照が残らないことを weakref で見る）。"""

    def __init__(self, n):
        self.data = bytearray(n)


class FakeAdapter:
    def __init__(self, script=None, clock=None, step=0.0, size=10, identity=None):
        self.script = script or {}
        self.calls: list[str] = []
        self.clock = clock
        self.step = step
        self.size = size
        self.refs: list = []
        self._identity = identity or {"tool": {"name": B.TOOL_NAME, "version": 1, "digest": "tool-x"},
                                      "engine": {"version": "0.179.0", "implementation": {"behavior_digest": "beh-x"}, "runtime": {"python": "x"}}}
        self.entry_problems: list[str] = []
        self.during_play = None

    def identity(self):
        return self._identity

    def conventions_key(self, conventions):
        return (conventions or "CS-TEST@1"), {"digest": "sha256:conv"}

    def entry(self, *, game_id, mode, seed, deck0, deck1, conventions, group, game_limits=None):
        return {"game_id": game_id, "mode": mode, "comparison_group": group,
                "config": {"deck0": deck0, "deck1": deck1, "conventions": self.conventions_key(conventions)[0], "game_seed": seed, "policy_seed": seed,
                           "host_seed": seed, "limits": {"operations": 2000, **(game_limits or {})}},
                "decks": {"0": {"preset": deck0}, "1": {"preset": deck1}}, "conventions": {"key": "CS-TEST@1", "digest": "sha256:conv"},
                "policies": {"0": {"name": mode}}}

    def check_entry(self, entry):
        return list(self.entry_problems)

    def play(self, entry, plan):
        gid = entry["game_id"]
        self.calls.append(gid)
        if self.during_play is not None:
            self.during_play(gid)
        action = self.script.get(gid)
        if isinstance(action, BaseException) or (isinstance(action, type) and issubclass(action, BaseException)):
            raise action
        if self.clock is not None:
            self.clock.t += self.step
        heavy = Heavy(self.size)
        self.refs.append(weakref.ref(heavy))
        files = [(name, json.dumps({"game": gid, "name": name, "pad": len(heavy.data), "rows": []}).encode() + b"\n")
                 for name in B.REQUIRED_FILES if name != "result.json"]
        files.append(("result.json", json.dumps(RESULT).encode()))
        if self.size > 1000:
            files.append(("big.bin", bytes(heavy.data)))
        return B.GameOutput(files=files, summary=action if isinstance(action, dict) else summary())


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def no_memory():
    return {"status": "not_measured", "reason": "test"}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vai-batch-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def plan(self, adapter, seeds=(1, 2), modes=("uniform-stage",), batch="b", **limits):
        return B.make_plan(self.tmp, batch, engine_commit="e", tool_commit="t", seeds=list(seeds), modes=list(modes), deck0="d0", deck1="d1",
                           limits=B.BatchLimits(**limits), adapter=adapter)

    def run_(self, adapter, batch="b", **kw):
        kw.setdefault("memory", no_memory)
        return B.run_batch(self.tmp, batch, adapter=adapter, **kw)

    def bdir(self, batch="b"):
        return B.batch_dir(self.tmp, batch)

    def ledger(self, batch="b"):
        return B.Ledger(self.bdir(batch) / B.LEDGER).read()[0]


class PlanTest(Base):
    def test_plan_is_expanded_hashed_and_unique(self):
        a = FakeAdapter()
        plan = self.plan(a, seeds=(5, 6), modes=("uniform-stage", "rules-v2", "mixed"))
        ids = [g["game_id"] for g in plan["games"]]
        self.assertEqual(len(ids), 6)
        self.assertEqual(len(set(ids)), 6)
        self.assertEqual([g["comparison_group"] for g in plan["games"]][:3], ["d0-vs-d1/CS-TEST@1/s5"] * 3)  # 同じ条件の比較の組。game_id は別
        data = (self.bdir() / "plan.json").read_bytes()
        self.assertEqual((self.bdir() / "plan.sha256").read_text().split()[0], B.sha256_bytes(data))
        for key in ("limits", "stop_policy", "identity", "commits", "format"):
            self.assertIn(key, plan)
        self.assertEqual(plan["limits"]["max_games"], 30)
        self.assertEqual(plan["stop_policy"]["on_suspect"], "stop")
        self.assertEqual(plan["stop_policy"]["on_undetermined"], {"evidence_missing_stop": "continue", "unknown_diagnostic": "stop", "contract_unknown": "stop",
                                                                  "no_progress": "stop", "unclassified": "stop"})
        self.assertEqual(plan["stop_policy"]["on_known_stop"], "continue")
        self.assertIn("api_contract_unknown", plan["stop_policy"]["stop_terminations"])
        B.load_plan(self.bdir(), a)

    def test_plan_refuses_overwrite_too_many_games_and_duplicates(self):
        a = FakeAdapter()
        self.plan(a)
        with self.assertRaises(B.BatchRefused):
            self.plan(a)
        with self.assertRaises(B.BatchRefused):
            self.plan(a, seeds=(1, 2, 3), batch="c", max_games=2)
        self.assertFalse(self.bdir("c").exists())
        with self.assertRaises(B.BatchRefused):
            self.plan(a, seeds=(1, 1), batch="d")

    def test_changed_plan_identity_or_entry_is_refused(self):
        a = FakeAdapter()
        self.plan(a)
        path = self.bdir() / "plan.json"
        original = path.read_bytes()
        path.write_bytes(original.replace(b'"max_games": 30', b'"max_games": 31'))
        with self.assertRaises(B.BatchRefused) as cm:
            self.run_(a)
        self.assertIn("plan.sha256", cm.exception.problems[0])
        path.write_bytes(original)
        other = FakeAdapter(identity={"tool": {"digest": "other"}, "engine": {}})
        with self.assertRaises(B.BatchRefused) as cm:
            self.run_(other)
        self.assertIn("実装識別", cm.exception.problems[0])
        a.entry_problems = ["g001: デッキの確認値が違う"]
        with self.assertRaises(B.BatchRefused):
            self.run_(a)
        self.assertEqual(a.calls, [])
        self.assertFalse((self.bdir() / B.LOCK).exists())  # 断ったあともロックを残さない（自分のセッションのロック）


class ResumeTest(Base):
    def test_completed_games_are_skipped_on_resume(self):
        a = FakeAdapter()
        self.plan(a, seeds=(1, 2, 3))
        r1 = self.run_(a, stop_after_games=2)
        self.assertEqual(r1.status, "stopped_requested")
        self.assertEqual(len(a.calls), 2)
        r2 = self.run_(a)
        self.assertEqual(r2.status, "completed")
        self.assertEqual(a.calls, ["g001-uniform-stage-s1", "g002-uniform-stage-s2", "g003-uniform-stage-s3"])  # 同じ局を 2 回実行しない
        self.assertEqual(r2.skipped_complete, ["g001-uniform-stage-s1", "g002-uniform-stage-s2"])
        r3 = self.run_(a)
        self.assertEqual((r3.status, r3.ran), ("completed", []))
        self.assertEqual(len(a.calls), 3)
        agg = json.loads((self.bdir() / "aggregate.json").read_text(encoding="utf-8"))
        self.assertEqual(agg["games"], {"planned": 3, "complete": 3, "started_incomplete": 0, "not_started": 0})
        self.assertEqual(agg["attempts"]["total"], 3)

    def test_corrupted_or_foreign_results_are_not_adopted(self):
        a = FakeAdapter()
        self.plan(a, seeds=(1, 2))
        self.run_(a, stop_after_games=1)
        adir = self.bdir() / "games" / "g001-uniform-stage-s1" / "attempt-001"
        trace = adir / "trace.jsonl"
        good = trace.read_bytes()
        trace.write_bytes(good + b"x")
        with self.assertRaises(B.BatchRefused) as cm:
            self.run_(a)
        self.assertTrue(any("sha256" in p for p in cm.exception.problems))
        trace.write_bytes(good)
        (adir / "extra.txt").write_text("x")
        with self.assertRaises(B.BatchRefused):
            self.run_(a)
        (adir / "extra.txt").unlink()
        marker = json.loads((adir / B.MARKER).read_text(encoding="utf-8"))
        bad = dict(marker, game_sha256="other-config")
        (adir / B.MARKER).write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(B.BatchRefused):
            self.run_(a)
        (adir / B.MARKER).write_text(json.dumps(marker), encoding="utf-8")
        (self.bdir() / "games" / "g999-unknown").mkdir()
        with self.assertRaises(B.BatchRefused):
            self.run_(a)
        (self.bdir() / "games" / "g999-unknown").rmdir()
        self.assertEqual(len(a.calls), 1)  # 不一致のあいだは何も実行しない
        self.assertEqual(self.run_(a).status, "completed")
        self.assertEqual(len(a.calls), 2)

    def test_interrupted_write_before_marker_keeps_attempt_and_retries(self):
        a = FakeAdapter()
        self.plan(a, seeds=(1,))
        real = B.atomic_write

        def failing(path, data):
            if path.name == B.MARKER:
                raise OSError("disk full (test)")
            return real(path, data)

        B.atomic_write = failing
        try:
            r1 = self.run_(a)
        finally:
            B.atomic_write = real
        self.assertEqual(r1.status, "stopped_write_failed")
        gdir = self.bdir() / "games" / "g001-uniform-stage-s1"
        self.assertFalse((gdir / "attempt-001" / B.MARKER).exists())
        self.assertTrue((gdir / "attempt-001" / "trace.jsonl").exists())
        # 書き込みの途中（一時ファイルだけが残った）attempt も、完了と見なさない
        (gdir / "attempt-001" / ".COMPLETE.json.tmp-abc").write_text("{")
        r2 = self.run_(a)
        self.assertEqual(r2.status, "completed")
        self.assertEqual(sorted(p.name for p in gdir.iterdir()), ["attempt-001", "attempt-002"])  # 未完了の attempt を残す
        self.assertTrue((gdir / "attempt-001" / B.NOTE).exists())
        agg = B.aggregate(self.tmp, "b", adapter=a)["verifier"]
        self.assertEqual(agg["attempts"], {"total": 2, "complete": 1, "incomplete": 1, "invalid": 0})
        self.assertEqual(agg["games"]["complete"], 1)  # attempt と完了局を合算しない
        events = self.ledger()
        self.assertEqual([e["status"] for e in events if e["event"] == "attempt_end"], ["write_failed", "complete"])


class InterruptTest(Base):
    def check_interrupt(self, error):
        a = FakeAdapter(script={"g002-uniform-stage-s2": error})
        self.plan(a, seeds=(1, 2, 3))
        with self.assertRaises(type(error) if isinstance(error, BaseException) else error):
            self.run_(a)
        self.assertEqual(a.calls, ["g001-uniform-stage-s1", "g002-uniform-stage-s2"])  # 次の局を始めない
        self.assertFalse((self.bdir() / B.LOCK).exists())
        adir = self.bdir() / "games" / "g002-uniform-stage-s2" / "attempt-001"
        self.assertFalse((adir / B.MARKER).exists())
        self.assertEqual(json.loads((adir / B.NOTE).read_text(encoding="utf-8"))["status"], "interrupted")
        ends = [e for e in self.ledger() if e["event"] == "session_end"]
        self.assertEqual(ends[-1]["status"], "interrupted")
        return a

    def test_keyboard_interrupt(self):
        self.check_interrupt(KeyboardInterrupt())

    def test_system_exit(self):
        self.check_interrupt(SystemExit(3))

    def test_memory_error_is_not_a_game_result(self):
        a = self.check_interrupt(MemoryError())
        a.script = {}
        r = self.run_(a)  # 再開すると、未完了の局を別の attempt で最初から
        self.assertEqual(r.status, "completed")
        self.assertEqual(a.calls.count("g002-uniform-stage-s2"), 2)

    def test_adapter_error_stops_batch(self):
        a = FakeAdapter(script={"g001-uniform-stage-s1": RuntimeError("bug")})
        self.plan(a, seeds=(1, 2))
        r = self.run_(a)
        self.assertEqual(r.status, "stopped_error")
        self.assertEqual(a.calls, ["g001-uniform-stage-s1"])
        note = json.loads((self.bdir() / "games" / "g001-uniform-stage-s1" / "attempt-001" / B.NOTE).read_text(encoding="utf-8"))
        self.assertEqual(note["status"], "error")


class LockTest(Base):
    def test_second_launch_is_refused_while_running(self):
        a = FakeAdapter()
        self.plan(a, seeds=(1, 2))
        seen = []

        def nested(gid):
            if not seen:
                with self.assertRaises(B.LockHeld):
                    B.run_batch(self.tmp, "b", adapter=FakeAdapter(), memory=no_memory)
                with self.assertRaises(B.LockHeld):
                    B.aggregate(self.tmp, "b", adapter=FakeAdapter())
                seen.append(gid)

        a.during_play = nested
        self.assertEqual(self.run_(a).status, "completed")
        self.assertEqual(seen, ["g001-uniform-stage-s1"])

    def test_stale_lock_is_not_removed_automatically(self):
        a = FakeAdapter()
        self.plan(a, seeds=(1,))
        (self.bdir() / B.LOCK).write_text(json.dumps({"session": "old", "pid": 1}), encoding="utf-8")
        with self.assertRaises(B.LockHeld):
            self.run_(a)
        self.assertTrue((self.bdir() / B.LOCK).exists())
        self.assertEqual(a.calls, [])
        with self.assertRaises(B.BatchRefused):
            B.unlock(self.tmp, "b", "wrong")
        self.assertTrue((self.bdir() / B.LOCK).exists())
        B.unlock(self.tmp, "b", "old")
        self.assertFalse((self.bdir() / B.LOCK).exists())
        self.assertEqual(self.ledger()[-1]["event"], "lock_removed")
        self.assertEqual(self.run_(a).status, "completed")


class LimitTest(Base):
    def test_time_budget_is_cumulative_across_resumes(self):
        clock = Clock()
        a = FakeAdapter(clock=clock, step=100.0)
        self.plan(a, seeds=(1, 2, 3, 4), budget_seconds=250.0, game_reserve_seconds=100.0)
        r1 = self.run_(a, clock=clock)
        self.assertEqual(r1.status, "stopped_budget_time")
        self.assertEqual(len(a.calls), 2)
        r2 = self.run_(a, clock=clock)  # 再開しても上限を戻さない
        self.assertEqual((r2.status, r2.ran), ("stopped_budget_time", []))
        self.assertEqual(len(a.calls), 2)

    def test_unended_session_is_charged_a_reserve(self):
        events = [{"event": "session_start", "session": "s1", "elapsed": 0.0}, {"event": "attempt_start", "session": "s1", "elapsed": 10.0},
                  {"event": "session_start", "session": "s2", "elapsed": 0.0}, {"event": "session_end", "session": "s2", "elapsed": 30.0}]
        acc = B.accounted_seconds(events, 150.0)
        self.assertEqual(acc["seconds"], 190.0)
        self.assertEqual(acc["estimated_sessions"], ["s1"])

    def test_broken_last_ledger_line_is_ignored_and_counted(self):
        a = FakeAdapter()
        self.plan(a, seeds=(1,))
        with (self.bdir() / B.LEDGER).open("a", encoding="utf-8") as f:
            f.write('{"event": "session_start", "sess')
        self.run_(a)
        events, broken = B.Ledger(self.bdir() / B.LEDGER).read()
        self.assertEqual(broken, 1)
        self.assertEqual(events[0]["event"], "session_start")
        self.assertEqual(events[0]["ledger_broken_lines"], 1)

    def test_evidence_limits_between_games_and_at_write(self):
        a = FakeAdapter(size=5_000)
        self.plan(a, seeds=(1, 2), evidence_max_bytes=12_000, evidence_reserve_bytes=5_000)
        self.assertLess(B.tree_bytes(self.bdir()), 6_000)
        r = self.run_(a)
        self.assertEqual(r.status, "stopped_budget_evidence")
        self.assertEqual(len(a.calls), 1)
        big = FakeAdapter(size=50_000)
        self.plan(big, seeds=(1,), batch="c", evidence_max_bytes=40_000, evidence_reserve_bytes=1_000)
        r = self.run_(big, batch="c")
        self.assertEqual(r.status, "stopped_evidence_limit")
        adir = self.bdir("c") / "games" / "g001-uniform-stage-s1" / "attempt-001"
        self.assertFalse((adir / "big.bin").exists())
        self.assertFalse((adir / B.MARKER).exists())

    def test_attempts_per_game_are_bounded(self):
        a = FakeAdapter(script={"g001-uniform-stage-s1": RuntimeError("bug")})
        self.plan(a, seeds=(1,), max_attempts_per_game=2)
        self.assertEqual(self.run_(a).status, "stopped_error")
        self.assertEqual(self.run_(a).status, "stopped_error")
        self.assertEqual(self.run_(a).status, "stopped_attempts_exhausted")
        self.assertEqual(len(a.calls), 2)


class PolicyTest(Base):
    def test_suspect_stops_and_needs_acknowledgement(self):
        a = FakeAdapter(script={"g001-uniform-stage-s1": summary(submits={"expected": 2, "suspect": 1})})
        self.plan(a, seeds=(1, 2))
        r = self.run_(a)
        self.assertEqual(r.status, "stopped_policy")
        self.assertEqual(r.stop["reasons"], ["suspect:1"])
        self.assertTrue((self.bdir() / "games" / "g001-uniform-stage-s1" / "attempt-001" / B.MARKER).exists())  # 証跡は確定して残す
        with self.assertRaises(B.BatchRefused):
            self.run_(a)
        self.assertEqual(len(a.calls), 1)
        r = self.run_(a, acknowledge=["g001-uniform-stage-s1"])
        self.assertEqual(r.status, "completed")
        self.assertEqual(a.calls, ["g001-uniform-stage-s1", "g002-uniform-stage-s2"])

    def test_undetermined_continues_and_is_counted(self):
        a = FakeAdapter(script={"g001-uniform-stage-s1": summary(termination="halted_known", term_verdict="undetermined", undetermined=[EVIDENCE_MISSING])})
        self.plan(a, seeds=(1, 2))
        r = self.run_(a)
        self.assertEqual(r.status, "completed")
        self.assertEqual(r.ran[0]["note"], ["undetermined:evidence_missing_stop:1"])
        agg = json.loads((self.bdir() / "aggregate.json").read_text(encoding="utf-8"))
        self.assertEqual(agg["judge"]["termination"], {"expected": 1, "undetermined": 1})

    def test_stop_reasons(self):
        policy = B._policy_dict(B.StopPolicy())
        self.assertEqual(B.stop_reasons(summary(), policy), ([], []))
        for kw, expect in ((dict(termination="exception", term_verdict="suspect"), ["termination:exception", "suspect:1"]),
                           (dict(termination="state_integrity", term_verdict="suspect"), ["termination:state_integrity", "suspect:1"]),
                           (dict(anomalies=["update_numbers"]), ["anomalies:update_numbers"]),
                           (dict(replay_ok=False), ["verification:replay=mismatch/expected=succeeded,correspondence=0"]),
                           (dict(termination="something_new"), ["unknown_termination:something_new"])):
            self.assertEqual(B.stop_reasons(summary(**kw), policy)[0], expect, kw)
        for term in ("game_over", "halted_known", "input_unavailable", "no_progress", "limit_turns", "limit_time"):
            self.assertEqual(B.stop_reasons(summary(termination=term), policy)[0], [], term)


class AggregateAndMemoryTest(Base):
    def test_aggregate_only_rerun_does_not_replay_games(self):
        a = FakeAdapter()
        self.plan(a, seeds=(1, 2), modes=("uniform-stage", "rules-v2"))
        self.run_(a)
        first = json.loads((self.bdir() / "aggregate.json").read_text(encoding="utf-8"))
        (self.bdir() / "aggregate.json").unlink()
        B.aggregate(self.tmp, "b", adapter=a)
        again = json.loads((self.bdir() / "aggregate.json").read_text(encoding="utf-8"))
        self.assertEqual(len(a.calls), 4)
        self.assertEqual({k: again[k] for k in ("games", "terminations", "judge", "by", "funnel")}, {k: first[k] for k in ("games", "terminations", "judge", "by", "funnel")})
        self.assertEqual(again["by"]["mode"]["rules-v2"]["games"], 2)
        public = json.loads((self.tmp / "public" / "runs" / "b" / "summary.json").read_text(encoding="utf-8"))
        self.assertNotIn("rows", public)  # 公開の集計に局ごとの行（seed を含む game_id）を入れない
        self.assertNotIn("-s1", json.dumps(public, ensure_ascii=False))
        self.assertNotIn("-s2", json.dumps(public, ensure_ascii=False))

    def test_game_results_are_not_retained(self):
        a = FakeAdapter(size=200_000)
        self.plan(a, seeds=(1, 2, 3))
        report = self.run_(a)
        gc.collect()
        self.assertEqual(len(a.refs), 3)
        self.assertTrue(all(r() is None for r in a.refs))
        self.assertLess(len(json.dumps([vars(report)], default=str)), 5_000)  # 戻り値は小さな要約だけ

    def test_process_memory_is_measured_or_marked(self):
        m = B.process_memory()
        self.assertIn(m["status"], ("measured", "not_measured"))


class EngineAdapterTest(unittest.TestCase):
    """本物の部品。計画の設定（規約集合の ID@版 を明示・既定を展開）の経路で、既存の方策の行動の指紋が変わらない。"""

    def test_planned_config_keeps_action_fingerprints(self):
        from tools.verification_ai import records as R

        from tests.test_verification_ai_v2_repeat import ACTION_GOLDEN

        from tools.verification_ai.runner import run_game

        a = B.EngineAdapter("test")
        for name, mode, seed in (("uniform-stage-s12", "uniform-stage", 12), ("rules-v1-s13", "rules-v1", 13)):
            with self.subTest(name):
                entry = a.entry(game_id=name, mode=mode, seed=seed, deck0="hitmonchan-dewgong", deck1="venusaur-parasect", conventions=None, group="g",
                                game_limits={"operations": 80, "seconds": 60})
                self.assertEqual(entry["config"]["conventions"], "CS-KYUURA-CURRENT@1")
                self.assertEqual(a.check_entry(entry), [])
                result = run_game(a.config_of(entry))
                digest = R.sequence_digest(R.action_sequence(result["trace"]), R.ACTION_FORMAT)
                self.assertEqual((digest["length"], digest["sha256"]), ACTION_GOLDEN[name])
                judged = B.judge_trace(result)
                self.assertEqual(sum(judged["counts"].values()), sum(1 for e in result["trace"] if e.get("type") == "attempt" and e.get("submit")))

    def test_mixed_entry_records_policy_settings(self):
        a = B.EngineAdapter("test")
        entry = a.entry(game_id="m", mode="mixed", seed=1001, deck0="hitmonchan-dewgong", deck1="venusaur-parasect", conventions=None, group="g")
        p0 = entry["policies"]["0"]
        self.assertEqual((p0["name"], p0["epsilon"], p0["rules_version"], p0["threshold"], p0["demote_after"]), ("mixed", 0.25, 2, 2, 2))
        self.assertEqual(entry["policies"]["host"]["name"], "uniform")
        self.assertEqual(entry["config"]["limits"]["seconds"], 120.0)  # 単局の上限は runner.Limits の既定（V0〜V3 と同じ）

    def test_runner_does_not_turn_memory_error_into_a_result(self):
        from tools.verification_ai.runner import Config, Runner

        def boom(actor, endpoint):
            raise MemoryError()

        with self.assertRaises(MemoryError):
            Runner(Config(game_seed=1), wrap_endpoint=boom).run()

    def test_real_batch_of_one_small_game(self):
        tmp = Path(tempfile.mkdtemp(prefix="vai-batch-real-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        a = B.EngineAdapter("test")
        B.make_plan(tmp, "r", engine_commit="test", tool_commit="test", seeds=[12], modes=["uniform-stage"], deck0="hitmonchan-dewgong",
                    deck1="venusaur-parasect", adapter=a, game_limits={"operations": 40, "seconds": 60})
        report = B.run_batch(tmp, "r", adapter=a)
        self.assertEqual(report.status, "completed")
        self.assertEqual(report.ran[0]["termination"], "limit_operations")
        adir = B.batch_dir(tmp, "r") / "games" / "g001-uniform-stage-s12" / "attempt-001"
        marker = json.loads((adir / B.MARKER).read_text(encoding="utf-8"))
        self.assertTrue(marker["summary"]["replay_run"]["matches_expectation"])
        self.assertEqual(marker["summary"]["correspondence_problems"], 0)
        self.assertEqual(B.run_batch(tmp, "r", adapter=a).ran, [])


if __name__ == "__main__":
    unittest.main()
