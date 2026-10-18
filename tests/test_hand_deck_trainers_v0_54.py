"""v0.54: 手札の入れ替え・ドロー・情報の確認のトレーナー 10 枚（docs/hand-deck-trainers-v0.54.md）。

10 枚: にせオーキドはかせ（PMCG1-089）・にせオーキドの逆襲（PMCG4-059）・ギャンブラー（PMCG3-045）・ナツメの眼（PMCG6-078）・カツラの奥の手（PMCG6-081）・
エリカ（PMCG5-083）・スパイ作戦（PMCG5-088）・カツラのギャンブル（PMCG6-076）・ミニスカート（PMCG1-095）・ポケモン図鑑 HANDY505（PMCG1-082）。どれも kyuura データの採用
（処理に使う文面は kyuura の印刷の文面。採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合（8 枚 match・2 枚は表記の違いだけ）。kyuura の研究の基準の
コミット（3f34908）に、この 10 枚の最新の説明・エラッタ・裁定・論点の記録はない（MIX-SUPPORTER-ERRATA は 2002 年の記録で使わない）。ガイドブックは読んでいない。英語版の文面
（「Show your hand」「shuffles … into」など）・現代のサポーターの規定で、日本語版の条件を補わない。

共通の処理（effects.py）: ``ReturnHandsToDeckTrainer``（手札を山札にもどし、切り、引く 5 枚）・``DrawIfOnlyNamedInHand``・``EachPlayerMayDraw``・
``DiscardFromHandThenDrawTrainer``（スパイ作戦・カツラのギャンブル）・``ArrangeOwnDeckTopTrainer``。ゾーンの関数は既存の ``return_hand_cards_to_deck``・``shuffle_deck``・
``draw_cards``・``discard_from_hand`` と、新しい ``reveal_hand``・``return_revealed_hand_cards_to_deck``・``look_at_hand``。新しい停止コードはない（カツラのギャンブルの
0 枚は v0.31 の HC5 と同じ言い回しの問い）。
"""

from __future__ import annotations

import json
import pathlib
import unittest

from kyuura_engine import (
    IllegalActionError,
    Phase,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    check_invariants,
    observe,
    state_to_dict,
    visible_log,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.decisions import (
    ARRANGE_DECK_TOP,
    DISCARD_FROM_HAND,
    SELECT_DRAW_COUNT,
    SELECT_LOOK_COUNT,
)
from kyuura_engine.observation import OPTION_MEANINGS, PRIVATE_FIELDS, PUBLIC_EVENTS
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests.helpers import (
    BLAINES_GAMBLE,
    BLAINES_LAST_RESORT,
    CLEFAIRY_DOLL,
    DARK_VILEPLUME,
    ERIKA,
    FIGHTING,
    GAMBLER,
    HITMONCHAN,
    IMPOSTER_OAK,
    IMPOSTER_OAKS_REVENGE,
    LASS,
    MYSTERIOUS_FOSSIL,
    POKEDEX,
    POTION,
    RATTATA,
    ROCKET_ODDISH,
    SABRINAS_GAZE,
    SECRET_MISSION,
    V0_54_CARDS,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import (
    hand_deck_problems,
    observation_problems,
    serialization_problems,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "hand-deck-trainers-v0.54.md"
TURN = 7
HC5 = "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO"
EDITIONS = {IMPOSTER_OAK: "082/096", IMPOSTER_OAKS_REVENGE: "055/065", GAMBLER: "045/048", SABRINAS_GAZE: "076/098", BLAINES_LAST_RESORT: "086/098",
            ERIKA: "084/096", SECRET_MISSION: "080/096", BLAINES_GAMBLE: "087/098", LASS: "094/096", POKEDEX: "089/096"}
TYPES = {IMPOSTER_OAK: E.ReturnHandsToDeckTrainer, IMPOSTER_OAKS_REVENGE: E.ReturnHandsToDeckTrainer, GAMBLER: E.ReturnHandsToDeckTrainer,
         SABRINAS_GAZE: E.ReturnHandsToDeckTrainer, BLAINES_LAST_RESORT: E.DrawIfOnlyNamedInHand, ERIKA: E.EachPlayerMayDraw,
         SECRET_MISSION: E.DiscardFromHandThenDrawTrainer, BLAINES_GAMBLE: E.DiscardFromHandThenDrawTrainer, LASS: E.ReturnHandsToDeckTrainer,
         POKEDEX: E.ArrangeOwnDeckTopTrainer}
NOTATION_ONLY = {IMPOSTER_OAKS_REVENGE: "trainer.text.ja", POKEDEX: "name.ja"}  # サイトとの違いは表記だけ（改行・空白）


def board(hand=(), *, deck=None, opponent_hand=(), opponent_deck=None, opponent_active=HITMONCHAN, seed=0):
    me = {"active": HITMONCHAN, "bench": [RATTATA], "hand": list(hand)}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent_active, "bench": [RATTATA], "hand": list(opponent_hand)}
    if opponent_deck is not None:
        them["deck"] = list(opponent_deck)
    return build_test_state([me, them], turn_number=TURN, current_player=0, seed=seed)


def card_of(state, card_id, zone="hand", player=0):
    return next(uid for uid in getattr(state.players[player], zone) if state.cards[uid].card_id == card_id)


def cards_of(state, card_id, zone, player=0):
    return [uid for uid in getattr(state.players[player], zone) if state.cards[uid].card_id == card_id]


def use(state, card_id, player=0):
    return apply_kernel(state, PlayTrainer(player, card_of(state, card_id, player=player)))


def answer(state, choices):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)))


def snapshot(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log], repr(state.rng.getstate())


def since_play(state):
    start = max(i for i, e in enumerate(state.log) if e["kind"] == "play_trainer")
    return state.log[start:]


def kinds(state):
    return [e["kind"] for e in since_play(state)]


def finished(test, state):
    """使い終えた: 使用中のカードがなく、番は続き（同じプレイヤーの MAIN）、カードはトラッシュにあり、1 回ぶんの並び・不変条件・書き出し・観測に問題がない。"""
    test.assertIsNone(state.trainer_in_use)
    test.assertIsNone(state.decision)
    test.assertEqual((state.phase, state.current_player), (Phase.MAIN, 0))
    events = [dict(e) for e in since_play(state)]
    test.assertEqual(events[-1]["kind"], "discard_trainer")
    test.assertIn(events[0]["card"], state.players[0].discard)
    test.assertEqual(hand_deck_problems(state, events), [])
    audited(test, state)


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def assert_stops(test, state, command, code, error=UnsupportedError):
    before = snapshot(state)
    with test.assertRaises(error) as caught:
        apply_kernel(state, command)
    test.assertEqual(caught.exception.code, code)
    test.assertEqual(snapshot(state), before)  # 状態・ログ・乱数は変わらない


def total_cards(state):
    total = sum(len(p.hand) + len(p.deck) + len(p.discard) + len(p.prizes) + sum(len(pk.cards()) + len(pk.energy) + len(pk.trainers) for pk in p.in_play())
                for p in state.players)
    return total + (state.trainer_in_use is not None)


def event(state, kind, player=None):
    return [e for e in since_play(state) if e["kind"] == kind and (player is None or e["player"] == player)]


# ---------------------------------------------------------------- 登録・資料


class RegistrationTest(unittest.TestCase):
    def test_pool_registrations_and_types(self):
        pool = load_card_pool()
        for card_id in V0_54_CARDS:
            with self.subTest(card_id=card_id):
                definition = pool.definitions[card_id]
                self.assertEqual(definition.category, "trainer")
                self.assertTrue(definition.supported)
                entry = E.DEFAULT_EFFECTS.trainer_entry(card_id)
                self.assertIs(type(entry.effect), TYPES[card_id])
                self.assertEqual(entry.text_ja, definition.trainer_text_ja)
                self.assertEqual(entry.play_text_ja, definition.trainer_text_ja)  # 処理に使う文面は kyuura の印刷の文面
                self.assertEqual(entry.effect.check(definition), [])
                self.assertEqual(definition.trainer_kinds, ())
                self.assertFalse(entry.effect.may_knock_out or entry.effect.empties_active or entry.effect.enters_play or entry.effect.stays_in_play)
        extract = json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text())
        self.assertEqual(extract["pool_v0_54"], list(V0_54_CARDS))

    def test_registration_rejects_text_mismatches(self):
        """登録の値（もどすプレイヤー・もどすカード・見せるか・引く枚数の決め方・コイン・使うための条件）が文面と合わなければ ``check`` が拒否する。"""
        d = load_card_pool().definitions
        wrong = [
            (IMPOSTER_OAK, E.ReturnHandsToDeckTrainer(E.IMPOSTER_OAK_TEXT, E.HANDS_SELF, draw=7)),
            (IMPOSTER_OAK, E.ReturnHandsToDeckTrainer(E.IMPOSTER_OAK_TEXT, E.HANDS_OPPONENT, draw=4)),
            (IMPOSTER_OAKS_REVENGE, E.ReturnHandsToDeckTrainer(E.IMPOSTER_OAKS_REVENGE_TEXT, E.HANDS_OPPONENT, draw=4)),  # 使うための条件
            (GAMBLER, E.ReturnHandsToDeckTrainer(E.GAMBLER_TEXT, E.HANDS_SELF, coin_draws=(1, 8))),
            (GAMBLER, E.ReturnHandsToDeckTrainer(E.GAMBLER_TEXT, E.HANDS_SELF, draw=8)),
            (SABRINAS_GAZE, E.ReturnHandsToDeckTrainer(E.SABRINAS_GAZE_TEXT, E.HANDS_BOTH, draw=5)),
            (LASS, E.ReturnHandsToDeckTrainer(E.LASS_TEXT, E.HANDS_BOTH, returns="trainers")),  # 見せ合う
            (LASS, E.ReturnHandsToDeckTrainer(E.LASS_TEXT, E.HANDS_BOTH, returns="all", reveal=True)),
            (BLAINES_LAST_RESORT, E.DrawIfOnlyNamedInHand(E.BLAINES_LAST_RESORT_TEXT, "カツラの奥の手", 4)),
            (ERIKA, E.EachPlayerMayDraw(E.ERIKA_TEXT, 2)),
            (SECRET_MISSION, E.DiscardFromHandThenDrawTrainer(E.SECRET_MISSION_TEXT, optional=True)),  # 相手の手札を見る
            (SECRET_MISSION, E.DiscardFromHandThenDrawTrainer(E.SECRET_MISSION_TEXT, look_opponent_hand=True)),  # のぞむなら
            (BLAINES_GAMBLE, E.DiscardFromHandThenDrawTrainer(E.BLAINES_GAMBLE_TEXT, multiplier=1, coin=True)),
            (BLAINES_GAMBLE, E.DiscardFromHandThenDrawTrainer(E.BLAINES_GAMBLE_TEXT, multiplier=2, coin=True, optional=True)),
            (POKEDEX, E.ArrangeOwnDeckTopTrainer(E.POKEDEX_TEXT, 3)),
        ]
        for card_id, effect in wrong:
            with self.subTest(card_id=card_id, effect=effect):
                self.assertNotEqual(effect.check(d[card_id]), [])

    def test_card_sources_and_research_links(self):
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text())["cards"]
        for card_id in V0_54_CARDS:
            with self.subTest(card_id=card_id):
                record = sources[card_id]
                self.assertEqual((record["basis"], record["status"], record["kyuura_records"], record["play_text"]),
                                 ("kyuura_data", "adopted", [], {"trainer": "kyuura_printed_text"}))
                (check,) = record["external_checks"]
                self.assertEqual((check["site"], check["edition"]["list_number"]), ("pcg-search.com", EDITIONS[card_id]))
                if card_id in NOTATION_ONLY:
                    self.assertEqual(check["result"], "differences")
                    self.assertEqual([(x["field"], x["affects_behavior"]) for x in check["differences"]], [(NOTATION_ONLY[card_id], False)])
                else:
                    self.assertEqual((check["result"], check["differences"]), ("match", []))
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text())
        self.assertIn({"version": "v0.54", "document": "docs/hand-deck-trainers-v0.54.md", "ruling_id": "HC5"},
                      links["stop_codes"][HC5]["engine_rulings"])
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (87, 88))  # 新しい停止コード・裁定はない

    def test_observation_tables(self):
        self.assertEqual(OPTION_MEANINGS[SELECT_DRAW_COUNT], "number")
        for kind in ("reveal_hand", "revealed_hand_to_deck", "trainer_draw_declined", "trainer_discard_declined", "look_at_deck_top_declined"):
            self.assertIn(kind, PUBLIC_EVENTS)
        self.assertEqual(PRIVATE_FIELDS["look_at_hand"][0], ("cards",))

    def test_document_lists_the_cards_and_codes(self):
        text = DOC.read_text(encoding="utf-8")
        for card_id in V0_54_CARDS:
            self.assertIn(card_id, text)
        self.assertIn(HC5, text)


# ---------------------------------------------------------------- 手札を山札にもどすトレーナー


class ImposterOakTest(unittest.TestCase):
    """にせオーキドはかせ: 相手の手札をすべて相手の山札にもどさせ、切り、相手が 7 枚引く。"""

    def test_opponent_returns_shuffles_and_draws_seven(self):
        state = board([IMPOSTER_OAK, FIGHTING], opponent_hand=[POTION, WATER])
        mine = list(state.players[0].hand)
        before = total_cards(state)
        after = use(state, IMPOSTER_OAK)
        self.assertEqual(kinds(after), ["play_trainer", "hand_to_deck", "shuffle", "draw", "discard_trainer"])
        self.assertEqual((event(after, "hand_to_deck")[0]["player"], event(after, "shuffle")[0]["player"], event(after, "draw")[0]["player"]), (1, 1, 1))
        self.assertEqual(len(after.players[1].hand), 7)
        self.assertEqual(after.players[0].hand, [uid for uid in mine if state.cards[uid].card_id != IMPOSTER_OAK])  # 自分の手札は変えない
        self.assertEqual(total_cards(after), before)
        returned = event(after, "hand_to_deck")[0]
        self.assertNotIn("cards", [e for e in visible_log(after, 0) if e["kind"] == "hand_to_deck"][-1])  # 見せない
        self.assertNotIn("cards", [e for e in visible_log(after, None) if e["kind"] == "hand_to_deck"][-1])
        self.assertEqual([e for e in visible_log(after, 1) if e["kind"] == "hand_to_deck"][-1]["cards"], returned["cards"])
        self.assertNotIn("cards", [e for e in visible_log(after, 0) if e["kind"] == "draw"][-1])  # 引いたカードは引いたプレイヤーだけ
        finished(self, after)

    def test_opponent_empty_hand_and_short_deck(self):
        """相手の手札が 0 枚でも、相手の山札を切って 7 枚引かせる（もどすログはない）。山札が足りなければ引けるだけ（p.312）。"""
        after = use(board([IMPOSTER_OAK], opponent_deck=[RATTATA, WATER, WATER]), IMPOSTER_OAK)
        self.assertEqual(kinds(after), ["play_trainer", "shuffle", "draw", "discard_trainer"])
        self.assertEqual((len(after.players[1].hand), len(after.players[1].deck)), (3, 0))
        self.assertEqual(after.phase, Phase.MAIN)  # 引けなくても負けではない
        finished(self, after)
        after = use(board([IMPOSTER_OAK], opponent_hand=[POTION], opponent_deck=[]), IMPOSTER_OAK)
        self.assertEqual(len(after.players[1].hand), 1)  # もどした 1 枚だけが山札にあり、それを引く
        finished(self, after)


class ImposterOaksRevengeTest(unittest.TestCase):
    """にせオーキドの逆襲: このカードを除く手札 1 枚のトラッシュが使うための条件。そのあと相手の手札をもどさせ、切り、4 枚引かせる。"""

    def test_condition_then_opponent_draws_four(self):
        state = use(board([IMPOSTER_OAKS_REVENGE, FIGHTING, POTION], opponent_hand=[POTION, WATER, WATER]), IMPOSTER_OAKS_REVENGE)
        d = state.decision
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices), (DISCARD_FROM_HAND, 0, 1, 1))
        self.assertNotIn(state.trainer_in_use.card, d.options)  # 使っているカードは選べない
        assert_stops(self, state, ResolveDecision(0, d.id, tuple(d.options)), "INVALID_CHOICE_COUNT", IllegalActionError)  # 不正な答えでは何も変わらない
        after = answer(state, d.options[:1])
        self.assertEqual(kinds(after), ["play_trainer", "discard_from_hand", "hand_to_deck", "shuffle", "draw", "discard_trainer"])
        self.assertEqual(len(after.players[1].hand), 4)
        self.assertIn(d.options[0], after.players[0].discard)
        finished(self, after)

    def test_condition_needs_another_card(self):
        state = board([IMPOSTER_OAKS_REVENGE], opponent_hand=[POTION])
        assert_stops(self, state, PlayTrainer(0, card_of(state, IMPOSTER_OAKS_REVENGE)), "INSUFFICIENT_CARDS_IN_HAND", IllegalActionError)


class GamblerTest(unittest.TestCase):
    """ギャンブラー: 自分の手札をすべて山札にもどして切る → コイン →「おもて」なら 8 枚、「うら」なら 1 枚引く。"""

    def test_heads_draws_eight_tails_draws_one(self):
        """コインは山札を切ったあと（切るのも乱数を使うので、seed を変えて両方の面を起こす）。"""
        seen = set()
        for seed in range(12):
            state = board([GAMBLER, FIGHTING, POTION], seed=seed)
            after = use(state, GAMBLER)
            self.assertEqual(kinds(after), ["play_trainer", "hand_to_deck", "shuffle", "coin_flip", "draw", "discard_trainer"])
            coin = event(after, "coin_flip")[0]
            self.assertEqual((coin["source"], coin["card"], coin["count"]), ("trainer", card_of(state, GAMBLER), 1))
            self.assertEqual(len(after.players[0].hand), 8 if coin["result"] == "heads" else 1)
            self.assertEqual(after.players[1].hand, state.players[1].hand)
            seen.add(coin["result"])
            finished(self, after)
        self.assertEqual(seen, {"heads", "tails"})

    def test_empty_hand_and_short_deck(self):
        """手札がこのカードだけでも使え、切ってコインを投げる（もどすログはない）。「おもて」で山札が 8 枚より少なければ引けるだけ。"""
        for seed in range(12):
            after = use(board([GAMBLER], deck=[WATER] * 3, seed=seed), GAMBLER)
            self.assertEqual(kinds(after), ["play_trainer", "shuffle", "coin_flip", "draw", "discard_trainer"])
            if event(after, "coin_flip")[0]["result"] == "heads":
                self.assertEqual((len(after.players[0].hand), len(after.players[0].deck)), (3, 0))
                finished(self, after)
                return
        self.fail("「おもて」の seed がない")


class SabrinasGazeTest(unittest.TestCase):
    """ナツメの眼: お互いに、自分の手札をすべて自分の山札にもどし、切り、自分がもどした枚数を引く（枚数はプレイヤーごと）。"""

    def test_each_player_draws_own_count(self):
        state = board([SABRINAS_GAZE, FIGHTING, POTION], opponent_hand=[POTION, WATER, WATER])
        after = use(state, SABRINAS_GAZE)
        self.assertEqual(kinds(after), ["play_trainer", "hand_to_deck", "hand_to_deck", "shuffle", "shuffle", "draw", "draw", "discard_trainer"])
        self.assertEqual([e["player"] for e in event(after, "hand_to_deck")], [0, 1])  # 使ったプレイヤー → 相手
        self.assertEqual([len(e["cards"]) for e in event(after, "hand_to_deck")], [2, 3])  # 使っているこのカードは数えない
        self.assertEqual((len(after.players[0].hand), len(after.players[1].hand)), (2, 3))
        finished(self, after)

    def test_zero_cards(self):
        """手札がこのカードだけなら 0 枚もどして 0 枚引く（相手は自分の枚数）。相手の手札が 0 枚なら相手は 0 枚。どちらの山札も切る。"""
        after = use(board([SABRINAS_GAZE], opponent_hand=[POTION, WATER]), SABRINAS_GAZE)
        self.assertEqual([len(e["cards"]) for e in event(after, "draw")], [0, 2])
        self.assertEqual([e["player"] for e in event(after, "shuffle")], [0, 1])
        finished(self, after)
        after = use(board([SABRINAS_GAZE, FIGHTING]), SABRINAS_GAZE)
        self.assertEqual([len(e["cards"]) for e in event(after, "draw")], [1, 0])
        finished(self, after)


class LassTest(unittest.TestCase):
    """ミニスカート: お互いに手札を見せ合い、手札のトレーナーカードをすべて山札にもどし、お互いに切る。"""

    def test_reveal_and_return_trainers(self):
        state = board([LASS, POTION, FIGHTING, MYSTERIOUS_FOSSIL, RATTATA], opponent_hand=[CLEFAIRY_DOLL, WATER, POTION])
        after = use(state, LASS)
        self.assertEqual(kinds(after), ["play_trainer", "reveal_hand", "reveal_hand", "revealed_hand_to_deck", "revealed_hand_to_deck", "shuffle", "shuffle",
                                        "discard_trainer"])
        mine = {after.cards[uid].card_id for uid in after.players[0].hand}
        theirs = {after.cards[uid].card_id for uid in after.players[1].hand}
        self.assertEqual((mine, theirs), ({FIGHTING, RATTATA}, {WATER}))  # ポケモン・エネルギーは動かさない。なにかの化石・ピッピ人形はトレーナーカード
        for viewer in (0, 1, None):
            revealed = [e for e in visible_log(after, viewer) if e["kind"] in ("reveal_hand", "revealed_hand_to_deck")]
            self.assertTrue(all("cards" in e for e in revealed))  # 見せ合ったカードは公開
        self.assertIsNone(observe(after, 1)["players"][0]["hand"]["cards"])  # 見せ合ったあとも、手札は持ち主にだけ見える（公開し続けない）
        self.assertIsNone(observe(after, None)["players"][1]["hand"]["cards"])
        finished(self, after)

    def test_new_cards_are_not_public(self):
        """見せたのはその時点の手札だけ。あとで加わったカード（引いたカード）は、ログ・観測で相手に見えない。"""
        from kyuura_engine import EndTurn
        after = use(board([LASS, FIGHTING], opponent_hand=[WATER]), LASS)
        later = apply_kernel(after, EndTurn(0))
        drawn = [e for e in visible_log(later, 0) if e["kind"] == "draw" and e["player"] == 1][-1]
        self.assertNotIn("cards", drawn)
        self.assertIsNone(observe(later, 0)["players"][1]["hand"]["cards"])
        self.assertEqual(observation_problems(later), [])

    def test_no_trainers_still_shuffles_both(self):
        after = use(board([LASS, FIGHTING], opponent_hand=[]), LASS)
        self.assertEqual(kinds(after), ["play_trainer", "reveal_hand", "reveal_hand", "shuffle", "shuffle", "discard_trainer"])
        finished(self, after)


# ---------------------------------------------------------------- 引く・見る トレーナー


class BlainesLastResortTest(unittest.TestCase):
    """カツラの奥の手: 手札に「カツラの奥の手」以外のカードがあれば使えない。5 枚引く。"""

    def test_only_this_name(self):
        state = board([BLAINES_LAST_RESORT, BLAINES_LAST_RESORT])
        after = use(state, BLAINES_LAST_RESORT)
        self.assertEqual(kinds(after), ["play_trainer", "draw", "discard_trainer"])
        self.assertEqual(len(after.players[0].hand), 6)  # 同じ名前のもう 1 枚は残る
        self.assertNotIn("reveal_hand", kinds(after))  # 手札を見せる指示は日本語版にない
        finished(self, after)
        after = use(board([BLAINES_LAST_RESORT], deck=[WATER, WATER]), BLAINES_LAST_RESORT)
        self.assertEqual(len(after.players[0].hand), 2)
        finished(self, after)

    def test_other_card_in_hand(self):
        state = board([BLAINES_LAST_RESORT, POTION])
        assert_stops(self, state, PlayTrainer(0, card_of(state, BLAINES_LAST_RESORT)), "OTHER_CARDS_IN_HAND", IllegalActionError)


class ErikaTest(unittest.TestCase):
    """エリカ: 使ったプレイヤーが 0〜3 枚引き、引き終わってから相手プレイヤーが自分で 0〜3 枚を選んで引く。"""

    def test_user_then_opponent(self):
        state = use(board([ERIKA]), ERIKA)
        d = state.decision
        self.assertEqual((d.kind, d.player, d.options, d.context_value("stage")), (SELECT_DRAW_COUNT, 0, (0, 1, 2, 3), 0))
        state = answer(state, (2,))
        d = state.decision
        self.assertEqual((d.kind, d.player, d.options, d.context_value("stage")), (SELECT_DRAW_COUNT, 1, (0, 1, 2, 3), 1))
        audited(self, state)
        assert_stops(self, state, ResolveDecision(0, d.id, (1,)), "NOT_YOUR_DECISION", IllegalActionError)  # 相手の決定を使ったプレイヤーは答えられない
        after = answer(state, (3,))
        self.assertEqual([(e["player"], len(e["cards"])) for e in event(after, "draw")], [(0, 2), (1, 3)])
        finished(self, after)

    def test_zero_and_short_decks(self):
        after = answer(answer(use(board([ERIKA]), ERIKA), (0,)), (0,))
        self.assertEqual([(e["player"], e["reason"]) for e in event(after, "trainer_draw_declined")], [(0, "declined"), (1, "declined")])
        finished(self, after)
        state = use(board([ERIKA], deck=[], opponent_deck=[WATER, WATER]), ERIKA)
        d = state.decision
        self.assertEqual((d.player, d.options), (1, (0, 1, 2)))  # 自分の山札が 0 枚なら自分の決定はない
        self.assertEqual(event(state, "trainer_draw_declined")[0]["reason"], "empty_deck")
        finished(self, answer(state, (2,)))
        after = use(board([ERIKA], deck=[], opponent_deck=[]), ERIKA)
        self.assertEqual([e["reason"] for e in event(after, "trainer_draw_declined")], ["empty_deck", "empty_deck"])
        finished(self, after)

    def test_decision_problems_require_the_drawer(self):
        """不変条件: 段階 0 の決定は使ったプレイヤー、段階 1 は相手プレイヤーが決める（ほかのトレーナーの、使ったプレイヤーが決める約束は変えない）。"""
        import dataclasses
        state = use(board([ERIKA]), ERIKA)
        effect = E.DEFAULT_EFFECTS.trainer_entry(ERIKA).effect
        use_info = E.TrainerUse(0, state.trainer_in_use.card, ERIKA)
        self.assertEqual(effect.decision_problems(state, use_info, state.decision), [])
        self.assertNotEqual(effect.decision_problems(state, use_info, dataclasses.replace(state.decision, player=1)), [])
        oak = E.DEFAULT_EFFECTS.trainer_entry(IMPOSTER_OAKS_REVENGE).effect
        self.assertNotEqual(oak.decision_problems(state, use_info, dataclasses.replace(state.decision, kind=DISCARD_FROM_HAND, player=1)), [])


class SecretMissionTest(unittest.TestCase):
    """スパイ作戦: 相手の手札を見る → のぞむなら、手札を好きなだけトラッシュして、同じ数を引く。"""

    def test_look_then_discard_and_draw(self):
        state = use(board([SECRET_MISSION, FIGHTING, POTION], opponent_hand=[POTION, WATER]), SECRET_MISSION)
        look = event(state, "look_at_hand")[0]
        self.assertEqual((look["player"], look["owner"], tuple(look["cards"])), (0, 1, tuple(state.players[1].hand)))
        visible = {viewer: [e for e in visible_log(state, viewer) if e["kind"] == "look_at_hand"][-1] for viewer in (0, 1, None)}
        self.assertIn("cards", visible[0])  # 見たプレイヤー
        self.assertIn("cards", visible[1])  # 持ち主（自分の手札を知っている）
        self.assertNotIn("cards", visible[None])  # 観戦者には見せない
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (DISCARD_FROM_HAND, 0, 2))
        audited(self, state)
        after = answer(state, d.options)
        self.assertEqual(kinds(after), ["play_trainer", "look_at_hand", "discard_from_hand", "draw", "discard_trainer"])
        self.assertEqual(len(event(after, "draw")[0]["cards"]), 2)
        finished(self, after)

    def test_decline_empty_hands_and_short_deck(self):
        after = answer(use(board([SECRET_MISSION, FIGHTING], opponent_hand=[POTION]), SECRET_MISSION), ())
        self.assertEqual(event(after, "trainer_discard_declined")[0]["reason"], "declined")
        self.assertEqual(len(after.players[0].hand), 1)
        finished(self, after)
        after = use(board([SECRET_MISSION], opponent_hand=[]), SECRET_MISSION)  # 相手の手札 0 枚（見るカードがない）・自分の手札 0 枚（決定なし）
        self.assertEqual(event(after, "look_at_hand")[0]["cards"], ())
        self.assertEqual(event(after, "trainer_discard_declined")[0]["reason"], "empty_hand")
        finished(self, after)
        after = answer(use(board([SECRET_MISSION, FIGHTING, POTION], deck=[WATER]), SECRET_MISSION), ())
        self.assertEqual(len(after.players[0].hand), 2)
        state = use(board([SECRET_MISSION, FIGHTING, POTION], deck=[WATER]), SECRET_MISSION)
        after = answer(state, state.decision.options)
        self.assertEqual(len(event(after, "draw")[0]["cards"]), 1)  # 山札が足りなければ引けるだけ
        finished(self, after)

    def test_opponent_hand_stays_hidden_in_observation(self):
        """見たのは 1 回だけ（［おみとおし］のように手札を公開し続けない）。見たあとも、観測の相手の手札は枚数だけ。"""
        state = use(board([SECRET_MISSION, FIGHTING], opponent_hand=[POTION, WATER]), SECRET_MISSION)
        self.assertIsNone(observe(state, 0)["players"][1]["hand"]["cards"])
        self.assertEqual(observe(state, 0)["players"][1]["hand"]["revealed_by"], [])
        after = answer(state, ())
        self.assertIsNone(observe(after, 0)["players"][1]["hand"]["cards"])
        self.assertEqual(observation_problems(after), [])


class BlainesGambleTest(unittest.TestCase):
    """カツラのギャンブル: 手札を好きなだけトラッシュ → コイン →「おもて」ならトラッシュした数 × 2 枚引く。"""

    def test_heads_draws_twice_tails_nothing(self):
        for side, drawn in ((H, 4), (T, 0)):
            with self.subTest(side=side):
                state = use(with_coin_results(board([BLAINES_GAMBLE, FIGHTING, POTION]), side), BLAINES_GAMBLE)
                d = state.decision
                self.assertEqual((d.kind, d.min_choices, d.max_choices), (DISCARD_FROM_HAND, 0, 2))
                after = answer(state, d.options)
                self.assertEqual(set(d.options) <= set(after.players[0].discard), True)  # 「うら」でもトラッシュしたカードはもどらない
                self.assertEqual(len(after.players[0].hand), drawn)
                self.assertEqual(kinds(after)[-2], "draw" if drawn else "coin_flip")
                finished(self, after)

    def test_zero_is_hc5(self):
        """0 枚（「のぞむなら」のない「好きなだけ」）は HC5。決定は待ったまま。手札がこのカードだけなら選べるのは 0 枚だけなので、使う前に止める。"""
        state = use(board([BLAINES_GAMBLE, FIGHTING]), BLAINES_GAMBLE)
        assert_stops(self, state, ResolveDecision(0, state.decision.id, ()), HC5)
        empty = board([BLAINES_GAMBLE])
        assert_stops(self, empty, PlayTrainer(0, card_of(empty, BLAINES_GAMBLE)), HC5)

    def test_short_deck(self):
        state = use(with_coin_results(board([BLAINES_GAMBLE, FIGHTING, POTION], deck=[WATER] * 3), H), BLAINES_GAMBLE)
        after = answer(state, state.decision.options)
        self.assertEqual((len(after.players[0].hand), len(after.players[0].deck)), (3, 0))
        finished(self, after)


class PokedexTest(unittest.TestCase):
    """ポケモン図鑑 HANDY505: 自分の山札の上から 0〜5 枚を見て、好きな順番にもどす（手札に加えない・切らない）。"""

    def test_look_and_arrange(self):
        state = board([POKEDEX], deck=[RATTATA, WATER, POTION, FIGHTING, WATER, POTION, RATTATA])
        deck = list(state.players[0].deck)
        state = use(state, POKEDEX)
        d = state.decision
        self.assertEqual((d.kind, d.options), (SELECT_LOOK_COUNT, (0, 1, 2, 3, 4, 5)))
        self.assertEqual(observe(state, 0)["decision"]["options"], [{"value": n} for n in range(6)])  # 見る前は数だけ（カードの内容を漏らさない）
        rng_before = repr(state.rng.getstate())
        state = answer(state, (3,))
        d = state.decision
        self.assertEqual((d.kind, d.options, d.min_choices), (ARRANGE_DECK_TOP, tuple(deck[:3]), 3))
        self.assertIsNone(observe(state, 1)["decision"].get("options"))
        audited(self, state)
        after = answer(state, tuple(reversed(deck[:3])))
        self.assertEqual(after.players[0].deck, [*reversed(deck[:3]), *deck[3:]])  # 下の並びは変えない
        self.assertEqual(repr(after.rng.getstate()), rng_before)  # 切らない
        self.assertEqual(after.players[0].hand, [])
        for viewer, sees in ((0, True), (1, False), (None, False)):
            self.assertEqual("cards" in [e for e in visible_log(after, viewer) if e["kind"] == "arrange_deck_top"][-1], sees)
        finished(self, after)

    def test_zero_one_and_empty_deck(self):
        after = answer(use(board([POKEDEX], deck=[WATER, RATTATA]), POKEDEX), (0,))  # 0 枚は見ないこと（GS1 を当てはめない）
        self.assertEqual(kinds(after), ["play_trainer", "look_at_deck_top_declined", "discard_trainer"])
        finished(self, after)
        state = use(board([POKEDEX], deck=[WATER]), POKEDEX)
        self.assertEqual(state.decision.options, (0, 1))
        after = answer(state, (1,))
        self.assertEqual(kinds(after), ["play_trainer", "look_at_deck_top", "arrange_deck_top", "discard_trainer"])
        finished(self, after)
        state = use(board([POKEDEX], deck=[WATER, RATTATA, POTION]), POKEDEX)
        self.assertEqual(state.decision.options, (0, 1, 2, 3))
        after = use(board([POKEDEX], deck=[]), POKEDEX)
        self.assertEqual(kinds(after), ["play_trainer", "look_at_deck_top_none", "discard_trainer"])
        finished(self, after)


# ---------------------------------------------------------------- 共通の性質


class CommonTest(unittest.TestCase):
    def test_trainer_lock_applies(self):
        """［アレルギーかふん］がはたらいていれば、10 枚とも使う前に TRAINER_PREVENTED（使うための条件より先）。"""
        for card_id in V0_54_CARDS:
            with self.subTest(card_id=card_id):
                state = board([card_id], opponent_active={"card": DARK_VILEPLUME, "evolved_from": [ROCKET_ODDISH, "PMCG4-006"]})
                assert_stops(self, state, PlayTrainer(0, card_of(state, card_id)), "TRAINER_PREVENTED", IllegalActionError)

    def test_apply_command_does_not_change_the_given_state(self):
        state = board([ERIKA])
        before = snapshot(state)
        after = use(state, ERIKA)
        self.assertEqual(snapshot(state), before)
        clone = after.clone()
        final = answer(answer(after, (1,)), (1,))
        self.assertEqual(snapshot(after), snapshot(clone))
        self.assertIsNone(final.trainer_in_use)

    def test_card_conservation(self):
        """どのカードも、使う前と使ったあとでカードの総数が同じ（複製・消失がない）。"""
        hands = {IMPOSTER_OAK: [FIGHTING], GAMBLER: [FIGHTING], SABRINAS_GAZE: [FIGHTING], BLAINES_LAST_RESORT: [], LASS: [POTION, FIGHTING]}
        for card_id, extra in hands.items():
            with self.subTest(card_id=card_id):
                state = board([card_id, *extra], opponent_hand=[POTION, WATER])
                self.assertEqual(total_cards(use(state, card_id)), total_cards(state))

    def test_pending_decisions_are_consistent(self):
        """エリカ・スパイ作戦・ポケモン図鑑の決定を待つ間も、書き出し・観測・不変条件に問題がない。"""
        for state in (use(board([ERIKA]), ERIKA), use(board([SECRET_MISSION, FIGHTING]), SECRET_MISSION), use(board([POKEDEX]), POKEDEX)):
            audited(self, state)


# ---------------------------------------------------------------- 正式な対戦


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.54 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.54 の 4 組を 2 seed ずつ（席を入れかえて 16 局）。どれも監査の失敗（不変条件・ログ（トレーナー 1 回ぶんの並びを含む）・書き出し・受け付けた操作ごとの観測）・
        想定外の拒否・内部エラー・手数の上限がなく、10 枚のどれも使われる。勝敗は判断に使わない。"""
        from tools import existing_effect_games as games

        results = games.run(range(2), pairings=games.PAIRINGS_V0_54)
        totals: dict = {}
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"), game.get("error"))
                if game["outcome"] == "halted":
                    self.assertIn(game["halt_code"], ("UNRESOLVED_MULLIGAN_COMPENSATION", "UNRESOLVED_PLAY_AS_POKEMON_SETUP"))
                for card, uses in game.get("card_uses", {}).items():
                    for key, count in uses.items():
                        totals[(card, key)] = totals.get((card, key), 0) + count
        for card in V0_54_CARDS:
            self.assertGreater(totals.get((card, "played"), 0), 0, card)
        for card, key in ((IMPOSTER_OAK, "draw_opponent"), (IMPOSTER_OAKS_REVENGE, "discard_from_hand_user"), (GAMBLER, "coin_heads_user"),
                          (GAMBLER, "coin_tails_user"), (SABRINAS_GAZE, "draw_opponent"), (ERIKA, "draw_opponent"), (SECRET_MISSION, "look_at_hand_user"),
                          (BLAINES_GAMBLE, "coin_heads_user"), (LASS, "reveal_hand_opponent"), (POKEDEX, "arrange_deck_top_user")):
            with self.subTest(card=card, key=key):
                self.assertGreater(totals.get((card, key), 0), 0)


if __name__ == "__main__":
    unittest.main()
