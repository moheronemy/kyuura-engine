"""v0.148（docs/attack-deck-evolution-preflight-v0.148.md）: 山札から進化カードを重ねるワザの、山札を見る前の確かめ（宣言の前の先読みを含む）が、本人に見えない山札の中身を
読んでいた情報漏れの修正（両モード共通。PSP-ATTACK-DECK-EVOLUTION-PREFLIGHT-ORACLE）。

v0.147 までは、``resolution/programs.py`` の次の要素が、山札を見る前の確かめで実際の山札の進化カードを読んだ。ワザの宣言の前の先読みは、ワザの要素を実際の状態の複製で試す
ので、同じ公開の情報・同じ持ち主の知識から、進化カードが山札とサイドのどちらにあるかで、宣言の受理・拒否・コード・理由の文（山札のカードの uid）が分かれた。

- たきのぼりしんか（``EvolveAttackerFromDeck``）の組（DV2・GV1）
- からやぶりしんか・ひざしをあびる・ばくれつしんか（``EvolveAttackerFromDeck`` の ``required``）の、どのカードも選ぶと止める（H1・PW4）
- つきのちから（``EvolveFromDeck``。コイン）の組（DV2・GV1）と、どのカードも選ぶと止める（H1・PW4）
- しんかのほうし（``EvolveChosenFromDeck``）の、選んだポケモンのどのカードも選ぶと止める（H1・PW4）
- しんかのうた（``EachPlayerEvolvesFromDeck``）の、ポケモンを選ぶと止める（DV2・GV1・NB2・H1・PW4）

修正: 山札にあるかもしれないカード（``effects.searchable_deck_cards``）と配分を読まない下限（``effects.deck_choice_may_only_stop``）で決める。盤面はテスト専用の盤面
（``build_test_state``）で、``new_game`` からの合法な操作の列ではない（docs 2 章）。研究上の問い（DV2・GV1・H1・PW4・NB2）は決めない。
"""

from __future__ import annotations

import pathlib
import pickle
import unittest
from contextlib import nullcontext

from kyuura_engine import (
    PlayTrainer,
    ResolveDecision,
    UseAttack,
    UsePokemonPower,
    apply_command,
)
from kyuura_engine import effects as E
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import SEARCH_DECK
from kyuura_engine.state import SetAsideCards
from tests import helpers as H
from tests.helpers import with_coin_results
from tests.log_audit import command_outcome, twin_command_problems
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
DOC = ROOT / "docs" / "attack-deck-evolution-preflight-v0.148.md"
G = H.GRASS
DV2, GV1, H1, PW4, NB2 = ("UNRESOLVED_EVOLVE_AFTER_DEVOLUTION", "UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK", "UNRESOLVED_EVOLUTION_HP",
                          "UNRESOLVED_ENTRY_POWER_DURING_ATTACK", "UNRESOLVED_NEO_TEXT_EVOLUTION_CARD_BABY")
JUMPLUFF, HOPPIP, SKIPLOOM = "neo3-007", "neo2-004", "neo1-012"
METAPOD_NEO2, BUTTERFREE_NEO2 = "neo2-006", "neo2-009"
PICHU = "neo1-042"
WATERFALL, MOON, SPORE, SONG, HATCH = 1, 0, 0, 0, 1  # ワザの位置


def spray(s, pokemon_id):
    """退化スプレーで ``pokemon_id`` の進化カードを 1 枚はがす（合法な操作。今の番に退化した）。"""
    s = apply_command(s, PlayTrainer(0, hand_uid(s, H.DEVOLUTION_SPRAY)))
    s = apply_command(s, ResolveDecision(0, s.decision.id, (pokemon_id,)))
    return apply_command(s, ResolveDecision(0, s.decision.id, (1,)))


def waterfall_devolved(n=1, prizes=HIDDEN, conventions=None, deck_rest=5):
    """ギャラドスを退化スプレーではがしたロケット団のコイキング（DV2。v0.147 の RemainingAttackLeakTest と同じ盤面）。"""
    s = state_of({"active": mon(H.GYARADOS, (W, W, W), evolved_from=[H.ROCKET_MAGIKARP]), "hand": [H.DEVOLUTION_SPRAY],
                  "deck": [H.GYARADOS] * n + [W] * deck_rest, "prizes": list(prizes)}, conventions=conventions)
    return spray(s, s.players[0].active.pokemon_id)


def waterfall(n=1, prizes=HIDDEN, conventions=None):
    return state_of({"active": mon(H.ROCKET_MAGIKARP, (W, W, W), played_turn=1), "deck": [H.GYARADOS] * n + [W] * 5, "prizes": list(prizes)},
                    conventions=conventions)


def moon_devolved(n=1, prizes=HIDDEN, conventions=None):
    s = state_of({"active": mon(H.ERIKAS_CLEFAIRY, (W,)), "bench": [mon(H.GYARADOS, evolved_from=[H.MAGIKARP])], "hand": [H.DEVOLUTION_SPRAY],
                  "deck": [H.GYARADOS] * n + [W] * 5, "prizes": list(prizes)}, conventions=conventions)
    return spray(s, s.players[0].bench[0].pokemon_id)


def moon_entry(n=1, prizes=HIDDEN, conventions=None, clefables=0):
    """わるいハクリューのいるつきのちから。わるいカイリュー（場に出た時の［てしたをよぶ］。選ぶと PW4）``n`` 枚と、止めないエリカのピクシー ``clefables`` 枚。"""
    return state_of({"active": mon(H.ERIKAS_CLEFAIRY, (W,)), "bench": [mon(H.DARK_DRAGONAIR, evolved_from=[H.ROCKET_DRATINI])],
                     "deck": [H.DARK_DRAGONITE] * n + [H.ERIKAS_CLEFABLE] * clefables + [W] * 5, "prizes": list(prizes)}, conventions=conventions)


def moon_hp(n=1, prizes=HIDDEN, conventions=None):
    """つきのちからとベンチのハネッコ（ポポッコを重ねると H1 になるよう ``with_low_evolution_hp`` で判定を差しかえる。構築盤面と差しかえた判定だけ）。"""
    return state_of({"active": mon(H.ERIKAS_CLEFAIRY, (W,)), "bench": [HOPPIP], "deck": [SKIPLOOM] * n + [W] * 5, "prizes": list(prizes)},
                    conventions=conventions)


def spore_hp(n=1, prizes=HIDDEN, conventions=None):
    """しんかのほうし（ワタッコ）とベンチのハネッコ。H1 は、ポポッコの HP がハネッコの HP より大きく、ダメージがハネッコの HP 以上ならきぜつしているので、今の写しの通常の
    ダメージでは起こらない（最大HP を変える「きょだいか」はバトル場のワザを使ったポケモン自身だけ）。``with_low_evolution_hp`` で判定を差しかえる（v0.43 のつきのちからの H1 の
    テストと同じ方法。構築盤面と差しかえた判定だけ）。"""
    return state_of({"active": mon(JUMPLUFF, (G,), evolved_from=[HOPPIP, SKIPLOOM]), "bench": [HOPPIP], "deck": [SKIPLOOM] * n + [W] * 5,
                     "prizes": list(prizes)}, conventions=conventions)


def with_low_evolution_hp(base_name="ハネッコ"):
    """判定の差しかえ: 「``base_name``」から進化するカードを重ねると HP が 0（どれも H1）。ほかのカードは今の判定のまま。"""
    from unittest import mock

    real = E.evolution_hp
    return mock.patch.object(E, "evolution_hp", lambda state, pokemon, card: 0 if state.card_def(card).evolves_from == base_name else real(state, pokemon, card))


def hatch_hp(n=1, prizes=HIDDEN, conventions=None):
    """からやぶりしんか（トランセル neo2-006。コイン →「おもて」なら回復して、山札のバタフリーを必ず重ねる）。H1 は回復のあとなので今の写しでは起こらない。
    ``with_low_evolution_hp("トランセル")`` で判定を差しかえる（構築盤面と差しかえた判定だけ。必ず重ねるワザの経路の確かめ）。"""
    return state_of({"active": mon(METAPOD_NEO2, (G, G), evolved_from=[H.CATERPIE], played_turn=1), "deck": [BUTTERFREE_NEO2] * n + [W] * 5, "prizes": list(prizes)}, conventions=conventions)


def song_devolved(n=1, prizes=HIDDEN, conventions=None):
    s = state_of({"active": mon(H.LIGHT_WIGGLYTUFF, (W,), evolved_from=H.JIGGLYPUFF_NEO4), "bench": [mon(H.GYARADOS, evolved_from=[H.MAGIKARP])],
                  "hand": [H.DEVOLUTION_SPRAY], "deck": [H.GYARADOS] * n + [W] * 5, "prizes": list(prizes)}, conventions=conventions)
    return spray(s, s.players[0].bench[0].pokemon_id)


def bench_pid(s):
    return s.players[0].bench[0].pokemon_id


def choose_bench(s):
    return ResolveDecision(0, s.decision.id, (bench_pid(s),))


# (名前, 盤面を作る関数, 動かすカード, ワザの位置, 止めるコード, 判定の差しかえ)。対象のカード 1 枚が山札（双子はサイド）
DECLARATIONS = (
    ("たきのぼりしんか DV2", waterfall_devolved, H.GYARADOS, WATERFALL, DV2, nullcontext),
    ("つきのちから DV2", moon_devolved, H.GYARADOS, MOON, DV2, nullcontext),
    ("つきのちから PW4", moon_entry, H.DARK_DRAGONITE, MOON, PW4, nullcontext),
    ("つきのちから H1", moon_hp, SKIPLOOM, MOON, H1, with_low_evolution_hp),
    ("しんかのほうし H1", spore_hp, SKIPLOOM, SPORE, H1, with_low_evolution_hp),
    ("からやぶりしんか H1", hatch_hp, BUTTERFREE_NEO2, HATCH, H1, lambda: with_low_evolution_hp("トランセル")),
)


class TwinTest(unittest.TestCase):
    """山札とサイドの配分だけが違う双子（3 者の観測・ログの写し・持ち主の所有カード・乱数が同じ）で、宣言の受理・拒否・コード・理由の文が同じ（3 つの集合）。"""

    def test_declarations_are_the_same_wherever_the_card_is(self):
        for name, build, card, index, code, patch in DECLARATIONS:
            for conventions in SETS:
                with self.subTest(name, conventions=conventions), patch():
                    s = build(conventions=conventions)
                    twin = swap_hidden(s, card)
                    outcomes = [command_outcome(x, UseAttack(0, index))[0] for x in (s, twin)]
                    self.assertEqual([o[:2] for o in outcomes], [("UnsupportedError", code)] * 2)
                    self.assertEqual(outcomes[0], outcomes[1])
                    self.assertEqual(twin_command_problems([s, twin], [UseAttack(0, index)], owner_knowledge=True), [])

    def test_reasons_carry_no_deck_card_uid(self):
        for name, build, card, index, _, patch in DECLARATIONS:
            with self.subTest(name), patch():
                s = build()
                outcome = command_outcome(s, UseAttack(0, index))[0]
                uids = [u for u in s.players[0].deck if s.cards[u].card_id == card]
                self.assertTrue(uids)
                self.assertIn(E.POSSIBLE_DECK_EVOLUTION_DETAIL, outcome[2])
                for uid in uids:
                    self.assertNotIn(f"[{uid}]", outcome[2])
                    self.assertNotIn(f"({uid},", outcome[2])

    def test_evolution_song_pokemon_choice_is_the_same(self):
        """しんかのうた: 宣言は受理（任意の決定）。1 つめの決定（山札を見る前）の選ぶと止めるポケモンと、そのポケモンを選んだ答えの拒否が、配分によらない。"""
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                s = song_devolved(conventions=conventions)
                twin = swap_hidden(s, H.GYARADOS)
                self.assertEqual(twin_command_problems([s, twin], [UseAttack(0, SONG), choose_bench], owner_knowledge=True, until_public_difference=False), [])
                waiting = [apply_command(x, UseAttack(0, SONG)) for x in (s, twin)]
                self.assertEqual([w.decision.context_value("unresolved_choices") for w in waiting], [(bench_pid(s),)] * 2)
                self.assertEqual([command_outcome(w, choose_bench(w))[0][:2] for w in waiting], [("UnsupportedError", DV2)] * 2)


class BeforeFixLeakTest(unittest.TestCase):
    """修正の前の挙動の記録（v0.147 の ``RemainingAttackLeakTest`` が記録していた漏れ）が、今は起こらないこと。v0.147 では、たきのぼりしんかの宣言が、ギャラドスが山札なら DV2、
    サイドなら受理だった。"""

    def test_waterfall_evolution_no_longer_depends_on_the_deck(self):
        s = waterfall_devolved()
        twin = swap_hidden(s, H.GYARADOS)
        self.assertEqual([command_outcome(x, UseAttack(0, WATERFALL))[0][:2] for x in (s, twin)], [("UnsupportedError", DV2)] * 2)


class BoundaryTest(unittest.TestCase):
    """どのカードも選ぶと止める確かめ（H1・PW4）の下限の境界と、組（DV2・GV1）の「あるかもしれない」の境界。"""

    def test_entry_card_with_confirmable_other_card(self):
        # つきのちから（PW4）: 止めないエリカのピクシーが山札にあると下限で確かめられれば受理。サイド 1 枚（うら）なら 2 枚、サイド 0 枚なら 1 枚
        for prizes, clefables, accepted in (((W,), 1, False), ((W,), 2, True), ((), 1, True), (HIDDEN, 6, False), (HIDDEN, 7, True)):
            with self.subTest(prizes=len(prizes), clefables=clefables):
                s = moon_entry(prizes=prizes, clefables=clefables)
                outcome = command_outcome(with_coin_results(s, CoinSide.HEADS), UseAttack(0, MOON))[0]
                self.assertEqual(outcome[:2], ("accepted",) if accepted else ("UnsupportedError", PW4))

    def test_no_possible_stop_card_is_accepted(self):
        # 止めるカード（わるいカイリュー）が見えないカードに 1 枚もなければ、サイドが何枚でも受理
        s = moon_entry(n=0)
        self.assertEqual(command_outcome(with_coin_results(s, CoinSide.HEADS), UseAttack(0, MOON))[0], ("accepted",))

    def test_devolved_without_any_possible_card_is_accepted(self):
        # 退化したコイキングでも、見えないカードにギャラドスがなければ（コイキングから進化するカードがない）受理し、選べるもののない決定にはならない
        s = waterfall_devolved(n=0)
        waiting = apply_command(s, UseAttack(0, WATERFALL))
        self.assertEqual((waiting.decision.kind, waiting.decision.options), (SEARCH_DECK, ()))  # v0.149: 選べるもののない決定（0〜1 枚）
        done = apply_command(waiting, ResolveDecision(0, waiting.decision.id, ()))
        self.assertTrue([e for e in done.log[len(waiting.log):] if e["kind"] == "evolve_from_deck_declined"])

    def test_empty_deck_does_not_count_prize_cards(self):
        # 山札にうらのカードがなければ、サイドのギャラドスは山札にありえない（``searchable_deck_cards``）。山札 0 枚の退化したコイキングは受理
        s = waterfall_devolved(n=0, deck_rest=0, prizes=(H.GYARADOS, W, W, W, W, W))
        self.assertEqual(s.players[0].deck, [])
        self.assertEqual(E.searchable_deck_cards(s, 0), ())
        self.assertEqual(command_outcome(s, UseAttack(0, WATERFALL))[0], ("accepted",))

    def test_reserve_counts_earlier_targets(self):
        # 補助関数だけの確かめ: しんかのほうしで先に重ねるポケモンが k 匹なら、止めないカードを k + 1 枚確かめる（``reserve``）。サイド 0 枚で、山札はポポッコ 1 枚・水 5 枚
        s = spore_hp(prizes=())
        hoppip = s.players[0].bench[0]

        def fits(uid):
            return E.evolution_card_fits(s, hoppip, uid)

        def skiploom(uid):
            return s.cards[uid].card_id == SKIPLOOM

        self.assertTrue(E.deck_choice_may_only_stop(s, 0, fits, skiploom))  # 選べるのはポポッコだけで、それが止める
        self.assertFalse(E.deck_choice_may_only_stop(s, 0, fits, lambda uid: False))  # 止めるカードがない
        self.assertFalse(E.deck_choice_may_only_stop(s, 0, lambda uid: True, skiploom, reserve=4))  # 止めない 5 枚 ≥ 4 + 1
        self.assertTrue(E.deck_choice_may_only_stop(s, 0, lambda uid: True, skiploom, reserve=5))  # 止めない 5 枚 < 5 + 1


class AcceptedPathTest(unittest.TestCase):
    """安全に宣言・処理できる正の例と、先読みと実行の一致・任意の進化を断る答え・コイン・保存と復元。"""

    def test_waterfall_evolution_still_evolves_or_finds_nothing(self):
        for in_deck in (True, False):
            with self.subTest(in_deck=in_deck):
                s = waterfall()
                if not in_deck:
                    s = swap_hidden(s, H.GYARADOS)
                waiting = apply_command(s, UseAttack(0, WATERFALL))
                # v0.149: どちらも決定（0〜1 枚）を出す（v0.148 までは、山札にギャラドスがなければ決定を出さずに evolve_from_deck_none で進んだ。
                # PSP-OPTIONAL-DECK-EVOLUTION-DECISION-PRESENCE。tests/test_optional_deck_evolution_presence_v0_149.py）
                self.assertEqual((waiting.decision.kind, waiting.decision.min_choices, waiting.decision.max_choices), (SEARCH_DECK, 0, 1))
                if in_deck:
                    done = apply_command(waiting, ResolveDecision(0, waiting.decision.id, waiting.decision.options))
                    self.assertEqual(done.cards[done.players[0].active.card].card_id, H.GYARADOS)
                else:
                    self.assertEqual(waiting.decision.options, ())
                    done = apply_command(waiting, ResolveDecision(0, waiting.decision.id, ()))
                    self.assertEqual([e["reason"] for e in done.log[len(waiting.log):] if e["kind"] == "evolve_from_deck_declined"], ["no_target"])

    def test_declining_the_optional_evolution(self):
        s = waterfall()
        waiting = apply_command(s, UseAttack(0, WATERFALL))
        done = apply_command(waiting, ResolveDecision(0, waiting.decision.id, ()))
        self.assertTrue([e for e in done.log[len(waiting.log):] if e["kind"] == "evolve_from_deck_declined"])
        self.assertEqual(done.cards[done.players[0].active.card].card_id, H.ROCKET_MAGIKARP)

    def test_accepted_moon_power_offers_a_card_that_does_not_stop(self):
        # 先読み（受理）と実行の一致: 受理したら、山札を見た決定に、選んでも止めないカードがある
        s = moon_entry(prizes=(), clefables=1)
        waiting = apply_command(with_coin_results(s, CoinSide.HEADS), UseAttack(0, MOON))
        d = waiting.decision
        stops = set(d.context_value("entry_power_choices", ())) | set(d.context_value("unresolved_choices", ()))
        self.assertEqual(d.kind, SEARCH_DECK)
        self.assertTrue(set(d.options) - stops)
        tails = apply_command(with_coin_results(s, CoinSide.TAILS), UseAttack(0, MOON))
        self.assertIsNone(tails.decision)

    def test_rejection_changes_nothing_and_repeats(self):
        for name, build, _, index, _, patch in DECLARATIONS:
            with self.subTest(name), patch():
                s = build()
                before = snapshot(s)
                first = command_outcome(s, UseAttack(0, index))[0]
                second = command_outcome(s, UseAttack(0, index))[0]
                self.assertEqual(first, second)
                self.assertNotIn("state_changed", first)
                self.assertEqual(snapshot(s), before)

    def test_save_and_restore_keep_the_result(self):
        for name, build, card, index, _, patch in DECLARATIONS:
            with self.subTest(name), patch():
                s = build()
                twin = swap_hidden(s, card)
                for x in (s, twin):
                    restored = pickle.loads(pickle.dumps(x))
                    self.assertEqual(command_outcome(restored, UseAttack(0, index))[0], command_outcome(x, UseAttack(0, index))[0])


class KeptStopsTest(unittest.TestCase):
    """既存の進化の制限と停止を緩めていないこと。"""

    def test_devolved_card_in_the_deck_still_stops(self):
        # ギャラドス 2 枚とうらのサイド 1 枚（ギャラドスが山札にあることを持ち主が下限で確かめられる）盤面でも、今までどおり DV2
        s = waterfall_devolved(n=2, prizes=(W,))
        self.assertEqual(E.deck_lower_bound_where(s, 0, lambda uid: s.cards[uid].card_id == H.GYARADOS), 1)
        self.assertEqual(command_outcome(s, UseAttack(0, WATERFALL))[0][:2], ("UnsupportedError", DV2))

    def test_permission_pair_still_stops(self):
        # 構築盤面: 今の番に場に出し、サカキの許可のあるロケット団のコイキング（今の写しでは許可を受けない。GV1 の確かめ）
        s = state_of({"active": mon(H.ROCKET_MAGIKARP, (W, W, W), played_turn=7), "deck": [H.GYARADOS] + [W] * 5, "prizes": list(HIDDEN)})
        s.players[0].active.evolution_permission_turn = 7
        twin = swap_hidden(s, H.GYARADOS)
        self.assertEqual([command_outcome(x, UseAttack(0, WATERFALL))[0][:2] for x in (s, twin)], [("UnsupportedError", GV1)] * 2)

    def test_required_evolution_open_question_is_unchanged(self):
        # からやぶりしんか（必ず重ねる）: 退化した番は、山札の中身によらず DV2（v0.105 の公開の情報だけの確かめ。コインの前）
        for n in (0, 1):
            with self.subTest(butterfree=n):
                s = state_of({"active": mon(BUTTERFREE_NEO2, (G, G), evolved_from=[H.CATERPIE, METAPOD_NEO2]), "hand": [H.DEVOLUTION_SPRAY],
                              "deck": [BUTTERFREE_NEO2] * n + [W] * 5, "prizes": list(HIDDEN)})
                s = spray(s, s.players[0].active.pokemon_id)
                self.assertEqual(command_outcome(s, UseAttack(0, HATCH))[0][:2], ("UnsupportedError", DV2))

    def test_normal_evolution_limits_still_apply(self):
        # 今の番に場に出したコイキング（許可なし）は、山札にギャラドスがあっても選べない（通常の進化の制限）。決定は選べるもののない形
        s = state_of({"active": mon(H.ROCKET_MAGIKARP, (W, W, W), played_turn=7), "deck": [H.GYARADOS] + [W] * 5, "prizes": list(HIDDEN)})
        waiting = apply_command(s, UseAttack(0, WATERFALL))
        self.assertEqual(waiting.decision.options, ())  # v0.149: 決定は出す（選べるものはない）
        done = apply_command(waiting, ResolveDecision(0, waiting.decision.id, ()))
        self.assertEqual(done.cards[done.players[0].active.card].card_id, H.ROCKET_MAGIKARP)

    def test_song_baby_counts_owner_hidden_set_aside_cards(self):
        # 補助関数だけの確かめ（構築盤面）: しんかのうたの NB2 の「山札にあるかもしれない」に、持ち主に見えない置いておくカードを含める（v0.147 までは山札とサイドだけ）
        s = state_of({"active": mon(H.LIGHT_WIGGLYTUFF, (W,), evolved_from=H.JIGGLYPUFF_NEO4), "bench": [PICHU], "deck": [H.PIKACHU_NEO1] + [W] * 5,
                      "prizes": list(HIDDEN)})
        pikachu = next(u for u in s.players[0].deck if s.cards[u].card_id == H.PIKACHU_NEO1)
        s.players[0].deck.remove(pikachu)
        s.set_aside = (*s.set_aside, SetAsideCards(kind="hand", owner=0, cards=(pikachu,), visible_to=(), user=1, trainer_card=pikachu, card_id="test",
                                                   created_turn=7))
        self.assertIn(pikachu, E.searchable_deck_cards(s, 0))
        pichu = s.players[0].bench[0]
        from kyuura_engine.resolution.programs import baby_evolution_cards_possible

        self.assertTrue(baby_evolution_cards_possible(s, 0, pichu))  # v0.147 までの山札とサイドだけでは偽（置いておくカードと山札の配分で変わった）


class PowerCocoonTest(unittest.TestCase):
    """［うか］（特殊能力。v0.147 で直した）の、v0.147 で確かめていなかった GV1・H1 の経路（構築盤面だけ）。"""

    def cocoon(self, prizes=HIDDEN, **extra):
        return state_of({"active": mon(H.KOGAS_KAKUNA, evolved_from=[H.KOGAS_WEEDLE], **extra), "deck": [H.KOGAS_BEEDRILL] + [W] * 5, "prizes": list(prizes)})

    def test_permission_is_the_same_in_both_twins(self):
        s = self.cocoon(evolved_turn=7)  # 今の番にキョウのビードルから進化した（構築盤面）。サカキの許可（今の写しでは「サカキの」ポケモンでないので受けない）
        s.players[0].active.evolution_permission_turn = 7
        twin = swap_hidden(s, H.KOGAS_BEEDRILL)
        declare = UsePokemonPower(0, s.players[0].active.pokemon_id, 0)
        outcomes = [command_outcome(x, declare)[0] for x in (s, twin)]
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(outcomes[0][:2], ("UnsupportedError", GV1))
        self.assertEqual(twin_command_problems([s, twin], [declare], owner_knowledge=True), [])

    def test_evolution_hp_is_the_same_in_both_twins(self):
        # キョウのコクーン（HP 60）にキョウのスピアー（HP 80）を重ねて H1 になる盤面は、ダメージが最大HP 以上（きぜつ）になり作れない（「きょだいか」の 80 でも同じ）。
        # v0.43 のつきのちからの H1 のテストと同じく、判定（``evolution_hp``）を差しかえて確かめる（判定を差しかえた構築盤面だけ）
        from unittest import mock

        s = self.cocoon(damage=10)
        twin = swap_hidden(s, H.KOGAS_BEEDRILL)
        declare = UsePokemonPower(0, s.players[0].active.pokemon_id, 0)
        with mock.patch.object(E, "evolution_hp", lambda state, pokemon, card: 10):
            outcomes = [command_outcome(x, declare)[0] for x in (s, twin)]
            self.assertEqual(outcomes[0][:2], ("UnsupportedError", H1))
            self.assertEqual(outcomes[0], outcomes[1])
            self.assertEqual(twin_command_problems([s, twin], [declare], owner_knowledge=True), [])


class DecisionPresenceNoLeakTest(unittest.TestCase):
    """v0.148 で直していなかった別の漏れ（PSP-OPTIONAL-DECK-EVOLUTION-DECISION-PRESENCE。docs 6 章）の回帰テスト。v0.148 では ``expectedFailure`` で置いた（クラス名
    ``RemainingDecisionPresenceLeakTest``）。v0.149（docs/optional-deck-evolution-presence-v0.149.md）で直したので、印を外して漏れがないことを確かめる通常のテストにした: 任意の
    山札からの進化（たきのぼりしんか）・つきのちから（「おもて」）は、山札にカードがあれば、選べる進化カードがなくても決定を出すので、宣言を受理したあとの相手・観戦者の公開の情報
    （観測とログの写し）は、進化カードが山札とサイドのどちらにあるかによらない。"""

    def test_waterfall_evolution_decision_presence_does_not_depend_on_the_deck(self):
        from tests.log_audit import public_view

        s = waterfall()
        twin = swap_hidden(s, H.GYARADOS)
        after = [apply_command(x, UseAttack(0, WATERFALL)) for x in (s, twin)]
        for viewer in (1, None):
            self.assertEqual(public_view(after[0], viewer), public_view(after[1], viewer))

    def test_moon_power_decision_presence_does_not_depend_on_the_deck(self):
        from tests.log_audit import public_view

        s = state_of({"active": mon(H.ERIKAS_CLEFAIRY, (W,)), "bench": [], "deck": [H.ERIKAS_CLEFABLE] + [W] * 5, "prizes": list(HIDDEN)})
        twin = swap_hidden(s, H.ERIKAS_CLEFABLE)
        after = [apply_command(with_coin_results(x, CoinSide.HEADS), UseAttack(0, MOON)) for x in (s, twin)]
        for viewer in (1, None):
            self.assertEqual(public_view(after[0], viewer), public_view(after[1], viewer))


class DocumentTest(unittest.TestCase):
    def test_document_records_the_fix(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("PSP-ATTACK-DECK-EVOLUTION-PREFLIGHT-ORACLE", "searchable_deck_cards", "deck_choice_may_only_stop", "PSP-DECK-CONTENT-PRECHECKS",
                       "RemainingAttackLeakTest"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
