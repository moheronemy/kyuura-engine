"""検証用 AI の判定の規則 8（docs/verification-ai-lost-target-p3-decision-design.md 4 章・5 章・6.3 節・10 章）: LOST_TARGET の P3s（使っているトレーナー
AttachedDamageReduction の select_pokemon 1 つへの回答で、本人のうらのカードを指定した UNSUPPORTED_SECRET_PLAN_LOST_TARGET の拒否）を、送った本人の送信前の観測と
エンジンの効果の登録・カードデータ・たねの判定で、条件 D1〜D12 をすべて確かめたときだけ known_stop にする（根拠の鍵 ``LOST_TARGET_P3_EVIDENCE``）。

- 人工の送信の行と観測（保存済みの r1 の P3 の行の形を写す。局・seed・本当のカードの値は写さない）で、正と設計 6.3 節の負の条件を確かめる
- 構築盤面（``tests/test_lost_target_p3_decision_v0_181.py`` の own_face_down・defender_decision。new_game からの対戦ではない）を本物の runner に通し、逐次バッチの入口
  （``batch.judge_trace``）と単局の runner の判定が同じ値になること、判定のための要求が増えないことを確かめる
"""

from __future__ import annotations

import copy
import json
import unittest

from kyuura_engine import diagnostics as D
from kyuura_engine.cards import load_card_pool
from kyuura_engine.effects import DEFAULT_EFFECTS, TEXT_PRE_NEO, card_is_basic_in_text
from kyuura_engine.replay_record import current_identity

from tools.verification_ai import batch as B
from tools.verification_ai import fixtures_u_r3a as F
from tools.verification_ai import judge as J
from tools.verification_ai import runner as V
from tools.verification_ai.policies import UniformPolicy

from tests.helpers import DEFENDER, DIGLETT, ENERGY_REMOVAL, HITMONCHAN, KADABRA, PSYCHIC, SWITCH
from tests.test_verification_ai_batch_judge import NoNegative, summary_and_rest
from tests.test_verification_ai_lost_target_p1 import RecordedFixtureRunner
from tests.test_verification_ai_lost_target_p1 import entry as p1_entry
from tests.test_verification_ai_lost_target_p1 import header as p1_header
from tests.test_verification_ai_lost_target_p1 import logs as p1_logs
from tests.test_verification_ai_lost_target_p1 import view as p1_view

CODE = J.LOST_TARGET_CODE
KEY = J.LOST_TARGET_P3_EVIDENCE
UNDET = (J.UNDETERMINED, [f"stop_condition_not_evidenced:{CODE}"])
PICHU = "neo1-042"
ACTOR, POSITION, EPISODE, TURN, N = 0, 3, 4, 7, 5
ACT, FD, FD2, OPP_ACT, OPP_FD = 1, 9, 11, 21, 20  # 場のポケモンの番号（人工）


def header():
    pool = load_card_pool()
    return {"engine": dict(current_identity()), "dependencies": {"rules": "JP-2000.02.14", "card_pool": "default",
                                                                 "card_data": {k: pool.source[k] for k in ("repository", "commit", "path")},
                                                                 "effects": DEFAULT_EFFECTS.id}}


def zone(pid, card_id=None, *, real=None, owner=0):
    z = {"pokemon_id": pid, "energy": []}
    if real is not None:
        z.update({"face_down": True, **({"real": {"card": 100 + pid, "card_id": real}} if owner == ACTOR else {})})
    else:
        z.update({"card": 100 + pid, "card_id": card_id})
    return z


def own_field(real=PSYCHIC):
    return zone(ACT, HITMONCHAN), [zone(FD, real=real)]


def decision(values=(ACT, FD), *, kind="select_pokemon", player=ACTOR, meaning="pokemon", mx=1):
    return {"kind": kind, "player": player, "min_choices": 1, "max_choices": mx, "option_count": len(values), "options": [{"value": v} for v in values],
            "meaning": meaning}


def trainer(card_id=DEFENDER, *, player=ACTOR, user=ACTOR):
    return {"player": player, "user": user, "card": 77, "card_id": card_id}


def view(*, real=PSYCHIC, own=None, opp_bench=None, turn=TURN, dec="default", phase="decision", current=ACTOR, viewer=ACTOR, used="default"):
    active, bench = own if own is not None else own_field(real)
    return {"ok": True, "type": "view", "viewer": viewer, "status": {"segment": 0, "status": "awaiting_decision", "phase": phase},
            "observation": {"viewer": viewer, "current_player": current, "phase": phase, "decision": decision() if dec == "default" else dec, "turn": turn,
                            "trainer_in_use": trainer() if used == "default" else used,
                            "players": [{"player": 0, "active": active, "bench": bench},
                                        {"player": 1, "active": zone(OPP_ACT, HITMONCHAN), "bench": opp_bench or []}]}}


def logs(*views, position=POSITION, episode=EPISODE):
    return {ACTOR: [{"type": "position", "position": position, "view": v, "episode": {"type": "episode", "episode": episode, "actor": ACTOR}} for v in views],
            1: [], "host": []}


def option(oid, value, reasons=None):
    o = {"id": oid, "value": value}
    if reasons is not None:
        o.update({"processability": "may_stop_later", "reasons": reasons})
    return o


def stages(values=(ACT, FD), *, kind="select_pokemon", meaning="pokemon", mx=1, option_reasons=None):
    return [{"stage": 1, "input": "choose_option", "decision_kind": kind, "meaning": meaning, "count": {"min": 1, "max": mx}, "order": "not_applicable",
             "options": [option(f"o{i + 1}", v, (option_reasons or {}).get(v)) for i, v in enumerate(values)]}]


def rejected(code=CODE, *, category=None, status="awaiting_decision", next_=None, viewer=ACTOR, refetch=False, halt=None, public_code=None):
    entry_ = D.default_catalog().get(code)
    category = category or (entry_.category if entry_ is not None else D.UNSUPPORTED)
    return {"ok": True, "outcome": D.REJECTED, "refetch_required": refetch, "refusal": None, "error": None,
            "result": {"outcome": D.REJECTED, "status": status, "continuable": True, "viewer": viewer, "role": "actor", "halt": halt,
                       "diagnostic_id": public_code or code, "category": category,
                       "next": [{"kind": "answer_decision", "player": viewer}] if next_ is None else next_},
            "verifier": {"diagnostic_id": code, "category": category, "engine_code": code}}


def candidate(reasons=("continuation_not_evaluated",)):
    return {"id": "c1", "kind": "answer_decision", "processability": "may_stop_later", "reasons": list(reasons), "input_stages": [{"stage": 1}]}


def entry(**over):
    e = {"type": "attempt", "n": N, "actor": ACTOR, "position": POSITION, "episode": EPISODE, "turn": [0, TURN], "candidate": candidate(),
         "stages": stages(), "choices": ["o2"], "meaning": [{"stage": 1, "option": option("o2", FD)}], "submit": rejected()}
    e.update(over)
    return e


def judge(e, actor_logs=None, *, trace=None, hdr="default", basis=None, basis_p3=None):
    actor_logs = logs(view()) if actor_logs is None else actor_logs
    trace = [e] if trace is None else trace
    hdr = header() if hdr == "default" else hdr
    failure = J.decision_lost_target_failure(e, trace=trace, actor_logs=actor_logs, header=hdr, basis_p3=basis_p3)
    evidence = J.submit_evidence(e, trace=trace, actor_logs=actor_logs, header=hdr, basis=basis, basis_p3=basis_p3)
    verdict = J.judge_normal(e["candidate"], e.get("meaning") or [], e["submit"], stages=e.get("stages"), evidence=evidence)
    return failure, evidence, verdict


POSITIVE_REASONS = [D.UNSUPPORTED, CODE, "continuation_not_evaluated", "evidence:" + J.KNOWN_STOP_EVIDENCE[KEY]["condition"]]


class RegistrationTest(unittest.TestCase):
    def test_versions_key_and_code(self):
        self.assertEqual((J.JUDGE_RULES_VERSION, B.TOOL_VERSION), (8, 10))
        self.assertEqual((B.PLAN_FORMAT, B.COMPLETE_FORMAT), ("kyuura-vai-batch-plan/6", "kyuura-vai-batch-complete/6"))
        self.assertEqual(KEY, "UNSUPPORTED_SECRET_PLAN_LOST_TARGET#P3")
        self.assertNotEqual(KEY, CODE)  # 根拠の鍵（経路の名前）と生の診断コードは別
        self.assertEqual(J.KNOWN_STOP_EVIDENCE[KEY]["code"], CODE)
        self.assertNotIn(KEY, J.RECORDED_STOP_CONDITIONS)
        self.assertIsNone(D.default_catalog().get(KEY))  # 診断のコード表に新しいコードを足していない
        self.assertEqual(J.LOST_TARGET_DECISION_EFFECTS, frozenset({"attached_damage_reduction"}))
        self.assertEqual(J.LOST_TARGET_P3_CONDITIONS, tuple(f"D{i}" for i in range(1, 13)))

    def test_matching_rule_keeps_existing_entries(self):
        """照合: 項目の code（なければ鍵）が元のコードと同じときだけ。既存の 3 項目は鍵 = 元のコード = 根拠のときだけ（規則 7 と同じ）。P3 の鍵を別のコードの停止に渡しても通らない。"""
        diag = {"engine_code": CODE}
        cat = J._catalog_category(CODE)
        for evidence, expected in ((CODE, J.KNOWN_STOP), (KEY, J.KNOWN_STOP), (None, J.UNDETERMINED), ("OTHER", J.UNDETERMINED)):
            with self.subTest(evidence):
                self.assertEqual(J._known_stop_or_undetermined(candidate(), [], diag, D.UNSUPPORTED, cat, evidence)[0], expected)
        self.assertEqual(J._known_stop_or_undetermined(candidate(), [], diag, D.UNSUPPORTED, cat, CODE)[1][-1],
                         "evidence:" + J.KNOWN_STOP_EVIDENCE[CODE]["condition"])  # P1 の理由の文は変わらない
        other = "UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE"
        verdict = J._known_stop_or_undetermined(candidate(), [], {"engine_code": other}, J._catalog_category(other), J._catalog_category(other), KEY)
        self.assertEqual(verdict, (J.UNDETERMINED, [f"stop_condition_not_evidenced:{other}"]))


class PositiveTest(unittest.TestCase):
    def test_saved_r1_shape_is_known_stop(self):
        """保存済みの r1 の P3 の行の形（ディフェンダーの select_pokemon の 2 つ目に、本人のたねでないうら）。理由は 4 項目（設計 4.2 節）。"""
        failure, evidence, verdict = judge(entry())
        self.assertEqual((failure, evidence, verdict), (None, KEY, (J.KNOWN_STOP, POSITIVE_REASONS)))

    def test_reason_on_the_chosen_option_only(self):
        """理由 continuation_not_evaluated が、候補になく選んだ選べるものにだけある形も足りる（P1 と同じ範囲）。"""
        e = entry(candidate=candidate(reasons=()), meaning=[{"stage": 1, "option": option("o2", FD, ["continuation_not_evaluated"])}])
        failure, evidence, (verdict, _) = judge(e)
        self.assertEqual((failure, evidence, verdict), (None, KEY, J.KNOWN_STOP))

    def test_other_non_basic_kinds_and_more_bench(self):
        """たねでない本当のカード（エネルギー・1 進化）。ベンチにおもてのポケモンがほかにいても、選べるものが場の並びと同じなら足りる。"""
        for real in (PSYCHIC, KADABRA):
            with self.subTest(real=real):
                own = (zone(ACT, HITMONCHAN), [zone(FD2, DIGLETT), zone(FD, real=real)])
                e = entry(stages=stages((ACT, FD2, FD)), choices=["o3"], meaning=[{"stage": 1, "option": option("o3", FD)}])
                self.assertEqual(judge(e, logs(view(own=own, dec=decision((ACT, FD2, FD)))))[:2], (None, KEY))


class NegativeTest(unittest.TestCase):
    """どれも known_stop にしない（規則 7 と同じ判定・同じ理由・同じ分類）。"""

    def assert_rule7(self, e, actor_logs=None, *, expected_failure, **kw):
        failure, evidence, verdict = judge(e, actor_logs, **kw)
        self.assertEqual(failure, expected_failure)
        self.assertIsNone(evidence)
        hdr = header() if kw.get("hdr", "default") == "default" else kw["hdr"]
        rule7 = J.judge_normal(e["candidate"], e.get("meaning") or [], e["submit"], stages=e.get("stages"),
                               evidence=J.recorded_stop_evidence(e["candidate"], e.get("meaning") or [], e.get("stages"), e["submit"])
                               or J.own_face_down_lost_target_evidence(e, trace=kw.get("trace") or [e], actor_logs=actor_logs or logs(view()), header=hdr,
                                                                       basis=kw.get("basis")))
        self.assertEqual(verdict, rule7)
        return verdict

    def assert_undetermined(self, e, actor_logs=None, *, expected_failure, **kw):
        verdict = self.assert_rule7(e, actor_logs, expected_failure=expected_failure, **kw)
        self.assertEqual(verdict, UNDET)  # 先頭 stop_condition_not_evidenced: と理由の並び
        self.assertEqual(B.undetermined_category("submit", verdict[1]), B.EVIDENCE_MISSING_STOP)

    def test_opponent_face_down_p3o(self):
        """相手のうら（P3o）を選んだ形（選べるものが本人の場の並びと違う → D8。並びを合わせても参照が相手 → D9）。"""
        opp = [zone(OPP_FD, real=KADABRA, owner=1)]
        e = entry(stages=stages((ACT, OPP_FD)), meaning=[{"stage": 1, "option": option("o2", OPP_FD)}])
        self.assert_undetermined(e, logs(view(opp_bench=opp, dec=decision((ACT, OPP_FD)))), expected_failure="D8")
        own = (zone(ACT, HITMONCHAN), [zone(OPP_FD, real=KADABRA, owner=1)])  # 並びは本人の場と同じだが、その番号の場のポケモンは相手の場にもある（2 つ）
        self.assert_undetermined(e, logs(view(own=own, opp_bench=opp, dec=decision((ACT, OPP_FD)))), expected_failure="D9")

    def test_face_up_target_and_no_face_down(self):
        """おもての対象（うらの指定なし）。"""
        e = entry(choices=["o1"], meaning=[{"stage": 1, "option": option("o1", ACT)}])
        self.assert_undetermined(e, expected_failure="D9")

    def test_basic_and_baby_are_contradictions(self):
        """本当のカードがたね・ベイビィ（エンジンはおもてにして続けるはず）。同じ関数（card_is_basic_in_text）の答え。"""
        for real in (DIGLETT, PICHU):
            with self.subTest(real=real):
                self.assertIs(card_is_basic_in_text(load_card_pool().get(real), TEXT_PRE_NEO), True)
                self.assert_undetermined(entry(), logs(view(real=real)), expected_failure="D11")

    def test_real_missing_or_unknown(self):
        no_real = zone(FD, real=PSYCHIC)
        no_real.pop("real")
        for name, fd in (("no_real", no_real), ("unknown", zone(FD, real="ZZZ-999"))):
            with self.subTest(name):
                self.assert_undetermined(entry(), logs(view(own=(zone(ACT, HITMONCHAN), [fd]))), expected_failure="D10")

    def test_decision_shape(self):
        """別の決定の種類・意味・複数選択・段の数・choices と meaning の不一致。"""
        two = [{"stage": 1, "option": option("o1", ACT)}, {"stage": 1, "option": option("o2", FD)}]
        cases = {
            "other_kind": entry(stages=stages(kind="select_bench_pokemon")),
            "card_meaning": entry(stages=stages(meaning="card")),
            "multiple": entry(stages=stages(mx=2), choices=["o1", "o2"], meaning=two),
            "two_choices": entry(choices=["o1", "o2"], meaning=two),
            "two_stages": entry(stages=stages() + [dict(stages()[0], stage=2)]),
            "choice_not_in_stage": entry(choices=["o9"]),
            "meaning_mismatch": entry(meaning=[{"stage": 1, "option": option("o2", ACT)}]),
            "duplicated_values": entry(stages=stages((FD, FD))),
            "no_choices": entry(choices=[]),
        }
        for name, e in cases.items():
            with self.subTest(name):
                self.assert_undetermined(e, expected_failure="D5")

    def test_other_answerer_reference_and_view(self):
        """別の回答者・観測の欠け・重複・古さ（前に受理）・別の番・段階・決定の不一致。"""
        cases = {
            "decision_player": logs(view(dec=decision(player=1))),
            "current_player": logs(view(current=1)),
            "missing": {ACTOR: [], 1: [], "host": []},
            "duplicated": logs(view(), view()),
            "other_episode": logs(view(), episode=EPISODE + 1),
            "other_turn": logs(view(turn=TURN + 1)),
            "phase_main": logs(view(phase="main")),
            "no_decision": logs(view(dec=None)),
            "decision_other_values": logs(view(dec=decision((FD, ACT)))),
            "decision_other_kind": logs(view(dec=decision(kind="select_bench_pokemon"))),
            "decision_two": logs(view(dec=decision(mx=2))),
            "not_ok": logs(dict(view(), ok=False)),
        }
        for name, actor_logs in cases.items():
            with self.subTest(name):
                self.assert_undetermined(entry(), actor_logs, expected_failure="D6")
        earlier = {"type": "attempt", "n": N - 1, "episode": EPISODE, "actor": ACTOR, "submit": {"outcome": D.ACCEPTED}}
        self.assert_undetermined(entry(), trace=[earlier, entry()], expected_failure="D6")
        self.assertEqual(J.decision_lost_target_failure(entry(), trace=[entry()], actor_logs=None, header=header()), "D6")

    def test_trainer_in_use_and_effect_registry(self):
        """trainer_in_use の欠け（特殊能力・スタジアム・ワザの途中・反応の決定）・別の主体（借りて使う）・表にない効果の型・対象を失ったら終える効果。"""
        self.assertIs(DEFAULT_EFFECTS.trainer_entry(SWITCH).effect.ends_on_lost_target, True)
        cases = {"missing": None, "other_player": trainer(player=1, user=ACTOR), "borrowed": trainer(user=1),
                 "switch_ends_on_lost_target": trainer(SWITCH), "other_effect_type": trainer(ENERGY_REMOVAL), "not_a_trainer": trainer(HITMONCHAN),
                 "unknown_card": trainer("ZZZ-999")}
        for name, used in cases.items():
            with self.subTest(name):
                self.assert_undetermined(entry(), logs(view(used=used)), expected_failure="D7")

    def test_options_not_the_own_field(self):
        """選べるものが本人の場（バトル場 → ベンチ）の並びと違う。"""
        own = (zone(ACT, HITMONCHAN), [zone(FD2, DIGLETT), zone(FD, real=PSYCHIC)])
        e = entry(stages=stages((ACT, FD)))
        self.assert_undetermined(e, logs(view(own=own)), expected_failure="D8")

    def test_reference_missing_or_twice(self):
        e = entry(stages=stages((ACT, 99)), meaning=[{"stage": 1, "option": option("o2", 99)}])
        own = (zone(ACT, HITMONCHAN), [zone(99, DIGLETT)])
        self.assert_undetermined(e, logs(view(own=own, opp_bench=[zone(99, DIGLETT)], dec=decision((ACT, 99)))), expected_failure="D9")

    def test_reason_only_on_unchosen_options(self):
        """未選択の選べるものにだけ continuation_not_evaluated がある（読まない）。候補の種類が use_power・play_trainer。"""
        e = entry(candidate=candidate(reasons=()), stages=stages(option_reasons={ACT: ["continuation_not_evaluated"]}))
        # 経路の理由がないので、既存の判定（規則 7 と同じ）の stop_not_explained_by_path のまま
        self.assertEqual(self.assert_rule7(e, expected_failure="D4"), (J.UNDETERMINED, [f"stop_not_explained_by_path:{CODE}"]))
        for kind in ("use_power", "play_trainer"):
            with self.subTest(kind):
                self.assert_rule7(entry(candidate=dict(candidate(), kind=kind)), expected_failure="D4")

    def test_after_rejection_shape(self):
        bad = rejected()
        bad["result"]["continuable"] = False
        cases = {"in_progress": rejected(status="in_progress"), "next_turn": rejected(next_=[{"kind": "turn_action", "player": ACTOR}]),
                 "viewer": rejected(viewer=1), "refetch": rejected(refetch=True), "halt": rejected(halt={"diagnostic_id": CODE}), "continuable": bad}
        for name, submit in cases.items():
            with self.subTest(name):
                self.assert_undetermined(entry(submit=submit), expected_failure="D3")

    def test_other_code_refused_failed_and_normal(self):
        """別のコード・refused・failed・分類の食い違い・通常の受理・拒否は既存の判定のまま（規則 8 は上書きしない）。"""
        for code in ("UNRESOLVED_KEEP_PROTECTED_TARGET", "UNSUPPORTED_SECRET_PLAN_IDENTITIES", "INVALID_CHOICE"):
            if D.default_catalog().get(code) is None:
                continue
            with self.subTest(code):
                self.assert_rule7(entry(submit=rejected(code)), expected_failure="D2")
        refused = {"ok": False, "outcome": "refused", "refusal": {"code": "STALE_HANDLE"}, "refetch_required": True, "result": None, "error": None}
        failed = dict(rejected(), outcome=D.FAILED)
        mismatch = rejected(category=D.RULING_UNRESOLVED)
        for name, submit, expected in (("refused", refused, "D1"), ("failed", failed, "D1"), ("mismatch", mismatch, "D2")):
            with self.subTest(name):
                self.assertEqual(self.assert_rule7(entry(submit=submit), expected_failure=expected)[0], J.SUSPECT)
        accepted = {"ok": True, "outcome": D.ACCEPTED, "refusal": None, "error": None, "refetch_required": False, "result": {"status": "in_progress"}}
        self.assertEqual(self.assert_rule7(entry(submit=accepted), expected_failure="D1"), (J.EXPECTED, []))

    def test_stop_policy_unchanged(self):
        """根拠が成り立たないときの分類・停止方針は規則 7 と同じ（evidence_missing_stop は続ける）。known_stop も続ける。"""
        for name, e, actor_logs in (("basic", entry(), logs(view(real=DIGLETT))), ("p3s", entry(), logs(view()))):
            with self.subTest(name):
                judged = B.judge_trace({"trace": [e], "actor_logs": actor_logs, "record": {"header": header()},
                                        "termination": {"class": "limit_operations", "detail": {}}})
                summary = summary_and_rest(B.judge_summary(judged))
                stops, notes = B.stop_reasons(summary, B._policy_dict(B.StopPolicy()))
                self.assertEqual(stops, [])
                if name == "basic":
                    self.assertEqual([u["category"] for u in judged["undetermined"]], [B.EVIDENCE_MISSING_STOP])
                    self.assertEqual(notes, ["undetermined:evidence_missing_stop:1"])
                else:
                    self.assertEqual(notes, ["known_stop:1"])

    def test_no_secret_in_reasons_rows_or_summary(self):
        positive = entry()
        negative = entry(n=N + 1, choices=["o1"], meaning=[{"stage": 1, "option": option("o1", ACT)}])
        result = {"trace": [positive, negative], "actor_logs": logs(view()), "record": {"header": header()},
                  "termination": {"class": "limit_operations", "detail": {}}}
        judged = B.judge_trace(result)
        self.assertEqual([r["verdict"] for r in judged["rows"]], [J.KNOWN_STOP, J.UNDETERMINED])
        self.assertEqual(judged["rows"][0]["reasons"], POSITIVE_REASONS)
        self.assertEqual(judged["rows"][0]["engine_code"], CODE)  # 行の生の診断コードは元のまま（鍵に書き換えない）
        self.assertEqual(judged["rules_version"], 8)
        text = json.dumps([judged["rows"], B.judge_summary(judged), judged["undetermined"]], ensure_ascii=False)
        for secret in (PSYCHIC, DEFENDER, HITMONCHAN, "real", "pokemon_id", "face_down\"", "#P3"):
            self.assertNotIn(secret, text)


class P1UnchangedTest(unittest.TestCase):
    def test_p1_and_p3_do_not_pick_each_other(self):
        """P1 の正の形は P1 の根拠のまま（P3 の関数では D3 で外れる）。P3 の形は P1 の関数で L3。P1 の理由の文は変わらない。"""
        e1 = p1_entry()
        hdr1 = p1_header()
        self.assertIsNone(J.lost_target_failure(e1, trace=[e1], actor_logs=p1_logs(p1_view()), header=hdr1))
        self.assertEqual(J.decision_lost_target_failure(e1, trace=[e1], actor_logs=p1_logs(p1_view()), header=hdr1), "D3")
        self.assertEqual(J.submit_evidence(e1, trace=[e1], actor_logs=p1_logs(p1_view()), header=hdr1), CODE)
        self.assertEqual(J.lost_target_failure(entry(), trace=[entry()], actor_logs=logs(view()), header=header()), "L3")
        verdict = J.judge_normal(e1["candidate"], e1["meaning"], e1["submit"], stages=e1["stages"], evidence=CODE)
        self.assertEqual(verdict[1][-1], "evidence:" + J.KNOWN_STOP_EVIDENCE[CODE]["condition"])
        self.assertEqual(J.LOST_TARGET_BASIS_FILES, ("cards.py", "data/kyuura_cards.json", "effects.py", "engine.py", "zones.py"))
        self.assertEqual(J.LOST_TARGET_BASIS_METHOD, "kyuura-lost-target-basis-sha256/1")


class BasisTest(unittest.TestCase):
    """D12: 判定の基礎が記録を作ったエンジンと同じこと（P3 用 basis。P1 の basis とは別）。"""

    def other_engine(self):
        hdr = header()
        hdr["engine"]["behavior_digest"] = "0" * 64
        return hdr

    def test_p3_basis_files_and_method(self):
        basis = J.lost_target_p3_basis()
        self.assertEqual(basis["method"], "kyuura-lost-target-p3-basis-sha256/1")
        self.assertEqual(basis["files"], ["cards.py", "data/kyuura_cards.json", "effects.py", "engine.py", "zones.py", "decisions.py", "observation.py"])
        self.assertRegex(basis["digest"], "^[0-9a-f]{64}$")
        self.assertNotEqual(basis["digest"], J.lost_target_basis()["digest"])

    def test_header_and_basis_cases(self):
        p3, p1 = J.lost_target_p3_basis(), J.lost_target_basis()
        other_data = header()
        other_data["dependencies"]["card_data"] = dict(other_data["dependencies"]["card_data"], commit="0" * 40)
        other_pool = header()
        other_pool["dependencies"]["card_pool"] = "custom"
        other_effects = header()
        other_effects["dependencies"]["effects"] = "kyuura-engine-0.0"
        no_effects = header()
        no_effects["dependencies"].pop("effects")
        cases = [("same_engine", header(), None, None, None), ("callable", header, None, None, None), ("no_header", None, None, None, "D12"),
                 ("other_engine_without_basis", self.other_engine(), None, None, "D12"),
                 ("other_engine_with_p3_basis", self.other_engine(), None, p3, None),
                 ("other_engine_with_p1_basis_only", self.other_engine(), p1, None, "D12"),
                 ("other_engine_with_p1_basis_as_p3", self.other_engine(), None, p1, "D12"),
                 ("other_engine_with_old_p3_digest", self.other_engine(), None, dict(p3, digest="1" * 64), "D12"),
                 ("other_engine_with_fewer_files", self.other_engine(), None, dict(p3, files=p3["files"][:5]), "D12"),
                 ("other_engine_with_other_method", self.other_engine(), None, dict(p3, method="x"), "D12"),
                 ("other_card_data_even_with_basis", other_data, None, p3, "D12"), ("other_pool", other_pool, None, p3, "D12"),
                 ("other_effects", other_effects, None, p3, "D12"), ("no_effects", no_effects, None, p3, "D12")]
        for name, hdr, b1, b3, expected in cases:
            with self.subTest(name):
                self.assertEqual(J.decision_lost_target_failure(entry(), trace=[entry()], actor_logs=logs(view()), header=hdr, basis_p3=b3), expected)
                evidence = J.submit_evidence(entry(), trace=[entry()], actor_logs=logs(view()), header=hdr, basis=b1, basis_p3=b3)
                self.assertEqual(evidence, None if expected else KEY)

    def test_batch_judge_trace_passes_basis_p3(self):
        result = {"trace": [entry()], "actor_logs": logs(view()), "record": {"header": self.other_engine()},
                  "termination": {"class": "limit_operations", "detail": {}}}
        self.assertEqual(B.judge_trace(result)["rows"][0]["verdict"], J.UNDETERMINED)
        self.assertEqual(B.judge_trace(result, basis=J.lost_target_basis())["rows"][0]["verdict"], J.UNDETERMINED)
        self.assertEqual(B.judge_trace(result, basis_p3=J.lost_target_p3_basis())["rows"][0]["verdict"], J.KNOWN_STOP)


# ---------------------------------------------------------------- 本物の runner に通す（構築盤面）


class P3Scripted(UniformPolicy):
    """ケースの選び手（方策ではない）: answer_decision の候補と、値が ``target`` の選べるもの。"""

    name, version = "scripted-lt-p3", 0

    def __init__(self, target):
        super().__init__("scripted-lt-p3")
        self.target = target

    def choose(self, purpose, items, context):
        if purpose == "candidate":
            return next(i for i, c in enumerate(items) if c.get("kind") == "answer_decision"), "scripted"
        if purpose == "option":
            by_id = {o["id"]: o for o in context["stage"].get("options", [])}
            return next(i for i, oid in enumerate(items) if by_id.get(oid, {}).get("value") == self.target), "scripted"
        return 0, "scripted"


def run_p3(real, *, negative=None, with_header=True, counts=None):
    from tests.test_lost_target_p3_decision_v0_181 import board, defender_decision, own_face_down

    state, fd = own_face_down(board(hand=(real, DEFENDER)), real)
    state = defender_decision(state)
    text, error = F.snapshot_text(state, "LT-P3")
    assert text is not None, error

    def wrap(endpoint):
        class Counting:
            def handle(self, message):
                counts[message.get("type")] = counts.get(message.get("type"), 0) + 1
                return endpoint.handle(message)
        return Counting()

    config = V.Config(profile="boundary", limits=V.Limits(operations=1, seconds=60), run_id="test-lt-p3")
    runner = RecordedFixtureRunner(config, text, with_header=with_header, policy_factory=lambda seed, dist: P3Scripted(fd.pokemon_id), negative=negative)
    if counts is not None:
        original = runner._start

        def start():
            original()
            runner.endpoints = {k: wrap(v) for k, v in runner.endpoints.items()}
        runner._start = start
    return runner.run()


def submitted(result):
    return [e for e in result["trace"] if e.get("type") == "attempt" and e.get("submit") is not None]


class RunnerConnectionTest(unittest.TestCase):
    """構築盤面 → 本物の runner → バッチの入口と単局の入口。new_game からの対戦の実績には数えない。"""

    def test_non_basic_is_known_stop_in_both_entries(self):
        batch_counts, single_counts = {}, {}
        result = run_p3(PSYCHIC, counts=batch_counts)
        (e,) = submitted(result)
        self.assertEqual((e["candidate"]["kind"], e["submit"]["outcome"], e["submit"]["verifier"]["engine_code"]), ("answer_decision", D.REJECTED, CODE))
        self.assertNotIn("judge", e)
        hdr = B.record_header(result["record"])
        self.assertEqual(hdr["dependencies"].get("effects"), DEFAULT_EFFECTS.id)
        self.assertIsNone(J.decision_lost_target_failure(e, trace=result["trace"], actor_logs=result["actor_logs"], header=hdr))
        judged = B.judge_trace(result)
        self.assertEqual([(r["attempt"], r["verdict"], r["reasons"]) for r in judged["rows"]], [(e["n"], J.KNOWN_STOP, POSITIVE_REASONS)])
        single = run_p3(PSYCHIC, negative=NoNegative(), counts=single_counts)
        (e_single,) = submitted(single)
        self.assertEqual(e_single["judge"], {"verdict": judged["rows"][0]["verdict"], "reasons": judged["rows"][0]["reasons"]})
        self.assertEqual(single_counts, batch_counts)  # 判定のための追加の要求はない
        from tools.verification_ai import records as R
        self.assertEqual(R.action_sequence(single["trace"]), R.action_sequence(result["trace"]))

    def test_saved_files_give_the_same_rows(self):
        result = run_p3(PSYCHIC)
        saved = {str(actor): [json.loads(line) for line in B.jsonl_bytes(rows).decode("utf-8").splitlines() if line.strip()]
                 for actor, rows in result["actor_logs"].items()}
        reloaded = dict(result, actor_logs=saved, trace=[json.loads(json.dumps(x)) for x in result["trace"]])
        self.assertEqual(B.judge_trace(reloaded)["rows"], B.judge_trace(result)["rows"])

    def test_basic_accepted_and_missing_header_undetermined_in_both_entries(self):
        basic = run_p3(DIGLETT)
        (e,) = submitted(basic)
        self.assertEqual(e["submit"]["outcome"], D.ACCEPTED)
        self.assertEqual(B.judge_trace(basic)["rows"][0]["verdict"], J.EXPECTED)
        for negative in (None, NoNegative()):
            with self.subTest(single=negative is not None):
                result = run_p3(PSYCHIC, with_header=False, negative=negative)
                (e,) = submitted(result)
                judged = B.judge_trace(result)
                self.assertEqual((judged["rows"][0]["verdict"], judged["rows"][0]["reasons"]), UNDET)
                self.assertEqual(judged["undetermined"][0]["category"], B.EVIDENCE_MISSING_STOP)
                self.assertEqual(J.decision_lost_target_failure(e, trace=result["trace"], actor_logs=result["actor_logs"], header=None), "D12")
                if negative is not None:
                    self.assertEqual(e["judge"], {"verdict": J.UNDETERMINED, "reasons": UNDET[1]})


class BoundaryTest(unittest.TestCase):
    def test_policy_and_input_generation_do_not_use_rule8(self):
        from pathlib import Path

        base = Path(J.__file__).resolve().parent
        for name in ("policies.py", "actions.py", "negative.py", "metrics.py", "records.py", "reach.py", "observe.py"):
            text = (base / name).read_text(encoding="utf-8")
            with self.subTest(name):
                for word in ("submit_evidence", "lost_target", "decision_lost_target", "basis_p3", "own_view_for"):
                    self.assertNotIn(word, text)
        runner_text = (base / "runner.py").read_text(encoding="utf-8")
        self.assertEqual(runner_text.count("submit_evidence("), 1)
        self.assertNotIn("basis_p3", runner_text)


if __name__ == "__main__":
    unittest.main()
