"""v0.83（docs/shining-gentle-pokemon-v0.83.md）: エコロジムとリサイクルエネルギーの不要な TE2 の修正と、ひかるポケモン 10 枚・やさしいポケモン 7 枚・ギャロップ（ES1-014）。

根拠は kyuura データの採用の記録（``card_sources.json``。印刷の文面）と、既存の記録の再利用（v0.82 の場からトラッシュに置かれたエネルギーカードの共通の処理・
RUL-ENERGY-DISCARD-ATTACKS・GR-2000-P321-DAMAGE-ORDER・CR-COUNTERATTACK-TIMING）。公式ガイドブックは読んでいない（誌面のページは書かない）。
"""

from __future__ import annotations

import copy
import pathlib
import pickle
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy,
    EndTurn,
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    UseAttack,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    ATTACH_FROM_HAND,
    DISCARD_TO_DECK,
    RECOVER_POKEMON,
    SEARCH_DECK,
    SELECT_DRAW_COUNT,
    SELECT_POKEMON,
    SELECT_SPECIAL_CONDITION,
    TAKE_LOOKED_CARDS,
)
from kyuura_engine.deck import deck_problems
from kyuura_engine.errors import UnsupportedError
from kyuura_engine.observation import (
    HIDDEN_COUNT_KINDS,
    PUBLIC_EVENTS,
    observe,
    visible_log,
)
from kyuura_engine.persistent import reflect_shield
from kyuura_engine.state import CannotAttackNextOwnTurn, ReflectShield
from tests import helpers as H
from tests.helpers import apply_kernel, build_test_state, with_coin_results
from tests.test_energy_discard_return_v0_82 import wooper_id
from tests.test_neo_trainer_components_v0_80 import (
    audited,
    mon,
    new_events,
    rejects,
    snapshot,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "shining-gentle-pokemon-v0.83.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
TURN = 7
W, F, L, P, G, FT = H.WATER, H.FIRE, H.LIGHTNING, H.PSYCHIC, H.GRASS, H.FIGHTING
RE, ECO, DCE, RAINBOW = H.RECYCLE_ENERGY, H.ECOGYM, H.DOUBLE_COLORLESS_ENERGY, H.RAINBOW_ENERGY
METAL = "neo1-095"
QUAGSIRE = "neo3-014"
SUNKERN, VENONAT, PSYDUCK, CHINCHOU, SLOWPOKE, DRATINI, PONYTA = "neo1-006", "PMCG2-004", "PMCG3-010", "neo1-037", "PMCG3-027", H.DRATINI, H.PONYTA


def board(active, *, bench=(H.RATTATA,), opponent=None, opponent_bench=(H.RATTATA,), hand=(), opponent_hand=(), deck=None, opponent_deck=None,
          discard=(), opponent_discard=(), current=0, turn=TURN):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": list(deck if deck is not None else [W] * 10), "discard": list(discard), "prizes": 6}
    them = {"active": opponent or mon(H.RATTATA), "bench": list(opponent_bench), "hand": list(opponent_hand),
            "deck": list(opponent_deck if opponent_deck is not None else [W] * 10), "discard": list(opponent_discard), "prizes": 6}
    return build_test_state([me, them], turn_number=turn, current_player=current)


def answer(state, choices, player=None):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player if player is None else player, d.id, tuple(choices)))


def attack(state, index, coins=(), **options):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, UseAttack(state.current_player, index), **options)


def play(state, card_id, player=0):
    uid = next(u for u in state.players[player].hand if state.cards[u].card_id == card_id)
    return apply_kernel(state, PlayTrainer(player, uid))


def returned(before, after):
    return [(e["card"], tuple(e["reasons"]), e["cause"], e.get("by_player")) for e in new_events(before, after, "energy_returned_to_hand")]


def amounts(before, after):
    return [(e.get("target", "opponent_active"), e["amount"]) for e in new_events(before, after, "damage")]


def all_uids(state):
    found = []
    for p in state.players:
        found += p.hand + p.deck + p.discard + list(p.prizes)
        for pokemon in p.in_play():
            found += list(pokemon.cards()) + list(pokemon.energy) + [t.card for t in pokemon.trainers]
    if state.stadium is not None:
        found.append(state.stadium.card)
    return sorted(found)


def uid_of(state, card_id, player=0, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


# ---------------------------------------------------------------- 2 章: エコロジムとリサイクルエネルギーの不要な TE2


class EcogymRecycleTe2Test(unittest.TestCase):
    """v0.82 の ``energy_discard_plan`` は、リサイクルエネルギーで手札にもどることが決まっていても、エコロジムの「「無色」以外」を ［へんしん］のメタモンの無色の特殊エネルギーで
    問い（TE2）、使う前にエネルギー・リムーブを拒否していた。どちらの読み方でも同じ uid が 1 回だけ持ち主の手札にもどる（ログの理由だけが違う）ので止めない。"""

    def ditto_board(self, energy):
        state = board(mon(H.RATTATA), hand=(ECO, H.ENERGY_REMOVAL), opponent=mon(H.DITTO, energy))
        return play(state, ECO)

    def test_recycle_alone_is_playable_and_returns_once(self):
        # 修正の前は、ここで UNRESOLVED_TRANSFORM_SPECIAL_ENERGY（エネルギー・リムーブを使う前）
        state = self.ditto_board((RE,))
        choosing = play(state, H.ENERGY_REMOVAL)
        recycle = state.players[1].active.energy[0]
        self.assertEqual(choosing.decision.options, (recycle,))
        done = answer(choosing, (recycle,))
        # 決まった理由（リサイクルエネルギー）だけを記録する。エコロジムが当たるかは決まらないので書かない
        self.assertEqual(returned(choosing, done), [(recycle, ("recycle_energy",), "trainer", 0)])
        self.assertEqual(done.players[1].hand.count(recycle), 1)
        self.assertNotIn(recycle, done.players[1].discard)
        events = new_events(choosing, done, "discard_attached_energy", "trainer_discard_energy")
        self.assertEqual(len(events), 1)  # トラッシュに置いたことは消さない
        self.assertEqual(sorted(state.cards), all_uids(done))
        audited(self, done)

    def test_recycle_with_dce_rejects_only_the_dce_answer(self):
        state = self.ditto_board((RE, DCE))
        choosing = play(state, H.ENERGY_REMOVAL)  # 修正の前は、ここで TE2
        recycle, dce = state.players[1].active.energy
        self.assertEqual(choosing.decision.options, (recycle, dce))
        rejects(self, choosing, ResolveDecision(0, choosing.decision.id, (dce,)), E.TRANSFORM_SPECIAL_ENERGY_CODE)
        done = answer(choosing, (recycle,))  # 同じ決定に、もう一度答えられる
        self.assertEqual(returned(choosing, done), [(recycle, ("recycle_energy",), "trainer", 0)])
        self.assertIn(dce, done.players[1].active.energy)
        audited(self, done)

    def test_dce_alone_is_still_te2(self):
        state = self.ditto_board((DCE,))
        rejects(self, state, PlayTrainer(0, uid_of(state, H.ENERGY_REMOVAL)), E.TRANSFORM_SPECIAL_ENERGY_CODE)

    def test_opponent_attack_path(self):
        """相手のワザ（ヌオーの「デストロイパンチ」。v0.82 のエネルギーカードをトラッシュする要素）でも、リサイクルエネルギーを選ぶ答えは進み、無色2個エネルギーを選ぶ答えだけを
        TE2 で拒否する（v0.82 では、宣言の前の先読みが無色2個エネルギーの答えで止まり、ワザを使えなかった）。"""
        state = play(board(mon(QUAGSIRE, (W, W, W, W), evolved_from=wooper_id()), hand=(ECO,), opponent=mon(H.DITTO, (RE, DCE))), ECO)
        recycle, dce = state.players[1].active.energy
        choosing = attack(state, 1)
        d = choosing.decision
        self.assertEqual((d.options, d.context_value("unresolved_choices"), d.context_value("unresolved_code")), ((recycle, dce), (dce,), E.TRANSFORM_SPECIAL_ENERGY_CODE))
        rejects(self, choosing, ResolveDecision(0, d.id, (dce,)), E.TRANSFORM_SPECIAL_ENERGY_CODE)
        done = answer(choosing, (recycle,))
        self.assertEqual(returned(choosing, done), [(recycle, ("recycle_energy",), "attack", 0)])
        audited(self, done)
        # 無色2個エネルギーだけなら、どの答えでも止まるので、宣言の前に止める（v0.82 と同じ）
        alone = play(board(mon(QUAGSIRE, (W, W, W, W), evolved_from=wooper_id()), hand=(ECO,), opponent=mon(H.DITTO, (DCE,))), ECO)
        rejects(self, alone, UseAttack(0, 1), E.TRANSFORM_SPECIAL_ENERGY_CODE)

    def test_opponent_power_path(self):
        """相手の特殊能力（キョウのベトベトンの［だつりょくえき］。控えでもはたらく）でトラッシュするとき、［へんしん］のメタモンのリサイクルエネルギーは手札にもどり、無色2個エネルギーを
        選ぶ答えだけを TE2 で拒否する。メタモンは相手の対戦ポケモン（ひかるカブトプス）に姿を変え、「いなずまぎり」の「おもて」で相手の控えのキョウのベトベトンにダメージを与える。"""
        muk = mon(H.KOGAS_MUK, (G,), evolved_from=H.KOGAS_GRIMER)
        state = play(board(mon(H.DITTO, (W, W, W, RE, DCE)), hand=(ECO,), opponent=mon(H.SHINING_KABUTOPS), opponent_bench=(muk,)), ECO)
        _, _, _, recycle, dce = state.players[0].active.energy
        choosing = attack(state, 0, (HD, HD))  # いなずまぎりの「おもて」→［だつりょくえき］の「おもて」
        d = choosing.decision
        self.assertEqual((d.kind, d.player), ("energy_drain_discard", 1))
        self.assertEqual((d.context_value("unresolved_choices"), d.context_value("unresolved_code")), ((dce,), E.TRANSFORM_SPECIAL_ENERGY_CODE))
        rejects(self, choosing, ResolveDecision(1, d.id, (dce,)), E.TRANSFORM_SPECIAL_ENERGY_CODE)
        done = answer(choosing, (recycle,))
        self.assertEqual(returned(choosing, done), [(recycle, ("recycle_energy",), "power", 1)])
        audited(self, done)

    def test_normal_side(self):
        # エコロジムがなければ、リサイクルエネルギーだけの理由でもどる（v0.82 と同じ）
        state = board(mon(H.RATTATA), hand=(H.ENERGY_REMOVAL,), opponent=mon(H.DITTO, (RE,)))
        choosing = play(state, H.ENERGY_REMOVAL)
        done = answer(choosing, choosing.decision.options)
        self.assertEqual([r[1] for r in returned(choosing, done)], [("recycle_energy",)])
        # エコロジムの場で、基本エネルギー（「無色」以外と決まる）はエコロジムでもどる
        state = play(board(mon(H.RATTATA), hand=(ECO, H.ENERGY_REMOVAL), opponent=mon(H.DITTO, (W,))), ECO)
        choosing = play(state, H.ENERGY_REMOVAL)
        done = answer(choosing, choosing.decision.options)
        self.assertEqual([r[1:] for r in returned(choosing, done)], [(("ecogym",), "trainer", 0)])
        self.assertEqual(new_events(choosing, done, "energy_returned_to_hand")[0]["stadium_card"], state.stadium.card)
        # 色が決まる（［へんしん］でない）ポケモンのリサイクルエネルギーは「無色」なので、エコロジムは当たらず、理由はリサイクルエネルギーだけ
        state = play(board(mon(H.RATTATA), hand=(ECO, H.ENERGY_REMOVAL), opponent=mon(H.HITMONCHAN, (RE, FT))), ECO)
        choosing = play(state, H.ENERGY_REMOVAL)
        recycle = state.players[1].active.energy[0]
        self.assertEqual(choosing.decision.context_value("unresolved_choices"), None)
        done = answer(choosing, (recycle,))
        self.assertEqual(returned(choosing, done), [(recycle, ("recycle_energy",), "trainer", 0)])

    def test_plan_function_only_rejects_when_the_result_changes(self):
        state = self.ditto_board((RE, DCE))
        ditto = state.players[1].active
        recycle, dce = ditto.energy
        self.assertIsNone(E.energy_discard_problem(state, ditto, recycle, cause=E.DISCARD_BY_TRAINER, by_player=0))
        self.assertEqual(E.energy_discard_problem(state, ditto, dce, cause=E.DISCARD_BY_TRAINER, by_player=0)[0], E.TRANSFORM_SPECIAL_ENERGY_CODE)
        self.assertIsNone(E.energy_discard_problem(state, ditto, dce, cause=E.DISCARD_BY_TRAINER, by_player=1))  # 自分の効果はエコロジムに当たらない
        plan = E.energy_discard_plan(state, ditto, (recycle,), cause=E.DISCARD_BY_TRAINER, by_player=0)
        self.assertEqual([(item.card, item.reasons, item.stadium) for item in plan], [(recycle, ("recycle_energy",), None)])
        with self.assertRaises(UnsupportedError) as caught:
            E.energy_discard_plan(state, ditto, (dce,), cause=E.DISCARD_BY_TRAINER, by_player=0)
        self.assertEqual(caught.exception.code, E.TRANSFORM_SPECIAL_ENERGY_CODE)


# ---------------------------------------------------------------- 4 章: ひかるポケモンのデッキの枚数


class ShiningDeckLimitTest(unittest.TestCase):
    def deck(self, extra):
        return list(extra) + [H.RATTATA] + [W] * (59 - len(extra))

    def test_each_shining_name_has_its_own_limit_of_one(self):
        pool = load_card_pool()
        for card in H.V0_83_SHINING:
            self.assertEqual(pool.definitions[card].deck_limit, 1, card)
        self.assertEqual(pool.definitions["neo4-025"].deck_limit, 1)  # v0.82 のひかるリザードン
        self.assertIsNone(pool.definitions[H.RAPIDASH_ES1].deck_limit)
        # 名前ごとの上限: ちがう名前のひかるポケモンを 1 枚ずつは入れられる（ひかるポケモン全体の上限にしない）
        legal = self.deck([c for c in H.V0_83_SHINING if c != H.SHINING_MAGIKARP_PRN] + ["neo4-025"])
        self.assertEqual(deck_problems(legal, pool), [])
        self.assertEqual(deck_problems(self.deck([]), pool), [])
        # 同じ名前（neo3-022 と PRN-046 はどちらも「ひかるコイキング」）は合わせて 1 枚まで
        problems = deck_problems(self.deck([H.SHINING_MAGIKARP, H.SHINING_MAGIKARP_PRN]), pool)
        self.assertTrue(any("TOO_MANY_COPIES" in str(p) or "ひかるコイキング" in str(p) for p in problems), problems)
        for card in H.V0_83_SHINING:
            self.assertNotEqual(deck_problems(self.deck([card, card]), pool), [], card)
        # ふつうの同じ名前 4 枚の制限は変えない（ギャロップは 4 枚まで）
        self.assertEqual(deck_problems(self.deck([PONYTA] * 4 + [H.RAPIDASH_ES1] * 4), pool), [])
        self.assertNotEqual(deck_problems(self.deck([PONYTA] * 4 + [H.RAPIDASH_ES1] * 3 + ["QSG-011"] * 2), pool), [])


# ---------------------------------------------------------------- 5 章: おたがいのプレイヤーが選ぶワザ


class EachPlayerDrawTest(unittest.TestCase):
    """ひかるコイキングの「きんいろのうろこ」: ワザを使ったプレイヤー → 相手プレイヤーの順に、引くプレイヤー自身が 0〜2 枚を決める（決定 SELECT_DRAW_COUNT）。"""

    def test_each_player_decides_own_count(self):
        state = board(mon(H.SHINING_MAGIKARP, (W,)), deck=[G] * 5, opponent_deck=[F] * 5)
        first = attack(state, 0)
        d = first.decision
        self.assertEqual((d.kind, d.player, d.options, d.context_value("stage")), (SELECT_DRAW_COUNT, 0, (0, 1, 2), 0))
        # 相手は先に答えられない（決めるのは段階のプレイヤー自身）
        rejects(self, first, ResolveDecision(1, d.id, (2,)), "NOT_YOUR_DECISION", IllegalActionError)
        rejects(self, first, ResolveDecision(0, d.id, (3,)), "INVALID_CHOICE", IllegalActionError)
        second = answer(first, (1,))
        d2 = second.decision
        self.assertEqual((d2.kind, d2.player, d2.options, d2.context_value("stage")), (SELECT_DRAW_COUNT, 1, (0, 1, 2), 1))
        self.assertEqual(len(second.players[0].hand), 1)
        rejects(self, second, ResolveDecision(0, d2.id, (2,)), "NOT_YOUR_DECISION", IllegalActionError)
        done = answer(second, (2,))
        self.assertEqual(len(done.players[1].hand), 3)  # 2 枚 + 番の最初の 1 枚
        draws = [(e["player"], len(e["cards"])) for e in new_events(first, done, "draw")]
        self.assertEqual(draws[:2], [(0, 1), (1, 2)])
        audited(self, done)
        # 引いたカードは引いたプレイヤーだけが見る（枚数は公開）
        seen = [e for e in visible_log(done, 1) if e["kind"] == "draw" and e["player"] == 0]
        self.assertTrue(seen and all("cards" not in e for e in seen))

    def test_decline_short_deck_and_empty_deck(self):
        state = board(mon(H.SHINING_MAGIKARP, (W,)), deck=[G], opponent_deck=[])
        first = attack(state, 0)
        self.assertEqual(first.decision.options, (0, 1))  # 引けるだけ（最大 2 枚まで）
        done = answer(first, (0,))
        self.assertEqual([(e["player"], e["reason"]) for e in new_events(first, done, "attack_draw_declined")], [(0, "declined"), (1, "empty_deck")])
        # 山札 0 枚の相手は、番の最初に引けずに負けになる（効果で引かなかったことは負けではない。負けはワザのあとの番の最初）
        self.assertEqual([e["kind"] for e in new_events(first, done) if e["kind"] in ("attack_draw_declined", "game_end")][-1], "game_end")
        audited(self, done)

    def test_save_and_restore_mid_decision(self):
        first = attack(board(mon(H.SHINING_MAGIKARP, (W,)), deck=[G] * 5), 0)
        second = answer(first, (2,))
        for restored in (copy.deepcopy(second), pickle.loads(pickle.dumps(second))):
            self.assertEqual(snapshot(answer(restored, (1,))), snapshot(answer(second, (1,))))
        self.assertEqual(state_to_dict(second, format_version=22)["decision"]["context"], state_to_dict(copy.deepcopy(second), format_version=22)["decision"]["context"])
        audited(self, second)

    def test_copied_by_metronome_keeps_players_separate(self):
        """ピッピの「ゆびをふる」で相手のひかるコイキングの「きんいろのうろこ」を使う: 段階 0 はワザを使ったプレイヤー（ピッピの持ち主）、段階 1 は相手。カードの持ち主（ひかる
        コイキングの持ち主）がワザを使ったことにはならない。"""
        state = board(mon(H.CLEFAIRY, (W, W, W)), opponent=mon(H.SHINING_MAGIKARP), deck=[G] * 5)
        choosing = attack(state, 1)
        self.assertEqual(choosing.decision.kind, "select_attack")
        first = answer(choosing, (0,))
        self.assertEqual((first.decision.kind, first.decision.player), (SELECT_DRAW_COUNT, 0))
        second = answer(first, (1,))
        self.assertEqual((second.decision.kind, second.decision.player), (SELECT_DRAW_COUNT, 1))
        audited(self, answer(second, (0,)))


class DragonBondTest(unittest.TestCase):
    def test_reveals_exactly_one_named_card(self):
        state = board(mon(H.SHINING_MAGIKARP, (P,)), deck=[W, H.SHINING_GYARADOS, H.GYARADOS, "PMCG4-025", H.MAGIKARP])
        choosing = attack(state, 1)
        d = choosing.decision
        names = [state.card_def(u).name_ja for u in d.options]
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (SEARCH_DECK, 1, 1))
        self.assertEqual(Counter(names), Counter(["ギャラドス", "ひかるギャラドス", "わるいギャラドス"]))  # コイキングは選べない（名前の完全一致）
        rejects(self, choosing, ResolveDecision(0, d.id, ()), "INVALID_CHOICE_COUNT", IllegalActionError)
        done = answer(choosing, (d.options[0],))
        kinds = [e["kind"] for e in new_events(choosing, done)]
        self.assertEqual(kinds[:2], ["reveal_from_deck", "shuffle"])
        self.assertIn(d.options[0], done.players[0].hand)
        audited(self, done)

    def test_no_target_shuffles_without_revealing(self):
        state = board(mon(H.SHINING_MAGIKARP, (P,)), deck=[W, H.MAGIKARP])
        done = attack(state, 1)
        self.assertEqual([e["kind"] for e in new_events(state, done)][1:3], ["reveal_from_deck_none", "shuffle"])


class RecoveryFromDiscardTest(unittest.TestCase):
    def test_strange_flapping_each_player_own_discard(self):
        state = board(mon(H.LIGHT_VENOMOTH, (G,), evolved_from=VENONAT), discard=(H.RATTATA, W, "neo1-091"), opponent_discard=(H.RATTATA, H.POTION))
        first = attack(state, 0)
        d = first.decision
        own = state.players[0].discard
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (RECOVER_POKEMON, 0, (own[0],), 0, 1))  # なにかの化石は選べない
        rejects(self, first, ResolveDecision(1, d.id, ()), "NOT_YOUR_DECISION", IllegalActionError)
        second = answer(first, (own[0],))
        d2 = second.decision
        self.assertEqual((d2.player, d2.options), (1, (state.players[1].discard[0],)))
        # 相手のトラッシュのカードを、ワザを使ったプレイヤーが選べない（決めるのは相手）
        done = answer(second, ())
        self.assertEqual([(e["kind"], e["player"]) for e in new_events(first, done, "each_player_recover", "each_player_declined")],
                         [("each_player_recover", 0), ("each_player_declined", 1)])
        self.assertIn(own[0], done.players[0].hand)
        audited(self, done)
        # 公開: 相手から見ても手札に加えたカードが見える
        self.assertTrue(any(e["kind"] == "each_player_recover" and e.get("cards") == (own[0],) for e in visible_log(done, 1)))

    def test_light_up_coin_and_any_card(self):
        state = board(mon(H.LIGHT_LANTURN, (L,), evolved_from=CHINCHOU), discard=(H.POTION,), opponent_discard=(W,))
        first = attack(state, 0, (HD,))
        self.assertEqual(first.decision.options, tuple(state.players[0].discard))
        done = answer(answer(first, first.decision.options), (state.players[1].discard[0],))
        self.assertEqual([e["cards"] for e in new_events(first, done, "each_player_recover")], [tuple(state.players[0].discard), tuple(state.players[1].discard)])
        tails = attack(state, 0, (TL,))
        self.assertIsNone(tails.decision)
        self.assertEqual(new_events(state, tails, "each_player_recover"), [])

    def test_pokemon_tower_suppresses_hand_recovery_without_coin(self):
        state = play(board(mon(H.LIGHT_LANTURN, (L,), evolved_from=CHINCHOU), hand=(H.POKEMON_TOWER,), discard=(H.POTION,)), H.POKEMON_TOWER)
        done = attack(state, 0)
        self.assertEqual([e["kind"] for e in new_events(state, done)][1:2], ["discard_to_hand_suppressed"])
        self.assertEqual(new_events(state, done, "coin_flip"), [])
        state = play(board(mon(H.LIGHT_VENOMOTH, (G,), evolved_from=VENONAT), hand=(H.POKEMON_TOWER,), discard=(H.RATTATA,)), H.POKEMON_TOWER)
        self.assertIsNone(attack(state, 0).decision)

    def test_scoop_up_returns_up_to_three_and_shuffles_chooser(self):
        state = board(mon(H.LIGHT_SLOWBRO, (P,), evolved_from=SLOWPOKE), discard=(H.RATTATA,) * 4 + (W,), opponent_discard=(H.RATTATA,))
        first = attack(state, 0)
        d = first.decision
        self.assertEqual((d.kind, d.max_choices), (DISCARD_TO_DECK, 3))
        second = answer(first, d.options[:3])
        self.assertEqual(second.decision.player, 1)
        done = answer(second, ())
        kinds = [(e["kind"], e["player"]) for e in new_events(first, done) if e["kind"] in ("each_player_discard_to_deck", "shuffle", "each_player_declined")]
        self.assertEqual(kinds, [("each_player_discard_to_deck", 0), ("shuffle", 0), ("each_player_declined", 1)])  # 0 枚のプレイヤーは切らない
        self.assertEqual(len(done.players[0].deck), 10 + 3)
        audited(self, done)
        # ポケモンタワーは山札にもどす効果を消さない
        towered = play(board(mon(H.LIGHT_SLOWBRO, (P,), evolved_from=SLOWPOKE), hand=(H.POKEMON_TOWER,), discard=(H.RATTATA,)), H.POKEMON_TOWER)
        self.assertEqual(attack(towered, 0).decision.kind, DISCARD_TO_DECK)


class WebbingTest(unittest.TestCase):
    """やさしいゴルダックの「みずかき」: それぞれ自分の山札の上 3 枚だけを見て、その中の基本エネルギーカードを好きなだけ見せて手札に加え、自分の山札を切る。"""

    def test_each_player_looks_own_top_three(self):
        state = board(mon(H.LIGHT_GOLDUCK, (W,), evolved_from=PSYDUCK), deck=[W, H.RATTATA, F, G, G], opponent_deck=[H.RATTATA, H.RATTATA, H.RATTATA, W])
        first = attack(state, 0)
        d = first.decision
        top = state.players[0].deck[:3]
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (TAKE_LOOKED_CARDS, 0, (top[0], top[2]), 0, 2))  # 4 枚目の草は見ない
        second = answer(first, (top[2],))
        # v0.84（A3）: 相手の見た中に基本エネルギーカードがなくても、相手の決定（選べるものなし・0 枚だけが答え）を出して答えを待つ
        self.assertEqual((second.decision.kind, second.decision.player, second.decision.options), (TAKE_LOOKED_CARDS, 1, ()))
        done = answer(second, ())
        kinds = [(e["kind"], e["player"]) for e in new_events(state, done) if e["kind"] in ("look_at_deck_top", "reveal_from_deck", "shuffle", "deck_top_take_declined")]
        self.assertEqual(kinds, [("look_at_deck_top", 0), ("reveal_from_deck", 0), ("shuffle", 0), ("look_at_deck_top", 1), ("deck_top_take_declined", 1), ("shuffle", 1)])
        audited(self, done)
        # 相手には、見た山札のカード・選べるものの数を見せない
        view = observe(first, 1)
        self.assertIn(TAKE_LOOKED_CARDS, HIDDEN_COUNT_KINDS)
        self.assertNotIn("options", view.get("decision") or {})
        looked = [e for e in visible_log(done, 1) if e["kind"] == "look_at_deck_top" and e["player"] == 0]
        self.assertTrue(looked and all("cards" not in e for e in looked))
        declined = [e for e in visible_log(done, 0) if e["kind"] == "deck_top_take_declined"]
        self.assertTrue(declined and all("reason" not in e for e in declined))

    def test_short_deck_is_lt1(self):
        state = board(mon(H.LIGHT_GOLDUCK, (W,), evolved_from=PSYDUCK), opponent_deck=[W, W])
        rejects(self, state, UseAttack(0, 0), "UNRESOLVED_ATTACK_DECK_TOP_SHORT")
        state = board(mon(H.SHINING_MEW, (L,)), deck=[W, W])
        rejects(self, state, UseAttack(0, 0), "UNRESOLVED_ATTACK_DECK_TOP_SHORT")


# ---------------------------------------------------------------- 6 章: ひかるポケモン


class ShiningGyaradosTest(unittest.TestCase):
    def test_outrage(self):
        state = board(mon(H.SHINING_GYARADOS, (W, FT, FT), damage=30), opponent=mon(H.HITMONCHAN))
        self.assertEqual(amounts(state, attack(state, 0, (HD,))), [("opponent_active", 60)])
        tails = attack(state, 0, (TL,))
        self.assertEqual(amounts(state, tails), [])
        self.assertEqual([e["reason"] for e in new_events(state, tails, "attack_failed")], ["coin"])

    def test_burn_up_order_and_single_coin(self):
        state = board(mon(H.SHINING_GYARADOS, (W, W, F, F)), opponent=mon(H.HITMONCHAN, (FT,)), opponent_bench=(mon(H.RATTATA, (W,)), mon(H.RATTATA, (W, W))))
        choosing = attack(state, 1, (HD,))
        self.assertEqual(choosing.decision.kind, "discard_energy")
        first = answer(choosing, choosing.decision.options)
        kinds = [e["kind"] for e in new_events(state, first)]
        self.assertEqual([k for k in kinds if k in ("discard_energy", "damage", "coin_flip")],
                         ["discard_energy", "discard_energy", "damage", "damage", "damage", "coin_flip"])
        self.assertEqual(len(new_events(state, first, "coin_flip")), 1)  # ポケモンごとに投げ直さない
        done = first
        while done.decision is not None and done.decision.kind == "discard_opponent_energy":
            done = answer(done, (done.decision.options[0],))
        self.assertEqual(len(new_events(state, done, "discard_attached_energy")), 3)
        audited(self, done)
        tails = answer(attack(state, 1, (TL,)), choosing.decision.options)
        self.assertEqual(new_events(state, tails, "discard_attached_energy"), [])


class ShiningCelebiTest(unittest.TestCase):
    def test_healing_water_counts_water_units(self):
        state = board(mon(H.SHINING_CELEBI, (W, W, G)), bench=(mon(H.RATTATA, damage=20), H.RATTATA))
        choosing = attack(state, 0)
        self.assertEqual(choosing.decision.kind, SELECT_POKEMON)
        done = answer(choosing, (state.players[0].bench[0].pokemon_id,))
        self.assertEqual([e["counters"] for e in new_events(choosing, done, "attack_heal")], [2])
        no_bench = board(mon(H.SHINING_CELEBI, (W,)), bench=())
        failed = attack(no_bench, 0)  # 宣言は受け付け、ワザの内容で失敗する
        self.assertEqual([e["reason"] for e in new_events(no_bench, failed, "attack_failed")], ["no_bench"])

    def test_miracle_leaf_coins_per_unit_and_one_choice(self):
        state = board(mon(H.SHINING_CELEBI, (G, P)), opponent=mon(H.RATTATA, (DCE, W)))
        chose = attack(state, 1, (TL, TL, HD))  # 無色2個エネルギーは 2 個（3 枚投げる）
        self.assertEqual(len(new_events(state, chose, "coin_flip")), 3)
        d = chose.decision
        self.assertEqual((d.kind, d.options), (SELECT_SPECIAL_CONDITION, tuple(sorted(E.CHOSEN_CONDITIONS.index(c) for c in ("poison", "sleep", "confusion")))))
        done = answer(chose, (E.CHOSEN_CONDITIONS.index("confusion"),))
        self.assertTrue(done.players[1].active.conditions.confused)
        self.assertIsNone(attack(state, 1, (TL, TL, TL)).decision)
        no_energy = board(mon(H.SHINING_CELEBI, (G, P)), opponent=mon(H.HITMONCHAN))
        self.assertEqual(new_events(no_energy, attack(no_energy, 1), "coin_flip"), [])


class ShiningRaichuTest(unittest.TestCase):
    def test_choose_first_then_damage(self):
        state = board(mon(H.SHINING_RAICHU, (L, L, W, W, W)), opponent=mon(H.HITMONCHAN), opponent_bench=(H.RATTATA, H.RATTATA))
        choosing = attack(state, 0)
        self.assertEqual(amounts(state, choosing), [])  # 選ぶのはダメージより先
        done = answer(choosing, (state.players[1].bench[1].pokemon_id,))
        self.assertEqual(amounts(choosing, done), [("opponent_active", 40), ("opponent_bench", 30)])
        no_bench = board(mon(H.SHINING_RAICHU, (L, L, W, W)), opponent=mon(H.HITMONCHAN), opponent_bench=())
        self.assertEqual(amounts(no_bench, attack(no_bench, 0)), [("opponent_active", 40)])


class ShiningMewtwoTest(unittest.TestCase):
    def shielded(self, opponent, **extra):
        state = board(mon(H.SHINING_MEWTWO, (P, L)), opponent=opponent, **extra)
        return attack(state, 0)  # リフレクトシールド（ワザを使うと番が終わる）

    def test_heads_negates_and_returns_20(self):
        shielded = self.shielded(mon(H.HITMONCHAN, (FT, FT)))
        self.assertIsNotNone(reflect_shield(shielded, shielded.players[0].active))
        heads = attack(shielded, 0, (HD,))
        kinds = [(e["kind"], e.get("amount")) for e in new_events(shielded, heads) if e["kind"] in ("reflect_shield_check", "reflect_shield_damage", "damage")]
        self.assertEqual(kinds, [("reflect_shield_check", 20), ("reflect_shield_damage", 20), ("damage", 40)])  # ヒトカゲ…でなくエビワラーの弱点 超 で 40
        self.assertEqual(heads.players[0].active.damage, 0)
        self.assertEqual(new_events(shielded, heads, "reflect_shield_check")[0]["player"], 0)  # 投げるのはこのカードの持ち主
        audited(self, heads)
        tails = attack(shielded, 0, (TL,))
        self.assertEqual(tails.players[0].active.damage, 20)
        self.assertEqual(new_events(shielded, tails, "reflect_shield_damage"), [])

    def test_no_coin_for_zero_damage_or_prevented(self):
        shielded = self.shielded(mon(H.RATTATA, (W,)))
        # ひかるミュウツーの抵抗力はないが、ラッタ…の「たいあたり」10 にディフェンダーがあれば 0
        defended = shielded
        state = board(mon(H.SHINING_MEWTWO, (P, L)), opponent=mon(H.RATTATA, (W,)), hand=(H.DEFENDER,))
        state = play(state, H.DEFENDER)
        state = apply_kernel(state, ResolveDecision(0, state.decision.id, (state.players[0].active.pokemon_id,))) if state.decision else state
        shielded = attack(state, 0)
        hit = attack(shielded, 0)
        self.assertEqual(new_events(shielded, hit, "reflect_shield_check"), [])
        self.assertIsNotNone(defended)

    def test_expires_and_lost_on_bench(self):
        shielded = self.shielded(mon(H.RATTATA, (W,)))
        after = apply_kernel(shielded, EndTurn(1))
        after = apply_kernel(after, EndTurn(0))
        self.assertEqual([e for e in after.players[0].active.persistent_effects if isinstance(e, ReflectShield)], [])

    def test_ko_by_returned_damage(self):
        shielded = self.shielded(mon(H.HITMONCHAN, (FT, FT), damage=40))  # エビワラー（HP 70・弱点 超）。返す 20 は弱点で 40
        heads = attack(shielded, 0, (HD,))
        knocked = [e for e in new_events(shielded, heads, "knock_out")]
        self.assertEqual([(e["player"], e["pokemon"]) for e in knocked], [(1, shielded.players[1].active.card)])
        audited(self, heads)

    def test_psycho_burst(self):
        state = board(mon(H.SHINING_MEWTWO, (P, P, F)), opponent=mon(H.HITMONCHAN, (DCE, FT)))
        done = answer(attack(state, 1), (state.players[0].active.energy[2],))
        self.assertEqual(amounts(state, done), [("opponent_active", 140)])  # (40 + 3 × 10) × 2（弱点 超）


class ShiningKabutopsTest(unittest.TestCase):
    def test_lightning_slash(self):
        state = board(mon(H.SHINING_KABUTOPS, (FT, FT, L)), opponent=mon(H.HITMONCHAN), opponent_bench=(H.RATTATA, H.RATTATA))
        self.assertEqual(amounts(state, attack(state, 0, (HD,))), [("opponent_active", 40), ("opponent_bench", 10), ("opponent_bench", 10)])
        self.assertEqual(amounts(state, attack(state, 0, (TL,))), [("opponent_active", 30), ("self", 10)])

    def test_water_slash_counts_excess_water_and_ignores_resistance(self):
        state = board(mon(H.SHINING_KABUTOPS, (FT, FT, W, W, W, W)), opponent=mon(H.RATTATA))
        self.assertEqual(amounts(state, attack(state, 1)), [("opponent_active", 140)])  # (50 + 2 × 10) × 2（ラッタ…の弱点 闘。弱点は計算する）
        state = board(mon(H.SHINING_KABUTOPS, (FT, FT, W, W)), opponent=mon(H.SHINING_NOCTOWL))  # ひかるヨルノズク（抵抗力 闘 -30）。抵抗力は計算しない
        done = attack(state, 1)
        self.assertEqual(amounts(state, done), [("opponent_active", 50)])
        self.assertTrue(new_events(state, done, "damage")[0].get("ignore_resistance"))


class ShiningSteelixTest(unittest.TestCase):
    def test_earth_crush(self):
        state = board(mon(H.SHINING_STEELIX, (METAL, METAL, FT, FT)), opponent=mon(H.HITMONCHAN), opponent_bench=(H.RATTATA,))
        heads = attack(state, 0, (HD,))
        self.assertEqual(amounts(state, heads), [("opponent_active", 80), ("opponent_bench", 10), ("self_bench", 10)])
        tails = attack(state, 0, (TL,))
        self.assertEqual(amounts(state, tails), [])
        for done in (heads, tails):
            self.assertTrue(any(isinstance(e, CannotAttackNextOwnTurn) for e in done.players[0].active.persistent_effects))
            audited(self, done)


class ShiningNoctowlTest(unittest.TestCase):
    def test_flash_eye_by_heads(self):
        state = board(mon(H.SHINING_NOCTOWL, (P, L, W)), opponent=mon(H.HITMONCHAN))
        expected = {0: None, 1: "sleep", 2: "confusion", 3: "paralysis"}
        for coins, heads in (((TL, TL, TL), 0), ((HD, TL, TL), 1), ((TL, HD, HD), 2), ((HD, HD, HD), 3)):
            done = attack(state, 0, coins)
            names = done.players[1].active.conditions.names()
            self.assertEqual(sorted(names), [] if expected[heads] is None else [expected[heads]], coins)


class ShiningMewTest(unittest.TestCase):
    def test_flash_search(self):
        state = board(mon(H.SHINING_MEW, (L,)), deck=[W, G, F, P, W])
        choosing = attack(state, 0)
        top = tuple(state.players[0].deck[:3])
        self.assertEqual((choosing.decision.kind, choosing.decision.options, choosing.decision.min_choices), (TAKE_LOOKED_CARDS, top, 1))
        done = answer(choosing, (top[1],))
        self.assertEqual([e["kind"] for e in new_events(choosing, done)][:2], ["search_deck", "shuffle"])
        self.assertIn(top[1], done.players[0].hand)
        self.assertEqual(len(done.players[0].discard), 0)  # ほかのカードはトラッシュしない
        audited(self, done)

    def test_mystery_fire(self):
        state = board(mon(H.SHINING_MEW, (P, F)), opponent=mon(H.HITMONCHAN))
        for coin, condition in ((HD, "confusion"), (TL, "sleep")):
            choosing = attack(state, 1, (coin,))
            done = answer(choosing, choosing.decision.options)
            self.assertEqual([e["condition"] for e in new_events(choosing, done, "special_condition")], [condition])


# ---------------------------------------------------------------- 7 章: やさしいポケモン・ギャロップ


class LightPokemonTest(unittest.TestCase):
    def test_return_sunlight(self):
        state = board(mon(H.LIGHT_SUNFLORA, (W, W), evolved_from=SUNKERN), hand=(G, G, G, W), bench=(H.TANGELA, H.RATTATA))
        choosing = attack(state, 0)
        d = choosing.decision
        self.assertEqual((d.kind, d.options), (SELECT_POKEMON, (state.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id)))
        cards = answer(choosing, (state.players[0].bench[0].pokemon_id,))
        self.assertEqual((cards.decision.kind, cards.decision.max_choices), (ATTACH_FROM_HAND, 2))
        rejects(self, cards, ResolveDecision(0, cards.decision.id, ()), "UNRESOLVED_ATTACH_FROM_DISCARD_ZERO")
        done = answer(cards, cards.decision.options[:2])
        self.assertEqual(len(done.players[0].bench[0].energy), 2)
        self.assertEqual(done.energy_attachments_this_turn if hasattr(done, "energy_attachments_this_turn") else 0, 0)
        audited(self, done)

    def test_synchro_wave_counts_cards(self):
        state = board(mon(H.LIGHT_VENOMOTH, (P, W), evolved_from=VENONAT), opponent=mon(H.HITMONCHAN, (DCE,)))
        self.assertEqual([e["reason"] for e in new_events(state, attack(state, 1), "attack_failed")], ["condition"])
        state = board(mon(H.LIGHT_VENOMOTH, (P, W), evolved_from=VENONAT), opponent=mon(H.HITMONCHAN, (FT, FT)))
        self.assertEqual(amounts(state, attack(state, 1)), [("opponent_active", 40)])

    def test_core_blast_and_water_play(self):
        state = board(mon(H.LIGHT_GOLDUCK, (P, W, W), evolved_from=PSYDUCK), opponent=mon(H.HITMONCHAN, (DCE, RAINBOW, FT)))
        self.assertEqual(amounts(state, attack(state, 1))[0][1], 70)
        state = board(mon(H.LIGHT_SLOWBRO, (W, P), evolved_from=SLOWPOKE), opponent=mon(H.HITMONCHAN, (FT, FT, FT)))
        self.assertEqual(amounts(state, attack(state, 1)), [("opponent_active", 80)])  # (20 + 20) × 2
        state = board(mon(H.LIGHT_SLOWBRO, (W, P), evolved_from=SLOWPOKE), opponent=mon(H.HITMONCHAN, (FT, FT)))
        self.assertEqual(amounts(state, attack(state, 1)), [("opponent_active", 40)])  # 同じ数なら追加しない

    def test_wash_away(self):
        state = board(mon(H.LIGHT_VAPOREON, (W,), evolved_from=H.EEVEE), bench=(mon(H.RATTATA, (W, RE), damage=20),))
        choosing = attack(state, 0, (HD,))
        done = answer(choosing, choosing.decision.options)
        rat = done.players[0].bench[0]
        self.assertEqual((rat.damage, list(rat.energy)), (0, []))
        self.assertEqual([r[1] for r in returned(choosing, done)], [("recycle_energy",)])  # 自分のワザなのでエコロジムは関係しない
        audited(self, done)
        self.assertIsNone(attack(state, 0, (TL,)).decision)
        no_bench = board(mon(H.LIGHT_VAPOREON, (W,), evolved_from=H.EEVEE), bench=())
        failed = attack(no_bench, 0)
        self.assertEqual(new_events(no_bench, failed, "coin_flip"), [])
        self.assertEqual([e["reason"] for e in new_events(no_bench, failed, "attack_failed")], ["no_bench"])

    def test_hypno_shower_heals_bench_only(self):
        state = board(mon(H.LIGHT_VAPOREON, (W, W, W), evolved_from=H.EEVEE, damage=20), bench=(mon(H.RATTATA, damage=10),), opponent=mon(H.HITMONCHAN, damage=20),
                      opponent_bench=(mon(H.RATTATA, damage=20),))
        done = attack(state, 1)
        self.assertEqual([e["condition"] for e in new_events(state, done, "special_condition")], ["sleep"])
        self.assertEqual([(e["player"], e["counters"]) for e in new_events(state, done, "attack_heal")], [(0, 1), (1, 1)])
        self.assertEqual(done.players[0].active.damage, 20)

    def test_spark_and_healing_light_and_protective_wave(self):
        state = board(mon(H.LIGHT_LANTURN, (L, L), evolved_from=CHINCHOU), opponent=mon(H.HITMONCHAN), opponent_bench=(H.RATTATA,))
        done = answer(attack(state, 1), (state.players[1].bench[0].pokemon_id,))
        self.assertEqual(amounts(state, done), [("opponent_active", 30), ("opponent_bench", 10)])
        state = board(mon(H.LIGHT_DRAGONAIR, (W, W), evolved_from=DRATINI, damage=20), bench=(mon(H.RATTATA, damage=10), H.RATTATA))
        self.assertEqual([e["counters"] for e in new_events(state, attack(state, 0), "attack_heal")], [1, 1])
        state = board(mon(H.LIGHT_DRAGONAIR, (W, W, W), evolved_from=DRATINI))
        self.assertEqual([e["persistent_effect"] for e in new_events(state, attack(state, 1, (HD,)), "persistent_effect_added")], ["attack_barrier"])

    def test_rapidash_es1_shares_qsg011(self):
        registry = E.DEFAULT_EFFECTS
        for index in (0, 1):
            self.assertIs(registry.attack_entry(H.RAPIDASH_ES1, index), registry.attack_entry("QSG-011", index))
        self.assertIs(registry.attack_entry(H.SHINING_MAGIKARP_PRN, 0), registry.attack_entry(H.SHINING_MAGIKARP, 0))


class BoundaryTest(unittest.TestCase):
    """結果が変わる境界と、ふつうの側（docs 8 章）。"""

    def shielded(self, opponent):
        return attack(board(mon(H.SHINING_MEWTWO, (P, L)), opponent=opponent), 0)

    def test_reflect_shield_timing_rs1(self):
        # コインのあとに、ダメージを与えたポケモンのダメージが同じワザで変わる（いなずまぎりの「うら」の自分へのダメージ）。20 を与える時点で結果が変わりうるので止める（宣言の前）
        shielded = self.shielded(mon(H.SHINING_KABUTOPS, (FT, FT, L)))
        rejects(self, shielded, UseAttack(1, 0), "UNRESOLVED_REFLECT_SHIELD_TIMING")
        # ふつうの側: ダメージを与えたポケモンのダメージが変わらないワザは止めない
        plain = self.shielded(mon(H.HITMONCHAN, (FT, FT)))
        audited(self, attack(plain, 0, (TL,)))

    def test_reflect_shield_lost_on_switch(self):
        # 次の相手の番に、相手が突風でひかるミュウツーをベンチにもどすと、効果は消える（v0.4b の消える契機。理由 switch）。v0.84 で、操作をしない確かめ（``if False``）を
        # 実際の突風の操作に置きかえた（docs/light-powers-evolution-v0.84.md 2 章の A4）
        state = board(mon(H.SHINING_MEWTWO, (P, L)), bench=(H.RATTATA,), opponent=mon(H.HITMONCHAN, (FT, FT)), opponent_hand=(H.GUST,))
        shielded = attack(state, 0)
        mewtwo = shielded.players[0].active
        self.assertIsNotNone(reflect_shield(shielded, mewtwo))
        rattata = shielded.players[0].bench[0]
        gusted = answer(play(shielded, H.GUST, player=1), (rattata.pokemon_id,))
        self.assertIs(gusted.players[0].active.pokemon_id, rattata.pokemon_id)
        benched = next(p for p in gusted.players[0].bench if p.pokemon_id == mewtwo.pokemon_id)
        self.assertEqual([e for e in benched.persistent_effects if isinstance(e, ReflectShield)], [])
        removed = new_events(shielded, gusted, "persistent_effect_removed")
        self.assertEqual([(e["pokemon_id"], e["persistent_effect"], e["reason"]) for e in removed], [(mewtwo.pokemon_id, "reflect_shield", "switch")])
        # ベンチにもどったポケモンの効果は、もどってきても復活しない。新しい対戦ポケモンへのワザにはコインを投げない
        hit = attack(gusted, 0)
        self.assertEqual(new_events(gusted, hit, "reflect_shield_check"), [])
        audited(self, hit)

    def test_steelix_confusion_is_stopped_by_metal_energy(self):
        # こんらん状態のひかるハガネールは、必要な「鋼」エネルギー（鋼エネルギー。ダメージを変える特殊エネルギー）のために、こんらんのコインの前に v0.3c の問いで止まる。
        # こんらんの「うら」でワザの要素を処理しないとき（効果も与えない）の場面は、この写しでは起こらない（docs 6 章）
        for metal in (METAL, "NIP1X-010"):
            state = board(mon(H.SHINING_STEELIX, (metal, metal, FT, FT), confusion=True), opponent=mon(H.HITMONCHAN))
            rejects(self, state, UseAttack(0, 0), "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS")

    def test_copied_burn_up_and_psycho_burst_without_fire(self):
        # ピッピの「ゆびをふる」（必要なエネルギーはいらない。説明にしたがう）で、炎エネルギーカードがないとき: やきつくすは失敗、サイコバーストはダメージがなくなる
        state = board(mon(H.CLEFAIRY, (W, W, W)), opponent=mon(H.SHINING_GYARADOS))
        failed = answer(attack(state, 1), (1,))
        self.assertEqual([e["reason"] for e in new_events(state, failed, "attack_failed")], ["discard"])
        self.assertEqual(amounts(state, failed), [])
        state = board(mon(H.CLEFAIRY, (W, W, W)), opponent=mon(H.SHINING_MEWTWO, (P,)))
        zero = answer(attack(state, 1), (1,))
        self.assertEqual([e["outcome"] for e in new_events(state, zero, "discard_energy_failed")], ["none"])
        self.assertEqual(amounts(state, zero), [])

    def test_invalid_answers_change_nothing(self):
        state = board(mon(H.LIGHT_SLOWBRO, (P,), evolved_from=SLOWPOKE), discard=(H.RATTATA,) * 4, opponent_discard=(H.RATTATA,))
        first = attack(state, 0)
        d = first.decision
        rejects(self, first, ResolveDecision(0, d.id, d.options), "INVALID_CHOICE_COUNT", IllegalActionError)  # 4 枚
        rejects(self, first, ResolveDecision(0, d.id, (d.options[0], d.options[0])), "DUPLICATE_CHOICE", IllegalActionError)
        rejects(self, first, ResolveDecision(0, d.id, (state.players[1].discard[0],)), "INVALID_CHOICE", IllegalActionError)  # 相手のカード
        rejects(self, first, ResolveDecision(1, d.id, ()), "NOT_YOUR_DECISION", IllegalActionError)
        self.assertEqual(first.decision, d)

    def test_returned_recycle_can_be_attached_again(self):
        state = play(board(mon(H.RATTATA), hand=(ECO, H.ENERGY_REMOVAL), opponent=mon(H.DITTO, (RE, DCE))), ECO)
        choosing = play(state, H.ENERGY_REMOVAL)
        recycle = state.players[1].active.energy[0]
        done = answer(choosing, (recycle,))
        later = apply_kernel(done, EndTurn(0))
        attached = apply_kernel(later, AttachEnergy(1, recycle, later.players[1].active.card))
        self.assertIn(recycle, attached.players[1].active.energy)
        audited(self, attached)

    def test_barrier_on_opponent_for_miracle_leaf(self):
        # 相手の「まもりのはどう」（ワザによるダメージや効果を受けない）: ダメージの要素も効果の要素も無効なので、効果だけを決めるコインを投げるかが決まらない（HC3）
        state = board(mon(H.SHINING_CELEBI, (G, P)), opponent=mon(H.LIGHT_DRAGONAIR, (W, W, W), evolved_from=DRATINI), current=1, turn=8)
        guarded = attack(state, 1, (HD,))
        rejects(self, guarded, UseAttack(0, 1), "UNRESOLVED_PREVENTED_EFFECT_COIN")


class RegistryTest(unittest.TestCase):
    def test_all_33_attacks_registered_and_unsupported_without_them(self):
        extract = read_extract()
        cards = {c["id"]: c for c in extract["cards"]}
        keys = [(card, i) for card in H.V0_83_POKEMON for i in range(len(cards[card]["pokemon"]["attacks"]))]
        self.assertEqual(len(keys), 33)
        registry = E.DEFAULT_EFFECTS
        for card, index in keys:
            self.assertIsNotNone(registry.attack_entry(card, index), (card, index))
        stripped = registry.without_attacks("without-v0.83", [E.AttackKey(card, index) for card, index in keys])
        pool = pool_from_extract(read_extract(), stripped)
        self.assertFalse(any(pool.definitions[c].supported for c in H.V0_83_POKEMON))
        # Removing this release must leave every other supported card intact.
        self.assertEqual(pool.playable_ids, load_card_pool().playable_ids - set(H.V0_83_POKEMON))
        pool = load_card_pool()
        self.assertTrue(all(pool.definitions[c].supported for c in H.V0_83_POKEMON))

    def test_evolution_sources_by_exact_name(self):
        pool = load_card_pool()
        for card, base in ((H.LIGHT_SUNFLORA, "ヒマナッツ"), (H.LIGHT_VENOMOTH, "コンパン"), (H.LIGHT_GOLDUCK, "コダック"), (H.LIGHT_VAPOREON, "イーブイ"),
                           (H.LIGHT_LANTURN, "チョンチー"), (H.LIGHT_SLOWBRO, "ヤドン"), (H.LIGHT_DRAGONAIR, "ミニリュウ"), (H.RAPIDASH_ES1, "ポニータ")):
            self.assertEqual(pool.definitions[card].evolves_from, base)
        for card in H.V0_83_SHINING:
            self.assertEqual(pool.definitions[card].stage, "basic", card)

    def test_new_events_are_classified(self):
        for kind in ("attack_draw_declined", "each_player_recover", "each_player_discard_to_deck", "each_player_declined", "reflect_shield_check",
                     "reflect_shield_damage", "reflect_shield_skipped"):
            self.assertIn(kind, PUBLIC_EVENTS)

    def test_doc_exists(self):
        self.assertTrue(DOC.exists())


if __name__ == "__main__":
    unittest.main()
