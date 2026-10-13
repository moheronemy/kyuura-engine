"""v0.1 との互換性: 決まった入力で、v0.1 と同じ結果になること。

参照データ tests/fixtures/v0_1_reference.json は、v0.1（コミット 6068785）のエンジンで
scripts/make_compat_fixture.py が作ったもの。各場面について、デッキ・seed と、送ったコマンドの列
（受け付けられたか、拒否されたならエラーコード）と、最後の状態（state_to_dict の既定の形式。
山札の並び・手札・サイド・場・トラッシュ・番の進行・ダメージ・きぜつ・勝敗・イベントログを含む）を持つ。

ここでは、それを今のエンジンで再生し、
- 受け付けられたコマンドは今も受け付けられ、拒否されたコマンドは同じエラーコードで拒否される
- 最後の状態（イベントログの内容と順序を含む）が完全に同じ
ことを確かめる。テストが通ることとは別に、v0.1 の結果そのものと比べるためのテスト。

v0.1 で未対応だった操作を、その後の版で対応にしたもの（``NOW_SUPPORTED``）は、エラーコードだけが
変わる。v0.1 の参照データのデッキにはトレーナーが入っていないので、``play_trainer`` は今もすべて
拒否される（状態は変わらない）。拒否の理由が「未対応（UNSUPPORTED_ACTION）」から、ルールによる
拒否（手札にない・トレーナーでない・番でない、など）に変わる。この場合は、ルールによる拒否
（``IllegalActionError``）であることを確かめ、最後の状態の完全な一致は同じように確かめる。
v0.4a で ``evolve_pokemon`` も対応にした。参照データの 43 回の進化のコマンドは、どれもルールによる拒否に変わる
（CARD_NOT_IN_HAND 4・INVALID_PLAYER 16・NOT_YOUR_TURN 8・WRONG_PHASE 15。参照データのデッキに進化カードはない）。
v0.5 で ``use_pokemon_power`` も対応にした。参照データの 36 回の特殊能力のコマンド（どれも v0.1 の 2 つの項目 ``player``・
``pokemon`` だけの形。今も読める）は、どれもルールによる拒否に変わる（INVALID_PLAYER 15・WRONG_PHASE 12・NOT_YOUR_TURN 6・
POKEMON_NOT_IN_PLAY 3。参照データのデッキに特殊能力を持つカードはない。v0.1 のコマンドの ``pokemon`` はカードの uid の
つもりの値だが、v0.5 からは場のポケモンの番号として読むので、場にいない番号なら POKEMON_NOT_IN_PLAY）。
参照データ（v0.1 の記録）は変えていない。
"""

import json
import unittest
from pathlib import Path

from kyuura_engine import EngineError, IllegalActionError, apply_command, command_from_dict, new_game, state_to_dict

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "v0_1_reference.json"

# v0.1 で UNSUPPORTED_ACTION だったが、その後の版で対応にしたコマンドの種類（v0.2b: トレーナー、v0.4a: 進化、v0.5: 特殊能力）
NOW_SUPPORTED = {"play_trainer", "evolve_pokemon", "use_pokemon_power"}


def plain(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


class V01CompatibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_was_made_with_v0_1(self):
        self.assertTrue(self.data["generated_at_commit"].startswith("6068785"))
        self.assertGreaterEqual(len(self.data["scenarios"]), 15)

    def test_replay_gives_the_same_results_as_v0_1(self):
        changed_codes = set()
        for scenario in self.data["scenarios"]:
            with self.subTest(scenario=scenario["name"]):
                state = new_game(scenario["deck0"], scenario["deck1"], scenario["seed"])
                for number, step in enumerate(scenario["steps"]):
                    command = command_from_dict(step["command"])
                    if "error" in step:
                        with self.assertRaises(EngineError, msg=(number, step)) as ctx:
                            apply_command(state, command)
                        if step["command"]["type"] in NOW_SUPPORTED and step["error"] == "UNSUPPORTED_ACTION":
                            self.assertIsInstance(ctx.exception, IllegalActionError, (number, step))
                            changed_codes.add(ctx.exception.code)
                        else:
                            self.assertEqual(ctx.exception.code, step["error"], (number, step))
                    else:
                        state = apply_command(state, command)
                self.assertEqual(plain(state_to_dict(state)), scenario["final_state"])
        # 変わったのは、ルールによる拒否のコードだけ（未対応・整合性の破れではない）。POKEMON_NOT_IN_PLAY は v0.5 の特殊能力
        self.assertLessEqual(changed_codes, {"WRONG_PHASE", "INVALID_PLAYER", "NOT_YOUR_TURN", "CARD_NOT_IN_HAND", "NOT_TRAINER", "GAME_OVER",
                                             "POKEMON_NOT_IN_PLAY"})

    def test_v0_1_pokemon_power_commands_are_rejected_by_rules(self):
        """v0.1 の 2 つの項目の ``use_pokemon_power``（36 回）は今も読め、v0.5 ではどれもルールによる拒否（docstring の内訳）。"""
        from collections import Counter

        codes = Counter()
        for scenario in self.data["scenarios"]:
            state = new_game(scenario["deck0"], scenario["deck1"], scenario["seed"])
            for step in scenario["steps"]:
                command = command_from_dict(step["command"])
                if "error" not in step:
                    state = apply_command(state, command)
                    continue
                if step["command"]["type"] != "use_pokemon_power":
                    continue
                self.assertEqual(set(step["command"]), {"type", "player", "pokemon"})  # v0.1 の形
                self.assertEqual(step["error"], "UNSUPPORTED_ACTION")
                with self.assertRaises(IllegalActionError) as ctx:
                    apply_command(state, command)
                codes[ctx.exception.code] += 1
        self.assertEqual(codes, {"INVALID_PLAYER": 15, "WRONG_PHASE": 12, "NOT_YOUR_TURN": 6, "POKEMON_NOT_IN_PLAY": 3})


if __name__ == "__main__":
    unittest.main()
