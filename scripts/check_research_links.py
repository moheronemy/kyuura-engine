"""研究の対応表（kyuura_engine/data/research_links.json）を、kyuura の研究の基準のコミットの記録と照らす（v0.18e）。

kyuura（https://github.com/moheronemy/kyuura）の ``research_commit`` の記録を ``git show`` で読み（作業ツリー・履歴は変えない）、次を確かめる。

1. 論点（UQ-）: 対応表に書いた論点がすべてあり、どれも UNRESOLVED。kyuura の論点はどれも対応表のどこかにある。
2. エンジンの未解決の一覧（``engine_unresolved_index``）: 停止コードの集合が対応表と同じで、コードごとの論点と処理（issue・out_of_scope）が同じ。
3. 分類の違い（``classification_differences``）: kyuura の裁定（CR-）があり、分類（status）が対応表と同じで、エンジンの id を参照している。
4. 最新の説明（LD-）: 対応表の id があり、カード・種類・位置が合い、文面がエンジンの登録の ``play_text_ja`` と同じ。印刷の文面と同じ最新の説明を
   kyuura が照合の記録（CC-）に書いたもの（``recorded_in_card_checks``）は、照合した欄の文面（またはデータの誤りの資料の値）が ``play_text_ja`` と
   同じで、ページが登録の出典と同じ。照合の記録はあるがワザの文面を照合していないもの（``card_checks_without_text``）は、その欄が照合していない欄に
   ある。kyuura の記録のない登録・登録のない kyuura の記録の一覧が、実際と同じ（v0.19 の準備。2026-10-15）。
5. 照合の記録（CC-）: id があり、カードが合う。kyuura がエンジンの照合の記録を取り込んだ記録（``import_provenance``）は、エンジンの
   ``card_verification.json`` の同じカードの記録とページ・PDF のページ・原典の確認日が同じ。取り込み（``engine_import_id``）が kyuura にある。
6. カードデータ: 研究の基準のコミットの ``data/cards.json`` と、エンジンの写し（``KYUURA_COMMIT``）を、写しの項目で比べ、違いが対応表の
   ``card_data_differences`` に挙げたものだけ。

kyuura のデータの写しは作らない（id と、照らした結果だけを使う）。問題があれば終了コード 1。

    python3 scripts/check_research_links.py --kyuura ../kyuura
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kyuura_engine import effects as E  # noqa: E402

LINKS = ROOT / "kyuura_engine" / "data" / "research_links.json"


def load_extract_script():
    spec = importlib.util.spec_from_file_location("extract_kyuura_cards", ROOT / "scripts" / "extract_kyuura_cards.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_show(kyuura: Path, commit: str, path: str):
    result = subprocess.run(["git", "-C", str(kyuura), "show", f"{commit}:{path}"], check=True, capture_output=True)
    return json.loads(result.stdout.decode("utf-8"))


def registered_texts() -> dict[str, tuple[str, str | None]]:
    """登録した最新の説明（カード id/種類/位置 → (play_text_ja, 出典)）。"""
    registry = E.DEFAULT_EFFECTS
    found = {}
    for key in registry.attack_keys():
        entry = registry.attack_entry(key.card_id, key.attack_index)
        if entry.play_text_ja is not None:
            found[f"{key.card_id}/attack/{key.attack_index}"] = (entry.play_text_ja, entry.source)
    for key in registry.power_keys():
        entry = registry.power_entry(key.card_id, key.power_index)
        if getattr(entry, "play_text_ja", None) is not None:
            found[f"{key.card_id}/power/{key.power_index}"] = (entry.play_text_ja, entry.source)
    return found


def issues_in_links(links: dict) -> set[str]:
    found = {v["kyuura_issue"] for v in links["stop_codes"].values() if v["kyuura_issue"]}
    found |= {v["kyuura_issue"] for v in links["codeless_questions"].values()}
    for section in ("unresolved_without_code", "deferred_card_questions", "implementation_assumptions_with_issue"):
        found |= {v["kyuura_issue"] for v in links[section]}
    return found


def check(kyuura: Path) -> list[str]:
    links = json.loads(LINKS.read_text(encoding="utf-8"))
    commit = links["research_commit"]
    rulings = git_show(kyuura, commit, "data/sidecar/rulings.json")
    descriptions = git_show(kyuura, commit, "data/sidecar/latest_descriptions.json")["records"]
    checks = git_show(kyuura, commit, "data/sidecar/card_checks.json")["records"]
    problems: list[str] = []

    # 1. 論点
    issues = {x["id"]: x for x in rulings["issues"]}
    for issue in sorted(issues_in_links(links)):
        if issue not in issues:
            problems.append(f"論点 {issue} が kyuura {commit[:7]} にない")
        elif issues[issue]["status"] != "UNRESOLVED":
            problems.append(f"論点 {issue} の分類が {issues[issue]['status']}（UNRESOLVED でなくなった。止める処理を見直す）")
    for issue in sorted(set(issues) - issues_in_links(links)):
        problems.append(f"kyuura の論点 {issue} が対応表にない")

    # 2. エンジンの未解決の一覧
    index = {x["stop_code"]: x for x in rulings["engine_unresolved_index"] if x.get("stop_code")}
    if set(index) != set(links["stop_codes"]):
        problems.append(f"停止コードの集合が違う: kyuura だけ {sorted(set(index) - set(links['stop_codes']))}、"
                        f"対応表だけ {sorted(set(links['stop_codes']) - set(index))}")
    for code, entry in links["stop_codes"].items():
        theirs = index.get(code)
        if theirs is None:
            continue
        if (theirs.get("kyuura_issue"), theirs.get("disposition")) != (entry["kyuura_issue"], entry["kyuura_disposition"]):
            problems.append(f"{code}: kyuura は {theirs.get('kyuura_issue')}・{theirs.get('disposition')}、対応表は "
                            f"{entry['kyuura_issue']}・{entry['kyuura_disposition']}")

    # 3. 分類の違い
    by_id = {x["id"]: x for x in rulings["rulings"]}
    for diff in links["classification_differences"]:
        ruling = by_id.get(diff["kyuura_ruling"])
        if ruling is None:
            problems.append(f"裁定 {diff['kyuura_ruling']} が kyuura にない")
            continue
        if ruling["status"] != diff["kyuura_status"]:
            problems.append(f"裁定 {diff['kyuura_ruling']} の分類が {ruling['status']}（対応表は {diff['kyuura_status']}）")
        refs = {(r.get("engine_version"), r.get("ruling_id")) for r in ruling.get("engine_refs") or []}
        for engine in diff["engine"]:
            if (engine["version"], engine["ruling_id"]) not in refs:
                problems.append(f"裁定 {diff['kyuura_ruling']} がエンジンの {engine['version']} {engine['ruling_id']} を参照していない")
        if not ruling.get("reclassification"):
            problems.append(f"裁定 {diff['kyuura_ruling']} に kyuura の分類の変更の記録（reclassification）がない")
    recorded = {x["id"] for x in rulings["rulings"] if x.get("reclassification")}
    listed = {d["kyuura_ruling"] for d in links["classification_differences"]}
    if recorded != listed:
        problems.append(f"分類を変えた kyuura の裁定の集合が違う: kyuura だけ {sorted(recorded - listed)}、対応表だけ {sorted(listed - recorded)}")

    # 4. 最新の説明
    texts = registered_texts()
    ld = {x["id"]: x for x in descriptions}
    ld_by_target = {f"{x['card_id']}/{x['target']['kind']}/{x['target']['index']}": x["id"] for x in descriptions}
    section = links["latest_descriptions"]
    for target, ld_id in section["registered"].items():
        record = ld.get(ld_id)
        if record is None:
            problems.append(f"最新の説明 {ld_id} が kyuura にない")
            continue
        if f"{record['card_id']}/{record['target']['kind']}/{record['target']['index']}" != target:
            problems.append(f"最新の説明 {ld_id} の対象が {target} でない")
        if target not in texts:
            problems.append(f"{target} の登録に最新の説明がない（{ld_id}）")
            continue
        text, source = texts[target]
        if record["latest_description"]["text_ja"] != text:
            problems.append(f"{target}: 登録の最新の説明が kyuura の {ld_id} と違う")
        if source != f"P43 p.{record['latest_description']['page']}" and not (source or "").startswith(f"P43 p.{record['latest_description']['page']}"):
            problems.append(f"{target}: 出典 {source} が kyuura の {ld_id} のページ（p.{record['latest_description']['page']}）と違う")
    in_checks = set(section.get("recorded_in_card_checks", {})) | set(section.get("card_checks_without_text", {}))
    without = sorted(t for t in texts if t not in ld_by_target and t not in in_checks)
    if without != sorted(section["registered_without_kyuura_record"]):
        problems.append(f"kyuura の記録のない登録の一覧が違う: 実際 {without}")
    if sorted(t for t in texts if t in ld_by_target) != sorted(section["registered"]):
        problems.append("kyuura の最新の説明（LD-）のある登録の一覧が違う")
    not_registered = sorted(ld_id for target, ld_id in ld_by_target.items() if target not in texts)
    if not_registered != sorted(section["kyuura_records_not_registered"]):
        problems.append(f"登録のない kyuura の最新の説明の一覧が違う: 実際 {not_registered}")

    # 4b. kyuura の照合の記録に書かれた最新の説明（印刷の文面と同じもの）・文面を照合していない記録
    for target, cc_id in section.get("recorded_in_card_checks", {}).items():
        card, kind, index = target.split("/")
        record = next((x for x in checks if x["id"] == cc_id), None)
        if record is None or record["card_id"] != card:
            problems.append(f"{target}: 照合の記録 {cc_id} が kyuura にない、またはカードが違う")
            continue
        if target not in texts:
            problems.append(f"{target} の登録に最新の説明がない（{cc_id}）")
            continue
        path = f"pokemon.{'attacks' if kind == 'attack' else 'powers'}[{index}].text.ja"
        text, source = texts[target]
        checked = record["checked_fields"].get(path)
        corrected = [e.get("source_value") for e in (record.get("data_error") or []) if e.get("field") == path]
        if checked != text and text not in corrected:
            problems.append(f"{target}: 照合の記録 {cc_id} の文面（照合した欄・データの誤りの資料の値）が登録の最新の説明と違う")
        if source != f"P43 p.{record['page']}" and not (source or "").startswith(f"P43 p.{record['page']}"):
            problems.append(f"{target}: 出典 {source} が kyuura の {cc_id} のページ（p.{record['page']}）と違う")
        if target in ld_by_target:
            problems.append(f"{target}: kyuura に最新の説明の記録 {ld_by_target[target]} もある（registered に移す）")
    for target, cc_id in section.get("card_checks_without_text", {}).items():
        card, kind, index = target.split("/")
        record = next((x for x in checks if x["id"] == cc_id), None)
        path = f"pokemon.{'attacks' if kind == 'attack' else 'powers'}[{index}].text.ja"
        if record is None or record["card_id"] != card:
            problems.append(f"{target}: 照合の記録 {cc_id} が kyuura にない、またはカードが違う")
        elif path in record["checked_fields"] or not any(f.startswith(path) for f in record.get("fields_not_checked", [])):
            problems.append(f"{target}: {cc_id} で文面を照合していないとした記録と合わない（照合した欄にある、または照合していない欄にない）")
    accounted = set(section["registered"]) | set(section.get("recorded_in_card_checks", {})) | set(section.get("card_checks_without_text", {}))
    if set(section["registered_without_kyuura_record"]) & accounted:
        problems.append("kyuura の記録のない登録の一覧に、記録のある登録が入っている")

    # 5. 照合の記録
    cc = {x["id"]: x for x in checks}
    for group in ("engine_verified", "not_in_engine"):
        for card, ids in links["card_checks"][group].items():
            for cc_id in ids:
                if cc_id not in cc or cc[cc_id]["card_id"] != card:
                    problems.append(f"照合の記録 {cc_id} が kyuura にない、またはカードが {card} でない")
    listed_cc = {cc_id for group in ("engine_verified", "not_in_engine") for ids in links["card_checks"][group].values() for cc_id in ids}
    if listed_cc != set(cc):
        problems.append(f"照合の記録の集合が違う: kyuura だけ {sorted(set(cc) - listed_cc)}")
    # kyuura がエンジンの照合の記録を取り込んだ記録（import_provenance）は、エンジンの記録とページ・原典の確認日が同じ
    verification = json.loads((ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8"))["cards"]
    for record in checks + descriptions:
        if not record.get("import_provenance"):
            continue
        for v in record["verification"]:
            if v.get("by") != "kyuura-engine" or v.get("document") != "kyuura_engine/data/card_verification.json":
                continue
            ours = verification.get(v.get("record", "").removeprefix("cards."))
            page = record.get("page") or record.get("latest_description", {}).get("page")
            pdf = record.get("pdf_page") or record.get("latest_description", {}).get("pdf_page")
            if ours is None:
                problems.append(f"{record['id']}: エンジンの照合の記録 {v.get('record')} がない")
            elif (str(ours["page"]), ours["pdf_page"]) != (str(page), pdf):
                problems.append(f"{record['id']}: ページが、エンジンの照合の記録 {v['record']}（p.{ours['page']}）と違う")
            elif ours.get("checked_on") and ours["checked_on"] != v.get("source_checked_on"):
                problems.append(f"{record['id']}: 原典の確認日が、エンジンの照合の記録 {v['record']}（{ours['checked_on']}）と違う")
    if links["engine_import_id"] not in {x["id"] for x in rulings["engine_imports"]}:
        problems.append(f"エンジンの取り込み {links['engine_import_id']} が kyuura にない")

    # 6. カードデータ
    extract_script = load_extract_script()
    extract = json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text(encoding="utf-8"))
    if extract["source"]["commit"] != links["card_data_commit"]:
        problems.append(f"写しのコミット {extract['source']['commit']} が対応表の card_data_commit と違う")
    cards = git_show(kyuura, commit, extract_script.KYUURA_PATH)
    research_cards = {c["id"]: c for c in (cards["cards"] if isinstance(cards, dict) else cards)}
    allowed = {(d["card_id"], d["field"]) for d in links["card_data_differences"]}
    seen = set()
    for card in extract["cards"]:
        theirs = research_cards.get(card["id"])
        if theirs is None:
            problems.append(f"写しのカード {card['id']} が研究の基準のコミットにない")
            continue
        for field in extract_script.FIELDS:
            if card.get(field) != theirs.get(field):
                seen.add((card["id"], field))
                if (card["id"], field) not in allowed:
                    problems.append(f"{card['id']} の {field} が研究の基準のコミットで違う（対応表の card_data_differences にない）")
    for missing in sorted(allowed - seen):
        problems.append(f"card_data_differences の {missing} は、もう違わない（対応表から外す）")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kyuura", type=Path, default=ROOT.parent / "kyuura", help="kyuura の clone（既定: ../kyuura）")
    args = parser.parse_args(argv)
    problems = check(args.kyuura)
    links = json.loads(LINKS.read_text(encoding="utf-8"))
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        print(f"研究の対応表と kyuura {links['research_commit']} の記録に {len(problems)} 件の違いがある", file=sys.stderr)
        return 1
    print(f"研究の対応表は kyuura {links['research_commit']} の記録と一致しています")
    return 0


if __name__ == "__main__":
    sys.exit(main())
