"""クライアント向けの最小のアダプタ（v0.164。docs/client-api-v0.164.md）。

別のリポジトリの GUI が、エンジンの内部の型（``GameState``・決定・``CommandResult``・検証者用の記録）を知らずに使える、JSON にできる要求と応答の境界。
通信の方式に依存しない（同じプロセスで ``handle(dict) -> dict`` を呼ぶ）。実行は U7（``legal_actions``）と U2（``adapter``）に任せ、別の実行器・独自の
合法性の判定を作らない。

- 契約の識別 ``kyuura-client-api``・形式の版 1（ゲームの版・規約集合・記録の形式とは別の番号）
- 入口（``PlayerEndpoint``・``SpectatorEndpoint``・``HostEndpoint``）は、信頼されたホストが ``ClientHub`` から作って配る。要求に操作主体・閲覧者を書く項目はない
  （書けば知らない項目として拒否する）。入口の所有と配り方、認証は、ホストするアプリケーションの責任
- 応答（要求した入口だけへ）と、公開の更新（受理のあと、閲覧者ごとに許された観測と状態の知らせ）を分ける。拒否・ホストの段の拒否では更新を作らない
"""

from __future__ import annotations

import json
from typing import Any

from . import diagnostics as D
from . import legal_actions as L
from .adapter import HostStoppedError, UnusableStateError, checked_state_copy  # noqa: F401（UnusableStateError は入口の拒否の型として公開）
from .observation import observe

CONTRACT = "kyuura-client-api"
FORMAT = 1

# 誤りのコード（決まった文。要求の値を文に入れない）
REQUEST_INVALID = "CLIENT_REQUEST_INVALID"
CONTRACT_UNKNOWN = "CLIENT_CONTRACT_UNKNOWN"
FORMAT_UNSUPPORTED = "CLIENT_FORMAT_UNSUPPORTED"
REQUEST_UNKNOWN = "CLIENT_REQUEST_UNKNOWN"
FIELD_UNKNOWN = "CLIENT_FIELD_UNKNOWN"
FIELD_INVALID = "CLIENT_FIELD_INVALID"
GAME_UNAVAILABLE = "CLIENT_GAME_UNAVAILABLE"
ERROR_MESSAGES = {
    REQUEST_INVALID: "要求が JSON のオブジェクトでない",
    CONTRACT_UNKNOWN: "要求の契約の識別が kyuura-client-api でない",
    FORMAT_UNSUPPORTED: "要求の形式の版に対応していない（この版は 1）",
    REQUEST_UNKNOWN: "この入口が受け付けない要求の種類",
    FIELD_UNKNOWN: "要求に知らない項目がある",
    FIELD_INVALID: "要求の項目の型・値が正しくない",
    GAME_UNAVAILABLE: "対戦は処理できない結果のあと止まっている（ホスト・検証者が調べる）",
}

ROLE_PLAYER = "player"
ROLE_SPECTATOR = "spectator"
ROLE_HOST = "host"
_ENVELOPE = frozenset({"contract", "format", "type"})
_HANDLE = {"game": str, "revision": str, "candidate": str}
# 入口ごとに受け付ける要求の種類と、その項目（必須・任意）
_REQUESTS = {
    ROLE_PLAYER: {"view": ({}, {}), "updates": ({}, {}), "candidates": ({}, {}), "inputs": (_HANDLE, {}),
                  "check": (_HANDLE, {"choices": list}), "submit": (_HANDLE, {"choices": list, "operation_id": str})},
    ROLE_SPECTATOR: {"view": ({}, {}), "updates": ({}, {})},
    ROLE_HOST: {"view": ({}, {}), "updates": ({}, {}), "candidates": ({}, {}), "inputs": (_HANDLE, {}),
                "check": (_HANDLE, {"choices": list}), "submit": (_HANDLE, {"choices": list, "operation_id": str})},
}
MAX_TEXT = 128  # 取っ手・候補の番号・operation_id の長さの上限
MAX_CHOICES = 64
# 送り直しが要る拒否（候補を取り直す）
_REFETCH = frozenset({L.CANDIDATES_STALE, L.CANDIDATES_WRONG_GAME, L.CANDIDATES_WRONG_ACTOR, L.CANDIDATE_UNKNOWN})


def _json(value):
    """許した値だけの JSON の写し（dataclass・enum・例外・関数を渡さない）。"""
    return json.loads(json.dumps(value, ensure_ascii=False))


def _envelope(kind, **body) -> dict[str, Any]:
    return _json({"contract": CONTRACT, "format": FORMAT, "type": kind, **body})


def _error(kind, code: str) -> dict[str, Any]:
    return _envelope(kind, ok=False, error={"code": code, "message": ERROR_MESSAGES[code]})


def _status(state) -> dict[str, Any]:
    """全員に見える状態の区分（観測と同じ公開の値。だれの入力・ホストの操作を待つか）。"""
    halt, _ = D.public_halt(state)
    ref = D.convention_ref(state)
    waiting = []
    for action in D.next_actions(state):
        if action.kind in (D.NEXT_JANKEN, D.NEXT_START_SUDDEN_DEATH):
            waiting.append({"kind": action.kind, "by": ROLE_HOST})
        else:
            waiting.append({"kind": action.kind, "by": "players" if action.player is None else action.player})
    return {"status": D.status_of(state), "phase": state.phase.value, "segment": state.segment_index, "continuable": D.continuable(state),
            "waiting": waiting, "halt": None if halt is None else halt.to_dict(), "convention_set": None if ref is None else ref.to_dict()}


def _choices_ok(choices) -> bool:
    return len(choices) <= MAX_CHOICES and all((type(c) is str and len(c) <= MAX_TEXT) or type(c) is int for c in choices)


class ClientHub:
    """信頼されたホストの側の対戦（``legal_actions.ActionHost`` を包む）。入口を作って配る・公開の更新を受け取るのはホストのアプリケーション。

    ``verifier`` は、処理の結果（``CommandResult``。検証者用の値を含む）をホスト・検証者だけが受け取る呼び出し（クライアントに渡さない）。
    公開の更新は、この hub の入口から送って受理された操作だけから作る（ホストが包んだ対戦へ直接送った操作では更新を作らない。直接送るのは契約の外）。"""

    def __init__(self, game, *, verifier=None):
        self._verifier = verifier
        self._host = L.ActionHost(game, on_result=self._on_result)
        self._seq = 0  # 公開の更新の番号（応答の number）（受理でだけ進む。拒否では進めない。秘密の値・エンジンの乱数を使わない）
        self._outbox: dict[Any, list] = {0: [], 1: [], ROLE_SPECTATOR: [], ROLE_HOST: []}

    @classmethod
    def start(cls, deck0, deck1, seed, *, verifier=None, **options) -> tuple[ClientHub | None, dict[str, Any]]:
        """対戦を始める（``adapter.start_game``）。2 つめの値は始めの結果の公開の知らせ（JSON）。開始できなければ (None, 知らせ)。"""
        from .adapter import HostedGame, start_game

        result = start_game(deck0, deck1, seed, **options)
        if verifier is not None:
            verifier(None, result)
        notice = _envelope("start", ok=result.outcome == D.ACCEPTED, outcome=result.outcome, status=result.status,
                           diagnostic=None if result.diagnosis is None else {"diagnostic_id": result.diagnosis.diagnostic_id, "category": result.diagnosis.category,
                                                                              "message": result.diagnosis.message})
        if result.outcome != D.ACCEPTED:
            return None, notice
        return cls(HostedGame(result.state), verifier=verifier), notice

    @classmethod
    def from_state(cls, state, *, verifier=None) -> ClientHub:
        """状態の複製から（ホスト・テストの側。復元した状態から始めるとき）。

        v0.177（PT5E-FROM-STATE-INVARIANT）: ``adapter.checked_state_copy`` で、型・複製・複製の不変条件を確かめてから包む（``ActionHost.from_state`` と同じ確かめ）。
        不整合なら ``UnusableStateError``（``TypeError`` は型の違い）で、hub・セッション・取っ手を作らない。例外の文は固定で、詳しい問題（``problems``）はホスト・
        検証者だけが読む（プレイヤー向けの応答・公開の更新には出さない）。``ClientHub(game)`` の直接の組み立ては確かめない（信頼された内部）。"""
        from .adapter import HostedGame

        return cls(HostedGame(checked_state_copy(state)), verifier=verifier)

    def player(self, actor) -> PlayerEndpoint:
        """認証したプレイヤー（0・1）の入口。本人だけに渡す（ホストの責任）。"""
        return PlayerEndpoint(self, self._host.session(actor))

    def spectator(self) -> SpectatorEndpoint:
        """観戦者の入口（観測と公開の更新だけ。操作の候補・送信はない）。"""
        return SpectatorEndpoint(self)

    def host(self) -> HostEndpoint:
        """ホストの操作の入口。信頼されたアプリケーションだけが持つ（GUI の通常の要求に混ぜない）。"""
        return HostEndpoint(self, self._host.host_session())

    def take_updates(self, audience) -> list[dict[str, Any]]:
        """閲覧者（0・1・"spectator"・"host"）へ配る公開の更新を取り出す（ホストのアプリケーションが配る）。"""
        if audience not in self._outbox:
            raise ValueError("閲覧者は 0・1・spectator・host")
        out, self._outbox[audience] = self._outbox[audience], []
        return out

    # ---------------------------------------------------------------- 内部

    def _state(self):
        return self._host._state()

    def _on_result(self, actor, result) -> None:
        if self._verifier is not None:
            self._verifier(actor, result)  # 検証者用の値を含む結果は、ホスト・検証者だけへ
        if result.outcome == D.REJECTED:
            return  # 拒否: 公開の更新を作らない（拒否の有無・中身を他の閲覧者に伝えない）
        self._seq += 1
        state = result.state
        for audience in self._outbox:
            viewer = audience if audience in (0, 1) else None
            if state is None:  # 処理できない結果: 対戦が止まったことだけ（詳細はホスト・検証者へ）
                body = {"status": {"status": D.UNAVAILABLE, "continuable": False, "waiting": []}, "observation": None}
            else:
                body = {"status": _status(state), "observation": observe(state, viewer)}
            self._outbox[audience].append(_envelope("update", number=self._seq, **body))


class _Endpoint:
    role = ""

    def __init__(self, hub: ClientHub, session=None):
        self._hub = hub
        self._session = session

    def handle(self, request) -> dict[str, Any]:
        """JSON のオブジェクトの要求を受け、JSON のオブジェクトの応答を返す（例外を投げない。処理できない結果のあとは CLIENT_GAME_UNAVAILABLE）。"""
        if not isinstance(request, dict):
            return _error(None, REQUEST_INVALID)
        kind = request.get("type") if isinstance(request.get("type"), str) else None
        if request.get("contract") != CONTRACT:
            return _error(kind, CONTRACT_UNKNOWN)
        if type(request.get("format")) is not int or request.get("format") != FORMAT:
            return _error(kind, FORMAT_UNSUPPORTED)
        spec = _REQUESTS[self.role].get(kind)
        if spec is None:
            return _error(kind, REQUEST_UNKNOWN)
        required, optional = spec
        extra = set(request) - _ENVELOPE - set(required) - set(optional)
        if extra:
            return _error(kind, FIELD_UNKNOWN)
        for name, typ in required.items():
            if type(request.get(name)) is not typ or len(request[name]) > MAX_TEXT:
                return _error(kind, FIELD_INVALID)
        for name, typ in optional.items():
            if name in request and (type(request[name]) is not typ or (typ is str and len(request[name]) > MAX_TEXT)):
                return _error(kind, FIELD_INVALID)
        if "choices" in request and not _choices_ok(request["choices"]):
            return _error(kind, FIELD_INVALID)
        try:
            return getattr(self, "_" + kind)(request)
        except HostStoppedError:
            return _error(kind, GAME_UNAVAILABLE)

    def _view(self, request) -> dict[str, Any]:
        state = self._hub._state()
        viewer = self._viewer()
        return _envelope("view", ok=True, viewer=viewer if viewer is not None else self.role, status=_status(state), observation=observe(state, viewer))

    def _updates(self, request) -> dict[str, Any]:
        return _envelope("updates", ok=True, updates=self._hub.take_updates(self._audience()))

    def _viewer(self):
        return None

    def _audience(self):
        return self.role

    def _candidates(self, request) -> dict[str, Any]:
        self._hub._state()
        return _envelope("candidates", ok=True, response=self._session.candidates())

    def _inputs(self, request) -> dict[str, Any]:
        self._hub._state()
        answer = self._session.inputs(request["game"], request["revision"], request["candidate"])
        refusal = answer.get("refusal")
        return _envelope("inputs", ok=refusal is None, response=answer, refetch_required=refusal is not None and refusal["code"] in _REFETCH)

    def _check(self, request) -> dict[str, Any]:
        self._hub._state()
        answer = self._session.check(request["game"], request["revision"], request["candidate"], list(request.get("choices", [])))
        refusal = answer["refusal"]
        return _envelope("check", ok=True, response=answer, refetch_required=refusal is not None and refusal["code"] in _REFETCH)

    def _submit(self, request) -> dict[str, Any]:
        self._hub._state()
        result = self._session.submit(request["game"], request["revision"], request["candidate"], list(request.get("choices", [])),
                                      operation_id=request.get("operation_id"))
        refusal = None if result.refusal is None else {"code": result.refusal.code, "message": result.refusal.message}
        refetch = result.outcome == D.ACCEPTED or (refusal is not None and refusal["code"] in _REFETCH)
        return _envelope("submit", ok=True, outcome=result.outcome, refusal=refusal, result=None if result.view is None else result.view.to_dict(),
                         refetch_required=refetch)


class PlayerEndpoint(_Endpoint):
    """プレイヤーの入口（本人の観測・候補・入力・検査・送信と、本人への公開の更新）。"""

    role = ROLE_PLAYER

    def _viewer(self):
        return self._session.actor

    def _audience(self):
        return self._session.actor


class SpectatorEndpoint(_Endpoint):
    """観戦者の入口（観戦者の観測と公開の更新だけ）。"""

    role = ROLE_SPECTATOR


class HostEndpoint(_Endpoint):
    """ホストの操作の入口（ジャンケンの結果・延長戦の開始。観測は観戦者と同じ範囲）。信頼されたアプリケーションだけが持つ。"""

    role = ROLE_HOST
