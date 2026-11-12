"""到達の段の集計（読むだけ。docs/verification-ai-reach-policy.md 5 章・12 章）。保存した局の記録（trace.jsonl・actors/*.jsonl・result.json）から、目標（P6・U-R3a）ごとに
提示・選択・入力の生成・check・実送信・結果・受理の中身と、前提の段を数える。方策・ランナー・判定に影響しない。

- 目標の操作の見分けは、方策と同じ契約の値（``reach.is_p6_candidate``・``is_u_r3a_candidate``）。受理の中身は既存の判定（``judge.judge_recorded_accepted_content``）
- 記録に必要な値がない段は 0 にせず ``{"status": "not_recorded", "reason": …}`` にする（古い記録・reach でない方策の局）
- カードの設定（秘策・対象のカード）は局の reach の設定から読む。reach でない局は ``settings`` を渡したときだけ前提の段を数える（渡さなければ not_applicable）

    python -m tools.verification_ai.reach_report <局の attempt のディレクトリ> ...  （結果の JSON を標準出力へ）
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from .reach import is_normal_retreat, is_p6_candidate, is_u_r3a_candidate

FORMAT = "kyuura-vai-reach-report/1"
NOT_RECORDED = "not_recorded"


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def not_recorded(reason: str) -> dict[str, str]:
    return {"status": NOT_RECORDED, "reason": reason}


def _target(goal: str):
    return is_p6_candidate if goal == "p6" else is_u_r3a_candidate


def target_funnel(goal: str, trace: list[dict[str, Any]], actor_logs: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """目標の操作の段（主体ごと）。提示は試みの記録の候補の一覧（同じ position は 1 回）、選択からあとは trace の試み。"""
    from .judge import judge_recorded_accepted_content

    pred = _target(goal)
    out: dict[str, Any] = {}
    for actor in ("0", "1"):
        rows = actor_logs.get(actor)
        offered: Any
        if rows is None:
            offered = not_recorded("actor_log_missing")
        else:
            positions = set()
            for r in rows:
                if r.get("type") != "attempt":
                    continue
                cands = ((r.get("candidates") or {}).get("response") or {}).get("candidates")
                if cands is None:
                    offered = not_recorded("candidates_not_in_actor_log")
                    break
                if any(pred(c) for c in cands):
                    positions.add(r.get("position"))
            else:
                offered = len(positions)
        entries = [e for e in trace if e.get("type") == "attempt" and str(e.get("actor")) == actor and pred(e.get("candidate") or {})]
        f: dict[str, Any] = {"offered_positions": offered, "selected": len(entries),
                             "built": sum(1 for e in entries if "choices" in e),
                             "unbuildable": sum(1 for e in entries if isinstance(e.get("build"), dict)),
                             "suppressed_or_retry": sum(1 for e in entries if e.get("build") in ("suppressed_by_policy", "ok_already_tried")),
                             "check_valid": sum(1 for e in entries if ((e.get("check") or {}).get("response") or {}).get("valid") is True),
                             "check_invalid": sum(1 for e in entries if ((e.get("check") or {}).get("response") or {}).get("valid") is False),
                             "submitted": sum(1 for e in entries if "submit" in e)}
        outcomes = Counter((e.get("submit") or {}).get("outcome") for e in entries if "submit" in e)
        f["outcomes"] = dict(sorted(outcomes.items()))
        f["rejection_codes"] = dict(sorted(Counter(((e.get("submit") or {}).get("verifier") or {}).get("engine_code")
                                                   for e in entries if (e.get("submit") or {}).get("outcome") == "rejected").items()))
        content: Counter = Counter()
        missing = 0
        for e in entries:
            if (e.get("submit") or {}).get("outcome") != "accepted":
                continue
            if "public_events_after_accept" not in e:
                missing += 1
                continue
            judged = judge_recorded_accepted_content(e)
            content[f"{judged[1]}:{judged[2][0] if judged[2] else ''}" if judged else "not_applicable"] += 1
        f["accepted_content"] = dict(sorted(content.items())) if not missing else {**dict(content), **{NOT_RECORDED: missing}}
        out[actor] = f
    return out


def _views(rows: list[dict[str, Any]]):
    view = None
    for r in rows:
        if r.get("type") == "position":
            view = r.get("view")
        elif r.get("type") == "attempt":
            yield view, r


def prerequisite_funnel(goal: str, settings: dict[str, Any] | None, trace: list[dict[str, Any]], actor_logs: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """前提の段（主体ごと。本人の観測と本人の記録だけ）。settings がなければ not_applicable。"""
    if settings is None:
        return {"status": "not_applicable", "reason": "no_reach_settings"}
    trainers, cards = set(settings["place_trainers"]), set(settings["place_cards"])
    out: dict[str, Any] = {}
    for actor in ("0", "1"):
        rows = actor_logs.get(actor)
        if rows is None:
            out[actor] = not_recorded("actor_log_missing")
            continue
        a = int(actor)
        hand_turns, both_turns, fd_active_turns = set(), set(), set()
        placed, placed_target, decisions = 0, 0, 0
        for view, r in _views(rows):
            obs = (view or {}).get("observation") or {}
            players = obs.get("players") or []
            if len(players) <= a:
                continue
            me = players[a]
            turn = ((view or {}).get("status", {}).get("segment"), obs.get("turn"))
            hand = {c.get("card_id") for c in ((me.get("hand") or {}).get("cards") or [])}
            if obs.get("current_player") == a:
                if hand & trainers:
                    hand_turns.add(turn)
                    if hand & cards:
                        both_turns.add(turn)
                if (me.get("active") or {}).get("face_down"):
                    fd_active_turns.add(turn)
            stages = ((r.get("inputs") or {}).get("response") or {}).get("stages") or []
            if stages and stages[0].get("decision_kind") == "secret_plan_card" and "submit" in r:
                decisions += 1
                if (r.get("submit") or {}).get("outcome") == "accepted":
                    ids = {o["id"]: o.get("card_id") for o in stages[0].get("options") or []}
                    chosen = [ids.get(i) for i in (r.get("choice") or {}).get("choices") or []]
                    placed += bool(chosen)
                    placed_target += any(c in cards for c in chosen)
        moves = Counter()
        for e in trace:
            if e.get("type") != "attempt" or str(e.get("actor")) != actor or (e.get("submit") or {}).get("outcome") != "accepted":
                continue
            first = (e.get("meaning") or [{}])[0].get("option") or {}
            stages = e.get("stages") or []
            if is_normal_retreat(e.get("candidate") or {}) and first.get("face_down") is True:
                moves["normal_retreat_to_face_down"] += 1
            elif stages and stages[0].get("decision_kind") == "promote_active" and first.get("face_down") is True:
                moves["promote_face_down"] += 1
        out[actor] = {"own_turns_with_place_trainer_in_hand": len(hand_turns),
                      "own_turns_with_place_trainer_and_card_in_hand": len(both_turns) if cards else "not_applicable",
                      "secret_plan_decisions_answered": decisions, "placed_face_down": placed,
                      "placed_target_card": placed_target if cards else "not_applicable",
                      "moved_face_down_to_active": dict(moves) if goal == "p6" else "not_applicable",
                      "own_turns_with_face_down_active": len(fd_active_turns) if goal == "p6" else "not_applicable"}
    return out


def policy_funnel(trace: list[dict[str, Any]], result: dict[str, Any] | None) -> dict[str, Any]:
    """reach の方策の記録（規則ごとの選択・送らない評価・試行・保護）。reach でない局・記録のない局は not_recorded。"""
    policies = (result or {}).get("policies")
    if policies is None:
        return not_recorded("result_policies_missing")
    if not all((policies.get(a) or {}).get("name") == "reach" for a in ("0", "1")):
        return not_recorded("not_reach_policy")
    rules = Counter()
    vetoes = Counter()
    profiles = Counter()
    for e in trace:
        if e.get("type") != "attempt":
            continue
        reason = e.get("candidate_reason") or ""
        parts = reason.split(":")
        if reason.startswith("reach:") and len(parts) > 2 and parts[2] in ("R0", "R1", "R2"):
            rules[f"{e.get('actor')}:{parts[2]}"] += 1
        verdict = (e.get("policy_review") or {}).get("reason") or ""
        if verdict in ("reach:protect_veto", "reach:trainer_not_offered"):
            vetoes[f"{e.get('actor')}:{verdict}"] += 1
        if "scope_profile" in e:
            profiles[f"{e.get('actor')}:{e['scope_profile']}"] += 1
    return {"rule_selections": dict(sorted(rules.items())), "vetoes": dict(sorted(vetoes.items())), "scope_profiles": dict(sorted(profiles.items())),
            "final_state": {a: (policies.get(a) or {}).get("reach_state") for a in ("0", "1")}}


def game_report(attempt_dir: Path, settings: dict[str, Any] | None = None, goals: tuple[str, ...] | None = None) -> dict[str, Any]:
    """1 局（attempt のディレクトリ）の到達の段。reach の局は局の設定の目標、ほかは ``goals``（既定は両方）。"""
    trace = _jsonl(attempt_dir / "trace.jsonl")
    actors = {}
    for actor in ("0", "1"):
        path = attempt_dir / "actors" / f"{actor}.jsonl"
        if path.is_file():
            actors[actor] = _jsonl(path)
    result_path = attempt_dir / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else None
    reach_settings = ((result or {}).get("policies") or {}).get("0", {}).get("reach")
    if reach_settings is not None:
        settings, goals = reach_settings, (reach_settings["goal"],)
    goals = goals or ("p6", "u_r3a")
    return {"format": FORMAT, "policy": policy_funnel(trace, result),
            "goals": {goal: {"target": target_funnel(goal, trace, actors), "prerequisites": prerequisite_funnel(goal, settings, trace, actors)}
                      for goal in goals}}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    out = {str(Path(a)): game_report(Path(a)) for a in args}
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
