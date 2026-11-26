"""戦略（C）。V0 は均等の選び方 1 つだけ（docs/verification-ai-v0.md 3 章）。

方策は、行動生成・ランナーが渡した選べるもの（JSON の値の並び）の中から 1 つの位置を選び、理由のコードを返すだけです。合法性を判定せず、
``kyuura_engine`` を import しません。``context`` は本人向けの JSON の値だけ（観測・API の応答）で、均等の方策は読みません（ルールの方策は V2）。

乱数は方策ごとの ``random.Random``（種は文字列。Python の文字列の種は実行ごとに同じ値になる）で、エンジンの乱数を使いません。
"""

from __future__ import annotations

import copy
import hashlib
import itertools
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
        ranks, prefix, note = self._adjust_ranks(items, ranks, prefix)
        known = [r for r in ranks if r is not None]
        if not known:
            index, _ = UniformPolicy.choose(self, "candidate", items, context)
            return index, f"{prefix}:fallback:no_priority{note}"
        best = min(known)
        tag = "demoted:" if best == DEMOTED_RANK else ""
        pool = [i for i, r in enumerate(ranks) if r == best]
        if len(pool) == 1:
            return pool[0], f"{prefix}:{tag}priority{best}:{items[pool[0]]['kind']}{note}"
        self.draws += 1
        pick = pool[self._rng.randrange(len(pool))]
        return pick, f"{prefix}:{tag}priority{best}:{items[pick]['kind']}:tie{len(pool)}{note}"

    def _adjust_ranks(self, items, ranks, prefix) -> tuple[list, str, str]:
        """rules-v3（LoopRulePolicy）の差し込み口。rules-v1・rules-v2 は順位・理由のコードを変えない（同じ値を返す）。"""
        return ranks, prefix, ""


# ---------------------------------------------------------------- rules-v3（試験の方策）: 観測が戻った［ダメージスワップ］の周期の候補を、その番の残りで下げる
# （docs/tr8-damage-swap-loop-analysis.md 5 章の案 C・docs/tr8-damage-swap-loop-experiment.md）。rules-v2 の順位・同順位の選び方・入力単位の再送抑止はそのまま使う。
# 履歴は方策の中だけに持つ（ランナーが渡すのは、本人の入口の観測の応答・本人の受理の候補・受理の通し番号だけ）。合法性を判定しない

RULES3_VERSION = 3
RULES3_DISTRIBUTION = "rules-v3-candidate+uniform-stage"
LOOP_KIND = "use_power"
LOOP_POWER_NAMES = ("ダメージスワップ",)  # 検出の対象の特殊能力（候補の power.name_ja。公開の値）
VIEW_OUTSIDE_FIELDS = frozenset({"request_id", "operation_id"})  # 観測の内容の外の識別子（比べない）。今の view の応答には現れない
LOOP_DEMOTION = {"version": 1, "kind": LOOP_KIND, "powers": list(LOOP_POWER_NAMES), "key": "kind+holder(pokemon)",
                 "compare": "own view response (canonical JSON, outside identifiers removed)", "scope": "same actor, same turn, run of accepted target powers only",
                 "effect": f"rank {DEMOTED_RANK} (after end_turn) until the turn changes", "reset": "turn change"}


def loop_target(candidate: dict[str, Any]) -> bool:
    """周期の検出の対象（［ダメージスワップ］の宣言の候補）か。"""
    return (isinstance(candidate, dict) and candidate.get("kind") == LOOP_KIND
            and (candidate.get("power") or {}).get("name_ja") in LOOP_POWER_NAMES)


def loop_key(candidate: dict[str, Any]) -> str:
    """周期の候補を追う鍵: 操作の種類と能力の持ち主の参照（場のポケモンの番号）。候補の番号・場所（バトル場・ベンチ）・入力（移動元・移動先）を含めない。"""
    holder = candidate.get("pokemon") or {}
    ref = holder.get("pokemon") if holder.get("pokemon") is not None else {"card": holder.get("card")}
    return _canon({"kind": candidate.get("kind"), "holder": ref})


def view_signature(view: dict[str, Any]) -> str | None:
    """本人の観測の応答の比較の値（観測の外の識別子だけを除く。ダメージ・付いたカード・特殊状態・手札・決定などを省かない）。取れなければ None。"""
    if not isinstance(view, dict) or not view.get("ok") or not isinstance(view.get("observation"), dict):
        return None
    return _canon({k: v for k, v in view.items() if k not in VIEW_OUTSIDE_FIELDS})


class LoopRulePolicy(RulePolicy):
    """rules-v3: rules-v2 に、同じ番の［ダメージスワップ］だけが続いた受理の区間で本人の観測が以前の観測に戻ったとき、直近の一致から今回の受理までに
    使った［ダメージスワップ］の候補（``loop_key``）を、その番の残りで ``DEMOTED_RANK``（end_turn より後ろ）に置く規則を加える。

    - ランナーは本人の選択のエピソードの始めに ``observe_view``（本人の観測の応答と受理の通し番号）、本人の受理のあとに ``accepted_candidate`` を呼ぶ
    - 区間: 本人の受理が対象の特殊能力で、次の本人の観測までにほかの受理がない（通し番号が続く）あいだ。ほかの操作の受理・ほかの主体の受理で区間を切る
    - 拒否・入力を作れない・送信の抑止では観測を取らず、履歴を進めない（同じエピソードの選び直し）
    - 観測を取れない受理があった区間では下げない。番が変われば区間と下げた候補の両方を消す
    - 下げた候補しか残らなければ、rules-v2 と同じく順位 ``DEMOTED_RANK`` の中から選ぶ（入力単位の抑止は rules-v2 の評価のまま）"""

    def __init__(self, seed: str, distribution: str = STAGE, *, threshold: int = REPEAT_THRESHOLD):
        super().__init__(seed, STAGE, version=2, threshold=threshold)
        self.version = RULES3_VERSION
        self.distribution = RULES3_DISTRIBUTION
        self.loop_demotion = LOOP_DEMOTION
        self._turn = None
        self._run: dict[str, Any] | None = None
        self._pending: dict[str, Any] | None = None
        self._loop_demoted: set[str] = set()
        self._detection: dict[str, Any] | None = None
        self.loop_counts = Counter()

    def observe_view(self, view: dict[str, Any], position: int) -> None:
        sig = view_signature(view)
        turn = turn_of(view) if sig is not None else self._turn  # 観測が取れなければ番を変えない（その区間を下げない区間にする）
        if turn != self._turn:
            if self._loop_demoted:
                self.loop_counts["turn_resets_with_demotion"] += 1
            self._turn, self._run, self._pending, self._loop_demoted = turn, None, None, set()
        pending, self._pending, self._detection = self._pending, None, None
        if pending is not None and pending["target"] and pending["position"] == position and self._run is not None:
            run = self._run
            run["keys"].append(pending["key"])
            if sig is None:
                run["valid"] = False
                self.loop_counts["runs_without_view"] += 1
            if run["valid"]:
                matched = [i for i, v in enumerate(run["views"]) if v == sig]
                if matched:
                    j = matched[-1]
                    keys = run["keys"][j:]
                    new = sorted(set(keys) - self._loop_demoted)
                    self._loop_demoted.update(keys)
                    self.loop_counts["detections"] += 1
                    self.loop_counts["demoted_keys"] += len(new)
                    self._detection = {"position": position, "turn": list(turn) if turn is not None else None, "returned_to": j,
                                       "run_accepts": len(run["keys"]), "cycle_length": len(keys), "view": short_key(sig),
                                       "newly_demoted": [short_key(k) for k in new], "demoted_this_turn": len(self._loop_demoted)}
            run["views"].append(sig)
        else:  # 区間の始め（番の始め・ほかの操作の受理・ほかの主体の受理・最初の観測）
            self._run = {"views": [sig], "keys": [], "valid": sig is not None}

    def accepted_candidate(self, candidate: dict[str, Any], position: int) -> None:
        target = loop_target(candidate)
        self._pending = {"position": position, "target": target, "key": loop_key(candidate) if target else None}

    def begin_episode(self) -> dict[str, Any]:
        info = super().begin_episode()
        if self._detection is not None:
            info["loop_detection"] = dict(self._detection)
        if self._loop_demoted:
            info["loop_demoted"] = len(self._loop_demoted)
        return info

    def _adjust_ranks(self, items, ranks, prefix) -> tuple[list, str, str]:
        hit = [r is not None and loop_target(c) and loop_key(c) in self._loop_demoted for r, c in zip(ranks, items)]
        n = sum(hit)
        ranks = [DEMOTED_RANK if h else r for r, h in zip(ranks, hit)]
        if n:
            self.loop_counts["choices_with_loop_demoted"] += 1
        return ranks, "rule3", (f":loop_demoted{n}" if n else "")

    def loop_summary(self) -> dict[str, Any]:
        return {**LOOP_DEMOTION, "counts": dict(sorted(self.loop_counts.items()))}


# ---------------------------------------------------------------- rules-v4（試験の方策）: 確認した［ダメージスワップ］の周期の移動だけを後回しにする
# （docs/tr8-damage-swap-transition-policy-design.md 3 章・4 章・docs/tr8-damage-swap-transition-policy-experiment.md）。rules-v2 の順位・同順位の選び方・
# 入力単位の再送抑止はそのまま。周期の検出は rules-v3 と同じ。下げるのは持ち主の候補の全体ではなく（操作前の本人の観測, 持ち主, 移動元, 移動先）の鍵。
# 1 番あたりの追加の上限・検出の回数による持ち主の全体の降格は入れない（設計の U1 を「追加の抑制なしで試す」と決めた）。合法性を判定しない

RULES4_VERSION = 4
RULES4_DISTRIBUTION = "rules-v4-candidate+uniform-stage"
DEFER_ALL = "transition_deferred_all"  # input_restriction の返り値: 新しい inputs の応答で外さない組が 0（その候補をこのエピソードで順位 7 にして選び直す）
TRANSITION_DEFERRAL = {"version": 1, "kind": LOOP_KIND, "powers": list(LOOP_POWER_NAMES),
                       "key": "(pre-move own view, holder kind+pokemon, source pokemon, target pokemon), directed",
                       "detection": "same as rules-v3 (same actor, same turn, run of accepted target powers, own view returns; latest match)",
                       "effect": "deferred pairs removed from the input choices at that view; candidate rank 7 (after end_turn) only when every buildable pair "
                                 "at the view is deferred; restriction lifted when only rank-7 candidates remain",
                       "scope": "deep processability only (supported, may_stop_later)", "extra_guard": None, "reset": "turn change"}


def move_of(meaning: list[dict[str, Any]]) -> tuple[int, int] | None:
    """受理した入力の意味の（移動元, 移動先）の場のポケモンの番号。2 段の選べるもので番号が整数でなければ None（記録しない）。"""
    if not isinstance(meaning, list) or len(meaning) != 2 or [m.get("stage") for m in meaning] != [1, 2]:
        return None
    refs = [(m.get("option") or {}).get("pokemon") for m in meaning]
    return (refs[0], refs[1]) if all(type(r) is int for r in refs) else None


def holder_of(candidate: dict[str, Any]) -> str | None:
    """持ち主の鍵（rules-v3 の ``loop_key`` と同じ値）。場のポケモンの番号がなければ None（記録しない・後回しにしない）。"""
    if type((candidate.get("pokemon") or {}).get("pokemon")) is not int:
        return None
    return loop_key(candidate)


class TransitionRulePolicy(RulePolicy):
    """rules-v4: rules-v2 に、rules-v3 と同じ検出で確認した周期の各移動を（操作前の本人の観測, 持ち主, 移動元, 移動先）で記録し、その観測でだけ後回しにする規則を加える。

    ランナーの差し込み口（この方策だけが持つ。rules-v2・rules-v3 の物にはない）:
    - ``observe_view(view, position)``: エピソードの始めの本人の観測（rules-v3 と同じ）
    - ``observe_inputs(candidate, stages, allowed)``: inputs の応答を受けたあと・組み立ての前。(今の観測, 持ち主) の組の写しを保存する
    - ``input_restriction(candidate, stages, allowed)``: 組み立ての直前。外す組の集合（なければ None）か ``DEFER_ALL``
    - ``accepted_input(candidate, meaning, position)``: 本人の受理のあと（rules-v3 の ``accepted_candidate`` の代わり）

    候補の順位: 今の観測 V・持ち主 h に鍵がなければ、また (V, h) の組の写しがなければ、順位は rules-v2 のまま。写しの組がすべて鍵にあれば順位 7。
    順位 7 の候補しか残らず、後回しで下げた候補を選んだときは、その試みの入力を制限しない（理由 :no_alternative）。"""

    def __init__(self, seed: str, distribution: str = STAGE, *, threshold: int = REPEAT_THRESHOLD):
        super().__init__(seed, STAGE, version=2, threshold=threshold)
        self.version = RULES4_VERSION
        self.distribution = RULES4_DISTRIBUTION
        self.transition_deferral = TRANSITION_DEFERRAL
        self._turn = None
        self._sig: str | None = None
        self._run: dict[str, Any] | None = None
        self._pending: dict[str, Any] | None = None
        self._deferred: set[tuple] = set()  # (観測, 持ち主, 移動元, 移動先)
        self._pairs: dict[tuple, frozenset] = {}  # (観測, 持ち主) → 組み立てられる組
        self._episode_deferred: set[str] = set()  # このエピソードで新しい応答の組が 0 になった持ち主
        self._demoted_now: set[str] = set()  # 直近の候補の選択で後回しにより順位 7 にした持ち主
        self._lifted: str | None = None  # 直近の候補の選択で制限を外した持ち主（:no_alternative）
        self._detection: dict[str, Any] | None = None
        self.last_restriction: dict[str, Any] | None = None
        self.loop_counts = Counter()

    # -- 観測と検出（rules-v3 と同じ区間・同じ一致）
    def observe_view(self, view: dict[str, Any], position: int) -> None:
        sig = view_signature(view)
        turn = turn_of(view) if sig is not None else self._turn
        if turn != self._turn:
            if self._deferred:
                self.loop_counts["turn_resets_with_deferral"] += 1
            self._turn, self._run, self._pending, self._deferred, self._pairs = turn, None, None, set(), {}
        self._sig = sig
        pending, self._pending, self._detection = self._pending, None, None
        if pending is not None and pending["target"] and pending["position"] == position and self._run is not None:
            run = self._run
            run["moves"].append(pending["move"])
            if sig is None:
                run["valid"] = False
                self.loop_counts["runs_without_view"] += 1
            if run["valid"]:
                matched = [i for i, v in enumerate(run["views"]) if v == sig]
                if matched:
                    j = matched[-1]
                    new = []
                    for k in range(j, len(run["moves"])):
                        move = run["moves"][k]
                        if move is None:
                            self.loop_counts["keys_missing_ref"] += 1
                            continue
                        key = (run["views"][k], *move)
                        if key not in self._deferred:
                            self._deferred.add(key)
                            new.append(key)
                    self.loop_counts["detections"] += 1
                    self.loop_counts["deferred_keys"] += len(new)
                    self._detection = {"position": position, "turn": list(turn) if turn is not None else None, "returned_to": j,
                                       "run_accepts": len(run["moves"]), "cycle_length": len(run["moves"]) - j, "view": short_key(sig),
                                       "newly_deferred": [{"view": short_key(k[0]), "holder": short_key(k[1]), "move": [k[2], k[3]]} for k in new],
                                       "deferred_this_turn": len(self._deferred)}
            run["views"].append(sig)
        else:  # 区間の始め（番の始め・ほかの操作の受理・ほかの主体の受理・最初の観測）
            self._run = {"views": [sig], "moves": [], "valid": sig is not None}

    def accepted_input(self, candidate: dict[str, Any], meaning: list[dict[str, Any]], position: int) -> None:
        target = loop_target(candidate)
        move = None
        if target:
            holder, pair = holder_of(candidate), move_of(meaning)
            move = (holder, *pair) if holder is not None and pair is not None else None
        self._pending = {"position": position, "target": target, "move": move}

    # -- 組の写しと入力の制限
    def _deferred_pairs(self, holder: str) -> frozenset:
        return frozenset((s, t) for v, h, s, t in self._deferred if v == self._sig and h == holder)

    def observe_inputs(self, candidate: dict[str, Any], stages: list[dict[str, Any]], allowed) -> None:
        from .actions import DEEP_PROCESSABILITY, transition_pairs  # actions は kyuura_engine を import しない
        holder = holder_of(candidate) if loop_target(candidate) else None
        if holder is None or self._sig is None or frozenset(allowed) != DEEP_PROCESSABILITY:
            return
        pairs = transition_pairs(stages, allowed)
        if pairs is None:
            return
        old = self._pairs.get((self._sig, holder))
        if old is not None and old != pairs:
            self.loop_counts["pairs_cache_mismatch"] += 1
        self._pairs[(self._sig, holder)] = pairs

    def input_restriction(self, candidate: dict[str, Any], stages: list[dict[str, Any]], allowed):
        from .actions import DEEP_PROCESSABILITY, transition_pairs
        self.last_restriction = None
        holder = holder_of(candidate) if loop_target(candidate) else None
        if holder is None or self._sig is None:
            return None
        deferred = self._deferred_pairs(holder)
        if not deferred:
            return None
        record = {"view": short_key(self._sig), "holder": short_key(holder), "deferred_at_view": sorted([list(p) for p in deferred])}
        self.last_restriction = record
        if self._lifted == holder:
            record["result"] = "lifted_no_alternative"
            self.loop_counts["restrictions_lifted"] += 1
            return None
        pairs = transition_pairs(stages, allowed) if frozenset(allowed) == DEEP_PROCESSABILITY else None
        if pairs is None:
            record["result"] = "restriction_unavailable"
            self.loop_counts["restriction_unavailable"] += 1
            return None
        excluded = deferred & pairs
        record.update({"pairs": len(pairs), "excluded": sorted([list(p) for p in excluded])})
        if not pairs - deferred:
            record["result"] = DEFER_ALL
            self._episode_deferred.add(holder)
            self.loop_counts["deferred_all_after_inputs"] += 1
            return DEFER_ALL
        if not excluded:
            record["result"] = "no_deferred_pair_buildable"
            return None
        record["result"] = "restricted"
        self.loop_counts["restricted_builds"] += 1
        return frozenset(excluded)

    # -- 候補の順位
    def begin_episode(self) -> dict[str, Any]:
        info = super().begin_episode()
        self._episode_deferred, self._lifted, self._demoted_now = set(), None, set()
        if self._detection is not None:
            info["loop_detection"] = dict(self._detection)
        if self._deferred:
            info["transition_deferred"] = len(self._deferred)
        return info

    def _all_deferred(self, holder: str) -> bool:
        if holder in self._episode_deferred:
            return True
        deferred = self._deferred_pairs(holder)
        pairs = self._pairs.get((self._sig, holder))
        return bool(deferred) and pairs is not None and pairs <= deferred

    def _adjust_ranks(self, items, ranks, prefix) -> tuple[list, str, str]:
        holders = [holder_of(c) if r is not None and loop_target(c) else None for r, c in zip(ranks, items)]
        hit = [h is not None and self._all_deferred(h) for h in holders]
        self._demoted_now = {h for h, x in zip(holders, hit) if x}
        ranks = [DEMOTED_RANK if x else r for r, x in zip(ranks, hit)]
        n = sum(hit)
        if n:
            self.loop_counts["choices_with_deferred_all"] += 1
        return ranks, "rule4", (f":deferred_all{n}" if n else "")

    def _rule_candidate(self, items, context) -> tuple[int, str]:
        self._lifted = None
        index, reason = super()._rule_candidate(items, context)
        chosen = items[index]
        holder = holder_of(chosen) if isinstance(chosen, dict) and loop_target(chosen) else None
        if holder is not None and holder in self._demoted_now and ":demoted:" in reason:
            self._lifted = holder
            self.loop_counts["no_alternative"] += 1
            reason += ":no_alternative"
        return index, reason

    def loop_summary(self) -> dict[str, Any]:
        return {**TRANSITION_DEFERRAL, "counts": dict(sorted(self.loop_counts.items()))}


# ---------------------------------------------------------------- rules-v5（試験の方策）: rules-v4 に、1 番の［ダメージスワップ］の受理の回数による順位の変更を加える
# （docs/tr8-rules-v4-9022-guard-analysis.md 6 章・docs/tr8-rules-v5-damage-swap-guard-experiment.md）。rules-v4 の周期の検出・入力の制限・後回し、rules-v2 の順位・
# 同順位の選び方・入力単位の再送抑止はそのまま。候補を消さず、合法性を判定しない（エンジンでの使用の禁止ではない。方策の順位だけ）

RULES5_VERSION = 5
RULES5_DISTRIBUTION = "rules-v5-candidate+uniform-stage"
SWAP_CAP = 6  # 同じ番に本人の［ダメージスワップ］が 6 回受理されたら、その番の残りで候補を順位 7（end_turn より後ろ）に置く
SWAP_CAP_RULE = {"version": 1, "kind": LOOP_KIND, "powers": list(LOOP_POWER_NAMES), "cap": SWAP_CAP,
                 "count": "own accepted target powers in the own (segment, turn), all holders summed; rejected / unbuildable / suppressed not counted; "
                          "other accepted operations do not reset",
                 "effect": f"after {SWAP_CAP} accepted, target power candidates rank {DEMOTED_RANK} (after end_turn) for the rest of the turn; "
                           "candidate kept (chosen only when nothing ranks higher; rules-v4 input restriction and rules-v2 repeat suppression unchanged)",
                 "base": "rules-v4", "reset": "turn change"}


class SwapCapRulePolicy(TransitionRulePolicy):
    """rules-v5: rules-v4 に、同じ番の本人の［ダメージスワップ］の受理の回数（持ち主をまたいで合計）が ``SWAP_CAP`` に達したら、その番の残りで
    対象の候補を ``DEMOTED_RANK``（end_turn より後ろ）に置く規則を加える。

    - 数えるのは本人の受理だけ（``accepted_input``）。拒否・入力を作れない・送信の抑止・後回しで組み立てなかった試みは数えない
    - ほかの操作の受理では消さない。番（本人の観測の（区間, 番））が変われば消す（rules-v4 の番の更新と同じ所）
    - 順位 7 の候補しか残らなければ rules-v2 と同じく順位 7 の中から選ぶ。そのときの入力の制限は rules-v4 のまま（回数では制限を外さない）"""

    def __init__(self, seed: str, distribution: str = STAGE, *, threshold: int = REPEAT_THRESHOLD, cap: int = SWAP_CAP):
        super().__init__(seed, STAGE, threshold=threshold)
        if type(cap) is not int or cap < 1:
            raise ValueError("cap は 1 以上の整数")
        self.version = RULES5_VERSION
        self.distribution = RULES5_DISTRIBUTION
        self.swap_cap = {**SWAP_CAP_RULE, "cap": cap}
        self.cap = cap
        self._swaps = 0  # この番の本人の対象の受理の回数
        self._swap_turn = None

    def observe_view(self, view: dict[str, Any], position: int) -> None:
        super().observe_view(view, position)
        if self._turn != self._swap_turn:
            if self._swaps >= self.cap:
                self.loop_counts["turn_resets_with_swap_cap"] += 1
            self._swap_turn, self._swaps = self._turn, 0

    def accepted_input(self, candidate: dict[str, Any], meaning: list[dict[str, Any]], position: int) -> None:
        super().accepted_input(candidate, meaning, position)
        if loop_target(candidate):
            self._swaps += 1
            self.loop_counts["swaps_accepted"] += 1
            if self._swaps == self.cap:
                self.loop_counts["swap_cap_reached"] += 1

    def begin_episode(self) -> dict[str, Any]:
        info = super().begin_episode()
        if self._swaps:
            info["swap_count"] = {"accepted_this_turn": self._swaps, "cap": self.cap, "capped": self._swaps >= self.cap}
        return info

    def _adjust_ranks(self, items, ranks, prefix) -> tuple[list, str, str]:
        ranks, _, note = super()._adjust_ranks(items, ranks, prefix)
        n = 0
        if self._swaps >= self.cap:
            hit = [r is not None and loop_target(c) for r, c in zip(ranks, items)]
            n = sum(hit)
            ranks = [DEMOTED_RANK if x else r for r, x in zip(ranks, hit)]
            if n:
                self.loop_counts["choices_with_swap_cap"] += 1
        return ranks, "rule5", note + (f":swap_cap{n}" if n else "")

    def loop_summary(self) -> dict[str, Any]:
        return {**TRANSITION_DEFERRAL, "swap_cap": self.swap_cap, "counts": dict(sorted(self.loop_counts.items()))}


# ---------------------------------------------------------------- rules-v6（試験の方策）: rules-v5 に、確認した［エナジートランス］の往復の移動だけを後回しにする規則を加える
# （docs/tr8-energy-trans-loop-analysis.md 6 章の案 B・docs/tr8-energy-trans-loop-experiment.md）。rules-v5 の［ダメージスワップ］の周期の検出・後回し・6 回の
# 上限、rules-v2 の順位・同順位の選び方・入力単位の再送抑止はそのまま。［エナジートランス］には回数による順位の変更を入れない。候補を消さず、合法性を判定しない

RULES6_VERSION = 6
RULES6_DISTRIBUTION = "rules-v6-candidate+uniform-stage"
ENERGY_TRANS_NAMES = ("エナジートランス",)  # 後回しの対象の特殊能力（候補の power.name_ja。公開の値）
ENERGY_TRANS_DEFERRAL = {"version": 1, "kind": LOOP_KIND, "powers": list(ENERGY_TRANS_NAMES),
                         "key": "(pre-move own view, source pokemon, energy card, target pokemon), directed; holder excluded",
                         "detection": "same actor, same turn, run of accepted Energy Trans (any holder), own view returns; latest match",
                         "inputs": "3 stages source -> energy -> target (actions.transfer_moves); references are pokemon numbers and the energy card number",
                         "effect": "deferred moves removed from the input choices at that view; candidate rank 7 (after end_turn) only when every buildable move "
                                   "of the holder at the view is deferred; restriction lifted when only rank-7 candidates remain",
                         "count_demotion": None, "unknown_moves": "no restriction", "run_cut": "any other accepted operation (either actor)",
                         "keep": "deferred moves kept until the turn changes", "reset": "turn change"}


def et_target(candidate: dict[str, Any]) -> bool:
    """後回しの対象（［エナジートランス］の宣言の候補）か。"""
    return (isinstance(candidate, dict) and candidate.get("kind") == LOOP_KIND
            and (candidate.get("power") or {}).get("name_ja") in ENERGY_TRANS_NAMES)


def et_holder_of(candidate: dict[str, Any]) -> str | None:
    """持ち主の候補の見分け（順位・エピソードの記録だけに使う。後回しの鍵には入れない）。場のポケモンの番号がなければ None。"""
    holder = holder_of(candidate)
    return None if holder is None else "et:" + holder


def transfer_of(meaning: list[dict[str, Any]]) -> tuple[int, int, int] | None:
    """受理した入力の意味の（移動元の場のポケモンの番号, エネルギーのカードの番号, 移動先の番号）。3 段で参照が整数でなければ None（記録しない）。"""
    if not isinstance(meaning, list) or len(meaning) != 3 or [m.get("stage") for m in meaning] != [1, 2, 3]:
        return None
    o = [m.get("option") or {} for m in meaning]
    refs = (o[0].get("pokemon"), o[1].get("card"), o[2].get("pokemon"))
    return refs if all(type(r) is int for r in refs) else None


class EnergyTransRulePolicy(SwapCapRulePolicy):
    """rules-v6: rules-v5 に、同じ番の本人の［エナジートランス］の受理だけが続いた区間で本人の観測が以前の観測に戻ったとき、直近の一致から今回の受理までの
    各移動を（操作前の本人の観測, 移動元, エネルギーのカード, 移動先）で記録し、その観測でだけ入力から外す規則を加える（持ち主は鍵に入れない）。

    - 区間: 本人の受理が［エナジートランス］（持ち主を問わない）で、次の本人の観測までにほかの受理がない（通し番号が続く）あいだ。ほかの操作・ほかの主体の受理で切る
    - 拒否・入力を作れない・送信の抑止・後回しで組み立てなかった試みでは観測を取らず、履歴を進めない
    - 記録した移動は番の終わりまで保つ。番が変われば区間と記録の両方を消す
    - 入力の応答の組（``actions.transfer_moves``）が取れないとき・照合できないときは外さない（推測で除外しない）
    - 今の観測で持ち主の組み立てられる移動がすべて外れたら、その候補を順位 7 にする。順位 7 の候補しか残らなければ、その試みは制限を外す（rules-v2 の再送抑止のまま）
    - ［ダメージスワップ］の規則（rules-v4 の 2 段の鍵・rules-v5 の 6 回）はそのまま。［エナジートランス］には回数による順位の変更を入れない"""

    def __init__(self, seed: str, distribution: str = STAGE, *, threshold: int = REPEAT_THRESHOLD, cap: int = SWAP_CAP):
        super().__init__(seed, STAGE, threshold=threshold, cap=cap)
        self.version = RULES6_VERSION
        self.distribution = RULES6_DISTRIBUTION
        self.energy_trans_deferral = ENERGY_TRANS_DEFERRAL
        self._et_turn = None
        self._et_run: dict[str, Any] | None = None
        self._et_pending: dict[str, Any] | None = None
        self._et_deferred: set[tuple] = set()  # (観測, 移動元, エネルギー, 移動先)
        self._et_moves: dict[tuple, frozenset] = {}  # (観測, 持ち主) → 組み立てられる移動
        self._et_episode_deferred: set[str] = set()
        self._et_demoted_now: set[str] = set()
        self._et_lifted: str | None = None
        self._et_detection: dict[str, Any] | None = None

    # -- 観測と検出（rules-v4 と同じ形。区間は［エナジートランス］の受理）
    def observe_view(self, view: dict[str, Any], position: int) -> None:
        super().observe_view(view, position)  # rules-v4 の self._sig・self._turn を更新する
        sig = self._sig
        if self._turn != self._et_turn:
            if self._et_deferred:
                self.loop_counts["et_turn_resets_with_deferral"] += 1
            self._et_turn, self._et_run, self._et_pending, self._et_deferred, self._et_moves = self._turn, None, None, set(), {}
        pending, self._et_pending, self._et_detection = self._et_pending, None, None
        if pending is not None and pending["target"] and pending["position"] == position and self._et_run is not None:
            run = self._et_run
            run["moves"].append(pending["move"])
            if sig is None:
                run["valid"] = False
                self.loop_counts["et_runs_without_view"] += 1
            if run["valid"]:
                matched = [i for i, v in enumerate(run["views"]) if v == sig]
                if matched:
                    j = matched[-1]
                    new = []
                    for k in range(j, len(run["moves"])):
                        move = run["moves"][k]
                        if move is None:
                            self.loop_counts["et_keys_missing_ref"] += 1
                            continue
                        key = (run["views"][k], *move)
                        if key not in self._et_deferred:
                            self._et_deferred.add(key)
                            new.append(key)
                    self.loop_counts["et_detections"] += 1
                    self.loop_counts["et_deferred_keys"] += len(new)
                    self._et_detection = {"position": position, "turn": list(self._turn) if self._turn is not None else None, "returned_to": j,
                                          "run_accepts": len(run["moves"]), "cycle_length": len(run["moves"]) - j, "view": short_key(sig),
                                          "newly_deferred": [{"view": short_key(k[0]), "move": [k[1], k[2], k[3]]} for k in new],
                                          "deferred_this_turn": len(self._et_deferred)}
            run["views"].append(sig)
        else:  # 区間の始め（番の始め・ほかの操作の受理・ほかの主体の受理・最初の観測）
            self._et_run = {"views": [sig], "moves": [], "valid": sig is not None}

    def accepted_input(self, candidate: dict[str, Any], meaning: list[dict[str, Any]], position: int) -> None:
        super().accepted_input(candidate, meaning, position)
        target = et_target(candidate)
        self._et_pending = {"position": position, "target": target, "move": transfer_of(meaning) if target else None}

    # -- 組の写しと入力の制限
    def _et_deferred_moves(self) -> frozenset:
        return frozenset((s, e, t) for v, s, e, t in self._et_deferred if v == self._sig)

    def observe_inputs(self, candidate: dict[str, Any], stages: list[dict[str, Any]], allowed) -> None:
        if not et_target(candidate):
            return super().observe_inputs(candidate, stages, allowed)
        from .actions import DEEP_PROCESSABILITY, transfer_moves
        holder = et_holder_of(candidate)
        if holder is None or self._sig is None or frozenset(allowed) != DEEP_PROCESSABILITY:
            return None
        moves = transfer_moves(stages, allowed)
        if moves is None:
            return None
        old = self._et_moves.get((self._sig, holder))
        if old is not None and old != moves:
            self.loop_counts["et_moves_cache_mismatch"] += 1
        self._et_moves[(self._sig, holder)] = moves
        return None

    def input_restriction(self, candidate: dict[str, Any], stages: list[dict[str, Any]], allowed):
        if not et_target(candidate):
            return super().input_restriction(candidate, stages, allowed)
        from .actions import DEEP_PROCESSABILITY, transfer_moves
        self.last_restriction = None
        holder = et_holder_of(candidate)
        if holder is None or self._sig is None:
            return None
        deferred = self._et_deferred_moves()
        if not deferred:
            return None
        record = {"rule": "energy_trans", "view": short_key(self._sig), "holder": short_key(holder), "deferred_at_view": sorted([list(m) for m in deferred])}
        self.last_restriction = record
        if self._et_lifted == holder:
            record["result"] = "lifted_no_alternative"
            self.loop_counts["et_restrictions_lifted"] += 1
            return None
        moves = transfer_moves(stages, allowed) if frozenset(allowed) == DEEP_PROCESSABILITY else None
        if moves is None:
            record["result"] = "restriction_unavailable"
            self.loop_counts["et_restriction_unavailable"] += 1
            return None
        excluded = deferred & moves
        record.update({"moves": len(moves), "excluded": sorted([list(m) for m in excluded])})
        if not moves - deferred:
            record["result"] = DEFER_ALL
            self._et_episode_deferred.add(holder)
            self.loop_counts["et_deferred_all_after_inputs"] += 1
            return DEFER_ALL
        if not excluded:
            record["result"] = "no_deferred_move_buildable"
            return None
        record["result"] = "restricted"
        self.loop_counts["et_restricted_builds"] += 1
        return frozenset(excluded)

    # -- 候補の順位
    def begin_episode(self) -> dict[str, Any]:
        info = super().begin_episode()
        self._et_episode_deferred, self._et_lifted, self._et_demoted_now = set(), None, set()
        if self._et_detection is not None:
            info["et_detection"] = dict(self._et_detection)
        if self._et_deferred:
            info["et_deferred"] = len(self._et_deferred)
        return info

    def _et_all_deferred(self, holder: str) -> bool:
        if holder in self._et_episode_deferred:
            return True
        deferred = self._et_deferred_moves()
        moves = self._et_moves.get((self._sig, holder))
        return bool(deferred) and moves is not None and moves <= deferred

    def _adjust_ranks(self, items, ranks, prefix) -> tuple[list, str, str]:
        ranks, _, note = super()._adjust_ranks(items, ranks, prefix)
        holders = [et_holder_of(c) if r is not None and et_target(c) else None for r, c in zip(ranks, items)]
        hit = [h is not None and self._et_all_deferred(h) for h in holders]
        self._et_demoted_now = {h for h, x in zip(holders, hit) if x}
        ranks = [DEMOTED_RANK if x else r for r, x in zip(ranks, hit)]
        n = sum(hit)
        if n:
            self.loop_counts["et_choices_with_deferred_all"] += 1
        return ranks, "rule6", note + (f":et_deferred_all{n}" if n else "")

    def _rule_candidate(self, items, context) -> tuple[int, str]:
        self._et_lifted = None
        index, reason = super()._rule_candidate(items, context)
        chosen = items[index]
        holder = et_holder_of(chosen) if isinstance(chosen, dict) and et_target(chosen) else None
        if holder is not None and holder in self._et_demoted_now and ":demoted:" in reason:
            self._et_lifted = holder
            self.loop_counts["et_no_alternative"] += 1
            reason += ":et_no_alternative"
        return index, reason

    def loop_summary(self) -> dict[str, Any]:
        return {**TRANSITION_DEFERRAL, "swap_cap": self.swap_cap, "energy_trans_deferral": self.energy_trans_deferral,
                "counts": dict(sorted(self.loop_counts.items()))}


# ---------------------------------------------------------------- rules-v7（試験の方策）: rules-v6 に、支払い条件が変わらない「にげる」を、その番の残りで後回しにする規則を加える
# （docs/tr8-retreat-input-build-analysis.md 6 章・docs/tr8-retreat-reselection-experiment.md）。rules-v6 の［エナジートランス］・rules-v5 の［ダメージスワップ］の規則、
# rules-v2 の順位・同順位の選び方・入力単位の再送抑止はそのまま。候補を消さず、合法性・支払いの可否を判定しない（組み立ての失敗を記憶して順位だけを変える）

RULES7_VERSION = 7
RULES7_DISTRIBUTION = "rules-v7-candidate+uniform-stage"
RETREAT_KIND = "retreat"
RETREAT_FAILURE = "total_units_unreachable"  # 記憶するのは、この理由の組み立ての失敗だけ（ほかの理由の失敗では順位を変えない）
RETREAT_DEFERRAL = {"version": 1, "kind": RETREAT_KIND, "failure": RETREAT_FAILURE,
                    "record": "own retreat build failed with total_units_unreachable in the own (segment, turn): (payment-condition view key, retreat candidate identity)",
                    "key": "own view response (outside identifiers removed) with only the energy / energy_units / energy_units_determined of the own bench Pokemon removed; "
                           "everything else kept: own active (pokemon, form, evolution stack, attached energy cards and units, trainers, markers, special conditions, "
                           "persistent effects, powers), own bench Pokemon (identity, form, powers, trainers, markers), hand, opponent side, stadium, field effects, turn",
                    "effect": f"retreat candidates whose (key, identity) was recorded rank {DEMOTED_RANK} (after end_turn); candidate kept; when only rank {DEMOTED_RANK} "
                              "remains it is chosen as in rules-v2 (:retreat_no_alternative)",
                    "not_applicable": "view unavailable, own active missing or its energy units not determined, or the failed inputs have no discard stage with "
                                      "total_units: not recorded (normal rank)",
                    "reenable": "key differs (active energy / units, active Pokemon, special conditions, markers, effects, stadium, opponent, bench identity, hand, ...)",
                    "keep": "bench-only energy moves keep the key", "reset": "turn change"}
BENCH_PAYMENT_OUTSIDE = ("energy", "energy_units", "energy_units_determined")  # 支払いに使えない、本人のベンチのポケモンのエネルギーだけを鍵から除く


def retreat_payment_key(view: dict[str, Any]) -> tuple[str | None, str | None]:
    """「にげる」の支払い条件の鍵（本人の観測の応答から。公開の値と本人に見える値だけ）。取れなければ (None, 理由)。

    除くのは本人のベンチのポケモンのエネルギー（``BENCH_PAYMENT_OUTSIDE``）だけ。バトル場の個体・ついているカードと単位・特殊状態・マーカー・持続効果・
    ベンチの個体と特殊能力・相手の場・スタジアム・場の効果は残すので、費用・交代先の適格性を変えうる変化はどれも鍵を変える（推測で同じとみなさない）。"""
    if not isinstance(view, dict) or not view.get("ok") or not isinstance(view.get("observation"), dict):
        return None, "view_unavailable"
    obs = view["observation"]
    me = obs.get("viewer", view.get("viewer"))
    players = obs.get("players")
    if me is None or not isinstance(players, list):
        return None, "own_player_unknown"
    own = [p for p in players if isinstance(p, dict) and p.get("player") == me]
    if len(own) != 1:
        return None, "own_player_unknown"
    active = own[0].get("active")
    if not isinstance(active, dict):
        return None, "own_active_missing"
    if active.get("energy_units_determined") is not True or not isinstance(active.get("energy_units"), list):
        return None, "active_energy_units_undetermined"
    bench = own[0].get("bench")
    if not isinstance(bench, list) or not all(isinstance(b, dict) for b in bench):
        return None, "own_bench_unknown"
    stripped = copy.deepcopy({k: v for k, v in view.items() if k not in VIEW_OUTSIDE_FIELDS})
    for p in stripped["observation"]["players"]:
        if isinstance(p, dict) and p.get("player") == me:
            p["bench"] = [{k: v for k, v in b.items() if k not in BENCH_PAYMENT_OUTSIDE} for b in p["bench"]]
    return _canon(stripped), None


def retreat_failure_inputs(stages: list[dict[str, Any]]) -> dict[str, Any] | None:
    """組み立てに失敗した「にげる」の inputs の要点（記録だけ。順位の判定には使わない）。トラッシュの段に total_units がなければ None。"""
    discard = [s for s in stages or [] if isinstance(s, dict) and s.get("role") == "discard" and isinstance(s.get("total_units"), dict)]
    if len(discard) != 1:
        return None
    d = discard[0]
    targets = [s for s in stages if isinstance(s, dict) and s.get("role") == "new_active"]
    return {"total_units": [d["total_units"].get("min"), d["total_units"].get("max")], "count": [(d.get("count") or {}).get("min"), (d.get("count") or {}).get("max")],
            "option_units": sorted(o.get("units") for o in d.get("options") or [] if isinstance(o, dict)),
            "new_active_options": len((targets[0].get("options") or [])) if len(targets) == 1 else None}


class RetreatDeferralRulePolicy(EnergyTransRulePolicy):
    """rules-v7: rules-v6 に、本人の「にげる」の入力の組み立てが ``total_units_unreachable`` で失敗したとき、その番の (支払い条件の鍵, 候補) を記録し、
    同じ鍵・同じ候補のあいだは「にげる」の候補を ``DEMOTED_RANK``（end_turn より後ろ）に置く規則を加える。

    - ランナーの差し込み口 ``retreat_build_failed(candidate, stages, reason, stage)``: 組み立ての失敗のあと（この方策だけが持つ）。記録したかどうかの値を返す
    - 鍵（``retreat_payment_key``）は本人のエピソードの始めの観測から作る。本人のベンチのポケモンのエネルギーだけを除くので、ベンチの間だけの移動では鍵が変わらない
    - 鍵が取れない・トラッシュの段の形が違う失敗は記録しない（適用外として数える）。ほかの理由の失敗・ほかの種類の候補では記録しない
    - 番（本人の観測の（区間, 番））が変われば記録を消す。順位 7 の候補しか残らなければ rules-v2 と同じく順位 7 の中から選ぶ（:retreat_no_alternative）"""

    def __init__(self, seed: str, distribution: str = STAGE, *, threshold: int = REPEAT_THRESHOLD, cap: int = SWAP_CAP):
        super().__init__(seed, STAGE, threshold=threshold, cap=cap)
        self.version = RULES7_VERSION
        self.distribution = RULES7_DISTRIBUTION
        self.retreat_deferral = RETREAT_DEFERRAL
        self._rt_turn = None
        self._rt_key: str | None = None
        self._rt_key_missing: str | None = None
        self._rt_deferred: dict[tuple, dict[str, Any]] = {}  # (鍵, 候補) → 記録
        self._rt_demoted_now = False
        self.last_retreat: dict[str, Any] | None = None

    def observe_view(self, view: dict[str, Any], position: int) -> None:
        super().observe_view(view, position)
        if self._turn != self._rt_turn:
            if self._rt_deferred:
                self.loop_counts["retreat_turn_resets_with_deferral"] += 1
            self._rt_turn, self._rt_deferred = self._turn, {}
        self._rt_key, self._rt_key_missing = retreat_payment_key(view)

    def retreat_build_failed(self, candidate: dict[str, Any], stages: list[dict[str, Any]], reason: str, stage) -> dict[str, Any] | None:
        self.last_retreat = None
        if not isinstance(candidate, dict) or candidate.get("kind") != RETREAT_KIND:
            return None
        if reason != RETREAT_FAILURE:
            self.loop_counts["retreat_failures_other_reason"] += 1
            self.last_retreat = {"result": "not_recorded:other_reason", "reason": reason}
            return self.last_retreat
        inputs = retreat_failure_inputs(stages)
        why = self._rt_key_missing if self._rt_key is None else (None if inputs is not None else "inputs_unrecognized")
        if why is not None:
            self.loop_counts[f"retreat_not_applicable:{why}"] += 1
            self.last_retreat = {"result": "not_applicable", "why": why}
            return self.last_retreat
        slot = (self._rt_key, candidate_identity(candidate))
        new = slot not in self._rt_deferred
        if new:
            self._rt_deferred[slot] = {"key": short_key(slot[0]), "candidate": short_key(slot[1]), "stage": stage, **inputs}
            self.loop_counts["retreat_failures_recorded"] += 1
        else:
            self.loop_counts["retreat_failures_same_key_again"] += 1  # 順位 7 しか残らず選ばれた・同じ鍵の別の候補の形など
        self.last_retreat = {"result": "recorded" if new else "already_recorded", **self._rt_deferred[slot], "deferred_this_turn": len(self._rt_deferred)}
        return self.last_retreat

    def begin_episode(self) -> dict[str, Any]:
        info = super().begin_episode()
        self._rt_demoted_now = False
        if self._rt_deferred:
            info["retreat_deferred"] = {"recorded_this_turn": len(self._rt_deferred), "key_now": short_key(self._rt_key) if self._rt_key is not None else None,
                                        "key_now_missing": self._rt_key_missing,
                                        "same_key_recorded": any(k == self._rt_key for k, _c in self._rt_deferred)}
        return info

    def _adjust_ranks(self, items, ranks, prefix) -> tuple[list, str, str]:
        ranks, _, note = super()._adjust_ranks(items, ranks, prefix)
        hit = [r is not None and isinstance(c, dict) and c.get("kind") == RETREAT_KIND and self._rt_key is not None
               and (self._rt_key, candidate_identity(c)) in self._rt_deferred for r, c in zip(ranks, items)]
        n = sum(hit)
        self._rt_demoted_now = bool(n)
        ranks = [DEMOTED_RANK if x else r for r, x in zip(ranks, hit)]
        if n:
            self.loop_counts["retreat_choices_deferred"] += 1
        elif self._rt_deferred and any(isinstance(c, dict) and c.get("kind") == RETREAT_KIND for c in items):
            self.loop_counts["retreat_choices_reenabled" if self._rt_key is not None else "retreat_choices_key_unavailable"] += 1
        return ranks, "rule7", note + (f":retreat_deferred{n}" if n else "")

    def _rule_candidate(self, items, context) -> tuple[int, str]:
        index, reason = super()._rule_candidate(items, context)
        chosen = items[index]
        if self._rt_demoted_now and isinstance(chosen, dict) and chosen.get("kind") == RETREAT_KIND and ":demoted:" in reason:
            self.loop_counts["retreat_no_alternative"] += 1
            reason += ":retreat_no_alternative"
        return index, reason

    def loop_summary(self) -> dict[str, Any]:
        return {**TRANSITION_DEFERRAL, "swap_cap": self.swap_cap, "energy_trans_deferral": self.energy_trans_deferral, "retreat_deferral": self.retreat_deferral,
                "counts": dict(sorted(self.loop_counts.items()))}


# ---------------------------------------------------------------- rules-v8（試験の方策）: rules-v7 に、［エナジートランス］の入力で、バトル場のワザ・「にげる」の費用に近づく移動を優先する規則を加える
# （docs/tr8-energy-trans-progress-policy-design.md・docs/tr8-energy-trans-progress-policy-experiment.md）。変えるのは、既存の順位で［エナジートランス］を選んだあとの
# 入力の選び方だけ（候補の順位・rules-v7 の「にげる」の後回し・rules-v6 の往復の後回し・rules-v5 の［ダメージスワップ］の上限・同順位の抽選はそのまま）。
# 費用は静的に評価するだけで、操作できる・受理されるとは見なさない（次の候補・check・submit で確かめる）。評価できなければ rules-v7 と同じ選び方に戻す

RULES8_VERSION = 8
RULES8_DISTRIBUTION = "rules-v8-candidate+uniform-stage"
SLEEP_PARALYSIS = ("sleep", "paralysis")  # 観測の special_conditions の名前（ねむり・マヒ）。バトル場がこの状態なら、ワザ・「にげる」の目標を評価しない
PROGRESS_SEARCH_LIMIT = 4_096  # 不足の探索で調べる、足すカードの組（色ごとの枚数の組）の数の上限（超えたら評価しない）
ENERGY_TRANS_PROGRESS = {
    "version": 1, "kind": LOOP_KIND, "powers": list(ENERGY_TRANS_NAMES),
    "order": ["rules-v6 deferred moves removed first (existing restriction)",
              "tier 1: after the move an unmet goal (own active's printed attack or retreat) is met",
              "tier 2: the move reduces the deficit of a goal confirmed reachable",
              "tier 3: otherwise, or nothing evaluable: the rules-v7 choice"],
    "reachability": "from every buildable move of the inputs before the rules-v6 exclusion; the choice is made from the moves after it",
    "draw": "the existing stage-wise uniform choice restricted to the chosen tier (build_choices restriction = the moves outside it); no tuple draw; "
            "no new priority between attack and retreat",
    "d1_retreat": "retreat inputs fetched read-only for each retreat candidate presented in the same response when Energy Trans is chosen "
                  "(total_units with modifiers, per-card units); reused only for the same actor, position and candidate; not a retreat selection",
    "d2_attack": "printed cost from the fixed engine card registry, only for attacks of the own active's own printed card (route form, printed form, "
                 "no provider / payer / problem); copies, transformations and unseen modifiers or prohibitions are not evaluated",
    "d3_draw": "transfer_moves + build_choices restriction (stage-wise uniform)",
    "d4_keep_met": "within the chosen tier, moves that keep every currently payable goal payable are preferred; when none, the tier is kept",
    "d5_special": "attack goals only when every card on the active is a basic energy whose type matches the view's units; retreat goals use the per-card "
                  "units of the retreat inputs; a moved card that is not basic energy makes the inputs not evaluable",
    "payment": "attack: colour symbols one unit each (bipartite), colourless by the rest; colourless units never pay colour symbols (cards.can_pay_with_units). "
               "retreat: a subset of the active's cards whose unit sum is within total_units (cards not split; actions._choose_by_units)",
    "not_evaluated": "sleep / paralysis, energy units undetermined, view or inputs unavailable, retreat inputs withheld / refused / cost not evaluated, "
                     "search limit: tier 3 (rules-v7 choice)"}


def _own_player(view: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(view, dict) or not view.get("ok") or not isinstance(view.get("observation"), dict):
        return None
    obs = view["observation"]
    me = obs.get("viewer", view.get("viewer"))
    own = [p for p in obs.get("players") or [] if isinstance(p, dict) and p.get("player") == me]
    return own[0] if len(own) == 1 else None


def can_pay_units(cost: list[str], units: list) -> bool:
    """``kyuura_engine.cards.can_pay_with_units`` と同じ割り当て（道具はエンジンを import しないので同じ規則を持つ）。色の記号には、その色になれる 1 個を 1 つずつ
    割り当て、無色の記号は残りのどの 1 個でも払う。無色の 1 個は色の記号を払えない。"""
    units = [frozenset(u) for u in units]
    if len(units) < len(cost):
        return False
    colored = [c for c in cost if c != "colorless"]
    owner: dict[int, int] = {}

    def assign(symbol: int, seen: set[int]) -> bool:
        for j, kinds in enumerate(units):
            if colored[symbol] in kinds and j not in seen:
                seen.add(j)
                if j not in owner or assign(owner[j], seen):
                    owner[j] = symbol
                    return True
        return False
    return all(assign(i, set()) for i in range(len(colored)))


def retreat_payable(total: tuple[int, int], card_units: list[int]) -> bool:
    """「にげる」の支払いの組があるか: カードの部分集合で、単位の合計が total_units の範囲に入るもの（1 枚で 2 個のカードは分けない）。"""
    lo, hi = total
    sums = {0}
    for u in card_units:
        sums |= {s + u for s in sums}
    return any(lo <= s <= hi for s in sums)


class _Goal:
    """評価する目標（バトル場のワザ 1 つか、「にげる」の候補 1 つ）。``met(extra, removed)`` は、カード（番号 → 単位）を足し・外したあとに費用を満たすか。"""

    def __init__(self, kind: str, label: str, source: str, *, cost=None, units=None, card_units=None, total=None):
        self.kind, self.label, self.source = kind, label, source
        self.cost, self.units = cost, units  # ワザ: 費用の記号・バトル場のカードごとの単位 {番号: [[色]...]}
        self.card_units, self.total = card_units, total  # にげる: バトル場のカードごとの単位の数 {番号: 個}・total_units

    def met(self, extra: list[list[list[str]]], removed: frozenset = frozenset()) -> bool:
        if self.kind == "attack":
            units = [u for card, us in self.units.items() if card not in removed for u in us] + [u for us in extra for u in us]
            return can_pay_units(self.cost, units)
        cards = [n for card, n in self.card_units.items() if card not in removed] + [len(us) for us in extra]
        return retreat_payable(self.total, cards)


def _deficit(goal: _Goal, base_extra: list, movable: list[list[list[str]]]) -> int | None:
    """足りない最小のカード枚数（``movable`` はバトル場へ移せるカードの単位の並び）。足しても満たせなければ None。同じ単位のカードはまとめて数える。
    探索の組が上限を超えたら ``OverflowError``（評価しない）。"""
    groups = Counter(json.dumps(us, sort_keys=True) for us in movable)
    kinds = sorted(groups)
    total = 1
    for k in kinds:
        total *= groups[k] + 1
    if total > PROGRESS_SEARCH_LIMIT:
        raise OverflowError("progress_search_limit")
    best = None
    for counts in itertools.product(*[range(groups[k] + 1) for k in kinds]):
        n = sum(counts)
        if best is not None and n >= best:
            continue
        extra = list(base_extra) + [json.loads(k) for k, c in zip(kinds, counts) for _ in range(c)]
        if goal.met(extra):
            best = n
    return best


class EnergyTransProgressRulePolicy(RetreatDeferralRulePolicy):
    """rules-v8: rules-v7 に、既存の順位で［エナジートランス］を選んだあとの入力（移動元 → エネルギー → 移動先）を、バトル場のワザ・「にげる」の費用に近づく組から
    選ぶ規則を加える（docs/tr8-energy-trans-progress-policy-design.md の D1〜D5 を確定した形）。

    - ランナーの差し込み口（この方策だけが持つ）: ``wants_retreat_inputs(candidate)``（［エナジートランス］を選んだとき真）、
      ``progress_retreat_inputs(items)``（同じ応答の「にげる」の候補の inputs。読み取り専用で取得した値・同じ局面で取得済みの値）、``last_progress``（試みの記録）
    - 入力の制限（``input_restriction``）: rules-v6 の結果（外す組・DEFER_ALL・None）を先に求め、DEFER_ALL ならそのまま返す。残りの組を優先 1・2・3 に分け、
      組がある最上位の段（D4 で、払える費用を保つ組があればその組）だけを残す制限を返す。優先 3 で絞らないときは rules-v6 の結果をそのまま返す（rules-v7 と同じ）
    - 到達できるかは rules-v6 の除外の前の全組から判定し、選ぶのは除外のあとの組から。組を推測で外さない（評価できなければ絞らない）"""

    def __init__(self, seed: str, distribution: str = STAGE, *, threshold: int = REPEAT_THRESHOLD, cap: int = SWAP_CAP,
                 cards: dict[str, dict[str, Any]] | None = None):
        super().__init__(seed, STAGE, threshold=threshold, cap=cap)
        self.version = RULES8_VERSION
        self.distribution = RULES8_DISTRIBUTION
        self.energy_trans_progress = ENERGY_TRANS_PROGRESS
        self._cards = cards or {}
        self._view: dict[str, Any] | None = None
        self._retreat_items: list[dict[str, Any]] = []
        self.last_progress: dict[str, Any] | None = None

    def observe_view(self, view: dict[str, Any], position: int) -> None:
        super().observe_view(view, position)
        self._view = view

    def wants_retreat_inputs(self, candidate: dict[str, Any]) -> bool:
        return et_target(candidate)

    def progress_retreat_inputs(self, items: list[dict[str, Any]]) -> None:
        self._retreat_items = list(items)

    def input_restriction(self, candidate: dict[str, Any], stages: list[dict[str, Any]], allowed):
        base = super().input_restriction(candidate, stages, allowed)
        self.last_progress = None
        if not et_target(candidate):
            return base
        items, self._retreat_items = self._retreat_items, []
        if base == DEFER_ALL:
            return base
        record, restriction = self._progress(stages, allowed, base if isinstance(base, frozenset) else frozenset(), items)
        self.last_progress = record
        self.loop_counts["progress_" + record["result"].split(":")[0]] += 1
        if record["result"].startswith("unevaluable"):
            self.loop_counts["progress_" + record["result"]] += 1
        return base if restriction is None else restriction

    # -- 目標の組み立て
    def _goals(self, active: dict[str, Any], items: list[dict[str, Any]], skipped: Counter) -> list[_Goal]:
        goals: list[_Goal] = []
        cards = self._cards
        attached = [e for e in active.get("energy") or [] if isinstance(e, dict)]
        basic = all((cards.get(e.get("card_id")) or {}).get("basic_energy") for e in attached)
        per_card = {e.get("card"): [[(cards.get(e.get("card_id")) or {}).get("provides")]] for e in attached} if basic else {}
        view_units = sorted(json.dumps(sorted(u)) for u in active.get("energy_units") or [])
        card_units = sorted(json.dumps(us[0]) for us in per_card.values())
        units_match = basic and view_units == card_units
        form = active.get("form") or {}
        for a in active.get("attacks") or []:
            if not isinstance(a, dict):
                continue
            why = None
            if a.get("route") != "form" or form.get("kind") != "printed" or a.get("card_id") != active.get("card_id"):
                why = "attack_not_own_printed"
            elif a.get("provider") is not None or a.get("payer") is not None or a.get("problem") is not None:
                why = "attack_provider_payer_or_problem"
            elif not basic:
                why = "attack_special_energy_on_active"
            elif not units_match:
                why = "attack_units_differ_from_cards"
            else:
                printed = ((cards.get(a.get("card_id")) or {}).get("attacks") or [])
                idx = a.get("attack_index")
                if type(idx) is not int or not 0 <= idx < len(printed):
                    why = "attack_not_in_registry"
            if why is not None:
                skipped[why] += 1
                continue
            goals.append(_Goal("attack", f"attack:{a.get('attack_index')}", "registry", cost=list(printed[idx]), units=per_card))
        for item in items:
            why = item.get("status")
            stages = item.get("stages")
            discard = [s for s in stages or [] if isinstance(s, dict) and s.get("role") == "discard"]
            if why == "ok":
                if len(discard) != 1 or "cost_evaluation" in discard[0] or not isinstance(discard[0].get("total_units"), dict):
                    why = "retreat_discard_unrecognized"
                else:
                    d = discard[0]
                    opts = [o for o in d.get("options") or [] if isinstance(o, dict)]
                    lo, hi = d["total_units"].get("min"), d["total_units"].get("max")
                    if any(type(o.get("units")) is not int or type(o.get("card")) is not int for o in opts) or type(lo) is not int or type(hi) is not int:
                        why = "retreat_units_unrecognized"
                    elif d.get("count") != {"min": 0, "max": len(opts)} and not (lo == 0 and hi == 0):
                        why = "retreat_count_shape"
            if why != "ok":
                skipped[f"retreat_{why}" if not str(why).startswith("retreat_") else why] += 1
                continue
            goals.append(_Goal("retreat", "retreat", item.get("source"), card_units={o["card"]: o["units"] for o in opts}, total=(lo, hi)))
        return goals

    def _progress(self, stages, allowed, excluded: frozenset, items) -> tuple[dict[str, Any], frozenset | None]:
        from .actions import DEEP_PROCESSABILITY, transfer_moves
        skipped: Counter = Counter()

        def out(result, **extra):
            return {"result": result, **extra, **({"skipped": dict(sorted(skipped.items()))} if skipped else {})}, None

        moves = transfer_moves(stages, allowed) if frozenset(allowed) == DEEP_PROCESSABILITY else None
        if moves is None:
            return out("unevaluable:inputs_shape")
        me = _own_player(self._view)
        active = (me or {}).get("active")
        if me is None:
            return out("unevaluable:view_unavailable")
        if not isinstance(active, dict) or type(active.get("pokemon_id")) is not int:
            return out("unevaluable:no_active")
        if active.get("energy_units_determined") is not True or not isinstance(active.get("energy_units"), list):
            return out("unevaluable:active_units_undetermined")
        if any(c in SLEEP_PARALYSIS for c in active.get("special_conditions") or []):
            return out("unevaluable:sleep_or_paralysis")
        aid = active["pokemon_id"]
        card_of = {o.get("card"): o.get("card_id") for o in (stages[1].get("options") or []) if isinstance(o, dict)}
        unit_of = {}
        for _s, e, _t in moves:
            d = self._cards.get(card_of.get(e)) or {}
            if not d.get("basic_energy") or not d.get("provides"):
                return out("unevaluable:moved_card_not_basic")
            unit_of[e] = [[d["provides"]]]
        goals = self._goals(active, items, skipped)
        if not goals:
            return out("unevaluable:no_evaluable_goal", moves=len(moves), excluded_v6=len(excluded & moves))
        movable = {e: unit_of[e] for s, e, t in moves if t == aid and s != aid}  # 到達の判定は rules-v6 の除外の前の全組
        try:
            met_now = [g.met([]) for g in goals]
            deficits = [0 if m else _deficit(g, [], list(movable.values())) for g, m in zip(goals, met_now)]
            choosable = sorted(moves - excluded)
            tiers, keeps = {}, {}
            for move in choosable:
                s, e, t = move
                if t == aid and s != aid:
                    extra, rest = [unit_of[e]], [u for c, u in movable.items() if c != e]
                    if any(not m and g.met(extra) for g, m in zip(goals, met_now)):
                        tiers[move] = 1
                    elif any(not m and d is not None and (a := _deficit(g, extra, rest)) is not None and a < d
                             for g, m, d in zip(goals, met_now, deficits)):
                        tiers[move] = 2
                    else:
                        tiers[move] = 3
                    keeps[move] = all(g.met(extra) for g, m in zip(goals, met_now) if m)
                else:
                    tiers[move] = 3
                    removed = frozenset([e]) if s == aid else frozenset()
                    keeps[move] = all(g.met([], removed) for g, m in zip(goals, met_now) if m)
        except OverflowError:
            return out("unevaluable:search_limit", moves=len(moves))
        sizes = [sum(1 for m in choosable if tiers[m] == k) for k in (1, 2, 3)]
        tier = next(k for k in (1, 2, 3) if sizes[k - 1])
        chosen = [m for m in choosable if tiers[m] == tier]
        d4 = None
        if any(met_now):
            kept = [m for m in chosen if keeps[m]]
            d4 = "kept" if kept and len(kept) < len(chosen) else "all_keep" if kept else "none_keep"
            if kept:
                chosen = kept
        goals_rec = [{"kind": g.kind, "label": g.label, "source": g.source, "met": m, "deficit": d} for g, m, d in zip(goals, met_now, deficits)]
        state = "reachable" if any(not m and d is not None for m, d in zip(met_now, deficits)) else "goal_met_only" if any(met_now) else "unreachable"
        record = {"result": f"tier{tier}", "state": state, "moves": len(moves), "excluded_v6": len(excluded & moves), "choosable": len(choosable),
                  "tier_sizes": sizes, "chosen_set": len(chosen), "d4": d4, "goals": goals_rec,
                  "set": sorted([list(m) for m in chosen]), **({"skipped": dict(sorted(skipped.items()))} if skipped else {})}
        if len(chosen) == len(choosable):
            record["restricted"] = False
            return record, None  # 絞らない: rules-v6 の結果のまま（rules-v7 と同じ選び方）
        record["restricted"] = True
        return record, frozenset(moves - frozenset(chosen))

    def loop_summary(self) -> dict[str, Any]:
        return {**TRANSITION_DEFERRAL, "swap_cap": self.swap_cap, "energy_trans_deferral": self.energy_trans_deferral, "retreat_deferral": self.retreat_deferral,
                "energy_trans_progress": self.energy_trans_progress, "counts": dict(sorted(self.loop_counts.items()))}


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
