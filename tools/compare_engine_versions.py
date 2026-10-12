"""2 つの版のエンジンを、同じ入力で動かして比べる（v0.4e。docs/compatibility-v0.4e.md）。標準ライブラリと git だけを使う
（ネットワークは使わない）。

使い方（リポジトリの直下で）::

    python3 tools/compare_engine_versions.py --base 4bd97bf            # 4bd97bf と今の作業ツリー
    python3 tools/compare_engine_versions.py --base 4bd97bf --new HEAD --scenario butterfree --seeds 2
    python3 tools/compare_engine_versions.py --base 4bd97bf --write-fixture tests/fixtures/compat_base_4bd97bf.json \\
        --scenario all --scenario trainers --seeds 2 --steps 150

- 比べる版の ``kyuura_engine`` を、``git archive`` で一時ディレクトリに取り出し（作業ツリーなら、そのまま）、版ごとに別のプロセス
  （``python3 -I tools/compat_driver.py --tree DIR``）で動かす。読み込んだ ``kyuura_engine`` がその木の下にあることを確かめる
  （import のキャッシュが混ざらない）。
- 駆動（tools/compat_driver.py）は、どの版にも同じ操作を送り、1 手ごとの記録（操作・受け付けたか・拒否のコード・状態の指紋
  （形式 8。ログ・乱数の指紋・決定・止めた理由を含む）・乱数の指紋・段階・ログの長さ・形式 1〜8 の書き出し）を作る。
- 比べるのは記録のすべての項目。除くのは効果の登録表の id（``effects``。版の名前）だけ。
- 食い違いがあれば、最初に食い違った手について、両方の版でその手の前の状態・操作・結果・増えたログ・乱数を書き出し、seed・
  デッキ・手の番号とともに報告する（``--report`` の JSON と、``--report`` と同じ場所の ``*.before.json``）。終了コード 1。
- ``--write-fixture``: 基準の版（``--base``）の記録の指紋を、軽い回帰テスト（tests/test_cross_version_compatibility.py）の参照
  データとして書き出す。今の版から作らない（それでは比べたことにならない）。
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
DRIVER = ROOT / "tools" / "compat_driver.py"


def driver_hash() -> str:
    """駆動のソースの指紋（参照データを作った駆動と、今の駆動が同じかを確かめる）。"""
    return hashlib.sha256(DRIVER.read_bytes()).hexdigest()


def prepare_tree(revision: str, workdir: pathlib.Path) -> tuple[pathlib.Path, str]:
    """``revision`` の ``kyuura_engine`` を取り出した木と、コミット id。``worktree`` なら今の作業ツリー（取り出さない）。"""
    if revision == "worktree":
        status = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "kyuura_engine"], capture_output=True, text=True)
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        return ROOT, f"worktree（HEAD {head}{'、kyuura_engine に未コミットの変更あり' if status.stdout.strip() else ''}）"
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", f"{revision}^{{commit}}"],
                            capture_output=True, text=True, check=True).stdout.strip()
    target = workdir / commit[:12]
    target.mkdir(parents=True)
    archive = subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", commit, "kyuura_engine"], capture_output=True, check=True)
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        for member in tar.getmembers():
            if member.name.startswith(("/", "..")) or ".." in pathlib.PurePosixPath(member.name).parts or not (member.isfile() or member.isdir()):
                raise SystemExit(f"取り出せないアーカイブの項目 {member.name}")
        tar.extractall(target, filter="data")
    return target, commit


def run_driver(tree: pathlib.Path, out: pathlib.Path, args, extra=()) -> None:
    command = [sys.executable, "-I", str(DRIVER), "--tree", str(tree), "--out", str(out), *extra]
    for name in args.scenario or ():
        command += ["--scenario", name]
    if args.seeds is not None:
        command += ["--seeds", str(args.seeds)]
    if args.steps is not None:
        command += ["--steps", str(args.steps)]
    subprocess.run(command, check=True, cwd=tree)


def first_difference(old: list[dict], new: list[dict]) -> tuple[int, list[str]] | None:
    """2 つの記録の並びで、最初に食い違った手の位置と、違った項目。同じなら None。"""
    for index in range(max(len(old), len(new))):
        a = old[index] if index < len(old) else None
        b = new[index] if index < len(new) else None
        if a != b:
            fields = ["(記録がない)"] if a is None or b is None else sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
            return index, fields
    return None


def dict_differences(old, new, path="", limit=40) -> list[str]:
    """2 つの書き出し（辞書）の違う場所（最大 ``limit`` 件）。"""
    out: list[str] = []

    def walk(a, b, where):
        if len(out) >= limit:
            return
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(set(a) | set(b), key=str):
                walk(a.get(key, "<なし>"), b.get(key, "<なし>"), f"{where}.{key}")
        elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, f"{where}[{i}]")
        elif a != b:
            out.append(f"{where}: {json.dumps(a, ensure_ascii=False, default=str)[:200]} → {json.dumps(b, ensure_ascii=False, default=str)[:200]}")

    walk(old, new, path)
    return out


def summarize(games: list[dict]) -> Counter:
    counted = Counter()
    for game in games:
        counted["games"] += 1
        for record in game["records"]:
            counted["records"] += 1
            result = record["res"]
            if record["i"] == 0:
                counted["initial_states"] += 1
            elif result == "ok":
                counted["accepted"] += 1
            elif result.startswith("INTERNAL"):
                counted["internal_errors"] += 1
            else:
                counted["rejected"] += 1
                counted[f"rejected:{result.split(':')[1] if ':' in result else result}"] += 1
                if "UNRESOLVED" in result:
                    counted["rejected_unresolved"] += 1
            counted["formats_compared"] += len(record.get("formats", ()))
        last = game["records"][-1]
        counted[f"final_phase:{last.get('phase')}"] += 1
    return counted


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="2 つの版のエンジンを同じ入力で動かして比べる")
    parser.add_argument("--base", default="4bd97bf", help="基準の版（コミット）")
    parser.add_argument("--new", default="worktree", help="比べる版（コミット。既定は今の作業ツリー）")
    parser.add_argument("--scenario", action="append", help="比べる組（省略ですべて。tools/compat_driver.py の SCENARIOS）")
    parser.add_argument("--seeds", type=int, default=None)
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--report", type=pathlib.Path, default=None, help="結果の JSON を書く場所")
    parser.add_argument("--write-fixture", type=pathlib.Path, default=None, help="基準の版の記録の指紋を、参照データとして書く")
    parser.add_argument("--keep", action="store_true", help="取り出した木と記録を消さない")
    args = parser.parse_args(argv)

    workdir = pathlib.Path(tempfile.mkdtemp(prefix="kyuura-compat-"))
    started = time.time()
    try:
        base_tree, base_commit = prepare_tree(args.base, workdir / "trees")
        if args.write_fixture:
            out = workdir / "base.json"
            run_driver(base_tree, out, args)
            data = json.loads(out.read_text())
            from compat_driver import record_digest  # noqa: PLC0415  （tools/ から読む。エンジンは読み込まない）

            fixture = {
                "base_commit": base_commit,
                "driver_sha256": driver_hash(),
                "excluded": ["effects"],
                "how": "python3 tools/compare_engine_versions.py --base " + args.base + " --write-fixture ... "
                       + " ".join(f"--scenario {s}" for s in args.scenario or ()) + (f" --seeds {args.seeds}" if args.seeds else "")
                       + (f" --steps {args.steps}" if args.steps else ""),
                "games": [
                    {"scenario": g["scenario"], "seed": g["seed"], "steps": [[r["i"], r["res"], record_digest(r)] for r in g["records"]]}
                    for g in data["games"]
                ],
            }
            args.write_fixture.write_text(json.dumps(fixture, ensure_ascii=False, indent=0) + "\n")
            print(f"参照データ {args.write_fixture}（基準 {base_commit}、{len(fixture['games'])} 局）")
            return 0

        new_tree, new_commit = prepare_tree(args.new, workdir / "trees")
        old_out, new_out = workdir / "old.json", workdir / "new.json"
        run_driver(base_tree, old_out, args)
        run_driver(new_tree, new_out, args)
        old, new = json.loads(old_out.read_text()), json.loads(new_out.read_text())
        for side, data, tree in (("base", old, base_tree), ("new", new, new_tree)):
            if not pathlib.Path(data["engine_file"]).resolve().is_relative_to(tree.resolve()):
                raise SystemExit(f"{side} の kyuura_engine が {tree} の外から読み込まれた: {data['engine_file']}")
        report = {
            "base": base_commit, "new": new_commit, "base_engine": old["engine_file"], "new_engine": new["engine_file"],
            "excluded": ["effects（効果の登録表の id）"], "summary_base": dict(summarize(old["games"])),
            "summary_new": dict(summarize(new["games"])), "differences": [],
        }
        if [(g["scenario"], g["seed"]) for g in old["games"]] != [(g["scenario"], g["seed"]) for g in new["games"]]:
            raise SystemExit("比べる対戦の並びが違う（駆動の引数を確かめる）")
        for a, b in zip(old["games"], new["games"]):
            found = first_difference(a["records"], b["records"])
            if found is None:
                continue
            index, fields = found
            entry = {"scenario": a["scenario"], "seed": a["seed"], "index": index, "fields": fields,
                     "base_record": a["records"][index] if index < len(a["records"]) else None,
                     "new_record": b["records"][index] if index < len(b["records"]) else None}
            if index > 0:
                dumps = []
                for tree, name in ((base_tree, "base"), (new_tree, "new")):
                    dump = workdir / f"dump-{name}.json"
                    run_driver(tree, dump, argparse.Namespace(scenario=None, seeds=None, steps=args.steps),
                               extra=("--dump", a["scenario"], str(a["seed"]), str(index)))
                    dumps.append(json.loads(dump.read_text()))
                entry["command"] = dumps[0]["record"]["cmd"]
                entry["results"] = [dumps[0]["record"]["res"], dumps[1]["record"]["res"]]
                entry["rng"] = [dumps[0]["record"]["rng"], dumps[1]["record"]["rng"]]
                entry["before_state_differences"] = dict_differences(dumps[0]["before"], dumps[1]["before"])
                entry["after_state_differences"] = dict_differences(dumps[0]["after"], dumps[1]["after"])
                entry["log_added"] = {"base": dumps[0]["log_added"], "new": dumps[1]["log_added"]}
                if args.report:
                    before_path = args.report.with_suffix(f".{a['scenario']}-{a['seed']}-{index}.before.json")
                    before_path.write_text(json.dumps(dumps[0]["before"], ensure_ascii=False, default=str))
                    entry["before_state_file"] = str(before_path)
            report["differences"].append(entry)
        report["seconds"] = round(time.time() - started, 1)
        text = json.dumps(report, ensure_ascii=False, indent=1, default=str)
        if args.report:
            args.report.write_text(text + "\n")
        summary = report["summary_new"]
        print(f"基準 {base_commit} / 比べる版 {new_commit}")
        print(f"対戦 {summary.get('games', 0)}・記録 {summary.get('records', 0)}（受け付けた {summary.get('accepted', 0)}・"
              f"拒否 {summary.get('rejected', 0)}・内部の誤り {summary.get('internal_errors', 0)}）・形式の書き出し {summary.get('formats_compared', 0)}")
        print(f"食い違い {len(report['differences'])} 局（{report['seconds']} 秒）")
        for entry in report["differences"]:
            print(f"- {entry['scenario']} seed {entry['seed']} の {entry['index']} 手目: {entry['fields']}")
            for line in entry.get("after_state_differences", [])[:10]:
                print("    " + line)
        return 1 if report["differences"] else 0
    finally:
        if args.keep:
            print(f"作業ディレクトリ {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "tools"))
    sys.exit(main())
