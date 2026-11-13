"""検証用 AI の 0.178.0（UP-5t-C1）への追従のテスト（docs/verification-ai-v0178-follow.md）。

UP-5t-C1: 特殊能力の候補の確かめが相手のうらのカードの本当のカードを使ったら、その結果を使わず unverified（face_down_reveal_not_evaluated）にする。
確認された秘密依存の判定を候補の側で採用しない補強で、修正の前の構築盤面でも外へ出る差は再現していない（docs/legal-actions-up5t-audit.md 11 章）。

盤面はエンジンのテスト ``tests/test_legal_actions_up5t_c1_v0_178.py`` の構築盤面（``opponent_face_down``・``opponent_face_up``。new_game からの到達ではない）。
AI の範囲（ランナーの ``_scope``・``actions.option_allowed``）と判定（``judge_normal``）は API の値（処理可能性・理由・入力の公開・表示だけの種類）だけで決まり、
カード名・カード ID を見ない。AI のコード（方策・入力生成・範囲・判定）は変えていない。
"""

from __future__ import annotations

import copy
import unittest

from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from tests.test_legal_actions_up5t_c1_v0_178 import POWERS, REALS, REQ, opponent_face_down, opponent_face_up
from tools.verification_ai import actions as B
from tools.verification_ai import judge as J
from tools.verification_ai import records as R
from tools.verification_ai import runner as V
from tools.verification_ai.policies import UniformPolicy, action_key


def query(state):
    hub = ClientHub.from_state(state)
    me = hub.player(1)
    return hub, me, me.handle({**REQ, "type": "candidates"})["response"]


def power(cands):
    return next(c for c in cands["candidates"] if c["kind"] == L.KIND_USE_POWER)


def scope(cands, profile="deep"):
    runner = V.Runner(V.Config(profile=profile))
    chosen, info, reasons = runner._scope(cands, {})
    return [c["id"] for c in chosen], info, reasons, runner.counters["deep_fallback_unverified"]


def attempt(candidate, submit):
    return {"type": "attempt", "n": 1, "actor": 1, "operation_id": "v0-000001", "build": "ok", "candidate": candidate, "stages": [], "meaning": [],
            "check": {"response": {"valid": True}}, "submit": submit}


class GuardedCandidateTest(unittest.TestCase):
    def test_face_down_twins_are_unverified_and_face_up_control_is_not(self):
        for name in POWERS:
            per_real = set()
            for real in REALS.values():
                _hub, _me, cands = query(opponent_face_down(name, real))
                c = power(cands)
                self.assertEqual((c["processability"], c["reasons"], c["input_disclosure"], c["input_stages"]),
                                 (L.UNVERIFIED, [J.FACE_DOWN_REASON], L.DISCLOSURE_NONE, []))
                self.assertFalse(J.is_face_down_power(c))  # 使うポケモンはおもて（本人のうらのカードの特殊能力の規則 5 の対象ではない）
                per_real.add(str({k: v for k, v in c.items() if k != "id"}))
            self.assertEqual(len(per_real), 1)  # 本当のカードによらない
            _hub, _me, cands = query(opponent_face_up(name))
            c = power(cands)
            self.assertEqual((c["processability"], c["reasons"]), (L.MAY_STOP_LATER, ["continuation_not_evaluated"]))

    def test_publicly_unusable_is_not_offered(self):
        for name in POWERS:
            for real in REALS.values():
                _hub, _me, cands = query(opponent_face_down(name, real, confusion=True))
                self.assertEqual([c for c in cands["candidates"] if c["kind"] == L.KIND_USE_POWER], [])  # 候補に出ない（AI は選べない）


class ScopeTest(unittest.TestCase):
    def test_deep_excludes_with_other_candidates_and_boundary_includes(self):
        for name in POWERS:
            for real in REALS.values():
                _hub, _me, cands = query(opponent_face_down(name, real))
                original = copy.deepcopy(cands)
                c = power(cands)
                display = set(cands["coverage"]["display_only_kinds"])
                with self.subTest(power=name, real=real):
                    chosen, info, reasons, fallbacks = scope(cands)
                    self.assertNotIn(c["id"], chosen)
                    self.assertEqual(reasons[c["id"]], "processability:unverified")
                    self.assertEqual((info["fallback_unverified"], fallbacks), (False, 0))  # ほかの候補（end_turn など）があるので代替は起きない
                    self.assertTrue(chosen)
                    chosen_b, info_b, _r, _f = scope(cands, "boundary")
                    self.assertIn(c["id"], chosen_b)
                    self.assertEqual(info_b["profile"], "boundary")
                    for ids, allowed in ((chosen, B.DEEP_PROCESSABILITY), (chosen_b, B.FALLBACK_PROCESSABILITY)):
                        for x in cands["candidates"]:
                            if x["id"] in ids:  # 表示だけ・入力を返さない・実行できない区分は選ばない
                                self.assertNotIn(x["kind"], display)
                                self.assertNotEqual(x["input_disclosure"], L.DISCLOSURE_UNCONFIRMED)
                                self.assertIn(x["processability"], allowed)
                    self.assertEqual(cands, original)  # 元の API の応答を変えない

    def test_deep_fallback_only_when_nothing_else_is_in_scope(self):
        """小さな JSON 例（実際の応答から、この候補だけを残した写し）: deep の範囲に何もないときだけ、既存の代替で unverified を選び、数える。"""
        _hub, _me, cands = query(opponent_face_down("くさいかふん", REALS["basic"]))
        only = copy.deepcopy(cands)
        only["candidates"] = [power(only)]
        chosen, info, _reasons, fallbacks = scope(only)
        self.assertEqual((chosen, info["fallback_unverified"], fallbacks), ([power(only)["id"]], True, 1))
        withheld = copy.deepcopy(only)
        withheld["candidates"][0]["input_disclosure"] = L.DISCLOSURE_UNCONFIRMED
        self.assertEqual(scope(withheld)[0], [])  # 代替でも入力を返さない候補は選ばない
        self.assertEqual(scope(withheld, "boundary")[0], [])

    def test_scope_does_not_read_card_names_or_ids(self):
        _hub, _me, cands = query(opponent_face_down("えんかくさいみん", REALS["stage1"]))
        renamed = copy.deepcopy(cands)
        c = power(renamed)
        c["power"]["name_ja"] = "x"
        c["pokemon"] = {**c["pokemon"], "card_id": "X-000"}
        for profile in ("deep", "boundary"):
            self.assertEqual(scope(renamed, profile)[:2], scope(cands, profile)[:2])


class CheckSubmitJudgeTest(unittest.TestCase):
    def test_no_input_check_then_submit_and_judge(self):
        for name in POWERS:
            for real in REALS.values():
                hub, me, cands = query(opponent_face_down(name, real))
                c = power(cands)
                handle = {"game": cands["game"], "revision": cands["revision"], "candidate": c["id"]}
                stages = me.handle({**REQ, "type": "inputs", **handle})["response"]["stages"]
                choices, picks, meaning = B.build_choices(stages, UniformPolicy("t"), {"candidate": c}, B.FALLBACK_PROCESSABILITY)
                self.assertEqual((stages, choices, picks, meaning), ([], [], [], []))
                check = me.handle({**REQ, "type": "check", **handle, "choices": choices})["response"]
                self.assertIs(check["valid"], True)  # 構造の検査だけ（受理・完走の保証ではない）
                sent = me.handle({**REQ, "type": "submit", **handle, "choices": choices})
                with self.subTest(power=name, real=real):
                    self.assertEqual(sent["outcome"], D.ACCEPTED)  # 受け付けるかは本当のカードによらない（エンジンのテストと同じ）
                    self.assertEqual(J.judge_normal(c, meaning, {"ok": sent["ok"], "outcome": sent["outcome"]}, stages=stages), (J.EXPECTED, []))

    def test_unverified_is_not_all_normal_nor_all_suspect(self):
        """API の値の写し（偽物の送信の結果）: unverified だからすべて正常にも、check のあとの拒否だからすべて suspect にもしない。"""
        _hub, _me, cands = query(opponent_face_down("くさいかふん", REALS["ditto"]))
        c = power(cands)
        self.assertNotIn(c["kind"], J.PRECHECK_KINDS)
        self.assertFalse(J.is_p6(c, []))

        def rejected(code, category):
            return {"ok": True, "outcome": D.REJECTED, "verifier": {"diagnostic_id": code, "category": category, "engine_code": code}}

        stop = "UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT"
        cases = {
            "refused": ({"ok": True, "outcome": "refused", "refusal": {"code": L.CANDIDATES_STALE}}, J.SUSPECT),
            "failed": ({"ok": False, "outcome": D.FAILED}, J.SUSPECT),
            "unknown": ({"ok": True, "outcome": "something_new"}, J.UNDETERMINED),
            "unmapped": (rejected("X", D.UNMAPPED), J.SUSPECT),
            "mismatch": (rejected("POWER_ALREADY_USED", D.UNSUPPORTED), J.SUSPECT),
            "engine_rejected": (rejected("POWER_ALREADY_USED", D.INVALID_INPUT), J.NORMAL_REJECTION),
            "stop_without_evidence": (rejected(stop, D.default_catalog().get(stop).category), J.UNDETERMINED),
            "stop_not_in_catalog": (rejected("UNRESOLVED_NOT_IN_TABLE", D.RULING_UNRESOLVED), J.UNDETERMINED),
        }
        for label, (submit, verdict) in cases.items():
            with self.subTest(label):
                self.assertEqual(J.judge_normal(c, [], submit, stages=[])[0], verdict)
        # 既知停止は代表の条件の根拠（場面の宣言）があるときだけ。理由 face_down_reveal_not_evaluated は経路の説明に使われる
        verdict, notes = J.judge_normal(c, [], cases["stop_without_evidence"][0], stages=[], evidence=stop)
        self.assertEqual(verdict, J.KNOWN_STOP)
        self.assertIn(J.FACE_DOWN_REASON, notes)
        self.assertEqual(J.judge_halt_after_accept({"category": D.UNMAPPED, "diagnostic_id": "X"})[0], J.SUSPECT)  # 受理のあとの停止は別に読む
        self.assertEqual(J.judge_halt_after_accept({"category": D.RULING_UNRESOLVED, "diagnostic_id": stop})[0], J.UNDETERMINED)
        self.assertEqual(J.JUDGE_RULES_VERSION, 7)  # この追従では判定の規則を変えていない（規則 6 はあとの C1 の確認、規則 7 はあとの LOST_TARGET の P1）


class FingerprintTest(unittest.TestCase):
    def test_guarded_candidate_changes_contract_rows_not_action_rows(self):
        """ガードが働く候補とおもての対照の差（処理可能性・理由）は契約の列にだけ出て、行動の列・反復の抑制の鍵には出ない。"""
        _hub, _me, down = query(opponent_face_down("くさいかふん", REALS["basic"]))
        _hub, _me, up = query(opponent_face_up("くさいかふん"))
        accepted = {"ok": True, "outcome": D.ACCEPTED, "refusal": None, "verifier": None}
        a, b = attempt(power(down), accepted), attempt(power(up), accepted)
        # 2 つの盤面はカードの番号（場のポケモン・特殊能力のカードの番号）が違うので、行動の対象を同じにそろえ、評価の値の差だけを残す
        b["candidate"] = {**b["candidate"], "id": a["candidate"]["id"], "pokemon": a["candidate"]["pokemon"], "power": a["candidate"]["power"]}
        self.assertEqual({k for k in a["candidate"] if a["candidate"][k] != b["candidate"].get(k)}, {"processability", "reasons"})
        self.assertEqual(R.action_sequence([a]), R.action_sequence([b]))
        self.assertNotEqual(R.contract_sequence([a]), R.contract_sequence([b]))
        self.assertEqual(action_key(1, a["candidate"], [], []), action_key(1, b["candidate"], [], []))

    def test_guarantee_text_is_the_0177_text_plus_one_sentence(self):
        """v2_repeat の契約の値の固定値 2 つの更新の根拠: 0.178.0 の use_power の preconditions は 0.177.0 の文に 1 文を足したもの。行動の列・反復の鍵は保証の文によらない。"""
        text = L.GUARANTEE_POWER["preconditions"]
        old, sep, added = text.partition("。v0.178:")
        self.assertTrue(sep and old and added)
        self.assertIn("unverified", added)
        _hub, _me, cands = query(opponent_face_up("えんかくさいみん"))
        c = power(cands)
        self.assertEqual(c["guarantees"]["preconditions"], text)
        older = {**c, "guarantees": {**c["guarantees"], "preconditions": old}}
        accepted = {"ok": True, "outcome": D.ACCEPTED, "refusal": None, "verifier": None}
        self.assertEqual(R.action_sequence([attempt(c, accepted)]), R.action_sequence([attempt(older, accepted)]))
        self.assertNotEqual(R.contract_sequence([attempt(c, accepted)]), R.contract_sequence([attempt(older, accepted)]))
        self.assertEqual(action_key(1, c, [], []), action_key(1, older, [], []))


if __name__ == "__main__":
    unittest.main()
