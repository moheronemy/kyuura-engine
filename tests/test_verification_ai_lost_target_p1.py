"""検証用 AI の判定の規則 7（docs/verification-ai-lost-target-own-face-down-design.md 5 章・6 章・8.2 節・13 章）: LOST_TARGET の P1（おもての使い手の特殊能力で
本人のうらのカードを指定した送信の UNSUPPORTED_SECRET_PLAN_LOST_TARGET の拒否）を、送った本人の送信前の観測とエンジンのカードデータ・たねの判定で、条件 L1〜L12 を
すべて確かめたときだけ known_stop にする。

- 人工の送信の行と観測（保存済みの s1 の記録の形を写す。局・seed・本当のカードの値は写さない）で J1〜J3・J9・N1〜N16・L12 を確かめる
- 構築盤面（``tests/test_lost_target_own_face_down_v0_180.py`` の board・own_face_down。new_game からの対戦ではない）を本物の runner に通し、逐次バッチの入口
  （``batch.judge_trace``）と単局の runner の判定（変異の実行の中）が同じ値になること、判定のための要求が増えないことを確かめる（J10 もここ）
"""

from __future__ import annotations

import copy
import json
import unittest

from kyuura_engine import diagnostics as D
from kyuura_engine import zones as Z
from kyuura_engine.cards import load_card_pool
from kyuura_engine.effects import TEXT_PRE_NEO, card_is_basic_in_text
from kyuura_engine.replay_record import current_identity

from tools.verification_ai import batch as B
from tools.verification_ai import fixtures_u_r3a as F
from tools.verification_ai import judge as J
from tools.verification_ai import runner as V
from tools.verification_ai.policies import UniformPolicy

from tests.helpers import DIGLETT, FIRE, KADABRA, PSYCHIC, RATTATA, ROCKET_CHARMANDER
from tests.test_verification_ai_batch_judge import FixtureRunner, NoNegative, _FixtureGame, summary_and_rest

CODE = J.LOST_TARGET_CODE
UNDET = (J.UNDETERMINED, [f"stop_condition_not_evidenced:{CODE}"])
ACTOR, POSITION, EPISODE, TURN, N = 0, 3, 4, 7, 5
USER, FD, FD2, RAT, OPP_FD = 10, 9, 11, 2, 20  # 場のポケモンの番号（人工）
ENERGY, ENERGY_RAT, ENERGY_OPP = 49, 50, 60  # エネルギーカードの uid（人工）


def header():
    pool = load_card_pool()
    return {"engine": dict(current_identity()), "dependencies": {"rules": "JP-2000.02.14", "card_pool": "default",
                                                                 "card_data": {k: pool.source[k] for k in ("repository", "commit", "path")}}}


def zone(pid, card_id=None, *, real=None, energy=(), owner=0):
    z = {"pokemon_id": pid, "energy": [{"card": e, "card_id": FIRE} for e in energy]}
    if real is not None:
        z.update({"face_down": True, **({"real": {"card": 100 + pid, "card_id": real}} if owner == ACTOR else {})})
    else:
        z.update({"card": 100 + pid, "card_id": card_id})
    return z


def view(*, own_bench=None, opp_bench=None, turn=TURN, decision=None, phase="main", current=ACTOR, viewer=ACTOR):
    own = own_bench if own_bench is not None else [zone(RAT, RATTATA, energy=(ENERGY_RAT,)), zone(FD, real=PSYCHIC, energy=(ENERGY,)), zone(USER, ROCKET_CHARMANDER)]
    opp = opp_bench if opp_bench is not None else []
    return {"ok": True, "type": "view", "viewer": viewer, "status": {"segment": 0, "status": "in_progress", "phase": phase},
            "observation": {"viewer": viewer, "current_player": current, "phase": phase, "decision": decision, "turn": turn,
                            "players": [{"player": 0, "active": zone(1, "PMCG1-058"), "bench": own},
                                        {"player": 1, "active": zone(21, "PMCG1-058"), "bench": opp}]}}


def logs(*views, position=POSITION, episode=EPISODE):
    return {ACTOR: [{"type": "position", "position": position, "view": v, "episode": {"type": "episode", "episode": episode, "actor": ACTOR}} for v in views],
            1: [], "host": []}


def stages():
    return [{"stage": 1, "role": "source", "meaning": "pokemon", "input": "choose_option", "count": {"min": 1, "max": 1}},
            {"stage": 2, "role": "energy", "meaning": "card", "input": "choose_option", "depends_on_stage": 1, "count": {"min": 1, "max": 1}}]


def pokemon_option(pid, face_down=False):
    o = {"pokemon": pid, "zone": "bench", "processability": "unverified", "reasons": ["face_down_reveal_not_evaluated"], "eligible": True}
    if face_down:
        o["face_down"] = True
    return o


def meaning(source=FD, source_face_down=True, energy=ENERGY):
    return [{"stage": 1, "option": pokemon_option(source, source_face_down)},
            {"stage": 2, "option": {"card": energy, "card_id": FIRE, "processability": "unverified", "reasons": ["face_down_reveal_not_evaluated"]}}]


def rejected(code=CODE, *, category=None, status="in_progress", next_=None, viewer=ACTOR, refetch=False, halt=None, public_code=None):
    entry = D.default_catalog().get(code)
    category = category or (entry.category if entry is not None else D.UNSUPPORTED)
    return {"ok": True, "outcome": D.REJECTED, "refetch_required": refetch, "refusal": None, "error": None,
            "result": {"outcome": D.REJECTED, "status": status, "continuable": True, "viewer": viewer, "role": "actor", "halt": halt,
                       "diagnostic_id": public_code or code, "category": category,
                       "next": [{"kind": "turn_action", "player": viewer}] if next_ is None else next_},
            "verifier": {"diagnostic_id": code, "category": category, "engine_code": code}}


def candidate(user_face_down=False):
    c = {"id": "c5", "kind": "use_power", "processability": "unverified", "reasons": ["face_down_reveal_not_evaluated"],
         "pokemon": {"pokemon": USER, "card_id": ROCKET_CHARMANDER, "zone": "bench"}, "power": {"index": 0},
         "input_stages": [{"stage": 1}, {"stage": 2}]}
    if user_face_down:
        c["pokemon"] = {"pokemon": USER, "zone": "bench", "face_down": True}
        c["power"] = {"face_down": True}
    return c


def entry(**over):
    e = {"type": "attempt", "n": N, "actor": ACTOR, "position": POSITION, "episode": EPISODE, "turn": [0, TURN], "candidate": candidate(),
         "stages": stages(), "meaning": meaning(), "submit": rejected()}
    e.update(over)
    return e


def judge(e, actor_logs=None, *, trace=None, hdr="default", basis=None):
    actor_logs = logs(view()) if actor_logs is None else actor_logs
    trace = [e] if trace is None else trace
    hdr = header() if hdr == "default" else hdr
    failure = J.lost_target_failure(e, trace=trace, actor_logs=actor_logs, header=hdr, basis=basis)
    evidence = J.submit_evidence(e, trace=trace, actor_logs=actor_logs, header=hdr, basis=basis)
    verdict = J.judge_normal(e["candidate"], e.get("meaning") or [], e["submit"], stages=e.get("stages"), evidence=evidence)
    return failure, evidence, verdict


class VersionTest(unittest.TestCase):
    def test_versions_and_registration(self):
        self.assertEqual(J.JUDGE_RULES_VERSION, 7)
        self.assertEqual(B.TOOL_VERSION, 9)
        self.assertEqual((B.PLAN_FORMAT, B.COMPLETE_FORMAT), ("kyuura-vai-batch-plan/6", "kyuura-vai-batch-complete/6"))
        self.assertEqual(J.LOST_TARGET_CODE, Z.SECRET_PLAN_LOST_TARGET_CODE)
        self.assertIn(CODE, J.KNOWN_STOP_EVIDENCE)
        self.assertNotIn(CODE, J.RECORDED_STOP_CONDITIONS)  # 規則 6 の仕組み（送信の値だけ）には入れない
        self.assertEqual(J.LOST_TARGET_ROLES, {"source": "pokemon", "target": "pokemon", "energy": "card"})


class PositiveTest(unittest.TestCase):
    def assert_known_stop(self, e, actor_logs=None, **kw):
        failure, evidence, (verdict, why) = judge(e, actor_logs, **kw)
        self.assertEqual((failure, evidence, verdict), (None, CODE, J.KNOWN_STOP))
        self.assertEqual(why, [D.UNSUPPORTED, CODE, "face_down_reveal_not_evaluated", "evidence:" + J.KNOWN_STOP_EVIDENCE[CODE]["condition"]])
        return why

    def test_j1_source_and_energy_on_the_same_own_non_basic_face_down(self):
        """J1: 保存済みの s1 の 2 件と同じ形（source と energy が同じ本人のたねでないうらのポケモン）。"""
        self.assert_known_stop(entry())

    def test_j2_only_energy_holder_is_face_down(self):
        """J2: source はおもてのコラッタ、energy だけが本人のうらについたカード（E2 の形）。"""
        e = entry(meaning=meaning(source=RAT, source_face_down=False, energy=ENERGY))
        self.assert_known_stop(e)

    def test_j3_basic_and_non_basic(self):
        """J3: 本人のたねのうら（source）とたねでないうら（energy のついているポケモン）を両方指定。1 つ以上がたねでなければ足りる。"""
        own = [zone(RAT, RATTATA, energy=(ENERGY_RAT,)), zone(FD, real=PSYCHIC, energy=(ENERGY,)), zone(FD2, real=DIGLETT), zone(USER, ROCKET_CHARMANDER)]
        self.assert_known_stop(entry(meaning=meaning(source=FD2, energy=ENERGY)), logs(view(own_bench=own)))

    def test_reason_only_on_the_chosen_options(self):
        """候補におもてだけの組もあると、候補の理由は continuation_not_evaluated で、face_down_reveal_not_evaluated は選んだ選べるものの側にだけある（本物の runner の形）。"""
        e = entry(candidate=dict(candidate(), processability="may_stop_later", reasons=["continuation_not_evaluated"]))
        failure, evidence, (verdict, reasons) = judge(e)
        self.assertEqual((failure, evidence, verdict), (None, CODE, J.KNOWN_STOP))
        self.assertEqual(reasons, [D.UNSUPPORTED, CODE, "continuation_not_evaluated", "face_down_reveal_not_evaluated",
                                   "evidence:" + J.KNOWN_STOP_EVIDENCE[CODE]["condition"]])

    def test_target_role(self):
        """source・target・energy のどれでも（段の role が target・meaning pokemon の 1 段）。"""
        e = entry(stages=[{"stage": 1, "role": "target", "meaning": "pokemon", "input": "choose_option"}],
                  meaning=[{"stage": 1, "option": pokemon_option(FD, True)}])
        self.assert_known_stop(e)

    def test_j9_same_answer_as_the_engine_for_every_card(self):
        """J9: カードの一覧のすべてのカードで、規則 7 のたねの判定と、エンジンの zones._secret_plan_keeps（印刷の定義だけを持つ代わりの状態で呼ぶ）が同じ答え。"""
        pool = load_card_pool()

        class Printed:
            def __init__(self, definition):
                self.definition = definition

            def printed_def(self, _card):
                return self.definition

        counted = {"stop": 0, "keep": 0}
        for card_id, definition in sorted(pool.definitions.items()):
            own = [zone(RAT, RATTATA, energy=(ENERGY_RAT,)), zone(FD, real=card_id, energy=(ENERGY,)), zone(USER, ROCKET_CHARMANDER)]
            failure = J.lost_target_failure(entry(), trace=[entry()], actor_logs=logs(view(own_bench=own)), header=header())
            keeps = Z._secret_plan_keeps(Printed(definition), 0)
            self.assertEqual(card_is_basic_in_text(definition, TEXT_PRE_NEO) is True, keeps, card_id)
            self.assertEqual(failure, "L11" if keeps else None, card_id)
            counted["keep" if keeps else "stop"] += 1
        self.assertGreater(counted["keep"], 0)
        self.assertGreater(counted["stop"], 0)


class NegativeTest(unittest.TestCase):
    """どれも known_stop にしない（規則 6 と同じ判定・同じ理由・同じ分類）。"""

    def assert_rule6(self, e, actor_logs=None, *, expected_failure, **kw):
        failure, evidence, verdict = judge(e, actor_logs, **kw)
        self.assertEqual(failure, expected_failure)
        self.assertIsNone(evidence)
        rule6 = J.judge_normal(e["candidate"], e.get("meaning") or [], e["submit"], stages=e.get("stages"),
                               evidence=J.recorded_stop_evidence(e["candidate"], e.get("meaning") or [], e.get("stages"), e["submit"]))
        self.assertEqual(verdict, rule6)
        return verdict

    def assert_undetermined(self, e, actor_logs=None, *, expected_failure, **kw):
        verdict = self.assert_rule6(e, actor_logs, expected_failure=expected_failure, **kw)
        self.assertEqual(verdict, UNDET)
        self.assertEqual(B.undetermined_category("submit", verdict[1]), B.EVIDENCE_MISSING_STOP)  # N16

    def test_n1_opponent_face_down(self):
        """N1: 指定したうらが相手の場（P2）。"""
        opp = [zone(OPP_FD, real=KADABRA, energy=(ENERGY_OPP,), owner=1)]
        self.assert_undetermined(entry(meaning=meaning(source=OPP_FD, energy=ENERGY_OPP)), logs(view(opp_bench=opp)), expected_failure="L9")

    def test_n2_mixed_own_and_opponent(self):
        """N2: 本人のたねでないうらと相手のうらの混在。"""
        opp = [zone(OPP_FD, real=KADABRA, owner=1)]
        e = entry(meaning=meaning(source=OPP_FD, energy=ENERGY))
        self.assert_undetermined(e, logs(view(opp_bench=opp)), expected_failure="L9")

    def test_n3_answer_decision(self):
        """N3: 決定への回答（P3）。拒否のあとが決定待ち。"""
        e = entry(candidate={"id": "c1", "kind": "answer_decision", "processability": "may_stop_later", "reasons": ["continuation_not_evaluated"]},
                  stages=[{"stage": 1, "decision_kind": "select_pokemon", "meaning": "pokemon", "count": {"min": 1, "max": 1}}],
                  meaning=[{"stage": 1, "option": {"value": 7}}],
                  submit=rejected(status="awaiting_decision", next_=[{"kind": "answer_decision", "player": ACTOR}]))
        self.assert_undetermined(e, expected_failure="L3")
        same_shape = dict(e, submit=rejected())  # 拒否のあとの形が P1 と同じでも、種類が違えば外れる
        self.assert_undetermined(same_shape, expected_failure="L4")

    def test_n4_face_down_user(self):
        """N4: 使い手がうら（P1u。規則 5 の is_face_down_power の経路）。"""
        e = entry(candidate=candidate(user_face_down=True))
        self.assertTrue(J.is_face_down_power(e["candidate"]))
        self.assert_undetermined(e, expected_failure="L4")

    def test_n4b_no_face_down_reason_anywhere(self):
        """候補にも選んだ選べるものにも face_down_reveal_not_evaluated がない（API がうらの指定を示していない）。"""
        plain = [{"stage": m["stage"], "option": dict(m["option"], reasons=["continuation_not_evaluated"])} for m in meaning()]
        e = entry(candidate=dict(candidate(), reasons=["continuation_not_evaluated"]), meaning=plain)
        failure, evidence, verdict = judge(e)
        self.assertEqual((failure, evidence), ("L4", None))
        self.assertEqual(verdict, J.judge_normal(e["candidate"], e["meaning"], e["submit"], stages=e["stages"]))

    def test_n5_all_designated_face_down_are_basic(self):
        """N5: 指定したうらがすべてたね（根拠の矛盾）・ベイビィ。"""
        for real in (DIGLETT, "neo1-042"):
            with self.subTest(real=real):
                own = [zone(RAT, RATTATA, energy=(ENERGY_RAT,)), zone(FD, real=real, energy=(ENERGY,)), zone(USER, ROCKET_CHARMANDER)]
                self.assert_undetermined(entry(), logs(view(own_bench=own)), expected_failure="L11")

    def test_n6_no_face_down_designated(self):
        """N6: 指定がすべておもて。"""
        e = entry(meaning=meaning(source=RAT, source_face_down=False, energy=ENERGY_RAT))
        self.assert_undetermined(e, expected_failure="L9")

    def test_n7_view_missing_duplicated_or_other_time(self):
        """N7: 観測の行がない・2 つある・episode が違う・番が違う・決定がある・番の主体でない・段階が違う・失敗の応答。"""
        cases = {
            "missing": {ACTOR: [], 1: [], "host": []},
            "duplicated": logs(view(), view()),
            "other_episode": logs(view(), episode=EPISODE + 1),
            "other_position": logs(view(), position=POSITION + 1),
            "other_turn": logs(view(turn=TURN + 1)),
            "decision": logs(view(decision={"kind": "promote_active"})),
            "not_current": logs(view(current=1)),
            "phase": logs(view(phase="setup")),
            "not_ok": logs(dict(view(), ok=False)),
            "no_actor_logs": None,
        }
        for name, actor_logs in cases.items():
            with self.subTest(name):
                if actor_logs is None:
                    failure = J.lost_target_failure(entry(), trace=[entry()], actor_logs=None, header=header())
                    self.assertEqual(failure, "L6")
                    continue
                self.assert_undetermined(entry(), actor_logs, expected_failure="L6")

    def test_n8_accepted_before_in_the_same_episode(self):
        """N8: 同じエピソードで、この送信の前に受理がある（古い観測）。"""
        earlier = {"type": "attempt", "n": N - 1, "episode": EPISODE, "actor": ACTOR, "submit": {"outcome": D.ACCEPTED}}
        self.assert_undetermined(entry(), trace=[earlier, entry()], expected_failure="L6")
        later = dict(earlier, n=N + 1)  # 後の受理・別のエピソードの受理は関係しない
        failure = J.lost_target_failure(entry(), trace=[entry(), later, dict(earlier, episode=EPISODE - 1)], actor_logs=logs(view()), header=header())
        self.assertIsNone(failure)

    def test_n9_references(self):
        """N9: 参照の欠け・食い違い・重複。"""
        own_dup_energy = [zone(RAT, RATTATA, energy=(ENERGY,)), zone(FD, real=PSYCHIC, energy=(ENERGY,)), zone(USER, ROCKET_CHARMANDER)]
        own_dup_pid = [zone(FD, real=PSYCHIC, energy=(ENERGY,)), zone(FD, real=PSYCHIC), zone(USER, ROCKET_CHARMANDER)]
        cases = {
            "pokemon_not_in_view": (entry(meaning=meaning(source=99)), None, "L8"),
            "energy_not_attached": (entry(meaning=meaning(energy=99)), None, "L8"),
            "energy_on_two": (entry(), logs(view(own_bench=own_dup_energy)), "L8"),
            "pokemon_twice": (entry(), logs(view(own_bench=own_dup_pid)), "L8"),
            "face_down_mismatch": (entry(meaning=meaning(source=FD, source_face_down=False)), None, "L8"),
            "user_not_in_view": (entry(candidate=dict(candidate(), pokemon={"pokemon": 77, "card_id": ROCKET_CHARMANDER})), None, "L7"),
            "user_face_down_in_view": (entry(candidate=dict(candidate(), pokemon={"pokemon": FD, "card_id": ROCKET_CHARMANDER})), None, "L7"),
            "unknown_role": (entry(stages=[dict(stages()[0], role="other")] + stages()[1:]), None, "L5"),
            "role_meaning_mismatch": (entry(stages=[dict(stages()[0], meaning="card")] + stages()[1:]), None, "L5"),
            "no_meaning": (entry(meaning=[]), None, "L5"),
            "stage_missing": (entry(stages=stages()[:1]), None, "L5"),
        }
        for name, (e, actor_logs, expected) in cases.items():
            with self.subTest(name):
                self.assert_undetermined(e, actor_logs, expected_failure=expected)

    def test_n10_real_or_definition_missing(self):
        """N10: real がない・card_id がない・カードの一覧にない。"""
        no_real = zone(FD, real=PSYCHIC, energy=(ENERGY,))
        no_real.pop("real")
        no_card_id = zone(FD, real=PSYCHIC, energy=(ENERGY,))
        no_card_id["real"] = {"card": 109}
        unknown = zone(FD, real="ZZZ-999", energy=(ENERGY,))
        for name, fd in (("no_real", no_real), ("no_card_id", no_card_id), ("unknown_card", unknown)):
            with self.subTest(name):
                own = [zone(RAT, RATTATA, energy=(ENERGY_RAT,)), fd, zone(USER, ROCKET_CHARMANDER)]
                self.assert_undetermined(entry(), logs(view(own_bench=own)), expected_failure="L10")

    def test_n11_after_rejection_shape(self):
        """N11: 拒否のあとの形が違う（status・next・viewer・refetch_required・halt・continuable）。"""
        bad_continuable = rejected()
        bad_continuable["result"]["continuable"] = False
        cases = {"status": rejected(status="awaiting_decision"), "next": rejected(next_=[{"kind": "turn_action", "player": 1}]),
                 "viewer": rejected(viewer=1), "refetch": rejected(refetch=True), "halt": rejected(halt={"diagnostic_id": CODE}),
                 "continuable": bad_continuable}
        for name, submit in cases.items():
            with self.subTest(name):
                self.assert_undetermined(entry(submit=submit), expected_failure="L3")

    def test_n12_other_code_same_shape(self):
        """N12: 同じ形で別のコード（停止系・正常な拒否）は既存の判定のまま。"""
        for code in ("WRONG_ENERGY_TYPE", "UNSUPPORTED_SECRET_PLAN_IDENTITIES", "UNRESOLVED_ENERGY_BURN_TRANSFER"):
            if D.default_catalog().get(code) is None:
                continue
            with self.subTest(code):
                self.assert_rule6(entry(submit=rejected(code)), expected_failure="L2")

    def test_n13_refused_failed_and_category_mismatch_stay_suspect(self):
        """N13: refused・failed・コード表との分類の食い違いは既存の suspect のまま（規則 7 は上書きしない）。"""
        refused = {"ok": False, "outcome": "refused", "refusal": {"code": "STALE_HANDLE"}, "refetch_required": True, "result": None, "error": None}
        failed = dict(rejected(), outcome=D.FAILED)
        mismatch = rejected(category=D.RULING_UNRESOLVED)
        for name, submit in (("refused", refused), ("failed", failed), ("mismatch", mismatch)):
            with self.subTest(name):
                verdict = self.assert_rule6(entry(submit=submit), expected_failure="L1" if name != "mismatch" else "L2")
                self.assertEqual(verdict[0], J.SUSPECT)

    def test_n14_normal_accept_and_reject(self):
        """N14: 通常の受理・通常の拒否は既存の判定のまま。"""
        accepted = {"ok": True, "outcome": D.ACCEPTED, "refusal": None, "error": None, "refetch_required": False, "result": {"status": "in_progress"}}
        self.assertEqual(self.assert_rule6(entry(submit=accepted), expected_failure="L1"), (J.EXPECTED, []))
        self.assert_rule6(entry(submit=rejected("WRONG_ENERGY_TYPE")), expected_failure="L2")

    def test_n15_no_secret_in_reasons_rows_or_summary(self):
        """N15: 理由・judge_trace の行・要約に、場のポケモンの番号・uid・card_id・real が入らない（理由は固定の文字列だけ）。"""
        positive = entry()
        negative = entry(n=N + 1, meaning=meaning(source=OPP_FD, energy=ENERGY_OPP))
        opp = [zone(OPP_FD, real=KADABRA, energy=(ENERGY_OPP,), owner=1)]
        result = {"trace": [positive, negative], "actor_logs": logs(view(opp_bench=opp)), "record": {"header": header()},
                  "termination": {"class": "limit_operations", "detail": {}}}
        judged = B.judge_trace(result)
        self.assertEqual([r["verdict"] for r in judged["rows"]], [J.KNOWN_STOP, J.UNDETERMINED])
        text = json.dumps([judged["rows"], B.judge_summary(judged), judged["undetermined"]], ensure_ascii=False)
        for secret in (PSYCHIC, KADABRA, ROCKET_CHARMANDER, FIRE, "real", "pokemon_id", "face_down\""):
            self.assertNotIn(secret, text)
        for row in judged["rows"]:
            self.assertEqual(set(row), {"attempt", "kind", "outcome", "refusal", "diagnostic_id", "category", "engine_code", "verdict", "reasons"})
        self.assertEqual(judged["rows"][0]["reasons"], [D.UNSUPPORTED, CODE, "face_down_reveal_not_evaluated", "evidence:" + J.KNOWN_STOP_EVIDENCE[CODE]["condition"]])
        self.assertEqual(judged["rows"][1]["reasons"], UNDET[1])
        self.assertEqual(judged["known_stop"], [N])
        self.assertEqual(judged["rules_version"], 7)

    def test_n16_stop_policy_unchanged(self):
        """N16: 根拠が成り立たないときの undetermined の分類と停止方針は規則 6 と同じ（evidence_missing_stop は続ける）。known_stop も続ける。"""
        opp = [zone(OPP_FD, real=KADABRA, energy=(ENERGY_OPP,), owner=1)]
        for name, e, actor_logs in (("p2", entry(meaning=meaning(source=OPP_FD, energy=ENERGY_OPP)), logs(view(opp_bench=opp))),
                                    ("p1", entry(), logs(view()))):
            with self.subTest(name):
                judged = B.judge_trace({"trace": [e], "actor_logs": actor_logs, "record": {"header": header()},
                                        "termination": {"class": "limit_operations", "detail": {}}})
                summary = summary_and_rest(B.judge_summary(judged))
                stops, notes = B.stop_reasons(summary, B._policy_dict(B.StopPolicy()))
                self.assertEqual(stops, [])  # 止めない（続ける）
                if name == "p2":
                    self.assertEqual([u["category"] for u in judged["undetermined"]], [B.EVIDENCE_MISSING_STOP])
                    self.assertEqual(notes, ["undetermined:evidence_missing_stop:1"])
                else:
                    self.assertEqual(notes, ["known_stop:1"])


class BasisTest(unittest.TestCase):
    """L12: 判定に使うカードデータ・たねの判定・入口の処理が、記録を作ったエンジンと同じであること。"""

    def test_header_cases(self):
        other_engine = header()
        other_engine["engine"]["behavior_digest"] = "0" * 64
        other_data = header()
        other_data["dependencies"]["card_data"] = dict(other_data["dependencies"]["card_data"], commit="0" * 40)
        other_pool = header()
        other_pool["dependencies"]["card_pool"] = "custom"
        basis = J.lost_target_basis()
        cases = [("same_engine", header(), None, None), ("callable_header", header, None, None), ("no_header", None, None, "L12"),
                 ("other_engine_without_basis", other_engine, None, "L12"), ("other_engine_with_basis", other_engine, basis, None),
                 ("other_engine_with_other_basis", other_engine, dict(basis, digest="1" * 64), "L12"),
                 ("other_engine_with_other_method", other_engine, dict(basis, method="x"), "L12"),
                 ("other_card_data_even_with_basis", other_data, basis, "L12"), ("other_pool", other_pool, basis, "L12")]
        for name, hdr, b, expected in cases:
            with self.subTest(name):
                self.assertEqual(J.lost_target_failure(entry(), trace=[entry()], actor_logs=logs(view()), header=hdr, basis=b), expected)

    def test_basis_files_cover_the_judgement(self):
        basis = J.lost_target_basis()
        self.assertEqual(basis["method"], J.LOST_TARGET_BASIS_METHOD)
        self.assertEqual(basis["files"], ["cards.py", "data/kyuura_cards.json", "effects.py", "engine.py", "zones.py"])
        self.assertRegex(basis["digest"], "^[0-9a-f]{64}$")

    def test_batch_judge_trace_passes_basis(self):
        other_engine = header()
        other_engine["engine"]["behavior_digest"] = "0" * 64
        result = {"trace": [entry()], "actor_logs": logs(view()), "record": {"header": other_engine}, "termination": {"class": "limit_operations", "detail": {}}}
        self.assertEqual(B.judge_trace(result)["rows"][0]["verdict"], J.UNDETERMINED)
        self.assertEqual(B.judge_trace(result, basis=J.lost_target_basis())["rows"][0]["verdict"], J.KNOWN_STOP)
        self.assertEqual(B.judge_trace(dict(result, record=None))["rows"][0]["verdict"], J.UNDETERMINED)


# ---------------------------------------------------------------- 本物の runner に通す（構築盤面）


class _RecordedFixtureGame(_FixtureGame):
    """復元した対戦に、開始のスナップショットの識別と依存だけの header を持たせる（テストだけ。操作の記録は持たない）。"""

    def __init__(self, game, header_):
        super().__init__(game)
        self._header = header_

    def record(self):
        return {"header": copy.deepcopy(self._header)}

    def close(self):
        return self.record()


class RecordedFixtureRunner(FixtureRunner):
    def __init__(self, config, snapshot, *, with_header=True, **kw):
        super().__init__(config, snapshot, **kw)
        self._with_header = with_header

    def _start(self):
        super()._start()
        if self._with_header:
            data = json.loads(self._snapshot)
            self.game = _RecordedFixtureGame(self.game._game, {"engine": data["engine"], "dependencies": data["dependencies"]})


class P1Scripted(UniformPolicy):
    """ケースの選び手（方策ではない）: おもての使い手の use_power と、段ごとに (うらの場のポケモンか、エネルギーカードの card_id)。"""

    name, version = "scripted-lt-p1", 0

    def __init__(self, energy_card_id):
        super().__init__("scripted-lt-p1")
        self.energy_card_id = energy_card_id

    def choose(self, purpose, items, context):
        if purpose == "candidate":
            return next(i for i, c in enumerate(items) if c.get("kind") == "use_power" and not J.is_face_down_power(c)), "scripted"
        if purpose == "option":
            stage = context["stage"]
            by_id = {o["id"]: o for o in stage.get("options", [])}
            for i, oid in enumerate(items):
                o = by_id.get(oid, {})
                if (stage.get("role") == "source" and o.get("face_down") is True) or (stage.get("role") == "energy" and o.get("card_id") == self.energy_card_id):
                    return i, "scripted"
            raise LookupError(f"stage {stage.get('stage')}")
        if purpose == "count":
            return (items.index(1) if 1 in items else 0), "scripted"
        return 0, "scripted"


def run_p1(real, *, negative=None, with_header=True, counts=None):
    from tests.test_lost_target_own_face_down_v0_180 import board, own_face_down

    state, _fd, _energy = own_face_down(board(hand=(real, FIRE)), real, FIRE)
    text, error = F.snapshot_text(state, "LT-P1")
    assert text is not None, error

    def wrap(actor, endpoint):
        if counts is None:
            return endpoint

        class Counting:
            def handle(self, message):
                counts[message.get("type")] = counts.get(message.get("type"), 0) + 1
                return endpoint.handle(message)
        return Counting()

    config = V.Config(profile="boundary", limits=V.Limits(operations=1, seconds=60), run_id="test-lt-p1")
    runner = RecordedFixtureRunner(config, text, with_header=with_header, policy_factory=lambda seed, dist: P1Scripted(FIRE), negative=negative,
                                   wrap_endpoint=wrap)
    if counts is not None:
        original = runner._start

        def start():
            original()
            runner.endpoints = {k: wrap(k, v) for k, v in runner.endpoints.items()}
        runner._start = start
    return runner.run()


def submitted(result):
    return [e for e in result["trace"] if e.get("type") == "attempt" and e.get("submit") is not None]


class RunnerConnectionTest(unittest.TestCase):
    """構築盤面 → 本物の runner → バッチの入口と単局の入口。new_game からの対戦の実績には数えない。"""

    def test_non_basic_is_known_stop_in_both_entries(self):
        batch_counts, single_counts = {}, {}
        result = run_p1(PSYCHIC, counts=batch_counts)
        (e,) = submitted(result)
        self.assertEqual((e["submit"]["outcome"], e["submit"]["verifier"]["engine_code"]), (D.REJECTED, CODE))
        self.assertNotIn("judge", e)  # 変異の実行でなければ runner は判定を当てない
        self.assertIsNone(J.lost_target_failure(e, trace=result["trace"], actor_logs=result["actor_logs"], header=B.record_header(result["record"])))
        judged = B.judge_trace(result)
        self.assertEqual([(r["attempt"], r["verdict"]) for r in judged["rows"]], [(e["n"], J.KNOWN_STOP)])
        single = run_p1(PSYCHIC, negative=NoNegative(), counts=single_counts)
        (e_single,) = submitted(single)
        self.assertEqual(e_single["judge"], {"verdict": judged["rows"][0]["verdict"], "reasons": judged["rows"][0]["reasons"]})
        # 判定のための追加の要求はない（単局の判定を有効にしても、観測・候補・入力・check・submit の回数は同じ）・行動の列も同じ
        self.assertEqual(single_counts, batch_counts)
        from tools.verification_ai import records as R
        self.assertEqual(R.action_sequence(single["trace"]), R.action_sequence(result["trace"]))

    def test_j10_own_view_is_the_same_from_runner_and_saved_files(self):
        """J10: own_view_for が runner の actor_logs と、保存する actors/*.jsonl（batch.jsonl_bytes）を読んだ値で同じ行を返す。"""
        result = run_p1(PSYCHIC)
        (e,) = submitted(result)
        saved = {}
        for actor, rows in result["actor_logs"].items():
            saved[str(actor)] = [json.loads(line) for line in B.jsonl_bytes(rows).decode("utf-8").splitlines() if line.strip()]
        live = J.own_view_for(result["actor_logs"], e)
        self.assertIsNotNone(live)
        self.assertEqual(J.own_view_for(saved, e), live)
        reloaded = dict(result, actor_logs=saved, trace=[json.loads(json.dumps(x)) for x in result["trace"]])
        self.assertEqual(B.judge_trace(reloaded)["rows"], B.judge_trace(result)["rows"])

    def test_basic_and_missing_header_stay_undetermined_in_both_entries(self):
        """たねのうら（受理される）と、記録の header のない対戦（L12 を確かめられない）は known_stop にならない。単局とバッチで同じ。"""
        basic = run_p1(DIGLETT)
        (e,) = submitted(basic)
        self.assertEqual(e["submit"]["outcome"], D.ACCEPTED)
        self.assertEqual(B.judge_trace(basic)["rows"][0]["verdict"], J.EXPECTED)
        for negative in (None, NoNegative()):
            with self.subTest(single=negative is not None):
                result = run_p1(PSYCHIC, with_header=False, negative=negative)
                (e,) = submitted(result)
                judged = B.judge_trace(result)
                self.assertEqual(judged["rows"][0]["verdict"], J.UNDETERMINED)
                self.assertEqual(judged["undetermined"][0]["category"], B.EVIDENCE_MISSING_STOP)
                self.assertEqual(J.lost_target_failure(e, trace=result["trace"], actor_logs=result["actor_logs"], header=None), "L12")
                if negative is not None:
                    self.assertEqual(e["judge"], {"verdict": J.UNDETERMINED, "reasons": UNDET[1]})


class BoundaryTest(unittest.TestCase):
    def test_policy_and_input_generation_do_not_use_rule7(self):
        """方策・行動生成・変異・集計・記録の部品は規則 7 の部品を使わない（runner は変異の実行の中の判定でだけ submit_evidence を呼ぶ）。"""
        from pathlib import Path

        base = Path(J.__file__).resolve().parent
        for name in ("policies.py", "actions.py", "negative.py", "metrics.py", "records.py", "reach.py", "observe.py"):
            text = (base / name).read_text(encoding="utf-8")
            with self.subTest(name):
                for word in ("submit_evidence", "lost_target", "own_view_for", "recorded_stop_evidence"):
                    self.assertNotIn(word, text)
        runner_text = (base / "runner.py").read_text(encoding="utf-8")
        self.assertEqual(runner_text.count("submit_evidence("), 1)
        self.assertNotIn("lost_target", runner_text)


if __name__ == "__main__":
    unittest.main()
