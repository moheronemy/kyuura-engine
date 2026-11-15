"""逐次バッチの判定の補完のテスト（docs/verification-ai-batch.md 11 章）。

- 既存の U-R3a の fixture（本人のうらのカードの特殊能力）を、本物の runner に通し、受理のあとの公開のログの記録 → バッチの判定の入口（``batch.judge_trace``）まで確かめる
  （「おもてにして使った」と「たねでないのでトラッシュ」を分ける）。同じ entry に単局の runner（変異の実行の中の判定）が当てた値と同じになることも確かめる
- 記録の欠けでは undetermined（推測しない）・undetermined の分類と停止方針・known_stop・停止の確かめを勝手に外さない・集計の作り直しでゲームの証跡の量が変わらない
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.verification_ai import batch as B
from tools.verification_ai import fixtures_u_r3a as F
from tools.verification_ai import judge as J
from tools.verification_ai import runner as V
from tools.verification_ai.fixtures_v3_3 import restore
from tools.verification_ai.policies import UniformPolicy

from tests.test_verification_ai_batch import Base, FakeAdapter, summary


class _FixtureGame:
    """復元した対戦（snapshot.RestoredGame）を runner の RecordingGame の代わりにする（完全な記録はない。テストだけ）。"""

    def __init__(self, game):
        self._game = game

    def __getattr__(self, name):
        return getattr(self._game, name)

    def last_check(self):
        from kyuura_engine.replay_record import checks

        return checks(self._game.state)

    def close(self):
        return None


class FixtureRunner(V.Runner):
    def __init__(self, config, snapshot, **kw):
        super().__init__(config, **kw)
        self._snapshot = snapshot

    def _start(self):
        from kyuura_engine.client_api import ClientHub

        game, status = restore(self._snapshot)
        assert game is not None, status
        self.game = _FixtureGame(game)
        self.hub = ClientHub(game, verifier=self._on_verifier)
        self.endpoints = {0: self.hub.player(0), 1: self.hub.player(1), V.HOST: self.hub.host()}


class Scripted(UniformPolicy):
    """ケースの選び手（方策ではない）: うらのカードの特殊能力の候補と、段ごとの (場所かカード, カード id) を選ぶ。"""

    name, version = "scripted-test", 0

    def __init__(self, wanted):
        super().__init__("scripted-test")
        self.wanted = wanted

    def choose(self, purpose, items, context):
        if purpose == "candidate":
            return next(i for i, c in enumerate(items) if J.is_face_down_power(c)), "scripted"
        if purpose == "option":
            stage = context["stage"]
            where, card = self.wanted[stage["stage"] - 1]
            by_id = {o["id"]: o for o in stage.get("options", [])}
            for i, oid in enumerate(items):
                o = by_id.get(oid, {})
                if o.get("card_id") == card and (where == "card" or o.get("zone") == where):
                    return i, "scripted"
            raise LookupError(f"stage {stage['stage']}: {where} {card}")
        if purpose == "count":
            return (items.index(1) if 1 in items else 0), "scripted"
        return 0, "scripted"


class NoNegative:
    """単局の runner の判定（変異の実行の中の判定）を有効にするだけの、何もしない negative。"""

    def before_submit(self, *args):
        pass

    def after_accept(self, *args):
        pass

    def summary(self):
        return {}


def run_fixture(fixture_id, wanted, negative=None):
    state, _record = F.build(fixture_id)
    text, error = F.snapshot_text(state, fixture_id)
    assert text is not None, error
    config = V.Config(profile="boundary", limits=V.Limits(operations=1, seconds=60), run_id=f"test-{fixture_id}")
    return FixtureRunner(config, text, policy_factory=lambda seed, dist: Scripted(wanted), negative=negative).run()


USED = [("bench", F.RATTATA), ("card", F.FIRE)]
TRASHED = [("active", F.HITMONCHAN), ("card", F.FIGHTING), ("active", F.HITMONCHAN)]


class FixtureConnectionTest(unittest.TestCase):
    """既存の fixture → 本物の runner → バッチの判定の入口。"""

    def check(self, fixture_id, wanted, expected_reason):
        result = run_fixture(fixture_id, wanted)
        self.assertEqual(result["termination"]["class"], V.LIMIT_OPERATIONS)
        accepted = [e for e in result["trace"] if e.get("type") == "attempt" and (e.get("submit") or {}).get("outcome") == "accepted"]
        self.assertEqual(len(accepted), 1)
        entry = accepted[0]
        self.assertTrue(J.is_face_down_power(entry["candidate"]))
        self.assertIn("public_events_after_accept", entry)  # 単局の runner が、変異の実行でなくても受理のあとの公開のログを記録する
        self.assertNotIn("judge_face_down_power_accepted", entry)  # 変異の実行でなければ runner は判定を当てない（バッチが当てる。重ねて数えない）
        judged = B.judge_trace(result)
        self.assertEqual(judged["accepted_content"]["counts"], {J.EXPECTED: 1})
        self.assertEqual(judged["accepted_content"]["rows"][0]["reasons"][0], expected_reason)
        self.assertEqual(judged["counts"], {J.EXPECTED: 1})  # 送信の判定は 1 件（受理の中身は別の軸）
        self.assertEqual(judged["undetermined"], [])
        summary_ = B.judge_summary(judged)
        self.assertEqual(B.stop_reasons({**summary_and_rest(summary_)}, B._policy_dict(B.StopPolicy())), ([], []))
        # 同じ fixture を単局の runner の判定（変異の実行の中）で走らせると、同じ entry に同じ判定が付く
        single = run_fixture(fixture_id, wanted, negative=NoNegative())
        entry_single = [e for e in single["trace"] if e.get("type") == "attempt" and (e.get("submit") or {}).get("outcome") == "accepted"][0]
        self.assertEqual(entry_single["judge_face_down_power_accepted"], {"verdict": judged["accepted_content"]["rows"][0]["verdict"],
                                                                          "reasons": judged["accepted_content"]["rows"][0]["reasons"]})
        self.assertEqual(entry_single["public_events_after_accept"], entry["public_events_after_accept"])
        self.assertEqual(single["judge_termination"], {"verdict": judged["termination"]["verdict"], "reasons": judged["termination"]["reasons"]})
        return entry

    def test_revealed_and_used(self):
        self.check("UR3A-RC", USED, "face_down_power_revealed_and_used")

    def test_revealed_not_basic_and_trashed(self):
        self.check("UR3A-VN", TRASHED, "face_down_power_revealed_not_basic_and_trashed")

    def test_missing_public_events_is_undetermined_and_stops(self):
        result = run_fixture("UR3A-RC", USED)
        for e in result["trace"]:
            e.pop("public_events_after_accept", None)  # 記録の欠け（古い trace の形）
        judged = B.judge_trace(result)
        self.assertEqual(judged["accepted_content"]["counts"], {J.UNDETERMINED: 1})
        self.assertEqual(judged["accepted_content"]["rows"][0]["reasons"], [J.FACE_DOWN_POWER_EVENTS_NOT_RECORDED])
        # P6 の接続（docs/verification-ai-batch.md 16 章）で、記録の欠けは unclassified から accepted_content_unrecorded（初期値 stop）に分けた
        self.assertEqual([u["category"] for u in judged["undetermined"]], [B.ACCEPTED_CONTENT_UNRECORDED])
        stop, _ = B.stop_reasons(summary_and_rest(B.judge_summary(judged)), B._policy_dict(B.StopPolicy()))
        self.assertEqual(stop, ["undetermined:accepted_content_unrecorded:1"])

    def test_events_that_do_not_match_are_undetermined(self):
        candidate = {"kind": "use_power", "pokemon": {"pokemon": 7, "face_down": True}, "power": {"face_down": True}, "reasons": [J.FACE_DOWN_REASON]}
        self.assertEqual(J.judge_recorded_face_down_power({"candidate": candidate, "public_events_after_accept": []})[0], J.UNDETERMINED)
        both = [{"kind": J.FACE_DOWN_POWER_REVEALED, "pokemon_id": 7, "card_id": "X"}, {"kind": J.FACE_DOWN_POWER_USED, "pokemon_id": 7},
                {"kind": J.FACE_DOWN_POWER_TRASHED, "pokemon_id": 7}]
        self.assertEqual(J.judge_recorded_face_down_power({"candidate": candidate, "public_events_after_accept": both})[0], J.UNDETERMINED)


def summary_and_rest(judge_summary):
    s = summary()
    s["judge"] = judge_summary
    s["termination"] = judge_summary["termination"]["class"]
    return s


class TerminationJudgeTest(unittest.TestCase):
    def test_halt_code_is_kept_and_classified(self):
        halt = {"category": "unresolved_ruling", "diagnostic_id": "UNRESOLVED_MULLIGAN_COMPENSATION"}  # V1 の seed 11 の保存した終わり方と同じ形
        verdict, why = J.judge_run_termination("halted_known", {"halt": halt}, [])
        self.assertEqual((verdict, why), (J.UNDETERMINED, ["halt_condition_not_evidenced:UNRESOLVED_MULLIGAN_COMPENSATION"]))
        self.assertEqual(B.undetermined_category("termination", why, "halted_known"), B.EVIDENCE_MISSING_STOP)
        self.assertEqual(J.judge_run_termination("game_over", {}, [])[0], J.EXPECTED)
        self.assertEqual(J.judge_run_termination("halted_unclassified", {"halt": {"category": "other"}}, [])[0], J.SUSPECT)

    def test_undetermined_categories(self):
        cases = [("submit", ["stop_condition_not_evidenced:X"], None, B.EVIDENCE_MISSING_STOP),
                 ("termination", ["halt_condition_not_evidenced"], "halted_known", B.EVIDENCE_MISSING_STOP),
                 ("submit", ["stop_code_not_in_catalog:X"], None, B.UNKNOWN_DIAGNOSTIC),
                 ("termination", ["halt_code_not_in_catalog:X"], "halted_known", B.UNKNOWN_DIAGNOSTIC),
                 ("submit", ["unknown_outcome:weird"], None, B.CONTRACT_UNKNOWN),
                 ("termination", [], "api_contract_unknown", B.CONTRACT_UNKNOWN),
                 ("termination", [], "no_progress", B.NO_PROGRESS),
                 ("submit", ["stop_not_explained_by_path:X"], None, B.UNCLASSIFIED),
                 ("submit", ["precheck_kind_category:invalid_input"], None, B.UNCLASSIFIED),
                 ("termination", ["halt_after_supported"], "halted_known", B.UNCLASSIFIED)]
        for source, reasons, term, expect in cases:
            self.assertEqual(B.undetermined_category(source, reasons, term), expect, (source, reasons, term))


def und(category, source="submit"):
    return {"source": source, "attempt": 1, "kind": "x", "reasons": ["r"], "category": category}


class PolicyTest(unittest.TestCase):
    def test_only_evidence_missing_continues_by_default(self):
        policy = B._policy_dict(B.StopPolicy())
        self.assertEqual(B.stop_reasons(summary(undetermined=[und(B.EVIDENCE_MISSING_STOP)] * 2), policy),
                         ([], ["undetermined:evidence_missing_stop:2"]))
        for category in (B.UNKNOWN_DIAGNOSTIC, B.CONTRACT_UNKNOWN, B.NO_PROGRESS, B.ACCEPTED_CONTENT_UNRECORDED, B.UNCLASSIFIED, "something_new"):
            self.assertEqual(B.stop_reasons(summary(undetermined=[und(category)]), policy)[0], [f"undetermined:{category}:1"], category)
        self.assertEqual(B.stop_reasons(summary(known_stop=2), policy), ([], ["known_stop:2"]))
        self.assertEqual(B.stop_reasons(summary(content={"suspect": 1}), policy)[0], ["suspect:1"])
        self.assertEqual(B.stop_reasons(summary(termination="api_contract_unknown"), policy)[0], ["termination:api_contract_unknown"])

    def test_evidence_missing_can_be_set_to_stop(self):
        policy = B._policy_dict(B.StopPolicy(on_undetermined={**B.StopPolicy().on_undetermined, B.EVIDENCE_MISSING_STOP: "stop"}))
        self.assertEqual(B.stop_reasons(summary(undetermined=[und(B.EVIDENCE_MISSING_STOP)]), policy)[0], ["undetermined:evidence_missing_stop:1"])
        with self.assertRaises(B.BatchRefused):
            B._policy_dict(B.StopPolicy(on_undetermined={"made_up": "continue"}))


class BatchPolicyTest(Base):
    def test_evidence_missing_continues_and_unknown_diagnostic_stops(self):
        a = FakeAdapter(script={"g001-uniform-stage-s1": summary(termination="halted_known", term_verdict="undetermined",
                                                                  undetermined=[und(B.EVIDENCE_MISSING_STOP, "termination")]),
                                "g002-uniform-stage-s2": summary(submits={"expected": 2, "undetermined": 1}, undetermined=[und(B.UNKNOWN_DIAGNOSTIC)])})
        self.plan(a, seeds=(1, 2, 3))
        r = self.run_(a)
        self.assertEqual(r.status, "stopped_policy")
        self.assertEqual(r.stop["reasons"], ["undetermined:unknown_diagnostic:1"])
        self.assertEqual(a.calls, ["g001-uniform-stage-s1", "g002-uniform-stage-s2"])
        # 停止の確かめは、集計・再実行で勝手に外れない（--acknowledge-stop を渡したときだけ）
        B.aggregate(self.tmp, "b", adapter=a)
        for _ in range(2):
            with self.assertRaises(B.BatchRefused):
                self.run_(a)
        self.assertNotIn("stop_acknowledged", [e["event"] for e in self.ledger()])
        self.assertEqual(len(a.calls), 2)
        agg = json.loads((self.bdir() / "aggregate.json").read_text(encoding="utf-8"))
        self.assertEqual(agg["judge"]["undetermined_by_category"]["evidence_missing_stop"]["count"], 1)
        self.assertEqual(agg["judge"]["undetermined_by_category"]["unknown_diagnostic"]["count"], 1)
        self.assertEqual(self.run_(a, acknowledge=["g002-uniform-stage-s2"]).status, "completed")


class EvidenceTest(Base):
    def test_game_evidence_is_fixed_and_aggregate_does_not_change_it(self):
        a = FakeAdapter(script={"g002-uniform-stage-s2": RuntimeError("bug")})
        self.plan(a, seeds=(1, 2))
        self.run_(a)  # 1 局完了・1 局は未完了の attempt
        first = B.aggregate(self.tmp, "b", adapter=a)["verifier"]["evidence"]
        for _ in range(2):
            again = B.aggregate(self.tmp, "b", adapter=a)["verifier"]["evidence"]
        self.assertEqual(again["bytes"]["game_complete"], first["bytes"]["game_complete"])
        self.assertEqual(again["files"]["game_complete"], first["files"]["game_complete"])
        self.assertEqual(again["bytes"]["attempt_not_complete"], first["bytes"]["attempt_not_complete"])
        self.assertGreater(again["bytes"]["attempt_not_complete"], 0)
        self.assertGreater(again["bytes"]["derived"], 0)
        self.assertEqual(again["bytes"]["other"], 0)
        adir = self.bdir() / "games" / "g001-uniform-stage-s1" / "attempt-001"
        on_disk = sum(p.stat().st_size for p in adir.rglob("*") if p.is_file())
        self.assertEqual(first["bytes"]["game_complete"], on_disk)  # 対象は完了の attempt のディレクトリのファイル（表・COMPLETE.json を含む）


class RealRecordTest(unittest.TestCase):
    """本物の 1 局（上限 40 の操作）: runner が受理のあとの公開のログを記録しても、既存の方策の行動の指紋が変わらない（v2_repeat の ACTION_GOLDEN）。"""

    def test_action_fingerprint_kept(self):
        from tools.verification_ai import records as R

        from tests.test_verification_ai_v2_repeat import ACTION_GOLDEN

        result = V.run_game(V.Config(game_seed=12, policy_seed=12, host_seed=12, limits=V.Limits(operations=80, seconds=60)))
        digest = R.sequence_digest(R.action_sequence(result["trace"]), R.ACTION_FORMAT)
        self.assertEqual((digest["length"], digest["sha256"]), ACTION_GOLDEN["uniform-stage-s12"])


if __name__ == "__main__":
    unittest.main()
