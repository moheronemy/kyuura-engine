"""完全な再現用記録の再実行と確認値の照合（v0.154。docs/replay-run-v0.154.md。仕様案 docs/diagnostics-replay-api-design.md の U4）。

信頼されたホスト・検証者だけが使います（記録・結果は seed・操作・確認値・例外の詳細を含む）。

流れ: 構造の検証（``replay_record.validate_record``）→ この実装・環境・規約集合で扱えるか（``support_problems``）→ 扱えなければ対戦を作らずに返す → 記録の初期の条件から
``adapter.start_game`` で対戦を作り、開始の確認値を照らす → 記録の行を ``seq`` の順に（受理・拒否・失敗のどれも）``adapter.submit`` で送り、結果と確認値を照らし、最初の不一致で止める →
終わりの情報を照らす。

- 方策を再実行しない（記録のコマンドと答えを送る）。乱数を各操作の前へ戻さず、コインの結果を入れない
- 理由の文は照らさない（記録は文を持たない。説明用で版で変わりうる。仕様案 4.5 節）。診断の識別・分類・元のコードは照らす
- 確認値は形式 35 の書き出しを元にした、決めた範囲の確認値で、状態がすべて同じことの証明ではない（docs 4 章）
- 内部エラーを未対応・不一致に変えない。``MemoryError`` と ``Exception`` の子でない終了は捕まえない（adapter と同じ）
"""

from __future__ import annotations

import traceback as _traceback
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from . import diagnostics as D
from .adapter import start_game, submit
from .commands import command_from_dict
from .errors import EngineError
from .replay_record import (
    END_ABORTED,
    EXTENSION_CONNECTION_CHECK,
    INCONSISTENT,
    MALFORMED,
    UNSUPPORTED,
    Problem,
    RecordReport,
    ReplayRecord,
    checks,
    connection_declared,
    connection_value,
    support_problems,
    validate_record,
)
from .state import GameState

SUCCEEDED = "succeeded"  # 閉じた記録の最後まで、結果・確認値・終わりの情報が一致した
INCOMPLETE = "incomplete"  # 終わりの情報がない記録で、ある行までは一致した（成功に数えない）
RECORDED_FAILURE = "recorded_failure"  # aborted の記録で、失敗の行まで一致し、同じ失敗がもう一度起きた（失敗を含む結果。成功に数えない）
NOT_SUPPORTED = "unsupported"  # 記録の形式・実装・環境・規約集合を扱えない（対戦を作らない）
INVALID_RECORD = "invalid_record"  # 形式の不正・内容の矛盾・送り直せないコマンド（対戦を作らないか、その行で止める）
DIVERGED = "diverged"  # 再実行の結果・確認値が記録と違った
INTERNAL_ERROR = "internal_error"  # 記録にない内部エラー・状態の不整合が再実行で起きた（不一致・未対応に変えない）
RESULTS = (SUCCEEDED, INCOMPLETE, RECORDED_FAILURE, NOT_SUPPORTED, INVALID_RECORD, DIVERGED, INTERNAL_ERROR)

LOCATION_START = "start"
LOCATION_OPERATION = "operation"
LOCATION_END = "end"
CHECK_ORDER = ("status", "decision", "halt", "segment", "log_length", "rng", "state")  # 比べる順（最初に違った項目を先に書く）


@dataclass(frozen=True)
class Mismatch:
    """最初の不一致。``items`` は違った項目（決めた順）。``recorded``・``replayed`` は検証者用の値（repr に出さない）。"""

    location: str
    seq: int | None
    accepted_index: int | None
    items: tuple[str, ...]
    recorded: Mapping[str, Any]
    replayed: Mapping[str, Any]

    def __repr__(self) -> str:
        return f"Mismatch(location={self.location!r}, seq={self.seq!r}, accepted_index={self.accepted_index!r}, items={self.items!r})"


@dataclass(frozen=True)
class ReplayRunReport:
    """再実行の結果（検証者用）。

    - ``status``: ``RESULTS`` の 1 つ。``succeeded`` だけが正常な再現の成功
    - ``executed``: 対戦を作って再実行したか（扱えない・構造の不正なら偽）
    - ``start_verified``・``verified_seq``・``verified_accepted``・``end_verified``: 一致を確かめられた範囲（``verified_seq`` は一致した最後の行の seq。0 は開始だけ）
    - ``mismatch``: 最初の不一致（なければ None）。``failure``: 再実行で起きた失敗の検証者用の記録（traceback を含む）"""

    status: str
    structure: RecordReport
    support: tuple[Problem, ...]
    executed: bool
    start_verified: bool
    verified_seq: int
    verified_accepted: int
    end_verified: bool
    mismatch: Mismatch | None
    failure: D.VerifierReport | None
    problems: tuple[Problem, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.status == SUCCEEDED

    def __repr__(self) -> str:
        return (f"ReplayRunReport(status={self.status!r}, executed={self.executed!r}, verified_seq={self.verified_seq!r}, "
                f"verified_accepted={self.verified_accepted!r}, end_verified={self.end_verified!r}, mismatch={self.mismatch!r})")

    __str__ = __repr__


class _Run:
    def __init__(self, structure: RecordReport, support: tuple[Problem, ...]):
        self.structure = structure
        self.support = support
        self.start_verified = False
        self.verified_seq = 0
        self.verified_accepted = 0
        self.end_verified = False

    def report(self, status, *, executed=True, mismatch=None, failure=None, problems=()) -> ReplayRunReport:
        return ReplayRunReport(status=status, structure=self.structure, support=self.support, executed=executed, start_verified=self.start_verified,
                               verified_seq=self.verified_seq, verified_accepted=self.verified_accepted, end_verified=self.end_verified,
                               mismatch=mismatch, failure=failure, problems=tuple(problems))


def boundary_items(state: GameState) -> dict[str, Any]:
    """確認値の範囲の外にある、コマンドの境界で空のはずの値（空でなければ不一致の項目にする。docs 4 章）。"""
    return {} if not state.pending_moves else {"pending_moves": len(state.pending_moves)}


def _diff_checks(recorded: Mapping[str, Any], replayed: Mapping[str, Any]) -> tuple[str, ...]:
    keys = [k for k in CHECK_ORDER if recorded.get(k) != replayed.get(k)]
    keys += sorted(k for k in set(recorded) | set(replayed) if k not in CHECK_ORDER and recorded.get(k) != replayed.get(k))
    return tuple(keys)


def _diagnostic(result) -> dict[str, Any]:
    return {"diagnostic_id": result.diagnosis.diagnostic_id, "category": result.diagnosis.category, "engine_code": result.verifier.engine_code}


def replay(record: ReplayRecord | dict[str, Any], *, observer=None) -> ReplayRunReport:
    """記録を再実行して照らす（docs 2 章の流れ）。

    v0.155: ``observer`` を渡すと、照合に通った開始の結果と各行の結果（``CommandResult``）を、その時点で順に渡す（閲覧用記録の変換 ``view_record.view_records_from_replay`` が使う）。
    照合に通らなかった結果は渡さない。最後まで成功したかは、返す結果の ``status`` で決まる（渡した結果だけで判断しない）。"""
    data = record.data if isinstance(record, ReplayRecord) else record
    structure = validate_record(data, check_support=False)
    if structure.status in (MALFORMED, INCONSISTENT):
        return _Run(structure, ()).report(INVALID_RECORD, executed=False, problems=structure.problems)
    if structure.status == UNSUPPORTED or any(p.kind == UNSUPPORTED for p in structure.problems):  # 知らない形式の版・知らない拡張（v0.158。途中で切れた記録でも）
        return _Run(structure, ()).report(NOT_SUPPORTED, executed=False, problems=tuple(p for p in structure.problems if p.kind == UNSUPPORTED))
    support = tuple(support_problems(data))
    run = _Run(structure, support)
    if support:
        return run.report(NOT_SUPPORTED, executed=False, problems=support)
    try:
        return _execute(run, data, observer)
    except Exception as error:  # 再実行の境界: 記録にない例外は内部エラーの結果（未対応・不一致に変えない。traceback は検証者用）
        if isinstance(error, MemoryError):
            raise
        failure = D.VerifierReport(mapped=False, engine_code=getattr(error, "code", None) if isinstance(error, EngineError) else None,
                                   exception_type=type(error).__name__, raw_message=str(error), traceback="".join(_traceback.format_exception(error)),
                                   exception=error)
        return run.report(INTERNAL_ERROR, failure=failure)


def _execute(run: _Run, data: dict[str, Any], observer=None) -> ReplayRunReport:
    report, state = run_start(run, data, observer)
    if report is not None:
        return report
    report, state, accepted = run_rows(run, data, state, 0, len(data["operations"]), 0, observer)
    if report is not None:
        return report
    return run_end(run, data, state, accepted)


def _connection_items(header: Mapping[str, Any], holder: Mapping[str, Any], state: GameState) -> tuple[tuple[str, ...], dict[str, Any], dict[str, Any]]:
    """v0.158: 拡張 ``connection_check`` を明示した記録で、記録した接続用確認値（None でないもの）と再実行の状態の値を比べる。
    違えば (("connection_check",), 記録の値, 再実行の値)。拡張のない記録・None の位置では比べない（値を作り出さない）。"""
    recorded = holder.get(EXTENSION_CONNECTION_CHECK)
    if not connection_declared(header) or recorded is None:
        return (), {}, {}
    replayed = connection_value(state)
    if replayed == recorded:
        return (), {}, {}
    return (EXTENSION_CONNECTION_CHECK,), {EXTENSION_CONNECTION_CHECK: recorded}, {EXTENSION_CONNECTION_CHECK: replayed}


def run_start(run: _Run, data: dict[str, Any], observer=None) -> tuple[ReplayRunReport | None, GameState | None]:
    """記録の初期の条件から対戦を作り、開始の確認値を照らす（U4 の最初の段。U6-S5 の前半の再実行も使う）。一致しなければ (結果, None)。"""
    header = data["header"]
    initial = header["initial"]
    start = start_game(initial["decklists"][0], initial["decklists"][1], initial["seed"], conventions=initial["conventions"],
                       operation_id=header["start"].get("operation_id"))
    if start.outcome == D.FAILED:
        return run.report(INTERNAL_ERROR, mismatch=Mismatch(LOCATION_START, None, None, ("outcome",), {"outcome": D.ACCEPTED}, {"outcome": start.outcome}),
                          failure=start.verifier), None
    if start.outcome != D.ACCEPTED:
        return run.report(DIVERGED, mismatch=Mismatch(LOCATION_START, None, None, ("outcome",), {"outcome": D.ACCEPTED},
                                                      {"outcome": start.outcome, "diagnostic_id": start.diagnosis.diagnostic_id})), None
    state = start.state
    recorded, replayed = dict(header["start"]["check"]), checks(state)
    extra, recorded_extra, replayed_extra = _connection_items(header, header["start"], state)
    items = _diff_checks(recorded, replayed) + (("status_field",) if header["start"]["status"] != start.status else ()) + tuple(boundary_items(state)) + extra
    if items:
        return run.report(DIVERGED, mismatch=Mismatch(LOCATION_START, None, None, items, {**recorded, **recorded_extra},
                                                      {**replayed, **boundary_items(state), **replayed_extra})), None
    run.start_verified = True
    if observer is not None:
        observer(start)
    return None, state


def run_rows(run: _Run, data: dict[str, Any], state: GameState, first: int, stop: int, accepted: int,
             observer=None) -> tuple[ReplayRunReport | None, GameState, int]:
    """記録の行 ``operations[first:stop]`` を seq の順に送り、結果と確認値を照らす（U4 の行の処理。U6-S5 の前半・後半の再実行も同じ処理を使う）。

    ``state`` はその行の前の状態、``accepted`` はそれまでに受理した操作の数（受理した行の ``accepted_index`` の照合に使う）。最初の不一致・記録された失敗・内部エラーで
    (結果, 状態, 数) を返し、最後まで一致すれば (None, 状態, 数)。乱数を各操作の前へ戻さず、コインの結果を入れず、方策を再実行しない。"""
    header = data["header"]
    for op in data["operations"][first:stop]:
        seq = op["seq"]
        try:
            command = command_from_dict(dict(op["command"]))
        except EngineError:
            return run.report(INVALID_RECORD, problems=(Problem(MALFORMED, "command_not_replayable", f"$.operations[{seq - 1}].command"),)), state, accepted
        before = checks(state) if op["outcome"] != D.ACCEPTED else None
        result = submit(state, command, submitter=op["submitter"], operation_id=op["operation_id"])
        index = accepted + 1 if op["outcome"] == D.ACCEPTED else None
        if result.outcome != op["outcome"]:
            mismatch = Mismatch(LOCATION_OPERATION, seq, index, ("outcome",), {"outcome": op["outcome"], **({"diagnostic": op["diagnostic"]} if "diagnostic" in op else {})},
                                {"outcome": result.outcome, **({"diagnostic": _diagnostic(result)} if result.diagnosis is not None else {})})
            if result.outcome == D.FAILED:
                return run.report(INTERNAL_ERROR, mismatch=mismatch, failure=result.verifier), state, accepted
            return run.report(DIVERGED, mismatch=mismatch), state, accepted
        differ = []
        if result.status != op["status"]:
            differ.append("status_field")
        if result.actor != op["actor"]:
            differ.append("actor")
        if result.outcome == D.ACCEPTED:
            accepted += 1
            if op.get("accepted_index") != accepted:  # 構造の検証で順を確かめている。途中から照らすとき（U6-S5）の数の食い違いも見つける
                differ.append("accepted_index")
            replayed = checks(result.state)
            extra, recorded_extra, replayed_extra = _connection_items(header, op, result.state)
            differ = list(_diff_checks(op["check"], replayed)) + differ + list(boundary_items(result.state)) + list(extra)
            if differ:
                return run.report(DIVERGED, mismatch=Mismatch(LOCATION_OPERATION, seq, accepted, tuple(differ), {**op["check"], **recorded_extra},
                                                              {**replayed, **boundary_items(result.state), **replayed_extra})), state, accepted
            state = result.state
        else:
            got = _diagnostic(result)
            differ += [k for k in ("diagnostic_id", "category", "engine_code") if op["diagnostic"].get(k) != got[k]]
            if result.outcome == D.REJECTED and (result.state is not state or checks(state) != before):
                differ.append("state_changed_by_rejection")
            if differ:
                return run.report(DIVERGED, mismatch=Mismatch(LOCATION_OPERATION, seq, None, tuple(differ), {**op["diagnostic"], "status": op["status"]},
                                                              {**got, "status": result.status})), state, accepted
            if result.outcome == D.FAILED:
                run.verified_seq = seq
                return run.report(RECORDED_FAILURE, failure=result.verifier), state, accepted
        run.verified_seq = seq
        run.verified_accepted = accepted
        if observer is not None:
            observer(result)
    return None, state, accepted


def run_end(run: _Run, data: dict[str, Any], state: GameState, accepted: int) -> ReplayRunReport:
    """終わりの情報を照らす（U4 の最後の段。終わりの情報がなければ incomplete）。"""
    end = data.get("end")
    if end is None:
        return run.report(INCOMPLETE)
    if end["state"] == END_ABORTED:  # 構造の検証で、失敗の行のない aborted は矛盾として除いている
        return run.report(INVALID_RECORD, problems=(Problem(INCONSISTENT, "aborted_without_failure", "$.end.state"),))
    final = checks(state)
    recorded_end = {"status": end["status"], "accepted": end["accepted"], "operations": end["operations"], **{f"final_check.{k}": v for k, v in end["final_check"].items()}}
    replayed_end = {"status": D.status_of(state), "accepted": accepted, "operations": len(data["operations"]), **{f"final_check.{k}": v for k, v in final.items()}}
    items = tuple(k for k in recorded_end if recorded_end[k] != replayed_end.get(k))
    if items:
        return run.report(DIVERGED, mismatch=Mismatch(LOCATION_END, None, None, items, recorded_end, replayed_end))
    run.end_verified = True
    return run.report(SUCCEEDED)
