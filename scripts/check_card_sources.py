#!/usr/bin/env python3
"""カードデータの採用と外部照合の記録（kyuura_engine/data/card_sources.json）を確かめる（2026-10-15 からの方針。docs/card-data-policy.md）。

記録は 3 種類を分けて持つ。

- kyuura データの採用（``basis: kyuura_data``）: kyuura の ``data/cards.json``（写しの元のコミット）を基本データとして実装したカード。
  採用したデータのコミット・カード id・記録した日・処理に使う文面の根拠（``play_text``）・確かめた kyuura の記録の id を持つ。
  論点のあるカードは ``status: on_hold``（登録しない）。
- pcg-search.com との照合（``external_checks``）: URL・確認日・対象の版（収録と、サイトの一覧の番号 ``list_number``）・結果・照合した欄・
  違い。対象の版がない・アクセスできなかったことも結果として残す（照合した欄は空）。
- 過去の原典照合（『オフィシャルブック2000』）: ``card_verification.json``（履歴。ここでは書き換えない）。そのカードに外部照合を加える
  とき、または照合の記録に処理に使う文面（最新の説明）のない登録（v0.30 のヒトカゲの「ひのこ」のように、照合したあとで登録したワザ）の
  文面の根拠（``play_text``・``kyuura_records``）を書くときだけ、``basis: guidebook_record`` の記録を置く。

確かめること（読んでいない原典を確かめたことにする記録・形の崩れた記録を拒否する）:

1. 形式と方針の値。記録の項目は決まったものだけ（ガイドブックの項目 ``page``・``pdf_page``・``latest_description_ja`` などは書けない）。
2. カードが写しにあり、名前が写しと同じ。採用のコミットが写しのコミット（``KYUURA_COMMIT``）と同じ。日付は方針の開始日から今日まで。
3. 登録したカードは、過去の原典照合の記録か採用の記録（``adopted``）のちょうど一方を持つ。保留（``on_hold``）のカードは登録しない。
4. 採用したカードの ``play_text`` は、登録の文面（ワザ・特殊能力・トレーナー）とちょうど対応し、根拠が kyuura の印刷の文面
   （``kyuura_printed_text``。登録の ``play_text_ja`` が写しの文面と同じで、出典が ``kyuura data/cards.json``）か、kyuura の記録の id
   （最新の説明 ``LD-``・エラッタ ``ERR-``/``TXT-``/``RUL-``。登録の出典がその id、LD- は研究の対応表の ``registered`` と、エラッタは
   ``errata_text`` と同じ）か、kyuura の日英の違いの記録が引く最新の説明（``kyuura data/curation/card_differences.json#<カード id>``。v0.31。
   登録の出典が同じ文字列で、研究の対応表の ``difference_text`` と同じ。文面は印刷の文面と違う）。過去の原典照合の記録のあるカード（``guidebook_record``）は、照合の記録に処理に使う文面のない登録だけを、
   同じ形の ``play_text`` に書く（v0.30。照合の記録に文面のある登録は、今までどおり照合の記録の文面にしたがう）。
5. 外部照合: サイトは pcg-search.com、URL は https で pcg-search.com、版の収録（と一覧の番号）がある。結果ごとに、照合した欄と違いの
   有無が合う（対象の版なし・アクセスできなかった照合に、照合した欄・違いを書けない）。欄は写しのカードにある欄だけ。違いの kyuura の
   値は写しの値と同じ。同じ版を同じデータで調べ直した照合は拒否する（既存の照合結果を再利用する）。kyuura の日本語の文面が
   pcg-search.com の転記のカード（写しの ``ja_text_source`` が pcg-search.com）は、日本語の欄を同じサイトと照合したことにしない
   （独立した照合にならない。JSON と CSV の一致と同じ）。
6. 挙動に影響する違い・論点のある採用は拒否する（そのカードは保留にする）。保留には挙動に影響する論点が要る。

kyuura の研究の基準のコミットの記録（LD-・CC-・CR-・UQ-・エラッタ）との照合は ``scripts/check_research_links.py`` が行う。

    python3 scripts/check_card_sources.py
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SOURCES = ROOT / "kyuura_engine" / "data" / "card_sources.json"
FORMAT = "kyuura-engine card sources 1"
POLICY = {
    "since": "2026-10-15",
    "document": "docs/card-data-policy.md",
    "card_data": "kyuura data/cards.json",
    "external_site": "pcg-search.com",
}
SITE = "pcg-search.com"
HOSTS = {"pcg-search.com", "www.pcg-search.com"}
KYUURA_DATA = "kyuura_data"
GUIDEBOOK_RECORD = "guidebook_record"
ADOPTED = "adopted"
ON_HOLD = "on_hold"
PRINTED_TEXT = "kyuura_printed_text"
PRINTED_TEXT_SOURCE = "kyuura data/cards.json"
# v0.31: kyuura の日英の違いの記録（data/curation/card_differences.json）が引く最新の説明を処理に使う文面にした登録の根拠・出典（``#`` のあとが
# カード id。研究の対応表の difference_text。文面が記録の引用と同じことは scripts/check_research_links.py が kyuura で確かめる）
DIFFERENCE_TEXT_SOURCE = "kyuura data/curation/card_differences.json"
# v0.58: 日本語の説明のない特殊エネルギー（無色2個エネルギー）の根拠。処理に使う文面はなく、出すエネルギーの個数と色を、kyuura の名前と pcg-search.com の同じ版の
# カードの記号で決めた（登録の出典は effects.DCE_SOURCE と同じ。同じ版の照合（結果 match。名前と種類を照らした）が要る）
NAME_AND_SYMBOLS = "card_name_and_edition_symbols"
NAME_AND_SYMBOLS_SOURCE = "kyuura data/cards.json name.ja + pcg-search.com 1st1096 (096/096) symbols"
# v0.65: このリポジトリの過去の記録（版の文書の節）の最新の説明を処理に使う文面にした登録の根拠・出典（カスミのドククラゲの［にげこむ］。v0.18b に p.100 を読んで
# docs/unresolved-research-v0.18b.md 4.1 に記録した文面の再利用）。許すのは ``ENGINE_RECORDS`` の根拠だけで、文面がその文書にそのまま書かれていること・研究の対応表の
# registered_without_kyuura_record（kyuura に記録がない。kyuura への報告事項）にあること・印刷の文面と違うことを確かめる
ENGINE_RECORDS = {"kyuura-engine docs/unresolved-research-v0.18b.md#4.1": ROOT / "docs" / "unresolved-research-v0.18b.md"}
# v0.68（docs/final-pmcg-cards-v0.68.md 2 章）: 利用者が示した修正（写しの書き出しの ``user_provided_corrections``。scripts/extract_kyuura_cards.py の
# USER_PROVIDED_CORRECTIONS）を当てはめた説明文を、処理に使う文面にした登録の根拠・出典（ガルーラの「こどものおつかい」）。kyuura の記録（CC-・LD-）ではない
USER_CORRECTION = "user_provided_correction"
USER_CORRECTION_SOURCE = "kyuura data/cards.json + USER_PROVIDED_CORRECTIONS"
# v0.68（4 章）: エンジンの簡略化した仕様（公式の裁定・エラッタではない）を処理に使う文面にした登録の根拠・出典（イマクニ？のドードー）。文面がその文書の引用（「」）に
# あること・印刷の文面と違うこと・研究の対応表の engine_simplified_text にあることを確かめる
ENGINE_SIMPLIFICATIONS = {"kyuura-engine docs/final-pmcg-cards-v0.68.md#4": ROOT / "docs" / "final-pmcg-cards-v0.68.md"}
RESULTS = ("match", "differences", "edition_not_listed", "inaccessible")
COMPLETED = ("match", "differences")

# 『オフィシャルブック2000』の照合の項目（card_verification.json の項目）。この記録には書かない（読んでいない原典を確かめたことにしない）
GUIDEBOOK_KEYS = {"page", "pdf_page", "scan", "rules_page", "commentary_page", "card_image_text_ja", "latest_description_ja",
                  "power_card_image_text_ja", "power_latest_description_ja", "image_check", "mismatches"}
KYUURA_DATA_KEYS = {"basis", "name_ja", "status", "kyuura_commit", "recorded_on", "kyuura_records", "play_text", "external_checks", "issues"}
GUIDEBOOK_RECORD_KEYS = {"basis", "name_ja", "external_checks"}
# v0.30: 過去の原典照合の記録のあるカードに、照合の記録に処理に使う文面のない登録の根拠（play_text・kyuura_records）を書ける
OPTIONAL_CARD_KEYS = {KYUURA_DATA: {"notes"}, GUIDEBOOK_RECORD: {"issues", "notes", "play_text", "kyuura_records"}}
CHECK_KEYS = {"site", "url", "checked_on", "kyuura_commit", "edition", "result", "checked_fields", "differences"}
DIFFERENCE_KEYS = {"field", "kyuura", "pcg_search", "affects_behavior"}
ISSUE_KEYS = {"question", "fields", "affects_behavior"}

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
RECORD_ID = re.compile(r"^(LD|CC|CR|UQ|ERR|TXT|RUL)-[A-Za-z0-9-]+$")
PLAY_TEXT_ID = re.compile(r"^(LD|ERR|TXT|RUL)-[A-Za-z0-9-]+$")
TARGET = re.compile(r"^(attack|power)/(\d+)$|^trainer$|^energy$")
CARD_FIELD = re.compile(r"^(name\.ja|pokemon\.(stage|evolves_from\.ja|hp|types|weaknesses|resistances|retreat_cost|rules_text)"
                        r"|trainer\.text\.ja|energy\.(kind|provides|text\.ja)|jp_print\.(level|rarity))$")
INDEXED_FIELD = re.compile(r"^pokemon\.(attacks|powers)\[(\d+)\]\.(name\.ja|cost|damage|text\.ja)$")
JAPANESE_FIELD = re.compile(r"(^|\.)(name|text)\.ja$")


def load_sources() -> dict:
    return json.loads(SOURCES.read_text(encoding="utf-8"))


def load_links() -> dict:
    return json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))


def registration_basis(card_id: str, verification: dict, sources: dict) -> str | None:
    """登録の根拠: 過去の原典照合の記録（``guidebook_record``）、採用の記録（``kyuura_data``）、どちらもない（None）。
    両方あるときも None（どちらにしたがうかが決まらない。``problems`` が拒否する）。"""
    record = sources["cards"].get(card_id, {})
    adopted = record.get("basis") == KYUURA_DATA and record.get("status") == ADOPTED
    legacy = card_id in verification["cards"]
    if adopted == legacy:
        return None
    return KYUURA_DATA if adopted else GUIDEBOOK_RECORD


def play_text_targets(registry, card_id: str) -> dict[str, object]:
    """登録の中で、処理に使う文面（``play_text_ja``）を持つもの: 対象（``attack/0``・``power/0``・``trainer``）→ 登録。"""
    found = {}
    for key in registry.attack_keys():
        entry = registry.attack_entry(key.card_id, key.attack_index)
        if key.card_id == card_id and entry.play_text_ja is not None:
            found[f"attack/{key.attack_index}"] = entry
    for key in registry.power_keys():
        if key.card_id == card_id:
            found[f"power/{key.power_index}"] = registry.power_entry(key.card_id, key.power_index)
    if card_id in registry.trainer_ids():
        found["trainer"] = registry.trainer_entry(card_id)
    if card_id in registry.energy_ids():
        found["energy"] = registry.energy_entry(card_id)  # v0.58: 特殊エネルギー（日本語の説明のないものも根拠を書く）
    return found


def verified_play_text_targets(record: dict, targets) -> set[str]:
    """過去の原典照合の記録（``card_verification.json`` のカードの記録）が処理に使う文面（最新の説明）を持つ対象（v0.30）。ワザ・トレーナーは
    ``latest_description_ja``（説明文のあるワザが 2 つのカードはワザの位置ごとの辞書）、特殊能力は ``power_latest_description_ja``（位置ごと）。
    ここにない対象（照合したあとで登録したワザ）の文面の根拠は、card_sources.json の ``play_text`` に書く。"""
    covered = set()
    for target in targets:
        if target == "trainer":
            if record.get("latest_description_ja") is not None:
                covered.add(target)
            continue
        kind, index = target.split("/")
        value = record.get("latest_description_ja" if kind == "attack" else "power_latest_description_ja")
        if (isinstance(value, dict) and value.get(index) is not None) or isinstance(value, str):
            covered.add(target)
    return covered


def uncovered_play_text_targets(card_id: str, verification: dict, registry) -> set[str]:
    """過去の原典照合の記録のあるカードで、処理に使う文面のある登録のうち、照合の記録に文面がないもの（v0.30）。"""
    targets = play_text_targets(registry, card_id)
    return set(targets) - verified_play_text_targets(verification["cards"].get(card_id, {}), targets)


def registered_cards(registry) -> set[str]:
    return ({k.card_id for k in registry.attack_keys()} | {k.card_id for k in registry.power_keys()} | set(registry.trainer_ids())
            | set(registry.energy_ids()))  # v0.58: 特殊エネルギー


def printed_text(card: dict, target: str) -> str | None:
    if target == "trainer":
        return ((card.get("trainer") or {}).get("text") or {}).get("ja")
    if target == "energy":
        return ((card.get("energy") or {}).get("text") or {}).get("ja")
    kind, index = target.split("/")
    items = (card.get("pokemon") or {}).get("attacks" if kind == "attack" else "powers") or []
    if int(index) >= len(items):
        return None
    return (items[int(index)].get("text") or {}).get("ja")


_MISSING = object()


def field_value(card: dict, path: str):
    """写しのカードの欄の値（``pokemon.attacks[0].text.ja`` の形）。欄がなければ ``_MISSING``。"""
    value = card
    for part in path.split("."):
        match = re.fullmatch(r"(\w+)\[(\d+)\]", part)
        name, index = (match.group(1), int(match.group(2))) if match else (part, None)
        if not isinstance(value, dict) or name not in value:
            return _MISSING
        value = value[name]
        if index is not None:
            if not isinstance(value, list) or index >= len(value):
                return _MISSING
            value = value[index]
    return value


def field_problem(card: dict, path) -> str | None:
    if not isinstance(path, str) or not (CARD_FIELD.match(path) or INDEXED_FIELD.match(path)):
        return f"欄 {path!r} は照合できる欄ではない"
    root = path.split(".")[0]
    if root in ("pokemon", "trainer", "energy") and not card.get(root):
        return f"欄 {path} はこのカード（{card['category']}）にない"
    if root not in ("name", "jp_print") and field_value(card, path) is _MISSING:
        return f"欄 {path} は写しのカードにない（位置がない）"
    return None


def date_problem(value, label: str, today: datetime.date) -> str | None:
    if not isinstance(value, str) or not DATE.match(value):
        return f"{label} {value!r} は YYYY-MM-DD の日付ではない"
    try:
        day = datetime.date.fromisoformat(value)
    except ValueError:
        return f"{label} {value!r} は日付ではない"
    if day < datetime.date.fromisoformat(POLICY["since"]):
        return f"{label} {value} は方針の開始日（{POLICY['since']}）より前"
    if day > today:
        return f"{label} {value} は今日（{today.isoformat()}）より後"
    return None


def keys_problems(where: str, record: dict, required: set[str], optional: set[str] = frozenset()) -> list[str]:
    found = []
    guidebook = sorted(set(record) & GUIDEBOOK_KEYS)
    if guidebook:
        found.append(f"{where}: ガイドブックの照合の項目 {guidebook} は書かない（原典の照合の記録は card_verification.json の履歴だけ）")
    unknown = sorted(set(record) - required - optional - GUIDEBOOK_KEYS)
    if unknown:
        found.append(f"{where}: 知らない項目 {unknown}")
    missing = sorted(required - set(record))
    if missing:
        found.append(f"{where}: 項目 {missing} がない")
    return found


def check_problems(where: str, check, card: dict, commit: str, today: datetime.date, corrections: dict | None = None) -> list[str]:
    if not isinstance(check, dict):
        return [f"{where}: 照合の記録が辞書ではない"]
    found = keys_problems(where, check, CHECK_KEYS, {"note"})
    if found:
        return found
    if check["site"] != SITE:
        found.append(f"{where}: 外部照合のサイト {check['site']!r} は {SITE} ではない")
    url = check["url"]
    parts = urlsplit(url) if isinstance(url, str) else None
    if parts is None or parts.scheme != "https" or parts.hostname not in HOSTS or parts.username or parts.password:
        found.append(f"{where}: URL {url!r} は https の {SITE} のページではない")
    problem = date_problem(check["checked_on"], "確認日", today)
    if problem:
        found.append(f"{where}: {problem}")
    if not isinstance(check["kyuura_commit"], str) or not COMMIT.match(check["kyuura_commit"]):
        found.append(f"{where}: 照らした kyuura のコミット {check['kyuura_commit']!r} が 40 桁の SHA ではない")
    result = check["result"]
    if result not in RESULTS:
        found.append(f"{where}: 結果 {result!r} は {list(RESULTS)} のどれでもない")
    edition = check["edition"]
    if not isinstance(edition, dict) or set(edition) != {"expansion", "list_number"}:
        found.append(f"{where}: 対象の版（edition）は収録（expansion）と一覧の番号（list_number）を持つ")
    else:
        if not isinstance(edition["expansion"], str) or not edition["expansion"].strip():
            found.append(f"{where}: 対象の版の収録（expansion）がない")
        number = edition["list_number"]
        if result in COMPLETED and (not isinstance(number, str) or not number.strip()):
            found.append(f"{where}: 照合した版の一覧の番号（list_number）がない（カード名だけで版を決めない）")
        elif number is not None and (not isinstance(number, str) or not number.strip()):
            found.append(f"{where}: 一覧の番号（list_number）は空でない文字列か null")
    fields, differences = check["checked_fields"], check["differences"]
    if not isinstance(fields, list) or not isinstance(differences, list):
        return [*found, f"{where}: checked_fields・differences はリスト"]
    if len(set(map(str, fields))) != len(fields):
        found.append(f"{where}: 照合した欄が重なっている")
    for field in fields:
        problem = field_problem(card, field)
        if problem:
            found.append(f"{where}: {problem}")
    source = urlsplit(card.get("ja_text_source") or "").hostname
    circular = sorted(f for f in fields if isinstance(f, str) and JAPANESE_FIELD.search(f)) if source in HOSTS else []
    if circular:
        found.append(f"{where}: kyuura の日本語の文面は pcg-search.com の転記（ja_text_source）なので、日本語の欄 {circular} を同じサイトと"
                     "照合したことにしない（独立した照合にならない）")
    if result in ("edition_not_listed", "inaccessible"):
        if fields or differences:
            found.append(f"{where}: 結果 {result} の照合に、照合した欄・違いを書けない（照合していない欄を確かめたことにしない）")
    elif result == "match":
        if not fields:
            found.append(f"{where}: 結果 match の照合に、照合した欄がない")
        if differences:
            found.append(f"{where}: 結果 match の照合に、違いがある（結果は differences）")
    elif result == "differences":
        if not fields:
            found.append(f"{where}: 結果 differences の照合に、照合した欄がない")
        if not differences:
            found.append(f"{where}: 結果 differences の照合に、違いがない（結果は match）")
    for i, difference in enumerate(differences):
        here = f"{where} の違い {i}"
        if not isinstance(difference, dict):
            found.append(f"{here}: 辞書ではない")
            continue
        problems = keys_problems(here, difference, DIFFERENCE_KEYS, {"note"})
        if problems:
            found.extend(problems)
            continue
        if difference["field"] not in fields:
            found.append(f"{here}: 欄 {difference['field']} が照合した欄にない")
        if not isinstance(difference["affects_behavior"], bool):
            found.append(f"{here}: affects_behavior は true か false")
        if difference["kyuura"] == difference["pcg_search"]:
            found.append(f"{here}: kyuura と pcg-search.com の値が同じ（違いではない）")
        # v0.68: 利用者が示した修正を当てはめた欄は、写しの元の値（修正の before）と比べる（照合は写しの元のデータと比べた記録）
        correction = (corrections or {}).get((card.get("id"), difference["field"]))
        original = correction["before"] if correction else field_value(card, difference["field"])
        if check["kyuura_commit"] == commit and original != difference["kyuura"] \
                and field_problem(card, difference["field"]) is None:
            found.append(f"{here}: kyuura の値が写しの値と違う（写しの値をそのまま書く）")
    return found


def issue_problems(where: str, issues, card: dict) -> list[str]:
    if not isinstance(issues, list):
        return [f"{where}: issues はリスト"]
    found = []
    for i, issue in enumerate(issues):
        here = f"{where} の論点 {i}"
        if not isinstance(issue, dict):
            found.append(f"{here}: 辞書ではない")
            continue
        problems = keys_problems(here, issue, ISSUE_KEYS, {"kyuura_issue", "note"})
        if problems:
            found.extend(problems)
            continue
        if not isinstance(issue["question"], str) or not issue["question"].strip():
            found.append(f"{here}: 問い（question）がない")
        if not isinstance(issue["affects_behavior"], bool):
            found.append(f"{here}: affects_behavior は true か false")
        if not isinstance(issue["fields"], list):
            found.append(f"{here}: fields はリスト")
        else:
            for field in issue["fields"]:
                problem = field_problem(card, field)
                if problem:
                    found.append(f"{here}: {problem}")
        if "kyuura_issue" in issue and not (isinstance(issue["kyuura_issue"], str) and issue["kyuura_issue"].startswith("UQ-")):
            found.append(f"{here}: kyuura_issue は UQ- の id")
    return found


def behaviour_affecting(record: dict, corrections: dict | None = None, card_id: str | None = None) -> list[str]:
    """挙動に影響するとした違い・論点の欄（または問い）。v0.68: 利用者が示した修正で写しを外部照合のサイトの値に直した欄の違いは、解消したので数えない。"""
    found = []
    for check in record.get("external_checks") or []:
        if isinstance(check, dict):
            for difference in check.get("differences") or []:
                correction = (corrections or {}).get((card_id, difference.get("field"))) if isinstance(difference, dict) else None
                if correction and correction["before"] == difference.get("kyuura") and correction["after"] == difference.get("pcg_search"):
                    continue
                if isinstance(difference, dict) and difference.get("affects_behavior") is True:
                    found.append(str(difference.get("field")))
    for issue in record.get("issues") or []:
        if isinstance(issue, dict) and issue.get("affects_behavior") is True:
            found.append(str(issue.get("question")))
    return found


def play_text_problems(where: str, record: dict, card: dict, registry, links: dict, expected: set[str] | None = None,
                       corrections: dict | None = None) -> list[str]:
    """``play_text`` の対象と根拠。``expected`` は書くべき対象（既定は、処理に使う文面のある登録すべて。過去の原典照合の記録のあるカードは、
    照合の記録に文面のない登録だけ。v0.30）。"""
    found = []
    play_text = record["play_text"]
    if not isinstance(play_text, dict):
        return [f"{where}: play_text は辞書"]
    for target in play_text:
        if not TARGET.match(target):
            found.append(f"{where}: play_text の対象 {target!r} は attack/<位置>・power/<位置>・trainer・energy のどれでもない")
    targets = play_text_targets(registry, card["id"])
    if record.get("status") == ON_HOLD:
        if play_text:
            found.append(f"{where}: 保留のカードに play_text を書けない（登録しない）")
        return found
    expected = set(targets) if expected is None else expected
    if set(play_text) != expected:
        found.append(f"{where}: play_text の対象 {sorted(play_text)} が、根拠を書くべき登録の文面 {sorted(expected)} と違う")
    registered_ld = links["latest_descriptions"]["registered"]
    registered_errata = links["latest_descriptions"].get("errata_text", {})
    adopted_printed = set(links["latest_descriptions"].get("adopted_printed_text", []))
    kyuura_records = record["kyuura_records"] if isinstance(record["kyuura_records"], list) else []
    for target, basis in play_text.items():
        entry = targets.get(target)
        if entry is None:
            continue
        key = f"{card['id']}/{target}"
        if entry.text_ja != printed_text(card, target):
            found.append(f"{where} {target}: 登録の印刷の文面（text_ja）が写しの文面と違う")
        if basis == PRINTED_TEXT:
            if entry.play_text_ja != entry.text_ja:
                found.append(f"{where} {target}: 根拠が kyuura の印刷の文面なのに、登録の play_text_ja が写しの文面と違う")
            if entry.source != PRINTED_TEXT_SOURCE:
                found.append(f"{where} {target}: 根拠が kyuura の印刷の文面なのに、出典が {entry.source!r}（{PRINTED_TEXT_SOURCE!r} にする）")
            if target not in ("trainer", "energy") and key not in adopted_printed:
                found.append(f"{where} {target}: 研究の対応表の adopted_printed_text にない")
        elif basis == NAME_AND_SYMBOLS:
            # v0.58: 日本語の説明のない特殊エネルギー。処理に使う文面はなく（登録の text_ja・play_text_ja は None）、出典は名前と同じ版の記号。同じ版の照合（match）が要る
            if target != "energy" or entry.text_ja is not None or entry.play_text_ja is not None or printed_text(card, target) is not None:
                found.append(f"{where} {target}: 根拠 {NAME_AND_SYMBOLS} は、日本語の説明のない特殊エネルギーの登録（文面なし）だけに使う")
            if entry.source != NAME_AND_SYMBOLS_SOURCE:
                found.append(f"{where} {target}: 根拠が {NAME_AND_SYMBOLS} なのに、出典が {entry.source!r}（{NAME_AND_SYMBOLS_SOURCE!r} にする）")
            if not any(isinstance(c, dict) and c.get("result") == "match" and "name.ja" in (c.get("checked_fields") or []) for c in record.get("external_checks") or []):
                found.append(f"{where} {target}: 根拠 {NAME_AND_SYMBOLS} には、名前を照らした同じ版の外部照合（match）が要る")
        elif basis == USER_CORRECTION:
            # v0.68: 利用者が示した修正を当てはめた写しの説明文（処理に使う文面は、修正のあとの文面と同じ）
            path = f"pokemon.{'attacks' if target.startswith('attack') else 'powers'}[{target.split('/')[1]}].text.ja" if "/" in target else None
            correction = (corrections or {}).get((card["id"], path))
            if correction is None:
                found.append(f"{where} {target}: 根拠 {USER_CORRECTION} なのに、写しにこの欄の利用者が示した修正（user_provided_corrections）がない")
            elif not (entry.text_ja == entry.play_text_ja == correction["after"] == printed_text(card, target)):
                found.append(f"{where} {target}: 根拠 {USER_CORRECTION} の登録の文面が、修正のあとの写しの文面と違う")
            if entry.source != USER_CORRECTION_SOURCE:
                found.append(f"{where} {target}: 根拠が {USER_CORRECTION} なのに、出典が {entry.source!r}（{USER_CORRECTION_SOURCE!r} にする）")
            if key not in links["latest_descriptions"].get("user_corrected_text", {}):
                found.append(f"{where} {target}: 研究の対応表の user_corrected_text にない")
            if key in adopted_printed:
                found.append(f"{where} {target}: 研究の対応表の adopted_printed_text にある（根拠は {USER_CORRECTION}）")
        elif isinstance(basis, str) and basis in ENGINE_SIMPLIFICATIONS:
            if entry.source != basis:
                found.append(f"{where} {target}: 根拠が {basis} なのに、出典が {entry.source!r}")
            if entry.play_text_ja == entry.text_ja:
                found.append(f"{where} {target}: 根拠がエンジンの簡略化した仕様なのに、処理に使う文面が印刷の文面と同じ")
            if f"「{entry.play_text_ja}」" not in ENGINE_SIMPLIFICATIONS[basis].read_text(encoding="utf-8"):
                found.append(f"{where} {target}: 処理に使う文面が、根拠の文書 {ENGINE_SIMPLIFICATIONS[basis].name} の引用（「」）にない")
            if links["latest_descriptions"].get("engine_simplified_text", {}).get(key) != basis:
                found.append(f"{where} {target}: 根拠 {basis} が研究の対応表の engine_simplified_text にない")
            if key in adopted_printed:
                found.append(f"{where} {target}: 研究の対応表の adopted_printed_text にある（根拠は {basis}）")
        elif isinstance(basis, str) and basis in ENGINE_RECORDS:
            if entry.source != basis:
                found.append(f"{where} {target}: 根拠が {basis} なのに、出典が {entry.source!r}")
            if entry.play_text_ja == entry.text_ja:
                found.append(f"{where} {target}: 根拠がこのリポジトリの記録の最新の説明なのに、処理に使う文面が印刷の文面と同じ")
            if f"「{entry.play_text_ja}」" not in ENGINE_RECORDS[basis].read_text(encoding="utf-8"):
                found.append(f"{where} {target}: 処理に使う文面が、根拠の文書 {ENGINE_RECORDS[basis].name} の引用（「」）にない")
            if key not in links["latest_descriptions"].get("registered_without_kyuura_record", []):
                found.append(f"{where} {target}: 根拠 {basis} の登録が、研究の対応表の registered_without_kyuura_record にない")
            if key in adopted_printed:
                found.append(f"{where} {target}: 研究の対応表の adopted_printed_text にある（根拠は {basis}）")
        elif isinstance(basis, str) and basis == f"{DIFFERENCE_TEXT_SOURCE}#{card['id']}":
            if entry.source != basis:
                found.append(f"{where} {target}: 根拠が {basis} なのに、出典が {entry.source!r}")
            if links["latest_descriptions"].get("difference_text", {}).get(key) != basis:
                found.append(f"{where} {target}: 根拠 {basis} が研究の対応表の difference_text にない")
            if entry.play_text_ja == entry.text_ja:
                found.append(f"{where} {target}: 根拠が kyuura の日英の違いの記録の最新の説明なのに、処理に使う文面が印刷の文面と同じ")
            if key in adopted_printed:
                found.append(f"{where} {target}: 研究の対応表の adopted_printed_text にある（根拠は {basis}）")
        elif isinstance(basis, str) and PLAY_TEXT_ID.match(basis):
            if entry.source != basis:
                found.append(f"{where} {target}: 根拠が {basis} なのに、出典が {entry.source!r}")
            if basis not in kyuura_records:
                found.append(f"{where} {target}: 根拠 {basis} が kyuura_records にない")
            if basis.startswith("LD-") and registered_ld.get(key) != basis:
                found.append(f"{where} {target}: 根拠 {basis} が研究の対応表の registered にない")
            if basis.split("-")[0] in ("ERR", "TXT", "RUL") and registered_errata.get(key) != basis:
                found.append(f"{where} {target}: 根拠のエラッタ {basis} が研究の対応表の errata_text にない")
            if key in adopted_printed:
                found.append(f"{where} {target}: 研究の対応表の adopted_printed_text にある（根拠は {basis}）")
        else:
            found.append(f"{where} {target}: 根拠 {basis!r} は {PRINTED_TEXT}・kyuura の記録の id（LD-・ERR-・TXT-・RUL-）・"
                         f"{DIFFERENCE_TEXT_SOURCE}#<カード id>・{NAME_AND_SYMBOLS}・{USER_CORRECTION}・このリポジトリの記録（{sorted(ENGINE_RECORDS)}）・"
                         f"エンジンの簡略化した仕様（{sorted(ENGINE_SIMPLIFICATIONS)}）のどれでもない")
    return found


def kyuura_records_problems(where: str, record: dict) -> list[str]:
    ids = record.get("kyuura_records")
    if not isinstance(ids, list) or any(not isinstance(x, str) or not RECORD_ID.match(x) for x in ids):
        return [f"{where}: kyuura_records は kyuura の記録の id（LD-・CC-・CR-・UQ-・ERR-・TXT-・RUL-）のリスト"]
    if len(set(ids)) != len(ids):
        return [f"{where}: kyuura_records に同じ id が重なっている"]
    return []


def card_problems(card_id: str, record, *, cards: dict, commit: str, verification: dict, registry, links: dict,
                  today: datetime.date, corrections: dict | None = None) -> list[str]:
    where = card_id
    if not isinstance(record, dict):
        return [f"{where}: 記録が辞書ではない"]
    card = cards.get(card_id)
    if card is None:
        return [f"{where}: 写し（kyuura_cards.json）にないカード"]
    basis = record.get("basis")
    if basis == KYUURA_DATA:
        found = keys_problems(where, record, KYUURA_DATA_KEYS, OPTIONAL_CARD_KEYS[KYUURA_DATA])
    elif basis == GUIDEBOOK_RECORD:
        found = keys_problems(where, record, GUIDEBOOK_RECORD_KEYS, OPTIONAL_CARD_KEYS[GUIDEBOOK_RECORD])
    else:
        return [f"{where}: basis {basis!r} は {KYUURA_DATA}・{GUIDEBOOK_RECORD} のどちらでもない"]
    if found:
        return found
    if record["name_ja"] != card["name"]["ja"]:
        found.append(f"{where}: 名前 {record['name_ja']!r} が写しの名前 {card['name']['ja']!r} と違う")
    checks = record["external_checks"]
    if not isinstance(checks, list):
        return [*found, f"{where}: external_checks はリスト"]
    for i, check in enumerate(checks):
        found.extend(check_problems(f"{where} の外部照合 {i}", check, card, commit, today, corrections))
    completed = {}
    for i, check in enumerate(checks):
        if isinstance(check, dict) and check.get("result") in COMPLETED and isinstance(check.get("edition"), dict):
            edition = (check["edition"].get("expansion"), check["edition"].get("list_number"), check.get("kyuura_commit"))
            if edition in completed:
                found.append(f"{where} の外部照合 {i}: 外部照合 {completed[edition]} と同じ版を同じデータで調べ直している（既存の照合結果を再利用する）")
            completed.setdefault(edition, i)
    found.extend(issue_problems(where, record.get("issues", []), card))
    if basis == GUIDEBOOK_RECORD:
        if card_id not in verification["cards"]:
            found.append(f"{where}: basis {GUIDEBOOK_RECORD} なのに、card_verification.json に記録がない")
        if not checks and not record.get("play_text"):
            found.append(f"{where}: basis {GUIDEBOOK_RECORD} の記録は、外部照合か、照合の記録に文面のない登録の根拠（play_text）を加えるときだけ置く")
        if "play_text" in record or "kyuura_records" in record:
            found.extend(kyuura_records_problems(where, record))
            if "play_text" not in record:
                found.append(f"{where}: kyuura_records は play_text といっしょに書く")
            else:
                found.extend(play_text_problems(where, record, card, registry, links,
                                                expected=uncovered_play_text_targets(card_id, verification, registry)))
        affected = {str(d.get("field")) for c in checks if isinstance(c, dict) for d in c.get("differences") or []
                    if isinstance(d, dict) and d.get("affects_behavior") is True}
        noted = {f for issue in record.get("issues", []) if isinstance(issue, dict) for f in issue.get("fields") or []}
        for field in sorted(affected - noted):
            found.append(f"{where}: 挙動に影響する違い（{field}）の論点がない")
        return found
    # kyuura データの採用
    if record["status"] not in (ADOPTED, ON_HOLD):
        found.append(f"{where}: status {record['status']!r} は {ADOPTED}・{ON_HOLD} のどちらでもない")
        return found
    if record["kyuura_commit"] != commit:
        found.append(f"{where}: 採用したデータのコミット {record['kyuura_commit']!r} が写しのコミット {commit} と違う")
    problem = date_problem(record["recorded_on"], "記録した日", today)
    if problem:
        found.append(f"{where}: {problem}")
    found.extend(kyuura_records_problems(where, record))
    if card_id in verification["cards"]:
        found.append(f"{where}: card_verification.json（過去の原典照合）にも記録がある（登録の根拠を 1 つにする）")
    registered = card_id in registered_cards(registry)
    affecting = behaviour_affecting(record, corrections, card_id)
    if record["status"] == ADOPTED:
        if not registered:
            found.append(f"{where}: 採用したカードが登録されていない（登録したときに採用の記録を置く）")
        if affecting:
            found.append(f"{where}: 挙動に影響する違い・論点 {affecting} がある（このカードは保留にする）")
    else:
        if registered:
            found.append(f"{where}: 保留のカードが登録されている")
        if not affecting:
            found.append(f"{where}: 保留の理由（挙動に影響する論点）がない")
    found.extend(play_text_problems(where, record, card, registry, links, corrections=corrections))
    return found


def problems(sources: dict | None = None, *, extract: dict | None = None, verification: dict | None = None, registry=None,
             links: dict | None = None, today: datetime.date | None = None) -> list[str]:
    """記録の問題の一覧（なければ空）。引数を省くと、同梱のデータと ``DEFAULT_EFFECTS`` を使う。"""
    from kyuura_engine.cards import read_extract, read_verification
    from kyuura_engine.effects import DEFAULT_EFFECTS

    sources = load_sources() if sources is None else sources
    extract = read_extract() if extract is None else extract
    verification = read_verification() if verification is None else verification
    registry = DEFAULT_EFFECTS if registry is None else registry
    links = load_links() if links is None else links
    today = datetime.date.today() if today is None else today
    found = keys_problems("記録", sources, {"format", "description", "policy", "cards"})
    if found:
        return found
    if sources["format"] != FORMAT:
        found.append(f"形式 {sources['format']!r} は {FORMAT!r} ではない")
    if sources["policy"] != POLICY:
        found.append(f"方針の値 {sources['policy']!r} が {POLICY!r} と違う")
    if not isinstance(sources["cards"], dict):
        return [*found, "cards は辞書"]
    cards = {c["id"]: c for c in extract["cards"]}
    commit = extract["source"]["commit"]
    corrections = {(c["card_id"], c["field"]): c for c in extract.get("user_provided_corrections", [])}
    for card_id, record in sources["cards"].items():
        found.extend(card_problems(card_id, record, cards=cards, commit=commit, verification=verification, registry=registry,
                                   links=links, today=today, corrections=corrections))
    for card_id in sorted(registered_cards(registry)):
        basis = registration_basis(card_id, verification, sources)
        if basis is None:
            found.append(f"{card_id}: 登録したカードに、過去の原典照合の記録か採用の記録（adopted）のちょうど一方がない")
        elif basis == GUIDEBOOK_RECORD:
            uncovered = uncovered_play_text_targets(card_id, verification, registry)
            record = sources["cards"].get(card_id)
            if uncovered and not (isinstance(record, dict) and isinstance(record.get("play_text"), dict)):
                found.append(f"{card_id}: 照合の記録に処理に使う文面のない登録 {sorted(uncovered)} の根拠（card_sources.json の play_text）がない")
    adopted_printed = set(links["latest_descriptions"].get("adopted_printed_text", []))
    expected = {f"{card_id}/{target}" for card_id, record in sources["cards"].items()
                if isinstance(record, dict) and record.get("basis") == KYUURA_DATA and record.get("status") == ADOPTED
                and isinstance(record.get("play_text"), dict)
                for target, basis in record["play_text"].items() if basis == PRINTED_TEXT and target not in ("trainer", "energy")}
    for key in sorted(adopted_printed - expected):
        found.append(f"研究の対応表の adopted_printed_text の {key} に、kyuura の印刷の文面を根拠とする採用の記録がない")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args(argv)
    found = problems()
    if found:
        for problem in found:
            print(problem, file=sys.stderr)
        print(f"カードデータの採用と外部照合の記録に {len(found)} 件の問題がある", file=sys.stderr)
        return 1
    count = len(load_sources()["cards"])
    print(f"カードデータの採用と外部照合の記録は方針と合っています（記録 {count} 件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
