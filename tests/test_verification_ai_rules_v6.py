"""検証用 AI の試験の方策 rules-v6 のテスト（docs/tr8-energy-trans-loop-analysis.md 6 章・7 章・docs/tr8-energy-trans-loop-experiment.md）。

rules-v6 は rules-v5 に、同じ番の本人の［エナジートランス］の受理だけが続いた区間で本人の観測が以前の観測に戻ったとき、周期の各移動を
（操作前の本人の観測, 移動元, エネルギーのカード, 移動先）で記録し、その観測でだけ 3 段の入力（移動元 → エネルギー → 移動先）の選べるものから外す規則を加える。
持ち主は鍵に入れない。組み立てられる移動がすべて後回しなら候補を end_turn より後ろへ下げ、ほかに選べる操作がなければ制限を外す。［エナジートランス］には
回数による順位の変更を入れない。小さな JSON の観測・候補・段で、直後の逆・3 手以上の周期・持ち主 2 体・エネルギーか移動先だけが違う組・ほかの受理で区間が切れる・
全移動が後回し・組が取れない・選び直しで履歴が進まない・番の更新と、行動生成の 3 段の制限・ランナー・バッチの記録・rules-v5 の列の維持を確かめる。
"""

from __future__ import annotations

import unittest

from tools.verification_ai import actions as A
from tools.verification_ai import batch as B
from tools.verification_ai import records as R
from tools.verification_ai import runner as V
from tools.verification_ai.policies import (DEFER_ALL, DEMOTED_RANK, ENERGY_TRANS_NAMES, LOOP_POWER_NAMES, RULES6_DISTRIBUTION, SWAP_CAP, EnergyTransRulePolicy,
                                            RulePolicy, SwapCapRulePolicy, et_holder_of, et_target, loop_target, transfer_of)
from tests.test_verification_ai_rules_v3 import V2_GOLDEN, end_turn, retreat, small, swap, swaps_accepted
from tests.test_verification_ai_rules_v4 import S5, S5_AFTER
from tests.test_verification_ai_rules_v4 import Driver as Driver4
from tests.test_verification_ai_rules_v4 import A0 as SW0, A1 as SW1

OPT = {"eligible": True, "processability": "may_stop_later"}
DEEP = A.DEEP_PROCESSABILITY
POKEMON = (1, 2, 3)  # 本人の場のポケモンの番号（バトル場 1、ベンチ 2・3）


def et(cid="c4", holder=2, card=68):
    """［エナジートランス］の宣言の候補（持ち主は場のポケモンの番号）。"""
    return {"id": cid, "kind": "use_power", "processability": "may_stop_later", "input_disclosure": "confirmed", "reasons": ["continuation_not_evaluated"],
            "pokemon": {"card": card, "card_id": "PMCG1-011", "pokemon": holder, "zone": "bench"},
            "power": {"card": card, "card_id": "PMCG1-011", "index": 0, "name_ja": "エナジートランス"},
            "input_stages": [{"input": "choose_option", "stage": 1}, {"input": "choose_option", "stage": 2}, {"input": "choose_option", "stage": 3}]}


def view(place: dict[int, tuple] | None = None, turn=5, hand=3, segment=0):
    """本人の観測の応答。place は場のポケモンの番号 → ついたエネルギーのカードの番号（並びのまま）。"""
    place = place or {}
    mons = [{"pokemon_id": p, "energy": [{"card": c, "card_id": "PMCG1-097"} for c in place.get(p, ())]} for p in POKEMON]
    return {"contract": "kyuura-client-api", "format": 1, "ok": True, "type": "view", "viewer": 0,
            "status": {"segment": segment, "phase": "main", "status": "in_progress", "continuable": True, "halt": None, "waiting": [{"by": 0, "kind": "turn"}]},
            "observation": {"turn": turn, "current_player": 0, "decision": None, "phase": "main",
                            "players": [{"player": 0, "active": mons[0], "bench": mons[1:], "hand": {"count": hand}}, {"player": 1, "hand": {"count": 5}}]}}


def moves_of(place: dict[int, tuple]) -> set[tuple[int, int, int]]:
    """配置から、組み立てられる移動（ほかのポケモンへ 1 枚）。"""
    return {(s, e, t) for s, cards in place.items() for e in cards for t in POKEMON if t != s}


def stages3(moves) -> list[dict]:
    """［エナジートランス］の inputs の段（移動元 → options_by_choice のエネルギー → options_by_choice の移動先）。番号は応答ごとに振る。"""
    tree: dict[int, dict[int, list[int]]] = {}
    for s, e, t in sorted(moves):
        tree.setdefault(s, {}).setdefault(e, []).append(t)
    first, second, third, by2, by3, n = [], [], [], {}, {}, 0
    for s in sorted(tree):
        n += 1
        sid = f"o{n}"
        first.append({"id": sid, "pokemon": s, "zone": "bench", **OPT})
        by2[sid] = []
        for e in sorted(tree[s]):
            n += 1
            eid = f"o{n}"
            second.append({"id": eid, "after": sid, "card": e, "card_id": "PMCG1-097", **OPT})
            by2[sid].append({"option": eid, **OPT})
            by3[eid] = []
            for t in tree[s][e]:
                n += 1
                second_t = {"id": f"o{n}", "after": eid, "pokemon": t, "zone": "bench", **OPT}
                third.append(second_t)
                by3[eid].append({"option": f"o{n}", **OPT})
    base = {"input": "choose_option", "count": {"min": 1, "max": 1}, "order": "not_applicable"}
    return [{"stage": 1, "role": "source", "meaning": "pokemon", "options": first, **base},
            {"stage": 2, "role": "energy", "meaning": "card", "depends_on_stage": 1, "upstream_stages": [1], "options": second, "options_by_choice": by2, **base},
            {"stage": 3, "role": "target", "meaning": "pokemon", "depends_on_stage": 2, "upstream_stages": [1, 2], "options": third, "options_by_choice": by3,
             **base}]


def meaning3(s, e, t):
    return [{"stage": 1, "option": {"pokemon": s}}, {"stage": 2, "option": {"card": e}}, {"stage": 3, "option": {"pokemon": t}}]


def moved(place, move):
    s, e, t = move
    out = {p: tuple(c for c in cs if not (p == s and c == e)) for p, cs in place.items()}
    out[t] = tuple(out.get(t, ())) + (e,)
    return {p: cs for p, cs in out.items() if cs}


class Driver:
    """ランナーの代わりに、本人のエピソードの始めの観測・inputs の応答・本人の受理を方策に渡す（受理のたびに通し番号を 1 進める）。"""

    def __init__(self, policy, place):
        self.policy, self.position, self.infos, self.place = policy, 0, [], dict(place)

    def see(self, place=None, **kw):
        if place is not None:
            self.place = dict(place)
        self.policy.observe_view(view(self.place, **kw), self.position)
        self.infos.append(self.policy.begin_episode())
        return self.infos[-1]

    def inputs(self, cand, moves=None):
        st = stages3(moves_of(self.place) if moves is None else moves)
        self.policy.observe_inputs(cand, st, DEEP)
        return self.policy.input_restriction(cand, st, DEEP)

    def accept(self, cand, move=None, *, others=0):
        self.position += 1 + others
        self.policy.accepted_input(cand, meaning3(*move) if move else [], self.position - others)

    def move(self, cand, move, **kw):
        """inputs を取り、受理して、受理のあとの観測を見る。"""
        r = self.inputs(cand)
        self.accept(cand, move)
        self.see(moved(self.place, move), **kw)
        return r


P0 = {1: (5,)}  # エネルギーのカード 5 がバトル場（1）に 1 枚


def inverse(policy=None, cand=None, cand2=None):
    """直後の逆: 1 -> 2 -> 1（P0 に戻る）。"""
    p = policy or EnergyTransRulePolicy("s")
    d = Driver(p, P0)
    d.see()
    d.move(cand or et(), (1, 5, 2))
    d.move(cand2 or cand or et(), (2, 5, 1))
    return p, d


class KeyAndMovesTest(unittest.TestCase):
    def test_target_holder_and_transfer_refs(self):
        self.assertTrue(et_target(et()) and not loop_target(et()))
        self.assertTrue(loop_target(swap()) and not et_target(swap()))
        self.assertEqual((ENERGY_TRANS_NAMES, LOOP_POWER_NAMES), (("エナジートランス",), ("ダメージスワップ",)))  # ［ダメージスワップ］の対象は変えない
        self.assertEqual(transfer_of(meaning3(1, 5, 2)), (1, 5, 2))
        self.assertIsNone(transfer_of(meaning3(1, 5, 2)[:2]))
        self.assertIsNone(transfer_of([{"stage": 1, "option": {"pokemon": 1}}, {"stage": 2, "option": {"pokemon": 5}}, {"stage": 3, "option": {"pokemon": 2}}]))
        self.assertEqual(et_holder_of(et("c3", zone_holder := 2)), et_holder_of(et("c9", zone_holder)))  # 候補の番号は見分けに入れない
        self.assertNotEqual(et_holder_of(et(holder=2)), et_holder_of(et(holder=3)))
        self.assertIsNone(et_holder_of({**et(), "pokemon": {"card": 68}}))

    def test_transfer_moves_follow_dependencies(self):
        st = stages3({(1, 5, 2), (1, 5, 3), (1, 6, 3), (2, 7, 1)})
        self.assertEqual(A.transfer_moves(st, DEEP), frozenset({(1, 5, 2), (1, 5, 3), (1, 6, 3), (2, 7, 1)}))  # 段を独立に組み合わせない（1-6-2 を作らない）
        st[2]["options_by_choice"][st[1]["options"][0]["id"]][0]["eligible"] = False  # 1-5-2 の参照が範囲の外
        self.assertEqual(A.transfer_moves(st, DEEP), frozenset({(1, 5, 3), (1, 6, 3), (2, 7, 1)}))
        self.assertIsNone(A.transfer_moves(st[:2], DEEP))  # 形が違う
        self.assertIsNone(A.transfer_moves([{**s, "role": None} for s in st], DEEP))  # 役割が違う
        broken = stages3({(1, 5, 2)})
        del broken[1]["options"][0]["card"]
        self.assertIsNone(A.transfer_moves(broken, DEEP))  # 参照がない（照合できない）
        self.assertIsNone(A.transition_pairs(stages3({(1, 5, 2)}), DEEP))  # 2 段の組（rules-v4）は 3 段に当てはめない

    def test_build_choices_three_stage_restriction(self):
        st = stages3({(1, 5, 2), (1, 5, 3), (1, 6, 2), (3, 7, 1)})
        ctx = {"candidate": et()}
        for seed in range(20):
            p = EnergyTransRulePolicy(f"r{seed}")
            _c, picks, mean = A.build_choices(st, p, ctx, DEEP, restriction=frozenset({(1, 5, 2), (1, 6, 2), (3, 7, 1)}))
            self.assertEqual(transfer_of(mean), (1, 5, 3))
            self.assertEqual([(x["stage"], x["items"]) for x in picks], [(1, 1), (2, 1), (3, 1)])  # 段ごとに 1 回（同じ組を引き直さない）
        p1, p2 = EnergyTransRulePolicy("q"), EnergyTransRulePolicy("q")
        self.assertEqual(A.build_choices(st, p1, ctx, DEEP), A.build_choices(st, p2, ctx, DEEP, restriction=None))  # 与えないときは今までと同じ


class DetectionTest(unittest.TestCase):
    def test_immediate_inverse_defers_only_the_returned_moves(self):
        p, d = inverse()
        det = d.infos[-1]["et_detection"]
        self.assertEqual((det["returned_to"], det["cycle_length"], [x["move"] for x in det["newly_deferred"]]), (0, 2, [[1, 5, 2], [2, 5, 1]]))
        twin = SwapCapRulePolicy("s")
        twin.begin_episode()
        mine = p.choose("candidate", [end_turn(), retreat(), et()], {})
        self.assertEqual((mine[0], mine[1].replace("rule6:", "rule5:", 1)), twin.choose("candidate", [end_turn(), retreat(), et()], {}))  # 順位は 5 のまま
        self.assertEqual(d.inputs(et()), frozenset({(1, 5, 2)}))  # P0 では 1-5-2 だけを外す（1-5-3 は残る）
        self.assertEqual(p.last_restriction["result"], "restricted")
        d.accept(et(), (1, 5, 3))
        d.see(moved(d.place, (1, 5, 3)))
        self.assertNotIn("et_detection", d.infos[-1])  # 新しい配置（戻りでない）は検出しない

    def test_three_move_cycle(self):
        p = EnergyTransRulePolicy("s")
        d = Driver(p, P0)
        d.see()
        for m in ((1, 5, 2), (2, 5, 3)):
            d.move(et(), m)
            self.assertNotIn("et_detection", d.infos[-1])
        d.move(et(), (3, 5, 1))
        det = d.infos[-1]["et_detection"]
        self.assertEqual((det["cycle_length"], len(det["newly_deferred"])), (3, 3))
        self.assertEqual(d.inputs(et()), frozenset({(1, 5, 2)}))

    def test_two_holders_share_the_move_key(self):
        p, d = inverse(cand=et(holder=2), cand2=et("c5", holder=3))  # 2 体の持ち主で往復しても 1 つの区間
        self.assertEqual(d.infos[-1]["et_detection"]["cycle_length"], 2)
        for cand in (et(holder=2), et("c5", holder=3)):  # どちらの持ち主の通常の入力からも同じ移動を外す
            self.assertEqual(d.inputs(cand), frozenset({(1, 5, 2)}))

    def test_energy_or_target_differs(self):
        p, d = inverse()
        moves = {(1, 5, 2), (1, 5, 3), (1, 6, 2)}  # エネルギーだけ違う 1-6-2、移動先だけ違う 1-5-3
        d.place = {1: (5, 6)}
        d.see()  # 配置が違うので、観測は P0 と一致しない: 外さない
        self.assertIsNone(d.inputs(et(), moves))
        d.see({1: (5,)})  # P0 の観測（同じ番）: 同じ組だけを外す
        self.assertEqual(d.inputs(et(), moves), frozenset({(1, 5, 2)}))
        st = stages3(moves)
        for seed in range(12):
            _c, _p, mean = A.build_choices(st, EnergyTransRulePolicy(f"x{seed}"), {"candidate": et()}, DEEP, restriction=frozenset({(1, 5, 2)}))
            self.assertIn(transfer_of(mean), {(1, 5, 3), (1, 6, 2)})


class RunAndTurnTest(unittest.TestCase):
    def test_other_accept_cuts_the_run_but_keeps_deferred_moves(self):
        p = EnergyTransRulePolicy("s")
        d = Driver(p, P0)
        d.see()
        d.move(et(), (1, 5, 2))
        d.accept(retreat())  # にげる（ほかの受理）で区間が切れる
        d.see(moved(P0, (1, 5, 2)), hand=2)
        d.move(et(), (2, 5, 1))
        self.assertNotIn("et_detection", d.infos[-1])  # 区間をまたぐ戻りは検出しない
        q, e = inverse()
        e.accept(retreat())
        e.see(P0)  # 検出のあとにほかの受理: 記録は番の終わりまで残る
        self.assertEqual(e.inputs(et()), frozenset({(1, 5, 2)}))
        e.see(P0, turn=7)  # 番が変われば消す
        self.assertIsNone(e.inputs(et()))
        self.assertNotIn("et_deferred", e.infos[-1])

    def test_rejections_and_suppressions_do_not_advance(self):
        p = EnergyTransRulePolicy("s")
        d = Driver(p, P0)
        d.see()
        d.inputs(et())  # 入力を取ったが送らない（拒否・抑止・組み立て失敗と同じく受理しない）
        d.see()
        d.see()
        self.assertNotIn("et_detection", d.infos[-1])
        self.assertEqual(p._et_deferred, set())

    def test_opponent_accept_cuts_the_run(self):
        p = EnergyTransRulePolicy("s")
        d = Driver(p, P0)
        d.see()
        d.move(et(), (1, 5, 2))
        r = d.inputs(et())
        d.accept(et(), (2, 5, 1), others=1)  # 本人の受理のあとに相手の受理が 1 つ
        d.see(P0)
        self.assertIsNone(r)
        self.assertNotIn("et_detection", d.infos[-1])


class AllDeferredTest(unittest.TestCase):
    def test_all_moves_deferred_ranks_seven_and_other_moves_kept(self):
        p = EnergyTransRulePolicy("s")
        d = Driver(p, {1: (5,)})
        d.place = {1: (5,)}
        two = {(1, 5, 2)}  # P0 で組み立てられるのは 1-5-2 だけ（移動先が 1 つ）
        d.see()
        d.inputs(et(), two)
        d.accept(et(), (1, 5, 2))
        d.see(moved(P0, (1, 5, 2)))
        d.inputs(et(), {(2, 5, 1)})
        d.accept(et(), (2, 5, 1))
        d.see(P0)
        self.assertEqual(d.infos[-1]["et_detection"]["cycle_length"], 2)
        i, reason = p.choose("candidate", [end_turn(), et()], {})  # 写しの組がすべて後回し: 順位 7 → end_turn
        self.assertEqual((i, reason), (0, "rule6:priority6:end_turn:et_deferred_all1"))
        self.assertEqual(d.inputs(et(), two), DEFER_ALL)  # 新しい応答でも外さない組が 0
        i, reason = p.choose("candidate", [et()], {})  # ほかに操作がない: 下げた候補を選び、制限を外す
        self.assertEqual(reason, f"rule6:demoted:priority{DEMOTED_RANK}:use_power:et_deferred_all1:et_no_alternative")
        self.assertIsNone(d.inputs(et(), two))
        self.assertEqual(p.last_restriction["result"], "lifted_no_alternative")

    def test_unknown_moves_are_not_excluded(self):
        p, d = inverse()
        broken = stages3(moves_of(P0))
        del broken[2]["options"][0]["pokemon"]
        p.observe_inputs(et(), broken, DEEP)
        self.assertIsNone(p.input_restriction(et(), broken, DEEP))
        self.assertEqual(p.last_restriction["result"], "restriction_unavailable")
        q, e = inverse()
        self.assertEqual(q.choose("candidate", [end_turn(), et("c9", holder=3)], {})[1], "rule6:priority5:use_power")  # 組を取っていない持ち主は下げない

    def test_no_count_demotion_for_energy_trans(self):
        p = EnergyTransRulePolicy("s")
        cards = tuple(range(10, 10 + SWAP_CAP + 4))
        d = Driver(p, {1: cards})
        d.see()
        for c in cards:  # 戻らない移動を上限の数より多く受理する
            d.move(et(), (1, c, 2))
            self.assertNotIn("et_detection", d.infos[-1])
        self.assertEqual(p.choose("candidate", [end_turn(), et()], {})[1], "rule6:priority5:use_power")
        self.assertNotIn("swap_count", d.infos[-1])


class DamageSwapUnchangedTest(unittest.TestCase):
    def test_damage_swap_choices_equal_rules_v5(self):
        for seed in ("a", "b", "c"):
            p5, p6 = SwapCapRulePolicy(seed), EnergyTransRulePolicy(seed)
            for pol in (p5, p6):
                d = Driver4(pol)
                d.see(SW0)
                d.move(swap(), S5, (1, 2), SW1)
                d.move(swap(), S5_AFTER, (2, 1), SW0)
            self.assertEqual(Driver4(p5).inputs(swap(), S5), Driver4(p6).inputs(swap(), S5))
            for items in ([end_turn(), retreat(), swap()], [swap()], [end_turn(), swap(), et()]):
                i5, r5 = p5.choose("candidate", items, {})
                i6, r6 = p6.choose("candidate", items, {})
                self.assertEqual((i5, r5.replace("rule5:", "", 1)), (i6, r6.replace("rule6:", "", 1)))
            self.assertEqual(p5.draws, p6.draws)


class RunnerAndBatchTest(unittest.TestCase):
    def test_runner_builds_rules_v6_and_records_it(self):
        result = V.run_game(small(policy="rules", rules_version=6, limits={"operations": 120}))
        p0 = result["policies"]["0"]
        self.assertEqual((p0["name"], p0["version"], p0["distribution"], p0["repeat_threshold"]), ("rules", 6, RULES6_DISTRIBUTION, 2))
        self.assertEqual((p0["loop"]["swap_cap"]["cap"], p0["loop"]["energy_trans_deferral"]["powers"], p0["loop"]["energy_trans_deferral"]["count_demotion"]),
                         (6, ["エナジートランス"], None))
        reasons = [e["candidate_reason"] for e in result["trace"] if e.get("type") == "attempt" and e.get("actor") in (0, 1)]
        self.assertTrue(reasons and all(r.startswith("rule6:") for r in reasons))

    def test_make_policies_and_batch_records(self):
        made = V.make_policies(small(policy="rules", rules_version=6))
        for policy in (made[0], made[1]):
            self.assertIsInstance(policy, EnergyTransRulePolicy)
        for version in (2, 3, 4, 5):
            for policy in V.make_policies(small(policy="rules", rules_version=version)).values():
                self.assertFalse(isinstance(policy, EnergyTransRulePolicy) or hasattr(policy, "energy_trans_deferral"))
        with self.assertRaises(ValueError):
            RulePolicy("s", version=6)
        self.assertEqual(B.MODES["rules-v6"], {"policy": "rules", "rules_version": 6, "repeat_threshold": 2})
        self.assertEqual(B.MODES["rules-v5"], {"policy": "rules", "rules_version": 5, "repeat_threshold": 2})
        adapter = B.EngineAdapter()
        v6 = adapter.policies_of(small(policy="rules", rules_version=6))
        v5 = adapter.policies_of(small(policy="rules", rules_version=5))
        self.assertEqual((v6["0"]["version"], v6["0"]["distribution"], v6["0"]["swap_cap"]["cap"], v6["0"]["energy_trans_deferral"]["version"]),
                         (6, RULES6_DISTRIBUTION, 6, 1))
        self.assertNotIn("energy_trans_deferral", v5["0"])
        self.assertEqual(B.TOOL_VERSION, 18)  # 18: rules-v7（旧の期待は 17）


class SequenceTest(unittest.TestCase):
    def test_rules_v6_equals_rules_v5_without_energy_trans(self):
        """L67-U どうし seed 9023（［ダメージスワップ］の局。［エナジートランス］なし）: rules-v6 の列は rules-v5 と同じ。"""
        kw, _golden, _swaps = V2_GOLDEN["rules-v2-l67u-s9023"]
        r5 = V.run_game(V.Config(policy="rules", rules_version=5, **kw))
        r6 = V.run_game(V.Config(policy="rules", rules_version=6, **kw))
        d5, d6 = (R.sequence_digest(R.action_sequence(r["trace"]), R.ACTION_FORMAT) for r in (r5, r6))
        self.assertEqual((d6["length"], d6["sha256"], swaps_accepted(r6)), (d5["length"], d5["sha256"], swaps_accepted(r5)))
        self.assertTrue(swaps_accepted(r6) > 0)
        self.assertFalse(any(":et_" in e["candidate_reason"] or (e.get("input_restriction") or {}).get("rule") == "energy_trans"
                             for e in r6["trace"] if e.get("type") == "attempt"))
        self.assertEqual(r6["anomalies"], [])

    def test_s13_differs_only_after_an_energy_trans_deferral(self):
        """既定のデッキ（フシギバナを含む）seed 13: rules-v6 の列は、最初に［エナジートランス］の後回しが働いた試みまで rules-v5 と同じ。"""
        kw, _golden, _swaps = V2_GOLDEN["rules-v2-s13"]
        r5 = V.run_game(V.Config(policy="rules", rules_version=5, **kw))
        r6 = V.run_game(V.Config(policy="rules", rules_version=6, **kw))
        a5, a6 = R.action_sequence(r5["trace"]), R.action_sequence(r6["trace"])
        t6 = [e for e in r6["trace"] if e.get("type") == "attempt"]
        hit = [i for i, e in enumerate(t6) if ":et_" in e["candidate_reason"] or (e.get("input_restriction") or {}).get("rule") == "energy_trans"]
        self.assertTrue(hit)
        before = sum(1 for e in t6[:hit[0]] if (e.get("submit") or {}).get("outcome") == "accepted")
        first = next((i for i, (x, y) in enumerate(zip(a5, a6)) if x != y), None)
        self.assertTrue(first is None or first >= before)
        self.assertEqual(a5[:before], a6[:before])
        self.assertEqual(r6["anomalies"], [])


if __name__ == "__main__":
    unittest.main()
