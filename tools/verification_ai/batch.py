"""上限つきの逐次バッチ（docs/verification-ai-batch.md）。既存の単局ランナー・方策・行動生成・judge・記録をそのまま使い、新しく持つ責任は次の 5 つだけ。

1. 実行計画を読む（``plan.json``。既定値も展開して保存し、計画自体の sha256 を ``plan.sha256`` に書く）
2. 1 局ずつ順に、同じプロセスで直接実行する（並列・分散・常駐・プロセスの起動・検索・終了はしない）
3. 各局を attempt ごとの別ディレクトリへ確定保存する（各ファイルは同じディレクトリの一時ファイルから ``os.replace``。ハッシュの表を書き、読み直して照合し、最後に ``COMPLETE.json``）
4. 完了局を照合して再開する（計画・実装識別・局の設定・必須ファイル・ハッシュ。正常な完了局は再実行しない。未完了の attempt は残し、別の attempt として最初から）
5. 保存済みの局から集計する（``aggregate``。対戦をやり直さない）

    python -m tools.verification_ai.batch plan --out <証跡> --batch <名前> --engine-commit <sha> --tool-commit <sha> --seeds 1001 1002 ... --modes uniform-stage rules-v2 mixed boundary \\
        --observation [--deck0 <固定デッキ> | --decklist0 <JSON>] [--deck1 <固定デッキ> | --decklist1 <JSON>]
    python -m tools.verification_ai.batch decklist --file <JSON>   （明示リストの形・確認値・deck_problems を確かめるだけ）
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

PLAN_FORMAT = "kyuura-vai-batch-plan/5"  # 5: 局のデッキの記録（固定デッキ・明示リスト。展開の順・確認値・deck_problems の結果）・方式 boundary・方策とプロファイルの組の照合（docs/verification-ai-decklist.md）。4: 主体別の観測の記録の設定 observation（docs/verification-ai-observation.md）。3 は C1・C2（undetermined の分類に accepted_content_unrecorded）・2 は 99 局 vai-batch-b2・1 は 30 局の初回 vai-batch-b1
COMPLETE_FORMAT = "kyuura-vai-batch-complete/5"  # 5: 証跡の判定 evidence（complete_without_stop・complete_with_stop）。照合で停止の理由を要約から計算し直す。4: 要約に主体別の観測の記録の状態（observation。有効な計画だけ）。3 は C1・C2（受理の中身の種類ごとの件数）・2 は vai-batch-b2
TOOL_NAME = "tools.verification_ai.batch"
TOOL_VERSION = 6  # 6: 明示的なデッキリスト・方式 boundary・観測の記録の要約の欠けで止める（docs/verification-ai-decklist.md）。5: 主体別の観測・更新・公開ログの記録（observe。計画で有効にしたときだけ）。4 は judge の規則 6（docs/verification-ai-batch-plan3.md 11 章）。3 は C1・C2（9385cc3）

# 方式（計画を作るときだけ使う。計画には Config の全項目を展開して書くので、ここを後で変えても既存の計画の局は変わらない）
MODES: dict[str, dict[str, Any]] = {
    "uniform-stage": {"policy": "uniform", "distribution": "uniform-candidate+uniform-stage"},
    "uniform-tuple": {"policy": "uniform", "distribution": "uniform-candidate+uniform-tuple"},
    "rules-v1": {"policy": "rules", "rules_version": 1},
    "rules-v2": {"policy": "rules", "rules_version": 2, "repeat_threshold": 2},
    "mixed": {"policy": "mixed", "rules_version": 2, "epsilon": 0.25, "repeat_threshold": 2},
    # V3-2 の boundary（方策 BoundaryPolicy とプロファイル boundary の組。docs/verification-ai-v3-2.md 4 章）。処理可能性の区分を均等に選び、その中で候補を均等に選ぶ
    "boundary": {"policy": "boundary", "profile": "boundary"},
}
STAGE_DISTRIBUTION = "uniform-candidate+uniform-stage"  # policies.STAGE と同じ値（テストで一致を確かめる）
TUPLE_DISTRIBUTION = "uniform-candidate+uniform-tuple"  # policies.TUPLE と同じ値
# 方策・プロファイル・分布の組（既存の実装で定義した組だけ）。ほかの組（rules・mixed・uniform の boundary プロファイル、boundary の方策の deep など）は計画を作るときに拒否し、
# 別の方式へ読み替えない
SUPPORTED_SETTINGS = (("uniform", "deep", STAGE_DISTRIBUTION), ("uniform", "deep", TUPLE_DISTRIBUTION), ("rules", "deep", STAGE_DISTRIBUTION),
                      ("mixed", "deep", STAGE_DISTRIBUTION), ("boundary", "boundary", STAGE_DISTRIBUTION))
DEFAULT_DECKS = {"0": "hitmonchan-dewgong", "1": "venusaur-parasect"}
PRESET_EXPANSION = "preset-entries-in-order/1"  # 固定デッキ: PresetDeck.cards()（登録の項目の並びのまま。decklist.EXPANSION と同じ規則）


def setting_problems(config: dict[str, Any]) -> list[str]:
    """計画の局の設定の、方策・プロファイル・分布の組の問題（定義していない組は拒否する）。"""
    combo = (config.get("policy"), config.get("profile"), config.get("distribution"))
    if combo not in SUPPORTED_SETTINGS:
        return [f"方策・プロファイル・分布の組 {list(combo)} は定義していない（定義した組 {[list(c) for c in SUPPORTED_SETTINGS]}）"]
    return []

# 局の終わり方（runner の分類）と停止方針。KeyboardInterrupt・SystemExit・MemoryError は分類に入らない（対戦の結果に変えない）
CONTINUE_TERMINATIONS = ("game_over", "halted_known", "input_unavailable", "no_progress",
                         "limit_operations", "limit_accepted", "limit_turns", "limit_time")
STOP_TERMINATIONS = ("halted_unclassified", "failed", "state_integrity", "exception", "inconsistency", "start_rejected", "negative_side_effect",
                     "api_contract_unknown")
# undetermined の理由の分類（judge の理由の文字列の先頭で決める。どれにも当たらなければ unclassified）
EVIDENCE_MISSING_STOP = "evidence_missing_stop"  # 停止・停止系の拒否で、公開の診断の分類とコード表は合うが、代表の条件の根拠（KNOWN_STOP_EVIDENCE）がない
UNKNOWN_DIAGNOSTIC = "unknown_diagnostic"  # 停止のコードが診断のコード表にない
CONTRACT_UNKNOWN = "contract_unknown"  # 知らない送信の結果・終わり方 api_contract_unknown
NO_PROGRESS = "no_progress"  # 終わり方 no_progress（同じ状態の拒否・選び直しの上限）
# 受理の中身（U-R3a・P6）を判定する公開のログの記録が trace にない（記録の欠け・古い trace）。根拠不足の停止（evidence_missing_stop）とは別
ACCEPTED_CONTENT_UNRECORDED = "accepted_content_unrecorded"
UNCLASSIFIED = "unclassified"
UNDETERMINED_CATEGORIES = (EVIDENCE_MISSING_STOP, UNKNOWN_DIAGNOSTIC, CONTRACT_UNKNOWN, NO_PROGRESS, ACCEPTED_CONTENT_UNRECORDED, UNCLASSIFIED)
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
    on_known_stop: str = "continue"
    on_undetermined: dict = field(default_factory=lambda: {EVIDENCE_MISSING_STOP: "continue", UNKNOWN_DIAGNOSTIC: "stop", CONTRACT_UNKNOWN: "stop",
                                                            NO_PROGRESS: "stop", ACCEPTED_CONTENT_UNRECORDED: "stop", UNCLASSIFIED: "stop"})
    on_anomaly: str = "stop"
    on_verification_problem: str = "stop"  # replay_run の期待との不一致・記録の対応の問題
    on_observation_problem: str = "stop"  # 主体別の観測の記録が complete でない（欠け・矛盾・記録の失敗）。観測の記録を有効にした計画だけ


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

    def legality(self, cards: list[str]) -> dict[str, Any]:
        """デッキの合法性（エンジンの deck_problems だけ。この道具は枚数・カードの登録・たねの有無を判定しない）。"""
        from kyuura_engine import deck_problems
        from kyuura_engine.rules import RULES_2000_02_14

        if getattr(self, "_engine", None) is None:
            engine = self.identity()["engine"]
            self._engine = {"version": engine["version"], "behavior_digest": engine["implementation"]["behavior_digest"]}
        problems = list(deck_problems(list(cards)))
        return {"checked_by": "kyuura_engine.deck.deck_problems", "rules": RULES_2000_02_14.id, "engine": dict(self._engine), "ok": not problems,
                "problems": problems}

    def deck_record(self, spec: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        """デッキの指定（固定デッキ ``{"kind": "preset", "preset": 名前}`` か、明示リスト ``{"kind": "decklist", "decklist": 内容, "input": 入力の記録}``）の記録と、
        実行用の並び。記録は内容・展開の順・確認値（内容 content_sha256・展開した並び sha256）・合法性。"""
        from kyuura_engine import preset_deck

        from . import decklist as DL

        if spec.get("kind") == "preset":
            deck = preset_deck(spec["preset"])
            cards = list(deck.cards())
            record = {"kind": "preset", "preset": spec["preset"], "expansion": PRESET_EXPANSION, "cards": len(cards),
                      "sha256": sha256_bytes(canonical(cards).encode()), "content_method": DL.CONTENT_METHOD, "content_sha256": DL.content_sha256(deck.entries)}
        elif spec.get("kind") == "decklist":
            decklist = DL.validate(spec["decklist"])
            cards = DL.expand(decklist["cards"])
            record = DL.describe(decklist)
            if spec.get("input") is not None:
                record["input"] = spec["input"]
        else:
            raise BatchRefused([f"知らないデッキの指定 {spec.get('kind')!r}"])
        record["legality"] = self.legality(cards)
        return record, cards

    @staticmethod
    def deck_spec(record: dict[str, Any]) -> dict[str, Any]:
        """計画のデッキの記録から、もとの指定を作り直す（照合用。外部ファイルは読まない）。"""
        if record.get("kind") == "preset":
            return {"kind": "preset", "preset": record.get("preset")}
        if record.get("kind") == "decklist":
            return {"kind": "decklist", "decklist": {"format": record.get("format"), "label": record.get("label"), "source": record.get("source"),
                                                     "cards": record.get("entries"), "content_sha256": record.get("content_sha256")},
                    "input": record.get("input")}
        return {"kind": record.get("kind")}

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
              game_limits: dict[str, Any] | None = None, decklists: dict[str, Any] | None = None) -> dict[str, Any]:
        """計画の 1 局。``decklists`` は側（"0"・"1"）ごとの明示リスト（``decklist.load_file`` の値）。その側の ``deck0``・``deck1`` は表示用の名前
        （``decklist:<content_sha256 の先頭 12 桁>``）。明示リストが 1 つでもあれば、両側の実行用の並びを ``config.decklists`` に書く（固定デッキの側は PresetDeck.cards() の並び）。"""
        from .runner import Config, Limits

        key, conv_record = self.conventions_key(conventions)
        options = MODES[mode]
        specs = {}
        for side, name in (("0", deck0), ("1", deck1)):
            specs[side] = {"kind": "decklist", **decklists[side]} if decklists and side in decklists else {"kind": "preset", "preset": name}
        records, cards = {}, {}
        for side, spec in specs.items():
            records[side], cards[side] = self.deck_record(spec)
        illegal = [f"{game_id}: デッキ {side} が deck_problems で不合格（対戦を始めない）: {p}" for side in ("0", "1") for p in records[side]["legality"]["problems"]]
        if illegal:
            raise BatchRefused(illegal)
        explicit = any(spec["kind"] == "decklist" for spec in specs.values())
        config = Config(deck0=deck0, deck1=deck1, conventions=key, game_seed=seed, policy_seed=seed, host_seed=seed, limits=Limits(**(game_limits or {})),
                        run_id=game_id, decklists=(tuple(cards["0"]), tuple(cards["1"])) if explicit else None, **options)
        expanded = json.loads(canonical(asdict(config)))
        problems = setting_problems(expanded)
        if problems:
            raise BatchRefused([f"{game_id}: {p}" for p in problems])
        return {"game_id": game_id, "mode": mode, "comparison_group": group, "config": expanded, "decks": records,
                "conventions": {"key": key, "digest": conv_record["digest"]}, "policies": self.policies_of(config)}

    def config_of(self, entry: dict[str, Any]):
        from .runner import Config, Limits

        c = dict(entry["config"])
        c["limits"] = Limits(**c["limits"])
        if c.get("decklists") is not None:
            c["decklists"] = tuple(tuple(side) for side in c["decklists"])
        return Config(**c)

    def check_entry(self, entry: dict[str, Any]) -> list[str]:
        """計画の局の設定が、今のデッキ・規約集合・方策の値と同じか（暗黙に変わっていないか）。"""
        from . import decklist as DL

        gid = entry["game_id"]
        problems = [f"{gid}: {p}" for p in setting_problems(entry["config"])]
        config = self.config_of(entry)
        decks = entry.get("decks") or {}
        explicit = any((decks.get(side) or {}).get("kind") == "decklist" for side in ("0", "1"))
        if (config.decklists is not None) != explicit:
            problems.append(f"{gid}: config.decklists（実行用の並び）とデッキの記録の種類が合わない")
        for side, name in (("0", config.deck0), ("1", config.deck1)):
            recorded = decks.get(side) or {}
            try:
                current, cards = self.deck_record(self.deck_spec(recorded))
            except (DL.DecklistError, BatchRefused, KeyError, TypeError) as error:
                problems.append(f"{gid}: デッキ {side} の記録を照らせない（{type(error).__name__}: {error}）")
                continue
            if current != recorded:
                diff = sorted(k for k in set(current) | set(recorded) if current.get(k) != recorded.get(k))
                problems.append(f"{gid}: デッキ {side}（{name}）の記録が計画と違う {diff}（内容・展開・確認値・合法性）")
            if not current["legality"]["ok"]:
                problems.append(f"{gid}: デッキ {side} が deck_problems で不合格（対戦を始めない）")
            if config.decklists is not None and list(config.decklists[int(side)]) != cards:
                problems.append(f"{gid}: デッキ {side} の実行用の並び（config.decklists）が記録の展開と違う")
            if recorded.get("kind") == "decklist" and name != "decklist:" + str(recorded.get("content_sha256"))[:12]:
                problems.append(f"{gid}: デッキ {side} の表示用の名前 {name} が明示リストの確認値と合わない")
            if recorded.get("kind") == "preset" and name != recorded.get("preset"):
                problems.append(f"{gid}: デッキ {side} の名前 {name} が固定デッキの記録と合わない")
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

        problems = self.check_entry(entry)  # 実行の前の照合（デッキの内容・並び・deck_problems・方式の組・規約集合・方策）。合わなければ対戦を始めない
        if problems:
            raise BatchRefused(problems)
        config = self.config_of(entry)
        recorder = None
        if observation_enabled(plan):
            from .observe import ObservationRecorder

            recorder = ObservationRecorder()  # 局ごとに作り、局のファイルを書いたら捨てる（全局の観測をためない）
        started = now()
        result = run_game(config, recorder=recorder)
        finished = now()
        verification = check_record(result)
        judged = judge_trace(result)
        sequences = {"action": R.sequence_digest(R.action_sequence(result["trace"]), R.ACTION_FORMAT),
                     "contract": R.sequence_digest(R.contract_sequence(result["trace"]), R.CONTRACT_FORMAT)}
        header = game_header(config, R.identity(plan["commits"]["engine"]), ["python", "-m", TOOL_NAME, "run"], result, started, finished)
        header["batch"] = {"game_id": entry["game_id"], "mode": entry["mode"], "comparison_group": entry["comparison_group"],
                           "decks": {side: {k: d.get(k) for k in ("kind", "preset", "label", "expansion", "content_sha256", "sha256")}
                                     for side, d in entry["decks"].items()}}
        files = [("header.json", json_bytes(header)), ("trace.jsonl", jsonl_bytes(result["trace"]))]
        for actor, rows in result["actor_logs"].items():
            files.append((f"actors/{actor}.jsonl", jsonl_bytes(rows)))
        files.append(("full_record.json", dumps_record(result["record"]).encode("utf-8")))
        files.append(("result.json", json_bytes({k: result[k] for k in ("termination", "counters", "anomalies", "coverage", "metrics", "elapsed_seconds",
                                                                         "policies", "limits", "distribution")})))
        files.append(("verification.json", json_bytes(verification)))
        files.append(("judge.json", json_bytes(judged)))
        files.append(("sequences.json", json_bytes(sequences)))
        if recorder is not None:
            files.extend(recorder.files())
        term = result["termination"]
        detail = term["detail"] if isinstance(term["detail"], dict) else {}
        summary = {"termination": term["class"],
                   "termination_detail": {k: detail[k] for k in ("reason", "halt", "result") if k in detail},
                   "counters": result["counters"], "anomalies": [a["kind"] for a in result["anomalies"]],
                   "judge": judge_summary(judged),
                   "replay_run": {k: verification["replay_run"][k] for k in ("expected", "status", "matches_expectation")},
                   "correspondence_problems": len(verification["correspondence_problems"]),
                   "elapsed_seconds": result["elapsed_seconds"], "sequences": sequences}
        if recorder is not None:
            obs = recorder.summary()
            summary["observation"] = {k: obs[k] for k in ("format", "status", "rows", "by_kind", "problem_codes", "problems_total", "failure")}
        return GameOutput(files=files, summary=summary)


# judge.ACCEPTED_CONTENT_NOT_RECORDED と同じ値（batch は judge を遅れて読み込むので、ここに写す。テストで一致を確かめる）
ACCEPTED_CONTENT_NOT_RECORDED_REASONS = ("face_down_power_public_events_not_recorded", "p6_public_events_not_recorded")


def undetermined_category(source: str, reasons: list[str], termination: str | None = None) -> str:
    """undetermined の理由の分類（停止方針で使う）。judge の理由の文字列の先頭で決め、どれにも当たらないものは unclassified（停止の初期値）。"""
    if source == "termination" and termination == "api_contract_unknown":
        return CONTRACT_UNKNOWN
    if source == "termination" and termination == "no_progress":
        return NO_PROGRESS
    first = reasons[0] if reasons else ""
    if first.startswith(("stop_condition_not_evidenced:", "halt_condition_not_evidenced")):
        return EVIDENCE_MISSING_STOP
    if first.startswith(("stop_code_not_in_catalog:", "halt_code_not_in_catalog:")):
        return UNKNOWN_DIAGNOSTIC
    if first.startswith("unknown_outcome:"):
        return CONTRACT_UNKNOWN
    if source == "accepted_content" and first in ACCEPTED_CONTENT_NOT_RECORDED_REASONS:
        return ACCEPTED_CONTENT_UNRECORDED
    return UNCLASSIFIED


def judge_trace(result: dict[str, Any]) -> dict[str, Any]:
    """保存する trace に、既存の judge（規則の版 6）をあとから当てる（runner の進行・方策に影響しない）。単局の runner（V3-1 の変異の実行の中の判定）と同じ入口・引数:

    - 送信（submit を送った試み）ごとに ``judge_normal``（1 つの送信に 1 回。件数は ``counts``）
    - 受理された本人のうらのカードの特殊能力（U-R3a）・P6 のにげるの送信の中身に ``judge_recorded_accepted_content``（runner が受理の直後に記録した公開のログ。
      記録がなければ undetermined。送信の判定とは別の軸で数える＝``accepted_content``。種類ごとは ``by_check``。同じ送信を 2 回数えない）
    - 終わり方に ``judge_run_termination``（halted_known では公開の停止の値を渡す）

    undetermined は 1 つずつ、出どころ・理由・分類（``undetermined_category``）を残す。行には生の診断（diagnostic_id・分類・エンジンのコード）を残す。"""
    from .judge import (JUDGE_RULES_VERSION, KNOWN_STOP, UNDETERMINED, judge_normal, judge_recorded_accepted_content, judge_run_termination,
                        recorded_stop_evidence, revealed_card_id)

    rows, counts, by_kind = [], {}, {}
    content_rows, content_counts, content_by_check = [], {}, {}
    undetermined = []
    for e in result["trace"]:
        if e.get("type") != "attempt" or e.get("submit") is None:
            continue
        # 規則 6: 記録した送信の API の値で代表の条件を満たす停止だけ、そのコードを根拠として渡す（満たさなければ None で、規則 5 と同じ）
        evidence = recorded_stop_evidence(e["candidate"], e.get("meaning") or [], e.get("stages"), e["submit"])
        verdict, why = judge_normal(e["candidate"], e.get("meaning") or [], e["submit"], stages=e.get("stages"), evidence=evidence)
        kind = e["candidate"].get("kind")
        diag = e["submit"].get("verifier") or {}
        rows.append({"attempt": e["n"], "kind": kind, "outcome": e["submit"].get("outcome"), "refusal": (e["submit"].get("refusal") or {}).get("code"),
                     "diagnostic_id": diag.get("diagnostic_id"), "category": diag.get("category"), "engine_code": diag.get("engine_code"),
                     "verdict": verdict, "reasons": why})
        counts[verdict] = counts.get(verdict, 0) + 1
        by_kind.setdefault(kind, {})[verdict] = by_kind.setdefault(kind, {}).get(verdict, 0) + 1
        if verdict == UNDETERMINED:
            undetermined.append({"source": "submit", "attempt": e["n"], "kind": kind, "reasons": why, "category": undetermined_category("submit", why)})
        content = judge_recorded_accepted_content(e)
        if content is not None:
            check, v2, why2 = content
            content_rows.append({"attempt": e["n"], "kind": kind, "check": check, "verdict": v2, "reasons": why2,
                                 "events_recorded": "public_events_after_accept" in e, "revealed_card_id": revealed_card_id(e)})
            content_counts[v2] = content_counts.get(v2, 0) + 1
            content_by_check.setdefault(check, {})[v2] = content_by_check.setdefault(check, {}).get(v2, 0) + 1
            if v2 == UNDETERMINED:
                undetermined.append({"source": "accepted_content", "attempt": e["n"], "kind": kind, "reasons": why2,
                                     "category": undetermined_category("accepted_content", why2)})
    term = result["termination"]
    detail = term["detail"] if isinstance(term["detail"], dict) else {}
    verdict, why = judge_run_termination(term["class"], detail, result["trace"])
    if verdict == UNDETERMINED:
        undetermined.append({"source": "termination", "attempt": None, "kind": None, "reasons": why,
                             "category": undetermined_category("termination", why, term["class"])})
    known_stop = [r["attempt"] for r in rows if r["verdict"] == KNOWN_STOP] + (["termination"] if verdict == KNOWN_STOP else [])
    return {"rules_version": JUDGE_RULES_VERSION, "counts": dict(sorted(counts.items())), "by_kind": by_kind, "rows": rows,
            "accepted_content": {"counts": dict(sorted(content_counts.items())), "by_check": content_by_check, "rows": content_rows},
            "termination": {"verdict": verdict, "reasons": why, "class": term["class"], "halt": detail.get("halt")},
            "undetermined": undetermined, "known_stop": known_stop}


def judge_summary(judged: dict[str, Any]) -> dict[str, Any]:
    """COMPLETE.json の要約に入れる判定（件数と undetermined の一覧。行は judge.json）。"""
    return {"submits": judged["counts"], "accepted_content": judged["accepted_content"]["counts"],
            "accepted_content_by_check": judged["accepted_content"]["by_check"], "termination": judged["termination"],
            "undetermined": judged["undetermined"], "known_stop": len(judged["known_stop"])}


def stop_reasons(summary: dict[str, Any], policy: dict[str, Any], observation_required: bool = False) -> tuple[list[str], list[str]]:
    """完了した局の要約から、停止方針で止める理由と、続けるが数えるもの（note）を返す。

    suspect は送信・受理の中身・終わり方の合計。undetermined は分類ごとに ``on_undetermined`` に従う（知らない分類は止める）。known_stop は ``on_known_stop``。"""
    stop, note = [], []
    term = summary.get("termination")
    if term in policy["stop_terminations"]:
        stop.append(f"termination:{term}")
    elif term not in policy["continue_terminations"] and policy["on_unknown_termination"] == "stop":
        stop.append(f"unknown_termination:{term}")
    judge = summary.get("judge") or {}
    tv = (judge.get("termination") or {}).get("verdict")
    suspect = (judge.get("submits") or {}).get("suspect", 0) + (judge.get("accepted_content") or {}).get("suspect", 0) + (1 if tv == "suspect" else 0)
    if suspect:
        (stop if policy["on_suspect"] == "stop" else note).append(f"suspect:{suspect}")
    if judge.get("known_stop"):
        (stop if policy["on_known_stop"] == "stop" else note).append(f"known_stop:{judge['known_stop']}")
    by_category: dict[str, int] = {}
    for item in judge.get("undetermined") or []:
        by_category[item["category"]] = by_category.get(item["category"], 0) + 1
    for category, n in sorted(by_category.items()):
        (stop if policy["on_undetermined"].get(category, "stop") == "stop" else note).append(f"undetermined:{category}:{n}")
    if tv == "known_limitation":
        note.append("known_limitation:termination")
    if summary.get("anomalies"):
        (stop if policy["on_anomaly"] == "stop" else note).append("anomalies:" + ",".join(sorted(set(summary["anomalies"]))))
    replay = summary.get("replay_run") or {}
    if replay.get("matches_expectation") is not True or summary.get("correspondence_problems"):
        (stop if policy["on_verification_problem"] == "stop" else note).append(
            f"verification:replay={replay.get('status')}/expected={replay.get('expected')},correspondence={summary.get('correspondence_problems')}")
    obs = summary.get("observation")
    if obs is None and observation_required:  # 観測の記録を有効にした計画で、局の要約に記録の状態がない（記録しなかった・要約の欠け）
        (stop if policy.get("on_observation_problem", "stop") == "stop" else note).append("observation:missing")
    elif obs is not None and obs.get("status") != "complete":
        (stop if policy.get("on_observation_problem", "stop") == "stop" else note).append(
            f"observation:{obs.get('status')}:" + ",".join(sorted(obs.get("problem_codes") or {})))
    return stop, note


# ---------------------------------------------------------------- 計画


def batch_dir(out: Path, batch_id: str) -> Path:
    return out / "verifier" / "runs" / batch_id


def observation_enabled(plan: dict[str, Any]) -> bool:
    return bool((plan.get("observation") or {}).get("enabled"))


def required_files(plan: dict[str, Any]) -> tuple[str, ...]:
    """局の必須ファイル（観測の記録を有効にした計画では observe/ の 5 つも必須。欠けた局を完了にしない）。"""
    if not observation_enabled(plan):
        return REQUIRED_FILES
    from .observe import FILES

    return REQUIRED_FILES + tuple(FILES)


def resolve_decks(deck0: str | None, deck1: str | None, decklists: dict[str, Any] | None) -> tuple[dict[str, str], dict[str, Any]]:
    """側ごとに、固定デッキの名前か明示リストのどちらか 1 つ（両方の指定は曖昧なので拒否）。どちらもなければ既定の固定デッキ。"""
    from . import decklist as DL

    decklists = dict(decklists or {})
    problems = [f"知らない側 {side!r}（\"0\"・\"1\" だけ）" for side in sorted(decklists) if side not in ("0", "1")]
    names = {}
    for side, preset in (("0", deck0), ("1", deck1)):
        if side not in decklists:
            names[side] = preset or DEFAULT_DECKS[side]
            continue
        item = decklists[side]
        if preset is not None:
            problems.append(f"デッキ {side}: 固定デッキ {preset!r} と明示リストを同時に指定した（どちらか 1 つ）")
        if type(item) is not dict or set(item) - {"decklist", "input"} or "decklist" not in item:
            problems.append(f"デッキ {side}: 明示リストの指定は decklist（と input）だけ")
            continue
        try:
            item = {"decklist": DL.validate(item["decklist"]), "input": item.get("input")}
        except DL.DecklistError as error:
            problems += [f"デッキ {side}: {p}" for p in error.problems]
            continue
        decklists[side] = item
        names[side] = "decklist:" + item["decklist"]["content_sha256"][:12]
    if problems:
        raise BatchRefused(problems)
    return names, decklists


def make_plan(out: Path, batch_id: str, *, engine_commit: str, tool_commit: str, seeds: list[int], modes: list[str], deck0: str | None = None,
              deck1: str | None = None, conventions: str | None = None, limits: BatchLimits = BatchLimits(), stop_policy: StopPolicy = StopPolicy(),
              adapter=None, note: str = "", game_limits: dict[str, Any] | None = None, observation: bool = False,
              decklists: dict[str, Any] | None = None) -> dict[str, Any]:
    """計画を作って保存する（既にあれば作らない）。並び: seed ごとに方式を並べる（比較の組 = デッキ・規約集合・seed。game_id は局ごとに別）。

    ``decklists`` は側（"0"・"1"）ごとの明示リスト（``decklist.load_file`` の値）。内容は計画に取り込み、再開でファイルを読み直さない。"""
    adapter = adapter or EngineAdapter(engine_commit)
    bdir = batch_dir(out, batch_id)
    if bdir.exists():
        raise BatchRefused([f"{bdir} はすでにある（既存の証跡を上書きしない）"])
    names, decklists = resolve_decks(deck0, deck1, decklists)
    deck0, deck1 = names["0"], names["1"]
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
                                       game_limits=game_limits, **({"decklists": decklists} if decklists else {})))
    if len(games) > limits.max_games:
        raise BatchRefused([f"計画の局数 {len(games)} が上限 {limits.max_games} を超える"])
    plan = {"format": PLAN_FORMAT, "batch_id": batch_id, "written": now(), "identity": adapter.identity(),
            "commits": {"engine": engine_commit, "tool": tool_commit}, "limits": asdict(limits), "stop_policy": _policy_dict(stop_policy),
            "seed_use": "ゲーム・方策・ホストの seed を同じ値にする（runner の player_seed・host_seed・mix_seed で主体ごとに分ける）",
            "order": "seed ごとに方式を並べる", "games": games,
            "observation": {"enabled": bool(observation), "format": "kyuura-vai-observation/1" if observation else None,
                            "note": "主体別の観測・更新・公開ログの記録（observe/。docs/verification-ai-observation.md）。有効なら局の必須ファイルに入る"},
            "decks": {"names": names, "explicit_sides": sorted(decklists),
                      "rules": ["明示リストは計画を作るときに 1 回だけ読み、内容を各局の decks に取り込む（再開でファイルを読み直さない）",
                                "展開: 項目の並びのまま、カード ID を枚数ぶん続けて並べる（固定デッキの PresetDeck.cards() と同じ規則）。ID 順へ並べかえない",
                                "content_sha256 は並びに依らない内容の確認値、sha256 は展開した並び（初期配列）の確認値。同じ内容でも並びが違えば sha256 と対戦は別",
                                "合法性はエンジンの deck_problems だけ。計画を作るとき・再開の照合・各局の開始の前に当て、不合格なら対戦を始めない",
                                "出典（source）は来歴の記録で、信頼性・合法性を保証しない"]},
            "settings": {"supported": [list(c) for c in SUPPORTED_SETTINGS],
                         "note": "方策・プロファイル・分布の組。定義した組だけを計画に書き、別の方式へ読み替えない"},
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
    unknown = sorted(set(d["on_undetermined"]) - set(UNDETERMINED_CATEGORIES))
    if unknown:
        raise BatchRefused([f"知らない undetermined の分類 {unknown}"])
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
        problems.append(f"計画の形式 {plan.get('format')} を知らない（旧形式の計画を新しい版で再開できるとは保証しない）")
    elif not isinstance(plan.get("observation"), dict) or type(plan["observation"].get("enabled")) is not bool:
        problems.append("計画の observation（主体別の観測の記録の設定）がない・形が違う")
    elif not isinstance(plan.get("decks"), dict):
        problems.append("計画の decks（デッキの指定の要約）がない")
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
    required = list(marker.get("required", REQUIRED_FILES))
    missing_from_marker = [name for name in required_files(plan) if name not in required]
    if missing_from_marker:
        problems.append(f"{adir}: {MARKER} の required に計画の必須ファイルがない {missing_from_marker}")
    for name in sorted(set(required) | set(required_files(plan))):
        if name not in table:
            problems.append(f"{adir}: 必須のファイル {name} が表にない")
    on_disk = {p.relative_to(adir).as_posix() for p in adir.rglob("*") if p.is_file()} - {TABLE, MARKER}
    if on_disk != set(table):
        problems.append(f"{adir}: 表とディスクのファイルが違う（余分 {sorted(on_disk - set(table))}・欠け {sorted(set(table) - on_disk)}）")
    for name, digest in table.items():
        path = adir / name
        if path.is_file() and sha256_file(path) != digest:
            problems.append(f"{adir}: {name} の sha256 が表と違う（破損か書きかえ）")
    summary_ = marker.get("summary") if isinstance(marker.get("summary"), dict) else {}
    stop, noted = stop_reasons(summary_, plan["stop_policy"], observation_enabled(plan))
    if marker.get("stop") != stop or marker.get("note") != noted:
        problems.append(f"{adir}: {MARKER} の stop・note が要約から計算した停止の理由と違う（計算 {stop}）")
    if marker.get("evidence") != evidence_verdict(stop):
        problems.append(f"{adir}: {MARKER} の evidence が停止の理由と合わない")
    if observation_enabled(plan):
        from .observe import SUMMARY

        try:
            saved = json.loads((adir / SUMMARY).read_text(encoding="utf-8")).get("status")
        except (OSError, ValueError, AttributeError):
            saved = None
        if saved != (summary_.get("observation") or {}).get("status"):
            problems.append(f"{adir}: {SUMMARY} の状態 {saved} が {MARKER} の要約の観測の状態と違う")
    return marker, problems


def evidence_verdict(stop: list[str]) -> str:
    """完了マーカーの証跡の判定。停止の理由があれば complete_with_stop（記録は保存したが、検証の証跡として成功とは扱わない）。"""
    return "complete_with_stop" if stop else "complete_without_stop"


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
        missing = [name for name in required_files(plan) if name not in table]
        if missing:
            raise OSError(f"必須のファイルがない: {missing}")
        table_bytes = json_bytes(table)
        atomic_write(adir / TABLE, table_bytes)
        stop, noted = stop_reasons(output.summary, policy, observation_enabled(plan))
        marker = {"evidence": evidence_verdict(stop), "format": COMPLETE_FORMAT, "batch_id": plan["batch_id"], "game_id": gid, "attempt": n, "session": session, "written": now(),
                  "plan_sha256": plan_sha, "game_sha256": game_sha(entry), "identity": plan["identity"], "files_table_sha256": sha256_bytes(table_bytes),
                  "required": list(required_files(plan)), "bytes": size, "memory": used_memory, "attempt_seconds": round(elapsed() - start, 3),
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


MANAGEMENT_FILES = ("plan.json", "plan.sha256", LEDGER, LOCK)
DERIVED_FILES = ("aggregate.json",)


def evidence_breakdown(bdir: Path, state: dict[str, Any], public_summary: Path | None = None) -> dict[str, Any]:
    """証跡の量を分けて数える。ゲームの証跡（``game_complete``）は、照合に通った完了の attempt のディレクトリのファイル（表の各ファイル・表・COMPLETE.json）だけで、
    集計・公開の要約・台帳を書いても変わらない。バッチの上限の確かめ（``tree_bytes``）は、ディレクトリ全体（すべての区分）で行う。"""
    complete = {(gid, info["complete"]["attempt"]) for gid, info in state["games"].items() if info["complete"]}
    out = {"management": 0, "game_complete": 0, "attempt_not_complete": 0, "derived": 0, "other": 0}
    files = {k: 0 for k in out}
    within = {"bytes": 0, "files": 0}  # game_complete のうち主体別の観測の記録（observe/）。区分の合計には重ねて足さない
    for path in bdir.rglob("*"):
        if not path.is_file():
            continue
        parts = path.relative_to(bdir).parts
        if parts[0] == "games" and len(parts) >= 4:
            key = "game_complete" if (parts[1], parts[2]) in complete else "attempt_not_complete"
            if key == "game_complete" and parts[3] == "observe":
                within["bytes"] += path.stat().st_size
                within["files"] += 1
        elif len(parts) == 1 and parts[0] in MANAGEMENT_FILES:
            key = "management"
        elif len(parts) == 1 and parts[0] in DERIVED_FILES:
            key = "derived"
        else:
            key = "other"
        out[key] += path.stat().st_size
        files[key] += 1
    if public_summary is not None and public_summary.is_file():
        out["derived"] += public_summary.stat().st_size
        files["derived"] += 1
    return {"bytes": out, "files": files, "game_complete_observation": within,
            "definition": {"game_complete_observation": "game_complete のうち observe/（主体別の観測の記録）の大きさ。区分の合計に重ねて足さない","management": "plan.json・plan.sha256・ledger.jsonl・LOCK", "game_complete": "照合に通った完了の attempt のディレクトリのすべてのファイル",
                           "attempt_not_complete": "完了マーカーのない attempt（中断・失敗・証跡の上限）のディレクトリのファイル",
                           "derived": "aggregate.json と public の summary.json（集計の時点の大きさ）", "other": "上のどれでもないファイル"}}


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
        result = _aggregate(bdir, plan, plan_sha, state, events, broken, out / "public" / "runs" / batch_id / "summary.json")
        atomic_write(bdir / "aggregate.json", json_bytes(result["verifier"]))
        atomic_write(out / "public" / "runs" / batch_id / "summary.json", json_bytes(result["public"]))
        return result
    finally:
        if not holding_lock:
            release_lock(bdir, session)


def _aggregate(bdir: Path, plan: dict[str, Any], plan_sha: str, state: dict[str, Any], events: list[dict[str, Any]], broken: int,
               public_summary: Path | None = None) -> dict[str, Any]:
    games = plan["games"]
    complete = [(g, state["games"][g["game_id"]]["complete"]) for g in games if state["games"][g["game_id"]]["complete"]]
    attempts = [a for g in games for a in state["games"][g["game_id"]]["attempts"]]
    started = [g for g in games if state["games"][g["game_id"]]["attempts"]]
    rows, by = [], {"mode": {}, "decks": {}, "conventions": {}}
    terminations, judge_submits, judge_term, anomalies, counters, coverage, axes, funnel, by_kind_outcome = {}, {}, {}, {}, {}, {}, {}, {}, {}
    replay, stops, notes, seconds, mems, sizes = {}, [], [], [], [], []
    content, undetermined_by, known_stop, term_vs_judge, raw_codes, halts = {}, {}, 0, {}, {}, {}
    content_by_check: dict[str, dict[str, int]] = {}
    observation = {"enabled": observation_enabled(plan), "status": {}, "rows": 0, "by_kind": {}, "problem_codes": {}, "games_without": 0}
    for entry, done in complete:
        s = done["summary"]
        adir = bdir / "games" / entry["game_id"] / done["attempt"]
        marker = json.loads((adir / MARKER).read_text(encoding="utf-8"))
        result = json.loads((adir / "result.json").read_text(encoding="utf-8"))
        _add(terminations, s["termination"])
        for k, v in (s["judge"]["submits"] or {}).items():
            _add(judge_submits, k, v)
        _add(judge_term, s["judge"]["termination"]["verdict"])
        for k, v in (s["judge"].get("accepted_content") or {}).items():
            _add(content, k, v)
        for check, verdicts in (s["judge"].get("accepted_content_by_check") or {}).items():
            for k, v in verdicts.items():
                _add(content_by_check.setdefault(check, {}), k, v)
        for item in s["judge"].get("undetermined") or []:
            bucket = undetermined_by.setdefault(item["category"], {"count": 0, "reasons": {}, "sources": {}})
            bucket["count"] += 1
            _add(bucket["reasons"], (item["reasons"] or [""])[0])
            _add(bucket["sources"], item["source"])
        known_stop += s["judge"].get("known_stop", 0)
        obs = s.get("observation")
        if obs is not None:
            _add(observation["status"], obs["status"])
            observation["rows"] += obs["rows"]
            for k, v in (obs.get("by_kind") or {}).items():
                _add(observation["by_kind"], k, v)
            for k, v in (obs.get("problem_codes") or {}).items():
                _add(observation["problem_codes"], k, v)
        else:
            observation["games_without"] += 1
        tj = term_vs_judge.setdefault(s["termination"], {"games": 0, "verdict": {}, "reasons": {}})
        tj["games"] += 1
        _add(tj["verdict"], s["judge"]["termination"]["verdict"])
        _add(tj["reasons"], ",".join(s["judge"]["termination"]["reasons"]) or "-")
        halt = s["judge"]["termination"].get("halt")
        if halt:
            _add(halts, f"{halt.get('category')}:{halt.get('diagnostic_id')}")
        judged = json.loads((adir / "judge.json").read_text(encoding="utf-8"))
        for row in judged["rows"]:
            if row.get("outcome") != "accepted":
                _add(raw_codes.setdefault(row["verdict"], {}), f"{row.get('outcome')}:{row.get('category')}:{row.get('engine_code') or row.get('refusal')}")
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
            b = by[dim].setdefault(key, {"games": 0, "termination": {}, "judge_submits": {}, "judge_termination": {}, "accepted": 0, "turns": 0, "operations": 0,
                                         "offered_kind": {}, "chosen_kind": {}, "submitted_kind": {}, "accepted_kind": {}, "scope_excluded": {},
                                         "build_failed": {}, "policy_suppressed": 0, "turns_range": [None, None], "accepted_range": [None, None]})
            b["games"] += 1
            _add(b["termination"], s["termination"])
            for k, v in (s["judge"]["submits"] or {}).items():
                _add(b["judge_submits"], k, v)
            _add(b["judge_termination"], s["judge"]["termination"]["verdict"])
            b["accepted"] += s["counters"]["accepted"]
            b["turns"] += s["counters"]["turns"]
            b["operations"] += s["counters"]["operations"]
            b["policy_suppressed"] += s["counters"].get("policy_suppressed", 0)
            for axis in ("offered_kind", "chosen_kind", "accepted_kind", "scope_excluded"):
                _merge(b[axis], result["coverage"].get(axis, {}))
            for kind, k in result["metrics"]["kinds"].items():
                if k["submitted"]:
                    _add(b["submitted_kind"], kind, k["submitted"])
                for why, n in k["build_failed"].items():
                    _add(b["build_failed"], f"{kind}:{why}", n)
            for name, value in (("turns_range", s["counters"]["turns"]), ("accepted_range", s["counters"]["accepted"])):
                lo, hi = b[name]
                b[name] = [value if lo is None else min(lo, value), value if hi is None else max(hi, value)]
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
                  "not_started": len(games) - len(started), "complete_without_stop": sum(1 for _, done in complete if not done["stop"]),
                  "complete_with_stop": sum(1 for _, done in complete if done["stop"])},
        "attempts": {"total": len(attempts), "complete": sum(a["status"] == "complete" for a in attempts),
                     "incomplete": sum(a["status"] == "incomplete" for a in attempts), "invalid": sum(a["status"] == "invalid" for a in attempts)},
        "sessions": {"ended": [{k: e.get(k) for k in ("status", "stop", "elapsed")} for e in sessions], "accounted_seconds": acc,
                     "ledger_broken_lines": broken, "policy_stops": [e.get("game") for e in events if e.get("event") == "policy_stop"],
                     "acknowledged": [e.get("game") for e in events if e.get("event") == "stop_acknowledged"]},
        "terminations": terminations,
        "judge": {"submits": judge_submits, "termination": judge_term, "accepted_content": content, "accepted_content_by_check": content_by_check,
                  "known_stop": known_stop,
                  "undetermined_by_category": undetermined_by, "termination_vs_judge": term_vs_judge, "non_accepted_submits_by_verdict": raw_codes,
                  "halts": halts},
        "anomalies": anomalies, "observation": observation,
        "counters": counters, "replay_run": replay, "by": by,
        "time": {"game_seconds_sum": round(sum(seconds), 3), "game_seconds_max": max(seconds, default=None),
                 "game_seconds_median": statistics.median(seconds) if seconds else None},
        "memory": {"measured_games": len(mems), "peak_working_set_bytes_max": peak,
                   "note": "プロセスの開始からの最大（局ごとの値ではない）。取れない環境では未計測"},
        "evidence": {"game_file_bytes_from_markers": sum(sizes), **evidence_breakdown(bdir, state, public_summary)},
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
    pl.add_argument("--deck0", default=None, help=f"固定デッキ（既定 {DEFAULT_DECKS['0']}）。--decklist0 と同時に指定しない")
    pl.add_argument("--deck1", default=None, help=f"固定デッキ（既定 {DEFAULT_DECKS['1']}）。--decklist1 と同時に指定しない")
    pl.add_argument("--decklist0", default=None, help="明示リストの JSON（kyuura-vai-decklist/1）。計画に取り込む")
    pl.add_argument("--decklist1", default=None, help="明示リストの JSON（kyuura-vai-decklist/1）。計画に取り込む")
    pl.add_argument("--conventions", default=None)
    pl.add_argument("--max-games", type=int, default=BatchLimits.max_games)
    pl.add_argument("--budget-seconds", type=float, default=BatchLimits.budget_seconds)
    pl.add_argument("--evidence-max-mb", type=int, default=BatchLimits.evidence_max_bytes // MB)
    pl.add_argument("--undetermined-evidence-missing", choices=("continue", "stop"), default="continue",
                    help="根拠不足の停止による undetermined の扱い（ほかの分類は止める）")
    pl.add_argument("--note", default="")
    obs = pl.add_mutually_exclusive_group(required=True)  # 既定を置かない（記録の有無を計画ごとに明示する）
    obs.add_argument("--observation", dest="observation", action="store_true", help="主体別の観測・更新・公開ログの記録（observe/）を局の必須ファイルにする")
    obs.add_argument("--no-observation", dest="observation", action="store_false", help="観測の記録をしない")
    dl = sub.add_parser("decklist", help="明示リストの形・確認値・deck_problems を確かめる（計画は作らない・対戦しない）")
    dl.add_argument("--file", required=True)
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
    if args.cmd == "decklist":
        from . import decklist as DL

        try:
            loaded = DL.load_file(Path(args.file))
        except DL.DecklistError as error:
            print(json.dumps({"refused": error.problems}, ensure_ascii=False, indent=1))
            return 2
        record, cards = EngineAdapter().deck_record({"kind": "decklist", **loaded})
        print(json.dumps(record, ensure_ascii=False, indent=1))
        return 0 if record["legality"]["ok"] else 2
    out = Path(args.out)
    try:
        if args.cmd == "plan":
            from . import decklist as DL

            loaded = {}
            for side, path in (("0", args.decklist0), ("1", args.decklist1)):
                if path is not None:
                    try:
                        loaded[side] = DL.load_file(Path(path))
                    except DL.DecklistError as error:
                        raise BatchRefused([f"デッキ {side}: {p}" for p in error.problems]) from None
            limits = BatchLimits(max_games=args.max_games, budget_seconds=args.budget_seconds, evidence_max_bytes=args.evidence_max_mb * MB)
            plan = make_plan(out, args.batch, engine_commit=args.engine_commit, tool_commit=args.tool_commit, seeds=args.seeds, modes=args.modes,
                             deck0=args.deck0, deck1=args.deck1, conventions=args.conventions, limits=limits, note=args.note, observation=args.observation,
                             decklists=loaded or None,
                             stop_policy=StopPolicy(on_undetermined={**StopPolicy().on_undetermined,
                                                                     EVIDENCE_MISSING_STOP: args.undetermined_evidence_missing}))
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
