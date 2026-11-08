"""V0 の実行の入口（docs/verification-ai-v0.md 7 章）。単一のプロセスで、上限つきの固定条件の対戦を 2 回（同じ種）実行し、記録を書く。

    python -m tools.verification_ai.run_v0 run --out C:/dev/kyuura-engine-verification-vai --engine-commit <sha>
    python -m tools.verification_ai.run_v0 manifest --out C:/dev/kyuura-engine-verification-vai --run <run> --command "<実行したコマンド>" --exit-code <n>

``run`` の流れ: 実行 A → A の完全な記録を ``replay_run.replay`` で再実行（期待は記録の終わりに合わせる）→ 閲覧者ごとの記録 → 同じ条件の実行 B → A と B の
意味の列を比べる → 検証者用（``verifier/``）と集計（``public/``）を書く。プロセスの起動・検索・終了はしない。git も呼ばない（コミットは引数）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from kyuura_engine import replay_run, view_record
from kyuura_engine.replay_record import END_ABORTED, END_CLOSED

from . import records as R
from .runner import EXCEPTION, LIMIT_TIME, Config, Limits, run_game

VERSION = "v0"


def expected_replay(record_data: dict[str, Any]) -> str:
    """完全な記録の終わりに合わせた再実行の期待（閉じた記録は succeeded、failed で止めた記録は recorded_failure）。"""
    end = (record_data.get("end") or {}).get("state")
    return {END_CLOSED: replay_run.SUCCEEDED, END_ABORTED: replay_run.RECORDED_FAILURE}.get(end, "unknown_end")


def replay_summary(report) -> dict[str, Any]:
    return {"status": report.status, "executed": report.executed, "verified_seq": report.verified_seq, "verified_accepted": report.verified_accepted,
            "end_verified": report.end_verified, "mismatch": None if report.mismatch is None else str(report.mismatch)}


def run_dir_name(config: Config) -> str:
    conv = config.conventions or "default"
    return f"v0-{config.deck0}-vs-{config.deck1}-{conv.replace('@', '_')}-g{config.game_seed}-p{config.policy_seed}-h{config.host_seed}"


def execute(config: Config, out: Path, engine_commit: str | None, argv: list[str]) -> int:
    name = run_dir_name(config)
    vdir, pdir = out / "verifier" / "runs" / name, out / "public" / "runs" / name
    ident = R.identity(engine_commit)
    results = {}
    for label in ("a", "b"):
        cfg = Config(**{**config.__dict__, "run_id": f"{name}-{label}"})
        results[label] = run_game(cfg)
    a, b = results["a"], results["b"]
    data_a = a["record"].data
    expected = expected_replay(data_a)
    report = replay_run.replay(a["record"])
    replay_ok = report.status == expected
    views_report, views = view_record.view_records_from_replay(a["record"])
    meanings = {k: R.meaning_sequence(v["trace"]) for k, v in results.items()}
    time_limited = LIMIT_TIME in (a["termination"]["class"], b["termination"]["class"])
    bound = min(len(meanings["a"]), len(meanings["b"]))
    comparison = R.compare_meanings(meanings["a"], meanings["b"], bound)
    same_end = a["termination"]["class"] == b["termination"]["class"] and len(meanings["a"]) == len(meanings["b"])
    comparison.update({"bound": bound, "time_limited": time_limited, "lengths": {"a": len(meanings["a"]), "b": len(meanings["b"])},
                       "same_termination_and_length": same_end})
    corr = {k: R.correspondence(v["trace"], v["record"].data) for k, v in results.items()}
    checks_ok = replay_ok and comparison["equal"] and (same_end or time_limited) and not any(corr.values()) and a["termination"]["class"] != EXCEPTION
    header = {"tool": {"name": "tools.verification_ai", "version": VERSION}, "engine": ident, "argv": argv,
              "convention_set": data_a["header"]["convention_set"], "decks": {"0": config.deck0, "1": config.deck1},
              "decklists_in_record": True, "game_seed": config.game_seed, "policy_seed": config.policy_seed, "host_seed": config.host_seed,
              "policies": a["policies"], "profile": config.profile, "limits": a["limits"]}
    for label, res in results.items():
        d = vdir / label
        R.write_json(d / "header.json", {**header, "run_id": f"{name}-{label}"})
        R.write_jsonl(d / "trace.jsonl", res["trace"])
        for actor, rows in res["actor_logs"].items():
            R.write_jsonl(d / "actors" / f"{actor}.jsonl", rows)
        R.write_record(d / "full_record.json", res["record"])
        R.write_json(d / "result.json", {k: res[k] for k in ("termination", "counters", "anomalies", "coverage", "elapsed_seconds", "policies", "limits")})
        R.write_jsonl(d / "meaning.jsonl", meanings[label])
    if views is not None:
        for viewer, rec in views.items():
            name_v = "spectator" if viewer is None else str(viewer)
            (vdir / "a" / "views").mkdir(parents=True, exist_ok=True)
            (vdir / "a" / "views" / f"{name_v}.json").write_text(view_record.dumps_view_record(rec), encoding="utf-8", newline="\n")
    verification = {"replay_run": {"expected": expected, **replay_summary(report), "matches_expectation": replay_ok},
                    "view_records": {"status": views_report.status, "written": views is not None},
                    "meaning_comparison": comparison, "correspondence_problems": corr, "pipeline_ok": checks_ok}
    R.write_json(vdir / "verification.json", verification)
    R.write_json(pdir / "summary.json", {
        "tool": {"name": "tools.verification_ai", "version": VERSION}, "engine": {"git_commit": engine_commit, "version": ident["version"],
                                                                                "behavior_digest": ident["implementation"]["behavior_digest"]},
        "convention_set": "{id}@{version}".format(**data_a["header"]["convention_set"]),
        "decks": {"0": config.deck0, "1": config.deck1}, "policy": {"name": a["policies"]["0"]["name"], "distribution": a["policies"]["0"]["distribution"]},
        "profile": config.profile, "limits": a["limits"],
        "runs": {label: {"termination": res["termination"]["class"], "counters": res["counters"], "coverage": res["coverage"],
                         "anomaly_kinds": sorted({x["kind"] for x in res["anomalies"]}), "anomaly_count": len(res["anomalies"])}
                 for label, res in results.items()},
        "replay_run": {"expected": expected, "status": report.status, "matches_expectation": replay_ok},
        "meaning_comparison": {"equal": comparison["equal"], "compared": comparison["compared"], "time_limited": time_limited,
                               "same_termination_and_length": same_end},
        "pipeline_ok": checks_ok})
    print(json.dumps({"run": name, "termination": {k: v["termination"]["class"] for k, v in results.items()},
                      "counters_a": a["counters"], "elapsed": {k: v["elapsed_seconds"] for k, v in results.items()},
                      "replay_run": verification["replay_run"], "meaning_comparison": {k: comparison[k] for k in ("equal", "compared", "bound", "lengths",
                                                                                                                  "same_termination_and_length")},
                      "correspondence_problems": corr, "anomalies_a": len(a["anomalies"]), "pipeline_ok": checks_ok}, ensure_ascii=False, indent=1))
    return 0 if checks_ok else 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="python -m tools.verification_ai.run_v0")
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--out", required=True)
    r.add_argument("--engine-commit", required=True)
    r.add_argument("--deck0", default="hitmonchan-dewgong")
    r.add_argument("--deck1", default="venusaur-parasect")
    r.add_argument("--game-seed", type=int, default=1)
    r.add_argument("--policy-seed", type=int, default=1)
    r.add_argument("--host-seed", type=int, default=1)
    m = sub.add_parser("manifest")
    m.add_argument("--out", required=True)
    m.add_argument("--run")
    m.add_argument("--command")
    m.add_argument("--exit-code", type=int)
    args = parser.parse_args(argv)
    out = Path(args.out)
    if args.cmd == "run":
        config = Config(deck0=args.deck0, deck1=args.deck1, game_seed=args.game_seed, policy_seed=args.policy_seed, host_seed=args.host_seed, limits=Limits())
        return execute(config, out, args.engine_commit, ["python", "-m", "tools.verification_ai.run_v0", *argv])
    if args.run:
        R.write_json(out / "verifier" / "runs" / args.run / "invocation.json", {"command": args.command, "exit_code": args.exit_code})
    sums = R.write_manifest(out)
    print(json.dumps({"files": len(sums), "sha256_json": R.sha256_file(out / "sha256.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
