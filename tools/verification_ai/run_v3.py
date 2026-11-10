"""V3-1 の実行の入口（通常の進行の中の negative。docs/verification-ai-v3-1.md 5 章）。単一のプロセスで、上限つきの対戦を 1 局ずつ順に実行する。プロセスの起動・検索・終了はしない。

    python -m tools.verification_ai.run_v3 run --out <保存先> --engine-commit <sha> --baseline <V1 の局のディレクトリ> --seeds 12 13

- 対戦の前に計画（``plan.json``: seed・変異を試す状態・種類・上限・予算）を書く
- 通常の進行は uniform-stage（V1 と同じ）。check が valid の入力を送る前に、決めた状態で変異を試し、元の入力を同じ取っ手で check して戻れることを確かめてから、通常の送信を 1 回
  だけする。古い取っ手の試験は、その入力の受理のあとに行う
- ``NegativeSession`` は、入口の要求（JSON）と、検証者の側の比べ（``judge``）だけを使う。方策の乱数・候補の取得を使わない（通常の進行の取っ手を失効させない）
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from . import judge as J
from . import negative as N
from . import records as R
from .policies import STAGE
from .run_v1 import check_record, engine_commands, game_header, now, read_jsonl, write_game
from .runner import Config, Limits, Runner, request

VERSION = "v3-1"
POSITIONS = 12  # 1 局で変異を試す状態の数
POSITION_RANGE = (2, 140)  # 受理の番号（V1 の stage-s12・s13 は 144・141 受理で終わる）
PER_POSITION = 2  # 1 つの状態で試す変異の種類（各種類 1 回まで）
MAX_REQUESTS = 60  # 1 局の変異の要求（check と submit を別に数える）


class NegativeSession:
    def __init__(self, seed: int, positions: list[int], *, per_position: int = PER_POSITION, max_requests: int = MAX_REQUESTS):
        self.seed = seed
        self.rng = N.negative_rng(seed)  # 種類の順・変異の中の選び方（plan_positions とは別の Random。同じ種の文字列）
        self.positions = set(positions)
        self.per_position = per_position
        self.max_requests = max_requests
        self.requests = {"check": 0, "submit": 0}
        self.recovery_checks = 0
        self.records: list[dict[str, Any]] = []
        self.done: set[int] = set()
        self.executed: Counter = Counter()
        self.pending_stale: dict[str, Any] | None = None

    # ---------------------------------------------------------------- ランナーからの呼び出し

    def before_submit(self, runner, actor, endpoint, entry, candidate, stages, handle, choices) -> None:
        position = runner.position
        if actor not in (0, 1) or position not in self.positions or position in self.done:
            return
        self.done.add(position)
        order = list(N.MUTATION_TYPES)
        self.rng.shuffle(order)
        order.sort(key=lambda kind: self.executed[kind])  # 試した回数の少ない種類から（同じ回数は乱数の順）
        tried = 0
        sent_any = False
        for index, kind in enumerate(order):
            if tried >= self.per_position:
                for rest in order[index:]:  # V3-3: 1 つの状態の種類の上限で試さなかった種類を記録する（要求は送らない）
                    self._record({"position": position, "attempt": entry["n"], "actor": actor, "candidate_kind": candidate["kind"], "mutation": rest,
                                  "status": N.NOT_RUN, "reason": "per_position_limit"}, runner)
                break
            base = {"position": position, "attempt": entry["n"], "actor": actor, "candidate_kind": candidate["kind"], "mutation": kind,
                    "base_choices": list(choices), "handle_for_reference": dict(handle)}
            if kind == "stale_after_accept":
                if self._room() < 2:
                    self._record({**base, "status": "not_run", "reason": "request_budget"}, runner)
                    continue
                self.pending_stale = {**base, "endpoint": endpoint, "handle": dict(handle), "choices": list(choices)}
                tried += 1
                continue
            if kind == "wrong_actor":
                target, mutated, change = runner.endpoints[1 - actor], list(choices), {"endpoint": f"player{1 - actor}"}
            else:
                mutated, change = N.mutate(kind, stages, list(choices), self.rng)
                if mutated is None:
                    self._record({**base, "status": N.outcome_status(change), **change}, runner)
                    continue
                if not N.single_difference(list(choices), mutated):
                    self._record({**base, "status": "not_applicable", "reason": "not_single_difference", "mutated_choices": mutated}, runner)
                    continue
                target = endpoint
            if self._room() < 2:
                self._record({**base, "status": "not_run", "reason": "request_budget"}, runner)
                break
            self._send(runner, {**base, "change": change, "mutated_choices": mutated}, target, handle, mutated, kind)
            tried += 1
            sent_any = True
        if sent_any:
            self._recover(runner, actor, endpoint, entry, handle, choices)

    def after_accept(self, runner, actor, endpoint, entry) -> None:
        pending, self.pending_stale = self.pending_stale, None
        if pending is None:
            return
        if pending["attempt"] != entry["n"]:  # 試験の元の入力が受理されなかった（拒否・断りのあと別の入力で受理）: 試さず記録する
            self._record({k: v for k, v in pending.items() if k not in ("endpoint", "handle", "choices")} | {"status": "not_run", "reason": "base_not_accepted"},
                         runner)
            return
        record = {k: v for k, v in pending.items() if k not in ("endpoint", "handle", "choices")}
        before = J.snapshot(runner.game, runner.hub)
        check = request(pending["endpoint"], "check", **pending["handle"], choices=pending["choices"])
        self.requests["check"] += 1
        responses = [("check", check)]
        if not (check.get("response") or {}).get("valid"):  # check が古いと断ったときだけ submit も送る（通ったなら送らない: 元の入力を正常に送り直さない）
            sent = request(pending["endpoint"], "submit", **pending["handle"], choices=pending["choices"], operation_id=f"{runner.config.run_id}-neg-stale")
            self.requests["submit"] += 1
            responses.append(("submit", sent))
        after = J.snapshot(runner.game, runner.hub)
        self._judge_and_store(runner, {**record, "change": {"timing": "after_accept"}, "mutated_choices": pending["choices"]}, "stale_after_accept",
                              responses, before, after)

    def summary(self) -> dict[str, Any]:
        statuses = Counter((r["mutation"], r.get("status")) for r in self.records if r.get("type") == "negative")
        verdicts = Counter((r["mutation"], r.get("verdict")) for r in self.records if r.get("type") == "negative" and r.get("verdict"))
        recov = Counter(r.get("verdict") for r in self.records if r.get("type") == "negative_recovery")
        return {"seed": self.seed, "positions_planned": sorted(self.positions), "positions_reached": sorted(self.done), "requests": dict(self.requests),
                "recovery_checks": self.recovery_checks, "status": {f"{k}:{s}": n for (k, s), n in sorted(statuses.items())},
                "verdicts": {f"{k}:{v}": n for (k, v), n in sorted(verdicts.items())}, "recovery_verdicts": dict(recov),
                "pending_stale_unrun": self.pending_stale is not None}

    # ---------------------------------------------------------------- 内部

    def _room(self) -> int:
        return self.max_requests - self.requests["check"] - self.requests["submit"]

    def _record(self, record, runner) -> None:
        row = {"type": "negative", **record}
        self.records.append(row)
        runner.trace.append(row)

    def _send(self, runner, record, target, handle, choices, kind) -> None:
        before = J.snapshot(runner.game, runner.hub)
        check = request(target, "check", **handle, choices=choices)
        self.requests["check"] += 1
        responses = [("check", check)]
        after_check = J.snapshot(runner.game, runner.hub)
        if not J.compare(before, after_check) and not (check.get("response") or {}).get("valid"):
            sent = request(target, "submit", **handle, choices=choices, operation_id=f"{runner.config.run_id}-neg-{len(self.records) + 1}")
            self.requests["submit"] += 1
            responses.append(("submit", sent))
        after = J.snapshot(runner.game, runner.hub)
        self._judge_and_store(runner, record, kind, responses, before, after)

    def _judge_and_store(self, runner, record, kind, responses, before, after) -> None:
        code, refetch = N.EXPECTED[kind]
        changed = J.compare(before, after)
        verdict, reasons = J.judge_negative(code, refetch, responses, changed)
        self.executed[kind] += 1
        self._record({**record, "status": "run", "expected": {"code": code, "refetch_required": refetch}, "responses": [{"request": k, "response": r} for k, r in responses],
                      "before": before, "after": after, "changed": changed, "verdict": verdict, "reasons": reasons}, runner)
        if changed or verdict == J.SUSPECT:
            runner.negative_stop({"mutation": kind, "position": record["position"], "changed": changed, "reasons": reasons})

    def _recover(self, runner, actor, endpoint, entry, handle, choices) -> None:
        before = J.snapshot(runner.game, runner.hub)
        check = request(endpoint, "check", **handle, choices=list(choices))
        self.recovery_checks += 1
        after = J.snapshot(runner.game, runner.hub)
        changed = J.compare(before, after)
        verdict, reasons = J.judge_recovery(check, changed)
        row = {"type": "negative_recovery", "position": runner.position, "attempt": entry["n"], "actor": actor, "response": check, "before": before, "after": after,
               "changed": changed, "verdict": verdict, "reasons": reasons}
        self.records.append(row)
        runner.trace.append(row)
        if verdict != J.EXPECTED:
            runner.negative_stop({"recovery": True, "position": runner.position, "reasons": reasons})


def run(out: Path, engine_commit: str, baseline: Path, seeds: list[int], budget: float, argv: list[str],
        deck0="hitmonchan-dewgong", deck1="venusaur-parasect") -> int:
    group = f"v3-1-{deck0}-vs-{deck1}-default"
    gdir = out / "verifier" / "runs" / group
    if gdir.exists():
        raise SystemExit(f"{gdir} はすでにある（既存の証跡を上書きしない）")
    positions = {s: N.plan_positions(s, POSITIONS, *POSITION_RANGE) for s in seeds}
    R.write_json(gdir / "plan.json", {
        "written": now(), "seeds": seeds, "seed_use": "ゲーム・方策・ホストの seed を同じ値にする（V1 と同じ）。変異の乱数は kyuura-vai-v3:negative:<seed>",
        "policy": "uniform", "distribution": STAGE, "positions": {str(s): p for s, p in positions.items()},
        "positions_rule": f"plan_positions(seed, {POSITIONS}, {POSITION_RANGE[0]}, {POSITION_RANGE[1]}): 受理の番号の範囲から変異の乱数で選ぶ。プレイヤーの状態だけ（ホストの状態は試さない）",
        "per_position": PER_POSITION, "type_order": "変異の乱数で並べたあと、試した回数の少ない種類から。前提を満たさない種類は not_applicable で次へ",
        "mutation_types": list(N.MUTATION_TYPES), "max_requests_per_game": MAX_REQUESTS, "budget_seconds": budget, "limits_per_game": Limits().__dict__,
        "baseline": {str(s): str(baseline / f"stage-s{s}").replace("\\", "/") for s in seeds},
        "note": "対戦の前に書いた計画。結果を見て seed・位置・局を変えない。届かなかった変異は未到達として残す"})
    ident = R.identity(engine_commit)
    start = time.monotonic()
    games, problems = [], []
    for seed in seeds:
        if time.monotonic() - start >= budget:
            games.append({"seed": seed, "status": "not_run", "reason": "budget_exceeded"})
            continue
        config = Config(game_seed=seed, policy_seed=seed, host_seed=seed, run_id=f"{group}-s{seed}")
        session = NegativeSession(seed, positions[seed])
        started = now()
        result = Runner(config, negative=session).run()
        finished = now()
        verification = check_record(result)
        base = baseline / f"stage-s{seed}"
        base_meaning = read_jsonl(base / "meaning.jsonl")
        base_result = json.loads((base / "result.json").read_text(encoding="utf-8"))
        base_record = json.loads((base / "full_record.json").read_text(encoding="utf-8"))
        meaning = R.meaning_sequence(result["trace"])
        comparison = R.compare_meanings(base_meaning, meaning, min(len(base_meaning), len(meaning)))
        comparison.update({"lengths": {"baseline": len(base_meaning), "run": len(meaning)},
                           "full_match": comparison["equal"] and len(base_meaning) == len(meaning),
                           "termination": {"baseline": base_result["termination"]["class"], "run": result["termination"]["class"]},
                           "engine_commands_equal": engine_commands(base_record) == engine_commands(result["record"].data)})
        verification["baseline_comparison"] = comparison
        d = gdir / f"s{seed}"
        write_game(d, game_header(config, ident, argv, result, started, finished), result, verification)
        R.write_jsonl(d / "negatives.jsonl", session.records)
        R.write_json(d / "negative_summary.json", result["negative"])
        normal = Counter((e.get("judge") or {}).get("verdict") for e in result["trace"] if e.get("type") == "attempt" and e.get("judge"))
        game = {"seed": seed, "status": "run", "termination": result["termination"]["class"], "judge_termination": result["judge_termination"],
                "accepted": result["counters"]["accepted"], "turns": result["counters"]["turns"], "negative": result["negative"],
                "normal_submit_verdicts": dict(normal), "anomalies": [a["kind"] for a in result["anomalies"]],
                "replay_run": verification["replay_run"]["status"], "replay_matches_expectation": verification["replay_run"]["matches_expectation"],
                "correspondence_problems": len(verification["correspondence_problems"]), "baseline": {k: comparison[k] for k in ("equal", "full_match", "lengths",
                                                                                                                              "termination", "engine_commands_equal")},
                "elapsed_seconds": result["elapsed_seconds"]}
        games.append(game)
        if not (game["replay_matches_expectation"] and not game["correspondence_problems"]):
            problems.append(f"s{seed}: replay_run・記録の対応")
        print(json.dumps({k: game[k] for k in ("seed", "termination", "accepted", "turns", "replay_run", "baseline", "elapsed_seconds")} |
                         {"negative": {k: result["negative"][k] for k in ("requests", "recovery_checks", "verdicts", "recovery_verdicts")}}, ensure_ascii=False))
    total = round(time.monotonic() - start, 3)
    suspects = sum(n for g in games if g["status"] == "run" for key, n in g["negative"]["verdicts"].items() if key.endswith(":suspect"))
    suspects += sum(g["normal_submit_verdicts"].get("suspect", 0) for g in games if g["status"] == "run")
    suspects += sum(1 for g in games if g["status"] == "run" and g["judge_termination"]["verdict"] == "suspect")
    aggregate = {"games": games, "total_seconds": total, "suspect_count": suspects, "tool_problems": problems,
                 "note": "suspect は不具合の疑いの件数（確定ではない）。known・expected と足さない"}
    R.write_json(gdir / "aggregate.json", aggregate)
    R.write_json(out / "public" / "runs" / group / "summary.json", {
        "tool": {"name": "tools.verification_ai", "version": VERSION}, "engine": {"git_commit": engine_commit, "version": ident["version"],
                                                                               "behavior_digest": ident["implementation"]["behavior_digest"]},
        "decks": {"0": deck0, "1": deck1}, "convention_set": "default", "suspect_count": suspects, "total_seconds": total,
        "games": [{k: g.get(k) for k in ("seed", "status", "termination", "judge_termination", "accepted", "turns", "normal_submit_verdicts", "replay_run",
                                         "replay_matches_expectation", "correspondence_problems", "baseline")}
                  | {"negative": {k: (g.get("negative") or {}).get(k) for k in ("requests", "recovery_checks", "status", "verdicts", "recovery_verdicts")}}
                  for g in games]})
    print(json.dumps({"group": group, "total_seconds": total, "suspect_count": suspects, "tool_problems": problems}, ensure_ascii=False))
    if problems or any(g["status"] != "run" for g in games):
        return 1
    return 3 if suspects else 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="python -m tools.verification_ai.run_v3")
    sub = parser.add_subparsers(dest="cmd", required=True)
    rn = sub.add_parser("run")
    rn.add_argument("--out", required=True)
    rn.add_argument("--engine-commit", required=True)
    rn.add_argument("--baseline", required=True)
    rn.add_argument("--seeds", type=int, nargs="+", required=True)
    rn.add_argument("--budget-seconds", type=float, default=600.0)
    args = parser.parse_args(argv)
    if len(args.seeds) > 2:
        parser.error("V3-1 は 2 局まで")
    return run(Path(args.out), args.engine_commit, Path(args.baseline), args.seeds, args.budget_seconds, ["python", "-m", "tools.verification_ai.run_v3", *argv])


if __name__ == "__main__":
    raise SystemExit(main())
