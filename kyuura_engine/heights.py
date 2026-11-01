"""公式図鑑の種族の身長の参照値（v0.129。docs/blaines-quiz-heights-v0.129.md 2 章・3 章）。

``data/species_heights.json`` は kyuura の ``data/species_heights.json``（固定したコミット）の写しです（``scripts/extract_species_heights.py`` で生成する。手で
編集しない）。実行時に公式サイトへ接続しません。

- 値は公式図鑑の **種族** の身長（全国図鑑 No.001〜251・通常の姿）で、カードに印刷された身長ではありません。カツラのクイズ その1（GD5-016）の正解に使うのは
  利用者の指定です（公式の裁定・最新の説明・印刷の訂正としては扱わない。``effects.USER_SPECIFIED_REFERENCES``）。
- カードとは全国図鑑番号（``CardDefinition.dex``。kyuura の ``pokemon.dex``）だけで対応づけます。名前から所有者名・接頭辞を取り除いて推測したり、欠けた
  図鑑番号を補ったりしません（``card_height``）。
- 名前は公式の表記のまま持ちます（No.233 は「ポリゴン２」）。照合の正規化と、クイズの答えの判定は別の処理です（答えは整数 cm の完全一致）。
- 読み込むときに、番号の一意性・範囲・通常の姿の写しであること・原表記と整数 cm の一致・出典を確かめ、合わなければ ``ValueError`` にします（0cm にしない）。

人向けの答えの入力（``height_answer_cm``）は、単位を明示した文字列（「0.4m」「40cm」）を整数 cm にします。エンジンの決定（``decisions.QUIZ_HEIGHT_ANSWER``）が受け付けるのは
整数 cm だけで、単位の換算はこの関数（または呼ぶ側）の責任です。単位のない数値を m か cm か推測しません。
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cards import CardDefinition

HEIGHTS_PATH = Path(__file__).resolve().parent / "data" / "species_heights.json"
HEIGHTS_FORMAT = "kyuura-engine species heights extract 1"
DEX_FIRST, DEX_LAST = 1, 251
_RAW_HEIGHT = re.compile(r"^(\d+)(?:\.(\d+))?\s?(m|cm)$")
_ANSWER = re.compile(r"^([0-9]+)(?:\.([0-9]+))?\s*(m|cm)$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

# 対応する身長がないカードの理由（エンジンの未対応。研究上の未解決とは別）
HEIGHT_WITHOUT_DEX = "without_dex"  # カードの記録に全国図鑑番号がない
HEIGHT_MULTIPLE_DEX = "multiple_dex"  # カードの記録に全国図鑑番号が 2 つ以上ある（どれの身長かを決めない）
HEIGHT_NOT_AVAILABLE = "not_available"  # 図鑑番号はあるが、写しにその種族の確定した身長がない


@dataclass(frozen=True)
class SpeciesHeight:
    """1 つの種族の身長の参照値（写しの 1 件）。``name_ja`` は公式の表記のまま。"""

    dex: int
    name_ja: str
    height_raw: str
    height_cm: int
    source: str
    url: str
    retrieved_on: str
    extract_sha256: str
    response_sha256: str
    response_bytes: int


@dataclass(frozen=True)
class SpeciesHeights:
    """身長の参照値の写し全体。``by_dex`` は図鑑番号 → 値（確定した値だけ）。``source`` は写しの元（kyuura のコミット・パス・ハッシュ）。"""

    by_dex: Mapping[int, SpeciesHeight]
    unavailable: Mapping[int, str]
    source: Mapping[str, object]
    sources: Mapping[str, Mapping[str, object]]


def raw_height_cm(raw) -> int | None:
    """原表記（「0.7m」「70cm」）を整数 cm にする。十進数のまま読み（浮動小数点を使わない）、整数 cm にならない・0 以下・形が違えば None（丸めない）。"""
    if not isinstance(raw, str):
        return None
    match = _RAW_HEIGHT.match(raw)
    if match is None:
        return None
    return _decimal_cm(match.group(1), match.group(2), match.group(3))


def _decimal_cm(whole: str, fraction: str | None, unit: str) -> int | None:
    try:
        number = Decimal(f"{whole}.{fraction or '0'}")
    except InvalidOperation:
        return None
    cm = number * 100 if unit == "m" else number
    if cm <= 0 or cm != cm.to_integral_value():
        return None
    return int(cm)


def heights_problems(data: dict) -> list[str]:
    """写しの形の検査: 形式・範囲・番号（整数・重ならない・順番・範囲の中）・確定した値と確定していない番号が重ならず範囲をちょうど覆う・通常の姿の写しであること（写しの
    元の姿の方針）・原表記と整数 cm の一致・出典（登録した公式の出典・詳細ページの URL・取得日・ハッシュ）。"""
    problems: list[str] = []
    if data.get("format") != HEIGHTS_FORMAT:
        return [f"形式 {data.get('format')!r} が {HEIGHTS_FORMAT!r} ではない"]
    scope = data.get("scope") or {}
    if (scope.get("dex_first"), scope.get("dex_last")) != (DEX_FIRST, DEX_LAST):
        problems.append(f"範囲 {scope.get('dex_first')!r}〜{scope.get('dex_last')!r} が {DEX_FIRST}〜{DEX_LAST} ではない")
    source = data.get("source") or {}
    for key in ("repository", "commit", "path", "git_blob", "sha256"):
        if not isinstance(source.get(key), str) or not source[key]:
            problems.append(f"写しの元の {key} がない")
    sources = data.get("sources") or {}
    for sid, item in sources.items():
        if item.get("official") is not True or "{dex:04d}" not in str(item.get("detail_url", "")):
            problems.append(f"出典 {sid} が公式の詳細ページの出典ではない")
    species = data.get("species")
    unavailable = data.get("unavailable")
    if not isinstance(species, list) or not isinstance(unavailable, list):
        return problems + ["species・unavailable が並びではない"]
    numbers = [entry.get("dex") for entry in species]
    missing_numbers = [entry.get("dex") for entry in unavailable]
    every = numbers + missing_numbers
    if any(type(n) is not int for n in every):
        return problems + [f"整数でない図鑑番号 {[n for n in every if type(n) is not int]!r}"]
    if len(set(every)) != len(every):
        problems.append(f"図鑑番号が重なる {sorted({n for n in every if every.count(n) > 1})}")
    if numbers != sorted(numbers):
        problems.append("確定した値が図鑑番号の順番ではない")
    if sorted(every) != list(range(DEX_FIRST, DEX_LAST + 1)):
        problems.append(f"図鑑番号が {DEX_FIRST}〜{DEX_LAST} をちょうど覆わない（範囲の外 {sorted(n for n in every if not DEX_FIRST <= n <= DEX_LAST)}・"
                        f"欠け {sorted(set(range(DEX_FIRST, DEX_LAST + 1)) - set(every))}）")
    counts = data.get("counts") or {}
    if (counts.get("species"), counts.get("confirmed"), counts.get("unavailable")) != (len(every), len(numbers), len(missing_numbers)):
        problems.append(f"件数 {counts!r} が中身と合わない")
    for entry in unavailable:
        if entry.get("status") == "confirmed" or set(entry) - {"dex", "status", "status_reason"}:
            problems.append(f"No.{entry.get('dex')}: 値のない種族の記録 {entry!r} が正しくない（値を持たない）")
    for entry in species:
        tag = f"No.{entry['dex']:03d}"
        cm = entry.get("height_cm")
        if type(cm) is not int or cm <= 0 or raw_height_cm(entry.get("height_raw")) != cm:
            problems.append(f"{tag}: 原表記 {entry.get('height_raw')!r} と整数 cm {cm!r} が合わない")
        if not isinstance(entry.get("name_ja"), str) or not entry["name_ja"]:
            problems.append(f"{tag}: 名前がない")
        item = sources.get(entry.get("source"))
        if item is None:
            problems.append(f"{tag}: 出典 {entry.get('source')!r} が登録した公式の出典ではない")
        elif entry.get("url") != str(item.get("detail_url")).format(dex=entry["dex"]):
            problems.append(f"{tag}: URL {entry.get('url')!r} が出典の詳細ページではない")
        if not isinstance(entry.get("retrieved_on"), str) or not _DATE.match(entry["retrieved_on"]):
            problems.append(f"{tag}: 取得日 {entry.get('retrieved_on')!r} の形が正しくない")
        if not all(isinstance(entry.get(k), str) and _HEX64.match(entry[k]) for k in ("extract_sha256", "response_sha256")):
            problems.append(f"{tag}: 抜き出し・応答の sha256 がない")
        if type(entry.get("response_bytes")) is not int or entry["response_bytes"] <= 0:
            problems.append(f"{tag}: 応答のバイト数がない")
    return problems


def parse_heights(data: dict) -> SpeciesHeights:
    problems = heights_problems(data)
    if problems:
        raise ValueError("身長の参照値の写しが正しくない:\n" + "\n".join(problems))
    by_dex = {entry["dex"]: SpeciesHeight(**{key: entry[key] for key in SpeciesHeight.__dataclass_fields__}) for entry in data["species"]}
    return SpeciesHeights(MappingProxyType(by_dex), MappingProxyType({e["dex"]: e["status"] for e in data["unavailable"]}),
                          MappingProxyType(dict(data["source"])), MappingProxyType({k: MappingProxyType(dict(v)) for k, v in data["sources"].items()}))


@lru_cache(maxsize=1)
def load_species_heights() -> SpeciesHeights:
    """同梱の写しを読み、検査して返す（1 回だけ読む）。"""
    return parse_heights(json.loads(HEIGHTS_PATH.read_text(encoding="utf-8")))


def card_height(definition: CardDefinition, heights: SpeciesHeights | None = None) -> tuple[SpeciesHeight | None, str | None]:
    """カードの定義の種族の身長と、ないときの理由（``HEIGHT_WITHOUT_DEX``・``HEIGHT_MULTIPLE_DEX``・``HEIGHT_NOT_AVAILABLE``）。図鑑番号（``definition.dex``）だけで引く
    （名前を読まない）。"""
    heights = heights or load_species_heights()
    if not definition.dex:
        return None, HEIGHT_WITHOUT_DEX
    if len(definition.dex) != 1:
        return None, HEIGHT_MULTIPLE_DEX
    found = heights.by_dex.get(definition.dex[0])
    return (found, None) if found is not None else (None, HEIGHT_NOT_AVAILABLE)


def height_answer_cm(text: str) -> int:
    """人向けの答えの入力（単位を明示した値。「0.4m」「0.4 m」「40cm」）を整数 cm にする（「0.4m」と「40cm」は同じ 40）。全角の数字・単位は NFKC で半角にそろえる。
    十進数のまま換算し（浮動小数点を使わない）、整数 cm にならない値（「0.405m」）・0 以下・単位のない値（「40」「0.4」）・形の違う値は ``ValueError``（m か cm かを
    推測しない）、文字列でない値は ``TypeError``。値の範囲（``decisions.QUIZ_HEIGHT_ANSWER`` の受け付ける範囲）は決定の確かめが見る。"""
    if not isinstance(text, str):
        raise TypeError(f"答え {text!r} が文字列ではない")
    normalized = unicodedata.normalize("NFKC", text).strip()
    match = _ANSWER.match(normalized)
    if match is None:
        raise ValueError(f"答え {text!r} は「数字 + 単位（m・cm）」の形ではない（単位のない数は m か cm か決めない）")
    cm = _decimal_cm(match.group(1), match.group(2), match.group(3))
    if cm is None:
        raise ValueError(f"答え {text!r} は 1 以上の整数 cm にならない")
    return cm
