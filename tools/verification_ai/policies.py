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

    def begin_episode(self) -> dict[str, Any]:
        """選択のエピソードの始め（V2）。均等の方策は乱数を使わない（V0・V1 の選び方を変えない）。"""
        return {"mode": "random"}

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


# ---------------------------------------------------------------- V2: ルールの方策と混合の方策（docs/verification-ai-v2.md 2 章・3 章）
#
# どちらも候補の「種類」（API の応答の kind）だけで順位をつける。カード名・カード ID・効果の型・入力の中身は読まない。入力（段の選択）は uniform-stage のまま。
# 合法性は判定しない（範囲・入力の組み立て・check・submit はランナーと行動生成とエンジン）

RULES_NAME = "rules"
RULES_VERSION = 1
RULES_DISTRIBUTION = "rules-v1-candidate+uniform-stage"  # 候補は優先順位（同順位は均等）、入力は段ごとの均等（STAGE と同じ手順）
MIXED_NAME = "mixed"
MIXED_VERSION = 1
MIXED_DISTRIBUTION = "mixed(rules-v1|uniform-candidate)+uniform-stage"
# 番の操作の優先順位（小さいほど先）。表にない種類（準備・ホスト・決定の回答）だけの場面は優先順位を当てはめず、均等に選ぶ（理由 rule:fallback）
PRIORITY = {"play_basic": 1, "evolve": 2, "attach_energy": 3, "use_attack": 4,
            "play_trainer": 5, "use_power": 5, "use_stadium": 5, "retreat": 5, "remove_disguise": 5, "discard_from_play": 5, "reveal_face_down": 5,
            "check_face_up_deck": 5, "end_turn": 6}


class RulePolicy(UniformPolicy):
    """rules-v1: 候補の選択だけに優先順位を使う。同じ順位の候補が 2 つ以上なら、方策の乱数（UniformPolicy と同じ種の導き方）で均等に選ぶ。"""

    name = RULES_NAME
    version = RULES_VERSION

    def __init__(self, seed: str, distribution: str = STAGE):
        super().__init__(seed, STAGE)
        self.distribution = RULES_DISTRIBUTION

    def begin_episode(self) -> dict[str, Any]:
        return {"mode": "rule"}

    def choose(self, purpose: str, items: list[Any], context: dict[str, Any]) -> tuple[int, str]:
        if purpose != "candidate":
            return UniformPolicy.choose(self, purpose, items, context)  # 入力は uniform-stage
        return self._rule_candidate(items, context)

    def _rule_candidate(self, items, context) -> tuple[int, str]:
        if not items:
            raise ValueError("選べるものがない場面で方策を呼んだ（行動生成の誤り）")
        ranks = [PRIORITY.get(c.get("kind")) if isinstance(c, dict) else None for c in items]
        known = [r for r in ranks if r is not None]
        if not known:
            index, _ = UniformPolicy.choose(self, "candidate", items, context)
            return index, "rule:fallback:no_priority"
        best = min(known)
        pool = [i for i, r in enumerate(ranks) if r == best]
        if len(pool) == 1:
            return pool[0], f"rule:priority{best}:{items[pool[0]]['kind']}"
        self.draws += 1
        pick = pool[self._rng.randrange(len(pool))]
        return pick, f"rule:priority{best}:{items[pick]['kind']}:tie{len(pool)}"


def mix_seed(policy_seed: int, player: int) -> str:
    """混合の判定の乱数の種（候補・入力の選択の乱数と別。ゲームの乱数とも別）。"""
    return f"kyuura-vai-v2:mix:{policy_seed}:{player}"


class MixedPolicy(RulePolicy):
    """選択のエピソード（1 つの状態での 1 つの主体の行動の選択。受理・対戦の終わり・上限で区切る）ごとに、混合の乱数で 1 回だけ ``random() < epsilon`` を引き、
    真ならエピソードのあいだずっと均等（UniformPolicy と同じ選び方）、偽なら rules-v1。エピソードの途中（段の選択・入力を作れない・check の invalid・拒否のあとの
    選び直し）では引き直さない。候補・入力の選択の乱数は 1 本で、どちらの方式でも同じ乱数を続けて使う。"""

    name = MIXED_NAME
    version = MIXED_VERSION

    def __init__(self, seed: str, distribution: str = STAGE, *, epsilon: float, mix_seed_text: str):
        super().__init__(seed)
        if not 0.0 <= epsilon <= 1.0:
            raise ValueError("epsilon は 0〜1")
        self.distribution = MIXED_DISTRIBUTION
        self.epsilon = epsilon
        self.mix_seed = mix_seed_text
        self._mix = random.Random(mix_seed_text)
        self.mode = None
        self.episodes = {"random": 0, "rule": 0}

    def begin_episode(self) -> dict[str, Any]:
        draw = self._mix.random()
        self.mode = "random" if draw < self.epsilon else "rule"
        self.episodes[self.mode] += 1
        return {"mode": self.mode, "draw": round(draw, 6), "epsilon": self.epsilon}

    def choose(self, purpose: str, items: list[Any], context: dict[str, Any]) -> tuple[int, str]:
        if self.mode is None:
            raise RuntimeError("エピソードを始める前に選んだ（ランナーの誤り）")
        if self.mode == "random" or purpose != "candidate":
            return UniformPolicy.choose(self, purpose, items, context)
        return self._rule_candidate(items, context)
