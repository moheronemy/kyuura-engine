"""正規化の成立条件の再検証（docs/normalization-revalidation.json）の検査と、文書の表の生成。

エンジンの動作・データは変えない。元の実装上の仮定の一覧（docs/implementation-assumptions.json）は読むだけ
（元の一覧への参照は、その台帳の ``addenda`` が持つ。過去の基点・集計は書き換えない）。

- ``--check``: 台帳の内部の整合と、元の一覧との対応を確かめる（問題があれば終了コード 1）。
- ``--write``: 集計（``counts``）を数え直し、文書の生成した表を書き直す。

確かめること（件数を期待値に写すのではなく、対応の漏れ・不整合を見つける）:

- 項目の ID の一意性と、元の一覧にあること（統合済みの重複を対象にしない）。
- 対象の範囲: 元の一覧の採否判断の順序のうち「前提の崩れ」の段の項目がすべて主対象にあり、範囲を広げた項目には理由がある。
- 食い違いの対応: 元の一覧の食い違いのうち、種類が premise_changed・equivalence_scope のものと、主対象の項目を指すものが、
  対応表にちょうど 1 回ずつあり、項目の対応が元の記録と同じで、その項目が再検証にある（ないなら理由がある）。
- 項目の欄: 9 つの軸がすべてあり、値が決めた語の中にある。分類と軸の評価の矛盾（A なのに違う軸がある、C なのに違う軸がない、など）。
- 確かめ方の区別: 合法な操作で到達したと書く項目は、合法な操作列の再現を持つ。構築盤面だけなら合法な操作の到達と書かない。
  実行で確かめたと書く軸は、再現または実行したテストを持つ。実行したと書くテストは、実行の記録にある。
- 参照: コードの名前・テストの名前・文書の存在。
- 範囲を添えない「問題なし」「網羅」「到達不能」がない（否定の言い方・未確認の事項の欄は除く）。
- 既存テストで到達を確かめた項目は、構築盤面・補助関数として扱い、そのテストが実行の記録にある。
- 承認の補完: 3 枚が写しの対象外の記録と名前まで一致し、指示の文があり、承認の範囲が 3 枚の移管だけである。
- 集計と文書の表が台帳と一致し、文書の本文の ID が台帳にある。
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check_implementation_assumptions as IA  # noqa: E402

ROOT = IA.ROOT
LEDGER = ROOT / "docs" / "normalization-revalidation.json"
DOCUMENT = ROOT / "docs" / "normalization-revalidation.md"
SOURCE = IA.LEDGER
CARDS = ROOT / "kyuura_engine" / "data" / "kyuura_cards.json"

AXES = {
    "legal_actions": "合法な操作・選択肢",
    "chooser": "選択するプレイヤー",
    "visible_info": "決定の時点で各プレイヤーに見える情報",
    "card_movement": "カードの移動先・移動順・処理途中の状態",
    "triggers_order": "効果・特殊能力・きぜつなどの誘発と処理順",
    "final_board_outcome": "最終的な盤面・勝敗",
    "distribution": "結果の確率分布",
    "rng_consumption": "乱数の消費回数と、同じ seed の続き",
    "log_save": "ログ・観測・保存復元",
}
VERDICTS = ("same", "differs", "conditional", "unknown", "not_applicable")
AXIS_CONFIDENCE = ("verified_run", "code_read", "doc_only", "unknown")
CLASSIFICATIONS = {
    "A": "確認した範囲では同等性が成立する",
    "B": "条件付きで成立する",
    "C": "同等性が成立しない",
    "D": "根拠・実装・到達可能性などが不足しており未確認",
}
RECOMMENDATIONS = {
    "maintain_document": "現行処理を維持し、成立条件の説明を補う",
    "common_defect_candidate": "両モード共通の不具合として修正候補にする",
    "user_rule_decision": "規約として利用者の判断が必要",
    "official_research": "公式情報の追加調査が必要",
    "implementation_rng_log": "実装方式・乱数再現性・ログの問題として扱う",
    "other_pending": "その他、または判断保留",
}
PRIORITIES = ("P0", "P1", "P2", "P3", "unknown")
SEVERITIES = ("high", "medium", "low", "unknown")
REACH_STATUS = ("reached_legal_ops", "constructed_state", "helper_only", "modified_impl", "not_reproduced", "not_applicable")
REACH_LEVELS = ("legal_play_confirmed", "legal_play_likely", "construct_only", "unknown")
CONFIDENCE = ("high", "medium", "low")
REPRO_KINDS = ("legal_ops", "constructed", "helper", "modified_impl")
BASIS = ("official_doc", "alternative_impl", "verification_assumption")
SCOPES = ("primary", "extended")
DISC_KINDS_IN_SCOPE = ("premise_changed", "equivalence_scope")
PREMISE_STEP_TITLE = "前提の崩れ"
SCOPE_WORDS = ("問題なし", "網羅", "到達不能")
# 「到達不能とはしない」「網羅の検索はしていない」のような否定の言い方は、確かめた範囲の主張ではないので許す（未確認の事項の欄も同じ）
SCOPE_NEGATION = r"[^。]{0,16}?(?:していない|とはしない|とは確かめていない|ではない|とはしていない)"
APPROVAL_COMPONENT_CLASSES = ("quote_missing", "no_approval")


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def primary_ids(source: dict) -> list[str]:
    steps = [row for row in source.get("decision_order", []) if PREMISE_STEP_TITLE in row.get("title", "")]
    return list(steps[0]["item_ids"]) if len(steps) == 1 else []


def in_scope_discrepancies(source: dict, primary: set[str]) -> list[dict]:
    return [d for d in source["discrepancies"] if d["kind"] in DISC_KINDS_IN_SCOPE or set(d.get("item_ids", [])) & primary]


def _texts(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _texts(v)
    elif isinstance(value, list):
        for v in value:
            yield from _texts(v)


def _executed(ledger: dict) -> list[str]:
    return [t["target"] for t in ledger.get("tests_executed", [])]


def _test_was_run(name: str, path: str, executed: list[str]) -> bool:
    module = "tests." + pathlib.PurePosixPath(path).stem
    full = f"{module}.{name}"
    return any(full == t or full.startswith(t + ".") or t.startswith(full + ".") or t == module for t in executed)


def counts(ledger: dict) -> dict:
    items = ledger["items"]
    by = lambda key: dict(sorted(collections.Counter(i[key] for i in items).items()))
    repro = collections.Counter(r["kind"] for i in items for r in i.get("repro", []))
    tests = [t for i in items for t in i.get("test_refs", [])]
    return {
        "items": len(items),
        "items_by_scope": by("scope"),
        "items_by_classification": by("classification"),
        "items_by_priority": by("priority"),
        "items_by_recommendation": by("recommendation"),
        "items_by_reachability": dict(sorted(collections.Counter(i["reachability"]["status"] for i in items).items())),
        "axes_differs": {axis: sum(1 for i in items if i.get("axes", {}).get(axis, {}).get("verdict") == "differs") for axis in AXES},
        "repro_by_kind": dict(sorted(repro.items())),
        "discrepancies_mapped": len(ledger["discrepancy_mapping"]),
        "test_refs_run": sum(1 for t in tests if t.get("run")),
        "test_refs_read_only": sum(1 for t in tests if not t.get("run")),
        "tests_executed_targets": len(ledger.get("tests_executed", [])),
    }


def check(ledger: dict, source: dict | None = None) -> list[str]:
    source = source if source is not None else load(SOURCE)
    problems: list[str] = []
    src_items = {i["id"]: i for i in source["items"]}
    items = ledger["items"]
    ids = [i["item_id"] for i in items]
    for dup in sorted({x for x in ids if ids.count(x) > 1}):
        problems.append(f"項目が重複: {dup}")
    by_id = {i["item_id"]: i for i in items}

    # 範囲
    primary = primary_ids(source)
    if not primary:
        problems.append(f"元の一覧に「{PREMISE_STEP_TITLE}」の段が 1 つだけない")
    for iid in primary:
        if iid not in by_id:
            problems.append(f"主対象 {iid} の再検証がない")
        elif by_id[iid]["scope"] != "primary":
            problems.append(f"{iid}: 主対象なのに scope が {by_id[iid]['scope']}")
    for item in items:
        iid = item["item_id"]
        if iid not in src_items:
            problems.append(f"{iid}: 元の一覧にない")
            continue
        if src_items[iid]["status"] == "merged_duplicate":
            problems.append(f"{iid}: 元の一覧で統合済みの重複（統合先 {src_items[iid].get('merged_into')} を対象にする）")
        if item.get("scope") not in SCOPES:
            problems.append(f"{iid}: scope が {item.get('scope')}")
        if item.get("scope") == "extended":
            if iid in primary:
                problems.append(f"{iid}: 主対象なのに extended")
            if not item.get("scope_reason"):
                problems.append(f"{iid}: 範囲を広げた理由がない")

    # 食い違いの対応
    expected = {d["id"]: d for d in in_scope_discrepancies(source, set(primary))}
    mapping = ledger["discrepancy_mapping"]
    mapped_ids = [m["disc_id"] for m in mapping]
    for dup in sorted({x for x in mapped_ids if mapped_ids.count(x) > 1}):
        problems.append(f"食い違いの対応が重複: {dup}")
    for missing in sorted(set(expected) - set(mapped_ids)):
        problems.append(f"食い違い {missing} の対応がない")
    for row in mapping:
        disc = expected.get(row["disc_id"])
        if disc is None:
            problems.append(f"対応表の {row['disc_id']} は対象の食い違いでない（元の一覧にない・種類が違う）")
            continue
        if row.get("kind") != disc["kind"] or sorted(row.get("item_ids", [])) != sorted(disc.get("item_ids", [])):
            problems.append(f"{row['disc_id']}: 種類・項目の対応が元の一覧と違う")
        for iid in disc.get("item_ids", []):
            if iid not in by_id and not row.get("not_covered_reason"):
                problems.append(f"{row['disc_id']}: 項目 {iid} の再検証がなく、理由もない")
        if row.get("in_primary") != bool(set(disc.get("item_ids", [])) & set(primary)):
            problems.append(f"{row['disc_id']}: in_primary が主対象との関係と違う")

    # 項目の欄
    executed = _executed(ledger)
    for item in items:
        iid = item["item_id"]
        axes = item.get("axes", {})
        for axis in AXES:
            a = axes.get(axis)
            if not isinstance(a, dict):
                problems.append(f"{iid}: 軸 {axis} がない")
                continue
            if a.get("verdict") not in VERDICTS:
                problems.append(f"{iid}: 軸 {axis} の評価 {a.get('verdict')}")
            if a.get("confidence") not in AXIS_CONFIDENCE:
                problems.append(f"{iid}: 軸 {axis} の確度 {a.get('confidence')}")
            if a.get("verdict") not in ("not_applicable",) and not a.get("detail"):
                problems.append(f"{iid}: 軸 {axis} の説明がない")
        for axis in set(axes) - set(AXES):
            problems.append(f"{iid}: 決めていない軸 {axis}")
        verdicts = [axes.get(a, {}).get("verdict") for a in AXES]
        cls = item.get("classification")
        if cls not in CLASSIFICATIONS:
            problems.append(f"{iid}: 分類 {cls}")
        if cls == "A" and "differs" in verdicts:
            problems.append(f"{iid}: 分類 A なのに違う軸がある")
        if cls == "C" and "differs" not in verdicts:
            problems.append(f"{iid}: 分類 C なのに違う軸がない")
        if cls == "B" and not item.get("conditions_for_equivalence"):
            problems.append(f"{iid}: 分類 B なのに成立の条件がない")
        if cls == "D" and not item.get("unconfirmed"):
            problems.append(f"{iid}: 分類 D なのに未確認の内容がない")
        for key, allowed in (("priority", PRIORITIES), ("severity", SEVERITIES), ("reachability_level", REACH_LEVELS),
                             ("confidence", CONFIDENCE), ("recommendation", tuple(RECOMMENDATIONS))):
            if item.get(key) not in allowed:
                problems.append(f"{iid}: {key} が {item.get(key)}")
        if item.get("comparison", {}).get("basis") not in BASIS:
            problems.append(f"{iid}: 比較対象の出所が {item.get('comparison', {}).get('basis')}")
        for key in ("current_processing", "classification_reason", "recommendation_detail"):
            if not item.get(key):
                problems.append(f"{iid}: {key} がない")

        # 確かめ方の区別
        kinds = {r.get("kind") for r in item.get("repro", [])}
        for r in item.get("repro", []):
            if r.get("kind") not in REPRO_KINDS:
                problems.append(f"{iid}: 再現の種類 {r.get('kind')}")
            if not r.get("result"):
                problems.append(f"{iid}: 再現 {r.get('script')} の結果がない")
        reach = item.get("reachability", {}).get("status")
        if reach not in REACH_STATUS:
            problems.append(f"{iid}: 到達の確かめ方 {reach}")
        need = {"reached_legal_ops": "legal_ops", "constructed_state": "constructed", "helper_only": "helper", "modified_impl": "modified_impl"}
        via = item.get("reachability", {}).get("via_tests", [])
        for target in via:
            if target not in executed:
                problems.append(f"{iid}: 到達の確かめに使ったテスト {target} が実行の記録にない")
        if reach in need and need[reach] not in kinds and not (via and reach in ("constructed_state", "helper_only")):
            problems.append(f"{iid}: 到達の確かめ方が {reach} なのに、その種類の再現がない（既存テストで確かめたなら、構築盤面・補助関数として via_tests に書く）")
        if item.get("reachability_level") == "legal_play_confirmed" and "legal_ops" not in kinds:
            problems.append(f"{iid}: 合法な対戦で確かめたと書くのに、合法な操作列の再現がない")
        ran_test = any(t.get("run") for t in item.get("test_refs", []))
        for axis in AXES:
            if axes.get(axis, {}).get("confidence") == "verified_run" and not (kinds or ran_test):
                problems.append(f"{iid}: 軸 {axis} を実行で確かめたと書くのに、再現も実行したテストもない")
                break

        # 参照
        for ref in item.get("code_refs", []):
            if not IA._exists(ref["path"]):
                problems.append(f"{iid}: {ref['path']} がない")
            elif ref.get("symbol") and (p := IA.symbol_problem(ref["path"], ref["symbol"])):
                problems.append(f"{iid}: {p}")
        for ref in item.get("test_refs", []):
            if not IA._exists(ref["path"]):
                problems.append(f"{iid}: {ref['path']} がない")
                continue
            if p := IA._test_name_problem(ref["path"], ref.get("name", "")):
                problems.append(f"{iid}: {p}")
            if ref.get("run") and not _test_was_run(ref.get("name", ""), ref["path"], executed):
                problems.append(f"{iid}: 実行したと書くテスト {ref['path']} {ref.get('name')} が実行の記録にない")
            if not ref.get("run") and ref.get("result") not in (None, "", "未実行"):
                problems.append(f"{iid}: 読んだだけのテスト {ref.get('name')} に結果 {ref.get('result')} がある")
        for text in _texts({k: v for k, v in item.items() if k not in ("code_refs", "test_refs", "unconfirmed")}):
            for word in SCOPE_WORDS:
                if word in text and "範囲" not in text and not re.search(re.escape(word) + SCOPE_NEGATION, text):
                    problems.append(f"{iid}: 範囲を添えない「{word}」: {text[:60]}")

    problems += approval_problems(ledger)
    problems += source_addendum_problems(ledger, source)
    problems += followup_problems(ledger, source)
    if ledger.get("counts") != counts(ledger):
        problems.append("集計（counts）が台帳から数え直した値と違う（--write で書き直す）")
    problems += generated_block_problems(ledger, source)
    return problems


def approval_problems(ledger: dict) -> list[str]:
    problems: list[str] = []
    sup = ledger.get("approval_supplement")
    if not sup:
        return ["承認の補完（approval_supplement）がない"]
    if not sup.get("instruction"):
        problems.append("承認の補完: 指示の文がない")
    excluded = {r["id"]: r for r in load(CARDS).get("catalog_scope", {}).get("excluded_records", [])}
    for card in sup.get("cards", []):
        rec = excluded.get(card["id"])
        if rec is None:
            problems.append(f"承認の補完: {card['id']} が写しの対象外の記録にない")
        elif rec.get("name_ja") != card.get("name_ja"):
            problems.append(f"承認の補完: {card['id']} の名前 {card.get('name_ja')} が写しの {rec.get('name_ja')} と違う")
    if {c["id"] for c in sup.get("cards", [])} != set(excluded):
        problems.append("承認の補完: 3 枚の集合が写しの対象外の記録と違う")
    src_ids = {i["id"] for i in load(SOURCE)["items"]}
    for comp in sup.get("components", []):
        if comp.get("class") not in APPROVAL_COMPONENT_CLASSES:
            problems.append(f"承認の補完: {comp.get('id')} の区分 {comp.get('class')}")
        for iid in comp.get("item_ids", []):
            if iid not in src_ids:
                problems.append(f"承認の補完: {comp.get('id')} の項目 {iid} が元の一覧にない")
        if comp.get("class") == "quote_missing" and set(comp.get("cards", [])) - set(excluded):
            problems.append(f"承認の補完: {comp.get('id')} の承認の範囲が 3 枚の移管の外に及ぶ")
        if comp.get("class") == "quote_missing" and not comp.get("cards"):
            problems.append(f"承認の補完: {comp.get('id')} は承認の範囲（カード）を持たない")
    if not any(c.get("class") == "quote_missing" for c in sup.get("components", [])):
        problems.append("承認の補完: 引用が未収録の承認の区分がない")
    return problems


def source_addendum_problems(ledger: dict, source: dict) -> list[str]:
    ref = "docs/normalization-revalidation.json"
    problems = []
    rows = [a for a in source.get("addenda", []) if a.get("ref") == ref and a.get("kind") == "revalidation"]
    if len(rows) != 1:
        problems.append("元の一覧の addenda に、この再検証への参照（revalidation）がちょうど 1 つない")
    elif sorted(rows[0].get("item_ids", [])) != sorted(i["item_id"] for i in ledger["items"]):
        problems.append("元の一覧の addenda の項目と、再検証の項目が違う")
    sup = [a for a in source.get("addenda", []) if a.get("ref") == ref and a.get("kind") == "approval_supplement"]
    expected = sorted({iid for c in ledger.get("approval_supplement", {}).get("components", []) for iid in c.get("item_ids", [])})
    if len(sup) != 1 or sorted(sup[0].get("item_ids", [])) != expected:
        problems.append("元の一覧の addenda に、承認の補完（approval_supplement）への参照がちょうど 1 つない・項目が違う")
    return problems


FOLLOWUP_KINDS = ("fix", "followup", "assumption")


def followup_problems(ledger: dict, source: dict) -> list[str]:
    """後の追記（``addenda``。種類 ``fix``: 直したコミット・``followup``: 後の追加の検証・``assumption``: 後の版の実装上の仮定）。再検証の記録（項目・軸・分類・集計・基点）は
    書き換えず、後の結果への参照だけを足す。追記は集計に入れない。元の一覧の addenda に、同じ ID・同じ種類・同じ項目（``fix`` は同じコミット）の追記があること。"""
    problems: list[str] = []
    rows = ledger.get("addenda", [])
    ids = [a.get("id", "") for a in rows]
    for dup in sorted({x for x in ids if ids.count(x) > 1}):
        problems.append(f"追記の ID が重複: {dup}")
    mine = {i["item_id"] for i in ledger["items"]}
    source_rows = {a.get("id"): a for a in source.get("addenda", []) if a.get("kind") in FOLLOWUP_KINDS}
    for row in rows:
        where = row.get("id", "?")
        if not re.fullmatch(r"ADD-[A-Z0-9][A-Z0-9-]*[A-Z0-9]", where):
            problems.append(f"{where}: 追記の ID の形（ADD-英大文字のスラッグ）でない")
        if row.get("kind") not in FOLLOWUP_KINDS:
            problems.append(f"{where}: 追記の種類 {row.get('kind')} が {FOLLOWUP_KINDS} のどれでもない")
        for key in ("on", "ref", "summary"):
            if not row.get(key):
                problems.append(f"{where}: 追記に {key} がない")
        if row.get("ref") and not (ROOT / row["ref"]).exists():
            problems.append(f"{where}: 参照先 {row['ref']} がない")
        commits = row.get("commits")
        if row.get("kind") == "fix" and (not commits or not all(isinstance(c, str) and re.fullmatch(r"[0-9a-f]{40}", c) for c in commits)):
            problems.append(f"{where}: 直したコミット（40 桁）の並び commits がない")
        if not row.get("item_ids"):
            problems.append(f"{where}: 追記の項目がない")
        for iid in row.get("item_ids", []):
            if iid not in mine:
                problems.append(f"{where}: 項目 {iid} が再検証にない")
        other = source_rows.get(where)
        if (other is None or other.get("kind") != row.get("kind") or sorted(other.get("item_ids", [])) != sorted(row.get("item_ids", []))
                or other.get("commits") != commits):
            problems.append(f"{where}: 元の一覧の addenda に、同じ種類・同じ項目・同じコミットの追記がない")
    return problems


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 文書の生成した表
# ---------------------------------------------------------------------------------------------------------------------------------------------------

def _markers(name: str) -> tuple[str, str]:
    return (f"<!-- generated:{name} begin（scripts/check_normalization_revalidation.py --write が台帳から書く。手で直さない） -->",
            f"<!-- generated:{name} end -->")


_cell = IA._cell
_MARK = {"same": "同", "differs": "**違**", "conditional": "条件", "unknown": "?", "not_applicable": "—"}


def render_counts(ledger: dict) -> str:
    c = ledger["counts"]
    fmt = lambda d: "・".join(f"{k} {v}" for k, v in d.items())
    rows = [
        ("再検証した項目", c["items"]),
        ("範囲", fmt(c["items_by_scope"])),
        ("分類", fmt(c["items_by_classification"])),
        ("優先", fmt(c["items_by_priority"])),
        ("推奨対応（提案。採用していない）", fmt(c["items_by_recommendation"])),
        ("到達の確かめ方", fmt(c["items_by_reachability"])),
        ("軸ごとの「違う」の項目数", fmt(c["axes_differs"])),
        ("再現の種類（本数）", fmt(c["repro_by_kind"])),
        ("対応を付けた食い違い", c["discrepancies_mapped"]),
        ("項目が参照するテスト（実行した・読んだだけ）", f"{c['test_refs_run']}・{c['test_refs_read_only']}"),
        ("実行したテストの指定", c["tests_executed_targets"]),
    ]
    return "\n".join(["| 集計 | 値 |", "|---|---|"] + [f"| {a} | {_cell(b)} |" for a, b in rows])


def render_mapping(ledger: dict) -> str:
    head = ["| 食い違い | 種類 | 項目 | 主対象 | 備考 |", "|---|---|---|---|---|"]
    return "\n".join(head + [f"| `{m['disc_id']}` | {m['kind']} | {_cell(['`' + x + '`' for x in m['item_ids']])} | "
                             f"{'○' if m['in_primary'] else '—'} | {_cell(m.get('note', ''))} |" for m in ledger["discrepancy_mapping"]])


def render_results(ledger: dict) -> str:
    head = ["| 項目 | 範囲 | 分類 | 優先 | " + " | ".join(AXES[a].split("・")[0] for a in AXES) + " | 到達 | 推奨（提案） |",
            "|---|---|---|---|" + "---|" * len(AXES) + "---|---|"]
    order = {p: n for n, p in enumerate(PRIORITIES)}
    rows = []
    for i in sorted(ledger["items"], key=lambda i: (order[i["priority"]], i["classification"], i["item_id"])):
        marks = " | ".join(_MARK.get(i.get("axes", {}).get(a, {}).get("verdict"), "（なし）") for a in AXES)
        rows.append(f"| `{i['item_id']}` | {i['scope']} | {i['classification']} | {i['priority']} | {marks} | "
                    f"{i['reachability']['status']} | {i['recommendation']} |")
    return "\n".join(head + rows)


def render_addenda(ledger: dict) -> str:
    head = ["| 追記 | 日 | 種類 | 項目 | 直したコミット | 参照先 | 内容 |", "|---|---|---|---|---|---|---|"]
    return "\n".join(head + [f"| `{a['id']}` | {a['on']} | {a['kind']} | {'・'.join(f'`{i}`' for i in a['item_ids'])} | "
                             f"{'・'.join(f'`{c[:7]}`' for c in a.get('commits', [])) or '—'} | "
                             f"[{a['ref']}](../{a['ref']}) | {_cell(a['summary'])} |" for a in ledger.get("addenda", [])])


BLOCKS = {"counts": render_counts, "mapping": render_mapping, "results": render_results, "addenda": render_addenda}


def with_generated_blocks(text: str, ledger: dict) -> str:
    for name, render in BLOCKS.items():
        begin, end = _markers(name)
        pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
        if pattern.search(text):
            text = pattern.sub(lambda _: f"{begin}\n{render(ledger)}\n{end}", text)
    return text


def generated_block_problems(ledger: dict, source: dict) -> list[str]:
    if not DOCUMENT.exists():
        return [f"{DOCUMENT.name} がない"]
    text = DOCUMENT.read_text(encoding="utf-8")
    problems = [f"{DOCUMENT.name}: 生成する表 {n} の印がない" for n in BLOCKS if _markers(n)[0] not in text]
    known = {i["id"] for i in source["items"]} | {d["id"] for d in source["discrepancies"]}
    for ref in sorted(set(re.findall(r"`((?:IA|DISC)-[A-Z0-9][A-Z0-9-]*[A-Z0-9])`", text)) - known):
        problems.append(f"{DOCUMENT.name}: 本文の {ref} が元の一覧にない")
    if with_generated_blocks(text, ledger) != text:
        problems.append(f"{DOCUMENT.name}: 生成した表が台帳と違う（--write で書き直す）")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()
    ledger = load(LEDGER)
    if args.write:
        ledger["counts"] = counts(ledger)
        LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        DOCUMENT.write_text(with_generated_blocks(DOCUMENT.read_text(encoding="utf-8"), ledger), encoding="utf-8")
        return 0
    problems = check(ledger)
    for p in problems:
        print(p)
    print(f"problems={len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
