"""negative の変異（V3-1。docs/verification-ai-v3-1.md 3 章）。正常な要求（check が valid だった取っ手・候補・入力）の写しから、1 つの条件だけを変えた不正な入力を作る。

純粋な関数だけで、JSON の値（候補・段・入力）だけを読みます。``kyuura_engine`` を import しません。変異の位置・種類の選び方は方策・ゲームと別の乱数（``negative_rng``）を使います。

- 入力の中身を変える変異（``unknown_option``・``duplicate``・``count_over``・``count_under``・``path_mix``・``non_executable``）は、変える前と後の入力と、変えた場所を返す。前提を
  満たさなければ ``None`` と理由（not_applicable）を返し、無理に作らない
- 取っ手を変える変異（``wrong_actor``・``stale_after_accept``）は入力を変えない（送り先の入口・送る時点だけが違う）。ランナーの側の接点が送る
"""

from __future__ import annotations

import random
from typing import Any

INPUT_MUTATIONS = ("unknown_option", "duplicate", "count_over", "count_under", "path_mix", "non_executable")
HANDLE_MUTATIONS = ("wrong_actor", "stale_after_accept")
MUTATION_TYPES = INPUT_MUTATIONS + HANDLE_MUTATIONS
# V3-2（docs/verification-ai-v3-2.md 3 章）: V3-1 の種類は変えずに加える
V3_2_INPUT_MUTATIONS = ("path_mix_path", "duplicate_replace")
V3_2_TYPES = ("unknown_option", "count_over", "count_under", "path_mix", "path_mix_path", "duplicate_replace", "non_executable", "wrong_actor",
              "stale_after_accept")
# 期待のコード（check と submit の両方。client_api の refetch_required の期待）
EXPECTED = {
    "unknown_option": ("CANDIDATE_INPUT_INVALID", False),
    "duplicate": ("CANDIDATE_INPUT_INVALID", False),
    "count_over": ("CANDIDATE_INPUT_INVALID", False),
    "count_under": ("CANDIDATE_INPUT_INVALID", False),
    "path_mix": ("CANDIDATE_INPUT_INVALID", False),
    "non_executable": ("CANDIDATE_NOT_EXECUTABLE", False),
    "wrong_actor": ("CANDIDATES_WRONG_ACTOR", True),
    "stale_after_accept": ("CANDIDATES_STALE", True),
    "path_mix_path": ("CANDIDATE_INPUT_INVALID", False),
    "duplicate_replace": ("CANDIDATE_INPUT_INVALID", False),
}
EXECUTABLE = frozenset({"supported", "may_stop_later", "unverified"})


def negative_rng(seed: int) -> random.Random:
    """変異の位置・種類を選ぶ乱数（方策の乱数・ゲームの乱数と別）。"""
    return random.Random(f"kyuura-vai-v3:negative:{seed}")


def plan_positions(seed: int, count: int, low: int, high: int) -> list[int]:
    """変異を試す状態（受理の番号 low〜high−1）を、対戦の前に決める（結果を見て変えない）。"""
    return sorted(negative_rng(seed).sample(range(low, high), count))


def _segments(stages: list[dict[str, Any]], choices: list[Any]) -> list[tuple[int, int]] | None:
    """入力を段ごとの（始め, 終わり）に分ける。選ぶものの番号がどの段のものかで分ける（options_from_stage の段は参照する段の番号を使う）。分けられなければ None。"""
    owner: dict[str, int] = {}
    for s in stages:
        source = stages[s["options_from_stage"] - 1] if "options_from_stage" in s else s
        for o in source.get("options", []):
            owner.setdefault(o["id"], s["stage"])
    spans, start = [], 0
    stage_of = []
    for c in choices:
        if not isinstance(c, str):
            return None
        stage_of.append(owner.get(c))
    for s in stages:
        n = s["stage"]
        if "options_from_stage" in s:  # 初期配置: 1 つめがバトル場、残りがベンチ
            spans.append((start, len(choices)))
            start = len(choices)
            continue
        end = start
        while end < len(choices) and stage_of[end] == n:
            end += 1
        spans.append((start, end))
        start = end
    if start != len(choices):
        return None
    return spans


def _option_ids(stages) -> set[str]:
    ids = set()
    for s in stages:
        for o in s.get("options", []):
            ids.add(o["id"])
    return ids


def _executable(option: dict[str, Any]) -> bool:
    return option.get("eligible") is not False and option.get("processability", "supported") in EXECUTABLE


def mutate(kind: str, stages: list[dict[str, Any]], choices: list[Any], rng: random.Random) -> tuple[list[Any] | None, dict[str, Any]]:
    """入力の中身を変える変異を 1 つ作る。(変えた入力 か None, 記録)。記録は変えた段・位置・前後の値、または not_applicable の理由。"""
    if kind not in INPUT_MUTATIONS + V3_2_INPUT_MUTATIONS:
        raise ValueError(kind)
    if not stages or not choices:
        return None, {"not_applicable": "no_input"}
    if any(s.get("input") != "choose_option" for s in stages):
        return None, {"unsupported_contract": "value_stage"}  # V3-3 の訂正: 値の段は生成器が対応していない（前提不足ではない）
    spans = _segments(stages, choices)
    if spans is None or any("options_from_stage" in s for s in stages):
        return None, {"unsupported_contract": "stage_layout_not_mapped"}  # V3-3 の訂正: 初期配置などの段の対応は生成器が対応していない
    return globals()[f"_m_{kind}"](stages, list(choices), spans, rng)


def _replace(choices, index, value) -> list[Any]:
    out = list(choices)
    out[index] = value
    return out


def _m_unknown_option(stages, choices, spans, rng):
    ids = _option_ids(stages)
    n = 1
    while f"o{n}" in ids:
        n += 1
    unknown = f"o{n}"  # この候補のどの段にもない番号
    index = rng.randrange(len(choices))
    return _replace(choices, index, unknown), {"index": index, "before": choices[index], "after": unknown}


def _m_duplicate(stages, choices, spans, rng):
    places = [(s, span) for s, span in zip(stages, spans) if span[1] > span[0] and span[1] - span[0] + 1 <= s["count"]["max"]]
    if not places:
        return None, {"not_applicable": "no_stage_with_room_for_duplicate"}
    stage, (start, end) = places[rng.randrange(len(places))]
    dup = choices[start + rng.randrange(end - start)]
    return choices[:end] + [dup] + choices[end:], {"stage": stage["stage"], "index": end, "inserted": dup}


def _m_count_over(stages, choices, spans, rng):
    stage, (start, end) = stages[-1], spans[-1]
    if end - start != stage["count"]["max"]:
        return None, {"not_applicable": "last_stage_not_at_max"}
    if "path_stages" in stage:
        return None, {"unsupported_contract": "path_stage_references_not_read"}  # V3-3 の訂正: 経路で引く段の参照を読まない（V3-2 では no_extra_option と記録した）
    allowed = _allowed_now(stages, choices, spans, len(stages) - 1)
    extra = [o for o in allowed if o not in choices[start:end]]
    if not extra:
        return None, {"not_applicable": "no_extra_option"}
    pick = extra[rng.randrange(len(extra))]
    return choices + [pick], {"stage": stage["stage"], "index": len(choices), "inserted": pick}


def _m_count_under(stages, choices, spans, rng):
    stage, (start, end) = stages[-1], spans[-1]
    if end - start == 0 or end - start != stage["count"]["min"]:
        return None, {"not_applicable": "last_stage_not_at_min"}
    return choices[:-1], {"stage": stage["stage"], "index": len(choices) - 1, "removed": choices[-1]}


def _allowed_now(stages, choices, spans, k) -> list[str]:
    """k 番目（0 から）の段で、今の前の段の選び方のもとで契約が示す選べるもの（実行できる区分）の番号。"""
    stage = stages[k]
    by_id = {o["id"]: o for o in stage.get("options", [])}
    if "depends_on_stage" in stage:
        prev = choices[spans[k - 1][0]:spans[k - 1][1]]
        if len(prev) != 1:
            return []
        refs = stage.get("options_by_choice", {}).get(prev[0], [])
        return [r["option"] for r in refs if _executable(r) and _executable(by_id.get(r["option"], {}))]
    if "path_stages" in stage:
        return []
    return [o["id"] for o in stage.get("options", []) if _executable(o)]


def _m_path_mix(stages, choices, spans, rng):
    """依存する段で、前の段の別の選び方の参照にだけある選ぶもの（この候補にある番号）にかえる。"""
    places = []
    for k, (stage, (start, end)) in enumerate(zip(stages, spans)):
        if k == 0 or "depends_on_stage" not in stage or end - start != 1:
            continue
        if k + 1 < len(stages) and "depends_on_stage" in stages[k + 1]:
            continue  # 後の段がこの段に依存する: かえると後の段の参照も合わなくなる（1 条件にならない）
        prev = choices[spans[k - 1][0]:spans[k - 1][1]]
        if len(prev) != 1:
            continue
        by_choice = stage.get("options_by_choice", {})
        mine = {r["option"] for r in by_choice.get(prev[0], [])}
        others = sorted({r["option"] for key, refs in by_choice.items() if key != prev[0] for r in refs} - mine)
        if others:
            places.append((stage["stage"], start, others))
    if not places:
        return None, {"not_applicable": "no_other_path_option"}
    number, index, others = places[rng.randrange(len(places))]
    pick = others[rng.randrange(len(others))]
    return _replace(choices, index, pick), {"stage": number, "index": index, "before": choices[index], "after": pick}


def _m_non_executable(stages, choices, spans, rng):
    """同じ段の、API が実行できない区分と示した選ぶもの（前の段の選び方のもとで参照にあるもの）にかえる。"""
    places = []
    for k, (stage, (start, end)) in enumerate(zip(stages, spans)):
        if end - start != 1:
            continue
        by_id = {o["id"]: o for o in stage.get("options", [])}
        if "depends_on_stage" in stage:
            prev = choices[spans[k - 1][0]:spans[k - 1][1]]
            refs = stage.get("options_by_choice", {}).get(prev[0], []) if len(prev) == 1 else []
            bad = [r["option"] for r in refs if not (_executable(r) and _executable(by_id.get(r["option"], {})))]
        elif "path_stages" in stage:
            bad = []
        else:
            bad = [o["id"] for o in stage.get("options", []) if not _executable(o)]
        if k + 1 < len(stages) and "depends_on_stage" in stages[k + 1]:
            bad = []  # 後の段がこの段に依存する: かえると後の段の参照も変わる（1 条件にならない）
        if bad:
            places.append((stage["stage"], start, bad))
    if not places:
        if any("path_stages" in s and e - b == 1 for s, (b, e) in zip(stages, spans)):
            return None, {"unsupported_contract": "path_stage_references_not_read"}  # V3-3 の訂正: 経路で引く段の参照を読まない
        return None, {"not_applicable": "no_non_executable_option"}
    number, index, bad = places[rng.randrange(len(places))]
    pick = bad[rng.randrange(len(bad))]
    return _replace(choices, index, pick), {"stage": number, "index": index, "before": choices[index], "after": pick}


def single_difference(original: list[Any], mutated: list[Any]) -> bool:
    """変えたのが 1 か所だけか（置きかえ 1 つ・加えた 1 つ・除いた 1 つ）。"""
    if len(original) == len(mutated):
        return sum(1 for a, b in zip(original, mutated) if a != b) == 1
    longer, shorter = (mutated, original) if len(mutated) > len(original) else (original, mutated)
    if len(longer) - len(shorter) != 1:
        return False
    return any(longer[:i] + longer[i + 1:] == shorter for i in range(len(longer)))


# ---------------------------------------------------------------- V3-2: options_by_path の別の経路と、個数を保った重複


def _option_of(stages, oid):
    for s in stages:
        for o in s.get("options", []):
            if o["id"] == oid:
                return s["stage"], o
    return None, {}


def _m_path_mix_path(stages, choices, spans, rng):
    """``options_by_path`` の段で、上流の選び方（鍵）を保ち、その鍵の参照にない選ぶもの（ほかの鍵の参照にはある・この段にある番号）にかえる。

    1 条件にするため、次は対象から外す: 後の段がこの段に依存する、この鍵の参照にもある（両方の経路で許される）、上流で選んだものと同じカード（``card``）を指す（同じカードを
    2 回選ぶことにもなり、条件が重なる）、どの鍵の参照でも実行できる区分でない。"""
    found = []
    for k, (stage, (start, end)) in enumerate(zip(stages, spans)):
        if "path_stages" not in stage or end - start != 1:
            continue
        if k + 1 < len(stages) and ("depends_on_stage" in stages[k + 1] or "path_stages" in stages[k + 1]):
            continue
        parts = []
        for s in stage["path_stages"]:
            a, b = spans[s - 1]
            if b - a != 1:
                parts = None
                break
            parts.append(choices[a])
        if parts is None:
            continue
        key = "/".join(parts)
        by_path = stage.get("options_by_path", {})
        mine = {r["option"] for r in by_path.get(key, [])}
        upstream_cards = {(_option_of(stages, c)[1]).get("card") for c in parts} - {None}
        by_id = {o["id"]: o for o in stage.get("options", [])}
        others = sorted({r["option"] for k2, refs in by_path.items() if k2 != key for r in refs if _executable(r)} - mine)
        others = [o for o in others if o in by_id and _executable(by_id[o]) and by_id[o].get("card") not in upstream_cards]
        if others:
            found.append((stage["stage"], start, key, others))
    if not found:
        return None, {"not_applicable": "no_other_path_option_without_overlap"}
    number, index, key, others = found[rng.randrange(len(found))]
    pick = others[rng.randrange(len(others))]
    return _replace(choices, index, pick), {"stage": number, "index": index, "key": key, "before": choices[index], "after": pick}


def _m_duplicate_replace(stages, choices, spans, rng):
    """同じ段（同じ役割）で 2 つ以上選んでいるとき、1 つを、その段の別の選んだものと同じ番号に置きかえる（個数は変えない）。役割の違う段の番号どうしは対象にしない。"""
    places = [(stage["stage"], start, end) for stage, (start, end) in zip(stages, spans) if end - start >= 2]
    if not places:
        return None, {"not_applicable": "no_stage_with_two_choices"}
    number, start, end = places[rng.randrange(len(places))]
    i, j = rng.sample(range(start, end), 2)
    return _replace(choices, j, choices[i]), {"stage": number, "index": j, "before": choices[j], "after": choices[i]}


# ---------------------------------------------------------------- V3-3: 変異の結果の分類（docs/verification-ai-v3-3.md 2 章）

NOT_APPLICABLE = "not_applicable"  # 前提を満たさない（その入力・状態では作れない）
UNSUPPORTED_CONTRACT = "unsupported_contract"  # 生成器がその段の契約に対応していない（前提がないとは言えない）
NOT_RUN = "not_run"  # 予算・位置の選び方・1 つの状態の種類の上限・元の入力が受理されないで試さなかった
RUN = "run"  # 作って送った
OUTCOME_CLASSES = (RUN, NOT_APPLICABLE, UNSUPPORTED_CONTRACT, NOT_RUN)


def outcome_status(change: dict) -> str:
    """``mutate`` が None を返したときの理由の辞書から、記録の状態（not_applicable か unsupported_contract）。"""
    return UNSUPPORTED_CONTRACT if "unsupported_contract" in change else NOT_APPLICABLE
