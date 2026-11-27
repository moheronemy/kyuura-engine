"""検証用 AI の試験の方策 rules-v7 のテスト（docs/tr8-retreat-input-build-analysis.md 6 章・docs/tr8-retreat-reselection-experiment.md）。

rules-v7 は rules-v6 に、本人の「にげる」の入力の組み立てが total_units_unreachable で失敗したとき、その番の（支払い条件の鍵, 候補）を記録し、
同じ鍵・同じ候補のあいだは「にげる」を end_turn より後ろへ下げる規則を加える。鍵は本人の観測の応答から、本人のベンチのポケモンのエネルギーだけを除いたもの。
小さな JSON の観測・候補・段で、鍵の変化（ベンチの間の移動・バトル場へ移す・交代・特殊状態・スタジアム・相手・ベンチの個体・番）、記録の条件（別の理由・別の種類・
観測が取れない・単位が決まらない・段の形が違う）、順位 7 と :retreat_no_alternative、rules-v6 と同じ選び方、ランナー・バッチの記録、既存の列の維持を確かめる。
"""

from __future__ import annotations

import copy
import unittest

from tools.verification_ai import batch as B
from tools.verification_ai import records as R
from tools.verification_ai import runner as V
from tools.verification_ai.policies import (DEMOTED_RANK, RETREAT_DEFERRAL, RULES7_DISTRIBUTION, EnergyTransRulePolicy, RetreatDeferralRulePolicy, RulePolicy,
                                            retreat_failure_inputs, retreat_payment_key)
from tests.test_verification_ai_rules_v3 import V2_GOLDEN, end_turn, small
from tests.test_verification_ai_rules_v6 import et

G = {"card": 117, "card_id": "PMCG1-097"}  # 草エネルギー（1 個）


def mon(pid, card_id="PMCG1-011", energy=0, status=(), trainers=(), units_determined=True):
    cards = [{**G, "card": 100 + pid * 10 + i} for i in range(energy)]
    return {"pokemon_id": pid, "card_id": card_id, "energy": cards, "energy_units": [["grass"] for _ in cards], "energy_units_determined": units_determined,
            "special_conditions": list(status), "trainers": list(trainers), "markers": [], "persistent_effects": [], "powers": [], "evolution_stack": []}


def view(active=1, bench=(0, 0), turn=24, stadium=None, opp_active="PMCG1-030", bench_ids=("PMCG1-007", "PMCG1-008"), status=(), units_determined=True, ok=True,
         segment=0, active_id="PMCG1-011"):
    """本人（プレイヤー 1）の観測。active・bench は付いた草エネルギーの枚数。"""
    me = {"player": 1, "active": mon(1, active_id, active, status, units_determined=units_determined),
          "bench": [mon(2 + i, cid, n) for i, (cid, n) in enumerate(zip(bench_ids, bench))], "hand": {"count": 3}}
    opp = {"player": 0, "active": mon(20, opp_active, 4), "bench": [mon(21, "PMCG1-058", 2)], "hand": {"count": 3}}
    return {"contract": "kyuura-client-api", "format": 1, "ok": ok, "type": "view", "viewer": 1,
            "status": {"segment": segment, "phase": "main", "status": "in_progress", "continuable": True, "halt": None, "waiting": [{"by": 1, "kind": "turn_action"}]},
            "observation": {"turn": turn, "current_player": 1, "viewer": 1, "phase": "main", "stadium": stadium, "trainer_effects": [], "players": [opp, me]}}


def retreat(cid="c2"):
    return {"id": cid, "kind": "retreat", "processability": "may_stop_later", "input_disclosure": "confirmed", "reasons": ["reactions_not_evaluated"],
            "input_stages": [{"input": "choose_option", "stage": 1}, {"input": "choose_option", "stage": 2}]}


def stages(units=1, cost=2):
    """にげるの inputs の段（入れ替える控え → トラッシュするエネルギー）。"""
    return [{"stage": 1, "role": "new_active", "meaning": "pokemon", "count": {"min": 1, "max": 1}, "options": [{"id": "o1", "pokemon": 3}, {"id": "o2", "pokemon": 9}]},
            {"stage": 2, "role": "discard", "meaning": "card", "count": {"min": 0, "max": units}, "total_units": {"min": cost, "max": cost},
             "options": [{"id": f"o{3 + i}", "card": 117 + i, "units": 1} for i in range(units)]}]


class Driver:
    def __init__(self, policy=None):
        self.policy, self.position, self.infos = policy or RetreatDeferralRulePolicy("s"), 0, []

    def see(self, v):
        self.policy.observe_view(v, self.position)
        self.infos.append(self.policy.begin_episode())
        return self.infos[-1]

    def fail(self, cand=None, st=None, reason="total_units_unreachable"):
        return self.policy.retreat_build_failed(cand or retreat(), stages() if st is None else st, reason, 2)

    def accept(self, cand=None, meaning=()):
        self.position += 1
        self.policy.accepted_input(cand or et(), list(meaning), self.position)

    def choose(self, items=None):
        return self.policy.choose("candidate", items or [end_turn(), retreat(), et()], {})


class KeyTest(unittest.TestCase):
    def test_bench_only_energy_keeps_the_key(self):
        k = retreat_payment_key(view(active=1, bench=(1, 0)))[0]
        self.assertIsNotNone(k)
        self.assertEqual(k, retreat_payment_key(view(active=1, bench=(0, 1)))[0])  # ベンチの間の移動
        self.assertEqual(k, retreat_payment_key({**view(active=1, bench=(1, 0)), "request_id": "x"})[0])  # 観測の外の識別子

    def test_payment_relevant_changes_change_the_key(self):
        k = retreat_payment_key(view(active=1, bench=(1, 0)))[0]
        for changed in (view(active=2, bench=(0, 0)),  # バトル場へ移す
                        view(active=1, bench=(1, 0), active_id="PMCG1-007"),  # バトル場の個体
                        view(active=1, bench=(1, 0), status=("asleep",)),  # 特殊状態
                        view(active=1, bench=(1, 0), stadium={"card_id": "PMCG5-095"}),  # スタジアム
                        view(active=1, bench=(1, 0), opp_active="PMCG4-007"),  # 相手のバトル場
                        view(active=1, bench=(1, 0), bench_ids=("PMCG2-040", "PMCG1-008")),  # ベンチの個体（にげるサポートなど）
                        view(active=1, bench=(1, 0), turn=26)):  # 番
            self.assertNotEqual(k, retreat_payment_key(changed)[0])
        v = view(active=1, bench=(1, 0))
        v["observation"]["players"][1]["active"]["trainers"] = [{"card_id": "neo3-055"}]  # バトル場についたトレーナー
        self.assertNotEqual(k, retreat_payment_key(v)[0])

    def test_key_unavailable(self):
        self.assertEqual(retreat_payment_key(view(ok=False)), (None, "view_unavailable"))
        self.assertEqual(retreat_payment_key(view(units_determined=False)), (None, "active_energy_units_undetermined"))
        v = view()
        v["observation"]["players"][1]["active"] = None
        self.assertEqual(retreat_payment_key(v), (None, "own_active_missing"))
        v = view()
        v["observation"]["viewer"] = 5
        self.assertEqual(retreat_payment_key(v), (None, "own_player_unknown"))
        original = view(active=1, bench=(1, 0))
        snapshot = copy.deepcopy(original)
        retreat_payment_key(original)
        self.assertEqual(original, snapshot)  # 観測を書き換えない

    def test_failure_inputs(self):
        self.assertEqual(retreat_failure_inputs(stages(1, 2)), {"total_units": [2, 2], "count": [0, 1], "option_units": [1], "new_active_options": 2})
        self.assertIsNone(retreat_failure_inputs([stages()[0]]))


class DeferralTest(unittest.TestCase):
    def test_same_condition_defers_and_bench_move_keeps_it(self):
        d = Driver()
        d.see(view(active=1, bench=(1, 0)))
        self.assertEqual(d.choose()[1].split(":")[0], "rule7")
        rec = d.fail()
        self.assertEqual((rec["result"], rec["total_units"], rec["option_units"]), ("recorded", [2, 2], [1]))
        d.accept()  # ベンチの間の［エナジートランス］
        info = d.see(view(active=1, bench=(0, 1)))
        self.assertEqual(info["retreat_deferred"]["same_key_recorded"], True)
        i, reason = d.choose()
        self.assertEqual((i, reason), (2, "rule7:priority5:use_power:retreat_deferred1"))  # 同順位の抽選をしない
        self.assertEqual(d.choose([end_turn(), retreat()]), (0, "rule7:priority6:end_turn:retreat_deferred1"))

    def test_energy_onto_active_reenables(self):
        d = Driver()
        d.see(view(active=1, bench=(1, 0)))
        d.fail()
        d.accept()
        d.see(view(active=2, bench=(0, 0)))  # バトル場へ移した
        self.assertNotIn("retreat_deferred", d.choose()[1])
        self.assertEqual(d.policy.loop_counts["retreat_choices_reenabled"], 1)
        d.accept()
        d.see(view(active=1, bench=(1, 0)))  # 前の失敗と同じ条件に戻った: 再び下げる
        self.assertIn(":retreat_deferred1", d.choose()[1])

    def test_switch_status_stadium_target_and_turn_reenable(self):
        for changed in (view(active=1, bench=(1, 0), active_id="PMCG1-007"), view(active=1, bench=(1, 0), status=("confused",)),
                        view(active=1, bench=(1, 0), stadium={"card_id": "PMCG5-095"}), view(active=1, bench=(1, 0), bench_ids=("PMCG1-007", "PMCG2-040")),
                        view(active=1, bench=(1, 0), turn=26)):
            d = Driver()
            d.see(view(active=1, bench=(1, 0)))
            d.fail()
            d.accept()
            d.see(changed)
            self.assertNotIn("retreat_deferred", d.choose()[1])
        d = Driver()
        d.see(view(active=1, bench=(1, 0)))
        d.fail()
        d.see(view(active=1, bench=(1, 0), turn=26))
        d.see(view(active=1, bench=(1, 0), turn=26))
        self.assertEqual(d.policy._rt_deferred, {})  # 番が変われば消す（同じ配置に戻っても下げない）
        self.assertEqual(d.policy.loop_counts["retreat_turn_resets_with_deferral"], 1)

    def test_not_recorded_cases(self):
        d = Driver()
        d.see(view(active=1, bench=(1, 0)))
        self.assertEqual(d.fail(reason="withheld")["result"], "not_recorded:other_reason")
        self.assertIsNone(d.fail(cand=et()))  # にげるでない候補
        self.assertEqual(d.fail(st=[stages()[0]]), {"result": "not_applicable", "why": "inputs_unrecognized"})
        self.assertNotIn("retreat_deferred", d.choose()[1])
        e = Driver()
        e.see(view(active=1, bench=(1, 0), units_determined=False))
        self.assertEqual(e.fail(), {"result": "not_applicable", "why": "active_energy_units_undetermined"})
        self.assertEqual(e.policy._rt_deferred, {})
        self.assertEqual(e.policy.loop_counts["retreat_not_applicable:active_energy_units_undetermined"], 1)
        f = Driver()
        f.see(view(active=1, bench=(1, 0)))
        f.fail()
        f.see(view(ok=False))  # 観測が取れない: 一致を確かめられないので下げない
        self.assertNotIn("retreat_deferred", f.choose()[1])
        self.assertEqual(f.policy.loop_counts["retreat_choices_key_unavailable"], 1)

    def test_only_rank_seven_remains(self):
        d = Driver()
        d.see(view(active=1, bench=(1, 0)))
        d.fail()
        d.see(view(active=1, bench=(0, 1)))
        self.assertEqual(d.choose([retreat()]), (0, f"rule7:demoted:priority{DEMOTED_RANK}:retreat:retreat_deferred1:retreat_no_alternative"))
        self.assertEqual(d.fail()["result"], "already_recorded")

    def test_other_candidate_identity_is_not_deferred(self):
        d = Driver()
        d.see(view(active=1, bench=(1, 0)))
        d.fail()
        other = {**retreat(), "processability": "supported"}  # 候補の中身が違う（評価の値は除く）
        self.assertIn(":retreat_deferred1", d.choose([end_turn(), {**retreat("c7")}, et()])[1])  # 番号だけ違う
        self.assertIn(":retreat_deferred1", d.choose([end_turn(), other, et()])[1])  # processability は評価の値で比べない
        changed = {**retreat(), "pokemon": {"pokemon": 3}}  # 評価の値の外の中身が違う候補
        self.assertNotIn("retreat_deferred", d.choose([end_turn(), changed, et()])[1])


class SameAsRulesV6Test(unittest.TestCase):
    def test_choices_equal_rules_v6_without_retreat_failures(self):
        for seed in ("a", "b", "c"):
            p6, p7 = EnergyTransRulePolicy(seed), RetreatDeferralRulePolicy(seed)
            for p in (p6, p7):
                p.observe_view(view(), 0)
                p.begin_episode()
            for items in ([end_turn(), retreat(), et()], [retreat(), et()], [end_turn()], [retreat()]):
                i6, r6 = p6.choose("candidate", items, {})
                i7, r7 = p7.choose("candidate", items, {})
                self.assertEqual((i6, r6.replace("rule6:", "", 1)), (i7, r7.replace("rule7:", "", 1)))
            self.assertEqual(p6.draws, p7.draws)


class RunnerAndBatchTest(unittest.TestCase):
    def test_runner_builds_rules_v7_and_records_it(self):
        result = V.run_game(small(policy="rules", rules_version=7, limits={"operations": 120}))
        p0 = result["policies"]["0"]
        self.assertEqual((p0["name"], p0["version"], p0["distribution"], p0["repeat_threshold"]), ("rules", 7, RULES7_DISTRIBUTION, 2))
        self.assertEqual((p0["loop"]["retreat_deferral"]["failure"], p0["loop"]["energy_trans_deferral"]["powers"], p0["loop"]["swap_cap"]["cap"]),
                         ("total_units_unreachable", ["エナジートランス"], 6))
        reasons = [e["candidate_reason"] for e in result["trace"] if e.get("type") == "attempt" and e.get("actor") in (0, 1)]
        self.assertTrue(reasons and all(r.startswith("rule7:") for r in reasons))

    def test_make_policies_and_batch_records(self):
        for policy in (V.make_policies(small(policy="rules", rules_version=7))[p] for p in (0, 1)):
            self.assertIsInstance(policy, RetreatDeferralRulePolicy)
        for version in (2, 3, 4, 5, 6):
            for policy in V.make_policies(small(policy="rules", rules_version=version)).values():
                self.assertFalse(isinstance(policy, RetreatDeferralRulePolicy) or hasattr(policy, "retreat_build_failed"))
        with self.assertRaises(ValueError):
            RulePolicy("s", version=7)
        self.assertEqual(B.MODES["rules-v7"], {"policy": "rules", "rules_version": 7, "repeat_threshold": 2})
        self.assertEqual(B.MODES["rules-v6"], {"policy": "rules", "rules_version": 6, "repeat_threshold": 2})
        adapter = B.EngineAdapter()
        v7 = adapter.policies_of(small(policy="rules", rules_version=7))
        v6 = adapter.policies_of(small(policy="rules", rules_version=6))
        self.assertEqual((v7["0"]["version"], v7["0"]["distribution"], v7["0"]["retreat_deferral"], v7["0"]["energy_trans_deferral"]["version"]),
                         (7, RULES7_DISTRIBUTION, RETREAT_DEFERRAL, 1))
        self.assertNotIn("retreat_deferral", v6["0"])
        self.assertEqual(B.TOOL_VERSION, 20)  # 20: rules-v9（旧の期待は 19）。 19: rules-v8（旧の期待は 18）


class SequenceTest(unittest.TestCase):
    def test_sequences_equal_rules_v6_until_the_first_retreat_deferral(self):
        """既定のデッキ seed 13・L67-U seed 9023: rules-v7 の列は、最初に「にげる」の後回しが働いた試みまで rules-v6 と同じ（働かなければ全体が同じ）。"""
        for name in ("rules-v2-s13", "rules-v2-l67u-s9023"):
            kw, _golden, _swaps = V2_GOLDEN[name]
            r6 = V.run_game(V.Config(policy="rules", rules_version=6, **kw))
            r7 = V.run_game(V.Config(policy="rules", rules_version=7, **kw))
            a6, a7 = R.action_sequence(r6["trace"]), R.action_sequence(r7["trace"])
            t7 = [e for e in r7["trace"] if e.get("type") == "attempt"]
            hit = [i for i, e in enumerate(t7) if ":retreat_deferred" in e["candidate_reason"]]
            if not hit:
                self.assertEqual(R.sequence_digest(a6, R.ACTION_FORMAT), R.sequence_digest(a7, R.ACTION_FORMAT), name)
            else:
                before = sum(1 for e in t7[:hit[0]] if (e.get("submit") or {}).get("outcome") == "accepted")
                self.assertEqual(a6[:before], a7[:before], name)
            self.assertEqual(r7["anomalies"], [], name)
            recorded = [e["retreat_deferral"] for e in t7 if "retreat_deferral" in e]
            self.assertTrue(all(r["result"] in ("recorded", "already_recorded", "not_applicable", "not_recorded:other_reason") for r in recorded), name)


if __name__ == "__main__":
    unittest.main()
