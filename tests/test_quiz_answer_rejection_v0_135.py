"""v0.135: カツラのクイズ その2（GD5-017）・その3（PMCG6-082）・ポケモン性格判定（neo4-105）の、答えの受理・拒否による情報漏れの修正（docs/quiz-answer-rejection-v0.135.md）。

おもてのカードのある山札（v0.126。フラッシュ）で、正解なら相手プレイヤー、正解でないなら使ったプレイヤーが引く。片方の引き方だけが既存の止め方（FU3）に当たると、v0.134 までは
同じ答えの受理・拒否が置いたカード（相手に見えない）で変わった（拒否は状態を変えないので、答えを試して正解を探せた）。v0.135 は、使う前に両方の引き方を確かめ、どちらかが止め方に
当たれば使う前に止める（その1 GD5-016 の v0.129 の確かめと共通の ``effects.quiz_draw_outcome_stop``）。

- 合法な実カードの経路（フラッシュ・パソコン通信・番の最初のドロー・錯乱ジム・［ちえくらべ］・サドン・デス）と、テスト専用の改変（山札の枚数・おもての印を直接決めた盤面。
  ``shaped``）を分けて書く。テスト専用の盤面は、山札の枚数と印の組み合わせを網羅するためだけに使う
- 比べる検査（``log_audit.twin_command_problems``）は、相手の公開の情報が同じで、見えない情報だけが違う 2 つの状態に、同じ操作を送る
"""

from __future__ import annotations

import copy
import itertools
import pathlib
import pickle
import unittest

from kyuura_engine import (
    EndTurn,
    IllegalActionError,
    Phase,
    PlayTrainer,
    ResolveDecision,
    StartSuddenDeath,
    UnsupportedError,
    apply_command,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine import faceup as FU
from kyuura_engine import heights as HT
from kyuura_engine.cards import load_card_pool
from kyuura_engine.decisions import (
    QUIZ_ANSWER,
    QUIZ_ATTACK,
    QUIZ_CARD,
    QUIZ_HEIGHT_ANSWER,
    REACTION_POWER,
)
from kyuura_engine.effects import TrainerUse
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests.helpers import CHAOS_GYM, HITMONCHAN, T, build_test_state, with_coin_results
from tests.log_audit import (
    observation_problems,
    public_view,
    serialization_problems,
    twin_command_problems,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "quiz-answer-rejection-v0.135.md"
LATEST = max(FORMAT_VERSIONS)

QUIZ1, QUIZ2, QUIZ3, PERSONALITY = "GD5-016", "GD5-017", "PMCG6-082", "neo4-105"
FLASH, COMPUTER_SEARCH, BILL, OAK = "ES2-035", "PMCG1-090", "PMCG1-074", "PMCG1-077"
DRATINI, DROWZEE = "PMCG1-065", "PMCG1-045"  # ミニリュウ（はたく）・スリープ（はたく・あやしいひかり）。どちらも 1 つ目のワザが「はたく」
HITMONCHAN_P, POTION = "PMCG1-058", "PMCG1-071"  # その2: ポケモン・トレーナーカード
DARK_GYARADOS, GYARADOS = "PMCG4-025", "PMCG1-034"  # 性格判定: 「わるい」の進化カード・それ以外の進化カード
SLOWKING, SLOWPOKE, PSYCHIC = "neo1-049", "neo1-045", "PMCG1-101"
ENERGIES = ("PMCG1-097", "PMCG1-098", "PMCG1-099", "PMCG1-100", "PMCG1-101", "PMCG1-102")
FU3 = FU.FACE_UP_DECK_HIDDEN_TAKE_CODE

# クイズごとの (引く枚数, 見えない 2 つの置くカード, 答えの位置を決める関数)。答えは、相手プレイヤーが公開の情報（決定の候補の名前）から決める位置
QUIZZES = {
    QUIZ3: (3, (DRATINI, DROWZEE), lambda d: d.context_value("names").index("ミニリュウ")),
    QUIZ2: (2, (HITMONCHAN_P, POTION), lambda d: 0),  # 「ポケモン」
    PERSONALITY: (3, (DARK_GYARADOS, GYARADOS), lambda d: 0),  # 「わるい」ポケモン
}


def fingerprint(state):
    return repr(state_to_dict(state, format_version=LATEST)), state.rng.getstate(), tuple(dict(e) for e in state.log), state.face_up_deck, state.decision


def card_in_hand(state, card_id, player=None):
    player = state.current_player if player is None else player
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)


def resolve(state, choices):
    d = state.decision
    return apply_command(state, ResolveDecision(d.player, d.id, tuple(choices)))


def board(hand, *, deck0=None, deck1=None, opponent_hand=(), opponent_active=None, turn_number=3):
    """プレイヤー 0 の番。山札は基本エネルギー（既定 12 枚ずつ。並びはプレイヤーで逆）。"""
    deck0 = list(ENERGIES) * 2 if deck0 is None else list(deck0)
    deck1 = list(reversed(ENERGIES)) * 2 if deck1 is None else list(deck1)
    return build_test_state([{"active": HITMONCHAN, "hand": list(hand), "deck": deck0, "prizes": 6},
                             {"active": opponent_active or HITMONCHAN, "hand": list(opponent_hand), "deck": deck1, "prizes": 6}],
                            current_player=0, turn_number=turn_number)


def play_flash(state):
    """合法な経路: フラッシュを使う（相手 → 自分の順に、上から 5 枚をそのままの順でおもてにする）。"""
    state = apply_command(state, PlayTrainer(state.current_player, card_in_hand(state, FLASH)))
    state = resolve(state, state.decision.options)
    return resolve(state, state.decision.options)


def computer_search_shuffle(state, player):
    """合法な経路: ``player`` の番に、パソコン通信（手札のマサキ・オーキドはかせをトラッシュ）で、おもてでないカードを手札に加えて山札を切る（その山札のおもての印は消える）。"""
    state = apply_command(state, PlayTrainer(player, card_in_hand(state, COMPUTER_SEARCH, player)))
    state = resolve(state, tuple(uid for uid in state.decision.options if state.cards[uid].card_id in (BILL, OAK)))
    return resolve(state, (next(uid for uid in state.decision.options if uid not in state.face_up_deck),))


def end_turns(state, count):
    for _ in range(count):
        state = apply_command(state, EndTurn(state.current_player))
    return state


def legal_marks(quiz, hidden, mode):
    """合法な実カードの経路で作った、おもてのカードのある山札の盤面（プレイヤー 0 の番。手札にクイズと ``hidden``）。

    - ``both``: フラッシュの直後（両方の山札の上から 5 枚がおもて）
    - ``user_only``: フラッシュ → 番の終わり → 相手が自分の番にパソコン通信で山札を切る → 番の終わり（使ったプレイヤーの山札だけ、上から 4 枚がおもて）
    - ``opponent_only``: フラッシュ → 同じ番にパソコン通信で自分の山札を切る（相手の山札だけ、上から 5 枚がおもて）
    - ``second``: フラッシュ → 番の終わりを 6 回（両方とも上から 2 枚がおもて。2 枚目にもおもてのカード）
    - ``top_only``: フラッシュ → 番の終わりを 8 回（両方とも、いちばん上の 1 枚だけがおもて）
    - ``none``: フラッシュを使わない
    """
    extra = (COMPUTER_SEARCH, BILL, OAK) if mode == "opponent_only" else ()
    opponent_hand = (COMPUTER_SEARCH, BILL, OAK) if mode == "user_only" else ()
    state = board((FLASH, quiz, hidden, *extra), opponent_hand=opponent_hand)
    if mode == "none":
        return state
    state = play_flash(state)
    if mode == "user_only":
        state = end_turns(state, 1)
        state = computer_search_shuffle(state, 1)
        state = end_turns(state, 1)
    elif mode == "opponent_only":
        state = computer_search_shuffle(state, 0)
    elif mode == "second":
        state = end_turns(state, 6)
    elif mode == "top_only":
        state = end_turns(state, 8)
    assert state.current_player == 0 and state.decision is None and check_invariants(state) == [], check_invariants(state)
    return state


def quiz_steps(quiz):
    """クイズを使い、見えない 2 つのカードのどちらか（twin では同じ uid で、カードだけが違う。送るコマンドは同じ）を置き、（その3 は 1 つ目のワザを伝え）、答える操作の並び。"""
    _, _, answer_of = QUIZZES[quiz]
    pair = QUIZZES[quiz][1]
    steps = [lambda s: PlayTrainer(0, card_in_hand(s, quiz, 0)),
             lambda s: ResolveDecision(s.decision.player, s.decision.id, (next(u for u in s.players[0].hand if s.cards[u].card_id in pair),))]
    if quiz == QUIZ3:
        steps.append(lambda s: ResolveDecision(s.decision.player, s.decision.id, (0,)))
    steps.append(lambda s: ResolveDecision(s.decision.player, s.decision.id, (answer_of(s.decision),)))
    return steps


def twins(quiz, mode):
    """相手（プレイヤー 1）と観戦者の公開の情報が同じで、置くカード（手札の同じ位置・同じ uid のカード）だけが違う 2 つの状態。"""
    return [legal_marks(quiz, hidden, mode) for hidden in QUIZZES[quiz][1]]


def correct_index(state, quiz):
    """置いたカードの正解の位置（テストが独立に持つ: その3 は名前、その2 はカードの分類、性格判定は名前の始まり）。"""
    d = state.decision
    card = d.context_value("quiz_card")
    definition = state.card_def(card)
    if quiz == QUIZ3:
        return d.context_value("names").index(definition.name_ja)
    if quiz == QUIZ2:
        return {"pokemon": 0, "energy": 1, "trainer": 2}[definition.category]
    return 0 if definition.name_ja.startswith("わるい") else 1 if definition.name_ja.startswith("やさしい") else 2


def to_answer(state, quiz, hidden):
    """クイズを使い、``hidden`` を置き（その3 はワザを伝え）、相手の答えを待つ状態。"""
    state = apply_command(state, PlayTrainer(0, card_in_hand(state, quiz, 0)))
    state = resolve(state, (card_in_hand(state, hidden, 0),))
    if quiz == QUIZ3:
        state = resolve(state, (0,))
    if quiz == QUIZ1:
        assert state.decision.kind == QUIZ_HEIGHT_ANSWER
    else:
        assert state.decision.kind == QUIZ_ANSWER
    return state


def both_outcomes(test, state, quiz, hidden, draw):
    """答えを待つ状態から、正解・正解でないの両方が、引く（引けるだけ）→ 置いたカードを手札にもどす まで進むか。"""
    decks = [len(p.deck) for p in state.players]
    if quiz == QUIZ1:
        height = HT.card_height(state.card_def(state.decision.context_value("quiz_card")))[0].height_cm
        answers = {True: height, False: height + 1}
    else:
        right = correct_index(state, quiz)
        answers = {True: right, False: (right + 1) % len(state.decision.options)}
    for correct, value in answers.items():
        done = resolve(state, (value,))
        drawer = 1 if correct else 0
        draws = [e for e in done.log[len(state.log):] if e["kind"] == "draw"]
        test.assertEqual([(e["player"], len(e["cards"])) for e in draws], [(drawer, min(draw, decks[drawer]))])
        test.assertEqual(len(done.players[drawer].deck), decks[drawer] - min(draw, decks[drawer]))
        test.assertEqual((done.decision, done.phase, done.set_aside), (None, Phase.MAIN, ()))
        test.assertIn(state.decision.context_value("quiz_card"), done.players[0].hand)  # 置いたカードは手札にもどる
        test.assertEqual(done.cards[state.decision.context_value("quiz_card")].card_id, hidden)
        test.assertEqual(check_invariants(done), [])
        reveal = next(e for e in done.log if e["kind"] in ("quiz_reveal", "quiz_kind_reveal", "quiz_height_reveal"))
        test.assertEqual(reveal["correct"], correct)


# ---------------------------------------------------------------- 1. 再現した漏れ（修正前に失敗し、修正後に通る）


class TwinRejectionTest(unittest.TestCase):
    """棚卸し（GAP-QUIZ3/QUIZ2/PERSONALITY-REJECTION-ORACLE）の再現を、合法な実カードの経路で作った盤面で比べる。v0.134 までは、相手の公開の情報が同じ 2 つの状態で、同じ答えの
    受理・拒否が置いたカードで逆になった（``twin_command_problems`` が「段 N: 受理・拒否・理由が状態によって違う」を返した）。"""

    def test_same_public_view_same_outcome(self):
        for quiz, mode in itertools.product(QUIZZES, ("both", "user_only", "opponent_only", "second")):
            with self.subTest(quiz=quiz, mode=mode):
                pair = twins(quiz, mode)
                for viewer in (1, None):
                    self.assertEqual(public_view(pair[0], viewer), public_view(pair[1], viewer))
                self.assertEqual(twin_command_problems(pair, quiz_steps(quiz), viewers=(1, None)), [])

    def test_stops_before_use_without_touching_the_state(self):
        """片方の引き方でもおもての山札の止め方に当たる盤面では、使う前（手札から出す前・置くカードを選ぶ前・ヒント・答え・公開の前）に FU3 で止める。状態・乱数・ログは変わらない。"""
        for quiz, mode in itertools.product(QUIZZES, ("both", "user_only", "opponent_only", "second")):
            with self.subTest(quiz=quiz, mode=mode):
                for state in twins(quiz, mode):
                    before = fingerprint(state)
                    for _ in range(3):  # くり返しても同じ（答えを試す段に進めない）
                        with self.assertRaises(UnsupportedError) as caught:
                            apply_command(state, PlayTrainer(0, card_in_hand(state, quiz, 0)))
                        self.assertEqual(caught.exception.code, FU3)
                        self.assertEqual(fingerprint(state), before)
                    self.assertIn(card_in_hand(state, quiz, 0), state.players[0].hand)

    def test_reason_does_not_depend_on_the_hidden_card(self):
        for quiz, mode in itertools.product(QUIZZES, ("both", "user_only", "opponent_only", "second")):
            with self.subTest(quiz=quiz, mode=mode):
                messages = set()
                for state in twins(quiz, mode):
                    with self.assertRaises(UnsupportedError) as caught:
                        apply_command(state, PlayTrainer(0, card_in_hand(state, quiz, 0)))
                    messages.add((caught.exception.code, caught.exception.message))
                self.assertEqual(len(messages), 1, messages)
                (_, message), = messages
                for hidden in QUIZZES[quiz][1]:
                    self.assertNotIn(hidden, message)
                    self.assertNotIn(load_card_pool().get(hidden).name_ja, message)

    def test_reason_does_not_depend_on_cards_hidden_from_the_user(self):
        """使ったプレイヤー（プレイヤー 0）にも見えないカード（自分のうらの山札・相手の 2 枚目より下のおもてのカード・相手の手札）だけが違う 2 つの状態で、使う宣言の受理・拒否と理由が
        同じ（事前の確かめが、引くカードの中身を使わない）。"""
        opponent_draws = {"both": 0, "user_only": 1, "opponent_only": 0, "second": 3, "top_only": 4, "none": 0}
        for quiz, mode in itertools.product(QUIZZES, opponent_draws):
            with self.subTest(quiz=quiz, mode=mode):
                hidden = QUIZZES[quiz][1][0]
                pair = []
                for variant in (0, 1):
                    deck0 = list(ENERGIES) * 2
                    deck1 = list(reversed(ENERGIES)) * 2
                    if variant:
                        deck0[6:] = reversed(deck0[6:])  # 自分の山札の 7 枚目より下（うら。番の最初のドローでも届かない）
                        k = opponent_draws[mode] + 1  # 相手の山札の、いちばん上より下で、まだいちばん上として見えたことのない 2 枚
                        deck1[k], deck1[k + 1] = deck1[k + 1], deck1[k]
                    extra = (COMPUTER_SEARCH, BILL, OAK) if mode == "opponent_only" else ()
                    opponent_hand = (COMPUTER_SEARCH, BILL, OAK) if mode == "user_only" else ((POTION,), (BILL,))[variant]
                    state = board((FLASH, quiz, hidden, *extra), deck0=deck0, deck1=deck1, opponent_hand=opponent_hand)
                    if mode != "none":
                        state = play_flash(state)
                    if mode == "user_only":
                        state = end_turns(computer_search_shuffle(end_turns(state, 1), 1), 1)
                    elif mode == "opponent_only":
                        state = computer_search_shuffle(state, 0)
                    elif mode in ("second", "top_only"):
                        state = end_turns(state, 2 * opponent_draws[mode])
                    pair.append(state)
                self.assertNotEqual(fingerprint(pair[0])[0], fingerprint(pair[1])[0])  # 見えない情報は違う
                self.assertEqual(twin_command_problems(pair, [lambda s, quiz=quiz: PlayTrainer(0, card_in_hand(s, quiz, 0))], viewers=(0,)), [])

    def test_exhaustive_answers_are_all_accepted_when_safe(self):
        """使うことを受け付けた盤面（いちばん上だけがおもて）では、答えのどの値も受け付ける（拒否から正解を探せない）。その3 は 513 の名前のすべて。"""
        for quiz in QUIZZES:
            with self.subTest(quiz=quiz):
                for hidden in QUIZZES[quiz][1]:
                    state = to_answer(legal_marks(quiz, hidden, "top_only"), quiz, hidden)
                    for value in state.decision.options:
                        done = resolve(state, (value,))
                        self.assertIsNone(done.decision)


# ---------------------------------------------------------------- 2. 受け付ける場面を保つ（合法な経路）


class LegalPathTest(unittest.TestCase):
    def test_no_face_up_and_top_only_are_accepted_with_both_outcomes(self):
        for quiz, mode in itertools.product(QUIZZES, ("none", "top_only")):
            draw = QUIZZES[quiz][0]
            for hidden in QUIZZES[quiz][1]:
                with self.subTest(quiz=quiz, mode=mode, hidden=hidden):
                    state = legal_marks(quiz, hidden, mode)
                    waiting = to_answer(state, quiz, hidden)
                    self.assertEqual(observation_problems(waiting), [])
                    self.assertEqual(serialization_problems(waiting), [])
                    both_outcomes(self, waiting, quiz, hidden, draw)
                    for correct in (True, False):
                        done = resolve(waiting, (correct_index(waiting, quiz) if correct else (correct_index(waiting, quiz) + 1) % len(waiting.decision.options),))
                        self.assertEqual(observation_problems(done), [])
                        self.assertEqual(serialization_problems(done), [])
                        if mode == "top_only":
                            drawer = 1 if correct else 0
                            self.assertEqual(FU.face_up_in_deck(done, drawer), ())  # いちばん上のおもてのカードは引いた（見えていたカード）

    def test_short_decks_draw_what_they_can(self):
        """合法な経路: 山札 5 枚ずつでフラッシュを使い（5 枚すべておもて）、番の最初のドローで減らす。おもてが 1 枚（いちばん上）なら受け付け、引けるだけ引く。2 枚以上なら使う前に止める。
        山札 0 枚（おもてのカードもない）も受け付け、0 枚引く（枚数の不足を新しい拒否の理由にしない）。"""
        for quiz, (draw, (hidden, _), _) in QUIZZES.items():
            base = play_flash(board((FLASH, quiz, hidden), deck0=ENERGIES[:5], deck1=ENERGIES[:5]))
            for rounds in range(6):
                with self.subTest(quiz=quiz, rounds=rounds):
                    state = end_turns(base, 2 * rounds)  # 両方が番の最初に rounds 枚ずつ引いた（いちばん上のおもてのカードを 1 枚ずつ）
                    size = len(state.players[0].deck)
                    self.assertEqual(size, 5 - rounds)
                    self.assertEqual(FU.face_up_count(state, 0), size)
                    if min(draw, size) >= 2:
                        before = fingerprint(state)
                        with self.assertRaises(UnsupportedError) as caught:
                            apply_command(state, PlayTrainer(0, card_in_hand(state, quiz, 0)))
                        self.assertEqual(caught.exception.code, FU3)
                        self.assertEqual(fingerprint(state), before)
                    else:
                        both_outcomes(self, to_answer(state, quiz, hidden), quiz, hidden, draw)

    def test_empty_decks_without_face_up(self):
        for quiz, (draw, (hidden, _), _) in QUIZZES.items():
            with self.subTest(quiz=quiz):
                both_outcomes(self, to_answer(board((quiz, hidden), deck0=(), deck1=()), quiz, hidden), quiz, hidden, draw)
                both_outcomes(self, to_answer(board((quiz, hidden), deck0=ENERGIES[:1], deck1=ENERGIES[:2]), quiz, hidden), quiz, hidden, draw)


# ---------------------------------------------------------------- 3. 山札の枚数とおもての印の組み合わせ（テスト専用の改変）


def shaped(quiz, hidden, sizes, marks):
    """テスト専用の改変（合法な経路ではない）: フラッシュを使った盤面から、それぞれの山札を上から ``sizes`` 枚だけ残し（残りはトラッシュへ移す）、おもての印を上から ``marks`` 枚に
    する。カードの数・印の並び（上から続く）の不変条件は保つ。組み合わせを網羅するためだけに使う。"""
    state = play_flash(board((FLASH, quiz, hidden)))
    for owner in (0, 1):
        p = state.players[owner]
        p.discard.extend(p.deck[sizes[owner]:])
        del p.deck[sizes[owner]:]
    state.face_up_deck = tuple(uid for owner in (0, 1) for uid in state.players[owner].deck[:marks[owner]])
    assert check_invariants(state) == [], check_invariants(state)
    return state


def expected_stop(draw, sizes, marks):
    """テストが独立に持つ予想: どちらかの山札で、引く枚数（引けるだけ）が 2 枚以上で、おもてのカードが 2 枚以上（上から続くので 2 枚目がおもて）なら止める。"""
    return any(min(draw, size) >= 2 and mark >= 2 for size, mark in zip(sizes, marks))


class ShapeMatrixTest(unittest.TestCase):
    def test_sizes_and_marks(self):
        sizes = (0, 1, 2, 3, 6)
        cases = []
        for size in sizes:
            for mark in sorted({0, 1, 2, min(size, 5)}):
                if mark <= size:
                    cases += [((size, 6), (mark, 0)), ((6, size), (0, mark)), ((size, size), (mark, mark))]
        for quiz in (*QUIZZES, QUIZ1):
            draw = QUIZZES[quiz][0] if quiz in QUIZZES else 2
            hidden = QUIZZES[quiz][1][0] if quiz in QUIZZES else DRATINI
            for case_sizes, case_marks in cases:
                with self.subTest(quiz=quiz, sizes=case_sizes, marks=case_marks):
                    state = shaped(quiz, hidden, case_sizes, case_marks)
                    if expected_stop(draw, case_sizes, case_marks):
                        before = fingerprint(state)
                        with self.assertRaises(UnsupportedError) as caught:
                            apply_command(state, PlayTrainer(0, card_in_hand(state, quiz, 0)))
                        self.assertEqual(caught.exception.code, FU3)
                        self.assertEqual(fingerprint(state), before)
                    else:
                        both_outcomes(self, to_answer(state, quiz, hidden), quiz, hidden, draw)

    def test_the_check_reads_only_public_counts(self):
        """事前の確かめの結果は、山札の枚数・おもての枚数（公開）と引く枚数だけで決まる（使ったプレイヤー・相手のどちらで確かめても同じ。錯乱ジムで借りたプレイヤーも同じ）。"""
        for quiz in (*QUIZZES, QUIZ1):
            effect = E.DEFAULT_EFFECTS.trainer_entry(quiz).effect
            hidden = QUIZZES[quiz][1][0] if quiz in QUIZZES else DRATINI
            for case_sizes in ((6, 6), (3, 1), (0, 6)):
                for case_marks in itertools.product(range(4), range(4)):
                    if case_marks[0] > case_sizes[0] or case_marks[1] > case_sizes[1]:
                        continue
                    with self.subTest(quiz=quiz, sizes=case_sizes, marks=case_marks):
                        state = shaped(quiz, hidden, case_sizes, case_marks)
                        uid = card_in_hand(state, quiz, 0)
                        before = fingerprint(state)
                        found = [effect.face_up_draw_stop(state, TrainerUse(user, uid, quiz)) for user in (0, 1)]
                        self.assertEqual(fingerprint(state), before)  # 試しても状態・乱数・ログは変わらない
                        self.assertEqual(found[0] is not None, expected_stop(effect.draw, case_sizes, case_marks))
                        self.assertEqual(found[0] is None, found[1] is None)
                        if found[0] is not None:
                            self.assertEqual(found[0][0], FU3)
                            self.assertEqual(found[0], E.quiz_draw_outcome_stop(state, 0, effect.draw))


# ---------------------------------------------------------------- 4. 無効な答え・保存と復元


class AnswerAndPersistenceTest(unittest.TestCase):
    def test_invalid_answer_is_rejected_the_same_way(self):
        for quiz in QUIZZES:
            with self.subTest(quiz=quiz):
                pair = twins(quiz, "top_only")
                steps = quiz_steps(quiz)[:-1] + [lambda s: ResolveDecision(s.decision.player, s.decision.id, (len(s.decision.options),))]
                self.assertEqual(twin_command_problems(pair, steps, viewers=(1, None)), [])
                state = to_answer(pair[0], quiz, QUIZZES[quiz][1][0])
                before = fingerprint(state)
                with self.assertRaises(IllegalActionError) as caught:
                    resolve(state, (len(state.decision.options),))
                self.assertEqual(caught.exception.code, "INVALID_CHOICE")
                self.assertEqual(fingerprint(state), before)

    def test_save_and_restore_while_waiting(self):
        for quiz in QUIZZES:
            with self.subTest(quiz=quiz):
                hidden = QUIZZES[quiz][1][0]
                state = to_answer(legal_marks(quiz, hidden, "top_only"), quiz, hidden)
                for restored in (pickle.loads(pickle.dumps(state)), copy.deepcopy(state), state.clone()):
                    self.assertEqual(state_to_dict(restored, format_version=LATEST), state_to_dict(state, format_version=LATEST))
                    self.assertEqual(check_invariants(restored), [])
                    for value in (0, len(state.decision.options) - 1):
                        self.assertEqual(state_to_dict(resolve(restored, (value,)), format_version=LATEST), state_to_dict(resolve(state, (value,)), format_version=LATEST))
                before = legal_marks(quiz, hidden, "both")
                for restored in (pickle.loads(pickle.dumps(before)), copy.deepcopy(before), before.clone()):
                    with self.assertRaises(UnsupportedError) as caught:
                        apply_command(restored, PlayTrainer(0, card_in_hand(restored, quiz, 0)))
                    self.assertEqual(caught.exception.code, FU3)


# ---------------------------------------------------------------- 5. 錯乱ジム・［ちえくらべ］


class ChaosGymTest(unittest.TestCase):
    def test_stops_before_the_chaos_coin(self):
        """場の錯乱ジム: おもての山札の止め方に当たるなら、手札から出す前（錯乱ジムのコインの前）に止める。コインを投げず、乱数は進まない。"""
        for quiz in QUIZZES:
            with self.subTest(quiz=quiz):
                hidden = QUIZZES[quiz][1][0]
                state = play_flash(board((FLASH, CHAOS_GYM, quiz, hidden)))
                state = apply_command(state, PlayTrainer(0, card_in_hand(state, CHAOS_GYM)))  # スタジアムはコインを投げない
                before = fingerprint(state)
                with self.assertRaises(UnsupportedError) as caught:
                    apply_command(state, PlayTrainer(0, card_in_hand(state, quiz, 0)))
                self.assertEqual(caught.exception.code, FU3)
                self.assertEqual(fingerprint(state), before)

    def test_borrowed_by_the_opponent_completes_both_outcomes(self):
        """錯乱ジムの「うら」で相手が借りて使う（合法な経路。いちばん上だけがおもての山札）: 確かめるのは使うプレイヤー（借りたプレイヤー）の手札・その両方の引き方。正解なら
        もとの使ったプレイヤー（借りたプレイヤーの相手）、正解でないなら借りたプレイヤーが引く。"""
        for quiz, (draw, (hidden, other), _) in QUIZZES.items():
            with self.subTest(quiz=quiz):
                state = board((FLASH, CHAOS_GYM, quiz, hidden), opponent_hand=(other,))
                state = play_flash(state)
                state = apply_command(state, PlayTrainer(0, card_in_hand(state, CHAOS_GYM)))
                state = end_turns(state, 8)
                self.assertEqual((FU.face_up_count(state, 0), FU.face_up_count(state, 1)), (1, 1))
                state = apply_command(with_coin_results(state, T), PlayTrainer(0, card_in_hand(state, quiz, 0)))
                state = resolve(state, (1,))  # 相手が借りて使う
                d = state.decision
                self.assertEqual((d.kind, d.player), (QUIZ_CARD, 1))
                state = resolve(state, (card_in_hand(state, other, 1),))
                if quiz == QUIZ3:
                    state = resolve(state, (0,))
                self.assertEqual((state.decision.kind, state.decision.player), (QUIZ_ANSWER, 0))
                decks = [len(p.deck) for p in state.players]
                right = correct_index(state, quiz)
                for correct, value in ((True, right), (False, (right + 1) % len(state.decision.options))):
                    done = resolve(state, (value,))
                    drawer = 0 if correct else 1
                    draws = [e for e in done.log[len(state.log):] if e["kind"] == "draw"]
                    self.assertEqual([(e["player"], len(e["cards"])) for e in draws], [(drawer, min(draw, decks[drawer]))])
                    self.assertIn(next(u for u in done.players[1].hand if done.cards[u].card_id == other), done.players[1].hand)
                    self.assertEqual((done.decision, check_invariants(done)), (None, []))

    def test_borrowing_check_matches_the_user_check(self):
        """借りたプレイヤーで確かめても、もとの使ったプレイヤーで確かめても同じ結果（引くのは正誤でどちらかのプレイヤー、引く枚数は同じ）。もとの使ったプレイヤーが使う前の確かめを
        通ったなら、錯乱ジムのコインのあいだに山札は変わらないので、借りるときに新しく止まらない。"""
        for quiz in QUIZZES:
            effect = E.DEFAULT_EFFECTS.trainer_entry(quiz).effect
            for mode in ("both", "user_only", "opponent_only", "second", "top_only", "none"):
                with self.subTest(quiz=quiz, mode=mode):
                    state = legal_marks(quiz, QUIZZES[quiz][1][0], mode)
                    uid = card_in_hand(state, quiz, 0)
                    found = [effect.face_up_draw_stop(state, TrainerUse(user, uid, quiz)) for user in (0, 1)]
                    self.assertEqual([None if f is None else f[0] for f in found], [None if found[0] is None else FU3] * 2)  # 理由の文は試す順のプレイヤーの番号だけが違う


class MindGamesTest(unittest.TestCase):
    """相手の［ちえくらべ］（ヤドキング neo1-049。v0.132 の利用者指定の規則「1. 状態を変えずに使えるかを確かめる（使えないカードの宣言には選択もコインもない）→ 2. 使うかを選ぶ」）。"""

    def board(self, quiz, hidden):
        return board((FLASH, quiz, hidden), opponent_active={"card": SLOWKING, "energy": [PSYCHIC] * 3, "evolved_from": SLOWPOKE}, turn_number=7)

    def decline(self, state):
        d = state.decision
        self.assertEqual(d.kind, REACTION_POWER)
        return apply_command(state, ResolveDecision(d.player, d.id, ()))

    def test_unusable_quiz_offers_no_reaction(self):
        for quiz in QUIZZES:
            with self.subTest(quiz=quiz):
                hidden = QUIZZES[quiz][1][0]
                start = self.board(quiz, hidden)
                state = self.decline(apply_command(start, PlayTrainer(0, card_in_hand(start, FLASH))))
                while state.decision is not None:  # フラッシュの並べ替え（相手 → 自分）
                    state = resolve(state, state.decision.options)
                self.assertTrue(FU.face_up_count(state, 0) >= 2)
                before = fingerprint(state)
                with self.assertRaises(UnsupportedError) as caught:
                    apply_command(state, PlayTrainer(0, card_in_hand(state, quiz, 0)))
                self.assertEqual(caught.exception.code, FU3)
                self.assertEqual(fingerprint(state), before)  # ［ちえくらべ］の決定もコインもない

    def test_declined_reaction_continues_to_both_outcomes(self):
        for quiz, (draw, (hidden, _), _) in QUIZZES.items():
            with self.subTest(quiz=quiz):
                start = self.board(quiz, hidden)
                state = self.decline(apply_command(start, PlayTrainer(0, card_in_hand(start, quiz, 0))))
                self.assertEqual(state.decision.kind, QUIZ_CARD)
                state = resolve(state, (card_in_hand(state, hidden, 0),))
                if quiz == QUIZ3:
                    self.assertEqual(state.decision.kind, QUIZ_ATTACK)
                    state = resolve(state, (0,))
                both_outcomes(self, state, quiz, hidden, draw)


# ---------------------------------------------------------------- 6. サドン・デスの延長戦（v0.134）


class SuddenDeathSegmentTest(unittest.TestCase):
    def test_new_segment_ignores_the_previous_marks(self):
        """前の区間でフラッシュを使い（おもての印・ログ）、サドン・デスの延長戦を始める。新しい区間の確かめは、今の区間の山札・おもての印（空から始まる）だけを見て、前の区間の記録
        （``segments`` のログの ``flash_face_up``）を使わない。"""
        from tests.test_sudden_death_v0_134 import (
            _until_main,
            constructed_sudden_death,
            with_decklists,
        )

        # 新しい区間の準備でたねポケモンは場に出るので、手札に残る出題の候補は 1 進化のギャラドス（ワザを持つ）。この構成で、新しい区間のプレイヤー 0 の手札にクイズ・ギャラドス・
        # フラッシュがあり、両方の山札が 5 枚以上になる（v0.135 のエンジンで構成を調べて決めた。配り方が変わったらテストが知らせる）
        cards = [QUIZ3] * 4 + [GYARADOS] * 4 + [FLASH] * 2 + list(ENERGIES[:2])
        state = build_test_state([{"active": DRATINI, "hand": [FLASH, QUIZ3, DRATINI], "deck": list(cards), "prizes": 1},
                                  {"active": DRATINI, "hand": [], "deck": list(cards), "prizes": 1}], current_player=0)
        state = with_decklists(state)
        state = play_flash(state)
        self.assertTrue(FU.face_up_count(state, 0) >= 2)
        with self.assertRaises(UnsupportedError) as caught:
            apply_command(state, PlayTrainer(0, card_in_hand(state, QUIZ3, 0)))
        self.assertEqual(caught.exception.code, FU3)
        ended = constructed_sudden_death(state)
        fresh = next(_until_main(apply_command(ended, StartSuddenDeath())))
        self.assertEqual(fresh.face_up_deck, ())
        self.assertTrue(any(e["kind"] == "flash_face_up" for e in fresh.segments[-1].log))
        self.assertFalse(any(e["kind"] == "flash_face_up" for e in fresh.log))
        for user in (0, 1):
            self.assertIsNone(E.quiz_draw_outcome_stop(fresh, user, 3))
        player = fresh.current_player
        hand = [fresh.cards[u].card_id for u in fresh.players[player].hand]
        self.assertTrue({QUIZ3, GYARADOS, FLASH} <= set(hand), hand)
        self.assertTrue(all(len(p.deck) >= 5 for p in fresh.players))
        waiting = apply_command(fresh, PlayTrainer(player, card_in_hand(fresh, QUIZ3, player)))  # 前の区間の印は見ない
        self.assertEqual(waiting.decision.kind, QUIZ_CARD)
        flashed = play_flash(fresh)  # 今の区間でフラッシュを使えば、今の区間の印で止める
        self.assertEqual(len([e for e in flashed.log if e["kind"] == "flash_face_up"]), 2)
        before = fingerprint(flashed)
        with self.assertRaises(UnsupportedError) as caught:
            apply_command(flashed, PlayTrainer(player, card_in_hand(flashed, QUIZ3, player)))
        self.assertEqual(caught.exception.code, FU3)
        self.assertEqual(fingerprint(flashed), before)


# ---------------------------------------------------------------- 7. 対戦


class GamesTest(unittest.TestCase):
    def test_development_seed_runs_without_audit_failures(self):
        """開発用の seed 90 の v0.135 の組（Q135 どうし・対 F126・対 S80）。監査の失敗・想定外の拒否・内部エラー・手数の上限がなく、クイズの正解と正解でない答えの両方・おもての
        カードのある山札での使用・使う前の FU3 の停止が起こる。"""
        from tools import existing_effect_games as games

        results = games.run(range(90, 91), pairings=games.PAIRINGS_V0_135)
        totals, stops = {}, 0
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"), game.get("error"))
                for key, count in game.get("v135", {}).items():
                    totals[key] = totals.get(key, 0) + count
                stops += sum(c for k, c in game.get("policy", {}).items() if k.endswith(f"_not_playable_{FU3}") and any(q in k for q in QUIZZES))
        for key in ("correct", "wrong", "drawn_by_answerer", "drawn_by_user", "returned"):
            self.assertGreater(totals.get(key, 0), 0, key)
        self.assertGreater(sum(v for k, v in totals.items() if k.startswith("with_face_up_")), 0)
        self.assertGreater(stops, 0)
        self.assertEqual(sum(v for k, v in totals.items() if k.startswith("played_")), totals["correct"] + totals["wrong"])
        self.assertEqual(totals["returned"], totals["correct"] + totals["wrong"])


# ---------------------------------------------------------------- 8. 文書


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = DOC.read_text(encoding="utf-8")
        for phrase in ("GAP-QUIZ3-REJECTION-ORACLE", "GAP-QUIZ2-REJECTION-ORACLE", "GAP-PERSONALITY-REJECTION-ORACLE", "quiz_draw_outcome_stop",
                       "UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE", "twin_command_problems", "使う前に止める", "情報漏れ"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
