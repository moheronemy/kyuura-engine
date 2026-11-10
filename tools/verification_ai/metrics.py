"""選択の過程と到達範囲の計測（V1。docs/verification-ai-v1.md 4 章）。

方策の乱数を使わず、ランナーが見た API の応答と結果だけを数えます。数の単位を混ぜないため、次を分けます。

- 「取得ごと」（``*_fetches``）: 候補の取得（``candidates`` の応答）1 回ごとに数える。同じ状態で選び直すと、同じ候補を何回も数える
- 「状態ごと」（``*_states``）: 異なる状態（受理と受理のあいだ。ランナーの ``position``）の数。同じ状態で何回取得しても 1
- 「試みごと」（``selected`` 以降）: 方策が候補を 1 つ選んだ回数と、その後の段階（入力の組み立て・check・submit・結果）

1 つの対戦の中の数です。複数の対戦をまとめるときは対戦の数を別に持ち、再現用の実行を独立した対戦として足しません（``run_v1`` の集計）。
"""

from __future__ import annotations

from typing import Any


def _inc(bucket: dict[str, int], key, n: int = 1) -> None:
    bucket[str(key)] = bucket.get(str(key), 0) + n


def stage_form(stages: list[dict[str, Any]]) -> str:
    """段の形の名前（段の数・入力の種類・選ぶ数・依存の形）。カード・選べるものの中身は入れない。"""
    parts = []
    for s in stages:
        count = s.get("count", {})
        dep = ("path" if "path_stages" in s else "upstream" if "upstream_stages" in s else "choice" if "depends_on_stage" in s
               else "from_stage" if "options_from_stage" in s else "none")
        extra = "+units" if "total_units" in s else ""
        parts.append(f"{s.get('input')}[{count.get('min')}-{count.get('max')}]:{dep}{extra}")
    return f"{len(stages)}|" + ">".join(parts)


class Metrics:
    def __init__(self):
        self.kinds: dict[str, dict[str, Any]] = {}
        self.fetches = 0
        self.states: set[int] = set()
        self.axes: dict[str, dict[str, int]] = {}

    def _kind(self, kind: str) -> dict[str, Any]:
        return self.kinds.setdefault(kind, {
            "offered_fetches": 0, "offered_states": set(), "in_scope_fetches": 0, "in_scope_states": set(), "excluded": {},
            "selection_opportunities": 0, "expected_selections": 0.0, "selected": 0, "build_ok": 0, "build_failed": {}, "build_method": {},
            "already_tried": 0, "policy_suppressed": 0, "check_valid": 0, "check_invalid": 0, "submitted": 0, "outcome": {}, "after_accept": {}})

    def axis(self, name: str, key, n: int = 1) -> None:
        _inc(self.axes.setdefault(name, {}), key, n)

    def fetch(self, position: int, cands: dict[str, Any], in_scope: list[dict[str, Any]], reasons: dict[str, str]) -> None:
        """候補の取得 1 回。``reasons`` は範囲の外にした候補の番号 → 理由。範囲の中の候補は、均等に選ぶとそれぞれ 1/len(in_scope) で選ばれる機会を持つ。"""
        self.fetches += 1
        self.states.add(position)
        self.axis("situation", cands["situation"])
        for c in cands["candidates"]:
            k = self._kind(c["kind"])
            k["offered_fetches"] += 1
            k["offered_states"].add(position)
            self.axis("offered_processability", c.get("processability"))
            self.axis("offered_input_disclosure", c.get("input_disclosure"))
            if c["id"] in reasons:
                _inc(k["excluded"], reasons[c["id"]])
        for item in cands["coverage"]["residual"]["present"]:
            self.axis("residual_present", item["id"])
        if cands.get("empty_reason"):
            self.axis("empty_reason", cands["empty_reason"])
        seen = set()
        for c in in_scope:
            k = self._kind(c["kind"])
            k["in_scope_fetches"] += 1
            k["in_scope_states"].add(position)
            if in_scope:
                k["expected_selections"] += 1 / len(in_scope)
            if c["kind"] not in seen:
                k["selection_opportunities"] += 1  # この種類が範囲にあった取得の回数（範囲の中の候補の数で割る前）
                seen.add(c["kind"])
        self.axis("in_scope_size", len(in_scope))

    def selected(self, candidate: dict[str, Any]) -> None:
        self._kind(candidate["kind"])["selected"] += 1
        self.axis("selected_processability", candidate.get("processability"))

    def built(self, kind: str, stages: list[dict[str, Any]], method: dict[str, Any] | None) -> None:
        k = self._kind(kind)
        k["build_ok"] += 1
        if method is not None:
            _inc(k["build_method"], method["method"] + ("" if method["method"] == "tuple" else f":{method.get('reason')}"))
        self.axis("stage_form", stage_form(stages))
        for s in stages:
            if "decision_kind" in s:
                self.axis("decision_kind", s["decision_kind"])

    def build_failed(self, kind: str, reason: str) -> None:
        _inc(self._kind(kind)["build_failed"], reason)

    def already_tried(self, kind: str) -> None:
        self._kind(kind)["already_tried"] += 1

    def policy_suppressed(self, kind: str, reason: str) -> None:
        """V2 の補完: 戦略の選好で送らなかった（API が入力を返さない・check の拒否・合法でないとは別）。"""
        self._kind(kind)["policy_suppressed"] += 1
        self.axis("policy_suppressed_reason", reason)

    def checked(self, kind: str, valid: bool) -> None:
        self._kind(kind)["check_valid" if valid else "check_invalid"] += 1

    def submitted(self, kind: str, outcome: str | None, after_status: str | None) -> None:
        k = self._kind(kind)
        k["submitted"] += 1
        _inc(k["outcome"], outcome)
        if outcome == "accepted":
            _inc(k["after_accept"], after_status)

    def to_dict(self) -> dict[str, Any]:
        kinds = {}
        for name, k in sorted(self.kinds.items()):
            kinds[name] = {**{key: (len(v) if isinstance(v, set) else round(v, 4) if isinstance(v, float) else dict(sorted(v.items())) if isinstance(v, dict) else v)
                              for key, v in k.items()}}
        return {"fetches": self.fetches, "states": len(self.states), "kinds": kinds,
                "axes": {name: dict(sorted(v.items())) for name, v in sorted(self.axes.items())}}


# ---------------------------------------------------------------- 保存した記録の読み直し（新しい対戦を走らせない）


DEEP = frozenset({"supported", "may_stop_later"})


def kind_opportunities(trace: list[dict[str, Any]], actor_logs: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    """保存した操作の記録と主体ごとの記録から、ある種類の提示・範囲・選ばれる機会を数え直す（V0 の記録は Metrics を持たないため）。

    範囲の規則は V0 の deep と同じ（表示だけ・入力を返さない・処理可能性が supported・may_stop_later でない・同じ状態で入力を作れなかったを外す）。"""
    unbuildable: dict[int, set[str]] = {}
    by_attempt = {e["n"]: e for e in trace if e.get("type") == "attempt"}
    out = {"offered_fetches": 0, "offered_states": set(), "in_scope_fetches": 0, "excluded": {}, "draws": [], "selected": 0}
    for row in sorted((r for r in actor_logs if r.get("type") == "attempt"), key=lambda r: r["n"]):
        entry = by_attempt[row["n"]]
        cands = row["candidates"]["response"]
        display = set(cands["coverage"]["display_only_kinds"])
        keys = unbuildable.setdefault(entry["position"], set())
        scope = []
        for c in cands["candidates"]:
            key = _key(c)
            why = ("display_only" if c["kind"] in display else "input_withheld" if c["input_disclosure"] == "unconfirmed"
                   else f"processability:{c.get('processability')}" if c.get("processability") not in DEEP else "unbuildable" if key in keys else None)
            if c["kind"] == kind:
                out["offered_fetches"] += 1
                out["offered_states"].add(entry["position"])
                if why is not None:
                    _inc(out["excluded"], why)
            if why is None:
                scope.append(c)
        mine = [c for c in scope if c["kind"] == kind]
        if mine:
            out["in_scope_fetches"] += len(mine)
            out["draws"].append({"attempt": row["n"], "position": entry["position"], "in_scope": len(scope), "of_kind": len(mine),
                                 "probability": round(len(mine) / len(scope), 4), "chosen_kind": entry["candidate"]["kind"]})
        if entry["candidate"]["kind"] == kind:
            out["selected"] += 1
        if isinstance(entry["build"], dict):
            keys.add(_key(entry["candidate"]))
    out["offered_states"] = len(out["offered_states"])
    out["expected_selections"] = round(sum(d["probability"] for d in out["draws"]), 4)
    return out


def _key(candidate: dict[str, Any]) -> str:
    import json

    return json.dumps({k: v for k, v in candidate.items() if k != "id"}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def repetition_summary(trace: list[dict[str, Any]], actor_logs) -> dict[str, Any]:
    """番ごとの同じ意味の操作の受理の回数（V2 の補完。どの方策の記録からも数える。保存した V2 の記録にも使える）。

    番は、試みの状態（``position``）の主体の観測（主体ごとの記録の ``position`` の行の ``view``）の（区間, 番の番号）。鍵は ``policies.action_key``。"""
    from collections import Counter

    from .policies import action_key, turn_of

    logs = actor_logs.items() if isinstance(actor_logs, dict) else actor_logs
    turns = {}
    for actor, rows in logs:
        for r in rows:
            if r.get("type") == "position":
                turns[(str(actor), r["position"])] = turn_of(r["view"])
    per_turn: dict[tuple, Counter] = {}
    powers: Counter = Counter()
    for e in trace:
        if e.get("type") != "attempt" or (e.get("submit") or {}).get("outcome") != "accepted":
            continue
        turn = turns.get((str(e["actor"]), e["position"]))
        key = action_key(e["actor"], e["candidate"], e.get("stages") or [], e.get("meaning") or [])
        per_turn.setdefault((str(e["actor"]), turn), Counter())[key] += 1
        if e["candidate"].get("kind") == "use_power":
            powers[(e["candidate"].get("power") or {}).get("name_ja")] += 1
    maxima = sorted(((max(c.values()), actor, turn) for (actor, turn), c in per_turn.items()), reverse=True)
    return {"actor_turns": len(per_turn), "max_same_action_per_turn": maxima[0][0] if maxima else 0,
            "actor_turns_with_repeat": sum(1 for c in per_turn.values() if max(c.values()) >= 2),
            "repeated_actions": sum(1 for c in per_turn.values() for n in c.values() if n >= 2),
            "top": [{"actor": a, "turn": list(t) if t else None, "max": m} for m, a, t in maxima[:5]],
            "accepted_power_uses": dict(powers)}
