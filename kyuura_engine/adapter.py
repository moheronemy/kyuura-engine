"""コマンド実行結果のアダプタ（v0.152。docs/diagnostics-adapter-v0.152.md。仕様案 docs/diagnostics-replay-api-design.md の U2）。

既存の ``new_game``・``apply_command`` を包み、結果（受理・拒否・処理できない）と、操作のあとの状態（進行中・決定待ち・停止・終局・延長戦の開始待ち）と診断を返します。
受理の条件・返す状態・乱数・ログ・観測は ``apply_command`` と同じです（アダプタは結果を読むだけ）。

- ``submit``: 状態とコマンドから ``CommandResult`` を作る。拒否なら元の状態をそのまま持つ（状態・乱数・ログは変わらない。``apply_command`` の約束）
- ``start_game``: ``new_game`` の前に seed の形を確かめ、デッキ・規約集合の拒否も同じ形で返す
- ``HostedGame``: 信頼されたホストが状態を持ち、受理したときだけ状態を進める最小の境界（見る人は状態を持たないので、前の状態から操作をやり直せない）

例外の捕まえ方（アダプタの責任の範囲）:

- ``EngineError``: 拒否（状態の不整合 ``StateIntegrityError`` だけは処理できない結果 ``failed``）。分類はコード表（``diagnostics``）で決める
- ``EngineError`` でない ``Exception``: 内部エラー（``failed``・``internal_error``）。元の例外と traceback は検証者用の記録に置き、ほかの分類に変えない
- ``MemoryError`` と、``Exception`` の子でない終了（``KeyboardInterrupt``・``SystemExit``・``GeneratorExit``・``asyncio.CancelledError``）は捕まえない
"""

from __future__ import annotations

import traceback as _traceback
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from . import diagnostics as D
from .commands import (
    PromoteActive,
    ResolveDecision,
    StartSuddenDeath,
    TakePrize,
    command_to_dict,
)
from .engine import apply_command, new_game
from .errors import EngineError, StateIntegrityError
from .observation import observe
from .state import GameState, Phase

_ANSWERS = (ResolveDecision, TakePrize, PromoteActive)
_SETUP_PHASES = (Phase.SETUP_PLACEMENT, Phase.SETUP_MULLIGAN_DRAW, Phase.SETUP_FIRST_PLAYER)


@dataclass(frozen=True)
class CommandResult:
    """操作 1 つの結果（ホストが持つ。``verifier`` は検証者用で、見る人に渡さない）。

    - ``outcome``: accepted・rejected・failed
    - ``status``: 操作のあとの状態。accepted は新しい状態、rejected は元の状態の値（対戦の開始の拒否は not_started）、failed は unavailable
    - ``state``: ホストがこのあと持つ状態（accepted は新しい状態、rejected は渡した状態そのもの、failed と開始の拒否は None）
    - ``diagnosis``: 拒否・処理できない理由（accepted は None）。``halt``: 停止した状態の公開の診断
    - ``continuable``: 実際の状態で、この版が次の操作を処理しうるか（分類からは推測しない）
    - ``actor``: 結果を本人として受け取るプレイヤー（送り手を指定したらその値、なければコマンドの ``player``）
    - ``operation_id``: ホストが付けた操作の識別（将来の記録との対応のため。そのまま本人の結果に返す）
    """

    outcome: str
    status: str
    stage: str
    actor: int | None
    operation_id: str | None
    state: GameState | None
    diagnosis: D.Diagnosis | None
    halt: D.PublicHalt | None
    continuable: bool
    next: tuple[D.NextAction, ...]
    convention_set: D.ConventionRef | None
    verifier: D.VerifierReport

    def __post_init__(self) -> None:
        problems = []
        if self.outcome == D.ACCEPTED:
            if self.status not in D.STATE_STATUSES or self.diagnosis is not None or self.state is None:
                problems.append("accepted は状態のある status・診断なし・新しい状態")
            if (self.status == D.HALTED) != (self.halt is not None):
                problems.append("halted のときだけ halt がある")
        elif self.outcome == D.REJECTED:
            if self.diagnosis is None or self.diagnosis.category in (D.STATE_INTEGRITY, D.INTERNAL_ERROR):
                problems.append("rejected は拒否の診断（状態の不整合・内部エラーでない）")
            if self.status == D.NOT_STARTED:
                if self.state is not None or self.stage != D.STAGE_SETUP:
                    problems.append("開始の拒否は状態なし・段階 setup")
            elif self.status not in D.STATE_STATUSES or self.state is None:
                problems.append("rejected は元の状態とその status")
        elif self.outcome == D.FAILED:
            if self.status != D.UNAVAILABLE or self.state is not None or self.diagnosis is None:
                problems.append("failed は unavailable・状態なし・診断あり")
            elif self.diagnosis.category not in (D.STATE_INTEGRITY, D.INTERNAL_ERROR, D.UNMAPPED):
                problems.append("failed は状態の不整合・内部エラー（状態の不整合のコードが表にないときは対応漏れ）だけ")
        else:
            problems.append(f"知らない outcome {self.outcome!r}")
        if self.continuable and (self.outcome == D.FAILED or self.status not in D.LIVE_STATUSES):
            problems.append("続けられるのは、処理できた結果の進行中・決定待ち・延長戦の開始待ちだけ")
        if self.stage not in D.STAGES:
            problems.append(f"知らない処理段階 {self.stage!r}")
        if problems:
            raise ValueError("CommandResult の組み合わせが正しくない: " + "; ".join(problems))

    def view_for(self, viewer) -> D.ActorDiagnostic | D.StatusNotice | None:
        """見る人（0・1・None）に渡してよい結果。本人には ``ActorDiagnostic``、相手・観戦者には今の状態の ``StatusNotice``、拒否は本人のほかに None（拒否があったことも知らせない）。
        対戦が終わったあとも同じ範囲（終局で広げない）。"""
        D.check_viewer(viewer)
        if self.actor is not None and viewer == self.actor:
            d = self.diagnosis
            return D.ActorDiagnostic(
                viewer=viewer, outcome=self.outcome, status=self.status, stage=self.stage, continuable=self.continuable, next=self.next,
                diagnostic_id=None if d is None else d.diagnostic_id, category=None if d is None else d.category, subkind=None if d is None else d.subkind,
                case_id=None if d is None else d.case_id, case_status=None if d is None else d.case_status, message=None if d is None else d.message,
                halt=self.halt, operation_id=self.operation_id, convention_set=self.convention_set)
        if self.outcome == D.REJECTED:
            return None
        if self.outcome == D.FAILED:
            return D.StatusNotice(viewer=viewer, status=D.UNAVAILABLE, continuable=False, next=(), halt=None, convention_set=None)
        return D.StatusNotice(viewer=viewer, status=self.status, continuable=self.continuable, next=self.next, halt=self.halt,
                              convention_set=self.convention_set)


def _command_record(command) -> Mapping[str, Any] | None:
    try:
        return command_to_dict(command)
    except (TypeError, ValueError, AttributeError):  # 検証者用の写しを作れないコマンドは repr で残す（コマンドの処理には使わない）
        return {"repr": repr(command)}


def _actor(command, submitter: int | None) -> int | None:
    if submitter is not None:
        return submitter
    player = getattr(command, "player", None)
    return player if player in (0, 1) and not isinstance(player, bool) else None


def _stage(state: GameState, command) -> str:
    if isinstance(command, StartSuddenDeath):
        return D.STAGE_SEGMENT_START
    if isinstance(command, _ANSWERS):
        return D.STAGE_DECISION_ANSWER
    if state.phase in _SETUP_PHASES:
        return D.STAGE_SETUP
    return D.STAGE_TURN_ACTION


def _state_check_failure(state: GameState, error: EngineError) -> bool:
    """拒否が、状態そのものの確かめ（規約集合・再開先。どのコマンドの前にも行う確かめ）によるものか。"""
    return not D.state_usable(state) and error.code in {e.code for e in _state_errors(state)}


def _state_errors(state: GameState) -> list[EngineError]:
    from .conventions import require_state_conventions
    from .engine import supported_decision_error
    from .errors import UnsupportedError

    found: list[EngineError] = []
    try:
        require_state_conventions(state)
    except UnsupportedError as error:
        found.append(error)
    error = supported_decision_error(state)
    if error is not None:
        found.append(error)
    return found


def _accepted(new: GameState, *, stage: str, actor, operation_id, command_record, catalog) -> CommandResult:
    halt, halt_mapped = D.public_halt(new, catalog=catalog)
    verifier = D.VerifierReport(mapped=halt_mapped, command=command_record,
                                halt_code=None if new.halt is None else new.halt.code, halt_message=None if new.halt is None else new.halt.message,
                                halt_references=() if new.halt is None else tuple(new.halt.references))
    return CommandResult(outcome=D.ACCEPTED, status=D.status_of(new), stage=stage, actor=actor, operation_id=operation_id, state=new, diagnosis=None,
                         halt=halt, continuable=D.continuable(new), next=D.next_actions(new), convention_set=D.convention_ref(new), verifier=verifier)


def _report(error: BaseException, mapped: bool, command_record) -> D.VerifierReport:
    return D.VerifierReport(
        mapped=mapped, engine_code=getattr(error, "code", None) if isinstance(error, EngineError) else None, exception_type=type(error).__name__,
        raw_message=str(error), traceback="".join(_traceback.format_exception(error)), problems=tuple(getattr(error, "problems", ()) or ()),
        command=command_record, exception=error)


def _failed(error: BaseException, diagnosis: D.Diagnosis, *, stage, actor, operation_id, command_record, mapped: bool) -> CommandResult:
    return CommandResult(outcome=D.FAILED, status=D.UNAVAILABLE, stage=stage, actor=actor, operation_id=operation_id, state=None, diagnosis=diagnosis,
                         halt=None, continuable=False, next=(), convention_set=None, verifier=_report(error, mapped, command_record))


def submit(state: GameState, command, *, submitter: int | None = None, operation_id: str | None = None,
           catalog: D.Catalog | None = None) -> CommandResult:
    """``apply_command(state, command)`` の結果を ``CommandResult`` にする。``state`` は変えない。

    ``submitter`` は、ホストが確かめた送り手のプレイヤー（0・1）。指定して、コマンドの ``player`` と違えば、エンジンに渡さずに拒否する（``SUBMITTER_MISMATCH``）。"""
    if submitter is not None and (isinstance(submitter, bool) or submitter not in (0, 1)):
        raise ValueError(f"送り手 {submitter!r} は 0 か 1")
    command_record = _command_record(command)
    stage = _stage(state, command)
    actor = _actor(command, submitter)
    player = getattr(command, "player", None)
    if submitter is not None and player is not None and player != submitter:
        diagnosis = D.adapter_diagnosis(D.SUBMITTER_MISMATCH_ID, "command")
        return CommandResult(outcome=D.REJECTED, status=D.status_of(state), stage=D.STAGE_SUBMISSION, actor=actor, operation_id=operation_id, state=state,
                             diagnosis=diagnosis, halt=D.public_halt(state, catalog=catalog)[0], continuable=D.continuable(state),
                             next=D.next_actions(state), convention_set=D.convention_ref(state), verifier=D.VerifierReport(mapped=True, command=command_record))
    subkind = "answer" if isinstance(command, _ANSWERS) else "command"
    try:
        new = apply_command(state, command)
    except EngineError as error:
        diagnosis, mapped = D.classify_error(error, subkind=subkind, catalog=catalog)
        if isinstance(error, StateIntegrityError):  # 状態を信頼できないので、分類（表の対応漏れでも）によらず処理できない結果
            return _failed(error, diagnosis, stage=stage, actor=actor, operation_id=operation_id, command_record=command_record, mapped=mapped)
        if _state_check_failure(state, error):
            stage = D.STAGE_STATE_CHECK
        return CommandResult(outcome=D.REJECTED, status=D.status_of(state), stage=stage, actor=actor, operation_id=operation_id, state=state,
                             diagnosis=diagnosis, halt=D.public_halt(state, catalog=catalog)[0], continuable=D.continuable(state),
                             next=D.next_actions(state), convention_set=D.convention_ref(state), verifier=_report(error, mapped, command_record))
    except Exception as error:  # アダプタの境界: EngineError でない例外は内部エラーの結果にする（分類を変えず、元の例外は検証者用の記録に残す）
        if isinstance(error, MemoryError):  # 資源の不足は内部エラーの結果にしない
            raise
        return _failed(error, D.internal_error(), stage=stage, actor=actor, operation_id=operation_id, command_record=command_record, mapped=False)
    return _accepted(new, stage=stage, actor=actor, operation_id=operation_id, command_record=command_record, catalog=catalog)


def start_game(deck0, deck1, seed, *, operation_id: str | None = None, catalog: D.Catalog | None = None, **options) -> CommandResult:
    """``new_game(deck0, deck1, seed, **options)`` の結果を ``CommandResult`` にする（本人はいない。結果はどの見る人にも同じ知らせ）。

    seed が 0 以上の整数でなければ、``new_game`` を呼ばずに拒否する（``INVALID_SEED``）。デッキ・規約集合の拒否は ``new_game`` の例外から決める。"""
    record = {"new_game": {"seed": repr(seed), "options": sorted(options)}}
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        return CommandResult(outcome=D.REJECTED, status=D.NOT_STARTED, stage=D.STAGE_SETUP, actor=None, operation_id=operation_id, state=None,
                             diagnosis=D.adapter_diagnosis(D.INVALID_SEED_ID, "setup"), halt=None, continuable=False, next=(), convention_set=None,
                             verifier=D.VerifierReport(mapped=True, command=record))
    try:
        state = new_game(deck0, deck1, seed, **options)
    except EngineError as error:
        diagnosis, mapped = D.classify_error(error, subkind="setup", catalog=catalog)
        if isinstance(error, StateIntegrityError):
            return _failed(error, diagnosis, stage=D.STAGE_SETUP, actor=None, operation_id=operation_id, command_record=record, mapped=mapped)
        return CommandResult(outcome=D.REJECTED, status=D.NOT_STARTED, stage=D.STAGE_SETUP, actor=None, operation_id=operation_id, state=None,
                             diagnosis=diagnosis, halt=None, continuable=False, next=(), convention_set=None, verifier=_report(error, mapped, record))
    except Exception as error:  # アダプタの境界（submit と同じ）
        if isinstance(error, MemoryError):
            raise
        return _failed(error, D.internal_error(), stage=D.STAGE_SETUP, actor=None, operation_id=operation_id, command_record=record, mapped=False)
    return _accepted(state, stage=D.STAGE_SETUP, actor=None, operation_id=operation_id, command_record=record, catalog=catalog)


class HostStoppedError(Exception):
    """処理できない結果（failed）のあとの ``HostedGame`` に操作を送った（使い方の誤り。検証者が調べる前に続けない）。"""


class HostedGame:
    """信頼されたホストが状態を持つ最小の境界。受理したときだけ状態を進め、拒否では前の状態のまま。処理できない結果のあとは操作を受け付けない。

    見る人には ``view``（観測）と ``CommandResult.view_for`` の結果だけを渡す。状態（``state``）はホストの中だけで使う。"""

    def __init__(self, state: GameState):
        self._state = state
        self._failure: CommandResult | None = None

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def failure(self) -> CommandResult | None:
        return self._failure

    def submit(self, command, *, submitter: int | None = None, operation_id: str | None = None) -> CommandResult:
        if self._failure is not None:
            raise HostStoppedError("処理できない結果のあとの対戦には、操作を送れない（検証者が調べる）")
        result = submit(self._state, command, submitter=submitter, operation_id=operation_id)
        if result.outcome == D.ACCEPTED:
            self._state = result.state
        elif result.outcome == D.FAILED:
            self._failure = result
        return result

    def view(self, viewer):
        D.check_viewer(viewer)
        return observe(self._state, viewer)
