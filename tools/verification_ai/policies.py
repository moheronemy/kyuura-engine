"""戦略（C）。V0 は均等の選び方 1 つだけ（docs/verification-ai-v0.md 3 章）。

方策は、行動生成・ランナーが渡した選べるもの（JSON の値の並び）の中から 1 つの位置を選び、理由のコードを返すだけです。合法性を判定せず、
``kyuura_engine`` を import しません。``context`` は本人向けの JSON の値だけ（観測・API の応答）で、均等の方策は読みません（ルールの方策は V2）。

乱数は方策ごとの ``random.Random``（種は文字列。Python の文字列の種は実行ごとに同じ値になる）で、エンジンの乱数を使いません。
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
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


# ---------------------------------------------------------------- V2 の補完: 同じ意味の操作と反復の抑制（docs/verification-ai-v2-repeat.md 2 章・3 章）

RULES2_DISTRIBUTION = "rules-v2-candidate+uniform-stage"
REPEAT_THRESHOLD = 2  # 同じ番・同じ主体で同じ鍵の操作が 2 回受理されたら、以後その番では抑える
DEMOTE_AFTER = 2  # 同じエピソードで同じ候補の入力を 2 回抑えたら、その候補を end_turn より後ろ（DEMOTED_RANK）へ下げる
DEMOTED_RANK = 7
EVAL_FIELDS = frozenset({"id", "after", "processability", "reasons", "eligible", "guarantees", "choices_format", "input_stages", "input_disclosure"})
ORDER_FREE = frozenset({"not_significant", "not_applicable"})


def _canon(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _strip(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if k not in EVAL_FIELDS}


def candidate_identity(candidate: dict[str, Any]) -> str:
    """候補の中身から評価の値と番号を除いたもの（同じ状態の中で候補を見分ける。番号 c1… は使わない）。"""
    return _canon(_strip(candidate))


def action_key(actor, candidate: dict[str, Any], stages: list[dict[str, Any]], meaning: list[dict[str, Any]]) -> str:
    """同じ意味の操作の鍵: 主体・種類・候補の対象・入力の意味。評価の値と応答ごとの番号を除く。並びに意味のない段（not_significant・not_applicable）は
    段の中を正準な順に並べかえ、ほかの段は選んだ順のまま。"""
    orders = {s["stage"]: s.get("order") for s in stages}
    by_stage: dict[int, list] = {}
    for m in meaning:
        by_stage.setdefault(m["stage"], []).append({"value": m["value"]} if "value" in m else _strip(m["option"]))
    parts = []
    for number in sorted(by_stage):
        items = by_stage[number]
        if orders.get(number) in ORDER_FREE:
            items = sorted(items, key=_canon)
        parts.append({"stage": number, "items": items})
    return _canon({"actor": actor, "kind": candidate.get("kind"), "candidate": _strip(candidate), "input": parts})


def short_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def turn_of(view: dict[str, Any]) -> tuple:
    """本人の観測の（区間の番号, 番の番号）。公開の値だけ。"""
    return (view.get("status", {}).get("segment"), view.get("observation", {}).get("turn"))


class RepeatMemory:
    """同じ番の同じ鍵の受理の回数（番が変われば空にする）と、エピソードの中の抑えた回数・下げた候補。"""

    def __init__(self, threshold: int = REPEAT_THRESHOLD, demote_after: int = DEMOTE_AFTER):
        self.threshold, self.demote_after = threshold, demote_after
        self.turn = None
        self.counts: Counter = Counter()
        self.suppressed: Counter = Counter()
        self.demoted: set[str] = set()

    def _at(self, turn) -> None:
        if turn != self.turn:
            self.turn, self.counts = turn, Counter()

    def begin_episode(self) -> None:
        self.suppressed, self.demoted = Counter(), set()

    def accepted(self, turn, key: str) -> None:
        self._at(turn)
        self.counts[key] += 1

    def count(self, turn, key: str) -> int:
        self._at(turn)
        return self.counts[key]


class RulePolicy(UniformPolicy):
    """rules-v1（``version=1``）: 候補の選択だけに優先順位を使う。同じ順位の候補が 2 つ以上なら、方策の乱数（UniformPolicy と同じ種の導き方）で均等に選ぶ。

    rules-v2（``version=2``）: rules-v1 に反復の抑制を加える（``review``・``observe_accepted``。docs/verification-ai-v2-repeat.md 3 章）。候補を消さず、処理可能性を書き換えない。"""

    name = RULES_NAME

    def __init__(self, seed: str, distribution: str = STAGE, *, version: int = RULES_VERSION, threshold: int = REPEAT_THRESHOLD):
        super().__init__(seed, STAGE)
        if version not in (1, 2):
            raise ValueError("rules の版は 1 か 2")
        self.version = version
        self.distribution = RULES_DISTRIBUTION if version == 1 else RULES2_DISTRIBUTION
        self.memory = RepeatMemory(threshold) if version == 2 else None
        self.threshold = threshold if version == 2 else None

    def begin_episode(self) -> dict[str, Any]:
        if self.memory is not None:
            self.memory.begin_episode()
        return {"mode": "rule"}

    def observe_accepted(self, turn, key: str) -> None:
        """受理された操作（どの方式で選んだものも）を履歴に加える。rules-v1 は何もしない。"""
        if self.memory is not None:
            self.memory.accepted(turn, key)

    def review(self, candidate: dict[str, Any], key: str, turn) -> dict[str, Any]:
        """送る前の評価（戦略の選好）。``send`` が偽なら、ランナーはその入力を送らず選び直す。合法性・処理可能性の判定ではない。"""
        if self.memory is None:
            return {"send": True, "reason": "no_review"}
        return self._rule_review(candidate, key, turn)

    def _rule_review(self, candidate, key, turn) -> dict[str, Any]:
        n = self.memory.count(turn, key)
        out = {"accepted_this_turn": n, "threshold": self.memory.threshold}
        if n < self.memory.threshold:
            return {"send": True, "reason": "below_threshold", **out}
        if candidate.get("kind") == "end_turn" or candidate.get("kind") not in PRIORITY:
            return {"send": True, "reason": "not_suppressible", **out}
        cid = candidate_identity(candidate)
        if cid in self.memory.demoted:
            return {"send": True, "reason": "rule2:no_alternative", **out}  # 下げた候補しか残っていないので選ばれた: 対戦を止めない
        self.memory.suppressed[cid] += 1
        demoted = self.memory.suppressed[cid] >= self.memory.demote_after
        if demoted:
            self.memory.demoted.add(cid)
        return {"send": False, "reason": "repeat_suppressed" + (":candidate_demoted" if demoted else ""), **out}

    def choose(self, purpose: str, items: list[Any], context: dict[str, Any]) -> tuple[int, str]:
        if purpose != "candidate":
            return UniformPolicy.choose(self, purpose, items, context)  # 入力は uniform-stage
        return self._rule_candidate(items, context)

    def _rule_candidate(self, items, context) -> tuple[int, str]:
        if not items:
            raise ValueError("選べるものがない場面で方策を呼んだ（行動生成の誤り）")
        ranks = [PRIORITY.get(c.get("kind")) if isinstance(c, dict) else None for c in items]
        prefix = "rule"
        if self.memory is not None:  # rules-v2: このエピソードで下げた候補は end_turn より後ろ
            prefix = "rule2"
            ranks = [DEMOTED_RANK if r is not None and candidate_identity(c) in self.memory.demoted else r for r, c in zip(ranks, items)]
        known = [r for r in ranks if r is not None]
        if not known:
            index, _ = UniformPolicy.choose(self, "candidate", items, context)
            return index, f"{prefix}:fallback:no_priority"
        best = min(known)
        tag = "demoted:" if best == DEMOTED_RANK else ""
        pool = [i for i, r in enumerate(ranks) if r == best]
        if len(pool) == 1:
            return pool[0], f"{prefix}:{tag}priority{best}:{items[pool[0]]['kind']}"
        self.draws += 1
        pick = pool[self._rng.randrange(len(pool))]
        return pick, f"{prefix}:{tag}priority{best}:{items[pick]['kind']}:tie{len(pool)}"


def mix_seed(policy_seed: int, player: int) -> str:
    """混合の判定の乱数の種（候補・入力の選択の乱数と別。ゲームの乱数とも別）。"""
    return f"kyuura-vai-v2:mix:{policy_seed}:{player}"


class MixedPolicy(RulePolicy):
    """選択のエピソード（1 つの状態での 1 つの主体の行動の選択。受理・対戦の終わり・上限で区切る）ごとに、混合の乱数で 1 回だけ ``random() < epsilon`` を引き、
    真ならエピソードのあいだずっと均等（UniformPolicy と同じ選び方）、偽なら rules-v1。エピソードの途中（段の選択・入力を作れない・check の invalid・拒否のあとの
    選び直し）では引き直さない。候補・入力の選択の乱数は 1 本で、どちらの方式でも同じ乱数を続けて使う。"""

    name = MIXED_NAME
    version = MIXED_VERSION

    def __init__(self, seed: str, distribution: str = STAGE, *, epsilon: float, mix_seed_text: str, rule_version: int = RULES_VERSION,
                 threshold: int = REPEAT_THRESHOLD):
        super().__init__(seed, version=rule_version, threshold=threshold)
        if not 0.0 <= epsilon <= 1.0:
            raise ValueError("epsilon は 0〜1")
        self.version = MIXED_VERSION
        self.rules_version = rule_version  # ルールの側の版（V2 の補完。既定は 1 で V2 と同じ）
        self.distribution = MIXED_DISTRIBUTION if rule_version == 1 else f"mixed(rules-v{rule_version}|uniform-candidate)+uniform-stage"
        self.epsilon = epsilon
        self.mix_seed = mix_seed_text
        self._mix = random.Random(mix_seed_text)
        self.mode = None
        self.episodes = {"random": 0, "rule": 0}

    def begin_episode(self) -> dict[str, Any]:
        draw = self._mix.random()
        self.mode = "random" if draw < self.epsilon else "rule"
        self.episodes[self.mode] += 1
        if self.memory is not None:
            self.memory.begin_episode()
        return {"mode": self.mode, "draw": round(draw, 6), "epsilon": self.epsilon}

    def review(self, candidate: dict[str, Any], key: str, turn) -> dict[str, Any]:
        if self.mode == "random":
            return {"send": True, "reason": "random_side"}  # ランダムの側は抑えない（履歴は observe_accepted で更新する）
        return RulePolicy.review(self, candidate, key, turn)

    def choose(self, purpose: str, items: list[Any], context: dict[str, Any]) -> tuple[int, str]:
        if self.mode is None:
            raise RuntimeError("エピソードを始める前に選んだ（ランナーの誤り）")
        if self.mode == "random" or purpose != "candidate":
            return UniformPolicy.choose(self, purpose, items, context)
        return self._rule_candidate(items, context)


# ---------------------------------------------------------------- V3-2: boundary の選び方（docs/verification-ai-v3-2.md 4 章）

BOUNDARY_NAME = "boundary"
BOUNDARY_VERSION = 1
BOUNDARY_DISTRIBUTION = "boundary-class-uniform+uniform-stage"


class BoundaryPolicy(UniformPolicy):
    """候補の選択だけ: 渡された候補（ランナーの boundary の範囲。表示だけ・入力を返さない・実行できない区分は入っていない）の、候補の処理可能性の区分を列挙し、区分を均等に 1 つ、
    その区分の候補を均等に 1 つ選ぶ（区分・候補が 1 つなら乱数を使わない）。入力は uniform-stage。合法性を判定しない。候補の区分は候補の値（選べるもの・組の中でいちばん
    進めやすい区分）で、完成した入力の区分とは別（ランナーが記録する）。"""

    name = BOUNDARY_NAME
    version = BOUNDARY_VERSION

    def __init__(self, seed: str, distribution: str = STAGE):
        super().__init__(seed, STAGE)
        self.distribution = BOUNDARY_DISTRIBUTION

    def choose(self, purpose: str, items: list[Any], context: dict[str, Any]) -> tuple[int, str]:
        if purpose != "candidate":
            return UniformPolicy.choose(self, purpose, items, context)
        if not items:
            raise ValueError("選べるものがない場面で方策を呼んだ（行動生成の誤り）")
        classes = sorted({c.get("processability") for c in items}, key=lambda v: (v is None, str(v)))
        cls = classes[0]
        if len(classes) > 1:
            self.draws += 1
            cls = classes[self._rng.randrange(len(classes))]
        pool = [i for i, c in enumerate(items) if c.get("processability") == cls]
        pick = pool[0]
        if len(pool) > 1:
            self.draws += 1
            pick = pool[self._rng.randrange(len(pool))]
        return pick, f"boundary:class:{cls}:{len(classes)}classes:{len(pool)}in_class"
