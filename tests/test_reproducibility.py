"""再現性と状態の独立（同じデッキ・同じ seed・同じ操作列なら同じ結果になる）。"""

import hashlib
import json
import random
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

    def test_negative_seed_is_rejected(self):
        """random.Random は負の seed を絶対値として扱うので、-5 と 5 が同じ対戦になってしまう。受け付けない。"""
        with self.assertRaises(ValueError):
            new_game(FIRE_DECK, WATER_FIGHTING_DECK, -5)

    def test_serialized_state_includes_rng_state(self):
        """state_to_dict が同じなら、乱数の状態も同じ（今後のコイン・山札を切る処理の結果が同じ）であること。"""
        a = new_game(FIRE_DECK, WATER_FIGHTING_DECK, 1)
        b = a.clone()
        b.rng.random()
        self.assertNotEqual(state_to_dict(a), state_to_dict(b))


class GoldenValueTest(unittest.TestCase):
    """乱数の結果を固定値と比べる（Python 3.11・3.12・3.13 で同じ値になることを確かめた）。

    ここが失敗したら、同じ seed・同じ操作列で以前と違う対戦になっている。記録した対戦を再生できなく
    なるので、乱数の使い方・カードの番号の付け方・状態の形を意図して変えたのでない限り、エンジンの不具合。
    意図した変更なら、値を更新し、その理由をコミットに書く。
    """

    def test_opening_deal_for_a_fixed_seed(self):
        state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, 12345)
        self.assertEqual(state.players[0].hand, [37, 18, 53, 45, 8, 3, 15])
        self.assertEqual(state.players[1].hand, [118, 96, 64, 114, 77, 116, 88])
        self.assertEqual(state.players[0].deck[:5], [49, 21, 34, 1, 30])
        self.assertEqual(state.players[1].deck[:5], [86, 78, 105, 106, 100])

    def test_scripted_game_for_a_fixed_seed(self):
        state, commands = play_until_end(new_game(FIRE_DECK, WATER_FIGHTING_DECK, 42))
        self.assertEqual((len(commands), state.result.winner, state.turn_number), (37, 1, 12))
        self.assertEqual(state.result.conditions, ((1, "OPPONENT_CANNOT_FIELD_ACTIVE"),))
        text = json.dumps(state_to_dict(state), sort_keys=True, ensure_ascii=False)
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), "83f9ccbfc48be56325d17b6b33debedd781d41f2647f7eacee5fca8190355bf3")


class GlobalRandomTest(unittest.TestCase):
    """エンジンはモジュールの random（グローバルな乱数）を使わない。"""

    def test_global_random_is_neither_used_nor_consulted(self):
        results = []
        for global_seed in (1, 2):
            random.seed(global_seed)
            before = random.getstate()
            state, _ = play_until_end(new_game(FIRE_DECK, WATER_FIGHTING_DECK, 3))
            self.assertEqual(random.getstate(), before)
            results.append(state_to_dict(state))
        self.assertEqual(results[0], results[1])


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
        self.assertEqual((deck0, deck1), (FIRE_DECK, WATER_FIGHTING_DECK))  # new_game は渡したリストを変えない
        deck0.clear()
        b = new_game(FIRE_DECK, WATER_FIGHTING_DECK, 5)
        self.assertEqual(state_to_dict(a), state_to_dict(b))


if __name__ == "__main__":
    unittest.main()
