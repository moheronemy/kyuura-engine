"""v0.55: すぐに使い終わるトレーナー 16 枚（docs/instant-trainers-v0.55.md）。

16 枚: カスミのいかり（PMCG5-075）・ロケット団のおねーさん（PMCG4-061）・礼儀作法（PMCG5-082）・トラッシュ交換（PMCG6-077）・エネルギー・リムーブ（PMCG1-070）・
超エネルギーリムーブ（PMCG1-088）・いいきずぐすり（PMCG1-075）・なんでもなおし（PMCG1-080）・ポケモンセンター（PMCG1-083）・ねむれ!ねむれ!（PMCG4-054）・
エネルギーサーキュレート（PMCG5-067）・エリカの親切（PMCG5-084）・タケシ（PMCG5-089）・サカキの切り札（PMCG6-096）・ナツメ（PMCG6-098）・ワープポイント（PMCG6-080）。
どれも kyuura データの採用（処理に使う文面は kyuura の印刷の文面。採用したデータのコミット ecb2d69。エネルギーサーキュレートは kyuura の card_differences の記録（確実）の
最新の説明が印刷の文面と同じ）と pcg-search.com の同じ版のページとの照合。kyuura の MIX-ENERGY-REMOVAL・MIX-SUPER-ENERGY-REMOVAL はのちの版の記録で使わない。
ガイドブックは読んでいない。英語版の文面・のちのルール・2002 年のサポーターの規定で、日本語版の条件を補わない。

新しい停止コード: MW1・EM1・SP1・FH1・GL1・GL2・SB1・SB2。再利用: FC1（超エネルギーリムーブ）・SG1（ワープポイント）・MH1（エンジンの共通の確かめ）。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import unittest

from kyuura_engine import (
    IllegalActionError,
    Phase,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    check_invariants,
    observe,
    state_to_dict,
    visible_log,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.decisions import (
    DISCARD_ENERGY,
    DISCARD_OPPONENT_ENERGY,
    OPPONENT_HAND_TO_DECK,
    RETURN_ENERGY,
    SELECT_COUNTER_COUNT,
    SELECT_POKEMON,
    TAKE_LOOKED_CARDS,
)
from kyuura_engine.observation import OPTION_MEANINGS, PRIVATE_FIELDS, PUBLIC_EVENTS
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests.helpers import (
    BILL,
    BROCK_TRAINER,
    CLEFAIRY_DOLL,
    DARK_VILEPLUME,
    DROWZEE,
    ENERGY_FLOW,
    ENERGY_REMOVAL,
    ERIKAS_KINDNESS,
    FIGHTING,
    FULL_HEAL,
    GIOVANNIS_LAST_RESORT,
    GIOVANNIS_MACHOP,
    GIOVANNIS_NIDOKING,
    GIOVANNIS_NIDORAN_M,
    GIOVANNIS_NIDORINO,
    GOOD_MANNERS,
    GRASS,
    GUST,
    HITMONCHAN,
    MISTYS_WRATH,
    MYSTERIOUS_FOSSIL,
    POKEMON_CENTER,
    POTION,
    PSYCHIC,
    RATTATA,
    ROCKET_ODDISH,
    ROCKETS_SNEAK_ATTACK,
    SABRINA_TRAINER,
    SABRINAS_ABRA,
    SABRINAS_DROWZEE,
    SABRINAS_GASTLY,
    SLEEP_TRAINER,
    SNORLAX,
    SUPER_ENERGY_REMOVAL,
    SUPER_POTION,
    SWITCH,
    TRASH_EXCHANGE,
    V0_55_CARDS,
    WARP_POINT,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import (
    instant_trainer_problems,
    observation_problems,
    search_retrieval_problems,
    serialization_problems,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "instant-trainers-v0.55.md"
TURN = 7
F, W, P = FIGHTING, WATER, PSYCHIC
NEW_CODES = {
    "MW1": "UNRESOLVED_MISTYS_WRATH_SHORT_DECK",
    "EM1": "UNRESOLVED_ENERGY_REMOVAL_WITHOUT_TARGET",
    "SP1": "UNRESOLVED_SUPER_POTION_UNDAMAGED_TARGET",
    "FH1": "UNRESOLVED_FULL_HEAL_SCOPE",
    "GL1": "UNRESOLVED_LAST_RESORT_WITHOUT_TARGET",
    "GL2": "UNRESOLVED_LAST_RESORT_UNDAMAGED_TARGET",
    "SB1": "UNRESOLVED_SABRINA_WITHOUT_TWO_POKEMON",
    "SB2": "UNRESOLVED_SABRINA_SOURCE_WITHOUT_ENERGY",
}
FC1 = "UNRESOLVED_STATED_CARDS_SHORT"
SG1 = "UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED"
MH1 = "UNRESOLVED_MAX_HP_DROP"
EDITIONS = {MISTYS_WRATH: "073/096", ROCKETS_SNEAK_ATTACK: "061/065", GOOD_MANNERS: "088/096", TRASH_EXCHANGE: "082/098", ENERGY_REMOVAL: "072/096",
            SUPER_ENERGY_REMOVAL: "078/096", SUPER_POTION: "070/096", FULL_HEAL: "081/096", POKEMON_CENTER: "090/096", SLEEP_TRAINER: "056/065",
            ENERGY_FLOW: "079/096", ERIKAS_KINDNESS: "089/096", BROCK_TRAINER: "067/096", GIOVANNIS_LAST_RESORT: "091/098", SABRINA_TRAINER: "074/098",
            WARP_POINT: "078/098"}
TYPES = {MISTYS_WRATH: E.LookTopTakeRestDiscardTrainer, ROCKETS_SNEAK_ATTACK: E.OpponentHandTrainerToDeck, GOOD_MANNERS: E.SearchDeckTrainer,
         TRASH_EXCHANGE: E.DiscardPileExchange, ENERGY_REMOVAL: E.DiscardAttachedEnergyTrainer, SUPER_ENERGY_REMOVAL: E.DiscardAttachedEnergyTrainer,
         SUPER_POTION: E.DiscardEnergyThenHealTrainer, FULL_HEAL: E.CureSpecialConditionsTrainer, POKEMON_CENTER: E.HealEachDamagedPokemonTrainer,
         SLEEP_TRAINER: E.CoinStatusOnOpponentActiveTrainer, ENERGY_FLOW: E.ReturnBasicEnergyToHandTrainer, ERIKAS_KINDNESS: E.HealEachDamagedPokemonTrainer,
         BROCK_TRAINER: E.HealEachDamagedPokemonTrainer, GIOVANNIS_LAST_RESORT: E.HealOwnerPokemonThenDiscardHand,
         SABRINA_TRAINER: E.MoveAllEnergyBetweenOwnerPokemon, WARP_POINT: E.SwitchBothActivesTrainer}
# サイトとの違いは表記だけ（挙動に影響しない）
NOTATION_ONLY = {SUPER_ENERGY_REMOVAL: "trainer.text.ja", SLEEP_TRAINER: "name.ja", BROCK_TRAINER: "trainer.text.ja", WARP_POINT: "trainer.text.ja"}


def mon(card, energy=(), **extra):
    return {"card": card, "energy": list(energy), **extra}


def board(hand=(), *, active=None, bench=(RATTATA,), deck=None, discard=None, opponent_hand=(), opponent_active=None, opponent_bench=(RATTATA,),
          opponent_deck=None, seed=0):
    me = {"active": active or mon(HITMONCHAN, (F,)), "bench": list(bench), "hand": list(hand)}
    if deck is not None:
        me["deck"] = list(deck)
    if discard is not None:
        me["discard"] = list(discard)
    them = {"active": opponent_active or mon(HITMONCHAN, (F, F)), "bench": list(opponent_bench), "hand": list(opponent_hand)}
    if opponent_deck is not None:
        them["deck"] = list(opponent_deck)
    return build_test_state([me, them], turn_number=TURN, current_player=0, seed=seed)


def card_of(state, card_id, zone="hand", player=0):
    return next(uid for uid in getattr(state.players[player], zone) if state.cards[uid].card_id == card_id)


def pid(state, player, card_id):
    return next(p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card_id)


def pokemon(state, pokemon_id):
    return state.find_pokemon(pokemon_id)[1]


def use(state, card_id, player=0, coins=()):
    if coins:
        state = with_coin_results(state, *coins)
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


def event(state, kind, player=None):
    return [e for e in since_play(state) if e["kind"] == kind and (player is None or e["player"] == player)]


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def finished(test, state, player=0):
    """使い終えた: 使用中のカードがなく、番は続き（同じプレイヤーの MAIN）、カードはトラッシュにあり、1 回ぶんの並び・不変条件・書き出し・観測に問題がない。"""
    test.assertIsNone(state.trainer_in_use)
    test.assertIsNone(state.decision)
    test.assertEqual((state.phase, state.current_player), (Phase.MAIN, player))
    events = [dict(e) for e in since_play(state)]
    test.assertEqual(events[-1]["kind"], "discard_trainer")
    test.assertIn(events[0]["card"], state.players[player].discard)
    test.assertEqual(instant_trainer_problems(state, events), [])
    test.assertEqual(search_retrieval_problems(state, events), [])
    audited(test, state)


def assert_stops(test, state, command, code, error=UnsupportedError):
    before = snapshot(state)
    with test.assertRaises(error) as caught:
        apply_kernel(state, command)
    test.assertEqual(caught.exception.code, code)
    test.assertEqual(snapshot(state), before)  # 状態・ログ・乱数は変わらない


def assert_use_stops(test, state, card_id, code, error=UnsupportedError):
    assert_stops(test, state, PlayTrainer(0, card_of(state, card_id)), code, error)


def assert_answer_stops(test, state, choices, code, error=UnsupportedError, player=None):
    d = state.decision
    assert_stops(test, state, ResolveDecision(d.player if player is None else player, d.id, tuple(choices)), code, error)


def total_cards(state):
    total = sum(len(p.hand) + len(p.deck) + len(p.discard) + len(p.prizes)
                + sum(len(pk.cards()) + len(pk.energy) + len(pk.trainers) + (pk.disguise is not None) for pk in p.in_play())
                for p in state.players)
    return total + (state.trainer_in_use is not None)


def uids(state):
    """どのカードがどこにあるか（重複がない）。"""
    seen = []
    for p in state.players:
        seen += p.hand + p.deck + p.discard + p.prizes
        for pk in p.in_play():
            seen += list(pk.cards()) + list(pk.energy) + [t.card for t in pk.trainers]
    if state.trainer_in_use is not None:
        seen.append(state.trainer_in_use.card)
    return seen


# ---------------------------------------------------------------- 登録・資料


class RegistrationTest(unittest.TestCase):
    def test_pool_registrations_and_types(self):
        pool = load_card_pool()
        for card_id in V0_55_CARDS:
            with self.subTest(card_id=card_id):
                definition = pool.definitions[card_id]
                self.assertEqual(definition.category, "trainer")
                self.assertTrue(definition.supported)
                entry = E.DEFAULT_EFFECTS.trainer_entry(card_id)
                self.assertIs(type(entry.effect), TYPES[card_id])
                self.assertEqual(entry.text_ja, definition.trainer_text_ja)
                self.assertEqual(entry.play_text_ja, definition.trainer_text_ja)  # 処理に使う文面は kyuura の印刷の文面
                self.assertEqual(entry.name_ja, definition.name_ja)
                self.assertEqual(entry.effect.check(definition), [])
                self.assertEqual(definition.trainer_kinds, ("rockets_secret_machine",) if card_id == SLEEP_TRAINER else ())
                self.assertFalse(entry.effect.may_knock_out or entry.effect.empties_active or entry.effect.enters_play or entry.effect.stays_in_play)
        extract = json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text())
        self.assertEqual(extract["pool_v0_55"], list(V0_55_CARDS))
        self.assertEqual(len(E.DEFAULT_EFFECTS.trainer_ids()), 84)  # 40（v0.54）+ 16。v0.56 で 10 枚、v0.57 でスタジアム 14 枚、v0.58 でサイキックコントロール、v0.59 で 3 枚を加えた

    def test_registration_parameters(self):
        e = {card_id: E.DEFAULT_EFFECTS.trainer_entry(card_id).effect for card_id in V0_55_CARDS}
        self.assertEqual((e[MISTYS_WRATH].look, e[MISTYS_WRATH].take), (7, 2))
        self.assertEqual((e[ENERGY_REMOVAL].opponent_cards, e[ENERGY_REMOVAL].own_cost), (1, 0))
        self.assertEqual((e[SUPER_ENERGY_REMOVAL].opponent_cards, e[SUPER_ENERGY_REMOVAL].own_cost), (2, 1))
        self.assertEqual(e[SUPER_POTION].max_counters, 4)
        self.assertEqual((e[POKEMON_CENTER].who, e[POKEMON_CENTER].counters, e[POKEMON_CENTER].discard_energy), (E.HEAL_SELF, None, True))
        self.assertEqual((e[ERIKAS_KINDNESS].who, e[ERIKAS_KINDNESS].counters, e[ERIKAS_KINDNESS].discard_energy), (E.HEAL_BOTH, 2, False))
        self.assertEqual((e[BROCK_TRAINER].who, e[BROCK_TRAINER].counters, e[BROCK_TRAINER].discard_energy), (E.HEAL_SELF, 1, False))
        self.assertEqual((e[GIOVANNIS_LAST_RESORT].owner, e[SABRINA_TRAINER].owner), ("サカキ", "ナツメ"))
        manners = e[GOOD_MANNERS]
        self.assertEqual((manners.target.kind, manners.count, manners.optional, manners.reveal, manners.no_basic_in_hand, manners.reveal_hand),
                         ("basic_pokemon", 1, True, True, True, True))

    def test_registration_rejects_text_mismatches(self):
        """登録の値（枚数・側・数・行き先・使うための条件・見せるか）が文面と合わなければ ``check`` が拒否する。"""
        d = load_card_pool().definitions
        wrong = [
            (MISTYS_WRATH, E.LookTopTakeRestDiscardTrainer(E.MISTYS_WRATH_TEXT, look=5)),
            (MISTYS_WRATH, E.LookTopTakeRestDiscardTrainer(E.MISTYS_WRATH_TEXT, take=1)),
            (ROCKETS_SNEAK_ATTACK, E.OpponentHandTrainerToDeck(E.MISTYS_WRATH_TEXT)),
            (ENERGY_REMOVAL, E.DiscardAttachedEnergyTrainer(E.ENERGY_REMOVAL_TEXT, 2)),
            (ENERGY_REMOVAL, E.DiscardAttachedEnergyTrainer(E.ENERGY_REMOVAL_TEXT, 1, own_cost=1)),
            (SUPER_ENERGY_REMOVAL, E.DiscardAttachedEnergyTrainer(E.SUPER_ENERGY_REMOVAL_TEXT, 2)),
            (SUPER_ENERGY_REMOVAL, E.DiscardAttachedEnergyTrainer(E.SUPER_ENERGY_REMOVAL_TEXT, 1, own_cost=1)),
            (SUPER_POTION, E.DiscardEnergyThenHealTrainer(E.SUPER_POTION_TEXT, max_counters=2)),
            (POKEMON_CENTER, E.HealEachDamagedPokemonTrainer(E.POKEMON_CENTER_TEXT, E.HEAL_SELF, None)),
            (POKEMON_CENTER, E.HealEachDamagedPokemonTrainer(E.POKEMON_CENTER_TEXT, E.HEAL_BOTH, None, discard_energy=True)),
            (ERIKAS_KINDNESS, E.HealEachDamagedPokemonTrainer(E.ERIKAS_KINDNESS_TEXT, E.HEAL_SELF, 2)),
            (ERIKAS_KINDNESS, E.HealEachDamagedPokemonTrainer(E.ERIKAS_KINDNESS_TEXT, E.HEAL_BOTH, 1)),
            (BROCK_TRAINER, E.HealEachDamagedPokemonTrainer(E.BROCK_TRAINER_TEXT, E.HEAL_BOTH, 1)),
            (BROCK_TRAINER, E.HealEachDamagedPokemonTrainer(E.BROCK_TRAINER_TEXT, E.HEAL_SELF, 2)),
            (GIOVANNIS_LAST_RESORT, E.HealOwnerPokemonThenDiscardHand(E.GIOVANNIS_LAST_RESORT_TEXT, owner="ナツメ")),
            (SABRINA_TRAINER, E.MoveAllEnergyBetweenOwnerPokemon(E.SABRINA_TRAINER_TEXT, owner="サカキ")),
            (GOOD_MANNERS, E.SearchDeckTrainer(E.GOOD_MANNERS_TEXT, E.CardFilter("basic_pokemon"), 1, optional=True, reveal=True, reveal_hand=True)),
            (GOOD_MANNERS, E.SearchDeckTrainer(E.GOOD_MANNERS_TEXT, E.CardFilter("basic_pokemon"), 1, optional=True, reveal=True, no_basic_in_hand=True)),
            (GOOD_MANNERS, E.SearchDeckTrainer(E.GOOD_MANNERS_TEXT, E.CardFilter("basic_pokemon"), 1, optional=False, reveal=True, no_basic_in_hand=True, reveal_hand=True)),
            (FULL_HEAL, E.CureSpecialConditionsTrainer(E.SLEEP_TRAINER_TEXT)),
            (SLEEP_TRAINER, E.CoinStatusOnOpponentActiveTrainer(E.SLEEP_TRAINER_TEXT, condition="poison")),
            (ENERGY_FLOW, E.ReturnBasicEnergyToHandTrainer(E.ENERGY_REMOVAL_TEXT)),
            (TRASH_EXCHANGE, E.DiscardPileExchange(E.ENERGY_FLOW_TEXT)),
            (WARP_POINT, E.SwitchBothActivesTrainer(E.TRASH_EXCHANGE_TEXT)),
        ]
        for card_id, effect in wrong:
            with self.subTest(card_id=card_id, effect=effect):
                self.assertNotEqual(effect.check(d[card_id]), [])

    def test_other_kinds_are_still_rejected(self):
        """ねむれ!ねむれ!の種類（ロケット団秘密メカ）だけを受け付け、ほかのカードの登録で種類を一律に受け付けない（夜の廃品回収と共通の ``secret_machine_ok``）。"""
        d = load_card_pool().definitions
        self.assertTrue(E.secret_machine_ok(d[SLEEP_TRAINER]))
        self.assertFalse(E.secret_machine_ok(d[FULL_HEAL]))
        self.assertTrue(E.DEFAULT_EFFECTS.trainer_entry("PMCG4-057").effect.secret_machine_ok)  # 夜の廃品回収（v0.53）は同じ関数に委ねる

    def test_card_sources_and_research_links(self):
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text())["cards"]
        for card_id in V0_55_CARDS:
            with self.subTest(card_id=card_id):
                record = sources[card_id]
                self.assertEqual((record["basis"], record["status"], record["play_text"]), ("kyuura_data", "adopted", {"trainer": "kyuura_printed_text"}))
                self.assertNotIn("page", json.dumps(record, ensure_ascii=False))  # ガイドブックの項目を書かない
                (check,) = record["external_checks"]
                self.assertEqual((check["site"], check["edition"]["list_number"]), ("pcg-search.com", EDITIONS[card_id]))
                if card_id in NOTATION_ONLY:
                    self.assertEqual(check["result"], "differences")
                    self.assertEqual([(x["field"], x["affects_behavior"]) for x in check["differences"]], [(NOTATION_ONLY[card_id], False)])
                else:
                    self.assertEqual((check["result"], check["differences"]), ("match", []))
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text())
        for ruling, code in NEW_CODES.items():
            with self.subTest(code=code):
                entry = links["stop_codes"][code]
                self.assertEqual(entry["kyuura_disposition"], "not_in_kyuura")
                self.assertIn({"version": "v0.55", "document": "docs/instant-trainers-v0.55.md", "ruling_id": ruling}, entry["engine_rulings"])
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (122, 123))  # v0.56 で LS1・RT1・RG1・MY1・MS1・KG1 を加えた、v0.57 で STB1・TG1・FG1・FG2・EX1・VG1・VM1・CH1、v0.58 で RB1〜RB4・TE2・RT1 を加えた、v0.59 で GG1・BL1・CB1・BZ1〜BZ4 を加えた

    def test_observation_tables(self):
        self.assertEqual((OPTION_MEANINGS[TAKE_LOOKED_CARDS], OPTION_MEANINGS[OPPONENT_HAND_TO_DECK], OPTION_MEANINGS[SELECT_COUNTER_COUNT]),
                         ("card", "card", "number"))
        for kind in ("trainer_discard_energy", "trainer_return_energy", "trainer_move_energy", "trainer_switch_skipped", "discard_pile_to_deck",
                     "deck_top_to_discard", "looked_to_discard"):
            self.assertIn(kind, PUBLIC_EVENTS)
        self.assertEqual(PRIVATE_FIELDS["looked_to_hand"][0], ("cards",))
        self.assertEqual(PRIVATE_FIELDS["opponent_hand_to_deck"][0], ("card",))

    def test_document_lists_the_cards_and_codes(self):
        text = DOC.read_text(encoding="utf-8")
        for card_id in V0_55_CARDS:
            self.assertIn(card_id, text)
        for ruling, code in NEW_CODES.items():
            self.assertIn(ruling, text)
            self.assertIn(code, text)
        for needle in (FC1, SG1, MH1, "MIX-ENERGY-REMOVAL", "MIX-SUPER-ENERGY-REMOVAL", "pcg-search.com"):
            self.assertIn(needle, text)


# ---------------------------------------------------------------- 山札・手札・トラッシュ


class MistysWrathTest(unittest.TestCase):
    """カスミのいかり: 山札の上から 7 枚を見て、2 枚を手札に加え、残りをトラッシュする。"""

    def state(self, deck_size=10):
        deck = [W, F, POTION, BILL, W, F, GUST, SWITCH, W, F][:deck_size] + [W] * max(0, deck_size - 10)
        return board([MISTYS_WRATH], deck=deck)

    def test_look_take_two_discard_rest(self):
        state = self.state()
        deck = list(state.players[0].deck)
        before = total_cards(state)
        looking = use(state, MISTYS_WRATH)
        d = looking.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (TAKE_LOOKED_CARDS, 0, tuple(deck[:7]), 2, 2))
        audited(self, looking)
        done = answer(looking, (deck[5], deck[1]))
        self.assertEqual(kinds(done), ["play_trainer", "look_at_deck_top", "looked_to_hand", "looked_to_discard", "discard_trainer"])
        self.assertEqual(event(done, "looked_to_hand")[0]["cards"], (deck[1], deck[5]))
        self.assertEqual(done.players[0].hand, [deck[1], deck[5]])
        self.assertEqual(done.players[0].deck, deck[7:])  # 下の並びは変えず、切らない
        self.assertEqual(done.players[0].discard[:5], [deck[i] for i in (0, 2, 3, 4, 6)])
        self.assertEqual(total_cards(done), before)
        finished(self, done)
        # 手札に加えたカードは使ったプレイヤーだけ、トラッシュしたカードは公開
        for viewer, sees in ((0, True), (1, False), (None, False)):
            with self.subTest(viewer=viewer):
                log = visible_log(done, viewer)
                self.assertEqual("cards" in [e for e in log if e["kind"] == "looked_to_hand"][-1], sees)
                self.assertEqual("cards" in [e for e in log if e["kind"] == "look_at_deck_top"][-1], sees)
                self.assertIn("cards", [e for e in log if e["kind"] == "looked_to_discard"][-1])

    def test_answers_must_be_exactly_two_of_the_looked_cards(self):
        looking = use(self.state(), MISTYS_WRATH)
        deck = looking.players[0].deck
        for bad in ((deck[0],), (deck[0], deck[1], deck[2]), (deck[0], deck[7]), (deck[0], deck[0])):
            with self.subTest(bad=bad):
                before = snapshot(looking)
                with self.assertRaises(IllegalActionError):
                    answer(looking, bad)
                self.assertEqual(snapshot(looking), before)
        assert_answer_stops(self, looking, (deck[0], deck[1]), "NOT_YOUR_DECISION", IllegalActionError, player=1)

    def test_exactly_seven_and_short_deck(self):
        """山札がちょうど 7 枚なら使え、山札は 0 枚になる。7 枚より少なければ（0・1・2・6 枚）MW1 で使う前に止める。"""
        looking = use(self.state(7), MISTYS_WRATH)
        done = answer(looking, looking.decision.options[:2])
        self.assertEqual(done.players[0].deck, [])
        finished(self, done)
        for size in (0, 1, 2, 6):
            with self.subTest(size=size):
                assert_use_stops(self, self.state(size), MISTYS_WRATH, NEW_CODES["MW1"])


class RocketsSneakAttackTest(unittest.TestCase):
    """ロケット団のおねーさん: 相手の手札を見て、トレーナーカードがあれば 1 枚を選んで相手の山札にもどさせ、切る。"""

    def test_look_choose_return_and_shuffle(self):
        state = board([ROCKETS_SNEAK_ATTACK], opponent_hand=[W, POTION, MYSTERIOUS_FOSSIL, BILL])
        hand = list(state.players[1].hand)
        before = total_cards(state)
        looking = use(state, ROCKETS_SNEAK_ATTACK)
        d = looking.decision
        # トレーナーカードは手札にある間の印刷の分類（なにかの化石も含む）。選ぶのは使ったプレイヤー
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (OPPONENT_HAND_TO_DECK, 0, tuple(hand[1:]), 1, 1))
        # 選べるものの中身は、見た使ったプレイヤーだけ（相手・観戦者には数だけ）
        self.assertEqual([o.get("card_id") for o in observe(looking, 0)["decision"]["options"]], [POTION, MYSTERIOUS_FOSSIL, BILL])
        self.assertNotIn("options", observe(looking, 1)["decision"])
        self.assertNotIn("options", observe(looking, None)["decision"])
        audited(self, looking)
        assert_answer_stops(self, looking, (hand[0],), "INVALID_CHOICE", IllegalActionError)
        done = answer(looking, (hand[2],))
        self.assertEqual(kinds(done), ["play_trainer", "look_at_hand", "opponent_hand_to_deck", "shuffle", "discard_trainer"])
        self.assertNotIn(hand[2], done.players[1].hand)
        self.assertIn(hand[2], done.players[1].deck)
        self.assertEqual(event(done, "shuffle")[0]["player"], 1)
        self.assertEqual(total_cards(done), before)
        finished(self, done)
        for viewer, sees in ((0, True), (1, True), (None, False)):
            with self.subTest(viewer=viewer):
                self.assertEqual("card" in [e for e in visible_log(done, viewer) if e["kind"] == "opponent_hand_to_deck"][-1], sees)
                self.assertEqual("cards" in [e for e in visible_log(done, viewer) if e["kind"] == "look_at_hand"][-1], sees)
        self.assertIsNone(observe(done, 0)["players"][1]["hand"]["cards"])  # 一度見ただけで、あとで手札を公開しない

    def test_no_trainer_does_not_shuffle(self):
        for hand in ([], [W, F]):
            with self.subTest(hand=hand):
                done = use(board([ROCKETS_SNEAK_ATTACK], opponent_hand=hand), ROCKETS_SNEAK_ATTACK)
                self.assertEqual(kinds(done), ["play_trainer", "look_at_hand", "discard_trainer"])
                finished(self, done)


class GoodMannersTest(unittest.TestCase):
    """礼儀作法: 手札にたねポケモンがない時だけ使える。手札を見せ、山札のたねポケモン 1 枚を見せて手札に加えてよい。切る。"""

    def test_reveal_hand_then_search_basic(self):
        state = board([GOOD_MANNERS, W, MYSTERIOUS_FOSSIL], deck=[W, RATTATA, POTION, DROWZEE, CLEFAIRY_DOLL])
        searching = use(state, GOOD_MANNERS)
        d = searching.decision
        deck_basics = tuple(uid for uid in searching.players[0].deck if searching.cards[uid].card_id in (RATTATA, DROWZEE))
        self.assertEqual((d.player, d.min_choices, d.max_choices), (0, 0, 1))
        self.assertEqual(tuple(sorted(d.options)), tuple(sorted(deck_basics)))  # ピッピ人形はトレーナーカード
        self.assertEqual(kinds(searching), ["play_trainer", "reveal_hand"])
        self.assertEqual(sorted(event(searching, "reveal_hand")[0]["cards"]), sorted(searching.players[0].hand))
        self.assertIn("cards", [e for e in visible_log(searching, 1) if e["kind"] == "reveal_hand"][-1])  # 相手プレイヤーに見せる
        audited(self, searching)
        done = answer(searching, (deck_basics[0],))
        self.assertEqual(kinds(done), ["play_trainer", "reveal_hand", "reveal_from_deck", "shuffle", "discard_trainer"])
        finished(self, done)
        declined = answer(searching, ())
        self.assertEqual(kinds(declined), ["play_trainer", "reveal_hand", "trainer_take_none", "shuffle", "discard_trainer"])
        finished(self, declined)

    def test_basic_in_hand_and_no_target(self):
        assert_use_stops(self, board([GOOD_MANNERS, RATTATA]), GOOD_MANNERS, "BASIC_POKEMON_IN_HAND", IllegalActionError)
        # なにかの化石・ピッピ人形は手札ではトレーナーカードなので、たねポケモンではない
        done = use(board([GOOD_MANNERS, MYSTERIOUS_FOSSIL, CLEFAIRY_DOLL], deck=[W, F]), GOOD_MANNERS)
        self.assertEqual(kinds(done), ["play_trainer", "reveal_hand", "trainer_take_none", "shuffle", "discard_trainer"])
        finished(self, done)


class TrashExchangeTest(unittest.TestCase):
    """トラッシュ交換: トラッシュの枚数を数え、すべて山札にもどして切り、上から同じ枚数をトラッシュする。"""

    def test_count_return_shuffle_and_discard(self):
        state = board([TRASH_EXCHANGE], deck=[W] * 5, discard=[F, POTION, BILL])
        before = total_cards(state)
        done = use(state, TRASH_EXCHANGE)
        self.assertEqual(kinds(done), ["play_trainer", "discard_pile_to_deck", "shuffle", "deck_top_to_discard", "discard_trainer"])
        self.assertEqual(len(event(done, "discard_pile_to_deck")[0]["cards"]), 3)  # 使っているこのカードは数えない
        self.assertEqual(len(event(done, "deck_top_to_discard")[0]["cards"]), 3)
        self.assertEqual((len(done.players[0].deck), len(done.players[0].discard)), (5, 4))
        self.assertEqual(total_cards(done), before)
        finished(self, done)

    def test_empty_discard_still_shuffles(self):
        done = use(board([TRASH_EXCHANGE], deck=[W] * 3, discard=[]), TRASH_EXCHANGE)
        self.assertEqual(kinds(done), ["play_trainer", "discard_pile_to_deck", "shuffle", "deck_top_to_discard", "discard_trainer"])
        self.assertEqual(event(done, "deck_top_to_discard")[0]["cards"], ())
        finished(self, done)


# ---------------------------------------------------------------- 場のエネルギーカード


class EnergyRemovalTest(unittest.TestCase):
    """エネルギー・リムーブ: 相手の場のポケモンについているエネルギーカードを 1 枚はがしてすてる。"""

    def test_choose_any_opponent_energy(self):
        state = board([ENERGY_REMOVAL], opponent_bench=[mon(RATTATA, (W,))])
        opponent = state.players[1]
        cards = tuple(opponent.active.energy) + tuple(opponent.bench[0].energy)
        choosing = use(state, ENERGY_REMOVAL)
        d = choosing.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (DISCARD_OPPONENT_ENERGY, 0, cards, 1, 1))
        assert_answer_stops(self, choosing, (state.players[0].active.energy[0],), "INVALID_CHOICE", IllegalActionError)  # 自分のカードは選べない
        assert_answer_stops(self, choosing, (cards[2],), "NOT_YOUR_DECISION", IllegalActionError, player=1)
        done = answer(choosing, (cards[2],))
        self.assertEqual(kinds(done), ["play_trainer", "trainer_discard_energy", "discard_trainer"])
        self.assertEqual(done.players[1].bench[0].energy, [])
        self.assertIn(cards[2], done.players[1].discard)  # 持ち主（相手）のトラッシュ
        self.assertEqual(sorted(uids(done)), sorted(uids(state)))
        finished(self, done)

    def test_no_opponent_energy_is_em1(self):
        state = board([ENERGY_REMOVAL], opponent_active=mon(HITMONCHAN), opponent_bench=[RATTATA])
        assert_use_stops(self, state, ENERGY_REMOVAL, NEW_CODES["EM1"])


class SuperEnergyRemovalTest(unittest.TestCase):
    """超エネルギーリムーブ: 自分のエネルギーカード 1 枚をはがしてすてることによって、相手のポケモン 1 匹から 2 枚をはがしてすてる。"""

    def state(self, *, own=(F,), opponent_active=(F, F), opponent_bench=(W,)):
        return board([SUPER_ENERGY_REMOVAL], active=mon(HITMONCHAN, own), opponent_active=mon(HITMONCHAN, opponent_active),
                     opponent_bench=[mon(RATTATA, opponent_bench)])

    def test_stages_in_order(self):
        state = self.state()
        before = total_cards(state)
        own = state.players[0].active.energy[0]
        paying = use(state, SUPER_ENERGY_REMOVAL)
        self.assertEqual((paying.decision.kind, paying.decision.options, paying.decision.context_value("stage")), (DISCARD_ENERGY, (own,), 1))
        selecting = answer(paying, (own,))
        self.assertIn(own, selecting.players[0].discard)
        d = selecting.decision
        rattata = selecting.players[1].bench[0].pokemon_id
        self.assertEqual((d.kind, d.player, d.context_value("unresolved_choices")), (SELECT_POKEMON, 0, (rattata,)))
        # 1 枚しかないポケモンは選べるが選ぶと FC1。前の段階（自分のカードのトラッシュ）は取り消さない
        assert_answer_stops(self, selecting, (rattata,), FC1)
        active = selecting.players[1].active
        choosing = answer(selecting, (active.pokemon_id,))
        self.assertEqual((choosing.decision.kind, choosing.decision.options, choosing.decision.min_choices, choosing.decision.max_choices),
                         (DISCARD_OPPONENT_ENERGY, tuple(active.energy), 2, 2))
        assert_answer_stops(self, choosing, (active.energy[0],), "INVALID_CHOICE_COUNT", IllegalActionError)
        done = answer(choosing, tuple(active.energy))
        self.assertEqual(kinds(done), ["play_trainer", "trainer_discard_energy", "trainer_discard_energy", "discard_trainer"])
        self.assertEqual([e["player"] for e in event(done, "trainer_discard_energy")], [0, 1])
        self.assertEqual((done.players[0].active.energy, done.players[1].active.energy), ([], []))
        self.assertEqual(total_cards(done), before)
        finished(self, done)

    def test_conditions(self):
        assert_use_stops(self, self.state(own=()), SUPER_ENERGY_REMOVAL, "NO_ENERGY_TO_DISCARD", IllegalActionError)
        # 相手のどのポケモンも 2 枚より少なければ FC1（使う前。自分のカードはすてない）
        assert_use_stops(self, self.state(opponent_active=(F,), opponent_bench=(W,)), SUPER_ENERGY_REMOVAL, FC1)
        assert_use_stops(self, self.state(opponent_active=(), opponent_bench=()), SUPER_ENERGY_REMOVAL, FC1)

    def test_bench_pokemon_from_a_two_card_bench(self):
        """2 枚以上ついていれば控えポケモンも選べる。3 枚ついていれば、その中から 2 枚を選ぶ。"""
        state = self.state(opponent_active=(F,), opponent_bench=(W, W, F))
        selecting = answer(use(state, SUPER_ENERGY_REMOVAL), state.players[0].active.energy)
        bench = selecting.players[1].bench[0]
        choosing = answer(selecting, (bench.pokemon_id,))
        done = answer(choosing, (bench.energy[0], bench.energy[2]))
        self.assertEqual([done.cards[u].card_id for u in done.players[1].bench[0].energy], [W])
        finished(self, done)


class SuperPotionTest(unittest.TestCase):
    """いいきずぐすり: 自分のポケモン 1 匹のエネルギーカードを 1 枚はがしてすてることによって、ダメージカウンターを 4 個までとりのぞくことができる。"""

    def test_three_stages(self):
        state = board([SUPER_POTION], active=mon(HITMONCHAN, (F, F), damage=50), bench=[mon(RATTATA, (), damage=10)])
        hitmonchan = state.players[0].active
        choosing = use(state, SUPER_POTION)
        self.assertEqual((choosing.decision.kind, choosing.decision.options), (SELECT_POKEMON, (hitmonchan.pokemon_id,)))  # エネルギーのないポケモンは選べない
        paying = answer(choosing, (hitmonchan.pokemon_id,))
        self.assertEqual((paying.decision.kind, paying.decision.options, paying.decision.min_choices), (DISCARD_ENERGY, tuple(hitmonchan.energy), 1))
        counting = answer(paying, (hitmonchan.energy[1],))
        self.assertIn(hitmonchan.energy[1], counting.players[0].discard)  # 使うための条件としてこのときにトラッシュする
        self.assertEqual((counting.decision.kind, counting.decision.options), (SELECT_COUNTER_COUNT, (0, 1, 2, 3, 4)))
        audited(self, counting)
        assert_answer_stops(self, counting, (5,), "INVALID_CHOICE", IllegalActionError)
        done = answer(counting, (3,))
        self.assertEqual(kinds(done), ["play_trainer", "trainer_discard_energy", "remove_damage_counters", "discard_trainer"])
        self.assertEqual(done.players[0].active.damage, 20)
        finished(self, done)
        zero = answer(counting, (0,))
        self.assertEqual((zero.players[0].active.damage, event(zero, "remove_damage_counters")[0]["counters"]), (50, 0))
        finished(self, zero)

    def test_fewer_counters_than_four(self):
        state = board([SUPER_POTION], active=mon(HITMONCHAN, (F,), damage=20))
        counting = answer(answer(use(state, SUPER_POTION), (state.players[0].active.pokemon_id,)), state.players[0].active.energy)
        self.assertEqual(counting.decision.options, (0, 1, 2))

    def test_conditions_and_sp1(self):
        assert_use_stops(self, board([SUPER_POTION], active=mon(HITMONCHAN, (), damage=30)), SUPER_POTION, "NO_ENERGY_TO_DISCARD", IllegalActionError)
        assert_use_stops(self, board([SUPER_POTION], active=mon(HITMONCHAN, (F,))), SUPER_POTION, NEW_CODES["SP1"])
        state = board([SUPER_POTION], active=mon(HITMONCHAN, (F,), damage=30), bench=[mon(RATTATA, (W,))])
        choosing = use(state, SUPER_POTION)
        rattata = state.players[0].bench[0].pokemon_id
        self.assertEqual(choosing.decision.context_value("unresolved_choices"), (rattata,))
        assert_answer_stops(self, choosing, (rattata,), NEW_CODES["SP1"])

    def test_max_hp_drop_with_gas_body(self):
        """［ガスのからだ］のナツメのゴース（超のエネルギーカード 1 枚ごとに最大HP + 10）のカードをはがすと最大HPが下がる。のっているダメージ以下になる答えは MH1
        （エンジンの共通の確かめ。はがすのは実際の処理の一歩）。それしか選べなければ、使う前・選ぶ前に止める（答えのない決定を残さない）。"""
        gastly = mon(SABRINAS_GASTLY, (P,), damage=40)  # 最大HP 50
        only = board([SUPER_POTION], active=gastly)
        assert_use_stops(self, only, SUPER_POTION, MH1)
        state = board([SUPER_POTION], active=gastly, bench=[mon(RATTATA, (W,), damage=10)])
        choosing = use(state, SUPER_POTION)
        assert_answer_stops(self, choosing, (state.players[0].active.pokemon_id,), MH1)
        safe = board([SUPER_POTION], active=mon(SABRINAS_GASTLY, (P,), damage=30))  # 最大HP 40 になってもダメージ 30 より大きい
        counting = answer(answer(use(safe, SUPER_POTION), (safe.players[0].active.pokemon_id,)), safe.players[0].active.energy)
        self.assertEqual(E.max_hp(counting, counting.players[0].active), 40)
        finished(self, answer(counting, (3,)))


class EnergyFlowTest(unittest.TestCase):
    """エネルギーサーキュレート: 自分の場のポケモンの基本エネルギーカードを好きなだけはがし、手札にもどしてよい。"""

    def test_any_number_from_any_pokemon(self):
        state = board([ENERGY_FLOW], active=mon(HITMONCHAN, (F, F)), bench=[mon(RATTATA, (W,))])
        cards = tuple(state.players[0].active.energy) + tuple(state.players[0].bench[0].energy)
        choosing = use(state, ENERGY_FLOW)
        d = choosing.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (RETURN_ENERGY, 0, cards, 0, 3))
        done = answer(choosing, (cards[0], cards[2]))
        self.assertEqual(kinds(done), ["play_trainer", "trainer_return_energy", "trainer_return_energy", "discard_trainer"])
        self.assertEqual(done.players[0].hand, [cards[0], cards[2]])
        self.assertEqual(done.energy_attachments_this_turn, state.energy_attachments_this_turn)  # 手札からつける回数は変えない
        finished(self, done)
        none = answer(choosing, ())
        self.assertEqual(kinds(none), ["play_trainer", "discard_trainer"])
        finished(self, none)
        all_cards = answer(choosing, cards)
        self.assertEqual(len(all_cards.players[0].hand), 3)
        finished(self, all_cards)

    def test_no_energy_ends_without_a_decision(self):
        done = use(board([ENERGY_FLOW], active=mon(HITMONCHAN), bench=[RATTATA]), ENERGY_FLOW)
        self.assertEqual(kinds(done), ["play_trainer", "discard_trainer"])
        finished(self, done)

    def test_max_hp_drop_rejects_only_that_answer(self):
        state = board([ENERGY_FLOW], active=mon(SABRINAS_GASTLY, (P,), damage=40), bench=[mon(RATTATA, (W,))])
        choosing = use(state, ENERGY_FLOW)
        assert_answer_stops(self, choosing, (state.players[0].active.energy[0],), MH1)
        finished(self, answer(choosing, (state.players[0].bench[0].energy[0],)))


class SabrinaTest(unittest.TestCase):
    """ナツメ: 「ナツメのポケモン」1 匹のエネルギーカードをすべてはがし、別の「ナツメのポケモン」1 匹につけなおす。"""

    def test_move_all_energy(self):
        state = board([SABRINA_TRAINER], active=mon(SABRINAS_DROWZEE, (P, W)), bench=[mon(SABRINAS_ABRA), RATTATA])
        drowzee, abra = state.players[0].active, state.players[0].bench[0]
        cards = list(drowzee.energy)
        source = use(state, SABRINA_TRAINER)
        d = source.decision
        self.assertEqual((d.kind, d.options, d.context_value("unresolved_choices")), (SELECT_POKEMON, (drowzee.pokemon_id, abra.pokemon_id), (abra.pokemon_id,)))
        assert_answer_stops(self, source, (abra.pokemon_id,), NEW_CODES["SB2"])
        target = answer(source, (drowzee.pokemon_id,))
        self.assertEqual(target.decision.options, (abra.pokemon_id,))  # 同じポケモンは選べない
        assert_answer_stops(self, target, (drowzee.pokemon_id,), "INVALID_CHOICE", IllegalActionError)
        done = answer(target, (abra.pokemon_id,))
        self.assertEqual(kinds(done), ["play_trainer", "trainer_move_energy", "discard_trainer"])
        self.assertEqual((pokemon(done, drowzee.pokemon_id).energy, pokemon(done, abra.pokemon_id).energy), ([], cards))
        self.assertEqual(done.energy_attachments_this_turn, state.energy_attachments_this_turn)
        finished(self, done)

    def test_sb1_sb2(self):
        assert_use_stops(self, board([SABRINA_TRAINER], active=mon(SABRINAS_DROWZEE, (P,))), SABRINA_TRAINER, NEW_CODES["SB1"])
        assert_use_stops(self, board([SABRINA_TRAINER], active=mon(SABRINAS_DROWZEE), bench=[mon(SABRINAS_ABRA)]), SABRINA_TRAINER, NEW_CODES["SB2"])

    def test_max_hp_drop_when_moving_from_gas_body(self):
        state = board([SABRINA_TRAINER], active=mon(SABRINAS_GASTLY, (P,), damage=40), bench=[mon(SABRINAS_ABRA)])
        assert_use_stops(self, state, SABRINA_TRAINER, MH1)  # どの答えも最大HPがダメージ以下になる
        fine = board([SABRINA_TRAINER], active=mon(SABRINAS_DROWZEE, (P,)), bench=[mon(SABRINAS_GASTLY, (), damage=30)])
        done = answer(answer(use(fine, SABRINA_TRAINER), (fine.players[0].active.pokemon_id,)), (fine.players[0].bench[0].pokemon_id,))
        self.assertEqual(E.max_hp(done, done.players[0].bench[0]), 50)  # つけなおしたあと、最大HPが上がる
        finished(self, done)


# ---------------------------------------------------------------- ダメージカウンター・特殊状態


class HealEachTest(unittest.TestCase):
    """ポケモンセンター・エリカの親切・タケシ（ダメージカウンターがのっているポケモン全員から）。"""

    def test_pokemon_center(self):
        state = board([POKEMON_CENTER], active=mon(HITMONCHAN, (F, F), damage=30), bench=[mon(RATTATA, (W,)), mon(DROWZEE, (P,), damage=10)],
                      opponent_active=mon(HITMONCHAN, (F,), damage=20))
        before = total_cards(state)
        done = use(state, POKEMON_CENTER)
        self.assertEqual(kinds(done), ["play_trainer", "remove_damage_counters", "trainer_discard_energy", "remove_damage_counters",
                                       "trainer_discard_energy", "discard_trainer"])
        mine = done.players[0]
        self.assertEqual((mine.active.damage, mine.active.energy, mine.bench[1].damage, mine.bench[1].energy), (0, [], 0, []))
        self.assertEqual(len(mine.bench[0].energy), 1)  # ダメージのないポケモンのエネルギーカードはすてない
        self.assertEqual(done.players[1].active.damage, 20)  # 相手のポケモンは変えない
        self.assertEqual(total_cards(done), before)
        finished(self, done)

    def test_erikas_kindness_user_then_opponent(self):
        state = board([ERIKAS_KINDNESS], active=mon(HITMONCHAN, (F,), damage=30), bench=[mon(RATTATA, (), damage=10)],
                      opponent_active=mon(HITMONCHAN, (F,), damage=50))
        done = use(state, ERIKAS_KINDNESS)
        removed = event(done, "remove_damage_counters")
        self.assertEqual([(e["player"], e["counters"]) for e in removed], [(0, 2), (0, 1), (1, 2)])
        self.assertEqual((done.players[0].active.damage, done.players[0].bench[0].damage, done.players[1].active.damage), (10, 0, 30))
        finished(self, done)

    def test_brock_one_each_and_nothing_to_do(self):
        state = board([BROCK_TRAINER], active=mon(HITMONCHAN, (F,), damage=30), bench=[mon(RATTATA, (), damage=10)],
                      opponent_active=mon(HITMONCHAN, (F,), damage=50))
        done = use(state, BROCK_TRAINER)
        self.assertEqual([(e["player"], e["counters"]) for e in event(done, "remove_damage_counters")], [(0, 1), (0, 1)])
        self.assertEqual(done.players[1].active.damage, 50)
        finished(self, done)
        for card_id in (BROCK_TRAINER, ERIKAS_KINDNESS, POKEMON_CENTER):
            with self.subTest(card_id=card_id):
                empty = use(board([card_id]), card_id)  # 全員ダメージなし: 何も起こらずに使い終わる
                self.assertEqual(kinds(empty), ["play_trainer", "discard_trainer"])
                finished(self, empty)


class GiovannisLastResortTest(unittest.TestCase):
    """サカキの切り札: 「サカキのポケモン」1 匹のダメージカウンターをすべてとりのぞき、その後、手札をすべてトラッシュする。"""

    def test_heal_then_discard_hand(self):
        state = board([GIOVANNIS_LAST_RESORT, W, POTION], active=mon(GIOVANNIS_MACHOP, (F,), damage=40), bench=[mon(GIOVANNIS_NIDORAN_M), RATTATA])
        machop, nidoran = state.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id
        hand = [uid for uid in state.players[0].hand if state.cards[uid].card_id != GIOVANNIS_LAST_RESORT]
        choosing = use(state, GIOVANNIS_LAST_RESORT)
        d = choosing.decision
        self.assertEqual((d.options, d.context_value("unresolved_choices")), ((machop, nidoran), (nidoran,)))
        assert_answer_stops(self, choosing, (nidoran,), NEW_CODES["GL2"])
        assert_answer_stops(self, choosing, (state.players[0].bench[1].pokemon_id,), "INVALID_CHOICE", IllegalActionError)
        done = answer(choosing, (machop,))
        self.assertEqual(kinds(done), ["play_trainer", "remove_damage_counters", "discard_hand", "discard_trainer"])
        self.assertEqual((done.players[0].active.damage, done.players[0].hand), (0, []))
        self.assertEqual(done.players[0].discard[:2], hand)
        finished(self, done)

    def test_empty_hand_and_codes(self):
        state = board([GIOVANNIS_LAST_RESORT], active=mon(GIOVANNIS_MACHOP, (F,), damage=10))
        done = answer(use(state, GIOVANNIS_LAST_RESORT), (state.players[0].active.pokemon_id,))
        self.assertEqual(event(done, "discard_hand")[0]["cards"], ())
        finished(self, done)
        assert_use_stops(self, board([GIOVANNIS_LAST_RESORT], active=mon(HITMONCHAN, (F,), damage=10)), GIOVANNIS_LAST_RESORT, NEW_CODES["GL1"])
        assert_use_stops(self, board([GIOVANNIS_LAST_RESORT], active=mon(GIOVANNIS_MACHOP, (F,))), GIOVANNIS_LAST_RESORT, NEW_CODES["GL2"])


class FullHealTest(unittest.TestCase):
    """なんでもなおし: 特殊状態のポケモンが自分の対戦ポケモンだけのときに回復する。ほかは FH1。"""

    def test_cures_all_conditions_of_own_active(self):
        state = board([FULL_HEAL], active=mon(HITMONCHAN, (F,), damage=20, poison=10, confusion=True))
        done = use(state, FULL_HEAL)
        self.assertEqual(kinds(done), ["play_trainer", "special_conditions_removed", "discard_trainer"])
        removed = event(done, "special_conditions_removed")[0]
        self.assertEqual((removed["player"], removed["reason"], removed["trainer_card"]), (0, "cured", since_play(done)[0]["card"]))
        self.assertEqual(done.players[0].active.conditions.names(), ())
        self.assertEqual(done.players[0].active.damage, 20)  # ダメージは変えない
        finished(self, done)
        asleep = use(board([FULL_HEAL], active=mon(HITMONCHAN, (F,), sleep=True)), FULL_HEAL)
        self.assertEqual(asleep.players[0].active.conditions.names(), ())
        finished(self, asleep)

    def test_fh1(self):
        assert_use_stops(self, board([FULL_HEAL]), FULL_HEAL, NEW_CODES["FH1"])
        assert_use_stops(self, board([FULL_HEAL], opponent_active=mon(HITMONCHAN, (F,), sleep=True)), FULL_HEAL, NEW_CODES["FH1"])
        assert_use_stops(self, board([FULL_HEAL], active=mon(HITMONCHAN, (F,), poison=10), opponent_active=mon(HITMONCHAN, (F,), sleep=True)),
                         FULL_HEAL, NEW_CODES["FH1"])


class SleepTrainerTest(unittest.TestCase):
    """ねむれ!ねむれ!: コインを投げて「おもて」なら相手の対戦ポケモンをねむりにする。"""

    def test_heads_and_tails(self):
        heads = use(board([SLEEP_TRAINER]), SLEEP_TRAINER, coins=(H,))
        self.assertEqual(kinds(heads), ["play_trainer", "coin_flip", "special_condition", "discard_trainer"])
        coin = event(heads, "coin_flip")[0]
        self.assertEqual((coin["player"], coin["source"]), (0, "trainer"))
        self.assertIn("sleep", heads.players[1].active.conditions.names())
        finished(self, heads)
        tails = use(board([SLEEP_TRAINER]), SLEEP_TRAINER, coins=(T,))
        self.assertEqual(kinds(tails), ["play_trainer", "coin_flip", "discard_trainer"])
        finished(self, tails)

    def test_immunity_and_existing_conditions(self):
        """［めんえき］（カビゴン）は防ぐ（ログ ``special_condition_prevented``）。どくは残り、マヒはねむりに置きかわる（p.322）。"""
        immune = use(board([SLEEP_TRAINER], opponent_active=mon(SNORLAX)), SLEEP_TRAINER, coins=(H,))
        self.assertIn("special_condition_prevented", kinds(immune))
        self.assertEqual(immune.players[1].active.conditions.names(), ())
        finished(self, immune)
        poisoned = use(board([SLEEP_TRAINER], opponent_active=mon(HITMONCHAN, (F,), poison=10, paralysis=TURN - 1)), SLEEP_TRAINER, coins=(H,))
        self.assertEqual(set(poisoned.players[1].active.conditions.names()), {"poison", "sleep"})
        finished(self, poisoned)


class WarpPointTest(unittest.TestCase):
    """ワープポイント: お互いの対戦ポケモンを控えと入れ替える。持ち主が選び、相手プレイヤーが先。"""

    def test_opponent_first_then_user(self):
        state = board([WARP_POINT], active=mon(HITMONCHAN, (F,), confusion=True), bench=[RATTATA, DROWZEE], opponent_bench=[RATTATA, DROWZEE])
        opponent_choice = use(state, WARP_POINT)
        d = opponent_choice.decision
        self.assertEqual((d.player, d.kind, d.options), (1, SELECT_POKEMON, tuple(p.pokemon_id for p in state.players[1].bench)))
        self.assertEqual(snapshot(pickle.loads(pickle.dumps(opponent_choice))), snapshot(opponent_choice))  # 決定の途中の保存・復元
        assert_answer_stops(self, opponent_choice, (d.options[0],), "NOT_YOUR_DECISION", IllegalActionError, player=0)
        self.assertNotIn("options", observe(opponent_choice, 0)["decision"])
        mine = answer(opponent_choice, (d.options[1],))
        self.assertEqual(mine.decision.player, 0)
        assert_answer_stops(self, mine, (mine.decision.options[0],), "NOT_YOUR_DECISION", IllegalActionError, player=1)
        done = answer(mine, (mine.decision.options[0],))
        self.assertEqual([(e["kind"], e["player"]) for e in since_play(done) if e["kind"] in ("switch", "special_conditions_removed")],
                         [("switch", 1), ("switch", 0), ("special_conditions_removed", 0)])
        self.assertEqual(done.cards[done.players[1].active.card].card_id, DROWZEE)
        self.assertEqual(done.cards[done.players[0].active.card].card_id, RATTATA)
        finished(self, done)

    def test_no_bench_skips(self):
        for bench, opponent_bench, expected in (([], [RATTATA], ["switch", "trainer_switch_skipped"]), ([RATTATA], [], ["trainer_switch_skipped", "switch"]),
                                                ([], [], ["trainer_switch_skipped", "trainer_switch_skipped"])):
            with self.subTest(bench=bench, opponent_bench=opponent_bench):
                s = use(board([WARP_POINT], bench=bench, opponent_bench=opponent_bench), WARP_POINT)
                while s.decision is not None:
                    s = answer(s, s.decision.options[:1])
                self.assertEqual([k for k in kinds(s) if k in ("switch", "trainer_switch_skipped")], expected)
                finished(self, s)

    def test_sg1_only_when_the_user_has_no_bench(self):
        """すごむ（サカキのニドキング）を受けたポケモンの持ち主がワープポイントを使い、相手が効果を与えたポケモンを選んでバトル場にもどす。使ったプレイヤーに控えが
        いれば、そのあと使ったプレイヤーの対戦ポケモンがベンチにもどって効果が消えるので問いにならない。控えがいなければ SG1（選べるが選ぶと止める・それしかなければ使う前）。"""
        king = {"card": GIOVANNIS_NIDOKING, "energy": [GRASS] * 4, "evolved_from": [GIOVANNIS_NIDORAN_M, GIOVANNIS_NIDORINO]}

        def locked(opponent_bench, user_bench):
            me = {"active": king, "bench": list(opponent_bench), "hand": []}
            them = {"active": mon(RATTATA, (F,)), "bench": list(user_bench), "hand": [GUST, WARP_POINT]}
            state = build_test_state([me, them], turn_number=TURN, current_player=0)
            attacked = apply_kernel(state, UseAttack(0, 0))
            gusted = apply_kernel(attacked, PlayTrainer(1, card_of(attacked, GUST, player=1)))
            king_pid = pid(gusted, 0, GIOVANNIS_NIDOKING)
            gusted = apply_kernel(gusted, ResolveDecision(1, gusted.decision.id, (next(o for o in gusted.decision.options if o != king_pid),)))
            self.assertIn(king_pid, [p.pokemon_id for p in gusted.players[0].bench])
            return gusted, king_pid

        lone, king_pid = locked([RATTATA], [])
        assert_stops(self, lone, PlayTrainer(1, card_of(lone, WARP_POINT, player=1)), SG1)
        two, king_pid = locked([RATTATA, DROWZEE], [])
        choosing = apply_kernel(two, PlayTrainer(1, card_of(two, WARP_POINT, player=1)))
        self.assertEqual(choosing.decision.context_value("unresolved_choices"), (king_pid,))
        assert_answer_stops(self, choosing, (king_pid,), SG1)
        other = next(o for o in choosing.decision.options if o != king_pid)
        finished(self, answer(choosing, (other,)), player=1)
        with_bench, king_pid = locked([RATTATA], [RATTATA])
        choosing = apply_kernel(with_bench, PlayTrainer(1, card_of(with_bench, WARP_POINT, player=1)))
        self.assertEqual(choosing.decision.context_value("unresolved_choices", ()), ())
        done = answer(answer(choosing, (king_pid,)), (choosing.players[1].bench[0].pokemon_id,))
        finished(self, done, player=1)


# ---------------------------------------------------------------- 共通の性質


SIMPLE_STATES = {
    TRASH_EXCHANGE: lambda: board([TRASH_EXCHANGE], deck=[W] * 3, discard=[F]),
    POKEMON_CENTER: lambda: board([POKEMON_CENTER], active=mon(HITMONCHAN, (F,), damage=10)),
    ERIKAS_KINDNESS: lambda: board([ERIKAS_KINDNESS], active=mon(HITMONCHAN, (F,), damage=10)),
    BROCK_TRAINER: lambda: board([BROCK_TRAINER], active=mon(HITMONCHAN, (F,), damage=10)),
    FULL_HEAL: lambda: board([FULL_HEAL], active=mon(HITMONCHAN, (F,), poison=10)),
}


class CommonTest(unittest.TestCase):
    def test_trainer_lock_applies_first(self):
        """［アレルギーかふん］がはたらいていれば、16 枚とも使う前に TRAINER_PREVENTED（使うための条件・未解決より先）。"""
        for card_id in V0_55_CARDS:
            with self.subTest(card_id=card_id):
                state = board([card_id], opponent_active={"card": DARK_VILEPLUME, "evolved_from": [ROCKET_ODDISH, "PMCG4-006"]})
                assert_use_stops(self, state, card_id, "TRAINER_PREVENTED", IllegalActionError)

    def test_apply_command_does_not_change_the_given_state(self):
        state = board([SUPER_POTION], active=mon(HITMONCHAN, (F, F), damage=50))
        before = snapshot(state)
        choosing = use(state, SUPER_POTION)
        self.assertEqual(snapshot(state), before)
        clone = choosing.clone()
        answer(choosing, choosing.decision.options)
        self.assertEqual(snapshot(choosing), snapshot(clone))

    def test_card_conservation_and_in_use_position(self):
        """決定を待つ間、このカードは使用中（``trainer_in_use``）で手札・トラッシュにない。どのカードも複製・消失がない。"""
        for card_id, factory in SIMPLE_STATES.items():
            with self.subTest(card_id=card_id):
                state = factory()
                self.assertEqual(sorted(uids(use(state, card_id))), sorted(uids(state)))
        state = board([MISTYS_WRATH], deck=[W] * 8)
        looking = use(state, MISTYS_WRATH)
        used = card_of(state, MISTYS_WRATH)
        self.assertEqual(looking.trainer_in_use.card, used)
        self.assertNotIn(used, looking.players[0].hand + looking.players[0].discard)
        self.assertEqual(sorted(uids(looking)), sorted(uids(state)))
        self.assertEqual(len(set(uids(looking))), len(uids(looking)))

    def test_mid_decision_serialization_round_trip(self):
        """決定を待つ状態を保存して復元し（pickle・deepcopy・clone）、同じ答えで続けると同じ結果（状態・ログ・乱数）になる（決定の種類ごと）。書き出しにも問題がない。"""
        cases = [
            (board([MISTYS_WRATH], deck=[W] * 8), MISTYS_WRATH, lambda d: d.options[:2]),
            (board([ROCKETS_SNEAK_ATTACK], opponent_hand=[POTION]), ROCKETS_SNEAK_ATTACK, lambda d: d.options[:1]),
            (board([SUPER_POTION], active=mon(HITMONCHAN, (F,), damage=30)), SUPER_POTION, lambda d: d.options[:1]),
            (board([ENERGY_FLOW]), ENERGY_FLOW, lambda d: d.options),
        ]
        latest = max(FORMAT_VERSIONS)
        for state, card_id, pick in cases:
            with self.subTest(card_id=card_id):
                pending = use(state, card_id)
                self.assertEqual(serialization_problems(pending), [])
                expected = snapshot(answer(pending, pick(pending.decision)))
                for restored in (pickle.loads(pickle.dumps(pending)), copy.deepcopy(pending), pending.clone()):
                    self.assertEqual(state_to_dict(restored, format_version=latest), state_to_dict(pending, format_version=latest))
                    self.assertEqual(snapshot(answer(restored, pick(restored.decision))), expected)

    def test_pending_decisions_are_consistent(self):
        states = [use(board([MISTYS_WRATH], deck=[W] * 8), MISTYS_WRATH), use(board([ROCKETS_SNEAK_ATTACK], opponent_hand=[POTION]), ROCKETS_SNEAK_ATTACK),
                  use(board([ENERGY_REMOVAL]), ENERGY_REMOVAL), use(board([ENERGY_FLOW]), ENERGY_FLOW),
                  use(board([WARP_POINT], opponent_bench=[RATTATA]), WARP_POINT)]
        for state in states:
            audited(self, state)
            for viewer in (0, 1, None):
                observe(state, viewer)  # どの視点でも観測できる

    def test_same_name_cards(self):
        """同じカードを 2 枚持っていれば、使ったカード（uid）だけが使用中・トラッシュになり、もう 1 枚は手札に残る（同じ番にもう 1 枚使える）。トレーナーの「タケシ」
        「ナツメ」は、同じ名前を含む「タケシの」「ナツメの」ポケモン・ナツメの眼とは別のカード。"""
        state = board([ENERGY_REMOVAL, ENERGY_REMOVAL], opponent_active=mon(HITMONCHAN, (F, F)))
        first, second = state.players[0].hand
        once = answer(apply_kernel(state, PlayTrainer(0, first)), (state.players[1].active.energy[0],))
        self.assertEqual((once.players[0].hand, once.players[0].discard[-1]), ([second], first))
        twice = answer(apply_kernel(once, PlayTrainer(0, second)), (once.players[1].active.energy[0],))
        self.assertEqual(twice.players[1].active.energy, [])
        finished(self, twice)
        pool = load_card_pool().definitions
        self.assertEqual((pool[BROCK_TRAINER].name_ja, pool[SABRINA_TRAINER].name_ja), ("タケシ", "ナツメ"))
        self.assertNotEqual(pool[SABRINA_TRAINER].name_ja, pool["PMCG6-078"].name_ja)

    def test_spectator_never_sees_hidden_cards(self):
        looking = use(board([ROCKETS_SNEAK_ATTACK], opponent_hand=[POTION, W]), ROCKETS_SNEAK_ATTACK)
        spectator = observe(looking, None)
        self.assertIsNone(spectator["players"][1]["hand"]["cards"])
        self.assertIsNone(spectator["players"][0]["hand"]["cards"])


# ---------------------------------------------------------------- 正式な対戦


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.55 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.55 の 4 組を 2 seed ずつ（席を入れかえて予定 16 局。G55-U55 と U55-G55 は同じデッキ・席・seed の同じ局なので、v0.56 から ``run`` が重複を除いて 12 局を
        行う（v0.55 の文書の「40 局」は重複を含む回数で、異なる局は 30。docs/trainer-decisions-turn-effects-v0.56.md 8 章））。どれも監査の失敗（不変条件・ログ（トレーナー 1 回ぶんの並び）・書き出し・受け付けた操作ごとの観測）・
        想定外の拒否・内部エラー・手数の上限がなく、なんでもなおし（対戦ではいつも FH1。回復は単体テスト）を除く 15 枚が使われる。勝敗は判断に使わない。"""
        from tools import existing_effect_games as games

        results = games.run(range(2), pairings=games.PAIRINGS_V0_55)
        self.assertEqual((sum(len(r["games"]) for r in results.values()), sum(len(r["duplicates"]) for r in results.values())), (12, 4))
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
        for card in V0_55_CARDS:
            if card != FULL_HEAL:
                self.assertGreater(totals.get((card, "played"), 0), 0, card)
        for card, key in ((MISTYS_WRATH, "looked_to_hand_user"), (ROCKETS_SNEAK_ATTACK, "opponent_hand_to_deck_opponent"),
                          (TRASH_EXCHANGE, "deck_top_to_discard_user"), (ENERGY_REMOVAL, "trainer_discard_energy_opponent"),
                          (SUPER_ENERGY_REMOVAL, "trainer_discard_energy_opponent"), (SUPER_POTION, "remove_damage_counters_user"),
                          (SLEEP_TRAINER, "special_condition_opponent"), (ENERGY_FLOW, "trainer_return_energy_user"),
                          (ERIKAS_KINDNESS, "remove_damage_counters_opponent"), (GIOVANNIS_LAST_RESORT, "discard_hand_user"),
                          (SABRINA_TRAINER, "trainer_move_energy_user"), (WARP_POINT, "switch_opponent"), (GOOD_MANNERS, "reveal_from_deck_user")):
            with self.subTest(card=card, key=key):
                self.assertGreater(totals.get((card, key), 0), 0)


if __name__ == "__main__":
    unittest.main()
