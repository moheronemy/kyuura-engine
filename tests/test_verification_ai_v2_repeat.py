"""検証用 AI の V2 の補完（rules-v2 の反復の抑制）のテスト（docs/verification-ai-v2-repeat.md 6 章）。

小さな JSON の例と偽物の応答で、同じ意味の操作の鍵・閾値の前後・番の切りかえ・受理だけが履歴を更新すること・混合のランダムの側・候補を下げたあとに end_turn へ進むこと・
抑える操作だけのとき・既存の方策の列を変えていないことを確かめる。対戦はどれも上限の小さな対戦。
"""

from __future__ import annotations

import json
import unittest

from tools.verification_ai import records as R
from tools.verification_ai import runner as V
from tools.verification_ai.policies import TUPLE, MixedPolicy, RulePolicy, action_key, candidate_identity, player_seed

TURN_A, TURN_B = (0, 5), (0, 6)


def power(cid="c3", pokemon=7, **extra):
    return {"id": cid, "kind": "use_power", "processability": "may_stop_later", "input_disclosure": "confirmed", "reasons": ["x"],
            "pokemon": {"pokemon": pokemon, "zone": "active"}, "power": {"index": 0, "name_ja": "P"}, "input_stages": [{"stage": 1}], **extra}


def end_turn(cid="c1"):
    return {"id": cid, "kind": "end_turn", "processability": "may_stop_later", "input_disclosure": "no_input", "input_stages": []}


STAGES = [{"stage": 1, "order": "not_applicable"}, {"stage": 2, "order": "significant"}, {"stage": 3, "order": "not_significant"}]


def meaning(source=1, target=2, extra=()):
    out = [{"stage": 1, "option": {"pokemon": source, "processability": "may_stop_later", "eligible": True}},
           {"stage": 2, "option": {"pokemon": target, "reasons": ["y"]}}]
    out += [{"stage": 3, "option": {"card": c}} for c in extra]
    return out


class KeyTest(unittest.TestCase):
    def test_temporary_ids_and_evaluation_fields_ignored(self):
        a = action_key(0, power("c3"), STAGES, meaning())
        b = action_key(0, {**power("c9"), "processability": "unverified", "reasons": []}, STAGES,
                       [{"stage": 1, "option": {"pokemon": 1}}, {"stage": 2, "option": {"pokemon": 2, "processability": "supported"}}])
        self.assertEqual(a, b)

    def test_target_input_actor_distinguished(self):
        base = action_key(0, power(), STAGES, meaning())
        self.assertNotEqual(base, action_key(0, power(), STAGES, meaning(target=3)))  # 対象が違う
        self.assertNotEqual(base, action_key(0, power(pokemon=8), STAGES, meaning()))  # 使うポケモンが違う
        self.assertNotEqual(base, action_key(1, power(), STAGES, meaning()))  # 主体が違う
        self.assertNotEqual(base, action_key(0, power(), STAGES, meaning(source=2, target=1)))  # 往復の逆向きは別

    def test_order_significance(self):
        sig = [{"stage": 1, "order": "significant"}]
        x = [{"stage": 1, "option": {"card": 1}}, {"stage": 1, "option": {"card": 2}}]
        y = list(reversed(x))
        self.assertNotEqual(action_key(0, power(), sig, x), action_key(0, power(), sig, y))  # 意味のある順序は区別する
        free = [{"stage": 1, "order": "not_significant"}]
        self.assertEqual(action_key(0, power(), free, x), action_key(0, power(), free, y))  # 意味のない並びは区別しない
        self.assertEqual(action_key(0, power(), STAGES, meaning(extra=(5, 6))), action_key(0, power(), STAGES, meaning(extra=(6, 5))))


def v2(seed="s"):
    policy = RulePolicy(seed, version=2)
    policy.begin_episode()
    return policy


class ThresholdTest(unittest.TestCase):
    def test_before_and_after_threshold(self):
        policy = v2()
        key = action_key(0, power(), STAGES, meaning())
        self.assertEqual(policy.review(power(), key, TURN_A)["reason"], "below_threshold")  # 0 回
        policy.observe_accepted(TURN_A, key)
        self.assertTrue(policy.review(power(), key, TURN_A)["send"])  # 1 回
        policy.observe_accepted(TURN_A, key)
        verdict = policy.review(power(), key, TURN_A)  # 2 回: 抑える
        self.assertEqual((verdict["send"], verdict["reason"], verdict["accepted_this_turn"]), (False, "repeat_suppressed", 2))
        other = action_key(0, power(), STAGES, meaning(target=3))
        self.assertTrue(policy.review(power(), other, TURN_A)["send"])  # 同じ候補でも入力が違えば別に数える

    def test_turn_change_resets(self):
        policy = v2()
        key = action_key(0, power(), STAGES, meaning())
        policy.observe_accepted(TURN_A, key)
        policy.observe_accepted(TURN_A, key)
        self.assertFalse(policy.review(power(), key, TURN_A)["send"])
        self.assertEqual(policy.review(power(), key, TURN_B)["reason"], "below_threshold")

    def test_demote_then_end_turn_and_no_alternative(self):
        policy = v2()
        key = action_key(0, power(), STAGES, meaning())
        for _ in range(2):
            policy.observe_accepted(TURN_A, key)
        items = [end_turn(), power()]
        self.assertEqual(policy.choose("candidate", items, {})[1], "rule2:priority5:use_power")
        self.assertEqual(policy.review(power(), key, TURN_A)["reason"], "repeat_suppressed")
        self.assertEqual(policy.review(power(), key, TURN_A)["reason"], "repeat_suppressed:candidate_demoted")  # 同じエピソードで 2 回
        self.assertIn(candidate_identity(power()), policy.memory.demoted)
        self.assertEqual(policy.choose("candidate", items, {}), (0, "rule2:priority6:end_turn"))  # end_turn へ進む
        self.assertEqual(policy.choose("candidate", [power()], {}), (0, "rule2:demoted:priority7:use_power"))  # 下げた候補しかない
        self.assertEqual(policy.review(power(), key, TURN_A)["reason"], "rule2:no_alternative")
        policy.begin_episode()  # 新しいエピソードでは下げた候補を戻す（受理の履歴は番のあいだ残る）
        self.assertEqual(policy.choose("candidate", items, {})[1], "rule2:priority5:use_power")
        self.assertFalse(policy.review(power(), key, TURN_A)["send"])

    def test_end_turn_and_unprioritized_never_suppressed(self):
        policy = v2()
        for cand in (end_turn(), {"id": "c1", "kind": "answer_decision"}):
            key = action_key(0, cand, [], [])
            for _ in range(3):
                policy.observe_accepted(TURN_A, key)
            self.assertTrue(policy.review(cand, key, TURN_A)["send"])

    def test_rules_v1_never_suppresses(self):
        policy = RulePolicy("s")
        key = action_key(0, power(), STAGES, meaning())
        for _ in range(5):
            policy.observe_accepted(TURN_A, key)
        self.assertEqual(policy.review(power(), key, TURN_A), {"send": True, "reason": "no_review"})
        self.assertEqual(policy.choose("candidate", [end_turn(), power()], {})[1], "rule:priority5:use_power")


class MixedTest(unittest.TestCase):
    def test_random_side_not_suppressed_but_updates_history(self):
        policy = MixedPolicy(player_seed(13, 0), epsilon=1.0, mix_seed_text="m", rule_version=2)
        key = action_key(0, power(), STAGES, meaning())
        self.assertEqual(policy.begin_episode()["mode"], "random")
        for _ in range(3):
            policy.observe_accepted(TURN_A, key)
        self.assertEqual(policy.review(power(), key, TURN_A), {"send": True, "reason": "random_side"})
        policy.epsilon = 0.0  # 次のエピソードはルールの側
        self.assertEqual(policy.begin_episode()["mode"], "rule")
        verdict = policy.review(power(), key, TURN_A)
        self.assertEqual((verdict["send"], verdict["accepted_this_turn"]), (False, 3))  # ランダムの側の受理が履歴にある
        self.assertEqual((policy.rules_version, policy.distribution), (2, "mixed(rules-v2|uniform-candidate)+uniform-stage"))


def small(**kw):
    limits = kw.pop("limits", {})
    return V.Config(game_seed=13, policy_seed=13, host_seed=13, limits=V.Limits(**{"operations": 300, "seconds": 60, **limits}), **kw)


class RunnerTest(unittest.TestCase):
    def test_rules_v2_game_records_suppression(self):
        runner = V.Runner(small(policy="rules", rules_version=2))
        result = runner.run()
        suppressed = [e for e in result["trace"] if e.get("build") == "suppressed_by_policy"]
        self.assertTrue(suppressed)
        self.assertEqual(result["counters"]["policy_suppressed"], len(suppressed))
        for e in suppressed:
            self.assertFalse(e["policy_review"]["send"])
            self.assertNotIn("check", e)  # 送らない（check も呼ばない）
            self.assertNotIn("submit", e)
        for kind, k in result["metrics"]["kinds"].items():
            self.assertEqual(k["check_valid"] + k["check_invalid"], k["build_ok"] - k["already_tried"] - k["policy_suppressed"], kind)
            self.assertEqual(k["submitted"], k["check_valid"], kind)
        self.assertEqual(result["policies"]["0"]["repeat_threshold"], 2)
        self.assertEqual((result["policies"]["0"]["name"], result["policies"]["0"]["version"]), ("rules", 2))

    def test_only_acceptance_updates_history(self):
        refused = {"ok": True, "outcome": "refused", "refusal": {"code": "CANDIDATE_INPUT_INVALID"}, "result": None, "refetch_required": False}

        def wrap(actor, endpoint):
            class Faulty:
                def handle(self, request):
                    return dict(refused) if request["type"] == "submit" else endpoint.handle(request)
            return Faulty() if actor in (0, 1) else endpoint
        runner = V.Runner(small(policy="rules", rules_version=2), wrap_endpoint=wrap)
        result = runner.run()
        self.assertEqual(result["termination"]["class"], V.NO_PROGRESS)  # 抑える対象がなくても上限で終わる
        self.assertEqual(sum(sum(p.memory.counts.values()) for p in (runner.policies[0], runner.policies[1])), 0)

    def test_suppression_only_case_ends_within_limits(self):
        """偽物の check（いつも invalid）でも、rules-v2 は選び直しの上限の中で止まる（無制限に引き直さない）。"""
        def wrap(actor, endpoint):
            class Faulty:
                def handle(self, request):
                    if request["type"] == "check":
                        return {"ok": True, "response": {"valid": False, "refusal": {"code": "TEST"}}}
                    return endpoint.handle(request)
            return Faulty() if actor in (0, 1) else endpoint
        result = V.run_game(small(policy="mixed", rules_version=2), wrap_endpoint=wrap)
        self.assertEqual(result["termination"]["class"], V.NO_PROGRESS)
        self.assertLessEqual(result["termination"]["detail"].get("draws", 0), V.Limits().draws_per_position)

    def test_repetition_summary_counts_turns(self):
        result = V.run_game(small(policy="rules", limits={"operations": 200}))  # rules-v1: 反復が起きる条件（V2 の rules-s13）
        rep = result["repetition"]
        self.assertGreater(rep["max_same_action_per_turn"], 2)
        self.assertGreater(rep["accepted_power_uses"].get("エナジートランス", 0), 0)
        again = __import__("tools.verification_ai.metrics", fromlist=["x"]).repetition_summary(
            json.loads(json.dumps(result["trace"])), {str(k): v for k, v in json.loads(json.dumps({str(k): v for k, v in result["actor_logs"].items()})).items()})
        self.assertEqual(again, rep)  # 保存した記録（JSON）からの数え直しと同じ


class ReproduceHeaderTest(unittest.TestCase):
    def test_reproduce_reads_mixed_rules_v2_header(self):
        import tempfile
        from pathlib import Path

        from tools.verification_ai import run_v1

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = small(policy="mixed", rules_version=2, epsilon=0.25, limits={"operations": 60}, run_id="base-a")
            result = V.run_game(config)
            base = root / "verifier" / "runs" / "base" / "a"
            header = run_v1.game_header(config, R.identity(None), [], result, "t0", "t1")
            self.assertEqual((header["policy"], header["epsilon"], header["rules_version"], header["repeat_threshold"]), ("mixed", 0.25, 2, 2))
            run_v1.write_game(base, header, result, {})
            self.assertEqual(run_v1.reproduce(base, root, "test", [], "t"), 0)


GAMES = {  # 上限 80 の操作の小さな対戦（V2 の補完の前から同じ 4 つ）
    "uniform-stage-s12": dict(policy="uniform"),
    "uniform-tuple-s12": dict(policy="uniform", distribution=TUPLE),
    "rules-v1-s13": dict(policy="rules"),
    "mixed-v1-s13": dict(policy="mixed", epsilon=0.25),
}
# 旧形式 meaning/v1（行動と API の契約の値が 1 行に混ざる）の指紋。V2 の補完の前のコード（1aad030）で取り、1c0fc07（エンジン 0.175.0）でも同じ値だった。
# 0.176.0（PT-5e）で play_trainer の保証の文（preconditions）が変わり、行動・入力・結果は同じまま、この指紋だけが変わった（docs/verification-ai-v0176-follow.md 2 章）。
# 来歴として残し、今のコードとは比べない（下の新しい形式の値と同じ意味の値として比べない）
LEGACY_MEANING_V1_AT_0175 = {
    "uniform-stage-s12": (87, "1d6b14f228b135084715eaf1267ecbdb4dfe18bd857541b61a89682505f7c048"),
    "uniform-tuple-s12": (88, "7431e4966a9568d1060f4b04998189b4ae0c7444cdf0e9a4397769f09ecf47ed"),
    "rules-v1-s13": (106, "7219cde8295951e4ad4ad834c400fc3c8ba597ccc90f59876715539b9b3243ca"),
    "mixed-v1-s13": (96, "f1862fa778d3be376cfb188e9274cb7c78e42ad13694e8ddc3573cda15f4dbe5"),
}
# 行動の列（形式 action-meaning/v2）。1c0fc07（0.175.0）と 0.176.0 で同じ値（行の数も旧形式と同じ）。方策・入力生成・乱数・エンジンの結果が変われば変わる
ACTION_GOLDEN = {
    "uniform-stage-s12": (87, "36167caf044bace0d2f0c74e663621f66b8a4cbeb707de6d052fdb9fd3492240"),
    "uniform-tuple-s12": (88, "24144fc4789aebdb387c3f1736ceae3a3e7540e3d7a5daf7268a6c6a0de02e3d"),
    "rules-v1-s13": (106, "41f4ca027c16bedf30a09745e04f4c7778f416494fd1bbe1570b43a1448fdd4e"),
    "mixed-v1-s13": (96, "3cca650466f3c0c02af7a24fe53e28e7e746b6237bd8a3e32581c317b07274cd"),
}
# API の契約の値の列（形式 candidate-contract/v1）。エンジン 0.176.0 の値（0.175.0 との差は play_trainer の preconditions の文だけ）。
# エンジンの契約の値（保証の文・処理可能性・理由・段の制約など）が変われば変わる。変わったら差を調べ、来歴つきで更新する（一括で更新しない）
CONTRACT_GOLDEN_0176 = {
    "uniform-stage-s12": (87, "0316ba75ecf78a08fd415d3c126733541ebf76365b1f4385d660e43eb3afb4f8"),
    "uniform-tuple-s12": (88, "b1fb93db141b49b79bdccb2918ddf679f17886fa4434d7178061322837ba92e9"),
    "rules-v1-s13": (106, "19e3c47021bb21ffbdaac7b734e5103e29d765025e4c343c96794431970b959e"),
    "mixed-v1-s13": (96, "2c82ac33c32ef412e6f4e897a337669789a48b9b75ae8078df7a2df4eaa1fc19"),
}


class UnchangedTest(unittest.TestCase):
    def test_existing_policies_keep_their_sequences(self):
        """行動の列と契約の値の列を、別の指紋で照らす（形式の名前つき）。check を経ない送信がないことも確かめる。"""
        for name, kw in GAMES.items():
            with self.subTest(name):
                seed = int(name[-2:])
                result = V.run_game(V.Config(game_seed=seed, policy_seed=seed, host_seed=seed, limits=V.Limits(operations=80, seconds=60), **kw))
                action = R.sequence_digest(R.action_sequence(result["trace"]), R.ACTION_FORMAT)
                contract = R.sequence_digest(R.contract_sequence(result["trace"]), R.CONTRACT_FORMAT)
                self.assertEqual((action["format"], action["length"], action["sha256"]), (R.ACTION_FORMAT, *ACTION_GOLDEN[name]))
                self.assertEqual((contract["format"], contract["length"], contract["sha256"]), (R.CONTRACT_FORMAT, *CONTRACT_GOLDEN_0176[name]))
                self.assertEqual(len(R.meaning_sequence(result["trace"])), LEGACY_MEANING_V1_AT_0175[name][0])  # 行の数は旧形式と同じ（指紋は比べない）
                for e in result["trace"]:
                    if e.get("type") == "attempt" and e.get("submit") is not None:
                        self.assertIs(((e.get("check") or {}).get("response") or {}).get("valid"), True, e.get("n"))  # check を経ない送信がない

    def test_legacy_fingerprints_are_kept_as_history(self):
        """旧形式の指紋は形式の名前と版を分けて残す（新しい形式の値と同じ集合に入れない）。"""
        for name in GAMES:
            self.assertNotEqual(LEGACY_MEANING_V1_AT_0175[name][1], ACTION_GOLDEN[name][1])
            self.assertNotEqual(LEGACY_MEANING_V1_AT_0175[name][1], CONTRACT_GOLDEN_0176[name][1])
        self.assertEqual((R.LEGACY_MEANING_FORMAT, R.ACTION_FORMAT, R.CONTRACT_FORMAT), ("meaning/v1", "action-meaning/v2", "candidate-contract/v1"))


if __name__ == "__main__":
    unittest.main()
