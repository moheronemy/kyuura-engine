"""検証用 AI の判定の規則 10（docs/verification-ai-recover-zero-energy-design.md 5 章・8 章）: エナジーへんかんの決定（recover_energy・最小 0）への 0 枚の答えの
UNRESOLVED_RECOVER_ZERO_ENERGY の拒否を、記録した送信の値・送った本人の送信前の観測・決定を出した経路（同じ trace の直前の受理）・専用の basis で、条件 R1〜R11・R13
をすべて確かめ、ほかの根拠の規則が根拠を返さない（R12）ときだけ known_stop にする。ER9（規則 6）とは別の項目・別の関数。

- 人工の送信の行と観測で、正（本人の印刷のワザ・最大 1・ゆびをふるの経路）と負（回答・決定・コード・段・上下限・参照・check・観測・拒否のあと・refused・failed・
  受理のあとの停止・経路・basis・重なり）を確かめる
- 構築盤面（ゴース・ピッピ・ピクシーのゆびをふる。new_game からの対戦ではない）を本物の runner に通し、逐次バッチの入口（``batch.judge_trace``）と単局の runner の判定
  （変異の実行の中）が同じ値になること、保存した形（trace・actors/*.jsonl）から読み直しても同じことを確かめる。メタモンの［へんしん］の経路は対象の外（R13）
"""

from __future__ import annotations

import copy
import json
import unittest
from unittest import mock

from kyuura_engine import diagnostics as D
from kyuura_engine.cards import load_card_pool
from kyuura_engine.effects import DEFAULT_EFFECTS
from kyuura_engine.replay_record import current_identity, implementation_identity, package_files, INSTRUMENTATION_FILES, PACKAGE_ROOT

from tools.verification_ai import batch as B
from tools.verification_ai import fixtures_u_r3a as F
from tools.verification_ai import judge as J
from tools.verification_ai import runner as V
from tools.verification_ai.policies import UniformPolicy

from tests.helpers import CLEFABLE, CLEFAIRY, DITTO, FIRE, GASTLY, GROWLITHE, PSYCHIC, RATTATA, WATER, build_test_state
from tests.test_verification_ai_batch_judge import NoNegative, summary_and_rest
from tests.test_verification_ai_lost_target_p1 import RecordedFixtureRunner

CODE = "UNRESOLVED_RECOVER_ZERO_ENERGY"
ER9 = "UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE"
UNDET = ("undetermined", [f"stop_condition_not_evidenced:{CODE}"])
ACTOR, TURN = 0, 7
USER_CARD, COPIER_CARD = 12, 13
ENERGY_CARDS = (54, 40, 47, 37)


def header():
    pool = load_card_pool()
    return {"engine": dict(current_identity()), "dependencies": {"rules": "JP-2000.02.14", "card_pool": "default", "effects": DEFAULT_EFFECTS.id,
                                                                 "card_data": {k: pool.source[k] for k in ("repository", "commit", "path")}}}


def zone(card=USER_CARD, card_id=GASTLY):
    return {"pokemon_id": 1, "card": card, "card_id": card_id, "damage": 0, "energy": []}


def view(*, phase="decision", decision="default", active=None, turn=TURN, current=ACTOR, viewer=ACTOR, ok=True, cards=ENERGY_CARDS, minimum=0, maximum=2,
         kind="recover_energy"):
    if decision == "default":
        decision = {"kind": kind, "player": ACTOR, "min_choices": minimum, "max_choices": maximum, "option_count": len(cards),
                    "options": [{"value": c, "card_id": PSYCHIC} for c in cards], "meaning": "card"}
    return {"ok": ok, "type": "view", "viewer": viewer, "status": {"segment": 0, "status": "in_progress", "phase": phase},
            "observation": {"viewer": viewer, "current_player": current, "phase": phase, "decision": decision, "turn": turn,
                            "players": [{"player": 0, "active": active or zone(), "bench": []}, {"player": 1, "active": zone(card=70, card_id=GROWLITHE), "bench": []}]}}


def position_row(v, position, episode):
    return {"type": "position", "position": position, "view": v, "episode": {"type": "episode", "episode": episode, "actor": ACTOR}}


def accepted(status="awaiting_decision", next_=None):
    return {"ok": True, "outcome": D.ACCEPTED, "refetch_required": True, "refusal": None, "error": None,
            "result": {"outcome": D.ACCEPTED, "status": status, "continuable": True, "viewer": ACTOR, "halt": None,
                       "next": [{"kind": "answer_decision", "player": ACTOR}] if next_ is None else next_}}


def attack_origin(n=1, *, card=USER_CARD, card_id=GASTLY, index=1, route="form", position=0, episode=1, submit=None):
    return {"type": "attempt", "n": n, "actor": ACTOR, "position": position, "episode": episode, "turn": [0, TURN],
            "candidate": {"id": "c1", "kind": "use_attack", "reasons": ["continuation_not_evaluated", "preflight_not_evaluated"]},
            "stages": [{"stage": 1, "role": "attack", "meaning": "attack", "input": "choose_option", "count": {"min": 1, "max": 1}}],
            "meaning": [{"stage": 1, "option": {"card": card, "card_id": card_id, "attack_index": index, "route": route}}],
            "submit": submit or accepted()}


def select_origin(n=2, *, card_id=GASTLY, index=1, position=1, episode=2, submit=None):
    return {"type": "attempt", "n": n, "actor": ACTOR, "position": position, "episode": episode, "turn": [0, TURN],
            "candidate": {"id": "c1", "kind": "answer_decision", "reasons": ["continuation_not_evaluated"]},
            "stages": [{"stage": 1, "decision_kind": "select_attack", "meaning": "number", "input": "choose_option", "count": {"min": 1, "max": 1}}],
            "meaning": [{"stage": 1, "option": {"value": index, "attack": {"card_id": card_id, "attack_index": index}}}], "submit": submit or accepted()}


def stages(cards=ENERGY_CARDS, minimum=0, maximum=2, kind="recover_energy"):
    return [{"stage": 1, "decision_kind": kind, "input": "choose_option", "meaning": "card", "count": {"min": minimum, "max": maximum}, "decline": True,
             "distinct": True, "options": [{"id": f"o{i + 1}", "card": c, "card_id": PSYCHIC, "processability": "may_stop_later"} for i, c in enumerate(cards)]}]


def rejected(code=CODE, *, category=None, status="awaiting_decision", next_=None, viewer=ACTOR, refetch=False, halt=None, public_code=None, stage="decision_answer"):
    entry = D.default_catalog().get(code)
    category = category or (entry.category if entry is not None else D.RULING_UNRESOLVED)
    return {"ok": True, "outcome": D.REJECTED, "refetch_required": refetch, "refusal": None, "error": None,
            "result": {"outcome": D.REJECTED, "status": status, "continuable": True, "viewer": viewer, "role": "actor", "halt": halt, "stage": stage,
                       "diagnostic_id": public_code or code, "category": category,
                       "next": [{"kind": "answer_decision", "player": viewer}] if next_ is None else next_},
            "verifier": {"diagnostic_id": code, "category": category, "engine_code": code}}


def check(valid=True, refusal=None):
    return {"contract": "kyuura-client-api", "format": 1, "ok": True, "refetch_required": False, "response": {"refusal": refusal, "valid": valid}, "type": "check"}


def entry(n=2, position=1, episode=2, **over):
    e = {"type": "attempt", "n": n, "actor": ACTOR, "position": position, "episode": episode, "turn": [0, TURN],
         "candidate": {"id": "c1", "kind": "answer_decision", "processability": "may_stop_later", "reasons": ["continuation_not_evaluated"]},
         "stages": stages(), "choices": [], "meaning": [], "check": check(), "submit": rejected()}
    e.update(over)
    return e


def logs(entry_view=None, origin_view=None, *, extra=()):
    rows = [position_row(origin_view or view(phase="main", decision=None), 0, 1), position_row(entry_view or view(), 1, 2), *extra]
    return {ACTOR: rows, 1: [], "host": []}


def judge(e, actor_logs=None, *, trace=None, hdr="default", basis_r=None):
    actor_logs = logs() if actor_logs is None else actor_logs
    trace = [attack_origin(), e] if trace is None else trace
    hdr = header() if hdr == "default" else hdr
    failure = J.recover_zero_energy_failure(e, trace=trace, actor_logs=actor_logs, header=hdr, basis_r=basis_r)
    evidence = J.submit_evidence(e, trace=trace, actor_logs=actor_logs, header=hdr, basis_r=basis_r)
    verdict = J.judge_normal(e["candidate"], e.get("meaning") or [], e["submit"], stages=e.get("stages"), evidence=evidence)
    return failure, evidence, verdict


class VersionTest(unittest.TestCase):
    def test_versions_registration_and_basis(self):
        self.assertEqual(J.JUDGE_RULES_VERSION, 10)
        self.assertEqual(B.TOOL_VERSION, 19)  # 19: rules-v8（旧の期待は 18）。 18: rules-v7（旧の期待は 17）。 17: rules-v6（旧の期待は 16）。 16: rules-v5（旧の期待は 15）。 15: rules-v4（旧の期待は 14）。 14: rules-v3（旧の期待は 13）
        self.assertEqual((B.PLAN_FORMAT, B.COMPLETE_FORMAT), ("kyuura-vai-batch-plan/7", "kyuura-vai-batch-complete/7"))
        self.assertEqual(J.RECOVER_ZERO_CODE, CODE)
        self.assertIn(CODE, J.KNOWN_STOP_EVIDENCE)
        self.assertNotIn("code", J.KNOWN_STOP_EVIDENCE[CODE])  # 鍵 = 元のコード
        self.assertEqual(J.RECORDED_STOP_CONDITIONS, {ER9: "retrieve_energy"})  # ER9 の表には足さない
        self.assertEqual(J.RECOVER_ZERO_CONDITIONS, ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R13", "R11"))
        basis = J.recover_zero_basis()
        self.assertEqual(basis["method"], "kyuura-recover-zero-basis-sha256/1")
        self.assertEqual(basis["files"], ["resolution/programs.py", "resolution/flow.py", "decisions.py", "checks.py", "engine.py", "legal_actions.py",
                                          "observation.py", "effects.py"])
        self.assertRegex(basis["digest"], "^[0-9a-f]{64}$")
        for other in (J.lost_target_basis(), J.lost_target_p2_basis(), J.lost_target_p3_basis()):
            self.assertNotEqual(basis["digest"], other["digest"])
        # basis のファイルはどれも実装の識別の behavior のファイル（instrumentation でない）。behavior_digest が同じなら同じ中身
        names = package_files(PACKAGE_ROOT)
        self.assertTrue(all(f in names and f not in INSTRUMENTATION_FILES for f in basis["files"]))


class PositiveTest(unittest.TestCase):
    def test_own_printed_attack_zero_answer_is_known_stop(self):
        failure, evidence, (verdict, why) = judge(entry())
        self.assertEqual((failure, evidence, verdict), (None, CODE, J.KNOWN_STOP))
        self.assertEqual(why, [D.RULING_UNRESOLVED, CODE, "continuation_not_evaluated", "evidence:" + J.KNOWN_STOP_EVIDENCE[CODE]["condition"]])

    def test_max_one(self):
        e = entry(stages=stages(cards=(54,), maximum=1))
        self.assertEqual(judge(e, logs(view(cards=(54,), maximum=1)))[:2], (None, CODE))

    def test_metronome_route(self):
        trace = [attack_origin(card=COPIER_CARD, card_id=CLEFAIRY, index=1), select_origin(), entry(n=3, position=2, episode=3)]
        actor_logs = {ACTOR: [position_row(view(phase="main", decision=None, active=zone(COPIER_CARD, CLEFAIRY)), 0, 1),
                              position_row(view(decision={"kind": "select_attack"}, active=zone(COPIER_CARD, CLEFAIRY)), 1, 2),
                              position_row(view(active=zone(COPIER_CARD, CLEFAIRY)), 2, 3)], 1: [], "host": []}
        self.assertEqual(judge(trace[-1], actor_logs, trace=trace)[:2], (None, CODE))
        clefable = [attack_origin(card=COPIER_CARD, card_id=CLEFABLE, index=0), select_origin(), entry(n=3, position=2, episode=3)]
        actor_logs = {ACTOR: [position_row(view(phase="main", decision=None, active=zone(COPIER_CARD, CLEFABLE)), 0, 1),
                              position_row(view(active=zone(COPIER_CARD, CLEFABLE)), 2, 3)], 1: [], "host": []}
        self.assertEqual(judge(clefable[-1], actor_logs, trace=clefable)[:2], (None, CODE))

    def test_rejected_attempts_between_origin_and_entry_are_allowed(self):
        earlier = entry(n=2)
        later = entry(n=3)
        self.assertEqual(judge(later, trace=[attack_origin(), earlier, later])[:2], (None, CODE))


class NegativeTest(unittest.TestCase):
    def assert_undetermined(self, e, actor_logs=None, *, expected, **kw):
        failure, evidence, verdict = judge(e, actor_logs, **kw)
        self.assertEqual(failure, expected)
        self.assertNotEqual(evidence, CODE)
        self.assertNotEqual(verdict[0], J.KNOWN_STOP)
        if expected not in ("R2", "R3") and e["submit"].get("outcome") == D.REJECTED and (e["submit"].get("verifier") or {}).get("engine_code") == CODE:
            self.assertEqual(verdict, UNDET)  # R2・R3 は既存の規則が先に suspect・stop_not_explained_by_path にする（どちらも known_stop でない）
        return verdict

    def test_answers_with_cards(self):
        for choices, m in ((["o1"], [{"stage": 1, "option": {"card": 54}}]), (["o1", "o2"], [{"stage": 1, "option": {"card": 54}}, {"stage": 1, "option": {"card": 40}}])):
            with self.subTest(len(choices)):
                self.assert_undetermined(entry(choices=choices, meaning=m), expected="R7")
        self.assert_undetermined(entry(choices=["o1"]), expected="R7")  # choices と meaning の食い違い

    def test_other_decision_effect_and_code(self):
        self.assert_undetermined(entry(stages=stages(kind="retrieve_energy")), logs(view(kind="retrieve_energy")), expected="R4")
        self.assert_undetermined(entry(stages=stages(minimum=1)), logs(view(minimum=1)), expected="R5")
        for code in (ER9, "UNRESOLVED_SUPER_ENERGY_RETRIEVAL_ZERO_CHOICE", "INVALID_CHOICE_COUNT"):
            with self.subTest(code):
                self.assert_undetermined(entry(submit=rejected(code)), expected="R1")
        self.assert_undetermined(entry(submit=rejected(public_code=ER9)), expected="R1")
        self.assert_undetermined(entry(submit=rejected(category=D.UNSUPPORTED)), expected="R2")
        other_attack = [attack_origin(card_id=RATTATA, index=0), entry()]
        self.assert_undetermined(entry(), logs(origin_view=view(phase="main", decision=None, active=zone(card_id=RATTATA))), trace=other_attack, expected="R13")

    def test_stage_shapes(self):
        two = stages() + [dict(stages()[0], stage=2)]
        cases = {"missing": (None, "R4"), "empty": ([], "R4"), "two": (two, "R4"), "input": ([dict(stages()[0], input="choose_value")], "R4"),
                 "meaning": ([dict(stages()[0], meaning="pokemon")], "R4"),
                 "max_zero": (stages(maximum=0), "R5"), "max_over": (stages(cards=(54,), maximum=2), "R5"), "max_str": ([dict(stages()[0], count={"min": 0, "max": "2"})], "R5"),
                 "no_options": (stages(cards=()), "R5"), "dup_card": (stages(cards=(54, 54)), "R6"),
                 "option_without_card": ([dict(stages()[0], options=[{"id": "o1"}] + stages()[0]["options"][1:])], "R6"),
                 "dup_id": ([dict(stages()[0], options=[dict(o, id="o1") for o in stages()[0]["options"]])], "R6")}
        for name, (st, expected) in cases.items():
            with self.subTest(name):
                e = entry()
                if st is None:
                    del e["stages"]
                else:
                    e["stages"] = st
                self.assert_undetermined(e, expected=expected)

    def test_candidate_and_check(self):
        self.assert_undetermined(entry(candidate={"id": "c1", "kind": "use_attack", "reasons": ["continuation_not_evaluated"]}), expected="R3")
        self.assert_undetermined(entry(candidate={"id": "c1", "kind": "answer_decision", "reasons": []}), expected="R3")
        for name, c in (("missing", None), ("invalid", check(valid=False)), ("refusal", check(refusal={"code": "X"})), ("stale", dict(check(), refetch_required=True))):
            with self.subTest(name):
                e = entry(check=c)
                if c is None:
                    del e["check"]
                self.assert_undetermined(e, expected="R8")

    def test_after_rejection_state(self):
        cases = {"status": rejected(status="in_progress"), "next_other": rejected(next_=[{"kind": "answer_decision", "player": 1}]),
                 "next_turn": rejected(next_=[{"kind": "turn_action", "player": ACTOR}]), "viewer": rejected(viewer=1), "refetch": rejected(refetch=True),
                 "halt": rejected(halt={"code": "X"}), "stage": rejected(stage="turn_action")}
        for name, submit in cases.items():
            with self.subTest(name):
                self.assert_undetermined(entry(submit=submit), expected="R9")

    def test_refused_failed_and_halt_after_acceptance(self):
        refused = {"ok": False, "outcome": "refused", "refusal": {"code": "STALE_HANDLE"}, "refetch_required": True, "result": None, "error": None}
        for name, submit in (("refused", refused), ("failed", dict(rejected(), outcome=D.FAILED)), ("error", dict(rejected(), error={"type": "X"}))):
            with self.subTest(name):
                failure, evidence, _ = judge(entry(submit=submit))
                self.assertEqual((failure, evidence), ("R1", None))
        verdict, why = J.judge_halt_after_accept({"category": D.RULING_UNRESOLVED, "diagnostic_id": CODE})
        self.assertEqual((verdict, why), (J.UNDETERMINED, [f"halt_condition_not_evidenced:{CODE}"]))

    def test_observation_missing_stale_viewer_and_contradiction(self):
        cases = {
            "missing": {ACTOR: [position_row(view(phase="main", decision=None), 0, 1)], 1: [], "host": []},
            "duplicated": logs(extra=[position_row(view(), 1, 2)]),
            "viewer": logs(view(viewer=1)), "not_ok": logs(view(ok=False)), "not_current": logs(view(current=1)),
            "phase": logs(view(phase="main")), "no_decision": logs(view(decision=None)), "other_turn": logs(view(turn=TURN + 1)),
            "kind": logs(view(kind="retrieve_energy")), "min": logs(view(minimum=1)), "max": logs(view(maximum=1)),
            "values": logs(view(cards=(54, 40, 37, 47))), "count": logs(view(cards=(54, 40, 47))),
            "player": logs(view(decision=dict(view()["observation"]["decision"], player=1))),
        }
        for name, actor_logs in cases.items():
            with self.subTest(name):
                self.assert_undetermined(entry(), actor_logs, expected="R10")
        stale = [attack_origin(), {"type": "attempt", "n": 2, "actor": ACTOR, "episode": 2, "submit": {"outcome": D.ACCEPTED}}, entry(n=3)]
        self.assert_undetermined(stale[-1], trace=stale, expected="R10")

    def test_route(self):
        cases = {
            "no_origin": ([entry()], None),
            "other_actor_accepted_between": ([attack_origin(), dict(attack_origin(n=2), actor=1, submit=accepted("in_progress")), entry(n=3)], None),
            "origin_not_awaiting": ([attack_origin(submit=accepted("in_progress")), entry()], None),
            "origin_route": ([attack_origin(route="mimic"), entry()], None),
            "origin_other_index": ([attack_origin(index=0), entry()], None),
            "ditto": ([attack_origin(card=21), entry()], logs(origin_view=view(phase="main", decision=None, active=zone(card=0, card_id=DITTO)))),
            "origin_view_missing": ([attack_origin(), entry()], {ACTOR: [position_row(view(), 1, 2)], 1: [], "host": []}),
            "select_without_metronome": ([attack_origin(), select_origin(), entry(n=3, position=2, episode=3)],
                                         {ACTOR: [position_row(view(phase="main", decision=None), 0, 1), position_row(view(), 2, 3)], 1: [], "host": []}),
            "select_other_attack": ([attack_origin(card=COPIER_CARD, card_id=CLEFAIRY), select_origin(index=0), entry(n=3, position=2, episode=3)],
                                    {ACTOR: [position_row(view(phase="main", decision=None, active=zone(COPIER_CARD, CLEFAIRY)), 0, 1), position_row(view(), 2, 3)], 1: [], "host": []}),
        }
        for name, (trace, actor_logs) in cases.items():
            with self.subTest(name):
                self.assert_undetermined(trace[-1], actor_logs, trace=trace, expected="R13")

    def test_basis(self):
        other = header()
        other["engine"]["behavior_digest"] = "0" * 64
        basis = J.recover_zero_basis()
        other_effects = header()
        other_effects["dependencies"]["effects"] = "other"
        other_method = header()
        other_method["engine"]["method"] = "other"
        cases = [("same", header(), None, None), ("same_with_basis", header(), basis, None), ("same_with_wrong_basis", header(), dict(basis, digest="1" * 64), "R11"),
                 ("no_header", None, None, "R11"), ("other_engine", other, None, "R11"), ("other_engine_with_basis", other, basis, None),
                 ("other_engine_wrong_digest", other, dict(basis, digest="1" * 64), "R11"), ("other_engine_wrong_files", other, dict(basis, files=basis["files"][:4]), "R11"),
                 ("other_engine_p2_basis", other, J.lost_target_p2_basis(), "R11"), ("other_effects", other_effects, basis, "R11"), ("other_method", other_method, None, "R11")]
        for name, hdr, b, expected in cases:
            with self.subTest(name):
                self.assertEqual(J.recover_zero_energy_failure(entry(), trace=[attack_origin(), entry()], actor_logs=logs(), header=hdr, basis_r=b), expected)

    def test_no_overlap_with_other_rules(self):
        e, trace, actor_logs, hdr = entry(), [attack_origin(), entry()], logs(), header()
        self.assertIsNone(J.recorded_stop_evidence(e["candidate"], e["meaning"], e["stages"], e["submit"]))
        self.assertIsNone(J.own_face_down_lost_target_evidence(e, trace=trace, actor_logs=actor_logs, header=hdr))
        self.assertIsNone(J.opponent_face_down_lost_target_evidence(e, trace=trace, actor_logs=actor_logs, header=hdr))
        self.assertIsNone(J.own_face_down_decision_lost_target_evidence(e, trace=trace, actor_logs=actor_logs, header=hdr))
        for name in ("recorded_stop_evidence", "own_face_down_lost_target_evidence", "opponent_face_down_lost_target_evidence",
                     "own_face_down_decision_lost_target_evidence"):
            with self.subTest(name), mock.patch.object(J, name, return_value="X"):
                failure, evidence, verdict = judge(entry())
                self.assertIsNone(failure)
                self.assertIsNone(evidence)  # 2 つの規則が根拠を返す矛盾は、どれにも決めない（呼ぶ順で隠さない）
                self.assertEqual(verdict, UNDET)

    def test_er9_entry_is_not_taken_by_rule_10(self):
        er9 = entry(stages=stages(kind="retrieve_energy"), submit=rejected(ER9))
        failure, evidence, (verdict, _why) = judge(er9, logs(view(kind="retrieve_energy")))
        self.assertEqual((failure, evidence, verdict), ("R1", ER9, J.KNOWN_STOP))


# ---------------------------------------------------------------- 本物の runner に通す（構築盤面）


class ZeroThenOne(UniformPolicy):
    """ケースの選び手（方策ではない）: ワザ（と、ゆびをふるならゴースのエナジーへんかん）を選び、回収の決定に最初は 0 枚、次は 1 枚を答える。"""

    name, version = "scripted-rz", 0

    def __init__(self, attack_name, copied_name=None):
        super().__init__("scripted-rz")
        self.attack_name, self.copied_name, self.zero = attack_name, copied_name, True

    def choose(self, purpose, items, context):
        if purpose == "candidate":
            kinds = [c.get("kind") for c in items]
            for kind in ("answer_decision", "use_attack"):
                if kind in kinds:
                    return kinds.index(kind), "scripted"
            return 0, "scripted"
        if purpose == "option":
            stage = context["stage"]
            by_id = {o["id"]: o for o in stage.get("options", [])}
            want = self.copied_name if stage.get("decision_kind") == "select_attack" else self.attack_name
            for i, oid in enumerate(items):
                o = by_id.get(oid, {})
                if (o.get("name_ja") or (o.get("attack") or {}).get("name_ja")) == want:
                    return i, "scripted"
            return 0, "scripted"
        if purpose == "count":
            zero, self.zero = self.zero, False
            return (0 if zero else 1), "scripted"
        return 0, "scripted"


def board(kind):
    if kind == "gastly":
        return build_test_state([{"active": {"card": GASTLY, "energy": [PSYCHIC, PSYCHIC]}, "bench": [RATTATA], "discard": [FIRE, WATER]}, {"active": GROWLITHE}],
                                turn_number=TURN), ZeroThenOne("エナジーへんかん")
    if kind == "ditto":
        return build_test_state([{"active": {"card": DITTO, "energy": [PSYCHIC, PSYCHIC]}, "discard": [FIRE, WATER]}, {"active": {"card": GASTLY, "energy": [PSYCHIC]}}],
                                turn_number=TURN), ZeroThenOne("エナジーへんかん")
    me = {"card": kind, "energy": [PSYCHIC, PSYCHIC, PSYCHIC]}
    if kind == CLEFABLE:
        me["evolved_from"] = CLEFAIRY
    return build_test_state([{"active": me, "discard": [FIRE, WATER]}, {"active": {"card": GASTLY, "energy": [PSYCHIC, PSYCHIC]}}], turn_number=TURN), \
        ZeroThenOne("ゆびをふる", "エナジーへんかん")


def run(kind, *, negative=None, with_header=True):
    state, policy = board(kind)
    text, error = F.snapshot_text(state, "RZ")
    assert text is not None, error
    operations = 3 if kind in ("gastly", "ditto") else 4  # ワザ（・ゆびをふるの選択）・0 枚の拒否・1 枚の受理まで
    config = V.Config(profile="boundary", limits=V.Limits(operations=operations, seconds=60), run_id="test-rz")
    return RecordedFixtureRunner(config, text, with_header=with_header, policy_factory=lambda seed, dist: policy, negative=negative).run()


def submitted(result):
    return [e for e in result["trace"] if e.get("type") == "attempt" and e.get("submit") is not None]


def zero_rows(judged):
    return [r for r in judged["rows"] if r["engine_code"] == CODE]


class RunnerConnectionTest(unittest.TestCase):
    """構築盤面 → 本物の runner → バッチの入口と単局の入口・保存した形からの読み直し。new_game からの対戦の実績には数えない。"""

    def test_known_stop_in_both_entries(self):
        for kind in ("gastly", CLEFAIRY, CLEFABLE):
            with self.subTest(kind=kind):
                result = run(kind)
                (e,) = [x for x in submitted(result) if (x["submit"].get("verifier") or {}).get("engine_code") == CODE]
                self.assertEqual(e["meaning"], [])
                self.assertIsNone(J.recover_zero_energy_failure(e, trace=result["trace"], actor_logs=result["actor_logs"], header=B.record_header(result["record"])))
                judged = B.judge_trace(result)
                self.assertEqual(judged["rules_version"], 10)
                self.assertEqual([r["verdict"] for r in zero_rows(judged)], [J.KNOWN_STOP])
                self.assertEqual(submitted(result)[-1]["submit"]["outcome"], D.ACCEPTED)  # 回答し直しの受理（補足。条件には使わない）
                single = run(kind, negative=NoNegative())
                (e_single,) = [x for x in submitted(single) if (x["submit"].get("verifier") or {}).get("engine_code") == CODE]
                row = zero_rows(judged)[0]
                self.assertEqual(e_single["judge"], {"verdict": row["verdict"], "reasons": row["reasons"]})
                saved = {str(a): [json.loads(x) for x in B.jsonl_bytes(r).decode("utf-8").splitlines() if x.strip()] for a, r in result["actor_logs"].items()}
                reloaded = dict(result, actor_logs=saved, trace=[json.loads(json.dumps(x)) for x in result["trace"]])
                self.assertEqual(B.judge_trace(reloaded)["rows"], judged["rows"])

    def test_ditto_route_is_outside_the_registration(self):
        result = run("ditto")
        (e,) = [x for x in submitted(result) if (x["submit"].get("verifier") or {}).get("engine_code") == CODE]
        self.assertEqual(J.recover_zero_energy_failure(e, trace=result["trace"], actor_logs=result["actor_logs"], header=B.record_header(result["record"])), "R13")
        self.assertEqual([r["verdict"] for r in zero_rows(B.judge_trace(result))], [J.UNDETERMINED])

    def test_missing_header_and_basis_in_both_entries(self):
        for negative in (None, NoNegative()):
            with self.subTest(single=negative is not None):
                result = run("gastly", with_header=False, negative=negative)
                (e,) = [x for x in submitted(result) if (x["submit"].get("verifier") or {}).get("engine_code") == CODE]
                judged = B.judge_trace(result)
                self.assertEqual([r["verdict"] for r in zero_rows(judged)], [J.UNDETERMINED])
                self.assertEqual(judged["undetermined"][0]["category"], B.EVIDENCE_MISSING_STOP)
                if negative is not None:
                    self.assertEqual(e["judge"], {"verdict": J.UNDETERMINED, "reasons": UNDET[1]})
        result = run("gastly")
        hdr = copy.deepcopy(B.record_header(result["record"]))
        hdr["engine"]["behavior_digest"] = "0" * 64
        other = dict(result, record={"header": hdr})
        self.assertEqual([r["verdict"] for r in zero_rows(B.judge_trace(other))], [J.UNDETERMINED])
        self.assertEqual([r["verdict"] for r in zero_rows(B.judge_trace(other, basis_r=J.recover_zero_basis()))], [J.KNOWN_STOP])
        self.assertEqual([r["verdict"] for r in zero_rows(B.judge_trace(other, basis_p2=J.lost_target_p2_basis()))], [J.UNDETERMINED])

    def test_stop_policy_and_no_secret_in_rows(self):
        result = run("gastly")
        judged = B.judge_trace(result)
        summary = summary_and_rest(B.judge_summary(judged))
        stops, notes = B.stop_reasons(summary, B._policy_dict(B.StopPolicy()))
        self.assertEqual(result["termination"]["class"], "limit_operations")
        self.assertEqual(stops, [])
        self.assertIn("known_stop:1", notes)
        text = json.dumps(zero_rows(judged), ensure_ascii=False)
        for secret in (GASTLY, FIRE, WATER, "card_id"):
            self.assertNotIn(secret, text)


if __name__ == "__main__":
    unittest.main()
