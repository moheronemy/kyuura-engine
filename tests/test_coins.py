"""コイントスの基本（v0.2d。kyuura_engine/coins.py）。

根拠: 『ポケモンカードオフィシャルブック2000』p.319「5 コイントス」（コインを投げて「おもて」か「うら」かを
判定する。コインは何でもよい）。kyuura の記録 NEO-2000-OFFICIAL-RULES。

- 結果は対戦の乱数 ``GameState.rng`` だけで決まる（1 枚につき ``getrandbits(1)`` を 1 回。1 なら「おもて」）
- 何枚でも 1 枚ずつ、投げた順に乱数を使う。余分に乱数を使わない
- 枚数・プレイヤーが正しくなければ、乱数を使う前に ValueError（効果の実装の誤り）
- 1 枚ごとに ``coin_flip`` をログに残す
"""

import copy
import json
import pickle
import random
import unittest

from kyuura_engine import CoinSide, new_game, state_to_dict
from kyuura_engine.coins import CoinFlips, flip_coins
from kyuura_engine.rng import copy_rng, rng_fingerprint, rng_from_json, rng_state_to_json

from tests.helpers import (
    DODUO_DECK, GROWLITHE, H, STARYU, T, WATER_FIGHTING_DECK, build_test_state, coin_events, rng_for_coins,
    with_coin_results,
)


def board(seed=0):
    return build_test_state([{"active": GROWLITHE}, {"active": STARYU}], seed=seed)


def flip(state, count, player=0):
    return flip_coins(state, player, count, source="test", effect="TEST#0", card=0, pokemon_id=1)


def letters(flips):
    return "".join("H" if side is CoinSide.HEADS else "T" for side in flips.results)


class CoinSideTest(unittest.TestCase):
    def test_heads_and_tails(self):
        self.assertEqual((CoinSide.HEADS.value, CoinSide.TAILS.value), ("heads", "tails"))
        flips = CoinFlips((H, T, H))
        self.assertEqual((flips.heads, flips.tails), (2, 1))
        self.assertEqual((CoinFlips(()).heads, CoinFlips(()).tails), (0, 0))

    def test_one_bit_per_coin_and_1_is_heads(self):
        """コイン 1 枚 = getrandbits(1) 1 回。1 なら「おもて」、0 なら「うら」。"""
        for seed in range(20):
            state = board(seed)
            expected = copy_rng(state.rng)
            bits = [expected.getrandbits(1) for _ in range(5)]
            flips = flip(state, 5)
            self.assertEqual([side is CoinSide.HEADS for side in flips.results], [b == 1 for b in bits])
            # 余分に乱数を使わない（5 枚なら 5 回だけ）
            self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected))


class FlipCountTest(unittest.TestCase):
    def test_one_coin(self):
        for side in (H, T):
            state = with_coin_results(board(), side)
            flips = flip(state, 1)
            self.assertEqual(flips.results, (side,))
            self.assertEqual(flips.heads, 1 if side is H else 0)

    def test_two_coins_all_combinations(self):
        for sides in ((T, T), (H, T), (T, H), (H, H)):
            state = with_coin_results(board(), *sides)
            flips = flip(state, 2)
            self.assertEqual(flips.results, sides)  # 投げた順
            self.assertEqual((flips.heads, flips.tails), (sides.count(H), sides.count(T)))

    def test_many_coins_in_order(self):
        sides = (H, T, T, H, H, T, H, T, T, T)
        state = with_coin_results(board(), *sides)
        flips = flip(state, len(sides))
        self.assertEqual(flips.results, sides)
        self.assertEqual((flips.heads, flips.tails), (4, 6))

    def test_invalid_count_is_an_implementation_error_and_uses_no_randomness(self):
        """枚数の誤りは効果の実装の誤り（ValueError）。乱数を使わず、ログも残さない。"""
        for count in (0, -1, 1.5, True, "2", None):
            state = board()
            before = (rng_fingerprint(state.rng), len(state.log))
            with self.assertRaises(ValueError, msg=repr(count)):
                flip(state, count)
            self.assertEqual((rng_fingerprint(state.rng), len(state.log)), before)

    def test_invalid_player_uses_no_randomness(self):
        for player in (2, -1, None, "0"):
            state = board()
            before = rng_fingerprint(state.rng)
            with self.assertRaises(ValueError):
                flip(state, 1, player=player)
            self.assertEqual(rng_fingerprint(state.rng), before)


class CoinLogTest(unittest.TestCase):
    def test_one_event_per_coin(self):
        state = with_coin_results(board(), H, T)
        start = len(state.log)
        flip_coins(state, 1, 2, source="attack", effect="PMCG1-061#0", card=5, pokemon_id=3)
        self.assertEqual(coin_events(state, start), [
            {"kind": "coin_flip", "turn": 3, "player": 1, "source": "attack", "effect": "PMCG1-061#0", "card": 5,
             "pokemon_id": 3, "number": 1, "count": 2, "result": "heads"},
            {"kind": "coin_flip", "turn": 3, "player": 1, "source": "attack", "effect": "PMCG1-061#0", "card": 5,
             "pokemon_id": 3, "number": 2, "count": 2, "result": "tails"},
        ])
        # ログは JSON にできる（どの形式でも同じ）
        json.dumps(state_to_dict(state))


class GoldenCoinTest(unittest.TestCase):
    """コインの結果を固定値と比べる（Python 3.11・3.12・3.13 で同じ値になることを確かめた。v0.2d）。

    ここが失敗したら、同じ seed で以前と違うコインになっている（記録した対戦を再生できない）。
    乱数の使い方を意図して変えたのでない限り、エンジンの不具合。
    """

    def test_bits_of_the_python_mt19937(self):
        rng = random.Random(0)
        self.assertEqual("".join(str(rng.getrandbits(1)) for _ in range(32)), "10110001100111010011101000101101")

    def test_coins_after_a_formal_start(self):
        """new_game（60 枚、山札を切る）のあとの乱数で投げるコイン。"""
        state = new_game(DODUO_DECK, WATER_FIGHTING_DECK, 12345)
        self.assertEqual(letters(flip(state, 16)), "THHTTTTTTTHTHHTT")

    def test_coins_from_a_seed(self):
        self.assertEqual(letters(flip(board(seed=7), 10, player=1)), "THTTHTTHHT")


class CoinRngTest(unittest.TestCase):
    """コインの乱数の複製・保存・復元（kyuura_engine/rng.py）。"""

    def setUp(self):
        self.state = new_game(DODUO_DECK, WATER_FIGHTING_DECK, 3)
        self.expected = letters(flip(self.state.clone(), 12))

    def test_clone_deepcopy_and_pickle_flip_the_same_coins(self):
        for copied in (self.state.clone(), copy.deepcopy(self.state), pickle.loads(pickle.dumps(self.state))):
            self.assertEqual(letters(flip(copied, 12)), self.expected)
        self.assertEqual(letters(flip(self.state.clone(), 12)), self.expected)  # 複製で投げても、元は進まない

    def test_json_restore_continues_the_same_coins(self):
        """乱数の状態だけを JSON で保存・復元できる（ゲーム状態全体の JSON からの読み込みは未実装）。"""
        saved = json.loads(json.dumps(rng_state_to_json(self.state.rng)))
        restored = self.state.clone()
        restored.rng = rng_from_json(saved)
        self.assertEqual(letters(flip(restored, 12)), self.expected)

    def test_save_in_the_middle_and_continue(self):
        """6 枚投げたところで保存し、もどしてから残りの 6 枚を投げると、続けて 12 枚投げたのと同じ。"""
        state = self.state.clone()
        first = letters(flip(state, 6))
        saved = json.dumps(rng_state_to_json(state.rng))
        resumed = state.clone()
        resumed.rng = rng_from_json(json.loads(saved))
        self.assertEqual(first + letters(flip(resumed, 6)), self.expected)

    def test_two_games_do_not_share_the_rng(self):
        a = new_game(DODUO_DECK, WATER_FIGHTING_DECK, 3)
        b = new_game(DODUO_DECK, WATER_FIGHTING_DECK, 3)
        self.assertIsNot(a.rng, b.rng)
        flip(a, 30)
        self.assertEqual(letters(flip(b, 12)), self.expected)

    def test_global_random_is_not_used(self):
        results = []
        for global_seed in (1, 2):
            random.seed(global_seed)
            before = random.getstate()
            state = new_game(DODUO_DECK, WATER_FIGHTING_DECK, 3)
            results.append(letters(flip(state, 12)))
            self.assertEqual(random.getstate(), before)
        self.assertEqual(results, [self.expected, self.expected])

    def test_rng_for_coins_is_test_only(self):
        """テスト専用の結果の指定は、状態の乱数を差し替えるだけ（エンジンに結果を指定する API はない）。"""
        rng = rng_for_coins(H, H, T, T)
        self.assertEqual([rng.getrandbits(1) for _ in range(4)], [1, 1, 0, 0])
        import kyuura_engine
        from kyuura_engine import commands

        self.assertFalse(any("coin" in name.lower() for name in kyuura_engine.__all__ if name != "CoinSide"))
        self.assertFalse(any("coin" in name.lower() for name in dir(commands)))


if __name__ == "__main__":
    unittest.main()
