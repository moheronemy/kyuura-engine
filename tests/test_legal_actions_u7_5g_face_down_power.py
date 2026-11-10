"""U7-5g（docs/legal-actions-u7-5fg.md 4 章）: 本人のうらのカードの特殊能力（D-U75-FACE-DOWN-POWER）の回帰テスト。

確かめの種類を分ける:

- 合法な操作の列（tests.test_secret_plan_v0_67 の盤面から apply_command でマチスの秘策を使い、本当のカードをうらにしてベンチに出す）: 本人への候補と相手・観戦者への非公開、
  入力なし・1 段の代表、2 段以上の型の入力を返さないこと、候補の取得でおもてにしないこと、送ったときの拒否・受理のあとの決定・「たねポケモン」でないカードのトラッシュ、
  直接のコマンドとの一致、本当のカードだけが違う双子、client_api
- 補助関数の確かめ: エンジンの確かめ（check_use_pokemon_power）をうらのままのカードに呼んでも、状態・ログを変えず、おもてにしないこと

停止コードの文字列はテストの中に書かない。
"""

from __future__ import annotations

import unittest

from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from kyuura_engine.commands import UsePokemonPower
from kyuura_engine.engine import check_use_pokemon_power
from kyuura_engine.errors import EngineError
from kyuura_engine.observation import observe, visible_log
from tests import helpers as H
from tests import test_secret_plan_v0_67 as S
from tests.test_legal_actions_u7_1 import snap, without_handles
from tests.test_legal_actions_u7_3 import host_of, via_direct

CONTRACT = {"contract": "kyuura-client-api", "format": 1}
MANKEY = H.JUNGLE_MANKEY  # マンキー（たね。［スパイ］: 入力なし。受理のあとに見るカードを選ぶ決定）
UNOWN_B = "neo3-032"  # アンノーンB（たね。［ベアー］: 自分の場のポケモン 1 匹を選ぶ 1 段）
MAGNETON = "GD3-006"  # マチスのレアコイル（1 進化。［エナジーチャージ］: 入力なし。うらから出すと「たねポケモン」でないのでトラッシュ）
ROCKET_CHARMANDER = H.ROCKET_CHARMANDER  # ロケット団のヒトカゲ（たね。［ほのおをもらう］: 2 段。本人の知識だけで入力を作れない）


def placed(real, hand=()):
    """プレイヤー 0 がマチスの秘策で ``real`` をうらにしてベンチに出した盤面（0 の番の MAIN。相手は知らない）。"""
    return S.place(S.board(hand=(real, *hand)), real)


def face_down_powers(response):
    return [c for c in response["candidates"] if c["kind"] == L.KIND_USE_POWER and c["power"].get("face_down")]


def one(state, actor=0):
    host = host_of(state)
    session = host.session(actor)
    r = session.candidates()
    found = face_down_powers(r)
    return host, session, r, (found[0] if found else None)


class CandidateTest(unittest.TestCase):
    def test_no_input_power_for_the_owner_only(self):
        state = placed(MANKEY)
        fd = S.face_down(state)[0]
        before = snap(state)
        _h, session, r, c = one(state)
        self.assertEqual((c["power"]["name_ja"], c["power"]["card_id"], c["power"]["index"]), ("スパイ", MANKEY, 0))
        self.assertEqual((c["processability"], c["reasons"], c["input_disclosure"], c["input_stages"]), (L.UNVERIFIED, [L.REASON_FACE_DOWN], L.DISCLOSURE_NONE, []))
        self.assertEqual((c["pokemon"]["pokemon"], c["pokemon"].get("face_down"), "card_id" in c["pokemon"]), (fd.pokemon_id, True, False))
        self.assertTrue(session.check(r["game"], r["revision"], c["id"], [])["valid"])
        self.assertEqual(snap(state), before)  # 候補・検査でおもてにしない（状態・乱数・ログ・決定の番号が同じ）
        self.assertTrue(state.is_face_down(fd))

    def test_one_stage_power_lists_the_declared_place_unverified(self):
        state = placed(UNOWN_B)
        _h, session, r, c = one(state)
        stages = session.inputs(r["game"], r["revision"], c["id"])["stages"]
        self.assertEqual([s["role"] for s in stages], ["source"])
        options = stages[0]["options"]
        self.assertEqual([o["pokemon"] for o in options], [q.pokemon_id for q in state.players[0].in_play()])  # 宣言の場所（自分の場）の並び
        self.assertEqual({(o["processability"], tuple(o["reasons"])) for o in options}, {(L.UNVERIFIED, (L.REASON_FACE_DOWN,))})
        self.assertEqual(L.stage_dependency_problems(stages), [])

    def test_multi_stage_power_withholds_inputs(self):
        # v0.175（U-R3a）: 2 段の型は構造の組を示す（tests/test_legal_actions_u_r3a_v0_175.py）。入力を返さないのは、組が完成しない場面（自分の場のどのポケモンにも
        # ついているカードがない）。v0.172〜v0.174 はエネルギーのある盤面でも返さなかった（意図した差）
        state = S.place(S.board(hand=(ROCKET_CHARMANDER,), active={"card": H.HITMONCHAN, "energy": []}), ROCKET_CHARMANDER)
        _h, session, r, c = one(state)
        self.assertEqual((c["processability"], c["input_disclosure"]), (L.NOT_IMPLEMENTED, L.DISCLOSURE_UNCONFIRMED))
        answer = session.inputs(r["game"], r["revision"], c["id"])
        self.assertEqual((answer["stages"], answer["withheld"]["code"]), ([], L.INPUT_BOUNDARY_UNCONFIRMED))
        self.assertIn({"id": "R-3", "scope": L.RESIDUAL_ACTOR, "candidate": c["id"]}, r["coverage"]["residual"]["present"])
        self.assertEqual(session.check(r["game"], r["revision"], c["id"], [])["refusal"]["code"], L.CANDIDATE_NOT_EXECUTABLE)

    def test_no_power_and_non_pokemon(self):
        for real in (H.RATTATA, H.FIRE):
            with self.subTest(real=real):
                self.assertIsNone(one(placed(real))[3])

    def test_engine_check_on_a_face_down_card_changes_nothing(self):
        state = placed(MANKEY)
        fd = S.face_down(state)[0]
        before = snap(state)
        try:
            check_use_pokemon_power(state, UsePokemonPower(0, fd.pokemon_id, 0))
        except EngineError:
            pass  # うらのままでは本当のカードの力を探さない（例外の種類はエンジンの今の挙動。候補の作成はこれを呼ばない）
        self.assertEqual(snap(state), before)
        self.assertTrue(state.is_face_down(fd))


class InformationTest(unittest.TestCase):
    def test_twins_other_viewers_and_updates_are_the_same(self):
        a, b = placed(MANKEY), placed(H.RATTATA)  # 本当のカードだけが違う（特殊能力がある・ない）
        self.assertEqual(without_handles(host_of(a).session(1).candidates()), without_handles(host_of(b).session(1).candidates()))
        for viewer in (1, None):
            self.assertEqual(observe(a, viewer), observe(b, viewer))
            self.assertEqual(visible_log(a, viewer), visible_log(b, viewer))
        own_a, own_b = host_of(a).session(0).candidates(), host_of(b).session(0).candidates()
        self.assertEqual(len(face_down_powers(own_a)), 1)
        self.assertEqual(face_down_powers(own_b), [])
        public = [lambda r: r["coverage"]["residual"]["classes"], lambda r: r["coverage"]["partial_residual"],
                  lambda r: [i for i in r["coverage"]["residual"]["present"] if i["scope"] == L.RESIDUAL_PUBLIC]]
        for get in public:
            self.assertEqual(get(own_a), get(own_b))
        hub = ClientHub.from_state(a)
        me = hub.player(0)
        r = me.handle({**CONTRACT, "type": "candidates"})["response"]
        c = face_down_powers(r)[0]
        handle = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        self.assertTrue(me.handle({**CONTRACT, "type": "check", **handle, "choices": []})["response"]["valid"])
        for audience in (0, 1, "spectator", "host"):
            self.assertEqual(hub.take_updates(audience), [])  # 候補・検査は更新を作らない（能力の名前・件数・カード id を相手・観戦者に出さない）


class SubmitTest(unittest.TestCase):
    def assert_same(self, state, command, choices):
        host = host_of(state.clone())
        session = host.session(0)
        r = session.candidates()
        c = face_down_powers(r)[0]
        result = session.submit(r["game"], r["revision"], c["id"], choices)
        game, direct = via_direct(state, command)
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual(snap(host.game.state), snap(game.state))
        return host, result

    def test_basic_card_reveals_then_uses_the_power_with_a_later_decision(self):
        state = placed(MANKEY)
        fd = S.face_down(state)[0]
        host, result = self.assert_same(state, UsePokemonPower(0, fd.pokemon_id, 0), [])
        after = host.game.state
        self.assertEqual(result.outcome, D.ACCEPTED)
        self.assertFalse(after.face_down_cards)  # 受理のあと、おもてにしたカードは全員に公開
        self.assertIsNotNone(after.decision)  # 受理のあとの決定（見るカード）。宣言の前に移していない
        self.assertEqual([c["kind"] for c in host.session(0).candidates()["candidates"]], [L.KIND_ANSWER_DECISION])

    def test_rejected_after_reveal_leaves_the_state_unchanged(self):
        state = placed(UNOWN_B)
        fd = S.face_down(state)[0]
        other = state.players[0].active.pokemon_id
        hub = ClientHub.from_state(state)
        me = hub.player(0)
        r = me.handle({**CONTRACT, "type": "candidates"})["response"]
        c = face_down_powers(r)[0]
        handle = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        stages = me.handle({**CONTRACT, "type": "inputs", **handle})["response"]["stages"]
        choice = next(o["id"] for o in stages[0]["options"] if o["pokemon"] == other)
        before = snap(hub._host.game.state)
        sent = me.handle({**CONTRACT, "type": "submit", **handle, "choices": [choice]})
        self.assertEqual(sent["outcome"], D.REJECTED)  # おもてにしたあとの確かめが受け付けない: コマンドごと拒否（ダメージカウンターがないなど）
        self.assertEqual(snap(hub._host.game.state), before)  # 状態・ログはもどり、おもてにしたことも公開されない
        for audience in (1, "spectator"):
            self.assertEqual(hub.take_updates(audience), [])
        _g, direct = via_direct(state, UsePokemonPower(0, fd.pokemon_id, 0, source=other))
        self.assertEqual(direct.outcome, D.REJECTED)

    def test_non_basic_card_is_trashed_and_accepted(self):
        state = placed(MAGNETON)
        fd = S.face_down(state)[0]
        _h, c = None, one(state)[3]
        self.assertEqual((c["processability"], c["power"]["card_id"]), (L.UNVERIFIED, MAGNETON))  # おもてにした結果（トラッシュ）を予告しない（D-U75-REVEAL-OUTCOME）
        host, result = self.assert_same(state, UsePokemonPower(0, fd.pokemon_id, 0), [])
        self.assertEqual(result.outcome, D.ACCEPTED)
        self.assertNotIn(fd.pokemon_id, [q.pokemon_id for q in host.game.state.players[0].in_play()])
        kinds = [e["kind"] for e in host.game.state.log[len(state.log):]]
        self.assertIn("secret_plan_discarded", kinds)
        self.assertNotIn("pokemon_power", kinds)  # 特殊能力はおこらない

    def test_handles_and_bad_input(self):
        state = placed(UNOWN_B)
        host, session, r, c = one(state)
        for choices in ([], ["o99"], ["o1", "o2"], [1]):
            self.assertEqual(session.check(r["game"], r["revision"], c["id"], choices)["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)
        other = host.session(1).candidates()
        self.assertEqual(session.check(other["game"], other["revision"], c["id"], ["o1"])["refusal"]["code"], L.CANDIDATES_WRONG_ACTOR)


if __name__ == "__main__":
    unittest.main()
