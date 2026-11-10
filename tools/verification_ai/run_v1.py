"""V1 の実行の入口（docs/verification-ai-v1.md 6 章）。単一のプロセスで、上限つきの対戦を 1 局ずつ順に実行し、記録を書く。プロセスの起動・検索・終了はしない。

    python -m tools.verification_ai.run_v1 reproduce --baseline <保存済みの V0 の実行の a> --out <保存先> --engine-commit <sha>
    python -m tools.verification_ai.run_v1 run --out <保存先> --engine-commit <sha> --seeds 11 12 13 --distributions <分布> ...

- ``reproduce``: 保存済みの実行の見出しと同じ条件で 1 局だけ走らせ、保存済みの意味の列・終わり方・エンジンの受理したコマンドの列と比べ、新しい記録の対応と replay_run を確かめる
- ``run``: 実行の前に計画（seed・分布・上限）を書き、決めた組を順に 1 局ずつ実行する。全体の時間の予算を超えたら残りを実行せず「未実行」として記録する（自動で増やさない）
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kyuura_engine import replay_run, view_record

from . import records as R
from .policies import DISTRIBUTIONS, STAGE, TUPLE
from .run_v0 import expected_replay, replay_summary
from .runner import LIMIT_TIME, Config, Limits, run_game

VERSION = "v1"
SHORT = {STAGE: "stage", TUPLE: "tuple"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def engine_commands(record_data: dict[str, Any]) -> list[Any]:
    """完全な記録の行のうち、比べる値（主体・送り手・コマンド・結果）。operation_id・確認値の項目名の外の値は比べない。"""
    return [{k: row.get(k) for k in ("actor", "submitter", "command", "outcome", "accepted_index")} for row in record_data["operations"]]


def check_record(result: dict[str, Any]) -> dict[str, Any]:
    data = result["record"].data
    expected = expected_replay(data)
    report = replay_run.replay(result["record"])
    return {"replay_run": {"expected": expected, **replay_summary(report), "matches_expectation": report.status == expected},
            "correspondence_problems": R.correspondence(result["trace"], data)}


def write_game(d: Path, header: dict[str, Any], result: dict[str, Any], verification: dict[str, Any]) -> None:
    R.write_json(d / "header.json", header)
    R.write_jsonl(d / "trace.jsonl", result["trace"])
    for actor, rows in result["actor_logs"].items():
        R.write_jsonl(d / "actors" / f"{actor}.jsonl", rows)
    R.write_record(d / "full_record.json", result["record"])
    R.write_json(d / "result.json", {k: result[k] for k in ("termination", "counters", "anomalies", "coverage", "metrics", "elapsed_seconds", "policies",
                                                             "limits", "distribution")})
    R.write_jsonl(d / "meaning.jsonl", R.meaning_sequence(result["trace"]))
    R.write_json(d / "verification.json", verification)


def game_header(config: Config, ident: dict[str, Any], argv: list[str], result: dict[str, Any], started: str, finished: str) -> dict[str, Any]:
    return {"tool": {"name": "tools.verification_ai", "version": VERSION}, "engine": ident, "argv": argv, "run_id": config.run_id,
            "convention_set": result["record"].data["header"]["convention_set"], "decks": {"0": config.deck0, "1": config.deck1},
            "game_seed": config.game_seed, "policy_seed": config.policy_seed, "host_seed": config.host_seed, "distribution": config.distribution,
            "policy": config.policy, "epsilon": config.epsilon if config.policy == "mixed" else None,
            "rules_version": config.rules_version if config.policy in ("rules", "mixed") else None,
            "repeat_threshold": config.repeat_threshold if config.policy in ("rules", "mixed") and config.rules_version == 2 else None,
            "policies": result["policies"], "profile": config.profile, "limits": result["limits"], "started": started, "finished": finished}


def reproduce(baseline: Path, out: Path, engine_commit: str, argv: list[str], label: str = "v1") -> int:
    base_header = json.loads((baseline / "header.json").read_text(encoding="utf-8"))
    base_result = json.loads((baseline / "result.json").read_text(encoding="utf-8"))
    base_meaning = read_jsonl(baseline / "meaning.jsonl")
    base_record = json.loads((baseline / "full_record.json").read_text(encoding="utf-8"))
    name = f"{label}-repro-of-{baseline.parent.name}-{baseline.name}"
    limits = Limits(**base_header["limits"])
    # 方策の設定は見出しから読む（V0・V1 の見出しは policy を持たないので均等。V2 の補完: rules・mixed の版・ε・閾値）
    policy = base_header.get("policy") or "uniform"
    rule_options = {"policy": policy}
    if policy in ("rules", "mixed"):
        rule_options.update(rules_version=base_header.get("rules_version") or 1, repeat_threshold=base_header.get("repeat_threshold") or 2)
    if policy == "mixed":
        rule_options["epsilon"] = base_header["epsilon"]
    distribution = base_header.get("distribution") or base_header["policies"]["0"]["distribution"]
    config = Config(deck0=base_header["decks"]["0"], deck1=base_header["decks"]["1"], game_seed=base_header["game_seed"], policy_seed=base_header["policy_seed"],
                    host_seed=base_header["host_seed"], profile=base_header["profile"], limits=limits, distribution=distribution, run_id=name, **rule_options)
    started = now()
    result = run_game(config)
    finished = now()
    verification = check_record(result)
    meaning = R.meaning_sequence(result["trace"])
    time_limited = LIMIT_TIME in (result["termination"]["class"], base_result["termination"]["class"])
    comparison = R.compare_meanings(base_meaning, meaning, min(len(base_meaning), len(meaning)))
    comparison.update({"lengths": {"baseline": len(base_meaning), "reproduction": len(meaning)}, "time_limited": time_limited,
                       "full_match": comparison["equal"] and len(base_meaning) == len(meaning) and not time_limited})
    commands_equal = engine_commands(base_record) == engine_commands(result["record"].data)
    verification.update({
        "baseline": str(baseline).replace("\\", "/"),
        "meaning_comparison": comparison,
        "termination": {"baseline": base_result["termination"]["class"], "reproduction": result["termination"]["class"],
                        "equal": base_result["termination"]["class"] == result["termination"]["class"]},
        "engine_commands_equal": commands_equal,
        "compared": "意味の列（取っ手・operation_id・応答ごとの番号・時間を除く）・終わり方・完全な記録の行（主体・送り手・コマンド・結果・受理の番号。operation_id・確認値・時刻は除く）",
    })
    ok = (comparison["equal"] and (comparison["full_match"] or time_limited) and verification["termination"]["equal"] and commands_equal
          and verification["replay_run"]["matches_expectation"] and not verification["correspondence_problems"])
    verification["reproduced"] = ok
    d = out / "verifier" / "runs" / name
    write_game(d, game_header(config, R.identity(engine_commit), argv, result, started, finished), result, verification)
    R.write_json(out / "public" / "runs" / name / "summary.json", {
        "tool": {"name": "tools.verification_ai", "version": VERSION}, "engine": {"git_commit": engine_commit},
        "baseline_run": f"{baseline.parent.name}/{baseline.name}", "termination": verification["termination"],
        "meaning_comparison": {k: comparison[k] for k in ("equal", "compared", "full_match", "time_limited", "lengths")},
        "engine_commands_equal": commands_equal, "replay_run": {k: verification["replay_run"][k] for k in ("expected", "status", "matches_expectation")},
        "correspondence_problem_count": len(verification["correspondence_problems"]), "reproduced": ok})
    print(json.dumps({"run": name, "reproduced": ok, "termination": verification["termination"], "meaning": {k: comparison[k] for k in ("equal", "compared", "lengths")},
                      "engine_commands_equal": commands_equal, "replay_run": verification["replay_run"]["status"],
                      "correspondence_problems": verification["correspondence_problems"], "elapsed": result["elapsed_seconds"]}, ensure_ascii=False, indent=1))
    return 0 if ok else 1


def run_matrix(out: Path, engine_commit: str, seeds: list[int], distributions: list[str], budget: float, argv: list[str],
               deck0="hitmonchan-dewgong", deck1="venusaur-parasect") -> int:
    group = f"v1-{deck0}-vs-{deck1}-default"
    gdir = out / "verifier" / "runs" / group
    plan = [{"distribution": dist, "seed": seed, "game": f"{SHORT[dist]}-s{seed}"} for dist in distributions for seed in seeds]
    R.write_json(gdir / "plan.json", {"written": now(), "seeds": seeds, "seed_use": "ゲーム・方策・ホストの seed を同じ値にする", "distributions": distributions,
                                      "games": plan, "budget_seconds": budget, "limits_per_game": Limits().__dict__,
                                      "note": "実行の前に書いた計画。結果を見て seed を差し替えない。予算を超えたら残りは実行しない"})
    ident = R.identity(engine_commit)
    start = time.monotonic()
    games = []
    for item in plan:
        if time.monotonic() - start >= budget:
            games.append({**item, "status": "not_run", "reason": "budget_exceeded"})
            continue
        config = Config(deck0=deck0, deck1=deck1, game_seed=item["seed"], policy_seed=item["seed"], host_seed=item["seed"], distribution=item["distribution"],
                        run_id=f"{group}-{item['game']}")
        started = now()
        result = run_game(config)
        finished = now()
        verification = check_record(result)
        write_game(gdir / item["game"], game_header(config, ident, argv, result, started, finished), result, verification)
        games.append({**item, "status": "run", "termination": result["termination"]["class"], "termination_detail": result["termination"]["detail"],
                      "counters": result["counters"], "anomalies": [a["kind"] for a in result["anomalies"]], "metrics": result["metrics"],
                      "replay_run": verification["replay_run"]["status"], "replay_matches_expectation": verification["replay_run"]["matches_expectation"],
                      "correspondence_problems": verification["correspondence_problems"], "elapsed_seconds": result["elapsed_seconds"]})
        print(json.dumps({"game": item["game"], "termination": result["termination"]["class"], "accepted": result["counters"]["accepted"],
                          "turns": result["counters"]["turns"], "replay_run": verification["replay_run"]["status"],
                          "elapsed": result["elapsed_seconds"]}, ensure_ascii=False))
    total = round(time.monotonic() - start, 3)
    R.write_json(gdir / "aggregate.json", {"games": games, "total_seconds": total, "independent_games": sum(g["status"] == "run" for g in games)})
    public_games = [{k: g.get(k) for k in ("distribution", "game", "status", "termination", "counters", "anomalies", "replay_run", "replay_matches_expectation")}
                    | {"correspondence_problem_count": len(g.get("correspondence_problems") or []),
                       "kinds": {kind: {key: v[key] for key in ("offered_fetches", "offered_states", "in_scope_fetches", "selection_opportunities", "expected_selections",
                                                                 "selected", "build_ok", "build_failed", "build_method", "check_valid", "check_invalid", "submitted",
                                                                 "outcome", "after_accept", "excluded")}
                                 for kind, v in (g.get("metrics") or {}).get("kinds", {}).items()},
                       "axes": {a: v for a, v in (g.get("metrics") or {}).get("axes", {}).items() if a not in ("stage_form",)},
                       "stage_forms": len((g.get("metrics") or {}).get("axes", {}).get("stage_form", {})),
                       "fetches": (g.get("metrics") or {}).get("fetches"), "states": (g.get("metrics") or {}).get("states")} for g in games]
    R.write_json(out / "public" / "runs" / group / "summary.json", {"tool": {"name": "tools.verification_ai", "version": VERSION},
                                                                   "engine": {"git_commit": engine_commit, "version": ident["version"],
                                                                              "behavior_digest": ident["implementation"]["behavior_digest"]},
                                                                   "decks": {"0": deck0, "1": deck1}, "convention_set": "default", "games": public_games,
                                                                   "independent_games": sum(g["status"] == "run" for g in games), "total_seconds": total})
    ok = all(g["status"] == "run" and g["replay_matches_expectation"] and not g["correspondence_problems"] for g in games)
    print(json.dumps({"group": group, "total_seconds": total, "all_ok": ok}, ensure_ascii=False))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="python -m tools.verification_ai.run_v1")
    sub = parser.add_subparsers(dest="cmd", required=True)
    rp = sub.add_parser("reproduce")
    rp.add_argument("--baseline", required=True)
    rp.add_argument("--out", required=True)
    rp.add_argument("--engine-commit", required=True)
    rp.add_argument("--label", default="v1")
    rn = sub.add_parser("run")
    rn.add_argument("--out", required=True)
    rn.add_argument("--engine-commit", required=True)
    rn.add_argument("--seeds", type=int, nargs="+", required=True)
    rn.add_argument("--distributions", nargs="+", choices=DISTRIBUTIONS, required=True)
    rn.add_argument("--budget-seconds", type=float, default=1200.0)
    args = parser.parse_args(argv)
    full = ["python", "-m", "tools.verification_ai.run_v1", *argv]
    if args.cmd == "reproduce":
        return reproduce(Path(args.baseline), Path(args.out), args.engine_commit, full, args.label)
    if len(args.seeds) * len(args.distributions) > 6:
        parser.error("V1 の実行は 6 局まで")
    return run_matrix(Path(args.out), args.engine_commit, args.seeds, args.distributions, args.budget_seconds, full)


if __name__ == "__main__":
    raise SystemExit(main())
