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
参照データ（v0.1 の記録）は変えていない。
"""

import json
import unittest
from pathlib import Path

from kyuura_engine import EngineError, IllegalActionError, apply_command, command_from_dict, new_game, state_to_dict

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "v0_1_reference.json"

# v0.1 で UNSUPPORTED_ACTION だったが、その後の版で対応にしたコマンドの種類（v0.2b: トレーナー）
NOW_SUPPORTED = {"play_trainer"}


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
        # 変わったのは、ルールによる拒否のコードだけ（未対応・整合性の破れではない）
        self.assertLessEqual(changed_codes, {"WRONG_PHASE", "INVALID_PLAYER", "NOT_YOUR_TURN", "CARD_NOT_IN_HAND", "NOT_TRAINER", "GAME_OVER"})


if __name__ == "__main__":
    unittest.main()
