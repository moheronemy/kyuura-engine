"""閲覧用記録（v0.155。docs/view-record-v0.155.md。仕様案 docs/diagnostics-replay-api-design.md の U5）。

本人・相手・観戦者の 1 人（作るときに固定する）が、その時点で知ることのできた情報だけを持つ対戦の記録です。完全な再現用記録（``replay_record``）とは別の用途・形式
（``kyuura_view_format``）で、閲覧用記録から対戦を再実行すること・状態を復元することは保証しません。

- 各項目は、その時点の ``observe``・閲覧用ログ（``visible_log``・``visible_segment_logs``）・``CommandResult.view_for`` から作り、JSON の値として写して固定する（あとで公開された
  情報を過去の項目へ遡って入れない。元の状態・ログがあとで変わっても、記録した項目は変わらない）
- 拒否は、送った本人の記録にだけ入る（相手・観戦者の記録には、行も通知も連番の欠けも残らない）。連番 ``n`` は、その閲覧者の記録に出した項目だけで連続する
- 入れないもの: seed・乱数の状態とその確認値・完全な状態の確認値・相手のデッキリスト・デッキの並び・完全な記録のコマンド・生の例外文・traceback・検証者用の診断・完全な記録の
  ``seq``・``accepted_index``・``operation_id``。実時刻・所要時間も入れない（通信のタイミングの対策ではない）
- 見る人の値は 0・1・None だけ。検証者の情報は、この記録からは取り出せない（完全な記録・``CommandResult.verifier`` はホストが別に持つ）
"""

from __future__ import annotations

import json
from typing import Any

from . import __version__
from . import diagnostics as D
from .adapter import CommandResult, HostedGame, start_game
from .observation import observe, visible_log, visible_segment_logs
from .replay_record import FORMAT_KEY as REPLAY_FORMAT_KEY
from .replay_record import (
    RecordFormatError,
    ReplayCollector,
    ReplayRecord,
    read_json_object,
)
from .state import GameState

VIEW_FORMAT = 1
SUPPORTED_VIEW_FORMATS = (1,)
VIEW_FORMAT_KEY = "kyuura_view_format"

ORIGIN_NEW_GAME = "new_game"  # 対戦の開始から記録した
ORIGIN_ATTACHED = "attached"  # 対戦の途中（構築した状態を含む）から記録を始めた
KIND_START = "start"
KIND_UPDATE = "update"  # 受理した操作のあとの観測・新しいログ・状態の知らせ
KIND_OWN_REJECTION = "own_rejection"  # 本人が送って拒否された操作の診断（本人の記録だけ）
KIND_UNAVAILABLE = "unavailable"  # 処理できない結果（内容は持たない）
END_CLOSED = "closed"
END_ABORTED = "aborted"

HEADER_KEYS = frozenset({"viewer", "role", "origin", "engine_version", "convention_set", "own_decklist", "diagnostic_schema"})
ENTRY_KEYS = {
    KIND_START: frozenset({"n", "kind", "segment", "events", "observation", "notice"}),
    KIND_UPDATE: frozenset({"n", "kind", "segment", "events", "observation", "notice"}),
    KIND_OWN_REJECTION: frozenset({"n", "kind", "segment", "notice"}),
    KIND_UNAVAILABLE: frozenset({"n", "kind", "segment", "notice"}),
}
END_KEYS = frozenset({"state", "entries", "status"})
# 閲覧用記録のどこにも入ってはいけない項目の名前（ログの ``hidden`` の中の名前は、隠した項目の名前なので除く）
FORBIDDEN_KEYS = frozenset({"seed", "rng", "rng_state", "rng_state_sha256", "rng_fingerprint", "state_digest", "check", "engine_code", "raw_message", "traceback",
                            "problems", "operation_id", "seq", "accepted_index", "command", "verifier", "decklists", "resume", "context", "halt_message",
                            "halt_references", REPLAY_FORMAT_KEY})

MALFORMED = "malformed"
INCONSISTENT = "inconsistent"
INCOMPLETE = "incomplete"
UNSUPPORTED = "unsupported"
STRUCTURE_VALID = "structure_valid"
REPORT_ORDER = (MALFORMED, INCONSISTENT, INCOMPLETE, UNSUPPORTED)

_TOKEN = object()


def _frozen(value) -> Any:
    """JSON の値としての写し（タプルはリストに。元のオブジェクトと共有しない）。"""
    return json.loads(json.dumps(value, ensure_ascii=False))


def _notice(view) -> dict[str, Any]:
    data = view.to_dict()
    data.pop("operation_id", None)  # ホストの操作の識別（完全な記録と対応付けられる）は入れない
    return data


def _status_notice(state: GameState, viewer) -> dict[str, Any]:
    halt, _ = D.public_halt(state)
    return D.StatusNotice(viewer=viewer, status=D.status_of(state), continuable=D.continuable(state), next=D.next_actions(state), halt=halt,
                          convention_set=D.convention_ref(state)).to_dict()


class ViewRecord:
    """閲覧用記録（見る人に渡してよい値だけ）。repr は形式・閲覧者・項目の数・閉じ方だけ。``data`` は写しを返す。"""

    def __init__(self, data: dict[str, Any]):
        self._data = _frozen(data)

    @property
    def data(self) -> dict[str, Any]:
        return _frozen(self._data)

    @property
    def viewer(self):
        return (self._data.get("header") or {}).get("viewer")

    def __repr__(self) -> str:
        end = self._data.get("end")
        return (f"ViewRecord(format={self._data.get(VIEW_FORMAT_KEY)!r}, viewer={self.viewer!r}, entries={len(self._data.get('entries') or [])}, "
                f"end={None if not isinstance(end, dict) else end.get('state')!r})")

    __str__ = __repr__


def dumps_view_record(record: ViewRecord) -> str:
    return json.dumps(record._data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def loads_view_record(text: str | bytes) -> ViewRecord:
    """閲覧用記録の JSON を読む（U3 と同じ安全な読み取り。``RecordFormatError``）。中身の検証は ``validate_view_record``。"""
    return ViewRecord(read_json_object(text))


# ---------------------------------------------------------------- 収集


class ViewRecorder:
    """閲覧者を固定した収集器。``ViewHost`` か ``attach`` で作る（閲覧者を途中で変える API はない）。

    ``add`` には、ホストが送った操作の ``CommandResult`` を順に渡す（受理なら新しい状態、拒否なら前と同じ状態のはず）。前の状態と合わない結果は ``ValueError``（ホストの誤り）。
    渡された結果の正しさそのものは確かめない（信頼されたホストの責任）。"""

    def __init__(self, token, viewer, state: GameState, origin: str, start_notice: dict[str, Any]):
        if token is not _TOKEN:
            raise TypeError("ViewRecorder は ViewHost か ViewRecorder.attach で作る")
        D.check_viewer(viewer)
        self._viewer = viewer
        self._state = state
        self._segment = state.segment_index
        self._cursor = len(state.log)
        identity = D.convention_ref(state)
        self._header = _frozen({
            "viewer": viewer, "role": "spectator" if viewer is None else "player", "origin": origin, "engine_version": __version__,
            "convention_set": None if identity is None else identity.to_dict(), "diagnostic_schema": D.DIAGNOSTIC_SCHEMA,
            "own_decklist": None if viewer is None else sorted(state.decklists[viewer]),  # 自分で出したデッキ（並びではなく、カードの組）
        })
        self._entries: list[dict[str, Any]] = []
        self._end: dict[str, Any] | None = None
        past = [{"segment": s["index"], "log_index": i, "event": event} for s in visible_segment_logs(state, viewer) for i, event in enumerate(s["log"])]
        self._append(KIND_START, events=past + self._events_since(state, 0), observation=observe(state, viewer), notice=start_notice)
        self._cursor = len(state.log)

    @classmethod
    def attach(cls, viewer, state: GameState) -> ViewRecorder:
        """対戦の途中（構築した状態を含む）から記録を始める（``origin`` は attached）。その時点の観測と、今の区間のログの閲覧用の写しから始める。"""
        return cls(_TOKEN, viewer, state, ORIGIN_ATTACHED, _status_notice(state, viewer))

    @property
    def viewer(self):
        return self._viewer

    @property
    def stopped(self) -> bool:
        return self._end is not None

    def _events_since(self, state: GameState, cursor: int) -> list[dict[str, Any]]:
        """今の区間のログの、``cursor`` からあとの閲覧用の写し（その時点の見える範囲）。"""
        log = visible_log(state, self._viewer)
        return [{"segment": state.segment_index, "log_index": i, "event": log[i]} for i in range(cursor, len(log))]

    def _append(self, kind: str, **fields) -> None:
        entry = {"n": len(self._entries) + 1, "kind": kind, "segment": self._segment, **fields}
        self._entries.append(_frozen(entry))

    def add(self, result: CommandResult) -> None:
        if self._end is not None:
            raise ValueError(f"閲覧用記録は {self._end['state']}（項目を加えられない）")
        viewer = self._viewer
        if result.outcome == D.REJECTED:
            if result.state is not self._state:
                raise ValueError("拒否の結果の状態が、記録している状態と違う（ホストの誤り）")
            if viewer is not None and viewer == result.actor:
                self._append(KIND_OWN_REJECTION, notice=_notice(result.view_for(viewer)))
            return
        if result.outcome == D.FAILED:
            self._append(KIND_UNAVAILABLE, notice=_notice(result.view_for(viewer)))
            self._end = {"state": END_ABORTED, "entries": len(self._entries), "status": D.UNAVAILABLE}
            return
        state = result.state
        events: list[dict[str, Any]] = []
        if state.segment_index != self._segment:
            # 前の区間の、まだ記録していないログ（区間が終わったときの見える範囲。うらのまま山札にもどったカードの uid は見せない）と、新しい区間のログ
            previous = next(s for s in visible_segment_logs(state, viewer) if s["index"] == self._segment)["log"]
            events = [{"segment": self._segment, "log_index": i, "event": previous[i]} for i in range(self._cursor, len(previous))]
            self._segment = state.segment_index
            self._cursor = 0
        events += self._events_since(state, self._cursor)
        self._append(KIND_UPDATE, events=events, observation=observe(state, viewer), notice=_notice(result.view_for(viewer)))
        self._state = state
        self._cursor = len(state.log)

    def close(self) -> ViewRecord:
        """記録を閉じる（対戦の終局とは別。閉じた記録から状態を復元できるとはしない）。"""
        if self._end is None:
            last = self._entries[-1]["notice"]
            self._end = {"state": END_CLOSED, "entries": len(self._entries), "status": last["status"]}
        return self.record()

    def record(self) -> ViewRecord:
        return ViewRecord({VIEW_FORMAT_KEY: VIEW_FORMAT, "header": self._header, "entries": self._entries, "end": self._end})


class ViewHost:
    """信頼されたホストが、対戦を進めながら閲覧者ごとの閲覧用記録を集める（閲覧者は作るときに固定）。対戦の実行は U2・U3（``HostedGame``・``ReplayCollector``）に任せる。"""

    def __init__(self, token, game, viewers, start: CommandResult):
        if token is not _TOKEN:
            raise TypeError("ViewHost は ViewHost.start で作る")
        self._game = game
        self._recorders = {v: ViewRecorder(_TOKEN, v, start.state, ORIGIN_NEW_GAME, _notice(start.view_for(v))) for v in viewers}

    @classmethod
    def start(cls, deck0, deck1, seed, *, viewers=(0, 1, None), conventions=None, full_record: bool = True, record_rejections: bool = True,
              game_id: str | None = None) -> tuple[ViewHost | None, CommandResult]:
        """対戦を始め、閲覧者ごとの収集を始める。``full_record`` なら完全な再現用記録も集める（``ReplayCollector``）。開始が拒否・処理できなければ (None, 結果)。"""
        viewers = tuple(viewers)
        for v in viewers:
            D.check_viewer(v)
        if len(set(viewers)) != len(viewers):
            raise ValueError("閲覧者が重なっている")
        if full_record:
            collector, result = ReplayCollector.start(deck0, deck1, seed, conventions=conventions, game_id=game_id, record_rejections=record_rejections,
                                                      include_git=False)
            game = collector
        else:
            options = {} if conventions is None else {"conventions": conventions}
            result = start_game(deck0, deck1, seed, **options)
            game = HostedGame(result.state) if result.outcome == D.ACCEPTED else None
        if result.outcome != D.ACCEPTED:
            return None, result
        return cls(_TOKEN, game, viewers, result), result

    @property
    def state(self) -> GameState:
        """ホストの中だけで使う今の状態。"""
        return self._game.state

    def submit(self, command, *, submitter: int | None = None, operation_id: str | None = None) -> CommandResult:
        result = self._game.submit(command, submitter=submitter, operation_id=operation_id)
        for recorder in self._recorders.values():
            recorder.add(result)
        return result

    def view_record(self, viewer) -> ViewRecord:
        D.check_viewer(viewer)
        return self._recorders[viewer].record()

    def close(self) -> tuple[ReplayRecord | None, dict[Any, ViewRecord]]:
        """閲覧用記録（と完全な記録）を閉じる。完全な記録は検証者用（閲覧者に渡さない）。"""
        full = self._game.close() if isinstance(self._game, ReplayCollector) else None
        return full, {v: r.close() for v, r in self._recorders.items()}


def view_records_from_replay(record: ReplayRecord | dict[str, Any], viewers=(0, 1, None)):
    """完全な再現用記録から、U4 の検証つきの再実行で閲覧用記録を作る（各時点の状態から作る。最後の状態だけから作らない）。

    (再実行の結果, 閲覧者 → 閲覧用記録) を返す。再実行が ``succeeded`` でなければ、閲覧用記録は None（不一致・内部エラー・不完全・記録された失敗の記録を、検証済みの閲覧用記録として
    出さない）。"""
    from .replay_run import SUCCEEDED, replay

    viewers = tuple(viewers)
    for v in viewers:
        D.check_viewer(v)
    recorders: dict[Any, ViewRecorder] = {}

    def observer(result: CommandResult) -> None:
        if not recorders:
            for v in viewers:
                recorders[v] = ViewRecorder(_TOKEN, v, result.state, ORIGIN_NEW_GAME, _notice(result.view_for(v)))
            return
        for recorder in recorders.values():
            recorder.add(result)

    report = replay(record, observer=observer)
    if report.status != SUCCEEDED:
        return report, None
    return report, {v: r.close() for v, r in recorders.items()}


# ---------------------------------------------------------------- 構造の検証


def _forbidden(value, path: str, found: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FORBIDDEN_KEYS:
                found.append(f"{path}.{key}")
            if key == "hidden" and isinstance(item, dict):
                if not all(v is None or (isinstance(v, int) and not isinstance(v, bool)) for v in item.values()):
                    found.append(f"{path}.hidden")
                continue
            _forbidden(item, f"{path}.{key}", found)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _forbidden(item, f"{path}[{i}]", found)


def _is_viewer(value) -> bool:
    return value is None or (type(value) is int and value in (0, 1))


def validate_view_record(record: ViewRecord | dict[str, Any]):
    """閲覧用記録の構造の検証。``replay_record.RecordReport`` と同じ形（``status``・``problems``・``complete``・``end_state``・``replay_verified`` はいつも偽）。

    確かめるのは形・許した項目だけか・連番・閲覧者・区間とログの位置の連続・終わりの情報。記録が本当に安全な投影から作られたこと、対戦が正しかったこと、手で作った記録の内容は
    確かめない（認証ではない）。"""
    from .replay_record import Problem, RecordReport

    data = record._data if isinstance(record, ViewRecord) else record
    problems: list[Problem] = []

    def add(kind, code, path):
        problems.append(Problem(kind, code, path))

    def report():
        kinds = {p.kind for p in problems}
        status = next((k for k in REPORT_ORDER if k in kinds), STRUCTURE_VALID)
        end = data.get("end") if isinstance(data, dict) else None
        end_state = end.get("state") if isinstance(end, dict) else None
        return RecordReport(status=status, problems=tuple(problems), complete=end_state is not None and INCOMPLETE not in kinds, end_state=end_state)

    if not isinstance(data, dict):
        add(MALFORMED, "not_object", "$")
        return report()
    fmt = data.get(VIEW_FORMAT_KEY)
    if type(fmt) is not int:
        add(MALFORMED, "format_missing", f"$.{VIEW_FORMAT_KEY}")
        return report()
    if fmt not in SUPPORTED_VIEW_FORMATS:
        add(UNSUPPORTED, "format_unknown", f"$.{VIEW_FORMAT_KEY}")
        return report()
    for key in sorted(set(data) - {VIEW_FORMAT_KEY, "header", "entries", "end"}):
        add(MALFORMED, "unknown_field", f"$.{key}")
    found: list[str] = []
    _forbidden(data, "$", found)
    for path in found:
        add(MALFORMED, "forbidden_field", path)
    header = data.get("header")
    if not isinstance(header, dict) or set(header) != HEADER_KEYS or not _is_viewer(header.get("viewer")):
        add(MALFORMED, "header_bad", "$.header")
        return report()
    viewer = header["viewer"]
    if header["role"] != ("spectator" if viewer is None else "player") or header["origin"] not in (ORIGIN_NEW_GAME, ORIGIN_ATTACHED):
        add(INCONSISTENT, "header_role_or_origin", "$.header")
    if (viewer is None) != (header["own_decklist"] is None):
        add(INCONSISTENT, "own_decklist_for_viewer", "$.header.own_decklist")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        add(MALFORMED, "entries_missing", "$.entries")
        return report()
    segment = None
    log_next: dict[int, int] = {}
    aborted_at = None
    for i, entry in enumerate(entries):
        path = f"$.entries[{i}]"
        if not isinstance(entry, dict) or entry.get("kind") not in ENTRY_KEYS:
            add(MALFORMED, "entry_kind_unknown", path)
            continue
        kind = entry["kind"]
        if set(entry) != ENTRY_KEYS[kind]:
            add(MALFORMED, "entry_fields", path)
            continue
        if entry["n"] != i + 1:
            add(INCONSISTENT, "n_out_of_order", f"{path}.n")
        if (kind == KIND_START) != (i == 0):
            add(INCONSISTENT, "start_not_first", path)
        if aborted_at is not None:
            add(INCONSISTENT, "entry_after_unavailable", path)
        notice = entry["notice"]
        if not isinstance(notice, dict) or notice.get("viewer", "x") != viewer or notice.get("status") not in D.STATUSES:
            add(INCONSISTENT, "notice_viewer_or_status", f"{path}.notice")
            continue
        if kind == KIND_OWN_REJECTION and (viewer is None or notice.get("role") != "actor" or notice.get("outcome") != D.REJECTED):
            add(INCONSISTENT, "rejection_not_own", path)
        if kind == KIND_UNAVAILABLE:
            aborted_at = i
            if notice["status"] != D.UNAVAILABLE:
                add(INCONSISTENT, "unavailable_status", path)
        if type(entry["segment"]) is not int:
            add(MALFORMED, "segment_bad", f"{path}.segment")
            continue
        if segment is not None and entry["segment"] not in (segment, segment + 1):
            add(INCONSISTENT, "segment_jump", f"{path}.segment")
        if kind in (KIND_START, KIND_UPDATE):
            if not isinstance(entry["events"], list) or not isinstance(entry["observation"], dict):
                add(MALFORMED, "entry_values", path)
                continue
            if entry["observation"].get("viewer", "x") != viewer:
                add(INCONSISTENT, "observation_viewer", f"{path}.observation")
            for j, item in enumerate(entry["events"]):
                if not isinstance(item, dict) or set(item) != {"segment", "log_index", "event"} or not isinstance(item.get("event"), dict):
                    add(MALFORMED, "event_bad", f"{path}.events[{j}]")
                    continue
                seg, index = item["segment"], item["log_index"]
                expected = log_next.get(seg, 0)
                allowed = type(seg) is int and (seg <= entry["segment"] if kind == KIND_START else seg in (entry["segment"], entry["segment"] - 1))
                if not allowed or index != expected:
                    add(INCONSISTENT, "log_index_gap_or_duplicate", f"{path}.events[{j}]")
                log_next[seg] = index + 1 if type(index) is int else expected
        segment = entry["segment"]
    end = data.get("end")
    if end is None:
        add(INCOMPLETE, "end_missing", "$.end")
    elif not isinstance(end, dict) or set(end) != END_KEYS or end.get("state") not in (END_CLOSED, END_ABORTED):
        add(MALFORMED, "end_bad", "$.end")
    else:
        if end["entries"] != len(entries):
            add(INCONSISTENT, "end_entry_count", "$.end.entries")
        last = entries[-1] if isinstance(entries[-1], dict) else {}
        if isinstance(last.get("notice"), dict) and end["status"] != last["notice"].get("status"):
            add(INCONSISTENT, "end_status", "$.end.status")
        if (end["state"] == END_ABORTED) != (aborted_at is not None):
            add(INCONSISTENT, "end_state_mismatch", "$.end.state")
    return report()


__all__ = [
    "VIEW_FORMAT",
    "RecordFormatError",
    "ViewHost",
    "ViewRecord",
    "ViewRecorder",
    "dumps_view_record",
    "loads_view_record",
    "validate_view_record",
    "view_records_from_replay",
]
