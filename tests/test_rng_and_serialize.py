"""乱数の状態の複製・保存・復元と、状態の辞書の形式（v0.2a）。

- 指紋（rng_fingerprint、state_to_dict に入る）は比べるためのもので、乱数はもどせない。
- 保存・復元（rng_state_to_json / rng_from_json）は乱数の状態そのものを JSON にする。
- clone・deepcopy・pickle は乱数の状態をそのまま複製する。
"""

import copy
import json
import pickle
import random
import unittest

from kyuura_engine import apply_command, new_game, state_to_dict
from kyuura_engine.rng import copy_rng, rng_fingerprint, rng_from_json, rng_state_to_json
from kyuura_engine.serialize import FORMAT_VERSIONS

from tests.helpers import FIRE_DECK, WATER_FIGHTING_DECK, build_test_state, GROWLITHE, STARYU, play_until_end


def draws(rng, n=20):
    return [rng.random() for _ in range(n)]


class RngStateTest(unittest.TestCase):
    def setUp(self):
        self.state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, 11)

    def test_clone_deepcopy_and_pickle_continue_the_same_sequence(self):
        expected = draws(copy_rng(self.state.rng))
        for copied in (self.state.clone(), copy.deepcopy(self.state), pickle.loads(pickle.dumps(self.state))):
            self.assertIsNot(copied.rng, self.state.rng)
            self.assertEqual(draws(copied.rng), expected)
        # 複製を進めても、元は進まない
        self.assertEqual(draws(copy_rng(self.state.rng)), expected)

    def test_json_save_and_restore(self):
        data = json.loads(json.dumps(rng_state_to_json(self.state.rng)))
        restored = rng_from_json(data)
        self.assertEqual(rng_fingerprint(restored), rng_fingerprint(self.state.rng))
        self.assertEqual(draws(restored), draws(copy_rng(self.state.rng)))
        with self.assertRaises(ValueError):
            rng_from_json({**data, "format": "other"})

    def test_fingerprint_is_only_for_comparison(self):
        fingerprint = state_to_dict(self.state)["rng_state_sha256"]
        self.assertEqual(fingerprint, rng_fingerprint(self.state.rng))
        self.assertEqual(len(fingerprint), 64)
        other = copy_rng(self.state.rng)
        other.random()
        self.assertNotEqual(rng_fingerprint(other), fingerprint)

    def test_engine_does_not_use_randomness_after_setup(self):
        """コインを投げるワザのないデッキでは、対戦準備（山札を切る）のあとは乱数を使わない。

        v0.2d からコインを投げるワザ（ドードー）がある。そのデッキで乱数を使うのはコインだけ（tests/test_coin_games.py）。
        """
        fingerprint = rng_fingerprint(self.state.rng)
        end, _ = play_until_end(self.state)
        self.assertEqual(rng_fingerprint(end.rng), fingerprint)

    def test_seed_alone_determines_the_rng(self):
        self.assertEqual(rng_fingerprint(new_game(FIRE_DECK, WATER_FIGHTING_DECK, 11).rng), rng_fingerprint(self.state.rng))
        random.seed(12345)  # グローバルな乱数は関係しない
        self.assertEqual(rng_fingerprint(new_game(FIRE_DECK, WATER_FIGHTING_DECK, 11).rng), rng_fingerprint(self.state.rng))


class SameInputSameLogTest(unittest.TestCase):
    def test_same_commands_give_the_same_event_log(self):
        a, commands = play_until_end(new_game(FIRE_DECK, WATER_FIGHTING_DECK, 9))
        b = new_game(FIRE_DECK, WATER_FIGHTING_DECK, 9)
        for command in commands:
            b = apply_command(b, command)
        self.assertEqual([dict(e) for e in a.log], [dict(e) for e in b.log])
        self.assertEqual(state_to_dict(a, format_version=2), state_to_dict(b, format_version=2))


class SerializeFormatTest(unittest.TestCase):
    def test_format_2_adds_only_documented_fields(self):
        state, _ = play_until_end(new_game(FIRE_DECK, WATER_FIGHTING_DECK, 4))
        v1 = state_to_dict(state)
        v2 = state_to_dict(state, format_version=2)
        self.assertEqual(set(v2) - set(v1), {"format_version", "effects", "next_pokemon_id", "next_decision_id", "decision"})
        self.assertEqual({k: v for k, v in v2.items() if k in v1 and k != "players"}, {k: v for k, v in v1.items() if k != "players"})
        for p1, p2 in zip(v1["players"], v2["players"]):
            for a, b in zip([p1["active"], *p1["bench"]], [p2["active"], *p2["bench"]]):
                if a is not None:
                    self.assertEqual({k: v for k, v in b.items() if k != "pokemon_id"}, a)
                    self.assertGreaterEqual(b["pokemon_id"], 1)
        # 登録表の id は、登録を加えるたびに変わる（v0.2b: "kyuura-engine-0.2b"、v0.2c: プラスパワー、
        # v0.2d: ドードーの「みだれづき」、v0.2e: ディフェンダー、v0.2f: ピカチュウ、v0.3a: ビードル、
        # v0.3b: キャタピー・パラス、v0.3c: ロコン、v0.4a: パラセクト・ジュゴン、v0.4b: トランセル・コクーン、v0.4c: スピアー、
        # v0.4d: バタフリー、v0.5: フシギダネ・フシギソウ・フシギバナ（ポケモンパワーの登録を加えた）、v0.6: ゼニガメ・カメール・
        # カメックス（ポケモンパワー「あまごい」）、v0.7: ケーシィ・ユンゲラー・フーディン（ポケモンパワー「ダメージスワップ」）、v0.8: ロケット団の
        # ベトベター・ベトベトン（常にはたらくポケモンパワー「かがくへんかガス」））
        self.assertEqual((v2["format_version"], v2["effects"]), (2, "kyuura-engine-0.10"))
        json.dumps(v2)

    def test_decision_is_serialized(self):
        from tests.test_decisions import knocked_out_state

        data = state_to_dict(knocked_out_state(), format_version=2)
        self.assertEqual(data["decision"]["kind"], "take_prize")
        self.assertEqual(data["decision"]["options"], [0, 1, 2, 3, 4, 5])
        self.assertEqual(data["decision"]["context"], {"remaining": []})
        json.dumps(data)

    def test_unknown_format_is_rejected(self):
        state = build_test_state([{"active": GROWLITHE}, {"active": STARYU}])
        # 3 は v0.2b（trainer_in_use）、4 は v0.2c（ついているトレーナー）、5 は v0.3a（特殊状態）、
        # 6 は v0.3c（こんらん状態で「にげる」に失敗した記録）
        self.assertEqual(FORMAT_VERSIONS, (1, 2, 3, 4, 5, 6, 7, 8, 9))  # 7 は v0.4a、8 は v0.4b、9 は v0.6（あまごい）
        for unknown in (0, 10, "5", None):
            with self.subTest(format_version=unknown), self.assertRaises(ValueError):
                state_to_dict(state, format_version=unknown)


if __name__ == "__main__":
    unittest.main()
