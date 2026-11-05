"""v0.137: 山札から選ぶトレーナーの使う前の拒否による情報漏れの修正（PSP-ST1-DECK-ORACLE・PSP-FC1-ENERGY-ARK-ORACLE。docs/deck-search-oracle-v0.137.md）。

v0.136 までは、選ばなくてよいと書かれていない山札の検索（エネルギー転送 PMCG3-044・ボスのやりかた PMCG4-060・タケシの育て方 PMCG5-077・遺跡の石版 neo2-054／neo2-057）が、実際の
山札に選べるカードがないと使う前に ST1 で、エネルギーアーク（neo2-053）が山札の基本エネルギーカードが 2 枚より少ないと使う前に FC1 で止めていた。山札とサイドの中身は使う人にも
見えないので、カードを使わずに、目的のカードが山札とサイドのどちらにあるかが分かった（拒否は状態を変えないので、毎番くりかえせた）。

v0.137 は、本人に見えない自分のカード（山札のうら・うらのサイド・見られない置いておくカード）のうち選べるカードの枚数 K と、山札の外の見えないカードの枚数 C から、山札に少なくとも
max(0, K - C) 枚あるという下限（``effects.deck_target_lower_bound``）で確かめる。K・C は配分によらないので、受理・拒否は配分によらない。

- 比べる検査（``log_audit.twin_command_problems``）は、公開の情報（3 者の観測・ログの写し）と、持ち主が知っている所有カードの集合（``owner_knowledge``）が同じで、目的のカードの
  山札とサイドの配分だけが違う状態に、同じ操作を送る
- 合法な実カードの経路（new_game からの対戦準備・錯乱ジム・［ちえくらべ］・フラッシュ・サドン・デス）と、テスト専用の盤面（``build_test_state``）を分けて書く
"""

from __future__ import annotations

import copy
import pathlib
import pickle
import unittest
from collections import Counter

from kyuura_engine import (
    Phase,
    PlayTrainer,
    ResolveDecision,
    StartSuddenDeath,
    apply_command,
    check_invariants,
    new_game,
)
from kyuura_engine import effects as E
from kyuura_engine import faceup as FU
from kyuura_engine.decisions import (
    ACCEPT_REQUEST,
    BENCH_FROM_DECK,
    REACTION_POWER,
    SEARCH_DECK,
)
from kyuura_engine.effects import CardFilter
from kyuura_engine.observation import observe, visible_log
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import (
    SET_ASIDE_HAND,
    CardInstance,
    SetAsideCards,
    TrainerUseLock,
    freeze_mapping,
)
from tests.helpers import (
    CATERPIE,
    CHAOS_GYM,
    DIGLETT,
    DRATINI,
    DROWZEE,
    FIRE,
    GROWLITHE,
    HITMONCHAN,
    MACHOP,
    PIKACHU,
    PONYTA,
    RATTATA,
    SEEL,
    STARYU,
    VOLTORB,
    WEEDLE,
    H,
    T,
    build_test_state,
    finish_setup,
    with_coin_results,
)
from tests.log_audit import (
    command_outcome,
    owned_card_ids,
    serialization_problems,
    twin_command_problems,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "deck-search-oracle-v0.137.md"
LATEST = max(FORMAT_VERSIONS)

ST1 = E.SEARCH_TRAINER_WITHOUT_TARGET_CODE
FC1 = E.STATED_CARDS_SHORT_CODE
ENERGY_SEARCH, BOSS_WAY, BROCK_TRAINING, ENERGY_ARK, RUIN_WALL, RUIN_WALL2 = "PMCG3-044", "PMCG4-060", "PMCG5-077", "neo2-053", "neo2-054", "neo2-057"
ROCKETS_EXPERIMENT, POKE_BALL, MISTYS_TEARS, ERIKAS_MAIDS, GOOD_MANNERS, RECYCLE = "PMCG6-091", "PMCG2-048", "PMCG5-069", "PMCG5-072", "PMCG5-082", "PMCG3-047"
ENERGY_SEARCH_REPRINT = "GD4-015"  # エネルギー転送の再録（選ばなくてよい文面。登録は optional）
DARK_GOLBAT, BROCKS_ZUBAT, UNOWN_E = "PMCG4-009", "PMCG5-001", "PF2-002"
FLASH, SLOWKING, SLOWPOKE, PSYCHIC = "ES2-035", "neo1-049", "neo1-045", "PMCG1-101"
POTION = "PMCG1-071"

# カードごとの (目的のカード, 必要な枚数, 拒否のコード)。目的のカードでない詰め物はコラッタ（たね・無色。どの条件にも当たらない）
TARGETED = {
    ENERGY_SEARCH: (FIRE, 1, ST1),
    BOSS_WAY: (DARK_GOLBAT, 1, ST1),
    BROCK_TRAINING: (BROCKS_ZUBAT, 1, ST1),
    RUIN_WALL: (UNOWN_E, 1, ST1),
    RUIN_WALL2: (UNOWN_E, 1, ST1),
    ENERGY_ARK: (FIRE, 2, FC1),
}
FILLER = RATTATA


def fingerprint(state):
    return repr(state_to_dict(state, format_version=LATEST)), state.rng.getstate(), tuple(dict(e) for e in state.log), state.decision


def card_in_hand(state, card_id, player=None):
    player = state.current_player if player is None else player
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)


def resolve(state, choices):
    d = state.decision
    return apply_command(state, ResolveDecision(d.player, d.id, tuple(choices)))


def hidden_split(target, total, in_prizes, *, prizes, deck_size, prize_fill=DROWZEE):
    """(山札, サイド): 目的のカード ``target`` が ``total`` 枚、そのうち ``in_prizes`` 枚がサイド。サイドから山札に移った分は ``prize_fill`` で、カードの集合（多重集合）は配分によらない。
    山札の上はコラッタ（見えるカードの uid が配分によらないよう、先に並べる）。"""
    assert in_prizes <= min(total, prizes) and total <= deck_size
    deck = [FILLER] * (deck_size - total) + [prize_fill] * in_prizes + [target] * (total - in_prizes)
    return deck, [target] * in_prizes + [prize_fill] * (prizes - in_prizes)


def split_board(card, target, total, in_prizes, *, prizes=6, deck_size=12, actor=0, hand_extra=(), bench=(), opponent=None, prize_fill=DROWZEE,
                face_up_prize=None, turn_number=None):
    """テスト専用の盤面: ``actor`` の番。目的のカード ``target`` が ``total`` 枚、そのうち ``in_prizes`` 枚がうらのサイド（残りは山札）。山札・サイドの枚数とカードの集合は配分によらない
    （``hidden_split``）。相手は山札 10 枚・サイド 6 枚。"""
    deck, prize_cards = hidden_split(target, total, in_prizes, prizes=prizes, deck_size=deck_size, prize_fill=prize_fill)
    me = {"active": HITMONCHAN, "bench": list(bench), "hand": [card, *hand_extra], "deck": deck, "prizes": prize_cards}
    them = opponent or {"active": MACHOP, "deck": [RATTATA] * 10}
    players = [me, them] if actor == 0 else [them, me]
    turn = turn_number if turn_number is not None else (3 if actor == 0 else 4)
    state = build_test_state(players, current_player=actor, turn_number=turn)
    if face_up_prize is not None:
        state.face_up_prizes = tuple(state.players[actor].prizes[i] for i in face_up_prize)
    return state


def splits(card, target, total, *, prizes=6, **kw):
    """配分だけが違う状態のすべて（サイドに置く目的のカードの枚数 0〜min(total, prizes)）。"""
    return [split_board(card, target, total, j, prizes=prizes, **kw) for j in range(min(total, prizes) + 1)]


def play(state, card_id):
    return PlayTrainer(state.current_player, card_in_hand(state, card_id))


def expected_accept(total, prizes, need):
    return total - prizes >= need


# ---------------------------------------------------------------- 1. 下限の計算


class LowerBoundTest(unittest.TestCase):
    def test_pigeonhole_bound(self):
        """K 枚（山札のうら・うらのサイドの合計）・山札の外の見えないカード C 枚なら max(0, K - C)。配分（サイドに何枚あるか）によらない。"""
        target = CardFilter("basic_energy")
        for total, prizes in ((0, 6), (1, 6), (6, 6), (7, 6), (12, 6), (2, 1), (1, 1), (1, 0), (3, 0)):
            for j in range(min(total, prizes) + 1):
                with self.subTest(total=total, prizes=prizes, in_prizes=j):
                    state = split_board(ENERGY_SEARCH, FIRE, total, j, prizes=prizes)
                    self.assertEqual(E.deck_target_lower_bound(state, 0, target), max(0, total - prizes))
                    self.assertGreaterEqual(len(E.deck_cards_matching(state, 0, target)), E.deck_target_lower_bound(state, 0, target))  # 下限は実際の数以下

    def test_face_up_prizes_are_neither_counted_nor_capacity(self):
        """おもてのサイド（ロケット団参上!。全員に見える）は、目的のカードでも数えず、山札の外の見えない枚数にも数えない。"""
        state = split_board(ENERGY_SEARCH, FIRE, 3, 2, prizes=3, face_up_prize=(0,))  # サイド: 炎（おもて）・炎・スリープ
        self.assertEqual(E.unseen_card_pool(state, 0)[1], tuple(state.players[0].prizes[1:]))
        self.assertEqual(E.deck_target_lower_bound(state, 0, CardFilter("basic_energy")), 0)  # 見えない炎は山札 1・サイド 1 の 2 枚、外の見えない枚数 2
        state = split_board(ENERGY_SEARCH, FIRE, 3, 1, prizes=2, face_up_prize=(1,))  # サイド: 炎（うら）・スリープ（おもて）。見えない炎は 3 枚、外の見えない枚数 1
        self.assertEqual(E.deck_target_lower_bound(state, 0, CardFilter("basic_energy")), 2)

    def test_hidden_set_aside_counts_as_capacity(self):
        """持ち主に見えない置いておくカード（くすぐりマシーンの手札。visible_to が空）は、山札の外の見えないカードに数える。見られる置いておくカードは数えない。"""
        for visible_to, capacity in (((), 7), ((0,), 6)):
            with self.subTest(visible_to=visible_to):
                state = split_board(ENERGY_SEARCH, FIRE, 7, 0, prizes=6, hand_extra=(FIRE,))
                aside = card_in_hand(state, FIRE)
                state.players[0].hand.remove(aside)
                state.set_aside = (SetAsideCards(SET_ASIDE_HAND, 0, (aside,), visible_to, 1, 0, "test", 3, 5),)
                elsewhere = E.unseen_card_pool(state, 0)[1]
                self.assertEqual(len(elsewhere), capacity)
                self.assertEqual(E.deck_target_lower_bound(state, 0, CardFilter("basic_energy")), max(0, 7 + (capacity - 6) - capacity))

    def test_flash_face_up_deck_cards_are_not_counted(self):
        """フラッシュでおもてにした山札のカードは数えない（保守的）。おもてでない山札のカードとサイドだけで下限を出す。"""
        state = split_board(ENERGY_SEARCH, FIRE, 10, 0, prizes=6, deck_size=10)  # 山札は炎 10 枚
        FU.set_marks(state, 0, state.players[0].deck[:3])  # 上 3 枚（炎）をおもて
        self.assertEqual(E.unseen_card_pool(state, 0)[0], tuple(state.players[0].deck[3:]))
        self.assertEqual(E.deck_target_lower_bound(state, 0, CardFilter("basic_energy")), 7 - 6)  # おもての 3 枚を数えれば 4

    def test_pool_is_the_owned_cards_the_owner_cannot_see(self):
        """見えない自分のカードの集合は、所有するカード（``owned_card_ids``）から、持ち主に見えるカード（観測の自分のゾーン）を除いたものと同じ（持ち主の知っている情報だけで決まる）。
        合法な対戦の途中の状態で確かめる。"""
        for seed in (18, 1):
            state = LegalPathTest.first_turn(seed)
            for player in (0, 1):
                with self.subTest(seed=seed, player=player):
                    deck, elsewhere = E.unseen_card_pool(state, player)
                    view = observe(state, player)["players"][player]
                    visible = [c["card_id"] for c in view["hand"]["cards"]] + [c["card_id"] for c in view["discard"]]
                    for pokemon in [view["active"], *view["bench"]]:
                        if pokemon is not None:
                            visible += [pokemon["card_id"]] + [c["card_id"] for key in ("energy", "trainers", "evolution_stack") for c in pokemon[key]]
                    pool = Counter(state.cards[u].card_id for u in (*deck, *elsewhere))
                    self.assertEqual(pool, Counter(owned_card_ids(state, player)) - Counter(visible))
                    self.assertEqual(Counter(owned_card_ids(state, player)), Counter(state.decklists[player]))  # 所有者の変更のない対戦では、デッキリストそのもの


# ---------------------------------------------------------------- 2. 比べる検査（配分だけが違う状態に同じ操作）


class TwinTest(unittest.TestCase):
    CASES = ((0, 6), (1, 6), (2, 6), (6, 6), (7, 6), (8, 6), (12, 6), (1, 1), (2, 1), (3, 1), (1, 0), (2, 0))

    def test_outcome_does_not_depend_on_the_split(self):
        """どの K・C でも、サイドに置く目的のカードの枚数だけが違う状態に同じ使う宣言を送ると、受理・拒否・コード・理由の文が同じ（見る人 0・1・観戦者。持ち主が知っている所有カードの
        集合も同じ）。受け付けるのは K - C が必要な枚数以上のときだけ。"""
        for card, (target, need, code) in TARGETED.items():
            for total, prizes in self.CASES:
                states = splits(card, target, total, prizes=prizes)
                if len(states) < 2:
                    continue
                with self.subTest(card=card, total=total, prizes=prizes):
                    self.assertEqual(twin_command_problems(states, [lambda s, card=card: play(s, card)], owner_knowledge=True), [])
                    outcome = command_outcome(states[0], play(states[0], card))[0]
                    if expected_accept(total, prizes, need):
                        self.assertEqual(outcome, ("accepted",))
                    else:
                        self.assertEqual(outcome[:2], ("UnsupportedError", code))

    def test_seat_swap(self):
        """使うのがプレイヤー 1 でも同じ（下限は使うプレイヤーの見えないカードで決める）。"""
        for card, (target, need, code) in TARGETED.items():
            for total, prizes in ((1, 6), (7, 6), (8, 6), (2, 1)):
                with self.subTest(card=card, total=total, prizes=prizes):
                    states = splits(card, target, total, prizes=prizes, actor=1)
                    self.assertEqual(twin_command_problems(states, [lambda s, card=card: play(s, card)], owner_knowledge=True), [])
                    outcome = command_outcome(states[0], play(states[0], card))[0]
                    self.assertEqual(outcome[0] == "accepted", expected_accept(total, prizes, need))

    def test_reason_text_is_fixed(self):
        """拒否の理由の文は決まった文（実際の山札の枚数・カードの名前・位置を書かない）。全部が拒否される配分どうしでも、文が同じ。"""
        for card, (target, need, code) in TARGETED.items():
            reasons = set()
            for total, prizes in ((0, 6), (1, 6), (6, 6), (1, 1)):
                for state in splits(card, target, total, prizes=prizes):
                    if expected_accept(total, prizes, need):
                        continue
                    outcome = command_outcome(state, play(state, card))[0]
                    self.assertEqual(outcome[:2], ("UnsupportedError", code))
                    self.assertNotIn("state_changed", outcome)
                    reasons.add(outcome[2])
            with self.subTest(card=card):
                self.assertEqual(len(reasons), 1, reasons)
                (reason,) = reasons
                self.assertIn(E.DECK_TARGET_UNCONFIRMED_DETAIL, reason)
                self.assertNotIn("枚（", reason)  # v0.136 までの FC1 の文は山札の枚数を書いていた

    def test_rejection_is_pure_and_repeatable(self):
        """拒否は状態・乱数・ログを変えず、何度送っても同じ。"""
        for card, (target, need, code) in TARGETED.items():
            with self.subTest(card=card):
                state = split_board(card, target, 1, 1)
                before = fingerprint(state)
                outcomes = [command_outcome(state, play(state, card))[0] for _ in range(3)]
                self.assertEqual(len(set(outcomes)), 1)
                self.assertEqual(outcomes[0][:2], ("UnsupportedError", code))
                self.assertEqual(fingerprint(state), before)

    def test_before_fix_reproduction_shape(self):
        """修正の前に漏れを示した盤面（docs 2 章。目的のカード 1 枚が山札／サイド、ほかのサイドはスリープ 5 枚）。今は両方とも同じ拒否。"""
        for card, (target, need, code) in TARGETED.items():
            total = need
            with self.subTest(card=card):
                states = [split_board(card, target, total, 0), split_board(card, target, total, 1)]
                self.assertEqual(twin_command_problems(states, [lambda s, card=card: play(s, card)]), [])
                for state in states:
                    self.assertEqual(command_outcome(state, play(state, card))[0][:2], ("UnsupportedError", code))


# ---------------------------------------------------------------- 3. 受け付ける場面の処理（選ぶ・見せる・手札・切る）


class SafePathTest(unittest.TestCase):
    def test_energy_search_hidden_take_and_shuffle(self):
        """エネルギー転送（見せない）: 下限が 1 以上なら使え、山札の基本エネルギーカードから 1 枚を選んで手札に加え、山札を切る。選んだカードは使ったプレイヤーだけが見る。"""
        state = split_board(ENERGY_SEARCH, FIRE, 7, 3)
        asked = apply_command(state, play(state, ENERGY_SEARCH))
        d = asked.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (SEARCH_DECK, 1, 1))
        self.assertEqual(d.options, E.deck_cards_matching(state, 0, CardFilter("basic_energy")))  # 選べるのは実際の山札のカード（山札をさがすので本人は見る）
        done = resolve(asked, d.options[:1])
        kinds = [e["kind"] for e in done.log[len(state.log):]]
        self.assertEqual(kinds, ["play_trainer", "search_deck", "shuffle", "discard_trainer"])
        self.assertIn(d.options[0], done.players[0].hand)
        self.assertNotIn("card", [e for e in visible_log(done, 1) if e["kind"] == "search_deck"][-1])
        self.assertEqual(check_invariants(done), [])

    def test_boss_way_and_brock_reveal(self):
        for card, target in ((BOSS_WAY, DARK_GOLBAT), (BROCK_TRAINING, BROCKS_ZUBAT)):
            with self.subTest(card=card):
                state = split_board(card, target, 3, 1, prizes=1)
                done = resolve(apply_command(state, play(state, card)), E.deck_cards_matching(state, 0, E.DEFAULT_EFFECTS.trainer_entry(card).effect.target)[:1])
                kinds = [e["kind"] for e in done.log[len(state.log):]]
                self.assertEqual(kinds, ["play_trainer", "reveal_from_deck", "shuffle", "discard_trainer"])
                self.assertIn("card", [e for e in visible_log(done, 1) if e["kind"] == "reveal_from_deck"][-1])

    def test_ruin_wall_benches_and_shuffles(self):
        for card in (RUIN_WALL, RUIN_WALL2):
            with self.subTest(card=card):
                state = split_board(card, UNOWN_E, 3, 1, prizes=1)
                asked = apply_command(state, play(state, card))
                self.assertEqual(asked.decision.kind, BENCH_FROM_DECK)
                done = resolve(asked, asked.decision.options[:1])
                kinds = [e["kind"] for e in done.log[len(state.log):]]
                self.assertEqual(kinds[:1] + kinds[-3:], ["play_trainer", "trainer_bench_from_deck", "shuffle", "discard_trainer"])
                self.assertEqual(done.cards[done.players[0].bench[-1].card].card_id, UNOWN_E)

    def test_energy_ark_every_heads_count(self):
        """エネルギーアーク: 下限が 2 以上なら使え、コインの「おもて」の数（0〜2）ぶんを見せて手札に加え、切る（0 なら山札を見ない）。"""
        for sides, heads in (((T, T), 0), ((H, T), 1), ((H, H), 2)):
            with self.subTest(heads=heads):
                state = with_coin_results(split_board(ENERGY_ARK, FIRE, 8, 6), *sides)
                after = apply_command(state, play(state, ENERGY_ARK))
                if heads == 0:
                    self.assertIsNone(after.decision)
                    self.assertNotIn("shuffle", [e["kind"] for e in after.log[len(state.log):]])
                    continue
                d = after.decision
                self.assertEqual((d.kind, d.min_choices, d.max_choices), (SEARCH_DECK, heads, heads))
                done = resolve(after, d.options[:heads])
                kinds = [e["kind"] for e in done.log[len(state.log):]]
                self.assertEqual(kinds.count("reveal_from_deck"), heads)
                self.assertEqual(kinds[-2:], ["shuffle", "discard_trainer"])

    def test_over_rejection_when_the_target_is_actually_in_the_deck(self):
        """保守的な制限: 実際には山札に目的のカードがあっても、下限が足りなければ使う前に止める（v0.136 までは受け付けた盤面）。"""
        for card, (target, need, code) in TARGETED.items():
            with self.subTest(card=card):
                state = split_board(card, target, 6, 0, prizes=6)  # 6 枚とも山札にある
                self.assertGreaterEqual(len(E.deck_cards_matching(state, 0, E.DEFAULT_EFFECTS.trainer_entry(card).effect.TARGET
                                                                  if card == ENERGY_ARK else E.DEFAULT_EFFECTS.trainer_entry(card).effect.target)), need)
                self.assertEqual(command_outcome(state, play(state, card))[0][:2], ("UnsupportedError", code))


# ---------------------------------------------------------------- 4. 使うための条件・ほかの検索（変えていない）


class UnchangedChecksTest(unittest.TestCase):
    def test_bench_full_comes_before_the_search_check(self):
        """遺跡の石版のベンチの空き（説明の「使えない」）は、下限の確かめの前のまま（BENCH_FULL）。"""
        state = split_board(RUIN_WALL, UNOWN_E, 0, 0, bench=[RATTATA] * 5)
        self.assertEqual(command_outcome(state, play(state, RUIN_WALL))[0][:2], ("IllegalActionError", "BENCH_FULL"))

    def test_trainer_lock_comes_first(self):
        """トレーナーの使用の禁止（ずつうなど）は、効果の確かめの前のまま。"""
        state = split_board(ENERGY_SEARCH, FIRE, 0, 0)
        state.trainer_locks = (TrainerUseLock(0, 1, state.players[1].active.card, "PMCG1-045#1", 2, 3),)
        self.assertEqual(command_outcome(state, play(state, ENERGY_SEARCH))[0][:2], ("IllegalActionError", "TRAINER_PREVENTED"))

    def test_optional_searches_accept_without_a_target(self):
        """選ばなくてよい山札の検索（モンスターボール・カスミのなみだ・エリカのお付き・礼儀作法・エネルギー転送の再録）は、選べるカードがなくても今までどおり使える（何も選ばず切る）。
        受理は配分によらない（比べる検査）。"""
        for card, target, extra in ((MISTYS_TEARS, "PMCG1-099", (POTION,)), (ERIKAS_MAIDS, "PMCG5-063", (POTION, POTION)), (GOOD_MANNERS, RATTATA, ()),
                                    (ENERGY_SEARCH_REPRINT, FIRE, ()), (POKE_BALL, RATTATA, ())):
            with self.subTest(card=card):
                states = [split_board(card, target, 1, j, hand_extra=extra, prize_fill=DROWZEE if target != RATTATA else FIRE) for j in (0, 1)]
                self.assertEqual(twin_command_problems(states, [lambda s, card=card: play(s, card)], owner_knowledge=True), [])
                self.assertEqual(command_outcome(states[1], play(states[1], card))[0], ("accepted",))

    def test_rockets_experiment_reads_only_the_deck_count(self):
        """ロケット団の実験（どのカードでも。選ばなくてよいと書かれていない）: 下限は山札のうらのカードの枚数（公開）と同じなので、山札があれば今までどおり使える。"""
        state = split_board(ROCKETS_EXPERIMENT, FIRE, 0, 0, deck_size=1)
        self.assertEqual(E.deck_target_lower_bound(state, 0, CardFilter("any")), 1)
        self.assertEqual(command_outcome(state, play(state, ROCKETS_EXPERIMENT))[0], ("accepted",))
        empty = split_board(ROCKETS_EXPERIMENT, FIRE, 0, 0, deck_size=0)
        self.assertEqual(command_outcome(empty, play(empty, ROCKETS_EXPERIMENT))[0][:2], ("UnsupportedError", ST1))

    def test_recycle_reads_the_public_discard(self):
        """リサイクル（トラッシュ。公開）の ST1 は変えていない（トラッシュが空なら止める）。"""
        state = split_board(RECYCLE, FIRE, 0, 0)
        self.assertEqual(command_outcome(state, play(state, RECYCLE))[0][:2], ("UnsupportedError", ST1))
        state = build_test_state([{"active": HITMONCHAN, "hand": [RECYCLE], "discard": [POTION]}, {"active": MACHOP}])
        self.assertEqual(command_outcome(state, play(state, RECYCLE))[0], ("accepted",))

    def test_other_fc1_effects_unchanged(self):
        """FC1 を使うほかの効果（メンテナンスの手札の枚数）は、今までどおり公開の枚数で止める。"""
        state = build_test_state([{"active": HITMONCHAN, "hand": ["PMCG1-085", POTION]}, {"active": MACHOP}])
        self.assertEqual(command_outcome(state, play(state, "PMCG1-085"))[0][:2], ("UnsupportedError", FC1))


# ---------------------------------------------------------------- 5. 錯乱ジム・［ちえくらべ］・フラッシュ


class ChaosGymTest(unittest.TestCase):
    def board(self, total0, in_prizes0, total1, in_prizes1):
        """プレイヤー 0 が錯乱ジムを出したあと、エネルギー転送を使う盤面。プレイヤー 1（借りるプレイヤー）の炎エネルギーの配分も決める。"""
        deck1, prizes1 = hidden_split(FIRE, total1, in_prizes1, prizes=6, deck_size=10)
        state = split_board(ENERGY_SEARCH, FIRE, total0, in_prizes0, hand_extra=(CHAOS_GYM,), opponent={"active": MACHOP, "deck": deck1, "prizes": prizes1})
        return apply_command(state, PlayTrainer(0, card_in_hand(state, CHAOS_GYM)))

    def test_stops_before_the_chaos_coin(self):
        state = self.board(1, 0, 8, 0)
        before = fingerprint(state)
        self.assertEqual(command_outcome(state, play(state, ENERGY_SEARCH))[0][:2], ("UnsupportedError", ST1))
        self.assertEqual(fingerprint(state), before)

    def test_borrower_is_checked_with_the_borrowers_own_bound(self):
        """「うら」で相手が借りて使うときは、借りたプレイヤーの見えないカードの下限で確かめる。借りたプレイヤーの配分だけが違う状態で、借りる答えの受理・拒否が同じ。"""
        for total1, accepts in ((1, False), (7, True)):
            with self.subTest(total1=total1):
                states = [with_coin_results(self.board(8, 0, total1, j), T) for j in (0, 1)]
                steps = [lambda s: play(s, ENERGY_SEARCH), lambda s: ResolveDecision(1, s.decision.id, (1,))]
                self.assertEqual(twin_command_problems(states, steps, owner_knowledge=True), [])
                asked = apply_command(states[0], play(states[0], ENERGY_SEARCH))
                self.assertEqual((asked.decision.kind, asked.decision.player), (ACCEPT_REQUEST, 1))
                outcome = command_outcome(asked, ResolveDecision(1, asked.decision.id, (1,)))[0]
                self.assertEqual(outcome[0] == "accepted", accepts)
                if not accepts:
                    self.assertEqual(outcome[1], ST1)
                self.assertEqual(command_outcome(asked, ResolveDecision(1, asked.decision.id, ()))[0], ("accepted",))  # 使わない答えはいつも受け付ける


class MindGamesTest(unittest.TestCase):
    """相手の［ちえくらべ］（v0.132 の利用者指定「1. 状態を変えずに使えるかを確かめる（使えないカードの宣言には選択もコインもない）→ 2. 使うかを選ぶ」）。"""

    def board(self, total, in_prizes):
        return split_board(ENERGY_SEARCH, FIRE, total, in_prizes, turn_number=7,
                           opponent={"active": {"card": SLOWKING, "energy": [PSYCHIC] * 3, "evolved_from": SLOWPOKE}, "deck": [RATTATA] * 10})

    def test_unusable_offers_no_reaction(self):
        states = [self.board(1, j) for j in (0, 1)]
        self.assertEqual(twin_command_problems(states, [lambda s: play(s, ENERGY_SEARCH)], owner_knowledge=True), [])
        before = fingerprint(states[0])
        self.assertEqual(command_outcome(states[0], play(states[0], ENERGY_SEARCH))[0][:2], ("UnsupportedError", ST1))
        self.assertEqual(fingerprint(states[0]), before)

    def test_declined_reaction_continues_to_the_search(self):
        states = [self.board(8, j) for j in (0, 2)]
        steps = [lambda s: play(s, ENERGY_SEARCH), lambda s: ResolveDecision(s.decision.player, s.decision.id, ())]
        self.assertEqual(twin_command_problems(states, steps, owner_knowledge=True), [])
        asked = apply_command(states[0], play(states[0], ENERGY_SEARCH))
        self.assertEqual(asked.decision.kind, REACTION_POWER)
        declined = resolve(asked, ())
        self.assertEqual(declined.decision.kind, SEARCH_DECK)


class FaceUpDeckTest(unittest.TestCase):
    def test_flash_then_search_twins(self):
        """フラッシュ（合法な経路）で上 5 枚をおもてにした山札。おもてのカードは数えず、うらの山札とサイドの配分だけが違う状態で、受理・拒否が同じ。"""
        def flashed(total, in_prizes):
            state = split_board(ENERGY_SEARCH, FIRE, total, in_prizes, hand_extra=(FLASH,), deck_size=14)
            state = apply_command(state, play(state, FLASH))
            while state.decision is not None:
                state = resolve(state, state.decision.options)
            return state

        for total, accepts in ((7, True), (6, False)):
            with self.subTest(total=total):
                states = [flashed(total, j) for j in (0, 1)]
                self.assertEqual(FU.face_up_count(states[0], 0), 5)
                self.assertEqual(twin_command_problems(states, [lambda s: play(s, ENERGY_SEARCH)], owner_knowledge=True), [])
                outcome = command_outcome(states[0], play(states[0], ENERGY_SEARCH))[0]
                self.assertEqual(outcome[0] == "accepted", accepts)


# ---------------------------------------------------------------- 6. 合法な操作の列（new_game から）


ES_DECK = [ENERGY_SEARCH] * 4 + [FIRE] + [p for p in (RATTATA, DRATINI, DROWZEE, HITMONCHAN, MACHOP, DIGLETT, PONYTA, GROWLITHE, STARYU, SEEL, VOLTORB, PIKACHU,
                                                     WEEDLE, CATERPIE) for _ in range(4)][:55]
OPPONENT_DECK = [FIRE] * 30 + [p for p in (RATTATA, DRATINI, DROWZEE, HITMONCHAN, MACHOP, DIGLETT, PONYTA, GROWLITHE) for _ in range(4)][:30]
RICH_DECK = [ENERGY_SEARCH] * 4 + [FIRE] * 20 + [p for p in (RATTATA, DRATINI, DROWZEE, HITMONCHAN, MACHOP, DIGLETT, PONYTA, GROWLITHE, STARYU) for _ in range(4)]


class LegalPathTest(unittest.TestCase):
    @staticmethod
    def first_turn(seed, deck=ES_DECK):
        state = finish_setup(new_game(deck, OPPONENT_DECK, seed), janken_winner=0)
        assert state.phase is Phase.MAIN and state.current_player == 0, (seed, state.phase)
        return state

    @staticmethod
    def swapped(state):
        """この状態の、プレイヤー 0 の炎エネルギー 1 枚と、反対の場所（山札・サイド）の炎エネルギーでないカード 1 枚を入れかえた状態（観測・所有カードは同じ。乱数の状態も同じ）。"""
        twin = state.clone()
        p = twin.players[0]
        fire = next(u for u in [*p.deck, *p.prizes] if twin.cards[u].card_id == FIRE)
        if fire in p.deck:
            other = next(u for u in p.prizes if twin.cards[u].card_id != FIRE)
            i, j = p.deck.index(fire), p.prizes.index(other)
            p.deck[i], p.prizes[j] = other, fire
        else:
            other = next(u for u in p.deck if twin.cards[u].card_id != FIRE)
            i, j = p.prizes.index(fire), p.deck.index(other)
            p.prizes[i], p.deck[j] = other, fire
        return twin

    def test_seeds_from_the_reproduction(self):
        """修正の前の再現の seed（docs 2.2 節）: seed 18 は炎エネルギー（デッキに 1 枚）がサイド、seed 1 は山札。どちらも手札にエネルギー転送がある最初の番。修正の前は受理・拒否が
        分かれた（seed 18 は ST1、seed 1 は受理）。今はどちらも同じ拒否で、双子（山札・サイドの 2 枚の入れかえ）とも違いがない。"""
        for seed, where in ((18, "prizes"), (1, "deck")):
            with self.subTest(seed=seed):
                state = self.first_turn(seed)
                fire = next(u for u in state.cards if state.cards[u].card_id == FIRE and state.cards[u].owner == 0)
                self.assertIn(fire, state.players[0].prizes if where == "prizes" else state.players[0].deck)
                self.assertEqual(twin_command_problems([state, self.swapped(state)], [play(state, ENERGY_SEARCH)], owner_knowledge=True), [])
                self.assertEqual(command_outcome(state, play(state, ENERGY_SEARCH))[0][:2], ("UnsupportedError", ST1))

    def test_rich_deck_accepts_from_the_first_turn(self):
        """基本エネルギーカードが 20 枚のデッキ: 最初の番から下限が 1 以上になり、今までどおり使える（双子とも受理）。"""
        state = next(s for s in (self.first_turn(seed, RICH_DECK) for seed in range(200)) if any(s.cards[u].card_id == ENERGY_SEARCH for u in s.players[0].hand))
        self.assertGreaterEqual(E.deck_target_lower_bound(state, 0, CardFilter("basic_energy")), 1)
        self.assertEqual(twin_command_problems([state, self.swapped(state)], [play(state, ENERGY_SEARCH)], owner_knowledge=True), [])
        asked = apply_command(state, play(state, ENERGY_SEARCH))
        done = resolve(asked, asked.decision.options[:1])
        self.assertEqual(check_invariants(done), [])


# ---------------------------------------------------------------- 7. サドン・デス・保存と復元・所有者の変更


class SuddenDeathTest(unittest.TestCase):
    def test_new_segment_uses_the_current_prizes(self):
        """延長戦の区間（サイド 1 枚）: 下限は今の区間の山札・サイド（1 枚）で決める。前の区間の記録は使わない。"""
        from tests.test_sudden_death_v0_134 import (
            _until_main,
            constructed_sudden_death,
            with_decklists,
        )

        cards = [ENERGY_SEARCH] * 4 + [FIRE] * 3 + [RATTATA] * 4
        state = build_test_state([{"active": RATTATA, "hand": [], "deck": list(cards), "prizes": 1},
                                  {"active": RATTATA, "hand": [], "deck": list(cards), "prizes": 1}], current_player=0)
        ended = constructed_sudden_death(with_decklists(state))
        fresh = next(_until_main(apply_command(ended, StartSuddenDeath())))
        player = fresh.current_player
        self.assertEqual(len(fresh.players[player].prizes), 1)
        bound = E.deck_target_lower_bound(fresh, player, CardFilter("basic_energy"))
        deck, elsewhere = E.unseen_card_pool(fresh, player)
        self.assertEqual(bound, max(0, sum(1 for u in (*deck, *elsewhere) if fresh.card_def(u).is_basic_energy) - 1))
        if any(fresh.cards[u].card_id == ENERGY_SEARCH for u in fresh.players[player].hand):
            outcome = command_outcome(fresh, play(fresh, ENERGY_SEARCH))[0]
            self.assertEqual(outcome[0] == "accepted", bound >= 1)


class PersistenceTest(unittest.TestCase):
    def test_save_and_restore_gives_the_same_outcome(self):
        """保存（pickle・deepcopy・clone）のあとも同じ受理・拒否（下限は状態だけで決まり、別の記録を持たない）。"""
        for total in (1, 7):
            state = split_board(ENERGY_SEARCH, FIRE, total, 1)
            expected = command_outcome(state, play(state, ENERGY_SEARCH))[0]
            for kind, restored in (("pickle", pickle.loads(pickle.dumps(state))), ("deepcopy", copy.deepcopy(state)), ("clone", state.clone())):
                with self.subTest(total=total, kind=kind):
                    self.assertEqual(command_outcome(restored, play(restored, ENERGY_SEARCH))[0], expected)

    def test_decision_across_save(self):
        """エネルギーアークのコインのあとの決定を保存（pickle）して、同じ答えで続けられる。書き出し（最新の形式）の検査も通る。"""
        state = with_coin_results(split_board(ENERGY_ARK, FIRE, 8, 6), H, H)
        asked = apply_command(state, play(state, ENERGY_ARK))
        self.assertEqual(serialization_problems(asked), [])
        restored = pickle.loads(pickle.dumps(asked))
        self.assertEqual(fingerprint(resolve(restored, asked.decision.options[:2])), fingerprint(resolve(asked, asked.decision.options[:2])))


class OwnershipTest(unittest.TestCase):
    def test_received_card_in_the_deck_counts_for_the_new_owner(self):
        """とりかえっこプリーズで受け取ったカード（所有者が変わった。両者が交換のときに見た）が山札に入っていれば、新しい所有者の見えないカードとして数える。"""
        state = split_board(ENERGY_SEARCH, FIRE, 6, 0)
        received = next(u for u in state.players[0].deck if state.cards[u].card_id == FIRE)
        cards = dict(state.cards)
        cards[received] = CardInstance(received, FIRE, 0, 1)
        state.cards = freeze_mapping(cards)
        self.assertEqual(state.cards[received].deck_owner, 1)
        self.assertEqual(E.deck_target_lower_bound(state, 0, CardFilter("basic_energy")), 0)
        self.assertIn(FIRE, owned_card_ids(state, 0))


# ---------------------------------------------------------------- 8. 対戦の道具・文書


class GamesTest(unittest.TestCase):
    def test_development_seed_runs_without_audit_failures(self):
        """開発用の seed 90 の v0.137 の組。監査の失敗・想定外の拒否・内部エラー・手数の上限がなく、安全に使えた場面と、使う前の保守的な停止の両方が起こる。"""
        from tools import existing_effect_games as games

        results = games.run(range(90, 91), pairings=games.PAIRINGS_V0_137)
        totals, stops = Counter(), Counter()
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"), game.get("error"))
                totals.update(game.get("v137", {}))
                stops.update({k: v for k, v in game.get("policy", {}).items() if k.endswith((f"_not_playable_{ST1}", f"_not_playable_{FC1}"))})
        for card in (ENERGY_SEARCH, BOSS_WAY, ENERGY_ARK):
            self.assertGreater(totals.get(f"played_{card}", 0), 0, card)
        self.assertGreater(sum(stops.values()), 0)


class AuditPrecisionTest(unittest.TestCase):
    """v0.137 の前の版の組の比べ（docs 10 章）で、対局が分かれたあとに既存のログの監査の読み違い 2 つに当たった（エンジンの動きは v0.96・v0.36 の仕様どおり）。監査を正しく
    読むように直した（``log_audit.log_problems``）。直したあとも、本当に合わないログは見つけることを確かめる（緩めていない）。"""

    @staticmethod
    def played(seat, seed):
        from tools import existing_effect_games as games

        return games.play(seat, seed, keep_state=True)

    @staticmethod
    def _increase_accept_problem_v0_146(effect, state, use):
        """v0.146 までの［INCREASE］の使う前の確かめ（実際の山札の候補を読む。v0.147 で配分を読まない下限に直した PSP-INCREASE-ENTRY-PW3-ORACLE の形。このテストの対戦を
        作るためだけに使う）。"""
        from kyuura_engine.errors import UnsupportedError

        options = effect.candidates(state, use.player)
        if not options:
            return E._power_zero_cards(f"［INCREASE］で、山札に「{effect.group}」がない")
        blocked, code, reason = E.bench_entry_unresolved(state, options)
        if len(blocked) == len(options):
            return UnsupportedError(code, reason)
        return None

    def test_card_returned_to_the_deck_can_be_benched_from_the_deck(self):
        """J97 対 F97 の seed 3: 25 番に山札にもどすワザ（PMCG5-066）で山札にもどったアンノーン[N]（カード 3）を、46 番に［INCREASE］で山札からベンチに出す。``uid in ids``（一度でも
        場に出た）ではなく、今場にあるかで確かめる。今場にあるカードを山札から出したログは、今までどおり問題にする。

        監査の精度の回帰テストで、受理の条件のテストではない。v0.147 から［INCREASE］の使う前の確かめは配分を読まない下限（docs/deck-content-prechecks-v0.147.md）で、
        この対戦の 46 番では使えない（v0.97 のバッチの 32 局で使う局がなくなった）。監査の標本を保つため、対戦を作る間だけ v0.146 までの確かめ（実際の山札を読む）にもどして、
        同じ対戦（v0.146 までと同じ手順）を作り、監査は今のコードで行う。"""
        from unittest import mock

        from tests.log_audit import log_problems

        with mock.patch.object(E.BenchNameGroupFromDeckOnEntry, "accept_problem", self._increase_accept_problem_v0_146):
            result = self.played(("J97", "F97"), 3)
        self.assertEqual(result["audit"], {})
        state = result["state"]
        index = next(i for i, e in enumerate(state.log) if e["kind"] == "bench_from_deck" and e.get("power") == "neo2-023@power0" and e["card"] == 3)
        broken = state.clone()
        log = [dict(e) for e in broken.log]
        in_play_card = log[index]["pokemon"]  # ［INCREASE］を使った、場にいるカード
        log[index]["card"] = in_play_card
        broken.log = log
        self.assertTrue(any(f"ベンチに出したカード {in_play_card} が" in p for p in log_problems(broken)))

    def test_owner_answers_an_entry_power_outside_their_turn(self):
        """L96 対 U96 の seed 2: 7 番（プレイヤー 0 の番）にエリカの香水でプレイヤー 1 のアンノーン[E] をベンチに出させ、持ち主が［ENGAGE］を使う（v0.96 の仕様）。記録した使う機会への
        答えなら、番でない持ち主の宣言でもよい。使う機会への答えでない宣言（entry を消したログ）は、今までどおり問題にする。"""
        from tests.log_audit import log_problems

        result = self.played(("L96", "U96"), 2)
        self.assertEqual(result["audit"], {})
        state = result["state"]
        index = next(i for i, e in enumerate(state.log) if e["kind"] == "pokemon_power" and e.get("entry") == "hand" and e["player"] != state.log[i - 1].get("chooser", e["player"]))
        broken = state.clone()
        log = [dict(e) for e in broken.log]
        del log[index]["entry"]
        broken.log = log
        self.assertTrue(any("番のプレイヤーの場のポケモンではない" in p for p in log_problems(broken)))


class DocumentTest(unittest.TestCase):
    def test_document_records_the_fix_and_the_open_rulings(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("PSP-ST1-DECK-ORACLE", "PSP-FC1-ENERGY-ARK-ORACLE", "deck_target_lower_bound", "UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET", "UNRESOLVED_STATED_CARDS_SHORT",
                       "未解決のまま", "厳密モード"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
