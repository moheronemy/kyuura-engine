"""主体別の観測・更新・公開ログの記録（tools/verification_ai/observe.py。docs/verification-ai-observation.md）。

本物の runner（開始だけ既存のテストの盤面。fixtures_observe）で、記録の中身・通常の進行への非干渉・欠落の検出・バッチの保存とハッシュの照合を確かめる。
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from kyuura_engine.replay_record import checks
from tools.verification_ai import batch as B
from tools.verification_ai import fixtures_observe as F
from tools.verification_ai import observe as O
from tools.verification_ai import records as R
from tools.verification_ai.judge import judge_recorded_accepted_content

_CACHE: dict = {}


def run(name, recorder=True):
    key = (name, recorder)
    if key not in _CACHE:
        rec = O.ObservationRecorder() if recorder else None
        result = F.run_case(name, recorder=rec)
        files = {} if rec is None else {n: data for n, data in rec.files()}
        _CACHE[key] = (result, rec, files)
    return _CACHE[key]


def rows_of(files):
    return [json.loads(line) for line in files[O.ROWS].decode("utf-8").splitlines()]


def view(files, key):
    return json.loads(files[f"observe/view-{key}.json"])


def card_refs(value, out=None):
    """JSON の中の、カードの uid を指す値（``card``・``cards`` の整数）を集める。"""
    out = set() if out is None else out
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "card" and type(v) is int:
                out.add(v)
            elif k == "cards" and isinstance(v, list):
                out.update(x for x in v if type(x) is int)
                card_refs([x for x in v if type(x) is not int], out)
            else:
                card_refs(v, out)
    elif isinstance(value, list):
        for v in value:
            card_refs(v, out)
    return out


def attempts(result):
    return [e for e in result["trace"] if e.get("type") == "attempt"]


class CaseTest(unittest.TestCase):
    def test_every_case_reaches_its_target_and_the_record_is_complete(self):
        for name in F.CASES:
            with self.subTest(name):
                result, rec, files = run(name)
                self.assertEqual(result["termination"]["class"], "script_complete")
                summary = json.loads(files[O.SUMMARY])
                self.assertEqual((summary["status"], summary["problems_total"], summary["failure"]), (O.COMPLETE, 0, None))
                for key in ("0", "1", "spectator"):
                    self.assertEqual(summary["view_records"][key]["validate"], "structure_valid")
                self.assertEqual(result["fixture"]["integrity"]["check_invariants"], [])

    def test_search_options_reach_only_the_answerer(self):
        result, rec, files = run("search")
        state0, _ = F.build("O-SEARCH")
        deck = set(state0.players[0].deck)
        search = next(e for e in attempts(result) if any(s.get("decision_kind") == "search_deck" for s in e.get("stages") or []))
        offered = {o["card"] for o in search["stages"][0]["options"]}
        self.assertEqual(offered, deck)  # 回答者（プレイヤー 0）には山札のカードが選べるものとして届く
        picked = search["meaning"][0]["option"]["card"]
        for key in ("1", "spectator"):
            seen = card_refs(view(files, key))
            self.assertEqual(seen & deck, set(), key)  # 相手・観戦者の観測・ログに、山札のカード・選んだカードが出ない
            self.assertNotIn(picked, seen)
        self.assertIn(picked, card_refs(view(files, "0")["entries"][-1]["observation"]))  # 本人は手札に見える
        row = next(r for r in rows_of(files) if r.get("attempt") == search["n"])
        for audience in ("1", "spectator", "host"):
            for u in row["updates"][audience]["updates"]:
                self.assertTrue(u["observation_same_as_after_view"])
                self.assertNotIn("observation", u)
        event = [e["event"] for e in view(files, "1")["entries"][-1]["events"] if e["event"]["kind"] == "search_deck"]
        self.assertEqual(event, [{"hidden": {"card": None}, "kind": "search_deck", "player": 0, "turn": 5}])

    def test_decision_answered_by_the_opponent_reaches_only_that_player(self):
        result, rec, files = run("opponent")
        self.assertEqual({e["actor"] for e in attempts(result)}, {1})
        self.assertFalse([x for x in result["actor_logs"][0] if x.get("type") == "attempt"])
        state, _ = F.build("O-OPPONENT")
        hub = ClientHub.from_state(state)  # 別の hub（runner の対戦とは別）で、答えない主体の候補と入力を見る
        r0 = hub.player(0).handle({"contract": "kyuura-client-api", "format": 1, "type": "candidates"})["response"]
        r1 = hub.player(1).handle({"contract": "kyuura-client-api", "format": 1, "type": "candidates"})["response"]
        self.assertEqual((r0["situation"], r0["candidates"], r0["empty_reason"]), (L.WAITING_FOR_PLAYER, [], L.EMPTY_NOT_ACTOR))
        self.assertEqual((r1["situation"], r1["candidates"][0]["kind"]), (L.ACTOR_TO_ACT, L.KIND_ANSWER_DECISION))
        refused = hub.player(0).handle({"contract": "kyuura-client-api", "format": 1, "type": "inputs", "game": r1["game"], "revision": r1["revision"],
                                        "candidate": r1["candidates"][0]["id"]})
        self.assertFalse(refused["ok"])
        row = [r for r in rows_of(files) if r["kind"] == "submit"][0]
        self.assertEqual((row["actor"], row["outcome"], row["accepted_index"]), (1, D.ACCEPTED, 1))
        self.assertEqual({a: [u["number"] for u in row["updates"][a]["updates"]] for a in ("0", "1", "spectator", "host")},
                         {"0": [1], "1": [1], "spectator": [1], "host": [1]})

    def test_trader_cards_are_shown_to_everyone(self):
        result, rec, files = run("trader")
        rows = {r.get("attempt"): r for r in rows_of(files)}
        for kind in ("return_to_deck", "search_deck"):
            entry = next(e for e in attempts(result) if any(s.get("decision_kind") == kind for s in e.get("stages") or []))
            card = entry["meaning"][0]["option"]["card"]
            row = rows[entry["n"]]
            for key in ("0", "1", "spectator"):
                n = row["viewers"][key]["view_entry"]
                events = view(files, key)["entries"][n - 1]["events"]
                self.assertIn(card, card_refs(events), (kind, key))  # 選んだ・もどしたカードは、その送信の新しいログで全員に公開

    def test_rejection_reaches_only_the_sender(self):
        result, rec, files = run("er9")
        rows = [r for r in rows_of(files) if r["kind"] == "submit"]
        rejected = [r for r in rows if r["outcome"] == D.REJECTED]
        self.assertEqual(len(rejected), 1)
        r = rejected[0]
        self.assertEqual((r["accepted_index"], r["viewers"]["0"]["view_kind"], r["viewers"]["1"]["view_entry"], r["viewers"]["spectator"]["view_entry"]),
                         (None, "own_rejection", None, None))
        for key in ("0", "1", "spectator"):
            self.assertEqual(r["viewers"][key]["before"], r["viewers"][key]["after"])
        self.assertEqual({a: v for a, v in r["updates"].items()}, {a: {"status": "drained", "updates": []} for a in ("0", "1", "spectator", "host")})
        notice = view(files, "0")["entries"][r["viewers"]["0"]["view_entry"] - 1]["notice"]
        self.assertEqual((notice["outcome"], notice["role"]), (D.REJECTED, "actor"))
        self.assertEqual((notice["diagnostic_id"], notice["category"]), ("UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE", "unresolved_ruling"))
        for key in ("1", "spectator"):
            self.assertNotIn("own_rejection", [e["kind"] for e in view(files, key)["entries"]])
        # 受理番号だけでは拒否を見分けられないので、ローカルの通し番号で区別する（拒否の前後の受理番号は連続）
        self.assertEqual([x["accepted_index"] for x in rows], [1, 2, None, 3])
        self.assertEqual([x["seq"] for x in rows], sorted({x["seq"] for x in rows}))

    def test_accepted_public_log_feeds_the_accepted_content_judge(self):
        for name, kind in (("p6", "retreat"), ("ur3a", "use_power")):
            with self.subTest(name):
                result, rec, files = run(name)
                entry = next(e for e in attempts(result) if e["candidate"]["kind"] == kind)
                row = next(r for r in rows_of(files) if r.get("attempt") == entry["n"])
                n = row["viewers"]["spectator"]["view_entry"]
                recorded = [e["event"] for e in view(files, "spectator")["entries"][n - 1]["events"]]
                self.assertEqual(recorded, json.loads(json.dumps(entry["public_events_after_accept"])))  # trace.jsonl に書いた形（タプルは JSON の並び）
                again = dict(entry, public_events_after_accept=recorded)
                self.assertEqual(judge_recorded_accepted_content(again), judge_recorded_accepted_content(entry))
                self.assertEqual(judge_recorded_accepted_content(again)[1], "expected")


class NonInterferenceTest(unittest.TestCase):
    def test_recording_does_not_change_actions_rng_state_or_updates(self):
        for name in F.CASES:
            with self.subTest(name):
                on, _rec, _files = run(name, True)
                off, _none, _ = run(name, False)
                self.assertEqual(R.action_sequence(on["trace"]), R.action_sequence(off["trace"]))
                self.assertEqual(checks(on["final_state"]), checks(off["final_state"]))  # 状態と乱数の確認値
                self.assertEqual((on["termination"]["class"], on["counters"], on["anomalies"]), (off["termination"]["class"], off["counters"], off["anomalies"]))
                self.assertEqual({k: p["draws"] for k, p in on["policies"].items()}, {k: p["draws"] for k, p in off["policies"].items()})

    def test_recorder_never_takes_updates_and_sees_what_the_runner_took(self):
        taken = {True: [], False: []}
        original = ClientHub.take_updates

        for flag in (True, False):
            def spy(self, audience, _flag=flag):
                got = original(self, audience)
                taken[_flag].append((audience, [u["number"] for u in got], [O.digest(u) for u in got]))
                return got

            ClientHub.take_updates = spy
            try:
                rec = O.ObservationRecorder() if flag else None
                F.run_case("er9", recorder=rec)
            finally:
                ClientHub.take_updates = original
            if flag:
                files = dict(rec.files())
        self.assertEqual(taken[True], taken[False])  # 取り出しの回数・順・中身が同じ（記録側は取り出さない）
        drained = [(a, [u["number"] for u in item["updates"]]) for r in rows_of(files) if r["kind"] in ("submit", "check_invalid")
                   for a, item in r["updates"].items()]
        self.assertEqual(sorted(drained), sorted((str(a), n) for a, n, _d in taken[True]))

    def test_policy_and_input_generation_do_not_see_the_recorder(self):
        """方策・行動生成・判定・指標は記録を参照しない（runner は self.recorder を _rec からだけ呼ぶ）。"""
        base = Path(B.__file__).resolve().parent
        for name in ("policies.py", "actions.py", "judge.py", "metrics.py", "records.py", "negative.py"):
            text = (base / name).read_text(encoding="utf-8")
            with self.subTest(name):
                self.assertNotIn("recorder", text)
                self.assertNotIn("observe import", text)
        runner = (base / "runner.py").read_text(encoding="utf-8")
        self.assertEqual(runner.count("self.recorder"), 2)  # 代入と _rec の中だけ

    def test_rows_match_trace_by_operation_id_and_attempt(self):
        for name in F.CASES:
            with self.subTest(name):
                result, rec, files = run(name)
                by_n = {e["n"]: e for e in attempts(result)}
                submits = [r for r in rows_of(files) if r["kind"] == "submit"]
                self.assertEqual(len(submits), result["counters"]["operations"])
                for r in submits:
                    e = by_n[r["attempt"]]
                    self.assertEqual((r["operation_id"], r["actor"], r["outcome"]), (e["operation_id"], e["actor"], e["submit"]["outcome"]))
                self.assertEqual([r["accepted_index"] for r in submits if r["accepted_index"] is not None], list(range(1, result["counters"]["accepted"] + 1)))


class MissingTest(unittest.TestCase):
    def test_updates_the_runner_did_not_take_are_marked_not_drained(self):
        from tools.verification_ai.runner import Runner

        original = Runner._after_accept

        def skip(self, entry, sent):  # 通常の取り出しをしない runner（記録側が空と書かないことを見る）
            return None

        Runner._after_accept = skip
        try:
            rec = O.ObservationRecorder()
            F.run_case("opponent", recorder=rec)
        finally:
            Runner._after_accept = original
        summary = rec.summary()
        self.assertEqual(summary["status"], O.INCOMPLETE)
        self.assertEqual(summary["problem_codes"], {"incomplete:updates_not_drained": 4})
        row = [r for r in rec.rows if r["kind"] == "submit"][0]
        self.assertEqual(row["updates"]["1"]["status"], "not_drained")

    def test_recorder_failure_is_recorded_and_the_game_is_unchanged(self):
        original = O.ObservationRecorder.on_drained

        def boom(self, audience, got):
            raise RuntimeError("記録の故障（試験）")

        O.ObservationRecorder.on_drained = boom
        try:
            rec = O.ObservationRecorder()
            broken = F.run_case("er9", recorder=rec)
        finally:
            O.ObservationRecorder.on_drained = original
        off, _none, _ = run("er9", False)
        self.assertEqual(R.action_sequence(broken["trace"]), R.action_sequence(off["trace"]))
        self.assertEqual(checks(broken["final_state"]), checks(off["final_state"]))
        summary = rec.summary()
        self.assertEqual((summary["status"], summary["failure"]["where"], summary["failure"]["type"]), (O.RECORDER_FAILED, "drained", "RuntimeError"))
        files = dict(rec.files())
        self.assertIn("missing", json.loads(files["observe/view-1.json"]))  # 閉じられなかった記録を空の記録として書かない

    def test_view_record_mismatch_is_detected(self):
        result, rec, files = run("search")
        rec2 = O.ObservationRecorder()
        rec2.rows = json.loads(json.dumps(rec.rows))
        rec2._records = rec._records
        rec2._entries = dict(rec._entries)
        submit = next(r for r in rec2.rows if r["kind"] == "submit")
        submit["viewers"]["1"]["after"]["observation_sha256"] = "0" * 64
        problems = rec2._verify_against_records()["problems"]
        self.assertIn("view_entry_observation", [p["code"] for p in problems])


class BatchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vai-observe-batch-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_real_batch_with_observation_keeps_the_golden_actions_and_verifies_hashes(self):
        from tests.test_verification_ai_v2_repeat import ACTION_GOLDEN

        a = B.EngineAdapter("test")
        plan = B.make_plan(self.tmp, "o", engine_commit="test", tool_commit="test", seeds=[12], modes=["uniform-stage"], deck0="hitmonchan-dewgong",
                           deck1="venusaur-parasect", adapter=a, game_limits={"operations": 80, "seconds": 60}, observation=True)
        self.assertEqual((plan["format"], plan["observation"]["enabled"]), (B.PLAN_FORMAT, True))
        report = B.run_batch(self.tmp, "o", adapter=a)
        self.assertEqual(report.status, "completed")
        bdir = B.batch_dir(self.tmp, "o")
        adir = bdir / "games" / "g001-uniform-stage-s12" / "attempt-001"
        marker = json.loads((adir / B.MARKER).read_text(encoding="utf-8"))
        s = marker["summary"]
        self.assertEqual((s["sequences"]["action"]["length"], s["sequences"]["action"]["sha256"]), ACTION_GOLDEN["uniform-stage-s12"])  # 記録の有効で行動が変わらない
        self.assertEqual(s["observation"]["status"], O.COMPLETE)
        self.assertEqual(marker["stop"], [])
        self.assertTrue(set(O.FILES) <= set(marker["required"]))
        self.assertTrue(s["replay_run"]["matches_expectation"])
        rows = [json.loads(x) for x in (adir / O.ROWS).read_text(encoding="utf-8").splitlines()]
        trace = [json.loads(x) for x in (adir / "trace.jsonl").read_text(encoding="utf-8").splitlines()]
        ops = {e["operation_id"] for e in trace if e.get("type") == "attempt" and e.get("operation_id")}
        self.assertEqual({r["operation_id"] for r in rows if r["kind"] == "submit"}, ops)
        agg = B.aggregate(self.tmp, "o", adapter=a)
        self.assertEqual(agg["public"]["observation"]["status"], {O.COMPLETE: 1})
        self.assertGreater(agg["verifier"]["evidence"]["game_complete_observation"]["bytes"], 0)
        plan_, plan_sha = B.load_plan(bdir, a)
        entry = plan_["games"][0]
        self.assertEqual(B.verify_complete(adir, plan=plan_, plan_sha=plan_sha, entry=entry)[1], [])
        # 破損: 観測の記録の 1 バイトを書きかえる → ハッシュの不一致
        path = adir / "observe" / "view-1.json"
        original = path.read_bytes()
        path.write_bytes(original[:-2] + b" \n")
        self.assertTrue(any("observe/view-1.json の sha256" in p for p in B.verify_complete(adir, plan=plan_, plan_sha=plan_sha, entry=entry)[1]))
        path.write_bytes(original)
        # 欠け: 完了マーカーの required から観測のファイルを外しても、計画が有効なら必須として照らす
        marker_path = adir / B.MARKER
        saved = marker_path.read_bytes()
        bad = dict(marker, required=list(B.REQUIRED_FILES))
        marker_path.write_bytes(json.dumps(bad).encode())
        self.assertTrue(any("required に計画の必須ファイルがない" in p for p in B.verify_complete(adir, plan=plan_, plan_sha=plan_sha, entry=entry)[1]))
        marker_path.write_bytes(saved)

    def test_observation_problem_stops_by_policy(self):
        policy = B._policy_dict(B.StopPolicy())
        base = {"termination": "game_over", "judge": {}, "replay_run": {"matches_expectation": True}, "correspondence_problems": 0, "anomalies": []}
        self.assertEqual(B.stop_reasons(dict(base, observation={"status": O.COMPLETE}), policy), ([], []))
        stop, _ = B.stop_reasons(dict(base, observation={"status": O.INCOMPLETE, "problem_codes": {"incomplete:updates_not_drained": 4}}), policy)
        self.assertEqual(stop, ["observation:incomplete:incomplete:updates_not_drained"])

    def test_old_plan_format_is_not_resumed(self):
        a = B.EngineAdapter("test")
        B.make_plan(self.tmp, "x", engine_commit="test", tool_commit="test", seeds=[12], modes=["uniform-stage"], deck0="hitmonchan-dewgong",
                    deck1="venusaur-parasect", adapter=a)
        bdir = B.batch_dir(self.tmp, "x")
        plan = json.loads((bdir / "plan.json").read_bytes())
        plan["format"] = "kyuura-vai-batch-plan/3"
        del plan["observation"]
        data = B.json_bytes(plan)
        (bdir / "plan.json").write_bytes(data)
        (bdir / "plan.sha256").write_text(B.sha256_bytes(data) + "  plan.json\n", encoding="utf-8")
        with self.assertRaises(B.BatchRefused):
            B.load_plan(bdir, a)


if __name__ == "__main__":
    unittest.main()
