"""検証用 AI の試験の方策 rules-v4 のテスト（docs/tr8-damage-swap-transition-policy-design.md 3 章〜6 章・docs/tr8-damage-swap-transition-policy-experiment.md）。

rules-v4 は rules-v2 に、rules-v3 と同じ検出で確認した［ダメージスワップ］の周期の各移動を（操作前の本人の観測, 持ち主, 移動元, 移動先）で記録し、
その観測でだけ入力の選べるものから外す規則を加える。組み立てられる組がすべて後回しなら候補を end_turn より後ろへ下げ、ほかに選べる操作がなければ制限を外す。
小さな JSON の観測・候補・段で、設計 6.1 節の対照（逆方向・3 手以上の周期・持ち主が複数・同じ移動で観測が違う・全組が後回し・ほかの操作がない・番の更新・
別の受理による区間の終了・選び直しで履歴が進まない・rules-v2／rules-v3 の列の維持）と、行動生成の制限・ランナー・バッチの記録を確かめる。
"""

from __future__ import annotations

import copy
import unittest

from tools.verification_ai import actions as A
from tools.verification_ai import batch as B
from tools.verification_ai import records as R
from tools.verification_ai import runner as V
from tools.verification_ai.policies import (DEFER_ALL, DEMOTED_RANK, RULES4_DISTRIBUTION, LoopRulePolicy, RulePolicy, TransitionRulePolicy, action_key,
                                            holder_of, loop_target, move_of)
from tests.test_verification_ai_rules_v3 import DECK, V2_GOLDEN, end_turn, other_power, retreat, swap, swaps_accepted, view

A0, A1, A2, A3 = view((30, 0, 0)), view((20, 10, 0)), view((20, 0, 10)), view((10, 10, 10))
MAIN = [end_turn(), retreat(), swap()]
OPT = {"eligible": True, "processability": "may_stop_later"}


def stages(pairs: dict[int, list[int]]) -> list[dict]:
    """［ダメージスワップ］の inputs の段（移動元 → options_by_choice の移動先）。番号は応答ごとに振る。"""
    first = [{"id": f"o{i + 1}", "pokemon": s, "zone": "active", **OPT} for i, s in enumerate(sorted(pairs))]
    second, by_choice, n = [], {}, len(first)
    for o in first:
        refs = []
        for t in pairs[o["pokemon"]]:
            n += 1
            second.append({"id": f"o{n}", "after": o["id"], "pokemon": t, "zone": "bench", **OPT})
            refs.append({"option": f"o{n}", **OPT})
        by_choice[o["id"]] = refs
    return [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "role": "source", "meaning": "pokemon", "order": "not_applicable",
             "options": first},
            {"stage": 2, "input": "choose_option", "count": {"min": 1, "max": 1}, "role": "target", "meaning": "pokemon", "order": "not_applicable",
             "depends_on_stage": 1, "upstream_stages": [1], "options": second, "options_by_choice": by_choice}]


def meaning(s, t):
    return [{"stage": 1, "option": {"pokemon": s, "zone": "active"}}, {"stage": 2, "option": {"pokemon": t, "zone": "bench"}}]


S5 = {1: [2, 3]}  # 往復の前: エビワラー（1）だけがダメージを持つ
S5_AFTER = {1: [2, 3], 2: [1, 3]}  # 1 -> 2 のあと
DEEP = A.DEEP_PROCESSABILITY


class Driver:
    """ランナーの代わりに、本人のエピソードの始めの観測・inputs の応答・本人の受理を方策に渡す（受理のたびに通し番号を 1 進める）。"""

    def __init__(self, policy):
        self.policy, self.position, self.infos = policy, 0, []

    def see(self, v):
        self.policy.observe_view(v, self.position)
        self.infos.append(self.policy.begin_episode())
        return self.infos[-1]

    def inputs(self, cand, pairs):
        st = stages(pairs)
        self.policy.observe_inputs(cand, st, DEEP)
        return self.policy.input_restriction(cand, st, DEEP)

    def accept(self, cand, move=None, *, others=0):
        self.position += 1 + others
        self.policy.accepted_input(cand, meaning(*move) if move else [], self.position - others)

    def move(self, cand, pairs, move, after):
        """inputs を取り、受理して、受理のあとの観測を見る。"""
        r = self.inputs(cand, pairs)
        self.accept(cand, move)
        self.see(after)
        return r


def loop12(policy=None, cand=None):
    """S5 の往復 1 -> 2 -> 1（A0 -> A1 -> A0）。"""
    p = policy or TransitionRulePolicy("s")
    d = Driver(p)
    c = cand or swap()
    d.see(A0)
    d.move(c, S5, (1, 2), A1)
    d.move(c, S5_AFTER, (2, 1), A0)
    return p, d


class KeyAndPairTest(unittest.TestCase):
    def test_move_and_holder_refs(self):
        self.assertEqual(move_of(meaning(1, 3)), (1, 3))
        self.assertIsNone(move_of([{"stage": 1, "option": {"pokemon": 1}}, {"stage": 2, "option": {"card": 9}}]))  # 番号が取れない
        self.assertIsNone(move_of([]))
        self.assertEqual(holder_of(swap("c3", zone="active")), holder_of(swap("c9", zone="bench")))  # 候補の番号・場所は鍵に入れない
        self.assertIsNone(holder_of({**swap(), "pokemon": {"card": 75}}))

    def test_transition_pairs_follow_options_by_choice(self):
        st = stages({1: [2], 4: [1, 2]})
        self.assertEqual(A.transition_pairs(st, DEEP), frozenset({(1, 2), (4, 1), (4, 2)}))  # 段を独立に組み合わせない（1 -> 1 などを作らない）
        st[1]["options_by_choice"]["o2"][0]["eligible"] = False  # 4 -> 1 の参照が範囲の外
        self.assertEqual(A.transition_pairs(st, DEEP), frozenset({(1, 2), (4, 2)}))
        self.assertIsNone(A.transition_pairs([st[0]], DEEP))  # 形が違う
        broken = stages({1: [2]})
        del broken[1]["options"][0]["pokemon"]
        self.assertIsNone(A.transition_pairs(broken, DEEP))  # 番号がない（照合できない）

    def test_build_choices_restriction_and_draws(self):
        st = stages({1: [2, 3], 2: [1]})
        ctx = {"candidate": swap()}
        for _ in range(20):
            p = TransitionRulePolicy("r")
            choices, picks, mean = A.build_choices(st, p, ctx, DEEP, restriction=frozenset({(1, 2), (2, 1)}))
            self.assertEqual(move_of(mean), (1, 3))
            self.assertEqual([(x["stage"], x["items"]) for x in picks], [(1, 1), (2, 1)])  # 段ごとに 1 回（乱数の回数は変えない）
            self.assertEqual(p.draws, 2)
        p1, p2 = TransitionRulePolicy("q"), TransitionRulePolicy("q")
        self.assertEqual(A.build_choices(st, p1, ctx, DEEP), A.build_choices(st, p2, ctx, DEEP, restriction=None))  # 与えないときは今までと同じ
        with self.assertRaises(A.ContractUnknown):
            A.build_choices([{"stage": 1, "input": "choose_value", "count": {"min": 1, "max": 1}, "range": {"min": 0, "max": 2}}], p1, ctx, DEEP,
                            restriction=frozenset())


class AcceptanceS5Test(unittest.TestCase):
    def test_s5_defers_only_the_returned_move(self):
        policy, d = loop12()
        det = d.infos[-1]["loop_detection"]
        self.assertEqual((det["returned_to"], det["cycle_length"], [x["move"] for x in det["newly_deferred"]]), (0, 2, [[1, 2], [2, 1]]))
        twin = RulePolicy("s", version=2)
        twin.begin_episode()
        mine = policy.choose("candidate", MAIN, {})
        self.assertEqual((mine[0], mine[1].replace("rule4:", "rule2:", 1)), twin.choose("candidate", MAIN, {}))  # 候補の順位は rules-v2 のまま（5）
        self.assertEqual(d.inputs(swap(), S5), frozenset({(1, 2)}))  # 戻った観測では 1 -> 2 だけを外す（2 -> 1 は A0 で組み立てられない）
        self.assertEqual(policy.last_restriction["result"], "restricted")
        d.accept(swap(), (1, 3))
        d.see(A2)
        self.assertNotIn("loop_detection", d.infos[-1])  # 1 -> 3 で新しい周期は検出しない


class ControlTest(unittest.TestCase):
    def test_reverse_direction(self):
        p = TransitionRulePolicy("s")
        d = Driver(p)
        d.see(A0)
        d.move(swap(), {2: [1, 3]}, (2, 1), A1)
        d.move(swap(), {1: [2, 3], 2: [1, 3]}, (1, 2), A0)
        self.assertEqual(d.inputs(swap(), {2: [1, 3]}), frozenset({(2, 1)}))  # A0 で後回しは 2 -> 1 だけ
        d.accept(swap(), (2, 3))
        d.see(A2)
        self.assertIsNone(d.inputs(swap(), {1: [2, 3], 2: [1, 3], 3: [1, 2]}))  # 1 -> 2 は A1 の鍵なので、A2 では外さない

    def test_cycle_of_three(self):
        p = TransitionRulePolicy("s")
        d = Driver(p)
        d.see(A0)
        d.move(swap(), S5, (1, 2), A1)
        d.move(swap(), S5_AFTER, (2, 3), A2)
        self.assertFalse(any("loop_detection" in i for i in d.infos))
        self.assertEqual(p._deferred, set())  # 途中の観測では後回しにしない
        d.move(swap(), {1: [2, 3], 3: [1, 2]}, (3, 1), A0)
        det = d.infos[-1]["loop_detection"]
        self.assertEqual((det["cycle_length"], [x["move"] for x in det["newly_deferred"]]), (3, [[1, 2], [2, 3], [3, 1]]))
        self.assertEqual({(k[2], k[3]) for k in p._deferred}, {(1, 2), (2, 3), (3, 1)})
        self.assertEqual(len({k[0] for k in p._deferred}), 3)  # それぞれの操作前の観測
        self.assertEqual(d.inputs(swap(), S5), frozenset({(1, 2)}))

    def test_two_holders(self):
        a, b = swap("c3", holder=2), swap("c6", holder=3, card=76, zone="bench")
        p, d = loop12(cand=a)
        self.assertEqual(d.inputs(a, S5), frozenset({(1, 2)}))
        self.assertIsNone(d.inputs(b, S5))  # 別の持ち主の同じ移動は後回しにしない（設計 U5 の扱い）
        self.assertEqual(p.choose("candidate", [end_turn(), a, b], {})[1], "rule4:priority5:use_power:tie2")

    def test_same_move_at_another_view(self):
        p, d = loop12()
        d.inputs(swap(), S5)
        d.accept(swap(), (1, 3))
        d.see(A2)
        self.assertIsNone(d.inputs(swap(), {1: [2, 3], 3: [1, 2]}))  # A2 では 1 -> 2 を選べる
        self.assertIsNone(p.last_restriction)

    def test_all_pairs_deferred(self):
        p = TransitionRulePolicy("s")
        d = Driver(p)
        d.see(A0)
        d.move(swap(), {1: [2]}, (1, 2), A1)
        d.move(swap(), {1: [2], 2: [1]}, (2, 1), A0)  # 9034 の型: A0 で組み立てられるのは 1 -> 2 だけ
        self.assertEqual(p.choose("candidate", MAIN, {}), (1, "rule4:priority5:retreat:deferred_all1"))
        self.assertEqual(p.choose("candidate", [end_turn(), swap()], {}), (0, "rule4:priority6:end_turn:deferred_all1"))  # 写しで決める（inputs を取らない）
        self.assertEqual(p.loop_counts["choices_with_deferred_all"], 2)

    def test_fresh_response_without_alternative_defers_in_the_episode(self):
        p, d = loop12()
        p._pairs = {k: frozenset({(1, 2), (1, 3)}) for k in p._pairs}  # 写しには 1 -> 3 もある
        self.assertEqual(d.inputs(swap(), {1: [2]}), DEFER_ALL)  # 新しい応答は 1 -> 2 だけ: 組み立てずに候補を下げる
        self.assertEqual(p.loop_counts["pairs_cache_mismatch"], 1)
        self.assertEqual(p.choose("candidate", [end_turn(), swap()], {})[1], "rule4:priority6:end_turn:deferred_all1")
        d.see(A0)  # 同じ観測の新しいエピソード（受理のない次の手番の始めの形）: エピソードの下げは消え、写しは新しい応答のまま
        self.assertEqual(p.choose("candidate", [end_turn(), swap()], {})[1], "rule4:priority6:end_turn:deferred_all1")

    def test_no_other_operation_lifts_the_restriction(self):
        p = TransitionRulePolicy("s")
        d = Driver(p)
        d.see(A0)
        d.move(swap(), {1: [2]}, (1, 2), A1)
        d.move(swap(), {1: [2], 2: [1]}, (2, 1), A0)
        index, reason = p.choose("candidate", [swap("c9")], {})
        self.assertEqual((index, reason), (0, f"rule4:demoted:priority{DEMOTED_RANK}:use_power:deferred_all1:no_alternative"))
        self.assertIsNone(d.inputs(swap("c9"), {1: [2]}))  # 後回しの組も選べる
        self.assertEqual(p.last_restriction["result"], "lifted_no_alternative")
        self.assertTrue(p.review(swap(), action_key(0, swap(), [], meaning(1, 2)), (0, 5))["send"])  # 入力単位の評価は rules-v2 のまま
        p.choose("candidate", [end_turn(), swap()], {})
        self.assertIsNone(p._lifted)  # 次の選択では外さない

    def test_turn_change_clears_keys_and_pairs(self):
        p, d = loop12()
        d.accept(end_turn(), others=3)
        d.see(view((30, 0, 0), turn=7))
        self.assertEqual((p._deferred, p._pairs), (set(), {}))
        self.assertNotIn("transition_deferred", d.infos[-1])
        self.assertIsNone(d.inputs(swap(), S5))
        self.assertEqual(p.loop_counts["turn_resets_with_deferral"], 1)

    def test_other_operation_cuts_the_run_and_keeps_keys(self):
        p, d = loop12()
        kept = set(p._deferred)
        d.accept(retreat())
        d.see(A3)  # ほかの操作の受理で区間を切る
        self.assertEqual(p._run["moves"], [])
        self.assertEqual(p._deferred, kept)  # 鍵は番の中で残る
        d.move(swap(), {1: [2, 3]}, (1, 3), A0)  # 同じ観測 A0 に戻る（切ったあとの区間には A0 がないので検出しない）
        self.assertNotIn("loop_detection", d.infos[-1])
        self.assertEqual(d.inputs(swap(), S5), frozenset({(1, 2)}))  # 残った鍵で A0 の 1 -> 2 を外す
        p2 = TransitionRulePolicy("s")
        d2 = Driver(p2)
        d2.see(A0)
        d2.move(swap(), S5, (1, 2), A1)
        d2.accept(swap(), (2, 1), others=1)  # 本人の受理のあとにほかの主体の受理
        d2.see(A0)
        self.assertNotIn("loop_detection", d2.infos[-1])
        d2.move(other_power(), S5, None, A1)
        d2.move(swap(), S5_AFTER, (2, 1), A0)
        self.assertNotIn("loop_detection", d2.infos[-1])

    def test_retries_do_not_advance_history(self):
        p, d = loop12()
        before = (copy.deepcopy(p._run), set(p._deferred), dict(p._pairs))
        for _ in range(5):  # 拒否・入力を作れない・送信の抑止のあとの選び直し（同じエピソード）
            index, _ = p.choose("candidate", MAIN, {})
            d.inputs(MAIN[index], S5)
            p.review(MAIN[index], action_key(0, MAIN[index], [], meaning(1, 3)), (0, 5))
        self.assertEqual((p._run, p._deferred, p._pairs), before)
        self.assertIsNone(p._pending)

    def test_missing_refs_are_not_recorded(self):
        p = TransitionRulePolicy("s")
        d = Driver(p)
        d.see(A0)
        d.inputs(swap(), S5)
        d.position += 1
        p.accepted_input(swap(), [{"stage": 1, "option": {"card": 1}}, {"stage": 2, "option": {"card": 2}}], d.position)
        d.see(A1)
        d.move(swap(), S5_AFTER, (2, 1), A0)
        self.assertEqual(d.infos[-1]["loop_detection"]["cycle_length"], 2)
        self.assertEqual((p.loop_counts["keys_missing_ref"], len(p._deferred)), (1, 1))  # 番号のない移動は後回しにしない
        self.assertIsNone(d.inputs(swap(), S5))

    def test_missing_view_disables_the_run(self):
        p = TransitionRulePolicy("s")
        d = Driver(p)
        d.see(A0)
        d.move(swap(), S5, (1, 2), {"ok": False, "error": {"code": "x"}})
        d.move(swap(), S5_AFTER, (2, 1), A0)
        self.assertEqual((p._deferred, p.loop_counts["runs_without_view"]), (set(), 1))


def small(**kw):
    limits = kw.pop("limits", {})
    return V.Config(game_seed=13, policy_seed=13, host_seed=13, limits=V.Limits(**{"operations": 300, "seconds": 60, **limits}), **kw)


# rules-v3 の行動の列（形式 action-meaning/v2）。基点 988bdc5（rules-v4 の前。rules-v3 のコードは 001210f と同じ）で取った値
# （証跡 vai-tr8v4-exp-run/out/golden_base_988bdc5.json）
V3_GOLDEN = {"rules-v3-s13": (387, "132cee3587b589021db03fca1e3ad7c0ac05b206588e7da1311b3fff0b27e772", 0),
             "rules-v3-l67u-s9023": (160, "0118115faae16bcd0706c427957aaeb040bfd53540b64cec857c0fff7f07980e", 11)}


class RunnerAndBatchTest(unittest.TestCase):
    def test_runner_builds_rules_v4_and_records_it(self):
        result = V.run_game(small(policy="rules", rules_version=4, limits={"operations": 120}))
        p0 = result["policies"]["0"]
        self.assertEqual((p0["name"], p0["version"], p0["distribution"], p0["repeat_threshold"]), ("rules", 4, RULES4_DISTRIBUTION, 2))
        self.assertEqual((p0["loop"]["powers"], p0["loop"]["extra_guard"]), (["ダメージスワップ"], None))
        reasons = [e["candidate_reason"] for e in result["trace"] if e.get("type") == "attempt" and e.get("actor") in (0, 1)]
        self.assertTrue(reasons and all(r.startswith("rule4:") for r in reasons))

    def test_only_acceptance_reaches_the_policy(self):
        refused = {"ok": True, "outcome": "refused", "refusal": {"code": "CANDIDATE_INPUT_INVALID"}, "result": None, "refetch_required": False}

        def wrap(actor, endpoint):
            class Faulty:
                def handle(self, request):
                    return dict(refused) if request["type"] == "submit" else endpoint.handle(request)
            return Faulty() if actor in (0, 1) else endpoint
        runner = V.Runner(small(policy="rules", rules_version=4), wrap_endpoint=wrap)
        result = runner.run()
        self.assertEqual(result["termination"]["class"], V.NO_PROGRESS)
        for p in (runner.policies[0], runner.policies[1]):
            self.assertIsNone(p._pending)
            self.assertTrue(p._run is None or (len(p._run["views"]), p._run["moves"]) == (1, []))
            self.assertEqual(p._deferred, set())

    def test_hooks_belong_to_rules_v4_only(self):
        hooks = ("observe_inputs", "input_restriction", "accepted_input")
        for version in (2, 3):
            for policy in V.make_policies(small(policy="rules", rules_version=version)).values():
                self.assertFalse(any(hasattr(policy, h) for h in hooks))
        made = V.make_policies(small(policy="rules", rules_version=4))
        for policy in (made[0], made[1]):  # 主体 0・1（ホストの係は均等の方策のまま）
            self.assertIsInstance(policy, TransitionRulePolicy)
            self.assertFalse(isinstance(policy, LoopRulePolicy) or hasattr(policy, "accepted_candidate") or hasattr(policy, "loop_demotion"))
        with self.assertRaises(ValueError):
            RulePolicy("s", version=4)

    def test_batch_mode_and_plan_records(self):
        self.assertEqual(B.MODES["rules-v4"], {"policy": "rules", "rules_version": 4, "repeat_threshold": 2})
        self.assertEqual((B.MODES["rules-v2"], B.MODES["rules-v3"]), ({"policy": "rules", "rules_version": 2, "repeat_threshold": 2},
                                                                      {"policy": "rules", "rules_version": 3, "repeat_threshold": 2}))
        adapter = B.EngineAdapter()
        v4 = adapter.policies_of(small(policy="rules", rules_version=4))
        v3 = adapter.policies_of(small(policy="rules", rules_version=3))
        self.assertEqual((v4["0"]["version"], v4["0"]["distribution"], v4["0"]["transition_deferral"]["version"]), (4, RULES4_DISTRIBUTION, 1))
        self.assertNotIn("loop_demotion", v4["0"])
        self.assertNotIn("transition_deferral", v3["0"])
        self.assertEqual(B.TOOL_VERSION, 20)  # 20: rules-v9（旧の期待は 19）。 19: rules-v8（旧の期待は 18）。 18: rules-v7（旧の期待は 17）。 17: rules-v6（旧の期待は 16）。 16: rules-v5（旧の期待は 15）


class SequenceTest(unittest.TestCase):
    def test_rules_v3_sequences_are_unchanged(self):
        for name, golden in (("s13", V3_GOLDEN["rules-v3-s13"]), ("l67u-s9023", V3_GOLDEN["rules-v3-l67u-s9023"])):
            with self.subTest(name):
                kw = V2_GOLDEN["rules-v2-s13" if name == "s13" else "rules-v2-l67u-s9023"][0]
                result = V.run_game(V.Config(policy="rules", rules_version=3, **kw))
                action = R.sequence_digest(R.action_sequence(result["trace"]), R.ACTION_FORMAT)
                self.assertEqual((action["length"], action["sha256"], swaps_accepted(result)), golden)

    def test_rules_v4_without_keys_equals_rules_v2(self):
        kw, golden, swaps = V2_GOLDEN["rules-v2-s13"]
        result = V.run_game(V.Config(policy="rules", rules_version=4, **kw))
        action = R.sequence_digest(R.action_sequence(result["trace"]), R.ACTION_FORMAT)
        self.assertEqual((action["length"], action["sha256"], swaps_accepted(result)), (*golden, swaps))

    def test_rules_v4_matches_rules_v2_until_the_first_detection(self):
        """L67-U どうし seed 9023（操作 400）: rules-v4 の列は最初の検出まで rules-v2 と同じで、最初に違う試みは後回しの鍵のある観測の［ダメージスワップ］。"""
        kw, _golden, swaps_v2 = V2_GOLDEN["rules-v2-l67u-s9023"]
        self.assertEqual(kw["decklists"], (DECK, DECK))
        r2 = V.run_game(V.Config(policy="rules", rules_version=2, **kw))
        r4 = V.run_game(V.Config(policy="rules", rules_version=4, **kw))
        a2, a4 = R.action_sequence(r2["trace"]), R.action_sequence(r4["trace"])
        t4 = [e for e in r4["trace"] if e.get("type") == "attempt"]
        first = next(i for i, (x, y) in enumerate(zip(a2, a4)) if x != y)
        detections = [e for e in r4["trace"] if e.get("type") == "episode" and "loop_detection" in e]
        self.assertTrue(detections)
        self.assertGreaterEqual(t4[first]["position"], detections[0]["loop_detection"]["position"])
        self.assertTrue(loop_target(t4[first]["candidate"]))
        self.assertEqual(t4[first].get("input_restriction", {}).get("result"), "restricted")
        self.assertFalse(any("input_restriction" in e for e in t4[:first]))
        self.assertLess(swaps_accepted(r4), swaps_v2)
        self.assertEqual(r4["anomalies"], [])


if __name__ == "__main__":
    unittest.main()
