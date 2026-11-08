"""U7-5g（docs/legal-actions-u7-5fg.md 2 章）: coverage の残り（residual）と完了の判定（D-U7-COMPLETENESS）の回帰テスト。

確かめの種類を分ける:

- 合法な操作の列（build_test_state の盤面から apply_command。マチスの秘策・フラッシュ・決定への答え）: 段階・主体ごとの coverage、隠れたカードだけを変えた双子
- new_game からの合法な操作の列（ActionHost.start。準備を U7 で終える）: 準備・ホスト・先攻・MAIN の各段階の coverage
- 補助関数の確かめ: 固定の分類（classes）が状態によらないこと、unverified_paths の集め方

停止コードの文字列はテストの中に書かない。
"""

from __future__ import annotations

import unittest

from kyuura_engine import legal_actions as L
from kyuura_engine.observation import observe, visible_log
from tests import helpers as H
from tests import test_secret_plan_v0_67 as S
from tests.test_legal_actions_u7_1 import DECKS, without_handles
from tests.test_legal_actions_u7_3 import host_of, setup_with_u7
from tests.test_legal_actions_u7_5e import opponent_face_down
from tests.test_legal_actions_u7_5f import flashed

FIXED = [dict(c) for c in L.RESIDUAL_CLASSES]


def cov(state, actor):
    return host_of(state).session(actor).candidates()["coverage"]


def present_ids(coverage):
    return [item["id"] for item in coverage["residual"]["present"]]


def own_face_down(real, *, hand=(), active=False):
    """プレイヤー 0 がマチスの秘策で ``real`` をうらにしてベンチに出した盤面（0 の番の MAIN）。``active`` ならにげるでバトル場に出す。"""
    state = S.place(S.board(hand=(real, *hand)), real)
    return S.to_active(state, S.face_down(state)[0]) if active else state


class FixedClassesTest(unittest.TestCase):
    def test_classes_are_the_same_in_every_response(self):
        host, _ = L.ActionHost.start(*DECKS, 3)
        seen = [host.session(a).candidates()["coverage"]["residual"]["classes"] for a in (0, 1)]
        seen.append(host.host_session().candidates()["coverage"]["residual"]["classes"])
        for state in (own_face_down(H.DIGLETT), own_face_down(H.KADABRA, active=True), flashed(), opponent_face_down(H.DIGLETT)):
            seen += [cov(state, a)["residual"]["classes"] for a in (0, 1)]
        for classes in seen:
            self.assertEqual(classes, FIXED)  # 状態・主体・カードによらない（該当するカードがあるときだけ出す方式にしない）
        self.assertEqual([c["id"] for c in FIXED], ["R-2", "R-3", "R-4", "R-5"])  # R-1（カツラの 2 枚目）は v0.172 で示す（tests/test_legal_actions_u7_5g_energy2.py）
        self.assertEqual({c["status"] for c in FIXED}, {L.RESIDUAL_NOT_OFFERED, L.RESIDUAL_OUT_OF_SCOPE, L.RESIDUAL_INPUT_WITHHELD})

    def test_new_game_phases(self):
        host, _ = L.ActionHost.start(*DECKS, 3)
        for actor in (0, 1):
            c = host.session(actor).candidates()["coverage"]
            self.assertEqual((c["scope_kinds"], c["completeness"], c["partial_residual"], c["residual"]["present"]), ([L.KIND_PLACE_STARTING], L.COMPLETE, [], []))
        setup_with_u7(host)
        main = host.session(0).candidates()["coverage"]
        self.assertEqual((main["completeness"], main["not_covered_kinds"]), (L.PARTIAL, []))  # 種類はそろったが、示さない経路が残る
        self.assertEqual(main["partial_residual"], ["R-2"])  # v0.172: R-1 は示し、R-3 は入力を返さない残り（種類の網羅は変えない）。R-2 だけが示さない経路
        other = host.session(1).candidates()
        self.assertEqual((other["coverage"]["completeness"], other["empty_reason"], other["coverage"]["residual"]["present"]), (L.COMPLETE, L.EMPTY_NOT_ACTOR, []))
        hosted = host.host_session().candidates()["coverage"]
        self.assertEqual((hosted["completeness"], hosted["partial_residual"], hosted["residual"]["present"]), (L.COMPLETE, [], []))


class SituationTest(unittest.TestCase):
    def test_turn_player_main_stays_partial_while_declaration_paths_remain(self):
        c = cov(own_face_down(H.DIGLETT, active=True), 0)
        self.assertEqual(c["completeness"], L.PARTIAL)
        self.assertIn("R-2", c["partial_residual"])  # R-2 が残るあいだ partial（D-U75-R2）
        self.assertEqual([i for i in c["residual"]["present"] if i["id"] in ("R-2", "R-3")], [{"id": "R-2", "scope": L.RESIDUAL_PUBLIC}])  # ディグダ: 特殊能力がない（R-3 はない）
        with_power = cov(own_face_down(H.ROCKET_CHARMANDER, active=True), 0)  # 2 段の特殊能力: 本人の候補から決まる R-3（本人の応答だけ）
        self.assertEqual([i["scope"] for i in with_power["residual"]["present"] if i["id"] == "R-3"], [L.RESIDUAL_ACTOR])
        self.assertEqual(cov(own_face_down(H.ROCKET_CHARMANDER, active=True), 1)["residual"]["present"], [])
        self.assertIn("completeness_basis", c)

    def test_non_turn_player_with_an_unresolved_request_is_not_called_complete(self):
        state = flashed()  # 0 の番。0 の山札のおもては 4 枚（1 から見て相手の山札）
        r = host_of(state).session(1).candidates()
        c = r["coverage"]
        self.assertEqual((r["candidates"], r["empty_reason"]), ([], L.EMPTY_NOT_COVERED))  # 理由なく「操作なし」と断定しない
        self.assertEqual((c["not_covered_kinds"], c["completeness"]), ([L.KIND_CHECK_FACE_UP_DECK], L.PARTIAL))
        self.assertEqual(c["residual"]["present"], [{"id": "R-4", "scope": L.RESIDUAL_PUBLIC}])
        plain = cov(own_face_down(H.DIGLETT), 1)  # おもての山札がない: 番でないプレイヤーの操作はない（complete）
        self.assertEqual((plain["completeness"], plain["residual"]["present"], plain["not_covered_kinds"]), (L.COMPLETE, [], []))

    def test_decision_answerer(self):
        state = S.board(hand=(H.DIGLETT,))
        state = S.apply_command(state, S.PlayTrainer(0, S.uid_of(state, S.LT_SURGES_SECRET_PLAN)))
        r = host_of(state).session(0).candidates()
        self.assertEqual((r["coverage"]["scope_kinds"], r["coverage"]["completeness"]), ([L.KIND_ANSWER_DECISION], L.COMPLETE))
        withheld = [{"id": "R-5", "scope": L.RESIDUAL_ACTOR, "candidate": c} for c in r["coverage"]["withheld_input_candidates"]]
        self.assertEqual(r["coverage"]["residual"]["present"], withheld)

    def test_unverified_paths_are_a_separate_axis(self):
        r = host_of(opponent_face_down(H.DIGLETT)).session(0).candidates()
        paths = r["coverage"]["unverified_paths"]
        self.assertIn(L.REASON_FACE_DOWN, [p["reason"] for p in paths])  # 相手のうらのカードを指す特殊能力の組（U7-5e）
        powers = {c["id"] for c in r["candidates"] if c["kind"] == L.KIND_USE_POWER}
        self.assertTrue(powers & set(next(p for p in paths if p["reason"] == L.REASON_FACE_DOWN)["candidates"]))
        self.assertEqual(L._unverified_paths([]), [])


class TwinTest(unittest.TestCase):
    """隠れたカード（本人の手札・うらのカードの本当のカード）だけを変えた双子: 相手・観戦者の応答・観測・ログと、本人の応答の residual の公開の部分が同じ。"""

    def pair(self):
        return own_face_down(H.DIGLETT, hand=(H.FIRE,)), own_face_down(H.KADABRA, hand=(H.WATER,))

    def test_other_viewers_see_the_same(self):
        a, b = self.pair()
        self.assertNotEqual(a.cards[S.face_down(a)[0].card].card_id, b.cards[S.face_down(b)[0].card].card_id)
        self.assertEqual(without_handles(host_of(a).session(1).candidates()), without_handles(host_of(b).session(1).candidates()))
        self.assertEqual(without_handles(host_of(a).host_session().candidates()), without_handles(host_of(b).host_session().candidates()))
        for viewer in (1, None):
            self.assertEqual(observe(a, viewer), observe(b, viewer))
            self.assertEqual(visible_log(a, viewer), visible_log(b, viewer))

    def test_own_response_public_residual_is_the_same(self):
        a, b = self.pair()
        ca, cb = cov(a, 0), cov(b, 0)
        public = [lambda c: c["residual"]["classes"], lambda c: [i for i in c["residual"]["present"] if i["scope"] == L.RESIDUAL_PUBLIC],
                  lambda c: c["partial_residual"], lambda c: c["completeness"]]
        for get in public:
            self.assertEqual(get(ca), get(cb))


if __name__ == "__main__":
    unittest.main()
