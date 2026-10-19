"""v0.53: 山札・トラッシュからカードを選ぶトレーナー 10 枚（docs/search-retrieval-trainers-v0.53.md）。

10 枚: エネルギー転送（PMCG3-044）・モンスターボール（PMCG2-048）・ボスのやりかた（PMCG4-060）・タケシの育て方（PMCG5-077）・カスミのなみだ（PMCG5-069）・
エリカのお付き（PMCG5-072）・メンテナンス（PMCG1-085）・ダウジングマシーン（PMCG1-087）・リサイクル（PMCG3-047）・夜の廃品回収（PMCG4-057）。どれも kyuura データの採用
（処理に使う文面は kyuura の印刷の文面。採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合（10 枚とも match）。kyuura の研究の基準のコミット（3f34908）
に、この 10 枚の最新の説明・エラッタ・裁定・論点の記録はない。ガイドブックは読んでいない。英語版の文面（「basic Energy」「in order to」「Shuffle … into your deck」など）で、
日本語版の条件を補わない。

共通の処理（effects.py）: ``CardFilter``（説明の言葉と 1 対 1 の種類）・``SearchDeckTrainer``（山札をさがして手札に加える 6 枚）・``TakeFromDiscardTrainer``（トラッシュから
手札・山札の一番上・山札へ 3 枚）・``ReturnHandToDeckThenDraw``（メンテナンス）。ゾーンの関数は既存の ``discard_from_hand``・``search_deck_to_hand``・``reveal_deck_to_hand``・
``return_hand_cards_to_deck``（トレーナーの出どころ ``trainer`` を加えた）・``return_discard_to_hand``・``put_discard_on_deck_top``（同じ）・``shuffle_deck``・``draw_cards`` と、
新しい ``return_discard_to_deck``（夜の廃品回収。ログ ``discard_to_deck`` は公開）。

新しい停止コードは 2: ST1（``UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET``）・NG1（``UNRESOLVED_NIGHTLY_GARBAGE_RUN_ZERO_CHOICE``）。メンテナンスの手札が足りない場面は、
v0.44 のラッキーたまごと同じ問い FC1（``UNRESOLVED_STATED_CARDS_SHORT``）。
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
    DISCARD_FROM_HAND,
    DISCARD_TO_DECK,
    DISCARD_TO_DECK_TOP,
    HAND_TO_DECK,
    RECOVER_TRAINER,
    SEARCH_DECK,
)
from kyuura_engine.observation import PRIVATE_FIELDS, PUBLIC_EVENTS
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests.helpers import (
    BILL,
    BOSS_WAY,
    BROCK_TRAINING,
    BROCKS_GEODUDE,
    BROCKS_GOLBAT,
    BROCKS_ZUBAT,
    CLEFAIRY_DOLL,
    DARK_GOLBAT,
    DARK_VILEPLUME,
    DEFENDER,
    ENERGY_SEARCH,
    ERIKAS_GLOOM,
    ERIKAS_MAIDS,
    ERIKAS_ODDISH,
    FIRE,
    GRASS,
    HITMONCHAN,
    ITEM_FINDER,
    MAINTENANCE,
    MISTYS_TEARS,
    MYSTERIOUS_FOSSIL,
    NIGHTLY_GARBAGE_RUN,
    POKE_BALL,
    POTION,
    RATTATA,
    RECYCLE,
    ROCKET_ODDISH,
    ROCKET_ZUBAT,
    V0_53_CARDS,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import (
    observation_problems,
    search_retrieval_problems,
    serialization_problems,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "search-retrieval-trainers-v0.53.md"
TURN = 7
ST1 = "UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET"
NG1 = "UNRESOLVED_NIGHTLY_GARBAGE_RUN_ZERO_CHOICE"
FC1 = "UNRESOLVED_STATED_CARDS_SHORT"
NEW_CODES = (ST1, NG1)
EDITIONS = {ENERGY_SEARCH: "044/048", POKE_BALL: "048/048", BOSS_WAY: "058/065", BROCK_TRAINING: "069/096", MISTYS_TEARS: "075/096",
            ERIKAS_MAIDS: "085/096", MAINTENANCE: "095/096", ITEM_FINDER: "077/096", RECYCLE: "048/048", NIGHTLY_GARBAGE_RUN: "060/065"}
TYPES = {ENERGY_SEARCH: E.SearchDeckTrainer, POKE_BALL: E.SearchDeckTrainer, BOSS_WAY: E.SearchDeckTrainer, BROCK_TRAINING: E.SearchDeckTrainer,
         MISTYS_TEARS: E.SearchDeckTrainer, ERIKAS_MAIDS: E.SearchDeckTrainer, MAINTENANCE: E.ReturnHandToDeckThenDraw,
         ITEM_FINDER: E.TakeFromDiscardTrainer, RECYCLE: E.TakeFromDiscardTrainer, NIGHTLY_GARBAGE_RUN: E.TakeFromDiscardTrainer}


def board(hand=(), *, deck=None, discard=(), opponent_discard=(), active=HITMONCHAN, opponent_active=HITMONCHAN, seed=0):
    me = {"active": active, "bench": [RATTATA], "hand": list(hand), "discard": list(discard)}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent_active, "bench": [RATTATA], "discard": list(opponent_discard)}
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


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def trainer_sequence_ok(test, state):
    """使い終えたトレーナー 1 回ぶんのイベントの並び（tests/log_audit.py の ``search_retrieval_problems``）。"""
    events = [dict(e) for e in since_play(state)]
    test.assertEqual(events[-1]["kind"], "discard_trainer")
    test.assertEqual(search_retrieval_problems(state, events), [])


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


# ---------------------------------------------------------------- 登録・資料


class RegistrationTest(unittest.TestCase):
    def test_pool_registrations_and_types(self):
        pool = load_card_pool()
        for card_id in V0_53_CARDS:
            with self.subTest(card_id=card_id):
                definition = pool.definitions[card_id]
                self.assertEqual(definition.category, "trainer")
                self.assertTrue(definition.supported)
                entry = E.DEFAULT_EFFECTS.trainer_entry(card_id)
                self.assertIs(type(entry.effect), TYPES[card_id])
                self.assertEqual(entry.text_ja, definition.trainer_text_ja)
                self.assertEqual(entry.play_text_ja, definition.trainer_text_ja)  # 処理に使う文面は kyuura の印刷の文面
                self.assertEqual(entry.effect.check(definition), [])
        extract = json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text())
        self.assertEqual(extract["pool_v0_53"], list(V0_53_CARDS))
        self.assertEqual(pool.definitions[NIGHTLY_GARBAGE_RUN].trainer_kinds, ("rockets_secret_machine",))

    def test_registration_rejects_text_mismatches(self):
        """登録の値（見せるか・選ばなくてよいか・コイン・枚数・使うための条件・行き先）が文面と合わなければ ``check`` が拒否する（登録の誤りを見つける）。"""
        pool = load_card_pool()
        poke_ball = pool.definitions[POKE_BALL]
        wrong = [
            E.SearchDeckTrainer(E.POKE_BALL_TEXT, E.CardFilter("pokemon"), 1, optional=False, reveal=True, coin=True),  # 「ことができる」がある
            E.SearchDeckTrainer(E.POKE_BALL_TEXT, E.CardFilter("pokemon"), 1, optional=True, reveal=False, coin=True),  # 見せる
            E.SearchDeckTrainer(E.POKE_BALL_TEXT, E.CardFilter("pokemon"), 1, optional=True, reveal=True, coin=False),  # コイン
            E.SearchDeckTrainer(E.POKE_BALL_TEXT, E.CardFilter("pokemon"), 2, optional=True, reveal=True, coin=True),  # 枚数
        ]
        for effect in wrong:
            self.assertNotEqual(effect.check(poke_ball), [], effect)
        maids = pool.definitions[ERIKAS_MAIDS]
        self.assertNotEqual(E.SearchDeckTrainer(E.ERIKAS_MAIDS_TEXT, E.CardFilter("pokemon", name_prefix="エリカの"), 2, optional=True, reveal=True,
                                                discard_cost=2).check(maids), [])  # 条件は山札にもどす（トラッシュではない）
        recycle = pool.definitions[RECYCLE]
        self.assertNotEqual(E.TakeFromDiscardTrainer(E.RECYCLE_TEXT, E.CardFilter("any"), 1, E.TO_HAND, coin=True).check(recycle), [])
        self.assertNotEqual(E.TakeFromDiscardTrainer(E.RECYCLE_TEXT, E.CardFilter("any"), 1, E.TO_DECK_TOP).check(recycle), [])
        nightly = pool.definitions[NIGHTLY_GARBAGE_RUN]
        self.assertNotEqual(E.TakeFromDiscardTrainer(E.NIGHTLY_GARBAGE_RUN_TEXT, E.CardFilter("pokemon_or_basic_energy"), 3, E.TO_DECK, optional=True)
                            .check(nightly), [])
        self.assertNotEqual(E.ReturnHandToDeckThenDraw(E.MAINTENANCE_TEXT, count=3).check(pool.definitions[MAINTENANCE]), [])

    def test_other_trainer_kinds_are_still_rejected(self):
        """夜の廃品回収の種類（rockets_secret_machine）を受け付けるのは、この種類だけのとき。ほかの種類のトレーナーは、ほかの実装と同じく拒否する。"""
        import dataclasses
        nightly = load_card_pool().definitions[NIGHTLY_GARBAGE_RUN]
        effect = E.DEFAULT_EFFECTS.trainer_entry(NIGHTLY_GARBAGE_RUN).effect
        self.assertNotEqual(effect.check(dataclasses.replace(nightly, trainer_kinds=("rockets_secret_machine", "other"))), [])
        self.assertNotEqual(E.DEFAULT_EFFECTS.trainer_entry(ENERGY_SEARCH).effect.check(
            dataclasses.replace(load_card_pool().definitions[ENERGY_SEARCH], trainer_kinds=("rockets_secret_machine",))), [])

    def test_card_sources_and_research_links(self):
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text())["cards"]
        for card_id in V0_53_CARDS:
            with self.subTest(card_id=card_id):
                record = sources[card_id]
                self.assertEqual((record["basis"], record["status"], record["kyuura_records"], record["play_text"]),
                                 ("kyuura_data", "adopted", [], {"trainer": "kyuura_printed_text"}))
                (check,) = record["external_checks"]
                self.assertEqual((check["site"], check["result"], check["edition"]["list_number"], check["differences"]),
                                 ("pcg-search.com", "match", EDITIONS[card_id], []))
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text())
        for code in NEW_CODES:
            self.assertEqual(links["stop_codes"][code]["kyuura_disposition"], "not_in_kyuura")
            self.assertEqual(links["stop_codes"][code]["engine_rulings"][0]["document"], "docs/search-retrieval-trainers-v0.53.md")
        self.assertIn({"version": "v0.53", "document": "docs/search-retrieval-trainers-v0.53.md", "ruling_id": "FC1"},
                      links["stop_codes"][FC1]["engine_rulings"])
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (147, 149))  # v0.55 で MW1・EM1・SP1・FH1・GL1・GL2・SB1・SB2 を加えた、v0.56 で LS1・RT1・RG1・MY1・MS1・KG1 を加えた、v0.57 で STB1・TG1・FG1・FG2・EX1・VG1・VM1・CH1、v0.58 で RB1〜RB4・TE2・RT1 を加えた、v0.59 で GG1・BL1・CB1・BZ1〜BZ4 を加えた。v0.60 で TS1 を加え、コードのない SS1 を数えた。v0.61 で SH1・SC1・SC2・TD1 を加え、Z9 に停止コードを付けた。v0.62 で MM1・MM2・OM1・OM2 を加え、コードのない ED1 を数えた。v0.63 で QZ1 を加えた  # v0.65 で NT1〜NT3・RX1・FL1・BG1・BG2・KD1 を加えた。v0.66 で CA1・ES1〜ES3 を加えた  # v0.67 で FD1・FD2 を加えた

    def test_observation_tables(self):
        self.assertIn("discard_to_deck", PUBLIC_EVENTS)
        self.assertIn("retrieve_trainer", PUBLIC_EVENTS)
        self.assertEqual(PRIVATE_FIELDS["trainer_take_none"][0], ("reason",))
        self.assertEqual(PRIVATE_FIELDS["hand_to_deck"][0], ("cards",))
        self.assertEqual(PRIVATE_FIELDS["search_deck"][0], ("card",))

    def test_document_lists_the_codes(self):
        text = DOC.read_text(encoding="utf-8")
        for code in (*NEW_CODES, FC1):
            self.assertIn(code, text)


# ---------------------------------------------------------------- カードの種類（CardFilter）


class CardFilterTest(unittest.TestCase):
    def test_kinds_use_printed_definitions(self):
        """山札・トラッシュではカードの印刷の定義で決める。なにかの化石・ピッピ人形はトレーナーカード（ポケモンのカードではない）。名前の始まりは進化カード自身の名前。"""
        pool = load_card_pool()
        d = pool.definitions
        pokemon = E.CardFilter("pokemon")
        self.assertTrue(pokemon.matches(d[RATTATA]))
        self.assertTrue(pokemon.matches(d[DARK_GOLBAT]))
        self.assertFalse(pokemon.matches(d[MYSTERIOUS_FOSSIL]))
        self.assertFalse(pokemon.matches(d[CLEFAIRY_DOLL]))
        self.assertTrue(E.CardFilter("trainer").matches(d[MYSTERIOUS_FOSSIL]))
        dark = E.CardFilter("pokemon", name_prefix="わるい", evolution_only=True)
        self.assertTrue(dark.matches(d[DARK_GOLBAT]))
        self.assertFalse(dark.matches(d[ROCKET_ZUBAT]))  # わるいゴルバットの進化元（わるいではない）
        brock = E.CardFilter("pokemon", name_prefix="タケシの")
        self.assertTrue(brock.matches(d[BROCKS_ZUBAT]) and brock.matches(d[BROCKS_GOLBAT]))
        self.assertFalse(brock.matches(d[RATTATA]))
        water = E.CardFilter("basic_energy", energy_type=E.EnergyType.WATER)
        self.assertTrue(water.matches(d[WATER]))
        self.assertFalse(water.matches(d[FIRE]))
        night = E.CardFilter("pokemon_or_basic_energy")
        self.assertTrue(night.matches(d[GRASS]) and night.matches(d[ERIKAS_GLOOM]))
        self.assertFalse(night.matches(d[POTION]) or night.matches(d[MYSTERIOUS_FOSSIL]))


# ---------------------------------------------------------------- 山札をさがすトレーナー


class EnergySearchTest(unittest.TestCase):
    """エネルギー転送: 山札の基本エネルギーカードを 1 枚、見せずに手札に加えて切る。"""

    def test_takes_one_basic_energy_without_revealing(self):
        state = use(board([ENERGY_SEARCH], deck=[RATTATA, WATER, POTION, FIRE]), ENERGY_SEARCH)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (SEARCH_DECK, 1, 1))
        self.assertEqual({state.cards[o].card_id for o in d.options}, {WATER, FIRE})
        assert_stops(self, state, ResolveDecision(0, d.id, ()), "INVALID_CHOICE_COUNT", IllegalActionError)
        chosen = cards_of(state, FIRE, "deck")[0]
        after = answer(state, (chosen,))
        self.assertIn(chosen, after.players[0].hand)
        self.assertEqual(kinds(after), ["play_trainer", "search_deck", "shuffle", "discard_trainer"])
        trainer_sequence_ok(self, after)
        opponent_log = [e for e in visible_log(after, 1) if e["kind"] == "search_deck"]
        self.assertNotIn("card", opponent_log[-1])  # 相手に見えない（見せる指示がない）
        self.assertIn("card", [e for e in visible_log(after, 0) if e["kind"] == "search_deck"][-1])
        self.assertEqual(after.phase, Phase.MAIN)
        audited(self, after)

    def test_no_basic_energy_stops_before_use(self):
        """ST1: 山札に基本エネルギーカードがない・山札が 0 枚。手札から出す前に止める（状態・ログ・乱数は変わらない）。"""
        for deck in ([RATTATA, POTION], []):
            state = board([ENERGY_SEARCH], deck=deck)
            assert_stops(self, state, PlayTrainer(0, card_of(state, ENERGY_SEARCH)), ST1)

    def test_trainer_lock_comes_first(self):
        """［アレルギーかふん］がはたらいていれば、ST1 より先に TRAINER_PREVENTED（使う前の共通の確かめ）。"""
        state = board([ENERGY_SEARCH], deck=[RATTATA], opponent_active={"card": DARK_VILEPLUME, "evolved_from": [ROCKET_ODDISH, "PMCG4-006"]})
        assert_stops(self, state, PlayTrainer(0, card_of(state, ENERGY_SEARCH)), "TRAINER_PREVENTED", IllegalActionError)


class PokeBallTest(unittest.TestCase):
    """モンスターボール: コインの「おもて」なら、山札のたねポケモン・進化カードを 0〜1 枚、見せて手札に加えて切る。"""

    def test_heads_reveals_one_pokemon_card(self):
        state = use(with_coin_results(board([POKE_BALL], deck=[GRASS, MYSTERIOUS_FOSSIL, DARK_GOLBAT, RATTATA]), H), POKE_BALL)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (SEARCH_DECK, 0, 1))
        self.assertEqual({state.cards[o].card_id for o in d.options}, {DARK_GOLBAT, RATTATA})  # なにかの化石（トレーナー）・エネルギーは選べない
        chosen = cards_of(state, DARK_GOLBAT, "deck")[0]
        after = answer(state, (chosen,))
        self.assertEqual(kinds(after), ["play_trainer", "coin_flip", "reveal_from_deck", "shuffle", "discard_trainer"])
        self.assertEqual([e for e in visible_log(after, 1) if e["kind"] == "reveal_from_deck"][-1]["card"], chosen)  # 相手に見せる
        self.assertEqual(sum(e["kind"] == "coin_flip" for e in since_play(after)), 1)  # 投げ直さない
        trainer_sequence_ok(self, after)
        audited(self, after)

    def test_heads_choose_none_still_shuffles(self):
        state = use(with_coin_results(board([POKE_BALL], deck=[RATTATA, GRASS]), H), POKE_BALL)
        after = answer(state, ())
        self.assertEqual(kinds(after), ["play_trainer", "coin_flip", "trainer_take_none", "shuffle", "discard_trainer"])
        none = next(e for e in since_play(after) if e["kind"] == "trainer_take_none")
        self.assertEqual((none["zone"], none["reason"]), ("deck", "declined"))
        self.assertNotIn("reason", [e for e in visible_log(after, 1) if e["kind"] == "trainer_take_none"][-1])  # 選ばなかったか、なかったかは相手に見えない
        trainer_sequence_ok(self, after)

    def test_heads_without_target_shuffles_without_decision(self):
        for deck in ([GRASS, POTION], []):
            after = use(with_coin_results(board([POKE_BALL], deck=deck), H), POKE_BALL)
            self.assertIsNone(after.decision)
            self.assertEqual(kinds(after), ["play_trainer", "coin_flip", "trainer_take_none", "shuffle", "discard_trainer"])
            self.assertEqual(next(e for e in since_play(after) if e["kind"] == "trainer_take_none")["reason"], "no_target")
            trainer_sequence_ok(self, after)

    def test_tails_does_nothing_and_does_not_shuffle(self):
        state = with_coin_results(board([POKE_BALL], deck=[RATTATA, GRASS, FIRE, WATER]), T)
        deck = list(state.players[0].deck)
        after = use(state, POKE_BALL)
        self.assertEqual(kinds(after), ["play_trainer", "coin_flip", "discard_trainer"])
        self.assertEqual(after.players[0].deck, deck)  # 山札の並びは変わらない（切らない）
        trainer_sequence_ok(self, after)


class NamedSearchTest(unittest.TestCase):
    """ボスのやりかた・タケシの育て方: 説明の名前の（進化）カードを 1 枚、見せて手札に加えて切る。選べなければ ST1。"""

    def test_boss_way_only_dark_evolution_cards(self):
        state = use(board([BOSS_WAY], deck=[ROCKET_ZUBAT, DARK_GOLBAT, DARK_GOLBAT, RATTATA]), BOSS_WAY)
        self.assertEqual([state.cards[o].card_id for o in state.decision.options], [DARK_GOLBAT, DARK_GOLBAT])  # 同じ名前の別のカードは両方
        after = answer(state, state.decision.options[1:])
        self.assertEqual(kinds(after), ["play_trainer", "reveal_from_deck", "shuffle", "discard_trainer"])
        trainer_sequence_ok(self, after)
        state = board([BOSS_WAY], deck=[ROCKET_ZUBAT, RATTATA])
        assert_stops(self, state, PlayTrainer(0, card_of(state, BOSS_WAY)), ST1)

    def test_brock_training_basic_and_evolution(self):
        state = use(board([BROCK_TRAINING], deck=[BROCKS_ZUBAT, BROCKS_GOLBAT, BROCKS_GEODUDE, RATTATA, GRASS]), BROCK_TRAINING)
        self.assertEqual({state.cards[o].card_id for o in state.decision.options}, {BROCKS_ZUBAT, BROCKS_GOLBAT, BROCKS_GEODUDE})
        self.assertEqual(state.decision.min_choices, 1)
        trainer_sequence_ok(self, answer(state, state.decision.options[:1]))
        state = board([BROCK_TRAINING], deck=[RATTATA])
        assert_stops(self, state, PlayTrainer(0, card_of(state, BROCK_TRAINING)), ST1)


class MistysTearsTest(unittest.TestCase):
    """カスミのなみだ: 手札 1 枚をトラッシュ（使うための条件）→ 山札の「水」エネルギーカードを最大 2 枚、見せて手札に加えてよい → 切る。"""

    def test_discard_then_up_to_two_water(self):
        state = use(board([MISTYS_TEARS, POTION], deck=[WATER, WATER, WATER, FIRE, RATTATA]), MISTYS_TEARS)
        d = state.decision
        self.assertEqual((d.kind, d.options, d.min_choices, d.max_choices), (DISCARD_FROM_HAND, (card_of(state, POTION),), 1, 1))  # 使っているカードは選べない
        state = answer(state, d.options)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (SEARCH_DECK, 0, 2))
        self.assertEqual({state.cards[o].card_id for o in d.options}, {WATER})  # 炎エネルギーは選べない
        before_total = total_cards(state)
        assert_stops(self, state, ResolveDecision(0, d.id, d.options[:3]), "INVALID_CHOICE_COUNT", IllegalActionError)  # 不正な答え: トラッシュは取り消さない
        self.assertIn(card_of(state, POTION, "discard"), state.players[0].discard)
        after = answer(state, d.options[:2])
        self.assertEqual(kinds(after), ["play_trainer", "discard_from_hand", "reveal_from_deck", "reveal_from_deck", "shuffle", "discard_trainer"])
        self.assertEqual(total_cards(after), before_total)
        trainer_sequence_ok(self, after)
        audited(self, after)

    def test_zero_and_no_target(self):
        state = use(board([MISTYS_TEARS, POTION], deck=[WATER, FIRE]), MISTYS_TEARS)
        state = answer(answer(state, state.decision.options), ())
        self.assertIsNone(state.decision)
        trainer_sequence_ok(self, state)  # 0 枚: 何も加えず切る
        state = use(board([MISTYS_TEARS, POTION], deck=[FIRE]), MISTYS_TEARS)
        after = answer(state, state.decision.options)
        self.assertEqual(kinds(after), ["play_trainer", "discard_from_hand", "trainer_take_none", "shuffle", "discard_trainer"])
        trainer_sequence_ok(self, after)

    def test_condition_needs_another_card(self):
        state = board([MISTYS_TEARS])
        assert_stops(self, state, PlayTrainer(0, card_of(state, MISTYS_TEARS)), "INSUFFICIENT_CARDS_IN_HAND", IllegalActionError)
        state = use(board([MISTYS_TEARS, MISTYS_TEARS], deck=[WATER]), MISTYS_TEARS)  # 別のカスミのなみだは手札のカード
        self.assertEqual(len(state.decision.options), 1)


class ErikasMaidsTest(unittest.TestCase):
    """エリカのお付き: 手札 2 枚を見せずに山札にもどす（使うための条件）→ 山札の「エリカのポケモン」を最大 2 枚、見せて手札に加えてよい → 切る。"""

    def test_returned_cards_are_candidates(self):
        """山札にエリカのポケモンがなくても使える。もどしたエリカのポケモンを選べる。もどしたカードは相手に見えない。"""
        state = use(board([ERIKAS_MAIDS, ERIKAS_ODDISH, POTION], deck=[RATTATA, GRASS]), ERIKAS_MAIDS)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (HAND_TO_DECK, 2, 2))
        oddish = card_of(state, ERIKAS_ODDISH)
        state = answer(state, d.options)
        self.assertEqual(state.decision.options, (oddish,))
        self.assertEqual((state.decision.min_choices, state.decision.max_choices), (0, 1))
        returned = [e for e in visible_log(state, 1) if e["kind"] == "hand_to_deck"][-1]
        self.assertNotIn("cards", returned)
        self.assertEqual(returned["hidden"], {"cards": 2})
        after = answer(state, (oddish,))
        self.assertIn(oddish, after.players[0].hand)
        self.assertEqual(kinds(after), ["play_trainer", "hand_to_deck", "reveal_from_deck", "shuffle", "discard_trainer"])
        trainer_sequence_ok(self, after)
        audited(self, after)

    def test_up_to_two_and_condition(self):
        state = use(board([ERIKAS_MAIDS, POTION, BILL], deck=[ERIKAS_ODDISH, ERIKAS_GLOOM, ERIKAS_ODDISH]), ERIKAS_MAIDS)
        state = answer(state, state.decision.options)
        self.assertEqual(state.decision.max_choices, 2)
        trainer_sequence_ok(self, answer(state, state.decision.options[:2]))
        state = board([ERIKAS_MAIDS, POTION])
        assert_stops(self, state, PlayTrainer(0, card_of(state, ERIKAS_MAIDS)), "INSUFFICIENT_CARDS_IN_HAND", IllegalActionError)


class MaintenanceTest(unittest.TestCase):
    """メンテナンス: 手札 2 枚を山札にもどす → 切る → 1 枚引く。"""

    def test_return_shuffle_then_draw(self):
        state = use(board([MAINTENANCE, POTION, BILL, GRASS], deck=[RATTATA, FIRE]), MAINTENANCE)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices, len(d.options)), (HAND_TO_DECK, 2, 2, 3))
        self.assertNotIn(state.trainer_in_use.card, d.options)  # 使っているこのカードは選べない
        after = answer(state, d.options[:2])
        self.assertEqual(kinds(after), ["play_trainer", "hand_to_deck", "shuffle", "draw", "discard_trainer"])  # 切ってから引く
        self.assertEqual(len(after.players[0].hand), 2)  # 1 枚残し + 1 枚引いた
        self.assertEqual(len(after.players[0].deck), 3)
        drawn = [e for e in visible_log(after, 1) if e["kind"] == "draw"][-1]
        self.assertNotIn("cards", drawn)
        trainer_sequence_ok(self, after)
        audited(self, after)

    def test_short_hand_is_fc1(self):
        """このカードを除く手札が 2 枚より少ない: FC1（ラッキーたまごと同じ問い。使うための条件にしない）。"""
        for hand in ([MAINTENANCE, POTION], [MAINTENANCE]):
            state = board(hand)
            assert_stops(self, state, PlayTrainer(0, card_of(state, MAINTENANCE)), FC1)


# ---------------------------------------------------------------- トラッシュから選ぶトレーナー


class ItemFinderTest(unittest.TestCase):
    """ダウジングマシーン: 手札 2 枚をすてる → 自分のトラッシュのトレーナーカードを 0〜1 枚手札に加える。"""

    def test_discarded_trainers_are_candidates_but_not_this_card(self):
        state = board([ITEM_FINDER, POTION, GRASS], discard=[ITEM_FINDER, FIRE], opponent_discard=[DEFENDER])
        other = card_of(state, ITEM_FINDER, "discard")
        state = use(state, ITEM_FINDER)
        in_use = state.trainer_in_use.card
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (DISCARD_FROM_HAND, 2, 2))
        potion = card_of(state, POTION)
        state = answer(state, d.options)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (RECOVER_TRAINER, 0, 1))
        self.assertEqual(set(d.options), {other, potion})  # すてたきずぐすりも、トラッシュの別のダウジングマシーンも選べる
        self.assertNotIn(in_use, d.options)  # 使っている最中のこのカードは選べない
        self.assertFalse(any(state.cards[o].owner == 1 for o in d.options))  # 相手のトラッシュは選べない
        after = answer(state, (potion,))
        self.assertIn(potion, after.players[0].hand)
        self.assertEqual(kinds(after), ["play_trainer", "discard_from_hand", "retrieve_trainer", "discard_trainer"])
        self.assertIn(in_use, after.players[0].discard)
        trainer_sequence_ok(self, after)
        audited(self, after)

    def test_zero_without_target_and_condition(self):
        state = use(board([ITEM_FINDER, GRASS, FIRE]), ITEM_FINDER)
        after = answer(state, state.decision.options)
        self.assertEqual(kinds(after), ["play_trainer", "discard_from_hand", "trainer_take_none", "discard_trainer"])
        state = use(board([ITEM_FINDER, POTION, FIRE]), ITEM_FINDER)
        state = answer(state, state.decision.options)
        trainer_sequence_ok(self, answer(state, ()))  # 選ばない（「ことができる」）
        state = board([ITEM_FINDER, POTION], discard=[BILL])
        assert_stops(self, state, PlayTrainer(0, card_of(state, ITEM_FINDER)), "INSUFFICIENT_CARDS_IN_HAND", IllegalActionError)


class RecycleTest(unittest.TestCase):
    """リサイクル: コインの「おもて」なら、自分のトラッシュの好きなカードを 1 枚、山札の一番上に置く（切らない）。"""

    def test_heads_puts_any_card_on_top_and_it_is_drawn_next(self):
        state = with_coin_results(board([RECYCLE], deck=[RATTATA, GRASS], discard=[POTION, FIRE, HITMONCHAN]), H)
        deck = list(state.players[0].deck)
        state = use(state, RECYCLE)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices, len(d.options)), (DISCARD_TO_DECK_TOP, 1, 1, 3))  # 種類の制限はない
        fire = card_of(state, FIRE, "discard")
        after = answer(state, (fire,))
        self.assertEqual(after.players[0].deck, [fire, *deck])  # 一番上。ほかの並びは変わらない（切らない）
        self.assertEqual(kinds(after), ["play_trainer", "coin_flip", "put_discard_on_deck_top", "discard_trainer"])
        self.assertEqual([e for e in visible_log(after, 1) if e["kind"] == "put_discard_on_deck_top"][-1]["card"], fire)
        self.assertEqual(observe(after, 1)["players"][0]["deck"], {"count": 3})  # 山札のほかのカードは見えない
        trainer_sequence_ok(self, after)
        audited(self, after)

    def test_tails_and_empty_discard(self):
        state = with_coin_results(board([RECYCLE], discard=[POTION]), T)
        after = use(state, RECYCLE)
        self.assertEqual(kinds(after), ["play_trainer", "coin_flip", "discard_trainer"])
        state = with_coin_results(board([RECYCLE]), H)
        assert_stops(self, state, PlayTrainer(0, card_of(state, RECYCLE)), ST1)  # コインの前に止める（乱数は変わらない）


class NightlyGarbageRunTest(unittest.TestCase):
    """夜の廃品回収: 自分のトラッシュのポケモン（進化）カード・基本エネルギーカードを最大 3 枚、見せて山札にもどして切る。"""

    def test_returns_up_to_three_and_shuffles(self):
        state = use(board([NIGHTLY_GARBAGE_RUN], discard=[POTION, RATTATA, RATTATA, GRASS, DARK_GOLBAT, MYSTERIOUS_FOSSIL]), NIGHTLY_GARBAGE_RUN)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (DISCARD_TO_DECK, 0, 3))
        self.assertEqual({state.cards[o].card_id for o in d.options}, {RATTATA, GRASS, DARK_GOLBAT})  # トレーナー（なにかの化石を含む）は選べない
        rattatas = cards_of(state, RATTATA, "discard")
        assert_stops(self, state, ResolveDecision(0, d.id, (rattatas[0], rattatas[0])), "DUPLICATE_CHOICE", IllegalActionError)
        assert_stops(self, state, ResolveDecision(0, d.id, ()), NG1)  # 0 枚: 決定は待ったまま
        after = answer(state, (*rattatas, card_of(state, GRASS, "discard")))  # 同じ名前の別のカードは選べる
        self.assertEqual(kinds(after), ["play_trainer", "discard_to_deck", "shuffle", "discard_trainer"])
        self.assertEqual(sorted([e for e in visible_log(after, 1) if e["kind"] == "discard_to_deck"][-1]["cards"]),
                         sorted([*rattatas, card_of(after, GRASS, "deck")]))
        self.assertTrue(set(rattatas) <= set(after.players[0].deck))
        trainer_sequence_ok(self, after)
        audited(self, after)

    def test_no_candidate_is_ng1(self):
        state = board([NIGHTLY_GARBAGE_RUN], discard=[POTION, MYSTERIOUS_FOSSIL])
        assert_stops(self, state, PlayTrainer(0, card_of(state, NIGHTLY_GARBAGE_RUN)), NG1)


# ---------------------------------------------------------------- 共通の性質


class CommonTest(unittest.TestCase):
    def test_apply_command_does_not_change_the_given_state(self):
        state = with_coin_results(board([POKE_BALL], deck=[RATTATA, GRASS]), H)
        before = snapshot(state)
        after = use(state, POKE_BALL)
        self.assertEqual(snapshot(state), before)
        clone = after.clone()
        self.assertEqual(snapshot(clone), snapshot(after))
        final = answer(after, after.decision.options[:1])
        self.assertEqual(snapshot(after), snapshot(clone))
        self.assertIsNone(final.trainer_in_use)

    def test_pending_decisions_serialize_and_observe(self):
        """どの段階の決定も書き出せ（最新の形式）、観測・不変条件の問題がない。山札の選べるものは決めるプレイヤーにだけ見える。"""
        state = use(board([MISTYS_TEARS, POTION], deck=[WATER, FIRE]), MISTYS_TEARS)
        audited(self, state)
        state = answer(state, state.decision.options)
        audited(self, state)
        mine, theirs = observe(state, 0), observe(state, 1)
        self.assertIsNotNone(mine["decision"]["options"])
        self.assertNotEqual(mine["decision"], theirs["decision"])
        state = use(board([NIGHTLY_GARBAGE_RUN], discard=[GRASS]), NIGHTLY_GARBAGE_RUN)
        audited(self, state)



# ---------------------------------------------------------------- 正式な対戦


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.53 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.53 の 4 組を 2 seed ずつ（席を入れかえて 16 局）。どれも監査の失敗（不変条件・ログ（トレーナー 1 回ぶんの並びを含む）・書き出し・観測）・想定外の拒否・
        内部エラー・手数の上限がなく、10 枚のどれも使われ、選んだカードがそのあと使われる（場に出す・エネルギーをつける・進化・トレーナーを使う・リサイクルで置いたカードを
        引く）。勝敗は判断に使わない。"""
        from tools import existing_effect_games as games

        results = games.run(range(2), pairings=games.PAIRINGS_V0_53)
        totals: dict = {}
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"), game.get("error"))
                if game["outcome"] == "halted":
                    self.assertEqual(game["halt_code"], "UNRESOLVED_MULLIGAN_COMPENSATION")
                for card, uses in game.get("card_uses", {}).items():
                    for key, count in uses.items():
                        totals[(card, key)] = totals.get((card, key), 0) + count
        for card in V0_53_CARDS:
            self.assertGreater(totals.get((card, "played"), 0), 0, card)
        for card, key in ((ENERGY_SEARCH, "search_deck"), (ENERGY_SEARCH, "taken_then_attach_energy"), (POKE_BALL, "coin_heads"), (POKE_BALL, "coin_tails"),
                          (POKE_BALL, "taken_then_play_to_bench"), (BOSS_WAY, "taken_then_evolve"), (BROCK_TRAINING, "taken_then_play_to_bench"),
                          (MISTYS_TEARS, "taken_then_attach_energy"), (MISTYS_TEARS, "none_declined"), (ERIKAS_MAIDS, "hand_to_deck"),
                          (ERIKAS_MAIDS, "taken_then_play_to_bench"), (MAINTENANCE, "draw"), (ITEM_FINDER, "retrieve_trainer"),
                          (ITEM_FINDER, "taken_then_play_trainer"), (RECYCLE, "coin_tails"), (RECYCLE, "taken_then_draw"), (NIGHTLY_GARBAGE_RUN, "discard_to_deck")):
            with self.subTest(card=card, key=key):
                self.assertGreater(totals.get((card, key), 0), 0)


if __name__ == "__main__":
    unittest.main()
