"""検証用 AI の判定の規則 9（docs/verification-ai-lost-target-p2-p3o-design.md 2 章・9 章）: LOST_TARGET の P2-min（おもてのゲンガーの［のろい］
（効果の型 MoveOpponentDamageCounter）の target に相手のうらを 1 匹だけ指定し、source は相手のおもて）の UNSUPPORTED_SECRET_PLAN_LOST_TARGET の拒否を、
送った本人の送信前の観測（相手の本当のカードは持たない）・選んだ入力・診断・P2 用の basis で、条件 Q1〜Q12 をすべて確かめたときだけ known_stop にする。
相手の real・相手の観測・完全な記録は使わない。

- 人工の送信の行と観測で、正（相手の正体だけを変えても同じ）と負（欠落・古い観測・viewer・P1・混在・2 匹・energy・P3o・受理後・うらの使い手・対象外の力・
  参照と持ち主の矛盾・real の境界違反・別のコード・refused・failed・拒否後の状態変化・basis・複数の経路）を確かめる
- 構築盤面（``tests/test_lost_target_p2_min_v0_187.py`` の curse_board。new_game からの対戦ではない）を本物の runner に通し、逐次バッチの入口（``batch.judge_trace``）と
  単局の runner の判定（変異の実行の中）が同じ値になること、保存した actors から読み直しても同じことを確かめる
"""

from __future__ import annotations

import copy
import json
import unittest
from unittest import mock

from kyuura_engine import diagnostics as D
from kyuura_engine.cards import load_card_pool
from kyuura_engine.effects import DEFAULT_EFFECTS
from kyuura_engine.replay_record import current_identity

from tools.verification_ai import batch as B
from tools.verification_ai import fixtures_u_r3a as F
from tools.verification_ai import judge as J
from tools.verification_ai import runner as V
from tools.verification_ai.policies import UniformPolicy

from tests.helpers import DIGLETT, FIRE, GENGAR, HITMONCHAN, KADABRA, PSYCHIC, ROCKET_CHARMANDER
from tests.test_verification_ai_batch_judge import NoNegative, summary_and_rest
from tests.test_verification_ai_lost_target_p1 import RecordedFixtureRunner

CODE = "UNSUPPORTED_SECRET_PLAN_LOST_TARGET"
KEY = "UNSUPPORTED_SECRET_PLAN_LOST_TARGET#P2"
UNDET = ("undetermined", [f"stop_condition_not_evidenced:{CODE}"])
ACTOR, POSITION, EPISODE, TURN, N = 1, 3, 4, 7, 5
USER, SRC, FD, FD2, OWN_FD = 30, 1, 9, 11, 40  # 場のポケモンの番号（人工）。USER はゲンガー（本人）、SRC は相手のダメージのあるおもて、FD は相手のうら


def header():
    pool = load_card_pool()
    return {"engine": dict(current_identity()), "dependencies": {"rules": "JP-2000.02.14", "card_pool": "default", "effects": DEFAULT_EFFECTS.id,
                                                                 "card_data": {k: pool.source[k] for k in ("repository", "commit", "path")}}}


def face_up(pid, card_id, damage=0):
    return {"pokemon_id": pid, "card": 100 + pid, "card_id": card_id, "damage": damage, "energy": []}


def face_down(pid, *, real=None):
    z = {"pokemon_id": pid, "face_down": True, "damage": 0, "energy": [], "trainers": []}
    if real is not None:
        z["real"] = {"card": 100 + pid, "card_id": real}
    return z


def view(*, opp_bench=None, own_bench=None, turn=TURN, decision=None, phase="main", current=ACTOR, viewer=ACTOR, ok=True):
    """本人（主体 1）の観測。相手（主体 0）の場: バトル場はダメージ 10 のエビワラー、ベンチに相手のうら（real なし）。"""
    opp = opp_bench if opp_bench is not None else [face_down(FD)]
    own = own_bench if own_bench is not None else []
    return {"ok": ok, "type": "view", "viewer": viewer, "status": {"segment": 0, "status": "in_progress", "phase": phase},
            "observation": {"viewer": viewer, "current_player": current, "phase": phase, "decision": decision, "turn": turn,
                            "players": [{"player": 0, "active": face_up(SRC, HITMONCHAN, damage=10), "bench": opp},
                                        {"player": 1, "active": face_up(USER, GENGAR), "bench": own}]}}


def logs(*views, position=POSITION, episode=EPISODE):
    return {ACTOR: [{"type": "position", "position": position, "view": v, "episode": {"type": "episode", "episode": episode, "actor": ACTOR}} for v in views],
            0: [], "host": []}


def stages():
    return [{"stage": 1, "role": "source", "meaning": "pokemon", "input": "choose_option", "count": {"min": 1, "max": 1}},
            {"stage": 2, "role": "target", "meaning": "pokemon", "input": "choose_option", "depends_on_stage": 1, "count": {"min": 1, "max": 1}}]


def pokemon_option(pid, face_down_=False):
    o = {"pokemon": pid, "zone": "bench", "processability": "unverified" if face_down_ else "may_stop_later",
         "reasons": ["face_down_reveal_not_evaluated"] if face_down_ else ["continuation_not_evaluated"], "eligible": True}
    if face_down_:
        o["face_down"] = True
    return o


def meaning(source=SRC, target=FD, *, source_fd=False, target_fd=True):
    return [{"stage": 1, "option": pokemon_option(source, source_fd)}, {"stage": 2, "option": pokemon_option(target, target_fd)}]


def rejected(code=CODE, *, category=None, status="in_progress", next_=None, viewer=ACTOR, refetch=False, halt=None, public_code=None):
    entry = D.default_catalog().get(code)
    category = category or (entry.category if entry is not None else D.UNSUPPORTED)
    return {"ok": True, "outcome": D.REJECTED, "refetch_required": refetch, "refusal": None, "error": None,
            "result": {"outcome": D.REJECTED, "status": status, "continuable": True, "viewer": viewer, "role": "actor", "halt": halt,
                       "diagnostic_id": public_code or code, "category": category,
                       "next": [{"kind": "turn_action", "player": viewer}] if next_ is None else next_},
            "verifier": {"diagnostic_id": code, "category": category, "engine_code": code}}


def candidate(*, power_card=GENGAR, user_face_down=False):
    c = {"id": "c3", "kind": "use_power", "processability": "may_stop_later", "reasons": ["continuation_not_evaluated"],
         "pokemon": {"pokemon": USER, "card": 100 + USER, "card_id": GENGAR, "zone": "active"},
         "power": {"index": 0, "name_ja": "のろい", "card": 100 + USER, "card_id": power_card},
         "input_stages": [{"stage": 1}, {"stage": 2}]}
    if user_face_down:
        c["pokemon"] = {"pokemon": USER, "zone": "active", "face_down": True}
        c["power"] = {"index": 0, "face_down": True}
    return c


def entry(**over):
    e = {"type": "attempt", "n": N, "actor": ACTOR, "position": POSITION, "episode": EPISODE, "turn": [0, TURN], "candidate": candidate(),
         "stages": stages(), "meaning": meaning(), "submit": rejected()}
    e.update(over)
    return e


def judge(e, actor_logs=None, *, trace=None, hdr="default", basis_p2=None):
    actor_logs = logs(view()) if actor_logs is None else actor_logs
    trace = [e] if trace is None else trace
    hdr = header() if hdr == "default" else hdr
    failure = J.opponent_face_down_lost_target_failure(e, trace=trace, actor_logs=actor_logs, header=hdr, basis_p2=basis_p2)
    evidence = J.submit_evidence(e, trace=trace, actor_logs=actor_logs, header=hdr, basis_p2=basis_p2)
    verdict = J.judge_normal(e["candidate"], e.get("meaning") or [], e["submit"], stages=e.get("stages"), evidence=evidence)
    return failure, evidence, verdict


class VersionTest(unittest.TestCase):
    def test_versions_registration_and_basis(self):
        self.assertEqual(J.JUDGE_RULES_VERSION, 10)  # 規則 10（UNRESOLVED_RECOVER_ZERO_ENERGY）を足した（旧の期待は 9）。
        self.assertEqual(B.TOOL_VERSION, 15)  # 15: rules-v4（旧の期待は 14）。 14: rules-v3（旧の期待は 13）。 13: 規則 10（旧の期待は 12）。
        self.assertEqual((B.PLAN_FORMAT, B.COMPLETE_FORMAT), ("kyuura-vai-batch-plan/7", "kyuura-vai-batch-complete/7"))  # 形式は変えない
        self.assertEqual(J.LOST_TARGET_P2_EVIDENCE, KEY)
        self.assertEqual(J.KNOWN_STOP_EVIDENCE[KEY]["code"], CODE)
        self.assertEqual(J.LOST_TARGET_P2_POWER_EFFECTS, frozenset({"move_opponent_damage_counter"}))
        self.assertEqual(J.LOST_TARGET_P2_CONDITIONS, ("Q1", "Q2", "Q3", "Q4", "Q12", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10", "Q11"))
        basis = J.lost_target_p2_basis()
        self.assertEqual(basis["method"], "kyuura-lost-target-p2-basis-sha256/1")
        self.assertEqual(basis["files"], ["cards.py", "data/kyuura_cards.json", "effects.py", "engine.py", "zones.py", "observation.py", "state.py"])
        self.assertRegex(basis["digest"], "^[0-9a-f]{64}$")
        self.assertNotEqual(basis["digest"], J.lost_target_basis()["digest"])
        self.assertNotEqual(basis["digest"], J.lost_target_p3_basis()["digest"])


class PositiveTest(unittest.TestCase):
    def test_curse_target_on_a_single_opponent_face_down_is_known_stop(self):
        failure, evidence, (verdict, why) = judge(entry())
        self.assertEqual((failure, evidence, verdict), (None, KEY, J.KNOWN_STOP))
        self.assertEqual(why, [D.UNSUPPORTED, CODE, "continuation_not_evaluated", "face_down_reveal_not_evaluated", "evidence:" + J.KNOWN_STOP_EVIDENCE[KEY]["condition"]])

    def test_judgement_does_not_depend_on_the_opponent_identity(self):
        """相手の正体だけが違う記録（判定に使う値は同じ）: 同じ判定・同じ理由。判定は相手の real を読まないので、観測に real がなければ値は同じ。"""
        results = []
        for real in (DIGLETT, KADABRA, FIRE, PSYCHIC):
            actor_logs = logs(view())
            # 相手（主体 0）自身の観測には本当のカードがある。判定は送った本人の観測だけを読むので、相手の記録の値が違っても同じ
            actor_logs[0] = [{"type": "position", "position": POSITION, "episode": {"type": "episode", "episode": EPISODE, "actor": 0},
                              "view": dict(view(viewer=0, current=0, opp_bench=[]), observation=dict(view()["observation"], viewer=0,
                                                                                                       players=[{"player": 0, "active": face_up(SRC, HITMONCHAN, 10), "bench": [face_down(FD, real=real)]},
                                                                                                                {"player": 1, "active": face_up(USER, GENGAR), "bench": []}]))}]
            results.append(judge(entry(), actor_logs))
        self.assertEqual(len({json.dumps(r, sort_keys=True, default=str) for r in results}), 1)
        self.assertEqual(results[0][1], KEY)


class NegativeTest(unittest.TestCase):
    def assert_undetermined(self, e, actor_logs=None, *, expected_failure, **kw):
        failure, evidence, verdict = judge(e, actor_logs, **kw)
        self.assertEqual(failure, expected_failure)
        self.assertNotEqual(evidence, KEY)
        rule8 = J.judge_normal(e["candidate"], e.get("meaning") or [], e["submit"], stages=e.get("stages"),
                               evidence=J.recorded_stop_evidence(e["candidate"], e.get("meaning") or [], e.get("stages"), e["submit"]))
        self.assertEqual(verdict, rule8)
        return verdict

    def test_missing_stale_and_viewer(self):
        cases = {"missing": ({ACTOR: [], 0: [], "host": []}, None), "duplicated": (logs(view(), view()), None),
                 "other_episode": (logs(view(), episode=EPISODE + 1), None), "other_turn": (logs(view(turn=TURN + 1)), None),
                 "viewer": (logs(view(viewer=0)), None), "not_current": (logs(view(current=0)), None), "decision": (logs(view(decision={"kind": "x"})), None),
                 "not_ok": (logs(view(ok=False)), None)}
        for name, (actor_logs, _x) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.assert_undetermined(entry(), actor_logs, expected_failure="Q6"), UNDET)
        earlier = {"type": "attempt", "n": N - 1, "episode": EPISODE, "actor": ACTOR, "submit": {"outcome": D.ACCEPTED}}
        self.assert_undetermined(entry(), trace=[earlier, entry()], expected_failure="Q6")

    def test_p1_and_mixed_own_and_opponent(self):
        own = [face_down(OWN_FD, real=KADABRA)]
        # 本人のうらだけ（P1）: 規則 9 は Q9 で外れ、規則 7 の根拠（P1）になる（規則 9 は P1 を上書きしない）
        failure, evidence, (verdict, _why) = judge(entry(meaning=meaning(target=OWN_FD)), logs(view(own_bench=own)))
        self.assertEqual((failure, evidence, verdict), ("Q9", CODE, J.KNOWN_STOP))
        e = entry(meaning=meaning(source=OWN_FD, source_fd=True))  # 本人のうら（source）と相手のうら（target）
        self.assert_undetermined(e, logs(view(own_bench=own)), expected_failure="Q9")

    def test_two_opponent_face_downs_and_source_face_down(self):
        e = entry(meaning=meaning(source=FD2, source_fd=True))
        self.assert_undetermined(e, logs(view(opp_bench=[face_down(FD), face_down(FD2)])), expected_failure="Q9")
        e = entry(meaning=meaning(source=FD, target=SRC, source_fd=True, target_fd=False))  # source に相手のうら（エンジンは NO_DAMAGE_COUNTERS を先に出す形）
        self.assert_undetermined(e, expected_failure="Q9")

    def test_energy_stage_and_other_stage_shapes(self):
        energy_stages = stages() + [{"stage": 3, "role": "energy", "meaning": "card", "input": "choose_option"}]
        e = entry(stages=energy_stages, meaning=meaning() + [{"stage": 3, "option": {"card": 77}}])
        self.assert_undetermined(e, expected_failure="Q5")
        self.assert_undetermined(entry(meaning=meaning()[1:]), expected_failure="Q5")  # target だけ
        self.assert_undetermined(entry(stages=[dict(stages()[0], role="target"), stages()[1]]), expected_failure="Q5")

    def test_p3o_after_acceptance_and_face_down_user(self):
        p3o = entry(candidate={"id": "c1", "kind": "answer_decision", "processability": "may_stop_later", "reasons": ["continuation_not_evaluated"]})
        self.assert_undetermined(p3o, expected_failure="Q4")
        after = entry(candidate=dict(candidate(), kind="play_trainer"))
        self.assert_undetermined(after, expected_failure="Q4")
        self.assert_undetermined(entry(candidate=candidate(user_face_down=True)), expected_failure="Q4")
        plain = [{"stage": m["stage"], "option": dict(m["option"], reasons=["continuation_not_evaluated"])} for m in meaning()]
        failure, evidence, _ = judge(entry(meaning=plain))
        self.assertEqual((failure, evidence), ("Q4", None))

    def test_other_power_and_copied_power(self):
        self.assert_undetermined(entry(candidate=candidate(power_card=ROCKET_CHARMANDER)), expected_failure="Q12")
        copied = candidate()
        copied["power"] = dict(copied["power"], card=999)
        self.assert_undetermined(entry(candidate=copied), expected_failure="Q12")
        no_index = candidate()
        no_index["power"] = {k: v for k, v in no_index["power"].items() if k != "index"}
        self.assert_undetermined(entry(candidate=no_index), expected_failure="Q12")

    def test_reference_owner_and_state_contradictions(self):
        cases = {
            "target_not_in_view": (entry(meaning=meaning(target=99)), None, "Q8"),
            "face_down_mismatch": (entry(meaning=[meaning()[0], {"stage": 2, "option": {k: v for k, v in pokemon_option(FD, True).items() if k != "face_down"}}]), None, "Q8"),
            "target_twice": (entry(), logs(view(opp_bench=[face_down(FD), face_down(FD)])), "Q8"),
            "user_not_in_view": (entry(candidate=dict(candidate(), pokemon={"pokemon": 77, "card": 100 + USER, "card_id": GENGAR})), None, "Q7"),
            "source_is_own": (entry(meaning=meaning(source=USER)), None, "Q9"),
            "target_face_up": (entry(candidate=dict(candidate(), reasons=["face_down_reveal_not_evaluated"]), meaning=meaning(target=SRC, target_fd=False, source=SRC)), None, "Q9"),
        }
        for name, (e, actor_logs, expected) in cases.items():
            with self.subTest(name):
                self.assert_undetermined(e, actor_logs, expected_failure=expected)

    def test_real_on_the_opponent_row_is_a_boundary_violation(self):
        self.assert_undetermined(entry(), logs(view(opp_bench=[face_down(FD, real=KADABRA)])), expected_failure="Q10")

    def test_other_code_refused_failed_and_after_state(self):
        for code in ("UNSUPPORTED_SECRET_PLAN_IDENTITIES", "UNRESOLVED_KEEP_PROTECTED_TARGET", "NO_DAMAGE_COUNTERS"):
            if D.default_catalog().get(code) is None:
                continue
            with self.subTest(code):
                self.assert_undetermined(entry(submit=rejected(code)), expected_failure="Q2")
        refused = {"ok": False, "outcome": "refused", "refusal": {"code": "STALE_HANDLE"}, "refetch_required": True, "result": None, "error": None}
        for name, submit in (("refused", refused), ("failed", dict(rejected(), outcome=D.FAILED))):
            with self.subTest(name):
                self.assertEqual(self.assert_undetermined(entry(submit=submit), expected_failure="Q1")[0], J.SUSPECT)
        for name, submit in (("status", rejected(status="awaiting_decision")), ("refetch", rejected(refetch=True)), ("next", rejected(next_=[]))):
            with self.subTest(name):
                self.assert_undetermined(entry(submit=submit), expected_failure="Q3")

    def test_basis(self):
        other = header()
        other["engine"]["behavior_digest"] = "0" * 64
        basis = J.lost_target_p2_basis()
        other_effects = header()
        other_effects["dependencies"]["effects"] = "other"
        cases = [("same", header(), None, None), ("no_header", None, None, "Q11"), ("other_engine", other, None, "Q11"),
                 ("other_engine_with_p2_basis", other, basis, None), ("other_engine_with_wrong_digest", other, dict(basis, digest="1" * 64), "Q11"),
                 ("other_engine_with_p1_basis", other, J.lost_target_basis(), "Q11"), ("other_effects", other_effects, basis, "Q11")]
        for name, hdr, b, expected in cases:
            with self.subTest(name):
                self.assertEqual(J.opponent_face_down_lost_target_failure(entry(), trace=[entry()], actor_logs=logs(view()), header=hdr, basis_p2=b), expected)

    def test_several_routes_at_once_is_undetermined(self):
        """複数の経路（P1・P2・P3s）が同時に根拠を返す証拠は、どれにも決めない（起こらないはずの矛盾）。"""
        with mock.patch.object(J, "own_face_down_lost_target_evidence", return_value=CODE):
            failure, evidence, verdict = judge(entry())
        self.assertIsNone(failure)
        self.assertIsNone(evidence)
        self.assertEqual(verdict, UNDET)

    def test_stop_policy_and_no_secret_in_rows(self):
        positive, negative = entry(), entry(n=N + 1, meaning=meaning(target=99))
        result = {"trace": [positive, negative], "actor_logs": logs(view()), "record": {"header": header()}, "termination": {"class": "limit_operations", "detail": {}}}
        judged = B.judge_trace(result)
        self.assertEqual([r["verdict"] for r in judged["rows"]], [J.KNOWN_STOP, J.UNDETERMINED])
        self.assertEqual(judged["rules_version"], 10)  # 規則 10（UNRESOLVED_RECOVER_ZERO_ENERGY）を足した（旧の期待は 9）。
        summary = summary_and_rest(B.judge_summary(judged))
        stops, notes = B.stop_reasons(summary, B._policy_dict(B.StopPolicy()))
        self.assertEqual(stops, [])
        self.assertEqual(sorted(notes), ["known_stop:1", "undetermined:evidence_missing_stop:1"])
        text = json.dumps([judged["rows"], B.judge_summary(judged)], ensure_ascii=False)
        for secret in (GENGAR, HITMONCHAN, "real", "pokemon_id"):
            self.assertNotIn(secret, text)


# ---------------------------------------------------------------- 本物の runner に通す（構築盤面）


class CurseScripted(UniformPolicy):
    """ケースの選び手（方策ではない）: ゲンガーの［のろい］、source は相手のダメージのあるおもて、target は相手のうら。"""

    name, version = "scripted-lt-p2", 0

    def __init__(self):
        super().__init__("scripted-lt-p2")

    def choose(self, purpose, items, context):
        if purpose == "candidate":
            return next(i for i, c in enumerate(items) if c.get("kind") == "use_power" and (c.get("power") or {}).get("card_id") == GENGAR), "scripted"
        if purpose == "option":
            stage = context["stage"]
            opts = stage.get("options") or []
            by_id = {o["id"]: o for o in opts}
            for i, oid in enumerate(items):
                o = by_id.get(oid, {})
                if (stage.get("role") == "source" and o.get("face_down") is not True) or (stage.get("role") == "target" and o.get("face_down") is True):
                    return i, "scripted"
            raise LookupError(f"stage {stage.get('stage')}")
        return 0, "scripted"


def run_p2(real, *, negative=None, with_header=True):
    from tests.test_lost_target_p2_min_v0_187 import curse_board

    state, *_ = curse_board(real)
    text, error = F.snapshot_text(state, "LT-P2")
    assert text is not None, error
    config = V.Config(profile="boundary", limits=V.Limits(operations=1, seconds=60), run_id="test-lt-p2")
    return RecordedFixtureRunner(config, text, with_header=with_header, policy_factory=lambda seed, dist: CurseScripted(), negative=negative).run()


def submitted(result):
    return [e for e in result["trace"] if e.get("type") == "attempt" and e.get("submit") is not None]


class RunnerConnectionTest(unittest.TestCase):
    """構築盤面 → 本物の runner → バッチの入口と単局の入口。new_game からの対戦の実績には数えない。"""

    def test_known_stop_in_both_entries_for_every_identity(self):
        rows = []
        for real in (KADABRA, DIGLETT, FIRE):
            with self.subTest(real=real):
                result = run_p2(real)
                (e,) = submitted(result)
                self.assertEqual((e["submit"]["outcome"], e["submit"]["verifier"]["engine_code"]), (D.REJECTED, CODE))
                self.assertIsNone(J.opponent_face_down_lost_target_failure(e, trace=result["trace"], actor_logs=result["actor_logs"],
                                                                          header=B.record_header(result["record"])))
                judged = B.judge_trace(result)
                self.assertEqual([r["verdict"] for r in judged["rows"]], [J.KNOWN_STOP])
                single = run_p2(real, negative=NoNegative())
                (e_single,) = submitted(single)
                self.assertEqual(e_single["judge"], {"verdict": judged["rows"][0]["verdict"], "reasons": judged["rows"][0]["reasons"]})
                rows.append(judged["rows"][0])
                # 保存の形（actors/*.jsonl）から読み直しても同じ
                saved = {str(a): [json.loads(x) for x in B.jsonl_bytes(r).decode("utf-8").splitlines() if x.strip()] for a, r in result["actor_logs"].items()}
                reloaded = dict(result, actor_logs=saved, trace=[json.loads(json.dumps(x)) for x in result["trace"]])
                self.assertEqual(B.judge_trace(reloaded)["rows"], judged["rows"])
                # 本人の観測の相手のうらの行に real がない
                view = J.own_view_for(result["actor_logs"], e)
                self.assertTrue(all("real" not in z for owner, z in J._field_rows(view["observation"]) if owner != e["actor"]))
        self.assertEqual(len({json.dumps(r, sort_keys=True) for r in rows}), 1)  # 相手の正体だけが違う 3 局面で、同じ判定の行

    def test_missing_header_is_undetermined_in_both_entries(self):
        for negative in (None, NoNegative()):
            with self.subTest(single=negative is not None):
                result = run_p2(KADABRA, with_header=False, negative=negative)
                (e,) = submitted(result)
                judged = B.judge_trace(result)
                self.assertEqual(judged["rows"][0]["verdict"], J.UNDETERMINED)
                self.assertEqual(judged["undetermined"][0]["category"], B.EVIDENCE_MISSING_STOP)
                self.assertEqual(J.opponent_face_down_lost_target_failure(e, trace=result["trace"], actor_logs=result["actor_logs"], header=None), "Q11")
                if negative is not None:
                    self.assertEqual(e["judge"], {"verdict": J.UNDETERMINED, "reasons": UNDET[1]})

    def test_batch_judge_trace_passes_basis_p2(self):
        result = run_p2(KADABRA)
        hdr = copy.deepcopy(B.record_header(result["record"]))
        hdr["engine"]["behavior_digest"] = "0" * 64
        other = dict(result, record={"header": hdr})
        self.assertEqual(B.judge_trace(other)["rows"][0]["verdict"], J.UNDETERMINED)
        self.assertEqual(B.judge_trace(other, basis_p2=J.lost_target_p2_basis())["rows"][0]["verdict"], J.KNOWN_STOP)
        self.assertEqual(B.judge_trace(other, basis=J.lost_target_basis())["rows"][0]["verdict"], J.UNDETERMINED)  # P1 の basis では通らない


if __name__ == "__main__":
    unittest.main()
