"""v0.24: ポケモン交換おじさん（PMCG1-093）。最新の説明「手札から「たねポケモン」または「進化カード」を1枚選び、相手プレイヤーに見せてから、
あなたの山札にもどす。それができないとき、このカードは使えない。あなたの山札から「たねポケモン」または「進化カード」を1枚選び出し、相手
プレイヤーに見せてから、手札に加える。その後、その山札をよく切る。」（『ポケモンカードオフィシャルブック2000』p.259。
docs/pokemon-trader-v0.24.md）。

規定と根拠（docs/pokemon-trader-v0.24.md 3 章の PT1〜PT19）:

- 使うための条件（PT2・PT3）: このカードを除く手札にたねポケモン・進化カードがなければ使えない（p.259「それができないとき、このカードは
  使えない」）。山札の中身（見えない情報）は条件にしない。
- 段階 1（PT4〜PT8）: 使ったプレイヤーが手札のたねポケモン・進化カードを 1 枚選び、相手に見せてから山札にもどす（公開。トラッシュでは
  ない）。段階 2（PT9〜PT13）: 山札のたねポケモン・進化カード（もどしたカードを含む）から 1 枚を選び出し、相手に見せてから手札に加え（公開。
  選べたほかの山札のカードは非公開）、その山札を切る。山札にポケモンのカードがない・山札が 0 枚なら、もどしたカードを持ってくる（p.259 の
  解説「山札の中にポケモンのカードがなかったら、交換のために入れたポケモンカードを持ってくることになります」）。
- 解決後（PT16・PT17）: このカードをトラッシュし、番は続く。手に入れたカードでベンチに出す・進化するのは通常の規定のまま（p.310）。

kyuura の記録: kyuura（研究の基準 3f34908）に、このカードの照合の記録（CC-）・最新の説明（LD-）・p.259 のページの記録はない（報告事項。
research_links.json の engine_verified_without_kyuura_record）。

盤面を直接作るテスト（``build_test_state``。規定 1 か所ずつ）と、正式な対戦開始（``new_game``・60 枚・サイド 6 枚）から使う統合テスト
（v0.23 の ``retrieval`` の一時的なデッキからさらに残りのきずぐすり 2 枚をポケモン交換おじさん 2 枚に置き換えた ``trader``。
tools/preset_deck_games.py）を分けている。
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
    EvolvePokemon, PlayBasicToBench, PlayTrainer, ResolveDecision, apply_command, check_invariants, preset_deck,
)
from kyuura_engine.cards import load_card_pool, read_verification
from kyuura_engine.decisions import RETURN_TO_DECK, SEARCH_DECK
from kyuura_engine.effects import DEFAULT_EFFECTS, TradePokemonWithDeck
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import (
    BILL, BULBASAUR, DEWGONG, ENERGY_RETRIEVAL, FIRE, GROWLITHE, IVYSAUR, POKEMON_TRADER, PONYTA, POTION, SEEL, STARYU, VENUSAUR,
    WATER, build_test_state,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_computer_search_v0_22 import Base, by_id, snapshot

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import preset_deck_games as driver  # noqa: E402

LATEST = (
    "手札から「たねポケモン」または「進化カード」を1枚選び、相手プレイヤーに見せてから、あなたの山札にもどす。それができないとき、このカードは"
    "使えない。あなたの山札から「たねポケモン」または「進化カード」を1枚選び出し、相手プレイヤーに見せてから、手札に加える。その後、その山札を"
    "よく切る。"
)
PRINTED = (
    "自分の山札から好きなポケモンカードか進化カードを1枚選んで、手札のポケモンカードか進化カードと交換することができる。そのあとで、自分の山札を"
    "よくきる。交換するカードは相手に見せなければならない。"
)
TURN = 5  # 自分（プレイヤー 0）の番


def board(hand=(DEWGONG, FIRE), deck=(WATER, SEEL, BILL, BULBASAUR, IVYSAUR), *, active=GROWLITHE, bench=(), turn_number=TURN):
    """自分（プレイヤー 0）の番の MAIN。手札の先頭がポケモン交換おじさん。"""
    return build_test_state([
        {"active": active, "bench": list(bench), "hand": [POKEMON_TRADER, *hand], "deck": list(deck), "discard": [WATER]},
        {"active": STARYU, "bench": [SEEL], "hand": [WATER, PONYTA], "deck": [WATER, SEEL]},
    ], turn_number=turn_number)


def is_pokemon_card(state, uid):
    d = state.card_def(uid)
    return d.is_basic_pokemon or d.is_evolution_pokemon


class RegistrationTest(unittest.TestCase):
    def test_entry_follows_the_verified_latest_description(self):
        """登録は（カード id で）1 件。照合した写しの文面（第1弾の印刷。図版と同じ）と、実装がしたがう最新の説明（p.259）を分けて持つ。"""
        entry = DEFAULT_EFFECTS.trainer_entry(POKEMON_TRADER)
        self.assertEqual(entry.effect, TradePokemonWithDeck())
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), ("ポケモン交換おじさん", PRINTED, LATEST, "P43 p.259"))
        definition = load_card_pool().get(POKEMON_TRADER)
        self.assertTrue(definition.supported)
        self.assertEqual(definition.trainer_text_ja, PRINTED)
        record = read_verification()["cards"][POKEMON_TRADER]
        self.assertEqual((record["page"], record["pdf_page"], record["checked_on"]), (259, 261, "2026-10-15"))
        self.assertEqual((record["card_image_text_ja"], record["latest_description_ja"]), (PRINTED, LATEST))
        self.assertEqual(record["status"], "不一致あり")  # 最新の説明が印刷の文面（写し・図版）と違う（書き方の違いで誤りではない）

    def test_no_card_specific_branch_in_the_engine(self):
        """engine.py・resolution/ にこのカードの id・実装での分岐を加えていない（既存のトレーナーの登録・決定・ゾーンの関数で扱う）。v0.38 から、見せて
        手札に加えるゾーンの関数 ``reveal_deck_to_hand`` は、ワザの要素（キョウのポッポの「でんれい」。``programs.RevealPokemonFromDeck``）も使う（共通の
        関数。このカードの処理ではない）ので、programs.py のその要素の中だけを許す。v0.44 から、ワザの要素 ``RevealTrainerFromDeck``（ニャースの「ねこのて」）・
        ``ReturnHandThenRevealEnergy``（_____のラッキーの「ラッキーたまご」）も同じ共通の関数を使うので、その 3 つの要素の中だけを許す（どれも 1 か所）。"""
        for path in [ROOT / "kyuura_engine" / "engine.py", *(ROOT / "kyuura_engine" / "resolution").glob("*.py")]:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(POKEMON_TRADER, text)
                self.assertIsNone(re.search(r"TradePokemonWithDeck|RETURN_TO_DECK|return_hand_to_deck", text))
                uses = [m.start() for m in re.finditer(r"reveal_deck_to_hand\(", text)]
                if path.name == "programs.py":
                    # v0.75: カスミのメノクラゲの「くらげのむれ」（``RevealNamedPokemonFromDeck``）も同じ共通の関数を使う
                    elements = ("RevealPokemonFromDeck", "RevealTrainerFromDeck", "ReturnHandThenRevealEnergy", "RevealNamedPokemonFromDeck")
                    spans = []
                    for name in elements:
                        start = text.index(f"class {name}(")
                        end = min(i for i in (text.find("\nclass ", start + 1), text.find("BUILDERS: dict", start)) if i > 0)
                        spans.append((start, end))
                        self.assertEqual(sum(start < use < end for use in uses), 1, name)
                    self.assertEqual(len(uses), len(elements))
                    self.assertTrue(all(any(start < use < end for start, end in spans) for use in uses))
                else:
                    self.assertEqual(uses, [])


class UsableTest(Base):
    """使うための条件（PT2・PT3）と、山札にポケモンのカードがない・山札が 0 枚のとき（PT10・PT11）。"""

    def test_hand_without_pokemon_cards_cannot_use_it(self):
        """このカードを除く手札にたねポケモン・進化カードがなければ使えない（p.259「それができないとき、このカードは使えない」）。手札が
        このカードだけ・トレーナーとエネルギーだけ（もう 1 枚のポケモン交換おじさんを含む）。拒否してもカードは手札に残り、状態・乱数・ログは
        変わらない。"""
        for hand in ((), (FIRE, BILL, POKEMON_TRADER)):
            with self.subTest(hand=hand):
                state = board(hand=hand)
                card = state.players[0].hand[0]
                self.assert_rejected(state, PlayTrainer(0, card), "NO_POKEMON_CARD_IN_HAND")
                self.assertIn(card, state.players[0].hand)
                self.assertIsNone(state.trainer_in_use)

    def test_one_basic_or_one_evolution_card_is_enough(self):
        """手札のたねポケモン 1 枚・進化カード（1 進化・2 進化）1 枚のどれでも使える。"""
        for card_id in (PONYTA, DEWGONG, VENUSAUR):
            with self.subTest(card=card_id):
                state = board(hand=(card_id, FIRE))
                pending = self.play(state)
                self.assertEqual(pending.decision.options, (state.players[0].hand[1],))

    def test_deck_contents_are_not_a_condition(self):
        """山札の中身（見えない情報）は使うための条件ではない。山札にポケモンのカードがない・山札が 0 枚でも使え、もどしたカードが山札に入るので、
        選べるのはそのカードだけ（p.259 の解説）。山札が 0 枚なら手に入れたあと 0 枚で、切っても乱数を使わない。"""
        for deck in ((WATER, BILL), ()):
            with self.subTest(deck=deck):
                state = board(hand=(PONYTA,), deck=deck)
                pending = self.play(state)
                ponyta = state.players[0].hand[1]
                searching = self.answer(pending, (ponyta,))
                self.assertEqual(searching.decision.options, (ponyta,))
                done = self.answer(searching, (ponyta,))
                self.assertIn(ponyta, done.players[0].hand)
                self.assertEqual(Counter(done.players[0].deck), Counter(state.players[0].deck))
                if not deck:
                    self.assertEqual(rng_fingerprint(done.rng), rng_fingerprint(state.rng))

    def test_other_rejections_do_not_change_state(self):
        """番でないプレイヤー・手札にないカード・決定を待つ間の宣言は拒否し、状態は変わらない。"""
        state = board(hand=(DEWGONG, POKEMON_TRADER))
        first, second = state.players[0].hand[0], state.players[0].hand[2]
        self.assert_rejected(state, PlayTrainer(1, first), "NOT_YOUR_TURN")
        self.assert_rejected(state, PlayTrainer(0, state.players[0].deck[0]), "CARD_NOT_IN_HAND")
        pending = self.play(state)
        self.assert_rejected(pending, PlayTrainer(0, second), "WRONG_PHASE")


class ReturnStageTest(Base):
    """段階 1（PT4〜PT8）: 使ったプレイヤーが手札のたねポケモン・進化カードから 1 枚を選び、相手に見せてから山札にもどす。"""

    def setUp(self):
        self.state = board(hand=(DEWGONG, FIRE, BILL, PONYTA))
        self.card = self.state.players[0].hand[0]
        self.pending = self.play(self.state)

    def test_decision_shape_and_card_in_use(self):
        d = self.pending.decision
        hand = self.state.players[0].hand
        self.assertEqual((d.player, d.kind, d.resume, d.min_choices, d.max_choices), (0, RETURN_TO_DECK, "trainer", 1, 1))
        self.assertEqual(d.context_value("use"), (0, self.card, POKEMON_TRADER))
        self.assertEqual(d.options, (hand[1], hand[4]))  # ジュゴン・ポニータ（手札の並び）。炎エネルギー・マサキ・このカードは選べない
        self.assertEqual((self.pending.trainer_in_use.player, self.pending.trainer_in_use.card), (0, self.card))

    def test_returned_card_goes_to_the_deck_and_is_shown(self):
        """選んだカードは手札から山札（一番下）に移る（トラッシュではない）。ログ return_to_deck の card は公開。乱数を使わない。"""
        dewgong = self.pending.decision.options[0]
        searching = self.answer(self.pending, (dewgong,))
        q = searching.players[0]
        self.assertNotIn(dewgong, q.hand)
        self.assertEqual(q.deck[-1], dewgong)
        self.assertNotIn(dewgong, q.discard)
        self.assertEqual(dict(searching.log[-1]), {"kind": "return_to_deck", "turn": TURN, "player": 0, "card": dewgong})
        self.assertEqual(rng_fingerprint(searching.rng), rng_fingerprint(self.state.rng))
        self.assertEqual(searching.decision.kind, SEARCH_DECK)

    def test_invalid_choices_keep_the_decision(self):
        """使っているこのカード・手札のエネルギーとトレーナー・山札・トラッシュ・相手の手札・自分の場・0 枚・2 枚は拒否し、決定を待ったまま、
        このカードは使用中のまま。使ったプレイヤー以外の答えも拒否。"""
        d = self.pending.decision
        p0, p1 = self.pending.players
        wrong = [
            ((self.card,), "INVALID_CHOICE"),
            ((by_id(self.pending, 0, "hand", FIRE)[0],), "INVALID_CHOICE"),
            ((by_id(self.pending, 0, "hand", BILL)[0],), "INVALID_CHOICE"),
            ((by_id(self.pending, 0, "deck", SEEL)[0],), "INVALID_CHOICE"),
            ((p0.discard[0],), "INVALID_CHOICE"),
            ((by_id(self.pending, 1, "hand", PONYTA)[0],), "INVALID_CHOICE"),
            ((p0.active.card,), "INVALID_CHOICE"),
            ((), "INVALID_CHOICE_COUNT"),
            (d.options[:2], "INVALID_CHOICE_COUNT"),
        ]
        for choices, code in wrong:
            with self.subTest(choices=choices):
                self.assert_rejected(self.pending, ResolveDecision(0, d.id, choices), code)
                self.assertEqual(self.pending.decision, d)
                self.assertEqual(self.pending.trainer_in_use.card, self.card)
                self.assert_conserved(self.pending)
        self.assert_rejected(self.pending, ResolveDecision(1, d.id, d.options[:1]), "NOT_YOUR_DECISION")


class SearchStageTest(Base):
    """段階 2（PT9〜PT15）: 使ったプレイヤーが山札のたねポケモン・進化カード（もどしたカードを含む）から 1 枚を選び出し、相手に見せてから
    手札に加え、その山札を切る。"""

    def at_search(self, hand=(SEEL, FIRE), deck=(WATER, SEEL, BILL, BULBASAUR, IVYSAUR, VENUSAUR, DEWGONG)):
        state = board(hand=hand, deck=deck)
        pending = self.play(state)
        returned = pending.decision.options[0]
        return state, returned, self.answer(pending, (returned,))

    def test_decision_shape(self):
        """選べるのは山札のたねポケモン・進化カード（uid の小さい順。もどしたカードを含む）。エネルギー・トレーナーは選べるものにない。"""
        state, returned, searching = self.at_search()
        d = searching.decision
        self.assertEqual((d.player, d.kind, d.resume, d.min_choices, d.max_choices), (0, SEARCH_DECK, "trainer", 1, 1))
        self.assertEqual(d.context_value("returned"), returned)
        expected = tuple(sorted(u for u in searching.players[0].deck if is_pokemon_card(searching, u)))
        self.assertEqual(d.options, expected)
        self.assertIn(returned, d.options)
        self.assertTrue(all(is_pokemon_card(searching, u) for u in d.options))
        self.assertEqual(len(d.options), 6)  # パウワウ・フシギダネ・フシギソウ・フシギバナ・ジュゴン・もどしたパウワウ

    def test_basic_and_evolution_cards_at_any_position_can_be_taken(self):
        """たねポケモン・1 進化・2 進化のどれでも、山札のどの位置でも選び出せる（解説「進化ポケモンだけでなくたねポケモンも持ってこられる」）。
        手札に加え、山札からなくなり、残りの山札（もどしたカードを含む）を切る。ログ reveal_from_deck の card は公開。"""
        state, returned, searching = self.at_search()
        for card_id in (BULBASAUR, IVYSAUR, VENUSAUR):
            with self.subTest(card=card_id):
                target = by_id(searching, 0, "deck", card_id)[0]
                done = self.answer(searching, (target,))
                q = done.players[0]
                self.assertIn(target, q.hand)
                self.assertNotIn(target, q.deck)
                self.assertIn(returned, q.deck)
                self.assertEqual(Counter(q.deck), Counter(u for u in searching.players[0].deck if u != target))
                self.assertEqual([e["kind"] for e in done.log[-3:]], ["reveal_from_deck", "shuffle", "discard_trainer"])
                self.assertEqual(done.log[-3]["card"], target)
                self.assertNotEqual(rng_fingerprint(done.rng), rng_fingerprint(searching.rng))
                self.assertEqual((done.phase.value, done.current_player, done.turn_number), ("main", 0, TURN))

    def test_returned_card_and_another_card_with_the_same_name(self):
        """もどしたカード自身を選べる（ほかに選べるものがあっても。山札に入ったカード）。同じ名前の別のカード（山札のパウワウ）も選べる。
        どちらも別のカードとして扱う。"""
        state, returned, searching = self.at_search()
        other = [u for u in by_id(searching, 0, "deck", SEEL) if u != returned]
        self.assertEqual(len(other), 1)
        for target in (returned, other[0]):
            with self.subTest(target=target):
                done = self.answer(searching, (target,))
                self.assertIn(target, done.players[0].hand)
                self.assertEqual(sorted(by_id(done, 0, "deck", SEEL) + by_id(done, 0, "hand", SEEL)), sorted([returned, other[0]]))

    def test_invalid_choices_keep_the_returned_card_in_the_deck(self):
        """山札のエネルギー・トレーナー・手札・トラッシュ・相手の山札・使用中のこのカード・0 枚・2 枚・相手の答えを拒否。段階 1（山札にもどした
        こと）は取り消さず、決定を待ったまま、このカードは使用中のまま。"""
        state, returned, searching = self.at_search()
        d = searching.decision
        q, them = searching.players
        wrong = [((by_id(searching, 0, "deck", WATER)[0],), "INVALID_CHOICE"), ((by_id(searching, 0, "deck", BILL)[0],), "INVALID_CHOICE"),
                 ((q.hand[0],), "INVALID_CHOICE"), ((q.discard[0],), "INVALID_CHOICE"), ((by_id(searching, 1, "deck", SEEL)[0],), "INVALID_CHOICE"),
                 ((searching.trainer_in_use.card,), "INVALID_CHOICE"), ((), "INVALID_CHOICE_COUNT"), (d.options[:2], "INVALID_CHOICE_COUNT")]
        for choices, code in wrong:
            with self.subTest(choices=choices):
                self.assert_rejected(searching, ResolveDecision(0, d.id, choices), code)
                self.assertEqual(searching.decision, d)
                self.assertIn(returned, searching.players[0].deck)
                self.assertNotIn(returned, searching.players[0].hand)
                self.assert_conserved(searching)
        self.assert_rejected(searching, ResolveDecision(1, d.id, d.options[:1]), "NOT_YOUR_DECISION")

    def test_shown_cards_and_hidden_deck(self):
        """見せるカード（もどしたカード・手に入れたカード）だけをログに書く。山札の中身（決定の選べるもの）はログに書かない。shuffle は誰の
        山札かだけ。"""
        state, returned, searching = self.at_search()
        options = searching.decision.options
        target = by_id(searching, 0, "deck", IVYSAUR)[0]
        done = self.answer(searching, (target,))
        events = [dict(e) for e in done.log[len(state.log):]]
        self.assertEqual([e["kind"] for e in events], ["play_trainer", "return_to_deck", "reveal_from_deck", "shuffle", "discard_trainer"])
        self.assertEqual((events[1], events[2], events[3]), (
            {"kind": "return_to_deck", "turn": TURN, "player": 0, "card": returned},
            {"kind": "reveal_from_deck", "turn": TURN, "player": 0, "card": target},
            {"kind": "shuffle", "turn": TURN, "player": 0}))
        others = {u for u in options if u not in (target, returned)} | {u for u in state.players[0].deck if not is_pokemon_card(state, u)}
        for e in events:
            written = set(e.get("cards", ())) | ({e["card"]} if "card" in e else set())
            self.assertTrue(others.isdisjoint(written), e)

    def test_same_seed_and_commands_give_the_same_result(self):
        """同じ盤面（seed）・同じ操作の列なら同じ結果（切った山札の並び・乱数を含む）。"""
        results = []
        for _ in range(2):
            state, returned, searching = self.at_search()
            results.append(snapshot(self.answer(searching, (by_id(searching, 0, "deck", BULBASAUR)[0],))))
        self.assertEqual(results[0], results[1])

    def test_pending_search_survives_copy_and_pickle(self):
        state, returned, searching = self.at_search()
        command = ResolveDecision(0, searching.decision.id, (searching.decision.options[1],))
        expected = snapshot(apply_command(searching, command))
        for copied in (searching.clone(), copy.deepcopy(searching), pickle.loads(pickle.dumps(searching))):
            self.assertEqual(snapshot(apply_command(copied, command)), expected)


class AfterResolutionTest(Base):
    """解決後（PT16・PT17）。手に入れたカードは手札のカードで、ベンチに出す・進化するのは通常の規定のまま（p.310）。"""

    def trade(self, state, give, take):
        pending = self.play(state)
        searching = self.answer(pending, (by_id(pending, 0, "hand", give)[0],))
        return self.answer(searching, (by_id(searching, 0, "deck", take)[0],))

    def test_take_an_evolution_card_and_evolve(self):
        """手に入れたジュゴンで、その番の最初から場にいるパウワウを進化できる。このカードはトラッシュに置かれ、番は続く。"""
        state = board(hand=(PONYTA,), deck=(WATER, DEWGONG), active=SEEL)
        card = state.players[0].hand[0]
        done = self.trade(state, PONYTA, DEWGONG)
        self.assertIn(card, done.players[0].discard)
        self.assertIsNone(done.trainer_in_use)
        dewgong = by_id(done, 0, "hand", DEWGONG)[0]
        evolved = apply_command(done, EvolvePokemon(0, dewgong, done.players[0].active.pokemon_id))
        self.assertEqual(evolved.players[0].active.card, dewgong)
        self.assertEqual(check_invariants(evolved), [])

    def test_take_a_basic_and_play_it_to_the_bench(self):
        """手に入れたたねポケモンをベンチに出せる（余った進化カードをもどした場合）。"""
        state = board(hand=(VENUSAUR,), deck=(WATER, BULBASAUR))
        done = self.trade(state, VENUSAUR, BULBASAUR)
        bulbasaur = by_id(done, 0, "hand", BULBASAUR)[0]
        benched = apply_command(done, PlayBasicToBench(0, bulbasaur))
        self.assertEqual(benched.players[0].bench[-1].card, bulbasaur)

    def test_evolution_limits_still_apply(self):
        """交換で手に入れた進化カードでも、進化の通常の制限は変わらない: その番に場に出したポケモン（PLAYED_THIS_TURN）・最初の番
        （FIRST_TURN_EVOLUTION）は進化できない（p.310）。"""
        state = board(hand=(SEEL, PONYTA), deck=(WATER, DEWGONG))
        benched = apply_command(state, PlayBasicToBench(0, by_id(state, 0, "hand", SEEL)[0]))
        done = self.trade(benched, PONYTA, DEWGONG)
        dewgong = by_id(done, 0, "hand", DEWGONG)[0]
        self.assert_rejected(done, EvolvePokemon(0, dewgong, done.players[0].bench[-1].pokemon_id), "PLAYED_THIS_TURN")
        first = board(hand=(PONYTA,), deck=(WATER, DEWGONG), active=SEEL, turn_number=1)
        done = self.trade(first, PONYTA, DEWGONG)
        dewgong = by_id(done, 0, "hand", DEWGONG)[0]
        self.assert_rejected(done, EvolvePokemon(0, dewgong, done.players[0].active.pokemon_id), "FIRST_TURN_EVOLUTION")

    def test_second_trader_in_the_same_turn(self):
        """同じ番に 2 枚目を使える（p.310。何枚でも）。"""
        state = board(hand=(POKEMON_TRADER, PONYTA), deck=(WATER, SEEL))
        done = self.trade(state, PONYTA, SEEL)
        again = apply_command(done, PlayTrainer(0, state.players[0].hand[1]))
        self.assert_conserved(again)
        self.assertEqual(again.decision.kind, RETURN_TO_DECK)


class TraderGamesTest(unittest.TestCase):
    """正式な対戦開始（``new_game``・60 枚・サイド 6 枚）から、v0.23 の ``retrieval`` の一時的なデッキからさらに残りのきずぐすり 2 枚をポケモン
    交換おじさん 2 枚に置き換えた一時的なデッキ（``trader``）で、席を入れかえて 6 局ずつ。余った進化カードなどをもどして、たねポケモンを手に
    入れてベンチに出す・進化カードを手に入れて進化する場面が自然に起こる。突風・パソコン通信・エネルギー回収の決定と混ざらない。"""

    GAMES = 6

    @classmethod
    def setUpClass(cls):
        cls.results = driver.run(cls.GAMES, keep_state=True, variant="trader")

    def test_decks(self):
        """公開の固定のデッキは変えていない。一時的なデッキは retrieval からきずぐすり 2 枚 → ポケモン交換おじさん 2 枚（きずぐすり 0 枚）。"""
        for deck_id in (driver.DECK_A, driver.DECK_B):
            with self.subTest(deck=deck_id):
                self.assertNotIn(POKEMON_TRADER, preset_deck(deck_id).counts())
                cards = Counter(driver.deck_cards(deck_id, "trader"))
                expected = Counter(driver.deck_cards(deck_id, "retrieval"))
                expected[POTION] -= 2
                expected[POKEMON_TRADER] += 2
                self.assertEqual(+cards, +expected)
                self.assertEqual((sum(cards.values()), cards[POTION], cards[ENERGY_RETRIEVAL]), (60, 0, 2))

    def test_trader_is_used_and_followed_up(self):
        uses = [u for r in self.results for u in r["trader_uses"]]
        self.assertTrue(uses)
        self.assertTrue(all("returned" in u and "taken" in u and u["shuffled"] for u in uses))
        self.assertTrue(any(u["returned_stage"] in ("stage1", "stage2") for u in uses))  # 余った進化カードをもどした
        self.assertTrue(any(u.get("used_as") == "play_to_bench" and u["used_same_turn"] for u in uses))
        self.assertTrue(any(u.get("used_as") == "evolve" and u["used_same_turn"] for u in uses))
        self.assertTrue(any(u["took_back"] for u in uses))  # もどしたカードを選び直した

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
                self.assertFalse(r["unresolved_rejections"])
        self.assertGreater(checks[f"check_decision_{POKEMON_TRADER}_return_to_deck"], 0)
        self.assertGreater(checks[f"check_decision_{POKEMON_TRADER}_search_deck"], 0)
        self.assertEqual((checks["check_decision_player_mismatch"], checks["check_in_use_mismatch"], checks["check_in_use_left_in_main"]),
                         (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
