"""配布物（wheel・sdist）の中身を、ソースの木のパッケージのファイルと名前で照らす（v0.165。docs/installation.md）。

    python scripts/check_distribution.py --wheel dist/kyuura_engine-X-py3-none-any.whl --sdist dist/kyuura_engine-X.tar.gz

- 入っているべきもの: ``kyuura_engine`` の下の .py（``__pycache__`` を除く。サブパッケージを含む）と ``data/*.json``。実装の識別（``replay_record.package_files``）が
  数えるファイルと同じ一覧を使う（配布物の欠けは識別の違いにもなる。正規化で隠さない）
- 入っていてはいけないもの: パッケージの外のファイル（tests・docs・scripts・tools・examples・ローカルの設定など）と、パッケージの下の一覧にないファイル
- 件数ではなく名前で照らす。欠け・余りをファイル名で示す。終了コードは問題がなければ 0、あれば 1
- ビルドはしない（配布物を作るのは利用者の環境。``python -m build``）
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import tarfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGE = "kyuura_engine"
# sdist の根に置いてよいもの（パッケージの外）。egg-info は setuptools が作るメタデータ
SDIST_ROOT_FILES = frozenset({"PKG-INFO", "README.md", "pyproject.toml", "setup.cfg", "MANIFEST.in"})
SDIST_METADATA_DIR = f"{PACKAGE}.egg-info/"


def required_files(root: pathlib.Path = ROOT) -> list[str]:
    """配布物に入っているべきパッケージのファイル（``kyuura_engine/…``。辞書順）。実装の識別と同じ数え方。"""
    package = root / PACKAGE
    files = [p for p in package.rglob("*.py") if "__pycache__" not in p.parts] + list((package / "data").glob("*.json"))
    return sorted(f"{PACKAGE}/{p.relative_to(package).as_posix()}" for p in files)


def _compare(present: set[str], required: list[str], outside: list[str], kind: str) -> list[str]:
    problems = [f"{kind}: 欠けている {name}" for name in required if name not in present]
    expected = set(required)
    problems += [f"{kind}: 一覧にないパッケージのファイル {name}" for name in sorted(present) if name not in expected]
    problems += [f"{kind}: パッケージの外のファイル {name}" for name in outside]
    return problems


def wheel_problems(names: list[str], required: list[str]) -> list[str]:
    """wheel の中の名前（zip の項目。ディレクトリの項目を除く）を照らす。"""
    present: set[str] = set()
    outside = []
    for name in names:
        if name.endswith("/"):
            continue
        if name.startswith(f"{PACKAGE}/"):
            present.add(name)
        elif not (name.split("/", 1)[0].startswith(f"{PACKAGE}-") and name.split("/", 1)[0].endswith(".dist-info")):
            outside.append(name)
    return _compare(present, required, sorted(outside), "wheel")


def sdist_problems(names: list[str], required: list[str]) -> list[str]:
    """sdist の中の名前（tar の項目。先頭の ``名前-版/`` を除いて照らす。ディレクトリの項目は呼ぶ側で除く）を照らす。"""
    present: set[str] = set()
    outside = []
    for name in names:
        rest = name.split("/", 1)[1] if "/" in name else ""
        if not rest:
            continue
        if rest.startswith(f"{PACKAGE}/"):
            present.add(rest)
        elif rest not in SDIST_ROOT_FILES and not rest.startswith(SDIST_METADATA_DIR):
            outside.append(rest)
    return _compare(present, required, sorted(outside), "sdist")


def wheel_names(path: pathlib.Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return archive.namelist()


def sdist_names(path: pathlib.Path) -> list[str]:
    with tarfile.open(path) as archive:
        return [member.name for member in archive.getmembers() if not member.isdir()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--wheel", type=pathlib.Path)
    parser.add_argument("--sdist", type=pathlib.Path)
    args = parser.parse_args(argv)
    if args.wheel is None and args.sdist is None:
        parser.error("--wheel か --sdist が必要")
    required = required_files()
    problems = []
    if args.wheel is not None:
        problems += wheel_problems(wheel_names(args.wheel), required)
    if args.sdist is not None:
        problems += sdist_problems(sdist_names(args.sdist), required)
    for problem in problems:
        print(problem)
    print(f"required={len(required)} problems={len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
