"""実装上の仮定の一覧（docs/implementation-assumptions.json）のための、候補箇所の抽出（読むだけ）。

エンジンの動作・文書・データは変えない。``scripts/check_implementation_assumptions.py`` が使う。

- 対象: ``docs/*.md``（一覧そのものの文書を除く）・``kyuura_engine/**/*.py``・``tests/**/*.py``・``scripts/*.py``（この抽出と検査の 2 つを除く。一覧の台帳のテストも除く）。
- 単位: 行。1 行に複数の語があっても 1 つの候補箇所（``keywords`` に語を並べる）。
- 候補箇所の ID: ``S-`` + (パス, 行の本文を空白で正規化したもの) の sha1 の先頭 12 桁。行番号は ID に入れない
  （行の挿入で ID が変わらない）。同じパスに同じ本文の行が複数あれば、2 つめから ``~2``・``~3`` を付ける。
- 語に当たったことは、その箇所が仮定であることを意味しない。分類は台帳の ``site_dispositions`` が持つ。

キーワードのない固定順序・既定値・フォールバックは、この抽出では見つからない（台帳の ``keywordless_review_scope`` と、``found_by`` が keywordless_review の項目が持つ）。
"""

from __future__ import annotations

import hashlib
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]

KEYWORDS = (
    "実装上の仮定", "実装上の読み方", "採用した仕様", "採用の仕様", "類推", "正規化",
    "結果が同じ", "結果は同じ", "結果が変わらない", "結果は変わらない",
    "後年の資料", "簡略化", "簡略ルール", "利用者指定", "利用者の指定", "利用者が指定",
)
KEYWORD_RE = re.compile("|".join(re.escape(k) for k in KEYWORDS))

EXCLUDED = {
    "docs/implementation-assumptions.md",
    "scripts/implementation_assumptions_scan.py",
    "scripts/check_implementation_assumptions.py",
    "tests/test_implementation_assumptions.py",
}


def surfaces(root: pathlib.Path = ROOT) -> list[pathlib.Path]:
    paths = sorted((root / "docs").glob("*.md"))
    for base in ("kyuura_engine", "tests"):
        paths += sorted(p for p in (root / base).rglob("*.py") if "__pycache__" not in p.parts)
    paths += sorted((root / "scripts").glob("*.py"))
    return [p for p in paths if p.relative_to(root).as_posix() not in EXCLUDED]


def site_id(path: str, text: str) -> str:
    norm = " ".join(text.split())
    return "S-" + hashlib.sha1(f"{path}\n{norm}".encode("utf-8")).hexdigest()[:12]


def scan(root: pathlib.Path = ROOT) -> list[dict]:
    sites = []
    for path in surfaces(root):
        rel = path.relative_to(root).as_posix()
        seen: dict[str, int] = {}
        heading = ""
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if rel.endswith(".md") and line.startswith("#"):
                heading = line.lstrip("#").strip()
            found = sorted(set(KEYWORD_RE.findall(line)), key=KEYWORDS.index)
            if not found:
                continue
            base = site_id(rel, line)
            seen[base] = seen.get(base, 0) + 1
            sid = base if seen[base] == 1 else f"{base}~{seen[base]}"
            sites.append({"id": sid, "path": rel, "line": number, "heading": heading, "keywords": found,
                          "kind": "doc" if rel.endswith(".md") else rel.split("/", 1)[0]})
    return sites


if __name__ == "__main__":
    import collections
    import json
    import sys

    result = scan()
    if "--json" in sys.argv:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
    else:
        by_kind = collections.Counter(s["kind"] for s in result)
        files = collections.Counter(s["path"] for s in result)
        print(f"sites={len(result)} files={len(files)} by_kind={dict(by_kind)}")
