"""v0.96（docs/unown-family-powers-v0.96.md）: アンノーン 7 枚（ワザ 7・特殊能力 7）と遺跡の石版 2 枚。

根拠は kyuura データの採用（kyuura ``7d3f4ca`` の data/cards.json の日本語の印刷の文面・ルール文）と、既存の規定・読み方の記録（p.308 のデッキの規定・p.312 の「引けるだけ」・
v0.43 の場に出たときの特殊能力・PW3・v0.46 の CP2・v0.47 の［スパイ］・v0.53 の ST1・v0.54 の HD1・v0.59 の GG1・v0.67 の FD1・v0.81 のふうせんのみ・BB1・v0.84 の［おくりもの］・
v0.86 の［いやしのかぜ］・エリカの香水の経路・v0.95 の見る処理）。英語版の文面・現代のルール・後年の裁定（2002-05-24 のポケボディーの分類・2000年7月・9月の誌面）は持ち込まない。
公式ガイドブックの新しい読み直し・カードの画像・pcg-search.com との照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの
自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.96``）。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import random
import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttackKey,
    PlayBasicToBench,
    PlayTrainer,
    PowerKey,
    ResolveDecision,
    Retreat,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import (
    _deck_group_rule,
    _name_letter,
    load_card_pool,
    pool_from_extract,
    read_extract,
)
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    ACCEPT_REQUEST,
    BENCH_FROM_DECK,
    ENTRY_POWER,
    SELECT_PRIZE_CARD,
)
from kyuura_engine.deck import deck_problems
from kyuura_engine.errors import (
    HiddenPropertyRead,
    IllegalActionError,
)
from kyuura_engine.observation import (
    HIDDEN_COUNT_KINDS,
    PUBLIC_EVENTS,
    observe,
    visible_log,
)
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import Phase
from tests import helpers as H
from tests.helpers import apply_kernel, build_test_state, with_coin_results
from tests.release_catalog import cards_after, cards_before
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_power_suppression_lasting_locks_v0_92 import mon, uid

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "unown-family-powers-v0.96.md"
RULES_DOC = ROOT / "docs" / "rules-2000-02-14.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, PS, FT = H.WATER, H.PSYCHIC, H.FIGHTING
UE, UO, UR, UL, US, UT, UZ = H.UNOWN_E, H.UNOWN_O, H.UNOWN_R, H.UNOWN_L, H.UNOWN_S, H.UNOWN_T, H.UNOWN_Z
WALL, WALL2 = H.RUIN_WALL, H.RUIN_WALL_2
POTION = H.POTION
BALLOON_BERRY, BUMPY_GYM = "neo3-055", "neo4-110"  # ふうせんのみ（v0.81）・でこぼこジム（たねポケモンの「にげる」+1。v0.81）
V096_ATTACKS = [AttackKey(c, 0) for c in H.V0_96_POKEMON]
V096_POWERS = [PowerKey(c, 0) for c in H.V0_96_POKEMON]
EG1, OB1, PW3, ST1, FD1, CP2, BB1 = ("UNRESOLVED_ENGAGE_EMPTY_HAND", "UNRESOLVED_POWER_DECK_TOP_SHORT", "UNRESOLVED_POWER_ZERO_CARDS",
                                     "UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET", "UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY", "UNRESOLVED_RETREAT_COST_FLOOR",
                                     "UNRESOLVED_BALLOON_BERRY_FAILED_RETREAT")
GG1 = "UNRESOLVED_GOOP_GAS_NEW_POKEMON"
TURN = 7


def board(active, *, bench=(H.RATTATA,), opponent=None, opponent_bench=(H.RATTATA,), hand=(), opponent_hand=(), deck=None, opponent_deck=None,
          prizes=6, opponent_prizes=6, current=0, turn=TURN):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": list(deck if deck is not None else [W] * 10), "discard": [], "prizes": prizes}
    them = {"active": opponent or mon(H.RATTATA), "bench": list(opponent_bench), "hand": list(opponent_hand),
            "deck": list(opponent_deck if opponent_deck is not None else [W] * 10), "discard": [], "prizes": opponent_prizes}
    return build_test_state([me, them], turn_number=turn, current_player=current)


def answer(state, choices, player=None):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player if player is None else player, d.id, tuple(choices)))


def power(state, pokemon_id, *coins, player=0):
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UsePokemonPower(player, pokemon_id, 0))


def bench_pid(state, card_id, player=0):
    return next(p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card_id)


def kinds(before, after, *names):
    return [e["kind"] for e in new_events(before, after, *names)]


def snap(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log], repr(state.rng.getstate())


def same_answers(test, state, choices):
    """待っている決定のある状態を clone・deepcopy・pickle しても、同じ答えで同じ結果になる。"""
    expected = answer(state, choices)
    for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
        test.assertEqual(snap(answer(other, choices)), snap(expected))
    return expected


def play_entry(state, card_id, player=0):
    """手札の ``card_id`` をベンチに出す（場に出たときの特殊能力の機会の決定まで）。"""
    return apply_kernel(state, PlayBasicToBench(player, uid(state, card_id, player)))


def deck_of(*cards):
    """デッキ 60 枚（``cards`` と水エネルギー）。"""
    cards = list(cards)
    return cards + [W] * (60 - len(cards))


# ---------------------------------------------------------------- 1〜3 章: 対象・登録・文面


class RegistrationTest(unittest.TestCase):
    def test_every_attack_power_and_trainer_is_registered(self):
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_96"]), H.V0_96_CARDS)
        for key in V096_ATTACKS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
                printed = pool.definitions[key.card_id].attacks[0]
                self.assertIs(entry.effect, E.DAMAGE_ONLY)
                self.assertEqual((entry.name_ja, printed.name_ja, printed.text_ja, entry.text_ja), ("めざめるパワー", "めざめるパワー", None, None))
                self.assertIsNone(DEFAULT_EFFECTS.attack_problem(key.card_id, printed, pool.definitions[key.card_id].attacks))
        for key in V096_POWERS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.power_entry(key.card_id, key.power_index)
                printed = pool.definitions[key.card_id].powers[0]
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja), (printed.name_ja, printed.text_ja, printed.text_ja))
                self.assertEqual(entry.effect.check(printed), [])
                self.assertIsNone(DEFAULT_EFFECTS.power_problem(key.card_id, printed))
        for card in (WALL, WALL2):
            entry = DEFAULT_EFFECTS.trainer_entry(card)
            self.assertEqual((entry.name_ja, entry.text_ja), (pool.definitions[card].name_ja, pool.definitions[card].trainer_text_ja))
        for card in H.V0_96_CARDS:
            self.assertIn(card, pool.playable_ids)

    def test_attack_values_are_the_extract_values(self):
        """めざめるパワーは説明文のないワザ。エネルギー・ダメージは写しの値（アンノーンT は超無・20。kyuura の pokemonwiki_review.json の neo4-052|cost の判定のあとの値）。"""
        pool = load_card_pool()
        expected = {UE: (("psychic",), 10), UO: (("psychic",), 10), UR: (("psychic", "colorless"), 20), UL: (("psychic",), 10),
                    US: (("psychic", "colorless"), 20), UT: (("psychic", "colorless"), 20), UZ: (("psychic",), 10)}
        for card, (cost, damage) in expected.items():
            with self.subTest(card=card):
                attack = pool.definitions[card].attacks[0]
                self.assertEqual((tuple(t.value for t in attack.cost), attack.damage), (cost, damage))
                definition = pool.definitions[card]
                self.assertEqual((definition.stage, definition.pokemon_type, definition.weakness, definition.retreat_cost), ("basic", E.EnergyType.PSYCHIC,
                                                                                                                            E.EnergyType.PSYCHIC, 1))
        self.assertEqual({c: pool.definitions[c].hp for c in H.V0_96_POKEMON}, {UE: 40, UO: 40, UR: 40, UL: 50, US: 50, UT: 40, UZ: 40})

    def test_types(self):
        effect = lambda card: DEFAULT_EFFECTS.power_entry(card, 0).effect
        self.assertEqual(effect(UE), E.EachPlayerMayReturnHandThenDrawOnEntry(4))
        self.assertEqual(effect(UO), E.LookOpponentDeckTopKeepOrder(5))
        self.assertEqual(effect(UR), E.HealAllNameGroupOnEntry("アンノーン"))
        self.assertEqual(effect(UL), E.CoinEachPlayerShufflesOpponentDeck())
        self.assertEqual(effect(US), E.LookOwnPrizeCard())
        self.assertEqual(effect(UT), E.CoinEachPlayerLooksOpponentHand())
        self.assertEqual(effect(UZ), E.ZeroGroupRetreatCostFromBench("アンノーン"))
        self.assertTrue(all(type(effect(c)).once_per_turn for c in (UO, UL, US, UT)))
        self.assertTrue(isinstance(effect(UE), E.EntryPower) and isinstance(effect(UR), E.EntryPower))
        self.assertTrue(effect(UE).from_hand_only and effect(UR).from_hand_only)
        self.assertFalse(effect(UZ).declared)
        self.assertEqual(DEFAULT_EFFECTS.trainer_entry(WALL).effect, E.BenchNameGroupFromDeckTrainer(E.RUIN_WALL_TEXT.format(group="アンノーン")))

    def test_the_ruin_wall_pair_shares_one_registration(self):
        """遺跡の石版（neo2-054・neo2-057）はゲーム用データが同じ組（SC-neo2-054）。id ごとに登録し、同じ登録の値を使う。"""
        self.assertEqual(dict(E.SAME_DATA_TRAINERS_V0_96), {WALL2: WALL})
        extract = {c["id"]: c for c in read_extract()["cards"]}
        self.assertEqual(extract[WALL2]["same_card_group"], extract[WALL]["same_card_group"])
        self.assertEqual(extract[WALL2]["trainer"], extract[WALL]["trainer"])
        self.assertIs(DEFAULT_EFFECTS.trainer_entry(WALL2), DEFAULT_EFFECTS.trainer_entry(WALL))

    def test_unregistered_without_the_v0_96_entries(self):
        """今回の登録を除くと対戦に使えなくなるのは、ちょうど 9 枚（ほかのカードは失われない）。過去の範囲は ``cards_before`` で切り出す。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V096_ATTACKS)
        registry = registry.without_powers(registry.id, V096_POWERS)
        registry = registry.without_trainers(registry.id, (WALL, WALL2))
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(H.V0_96_CARDS))
        self.assertEqual(set(H.V0_96_CARDS) & set(cards_before(read_extract(), "0.96")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.95")) & set(cards_before(read_extract(), "0.97")), set(H.V0_96_CARDS))

    def test_adoption_records(self):
        data = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        for card in H.V0_96_CARDS:
            with self.subTest(card=card):
                record = data[card]
                self.assertEqual((record["basis"], record["status"], record["kyuura_records"], record["external_checks"]), ("kyuura_data", "adopted", [], []))
                self.assertEqual(record["play_text"], {"trainer": "kyuura_printed_text"} if card in H.V0_96_TRAINERS else {"power/0": "kyuura_printed_text"})
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        adopted = links["latest_descriptions"]["adopted_printed_text"]
        self.assertEqual([k for k in adopted if k.split("/")[0] in H.V0_96_CARDS], [f"{c}/power/0" for c in H.V0_96_POKEMON])  # 説明文のないワザ・トレーナーは書かない


class TextTest(unittest.TestCase):
    """新しい型は全文を照らし、似た形の別の文面・別の値を通さない。"""

    def test_values_and_texts_are_checked(self):
        pool = load_card_pool()
        printed = lambda card: pool.definitions[card].powers[0]
        self.assertTrue(E.EachPlayerMayReturnHandThenDrawOnEntry(5).check(printed(UE)))
        self.assertTrue(E.LookOpponentDeckTopKeepOrder(3).check(printed(UO)))
        self.assertTrue(E.HealAllNameGroupOnEntry("ピカチュウ").check(printed(UR)))
        self.assertTrue(E.ZeroGroupRetreatCostFromBench("ピカチュウ").check(printed(UZ)))
        self.assertTrue(E.HealEachOwnPokemonOnEntry().check(printed(UR)))  # ［いやしのかぜ］の型で通さない
        self.assertTrue(E.CoinPeekOpponentDeckTopMayShuffle().check(printed(UO)))  # ［わるぢえ］の型で通さない
        self.assertTrue(E.CoinLookOpponentHandMayReturnTrainer().check(printed(UT)))  # ［みやぶる］の型で通さない
        self.assertTrue(E.ReduceOwnActiveRetreatCost(1).check(printed(UZ)))
        self.assertTrue(E.LookOwnPrizeCard().check(printed(UL)))
        self.assertTrue(E.CoinEachPlayerShufflesOpponentDeck().check(printed(UT)))
        wall = pool.definitions[WALL]
        self.assertTrue(E.BenchNameGroupFromDeckTrainer(E.RUIN_WALL_TEXT.format(group="ピカチュウ"), "ピカチュウ").check(wall))
        self.assertTrue(E.BenchNameGroupFromDeckTrainer(wall.trainer_text_ja, "ピカチュウ").check(wall))

    def test_power_names_are_the_extract_spellings(self):
        """名前は写しの表記のまま（［LAUGH］は空白のある「LAUGH [ラフ]」）。書き方を直して登録しない。"""
        names = {c: DEFAULT_EFFECTS.power_entry(c, 0).name_ja for c in H.V0_96_POKEMON}
        self.assertEqual(names, {UE: "ENGAGE[エンゲージ]", UO: "OBSERVE[オブザーブ]", UR: "REASSURE[リーアシュア]", UL: "LAUGH [ラフ]", US: "SEARCH[サーチ]",
                                 UT: "TELL[テル]", UZ: "ZOOM[ズーム]"})

    def test_no_status_condition_in_the_japanese_texts(self):
        """日本語の文面に「ねむり・マヒ・こんらん」の条件はない（英語版の「can be used even if …」・ほかのカードの条件を持ち込まない）。"""
        for card in H.V0_96_POKEMON:
            self.assertNotIn("ねむり", DEFAULT_EFFECTS.power_entry(card, 0).text_ja)
        self.assertFalse(E.ZeroGroupRetreatCostFromBench.blocked_by_status)


class RulesDocumentTest(unittest.TestCase):
    def test_reference_section_and_document(self):
        text = RULES_DOC.read_text(encoding="utf-8")
        for word in ("unown-family-powers-v0.96.md", "EG1", "OB1", "ST1", "CP2", "根拠のある規定", "未解決", "実装上の読み方"):
            self.assertIn(word, text)
        doc = DOC.read_text(encoding="utf-8")
        for word in ("EG1", "OB1", "UNRESOLVED_ENGAGE_EMPTY_HAND", "UNRESOLVED_POWER_DECK_TOP_SHORT", "P39", "P40", "2002-05-24"):
            self.assertIn(word, doc)


# ---------------------------------------------------------------- 2 章: 「アンノーン」の名前のグループとデッキの規定


class NameGroupTest(unittest.TestCase):
    def test_both_spellings_are_one_group(self):
        pool = load_card_pool()
        letters = {c: (pool.definitions[c].name_group, pool.definitions[c].name_letter, pool.definitions[c].deck_group_limit) for c in H.V0_96_POKEMON}
        self.assertEqual(letters, {UE: ("アンノーン", "E", 4), UO: ("アンノーン", "O", 4), UR: ("アンノーン", "R", 4), UL: ("アンノーン", "L", 4),
                                   US: ("アンノーン", "S", 4), UT: ("アンノーン", "T", 4), UZ: ("アンノーン", "Z", 4)})
        for card in H.V0_96_POKEMON:  # 名前・id は書き換えない。同じ名前の上限（deck_limit）とは別
            self.assertTrue(pool.definitions[card].name_ja.startswith("アンノーン"))
            self.assertIsNone(pool.definitions[card].deck_limit)
        self.assertEqual({pool.definitions[c].name_group for c in pool.playable_ids} - {None}, {"アンノーン"})

    def test_letter_notations_are_exact(self):
        self.assertEqual((_name_letter("アンノーンT", "アンノーン"), _name_letter("アンノーン[O]", "アンノーン")), ("T", "O"))
        for name in ("アンノーン", "アンノーンTT", "アンノーン[TT]", "アンノーンＴ", "アンノーン[t]", "アンノーンT[O]", "わるいアンノーンT", "アンノーン[O"):
            with self.subTest(name=name):
                self.assertIsNone(_name_letter(name, "アンノーン"))
        rule = "「アンノーン」はデッキに4枚までしか入れることができません。"
        self.assertEqual(_deck_group_rule("アンノーンT", rule), ("アンノーン", "T", 4))
        self.assertIsNone(_deck_group_rule("ピカチュウ", rule))  # 名前がグループの名前で書かれていない
        self.assertIsNone(_deck_group_rule("アンノーンT", "「アンノーン」はデッキに4枚まで入れることができます。"))
        self.assertIsNone(_deck_group_rule("アンノーンT", rule + "このカードはにげられない。"))

    def test_face_down_card_hides_the_group(self):
        from kyuura_engine.cards import FACE_DOWN_DEFINITION, FACE_DOWN_HIDDEN_FIELDS

        with self.assertRaises(HiddenPropertyRead):
            FACE_DOWN_DEFINITION.name_group  # noqa: B018
        self.assertLessEqual({"name_group", "name_letter", "deck_group_limit"}, set(FACE_DOWN_HIDDEN_FIELDS))

    def test_cards_without_the_rule_text_still_belong_but_do_not_declare(self):
        """ルール文のない文字（アンノーンI など。今の写しにない）は、同じ写しにグループを書くカードがあればグループのカードとして数える。上限を書くのは自分のルール文だけで、
        ルール文のないカードだけのデッキに上限を作らない。対戦に使えるかは登録で決まる（ルール文の確かめを緩めない）。"""
        extract = copy.deepcopy(read_extract())
        record = copy.deepcopy(next(c for c in extract["cards"] if c["id"] == UZ))
        record["id"], record["name"] = "TEST-UNOWN-I", {"ja": "アンノーンI", "en": None}
        record["pokemon"]["rules_text"] = None
        extract["cards"].append(record)
        pool = pool_from_extract(extract)
        test_i = pool.definitions["TEST-UNOWN-I"]
        self.assertEqual((test_i.name_group, test_i.name_letter, test_i.deck_group_limit, test_i.supported), ("アンノーン", "I", None, False))
        problems = deck_problems(deck_of(UE, UO, UL, UZ, "TEST-UNOWN-I", H.RATTATA), pool)
        self.assertTrue(any(p.startswith("TOO_MANY_GROUP_COPIES") and "5 枚" in p for p in problems))
        alone = deck_problems(deck_of(*(["TEST-UNOWN-I"] * 4), H.RATTATA), pool)
        self.assertFalse(any(p.startswith("TOO_MANY_GROUP_COPIES") for p in alone))
        self.assertTrue(any(p.startswith("UNSUPPORTED_CARD") for p in alone))


class DeckLimitTest(unittest.TestCase):
    """デッキの規定（p.308 とカードのルール文）。場のポケモンの数の制限ではない。"""

    def test_four_across_letters_is_allowed_five_is_not(self):
        self.assertEqual(deck_problems(deck_of(UE, UO, UL, UZ, H.RATTATA)), [])
        self.assertEqual(deck_problems(deck_of(UE, UE, UE, UE, H.RATTATA)), [])  # 同じ文字 4 枚も合わせて 4 枚
        five = deck_problems(deck_of(UE, UO, UR, UL, UZ, H.RATTATA))
        self.assertEqual([p for p in five if p.startswith("TOO_MANY")], ["TOO_MANY_GROUP_COPIES: 「アンノーン」のカードが合わせて 5 枚（カードのルール文で、デッキに 4 枚まで）"])
        self.assertTrue(any(p.startswith("TOO_MANY_GROUP_COPIES") for p in deck_problems(deck_of(*([US] * 3 + [UT] * 2), H.RATTATA))))

    def test_same_name_and_shining_limits_are_kept(self):
        same = deck_problems(deck_of(*([UE] * 5), H.RATTATA))
        self.assertIn("TOO_MANY_COPIES: 「アンノーン[E]」が 5 枚（同じ名前は 4 枚まで）", same)
        self.assertTrue(any(p.startswith("TOO_MANY_GROUP_COPIES") for p in same))
        shining = deck_problems(deck_of("neo4-025", "neo4-025", H.RATTATA))
        self.assertIn("TOO_MANY_COPIES: 「ひかるリザードン」が 2 枚（カードのルール文で、デッキに 1 枚まで）", shining)
        handy = deck_problems(deck_of(*([H.POKEDEX] * 3 + ["GD1-022"] * 2), H.RATTATA))  # 書き方の違う同じ名前（v0.71）
        self.assertTrue(any("ポケモン図鑑 HANDY505" in p and "5 枚" in p for p in handy))
        self.assertEqual(deck_problems(deck_of(*([H.RATTATA] * 4), UE, UO, UL, UZ)), [])  # ほかの名前は数えない

    def test_the_ruin_wall_is_not_an_unown(self):
        self.assertEqual(deck_problems(deck_of(UE, UO, UL, UZ, WALL, WALL, WALL2, WALL2)), [])
        self.assertTrue(any(p.startswith("TOO_MANY_COPIES: 「遺跡の石版」") for p in deck_problems(deck_of(UE, *([WALL] * 3 + [WALL2] * 2)))))

    def test_field_uses_the_current_form(self):
        """場で「アンノーン」かは今の姿で決める: ［へんしん］のメタモン（相手のバトル場がアンノーン）は「アンノーン」、デッキでは印刷のメタモン（数えない）。"""
        state = board(mon(H.DITTO, (W,), damage=20), bench=(mon(UZ),), opponent=mon(UL))
        ditto = state.players[0].active
        self.assertTrue(E.in_name_group(state, ditto, "アンノーン"))
        self.assertEqual(E.retreat_cost(state, 0).maximum, 0)
        self.assertEqual(deck_problems(deck_of(H.DITTO, UE, UO, UL, UZ)), [])
        plain = board(mon(H.DITTO, (W,)), bench=(mon(UZ),), opponent=mon(H.ONIX))
        self.assertFalse(E.in_name_group(plain, plain.players[0].active, "アンノーン"))
        self.assertEqual((E.retreat_cost(plain, 0).maximum, E.retreat_cost(plain, 0).power_zeroed), (3, ()))  # 今の姿のイワークのにげる 3


# ---------------------------------------------------------------- 4 章: 手札から場に出したときの特殊能力（［ENGAGE］・［REASSURE］）


class EngageTest(unittest.TestCase):
    def _offered(self, hand=(POTION, W), opponent_hand=(W, W, W), deck=None, opponent_deck=None):
        state = board(mon(H.RATTATA), hand=(UE, *hand), opponent_hand=opponent_hand, deck=deck, opponent_deck=opponent_deck)
        offered = play_entry(state, UE)
        self.assertEqual((offered.decision.kind, offered.decision.player, offered.decision.options), (ENTRY_POWER, 0, (bench_pid(offered, UE),)))
        return offered

    def test_each_player_decides_for_themselves(self):
        offered = self._offered(deck=[POTION] * 3 + [W] * 7)
        used = answer(offered, offered.decision.options)
        self.assertEqual((used.decision.kind, used.decision.player, used.decision.options, used.decision.context_value("stage")), (ACCEPT_REQUEST, 0, (1,), 0))
        hand = tuple(used.players[0].hand)
        mine = same_answers(self, used, (1,))
        (returned,) = new_events(used, mine, "hand_to_deck")
        self.assertEqual((returned["player"], returned["cards"], returned["power"]), (0, hand, f"{UE}@power0"))
        self.assertEqual(len(mine.players[0].hand), 4)
        self.assertEqual(kinds(used, mine, "hand_to_deck", "shuffle", "draw"), ["hand_to_deck", "shuffle", "draw"])
        self.assertEqual((mine.decision.kind, mine.decision.player, mine.decision.context_value("stage")), (ACCEPT_REQUEST, 1, 1))
        # 相手が決める段階で、使ったプレイヤーが答えても受け付けない
        with self.assertRaises(IllegalActionError):
            apply_kernel(mine, ResolveDecision(0, mine.decision.id, (1,)))
        before_rng = repr(mine.rng.getstate())
        declined = answer(mine, ())
        self.assertEqual(declined.players[1].hand, mine.players[1].hand)
        self.assertEqual(declined.players[1].deck, mine.players[1].deck)
        self.assertEqual(repr(declined.rng.getstate()), before_rng)
        self.assertEqual([(e["player"], e["power"]) for e in new_events(mine, declined, "hand_return_declined")], [(1, f"{UE}@power0")])
        self.assertEqual((declined.decision, declined.phase, declined.current_player), (None, Phase.MAIN, 0))
        audited(self, declined)

    def test_answer_combinations(self):
        for mine, theirs in (((), ()), ((), (1,)), ((1,), (1,))):
            with self.subTest(mine=mine, theirs=theirs):
                offered = self._offered()
                used = answer(offered, offered.decision.options)
                first = answer(used, mine)
                done = answer(first, theirs)
                returned = [e["player"] for e in new_events(used, done, "hand_to_deck")]
                self.assertEqual(returned, [p for p, a in ((0, mine), (1, theirs)) if a])
                self.assertEqual([e["player"] for e in new_events(used, done, "shuffle")], returned)
                self.assertEqual([len(e["cards"]) for e in new_events(used, done, "draw")], [4] * len(returned))
                self.assertEqual(len(done.players[1].hand), 4 if theirs else 3)
                audited(self, done)

    def test_not_using_the_power_asks_nobody(self):
        offered = self._offered()
        done = answer(offered, ())
        self.assertIsNone(done.decision)
        self.assertFalse(new_events(offered, done, "hand_to_deck", "hand_return_declined", "shuffle"))

    def test_empty_hand_return_is_eg1_but_keeping_is_answerable(self):
        offered = self._offered(hand=())
        used = answer(offered, offered.decision.options)
        self.assertEqual(used.players[0].hand, [])
        self.assertEqual((used.decision.context_value("unresolved_choices"), used.decision.context_value("unresolved_code")), ((1,), EG1))
        rejects(self, used, ResolveDecision(0, used.decision.id, (1,)), EG1)
        kept = answer(used, ())
        self.assertEqual(kept.decision.context_value("unresolved_choices", ()), ())  # 相手は手札がある
        empty_opponent = self._offered(opponent_hand=())
        step = answer(answer(empty_opponent, empty_opponent.decision.options), (1,))
        self.assertEqual((step.decision.player, step.decision.context_value("unresolved_code")), (1, EG1))
        rejects(self, step, ResolveDecision(1, step.decision.id, (1,)), EG1)
        audited(self, answer(step, ()))

    def test_draw_shortage_draws_what_it_can(self):
        """p.312: 効果で引くときに山札が足りなければ、引けるだけ引く（負けではない）。"""
        offered = self._offered(hand=(POTION,), deck=[])
        used = answer(offered, offered.decision.options)
        done = answer(answer(used, (1,)), ())
        self.assertEqual([len(e["cards"]) for e in new_events(used, done, "draw")], [1])
        self.assertEqual((len(done.players[0].hand), done.players[0].deck, done.phase), (1, [], Phase.MAIN))

    def test_returned_cards_are_not_revealed(self):
        offered = self._offered()
        used = answer(offered, offered.decision.options)
        done = answer(used, (1,))
        (event,) = new_events(used, done, "hand_to_deck")
        for viewer in (1, None):
            seen = [e for e in visible_log(done, viewer) if e["kind"] == "hand_to_deck"][-1]
            self.assertNotIn("cards", seen)
        self.assertEqual([e for e in visible_log(done, 0) if e["kind"] == "hand_to_deck"][-1]["cards"], event["cards"])
        self.assertIn("hand_return_declined", PUBLIC_EVENTS)

    def test_invalid_answers_change_nothing(self):
        offered = self._offered()
        used = answer(offered, offered.decision.options)
        for choices in ((2,), (1, 1), (0,)):
            with self.subTest(choices=choices):
                before = snap(used)
                with self.assertRaises(IllegalActionError):
                    apply_kernel(used, ResolveDecision(0, used.decision.id, choices))
                self.assertEqual(snap(used), before)

    def test_no_opportunity_from_the_deck_or_under_chemical_gas(self):
        for card in (UE, UR):
            with self.subTest(card=card):
                wall = board(mon(H.RATTATA), hand=(WALL,), deck=[card, W, W])
                chosen = answer(apply_kernel(wall, PlayTrainer(0, uid(wall, WALL))), (uid(wall, card, zone="deck"),))
                self.assertIsNone(chosen.decision)
                self.assertFalse(new_events(wall, chosen, "pokemon_power", "entry_power_declined"))
                # 機会が過ぎたあとに宣言して使うことはできない（場に出たときの 1 回だけ）
                rejects(self, chosen, UsePokemonPower(0, bench_pid(chosen, card), 0), "POWER_NOT_USABLE_NOW", error=IllegalActionError)
        gas = board(mon(H.RATTATA), hand=(UE, W), opponent=mon(H.MUK, evolved_from=H.GRIMER))
        self.assertIsNone(play_entry(gas, UE).decision)

    def test_erikas_perfume_offers_the_owner_outside_their_turn(self):
        """エリカの香水（相手の手札のたねポケモンを相手のベンチに出させる）で手札から場に出たアンノーン[E]: 持ち主（相手）に機会があり、使ったら持ち主 → 番のプレイヤーの順に決める。"""
        state = board(mon(H.RATTATA), hand=(H.ERIKAS_PERFUME, W), opponent_hand=(UE, W, W))
        step = apply_kernel(state, PlayTrainer(0, uid(state, H.ERIKAS_PERFUME)))
        while step.decision is not None and step.decision.kind != ENTRY_POWER:
            step = answer(step, step.decision.options[:1])
        self.assertEqual((step.decision.kind, step.decision.player), (ENTRY_POWER, 1))
        self.assertIsNone(step.decision.context_value("unresolved_code", None))
        used = answer(step, step.decision.options)
        self.assertEqual((used.decision.kind, used.decision.player, used.decision.context_value("stage")), (ACCEPT_REQUEST, 1, 0))
        second = answer(used, (1,))
        self.assertEqual((second.decision.player, second.decision.context_value("stage")), (0, 1))
        done = answer(second, ())
        self.assertIsNone(done.trainer_in_use)
        self.assertEqual((done.phase, done.current_player), (Phase.MAIN, 0))
        audited(self, done)


class ReassureTest(unittest.TestCase):
    def test_heals_all_own_unowns_only(self):
        state = board(mon(UL, (PS,), damage=30, confusion=True), bench=(mon(UZ, damage=10), mon(H.RATTATA, damage=20), mon(UO)), hand=(UR,),
                      opponent=mon(UT, damage=20))
        offered = play_entry(state, UR)
        self.assertEqual(offered.decision.kind, ENTRY_POWER)
        done = same_answers(self, offered, offered.decision.options)
        p0, p1 = done.players
        self.assertEqual([(done.cards[p.card].card_id, p.damage) for p in p0.in_play()],
                         [(UL, 0), (UZ, 0), (H.RATTATA, 20), (UO, 0), (UR, 0)])
        self.assertEqual(p1.active.damage, 20)  # 相手のアンノーンは対象ではない
        self.assertTrue(p0.active.conditions.confused)  # 特殊状態は変えない
        self.assertEqual([(e["pokemon_id"], e["counters"], e["power"]) for e in new_events(offered, done, "remove_damage_counters")],
                         [(state.players[0].active.pokemon_id, 3, f"{UR}@power0"), (state.players[0].bench[0].pokemon_id, 1, f"{UR}@power0")])
        audited(self, done)

    def test_no_damage_is_allowed_and_does_nothing(self):
        state = board(mon(UL), hand=(UR,))
        offered = play_entry(state, UR)
        self.assertIsNone(offered.decision.context_value("unresolved_code", None))
        done = answer(offered, offered.decision.options)
        self.assertEqual(kinds(offered, done), ["pokemon_power"])

    def test_current_form_ditto_is_healed(self):
        state = board(mon(H.DITTO, (W,), damage=20), hand=(UR,), opponent=mon(UL))
        done = answer(play_entry(state, UR), (bench_pid(play_entry(state, UR), UR),))
        self.assertEqual(done.players[0].active.damage, 0)

    def test_face_down_card_is_read_only_when_damaged(self):
        """うらのカード（マチスの秘策）は名前のグループを読めない。ダメージがなければ読まない（結果は同じ）。ダメージがあれば FD1 で、使うを選ぶと止める（テスト専用に
        ダメージをのせた盤面）。"""
        from tests.test_secret_plan_v0_67 import place

        state = place(build_test_state([
            {"active": mon(UL), "bench": [], "hand": [H.LT_SURGES_SECRET_PLAN, H.RATTATA, UR], "deck": [W] * 10, "prizes": 6},
            {"active": mon(H.RATTATA), "deck": [W] * 10, "prizes": 6}], turn_number=TURN), H.RATTATA)
        self.assertTrue(state.is_face_down(state.players[0].bench[0]))
        offered = play_entry(state, UR)
        self.assertIsNone(offered.decision.context_value("unresolved_code", None))
        damaged = state.clone()
        damaged.players[0].bench[0].damage = 10
        use = E.PowerUse(0, damaged.players[0].active.pokemon_id, PowerKey(UR, 0))
        problem = E.HealAllNameGroupOnEntry().accept_problem(damaged, use)
        self.assertIsInstance(problem, HiddenPropertyRead)
        self.assertEqual(problem.code, FD1)


# ---------------------------------------------------------------- 5 章: 自分の番ごとに 1 回の特殊能力（［OBSERVE］・［SEARCH］・［LAUGH］・［TELL］）


class ObserveTest(unittest.TestCase):
    def test_looks_at_exactly_five_in_order(self):
        deck = [POTION, W, H.RATTATA, W, POTION, W, W]
        state = board(mon(UO), opponent_deck=deck, opponent_hand=(W,))
        pid = state.players[0].active.pokemon_id
        done = power(state, pid)
        (look,) = new_events(state, done, "look_at_deck_top")
        self.assertEqual((look["player"], look["owner"], look["count"], look["cards"], look["power"]),
                         (0, 1, 5, tuple(state.players[1].deck[:5]), f"{UO}@power0"))
        self.assertEqual(done.players[1].deck, state.players[1].deck)
        self.assertEqual(repr(done.rng.getstate()), repr(state.rng.getstate()))
        self.assertEqual(kinds(state, done), ["pokemon_power", "look_at_deck_top"])
        for viewer in (1, None):
            self.assertNotIn("cards", [e for e in visible_log(done, viewer) if e["kind"] == "look_at_deck_top"][-1])
        self.assertIsNone(done.decision)
        rejects(self, done, UsePokemonPower(0, pid, 0), "POWER_ALREADY_USED", error=IllegalActionError)
        audited(self, done)

    def test_short_deck(self):
        for size, code in ((0, PW3), (1, OB1), (4, OB1)):
            with self.subTest(size=size):
                state = board(mon(UO), opponent_deck=[W] * size)
                rejects(self, state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0), code)
        five = board(mon(UO), opponent_deck=[W] * 5)
        self.assertEqual(len(new_events(five, power(five, five.players[0].active.pokemon_id), "look_at_deck_top")), 1)

    def test_status_does_not_block_but_chemical_gas_does(self):
        for status in ({"sleep": True}, {"paralysis": TURN - 1}, {"confusion": True}):
            with self.subTest(status=status):
                state = board(mon(UO, **status))
                self.assertEqual(kinds(state, power(state, state.players[0].active.pokemon_id))[-1], "look_at_deck_top")
        bench = board(mon(H.RATTATA), bench=(mon(UO),))
        self.assertEqual(kinds(bench, power(bench, bench.players[0].bench[0].pokemon_id))[-1], "look_at_deck_top")
        gas = board(mon(UO), opponent=mon(H.MUK, evolved_from=H.GRIMER))
        rejects(self, gas, UsePokemonPower(0, gas.players[0].active.pokemon_id, 0), "POWER_SUPPRESSED", error=IllegalActionError)


class SearchTest(unittest.TestCase):
    def _state(self):
        return build_test_state([
            {"active": mon(US), "bench": [H.RATTATA], "hand": [], "deck": [W] * 10, "prizes": [W, POTION, H.RATTATA, W, W, H.FIRE]},
            {"active": mon(H.RATTATA), "bench": [], "hand": [W], "deck": [W] * 10, "prizes": 6}], turn_number=TURN)

    def test_chooses_a_position_and_looks_privately(self):
        state = self._state()
        pid = state.players[0].active.pokemon_id
        asked = power(state, pid)
        self.assertEqual((asked.decision.kind, asked.decision.options, asked.decision.min_choices, asked.decision.max_choices),
                         (SELECT_PRIZE_CARD, tuple(range(6)), 1, 1))
        done = same_answers(self, asked, (2,))
        (look,) = new_events(asked, done, "look_at_card")
        self.assertEqual((look["player"], look["owner"], look["zone"], look["position"], look["card"], look["power"]),
                         (0, 0, "prize", 2, state.players[0].prizes[2], f"{US}@power0"))
        self.assertEqual(done.players[0].prizes, state.players[0].prizes)
        for viewer in (1, None):
            self.assertNotIn("card", [e for e in visible_log(done, viewer) if e["kind"] == "look_at_card"][-1])
        self.assertIsNone(observe(done, 1)["players"][0]["prizes"].get("cards") if isinstance(observe(done, 1)["players"][0]["prizes"], dict) else None)
        rejects(self, done, UsePokemonPower(0, pid, 0), "POWER_ALREADY_USED", error=IllegalActionError)
        audited(self, done)

    def test_invalid_positions_change_nothing(self):
        asked = power(self._state(), self._state().players[0].active.pokemon_id)
        for choices in ((6,), (), (0, 1)):
            with self.subTest(choices=choices):
                before = snap(asked)
                with self.assertRaises(IllegalActionError):
                    apply_kernel(asked, ResolveDecision(0, asked.decision.id, choices))
                self.assertEqual(snap(asked), before)


class LaughTest(unittest.TestCase):
    def test_heads_each_player_shuffles_the_other_deck(self):
        state = board(mon(UL), deck=[W, POTION, H.RATTATA, W, W], opponent_deck=[POTION, W, W, H.RATTATA, W, W])
        pid = state.players[0].active.pokemon_id
        coined = with_coin_results(state, HD)
        done = power(state, pid, HD)
        self.assertEqual([(e["player"], e["shuffled_by"], e["power"]) for e in new_events(state, done, "shuffle")],
                         [(1, 0, f"{UL}@power0"), (0, 1, f"{UL}@power0")])
        rng = random.Random()
        rng.setstate(coined.rng.getstate())
        rng.getrandbits(1)
        theirs, mine = list(state.players[1].deck), list(state.players[0].deck)
        rng.shuffle(theirs)
        rng.shuffle(mine)
        self.assertEqual((done.players[1].deck, done.players[0].deck), (theirs, mine))  # 相手の山札を先に切る（実装上の順番）
        rejects(self, done, UsePokemonPower(0, pid, 0), "POWER_ALREADY_USED", error=IllegalActionError)
        audited(self, done)

    def test_status_does_not_block_the_declared_powers(self):
        """日本語の文面にねむり・マヒ・こんらんの条件はない（［SEARCH］・［LAUGH］・［TELL］も、ねむりのバトル場のカードで使える）。"""
        for card in (US, UL, UT):
            with self.subTest(card=card):
                state = board(mon(card, sleep=True))
                done = power(state, state.players[0].active.pokemon_id, HD)
                self.assertEqual(kinds(state, done)[0], "pokemon_power")

    def test_tails_does_nothing_but_counts_as_used(self):
        state = board(mon(UL))
        pid = state.players[0].active.pokemon_id
        done = power(state, pid, TL)
        self.assertEqual(kinds(state, done), ["pokemon_power", "coin_flip"])
        rejects(self, done, UsePokemonPower(0, pid, 0), "POWER_ALREADY_USED", error=IllegalActionError)

    def test_other_shuffles_have_no_shuffler_field(self):
        wall = board(mon(H.RATTATA), hand=(WALL,), deck=[UE, W, W])
        chosen = answer(apply_kernel(wall, PlayTrainer(0, uid(wall, WALL))), (uid(wall, UE, zone="deck"),))
        self.assertEqual([sorted(e) for e in new_events(wall, chosen, "shuffle")], [["kind", "player", "turn"]])


class TellTest(unittest.TestCase):
    def test_heads_each_player_looks_at_the_other_hand(self):
        state = board(mon(UT), hand=(POTION, W), opponent_hand=(W, H.RATTATA, W))
        pid = state.players[0].active.pokemon_id
        done = power(state, pid, HD)
        looks = new_events(state, done, "look_at_hand")
        self.assertEqual([(e["player"], e["owner"], e["cards"], e["power"]) for e in looks],
                         [(0, 1, tuple(state.players[1].hand), f"{UT}@power0"), (1, 0, tuple(state.players[0].hand), f"{UT}@power0")])
        self.assertEqual((done.players[0].hand, done.players[1].hand), (state.players[0].hand, state.players[1].hand))
        spectator = [e for e in visible_log(done, None) if e["kind"] == "look_at_hand"]
        self.assertTrue(all("cards" not in e for e in spectator))
        for viewer in (0, 1):
            self.assertEqual([e["cards"] for e in visible_log(done, viewer) if e["kind"] == "look_at_hand"], [looks[0]["cards"], looks[1]["cards"]])
            self.assertIsNone(observe(done, None)["players"][viewer]["hand"]["cards"])
        rejects(self, done, UsePokemonPower(0, pid, 0), "POWER_ALREADY_USED", error=IllegalActionError)
        audited(self, done)

    def test_tails_and_empty_hands(self):
        state = board(mon(UT), opponent_hand=())
        self.assertEqual(kinds(state, power(state, state.players[0].active.pokemon_id, TL)), ["pokemon_power", "coin_flip"])
        done = power(state, state.players[0].active.pokemon_id, HD)
        self.assertEqual([e["cards"] for e in new_events(state, done, "look_at_hand")], [(), ()])


# ---------------------------------------------------------------- 6 章: ［ZOOM］と「にげる」


class ZoomTest(unittest.TestCase):
    def test_bench_zoom_zeroes_own_unown_retreat(self):
        state = board(mon(UL, (PS,)), bench=(mon(UZ), mon(H.RATTATA)))
        cost = E.retreat_cost(state, 0)
        z = state.players[0].bench[0].pokemon_id
        self.assertEqual((cost.minimum, cost.maximum, cost.power_zeroed, cost.zeroed), (0, 0, ((z, f"{UZ}@power0"),), ()))
        target = state.players[0].bench[1].card
        rejects(self, state, Retreat(0, tuple(state.players[0].active.energy), target), "WRONG_RETREAT_COST", error=IllegalActionError)
        done = apply_kernel(state, Retreat(0, (), target))
        (event,) = new_events(state, done, "retreat")
        self.assertEqual((event["discarded"], event["retreat_cost_power_zeroed"]), ((), ((z, f"{UZ}@power0"),)))
        self.assertNotIn("retreat_cost_zeroed", event)
        self.assertFalse(new_events(state, done, "discard_attached_trainer", "discard_from_play"))
        self.assertEqual(done.cards[done.players[0].bench[0].card].card_id, UZ)  # ［ZOOM］のカードはトラッシュしない
        audited(self, done)

    def test_only_own_unowns_while_zoom_is_benched_and_working(self):
        cases = (
            (board(mon(H.ONIX, (FT, FT, FT)), bench=(mon(UZ),)), 3),  # ほかの名前
            (board(mon(UL, (PS,)), opponent_bench=(mon(UZ),)), 1),  # 相手のベンチの［ZOOM］
            (board(mon(UZ, (PS,)), bench=(mon(UL),)), 1),  # バトル場の［ZOOM］ははたらかない
            (board(mon(UL, (PS,)), bench=(mon(UZ),), opponent=mon(H.MUK, evolved_from=H.GRIMER)), 1),  # かがくへんかガス
            (board(mon(UZ, (PS,)), bench=(mon(UZ),)), 0),  # ベンチのもう 1 匹の［ZOOM］
        )
        for state, expected in cases:
            with self.subTest(active=state.cards[state.players[0].active.card].card_id):
                self.assertEqual(E.retreat_cost(state, 0).maximum, expected)

    def test_zoom_is_not_declared(self):
        state = board(mon(UL, (PS,)), bench=(mon(UZ),))
        rejects(self, state, UsePokemonPower(0, state.players[0].bench[0].pokemon_id, 0), "POWER_NOT_DECLARABLE", error=IllegalActionError)

    def test_two_zooms_do_not_stack(self):
        state = board(mon(UL, (PS,)), bench=(mon(UZ), mon(UZ)))
        cost = E.retreat_cost(state, 0)
        self.assertEqual((cost.minimum, cost.maximum, len(cost.power_zeroed)), (0, 0, 2))

    def test_confused_unown_with_zoom_is_not_bb1(self):
        state = board(mon(UL, (PS,), confusion=True), bench=(mon(UZ),))
        target = state.players[0].bench[0].card
        failed = apply_kernel(with_coin_results(state, TL), Retreat(0, (), target))
        self.assertEqual(kinds(state, failed, "coin_flip", "retreat_failed"), ["coin_flip", "retreat_failed"])
        self.assertEqual(new_events(state, failed, "retreat_failed")[0]["discarded"], ())
        ok = apply_kernel(with_coin_results(state, HD), Retreat(0, (), target))
        self.assertEqual(kinds(state, ok, "retreat"), ["retreat"])
        audited(self, ok)

    def test_real_balloon_berry_keeps_its_own_rules(self):
        berry = board(mon(UL, (PS,), trainers=[(BALLOON_BERRY, None)]), bench=(mon(UZ), mon(H.RATTATA)))
        cost = E.retreat_cost(berry, 0)
        self.assertEqual((len(cost.zeroed), len(cost.power_zeroed), cost.maximum), (1, 1, 0))
        done = apply_kernel(berry, Retreat(0, (), berry.players[0].bench[1].card))
        self.assertEqual([e["card"] for e in new_events(berry, done, "discard_attached_trainer")], [berry.players[0].active.trainers[0].card])
        (event,) = new_events(berry, done, "retreat")
        self.assertIn("retreat_cost_zeroed", event)
        self.assertIn("retreat_cost_power_zeroed", event)
        self.assertEqual([done.cards[p.card].card_id for p in done.players[0].bench], [UZ, UL])  # ［ZOOM］のカードは残る
        confused = board(mon(UL, (PS,), confusion=True, trainers=[(BALLOON_BERRY, None)]), bench=(mon(UZ),))
        rejects(self, confused, Retreat(0, (), confused.players[0].bench[0].card), BB1)

    def test_increases_are_cp2(self):
        """［ZOOM］と決まって増やす効果（でこぼこジム・［ねんちゃくえき］）: 「すべてなくなる」を先か後かで数が変わる（v0.46・v0.81 の CP2）。順番を推測しない。"""
        bumpy = board(mon(UL, (PS, PS)), bench=(mon(UZ),), hand=(BUMPY_GYM,))
        bumpy = apply_kernel(bumpy, PlayTrainer(0, uid(bumpy, BUMPY_GYM)))
        goo = board(mon(UL, (PS, PS)), bench=(mon(UZ),), opponent=mon(H.DARK_MUK, evolved_from=H.GRIMER))
        for state, added in ((bumpy, 1), (goo, 2)):  # でこぼこジム +1・［ねんちゃくえき］ +2
            with self.subTest(added=added):
                cost = E.retreat_cost(state, 0)
                self.assertEqual(cost.readings, ((0, 0), (added, added), (added, added)))
                self.assertTrue(cost.floor_ambiguous(0) and cost.floor_ambiguous(added))
                target = state.players[0].bench[0].card
                rejects(self, state, Retreat(0, (), target), CP2)
                rejects(self, state, Retreat(0, tuple(state.players[0].active.energy[:added]), target), CP2)
        aid = board(mon(UL, (PS,)), bench=(mon(UZ), mon(H.DODRIO, evolved_from=H.DODUO)))
        self.assertEqual((E.retreat_cost(aid, 0).minimum, E.retreat_cost(aid, 0).maximum), (0, 0))  # 少なくできる効果だけなら 0 のまま

    def test_retreating_into_zoom_pays_once(self):
        """払う数は「にげる」のときの場で決める。［ZOOM］のアンノーンがバトル場に出ても払い直さず、そのあとは［ZOOM］がはたらかない（バトル場）。"""
        state = board(mon(UL, (PS,)), bench=(mon(UZ, (PS,)),))
        done = apply_kernel(state, Retreat(0, (), state.players[0].bench[0].card))
        self.assertEqual(new_events(state, done, "retreat")[0]["discarded"], ())
        self.assertEqual(done.cards[done.players[0].active.card].card_id, UZ)
        self.assertEqual(E.retreat_cost(done, 0).maximum, 1)
        self.assertEqual(done.players[0].active.energy, state.players[0].bench[0].energy)


# ---------------------------------------------------------------- 7 章: 遺跡の石版


class RuinWallTest(unittest.TestCase):
    def test_benches_one_unown_from_the_deck_and_shuffles_once(self):
        for card in (WALL, WALL2):
            with self.subTest(card=card):
                state = board(mon(H.RATTATA), hand=(card,), deck=[W, UO, H.RATTATA, UL, POTION, UE, W])
                asked = apply_kernel(state, PlayTrainer(0, uid(state, card)))
                deck = state.players[0].deck
                options = tuple(sorted(u for u in deck if state.cards[u].card_id in (UO, UL, UE)))
                self.assertEqual((asked.decision.kind, asked.decision.options, asked.decision.min_choices, asked.decision.max_choices),
                                 (BENCH_FROM_DECK, options, 1, 1))
                self.assertIn(BENCH_FROM_DECK, HIDDEN_COUNT_KINDS)
                self.assertEqual(observe(asked, 1)["decision"], {"kind": BENCH_FROM_DECK, "player": 0})  # 相手には選べるものの数も見せない
                self.assertEqual(observe(asked, None)["decision"], {"kind": BENCH_FROM_DECK, "player": 0})
                chosen = uid(state, UE, zone="deck")
                done = same_answers(self, asked, (chosen,))
                self.assertEqual(kinds(asked, done, "trainer_bench_from_deck", "shuffle"), ["trainer_bench_from_deck", "shuffle"])
                self.assertEqual(done.players[0].bench[-1].card, chosen)
                self.assertNotIn(chosen, done.players[0].deck)
                self.assertFalse(new_events(asked, done, "pokemon_power"))  # 手札から出していないので［ENGAGE］の機会はない
                self.assertIsNone(done.decision)
                self.assertIn(uid(state, card), done.players[0].discard)
                audited(self, done)

    def test_invalid_answers_change_nothing(self):
        state = board(mon(H.RATTATA), hand=(WALL,), deck=[W, UO, H.RATTATA])
        asked = apply_kernel(state, PlayTrainer(0, uid(state, WALL)))
        rattata = uid(state, H.RATTATA, zone="deck")
        for choices in ((), (rattata,), (asked.decision.options[0], rattata)):
            with self.subTest(choices=choices):
                before = snap(asked)
                with self.assertRaises(IllegalActionError):
                    apply_kernel(asked, ResolveDecision(0, asked.decision.id, choices))
                self.assertEqual(snap(asked), before)

    def test_bench_full_and_no_target(self):
        full = board(mon(H.RATTATA), bench=(H.RATTATA,) * 5, hand=(WALL,), deck=[UO])
        rejects(self, full, PlayTrainer(0, uid(full, WALL)), "BENCH_FULL", error=IllegalActionError)
        for deck in ([W, H.RATTATA], []):
            with self.subTest(deck=deck):
                state = board(mon(H.RATTATA), hand=(WALL,), deck=deck)
                rejects(self, state, PlayTrainer(0, uid(state, WALL)), ST1)

    def test_goop_gas_blocks_every_candidate_before_use(self):
        state = board(mon(H.RATTATA), hand=(H.GOOP_GAS_ATTACK, WALL), deck=[UO, UL, W])
        gas = apply_kernel(state, PlayTrainer(0, uid(state, H.GOOP_GAS_ATTACK)))
        rejects(self, gas, PlayTrainer(0, uid(gas, WALL)), GG1)


if __name__ == "__main__":
    unittest.main()
