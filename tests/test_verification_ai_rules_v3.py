"""検証用 AI の試験の方策 rules-v3 のテスト（docs/tr8-damage-swap-loop-experiment.md 2 章・3 章）。

rules-v3 は rules-v2 に、同じ番の［ダメージスワップ］だけが続いた受理の区間で本人の観測が以前の観測に戻ったとき、直近の一致から今回の受理までに使った
［ダメージスワップ］の候補を番の残りで end_turn より後ろへ下げる規則を加える。小さな JSON の観測と候補で、直後の逆操作・3 手以上の周期・能力の持ち主が複数・
観測の一部だけが一致する対照・番をまたぐ対照・代わりの手がない場合・戻していない移動のあとに「にげる」・ワザへ進めること（TR8 の C1 seed 9024 の番 23 の型）・
ほかの操作や主体の受理で区間を切ること・観測が取れない区間で下げないこと・ランナーが受理のときだけ履歴を進めること・rules-v2 の列が変わらないことを確かめる。
"""

from __future__ import annotations

import copy
import unittest

from tools.verification_ai import batch as B
from tools.verification_ai import records as R
from tools.verification_ai import runner as V
from tools.verification_ai.policies import (DEMOTED_RANK, RULES3_DISTRIBUTION, LoopRulePolicy, RulePolicy, action_key, loop_key, loop_target,
                                            player_seed, view_signature)


def swap(cid="c3", holder=2, zone="active", card=75):
    return {"id": cid, "kind": "use_power", "processability": "may_stop_later", "input_disclosure": "confirmed", "reasons": ["continuation_not_evaluated"],
            "pokemon": {"card": card, "card_id": "PMCG1-049", "pokemon": holder, "zone": zone},
            "power": {"card": card, "card_id": "PMCG1-049", "index": 0, "name_ja": "ダメージスワップ"},
            "input_stages": [{"input": "choose_option", "stage": 1}, {"input": "choose_option", "stage": 2}]}


def other_power(cid="c5", holder=4):
    return {"id": cid, "kind": "use_power", "processability": "may_stop_later", "input_disclosure": "confirmed", "reasons": ["x"],
            "pokemon": {"card": 40, "pokemon": holder, "zone": "bench"}, "power": {"card": 40, "index": 0, "name_ja": "エナジートランス"},
            "input_stages": [{"stage": 1}]}


def end_turn(cid="c1"):
    return {"id": cid, "kind": "end_turn", "processability": "may_stop_later", "input_disclosure": "no_input", "input_stages": []}


def retreat(cid="c2"):
    return {"id": cid, "kind": "retreat", "processability": "may_stop_later", "input_disclosure": "confirmed", "input_stages": [{"stage": 1}]}


def attack(cid="c4"):
    return {"id": cid, "kind": "use_attack", "processability": "may_stop_later", "input_disclosure": "no_input", "input_stages": []}


def view(damage=(0, 0, 0), turn=5, hand=3, status=None, decision=None, attached=(), segment=0):
    """本人の観測の応答（client_api の view の形の一部）。damage は自分のバトル場とベンチ 2 匹のダメージ。"""
    active = {"pokemon": 2, "damage": damage[0], "hp": 80, "special_conditions": list(status or []), "attached": list(attached)}
    bench = [{"pokemon": 7 + i, "damage": d, "hp": 60, "special_conditions": [], "attached": []} for i, d in enumerate(damage[1:])]
    return {"contract": "kyuura-client-api", "format": 1, "ok": True, "type": "view", "viewer": 0,
            "status": {"segment": segment, "phase": "main", "status": "in_progress", "continuable": True, "halt": None, "waiting": [{"by": 0, "kind": "turn"}]},
            "observation": {"turn": turn, "current_player": 0, "decision": decision, "phase": "main",
                            "players": [{"player": 0, "active": active, "bench": bench, "hand": {"count": hand}}, {"player": 1, "hand": {"count": 5}}]}}


A0, A1, A2, A3 = view((30, 0, 0)), view((20, 10, 0)), view((20, 0, 10)), view((10, 10, 10))
MAIN = [end_turn(), retreat(), swap()]


class Driver:
    """ランナーの代わりに、本人のエピソードの始めの観測と本人の受理を方策に渡す（受理のたびに通し番号を 1 進める）。"""

    def __init__(self, policy):
        self.policy, self.position = policy, 0
        self.infos = []

    def see(self, v):
        self.policy.observe_view(v, self.position)
        self.infos.append(self.policy.begin_episode())
        return self.infos[-1]

    def accept(self, cand, *, others=0):
        self.position += 1 + others  # others: 本人の受理のあとに続いたほかの主体の受理の数
        self.policy.accepted_candidate(cand, self.position - others)

    def path(self, steps):
        """(受理の候補, 受理のあとの観測) の並び。最初の観測を先に see しておく。"""
        for cand, after in steps:
            self.accept(cand)
            self.see(after)


def v3(seed="s"):
    return LoopRulePolicy(seed)


class KeyAndSignatureTest(unittest.TestCase):
    def test_loop_key_ignores_id_zone_and_inputs(self):
        self.assertEqual(loop_key(swap("c3", zone="active")), loop_key(swap("c9", zone="bench")))  # 候補の番号の振り直し・場所の移動
        self.assertNotEqual(loop_key(swap(holder=2)), loop_key(swap(holder=3, card=76)))  # 能力の持ち主が違う
        self.assertTrue(loop_target(swap()))
        self.assertFalse(loop_target(other_power()))
        self.assertFalse(loop_target(retreat()))

    def test_view_signature_keeps_content_and_drops_outside_ids(self):
        self.assertEqual(view_signature(A0), view_signature(copy.deepcopy(A0)))
        self.assertEqual(view_signature(A0), view_signature({**A0, "request_id": "r-17"}))  # 観測の外の識別子だけを除く
        for changed in (view((30, 0, 0), hand=4), view((30, 0, 0), status=["poisoned"]), view((30, 0, 0), decision={"kind": "x"}),
                        view((30, 0, 0), attached=[{"card": 9}]), view((30, 0, 0), turn=6)):
            self.assertNotEqual(view_signature(A0), view_signature(changed))  # ダメージ以外の観測も比べる
        self.assertIsNone(view_signature({"ok": False, "error": {"code": "x"}}))


class DetectionTest(unittest.TestCase):
    def test_immediate_reverse_demotes_until_turn_end(self):
        policy, twin = v3(), RulePolicy("s", version=2)
        d = Driver(policy)
        d.see(A0)
        twin.begin_episode()
        mine, theirs = policy.choose("candidate", MAIN, {}), twin.choose("candidate", MAIN, {})
        self.assertEqual((mine[0], mine[1].replace("rule3:", "rule2:", 1)), theirs)  # 戻る前は rules-v2 と同じ（同じ乱数・同じ理由）
        self.assertTrue(mine[1].endswith(":tie2"))
        d.path([(swap(), A1)])
        self.assertNotIn("loop_detection", d.infos[-1])
        d.path([(swap("c7"), A0)])  # 直後の逆操作で A0 に戻った
        det = d.infos[-1]["loop_detection"]
        self.assertEqual((det["returned_to"], det["cycle_length"], det["run_accepts"], len(det["newly_demoted"])), (0, 2, 2, 1))
        self.assertEqual(policy.choose("candidate", MAIN, {})[1], "rule3:priority5:retreat:loop_demoted1")  # 同順位から外れ、にげるだけが残る
        self.assertEqual(policy.choose("candidate", [end_turn(), swap("c8")], {}), (0, "rule3:priority6:end_turn:loop_demoted1"))
        d.path([(swap(), A1)])  # 別のエピソードでも番の残りは下げたまま（rules-v2 のエピソードごとの解除と別）
        self.assertEqual(d.infos[-1]["loop_demoted"], 1)
        self.assertEqual(policy.choose("candidate", [end_turn(), swap()], {})[1], "rule3:priority6:end_turn:loop_demoted1")

    def test_cycle_of_three_detected_only_on_return(self):
        policy = v3()
        d = Driver(policy)
        d.see(A0)
        d.path([(swap(), A1), (swap(), A2)])
        self.assertFalse(any("loop_detection" in i for i in d.infos))  # 新しい観測のあいだは下げない
        self.assertEqual(policy.choose("candidate", [end_turn(), swap()], {})[1], "rule3:priority5:use_power")
        d.path([(swap(), A0)])  # 3 手で A0 に戻った
        det = d.infos[-1]["loop_detection"]
        self.assertEqual((det["returned_to"], det["cycle_length"]), (0, 3))
        self.assertEqual(policy.choose("candidate", [end_turn(), swap()], {})[1], "rule3:priority6:end_turn:loop_demoted1")

    def test_latest_match_and_multiple_holders(self):
        policy = v3()
        a, b = swap("c3", holder=2), swap("c6", holder=3, card=76, zone="bench")
        d = Driver(policy)
        d.see(A0)
        d.path([(a, A1), (b, A2), (b, A1)])  # A1 に戻った: 直近の一致（A1）から今回までは b だけ
        self.assertEqual(d.infos[-1]["loop_detection"]["cycle_length"], 2)
        items = [end_turn(), a, swap("c9", holder=3, card=76, zone="active")]  # b の番号と場所が変わっても同じ持ち主
        self.assertEqual(policy.choose("candidate", items, {}), (1, "rule3:priority5:use_power:loop_demoted1"))
        d.path([(a, A0)])  # A0 に戻った: A0 からの区間には a と b
        self.assertEqual(policy.choose("candidate", items, {}), (0, "rule3:priority6:end_turn:loop_demoted2"))

    def test_partial_match_is_not_a_return(self):
        policy = v3()
        d = Driver(policy)
        d.see(A0)
        d.path([(swap(), A1), (swap(), view((30, 0, 0), hand=2))])  # ダメージは A0 と同じだが手札が違う
        self.assertFalse(any("loop_detection" in i for i in d.infos))
        d.path([(swap(), view((30, 0, 0), status=["asleep"]))])  # 特殊状態だけが違う
        self.assertFalse(any("loop_detection" in i for i in d.infos))
        self.assertEqual(policy.choose("candidate", [end_turn(), swap()], {})[1], "rule3:priority5:use_power")

    def test_turn_change_clears_run_and_demotion(self):
        policy = v3()
        d = Driver(policy)
        d.see(A0)
        d.path([(swap(), A1), (swap(), A0)])
        self.assertEqual(policy.choose("candidate", [end_turn(), swap()], {})[1], "rule3:priority6:end_turn:loop_demoted1")
        d.accept(end_turn(), others=3)  # 相手の番をはさんで、次の自分の番
        d.see(view((30, 0, 0), turn=7))
        self.assertNotIn("loop_demoted", d.infos[-1])
        self.assertEqual(policy.choose("candidate", [end_turn(), swap()], {})[1], "rule3:priority5:use_power")
        d.path([(swap(), view((20, 10, 0), turn=7))])  # 前の番の観測（A1）とは番が違うので一致しない
        self.assertEqual(policy.loop_counts["detections"], 1)
        self.assertEqual(policy.loop_counts["turn_resets_with_demotion"], 1)

    def test_no_alternative_keeps_demoted_candidate_selectable(self):
        policy = v3()
        d = Driver(policy)
        d.see(A0)
        d.path([(swap(), A1), (swap(), A0)])
        index, reason = policy.choose("candidate", [swap("c9")], {})  # 下げた候補しか組み立てられない
        self.assertEqual((index, reason), (0, f"rule3:demoted:priority{DEMOTED_RANK}:use_power:loop_demoted1"))
        key = action_key(0, swap(), [], [])
        self.assertTrue(policy.review(swap(), key, (0, 5))["send"])  # 入力単位の抑止は rules-v2 の評価のまま（閾値の前は送る）

    def test_other_operation_or_actor_cuts_the_run(self):
        policy = v3()
        d = Driver(policy)
        d.see(A0)
        d.path([(swap(), A1), (retreat(), A3)])  # ほかの操作の受理で区間を切る
        d.path([(swap(), A0), (swap(), A1)])  # A0・A1 は切る前の区間の観測なので一致にしない
        self.assertFalse(any("loop_detection" in i for i in d.infos))
        d.path([(swap(), A0)])  # 今の区間（A3 から）の中で A0 に戻った
        self.assertEqual(d.infos[-1]["loop_detection"]["returned_to"], 1)
        p2 = v3()
        d2 = Driver(p2)
        d2.see(A0)
        d2.path([(swap(), A1)])
        d2.accept(swap(), others=1)  # 本人の受理のあと、次の本人の観測の前にほかの主体の受理（決定の回答など）
        d2.see(A0)
        self.assertNotIn("loop_detection", d2.infos[-1])
        d2.path([(other_power(), A1), (swap(), A0)])  # 対象でない特殊能力も区間を切る
        self.assertNotIn("loop_detection", d2.infos[-1])

    def test_missing_view_disables_the_run(self):
        policy = v3()
        d = Driver(policy)
        d.see(A0)
        d.path([(swap(), {"ok": False, "error": {"code": "x"}}), (swap(), A0)])
        self.assertFalse(any("loop_detection" in i for i in d.infos))
        self.assertEqual(policy.loop_counts["runs_without_view"], 1)
        self.assertEqual(policy.choose("candidate", [end_turn(), swap()], {})[1], "rule3:priority5:use_power")

    def test_choice_retries_do_not_advance_history(self):
        policy = v3()
        d = Driver(policy)
        d.see(A0)
        d.path([(swap(), A1)])
        before = copy.deepcopy(policy._run)
        for _ in range(5):  # 拒否・入力を作れない・送信の抑止のあとの選び直し（同じエピソード）
            index, _ = policy.choose("candidate", MAIN, {})
            policy.review(MAIN[index], action_key(0, MAIN[index], [], []), (0, 5))
        self.assertEqual(policy._run, before)

    def test_net_move_then_retreat_then_attack(self):
        """TR8 の C1 seed 9024 の番 23 の型: 戻していないダメージの移動のあと、にげる → ワザ。rules-v2 と同じ選択（同じ乱数）のまま下げない。"""
        seed = player_seed(9024, 0)
        p3, p2 = LoopRulePolicy(seed), RulePolicy(seed, version=2)
        d = Driver(p3)
        d.see(view((30, 0, 0)))
        p2.begin_episode()
        picks = []
        for p in (p3, p2):
            picks.append([p.choose("candidate", MAIN, {})[0] for _ in range(6)])  # 同順位（にげる・［ダメージスワップ］）の引き方が同じ
        self.assertEqual(picks[0], picks[1])
        d.path([(swap(), view((20, 10, 0))), (retreat(), view((10, 20, 0), hand=3))])  # バトル場のダメージを 10 減らして、にげた
        self.assertFalse(any("loop_detection" in i for i in d.infos))
        self.assertEqual(p3.choose("candidate", [end_turn(), attack(), swap()], {}), (1, "rule3:priority4:use_attack"))


def small(**kw):
    limits = kw.pop("limits", {})
    return V.Config(game_seed=13, policy_seed=13, host_seed=13, limits=V.Limits(**{"operations": 300, "seconds": 60, **limits}), **kw)


class RunnerAndBatchTest(unittest.TestCase):
    def test_runner_builds_rules_v3_and_records_it(self):
        result = V.run_game(small(policy="rules", rules_version=3, limits={"operations": 120}))
        p0 = result["policies"]["0"]
        self.assertEqual((p0["name"], p0["version"], p0["distribution"], p0["repeat_threshold"]), ("rules", 3, RULES3_DISTRIBUTION, 2))
        self.assertEqual(p0["loop"]["powers"], ["ダメージスワップ"])
        reasons = [e["candidate_reason"] for e in result["trace"] if e.get("type") == "attempt" and e.get("actor") in (0, 1)]
        self.assertTrue(reasons and all(r.startswith("rule3:") for r in reasons))

    def test_only_acceptance_reaches_the_policy(self):
        refused = {"ok": True, "outcome": "refused", "refusal": {"code": "CANDIDATE_INPUT_INVALID"}, "result": None, "refetch_required": False}

        def wrap(actor, endpoint):
            class Faulty:
                def handle(self, request):
                    return dict(refused) if request["type"] == "submit" else endpoint.handle(request)
            return Faulty() if actor in (0, 1) else endpoint
        runner = V.Runner(small(policy="rules", rules_version=3), wrap_endpoint=wrap)
        result = runner.run()
        self.assertEqual(result["termination"]["class"], V.NO_PROGRESS)
        for p in (runner.policies[0], runner.policies[1]):
            self.assertIsNone(p._pending)  # 拒否では受理の履歴を進めない
            self.assertTrue(p._run is None or (len(p._run["views"]), p._run["keys"]) == (1, []))  # 観測はエピソードの始めの 1 つだけ
            self.assertEqual(dict(p.loop_counts), {})

    def test_rules_v2_objects_have_no_rules_v3_hooks(self):
        for policy in V.make_policies(small(policy="rules", rules_version=2)).values():
            self.assertFalse(hasattr(policy, "observe_view") or hasattr(policy, "accepted_candidate") or hasattr(policy, "loop_summary"))
        with self.assertRaises(ValueError):
            RulePolicy("s", version=3)  # rules-v3 は LoopRulePolicy だけ（RulePolicy の版を増やさない）

    def test_batch_mode_and_plan_records(self):
        self.assertEqual(B.MODES["rules-v3"], {"policy": "rules", "rules_version": 3, "repeat_threshold": 2})
        self.assertEqual(B.MODES["rules-v2"], {"policy": "rules", "rules_version": 2, "repeat_threshold": 2})  # 既存の方式は同じ
        adapter = B.EngineAdapter()
        v3 = adapter.policies_of(small(policy="rules", rules_version=3))
        v2 = adapter.policies_of(small(policy="rules", rules_version=2))
        self.assertEqual((v3["0"]["version"], v3["0"]["distribution"], v3["0"]["loop_demotion"]["version"]), (3, RULES3_DISTRIBUTION, 1))
        self.assertNotIn("loop_demotion", v2["0"])
        self.assertEqual(set(v2["0"]), {"name", "version", "distribution", "seed", "threshold", "demote_after"})


# rules-v2 の行動の列（形式 action-meaning/v2）と契約の値の列。基点 3fd20a8（rules-v3 の前）のコードで取った値（証跡 vai-tr8-swap-v3-run/out/v2_golden_base_3fd20a8.json）
L67U = [("PMCG1-052", 4), ("PMCG1-058", 4), ("PMCG1-043", 4), ("PMCG1-046", 3), ("PMCG1-049", 2), ("PMCG5-093", 4), ("PMCG1-074", 2), ("PMCG1-073", 2),
        ("PMCG1-071", 2), ("PMCG1-081", 2), ("PMCG1-079", 2), ("PMCG1-072", 2), ("PMCG1-102", 15), ("PMCG1-101", 12)]
DECK = [c for c, n in L67U for _ in range(n)]
V2_GOLDEN = {  # (Config, 行動の列の長さと sha256, 受理した［ダメージスワップ］の数)
    "rules-v2-s13": (dict(game_seed=13, policy_seed=13, host_seed=13, limits=V.Limits(operations=300, seconds=60)),
                     (387, "132cee3587b589021db03fca1e3ad7c0ac05b206588e7da1311b3fff0b27e772"), 0),
    "rules-v2-l67u-s9023": (dict(game_seed=9023, policy_seed=9023, host_seed=9023, decklists=(DECK, DECK), limits=V.Limits(operations=400, seconds=120)),
                            (597, "c83fde59d83cb2c5c0c7094f2e1f49aa7c83a221cca6e59bd580276ff94ec9ce"), 210),
}


def swaps_accepted(result):
    return sum(1 for e in result["trace"] if e.get("type") == "attempt" and (e.get("submit") or {}).get("outcome") == "accepted" and loop_target(e["candidate"]))


class RulesV2UnchangedTest(unittest.TestCase):
    def test_rules_v2_sequence_is_unchanged(self):
        for name, (kw, golden, swaps) in V2_GOLDEN.items():
            with self.subTest(name):
                result = V.run_game(V.Config(policy="rules", rules_version=2, **kw))
                action = R.sequence_digest(R.action_sequence(result["trace"]), R.ACTION_FORMAT)
                self.assertEqual((action["length"], action["sha256"], swaps_accepted(result)), (*golden, swaps))
                self.assertTrue(all(e["candidate_reason"].startswith(("rule2:", "uniform:")) for e in result["trace"] if e.get("type") == "attempt"))

    def test_rules_v3_matches_rules_v2_until_the_first_loop_demotion(self):
        """L67-U どうし seed 9023（操作 400）: rules-v3 の試みの列は最初の検出まで rules-v2 と同じで、最初に違う試みは下げた候補のある選択。"""
        kw, _golden, swaps_v2 = V2_GOLDEN["rules-v2-l67u-s9023"]
        r2 = V.run_game(V.Config(policy="rules", rules_version=2, **kw))
        r3 = V.run_game(V.Config(policy="rules", rules_version=3, **kw))
        a2, a3 = R.action_sequence(r2["trace"]), R.action_sequence(r3["trace"])
        t3 = [e for e in r3["trace"] if e.get("type") == "attempt"]
        first = next(i for i, (x, y) in enumerate(zip(a2, a3)) if x != y)
        detections = [e for e in r3["trace"] if e.get("type") == "episode" and "loop_detection" in e]
        self.assertTrue(detections)
        self.assertGreaterEqual(t3[first]["position"], detections[0]["loop_detection"]["position"])
        self.assertIn(":loop_demoted", t3[first]["candidate_reason"])
        self.assertFalse(any(":loop_demoted" in e["candidate_reason"] for e in t3[:first]))
        self.assertLess(swaps_accepted(r3), swaps_v2)


if __name__ == "__main__":
    unittest.main()
