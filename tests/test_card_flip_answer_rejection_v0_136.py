"""v0.136: カードめくりゲーム（neo1-080）の、答えの受理・拒否による情報漏れの修正（docs/card-flip-answer-rejection-v0.136.md）。

原文: うらになっている相手の「サイドカード」を1枚選び、そのカードが「ポケモン」か「トレーナーカード」か「エネルギーカード」かを答える。その後、そのカードをおもてにして、正解なら、
あなたは山札からカードを2枚引いて、手札に加える。（正解でないなら何もしない。おもてにしたサイドはそのまま。）

選ぶのも答えるのも使ったプレイヤーで、選ぶサイドはだれにも見えない。おもてのカードのある山札（v0.126。フラッシュ）で、正解の引き方（使ったプレイヤーが 2 枚）だけが既存の止め方（FU3）
に当たると、v0.135 までは答えの段階で正解だけが拒否された（拒否は状態を変えないので、答えを試してサイドの種類を知り、正解でない答えを選び直せた）。v0.136 は、使う前に両方の結果
（正解: 使ったプレイヤーが 2 枚引く。正解でない: 引かない）を確かめ、どちらかが止め方に当たれば使う前に止める（v0.135 の ``effects.quiz_draw_outcome_stop`` に ``outcomes`` を加えて共通に使う）。

- 合法な実カードの経路（フラッシュ・パソコン通信・番の最初のドロー・錯乱ジム・［ちえくらべ］・サドン・デス）と、テスト専用の改変（山札の枚数・おもての印を直接決めた盤面。
  ``shaped``）を分けて書く。テスト専用の盤面は、山札の枚数と印の組み合わせを網羅するためだけに使う
- 比べる検査（``log_audit.twin_command_problems``）は、公開の情報が同じで、選ぶサイド（うら）の種類だけが違う状態に、同じ操作を送る
"""

from __future__ import annotations

import copy
import itertools
import pathlib
import pickle
import unittest

from kyuura_engine import (
    IllegalActionError,
    Phase,
    PlayTrainer,
    ResolveDecision,
    StartSuddenDeath,
    UnsupportedError,
    apply_command,
    check_invariants,
)
from kyuura_engine import effects as E
from kyuura_engine import faceup as FU
from kyuura_engine.cards import load_card_pool
from kyuura_engine.decisions import QUIZ_ANSWER, REACTION_POWER, SELECT_OPPONENT_PRIZE
from kyuura_engine.effects import TrainerUse
from tests.helpers import CHAOS_GYM, HITMONCHAN, T, build_test_state, with_coin_results
from tests.log_audit import (
    observation_problems,
    public_view,
    serialization_problems,
    twin_command_problems,
)
from tests.test_quiz_answer_rejection_v0_135 import (
    BILL,
    COMPUTER_SEARCH,
    ENERGIES,
    FLASH,
    GYARADOS,
    OAK,
    PSYCHIC,
    QUIZZES,
    SLOWKING,
    SLOWPOKE,
    card_in_hand,
    computer_search_shuffle,
    end_turns,
    fingerprint,
    play_flash,
    resolve,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "card-flip-answer-rejection-v0.136.md"

CARD_FLIP = "neo1-080"
DRAW = 2
FU3 = FU.FACE_UP_DECK_HIDDEN_TAKE_CODE
FC1 = E.STATED_CARDS_SHORT_CODE
# 選ぶサイド（相手のサイドの位置 0）の 3 つの種類。答えの位置は FLIP_KIND_NAMES の順（ポケモン・トレーナーカード・エネルギーカード）。テストが独立に持つ
HIDDEN_PRIZES = {"PMCG1-058": 0, "PMCG1-071": 1, "PMCG1-097": 2}  # エビワラー（ポケモン）・きずぐすり（トレーナーカード）・草エネルギー（エネルギーカード）
FILLER_PRIZE = "PMCG1-098"
MODES = ("none", "both", "user_only", "opponent_only", "second", "top_only")
STOPPING = ("both", "user_only", "second")  # 使ったプレイヤーの山札の 2 枚目がおもて（正解で 2 枚引くと FU3）
SAFE = ("none", "opponent_only", "top_only")


def board(hand, prize0, *, deck0=None, deck1=None, opponent_hand=(), opponent_active=None, turn_number=3, prizes1=None, discard1=()):
    """プレイヤー 0 の番。相手（プレイヤー 1）のサイドの位置 0 が ``prize0``（うら）、ほかは草以外の基本エネルギー。山札は基本エネルギー（既定 12 枚ずつ）。"""
    deck0 = list(ENERGIES) * 2 if deck0 is None else list(deck0)
    deck1 = list(reversed(ENERGIES)) * 2 if deck1 is None else list(deck1)
    prizes1 = [prize0] + [FILLER_PRIZE] * 5 if prizes1 is None else prizes1
    return build_test_state([{"active": HITMONCHAN, "hand": list(hand), "deck": deck0, "prizes": 6},
                             {"active": opponent_active or HITMONCHAN, "hand": list(opponent_hand), "deck": deck1, "prizes": prizes1, "discard": list(discard1)}],
                            current_player=0, turn_number=turn_number)


def legal_marks(prize0, mode, *, extra_hand=(), hand=(CARD_FLIP,), discard1=()):
    """合法な実カードの経路で作った盤面（プレイヤー 0 の番。手札にカードめくりゲーム）。``mode`` は v0.135 の ``legal_marks`` と同じ（none・both・user_only・opponent_only・second・top_only）。"""
    extra = (COMPUTER_SEARCH, BILL, OAK) if mode == "opponent_only" else ()
    opponent_hand = (COMPUTER_SEARCH, BILL, OAK) if mode == "user_only" else ()
    state = board((FLASH, *hand, *extra_hand, *extra), prize0, opponent_hand=opponent_hand, discard1=discard1)
    if mode == "none":
        return state
    state = play_flash(state)
    if mode == "user_only":
        state = end_turns(computer_search_shuffle(end_turns(state, 1), 1), 1)
    elif mode == "opponent_only":
        state = computer_search_shuffle(state, 0)
    elif mode == "second":
        state = end_turns(state, 6)
    elif mode == "top_only":
        state = end_turns(state, 8)
    assert state.current_player == 0 and state.decision is None and check_invariants(state) == [], check_invariants(state)
    return state


def twins(mode):
    """だれの公開の情報も同じで、相手のサイドの位置 0（うら）の種類だけが違う 3 つの状態。"""
    return [legal_marks(prize, mode) for prize in HIDDEN_PRIZES]


def play(state, player=0):
    return apply_command(state, PlayTrainer(player, card_in_hand(state, CARD_FLIP, player)))


def steps(answer):
    return [lambda s: PlayTrainer(0, card_in_hand(s, CARD_FLIP, 0)),
            lambda s: ResolveDecision(s.decision.player, s.decision.id, (0,)),
            lambda s: ResolveDecision(s.decision.player, s.decision.id, (answer,))]


def to_answer(state, player=0, position=0):
    state = resolve(play(state, player), (position,))
    assert state.decision.kind == QUIZ_ANSWER
    return state


def both_outcomes(test, waiting, prize_card, user=0, *, observe=True):
    """答えを待つ状態から、3 つの答えのそれぞれで原文どおりに終わるか: おもてにする（そのまま）→ 正解なら使ったプレイヤーが 2 枚（引けるだけ。山札 0 枚なら 0 枚のログ）引く。
    正解でないなら引かない。``observe`` が偽なら観測の検査をしない（テスト専用の改変の盤面は、ログからおもての印を組み立てられない）。"""
    position = waiting.decision.context_value("position")
    uid = waiting.players[1 - user].prizes[position]
    test.assertEqual(waiting.cards[uid].card_id, prize_card)
    right = HIDDEN_PRIZES[prize_card]
    size = len(waiting.players[user].deck)
    for answer in range(3):
        done = resolve(waiting, (answer,))
        events = done.log[len(waiting.log):]
        draws = [(e["player"], len(e["cards"])) for e in events if e["kind"] == "draw"]
        test.assertEqual(draws, [(user, min(DRAW, size))] if answer == right else [])
        guess = next(e for e in events if e["kind"] == "prize_guess")
        test.assertEqual((guess["correct"], guess["position"]), (answer == right, position))
        test.assertIn(uid, done.face_up_prizes)  # おもてにしたサイドはそのまま
        test.assertEqual(done.players[1 - user].prizes[position], uid)
        test.assertEqual((done.decision, done.phase), (None, Phase.MAIN))
        test.assertEqual(check_invariants(done), [])
        if observe:
            test.assertEqual(observation_problems(done), [])


# ---------------------------------------------------------------- 1. 再現した漏れ（修正前に失敗し、修正後に通る）


class TwinRejectionTest(unittest.TestCase):
    """v0.135 の文書 11 章の報告（カードめくりゲームは正解の答えだけが FU3 で拒否された）を、合法な実カードの経路で作った盤面で比べる。v0.135 までは、だれの公開の情報も同じ
    3 つの状態で、同じ答えの受理・拒否が選んだサイドの種類で変わった。"""

    def test_same_public_view_same_outcome_for_every_answer(self):
        for mode, answer in itertools.product(MODES, range(3)):
            with self.subTest(mode=mode, answer=answer):
                states = twins(mode)
                for viewer in (0, 1, None):
                    self.assertTrue(all(public_view(s, viewer) == public_view(states[0], viewer) for s in states))
                self.assertEqual(twin_command_problems(states, steps(answer)), [])

    def test_stops_before_use_without_touching_the_state(self):
        """使ったプレイヤーの山札で、正解の引き方が止め方に当たる盤面では、使う前（手札から出す前・サイドを選ぶ前・答え・おもてにする前）に FU3。状態・乱数・ログは変わらない。"""
        for mode in STOPPING:
            with self.subTest(mode=mode):
                for state in twins(mode):
                    before = fingerprint(state)
                    for _ in range(3):  # くり返しても同じ（答えを試す段に進めない）
                        with self.assertRaises(UnsupportedError) as caught:
                            play(state)
                        self.assertEqual(caught.exception.code, FU3)
                        self.assertEqual(fingerprint(state), before)
                    self.assertIn(card_in_hand(state, CARD_FLIP, 0), state.players[0].hand)
                    self.assertFalse(state.face_up_prizes)

    def test_reason_does_not_depend_on_the_hidden_prize(self):
        for mode in STOPPING:
            with self.subTest(mode=mode):
                messages = set()
                for state in twins(mode):
                    with self.assertRaises(UnsupportedError) as caught:
                        play(state)
                    messages.add((type(caught.exception).__name__, caught.exception.code, caught.exception.message))
                self.assertEqual(len(messages), 1, messages)
                (_, _, message), = messages
                self.assertIn("プレイヤー 0 の山札", message)
                for prize in HIDDEN_PRIZES:
                    self.assertNotIn(prize, message)
                    self.assertNotIn(load_card_pool().get(prize).name_ja, message)

    def test_retrying_answers_cannot_find_the_kind(self):
        """安全な盤面で、答えの 3 つの値は、どのサイドの種類でもすべて受け付ける（拒否から種類を探せない）。止める盤面では答えの段まで進めない。"""
        for mode in SAFE:
            for prize in HIDDEN_PRIZES:
                with self.subTest(mode=mode, prize=prize):
                    waiting = to_answer(legal_marks(prize, mode))
                    outcomes = []
                    for answer in waiting.decision.options:
                        done = resolve(waiting, (answer,))
                        outcomes.append(done.decision is None)
                    self.assertEqual(outcomes, [True, True, True])

    def test_check_does_not_read_cards_hidden_from_the_user(self):
        """使ったプレイヤーにも見えないもの（自分の山札のうらの部分・相手のうらの山札・相手の手札・サイドの中身）だけが違う状態で、使う宣言の受理・拒否と理由が同じ。"""
        for mode in MODES:
            with self.subTest(mode=mode):
                pair = []
                for variant in (0, 1):
                    deck0 = list(ENERGIES) * 2
                    deck1 = list(reversed(ENERGIES)) * 2
                    if variant:
                        deck0[6:] = reversed(deck0[6:])
                        deck1[8:] = reversed(deck1[8:])
                    extra = (COMPUTER_SEARCH, BILL, OAK) if mode == "opponent_only" else ()
                    opponent_hand = (COMPUTER_SEARCH, BILL, OAK) if mode == "user_only" else (("PMCG1-071",), (BILL,))[variant]
                    prizes1 = [list(HIDDEN_PRIZES)[variant]] + [FILLER_PRIZE] * 5
                    state = board((FLASH, CARD_FLIP, *extra), None, deck0=deck0, deck1=deck1, opponent_hand=opponent_hand, prizes1=prizes1)
                    if mode != "none":
                        state = play_flash(state)
                    if mode == "user_only":
                        state = end_turns(computer_search_shuffle(end_turns(state, 1), 1), 1)
                    elif mode == "opponent_only":
                        state = computer_search_shuffle(state, 0)
                    elif mode in ("second", "top_only"):
                        state = end_turns(state, {"second": 6, "top_only": 8}[mode])
                    pair.append(state)
                self.assertNotEqual(fingerprint(pair[0])[0], fingerprint(pair[1])[0])
                self.assertEqual(twin_command_problems(pair, [lambda s: PlayTrainer(0, card_in_hand(s, CARD_FLIP, 0))], viewers=(0,)), [])


# ---------------------------------------------------------------- 2. 受け付ける場面を保つ（合法な経路）


class LegalPathTest(unittest.TestCase):
    def test_safe_marks_complete_all_answers(self):
        """おもてのカードがない・相手の山札だけ・いちばん上だけがおもて: 使うことを受け付け、正解・正解でないのどちらも原文どおりに終わる。"""
        for mode, prize in itertools.product(SAFE, HIDDEN_PRIZES):
            with self.subTest(mode=mode, prize=prize):
                state = legal_marks(prize, mode)
                selecting = play(state)
                self.assertEqual((selecting.decision.kind, selecting.decision.player), (SELECT_OPPONENT_PRIZE, 0))
                waiting = resolve(selecting, (0,))
                self.assertEqual((waiting.decision.kind, waiting.decision.player), (QUIZ_ANSWER, 0))
                self.assertEqual(observation_problems(waiting), [])
                self.assertEqual(serialization_problems(waiting), [])
                both_outcomes(self, waiting, prize)
                if mode == "top_only":
                    done = resolve(waiting, (HIDDEN_PRIZES[prize],))
                    self.assertEqual(FU.face_up_in_deck(done, 0), ())  # いちばん上のおもてのカードは引いた（見えていたカード）
                    self.assertEqual(FU.face_up_count(done, 1), 1)  # 相手の山札はそのまま

    def test_short_decks_draw_what_they_can(self):
        """合法な経路: 山札 5 枚ずつでフラッシュ（5 枚すべておもて）、番の最初のドローで減らす。山札が 1 枚（おもて 1 枚）・0 枚なら受け付け、引けるだけ引く。2 枚以上がおもてなら止める。"""
        for prize in HIDDEN_PRIZES:
            base = play_flash(board((FLASH, CARD_FLIP), prize, deck0=ENERGIES[:5], deck1=ENERGIES[:5]))
            for rounds in range(6):
                with self.subTest(prize=prize, rounds=rounds):
                    state = end_turns(base, 2 * rounds)
                    size = len(state.players[0].deck)
                    self.assertEqual((size, FU.face_up_count(state, 0)), (5 - rounds, 5 - rounds))
                    if min(DRAW, size) >= 2:
                        before = fingerprint(state)
                        with self.assertRaises(UnsupportedError) as caught:
                            play(state)
                        self.assertEqual(caught.exception.code, FU3)
                        self.assertEqual(fingerprint(state), before)
                    else:
                        both_outcomes(self, to_answer(state), prize)

    def test_without_face_up_any_deck_size(self):
        for prize, size in itertools.product(HIDDEN_PRIZES, (0, 1, 2, 3)):
            with self.subTest(prize=prize, size=size):
                both_outcomes(self, to_answer(board((CARD_FLIP,), prize, deck0=ENERGIES[:size], deck1=())), prize)

    def test_target_condition_comes_first(self):
        """うらの相手のサイドがなければ、おもての山札の止め方より先に FC1（カード固有の使う条件。情報漏れの対策のエラーに置きかえない）。"""
        state = play_flash(board((FLASH, CARD_FLIP), None, prizes1=[FILLER_PRIZE]))
        self.assertGreaterEqual(FU.face_up_count(state, 0), 2)
        state.face_up_prizes = (state.players[1].prizes[0],)  # テスト専用: 相手のサイド 1 枚がおもて（ほかの経路で作った前提）
        before = fingerprint(state)
        with self.assertRaises(UnsupportedError) as caught:
            play(state)
        self.assertEqual(caught.exception.code, FC1)
        self.assertEqual(fingerprint(state), before)

    def test_only_face_down_prizes_are_offered(self):
        """選べるのはうらの相手のサイドの位置だけ（おもてにしたサイドは選べない）。2 回目のカードめくりゲームは残りのうらのサイドから選ぶ。"""
        state = board((CARD_FLIP, CARD_FLIP), "PMCG1-058")
        done = resolve(to_answer(state), (0,))
        selecting = play(done)
        self.assertEqual(selecting.decision.options, (1, 2, 3, 4, 5))
        with self.assertRaises(IllegalActionError) as caught:
            resolve(selecting, (0,))
        self.assertEqual(caught.exception.code, "INVALID_CHOICE")


# ---------------------------------------------------------------- 3. 山札の枚数とおもての印の組み合わせ（テスト専用の改変）


def shaped(sizes, marks, prize="PMCG1-058"):
    """テスト専用の改変（合法な経路ではない）: フラッシュを使った盤面から、それぞれの山札を上から ``sizes`` 枚だけ残し（残りはトラッシュへ移す）、おもての印を上から ``marks`` 枚に
    する。カードの数・印の並び（上から続く）の不変条件は保つ。組み合わせを網羅するためだけに使う。"""
    state = play_flash(board((FLASH, CARD_FLIP), prize))
    for owner in (0, 1):
        p = state.players[owner]
        p.discard.extend(p.deck[sizes[owner]:])
        del p.deck[sizes[owner]:]
    state.face_up_deck = tuple(uid for owner in (0, 1) for uid in state.players[owner].deck[:marks[owner]])
    assert check_invariants(state) == [], check_invariants(state)
    return state


def expected_stop(sizes, marks, user=0):
    """テストが独立に持つ予想: 引くのは使ったプレイヤーだけ（正解のとき）。その山札で、引く枚数（引けるだけ）が 2 枚以上で、おもてのカードが 2 枚以上なら止める。相手の山札はみない。"""
    return min(DRAW, sizes[user]) >= 2 and marks[user] >= 2


def cases():
    found = []
    for size in (0, 1, 2, 3, 6):
        for mark in sorted({0, 1, 2, min(size, 5)}):
            if mark <= size:
                found += [((size, 6), (mark, 0)), ((6, size), (0, mark)), ((size, size), (mark, mark)), ((size, 6), (mark, 5)), ((6, size), (5, mark))]
    return found


class ShapeMatrixTest(unittest.TestCase):
    def test_sizes_and_marks(self):
        for case_sizes, case_marks in cases():
            with self.subTest(sizes=case_sizes, marks=case_marks):
                state = shaped(case_sizes, case_marks)
                if expected_stop(case_sizes, case_marks):
                    before = fingerprint(state)
                    with self.assertRaises(UnsupportedError) as caught:
                        play(state)
                    self.assertEqual(caught.exception.code, FU3)
                    self.assertEqual(fingerprint(state), before)
                else:
                    both_outcomes(self, to_answer(state), "PMCG1-058", observe=False)

    def test_the_check_reads_only_public_counts(self):
        """事前の確かめは、使ったプレイヤーの山札の枚数・おもての枚数（公開）と引く枚数だけで決まる。どちらのプレイヤーが使っても、そのプレイヤーの山札で決まり、理由の文の番号は
        使ったプレイヤー（サイドで変わらない）。試しても状態・乱数・ログは変わらない。"""
        effect = E.DEFAULT_EFFECTS.trainer_entry(CARD_FLIP).effect
        for case_sizes, case_marks in cases():
            for prize in HIDDEN_PRIZES:
                with self.subTest(sizes=case_sizes, marks=case_marks, prize=prize):
                    state = shaped(case_sizes, case_marks, prize)
                    uid = card_in_hand(state, CARD_FLIP, 0)
                    before = fingerprint(state)
                    for user in (0, 1):
                        found = effect.face_up_draw_stop(state, TrainerUse(user, uid, CARD_FLIP))
                        self.assertEqual(found is not None, expected_stop(case_sizes, case_marks, user))
                        if found is not None:
                            self.assertEqual(found[0], FU3)
                            self.assertIn(f"プレイヤー {user} の山札", found[1])
                    self.assertEqual(fingerprint(state), before)


class SharedCheckTest(unittest.TestCase):
    """v0.135 の共通の確かめに ``outcomes`` を加えた。既定（ほかのクイズ 4 種類）は v0.135 と同じ（正解・正解でないで、使ったプレイヤー・相手がそれぞれ ``draw`` 枚）。"""

    def test_default_outcomes_are_unchanged(self):
        for case_sizes, case_marks in cases():
            state = shaped(case_sizes, case_marks)
            for user, draw in itertools.product((0, 1), (2, 3)):
                with self.subTest(sizes=case_sizes, marks=case_marks, user=user, draw=draw):
                    self.assertEqual(E.quiz_draw_outcome_stop(state, user, draw), E.quiz_draw_outcome_stop(state, user, draw, outcomes=((user, draw), (1 - user, draw))))

    def test_zero_count_outcome_is_not_tried(self):
        state = shaped((6, 6), (5, 5))
        before = fingerprint(state)
        self.assertIsNone(E.quiz_draw_outcome_stop(state, 0, DRAW, outcomes=((0, 0), (1, 0))))
        self.assertEqual(E.quiz_draw_outcome_stop(state, 0, DRAW, outcomes=((0, 0), (1, DRAW)))[0], FU3)
        self.assertEqual(fingerprint(state), before)

    def test_other_quizzes_still_use_both_players(self):
        for quiz in (*QUIZZES, "GD5-016"):
            effect = E.DEFAULT_EFFECTS.trainer_entry(quiz).effect
            with self.subTest(quiz=quiz):
                state = shaped((6, 6), (0, 5))  # 相手の山札だけおもて: 正解で相手が引くクイズは止める（カードめくりゲームは止めない）
                self.assertEqual(effect.face_up_draw_stop(state, TrainerUse(0, card_in_hand(state, CARD_FLIP, 0), quiz))[0], FU3)
        self.assertIsNone(E.DEFAULT_EFFECTS.trainer_entry(CARD_FLIP).effect.face_up_draw_stop(state, TrainerUse(0, card_in_hand(state, CARD_FLIP, 0), CARD_FLIP)))


# ---------------------------------------------------------------- 4. 無効な選択・答え、保存と復元


class DecisionAndPersistenceTest(unittest.TestCase):
    def test_invalid_choices_are_rejected_the_same_way(self):
        for mode in SAFE:
            with self.subTest(mode=mode):
                states = twins(mode)
                bad_position = [steps(0)[0], lambda s: ResolveDecision(s.decision.player, s.decision.id, (6,))]
                bad_answer = steps(0)[:2] + [lambda s: ResolveDecision(s.decision.player, s.decision.id, (3,))]
                wrong_player = steps(0)[:2] + [lambda s: ResolveDecision(1, s.decision.id, (0,))]
                for sequence in (bad_position, bad_answer, wrong_player):
                    self.assertEqual(twin_command_problems(states, sequence), [])
                waiting = to_answer(states[0])
                before = fingerprint(waiting)
                for command in (ResolveDecision(0, waiting.decision.id, (3,)), ResolveDecision(0, waiting.decision.id, ()), ResolveDecision(1, waiting.decision.id, (0,))):
                    with self.assertRaises(IllegalActionError):
                        apply_command(waiting, command)
                    self.assertEqual(fingerprint(waiting), before)

    def test_save_and_restore(self):
        for prize in HIDDEN_PRIZES:
            with self.subTest(prize=prize):
                waiting = to_answer(legal_marks(prize, "top_only"))
                for restored in (pickle.loads(pickle.dumps(waiting)), copy.deepcopy(waiting), waiting.clone()):
                    self.assertEqual(fingerprint(restored)[:4], fingerprint(waiting)[:4])
                    self.assertEqual(check_invariants(restored), [])
                    for answer in range(3):
                        self.assertEqual(fingerprint(resolve(restored, (answer,)))[:3], fingerprint(resolve(waiting, (answer,)))[:3])
                self.assertEqual(serialization_problems(waiting), [])
                stopping = legal_marks(prize, "both")
                for restored in (pickle.loads(pickle.dumps(stopping)), copy.deepcopy(stopping), stopping.clone()):
                    with self.assertRaises(UnsupportedError) as caught:
                        play(restored)
                    self.assertEqual(caught.exception.code, FU3)


# ---------------------------------------------------------------- 5. 錯乱ジム・［ちえくらべ］


def chaos_board(prize, mode):
    """フラッシュなどで印を作ったあとに錯乱ジムを出す（合法な経路。スタジアムはコインを投げない）。"""
    extra = (COMPUTER_SEARCH, BILL, OAK) if mode == "opponent_only" else ()
    opponent_hand = (COMPUTER_SEARCH, BILL, OAK) if mode == "user_only" else ()
    state = play_flash(board((FLASH, CHAOS_GYM, CARD_FLIP, *extra), prize, opponent_hand=opponent_hand))
    if mode == "user_only":
        state = end_turns(computer_search_shuffle(end_turns(state, 1), 1), 1)
    elif mode == "opponent_only":
        state = computer_search_shuffle(state, 0)
    elif mode == "top_only":
        state = end_turns(state, 8)
    return apply_command(state, PlayTrainer(0, card_in_hand(state, CHAOS_GYM)))


class ChaosGymTest(unittest.TestCase):
    def test_stops_before_the_chaos_coin(self):
        for prize in HIDDEN_PRIZES:
            with self.subTest(prize=prize):
                state = chaos_board(prize, "user_only")
                before = fingerprint(state)
                with self.assertRaises(UnsupportedError) as caught:
                    play(state)
                self.assertEqual(caught.exception.code, FU3)
                self.assertEqual(fingerprint(state), before)  # コインを投げない

    def test_borrowing_checks_the_borrower_deck_independently_of_the_prize(self):
        """錯乱ジムの「うら」で相手が借りて使う: 確かめるのは借りたプレイヤー（そのプレイヤーが選び・答え・正解なら引く）の山札。借りたプレイヤーの山札の 2 枚目がおもてなら、借りる
        答えは既存の借りる確かめ（v0.132 ``borrow_unusable_reason``）で拒否され、サイドの種類によらない（新しい順序を決めない。既存の動きを確かめるだけ）。"""
        for mode in ("opponent_only", "top_only"):
            with self.subTest(mode=mode):
                states = [with_coin_results(chaos_board(prize, mode), T) for prize in HIDDEN_PRIZES]
                borrow = [lambda s: PlayTrainer(0, card_in_hand(s, CARD_FLIP, 0)), lambda s: ResolveDecision(s.decision.player, s.decision.id, (1,)),
                          lambda s: ResolveDecision(s.decision.player, s.decision.id, (0,)), lambda s: ResolveDecision(s.decision.player, s.decision.id, (0,))]
                self.assertEqual(twin_command_problems(states, borrow), [])
                offered = play(states[0])
                self.assertEqual(offered.decision.player, 1)
                if mode == "opponent_only":
                    with self.assertRaises(UnsupportedError) as caught:
                        resolve(offered, (1,))
                    self.assertEqual((caught.exception.code, "プレイヤー 1 の山札" in caught.exception.message), (FU3, True))
                    continue
                for prize, state in zip(HIDDEN_PRIZES, states):
                    selecting = resolve(play(state), (1,))
                    self.assertEqual((selecting.decision.kind, selecting.decision.player), (SELECT_OPPONENT_PRIZE, 1))
                    waiting = resolve(selecting, (0,))
                    self.assertEqual(waiting.card_def(waiting.players[0].prizes[0]).category, "energy")  # 借りたプレイヤーの相手（もとの使ったプレイヤー）のサイド（炎エネルギー）
                    size = len(waiting.players[1].deck)
                    for answer in range(3):
                        done = resolve(waiting, (answer,))
                        draws = [(e["player"], len(e["cards"])) for e in done.log[len(waiting.log):] if e["kind"] == "draw"]
                        self.assertEqual(draws, [(1, min(DRAW, size))] if answer == 2 else [])  # 草以外の基本エネルギー: 「エネルギーカード」が正解
                        self.assertEqual((done.decision, check_invariants(done)), (None, []))


class PsychicControlChoicesTest(unittest.TestCase):
    """ナツメのサイキックコントロール（v0.58。相手のトラッシュのトレーナーを使う）の選べるカードの確かめ（``effects.discard_trainer_use_choices``）: ``check_playable`` の止め方を「選ぶと止める」に
    する既存の扱いのまま。止めるかは使うプレイヤーの山札（公開）で決まり、相手のサイドの種類によらない。"""

    def test_stop_marks_do_not_depend_on_the_hidden_prize(self):
        """プレイヤー 0 が相手（プレイヤー 1）のトラッシュのカードめくりゲームを使う（選ぶのはプレイヤー 1 のうらのサイド。その位置 0 の種類だけが違う 3 つの状態）。"""
        for mode in ("both", "user_only", "opponent_only", "second", "top_only", "none"):
            with self.subTest(mode=mode):
                found = []
                for prize in HIDDEN_PRIZES:
                    state = legal_marks(prize, mode, hand=(), discard1=(CARD_FLIP,))
                    before = fingerprint(state)
                    flip = next(u for u in state.players[1].discard if state.cards[u].card_id == CARD_FLIP)
                    options, stops = E.discard_trainer_use_choices(state, 0)
                    self.assertEqual(fingerprint(state), before)
                    found.append((flip in options, tuple(s for s in stops if s[0] == flip)))
                self.assertTrue(all(f == found[0] for f in found), found)
                offered, stops = found[0]
                self.assertTrue(offered)
                self.assertEqual(bool(stops), mode in STOPPING)
                if stops:
                    self.assertEqual(stops[0][1], FU3)


class MindGamesTest(unittest.TestCase):
    """相手の［ちえくらべ］（ヤドキング neo1-049。v0.132 の利用者指定の規則「1. 状態を変えずに使えるかを確かめる → 2. 使うかを選ぶ」）。"""

    def board(self, prize):
        return board((FLASH, CARD_FLIP), prize, opponent_active={"card": SLOWKING, "energy": [PSYCHIC] * 3, "evolved_from": SLOWPOKE}, turn_number=7)

    def decline(self, state):
        self.assertEqual(state.decision.kind, REACTION_POWER)
        return apply_command(state, ResolveDecision(state.decision.player, state.decision.id, ()))

    def test_unusable_card_offers_no_reaction(self):
        for prize in HIDDEN_PRIZES:
            with self.subTest(prize=prize):
                start = self.board(prize)
                state = self.decline(apply_command(start, PlayTrainer(0, card_in_hand(start, FLASH))))
                while state.decision is not None:
                    state = resolve(state, state.decision.options)
                self.assertGreaterEqual(FU.face_up_count(state, 0), 2)
                before = fingerprint(state)
                with self.assertRaises(UnsupportedError) as caught:
                    play(state)
                self.assertEqual(caught.exception.code, FU3)
                self.assertEqual(fingerprint(state), before)

    def test_declined_reaction_continues_to_all_answers(self):
        for prize in HIDDEN_PRIZES:
            with self.subTest(prize=prize):
                state = self.decline(play(self.board(prize)))
                self.assertEqual(state.decision.kind, SELECT_OPPONENT_PRIZE)
                both_outcomes(self, resolve(state, (0,)), prize)


# ---------------------------------------------------------------- 6. サドン・デスの延長戦（v0.134）


class SuddenDeathSegmentTest(unittest.TestCase):
    def test_new_segment_ignores_the_previous_marks(self):
        """前の区間でフラッシュを使い（おもての印・ログ）、延長戦を始める。新しい区間の確かめは、今の区間の山札・おもての印（空から始まる）だけを見て、前の区間の記録（``segments`` の
        ログの ``flash_face_up``）を使わない。今の区間でフラッシュを使えば、今の区間の印で止める。"""
        from tests.test_sudden_death_v0_134 import (
            _until_main,
            constructed_sudden_death,
            with_decklists,
        )

        # 新しい区間の準備でたねポケモンは場に出る。カードめくりゲーム・フラッシュは手札に残る（v0.136 のエンジンで構成を調べて決めた。配り方が変わったらテストが知らせる）
        cards = [CARD_FLIP] * 4 + [GYARADOS] * 4 + [FLASH] * 2 + list(ENERGIES)
        state = build_test_state([{"active": "PMCG1-065", "hand": [FLASH, CARD_FLIP], "deck": list(cards), "prizes": 1},
                                  {"active": "PMCG1-065", "hand": [], "deck": list(cards), "prizes": 1}], current_player=0)
        state = play_flash(with_decklists(state))
        with self.assertRaises(UnsupportedError) as caught:
            play(state)
        self.assertEqual(caught.exception.code, FU3)
        fresh = next(_until_main(apply_command(constructed_sudden_death(state), StartSuddenDeath())))
        self.assertEqual(fresh.face_up_deck, ())
        self.assertTrue(any(e["kind"] == "flash_face_up" for e in fresh.segments[-1].log))
        self.assertFalse(any(e["kind"] == "flash_face_up" for e in fresh.log))
        player = fresh.current_player
        effect = E.DEFAULT_EFFECTS.trainer_entry(CARD_FLIP).effect
        hand = [fresh.cards[u].card_id for u in fresh.players[player].hand]
        self.assertTrue({CARD_FLIP, FLASH} <= set(hand), hand)
        self.assertTrue(all(len(p.deck) >= 5 for p in fresh.players))
        self.assertIsNone(effect.face_up_draw_stop(fresh, TrainerUse(player, card_in_hand(fresh, CARD_FLIP, player), CARD_FLIP)))
        selecting = play(fresh, player)  # 前の区間の印は見ない
        self.assertEqual(selecting.decision.kind, SELECT_OPPONENT_PRIZE)
        flashed = play_flash(fresh)
        self.assertEqual(len([e for e in flashed.log if e["kind"] == "flash_face_up"]), 2)
        before = fingerprint(flashed)
        with self.assertRaises(UnsupportedError) as caught:
            play(flashed, player)
        self.assertEqual(caught.exception.code, FU3)
        self.assertEqual(fingerprint(flashed), before)


# ---------------------------------------------------------------- 7. 対戦


class GamesTest(unittest.TestCase):
    def test_development_seed_runs_without_audit_failures(self):
        """開発用の seed 90 の v0.136 の組。監査の失敗・想定外の拒否・内部エラー・手数の上限がなく、正解・正解でない答えの両方が起こる。"""
        from tools import existing_effect_games as games

        results = games.run(range(90, 91), pairings=games.PAIRINGS_V0_136)
        totals = {}
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"), game.get("error"))
                for key, count in game.get("v136", {}).items():
                    totals[key] = totals.get(key, 0) + count
        for key in ("played", "correct", "wrong", "drawn"):
            self.assertGreater(totals.get(key, 0), 0, key)
        self.assertEqual(totals["played"], totals["correct"] + totals["wrong"])


# ---------------------------------------------------------------- 8. 文書


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = DOC.read_text(encoding="utf-8")
        for phrase in ("GAP-CARD-FLIP-REJECTION-ORACLE", "neo1-080", "quiz_draw_outcome_stop", "outcomes", "UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE",
                       "twin_command_problems", "使う前に止める", "情報漏れ", "da9d4e9e908b4d9729486ce3b508d5fda2d27ba4"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
