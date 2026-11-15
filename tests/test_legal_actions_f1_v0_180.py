"""v0.180（F-1。docs/legal-actions-f1-face-down-attack-guarantee.md）: 本人のうらのバトル場のポケモンのワザの候補の保証の文。

0.179.0 まで、うらの分岐（``_face_down_attack_candidate``）は、おもてのワザと同じ ``GUARANTEE_ATTACK``（「check_use_attack を候補の作成と入力の検査に使う」）を付けていたが、
うらの分岐は check_use_attack を呼ばない（``verify=_not_checked``）。0.180.0 では、うらの分岐だけに ``GUARANTEE_FACE_DOWN_ATTACK`` を付ける。直したのは保証の文と実装の対応で、
候補・入力・検査・送信・エンジンの裁定は変えていない。

確かめること（構築盤面。P6 のテストの ``face_down_active`` の双子を再利用する。new_game からの到達ではない）:

- うらの候補に新しい保証の文が付く。本当のカード（たね・1 進化・ワザのないエネルギー）によらず同じ値
- おもてのワザの候補の保証の文は 0.179.0 の値のまま（sha256 で固定）
- 保証の文以外の、候補・inputs・check の値は 0.179.0 と同じ（期待値は定数で書く。修正の前後の応答の項目ごとの比べは証跡の contract_diff.json）
- 受理・拒否の動作（U7 と直接のコマンドで結果・状態が同じ。拒否は状態を変えず、相手・観戦者へ知らせない）
- 元の文（GUARANTEE_ATTACK）に戻すと、文の確かめが失敗する
"""

from __future__ import annotations

import hashlib
import json
import unittest
from unittest import mock

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from kyuura_engine.commands import UseAttack
from tests import helpers as H
from tests import test_secret_plan_v0_67 as S
from tests.test_legal_actions_p6_face_down_retreat_v0_174 import face_down_active
from tests.test_legal_actions_u7_1 import snap

REQ = {"contract": "kyuura-client-api", "format": 1}
REALS = (H.RATTATA, H.ONIX, H.KADABRA, H.FIRE)  # たね（ワザ 1）・たね（ワザ 2）・1 進化（ワザ 2）・エネルギー（印刷のワザなし）
# 0.179.0 の GUARANTEE_ATTACK（おもてのワザ。変えない）と、0.180.0 の GUARANTEE_FACE_DOWN_ATTACK の値（JSON・キーの順・区切りの空白なし）の sha256
ATTACK_0179_SHA256 = "f1e79cef13b69200910504f90614393b2b2344d6dad71b47d25eff260ec5bc5b"
FACE_DOWN_ATTACK_SHA256 = "aa316b12cb9a79033e6d80685a4fbffacfa2e13b1af310bda57d76049b6f1d0c"


def sha256(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def wording_problems(guarantees):
    """うらのワザの候補の保証の文が、実装（check_use_attack を呼ばない・構造の検査だけ・受理を保証しない・結果を予告しない）と合わない点の一覧。"""
    problems = []
    pre, acc, after, scope = (guarantees.get(k, "") for k in ("preconditions", "acceptance", "after_acceptance", "supported_scope"))
    if ("を候補の作成と入力の検査に使う" in pre or "resolution.flow.check_use_attack" not in pre
            or "含む）と宣言の前の先読みは、候補の作成でも入力の検査でも呼ばない" not in pre):
        problems.append("preconditions: check_use_attack を使うと読める")
    if "入力の検査（check）は形（ワザの番号が 1 つで、ほかを選ばないこと）だけを確かめる" not in pre:
        problems.append("preconditions: 構造の検査だけであることがない")
    if not acc.startswith("保証しない。") or "check が valid でも、エンジンの確かめを通したことを意味しない" not in acc:
        problems.append("acceptance: check と送信後の判定を分けていない")
    if not after.startswith("評価していない"):
        problems.append("after_acceptance: 受理のあとを評価したと読める")
    if "unverified は受理・必要なエネルギー・ワザの実行の完了の保証ではなく" not in scope:
        problems.append("supported_scope: 受理・エネルギー・完了を保証しないことがない")
    if any(word in text for text in (pre, acc, after, scope) for word in ("トラッシュ", "たねポケモン")):
        problems.append("おもてにしたあとの結果を予告している")
    return problems


def attack_candidate(state, actor=0):
    host = L.ActionHost(A.HostedGame(state.clone()))
    session = host.session(actor)
    r = session.candidates()
    return host, session, r, next(c for c in r["candidates"] if c["kind"] == L.KIND_USE_ATTACK)


class ConstantTest(unittest.TestCase):
    def test_face_up_guarantee_is_the_0179_value(self):
        self.assertEqual(sha256(L.GUARANTEE_ATTACK), ATTACK_0179_SHA256)
        self.assertIs(L._UNUSABLE_GUARANTEES[L.KIND_USE_ATTACK], L.GUARANTEE_ATTACK)  # 使えないワザの候補（おもて）の保証も変えない

    def test_face_down_guarantee_value_and_wording(self):
        self.assertEqual(sha256(L.GUARANTEE_FACE_DOWN_ATTACK), FACE_DOWN_ATTACK_SHA256)
        self.assertEqual(set(L.GUARANTEE_FACE_DOWN_ATTACK), set(L.GUARANTEE_ATTACK))  # 項目の名前は増やさない
        self.assertEqual(wording_problems(L.GUARANTEE_FACE_DOWN_ATTACK), [])

    def test_the_old_wording_fails(self):
        """0.179.0 の文（GUARANTEE_ATTACK）は、うらの分岐の確かめに合わない。"""
        self.assertIn("preconditions: check_use_attack を使うと読める", wording_problems(L.GUARANTEE_ATTACK))
        with mock.patch.object(L, "GUARANTEE_FACE_DOWN_ATTACK", L.GUARANTEE_ATTACK):  # 元の文に戻した場合
            _h, _s, _r, c = attack_candidate(face_down_active(H.ONIX))
            self.assertNotEqual(sha256(c["guarantees"]), FACE_DOWN_ATTACK_SHA256)
            self.assertTrue(wording_problems(c["guarantees"]))


class CandidateTest(unittest.TestCase):
    def test_face_down_candidates_carry_the_new_guarantee(self):
        seen = []
        for real in REALS:
            with self.subTest(real=real):
                state = face_down_active(real)
                _h, _s, _r, c = attack_candidate(state)
                self.assertEqual(c["guarantees"], L.GUARANTEE_FACE_DOWN_ATTACK)
                self.assertEqual(sha256(c["guarantees"]), FACE_DOWN_ATTACK_SHA256)
                client = ClientHub(A.HostedGame(state.clone())).player(0).handle({**REQ, "type": "candidates"})["response"]
                self.assertEqual(next(x for x in client["candidates"] if x["kind"] == L.KIND_USE_ATTACK)["guarantees"], L.GUARANTEE_FACE_DOWN_ATTACK)
                seen.append(sha256(c["guarantees"]))
        self.assertEqual(len(set(seen)), 1)  # 本当のカード（ワザの有無を含む）で保証の文を分けない

    def test_face_up_candidate_keeps_the_attack_guarantee(self):
        _h, _s, _r, c = attack_candidate(S.board())  # おもてのエビワラー（闘エネルギー 2 枚）
        self.assertEqual(c["guarantees"], L.GUARANTEE_ATTACK)
        self.assertEqual(sha256(c["guarantees"]), ATTACK_0179_SHA256)
        self.assertEqual(c["processability"], L.MAY_STOP_LATER)

    def test_values_other_than_the_guarantee_are_unchanged(self):
        """0.179.0 と同じ値（候補の区分・理由・入力の公開・段・選べるもの・check）。"""
        _h, session, r, c = attack_candidate(face_down_active(H.ONIX))
        self.assertEqual((c["processability"], c["reasons"], c["input_disclosure"]), (L.UNVERIFIED, [L.REASON_FACE_DOWN], L.DISCLOSURE_CONFIRMED))
        stages = session.inputs(r["game"], r["revision"], c["id"])["stages"]
        first, second = stages
        self.assertEqual([(o["id"], o["name_ja"], o["cost"], o["face_down"], o["processability"], o["reasons"]) for o in first["options"]],
                         [("o1", "いわおとし", ["fighting"], True, L.UNVERIFIED, [L.REASON_FACE_DOWN]),
                          ("o2", "かたくなる", ["fighting", "fighting"], True, L.UNVERIFIED, [L.REASON_FACE_DOWN])])
        self.assertEqual((second["count"], second["options"], second["options_by_choice"]), ({"min": 0, "max": 0}, [], {"o1": [], "o2": []}))
        for choices, code in ((["o1"], None), (["o2"], None), ([], L.CANDIDATE_INPUT_INVALID), (["o1", "o2"], L.CANDIDATE_INPUT_INVALID),
                              (["o9"], L.CANDIDATE_INPUT_INVALID), ([1], L.CANDIDATE_INPUT_INVALID)):
            with self.subTest(choices=choices):
                answer = session.check(r["game"], r["revision"], c["id"], choices)
                self.assertEqual((answer["valid"], None if answer["refusal"] is None else answer["refusal"]["code"]), (code is None, code))
        _h, session, r, c = attack_candidate(face_down_active(H.FIRE))  # 印刷のワザがない本当のカード
        self.assertEqual((c["processability"], c["reasons"]), (L.NOT_IMPLEMENTED, [L.REASON_FACE_DOWN, L.REASON_NO_PRINTED_ATTACK]))
        self.assertEqual(session.inputs(r["game"], r["revision"], c["id"])["stages"], [])


class BehaviorTest(unittest.TestCase):
    """受理・拒否の動作は 0.179.0 と同じ（check が valid でも、送信の判定はエンジン）。"""

    def submit(self, real, name):
        state = face_down_active(real)
        host, session, r, c = attack_candidate(state)
        option = next(o for o in session.inputs(r["game"], r["revision"], c["id"])["stages"][0]["options"] if o["name_ja"] == name)
        self.assertTrue(session.check(r["game"], r["revision"], c["id"], [option["id"]])["valid"])
        result = session.submit(r["game"], r["revision"], c["id"], [option["id"]])
        game = A.HostedGame(state.clone())
        direct = game.submit(UseAttack(0, option["attack_index"]), submitter=0)
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual(snap(host._game.state), snap(game.state))
        return state, host, result

    def test_accepted_and_rejected_as_before(self):
        self.submit(H.RATTATA, "かみつく")  # たね・必要なエネルギー（無色 1）が足りる: 受理
        self.submit(H.ONIX, "いわおとし")  # たね・闘 1 が足りる: 受理
        state, host, result = self.submit(H.ONIX, "かたくなる")  # たね・闘 2 に足りない: エンジンが拒否
        self.assertEqual((result.outcome, result.view.diagnostic_id, result.view.category), (D.REJECTED, "INSUFFICIENT_ENERGY", D.INVALID_INPUT))
        self.assertEqual(snap(host._game.state), snap(state))  # 拒否は状態・乱数・ログを変えない
        self.submit(H.KADABRA, "ちょうねんりき")  # 1 進化: 受理（そのあとの結果は保証の文では予告しない）

    def test_rejection_is_not_announced(self):
        state = face_down_active(H.ONIX)
        hub = ClientHub(A.HostedGame(state.clone()))
        me = hub.player(0)
        r = me.handle({**REQ, "type": "candidates"})["response"]
        c = next(x for x in r["candidates"] if x["kind"] == L.KIND_USE_ATTACK)
        sent = me.handle({**REQ, "type": "submit", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": ["o2"]})
        self.assertEqual(sent["outcome"], D.REJECTED)
        self.assertEqual([hub.take_updates(a) for a in (1, "spectator")], [[], []])


if __name__ == "__main__":
    unittest.main()
