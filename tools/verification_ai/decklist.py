"""明示的なデッキリスト（逐次バッチの計画で、固定デッキの代わりに使う。docs/verification-ai-decklist.md）。

この道具が持つのは、入力の形の厳密な検証・展開の順・確認値の計算だけ。デッキの合法性（枚数・カードの登録・たねの有無など）は判定しない（エンジンの
``kyuura_engine.deck.deck_problems`` に任せる。batch の adapter が計画を作るときと実行の前に当てる）。``kyuura_engine`` を import しない。

形式（``kyuura-vai-decklist/1``。この 5 項目だけ。ほかの項目は拒否）::

    {"format": "kyuura-vai-decklist/1",
     "label": "人が見分けるための名前",
     "source": {"description": "どこから来たリストか（来歴の説明）", "reference": "任意: 文書・コミットなどの参照"},
     "cards": [["PMCG1-058", 4], ["PMCG1-029", 4], ...],
     "content_sha256": "<content_sha256(cards) の値>"}

- ``source`` は来歴の記録で、信頼性・合法性を保証する値ではない
- 展開（``EXPANSION``）: ``cards`` の並びのまま、カード ID を枚数ぶん続けて並べる（``kyuura_engine.deck.expand_decklist`` と同じ規則。固定デッキの展開も同じ）。
  入力の並びを保持し、ID 順へ並べかえない。展開した並びは、同じ seed での初期の山札の切り方の結果に影響する
- ``content_sha256``（``CONTENT_METHOD``）: カード ID の順（コードポイント順）に並べた [ID, 枚数] の並びの sha256。並びに依らない内容の同一性。``label``・``source`` は含めない
- ``expanded_sha256``: 展開した並びの sha256（初期配列の同一性。batch の固定デッキの記録 ``sha256`` と同じ定義）
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

FORMAT = "kyuura-vai-decklist/1"
EXPANSION = "entries-in-order/1"  # cards の並びのまま、各カード ID を枚数ぶん続ける（expand_decklist と同じ）
CONTENT_METHOD = "sorted-id-count-sha256/1"  # カード ID 順の [ID, 枚数] の並びの sha256（並びに依らない）
KEYS = ("format", "label", "source", "cards", "content_sha256")
SOURCE_REQUIRED = ("description",)
SOURCE_OPTIONAL = ("reference",)
# 入力の大きさの上限（壊れた入力・過大な入力を受けないための値で、デッキの規定ではない。60 枚かどうか・同じ名前の枚数は deck_problems が決める）
MAX_FILE_BYTES = 64 * 1024
MAX_ENTRIES = 200
MAX_TOTAL_CARDS = 1000
MAX_LABEL = 80
MAX_TEXT = 500
CARD_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
SHA256 = re.compile(r"[0-9a-f]{64}")


class DecklistError(ValueError):
    """入力の形が違う（デッキの合法性の判定ではない）。"""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def content_sha256(cards) -> str:
    """並びに依らない内容の確認値（カード ID 順の [ID, 枚数]）。"""
    return _sha(sorted([[c, n] for c, n in cards], key=lambda item: item[0]))


def expand(cards) -> list[str]:
    """実行用の並び（``EXPANSION``）。"""
    out: list[str] = []
    for card_id, count in cards:
        out.extend([card_id] * count)
    return out


def expanded_sha256(expanded) -> str:
    """展開した並びの確認値（初期配列の同一性）。"""
    return _sha(list(expanded))


def _text(value, name: str, limit: int, problems: list[str]) -> None:
    if type(value) is not str:
        problems.append(f"{name} は文字列（{type(value).__name__}）")
    elif not value.strip():
        problems.append(f"{name} が空")
    elif len(value) > limit:
        problems.append(f"{name} が {limit} 文字を超える（{len(value)}）")
    elif not value.isprintable():
        problems.append(f"{name} に制御文字・改行がある")


def problems_of(obj) -> list[str]:
    """形の問題（空なら正しい形）。合法性は見ない。"""
    problems: list[str] = []
    if type(obj) is not dict:
        return [f"デッキリストは JSON のオブジェクト（{type(obj).__name__}）"]
    unknown = sorted(set(obj) - set(KEYS))
    missing = [k for k in KEYS if k not in obj]
    if unknown:
        problems.append(f"知らない項目 {unknown}")
    if missing:
        problems.append(f"項目がない {missing}")
    if "format" in obj and obj["format"] != FORMAT:
        problems.append(f"形式 {obj['format']!r} を知らない（{FORMAT} だけ）")
    if "label" in obj:
        _text(obj["label"], "label", MAX_LABEL, problems)
    if "source" in obj:
        source = obj["source"]
        if type(source) is not dict:
            problems.append(f"source はオブジェクト（{type(source).__name__}）")
        else:
            extra = sorted(set(source) - set(SOURCE_REQUIRED) - set(SOURCE_OPTIONAL))
            if extra:
                problems.append(f"source の知らない項目 {extra}")
            for key in SOURCE_REQUIRED:
                if key not in source:
                    problems.append(f"source.{key} がない")
            for key in SOURCE_REQUIRED + SOURCE_OPTIONAL:
                if key in source:
                    _text(source[key], f"source.{key}", MAX_TEXT, problems)
    cards_ok = False
    if "cards" in obj:
        cards = obj["cards"]
        if type(cards) is not list:
            problems.append(f"cards は並び（{type(cards).__name__}）")
        elif not cards:
            problems.append("cards が空")
        elif len(cards) > MAX_ENTRIES:
            problems.append(f"cards の項目が {MAX_ENTRIES} を超える（{len(cards)}）")
        else:
            before = len(problems)
            seen: dict[str, str] = {}
            total = 0
            for i, item in enumerate(cards):
                if type(item) is not list or len(item) != 2:
                    problems.append(f"cards[{i}] は [カード ID, 枚数] の 2 つの並び")
                    continue
                card_id, count = item
                if type(card_id) is not str or not CARD_ID.fullmatch(card_id):
                    problems.append(f"cards[{i}] のカード ID {card_id!r} の形が違う（英数字・「.」「_」「-」、64 文字まで）")
                else:
                    folded = card_id.casefold()
                    if folded in seen:
                        problems.append(f"cards[{i}] のカード ID {card_id!r} が {seen[folded]!r} と重複する（同じカードは 1 項目にまとめる）")
                    else:
                        seen[folded] = card_id
                if type(count) is not int:
                    problems.append(f"cards[{i}] の枚数 {count!r} は整数（{type(count).__name__}）")
                elif count < 1:
                    problems.append(f"cards[{i}] の枚数 {count} は 1 以上")
                else:
                    total += count
            if total > MAX_TOTAL_CARDS:
                problems.append(f"枚数の合計 {total} が入力の上限 {MAX_TOTAL_CARDS} を超える")
            cards_ok = len(problems) == before
    if "content_sha256" in obj:
        value = obj["content_sha256"]
        if type(value) is not str or not SHA256.fullmatch(value):
            problems.append("content_sha256 は 64 桁の小文字の 16 進")
        elif cards_ok and value != content_sha256(obj["cards"]):
            problems.append(f"content_sha256 が cards の内容と違う（計算した値 {content_sha256(obj['cards'])}）")
    return problems


def validate(obj) -> dict[str, Any]:
    """正しい形なら、検証した値の写しを返す。違えば DecklistError。"""
    problems = problems_of(obj)
    if problems:
        raise DecklistError(problems)
    return json.loads(canonical(obj))


def _no_duplicate_keys(pairs):
    keys = [k for k, _ in pairs]
    dup = sorted({k for k in keys if keys.count(k) > 1})
    if dup:
        raise DecklistError([f"JSON のオブジェクトに同じ項目が 2 回ある {dup}"])
    return dict(pairs)


def _no_constant(name):
    raise DecklistError([f"JSON の {name} は受けない"])


def _float(text):
    value = float(text)
    if not math.isfinite(value):
        raise DecklistError([f"JSON の数 {text} は受けない"])
    return value


def parse_bytes(data: bytes) -> dict[str, Any]:
    """ファイルのバイト列を厳密に読む（大きさ・UTF-8・重複キー・NaN）。形の検証まで行う。"""
    if len(data) > MAX_FILE_BYTES:
        raise DecklistError([f"ファイルが {MAX_FILE_BYTES} バイトを超える（{len(data)}）"])
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise DecklistError([f"UTF-8 でない（{error}）"]) from None
    try:
        obj = json.loads(text, object_pairs_hook=_no_duplicate_keys, parse_constant=_no_constant, parse_float=_float)
    except ValueError as error:
        if isinstance(error, DecklistError):
            raise
        raise DecklistError([f"JSON として読めない（{error}）"]) from None
    return validate(obj)


def load_file(path: Path) -> dict[str, Any]:
    """外部ファイルを 1 回だけ読み、内容と入力の記録（ファイル名・バイト数・sha256）を返す。計画に取り込んだあとは、このファイルを読み直さない。"""
    path = Path(path)
    with path.open("rb") as f:
        data = f.read(MAX_FILE_BYTES + 1)
    decklist = parse_bytes(data)
    return {"decklist": decklist, "input": {"file_name": path.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                                            "note": "計画を作ったときに 1 回だけ読んだ。再開ではこのファイルを読まない（計画に取り込んだ内容で動かす）"}}


def describe(decklist: dict[str, Any]) -> dict[str, Any]:
    """計画に書く、合法性を除いた記録（検証済みの値から）。"""
    expanded = expand(decklist["cards"])
    return {"kind": "decklist", "format": decklist["format"], "label": decklist["label"], "source": decklist["source"], "entries": decklist["cards"],
            "content_method": CONTENT_METHOD, "content_sha256": decklist["content_sha256"], "expansion": EXPANSION, "cards": len(expanded),
            "sha256": expanded_sha256(expanded)}
