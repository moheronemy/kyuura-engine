"""V3-2 の実行の入口（カツラの固定の到達例。docs/verification-ai-v3-2.md 6 章）。単一のプロセスで、上限つきの対戦を 1 局ずつ順に実行する。プロセスの起動・検索・終了はしない。

    python -m tools.verification_ai.run_v3_2 run --out <保存先> --engine-commit <sha>

- 局 1・2: 固定の到達の列（``FixedReach``。new_game から公開の API の候補・入力・check・submit だけで、準備 → ジャンケン（0）→ カツラ → エネルギーをつける）で、
  エネルギーを 1 枚（局 1）・2 枚（局 2）つける。つける操作の送信の前に、V3-2 の変異（1 条件）を試し、元の入力の check で復帰を確かめてから通常の送信を 1 回だけする。
  つけ終えたら止める（``script_complete``。計画した止まり方）
- 局 3: BoundaryPolicy の短い確かめ（同じデッキ・seed。方策が自分で選ぶ。上限 40 操作）
- 固定の到達例のデッキは、``tests/test_legal_actions_u7_5g_energy2.py`` の ``BLAINE_DECK``・``BLAINE_SEED`` を、出典と内容の sha256 を記録して道具に写したもの
  （実行時に tests を読まない。固定デッキではない）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from . import actions as B
from . import judge as J
from . import negative as N
from . import records as R
from .policies import UniformPolicy, host_seed, player_seed
from .run_v1 import check_record, game_header, now, write_game
from .run_v3 import NegativeSession
from .runner import Config, Limits, Runner, request

VERSION = "v3-2"
FIRE = "PMCG1-098"
BLAINES_GROWLITHE = "PMCG6-027"
BLAINE_TRAINER = "PMCG6-093"
BLAINE_DECK = (BLAINES_GROWLITHE,) * 4 + (BLAINE_TRAINER,) * 4 + (FIRE,) * 52
BLAINE_SEED = 1
DECK_SOURCE = {"file": "tests/test_legal_actions_u7_5g_energy2.py", "names": ["BLAINE_DECK", "BLAINE_SEED"], "lines": [224, 225], "base_commit": "e26df79",
               "content_sha256": hashlib.sha256(json.dumps(list(BLAINE_DECK)).encode("utf-8")).hexdigest(), "cards": 60}
BOUNDARY_OPERATIONS = 40


class ScriptMiss(Exception):
    """固定の到達の列の想定した候補・選べるものが応答にない（列を推測で続けない）。"""


class FixedReach:
    """固定の到達の列の状態（3 つの主体で共有）。``energy2`` が真なら 2 枚目もつける。"""

    def __init__(self, energy2: bool):
        self.energy2 = energy2
        self.step = "setup"  # setup → blaine → attach → done

    def until(self, runner, entry) -> bool:
        kind = entry["candidate"]["kind"]
        if self.step in ("setup", "blaine") and entry["actor"] == 0 and kind == "play_trainer":
            self.step = "attach"
            return False
        if self.step == "attach" and entry["actor"] == 0 and kind == "attach_energy":
            self.step = "done"
            return True
        return False


class FixedReachPolicy(UniformPolicy):
    """固定の到達の列の選び手（方策ではない。記録の名前 ``fixed-reach``）。API の応答の候補の種類と、選べるものの公開の項目（``card_id``）・段の役割（``role``）で選ぶ。
    カード名からコマンドを作らない（入力は行動生成が段の契約から作り、check・submit を通す）。乱数を使わない。"""

    name = "fixed-reach"
    version = 1

    def __init__(self, seed: str, distribution: str, reach: FixedReach):
        super().__init__(seed)
        self.distribution = "fixed-reach"
        self.reach = reach

    def choose(self, purpose, items, context):
        stage = context.get("stage") or {}
        candidate = context.get("candidate") or {}
        if purpose == "candidate":
            kinds = [c["kind"] for c in items]
            if "end_turn" in kinds and self.reach.step == "setup":  # 番の操作の場面（プレイヤー 0 の最初の番）に入った
                self.reach.step = "blaine"
            want = {"blaine": "play_trainer", "attach": "attach_energy"}.get(self.reach.step)
            if want is None:
                return 0, "fixed-reach:first_candidate"
            if want not in kinds:
                raise ScriptMiss(f"{want} が候補にない: {kinds}")
            return kinds.index(want), f"fixed-reach:{want}"
        if purpose == "value":
            if stage.get("meaning") == "player":
                return items.index(0), "fixed-reach:janken_winner_0"
            return len(items) - 1, "fixed-reach:value_max"
        if purpose == "count":
            if candidate.get("kind") == "place_starting":
                return (items.index(1) if 1 in items else 0), "fixed-reach:bench_1"
            if stage.get("role") == "energy2":
                want = 1 if self.reach.energy2 else 0
                if want not in items:
                    raise ScriptMiss(f"energy2 の数 {want} を選べない: {items}")
                return items.index(want), f"fixed-reach:energy2_count_{want}"
            return 0, "fixed-reach:first_count"
        if purpose == "option":
            by_id = {o["id"]: o for o in stage.get("options", [])}
            source = {"play_trainer": BLAINE_TRAINER}.get(candidate.get("kind"))
            if candidate.get("kind") == "attach_energy":
                source = {"energy": FIRE, "target": BLAINES_GROWLITHE, "energy2": FIRE}.get(stage.get("role"))
            if source is None:
                return 0, "fixed-reach:first_option"
            for i, oid in enumerate(items):
                if by_id.get(oid, {}).get("card_id") == source:
                    return i, f"fixed-reach:{stage.get('role') or 'card'}:{source}"
            raise ScriptMiss(f"{source} の選べるものがない（段 {stage.get('stage')}）")
        return UniformPolicy.choose(self, purpose, items, context)


class AttachNegativeSession(NegativeSession):
    """V3-2: プレイヤー 0 のエネルギーをつける操作（1 回目）の送信の前に、V3-2 の種類を決まった順に 1 回ずつ試す（前提を満たさない種類は not_applicable）。"""

    def __init__(self, seed: int):
        super().__init__(seed, [], per_position=len(N.V3_2_TYPES))
        self.fired = False
        self.attach_stages = None

    def before_submit(self, runner, actor, endpoint, entry, candidate, stages, handle, choices) -> None:
        if self.fired or actor != 0 or candidate["kind"] != "attach_energy":
            return
        self.fired = True
        self.attach_stages = stages
        self.done.add(runner.position)
        sent_any = False
        for kind in N.V3_2_TYPES:
            base = {"position": runner.position, "attempt": entry["n"], "actor": actor, "candidate_kind": candidate["kind"], "mutation": kind,
                    "base_choices": list(choices), "handle_for_reference": dict(handle)}
            if kind == "stale_after_accept":
                self.pending_stale = {**base, "endpoint": endpoint, "handle": dict(handle), "choices": list(choices)}
                continue
            if kind == "wrong_actor":
                target, mutated, change = runner.endpoints[1], list(choices), {"endpoint": "player1"}
            else:
                mutated, change = N.mutate(kind, stages, list(choices), self.rng)
                if mutated is None:
                    self._record({**base, "status": "not_applicable", **change}, runner)
                    continue
                if not N.single_difference(list(choices), mutated):
                    self._record({**base, "status": "not_applicable", "reason": "not_single_difference", "mutated_choices": mutated}, runner)
                    continue
                target = endpoint
            if self._room() < 2:
                self._record({**base, "status": "not_run", "reason": "request_budget"}, runner)
                continue
            self._send(runner, {**base, "change": change, "mutated_choices": mutated}, target, handle, mutated, kind)
            sent_any = True
        if sent_any:
            self._recover(runner, actor, endpoint, entry, handle, choices)


def path_report(stages: list[dict[str, Any]], choices: list[Any]) -> dict[str, Any]:
    """実際の応答の options_by_path の形（path_stages・鍵・参照の eligible と処理可能性・鍵ごとに使えない選ぶもの・省いたときの入力の形）。"""
    path = next((s for s in stages if "path_stages" in s), None)
    if path is None:
        return {"present": False}
    by_id = {o["id"]: o for s in stages for o in s.get("options", [])}
    ids = [o["id"] for o in path.get("options", [])]
    keys = {}
    for key, refs in path.get("options_by_path", {}).items():
        upstream = key.split("/")
        allowed = [r["option"] for r in refs]
        keys[key] = {"upstream": [{"id": u, "card_id": by_id.get(u, {}).get("card_id"), "pokemon": by_id.get(u, {}).get("pokemon")} for u in upstream],
                     "refs": [{"option": r["option"], "eligible": r.get("eligible"), "processability": r.get("processability"),
                               "card_id": by_id.get(r["option"], {}).get("card_id")} for r in refs],
                     "not_usable_here": [i for i in ids if i not in allowed]}
    return {"present": True, "stage": path["stage"], "path_stages": path["path_stages"], "count": path["count"], "decline": path.get("decline"),
            "options": [{"id": o["id"], "card_id": o.get("card_id"), "eligible": o.get("eligible"), "processability": o.get("processability")} for o in path["options"]],
            "keys": keys, "declined_input_length": len(path["path_stages"]), "chosen": choices}


def attachment_check(runner, result) -> dict[str, Any]:
    """受理のあとの観測（プレイヤー 0 の入口）と完全な記録から、実際につけたものを確かめる。"""
    attach = next(e for e in result["trace"] if e.get("type") == "attempt" and e["candidate"]["kind"] == "attach_energy"
                  and (e.get("submit") or {}).get("outcome") == "accepted")
    target = next(m["option"] for m in attach["meaning"] if m["stage"] == 2)
    rows = [op for op in result["record"].data["operations"] if (op.get("command") or {}).get("type") == "attach_energy" and op["outcome"] == "accepted"]
    command = rows[-1]["command"] if rows else None
    before_view = next(r["view"] for r in reversed(runner.actor_logs[0]) if r.get("type") == "position" and r["position"] == attach["position"])
    after_view = request(runner.endpoints[0], "view")

    def energy_on(view):
        me = view["observation"]["players"][0]
        for pokemon in [me.get("active")] + list(me.get("bench") or []):
            if pokemon and pokemon.get("pokemon_id") == target.get("pokemon"):
                return [e.get("card_id") for e in pokemon.get("energy", [])]
        return None

    before, after = energy_on(before_view), energy_on(after_view)
    return {"target_pokemon": target.get("pokemon"), "command": command, "energy2_in_command": None if command is None else command.get("energy2") is not None,
            "fire_before": None if before is None else before.count(FIRE), "fire_after": None if after is None else after.count(FIRE),
            "attached_by_observation": None if before is None or after is None else after.count(FIRE) - before.count(FIRE),
            "input_length": len(attach["choices"])}


def run(out: Path, engine_commit: str, argv: list[str]) -> int:
    group = "v3-2-blaine-s1-default"
    gdir = out / "verifier" / "runs" / group
    if gdir.exists():
        raise SystemExit(f"{gdir} はすでにある（既存の証跡を上書きしない）")
    games = [{"game": "one-card", "purpose": "固定の到達の列で、エネルギーを 1 枚つける（3 段目を省く）。つける前に V3-2 の変異", "energy2": False},
             {"game": "two-card", "purpose": "同じ固定の到達の列で、エネルギーを 2 枚つける（3 段目 energy2）。つける前に V3-2 の変異", "energy2": True},
             {"game": "boundary", "purpose": f"BoundaryPolicy の短い確かめ（方策が選ぶ。上限 {BOUNDARY_OPERATIONS} 操作）"}]
    R.write_json(gdir / "plan.json", {
        "written": now(), "deck": DECK_SOURCE, "seed": BLAINE_SEED, "seed_use": "ゲーム・方策・ホストの seed を同じ値にする", "conventions": "default",
        "games": games, "negative": {"where": "プレイヤー 0 のエネルギーをつける操作（1 回目）の送信の前", "types_in_order": list(N.V3_2_TYPES),
                                     "random": "kyuura-vai-v3:negative:1（変異の中の選び方だけ）", "max_requests_per_game": 60},
        "stop": "局 1・2 はつける操作の受理（と古い取っ手の試験）のあとに script_complete で止める。局 3 は 40 操作で止める（limit_operations）",
        "limits_per_game": Limits().__dict__, "budget_seconds": 600, "judge_rules_version": J.JUDGE_RULES_VERSION,
        "note": "対戦の前に書いた計画。結果を見て seed・局・変異を変えない。届かなければ未到達として残す"})
    ident = R.identity(engine_commit)
    start = time.monotonic()
    rows, problems = [], []
    for item in games:
        if time.monotonic() - start >= 600:
            rows.append({**item, "status": "not_run", "reason": "budget_exceeded"})
            continue
        if item["game"] == "boundary":
            config = Config(game_seed=BLAINE_SEED, policy_seed=BLAINE_SEED, host_seed=BLAINE_SEED, policy="boundary", profile="boundary",
                            decklists=(BLAINE_DECK, BLAINE_DECK), limits=Limits(operations=BOUNDARY_OPERATIONS), run_id=f"{group}-boundary")
            runner = Runner(config)
            session = None
        else:
            reach = FixedReach(item["energy2"])
            config = Config(game_seed=BLAINE_SEED, policy_seed=BLAINE_SEED, host_seed=BLAINE_SEED, decklists=(BLAINE_DECK, BLAINE_DECK),
                            run_id=f"{group}-{item['game']}")
            session = AttachNegativeSession(BLAINE_SEED)
            runner = Runner(config, policy_factory=lambda seed, dist, r=reach: FixedReachPolicy(seed, dist, r), negative=session, until=reach.until)
        started = now()
        result = runner.run()
        finished = now()
        verification = check_record(result)
        d = gdir / item["game"]
        header = {**game_header(config, ident, argv, result, started, finished), "deck_source": DECK_SOURCE, "purpose": item["purpose"],
                  "judge_rules_version": J.JUDGE_RULES_VERSION, "decklists": None}
        write_game(d, header, result, verification)
        row = {**item, "status": "run", "termination": result["termination"]["class"], "termination_detail": result["termination"]["detail"],
               "accepted": result["counters"]["accepted"], "replay_run": verification["replay_run"]["status"],
               "replay_matches_expectation": verification["replay_run"]["matches_expectation"], "correspondence_problems": len(verification["correspondence_problems"]),
               "anomalies": [a["kind"] for a in result["anomalies"]], "elapsed_seconds": result["elapsed_seconds"]}
        if session is not None:
            R.write_jsonl(d / "negatives.jsonl", session.records)
            stages = session.attach_stages or []
            attach = next((e for e in result["trace"] if e.get("type") == "attempt" and e["candidate"]["kind"] == "attach_energy"), None)
            report = path_report(stages, attach["choices"] if attach else [])
            R.write_json(d / "options_by_path.json", report)
            check = attachment_check(runner, result) if result["termination"]["class"] == "script_complete" else {"reached": False}
            R.write_json(d / "attachment.json", check)
            normal = Counter((e.get("judge") or {}).get("verdict") for e in result["trace"] if e.get("type") == "attempt" and e.get("judge"))
            row.update({"negative": result["negative"], "normal_submit_verdicts": dict(normal), "judge_termination": result.get("judge_termination"),
                        "options_by_path": {k: report.get(k) for k in ("present", "path_stages", "count", "decline")} | {"keys": len(report.get("keys", {}))},
                        "attachment": check})
        else:
            classes = Counter(e.get("candidate_class") for e in result["trace"] if e.get("type") == "attempt" and "candidate_class" in e)
            inputs = Counter((e.get("input_processability") or {}).get("class") for e in result["trace"] if e.get("type") == "attempt" and "input_processability" in e)
            offered = result["metrics"]["axes"].get("offered_processability", {})
            row.update({"boundary": {"offered_processability_fetches": offered, "chosen_candidate_class": dict(classes), "built_input_class": dict(inputs),
                                     "unverified_offered": offered.get("unverified", 0), "unverified_chosen": classes.get("unverified", 0),
                                     "reasons": Counter(e["candidate_reason"].split(":")[2] for e in result["trace"]
                                                        if e.get("type") == "attempt" and e["candidate_reason"].startswith("boundary:")),
                                     "accepted_kinds": {k: v["outcome"].get("accepted", 0) for k, v in result["metrics"]["kinds"].items() if v["outcome"].get("accepted")}}})
        rows.append(row)
        if not (row["replay_matches_expectation"] and not row["correspondence_problems"]):
            problems.append(f"{item['game']}: replay_run・記録の対応")
        print(json.dumps({k: row.get(k) for k in ("game", "termination", "accepted", "replay_run", "attachment", "elapsed_seconds")}
                         | ({"negative": {k: row["negative"][k] for k in ("requests", "recovery_checks", "status", "verdicts", "recovery_verdicts")}} if "negative" in row else {})
                         | ({"boundary": row["boundary"]} if "boundary" in row else {}), ensure_ascii=False, default=str))
    total = round(time.monotonic() - start, 3)
    suspects = sum(n for r in rows if r.get("negative") for k, n in r["negative"]["verdicts"].items() if k.endswith(":suspect"))
    suspects += sum((r.get("normal_submit_verdicts") or {}).get("suspect", 0) for r in rows)
    aggregate = {"games": rows, "total_seconds": total, "suspect_count": suspects, "tool_problems": problems, "judge_rules_version": J.JUDGE_RULES_VERSION}
    R.write_json(gdir / "aggregate.json", aggregate)
    R.write_json(out / "public" / "runs" / group / "summary.json", {
        "tool": {"name": "tools.verification_ai", "version": VERSION}, "engine": {"git_commit": engine_commit, "version": ident["version"],
                                                                               "behavior_digest": ident["implementation"]["behavior_digest"]},
        "deck": {"source": DECK_SOURCE["file"], "content_sha256": DECK_SOURCE["content_sha256"]}, "convention_set": "default", "suspect_count": suspects,
        "judge_rules_version": J.JUDGE_RULES_VERSION, "total_seconds": total,
        "games": [{k: r.get(k) for k in ("game", "status", "termination", "accepted", "replay_run", "replay_matches_expectation", "correspondence_problems",
                                         "normal_submit_verdicts", "options_by_path")}
                  | ({"negative": {k: r["negative"][k] for k in ("requests", "recovery_checks", "status", "verdicts", "recovery_verdicts")}} if r.get("negative") else {})
                  | ({"attachment": {k: (r.get("attachment") or {}).get(k) for k in ("energy2_in_command", "attached_by_observation", "input_length")}}
                     if r.get("attachment") else {})
                  | ({"boundary": {k: r["boundary"][k] for k in ("offered_processability_fetches", "chosen_candidate_class", "built_input_class",
                                                                    "unverified_offered", "unverified_chosen")}} if r.get("boundary") else {})
                  for r in rows]})
    print(json.dumps({"group": group, "total_seconds": total, "suspect_count": suspects, "tool_problems": problems}, ensure_ascii=False))
    if problems or any(r["status"] != "run" for r in rows):
        return 1
    return 3 if suspects else 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="python -m tools.verification_ai.run_v3_2")
    sub = parser.add_subparsers(dest="cmd", required=True)
    rn = sub.add_parser("run")
    rn.add_argument("--out", required=True)
    rn.add_argument("--engine-commit", required=True)
    args = parser.parse_args(argv)
    return run(Path(args.out), args.engine_commit, ["python", "-m", "tools.verification_ai.run_v3_2", *argv])


if __name__ == "__main__":
    raise SystemExit(main())
