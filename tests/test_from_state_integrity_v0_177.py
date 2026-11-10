"""v0.177（PT5E-FROM-STATE-INVARIANT。docs/pt5e-from-state-invariant-audit.md 9 章）: ``ClientHub.from_state``・``ActionHost.from_state`` の共通の状態の確かめ。

2 つの公開入口は ``adapter.checked_state_copy``（型 → 複製 → 複製の ``check_invariants``）を通し、不整合な状態を hub・セッション・取っ手を作る前に
``UnusableStateError``（``ValueError`` の子。``code`` は ``STATE_INTEGRITY``・``STATE_CHECK_ERROR``。文は固定。詳しい問題は ``problems``）で拒否する。

- 有効な状態（準備・番の途中・決定待ち・終局・停止・途中停止・サドン・デス）を受け付ける（不整合と混ぜない）
- 不整合（おもての山札の並び・重複・持ち主の違い・未知の番号）を拒否する。型の違いは ``TypeError``。複製・確かめの途中の例外は ``STATE_CHECK_ERROR``
- ``MemoryError`` は投げ直し、``KeyboardInterrupt``・``SystemExit`` は変えない。渡した状態を変えない。拒否では対戦・取っ手を作らない
- 秘密の位置だけが違う崩れた状態で、例外の型・code・文が同じ。文に問題の文を入れない
- スナップショットの保存・復元との整合。信頼された内部の組み立て（``ClientHub(A.HostedGame(state))``）は今のまま（検証者専用）

盤面は既存のテストの経路（``new_game``・``start_game``・公開のコマンド・``build_test_state`` の構築盤面）。確かめは不変条件だけで、効果の登録・規約集合の正しさは見ない。
"""

from __future__ import annotations

import unittest
from unittest import mock

from kyuura_engine import adapter as A
from kyuura_engine import client_api as C
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine import snapshot as SN
from kyuura_engine.engine import check_invariants
from kyuura_engine.errors import EngineError, StateIntegrityError
from kyuura_engine.state import GameState
from tests import helpers as H
from tests import test_sudden_death_v0_134 as SD
from tests.test_deferred_shortage_user_promos_v0_127 import dry_board, dry_up
from tests.test_legal_actions_pt5e_v0_176 import QUIZ3, broken_marks, staged, table
from tests.test_legal_actions_u7_1 import host_after_trainer, search_board, snap, without_handles
from tests.test_pikachu_games import play_game as pikachu_game
from tests.test_replay_record_v0_153 import HALT_DECK

REQ = {"contract": "kyuura-client-api", "format": 1}
MULLIGAN_DECKS = ([H.PIKACHU] + [H.FIRE] * 59, [H.PIKACHU] * 4 + [H.FIRE] * 56)  # test_client_api と同じ（seed 0）
ENTRIES = {"ClientHub.from_state": C.ClientHub.from_state, "ActionHost.from_state": L.ActionHost.from_state}


def held_state(entry_name, made):
    return made._host.game.state if entry_name == "ClientHub.from_state" else made.game.state


def valid_states():
    sudden = SD.constructed_sudden_death(SD.with_decklists(H.build_test_state(
        [{"active": SD.PIKA, "deck": [SD.PIKA] + [H.FIRE] * 30, "prizes": 0}, {"active": SD.PIKA, "deck": [SD.PIKA] + [H.FIRE] * 30, "prizes": 0}], current_player=0)))
    return {
        "setup": (A.start_game(*MULLIGAN_DECKS, 0).state, D.IN_PROGRESS),
        "main_constructed": (search_board(), D.IN_PROGRESS),
        "decision": (host_after_trainer(search_board((H.FIRE, H.FIRE, H.PONYTA))).game.state, None),
        "game_over": (pikachu_game(0)[0], D.GAME_OVER),
        "halted_setup": (A.start_game(HALT_DECK, HALT_DECK, 1).state, D.HALTED),
        "halted_interruption": (dry_up(dry_board(2), 3), D.HALTED),
        "sudden_death": (sudden, D.SUDDEN_DEATH_PENDING),
        "custom_registry": (H.build_test_state([{"active": {"card": H.CHARMANDER, "energy": [H.FIRE, H.FIRE]}}, {"active": H.STARYU}],
                                                effects=H.NO_EMBER_EFFECTS), D.IN_PROGRESS),
    }


def broken_states():
    base = search_board()
    duplicate = base.clone()
    duplicate.players[0].deck.append(duplicate.players[0].hand[1])  # 同じカードが手札と山札の 2 か所
    owner = base.clone()
    owner.players[0].hand.append(owner.players[1].hand.pop())  # 相手のカードを自分の手札へ（持ち主でないゾーン）
    unknown = base.clone()
    unknown.players[0].hand.append(9999)  # 未知の番号
    return {"face_up_marks": broken_marks(staged(table(QUIZ3), "top_only"), 1, 2), "duplicate": duplicate, "wrong_owner": owner, "unknown_reference": unknown}


def rejection(test, entry, state):
    with test.assertRaises(A.UnusableStateError) as caught:
        entry(state)
    return caught.exception


class AcceptTest(unittest.TestCase):
    def test_new_game_state_is_accepted_like_start(self):
        state = A.start_game(*MULLIGAN_DECKS, 0).state
        started, _ = C.ClientHub.start(*MULLIGAN_DECKS, 0)
        hub = C.ClientHub.from_state(state)
        for actor in (0, 1):
            self.assertEqual(without_handles(hub.player(actor).handle({**REQ, "type": "candidates"})["response"]),
                             without_handles(started.player(actor).handle({**REQ, "type": "candidates"})["response"]))
        self.assertEqual(snap(L.ActionHost.from_state(state).game.state), snap(state))

    def test_valid_states_are_accepted_by_both_entries(self):
        for name, (state, status) in valid_states().items():
            self.assertEqual(check_invariants(state), [], name)
            for entry_name, entry in ENTRIES.items():
                with self.subTest(state=name, entry=entry_name):
                    before = snap(state)
                    held = held_state(entry_name, entry(state))
                    self.assertIsNot(held, state)  # 複製を持つ
                    self.assertEqual((snap(held), snap(state)), (before, before))  # 渡した状態は変わらず、同じ中身
                    if status is not None:
                        self.assertEqual(D.status_of(held), status)
        decision = valid_states()["decision"][0]
        self.assertIsNotNone(decision.decision)  # 決定待ち


class RejectTest(unittest.TestCase):
    def test_inconsistent_states_are_rejected_by_both_entries(self):
        for name, state in broken_states().items():
            for entry_name, entry in ENTRIES.items():
                with self.subTest(state=name, entry=entry_name):
                    before = snap(state)
                    error = rejection(self, entry, state)
                    self.assertEqual((error.code, error.stage), (A.STATE_INTEGRITY_CODE, "check"))
                    self.assertIsInstance(error.problems, tuple)
                    self.assertTrue(error.problems and all(type(p) is str for p in error.problems))
                    self.assertEqual(tuple(check_invariants(state)), error.problems)
                    self.assertEqual(snap(state), before)  # 渡した状態は変わらない
                    self.assertIsInstance(error, ValueError)
                    self.assertNotIsInstance(error, (EngineError, StateIntegrityError))

    def test_fixed_text_has_no_problem_details(self):
        for name, state in broken_states().items():
            error = rejection(self, C.ClientHub.from_state, state)
            with self.subTest(name):
                self.assertEqual(str(error), A._UNUSABLE_STATE_TEXTS[A.STATE_INTEGRITY_CODE])
                for problem in error.problems:
                    self.assertNotIn(problem, str(error))
                self.assertFalse(any(ch.isdigit() for ch in str(error)))  # カードの番号などの値を入れない

    def test_hidden_position_only_twins_get_the_same_rejection(self):
        """秘密（相手の山札のどの位置に印があるか）だけが違う 2 つの崩れた状態（本人の観測は同じ）で、型・code・文が同じ。詳しい問題は problems だけ。"""
        base = staged(table(QUIZ3), "top_only")
        far, near = broken_marks(base, 1, 6), broken_marks(base, 1, 1)
        outs = []
        for state in (far, near):
            for entry in ENTRIES.values():
                error = rejection(self, entry, state)
                outs.append((type(error), error.code, error.stage, str(error)))
                self.assertTrue(error.problems)
        self.assertEqual(len(set(outs)), 1)

    def test_no_host_session_or_handle_is_created_on_rejection(self):
        state = broken_states()["face_up_marks"]
        with mock.patch.object(A.HostedGame, "__init__", side_effect=AssertionError("HostedGame を作った")), \
                mock.patch.object(L.secrets, "token_hex", side_effect=AssertionError("取っ手・対戦の番号を作った")):
            for entry in ENTRIES.values():
                rejection(self, entry, state)

    def test_type_mismatch_is_a_type_error(self):
        state = search_board()

        class Sub(GameState):
            pass

        sub = state.clone()
        sub.__class__ = Sub
        for value in (None, {}, "state", sub):
            for entry in ENTRIES.values():
                with self.subTest(value=type(value).__name__), self.assertRaises(TypeError) as caught:
                    entry(value)
                self.assertNotIsInstance(caught.exception, A.UnusableStateError)

    def test_clone_and_check_exceptions_are_check_errors(self):
        state = search_board()
        cases = [("clone", mock.patch.object(GameState, "clone", side_effect=RuntimeError("壊れた複製"))),
                 ("check", mock.patch.object(A, "check_invariants", side_effect=KeyError("壊れた参照")))]
        for stage, patch in cases:
            for entry in ENTRIES.values():
                with self.subTest(stage=stage), patch:
                    error = rejection(self, entry, state)
                    self.assertEqual((error.code, error.stage, error.problems), (A.STATE_CHECK_ERROR_CODE, stage, ()))
                    self.assertIsInstance(error.__cause__, (RuntimeError, KeyError))
                    self.assertEqual(str(error), A._UNUSABLE_STATE_TEXTS[A.STATE_CHECK_ERROR_CODE])

    def test_memory_error_and_exits_are_not_converted(self):
        state = search_board()
        for stage, target, attr in (("clone", GameState, "clone"), ("check", A, "check_invariants")):
            for raised in (MemoryError(), KeyboardInterrupt(), SystemExit(3)):
                with self.subTest(stage=stage, raised=type(raised).__name__), mock.patch.object(target, attr, side_effect=raised), \
                        self.assertRaises(type(raised)) as caught:
                    C.ClientHub.from_state(state)
                self.assertNotIsInstance(caught.exception, A.UnusableStateError)


class ConsistencyTest(unittest.TestCase):
    def test_snapshot_round_trip_and_refusal_agree(self):
        state = staged(table(QUIZ3), "top_only")
        restored = SN.restore_snapshot(SN.dumps_snapshot(SN.save_snapshot(state, label="from-state")))
        self.assertTrue(restored.restored)
        for entry in ENTRIES.values():
            entry(restored.state)  # 復元した状態は受け付ける
        broken = broken_marks(state, 1, 2)
        with self.assertRaises(SN.SnapshotSaveError):
            SN.save_snapshot(broken, label="broken")
        for entry in ENTRIES.values():
            rejection(self, entry, broken)  # スナップショットが保存を断る崩れた状態は、入口も断る

    def test_trusted_internal_construction_is_unchanged(self):
        """信頼された内部の組み立て（検証者専用。通常の使い方ではない）は確かめない（v0.176 までと同じ）。崩れた状態でも PT-5e の候補の側のガードで unverified。"""
        broken = broken_marks(staged(table(QUIZ3), "top_only"), 1, 2)
        hub = C.ClientHub(A.HostedGame(broken.clone()))
        r = hub.player(0).handle({**REQ, "type": "candidates"})["response"]
        c = next(x for x in r["candidates"] if x["kind"] == L.KIND_PLAY_TRAINER)
        stage = hub.player(0).handle({**REQ, "type": "inputs", "game": r["game"], "revision": r["revision"], "candidate": c["id"]})["response"]["stages"][0]
        option = next(o for o in stage["options"] if o["card_id"] == QUIZ3)
        self.assertEqual(option["processability"], L.UNVERIFIED)
        self.assertIsNotNone(L.ActionHost(A.HostedGame(broken.clone())).session(0).candidates())

    def test_public_names(self):
        self.assertIs(C.UnusableStateError, A.UnusableStateError)
        self.assertIs(L.UnusableStateError, A.UnusableStateError)
        self.assertEqual((A.STATE_INTEGRITY_CODE, A.STATE_CHECK_ERROR_CODE), ("STATE_INTEGRITY", "STATE_CHECK_ERROR"))
        self.assertNotIn("STATE_INTEGRITY", C.ERROR_MESSAGES)  # JSON の要求・応答のエラーのコード表は変えていない


if __name__ == "__main__":
    unittest.main()
