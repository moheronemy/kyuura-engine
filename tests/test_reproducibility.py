"""再現性と状態の独立（同じデッキ・同じ seed・同じ操作列なら同じ結果になる）。"""

import unittest

from kyuura_engine import AttachEnergy, EndTurn, apply_command, new_game, state_to_dict

from tests.helpers import FIRE, FIRE_DECK, GROWLITHE, STARYU, WATER_FIGHTING_DECK, active, build_test_state, play_until_end, replay


class ReproducibilityTest(unittest.TestCase):
    def test_same_seed_and_commands_give_same_result(self):
        state_a, commands = play_until_end(new_game(FIRE_DECK, WATER_FIGHTING_DECK, 42))
        state_b = replay(new_game(FIRE_DECK, WATER_FIGHTING_DECK, 42), commands)
        self.assertEqual(state_to_dict(state_a), state_to_dict(state_b))
        self.assertEqual(state_a.rng.getstate(), state_b.rng.getstate())
        # もう一度、手順も最初から作り直しても同じ
        state_c, commands_c = play_until_end(new_game(FIRE_DECK, WATER_FIGHTING_DECK, 42))
        self.assertEqual(commands, commands_c)
        self.assertEqual(state_to_dict(state_a), state_to_dict(state_c))

    def test_different_seed_shuffles_differently(self):
        a = new_game(FIRE_DECK, WATER_FIGHTING_DECK, 1)
        b = new_game(FIRE_DECK, WATER_FIGHTING_DECK, 2)
        self.assertNotEqual(a.players[0].deck + a.players[0].hand, b.players[0].deck + b.players[0].hand)

    def test_seed_must_be_an_integer(self):
        with self.assertRaises(TypeError):
            new_game(FIRE_DECK, WATER_FIGHTING_DECK, "42")


class IndependenceTest(unittest.TestCase):
    """ゲーム状態が予期せず共有・破壊されない。"""

    def test_new_state_shares_no_mutable_parts(self):
        state = build_test_state([{"active": GROWLITHE, "hand": [FIRE, FIRE]}, {"active": STARYU}])
        new = apply_command(state, AttachEnergy(0, state.players[0].hand[0], active(state, 0).card))
        before = state_to_dict(state)
        # 新しい状態を壊しても、元の状態は変わらない
        new.players[0].hand.clear()
        new.players[0].active.energy.append(999)
        new.players[1].deck.clear()
        new.rng.random()
        self.assertEqual(state_to_dict(state), before)
        self.assertIsNot(new.players[0], state.players[0])
        self.assertIsNot(new.rng, state.rng)

    def test_shared_read_only_parts_cannot_be_modified(self):
        state = build_test_state([{"active": GROWLITHE}, {"active": STARYU}])
        with self.assertRaises(TypeError):
            state.cards[0] = None
        with self.assertRaises(TypeError):
            state.definitions["x"] = None
        state = apply_command(state, EndTurn(0))
        with self.assertRaises(TypeError):
            state.log[-1]["kind"] = "changed"

    def test_two_games_from_the_same_decks_are_independent(self):
        deck0, deck1 = list(FIRE_DECK), list(WATER_FIGHTING_DECK)
        a = new_game(deck0, deck1, 5)
        deck0.clear()
        b = new_game(FIRE_DECK, WATER_FIGHTING_DECK, 5)
        self.assertEqual(state_to_dict(a), state_to_dict(b))


if __name__ == "__main__":
    unittest.main()
