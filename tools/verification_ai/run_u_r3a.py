"""U-R3a の追従の固定確認の入口（docs/verification-ai-u-r3a.md 5 章）。単一のプロセスで、上限つきのケースを 1 つずつ順に実行する。プロセスの起動・検索・終了はしない。

    python -m tools.verification_ai.run_u_r3a run --out <保存先> --engine-commit <sha>

各ケースは、fixture（``fixtures_u_r3a``）の開始のスナップショットを保存し、それを復元した対戦（``snapshot.RestoredGame``）を ``ClientHub`` で包み、公開の API の
candidates・inputs・check・submit・view だけで操作する。うらのカードの特殊能力の入力は、共通の行動生成（``actions.enumerate_inputs``。uniform-tuple と同じ列挙）が作った
組から、ケースの選び手（``fixtures_u_r3a`` の関数。方策ではない）が選ぶ。uniform-stage（``actions.build_choices``・均等の方策）で作った組がその列挙に入ることも記録する
（送らない）。送信は check が valid のあとだけ（``runner.submit_checked``）。判定は ``judge``（規則 5）。完全な再現用記録は作らない（開始のスナップショットと操作の記録）。
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path
from typing import Any

from kyuura_engine import diagnostics as D
from kyuura_engine.observation import visible_log

from . import actions as B
from . import fixtures_u_r3a as F
from . import judge as J
from . import records as R
from .fixtures_v3_3 import restore
from .policies import UniformPolicy
from .run_v1 import now
from .run_v3_3 import CASE_SECONDS, MAX_REQUESTS, Case, CaseStop
from .runner import submit_checked

VERSION = "u-r3a"
TOTAL_SECONDS = 300.0
STAGE_SEED = "kyuura-vai-u-r3a:stage"  # uniform-stage で組を作れることの記録に使う均等の方策の種（送らない）

CASES = [
    {"case": "U1", "fixture": "UR3A-RC", "purpose": "うらのロケット団のヒトカゲ（たね・2 段）: コラッタの炎エネルギーを選んで check してから送り、おもてにして特殊能力が使われて受理",
     "select": F.rattata_fire, "selector": "fixtures_u_r3a.rattata_fire",
     "expect": {"check_valid": True, "outcome": "accepted", "accepted_as": "face_down_power_revealed_and_used", "revealed": F.ROCKET_CHARMANDER}},
    {"case": "U2", "fixture": "UR3A-RC", "purpose": "うらのロケット団のヒトカゲ: エビワラーの闘エネルギーを選んで check してから送り、おもてにしたあと WRONG_ENERGY_TYPE で拒否",
     "select": F.hitmonchan_fighting, "selector": "fixtures_u_r3a.hitmonchan_fighting",
     "expect": {"check_valid": True, "outcome": "rejected", "engine_code": "WRONG_ENERGY_TYPE", "normal": J.NORMAL_REJECTION}},
    {"case": "U3", "fixture": "UR3A-VN", "purpose": "うらのフシギバナ（2 進化・3 段）: エビワラー → 闘エネルギー → エビワラーを check してから送り、おもてにしてトラッシュして受理",
     "select": F.hitmonchan_fighting_hitmonchan, "selector": "fixtures_u_r3a.hitmonchan_fighting_hitmonchan",
     "expect": {"check_valid": True, "outcome": "accepted", "accepted_as": "face_down_power_revealed_not_basic_and_trashed", "revealed": F.VENUSAUR}},
]


def _count_submit(case: Case) -> None:
    """submit は check の確かめのある送信（runner.submit_checked）で送るので、Case.req を通らない。同じ上限（要求の数・ケースの時間）を当てる。"""
    if case.requests >= MAX_REQUESTS:
        raise CaseStop("request_limit")
    if time.monotonic() - case.started >= CASE_SECONDS:
        raise CaseStop("time_limit")
    case.requests += 1


def _submit_entry(case: Case, sent, n_results) -> dict[str, Any]:
    result = case.results[-1] if len(case.results) > n_results else None
    entry = {"ok": sent.get("ok"), "outcome": sent.get("outcome"), "refusal": sent.get("refusal"), "result": sent.get("result")}
    if result is not None and result.diagnosis is not None:
        entry["verifier"] = {"diagnostic_id": result.diagnosis.diagnostic_id, "category": result.diagnosis.category, "engine_code": result.verifier.engine_code}
    return entry


def _public(case: Case) -> dict[str, Any]:
    """相手（1）と観戦者の観測（公開の API の view）と、検証者の側で読む公開のログ（visible_log）。"""
    return {"opponent_view": case.req(case.endpoints[1], "view")["observation"], "spectator_view": case.req(case.spectator, "view")["observation"],
            "opponent_log": visible_log(case.game.state, 1), "spectator_log": visible_log(case.game.state, None)}


def _owner_field_ids(observation) -> list[dict[str, Any]]:
    side = observation["players"][0]
    field = [q for q in [side.get("active"), *(side.get("bench") or [])] if q]
    return [{"pokemon_id": q["pokemon_id"], "face_down": bool(q.get("face_down")), "card_id": q.get("card_id")} for q in field]


def run_case(spec, snapshot: str) -> dict[str, Any]:
    game, status = restore(snapshot)
    if game is None:
        return {"case": spec["case"], "status": "not_run", "reason": f"restore:{status}"}
    case = Case(game)
    out: dict[str, Any] = {"case": spec["case"], "status": "run", "expect": {k: v for k, v in spec["expect"].items()}, "selector": spec["selector"]}
    try:
        _power_step(case, spec, out)
    except CaseStop as error:
        out["stop"] = str(error)
    out["requests"] = case.requests
    out["trace"] = case.trace if hasattr(case, "trace") else []
    out["final"] = {"status": D.status_of(game.state), "checks": J.snapshot(game, case.hub)["checks"]}
    out["expectation_met"] = _met(spec["expect"], out)
    return out


def _power_step(case: Case, spec, out) -> None:
    endpoint = case.endpoints[0]
    cands = case.req(endpoint, "candidates")["response"]
    candidate = next((c for c in cands["candidates"] if J.is_face_down_power(c)), None)
    if candidate is None:
        out["reached"] = False
        return
    handle = {"game": cands["game"], "revision": cands["revision"], "candidate": candidate["id"]}
    inputs = case.req(endpoint, "inputs", **handle)["response"]
    out.update({"reached": True, "candidate": candidate, "withheld": "withheld" in inputs})
    if "withheld" in inputs:
        return  # 入力を返さない候補は送らない
    stages = inputs["stages"]
    stages_before = copy.deepcopy(stages)
    tuples = B.enumerate_inputs(stages, B.FALLBACK_PROCESSABILITY, kind=candidate["kind"])  # 共通の行動生成（uniform-tuple の列挙）。boundary の範囲
    stage_choices, _picks, _m = B.build_choices(stages, UniformPolicy(STAGE_SEED), {"view": None, "candidate": candidate}, B.FALLBACK_PROCESSABILITY)
    index = spec["select"](tuples)
    choices, meaning = tuples[index]
    public_before = _public(case)
    before = J.snapshot(case.game, case.hub)
    log_before = {"opponent": len(public_before["opponent_log"]), "spectator": len(public_before["spectator_log"])}
    checked = case.req(endpoint, "check", **handle, choices=choices)
    checked["_handle"], checked["_choices"] = handle, choices
    after_check = J.snapshot(case.game, case.hub)
    n_results = len(case.results)
    _count_submit(case)
    sent = submit_checked(endpoint, handle, choices, checked, operation_id=f"u-r3a-{spec['case']}-1")
    after = J.snapshot(case.game, case.hub)
    changed = J.compare(before, after)
    submit = _submit_entry(case, sent, n_results)
    delivered = {str(a): copy.deepcopy(list(case.hub._outbox[a])[before["outbox"][str(a)]:]) for a in (1, "spectator")}  # 取り出さずに読む（配る順を変えない）
    row: dict[str, Any] = {
        "stages": stages, "stages_unchanged_by_generator": stages == stages_before,
        "generated": {"method": "enumerate_inputs（uniform-tuple の列挙）", "tuples": len(tuples), "choices_by_tuple": [c for c, _m in tuples],
                      "uniform_stage_sample": stage_choices, "uniform_stage_sample_in_tuples": stage_choices in [c for c, _m in tuples],
                      "picked_index": index, "picked_by": spec["selector"] + "（ケースの選び手。方策ではない）"},
        "choices": choices, "meaning": meaning, "check": {k: v for k, v in checked.items() if not k.startswith("_")}, "check_changed": J.compare(before, after_check),
        "submit": submit, "changed": changed,
        "normal_verdict": J.judge_normal(candidate, meaning, submit, stages=stages), "effects_verdict": J.judge_effects(sent.get("outcome"), changed),
        "delivered_updates": delivered,
    }
    out["outcome"] = sent.get("outcome")
    public_after = _public(case)
    new_public = {"opponent": public_after["opponent_log"][log_before["opponent"]:], "spectator": public_after["spectator_log"][log_before["spectator"]:]}
    if sent.get("outcome") == D.ACCEPTED:
        row["accepted_verdict"] = J.judge_face_down_power_accepted(candidate, new_public["spectator"])
        row["accepted_verdict_opponent_log"] = J.judge_face_down_power_accepted(candidate, new_public["opponent"])
        stale = case.req(endpoint, "check", **handle, choices=choices)
        row["old_handle_check"] = (stale["response"].get("refusal") or {}).get("code")
    else:
        recovery = case.req(endpoint, "check", **handle, choices=choices)  # 同じ取っ手で、同じ入力の check に戻れる（状態を変えない）
        row["recovery"] = recovery
        row["recovery_verdict"] = J.judge_recovery(recovery, J.compare(after, J.snapshot(case.game, case.hub)))
        row["public_unchanged"] = {"opponent_view": public_before["opponent_view"] == public_after["opponent_view"],
                                   "spectator_view": public_before["spectator_view"] == public_after["spectator_view"],
                                   "opponent_log": public_before["opponent_log"] == public_after["opponent_log"],
                                   "spectator_log": public_before["spectator_log"] == public_after["spectator_log"]}
    real = F.FIXTURES[spec["fixture"]]["real"]
    row["public"] = {
        "before": {"opponent_field": _owner_field_ids(public_before["opponent_view"]), "spectator_field": _owner_field_ids(public_before["spectator_view"])},
        "after": {"opponent_field": _owner_field_ids(public_after["opponent_view"]), "spectator_field": _owner_field_ids(public_after["spectator_view"]),
                  "opponent_discard": [c["card_id"] for c in public_after["opponent_view"]["players"][0]["discard"]],
                  "spectator_discard": [c["card_id"] for c in public_after["spectator_view"]["players"][0]["discard"]]},
        "new_public_log": new_public,
        "revealed_card_ids": {k: [e.get("card_id") for e in v if e.get("kind") == J.FACE_DOWN_POWER_REVEALED] for k, v in new_public.items()},
        "real_in_public_before": real in json.dumps([public_before["opponent_view"], public_before["spectator_view"], public_before["opponent_log"],
                                                      public_before["spectator_log"]], ensure_ascii=False, default=str),
        "real_in_public_after": real in json.dumps([public_after["opponent_view"], public_after["spectator_view"], public_after["opponent_log"],
                                                     public_after["spectator_log"]], ensure_ascii=False, default=str),
    }
    out["power"] = row
    case.trace.append({"step": "use_power", **{k: v for k, v in row.items() if k != "stages"}})


def _met(expect, out) -> bool:
    row = out.get("power") or {}
    if not out.get("reached") or out.get("withheld") or out.get("stop"):
        return False
    if row.get("check", {}).get("response", {}).get("valid") != expect["check_valid"] or out.get("outcome") != expect["outcome"]:
        return False
    if "engine_code" in expect and (row["submit"].get("verifier") or {}).get("engine_code") != expect["engine_code"]:
        return False
    if "normal" in expect and row["normal_verdict"][0] != expect["normal"]:
        return False
    if "accepted_as" in expect and (row.get("accepted_verdict") or ("", []))[1][:1] != [expect["accepted_as"]]:
        return False
    if "revealed" in expect and row["public"]["revealed_card_ids"] != {"opponent": [expect["revealed"]], "spectator": [expect["revealed"]]}:
        return False
    if out.get("outcome") == D.REJECTED and (row["public"]["real_in_public_after"] or not all(row["public_unchanged"].values())):
        return False
    return True


def run(out: Path, engine_commit: str, argv: list[str]) -> int:
    group = "u-r3a-ai-follow"
    gdir = out / "verifier" / "runs" / group
    if gdir.exists():
        raise SystemExit(f"{gdir} はすでにある（既存の証跡を上書きしない）")
    R.write_json(gdir / "plan.json", {
        "written": now(), "argv": argv, "cases": [{k: v for k, v in c.items() if k != "select"} for c in CASES],
        "fixtures": {k: {"what": v["what"], "source": F.SOURCE} for k, v in F.FIXTURES.items()},
        "generation": "actions.enumerate_inputs（uniform-tuple の列挙。boundary の範囲 FALLBACK_PROCESSABILITY）。選ぶのはケースの選び手で、ランダムの方策ではない。"
                      "actions.build_choices（uniform-stage・均等の方策）で作った組が列挙に入ることも記録する（送らない）",
        "limits": {"requests_per_case": MAX_REQUESTS, "seconds_per_case": CASE_SECONDS, "total_seconds": TOTAL_SECONDS}, "judge_rules_version": J.JUDGE_RULES_VERSION,
        "record_limits": "構築盤面から始めるので、完全な再現用記録・replay_run は対象の外。開始のスナップショットと操作の記録を残す",
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
        trace = result.pop("trace", [])
        R.write_jsonl(d / "trace.jsonl", trace)
        row = {"case": spec["case"], "fixture": spec["fixture"], "purpose": spec["purpose"], "started": started, "finished": now(), "origin": "constructed_fixture",
               "full_record": None, "replay_run": "not_applicable（new_game からの完全な記録がない）", **result}
        R.write_json(d / "case_result.json", row)
        rows.append(row)
    verdicts = []
    for r in rows:
        for key in ("normal_verdict", "effects_verdict", "accepted_verdict", "accepted_verdict_opponent_log", "recovery_verdict"):
            v = (r.get("power") or {}).get(key)
            if v is not None:
                verdicts.append([r["case"], key, v[0], v[1]])
    suspects = sum(1 for v in verdicts if v[2] == J.SUSPECT)
    undetermined = sum(1 for v in verdicts if v[2] == J.UNDETERMINED)
    unmet = [r["case"] for r in rows if not r.get("expectation_met")]
    aggregate = {"verdicts": verdicts, "suspect_count": suspects, "undetermined_count": undetermined, "expectation_unmet": unmet,
                 "revealed_card_ids": {r["case"]: (r.get("power") or {}).get("public", {}).get("revealed_card_ids") for r in rows},
                 "judge_rules_version": J.JUDGE_RULES_VERSION, "total_seconds": round(time.monotonic() - start, 3),
                 "requests": {r["case"]: r.get("requests") for r in rows}}
    R.write_json(gdir / "aggregate.json", aggregate)
    R.write_json(out / "public" / "runs" / group / "summary.json", {
        "tool": {"name": "tools.verification_ai", "version": VERSION}, "engine": {"git_commit": engine_commit, "version": ident["version"],
                                                                               "behavior_digest": ident["implementation"]["behavior_digest"]},
        "origin": "constructed_fixture（new_game から届いた証拠ではない）", "judge_rules_version": J.JUDGE_RULES_VERSION,
        "generation": "common action generator (enumerate_inputs); case selector picks the tuple (not a random policy)",
        "cases": [{"case": r["case"], "status": r["status"], "outcome": r.get("outcome"), "expectation_met": r.get("expectation_met"), "requests": r.get("requests"),
                   "verdicts": {v[1]: v[2] for v in verdicts if v[0] == r["case"]}} for r in rows],
        "suspect_count": suspects, "undetermined_count": undetermined, "expectation_unmet": unmet})
    print(json.dumps({k: aggregate[k] for k in ("suspect_count", "undetermined_count", "expectation_unmet", "revealed_card_ids", "total_seconds", "requests")},
                     ensure_ascii=False))
    if any(r["status"] != "run" for r in rows):
        return 1
    return 3 if suspects or unmet or undetermined else 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="python -m tools.verification_ai.run_u_r3a")
    sub = parser.add_subparsers(dest="cmd", required=True)
    rn = sub.add_parser("run")
    rn.add_argument("--out", required=True)
    rn.add_argument("--engine-commit", required=True)
    args = parser.parse_args(argv)
    return run(Path(args.out), args.engine_commit, ["python", "-m", "tools.verification_ai.run_u_r3a", *argv])


if __name__ == "__main__":
    raise SystemExit(main())
