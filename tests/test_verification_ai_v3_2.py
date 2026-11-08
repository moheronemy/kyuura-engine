"""検証用 AI の V3-2（カツラの固定の到達例・options_by_path・BoundaryPolicy・判定の規則 2）のテスト（docs/verification-ai-v3-2.md 7 章）。

小さな JSON の例と偽物で確かめ、固定の到達例の通しはメモリの中の対戦（証跡の局とは別）で確かめる。
"""

from __future__ import annotations

import random
import unittest
from unittest import mock

from kyuura_engine import diagnostics as D
from tools.verification_ai import actions as B
from tools.verification_ai import judge as J
from tools.verification_ai import negative as N
from tools.verification_ai import runner as V
from tools.verification_ai.policies import BoundaryPolicy, UniformPolicy
from tools.verification_ai.run_v3_2 import (
    BLAINE_DECK,
    BLAINE_SEED,
    DECK_SOURCE,
    AttachNegativeSession,
    FixedReach,
    FixedReachPolicy,
    attachment_check,
    path_report,
)


def opt(oid, **kw):
    return {"id": oid, "eligible": True, "processability": "may_stop_later", **kw}


def path_stages(refs_a, refs_b, third_options):
    return [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1", card=101), opt("o2", card=102)]},
            {"stage": 2, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o3", card=900)], "depends_on_stage": 1,
             "options_by_choice": {"o1": [{"option": "o3"}], "o2": [{"option": "o3"}]}},
            {"stage": 3, "input": "choose_option", "count": {"min": 0, "max": 1}, "decline": True, "path_stages": [1, 2], "options": third_options,
             "options_by_path": {"o1/o3": [{"option": o, "eligible": True, "processability": "may_stop_later"} for o in refs_a],
                                 "o2/o3": [{"option": o, "eligible": True, "processability": "may_stop_later"} for o in refs_b]}}]


class DeckTest(unittest.TestCase):
    def test_copy_matches_the_fixed_reach_example(self):
        from tests.test_legal_actions_u7_5g_energy2 import BLAINE_DECK as SOURCE
        from tests.test_legal_actions_u7_5g_energy2 import BLAINE_SEED as SOURCE_SEED

        self.assertEqual((list(BLAINE_DECK), BLAINE_SEED), (list(SOURCE), SOURCE_SEED))
        self.assertEqual(DECK_SOURCE["cards"], 60)


class PathMutationTest(unittest.TestCase):
    def test_other_path_option_single_condition(self):
        stages = path_stages(["o4"], ["o5"], [opt("o4", card=201), opt("o5", card=202)])
        mutated, change = N.mutate("path_mix_path", stages, ["o1", "o3", "o4"], random.Random("p"))
        self.assertEqual((mutated, change["key"]), (["o1", "o3", "o5"], "o1/o3"))
        self.assertTrue(N.single_difference(["o1", "o3", "o4"], mutated))

    def test_blaine_like_overlap_is_not_applicable(self):
        """カツラの形: 鍵 o1/o3 の参照は 2 枚目（o5。カード 102）だけ、鍵 o2/o3 は 1 枚目と同じカード（o4。カード 101）。o4 はこの鍵の参照にないが、上流で選んだカードと
        同じカードを 2 回選ぶことにもなる（条件が重なる）ので、別の経路の試験にしない。"""
        stages = path_stages(["o5"], ["o4"], [opt("o4", card=101), opt("o5", card=102)])
        self.assertEqual(N.mutate("path_mix_path", stages, ["o1", "o3", "o5"], random.Random("p")),
                         (None, {"not_applicable": "no_other_path_option_without_overlap"}))
        both = path_stages(["o4", "o5"], ["o4", "o5"], [opt("o4", card=201), opt("o5", card=202)])
        self.assertIsNone(N.mutate("path_mix_path", both, ["o1", "o3", "o4"], random.Random("p"))[0])  # 両方の経路で許される
        self.assertIsNone(N.mutate("path_mix_path", stages, ["o1", "o3"], random.Random("p"))[0])  # 3 段目を省いた入力

    def test_duplicate_replace(self):
        multi = [{"stage": 1, "input": "choose_option", "count": {"min": 0, "max": 3}, "options": [opt("o1"), opt("o2"), opt("o3")]}]
        mutated, change = N.mutate("duplicate_replace", multi, ["o1", "o2"], random.Random("d"))
        self.assertEqual(len(mutated), 2)
        self.assertEqual(len(set(mutated)), 1)
        self.assertTrue(N.single_difference(["o1", "o2"], mutated))
        stages = path_stages(["o5"], ["o4"], [opt("o4", card=101), opt("o5", card=102)])
        self.assertEqual(N.mutate("duplicate_replace", stages, ["o1", "o3", "o5"], random.Random("d"))[1],
                         {"not_applicable": "no_stage_with_two_choices"})  # 役割の違う段の番号を同じにしない


class InputProcessabilityTest(unittest.TestCase):
    def test_candidate_class_and_input_class_differ(self):
        stages = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1")]},
                  {"stage": 2, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o2", processability="supported")], "depends_on_stage": 1,
                   "options_by_choice": {"o1": [{"option": "o2", "eligible": True, "processability": "unverified"}]}}]
        got = B.input_processability(stages, ["o1", "o2"])
        self.assertEqual(got["class"], "unverified")  # 組の参照の区分（選べるものの区分 supported ではない）
        self.assertEqual([i["from"] for i in got["items"]], ["option", "reference"])
        stages3 = path_stages(["o4"], ["o5"], [opt("o4", card=1, processability="supported"), opt("o5", card=2)])
        self.assertEqual(B.input_processability(stages3, ["o1", "o3", "o4"])["items"][2]["from"], "reference")
        self.assertEqual(B.input_processability(stages3, ["o1", "o3"])["class"], "may_stop_later")


class BoundaryPolicyTest(unittest.TestCase):
    def cands(self):
        return [{"id": "c1", "kind": "end_turn", "processability": "may_stop_later"}, {"id": "c2", "kind": "play_basic", "processability": "supported"},
                {"id": "c3", "kind": "use_power", "processability": "unverified"}, {"id": "c4", "kind": "retreat", "processability": "may_stop_later"}]

    def test_class_then_candidate(self):
        policy = BoundaryPolicy("b")
        rng = random.Random("b")
        classes = ["may_stop_later", "supported", "unverified"]
        cls = classes[rng.randrange(3)]
        pool = [i for i, c in enumerate(self.cands()) if c["processability"] == cls]
        expected = pool[rng.randrange(len(pool))] if len(pool) > 1 else pool[0]
        index, reason = policy.choose("candidate", self.cands(), {})
        self.assertEqual((index, reason.split(":")[2]), (expected, cls))
        single = BoundaryPolicy("s")
        self.assertEqual(single.choose("candidate", [self.cands()[1]], {}), (0, "boundary:class:supported:1classes:1in_class"))
        self.assertEqual(single.draws, 0)  # 区分・候補が 1 つなら乱数を使わない
        self.assertEqual(BoundaryPolicy("u").choose("option", list(range(5)), {}), UniformPolicy("u").choose("option", list(range(5)), {}))

    def test_boundary_scope_keeps_unsendable_out(self):
        runner = V.Runner(V.Config(policy="boundary", profile="boundary"))
        cands = {"coverage": {"display_only_kinds": ["check_face_up_deck"], "residual": {"present": []}},
                 "candidates": [{"id": "c1", "kind": "end_turn", "processability": "may_stop_later", "input_disclosure": "no_input"},
                                {"id": "c2", "kind": "use_power", "processability": "unverified", "input_disclosure": "confirmed"},
                                {"id": "c3", "kind": "use_power", "processability": "not_implemented", "input_disclosure": "unconfirmed"},
                                {"id": "c4", "kind": "play_trainer", "processability": "unresolved_ruling", "input_disclosure": "confirmed"},
                                {"id": "c5", "kind": "check_face_up_deck", "processability": "unresolved_ruling", "input_disclosure": "confirmed"}]}
        chosen, scope, reasons = runner._scope(cands, {})
        self.assertEqual([c["id"] for c in chosen], ["c1", "c2"])
        self.assertEqual(reasons, {"c3": "input_withheld", "c4": "processability:unresolved_ruling", "c5": "display_only"})
        deep = V.Runner(V.Config())._scope(cands, {})[0]
        self.assertEqual([c["id"] for c in deep], ["c1"])  # deep は unverified を入れない（V0 のまま）


class JudgeRulesTest(unittest.TestCase):
    def rejected(self, category, code):
        return {"ok": True, "outcome": D.REJECTED, "verifier": {"category": category, "diagnostic_id": "X", "engine_code": code}}

    def test_known_stop_needs_catalog_and_path_reason(self):
        attack = {"kind": "use_attack", "processability": "may_stop_later", "reasons": ["continuation_not_evaluated", "preflight_not_evaluated"]}
        self.assertEqual(J.judge_normal(attack, [], self.rejected(D.RULING_UNRESOLVED, "UNRESOLVED_MULLIGAN_COMPENSATION"))[0], J.KNOWN_STOP)
        self.assertEqual(J.judge_normal({**attack, "reasons": []}, [], self.rejected(D.RULING_UNRESOLVED, "UNRESOLVED_MULLIGAN_COMPENSATION"))[0],
                         J.UNDETERMINED)  # 区分だけでは known_stop にしない
        self.assertEqual(J.judge_normal(attack, [], self.rejected(D.RULING_UNRESOLVED, "NO_SUCH_CODE"))[0], J.UNDETERMINED)  # コード表にない元のコード
        self.assertEqual(J.judge_normal(attack, [], self.rejected(D.UNSUPPORTED, "UNRESOLVED_MULLIGAN_COMPENSATION"))[0], J.SUSPECT)  # 分類の食い違い
        unverified = {"kind": "use_power", "processability": "unverified", "reasons": ["face_down_reveal_not_evaluated"]}
        self.assertEqual(J.judge_normal(unverified, [], self.rejected(D.RULING_UNRESOLVED, "UNRESOLVED_MULLIGAN_COMPENSATION"))[0], J.KNOWN_STOP)
        self.assertEqual(J.judge_normal(attack, [], {"ok": True, "outcome": "refused", "refusal": {"code": "CANDIDATE_INPUT_INVALID"}})[0], J.SUSPECT)
        self.assertEqual(J.judge_normal(attack, [], {"ok": True, "outcome": D.FAILED})[0], J.SUSPECT)
        self.assertEqual(J.JUDGE_RULES_VERSION, 2)


def reach_run(energy2, **patches):
    reach = FixedReach(energy2)
    session = AttachNegativeSession(BLAINE_SEED)
    config = V.Config(game_seed=BLAINE_SEED, policy_seed=BLAINE_SEED, host_seed=BLAINE_SEED, decklists=(BLAINE_DECK, BLAINE_DECK), run_id=f"t-{energy2}")
    runner = V.Runner(config, policy_factory=lambda seed, dist: FixedReachPolicy(seed, dist, reach), negative=session, until=reach.until)
    return runner, runner.run(), session


class FixedReachTest(unittest.TestCase):
    def test_one_and_two_cards(self):
        for energy2, attached in ((False, 1), (True, 2)):
            with self.subTest(energy2=energy2):
                runner, result, session = reach_run(energy2)
                self.assertEqual(result["termination"]["class"], V.SCRIPT_COMPLETE)
                check = attachment_check(runner, result)
                self.assertEqual((check["attached_by_observation"], check["energy2_in_command"], check["input_length"]), (attached, energy2, 2 + energy2))
                report = path_report(session.attach_stages, [])
                self.assertEqual((report["present"], report["path_stages"], report["count"]), (True, [1, 2], {"min": 0, "max": 1}))
                attach = [e for e in result["trace"] if e.get("type") == "attempt" and e["candidate"]["kind"] == "attach_energy"]
                self.assertEqual(sum(1 for e in attach if e.get("submit")), 1)  # 通常の送信は 1 回
                self.assertTrue(all(e["check"]["response"]["valid"] for e in attach if e.get("submit")))  # check のあとに送った
                verdicts = result["negative"]["verdicts"]
                self.assertTrue(verdicts and all(k.endswith(":expected") for k in verdicts), verdicts)
                self.assertEqual(result["negative"]["recovery_verdicts"], {"expected": 1})
                reasons = {e["candidate_reason"].split(":")[0] for e in result["trace"] if e.get("type") == "attempt"}
                self.assertEqual(reasons, {"fixed-reach"})  # 固定の到達の列の選び手が選んだ（方策ではない）

    def test_side_effect_stops(self):
        with mock.patch("tools.verification_ai.judge.compare", return_value=["checks.log_length"]):
            _runner, result, _session = reach_run(True)
        self.assertEqual(result["termination"]["class"], V.NEGATIVE_SIDE_EFFECT)


class SummarizeTest(unittest.TestCase):
    def test_run_writes_aggregate_from_saved_files(self):
        """入力のない候補の完成した入力の区分は no_input と書く（None のキーで集計の書き出しが止まらない）。集計は保存した局のファイルだけから作る。"""
        import json
        import tempfile
        from pathlib import Path

        from tools.verification_ai import run_v3_2

        with tempfile.TemporaryDirectory() as tmp:
            code = run_v3_2.run(Path(tmp), "test", [])
            self.assertIn(code, (0, 3))
            agg = json.loads((Path(tmp) / "verifier" / "runs" / "v3-2-blaine-s1-default" / "aggregate.json").read_text(encoding="utf-8"))
            boundary = next(r for r in agg["games"] if r["game"] == "boundary")["boundary"]
            self.assertNotIn("None", boundary["built_input_class"])
            self.assertEqual(run_v3_2.summarize(Path(tmp), "test", written_by="test"), code)


if __name__ == "__main__":
    unittest.main()
