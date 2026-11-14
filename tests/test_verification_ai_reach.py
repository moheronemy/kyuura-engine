"""到達目的の方策 reach 版 1（docs/verification-ai-reach-policy.md 12 章）。

- 人工の API の応答（JSON）: 規則 R0〜R2・保護・段の選好・実送信の通知でだけ達成・両方の主体の復帰・保護の期間・情報境界の双子・既存の方策への非干渉
- バッチ: 方式の設定の計画への固定・改変の拒否・旧形式の拒否・短い本物の 1 局で記録への伝播（到達を狙う seed の探索ではない）
- fixture（構築盤面。new_game からの到達ではない）: P6・U-R3a の目標の操作を reach が選び、作った入力が check を通り、送ったあと両方の主体が復帰する
"""

from __future__ import annotations

import ast
import copy
import json
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from tools.verification_ai import batch as B
from tools.verification_ai import reach as RP
from tools.verification_ai.policies import BoundaryPolicy, MixedPolicy, RulePolicy, UniformPolicy, action_key

ROOT = Path(__file__).resolve().parents[1]
FD = RP.FACE_DOWN_REASON
SECRET, ALAKAZAM = "PMCG5-093", "PMCG1-049"
P6_SETTINGS = B.MODES["reach-p6"]["reach"]
UR3A_SETTINGS = B.MODES["reach-u-r3a"]["reach"]


# ---------------------------------------------------------------- 人工の応答


def view(*, actor=0, current=0, turn=3, segment=1, hand=(), active_fd=False, bench_fd=0, bench_normal=1, real=None, opponent_hand=None):
    me = {"active": {"pokemon_id": 1, **({"face_down": True} if active_fd else {}), **({"real": real} if real and active_fd else {})},
          "bench": [{"pokemon_id": 10 + i, "face_down": True, **({"real": real} if real else {})} for i in range(bench_fd)]
          + [{"pokemon_id": 20 + i} for i in range(bench_normal)],
          "hand": {"cards": [{"card": 100 + i, "card_id": c} for i, c in enumerate(hand)], "count": len(hand)}}
    other = {"active": {"pokemon_id": 50}, "bench": [], "hand": {"count": 3, **({"cards": opponent_hand} if opponent_hand is not None else {})}}
    players = [me, other] if actor == 0 else [other, me]
    return {"status": {"segment": segment}, "viewer": actor, "observation": {"current_player": current, "turn": turn, "phase": "main", "players": players}}


def cand(cid, kind, **extra):
    return {"id": cid, "kind": kind, "processability": extra.pop("processability", "may_stop_later"), "reasons": extra.pop("reasons", []),
            "input_disclosure": "confirmed", "input_stages": extra.pop("input_stages", []), **extra}


P6 = cand("c9", "retreat", processability="unverified", reasons=[FD], input_stages=[{"input": "choose_option", "stage": 1}, {"input": "choose_option", "stage": 2}])
RETREAT = cand("c5", "retreat", input_stages=[{"input": "choose_option", "stage": 1}, {"input": "choose_option", "stage": 2}])
UR3A = cand("c8", "use_power", processability="unverified", reasons=[FD], power={"index": 0, "face_down": True}, pokemon={"pokemon": 10, "face_down": True},
            input_stages=[{"input": "choose_option", "stage": 1}, {"input": "choose_option", "stage": 2}])
FD_POWER_ONE_STAGE = cand("c7", "use_power", processability="unverified", reasons=[FD], power={"index": 0, "face_down": True},
                          pokemon={"pokemon": 10, "face_down": True}, input_stages=[{"input": "choose_option", "stage": 1}])
REVEAL = cand("c4", "reveal_face_down", reasons=[FD], input_stages=[{"input": "choose_option", "stage": 1}])
END = cand("c1", "end_turn")
ATTACH = cand("c3", "attach_energy", processability="supported", input_stages=[{"input": "choose_option", "stage": 1}])
TRAINER = cand("c6", "play_trainer", input_stages=[{"input": "choose_option", "stage": 1}])
EVOLVE_FD = cand("c2", "evolve", processability="unverified", reasons=[FD], input_stages=[{"input": "choose_option", "stage": 1}, {"input": "choose_option", "stage": 2}])
DECISION = cand("c1", "answer_decision", input_stages=[{"input": "choose_option", "stage": 1}])


def pair(settings, seed="t"):
    budget = RP.ReachBudget(settings["tries_per_game"])
    return {a: RP.ReachPolicy(f"{seed}:{a}", actor=a, settings=copy.deepcopy(settings), budget=budget) for a in (0, 1)}, budget


def pick(policy, items, v):
    policy.begin_episode()
    policy.scope_profile(v)
    index, reason = policy.choose("candidate", items, {"view": v, "candidates": {}})
    return items[index], reason


def stage(policy, candidate, st, purpose, items, v):
    return policy.choose(purpose, items, {"view": v, "candidate": candidate, "stage": st})


class SettingsTest(unittest.TestCase):
    def test_modes_are_valid_and_target_alakazam(self):
        self.assertEqual(RP.validate_settings(P6_SETTINGS)["goal"], "p6")
        self.assertEqual((UR3A_SETTINGS["goal"], UR3A_SETTINGS["place_cards"], UR3A_SETTINGS["move_to_active"]), ("u_r3a", [ALAKAZAM], False))
        for s in (P6_SETTINGS, UR3A_SETTINGS):
            self.assertEqual((s["version"], s["protect_own_turns"], s["tries_per_game"], s["base"], s["place_trainers"]), (1, 3, 1, "rules-v2", [SECRET]))

    def test_bad_settings_are_refused(self):
        bad = [{**P6_SETTINGS, "extra": 1}, {k: v for k, v in P6_SETTINGS.items() if k != "goal"}, {**P6_SETTINGS, "goal": "x"},
               {**P6_SETTINGS, "tries_per_game": 2}, {**P6_SETTINGS, "protect_own_turns": 0}, {**P6_SETTINGS, "version": 2},
               {**UR3A_SETTINGS, "move_to_active": True}, {**UR3A_SETTINGS, "place_cards": []}, {**P6_SETTINGS, "base": "boundary"},
               {**P6_SETTINGS, "place_trainers": []}, "p6"]
        for s in bad:
            with self.subTest(s=s), self.assertRaises(RP.ReachSettingsError):
                RP.validate_settings(s)

    def test_policy_module_does_not_import_engine(self):
        for name in ("reach.py", "policies.py"):
            tree = ast.parse((ROOT / "tools" / "verification_ai" / name).read_text(encoding="utf-8"))
            mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)] + [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
            self.assertFalse([m for m in mods if "kyuura_engine" in m], name)

    def test_predicates_match_judge(self):
        from tools.verification_ai import judge as J

        self.assertEqual(RP.FACE_DOWN_REASON, J.FACE_DOWN_REASON)
        p6_stages = [{"stage": 1}, {"stage": 2, "cost_evaluation": {"status": "not_evaluated", "reason": FD, "omitted": ["total_units", "units"]}}]
        self.assertTrue(RP.is_p6_candidate(P6) and J.is_p6(P6, p6_stages))
        self.assertFalse(RP.is_p6_candidate(RETREAT) or J.is_p6(RETREAT, [{"stage": 1}, {"stage": 2, "total_units": {"min": 0, "max": 0}}]))
        self.assertTrue(RP.is_u_r3a_candidate(UR3A) and J.is_face_down_power(UR3A))
        self.assertTrue(J.is_face_down_power(FD_POWER_ONE_STAGE) and not RP.is_u_r3a_candidate(FD_POWER_ONE_STAGE))  # 0〜1 段は U-R3a でない


class RuleTest(unittest.TestCase):
    def test_p6_target_first(self):
        ps, _ = pair(P6_SETTINGS)
        chosen, reason = pick(ps[0], [END, REVEAL, P6, ATTACH], view(active_fd=True))
        self.assertEqual((chosen["id"], reason.split(":")[:3]), ("c9", ["reach", "p6", "R0"]))
        self.assertEqual(ps[0].scope_profile(view(active_fd=True)), "boundary")

    def test_p6_moves_face_down_bench_by_normal_retreat_once_per_turn(self):
        ps, _ = pair(P6_SETTINGS)
        v = view(bench_fd=1)
        chosen, reason = pick(ps[0], [END, ATTACH, RETREAT, REVEAL], v)
        self.assertEqual((chosen["id"], reason.split(":")[2]), ("c5", "R1"))
        st = {"stage": 1, "role": "new_active", "options": [{"id": "o1", "pokemon": 20}, {"id": "o2", "pokemon": 10, "face_down": True}]}
        index, why = stage(ps[0], RETREAT, st, "option", ["o1", "o2"], v)
        self.assertEqual((index, "R1:face_down_new_active" in why), (1, True))
        chosen, reason = pick(ps[0], [END, ATTACH, RETREAT, REVEAL], v)  # 同じ番の 2 回目は R1 にしない（保護のあいだの rules-v2）
        self.assertEqual((chosen["id"], reason.split(":")[1]), ("c3", "protect"))

    def test_promote_active_prefers_face_down_for_p6_only(self):
        st = {"stage": 1, "decision_kind": "promote_active", "options": [{"id": "o1", "pokemon": 20}, {"id": "o2", "pokemon": 10, "face_down": True}]}
        v = view(current=1, bench_fd=1)
        ps, _ = pair(P6_SETTINGS)
        pick(ps[0], [DECISION], v)
        self.assertEqual(stage(ps[0], DECISION, st, "option", ["o1", "o2"], v)[0], 1)
        us, _ = pair(UR3A_SETTINGS)
        pick(us[0], [DECISION], v)
        self.assertIn("reach:stage:uniform", stage(us[0], DECISION, st, "option", ["o1", "o2"], v)[1])

    def test_u_r3a_does_not_require_active(self):
        us, _ = pair(UR3A_SETTINGS)
        v = view(bench_fd=1)
        chosen, reason = pick(us[0], [END, RETREAT, UR3A, REVEAL], v)
        self.assertEqual((chosen["id"], reason.split(":")[2]), ("c8", "R0"))
        us, _ = pair(UR3A_SETTINGS)
        chosen, reason = pick(us[0], [END, RETREAT, FD_POWER_ONE_STAGE, REVEAL], v)  # 目標がなければ R1 はない（u_r3a）。保護で reveal を下げ、rules-v2 の順位
        self.assertNotEqual(reason.split(":")[2:3], ["R1"])
        self.assertNotIn(chosen["id"], ("c4",))

    def test_secret_plan_preferences(self):
        us, _ = pair(UR3A_SETTINGS)
        v = view(hand=(SECRET, ALAKAZAM, "PMCG1-101"))
        chosen, reason = pick(us[0], [END, ATTACH, TRAINER], v)
        self.assertEqual((chosen["id"], reason.split(":")[2]), ("c6", "R2"))
        trainer_stage = {"stage": 1, "role": "trainer", "options": [{"id": "o1", "card_id": "PMCG1-074"}, {"id": "o2", "card_id": SECRET}]}
        self.assertEqual(stage(us[0], TRAINER, trainer_stage, "option", ["o1", "o2"], v)[0], 1)
        decision = {"stage": 1, "decision_kind": "secret_plan_card", "count": {"min": 0, "max": 1},
                    "options": [{"id": "o1", "card_id": "PMCG1-101"}, {"id": "o2", "card_id": ALAKAZAM}, {"id": "o3", "card_id": "PMCG1-046"}]}
        self.assertEqual(stage(us[0], DECISION, decision, "count", [0, 1], v)[0], 1)
        self.assertEqual(stage(us[0], DECISION, decision, "option", ["o1", "o2", "o3"], v)[0], 1)
        no_target = {**decision, "options": [o for o in decision["options"] if o["card_id"] != ALAKAZAM]}
        self.assertEqual(stage(us[0], DECISION, no_target, "count", [0, 1], v)[0], 0)  # 対象が選べなければ出さない（捏造しない）
        ps, _ = pair(P6_SETTINGS)
        pick(ps[0], [DECISION], v)
        self.assertEqual(stage(ps[0], DECISION, no_target, "count", [0, 1], v)[0], 1)  # P6 は手札のどれでもよい

    def test_r2_needs_target_in_hand_for_u_r3a(self):
        us, _ = pair(UR3A_SETTINGS)
        chosen, reason = pick(us[0], [END, ATTACH, TRAINER], view(hand=(SECRET, "PMCG1-101")))
        self.assertTrue(reason.startswith("reach:base:"))
        self.assertEqual(chosen["id"], "c3")

    def test_trainer_not_offered_veto_then_send(self):
        us, _ = pair(UR3A_SETTINGS)
        v = view(hand=(SECRET, ALAKAZAM))
        pick(us[0], [END, TRAINER], v)
        key = action_key(0, TRAINER, [], [{"stage": 1, "option": {"id": "o1", "card_id": "PMCG1-074"}}])
        self.assertEqual(us[0].review(TRAINER, key, (1, 3)), {"send": False, "reason": "reach:trainer_not_offered"})
        self.assertTrue(us[0].review(TRAINER, key, (1, 3))["send"])  # 下げたあとは rules-v2 の評価（選び直しを止めない）


class ProtectionTest(unittest.TestCase):
    def test_reveal_is_demoted_while_protecting_and_restored_after_expiry(self):
        ps, _ = pair(P6_SETTINGS)
        chosen, _ = pick(ps[0], [REVEAL, END], view(bench_fd=1, turn=3))
        self.assertEqual(chosen["id"], "c1")
        chosen, _ = pick(ps[0], [REVEAL, END, ATTACH], view(bench_fd=1, turn=3))
        self.assertEqual(chosen["id"], "c3")
        for t in (5, 7):
            pick(ps[0], [REVEAL, END], view(bench_fd=1, turn=t))
        self.assertEqual((ps[0].protect_turns, ps[0].expired), (3, False))
        self.assertEqual(ps[0].scope_profile(view(bench_fd=1, turn=9)), "deep")  # 4 番目の自分の番で使い切り
        chosen, reason = pick(ps[0], [REVEAL, END], view(bench_fd=1, turn=9))
        self.assertEqual((chosen["id"], reason.startswith("reach:off:rule2:")), ("c4", True))
        self.assertTrue(ps[1].active())  # 期限は主体ごと

    def test_period_counts_own_turn_transitions_only(self):
        ps, _ = pair(P6_SETTINGS)
        for _ in range(4):
            pick(ps[0], [REVEAL, END], view(bench_fd=1, turn=3))  # 同じ番の選び直し
        pick(ps[0], [DECISION], view(current=1, bench_fd=1, turn=4))  # 相手の番の決定への回答
        self.assertEqual(ps[0].protect_turns, 1)
        pick(ps[0], [END], view(bench_fd=0, turn=5))  # 対象が消えても数え直さない
        pick(ps[0], [REVEAL, END], view(bench_fd=1, turn=7))
        self.assertEqual(ps[0].protect_turns, 3)

    def test_protect_veto_for_face_down_designation(self):
        ps, _ = pair(P6_SETTINGS)
        pick(ps[0], [EVOLVE_FD, END], view(bench_fd=1))
        key = action_key(0, EVOLVE_FD, [], [{"stage": 1, "option": {"id": "o1", "card_id": "PMCG1-046"}},
                                            {"stage": 2, "option": {"id": "o2", "pokemon": 10, "face_down": True}}])
        self.assertEqual(ps[0].review(EVOLVE_FD, key, (1, 3))["reason"], "reach:protect_veto")
        self.assertTrue(ps[0].review(EVOLVE_FD, key, (1, 3))["send"])
        decision_key = action_key(0, DECISION, [], [{"stage": 1, "option": {"id": "o2", "pokemon": 10, "face_down": True}}])
        self.assertTrue(ps[0].review(DECISION, decision_key, (1, 3))["send"])  # 決定は止めない
        st = {"stage": 1, "role": "target", "options": [{"id": "o1", "pokemon": 20}, {"id": "o2", "pokemon": 10, "face_down": True}]}
        self.assertEqual(stage(ps[0], ATTACH, st, "option", ["o1", "o2"], view(bench_fd=1))[0], 0)  # 保護のあいだ、ほかの段はうらを避ける


class SubmitTest(unittest.TestCase):
    def test_selection_and_check_do_not_count(self):
        ps, budget = pair(P6_SETTINGS)
        pick(ps[0], [P6, END], view(active_fd=True))
        key = action_key(0, P6, [], [{"stage": 1, "option": {"id": "o1", "pokemon": 20}}])
        self.assertEqual(ps[0].review(P6, key, (1, 3)), {"send": True, "reason": "reach:target_send"})
        self.assertEqual(budget.used, 0)
        ps[0].notify_submit(END, "k")  # 目標でない操作の通知は数えない
        self.assertEqual(budget.used, 0)
        self.assertTrue(all(p.active() for p in ps.values()))

    def test_actual_submit_returns_both_players_to_rules_v2_and_deep(self):
        ps, budget = pair(P6_SETTINGS, seed="s")
        pick(ps[0], [P6, END], view(active_fd=True))
        ps[0].notify_submit(P6, "k")
        self.assertEqual((budget.used, ps[0].target_submits), (1, 1))
        for a, p in ps.items():
            self.assertEqual((p.active(), p.scope_profile(view(actor=a, current=a, active_fd=True))), (False, "deep"))
        chosen, reason = pick(ps[1], [P6, END], view(actor=1, current=1, active_fd=True))  # 局で 2 回目を狙わない（rules-v2 の順位: retreat 5 < end_turn 6）
        self.assertTrue(reason.startswith("reach:off:rule2:"))
        ps[1].notify_submit(P6, "k")
        self.assertEqual(budget.used, 1)

    def test_inactive_reach_matches_rules_v2_choices_and_draws(self):
        budget = RP.ReachBudget(1)
        budget.use()
        reach = RP.ReachPolicy("same", actor=0, settings=P6_SETTINGS, budget=budget)
        rules = RulePolicy("same", version=2)
        lists = [[END, REVEAL, ATTACH, RETREAT], [END, REVEAL], [DECISION], [TRAINER, ATTACH, cand("c7", "attach_energy")], [P6, RETREAT, END]]
        for items in lists * 3:
            v = view(bench_fd=1)
            reach.begin_episode(), rules.begin_episode()
            a = reach.choose("candidate", items, {"view": v})
            b = rules.choose("candidate", items, {"view": v})
            self.assertEqual((a[0], a[1]), (b[0], "reach:off:" + b[1]))
            for purpose, xs in (("option", ["o1", "o2", "o3"]), ("count", [0, 1, 2])):
                self.assertEqual(reach.choose(purpose, xs, {"view": v})[0], rules.choose(purpose, xs, {"view": v})[0])
        self.assertEqual(reach.draws, rules.draws)

    def test_existing_policies_have_no_reach_hooks(self):
        for p in (UniformPolicy("x"), RulePolicy("x", version=1), RulePolicy("x", version=2), BoundaryPolicy("x"),
                  MixedPolicy("x", epsilon=0.25, mix_seed_text="m")):
            self.assertFalse(hasattr(p, "scope_profile") or hasattr(p, "notify_submit"), type(p).__name__)


class InformationTest(unittest.TestCase):
    def test_twins_differing_in_real_and_opponent_hand_choose_the_same(self):
        seqs = []
        for real, opp in (({"card_id": "PMCG1-052"}, [{"card_id": "PMCG1-058"}]), ({"card_id": "PMCG1-046"}, [{"card_id": "PMCG1-049"}])):
            ps, _ = pair(P6_SETTINGS, seed="twin")
            out = []
            for items, kw in (([END, ATTACH, RETREAT, REVEAL], {"bench_fd": 1}), ([REVEAL, END, ATTACH], {"bench_fd": 1}), ([P6, END], {"active_fd": True})):
                v = view(real=real, opponent_hand=opp, **kw)
                out.append(pick(ps[0], items, v))
                st = {"stage": 1, "role": "new_active", "options": [{"id": "o1", "pokemon": 20}, {"id": "o2", "pokemon": 10, "face_down": True}]}
                out.append(stage(ps[0], RETREAT, st, "option", ["o1", "o2"], v))
            seqs.append(out)
        self.assertEqual(seqs[0], seqs[1])


# ---------------------------------------------------------------- バッチ


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vai-reach-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.a = B.EngineAdapter("test")

    def plan(self, name, modes=("reach-p6", "reach-u-r3a"), **kw):
        return B.make_plan(self.tmp, name, engine_commit="test", tool_commit="test", seeds=[12], modes=list(modes), deck0="hitmonchan-dewgong",
                           deck1="venusaur-parasect", adapter=self.a, game_limits={"operations": 40, "seconds": 60}, **kw)

    def test_plan_fixes_reach_settings_and_identity(self):
        plan = self.plan("p")
        self.assertEqual((plan["format"], B.PLAN_FORMAT, B.COMPLETE_FORMAT, B.TOOL_VERSION),
                         ("kyuura-vai-batch-plan/6", "kyuura-vai-batch-plan/6", "kyuura-vai-batch-complete/6", 10))  # 10: 判定の規則 8。9: 判定の規則 7。8: reach 版 2 を加えた（版 1 の設定・選び方は同じ）
        for entry, settings in zip(plan["games"], (P6_SETTINGS, UR3A_SETTINGS)):
            self.assertEqual((entry["config"]["policy"], entry["config"]["profile"], entry["config"]["rules_version"], entry["config"]["reach"]),
                             ("reach", "boundary", 2, settings))
            for side in ("0", "1"):
                p = entry["policies"][side]
                self.assertEqual((p["name"], p["version"], p["rules_version"], p["reach"], p["distribution"]),
                                 ("reach", 1, 2, settings, RP.REACH_DISTRIBUTION))
            self.assertEqual(entry["policies"]["host"]["name"], "uniform")
        loaded, digest = B.load_plan(B.batch_dir(self.tmp, "p"), self.a)
        self.assertEqual(loaded["games"][0]["config"]["reach"]["protect_own_turns"], 3)
        self.assertEqual(digest, (B.batch_dir(self.tmp, "p") / "plan.sha256").read_text(encoding="utf-8").split()[0])

    def test_existing_modes_have_no_reach(self):
        plan = self.plan("e", modes=("uniform-stage", "rules-v2", "boundary"))
        self.assertTrue(all(g["config"]["reach"] is None and "reach" not in g["policies"]["0"] for g in plan["games"]))

    def _rewrite(self, name, edit, *, fix_sha=True):
        bdir = B.batch_dir(self.tmp, name)
        plan = json.loads((bdir / "plan.json").read_bytes())
        edit(plan)
        data = B.json_bytes(plan)
        (bdir / "plan.json").write_bytes(data)
        if fix_sha:
            (bdir / "plan.sha256").write_bytes((B.sha256_bytes(data) + "  plan.json\n").encode())
        return bdir

    def test_tampered_or_mismatched_plans_are_refused(self):
        cases = {
            "protect": lambda p: p["games"][0]["config"]["reach"].update(protect_own_turns=4),
            "goal": lambda p: p["games"][0]["config"]["reach"].update(goal="u_r3a", move_to_active=False, place_cards=[ALAKAZAM]),
            "tries": lambda p: p["games"][1]["config"]["reach"].update(tries_per_game=2),
            "mode": lambda p: p["games"][0].update(mode="reach-u-r3a"),
            "unknown_key": lambda p: p["games"][0]["config"]["reach"].update(extra=True),
            "old_format": lambda p: p.update(format="kyuura-vai-batch-plan/5"),
            "base": lambda p: p["games"][0]["config"].update(rules_version=1),
        }
        for name, edit in cases.items():
            with self.subTest(name):
                self.plan(name)
                bdir = self._rewrite(name, edit)
                with self.assertRaises(B.BatchRefused):
                    B.load_plan(bdir, self.a)
        self.plan("nosha")
        with self.assertRaises(B.BatchRefused) as ctx:
            B.load_plan(self._rewrite("nosha", cases["protect"], fix_sha=False), self.a)
        self.assertIn("sha256", str(ctx.exception))

    def test_short_real_game_records_reach_settings_and_observation(self):
        """本物の 1 局（操作 40。固定デッキ。秘策はない）: 計画の設定が runner・記録・観測の記録・到達の段の集計へ届く（到達を狙わない）。"""
        from tools.verification_ai import reach_report as RR

        self.plan("real", modes=("reach-u-r3a",), observation=True)
        out = B.run_batch(self.tmp, "real", adapter=self.a)
        self.assertEqual(out.status, "completed")
        adir = B.batch_dir(self.tmp, "real") / "games" / "g001-reach-u-r3a-s12" / "attempt-001"
        result = json.loads((adir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["policies"]["0"]["reach"], UR3A_SETTINGS)
        self.assertEqual(result["policies"]["0"]["reach_state"]["budget_used"], 0)
        trace = [json.loads(line) for line in (adir / "trace.jsonl").read_text(encoding="utf-8").splitlines()]
        episodes = [e for e in trace if e.get("type") == "episode"]
        players = [e for e in episodes if e["actor"] in (0, 1)]
        self.assertTrue(players and all(e["policy"] == "reach" and "reach" in e for e in players))
        attempts = [e for e in trace if e.get("type") == "attempt" and e["actor"] in (0, 1)]
        self.assertTrue(attempts and all(e["scope_profile"] in ("boundary", "deep") and e["candidate_reason"].startswith("reach:") for e in attempts))
        self.assertEqual(json.loads((adir / "observe" / "summary.json").read_text(encoding="utf-8"))["status"], "complete")
        report = RR.game_report(adir)
        target = report["goals"]["u_r3a"]["target"]["0"]
        self.assertEqual((target["offered_positions"], target["submitted"]), (0, 0))
        self.assertEqual(report["goals"]["u_r3a"]["prerequisites"]["0"]["placed_target_card"], 0)
        self.assertEqual(report["policy"]["final_state"]["0"]["goal"], "u_r3a")

    def test_report_marks_missing_records(self):
        from tools.verification_ai import reach_report as RR

        d = self.tmp / "old" / "attempt-001"
        (d / "actors").mkdir(parents=True)
        entry = {"type": "attempt", "actor": 0, "candidate": P6, "choices": ["o1"], "check": {"response": {"valid": True}},
                 "submit": {"outcome": "accepted"}, "stages": []}
        (d / "trace.jsonl").write_text(json.dumps(entry) + "\n", encoding="utf-8")
        (d / "actors" / "0.jsonl").write_text(json.dumps({"type": "attempt", "position": 1}) + "\n", encoding="utf-8")
        report = RR.game_report(d)
        p6 = report["goals"]["p6"]
        self.assertEqual(p6["target"]["0"]["offered_positions"]["status"], RR.NOT_RECORDED)
        self.assertEqual(p6["target"]["1"]["offered_positions"]["status"], RR.NOT_RECORDED)
        self.assertEqual(p6["target"]["0"]["accepted_content"], {RR.NOT_RECORDED: 1})
        self.assertEqual(report["policy"]["status"], RR.NOT_RECORDED)
        self.assertEqual(p6["prerequisites"]["status"], "not_applicable")


# ---------------------------------------------------------------- fixture（構築盤面。new_game からの到達ではない）


def _hosted(state):
    from kyuura_engine import snapshot as SN

    from tools.verification_ai.fixtures_v3_3 import restore
    from tools.verification_ai.run_v3_3 import Case

    game, status = restore(SN.dumps_snapshot(SN.save_snapshot(state, label="verification-ai reach fixture")))
    assert game is not None, status
    return Case(game)


def _scope(cands, profile):
    from tools.verification_ai.runner import Runner

    stub = SimpleNamespace(config=SimpleNamespace(profile=profile), counters=Counter(), _cover=lambda *a: None)
    return Runner._scope(stub, cands, {}, profile)


def drive(case, policies, actor, *, expect_rule):
    """1 回の選択から submit まで（共通の行動生成・check・submit_checked。方策は位置を選ぶだけ）。fixture の到達の段を返す。"""
    from kyuura_engine.observation import visible_log

    from tools.verification_ai import actions as A
    from tools.verification_ai.judge import judge_normal, judge_recorded_accepted_content
    from tools.verification_ai.runner import request, submit_checked

    policy = policies[actor]
    endpoint = case.endpoints[actor]
    v = request(endpoint, "view")
    policy.begin_episode()
    profile = policy.scope_profile(v)
    cands = request(endpoint, "candidates")["response"]
    in_scope, _scope_info, _ = _scope(cands, profile)
    index, reason = policy.choose("candidate", in_scope, {"view": v, "candidates": cands})
    candidate = in_scope[index]
    out = {"profile": profile, "offered": [c["kind"] for c in cands["candidates"]], "chosen": candidate["kind"], "rule": reason.split(":")[2],
           "target": RP.is_target(policy.goal, candidate)}
    assert out["rule"] == expect_rule, (reason, out)
    handle = {"game": cands["game"], "revision": cands["revision"], "candidate": candidate["id"]}
    stages = request(endpoint, "inputs", **handle)["response"]["stages"] if candidate["input_stages"] else []
    allowed = A.FALLBACK_PROCESSABILITY if profile == "boundary" else A.DEEP_PROCESSABILITY
    choices, picks, meaning = A.build_choices(stages, policy, {"view": v, "candidate": candidate}, allowed)
    out.update(built=True, picks=[p["reason"] for p in picks])
    key = action_key(actor, candidate, stages, meaning)
    out["review"] = policy.review(candidate, key, None)["reason"]
    checked = request(endpoint, "check", **handle, choices=choices)
    checked["_handle"], checked["_choices"] = handle, choices  # runner と同じ（submit_checked が照らす）
    out["check_valid"] = checked["response"]["valid"]
    out["budget_before_submit"] = policy.budget.used
    before = case.game.state
    sent = submit_checked(endpoint, handle, choices, checked, operation_id=f"reach-fixture-{policy.budget.used}")
    policy.notify_submit(candidate, key)
    out.update(submitted=True, outcome=sent.get("outcome"), budget_after_submit=policy.budget.used)
    submit = {"ok": sent.get("ok"), "outcome": sent.get("outcome"), "refusal": sent.get("refusal"), "result": sent.get("result")}
    result = case.results[-1] if case.results else None  # 検証者の側の診断（方策には渡さない）
    if result is not None and result.diagnosis is not None:
        submit["verifier"] = {"diagnostic_id": result.diagnosis.diagnostic_id, "category": result.diagnosis.category, "engine_code": result.verifier.engine_code}
    verdict, why = judge_normal(candidate, meaning, submit, stages=stages)
    out["judge"] = [verdict, why[:2]]
    entry = {"candidate": candidate, "stages": stages, "submit": submit}
    if sent.get("outcome") == "accepted":
        entry["public_events_after_accept"] = visible_log(case.game.state, None)[len(visible_log(before, None)):]
        judged = judge_recorded_accepted_content(entry)
        out["accepted_content"] = None if judged is None else [judged[1], judged[2][0]]
    out["after"] = {str(a): {"active": p.active(), "profile": p.scope_profile(request(case.endpoints[a], "view"))} for a, p in policies.items()}
    return out


def fixture_p6_direct():
    from tools.verification_ai import fixtures_p6 as F

    state, _record = F.build("P6A")
    case = _hosted(state)
    policies, _ = pair(P6_SETTINGS, seed="fixture-p6")
    return {"fixture": "P6A", "origin": "constructed_fixture", "new_game": False, "steps": [drive(case, policies, 0, expect_rule="R0")]}


def fixture_u_r3a_bench():
    from tools.verification_ai import fixtures_u_r3a as F

    state, _record = F.build("UR3A-VN")
    case = _hosted(state)
    policies, _ = pair(UR3A_SETTINGS, seed="fixture-ur3a")
    return {"fixture": "UR3A-VN", "origin": "constructed_fixture", "new_game": False, "steps": [drive(case, policies, 0, expect_rule="R0")]}


def fixture_p6_chain():
    """秘策でうらにしたディグダがベンチ、バトル場は闘エネルギー 2 枚のエビワラー（tests/test_secret_plan_v0_67 の board・place）。R1（通常のにげるでうらの控えへ）→ R0（P6）。"""
    from tests import test_secret_plan_v0_67 as S

    state = S.place(S.board(hand=(S.DIGLETT,)), S.DIGLETT)
    case = _hosted(state)
    policies, _ = pair(P6_SETTINGS, seed="fixture-chain")
    first = drive(case, policies, 0, expect_rule="R1")
    second = drive(case, policies, 0, expect_rule="R0")
    return {"fixture": "secret_plan_board+place(DIGLETT)", "origin": "constructed_fixture", "new_game": False, "steps": [first, second]}


class FixtureTest(unittest.TestCase):
    def test_p6_face_down_active(self):
        step = fixture_p6_direct()["steps"][0]
        self.assertEqual((step["profile"], step["chosen"], step["target"], step["check_valid"], step["review"]), ("boundary", "retreat", True, True, "reach:target_send"))
        # 入力の中身は uniform-stage（目標ではない）。この fixture（にげる 0・闘エネルギー 1 枚）では 1 枚トラッシュを選び、エンジンが正常に拒否する（submit は呼んだので達成）
        self.assertEqual((step["budget_before_submit"], step["budget_after_submit"], step["outcome"]), (0, 1, "rejected"))
        self.assertEqual(step["judge"], ["normal_rejection", ["invalid_input", "WRONG_RETREAT_COST"]])
        self.assertEqual(step["after"], {"0": {"active": False, "profile": "deep"}, "1": {"active": False, "profile": "deep"}})

    def test_u_r3a_on_bench(self):
        step = fixture_u_r3a_bench()["steps"][0]
        self.assertEqual((step["chosen"], step["target"], step["check_valid"], step["outcome"]), ("use_power", True, True, "accepted"))
        self.assertEqual(step["accepted_content"], ["expected", "face_down_power_revealed_not_basic_and_trashed"])
        self.assertEqual(step["after"]["1"], {"active": False, "profile": "deep"})

    def test_p6_chain_from_bench(self):
        first, second = fixture_p6_chain()["steps"]
        self.assertEqual((first["chosen"], first["target"], first["check_valid"], first["outcome"], first["budget_after_submit"]),
                         ("retreat", False, True, "accepted", 0))
        self.assertTrue(any("R1:face_down_new_active" in r for r in first["picks"]))
        self.assertEqual((second["chosen"], second["target"], second["outcome"], second["budget_after_submit"]), ("retreat", True, "accepted", 1))
        self.assertEqual(second["accepted_content"], ["expected", "p6_revealed_and_retreated"])


if __name__ == "__main__":
    unittest.main()
