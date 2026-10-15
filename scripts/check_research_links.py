"""研究の対応表（kyuura_engine/data/research_links.json）を、kyuura の研究の基準のコミットの記録と照らす（v0.18e）。

kyuura（https://github.com/moheronemy/kyuura）の ``research_commit`` の記録を ``git show`` で読み（作業ツリー・履歴は変えない）、次を確かめる。

1. 論点（UQ-）: 対応表に書いた論点がすべてあり、どれも UNRESOLVED。kyuura の論点はどれも対応表のどこかにある。
2. エンジンの未解決の一覧（``engine_unresolved_index``）: 停止コードの集合が対応表と同じで、コードごとの論点と処理（issue・out_of_scope）が同じ。
   kyuura にまだ記録がないとした停止コード（``not_in_kyuura``。v0.21）は比べる集合から除き、kyuura に記録ができていたら知らせる。
3. 分類の違い（``classification_differences``）: kyuura の裁定（CR-）があり、分類（status）が対応表と同じで、エンジンの id を参照している。
4. 最新の説明（LD-）: 対応表の id があり、カード・種類・位置が合い、文面がエンジンの登録の ``play_text_ja`` と同じ。印刷の文面と同じ最新の説明を
   kyuura が照合の記録（CC-）に書いたもの（``recorded_in_card_checks``）は、照合した欄の文面（またはデータの誤りの資料の値）が ``play_text_ja`` と
   同じで、ページが登録の出典と同じ。照合の記録はあるがワザの文面を照合していないもの（``card_checks_without_text``）は、その欄が照合していない欄に
   ある。kyuura の記録のない登録・登録のない kyuura の記録の一覧が、実際と同じ（v0.19 の準備。2026-10-15）。
5. 照合の記録（CC-）: id があり、カードが合う。kyuura がエンジンの照合の記録を取り込んだ記録（``import_provenance``）は、エンジンの
   ``card_verification.json`` の同じカードの記録とページ・PDF のページ・原典の確認日が同じ。取り込み（``engine_import_id``）が kyuura にある。
6. カードデータ: 研究の基準のコミットの ``data/cards.json`` と、エンジンの写し（``KYUURA_COMMIT``）を、写しの項目で比べ、違いが対応表の
   ``card_data_differences`` に挙げたものだけ。
7. kyuura データの採用（2026-10-15 からの方針。``kyuura_engine/data/card_sources.json``。docs/card-data-policy.md）: 処理に使う文面を
   kyuura の印刷の文面にした登録（``adopted_printed_text``）は、文面が研究の基準のコミットの ``data/cards.json`` と同じで、その対象の
   最新の説明（LD-）・データの誤りの記録（CC- の ``data_error``）がない。採用の記録の ``kyuura_records`` は、研究の基準のコミットで
   そのカードを指す kyuura の記録（LD-・CC-・CR-・UQ-・エラッタ）とちょうど同じ（既存の記録を探して確かめたこと）。根拠にした
   エラッタはそのカードを指す。CC- のデータの誤りの欄は、採用の記録の論点（``issues``）に挙げる。

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


def registered_texts(registry=None) -> dict[str, tuple[str, str | None]]:
    """登録した最新の説明（カード id/種類/位置 → (play_text_ja, 出典)）。"""
    registry = E.DEFAULT_EFFECTS if registry is None else registry
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


def check(kyuura: Path, *, links: dict | None = None, sources: dict | None = None, registry=None) -> list[str]:
    """問題の一覧（なければ空）。``links``・``sources``（card_sources.json の ``cards``）・``registry`` を省くと同梱のデータと
    ``DEFAULT_EFFECTS`` を使う（テストは差し替えて、採用の記録の確かめ方を調べる）。"""
    links = json.loads(LINKS.read_text(encoding="utf-8")) if links is None else links
    commit = links["research_commit"]
    rulings = git_show(kyuura, commit, "data/sidecar/rulings.json")
    descriptions = git_show(kyuura, commit, "data/sidecar/latest_descriptions.json")["records"]
    checks = git_show(kyuura, commit, "data/sidecar/card_checks.json")["records"]
    extract_script = load_extract_script()
    cards = git_show(kyuura, commit, extract_script.KYUURA_PATH)
    research_cards = {c["id"]: c for c in (cards["cards"] if isinstance(cards, dict) else cards)}
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
    # kyuura にまだ記録がない停止コード（not_in_kyuura。kyuura への報告事項。v0.21）は、kyuura の一覧と比べる集合から除く。kyuura に記録が
    # できていたら、対応表を直すよう知らせる（v0.19 の照合の記録と同じ）
    pending = {code for code, v in links["stop_codes"].items() if v["kyuura_disposition"] == "not_in_kyuura"}
    for code in sorted(pending & set(index)):
        problems.append(f"kyuura に記録がないとした停止コード {code} が、kyuura の未解決の一覧にある（対応表を直す）")
    expected = set(links["stop_codes"]) - pending
    if set(index) - pending != expected:
        problems.append(f"停止コードの集合が違う: kyuura だけ {sorted(set(index) - set(links['stop_codes']))}、"
                        f"対応表だけ {sorted(expected - set(index))}")
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
    texts = registered_texts(registry)
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
        # 出典は LD- のページ（過去の原典照合で登録したもの）か、LD- の id（kyuura データの採用で、最新の説明を根拠にしたもの。2026-10-15 から）
        if source != ld_id and source != f"P43 p.{record['latest_description']['page']}" \
                and not (source or "").startswith(f"P43 p.{record['latest_description']['page']}"):
            problems.append(f"{target}: 出典 {source} が kyuura の {ld_id} のページ（p.{record['latest_description']['page']}）と違う")
    adopted_printed = set(section.get("adopted_printed_text", []))
    in_checks = set(section.get("recorded_in_card_checks", {})) | set(section.get("card_checks_without_text", {})) | adopted_printed
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
    if adopted_printed & (accounted | set(section["registered_without_kyuura_record"])):
        problems.append("adopted_printed_text の登録が、ほかの区分にも入っている")

    # 4c. kyuura データの採用で、処理に使う文面を kyuura の印刷の文面にした登録（2026-10-15 からの方針）
    data_errors = {(x["card_id"], e.get("field")) for x in checks for e in (x.get("data_error") or [])}
    for target in sorted(adopted_printed):
        card, kind, index = target.split("/")
        path = f"pokemon.{'attacks' if kind == 'attack' else 'powers'}[{index}].text.ja"
        if target not in texts:
            problems.append(f"{target}: adopted_printed_text の登録に、処理に使う文面がない")
            continue
        theirs = research_cards.get(card)
        items = ((theirs or {}).get("pokemon") or {}).get("attacks" if kind == "attack" else "powers") or []
        printed = (items[int(index)].get("text") or {}).get("ja") if int(index) < len(items) else None
        if printed != texts[target][0]:
            problems.append(f"{target}: 処理に使う文面が、研究の基準のコミットの印刷の文面と違う")
        if target in ld_by_target:
            problems.append(f"{target}: kyuura に最新の説明の記録 {ld_by_target[target]} がある（registered に移し、最新の説明にしたがう）")
        if (card, path) in data_errors:
            problems.append(f"{target}: kyuura の照合の記録に、この文面のデータの誤りの記録がある（論点を記録してカードを保留にする）")

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
    # kyuura に照合の記録がないとしたカード（報告事項）に、kyuura の記録ができていたら、一覧を直す（v0.19）
    for card in links["card_checks"]["engine_verified_without_kyuura_record"]:
        found = sorted(x["id"] for x in checks if x["card_id"] == card)
        if found:
            problems.append(f"kyuura に照合の記録がないとしたカード {card} に、kyuura の記録 {found} がある")
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
    extract = json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text(encoding="utf-8"))
    if extract["source"]["commit"] != links["card_data_commit"]:
        problems.append(f"写しのコミット {extract['source']['commit']} が対応表の card_data_commit と違う")
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

    # 7. kyuura データの採用の記録と、研究の基準のコミットの kyuura の記録（2026-10-15 からの方針）
    if sources is None:
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
    errata = git_show(kyuura, commit, "data/rule_history.json")["errata"]
    for card, record in sources.items():
        if not isinstance(record, dict) or record.get("basis") != "kyuura_data":
            continue
        found = {x["id"] for x in descriptions if x["card_id"] == card}
        found |= {x["id"] for x in checks if x["card_id"] == card}
        found |= {x["id"] for x in rulings["rulings"]
                  if card in {c.get("card_id") for c in x.get("cards") or []} | set(x.get("related_cards") or [])}
        found |= {x["id"] for x in rulings["issues"] if card in {c.get("card_id") for c in x.get("cases") or []}}
        found |= {x["id"] for x in errata if card in (x.get("cards") or [])}
        listed = set(record.get("kyuura_records") or [])
        if listed != found:
            problems.append(f"{card}: 採用の記録の kyuura_records が、研究の基準のコミットの kyuura の記録と違う"
                            f"（kyuura だけ {sorted(found - listed)}、採用の記録だけ {sorted(listed - found)}）")
        for target, basis in (record.get("play_text") or {}).items():
            if isinstance(basis, str) and basis.split("-")[0] in ("ERR", "TXT", "RUL") and basis not in found:
                problems.append(f"{card} {target}: 根拠のエラッタ {basis} が、研究の基準のコミットでこのカードを指していない")
        noted = {f for issue in record.get("issues") or [] if isinstance(issue, dict) for f in issue.get("fields") or []}
        for x in checks:
            if x["card_id"] != card:
                continue
            for e in x.get("data_error") or []:
                if e.get("field") not in noted:
                    problems.append(f"{card}: kyuura の {x['id']} のデータの誤りの欄 {e.get('field')} が、採用の記録の論点にない")
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
