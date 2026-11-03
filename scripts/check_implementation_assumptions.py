"""実装上の仮定の一覧 docs/implementation-assumptions.json を確かめ、文書の生成した表を書く（調査・文書化だけ。エンジンの動作は変えない）。

    python scripts/check_implementation_assumptions.py --check   # 台帳の不変条件・参照・集計・文書の表を確かめる
    python scripts/check_implementation_assumptions.py --write   # 集計（counts）と文書の生成した表を台帳から書き直す
    python scripts/check_implementation_assumptions.py --sites   # 今の木の候補箇所と、台帳の site_dispositions を比べる（差は報告だけ）

台帳（JSON）が項目の正本です。文書（docs/implementation-assumptions.md）の印の間の表は、この台帳から書きます（手で直さない）。

``--check`` が確かめるのは台帳の内部の整合だけです（件数を写した期待値は持たない）。候補箇所の網羅は ``--sites`` が、台帳の基点の時点の走査と今の木を比べて報告します。
後の正当な文書の変更で候補箇所が増減しても、``--check`` は失敗しません（``--sites`` が差を示すので、数え上げをやり直すかを判断する）。
"""

from __future__ import annotations

import argparse
import ast
import collections
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import implementation_assumptions_scan as scan

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "implementation-assumptions.json"
DOCUMENT = ROOT / "docs" / "implementation-assumptions.md"
STOP_POLICY = ROOT / "docs" / "stop-policy-classification.json"
INVENTORY = ROOT / "docs" / "pre-freeze-gap-inventory.json"
RESEARCH = ROOT / "kyuura_engine" / "data" / "research_links.json"

CATEGORIES = {
    "official_direct": "1. 公式情報から直接確定",
    "inference": "2. 公式情報からの推論・類推を含む",
    "normalization": "3. 結果が同じことを根拠にした正規化",
    "engine_adopted": "4. 公式では決まらないがエンジンが採っている挙動",
    "later_source": "5. 後年・別版・別言語の資料を限定的に採用",
    "user_specified": "6. 利用者の明示指定",
    "data_correction": "7. データ訂正・表記の扱い",
    "implementation_method": "8. 純粋な実装方式・最適化",
    "unresolved_stop": "9. 未解決として停止",
    "defect_or_unsupported": "10. 不具合・未対応・確認不足",
}
MAIN_CATEGORIES = ("inference", "normalization", "engine_adopted", "later_source", "user_specified")
STATUSES = {
    "adopted_current": "現行コードで採用中",
    "documented_impl_unverified": "文書にはあるが実装を確認できない",
    "superseded": "以前は採用したが修正・廃止済み",
    "merged_duplicate": "他の項目へ統合した重複記載",
    "unconfirmed": "未確認",
}
GROUPS = {
    "approved_user": "承認済み指定として基礎集合に含まれる",
    "needs_decision": "追加の採否判断が必要",
    "needs_research": "研究で確認すべき",
    "technical": "技術的な実装方式（対戦規約として識別する必要が薄い）",
    "defect_separate": "不具合・未対応として別作業",
    "history": "過去の記録として保持",
}
VERIFICATION = ("doc", "code", "tests_read", "tests_run", "reach_unconfirmed")
IMPACT_AXES = ("outcome", "legal_actions", "card_movement", "rng_order", "public_info", "save_replay")
DISPOSITIONS = ("item", "merged", "excluded", "unconfirmed")
REASON_CLASSES = ("official_direct", "data_correction", "implementation_method", "unresolved_stop", "defect_or_unsupported",
                  "meta_reference", "negation", "other")
APPROVAL = ("user_approved", "none")
RESOLVED_WORDS = ("解決済み", "確定した裁定", "公式に決まった")


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _exists(rel: str) -> bool:
    return (ROOT / rel.split("#", 1)[0]).exists()


_SYMBOLS: dict[str, set[str]] = {}


def _symbols(rel: str) -> set[str]:
    """モジュールの最上位・クラスの中の名前（関数・クラス・代入の対象）。"""
    if rel not in _SYMBOLS:
        names: set[str] = set()
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                for target in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                    if isinstance(target, ast.Name):
                        names.add(target.id)
        _SYMBOLS[rel] = names
    return _SYMBOLS[rel]


def symbol_problem(rel: str, symbol: str) -> str | None:
    """``symbol`` の各部分（``A.b``・``A/B``・``A['k']`` の名前の部分）のうち、少なくとも先頭の名前がそのファイルにあるか。"""
    head = re.split(r"[.\[(/ 、・]", symbol.strip(), maxsplit=1)[0]
    if not head or not rel.endswith(".py"):
        return None
    if head not in _symbols(rel) and head not in (ROOT / rel).read_text(encoding="utf-8"):
        return f"{rel}: 名前 {head} が見つからない"
    return None


def _test_name_problem(rel: str, name: str) -> str | None:
    if not rel.endswith(".py") or not name:
        return None
    parts = [p for p in re.split(r"[.\s]", name) if p and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", p)]
    text = (ROOT / rel).read_text(encoding="utf-8")
    missing = [p for p in parts if not re.search(rf"\b(def|class)\s+{re.escape(p)}\b", text)]
    if parts and missing:
        return f"{rel}: テスト {name} の {missing} が見つからない"
    return None


def counts(ledger: dict) -> dict:
    items = ledger["items"]
    current = [i for i in items if i["status"] != "merged_duplicate"]
    sites = ledger["site_dispositions"]
    by = lambda key, rows: dict(sorted(collections.Counter(r[key] for r in rows).items()))
    main = [i for i in current if i["category"] in MAIN_CATEGORIES]
    return {
        "documents_scanned": ledger["scan"]["documents_scanned"],
        "documents_with_sites": len({s["path"] for s in sites if s["path"].endswith(".md")}),
        "files_with_sites": len({s["path"] for s in sites}),
        "sites": len(sites),
        "sites_by_surface": by("surface", sites),
        "sites_by_disposition": by("disposition", sites),
        "sites_excluded_by_reason": by("reason_class", [s for s in sites if s["disposition"] == "excluded"]),
        "items": len(items),
        "items_after_merge": len(current),
        "items_by_category": by("category", current),
        "items_by_status": by("status", items),
        "items_by_group": by("baseline_group", current),
        "main_items": len(main),
        "main_items_adopted_current": sum(1 for i in main if i["status"] == "adopted_current"),
        "main_items_user_approved": sum(1 for i in main if i["approval"]["status"] == "user_approved"),
        "main_items_not_approved": sum(1 for i in main if i["approval"]["status"] != "user_approved"),
        "items_user_approved_all_categories": sum(1 for i in current if i["approval"]["status"] == "user_approved"),
        "main_items_unconfirmed_status": sum(1 for i in main if i["status"] in ("unconfirmed", "documented_impl_unverified")),
        "main_items_with_unconfirmed_points": sum(1 for i in main if i.get("unconfirmed")),
        "main_items_verification": {level: sum(1 for i in main if level in i["verification"]) for level in VERIFICATION},
        "main_items_doc_only": sum(1 for i in main if not set(i["verification"]) & {"code", "tests_read", "tests_run"}),
        "user_specification_rules": len({i["id"] for i in current if i["category"] == "user_specified"}),
        "user_specification_targets": sum(len(i.get("targets_registered", [])) for i in current if i["category"] == "user_specified"),
        "keywordless_items": sum(1 for i in current if i.get("found_by") == "keywordless_review"),
        "discrepancies": len(ledger["discrepancies"]),
    }


def check(ledger: dict) -> list[str]:
    problems: list[str] = []
    items = ledger["items"]
    ids = [i["id"] for i in items]
    for dup in sorted({x for x in ids if ids.count(x) > 1}):
        problems.append(f"項目の ID が重複: {dup}")
    known = set(ids)
    by_id = {i["id"]: i for i in items}
    stop = load(STOP_POLICY)
    conventions = {c["id"]: c for c in stop["conventions"]}
    research = load(RESEARCH)
    uq_known = set()
    for record in research.get("implementation_assumptions_with_issue", []):
        uq_known.add(record["kyuura_issue"])

    for item in items:
        where = item["id"]
        if not re.fullmatch(r"IA-[A-Z0-9][A-Z0-9-]*[A-Z0-9]", item["id"]):
            problems.append(f"{where}: ID の形（IA-英大文字のスラッグ）でない")
        if item["category"] not in CATEGORIES:
            problems.append(f"{where}: 分類 {item['category']} が未知")
        if item["status"] not in STATUSES:
            problems.append(f"{where}: 状態 {item['status']} が未知")
        if item["status"] == "merged_duplicate":
            target = item.get("merged_into")
            if target not in known or by_id[target]["status"] == "merged_duplicate":
                problems.append(f"{where}: 統合先 {target} が一覧にない（または統合先も重複記載）")
            for ref in item.get("doc_refs", []):
                if not _exists(ref["path"]):
                    problems.append(f"{where}: 文書 {ref['path']} がない")
            continue
        if item["baseline_group"] not in GROUPS:
            problems.append(f"{where}: 群 {item['baseline_group']} が未知")
        if set(item["verification"]) - set(VERIFICATION):
            problems.append(f"{where}: 確認の段階 {set(item['verification']) - set(VERIFICATION)} が未知")
        if set(item["alternative_impact"]) != set(IMPACT_AXES):
            problems.append(f"{where}: 別の扱いの影響の軸が {sorted(IMPACT_AXES)} と違う")
        approval = item["approval"]
        if approval["status"] not in APPROVAL:
            problems.append(f"{where}: 承認の状態 {approval['status']} が未知")
        if approval["status"] == "user_approved":
            ev = approval.get("evidence") or {}
            for key in ("document", "on", "instruction"):
                if not ev.get(key):
                    problems.append(f"{where}: 利用者承認の根拠に {key} がない")
            doc = (ev.get("document") or "").split()[0] if ev.get("document") else ""
            if doc and _exists(doc) and ev.get("instruction") and ev["instruction"] not in (ROOT / doc).read_text(encoding="utf-8"):
                problems.append(f"{where}: 指定の文が根拠の文書 {doc} にない")
            if item["category"] not in ("user_specified", "data_correction"):
                problems.append(f"{where}: 利用者承認は利用者指定・利用者が示したデータの訂正だけ")
        if item["category"] == "user_specified" and approval["status"] != "user_approved":
            problems.append(f"{where}: 利用者指定なのに承認の根拠がない")
        if item["baseline_group"] == "approved_user" and approval["status"] != "user_approved":
            problems.append(f"{where}: approved_user の群は利用者承認の根拠が要る")
        if item["category"] in ("normalization",) and item["status"] != "merged_duplicate":
            eq = item.get("equivalence") or {}
            for key in ("compared", "conditions", "verified_scope"):
                if not eq.get(key):
                    problems.append(f"{where}: 正規化の {key}（何と何を比べたか・成立条件・検証範囲）がない")
        for ref in item.get("doc_refs", []):
            if not _exists(ref["path"]):
                problems.append(f"{where}: 文書 {ref['path']} がない")
        for ref in item.get("code_refs", []):
            if not _exists(ref["path"]):
                problems.append(f"{where}: コード {ref['path']} がない")
            elif ref.get("symbol"):
                p = symbol_problem(ref["path"], ref["symbol"])
                if p:
                    problems.append(f"{where}: {p}")
        for ref in item.get("test_refs", []):
            if not _exists(ref["path"]):
                problems.append(f"{where}: テスト {ref['path']} がない")
            else:
                p = _test_name_problem(ref["path"], ref.get("name", ""))
                if p:
                    problems.append(f"{where}: {p}")
        for conv in item.get("ledger_refs", {}).get("stop_policy_conventions", []):
            if conv not in conventions:
                problems.append(f"{where}: 停止の方針の台帳の規約 {conv} がない")
        resolved_claim = [w for w in RESOLVED_WORDS if w in item.get("statement", "") and "しない" not in item.get("statement", "")]
        if resolved_claim and any(r.startswith("UQ-") for r in item.get("research_refs", [])):
            problems.append(f"{where}: 研究の論点（UQ-）を持つ項目の内容に「{resolved_claim[0]}」とある（一覧化で論点を解決済みにしない）")
        if item.get("research_status_changed"):
            problems.append(f"{where}: この一覧は研究の論点の状態を変えない（research_status_changed を持たない）")

    # 既存台帳の 18 対象の対応
    mapped = collections.defaultdict(list)
    for item in items:
        for conv in item.get("ledger_refs", {}).get("stop_policy_conventions", []):
            mapped[conv].append(item["id"])
    for conv_id, conv in conventions.items():
        if conv_id not in mapped:
            problems.append(f"停止の方針の台帳の規約 {conv_id} が、どの項目にも対応付けられていない")
            continue
        for iid in mapped[conv_id]:
            item = by_id[iid]
            if conv["baseline_category"] == "user_specified" and item.get("approval", {}).get("status") != "user_approved":
                problems.append(f"{iid}: 台帳 {conv_id} は利用者指定なのに、承認の根拠がない")
            if conv["baseline_category"] != "user_specified" and item["category"] == "user_specified":
                problems.append(f"{iid}: 台帳 {conv_id} は利用者指定でないのに、利用者指定に分類した")
    for item in items:
        if item.get("approval", {}).get("status") == "user_approved" and item["category"] == "user_specified":
            convs = item.get("ledger_refs", {}).get("stop_policy_conventions", [])
            if not any(conventions.get(c, {}).get("baseline_category") == "user_specified" for c in convs):
                problems.append(f"{item['id']}: 利用者承認の項目が、停止の方針の台帳の利用者指定の記録に対応していない")

    # 候補箇所の整理
    site_ids = [s["id"] for s in ledger["site_dispositions"]]
    for dup in sorted({x for x in site_ids if site_ids.count(x) > 1}):
        problems.append(f"候補箇所の ID が重複: {dup}")
    for site in ledger["site_dispositions"]:
        d = site["disposition"]
        if d not in DISPOSITIONS:
            problems.append(f"{site['id']}: 整理 {d} が未知")
        if d in ("item", "merged"):
            if site.get("item_id") not in known:
                problems.append(f"{site['id']}: 項目 {site.get('item_id')} が一覧にない")
        elif d == "excluded":
            if site.get("reason_class") not in REASON_CLASSES:
                problems.append(f"{site['id']}: 除外の理由の区分 {site.get('reason_class')} が未知")
            if not site.get("reason"):
                problems.append(f"{site['id']}: 除外の理由がない")
            if site.get("item_id") and site["item_id"] not in known:
                problems.append(f"{site['id']}: 参照する項目 {site['item_id']} が一覧にない")
        elif d == "unconfirmed" and not site.get("reason"):
            problems.append(f"{site['id']}: 未確認の理由がない")
    for disc in ledger["discrepancies"]:
        for iid in disc.get("item_ids", []):
            if iid not in known:
                problems.append(f"食い違い {disc['id']}: 項目 {iid} が一覧にない")
    disc_ids = [d["id"] for d in ledger["discrepancies"]]
    for dup in sorted({x for x in disc_ids if disc_ids.count(x) > 1}):
        problems.append(f"食い違いの ID が重複: {dup}")
    for row in ledger.get("decision_order", []):
        for iid in row.get("item_ids", []):
            if iid not in known:
                problems.append(f"採否判断の順序: 項目 {iid} が一覧にない")

    if ledger.get("counts") != counts(ledger):
        problems.append("集計（counts）が台帳の項目・候補箇所から数え直した値と違う（--write で書き直す）")
    problems += generated_block_problems(ledger)
    return problems


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 文書の生成した表
# ---------------------------------------------------------------------------------------------------------------------------------------------------

def _markers(name: str) -> tuple[str, str]:
    return (f"<!-- generated:{name} begin（scripts/check_implementation_assumptions.py --write が台帳から書く。手で直さない） -->",
            f"<!-- generated:{name} end -->")


def _cell(value) -> str:
    if isinstance(value, (list, tuple)):
        value = "・".join(str(v) for v in value)
    return str(value).replace("|", "／").replace("\n", " ")


def _short(values, limit: int = 70) -> str:
    """表の対象の欄: 先頭の 2 つまで、長ければ切る（全体は台帳の targets）。"""
    text = _cell(list(values)[:2]) + ("・…" if len(values) > 2 else "")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def render_counts(ledger: dict) -> str:
    c = ledger["counts"]
    rows = [
        ("走査した文書（docs/*.md）", c["documents_scanned"]),
        ("候補箇所のある文書", c["documents_with_sites"]),
        ("候補箇所のあるファイル（文書・コード・テスト・スクリプト）", c["files_with_sites"]),
        ("候補箇所（行）", c["sites"]),
        ("候補箇所の内訳（面）", "・".join(f"{k} {v}" for k, v in c["sites_by_surface"].items())),
        ("候補箇所の整理", "・".join(f"{k} {v}" for k, v in c["sites_by_disposition"].items())),
        ("除外の理由", "・".join(f"{k} {v}" for k, v in c["sites_excluded_by_reason"].items())),
        ("項目（重複記載を含む）", c["items"]),
        ("重複統合後の項目", c["items_after_merge"]),
        ("分類別（重複統合後）", "・".join(f"{k} {v}" for k, v in c["items_by_category"].items())),
        ("状態別（すべての項目）", "・".join(f"{k} {v}" for k, v in c["items_by_status"].items())),
        ("群別（重複統合後）", "・".join(f"{k} {v}" for k, v in c["items_by_group"].items())),
        ("主要な一覧（分類 2〜6）", c["main_items"]),
        ("　うち現行コードで採用中", c["main_items_adopted_current"]),
        ("　うち利用者承認あり", c["main_items_user_approved"]),
        ("　うち利用者承認なし", c["main_items_not_approved"]),
        ("　うち状態が未確認・実装を確認できない", c["main_items_unconfirmed_status"]),
        ("　うち未確認事項を持つ", c["main_items_with_unconfirmed_points"]),
        ("　確認の段階（該当する項目の数。重なる）", "・".join(f"{k} {v}" for k, v in c["main_items_verification"].items())),
        ("　うち文書の記載だけを確認", c["main_items_doc_only"]),
        ("承認ありの項目（データの訂正を含むすべての分類）", c["items_user_approved_all_categories"]),
        ("利用者指定の規約（USER-ID の数）", c["user_specification_rules"]),
        ("利用者指定の登録対象（カードの位置の数）", c["user_specification_targets"]),
        ("キーワードのない見直しで見つけた項目", c["keywordless_items"]),
        ("食い違い", c["discrepancies"]),
    ]
    return "\n".join(["| 集計 | 値 |", "|---|---|"] + [f"| {a} | {_cell(b)} |" for a, b in rows])


def render_items(ledger: dict, groups: tuple[str, ...]) -> str:
    head = ["| ID | 名称 | 分類 | 状態 | 承認 | 対象 | 確認 |", "|---|---|---|---|---|---|---|"]
    rows = []
    order = {g: n for n, g in enumerate(GROUPS)}
    for item in sorted((i for i in ledger["items"] if i["status"] != "merged_duplicate" and i["baseline_group"] in groups),
                       key=lambda i: (order[i["baseline_group"]], list(CATEGORIES).index(i["category"]), i["id"])):
        rows.append(f"| `{item['id']}` | {_cell(item['name'])} | {CATEGORIES[item['category']].split('. ', 1)[0]} | {item['status']} | "
                    f"{'あり' if item['approval']['status'] == 'user_approved' else 'なし'} | {_short(item.get('targets', []))} | {_cell(item['verification'])} |")
    return "\n".join(head + rows)


def render_discrepancies(ledger: dict) -> str:
    head = ["| ID | 項目 | 内容 |", "|---|---|---|"]
    return "\n".join(head + [f"| `{d['id']}` | {_cell(d.get('item_ids', []))} | {_cell(d['summary'])} |" for d in ledger["discrepancies"]])


def render_existing(ledger: dict) -> str:
    stop = load(STOP_POLICY)
    head = ["| 停止の方針の台帳の規約 | 区分 | この一覧の項目 |", "|---|---|---|"]
    mapped = collections.defaultdict(list)
    for item in ledger["items"]:
        for conv in item.get("ledger_refs", {}).get("stop_policy_conventions", []):
            mapped[conv].append(item["id"])
    return "\n".join(head + [f"| `{c['id']}` | {c['baseline_category']} | {_cell(['`' + x + '`' for x in mapped.get(c['id'], [])])} |"
                             for c in stop["conventions"]])


BLOCKS = {
    "counts": render_counts,
    "items-approved": lambda l: render_items(l, ("approved_user",)),
    "items-decision": lambda l: render_items(l, ("needs_decision",)),
    "items-research": lambda l: render_items(l, ("needs_research",)),
    "items-other": lambda l: render_items(l, ("technical", "defect_separate", "history")),
    "existing-ledger": render_existing,
    "discrepancies": render_discrepancies,
}


def with_generated_blocks(text: str, ledger: dict) -> str:
    for name, render in BLOCKS.items():
        begin, end = _markers(name)
        pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
        if pattern.search(text):
            text = pattern.sub(lambda _: f"{begin}\n{render(ledger)}\n{end}", text)
    return text


def generated_block_problems(ledger: dict) -> list[str]:
    if not DOCUMENT.exists():
        return [f"{DOCUMENT.name} がない"]
    text = DOCUMENT.read_text(encoding="utf-8")
    problems = [f"{DOCUMENT.name}: 生成する表 {n} の印がない" for n in BLOCKS if _markers(n)[0] not in text]
    known = {i["id"] for i in ledger["items"]} | {d["id"] for d in ledger["discrepancies"]}
    for ref in sorted(set(re.findall(r"`((?:IA|DISC)-[A-Z0-9][A-Z0-9-]*[A-Z0-9])`", text)) - known):
        if not ref.endswith("-"):
            problems.append(f"{DOCUMENT.name}: 本文の {ref} が台帳にない")
    if with_generated_blocks(text, ledger) != text:
        problems.append(f"{DOCUMENT.name}: 生成した表が台帳と違う（--write で書き直す）")
    return problems


def site_differences(ledger: dict) -> dict:
    now = {s["id"]: s for s in scan.scan(ROOT)}
    recorded = {s["id"]: s for s in ledger["site_dispositions"]}
    return {"new_sites": sorted(set(now) - set(recorded)), "missing_sites": sorted(set(recorded) - set(now))}


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    group.add_argument("--sites", action="store_true")
    args = parser.parse_args()
    ledger = load(LEDGER)
    if args.write:
        ledger["counts"] = counts(ledger)
        LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        DOCUMENT.write_text(with_generated_blocks(DOCUMENT.read_text(encoding="utf-8"), ledger), encoding="utf-8")
        return 0
    if args.sites:
        diff = site_differences(ledger)
        print(json.dumps({k: len(v) for k, v in diff.items()}, ensure_ascii=False))
        for key, values in diff.items():
            for v in values[:50]:
                print(key, v)
        return 0
    problems = check(ledger)
    for p in problems:
        print(p)
    print(f"problems={len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
