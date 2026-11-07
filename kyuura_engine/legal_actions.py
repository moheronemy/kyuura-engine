"""合法手 API の最小の実装（U7-1。docs/legal-actions-u7-1.md。仕様案 docs/legal-actions-api-design.md）。

対象は決定への回答（サイドを取る・バトル場に出す・ほかの決定）と「番を終える」だけ。ほかの操作の種類は候補に出さず、対応していない種類として示す（ゲーム上できないこととは別）。

境界:

- ``ActionHost``（信頼されたホストの入口）: ホストが持つ対戦（``adapter.HostedGame`` と同じ形の対戦。``HostedGame``・``snapshot.RestoredGame``・``view_record.ViewHost``）を包み、
  認証した操作主体（0・1）に ``ActorSession`` を渡す。操作の実行は包んだ対戦の ``submit``（U2 の ``CommandResult``）だけで、別の実行器を作らない
- ``ActorSession``（クライアント向けの入口）: 操作主体はホストが結びつけた値に固定。要求にプレイヤーの番号を書かせない。返すのは JSON にできる値の写しだけ（内部の可変の
  状態・候補の記録を返さない）
- 取っ手（``game``・``revision``）: ``secrets`` の乱数（エンジンの乱数を使わない）。状態のハッシュ・乱数の確認値・決定の番号から作らない。保存・復元しない
- 候補の作成は ``apply_command``・先読みを呼ばない。状態・乱数・ログを変えない。最終の判定は ``apply_command``（包んだ対戦の ``submit``）
- 処理できるか（``processability``）と、入力を本人に示して安全か（``input_disclosure``）は別の軸。情報境界を確かめていない決定の入力（選べるもの・数・並び）は返さない
"""

from __future__ import annotations

import json
import secrets
from collections import deque
from dataclasses import dataclass
from typing import Any

from . import diagnostics as D
from .adapter import CommandResult, HostedGame, HostStoppedError
from .commands import EndTurn, ResolveDecision
from .decisions import ARRANGE_DECK_TOP, value_range
from .observation import (
    DECK_REVEALING_KINDS,
    LOOKED_HAND_KINDS,
    OPTION_MEANINGS,
    observe,
)
from .state import GameState, Phase

FORMAT_KEY = "kyuura_legal_actions_format"
FORMAT = 1

# 処理可能性（docs/legal-actions-api-design.md 6 章）。公開してよいかとは別の軸
SUPPORTED = "supported"
MAY_STOP_LATER = "may_stop_later"
RULING_UNRESOLVED = "unresolved_ruling"
NOT_IMPLEMENTED = "not_implemented"
TECHNICAL_LIMIT = "technical_limit"
UNVERIFIED = "unverified"
PROCESSABILITY = (SUPPORTED, MAY_STOP_LATER, RULING_UNRESOLVED, NOT_IMPLEMENTED, TECHNICAL_LIMIT, UNVERIFIED)
EXECUTABLE = frozenset({SUPPORTED, MAY_STOP_LATER, UNVERIFIED})

# 入力を本人に示して安全か（情報境界）
DISCLOSURE_CONFIRMED = "confirmed"
DISCLOSURE_UNCONFIRMED = "unconfirmed"
DISCLOSURE_NONE = "no_input"

# 選んだ順の意味（確かめた分類だけ。未確認を順不同と扱わない）
ORDER_SIGNIFICANT = "significant"  # 答えの並びが結果に入る（確かめた種類）
ORDER_NOT_APPLICABLE = "not_applicable"  # 選ぶ数が 1 以下（並びがない）
ORDER_UNCONFIRMED = "unconfirmed"  # 確かめていない（U7 は並びをそのまま送る）
ORDER_SIGNIFICANT_KINDS = frozenset({ARRANGE_DECK_TOP})  # 答えの並びが山札の上の新しい並び（deck[:count] = list(choices)。どの出し方も同じ）

# 選べるものの情報境界を確かめた決定の種類（docs/legal-actions-u7-1.md 2 章。scripts/build_legal_actions_api_design.py の DISCLOSURE が同じ一覧を持ち、--check が照らす）。
# 山札をさがす決定・見た手札の決定は、始まった検索・見たカードの本人の選択肢として実際のカードを示してよい（契約の例外）
DISCLOSURE_CONFIRMED_KINDS = frozenset({
    # カードでない値（選べるものが公開の数・位置・場のポケモン・決まった語彙だけから決まる）
    "accept_request", "allocate_damage", "damage_option", "damage_step_order", "entry_power", "esp_redo", "evolution_heal", "heal_allocation", "janken_hand",
    "knock_out_power", "optional_coin", "optional_discard_all", "optional_drain", "optional_heal", "optional_shuffle", "peek_card", "prize_first", "promote_active",
    "quiz_answer", "quiz_attack", "quiz_height_answer", "reaction_order", "reaction_power", "remove_counters", "select_counter_count", "select_devolve_count",
    "select_draw_count", "select_hand_card", "select_look_count", "select_opponent_attack", "select_prize_card", "stadium_return_bench", "take_prize",
    # カード（選べるものが本人の手札・トラッシュ・場のカードだけから決まる）
    "deck_top_from_hand", "discard_from_hand", "discard_stadium", "discard_to_deck_top", "hand_to_active", "hand_to_deck", "swap_with_prize",
    "energy_drain_discard", "exp_all_energy", "magma_pool_energy",
}) | DECK_REVEALING_KINDS | LOOKED_HAND_KINDS

# 完全性（その応答の scope に明示した操作の種類の範囲だけ。全コマンドの合法手ではない）
COMPLETE = "complete"
PARTIAL = "partial"
UNDETERMINED = "undetermined"

# 操作主体から見た状況
ACTOR_TO_ACT = "actor_to_act"  # 本人が操作する（U7-1 が対応しない種類だけのこともある。coverage を見る）
WAITING_FOR_PLAYER = "waiting_for_player"  # 相手（または両方の準備のうちの相手）の操作を待つ
WAITING_FOR_HOST = "waiting_for_host"  # ホストの操作（ジャンケンの結果・延長戦の開始）を待つ。ホストの操作の入口は U7-2
GAME_OVER = "game_over"
HALTED = "halted"

# 候補がないときの理由（対応の範囲の外か、範囲の中で本当にないか）
EMPTY_NOT_ACTOR = "not_actor"  # 本人が操作する場面でない（ゲーム上の理由。範囲の中で候補がない）
EMPTY_HOST_OPERATION = "host_operation"  # ホストの操作の待ち（本人の操作はない）
EMPTY_GAME_ENDED = "game_ended"  # 終局・停止（どの操作も受け付けない）
EMPTY_NOT_COVERED = "kinds_not_covered"  # 本人が操作できる種類があるが、U7-1 が対応しない（ゲーム上できないのではない）

# 候補の種類（U7-1 が対応するもの）と、段階ごとの種類（仕様案の OPERATIONS と同じ名前）
KIND_TAKE_PRIZE = "take_prize"
KIND_PROMOTE_ACTIVE = "promote_active"
KIND_ANSWER_DECISION = "answer_decision"
KIND_END_TURN = "end_turn"
IMPLEMENTED_KINDS = (KIND_TAKE_PRIZE, KIND_PROMOTE_ACTIVE, KIND_ANSWER_DECISION, KIND_END_TURN)
MAIN_KINDS = ("end_turn", "play_basic", "attach_energy", "evolve", "retreat", "use_attack", "play_trainer", "use_power", "use_stadium", "remove_disguise",
              "discard_from_play", "reveal_face_down", "check_face_up_deck")
_DECISION_KIND = {Phase.TAKE_PRIZE: KIND_TAKE_PRIZE, Phase.PROMOTE_ACTIVE: KIND_PROMOTE_ACTIVE, Phase.DECISION: KIND_ANSWER_DECISION}

# 入力の種類
INPUT_CHOOSE_OPTION = "choose_option"
INPUT_CHOOSE_VALUE = "choose_value"

# ホストの段の拒否・入力を返さない理由（エンジンに渡す前。決まった文。入力の値を文に入れない）
CANDIDATES_STALE = "CANDIDATES_STALE"
CANDIDATES_WRONG_GAME = "CANDIDATES_WRONG_GAME"
CANDIDATES_WRONG_ACTOR = "CANDIDATES_WRONG_ACTOR"
CANDIDATE_UNKNOWN = "CANDIDATE_UNKNOWN"
CANDIDATE_INPUT_INVALID = "CANDIDATE_INPUT_INVALID"
CANDIDATE_NOT_EXECUTABLE = "CANDIDATE_NOT_EXECUTABLE"
INPUT_BOUNDARY_UNCONFIRMED = "INPUT_BOUNDARY_UNCONFIRMED"
REFUSAL_MESSAGES = {
    CANDIDATES_STALE: "候補を作った時点から対戦の状態が変わったか、取っ手が失効した。候補を取り直す",
    CANDIDATES_WRONG_GAME: "別の対戦（または前の世代のホスト）の取っ手。この対戦の候補を取る",
    CANDIDATES_WRONG_ACTOR: "別の操作主体の取っ手。自分の候補を取る",
    CANDIDATE_UNKNOWN: "この取っ手の候補にない。候補を取り直す",
    CANDIDATE_INPUT_INVALID: "入力が候補の制約に合わない（選ぶものの番号・数・重なり・値の範囲）",
    CANDIDATE_NOT_EXECUTABLE: "選んだものは、今の規約集合と実装では処理できない（ゲーム上の禁止ではない）",
    INPUT_BOUNDARY_UNCONFIRMED: "情報境界が未確認のため、この入力取得は未対応（ゲーム上の禁止・未裁定ではない）",
}

# 取っ手の保持の上限（操作主体ごと）。受理・ホストの差し替えで全部、上限を超えたら古い順に失効する
MAX_REVISIONS_PER_ACTOR = 4
_TOKEN_BYTES = 16

# 保証の範囲（候補ごとに返す。どこまで保証しないかを明示する）
GUARANTEE_ANSWER = {
    "preconditions": "決定の番・決める人・選ぶ数・重なり・選べるもの・選ぶと止めるもの（check_choices と同じ公開の制約）を、入力の検査で確かめる",
    "acceptance": "保証しない（最終の判定は apply_command）",
    "after_acceptance": "評価していない（効果の続きで、決定待ち・停止・未裁定や未対応による拒否がありうる）",
}
GUARANTEE_END_TURN = {
    "preconditions": "番のプレイヤーの main の段階（require_turn と同じ公開の条件）だけを確かめた",
    "acceptance": "保証しない（最終の判定は apply_command）",
    "after_acceptance": "評価していない（ポケモンチェックで、決定待ち・停止・未裁定や未対応による拒否がありうる。先読みしない）",
}


def _copy(value):
    """クライアントに返す値の写し（JSON にできる値だけ。内部の記録と共有しない）。"""
    return json.loads(json.dumps(value, ensure_ascii=False))


@dataclass(frozen=True)
class Refusal:
    """ホストの段の拒否（エンジンに渡していない。状態は変わらない）。"""

    code: str
    message: str


@dataclass(frozen=True)
class ActionResult:
    """クライアントに返す送信の結果。``view`` は U2 の ``CommandResult.view_for(本人)``（凍結した値）。状態・コマンド・検証者用の値を持たない。"""

    outcome: str  # accepted・rejected・failed（エンジンの結果）か refused（ホストの段の拒否）
    refusal: Refusal | None
    view: D.ActorDiagnostic | None


REFUSED = "refused"


@dataclass
class _Candidate:
    id: str
    kind: str
    public: dict[str, Any]
    inputs: list[dict[str, Any]]
    disclosure: str = DISCLOSURE_NONE
    decision_id: int | None = None
    values: tuple[int, ...] = ()
    executable: tuple[bool, ...] = ()
    value_bounds: tuple[int, int] | None = None
    min_choices: int = 0
    max_choices: int = 0

    def blocked(self) -> bool:
        return self.public.get("processability") not in EXECUTABLE

    def option_index(self, choice) -> int | None:
        """選ぶものの番号（o1, o2, …）から決定の選べるものの位置。知らない番号は None。"""
        names = {f"o{i + 1}": i for i in range(len(self.values))}
        return names.get(choice) if type(choice) is str else None


@dataclass
class _Issued:
    actor: int
    state: GameState  # 候補を作った状態（同じオブジェクトかで比べる。値・ハッシュで比べない。所有権の契約は ActionHost の説明）
    candidates: dict[str, _Candidate]


def _refused(code: str) -> ActionResult:
    return ActionResult(REFUSED, Refusal(code, REFUSAL_MESSAGES[code]), None)


def _refusal(code: str) -> dict[str, str]:
    return {"code": code, "message": REFUSAL_MESSAGES[code]}


def _check_actor(actor) -> int:
    if isinstance(actor, bool) or actor not in (0, 1):
        raise ValueError("操作主体はプレイヤー 0 か 1（観戦者・ホストの操作の入口は U7-1 にない）")
    return actor


class ActionHost:
    """信頼されたホストの入口。認証・権限の確かめはホストの責任で、ここは確かめ終わった操作主体を受け取る（``session``）。

    状態の所有権（取っ手の対応の前提）:

    - 取っ手は、候補を作った状態のオブジェクトと今の状態が同じオブジェクトかで対応を確かめる。包んだ対戦は受理で状態を新しいオブジェクトに置きかえ、拒否では同じ
      オブジェクトを持つ（U2 の ``HostedGame`` の約束）。**同じオブジェクトを直接変えた場合は検出できない**（重い全体の照合・状態のハッシュは使わない）
    - ``start``・``from_state`` は、ホストの外から別名で参照されない対戦を作る（``from_state`` は渡した状態を複製する）。``ActionHost(game)`` に渡した対戦・状態の別名を
      ホストが持ち続けて直接変えたり、包んだ対戦へ別の経路で操作を送ったりするのは、取っ手の管理の保証の外（受理による状態の置きかえだけは検出する）
    - 正式な差し替え・復元は ``replace_game``（新しい世代。取っ手をすべて失効）を通す
    - ``game``（状態を持つ）はホストの中だけで使う。クライアント用ではない。Python の型だけでは、渡したオブジェクトからの別名の参照を完全には防げない
    """

    def __init__(self, game, *, on_result=None):
        self._game = game
        self._game_id = secrets.token_hex(_TOKEN_BYTES)
        self._issued: dict[str, _Issued] = {}
        self._order: dict[int, deque[str]] = {0: deque(), 1: deque()}
        self._on_result = on_result

    @classmethod
    def start(cls, deck0, deck1, seed, *, on_result=None, **options) -> tuple[ActionHost | None, CommandResult]:
        """``adapter.start_game`` で対戦を始め、``HostedGame`` で包む（状態はこのホストだけが持つ）。開始が拒否・処理できなければ (None, 結果)。"""
        from .adapter import start_game

        result = start_game(deck0, deck1, seed, **options)
        if result.outcome != D.ACCEPTED:
            return None, result
        return cls(HostedGame(result.state), on_result=on_result), result

    @classmethod
    def from_state(cls, state: GameState, *, on_result=None) -> ActionHost:
        """状態の複製を ``HostedGame`` で包む（渡した状態を、あとから変えてもホストの対戦に影響しない）。"""
        return cls(HostedGame(state.clone()), on_result=on_result)

    @property
    def game(self):
        """ホストの中だけで使う対戦（状態を持つ）。クライアントに渡さない。直接の変更・別の経路の操作は取っ手の管理の保証の外。"""
        return self._game

    def replace_game(self, game) -> None:
        """包む対戦を差し替える（再起動・復元・状態の差し替え）。新しい世代の取っ手にし、前の取っ手をすべて失効させる。"""
        self._game = game
        self._game_id = secrets.token_hex(_TOKEN_BYTES)
        self.invalidate()

    def invalidate(self) -> None:
        """発行したすべての取っ手を失効させる。"""
        self._issued.clear()
        for order in self._order.values():
            order.clear()

    def session(self, actor) -> ActorSession:
        """ホストが認証した操作主体（0・1）のクライアント向けの入口。観戦者・相手に本人の入口を渡さないのはホストの責任。"""
        return ActorSession(_SessionLink(self), _check_actor(actor))

    def issued_count(self) -> int:
        """今保持している取っ手の数（上限の確かめ用）。"""
        self._purge()
        return len(self._issued)

    # ---------------------------------------------------------------- 内部

    def _state(self) -> GameState:
        if self._game.failure is not None:
            raise HostStoppedError("処理できない結果のあとの対戦には、候補を出さない（検証者が調べる）")
        return self._game.state

    def _purge(self) -> None:
        current = self._game.state
        for token in [t for t, item in self._issued.items() if item.state is not current]:
            self._drop(token)

    def _drop(self, token: str) -> None:
        item = self._issued.pop(token, None)
        if item is not None:
            self._order[item.actor].remove(token)

    def _issue(self, actor: int, state: GameState, candidates: list[_Candidate]) -> str:
        self._purge()
        token = secrets.token_hex(_TOKEN_BYTES)
        self._issued[token] = _Issued(actor, state, {c.id: c for c in candidates})
        order = self._order[actor]
        order.append(token)
        while len(order) > MAX_REVISIONS_PER_ACTOR:
            self._issued.pop(order.popleft(), None)
        return token

    def _lookup(self, actor: int, game, revision, candidate) -> tuple[_Candidate | None, str | None]:
        if not isinstance(game, str) or game != self._game_id:
            return None, CANDIDATES_WRONG_GAME
        item = self._issued.get(revision) if isinstance(revision, str) else None
        if item is None:
            return None, CANDIDATES_STALE
        if item.actor != actor:
            return None, CANDIDATES_WRONG_ACTOR
        if item.state is not self._state():
            self._purge()
            return None, CANDIDATES_STALE
        found = item.candidates.get(candidate) if isinstance(candidate, str) else None
        if found is None:
            return None, CANDIDATE_UNKNOWN
        return found, None


class _SessionLink:
    """``ActorSession`` がホストの内部を呼ぶ窓口（クライアントに ``ActionHost``・対戦・状態を属性として渡さない）。"""

    __slots__ = ("_candidates", "_check", "_inputs", "_submit")

    def __init__(self, host: ActionHost):
        self._candidates = lambda actor: _candidates(host, actor)
        self._inputs = lambda actor, *args: _inputs(host, actor, *args)
        self._check = lambda actor, *args: _check(host, actor, *args)
        self._submit = lambda actor, *args, **kw: _submit(host, actor, *args, **kw)


class ActorSession:
    """クライアント向けの入口（操作主体はホストが結びつけた値に固定）。返す値は JSON にできる dict の写しと ``ActionResult`` だけ。"""

    __slots__ = ("_actor", "_link")

    def __init__(self, link: _SessionLink, actor: int):
        self._link = link
        self._actor = actor

    @property
    def actor(self) -> int:
        return self._actor

    def candidates(self) -> dict[str, Any]:
        """今の状態での本人の操作候補（状態・乱数・ログを変えない。決定を作らない・答えない）。"""
        return self._link._candidates(self._actor)

    def inputs(self, game, revision, candidate) -> dict[str, Any]:
        """候補に必要な入力（段ごとの種類・制約・選べるもの）。取っ手が合わなければ ``refusal``、情報境界が未確認なら ``withheld`` だけ（数・並びも返さない）。"""
        return self._link._inputs(self._actor, game, revision, candidate)

    def check(self, game, revision, candidate, choices=()) -> dict[str, Any]:
        """入力の検査（候補の制約だけ。送らない）。合えば ``valid`` 真。受理の保証ではない。"""
        return self._link._check(self._actor, game, revision, candidate, choices)

    def submit(self, game, revision, candidate, choices=(), *, operation_id: str | None = None) -> ActionResult:
        """候補と入力からコマンドを作り、包んだ対戦の ``submit`` に送る（送り手は本人）。最終の判定は apply_command。"""
        return self._link._submit(self._actor, game, revision, candidate, choices, operation_id=operation_id)


def _candidates(host: ActionHost, actor: int) -> dict[str, Any]:
    state = host._state()
    situation, candidates, offered, not_covered, completeness, empty = _build(state, actor)
    token = host._issue(actor, state, candidates)
    withheld = [c.id for c in candidates if c.disclosure == DISCLOSURE_UNCONFIRMED]
    return _copy({
        FORMAT_KEY: FORMAT,
        "game": host._game_id,
        "actor": actor,
        "revision": token,
        "status": D.status_of(state),
        "situation": situation,
        "empty_reason": None if candidates else empty,
        "coverage": {"implemented_kinds": list(IMPLEMENTED_KINDS), "scope_kinds": offered + not_covered, "offered_kinds": offered,
                     "not_covered_kinds": not_covered, "withheld_input_candidates": withheld, "completeness": completeness,
                     "completeness_scope": "scope_kinds（この応答に明示した種類だけ。全コマンドの合法手ではない）"},
        "candidates": [{"id": c.id, "kind": c.kind, **c.public, "input_disclosure": c.disclosure,
                        "input_stages": [{"stage": s["stage"], "input": s["input"]} for s in c.inputs]} for c in candidates],
    })


def _inputs(host: ActionHost, actor: int, game, revision, candidate) -> dict[str, Any]:
    found, code = host._lookup(actor, game, revision, candidate)
    if code is not None:
        return {"refusal": _refusal(code)}
    if found.disclosure == DISCLOSURE_UNCONFIRMED:
        return _copy({"candidate": found.id, "kind": found.kind, "withheld": _refusal(INPUT_BOUNDARY_UNCONFIRMED), "stages": []})
    return _copy({"candidate": found.id, "kind": found.kind, "stages": found.inputs})


def _check(host: ActionHost, actor: int, game, revision, candidate, choices) -> dict[str, Any]:
    found, code = host._lookup(actor, game, revision, candidate)
    if code is None:
        code = _input_problem(found, choices)[0]
    return {"valid": code is None, "refusal": None if code is None else _refusal(code)}


def _submit(host: ActionHost, actor: int, game, revision, candidate, choices, *, operation_id=None) -> ActionResult:
    found, code = host._lookup(actor, game, revision, candidate)
    if code is not None:
        return _refused(code)
    code, values = _input_problem(found, choices)
    if code is not None:
        return _refused(code)
    command = EndTurn(actor) if found.kind == KIND_END_TURN else ResolveDecision(actor, found.decision_id, values)
    result = host._game.submit(command, submitter=actor, operation_id=operation_id)
    if result.outcome == D.ACCEPTED:
        host.invalidate()  # 受理: その対戦の取っ手をすべて失効させる（拒否では変えない）
    if host._on_result is not None:
        host._on_result(actor, result)
    return ActionResult(result.outcome, None, result.view_for(actor))


# ---------------------------------------------------------------- 候補の作成（観測と公開の状態だけを読む）


def _build(state: GameState, actor: int):
    """(状況, 候補, 出した種類, 対応しない種類, 完全性, 候補がないときの理由)。決定待ちは、段階より先に、決定の回答者で決める。"""
    status = D.status_of(state)
    if status == D.HALTED:
        return HALTED, [], [], [], COMPLETE, EMPTY_GAME_ENDED
    if status == D.GAME_OVER:
        return GAME_OVER, [], [], [], COMPLETE, EMPTY_GAME_ENDED
    if status == D.AWAITING_DECISION and state.decision is not None:
        # 番・段階によらず、決定の回答者だけが答える（相手の番の決定・相手の操作への反応の決定を含む）
        if state.decision.player != actor:
            return WAITING_FOR_PLAYER, [], [], [], COMPLETE, EMPTY_NOT_ACTOR
        candidate = _answer_candidate(state)
        return ACTOR_TO_ACT, [candidate], [candidate.kind], [], COMPLETE, None
    if status == D.SUDDEN_DEATH_PENDING or state.phase == Phase.SETUP_FIRST_PLAYER:
        return WAITING_FOR_HOST, [], [], [], COMPLETE, EMPTY_HOST_OPERATION
    if state.phase == Phase.SETUP_PLACEMENT:
        if state.players[actor].placed_starting_pokemon:
            return WAITING_FOR_PLAYER, [], [], [], COMPLETE, EMPTY_NOT_ACTOR
        return ACTOR_TO_ACT, [], [], ["place_starting"], PARTIAL, EMPTY_NOT_COVERED
    if state.phase == Phase.SETUP_MULLIGAN_DRAW:
        if not state.players[actor].mulligan_draws_remaining:
            return WAITING_FOR_PLAYER, [], [], [], COMPLETE, EMPTY_NOT_ACTOR
        return ACTOR_TO_ACT, [], [], ["mulligan_draw"], PARTIAL, EMPTY_NOT_COVERED
    if state.phase == Phase.MAIN:
        if state.current_player != actor:
            return WAITING_FOR_PLAYER, [], [], [], COMPLETE, EMPTY_NOT_ACTOR
        public = {"processability": MAY_STOP_LATER, "reasons": ["checkup_not_evaluated"], "guarantees": dict(GUARANTEE_END_TURN)}
        if not D.state_usable(state):
            public = {"processability": NOT_IMPLEMENTED, "reasons": ["state_not_supported"], "guarantees": dict(GUARANTEE_END_TURN)}
        candidate = _Candidate("c1", KIND_END_TURN, public, [])
        return ACTOR_TO_ACT, [candidate], [KIND_END_TURN], [k for k in MAIN_KINDS if k != KIND_END_TURN], PARTIAL, None
    return WAITING_FOR_PLAYER, [], [], [], UNDETERMINED, None  # 知らない段階（状態の区分と段階の組が上のどれでもない）は完全と称さない


def _stop_processability(code: str | None) -> str:
    if code is None:
        return RULING_UNRESOLVED  # 停止のコードが書かれていない選ぶと止める選択（check_choices と同じく未裁定として止める）
    entry = D.default_catalog().get(code)
    category = None if entry is None else entry.category
    return {D.RULING_UNRESOLVED: RULING_UNRESOLVED, D.UNSUPPORTED: NOT_IMPLEMENTED, D.TECHNICAL_LIMIT: TECHNICAL_LIMIT}.get(category, UNVERIFIED)


def _withheld(kind: str, d, guarantees) -> _Candidate:
    """情報境界を確かめていない決定: 選べるもの・数・並びを返さない（入力の取得は未対応。ゲーム上の禁止・未裁定ではない）。"""
    public = {"processability": MAY_STOP_LATER, "reasons": ["continuation_not_evaluated", "input_boundary_unconfirmed"], "guarantees": guarantees}
    return _Candidate("c1", kind, public, [], disclosure=DISCLOSURE_UNCONFIRMED, decision_id=d.id)


def _answer_candidate(state: GameState) -> _Candidate:
    d = state.decision
    actor = d.player
    kind = _DECISION_KIND[state.phase]
    guarantees = dict(GUARANTEE_ANSWER)
    if not D.state_usable(state) or d.kind not in OPTION_MEANINGS:
        # この版が続けられない決定（再開先・規約集合）・選べるものの意味が決まっていない種類: 候補から消さず、未対応として示す（入力は返さない）
        return _Candidate("c1", kind, {"processability": NOT_IMPLEMENTED, "reasons": ["decision_not_supported"], "guarantees": guarantees}, [],
                          disclosure=DISCLOSURE_UNCONFIRMED, decision_id=d.id)
    if d.kind not in DISCLOSURE_CONFIRMED_KINDS:
        return _withheld(kind, d, guarantees)
    view = observe(state, actor)["decision"]
    bounds = value_range(d)
    if bounds is not None:
        stage = {"stage": 1, "input": INPUT_CHOOSE_VALUE, "decision_kind": d.kind, "meaning": view.get("meaning"), "range": dict(view["value_range"]),
                 "count": {"min": 1, "max": 1}, "order": ORDER_NOT_APPLICABLE}
        if "name" in view:
            stage["name"] = view["name"]
        public = {"processability": MAY_STOP_LATER, "reasons": ["continuation_not_evaluated"], "guarantees": guarantees}
        return _Candidate("c1", kind, public, [stage], disclosure=DISCLOSURE_CONFIRMED, decision_id=d.id, value_bounds=bounds, min_choices=1, max_choices=1)
    meaning = view["meaning"]
    if meaning == "card" and any("card_id" not in shown for shown in view["options"]):
        return _withheld(kind, d, guarantees)  # 実行時の確かめ: 決める人に見えないカードが選べるものにある（uid だけを伏せて数を返すことはしない）
    unresolved = set(d.context_value("unresolved_choices", ()))
    detail = {item[0]: item for item in d.context_value("unresolved_detail", ())}
    default_code = d.context_value("unresolved_code")
    options, executable = [], []
    for index, (value, shown) in enumerate(zip(d.options, view["options"])):
        option = {"id": f"o{index + 1}"}
        if meaning == "card":
            option["card"] = value  # 決める人に見えるカード（観測が card_id を渡す）の uid
        else:
            option["value"] = value
        option.update({k: v for k, v in shown.items() if k != "value"})
        processability = MAY_STOP_LATER
        if value in detail:
            processability = _stop_processability(detail[value][1])
        elif value in unresolved:
            processability = _stop_processability(default_code)
        option["processability"] = processability
        options.append(option)
        executable.append(processability in EXECUTABLE)
    if d.max_choices <= 1:
        order = ORDER_NOT_APPLICABLE
    else:
        order = ORDER_SIGNIFICANT if d.kind in ORDER_SIGNIFICANT_KINDS else ORDER_UNCONFIRMED
    stage = {"stage": 1, "input": INPUT_CHOOSE_OPTION, "decision_kind": d.kind, "meaning": meaning, "count": {"min": d.min_choices, "max": d.max_choices},
             "distinct": True, "order": order, "order_preserved": True, "decline": d.min_choices == 0, "options": options}
    public = {"processability": MAY_STOP_LATER, "reasons": ["continuation_not_evaluated"], "guarantees": guarantees}
    return _Candidate("c1", kind, public, [stage], disclosure=DISCLOSURE_CONFIRMED, decision_id=d.id, values=tuple(d.options),
                      executable=tuple(executable), min_choices=d.min_choices, max_choices=d.max_choices)


def _input_problem(found: _Candidate, choices) -> tuple[str | None, tuple[int, ...]]:
    """入力が候補の制約に合うか（公開の制約だけ。並びは変えない）。合えば (None, 決定の選択)。"""
    if not isinstance(choices, (tuple, list)):
        return CANDIDATE_INPUT_INVALID, ()
    choices = tuple(choices)
    if found.kind == KIND_END_TURN:
        return (None, ()) if not choices else (CANDIDATE_INPUT_INVALID, ())
    if found.blocked():
        return CANDIDATE_NOT_EXECUTABLE, ()
    if found.disclosure == DISCLOSURE_UNCONFIRMED:
        return INPUT_BOUNDARY_UNCONFIRMED, ()
    if found.value_bounds is not None:
        if len(choices) != 1 or type(choices[0]) is not int or not found.value_bounds[0] <= choices[0] <= found.value_bounds[1]:
            return CANDIDATE_INPUT_INVALID, ()
        return None, choices
    indexes = [found.option_index(choice) for choice in choices]  # 並びは送られた順のまま（集合にしない）
    if None in indexes or len(set(indexes)) != len(indexes) or not found.min_choices <= len(indexes) <= found.max_choices:
        return CANDIDATE_INPUT_INVALID, ()  # 重なりは check_choices と同じく不正（DUPLICATE_CHOICE と同じ契約）
    if not all(found.executable[i] for i in indexes):
        return CANDIDATE_NOT_EXECUTABLE, ()
    return None, tuple(found.values[i] for i in indexes)
