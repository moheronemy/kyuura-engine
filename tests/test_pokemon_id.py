"""場のポケモンの番号（pokemon_id）と、カードの uid の区別（v0.2a、M3）。

- カードの uid: 物理的なカード 1 枚の番号。対戦中に変わらない。
- 場のポケモンの番号: 場に出たときに付ける。にげる・交代でも変わらない（将来の進化でも変わらない）。
  場を離れたら無効になり、同じカードがもう一度場に出ても、前の番号は使わない。
"""

import copy
import pickle
import unittest

from kyuura_engine import (
    EndTurn, PlayBasicToBench, PromoteActive, Retreat, TakePrize, UseAttack, apply_command, check_invariants, new_game,
)

from tests.helpers import (
    FIGHTING, FIRE_DECK, GROWLITHE, HITMONCHAN, MACHOP, PONYTA, RATTATA, SEEL, STARYU, WATER_FIGHTING_DECK,
    basics_in_hand, build_test_state, find_seed, place_all, scripted_command,
)


def play_steps(state, steps):
    """決まった手順で steps 手だけ進める（途中で終われば止める）。送ったコマンドの列も返す。"""
    commands = []
    while len(commands) < steps and state.phase.value not in ("game_over", "halted", "sudden_death"):
        commands.append(scripted_command(state))
        state = apply_command(state, commands[-1])
    return state, commands


def in_play_ids(state):
    return [(pokemon.pokemon_id, pokemon.card) for p in state.players for pokemon in p.in_play()]


class AssignmentTest(unittest.TestCase):
    def test_ids_are_assigned_when_entering_play(self):
        """対戦準備でバトル場・ベンチに出した順に 1, 2, ... と付け、番の途中で出したポケモンには次の番号を付ける。"""
        seed = find_seed(FIRE_DECK, WATER_FIGHTING_DECK, lambda s: s.mulligan_rounds == () and len(basics_in_hand(s, 0)) >= 2)
        state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, seed)
        self.assertEqual(state.next_pokemon_id, 1)
        state = place_all(state, 0)
        p0 = state.players[0]
        self.assertEqual([p.pokemon_id for p in p0.in_play()], list(range(1, 1 + len(p0.in_play()))))
        first = state.next_pokemon_id
        state = place_all(state, 1)
        self.assertEqual([p.pokemon_id for p in state.players[1].in_play()], list(range(first, state.next_pokemon_id)))

    def test_play_to_bench_gets_the_next_id(self):
        state = build_test_state([{"active": GROWLITHE, "hand": [PONYTA, RATTATA]}, {"active": STARYU}])
        nxt = state.next_pokemon_id
        ponyta, rattata = state.players[0].hand
        state = apply_command(state, PlayBasicToBench(0, ponyta))
        state = apply_command(state, PlayBasicToBench(0, rattata))
        self.assertEqual([(b.card, b.pokemon_id) for b in state.players[0].bench], [(ponyta, nxt), (rattata, nxt + 1)])
        self.assertEqual(state.next_pokemon_id, nxt + 2)

    def test_ids_never_collide_in_a_full_game(self):
        """1 局を通して、場に出たポケモンの番号はすべて違う（場を離れたものも含めて）。"""
        state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, 8)
        seen = {}
        while state.phase.value != "game_over":
            for pokemon_id, card in in_play_ids(state):
                self.assertEqual(seen.setdefault(pokemon_id, card), card)  # 同じ番号はずっと同じポケモン
            state = apply_command(state, scripted_command(state))
        self.assertGreater(len(seen), 10)
        self.assertEqual(len(set(seen.values())), len(seen))  # この試合では、どのカードも場に出たのは 1 回
        self.assertEqual(max(seen), state.next_pokemon_id - 1)


class LifecycleTest(unittest.TestCase):
    def setUp(self):
        self.state = build_test_state([
            {"active": {"card": HITMONCHAN, "energy": [FIGHTING, FIGHTING, FIGHTING]}, "bench": [MACHOP]},
            {"active": PONYTA, "bench": [SEEL, GROWLITHE]},
        ])

    def test_retreat_and_promote_keep_the_id_with_the_pokemon(self):
        p0 = self.state.players[0]
        pairs = {(p.card, p.pokemon_id) for p in p0.in_play()}
        state = apply_command(self.state, Retreat(0, tuple(p0.active.energy[:2]), p0.bench[0].card))
        self.assertEqual({(p.card, p.pokemon_id) for p in state.players[0].in_play()}, pairs)
        self.assertEqual(state.players[0].active.card, self.state.players[0].bench[0].card)

    def test_id_becomes_invalid_after_leaving_play(self):
        """きぜつして場を離れたポケモンの番号は、どの場のポケモンも指さない。"""
        ponyta_id = self.state.players[1].active.pokemon_id
        state = apply_command(self.state, UseAttack(0, 1))  # スペシャルパンチ 40 で HP40 のポニータがきぜつ
        self.assertIsNone(state.find_pokemon(ponyta_id))
        state = apply_command(state, TakePrize(0, 0))
        seel = state.players[1].bench[0]
        state = apply_command(state, PromoteActive(1, seel.card))
        self.assertEqual(state.find_pokemon(seel.pokemon_id), (1, state.players[1].active))
        self.assertIsNone(state.find_pokemon(ponyta_id))

    def test_card_entering_play_again_gets_a_new_id(self):
        """同じカードが場を離れて、もう一度場に出たら、前の番号は使わない。

        v0.1 のカードには、トラッシュのポケモンを手札にもどすカードがないので、もどす部分はテストの中で
        直接行う（将来のカードの効果の代わり）。
        """
        ponyta = self.state.players[1].active
        state = apply_command(self.state, UseAttack(0, 1))
        state = apply_command(apply_command(state, TakePrize(0, 0)), PromoteActive(1, state.players[1].bench[0].card))
        self.assertIn(ponyta.card, state.players[1].discard)
        state = state.clone()
        state.players[1].discard.remove(ponyta.card)
        state.players[1].hand.append(ponyta.card)  # 将来の「トラッシュから手札にもどす」効果の代わり
        self.assertEqual(check_invariants(state), [])
        state = apply_command(state, PlayBasicToBench(1, ponyta.card))
        again = state.players[1].bench[-1]
        self.assertEqual(again.card, ponyta.card)
        self.assertNotEqual(again.pokemon_id, ponyta.pokemon_id)
        self.assertGreater(again.pokemon_id, max(p for p, _ in in_play_ids(self.state)))


class PreservationTest(unittest.TestCase):
    def test_clone_deepcopy_and_pickle_keep_ids(self):
        state, _ = play_steps(new_game(FIRE_DECK, WATER_FIGHTING_DECK, 1), 30)
        for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            self.assertEqual(in_play_ids(copied), in_play_ids(state))
            self.assertEqual(copied.next_pokemon_id, state.next_pokemon_id)
        nxt = state.clone()
        nxt.next_pokemon_id += 5
        self.assertNotEqual(nxt.next_pokemon_id, state.next_pokemon_id)

    def test_same_commands_give_same_ids(self):
        a, commands = play_steps(new_game(FIRE_DECK, WATER_FIGHTING_DECK, 2), 40)
        b = new_game(FIRE_DECK, WATER_FIGHTING_DECK, 2)
        for command in commands:
            b = apply_command(b, command)
        self.assertEqual(in_play_ids(a), in_play_ids(b))
        self.assertEqual(a.next_pokemon_id, b.next_pokemon_id)


class InvariantTest(unittest.TestCase):
    def setUp(self):
        self.state = build_test_state([{"active": GROWLITHE, "bench": [PONYTA]}, {"active": STARYU}])

    def assert_detects(self, state, fragment="場のポケモンの番号"):
        problems = check_invariants(state)
        self.assertTrue(any(fragment in p for p in problems), problems)

    def test_missing_duplicate_or_future_ids_are_detected(self):
        for mutate in (
            lambda s: setattr(s.players[0].bench[0], "pokemon_id", 0),
            lambda s: setattr(s.players[0].bench[0], "pokemon_id", s.players[0].active.pokemon_id),
            lambda s: setattr(s.players[1].active, "pokemon_id", s.next_pokemon_id),
            lambda s: setattr(s.players[1].active, "pokemon_id", True),
        ):
            state = self.state.clone()
            mutate(state)
            self.assert_detects(state)

    def test_engine_never_returns_a_state_with_broken_ids(self):
        state = self.state.clone()
        state.players[0].bench[0].pokemon_id = state.players[0].active.pokemon_id
        with self.assertRaises(Exception) as ctx:
            apply_command(state, EndTurn(0))
        self.assertEqual(ctx.exception.code, "STATE_INTEGRITY")


if __name__ == "__main__":
    unittest.main()
