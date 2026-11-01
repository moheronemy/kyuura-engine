"""研究の対応表（kyuura_engine/data/research_links.json）を、kyuura の研究の基準のコミットの記録と照らす（v0.18e）。

kyuura（https://github.com/moheronemy/kyuura）の ``research_commit`` の記録を ``git show`` で読み（作業ツリー・履歴は変えない）、次を確かめる。

1. 論点（UQ-）: 対応表に書いた論点がすべてあり、どれも UNRESOLVED。kyuura の論点はどれも対応表のどこかにある。
2. エンジンの未解決の一覧（``engine_unresolved_index``）: 停止コードの集合が対応表と同じで、コードごとの論点と処理（issue・out_of_scope）が同じ。
   kyuura にまだ記録がないとした停止コード（``not_in_kyuura``。v0.21）は比べる集合から除き、kyuura に記録ができていたら知らせる。v0.31 で
   コードを付けた、kyuura の一覧ではコードのない行（``kyuura_index_engine_key``）は、その行の論点・処理と照らす。
3. 分類の違い（``classification_differences``）: kyuura の裁定（CR-）があり、分類（status）が対応表と同じで、エンジンの id を参照している。
4. 最新の説明（LD-）: 対応表の id があり、カード・種類・位置が合い、文面がエンジンの登録の ``play_text_ja`` と同じ。印刷の文面と同じ最新の説明を
   kyuura が照合の記録（CC-）に書いたもの（``recorded_in_card_checks``）は、照合した欄の文面（またはデータの誤りの資料の値）が ``play_text_ja`` と
   同じで、ページが登録の出典と同じ。照合の記録はあるがワザの文面を照合していないもの（``card_checks_without_text``）は、その欄が照合していない欄に
   ある。kyuura の記録のない登録・登録のない kyuura の記録の一覧が、実際と同じ（v0.19 の準備。2026-10-15）。kyuura のエラッタの記録
   （ERR-・TXT-・RUL-）を処理に使う文面にした登録（``errata_text``。v0.30）は、登録の出典がその id で、文面が記録の notes の引用と同じで、
   記録の ``cards`` がそのカードを挙げるか、記録の範囲としての当てはめ（``errata_scope``。当てはめる文と処理に使う文面が記録の notes にあり、
   対象の印刷の文面が研究の基準のコミットで書いた文面と同じで、記録が挙げるカードに同じ印刷の文面のワザがある）に挙げてある（v0.31 から、
   文面は記録の play_text（最後の出典の注を除く）でもよい）。kyuura の日英の違いの記録（``data/curation/card_differences.json``）が引く
   最新の説明を処理に使う文面にした登録（``difference_text``。v0.31）は、出典がその記録で、文面が確度「確実」の記録の「」の引用の 1 つと同じ。
5. 照合の記録（CC-）: id があり、カードが合う。kyuura がエンジンの照合の記録を取り込んだ記録（``import_provenance``）は、エンジンの
   ``card_verification.json`` の同じカードの記録とページ・PDF のページ・原典の確認日が同じ。取り込み（``engine_import_id``）が kyuura にある。
6. カードデータ: 研究の基準のコミットの ``data/cards.json`` と、エンジンの写し（``KYUURA_COMMIT``）を、写しの項目で比べ、違いが対応表の
   ``card_data_differences`` に挙げたものだけ。
7. kyuura データの採用（2026-10-15 からの方針。``kyuura_engine/data/card_sources.json``。docs/card-data-policy.md）: 処理に使う文面を
   kyuura の印刷の文面にした登録（``adopted_printed_text``）は、文面が研究の基準のコミットの ``data/cards.json`` と同じで、その対象の
   最新の説明（LD-）・データの誤りの記録（CC- の ``data_error``）がない。採用の記録の ``kyuura_records`` は、研究の基準のコミットで
   そのカードを指す kyuura の記録（LD-・CC-・CR-・UQ-・エラッタ。エラッタの範囲として当てはめた ``errata_scope`` の記録を含む）とちょうど
   同じ（既存の記録を探して確かめたこと）。根拠にしたエラッタはそのカードを指す（``errata_scope`` に挙げたものを含む）。CC- のデータの誤りの
   欄は、採用の記録の論点（``issues``）に挙げる。過去の原典照合の記録のあるカードに、照合の記録に文面のない登録の根拠（``play_text``）を
   書いた記録（``basis: guidebook_record``。v0.30）も同じに確かめる。

v0.70（docs/non-pack-effect-reuse-v0.70.md 3 章）: 6 のカードデータの比べ方で、エンジンが写しに当てはめた利用者が示した訂正（``engine_user_corrections``。PR1-069 の名前）だけは、
   対応表・写し・写しの作り直しの表が同じ訂正で、研究の基準のコミットの値が訂正の前の値のときに、その欄を訂正のあとの値にして比べる。

v0.69（docs/equivalent-non-pack-cards-v0.69.md 4 章・7 章）: 利用者が示した訂正（``user_corrected_text``）は kyuura の台帳（data/curation/card_corrections.json）の
   根拠 ``user_provided`` の記録に結ぶ。トレーナーの最新の説明（LD-…-TRAINER）は ``registered_trainers`` に結び、登録の処理に使う文面と出典のページと照らす（v0.126: 登録していないトレーナーの説明は ``trainer_records_not_registered``）。
   拡張パック以外の商品の同じカード（effects.EQUIVALENT_CARDS）の登録（``equivalent_registrations``）は、元のカードの登録と文面・出典が同じで、元のカードの登録が
   ほかの区分にあり、研究の基準のコミットで同じカードの組（same_card_group）にあって印刷の文面が同じ（4g）。

v0.97（docs/unown-research-idfnj-v0.97.md 3 章）: kyuura が調査で立てた・事例を加えた論点のうち、kyuura の未解決の一覧（``engine_unresolved_index``。取り込んだ版までの
   項目）に行のない停止コード（``kyuura_disposition`` が ``issue_not_in_index``）は、kyuura の論点があり、その停止コードを結んだ事例（下の 9）があり、一覧にコードがない
   ことを確かめて、停止コードの集合の比べから除く（kyuura に記録がない ``not_in_kyuura`` とは別）。9. kyuura の論点の事例のうちエンジンの裁定 id のないもの
   （``kyuura_cases_without_engine_ruling``）は、研究の基準のコミットのそのような事例のすべてと同じで、エンジンの扱い（停止コード・コードのない問い・登録していない）が
   対応表・登録表と合う。

v0.123（docs/arcanine-name-migration-v0.123.md 2 章）: 9 のエンジンの扱いに ``requires_unregistered`` を加えた。登録したカードの事例で、その場面が同じ論点の事例の別のカード
   （エンジンに登録していないカード。ちえくらべ・フラッシュ・とりかえっこプリーズ・ナッシー[Exeggutor]）があるときだけ起こるもの。挙げたカードがどれも登録されておらず、同じ論点の事例の
   カードで、事例のカードそのものではないことを確かめる。

kyuura のデータの写しは作らない（id と、照らした結果だけを使う）。問題があれば終了コード 1。

    python3 scripts/check_research_links.py --kyuura ../kyuura
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
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
    found |= {v["kyuura_issue"] for v in links["codeless_questions"].values() if v["kyuura_issue"]}  # v0.31: kyuura に論点がない問いは None
    for section in ("unresolved_without_code", "deferred_card_questions", "implementation_assumptions_with_issue"):
        found |= {v["kyuura_issue"] for v in links[section]}
    found |= {v["kyuura_issue"] for v in (links.get("kyuura_cases_without_engine_ruling") or {}).get("cases", [])}  # v0.97
    return found


ISSUE_NOT_IN_INDEX = "issue_not_in_index"  # v0.97: kyuura に論点はあるが、kyuura の未解決の一覧にこのコードの行がない停止コード


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
    # v0.31: エンジンがコードを付けた、kyuura の一覧ではコードのない行（kyuura_index_engine_key。T27 など）。その行の論点・処理と照らし、比べる集合から除く
    keyed = {code: v["kyuura_index_engine_key"] for code, v in links["stop_codes"].items() if v.get("kyuura_index_engine_key")}
    codeless_rows = {x["engine_key"]: x for x in rulings["engine_unresolved_index"] if not x.get("stop_code")}
    for code, key in sorted(keyed.items()):
        row = codeless_rows.get(key)
        entry = links["stop_codes"][code]
        if code in index:
            problems.append(f"コードを付けた {code}（kyuura の {key}）が、kyuura の未解決の一覧にコードつきである（対応表を直す）")
        elif row is None:
            problems.append(f"{code}: kyuura の未解決の一覧に、コードのない行 {key} がない")
        elif (row.get("kyuura_issue"), row.get("disposition")) != (entry["kyuura_issue"], entry["kyuura_disposition"]):
            problems.append(f"{code}: kyuura の {key} は {row.get('kyuura_issue')}・{row.get('disposition')}、対応表は "
                            f"{entry['kyuura_issue']}・{entry['kyuura_disposition']}")
    pending |= set(keyed)
    # v0.97: kyuura に論点はあるが、kyuura の未解決の一覧（取り込んだ版までの項目）にこのコードの行がない停止コード（issue_not_in_index）。論点があり、その停止コードを
    # 結んだ kyuura の事例（9 の kyuura_cases_without_engine_ruling）があり、一覧にコードがないことを確かめて、比べる集合から除く
    linked_cases = (links.get("kyuura_cases_without_engine_ruling") or {}).get("cases", [])
    unindexed = {code: v for code, v in links["stop_codes"].items() if v["kyuura_disposition"] == ISSUE_NOT_IN_INDEX}
    for code, entry in sorted(unindexed.items()):
        if code in index:
            problems.append(f"論点の一覧に行がないとした停止コード {code} が、kyuura の未解決の一覧にある（対応表を直す）")
        if entry["kyuura_issue"] not in issues:
            problems.append(f"{code}: 論点の一覧に行がないとした停止コードの論点 {entry['kyuura_issue']} が kyuura にない")
        if not any(code in (case.get("engine") or {}).get("stop_codes", ()) and case.get("kyuura_issue") == entry["kyuura_issue"] for case in linked_cases):
            problems.append(f"{code}: 論点 {entry['kyuura_issue']} の、この停止コードに結んだ kyuura の事例（kyuura_cases_without_engine_ruling）がない")
    pending |= set(unindexed)
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
    ld_by_target = {f"{x['card_id']}/{x['target']['kind']}/{x['target']['index']}": x["id"] for x in descriptions if x["target"]["kind"] != "trainer"}
    # v0.69: kyuura はトレーナーの最新の説明も記録した（LD-…-TRAINER。target に位置がない）。登録の TrainerEntry の play_text_ja・出典（ページ）と照らす
    trainer_ld = {x["card_id"]: x for x in descriptions if x["target"]["kind"] == "trainer"}
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
    registry_ = E.DEFAULT_EFFECTS if registry is None else registry
    trainers_listed = section.get("registered_trainers", {})
    # v0.126（docs/flash-faceup-deck-v0.126.md 2.4 節）: 登録していないトレーナーの最新の説明（kyuura 57d01f4 のとりかえっこプリーズ）は trainer_records_not_registered に挙げる。
    # 登録したトレーナーの説明と重ならず、合わせて kyuura のトレーナーの最新の説明のすべてと同じ
    trainers_not_registered = section.get("trainer_records_not_registered", {})
    if set(trainers_listed) & set(trainers_not_registered):
        problems.append(f"トレーナーの最新の説明が、登録したものと登録していないものの両方にある: {sorted(set(trainers_listed) & set(trainers_not_registered))}")
    if set(trainers_listed) | set(trainers_not_registered) != set(trainer_ld):
        problems.append(f"トレーナーの最新の説明（LD-…-TRAINER）の一覧が違う: kyuura だけ {sorted(set(trainer_ld) - set(trainers_listed) - set(trainers_not_registered))}、"
                        f"対応表だけ {sorted((set(trainers_listed) | set(trainers_not_registered)) - set(trainer_ld))}")
    for card, ld_id in trainers_not_registered.items():
        record = trainer_ld.get(card)
        if record is None or record["id"] != ld_id:
            problems.append(f"{card}: 登録していないトレーナーの最新の説明 {ld_id} が kyuura にない、またはカードが違う")
        elif registry_.trainer_entry(card) is not None:
            problems.append(f"{card}: トレーナーの最新の説明 {ld_id} のカードは登録されている（registered_trainers に挙げる）")
    for card, ld_id in trainers_listed.items():
        record = trainer_ld.get(card)
        entry = registry_.trainer_entry(card)
        if record is None or record["id"] != ld_id:
            problems.append(f"{card}: トレーナーの最新の説明 {ld_id} が kyuura にない、またはカードが違う")
            continue
        if entry is None:
            problems.append(f"{card}: トレーナーの最新の説明 {ld_id} のカードが登録されていない")
            continue
        if record["latest_description"]["text_ja"] != entry.play_text_ja:
            problems.append(f"{card}: 登録の処理に使う文面が kyuura の {ld_id} と違う")
        # v0.126: 出典は LD- のページ（過去の原典照合で登録したもの）か、LD- の id（kyuura データの採用で、最新の説明を根拠にしたもの。ワザ・特殊能力と同じ。フラッシュ ES2-035）
        if entry.source != f"P43 p.{record['latest_description']['page']}" and entry.source != ld_id:
            problems.append(f"{card}: 出典 {entry.source} が kyuura の {ld_id} のページ（p.{record['latest_description']['page']}）と違う")
    adopted_printed = set(section.get("adopted_printed_text", []))
    errata_text = section.get("errata_text", {})
    difference_text = section.get("difference_text", {})
    user_corrected = section.get("user_corrected_text", {})  # v0.68: 利用者が示した訂正（kyuura の照合の記録・最新の説明ではない。v0.69 から kyuura の台帳の記録）
    simplified = section.get("engine_simplified_text", {})  # v0.68: エンジンの簡略化した仕様（公式の裁定・エラッタではない）
    user_simplified = section.get("user_simplified_text", {})  # v0.127: 利用者が指定した簡略ルール（公式の裁定・エラッタ・エンジンの仕様の判断ではない）
    user_references = section.get("user_specified_references", {})  # v0.129: 利用者が指定した参照値（処理に使う文面は印刷のまま。公式の裁定・最新の説明・印刷の訂正ではない）
    user_rules = section.get("user_specified_rules", {})  # v0.130: 利用者が指定した、説明が書かない処理の規則（処理に使う文面は最新の説明のまま。公式の裁定ではない）
    user_names = section.get("user_specified_names", {})  # v0.131: 利用者が指定した名前の扱い（日英併記の名前の判定。文面の区分ではない。公式の裁定・転記の訂正ではない）
    equivalent = section.get("equivalent_registrations", {})  # v0.69: 登録したカードと処理に使う欄が同じカードの登録 → 元のカードの登録
    reprinted = section.get("reprint_registrations", {})  # v0.71: 再録のカードの、元のカードの記録の文面を処理に使う登録 → 元のカードの登録
    in_checks = (set(section.get("recorded_in_card_checks", {})) | set(section.get("card_checks_without_text", {})) | adopted_printed
                 | set(errata_text) | set(difference_text) | set(user_corrected) | set(simplified) | set(user_simplified) | set(equivalent) | set(reprinted))
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
    if set(errata_text) & (accounted | set(section["registered_without_kyuura_record"]) | adopted_printed):
        problems.append("errata_text の登録が、ほかの区分にも入っている")
    if set(difference_text) & (accounted | set(section["registered_without_kyuura_record"]) | adopted_printed | set(errata_text)):
        problems.append("difference_text の登録が、ほかの区分にも入っている")

    # 4d. kyuura のエラッタの記録を処理に使う文面にした登録（v0.30）
    errata = git_show(kyuura, commit, "data/rule_history.json")["errata"]
    errata_by_id = {x["id"]: x for x in errata}

    def printed_at_research(target: str) -> str | None:
        card, kind, index = target.split("/")
        items = ((research_cards.get(card) or {}).get("pokemon") or {}).get("attacks" if kind == "attack" else "powers") or []
        return (items[int(index)].get("text") or {}).get("ja") if int(index) < len(items) else None

    # v0.73（docs/search-recovery-trainers-v0.73.md 4 章）: エラッタの記録の ``cards`` がカードを pcg-search.com の id で挙げるもの（ERR-SUPER-ENERGY-RETRIEVAL の 1stp009）の、
    # エンジンのカード id との対応（``errata_card_ids``。カード id → {record, record_card, page}）。対応は、記録の cards がその id を挙げ、研究の基準のコミットの
    # data/cards.json でそのカードの source_ids.pcg_search がその id を持ち、ほかのカードは持たないときだけ認める（名前・カード id の形で推測しない）
    errata_card_ids = section.get("errata_card_ids", {})
    mapped_errata: dict[str, set[str]] = {}
    for card, item in errata_card_ids.items():
        where = f"errata_card_ids {card}"
        record = errata_by_id.get(item.get("record"))
        old_id = item.get("record_card")
        holders = sorted(c for c, x in research_cards.items() if old_id in ((x.get("source_ids") or {}).get("pcg_search") or []))
        if record is None:
            problems.append(f"{where}: エラッタの記録 {item.get('record')} が研究の基準のコミットにない")
            continue
        found_here = []
        if old_id not in (record.get("cards") or []):
            found_here.append(f"{where}: エラッタの記録 {record['id']} の cards が {old_id} を挙げていない")
        if holders != [card]:
            found_here.append(f"{where}: pcg-search.com の id {old_id} を持つ kyuura のカードが {holders}（{card} だけのはず）")
        if not str(item.get("page") or "").startswith("p."):
            found_here.append(f"{where}: 引用のページ（page）がない")
        problems += found_here
        if not found_here:
            mapped_errata.setdefault(card, set()).add(record["id"])

    scoped: dict[str, str] = {}
    for i, scope in enumerate(section.get("errata_scope", [])):
        where = f"errata_scope {i}（{scope.get('record')}）"
        record = errata_by_id.get(scope.get("record"))
        if record is None:
            problems.append(f"{where}: エラッタの記録が研究の基準のコミットにない")
            continue
        notes = "\n".join(record.get("notes") or [])
        for quote in ("scope_quote", "play_text_quote"):
            if not scope.get(quote) or scope[quote] not in notes:
                problems.append(f"{where}: {quote} が記録の notes にない（記録の文を引用する）")
        listed = record.get("cards") or []
        anchors = [c for c in listed for a in ((research_cards.get(c) or {}).get("pokemon") or {}).get("attacks") or []
                   if (a.get("text") or {}).get("ja") == scope.get("printed_text")]
        if not anchors:
            problems.append(f"{where}: 記録が挙げるカード {listed} に、印刷の文面 {scope.get('printed_text')!r} のワザがない")
        for target in scope.get("targets") or []:
            scoped[target] = scope["record"]
            if target.split("/")[0] in listed:
                problems.append(f"{where}: {target} のカードは記録の cards にある（errata_scope に書かない）")
            if printed_at_research(target) != scope.get("printed_text"):
                problems.append(f"{where}: {target} の印刷の文面が、研究の基準のコミットで printed_text と違う")
            if errata_text.get(target) != scope["record"]:
                problems.append(f"{where}: {target} が errata_text に {scope['record']} として挙げていない")
            if target in texts and texts[target][0] != scope.get("play_text_quote"):
                problems.append(f"{where}: {target} の登録の処理に使う文面が play_text_quote と違う")
    for target, rid in errata_text.items():
        record = errata_by_id.get(rid)
        if record is None:
            problems.append(f"{target}: エラッタの記録 {rid} が研究の基準のコミットにない")
            continue
        if target.endswith("/trainer"):
            # v0.73: トレーナーの処理に使う文面をエラッタにした登録（超エネルギー回収）。文面が、記録の notes の、対応のページ（errata_card_ids の page）を書いた 1 つの
            # note に「」でちょうど引用されていること（文面の一部・別のページの引用では通さない）・出典が記録の id・登録の照合した文面が研究の基準のコミットの印刷の文面と
            # 同じ・記録の cards がこのカード（カード id か、errata_card_ids の対応）を挙げること
            card = target.split("/")[0]
            entry = registry_.trainer_entry(card)
            item = errata_card_ids.get(card) or {}
            if entry is None:
                problems.append(f"{target}: errata_text の登録が、トレーナーの登録にない")
                continue
            if entry.source != rid:
                problems.append(f"{target}: 出典 {entry.source} が、根拠のエラッタ {rid} と違う")
            if not any(f"「{entry.play_text_ja}」" in note and item.get("page") and item["page"] in note for note in record.get("notes") or []):
                problems.append(f"{target}: 処理に使う文面が、エラッタの記録 {rid} の notes の {item.get('page')} の引用（「」）にない")
            printed = (((research_cards.get(card) or {}).get("trainer") or {}).get("text") or {}).get("ja")
            if entry.text_ja != printed:
                problems.append(f"{target}: 登録の照合した文面が、研究の基準のコミットの印刷の文面と違う")
            if card not in (record.get("cards") or []) and rid not in mapped_errata.get(card, set()):
                problems.append(f"{target}: エラッタの記録 {rid} がこのカードを挙げていない（pcg-search.com の id で挙げるなら errata_card_ids に書く）")
            continue
        if target not in texts:
            problems.append(f"{target}: errata_text の登録に、処理に使う文面がない")
            continue
        text, source = texts[target]
        if source != rid:
            problems.append(f"{target}: 出典 {source} が、根拠のエラッタ {rid} と違う")
        # 記録の notes の引用か、記録の play_text（v0.31。TXT-CHARIZARD。最後の「（…の最新の説明）」の出典の注を除いた文面）
        quoted = "\n".join(record.get("notes") or []) + "\n" + re.sub(r"（[^（）]*）$", "", record.get("play_text") or "")
        if text not in quoted:
            problems.append(f"{target}: 処理に使う文面が、エラッタの記録 {rid} の notes の引用・play_text にない")
        if target.split("/")[0] not in (record.get("cards") or []) and scoped.get(target) != rid:
            problems.append(f"{target}: エラッタの記録 {rid} がこのカードを挙げていない（記録の範囲として当てはめるなら errata_scope に書く）")
        if target in ld_by_target:
            problems.append(f"{target}: kyuura に最新の説明の記録 {ld_by_target[target]} がある（registered に移し、最新の説明にしたがう）")

    # 4e. kyuura の日英の違いの記録（data/curation/card_differences.json）が引く最新の説明を処理に使う文面にした登録（v0.31。ピッピの
    # 「ゆびをふる」）。出典は「kyuura data/curation/card_differences.json#カード id」で、文面が、確度「確実」のその記録の ja の「」の引用の 1 つと同じ
    if difference_text:
        differences = git_show(kyuura, commit, "data/curation/card_differences.json")
        for target, basis in difference_text.items():
            card = target.split("/")[0]
            if basis != f"kyuura data/curation/card_differences.json#{card}":
                problems.append(f"{target}: difference_text の根拠 {basis!r} が、このカードの記録を指していない")
            if target not in texts:
                problems.append(f"{target}: difference_text の登録に、処理に使う文面がない")
                continue
            text, source = texts[target]
            if source != basis:
                problems.append(f"{target}: 出典 {source} が、根拠 {basis} と違う")
            entries = [e for e in differences.get(card) or [] if e.get("confidence") == "確実"]
            quotes = {q for e in entries for q in re.findall(r"「((?:[^「」]|「[^「」]*」)*)」", e.get("ja") or "")}
            if text not in quotes:
                problems.append(f"{target}: 処理に使う文面が、kyuura の card_differences の {card} の記録（確度: 確実）の引用にない")
            if target in ld_by_target:
                problems.append(f"{target}: kyuura に最新の説明の記録 {ld_by_target[target]} がある（registered に移し、最新の説明にしたがう）")

    # 4f. v0.68（docs/final-pmcg-cards-v0.68.md 2 章・4 章）: 利用者が示した修正を当てはめた写しの説明文・エンジンの簡略化した仕様を処理に使う文面にした登録
    others = accounted | set(section["registered_without_kyuura_record"]) | adopted_printed | set(errata_text) | set(difference_text)
    if (set(user_corrected) | set(simplified)) & others or set(user_corrected) & set(simplified):
        problems.append("user_corrected_text・engine_simplified_text の登録が、ほかの区分にも入っている")
    # v0.69: 利用者が示した訂正は、kyuura が data/cards.json に当てはめた（台帳 data/curation/card_corrections.json の根拠 user_provided の記録）。根拠は台帳の記録の id で、
    # 研究の基準のコミットの台帳・カードの記録の corrections に同じ記録があり、文面が訂正のあとの値と同じ・訂正の前の値と違う・kyuura が画像を見ていないことを確かめる
    ledger = {x["id"]: x for x in git_show(kyuura, commit, "data/curation/card_corrections.json")["corrections"]}
    for target, basis in user_corrected.items():
        card, kind, index = target.split("/")
        path = f"pokemon.{'attacks' if kind == 'attack' else 'powers'}[{index}].text.ja"
        prefix = "kyuura data/curation/card_corrections.json#"
        correction = ledger.get(basis.removeprefix(prefix)) if basis.startswith(prefix) else None
        if correction is None or (correction.get("card_id"), correction.get("field"), correction.get("basis")) != (card, path, "user_provided"):
            problems.append(f"{target}: user_corrected_text の根拠 {basis!r} が、研究の基準のコミットの台帳のこの欄の利用者が示した訂正（user_provided）でない")
            continue
        if correction.get("kyuura_saw_image") is not False:
            problems.append(f"{target}: 台帳の訂正 {correction['id']} が、kyuura が画像を見たと書いている（利用者が示した訂正として扱えない）")
        if correction["id"] not in {x.get("id") for x in (research_cards.get(card) or {}).get("corrections") or ()}:
            problems.append(f"{target}: 研究の基準のコミットのカードの記録の corrections に {correction['id']} がない")
        if target not in texts or texts[target][0] != correction["after"]:
            problems.append(f"{target}: 処理に使う文面が、利用者が示した訂正のあとの文面と違う")
        if printed_at_research(target) != correction["after"] or correction["before"] == correction["after"]:
            problems.append(f"{target}: kyuura の研究の基準のコミットの文面が、訂正のあとの値でない")
        if target in ld_by_target:
            problems.append(f"{target}: kyuura に最新の説明の記録 {ld_by_target[target]} がある（registered に移し、最新の説明にしたがう）")
    for target, basis in simplified.items():
        if target not in texts or texts[target][1] != basis:
            problems.append(f"{target}: engine_simplified_text の登録の出典が {basis} でない")
        if printed_at_research(target) is None:
            problems.append(f"{target}: engine_simplified_text の対象に、研究の基準のコミットの印刷の文面がない")
        if target in ld_by_target:
            problems.append(f"{target}: kyuura に最新の説明の記録 {ld_by_target[target]} がある（registered に移し、最新の説明にしたがう）")
    # 4f'. v0.127（docs/deferred-shortage-user-promos-v0.127.md 4 章）: 利用者が指定した簡略ルールを処理に使う文面にした登録。区分は対象ごとの記録（effects.USER_SIMPLIFICATIONS）と
    # ちょうど同じで、出典は USER_SIMPLIFICATION_SOURCE。記録の印刷の文面が研究の基準のコミットの印刷の文面と同じ（kyuura の文面を書き換えていない）・処理に使う文面が記録と同じで印刷の
    # 文面と違う・kyuura に最新の説明がない（あれば最新の説明にしたがうべきなので、黙って簡略化を優先しない）。ほかの区分（エンジンの簡略化した仕様をふくむ）に入れない
    if (set(user_simplified) & (others | set(user_corrected) | set(simplified))) or set(user_simplified) != set(getattr(E, "USER_SIMPLIFICATIONS", {})):
        problems.append(f"user_simplified_text の一覧が、利用者の簡略ルールの記録と違うか、ほかの区分にも入っている: 対応表 {sorted(user_simplified)}")
    for target, basis in user_simplified.items():
        record = getattr(E, "USER_SIMPLIFICATIONS", {}).get(target)
        if basis != getattr(E, "USER_SIMPLIFICATION_SOURCE", None) or record is None:
            problems.append(f"{target}: user_simplified_text の根拠 {basis!r} が、利用者の簡略ルールの出典・記録でない")
            continue
        if target not in texts or texts[target] != (record.play_text, basis):
            problems.append(f"{target}: user_simplified_text の登録の処理に使う文面・出典が、利用者の簡略ルールの記録と違う")
        if printed_at_research(target) != record.printed_text or record.printed_text == record.play_text:
            problems.append(f"{target}: 利用者の簡略ルールの記録の印刷の文面が、研究の基準のコミットの印刷の文面と違う（または処理に使う文面と同じ）")
        if target in ld_by_target:
            problems.append(f"{target}: kyuura に最新の説明の記録 {ld_by_target[target]} がある（利用者の簡略ルールより先に確かめる）")
    # 4f''. v0.129（docs/blaines-quiz-heights-v0.129.md 3 章）: 利用者が指定した参照値（カツラのクイズ その1の正解に公式図鑑の種族の身長を採る）。処理に使う文面の区分ではない（文面は
    # 印刷のまま）ので、印刷の文面の採用（adopted_printed_text）・利用者の簡略ルール（user_simplified_text）と別に挙げる。一覧は対象ごとの記録（effects.USER_SPECIFIED_REFERENCES）と
    # ちょうど同じで、出典は USER_SPECIFIED_REFERENCE_SOURCE。記録の印刷の文面が研究の基準のコミットの印刷の文面・登録の処理に使う文面と同じ、kyuura に最新の説明がない
    if set(user_references) != set(getattr(E, "USER_SPECIFIED_REFERENCES", {})) or set(user_references) & (set(user_simplified) | adopted_printed):
        problems.append(f"user_specified_references の一覧が、利用者が指定した参照値の記録と違うか、文面の区分にも入っている: 対応表 {sorted(user_references)}")
    for target, basis in user_references.items():
        record = getattr(E, "USER_SPECIFIED_REFERENCES", {}).get(target)
        if basis != getattr(E, "USER_SPECIFIED_REFERENCE_SOURCE", None) or record is None:
            problems.append(f"{target}: user_specified_references の根拠 {basis!r} が、利用者が指定した参照値の出典・記録でない")
            continue
        card, _, kind = target.partition("/")
        entry = registry_.trainer_entry(card) if kind == "trainer" else None
        printed = (((research_cards.get(card) or {}).get("trainer") or {}).get("text") or {}).get("ja") if kind == "trainer" else None
        if entry is None or not (entry.text_ja == entry.play_text_ja == record.printed_text == printed):
            problems.append(f"{target}: 利用者が指定した参照値の記録の印刷の文面が、研究の基準のコミットの印刷の文面・登録の処理に使う文面と同じではない")
        if card in trainer_ld:
            problems.append(f"{target}: kyuura に最新の説明の記録 {trainer_ld[card]['id']} がある（利用者が指定した参照値より先に確かめる）")

    # 4f-3. v0.130（docs/trade-please-ownership-v0.130.md 3 章）: 利用者が指定した、説明が書かない処理の規則（とりかえっこプリーズで交換したカードの対戦の中の所有者）。処理に使う
    # 文面の区分ではない（文面は登録の区分のまま。PR1-027 は registered_trainers の最新の説明）ので、文面の区分と別に挙げる。一覧は対象ごとの記録（effects.USER_SPECIFIED_RULES）と
    # ちょうど同じで、出典は USER_SPECIFIED_RULE_SOURCE。記録の印刷の文面が研究の基準のコミットの印刷の文面と同じ、処理に使う文面が登録の処理に使う文面と同じで、kyuura の
    # 最新の説明があればその文面（規則は文面を書き換えない）。解決済みにしない論点が、研究の基準のコミットで UNRESOLVED のまま
    if set(user_rules) != set(getattr(E, "USER_SPECIFIED_RULES", {})) or set(user_rules) & (set(user_simplified) | set(user_references)):
        problems.append(f"user_specified_rules の一覧が、利用者が指定した規則の記録と違うか、簡略ルール・参照値の区分にも入っている: 対応表 {sorted(user_rules)}")
    for target, basis in user_rules.items():
        record = getattr(E, "USER_SPECIFIED_RULES", {}).get(target)
        # v0.132: 出典は記録ごと（v0.130 の所有者の規則は USER_SPECIFIED_RULE_SOURCE、v0.132 の［ちえくらべ］の規則はその版の文書）
        if record is None or basis != getattr(record, "source", getattr(E, "USER_SPECIFIED_RULE_SOURCE", None)):
            problems.append(f"{target}: user_specified_rules の根拠 {basis!r} が、利用者が指定した規則の出典・記録でない")
            continue
        card, _, kind = target.partition("/")
        latest = None
        if kind == "trainer":
            entry = registry_.trainer_entry(card)
            printed = (((research_cards.get(card) or {}).get("trainer") or {}).get("text") or {}).get("ja")
            latest = trainer_ld.get(card)
        elif kind.startswith("power/") and kind.split("/", 1)[1].isdigit():
            # v0.132: 特殊能力の対象（``<カード id>/power/<位置>``）。kyuura の最新の説明があれば、規則より先に確かめる（文面の区分は登録のまま）
            index = int(kind.split("/", 1)[1])
            entry = registry_.power_entry(card, index)
            powers = (((research_cards.get(card) or {}).get("pokemon") or {}).get("powers") or [])
            printed = ((powers[index].get("text") or {}).get("ja")) if index < len(powers) else None
            if f"{card}/power/{index}" in ld_by_target:
                problems.append(f"{target}: kyuura に最新の説明の記録 {ld_by_target[f'{card}/power/{index}']} がある（利用者が指定した規則より先に確かめる）")
        elif kind.startswith("attack/") and kind.split("/", 1)[1].isdigit():
            # v0.133: ワザの対象（``<カード id>/attack/<位置>``。ひかるバンギラスの足りないときの処理・宣言の条件・順番）。kyuura の最新の説明があれば、規則より先に確かめる
            index = int(kind.split("/", 1)[1])
            entry = registry_.attack_entry(card, index)
            attacks = (((research_cards.get(card) or {}).get("pokemon") or {}).get("attacks") or [])
            printed = ((attacks[index].get("text") or {}).get("ja")) if index < len(attacks) else None
            if f"{card}/attack/{index}" in ld_by_target:
                problems.append(f"{target}: kyuura に最新の説明の記録 {ld_by_target[f'{card}/attack/{index}']} がある（利用者が指定した規則より先に確かめる）")
        else:
            entry, printed = None, None
        if entry is None or not (entry.text_ja == record.printed_text == printed and entry.play_text_ja == record.play_text):
            problems.append(f"{target}: 利用者が指定した規則の記録の文面が、研究の基準のコミットの印刷の文面・登録の処理に使う文面と同じではない")
        elif latest is not None and (entry.source != latest["id"] or entry.play_text_ja != (latest.get("latest_description") or {}).get("text_ja")):
            problems.append(f"{target}: 最新の説明 {latest['id']} があるのに、処理に使う文面がその文面ではない（規則は文面を書き換えない）")
        for issue_id in getattr(record, "issues", (record.kyuura_issue,)):
            issue = issues.get(issue_id)
            if issue is None or issue.get("status") != "UNRESOLVED":
                problems.append(f"{target}: 解決済みにしない論点 {issue_id} が、研究の基準のコミットで UNRESOLVED ではない")

    # 4f-4. v0.131（docs/exeggutor-bilingual-names-v0.131.md 3 章）: 利用者が指定した名前の扱い（ナッシー[Exeggutor] の英語の併記を翻訳の表示とし、名前・進化元・ワザ名の判定に日本語の部分を
    # 使う）。処理に使う文面の区分ではない（ワザの文面は adopted_printed_text の印刷の文面のまま）ので、文面の区分と別に挙げる。一覧は対象ごとの記録（effects.USER_SPECIFIED_NAMES）とちょうど同じで、
    # 出典は USER_SPECIFIED_NAME_SOURCE。記録の欄ごとの写しの値が研究の基準のコミットの値（kyuura の値を書き換えていない）、カードが登録されている、ほかの利用者の指定の区分と重ならない、
    # 解決済みにしない論点が研究の基準のコミットで UNRESOLVED のまま
    if set(user_names) != set(getattr(E, "USER_SPECIFIED_NAMES", {})) or set(user_names) & (set(user_simplified) | set(user_references) | set(user_rules)):
        problems.append(f"user_specified_names の一覧が、利用者が指定した名前の扱いの記録と違うか、ほかの利用者の指定の区分にも入っている: 対応表 {sorted(user_names)}")
    for target, basis in user_names.items():
        record = getattr(E, "USER_SPECIFIED_NAMES", {}).get(target)
        if basis != getattr(E, "USER_SPECIFIED_NAME_SOURCE", None) or record is None:
            problems.append(f"{target}: user_specified_names の根拠 {basis!r} が、利用者が指定した名前の扱いの出典・記録でない")
            continue
        card = research_cards.get(record.card_id) or {}
        pokemon = card.get("pokemon") or {}
        values = {"name.ja": (card.get("name") or {}).get("ja"), "pokemon.evolves_from.ja": (pokemon.get("evolves_from") or {}).get("ja")}
        values |= {f"pokemon.attacks[{i}].name.ja": (a.get("name") or {}).get("ja") for i, a in enumerate(pokemon.get("attacks") or ())}
        if any(values.get(field.field) != field.copy_value for field in record.fields):
            problems.append(f"{target}: 利用者が指定した名前の扱いの記録の写しの値が、研究の基準のコミットの値と違う")
        if not _registered_targets(registry_, record.card_id):
            problems.append(f"{target}: 利用者が指定した名前の扱いのカードが登録されていない")
        issue = issues.get(record.kyuura_issue)
        if issue is None or issue.get("status") != "UNRESOLVED":
            problems.append(f"{target}: 解決済みにしない論点 {record.kyuura_issue} が、研究の基準のコミットで UNRESOLVED ではない")

    # 4g. v0.69（docs/equivalent-non-pack-cards-v0.69.md 4 章）: 登録したカードと処理に使う欄が同じカード（拡張パック以外の商品）の登録。元のカードの登録の区分にしたがう。
    # 元のカードと、研究の基準のコミットで同じカードの組（same_card_group）にあり、印刷の文面が同じで、登録の処理に使う文面・出典が元のカードと同じ。元のカードの登録は
    # ほかの区分にある（最新の説明・エラッタなどの記録は元のカードのもので、再録のカードの照合の記録ではない）
    others = (set(section["registered"]) | set(section.get("recorded_in_card_checks", {})) | set(section.get("card_checks_without_text", {}))
              | adopted_printed | set(errata_text) | set(difference_text) | set(user_corrected) | set(simplified) | set(user_simplified)
              | set(section["registered_without_kyuura_record"]))
    actual = {t for t in texts if t.split("/")[0] in getattr(E, "EQUIVALENT_CARDS", {})}
    if set(equivalent) != actual:
        problems.append(f"equivalent_registrations の一覧が違う: 実際だけ {sorted(actual - set(equivalent))}、対応表だけ {sorted(set(equivalent) - actual)}")
    if set(equivalent) & others:
        problems.append("equivalent_registrations の登録が、ほかの区分にも入っている")
    for target, original in equivalent.items():
        card, kind, index = target.split("/")
        theirs = original.split("/")
        if getattr(E, "EQUIVALENT_CARDS", {}).get(card) != theirs[0] or theirs[1:] != [kind, index]:
            problems.append(f"{target}: equivalent_registrations の元 {original} が effects.EQUIVALENT_CARDS の元のカードの同じ対象でない")
            continue
        if original not in others:
            problems.append(f"{target}: 元のカードの登録 {original} が、研究の対応表のどの区分にもない")
        if target not in texts or original not in texts or texts[target] != texts[original]:
            problems.append(f"{target}: 処理に使う文面・出典が、元のカードの登録 {original} と違う")
        group = (research_cards.get(card) or {}).get("same_card_group")
        if group is None or group != (research_cards.get(theirs[0]) or {}).get("same_card_group"):
            problems.append(f"{target}: 研究の基準のコミットで、元のカード {theirs[0]} と同じカードの組（same_card_group）にない")
        if printed_at_research(target) != printed_at_research(original):
            problems.append(f"{target}: 研究の基準のコミットの印刷の文面が、元のカード {theirs[0]} と違う")

    # 4h. v0.71（docs/reprint-text-variants-v0.71.md 3 章）: 再録のカード（effects.REPRINT_CARDS）の、元のカードの記録（最新の説明・エラッタ）の文面を処理に使う登録。
    # 元のカードと研究の基準のコミットで同じカードの組にあり、処理に使う文面・出典が元のカードの登録と同じで、元のカードの登録の記録が研究の対応表のとおり。エラッタの記録の
    # 範囲として当てはめるもの（TXT-CHARIZARD）は、記録の notes の引用（scope_quote）が研究の基準のコミットにある。印刷の文面は元のカードと違ってよい（効果の文面の違い）
    reprints = getattr(E, "REPRINT_CARDS", {})
    actual = {t for t in texts if t.split("/")[0] in reprints and (texts[t] == texts.get(f"{reprints[t.split('/')[0]].original}/{t.split('/', 1)[1]}"))
              and texts[t][1] != "kyuura data/cards.json"}
    if set(reprinted) != actual:
        problems.append(f"reprint_registrations の一覧が違う: 実際だけ {sorted(actual - set(reprinted))}、対応表だけ {sorted(set(reprinted) - actual)}")
    if set(reprinted) & (others | set(equivalent)):
        problems.append("reprint_registrations の登録が、ほかの区分にも入っている")
    for target, value in reprinted.items():
        card, kind, index = target.split("/")
        original = value.get("original", "")
        theirs = original.split("/")
        if card not in reprints or reprints[card].original != theirs[0] or theirs[1:] != [kind, index]:
            problems.append(f"{target}: reprint_registrations の元 {original} が effects.REPRINT_CARDS の元のカードの同じ対象でない")
            continue
        if original not in others:
            problems.append(f"{target}: 元のカードの登録 {original} が、研究の対応表のどの区分にもない")
        if target not in texts or original not in texts or texts[target] != texts[original]:
            problems.append(f"{target}: 処理に使う文面・出典が、元のカードの登録 {original} と違う")
        group = (research_cards.get(card) or {}).get("same_card_group")
        if group is None or group != (research_cards.get(theirs[0]) or {}).get("same_card_group"):
            problems.append(f"{target}: 研究の基準のコミットで、元のカード {theirs[0]} と同じカードの組（same_card_group）にない")
        expected = {section["registered"].get(original), errata_text.get(original)} | set(links["card_checks"]["engine_verified"].get(theirs[0], []))
        if set(value.get("records") or []) != expected - {None}:
            problems.append(f"{target}: reprint_registrations の records が、元のカードの登録の記録 {sorted(expected - {None})} と違う")
        for rid in value.get("records") or []:
            if rid.split("-")[0] in ("ERR", "TXT", "RUL"):
                record = errata_by_id.get(rid)
                if record is None or not value.get("scope_quote") or value["scope_quote"] not in "\n".join(record.get("notes") or []):
                    problems.append(f"{target}: エラッタの記録 {rid} の範囲の引用（scope_quote）が研究の基準のコミットの記録の notes にない")

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
    # v0.70（docs/non-pack-effect-reuse-v0.70.md 3 章）: エンジンが写しの作り直しで当てはめた、利用者が示した訂正（extract_kyuura_cards.ENGINE_USER_CORRECTIONS。
    # 写しの engine_user_corrections）。対応表の engine_user_corrections に同じ訂正（カード・欄・kyuura の値・エンジンの値・根拠）があり、研究の基準のコミットの値が
    # 訂正の前の値のときだけ、その欄だけを訂正のあとの値にして比べる（ほかの欄・ほかのカードの比べ方は変えない）
    corrected = {}
    listed = {(c["card_id"], c["field"]): c for c in links.get("engine_user_corrections", [])}
    applied = {(c["card_id"], c["field"]): c for c in extract.get("engine_user_corrections", [])}
    if set(listed) != set(applied) or set(applied) != {(c["card_id"], c["field"]) for c in extract_script.ENGINE_USER_CORRECTIONS}:
        problems.append(f"対応表の engine_user_corrections {sorted(listed)} が、写しの engine_user_corrections {sorted(applied)}・ENGINE_USER_CORRECTIONS と違う")
    for key, c in sorted(applied.items()):
        entry = listed.get(key)
        theirs = research_cards.get(c["card_id"])
        if entry is None or theirs is None:
            continue
        if (entry.get("kyuura_value"), entry.get("engine_value"), entry.get("basis")) != (c["before"], c["after"], c["basis"]) or c["basis"] != "user_provided":
            problems.append(f"{c['card_id']} の {c['field']}: 対応表の engine_user_corrections が写しの訂正と違う")
            continue
        if extract_script.get_field(theirs, c["field"]) != c["before"]:
            problems.append(f"{c['card_id']} の {c['field']}: 研究の基準のコミットの値が訂正の前の値 {c['before']!r} ではない（kyuura が直したなら KYUURA_CORRECTIONS に移す）")
            continue
        corrected.setdefault(c["card_id"], []).append(c)
    for card in extract["cards"]:
        theirs = research_cards.get(card["id"])
        if theirs is None:
            problems.append(f"写しのカード {card['id']} が研究の基準のコミットにない")
            continue
        if card["id"] in corrected:
            theirs = json.loads(json.dumps(theirs))
            for c in corrected[card["id"]]:
                extract_script.set_field(theirs, c["field"], c["after"])
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
    scope_cards = {target.split("/")[0]: rid for target, rid in scoped.items()}
    for card, record in sources.items():
        if not isinstance(record, dict):
            continue
        # 採用の記録と、過去の原典照合の記録のあるカードの、照合の記録に文面のない登録の根拠（v0.30）
        if record.get("basis") != "kyuura_data" and not (record.get("basis") == "guidebook_record" and "play_text" in record):
            continue
        found = {x["id"] for x in descriptions if x["card_id"] == card}
        found |= {x["id"] for x in checks if x["card_id"] == card}
        found |= {x["id"] for x in rulings["rulings"]
                  if card in {c.get("card_id") for c in x.get("cards") or []} | set(x.get("related_cards") or [])}
        found |= {x["id"] for x in rulings["issues"] if card in {c.get("card_id") for c in x.get("cases") or []}}
        found |= {x["id"] for x in errata if card in (x.get("cards") or [])}
        found |= mapped_errata.get(card, set())  # v0.73: pcg-search.com の id で挙げたエラッタ（errata_card_ids で確かめた対応だけ）
        if card in scope_cards:  # v0.30: エラッタの記録の範囲として当てはめたもの（errata_scope）
            found.add(scope_cards[card])
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
                elif record.get("status") == "adopted" and _data_error_marked_harmless(record, e.get("field")):
                    # v0.125（docs/wigglytuff-helping-hand-v0.125.md 3 章）: データの誤りの欄を「挙動に影響しない」とした採用は、その欄が説明文で、その対象の処理に使う文面が、
                    # 印刷の文面の欄（printed_text.path）がこの欄・写しの値が kyuura の値と同じ最新の説明（LD-）のときだけ（プクリンのふくらむ）。未読の印刷・訂正の候補を一律に許可しない
                    reason = _harmless_data_error_problem(card, record, e, descriptions)
                    if reason:
                        problems.append(f"{card}: kyuura の {x['id']} のデータの誤りの欄 {e.get('field')} を挙動に影響しないとした論点: {reason}")

    # 8. エンジンの処理に使う kyuura の規定・裁定（v0.50。applied_rule_records。退化の共通の処理）: 研究の基準のコミットにあり、裁定なら分類が対応表と同じ
    clauses = {x["id"] for x in rulings.get("rule_clauses", [])}
    for entry in links.get("applied_rule_records", []):
        record_id = entry.get("kyuura_record")
        if entry.get("kind") == "rule_clause":
            if record_id not in clauses:
                problems.append(f"applied_rule_records: 規定 {record_id} が kyuura {commit[:7]} にない")
        elif entry.get("kind") == "ruling":
            ruling = by_id.get(record_id)
            if ruling is None:
                problems.append(f"applied_rule_records: 裁定 {record_id} が kyuura {commit[:7]} にない")
            elif ruling.get("status") != entry.get("kyuura_status"):
                problems.append(f"applied_rule_records: 裁定 {record_id} の分類が {ruling.get('status')}（対応表は {entry.get('kyuura_status')}）")
        else:
            problems.append(f"applied_rule_records: {record_id} の種類 {entry.get('kind')!r} は rule_clause か ruling")

    # 9. v0.97: kyuura の論点の事例のうち、エンジンの裁定 id（engine_ruling）を書いていないもの（kyuura の調査で加えた事例）と、エンジンでの扱い
    problems += unlinked_case_problems(links, issues, registry_)
    return problems


def _data_error_marked_harmless(record: dict, field: str | None) -> bool:
    """v0.125: 採用の記録の論点のうち、欄 ``field`` を挙げるものが、どれも挙動に影響しない（``affects_behavior`` が偽）か。"""
    issues = [i for i in record.get("issues") or [] if isinstance(i, dict) and field in (i.get("fields") or [])]
    return bool(issues) and all(i.get("affects_behavior") is False for i in issues)


def _harmless_data_error_problem(card: str, record: dict, error: dict, descriptions: list) -> str | None:
    """v0.125: データの誤り ``error``（CC- の ``data_error`` の 1 件）を挙動に影響しないとしてよいか。よければ None、だめなら理由の文。

    よいのは、欄が説明文（``pokemon.attacks[i].text.ja``・``pokemon.powers[i].text.ja``）で、その対象（``attack/i``・``power/i``）の採用の記録の処理に使う文面の根拠が kyuura の
    最新の説明（LD-）の id で、その記録がこのカード・この対象を指し、印刷の文面の欄（``printed_text.path``）がこの欄、印刷の文面の写しの値（``printed_text.text_ja``）が
    データの誤りの kyuura の値と同じときだけ（処理は最新の説明の全文にしたがい、誤りのある写しの文面は照合だけに使う）。"""
    field = error.get("field") or ""
    match = re.fullmatch(r"pokemon\.(attacks|powers)\[(\d+)\]\.text\.ja", field)
    if match is None:
        return "説明文でない欄の誤りは、挙動に影響しないとしない"
    target = f"{'attack' if match.group(1) == 'attacks' else 'power'}/{match.group(2)}"
    basis = (record.get("play_text") or {}).get(target)
    if not isinstance(basis, str) or not basis.startswith("LD-"):
        return f"対象 {target} の処理に使う文面の根拠が最新の説明（LD-）ではない（{basis!r}）"
    ld = next((x for x in descriptions if x.get("id") == basis), None)
    if ld is None or ld.get("card_id") != card:
        return f"最新の説明 {basis} が研究の基準のコミットにない、またはカードが違う"
    kind, index = target.split("/")
    if (ld.get("target") or {}).get("kind") != kind or (ld.get("target") or {}).get("index") != int(index):
        return f"最新の説明 {basis} の対象が {target} ではない"
    printed = ld.get("printed_text") or {}
    if printed.get("path") != field or printed.get("text_ja") != error.get("kyuura_value"):
        return f"最新の説明 {basis} の印刷の文面の欄・値が、データの誤りの欄・kyuura の値と違う"
    return None


def _registered_targets(registry, card_id: str) -> set[str]:
    targets = {f"attack/{key.attack_index}" for key in registry.attack_keys() if key.card_id == card_id}
    targets |= {f"power/{key.power_index}" for key in registry.power_keys() if key.card_id == card_id}
    if registry.trainer_entry(card_id) is not None:
        targets.add("trainer")
    # v0.124: 特殊エネルギーの登録（``EnergyEntry``。無色2個エネルギー・レインボーエネルギー）も、カードそのものの事例（``card``）の登録した対象とする
    if targets or registry.energy_entry(card_id) is not None:
        # v0.114: カードそのものの事例（``card``。ベイビィポケモンのルールのような、ワザ・特殊能力・トレーナーの登録でないカードの規定）は、カードの登録があれば登録した対象とする
        targets.add("card")
    return targets


def unlinked_case_problems(links: dict, issues: dict, registry) -> list[str]:
    """v0.97: kyuura の論点の事例のうちエンジンの裁定 id のないもの（``kyuura_cases_without_engine_ruling``）を、研究の基準のコミットの論点と照らす。

    - 対応表の事例（論点・カード・対象）の集まりが、研究の基準のコミットの、``engine_ruling`` のない事例のすべてと同じ（見落とし・余分がない）
    - エンジンの扱いはちょうど 1 つ: ``stop_codes``（対応表の stop_codes にある停止コード。そのカードの対象が登録されている。コードの kyuura_issue が事例の論点と違えば
      ``engine_issue_differs`` を真にする（kyuura への報告事項）。同じなら書かない）・``codeless_question``（codeless_questions にあり、論点が同じ。対象が登録されている）・
      ``unregistered``（そのカードの対象を登録していない。その場面は起こらない）・``requires_unregistered``（v0.123。対象は登録されているが、その場面は、同じ論点の事例の、
      登録していない別のカード（挙げた id のどれか）があるときだけ起こる。デッキに入れられないので、その場面は起こらない）・``user_specified_rule``（v0.130。その場面を、
      利用者が指定した規則 ``effects.USER_SPECIFIED_RULES`` の対象（``<カード id>/trainer``）で処理する。規則の対象のカードが登録されていて、規則の解決済みにしない論点が事例の論点と同じ。
      論点を解決したことにはしない。事例のカードの対象が登録されていなければ unregistered のまま）・``user_specified_name``（v0.131。その場面を、利用者が指定した名前の扱い
      ``effects.USER_SPECIFIED_NAMES`` の対象（``<カード id>/name`` の重ならないリスト）で処理する。どの記録のカードも登録されていて、記録の解決済みにしない論点が事例の論点と同じ。
      論点を解決したことにはしない）
    """
    problems: list[str] = []
    section = links.get("kyuura_cases_without_engine_ruling")
    if section is None:
        return problems
    cases = section.get("cases")
    if not isinstance(cases, list):
        return ["kyuura_cases_without_engine_ruling の cases はリスト"]
    actual = set()
    case_cards = {issue_id: {case.get("card_id") for case in issue.get("cases") or ()} for issue_id, issue in issues.items()}  # v0.123
    for issue_id, issue in issues.items():
        for case in issue.get("cases") or ():
            if case.get("engine_ruling"):
                continue
            target = case.get("target") or {}
            where = target.get("kind") if target.get("kind") in ("trainer", "energy", "card") else f"{target.get('kind')}/{target.get('index')}"
            actual.add((issue_id, case.get("card_id"), where))
    listed = []
    for i, case in enumerate(cases):
        where = f"kyuura_cases_without_engine_ruling {i}（{case.get('kyuura_issue')}・{case.get('card_id')}・{case.get('target')}）"
        allowed = {"kyuura_issue", "card_id", "target", "engine", "engine_issue_differs", "note"}
        if set(case) - allowed or not {"kyuura_issue", "card_id", "target", "engine"} <= set(case):
            problems.append(f"{where}: 項目は kyuura_issue・card_id・target・engine（と任意の engine_issue_differs・note）")
            continue
        listed.append((case["kyuura_issue"], case["card_id"], case["target"]))
        engine = case["engine"]
        registered = case["target"] in _registered_targets(registry, case["card_id"])
        if not isinstance(engine, dict) or len(engine) != 1:
            problems.append(f"{where}: エンジンの扱い（engine）は stop_codes・codeless_question・unregistered・requires_unregistered・user_specified_rule・user_specified_name のちょうど 1 つ")
            continue
        differs = False
        if "stop_codes" in engine:
            codes = engine["stop_codes"]
            if not isinstance(codes, list) or not codes or any(code not in links["stop_codes"] for code in codes):
                problems.append(f"{where}: 停止コード {codes!r} が対応表の stop_codes にない")
                continue
            differs = any(links["stop_codes"][code]["kyuura_issue"] != case["kyuura_issue"] for code in codes)
            if not registered:
                problems.append(f"{where}: 停止コードで止めるとしたカードの対象が登録されていない")
        elif "codeless_question" in engine:
            question = links["codeless_questions"].get(engine["codeless_question"])
            if question is None or question.get("kyuura_issue") != case["kyuura_issue"]:
                problems.append(f"{where}: コードのない問い {engine['codeless_question']!r} が対応表にない・論点が違う")
            if not registered:
                problems.append(f"{where}: コードのない問いの比べを通すとしたカードの対象が登録されていない")
        elif "requires_unregistered" in engine:
            # v0.123: 場面に要る別のカードは、同じ論点の事例のカードで、どれもエンジンに登録していない（事例のカードそのものではない）。事例の対象は登録されている
            required = engine["requires_unregistered"]
            if (not isinstance(required, list) or not required or len(set(required)) != len(required)
                    or any(not isinstance(card, str) or card == case["card_id"] for card in required)):
                problems.append(f"{where}: requires_unregistered は、事例のカードと違うカードの id の重ならないリスト")
                continue
            for card in required:
                if card not in case_cards.get(case["kyuura_issue"], ()):
                    problems.append(f"{where}: 場面に要るとしたカード {card} が、論点 {case['kyuura_issue']} の事例のカードではない")
                if _registered_targets(registry, card):
                    problems.append(f"{where}: 場面に要るとしたカード {card} が登録されている（扱いを書き直す）")
            if not registered:
                problems.append(f"{where}: 登録していない別のカードを要るとしたカードの対象 {case['target']} が登録されていない（unregistered にする）")
        elif "user_specified_rule" in engine:
            # v0.130: 利用者が指定した規則で処理する場面（とりかえっこプリーズで交換したカードの所有者）。規則の対象が登録されていて、規則の論点が事例の論点と同じ
            from kyuura_engine import effects as E

            rule = getattr(E, "USER_SPECIFIED_RULES", {}).get(engine["user_specified_rule"])
            rule_card, _, rule_kind = str(engine["user_specified_rule"]).partition("/")
            if rule is None or case["kyuura_issue"] not in getattr(rule, "issues", (rule.kyuura_issue,)) or rule_kind not in _registered_targets(registry, rule_card):
                problems.append(f"{where}: 利用者が指定した規則 {engine['user_specified_rule']!r} が記録にない・論点が違う・規則の対象が登録されていない")
            if not registered:
                problems.append(f"{where}: 利用者が指定した規則で処理するとしたカードの対象 {case['target']} が登録されていない（unregistered にする）")
        elif "user_specified_name" in engine:
            # v0.131: 利用者が指定した名前の扱いで処理する場面（ナッシー[Exeggutor] の名前）。記録のカードがどれも登録されていて、記録の論点が事例の論点と同じ
            from kyuura_engine import effects as E

            keys = engine["user_specified_name"]
            if not isinstance(keys, list) or not keys or len(set(keys)) != len(keys):
                problems.append(f"{where}: user_specified_name は、利用者が指定した名前の扱いの対象の重ならないリスト")
                continue
            for key in keys:
                spec = getattr(E, "USER_SPECIFIED_NAMES", {}).get(key)
                if spec is None or spec.kyuura_issue != case["kyuura_issue"] or not _registered_targets(registry, spec.card_id):
                    problems.append(f"{where}: 利用者が指定した名前の扱い {key!r} が記録にない・論点が違う・記録のカードが登録されていない")
            if not registered:
                problems.append(f"{where}: 利用者が指定した名前の扱いで処理するとしたカードの対象 {case['target']} が登録されていない（unregistered にする）")
        elif engine != {"unregistered": True}:
            problems.append(f"{where}: エンジンの扱い {engine!r} を扱えない")
        elif registered:
            problems.append(f"{where}: 登録していないとしたカードの対象 {case['target']} が登録されている（扱いを書き直す）")
        if differs and case.get("engine_issue_differs") is not True:
            problems.append(f"{where}: 停止コードの論点が事例の論点と違うので、engine_issue_differs を真にする（kyuura への報告事項）")
        if not differs and "engine_issue_differs" in case:
            problems.append(f"{where}: 停止コードの論点が事例の論点と同じなので、engine_issue_differs を書かない")
    if len(set(listed)) != len(listed):
        problems.append("kyuura_cases_without_engine_ruling に同じ事例が重なっている")
    if set(listed) != actual:
        problems.append(f"kyuura の論点の、エンジンの裁定 id のない事例が違う: kyuura だけ {sorted(actual - set(listed))}、対応表だけ {sorted(set(listed) - actual)}")
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
