"""v0.56: 相手の決定・番の終わり・期限のある効果のトレーナー 10 枚（docs/trainer-decisions-turn-effects-v0.56.md）。

10 枚: エリカの香水（PMCG5-073）・マチス（PMCG5-092）・ロケット団のワナ（PMCG5-096）・ロケット団員（PMCG6-089）・マチスの交渉（PMCG5-081）・
カスミのわがまま（PMCG5-086）・カスミ（PMCG5-085）・キョウ（PMCG6-094）・見えない壁（PMCG6-079）・ロケット団の実験（PMCG6-091）。
どれも kyuura データの採用（処理に使う文面は kyuura の印刷の文面。採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合（10 枚とも一致）。
ガイドブックは読んでいない。英語版の文面・現代のルール・2002 年のサポーターの規定で、日本語版の条件を補わない。

新しい停止コード: LS1・RT1・RG1・MY1・MS1・KG1。再利用: ST1（ロケット団の実験の山札 0 枚）・G37（キョウのどくとこんじょう）・MH1（エンジンの共通の確かめ）・
v0.4b の UNRESOLVED_PREVENTED_COIN_DAMAGE（見えない壁でコインが決める控えへのダメージがどれも無効）。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import unittest

from kyuura_engine import (
    EndTurn,
    EvolvePokemon,
    IllegalActionError,
    Phase,
    PlayTrainer,
    ResolveDecision,
    UseAttack,
    check_invariants,
    observe,
    state_to_dict,
    visible_log,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.decisions import (
    ACCEPT_REQUEST,
    DISCARD_FROM_HAND,
    HAND_TO_ACTIVE,
    OPPONENT_HAND_TO_BENCH,
    SEARCH_DECK,
    SELECT_HAND_POSITIONS,
    SELECT_POKEMON,
    SELECT_PRIZE_CARD,
    SWAP_WITH_PRIZE,
)
from kyuura_engine.observation import OPTION_MEANINGS, PRIVATE_FIELDS, PUBLIC_EVENTS
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import (
    ATTACK_DAMAGE_BONUS,
    BENCH_ATTACK_DAMAGE_PREVENTION,
    POISON_ON_ATTACK_DAMAGE,
)
from tests.helpers import (
    BLAINES_RHYHORN,
    BROCKS_DIGLETT,
    DARK_GOLBAT,
    DARK_VILEPLUME,
    DEFENDER,
    ERIKAS_BELLSPROUT_40,
    ERIKAS_PERFUME,
    FIGHTING,
    FOSSIL_PSYDUCK,
    FULL_HEAL,
    GRASS,
    GRIMER,
    HITMONCHAN,
    INVISIBLE_WALL,
    KOGA_TRAINER,
    KOGAS_KOFFING,
    KOGAS_KOFFING_40,
    KOGAS_PIDGEY,
    KOGAS_WEEZING,
    LT_SURGE_TRAINER,
    LT_SURGES_TREATY,
    MISTY_TRAINER,
    MISTYS_DEWGONG,
    MISTYS_SEEL,
    MISTYS_WISH,
    MUK,
    MYSTERIOUS_FOSSIL,
    POTION,
    PSYCHIC,
    RATTATA,
    ROCKET_GRUNT,
    ROCKET_ODDISH,
    ROCKETS_EXPERIMENT,
    ROCKETS_TRAP,
    V0_56_CARDS,
    V0_69_STOP_CODE_ISSUES,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import LATEST_FORMAT, observation_problems, serialization_problems
from tests.test_instant_trainers_v0_55 import (
    answer,
    assert_answer_stops,
    assert_stops,
    assert_use_stops,
    audited,
    card_of,
    kinds,
    mon,
    pid,
    snapshot,
    uids,
    use,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "trainer-decisions-turn-effects-v0.56.md"
TURN = 7
F, W, G = FIGHTING, WATER, GRASS
NEW_CODES = {
    "LS1": "UNRESOLVED_LT_SURGE_WITHOUT_BASIC",
    "RT1": "UNRESOLVED_ROCKETS_TRAP_ZERO_CHOICE",
    "RG1": "UNRESOLVED_ROCKET_GRUNT_WITHOUT_BENCH",
    "MY1": "UNRESOLVED_MISTYS_WISH_WITHOUT_HAND",
    "MS1": "UNRESOLVED_MISTY_SELF_DAMAGE",
    "KG1": "UNRESOLVED_KOGA_POISON_ORDER",
}
ST1 = "UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET"
G37 = "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT"
EDITIONS = {ERIKAS_PERFUME: "085/096", LT_SURGE_TRAINER: "077/096", ROCKETS_TRAP: "095/096", ROCKET_GRUNT: "093/098", LT_SURGES_TREATY: "080/096",
            MISTYS_WISH: "075/096", MISTY_TRAINER: "071/096", KOGA_TRAINER: "079/098", INVISIBLE_WALL: "082/098", ROCKETS_EXPERIMENT: "094/098"}
TYPES = {ERIKAS_PERFUME: E.LookOpponentHandThenBenchBasics, LT_SURGE_TRAINER: E.BenchActiveThenHandBasicToActive,
         ROCKETS_TRAP: E.CoinReturnOpponentHandPositions, ROCKET_GRUNT: E.CoinsReturnOpponentBenchElseEndTurn,
         LT_SURGES_TREATY: E.AskOpponentEachTakePrizeElseDraw, MISTYS_WISH: E.LookPrizeAskSwapElseDraw, MISTY_TRAINER: E.TrainerTurnEffectTrainer,
         KOGA_TRAINER: E.TrainerTurnEffectTrainer, INVISIBLE_WALL: E.TrainerTurnEffectTrainer, ROCKETS_EXPERIMENT: E.SearchDeckTrainer}


def board(hand=(), *, active=None, bench=(RATTATA,), deck=None, prizes=6, opponent_hand=(), opponent_active=None, opponent_bench=(RATTATA,),
          opponent_deck=None, opponent_prizes=6, turn=TURN, player=0):
    """番のプレイヤー ``player`` の MAIN の盤面（自分 = ``player``）。"""
    me = {"active": active or mon(HITMONCHAN, (F,)), "bench": list(bench), "hand": list(hand), "prizes": prizes}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent_active or mon(HITMONCHAN, (F, F)), "bench": list(opponent_bench), "hand": list(opponent_hand), "prizes": opponent_prizes}
    if opponent_deck is not None:
        them["deck"] = list(opponent_deck)
    players = [me, them] if player == 0 else [them, me]
    return build_test_state(players, turn_number=turn, current_player=player)


def finished(test, state, player=0):
    """使い終えた: 使用中のカードがなく、同じプレイヤーの MAIN（番は続く）。カードはトラッシュにある。不変条件・書き出し・観測・ログの監査に問題がない。"""
    test.assertIsNone(state.trainer_in_use)
    test.assertIsNone(state.decision)
    test.assertEqual((state.phase, state.current_player), (Phase.MAIN, player))
    test.assertEqual(state.log[-1]["kind"], "discard_trainer")
    audited(test, state)


def attack(state, index=0, player=0):
    return apply_kernel(state, UseAttack(player, index))


def damage_events(state, since=0):
    return [dict(e) for e in state.log[since:] if e["kind"] == "damage"]


# ---------------------------------------------------------------- 登録・資料


class RegistrationTest(unittest.TestCase):
    def test_pool_registrations_and_types(self):
        pool = load_card_pool()
        for card_id in V0_56_CARDS:
            with self.subTest(card_id=card_id):
                definition = pool.definitions[card_id]
                self.assertEqual(definition.category, "trainer")
                self.assertTrue(definition.supported)
                entry = E.DEFAULT_EFFECTS.trainer_entry(card_id)
                self.assertIs(type(entry.effect), TYPES[card_id])
                self.assertEqual((entry.text_ja, entry.play_text_ja, entry.name_ja), (definition.trainer_text_ja, definition.trainer_text_ja, definition.name_ja))
                self.assertEqual(entry.effect.check(definition), [])
                self.assertEqual(definition.trainer_kinds, ())
                self.assertFalse(entry.effect.may_knock_out or entry.effect.empties_active or entry.effect.enters_play or entry.effect.stays_in_play)
        extract = json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text())
        self.assertEqual(extract["pool_v0_56"], list(V0_56_CARDS))
        self.assertEqual(len(E.DEFAULT_EFFECTS.trainer_ids()), 113)  # v0.69 で拡張パック以外の商品の同じカード 19 枚の写しを加えた。v0.67 でマチスの秘策を加えた。v0.66 で 3 枚を加えた。v0.65 で変わり身の術を加えた。v0.63 で 4 枚を加えた。 56（v0.55）+ 10。v0.57 でスタジアム 14 枚、v0.58 でサイキックコントロール、v0.59 で 3 枚を加えた、v0.61 でバトル場は穴だらけ!を加えた
        e = {card_id: E.DEFAULT_EFFECTS.trainer_entry(card_id).effect for card_id in V0_56_CARDS}
        self.assertEqual([c for c in V0_56_CARDS if e[c].may_end_turn], [ROCKET_GRUNT])
        self.assertEqual([c for c in V0_56_CARDS if e[c].takes_prizes], [LT_SURGES_TREATY])
        self.assertEqual(e[MISTY_TRAINER].turn_effect_terms(), (ATTACK_DAMAGE_BONUS, 0, "カスミ", 20))
        self.assertEqual(e[KOGA_TRAINER].turn_effect_terms(), (POISON_ON_ATTACK_DAMAGE, 0, "キョウ", None))
        self.assertEqual(e[INVISIBLE_WALL].turn_effect_terms(), (BENCH_ATTACK_DAMAGE_PREVENTION, 1, None, None))
        self.assertEqual((e[MISTY_TRAINER].discard_cost, e[KOGA_TRAINER].discard_cost), (2, 0))
        experiment = e[ROCKETS_EXPERIMENT]
        self.assertEqual((experiment.target.kind, experiment.count, experiment.optional, experiment.reveal, experiment.coin, experiment.tails_self_lock),
                         ("any", 1, False, False, True, True))
        self.assertEqual(e[ROCKETS_TRAP].count, 3)
        self.assertEqual(E.SELF_TRAINER_LOCK_TURNS, 2)

    def test_registration_rejects_text_mismatches(self):
        """登録の値（効果の種類・期限・名前・数・使うための条件・コインのあとの禁止）が文面と合わなければ ``check`` が拒否する。"""
        d = load_card_pool().definitions
        wrong = [
            (MISTY_TRAINER, E.TrainerTurnEffectTrainer(E.MISTY_TRAINER_TEXT, ATTACK_DAMAGE_BONUS, 0, owner="カスミ", amount=10, discard_cost=2)),
            (MISTY_TRAINER, E.TrainerTurnEffectTrainer(E.MISTY_TRAINER_TEXT, ATTACK_DAMAGE_BONUS, 0, owner="キョウ", amount=20, discard_cost=2)),
            (MISTY_TRAINER, E.TrainerTurnEffectTrainer(E.MISTY_TRAINER_TEXT, ATTACK_DAMAGE_BONUS, 1, owner="カスミ", amount=20, discard_cost=2)),
            (MISTY_TRAINER, E.TrainerTurnEffectTrainer(E.MISTY_TRAINER_TEXT, ATTACK_DAMAGE_BONUS, 0, owner="カスミ", amount=20)),
            (KOGA_TRAINER, E.TrainerTurnEffectTrainer(E.KOGA_TRAINER_TEXT, POISON_ON_ATTACK_DAMAGE, 1, owner="キョウ")),
            (KOGA_TRAINER, E.TrainerTurnEffectTrainer(E.KOGA_TRAINER_TEXT, ATTACK_DAMAGE_BONUS, 0, owner="キョウ", amount=20)),
            (INVISIBLE_WALL, E.TrainerTurnEffectTrainer(E.INVISIBLE_WALL_TEXT, BENCH_ATTACK_DAMAGE_PREVENTION, 0)),
            (INVISIBLE_WALL, E.TrainerTurnEffectTrainer(E.INVISIBLE_WALL_TEXT, POISON_ON_ATTACK_DAMAGE, 1)),
            (ROCKETS_TRAP, E.CoinReturnOpponentHandPositions(E.ROCKETS_TRAP_TEXT, count=2)),
            (ROCKETS_EXPERIMENT, E.SearchDeckTrainer(E.ROCKETS_EXPERIMENT_TEXT, E.CardFilter("any"), 1, optional=False, reveal=False, coin=True)),
            (ROCKETS_EXPERIMENT, E.SearchDeckTrainer(E.ROCKETS_EXPERIMENT_TEXT, E.CardFilter("any"), 1, optional=False, reveal=True, coin=True,
                                                     tails_self_lock=True)),
            (ERIKAS_PERFUME, E.LookOpponentHandThenBenchBasics(E.LT_SURGE_TRAINER_TEXT)),
            (LT_SURGE_TRAINER, E.BenchActiveThenHandBasicToActive(E.ERIKAS_PERFUME_TEXT)),
            (ROCKET_GRUNT, E.CoinsReturnOpponentBenchElseEndTurn(E.ROCKETS_TRAP_TEXT)),
            (LT_SURGES_TREATY, E.AskOpponentEachTakePrizeElseDraw(E.MISTYS_WISH_TEXT)),
            (MISTYS_WISH, E.LookPrizeAskSwapElseDraw(E.LT_SURGES_TREATY_TEXT)),
        ]
        for card_id, effect in wrong:
            with self.subTest(card_id=card_id, effect=effect):
                self.assertNotEqual(effect.check(d[card_id]), [])

    def test_entry_power_guard(self):
        state = board([DARK_GOLBAT, RATTATA])
        with self.assertRaises(RuntimeError):
            E.placed_entry_power_guard(state, card_of(state, DARK_GOLBAT))
        E.placed_entry_power_guard(state, card_of(state, RATTATA))

    def test_no_basic_pokemon_has_an_entry_power(self):
        """エリカの香水・マチスが手札から場に出すのはたねポケモンで、場に出たときに使える特殊能力（``EntryPower``）を持つたねポケモンは写しにない（どれも進化カード）。
        来たら ``placed_entry_power_guard`` が状態を変える前に RuntimeError（トレーナーの途中で特殊能力の決定を出して残りにもどる処理は加えていない。docs 4 章）。"""
        pool = load_card_pool()
        holders = []
        for card_id, definition in pool.definitions.items():
            if definition.category != "pokemon":
                continue
            for index, _ in enumerate(definition.powers):
                entry = E.DEFAULT_EFFECTS.power_entry(card_id, index)
                if entry is not None and isinstance(entry.effect, E.EntryPower):
                    holders.append((card_id, definition.stage))
        self.assertTrue(holders)
        self.assertEqual([c for c, stage in holders if stage == "basic"], [])

    def test_card_sources_and_research_links(self):
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text())["cards"]
        for card_id in V0_56_CARDS:
            with self.subTest(card_id=card_id):
                record = sources[card_id]
                self.assertEqual((record["basis"], record["status"], record["play_text"]), ("kyuura_data", "adopted", {"trainer": "kyuura_printed_text"}))
                self.assertNotIn("page", json.dumps(record, ensure_ascii=False))  # ガイドブックの項目を書かない
                (check,) = record["external_checks"]
                self.assertEqual((check["site"], check["edition"]["list_number"]), ("pcg-search.com", EDITIONS[card_id]))
                self.assertEqual((check["result"], check["differences"]), ("match", []))
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text())
        for ruling, code in NEW_CODES.items():
            with self.subTest(code=code):
                entry = links["stop_codes"][code]
                self.assertEqual((entry["kyuura_disposition"], entry["kyuura_issue"]), ("issue", V0_69_STOP_CODE_ISSUES[code]))  # v0.69: kyuura が論点に結んだ（v0.68 までは not_in_kyuura。tests/helpers.py の V0_69_STOP_CODE_ISSUES）
                self.assertIn({"version": "v0.56", "document": "docs/trainer-decisions-turn-effects-v0.56.md", "ruling_id": ruling}, entry["engine_rulings"])
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (149, 151))  # v0.68 で DR8・DR13 を加えた。v0.57 で STB1・TG1・FG1・FG2・EX1・VG1・VM1・CH1、v0.58 で RB1〜RB4・TE2・RT1 を加えた、v0.59 で GG1・BL1・CB1・BZ1〜BZ4 を加えた。v0.60 で TS1 を加え、コードのない SS1 を数えた。v0.61 で SH1・SC1・SC2・TD1 を加え、Z9 に停止コードを付けた。v0.62 で MM1・MM2・OM1・OM2 を加え、コードのない ED1 を数えた。v0.63 で QZ1 を加えた  # v0.65 で NT1〜NT3・RX1・FL1・BG1・BG2・KD1 を加えた。v0.66 で CA1・ES1〜ES3 を加えた  # v0.67 で FD1・FD2 を加えた

    def test_observation_tables(self):
        self.assertEqual([OPTION_MEANINGS[k] for k in (ACCEPT_REQUEST, OPPONENT_HAND_TO_BENCH, SELECT_HAND_POSITIONS, HAND_TO_ACTIVE, SWAP_WITH_PRIZE)],
                         ["number", "card", "position", "card", "card"])
        for kind in ("trainer_bench_from_hand", "trainer_hand_to_active", "request_answered", "trainer_effect_added", "trainer_effect_removed",
                     "trainer_turn_end"):
            self.assertIn(kind, PUBLIC_EVENTS)
        self.assertEqual(PRIVATE_FIELDS["hand_positions_to_deck"][0], ("cards",))
        self.assertEqual(PRIVATE_FIELDS["trainer_take_prize"][0], ("card",))
        self.assertEqual(PRIVATE_FIELDS["swap_prize_with_hand"][0], ("to_prize", "to_hand"))

    def test_document_lists_the_cards_and_codes(self):
        text = DOC.read_text(encoding="utf-8")
        for card_id in V0_56_CARDS:
            self.assertIn(card_id, text)
        for ruling, code in NEW_CODES.items():
            self.assertIn(ruling, text)
            self.assertIn(code, text)
        for needle in (ST1, G37, "UNRESOLVED_MAX_HP_DROP", "pcg-search.com", "形式 16", "GR-2000-P321-DAMAGE-ORDER"):
            self.assertIn(needle, text)


# ---------------------------------------------------------------- エリカの香水


class ErikasPerfumeTest(unittest.TestCase):
    def test_look_then_bench_chosen_basics_on_the_opponent_bench(self):
        """相手の手札を見て（見たプレイヤーと持ち主だけ）、使ったプレイヤーが相手の手札のたねポケモンを選び、相手のベンチの最後に出す。なにかの化石は手札ではトレーナー
        カードなので選べない。出したポケモンは新しい場のポケモン（場に出た番は今の番。持ち主はこの番には進化できない）。手札はあとで公開しない。"""
        state = board([ERIKAS_PERFUME], opponent_hand=[RATTATA, MYSTERIOUS_FOSSIL, G, RATTATA])
        choosing = use(state, ERIKAS_PERFUME)
        d = choosing.decision
        rattatas = tuple(uid for uid in state.players[1].hand if state.cards[uid].card_id == RATTATA)
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (OPPONENT_HAND_TO_BENCH, 0, rattatas, 0, 2))
        for viewer, sees in ((0, True), (1, True), (None, False)):
            self.assertEqual("cards" in [e for e in visible_log(choosing, viewer) if e["kind"] == "look_at_hand"][-1], sees)
        self.assertIsNotNone(observe(choosing, 0)["decision"]["options"])  # 見た手札から選ぶ（決めるプレイヤーには見える）
        audited(self, choosing)
        before_ids = {p.pokemon_id for p in choosing.players[1].in_play()}
        done = answer(choosing, rattatas[::-1])  # 答えの順でなく、手札の並びの順に出す
        bench = done.players[1].bench
        self.assertEqual([p.card for p in bench[-2:]], list(rattatas))
        for p in bench[-2:]:
            self.assertNotIn(p.pokemon_id, before_ids)
            self.assertEqual(p.played_turn, TURN)
        placed = [(e["player"], e["chooser"], e["card"], e["trainer_card"]) for e in done.log if e["kind"] == "trainer_bench_from_hand"]
        self.assertEqual(placed, [(1, 0, uid, card_of(state, ERIKAS_PERFUME)) for uid in rattatas])
        self.assertIsNone(observe(done, 0)["players"][1]["hand"]["cards"])
        finished(self, done)

    def test_zero_choice_no_space_and_no_basic(self):
        """0 枚は「てよい」の出さないこと。ベンチに空きがない・たねポケモンがなければ、見るだけで決定を出さない。"""
        state = board([ERIKAS_PERFUME], opponent_hand=[RATTATA])
        none = answer(use(state, ERIKAS_PERFUME), ())
        self.assertEqual(len(none.players[1].bench), 1)
        self.assertIn("trainer_take_none", kinds(none))
        finished(self, none)
        for opponent_bench, hand in (([RATTATA] * 5, [RATTATA]), ([RATTATA], [G, MYSTERIOUS_FOSSIL]), ([RATTATA], [])):
            with self.subTest(bench=len(opponent_bench), hand=hand):
                done = use(board([ERIKAS_PERFUME], opponent_bench=opponent_bench, opponent_hand=hand), ERIKAS_PERFUME)
                self.assertEqual(kinds(done), ["play_trainer", "look_at_hand", "trainer_take_none", "discard_trainer"])
                finished(self, done)

    def test_space_limits_the_number(self):
        state = board([ERIKAS_PERFUME], opponent_bench=[RATTATA] * 4, opponent_hand=[RATTATA, RATTATA, RATTATA])
        self.assertEqual(use(state, ERIKAS_PERFUME).decision.max_choices, 1)


# ---------------------------------------------------------------- マチス


class LtSurgeTest(unittest.TestCase):
    def test_bench_active_then_hand_basic_to_active(self):
        """バトル場のポケモンをベンチの最後にもどし（特殊状態・持続する効果が消える。「にげる」ではない）、選んだ手札のたねポケモンを新しい場のポケモンとしてバトル場に出す。
        出したポケモンはこの番には進化できない。"""
        state = board([LT_SURGE_TRAINER, RATTATA, G], active=mon(HITMONCHAN, (F,), poison=10))
        old = state.players[0].active.pokemon_id
        choosing = use(state, LT_SURGE_TRAINER)
        d = choosing.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (HAND_TO_ACTIVE, 0, (card_of(state, RATTATA),), 1, 1))
        done = answer(choosing, d.options)
        self.assertEqual(done.players[0].bench[-1].pokemon_id, old)
        self.assertIsNone(done.players[0].bench[-1].conditions.poison)
        new = done.players[0].active
        self.assertEqual((new.card, new.played_turn), (card_of(state, RATTATA), TURN))
        self.assertNotIn(new.pokemon_id, {p.pokemon_id for p in state.players[0].in_play()})
        self.assertIn("special_conditions_removed", kinds(done))
        self.assertNotIn("retreat", kinds(done))
        finished(self, done)

    def test_bench_full_and_ls1(self):
        assert_use_stops(self, board([LT_SURGE_TRAINER, RATTATA], bench=[RATTATA] * 5), LT_SURGE_TRAINER, "BENCH_FULL", IllegalActionError)
        assert_use_stops(self, board([LT_SURGE_TRAINER, G, MYSTERIOUS_FOSSIL]), LT_SURGE_TRAINER, NEW_CODES["LS1"])


# ---------------------------------------------------------------- ロケット団のワナ


class RocketsTrapTest(unittest.TestCase):
    def test_heads_choose_positions_without_seeing(self):
        """「おもて」なら、使ったプレイヤーが相手の手札の位置（カードの uid ではない）を最大 3 つ選び、もどして切る。もどしたカードは持ち主だけが見る。"""
        state = board([ROCKETS_TRAP], opponent_hand=[RATTATA, G, POTION, F])
        choosing = use(state, ROCKETS_TRAP, coins=(H,))
        d = choosing.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (SELECT_HAND_POSITIONS, 0, (0, 1, 2, 3), 0, 3))
        seen = observe(choosing, 0)["decision"]
        self.assertEqual((seen["meaning"], [o["value"] for o in seen["options"]]), ("position", [0, 1, 2, 3]))
        self.assertTrue(all(set(o) == {"value"} for o in seen["options"]))  # カード（uid・id）を渡さない
        self.assertNotIn("options", observe(choosing, 1)["decision"])
        audited(self, choosing)
        hand = list(state.players[1].hand)
        done = answer(choosing, (0, 2))
        self.assertEqual(done.players[1].hand, [hand[1], hand[3]])
        self.assertEqual(sorted(done.players[1].deck), sorted(state.players[1].deck + [hand[0], hand[2]]))
        returned = [e for e in done.log if e["kind"] == "hand_positions_to_deck"][-1]
        self.assertEqual((returned["player"], returned["chooser"], tuple(returned["positions"])), (1, 0, (0, 2)))
        for viewer, sees in ((0, False), (1, True), (None, False)):
            self.assertEqual("cards" in [e for e in visible_log(done, viewer) if e["kind"] == "hand_positions_to_deck"][-1], sees)
        self.assertEqual(kinds(done)[-3:], ["hand_positions_to_deck", "shuffle", "discard_trainer"])
        finished(self, done)

    def test_tails_does_nothing_and_rt1(self):
        state = board([ROCKETS_TRAP], opponent_hand=[RATTATA])
        tails = use(state, ROCKETS_TRAP, coins=(T,))
        self.assertEqual(kinds(tails), ["play_trainer", "coin_flip", "discard_trainer"])  # 切らない
        finished(self, tails)
        assert_use_stops(self, board([ROCKETS_TRAP], opponent_hand=[]), ROCKETS_TRAP, NEW_CODES["RT1"])  # コインの前
        choosing = use(state, ROCKETS_TRAP, coins=(H,))
        assert_answer_stops(self, choosing, (), NEW_CODES["RT1"])  # 0 個の答えは止める（決定は待ったまま）
        self.assertEqual(choosing.decision.max_choices, 1)  # 手札 1 枚なら最大 1


# ---------------------------------------------------------------- ロケット団員


class RocketGruntTest(unittest.TestCase):
    def test_both_heads_returns_bench_pokemon_with_cards(self):
        """2 枚とも「おもて」なら、使ったプレイヤーが相手の控えを選び、そのポケモンと重なったカード・ついているカードを持ち主の手札にもどす（きぜつではない。サイドは
        取られない）。番は続く。"""
        state = board([ROCKET_GRUNT], opponent_bench=[mon(RATTATA, (G,), damage=10)])
        choosing = use(state, ROCKET_GRUNT, coins=(H, H))
        d = choosing.decision
        target = state.players[1].bench[0]
        self.assertEqual((d.kind, d.player, d.options), (SELECT_POKEMON, 0, (target.pokemon_id,)))
        done = answer(choosing, d.options)
        self.assertEqual(done.players[1].bench, [])
        self.assertTrue({target.card, *target.energy} <= set(done.players[1].hand))
        self.assertNotIn("knock_out", kinds(done))
        self.assertEqual(len(done.players[0].prizes), len(state.players[0].prizes))
        finished(self, done)

    def test_any_tails_discards_the_card_then_ends_the_turn(self):
        """1 枚でも「うら」なら、このカードをトラッシュしてから番が終わる（番の終わり → ポケモンチェック → 相手の番）。両方のコインはいつも投げる。"""
        state = board([ROCKET_GRUNT])
        for coins in ((H, T), (T, H), (T, T)):
            with self.subTest(coins=coins):
                ended = use(state, ROCKET_GRUNT, coins=coins)
                self.assertEqual((ended.turn_number, ended.current_player, ended.phase), (TURN + 1, 1, Phase.MAIN))
                self.assertIsNone(ended.trainer_in_use)
                self.assertIn(card_of(state, ROCKET_GRUNT), ended.players[0].discard)
                tail = [e["kind"] for e in ended.log if e["turn"] == TURN]
                self.assertEqual(tail[tail.index("play_trainer"):], ["play_trainer", "coin_flip", "coin_flip", "discard_trainer", "trainer_turn_end", "turn_end",
                                                                     "pokemon_check"])
                audited(self, ended)

    def test_rg1(self):
        assert_use_stops(self, board([ROCKET_GRUNT], opponent_bench=[]), ROCKET_GRUNT, NEW_CODES["RG1"])


# ---------------------------------------------------------------- マチスの交渉


class LtSurgesTreatyTest(unittest.TestCase):
    def test_opponent_accepts_then_each_takes_one(self):
        """相手プレイヤーがたずねる決定に答え、オーケーなら使ったプレイヤー → 相手の順に、それぞれ自分のサイドの位置を選んで取る（取ったカードは取ったプレイヤーだけ）。
        きぜつで取るサイドではない。"""
        state = board([LT_SURGES_TREATY])
        asking = use(state, LT_SURGES_TREATY)
        d = asking.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (ACCEPT_REQUEST, 1, (1,), 0, 1))
        audited(self, asking)
        mine = answer(asking, (1,))
        self.assertEqual((mine.decision.kind, mine.decision.player, mine.decision.options), (SELECT_PRIZE_CARD, 0, tuple(range(6))))
        theirs = answer(mine, (2,))
        self.assertEqual((theirs.decision.kind, theirs.decision.player), (SELECT_PRIZE_CARD, 1))
        done = answer(theirs, (0,))
        self.assertEqual((len(done.players[0].prizes), len(done.players[1].prizes)), (5, 5))
        self.assertIn(state.players[0].prizes[2], done.players[0].hand)
        self.assertIn(state.players[1].prizes[0], done.players[1].hand)
        taken = [e for e in visible_log(done, 1) if e["kind"] == "trainer_take_prize"]
        self.assertEqual([("card" in e, e["player"]) for e in taken], [(False, 0), (True, 1)])
        self.assertNotIn("take_prize", kinds(done))
        self.assertNotIn("knock_out", kinds(done))
        finished(self, done)

    def test_declined_draws_one(self):
        state = board([LT_SURGES_TREATY], deck=[G, W])
        done = answer(use(state, LT_SURGES_TREATY), ())
        self.assertEqual(done.players[0].hand, [state.players[0].deck[0]])
        self.assertEqual([e["accepted"] for e in done.log if e["kind"] == "request_answered"], [False])
        finished(self, done)
        empty = answer(use(board([LT_SURGES_TREATY], deck=[]), LT_SURGES_TREATY), ())  # 山札が 0 枚でも負けではない（p.312）
        finished(self, empty)

    def test_last_prize_judged_after_the_card(self):
        """最後のサイドを取っても、このカードの途中では対戦を終えず、トラッシュしてから p.311 の表で判定する（片方だけ 0 枚なら勝ち、両方 0 枚なら同時に満たした表）。"""
        state = board([LT_SURGES_TREATY], prizes=1, opponent_prizes=2)
        mine = answer(answer(use(state, LT_SURGES_TREATY), (1,)), (0,))
        self.assertEqual(mine.phase, Phase.DECISION)  # 自分が 0 枚になっても相手が選ぶ
        self.assertIsNone(mine.result)
        done = answer(mine, (0,))
        self.assertEqual((done.phase, done.result.winner), (Phase.GAME_OVER, 0))
        self.assertIn(card_of(state, LT_SURGES_TREATY), done.players[0].discard)
        both = answer(answer(answer(use(board([LT_SURGES_TREATY], prizes=1, opponent_prizes=1), LT_SURGES_TREATY), (1,)), (0,)), (0,))
        self.assertEqual(both.phase, Phase.SUDDEN_DEATH)  # 両方が同時に勝ちの条件を満たした（p.311 の表。サドンデス）
        for s in (done, both):
            self.assertEqual(check_invariants(s), [])


# ---------------------------------------------------------------- カスミのわがまま


class MistysWishTest(unittest.TestCase):
    def test_look_ask_swap(self):
        """自分のサイドの位置を選んで見て（見たプレイヤーだけ）、相手にたずね、オーケーなら手札の 1 枚と交換する（サイドの枚数は変わらない。サイドを取ることではない）。"""
        state = board([MISTYS_WISH, G, W])
        choosing = use(state, MISTYS_WISH)
        self.assertEqual((choosing.decision.kind, choosing.decision.player, choosing.decision.options), (SELECT_PRIZE_CARD, 0, tuple(range(6))))
        asking = answer(choosing, (3,))
        self.assertEqual((asking.decision.kind, asking.decision.player), (ACCEPT_REQUEST, 1))
        self.assertEqual(asking.decision.context_value("position"), 3)
        self.assertNotIn(state.players[0].prizes[3], [v for _, v in asking.decision.context])  # 続きの情報に見たカードを書かない
        for viewer, sees in ((0, True), (1, False), (None, False)):
            self.assertEqual("card" in [e for e in visible_log(asking, viewer) if e["kind"] == "look_at_card"][-1], sees)
        self.assertIsNone(observe(asking, 1)["decision"].get("context_card"))
        audited(self, asking)
        swapping = answer(asking, (1,))
        hand = tuple(swapping.players[0].hand)
        self.assertEqual((swapping.decision.kind, swapping.decision.player, swapping.decision.options), (SWAP_WITH_PRIZE, 0, hand))
        done = answer(swapping, (hand[0],))
        self.assertEqual(done.players[0].prizes[3], hand[0])
        self.assertIn(state.players[0].prizes[3], done.players[0].hand)
        self.assertEqual(len(done.players[0].prizes), 6)
        for viewer, sees in ((0, True), (1, False), (None, False)):
            swapped = [e for e in visible_log(done, viewer) if e["kind"] == "swap_prize_with_hand"][-1]
            self.assertEqual(("to_prize" in swapped, "to_hand" in swapped, swapped["position"]), (sees, sees, 3))
        finished(self, done)

    def test_declined_draws_and_my1(self):
        state = board([MISTYS_WISH, G], deck=[W, F])
        done = answer(answer(use(state, MISTYS_WISH), (0,)), ())
        self.assertEqual(done.players[0].hand, [card_of(state, G), state.players[0].deck[0]])
        finished(self, done)
        assert_use_stops(self, board([MISTYS_WISH]), MISTYS_WISH, NEW_CODES["MY1"])  # このカードのほかに手札がない


# ---------------------------------------------------------------- カスミ


class MistyTest(unittest.TestCase):
    def misty(self, active, hand=(G, G), **extra):
        state = board([MISTY_TRAINER, *hand], active=active, **extra)
        choosing = use(state, MISTY_TRAINER)
        self.assertEqual((choosing.decision.kind, choosing.decision.min_choices, choosing.decision.max_choices), (DISCARD_FROM_HAND, 2, 2))
        return answer(choosing, choosing.decision.options[:2])

    def test_plus_twenty_at_step_six_for_mistys_pokemon(self):
        """「カスミのポケモン」のワザの相手の対戦ポケモンへのダメージは、p.321 の 6 段階（GR-2000-P321-DAMAGE-ORDER の「それ以外の効果」）で + 20（弱点のあと）。
        手札 2 枚のトラッシュは使うための条件。効果はこの番の終わりに消える。"""
        done = self.misty(mon(MISTYS_SEEL, (W,)))
        effect = done.trainer_effects[-1]
        self.assertEqual((effect.kind, effect.player, effect.created_turn, effect.expires_turn), (ATTACK_DAMAGE_BONUS, 0, TURN, TURN))
        finished(self, done)
        attacked = attack(done)
        (hit,) = damage_events(attacked, len(done.log))
        self.assertEqual((hit["amount"], hit["modifiers"]), (30, ((6, card_of(done, MISTY_TRAINER, "discard"), 20),)))
        self.assertEqual(attacked.trainer_effects, ())  # 番の終わりに消えた
        self.assertEqual([e["reason"] for e in attacked.log if e["kind"] == "trainer_effect_removed"], ["expired"])

    def test_other_pokemon_and_insufficient_hand(self):
        done = self.misty(mon(HITMONCHAN, (F,)))  # 「カスミのポケモン」でない
        (hit,) = damage_events(attack(done), len(done.log))
        self.assertNotIn("modifiers", hit)
        assert_use_stops(self, board([MISTY_TRAINER, G]), MISTY_TRAINER, "INSUFFICIENT_CARDS_IN_HAND", IllegalActionError)

    def test_two_cards_add_twice(self):
        state = board([MISTY_TRAINER, MISTY_TRAINER, G, G, G, G], active=mon(MISTYS_SEEL, (W,)))
        first, second = [uid for uid in state.players[0].hand if state.cards[uid].card_id == MISTY_TRAINER]
        once = apply_kernel(state, PlayTrainer(0, first))
        once = answer(once, [uid for uid in once.decision.options if uid != second][:2])
        twice = apply_kernel(once, PlayTrainer(0, second))
        twice = answer(twice, twice.decision.options[:2])
        (hit,) = damage_events(attack(twice), len(twice.log))
        self.assertEqual(hit["amount"], 50)

    def test_judged_by_the_current_form_at_damage_time(self):
        """「カスミのポケモン」かは、ダメージを与える時点の今の姿（いちばん上のカード）の名前で決める。カスミを使ったあとにカスミのパウワウをカスミのジュゴンに進化させても
        + 20。使ったときに場にいたかは関係しない。"""
        state = board([MISTY_TRAINER, G, G, MISTYS_DEWGONG], active=mon(MISTYS_SEEL, (W, W)))
        played = answer(use(state, MISTY_TRAINER), [uid for uid in state.players[0].hand if state.cards[uid].card_id == G])
        evolved = apply_kernel(played, EvolvePokemon(0, card_of(played, MISTYS_DEWGONG), pid(played, 0, MISTYS_SEEL)))
        (hit,) = damage_events(attack(evolved, 0), len(evolved.log))
        self.assertIn((6, card_of(evolved, MISTY_TRAINER, "discard"), 20), hit["modifiers"])

    def test_self_damage_is_ms1(self):
        """自分にもダメージを与えるワザ（カスミのジュゴンのとっしん）に + 20 を当てはめるか（「対戦ポケモンに」）は決まらない（MS1）。宣言の前に止める。"""
        done = self.misty(mon(MISTYS_DEWGONG, (W, W, W, W), evolved_from=MISTYS_SEEL))
        assert_stops(self, done, UseAttack(0, 1), NEW_CODES["MS1"])
        proceeded = attack(done, 0)  # 自分へのダメージのないワザ（こおりのつぶて）は止めない
        self.assertIn((6, card_of(done, MISTY_TRAINER, "discard"), 20), damage_events(proceeded, len(done.log))[0]["modifiers"])


# ---------------------------------------------------------------- キョウ


class KogaTest(unittest.TestCase):
    def koga(self, active, **extra):
        done = use(board([KOGA_TRAINER], active=active, **extra), KOGA_TRAINER)
        finished(self, done)
        return done

    def test_poison_after_damage(self):
        """「キョウのポケモン」がワザで相手の対戦ポケモンにダメージを与えたら、受けたポケモンをどく状態にする（その番の終わりに効果は消える）。"""
        done = self.koga(mon(KOGAS_PIDGEY, (G,)))
        attacked = attack(done)
        self.assertIsNotNone(attacked.players[1].active.conditions.poison)
        poisoned = [e for e in attacked.log if e["kind"] == "special_condition" and e.get("effect") == KOGA_TRAINER]
        self.assertEqual(len(poisoned), 1)
        self.assertEqual(attacked.trainer_effects, ())

    def test_no_damage_no_poison(self):
        """ダメージを与えない（ディフェンダーで最終ダメージ 0・「ダメージを受けない」状態）ならどくにしない。「キョウのポケモン」でなければどくにしない。"""
        for opponent in (mon(HITMONCHAN, (F,), prevent_damage=TURN - 1), mon(HITMONCHAN, (F,), trainers=[(DEFENDER, TURN)])):
            with self.subTest(opponent=opponent):
                done = self.koga(mon(KOGAS_PIDGEY, (G,)), opponent_active=opponent)
                attacked = attack(done)
                self.assertIsNone(attacked.players[1].active.conditions.poison)
        other = attack(self.koga(mon(HITMONCHAN, (F,))))
        self.assertIsNone(other.players[1].active.conditions.poison)

    def test_bench_damage_does_not_poison_and_no_double_poison(self):
        """控えへのダメージではどくにしない（「相手の対戦ポケモンに」）。すでにどく状態の対戦ポケモンをもう一度どくにしても、どくは 1 つ（受けるダメージは 10 のまま）。"""
        done = self.koga(mon(KOGAS_KOFFING_40, (G,)), opponent_active=mon(HITMONCHAN, (F,), poison=10))
        attacked = attack(with_coin_results(done, H), 0)  # おならガス（「おもて」ならお互いの控えに 10）
        self.assertEqual(attacked.players[1].active.conditions.poison.damage, 10)
        self.assertTrue(all(not p.conditions.poison for p in attacked.players[1].bench))
        self.assertTrue(any(e["kind"] == "damage" and e.get("target") == "opponent_bench" for e in attacked.log))

    def test_special_poison_of_the_same_attack_is_kg1(self):
        """同じワザで受けるダメージの違う特殊などくを与えるワザ（キョウのマタドガスのどくどくガス）は、キョウのどくとの順番が決まらない（KG1）。宣言の前に止める。"""
        done = self.koga(mon(KOGAS_WEEZING, (G, G, G), evolved_from=KOGAS_KOFFING))
        assert_stops(self, done, UseAttack(0, 1), NEW_CODES["KG1"])


# ---------------------------------------------------------------- 見えない壁


class InvisibleWallTest(unittest.TestCase):
    def test_bench_attack_damage_prevented_until_next_opponent_turn_ends(self):
        """次の相手の番が終わるまで、使ったプレイヤーの控えポケモンはワザによるダメージを受けない（受ける時点の控えで決める）。対戦ポケモンへのダメージは受ける。"""
        state = board([INVISIBLE_WALL], opponent_active=mon(ERIKAS_BELLSPROUT_40, (G,)))
        done = use(state, INVISIBLE_WALL)
        effect = done.trainer_effects[-1]
        self.assertEqual((effect.kind, effect.created_turn, effect.expires_turn), (BENCH_ATTACK_DAMAGE_PREVENTION, TURN, TURN + 1))
        finished(self, done)
        theirs = apply_kernel(done, EndTurn(0))
        self.assertEqual(len(theirs.trainer_effects), 1)  # 自分の番の終わりでは消えない
        choosing = attack(theirs, 0, player=1)  # のびるつる（相手の控えを選んで 20）
        target = choosing.decision.options[0]
        hit = apply_kernel(choosing, ResolveDecision(1, choosing.decision.id, (target,)))
        prevented = [e for e in hit.log if e["kind"] == "damage_prevented"]
        self.assertEqual([(e["pokemon_id"], e["persistent_effect"]) for e in prevented], [(target, BENCH_ATTACK_DAMAGE_PREVENTION)])
        self.assertEqual(hit.trainer_effects, ())  # 次の相手の番の終わりに消えた

    def wall_then_opponent(self, *, bench, opponent_active, me_active=None):
        state = build_test_state([{"active": me_active or mon(HITMONCHAN, (F,)), "bench": list(bench), "hand": [INVISIBLE_WALL]},
                                  {"active": opponent_active, "bench": [RATTATA]}], turn_number=TURN, current_player=0)
        return apply_kernel(use(state, INVISIBLE_WALL), EndTurn(0))

    def test_wall_ignores_gas_and_is_judged_at_damage_time(self):
        """特殊能力ではないので、かがくへんかガス（自分の控えのベトベトン）がはたらいていても消えない（カタログの定義は ``disabled_by`` が空・抑止されない）。"""
        from kyuura_engine.resolution import catalog

        self.assertEqual((catalog.INVISIBLE_WALL.disabled_by, catalog.INVISIBLE_WALL.suppressible), (frozenset(), False))
        theirs = self.wall_then_opponent(bench=[{"card": MUK, "evolved_from": GRIMER}], opponent_active=mon(ERIKAS_BELLSPROUT_40, (G,)))
        choosing = attack(theirs, 0, player=1)
        muk = pid(theirs, 0, MUK)
        hit = apply_kernel(choosing, ResolveDecision(1, choosing.decision.id, (muk,)))
        self.assertEqual([e["pokemon_id"] for e in hit.log if e["kind"] == "damage_prevented"], [muk])
        self.assertEqual(hit.players[0].bench[0].damage, 0)

    def test_own_attack_on_own_bench_is_also_prevented(self):
        """使った番の自分のワザ（タケシのディグダのミニじしん。自分の控えに 10）も「ワザによるダメージ」なので、自分の控えは受けない。対戦ポケモンへの 40 は与える。"""
        state = board([INVISIBLE_WALL], active=mon(BROCKS_DIGLETT, (F, F)))
        hit = attack(use(state, INVISIBLE_WALL), 1)
        self.assertEqual([e["target"] for e in hit.log if e["kind"] == "damage_prevented"], ["self_bench"])
        self.assertEqual((hit.players[0].bench[0].damage, hit.players[1].active.damage), (0, 40))

    def test_coin_deciding_only_walled_bench_damage(self):
        """コインが決めるのが相手の控えへのダメージだけで、その控えがどれも見えない壁で無効なら、v0.4b の UNRESOLVED_PREVENTED_COIN_DAMAGE（コインの前）。
        対戦ポケモンへのダメージは受ける（壁は控えだけ）。"""
        theirs = self.wall_then_opponent(bench=[RATTATA], opponent_active=mon(BLAINES_RHYHORN, (F, F, F)))
        assert_stops(self, theirs, UseAttack(1, 1), "UNRESOLVED_PREVENTED_COIN_DAMAGE")
        hit = attack(theirs, 0, player=1)  # ホーンアタック（対戦ポケモンへのダメージ）は受ける
        self.assertEqual(hit.players[0].active.damage, 30)


# ---------------------------------------------------------------- ロケット団の実験


class RocketsExperimentTest(unittest.TestCase):
    def test_heads_search_tails_lock_until_next_own_turn_ends(self):
        """「おもて」なら山札から 1 枚を選んで手札に加え（見せない）、切る。「うら」なら次の自分の番が終わるまでトレーナーを使えない（使った番 + 2 の終わりに消える）。"""
        state = board([ROCKETS_EXPERIMENT, POTION], deck=[RATTATA, G], active=mon(HITMONCHAN, (F,), damage=10))
        heads = use(state, ROCKETS_EXPERIMENT, coins=(H,))
        self.assertEqual((heads.decision.kind, heads.decision.min_choices), (SEARCH_DECK, 1))
        finished(self, answer(heads, heads.decision.options[:1]))
        tails = use(state, ROCKETS_EXPERIMENT, coins=(T,))
        (lock,) = tails.trainer_locks
        self.assertEqual((lock.player, lock.origin, lock.expires_turn), (0, "trainer", TURN + 2))
        finished(self, tails)
        assert_use_stops(self, tails, POTION, "TRAINER_PREVENTED", IllegalActionError)  # この番も
        later = apply_kernel(apply_kernel(tails, EndTurn(0)), EndTurn(1))
        self.assertEqual(later.turn_number, TURN + 2)
        assert_use_stops(self, later, POTION, "TRAINER_PREVENTED", IllegalActionError)  # 次の自分の番も
        after = apply_kernel(apply_kernel(later, EndTurn(0)), EndTurn(1))
        self.assertEqual(after.trainer_locks, ())
        potion = use(after, POTION)  # その次の自分の番は使える（きずぐすりの決定を待つ）
        self.assertEqual(potion.cards[potion.trainer_in_use.card].card_id, POTION)

    def test_st1_before_the_coin(self):
        assert_use_stops(self, board([ROCKETS_EXPERIMENT], deck=[]), ROCKETS_EXPERIMENT, ST1)

    def test_overlapping_locks_keep_their_own_expiry(self):
        """トレーナーの使用の禁止が 2 つ（ロケット団の実験の「うら」= 使った番 + 2、相手のずつう = 相手が使った番 + 1）重なっても、別の記録（``origin``）として持ち、
        それぞれの記録が期限で消える（片方がもう片方を消さない）。実験を使える番に相手のずつうが重なる場合は、どちらも同じ番（自分の次の番）の終わりに消える。"""
        # 相手（プレイヤー 1）が前の番に化石の秘密のコダックの「ずつう」を使う（消える番 = 使った番 + 1 = 今の番）。ロケット団の実験はその禁止の前に使えないので、
        # 禁止のある番は TRAINER_PREVENTED。禁止が消えた次の自分の番に実験の「うら」で 2 つめを作る代わりに、実験の「うら」→ 相手のずつうの順で重ねる
        state = build_test_state([{"active": mon(HITMONCHAN, (F,)), "bench": [RATTATA], "hand": [ROCKETS_EXPERIMENT, POTION], "deck": [RATTATA, G] * 5},
                                  {"active": mon(FOSSIL_PSYDUCK, (PSYCHIC,)), "bench": [RATTATA]}], turn_number=TURN, current_player=0)
        mine = use(state, ROCKETS_EXPERIMENT, coins=(T,))
        theirs = attack(apply_kernel(mine, EndTurn(0)), 0, player=1)  # ずつう（相手の次の番 = TURN + 2 の終わりまで）
        locks = sorted((lk.player, lk.origin, lk.expires_turn) for lk in theirs.trainer_locks)
        self.assertEqual(locks, [(0, "attack", TURN + 2), (0, "trainer", TURN + 2)])
        assert_use_stops(self, theirs, POTION, "TRAINER_PREVENTED", IllegalActionError)
        after = apply_kernel(apply_kernel(theirs, EndTurn(0)), EndTurn(1))
        self.assertEqual(after.trainer_locks, ())  # どちらもそれぞれの記録で消えた（片方がもう片方を消すのではない）
        removed = [(e.get("origin", "attack"), e["turn"]) for e in after.log if e["kind"] == "trainer_lock_removed"]
        self.assertEqual(sorted(removed), [("attack", TURN + 2), ("trainer", TURN + 2)])
        self.assertEqual(check_invariants(after), [])


# ---------------------------------------------------------------- 書き出し・観測・共通


class SaveObservationTest(unittest.TestCase):
    def test_format_16_and_older_formats_reject(self):
        """期限のある効果（``trainer_effects``）・ロケット団の実験の禁止（``origin`` が trainer）は形式 16 で書き出し、形式 1〜15 は ``ValueError``（黙って落とさない）。"""
        self.assertEqual((max(FORMAT_VERSIONS), LATEST_FORMAT), (22, 22))  # v0.67 で形式 22  # v0.63 で形式 21。 v0.57 で 17、v0.58 で 18、v0.59 で 19
        wall = use(board([INVISIBLE_WALL]), INVISIBLE_WALL)
        locked = use(board([ROCKETS_EXPERIMENT], deck=[G]), ROCKETS_EXPERIMENT, coins=(T,))
        for state in (wall, locked):
            data = state_to_dict(state, format_version=16)
            self.assertIn("trainer_effects", data)
            for version in range(1, 16):
                with self.assertRaises(ValueError):
                    state_to_dict(state, format_version=version)
            self.assertEqual(serialization_problems(state), [])
        self.assertEqual(state_to_dict(wall, format_version=16)["trainer_effects"][0]["kind"], BENCH_ATTACK_DAMAGE_PREVENTION)
        self.assertEqual(state_to_dict(locked, format_version=16)["trainer_locks"][0]["origin"], "trainer")
        plain = board([POTION])  # 期限のある効果・トレーナーからの禁止がなければ、形式 15 は形式 16 から trainer_effects を除いたものと同じ
        self.assertEqual(state_to_dict(plain, format_version=15),
                         {k: v for k, v in state_to_dict(plain, format_version=16).items() if k not in ("trainer_effects", "format_version")}
                         | {"format_version": 15})

    def test_mid_decision_round_trip(self):
        """相手が答える決定・サイドを選ぶ決定などを待つ状態を保存して復元し（pickle・deepcopy・clone）、同じ答えで続けると同じ結果（状態・ログ・乱数）。"""
        cases = [
            (use(board([LT_SURGES_TREATY]), LT_SURGES_TREATY), (1,)),
            (answer(use(board([MISTYS_WISH, G]), MISTYS_WISH), (2,)), (1,)),
            (use(board([ROCKETS_TRAP], opponent_hand=[G, W]), ROCKETS_TRAP, coins=(H,)), (1,)),
            (use(board([ERIKAS_PERFUME], opponent_hand=[RATTATA]), ERIKAS_PERFUME), None),
        ]
        latest = max(FORMAT_VERSIONS)
        for pending, choices in cases:
            with self.subTest(kind=pending.decision.kind):
                choices = choices if choices is not None else pending.decision.options
                expected = snapshot(answer(pending, choices))
                for restored in (pickle.loads(pickle.dumps(pending)), copy.deepcopy(pending), pending.clone()):
                    self.assertEqual(state_to_dict(restored, format_version=latest), state_to_dict(pending, format_version=latest))
                    self.assertEqual(snapshot(answer(restored, choices)), expected)

    def test_observation_of_user_opponent_and_spectator(self):
        """どの視点でも観測でき、観測を状態から別に求めた監査と合う。期限のある効果は全員に見える。サイド・相手の手札のカードは見えない。"""
        states = [use(board([KOGA_TRAINER]), KOGA_TRAINER), use(board([LT_SURGES_TREATY]), LT_SURGES_TREATY),
                  answer(use(board([MISTYS_WISH, G]), MISTYS_WISH), (0,)), use(board([ROCKETS_TRAP], opponent_hand=[G]), ROCKETS_TRAP, coins=(H,))]
        for state in states:
            self.assertEqual(observation_problems(state), [])
            for viewer in (0, 1, None):
                seen = observe(state, viewer)
                self.assertEqual(len(seen["trainer_effects"]), len(state.trainer_effects))
                self.assertIsNone(seen["players"][1 if viewer != 1 else 0]["hand"]["cards"])

    def test_apply_command_does_not_change_the_given_state(self):
        state = board([LT_SURGES_TREATY])
        before = snapshot(state)
        asking = use(state, LT_SURGES_TREATY)
        self.assertEqual(snapshot(state), before)
        clone = asking.clone()
        answer(asking, (1,))
        self.assertEqual(snapshot(asking), snapshot(clone))

    def test_card_conservation(self):
        for state, card_id in ((board([ERIKAS_PERFUME], opponent_hand=[RATTATA]), ERIKAS_PERFUME), (board([LT_SURGE_TRAINER, RATTATA]), LT_SURGE_TRAINER),
                               (board([LT_SURGES_TREATY]), LT_SURGES_TREATY), (board([MISTYS_WISH, G]), MISTYS_WISH)):
            with self.subTest(card_id=card_id):
                pending = use(state, card_id)
                self.assertEqual(sorted(uids(pending)), sorted(uids(state)))
                self.assertEqual(len(set(uids(pending))), len(uids(pending)))

    def test_trainer_lock_applies_first(self):
        """［アレルギーかふん］・使用の禁止がはたらいていれば、10 枚とも使う前に TRAINER_PREVENTED（使うための条件・未解決より先）。"""
        for card_id in V0_56_CARDS:
            with self.subTest(card_id=card_id):
                state = board([card_id], opponent_active={"card": DARK_VILEPLUME, "evolved_from": [ROCKET_ODDISH, "PMCG4-006"]})
                assert_use_stops(self, state, card_id, "TRAINER_PREVENTED", IllegalActionError)


# ---------------------------------------------------------------- 正式な対戦


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.56 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.56 の 4 組を 2 seed ずつ（席を入れかえて 16 局。同じデッキ・席・seed の重複はない）。どれも監査の失敗・想定外の拒否・内部エラー・手数の上限がなく、
        10 枚とも使われ、なんでもなおしが正式な対戦の中で特殊状態を回復する（v0.55 の対戦ではいつも FH1 だった）。勝敗は判断に使わない。"""
        from tools import existing_effect_games as games

        results = games.run(range(2), pairings=games.PAIRINGS_V0_56)
        played = sum(len(run["games"]) for run in results.values())
        self.assertEqual((played, sum(len(run["duplicates"]) for run in results.values())), (16, 0))
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
        for card in V0_56_CARDS:
            self.assertGreater(totals.get((card, "played"), 0), 0, card)
        for card, key in ((FULL_HEAL, "special_conditions_removed_user"), (KOGA_TRAINER, "poisoned"), (MISTY_TRAINER, "bonus_applied"),
                          (ROCKET_GRUNT, "turn_end"), (ROCKETS_EXPERIMENT, "lock_expired"), (LT_SURGES_TREATY, "trainer_take_prize_opponent"),
                          (MISTYS_WISH, "swap_prize_with_hand_user"), (ROCKETS_TRAP, "hand_positions_to_deck_opponent"),
                          (LT_SURGE_TRAINER, "trainer_hand_to_active_user")):
            with self.subTest(card=card, key=key):
                self.assertGreater(totals.get((card, key), 0), 0)


if __name__ == "__main__":
    unittest.main()
