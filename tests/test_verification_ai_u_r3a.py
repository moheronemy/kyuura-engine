"""検証用 AI の U-R3a の追従（docs/verification-ai-u-r3a.md）: 本人のうらのカードの、宣言の段が 2〜3 段の特殊能力の入力。

- ContractTest: 小さな JSON の例で、2 段・3 段を uniform-stage・uniform-tuple の両方で作れること、別の経路の番号を混ぜないこと、元の応答を変えないこと、
  入力を返さない候補を送らないこと、check のない送信がないこと、deep の範囲を広げていないこと
- InfoBoundaryTest: 本人の観測以外の完全な状態を方策へ渡さないこと
- JudgeTest: 規則 5（うらのカードの特殊能力の拒否を、元のコードと、条件に要る段が選んだ入力にあることで分ける。受理の中身を公開のログで分ける）。P6（規則 4）・おもての
  特殊能力・ほかの送信の判定は変わらないこと
- RunCaseTest: 3 つの構築盤面（受理・おもてにしたあとの WRONG_ENERGY_TYPE の拒否と無副作用と取っ手・トラッシュ）を、共通の行動生成・check・submit で通す
"""

from __future__ import annotations

import copy
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from tools.verification_ai import actions as B
from tools.verification_ai import fixtures_u_r3a as F
from tools.verification_ai import judge as J
from tools.verification_ai import run_u_r3a
from tools.verification_ai.policies import BoundaryPolicy, MixedPolicy, RulePolicy, UniformPolicy

FD = "face_down_reveal_not_evaluated"
REQ = {"contract": "kyuura-client-api", "format": 1}
CAND = {"kind": "use_power", "processability": "unverified", "reasons": [FD], "input_disclosure": "confirmed",
        "pokemon": {"pokemon": 4, "card": 7, "zone": "bench", "bench_index": 1, "face_down": True},
        "power": {"index": 0, "name_ja": "X", "card": 7, "card_id": "Y", "face_down": True}}
CTX = {"view": None, "candidate": CAND}


def opt(oid, **fields):
    return {"id": oid, **fields, "eligible": True, "processability": "unverified", "reasons": [FD]}


def ref(oid):
    return {"option": oid, "eligible": True, "processability": "unverified", "reasons": [FD]}


def two_stage():
    """source（自分の場 2 匹）→ energy（選んだポケモンについているカード。番号は前の段の選び方ごとに別）。"""
    return [
        {"stage": 1, "input": "choose_option", "role": "source", "meaning": "pokemon", "count": {"min": 1, "max": 1}, "order": "not_applicable", "note": "…",
         "options": [opt("o1", pokemon=1, card=0, zone="active", card_id="A"), opt("o2", pokemon=2, card=3, zone="bench", bench_index=0, card_id="B")]},
        {"stage": 2, "input": "choose_option", "role": "energy", "meaning": "card", "count": {"min": 1, "max": 1}, "order": "not_applicable",
         "depends_on_stage": 1, "upstream_stages": [1], "note": "…",
         "options": [opt("o3", card=1, card_id="F", after="o1"), opt("o4", card=4, card_id="R", after="o2"), opt("o5", card=5, card_id="W", after="o2")],
         "options_by_choice": {"o1": [ref("o3")], "o2": [ref("o4"), ref("o5")]}},
    ]


def three_stage():
    stages = two_stage()
    targets = []
    by: dict[str, list] = {}
    n = 6
    for parent in ("o3", "o4", "o5"):
        for pokemon in (1, 2):
            oid = f"o{n}"
            targets.append(opt(oid, pokemon=pokemon, card=0 if pokemon == 1 else 3, zone="active" if pokemon == 1 else "bench", card_id="A" if pokemon == 1 else "B",
                               after=parent))
            by.setdefault(parent, []).append(ref(oid))
            n += 1
    stages.append({"stage": 3, "input": "choose_option", "role": "target", "meaning": "pokemon", "count": {"min": 1, "max": 1}, "order": "not_applicable",
                   "depends_on_stage": 2, "upstream_stages": [1, 2], "note": "…", "options": targets, "options_by_choice": by})
    return stages


def tuples(stages):
    return [tuple(c) for c, _m in B.enumerate_inputs(stages, B.FALLBACK_PROCESSABILITY, kind="use_power")]


def valid_paths(stages):
    """契約の参照（options_by_choice と after）だけから作る、完成した組の集合（試験側の参照）。"""
    paths = [(o["id"],) for o in stages[0]["options"]]
    for stage in stages[1:]:
        by_id = {o["id"]: o for o in stage["options"]}
        paths = [p + (r["option"],) for p in paths for r in stage["options_by_choice"].get(p[-1], []) if by_id[r["option"]]["after"] == p[-1]]
    return set(paths)


class ContractTest(unittest.TestCase):
    def test_two_and_three_stages_in_both_distributions(self):
        for stages in (two_stage(), three_stage()):
            with self.subTest(n=len(stages)):
                original = copy.deepcopy(stages)
                expected = valid_paths(stages)
                self.assertEqual(set(tuples(stages)), expected)  # uniform-tuple: 別の経路の番号を混ぜない（参照の組だけ）
                self.assertEqual(len(tuples(stages)), len(expected))
                seen = set()
                for seed in range(60):
                    choices, _p, meaning = B.build_choices(stages, UniformPolicy(f"s{seed}"), CTX, B.FALLBACK_PROCESSABILITY)
                    self.assertIn(tuple(choices), expected)  # uniform-stage も同じ集合の中
                    self.assertEqual([m["stage"] for m in meaning], list(range(1, len(stages) + 1)))
                    seen.add(tuple(choices))
                self.assertEqual(seen, expected)  # どの組も選ばれうる
                self.assertEqual(stages, original)  # 元の応答を変えない
        self.assertEqual(len(tuples(three_stage())), 6)

    def test_all_policies_use_the_same_generator(self):
        stages = three_stage()
        for policy in (UniformPolicy("s"), RulePolicy("s"), RulePolicy("s", version=2), MixedPolicy("s", epsilon=0.25, mix_seed_text="m"), BoundaryPolicy("s")):
            with self.subTest(policy.distribution):
                policy.begin_episode()
                choices, _p, _m = B.build_choices(stages, policy, CTX, B.FALLBACK_PROCESSABILITY)
                self.assertIn(tuple(choices), valid_paths(stages))

    def test_deep_does_not_take_unverified(self):
        with self.assertRaises(B.Unbuildable):
            B.build_choices(two_stage(), UniformPolicy("d"), CTX, B.DEEP_PROCESSABILITY)  # deep の範囲は広げていない（boundary・代替だけ）

    def test_withheld_candidate_is_not_sent(self):
        """組が完成しない盤面（R-3 のまま）: inputs は withheld で、submit は断られ、エンジンに渡らない。"""
        from tests import test_secret_plan_v0_67 as S
        from tests import helpers as H

        state = S.place(S.board(hand=(H.ROCKET_CHARMANDER,), active={"card": H.HITMONCHAN, "energy": []}), H.ROCKET_CHARMANDER)
        hub = ClientHub(A.HostedGame(state))
        me = hub.player(0)
        cands = me.handle({**REQ, "type": "candidates"})["response"]
        c = next(c for c in cands["candidates"] if c["kind"] == "use_power" and c["power"].get("face_down"))
        self.assertEqual((c["input_disclosure"], c["input_stages"]), (L.DISCLOSURE_UNCONFIRMED, []))  # 入力非公開: 生成の対象外（ランナーは withheld で止める）
        handle = {"game": cands["game"], "revision": cands["revision"], "candidate": c["id"]}
        self.assertIn("withheld", me.handle({**REQ, "type": "inputs", **handle})["response"])
        sent = me.handle({**REQ, "type": "submit", **handle, "choices": []})
        self.assertEqual(sent["outcome"], L.REFUSED)


class SpyPolicy(UniformPolicy):
    def __init__(self, seed):
        super().__init__(seed)
        self.contexts = []

    def choose(self, purpose, items, context):
        self.contexts.append(sorted(context))
        return super().choose(purpose, items, context)


class InfoBoundaryTest(unittest.TestCase):
    def test_policy_sees_only_the_owner_contract(self):
        state, _record = F.build("UR3A-RC")
        hub = ClientHub(A.HostedGame(state))
        me = hub.player(0)
        cands = me.handle({**REQ, "type": "candidates"})["response"]
        candidate = next(c for c in cands["candidates"] if J.is_face_down_power(c))
        stages = me.handle({**REQ, "type": "inputs", "game": cands["game"], "revision": cands["revision"], "candidate": candidate["id"]})["response"]["stages"]
        view = me.handle({**REQ, "type": "view"})
        spy = SpyPolicy("ib")
        got = B.build_choices(stages, spy, {"view": view, "candidate": candidate}, B.FALLBACK_PROCESSABILITY)
        self.assertEqual(got, B.build_choices(stages, UniformPolicy("ib"), {"view": None, "candidate": candidate}, B.FALLBACK_PROCESSABILITY))  # 観測によらない
        self.assertTrue(all(set(keys) <= {"view", "candidate", "stage"} for keys in spy.contexts))  # 完全な状態を渡さない


def submit(outcome, code=None, category=None):
    entry = {"ok": True, "outcome": outcome}
    if code is not None:
        entry["verifier"] = {"diagnostic_id": code, "category": category, "engine_code": code}
    return entry


def meaning(*roles_stages):
    return [{"stage": n, "option": {}} for n in roles_stages]


class JudgeTest(unittest.TestCase):
    def judge(self, sub, chosen=(1, 2), stages=None, candidate=CAND):
        return J.judge_normal(candidate, meaning(*chosen), sub, stages=two_stage() if stages is None else stages)

    def test_version(self):
        self.assertEqual(J.JUDGE_RULES_VERSION, 7)  # 規則 6（C1 の確認）・規則 7（LOST_TARGET の P1。うらの使い手は対象外）は規則 5 の中身を変えていない

    def test_face_down_power_rejections(self):
        cat = J._catalog_category
        verdict = self.judge(submit(D.REJECTED, "WRONG_ENERGY_TYPE", cat("WRONG_ENERGY_TYPE")))
        self.assertEqual(verdict[0], J.NORMAL_REJECTION)
        self.assertIn("face_down_power_engine_decides_after_reveal", verdict[1])
        self.assertEqual(self.judge(submit(D.REJECTED, "SAME_POKEMON", cat("SAME_POKEMON")))[0], J.NORMAL_REJECTION)
        # 条件に要る段を選んでいない（エネルギーの段がない入力でタイプの拒否）: 説明できないので undetermined
        self.assertEqual(self.judge(submit(D.REJECTED, "WRONG_ENERGY_TYPE", cat("WRONG_ENERGY_TYPE")), chosen=(1,), stages=two_stage()[:1])[0], J.UNDETERMINED)
        for code in ("POWER_CHOICE_MISSING", "POWER_CHOICE_NOT_USED", "ENERGY_NOT_ATTACHED", "NOT_YOUR_TURN", "DECISION_PENDING"):
            self.assertEqual(self.judge(submit(D.REJECTED, code, cat(code)))[0], J.SUSPECT, code)  # 構造の保証と矛盾
        self.assertEqual(self.judge(submit(D.REJECTED, "SOME_NEW_CODE", D.INVALID_INPUT))[0], J.UNDETERMINED)  # 未知の診断
        self.assertEqual(self.judge(submit(D.REJECTED, "CARD_NOT_IN_HAND", cat("CARD_NOT_IN_HAND")))[0], J.UNDETERMINED)  # コード表にあるだけでは正常としない
        self.assertEqual(self.judge(submit(D.REJECTED, "WRONG_ENERGY_TYPE", D.RULING_UNRESOLVED))[0], J.SUSPECT)  # 分類がコード表と違う
        self.assertEqual(self.judge(submit(D.REJECTED, None, D.UNMAPPED))[0], J.SUSPECT)
        self.assertEqual(self.judge({"ok": True, "outcome": D.FAILED})[0], J.SUSPECT)
        self.assertEqual(self.judge({"ok": True, "outcome": "refused", "refusal": {"code": "CANDIDATE_INPUT_INVALID"}})[0], J.SUSPECT)
        self.assertEqual(self.judge(submit(D.REJECTED, "SOME_STOP", D.UNSUPPORTED))[0], J.UNDETERMINED)  # 停止系: 根拠がなければ known_stop にしない
        self.assertEqual(self.judge(submit(D.ACCEPTED))[0], J.EXPECTED)

    def test_other_paths_are_unchanged(self):
        face_up = {**CAND, "processability": "may_stop_later", "reasons": ["continuation_not_evaluated"],
                   "pokemon": {"pokemon": 1, "card": 0, "zone": "active", "card_id": "A"}, "power": {"index": 0, "name_ja": "X", "card": 0, "card_id": "A"}}
        self.assertFalse(J.is_face_down_power(face_up))
        verdict = J.judge_normal(face_up, meaning(1, 2), submit(D.REJECTED, "CARD_NOT_IN_HAND", J._catalog_category("CARD_NOT_IN_HAND")), stages=two_stage())
        self.assertEqual(verdict[0], J.NORMAL_REJECTION)  # おもての特殊能力は規則 4 のまま（規則 5 は当てない）
        p6 = {"kind": "retreat", "processability": "unverified", "reasons": [FD]}
        cost = {"status": "not_evaluated", "reason": FD, "omitted": ["total_units", "units"]}
        p6_stages = [{"stage": 1, "role": "new_active", "options": []}, {"stage": 2, "role": "discard", "cost_evaluation": cost, "options": []}]
        self.assertEqual(J.judge_normal(p6, [], submit(D.REJECTED, "WRONG_RETREAT_COST", J._catalog_category("WRONG_RETREAT_COST")), stages=p6_stages)[0],
                         J.NORMAL_REJECTION)  # P6（規則 4）は変わらない

    def test_accepted_kinds_from_public_log(self):
        rev = {"kind": "secret_plan_revealed", "pokemon_id": 4, "card_id": "Y"}
        used = {"kind": "pokemon_power", "pokemon_id": 4}
        gone = {"kind": "secret_plan_discarded", "pokemon_id": 4}
        self.assertEqual(J.judge_face_down_power_accepted(CAND, [rev, used, {"kind": "move_energy"}]), (J.EXPECTED, ["face_down_power_revealed_and_used", "revealed:Y"]))
        self.assertEqual(J.judge_face_down_power_accepted(CAND, [rev, gone])[1][0], "face_down_power_revealed_not_basic_and_trashed")
        for events in ([], [used], [rev], [rev, used, gone], [{**rev, "pokemon_id": 9}, used], [{**rev, "card_id": None}, used],
                       [rev, {"kind": "pokemon_power", "pokemon_id": 9}]):
            self.assertEqual(J.judge_face_down_power_accepted(CAND, events)[0], J.UNDETERMINED, events)  # 確定できなければ未判定


class RunCaseTest(unittest.TestCase):
    def run_spec(self, case_id):
        spec = next(c for c in run_u_r3a.CASES if c["case"] == case_id)
        state, _record = F.build(spec["fixture"])
        text, why = F.snapshot_text(state, spec["fixture"])
        self.assertIsNone(why)
        return run_u_r3a.run_case(spec, text)

    def common(self, out):
        row = out["power"]
        self.assertTrue(out["expectation_met"])
        self.assertTrue(row["stages_unchanged_by_generator"])
        self.assertTrue(row["generated"]["uniform_stage_sample_in_tuples"])
        self.assertEqual(row["check_changed"], [])  # check は状態・更新を変えない
        self.assertLessEqual(out["requests"], run_u_r3a.MAX_REQUESTS)
        return row

    def test_accept_power_used(self):
        row = self.common(self.run_spec("U1"))
        self.assertEqual(row["generated"]["tuples"], 4)
        self.assertEqual((row["normal_verdict"][0], row["effects_verdict"][0], row["accepted_verdict"][1][0]),
                         (J.EXPECTED, J.EXPECTED, "face_down_power_revealed_and_used"))
        self.assertEqual(row["old_handle_check"], L.CANDIDATES_STALE)  # 受理で取っ手は失効
        self.assertEqual(row["public"]["revealed_card_ids"], {"opponent": [F.ROCKET_CHARMANDER], "spectator": [F.ROCKET_CHARMANDER]})
        self.assertFalse(row["public"]["real_in_public_before"])
        self.assertTrue(all(row["delivered_updates"][a] for a in ("1", "spectator")))  # 受理は公開の更新になる

    def test_reject_without_side_effects(self):
        row = self.common(self.run_spec("U2"))
        self.assertEqual((row["normal_verdict"][0], row["submit"]["verifier"]["engine_code"]), (J.NORMAL_REJECTION, "WRONG_ENERGY_TYPE"))
        self.assertEqual((row["changed"], row["effects_verdict"][0]), ([], J.EXPECTED))  # 状態・乱数・ログ・決定・他者への更新が変わらない
        self.assertEqual(row["delivered_updates"], {"1": [], "spectator": []})
        self.assertEqual((row["recovery"]["response"]["valid"], row["recovery_verdict"][0]), (True, J.EXPECTED))  # 同じ取っ手で check に戻れる
        self.assertTrue(all(row["public_unchanged"].values()))
        self.assertFalse(row["public"]["real_in_public_after"])  # 本当のカードは公開されない

    def test_three_stage_trash(self):
        row = self.common(self.run_spec("U3"))
        self.assertEqual(row["generated"]["tuples"], 12)
        self.assertEqual(row["accepted_verdict"][1][0], "face_down_power_revealed_not_basic_and_trashed")
        self.assertEqual(row["public"]["revealed_card_ids"], {"opponent": [F.VENUSAUR], "spectator": [F.VENUSAUR]})
        self.assertIn(F.VENUSAUR, row["public"]["after"]["opponent_discard"])
        self.assertEqual(row["old_handle_check"], L.CANDIDATES_STALE)


if __name__ == "__main__":
    unittest.main()
