"""変異試験を実行する（v0.18e）。定義は ``tools/mutants.py``（版管理）。docs/verification-reproducibility-v0.18e.md。

使い方（リポジトリの直下で。どれも作業ツリーは変えない。変異は ``--work`` の下の写しの木に入れる）:

    python3 tools/run_mutants.py check
        定義の検査だけ（速い）: 置きかえる前の文字列がちょうど 1 か所・置きかえたあとが構文として正しい（.py はコンパイル、.json は読める）。
    python3 tools/run_mutants.py witness [ID ...] [--jobs N] [--work DIR] [--out FILE]
        証人のテスト（``WITNESSES``）が元の木で通り、変異を入れた写しで失敗するか（変異が狙った欠陥を起こすか）。
    python3 tools/run_mutants.py full [ID ...] [--jobs N] [--work DIR] [--out FILE]
        ``MODULES`` のテストをすべて走らせ、失敗したテスト（見つけたテスト）を記録する。C 段階（1 つの変異で数分）。ふだんのテストでは走らせない。

結果は 1 つの変異につき 1 行の JSON（``--out``。省略で標準出力）。状態:

- ``not_applied``: 置きかえる前の文字列がちょうど 1 か所にない（数えない）
- ``invalid``: 置きかえたあとが構文として正しくない（見つけた数に入れない）
- ``detected`` / ``survived``（full）: テストが失敗した / すべて通った
- ``witness_failed`` / ``witness_passed``（witness）: 証人のテストがすべて失敗した / 通ったものがある（狙った欠陥を起こしていない）
- ``no_witness``（witness）: 証人のテストが定義にない

``witness``・``full`` は、まず元の木（変異なし）で同じテストを走らせ、すべて通ることを確かめる（結果の最初の行 ``baseline``）。
終了コードは、``check`` で問題があれば 1、``full`` で ``detected`` でない変異があれば 1、``witness`` で ``witness_failed`` でない変異が
あれば 1（元の木でテストが失敗したときも 1）。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.mutants import MODULES, MUTANTS, Mutant  # noqa: E402

FAILED_LINE = re.compile(r"^(FAIL|ERROR): (\S+) \(([^)]+)\)")
IGNORE = shutil.ignore_patterns(".git", "__pycache__", "*.pyc")


def mutated_text(root: Path, mutant: Mutant) -> tuple[str | None, str]:
    """変異を入れたファイルの中身と状態（``ok``・``not_applied``・``invalid``）。"""
    text = (root / mutant.path).read_text(encoding="utf-8")
    if text.count(mutant.old) != 1:
        return None, "not_applied"
    new = text.replace(mutant.old, mutant.new)
    try:
        if mutant.path.endswith(".py"):
            compile(new, mutant.path, "exec")
        elif mutant.path.endswith(".json"):
            json.loads(new)
    except (SyntaxError, ValueError):
        return new, "invalid"
    return new, "ok"


def failing_tests(stderr: str) -> list[str]:
    """unittest の出力から、失敗・誤りになったテストの id（``tests.test_x.Class.test_y``）を返す（subTest は 1 つにまとめる）。"""
    found = []
    for line in stderr.splitlines():
        match = FAILED_LINE.match(line)
        if match:
            test_id = match.group(3)
            if test_id not in found:
                found.append(test_id)
    return found


def run_tests(tree: Path, tests, timeout: int) -> tuple[int, list[str], str]:
    run = subprocess.run([sys.executable, "-m", "unittest", *tests], cwd=tree, capture_output=True, text=True, timeout=timeout)
    tail = run.stderr.strip().splitlines()[-1] if run.stderr.strip() else ""
    return run.returncode, failing_tests(run.stderr), tail


def run_one(mutant: Mutant, mode: str, work: Path, timeout: int) -> dict:
    started = time.time()
    record = {"id": mutant.id, "title": mutant.title, "origin": mutant.origin, "path": mutant.path, "mode": mode}
    new, status = mutated_text(ROOT, mutant)
    if status != "ok":
        record["status"] = status
        return record
    tests = mutant.witnesses if mode == "witness" else MODULES
    if mode == "witness" and not tests:
        record["status"] = "no_witness"
        return record
    copy = work / mutant.id
    if copy.exists():
        shutil.rmtree(copy)
    shutil.copytree(ROOT, copy, ignore=IGNORE)
    try:
        (copy / mutant.path).write_text(new, encoding="utf-8")
        code, failing, tail = run_tests(copy, tests, timeout)
    finally:
        shutil.rmtree(copy, ignore_errors=True)
    record.update({"returncode": code, "failing": failing, "summary": tail, "seconds": round(time.time() - started)})
    if mode == "witness":
        missed = [t for t in tests if t not in failing]
        record["status"] = "witness_failed" if code != 0 and not missed else "witness_passed"
        record["witnesses_not_failing"] = missed
    else:
        record["status"] = "detected" if code != 0 else "survived"
    return record


def select(ids: list[str]) -> list[Mutant]:
    if not ids:
        return list(MUTANTS)
    known = {m.id: m for m in MUTANTS}
    unknown = [i for i in ids if i not in known]
    if unknown:
        raise SystemExit(f"定義にない変異: {unknown}")
    return [known[i] for i in ids]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=("check", "witness", "full"))
    parser.add_argument("ids", nargs="*", help="変異の id（省略ですべて）")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--work", type=Path, default=None, help="写しの木を作る場所（省略で一時ディレクトリ）")
    parser.add_argument("--out", type=Path, default=None, help="結果の JSON Lines（追記。省略で標準出力）")
    parser.add_argument("--timeout", type=int, default=5400)
    args = parser.parse_args(argv)
    mutants = select(args.ids)

    if args.mode == "check":
        problems = 0
        ids = [m.id for m in MUTANTS]
        if len(ids) != len(set(ids)):
            print("変異の id が重なっている")
            problems += 1
        for mutant in mutants:
            _, status = mutated_text(ROOT, mutant)
            if status != "ok":
                problems += 1
            print(f"{mutant.id}\t{status}\t{len(mutant.witnesses)} 証人\t{mutant.title}")
        return 1 if problems else 0

    # 元の木（変異なし）で、走らせるテストがすべて通ることを先に確かめる（通らなければ、変異の結果を数えない）
    tests = sorted({t for m in mutants for t in m.witnesses}) if args.mode == "witness" else list(MODULES)
    started = time.time()
    code, failing, tail = run_tests(ROOT, tests, args.timeout)
    emit({"id": "baseline", "mode": args.mode, "tests": len(tests), "returncode": code, "failing": failing, "summary": tail,
          "seconds": round(time.time() - started)}, args.out)
    if code != 0:
        print("元の木でテストが失敗した（変異の結果を数えない）", file=sys.stderr)
        return 1

    work = args.work or Path(tempfile.mkdtemp(prefix="kyuura-mutants-"))
    work.mkdir(parents=True, exist_ok=True)
    ok = True
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        for record in pool.map(lambda m: run_one(m, args.mode, work, args.timeout), mutants):
            emit(record, args.out)
            expected = "witness_failed" if args.mode == "witness" else "detected"
            ok = ok and record["status"] == expected
    return 0 if ok else 1


def emit(record: dict, out: Path | None) -> None:
    line = json.dumps(record, ensure_ascii=False)
    if out is None:
        print(line, flush=True)
    else:
        with out.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


if __name__ == "__main__":
    sys.exit(main())
