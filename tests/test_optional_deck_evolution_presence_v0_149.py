"""v0.149（docs/optional-deck-evolution-presence-v0.149.md）: 両モード共通の情報漏れの修正 2 つ。

A. PSP-OPTIONAL-DECK-EVOLUTION-DECISION-PRESENCE: たきのぼりしんか（``EvolveAttackerFromDeck`` の任意）・つきのちから（``EvolveFromDeck``）は、宣言を受理したあと（山札をさがし
   始めたあと）、山札に選べる進化カードがなければ決定を出さずに ``evolve_from_deck_none`` で進んだ。決定の有無とログが相手・観戦者に見えるので、選べる進化カードが山札にあるかが
   伝わった。山札にカードがあれば、選べるカードがなくても決定を出す（たきのぼりしんかは 0〜1 枚のまま、0 枚の答えのログは ``evolve_from_deck_declined`` で理由は本人だけ。
   つきのちからは v0.84 の A3 と同じ 0〜0 枚の決定）。
B. PSP-HIDDEN-SET-ASIDE-DECK-POOL: 熱血!（FV1）・［おたけび］（RB1）・マスターボール neo（NB1）・山札の上からトラッシュするワザ（``hidden_deck_pool``。FV1）の使う前の確かめが、
   山札とすべてのサイドだけを見て、持ち主に見えない置いておくカード（くすぐりマシーン）を含まなかった。山札とその置いておくカードの配分で受理・拒否が変わった。

盤面の種類を分ける（docs 1 章）:
- 構築盤面（``build_test_state``）: ``state_of``・``tickled`` の始まり。``new_game`` からの合法な操作の列ではない
- 構築盤面からの合法な操作: ``tickled`` は、構築盤面で相手がくすぐりマシーンを使い（「おもて」）、番を終えるところまでを合法なコマンドで進める
- 双子（テストだけの操作）: ``swap_hidden``（山札とうらのサイド）・``swap_set_aside``（山札と持ち主に見えない置いておくカード。置いたログの見えない項目も合わせる）
- 補助関数だけの確かめ: ``hidden_deck_pool``・``searchable_deck_cards`` を直接呼ぶもの
"""

from __future__ import annotations

import dataclasses
import pathlib
import pickle
import re
import unittest
from types import MappingProxyType

from kyuura_engine import (
    EndTurn,
    PlayBasicToBench,
    PlayTrainer,
    ResolveDecision,
    UseAttack,
    UsePokemonPower,
    apply_command,
)
from kyuura_engine import conventions as C
from kyuura_engine import effects as E
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import SEARCH_DECK
from kyuura_engine.observation import observe, visible_log
from tests import helpers as H
from tests.helpers import build_test_state, with_coin_results
from tests.log_audit import command_outcome, public_view, twin_command_problems
from tests.test_attack_deck_evolution_preflight_v0_148 import (
    DECLARATIONS,
    MOON,
    WATERFALL,
)
from tests.test_deck_content_prechecks_v0_147 import (
    HIDDEN,
    SETS,
    W,
    hand_uid,
    mon,
    snapshot,
    state_of,
    swap_hidden,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "optional-deck-evolution-presence-v0.149.md"
R = H.FIRE
RAINBOW, PICHU, QUILAVA = H.RAINBOW_ENERGY, "neo1-042", H.DARK_QUILAVA_NEO4
FV1, RB1, NB1 = "UNRESOLVED_FERVOR_RAINBOW_ENERGY", "UNRESOLVED_RAINBOW_ATTACH_AS_TYPE", "UNRESOLVED_NEO_TEXT_BASIC_BABY"
OPPONENT_VIEWS = (1, None)


def tickled(me, *, conventions=None, set_aside=(W, W)):
    """構築盤面（番 6・相手の番）から、相手がくすぐりマシーンを使って「おもて」で自分（プレイヤー 0）の手札 ``set_aside`` を置いておき（だれも見られない。持ち主にも見えない）、
    番を終える（合法な操作）。自分の番 7 の最初に山札の上の 1 枚を引く（``me`` の山札の先頭）。"""
    them = {"active": mon(H.RATTATA), "bench": [H.RATTATA], "deck": [W] * 10, "prizes": [W] * 6, "hand": [H.TICKLING_MACHINE]}
    s = build_test_state([dict(me, hand=list(set_aside)), them], turn_number=6, current_player=1)
    if conventions is not None:
        s.conventions = C.registered_identity(C.parse_key(conventions))
    s = apply_command(with_coin_results(s, CoinSide.HEADS), PlayTrainer(1, hand_uid(s, H.TICKLING_MACHINE, 1)))
    s = apply_command(s, EndTurn(1))
    assert s.current_player == 0 and s.set_aside and s.set_aside[0].visible_to == ()
    return s


def swap_set_aside(state, card_id, player=0):
    """``card_id`` のカード 1 枚（山札）と、持ち主に見えない置いておくカードの別のカード 1 枚を入れかえた双子（テストだけの操作）。置いたログ（``set_aside_hand``。カードはだれにも
    見えない項目）も同じに合わせる（置いたカードとログが合う形を保つ）。観測・ログの写し・所有カード・乱数は同じ。"""
    twin = state.clone()
    p = twin.players[player]
    target = next(u for u in p.deck if twin.cards[u].card_id == card_id)
    index, group = next((i, g) for i, g in enumerate(twin.set_aside) if g.owner == player and player not in g.visible_to)
    other = next(u for u in group.cards if twin.cards[u].card_id != card_id)
    p.deck[p.deck.index(target)] = other
    cards = tuple(target if u == other else u for u in group.cards)
    twin.set_aside = (*twin.set_aside[:index], dataclasses.replace(group, cards=cards), *twin.set_aside[index + 1:])
    twin.log = tuple(MappingProxyType({**e, "cards": cards}) if e["kind"] == "set_aside_hand" and e.get("trainer_card") == group.trainer_card else e
                     for e in twin.log)
    return twin


def opponent_views(state):
    return [public_view(state, viewer) for viewer in OPPONENT_VIEWS]


def answer(state, choices, player=0):
    return apply_command(state, ResolveDecision(player, state.decision.id, tuple(choices)))


def heads(state):
    return with_coin_results(state, CoinSide.HEADS)


# ---------------------------------------------------------------- A: 盤面


def waterfall(conventions=None, prizes=HIDDEN, deck=None):
    """たきのぼりしんか（ロケット団のコイキング）。山札にギャラドス 1 枚（双子はサイド・置いておくカード）。"""
    return state_of({"active": mon(H.ROCKET_MAGIKARP, (W, W, W), played_turn=1), "deck": deck if deck is not None else [H.GYARADOS] + [W] * 5,
                     "prizes": list(prizes)}, conventions=conventions)


def moon(conventions=None, prizes=HIDDEN, deck=None):
    """つきのちから（エリカのピッピ）。山札にエリカのピクシー 1 枚（ピッピ自身に重ねられる）。"""
    return state_of({"active": mon(H.ERIKAS_CLEFAIRY, (W,)), "deck": deck if deck is not None else [H.ERIKAS_CLEFABLE] + [W] * 5, "prizes": list(prizes)},
                    conventions=conventions)


def waterfall_tickled(conventions=None):
    return tickled({"active": mon(H.ROCKET_MAGIKARP, (W, W, W), played_turn=1), "deck": [W, H.GYARADOS] + [W] * 5, "prizes": list(HIDDEN)},
                   conventions=conventions)


def moon_tickled(conventions=None):
    return tickled({"active": mon(H.ERIKAS_CLEFAIRY, (W,)), "deck": [W, H.ERIKAS_CLEFABLE] + [W] * 5, "prizes": list(HIDDEN)}, conventions=conventions)


# (名前, 盤面, 動かすカード, 双子を作る関数, 宣言の前の盤面の準備)
A_TWINS = (
    ("たきのぼりしんか・サイド", waterfall, H.GYARADOS, swap_hidden, lambda s: s),
    ("たきのぼりしんか・置いておくカード", waterfall_tickled, H.GYARADOS, swap_set_aside, lambda s: s),
    ("つきのちから・サイド", moon, H.ERIKAS_CLEFABLE, swap_hidden, heads),
    ("つきのちから・置いておくカード", moon_tickled, H.ERIKAS_CLEFABLE, swap_set_aside, heads),
)
A_INDEX = {waterfall: WATERFALL, waterfall_tickled: WATERFALL, moon: MOON, moon_tickled: MOON}


class DecisionPresenceTwinTest(unittest.TestCase):
    """A: 進化カードが山札にある・ない（サイド・持ち主に見えない置いておくカード）だけが違う双子で、宣言を受理したあとの相手・観戦者の観測とログが同じ（3 つの集合）。"""

    def test_opponent_and_spectator_see_the_same_after_declaration(self):
        for conventions in SETS:
            for name, build, card, twin_of, prepare in A_TWINS:
                with self.subTest(conventions=conventions, board=name):
                    s = prepare(build(conventions))
                    twin = twin_of(s, card)
                    self.assertEqual(opponent_views(s), opponent_views(twin))  # 前提
                    declare = UseAttack(0, A_INDEX[build])
                    self.assertEqual(twin_command_problems([s, twin], [declare], viewers=OPPONENT_VIEWS, owner_knowledge=True, until_public_difference=False), [])
                    after = [apply_command(x, declare) for x in (s, twin)]
                    self.assertEqual(opponent_views(after[0]), opponent_views(after[1]))
                    for viewer in OPPONENT_VIEWS:
                        self.assertEqual(observe(after[0], viewer)["decision"], {"kind": SEARCH_DECK, "player": 0})  # 選べるものの数・空であることも見せない

    def test_waterfall_declining_and_finding_nothing_look_the_same(self):
        # 任意の進化: 0 枚の答えは、選ばなかった（山札にギャラドス）・選べるカードがなかった（サイド・置いておくカード）のどちらも同じ公開のログ（理由は本人だけ）
        for conventions in SETS:
            for name, build, card, twin_of, _ in A_TWINS[:2]:
                with self.subTest(conventions=conventions, board=name):
                    s = build(conventions)
                    twin = twin_of(s, card)
                    steps = [UseAttack(0, WATERFALL), lambda x: ResolveDecision(0, x.decision.id, ())]
                    self.assertEqual(twin_command_problems([s, twin], steps, viewers=OPPONENT_VIEWS, owner_knowledge=True, until_public_difference=False), [])
                    done = [answer(apply_command(x, UseAttack(0, WATERFALL)), ()) for x in (s, twin)]
                    self.assertEqual(opponent_views(done[0]), opponent_views(done[1]))
                    reasons = [[e["reason"] for e in x.log if e["kind"] == "evolve_from_deck_declined"] for x in done]
                    self.assertEqual(reasons, [["declined"], ["no_target"]])
                    for x in done:
                        public = [e for e in visible_log(x, 1) if e["kind"] == "evolve_from_deck_declined"]
                        self.assertEqual([("reason" in e, e["hidden"]) for e in public], [(False, {"reason": None})])
                        own = [e for e in visible_log(x, 0) if e["kind"] == "evolve_from_deck_declined"]
                        self.assertIn(own[0]["reason"], ("declined", "no_target"))

    def test_moon_power_result_is_the_public_outcome(self):
        # つきのちからは「のせる」（「てよい」がない。v0.42 の決定は 1〜1 枚）。答えのあとの結果（進化した・しなかった）は場の公開の情報で、ここで分かれるのは原文の処理が公開する
        # 結果（v0.84 の A3・v0.105 の test_hidden_deck_contents_do_not_leak と同じ区別）。決定の有無・形（相手に見える部分）は分かれない
        s = heads(moon())
        twin = swap_hidden(s, H.ERIKAS_CLEFABLE)
        a, b = apply_command(s, UseAttack(0, MOON)), apply_command(twin, UseAttack(0, MOON))
        self.assertEqual(((a.decision.min_choices, a.decision.max_choices), (b.decision.min_choices, b.decision.max_choices)), ((1, 1), (0, 0)))
        done_a, done_b = answer(a, a.decision.options), answer(b, ())
        self.assertEqual(done_a.cards[done_a.players[0].active.card].card_id, H.ERIKAS_CLEFABLE)
        self.assertEqual([e["kind"] for e in done_b.log[len(b.log):] if e["kind"] in ("evolve", "evolve_from_deck_none", "shuffle")],
                         ["evolve_from_deck_none", "shuffle"])


class OwnerChoiceTest(unittest.TestCase):
    """A: 検索が始まったあとは、本人の選択に実際の山札を使う（本人の観測に実際の候補とカード）。"""

    def test_owner_sees_and_chooses_the_real_candidates(self):
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                s = waterfall(conventions)
                waiting = apply_command(s, UseAttack(0, WATERFALL))
                gyarados = next(u for u in s.players[0].deck if s.cards[u].card_id == H.GYARADOS)
                self.assertEqual(waiting.decision.options, (gyarados,))
                self.assertEqual([o["card_id"] for o in observe(waiting, 0)["decision"]["options"]], [H.GYARADOS])
                done = answer(waiting, (gyarados,))
                self.assertEqual(done.cards[done.players[0].active.card].card_id, H.GYARADOS)
                m = heads(moon(conventions))
                asked = apply_command(m, UseAttack(0, MOON))
                self.assertEqual([m.cards[u].card_id for u in asked.decision.options], [H.ERIKAS_CLEFABLE])
                self.assertEqual(answer(asked, asked.decision.options).cards[asked.players[0].active.card].card_id, H.ERIKAS_CLEFAIRY)  # 下のカード

    def test_no_candidate_candidate_and_declining(self):
        s = waterfall()
        asked = apply_command(s, UseAttack(0, WATERFALL))
        self.assertEqual((asked.decision.min_choices, asked.decision.max_choices), (0, 1))
        declined = answer(asked, ())
        self.assertEqual(declined.cards[declined.players[0].active.card].card_id, H.ROCKET_MAGIKARP)
        self.assertEqual([e["kind"] for e in declined.log[len(asked.log):] if e["kind"] in ("evolve_from_deck_declined", "shuffle")],
                         ["evolve_from_deck_declined", "shuffle"])
        none = apply_command(waterfall(deck=[W] * 6), UseAttack(0, WATERFALL))
        self.assertEqual((none.decision.kind, none.decision.options, none.decision.min_choices, none.decision.max_choices), (SEARCH_DECK, (), 0, 1))
        done = answer(none, ())
        self.assertEqual([e["kind"] for e in done.log[len(none.log):] if e["kind"] in ("evolve_from_deck_declined", "evolve_from_deck_none", "shuffle")],
                         ["evolve_from_deck_declined", "shuffle"])
        self.assertEqual(done.current_player, 1)  # ワザなので番は終わる（決定を答えたあと）

    def test_empty_deck_has_no_decision(self):
        # 山札が 0 枚なら見るカードがない（枚数は公開）。決定を出さずに evolve_from_deck_none（v0.148 までと同じ）
        for build, index, prepare in ((waterfall, WATERFALL, lambda s: s), (moon, MOON, heads)):
            with self.subTest(build=build.__name__):
                s = prepare(build(deck=[], prizes=(W,)))
                done = apply_command(s, UseAttack(0, index))
                self.assertIsNone(done.decision)
                self.assertIn("evolve_from_deck_none", [e["kind"] for e in done.log[len(s.log):]])

    def test_both_coin_faces(self):
        s = moon(deck=[W] * 6)
        tails = apply_command(with_coin_results(s, CoinSide.TAILS), UseAttack(0, MOON))
        self.assertIsNone(tails.decision)
        self.assertFalse([e for e in tails.log[len(s.log):] if e["kind"] in ("evolve_from_deck_none", "shuffle")])  # 「うら」なら山札を見ない・切らない
        asked = apply_command(heads(s), UseAttack(0, MOON))
        self.assertEqual((asked.decision.kind, asked.decision.options, asked.decision.min_choices, asked.decision.max_choices), (SEARCH_DECK, (), 0, 0))
        done = answer(asked, ())
        self.assertEqual([e["kind"] for e in done.log[len(asked.log):] if e["kind"] in ("evolve_from_deck_none", "shuffle")], ["evolve_from_deck_none", "shuffle"])


class InvalidAnswerTest(unittest.TestCase):
    """A: 不正な答え（選べないカード・数の違う答え・相手プレイヤーの答え）は拒否し、状態・乱数・ログを変えない。理由の文は双子で同じ。"""

    def test_invalid_answers_change_nothing(self):
        for name, build, card, twin_of, prepare in A_TWINS:
            with self.subTest(board=name):
                s = prepare(build())
                asked = apply_command(s, UseAttack(0, A_INDEX[build]))
                twin = apply_command(twin_of(s, card), UseAttack(0, A_INDEX[build]))
                stray = next(u for u in s.players[0].deck if s.cards[u].card_id == W)
                for player, choices in ((0, (stray,)), (0, (stray, stray)), (1, ())):
                    for x in (asked, twin):
                        before = snapshot(x)
                        outcome = command_outcome(x, ResolveDecision(player, x.decision.id, choices))[0]
                        self.assertNotEqual(outcome[0], "accepted", (player, choices))
                        self.assertNotIn("state_changed", outcome)
                        self.assertEqual(snapshot(x), before)
                    # 相手プレイヤーの答えの拒否は、双子で同じ理由の文（選べるものの数・中身を書かない）
                    if player == 1:
                        outcomes = [command_outcome(x, ResolveDecision(1, x.decision.id, ()))[0] for x in (asked, twin)]
                        self.assertEqual(outcomes[0], outcomes[1])


class SaveRestoreTest(unittest.TestCase):
    """A: 決定を待つ状態を保存・復元しても、同じ決定・同じ答えの結果（v0.148 と同じく pickle の往復）。"""

    def test_pending_decision_survives_save_and_restore(self):
        for name, build, card, twin_of, prepare in A_TWINS:
            with self.subTest(board=name):
                s = prepare(build())
                for x in (s, twin_of(s, card)):
                    asked = apply_command(x, UseAttack(0, A_INDEX[build]))
                    restored = pickle.loads(pickle.dumps(asked))
                    self.assertEqual(restored.decision, asked.decision)
                    self.assertEqual(opponent_views(restored), opponent_views(asked))
                    choices = asked.decision.options[:1] if asked.decision.min_choices else ()
                    self.assertEqual(snapshot(answer(restored, choices)), snapshot(answer(asked, choices)))


class V148PreflightTest(unittest.TestCase):
    """v0.148 の宣言の前の漏れ（PSP-ATTACK-DECK-EVOLUTION-PREFLIGHT-ORACLE）が再発しない（v0.148 の双子をそのまま試す。3 つの集合）。"""

    def test_v148_declarations_still_do_not_depend_on_the_deck(self):
        for conventions in SETS:
            for name, build, card, index, code, patch in DECLARATIONS:
                with self.subTest(conventions=conventions, declaration=name), patch():
                    s = build(conventions=conventions)
                    twin = swap_hidden(s, card)
                    outcomes = [command_outcome(x, UseAttack(0, index))[0] for x in (s, twin)]
                    self.assertEqual(outcomes[0][:2], ("UnsupportedError", code))
                    self.assertEqual(outcomes[0], outcomes[1])


# ---------------------------------------------------------------- B: 秘密領域の候補集合


def fervor(conventions=None, rainbow_in="deck"):
    """熱血!（引いた 1 枚）。山札（引いたあと）にレインボーエネルギー 1 枚。置いておくカードは水 2 枚。"""
    return tickled({"active": mon(H.RATTATA), "deck": [H.FERVOR, W, RAINBOW, W, W, W], "prizes": list(HIDDEN)}, conventions=conventions)


def master_ball(conventions=None):
    """マスターボール（イントロパック★neo。neo の説明の「たねポケモン」で NB1）。山札にピチュー（ベイビィポケモン）1 枚。"""
    return tickled({"active": mon(H.RATTATA), "deck": [H.MASTER_BALL_NIP1, W, PICHU] + [W] * 7, "prizes": list(HIDDEN)}, conventions=conventions)


def howl(conventions=None):
    """エンテイ（［おたけび］。手札から場に出した時）。山札にレインボーエネルギー 1 枚。"""
    return tickled({"active": mon(H.CHARMANDER), "deck": [H.ENTEI_NEO3, W, RAINBOW] + [W] * 6, "prizes": list(HIDDEN), "discard": [R]},
                   conventions=conventions)


def quilava(conventions=None):
    """わるいマグマラシのマグマラッシュ（山札の上から 5 枚をトラッシュ。``hidden_deck_pool``）。山札にレインボーエネルギー 1 枚。"""
    return tickled({"active": mon(QUILAVA, (R, R), evolved_from=[H.CYNDAQUIL_PF1]), "deck": [W, W, RAINBOW] + [W] * 6, "prizes": list(HIDDEN)}, conventions=conventions)


def play(card_id):
    return lambda s: PlayTrainer(0, hand_uid(s, card_id))


def bench(card_id):
    return lambda s: PlayBasicToBench(0, hand_uid(s, card_id))


def use_offered(s):
    return ResolveDecision(0, s.decision.id, s.decision.options)


# (名前, 盤面, 動かすカード, コマンドの並び, 止めるコード)
B_TARGETS = (
    ("熱血! FV1", fervor, RAINBOW, (play(H.FERVOR),), FV1),
    ("マスターボール neo NB1", master_ball, PICHU, (play(H.MASTER_BALL_NIP1),), NB1),
    ("［おたけび］ RB1", howl, RAINBOW, (bench(H.ENTEI_NEO3), use_offered), RB1),
    ("マグマラッシュ FV1（hidden_deck_pool）", quilava, RAINBOW, (UseAttack(0, 1),), FV1),
)


def run_steps(state, steps):
    """コマンドを順に送り、それぞれの段の結果の印（拒否で止める）。"""
    outcomes = []
    for step in steps:
        command = step(state) if callable(step) else step
        outcome, after = command_outcome(state, command)
        outcomes.append(outcome)
        if after is None:
            break
        state = after
    return outcomes


class HiddenSetAsideTwinTest(unittest.TestCase):
    """B: 山札と持ち主に見えない置いておくカードの配分だけが違う双子・山札とうらのサイドの配分だけが違う双子で、受理・拒否・コード・理由の文が同じ（3 つの集合）。"""

    def test_outcomes_do_not_depend_on_the_distribution(self):
        for conventions in SETS:
            for name, build, card, steps, code in B_TARGETS:
                with self.subTest(conventions=conventions, target=name):
                    s = build(conventions)
                    for twin in (swap_set_aside(s, card), swap_hidden(s, card)):
                        self.assertEqual([public_view(s, v) for v in (0, 1, None)], [public_view(twin, v) for v in (0, 1, None)])  # 前提（持ち主を含む）
                        a, b = run_steps(s, steps), run_steps(twin, steps)
                        self.assertEqual(a, b)
                        self.assertEqual(a[-1][:2], ("UnsupportedError", code))

    def test_reasons_carry_no_hidden_uid(self):
        for name, build, card, steps, _ in B_TARGETS:
            with self.subTest(target=name):
                s = build()
                hidden = {u for u in (*s.players[0].deck, *s.players[0].prizes, *s.set_aside[0].cards) if s.cards[u].card_id == card}
                message = run_steps(s, steps)[-1][2]
                self.assertFalse([u for u in hidden if re.search(rf"(?<![\d.]){u}(?!\d)", message)], message)


class SetAsideBoundaryTest(unittest.TestCase):
    """B: 候補集合の境界。持ち主に見えない置いておくカードは含む・持ち主に見える置いておくカード・おもてのサイドは含まない・山札にうらのカードがなければ山札だけ。"""

    def test_hidden_set_aside_card_alone_still_stops(self):
        # 止めるカードが置いておくカードだけにあっても止める（山札にあるかもしれない。持ち主にも見えない）
        s = swap_set_aside(fervor(), RAINBOW)
        self.assertFalse([u for u in s.players[0].deck if s.cards[u].card_id == RAINBOW])
        self.assertEqual(run_steps(s, (play(H.FERVOR),))[-1][:2], ("UnsupportedError", FV1))

    def test_pool_helpers(self):
        # 補助関数だけの確かめ（構築盤面からの合法な操作のあと）: searchable_deck_cards・possible_deck_cards は持ち主に見えない置いておくカードを含む。hidden_deck_pool も
        s = quilava()
        aside = set(s.set_aside[0].cards)
        self.assertTrue(aside <= set(E.searchable_deck_cards(s, 0)))
        self.assertTrue(aside <= set(E.possible_deck_cards(s, 0)))
        from kyuura_engine.resolution.programs import hidden_deck_pool

        class Run:
            state, player = s, 0

        self.assertEqual(sorted(hidden_deck_pool(Run, ())), sorted(E.possible_deck_cards(s, 0)))

    def test_face_up_prizes_are_not_in_the_pool(self):
        # おもてのサイド（ロケット団参上!で全員に見える）は山札の上にありえないので数えない（v0.148 までは数えて止めた。意図した変化。docs 4 章）
        s = state_of({"active": mon(H.RATTATA), "hand": [H.HERE_COMES_TEAM_ROCKET, H.FERVOR], "deck": [W] * 6, "prizes": [RAINBOW] + [W] * 5})
        s = apply_command(s, PlayTrainer(0, hand_uid(s, H.HERE_COMES_TEAM_ROCKET)))
        self.assertTrue(set(s.players[0].prizes) <= set(s.face_up_prizes))
        self.assertEqual(run_steps(s, (play(H.FERVOR),))[-1], ("accepted",))
        hidden = state_of({"active": mon(H.RATTATA), "hand": [H.FERVOR], "deck": [W] * 6, "prizes": [RAINBOW] + [W] * 5})
        self.assertEqual(run_steps(hidden, (play(H.FERVOR),))[-1][:2], ("UnsupportedError", FV1))  # うらのサイドは今までどおり

    def test_without_rainbow_anywhere_is_accepted(self):
        s = tickled({"active": mon(H.RATTATA), "deck": [H.FERVOR] + [W] * 5, "prizes": list(HIDDEN)})
        self.assertEqual(run_steps(s, (play(H.FERVOR),))[-1], ("accepted",))


class RemainingDecisionPresenceLeakTest(unittest.TestCase):
    """直していない別の漏れ（PSP-DECK-SEARCH-DECISION-PRESENCE-OTHERS。docs 6 章）: 同じ形（山札に選べるカードがなければ決定を出さずに ``…_none`` で進む）のほかの経路のうち、構築盤面の
    双子で確かめた 2 つ。漏れがないこと（相手・観戦者の公開の情報が配分によらない）を確かめるテストを ``expectedFailure`` で置く（漏れを正常な仕様として固定しない。直したら、この
    テストが「予期しない成功」になるので、印を外す）。この版の範囲（任意の山札からの進化のワザ・秘密領域の候補集合）の外なので、直していない。"""

    @unittest.expectedFailure
    def test_errand_decision_presence_does_not_depend_on_the_deck(self):
        # エリカのフシギダネの「おつかい」（RevealTrainerFromDeck。「加えてよい」の任意）。山札にキズぐすり 1 枚（双子はサイド）
        s = heads(state_of({"active": mon(H.ERIKAS_BULBASAUR, (H.GRASS, H.GRASS)), "deck": [H.POTION] + [W] * 5, "prizes": list(HIDDEN)}))
        after = [apply_command(x, UseAttack(0, 1)) for x in (s, swap_hidden(s, H.POTION))]
        self.assertEqual(opponent_views(after[0]), opponent_views(after[1]))

    @unittest.expectedFailure
    def test_cocoon_decision_presence_does_not_depend_on_the_deck(self):
        # キョウのコクーンの［うか］（CoinEvolveSelfFromDeck。「のせて進化させる」の必ず重ねる特殊能力）。山札にキョウのスピアー 1 枚（双子はサイド）。必ず重ねるので、答えのあとの
        # 結果（進化した・しなかった）は公開されるが、決定の有無はその前に分かれる（v0.84 の A3 の考え方と合わない）
        s = heads(state_of({"active": mon(H.KOGAS_KAKUNA, (H.GRASS,), evolved_from=[H.KOGAS_WEEDLE]), "deck": [H.KOGAS_BEEDRILL] + [W] * 5, "prizes": list(HIDDEN)}))
        pid = s.players[0].active.pokemon_id
        after = [apply_command(x, UsePokemonPower(0, pid, 0)) for x in (s, swap_hidden(s, H.KOGAS_BEEDRILL))]
        self.assertEqual(opponent_views(after[0]), opponent_views(after[1]))


class DocumentTest(unittest.TestCase):
    def test_document_records_the_fix(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("PSP-OPTIONAL-DECK-EVOLUTION-DECISION-PRESENCE", "PSP-HIDDEN-SET-ASIDE-DECK-POOL", "evolve_from_deck_declined", "hidden_deck_pool",
                       "searchable_deck_cards", "possible_deck_cards", "DecisionPresenceNoLeakTest",
                       "PSP-DECK-SEARCH-DECISION-PRESENCE-OTHERS"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
