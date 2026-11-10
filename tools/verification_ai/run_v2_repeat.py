"""V2 の補完の実行の入口（docs/verification-ai-v2-repeat.md 5 章）。単一のプロセスで、上限つきの対戦を 1 局ずつ順に実行する。プロセスの起動・検索・終了はしない。

    python -m tools.verification_ai.run_v2_repeat run --out <保存先> --engine-commit <sha> --reuse <V2 の局のディレクトリ> --seed 13 --epsilon 0.25

- 対戦の前に計画（``plan.json``）を書く。rules-v2 と mixed（ルールの側 rules-v2）の 2 局を実行する。3 局目（mixed の別のプロセスでの再現）は、計画に書いた
  ``run_v1 reproduce`` で別に実行する
- V2 の rules-s13・mixed-e0.25-s13 の保存した記録を読み、同じ関数で番ごとの反復を数え直して比べる（再実行しない・保存した記録を変えない）
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from . import records as R
from .metrics import repetition_summary
from .run_v1 import check_record, game_header, now, read_jsonl, write_game
from .runner import Config, Limits, run_game

VERSION = "v2-repeat"


def compare_row(label: str, source: str, result: dict[str, Any], repetition: dict[str, Any], verification: dict[str, Any], notes: list[str]) -> dict[str, Any]:
    kinds = result["metrics"]["kinds"]
    accepted = {k: v["outcome"].get("accepted", 0) for k, v in kinds.items() if v["outcome"].get("accepted")}
    axes = result["metrics"]["axes"]
    return {"game": label, "source": source, "termination": result["termination"]["class"], "turns": result["counters"]["turns"],
            "operations": result["counters"]["operations"], "accepted": result["counters"]["accepted"], "attempts": result["counters"]["attempts"],
            "policy_suppressed": result["counters"].get("policy_suppressed", "not_recorded"), "accepted_kinds": accepted,
            "use_attack_accepted": accepted.get("use_attack", 0), "take_prize_accepted": accepted.get("take_prize", 0),
            "promote_active_accepted": accepted.get("promote_active", 0), "decision_kinds": axes.get("decision_kind", {}),
            "prize_count_decrease": axes.get("prize_count_decrease", {}), "episode_mode": axes.get("episode_mode", {}),
            "suppressed_reasons": axes.get("policy_suppressed_reason", {}), "repetition": repetition,
            "replay_run": verification["replay_run"]["status"], "replay_matches_expectation": verification["replay_run"]["matches_expectation"],
            "correspondence_problems": len(verification["correspondence_problems"]), "notes": notes}


def run(out: Path, engine_commit: str, reuse: Path, seed: int, epsilon: float, budget: float, argv: list[str],
        deck0="hitmonchan-dewgong", deck1="venusaur-parasect") -> int:
    group = f"v2r-{deck0}-vs-{deck1}-default-s{seed}"
    gdir = out / "verifier" / "runs" / group
    if gdir.exists():
        raise SystemExit(f"{gdir} はすでにある（既存の証跡を上書きしない）")
    new = [{"policy": "rules", "rules_version": 2, "game": f"rules-v2-s{seed}"},
           {"policy": "mixed", "rules_version": 2, "epsilon": epsilon, "game": f"mixed-v2-e{epsilon}-s{seed}"}]
    reused = [{"game": f"rules-s{seed}", "policy": "rules", "rules_version": 1}, {"game": f"mixed-e{epsilon}-s{seed}", "policy": "mixed", "rules_version": 1}]
    R.write_json(gdir / "plan.json", {
        "written": now(), "seeds": {"game": seed, "policy": seed, "host": seed}, "repeat_threshold": 2, "demote_after": 2, "epsilon": epsilon,
        "new_games": new, "reused_games": [{**r, "source": str(reuse / r["game"]).replace("\\", "/")} for r in reused],
        "reproduction": {"of": new[1]["game"], "how": "python -m tools.verification_ai.run_v1 reproduce --label v2r --baseline <この計画のディレクトリ>/" + new[1]["game"],
                         "process": "別の Python のプロセスで 1 回"},
        "limits_per_game": Limits().__dict__, "budget_seconds": budget,
        "note": "対戦の前に書いた計画。結果を見て閾値・seed を変えない・局を増やさない。V2 の記録は再実行しない"})
    ident = R.identity(engine_commit)
    start = time.monotonic()
    rows, status = [], []
    for item in reused:
        d = reuse / item["game"]
        result = json.loads((d / "result.json").read_text(encoding="utf-8"))
        trace = read_jsonl(d / "trace.jsonl")
        logs = {name: read_jsonl(d / "actors" / f"{name}.jsonl") for name in ("0", "1", "host")}
        verification = json.loads((d / "verification.json").read_text(encoding="utf-8"))
        rows.append(compare_row(item["game"], "reused_v2", result, repetition_summary(trace, logs), verification,
                                ["V2（e9fc20b）の記録: 公開のサイドの枚数の減少は終局の観測を数えていない下限", "header.json に policy・epsilon がない（result.json の policies にある）",
                                 "policy_suppressed は記録していない（rules-v1 は抑えない）"]))
    for item in new:
        if time.monotonic() - start >= budget:
            status.append({**item, "status": "not_run", "reason": "budget_exceeded"})
            continue
        config = Config(deck0=deck0, deck1=deck1, game_seed=seed, policy_seed=seed, host_seed=seed, policy=item["policy"], rules_version=2,
                        epsilon=item.get("epsilon", 0.25), run_id=f"{group}-{item['game']}")
        started = now()
        result = run_game(config)
        finished = now()
        verification = check_record(result)
        write_game(gdir / item["game"], game_header(config, ident, argv, result, started, finished), result, verification)
        status.append({**item, "status": "run"})
        rows.append(compare_row(item["game"], "new", result, result["repetition"], verification, []))
        print(json.dumps({"game": item["game"], "termination": result["termination"]["class"], "accepted": result["counters"]["accepted"],
                          "turns": result["counters"]["turns"], "policy_suppressed": result["counters"]["policy_suppressed"],
                          "max_same": result["repetition"]["max_same_action_per_turn"], "replay_run": verification["replay_run"]["status"],
                          "elapsed": result["elapsed_seconds"]}, ensure_ascii=False))
    total = round(time.monotonic() - start, 3)
    comparison = {"games": rows, "status": status, "total_seconds": total,
                  "note": "少数の局で、差を閾値の効果と断定しない（方策の版で乱数の消費と操作の列が変わる）。勝ちは参考値"}
    R.write_json(gdir / "comparison.json", comparison)
    R.write_json(out / "public" / "runs" / group / "summary.json", {"tool": {"name": "tools.verification_ai", "version": VERSION},
                                                                   "engine": {"git_commit": engine_commit, "version": ident["version"],
                                                                              "behavior_digest": ident["implementation"]["behavior_digest"]},
                                                                   "decks": {"0": deck0, "1": deck1}, "convention_set": "default",
                                                                   "games": [{k: v for k, v in r.items() if k != "repetition"} | {"repetition": {k: r["repetition"][k] for k in (
                                                                       "actor_turns", "max_same_action_per_turn", "actor_turns_with_repeat", "repeated_actions",
                                                                       "accepted_power_uses")}} for r in rows], "total_seconds": total})
    ok = all(s["status"] == "run" for s in status) and all(r["replay_matches_expectation"] and not r["correspondence_problems"] for r in rows)
    print(json.dumps({"group": group, "total_seconds": total, "all_ok": ok}, ensure_ascii=False))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="python -m tools.verification_ai.run_v2_repeat")
    sub = parser.add_subparsers(dest="cmd", required=True)
    rn = sub.add_parser("run")
    rn.add_argument("--out", required=True)
    rn.add_argument("--engine-commit", required=True)
    rn.add_argument("--reuse", required=True)
    rn.add_argument("--seed", type=int, required=True)
    rn.add_argument("--epsilon", type=float, default=0.25)
    rn.add_argument("--budget-seconds", type=float, default=1200.0)
    args = parser.parse_args(argv)
    return run(Path(args.out), args.engine_commit, Path(args.reuse), args.seed, args.epsilon, args.budget_seconds,
               ["python", "-m", "tools.verification_ai.run_v2_repeat", *argv])


if __name__ == "__main__":
    raise SystemExit(main())
