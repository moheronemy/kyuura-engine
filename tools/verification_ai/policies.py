"""戦略（C）。V0 は均等の選び方 1 つだけ（docs/verification-ai-v0.md 3 章）。

方策は、行動生成・ランナーが渡した選べるもの（JSON の値の並び）の中から 1 つの位置を選び、理由のコードを返すだけです。合法性を判定せず、
``kyuura_engine`` を import しません。``context`` は本人向けの JSON の値だけ（観測・API の応答）で、均等の方策は読みません（ルールの方策は V2）。

乱数は方策ごとの ``random.Random``（種は文字列。Python の文字列の種は実行ごとに同じ値になる）で、エンジンの乱数を使いません。
"""

from __future__ import annotations

import random
from typing import Any

POLICY_NAME = "uniform"
POLICY_VERSION = 1
# 分布の名前（仕様 3.1 節）。候補を均等に選び、各段で前の段の選び方のもとで契約が許す選べるものを均等に選ぶ。完成した入力の組の均等（uniform-tuple）・
# 全候補の操作の均等（uniform-action）ではない
DISTRIBUTION = "uniform-candidate+uniform-stage"
STAGE = DISTRIBUTION
# V1: 候補は均等に選び、その候補の中で、契約の上で作れる完成した入力の組（上限 4,096）を均等に選ぶ。全候補を通した操作の均等ではない。上限を超えた候補は STAGE に戻す
TUPLE = "uniform-candidate+uniform-tuple"
DISTRIBUTIONS = (STAGE, TUPLE)


class UniformPolicy:
    """渡された並びの位置を均等に選ぶ。``draws`` は乱数を使った回数（記録用）。"""

    name = POLICY_NAME
    version = POLICY_VERSION

    def __init__(self, seed: str, distribution: str = STAGE):
        if distribution not in DISTRIBUTIONS:
            raise ValueError(f"知らない分布 {distribution!r}")
        self.distribution = distribution  # 行動生成がどちらの組み立て方を使うか（選ぶ処理は同じ: 渡された並びの位置を均等に選ぶ）
        self.seed = seed
        self._rng = random.Random(seed)
        self.draws = 0

    def choose(self, purpose: str, items: list[Any], context: dict[str, Any]) -> tuple[int, str]:
        """``items`` の位置を 1 つ選ぶ（``items`` は空でない）。``purpose`` は場面の名前（記録用）。"""
        if not items:
            raise ValueError("選べるものがない場面で方策を呼んだ（行動生成の誤り）")
        self.draws += 1
        return self._rng.randrange(len(items)), f"uniform:{purpose}"


def player_seed(policy_seed: int, player: int) -> str:
    """プレイヤーごとの方策の種。"""
    return f"kyuura-vai-v0:player:{policy_seed}:{player}"


def host_seed(seed: int) -> str:
    """ホストの係（ジャンケンの勝者）の種。プレイヤーの方策とは別の乱数。"""
    return f"kyuura-vai-v0:host:{seed}"
