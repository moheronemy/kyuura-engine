"""V2 の実行の入口（docs/verification-ai-v2.md 5 章）。単一のプロセスで、上限つきの対戦を 1 局ずつ順に実行する。プロセスの起動・検索・終了はしない。

    python -m tools.verification_ai.run_v2 run --out <保存先> --engine-commit <sha> --reuse <V1 の局のディレクトリ> --seeds 11 12 13 --epsilon 0.25

- 対戦の前に計画（``plan.json``: seed・方式・ε・再利用する V1 の局・事前に選んだ再現の条件・上限・予算）を書く
- rules と mixed の局を実行する。uniform-stage は V1 の局（同じデッキ・規約集合・seed・上限）を再利用し、新しく実行しない（再利用の根拠は文書の 5.1 節）
- 比べる表（``comparison.json``）を作る。再利用した V1 の局にない計測（エピソード・サイドの枚数の変化）は欠測（``unmeasured``）
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from . import records as R
from .policies import STAGE
from .run_v1 import check_record, game_header, now, write_game
from .runner import Config, Limits, run_game

VERSION = "v2"
UNMEASURED = "unmeasured"


def stage_totals(metrics: dict[str, Any]) -> dict[str, int]:
    keys = ("offered_fetches", "in_scope_fetches", "selected", "build_ok", "check_valid", "check_invalid", "submitted", "already_tried")
    out = {k: sum(v[k] for v in metrics["kinds"].values()) for k in keys}
    out["build_failed"] = sum(sum(v["build_failed"].values()) for v in metrics["kinds"].values())
    for outcome in ("accepted", "refused", "rejected", "failed"):
        out[outcome] = sum(v["outcome"].get(outcome, 0) for v in metrics["kinds"].values())
    return out


def row(label: str, source: str, result: dict[str, Any], verification: dict[str, Any]) -> dict[str, Any]:
    m = result["metrics"]
    kinds = m["kinds"]
    accepted = {k: v["outcome"].get("accepted", 0) for k, v in kinds.items() if v["outcome"].get("accepted")}
    axes = m["axes"]
    has_v2 = source == "new"  # 再利用した V1 の局は V2 の計測（エピソード・サイドの枚数の変化）を持たない
    detail = result["termination"].get("detail") or {}
    return {
        "game": label, "source": source, "termination": result["termination"]["class"],
        "halt": (detail.get("halt") or {}).get("diagnostic_id"), "winner_reference": ((detail.get("result") or {}).get("winner")),
        "turns": result["counters"]["turns"], "operations": result["counters"]["operations"], "accepted": result["counters"]["accepted"],
        "attempts": result["counters"]["attempts"], "retry_same_input": result["counters"]["retry_same_input"], "unbuildable": result["counters"]["unbuildable"],
        "stages": stage_totals(m) if kinds else {}, "accepted_kinds": accepted, "use_attack_accepted": accepted.get("use_attack", 0),
        "take_prize_accepted": accepted.get("take_prize", 0), "promote_active_accepted": accepted.get("promote_active", 0),
        "decision_kinds": axes.get("decision_kind", {}), "stage_features": result["coverage"].get("stage_feature", {}),
        "excluded": {k: v["excluded"] for k, v in kinds.items() if v["excluded"]},
        "prize_count_decrease": axes.get("prize_count_decrease", {}) if has_v2 else UNMEASURED,
        "episode_mode": axes.get("episode_mode", {}) if has_v2 else UNMEASURED,
        "episode_attempts": axes.get("episode_attempts", {}) if has_v2 else UNMEASURED,
        "knock_outs": UNMEASURED,  # 公開の応答・更新から確実に数えられない（きぜつのログの見え方を使っていない）。推測しない
        "replay_run": verification["replay_run"]["status"], "replay_matches_expectation": verification["replay_run"]["matches_expectation"],
        "correspondence_problems": len(verification["correspondence_problems"]),
    }


def run(out: Path, engine_commit: str, reuse: Path, seeds: list[int], epsilon: float, budget: float, repro_seed: int, argv: list[str],
        deck0="hitmonchan-dewgong", deck1="venusaur-parasect") -> int:
    group = f"v2-{deck0}-vs-{deck1}-default"
    gdir = out / "verifier" / "runs" / group
    if gdir.exists():
        raise SystemExit(f"{gdir} はすでにある（既存の証跡を上書きしない）")
    new = [{"policy": "rules", "seed": s, "game": f"rules-s{s}"} for s in seeds] + \
          [{"policy": "mixed", "epsilon": epsilon, "seed": s, "game": f"mixed-e{epsilon}-s{s}"} for s in seeds]
    reused = [{"policy": "uniform", "distribution": STAGE, "seed": s, "game": f"stage-s{s}", "source": str((reuse / f"stage-s{s}")).replace("\\", "/")}
              for s in seeds]
    R.write_json(gdir / "plan.json", {
        "written": now(), "seeds": seeds, "seed_use": "ゲーム・方策・ホストの seed を同じ値にする（V1 と同じ）", "epsilon": epsilon,
        "new_games": new, "reused_games": reused, "limits_per_game": Limits().__dict__, "budget_seconds": budget,
        "reproduction": {"policy": "uniform", "distribution": STAGE, "seed": repro_seed, "baseline": str(reuse / f"stage-s{repro_seed}").replace("\\", "/"),
                         "how": "python -m tools.verification_ai.run_v1 reproduce --label v2（この計画のあとに 1 回だけ）",
                         "why": "V2 のコードで均等の選択の経路が V1 と同じかを確かめ、再利用の根拠を補う"},
        "note": "対戦の前に書いた計画。結果を見て seed・局を差し替えない・増やさない。予算を超えたら残りは実行しない"})
    ident = R.identity(engine_commit)
    start = time.monotonic()
    rows, games = [], []
    for item in reused:
        d = Path(item["source"])
        result = json.loads((d / "result.json").read_text(encoding="utf-8"))
        verification = json.loads((d / "verification.json").read_text(encoding="utf-8"))
        rows.append(row(item["game"], "reused_v1", result, verification))
    for item in new:
        if time.monotonic() - start >= budget:
            games.append({**item, "status": "not_run", "reason": "budget_exceeded"})
            continue
        config = Config(deck0=deck0, deck1=deck1, game_seed=item["seed"], policy_seed=item["seed"], host_seed=item["seed"], policy=item["policy"],
                        epsilon=item.get("epsilon", 0.25), run_id=f"{group}-{item['game']}")
        started = now()
        result = run_game(config)
        finished = now()
        verification = check_record(result)
        write_game(gdir / item["game"], game_header(config, ident, argv, result, started, finished), result, verification)
        games.append({**item, "status": "run"})
        rows.append(row(item["game"], "new", result, verification))
        print(json.dumps({"game": item["game"], "termination": result["termination"]["class"], "accepted": result["counters"]["accepted"],
                          "turns": result["counters"]["turns"], "replay_run": verification["replay_run"]["status"], "elapsed": result["elapsed_seconds"]},
                         ensure_ascii=False))
    total = round(time.monotonic() - start, 3)
    comparison = {"games": rows, "new_games_run": sum(g["status"] == "run" for g in games), "reused_games": len(reused), "not_run": [g for g in games if g["status"] != "run"],
                  "total_seconds": total, "note": "勝ちは参考値。少数の局で、方式の差を優先順位の効果と断定しない（同じ seed でも方式でゲームの乱数の消費と操作の列が変わる）"}
    R.write_json(gdir / "comparison.json", comparison)
    R.write_json(out / "public" / "runs" / group / "summary.json", {"tool": {"name": "tools.verification_ai", "version": VERSION},
                                                                   "engine": {"git_commit": engine_commit, "version": ident["version"],
                                                                              "behavior_digest": ident["implementation"]["behavior_digest"]},
                                                                   "decks": {"0": deck0, "1": deck1}, "convention_set": "default", **comparison})
    ok = all(g["status"] == "run" for g in games) and all(r["replay_matches_expectation"] and not r["correspondence_problems"] for r in rows)
    print(json.dumps({"group": group, "total_seconds": total, "all_ok": ok}, ensure_ascii=False))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="python -m tools.verification_ai.run_v2")
    sub = parser.add_subparsers(dest="cmd", required=True)
    rn = sub.add_parser("run")
    rn.add_argument("--out", required=True)
    rn.add_argument("--engine-commit", required=True)
    rn.add_argument("--reuse", required=True)
    rn.add_argument("--seeds", type=int, nargs="+", required=True)
    rn.add_argument("--epsilon", type=float, default=0.25)
    rn.add_argument("--repro-seed", type=int, required=True)
    rn.add_argument("--budget-seconds", type=float, default=1200.0)
    args = parser.parse_args(argv)
    if len(args.seeds) > 3:
        parser.error("V2 の新しい局は 2 方式 × seed 3 個まで")
    return run(Path(args.out), args.engine_commit, Path(args.reuse), args.seeds, args.epsilon, args.budget_seconds, args.repro_seed,
               ["python", "-m", "tools.verification_ai.run_v2", *argv])


if __name__ == "__main__":
    raise SystemExit(main())
