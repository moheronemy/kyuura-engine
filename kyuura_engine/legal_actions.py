"""合法手 API の最小の実装（U7-1。docs/legal-actions-u7-1.md。仕様案 docs/legal-actions-api-design.md）。

対象は決定への回答（サイドを取る・バトル場に出す・ほかの決定）と「番を終える」（U7-1）、対戦の準備（初期配置・切り直しの補償の引く枚数）と、ホストの操作（ジャンケンの結果・
延長戦の開始。U7-2。docs/legal-actions-u7-2.md）。ほかの操作の種類（番の通常の操作）は候補に出さず、対応していない種類として示す（ゲーム上できないこととは別）。

境界:

- ``ActionHost``（信頼されたホストの入口）: ホストが持つ対戦（``adapter.HostedGame`` と同じ形の対戦。``HostedGame``・``snapshot.RestoredGame``・``view_record.ViewHost``）を包み、
  認証した操作主体（0・1）に ``ActorSession`` を渡す。操作の実行は包んだ対戦の ``submit``（U2 の ``CommandResult``）だけで、別の実行器を作らない
- ``HostSession``（U7-2。信頼されたアプリケーションだけが持つホストの操作の入口）: ``ActionHost.host_session`` だけが作る。プレイヤーの入口から移れない
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
from .commands import (
    DrawMulliganCards,
    EndTurn,
    PlaceStartingPokemon,
    ReportJankenResult,
    ResolveDecision,
    StartSuddenDeath,
)
from .conventions import continuation_for
from .decisions import ARRANGE_DECK_TOP, value_range
from .effects import PLAY_AS_POKEMON_SETUP_CODE, play_as_pokemon_in_hand
from .engine import SETUP_PLACEMENT_CASE
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
ORDER_SIGNIFICANT = "significant"  # 答えの並びが結果（ゾーンの並び・ログ・解決の順）に入る（確かめた種類）
ORDER_NOT_SIGNIFICANT = "not_significant"  # 適用の前に決まった並び（場・トラッシュ・手札の並び）に直す（確かめた種類）
ORDER_NOT_APPLICABLE = "not_applicable"  # 選ぶ数が 1 以下（並びがない）
ORDER_UNCONFIRMED = "unconfirmed"  # 確かめていない（U7 は並びをそのまま送る）
# 答えの並びを確かめた種類（docs/legal-actions-decision-audit.md 3 章。scripts/build_legal_actions_api_design.py の ORDER と --check が照らす）。どれも U7 は並びを変えずに送る
ORDER_SIGNIFICANT_KINDS = frozenset({ARRANGE_DECK_TOP, "bench_guard", "discard_energy", "move_energy", "recover_energy", "return_energy", "select_pokemon"})
ORDER_NOT_SIGNIFICANT_KINDS = frozenset({"attach_from_discard", "attach_from_hand", "discard_opponent_energy", "discard_to_deck", "recover_pokemon", "recover_trainer",
                                         "retrieve_energy", "select_hand_positions"})

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
    # v0.162 の監査（docs/legal-actions-decision-audit.md。生成箇所ごとに選べるもの・選ぶと止める選択・選ぶ数の式の情報源をたどった）
    "attach_from_discard", "attach_from_hand", "attach_to_bench", "bench_from_discard", "bench_guard", "damage_reduction", "discard_energy", "discard_opponent_energy",
    "discard_to_deck", "evolution_song_pokemon", "forced_switch", "ko_prevention", "move_energy", "move_opponent_energy", "ninja_trick", "post_knockout_power",
    "quiz_card", "reaction_switch", "recover_energy", "recover_pokemon", "recover_trainer", "retrieve_energy", "return_energy", "return_to_deck", "revive_source",
    "secret_plan_card", "select_attached_special_energy", "select_attached_trainer", "select_attack", "select_color", "select_deck_owner", "select_evolution_card",
    "select_hand_positions", "select_marker_count", "select_opponent_prize", "select_pokemon", "select_special_condition", "stadium_from_discard", "use_discard_trainer",
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
EMPTY_NOT_COVERED = "kinds_not_covered"  # 本人が操作できる種類があるが、U7 が対応しない（ゲーム上できないのではない）
EMPTY_PLAYERS_TO_ACT = "players_to_act"  # ホストの入口で: プレイヤーの操作の待ち（ホストの操作はない）

# 候補の種類（U7-1 が対応するもの）と、段階ごとの種類（仕様案の OPERATIONS と同じ名前）
KIND_TAKE_PRIZE = "take_prize"
KIND_PROMOTE_ACTIVE = "promote_active"
KIND_ANSWER_DECISION = "answer_decision"
KIND_END_TURN = "end_turn"
KIND_PLACE_STARTING = "place_starting"  # U7-2: 本人の初期配置（PlaceStartingPokemon）
KIND_MULLIGAN_DRAW = "mulligan_draw"  # U7-2: 本人の切り直しの補償の引く枚数（DrawMulliganCards）
KIND_REPORT_JANKEN = "report_janken"  # U7-2: ホストの操作。ジャンケンの勝者（先攻）を伝える（ReportJankenResult。エンジンは乱数で決めない）
KIND_START_SUDDEN_DEATH = "start_sudden_death"  # U7-2: ホストの操作。延長戦を始める（StartSuddenDeath。player を持たない）
PLAYER_KINDS = (KIND_TAKE_PRIZE, KIND_PROMOTE_ACTIVE, KIND_ANSWER_DECISION, KIND_END_TURN, KIND_PLACE_STARTING, KIND_MULLIGAN_DRAW)
HOST_KINDS = (KIND_REPORT_JANKEN, KIND_START_SUDDEN_DEATH)
IMPLEMENTED_KINDS = PLAYER_KINDS + HOST_KINDS
HOST = "host"  # ホストの入口の操作主体（プレイヤーの番号ではない）
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

# 初期配置の選べるものの区分（U7-2）
PLACEMENT_ELIGIBLE = "eligible"  # たねポケモン・ベイビィポケモンのカード（バトル場・ベンチに出せる）
PLACEMENT_EXCLUDED_BY_CONVENTION = "excluded_by_convention"  # 化石・人形を、状態の規約集合の続行規約がたねポケモンとして数えない（規約による拒否。ゲーム上の未裁定ではない）
PLACEMENT_STOP = "stops"  # 化石・人形で、続行規約がない（選ぶと止める。処理可能性は診断のコード表の分類）

# 保証の範囲（候補ごとに返す。どこまで保証しないかを明示する）
GUARANTEE_ANSWER = {
    "preconditions": "決定の番・決める人・選ぶ数・重なり・選べるもの・選ぶと止めるもの（check_choices と同じ公開の制約）を、入力の検査で確かめる",
    "acceptance": "保証しない（最終の判定は apply_command）",
    "after_acceptance": "評価していない（効果の続きで、決定待ち・停止・未裁定や未対応による拒否がありうる）",
}
GUARANTEE_PLACEMENT = {
    "preconditions": "準備の段階・まだ置いていないこと・手札にあること・重なり・ベンチの上限・たねポケモン／ベイビィであること・化石と人形の扱い（_place_starting_pokemon と同じ述語と規約の照会）を、入力の検査で確かめる",
    "acceptance": "入力の検査に合えば、エンジンの受理の条件を満たす（最終の判定は apply_command）",
    "after_acceptance": "両方が置いたら、サイドを置いて切り直しの補償か先攻を決める段階に進む（止まる処理はない）",
}
GUARANTEE_MULLIGAN = {
    "preconditions": "補償の段階・本人に補償が残ること・引く枚数（0〜1 回の上限・山札の枚数まで。_draw_mulligan_cards と同じ値）を、入力の検査で確かめる",
    "acceptance": "入力の検査に合えば、エンジンの受理の条件を満たす（最終の判定は apply_command）",
    "after_acceptance": "1 回ぶんを引く。補償がなくなれば先攻を決める段階に進む（止まる処理はない）",
}
GUARANTEE_JANKEN = {
    "preconditions": "先攻を決める段階（_report_janken_result と同じ条件）と、勝者が 0 か 1 であること",
    "acceptance": "保証しない（最終の判定は apply_command）",
    "after_acceptance": "評価していない（勝者の番が始まる。番の始めの処理で止まる・決定待ちになることがありうる）",
}
GUARANTEE_SUDDEN_DEATH = {
    "preconditions": "サドン・デスに移った状態（status が sudden_death_pending）であること。整合の確かめ（不変条件・最初のデッキの復元）は apply_command が行う",
    "acceptance": "保証しない（整合しない状態は処理できない結果になる）",
    "after_acceptance": "評価していない（延長戦の準備で、切り直しの補償・化石の手札などで止まりうる。乱数は今の状態から続ける）",
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
    bench_max: int = 0  # 初期配置のベンチの上限（U7-2）

    def blocked(self) -> bool:
        return self.public.get("processability") not in EXECUTABLE

    def option_index(self, choice) -> int | None:
        """選ぶものの番号（o1, o2, …）から決定の選べるものの位置。知らない番号は None。"""
        names = {f"o{i + 1}": i for i in range(len(self.values))}
        return names.get(choice) if type(choice) is str else None


@dataclass
class _Issued:
    actor: int | str  # プレイヤー（0・1）か HOST
    state: GameState  # 候補を作った状態（同じオブジェクトかで比べる。値・ハッシュで比べない。所有権の契約は ActionHost の説明）
    candidates: dict[str, _Candidate]


def _refused(code: str) -> ActionResult:
    return ActionResult(REFUSED, Refusal(code, REFUSAL_MESSAGES[code]), None)


def _refusal(code: str) -> dict[str, str]:
    return {"code": code, "message": REFUSAL_MESSAGES[code]}


def _check_actor(actor) -> int:
    if isinstance(actor, bool) or actor not in (0, 1):
        raise ValueError("操作主体はプレイヤー 0 か 1（観戦者の入口はない。ホストの操作は host_session）")
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
        self._order: dict[int | str, deque[str]] = {0: deque(), 1: deque(), HOST: deque()}
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
        actor = _check_actor(actor)
        return ActorSession(_SessionLink(self, actor), actor)

    def host_session(self) -> HostSession:
        """ホストの操作（ジャンケンの結果・延長戦の開始）の入口（U7-2）。信頼されたアプリケーションだけが持つ。クライアントに渡さないこと・この入口を呼べる人の
        権限の確かめは、ホストするアプリケーションの責任。プレイヤーの入口からこの入口へ移る方法はない（主体の値は入口を作ったときの窓口に固定）。"""
        return HostSession(_SessionLink(self, HOST), HOST)

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

    def _issue(self, actor: int | str, state: GameState, candidates: list[_Candidate]) -> str:
        self._purge()
        token = secrets.token_hex(_TOKEN_BYTES)
        self._issued[token] = _Issued(actor, state, {c.id: c for c in candidates})
        order = self._order[actor]
        order.append(token)
        while len(order) > MAX_REVISIONS_PER_ACTOR:
            self._issued.pop(order.popleft(), None)
        return token

    def _lookup(self, actor: int | str, game, revision, candidate) -> tuple[_Candidate | None, str | None]:
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
    """入口がホストの内部を呼ぶ窓口（クライアントに ``ActionHost``・対戦・状態を属性として渡さない）。操作主体は作ったときの値に固定（入口の属性を変えても
    主体は変わらない）。Python の型だけでは、閉包の中の参照までは隠せない（信頼できない利用者のコードと同じプロセスで動かさないのはホストの責任）。"""

    __slots__ = ("_candidates", "_check", "_inputs", "_submit")

    def __init__(self, host: ActionHost, actor: int | str):
        self._candidates = lambda: _candidates(host, actor)
        self._inputs = lambda *args: _inputs(host, actor, *args)
        self._check = lambda *args: _check(host, actor, *args)
        self._submit = lambda *args, **kw: _submit(host, actor, *args, **kw)


class _Session:
    __slots__ = ("_actor", "_link")

    def __init__(self, link: _SessionLink, actor):
        self._link = link
        self._actor = actor  # 表示用（呼び出しには使わない。主体は窓口に固定）

    def candidates(self) -> dict[str, Any]:
        """今の状態での操作候補（状態・乱数・ログを変えない。決定を作らない・答えない）。"""
        return self._link._candidates()

    def inputs(self, game, revision, candidate) -> dict[str, Any]:
        """候補に必要な入力（段ごとの種類・制約・選べるもの）。取っ手が合わなければ ``refusal``、情報境界が未確認なら ``withheld`` だけ（数・並びも返さない）。"""
        return self._link._inputs(game, revision, candidate)

    def check(self, game, revision, candidate, choices=()) -> dict[str, Any]:
        """入力の検査（候補の制約だけ。送らない）。合えば ``valid`` 真。受理の保証ではない。"""
        return self._link._check(game, revision, candidate, choices)

    def submit(self, game, revision, candidate, choices=(), *, operation_id: str | None = None) -> ActionResult:
        """候補と入力からコマンドを作り、包んだ対戦の ``submit`` に送る。最終の判定は apply_command。"""
        return self._link._submit(game, revision, candidate, choices, operation_id=operation_id)


class ActorSession(_Session):
    """クライアント向けの入口（操作主体はホストが結びつけたプレイヤー。送り手は本人）。返す値は JSON にできる dict の写しと ``ActionResult`` だけ。"""

    __slots__ = ()

    @property
    def actor(self) -> int:
        return self._actor


class HostSession(_Session):
    """ホストの操作の入口（U7-2。``ActionHost.host_session`` だけが作る。信頼されたアプリケーションだけが持つ）。プレイヤーの候補・入力は返さない。"""

    __slots__ = ()

    @property
    def actor(self) -> str:
        return HOST


def _candidates(host: ActionHost, actor: int | str) -> dict[str, Any]:
    state = host._state()
    situation, candidates, offered, not_covered, completeness, empty = _build_host(state) if actor == HOST else _build(state, actor)
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


def _inputs(host: ActionHost, actor: int | str, game, revision, candidate) -> dict[str, Any]:
    found, code = host._lookup(actor, game, revision, candidate)
    if code is not None:
        return {"refusal": _refusal(code)}
    if found.disclosure == DISCLOSURE_UNCONFIRMED:
        return _copy({"candidate": found.id, "kind": found.kind, "withheld": _refusal(INPUT_BOUNDARY_UNCONFIRMED), "stages": []})
    return _copy({"candidate": found.id, "kind": found.kind, "stages": found.inputs})


def _check(host: ActionHost, actor: int | str, game, revision, candidate, choices) -> dict[str, Any]:
    found, code = host._lookup(actor, game, revision, candidate)
    if code is None:
        code = _input_problem(found, choices)[0]
    return {"valid": code is None, "refusal": None if code is None else _refusal(code)}


def _command(found: _Candidate, actor, values: tuple[int, ...]):
    """候補と確かめた入力から既存のコマンドを作る（U7 は新しい操作を作らない）。"""
    if found.kind == KIND_END_TURN:
        return EndTurn(actor)
    if found.kind == KIND_PLACE_STARTING:
        return PlaceStartingPokemon(actor, values[0], tuple(values[1:]))  # ベンチは選んだ順（場の並び）
    if found.kind == KIND_MULLIGAN_DRAW:
        return DrawMulliganCards(actor, values[0])
    if found.kind == KIND_REPORT_JANKEN:
        return ReportJankenResult(values[0])
    if found.kind == KIND_START_SUDDEN_DEATH:
        return StartSuddenDeath()
    return ResolveDecision(actor, found.decision_id, values)


def _submit(host: ActionHost, actor: int | str, game, revision, candidate, choices, *, operation_id=None) -> ActionResult:
    found, code = host._lookup(actor, game, revision, candidate)
    if code is not None:
        return _refused(code)
    code, values = _input_problem(found, choices)
    if code is not None:
        return _refused(code)
    is_host = actor == HOST
    result = host._game.submit(_command(found, actor, values), submitter=None if is_host else actor, operation_id=operation_id)
    if result.outcome == D.ACCEPTED:
        host.invalidate()  # 受理: その対戦の取っ手をすべて失効させる（拒否では変えない）
    if host._on_result is not None:
        host._on_result(actor, result)
    # ホストの操作の結果は、全員に見える状態の知らせ（view_for(None)）。CommandResult そのものはホストだけが on_result で受け取る
    return ActionResult(result.outcome, None, result.view_for(None if is_host else actor))


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
        candidate = _placement_candidate(state, actor)
        return ACTOR_TO_ACT, [candidate], [KIND_PLACE_STARTING], [], COMPLETE, None
    if state.phase == Phase.SETUP_MULLIGAN_DRAW:
        if not state.players[actor].mulligan_draws_remaining:
            return WAITING_FOR_PLAYER, [], [], [], COMPLETE, EMPTY_NOT_ACTOR
        candidate = _mulligan_candidate(state, actor)
        return ACTOR_TO_ACT, [candidate], [KIND_MULLIGAN_DRAW], [], COMPLETE, None
    if state.phase == Phase.MAIN:
        if state.current_player != actor:
            return WAITING_FOR_PLAYER, [], [], [], COMPLETE, EMPTY_NOT_ACTOR
        public = {"processability": MAY_STOP_LATER, "reasons": ["checkup_not_evaluated"], "guarantees": dict(GUARANTEE_END_TURN)}
        if not D.state_usable(state):
            public = {"processability": NOT_IMPLEMENTED, "reasons": ["state_not_supported"], "guarantees": dict(GUARANTEE_END_TURN)}
        candidate = _Candidate("c1", KIND_END_TURN, public, [])
        return ACTOR_TO_ACT, [candidate], [KIND_END_TURN], [k for k in MAIN_KINDS if k != KIND_END_TURN], PARTIAL, None
    return WAITING_FOR_PLAYER, [], [], [], UNDETERMINED, None  # 知らない段階（状態の区分と段階の組が上のどれでもない）は完全と称さない


def _build_host(state: GameState):
    """ホストの入口の候補（ジャンケンの結果・延長戦の開始）。プレイヤーの決定・操作はここに出さない。"""
    status = D.status_of(state)
    if status in (D.HALTED, D.GAME_OVER):
        return (HALTED if status == D.HALTED else GAME_OVER), [], [], [], COMPLETE, EMPTY_GAME_ENDED
    if status == D.SUDDEN_DEATH_PENDING:
        public = {"processability": MAY_STOP_LATER, "reasons": ["segment_setup_not_evaluated"], "guarantees": dict(GUARANTEE_SUDDEN_DEATH)}
        return ACTOR_TO_ACT, [_Candidate("c1", KIND_START_SUDDEN_DEATH, public, [])], [KIND_START_SUDDEN_DEATH], [], COMPLETE, None
    if status == D.IN_PROGRESS and state.phase == Phase.SETUP_FIRST_PLAYER and state.decision is None:
        public = {"processability": MAY_STOP_LATER if D.state_usable(state) else NOT_IMPLEMENTED, "reasons": ["turn_start_not_evaluated"],
                  "guarantees": dict(GUARANTEE_JANKEN)}
        stage = {"stage": 1, "input": INPUT_CHOOSE_VALUE, "meaning": "player", "range": {"min": 0, "max": 1}, "count": {"min": 1, "max": 1},
                 "order": ORDER_NOT_APPLICABLE, "note": "エンジンの外で行ったジャンケンの勝者（勝った人が先攻。エンジンは乱数で決めない）"}
        return ACTOR_TO_ACT, [_Candidate("c1", KIND_REPORT_JANKEN, public, [stage], disclosure=DISCLOSURE_CONFIRMED, value_bounds=(0, 1))], \
            [KIND_REPORT_JANKEN], [], COMPLETE, None
    return WAITING_FOR_PLAYER, [], [], [], COMPLETE, EMPTY_PLAYERS_TO_ACT


def _placement_candidate(state: GameState, actor: int) -> _Candidate:
    """本人の初期配置（手札から）。選べるものは本人の手札のたねポケモン・ベイビィポケモンと、化石・人形（候補から消さず区分で示す）。2 段（バトル場 1 枚・ベンチ）。"""
    p = state.players[actor]
    guarantees = dict(GUARANTEE_PLACEMENT)
    if not D.state_usable(state):
        return _Candidate("c1", KIND_PLACE_STARTING, {"processability": NOT_IMPLEMENTED, "reasons": ["state_not_supported"], "guarantees": guarantees}, [],
                          disclosure=DISCLOSURE_UNCONFIRMED)
    fossils = set(play_as_pokemon_in_hand(state, actor))
    lookup = continuation_for(state, PLAY_AS_POKEMON_SETUP_CODE, SETUP_PLACEMENT_CASE) if fossils else None
    options, values, executable = [], [], []
    for uid in p.hand:  # 本人の手札の並び（本人に見える）
        if uid in fossils:
            if lookup is not None:
                option = {"placement": PLACEMENT_EXCLUDED_BY_CONVENTION, "eligible": False, "convention": f"{lookup.convention[0]}@{lookup.convention[1]}"}
            else:
                option = {"placement": PLACEMENT_STOP, "eligible": False, "processability": _stop_processability(PLAY_AS_POKEMON_SETUP_CODE)}
        elif state.card_def(uid).is_baby_or_basic_pokemon:
            option = {"placement": PLACEMENT_ELIGIBLE, "eligible": True, "processability": SUPPORTED}
        else:
            continue
        values.append(uid)
        executable.append(option["eligible"])
        options.append({"id": f"o{len(values)}", "card": uid, "card_id": state.cards[uid].card_id, **option})
    bench_max = state.rules.max_setup_bench
    stages = [{"stage": 1, "input": INPUT_CHOOSE_OPTION, "role": "active", "count": {"min": 1, "max": 1}, "options": options, "order": ORDER_NOT_APPLICABLE},
              {"stage": 2, "input": INPUT_CHOOSE_OPTION, "role": "bench", "count": {"min": 0, "max": bench_max}, "options_from_stage": 1,
               "distinct_across_stages": True, "order": ORDER_SIGNIFICANT, "order_preserved": True, "note": "ベンチは選んだ順に場に並ぶ"}]
    public = {"processability": SUPPORTED if any(executable) else (_stop_processability(PLAY_AS_POKEMON_SETUP_CODE) if fossils and lookup is None else NOT_IMPLEMENTED),
              "reasons": [] if any(executable) else ["no_eligible_card"], "guarantees": guarantees,
              "choices_format": "[バトル場の番号, ベンチの番号, ...]（ベンチは選んだ順）"}
    return _Candidate("c1", KIND_PLACE_STARTING, public, stages, disclosure=DISCLOSURE_CONFIRMED, values=tuple(values), executable=tuple(executable),
                      min_choices=1, max_choices=1 + bench_max, bench_max=bench_max)


def _mulligan_candidate(state: GameState, actor: int) -> _Candidate:
    """本人の切り直しの補償の 1 回ぶんの引く枚数（0〜1 回の上限・山札の枚数まで。数は公開の値）。"""
    p = state.players[actor]
    top = min(state.rules.mulligan_draw_max_per_mulligan, len(p.deck))
    stage = {"stage": 1, "input": INPUT_CHOOSE_VALUE, "meaning": "count", "range": {"min": 0, "max": top}, "count": {"min": 1, "max": 1},
             "order": ORDER_NOT_APPLICABLE, "remaining": p.mulligan_draws_remaining, "decline": True, "note": "相手の切り直し 1 回ぶん。0 枚も選べる"}
    public = {"processability": SUPPORTED if D.state_usable(state) else NOT_IMPLEMENTED, "reasons": [], "guarantees": dict(GUARANTEE_MULLIGAN)}
    return _Candidate("c1", KIND_MULLIGAN_DRAW, public, [stage], disclosure=DISCLOSURE_CONFIRMED, value_bounds=(0, top))


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
        order = (ORDER_SIGNIFICANT if d.kind in ORDER_SIGNIFICANT_KINDS else ORDER_NOT_SIGNIFICANT if d.kind in ORDER_NOT_SIGNIFICANT_KINDS
                 else ORDER_UNCONFIRMED)
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
    if found.kind in (KIND_END_TURN, KIND_START_SUDDEN_DEATH):
        return (None, ()) if not choices else (CANDIDATE_INPUT_INVALID, ())
    if found.blocked():
        return CANDIDATE_NOT_EXECUTABLE, ()
    if found.disclosure == DISCLOSURE_UNCONFIRMED:
        return INPUT_BOUNDARY_UNCONFIRMED, ()
    if found.value_bounds is not None:
        if len(choices) != 1 or type(choices[0]) is not int or not found.value_bounds[0] <= choices[0] <= found.value_bounds[1]:
            return CANDIDATE_INPUT_INVALID, ()
        return None, choices
    if found.kind == KIND_PLACE_STARTING:
        indexes = [found.option_index(choice) for choice in choices]  # 1 つめがバトル場、残りがベンチ（選んだ順）
        if not choices or None in indexes or len(set(indexes)) != len(indexes) or len(indexes) - 1 > found.bench_max:
            return CANDIDATE_INPUT_INVALID, ()  # 重なり（DUPLICATE_CARD）・ベンチの上限（SETUP_BENCH_LIMIT）と同じ契約
        if not all(found.executable[i] for i in indexes):
            return CANDIDATE_NOT_EXECUTABLE, ()  # 化石・人形（続行規約で数えない・止める）。ゲーム上の禁止とは別の理由（選べるものの placement）
        return None, tuple(found.values[i] for i in indexes)
    indexes = [found.option_index(choice) for choice in choices]  # 並びは送られた順のまま（集合にしない）
    if None in indexes or len(set(indexes)) != len(indexes) or not found.min_choices <= len(indexes) <= found.max_choices:
        return CANDIDATE_INPUT_INVALID, ()  # 重なりは check_choices と同じく不正（DUPLICATE_CHOICE と同じ契約）
    if not all(found.executable[i] for i in indexes):
        return CANDIDATE_NOT_EXECUTABLE, ()
    return None, tuple(found.values[i] for i in indexes)
