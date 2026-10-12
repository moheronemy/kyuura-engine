"""v0.1 との互換性: 決まった入力で、v0.1 と同じ結果になること。

参照データ tests/fixtures/v0_1_reference.json は、v0.1（コミット 6068785）のエンジンで
scripts/make_compat_fixture.py が作ったもの。各場面について、デッキ・seed と、送ったコマンドの列
（受け付けられたか、拒否されたならエラーコード）と、最後の状態（state_to_dict の既定の形式。
山札の並び・手札・サイド・場・トラッシュ・番の進行・ダメージ・きぜつ・勝敗・イベントログを含む）を持つ。

ここでは、それを今のエンジンで再生し、
- 受け付けられたコマンドは今も受け付けられ、拒否されたコマンドは同じエラーコードで拒否される
- 最後の状態（イベントログの内容と順序を含む）が完全に同じ
ことを確かめる。テストが通ることとは別に、v0.1 の結果そのものと比べるためのテスト。
"""

import json
import unittest
from pathlib import Path

from kyuura_engine import EngineError, apply_command, command_from_dict, new_game, state_to_dict

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "v0_1_reference.json"


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
        for scenario in self.data["scenarios"]:
            with self.subTest(scenario=scenario["name"]):
                state = new_game(scenario["deck0"], scenario["deck1"], scenario["seed"])
                for number, step in enumerate(scenario["steps"]):
                    command = command_from_dict(step["command"])
                    if "error" in step:
                        with self.assertRaises(EngineError, msg=(number, step)) as ctx:
                            apply_command(state, command)
                        self.assertEqual(ctx.exception.code, step["error"], (number, step))
                    else:
                        state = apply_command(state, command)
                self.assertEqual(plain(state_to_dict(state)), scenario["final_state"])


if __name__ == "__main__":
    unittest.main()
