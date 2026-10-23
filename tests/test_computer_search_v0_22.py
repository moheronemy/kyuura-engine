"""v0.22: パソコン通信（PMCG1-090）。最新の説明「手札からカードを2枚選んでトラッシュしなければ、このカードは使えない。あなたの山札から
カードを1枚選び出し、手札に加える。その後、その山札をよく切る。」（『ポケモンカードオフィシャルブック2000』p.260。p.310 の「使うための
条件」の例にも同じ文。docs/computer-search-v0.22.md）。

規定と根拠（docs/computer-search-v0.22.md 3 章の CS1〜CS20）:

- 使うための条件（CS2〜CS5）: このカードを除く手札から 2 枚をトラッシュできなければ使えない（p.310「2枚トラッシュできないときには、
  「パソコン通信」を使うことはできません。」）。使っているこのカードは p.310 の手順 1 で手札から出しているので含まない。
- 山札が 0 枚のとき（CS6）は原典で決められない（``UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK``）。
- 段階 1（CS7〜CS10）: 使ったプレイヤーが手札からちょうど 2 枚を選び、トラッシュする（公開）。段階 2（CS11〜CS16）: 使ったプレイヤーが
  山札からどの種類のカードでも 1 枚を選び（省略できない）、手札に加え（相手に見せる指示はない。選んだカードは非公開の項目）、その山札を
  切る（``state.rng``）。
- 解決後（CS17〜CS20）: このカードをトラッシュし、番は続く。「カードを引く」ではないので、山札が 0 枚になっても負けではない。

kyuura の記録: kyuura（研究の基準 3f34908）に、このカードの照合の記録（CC-）・最新の説明・p.260 のページの記録・CS6 の論点はない
（報告事項。research_links.json の engine_verified_without_kyuura_record・stop_codes の not_in_kyuura）。

盤面を直接作るテスト（``build_test_state``。規定 1 か所ずつ）と、正式な対戦開始（``new_game``・60 枚・サイド 6 枚）から使う統合テスト
（``NaturalGamesTest``。v0.20 の固定のデッキのディフェンダー 3 枚をパソコン通信 3 枚に置き換えた一時的なデッキ。tools/preset_deck_games.py）を
分けている。
"""

from __future__ import annotations

import copy
import pickle
import re
import sys
import unittest
from collections import Counter
from pathlib import Path

from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, Phase, PlayTrainer, ResolveDecision, UnsupportedError, apply_command,
    check_invariants, preset_deck, state_to_dict,
)
from kyuura_engine.cards import load_card_pool, read_verification
from kyuura_engine.decisions import DISCARD_FROM_HAND, SEARCH_DECK
from kyuura_engine.effects import DEFAULT_EFFECTS, DiscardFromHandThenSearchDeck
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import (
    BILL, COMPUTER_SEARCH, DEFENDER, DEWGONG, FIRE, GROWLITHE, PONYTA, POTION, SEEL, STARYU, WATER, build_test_state,
)
from tests.log_audit import log_problems, serialization_problems

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import preset_deck_games as driver  # noqa: E402

LATEST = "手札からカードを2枚選んでトラッシュしなければ、このカードは使えない。あなたの山札からカードを1枚選び出し、手札に加える。その後、その山札をよく切る。"
PRINTED = "手札から2枚カードをすてることによって、山札から好きなカードを1枚選んで手札にすることができる。そのあとで山札をよくきってもとに戻す。"
TURN = 5  # 自分（プレイヤー 0）の番


def full(state):
    return state_to_dict(state, format_version=9)


def snapshot(state):
    """拒否で変わらないことを確かめる値（書き出しの全体・乱数・ログ）。"""
    return full(state), rng_fingerprint(state.rng), tuple(state.log)


def board(hand=(FIRE, PONYTA), deck=(WATER, SEEL, BILL, FIRE), *, their_deck=(WATER, WATER), active=GROWLITHE, bench=()):
    """自分（プレイヤー 0）の番の MAIN。手札の先頭がパソコン通信。"""
    return build_test_state([
        {"active": active, "bench": list(bench), "hand": [COMPUTER_SEARCH, *hand], "deck": list(deck)},
        {"active": STARYU, "bench": [SEEL], "hand": [WATER], "deck": list(their_deck)},
    ], turn_number=TURN)


def all_uids(state):
    """どのゾーンにもあるカードの uid（使用中のトレーナーを含む）。"""
    found = []
    for p in state.players:
        found += p.deck + p.hand + p.discard + p.prizes
        for pokemon in p.in_play():
            found += list(pokemon.cards()) + pokemon.energy + [t.card for t in pokemon.trainers]
    if state.trainer_in_use is not None:
        found.append(state.trainer_in_use.card)
    return found


def by_id(state, player, zone, card_id):
    return [u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id]


class Base(unittest.TestCase):
    def assert_rejected(self, state, command, code, error=IllegalActionError):
        before = snapshot(state)
        with self.assertRaises(error) as ctx:
            apply_command(state, command)
        self.assertIs(type(ctx.exception), error)
        self.assertEqual(ctx.exception.code, code, command)
        self.assertEqual(snapshot(state), before)  # 拒否しても状態・乱数・ログは変わらない
        return ctx.exception

    def assert_conserved(self, state):
        self.assertEqual(Counter(all_uids(state)), Counter(list(state.cards)))
        self.assertEqual(check_invariants(state), [])

    def play(self, state):
        before = snapshot(state)
        pending = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        self.assertEqual(snapshot(state), before)  # 渡した状態は変えない
        self.assert_conserved(pending)
        return pending

    def answer(self, state, choices, player=0):
        before = snapshot(state)
        new = apply_command(state, ResolveDecision(player, state.decision.id, tuple(choices)))
        self.assertEqual(snapshot(state), before)
        self.assert_conserved(new)
        return new


class RegistrationTest(unittest.TestCase):
    def test_entry_follows_the_verified_latest_description(self):
        """登録は（カード id で）1 件。照合した写しの文面（印刷）と、実装がしたがう最新の説明（p.260）を分けて持つ。"""
        entry = DEFAULT_EFFECTS.trainer_entry(COMPUTER_SEARCH)
        self.assertEqual(entry.effect, DiscardFromHandThenSearchDeck(discard=2, search=1))
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), ("パソコン通信", PRINTED, LATEST, "P43 p.260"))
        definition = load_card_pool().get(COMPUTER_SEARCH)
        self.assertTrue(definition.supported)
        self.assertEqual(definition.trainer_text_ja, PRINTED)
        record = read_verification()["cards"][COMPUTER_SEARCH]
        self.assertEqual((record["page"], record["pdf_page"], record["checked_on"]), (260, 262, "2026-10-15"))
        self.assertEqual((record["card_image_text_ja"], record["latest_description_ja"]), (PRINTED, LATEST))
        self.assertEqual(record["status"], "不一致あり")  # 最新の説明が印刷の文面（kyuura の写し・図版）と違う（版の違いで誤りではない）

    def test_no_card_specific_branch_in_the_engine(self):
        """engine.py・resolution/ にこのカードの id・実装での分岐を加えていない（既存のトレーナーの登録・決定・ゾーンの関数で扱う）。"""
        for path in [ROOT / "kyuura_engine" / "engine.py", *(ROOT / "kyuura_engine" / "resolution").glob("*.py")]:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(COMPUTER_SEARCH, text)
                self.assertIsNone(re.search(r"DiscardFromHandThenSearchDeck|discard_from_hand", text))
                # v0.83: 山札から選んだカードを見せずに手札に加えるゾーンの関数 ``search_deck_to_hand`` は、ワザの要素（ひかるミュウの「フラッシュサーチ」。
                # ``programs.LookTopTakeOne``）も使う（共通の関数。このカードの処理ではない）ので、programs.py のその要素の中の 1 か所だけを許す
                uses = [m.start() for m in re.finditer(r"search_deck_to_hand\(", text)]
                if path.name == "programs.py":
                    start = text.index("class LookTopTakeOne(")
                    end = text.find("\nclass ", start + 1)
                    self.assertEqual(len(uses), 1)
                    self.assertTrue(start < uses[0] < end)
                else:
                    self.assertEqual(uses, [])


class UsableTest(Base):
    """使うための条件（CS2〜CS5）と、山札が 0 枚のとき（CS6）。どれも手札から出す前に確かめる。"""

    def test_hand_of_one_or_two_cards_cannot_use_it(self):
        """手札がこのカードだけ（合計 1 枚）・ほかに 1 枚（合計 2 枚）なら、このカードを除く手札から 2 枚トラッシュできないので使えない
        （p.310）。拒否してもカードは手札に残り、状態・乱数・ログは変わらない。"""
        for hand in ((), (FIRE,)):
            with self.subTest(total=1 + len(hand)):
                state = board(hand)
                card = state.players[0].hand[0]
                self.assert_rejected(state, PlayTrainer(0, card), "INSUFFICIENT_CARDS_IN_HAND")
                self.assertIn(card, state.players[0].hand)
                self.assertIsNone(state.trainer_in_use)

    def test_hand_of_three_cards_can_use_it(self):
        """合計 3 枚（このカードと、ほかに 2 枚）なら使える。トラッシュするのは残りの 2 枚で、このカードは選べるものにない。"""
        state = board((FIRE, PONYTA))
        pending = self.play(state)
        self.assertEqual(pending.decision.options, tuple(state.players[0].hand[1:]))
        self.assertNotIn(state.players[0].hand[0], pending.decision.options)

    def test_empty_deck_is_unresolved_and_checked_after_the_condition(self):
        """CS6: 山札が 0 枚のときに使えるかは原典で決められない（使うための条件は手札のトラッシュだけで、山札から選び出せないときの扱いは
        書かれていない。p.312 の「引けるだけ引く」は「カードを引く」ときの規定）。条件の確認のあとで止める（条件を満たさなければ条件の拒否）。"""
        state = board((FIRE, PONYTA), deck=())
        error = self.assert_rejected(state, PlayTrainer(0, state.players[0].hand[0]), "UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK", UnsupportedError)
        self.assertIn("パソコン通信", str(error))
        small = board((FIRE,), deck=())
        self.assert_rejected(small, PlayTrainer(0, small.players[0].hand[0]), "INSUFFICIENT_CARDS_IN_HAND")
        # 隣: 山札が 1 枚なら使える
        self.play(board((FIRE, PONYTA), deck=(WATER,)))

    def test_other_rejections_do_not_change_state(self):
        """番でないプレイヤー・手札にないカード・決定を待つ間の宣言は拒否し、状態は変わらない。"""
        state = board((FIRE, PONYTA, COMPUTER_SEARCH))
        first, second = state.players[0].hand[0], state.players[0].hand[3]
        self.assert_rejected(state, PlayTrainer(1, first), "NOT_YOUR_TURN")
        self.assert_rejected(state, PlayTrainer(0, state.players[0].deck[0]), "CARD_NOT_IN_HAND")
        pending = self.play(state)
        self.assert_rejected(pending, PlayTrainer(0, second), "WRONG_PHASE")


class DiscardStageTest(Base):
    """段階 1（CS7〜CS10）: 使ったプレイヤーが、このカードを除く手札からちょうど 2 枚を選んでトラッシュする。"""

    def setUp(self):
        self.state = board((FIRE, FIRE, PONYTA, POTION))
        self.card = self.state.players[0].hand[0]
        self.pending = self.play(self.state)

    def test_decision_shape_and_card_in_use(self):
        d = self.pending.decision
        self.assertEqual((d.player, d.kind, d.resume, d.min_choices, d.max_choices), (0, DISCARD_FROM_HAND, "trainer", 2, 2))
        self.assertEqual(d.context_value("use"), (0, self.card, COMPUTER_SEARCH))
        self.assertEqual(d.options, tuple(self.state.players[0].hand[1:]))
        self.assertEqual((self.pending.trainer_in_use.player, self.pending.trainer_in_use.card), (0, self.card))
        self.assertNotIn(self.card, self.pending.players[0].hand + self.pending.players[0].discard)
        self.assertEqual((self.pending.current_player, self.pending.turn_number, self.pending.phase), (0, TURN, Phase.DECISION))

    def test_two_cards_with_the_same_name_can_be_discarded(self):
        """同じ名前の別のカード 2 枚（炎エネルギー 2 枚）を選べる。選んだカードが先にトラッシュに移り、そのあと山札を選ぶ決定になる。"""
        fires = by_id(self.pending, 0, "hand", FIRE)
        done = self.answer(self.pending, fires)
        self.assertEqual(done.players[0].discard, fires)
        self.assertTrue(set(fires).isdisjoint(done.players[0].hand))
        self.assertEqual(done.decision.kind, SEARCH_DECK)
        self.assertEqual([e["kind"] for e in done.log[-2:]], ["play_trainer", "discard_from_hand"])
        self.assertEqual(done.log[-1]["cards"], tuple(fires))
        self.assertEqual(rng_fingerprint(done.rng), rng_fingerprint(self.state.rng))  # トラッシュでは乱数を使わない

    def test_answer_order_does_not_matter(self):
        """選んだ 2 枚は手札の並びの順にトラッシュする（トラッシュに順番はない。p.312）。答えの並びが違っても同じ状態になる。"""
        a, b = self.pending.decision.options[1], self.pending.decision.options[3]
        self.assertEqual(full(self.answer(self.pending, (a, b))), full(self.answer(self.pending, (b, a))))

    def test_invalid_choices_keep_the_decision(self):
        """使っているこのカード・山札・トラッシュ・相手のカード・場のカード・1 枚・3 枚・同じカード 2 回は拒否し、決定を待ったまま、このカードは
        使用中のまま（なくならない）。使ったプレイヤー以外の答えも拒否。"""
        d = self.pending.decision
        p0, p1 = self.pending.players
        hand = d.options
        wrong = [
            ((self.card, hand[0]), "INVALID_CHOICE"),  # 使用中のこのカード
            ((p0.deck[0], hand[0]), "INVALID_CHOICE"),  # 自分の山札
            ((p1.hand[0], hand[0]), "INVALID_CHOICE"),  # 相手の手札
            ((p1.deck[0], hand[0]), "INVALID_CHOICE"),  # 相手の山札
            ((p0.active.card, hand[0]), "INVALID_CHOICE"),  # 自分の場
            ((hand[0],), "INVALID_CHOICE_COUNT"),
            ((hand[0], hand[1], hand[2]), "INVALID_CHOICE_COUNT"),
            ((hand[0], hand[0]), "DUPLICATE_CHOICE"),
        ]
        for choices, code in wrong:
            with self.subTest(choices=choices):
                self.assert_rejected(self.pending, ResolveDecision(0, d.id, choices), code)
                self.assertEqual(self.pending.decision, d)
                self.assertEqual(self.pending.trainer_in_use.card, self.card)
                self.assert_conserved(self.pending)
        self.assert_rejected(self.pending, ResolveDecision(1, d.id, hand[:2]), "NOT_YOUR_DECISION")

    def test_discarded_cards_cannot_be_chosen_as_trash(self):
        """トラッシュにあるカードは選べない（手札のカードだけ）。"""
        state = build_test_state([
            {"active": GROWLITHE, "hand": [COMPUTER_SEARCH, FIRE, PONYTA], "deck": [WATER], "discard": [BILL]},
            {"active": STARYU},
        ], turn_number=TURN)
        pending = self.play(state)
        trash = state.players[0].discard[0]
        self.assert_rejected(pending, ResolveDecision(0, pending.decision.id, (trash, pending.decision.options[0])), "INVALID_CHOICE")


class SearchStageTest(Base):
    """段階 2（CS11〜CS16）: 使ったプレイヤーが山札から 1 枚を選び、手札に加え、その山札を切る。"""

    def at_search(self, deck=(WATER, SEEL, BILL, FIRE, DEWGONG)):
        state = board((FIRE, PONYTA), deck=deck)
        pending = self.play(state)
        return state, self.answer(pending, pending.decision.options)

    def test_decision_shape(self):
        state, searching = self.at_search()
        d = searching.decision
        self.assertEqual((d.player, d.kind, d.resume, d.min_choices, d.max_choices), (0, SEARCH_DECK, "trainer", 1, 1))
        self.assertEqual(d.options, tuple(sorted(state.players[0].deck)))  # 山札の並びを決定に写さない（uid の小さい順）
        self.assertEqual(searching.trainer_in_use.card, state.players[0].hand[0])

    def test_any_card_and_any_position_can_be_chosen(self):
        """山札の一番上以外のカードも選べ、ポケモン（たね・進化カード）・トレーナー・エネルギーのどれでもよい（最新の説明「カードを1枚」・
        解説「何でも好きなカード」）。選んだカードは手札に加わり、山札からなくなる。残りの山札は切る（乱数を使う。ログ shuffle）。"""
        state, searching = self.at_search()
        deck = state.players[0].deck
        for card_id in (WATER, SEEL, BILL, DEWGONG):
            with self.subTest(card=card_id):
                target = by_id(searching, 0, "deck", card_id)[0]
                done = self.answer(searching, (target,))
                q = done.players[0]
                self.assertIn(target, q.hand)
                self.assertNotIn(target, q.deck)
                self.assertEqual(Counter(q.deck), Counter(u for u in deck if u != target))
                self.assertEqual([e["kind"] for e in done.log[-3:]], ["search_deck", "shuffle", "discard_trainer"])
                self.assertNotEqual(rng_fingerprint(done.rng), rng_fingerprint(searching.rng))
                self.assertEqual((done.phase, done.current_player, done.turn_number), (Phase.MAIN, 0, TURN))
        self.assertNotEqual(by_id(searching, 0, "deck", DEWGONG)[0], deck[0])  # 一番上ではないカード

    def test_invalid_choices_keep_the_discards_and_the_decision(self):
        """手札・トラッシュ（段階 1 でトラッシュしたカード）・使用中のこのカード・相手の山札・0 枚・2 枚は拒否。段階 1 のトラッシュは取り消さず、
        決定を待ったまま、このカードは使用中のまま、乱数は変わらない。"""
        pending = self.play(board((FIRE, PONYTA, POTION)))
        searching = self.answer(pending, pending.decision.options[:2])  # 手札にきずぐすりが残る
        d = searching.decision
        q = searching.players[0]
        self.assertEqual(len(q.hand), 1)
        wrong = [((q.hand[0],), "INVALID_CHOICE"), ((q.discard[0],), "INVALID_CHOICE"),
                 ((searching.trainer_in_use.card,), "INVALID_CHOICE"), ((searching.players[1].deck[0],), "INVALID_CHOICE"),
                 ((), "INVALID_CHOICE_COUNT"), ((d.options[0], d.options[1]), "INVALID_CHOICE_COUNT")]
        for choices, code in wrong:
            with self.subTest(choices=choices):
                self.assert_rejected(searching, ResolveDecision(0, d.id, choices), code)
                self.assertEqual(searching.decision, d)
                self.assertEqual(len(searching.players[0].discard), 2)
                self.assertEqual(searching.trainer_in_use.card, pending.trainer_in_use.card)
                self.assert_conserved(searching)
        self.assert_rejected(searching, ResolveDecision(1, d.id, d.options[:1]), "NOT_YOUR_DECISION")

    def test_deck_of_one(self):
        """山札が 1 枚: 選べるのはその 1 枚（決定は出す）。選ぶと山札は 0 枚。「カードを引く」ではないので負けではなく、番は続く。0 枚の山札を
        切っても乱数は使わない。"""
        state, searching = self.at_search(deck=(DEWGONG,))
        self.assertEqual(searching.decision.options, tuple(state.players[0].deck))
        done = self.answer(searching, searching.decision.options)
        self.assertEqual((done.players[0].deck, done.phase, done.result), ([], Phase.MAIN, None))
        self.assertEqual(rng_fingerprint(done.rng), rng_fingerprint(searching.rng))
        self.assertEqual(done.log[-2]["kind"], "shuffle")

    def test_same_seed_and_commands_give_the_same_result(self):
        """同じ盤面（seed）・同じ操作の列なら同じ結果（切った山札の並び・乱数を含む）。"""
        results = []
        for _ in range(2):
            state, searching = self.at_search()
            results.append(snapshot(self.answer(searching, (by_id(searching, 0, "deck", BILL)[0],))))
        self.assertEqual(results[0], results[1])

    def test_hidden_information_stays_out_of_the_log(self):
        """山札の中身（決定の選べるもの）はログに書かない。選んだカードは search_deck の card（選んだプレイヤーだけが見る項目）だけに書き、
        shuffle は誰の山札かだけ。トラッシュした 2 枚（discard_from_hand の cards）は公開。"""
        state, searching = self.at_search()
        options = searching.decision.options
        target = options[2]
        done = self.answer(searching, (target,))
        events = [dict(e) for e in done.log[len(state.log):]]
        self.assertEqual([e["kind"] for e in events], ["play_trainer", "discard_from_hand", "search_deck", "shuffle", "discard_trainer"])
        search, shuffle = events[2], events[3]
        self.assertEqual(set(search), {"kind", "turn", "player", "card"})
        self.assertEqual(set(shuffle), {"kind", "turn", "player"})
        # カードを書く項目（card・cards）に、選ばなかった山札のカードがない
        others = {u for u in options if u != target}
        for e in events:
            written = set(e.get("cards", ())) | ({e["card"]} if "card" in e else set())
            self.assertTrue(others.isdisjoint(written), e)

    def test_pending_search_survives_copy_and_pickle(self):
        state, searching = self.at_search()
        command = ResolveDecision(0, searching.decision.id, (searching.decision.options[1],))
        expected = snapshot(apply_command(searching, command))
        for copied in (searching.clone(), copy.deepcopy(searching), pickle.loads(pickle.dumps(searching))):
            self.assertEqual(snapshot(apply_command(copied, command)), expected)


class AfterResolutionTest(Base):
    """解決後（CS17〜CS20）。"""

    def test_turn_continues_and_the_searched_card_can_be_used(self):
        """このカードは効果のあとにトラッシュし、番は続く。選んだ進化カードで、その番に進化できる（通常の操作を続けられる）。"""
        state = board((FIRE, PONYTA), deck=(WATER, DEWGONG, BILL), active=SEEL)
        card = state.players[0].hand[0]
        pending = self.play(state)
        searching = self.answer(pending, pending.decision.options)
        dewgong = by_id(searching, 0, "deck", DEWGONG)[0]
        done = self.answer(searching, (dewgong,))
        self.assertEqual(done.log[-1]["kind"], "discard_trainer")
        self.assertIn(card, done.players[0].discard)
        self.assertIsNone(done.trainer_in_use)
        evolved = apply_command(done, EvolvePokemon(0, dewgong, done.players[0].active.pokemon_id))
        self.assertEqual(evolved.players[0].active.card, dewgong)

    def test_another_computer_search_in_the_same_turn(self):
        """同じ番に 2 枚目を使える（p.310。何枚でも）。1 枚目のトラッシュする手札に、もう 1 枚のパソコン通信を選ぶこともできる。"""
        state = board((COMPUTER_SEARCH, FIRE, PONYTA, POTION), deck=(WATER, SEEL, BILL))
        pending = self.play(state)
        second = state.players[0].hand[1]
        searching = self.answer(pending, (pending.decision.options[2], pending.decision.options[3]))
        done = self.answer(searching, (searching.decision.options[0],))
        again = self.play_again(done, second)
        self.assertEqual(again.decision.kind, DISCARD_FROM_HAND)
        # もう 1 枚をトラッシュに選ぶ場合
        pending = self.play(state)
        searching = self.answer(pending, (second, pending.decision.options[1]))
        self.assertIn(second, searching.players[0].discard)

    def play_again(self, state, card):
        new = apply_command(state, PlayTrainer(0, card))
        self.assert_conserved(new)
        return new

    def test_empty_deck_after_search_loses_only_at_the_next_draw(self):
        """選び出して山札が 0 枚になっても、その場では負けではない。負けるのは次の自分の番の最初に引けないとき（p.309・p.312）。"""
        state = board((FIRE, PONYTA), deck=(WATER,))
        pending = self.play(state)
        searching = self.answer(pending, pending.decision.options)
        done = self.answer(searching, searching.decision.options)
        attached = apply_command(done, AttachEnergy(0, by_id(done, 0, "hand", WATER)[0], done.players[0].active.card))
        self.assertEqual(attached.phase, Phase.MAIN)
        theirs = apply_command(attached, EndTurn(0))
        self.assertEqual(theirs.result, None)
        mine = apply_command(theirs, EndTurn(1))
        self.assertEqual(mine.phase, Phase.GAME_OVER)
        self.assertEqual(mine.result.winner, 1)


class NaturalGamesTest(unittest.TestCase):
    """正式な対戦開始（``new_game``・60 枚・サイド 6 枚）から、v0.20 の固定のデッキのディフェンダー 3 枚をパソコン通信 3 枚に置き換えた一時的な
    デッキで、席を入れかえて 6 局ずつ（tools/preset_deck_games.py の ``--variant computer``）。パソコン通信を山札から引き、使うための条件を
    満たして使い、手札を 2 枚選んでトラッシュし、山札から選んだカードをその番に使った場面が自然に起こることを確かめる（盤面は作らない）。"""

    GAMES = 6

    @classmethod
    def setUpClass(cls):
        cls.results = driver.run(cls.GAMES, keep_state=True, variant="computer")

    def test_presets_are_unchanged(self):
        """公開の固定のデッキは変えていない。一時的なデッキは 60 枚・ディフェンダー 1 枚・パソコン通信 3 枚。突風の変種もそのまま。"""
        for deck_id in (driver.DECK_A, driver.DECK_B):
            with self.subTest(deck=deck_id):
                self.assertNotIn(COMPUTER_SEARCH, preset_deck(deck_id).counts())
                self.assertEqual(preset_deck(deck_id).counts()[DEFENDER], 4)
                cards = Counter(driver.deck_cards(deck_id, "computer"))
                self.assertEqual((sum(cards.values()), cards[COMPUTER_SEARCH], cards[DEFENDER]), (60, 3, 1))
                self.assertEqual(Counter(driver.deck_cards(deck_id, "gust"))[driver.GUST], 3)

    def test_computer_search_is_drawn_used_and_followed_up(self):
        uses = [u for r in self.results for u in r["computer_uses"]]
        self.assertTrue(uses)
        self.assertTrue(all(len(u["discarded"]) == 2 and "searched" in u and u["shuffled"] for u in uses))
        self.assertTrue(any(u.get("used_same_turn") for u in uses))  # 選んだカードをその番の展開・攻撃の準備に使った
        self.assertGreaterEqual(len({u["used_as"] for u in uses if "used_as" in u}), 2)
        origins = Counter()
        for r in self.results:
            state = r["state"]
            for i, e in enumerate(state.log):
                if e["kind"] == "play_trainer" and state.cards[e["card"]].card_id == COMPUTER_SEARCH:
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
        for r in self.results:
            state = r["state"]
            with self.subTest(seed=r["seed"], decks=r["decks"]):
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])
                self.assertFalse(r["unresolved_rejections"])  # 手順は山札が 0 枚のときに使わないので、CS6 で拒否されない


if __name__ == "__main__":
    unittest.main()
