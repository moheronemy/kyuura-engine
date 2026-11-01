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
ENGINE_RECORDS = {"kyuura-engine docs/unresolved-research-v0.18b.md#4.1": ROOT / "docs" / "unresolved-research-v0.18b.md",
                  # v0.87（docs/movement-damage-reactions-v0.87.md 2 章）: v0.10 の読取記録（p.20 のコクーンの［どくのたいえき］・p.138 のマチスのマルマインの［ショックボム］の
                  # 特殊能力欄。2026-10-14 に読んだ。v0.87 では原典を開いていない）
                  "kyuura-engine docs/counterattack-v0.10.md#2": ROOT / "docs" / "counterattack-v0.10.md"}
# v0.68（docs/final-pmcg-cards-v0.68.md 2 章）: 利用者が示した修正を当てはめた説明文を、処理に使う文面にした登録の根拠・出典（ガルーラの「こどものおつかい」）。
# kyuura の照合の記録（CC-）・最新の説明（LD-）ではない。v0.68 はエンジンが写しに当てはめていた（USER_PROVIDED_CORRECTIONS）。v0.69 から kyuura が data/cards.json に
# 当てはめた（台帳 data/curation/card_corrections.json の根拠 user_provided の記録。写しの書き出しの ``kyuura_corrections``）。根拠の名前は変えない（利用者が示した訂正）
USER_CORRECTION = "user_provided_correction"
USER_CORRECTION_SOURCE = "kyuura data/cards.json + data/curation/card_corrections.json (user_provided)"
# v0.68（4 章）: エンジンの簡略化した仕様（公式の裁定・エラッタではない）を処理に使う文面にした登録の根拠・出典（イマクニ？のドードー）。文面がその文書の引用（「」）に
# あること・印刷の文面と違うこと・研究の対応表の engine_simplified_text にあることを確かめる
ENGINE_SIMPLIFICATIONS = {"kyuura-engine docs/final-pmcg-cards-v0.68.md#4": ROOT / "docs" / "final-pmcg-cards-v0.68.md"}
# v0.127（docs/deferred-shortage-user-promos-v0.127.md 4 章）: 利用者が指定したエンジン固有の簡略ルール（公式の裁定・最新の説明・エラッタではない）を処理に使う文面にした登録の根拠・出典
# （_のピカチュウの誕生日の条件・ハマちゃんのヤドキングの発話の条件を省く）。根拠の種類を明示的に分け（engine_simplified_text・adopted_printed_text とは別。印刷の文面との不一致を一般に許さない）、
# 対象ごとの記録（effects.USER_SIMPLIFICATIONS）が、カード・対象・印刷の文面（写しと同じ）・処理に使う文面（登録と同じ・印刷と違う）・省いた条件・登録の型の値・指定した主体と日と合うかを照らす
USER_SIMPLIFICATION_SOURCE = "kyuura-engine user simplification docs/deferred-shortage-user-promos-v0.127.md#4"
USER_SIMPLIFICATION_DOCUMENT = ROOT / "docs" / "deferred-shortage-user-promos-v0.127.md"
# v0.129（docs/blaines-quiz-heights-v0.129.md 3 章）: 利用者が指定した参照値（カツラのクイズ その1の正解に、kyuura が集めた公式図鑑の種族の身長を採る）。処理に使う文面は印刷の文面のまま
# （play_text の根拠は kyuura_printed_text）で、採用の記録の ``user_specified_reference``（対象 → 出典）に別に書く。印刷の文面の採用・利用者の簡略ルール・印刷の訂正・最新の説明とは別の
# 記録で、対象ごとの記録（effects.USER_SPECIFIED_REFERENCES）・登録の型の参照の種類・根拠の文書の引用・研究の対応表の user_specified_references と照らす
USER_SPECIFIED_REFERENCE_SOURCE = "kyuura-engine user specification docs/blaines-quiz-heights-v0.129.md#3"
USER_SPECIFIED_REFERENCE_DOCUMENT = ROOT / "docs" / "blaines-quiz-heights-v0.129.md"
# v0.130（docs/trade-please-ownership-v0.130.md 3 章）: 利用者が指定した、説明が書かない処理の規則（とりかえっこプリーズで交換したカードの対戦の中の所有者を、受け取ったプレイヤーに
# する）。処理に使う文面は最新の説明のまま（play_text の根拠は LD-…。文面の区分とは別）で、採用の記録の ``user_specified_rule``（対象 → 出典）に別に書く。公式の裁定・最新の説明・
# 印刷の訂正・利用者の簡略ルール・参照値とは別の記録で、対象ごとの記録（effects.USER_SPECIFIED_RULES）・登録の型の規則の種類・根拠の文書の引用・研究の対応表の user_specified_rules と照らす
USER_SPECIFIED_RULE_SOURCE = "kyuura-engine user specification docs/trade-please-ownership-v0.130.md#3"
USER_SPECIFIED_RULE_DOCUMENT = ROOT / "docs" / "trade-please-ownership-v0.130.md"
RESULTS = ("match", "differences", "edition_not_listed", "inaccessible")
COMPLETED = ("match", "differences")

# 『オフィシャルブック2000』の照合の項目（card_verification.json の項目）。この記録には書かない（読んでいない原典を確かめたことにしない）
GUIDEBOOK_KEYS = {"page", "pdf_page", "scan", "rules_page", "commentary_page", "card_image_text_ja", "latest_description_ja",
                  "power_card_image_text_ja", "power_latest_description_ja", "image_check", "mismatches"}
KYUURA_DATA_KEYS = {"basis", "name_ja", "status", "kyuura_commit", "recorded_on", "kyuura_records", "play_text", "external_checks", "issues"}
GUIDEBOOK_RECORD_KEYS = {"basis", "name_ja", "external_checks"}
# v0.30: 過去の原典照合の記録のあるカードに、照合の記録に処理に使う文面のない登録の根拠（play_text・kyuura_records）を書ける
OPTIONAL_CARD_KEYS = {KYUURA_DATA: {"notes", "equivalent_to", "user_name_correction", "reprint_of", "reprint_scope", "behavior_differs", "user_specified_reference",
                                    "user_specified_rule"},
                      GUIDEBOOK_RECORD: {"issues", "notes", "play_text", "kyuura_records"}}
# v0.70（docs/non-pack-effect-reuse-v0.70.md 3 章）: エンジンが写しの作り直しで当てはめた、利用者が示した名前の訂正（写しの engine_user_corrections。PR1-069 の
# 「？？？」→「ミュウ」）。採用の記録の ``user_name_correction`` に kyuura の値・採用した値・根拠を書き、写しの訂正と照らす（名前の比べ方はほかのカードと同じ。
# 訂正のないカードに書けず、写しの訂正のあるカードには必ず書く）
USER_NAME_CORRECTION_KEYS = {"field", "kyuura", "adopted", "basis", "evidence"}
# v0.69（docs/equivalent-non-pack-cards-v0.69.md 4 章）: 拡張パック以外の商品の、登録したカードと処理に使う欄が同じカード（effects.EQUIVALENT_CARDS）の根拠。採用の記録の
# ``equivalent_to`` が元のカードで、登録は元のカードの登録と同じもの（効果の実装・照合した文面・処理に使う文面・出典）。処理に使う文面の根拠は元のカードの根拠（元のカードの
# 記録・研究の対応表の区分）で、新しいカードの記録としては書き直さない（再録のカードの画像を照合したことにしない）。確かめること: 写しの表と元のカード、元のカードの
# 登録の根拠、登録が同じもの、写しのカードの処理に使う欄（日本語）と同じカードの組（same_card_group）が同じ、研究の対応表の equivalent_registrations
EQUIVALENT = "equivalent_registration"
# v0.71（docs/reprint-text-variants-v0.71.md 3 章）: 再録のカード（effects.REPRINT_CARDS）で、元のカードの記録の最新の説明・エラッタを処理に使う文面にした登録の根拠
# （``play_text`` の値）。登録の処理に使う文面と出典は元のカードの登録と同じで、``reprint_scope`` に、元のカードの出典・その対象の記録の id（研究の対応表の CC-・LD-・
# エラッタ）・過去の原典照合の記録（``card_verification <元のカード>``）・その記録の収録の一覧にこの版の商品があるか（``listed_product``）を書く。再録のカードを照合した
# 記録ではない（元のカードの記録の範囲を当てはめたもの。GR-P43-P6-LATEST-DESCRIPTION と同じカードの組）。元のカードが印刷の文面にしたがう登録・処理が違う登録
# （``behavior_differs``）は、この版の印刷の文面（``kyuura_printed_text``）
REPRINT = "reprint_original_play_text"
REPRINT_SCOPE_KEYS = {"original_source", "records", "verification", "listed_product"}
REPRINT_SCOPE_OPTIONAL = {"scope_quote", "note"}
# 過去の原典照合の記録（card_verification.json の notes の「収録「…」」）での商品の名前（写しの jp_set → 名前）。ここにない商品（プロモ・イントロパックのおまけカード・
# イントロパック★neo（2001 年））は、2000 年の本の収録の一覧にない
REPRINT_PRODUCT_NAMES = {
    "GD1": "ポケモンジム第1弾タケシ", "GD2": "ポケモンジム第1弾カスミ", "GD3": "ポケモンジム第2弾マチス", "GD4": "ポケモンジム第2弾エリカ",
    "GD5": "ポケモンジム第3弾カツラ", "GD6": "ポケモンジム第3弾ナツメ", "QSG": "クイックスターターギフトパック", "IP1": "イントロパック", "IP2": "イントロパック",
}
ENGINE_FIELDS = ("category", "name", "pokemon", "trainer", "energy")
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


def _before_correction(earlier, checked: str, correction: dict) -> bool:
    """照らしたコミット ``checked`` が、kyuura が修正を当てはめた移行の段の前（修正の前の値のコミット）か（v0.97）。連鎖の位置のない古い呼び方（frozenset）では、
    移行の前のコミットならどれも前（v0.69 の 1 段だけの移行と同じ）。"""
    if not isinstance(earlier, MigrationChain):
        return True
    position, before = earlier.position(checked), earlier.position(correction.get("previous_source") or "")
    return position is not None and before is not None and position <= before


def check_problems(where: str, check, card: dict, commit: str, today: datetime.date, corrections: dict | None = None,
                   earlier: frozenset = frozenset()) -> list[str]:
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
    elif check["kyuura_commit"] != commit and check["kyuura_commit"] not in earlier:
        found.append(f"{where}: 照らした kyuura のコミット {check['kyuura_commit'][:7]} が、写しのコミットでも移行の前のコミット（data_migrations）でもない")
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
        # v0.68: 修正した欄は、照らしたデータの値と比べる。v0.69: 移行の前のコミット（ecb2d69）と照らした記録の、kyuura が当てはめた修正（kyuura_corrections）の欄は、
        # 修正の前の値（写しの元の値と照らした記録。ガルーラ）か、修正のあとの値（v0.62〜v0.68 のエンジンが修正を当てはめた写しと照らした記録。ベロリンガ）のどちらか。
        # ほかの欄は写しの値（写しの作り直しの検査が、移行の前と同じことを確かめている）。写しのコミットと照らした記録は写しの値と比べる
        correction = (corrections or {}).get((card.get("id"), difference["field"]))
        allowed = {repr(field_value(card, difference["field"]))}
        if correction and check["kyuura_commit"] in earlier and _before_correction(earlier, check["kyuura_commit"], correction):
            allowed.add(repr(correction["before"]))
        if (check["kyuura_commit"] == commit or check["kyuura_commit"] in earlier) and repr(difference["kyuura"]) not in allowed \
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


def user_simplification_problems(here: str, key: str, entry, card: dict, target: str, links: dict, adopted_printed: set) -> list[str]:
    """v0.127: 根拠が利用者の簡略ルール（``USER_SIMPLIFICATION_SOURCE``）の登録。対象の記録（``effects.USER_SIMPLIFICATIONS``）があり、記録のカード・対象が同じ、印刷の文面が写しと登録の
    ``text_ja`` と同じ、処理に使う文面が登録の ``play_text_ja`` と同じで印刷の文面と違う、省いた条件・処理の説明・利用者の指定がある、指定したのが利用者で日付が方針の開始日から今日まで、
    登録の型が記録の簡略化の種類と値を持つ、処理に使う文面が根拠の文書に引用（「」）されている、研究の対応表の user_simplified_text にあり adopted_printed_text にない。"""
    from kyuura_engine import effects as E

    found = []
    record = E.USER_SIMPLIFICATIONS.get(key)
    if entry.source != USER_SIMPLIFICATION_SOURCE:
        found.append(f"{here}: 根拠が利用者の簡略ルールなのに、出典が {entry.source!r}（{USER_SIMPLIFICATION_SOURCE!r} にする）")
    if record is None:
        return found + [f"{here}: 根拠が利用者の簡略ルールなのに、対象の記録（effects.USER_SIMPLIFICATIONS の {key}）がない"]
    if record.key != key or not record.key.startswith(f"{card['id']}/{target}"):
        found.append(f"{here}: 利用者の簡略ルールの記録のカード・対象 {record.key} が違う")
    if not (record.printed_text == entry.text_ja == printed_text(card, target)):
        found.append(f"{here}: 利用者の簡略ルールの記録の印刷の文面が、写し・登録の照合する文面と違う（kyuura の文面を書き換えない）")
    if record.play_text != entry.play_text_ja or record.play_text == record.printed_text:
        found.append(f"{here}: 利用者の簡略ルールの記録の処理に使う文面が、登録の play_text_ja と違う（または印刷の文面と同じ）")
    if not (record.omitted and record.processing and record.instruction):
        found.append(f"{here}: 利用者の簡略ルールの記録に、省いた条件・実際の処理・利用者の指定がない")
    if record.specified_by != "user" or not (DATE.match(record.specified_on or "") and POLICY["since"] <= record.specified_on <= datetime.date.today().isoformat()):
        found.append(f"{here}: 利用者の簡略ルールの記録の指定した主体 {record.specified_by!r}・日 {record.specified_on!r} が正しくない")
    effect = entry.effect
    # 型の値（bonus・condition）は登録の型から、ダメージの目安（damage）は写しのワザから読む（どれも記録の値と同じ）
    printed_damage = ((card.get("pokemon") or {}).get("attacks") or [{}] * (int(target.split("/")[1]) + 1))[int(target.split("/")[1])].get("damage") if target.startswith("attack/") else None
    actual = {name: ((printed_damage or {}).get("base") if name == "damage" else getattr(effect, name, None)) for name, _ in record.parameters}
    if getattr(effect, "rule", None) != record.rule or actual != dict(record.parameters):
        found.append(f"{here}: 登録の型 {type(effect).__name__} の簡略化の種類・値 {getattr(effect, 'rule', None)}・{actual} が、利用者の簡略ルールの記録（{record.rule}・{record.parameters}）と違う")
    if USER_SIMPLIFICATION_DOCUMENT.exists() and f"「{entry.play_text_ja}」" not in USER_SIMPLIFICATION_DOCUMENT.read_text(encoding="utf-8"):
        found.append(f"{here}: 処理に使う文面が、根拠の文書 {USER_SIMPLIFICATION_DOCUMENT.name} の引用（「」）にない")
    if links["latest_descriptions"].get("user_simplified_text", {}).get(key) != USER_SIMPLIFICATION_SOURCE:
        found.append(f"{here}: 根拠 {USER_SIMPLIFICATION_SOURCE} が研究の対応表の user_simplified_text にない")
    if key in adopted_printed:
        found.append(f"{here}: 研究の対応表の adopted_printed_text にある（根拠は利用者の簡略ルール。印刷の文面の採用と偽らない）")
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
            if correction is None or correction.get("basis") != "user_provided":
                found.append(f"{where} {target}: 根拠 {USER_CORRECTION} なのに、写しにこの欄の利用者が示した訂正（kyuura_corrections の根拠 user_provided）がない")
            elif correction.get("kyuura_saw_image") is not False or correction.get("engine_saw_image") is not False or "record" in correction:
                found.append(f"{where} {target}: 根拠 {USER_CORRECTION} の訂正に、画像を見た・照合の記録がある、と書かれている")
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
        elif basis == USER_SIMPLIFICATION_SOURCE:
            found.extend(user_simplification_problems(f"{where} {target}", key, entry, card, target, links, adopted_printed))
        elif isinstance(basis, str) and basis in ENGINE_RECORDS:
            if entry.source != basis:
                found.append(f"{where} {target}: 根拠が {basis} なのに、出典が {entry.source!r}")
            if entry.play_text_ja == entry.text_ja:
                found.append(f"{where} {target}: 根拠がこのリポジトリの記録の最新の説明なのに、処理に使う文面が印刷の文面と同じ")
            quoted = ENGINE_RECORDS[basis].read_text(encoding="utf-8")
            # v0.87: 特殊能力欄の引用は、誌面のとおり「●名前 文面」の形のことがある（v0.10 の記録の p.138）。名前は登録の名前と同じであること
            if f"「{entry.play_text_ja}」" not in quoted and f"「●{getattr(entry, 'name_ja', None)} {entry.play_text_ja}」" not in quoted:
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
            # v0.126: トレーナーの最新の説明（LD-…-TRAINER）は研究の対応表の registered_trainers に結ぶ（ワザ・特殊能力は registered。フラッシュ ES2-035）
            registered_here = (links["latest_descriptions"].get("registered_trainers", {}).get(card["id"]) if target == "trainer" else registered_ld.get(key))
            if basis.startswith("LD-") and registered_here != basis:
                found.append(f"{where} {target}: 根拠 {basis} が研究の対応表の {'registered_trainers' if target == 'trainer' else 'registered'} にない")
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
                  today: datetime.date, corrections: dict | None = None, earlier: frozenset = frozenset(), sources: dict | None = None,
                  equivalents: dict | None = None, user_corrections: dict | None = None, reprints: dict | None = None) -> list[str]:
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
    if "user_name_correction" in record:
        found.extend(user_name_correction_problems(where, record, card, user_corrections or {}))
    checks = record["external_checks"]
    if not isinstance(checks, list):
        return [*found, f"{where}: external_checks はリスト"]
    for i, check in enumerate(checks):
        found.extend(check_problems(f"{where} の外部照合 {i}", check, card, commit, today, corrections, earlier))
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
    # v0.69: 採用の記録の kyuura_commit は採用したときのデータのコミット（書き換えない）。移行の前のコミット（data_migrations）で採用した記録は、写しの作り直しの検査が
    # 写す欄の同じことを確かめているので、そのまま使う（記録した日・外部照合の確認日を更新しない。採用し直したことにしない）
    if record["kyuura_commit"] != commit and record["kyuura_commit"] not in earlier:
        found.append(f"{where}: 採用したデータのコミット {record['kyuura_commit']!r} が写しのコミット {commit} でも移行の前のコミットでもない")
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
    if "reprint_of" in record or any(v == REPRINT for v in (record.get("play_text") or {}).values()):
        found.extend(reprint_problems(where, record, card, cards=cards, registry=registry, links=links, verification=verification,
                                      sources=sources or {}, reprints=reprints or {}, corrections=corrections))
    elif "equivalent_to" in record or any(v == EQUIVALENT for v in (record.get("play_text") or {}).values()):
        found.extend(equivalent_problems(where, record, card, cards=cards, registry=registry, links=links, verification=verification,
                                         sources=sources or {}, equivalents=equivalents or {}))
    else:
        found.extend(play_text_problems(where, record, card, registry, links, corrections=corrections))
    found.extend(user_specified_reference_problems(where, card_id, record, card, registry, links))
    found.extend(user_specified_rule_problems(where, card_id, record, card, registry, links))
    return found


def user_specified_rule_problems(where: str, card_id: str, record: dict, card: dict, registry, links: dict) -> list[str]:
    """v0.130: 利用者が指定した、説明が書かない処理の規則（``user_specified_rule``。対象 → 出典）。対象ごとの記録（``effects.USER_SPECIFIED_RULES``）のあるカードには必ず書き、ないカードには
    書けない。処理に使う文面は書き換えない（登録の照合の文面と記録の印刷の文面が写しの文面と同じ・登録の処理に使う文面と記録の処理に使う文面が同じ・play_text の根拠が利用者の
    指定ではない）、登録の型の規則の種類が記録と同じ、指定した主体と日・当てはめる場面・規則・範囲・決めないこと・利用者の指定の文（根拠の文書の引用「」）・kyuura の記録の場所・記録しない
    扱い・解決済みにしない論点があり、研究の対応表の user_specified_rules に同じ出典で挙がる。"""
    from kyuura_engine import effects as E

    rules = getattr(E, "USER_SPECIFIED_RULES", {})
    records = {key.split("/", 1)[1]: r for key, r in rules.items() if key.split("/", 1)[0] == card_id}
    value = record.get("user_specified_rule")
    if value is None:
        return [f"{where}: 利用者が指定した規則の記録 {sorted(records)} があるのに user_specified_rule がない"] if records else []
    if not isinstance(value, dict) or set(value) != set(records):
        return [f"{where}: user_specified_rule の対象 {value!r} が、利用者が指定した規則の記録の対象 {sorted(records)} と違う"]
    found = []
    listed = links["latest_descriptions"].get("user_specified_rules", {})
    targets = play_text_targets(registry, card_id)
    document = USER_SPECIFIED_RULE_DOCUMENT.read_text(encoding="utf-8") if USER_SPECIFIED_RULE_DOCUMENT.exists() else ""
    for target, source in value.items():
        here = f"{where} {target}"
        rule = records[target]
        entry = targets.get(target)
        if source != USER_SPECIFIED_RULE_SOURCE:
            found.append(f"{here}: user_specified_rule の出典 {source!r} が {USER_SPECIFIED_RULE_SOURCE!r} ではない")
        if (record.get("play_text") or {}).get(target) in (USER_SPECIFIED_RULE_SOURCE, USER_SPECIFIED_REFERENCE_SOURCE, USER_SIMPLIFICATION_SOURCE):
            found.append(f"{here}: 処理に使う文面の根拠が利用者の指定になっている（規則は文面の区分ではない）")
        if entry is None or not (entry.text_ja == rule.printed_text == printed_text(card, target) and entry.play_text_ja == rule.play_text):
            found.append(f"{here}: 登録の文面・処理に使う文面が、利用者が指定した規則の記録の印刷の文面（写しと同じ）・処理に使う文面と同じではない")
        effect = registry.trainer_entry(card_id).effect if target == "trainer" and registry.trainer_entry(card_id) is not None else None
        if getattr(effect, "ownership_rule", None) != rule.rule:
            found.append(f"{here}: 登録の型の規則の種類 {getattr(effect, 'ownership_rule', None)!r} が記録 {rule.rule!r} と違う")
        if rule.specified_by != "user" or not all((rule.specified_on, rule.applies_to, rule.specification, rule.scope, rule.not_decided, rule.kyuura_record,
                                                   rule.not_recorded_as, rule.kyuura_issue)):
            found.append(f"{here}: 利用者が指定した規則の記録に、指定した主体と日・場面・規則・範囲・決めないこと・kyuura の記録・記録しない扱い・論点がない")
        if f"「{rule.instruction}」" not in document:
            found.append(f"{here}: 利用者の指定の文が、根拠の文書 {USER_SPECIFIED_RULE_DOCUMENT.name} の引用（「」）にない")
        if rule.kyuura_issue not in record.get("kyuura_records", ()):
            found.append(f"{here}: 解決済みにしない論点 {rule.kyuura_issue} が、採用の記録の kyuura_records にない")
        if listed.get(f"{card_id}/{target}") != source:
            found.append(f"{here}: 研究の対応表の user_specified_rules にない")
    return found


def user_specified_reference_problems(where: str, card_id: str, record: dict, card: dict, registry, links: dict) -> list[str]:
    """v0.129: 利用者が指定した参照値（``user_specified_reference``。対象 → 出典）。対象ごとの記録（``effects.USER_SPECIFIED_REFERENCES``）のあるカードには必ず書き、ないカードには書けない。
    処理に使う文面は印刷の文面のまま（play_text の根拠が kyuura_printed_text・登録の照合の文面と処理に使う文面と記録の印刷の文面が写しの文面と同じ）、登録の型の参照の種類が記録と同じ、
    指定した主体と日・利用者の指定の文（根拠の文書の引用「」）・記録しない扱いがあり、研究の対応表の user_specified_references に同じ出典で挙がる。"""
    from kyuura_engine import effects as E

    records = {key.split("/", 1)[1]: r for key, r in E.USER_SPECIFIED_REFERENCES.items() if key.split("/", 1)[0] == card_id}
    value = record.get("user_specified_reference")
    if value is None:
        return [f"{where}: 利用者が指定した参照値の記録 {sorted(records)} があるのに user_specified_reference がない"] if records else []
    if not isinstance(value, dict) or set(value) != set(records):
        return [f"{where}: user_specified_reference の対象 {value!r} が、利用者が指定した参照値の記録の対象 {sorted(records)} と違う"]
    found = []
    listed = links["latest_descriptions"].get("user_specified_references", {})
    targets = play_text_targets(registry, card_id)
    document = USER_SPECIFIED_REFERENCE_DOCUMENT.read_text(encoding="utf-8") if USER_SPECIFIED_REFERENCE_DOCUMENT.exists() else ""
    for target, source in value.items():
        here = f"{where} {target}"
        reference = records[target]
        entry = targets.get(target)
        if source != USER_SPECIFIED_REFERENCE_SOURCE:
            found.append(f"{here}: user_specified_reference の出典 {source!r} が {USER_SPECIFIED_REFERENCE_SOURCE!r} ではない")
        if (record.get("play_text") or {}).get(target) != PRINTED_TEXT:
            found.append(f"{here}: 利用者が指定した参照値の対象の処理に使う文面の根拠が {PRINTED_TEXT} ではない（文面は印刷のまま）")
        if entry is None or not (entry.text_ja == entry.play_text_ja == reference.printed_text == printed_text(card, target)):
            found.append(f"{here}: 登録の文面・処理に使う文面・利用者が指定した参照値の記録の印刷の文面が、写しの文面と同じではない")
        effect = registry.trainer_entry(card_id).effect if target == "trainer" and registry.trainer_entry(card_id) is not None else None
        if getattr(effect, "reference", None) != reference.rule:
            found.append(f"{here}: 登録の型の参照の種類 {getattr(effect, 'reference', None)!r} が記録 {reference.rule!r} と違う")
        if reference.specified_by != "user" or not reference.specified_on or not reference.applies_to or not reference.reference or not reference.not_recorded_as:
            found.append(f"{here}: 利用者が指定した参照値の記録に、指定した主体と日・当てはめる部分・参照値・記録しない扱いがない")
        if f"「{reference.instruction}」" not in document:
            found.append(f"{here}: 利用者の指定の文が、根拠の文書 {USER_SPECIFIED_REFERENCE_DOCUMENT.name} の引用（「」）にない")
        if listed.get(f"{card_id}/{target}") != source:
            found.append(f"{here}: 研究の対応表の user_specified_references にない")
    return found


def user_name_correction_problems(where: str, record: dict, card: dict, user_corrections: dict) -> list[str]:
    """採用の記録の ``user_name_correction`` を、写しの ``engine_user_corrections`` と照らす（v0.70）。"""
    value = record["user_name_correction"]
    if not isinstance(value, dict):
        return [f"{where}: user_name_correction は辞書"]
    found = keys_problems(f"{where} の user_name_correction", value, USER_NAME_CORRECTION_KEYS)
    if found:
        return found
    correction = user_corrections.get((card["id"], "name.ja"))
    if correction is None:
        return [f"{where}: user_name_correction があるのに、写しにこのカードの名前の訂正（engine_user_corrections）がない"]
    if (value["field"], value["kyuura"], value["adopted"], value["basis"]) != ("name.ja", correction["before"], correction["after"], correction["basis"]):
        found.append(f"{where}: user_name_correction が写しの訂正（{correction['before']!r} → {correction['after']!r}・{correction['basis']}）と違う")
    if value["basis"] != "user_provided" or correction.get("engine_saw_image") is not False:
        found.append(f"{where}: 名前の訂正の根拠は利用者が示したもの（user_provided。エンジンは画像を見ていない）")
    if card["name"]["ja"] != value["adopted"] or record["name_ja"] != value["adopted"]:
        found.append(f"{where}: 写し・採用の記録の名前が、採用した値 {value['adopted']!r} ではない")
    return found


def engine_view(card: dict) -> dict:
    """写しのカードの、処理に使う欄（日本語）だけ（v0.69。英語の文面・図鑑番号など処理に使わない欄を除く）。"""
    def ja(value):
        return (value or {}).get("ja") if isinstance(value, dict) else value
    view = {"category": card["category"], "name": card["name"]["ja"]}
    pokemon = card.get("pokemon")
    if pokemon:
        view["pokemon"] = {
            "stage": pokemon["stage"], "evolves_from": ja(pokemon.get("evolves_from")), "hp": pokemon["hp"], "types": pokemon["types"],
            "weaknesses": pokemon["weaknesses"], "resistances": pokemon["resistances"], "retreat_cost": pokemon["retreat_cost"],
            "rules_text": ja(pokemon.get("rules_text")),
            "powers": [{"kind": w.get("kind"), "name": ja(w["name"]), "text": ja(w.get("text"))} for w in pokemon["powers"]],
            "attacks": [{"name": ja(a["name"]), "cost": a["cost"], "damage": a["damage"], "text": ja(a.get("text"))} for a in pokemon["attacks"]],
        }
    trainer = card.get("trainer")
    if trainer:
        view["trainer"] = {"kinds": trainer.get("kinds"), "text": ja(trainer.get("text"))}
    energy = card.get("energy")
    if energy:
        view["energy"] = {"kind": energy["kind"], "provides": energy["provides"], "text": ja(energy.get("text"))}
    return view


def _registrations(registry, card_id: str) -> dict:
    found = {}
    for key in registry.attack_keys():
        if key.card_id == card_id:
            found[f"attack/{key.attack_index}"] = registry.attack_entry(key.card_id, key.attack_index)
    for key in registry.power_keys():
        if key.card_id == card_id:
            found[f"power/{key.power_index}"] = registry.power_entry(key.card_id, key.power_index)
    if card_id in registry.trainer_ids():
        found["trainer"] = registry.trainer_entry(card_id)
    if card_id in registry.energy_ids():
        found["energy"] = registry.energy_entry(card_id)
    return found


def equivalent_problems(where: str, record: dict, card: dict, *, cards: dict, registry, links: dict, verification: dict, sources: dict,
                        equivalents: dict) -> list[str]:
    """v0.69: 登録したカードと処理に使う欄が同じカード（``equivalent_to``）の採用の記録。"""
    from kyuura_engine.effects import EQUIVALENT_CARDS

    found = []
    original = record.get("equivalent_to")
    if record.get("status") != ADOPTED:
        return [f"{where}: equivalent_to は採用（adopted）の記録だけに書く"]
    if not isinstance(original, str) or original not in cards:
        return [f"{where}: equivalent_to {original!r} が写しのカードではない"]
    if EQUIVALENT_CARDS.get(card["id"]) != original:
        found.append(f"{where}: effects.EQUIVALENT_CARDS の元のカードが {EQUIVALENT_CARDS.get(card['id'])!r}（記録は {original}）")
    if equivalents.get(card["id"]) != [original]:
        found.append(f"{where}: 写しの equivalent_targets（kyuura engine_targets.json）の元のカードが {equivalents.get(card['id'])!r}（記録は {original}）")
    if registration_basis(original, verification, sources) is None:
        found.append(f"{where}: 元のカード {original} に登録の根拠（過去の原典照合の記録か採用の記録）がない")
    if engine_view(card) != engine_view(cards[original]):
        found.append(f"{where}: 写しの処理に使う欄が、元のカード {original} と違う")
    if card.get("same_card_group") is None or card.get("same_card_group") != cards[original].get("same_card_group"):
        found.append(f"{where}: 同じカードの組（same_card_group）が元のカード {original} と同じでない")
    mine, theirs = _registrations(registry, card["id"]), _registrations(registry, original)
    if set(mine) != set(theirs) or any(mine[t] is not theirs[t] for t in mine):
        found.append(f"{where}: 登録が元のカード {original} の登録と同じものでない")
    play_text = record.get("play_text")
    expected = set(play_text_targets(registry, card["id"]))
    if not isinstance(play_text, dict) or set(play_text) != expected or any(v != EQUIVALENT for v in play_text.values()):
        found.append(f"{where}: play_text は、処理に使う文面のある登録 {sorted(expected)} のすべてを {EQUIVALENT} にする")
    if record.get("external_checks"):
        found.append(f"{where}: 元のカードと同じとした記録に、外部照合を書かない（元のカードの照合を再利用する。v0.69 では照合していない）")
    section = links["latest_descriptions"].get("equivalent_registrations", {})
    for target, entry in mine.items():
        if (target.startswith(("attack/", "power/")) and getattr(entry, "play_text_ja", None) is not None
                and section.get(f"{card['id']}/{target}") != f"{original}/{target}"):
            found.append(f"{where} {target}: 研究の対応表の equivalent_registrations にない")
    return found


def text_free_view(card: dict) -> dict:
    """``engine_view`` から効果の文面（トレーナーの文面・ワザと特殊能力の説明文）と名前を除いたもの（v0.71。再録のカードの、文面のほかの処理に使う欄の比べ方）。"""
    view = json.loads(json.dumps(engine_view(card), ensure_ascii=False))
    view.pop("name")
    if "trainer" in view:
        view["trainer"]["text"] = None
    for part in ("powers", "attacks"):
        for item in (view.get("pokemon") or {}).get(part, []):
            item["text"] = None
    return view


def reprint_problems(where: str, record: dict, card: dict, *, cards: dict, registry, links: dict, verification: dict, sources: dict,
                     reprints: dict, corrections: dict | None) -> list[str]:
    """v0.71: 再録のカード（``reprint_of``。effects.REPRINT_CARDS）の採用の記録。元のカードとの関係（写しの reprint_targets・同じカードの組・文面と名前のほかの処理に
    使う欄が同じ・元のカードの登録の根拠）、登録が元のカードの登録から決まりどおりに作られていること（効果の実装・照合した文面・処理に使う文面・出典）、処理に使う文面の
    根拠（``reprint_scope``・研究の対応表）を確かめる。"""
    from dataclasses import fields, replace

    from kyuura_engine.deck import same_name
    from kyuura_engine.effects import REPRINT_CARDS

    found = []
    original = record.get("reprint_of")
    reprint = REPRINT_CARDS.get(card["id"])
    if record.get("status") != ADOPTED:
        return [f"{where}: reprint_of は採用（adopted）の記録だけに書く"]
    if not isinstance(original, str) or original not in cards:
        return [f"{where}: reprint_of {original!r} が写しのカードではない"]
    if reprint is None or reprint.original != original:
        return [f"{where}: effects.REPRINT_CARDS の元のカードが {getattr(reprint, 'original', None)!r}（記録は {original}）"]
    if "equivalent_to" in record:
        found.append(f"{where}: 再録の記録に equivalent_to を書かない（v0.69 の処理に使う欄が全部同じカードとは別）")
    if reprints.get(card["id"]) != [original]:
        found.append(f"{where}: 写しの reprint_targets（kyuura engine_targets.json）のいちばん近い登録したカードが {reprints.get(card['id'])!r}（記録は {original}）")
    if registration_basis(original, verification, sources) is None:
        found.append(f"{where}: 元のカード {original} に登録の根拠（過去の原典照合の記録か採用の記録）がない")
    if card.get("same_card_group") is None or card.get("same_card_group") != cards[original].get("same_card_group"):
        found.append(f"{where}: 同じカードの組（same_card_group）が元のカード {original} と同じでない")
    if text_free_view(card) != text_free_view(cards[original]):
        found.append(f"{where}: 写しの文面のほかの処理に使う欄が、元のカード {original} と違う")
    if same_name(card["name"]["ja"]) != same_name(cards[original]["name"]["ja"]):
        found.append(f"{where}: 名前 {card['name']['ja']!r} が元のカード {original} の名前と同じ名前でない（deck.SAME_NAME_SPELLINGS）")
    if record.get("external_checks"):
        found.append(f"{where}: 再録の記録に外部照合を書かない（v0.71 では照合していない）")
    mine, theirs = _registrations(registry, card["id"]), _registrations(registry, original)
    if set(mine) != set(theirs):
        return [*found, f"{where}: 登録の対象 {sorted(mine)} が元のカード {original} の登録 {sorted(theirs)} と違う"]
    behavior = record.get("behavior_differs", [])
    if not isinstance(behavior, list) or set(behavior) != set(reprint.behavior):
        found.append(f"{where}: behavior_differs {behavior!r} が effects.REPRINT_CARDS の処理が違う登録 {sorted(reprint.behavior)} と違う")
    reused, printed = set(), set()
    for target, entry in mine.items():
        base = theirs[target]
        if base.text_ja is None:
            if entry is not base:
                found.append(f"{where} {target}: 説明文のない登録が、元のカードの登録と同じものでない")
            continue
        if entry.text_ja != printed_text(card, target):
            found.append(f"{where} {target}: 登録の印刷の文面（text_ja）が写しの文面と違う")
        if target == "trainer" and entry.name_ja != card["name"]["ja"]:
            found.append(f"{where} {target}: 登録の名前が写しの名前と違う")
        if target in reprint.behavior:
            if entry.effect == base.effect:
                found.append(f"{where} {target}: 処理が違うとした登録の実装が、元のカードと同じ")
            printed.add(target)
            continue
        effect = base.effect
        if any(f.name == "text" for f in fields(effect)):
            effect = replace(effect, text=entry.text_ja)
        if entry.effect != effect:
            found.append(f"{where} {target}: 登録の実装が、元のカードの実装（文面の引数をこの版の文面にしたもの）と違う")
        if base.source == PRINTED_TEXT_SOURCE and base.play_text_ja == base.text_ja:
            printed.add(target)
        else:
            reused.add(target)
            if (entry.play_text_ja, entry.source) != (base.play_text_ja, base.source):
                found.append(f"{where} {target}: 処理に使う文面・出典が、元のカードの登録と違う")
    play_text = record.get("play_text")
    expected = {t: REPRINT for t in reused} | {t: PRINTED_TEXT for t in printed}
    if play_text != expected:
        found.append(f"{where}: play_text {play_text!r} が {expected!r} ではない（元のカードの記録の文面は {REPRINT}、ほかは {PRINTED_TEXT}）")
    elif printed:
        subset = dict(record, play_text={t: PRINTED_TEXT for t in printed})
        found.extend(play_text_problems(where, subset, card, registry, links, expected=printed, corrections=corrections))
    scope = record.get("reprint_scope", {})
    if not isinstance(scope, dict) or set(scope) != reused:
        return [*found, f"{where}: reprint_scope の対象 {sorted(scope) if isinstance(scope, dict) else scope!r} が {sorted(reused)} と違う"]
    section = links["latest_descriptions"]
    for target in sorted(reused):
        here, value = f"{where} {target}", scope[target]
        problems_ = keys_problems(f"{here} の reprint_scope", value, REPRINT_SCOPE_KEYS, REPRINT_SCOPE_OPTIONAL) if isinstance(value, dict) else [f"{here}: reprint_scope は辞書"]
        if problems_:
            found.extend(problems_)
            continue
        key = f"{original}/{target}"
        records = set(links["card_checks"]["engine_verified"].get(original, []))
        if target == "trainer":
            records |= {section.get("registered_trainers", {}).get(original)} - {None}
        else:
            records |= {section["registered"].get(key), section.get("errata_text", {}).get(key)} - {None}
        if value["original_source"] != theirs[target].source:
            found.append(f"{here}: reprint_scope の original_source が元のカードの出典 {theirs[target].source!r} と違う")
        if not records or set(value["records"]) != records:
            found.append(f"{here}: reprint_scope の records {value['records']} が、研究の対応表の元のカードの記録 {sorted(records)} と違う")
        if any(r.split("-")[0] in ("ERR", "TXT", "RUL") for r in records) and not value.get("scope_quote"):
            found.append(f"{here}: エラッタの記録の範囲として当てはめるので、記録の notes の引用（scope_quote）が要る")
        legacy = verification["cards"].get(original)
        if value["verification"] != (f"card_verification {original}" if legacy else None):
            found.append(f"{here}: reprint_scope の verification が {value['verification']!r}（元のカードの過去の原典照合の記録を指す）")
        name = REPRINT_PRODUCT_NAMES.get(card.get("jp_set"))
        listed = name if legacy and name and f"「{name}」" in (legacy.get("notes") or "") else None
        if value["listed_product"] != listed:
            found.append(f"{here}: reprint_scope の listed_product {value['listed_product']!r} が、元のカードの照合の記録の収録の一覧から決まる {listed!r} と違う")
        if target != "trainer" and section.get("reprint_registrations", {}).get(f"{card['id']}/{target}", {}).get("original") != key:
            found.append(f"{here}: 研究の対応表の reprint_registrations にない")
    return found


class MigrationChain(dict):
    """移行の前のコミット → 移行の連鎖での位置（0 が最初の段の前。v0.97）。``in`` で移行の前のコミットか（v0.69 までの frozenset と同じ使い方）、``position`` で
    写しのコミットを含む位置（写しのコミットは段の数）を引く。"""

    def __init__(self, positions: dict[str, int] | None = None, current: str | None = None):
        super().__init__(positions or {})
        self.current = current

    def position(self, commit: str) -> int | None:
        if commit == self.current:
            return len(self)
        return self.get(commit)


def data_migrations(sources: dict, extract: dict) -> tuple[MigrationChain, list[str]]:
    """v0.69: 写しの元を上げた記録（``data_migrations``）。移行の前のコミットの集まりと、問題の一覧。移行の前のコミットは、写しの書き出しの
    ``previous_source``（写しの作り直しの検査が、写す欄が修正の欄と出典の記録の欄を除いて同じことを確かめたコミット）と同じでなければならない。

    v0.97: 移行は連鎖（ecb2d69 → 7d3f4ca → 73a1690）。記録の並びの前・あとのコミットと説明の文書が、写しの書き出しの ``source_migrations``（写しの作り直しの検査が、段ごとに
    写す欄を比べた段）と同じ並びで、最初の段の前が ``previous_source``、段の前がその前の段のあと、最後の段のあとが写しのコミット。過去の段の記録（前・あと・日付）は
    書き換えない（記録の日付は段の並びの順）。移行の前のコミットは、連鎖での位置といっしょに返す（外部照合の照らしたコミットと、修正の段の前後を比べるため）。"""
    migrations = sources.get("data_migrations", [])
    found = []
    current = extract["source"]["commit"]
    if not isinstance(migrations, list):
        return MigrationChain(current=current), ["data_migrations はリスト"]
    positions: dict[str, int] = {}
    steps = [(s.get("from"), s.get("to"), s.get("document")) for s in extract.get("source_migrations") or ()]
    previous = (extract.get("previous_source") or {}).get("commit")
    expected_from = previous
    last_on = None
    for i, migration in enumerate(migrations):
        where = f"data_migrations {i}"
        if not isinstance(migration, dict):
            found.append(f"{where}: 辞書ではない")
            continue
        found.extend(keys_problems(where, migration, {"from", "to", "on", "check", "document"}, {"note"}))
        if migration.get("from") != expected_from:
            found.append(f"{where}: 移行の前のコミットが、" + ("写しの書き出しの previous_source（作り直しの検査で比べたコミット）ではない" if i == 0
                                                       else "前の段の移行のあとのコミットではない（移行の連鎖がつながっていない）"))
        if i >= len(steps) or (migration.get("from"), migration.get("to"), migration.get("document")) != steps[i]:
            found.append(f"{where}: 移行の前・あと・文書が、写しの書き出しの source_migrations の {i} 番目の段と違う")
        if i == len(migrations) - 1 and migration.get("to") != current:
            found.append(f"{where}: 最後の移行のあとのコミットが写しのコミットではない")
        on = migration.get("on")
        if not isinstance(on, str) or (last_on is not None and on < last_on):
            found.append(f"{where}: 移行した日 {on!r} が、前の段の日より前（記録の並びは移行の順）")
        last_on = on if isinstance(on, str) else last_on
        if isinstance(migration.get("from"), str) and COMMIT.match(migration["from"]):
            positions[migration["from"]] = i
        expected_from = migration.get("to")
    if len(migrations) != len(steps):
        found.append(f"data_migrations の段の数 {len(migrations)} が、写しの書き出しの source_migrations の {len(steps)} と違う")
    return MigrationChain(positions, current), found


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
    found = keys_problems("記録", sources, {"format", "description", "policy", "cards"}, {"data_migrations"})
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
    corrections = {(c["card_id"], c["field"]): c for c in extract.get("kyuura_corrections", [])}
    earlier, migration_problems = data_migrations(sources, extract)
    equivalents = {c["id"]: c["equivalent_to"] for c in (extract.get("equivalent_targets") or {}).get("cards", [])}
    user_corrections = {(c["card_id"], c["field"]): c for c in extract.get("engine_user_corrections", [])}
    reprints = {c["id"]: [x["id"] for x in c.get("nearest_registered") or []] for c in (extract.get("reprint_targets") or {}).get("cards", [])}
    found.extend(migration_problems)
    for card_id, record in sources["cards"].items():
        found.extend(card_problems(card_id, record, cards=cards, commit=commit, verification=verification, registry=registry,
                                   links=links, today=today, corrections=corrections, earlier=earlier, sources=sources, equivalents=equivalents,
                                   user_corrections=user_corrections, reprints=reprints))
    from kyuura_engine.effects import REPRINT_CARDS

    for card_id in sorted(set(REPRINT_CARDS) & registered_cards(registry)):  # v0.71: 登録した再録の表のカードは、reprint_of のある採用の記録を持つ
        record = sources["cards"].get(card_id)
        if not (isinstance(record, dict) and record.get("reprint_of") == REPRINT_CARDS[card_id].original):
            found.append(f"{card_id}: effects.REPRINT_CARDS のカードに、元のカード {REPRINT_CARDS[card_id].original} を reprint_of とする採用の記録がない")
    for card_id, field in sorted(user_corrections):  # v0.70: 写しの名前の訂正は、採用の記録の user_name_correction に書く
        record = sources["cards"].get(card_id)
        if field != "name.ja" or not (isinstance(record, dict) and "user_name_correction" in record):
            found.append(f"{card_id}: 写しの利用者が示した訂正（{field}）が、採用の記録の user_name_correction にない")
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
