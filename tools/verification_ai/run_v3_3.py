"""V3-3 の実行の入口（構築盤面の代表例。docs/verification-ai-v3-3.md 6 章）。単一のプロセスで、上限つきのケースを 1 つずつ順に実行する。プロセスの起動・検索・終了はしない。

    python -m tools.verification_ai.run_v3_3 run --out <保存先> --engine-commit <sha>

各ケースは、fixture（``fixtures_v3_3``）の開始のスナップショットを保存し、それを復元した対戦（``snapshot.RestoredGame``）を ``ClientHub`` で包み、公開の API の
candidates・inputs・check・submit だけで操作する。選び方はケースの選び手（本人の入口の JSON だけを読む）。判定は ``judge``（検証者の側）。完全な再現用記録は作らない
（new_game からでない。開始点を偽らない）。事前に選んだ 1 ケース（C3）だけ、同じスナップショットからもう一度復元し、新しい取っ手で同じ操作を送って比べる。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from kyuura_engine import diagnostics as D
from kyuura_engine.client_api import ClientHub

from . import fixtures_v3_3 as F
from . import judge as J
from . import records as R
from .run_v1 import now
from .runner import request

VERSION = "v3-3"
MAX_REQUESTS = 20
CASE_SECONDS = 30.0
TOTAL_SECONDS = 600.0
RESTORE_CASE = "C3"
DU1 = "UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT"


class CaseStop(Exception):
    pass


def _face_down_power(cands, view):
    return next((c for c in cands if c["kind"] == "use_power" and (c.get("power") or {}).get("face_down")), None)


def _kind(kind):
    return lambda cands, view: next((c for c in cands if c["kind"] == kind), None)


def _own_active(stages, view):
    me = view["observation"]["players"][view["viewer"]]["active"]["pokemon_id"]
    return [next(o["id"] for o in stages[0]["options"] if o.get("pokemon") == me)]


def _first_attack(stages, view):
    return [stages[0]["options"][0]["id"]]  # 2 段目（宣言といっしょに選ぶもの）は 0 個


def _opponent_active(stages, view):
    them = view["observation"]["players"][1 - view["viewer"]]["active"]["pokemon_id"]
    return [next(o["id"] for o in stages[0]["options"] if o.get("value") == them)]


def _first_option(stages, view):
    return [stages[0]["options"][0]["id"]]


CASES = [
    {"case": "C1", "fixture": "F1", "kind": "boundary", "purpose": "unverified の入力（本人のうらのカードの特殊能力。入力なし）を check してから送り、受理される",
     "steps": [{"actor": 0, "select": _face_down_power, "build": lambda s, v: [], "expect": {"candidate_processability": "unverified", "check_valid": True,
                                                                                            "outcome": "accepted"}}],
     "disclosure": "face_down", "evidence": None},
    {"case": "C2", "fixture": "F2", "kind": "boundary", "purpose": "unverified の入力（本人のうらのカードの特殊能力。1 段。自分のバトル場のポケモン）を check してから送り、エンジンが拒否する",
     "steps": [{"actor": 0, "select": _face_down_power, "build": _own_active, "expect": {"candidate_processability": "unverified", "check_valid": True,
                                                                                        "outcome": "rejected"}, "recover": "same_input_check"}],
     "disclosure": "face_down", "evidence": None},
    {"case": "C3", "fixture": "F3", "kind": "boundary", "purpose": "may_stop_later のワザの宣言が受理され、受理のあとの決定に答えると、既知の停止（DU1）になる",
     "steps": [{"actor": 0, "select": _kind("use_attack"), "build": _first_attack, "expect": {"candidate_processability": "may_stop_later", "check_valid": True,
                                                                                             "outcome": "accepted", "status": "awaiting_decision"}},
               {"actor": 0, "select": _kind("answer_decision"), "build": _opponent_active, "expect": {"check_valid": True, "outcome": "accepted",
                                                                                                     "status": "halted"}}],
     "disclosure": None, "evidence": DU1},
    {"case": "C4", "fixture": "F4", "kind": "negative", "purpose": "表示だけの候補（check_face_up_deck。FU2）へ、形の合う入力を意図的に送る",
     "steps": [{"actor": 0, "select": _kind("check_face_up_deck"), "build": _first_option, "negative": True,
                "expect": {"code": "CANDIDATE_NOT_EXECUTABLE", "refetch_required": False}, "recover": "end_turn_check",
                "broken": "表示だけの候補（coverage.display_only_kinds）への送信。根拠: legal_actions.GUARANTEE_FACE_UP の acceptance「送れない」・_input_problem（形の合う入力は CANDIDATE_NOT_EXECUTABLE）"}],
     "disclosure": None, "evidence": None},
]


class Case:
    def __init__(self, game):
        self.results: list[Any] = []
        self.game = game
        self.hub = ClientHub(game, verifier=lambda actor, result: self.results.append(result))
        self.endpoints = {0: self.hub.player(0), 1: self.hub.player(1)}
        self.spectator = self.hub.spectator()
        self.requests = 0
        self.started = time.monotonic()
        self.trace: list[dict[str, Any]] = []

    def req(self, endpoint, kind, **fields):
        if self.requests >= MAX_REQUESTS:
            raise CaseStop("request_limit")
        if time.monotonic() - self.started >= CASE_SECONDS:
            raise CaseStop("time_limit")
        self.requests += 1
        return request(endpoint, kind, **fields)

    def face_down_view(self, owner=0) -> dict[str, Any]:
        """相手（1）と観戦者の観測で、持ち主の場のうらのポケモンの数と、カード id が見えているか（公開の範囲の確かめ）。"""
        out = {}
        for name, endpoint in (("opponent", self.endpoints[1 - owner]), ("spectator", self.spectator)):
            side = self.req(endpoint, "view")["observation"]["players"][owner]
            field = [side.get("active")] + list(side.get("bench") or [])
            out[name] = {"face_down": sum(1 for p in field if p and p.get("face_down")),
                         "face_down_with_card_id": sum(1 for p in field if p and p.get("face_down") and "card_id" in p)}
        return out


def _meaning(stages, choices):
    by_id = {o["id"]: (s["stage"], o) for s in stages for o in s.get("options", [])}
    return [{"stage": by_id[c][0], "option": {k: v for k, v in by_id[c][1].items() if k not in ("id", "after")}} for c in choices if c in by_id]


def run_case(spec, snapshot: str) -> dict[str, Any]:
    game, status = F.restore(snapshot)
    if game is None:
        return {"case": spec["case"], "status": "not_run", "reason": f"restore:{status}"}
    case = Case(game)
    steps_out = []
    stop = None
    try:
        for index, step in enumerate(spec["steps"], 1):
            steps_out.append(_run_step(case, spec, index, step))
            if not steps_out[-1].get("continue", True):
                break
    except CaseStop as error:
        stop = str(error)
    return {"case": spec["case"], "status": "run", "stop": stop, "steps": steps_out, "requests": case.requests, "trace": case.trace,
            "final": {"status": D.status_of(game.state), "checks": J.snapshot(game, case.hub)["checks"]}}


def _run_step(case: Case, spec, index, step) -> dict[str, Any]:
    endpoint = case.endpoints[step["actor"]]
    view = case.req(endpoint, "view")
    cands = case.req(endpoint, "candidates")["response"]
    candidate = step["select"](cands["candidates"], view)
    out: dict[str, Any] = {"step": index, "actor": step["actor"], "expect": step["expect"]}
    if candidate is None:
        out.update({"reached": False, "continue": False, "kinds": [c["kind"] for c in cands["candidates"]]})
        return out
    handle = {"game": cands["game"], "revision": cands["revision"], "candidate": candidate["id"]}
    stages = []
    if candidate["input_stages"]:
        inputs = case.req(endpoint, "inputs", **handle)["response"]
        if "withheld" in inputs:
            out.update({"reached": True, "candidate": candidate, "withheld": inputs["withheld"], "continue": False})
            return out
        stages = inputs["stages"]
    choices = step["build"](stages, view)
    disclosure_before = case.face_down_view() if spec["disclosure"] else None
    before = J.snapshot(case.game, case.hub)
    n_results = len(case.results)
    check = case.req(endpoint, "check", **handle, choices=choices)
    after_check = J.snapshot(case.game, case.hub)
    out.update({"reached": True, "candidate": candidate, "stages": stages, "choices": choices, "meaning": _meaning(stages, choices), "check": check,
                "check_changed": J.compare(before, after_check)})
    if step.get("negative"):
        responses = [("check", check)]
        if not check["response"]["valid"]:
            sent = case.req(endpoint, "submit", **handle, choices=choices, operation_id=f"v3-3-{spec['case']}-neg")
            responses.append(("submit", sent))
            out["submit"] = sent
        after = J.snapshot(case.game, case.hub)
        changed = J.compare(before, after)
        verdict, reasons = J.judge_negative(step["expect"]["code"], step["expect"]["refetch_required"], responses, changed)
        out.update({"changed": changed, "verdict": verdict, "reasons": reasons, "broken": step["broken"], "reached_engine": len(case.results) > n_results})
    else:
        if not check["response"]["valid"]:
            out.update({"verdict": J.SUSPECT, "reasons": ["check_invalid_for_api_input"], "continue": False})
            return out
        sent = case.req(endpoint, "submit", **handle, choices=choices, operation_id=f"v3-3-{spec['case']}-{index}")
        after = J.snapshot(case.game, case.hub)
        changed = J.compare(before, after)
        result = case.results[-1] if len(case.results) > n_results else None
        submit_entry = {"ok": sent.get("ok"), "outcome": sent.get("outcome"), "refusal": sent.get("refusal"), "result": sent.get("result")}
        if result is not None and result.diagnosis is not None:
            submit_entry["verifier"] = {"diagnostic_id": result.diagnosis.diagnostic_id, "category": result.diagnosis.category,
                                        "engine_code": result.verifier.engine_code}
        normal = J.judge_normal(candidate, out["meaning"], submit_entry, evidence=spec["evidence"])
        effects = J.judge_effects(sent.get("outcome"), changed)
        status = (sent.get("result") or {}).get("status")
        out.update({"submit": submit_entry, "changed": changed, "status_after": status, "normal_verdict": normal, "effects_verdict": effects})
        if status == D.HALTED:
            halt = (sent.get("result") or {}).get("halt")
            out["halt_verdict"] = J.judge_halt_after_accept(halt, evidence=spec["evidence"])
            out["continue"] = False
        if sent.get("outcome") != D.ACCEPTED:
            out["continue"] = False
    if spec["disclosure"]:
        out["disclosure"] = {"before": disclosure_before, "after": case.face_down_view()}
    if step.get("recover") == "same_input_check":
        out["recovery"] = case.req(endpoint, "check", **handle, choices=choices)
    elif step.get("recover") == "end_turn_check":
        end = next((c for c in cands["candidates"] if c["kind"] == "end_turn"), None)
        out["recovery"] = None if end is None else case.req(endpoint, "check", **{**handle, "candidate": end["id"]}, choices=[])
    if "recovery" in out and out["recovery"] is not None:
        out["recovery_verdict"] = J.judge_recovery(out["recovery"], J.compare(after, J.snapshot(case.game, case.hub)))
    out["expectation_met"] = _met(step["expect"], out)
    case.trace.append({k: v for k, v in out.items()})
    return out


def _met(expect, out) -> bool:
    if not out.get("reached"):
        return False
    if "candidate_processability" in expect and out["candidate"].get("processability") != expect["candidate_processability"]:
        return False
    if "check_valid" in expect and out["check"]["response"]["valid"] != expect["check_valid"]:
        return False
    if "outcome" in expect and (out.get("submit") or {}).get("outcome") != expect["outcome"]:
        return False
    if "status" in expect and out.get("status_after") != expect["status"]:
        return False
    if "code" in expect:
        codes = [((out["check"]["response"].get("refusal") or {}).get("code"))] + ([((out.get("submit") or {}).get("refusal") or {}).get("code")] if out.get("submit") else [])
        if any(c != expect["code"] for c in codes):
            return False
    return True


def _steps_semantic(result) -> list[dict[str, Any]]:
    return [{"kind": (s.get("candidate") or {}).get("kind"), "meaning": s.get("meaning"), "outcome": (s.get("submit") or {}).get("outcome"),
             "status_after": s.get("status_after")} for s in result.get("steps", [])]


def run(out: Path, engine_commit: str, argv: list[str]) -> int:
    group = "v3-3-constructed"
    gdir = out / "verifier" / "runs" / group
    if gdir.exists():
        raise SystemExit(f"{gdir} はすでにある（既存の証跡を上書きしない）")
    R.write_json(gdir / "plan.json", {
        "written": now(), "cases": [{k: v for k, v in c.items() if k not in ("steps",)} | {"steps": [{k: v for k, v in s.items() if k in ("actor", "expect", "recover",
                                                                                                                                      "negative", "broken")}
                                                                                                    for s in c["steps"]]} for c in CASES],
        "fixtures": {k: {"source": v["source"], "changes": v["changes"]} for k, v in F.FIXTURES.items()},
        "restore_check": {"case": RESTORE_CASE, "how": "同じ開始のスナップショットをもう一度復元し、新しい ClientHub（新しい取っ手）で同じ選び方の操作を送り、段ごとの結果と最後の確認値を比べる"},
        "limits": {"requests_per_case": MAX_REQUESTS, "seconds_per_case": CASE_SECONDS, "total_seconds": TOTAL_SECONDS}, "judge_rules_version": J.JUDGE_RULES_VERSION,
        "record_limits": "構築盤面から始めるので、完全な再現用記録（ReplayCollector）・replay_run（U4）・snapshot_replay（記録との接続）は対象の外。開始のスナップショットと操作の記録を残す",
        "note": "実行の前に書いた計画。結果を見てケースを足さない"})
    ident = R.identity(engine_commit)
    start = time.monotonic()
    rows = []
    for spec in CASES:
        if time.monotonic() - start >= TOTAL_SECONDS:
            rows.append({"case": spec["case"], "status": "not_run", "reason": "budget"})
            continue
        state, fixture = F.build(spec["fixture"])
        text, why = F.snapshot_text(state, spec["fixture"])
        d = gdir / spec["case"]
        R.write_json(d / "fixture.json", fixture | {"snapshot_saved": text is not None, "snapshot_problem": why})
        if text is None:
            rows.append({"case": spec["case"], "status": "not_run", "reason": f"snapshot:{why}"})
            continue
        (d / "start_snapshot.json").write_text(text, encoding="utf-8", newline="\n")
        started = now()
        result = run_case(spec, text)
        finished = now()
        trace = result.pop("trace", [])
        R.write_jsonl(d / "trace.jsonl", trace)
        row = {"case": spec["case"], "fixture": spec["fixture"], "kind": spec["kind"], "purpose": spec["purpose"], "started": started, "finished": finished,
               "origin": "constructed_fixture", "full_record": None, "replay_run": "not_applicable（new_game からの完全な記録がない）", **result}
        if spec["case"] == RESTORE_CASE and result["status"] == "run":
            again = run_case(spec, text)
            again.pop("trace", None)
            row["restore_check"] = {"same_steps": _steps_semantic(again) == _steps_semantic(result), "same_final_checks": again["final"] == result["final"],
                                    "first": _steps_semantic(result), "second": _steps_semantic(again), "second_final": again["final"],
                                    "handles": "復元のたびに新しい ClientHub と取っ手（前の取っ手を使わない）"}
        R.write_json(d / "case_result.json", row)
        rows.append(row)
        print(json.dumps({"case": spec["case"], "status": row["status"], "stop": row.get("stop"), "requests": row.get("requests"),
                          "steps": [{k: s.get(k) for k in ("reached", "expectation_met", "verdict", "normal_verdict", "effects_verdict", "halt_verdict", "recovery_verdict")}
                                    | {"outcome": (s.get("submit") or {}).get("outcome")} for s in row.get("steps", [])],
                          "restore_check": {k: (row.get("restore_check") or {}).get(k) for k in ("same_steps", "same_final_checks")} if row.get("restore_check") else None},
                         ensure_ascii=False, default=str))
    verdicts = []
    for row in rows:
        for s in row.get("steps", []):
            for key in ("verdict", "normal_verdict", "effects_verdict", "halt_verdict", "recovery_verdict"):
                if s.get(key) is not None:
                    verdicts.append((row["case"], key, s[key] if isinstance(s[key], str) else s[key][0]))
    suspects = sum(1 for _c, _k, v in verdicts if v == J.SUSPECT)
    undetermined = sum(1 for _c, _k, v in verdicts if v == J.UNDETERMINED)
    unmet = [f"{r['case']}:{s['step']}" for r in rows for s in r.get("steps", []) if not s.get("expectation_met")]
    aggregate = {"cases": [{k: v for k, v in r.items() if k not in ("steps",)} | {"steps": [{k: s.get(k) for k in ("step", "reached", "expectation_met", "verdict",
                                                                                                             "normal_verdict", "effects_verdict", "halt_verdict",
                                                                                                             "recovery_verdict", "changed", "status_after")}
                                                                                           | {"outcome": (s.get("submit") or {}).get("outcome"),
                                                                                              "disclosure": s.get("disclosure")} for s in r.get("steps", [])]}
                           for r in rows],
                 "verdicts": [list(v) for v in verdicts], "suspect_count": suspects, "undetermined_count": undetermined, "expectation_unmet": unmet,
                 "judge_rules_version": J.JUDGE_RULES_VERSION, "total_seconds": round(time.monotonic() - start, 3)}
    R.write_json(gdir / "aggregate.json", aggregate)
    R.write_json(out / "public" / "runs" / group / "summary.json", {
        "tool": {"name": "tools.verification_ai", "version": VERSION}, "engine": {"git_commit": engine_commit, "version": ident["version"],
                                                                               "behavior_digest": ident["implementation"]["behavior_digest"]},
        "origin": "constructed_fixture（new_game から届いた証拠ではない）", "judge_rules_version": J.JUDGE_RULES_VERSION,
        "cases": [{"case": r["case"], "fixture": r.get("fixture"), "kind": r.get("kind"), "status": r["status"],
                   "steps": [{"reached": s.get("reached"), "expectation_met": s.get("expectation_met"), "outcome": (s.get("submit") or {}).get("outcome"),
                              "status_after": s.get("status_after"),
                              "verdicts": {k: (s[k] if isinstance(s[k], str) else s[k][0]) for k in ("verdict", "normal_verdict", "effects_verdict", "halt_verdict",
                                                                                                       "recovery_verdict") if s.get(k) is not None}}
                             for s in r.get("steps", [])],
                   "restore_check": {k: (r.get("restore_check") or {}).get(k) for k in ("same_steps", "same_final_checks")} if r.get("restore_check") else None}
                  for r in rows],
        "suspect_count": suspects, "undetermined_count": undetermined, "expectation_unmet": unmet})
    print(json.dumps({"group": group, "suspect_count": suspects, "undetermined_count": undetermined, "expectation_unmet": unmet}, ensure_ascii=False))
    if any(r["status"] != "run" for r in rows):
        return 1
    return 3 if suspects or unmet else 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="python -m tools.verification_ai.run_v3_3")
    sub = parser.add_subparsers(dest="cmd", required=True)
    rn = sub.add_parser("run")
    rn.add_argument("--out", required=True)
    rn.add_argument("--engine-commit", required=True)
    args = parser.parse_args(argv)
    return run(Path(args.out), args.engine_commit, ["python", "-m", "tools.verification_ai.run_v3_3", *argv])


if __name__ == "__main__":
    raise SystemExit(main())
