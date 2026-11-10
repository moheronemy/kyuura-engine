"""検証用 AI の V2 のテスト（docs/verification-ai-v2.md 6 章）。

- PriorityTest: rules-v1 の優先順位・同順位の選択・end_turn だけの場面・準備・ホスト・決定での均等への切りかえ・入力の選択は uniform-stage のまま
- MixedTest: ε=0・ε=1 の境界、固定の種での混合の判定と記録、エピソードの途中で方式を変えない
- EpisodeTest: 試みとエピソードの対応、選び直しのあいだ方式が固定で、上限で止まる
- BoundaryTest: ルール・混合の方策に渡る値が本人の JSON だけ。check を経ない送信がない
- RandomUnchangedTest: 均等の方策の選び方と再現性を変えていない（エピソードの始めは乱数を使わない・ε=1 の混合は均等と同じ列）
- PrizeTest: 公開のサイドの枚数の増減の数え方

確率は固定の種での具体的な選択だけで確かめる。対戦はどれも上限の小さな対戦。
"""

from __future__ import annotations

import json
import random
import unittest

from tools.verification_ai import records as R
from tools.verification_ai import runner as V
from tools.verification_ai.policies import (
    PRIORITY,
    STAGE,
    MixedPolicy,
    RulePolicy,
    UniformPolicy,
    mix_seed,
    player_seed,
)


def cand(kind, cid="c1"):
    return {"id": cid, "kind": kind, "processability": "may_stop_later", "input_disclosure": "no_input", "input_stages": []}


def small(policy, **kw):
    limits = kw.pop("limits", {})
    return V.Config(policy=policy, limits=V.Limits(**{"operations": 30, "seconds": 60, **limits}), **kw)


def json_only(value) -> bool:
    if isinstance(value, dict):
        return all(type(k) is str and json_only(v) for k, v in value.items())
    if isinstance(value, list):
        return all(json_only(v) for v in value)
    return value is None or type(value) in (str, int, float, bool)


class PriorityTest(unittest.TestCase):
    def test_priority_order(self):
        items = [cand("end_turn", "c1"), cand("play_trainer", "c2"), cand("attach_energy", "c3"), cand("evolve", "c4"), cand("use_attack", "c5")]
        policy = RulePolicy("p")
        self.assertEqual(policy.choose("candidate", items, {}), (3, "rule:priority2:evolve"))
        self.assertEqual(policy.draws, 0)  # 1 つに決まれば乱数を使わない
        self.assertEqual(policy.choose("candidate", items[:3] + items[4:], {}), (2, "rule:priority3:attach_energy"))
        self.assertEqual(policy.choose("candidate", [items[0], items[1], items[4]], {}), (2, "rule:priority4:use_attack"))
        self.assertEqual(policy.choose("candidate", [items[0], items[1]], {}), (1, "rule:priority5:play_trainer"))
        self.assertEqual(policy.choose("candidate", [items[0]], {}), (0, "rule:priority6:end_turn"))  # end_turn だけ

    def test_tie_uses_policy_rng(self):
        items = [cand("end_turn", "c1"), cand("play_trainer", "c2"), cand("use_power", "c3"), cand("retreat", "c4")]
        policy = RulePolicy("tie-seed")
        expected = random.Random("tie-seed").randrange(3)
        index, reason = policy.choose("candidate", items, {})
        self.assertEqual(index, 1 + expected)
        self.assertEqual(reason, f"rule:priority5:{items[index]['kind']}:tie3")
        self.assertEqual(policy.draws, 1)

    def test_fallback_without_priority(self):
        for kind in ("place_starting", "mulligan_draw", "answer_decision", "take_prize", "promote_active", "report_janken"):
            with self.subTest(kind):
                self.assertNotIn(kind, PRIORITY)
                items = [cand(kind, "c1"), cand(kind, "c2")]
                rule, uniform = RulePolicy("fb"), UniformPolicy("fb")
                index, reason = rule.choose("candidate", items, {})
                self.assertEqual(reason, "rule:fallback:no_priority")
                self.assertEqual(index, uniform.choose("candidate", items, {})[0])

    def test_inputs_stay_uniform_stage(self):
        rule, uniform = RulePolicy("inputs"), UniformPolicy("inputs")
        for purpose in ("count", "option", "value", "units_set"):
            self.assertEqual(rule.choose(purpose, list(range(7)), {}), uniform.choose(purpose, list(range(7)), {}))
        self.assertEqual(rule.distribution, "rules-v1-candidate+uniform-stage")

    def test_host_is_uniform_for_every_policy(self):
        for name in ("uniform", "rules", "mixed"):
            with self.subTest(name):
                policies = V.make_policies(V.Config(policy=name))
                self.assertIs(type(policies[V.HOST]), UniformPolicy)
                self.assertEqual(policies[V.HOST].distribution, STAGE)
        self.assertIs(type(V.make_policies(V.Config(policy="rules"))[0]), RulePolicy)
        self.assertIs(type(V.make_policies(V.Config(policy="mixed"))[1]), MixedPolicy)


class MixedTest(unittest.TestCase):
    def mixed(self, epsilon, seed="mix"):
        return MixedPolicy(player_seed(1, 0), epsilon=epsilon, mix_seed_text=seed)

    def test_boundaries(self):
        for epsilon, mode in ((0.0, "rule"), (1.0, "random")):
            policy = self.mixed(epsilon)
            self.assertEqual({policy.begin_episode()["mode"] for _ in range(20)}, {mode})

    def test_fixed_seed_modes_and_record(self):
        policy = self.mixed(0.25, "fixed-mix")
        rng = random.Random("fixed-mix")
        for _ in range(8):
            draw = rng.random()
            record = policy.begin_episode()
            self.assertEqual(record, {"mode": "random" if draw < 0.25 else "rule", "draw": round(draw, 6), "epsilon": 0.25})
        self.assertEqual(sum(policy.episodes.values()), 8)

    def test_mode_fixed_inside_episode(self):
        items = [cand("end_turn", "c1"), cand("play_basic", "c2"), cand("play_basic", "c3")]
        policy = self.mixed(0.25, "fixed-mix")
        with self.assertRaises(RuntimeError):
            policy.choose("candidate", items, {})
        for _ in range(6):
            mode = policy.begin_episode()["mode"]
            reasons = [policy.choose("candidate", items, {})[1] for _ in range(4)]  # 選び直しを含む同じエピソードの中の選択
            self.assertTrue(all(r.startswith("uniform:" if mode == "random" else "rule:") for r in reasons), (mode, reasons))
            self.assertEqual(policy.mode, mode)

    def test_seed_derivation(self):
        self.assertEqual(mix_seed(12, 1), "kyuura-vai-v2:mix:12:1")
        self.assertNotEqual(mix_seed(12, 1), player_seed(12, 1))


class EpisodeTest(unittest.TestCase):
    def test_attempts_belong_to_episodes(self):
        result = V.run_game(small("mixed", game_seed=12, policy_seed=12, host_seed=12, limits={"operations": 60}))
        episodes = {e["episode"]: e for e in result["trace"] if e.get("type") == "episode"}
        attempts = [e for e in result["trace"] if e.get("type") == "attempt"]
        self.assertTrue(attempts and all("episode" in a for a in attempts))
        for number, ep in episodes.items():
            mine = [a for a in attempts if a["episode"] == number]
            self.assertEqual(ep["attempts"], len(mine))
            prefix = "uniform:" if ep["mode"] == "random" else "rule:"
            self.assertTrue(all(a["candidate_reason"].startswith(prefix) for a in mine), number)
            self.assertIn(ep["result"], ("accepted", result["termination"]["class"]))
        self.assertEqual(sum(1 for e in episodes.values() if e["result"] == "accepted"), result["counters"]["accepted"])

    def test_retry_keeps_mode_until_limit(self):
        def wrap(actor, endpoint):
            class Faulty:
                def handle(self, request):
                    if request["type"] == "check":
                        return {"ok": True, "response": {"valid": False, "refusal": {"code": "TEST"}}}
                    return endpoint.handle(request)
            return Faulty() if actor in (0, 1) else endpoint
        result = V.run_game(small("mixed"), wrap_endpoint=wrap)
        self.assertEqual(result["termination"]["class"], V.NO_PROGRESS)
        last = [e for e in result["trace"] if e.get("type") == "episode"][-1]
        self.assertEqual(last["result"], V.NO_PROGRESS)
        mine = [a for a in result["trace"] if a.get("type") == "attempt" and a["episode"] == last["episode"]]
        self.assertGreater(len(mine), 1)
        prefix = "uniform:" if last["mode"] == "random" else "rule:"
        self.assertTrue(all(a["candidate_reason"].startswith(prefix) for a in mine))  # 選び直しで引き直さない


class Recording(RulePolicy):
    contexts: list = []

    def choose(self, purpose, items, context):
        Recording.contexts.append((self.seed, purpose, items, context))
        return super().choose(purpose, items, context)


class BoundaryTest(unittest.TestCase):
    def test_rule_policy_receives_only_own_json(self):
        Recording.contexts = []
        V.run_game(small("rules"), policy_factory=Recording)
        self.assertTrue(Recording.contexts)
        for seed, purpose, items, context in Recording.contexts:
            self.assertTrue(json_only(items) and json_only(context), purpose)
            if seed.split(":")[1] == "player":
                self.assertEqual((context.get("view") or {}).get("viewer"), int(seed.split(":")[-1]))

    def test_no_submit_without_valid_check(self):
        for name in ("rules", "mixed"):
            with self.subTest(name):
                result = V.run_game(small(name, limits={"operations": 60}))
                for entry in result["trace"]:
                    if entry.get("submit"):
                        self.assertTrue(entry["check"]["response"]["valid"])
                for kind, k in result["metrics"]["kinds"].items():
                    self.assertEqual(k["submitted"], k["check_valid"], kind)


class RandomUnchangedTest(unittest.TestCase):
    def test_begin_episode_uses_no_randomness(self):
        a, b = UniformPolicy("same"), UniformPolicy("same")
        a.begin_episode()
        self.assertEqual([a.choose("x", list(range(9)), {}) for _ in range(5)], [b.choose("x", list(range(9)), {}) for _ in range(5)])

    def test_mixed_epsilon_bounds_equal_pure_policies(self):
        """ε=1 の混合は均等の方策と同じ意味の列、ε=0 は rules-v1 と同じ意味の列（候補・入力の選択の乱数は 1 本で、混合の判定は別の乱数）。"""
        uniform = R.meaning_sequence(V.run_game(small("uniform"))["trace"])
        rules = R.meaning_sequence(V.run_game(small("rules"))["trace"])
        self.assertEqual(R.meaning_sequence(V.run_game(small("mixed", epsilon=1.0))["trace"]), uniform)
        self.assertEqual(R.meaning_sequence(V.run_game(small("mixed", epsilon=0.0))["trace"]), rules)
        self.assertNotEqual(uniform, rules)

    def test_default_config_is_uniform_stage(self):
        policies = V.make_policies(V.Config())
        self.assertEqual([(type(p), p.distribution, p.seed) for p in (policies[0], policies[1])],
                         [(UniformPolicy, STAGE, player_seed(1, 0)), (UniformPolicy, STAGE, player_seed(1, 1))])


class ComparisonRowTest(unittest.TestCase):
    def test_reused_rows_mark_v2_metrics_unmeasured(self):
        from tools.verification_ai.run_v2 import UNMEASURED, row

        result = V.run_game(small("uniform"))
        verification = {"replay_run": {"status": "succeeded", "matches_expectation": True}, "correspondence_problems": []}
        reused, new = row("x", "reused_v1", result, verification), row("x", "new", result, verification)
        for key in ("prize_count_decrease", "episode_mode", "episode_attempts"):
            self.assertEqual(reused[key], UNMEASURED)
            self.assertNotEqual(new[key], UNMEASURED)
        self.assertEqual((reused["knock_outs"], new["knock_outs"]), (UNMEASURED, UNMEASURED))  # きぜつは推測しない
        self.assertEqual(new["stages"]["submitted"], new["stages"]["check_valid"])


class PrizeTest(unittest.TestCase):
    def test_prize_count_changes(self):
        runner = V.Runner(V.Config())
        obs = lambda a, b: {"players": [{"prizes": {"count": a}}, {"prizes": {"count": b}}]}
        for o in (obs(6, 6), obs(5, 6), obs(5, 4), obs(6, 4)):
            runner._track_prizes(o)
        axes = runner.metrics.to_dict()["axes"]
        self.assertEqual(axes["prize_count_decrease"], {"player0": 1, "player1": 2})
        self.assertEqual(axes["prize_count_increase"], {"player0": 1})

    def test_change_seen_with_game_over_is_counted(self):
        """終局の観測のサイドの減少も数える（e9fc20b の実行では終わり方の判定が先で、最後の減少が抜けていた）。"""
        calls = {"n": 0}

        def wrap(actor, endpoint):
            class Fake:
                def handle(self, request):
                    answer = endpoint.handle(request)
                    if request["type"] == "view":
                        calls["n"] += 1
                        players = answer["observation"]["players"]
                        if calls["n"] >= 3:  # 直前に見た枚数から 1 減った終局の観測
                            answer["status"] = {**answer["status"], "status": "game_over"}
                            players[1]["prizes"] = {**players[1]["prizes"], "count": calls["last"] - 1}
                        calls["last"] = players[1]["prizes"]["count"]
                    return answer
            return Fake() if actor == V.HOST else endpoint
        result = V.run_game(small("uniform"), wrap_endpoint=wrap)
        self.assertEqual(result["termination"]["class"], V.GAME_OVER)
        self.assertEqual(result["metrics"]["axes"].get("prize_count_decrease"), {"player1": 1})


if __name__ == "__main__":
    unittest.main()
