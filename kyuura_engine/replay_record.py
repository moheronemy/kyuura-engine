"""完全な再現用記録の収集・読み書き・構造の検証（v0.153。docs/replay-record-v0.153.md。仕様案 docs/diagnostics-replay-api-design.md の U3）。

信頼されたホスト・検証者だけが扱う記録です（seed・デッキリスト・すべての操作・確認値を含む）。見る人（本人・相手・観戦者）に渡しません。

- 収集: ``ReplayCollector.start`` が ``adapter.start_game`` で対戦を始め、``submit`` が ``adapter.HostedGame`` で操作を送り、その結果から記録の 1 行を作る。操作と結果を
  別々に渡す入口はない（食い違う記録を作らない）。途中の状態から収集を始める入口もない
- 再現の入力は、見出しの初期の条件と、受理した操作（``outcome`` が ``accepted``）の列だけ。拒否した操作（任意で記録）・確認値（状態と乱数の指紋・ログの長さ・状態）・診断の識別は、
  あとで照らすための値で、入力ではない
- 構造の検証（``validate_record``）は、記録の形・順序・前後の矛盾・完結・この実装で扱えるかを確かめる。エンジンで再実行して確認値と一致することは確かめない（U4）
- 記録の JSON の読み取り（``loads_record``）は、記録の形式の読み取りで、ゲームの状態の復元ではない（状態の JSON から ``GameState`` を作る機能はない）

ハッシュ（実装の識別・確認値）は内容を見分けるための値で、署名・改ざんの防止ではない。
"""

from __future__ import annotations

import hashlib
import json
import platform
import random
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import __version__
from . import diagnostics as D
from .adapter import CommandResult, HostedGame, HostStoppedError, start_game
from .conventions import (
    ConventionSetError,
    registered_identity,
    require_state_conventions,
)
from .rng import RNG_FORMAT, rng_fingerprint
from .rules import RULES_2000_02_14
from .serialize import FORMAT_VERSIONS, state_to_dict
from .state import GameState

REPLAY_FORMAT = 1
SUPPORTED_REPLAY_FORMATS = (1,)
STATE_EXPORT_FORMAT = 35
STATE_CHECK_METHOD = "state-export-35-sha256/1"  # state_to_dict(形式 35) から engine_version を除き、鍵の順・区切りを決めた JSON（UTF-8）の sha256
RNG_CHECK_METHOD = "python-random-getstate-sha256/1"  # rng.rng_fingerprint（random.Random.getstate() の repr の sha256）
IDENTITY_METHOD = "kyuura-package-files-sha256/1"
CHECK_METHODS = {"state": STATE_CHECK_METHOD, "rng": RNG_CHECK_METHOD}
STATE_CHECK_EXCLUDED = ("engine_version",)
# v0.158（U6-S5）: 接続用確認値の方式（snapshot.connection_check。スナップショットの保存する全項目の sha256）。既存の方式（CHECK_METHODS）とは別の名前で、
# 意味を変えない。記録には任意の拡張（見出しの extensions）として明示したときだけ入る（形式の版は 1 のまま。拡張のない記録を、値があるものとして読みかえない）
CONNECTION_CHECK_METHOD = "kyuura-snapshot-state-sha256/1"
EXTENSION_CONNECTION_CHECK = "connection_check"
KNOWN_EXTENSIONS = {EXTENSION_CONNECTION_CHECK: (CONNECTION_CHECK_METHOD,)}  # 見出しにある（lockstep の DIGEST_EXCLUDED と同じ扱い）
MAX_RECORD_BYTES = 64 * 1024 * 1024
MAX_DEPTH = 64

# 実装の識別: パッケージの中の .py と data/*.json。記録と診断の部品（ゲームの処理に使わない）は別の識別にする
INSTRUMENTATION_FILES = ("adapter.py", "diagnostics.py", "replay_record.py", "data/diagnostic_catalog.json")
PACKAGE_ROOT = Path(__file__).resolve().parent
KNOWN_RULES = {RULES_2000_02_14.id: RULES_2000_02_14}

END_CLOSED = "closed"  # ホストが記録を閉じた（対戦の終局とは別。決定待ち・停止のままでも閉じられる）
END_ABORTED = "aborted"  # 処理できない結果（failed）で収集を止めた
ANSWER_COMMANDS = ("resolve_decision", "take_prize", "promote_active")

# 検証の結果の種類（重い順）
MALFORMED = "malformed"  # 形式として不正
INCONSISTENT = "inconsistent"  # 内容・順序が矛盾
INCOMPLETE = "incomplete"  # 途中で切れている（終わりの情報がない）
UNSUPPORTED = "unsupported"  # 形式は読めるが、この実装・環境・規約集合では扱えない
STRUCTURE_VALID = "structure_valid"  # 構造の検証に通った（再実行で一致したことではない）
REPORT_ORDER = (MALFORMED, INCONSISTENT, INCOMPLETE, UNSUPPORTED)


class RecordFormatError(ValueError):
    """記録の JSON を読めない（大きさ・深さ・重なった鍵・JSON の形）。文に入力の値を入れない。"""

    def __init__(self, code: str, path: str = "$"):
        super().__init__(f"記録を読めない: {code}（{path}）")
        self.code = code
        self.path = path


class CollectorStoppedError(Exception):
    """閉じた・止まった収集器に操作を送った。"""


# ---------------------------------------------------------------- 実装・環境の識別


def _normalized(data: bytes) -> bytes:
    """改行を LF にそろえ、先頭の BOM を除く（文字コードは UTF-8。読めなければそのままのバイト）。"""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    return text.removeprefix("﻿").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def package_files(root: Path | None = None) -> list[str]:
    """識別に入れるファイル（パッケージの中の相対パス。/ 区切り・辞書順）。``__pycache__`` を除く。"""
    root = Path(root) if root is not None else PACKAGE_ROOT
    files = [p for p in root.rglob("*.py") if "__pycache__" not in p.parts] + list((root / "data").glob("*.json"))
    return sorted(p.relative_to(root).as_posix() for p in files)


def _digest(root: Path, names) -> str:
    h = hashlib.sha256(b"kyuura-package-files/1\n")
    for name in names:
        content = hashlib.sha256(_normalized((root / name).read_bytes())).hexdigest()
        h.update(f"{name}\0{content}\n".encode())
    return h.hexdigest()


def implementation_identity(root: Path | None = None) -> dict[str, Any]:
    """エンジンの版と、ゲームの処理に関わるファイルの内容の識別（``behavior``）・記録と診断の部品の識別（``instrumentation``）。チェックアウトの場所・改行・Git の有無によらない。"""
    root = Path(root) if root is not None else PACKAGE_ROOT
    names = package_files(root)
    instrumentation = [n for n in names if n in INSTRUMENTATION_FILES]
    behavior = [n for n in names if n not in INSTRUMENTATION_FILES]
    return {"version": _read_version(root), "method": IDENTITY_METHOD, "behavior_digest": _digest(root, behavior), "behavior_files": len(behavior),
            "instrumentation_digest": _digest(root, instrumentation), "instrumentation_files": len(instrumentation)}


def _read_version(root: Path) -> str:
    if root == PACKAGE_ROOT:
        return __version__
    for line in _normalized((root / "__init__.py").read_bytes()).decode("utf-8").splitlines():
        if line.startswith("__version__ = "):
            return line.split("=", 1)[1].strip().strip('"')
    return ""


@lru_cache(maxsize=1)
def current_identity() -> dict[str, Any]:
    return implementation_identity()


def git_commit(root: Path | None = None) -> str | None:
    """補助の情報: パッケージのある Git の木の HEAD（Git がない・木でないなら None）。識別には使わない。"""
    try:
        done = subprocess.run(["git", "-C", str(root or PACKAGE_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    value = done.stdout.strip()
    return value if done.returncode == 0 and len(value) == 40 else None


def runtime_identity() -> dict[str, Any]:
    """再現の保証に関わる実行環境（Python の実装・版と乱数の方式）。OS・パスは入れない。"""
    return {"python_implementation": platform.python_implementation(), "python_version": list(sys.version_info[:3]),
            "rng": {"format": RNG_FORMAT, "state_version": random.Random(0).getstate()[0]}}


# ---------------------------------------------------------------- 確認値


def state_check(state: GameState) -> str:
    data = state_to_dict(state, format_version=STATE_EXPORT_FORMAT)
    for key in STATE_CHECK_EXCLUDED:
        data.pop(key, None)
    text = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def checks(state: GameState) -> dict[str, Any]:
    """受理した操作のあとの確認値（照らすための値。再現の入力ではない）。"""
    d = state.decision
    return {"state": state_check(state), "rng": rng_fingerprint(state.rng), "log_length": len(state.log), "segment": state.segment_index,
            "status": D.status_of(state), "decision": None if d is None else {"id": d.id, "kind": d.kind, "player": d.player},
            "halt": None if state.halt is None else state.halt.code}


def connection_value(state: GameState) -> str | None:
    """接続用確認値（``snapshot.connection_check``）。保存の境界・型の対応を満たさない状態では None（その位置は接続用確認値で確かめられない。値を作り出さない）。"""
    from .snapshot import (  # snapshot は replay_record を読み込むので、ここで読み込む
        SnapshotSaveError,
        connection_check,
    )

    try:
        return connection_check(state)
    except SnapshotSaveError:
        return None


# ---------------------------------------------------------------- 記録


class ReplayRecord:
    """完全な再現用記録（検証者用）。repr に秘密の値を出さない。``data`` は写しを返す。"""

    def __init__(self, data: dict[str, Any]):
        self._data = json.loads(json.dumps(data))

    @property
    def data(self) -> dict[str, Any]:
        return json.loads(json.dumps(self._data))

    def __repr__(self) -> str:
        end = self._data.get("end")
        return (f"ReplayRecord(format={self._data.get(FORMAT_KEY)!r}, operations={len(self._data.get('operations') or [])}, "
                f"end={None if not isinstance(end, dict) else end.get('state')!r})")

    __str__ = __repr__


FORMAT_KEY = "kyuura_replay_format"


def dumps_record(record: ReplayRecord) -> str:
    return json.dumps(record._data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _reject_constant(name):
    raise RecordFormatError("non_finite_number")


def _pairs(pairs):
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise RecordFormatError("duplicate_key")
    return dict(pairs)


def _depth_ok(value) -> bool:
    stack = [(value, 1)]
    while stack:
        item, depth = stack.pop()
        if depth > MAX_DEPTH:
            return False
        if isinstance(item, dict):
            stack.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            stack.extend((v, depth + 1) for v in item)
    return True


def loads_record(text: str | bytes) -> ReplayRecord:
    """記録の JSON を読む（JSON の値だけ。pickle などには変えない）。大きさ・深さ・重なった鍵・数でない数・最上位が辞書でないものは ``RecordFormatError``。
    中身の検証は ``validate_record``。"""
    return ReplayRecord(read_json_object(text))


def read_json_object(text: str | bytes) -> dict[str, Any]:
    """記録の JSON の安全な読み取り（v0.155 で ``loads_record`` から分けた。閲覧用記録の読み取りも使う）。誤りは ``RecordFormatError``（入力の値を文に入れない）。"""
    raw = text if isinstance(text, bytes) else text.encode("utf-8")
    if len(raw) > MAX_RECORD_BYTES:
        raise RecordFormatError("too_large")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_reject_constant)
    except UnicodeDecodeError:
        raise RecordFormatError("not_utf8") from None
    except RecursionError:
        raise RecordFormatError("too_deep") from None
    except json.JSONDecodeError as error:
        raise RecordFormatError("not_json", f"$@{error.pos}") from None
    if not isinstance(data, dict):
        raise RecordFormatError("not_object")
    if not _depth_ok(data):
        raise RecordFormatError("too_deep")
    return data


# ---------------------------------------------------------------- 収集


_START_TOKEN = object()


def _command_type(command: Any) -> str | None:
    return command.get("type") if isinstance(command, dict) and isinstance(command.get("type"), str) else None


class ReplayCollector:
    """信頼されたホストが、対戦の開始から操作の送信・記録まで一体で扱う収集器。``start`` だけで作る（途中の状態から作らない）。

    - 拒否した操作は ``record_rejections`` が真のときだけ記録する（受理した操作の順は ``accepted_index`` で決まる）
    - v0.158: ``connection_checks`` が真のときだけ、見出しに任意の拡張 ``extensions.connection_check`` を書き、開始と受理した操作ごとに接続用確認値
      （``connection_check``。U6-S5 のスナップショットとの接続に使う）を残す。既定は偽（v0.157 までと同じ記録）
    - 処理できない結果（failed）を記録したら収集を止める（``end.state`` が aborted）。そのあとの操作は ``CollectorStoppedError``
    - ``close`` は記録を閉じる（対戦の終局とは別）。閉じたあとの操作は ``CollectorStoppedError``
    - 見る人には ``view``（観測）と ``CommandResult.view_for`` の結果だけを渡す。記録（``record``・``close`` の値）は渡さない"""

    def __init__(self, token, game: HostedGame, header: dict[str, Any], record_rejections: bool):
        if token is not _START_TOKEN:
            raise TypeError("ReplayCollector は ReplayCollector.start で作る（途中の状態から収集を始めない）")
        self._game = game
        self._header = header
        self._record_rejections = record_rejections
        self._connection_checks = EXTENSION_CONNECTION_CHECK in header.get("extensions", {})
        self._operations: list[dict[str, Any]] = []
        self._accepted = 0
        self._last_check = header["start"]["check"]
        self._segments = [{"index": header["start"]["check"]["segment"], "start_seq": 0}]
        self._end: dict[str, Any] | None = None

    @classmethod
    def start(cls, deck0, deck1, seed, *, conventions=None, game_id: str | None = None, record_rejections: bool = True,
              operation_id: str | None = None, include_git: bool = True, connection_checks: bool = False) -> tuple[ReplayCollector | None, CommandResult]:
        """``adapter.start_game`` で対戦を始める（既定のカードプールとルールの組だけ）。開始が拒否・処理できなければ (None, 結果)。
        ``connection_checks`` は v0.158 の任意の拡張（接続用確認値を残す。クラスの説明）。"""
        options = {} if conventions is None else {"conventions": conventions}
        result = start_game(deck0, deck1, seed, operation_id=operation_id, **options)
        if result.outcome != D.ACCEPTED:
            return None, result
        state = result.state
        identity = require_state_conventions(state)
        engine = dict(current_identity())
        if include_git:
            engine["git_commit"] = git_commit()
        header = {
            "game_id": game_id,
            "engine": engine,
            "runtime": runtime_identity(),
            "dependencies": {"rules": state.rules.id, "card_pool": "default",
                             "card_data": {"repository": state.card_data.repository, "commit": state.card_data.commit, "path": state.card_data.path},
                             "effects": state.effects.id},
            "convention_set": identity.record(),
            "formats": {"state_export": STATE_EXPORT_FORMAT, "check_methods": dict(CHECK_METHODS), "diagnostic_schema": D.DIAGNOSTIC_SCHEMA,
                        "diagnostic_catalog_schema": 1},
            "initial": {"decklists": [list(state.decklists[0]), list(state.decklists[1])], "seed": seed, "rules": state.rules.id,
                        "conventions": f"{identity.set_id}@{identity.version}", "card_pool": "default"},
            "rejections_recorded": bool(record_rejections),
            "start": {"operation_id": operation_id, "status": result.status, "check": checks(state)},
        }
        if connection_checks:
            header["extensions"] = {EXTENSION_CONNECTION_CHECK: CONNECTION_CHECK_METHOD}
            header["start"][EXTENSION_CONNECTION_CHECK] = connection_value(state)
        return cls(_START_TOKEN, HostedGame(state), header, record_rejections), result

    @property
    def state(self) -> GameState:
        """ホストの中だけで使う今の状態。"""
        return self._game.state

    @property
    def stopped(self) -> bool:
        return self._end is not None

    @property
    def failure(self) -> CommandResult | None:
        """処理できない結果（failed）を受け取っていれば、その結果。なければ None（v0.173。CN-1）。

        包んだ ``HostedGame`` の値をそのまま返す（収集器は別の失敗の状態を持たない）。``legal_actions.ActionHost``・``client_api.ClientHub`` が包む対戦の形
        （``state``・``submit``・``failure``）にそろえるためで、検証者用の値を含む結果はホストの中だけで使う（見る人に渡さない）。"""
        return self._game.failure

    def view(self, viewer):
        return self._game.view(viewer)

    def submit(self, command, *, submitter: int | None = None, operation_id: str | None = None) -> CommandResult:
        if self._end is not None:
            raise CollectorStoppedError(f"記録は {self._end['state']}（操作を送れない）")
        before = self._game.state
        try:
            result = self._game.submit(command, submitter=submitter, operation_id=operation_id)
        except HostStoppedError:  # pragma: no cover - 収集器は failed のあと先に止まる
            raise CollectorStoppedError("記録は aborted（操作を送れない）") from None
        entry: dict[str, Any] = {"operation_id": operation_id, "actor": result.actor, "submitter": submitter, "segment": before.segment_index,
                                 "command": result.verifier.command, "outcome": result.outcome, "status": result.status}
        if before.decision is not None and _command_type(result.verifier.command) in ANSWER_COMMANDS:
            entry["answers_decision"] = before.decision.id
        if result.outcome == D.ACCEPTED:
            self._accepted += 1
            entry["accepted_index"] = self._accepted
            entry["check"] = checks(result.state)
            if self._connection_checks:
                entry[EXTENSION_CONNECTION_CHECK] = connection_value(result.state)
            self._last_check = entry["check"]
        else:
            entry["diagnostic"] = {"diagnostic_id": result.diagnosis.diagnostic_id, "category": result.diagnosis.category,
                                   "engine_code": result.verifier.engine_code}
            if result.outcome == D.REJECTED and not self._record_rejections:
                return result
        entry["seq"] = len(self._operations) + 1
        self._operations.append(entry)
        if result.outcome == D.ACCEPTED and entry["check"]["segment"] != self._segments[-1]["index"]:
            self._segments.append({"index": entry["check"]["segment"], "start_seq": entry["seq"]})
        if result.outcome == D.FAILED:
            self._end = self._end_info(END_ABORTED)
        return result

    def _end_info(self, state: str) -> dict[str, Any]:
        return {"state": state, "operations": len(self._operations), "accepted": self._accepted, "status": self._last_check["status"],
                "final_check": dict(self._last_check), "segments": [dict(s) for s in self._segments]}

    def record(self) -> ReplayRecord:
        """今までの記録（閉じていなければ ``end`` がない。途中の記録として検証すると incomplete）。"""
        return ReplayRecord({FORMAT_KEY: REPLAY_FORMAT, "header": self._header, "operations": self._operations, "end": self._end})

    def close(self) -> ReplayRecord:
        """記録を閉じる（止まった記録はそのまま返す）。終局でなくても閉じられるが、閉じた記録から対戦を再開する機能はない。"""
        if self._end is None:
            self._end = self._end_info(END_CLOSED)
        return self.record()


# ---------------------------------------------------------------- 構造の検証


@dataclass(frozen=True)
class Problem:
    kind: str  # MALFORMED・INCONSISTENT・INCOMPLETE・UNSUPPORTED
    code: str
    path: str


@dataclass(frozen=True)
class RecordReport:
    """構造の検証の結果。``replay_verified`` はいつも偽（U3 はエンジンで再実行しない）。"""

    status: str
    problems: tuple[Problem, ...]
    complete: bool
    end_state: str | None
    replay_verified: bool = False

    @property
    def structure_valid(self) -> bool:
        return self.status in (STRUCTURE_VALID, UNSUPPORTED)


_HEX = frozenset("0123456789abcdef")


def _is_hex64(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX


def _is_player(value) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool) and value in (0, 1))


def _is_int(value, minimum=0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


class _Checker:
    def __init__(self):
        self.problems: list[Problem] = []

    def add(self, kind, code, path):
        self.problems.append(Problem(kind, code, path))

    def need(self, obj, key, path, test, code="missing_or_bad") -> bool:
        if not isinstance(obj, dict) or key not in obj or not test(obj[key]):
            self.add(MALFORMED, code, f"{path}.{key}")
            return False
        return True


def _check_shape(c: _Checker, check, path) -> bool:
    if not isinstance(check, dict):
        c.add(MALFORMED, "check_missing", path)
        return False
    ok = c.need(check, "state", path, _is_hex64, "check_bad") & c.need(check, "rng", path, _is_hex64, "check_bad")
    ok &= c.need(check, "log_length", path, _is_int, "check_bad") & c.need(check, "segment", path, _is_int, "check_bad")
    ok &= c.need(check, "status", path, lambda v: v in D.STATE_STATUSES, "check_bad")
    ok &= c.need(check, "decision", path, lambda v: v is None or (isinstance(v, dict) and _is_int(v.get("id")) and isinstance(v.get("kind"), str)
                                                                    and _is_player(v.get("player")) and v.get("player") is not None), "check_bad")
    ok &= c.need(check, "halt", path, lambda v: v is None or isinstance(v, str), "check_bad")
    if ok and (check["status"] == D.AWAITING_DECISION) != (check["decision"] is not None):
        c.add(INCONSISTENT, "decision_status_mismatch", path)
    if ok and (check["status"] == D.HALTED) != (check["halt"] is not None):
        c.add(INCONSISTENT, "halt_status_mismatch", path)
    return ok


def declared_extensions(header) -> dict[str, str]:
    """見出しが明示した任意の拡張（v0.158）。ない・形が違えば空（形の誤りは構造の検証が見つける）。"""
    ext = header.get("extensions") if isinstance(header, dict) else None
    return dict(ext) if isinstance(ext, dict) else {}


def _check_extensions(c: _Checker, header) -> None:
    if not isinstance(header, dict) or "extensions" not in header:
        return
    ext = header["extensions"]
    if not isinstance(ext, dict) or not ext or not all(isinstance(v, str) for v in ext.values()):
        c.add(MALFORMED, "extensions_bad", "$.header.extensions")
        return
    for name in sorted(ext):
        if name not in KNOWN_EXTENSIONS:
            c.add(UNSUPPORTED, "extension_unknown", f"$.header.extensions.{name}")
        elif ext[name] not in KNOWN_EXTENSIONS[name]:
            c.add(UNSUPPORTED, "extension_method_unknown", f"$.header.extensions.{name}")


def _check_connection_value(c: _Checker, holder: dict, declared: bool, path: str) -> None:
    """接続用確認値（拡張を明示したときだけ。64 桁の 16 進か None。明示していないのに値があれば矛盾）。"""
    if not declared:
        if EXTENSION_CONNECTION_CHECK in holder:
            c.add(INCONSISTENT, "connection_check_undeclared", f"{path}.{EXTENSION_CONNECTION_CHECK}")
        return
    if EXTENSION_CONNECTION_CHECK not in holder:
        c.add(MALFORMED, "connection_check_missing", f"{path}.{EXTENSION_CONNECTION_CHECK}")
    elif holder[EXTENSION_CONNECTION_CHECK] is not None and not _is_hex64(holder[EXTENSION_CONNECTION_CHECK]):
        c.add(MALFORMED, "connection_check_bad", f"{path}.{EXTENSION_CONNECTION_CHECK}")


def _check_header(c: _Checker, header) -> bool:
    if not isinstance(header, dict):
        c.add(MALFORMED, "header_missing", "$.header")
        return False
    p = "$.header"
    _check_extensions(c, header)
    ok = c.need(header, "engine", p, lambda v: isinstance(v, dict) and isinstance(v.get("version"), str) and v.get("method") == IDENTITY_METHOD
                and _is_hex64(v.get("behavior_digest")) and _is_hex64(v.get("instrumentation_digest")))
    ok &= c.need(header, "runtime", p, lambda v: isinstance(v, dict) and isinstance(v.get("python_implementation"), str)
                 and isinstance(v.get("python_version"), list) and len(v["python_version"]) == 3 and all(_is_int(x) for x in v["python_version"])
                 and isinstance(v.get("rng"), dict))
    ok &= c.need(header, "dependencies", p, lambda v: isinstance(v, dict) and isinstance(v.get("rules"), str) and isinstance(v.get("card_data"), dict)
                 and isinstance(v.get("effects"), str) and v.get("card_pool") == "default")
    ok &= c.need(header, "convention_set", p, lambda v: isinstance(v, dict) and isinstance(v.get("id"), str) and _is_int(v.get("version"), 1)
                 and isinstance(v.get("digest"), str) and isinstance(v.get("members"), list))
    ok &= c.need(header, "formats", p, lambda v: isinstance(v, dict) and _is_int(v.get("state_export"), 1) and isinstance(v.get("check_methods"), dict)
                 and _is_int(v.get("diagnostic_schema"), 1))
    ok &= c.need(header, "rejections_recorded", p, lambda v: isinstance(v, bool))
    initial = header.get("initial")
    if not isinstance(initial, dict):
        c.add(MALFORMED, "initial_missing", f"{p}.initial")
        ok = False
    else:
        q = f"{p}.initial"
        ok &= c.need(initial, "decklists", q, lambda v: isinstance(v, list) and len(v) == 2 and all(
            isinstance(d, list) and d and all(isinstance(x, str) and x for x in d) for d in v), "initial_incomplete")
        ok &= c.need(initial, "seed", q, _is_int, "initial_incomplete")
        ok &= c.need(initial, "rules", q, lambda v: isinstance(v, str), "initial_incomplete")
        ok &= c.need(initial, "conventions", q, lambda v: isinstance(v, str) and "@" in v, "initial_incomplete")
        ok &= c.need(initial, "card_pool", q, lambda v: v == "default", "initial_incomplete")
        if ok and isinstance(header.get("convention_set"), dict):
            cs = header["convention_set"]
            if initial["conventions"] != f"{cs['id']}@{cs['version']}":
                c.add(INCONSISTENT, "conventions_mismatch", f"{q}.conventions")
            if initial["rules"] != header["dependencies"]["rules"]:
                c.add(INCONSISTENT, "rules_mismatch", f"{q}.rules")
    start = header.get("start")
    if not isinstance(start, dict) or not _check_shape(c, start.get("check"), f"{p}.start.check"):
        if not isinstance(start, dict):
            c.add(MALFORMED, "start_missing", f"{p}.start")
        ok = False
    elif start.get("status") != start["check"]["status"]:
        c.add(INCONSISTENT, "start_status_mismatch", f"{p}.start.status")
    if isinstance(start, dict):
        _check_connection_value(c, start, connection_declared(header), f"{p}.start")
    return ok


def _structure(data) -> tuple[list[Problem], bool, str | None]:
    c = _Checker()
    if not isinstance(data, dict):
        return [Problem(MALFORMED, "not_object", "$")], False, None
    fmt = data.get(FORMAT_KEY)
    if not _is_int(fmt, 1):
        c.add(MALFORMED, "format_missing", f"$.{FORMAT_KEY}")
        return c.problems, False, None
    if fmt not in SUPPORTED_REPLAY_FORMATS:
        c.add(UNSUPPORTED, "format_unknown", f"$.{FORMAT_KEY}")
        return c.problems, False, None
    unknown = set(data) - {FORMAT_KEY, "header", "operations", "end"}
    for key in sorted(unknown):
        c.add(MALFORMED, "unknown_field", f"$.{key}")
    header_ok = _check_header(c, data.get("header"))
    header = data.get("header") if isinstance(data.get("header"), dict) else {}
    ops = data.get("operations")
    if not isinstance(ops, list):
        c.add(MALFORMED, "operations_missing", "$.operations")
        ops = []
    rejections_recorded = header.get("rejections_recorded") is True
    start_check = (header.get("start") or {}).get("check") if header_ok else None
    last = dict(start_check) if isinstance(start_check, dict) else None
    segments = [{"index": last["segment"], "start_seq": 0}] if last else []
    accepted = 0
    seen_ids: set[str] = set()
    failed_at = None
    for i, op in enumerate(ops):
        path = f"$.operations[{i}]"
        if not isinstance(op, dict):
            c.add(MALFORMED, "operation_not_object", path)
            continue
        if not c.need(op, "seq", path, _is_int):
            continue
        if op["seq"] != i + 1:
            c.add(INCONSISTENT, "seq_out_of_order", f"{path}.seq")
        outcome = op.get("outcome")
        if outcome not in D.OUTCOMES:
            c.add(MALFORMED, "outcome_unknown", f"{path}.outcome")
            continue
        c.need(op, "actor", path, _is_player)
        c.need(op, "submitter", path, _is_player)
        c.need(op, "segment", path, _is_int)
        command_ok = c.need(op, "command", path, lambda v: _command_type(v) is not None)
        op_id = op.get("operation_id")
        if op_id is not None:
            if not isinstance(op_id, str) or not op_id:
                c.add(MALFORMED, "operation_id_bad", f"{path}.operation_id")
            elif op_id in seen_ids:
                c.add(INCONSISTENT, "operation_id_duplicate", f"{path}.operation_id")
            else:
                seen_ids.add(op_id)
        if command_ok and op.get("submitter") is not None and isinstance(op["command"].get("player"), int) and op["command"]["player"] != op["submitter"] \
                and outcome == D.ACCEPTED:
            c.add(INCONSISTENT, "submitter_mismatch_accepted", path)
        if failed_at is not None:
            c.add(INCONSISTENT, "operation_after_failure", path)
        if last is not None and isinstance(op.get("segment"), int) and op["segment"] != last["segment"]:
            c.add(INCONSISTENT, "segment_mismatch", f"{path}.segment")
        if outcome == D.ACCEPTED:
            accepted += 1
            if op.get("accepted_index") != accepted:
                c.add(INCONSISTENT, "accepted_index_out_of_order", f"{path}.accepted_index")
            if "diagnostic" in op:
                c.add(INCONSISTENT, "accepted_with_diagnostic", path)
            _check_connection_value(c, op, connection_declared(header), path)
            if not _check_shape(c, op.get("check"), f"{path}.check"):
                continue
            check = op["check"]
            if op.get("status") != check["status"]:
                c.add(INCONSISTENT, "status_mismatch", f"{path}.status")
            ctype = _command_type(op.get("command"))
            if last is not None:
                if last["status"] in (D.GAME_OVER, D.HALTED):
                    c.add(INCONSISTENT, "accepted_after_terminal", path)
                if last["status"] == D.SUDDEN_DEATH_PENDING:
                    if ctype != "start_sudden_death":
                        c.add(INCONSISTENT, "sudden_death_requires_start", path)
                    elif check["segment"] != last["segment"] + 1:
                        c.add(INCONSISTENT, "segment_not_advanced", f"{path}.check.segment")
                elif check["segment"] != last["segment"]:
                    c.add(INCONSISTENT, "segment_changed_without_start", f"{path}.check.segment")
                if last["status"] == D.AWAITING_DECISION:
                    if ctype not in ANSWER_COMMANDS:
                        c.add(INCONSISTENT, "decision_not_answered", path)
                    elif op.get("answers_decision") != last["decision"]["id"] or (
                            ctype == "resolve_decision" and op["command"].get("decision") != last["decision"]["id"]):
                        c.add(INCONSISTENT, "wrong_decision_answered", path)
                if check["log_length"] < last["log_length"] and check["segment"] == last["segment"]:
                    c.add(INCONSISTENT, "log_shrank", f"{path}.check.log_length")
            if check["segment"] != (segments[-1]["index"] if segments else check["segment"]):
                segments.append({"index": check["segment"], "start_seq": op["seq"]})
            last = dict(check)
        else:
            if "check" in op or "accepted_index" in op or EXTENSION_CONNECTION_CHECK in op:
                c.add(INCONSISTENT, "check_on_non_accepted", path)
            diag = op.get("diagnostic")
            if not isinstance(diag, dict) or not isinstance(diag.get("diagnostic_id"), str) or diag.get("category") not in D.CATEGORIES:
                c.add(MALFORMED, "diagnostic_missing", f"{path}.diagnostic")
                continue
            if outcome == D.REJECTED:
                if not rejections_recorded:
                    c.add(INCONSISTENT, "rejection_not_announced", path)
                if diag["category"] in (D.INTERNAL_ERROR, D.STATE_INTEGRITY):
                    c.add(INCONSISTENT, "failure_recorded_as_rejection", f"{path}.diagnostic")
                if last is not None and op.get("status") not in (last["status"], D.NOT_STARTED):
                    c.add(INCONSISTENT, "rejection_changed_status", f"{path}.status")
            else:
                if diag["category"] not in (D.INTERNAL_ERROR, D.STATE_INTEGRITY, D.UNMAPPED) or op.get("status") != D.UNAVAILABLE:
                    c.add(INCONSISTENT, "failure_kind_mismatch", f"{path}.diagnostic")
                failed_at = op["seq"]
    end = data.get("end")
    end_state = None
    if end is None:
        c.add(INCOMPLETE, "end_missing", "$.end")
    elif not isinstance(end, dict) or end.get("state") not in (END_CLOSED, END_ABORTED):
        c.add(MALFORMED, "end_bad", "$.end")
    else:
        end_state = end["state"]
        if end.get("operations") != len(ops):
            c.add(INCONSISTENT, "end_operation_count", "$.end.operations")
        if end.get("accepted") != accepted:
            c.add(INCONSISTENT, "end_accepted_count", "$.end.accepted")
        if last is not None and end.get("final_check") != last:
            c.add(INCONSISTENT, "end_final_check", "$.end.final_check")
        if last is not None and end.get("status") != last["status"]:
            c.add(INCONSISTENT, "end_status", "$.end.status")
        if end.get("segments") != segments:
            c.add(INCONSISTENT, "end_segments", "$.end.segments")
        if (end_state == END_ABORTED) != (failed_at is not None):
            c.add(INCONSISTENT, "end_state_failure_mismatch", "$.end.state")
    return c.problems, end_state is not None and not any(p.kind == INCOMPLETE for p in c.problems), end_state


def connection_declared(header) -> bool:
    """接続用確認値の拡張を、知っている方式で明示しているか。"""
    return declared_extensions(header).get(EXTENSION_CONNECTION_CHECK) in KNOWN_EXTENSIONS[EXTENSION_CONNECTION_CHECK]


def support_problems(data: dict[str, Any], *, identity: dict[str, Any] | None = None, runtime: dict[str, Any] | None = None) -> list[Problem]:
    """この実装・環境・規約集合で扱えるか（扱えなければ UNSUPPORTED の問題）。値は返さない（どの項目が合わないかだけ）。"""
    problems: list[Problem] = []
    header = data.get("header") if isinstance(data, dict) else None
    if not isinstance(header, dict):
        return problems
    identity = identity or current_identity()
    runtime = runtime or runtime_identity()

    def bad(code, path):
        problems.append(Problem(UNSUPPORTED, code, path))

    engine = header.get("engine") or {}
    if engine.get("behavior_digest") != identity["behavior_digest"] or engine.get("method") != IDENTITY_METHOD:
        bad("implementation_differs", "$.header.engine.behavior_digest")
    if engine.get("version") != identity["version"]:
        bad("engine_version_differs", "$.header.engine.version")
    rt = header.get("runtime") or {}
    if rt.get("python_implementation") != runtime["python_implementation"] or list(rt.get("python_version") or [])[:2] != runtime["python_version"][:2]:
        bad("runtime_differs", "$.header.runtime")
    if rt.get("rng") != runtime["rng"]:
        bad("rng_scheme_differs", "$.header.runtime.rng")
    formats = header.get("formats") or {}
    if formats.get("state_export") not in FORMAT_VERSIONS or formats.get("state_export") != STATE_EXPORT_FORMAT:
        bad("state_export_format_unsupported", "$.header.formats.state_export")
    if formats.get("check_methods") != CHECK_METHODS:
        bad("check_method_unknown", "$.header.formats.check_methods")
    if formats.get("diagnostic_schema") != D.DIAGNOSTIC_SCHEMA:
        bad("diagnostic_schema_unsupported", "$.header.formats.diagnostic_schema")
    deps = header.get("dependencies") or {}
    rules = KNOWN_RULES.get(deps.get("rules"))
    if rules is None:
        bad("rules_unknown", "$.header.dependencies.rules")
    from .cards import load_card_pool

    pool = load_card_pool()
    if deps.get("card_data") != {"repository": pool.source["repository"], "commit": pool.source["commit"], "path": pool.source["path"]}:
        bad("card_data_differs", "$.header.dependencies.card_data")
    if deps.get("effects") != pool.effects.id:
        bad("effects_differs", "$.header.dependencies.effects")
    cs = header.get("convention_set") or {}
    try:
        registered = registered_identity((cs.get("id"), cs.get("version")))
    except (ConventionSetError, TypeError):  # 知らない集合・形の合わない識別
        registered = None
    if registered is None or registered.record() != cs:
        bad("convention_set_unsupported", "$.header.convention_set")
    return problems


def validate_record(record: ReplayRecord | dict[str, Any], *, check_support: bool = True) -> RecordReport:
    """記録の構造の検証。結果の ``status`` は malformed・inconsistent・incomplete・unsupported・structure_valid の重い順の 1 つ。

    structure_valid は「形・順序・前後の矛盾・完結・扱える範囲に問題が見つからない」ことで、エンジンで再実行して確認値と一致したことではない（``replay_verified`` はいつも偽）。"""
    data = record._data if isinstance(record, ReplayRecord) else record
    problems, complete, end_state = _structure(data)
    if check_support and not any(p.kind == MALFORMED for p in problems) and isinstance(data, dict) and data.get(FORMAT_KEY) in SUPPORTED_REPLAY_FORMATS:
        problems += support_problems(data)
    kinds = {p.kind for p in problems}
    status = next((k for k in REPORT_ORDER if k in kinds), STRUCTURE_VALID)
    return RecordReport(status=status, problems=tuple(problems), complete=complete, end_state=end_state)
