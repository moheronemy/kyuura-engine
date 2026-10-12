#!/usr/bin/env python3
"""kyuura の調査データから、エンジンが使うカードの記録だけを抜き出す。

kyuura（https://github.com/moheronemy/kyuura）がカードデータの正本です。
このスクリプトは、固定したコミットの ``data/cards.json`` を ``git show`` で読み、
対戦で使うカード（v0.1 のたねポケモン・基本エネルギーと、v0.2b・v0.2c のトレーナー）と、
分類のテストに使う参照カードの記録を ``kyuura_engine/data/kyuura_cards.json`` に書き出します。

- kyuura の作業ツリーや履歴は書き換えません（``git show`` で読むだけ）。
- kyuura の checkout がどのコミットにあっても、KYUURA_COMMIT の内容を読みます。
- 記録の値は書き換えずにコピーします。照合の結果はこのファイルではなく
  ``kyuura_engine/data/card_verification.json`` に書きます。

使い方::

    python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura          # 書き出す
    python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura --check  # 差分の確認だけ
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

KYUURA_REPOSITORY = "https://github.com/moheronemy/kyuura"
KYUURA_COMMIT = "ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691"
KYUURA_PATH = "data/cards.json"

# v0.1 の対戦で使うカード（kyuura docs/engine-readiness.md 5章の段階 1 のたねポケモンと基本エネルギー）
POOL_V0_1 = [
    "PMCG1-016",  # ポニータ
    "PMCG1-018",  # ガーディ
    "PMCG1-025",  # ヒトデマン
    "PMCG1-029",  # パウワウ
    "PMCG1-037",  # ビリリダマ
    "PMCG1-052",  # ディグダ
    "PMCG1-053",  # ワンリキー
    "PMCG1-058",  # エビワラー
    "PMCG1-060",  # コラッタ
    "PMCG1-065",  # ミニリュウ
    "PMCG1-097",  # 草エネルギー
    "PMCG1-098",  # 炎エネルギー
    "PMCG1-099",  # 水エネルギー
    "PMCG1-100",  # 雷エネルギー
    "PMCG1-101",  # 超エネルギー
    "PMCG1-102",  # 闘エネルギー
]

# v0.2b で加えたトレーナー（kyuura docs/engine-readiness.md 5章の段階 1 の残り）。
# 『オフィシャルブック2000』p.254 と照合した（kyuura_engine/data/card_verification.json）
POOL_V0_2B = [
    "PMCG1-071",  # きずぐすり
    "PMCG1-073",  # ポケモンいれかえ
    "PMCG1-074",  # マサキ
]

# v0.2c で加えたトレーナー（つけて使うトレーナー）。『オフィシャルブック2000』p.257 と照合した
POOL_V0_2C = [
    "PMCG1-081",  # プラスパワー
]

# v0.2d で加えたポケモン（コインを投げるワザ）。『オフィシャルブック2000』p.231 と照合した。
# v0.2c までは参照カード（「×」のダメージが未対応であることのテスト）だった
POOL_V0_2D = [
    "PMCG1-061",  # ドードー（みだれづき）
]

# v0.2e で加えたトレーナー（相手の番の終わりまでつくトレーナー）。『オフィシャルブック2000』p.257 と照合した
POOL_V0_2E = [
    "PMCG1-079",  # ディフェンダー
]

# 対戦には使わない。未対応のカード・ワザを正しく「未対応」と分類できるかのテストに使う
REFERENCE_ONLY = [
    "PMCG1-011",  # フシギバナ（2進化・ポケモンパワー）
    "PMCG1-014",  # ヒトカゲ（効果のないワザと、効果のあるワザ「ひのこ」を持つ）
    "PMCG1-075",  # いいきずぐすり（実装を登録していないトレーナー）
]

# コピーする項目（kyuura の記録のキー。値は書き換えない）
FIELDS = [
    "id",
    "jp_set",
    "category",
    "name",
    "name_ja_confidence",
    "pokemon",
    "trainer",
    "energy",
    "jp_en_differences",
    "notes",
    "source_ids",
    "ja_text_source",
    "jp_print",
]

# エンジンが対戦の処理に使う項目（それ以外は出典の確認用にコピーしているだけ）
FIELDS_USED_BY_ENGINE = [
    "id",
    "category",
    "name.ja",
    "pokemon.stage",
    "pokemon.hp",
    "pokemon.types",
    "pokemon.weaknesses",
    "pokemon.resistances",
    "pokemon.retreat_cost",
    "pokemon.rules_text",
    "pokemon.powers",
    "pokemon.attacks[].name",
    "pokemon.attacks[].cost",
    "pokemon.attacks[].damage",
    "pokemon.attacks[].text",
    "trainer",
    "energy.kind",
    "energy.provides",
]

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "kyuura_engine" / "data" / "kyuura_cards.json"


def read_kyuura_cards(kyuura: Path) -> dict:
    """固定したコミットの data/cards.json を読む（作業ツリーは見ない）。"""
    result = subprocess.run(
        ["git", "-C", str(kyuura), "show", f"{KYUURA_COMMIT}:{KYUURA_PATH}"],
        check=True,
        capture_output=True,
    )
    return json.loads(result.stdout.decode("utf-8"))


def build_extract(source: dict) -> dict:
    by_id = {card["id"]: card for card in source["cards"]}
    missing = [card_id for card_id in POOL_V0_1 + POOL_V0_2B + POOL_V0_2C + POOL_V0_2D + POOL_V0_2E + REFERENCE_ONLY if card_id not in by_id]
    if missing:
        raise SystemExit(f"kyuura {KYUURA_COMMIT} に次のカードがない: {missing}")
    cards = [{field: by_id[card_id][field] for field in FIELDS} for card_id in POOL_V0_1 + POOL_V0_2B + POOL_V0_2C + POOL_V0_2D + POOL_V0_2E + REFERENCE_ONLY]
    return {
        "format": "kyuura-engine card extract 1",
        "description": (
            "kyuura の data/cards.json から、kyuura-engine が使うカードの記録を抜き出した写し。"
            "カード情報の正本は kyuura。値は書き換えていない。"
            "生成: scripts/extract_kyuura_cards.py（手で編集しない）。"
        ),
        "source": {
            "repository": KYUURA_REPOSITORY,
            "commit": KYUURA_COMMIT,
            "path": KYUURA_PATH,
            "schema_version": source.get("schema_version"),
        },
        "fields_copied": FIELDS,
        "fields_used_by_engine": FIELDS_USED_BY_ENGINE,
        "pool_v0_1": POOL_V0_1,
        "pool_v0_2b": POOL_V0_2B,
        "pool_v0_2c": POOL_V0_2C,
        "pool_v0_2d": POOL_V0_2D,
        "pool_v0_2e": POOL_V0_2E,
        "reference_only": REFERENCE_ONLY,
        "cards": cards,
    }


def render(extract: dict) -> str:
    return json.dumps(extract, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kyuura", type=Path, default=ROOT.parent / "kyuura", help="kyuura の clone（既定: ../kyuura）")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="書き出さずに、既存のファイルと同じか確かめる")
    args = parser.parse_args(argv)

    text = render(build_extract(read_kyuura_cards(args.kyuura)))
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        if current != text:
            print(f"{args.output} は kyuura {KYUURA_COMMIT} から生成した内容と違います", file=sys.stderr)
            return 1
        print(f"{args.output} は kyuura {KYUURA_COMMIT} と一致しています")
        return 0
    args.output.write_text(text, encoding="utf-8")
    print(f"{args.output} を書き出しました（{len(POOL_V0_1)} + {len(POOL_V0_2B)} + {len(POOL_V0_2C)} + {len(POOL_V0_2D)} + {len(POOL_V0_2E)} + {len(REFERENCE_ONLY)} 枚）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
