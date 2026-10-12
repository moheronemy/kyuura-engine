"""勝ち負けの判定表（『オフィシャルブック2000』p.311 の表、kyuura sudden_death）。

表の 9 行を画像で読んで、そのまま写したもの。列は
「あなたがサイドカードをすべて取った」「相手がサイドカードをすべて取った」
「あなたの対戦ポケモンが出せない」「相手の対戦ポケモンが出せない」。あなた = プレイヤー 0。
"""

import unittest

from kyuura_engine.judge import decide, deck_out

YOU, OPPONENT = 0, 1

TABLE_P311 = [
    # (あなたがサイドを取った, 相手がサイドを取った, あなたが出せない, 相手が出せない, 結果)
    (True, False, True, False, "サドン・デス"),
    (False, True, False, True, "サドン・デス"),
    (True, True, True, True, "サドン・デス"),
    (True, True, False, True, "あなたの勝ち"),
    (True, False, True, True, "あなたの勝ち"),
    (True, False, False, True, "あなたの勝ち"),
    (True, True, True, False, "あなたの負け"),
    (False, True, True, True, "あなたの負け"),
    (False, True, True, False, "あなたの負け"),
]


class JudgeTableTest(unittest.TestCase):
    def test_every_row_of_the_table(self):
        for you_prizes, opp_prizes, you_cannot, opp_cannot, expected in TABLE_P311:
            with self.subTest(row=(you_prizes, opp_prizes, you_cannot, opp_cannot)):
                result = decide([you_prizes, opp_prizes], [you_cannot, opp_cannot])
                if expected == "サドン・デス":
                    self.assertEqual((result.outcome, result.winner), ("sudden_death", None))
                elif expected == "あなたの勝ち":
                    self.assertEqual((result.outcome, result.winner), ("win", YOU))
                else:
                    self.assertEqual((result.outcome, result.winner), ("win", OPPONENT))

    def test_single_conditions(self):
        self.assertEqual(decide([True, False], [False, False]).winner, YOU)
        self.assertEqual(decide([False, False], [True, False]).winner, OPPONENT)

    def test_no_condition(self):
        self.assertIsNone(decide([False, False], [False, False]))

    def test_deck_out(self):
        result = deck_out(loser=1)
        self.assertEqual((result.outcome, result.winner), ("win", 0))


if __name__ == "__main__":
    unittest.main()
