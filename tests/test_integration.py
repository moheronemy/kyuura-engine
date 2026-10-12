"""統合テスト: 正式な対戦開始（new_game、60 枚のデッキ、サイド 6 枚）から勝敗が決まるまで進める。

操作は tests/helpers.py の scripted_command（決まった手順。AI ではない）。各手の後に
check_invariants で、カードの重複・紛失、HP 以上のダメージで場に残るポケモンなどがないことを確かめる。
"""

import unittest
from collections import Counter

from kyuura_engine import Phase, check_invariants, new_game

from tests.helpers import FIRE_DECK, WATER_FIGHTING_DECK, play_until_end

SEEDS = range(10)


class FullGameTest(unittest.TestCase):
    def assert_consistent(self, state):
        self.assertEqual(check_invariants(state), [])
        for player in (0, 1):
            self.assertEqual(sum(1 for c in state.cards.values() if c.owner == player), 60)

    def test_games_finish_with_a_winner(self):
        for seed in SEEDS:
            with self.subTest(seed=seed):
                start = new_game(FIRE_DECK, WATER_FIGHTING_DECK, seed)
                state, commands = play_until_end(start, check=self.assert_consistent, janken_winner=seed % 2)
                self.assertEqual(state.phase, Phase.GAME_OVER, state.halt)
                self.assertIn(state.result.winner, (0, 1))
                kinds = Counter(e["kind"] for e in state.log)
                self.assertGreater(kinds["attack"], 0)
                self.assertGreater(kinds["knock_out"], 0)
                self.assertEqual(kinds["game_end"], 1)
                self.assertEqual(state.first_player, seed % 2)

    def test_game_won_by_taking_all_prizes(self):
        """6 匹きぜつさせてサイドを取り終えて勝つ試合（ベンチを使う手順）。"""
        found = False
        for seed in SEEDS:
            state, _ = play_until_end(new_game(FIRE_DECK, WATER_FIGHTING_DECK, seed))
            if state.result and ("ALL_PRIZES_TAKEN" in {c for _, c in state.result.conditions}):
                found = True
                winner = state.result.winner
                self.assertEqual(state.players[winner].prizes, [])
                self.assertEqual(sum(1 for e in state.log if e["kind"] == "knock_out" and e["player"] != winner), 6)
                break
        self.assertTrue(found)

    def test_game_lost_by_having_no_pokemon_to_promote(self):
        """ベンチに出さない手順では、最初のきぜつで「バトル場に出せるポケモンがいない」になる。"""
        state, _ = play_until_end(new_game(FIRE_DECK, WATER_FIGHTING_DECK, 0), bench=False, check=self.assert_consistent)
        self.assertEqual(state.phase, Phase.GAME_OVER)
        self.assertEqual(state.result.conditions, ((state.result.winner, "OPPONENT_CANNOT_FIELD_ACTIVE"),))
        loser = 1 - state.result.winner
        self.assertIsNone(state.players[loser].active)
        self.assertEqual(state.players[loser].bench, [])

    def test_game_lost_by_deck_out(self):
        """ワザを使わない手順では、山札が先になくなったプレイヤーが番の最初に負ける。"""
        state, _ = play_until_end(new_game(FIRE_DECK, WATER_FIGHTING_DECK, 3), attack=False, janken_winner=0, check=self.assert_consistent)
        self.assertEqual(state.phase, Phase.GAME_OVER)
        self.assertEqual(state.result.conditions, ((1, "OPPONENT_DECK_EMPTY"),))
        self.assertEqual(state.players[0].deck, [])
        # 先攻（プレイヤー 0）が引けなくなるのは、山札 47 枚を 47 回の自分の番で引き終えた次の番
        self.assertEqual(sum(1 for e in state.log if e["kind"] == "turn_start" and e["player"] == 0), 48)


if __name__ == "__main__":
    unittest.main()
