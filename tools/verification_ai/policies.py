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
