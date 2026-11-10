"""上限つきの逐次バッチ（docs/verification-ai-batch.md）。既存の単局ランナー・方策・行動生成・judge・記録をそのまま使い、新しく持つ責任は次の 5 つだけ。

1. 実行計画を読む（``plan.json``。既定値も展開して保存し、計画自体の sha256 を ``plan.sha256`` に書く）
2. 1 局ずつ順に、同じプロセスで直接実行する（並列・分散・常駐・プロセスの起動・検索・終了はしない）
3. 各局を attempt ごとの別ディレクトリへ確定保存する（各ファイルは同じディレクトリの一時ファイルから ``os.replace``。ハッシュの表を書き、読み直して照合し、最後に ``COMPLETE.json``）
4. 完了局を照合して再開する（計画・実装識別・局の設定・必須ファイル・ハッシュ。正常な完了局は再実行しない。未完了の attempt は残し、別の attempt として最初から）
5. 保存済みの局から集計する（``aggregate``。対戦をやり直さない）

    python -m tools.verification_ai.batch plan --out <証跡> --batch <名前> --engine-commit <sha> --tool-commit <sha> --seeds 1001 1002 ... --modes uniform-stage rules-v2 mixed
    python -m tools.verification_ai.batch run --out <証跡> --batch <名前> [--stop-after-games N] [--acknowledge-stop <game_id> ...]
    python -m tools.verification_ai.batch aggregate --out <証跡> --batch <名前>
    python -m tools.verification_ai.batch unlock --out <証跡> --batch <名前> --session <ロックのセッション ID>

方策（``policies``）・行動生成（``actions``）には、この道具の値（計画・台帳・ロック）を渡さない。方策の順位・反復の抑制・乱数の消費は変えない。
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import socket
import statistics
import sys
import time
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PLAN_FORMAT = "kyuura-vai-batch-plan/1"
COMPLETE_FORMAT = "kyuura-vai-batch-complete/1"
TOOL_NAME = "tools.verification_ai.batch"
TOOL_VERSION = 1

# 方式（計画を作るときだけ使う。計画には Config の全項目を展開して書くので、ここを後で変えても既存の計画の局は変わらない）
MODES: dict[str, dict[str, Any]] = {
    "uniform-stage": {"policy": "uniform", "distribution": "uniform-candidate+uniform-stage"},
    "uniform-tuple": {"policy": "uniform", "distribution": "uniform-candidate+uniform-tuple"},
    "rules-v1": {"policy": "rules", "rules_version": 1},
    "rules-v2": {"policy": "rules", "rules_version": 2, "repeat_threshold": 2},
    "mixed": {"policy": "mixed", "rules_version": 2, "epsilon": 0.25, "repeat_threshold": 2},
}

# 局の終わり方（runner の分類）と停止方針。KeyboardInterrupt・SystemExit・MemoryError は分類に入らない（対戦の結果に変えない）
CONTINUE_TERMINATIONS = ("game_over", "halted_known", "input_unavailable", "no_progress", "api_contract_unknown",
                         "limit_operations", "limit_accepted", "limit_turns", "limit_time")
STOP_TERMINATIONS = ("halted_unclassified", "failed", "state_integrity", "exception", "inconsistency", "start_rejected", "negative_side_effect")
REQUIRED_FILES = ("header.json", "trace.jsonl", "actors/0.jsonl", "actors/1.jsonl", "actors/host.jsonl", "full_record.json", "result.json",
                  "verification.json", "judge.json", "sequences.json")
TABLE = "files.sha256.json"
MARKER = "COMPLETE.json"
NOTE = "INCOMPLETE.json"
LOCK = "LOCK"
LEDGER = "ledger.jsonl"
MB = 1 << 20


@dataclass(frozen=True)
class BatchLimits:
    """バッチ全体の上限。単局の上限は各局の ``config.limits``（runner.Limits の既定 = V0〜V3 と同じ）。

    - ``max_games``: 計画の局数の上限（計画を作るときに確かめる）
    - ``budget_seconds``: 累積の実行時間（セッションごとの単調時計の合計。再開で戻さない）
    - ``game_reserve_seconds``: 次の局を始める条件（残りがこれ以上）。終わりのないセッションに課す見込みの秒にも使う
    - ``evidence_max_bytes``・``evidence_reserve_bytes``: バッチのディレクトリの量の上限と、次の局を始める条件（残りがこれ以上）
    - ``max_attempts_per_game``: 1 局の attempt の数の上限（未完了の attempt も数える）"""

    max_games: int = 30
    budget_seconds: float = 600.0
    game_reserve_seconds: float = 150.0
    evidence_max_bytes: int = 800 * MB
    evidence_reserve_bytes: int = 64 * MB
    max_attempts_per_game: int = 3


@dataclass(frozen=True)
class StopPolicy:
    """停止方針（実行の前に計画へ保存する）。``stop`` は止める・``continue`` は数えて続ける。"""

    continue_terminations: tuple = CONTINUE_TERMINATIONS
    stop_terminations: tuple = STOP_TERMINATIONS
    on_unknown_termination: str = "stop"
    on_suspect: str = "stop"
    on_undetermined: str = "continue"
    on_anomaly: str = "stop"
    on_verification_problem: str = "stop"  # replay_run の期待との不一致・記録の対応の問題


@dataclass
class GameOutput:
    """1 局の出力（adapter が返す）。``files`` は (attempt のディレクトリからの相対パス, バイト列)。``summary`` は COMPLETE.json に入る小さな値。"""

    files: list
    summary: dict[str, Any]


class BatchRefused(Exception):
    """計画・識別・保存内容の照合の不一致など、バッチを始めない（黙って採用・再実行しない）。"""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


class LockHeld(BatchRefused):
    """同じ出力先にロックがある（二重起動か、前のセッションの残り。PID で自動解除しない）。"""


# ---------------------------------------------------------------- 小さな道具


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def json_bytes(value) -> bytes:
    """records.write_json と同じ形（indent 1・sort_keys・LF）。"""
    return (json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8")


def jsonl_bytes(rows) -> bytes:
    return "".join(canonical(r) + "\n" for r in rows).encode("utf-8")


def atomic_write(path: Path, data: bytes) -> None:
    """同じディレクトリの一時ファイルに書き、flush・fsync のあと ``os.replace`` で置きかえる（同じファイルシステム）。

    書き込みの途中で止まると、一時ファイル（``.<名前>.tmp-…``）が残り、目的のファイルは前のまま（なければないまま）。ディレクトリの fsync は Windows ではできないので、
    置きかえの永続化は OS に任せる（完了の判断はファイルの存在でなく、COMPLETE.json とハッシュの照合で行う）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex[:12]}")
    with open(tmp, "xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def tree_bytes(root: Path) -> int:
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file()) if root.exists() else 0


def process_memory() -> dict[str, Any]:
    """このプロセスの使用量（自分のプロセスだけ。ほかのプロセスは調べない）。取れない環境では未計測。"""
    try:
        if sys.platform == "win32":
            class Counters(ctypes.Structure):
                _fields_ = [("cb", ctypes.c_uint32), ("PageFaultCount", ctypes.c_uint32), ("PeakWorkingSetSize", ctypes.c_size_t),
                            ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
            counters = Counters()
            counters.cb = ctypes.sizeof(Counters)
            kernel32 = ctypes.WinDLL("kernel32")
            kernel32.GetCurrentProcess.restype = ctypes.c_void_p
            ok = kernel32.K32GetProcessMemoryInfo(ctypes.c_void_p(kernel32.GetCurrentProcess()), ctypes.byref(counters), counters.cb)
            if not ok:
                return {"status": "not_measured", "reason": "K32GetProcessMemoryInfo failed"}
            return {"status": "measured", "source": "K32GetProcessMemoryInfo", "working_set_bytes": counters.WorkingSetSize,
                    "peak_working_set_bytes": counters.PeakWorkingSetSize, "private_bytes": counters.PagefileUsage}
        import resource  # POSIX だけ

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return {"status": "measured", "source": "getrusage", "peak_rss": peak, "unit": "bytes" if sys.platform == "darwin" else "KiB"}
    except Exception as error:  # 計測できないことは失敗にしない
        return {"status": "not_measured", "reason": f"{type(error).__name__}: {error}"}


def tool_digest() -> dict[str, Any]:
    """この道具（tools/verification_ai の .py）のファイルの sha256 の要約。計画と実行で同じでなければ実行しない。"""
    base = Path(__file__).resolve().parent
    files = sorted(p for p in base.glob("*.py"))
    h = hashlib.sha256()
    for p in files:
        h.update(p.name.encode() + b"\0" + sha256_file(p).encode() + b"\n")
    return {"method": "tools-verification-ai-py-sha256/1", "files": len(files), "digest": h.hexdigest()}


# ---------------------------------------------------------------- adapter（既存の部品への橋。テストでは偽物に置きかえる）


class EngineAdapter:
    """本物の対戦（runner.run_game）・replay_run（run_v1.check_record）・judge を使う。"""

    def __init__(self, engine_commit: str | None = None):
        self.engine_commit = engine_commit

    def identity(self) -> dict[str, Any]:
        from . import records as R

        ident = R.identity(None)
        return {"tool": {"name": TOOL_NAME, "version": TOOL_VERSION, **tool_digest()},
                "engine": {"version": ident["version"], "implementation": ident["implementation"], "runtime": ident["runtime"]}}

    def conventions_key(self, conventions: str | None) -> tuple[str, dict[str, Any]]:
        from kyuura_engine import conventions as C

        identity = C.resolve_for_new_game(conventions)
        return f"{identity.set_id}@{identity.version}", identity.record()

    def deck_check(self, name: str) -> dict[str, Any]:
        from kyuura_engine import preset_deck

        cards = list(preset_deck(name).cards())
        return {"preset": name, "cards": len(cards), "sha256": sha256_bytes(canonical(cards).encode())}

    def policies_of(self, config) -> dict[str, Any]:
        from .runner import HOST, make_policies

        out = {}
        for actor, p in make_policies(config).items():  # 作るだけ（乱数を引かない）
            item = {"name": p.name, "version": p.version, "distribution": p.distribution, "seed": p.seed}
            for attr in ("epsilon", "mix_seed", "rules_version", "threshold"):
                if getattr(p, attr, None) is not None:
                    item[attr] = getattr(p, attr)
            if getattr(p, "memory", None) is not None:
                item["demote_after"] = p.memory.demote_after
            out["host" if actor == HOST else str(actor)] = item
        return out

    def entry(self, *, game_id: str, mode: str, seed: int, deck0: str, deck1: str, conventions: str | None, group: str,
              game_limits: dict[str, Any] | None = None) -> dict[str, Any]:
        from .runner import Config, Limits

        key, conv_record = self.conventions_key(conventions)
        options = MODES[mode]
        config = Config(deck0=deck0, deck1=deck1, conventions=key, game_seed=seed, policy_seed=seed, host_seed=seed, limits=Limits(**(game_limits or {})),
                        run_id=game_id, **options)
        expanded = asdict(config)
        expanded["decklists"] = None
        return {"game_id": game_id, "mode": mode, "comparison_group": group, "config": expanded,
                "decks": {"0": self.deck_check(deck0), "1": self.deck_check(deck1)},
                "conventions": {"key": key, "digest": conv_record["digest"]}, "policies": self.policies_of(config)}

    def config_of(self, entry: dict[str, Any]):
        from .runner import Config, Limits

        c = dict(entry["config"])
        c["limits"] = Limits(**c["limits"])
        return Config(**c)

    def check_entry(self, entry: dict[str, Any]) -> list[str]:
        """計画の局の設定が、今のデッキ・規約集合・方策の値と同じか（暗黙に変わっていないか）。"""
        problems = []
        config = self.config_of(entry)
        for side, name in (("0", config.deck0), ("1", config.deck1)):
            if self.deck_check(name) != entry["decks"][side]:
                problems.append(f"{entry['game_id']}: デッキ {name} の内容の確認値が計画と違う")
        key, record = self.conventions_key(config.conventions)
        if {"key": key, "digest": record["digest"]} != entry["conventions"]:
            problems.append(f"{entry['game_id']}: 規約集合の識別が計画と違う")
        if self.policies_of(config) != entry["policies"]:
            problems.append(f"{entry['game_id']}: 方策の設定（名前・版・分布・seed・ε・閾値）が計画と違う")
        return problems

    def play(self, entry: dict[str, Any], plan: dict[str, Any]) -> GameOutput:
        """1 局を実行し、保存するファイルと要約を返す（runner の結果のオブジェクトはこの関数の外へ持ち出さない）。"""
        from kyuura_engine.replay_record import dumps_record

        from . import records as R
        from .run_v1 import check_record, game_header
        from .runner import run_game

        config = self.config_of(entry)
        started = now()
        result = run_game(config)
        finished = now()
        verification = check_record(result)
        judged = judge_trace(result)
        sequences = {"action": R.sequence_digest(R.action_sequence(result["trace"]), R.ACTION_FORMAT),
                     "contract": R.sequence_digest(R.contract_sequence(result["trace"]), R.CONTRACT_FORMAT)}
        header = game_header(config, R.identity(plan["commits"]["engine"]), ["python", "-m", TOOL_NAME, "run"], result, started, finished)
        header["batch"] = {"game_id": entry["game_id"], "mode": entry["mode"], "comparison_group": entry["comparison_group"]}
        files = [("header.json", json_bytes(header)), ("trace.jsonl", jsonl_bytes(result["trace"]))]
        for actor, rows in result["actor_logs"].items():
            files.append((f"actors/{actor}.jsonl", jsonl_bytes(rows)))
        files.append(("full_record.json", dumps_record(result["record"]).encode("utf-8")))
        files.append(("result.json", json_bytes({k: result[k] for k in ("termination", "counters", "anomalies", "coverage", "metrics", "elapsed_seconds",
                                                                         "policies", "limits", "distribution")})))
        files.append(("verification.json", json_bytes(verification)))
        files.append(("judge.json", json_bytes(judged)))
        files.append(("sequences.json", json_bytes(sequences)))
        term = result["termination"]
        detail = term["detail"] if isinstance(term["detail"], dict) else {}
        summary = {"termination": term["class"],
                   "termination_detail": {k: detail[k] for k in ("reason", "halt", "result") if k in detail},
                   "counters": result["counters"], "anomalies": [a["kind"] for a in result["anomalies"]],
                   "judge": {"submits": judged["counts"], "termination": judged["termination"], "not_applied": judged["not_applied"]},
                   "replay_run": {k: verification["replay_run"][k] for k in ("expected", "status", "matches_expectation")},
                   "correspondence_problems": len(verification["correspondence_problems"]),
                   "elapsed_seconds": result["elapsed_seconds"], "sequences": sequences}
        return GameOutput(files=files, summary=summary)


def judge_trace(result: dict[str, Any]) -> dict[str, Any]:
    """保存する trace に、既存の judge（規則の版 5）をあとから当てる（runner の進行・方策に影響しない）。

    - 送信（submit を送った試み）ごとに ``judge_normal``（check のあとの送信。runner が V3-1 の変異の実行の中で当てるのと同じ引数）
    - 終わり方に ``judge_termination``（halted_known では公開の停止の値を渡す。代表の条件の根拠の宣言はないので known_stop にはならない）
    - ``judge_face_down_power_accepted`` は受理の前後の公開のログが要るので当てない（数を ``not_applied`` に記録）"""
    from .judge import JUDGE_RULES_VERSION, is_face_down_power, judge_normal, judge_termination

    rows, counts, by_kind = [], {}, {}
    not_applied = {"face_down_power_accepted": 0}
    last_accepted = None
    for e in result["trace"]:
        if e.get("type") != "attempt" or e.get("submit") is None:
            continue
        verdict, why = judge_normal(e["candidate"], e.get("meaning") or [], e["submit"], stages=e.get("stages"))
        kind = e["candidate"].get("kind")
        rows.append({"attempt": e["n"], "kind": kind, "outcome": e["submit"].get("outcome"), "verdict": verdict, "reasons": why})
        counts[verdict] = counts.get(verdict, 0) + 1
        by_kind.setdefault(kind, {})[verdict] = by_kind.setdefault(kind, {}).get(verdict, 0) + 1
        if e["submit"].get("outcome") == "accepted":
            last_accepted = e["candidate"].get("processability")
            if is_face_down_power(e["candidate"]):
                not_applied["face_down_power_accepted"] += 1
    term = result["termination"]
    detail = term["detail"] if isinstance(term["detail"], dict) else {}
    verdict, why = judge_termination(term["class"], last_accepted, halt=detail.get("halt") if term["class"] == "halted_known" else None)
    return {"rules_version": JUDGE_RULES_VERSION, "counts": dict(sorted(counts.items())), "by_kind": by_kind, "rows": rows,
            "termination": {"verdict": verdict, "reasons": why}, "not_applied": not_applied}


def stop_reasons(summary: dict[str, Any], policy: dict[str, Any]) -> tuple[list[str], list[str]]:
    """完了した局の要約から、停止方針で止める理由と、続けるが数えるもの（undetermined）を返す。"""
    stop, note = [], []
    term = summary.get("termination")
    if term in policy["stop_terminations"]:
        stop.append(f"termination:{term}")
    elif term not in policy["continue_terminations"] and policy["on_unknown_termination"] == "stop":
        stop.append(f"unknown_termination:{term}")
    judge = summary.get("judge") or {}
    verdicts = dict(judge.get("submits") or {})
    tv = (judge.get("termination") or {}).get("verdict")
    if tv:
        verdicts[f"termination:{tv}"] = 1
    suspect = verdicts.get("suspect", 0) + (1 if tv == "suspect" else 0)
    undetermined = verdicts.get("undetermined", 0) + (1 if tv == "undetermined" else 0)
    if suspect:
        (stop if policy["on_suspect"] == "stop" else note).append(f"suspect:{suspect}")
    if undetermined:
        (stop if policy["on_undetermined"] == "stop" else note).append(f"undetermined:{undetermined}")
    if summary.get("anomalies"):
        (stop if policy["on_anomaly"] == "stop" else note).append("anomalies:" + ",".join(sorted(set(summary["anomalies"]))))
    replay = summary.get("replay_run") or {}
    if replay.get("matches_expectation") is not True or summary.get("correspondence_problems"):
        (stop if policy["on_verification_problem"] == "stop" else note).append(
            f"verification:replay={replay.get('status')}/expected={replay.get('expected')},correspondence={summary.get('correspondence_problems')}")
    return stop, note


# ---------------------------------------------------------------- 計画


def batch_dir(out: Path, batch_id: str) -> Path:
    return out / "verifier" / "runs" / batch_id


def make_plan(out: Path, batch_id: str, *, engine_commit: str, tool_commit: str, seeds: list[int], modes: list[str], deck0: str, deck1: str,
              conventions: str | None = None, limits: BatchLimits = BatchLimits(), stop_policy: StopPolicy = StopPolicy(),
              adapter=None, note: str = "", game_limits: dict[str, Any] | None = None) -> dict[str, Any]:
    """計画を作って保存する（既にあれば作らない）。並び: seed ごとに方式を並べる（比較の組 = デッキ・規約集合・seed。game_id は局ごとに別）。"""
    adapter = adapter or EngineAdapter(engine_commit)
    bdir = batch_dir(out, batch_id)
    if bdir.exists():
        raise BatchRefused([f"{bdir} はすでにある（既存の証跡を上書きしない）"])
    unknown = [m for m in modes if m not in MODES]
    if unknown:
        raise BatchRefused([f"知らない方式 {unknown}"])
    if len(set(seeds)) != len(seeds):
        raise BatchRefused(["seed が重複している"])
    games = []
    for seed in seeds:
        for mode in modes:
            n = len(games) + 1
            conv_key = adapter.conventions_key(conventions)[0]
            group = f"{deck0}-vs-{deck1}/{conv_key}/s{seed}"
            games.append(adapter.entry(game_id=f"g{n:03d}-{mode}-s{seed}", mode=mode, seed=seed, deck0=deck0, deck1=deck1, conventions=conventions, group=group,
                                       game_limits=game_limits))
    if len(games) > limits.max_games:
        raise BatchRefused([f"計画の局数 {len(games)} が上限 {limits.max_games} を超える"])
    plan = {"format": PLAN_FORMAT, "batch_id": batch_id, "written": now(), "identity": adapter.identity(),
            "commits": {"engine": engine_commit, "tool": tool_commit}, "limits": asdict(limits), "stop_policy": _policy_dict(stop_policy),
            "seed_use": "ゲーム・方策・ホストの seed を同じ値にする（runner の player_seed・host_seed・mix_seed で主体ごとに分ける）",
            "order": "seed ごとに方式を並べる", "games": games,
            "rules": ["実行の前に書いた計画。結果を見て seed・デッキ・方式を差し替えない・局を増やさない",
                      "単局の上限は各局の config.limits（runner.Limits の既定）", "上限に達したら未着手を残して止める（自動で延長しない）"],
            "note": note}
    data = json_bytes(plan)
    bdir.mkdir(parents=True)
    atomic_write(bdir / "plan.json", data)
    atomic_write(bdir / "plan.sha256", (sha256_bytes(data) + "  plan.json\n").encode())
    return plan


def _policy_dict(policy: StopPolicy) -> dict[str, Any]:
    d = asdict(policy)
    d["continue_terminations"] = list(d["continue_terminations"])
    d["stop_terminations"] = list(d["stop_terminations"])
    return d


def load_plan(bdir: Path, adapter) -> tuple[dict[str, Any], str]:
    """計画を読み、計画自体の sha256・形式・実装識別・各局の設定を照合する。"""
    problems = []
    data = (bdir / "plan.json").read_bytes()
    digest = sha256_bytes(data)
    recorded = (bdir / "plan.sha256").read_text(encoding="utf-8").split()[0]
    if digest != recorded:
        raise BatchRefused([f"plan.json の sha256 {digest} が plan.sha256 {recorded} と違う（計画が変わった）"])
    plan = json.loads(data)
    if plan.get("format") != PLAN_FORMAT:
        problems.append(f"計画の形式 {plan.get('format')} を知らない")
    if plan.get("batch_id") != bdir.name:
        problems.append("計画の batch_id がディレクトリ名と違う")
    current = adapter.identity()
    if current != plan["identity"]:
        diff = [k for k in sorted(set(current) | set(plan["identity"])) if current.get(k) != plan["identity"].get(k)]
        problems.append(f"実装識別が計画と違う: {diff}（道具・エンジンの版・behavior_digest・実行環境）")
    ids = [g["game_id"] for g in plan["games"]]
    if len(set(ids)) != len(ids):
        problems.append("game_id が重複している")
    if len(ids) > plan["limits"]["max_games"]:
        problems.append("計画の局数が上限を超える")
    if not problems:
        for entry in plan["games"]:
            problems += adapter.check_entry(entry)
    if problems:
        raise BatchRefused(problems)
    return plan, digest


# ---------------------------------------------------------------- ロック・台帳


def acquire_lock(bdir: Path, session: str) -> dict[str, Any]:
    info = {"session": session, "pid": os.getpid(), "host": socket.gethostname(), "started": now(),
            "note": "PID は記録だけ。PID で生死を調べて自動で解除しない（unlock --session で、利用者が確かめてから外す）"}
    try:
        fd = os.open(bdir / LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            held = (bdir / LOCK).read_text(encoding="utf-8")
        except OSError as error:
            held = f"(読めない: {error})"
        raise LockHeld([f"ロック {bdir / LOCK} がある（実行中か、前のセッションの残り）: {held.strip()}"]) from None
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(canonical(info) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return info


def release_lock(bdir: Path, session: str) -> bool:
    """自分のセッションのロックだけを外す。"""
    path = bdir / LOCK
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if held.get("session") != session:
        return False
    path.unlink()
    return True


class Ledger:
    """追記だけの台帳（1 行 1 つの出来事。書くたびに flush・fsync）。最後の行が途中（改行なし・JSON でない）なら、読むときに除いて数える。"""

    def __init__(self, path: Path):
        self.path = path

    def append(self, event: dict[str, Any]) -> None:
        lead = ""
        if self.path.exists() and self.path.stat().st_size:
            with self.path.open("rb") as f:
                f.seek(-1, os.SEEK_END)
                lead = "" if f.read(1) == b"\n" else "\n"  # 途中で切れた行のあとに続けて書かない（切れた行は 1 行の壊れた行として残す）
        with self.path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(lead + canonical({"at": now(), **event}) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def read(self) -> tuple[list[dict[str, Any]], int]:
        if not self.path.exists():
            return [], 0
        events, broken = [], 0
        text = self.path.read_text(encoding="utf-8")
        for line in text.split("\n"):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except ValueError:
                broken += 1
        return events, broken


def accounted_seconds(events: list[dict[str, Any]], reserve: float) -> dict[str, Any]:
    """累積の実行時間。セッションごとに、記録した単調時計の経過の最大を足す。終わり（session_end）のないセッション（異常終了・強制終了）は、
    最後の記録のあとの時間がわからないので、見込みとして ``reserve``（局の予備の秒）を足す（estimated に数える）。"""
    sessions: dict[str, dict[str, Any]] = {}
    for e in events:
        sid = e.get("session")
        if sid is None:
            continue
        s = sessions.setdefault(sid, {"elapsed": 0.0, "ended": False})
        s["elapsed"] = max(s["elapsed"], float(e.get("elapsed") or 0.0))
        if e.get("event") == "session_end":
            s["ended"] = True
    total, estimated = 0.0, []
    for sid, s in sessions.items():
        total += s["elapsed"]
        if not s["ended"]:
            total += reserve
            estimated.append(sid)
    return {"seconds": round(total, 3), "sessions": len(sessions), "estimated_sessions": estimated}


# ---------------------------------------------------------------- 保存した局の照合


def game_sha(entry: dict[str, Any]) -> str:
    return sha256_bytes(canonical(entry).encode())


def attempts_of(bdir: Path, game_id: str) -> list[Path]:
    gdir = bdir / "games" / game_id
    return sorted(p for p in gdir.iterdir() if p.is_dir() and p.name.startswith("attempt-")) if gdir.exists() else []


def verify_complete(adir: Path, *, plan: dict[str, Any], plan_sha: str, entry: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """完了マーカーだけでなく、計画・局の設定・識別・必須ファイル・ハッシュを照合する。問題がなければ (marker, [])。"""
    problems = []
    try:
        marker = json.loads((adir / MARKER).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return None, [f"{adir}: {MARKER} が読めない ({error})"]
    expect = {"format": COMPLETE_FORMAT, "batch_id": plan["batch_id"], "game_id": entry["game_id"], "attempt": int(adir.name.split("-")[1]),
              "plan_sha256": plan_sha, "game_sha256": game_sha(entry), "identity": plan["identity"]}
    for key, value in expect.items():
        if marker.get(key) != value:
            problems.append(f"{adir}: {MARKER} の {key} が計画・設定と違う")
    try:
        table_bytes = (adir / TABLE).read_bytes()
        table = json.loads(table_bytes)
    except (OSError, ValueError) as error:
        return marker, problems + [f"{adir}: {TABLE} が読めない ({error})"]
    if marker.get("files_table_sha256") != sha256_bytes(table_bytes):
        problems.append(f"{adir}: {TABLE} の sha256 が {MARKER} と違う")
    for name in marker.get("required", REQUIRED_FILES):
        if name not in table:
            problems.append(f"{adir}: 必須のファイル {name} が表にない")
    on_disk = {p.relative_to(adir).as_posix() for p in adir.rglob("*") if p.is_file()} - {TABLE, MARKER}
    if on_disk != set(table):
        problems.append(f"{adir}: 表とディスクのファイルが違う（余分 {sorted(on_disk - set(table))}・欠け {sorted(set(table) - on_disk)}）")
    for name, digest in table.items():
        path = adir / name
        if path.is_file() and sha256_file(path) != digest:
            problems.append(f"{adir}: {name} の sha256 が表と違う（破損か書きかえ）")
    return marker, problems


def scan(bdir: Path, plan: dict[str, Any], plan_sha: str) -> dict[str, Any]:
    """保存済みの局の状態。完了の照合に失敗したもの・計画にない局のディレクトリ・完了が 2 つある局は problems に入れる（黙って採用・再実行しない）。"""
    problems, state = [], {}
    known = {g["game_id"] for g in plan["games"]}
    gdir = bdir / "games"
    if gdir.exists():
        for p in gdir.iterdir():
            if p.name not in known:
                problems.append(f"計画にない局のディレクトリ {p}")
    for entry in plan["games"]:
        gid = entry["game_id"]
        info = {"attempts": [], "complete": None}
        for adir in attempts_of(bdir, gid):
            if (adir / MARKER).exists():
                marker, issues = verify_complete(adir, plan=plan, plan_sha=plan_sha, entry=entry)
                problems += issues
                if not issues:
                    if info["complete"] is not None:
                        problems.append(f"{gid}: 完了した attempt が 2 つある")
                    info["complete"] = {"attempt": adir.name, "summary": marker["summary"], "stop": marker.get("stop", []), "note": marker.get("note", [])}
                info["attempts"].append({"attempt": adir.name, "status": "complete" if not issues else "invalid"})
            else:
                note = None
                if (adir / NOTE).exists():
                    try:
                        note = json.loads((adir / NOTE).read_text(encoding="utf-8")).get("status")
                    except (OSError, ValueError):
                        note = "note_unreadable"
                info["attempts"].append({"attempt": adir.name, "status": "incomplete", "note": note})
        state[gid] = info
    return {"games": state, "problems": problems}


# ---------------------------------------------------------------- 実行


@dataclass
class RunReport:
    status: str
    session: str
    ran: list = field(default_factory=list)
    skipped_complete: list = field(default_factory=list)
    stop: dict[str, Any] = field(default_factory=dict)
    accounted_seconds: float = 0.0


def run_batch(out: Path, batch_id: str, *, adapter=None, clock: Callable[[], float] = time.monotonic, stop_after_games: int | None = None,
              acknowledge: list[str] | None = None, memory: Callable[[], dict[str, Any]] = process_memory, aggregate_after: bool = True) -> RunReport:
    """計画の未完了の局を順に 1 局ずつ実行する。正常な停止の状態は戻り値、計画・保存内容の不一致は BatchRefused、二重起動は LockHeld。

    KeyboardInterrupt・SystemExit・MemoryError は対戦の結果に変えずに、attempt を未完了のまま残し、台帳に書いて（書ければ）そのまま投げ直す。次の局は始めない。"""
    adapter = adapter or EngineAdapter()
    bdir = batch_dir(out, batch_id)
    if not (bdir / "plan.json").exists():
        raise BatchRefused([f"{bdir / 'plan.json'} がない（先に plan で計画を保存する）"])
    session = uuid.uuid4().hex
    acquire_lock(bdir, session)
    ledger = Ledger(bdir / LEDGER)
    t0 = clock()
    elapsed = lambda: round(clock() - t0, 3)  # noqa: E731
    report = RunReport(status="running", session=session)
    ended = False
    try:
        events, broken = ledger.read()
        ledger.append({"event": "session_start", "session": session, "pid": os.getpid(), "elapsed": 0.0, "ledger_broken_lines": broken,
                       "stop_after_games": stop_after_games})
        try:
            plan, plan_sha = load_plan(bdir, adapter)
            state = scan(bdir, plan, plan_sha)
            if state["problems"]:
                raise BatchRefused(state["problems"])
        except BatchRefused as refused:
            ledger.append({"event": "session_end", "session": session, "status": "refused", "problems": refused.problems, "elapsed": elapsed()})
            ended = True
            raise
        limits, policy = plan["limits"], plan["stop_policy"]
        for gid in acknowledge or []:
            ledger.append({"event": "stop_acknowledged", "session": session, "game": gid, "elapsed": elapsed()})
        events, _ = ledger.read()
        acked = {e["game"] for e in events if e.get("event") == "stop_acknowledged"}
        pending = [gid for gid, info in state["games"].items() if info["complete"] and info["complete"]["stop"] and gid not in acked]
        if pending:
            ledger.append({"event": "session_end", "session": session, "status": "refused_unacknowledged_stop", "games": pending, "elapsed": elapsed()})
            ended = True
            raise BatchRefused([f"停止方針で止めた局 {pending} を確かめていない（--acknowledge-stop で台帳に書いてから再開する）"])
        prior = accounted_seconds([e for e in events if e.get("session") != session], limits["game_reserve_seconds"])
        evidence = tree_bytes(bdir)
        status, stop = "completed", {}
        for entry in plan["games"]:
            gid = entry["game_id"]
            info = state["games"][gid]
            if info["complete"] is not None:
                report.skipped_complete.append(gid)
                continue
            used = prior["seconds"] + (clock() - t0)
            if stop_after_games is not None and len(report.ran) >= stop_after_games:
                status, stop = "stopped_requested", {"after_games": len(report.ran)}
                break
            if limits["budget_seconds"] - used < limits["game_reserve_seconds"]:
                status, stop = "stopped_budget_time", {"accounted_seconds": round(used, 3), "budget_seconds": limits["budget_seconds"],
                                                       "game_reserve_seconds": limits["game_reserve_seconds"]}
                break
            if limits["evidence_max_bytes"] - evidence < limits["evidence_reserve_bytes"]:
                status, stop = "stopped_budget_evidence", {"evidence_bytes": evidence, "evidence_max_bytes": limits["evidence_max_bytes"]}
                break
            if len(info["attempts"]) >= limits["max_attempts_per_game"]:
                status, stop = "stopped_attempts_exhausted", {"game": gid, "attempts": len(info["attempts"])}
                break
            outcome = _run_attempt(bdir, entry, plan, plan_sha, adapter, ledger, session, elapsed, len(info["attempts"]) + 1, evidence, limits, policy, memory)
            evidence = tree_bytes(bdir)
            report.ran.append({"game": gid, **outcome})
            if outcome["status"] != "complete":
                status, stop = f"stopped_{outcome['status']}", {"game": gid, **outcome}
                break
            if outcome["stop"]:
                ledger.append({"event": "policy_stop", "session": session, "game": gid, "reasons": outcome["stop"], "elapsed": elapsed()})
                status, stop = "stopped_policy", {"game": gid, "reasons": outcome["stop"]}
                break
        report.status, report.stop = status, stop
        events, _ = ledger.read()
        report.accounted_seconds = accounted_seconds([e for e in events if e.get("session") != session], limits["game_reserve_seconds"])["seconds"] + elapsed()
        ledger.append({"event": "session_end", "session": session, "status": status, "stop": stop, "elapsed": elapsed(),
                       "evidence_bytes": evidence, "accounted_seconds_total": round(report.accounted_seconds, 3)})
        ended = True
        if aggregate_after:
            try:
                aggregate(out, batch_id, adapter=adapter, holding_lock=True)
            except Exception as error:  # 集計の失敗で対戦をやり直さない（aggregate を別に実行し直す）
                ledger.append({"event": "aggregate_failed", "session": session, "error": f"{type(error).__name__}: {error}", "elapsed": elapsed()})
        return report
    except BaseException as error:
        if not ended:
            try:
                ledger.append({"event": "session_end", "session": session, "status": "interrupted", "error": type(error).__name__, "elapsed": elapsed()})
            except BaseException:  # noqa: BLE001  台帳も書けなければ、終わりのないセッションとして累積の時間に見込みを足す
                pass
        raise
    finally:
        release_lock(bdir, session)


def _run_attempt(bdir, entry, plan, plan_sha, adapter, ledger, session, elapsed, n, evidence, limits, policy, memory) -> dict[str, Any]:
    gid = entry["game_id"]
    adir = bdir / "games" / gid / f"attempt-{n:03d}"
    adir.mkdir(parents=True, exist_ok=False)
    ledger.append({"event": "attempt_start", "session": session, "game": gid, "attempt": n, "elapsed": elapsed()})
    start = elapsed()

    def end(status, **extra):
        ledger.append({"event": "attempt_end", "session": session, "game": gid, "attempt": n, "status": status, "elapsed": elapsed(),
                       "attempt_seconds": round(elapsed() - start, 3), **extra})

    def note(status, **extra):
        try:
            atomic_write(adir / NOTE, json_bytes({"status": status, "game_id": gid, "attempt": n, "session": session, "written": now(), **extra}))
        except BaseException:  # noqa: BLE001  書けなくても、COMPLETE.json がないので未完了として扱われる
            pass

    try:
        output = adapter.play(entry, plan)
    except (KeyboardInterrupt, SystemExit, MemoryError) as error:
        note("interrupted", error=type(error).__name__)
        end("interrupted", error=type(error).__name__)
        raise
    except Exception as error:  # adapter（記録・replay_run・judge の当て方）の誤り。runner の中の例外は runner が exception の終わり方にする
        note("error", error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
        end("error", error=f"{type(error).__name__}: {error}")
        return {"status": "error", "error": f"{type(error).__name__}: {error}"}
    used_memory = memory()
    size = sum(len(data) for _, data in output.files)
    if evidence + size > limits["evidence_max_bytes"]:
        note("evidence_limit", bytes=size, evidence_bytes=evidence, summary=output.summary)
        end("evidence_limit", bytes=size)
        return {"status": "evidence_limit", "bytes": size}
    try:
        table = {}
        for name, data in output.files:
            atomic_write(adir / name, data)
            table[name] = sha256_bytes(data)
        del output.files[:]  # 書いたバイト列を持ち続けない
        for name, digest in table.items():  # 読み直して照合する（書き込みの誤りを完了にしない）
            if sha256_file(adir / name) != digest:
                raise OSError(f"{name} を読み直した sha256 が書いた値と違う")
        missing = [name for name in REQUIRED_FILES if name not in table]
        if missing:
            raise OSError(f"必須のファイルがない: {missing}")
        table_bytes = json_bytes(table)
        atomic_write(adir / TABLE, table_bytes)
        stop, noted = stop_reasons(output.summary, policy)
        marker = {"format": COMPLETE_FORMAT, "batch_id": plan["batch_id"], "game_id": gid, "attempt": n, "session": session, "written": now(),
                  "plan_sha256": plan_sha, "game_sha256": game_sha(entry), "identity": plan["identity"], "files_table_sha256": sha256_bytes(table_bytes),
                  "required": list(REQUIRED_FILES), "bytes": size, "memory": used_memory, "attempt_seconds": round(elapsed() - start, 3),
                  "summary": output.summary, "stop": stop, "note": noted}
        atomic_write(adir / MARKER, json_bytes(marker))  # 最後に書く
    except (KeyboardInterrupt, SystemExit, MemoryError) as error:
        note("interrupted", error=type(error).__name__)
        end("interrupted", error=type(error).__name__)
        raise
    except Exception as error:
        note("write_failed", error=f"{type(error).__name__}: {error}")
        end("write_failed", error=f"{type(error).__name__}: {error}")
        return {"status": "write_failed", "error": f"{type(error).__name__}: {error}"}
    end("complete", termination=output.summary.get("termination"), bytes=size, memory=used_memory, stop=stop)
    return {"status": "complete", "termination": output.summary.get("termination"), "stop": stop, "note": noted, "bytes": size}


# ---------------------------------------------------------------- 集計（保存済みの局だけから。対戦を走らせない）


def _add(bucket: dict[str, Any], key, n=1) -> None:
    bucket[str(key)] = bucket.get(str(key), 0) + n


def _merge(into: dict[str, Any], src: dict[str, Any]) -> None:
    for k, v in (src or {}).items():
        if isinstance(v, dict):
            _merge(into.setdefault(k, {}), v)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            into[k] = round(into.get(k, 0) + v, 4)


COVERAGE_AXES = ("chosen_kind", "accepted_kind", "offered_kind", "input", "decision_kind", "stage_feature", "stage_count", "optional_stage", "outcome",
                 "refusal", "waiting", "situation", "status", "phase", "scope_excluded", "chosen_processability", "residual_present")
METRIC_AXES = ("termination", "halt", "decision_kind", "episode_mode", "episode_result", "policy_suppressed_reason", "offered_processability",
               "selected_processability", "empty_reason")
FUNNEL = ("offered_fetches", "in_scope_fetches", "selected", "build_ok", "already_tried", "policy_suppressed", "check_valid", "check_invalid", "submitted")


def aggregate(out: Path, batch_id: str, *, adapter=None, holding_lock: bool = False) -> dict[str, Any]:
    """保存済みの局（照合済みの完了局）と台帳から、集計を作り直す。対戦・replay_run をやり直さない。"""
    adapter = adapter or EngineAdapter()
    bdir = batch_dir(out, batch_id)
    session = uuid.uuid4().hex
    if not holding_lock:
        acquire_lock(bdir, session)
    try:
        plan, plan_sha = load_plan(bdir, adapter)
        state = scan(bdir, plan, plan_sha)
        events, broken = Ledger(bdir / LEDGER).read()
        result = _aggregate(bdir, plan, plan_sha, state, events, broken)
        atomic_write(bdir / "aggregate.json", json_bytes(result["verifier"]))
        atomic_write(out / "public" / "runs" / batch_id / "summary.json", json_bytes(result["public"]))
        return result
    finally:
        if not holding_lock:
            release_lock(bdir, session)


def _aggregate(bdir: Path, plan: dict[str, Any], plan_sha: str, state: dict[str, Any], events: list[dict[str, Any]], broken: int) -> dict[str, Any]:
    games = plan["games"]
    complete = [(g, state["games"][g["game_id"]]["complete"]) for g in games if state["games"][g["game_id"]]["complete"]]
    attempts = [a for g in games for a in state["games"][g["game_id"]]["attempts"]]
    started = [g for g in games if state["games"][g["game_id"]]["attempts"]]
    rows, by = [], {"mode": {}, "decks": {}, "conventions": {}}
    terminations, judge_submits, judge_term, anomalies, counters, coverage, axes, funnel, by_kind_outcome = {}, {}, {}, {}, {}, {}, {}, {}, {}
    replay, stops, notes, seconds, mems, sizes = {}, [], [], [], [], []
    for entry, done in complete:
        s = done["summary"]
        adir = bdir / "games" / entry["game_id"] / done["attempt"]
        marker = json.loads((adir / MARKER).read_text(encoding="utf-8"))
        result = json.loads((adir / "result.json").read_text(encoding="utf-8"))
        _add(terminations, s["termination"])
        for k, v in (s["judge"]["submits"] or {}).items():
            _add(judge_submits, k, v)
        _add(judge_term, s["judge"]["termination"]["verdict"])
        for a in s["anomalies"]:
            _add(anomalies, a)
        _merge(counters, s["counters"])
        for axis in COVERAGE_AXES:
            _merge(coverage.setdefault(axis, {}), result["coverage"].get(axis, {}))
        for axis in METRIC_AXES:
            _merge(axes.setdefault(axis, {}), result["metrics"]["axes"].get(axis, {}))
        for kind, k in result["metrics"]["kinds"].items():
            _merge(funnel.setdefault(kind, {}), {f: k[f] for f in FUNNEL})
            _merge(by_kind_outcome.setdefault(kind, {}), {"outcome": k["outcome"], "build_failed": k["build_failed"], "excluded": k["excluded"]})
        _add(replay, f"{s['replay_run']['status']}(expected {s['replay_run']['expected']})")
        for dim, key in (("mode", entry["mode"]), ("decks", f"{entry['config']['deck0']} vs {entry['config']['deck1']}"),
                         ("conventions", entry["conventions"]["key"])):
            b = by[dim].setdefault(key, {"games": 0, "termination": {}, "judge_submits": {}, "judge_termination": {}, "accepted": 0, "turns": 0})
            b["games"] += 1
            _add(b["termination"], s["termination"])
            for k, v in (s["judge"]["submits"] or {}).items():
                _add(b["judge_submits"], k, v)
            _add(b["judge_termination"], s["judge"]["termination"]["verdict"])
            b["accepted"] += s["counters"]["accepted"]
            b["turns"] += s["counters"]["turns"]
        if done["stop"]:
            stops.append({"game": entry["game_id"], "reasons": done["stop"]})
        if done["note"]:
            notes.append({"game": entry["game_id"], "note": done["note"]})
        seconds.append(s["elapsed_seconds"])
        sizes.append(marker["bytes"])
        if (marker.get("memory") or {}).get("status") == "measured":
            mems.append(marker["memory"])
        rows.append({"game_id": entry["game_id"], "mode": entry["mode"], "group": entry["comparison_group"], "attempt": done["attempt"],
                     "termination": s["termination"], "termination_detail": s["termination_detail"], "turns": s["counters"]["turns"],
                     "accepted": s["counters"]["accepted"], "operations": s["counters"]["operations"], "judge": s["judge"],
                     "anomalies": s["anomalies"], "replay_run": s["replay_run"], "elapsed_seconds": s["elapsed_seconds"], "bytes": marker["bytes"],
                     "stop": done["stop"], "note": done["note"], "action_sha256": s["sequences"]["action"]["sha256"]})
    sessions = [e for e in events if e.get("event") == "session_end"]
    acc = accounted_seconds(events, plan["limits"]["game_reserve_seconds"])
    peak = max((m.get("peak_working_set_bytes") or 0 for m in mems), default=None)
    common = {
        "batch_id": plan["batch_id"], "plan_sha256": plan_sha, "identity": {"tool": plan["identity"]["tool"]["digest"],
                                                                         "engine_version": plan["identity"]["engine"]["version"],
                                                                         "behavior_digest": plan["identity"]["engine"]["implementation"]["behavior_digest"]},
        "commits": plan["commits"], "limits": plan["limits"], "stop_policy": plan["stop_policy"],
        "games": {"planned": len(games), "complete": len(complete), "started_incomplete": len(started) - len(complete),
                  "not_started": len(games) - len(started)},
        "attempts": {"total": len(attempts), "complete": sum(a["status"] == "complete" for a in attempts),
                     "incomplete": sum(a["status"] == "incomplete" for a in attempts), "invalid": sum(a["status"] == "invalid" for a in attempts)},
        "sessions": {"ended": [{k: e.get(k) for k in ("status", "stop", "elapsed")} for e in sessions], "accounted_seconds": acc,
                     "ledger_broken_lines": broken, "policy_stops": [e.get("game") for e in events if e.get("event") == "policy_stop"],
                     "acknowledged": [e.get("game") for e in events if e.get("event") == "stop_acknowledged"]},
        "terminations": terminations, "judge": {"submits": judge_submits, "termination": judge_term}, "anomalies": anomalies,
        "counters": counters, "replay_run": replay, "by": by,
        "time": {"game_seconds_sum": round(sum(seconds), 3), "game_seconds_max": max(seconds, default=None),
                 "game_seconds_median": statistics.median(seconds) if seconds else None},
        "memory": {"measured_games": len(mems), "peak_working_set_bytes_max": peak,
                   "note": "プロセスの開始からの最大（局ごとの値ではない）。取れない環境では未計測"},
        "evidence": {"game_bytes_sum": sum(sizes), "batch_dir_bytes": tree_bytes(bdir)},
        "stops": stops, "notes": notes, "problems": state["problems"],
        "reading": ["回数・勝ち・到達の数は、この計画の局の観測。網羅性・強さ・正しさの証明ではない",
                    "段階（提示 offered・範囲 in_scope・選択 selected・入力の作成 build_ok・check・送信 submitted・結果 outcome）は別の数で、混ぜない",
                    "replay_run は元の対戦とは別の確認で、局の数に足さない"],
    }
    verifier = {**common, "rows": rows, "coverage": coverage, "axes": axes, "funnel": funnel, "by_kind": by_kind_outcome}
    hidden = {"stops", "notes", "problems", "sessions"}  # game_id は seed を含むので、公開の集計には数と理由だけを書く
    public = {**{k: v for k, v in common.items() if k not in hidden}, "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
              "stops": [{"mode": next(g["mode"] for g in games if g["game_id"] == s["game"]), "reasons": s["reasons"]} for s in stops],
              "notes": [n["note"] for n in notes], "problem_count": len(state["problems"]),
              "sessions": {"ended": [{k: e.get(k) for k in ("status", "elapsed")} for e in sessions], "accounted_seconds": {k: v for k, v in acc.items() if k != "estimated_sessions"},
                           "estimated_sessions": len(acc["estimated_sessions"]), "policy_stops": len(common["sessions"]["policy_stops"]),
                           "acknowledged": len(common["sessions"]["acknowledged"]), "ledger_broken_lines": broken},
              "coverage_keys": {axis: sorted(v) for axis, v in coverage.items()}, "axes": axes, "funnel": funnel, "by_kind": by_kind_outcome,
              "public_note": "seed・デッキの並び・選択の中身・本人向けの情報を含まない集計"}
    return {"verifier": verifier, "public": public}


# ---------------------------------------------------------------- 入口


def unlock(out: Path, batch_id: str, session: str) -> None:
    """残ったロックを外す（利用者が、そのセッションのプロセスが動いていないことを確かめたあと）。PID は調べない。セッション ID が合うときだけ。"""
    bdir = batch_dir(out, batch_id)
    held = json.loads((bdir / LOCK).read_text(encoding="utf-8"))
    if held.get("session") != session:
        raise BatchRefused([f"ロックのセッション {held.get('session')} が指定 {session} と違う"])
    (bdir / LOCK).unlink()
    Ledger(bdir / LEDGER).append({"event": "lock_removed", "lock": held, "by": "unlock"})


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="python -m tools.verification_ai.batch")
    sub = parser.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan")
    pl.add_argument("--out", required=True)
    pl.add_argument("--batch", required=True)
    pl.add_argument("--engine-commit", required=True)
    pl.add_argument("--tool-commit", required=True)
    pl.add_argument("--seeds", type=int, nargs="+", required=True)
    pl.add_argument("--modes", nargs="+", choices=sorted(MODES), required=True)
    pl.add_argument("--deck0", default="hitmonchan-dewgong")
    pl.add_argument("--deck1", default="venusaur-parasect")
    pl.add_argument("--conventions", default=None)
    pl.add_argument("--max-games", type=int, default=BatchLimits.max_games)
    pl.add_argument("--budget-seconds", type=float, default=BatchLimits.budget_seconds)
    pl.add_argument("--evidence-max-mb", type=int, default=BatchLimits.evidence_max_bytes // MB)
    pl.add_argument("--note", default="")
    rn = sub.add_parser("run")
    rn.add_argument("--out", required=True)
    rn.add_argument("--batch", required=True)
    rn.add_argument("--engine-commit", default=None)
    rn.add_argument("--stop-after-games", type=int, default=None)
    rn.add_argument("--acknowledge-stop", nargs="*", default=[])
    ag = sub.add_parser("aggregate")
    ag.add_argument("--out", required=True)
    ag.add_argument("--batch", required=True)
    ul = sub.add_parser("unlock")
    ul.add_argument("--out", required=True)
    ul.add_argument("--batch", required=True)
    ul.add_argument("--session", required=True)
    args = parser.parse_args(argv)
    out = Path(args.out)
    try:
        if args.cmd == "plan":
            limits = BatchLimits(max_games=args.max_games, budget_seconds=args.budget_seconds, evidence_max_bytes=args.evidence_max_mb * MB)
            plan = make_plan(out, args.batch, engine_commit=args.engine_commit, tool_commit=args.tool_commit, seeds=args.seeds, modes=args.modes,
                             deck0=args.deck0, deck1=args.deck1, conventions=args.conventions, limits=limits, note=args.note)
            print(json.dumps({"batch": args.batch, "games": len(plan["games"]),
                              "plan_sha256": (batch_dir(out, args.batch) / "plan.sha256").read_text(encoding="utf-8").split()[0]}, ensure_ascii=False))
            return 0
        if args.cmd == "run":
            report = run_batch(out, args.batch, adapter=EngineAdapter(args.engine_commit), stop_after_games=args.stop_after_games,
                               acknowledge=args.acknowledge_stop)
            print(json.dumps(asdict(report), ensure_ascii=False, indent=1))
            return 0 if report.status in ("completed", "stopped_requested", "stopped_budget_time", "stopped_budget_evidence") else 1
        if args.cmd == "aggregate":
            result = aggregate(out, args.batch)
            print(json.dumps({k: result["verifier"][k] for k in ("games", "attempts", "terminations", "judge")}, ensure_ascii=False, indent=1))
            return 0
        unlock(out, args.batch, args.session)
        return 0
    except BatchRefused as refused:
        print(json.dumps({"refused": refused.problems, "lock": isinstance(refused, LockHeld)}, ensure_ascii=False, indent=1))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
