"""記録（D の一部）: CN-1 の包み・識別・意味の列・書き出し・マニフェスト（docs/verification-ai-v0.md 5 章・6 章）。

検証者だけが扱う値（完全な記録・seed・方策の記録）を持ちます。方策（``policies``）・行動生成（``actions``）には渡しません。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from kyuura_engine import __version__
from kyuura_engine import diagnostics as D
from kyuura_engine.adapter import HostStoppedError
from kyuura_engine.replay_record import ReplayCollector, current_identity, dumps_record, runtime_identity


class RecordingGame:
    """``ReplayCollector`` を ``adapter.HostedGame`` と同じ形（``state``・``submit``・``failure``）にする包み（CN-1）。

    ``legal_actions.ActionHost`` は包んだ対戦の ``failure`` を読むが、``ReplayCollector``・``view_record.ViewHost`` は ``failure`` を持たない
    （v0.172.0。``tests/test_verification_ai_v0.py`` の CN1Test で確かめた）。この包みは、送った操作の公開の結果（``CommandResult.outcome``）が ``failed``
    なら、その結果を ``failure`` として持ち、それより後の送信を ``HostedGame`` と同じく ``HostStoppedError`` で断る（失敗を隠さない。いつも None を
    返すことはしない）。``ActionHost`` からの送信だけを受ける（別の経路で送らない）。"""

    def __init__(self, collector: ReplayCollector):
        self._collector = collector
        self._failure = None

    @classmethod
    def start(cls, deck0, deck1, seed, *, conventions=None, game_id=None):
        collector, result = ReplayCollector.start(deck0, deck1, seed, conventions=conventions, game_id=game_id, record_rejections=True, include_git=False)
        return (None if collector is None else cls(collector)), result

    @property
    def state(self):
        return self._collector.state

    @property
    def failure(self):
        return self._failure

    def submit(self, command, *, submitter=None, operation_id=None):
        if self._failure is not None:
            raise HostStoppedError("処理できない結果のあとの対戦には、操作を送れない（検証者が調べる）")
        result = self._collector.submit(command, submitter=submitter, operation_id=operation_id)
        if result.outcome == D.FAILED:
            self._failure = result
        return result

    def view(self, viewer):
        return self._collector.view(viewer)

    def last_check(self) -> dict[str, Any]:
        """今の状態の確認値（最後に受理した操作か開始の、収集器が記録した値）。拒否で状態が変わらないことの照合に使う。"""
        data = self._collector.record().data
        accepted = [op for op in data["operations"] if op["outcome"] == D.ACCEPTED]
        return accepted[-1]["check"] if accepted else data["header"]["start"]["check"]

    def record(self):
        return self._collector.record()

    def close(self):
        return self._collector.close()


def identity(engine_commit: str | None) -> dict[str, Any]:
    """エンジンの識別（コミットは呼び出し側が実行の前に取った値。ここで git を呼ばない）。"""
    return {"git_commit": engine_commit, "version": __version__, "implementation": dict(current_identity()), "runtime": runtime_identity()}


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def meaning_sequence(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """操作の列の意味の表現（方策の再実行の比べに使う）。

    1 行は 1 回の試み（入力を作れなかった・check で止めた・送ったもの）。含めるもの: 主体・候補の中身（応答ごとの番号 ``id`` を除く）・入力の意味
    （``actions.meaning_of``）・作れたか・check の結果・送信の結果と断り・拒否のコード。除くもの: 取っ手（``game``・``revision``）・``operation_id``・
    応答ごとの候補と選ぶものの番号・時間。ほかは除かない（差を隠す広い正規化をしない）。"""
    out = []
    for entry in trace:
        if entry.get("type") != "attempt":
            continue
        submit = entry.get("submit") or {}
        check = entry.get("check") or {}
        out.append({
            "actor": entry["actor"],
            "candidate": {k: v for k, v in entry["candidate"].items() if k != "id"},
            "meaning": entry.get("meaning"),
            "build": entry["build"],
            "check_valid": (check.get("response") or {}).get("valid"),
            "check_refusal": ((check.get("response") or {}).get("refusal") or {}).get("code"),
            "outcome": submit.get("outcome"),
            "refusal": (submit.get("refusal") or {}).get("code"),
            "diagnostic_id": (submit.get("verifier") or {}).get("diagnostic_id"),
        })
    return out


def compare_meanings(a: list[dict[str, Any]], b: list[dict[str, Any]], bound: int) -> dict[str, Any]:
    """先頭から ``bound`` 行（2 つの列の短い方まで）を比べる。最初の違いの位置を返す。"""
    n = min(bound, len(a), len(b))
    for i in range(n):
        if canonical(a[i]) != canonical(b[i]):
            return {"compared": i, "equal": False, "first_difference": i, "a": a[i], "b": b[i]}
    return {"compared": n, "equal": True, "first_difference": None}


def correspondence(trace: list[dict[str, Any]], record_data: dict[str, Any]) -> list[str]:
    """操作の記録とエンジンの記録の対応: エンジンに渡った送信（accepted・rejected・failed）が、完全な記録の行と同じ順・同じ operation_id・同じ結果。

    check で止めた試み・ホストの段の refused はエンジンに渡らないので、完全な記録には行がない（操作の記録にだけある）。"""
    sent = [e for e in trace if e.get("type") == "attempt" and (e.get("submit") or {}).get("outcome") in (D.ACCEPTED, D.REJECTED, D.FAILED)]
    rows = record_data["operations"]
    problems = []
    if len(sent) != len(rows):
        problems.append(f"エンジンに渡った送信 {len(sent)} と記録の行 {len(rows)} の数が違う")
    for e, row in zip(sent, rows):
        if e["operation_id"] != row["operation_id"] or e["submit"]["outcome"] != row["outcome"]:
            problems.append(f"試み {e['n']} と記録の seq {row['seq']} が対応しない")
            break
    return problems


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(canonical(row) + "\n")


def write_record(path: Path, record) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_record(record), encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


MANIFEST_NAMES = ("manifest.json", "sha256.json", "MANIFEST.md")


def write_manifest(root: Path) -> dict[str, str]:
    """保存先のすべてのファイル（マニフェスト自身を除く）の sha256 を書く。"""
    files = sorted(p for p in root.rglob("*") if p.is_file() and not (p.parent == root and p.name in MANIFEST_NAMES))
    sums = {p.relative_to(root).as_posix(): sha256_file(p) for p in files}
    write_json(root / "sha256.json", sums)
    runs = sorted({rel.split("/")[2] for rel in sums if rel.startswith(("verifier/runs/", "public/runs/")) and rel.count("/") >= 3})
    write_json(root / "manifest.json", {"tool": "tools.verification_ai.run_v0", "files": len(sums), "runs": runs,
                                       "layout": {"verifier/": "完全な記録・操作の記録・本人向けの記録・診断（検証者だけ）",
                                                  "public/": "seed・デッキの並び・選択の中身を含まない集計だけ"}})
    lines = ["# 検証用 AI の証跡", "", "- `verifier/`: 完全な記録・操作の記録・本人向けの記録・診断（検証者だけが読む）",
             "- `public/`: seed・デッキの並び・選択の中身を含まない集計だけ", "- `sha256.json`: マニフェストの 3 つを除くすべてのファイルの sha256", "",
             f"ファイル {len(sums)} 個。実行: {', '.join(runs)}", ""]
    (root / "MANIFEST.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return sums
