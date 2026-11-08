"""検証用 AI の P6 の追従（docs/verification-ai-p6.md）: 本人のうらのバトル場のポケモンのにげるの入力（段の cost_evaluation）。

- ContractTest: 小さな JSON の例で、0 枚・1 枚・複数枚の選択、選んだ順の保持、total_units・units を求めない・推測しないこと、矛盾・知らない cost_evaluation と
  不正な省略で止まること（uniform-stage と uniform-tuple の両方）、uniform-tuple の既知の小さな集合と上限、おもてのにげるの扱いの保持、check のない送信がないこと
- InfoBoundaryTest: 本当のカードだけが違う構築盤面で、同じ公開の入力契約から同じ入力を作ること。本人の観測には real があり、行動生成はそれを使わないこと。方策に完全な状態を
  渡さないこと
- JudgeTest: 規則 4 の P6 の拒否・受理の分け方。cost_evaluation のない送信は規則 3 のまま
- RunCaseTest: 3 つの構築盤面を、共通の行動生成・check・submit で通す（受理・エネルギー不足の拒否と無副作用と取っ手・トラッシュと受理のあとの決定）
"""

from __future__ import annotations

import copy
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from tools.verification_ai import actions as B
from tools.verification_ai import fixtures_p6 as F
from tools.verification_ai import judge as J
from tools.verification_ai import run_p6
from tools.verification_ai.policies import TUPLE, BoundaryPolicy, MixedPolicy, RulePolicy, UniformPolicy
from tools.verification_ai.runner import SubmitWithoutCheck, submit_checked

FD = "face_down_reveal_not_evaluated"
COST = {"status": "not_evaluated", "reason": FD, "omitted": ["total_units", "units"]}
RETREAT = {"candidate": {"kind": "retreat"}}
REQ = {"contract": "kyuura-client-api", "format": 1}


def bench():
    return {"stage": 1, "input": "choose_option", "role": "new_active", "meaning": "pokemon", "count": {"min": 1, "max": 1}, "order": "not_applicable",
            "options": [{"id": "o1", "pokemon": 1, "card": 0, "zone": "bench", "bench_index": 0, "card_id": "X", "eligible": True, "processability": "unverified",
                         "reasons": [FD]}]}


def discard(n, **extra):
    stage = {"stage": 2, "input": "choose_option", "role": "discard", "meaning": "card", "count": {"min": 0, "max": n}, "distinct": True, "order": "significant",
             "order_preserved": True, "note": "…",
             "options": [{"id": f"o{2 + i}", "card": 10 + i, "card_id": "E", "special": False, "eligible": True, "processability": "unverified", "reasons": [FD]}
                         for i in range(n)]}
    stage["cost_evaluation"] = copy.deepcopy(COST)
    stage.update(extra)
    return stage


def p6(n=2):
    return [bench(), discard(n)]


def tuples(stages, **kw):
    return [c for c, _m in B.enumerate_inputs(stages, B.FALLBACK_PROCESSABILITY, kind="retreat", **kw)]


class ContractTest(unittest.TestCase):
    def test_zero_one_many_and_order(self):
        seen = set()
        for seed in range(80):
            choices, _picks, _m = B.build_choices(p6(), UniformPolicy(f"p6-{seed}"), RETREAT, B.FALLBACK_PROCESSABILITY)
            self.assertEqual(choices[0], "o1")
            seen.add(tuple(choices))
        self.assertEqual(seen, {("o1",), ("o1", "o2"), ("o1", "o3"), ("o1", "o2", "o3"), ("o1", "o3", "o2")})  # 0・1・2 枚、選んだ順のどちらも
        choices, picks, _m, method = B.build_choices_tuple(p6(), UniformPolicy("p6-t", TUPLE), RETREAT, B.FALLBACK_PROCESSABILITY)
        self.assertEqual(method, {"method": "tuple", "tuples": 5})

    def test_tuple_known_set_and_limit(self):
        self.assertEqual(tuples(p6()), [["o1"], ["o1", "o2"], ["o1", "o3"], ["o1", "o2", "o3"], ["o1", "o3", "o2"]])  # 並びは別の組（order significant）
        self.assertEqual(tuples(p6(0)), [["o1"]])  # ついているカードがない: 0 枚だけ
        with self.assertRaises(B.TupleLimit):
            tuples(p6(), limit=2)
        _c, _p, _m, method = B.build_choices_tuple(p6(), UniformPolicy("p6-l", TUPLE), RETREAT, B.FALLBACK_PROCESSABILITY, limit=2)
        self.assertEqual((method["method"], method["reason"]), ("stage_fallback", "tuple_limit"))

    def test_units_are_not_required_or_guessed(self):
        stages = p6(3)
        self.assertFalse(any("units" in o for s in stages for o in s["options"]))
        self.assertEqual(len(tuples(stages)), 1 + 3 + 6 + 6)  # 個数・費用で絞らない（0〜3 枚のすべての並び）

    def test_bad_cost_evaluation_stops(self):
        bad = {
            "status": {**COST, "status": "evaluated"}, "reason": {**COST, "reason": "other"}, "omitted_short": {**COST, "omitted": ["total_units"]},
            "omitted_order": {**COST, "omitted": ["units", "total_units"]}, "extra_key": {**COST, "basis": "x"}, "not_dict": "not_evaluated",
        }
        cases = {name: [bench(), discard(2, cost_evaluation=value)] for name, value in bad.items()}
        cases["with_total_units"] = [bench(), discard(2, total_units={"min": 1, "max": 1})]
        with_units = [bench(), discard(2)]
        with_units[1]["options"][0]["units"] = 1
        cases["with_units"] = with_units
        value_stage = {"stage": 1, "input": "choose_value", "count": {"min": 1, "max": 1}, "range": {"min": 0, "max": 1}, "cost_evaluation": dict(COST)}
        cases["on_value_stage"] = [value_stage]
        no_cost = [bench(), discard(2)]
        del no_cost[1]["cost_evaluation"]
        cases["retreat_discard_without_cost_or_total_units"] = no_cost
        units_only = [bench(), discard(2)]
        del units_only[1]["cost_evaluation"]
        units_only[1]["options"][0]["units"] = 1
        cases["units_without_total_units"] = units_only
        for name, stages in cases.items():
            with self.subTest(name):
                with self.assertRaises(B.ContractUnknown):
                    B.build_choices(stages, UniformPolicy("x"), RETREAT, B.FALLBACK_PROCESSABILITY)
                with self.assertRaises(B.ContractUnknown):
                    B.enumerate_inputs(stages, B.FALLBACK_PROCESSABILITY, kind="retreat")
        # 候補の種類が分からない呼び出しでは、「にげるのトラッシュの段で total_units も cost_evaluation もない」だけは確かめられない（文書の制限）
        self.assertEqual(B.build_choices(no_cost, UniformPolicy("x"), {}, B.FALLBACK_PROCESSABILITY)[0][0], "o1")

    def test_face_up_retreat_is_unchanged(self):
        face_up = [bench(), {"stage": 2, "input": "choose_option", "role": "discard", "meaning": "card", "count": {"min": 0, "max": 2}, "distinct": True,
                             "order": "significant", "order_preserved": True, "total_units": {"min": 1, "max": 1},
                             "options": [{"id": "o2", "card": 10, "card_id": "E", "special": False, "units": 1, "processability": "unverified"},
                                         {"id": "o3", "card": 11, "card_id": "E", "special": False, "units": 1, "processability": "unverified"}]}]
        self.assertEqual(tuples(face_up), [["o1", "o2"], ["o1", "o3"]])  # 個数の合計で絞る（従来どおり）
        choices, picks, _m = B.build_choices(face_up, UniformPolicy("u"), RETREAT, B.FALLBACK_PROCESSABILITY)
        self.assertEqual(len(choices), 2)
        self.assertIn("units_set", [p["purpose"] for p in picks])

    def test_deep_does_not_take_unverified(self):
        with self.assertRaises(B.Unbuildable):
            B.build_choices(p6(), UniformPolicy("d"), RETREAT, B.DEEP_PROCESSABILITY)  # deep の範囲は広げていない（boundary・代替だけ）

    def test_all_policies_use_the_same_generator(self):
        for policy in (UniformPolicy("s"), RulePolicy("s"), RulePolicy("s", version=2), MixedPolicy("s", epsilon=0.25, mix_seed_text="m"), BoundaryPolicy("s")):
            with self.subTest(policy.distribution):
                policy.begin_episode()  # 混合の方策は、エピソードを始めてから選ぶ（ランナーと同じ順）
                choices, _p, _m = B.build_choices(p6(), policy, RETREAT, B.FALLBACK_PROCESSABILITY)
                self.assertIn(tuple(choices), {tuple(t) for t in tuples(p6())})

    def test_no_submit_without_valid_check(self):
        handle = {"game": "g", "revision": "r", "candidate": "c2"}
        for checked in (None, {"response": {"valid": False}, "_handle": handle, "_choices": ["o1"]},
                        {"response": {"valid": True}, "_handle": handle, "_choices": ["o1", "o2"]}):
            with self.assertRaises(SubmitWithoutCheck):
                submit_checked(None, handle, ["o1"], checked, operation_id="x")


class SpyPolicy(UniformPolicy):
    def __init__(self, seed):
        super().__init__(seed)
        self.contexts = []

    def choose(self, purpose, items, context):
        self.contexts.append(sorted(context))
        return super().choose(purpose, items, context)


class InfoBoundaryTest(unittest.TestCase):
    def own(self, fixture_id):
        state, _record = F.build(fixture_id)
        hub = ClientHub(A.HostedGame(state))
        me = hub.player(0)
        cands = me.handle({**REQ, "type": "candidates"})["response"]
        candidate = next(c for c in cands["candidates"] if c["kind"] == "retreat")
        stages = me.handle({**REQ, "type": "inputs", "game": cands["game"], "revision": cands["revision"], "candidate": candidate["id"]})["response"]["stages"]
        view = me.handle({**REQ, "type": "view"})
        return candidate, stages, view

    def test_same_public_contract_gives_the_same_inputs(self):
        rows = [self.own(f) for f in ("P6A", "P6B", "P6C")]
        reals = [r[2]["observation"]["players"][0]["active"]["real"]["card_id"] for r in rows]
        self.assertEqual(len(set(reals)), 3)  # 本人の観測には本当のカード（real）がある（本人の全知識は同じでない）
        first = rows[0]
        for candidate, stages, view in rows:
            self.assertEqual((candidate, stages), (first[0], first[1]))  # 公開の入力契約は同じ
            self.assertEqual(B.enumerate_inputs(stages, B.FALLBACK_PROCESSABILITY, kind="retreat"),
                             B.enumerate_inputs(first[1], B.FALLBACK_PROCESSABILITY, kind="retreat"))
            for seed in range(5):
                spy = SpyPolicy(f"ib-{seed}")
                got = B.build_choices(stages, spy, {"view": view, "candidate": candidate}, B.FALLBACK_PROCESSABILITY)  # 本人の観測（real つき）を渡しても
                again = B.build_choices(stages, UniformPolicy(f"ib-{seed}"), {"view": first[2], "candidate": candidate}, B.FALLBACK_PROCESSABILITY)
                self.assertEqual(got, again)  # 生成は real に依存しない（同じ種なら同じ選び方）
                self.assertTrue(all(set(keys) <= {"view", "candidate", "stage"} for keys in spy.contexts))  # 方策に渡すのは本人の観測・候補・段だけ（完全な状態はない）


def submit(outcome, code=None, category=None):
    entry = {"ok": True, "outcome": outcome}
    if code is not None:
        entry["verifier"] = {"diagnostic_id": code, "category": category, "engine_code": code}
    return entry


class JudgeTest(unittest.TestCase):
    CAND = {"kind": "retreat", "processability": "unverified", "reasons": [FD]}

    def judge(self, sub, stages=None):
        return J.judge_normal(self.CAND, [], sub, stages=p6() if stages is None else stages)

    def test_version(self):
        self.assertEqual(J.JUDGE_RULES_VERSION, 4)

    def test_p6_rejections(self):
        cat = J._catalog_category
        self.assertEqual(self.judge(submit(D.REJECTED, "WRONG_RETREAT_COST", cat("WRONG_RETREAT_COST")))[0], J.NORMAL_REJECTION)
        for code in ("POKEMON_ASLEEP", "POKEMON_PARALYZED", "RETREAT_PREVENTED"):
            self.assertEqual(self.judge(submit(D.REJECTED, code, cat(code)))[0], J.NORMAL_REJECTION, code)
        for code in ("DUPLICATE_CARD", "ENERGY_NOT_ATTACHED", "NOT_ON_BENCH"):
            self.assertEqual(self.judge(submit(D.REJECTED, code, cat(code)))[0], J.SUSPECT, code)  # API の形の保証と矛盾
        self.assertEqual(self.judge(submit(D.REJECTED, "SOME_NEW_CODE", D.INVALID_INPUT))[0], J.UNDETERMINED)  # 未知の診断
        self.assertEqual(self.judge(submit(D.REJECTED, "WRONG_RETREAT_COST", D.RULING_UNRESOLVED))[0], J.SUSPECT)  # 分類がコード表と違う
        self.assertEqual(self.judge(submit(D.REJECTED, None, D.UNMAPPED))[0], J.SUSPECT)
        self.assertEqual(self.judge({"ok": True, "outcome": D.FAILED})[0], J.SUSPECT)
        self.assertEqual(self.judge({"ok": True, "outcome": "refused", "refusal": {"code": "CANDIDATE_INPUT_INVALID"}})[0], J.SUSPECT)
        self.assertEqual(self.judge(submit(D.ACCEPTED))[0], J.EXPECTED)

    def test_without_cost_evaluation_rule_3_is_unchanged(self):
        face_up = [bench(), {**discard(2), "total_units": {"min": 1, "max": 1}}]
        del face_up[1]["cost_evaluation"]
        for stages in (None, face_up):
            verdict = J.judge_normal(self.CAND, [], submit(D.REJECTED, "DUPLICATE_CARD", J._catalog_category("DUPLICATE_CARD")), stages=stages)
            self.assertEqual(verdict[0], J.NORMAL_REJECTION)  # 規則 3: うらの経路の invalid_input は正常な拒否（cost_evaluation がなければ規則 4 の分けは当てない）

    def test_accepted_kinds(self):
        self.assertEqual(J.judge_p6_accepted(["secret_plan_revealed", "retreat"]), (J.EXPECTED, ["p6_revealed_and_retreated"]))
        self.assertEqual(J.judge_p6_accepted(["secret_plan_revealed", "secret_plan_discarded", "x"])[1], ["p6_revealed_not_basic_and_trashed"])
        for events in ([], ["retreat"], ["secret_plan_revealed"], ["secret_plan_revealed", "retreat", "secret_plan_discarded"]):
            self.assertEqual(J.judge_p6_accepted(events)[0], J.UNDETERMINED, events)


class RunCaseTest(unittest.TestCase):
    def run_spec(self, case_id):
        spec = next(c for c in run_p6.CASES if c["case"] == case_id)
        state, _record = F.build(spec["fixture"])
        text, why = F.snapshot_text(state, spec["fixture"])
        self.assertIsNone(why)
        return run_p6.run_case(spec, text)

    def test_accept(self):
        out = self.run_spec("R1")
        row = out["retreat"]
        self.assertTrue(out["expectation_met"])
        self.assertEqual((row["normal_verdict"][0], row["effects_verdict"][0], row["accepted_verdict"]),
                         (J.EXPECTED, J.EXPECTED, (J.EXPECTED, ["p6_revealed_and_retreated"])))
        self.assertEqual(row["old_handle_check"], L.CANDIDATES_STALE)
        self.assertEqual(row["generated"]["tuples"], 2)  # エネルギー 1 枚: 0 枚・1 枚

    def test_reject_without_side_effects(self):
        out = self.run_spec("R2")
        row = out["retreat"]
        self.assertTrue(out["expectation_met"])
        self.assertEqual(row["normal_verdict"][0], J.NORMAL_REJECTION)
        self.assertEqual((row["changed"], row["effects_verdict"][0]), ([], J.EXPECTED))  # 状態・乱数・ログ・決定・他者への更新が変わらない
        self.assertEqual((row["recovery"]["response"]["valid"], row["recovery_verdict"][0]), (True, J.EXPECTED))  # 同じ取っ手で正常な check に戻れる
        self.assertEqual(row["disclosure"]["before"], row["disclosure"]["after"])  # うらのまま（相手・観戦者に公開されない）

    def test_trash_then_promote(self):
        out = self.run_spec("R3")
        self.assertTrue(out["expectation_met"])
        self.assertEqual(out["retreat"]["accepted_verdict"][1], ["p6_revealed_not_basic_and_trashed"])
        follow = out["follow"]
        self.assertEqual((follow["kinds"], follow["submit"]["outcome"], follow["normal_verdict"][0]), (["promote_active"], D.ACCEPTED, J.EXPECTED))
        self.assertLessEqual(out["requests"], run_p6.MAX_REQUESTS)


if __name__ == "__main__":
    unittest.main()
