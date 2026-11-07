"""診断の共通の型と、見る人ごとの情報境界（v0.152。docs/diagnostics-adapter-v0.152.md。仕様案 docs/diagnostics-replay-api-design.md の U1）。

エンジンの例外・停止を、機械が判定できる診断にする部品です。エンジンの処理（``apply_command``・``observe``・例外・停止）は変えず、その結果を読むだけです。

- 分類はコード表（``data/diagnostic_catalog.json``。``scripts/build_diagnostic_catalog.py`` が停止の方針の台帳・場面の索引・エンジンのソースから作る。手で直さない）で決める。
  表にないコード、表と違う例外の型で来たコードは、診断の対応漏れ（``unmapped``）にする。コードの接頭辞・例外の型の名前から分類を推測しない
- 事例は、コードの場面が 1 つのときだけ返す。2 つ以上なら選ばない（``not_identified``）
- 本人向けの説明は、コード表の決まった文だけ（カード名・uid・枚数を埋め込まない）。例外の生の文・traceback・停止の診断用の文は、検証者用の記録（``VerifierReport``）にだけ置く
- 見る人の値は 0・1（プレイヤー）・None（観戦者）だけ。検証者を表す値はない。検証者用の記録は、ホストが持つ結果（``adapter.CommandResult``）の項目で、見る人の値からは取り出せない
- 閲覧用の型（``ActorDiagnostic``・``StatusNotice``）は、公開を許した項目だけを持つ（内部の値を持ったまま隠すのではない）

コードの対応付けは状態を変えず、乱数を使わない。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from types import MappingProxyType
from typing import Any

from .conventions import ConventionSetError, require_state_conventions
from .errors import (
    DeckValidationError,
    EngineError,
    IllegalActionError,
    StateIntegrityError,
    UnsupportedError,
)
from .state import GameState, Phase

DIAGNOSTIC_SCHEMA = 1

# 分類（仕様案 4.2 節。unmapped は v0.152 で加えた、診断の対応漏れ）
INVALID_INPUT = "invalid_input"
RULING_UNRESOLVED = "unresolved_ruling"
UNSUPPORTED = "unsupported"
TECHNICAL_LIMIT = "technical_limit"
COMPATIBILITY = "compatibility"
STATE_INTEGRITY = "state_integrity"
INTERNAL_ERROR = "internal_error"
UNMAPPED = "unmapped"
CATEGORIES = (INVALID_INPUT, RULING_UNRESOLVED, UNSUPPORTED, TECHNICAL_LIMIT, COMPATIBILITY, STATE_INTEGRITY, INTERNAL_ERROR, UNMAPPED)

# 操作の結果（outcome）
ACCEPTED = "accepted"  # 受け付けた。状態は新しい状態に置きかわる
REJECTED = "rejected"  # 拒否した。元の状態（状態・乱数・ログ）を保った
FAILED = "failed"  # 処理できなかった（状態の不整合・内部エラー）。元の状態で続けることを保証しない
OUTCOMES = (ACCEPTED, REJECTED, FAILED)

# 操作のあとの状態（status）
IN_PROGRESS = "in_progress"
AWAITING_DECISION = "awaiting_decision"
HALTED = "halted"
GAME_OVER = "game_over"
SUDDEN_DEATH_PENDING = "sudden_death_pending"
NOT_STARTED = "not_started"  # 対戦を始める前の拒否（``adapter.start_game``）
UNAVAILABLE = "unavailable"  # 処理できなかったので、状態を返さない（failed だけ）
STATE_STATUSES = (IN_PROGRESS, AWAITING_DECISION, HALTED, GAME_OVER, SUDDEN_DEATH_PENDING)
STATUSES = (*STATE_STATUSES, NOT_STARTED, UNAVAILABLE)
LIVE_STATUSES = (IN_PROGRESS, AWAITING_DECISION, SUDDEN_DEATH_PENDING)

# 処理段階（stage）
STAGE_SETUP = "setup"
STAGE_TURN_ACTION = "turn_action"
STAGE_DECISION_ANSWER = "decision_answer"
STAGE_SEGMENT_START = "segment_start"
STAGE_STATE_CHECK = "state_check"
STAGE_SUBMISSION = "submission"
STAGES = (STAGE_SETUP, STAGE_TURN_ACTION, STAGE_DECISION_ANSWER, STAGE_SEGMENT_START, STAGE_STATE_CHECK, STAGE_SUBMISSION)

# 事例の特定の状態
CASE_IDENTIFIED = "identified"
CASE_NOT_IDENTIFIED = "not_identified"
CASE_NOT_APPLICABLE = "not_applicable"

# アダプタが作る診断の識別（エンジンのコードではない）
UNMAPPED_ID = "DIAGNOSTIC_UNMAPPED"
INTERNAL_ERROR_ID = "INTERNAL_ERROR"
SUBMITTER_MISMATCH_ID = "SUBMITTER_MISMATCH"
INVALID_SEED_ID = "INVALID_SEED"

ADAPTER_TEXTS = MappingProxyType({
    UNMAPPED_ID: "この結果を説明する決まった文が、診断の表にありません（診断の対応漏れ）。",
    INTERNAL_ERROR_ID: "エンジンの内部で問題が起きたため、この操作を処理できませんでした。対戦を続けられません。",
    SUBMITTER_MISMATCH_ID: "操作のプレイヤーが、送ったプレイヤーと違います。",
    INVALID_SEED_ID: "seed は 0 以上の整数で指定してください。",
})

# 次の操作の種類（合法手の一覧ではない。どの操作を受け付けうるかの種類だけ）
NEXT_PLACE_STARTING = "place_starting_pokemon"
NEXT_MULLIGAN_DRAW = "draw_mulligan_cards"
NEXT_JANKEN = "report_janken_result"
NEXT_TURN_ACTION = "turn_action"
NEXT_ANSWER_DECISION = "answer_decision"
NEXT_START_SUDDEN_DEATH = "start_sudden_death"

VIEWERS = (0, 1, None)


# ---------------------------------------------------------------- コード表


@dataclass(frozen=True)
class CodeEntry:
    """コード表の 1 行（エンジンが返す元のコード → 分類・事例・決まった文）。"""

    code: str
    category: str
    raised_as: tuple[str, ...]
    case_id: str | None
    case_status: str
    text: str
    text_source: str


class Catalog:
    """診断のコード表（読み取り専用）。"""

    def __init__(self, data: Mapping[str, Any]):
        if data.get("schema_version") != 1:
            raise ValueError(f"知らないコード表の形式 {data.get('schema_version')!r}")
        self.codes: Mapping[str, CodeEntry] = MappingProxyType({
            code: CodeEntry(code, row["category"], tuple(row["raised_as"]), row["case"], row["case_status"], row["text"], row["text_source"])
            for code, row in data["codes"].items()})
        self.category_texts: Mapping[str, str] = MappingProxyType(dict(data["category_texts"]))
        self.subkind_texts: Mapping[str, str] = MappingProxyType(dict(data["subkind_texts"]))
        self.halt_texts: Mapping[str, str] = MappingProxyType(dict(data["halt_texts"]))
        for entry in self.codes.values():
            if entry.category not in CATEGORIES or entry.category in (INTERNAL_ERROR, UNMAPPED):
                raise ValueError(f"コード表のコード {entry.code} の分類 {entry.category!r} が使えない")

    def get(self, code: str) -> CodeEntry | None:
        return self.codes.get(code)

    def text_for(self, entry: CodeEntry, subkind: str | None) -> str:
        if entry.text_source == "code":
            return entry.text
        return self.subkind_texts.get(f"{entry.category}/{subkind}", entry.text)


@lru_cache(maxsize=1)
def default_catalog() -> Catalog:
    """同梱のコード表（``kyuura_engine/data/diagnostic_catalog.json``）。"""
    text = resources.files(__package__).joinpath("data/diagnostic_catalog.json").read_text(encoding="utf-8")
    return Catalog(json.loads(text))


# ---------------------------------------------------------------- 分類


@dataclass(frozen=True)
class Diagnosis:
    """見る人に返してよい分類の結果（決まった値と決まった文だけ）。"""

    diagnostic_id: str
    category: str
    subkind: str | None
    case_id: str | None
    case_status: str
    message: str


def _raised_as(error: EngineError) -> str | None:
    """例外の型の区分（コード表の ``raised_as`` と照らす。型だけでは分類しない）。"""
    if isinstance(error, StateIntegrityError):
        return "state_integrity"
    if isinstance(error, DeckValidationError):
        return "deck_validation"
    if isinstance(error, ConventionSetError):
        return "convention_set"
    if isinstance(error, IllegalActionError):
        return "illegal"
    if isinstance(error, UnsupportedError):
        return "unsupported"
    return None


def unmapped() -> Diagnosis:
    return Diagnosis(UNMAPPED_ID, UNMAPPED, None, None, CASE_NOT_APPLICABLE, ADAPTER_TEXTS[UNMAPPED_ID])


def internal_error() -> Diagnosis:
    return Diagnosis(INTERNAL_ERROR_ID, INTERNAL_ERROR, None, None, CASE_NOT_APPLICABLE, ADAPTER_TEXTS[INTERNAL_ERROR_ID])


def adapter_diagnosis(diagnostic_id: str, subkind: str) -> Diagnosis:
    """アダプタが自分で拒否するときの診断（送り手の違い・seed の形。どれも不正な入力）。"""
    return Diagnosis(diagnostic_id, INVALID_INPUT, subkind, None, CASE_NOT_APPLICABLE, ADAPTER_TEXTS[diagnostic_id])


def classify_error(error: BaseException, *, subkind: str | None = None, catalog: Catalog | None = None) -> tuple[Diagnosis, bool]:
    """例外の診断と、コード表で対応付けたか（偽なら対応漏れか内部エラー）。

    - EngineError でない例外は内部エラー（ほかの分類に変えない）
    - EngineError は、コードがコード表にあり、例外の型の区分が表の ``raised_as`` にあるときだけ、その行の分類。どちらかが合わなければ対応漏れ"""
    if not isinstance(error, EngineError):
        return internal_error(), False
    catalog = catalog or default_catalog()
    entry = catalog.get(error.code)
    kind = _raised_as(error)
    if entry is None or kind not in entry.raised_as:
        return unmapped(), False
    sub = subkind if entry.category == INVALID_INPUT else None
    return Diagnosis(entry.code, entry.category, sub, entry.case_id, entry.case_status, catalog.text_for(entry, sub)), True


def classify_halt_code(code: str, *, catalog: Catalog | None = None) -> tuple[Diagnosis, bool]:
    """停止した状態（``Phase.HALTED``）の ``halt.code`` の診断。停止は例外ではないので、コード表の行の例外の型の区分は問わない。"""
    catalog = catalog or default_catalog()
    entry = catalog.get(code)
    if entry is None or entry.category not in catalog.halt_texts:
        return unmapped(), False
    return Diagnosis(entry.code, entry.category, None, entry.case_id, entry.case_status, catalog.halt_texts[entry.category]), True


# ---------------------------------------------------------------- 状態から決まる値（観測と同じ公開の値だけを読む）


@dataclass(frozen=True)
class NextAction:
    """次に受け付けうる操作の種類と、送るプレイヤー（None はこの API では決めない）。合法手の一覧ではない。"""

    kind: str
    player: int | None

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "player": self.player}


@dataclass(frozen=True)
class ConventionRef:
    """規約集合の識別（観測の ``convention_set`` と同じ公開の値の一部）。"""

    id: str
    version: int
    digest: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "version": self.version, "digest": self.digest}


@dataclass(frozen=True)
class PublicHalt:
    """停止した状態の公開の診断（停止のコードはログ ``halted`` で全員に見える。途中停止かどうかは観測の ``interruption`` で全員に見える）。"""

    diagnostic_id: str
    category: str
    case_id: str | None
    case_status: str
    message: str
    interrupted: bool

    def to_dict(self) -> dict[str, Any]:
        return {"diagnostic_id": self.diagnostic_id, "category": self.category, "case_id": self.case_id, "case_status": self.case_status,
                "message": self.message, "interrupted": self.interrupted}


def status_of(state: GameState) -> str:
    if state.phase == Phase.HALTED:
        return HALTED
    if state.phase == Phase.GAME_OVER:
        return GAME_OVER
    if state.phase == Phase.SUDDEN_DEATH:
        return SUDDEN_DEATH_PENDING
    if state.decision is not None:
        return AWAITING_DECISION
    return IN_PROGRESS


def next_actions(state: GameState) -> tuple[NextAction, ...]:
    """段階と保留中の決定から決まる、次の操作の種類（どれも観測で全員に見える値から決まる）。"""
    status = status_of(state)
    if status in (HALTED, GAME_OVER):
        return ()
    if status == SUDDEN_DEATH_PENDING:
        return (NextAction(NEXT_START_SUDDEN_DEATH, None),)
    if status == AWAITING_DECISION:
        return (NextAction(NEXT_ANSWER_DECISION, state.decision.player),)
    if state.phase == Phase.SETUP_PLACEMENT:
        return (NextAction(NEXT_PLACE_STARTING, None),)
    if state.phase == Phase.SETUP_MULLIGAN_DRAW:
        return (NextAction(NEXT_MULLIGAN_DRAW, None),)
    if state.phase == Phase.SETUP_FIRST_PLAYER:
        return (NextAction(NEXT_JANKEN, None),)
    return (NextAction(NEXT_TURN_ACTION, state.current_player),)


def state_usable(state: GameState) -> bool:
    """この版がその状態で次の操作を処理しうるか（規約集合・保留中の決定の再開先。コマンドの入口と同じ確かめ。状態を変えない）。"""
    from .engine import supported_decision_error

    try:
        require_state_conventions(state)
    except UnsupportedError:
        return False
    return supported_decision_error(state) is None


def continuable(state: GameState) -> bool:
    return status_of(state) in LIVE_STATUSES and state_usable(state)


def convention_ref(state: GameState) -> ConventionRef | None:
    try:
        identity = require_state_conventions(state)
    except UnsupportedError:
        return None
    return ConventionRef(identity.set_id, identity.version, identity.digest)


def public_halt(state: GameState, *, catalog: Catalog | None = None) -> tuple[PublicHalt | None, bool]:
    if state.phase != Phase.HALTED or state.halt is None:
        return None, True
    diagnosis, mapped = classify_halt_code(state.halt.code, catalog=catalog)
    return PublicHalt(diagnosis.diagnostic_id, diagnosis.category, diagnosis.case_id, diagnosis.case_status, diagnosis.message,
                      state.halt.interruption is not None), mapped


# ---------------------------------------------------------------- 見る人ごとの結果（公開を許した項目だけ）


def check_viewer(viewer) -> None:
    """見る人の値は 0・1・None だけ（真偽値・文字列・検証者を表す値は受け付けない）。"""
    if isinstance(viewer, bool) or viewer not in VIEWERS:
        raise ValueError(f"見る人 {viewer!r} は 0・1（プレイヤー）か None（観戦者）")


@dataclass(frozen=True)
class ActorDiagnostic:
    """操作した本人への結果。生の文・traceback・秘密の配分・乱数・状態の指紋は持たない。"""

    viewer: int
    outcome: str
    status: str
    stage: str
    continuable: bool
    next: tuple[NextAction, ...]
    diagnostic_id: str | None
    category: str | None
    subkind: str | None
    case_id: str | None
    case_status: str | None
    message: str | None
    halt: PublicHalt | None
    operation_id: str | None
    convention_set: ConventionRef | None

    def to_dict(self) -> dict[str, Any]:
        return {"kyuura_diagnostic_schema": DIAGNOSTIC_SCHEMA, "role": "actor", "viewer": self.viewer, "outcome": self.outcome, "status": self.status,
                "stage": self.stage, "continuable": self.continuable, "next": [a.to_dict() for a in self.next], "diagnostic_id": self.diagnostic_id,
                "category": self.category, "subkind": self.subkind, "case_id": self.case_id, "case_status": self.case_status, "message": self.message,
                "halt": None if self.halt is None else self.halt.to_dict(), "operation_id": self.operation_id,
                "convention_set": None if self.convention_set is None else self.convention_set.to_dict()}


@dataclass(frozen=True)
class StatusNotice:
    """本人でない見る人（相手・観戦者）への知らせ。今の状態の公開の値だけで、だれが何を送ったか・拒否があったかを持たない。"""

    viewer: int | None
    status: str
    continuable: bool
    next: tuple[NextAction, ...]
    halt: PublicHalt | None
    convention_set: ConventionRef | None

    def to_dict(self) -> dict[str, Any]:
        return {"kyuura_diagnostic_schema": DIAGNOSTIC_SCHEMA, "role": "observer", "viewer": self.viewer, "status": self.status,
                "continuable": self.continuable, "next": [a.to_dict() for a in self.next], "halt": None if self.halt is None else self.halt.to_dict(),
                "convention_set": None if self.convention_set is None else self.convention_set.to_dict()}


@dataclass(frozen=True)
class VerifierReport:
    """検証者用の記録（ホストだけが持つ。見る人に渡さない）。元のコード・例外の生の文・traceback・停止の診断用の文・コマンドを持つ。"""

    mapped: bool
    engine_code: str | None = None
    exception_type: str | None = None
    raw_message: str | None = None
    traceback: str | None = None
    problems: tuple[str, ...] = ()
    halt_code: str | None = None
    halt_message: str | None = None
    halt_references: tuple[str, ...] = ()
    command: Mapping[str, Any] | None = None
    exception: BaseException | None = None
