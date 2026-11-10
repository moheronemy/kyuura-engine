"""U7-5f（docs/legal-actions-u7-5fg.md 1 章）: おもての山札の確かめ（CheckFaceUpDeckCard）の、表示だけの候補 check_face_up_deck の回帰テスト。

確かめの種類を分ける:

- 合法な操作の列（tests.helpers.build_test_state の盤面から apply_command でフラッシュ（ES2-035）を使い、決定に答え、番を終える）: おもての枚数 5・4、相手・本人の山札、
  番のプレイヤー・番でないプレイヤー、本当のカードだけが違う双子、直接のコマンドとの一致、client_api
- 構築盤面（状態の face_up_deck を直接置く。おもての並びの不変条件は満たすが、おもてにしたログはない）: おもての枚数 0・1（いちばん上だけ）
- 状態・乱数・ログの不変、取っ手、入力の形の誤りと未裁定による送信不可の区別

停止コードの文字列はテストの中に書かない（区分・ホストの段のコード・エンジンの例外の型で確かめる）。
"""

from __future__ import annotations

import pathlib
import unittest

from kyuura_engine import diagnostics as D
from kyuura_engine import faceup
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from kyuura_engine.commands import (
    CheckFaceUpDeckCard,
    EndTurn,
    PlayTrainer,
    ResolveDecision,
)
from kyuura_engine.engine import apply_command
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe
from tests import helpers as H
from tests.test_legal_actions_u7_1 import snap, without_handles
from tests.test_legal_actions_u7_3 import cand, host_of

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT = {"contract": "kyuura-client-api", "format": 1}
FLASH = "ES2-035"  # フラッシュ（おたがいの山札の上から 5 枚をならべ替えて、おもてを上にもどす）


def flashed(deck1=(H.FIRE, H.WATER, H.GRASS, H.FIRE, H.WATER, H.FIRE, H.FIRE)):
    """相手（1）が自分の番にフラッシュを使い、両方が並べ替えに答えて、番を終えた盤面（プレイヤー 0 の番。0 は番の始めに 1 枚引くので、0 の山札のおもては 4 枚、1 は 5 枚）。"""
    me = {"active": H.CHARMANDER, "bench": [H.RATTATA], "hand": [H.FIRE], "deck": [H.FIRE] * 8, "prizes": [H.FIRE] * 2}
    them = {"active": H.CHARMANDER, "bench": [], "hand": [FLASH], "deck": list(deck1), "prizes": [H.FIRE] * 2}
    state = H.build_test_state([me, them], turn_number=4, current_player=1)
    flash = next(u for u in state.players[1].hand if state.cards[u].card_id == FLASH)
    state = apply_command(state, PlayTrainer(1, flash))
    while state.decision is not None:
        d = state.decision
        state = apply_command(state, ResolveDecision(d.player, d.id, tuple(d.options)))  # 見た 5 枚を上からの順のまま
    state = apply_command(state, EndTurn(1))
    while state.decision is not None:
        d = state.decision
        state = apply_command(state, ResolveDecision(d.player, d.id, d.options[:d.min_choices]))
    assert state.current_player == 0 and faceup.prefix_problems(state) == []
    return state


def built(count):
    """構築盤面: 相手（1）の山札の上から ``count`` 枚をおもてにした（ログはない。並びの不変条件は満たす）。"""
    state = H.build_test_state([{"active": H.CHARMANDER, "deck": [H.FIRE] * 5}, {"active": H.CHARMANDER, "deck": [H.FIRE, H.WATER, H.GRASS, H.FIRE]}], turn_number=3)
    state.face_up_deck = tuple(state.players[1].deck[:count])
    return state


def face_up(state, actor=0):
    host = host_of(state)
    session = host.session(actor)
    r = session.candidates()
    c = cand(r, L.KIND_CHECK_FACE_UP_DECK)
    return host, session, r, c


class CandidateTest(unittest.TestCase):
    def test_positions_from_the_public_count_only(self):
        state = flashed()
        self.assertEqual((observe(state, 0)["players"][1]["deck"]["face_up_count"], observe(state, 0)["players"][0]["deck"]["face_up_count"]), (5, 4))
        _h, session, r, c = face_up(state)
        self.assertEqual((c["processability"], c["reasons"], c["input_disclosure"], c["input_stages"]),
                         (L.RULING_UNRESOLVED, [L.REASON_STOPS], L.DISCLOSURE_CONFIRMED, [{"stage": 1, "input": L.INPUT_CHOOSE_OPTION}]))
        stage = session.inputs(r["game"], r["revision"], c["id"])["stages"][0]
        self.assertEqual((stage["role"], stage["meaning"], stage["count"]), ("face_up_position", "deck_position", {"min": 1, "max": 1}))
        self.assertEqual([(o["owner"], o["position"]) for o in stage["options"]], [(1, p) for p in range(1, 5)])  # 相手の山札の 2 枚目〜5 枚目（自分の山札・いちばん上を出さない）
        for option in stage["options"]:
            self.assertEqual(set(option), {"id", "owner", "position", "eligible", "processability", "reasons"})  # カード id・uid・名前を出さない
            self.assertEqual((option["eligible"], option["processability"]), (False, L.RULING_UNRESOLVED))
        cov = r["coverage"]
        self.assertEqual((cov["display_only_kinds"], cov["not_covered_kinds"], cov["completeness"]), ([L.KIND_CHECK_FACE_UP_DECK], [], L.PARTIAL))
        self.assertIn(L.KIND_CHECK_FACE_UP_DECK, cov["offered_kinds"])

    def test_counts_zero_one_many(self):
        for count, positions in ((0, None), (1, None), (2, [1]), (4, [1, 2, 3])):
            with self.subTest(count=count):
                _h, session, r, c = face_up(built(count))
                if positions is None:
                    self.assertIsNone(c)  # おもてがない・いちばん上だけ（観測に出ている）: ゲーム上できない
                    self.assertIn(L.KIND_CHECK_FACE_UP_DECK, r["coverage"]["scope_kinds"])
                    continue
                stage = session.inputs(r["game"], r["revision"], c["id"])["stages"][0]
                self.assertEqual([o["position"] for o in stage["options"]], positions)

    def test_shown_positions_are_the_engines_fu2_and_hidden_ones_are_illegal(self):
        state = flashed()
        _h, session, r, c = face_up(state)
        shown = {o["position"] for o in session.inputs(r["game"], r["revision"], c["id"])["stages"][0]["options"]}
        for owner in (0, 1):
            for position in range(8):
                with self.subTest(owner=owner, position=position):
                    expected = UnsupportedError if (owner == 1 and position in shown) else IllegalActionError
                    with self.assertRaises(expected) as caught:
                        apply_command(state, CheckFaceUpDeckCard(0, owner, position))
                    self.assertIs(type(caught.exception), expected)
                    if expected is UnsupportedError:  # 未裁定（診断のコード表の分類）。候補の処理可能性と同じ
                        self.assertEqual(D.default_catalog().get(caught.exception.code).category, D.RULING_UNRESOLVED)

    def test_twins_differ_only_in_the_face_up_cards_below_the_top(self):
        a = flashed((H.FIRE, H.WATER, H.GRASS, H.FIRE, H.WATER, H.FIRE, H.FIRE))
        b = flashed((H.FIRE, H.GRASS, H.WATER, H.WATER, H.FIRE, H.FIRE, H.FIRE))
        self.assertNotEqual([a.cards[u].card_id for u in a.players[1].deck], [b.cards[u].card_id for u in b.players[1].deck])
        self.assertEqual(observe(a, 0), observe(b, 0))  # 本人の観測は同じ（いちばん上だけが公開）

        def answers(state):
            _h, session, r, c = face_up(state)
            out = [without_handles(r), session.inputs(r["game"], r["revision"], c["id"])]
            out += [session.check(r["game"], r["revision"], c["id"], ch) for ch in (["o1"], ["o4"], ["o9"], [], ["o1", "o2"], [1])]
            return out

        self.assertEqual(answers(a), answers(b))


class ActorTest(unittest.TestCase):
    def test_not_the_turn_player_gets_no_candidate(self):
        state = flashed()
        _h, _s, r, c = face_up(state, actor=1)
        self.assertIsNone(c)
        self.assertEqual((r["situation"], r["candidates"]), (L.WAITING_FOR_PLAYER, []))
        # 番でないプレイヤーの相手の山札（0 の山札。おもて 4 枚）にエンジンは FU2 を返す（番を確かめない）。U7 は示さない（API の対応の範囲。D-U75-FACE-UP-ACTORS）
        with self.assertRaises(UnsupportedError):
            apply_command(state, CheckFaceUpDeckCard(1, 0, 1))


class SubmitTest(unittest.TestCase):
    def test_refusals_distinguish_bad_input_from_unresolved(self):
        state = flashed()
        before = snap(state)
        host, session, r, c = face_up(state)
        for choices, code in ((["o1"], L.CANDIDATE_NOT_EXECUTABLE), (["o4"], L.CANDIDATE_NOT_EXECUTABLE), (["o9"], L.CANDIDATE_INPUT_INVALID),
                              ([], L.CANDIDATE_INPUT_INVALID), (["o1", "o2"], L.CANDIDATE_INPUT_INVALID), (["o1", "o1"], L.CANDIDATE_INPUT_INVALID),
                              ([1], L.CANDIDATE_INPUT_INVALID), ("o1", L.CANDIDATE_INPUT_INVALID)):
            with self.subTest(choices=choices):
                self.assertEqual(session.check(r["game"], r["revision"], c["id"], choices)["refusal"]["code"], code)
                result = session.submit(r["game"], r["revision"], c["id"], choices)
                self.assertEqual((result.outcome, result.refusal.code, result.view), (L.REFUSED, code, None))  # エンジンに渡さない
        self.assertIs(host.game.state, state)
        self.assertEqual(snap(host.game.state), before)
        self.assertEqual(session.check(r["game"], r["revision"], c["id"], ["o1"])["refusal"]["code"], L.CANDIDATE_NOT_EXECUTABLE)  # 拒否で取っ手を失効させない
        other = host.session(1).candidates()
        self.assertEqual(session.check(other["game"], other["revision"], c["id"], ["o1"])["refusal"]["code"], L.CANDIDATES_WRONG_ACTOR)

    def test_client_api(self):
        state = flashed()
        hub = ClientHub.from_state(state)
        player, other, spectator = hub.player(0), hub.player(1), hub.spectator()
        r = player.handle({**CONTRACT, "type": "candidates"})["response"]
        c = cand(r, L.KIND_CHECK_FACE_UP_DECK)
        handle = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        inputs = player.handle({**CONTRACT, "type": "inputs", **handle})
        self.assertTrue(inputs["ok"])
        sent = player.handle({**CONTRACT, "type": "submit", **handle, "choices": ["o1"]})
        self.assertEqual((sent["outcome"], sent["refusal"]["code"], sent["refetch_required"]), (L.REFUSED, L.CANDIDATE_NOT_EXECUTABLE, False))
        for audience in (0, 1, "spectator", "host"):
            self.assertEqual(hub.take_updates(audience), [])  # 送る前の拒否: 公開の更新を作らない（相手・観戦者に知らせない）
        self.assertIsNone(cand(other.handle({**CONTRACT, "type": "candidates"})["response"], L.KIND_CHECK_FACE_UP_DECK))
        self.assertEqual(spectator.handle({**CONTRACT, "type": "candidates"})["error"]["code"], "CLIENT_REQUEST_UNKNOWN")


class MappingTest(unittest.TestCase):
    def test_kind_lists(self):
        self.assertIn(L.KIND_CHECK_FACE_UP_DECK, L.IMPLEMENTED_KINDS)
        self.assertEqual(L.DISPLAY_ONLY_KINDS, (L.KIND_CHECK_FACE_UP_DECK,))
        self.assertEqual(L.MAIN_KINDS[-1], L.KIND_CHECK_FACE_UP_DECK)


if __name__ == "__main__":
    unittest.main()
