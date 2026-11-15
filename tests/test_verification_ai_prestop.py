"""範囲の外の未裁定の候補の inputs の検証者用の記録（tools/verification_ai/prestop.py・runner._prestop_fetch・batch の接続。docs/prestop-record-design.md）。

- 単体（人工の応答。PrestopRecorder だけ）: 対象・重複・段なし・上限（256 回・16 KiB・1 MiB の境界と、マルチバイト・改行の実バイト数）・失敗・照合式・計画の設定
- 本物の runner（既存の固定の短い局。uniform-stage・seed 12・80 操作）: 有効と無効で行動・選択・乱数・状態が同じ、記録用の要求が取っ手・更新・状態・_purge に触れない
- 本物のバッチ（同じ局）: 保存・必須ファイル・ハッシュ・COMPLETE・停止・承認・再開・集計・公開の出力
人工の応答・短い局は、新しいバッチの実績に数えない。
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from kyuura_engine import legal_actions as L
from kyuura_engine.replay_record import checks
from tools.verification_ai import batch as B
from tools.verification_ai import prestop as P
from tools.verification_ai import records as R
from tools.verification_ai.runner import Runner

T = P.TARGET_REASON


def cand(cid, kind="play_trainer", stages=True, **extra):
    return {"id": cid, "kind": kind, "processability": "unresolved_ruling", "reasons": ["stops_before_acceptance"], "input_disclosure": "confirmed",
            "input_stages": [{"stage": 1, "input": "choose_option"}] if stages else [], "guarantees": {"acceptance": "保証しない"}, **extra}


def fetch_of(cands_list, reasons=None):
    return {"game": "g", "revision": "r", "candidates": cands_list}, (reasons if reasons is not None else {c["id"]: T for c in cands_list})


def ok_answer(options=None, pad=""):
    options = options if options is not None else [{"id": "o1", "card": 7, "card_id": "X-001", "eligible": False, "processability": "unresolved_ruling",
                                                    "reasons": ["stops_before_acceptance"], "extra": "写さない"}]
    return {"contract": "kyuura-client-api", "format": 1, "type": "inputs", "ok": True, "refetch_required": False,
            "response": {"candidate": "c1", "kind": "play_trainer", "stages": [{"stage": 1, "input": "choose_option", "role": "trainer" + pad, "meaning": "card",
                                                                                "count": {"min": 1, "max": 1}, "options": options, "order": "not_applicable"}]}}


class Calls:
    def __init__(self, answer=None, error=None):
        self.n, self.answer, self.error = [], answer, error

    def __call__(self, cid):
        self.n.append(cid)
        if self.error is not None:
            raise self.error
        return self.answer(cid) if callable(self.answer) else (self.answer if self.answer is not None else ok_answer())


def handles_masked(value):
    """取っ手（エンジンが実行ごとに乱数で発行する game・revision の値）だけを置き換えた写し。ほかの値は変えない。"""
    if isinstance(value, dict):
        return {k: ("<handle>" if k in ("game", "revision") and isinstance(v, str) else handles_masked(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [handles_masked(v) for v in value]
    return value


def rows(rec):
    return [json.loads(x) for x in rec.rows_bytes().decode("utf-8").splitlines()]


class TargetAndDedupTest(unittest.TestCase):
    def test_only_candidate_level_unresolved_with_stages_is_requested(self):
        rec, calls = P.PrestopRecorder(), Calls()
        partial = dict(cand("c3"), processability="may_stop_later")  # 選択肢の一部だけが未裁定の候補（範囲の中。既存の actors の inputs の記録を使う）
        cands, _ = fetch_of([cand("c1"), cand("c2", stages=False), partial, cand("c4", kind="use_stadium")])
        reasons = {"c1": T, "c2": T, "c4": T, "c5": "processability:not_implemented"}  # c3 は範囲の中（理由なし）
        rec.on_fetch(0, 5, 1, cands, reasons, calls)
        s = rec.summary()
        self.assertEqual(calls.n, ["c1", "c4"])
        self.assertEqual((s["offered"], s["keys"], s["no_stages"], s["attempted"], s["ok"]), (3, 3, 1, 2, 2))
        self.assertEqual(s["offered_by_kind"], {"play_trainer": 2, "use_stadium": 1})
        self.assertEqual(P.reconcile(s, rows=rec.rows_bytes()), [])

    def test_same_key_with_new_handle_is_not_requested_again(self):
        rec, calls = P.PrestopRecorder(), Calls()
        for rev, cid in (("r1", "c1"), ("r2", "c9"), ("r3", "c4")):  # 取り直しで取っ手・番号だけが違う
            rec.on_fetch(0, 5, 1, {"game": "g", "revision": rev, "candidates": [cand(cid)]}, {cid: T}, calls)
        changed = dict(cand("c1"), reasons=["stops_before_acceptance", "x"])  # 同じ位置でも中身が違えば別の鍵
        rec.on_fetch(0, 5, 1, {"game": "g", "revision": "r4", "candidates": [changed]}, {"c1": T}, calls)
        rec.on_fetch(1, 5, 1, {"game": "g", "revision": "r5", "candidates": [cand("c1")]}, {"c1": T}, calls)  # 主体が違えば別
        s = rec.summary()
        self.assertEqual((len(calls.n), s["offered"], s["keys"], s["repeats"], s["fetches"]), (3, 5, 3, 2, 5))
        self.assertEqual(P.reconcile(s, rows=rec.rows_bytes()), [])

    def test_row_keeps_returned_values_only_and_hashes_guarantees(self):
        rec = P.PrestopRecorder()
        face_down = {"id": "o2", "pokemon": 3, "card": 11, "zone": "bench", "face_down": True, "eligible": False, "processability": "unresolved_ruling"}
        rec.on_fetch(0, 2, 4, *fetch_of([cand("c1", stadium={"card": 9, "card_id": "S-1", "owner": 0})]), Calls(ok_answer(options=[face_down])))
        row = rows(rec)[0]
        self.assertEqual((row["actor"], row["position"], row["episode"], row["fetch"], row["source"], row["status"]), (0, 2, 4, 1, "record_fetch", "ok"))
        self.assertEqual(row["stages"][0]["options"], [face_down])  # face_down のまま。card_id・real を足さない
        self.assertNotIn("guarantees", row["candidate"])
        self.assertEqual(row["candidate"]["guarantees_sha256"], P._sha({"acceptance": "保証しない"}))
        self.assertEqual(row["candidate"]["stadium"]["card_id"], "S-1")
        self.assertNotIn("extra", json.dumps(rows(rec)))
        self.assertNotIn("code", json.dumps(row["stages"]))  # 停止コードは書かない（応答にない）


class LimitTest(unittest.TestCase):
    def test_fetch_cap_256_then_counted_not_requested(self):
        rec, calls = P.PrestopRecorder(), Calls()
        rec.on_fetch(0, 0, 1, *fetch_of([cand(f"c{i}", reasons=[str(i)]) for i in range(258)]), calls)
        s = rec.summary()
        self.assertEqual((len(calls.n), s["attempted"], s["skipped_fetch_cap"], s["status"], s["capped"]), (256, 256, 2, "capped", [P.CAP_FETCHES]))
        self.assertEqual(P.reconcile(s, rows=rec.rows_bytes()), [])

    def test_response_16kib_boundary_with_multibyte_text(self):
        def answer_of_size(n):
            base = ok_answer(pad="")
            size = len(P.canonical(base).encode("utf-8"))
            fill = n - size
            pad = "あ" * (fill // 3) + "a" * (fill % 3)  # 3 バイトの文字と 1 バイトの文字で、ちょうど n バイト
            got = ok_answer(pad=pad)
            self.assertEqual(len(P.canonical(got).encode("utf-8")), n)
            return got

        for n, status in ((16384, "ok"), (16385, "oversize")):
            with self.subTest(n):
                rec = P.PrestopRecorder()
                rec.on_fetch(0, 0, 1, *fetch_of([cand("c1")]), Calls(answer_of_size(n)))
                row = rows(rec)[0]
                self.assertEqual((row["status"], row["response_bytes"]), (status, n))
                if status == "oversize":
                    self.assertNotIn("stages", row)  # 本文を保存しない（量と理由だけ）
                    self.assertEqual(row["detail"]["reason"], "response_too_large")
                self.assertEqual(P.reconcile(rec.summary(), rows=rec.rows_bytes()), [])

    def test_rows_1mib_counts_utf8_bytes_and_newlines_before_writing(self):
        probe = P.PrestopRecorder()
        probe.on_fetch(0, 0, 1, *fetch_of([cand("c0", reasons=["理由0"])]), Calls(ok_answer(pad="日本語")))
        one = len(probe.rows_bytes())  # 1 行の実際の UTF-8 のバイト数（改行をふくむ）
        self.assertEqual(probe.rows_bytes().count(b"\n"), 1)
        limits = dict(P.DEFAULT_LIMITS, max_rows_bytes=one)
        rec, calls = P.PrestopRecorder(limits), Calls(ok_answer(pad="日本語"))
        rec.on_fetch(0, 0, 1, *fetch_of([cand("c0", reasons=["理由0"]), cand("c1", reasons=["理由1"])]), calls)
        s = rec.summary()
        self.assertEqual((s["rows"], s["rows_bytes"], len(calls.n), s["skipped_bytes_cap"], s["capped"]), (1, one, 1, 1, [P.CAP_ROWS_BYTES]))
        self.assertEqual(P.reconcile(s, rows=rec.rows_bytes()), [])

    def test_row_too_big_after_request_is_not_written_and_stops_requests(self):
        probe = P.PrestopRecorder()
        probe.on_fetch(0, 0, 1, *fetch_of([cand("c0")]), Calls(ok_answer(pad="x" * 500)))
        limit = len(probe.rows_bytes()) - 1  # 本文のない行は入るが、本文つきの行は 1 バイト入らない
        rec, calls = P.PrestopRecorder(dict(P.DEFAULT_LIMITS, max_rows_bytes=limit)), Calls(ok_answer(pad="x" * 500))
        rec.on_fetch(0, 0, 1, *fetch_of([cand("c0"), cand("c1", reasons=["y"])]), calls)
        s = rec.summary()
        self.assertEqual((len(calls.n), s["attempted"], s["unsaved_bytes_cap"], s["rows"], s["rows_bytes"], s["skipped_bytes_cap"]), (1, 1, 1, 0, 0, 1))
        self.assertEqual(rec.rows_bytes(), b"")  # 上限を超える行を書かない・別のファイルへ逃がさない
        self.assertEqual(P.reconcile(s, rows=rec.rows_bytes()), [])


class FailureTest(unittest.TestCase):
    def run_one(self, answer=None, error=None):
        rec, calls = P.PrestopRecorder(), Calls(answer, error)
        rec.on_fetch(0, 0, 1, *fetch_of([cand("c1"), cand("c2", reasons=["z"])]), calls)
        return rec, calls

    def test_withheld_refused_stale_and_contract_unknown_are_recorded_and_continue(self):
        stale = {"ok": False, "refetch_required": True, "response": {"refusal": {"code": L.CANDIDATES_STALE, "message": "..."}}}
        unavailable = {"ok": False, "error": {"code": "CLIENT_GAME_UNAVAILABLE", "message": "..."}}
        withheld = {"ok": True, "response": {"candidate": "c1", "withheld": {"code": L.INPUT_BOUNDARY_UNCONFIRMED}, "stages": []}}
        broken = {"ok": True, "response": {"stages": "x"}}
        for answer, status in ((stale, "refused"), (unavailable, "refused"), (withheld, "withheld"), (broken, "contract_unknown"), ([1], "contract_unknown")):
            with self.subTest(status):
                rec, calls = self.run_one(answer)
                s = rec.summary()
                self.assertEqual((len(calls.n), s[status], s["status"]), (2, 2, "complete"))  # stale でも candidates を取り直さず、次の鍵も要求する
                self.assertEqual(P.reconcile(s, rows=rec.rows_bytes()), [])
        self.assertEqual(rows(self.run_one(stale)[0])[0]["refusal"], {"code": L.CANDIDATES_STALE, "from": "refusal"})

    def test_ordinary_exception_stops_recording_for_the_game(self):
        rec, calls = self.run_one(error=RuntimeError("入口の不具合"))
        rec.on_fetch(0, 1, 1, *fetch_of([cand("c3")]), calls)
        s = rec.summary()
        self.assertEqual((len(calls.n), s["error"], s["skipped_after_failure"], s["status"], s["failure"]["where"]), (1, 1, 2, "failed", "inputs_request"))
        self.assertEqual(rows(rec)[0]["status"], "error")
        self.assertEqual(P.reconcile(s, rows=rec.rows_bytes()), [])

    def test_memory_error_keyboard_interrupt_and_system_exit_are_not_absorbed(self):
        for error in (MemoryError(), KeyboardInterrupt(), SystemExit(3)):
            with self.subTest(type(error).__name__), self.assertRaises(type(error)):
                self.run_one(error=error)

    def test_reconcile_detects_broken_counts_rows_and_result_mismatch(self):
        rec, _ = self.run_one()
        s, data = rec.summary(), rec.rows_bytes()
        self.assertEqual(P.reconcile(s, rows=data, excluded_by_kind={"play_trainer": 2}), [])
        self.assertTrue(P.reconcile(dict(s, offered=3), rows=data))
        self.assertTrue(P.reconcile(dict(s, ok=1), rows=data))
        self.assertTrue(P.reconcile(s, rows=data[:-1]))
        self.assertTrue(P.reconcile(s, rows=data, excluded_by_kind={"play_trainer": 4}))  # 前回の 2 倍の誤りのような不一致を通さない
        self.assertTrue(P.reconcile(dict(s, status="complete", failure={"where": "x"}), rows=data))
        self.assertEqual(P.reconcile(None), ["prestop の要約がない・形式が違う"])


class SettingTest(unittest.TestCase):
    def test_plan_setting_and_problems(self):
        self.assertEqual(P.setting_problems(P.plan_setting(False)), [])
        self.assertEqual(P.setting_problems(P.plan_setting(True)), [])
        self.assertEqual(P.plan_setting(True)["limits"], {"max_fetches_per_game": 256, "max_response_bytes": 16384, "max_rows_bytes": 1048576})
        good = P.plan_setting(True)
        for bad in (None, dict(good, extra=1), dict(good, enabled="yes"), dict(P.plan_setting(False), limits=good["limits"]),
                    dict(good, version=2), dict(good, limits=dict(good["limits"], max_fetches_per_game=257)),
                    dict(good, limits=dict(good["limits"], max_rows_bytes=True)), dict(good, limits={"max_fetches_per_game": 1})):
            with self.subTest(bad):
                self.assertTrue(P.setting_problems(bad))
        with self.assertRaises(ValueError):
            P.plan_setting(False, {"max_fetches_per_game": 1})
        with self.assertRaises(ValueError):
            P.PrestopRecorder(dict(P.DEFAULT_LIMITS, max_response_bytes=0))

    def test_negative_and_prestop_are_not_combined(self):
        with self.assertRaises(ValueError):
            Runner(B.EngineAdapter("test").config_of(_entry()), negative=object(), prestop=P.PrestopRecorder())


_PLAN_CACHE: dict = {}


def _entry():
    if "entry" not in _PLAN_CACHE:
        tmp = Path(tempfile.mkdtemp(prefix="vai-prestop-entry-"))
        try:
            plan = B.make_plan(tmp, "e", engine_commit="test", tool_commit="test", seeds=[12], modes=["uniform-stage"], deck0="hitmonchan-dewgong",
                               deck1="venusaur-parasect", adapter=B.EngineAdapter("test"), game_limits={"operations": 80, "seconds": 60})
            _PLAN_CACHE["entry"] = plan["games"][0]
        finally:
            shutil.rmtree(tmp, True)
    return _PLAN_CACHE["entry"]


class Spy:
    """記録用の要求（直前の候補の応答で未裁定の候補への inputs）の前後で、hub の取っ手・更新・状態・_purge を見る。ほかの要求は数えるだけ。"""

    log: list = []

    def __init__(self, actor, inner, box):
        self.actor, self.inner, self.box = actor, inner, box
        self.unresolved: set[str] = set()

    def handle(self, req):
        hub = self.box["runner"].hub
        host = hub._host
        record = req.get("type") == "inputs" and req.get("candidate") in self.unresolved
        if record:
            before = (len(host._issued), {a: len(v) for a, v in hub._outbox.items()}, id(hub._state()), len(hub._state().log), self.box["purge"])
        got = self.inner.handle(req)
        if record:
            after = (len(host._issued), {a: len(v) for a, v in hub._outbox.items()}, id(hub._state()), len(hub._state().log), self.box["purge"])
            self.box["record"].append((before == after, got.get("ok"), got.get("refetch_required")))
        else:
            self.box["normal"].append((self.actor, req.get("type"), req.get("candidate")))
        if req.get("type") == "candidates" and got.get("ok"):
            self.unresolved = {c["id"] for c in got["response"]["candidates"] if c.get("processability") == "unresolved_ruling"}
        return got


def run_real(prestop):
    from kyuura_engine.legal_actions import ActionHost

    box = {"record": [], "normal": [], "purge": 0}
    original = ActionHost._purge

    def counting(self):
        box["purge"] += 1
        return original(self)

    ActionHost._purge = counting
    try:
        runner = Runner(B.EngineAdapter("test").config_of(_entry()), prestop=prestop, wrap_endpoint=lambda actor, ep: Spy(actor, ep, box))
        box["runner"] = runner
        result = runner.run()
    finally:
        ActionHost._purge = original
    return runner, result, box


class RealRunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rec = P.PrestopRecorder()
        cls.on = run_real(cls.rec)
        cls.off = run_real(None)

    def test_actions_choices_rng_state_and_outcome_are_the_same(self):
        (r_on, on, b_on), (r_off, off, b_off) = self.on, self.off
        self.assertEqual(R.action_sequence(on["trace"]), R.action_sequence(off["trace"]))
        self.assertEqual(R.contract_sequence(on["trace"]), R.contract_sequence(off["trace"]))
        self.assertEqual([(e.get("choices"), e.get("candidate_reason")) for e in on["trace"] if e.get("type") == "attempt"],
                         [(e.get("choices"), e.get("candidate_reason")) for e in off["trace"] if e.get("type") == "attempt"])
        self.assertEqual({k: p["draws"] for k, p in on["policies"].items()}, {k: p["draws"] for k, p in off["policies"].items()})
        self.assertEqual(checks(r_on.game.state), checks(r_off.game.state))  # 状態と乱数の確認値
        self.assertEqual((on["termination"]["class"], on["counters"], on["anomalies"], on["metrics"], on["coverage"]),
                         (off["termination"]["class"], off["counters"], off["anomalies"], off["metrics"], off["coverage"]))
        # 本人の記録に記録用の応答を入れない。取っ手（game・revision）は実行ごとに乱数で発行される値なので、その 2 つの値だけを置き換えて比べる（attempt 2 で直した）
        self.assertEqual(handles_masked(on["actor_logs"]), handles_masked(off["actor_logs"]))
        self.assertEqual(b_on["normal"], b_off["normal"])  # 通常の要求の種類・順・候補が同じ
        self.assertLess(on["elapsed_seconds"], 60 / 2)  # 時間の上限に余裕のある比較（上限の近くでは終わり方が変わりうる。設計 3 章）

    def test_record_requests_touch_no_handles_updates_state_or_purge(self):
        _r, on, box = self.on
        s = self.rec.summary()
        self.assertGreater(s["attempted"], 0)  # この局で記録用の要求が実際に起きた
        self.assertEqual(len(box["record"]), s["attempted"])
        self.assertTrue(all(same and ok is True and refetch is False for same, ok, refetch in box["record"]))
        self.assertEqual((s["status"], s["refused"], s["error"], s["contract_unknown"]), ("complete", 0, 0, 0))
        self.assertEqual(P.reconcile(s, rows=self.rec.rows_bytes(), excluded_by_kind=P.excluded_by_kind(on["metrics"])), [])
        for row in rows(self.rec):  # 本人の入口が返した値だけ（本人のうらは face_down だけ）
            for stage in row["stages"]:
                for o in stage["options"] or []:
                    self.assertFalse(o.get("face_down") and "card_id" in o)
        self.assertGreater(s["seconds"], 0)


class BatchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vai-prestop-batch-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.a = B.EngineAdapter("test")

    def plan(self, name, seeds=(12,), **kw):
        return B.make_plan(self.tmp, name, engine_commit="test", tool_commit="test", seeds=list(seeds), modes=["uniform-stage"], deck0="hitmonchan-dewgong",
                           deck1="venusaur-parasect", adapter=self.a, game_limits={"operations": 80, "seconds": 60}, **kw)

    def test_real_batch_saves_verifies_and_aggregates_prestop(self):
        from tests.test_verification_ai_v2_repeat import ACTION_GOLDEN

        plan = self.plan("p", prestop_inputs=True)
        self.assertEqual((plan["format"], plan["prestop_inputs"]["enabled"], plan["prestop_inputs"]["limits"]["max_rows_bytes"]), (B.PLAN_FORMAT, True, 1 << 20))
        self.assertEqual(B.run_batch(self.tmp, "p", adapter=self.a).status, "completed")
        bdir = B.batch_dir(self.tmp, "p")
        adir = bdir / "games" / "g001-uniform-stage-s12" / "attempt-001"
        marker = json.loads((adir / B.MARKER).read_text(encoding="utf-8"))
        s = marker["summary"]
        self.assertEqual((s["sequences"]["action"]["length"], s["sequences"]["action"]["sha256"]), ACTION_GOLDEN["uniform-stage-s12"])  # 有効でも行動が同じ
        self.assertEqual((s["prestop"]["status"], s["prestop_problems"], marker["stop"]), ("complete", [], []))
        self.assertTrue(set(P.FILES) <= set(marker["required"]))
        self.assertEqual(json.loads((adir / P.SUMMARY).read_text(encoding="utf-8")), s["prestop"])
        self.assertEqual(len((adir / P.ROWS).read_bytes()), s["prestop"]["rows_bytes"])
        plan_, sha = B.load_plan(bdir, self.a)
        entry = plan_["games"][0]
        self.assertEqual(B.verify_complete(adir, plan=plan_, plan_sha=sha, entry=entry)[1], [])
        agg = B.aggregate(self.tmp, "p", adapter=self.a)
        pv = agg["verifier"]["prestop"]
        self.assertEqual((pv["games"], pv["counts"]["offered"], pv["counts"]["attempted"]), (1, s["prestop"]["offered"], s["prestop"]["attempted"]))
        self.assertEqual(agg["verifier"]["evidence"]["game_complete_prestop"]["files"], 2)
        public = json.dumps(agg["public"], ensure_ascii=False)
        self.assertNotIn("card_id", public)
        for row in (adir / P.ROWS).read_text(encoding="utf-8").splitlines():  # 検証者用の記録のカード ID は公開の集計に出ない
            for stage in json.loads(row).get("stages") or []:
                for o in stage.get("options") or []:
                    if o.get("card_id"):
                        self.assertNotIn(o["card_id"], public)
        # 破損・欠け・不整合を黙って受け入れない
        rows_path, summary_path = adir / P.ROWS, adir / P.SUMMARY
        original = rows_path.read_bytes()
        rows_path.write_bytes(original + b"\n")
        problems = B.verify_complete(adir, plan=plan_, plan_sha=sha, entry=entry)[1]
        self.assertTrue(any("prestop/inputs.jsonl の sha256" in p for p in problems) and any("照合式" in p for p in problems))
        rows_path.write_bytes(original)
        saved = summary_path.read_bytes()
        summary_path.unlink()
        self.assertTrue(B.verify_complete(adir, plan=plan_, plan_sha=sha, entry=entry)[1])
        summary_path.write_bytes(saved)
        self.assertEqual(B.verify_complete(adir, plan=plan_, plan_sha=sha, entry=entry)[1], [])

    def test_disabled_plan_is_explicit_and_unchanged(self):
        plan = self.plan("n")
        self.assertEqual(plan["prestop_inputs"], P.plan_setting(False))
        self.assertEqual(B.run_batch(self.tmp, "n", adapter=self.a).status, "completed")
        adir = B.batch_dir(self.tmp, "n") / "games" / "g001-uniform-stage-s12" / "attempt-001"
        marker = json.loads((adir / B.MARKER).read_text(encoding="utf-8"))
        self.assertNotIn("prestop", marker["summary"])
        self.assertFalse((adir / "prestop").exists())
        self.assertEqual(list(marker["required"]), list(B.REQUIRED_FILES))

    def test_recorder_failure_stops_the_batch_after_saving_and_needs_acknowledgement(self):
        original = P.PrestopRecorder.on_fetch

        def broken(self, *args, **kw):
            raise RuntimeError("記録の誤り")

        self.plan("f", seeds=(12, 13), prestop_inputs=True)
        P.PrestopRecorder.on_fetch = broken
        try:
            report = B.run_batch(self.tmp, "f", adapter=self.a)
        finally:
            P.PrestopRecorder.on_fetch = original
        self.assertEqual(report.status, "stopped_policy")
        self.assertTrue(any(r.startswith("prestop:failed:on_fetch") for r in report.stop["reasons"]))
        adir = B.batch_dir(self.tmp, "f") / "games" / "g001-uniform-stage-s12" / "attempt-001"
        marker = json.loads((adir / B.MARKER).read_text(encoding="utf-8"))
        self.assertEqual((marker["evidence"], marker["summary"]["prestop"]["status"], marker["summary"]["prestop"]["counts_complete"]),
                         ("complete_with_stop", "failed", False))
        self.assertEqual(marker["summary"]["termination"], json.loads((adir / "result.json").read_text(encoding="utf-8"))["termination"]["class"])
        self.assertFalse((B.batch_dir(self.tmp, "f") / "games" / "g002-uniform-stage-s13").exists())  # 保存したあとで止める（次の局を始めない）
        with self.assertRaises(B.BatchRefused):  # 停止の承認を自動で解除しない
            B.run_batch(self.tmp, "f", adapter=self.a)

    def test_resume_keeps_completed_games_and_plan_settings(self):
        self.plan("r", seeds=(12, 13), prestop_inputs=True)
        self.assertEqual(B.run_batch(self.tmp, "r", adapter=self.a, stop_after_games=1).status, "stopped_requested")
        adir = B.batch_dir(self.tmp, "r") / "games" / "g001-uniform-stage-s12" / "attempt-001"
        before = {p.name: p.read_bytes() for p in (adir / "prestop").iterdir()}
        self.assertEqual(B.run_batch(self.tmp, "r", adapter=self.a).status, "completed")
        self.assertEqual({p.name: p.read_bytes() for p in (adir / "prestop").iterdir()}, before)

    def test_plan_settings_are_checked_and_old_formats_not_resumed(self):
        with self.assertRaises(B.BatchRefused):
            self.plan("bad", prestop_inputs=True, prestop_limits={"max_fetches_per_game": 0, "max_response_bytes": 1, "max_rows_bytes": 1})
        self.plan("x", prestop_inputs=True)
        bdir = B.batch_dir(self.tmp, "x")
        original = json.loads((bdir / "plan.json").read_bytes())
        for change in ({"format": "kyuura-vai-batch-plan/6"}, {"prestop_inputs": dict(original["prestop_inputs"], unknown=1)},
                       {"prestop_inputs": dict(original["prestop_inputs"], enabled=1)}, {"prestop_inputs": None}):
            with self.subTest(change):
                data = B.json_bytes({**original, **change})
                (bdir / "plan.json").write_bytes(data)
                (bdir / "plan.sha256").write_text(B.sha256_bytes(data) + "  plan.json\n", encoding="utf-8")
                with self.assertRaises(B.BatchRefused):
                    B.load_plan(bdir, self.a)

    def test_stop_reasons_for_prestop(self):
        policy = B._policy_dict(B.StopPolicy())
        base = {"termination": "game_over", "judge": {}, "replay_run": {"matches_expectation": True}, "correspondence_problems": 0, "anomalies": []}
        self.assertEqual(B.stop_reasons(dict(base, prestop={"status": "complete"}, prestop_problems=[]), policy, False, True), ([], []))
        self.assertEqual(B.stop_reasons(base, policy, False, True), (["prestop:missing"], []))
        self.assertEqual(B.stop_reasons(dict(base, prestop={"status": "capped", "capped": [P.CAP_FETCHES]}, prestop_problems=[]), policy, False, True),
                         ([], [f"prestop:capped:{P.CAP_FETCHES}"]))
        self.assertEqual(B.stop_reasons(dict(base, prestop={"status": "complete"}, prestop_problems=["x"]), policy, False, True)[0], ["prestop:inconsistent:1"])
        self.assertEqual(B.stop_reasons(base, policy), ([], []))  # 無効の計画では要約がなくても止めない


class IsolationTest(unittest.TestCase):
    def test_policies_actions_judge_metrics_do_not_see_prestop(self):
        base = Path(B.__file__).resolve().parent
        for name in ("policies.py", "actions.py", "judge.py", "metrics.py", "records.py", "negative.py", "observe.py", "reach.py"):
            with self.subTest(name):
                self.assertNotIn("prestop", (base / name).read_text(encoding="utf-8"))
        runner = (base / "runner.py").read_text(encoding="utf-8")
        self.assertEqual(runner.count("self.prestop"), 3)  # 代入・呼ぶ前の確かめ・_prestop_fetch の中
        self.assertEqual(runner.count('request(endpoint, "inputs", game=game, revision=revision'), 1)  # 記録用の要求は 1 か所だけ


if __name__ == "__main__":
    unittest.main()
