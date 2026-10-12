"""対戦準備（『オフィシャルブック2000』p.308「対戦スタート」、kyuura NEO-2000-OFFICIAL-RULES）。

kyuura の記録 id: setup_bench・prizes・first_player・mulligan（data/rule_differences.json の「2000年2月」の行）。
"""

import unittest

from kyuura_engine import (
    DrawMulliganCards, IllegalActionError, Phase, PlaceStartingPokemon, ReportJankenResult, UnsupportedError,
    apply_command, check_invariants, expand_decklist, new_game, state_to_dict,
)

from tests.helpers import (
    DIGLETT, DRATINI, FIGHTING, FIRE, FIRE_DECK, GROWLITHE, HITMONCHAN, MACHOP, PONYTA, RATTATA, SEEL, STARYU,
    VOLTORB, WATER, WATER_FIGHTING_DECK, basics_in_hand, energy_in_hand, find_seed, finish_setup, place_all,
)

# たねポケモン 40 枚（10 種 × 4）+ エネルギー 20 枚。手札がたねポケモンだけになる seed を探すのに使う
MANY_BASICS = expand_decklist({p: 4 for p in (PONYTA, GROWLITHE, STARYU, SEEL, VOLTORB, DIGLETT, MACHOP, HITMONCHAN, RATTATA, DRATINI)} | {FIRE: 20})
# たねポケモンが少ないデッキ（切り直しが起こりやすい）
ONE_BASIC = expand_decklist({MACHOP: 1, FIGHTING: 59})
FEW_BASICS = expand_decklist({SEEL: 4, WATER: 56})


def no_mulligan(state):
    return state.mulligan_rounds == ()


class OpeningHandTest(unittest.TestCase):
    def test_opening_hand_is_seven(self):
        """山札の一番上からカードを7枚取り、手札とする（p.308）。"""
        seed = find_seed(FIRE_DECK, WATER_FIGHTING_DECK, no_mulligan)
        state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, seed)
        self.assertEqual(state.phase, Phase.SETUP_PLACEMENT)
        for p in state.players:
            self.assertEqual(len(p.hand), 7)
            self.assertEqual(len(p.deck), 53)
        self.assertEqual(check_invariants(state), [])

    def test_hand_keeps_basic_pokemon(self):
        """切り直しは、手札にたねポケモンが来るまでくりかえす（p.308）。"""
        for seed in range(20):
            state = new_game(ONE_BASIC, FIRE_DECK, seed)
            if state.phase is Phase.HALTED:
                continue
            for player in (0, 1):
                self.assertTrue(basics_in_hand(state, player))


class PlacementTest(unittest.TestCase):
    """バトル場に1枚、ベンチに最大5枚まで（p.308、kyuura setup_bench）。"""

    def setUp(self):
        self.seed = find_seed(MANY_BASICS, FIRE_DECK, lambda s: no_mulligan(s) and len(basics_in_hand(s, 0)) == 7)
        self.state = new_game(MANY_BASICS, FIRE_DECK, self.seed)

    def test_bench_up_to_five_at_setup(self):
        basics = basics_in_hand(self.state, 0)
        state = apply_command(self.state, PlaceStartingPokemon(0, basics[0], tuple(basics[1:6])))
        self.assertEqual(len(state.players[0].bench), 5)
        self.assertEqual(state.players[0].active.card, basics[0])
        self.assertEqual(len(state.players[0].hand), 1)

    def test_six_on_bench_at_setup_is_rejected(self):
        basics = basics_in_hand(self.state, 0)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(self.state, PlaceStartingPokemon(0, basics[0], tuple(basics[1:7])))
        self.assertEqual(ctx.exception.code, "SETUP_BENCH_LIMIT")

    def test_bench_is_optional(self):
        """かならずしもベンチに出す必要はない（p.308）。"""
        basics = basics_in_hand(self.state, 0)
        state = apply_command(self.state, PlaceStartingPokemon(0, basics[0]))
        self.assertEqual(state.players[0].bench, [])

    def test_only_basic_pokemon_from_hand(self):
        seed = find_seed(FIRE_DECK, WATER_FIGHTING_DECK, lambda s: no_mulligan(s) and energy_in_hand(s, 0))
        state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, seed)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, PlaceStartingPokemon(0, energy_in_hand(state, 0)[0]))
        self.assertEqual(ctx.exception.code, "NOT_BASIC_POKEMON")
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, PlaceStartingPokemon(0, state.players[0].deck[0]))
        self.assertEqual(ctx.exception.code, "CARD_NOT_IN_HAND")

    def test_cannot_place_twice(self):
        state = place_all(self.state, 0)
        with self.assertRaises(IllegalActionError) as ctx:
            place_all(state, 0)
        self.assertEqual(ctx.exception.code, "ALREADY_PLACED")


class PrizeAndFirstPlayerTest(unittest.TestCase):
    def setUp(self):
        seed = find_seed(FIRE_DECK, WATER_FIGHTING_DECK, no_mulligan)
        self.state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, seed)

    def test_six_prizes_from_top_of_deck_after_both_placed(self):
        """サイドは山札の一番上から6枚。両方がポケモンを出した後に置く（p.308、kyuura prizes）。"""
        state = place_all(self.state, 0)
        self.assertEqual(state.players[0].prizes, [])
        top6 = [list(p.deck[:6]) for p in state.players]
        state = place_all(state, 1)
        for player in (0, 1):
            self.assertEqual(state.players[player].prizes, top6[player])
            self.assertEqual(len(state.players[player].deck), 47)
        self.assertEqual(state.phase, Phase.SETUP_FIRST_PLAYER)

    def test_janken_winner_goes_first(self):
        """ジャンケンをして、勝った人が先攻、負けた人が後攻（p.308、kyuura first_player）。"""
        for winner in (0, 1):
            state = finish_setup(self.state, janken_winner=winner)
            self.assertEqual(state.first_player, winner)
            self.assertEqual(state.current_player, winner)
            self.assertEqual(state.turn_number, 1)
            self.assertEqual(state.phase, Phase.MAIN)

    def test_janken_before_placement_is_rejected(self):
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(self.state, ReportJankenResult(0))
        self.assertEqual(ctx.exception.code, "WRONG_PHASE")


class MulliganTest(unittest.TestCase):
    """たねポケモンがない場合の切り直し（p.308、kyuura mulligan）。"""

    def test_opponent_may_draw_up_to_two_per_mulligan_after_prizes(self):
        seed = find_seed(ONE_BASIC, FIRE_DECK, lambda s: s.players[0].mulligans >= 2 and s.players[1].mulligans == 0)
        state = new_game(ONE_BASIC, FIRE_DECK, seed)
        mulligans = state.players[0].mulligans
        self.assertTrue(all(r == (0,) for r in state.mulligan_rounds))
        self.assertEqual(state.players[1].mulligan_draws_remaining, mulligans)
        self.assertEqual(state.players[0].mulligan_draws_remaining, 0)
        revealed = [e for e in state.log if e["kind"] == "mulligan"]
        self.assertEqual(len(revealed), mulligans)
        for event in revealed:  # 見せた手札にたねポケモンがない
            self.assertFalse(any(state.card_def(u).is_basic_pokemon for u in event["revealed_hand"]))

        # 引くのはサイドをセットした後（p.308）
        with self.assertRaises(IllegalActionError):
            apply_command(state, DrawMulliganCards(1, 2))
        state = place_all(place_all(state, 0), 1)
        self.assertEqual(state.phase, Phase.SETUP_MULLIGAN_DRAW)
        self.assertEqual(len(state.players[1].prizes), 6)

        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, DrawMulliganCards(1, 3))
        self.assertEqual(ctx.exception.code, "INVALID_DRAW_COUNT")
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, DrawMulliganCards(0, 1))
        self.assertEqual(ctx.exception.code, "NO_MULLIGAN_DRAW")

        hand = len(state.players[1].hand)
        counts = [2, 0, 1] + [2] * mulligans  # 2 枚・引かない・1 枚もよい
        drawn = 0
        for count in counts[:mulligans]:
            state = apply_command(state, DrawMulliganCards(1, count))
            drawn += count
        self.assertEqual(len(state.players[1].hand), hand + drawn)
        self.assertEqual(state.phase, Phase.SETUP_FIRST_PLAYER)
        self.assertEqual(check_invariants(state), [])

    def test_no_draw_when_both_players_had_no_basic(self):
        """両方のプレイヤーともたねポケモンがなかった場合は、どちらも引かない（p.308）。"""
        seed = find_seed(FEW_BASICS, FEW_BASICS, lambda s: s.mulligan_rounds == ((0, 1),))
        state = new_game(FEW_BASICS, FEW_BASICS, seed)
        self.assertEqual([p.mulligans for p in state.players], [1, 1])
        self.assertEqual([p.mulligan_draws_remaining for p in state.players], [0, 0])
        state = place_all(place_all(state, 0), 1)
        self.assertEqual(state.phase, Phase.SETUP_FIRST_PLAYER)

    def test_unequal_mulligans_after_both_mulliganed_is_halted(self):
        """両方が切り直したあと、片方だけがさらに切り直した場合の枚数は原文から決められない。

        推測で処理せず、対戦を止めて UnsupportedError を返す（kyuura docs/engine-readiness.md 4章）。
        """
        seed = find_seed(FEW_BASICS, FEW_BASICS, lambda s: len(s.mulligan_rounds) >= 2 and s.mulligan_rounds[0] == (0, 1) and len(s.mulligan_rounds[-1]) == 1)
        state = new_game(FEW_BASICS, FEW_BASICS, seed)
        self.assertEqual(state.phase, Phase.HALTED)
        self.assertEqual(state.halt.code, "UNRESOLVED_MULLIGAN_COMPENSATION")
        before = state_to_dict(state)
        with self.assertRaises(UnsupportedError) as ctx:
            place_all(state, 0)
        self.assertEqual(ctx.exception.code, "UNRESOLVED_MULLIGAN_COMPENSATION")
        self.assertEqual(state_to_dict(state), before)


if __name__ == "__main__":
    unittest.main()
