#!/usr/bin/env python3
"""kyuura の公式図鑑の種族の身長（data/species_heights.json）から、エンジンが使う値を写す（v0.129。docs/blaines-quiz-heights-v0.129.md 2 章）。

kyuura（https://github.com/moheronemy/kyuura）が参照データの正本です。このスクリプトは、固定したコミット（``HEIGHTS_KYUURA_COMMIT``）の
``data/species_heights.json`` を ``git show`` で読み、検査を通った値だけを ``kyuura_engine/data/species_heights.json`` に書き出します。

- kyuura の作業ツリー・履歴は書き換えません（``git show`` で読むだけ）。kyuura の checkout がどのコミットにあっても、固定したコミットの内容を読みます。
- 実行時に公式サイトへ接続しません（このスクリプトも接続しない。kyuura が記録した出典・取得日・ハッシュを写す）。
- 値は書き換えません。名前は公式の表記のまま（No.233 は全角数字の「ポリゴン２」）。照合のための正規化（NFKC）はこのスクリプトでは使いません。
- 写すのは状態が ``confirmed`` の種族だけです。ほかの状態の種族は値を持たず、``unavailable`` に番号と状態だけを残します（0cm にしない）。
- カードとの対応は全国図鑑番号（kyuura の ``pokemon.dex``）だけで、エンジンのカードの写し（``scripts/extract_kyuura_cards.py`` の ``KYUURA_COMMIT``）から読みます。
  このコミットの ``data/cards.json`` が写しの元と同じブロブであることを確かめます（違えば図鑑番号の対応が写しとずれるので止める）。
- カードの写しの元・研究の基準（``KYUURA_COMMIT``。71d1728）は上げていません。この参照データだけを別のコミットに固定します。

使い方::

    python3 scripts/extract_species_heights.py --kyuura ../kyuura          # 書き出す
    python3 scripts/extract_species_heights.py --kyuura ../kyuura --check  # 差分の確認だけ
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from extract_kyuura_cards import KYUURA_COMMIT, KYUURA_PATH, KYUURA_REPOSITORY

# kyuura main の PR #8 のマージ 9242b9b（公式図鑑の種族の身長 No.001〜251 の取得）。木は報告の最後のコミット 59a99fc と同じ（b1fbdfc）
HEIGHTS_KYUURA_COMMIT = "9242b9be89be0f747279f39c11875d1ed61763ec"
HEIGHTS_REPORTED_COMMIT = "59a99fcb9dc414ecbc7e4f5929bc0e34a6776ff6"
HEIGHTS_PATH = "data/species_heights.json"
DEFAULT_OUTPUT = ROOT / "kyuura_engine" / "data" / "species_heights.json"
FORMAT = "kyuura-engine species heights extract 1"
DEX_FIRST, DEX_LAST = 1, 251
OFFICIAL_SOURCES = ("SRC-ZUKAN-JP",)  # 写す出典（kyuura が公式として登録したもの。ほかの id があれば止める）
_RAW_HEIGHT = re.compile(r"^(\d+)(?:\.(\d+))?\s?(m|cm)$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _show(kyuura: Path, commit: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", str(kyuura), "show", f"{commit}:{path}"], check=True, capture_output=True).stdout


def _blob(kyuura: Path, commit: str, path: str) -> str:
    return subprocess.run(["git", "-C", str(kyuura), "rev-parse", f"{commit}:{path}"], check=True, capture_output=True, text=True).stdout.strip()


def _tree(kyuura: Path, commit: str) -> str:
    return subprocess.run(["git", "-C", str(kyuura), "rev-parse", f"{commit}^{{tree}}"], check=True, capture_output=True, text=True).stdout.strip()


def raw_height_cm(raw) -> int | None:
    """身長の原表記（kyuura の ``height.raw``。「0.7m」「70cm」）を整数 cm にする。十進数のまま読み、m は 100 倍。整数 cm にならない・0 以下・形が違えば None
    （丸めない）。"""
    if not isinstance(raw, str):
        return None
    match = _RAW_HEIGHT.match(raw)
    if match is None:
        return None
    number = Decimal(f"{match.group(1)}.{match.group(2) or '0'}")
    cm = number * 100 if match.group(3) == "m" else number
    if cm <= 0 or cm != cm.to_integral_value():
        return None
    return int(cm)


def canonical_sha256(value) -> str:
    """kyuura の ``extract_sha256`` と同じ求め方（``sort_keys``・区切りの空白なし・ASCII にしない JSON の UTF-8 の sha256）。"""
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _is_int(value) -> bool:
    return type(value) is int


def species_problems(data: dict) -> list[str]:
    """写す前の検査: 番号の一意性・範囲・欠け・順番、通常の姿、原表記と整数 cm の一致、出典（公式の登録・URL・取得日・ハッシュ）、状態と値の対応。"""
    problems: list[str] = []
    if data.get("schema_version") != 1:
        problems.append(f"schema_version {data.get('schema_version')!r} が 1 ではない")
    scope = data.get("scope") or {}
    if (scope.get("dex_first"), scope.get("dex_last")) != (DEX_FIRST, DEX_LAST):
        problems.append(f"範囲 {scope.get('dex_first')!r}〜{scope.get('dex_last')!r} が {DEX_FIRST}〜{DEX_LAST} ではない")
    sources = data.get("sources") or {}
    if sorted(sources) != sorted(OFFICIAL_SOURCES):
        problems.append(f"出典 {sorted(sources)} が {list(OFFICIAL_SOURCES)} ではない（新しい出典を写すときは、このスクリプトの扱いを決め直す）")
    for sid, source in sources.items():
        if source.get("official") is not True or not source.get("detail_url") or "{dex:04d}" not in source.get("detail_url", "") or source.get("height_unit") != "m":
            problems.append(f"出典 {sid} が公式の詳細ページ・単位 m の出典として登録されていない")
    species = data.get("species")
    if not isinstance(species, list):
        return problems + ["species が並びではない"]
    numbers = [entry.get("dex") for entry in species]
    if any(not _is_int(n) for n in numbers):
        problems.append(f"整数でない図鑑番号 {[n for n in numbers if not _is_int(n)]!r}")
        return problems
    if len(set(numbers)) != len(numbers):
        problems.append(f"図鑑番号が重なる {sorted({n for n in numbers if numbers.count(n) > 1})}")
    if numbers != sorted(numbers):
        problems.append("図鑑番号の順番ではない")
    outside = [n for n in numbers if not DEX_FIRST <= n <= DEX_LAST]
    if outside:
        problems.append(f"範囲の外の図鑑番号 {outside}")
    missing = sorted(set(range(DEX_FIRST, DEX_LAST + 1)) - set(numbers))
    if missing:
        problems.append(f"欠けた図鑑番号 {missing}（補わない）")
    for entry in species:
        problems += entry_problems(entry, sources)
    return problems


def entry_problems(entry: dict, sources: dict) -> list[str]:
    dex = entry["dex"]
    tag = f"No.{dex:03d}"
    status = entry.get("status")
    height = entry.get("height")
    if status != "confirmed":
        if height is not None or entry.get("name_ja") is not None:
            return [f"{tag}: 状態 {status!r} なのに名前・身長の値がある（値を持つのは confirmed だけ）"]
        return []
    problems: list[str] = []
    name = entry.get("name_ja")
    if not isinstance(name, str) or not name:
        problems.append(f"{tag}: 名前がない")
    form = entry.get("form") or {}
    if (form.get("kind"), form.get("source_form_id"), form.get("form_name")) != ("default", 0, None):
        problems.append(f"{tag}: 通常の姿（kind default・姿の番号 0・姿の名前なし）ではない {form!r}")
    if not isinstance(height, dict):
        return problems + [f"{tag}: 身長がない"]
    cm = height.get("cm")
    if not _is_int(cm) or cm <= 0 or raw_height_cm(height.get("raw")) != cm:
        problems.append(f"{tag}: 原表記 {height.get('raw')!r} と整数 cm {cm!r} が合わない")
    if height.get("source") not in sources:
        problems.append(f"{tag}: 身長の出典 {height.get('source')!r} が登録した公式の出典ではない")
        return problems
    observations = [o for o in entry.get("observations") or () if o.get("source") == height["source"]]
    if len(observations) != 1:
        return problems + [f"{tag}: 出典 {height['source']} の観測が 1 件ではない（{len(observations)} 件）"]
    o = observations[0]
    if o.get("url") != sources[height["source"]]["detail_url"].format(dex=dex):
        problems.append(f"{tag}: 観測の URL {o.get('url')!r} が出典の詳細ページではない")
    if not isinstance(o.get("retrieved_on"), str) or not _DATE.match(o["retrieved_on"]):
        problems.append(f"{tag}: 取得日 {o.get('retrieved_on')!r} の形が正しくない")
    for key in ("extract_sha256", "response_sha256"):
        if not isinstance(o.get(key), str) or not _HEX64.match(o[key]):
            problems.append(f"{tag}: {key} がない・形が正しくない")
    if not _is_int(o.get("response_bytes")) or o["response_bytes"] <= 0:
        problems.append(f"{tag}: response_bytes が正しくない")
    if (o.get("name_ja"), o.get("raw_height"), o.get("cm"), o.get("source_form_id"), o.get("form_name")) != (name, height.get("raw"), cm, 0, None):
        problems.append(f"{tag}: 観測の値（名前・原表記・cm・姿）が採った値と合わない")
    extract = o.get("extract") or {}
    if canonical_sha256(extract) != o.get("extract_sha256"):
        problems.append(f"{tag}: 抜き出しの sha256 が合わない")
    if (extract.get("no"), extract.get("sub"), extract.get("name"), extract.get("takasa"), extract.get("form_name")) != (dex, 0, name, height.get("raw"), ""):
        problems.append(f"{tag}: 抜き出し {extract!r} が観測の値と合わない")
    return problems


def build_extract(kyuura: Path, raw: bytes, data: dict) -> dict:
    sources = data["sources"]
    copied = []
    unavailable = []
    for entry in data["species"]:
        if entry["status"] != "confirmed":
            unavailable.append({"dex": entry["dex"], "status": entry["status"], "status_reason": entry.get("status_reason")})
            continue
        o = next(o for o in entry["observations"] if o["source"] == entry["height"]["source"])
        copied.append({
            "dex": entry["dex"],
            "name_ja": entry["name_ja"],
            "height_raw": entry["height"]["raw"],
            "height_cm": entry["height"]["cm"],
            "source": entry["height"]["source"],
            "url": o["url"],
            "retrieved_on": o["retrieved_on"],
            "extract_sha256": o["extract_sha256"],
            "response_sha256": o["response_sha256"],
            "response_bytes": o["response_bytes"],
        })
    keep = ("name_ja", "publisher", "official", "base_url", "detail_url", "robots_url", "height_unit", "access_log")
    return {
        "format": FORMAT,
        "description": ("公式図鑑の種族の身長（全国図鑑 No.001〜251・当時に対応する通常の姿）の写し。kyuura data/species_heights.json の confirmed の値だけ。カードに印刷された"
                        "身長ではない。カツラのクイズ その1（GD5-016）の正解の参照値として使うのは利用者の指定（docs/blaines-quiz-heights-v0.129.md 3 章。公式の裁定・最新の説明・"
                        "印刷の訂正ではない）。カードとは全国図鑑番号（写しの pokemon.dex）だけで対応づける。scripts/extract_species_heights.py で生成する（手で編集しない）"),
        "source": {
            "repository": KYUURA_REPOSITORY,
            "commit": HEIGHTS_KYUURA_COMMIT,
            "tree": _tree(kyuura, HEIGHTS_KYUURA_COMMIT),
            "reported_commit": HEIGHTS_REPORTED_COMMIT,
            "path": HEIGHTS_PATH,
            "git_blob": _blob(kyuura, HEIGHTS_KYUURA_COMMIT, HEIGHTS_PATH),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "schema_version": data["schema_version"],
            "card_data": {"path": KYUURA_PATH, "git_blob": _blob(kyuura, HEIGHTS_KYUURA_COMMIT, KYUURA_PATH), "same_as_commit": KYUURA_COMMIT},
        },
        "scope": {"dex_first": DEX_FIRST, "dex_last": DEX_LAST, "form_policy": data["scope"]["form_policy"]},
        "sources": {sid: {key: source[key] for key in keep if key in source} for sid, source in sources.items()},
        "counts": {"species": len(data["species"]), "confirmed": len(copied), "unavailable": len(unavailable)},
        "unavailable": unavailable,
        "species": copied,
    }


def render(extract: dict) -> str:
    return json.dumps(extract, ensure_ascii=False, indent=1) + "\n"


def source_problems(kyuura: Path) -> list[str]:
    """固定したコミットの関係: 報告の最後のコミットと木が同じ、カードのデータが写しの元（KYUURA_COMMIT）と同じブロブ。"""
    problems = []
    if _tree(kyuura, HEIGHTS_KYUURA_COMMIT) != _tree(kyuura, HEIGHTS_REPORTED_COMMIT):
        problems.append(f"{HEIGHTS_KYUURA_COMMIT[:7]} と報告のコミット {HEIGHTS_REPORTED_COMMIT[:7]} の木が違う")
    if _blob(kyuura, HEIGHTS_KYUURA_COMMIT, KYUURA_PATH) != _blob(kyuura, KYUURA_COMMIT, KYUURA_PATH):
        problems.append(f"{HEIGHTS_KYUURA_COMMIT[:7]} の {KYUURA_PATH} が写しの元 {KYUURA_COMMIT[:7]} と違う（図鑑番号の対応がずれる）")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kyuura", type=Path, default=ROOT.parent / "kyuura", help="kyuura の clone（既定: ../kyuura）")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="書き出さずに、既存のファイルと同じか確かめる")
    args = parser.parse_args(argv)

    raw = _show(args.kyuura, HEIGHTS_KYUURA_COMMIT, HEIGHTS_PATH)
    data = json.loads(raw.decode("utf-8"))
    problems = source_problems(args.kyuura) + species_problems(data)
    if problems:
        print("kyuura の身長のデータを写せない:\n" + "\n".join(problems), file=sys.stderr)
        return 1
    text = render(build_extract(args.kyuura, raw, data))
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        if current != text:
            print(f"{args.output} は kyuura {HEIGHTS_KYUURA_COMMIT} から生成した内容と違います", file=sys.stderr)
            return 1
        print(f"{args.output} は kyuura {HEIGHTS_KYUURA_COMMIT} と一致しています")
        return 0
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(f"{args.output} を書き出しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
