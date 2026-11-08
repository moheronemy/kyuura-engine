"""行動生成（B）。U7 の ``inputs`` が返す段の契約から、完成した入力（``choices``）を組み立てる（docs/verification-ai-v0.md 3 章）。

読むのは API の契約に書かれた項目だけです（``count``・``range``・``options``・``distinct``・``depends_on_stage``/``options_by_choice``・
``upstream_stages``/``after``・``path_stages``/``options_by_path``・``options_from_stage``/``distinct_across_stages``・``total_units`` と選べるものの
``units``・``eligible``・``processability``）。カード名・カード ID・効果の型による判定は持たず、``kyuura_engine`` を import しません。

- 知らない項目・知らない ``input`` は推測しない: ``ContractUnknown``
- 入力を作れない（選べるものが足りない・経路の鍵がない必須の段・数え上げの上限）: ``Unbuildable``（理由のコードつき）
- 選び方は方策に任せる（``policy.choose``）。均等の方策なら、各段で「前の段の選び方のもとで契約が許す選べるもの」を均等に選ぶ分布になる
"""

from __future__ import annotations

import itertools
from typing import Any

CHOOSE_OPTION = "choose_option"
CHOOSE_VALUE = "choose_value"
# 段の項目（legal_actions.py が作る形。v0.172.0）。ここにない項目は ContractUnknown
STAGE_KEYS = frozenset({
    "stage", "input", "role", "meaning", "count", "range", "options", "order", "order_preserved", "distinct", "decline", "note", "decision_kind", "name",
    "depends_on_stage", "options_by_choice", "upstream_stages", "path_stages", "options_by_path", "options_from_stage", "distinct_across_stages", "total_units",
    "bench", "remaining", "confused",
})
# 入力の組み立てに使う制約の項目（ほかの項目は表示用で、組み立てに使わない）
VALUE_RANGE_LIMIT = 10_000  # choose_value の範囲の大きさの上限（無制限に並べない）
TOTAL_UNITS_COMBINATIONS_LIMIT = 4_096  # total_units の段で調べる組み合わせの数の上限（無制限に列挙しない）

# 深く進める範囲（プロファイル deep。仕様 4.5 節）の処理可能性。unverified は、ほかに進む道がない場面だけ許す（ランナーが決める）
DEEP_PROCESSABILITY = frozenset({"supported", "may_stop_later"})
FALLBACK_PROCESSABILITY = frozenset({"supported", "may_stop_later", "unverified"})


class ContractUnknown(Exception):
    """段の契約に知らない項目・値がある（API が変わった。推測で扱わない）。"""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class Unbuildable(Exception):
    """契約の制約を満たす入力を作れない。"""

    def __init__(self, reason: str, stage: int | None = None):
        super().__init__(f"{reason} (stage {stage})")
        self.reason = reason
        self.stage = stage


def option_allowed(option: dict[str, Any], allowed: frozenset[str]) -> bool:
    """選べるもの（または options_by_choice・options_by_path の参照）が範囲にあるか。``eligible`` が偽・処理可能性が範囲の外なら外す。"""
    if option.get("eligible") is False:
        return False
    proc = option.get("processability")
    return proc is None or proc in allowed


def build_choices(stages: list[dict[str, Any]], policy, context: dict[str, Any], allowed: frozenset[str] = DEEP_PROCESSABILITY):
    """段の順に選び、(choices, picks, meaning) を返す。picks は段ごとの選択の記録（場面・選べる数・選んだ位置・理由）、meaning は入力の意味の表現
    （``meaning_of`` と同じ形。再現の比べに使う）。"""
    choices: list[Any] = []
    picks: list[dict[str, Any]] = []
    meaning: list[dict[str, Any]] = []
    selected: dict[int, list[str]] = {}
    for position, stage in enumerate(stages, 1):
        unknown = sorted(set(stage) - STAGE_KEYS)
        if unknown:
            raise ContractUnknown(f"stage {position}: unknown keys {unknown}")
        number = stage.get("stage")
        if number != position:
            raise ContractUnknown(f"stage number {number!r} at position {position}")
        kind = stage.get("input")
        if kind == CHOOSE_VALUE:
            value = _choose_value(stage, policy, context, picks)
            choices.append(value)
            meaning.append({"stage": number, "value": value})
            selected[number] = []
            continue
        if kind != CHOOSE_OPTION:
            raise ContractUnknown(f"stage {number}: unknown input {kind!r}")
        ids = _choose_options(stages, stage, selected, policy, context, picks, allowed)
        selected[number] = ids
        choices.extend(ids)
        source = stages[stage["options_from_stage"] - 1] if "options_from_stage" in stage else stage
        meaning.extend(meaning_of(number, source, ids))
    return choices, picks, meaning


def _count(stage: dict[str, Any]) -> tuple[int, int]:
    count = stage.get("count")
    if not isinstance(count, dict) or type(count.get("min")) is not int or type(count.get("max")) is not int:
        raise ContractUnknown(f"stage {stage.get('stage')}: count {count!r}")
    return count["min"], count["max"]


def _choose_value(stage, policy, context, picks) -> int:
    lo, hi = stage["range"]["min"], stage["range"]["max"]
    if _count(stage) != (1, 1):
        raise ContractUnknown(f"stage {stage['stage']}: choose_value with count {stage['count']!r}")
    if hi < lo:
        raise Unbuildable("empty_range", stage["stage"])
    if hi - lo + 1 > VALUE_RANGE_LIMIT:
        raise Unbuildable("range_too_large", stage["stage"])
    values = list(range(lo, hi + 1))
    index, reason = policy.choose("value", values, {**context, "stage": stage})
    picks.append({"stage": stage["stage"], "purpose": "value", "items": len(values), "index": index, "reason": reason})
    return values[index]


def _allowed_ids(stages, stage, selected, allowed) -> list[str]:
    """契約が今の部分の入力に許す選べるもの（API の並びのまま）。"""
    number = stage["stage"]
    source = stage
    if "options_from_stage" in stage:
        source = stages[stage["options_from_stage"] - 1]
    options = source.get("options", [])
    by_id = {o["id"]: o for o in options}
    if "path_stages" in stage or "options_by_path" in stage:
        key = "/".join(selected.get(s, [""])[0] if len(selected.get(s, [])) == 1 else "" for s in stage["path_stages"])
        refs = stage["options_by_path"].get(key)
        if refs is None:
            return []  # この組では選べない（任意の段なら 0 個だけ）
        ids = [r["option"] for r in refs if option_allowed(r, allowed) and option_allowed(by_id[r["option"]], allowed)]
    elif "depends_on_stage" in stage:
        before = selected.get(stage["depends_on_stage"], [])
        if len(before) != 1:
            raise ContractUnknown(f"stage {number}: depends on stage {stage['depends_on_stage']} with {len(before)} choices")
        refs = stage.get("options_by_choice", {}).get(before[0], [])
        ids = [r["option"] for r in refs if option_allowed(r, allowed) and option_allowed(by_id[r["option"]], allowed)]
        if "upstream_stages" in stage:
            ids = [i for i in ids if by_id[i].get("after") == before[0]]
    else:
        ids = [o["id"] for o in options if option_allowed(o, allowed)]
    if stage.get("distinct_across_stages"):
        used = {i for s, chosen in selected.items() for i in chosen}
        ids = [i for i in ids if i not in used]
    return ids


def _choose_options(stages, stage, selected, policy, context, picks, allowed) -> list[str]:
    number = stage["stage"]
    lo, hi = _count(stage)
    ids = _allowed_ids(stages, stage, selected, allowed)
    sub = {**context, "stage": stage}
    if "total_units" in stage:
        return _choose_by_units(stage, ids, lo, hi, policy, sub, picks)
    top = min(hi, len(ids))
    if top < lo:
        raise Unbuildable("not_enough_options", number)
    ks = list(range(lo, top + 1))
    k = ks[0]
    if len(ks) > 1:
        index, reason = policy.choose("count", ks, sub)
        picks.append({"stage": number, "purpose": "count", "items": len(ks), "index": index, "reason": reason})
        k = ks[index]
    return _ordered_pick(number, ids, k, policy, sub, picks)


def _ordered_pick(number, ids, k, policy, context, picks) -> list[str]:
    """重ならずに k 個を順に均等に選ぶ（選んだ順が送る並び）。"""
    remaining, out = list(ids), []
    for _ in range(k):
        index, reason = policy.choose("option", remaining, context)
        picks.append({"stage": number, "purpose": "option", "items": len(remaining), "index": index, "reason": reason})
        out.append(remaining.pop(index))
    return out


def _choose_by_units(stage, ids, lo, hi, policy, context, picks) -> list[str]:
    """total_units の段: 契約の units の合計が範囲に入る組だけから選ぶ（選ぶ数 k → 組 → 並び）。組の数え上げは上限つき。"""
    number = stage["stage"]
    units = {o["id"]: o.get("units") for o in stage.get("options", [])}
    if any(type(units.get(i)) is not int for i in ids):
        raise ContractUnknown(f"stage {number}: total_units without integer units")
    low, high = stage["total_units"]["min"], stage["total_units"]["max"]
    groups: dict[int, list[tuple[str, ...]]] = {}
    examined = 0
    for k in range(lo, min(hi, len(ids)) + 1):
        for combo in itertools.combinations(ids, k):
            examined += 1
            if examined > TOTAL_UNITS_COMBINATIONS_LIMIT:
                raise Unbuildable("combinations_limit", number)
            if low <= sum(units[i] for i in combo) <= high:
                groups.setdefault(k, []).append(combo)
    if not groups:
        raise Unbuildable("total_units_unreachable", number)
    ks = sorted(groups)
    k = ks[0]
    if len(ks) > 1:
        index, reason = policy.choose("count", ks, context)
        picks.append({"stage": number, "purpose": "count", "items": len(ks), "index": index, "reason": reason})
        k = ks[index]
    combos = groups[k]
    combo = combos[0]
    if len(combos) > 1:
        index, reason = policy.choose("units_set", combos, context)
        picks.append({"stage": number, "purpose": "units_set", "items": len(combos), "index": index, "reason": reason})
        combo = combos[index]
    return _ordered_pick(number, list(combo), k, policy, context, picks)


def meaning_of(number: int, source: dict[str, Any], ids: list[str]) -> list[dict[str, Any]]:
    """選んだ番号の意味の表現: 段の番号と、その選べるものの中身から応答ごとの番号（``id``・``after``）だけを除いたもの。

    カード・場のポケモン・ワザ・処理可能性などの中身はすべて残す（比べで差を隠さない）。番号は応答ごとの値なので、意味の比べには使わない。"""
    by_id = {o["id"]: o for o in source.get("options", [])}
    return [{"stage": number, "option": {k: v for k, v in by_id[i].items() if k not in ("id", "after")}} for i in ids]
