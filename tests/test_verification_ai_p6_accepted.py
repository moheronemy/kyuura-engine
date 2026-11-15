"""P6 の受理の中身の判定の接続のテスト（docs/verification-ai-batch.md 16 章）。

既存の P6 の 3 つの構築盤面（``tools/verification_ai/fixtures_p6.py``。出典はエンジンのテスト ``tests/test_legal_actions_p6_face_down_retreat_v0_174.py`` の
``face_down_active``）を、スナップショットから復元して本物の runner（復元した対戦を使うテスト用の派生）で動かし、受理のあとの公開のログの記録 → 単局の判定（変異の実行の中）
と逐次バッチの判定の入口（``batch.judge_trace``）まで確かめる。入力はケースの選び手（方策ではない）が、共通の行動生成の段の中から選ぶ。

- P6A（本当のカードはたね・にげる 0）: エネルギー 0 枚 → 受理。受理の中身は「おもてにしてにげた」
- P6B（たね・にげる 3）: エネルギー 1 枚 → エンジンの拒否（WRONG_RETREAT_COST）。受理の中身の判定は付かない。無副作用
- P6C（1 進化）: エネルギー 0 枚 → 受理。受理の中身は「たねでないのでトラッシュ」。そのあとの promote_active は別の送信として判定する

構築盤面の結果で、new_game から届いた証拠ではない。
"""

from __future__ import annotations

import copy
import json
import unittest

from kyuura_engine import legal_actions as L
from kyuura_engine.observation import visible_log
from tools.verification_ai import batch as B
from tools.verification_ai import fixtures_p6 as F
from tools.verification_ai import judge as J
from tools.verification_ai import runner as V
from tools.verification_ai.policies import UniformPolicy

from tests.test_verification_ai_batch import Base, FakeAdapter, summary
from tests.test_verification_ai_batch_judge import FixtureRunner, summary_and_rest


class P6Pick(UniformPolicy):
    """ケースの選び手（方策ではない）: 最初はにげるの候補を選び、トラッシュの段の数で ``energy`` 枚を選ぶ。にげたあとは promote_active・end_turn の順で選ぶ。"""

    name, version = "scripted-test", 0

    def __init__(self, energy):
        super().__init__("scripted-test")
        self.energy = energy
        self.retreated = False
        self.contexts = []

    def choose(self, purpose, items, context):
        self.contexts.append(sorted(context))  # 方策に渡る値の鍵（完全な状態・検証者の記録が入っていないことを見る）
        if purpose == "candidate":
            kinds = [c["kind"] for c in items]
            if not self.retreated and "retreat" in kinds:
                self.retreated = True
                return kinds.index("retreat"), "scripted"
            for kind in ("promote_active", "end_turn"):
                if kind in kinds:
                    return kinds.index(kind), "scripted"
            return 0, "scripted"
        if purpose == "count" and context["stage"].get("role") == "discard":
            return items.index(self.energy), "scripted"
        return 0, "scripted"


class Probe:
    """単局の runner の判定（変異の実行の中の判定）を有効にし、送信の前後の確認値・公開の範囲・古い取っ手を記録する（入力・送信は変えない）。"""

    def __init__(self):
        self.rows = []

    def _disclosure(self, runner):
        side = V.request(runner.endpoints[1], "view")["observation"]["players"][0]  # 相手（プレイヤー 1）の観測の、プレイヤー 0 のバトル場
        active = side.get("active") or {}
        state = runner.game.state
        return {"opponent_active_face_down": active.get("face_down"), "opponent_active_card_id": active.get("card_id"),
                "spectator_log": len(visible_log(state, None)), "opponent_log": len(visible_log(state, 1))}

    def before_submit(self, runner, actor, endpoint, entry, candidate, stages, handle, choices):
        self.rows.append({"attempt": entry["n"], "kind": candidate["kind"], "handle": handle, "choices": choices, "endpoint": endpoint,
                          "before": J.snapshot(runner.game, runner.hub), "disclosure_before": self._disclosure(runner)})

    def after_accept(self, runner, actor, endpoint, entry):
        row = self.rows[-1]
        row["after"] = J.snapshot(runner.game, runner.hub)
        row["disclosure_after"] = self._disclosure(runner)
        state = runner.game.state
        row["opponent_new_log"] = visible_log(state, 1)[row["disclosure_before"]["opponent_log"]:]
        stale = V.request(endpoint, "check", **row["handle"], choices=row["choices"])
        row["old_handle_check"] = (stale["response"].get("refusal") or {}).get("code")

    def summary(self):
        return {}


class ProbeRunner(FixtureRunner):
    """拒否のあとの確かめ（runner が公開の更新を取り出す前）に、送信の前との違いを記録する。"""

    def _after_refusal_like(self, entry, actor):
        probe = self.negative
        if isinstance(probe, Probe) and probe.rows and probe.rows[-1]["attempt"] == entry["n"]:
            row = probe.rows[-1]
            row["after"] = J.snapshot(self.game, self.hub)
            row["changed"] = J.compare(row["before"], row["after"])
            row["disclosure_after"] = probe._disclosure(self)
        super()._after_refusal_like(entry, actor)


def run_p6(fixture_id, energy, operations, negative=None):
    state, _record = F.build(fixture_id)
    text, error = F.snapshot_text(state, fixture_id)
    assert text is not None, error
    config = V.Config(profile="boundary", limits=V.Limits(operations=operations, seconds=60), run_id=f"test-{fixture_id}")
    policy = P6Pick(energy)
    result = ProbeRunner(config, text, policy_factory=lambda seed, dist: policy, negative=negative).run()
    return result, policy


def attempts(result):
    return [e for e in result["trace"] if e.get("type") == "attempt" and e.get("submit") is not None]


CASES = {  # fixture: (energy, operations, 受理の中身, 公開されたカード ID)
    "P6A": (0, 1, "p6_revealed_and_retreated", F.RATTATA),
    "P6C": (0, 2, "p6_revealed_not_basic_and_trashed", F.KADABRA),
}


class AcceptedContentTest(unittest.TestCase):
    """受理の 2 種類: 本物の runner → 単局の判定とバッチの判定の入口が同じ記録・同じ関数で同じ値。"""

    def check(self, fixture_id):
        energy, operations, expected_reason, card_id = CASES[fixture_id]
        result, policy = run_p6(fixture_id, energy, operations)
        self.assertEqual(result["termination"]["class"], V.LIMIT_OPERATIONS)
        self.assertEqual(result["anomalies"], [])
        entry = attempts(result)[0]
        self.assertEqual((entry["candidate"]["kind"], entry["submit"]["outcome"]), ("retreat", "accepted"))
        self.assertTrue(J.is_p6(entry["candidate"], entry["stages"]))
        self.assertEqual(J.accepted_content_check(entry), J.ACCEPTED_P6)
        self.assertNotIn("judge_p6_accepted", entry)  # 変異の実行でなければ runner は判定を当てない（バッチが当てる。重ねて数えない）
        events = entry["public_events_after_accept"]
        self.assertEqual((events[0]["kind"], events[0]["card_id"]), (J.P6_REVEALED, card_id))  # 公開されたカード ID（観戦者の公開のログ）
        original = copy.deepcopy(result)
        judged = B.judge_trace(result)
        self.assertEqual(result, original)  # 判定は trace の写しに当てるだけで、元の API の応答・記録を変えない
        self.assertEqual(judged["counts"], {J.EXPECTED: len(attempts(result))})  # 送信の判定（受理の中身は別の軸。二重に数えない）
        content = judged["accepted_content"]
        self.assertEqual(content["counts"], {J.EXPECTED: 1})
        self.assertEqual(content["by_check"], {J.ACCEPTED_P6: {J.EXPECTED: 1}})
        row = content["rows"][0]
        self.assertEqual((row["attempt"], row["check"], row["reasons"], row["revealed_card_id"], row["events_recorded"]),
                         (entry["n"], J.ACCEPTED_P6, [expected_reason], card_id, True))
        self.assertEqual(judged["undetermined"], [])
        self.assertEqual(B.stop_reasons(summary_and_rest(B.judge_summary(judged)), B._policy_dict(B.StopPolicy())), ([], []))
        # 方策に渡る値に、完全な状態・検証者の記録（公開のログの記録・判定）が入っていない
        self.assertTrue(all(set(keys) <= {"view", "candidates", "candidate", "stage", "chosen", "picks", "purpose"} for keys in policy.contexts), policy.contexts)
        # 単局の runner の判定（変異の実行の中）: 同じ entry に同じ値が付き、記録した公開のログも同じ
        probe = Probe()
        single, _p = run_p6(fixture_id, energy, operations, negative=probe)
        entry_single = attempts(single)[0]
        self.assertEqual(entry_single["judge_p6_accepted"], {"verdict": row["verdict"], "reasons": row["reasons"]})
        self.assertNotIn("judge_face_down_power_accepted", entry_single)
        self.assertEqual(entry_single["public_events_after_accept"], events)
        self.assertEqual(single["judge_termination"], {"verdict": judged["termination"]["verdict"], "reasons": judged["termination"]["reasons"]})
        self.assertEqual(B.judge_trace(single)["accepted_content"]["rows"], content["rows"])
        # 受理の正当な公開と古い取っ手の失効
        p = probe.rows[0]
        self.assertEqual(J.judge_effects("accepted", J.compare(p["before"], p["after"]))[0], J.EXPECTED)
        self.assertEqual(p["disclosure_before"]["opponent_active_face_down"], True)
        self.assertIsNone(p["disclosure_before"]["opponent_active_card_id"])  # 受理の前は相手に本当のカードが見えない
        self.assertEqual(p["opponent_new_log"][0]["card_id"], card_id)  # 受理で相手にも公開される
        self.assertEqual(p["old_handle_check"], L.CANDIDATES_STALE)
        return result, judged, single

    def test_revealed_and_retreated(self):
        result, judged, _single = self.check("P6A")
        self.assertEqual(len(attempts(result)), 1)

    def test_revealed_not_basic_and_trashed_then_promote(self):
        result, judged, single = self.check("P6C")
        follow = attempts(result)[1]
        self.assertEqual((follow["candidate"]["kind"], follow["submit"]["outcome"]), ("promote_active", "accepted"))
        self.assertIsNone(J.accepted_content_check(follow))  # 交代の決定への回答は受理の中身の判定の対象でなく、送信の判定だけ
        self.assertNotIn("public_events_after_accept", follow)
        self.assertEqual([r["attempt"] for r in judged["accepted_content"]["rows"]], [attempts(result)[0]["n"]])
        self.assertEqual([(r["kind"], r["verdict"]) for r in judged["rows"]], [("retreat", J.EXPECTED), ("promote_active", J.EXPECTED)])
        trashed = attempts(result)[0]["public_events_after_accept"]
        self.assertEqual([e["kind"] for e in trashed], [J.P6_REVEALED, J.P6_TRASHED])  # 受理の直後（交代の決定の前）までの出来事
        self.assertNotIn("judge_p6_accepted", attempts(single)[1])


class RejectionTest(unittest.TestCase):
    def test_rejection_has_no_accepted_content_and_no_side_effects(self):
        probe = Probe()
        result, _policy = run_p6("P6B", 1, 1, negative=probe)
        self.assertEqual(result["anomalies"], [])
        entry = attempts(result)[0]
        self.assertEqual((entry["candidate"]["kind"], entry["submit"]["outcome"], entry["submit"]["verifier"]["engine_code"]),
                         ("retreat", "rejected", "WRONG_RETREAT_COST"))
        self.assertIsNone(J.accepted_content_check(entry))
        self.assertNotIn("public_events_after_accept", entry)
        self.assertNotIn("judge_p6_accepted", entry)
        self.assertEqual(entry["judge"]["verdict"], J.NORMAL_REJECTION)
        judged = B.judge_trace(result)
        self.assertEqual(judged["counts"], {J.NORMAL_REJECTION: 1})
        self.assertEqual(judged["accepted_content"], {"counts": {}, "by_check": {}, "rows": []})
        row = probe.rows[0]
        self.assertEqual(row["changed"], [])  # 状態・確認値（乱数・ログ・決定をふくむ）・他者への新しい更新・更新の番号が変わらない
        self.assertEqual(row["disclosure_before"], row["disclosure_after"])  # うらのまま（相手・観戦者に公開されない）


class MissingRecordTest(Base):
    """記録の欠け: undetermined（accepted_content_unrecorded）で、根拠不足の停止とは別の分類。バッチの停止方針が止め、停止の確かめを勝手に外さない。"""

    def test_missing_events_are_undetermined_and_stop(self):
        result, _policy = run_p6("P6A", 0, 1)
        for e in result["trace"]:
            e.pop("public_events_after_accept", None)  # 記録の欠け（旧 trace の形）
        judged = B.judge_trace(result)
        self.assertEqual(judged["accepted_content"]["by_check"], {J.ACCEPTED_P6: {J.UNDETERMINED: 1}})
        self.assertEqual(judged["accepted_content"]["rows"][0]["reasons"], [J.P6_EVENTS_NOT_RECORDED])
        self.assertEqual(judged["counts"], {J.EXPECTED: 1})  # 送信の判定は変わらない
        self.assertEqual([(u["source"], u["category"]) for u in judged["undetermined"]], [("accepted_content", B.ACCEPTED_CONTENT_UNRECORDED)])
        self.assertNotEqual(B.ACCEPTED_CONTENT_UNRECORDED, B.EVIDENCE_MISSING_STOP)
        stop, _note = B.stop_reasons(summary_and_rest(B.judge_summary(judged)), B._policy_dict(B.StopPolicy()))
        self.assertEqual(stop, ["undetermined:accepted_content_unrecorded:1"])
        # 根拠不足の停止を続ける設定（vai-batch-b2 と同じ）でも、受理の中身の記録の欠けは止める
        policy = B._policy_dict(B.StopPolicy(on_undetermined={**B.StopPolicy().on_undetermined, B.EVIDENCE_MISSING_STOP: "continue"}))
        self.assertEqual(B.stop_reasons(summary_and_rest(B.judge_summary(judged)), policy)[0], stop)

    def test_events_that_do_not_match_are_not_guessed(self):
        result, _policy = run_p6("P6C", 0, 2)
        entry = attempts(result)[0]
        for events, category in (([], B.UNCLASSIFIED), (entry["public_events_after_accept"][1:], B.UNCLASSIFIED),
                                 (entry["public_events_after_accept"] + [{"kind": J.P6_RETREATED}], B.UNCLASSIFIED)):
            broken = copy.deepcopy(result)
            attempts(broken)[0]["public_events_after_accept"] = events
            judged = B.judge_trace(broken)
            self.assertEqual(judged["accepted_content"]["counts"], {J.UNDETERMINED: 1}, events)
            self.assertEqual([u["category"] for u in judged["undetermined"]], [category])

    def test_reason_constants_match(self):
        self.assertEqual(B.ACCEPTED_CONTENT_NOT_RECORDED_REASONS, J.ACCEPTED_CONTENT_NOT_RECORDED)
        self.assertIn(B.ACCEPTED_CONTENT_UNRECORDED, B.UNDETERMINED_CATEGORIES)
        self.assertEqual(B.StopPolicy().on_undetermined[B.ACCEPTED_CONTENT_UNRECORDED], "stop")

    def test_batch_stops_and_acknowledgement_is_not_removed(self):
        unrecorded = {"source": "accepted_content", "attempt": 1, "kind": "retreat", "reasons": [J.P6_EVENTS_NOT_RECORDED],
                      "category": B.ACCEPTED_CONTENT_UNRECORDED}
        s = summary(content={J.UNDETERMINED: 1}, undetermined=[unrecorded])
        s["judge"]["accepted_content_by_check"] = {J.ACCEPTED_P6: {J.UNDETERMINED: 1}}
        a = FakeAdapter(script={"g001-uniform-stage-s1": s})
        self.plan(a, seeds=(1, 2))
        r = self.run_(a)
        self.assertEqual((r.status, r.stop["reasons"]), ("stopped_policy", ["undetermined:accepted_content_unrecorded:1"]))
        B.aggregate(self.tmp, "b", adapter=a)
        for _ in range(2):
            with self.assertRaises(B.BatchRefused):
                self.run_(a)
        self.assertNotIn("stop_acknowledged", [e["event"] for e in self.ledger()])
        self.assertEqual(a.calls, ["g001-uniform-stage-s1"])
        agg = json.loads((self.bdir() / "aggregate.json").read_text(encoding="utf-8"))
        self.assertEqual(agg["judge"]["accepted_content_by_check"], {J.ACCEPTED_P6: {J.UNDETERMINED: 1}})
        self.assertEqual(agg["judge"]["undetermined_by_category"][B.ACCEPTED_CONTENT_UNRECORDED]["count"], 1)
        self.assertEqual(self.run_(a, acknowledge=["g001-uniform-stage-s1"]).status, "completed")


class AggregateSeparationTest(Base):
    def test_u_r3a_and_p6_are_counted_separately(self):
        s1 = summary(content={J.EXPECTED: 2})
        s1["judge"]["accepted_content_by_check"] = {J.ACCEPTED_P6: {J.EXPECTED: 1}, J.ACCEPTED_FACE_DOWN_POWER: {J.EXPECTED: 1}}
        s2 = summary(content={J.EXPECTED: 1})
        s2["judge"]["accepted_content_by_check"] = {J.ACCEPTED_P6: {J.EXPECTED: 1}}
        a = FakeAdapter(script={"g001-uniform-stage-s1": s1, "g002-uniform-stage-s2": s2})
        self.plan(a, seeds=(1, 2))
        self.assertEqual(self.run_(a).status, "completed")
        agg = json.loads((self.bdir() / "aggregate.json").read_text(encoding="utf-8"))
        self.assertEqual(agg["judge"]["accepted_content"], {J.EXPECTED: 3})
        self.assertEqual(agg["judge"]["accepted_content_by_check"], {J.ACCEPTED_P6: {J.EXPECTED: 2}, J.ACCEPTED_FACE_DOWN_POWER: {J.EXPECTED: 1}})
        public = json.loads((self.tmp / "public" / "runs" / "b" / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(public["judge"]["accepted_content_by_check"], agg["judge"]["accepted_content_by_check"])


if __name__ == "__main__":
    unittest.main()
