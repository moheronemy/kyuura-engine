"""P6 の追従の固定確認の入口（docs/verification-ai-p6.md 5 章）。単一のプロセスで、上限つきのケースを 1 つずつ順に実行する。プロセスの起動・検索・終了はしない。

    python -m tools.verification_ai.run_p6 run --out <保存先> --engine-commit <sha>

各ケースは、fixture（``fixtures_p6``）の開始のスナップショットを保存し、それを復元した対戦（``snapshot.RestoredGame``）を ``ClientHub`` で包み、公開の API の
candidates・inputs・check・submit だけで操作する。にげるの入力は共通の行動生成（``actions.enumerate_inputs``。uniform-tuple と同じ列挙）が作った組から、ケースの選び手
（``fixtures_p6`` の関数。方策ではない）が選ぶ。送信は check が valid のあとだけ（``runner.submit_checked``）。判定は ``judge``（規則 4）。完全な再現用記録は作らない。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from kyuura_engine import diagnostics as D

from . import actions as B
from . import fixtures_p6 as F
from . import judge as J
from . import records as R
from .fixtures_v3_3 import restore
from .policies import UniformPolicy
from .run_v1 import now
from .run_v3_3 import CASE_SECONDS, MAX_REQUESTS, Case, CaseStop
from .runner import submit_checked

VERSION = "p6"
TOTAL_SECONDS = 300.0
FOLLOW_SEED = "kyuura-vai-p6:promote"  # 受理のあとの決定（バトル場に出す）の入力を作る均等の方策の種（uniform-stage）

CASES = [
    {"case": "R1", "fixture": "P6A", "purpose": "うらのバトル場のにげる（本当のカードはたね・にげる 0）: エネルギー 0 枚の入力を check してから送り、受理されてにげる",
     "select": F.zero_energy, "selector": "fixtures_p6.zero_energy", "expect": {"check_valid": True, "outcome": "accepted", "accepted_as": "p6_revealed_and_retreated"}},
    {"case": "R2", "fixture": "P6B", "purpose": "うらのバトル場のにげる（本当のカードはたね・にげる 3）: エネルギー 1 枚の入力を check してから送り、エネルギー不足でエンジンが拒否する",
     "select": F.one_energy, "selector": "fixtures_p6.one_energy", "expect": {"check_valid": True, "outcome": "rejected", "engine_code": "WRONG_RETREAT_COST"}},
    {"case": "R3", "fixture": "P6C", "purpose": "うらのバトル場のにげる（本当のカードは 1 進化）: エネルギー 0 枚の入力を送り、おもてにしてトラッシュして受理され、バトル場に出す決定に答える",
     "select": F.zero_energy, "selector": "fixtures_p6.zero_energy", "expect": {"check_valid": True, "outcome": "accepted", "accepted_as": "p6_revealed_not_basic_and_trashed",
                                                                                "follow": "promote_active"}},
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


def run_case(spec, snapshot: str) -> dict[str, Any]:
    game, status = restore(snapshot)
    if game is None:
        return {"case": spec["case"], "status": "not_run", "reason": f"restore:{status}"}
    case = Case(game)
    out: dict[str, Any] = {"case": spec["case"], "status": "run", "expect": spec["expect"], "selector": spec["selector"]}
    try:
        _retreat_step(case, spec, out)
        if out.get("outcome") == D.ACCEPTED and spec["expect"].get("follow"):
            _follow_step(case, spec, out)
    except CaseStop as error:
        out["stop"] = str(error)
    out["requests"] = case.requests
    out["trace"] = case.trace
    out["final"] = {"status": D.status_of(game.state), "checks": J.snapshot(game, case.hub)["checks"]}
    out["expectation_met"] = _met(spec["expect"], out)
    return out


def _retreat_step(case: Case, spec, out) -> None:
    endpoint = case.endpoints[0]
    cands = case.req(endpoint, "candidates")["response"]
    candidate = next((c for c in cands["candidates"] if c["kind"] == B.RETREAT_KIND), None)
    if candidate is None:
        out["reached"] = False
        return
    handle = {"game": cands["game"], "revision": cands["revision"], "candidate": candidate["id"]}
    inputs = case.req(endpoint, "inputs", **handle)["response"]
    out.update({"reached": True, "candidate": candidate, "withheld": "withheld" in inputs})
    if "withheld" in inputs:
        return
    stages = inputs["stages"]
    # 共通の行動生成（uniform-tuple の列挙）: boundary の範囲（unverified を許す）。費用・個数で絞らない
    tuples = B.enumerate_inputs(stages, B.FALLBACK_PROCESSABILITY, kind=candidate["kind"])
    index = spec["select"](tuples)
    choices, meaning = tuples[index]
    disclosure_before = case.face_down_view()
    before = J.snapshot(case.game, case.hub)
    log_before = len(case.game.state.log)
    checked = case.req(endpoint, "check", **handle, choices=choices)
    checked["_handle"], checked["_choices"] = handle, choices
    after_check = J.snapshot(case.game, case.hub)
    n_results = len(case.results)
    _count_submit(case)
    sent = submit_checked(endpoint, handle, choices, checked, operation_id=f"p6-{spec['case']}-1")
    after = J.snapshot(case.game, case.hub)
    changed = J.compare(before, after)
    submit = _submit_entry(case, sent, n_results)
    normal = J.judge_normal(candidate, meaning, submit, stages=stages)
    effects = J.judge_effects(sent.get("outcome"), changed)
    new_log = [e["kind"] for e in case.game.state.log[log_before:]] if sent.get("outcome") == D.ACCEPTED else []
    row = {"stages": stages, "generated": {"method": "enumerate_inputs(uniform-tuple の列挙)", "tuples": len(tuples), "choices_by_tuple": [c for c, _m in tuples],
                                           "picked_index": index, "picked_by": spec["selector"] + "（ケースの選び手。方策ではない）"},
           "choices": choices, "meaning": meaning, "check": {k: v for k, v in checked.items() if not k.startswith("_")}, "check_changed": J.compare(before, after_check),
           "submit": submit, "changed": changed, "normal_verdict": normal, "effects_verdict": effects}
    out["outcome"] = sent.get("outcome")
    if sent.get("outcome") == D.ACCEPTED:
        row["accepted_verdict"] = J.judge_p6_accepted(new_log)
        row["new_log_kinds"] = new_log
        stale = case.req(endpoint, "check", **handle, choices=choices)
        row["old_handle_check"] = (stale["response"].get("refusal") or {}).get("code")
    else:
        recovery = case.req(endpoint, "check", **handle, choices=choices)  # 同じ取っ手で、同じ正常な入力の check に戻れる（状態を変えない）
        row["recovery"] = recovery
        row["recovery_verdict"] = J.judge_recovery(recovery, J.compare(after, J.snapshot(case.game, case.hub)))
    row["disclosure"] = {"before": disclosure_before, "after": case.face_down_view()}
    out["retreat"] = row
    case.trace.append({"step": "retreat", **{k: v for k, v in row.items() if k != "stages"}})


def _follow_step(case: Case, spec, out) -> None:
    """受理のあとの決定（バトル場に出す）: 共通の行動生成（uniform-stage・均等の方策）で入力を作り、check のあとに送る。"""
    endpoint = case.endpoints[0]
    cands = case.req(endpoint, "candidates")["response"]
    kinds = [c["kind"] for c in cands["candidates"]]
    row: dict[str, Any] = {"situation": cands["situation"], "kinds": kinds}
    candidate = next((c for c in cands["candidates"] if c["kind"] == spec["expect"]["follow"]), None)
    if candidate is None:
        out["follow"] = row
        return
    handle = {"game": cands["game"], "revision": cands["revision"], "candidate": candidate["id"]}
    stages = case.req(endpoint, "inputs", **handle)["response"]["stages"] if candidate["input_stages"] else []
    policy = UniformPolicy(FOLLOW_SEED)
    choices, picks, meaning = B.build_choices(stages, policy, {"view": None, "candidate": candidate}, B.DEEP_PROCESSABILITY)
    checked = case.req(endpoint, "check", **handle, choices=choices)
    checked["_handle"], checked["_choices"] = handle, choices
    n_results = len(case.results)
    before = J.snapshot(case.game, case.hub)
    _count_submit(case)
    sent = submit_checked(endpoint, handle, choices, checked, operation_id=f"p6-{spec['case']}-2")
    submit = _submit_entry(case, sent, n_results)
    row.update({"candidate": candidate, "choices": choices, "picks": picks, "meaning": meaning, "policy": {"name": policy.name, "seed": FOLLOW_SEED},
                "check": {k: v for k, v in checked.items() if not k.startswith("_")}, "submit": submit,
                "normal_verdict": J.judge_normal(candidate, meaning, submit, stages=stages),
                "effects_verdict": J.judge_effects(sent.get("outcome"), J.compare(before, J.snapshot(case.game, case.hub))),
                "status_after": (sent.get("result") or {}).get("status")})
    out["follow"] = row
    case.trace.append({"step": "follow", **row})


def _met(expect, out) -> bool:
    row = out.get("retreat") or {}
    if not out.get("reached") or out.get("withheld") or out.get("stop"):
        return False
    if row.get("check", {}).get("response", {}).get("valid") != expect["check_valid"] or out.get("outcome") != expect["outcome"]:
        return False
    if "engine_code" in expect and (row["submit"].get("verifier") or {}).get("engine_code") != expect["engine_code"]:
        return False
    if "accepted_as" in expect and (row.get("accepted_verdict") or ("", []))[1][:1] != [expect["accepted_as"]]:
        return False
    if "follow" in expect and (out.get("follow") or {}).get("submit", {}).get("outcome") != D.ACCEPTED:
        return False
    return True


def run(out: Path, engine_commit: str, argv: list[str]) -> int:
    group = "p6-ai-follow"
    gdir = out / "verifier" / "runs" / group
    if gdir.exists():
        raise SystemExit(f"{gdir} はすでにある（既存の証跡を上書きしない）")
    R.write_json(gdir / "plan.json", {
        "written": now(), "argv": argv, "cases": [{k: v for k, v in c.items() if k != "select"} for c in CASES],
        "fixtures": {k: {"what": v["what"], "source": F.SOURCE} for k, v in F.FIXTURES.items()},
        "generation": "actions.enumerate_inputs（uniform-tuple の列挙。boundary の範囲 FALLBACK_PROCESSABILITY）。選ぶのはケースの選び手で、ランダムの方策ではない。"
                      "受理のあとの決定は actions.build_choices（uniform-stage・均等の方策）",
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
    # 情報境界: 本当のカードだけが違う 3 つの盤面で、同じ公開の入力契約から共通の行動生成が作った組が同じ
    generated = [(r.get("retreat") or {}).get("generated", {}).get("choices_by_tuple") for r in rows]
    meanings = [[m for m in (r.get("retreat") or {}).get("stages", [])] for r in rows]
    verdicts = []
    for r in rows:
        for part in ("retreat", "follow"):
            for key in ("normal_verdict", "effects_verdict", "accepted_verdict", "recovery_verdict"):
                v = (r.get(part) or {}).get(key)
                if v is not None:
                    verdicts.append([r["case"], part, key, v[0], v[1]])
    suspects = sum(1 for v in verdicts if v[3] == J.SUSPECT)
    undetermined = sum(1 for v in verdicts if v[3] == J.UNDETERMINED)
    unmet = [r["case"] for r in rows if not r.get("expectation_met")]
    aggregate = {"verdicts": verdicts, "suspect_count": suspects, "undetermined_count": undetermined, "expectation_unmet": unmet,
                 "generated_identical_across_cases": all(g == generated[0] for g in generated), "stages_identical_across_cases": all(m == meanings[0] for m in meanings),
                 "judge_rules_version": J.JUDGE_RULES_VERSION, "total_seconds": round(time.monotonic() - start, 3),
                 "requests": {r["case"]: r.get("requests") for r in rows}}
    R.write_json(gdir / "aggregate.json", aggregate)
    R.write_json(out / "public" / "runs" / group / "summary.json", {
        "tool": {"name": "tools.verification_ai", "version": VERSION}, "engine": {"git_commit": engine_commit, "version": ident["version"],
                                                                               "behavior_digest": ident["implementation"]["behavior_digest"]},
        "origin": "constructed_fixture（new_game から届いた証拠ではない）", "judge_rules_version": J.JUDGE_RULES_VERSION,
        "generation": "common action generator (enumerate_inputs); case selector picks the tuple (not a random policy)",
        "cases": [{"case": r["case"], "status": r["status"], "outcome": r.get("outcome"), "expectation_met": r.get("expectation_met"), "requests": r.get("requests"),
                   "verdicts": {f"{v[1]}.{v[2]}": v[3] for v in verdicts if v[0] == r["case"]},
                   "follow_outcome": ((r.get("follow") or {}).get("submit") or {}).get("outcome")} for r in rows],
        "generated_identical_across_cases": aggregate["generated_identical_across_cases"], "suspect_count": suspects, "undetermined_count": undetermined,
        "expectation_unmet": unmet})
    print(json.dumps({k: aggregate[k] for k in ("suspect_count", "undetermined_count", "expectation_unmet", "generated_identical_across_cases",
                                                "stages_identical_across_cases", "total_seconds", "requests")}, ensure_ascii=False))
    if any(r["status"] != "run" for r in rows):
        return 1
    return 3 if suspects or unmet or undetermined else 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="python -m tools.verification_ai.run_p6")
    sub = parser.add_subparsers(dest="cmd", required=True)
    rn = sub.add_parser("run")
    rn.add_argument("--out", required=True)
    rn.add_argument("--engine-commit", required=True)
    args = parser.parse_args(argv)
    return run(Path(args.out), args.engine_commit, ["python", "-m", "tools.verification_ai.run_p6", *argv])


if __name__ == "__main__":
    raise SystemExit(main())
