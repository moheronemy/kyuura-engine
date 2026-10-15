"""v0.23: エネルギー回収（PMCG1-076）と、突風・パソコン通信を同じデッキに入れた対戦。

エネルギー回収の最新の説明「手札からカードを1枚選んでトラッシュしなければ、このカードは使えない。あなたのトラッシュから「基本エネルギー
カード」を最大2枚選び出し、手札に加える。ただし、このカードを使うためにトラッシュしたカードを選ぶことはできない。」（『ポケモンカード
オフィシャルブック2000』p.257。docs/energy-retrieval-v0.23.md）。

規定と根拠（docs/energy-retrieval-v0.23.md 3 章の ER1〜ER17）:

- 使うための条件（ER2・ER3）: このカードを除く手札から 1 枚をトラッシュできなければ使えない（p.257・p.310）。トラッシュするカードの種類に
  制限はない。使っているこのカードは p.310 の手順 1 で手札から出しているので含まない。
- 回収できるもの（ER6・ER7・ER11）: 自分のトラッシュの基本エネルギーカードだけ。このカードを使うためにトラッシュしたカードは選べない
  （最新の説明「ただし…」・解説「「エネルギー回収」を使うときにトラッシュしたエネルギーカードは回収できない」）。
- 枚数（ER8）: 最大 2 枚（対象が 1 枚なら 1 枚まで。2 枚以上あっても 1 枚を選べる）。対象があるのに 0 枚を選べるか（ER9）、使う前の
  トラッシュに基本エネルギーカードがないときに使えるか（ER10）は原典で決められない（``UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE``・
  ``UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET``）。ゴースのエナジーへんかんの H4 と同じ言い回しの問いだが、別のカードの別の論点。
- 解決後（ER14・ER17）: このカードをトラッシュし、番は続く。手札に加えた基本エネルギーカードは、その番にまだつけていなければつけられる。

kyuura の記録: ERR-ENERGY-RETRIEVAL（rule_history.json。p.257 の最新の説明を kyuura が読んだ記録）はあるが、照合の記録（CC-）・最新の説明
（LD-）・ER9・ER10 の論点はない（報告事項。research_links.json）。

盤面を直接作るテスト（``build_test_state``。規定 1 か所ずつ）と、正式な対戦開始（``new_game``・60 枚・サイド 6 枚）から使う統合テスト
（v0.20 の固定のデッキのディフェンダー 4 枚を突風 2 枚・パソコン通信 2 枚に置き換えた ``mixed``、さらにきずぐすり 2 枚をエネルギー回収 2 枚に
置き換えた ``retrieval``。tools/preset_deck_games.py）を分けている。
"""

from __future__ import annotations

import copy
import pickle
import re
import sys
import unittest
from collections import Counter
from pathlib import Path

from kyuura_engine import AttachEnergy, PlayTrainer, ResolveDecision, UnsupportedError, apply_command, check_invariants, preset_deck
from kyuura_engine.cards import load_card_pool, read_verification
from kyuura_engine.decisions import DISCARD_FROM_HAND, RETRIEVE_ENERGY
from kyuura_engine.effects import DEFAULT_EFFECTS, DiscardFromHandThenRetrieveEnergy
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import (
    BILL, COMPUTER_SEARCH, DEFENDER, ENERGY_RETRIEVAL, FIRE, GRASS, GROWLITHE, GUST, PONYTA, POTION, SEEL, STARYU, WATER,
    build_test_state,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_computer_search_v0_22 import Base, by_id, snapshot

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import preset_deck_games as driver  # noqa: E402

LATEST = (
    "手札からカードを1枚選んでトラッシュしなければ、このカードは使えない。あなたのトラッシュから「基本エネルギーカード」を最大2枚選び出し、"
    "手札に加える。ただし、このカードを使うためにトラッシュしたカードを選ぶことはできない。"
)
PRINTED = "手札から1枚のカードをすてることによって、トラッシュから2枚の好きなエネルギーカードをひろって、手札に加えることができる。"
IMAGE = (
    "手札からカードを1枚選んでトラッシュしなければ、このカードは使えない。あなたのトラッシュから基本エネルギーカードを最大2枚選び、"
    "手札に加えてよい。(ただし、このカードを使うためにトラッシュしたカードを選ぶことはできない)"
)
TURN = 5  # 自分（プレイヤー 0）の番


def board(hand=(PONYTA,), discard=(WATER, FIRE, WATER), *, deck=(WATER, WATER), active=GROWLITHE, their_discard=(FIRE,)):
    """自分（プレイヤー 0）の番の MAIN。手札の先頭がエネルギー回収。トラッシュは discard。"""
    return build_test_state([
        {"active": active, "hand": [ENERGY_RETRIEVAL, *hand], "deck": list(deck), "discard": list(discard)},
        {"active": STARYU, "bench": [SEEL], "hand": [WATER], "deck": [WATER, WATER], "discard": list(their_discard)},
    ], turn_number=TURN)


class RegistrationTest(unittest.TestCase):
    def test_entry_follows_the_verified_latest_description(self):
        """登録は（カード id で）1 件。照合した写しの文面（第1弾の印刷）と、実装がしたがう最新の説明（p.257）を分けて持つ。図版は別の版。"""
        entry = DEFAULT_EFFECTS.trainer_entry(ENERGY_RETRIEVAL)
        self.assertEqual(entry.effect, DiscardFromHandThenRetrieveEnergy(discard=1, retrieve=2))
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), ("エネルギー回収", PRINTED, LATEST, "P43 p.257"))
        definition = load_card_pool().get(ENERGY_RETRIEVAL)
        self.assertTrue(definition.supported)
        self.assertEqual(definition.trainer_text_ja, PRINTED)
        record = read_verification()["cards"][ENERGY_RETRIEVAL]
        self.assertEqual((record["page"], record["pdf_page"], record["checked_on"]), (257, 259, "2026-10-15"))
        self.assertEqual((record["card_image_text_ja"], record["latest_description_ja"]), (IMAGE, LATEST))
        self.assertEqual(record["status"], "不一致あり")  # 印刷の文面（写し）・図版（別の版）・最新の説明が違う（エラッタで誤りではない）

    def test_no_card_specific_branch_in_the_engine(self):
        """engine.py・resolution/ にこのカードの id・実装での分岐を加えていない（既存のトレーナーの登録・決定・ゾーンの関数で扱う）。"""
        for path in [ROOT / "kyuura_engine" / "engine.py", *(ROOT / "kyuura_engine" / "resolution").glob("*.py")]:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(ENERGY_RETRIEVAL, text)
                self.assertIsNone(re.search(r"DiscardFromHandThenRetrieveEnergy|RETRIEVE_ENERGY|retrieve_energy", text))


class UsableTest(Base):
    """使うための条件（ER2・ER3）と、使う前のトラッシュに基本エネルギーカードがないとき（ER10）。どれも手札から出す前に確かめる。"""

    def test_hand_of_this_card_only_cannot_use_it(self):
        """手札がこのカードだけ（合計 1 枚）なら、このカードを除く手札から 1 枚トラッシュできないので使えない（p.257・p.310）。拒否しても
        カードは手札に残り、状態・乱数・ログは変わらない。合計 2 枚なら使え、選べるのはもう 1 枚だけ（このカードは選べるものにない）。"""
        state = board(hand=())
        card = state.players[0].hand[0]
        self.assert_rejected(state, PlayTrainer(0, card), "INSUFFICIENT_CARDS_IN_HAND")
        self.assertIn(card, state.players[0].hand)
        self.assertIsNone(state.trainer_in_use)
        state = board(hand=(PONYTA,))
        pending = self.play(state)
        self.assertEqual(pending.decision.options, (state.players[0].hand[1],))

    def test_any_kind_of_card_can_be_discarded(self):
        """トラッシュするカードの種類に制限はない（「カードを1枚」。ER3）。ポケモン・トレーナー（もう 1 枚のエネルギー回収を含む）・エネルギー。"""
        for card_id in (PONYTA, BILL, ENERGY_RETRIEVAL, FIRE):
            with self.subTest(card=card_id):
                state = board(hand=(card_id,))
                pending = self.play(state)
                done = self.answer(pending, pending.decision.options)
                self.assertEqual(done.decision.kind, RETRIEVE_ENERGY)
                self.assertEqual(done.players[0].discard[-1], state.players[0].hand[1])

    def test_no_basic_energy_in_the_discard_is_unresolved(self):
        """ER10: 使う前のトラッシュに基本エネルギーカードがないときに使えるかは原典で決められない。トラッシュする手札が基本エネルギーカードでも、
        そのカードは選べない（ER7）ので対象は生じない。条件の確認のあとで止める（条件を満たさなければ条件の拒否が先）。"""
        for hand in ((PONYTA,), (FIRE,)):
            with self.subTest(hand=hand):
                state = board(hand=hand, discard=(BILL, PONYTA))
                error = self.assert_rejected(state, PlayTrainer(0, state.players[0].hand[0]), "UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET",
                                             UnsupportedError)
                self.assertIn("エネルギー回収", str(error))
        empty = board(hand=(FIRE,), discard=())
        self.assert_rejected(empty, PlayTrainer(0, empty.players[0].hand[0]), "UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET", UnsupportedError)
        small = board(hand=(), discard=())
        self.assert_rejected(small, PlayTrainer(0, small.players[0].hand[0]), "INSUFFICIENT_CARDS_IN_HAND")
        # 相手のトラッシュの基本エネルギーカードは対象ではない（「あなたのトラッシュ」）
        theirs = board(hand=(PONYTA,), discard=(BILL,), their_discard=(FIRE, WATER))
        self.assert_rejected(theirs, PlayTrainer(0, theirs.players[0].hand[0]), "UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET", UnsupportedError)
        # 隣: 基本エネルギーカードが 1 枚あれば使える
        self.play(board(hand=(PONYTA,), discard=(BILL, WATER)))

    def test_other_rejections_do_not_change_state(self):
        """番でないプレイヤー・手札にないカード・決定を待つ間の宣言は拒否し、状態は変わらない。"""
        state = board(hand=(PONYTA, ENERGY_RETRIEVAL))
        first, second = state.players[0].hand[0], state.players[0].hand[2]
        self.assert_rejected(state, PlayTrainer(1, first), "NOT_YOUR_TURN")
        self.assert_rejected(state, PlayTrainer(0, state.players[0].discard[0]), "CARD_NOT_IN_HAND")
        pending = self.play(state)
        self.assert_rejected(pending, PlayTrainer(0, second), "WRONG_PHASE")


class DiscardStageTest(Base):
    """段階 1（ER4・ER5）: 使ったプレイヤーが、このカードを除く手札からちょうど 1 枚を選んでトラッシュする（パソコン通信と同じ処理）。"""

    def setUp(self):
        self.state = board(hand=(FIRE, PONYTA))
        self.card = self.state.players[0].hand[0]
        self.pending = self.play(self.state)

    def test_decision_shape_and_card_in_use(self):
        d = self.pending.decision
        self.assertEqual((d.player, d.kind, d.resume, d.min_choices, d.max_choices), (0, DISCARD_FROM_HAND, "trainer", 1, 1))
        self.assertEqual(d.context_value("use"), (0, self.card, ENERGY_RETRIEVAL))
        self.assertEqual(d.options, tuple(self.state.players[0].hand[1:]))
        self.assertEqual((self.pending.trainer_in_use.player, self.pending.trainer_in_use.card), (0, self.card))
        self.assertNotIn(self.card, self.pending.players[0].hand + self.pending.players[0].discard)

    def test_invalid_choices_keep_the_decision(self):
        """使っているこのカード・トラッシュ・山札・相手のカード・場のカード・0 枚・2 枚は拒否し、決定を待ったまま、このカードは使用中のまま。
        使ったプレイヤー以外の答えも拒否。"""
        d = self.pending.decision
        p0, p1 = self.pending.players
        hand = d.options
        wrong = [
            ((self.card,), "INVALID_CHOICE"),  # 使用中のこのカード
            ((p0.discard[0],), "INVALID_CHOICE"),  # 自分のトラッシュ
            ((p0.deck[0],), "INVALID_CHOICE"),  # 自分の山札
            ((p1.hand[0],), "INVALID_CHOICE"),  # 相手の手札
            ((p0.active.card,), "INVALID_CHOICE"),  # 自分の場
            ((), "INVALID_CHOICE_COUNT"),
            ((hand[0], hand[1]), "INVALID_CHOICE_COUNT"),
            ((hand[0], hand[0]), "INVALID_CHOICE_COUNT"),
        ]
        for choices, code in wrong:
            with self.subTest(choices=choices):
                self.assert_rejected(self.pending, ResolveDecision(0, d.id, choices), code)
                self.assertEqual(self.pending.decision, d)
                self.assertEqual(self.pending.trainer_in_use.card, self.card)
                self.assert_conserved(self.pending)
        self.assert_rejected(self.pending, ResolveDecision(1, d.id, hand[:1]), "NOT_YOUR_DECISION")


class RetrieveStageTest(Base):
    """段階 2（ER6〜ER9・ER11〜ER13）: 使ったプレイヤーが、トラッシュの基本エネルギーカード（段階 1 でトラッシュしたカードを除く）を最大 2 枚選び、
    手札に加える。"""

    def at_retrieve(self, hand=(FIRE,), discard=(WATER, BILL, FIRE, PONYTA, WATER)):
        state = board(hand=hand, discard=discard)
        pending = self.play(state)
        return state, self.answer(pending, pending.decision.options[:1])

    def test_decision_shape_excludes_the_discarded_card(self):
        """選べるのはトラッシュの基本エネルギーカード（トラッシュの並び）だけで、このカードを使うためにトラッシュした基本エネルギーカード
        （炎）は除く（ER7）。トレーナー・ポケモンのカードは選べるものにない（ER6）。0〜2 枚（0 枚は答えのときに止める。ER9）。"""
        state, retrieving = self.at_retrieve()
        d = retrieving.decision
        discarded = state.players[0].hand[1]
        self.assertEqual((d.player, d.kind, d.resume, d.min_choices, d.max_choices), (0, RETRIEVE_ENERGY, "trainer", 0, 2))
        self.assertEqual(d.context_value("discarded"), (discarded,))
        expected = tuple(u for u in state.players[0].discard if retrieving.card_def(u).is_basic_energy)
        self.assertEqual(d.options, expected)
        self.assertIn(discarded, retrieving.players[0].discard)  # トラッシュにはあるが選べない
        self.assertNotIn(discarded, d.options)
        self.assertEqual(retrieving.trainer_in_use.card, state.players[0].hand[0])

    def test_retrieve_one_or_two_basic_energy_cards(self):
        """2 枚以上あるとき、2 枚（同じ名前の別のカード・タイプの違うカード）も 1 枚だけも選べる（「最大2枚」。ER8・ER12）。選んだカードは
        トラッシュから手札に移り（トラッシュの並びの順）、ログ retrieve_energy に書く（公開。ER13）。乱数を使わない。"""
        state, retrieving = self.at_retrieve(discard=(WATER, FIRE, WATER, GRASS))
        waters = by_id(retrieving, 0, "discard", WATER)
        fire = by_id(retrieving, 0, "discard", FIRE)
        fire = [u for u in fire if u in retrieving.decision.options]
        for choices in (tuple(waters), (waters[1], fire[0]), (fire[0],)):
            with self.subTest(choices=choices):
                done = self.answer(retrieving, choices)
                q = done.players[0]
                ordered = tuple(u for u in retrieving.players[0].discard if u in choices)
                self.assertEqual(q.hand[-len(choices):], list(ordered))
                self.assertTrue(set(choices).isdisjoint(q.discard))
                self.assertEqual([e["kind"] for e in done.log[-2:]], ["retrieve_energy", "discard_trainer"])
                self.assertEqual(done.log[-2]["cards"], ordered)
                self.assertEqual(rng_fingerprint(done.rng), rng_fingerprint(retrieving.rng))
                self.assertEqual((done.phase.value, done.current_player, done.turn_number), ("main", 0, TURN))
        # 答えの順番によらない
        a, b = waters
        self.assertEqual(snapshot(self.answer(retrieving, (a, b))), snapshot(self.answer(retrieving, (b, a))))

    def test_only_one_target(self):
        """対象が 1 枚なら 1 枚まで（max_choices 1）。2 枚を選ぶのは枚数の誤り。"""
        state, retrieving = self.at_retrieve(hand=(PONYTA,), discard=(BILL, WATER))
        d = retrieving.decision
        self.assertEqual((d.min_choices, d.max_choices, len(d.options)), (0, 1, 1))
        self.assert_rejected(retrieving, ResolveDecision(0, d.id, (d.options[0], d.options[0])), "INVALID_CHOICE_COUNT")
        done = self.answer(retrieving, d.options)
        self.assertIn(d.options[0], done.players[0].hand)

    def test_zero_cards_is_unresolved_and_keeps_the_decision(self):
        """ER9: 選べるものがあるのに 0 枚を選べるか（「最大2枚」が 0 枚を含むか）は原典で決められない。状態を変えずに止め、決定は待ったまま、
        段階 1 のトラッシュは取り消さない。1 枚以上を選び直せる。"""
        state, retrieving = self.at_retrieve()
        d = retrieving.decision
        error = self.assert_rejected(retrieving, ResolveDecision(0, d.id, ()), "UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE", UnsupportedError)
        self.assertIn("最大2枚", str(error))
        self.assertEqual(retrieving.decision, d)
        self.assertIn(state.players[0].hand[1], retrieving.players[0].discard)
        self.answer(retrieving, d.options[:1])

    def test_invalid_choices_keep_the_discard_and_the_decision(self):
        """トラッシュしたカード・トラッシュのトレーナーとポケモン・手札・山札・相手のトラッシュの基本エネルギーカード・使用中のこのカード・
        3 枚・同じカード 2 回・相手の答えを拒否。段階 1 のトラッシュは取り消さず、決定を待ったまま、このカードは使用中のまま。"""
        state, retrieving = self.at_retrieve(hand=(FIRE, PONYTA))
        d = retrieving.decision
        q, them = retrieving.players
        discarded = d.context_value("discarded")[0]
        trainer = by_id(retrieving, 0, "discard", BILL)[0]
        pokemon = by_id(retrieving, 0, "discard", PONYTA)[0]
        wrong = [((discarded,), "INVALID_CHOICE"), ((trainer,), "INVALID_CHOICE"), ((pokemon,), "INVALID_CHOICE"),
                 ((q.hand[0],), "INVALID_CHOICE"), ((q.deck[0],), "INVALID_CHOICE"), ((them.discard[0],), "INVALID_CHOICE"),
                 ((retrieving.trainer_in_use.card,), "INVALID_CHOICE"), (tuple(d.options[:3]), "INVALID_CHOICE_COUNT"),
                 ((d.options[0], d.options[0]), "DUPLICATE_CHOICE")]
        for choices, code in wrong:
            with self.subTest(choices=choices):
                self.assert_rejected(retrieving, ResolveDecision(0, d.id, choices), code)
                self.assertEqual(retrieving.decision, d)
                self.assertIn(discarded, retrieving.players[0].discard)
                self.assert_conserved(retrieving)
        self.assert_rejected(retrieving, ResolveDecision(1, d.id, d.options[:1]), "NOT_YOUR_DECISION")

    def test_pending_retrieve_survives_copy_and_pickle(self):
        state, retrieving = self.at_retrieve()
        command = ResolveDecision(0, retrieving.decision.id, retrieving.decision.options[:2])
        expected = snapshot(apply_command(retrieving, command))
        for copied in (retrieving.clone(), copy.deepcopy(retrieving), pickle.loads(pickle.dumps(retrieving))):
            self.assertEqual(snapshot(apply_command(copied, command)), expected)


class AfterResolutionTest(Base):
    """解決後（ER14・ER17）。"""

    def test_turn_continues_and_the_retrieved_energy_can_be_attached(self):
        """このカードは効果のあとトラッシュし、番は続く。手札に加えた基本エネルギーカードを、その番にバトル場のポケモンにつけられる（p.310）。"""
        state = board(hand=(PONYTA,), discard=(FIRE, WATER))
        card = state.players[0].hand[0]
        pending = self.play(state)
        retrieving = self.answer(pending, pending.decision.options)
        fire = by_id(retrieving, 0, "discard", FIRE)[0]
        done = self.answer(retrieving, (fire,))
        self.assertIn(card, done.players[0].discard)
        self.assertIsNone(done.trainer_in_use)
        attached = apply_command(done, AttachEnergy(0, fire, done.players[0].active.card))
        self.assertIn(fire, attached.players[0].active.energy)
        self.assertEqual((check_invariants(attached), attached.phase.value), ([], "main"))

    def test_second_energy_retrieval_in_the_same_turn(self):
        """同じ番に 2 枚目を使える（p.310。何枚でも）。1 枚目のトラッシュする手札に、もう 1 枚のエネルギー回収を選ぶこともできる（選べるものには
        ならない）。1 枚目で基本エネルギーカードをすべて手札に加えたら、トラッシュに対象がないので 2 枚目は ER10 で止まる。"""
        state = board(hand=(ENERGY_RETRIEVAL, PONYTA, BILL), discard=(FIRE, WATER, WATER))
        second = state.players[0].hand[1]
        pending = self.play(state)
        retrieving = self.answer(pending, (by_id(pending, 0, "hand", PONYTA)[0],))
        done = self.answer(retrieving, retrieving.decision.options[:2])  # 3 枚のうち 2 枚。トラッシュに水が 1 枚残る
        again = apply_command(done, PlayTrainer(0, second))
        self.assert_conserved(again)
        self.assertEqual(again.decision.kind, DISCARD_FROM_HAND)
        last = self.answer(again, (by_id(again, 0, "hand", BILL)[0],))
        self.assertEqual(len(last.decision.options), 1)
        finished = self.answer(last, last.decision.options)
        self.assertEqual([u for u in finished.players[0].discard if finished.card_def(u).is_basic_energy], [])
        # 1 枚目で 2 枚すべてを手札に加えたら、2 枚目は対象がない（ER10）
        state = board(hand=(ENERGY_RETRIEVAL, PONYTA), discard=(FIRE, WATER))
        pending = self.play(state)
        retrieving = self.answer(pending, (by_id(pending, 0, "hand", PONYTA)[0],))
        done = self.answer(retrieving, retrieving.decision.options)
        self.assert_rejected(done, PlayTrainer(0, state.players[0].hand[1]), "UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET", UnsupportedError)
        # もう 1 枚のエネルギー回収をトラッシュに選ぶ場合
        state = board(hand=(ENERGY_RETRIEVAL, PONYTA), discard=(FIRE, WATER))
        second = state.players[0].hand[1]
        pending = self.play(state)
        retrieving = self.answer(pending, (second,))
        self.assertIn(second, retrieving.players[0].discard)
        self.assertNotIn(second, retrieving.decision.options)


class MixedGamesTest(unittest.TestCase):
    """第1段階: 正式な対戦開始から、v0.20 の固定のデッキのディフェンダー 4 枚を突風 2 枚・パソコン通信 2 枚に置き換えた一時的なデッキ（``mixed``）
    で、席を入れかえて 6 局ずつ。両方のカードを使い、パソコン通信で山札から突風を選んでその番に使う場面が自然に起こる。決定ごとに、決定する
    プレイヤー・番のプレイヤー・使用中のカードが、その決定のトレーナーの使用と同じで、MAIN にもどったら使用中のカードが残っていない（突風と
    パソコン通信の決定・使用中のカードが混ざらない）。"""

    GAMES = 6

    @classmethod
    def setUpClass(cls):
        cls.results = driver.run(cls.GAMES, keep_state=True, variant="mixed")

    def test_decks(self):
        """公開の固定のデッキは変えていない。一時的なデッキは 60 枚・ディフェンダー 0 枚・突風 2 枚・パソコン通信 2 枚で、ほかは同じ。"""
        for deck_id in (driver.DECK_A, driver.DECK_B):
            with self.subTest(deck=deck_id):
                base = preset_deck(deck_id).counts()
                self.assertEqual(base[DEFENDER], 4)
                self.assertNotIn(GUST, base)
                self.assertNotIn(COMPUTER_SEARCH, base)
                cards = Counter(driver.deck_cards(deck_id, "mixed"))
                expected = Counter(base)
                expected[DEFENDER] -= 4
                expected[GUST] += 2
                expected[COMPUTER_SEARCH] += 2
                self.assertEqual(+cards, +expected)
                self.assertEqual(sum(cards.values()), 60)

    def test_both_cards_used_and_searched_gust_played_the_same_turn(self):
        gust = [u for r in self.results for u in r["gust_uses"]]
        computer = [u for r in self.results for u in r["computer_uses"]]
        self.assertTrue(gust and computer)
        self.assertTrue(all(u["switched"] for u in gust))
        self.assertTrue(all(len(u["discarded"]) == 2 and u["shuffled"] for u in computer))
        self.assertTrue(any(bool(r["gust_uses"]) and bool(r["computer_uses"]) for r in self.results))
        searched = [u for u in computer if u.get("searched") == GUST]
        self.assertTrue(searched)
        self.assertTrue(all(u.get("used_as") == "play_trainer" and u.get("used_same_turn") for u in searched))
        # その突風は、同じ番に相手の場を入れ替えた
        turns = {(r["seed"], tuple(r["decks"]), u["turn"], u["user"]) for r in self.results for u in r["computer_uses"] if u.get("searched") == GUST}
        switched = {(r["seed"], tuple(r["decks"]), u["turn"], u["user"]) for r in self.results for u in r["gust_uses"] if u["switched"]}
        self.assertLessEqual(turns, switched)

    def test_decisions_and_cards_in_use_do_not_mix(self):
        checks = Counter()
        for r in self.results:
            checks.update({k: v for k, v in r["policy"].items() if k.startswith("check_")})
            self.assertEqual(r["trainer_sequence_problems"], [], (r["seed"], r["decks"]))
        self.assertGreater(checks[f"check_decision_{GUST}_select_pokemon"], 0)
        self.assertGreater(checks[f"check_decision_{COMPUTER_SEARCH}_search_deck"], 0)
        self.assertEqual((checks["check_decision_player_mismatch"], checks["check_in_use_mismatch"], checks["check_in_use_left_in_main"]),
                         (0, 0, 0))

    def test_every_game_is_classified_and_audited(self):
        outcomes = Counter(r["outcome"] for r in self.results)
        self.assertEqual(sum(outcomes.values()), 2 * self.GAMES)
        self.assertEqual(outcomes["internal_error"] + outcomes["unexpected_rejection"], 0, [r.get("error") for r in self.results])
        for r in self.results:
            state = r["state"]
            with self.subTest(seed=r["seed"], decks=r["decks"]):
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])
                self.assertFalse(r["unresolved_rejections"])


class RetrievalGamesTest(unittest.TestCase):
    """第2段階: ``mixed`` からさらにきずぐすり 2 枚をエネルギー回収 2 枚に置き換えた一時的なデッキ（``retrieval``）で、席を入れかえて 6 局ずつ。
    エネルギー回収を山札から引いて使い、手札から 1 枚トラッシュし、トラッシュの基本エネルギーカードを手札に加え、その番にエネルギーをつける
    場面が自然に起こる（盤面は作らない）。"""

    GAMES = 6

    @classmethod
    def setUpClass(cls):
        cls.results = driver.run(cls.GAMES, keep_state=True, variant="retrieval")

    def test_decks(self):
        for deck_id in (driver.DECK_A, driver.DECK_B):
            with self.subTest(deck=deck_id):
                base = preset_deck(deck_id).counts()
                self.assertNotIn(ENERGY_RETRIEVAL, base)
                cards = Counter(driver.deck_cards(deck_id, "retrieval"))
                expected = Counter(driver.deck_cards(deck_id, "mixed"))
                expected[POTION] -= 2
                expected[ENERGY_RETRIEVAL] += 2
                self.assertEqual(+cards, +expected)
                self.assertEqual((sum(cards.values()), cards[POTION]), (60, 2))

    def test_energy_retrieval_is_drawn_used_and_followed_up(self):
        uses = [u for r in self.results for u in r["retrieval_uses"]]
        self.assertTrue(uses)
        self.assertTrue(all(len(u["discarded"]) == 1 and 1 <= len(u["retrieved"]) <= 2 for u in uses))
        self.assertTrue(all("attached_same_turn" in u["fates"] for u in uses))  # 手に入れたエネルギーをその番につけた
        origins = Counter()
        for r in self.results:
            state = r["state"]
            for i, e in enumerate(state.log):
                if e["kind"] == "play_trainer" and state.cards[e["card"]].card_id == ENERGY_RETRIEVAL:
                    came = next(x["kind"] for x in reversed(state.log[:i])
                                if (x["kind"] in ("draw", "search_deck") and e["card"] in (x.get("cards") or (x.get("card"),)))
                                or (x["kind"] == "take_prize" and x["card"] == e["card"]))
                    origins[came] += 1
        self.assertEqual(sum(origins.values()), len(uses))
        self.assertGreater(origins["draw"], 0)

    def test_every_game_is_classified_and_audited(self):
        outcomes = Counter(r["outcome"] for r in self.results)
        self.assertEqual(sum(outcomes.values()), 2 * self.GAMES)
        self.assertEqual(outcomes["internal_error"] + outcomes["unexpected_rejection"], 0, [r.get("error") for r in self.results])
        checks = Counter()
        for r in self.results:
            state = r["state"]
            checks.update({k: v for k, v in r["policy"].items() if k.startswith("check_")})
            with self.subTest(seed=r["seed"], decks=r["decks"]):
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])
                self.assertEqual(r["trainer_sequence_problems"], [])
                self.assertFalse(r["unresolved_rejections"])  # 手順は ER9・ER10 に当たる使い方をしない
        self.assertGreater(checks[f"check_decision_{ENERGY_RETRIEVAL}_retrieve_energy"], 0)
        self.assertEqual((checks["check_decision_player_mismatch"], checks["check_in_use_mismatch"], checks["check_in_use_left_in_main"]),
                         (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
