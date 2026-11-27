"""検証用 AI の試験の方策 rules-v5 のテスト（docs/tr8-rules-v4-9022-guard-analysis.md 6 章・docs/tr8-rules-v5-damage-swap-guard-experiment.md）。

rules-v5 は rules-v4 に、同じ番の本人の［ダメージスワップ］の受理の回数（持ち主をまたいで合計）が 6 回に達したら、その番の残りで対象の候補を順位 7
（end_turn より後ろ）に置く規則を加える。ほかの操作の受理では回数を消さず、番が変われば消す。拒否・入力を作れない・送信の抑止は数えない。候補は消さず、
ほかに選べる操作がなければ順位 7 の中から選び、そのときの入力の制限と再送抑止は rules-v4・rules-v2 のまま。
小さな JSON の観測・候補・段で、5 回の受理のあと・6 回目の受理の直後・7 回目の選択の機会、持ち主が複数、別の操作を挟む、拒否・抑止、翌番、代わりの操作がない場合と、
ランナー・バッチの記録・rules-v4 の列の維持を確かめる。
"""

from __future__ import annotations

import unittest

from tools.verification_ai import batch as B
from tools.verification_ai import records as R
from tools.verification_ai import runner as V
from tools.verification_ai.policies import (DEFER_ALL, DEMOTED_RANK, RULES5_DISTRIBUTION, SWAP_CAP, RulePolicy, SwapCapRulePolicy, TransitionRulePolicy,
                                            action_key, loop_target)
from tests.test_verification_ai_rules_v3 import V2_GOLDEN, end_turn, retreat, swap, swaps_accepted, view
from tests.test_verification_ai_rules_v4 import S5, Driver, meaning, small

# 区間の中で一度も戻らない観測の並び（自分のバトル場・ベンチ 2 匹のダメージ）。W[k] は k 回目の受理のあと
W = [view(d) for d in ((60, 0, 0), (50, 10, 0), (40, 20, 0), (30, 30, 0), (30, 20, 10), (30, 10, 20), (30, 0, 30), (20, 10, 30), (10, 20, 30))]
MOVES = [(1, 2), (1, 2), (1, 2), (2, 3), (2, 3), (2, 3), (1, 2), (1, 2)]
PAIRS = {1: [2, 3], 2: [1, 3], 3: [1, 2]}


def walk(policy, n, cand=None, *, start=0):
    """W[start] から n 回、戻らない［ダメージスワップ］を受理する（各受理のあとに観測を見る）。"""
    d = Driver(policy)
    d.see(W[start])
    for k in range(n):
        c = cand(k) if callable(cand) else (cand or swap())
        d.move(c, PAIRS, MOVES[start + k], W[start + k + 1])
    return d


class CapTest(unittest.TestCase):
    def test_after_five_six_and_the_seventh_choice(self):
        p = SwapCapRulePolicy("s")
        self.assertEqual((SWAP_CAP, p.cap), (6, 6))
        d = walk(p, 5)
        self.assertEqual(d.infos[-1]["swap_count"], {"accepted_this_turn": 5, "cap": 6, "capped": False})
        self.assertEqual(p.choose("candidate", [end_turn(), swap()], {}), (1, "rule5:priority5:use_power"))  # 5 回の受理のあと: 順位 5 のまま
        self.assertNotIn("detection", "".join(str(i) for i in d.infos))
        d.move(swap(), PAIRS, MOVES[5], W[6])  # 6 回目の受理
        self.assertEqual(d.infos[-1]["swap_count"], {"accepted_this_turn": 6, "cap": 6, "capped": True})  # 受理の直後のエピソード
        self.assertEqual(p.loop_counts["swap_cap_reached"], 1)
        self.assertEqual(p.choose("candidate", [end_turn(), swap()], {}), (0, "rule5:priority6:end_turn:swap_cap1"))  # 7 回目の選択の機会: end_turn
        self.assertEqual(p.choose("candidate", [end_turn(), retreat(), swap()], {}), (1, "rule5:priority5:retreat:swap_cap1"))  # ほかの順位 5 は下げない
        self.assertEqual(p.loop_counts["choices_with_swap_cap"], 2)

    def test_holders_are_summed(self):
        a, b = swap("c3", holder=2), swap("c6", holder=3, card=76, zone="bench")
        p = SwapCapRulePolicy("s")
        walk(p, 6, lambda k: a if k % 2 == 0 else b)
        self.assertEqual(p.choose("candidate", [end_turn(), a, b], {}), (0, "rule5:priority6:end_turn:swap_cap2"))  # 両方の持ち主の候補が順位 7

    def test_other_operation_does_not_reset(self):
        p = SwapCapRulePolicy("s")
        d = walk(p, 3)
        d.accept(retreat())  # 別の操作の受理（区間は切れるが回数は残る）
        d.see(W[4])
        self.assertEqual(d.infos[-1]["swap_count"]["accepted_this_turn"], 3)
        for k in range(3):
            d.move(swap(), PAIRS, MOVES[4 + k], W[5 + k] if k < 2 else W[8])
        self.assertEqual(d.infos[-1]["swap_count"], {"accepted_this_turn": 6, "cap": 6, "capped": True})
        self.assertEqual(p.choose("candidate", [end_turn(), swap()], {})[0], 0)

    def test_rejections_and_suppressions_are_not_counted(self):
        p = SwapCapRulePolicy("s")
        d = walk(p, 5)
        for _ in range(4):  # 拒否・入力を作れない・送信の抑止のあとの選び直し（同じエピソード。受理がない）
            index, _ = p.choose("candidate", [end_turn(), swap()], {})
            d.inputs(swap(), PAIRS)
            p.review(swap(), action_key(0, swap(), [], meaning(1, 2)), (0, 5))
        p.observe_accepted((0, 5), action_key(0, end_turn(), [], []))  # rules-v2 の履歴だけの更新では数えない
        self.assertEqual(p._swaps, 5)
        self.assertEqual(p.choose("candidate", [end_turn(), swap()], {}), (1, "rule5:priority5:use_power"))

    def test_deferred_all_attempt_is_not_counted(self):
        p = SwapCapRulePolicy("s")
        d = Driver(p)
        d.see(W[0])
        d.move(swap(), {1: [2]}, (1, 2), W[1])
        d.move(swap(), {1: [2], 2: [1]}, (2, 1), W[0])  # 往復（rules-v4 の検出）
        self.assertEqual(d.inputs(swap(), {1: [2]}), DEFER_ALL)  # 組み立てない試み
        self.assertEqual(p._swaps, 2)

    def test_next_turn_resets(self):
        p = SwapCapRulePolicy("s")
        d = walk(p, 6)
        d.accept(end_turn(), others=4)
        d.see(view((60, 0, 0), turn=7))
        self.assertNotIn("swap_count", d.infos[-1])
        self.assertEqual(p.choose("candidate", [end_turn(), swap()], {}), (1, "rule5:priority5:use_power"))
        self.assertEqual(p.loop_counts["turn_resets_with_swap_cap"], 1)
        d.move(swap(), PAIRS, (1, 2), view((50, 10, 0), turn=7))
        self.assertEqual(p._swaps, 1)
        d.see(view((50, 10, 0), turn=7, segment=1))  # 区間が変わっても新しい番として消す
        self.assertEqual(p._swaps, 0)

    def test_only_rank_seven_left_keeps_restriction_and_review(self):
        p = SwapCapRulePolicy("s")
        d = walk(p, 6)
        self.assertEqual(p.choose("candidate", [swap("c9")], {}), (0, f"rule5:demoted:priority{DEMOTED_RANK}:use_power:swap_cap1"))  # 代わりがない: 選べる
        self.assertIsNone(d.inputs(swap("c9"), PAIRS))  # 後回しの鍵がなければ制限なし
        key = action_key(0, swap(), [], meaning(2, 3))
        p.observe_accepted((0, 5), key)
        p.observe_accepted((0, 5), key)
        self.assertEqual(p.review(swap(), key, (0, 5))["reason"], "repeat_suppressed")  # rules-v2 の再送抑止はそのまま

    def test_cap_does_not_lift_the_rules_v4_restriction(self):
        """6 手で最初の観測に戻る（rules-v4 の検出で最初の移動を後回し）: 戻った観測で回数は 6。候補は順位 7 で、選ばれたときの入力の制限は外さない。"""
        p = SwapCapRulePolicy("s")
        d = Driver(p)
        d.see(W[0])
        d.inputs(swap(), S5)  # W[0] の組の写し {1 -> 2, 1 -> 3}
        d.accept(swap(), (1, 2))
        d.see(W[1])
        for k in range(1, 5):
            d.move(swap(), PAIRS, MOVES[k], W[k + 1])
        d.move(swap(), PAIRS, (2, 1), W[0])
        self.assertEqual((d.infos[-1]["loop_detection"]["cycle_length"], d.infos[-1]["swap_count"]["accepted_this_turn"]), (6, 6))
        self.assertEqual(p.choose("candidate", [swap("c9")], {})[1], f"rule5:demoted:priority{DEMOTED_RANK}:use_power:swap_cap1")
        self.assertIsNone(p._lifted)
        self.assertEqual(d.inputs(swap("c9"), S5), frozenset({(1, 2)}))  # rules-v4 の制限のまま（回数では外さない）
        self.assertEqual(p.last_restriction["result"], "restricted")

    def test_before_the_cap_equals_rules_v4(self):
        for seed in ("a", "b", "c", "d"):
            p4, p5 = TransitionRulePolicy(seed), SwapCapRulePolicy(seed)
            d4, d5 = walk(p4, 5), walk(p5, 5)
            for items in ([end_turn(), retreat(), swap()], [end_turn(), swap(), swap("c6", holder=3, card=76)], [swap()]):
                i4, r4 = p4.choose("candidate", items, {})
                i5, r5 = p5.choose("candidate", items, {})
                self.assertEqual((i4, r4.replace("rule4:", "", 1)), (i5, r5.replace("rule5:", "", 1)))
            self.assertEqual(p4.draws, p5.draws)
            self.assertEqual([{k: v for k, v in i.items() if k != "swap_count"} for i in d5.infos], d4.infos)

    def test_cap_argument(self):
        with self.assertRaises(ValueError):
            SwapCapRulePolicy("s", cap=0)
        p = SwapCapRulePolicy("s", cap=2)
        walk(p, 2)
        self.assertEqual(p.choose("candidate", [end_turn(), swap()], {})[1], "rule5:priority6:end_turn:swap_cap1")


class RunnerAndBatchTest(unittest.TestCase):
    def test_runner_builds_rules_v5_and_records_it(self):
        result = V.run_game(small(policy="rules", rules_version=5, limits={"operations": 120}))
        p0 = result["policies"]["0"]
        self.assertEqual((p0["name"], p0["version"], p0["distribution"], p0["repeat_threshold"]), ("rules", 5, RULES5_DISTRIBUTION, 2))
        self.assertEqual((p0["loop"]["swap_cap"]["cap"], p0["loop"]["swap_cap"]["base"], p0["loop"]["extra_guard"]), (6, "rules-v4", None))
        reasons = [e["candidate_reason"] for e in result["trace"] if e.get("type") == "attempt" and e.get("actor") in (0, 1)]
        self.assertTrue(reasons and all(r.startswith("rule5:") for r in reasons))

    def test_make_policies_and_batch_records(self):
        made = V.make_policies(small(policy="rules", rules_version=5))
        for policy in (made[0], made[1]):
            self.assertIsInstance(policy, SwapCapRulePolicy)
        for version in (2, 3, 4):
            for policy in V.make_policies(small(policy="rules", rules_version=version)).values():
                self.assertFalse(isinstance(policy, SwapCapRulePolicy) or hasattr(policy, "swap_cap"))
        with self.assertRaises(ValueError):
            RulePolicy("s", version=5)
        self.assertEqual(B.MODES["rules-v5"], {"policy": "rules", "rules_version": 5, "repeat_threshold": 2})
        self.assertEqual(B.MODES["rules-v4"], {"policy": "rules", "rules_version": 4, "repeat_threshold": 2})
        adapter = B.EngineAdapter()
        v5 = adapter.policies_of(small(policy="rules", rules_version=5))
        v4 = adapter.policies_of(small(policy="rules", rules_version=4))
        self.assertEqual((v5["0"]["version"], v5["0"]["distribution"], v5["0"]["swap_cap"]["cap"], v5["0"]["transition_deferral"]["version"]),
                         (5, RULES5_DISTRIBUTION, 6, 1))
        self.assertNotIn("swap_cap", v4["0"])
        self.assertEqual(B.TOOL_VERSION, 20)  # 20: rules-v9（旧の期待は 19）。 19: rules-v8（旧の期待は 18）。 18: rules-v7（旧の期待は 17）。 17: rules-v6（旧の期待は 16）


class SequenceTest(unittest.TestCase):
    def test_rules_v5_equals_rules_v4_while_no_turn_reaches_the_cap(self):
        kw, _golden, _swaps = V2_GOLDEN["rules-v2-s13"]
        r4 = V.run_game(V.Config(policy="rules", rules_version=4, **kw))
        r5 = V.run_game(V.Config(policy="rules", rules_version=5, **kw))
        d4, d5 = (R.sequence_digest(R.action_sequence(r["trace"]), R.ACTION_FORMAT) for r in (r4, r5))
        self.assertEqual((d5["length"], d5["sha256"], swaps_accepted(r5)), (d4["length"], d4["sha256"], swaps_accepted(r4)))
        self.assertFalse(any(":swap_cap" in e["candidate_reason"] for e in r5["trace"] if e.get("type") == "attempt"))

    def test_l67u_9023_differs_only_after_a_capped_choice(self):
        """L67-U どうし seed 9023（操作 400）: rules-v5 の列は、最初に回数で下げた選択まで rules-v4 と同じ（下げなければ全体が同じ）。"""
        kw, _golden, _swaps = V2_GOLDEN["rules-v2-l67u-s9023"]
        r4 = V.run_game(V.Config(policy="rules", rules_version=4, **kw))
        r5 = V.run_game(V.Config(policy="rules", rules_version=5, **kw))
        a4, a5 = R.action_sequence(r4["trace"]), R.action_sequence(r5["trace"])
        t5 = [e for e in r5["trace"] if e.get("type") == "attempt"]
        capped = [i for i, e in enumerate(t5) if ":swap_cap" in e["candidate_reason"]]
        first = next((i for i, (x, y) in enumerate(zip(a4, a5)) if x != y), None)
        if not capped:
            self.assertEqual(a4, a5)
        else:
            self.assertTrue(first is None or first >= capped[0])
        self.assertEqual(r5["anomalies"], [])


if __name__ == "__main__":
    unittest.main()
