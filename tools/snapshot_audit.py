"""状態スナップショット（U6）の限定の監査（docs/state-snapshot-v0.157.md 8 章）。自動では実行しない。

選んだテストのモジュールを、``engine._require_integrity``（new_game・apply_command が返す前の確かめ）の位置で保存・復元を試しながら走らせ、保存を拒んだ理由・復元の結果・
スナップショットの最大の深さを数える。コマンドの処理の途中で呼ばれる位置もあるので、保存の境界の外（boundary）の拒否は数えるだけで問題にしない。表せない値・構造の問題・
restored でない復元は、場所（JSON の経路）と一緒に書く。テストの結果は変えない（保存・復元は状態を変えない）。

使い方: ``python -m tools.snapshot_audit tests.test_secret_plan_v0_67 tests.test_markers_counters_v0_90``（リポジトリの根から。重い。全体のテストに使わない）。
既定のカードプールでない効果の登録表（テストで差し替えた登録表）の保存の拒否（effects）は、対応の外として数えるだけで、終了コードを 1 にしない
"""

from __future__ import annotations

import collections
import io
import sys
import time
import unittest

from kyuura_engine import engine as E
from kyuura_engine import snapshot as SN


def run(modules: list[str]) -> dict:
    stats: collections.Counter = collections.Counter()
    gaps: collections.Counter = collections.Counter()
    deepest = 0
    original = E._require_integrity
    busy = False

    def hook(state):
        nonlocal deepest, busy
        original(state)
        if busy:
            return
        busy = True
        try:
            try:
                snapshot = SN.save_snapshot(state)
            except SN.SnapshotSaveError as error:
                stats[f"save:{error.code}"] += 1
                if error.kind != SN.SAVE_BOUNDARY or error.code == "structure":
                    gaps[(error.code, error.path)] += 1
                return
            deepest = max(deepest, SN._depth(snapshot.data))
            report = SN.restore_snapshot(SN.dumps_snapshot(snapshot))
            stats[f"restore:{report.status}"] += 1
            if not report.restored:
                gaps[(report.status, tuple((p.code, p.path) for p in report.problems))] += 1
        finally:
            busy = False

    E._require_integrity = hook
    try:
        started = time.time()
        suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
        result = unittest.TextTestRunner(verbosity=0, stream=io.StringIO()).run(suite)
    finally:
        E._require_integrity = original
    return {"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "seconds": round(time.time() - started, 1),
            "stats": dict(stats), "max_depth": deepest, "gaps": gaps.most_common()}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    report = run(sys.argv[1:])
    for key in ("tests", "failures", "errors", "seconds", "stats", "max_depth"):
        print(f"{key}: {report[key]}")
    for gap, count in report["gaps"]:
        print(count, gap)
    return 1 if report["failures"] or report["errors"] or any(k[0] != "effects" for k, _ in report["gaps"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
