"""v0.151（docs/deck-search-stop-oracles-v0.151.md）: 山札をさがす前の研究上の停止（RB2・FC1）が実際の山札を読む情報漏れの修正（両モード共通。PSP-DECK-SEARCH-STOP-ORACLES）。

山札から「○」エネルギーカード・基本エネルギーカードをつける・加えるワザの、山札を見る前（宣言の前の先読み・てじなの段階 1 の答え）の RB2・FC1 が、実際の山札のレインボーエネルギー・
基本エネルギーカードの枚数を読み、山札とサイド（・持ち主に見えない置いておくカード）の配分で宣言・答えの受理・拒否と理由の文（uid・枚数）が変わった。山札にあるかもしれないカード
（``searchable_deck_cards``）と配分を読まない下限（``deck_lower_bound_where``）で決める（v0.147・v0.148 の形）。

盤面の種類を分ける（docs 1 章）:
- 構築盤面（``build_test_state``）: ``state_of``・``tickled`` の始まり。``new_game`` からの合法な操作の列ではない
- 構築盤面からの合法な操作: ``tickled``（相手がくすぐりマシーンを使い、番を終える）・宣言・答えのコマンド
- 双子（テストだけの操作）: ``swap_hidden``（山札とうらのサイド）・``swap_set_aside``（山札と持ち主に見えない置いておくカード）・おもてのサイド（``face_up_prizes`` を直接置く前提）
- 補助関数だけの確かめ: ``deck_count_may_fall_short``・``deck_rainbow_possible``
"""

from __future__ import annotations

import pathlib
import pickle
import unittest
from dataclasses import dataclass

from kyuura_engine import ResolveDecision, UseAttack, apply_command
from kyuura_engine import effects as E
from kyuura_engine.errors import EngineError
from tests import helpers as H
from tests.helpers import with_coin_results
from tests.log_audit import command_outcome, twin_command_problems
from tests.test_deck_content_prechecks_v0_147 import (
    SETS,
    snapshot,
    state_of,
    swap_hidden,
)
from tests.test_deck_search_decision_presence_v0_150 import (
    FC1,
    HEADS,
    RB2,
    TAILS,
    P,
    answer,
    attacker,
)
from tests.test_optional_deck_evolution_presence_v0_149 import swap_set_aside, tickled

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "deck-search-stop-oracles-v0.151.md"
VIEWERS = (0, 1, None)  # 持ち主にも見えない配分なので、持ち主を含めて観測が同じ
RAINBOW = H.RAINBOW_ENERGY
L = H.LIGHTNING


@dataclass(frozen=True)
class Case:
    """対象の経路 1 つ（docs 2 章の表の行）。``energy`` はつける色のエネルギーカード（ふつうに使う例の山札）。``coins`` はワザ全体・要素のコインの枚数（「おもて」に固定）。"""

    name: str
    card: str
    energy: str
    bench: tuple = ()
    coins: int = 0
    needed: int = 1  # ふつうに使う例で、宣言を受理するのに必要な配分によらない下限


RB2_CASES = (
    Case("ひなたぼっこ（PMCG4-032。AttachFromDeck）", "PMCG4-032", H.PSYCHIC),
    Case("じゅうでん（QSG-021。AttachFromDeck）", "QSG-021", L),
    Case("もえあがる（GD5-006。AttachFromDeck）", "GD5-006", H.FIRE),
    Case("しおまねき（ES3-014。AttachFromDeck・コイン）", "ES3-014", H.WATER, coins=1),
    Case("エナジーサポート（GD6-009。AttachFromDeckToBench）", "GD6-009", H.PSYCHIC, bench=(H.RATTATA,)),
    Case("あたためる（neo4-019。AttachFromDeckToBench・控えが先）", "neo4-019", H.FIRE, bench=(H.RATTATA,)),
    Case("せいでんき（neo1-038。AttachFromDeckUpToNamedCount）", "neo1-038", L),
    Case("ゆうでん（neo3-028。AttachFromDeckByHeads）", "neo3-028", L, coins=3, needed=3),
)
YUUDEN = RB2_CASES[-1]
BELLY_DRUM, TRICK = "neo2-016", "PMCG6-046"


def board(case, deck, *, prizes=(P,) * 6, conventions=None, coin=HEADS, discard=()):
    s = state_of({"active": attacker(case.card, 0), "deck": list(deck), "prizes": list(prizes), "bench": list(case.bench), "discard": list(discard)},
                 conventions=conventions)
    return with_coin_results(s, *(coin,) * case.coins) if case.coins else s


def belly_drum(deck, *, prizes=(P,) * 6, conventions=None, discard=()):
    return state_of({"active": attacker(BELLY_DRUM, 0), "deck": list(deck), "prizes": list(prizes), "discard": list(discard)}, conventions=conventions)


def trick(deck, *, hand=(P, P), prizes=(P,) * 6, conventions=None):
    return state_of({"active": attacker(TRICK, 0), "deck": list(deck), "prizes": list(prizes), "hand": list(hand)}, conventions=conventions)


def declare(state):
    return command_outcome(state, UseAttack(0, 0))[0]


def returning(count):
    """てじなの段階 1 の答え: 手札の先頭から ``count`` 枚をもどす。"""
    return lambda x: ResolveDecision(0, x.decision.id, tuple(x.players[0].hand[:count]))


def set_aside_board(case, deck, conventions=None):
    s = tickled({"active": attacker(case.card, 0), "deck": [P, *deck], "prizes": [P] * 6, "bench": list(case.bench)}, conventions=conventions,
                set_aside=(H.POTION, H.POTION))
    return with_coin_results(s, *(HEADS,) * case.coins) if case.coins else s


def mentions(text, uids):
    return [u for u in uids if f" {u}" in text or f"[{u}" in text or f"{u}]" in text or f"{u}," in text]


class Rb2DeclarationTwinTest(unittest.TestCase):
    """RB2（山札から「○」エネルギーカードをつける 8 経路。``rainbow_attach_question`` を山札で呼ぶ 4 つの要素）: レインボーエネルギーが山札にある・うらのサイド・持ち主に見えない置いておく
    カードにあるだけが違う双子で、宣言の受理・拒否・コード・理由の文が同じ。修正の前の木では、山札にあるほうだけ RB2 で拒否し、理由の文に uid を書いた。"""

    def test_deck_versus_hidden_prize(self):
        for conventions in SETS:
            for case in RB2_CASES:
                with self.subTest(conventions=conventions, case=case.name):
                    s = board(case, [RAINBOW] + [P] * 5, conventions=conventions)
                    twin = swap_hidden(s, RAINBOW)
                    self.assertEqual(twin_command_problems([s, twin], [UseAttack(0, 0)], viewers=VIEWERS, owner_knowledge=True, until_public_difference=False), [])
                    outcome = declare(s)
                    self.assertEqual(outcome[:2], ("UnsupportedError", RB2))  # 研究上の停止は残す（山札にあるかもしれない）
                    rainbow = [u for u in s.cards if s.cards[u].card_id == RAINBOW]
                    self.assertEqual(mentions(outcome[2], rainbow), [])  # 理由の文に uid を書かない

    def test_deck_versus_hidden_set_aside(self):
        for conventions in SETS:
            for case in RB2_CASES:
                with self.subTest(conventions=conventions, case=case.name):
                    s = set_aside_board(case, [RAINBOW] + [P] * 4, conventions=conventions)
                    twin = swap_set_aside(s, RAINBOW)
                    self.assertEqual(twin_command_problems([s, twin], [UseAttack(0, 0)], viewers=VIEWERS, owner_knowledge=True, until_public_difference=False), [])
                    self.assertEqual(declare(s)[:2], ("UnsupportedError", RB2))

    def test_both_coin_faces(self):
        # コインのある経路（しおまねき・ゆうでん）: 先読みはコインの面を試すので、どちらの面に固定しても宣言の結果は同じ（コインを投げる前に決まる。投げ直しの経路を作らない）
        for case in (c for c in RB2_CASES if c.coins):
            for coin in (HEADS, TAILS):
                with self.subTest(case=case.name, coin=coin):
                    s = board(case, [RAINBOW] + [P] * 5, coin=coin)
                    self.assertEqual(twin_command_problems([s, swap_hidden(s, RAINBOW)], [UseAttack(0, 0)], viewers=VIEWERS, owner_knowledge=True,
                                                           until_public_difference=False), [])
                    self.assertEqual(declare(s)[:2], ("UnsupportedError", RB2))


class KnownCardTest(unittest.TestCase):
    """持ち主に見えている（公開の）カードは山札にないことが分かっているので、止める理由にしない（公開の情報で決まる差は残す）。"""

    def test_rainbow_known_outside_the_deck_does_not_stop(self):
        for case in RB2_CASES:
            with self.subTest(case=case.name):
                deck = [case.energy] * 10 + [P] * 2
                in_discard = board(case, deck, discard=(RAINBOW,))
                self.assertEqual(declare(in_discard), ("accepted",))
                face_up = board(case, deck, prizes=(RAINBOW,) + (P,) * 5)
                # テスト専用の前提: おもてのサイド（ロケット団参上! などのほかの経路で作った）。おもてにしたログがないので宣言は状態の検査で拒否される。補助関数だけで確かめる
                face_up.face_up_prizes = (face_up.players[0].prizes[0],)
                self.assertFalse(E.deck_rainbow_possible(face_up, 0))
                hidden = board(case, deck, prizes=(RAINBOW,) + (P,) * 5)  # 同じ配置でうらなら止める（保守的）。ゆうでんは下限（10 - 6 = 4）が「おもて」の数以上なので止めない
                self.assertEqual(declare(hidden)[:2], ("accepted",) if case is YUUDEN else ("UnsupportedError", RB2))

    def test_known_basic_energy_is_not_counted(self):
        # はらだいこ: トラッシュの基本エネルギーカードは山札にない（下限に数えない）。うらのサイドを埋める基本エネルギーカードは、どこにあるか分からない
        self.assertEqual(declare(belly_drum([H.GRASS] * 7 + [P] * 3, discard=(H.GRASS,) * 4))[:2], ("UnsupportedError", FC1))
        self.assertEqual(declare(belly_drum([H.GRASS] * 8 + [P] * 3)), ("accepted",))


class Fc1DeclarationTwinTest(unittest.TestCase):
    """FC1（はらだいこ・ゆうでんの宣言の前の先読み）: 山札の基本エネルギーカード・「雷」エネルギーカードの枚数だけが違う双子で、宣言の受理・拒否・コード・理由の文が同じ。修正の前の木
    では、1 枚以上あって足りないほうだけ FC1 で拒否し（理由の文に枚数）、0 枚なら受理した。"""

    def test_belly_drum(self):
        for conventions in SETS:
            for deck in ([H.GRASS] + [P] * 5, [H.GRASS, H.GRASS] + [P] * 5):
                with self.subTest(conventions=conventions, deck=len([c for c in deck if c != P])):
                    s = belly_drum(deck, conventions=conventions)
                    for twin in (swap_hidden(s, H.GRASS),):
                        self.assertEqual(twin_command_problems([s, twin], [UseAttack(0, 0)], viewers=VIEWERS, owner_knowledge=True,
                                                               until_public_difference=False), [])
                    self.assertEqual(declare(s)[:2], ("UnsupportedError", FC1))

    def test_belly_drum_set_aside(self):
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                s = tickled({"active": attacker(BELLY_DRUM, 0), "deck": [P, H.GRASS] + [P] * 4, "prizes": [P] * 6}, conventions=conventions,
                            set_aside=(H.POTION, H.POTION))
                self.assertEqual(twin_command_problems([s, swap_set_aside(s, H.GRASS)], [UseAttack(0, 0)], viewers=VIEWERS, owner_knowledge=True,
                                                       until_public_difference=False), [])

    def test_yuuden(self):
        for conventions in SETS:
            for coin in (HEADS, TAILS):
                with self.subTest(conventions=conventions, coin=coin):
                    s = board(YUUDEN, [L] + [P] * 5, conventions=conventions, coin=coin)
                    self.assertEqual(twin_command_problems([s, swap_hidden(s, L)], [UseAttack(0, 0)], viewers=VIEWERS, owner_knowledge=True,
                                                           until_public_difference=False), [])
                    self.assertEqual(declare(s)[:2], ("UnsupportedError", FC1))


class TrickStageOneTest(unittest.TestCase):
    """てじな（``ReturnHandThenRevealEnergy``）の段階 1（手札をもどす答え。山札を見る前）: 山札の基本エネルギーカードの枚数だけが違う双子で、答えの受理・拒否・理由の文が同じ。修正の前の
    木では、1 枚以上あって足りないほうだけ FC1 で拒否し（理由の文に枚数。決定は待ったまま）、答えを選び直して山札の枚数を探れた。"""

    def test_return_answer_twins(self):
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                s = trick([H.GRASS] + [P] * 5, conventions=conventions)
                steps = [UseAttack(0, 0), returning(2)]
                self.assertEqual(twin_command_problems([s, swap_hidden(s, H.GRASS)], steps, viewers=VIEWERS, owner_knowledge=True, until_public_difference=False), [])
                asked = apply_command(s, UseAttack(0, 0))
                outcome = command_outcome(asked, returning(2)(asked))[0]
                self.assertEqual(outcome[:2], ("UnsupportedError", FC1))
                self.assertNotIn("山札の基本エネルギーカード 1 枚", outcome[2])

    def test_set_aside_pool(self):
        # 山札と持ち主に見えない置いておくカードの双子は、くすぐりマシーンが手札をすべて置いておくので（手札は引いた 1 枚。2 枚をもどす答えを作れない）、補助関数で確かめる
        s = tickled({"active": attacker(TRICK, 0), "deck": [P, H.GRASS] + [P] * 4, "prizes": [P] * 6}, set_aside=(H.POTION, H.POTION))
        twin = swap_set_aside(s, H.GRASS)
        for x in (s, twin):
            self.assertTrue(E.deck_count_may_fall_short(x, 0, lambda uid, x=x: x.card_def(uid).is_basic_energy, 2))

    def test_probing_answers_learns_nothing(self):
        # 拒否のあと別の答え（1 枚）を試しても、双子で同じ結果（答えを選び直して山札の中身を探れない）。1 枚をもどす答えは配分によらず受理
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                s = trick([H.GRASS] + [P] * 5, conventions=conventions)
                outcomes = []
                for x in (s, swap_hidden(s, H.GRASS)):
                    asked = apply_command(x, UseAttack(0, 0))
                    outcomes.append([command_outcome(asked, returning(n)(asked))[0] for n in (2, 1)])
                self.assertEqual(outcomes[0], outcomes[1])
                self.assertEqual(outcomes[0][0][:2], ("UnsupportedError", FC1))
                self.assertEqual(outcomes[0][1], ("accepted",))

    def test_returned_basic_energy_counts(self):
        # もどすカードの基本エネルギーカードは山札に入ることが分かっている（持ち主が選んだ）。ほかに基本エネルギーカードがなければ、もどしたあとちょうど 1 枚で FC1（今までどおり）
        s = trick([P] * 6, hand=(H.GRASS, P))
        asked = apply_command(s, UseAttack(0, 0))
        self.assertEqual(command_outcome(asked, returning(2)(asked))[0][:2], ("UnsupportedError", FC1))
        # もどすのが 1 枚（基本エネルギーカード）なら受理し、段階 2 で山札（もどしたカード）から 1 枚を選ぶ
        searching = apply_command(asked, returning(1)(asked))
        self.assertEqual((searching.decision.min_choices, searching.decision.max_choices, len(searching.decision.options)), (1, 1, 1))


class NormalUseAndBoundaryTest(unittest.TestCase):
    """ふつうに使える例と、保守的に止める境界（配分を読まない下限 = 見えない対象の枚数 - 山札の外の見えない枚数）。"""

    def test_attach_paths_without_rainbow_are_usable(self):
        for case in RB2_CASES:
            with self.subTest(case=case.name):
                s = board(case, [case.energy] * 10 + [P] * 2)
                self.assertEqual(declare(s), ("accepted",))
                x = apply_command(s, UseAttack(0, 0))
                self.assertIsNotNone(x.decision)

    def test_hinatabokko_choose_and_decline(self):
        case = RB2_CASES[0]
        s = board(case, [case.energy] + [P] * 5)
        asked = apply_command(s, UseAttack(0, 0))
        attached = answer(asked, asked.decision.options[:1])
        self.assertEqual([e["kind"] for e in attached.log[len(asked.log):] if e["kind"] in ("attach_energy_from_deck", "shuffle")], ["attach_energy_from_deck", "shuffle"])
        declined = answer(asked, ())
        self.assertEqual([e.get("reason") for e in declined.log[len(asked.log):] if e["kind"] == "attach_energy_from_deck_none"], ["declined"])

    def test_belly_drum_boundary(self):
        # 山札 + うらのサイドの基本エネルギーカード K 枚・サイド 6 枚: 下限 K - 6 が 2 以上で受理（2 枚をつける）、1 なら止める。基本エネルギーカードがどこにもなければ受理（0〜0 枚）
        accepted = belly_drum([H.GRASS] * 8 + [P] * 2)
        self.assertEqual(declare(accepted), ("accepted",))
        x = apply_command(accepted, UseAttack(0, 0))
        self.assertEqual((x.decision.min_choices, x.decision.max_choices), (2, 2))
        done = answer(x, x.decision.options[:2])
        self.assertEqual(len(done.players[0].active.energy) - len(accepted.players[0].active.energy), 2)
        self.assertEqual(declare(belly_drum([H.GRASS] * 7 + [P] * 3))[:2], ("UnsupportedError", FC1))
        none = apply_command(belly_drum([P] * 6), UseAttack(0, 0))
        self.assertEqual((none.decision.options, none.decision.min_choices, none.decision.max_choices), ((), 0, 0))

    def test_yuuden_boundary(self):
        # 「おもて」の数の最大 3: 下限 3 で受理、2 で止める（FC1）。レインボーエネルギーがあるかもしれなくても下限が足りれば受理（選ぶと止める選択肢として出す）
        self.assertEqual(declare(board(YUUDEN, [L] * 9 + [P])), ("accepted",))
        self.assertEqual(declare(board(YUUDEN, [L] * 8 + [P] * 2))[:2], ("UnsupportedError", FC1))
        with_rainbow = board(YUUDEN, [L] * 9 + [RAINBOW])
        self.assertEqual(declare(with_rainbow), ("accepted",))
        x = apply_command(with_rainbow, UseAttack(0, 0))
        rainbow = [u for u in x.players[0].deck if x.cards[u].card_id == RAINBOW]
        self.assertEqual(tuple(x.decision.context_value("unresolved_choices", ())), tuple(rainbow))
        self.assertEqual(declare(board(YUUDEN, [L] * 8 + [RAINBOW, P]))[:2], ("UnsupportedError", RB2))
        self.assertEqual(declare(with_coin_results(board(YUUDEN, [L] * 8 + [P] * 2), TAILS, TAILS, TAILS))[:2], ("UnsupportedError", FC1))  # 先読みはコインの面を試す

    def test_trick_boundary(self):
        self.assertEqual(self._return(trick([H.GRASS] * 8 + [P] * 2), 2), ("accepted",))  # 下限 2
        self.assertEqual(self._return(trick([H.GRASS] * 7 + [P] * 3), 2)[:2], ("UnsupportedError", FC1))  # 下限 1
        self.assertEqual(self._return(trick([P] * 6), 2), ("accepted",))  # どこにもない: 段階 2 は選べるもののない決定
        for deck in ([H.GRASS] * 7 + [P] * 3, [H.GRASS] + [P] * 5):
            self.assertEqual(self._return(trick(deck), 1), ("accepted",))  # 1 枚は配分によらず受理

    def _return(self, s, n):
        asked = apply_command(s, UseAttack(0, 0))
        return command_outcome(asked, returning(n)(asked))[0]


class InvalidAndSaveRestoreTest(unittest.TestCase):
    def test_invalid_commands_leave_state(self):
        s = trick([H.GRASS] + [P] * 5)
        asked = apply_command(s, UseAttack(0, 0))
        before = snapshot(asked)
        for command in (ResolveDecision(0, asked.decision.id + 1, tuple(asked.players[0].hand[:1])), ResolveDecision(1, asked.decision.id, ()), returning(2)(asked)):
            with self.subTest(command=command):
                with self.assertRaises(EngineError):
                    apply_command(asked, command)
                self.assertEqual(snapshot(asked), before)

    def test_pending_stage_one_survives_save_and_restore(self):
        for deck in ([H.GRASS] + [P] * 5, [H.GRASS] * 8 + [P] * 2):
            with self.subTest(deck=deck[:2]):
                asked = apply_command(trick(deck), UseAttack(0, 0))
                restored = pickle.loads(pickle.dumps(asked))
                self.assertEqual(restored.decision, asked.decision)
                for n in (2, 1):
                    self.assertEqual(command_outcome(restored, returning(n)(restored))[0], command_outcome(asked, returning(n)(asked))[0])
                self.assertEqual(snapshot(apply_command(restored, returning(1)(restored))), snapshot(apply_command(asked, returning(1)(asked))))


class HelperTest(unittest.TestCase):
    """補助関数だけの確かめ（配分によらない）。"""

    def test_count_may_fall_short(self):
        def basic(s):
            return lambda uid: s.cards[uid].card_id == H.GRASS

        for k, expected in ((0, False), (1, True), (2, True), (7, True), (8, False)):
            for j in range(min(k, 6) + 1):
                deck = [H.GRASS] * (k - j) + [P] * (4 + j)
                prizes = [H.GRASS] * j + [P] * (6 - j)
                with self.subTest(k=k, in_prizes=j):
                    s = belly_drum(deck, prizes=prizes)
                    self.assertEqual(E.deck_count_may_fall_short(s, 0, basic(s), 2), expected)
        s = belly_drum([H.GRASS] + [P] * 5)
        self.assertFalse(E.deck_count_may_fall_short(s, 0, basic(s), 1))  # 1 枚を選ぶなら足りないことはない
        self.assertTrue(E.deck_count_may_fall_short(belly_drum([P] * 6), 0, basic(s), 2, added=1))  # もどした 1 枚だけ
        self.assertFalse(E.deck_count_may_fall_short(belly_drum([P] * 6), 0, basic(s), 1, added=1))

    def test_rainbow_possible(self):
        case = RB2_CASES[0]
        s = board(case, [RAINBOW] + [P] * 5)
        self.assertTrue(E.deck_rainbow_possible(s, 0))
        self.assertTrue(E.deck_rainbow_possible(swap_hidden(s, RAINBOW), 0))
        self.assertFalse(E.deck_rainbow_possible(board(case, [P] * 6, discard=(RAINBOW,)), 0))
        self.assertFalse(E.deck_rainbow_possible(board(case, [], prizes=(RAINBOW,) + (P,) * 5), 0))  # 山札が 0 枚ならさがさない


class DocumentTest(unittest.TestCase):
    def test_document_records_the_fix(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("PSP-DECK-SEARCH-STOP-ORACLES", "deck_count_may_fall_short", "deck_rainbow_possible", "rainbow_deck_attach_question", "SeparateStopOracleTest"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
