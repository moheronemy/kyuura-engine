"""規約集合の同梱の記録（kyuura_engine/data/convention_records.json）を、台帳から作る・確かめる（v0.142。docs/ruleset-foundation-v0.142.md）。

    python scripts/build_convention_records.py --write   # 台帳から作り直して書く
    python scripts/build_convention_records.py --check   # 作り直した記録と書いた記録が同じか・対応の漏れ・不正な参照・競合がないか

記録は 2 つ:

- ``scene_index``: 停止の方針の台帳（docs/stop-policy-classification.json）の現在有効な場面（事例のあるコードは事例。ID は台帳の ID をそのまま使う）と、停止コードから場面への対応。
  場面の一覧は共通規約の設計案（scripts/build_play_policy_family_plan.py の ``scenes_from_ledger``）と同じ作り方
- ``current_behavior``: 実装上の仮定の一覧（docs/implementation-assumptions.json）の、今の実装にある項目（利用者の指定を除く）の ID・区分・状態。規約集合の今の挙動の記録
  （``CB-IMPLEMENTATION-ASSUMPTIONS``。承認の記録ではない）の内容

手で直さない。台帳が変わったら作り直す（記録の中身が変われば ``CB-IMPLEMENTATION-ASSUMPTIONS`` の照合値が変わり、規約集合の版を上げる判断が要る。テストが固定の照合値で見つける）。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from build_play_policy_family_plan import scenes_from_ledger

LEDGER = ROOT / "docs" / "stop-policy-classification.json"
ASSUMPTIONS = ROOT / "docs" / "implementation-assumptions.json"
PLAN = ROOT / "docs" / "play-policy-family-plan.json"
OUTPUT = ROOT / "kyuura_engine" / "data" / "convention_records.json"
CODE_KINDS = ("research_stop_code", "runtime_stop_code")
CURRENT_STATUSES = ("adopted_current", "documented_impl_unverified")


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(ledger: dict, assumptions: dict) -> dict:
    scenes = []
    codes: dict[str, list[str]] = {}
    for scene in scenes_from_ledger(ledger):
        code = scene["parent"] or scene["code"]
        scene_codes = [code] if scene["entry_kind"] in CODE_KINDS and code else []
        scenes.append({"id": scene["id"], "entry_kind": scene["entry_kind"], "codes": scene_codes})
        for c in scene_codes:
            codes.setdefault(c, []).append(scene["id"])
    items = sorted(({"id": it["id"], "category": it["category"], "status": it["status"]} for it in assumptions["items"]
                    if it["status"] in CURRENT_STATUSES and it["category"] != "user_specified"), key=lambda it: it["id"])
    return {
        "schema_version": 1,
        "generated_by": "scripts/build_convention_records.py",
        "sources": {"scene_index": "docs/stop-policy-classification.json entries（現在有効な項目。事例のあるコードは事例）",
                    "current_behavior": "docs/implementation-assumptions.json items（状態 adopted_current・documented_impl_unverified、区分 user_specified を除く）"},
        "scene_index": {"scenes": sorted(scenes, key=lambda s: s["id"]), "codes": {c: sorted(v) for c, v in sorted(codes.items())}},
        "current_behavior": {"items": items},
    }


def dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def check(written: dict, ledger: dict, assumptions: dict, plan: dict | None) -> list[str]:
    from kyuura_engine import conventions as C

    problems: list[str] = []
    fresh = build(ledger, assumptions)
    if fresh != written:
        problems.append("書いた記録が、台帳から作り直した記録と違う（--write で作り直す）")
    index = written["scene_index"]
    ids = [s["id"] for s in index["scenes"]]
    if len(ids) != len(set(ids)):
        problems.append("場面 ID が重複している")
    entries = {e["id"]: e for e in ledger["entries"]}
    for scene in index["scenes"]:
        if scene["id"] not in entries:
            problems.append(f"場面 {scene['id']} が台帳の項目にない（不正な参照）")
        for code in scene["codes"]:
            if code not in entries or entries[code]["entry_kind"] not in CODE_KINDS:
                problems.append(f"場面 {scene['id']} の停止コード {code} が台帳の停止コードにない（不正な参照）")
            if scene["id"] not in index["codes"].get(code, []):
                problems.append(f"停止コード {code} の対応に、場面 {scene['id']} がない（対応の漏れ）")
    for code, scene_ids in index["codes"].items():
        for sid in scene_ids:
            if sid not in ids:
                problems.append(f"停止コード {code} の対応の場面 {sid} が、場面の一覧にない（不正な参照）")
    for e in ledger["entries"]:
        if e["entry_kind"] in CODE_KINDS and e["status"] in ("active", "unverified"):
            if not index["codes"].get(e["id"]):
                problems.append(f"台帳の停止コード {e['id']} に、対応する場面がない（対応の漏れ）")
            cases = e.get("cases") or []
            if cases and sorted(cases) != index["codes"].get(e["id"], []):
                problems.append(f"停止コード {e['id']} の事例 {cases} と、対応の場面が違う")
            if not cases and index["codes"].get(e["id"]) != [e["id"]]:
                problems.append(f"事例のない停止コード {e['id']} の場面は、コードそのもの 1 つ")
    # 設計案の場面は、台帳の場面に、設計案の調査で見つけた台帳にまだない項目（entry_kind new_finding。PSP-NJ1-NINJA-GYM-ORACLE）を加えたもの
    if plan is not None and sorted(s["id"] for s in plan["scenes"] if s["entry_kind"] != "new_finding") != sorted(ids):
        problems.append("共通規約の設計案（docs/play-policy-family-plan.json）の場面と、同梱の場面の一覧が違う（どちらかを作り直す）")
    # 利用者の指定: 台帳の基礎集合の規約・エンジンの登録・規約集合の規約 ID が同じ（二重管理の食い違いを見つける）
    ledger_user = sorted({uid for conv in ledger["conventions"] if conv.get("baseline_category") == "user_specified" for uid in conv.get("user_ids", [])})
    registered = sorted(C.user_registrations())
    if ledger_user != sorted(C.USER_CONVENTION_IDS):
        problems.append(f"台帳の利用者の指定 {ledger_user} と、規約集合の利用者の指定の規約 ID が違う")
    if registered != sorted(C.USER_CONVENTION_IDS):
        problems.append(f"エンジンの登録の利用者の指定 {registered} と、規約集合の利用者の指定の規約 ID が違う")
    for conv in ledger["conventions"]:
        if conv.get("baseline_category") == "user_specified" and conv.get("mode_policy_status") != "user_agreed":
            problems.append(f"台帳の利用者の指定 {conv['id']} が user_agreed でない")
    # 規約集合の確かめ（登録した集合がどれも問題なく、照合値が固定の値と同じ）
    for key, spec in C.SETS.items():
        for problem in C.validate(spec, for_new_game=spec.usage != C.USAGE_LEGACY):
            problems.append(f"規約集合 {key[0]}@{key[1]}: {problem}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    ledger, assumptions = load_json(LEDGER), load_json(ASSUMPTIONS)
    if args.write:
        OUTPUT.write_text(dump(build(ledger, assumptions)), encoding="utf-8", newline="\n")
        print(f"wrote {OUTPUT.relative_to(ROOT)}")
        return 0
    written = load_json(OUTPUT)
    plan = load_json(PLAN) if PLAN.exists() else None
    problems = check(written, ledger, assumptions, plan)
    for problem in problems:
        print(problem)
    print(f"problems={len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
