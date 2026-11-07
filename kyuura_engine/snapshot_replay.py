"""完全な再現用記録とスナップショットの接続（U6-S5。v0.158。docs/state-snapshot-v0.158.md）。

信頼されたホスト・検証者だけが使います（記録・スナップショット・接続用確認値・照合の詳細は seed・非公開のカード・乱数を含む）。見る人に渡しません。

完全な再現用記録（U3）の決まった位置と、その位置の状態のスナップショット（U6）をつなぎ、スナップショットから復元した状態から記録の残りの行を U4 と同じ処理
（``replay_run.run_rows``・``run_end``）で照らす。記録を収集し直さない（``ReplayCollector`` は新しい対戦の開始からだけ）。新しい記録の行を継ぎ足さない。

接続位置（``RecordPosition``）:

- ``initial``: 初期化が終わった直後・最初の操作の前（seq 0）
- ``after_operation``: 記録の ``seq`` の行の処理が終わった直後。拒否の行の直後も、状態は変わらないが記録の中の別の位置として扱う（残りは seq+1 から）。失敗の行の直後は扱わない
- ``accepted_index`` だけでは位置を決めない。``record`` に ``record_identity`` を入れると、別の記録への誤接続を見つける（識別は内容を見分ける値で、認証ではない）

接続の確かめ（どれかが合わなければ続けない）: 記録の構造 → この実装・環境・規約集合で扱えるか → 接続位置 → スナップショットの復元（形式・対応・整合）→
記録とスナップショットの識別・初期の条件・依存・規約集合 → その位置の確認値（状態・乱数・ログの長さ・区間・状態の知らせ・決定・停止）→ 保存する全項目の一致
（記録の前半を今回再実行して得た状態と比べる ``prefix_replay``、または記録の任意の拡張の接続用確認値と比べる ``connection_check``）。

既存の確認値（形式 35 の sha256 と乱数の指紋）は、スナップショットの保存する項目の一部（decklists・CardInstance.origin・カードの定義の解決・型とログのイベントの鍵の順）
を見ないので、それだけで接続を検証済みとしない（docs/state-snapshot-v0.158.md 4 章）。

例外の扱いは adapter・U4 と同じ（想定外の例外は internal_error。``MemoryError`` と ``Exception`` の子でない終了は捕まえない）。
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import traceback as _traceback
from dataclasses import dataclass
from typing import Any

from . import diagnostics as D
from . import snapshot as SN
from .errors import EngineError
from .replay_record import (
    EXTENSION_CONNECTION_CHECK,
    INCONSISTENT,
    MALFORMED,
    UNSUPPORTED,
    Problem,
    RecordReport,
    ReplayRecord,
    checks,
    connection_declared,
    support_problems,
    validate_record,
)
from .replay_run import (
    DIVERGED,
    INCOMPLETE,
    INTERNAL_ERROR,
    INVALID_RECORD,
    NOT_SUPPORTED,
    RECORDED_FAILURE,
    SUCCEEDED,
    Mismatch,
    ReplayRunReport,
    _diff_checks,
    _Run,
    run_end,
    run_rows,
    run_start,
)
from .snapshot import (
    RestoreReport,
    SnapshotSaveError,
    StateSnapshot,
    connection_check,
    loads_snapshot,
    restore_snapshot,
    state_items,
)
from .state import GameState

RECORD_IDENTITY_METHOD = "kyuura-replay-header-sha256/1"  # 記録の見出しの JSON（鍵の順・区切りを決めた UTF-8）の sha256。記録を見分ける値で、認証ではない

POSITION_INITIAL = "initial"
POSITION_AFTER = "after_operation"
POSITION_KINDS = (POSITION_INITIAL, POSITION_AFTER)

# 接続の根拠
BASIS_PREFIX = "prefix_replay"  # 記録の初期の条件から接続位置まで今回再実行して得た状態と、復元した状態の保存する全項目を比べた
BASIS_CONNECTION_CHECK = "connection_check"  # 記録の任意の拡張の接続用確認値と、復元した状態の接続用確認値を比べた

# 検証の範囲
SCOPE_FROM_CONNECTION = "from_connection"  # 接続位置のあとの行（と終わりの情報）だけを再実行して照らした
SCOPE_WHOLE_RECORD = "whole_record"  # 前半も今回再実行して照らし、記録の全体を照らした

# 結果（U4 の語彙に、スナップショット・接続位置・接続の不一致を加えた）
INVALID_SNAPSHOT = "invalid_snapshot"  # スナップショットを読めない・形式が正しくない・状態が整合しない
INVALID_POSITION = "invalid_position"  # 接続位置が記録の中にない・失敗の行の直後
CONNECTION_MISMATCH = "connection_mismatch"  # スナップショットが記録のその位置の状態と一致しない（別の記録・別の位置・別の区間・違う状態）
RESULTS = (SUCCEEDED, INCOMPLETE, RECORDED_FAILURE, NOT_SUPPORTED, INVALID_RECORD, INVALID_SNAPSHOT, INVALID_POSITION, CONNECTION_MISMATCH, DIVERGED,
           INTERNAL_ERROR)

# 最初の不一致・失敗が起きた部分
PHASE_PREFIX = "prefix"  # 前半の再実行（記録が初期の条件から再現しない）
PHASE_CONNECTION = "connection"  # 接続の確かめ
PHASE_SUFFIX = "suffix"  # 残りの行・終わりの情報

LOCATION_CONNECTION = "connection"


def record_identity(record: ReplayRecord | dict[str, Any]) -> str:
    """記録の識別（見出しの sha256。``RECORD_IDENTITY_METHOD``）。同じ対戦でも、拒否を記録したか・拡張・実装の識別が違えば別の記録。署名・認証ではない。"""
    data = record.data if isinstance(record, ReplayRecord) else record
    header = data.get("header") if isinstance(data, dict) else None
    text = json.dumps(header, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(f"{RECORD_IDENTITY_METHOD}\n{text}".encode()).hexdigest()


def _is_seq(value) -> bool:
    return type(value) is int


@dataclass(frozen=True)
class RecordPosition:
    """完全な再現用記録の中の接続位置。``initial``（seq 0）か、``after_operation``（その seq の行の直後。1 以上）。``record`` は任意の記録の識別（``record_identity``）。"""

    kind: str
    seq: int
    record: str | None = None

    def __post_init__(self):
        if self.kind not in POSITION_KINDS:
            raise ValueError("接続位置の種類は initial か after_operation")
        if not _is_seq(self.seq) or (self.kind == POSITION_INITIAL and self.seq != 0) or (self.kind == POSITION_AFTER and self.seq < 1):
            raise ValueError("initial の seq は 0、after_operation の seq は 1 以上の整数")
        if self.record is not None and not (type(self.record) is str and len(self.record) == 64 and all(c in "0123456789abcdef" for c in self.record)):
            raise ValueError("record は record_identity の値（64 桁の 16 進）")

    @classmethod
    def initial(cls, *, record: str | None = None) -> RecordPosition:
        return cls(POSITION_INITIAL, 0, record)

    @classmethod
    def after(cls, seq: int, *, record: str | None = None) -> RecordPosition:
        return cls(POSITION_AFTER, seq, record)


@dataclass(frozen=True)
class ResumeReport:
    """接続と残りの再実行の結果（検証者用）。

    - ``status``: ``RESULTS`` の 1 つ。``succeeded`` は、照らした範囲（``scope``）の最後まで一致したこと
    - ``scope``: ``whole_record``（前半も今回再実行して全体を照らした）か ``from_connection``（接続位置のあとだけ）。接続を確かめる前に止まれば None
    - ``replay_verified``: 記録の全体を照らして成功したときだけ真（``from_connection`` の成功では偽）
    - ``connection_basis``: 接続の根拠（``prefix_replay``・``connection_check``）。``connection_verified``: 接続を確かめ終えたか
    - ``verified_from``: 照らした行の範囲の始まり（その seq の行の後から。全体なら 0 で、開始の確認値も含む）。``verified_seq``・``verified_accepted``: 一致した最後の行の seq と
      それまでの受理の数
    - ``mismatch``・``phase``: 最初の不一致とその部分（prefix・connection・suffix）。``failure``: 再実行で起きた失敗の検証者用の記録
    - ``restore``: スナップショットの復元の結果（restored でなければ、その結果の種類と問題の場所）"""

    status: str
    position: RecordPosition
    scope: str | None
    prefix_replayed: bool
    connection_basis: tuple[str, ...]
    connection_verified: bool
    verified_from: int | None
    verified_seq: int | None
    verified_accepted: int | None
    start_verified: bool
    end_verified: bool
    mismatch: Mismatch | None
    phase: str | None
    failure: D.VerifierReport | None = dataclasses.field(default=None, repr=False)
    problems: tuple[Problem, ...] = ()
    structure: RecordReport | None = dataclasses.field(default=None, repr=False)
    restore: RestoreReport | None = dataclasses.field(default=None, repr=False)

    @property
    def succeeded(self) -> bool:
        return self.status == SUCCEEDED

    @property
    def replay_verified(self) -> bool:
        """記録の全体（開始・すべての行・終わりの情報）を今回照らして一致した。"""
        return self.status == SUCCEEDED and self.scope == SCOPE_WHOLE_RECORD

    @property
    def suffix_verified(self) -> bool:
        """接続位置のあとの行と終わりの情報が一致した（前半を照らしたかは ``scope``）。"""
        return self.status == SUCCEEDED

    def __repr__(self) -> str:
        return (f"ResumeReport(status={self.status!r}, position={self.position.kind}:{self.position.seq}, scope={self.scope!r}, "
                f"basis={self.connection_basis!r}, verified_from={self.verified_from!r}, verified_seq={self.verified_seq!r}, phase={self.phase!r}, "
                f"mismatch={self.mismatch!r})")

    __str__ = __repr__


class _Progress:
    """結果を作るための途中の値（例外のときもどこまで進んだかを返す）。"""

    def __init__(self, position: RecordPosition):
        self.position = position
        self.phase: str | None = None
        self.prefix_replayed = False
        self.basis: list[str] = []
        self.connection_verified = False
        self.structure: RecordReport | None = None
        self.restore: RestoreReport | None = None
        self.run: _Run | None = None
        self.verified_from: int | None = None

    def report(self, status: str, *, mismatch: Mismatch | None = None, failure=None, problems=(), phase: str | None = None) -> ResumeReport:
        run = self.run
        scope = None
        if self.connection_verified:
            scope = SCOPE_WHOLE_RECORD if BASIS_PREFIX in self.basis else SCOPE_FROM_CONNECTION
        return ResumeReport(status=status, position=self.position, scope=scope, prefix_replayed=self.prefix_replayed, connection_basis=tuple(self.basis),
                            connection_verified=self.connection_verified, verified_from=self.verified_from,
                            verified_seq=None if run is None else run.verified_seq, verified_accepted=None if run is None else run.verified_accepted,
                            start_verified=bool(run and run.start_verified), end_verified=bool(run and run.end_verified), mismatch=mismatch,
                            phase=phase if phase is not None else (self.phase if status not in (SUCCEEDED, INCOMPLETE) else None),
                            failure=failure, problems=tuple(problems), structure=self.structure, restore=self.restore)

    def from_run(self, run_report: ReplayRunReport) -> ResumeReport:
        return self.report(run_report.status, mismatch=run_report.mismatch, failure=run_report.failure, problems=run_report.problems)


def replay_from_snapshot(record: ReplayRecord | dict[str, Any], snapshot: StateSnapshot | str | bytes, position: RecordPosition, *,
                         replay_prefix: bool = True) -> ResumeReport:
    """記録の ``position`` にスナップショットをつなぎ、復元した状態から記録の残りの行を U4 と同じ処理で照らす。

    ``replay_prefix`` が真（既定）なら、記録の初期の条件から接続位置まで今回再実行し、得た状態とスナップショットの全項目を比べる（旧記録もこの方法で扱える。結果の範囲は
    ``whole_record``）。偽なら、記録の任意の拡張の接続用確認値だけで接続を確かめる（範囲は ``from_connection``）。その値がない記録・位置では、検証済みとして続けず unsupported を返す。
    記録・スナップショット・位置の型が違えば ``TypeError``（使い方の誤り）。不正・非対応・不一致の入力では例外を投げず、結果を返す。"""
    if not isinstance(record, (ReplayRecord, dict)):
        raise TypeError("record には ReplayRecord か記録の辞書を渡す")
    if not isinstance(snapshot, (StateSnapshot, str, bytes)):
        raise TypeError("snapshot には StateSnapshot か JSON の文字列を渡す")
    if not isinstance(position, RecordPosition):
        raise TypeError("position には RecordPosition を渡す")
    progress = _Progress(position)
    try:
        return _resume(progress, record.data if isinstance(record, ReplayRecord) else record, snapshot, position, replay_prefix)
    except Exception as error:  # 接続と再実行の境界: 記録にない例外は内部エラーの結果（不一致・未対応に変えない。traceback は検証者用）
        if isinstance(error, MemoryError):
            raise
        failure = D.VerifierReport(mapped=False, engine_code=getattr(error, "code", None) if isinstance(error, EngineError) else None,
                                   exception_type=type(error).__name__, raw_message=str(error), traceback="".join(_traceback.format_exception(error)),
                                   exception=error)
        return progress.report(INTERNAL_ERROR, failure=failure, problems=(Problem(INTERNAL_ERROR, "internal_error", "$"),))


def _recorded_at(data: dict[str, Any], seq: int) -> tuple[dict[str, Any], int]:
    """位置の状態の確認値を持つもの（開始か、seq 以前の最後の受理の行）と、そこまでの受理の数。拒否の行は状態を変えないので、前の受理の値を使う。"""
    header = data["header"]
    holder, accepted = header["start"], 0
    for op in data["operations"][:seq]:
        if op["outcome"] == D.ACCEPTED:
            holder, accepted = op, accepted + 1
    return holder, accepted


def _resume(progress: _Progress, data: dict[str, Any], snapshot, position: RecordPosition, replay_prefix: bool) -> ResumeReport:
    # 1. 記録の構造と、この実装・環境・規約集合で扱えるか（U4 と同じ）
    progress.phase = PHASE_CONNECTION
    structure = validate_record(data, check_support=False)
    progress.structure = structure
    if structure.status in (MALFORMED, INCONSISTENT):
        return progress.report(INVALID_RECORD, problems=structure.problems)
    unsupported = tuple(p for p in structure.problems if p.kind == UNSUPPORTED)
    if unsupported:
        return progress.report(NOT_SUPPORTED, problems=unsupported)
    support = tuple(support_problems(data))
    if support:
        return progress.report(NOT_SUPPORTED, problems=support)
    header, ops = data["header"], data["operations"]

    # 2. 接続位置（記録の識別・記録の中にあるか・失敗の行の直後でないか）
    if position.record is not None and position.record != record_identity(data):
        return progress.report(CONNECTION_MISMATCH, problems=(Problem(CONNECTION_MISMATCH, "record_differs", "$.position.record"),))
    if position.seq > len(ops):
        return progress.report(INVALID_POSITION, problems=(Problem(INVALID_POSITION, "seq_out_of_range", "$.position.seq"),))
    if position.seq and ops[position.seq - 1]["outcome"] == D.FAILED:
        return progress.report(INVALID_POSITION, problems=(Problem(INVALID_POSITION, "after_failure", f"$.operations[{position.seq - 1}]"),))

    # 3. スナップショットの復元（読み取り・形式・対応・整合。U6 の段 1〜7）
    restored = restore_snapshot(snapshot)
    progress.restore = restored
    if restored.status in (SN.READ_ERROR, SN.MALFORMED, SN.INCONSISTENT):  # 状態の不整合も、不一致・未対応にまとめない
        return progress.report(INVALID_SNAPSHOT, problems=restored.problems)
    if restored.status == SN.NOT_SUPPORTED:
        return progress.report(NOT_SUPPORTED, problems=restored.problems)
    if restored.status == SN.INTERNAL_ERROR:
        return progress.report(INTERNAL_ERROR, problems=restored.problems)
    state = restored.state
    snap = (snapshot if isinstance(snapshot, StateSnapshot) else loads_snapshot(snapshot)).data

    # 4. 識別・初期の条件・依存・規約集合・その位置の確認値（安い確かめを先にする。違えば前半を再実行しない）
    holder, accepted = _recorded_at(data, position.seq)
    mismatch = _identity_mismatch(header, snap, state, holder, position, accepted)
    if mismatch is not None:
        return progress.report(CONNECTION_MISMATCH, mismatch=mismatch)

    # 5. 保存する全項目の一致: 記録の接続用確認値（任意の拡張）と、前半の再実行
    anchor = holder.get(EXTENSION_CONNECTION_CHECK) if connection_declared(header) else None
    if anchor is not None:
        value = _connection_value(state)
        if value != anchor:
            return progress.report(CONNECTION_MISMATCH, mismatch=Mismatch(LOCATION_CONNECTION, position.seq, accepted, (EXTENSION_CONNECTION_CHECK,),
                                                                           {EXTENSION_CONNECTION_CHECK: anchor}, {EXTENSION_CONNECTION_CHECK: value}))
        progress.basis.append(BASIS_CONNECTION_CHECK)
    run = _Run(structure, support)
    progress.run = run
    if replay_prefix:
        progress.phase = PHASE_PREFIX
        progress.prefix_replayed = True
        run_report, replayed = run_start(run, data)
        if run_report is None:
            run_report, replayed, _count = run_rows(run, data, replayed, 0, position.seq, 0)
        if run_report is not None:
            return progress.from_run(run_report)
        progress.phase = PHASE_CONNECTION
        items = _state_differences(replayed, state)
        if items:
            return progress.report(CONNECTION_MISMATCH, mismatch=Mismatch(LOCATION_CONNECTION, position.seq, accepted, items, {}, {}))
        progress.basis.append(BASIS_PREFIX)
    elif anchor is None:
        code = "connection_check_unavailable" if connection_declared(header) else "connection_check_absent"
        return progress.report(NOT_SUPPORTED, problems=(Problem(UNSUPPORTED, code, "$.header.extensions" if code.endswith("absent") else "$.operations"),))
    progress.connection_verified = True
    progress.verified_from = 0 if replay_prefix else position.seq
    run.verified_seq, run.verified_accepted = position.seq, accepted

    # 6. 残りの行を元の seq の順に（拒否・失敗の行も）復元した状態から送り、終わりの情報を照らす（U4 と同じ処理）
    progress.phase = PHASE_SUFFIX
    run_report, state, accepted = run_rows(run, data, state, position.seq, len(ops), accepted)
    if run_report is None:
        run_report = run_end(run, data, state, accepted)
    return progress.from_run(run_report)


def _connection_value(state: GameState) -> str | None:
    try:
        return connection_check(state)
    except SnapshotSaveError:  # 復元に成功した状態は保存の境界を満たすので、ここへは来ない想定（来れば一致しない値として扱う）
        return None


def _identity_mismatch(header: dict[str, Any], snap: dict[str, Any], state: GameState, holder: dict[str, Any], position: RecordPosition,
                       accepted: int) -> Mismatch | None:
    """記録とスナップショットの識別・初期の条件・依存・規約集合・位置の確認値を比べる。項目の名前だけで違いを表す（値は検証者用の Mismatch の中だけ）。"""
    initial = header["initial"]
    recorded: dict[str, Any] = {}
    restored: dict[str, Any] = {}

    def compare(name: str, a, b) -> None:
        if a != b:
            recorded[name], restored[name] = a, b

    origin = snap.get("origin") or {}
    if "game_id" in origin:
        compare("origin.game_id", header.get("game_id"), origin["game_id"])
    if "seq" in origin:
        compare("origin.seq", position.seq, origin["seq"])
    compare("initial.decklists", initial["decklists"], [list(d) for d in state.decklists])
    compare("initial.seed", initial["seed"], state.seed)
    compare("initial.rules", initial["rules"], state.rules.id)
    compare("convention_set", header["convention_set"], snap["convention_set"])
    compare("dependencies", header["dependencies"], snap["dependencies"])
    expected = dict(holder["check"])
    got = checks(state)
    for key in _diff_checks(expected, got):
        recorded[f"check.{key}"], restored[f"check.{key}"] = expected.get(key), got.get(key)
    if not recorded:
        return None
    return Mismatch(LOCATION_CONNECTION, position.seq, accepted, tuple(recorded), recorded, restored)


def _state_differences(replayed: GameState, restored: GameState) -> tuple[str, ...]:
    """前半を再実行した状態と復元した状態の、保存する全項目の違い（項目の名前。値は出さない）。項目の順（ログのイベントの鍵の順）も比べる。"""
    a, b = state_items(replayed), state_items(restored)
    names = [f"state.{name}" for name in a if json.dumps(a[name], ensure_ascii=False) != json.dumps(b.get(name), ensure_ascii=False)]
    names += [f"state.{name}" for name in b if name not in a]
    if not names and connection_check(replayed) != connection_check(restored):  # pragma: no cover - 項目ごとに同じなら同じ（念のための確かめ）
        names.append(EXTENSION_CONNECTION_CHECK)
    return tuple(names)
