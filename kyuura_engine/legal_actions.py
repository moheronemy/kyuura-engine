"""合法手 API の最小の実装（U7-1。docs/legal-actions-u7-1.md。仕様案 docs/legal-actions-api-design.md）。

対象は決定への回答（サイドを取る・バトル場に出す・ほかの決定）と「番を終える」（U7-1）、対戦の準備（初期配置・切り直しの補償の引く枚数）と、ホストの操作（ジャンケンの結果・
延長戦の開始。U7-2。docs/legal-actions-u7-2.md）、番の基本の操作（ベンチに出す・エネルギーをつける・進化させる・にげる。U7-3。docs/legal-actions-u7-3.md）、ワザの宣言
（U7-4。docs/legal-actions-u7-4.md）、場のポケモン 1 匹を指す操作（「ばける」でのせたカードをトラッシュする・なにかの化石・ピッピ人形をすてる・うらのカードを
おもてにする。U7-5a・U7-5b。docs/legal-actions-u7-5ab.md）、手札のトレーナー（U7-5c。docs/legal-actions-u7-5c.md）。ほかの操作の種類（特殊能力・スタジアムの効果など）は
候補に出さず、対応していない種類として示す（ゲーム上できないこととは別）。

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
from dataclasses import dataclass, field
from functools import partial
from typing import Any

from . import diagnostics as D
from .adapter import CommandResult, HostedGame, HostStoppedError
from .commands import (
    AttachEnergy,
    DiscardFromPlay,
    DrawMulliganCards,
    EndTurn,
    EvolvePokemon,
    PlaceStartingPokemon,
    PlayBasicToBench,
    PlayTrainer,
    RemoveDisguise,
    ReportJankenResult,
    ResolveDecision,
    Retreat,
    RevealFaceDown,
    StartSuddenDeath,
    UseAttack,
)
from .conventions import continuation_for
from .decisions import ARRANGE_DECK_TOP, value_range
from .effects import (
    PLAY_AS_POKEMON_SETUP_CODE,
    AttackCoinStadium,
    attack_power_slot,
    available_attacks,
    energy_unit_count,
    group_attack_power_slot,
    play_as_pokemon_in_hand,
    powers_of,
    retreat_cost,
    stadium_of,
)
from .engine import (
    SETUP_PLACEMENT_CASE,
    check_attach_energy,
    check_discard_from_play,
    check_evolve,
    check_play_basic,
    check_play_trainer,
    check_remove_disguise,
    check_retreat,
    check_retreat_declaration,
    check_reveal_face_down,
)
from .errors import HiddenPropertyRead, IllegalActionError, UnsupportedError
from .observation import (
    DECK_REVEALING_KINDS,
    LOOKED_HAND_KINDS,
    OPTION_MEANINGS,
    observe,
)
from .resolution.flow import check_use_attack
from .stadiums import bench_limit
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
KIND_PLAY_BASIC = "play_basic"  # U7-3: 手札のたね・ベイビィポケモンのカードをベンチに出す（PlayBasicToBench）
KIND_ATTACH_ENERGY = "attach_energy"  # U7-3: 手札のエネルギーカードを自分の場のポケモンにつける（AttachEnergy。1 枚。カツラの 2 枚目 energy2 は使わない）
KIND_EVOLVE = "evolve"  # U7-3: 手札の進化カード（ベイビィからはたねポケモンのカード）を自分の場のポケモンに重ねる（EvolvePokemon）
KIND_RETREAT = "retreat"  # U7-3: バトル場のポケモンをにがす（Retreat）
TURN_KINDS = (KIND_PLAY_BASIC, KIND_ATTACH_ENERGY, KIND_EVOLVE, KIND_RETREAT)
KIND_USE_ATTACK = "use_attack"  # U7-4: バトル場のポケモンのワザを宣言する（UseAttack。宣言といっしょに選ぶもの: クチバシティジムのコイン・ワザといっしょに使う特殊能力）
KIND_REMOVE_DISGUISE = "remove_disguise"  # U7-5a: 「ばける」でのせた進化カードをトラッシュして元の姿にもどす（RemoveDisguise）
KIND_DISCARD_FROM_PLAY = "discard_from_play"  # U7-5a: 自分の場のなにかの化石・ピッピ人形をすてる（DiscardFromPlay）
KIND_REVEAL_FACE_DOWN = "reveal_face_down"  # U7-5b: 自分の場のうらのカード（マチスの秘策）をおもてにする（RevealFaceDown）
BOARD_KINDS = (KIND_REMOVE_DISGUISE, KIND_DISCARD_FROM_PLAY, KIND_REVEAL_FACE_DOWN)  # 場のポケモン 1 匹を指す操作（MAIN_KINDS の順）
KIND_PLAY_TRAINER = "play_trainer"  # U7-5c: 手札のトレーナーカードを使う（PlayTrainer。宣言の入力は card だけ。対象・枚数などは受理のあとの決定）
PLAYER_KINDS = (KIND_TAKE_PRIZE, KIND_PROMOTE_ACTIVE, KIND_ANSWER_DECISION, KIND_END_TURN, KIND_PLACE_STARTING, KIND_MULLIGAN_DRAW, *TURN_KINDS, KIND_USE_ATTACK,
                *BOARD_KINDS, KIND_PLAY_TRAINER)  # implemented_kinds の並び（実装した順。U7-5c の play_trainer は最後に加えた）
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
    "acceptance": "eligible の選べるものだけで作り、入力の検査に合った入力は、エンジンの受理の条件を満たす（最終の判定は apply_command）。eligible が偽の選べるもの（化石・人形）を含む入力は送れない",
    "after_acceptance": "両方が置いたら、サイドを置いて切り直しの補償か先攻を決める段階に進む（止まる処理はない）",
    "supported_scope": "候補の supported は、eligible の選べるものだけで作った入力の範囲の保証（表示した化石・人形まで実行できるという意味ではない）",
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
GUARANTEE_TURN_ACTION = {
    "preconditions": "番・段階と、選べるもの・組ごとに、エンジンが受け付ける前の確かめ（engine.check_play_basic・check_attach_energy・check_evolve・check_retreat_declaration。コマンドの"
                     "処理と同じ関数・同じ順番）を候補の作成に使う。にげるの入れ替える控えとトラッシュするエネルギーの組は、入力の検査で engine.check_retreat を呼ぶ",
    "acceptance": "eligible の選べるもの（2 段の操作は options_by_choice の eligible の組）だけで作り、入力の検査に合った入力は、エンジンが受け付ける前の確かめを満たす"
                  "（最終の判定は apply_command。うらのカードをおもてにする処理・コマンドの項目の確かめはエンジンの入口）",
    "after_acceptance": "supported は、受理のあとの反応・決定・停止のもと（特殊能力・ついているトレーナー・スタジアム・マーカー・持続する効果・特殊エネルギー・うらのカード・番の効果など）が"
                        "場にないことを公開の情報で確かめた場合だけ。ほかは may_stop_later（受理のあとを評価していない）",
    "supported_scope": "supported は上の条件の範囲の保証で、受理のあとの全分岐の完走の保証ではない（こんらんのコインなど、乱数で決まる続きを含む）",
}
GUARANTEE_ATTACK = {
    "preconditions": "番・段階と、ワザ・宣言といっしょに選ぶものごとに、エンジンが宣言を受け付ける前の確かめ（resolution.flow.check_use_attack。checks.attack_request・要素の並び・"
                     "クチバシティジムのコイン・ワザといっしょに使う特殊能力の確かめ。コマンドの処理と同じ関数・同じ順番）を候補の作成と入力の検査に使う",
    "acceptance": "保証しない。エンジンは宣言の前に先読み（コインの結果・ワザの途中の決定の答えを状態の複製の上で試す）をして、原典で決められない場合・未対応に当たれば宣言を拒否する"
                  "（状態は変わらない）。候補の作成・入力の検査は、この先読みを呼ばない（秘密の山札・サイドの配分・乱数を読まない）。最終の判定は apply_command。うらのカードを"
                  "おもてにする処理・コマンドの項目の確かめはエンジンの入口",
    "after_acceptance": "評価していない（コイン・ワザの途中の決定・きぜつ・サイド・バトル場に出す決定・反応で、決定待ち・停止がありうる。決定は受理のあと answer_decision の候補で答える）",
    "supported_scope": "ワザの候補は supported にしない（宣言の前の先読みと受理のあとを評価していないため）",
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
class HostNotice:
    """ホストの操作の送り手（ホスト）だけへの結果（v0.164）。拒否・処理できない結果の定型の診断を持つ。全員へ配る知らせではない（配る更新は client_api の更新）。"""

    outcome: str
    status: str
    continuable: bool
    next: tuple[D.NextAction, ...]
    diagnostic_id: str | None
    category: str | None
    message: str | None
    halt: D.PublicHalt | None
    operation_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return {"role": "host", "outcome": self.outcome, "status": self.status, "continuable": self.continuable, "next": [a.to_dict() for a in self.next],
                "diagnostic_id": self.diagnostic_id, "category": self.category, "message": self.message,
                "halt": None if self.halt is None else self.halt.to_dict(), "operation_id": self.operation_id}


def _host_notice(result: CommandResult) -> HostNotice:
    d = result.diagnosis
    return HostNotice(outcome=result.outcome, status=result.status, continuable=result.continuable, next=result.next,
                      diagnostic_id=None if d is None else d.diagnostic_id, category=None if d is None else d.category, message=None if d is None else d.message,
                      halt=result.halt, operation_id=result.operation_id)


@dataclass(frozen=True)
class ActionResult:
    """送り手に返す送信の結果（送り手だけへの応答。全員へ配る知らせではない）。``view`` は、プレイヤーなら U2 の ``CommandResult.view_for(本人)``、ホストなら
    ``HostNotice``（v0.164。v0.163 は全員向けの ``view_for(None)`` を返していたので、拒否のときホストが理由を受け取れなかった）。状態・コマンド・検証者用の値を持たない。"""

    outcome: str  # accepted・rejected・failed（エンジンの結果）か refused（ホストの段の拒否）
    refusal: Refusal | None
    view: D.ActorDiagnostic | HostNotice | None


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
    ids: dict[str, tuple[int, int]] = field(default_factory=dict)  # U7-3 の 2 段の操作: 選ぶものの番号 → (段, 値)
    pairs: dict[tuple[str, str], bool] = field(default_factory=dict)  # U7-3 のエネルギー・進化: (1 段目, 2 段目) の組 → 実行できるか（ない組はゲーム上できない）
    verify: Any = None  # U7-3 のにげる: 入力の検査でエンジンの確かめを呼ぶ（候補を作った状態に結びつける。取っ手が同じ状態を確かめてから呼ぶ）

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
    situation, candidates, evaluated, not_covered, completeness, empty = _build_host(state) if actor == HOST else _build(state, actor)
    offered = list(dict.fromkeys(c.kind for c in candidates))  # 候補がある種類（evaluated のうち。ゲーム上できない種類は候補がない）
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
        "coverage": {"implemented_kinds": list(IMPLEMENTED_KINDS), "scope_kinds": _scope_kinds(evaluated + not_covered), "offered_kinds": offered,
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


def _scope_kinds(kinds: list[str]) -> list[str]:
    """応答の範囲の種類。番の操作（MAIN_KINDS）なら MAIN_KINDS の順（U7-4 までと同じ並び。U7-5a・U7-5b で評価する種類が MAIN_KINDS の途中に加わっても変えない）。"""
    if kinds and all(k in MAIN_KINDS for k in kinds):
        return sorted(kinds, key=MAIN_KINDS.index)
    return kinds


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
    if found.kind == KIND_PLAY_BASIC:
        return PlayBasicToBench(actor, values[0])
    if found.kind == KIND_ATTACH_ENERGY:
        return AttachEnergy(actor, values[0], values[1])  # つけるカード, つける場のポケモン（いちばん上のカードの uid）
    if found.kind == KIND_EVOLVE:
        return EvolvePokemon(actor, values[0], values[1])  # 進化カード, 進化させる場のポケモンの番号
    if found.kind == KIND_RETREAT:
        return Retreat(actor, tuple(values[1:]), values[0])  # トラッシュするカード（選んだ順）, 入れ替える控え（いちばん上のカードの uid）
    if found.kind == KIND_USE_ATTACK:
        return _attack_command(actor, values)
    if found.kind in _BOARD_COMMANDS:
        return _BOARD_COMMANDS[found.kind](actor, values[0])  # 場のポケモンの番号（pokemon_id）
    if found.kind == KIND_PLAY_TRAINER:
        return PlayTrainer(actor, values[0])  # 手札のトレーナーカード（uid）
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
    # 送り手だけへの応答（ホストは HostNotice。拒否を全員へ配る知らせにしない）。CommandResult そのものはホストだけが on_result で受け取る
    return ActionResult(result.outcome, None, _host_notice(result) if is_host else result.view_for(actor))


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
        usable = D.state_usable(state)
        if not usable:
            public = {"processability": NOT_IMPLEMENTED, "reasons": ["state_not_supported"], "guarantees": dict(GUARANTEE_END_TURN)}
        candidates = [_Candidate("c1", KIND_END_TURN, public, [])]
        if usable:
            candidates += _turn_candidates(state, actor)
            attack = _attack_candidate(state, actor)
            candidates += [] if attack is None else [attack]
            trainer = _trainer_candidate(state, actor)  # U7-5c: MAIN_KINDS では use_attack と場のポケモン 1 匹を指す操作のあいだ
            candidates += [] if trainer is None else [trainer]
            candidates += _board_candidates(state, actor)
        else:
            candidates += [_Candidate("", kind, {"processability": NOT_IMPLEMENTED, "reasons": ["state_not_supported"],
                                                 "guarantees": dict(_UNUSABLE_GUARANTEES.get(kind, GUARANTEE_TURN_ACTION))}, [],
                                      disclosure=DISCLOSURE_UNCONFIRMED) for kind in (*TURN_KINDS, KIND_USE_ATTACK, KIND_PLAY_TRAINER, *BOARD_KINDS)]
        for number, candidate in enumerate(candidates, 1):
            candidate.id = f"c{number}"  # 種類の並び（MAIN_KINDS の順）。番号は応答ごと（取っ手と組で使う）
        evaluated = [k for k in MAIN_KINDS if k in (KIND_END_TURN, *TURN_KINDS, KIND_USE_ATTACK, KIND_PLAY_TRAINER, *BOARD_KINDS)]  # MAIN_KINDS の順（scope_kinds は MAIN_KINDS のまま）
        return ACTOR_TO_ACT, candidates, evaluated, [k for k in MAIN_KINDS if k not in evaluated], PARTIAL, None
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
    if found.kind in (KIND_ATTACH_ENERGY, KIND_EVOLVE, KIND_RETREAT):
        return _turn_input_problem(found, choices)
    if found.kind == KIND_USE_ATTACK:
        return _attack_input_problem(found, choices)
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


# ---------------------------------------------------------------- 番の基本の操作（U7-3。docs/legal-actions-u7-3.md）

ILLEGAL = "illegal"  # エンジンの確かめが IllegalActionError（ゲーム上できない。候補・組に出さない）
STOP = "stop"  # エンジンの確かめが UnsupportedError（未裁定・未対応。選べるものとして示し、実行できない区分にする）
REASON_REACTIONS = "reactions_not_evaluated"  # 受理のあとの反応・決定・停止のもとが場にある（評価していない）
REASON_FACE_DOWN = "face_down_reveal_not_evaluated"  # 自分のうらのカード（マチスの秘策）がする操作。エンジンがおもてにしてから確かめる（候補の作成では確かめていない）
REASON_STOPS = "stops_before_acceptance"  # エンジンが受け付ける前に止める（未裁定・未対応）
# 候補の処理可能性を、選べるもの・組の中のいちばん進めやすい区分で示す順
_RANK = (SUPPORTED, MAY_STOP_LATER, UNVERIFIED, RULING_UNRESOLVED, NOT_IMPLEMENTED, TECHNICAL_LIMIT)
# 受理のあとに反応・決定・停止のもとになりうる、状態の番の効果・場の外の記録（公開の情報。あれば supported にしない）
_EFFECT_FIELDS = ("face_down_cards", "face_up_deck", "trainer_effects", "energy_burn", "energy_roles", "color_effects", "poison_mists", "replacement_poisons",
                  "frozen_forms", "set_aside", "trainer_locks", "recalls", "pending_moves")


def _probe(check, *args) -> tuple[str | None, str | None]:
    """エンジンが受け付ける前の確かめ（``engine.check_*``。状態・乱数・ログを変えない）を呼び、(ILLEGAL・STOP・None, コード) にする。理由の文は返さない。"""
    try:
        check(*args)
    except IllegalActionError as error:
        return ILLEGAL, error.code
    except UnsupportedError as error:
        return STOP, error.code
    return None, None


def _quiet(state: GameState) -> bool:
    """受理のあとの反応・決定・停止のもとが場にない（supported の条件。公開の情報だけ。うらのカードがあれば偽なので、本当のカードを読まない）。十分条件で、偽でも止まるとは限らない。"""
    if state.stadium is not None or state.energy_attached_by_powers_this_turn or any(getattr(state, name) for name in _EFFECT_FIELDS):
        return False
    for side in state.players:
        for pokemon in side.in_play():
            if (pokemon.trainers or pokemon.markers or pokemon.persistent_effects or pokemon.type_shift is not None or pokemon.disguise is not None
                    or powers_of(state, pokemon)):
                return False
    return True


def _after(quiet: bool) -> tuple[str, list[str]]:
    return (SUPPORTED, []) if quiet else (MAY_STOP_LATER, [REASON_REACTIONS])


def _verdict(verdict: str | None, code: str | None, quiet: bool) -> tuple[str, list[str]] | None:
    """確かめの結果から (処理可能性, 理由)。ゲーム上できないなら None。"""
    if verdict == ILLEGAL:
        return None
    if verdict == STOP:
        return _stop_processability(code), [REASON_STOPS]
    return _after(quiet)


def _best(items: list[tuple[str, list[str]]]) -> tuple[str, list[str]]:
    best = min((item[0] for item in items), key=_RANK.index)
    return best, sorted({reason for proc, reasons in items if proc == best for reason in reasons})


def _option(base: dict[str, Any], processability: str, reasons: list[str]) -> dict[str, Any]:
    option = {**base, "eligible": processability in EXECUTABLE, "processability": processability}
    if reasons:
        option["reasons"] = list(reasons)
    return option


def _card_option(state: GameState, uid: int) -> dict[str, Any]:
    """本人の手札のカード（本人に見える）。"""
    definition = state.card_def(uid)
    option = {"card": uid, "card_id": state.cards[uid].card_id}
    if definition.category == "energy":
        option["special"] = definition.is_special_energy
    return option


def _pokemon_option(state: GameState, pokemon, zone: str, index: int | None) -> dict[str, Any]:
    """本人の場のポケモン（公開。本人のうらのカードは face_down で示し、カード id を出さない）。"""
    option = {"pokemon": pokemon.pokemon_id, "card": pokemon.card, "zone": zone}
    if index is not None:
        option["bench_index"] = index
    if state.is_face_down(pokemon):
        option["face_down"] = True
    else:
        option["card_id"] = state.cards[pokemon.card].card_id
    return option


def _field(state: GameState, actor: int) -> list[tuple[Any, dict[str, Any]]]:
    p = state.players[actor]
    return [(p.active, _pokemon_option(state, p.active, "active", None))] + [(q, _pokemon_option(state, q, "bench", i)) for i, q in enumerate(p.bench)]


def _turn_candidates(state: GameState, actor: int) -> list[_Candidate]:
    """番の基本の操作の候補（種類の順。ゲーム上できない種類は候補を作らない）。手札・場の並びは本人に見える並びのまま。"""
    quiet = _quiet(state)
    built = [_play_basic_candidate(state, actor, quiet), _attach_candidate(state, actor, quiet), _evolve_candidate(state, actor, quiet),
             _retreat_candidate(state, actor, quiet)]
    return [c for c in built if c is not None]


def _play_basic_candidate(state: GameState, actor: int, quiet: bool) -> _Candidate | None:
    """手札からベンチに出す（1 段。手札のカード 1 枚）。場の並び・場のポケモンの番号はエンジンが決める。"""
    p = state.players[actor]
    options, values, executable, found_all = [], [], [], []
    for uid in p.hand:
        found = _verdict(*_probe(check_play_basic, state, PlayBasicToBench(actor, uid)), quiet and not state.card_def(uid).powers)
        if found is None:
            continue
        values.append(uid)
        executable.append(found[0] in EXECUTABLE)
        found_all.append(found)
        options.append(_option({"id": f"o{len(values)}", **_card_option(state, uid)}, *found))
    if not options:
        return None  # たねポケモン・ベイビィのカードがない・ベンチに空きがない（ゲーム上できない）
    processability, reasons = _best(found_all)
    stage = {"stage": 1, "input": INPUT_CHOOSE_OPTION, "role": "bench", "meaning": "card", "count": {"min": 1, "max": 1}, "options": options,
             "order": ORDER_NOT_APPLICABLE, "bench": {"count": len(p.bench), "limit": bench_limit(state, actor)}}
    public = {"processability": processability, "reasons": reasons, "guarantees": dict(GUARANTEE_TURN_ACTION), "choices_format": "[手札のカードの番号]"}
    return _Candidate("", KIND_PLAY_BASIC, public, [stage], disclosure=DISCLOSURE_CONFIRMED, values=tuple(values), executable=tuple(executable),
                      min_choices=1, max_choices=1)


def _pair_candidate(kind: str, firsts, seconds, evaluate, roles: tuple[str, str], choices_format: str) -> _Candidate | None:
    """2 段の操作（手札のカード → 場のポケモン）。組ごとの確かめの結果を options_by_choice に置く（組の条件は 2 段目の選べるものだけでは表せない）。"""
    pairs = {}
    for i, (first, _) in enumerate(firsts):
        for j, (second, _) in enumerate(seconds):
            found = evaluate(first, second)
            if found is not None:
                pairs[(i, j)] = found
    if not pairs:
        return None
    used_first = sorted({i for i, _ in pairs})
    used_second = sorted({j for _, j in pairs})
    names = {("a", i): f"o{n}" for n, i in enumerate(used_first, 1)}
    names.update({("b", j): f"o{len(used_first) + n}" for n, j in enumerate(used_second, 1)})
    ids = {names[("a", i)]: (1, firsts[i][0]) for i in used_first}
    ids.update({names[("b", j)]: (2, seconds[j][0]) for j in used_second})
    first_options = [_option({"id": names[("a", i)], **firsts[i][1]}, *_best([v for k, v in pairs.items() if k[0] == i])) for i in used_first]
    second_options = [_option({"id": names[("b", j)], **seconds[j][1]}, *_best([v for k, v in pairs.items() if k[1] == j])) for j in used_second]
    by_choice = {names[("a", i)]: [_option({"option": names[("b", j)]}, *pairs[(i, j)]) for j in used_second if (i, j) in pairs] for i in used_first}
    stages = [{"stage": 1, "input": INPUT_CHOOSE_OPTION, "role": roles[0], "meaning": "card", "count": {"min": 1, "max": 1}, "options": first_options,
               "order": ORDER_NOT_APPLICABLE},
              {"stage": 2, "input": INPUT_CHOOSE_OPTION, "role": roles[1], "meaning": "pokemon", "count": {"min": 1, "max": 1}, "options": second_options,
               "order": ORDER_NOT_APPLICABLE, "depends_on_stage": 1, "options_by_choice": by_choice,
               "note": "選べる組は options_by_choice（1 段目の番号ごと）。options は組のどれかにある場のポケモン"}]
    processability, reasons = _best(list(pairs.values()))
    public = {"processability": processability, "reasons": reasons, "guarantees": dict(GUARANTEE_TURN_ACTION), "choices_format": choices_format}
    return _Candidate("", kind, public, stages, disclosure=DISCLOSURE_CONFIRMED, ids=ids, min_choices=2, max_choices=2,
                      pairs={(names[("a", i)], names[("b", j)]): found[0] in EXECUTABLE for (i, j), found in pairs.items()})


def _attach_candidate(state: GameState, actor: int, quiet: bool) -> _Candidate | None:
    """手札からエネルギーをつける（エネルギーカード → つける場のポケモン）。その番につけた数・つける先の制限・特殊エネルギーの確かめはエンジンの確かめ。"""
    p = state.players[actor]
    firsts = [(uid, _card_option(state, uid)) for uid in p.hand if state.card_def(uid).category == "energy"]
    seconds = [(pokemon.card, option) for pokemon, option in _field(state, actor)]

    def evaluate(energy, target):
        return _verdict(*_probe(check_attach_energy, state, AttachEnergy(actor, energy, target)), quiet and not state.card_def(energy).is_special_energy)

    return _pair_candidate(KIND_ATTACH_ENERGY, firsts, seconds, evaluate, ("energy", "target"), "[エネルギーカードの番号, つける場のポケモンの番号]")


def _evolve_candidate(state: GameState, actor: int, quiet: bool) -> _Candidate | None:
    """手札から進化させる（進化カード → 進化させる場のポケモン）。名前・段階・その番の制限・退化・ベイビィの確かめはエンジンの確かめ（evolution_block を含む）。"""
    p = state.players[actor]
    firsts = [(uid, _card_option(state, uid)) for uid in p.hand if state.card_def(uid).category == "pokemon"]
    field_by_id = {pokemon.pokemon_id: pokemon for pokemon, _ in _field(state, actor)}
    seconds = [(pokemon.pokemon_id, option) for pokemon, option in _field(state, actor)]

    def evaluate(card, pokemon_id):
        if state.is_face_down(field_by_id[pokemon_id]):
            # 自分のうらのカード: エンジンがおもてにしてから確かめる（本当のカードを候補の作成では読まない）。進化カードとの組だけ示す
            return (UNVERIFIED, [REASON_FACE_DOWN]) if state.card_def(card).stage in ("stage1", "stage2") else None
        return _verdict(*_probe(check_evolve, state, EvolvePokemon(actor, card, pokemon_id)), quiet and not state.card_def(card).powers)

    return _pair_candidate(KIND_EVOLVE, firsts, seconds, evaluate, ("evolution_card", "target"), "[進化カードの番号, 進化させる場のポケモンの番号]")


def _retreat_candidate(state: GameState, actor: int, quiet: bool) -> _Candidate | None:
    """にげる（入れ替える控え → トラッシュするエネルギー）。全部の組を並べず、エネルギーの個数の条件で示す。組の確かめは入力の検査で engine.check_retreat。"""
    p = state.players[actor]
    if not p.bench:
        return None  # 控えがいない（ゲーム上できない）
    active = p.active
    face_down = state.is_face_down(active)
    if face_down:
        processability, reasons = UNVERIFIED, [REASON_FACE_DOWN]
    else:
        found = _verdict(*_probe(check_retreat_declaration, state, actor), quiet and not any(state.card_def(uid).is_special_energy for uid in active.energy))
        if found is None:
            return None  # ねむり・マヒ・にげられない効果・こんらんで失敗した番（ゲーム上できない）
        processability, reasons = found
    try:
        cost = retreat_cost(state, actor)
    except HiddenPropertyRead:
        if not face_down:
            raise
        # U7-5b で直した: 自分のうらのバトル場のポケモンは、にげるエネルギーがうらのあいだ決まらない（FD1。本当のカードによらない）。v0.166 までは候補の取得そのものが
        # 例外で失敗していた。費用・トラッシュするエネルギーの段を示せないので、入力を返さない（INPUT_BOUNDARY_UNCONFIRMED。送ればエンジンがおもてにしてから確かめる）
        public = {"processability": processability, "reasons": reasons, "guarantees": dict(GUARANTEE_TURN_ACTION),
                  "choices_format": "[入れ替える控えの番号, トラッシュするエネルギーの番号, ...]（エネルギーは選んだ順）"}
        return _Candidate("", KIND_RETREAT, public, [], disclosure=DISCLOSURE_UNCONFIRMED)
    except UnsupportedError:
        if processability in EXECUTABLE:
            raise  # 宣言の確かめを通ったのに費用が決まらない（エンジンの不具合。ここで隠さない）
        # U7-5a で直した: 宣言の確かめが止める（バトル場のなにかの化石・ピッピ人形の PF2 など）とき、費用も同じ理由で決まらない。v0.166 までは候補の取得そのものが
        # 例外で失敗していた。選べるものを示さない、実行できない候補にする（U7-4 の印刷のワザのないうらのカードと同じ形）
        public = {"processability": processability, "reasons": reasons, "guarantees": dict(GUARANTEE_TURN_ACTION),
                  "choices_format": "[入れ替える控えの番号, トラッシュするエネルギーの番号, ...]（エネルギーは選んだ順）"}
        return _Candidate("", KIND_RETREAT, public, [], disclosure=DISCLOSURE_CONFIRMED)
    ids, bench_options, energy_options = {}, [], []
    for index, pokemon in enumerate(p.bench):
        oid = f"o{len(ids) + 1}"
        ids[oid] = (1, pokemon.card)
        bench_options.append(_option({"id": oid, **_pokemon_option(state, pokemon, "bench", index)}, processability, reasons))
    for uid in active.energy:
        oid = f"o{len(ids) + 1}"
        ids[oid] = (2, uid)
        energy_options.append({"id": oid, "card": uid, "card_id": state.cards[uid].card_id, "special": state.card_def(uid).is_special_energy,
                               "units": energy_unit_count(state, (uid,), active), "processability": processability})
    stages = [{"stage": 1, "input": INPUT_CHOOSE_OPTION, "role": "new_active", "meaning": "pokemon", "count": {"min": 1, "max": 1}, "options": bench_options,
               "order": ORDER_NOT_APPLICABLE},
              {"stage": 2, "input": INPUT_CHOOSE_OPTION, "role": "discard", "meaning": "card", "count": {"min": 0, "max": len(energy_options)},
               "options": energy_options, "distinct": True, "order": ORDER_SIGNIFICANT, "order_preserved": True,
               "total_units": {"min": cost.minimum, "max": cost.maximum},
               "note": "トラッシュするカードの出すエネルギーの個数（units。カードの枚数ではない）の合計が total_units の範囲。1 枚で 2 個のカードは分けられない。トラッシュの並びは"
                       "選んだ順。余る個数・読み方で変わる数・入れ替えの前後で変わる効果は、入力の検査（エンジンの確かめ）が止める",
               **({"confused": True} if active.conditions.confused else {})}]
    public = {"processability": processability, "reasons": reasons, "guarantees": dict(GUARANTEE_TURN_ACTION),
              "choices_format": "[入れ替える控えの番号, トラッシュするエネルギーの番号, ...]（エネルギーは選んだ順）"}

    def verify(values):
        if face_down:
            return None  # エンジンがおもてにしてから確かめる（最終の判定は apply_command）
        verdict, _ = _probe(check_retreat, state, Retreat(actor, tuple(values[1:]), values[0]))
        return None if verdict is None else CANDIDATE_INPUT_INVALID if verdict == ILLEGAL else CANDIDATE_NOT_EXECUTABLE

    return _Candidate("", KIND_RETREAT, public, stages, disclosure=DISCLOSURE_CONFIRMED, ids=ids, min_choices=1, max_choices=1 + len(energy_options),
                      verify=verify)


def _turn_input_problem(found: _Candidate, choices: tuple) -> tuple[str | None, tuple[int, ...]]:
    """2 段の番の操作の入力（選ぶものの番号だけ。並びは変えない）。"""
    if not choices or any(type(choice) is not str or choice not in found.ids for choice in choices):
        return CANDIDATE_INPUT_INVALID, ()
    stages = [found.ids[choice][0] for choice in choices]
    if found.kind == KIND_RETREAT:
        rest = choices[1:]
        if stages[0] != 1 or any(stage != 2 for stage in stages[1:]) or len(set(rest)) != len(rest):
            return CANDIDATE_INPUT_INVALID, ()
        values = tuple(found.ids[choice][1] for choice in choices)
        code = found.verify(values)
        return (code, ()) if code is not None else (None, values)
    if len(choices) != 2 or stages != [1, 2] or tuple(choices) not in found.pairs:
        return CANDIDATE_INPUT_INVALID, ()  # 組にない（ゲーム上できない組・数・段の並びが違う）
    if not found.pairs[tuple(choices)]:
        return CANDIDATE_NOT_EXECUTABLE, ()
    return None, tuple(found.ids[choice][1] for choice in choices)


# ---------------------------------------------------------------- ワザの宣言（U7-4。docs/legal-actions-u7-4.md）

REASON_PREFLIGHT = "preflight_not_evaluated"  # エンジンの宣言の前の先読み（コインの結果・ワザの途中の決定を試す）を、候補の作成・入力の検査では呼ばない（宣言の受理を保証しない）
REASON_CONTINUATION = "continuation_not_evaluated"  # 受理のあと（コイン・ワザの途中の決定・きぜつ・反応）を評価していない
REASON_NO_PRINTED_ATTACK = "no_printed_attack"  # 自分のうらのバトル場のカードに印刷のワザがない（おもてにする処理だけになる。U7-4 は入力の形を作らない）
ADDON_STADIUM_COIN = "stadium_coin"  # UseAttack.stadium_coin（クチバシティジムのコインを投げる）
ADDON_ATTACK_POWER = "attack_power"  # UseAttack.attack_power（ワザを使うポケモン自身の、そのワザといっしょに使える特殊能力）
ADDON_WITH_POWER = "with_power"  # UseAttack.with_power・with_powers（自分の場のポケモンの、ワザといっしょに使う特殊能力。選んだ順に宣言する）


def _attack_command(actor: int, specs) -> UseAttack:
    """ワザ（("attack", 位置, 印刷したカード)）と、宣言といっしょに選ぶもの（選んだ順）から UseAttack を作る。力を持つポケモンが 1 匹なら with_power（v0.118 の形）、2 匹以上なら
    with_powers（v0.122 の形。選んだ順）。"""
    _, index, card = specs[0]
    kinds = [spec[0] for spec in specs[1:]]
    holders = tuple(spec[1] for spec in specs[1:] if spec[0] == ADDON_WITH_POWER)
    return UseAttack(actor, index, card, stadium_coin=ADDON_STADIUM_COIN in kinds, attack_power=ADDON_ATTACK_POWER in kinds,
                     with_power=holders[0] if len(holders) == 1 else None, with_powers=holders if len(holders) > 1 else ())


def _attack_public(attack, base: dict[str, Any]) -> dict[str, Any]:
    """ワザの表示（印刷の情報。名前・必要なエネルギー・ダメージの表示・説明）。"""
    return {**base, "name_ja": attack.name_ja, "cost": [energy.value for energy in attack.cost], "damage": attack.damage_display, "text_ja": attack.text_ja}


def _attack_verdict(verdict: str | None, code: str | None) -> tuple[str, list[str]]:
    if verdict == STOP:
        return _stop_processability(code), [REASON_STOPS]
    return MAY_STOP_LATER, [REASON_CONTINUATION, REASON_PREFLIGHT]  # _best と同じ並び（名前の順）


def _attack_candidate(state: GameState, actor: int) -> _Candidate | None:
    """ワザの宣言（1 段目: バトル場のポケモンが今持つワザ、2 段目: 宣言といっしょに選ぶもの（0 個以上・選んだ順））。ゲーム上宣言できるワザがなければ候補を作らない。

    選べるワザは ``effects.available_attacks``（今の姿・「思い出させる」・［サイコリンク］・許可で使えるワザ。公開の場から決まる）。ワザ・組ごとに ``check_use_attack``
    （エンジンが宣言を受け付ける前の確かめ。宣言の前の先読みは含まない）を呼ぶ。IllegalActionError のワザ・組は出さず、UnsupportedError は実行できない区分で示す。"""
    active = state.players[actor].active
    if active is None:
        return None
    guarantees = dict(GUARANTEE_ATTACK)
    if state.is_face_down(active):
        return _face_down_attack_candidate(state, active, guarantees)
    specs: dict[str, tuple] = {}
    attack_options, verdicts = [], {}
    for option in available_attacks(state, active):
        spec = ("attack", option.attack_index, option.card)
        verdict, code = _probe(check_use_attack, state, _attack_command(actor, (spec,)))
        if verdict == ILLEGAL:
            continue
        oid = f"o{len(specs) + 1}"
        specs[oid] = spec
        verdicts[oid] = _attack_verdict(verdict, code)
        # card_id はワザの登録の定義（AttackOption.card_id。state.card_def から決まる。うらのカードの本当のカードを読まない）
        base = {"id": oid, "card": option.card, "card_id": option.card_id, "attack_index": option.attack_index, "route": option.route}
        for name in ("provider", "payer"):
            if getattr(option, name) is not None:
                base[name] = getattr(option, name)
        if option.grantors:
            base["grantors"] = list(option.grantors)
        attack_options.append(_option(_attack_public(state.definitions[option.card_id].attacks[option.attack_index], base), *verdicts[oid]))
    if not attack_options:
        return None  # ねむり・マヒ・ワザを使えない効果・エネルギーが足りないなど（ゲーム上宣言できない）
    addons = _addon_specs(state, actor, active)
    addon_ids = {}
    for spec, _shown in addons:
        addon_ids[spec] = f"o{len(specs) + len(addon_ids) + 1}"
    pairs: dict[tuple[str, str], bool] = {}
    by_choice: dict[str, list[dict[str, Any]]] = {}
    used: dict[tuple, list[tuple[str, list[str]]]] = {}
    for aid, found in verdicts.items():
        by_choice[aid] = []
        pairs[(aid, "")] = found[0] in EXECUTABLE
        if found[0] not in EXECUTABLE:
            continue  # 選ぶと止めるワザ: いっしょに選ぶものを確かめない（ワザごと実行できない）
        for spec, _shown in addons:
            verdict, code = _probe(check_use_attack, state, _attack_command(actor, (specs[aid], spec)))
            if verdict == ILLEGAL:
                continue
            pair = _attack_verdict(verdict, code)
            pairs[(aid, addon_ids[spec])] = pair[0] in EXECUTABLE
            used.setdefault(spec, []).append(pair)
            by_choice[aid].append(_option({"option": addon_ids[spec]}, *pair))
    addon_options = []
    for spec, shown in addons:
        if spec in used:  # どのワザともいっしょに選べないもの（ゲーム上できない）は出さない（番号は欠番のまま）
            specs[addon_ids[spec]] = spec
            addon_options.append(_option({"id": addon_ids[spec], **shown}, *_best(used[spec])))
    stages = [{"stage": 1, "input": INPUT_CHOOSE_OPTION, "role": "attack", "meaning": "attack", "count": {"min": 1, "max": 1}, "options": attack_options,
               "order": ORDER_NOT_APPLICABLE},
              {"stage": 2, "input": INPUT_CHOOSE_OPTION, "role": "declaration_options", "meaning": "declaration_option",
               "count": {"min": 0, "max": len(addon_options)}, "options": addon_options, "depends_on_stage": 1, "options_by_choice": by_choice, "distinct": True,
               "decline": True, "order": ORDER_SIGNIFICANT, "order_preserved": True,
               "note": "宣言といっしょに選ぶもの（0 個でもよい）。選べるのは options_by_choice（1 段目の番号ごと）。with_power は選んだ順に宣言する。組み合わせは入力の検査"
                       "（エンジンの確かめ）が確かめる。ワザの対象・トラッシュするエネルギー・山札から選ぶカードなどは、受理のあとの決定で答える"}]
    processability, reasons = _best(list(verdicts.values()))
    public = {"processability": processability, "reasons": reasons, "guarantees": guarantees,
              "choices_format": "[ワザの番号, 宣言といっしょに選ぶものの番号, ...]（いっしょに選ぶものは選んだ順。0 個でもよい）"}

    def verify(values):
        verdict, _ = _probe(check_use_attack, state, _attack_command(actor, values))
        return None if verdict is None else CANDIDATE_INPUT_INVALID if verdict == ILLEGAL else CANDIDATE_NOT_EXECUTABLE

    ids = {oid: (1 if spec[0] == "attack" else 2, spec) for oid, spec in specs.items()}
    return _Candidate("", KIND_USE_ATTACK, public, stages, disclosure=DISCLOSURE_CONFIRMED, ids=ids, pairs=pairs, min_choices=1,
                      max_choices=1 + len(addon_options), verify=verify)


def _addon_specs(state: GameState, actor: int, active) -> list[tuple[tuple, dict[str, Any]]]:
    """宣言といっしょに選べるかもしれないもの（公開の場から。選べるかはワザごとにエンジンの確かめで決める）。並びは コイン → 自身の特殊能力 → 場の並び（バトル場 → ベンチ）。"""
    found: list[tuple[tuple, dict[str, Any]]] = []
    stadium = stadium_of(state, AttackCoinStadium)
    if stadium is not None:
        found.append(((ADDON_STADIUM_COIN,), {"addon": ADDON_STADIUM_COIN, "card": stadium[0].card, "card_id": state.cards[stadium[0].card].card_id}))
    if any(attack_power_slot(state, active, option.key) is not None for option in available_attacks(state, active)):
        found.append(((ADDON_ATTACK_POWER,), {"addon": ADDON_ATTACK_POWER, "pokemon": active.pokemon_id}))
    for pokemon, shown in _field(state, actor):
        slot = None if state.is_face_down(pokemon) else group_attack_power_slot(state, pokemon)
        if slot is not None:
            found.append(((ADDON_WITH_POWER, pokemon.pokemon_id), {"addon": ADDON_WITH_POWER, **shown, "power": slot.power.name_ja}))
    return found


def _face_down_attack_candidate(state: GameState, active, guarantees) -> _Candidate:
    """自分のうらのバトル場のポケモン（マチスの秘策）: エンジンがおもてにしてから確かめる（「たねポケモン」でなければトラッシュし、ワザは使わない）。選べるワザは本人が知る本当の
    カード（観測の real。本人だけに見える）の印刷のワザで、エンジンの確かめは呼ばない（unverified）。宣言といっしょに選ぶものは示さない。"""
    definition = state.printed_def(active.card)
    options, specs = [], {}
    for attack in definition.attacks if definition.category == "pokemon" else ():
        oid = f"o{len(specs) + 1}"
        specs[oid] = ("attack", attack.index, None)
        options.append(_option(_attack_public(attack, {"id": oid, "card": active.card, "card_id": definition.id, "attack_index": attack.index, "face_down": True}),
                               UNVERIFIED, [REASON_FACE_DOWN]))
    if not options:
        public = {"processability": NOT_IMPLEMENTED, "reasons": [REASON_FACE_DOWN, REASON_NO_PRINTED_ATTACK], "guarantees": guarantees}
        return _Candidate("", KIND_USE_ATTACK, public, [], disclosure=DISCLOSURE_CONFIRMED)
    stages = [{"stage": 1, "input": INPUT_CHOOSE_OPTION, "role": "attack", "meaning": "attack", "count": {"min": 1, "max": 1}, "options": options,
               "order": ORDER_NOT_APPLICABLE},
              {"stage": 2, "input": INPUT_CHOOSE_OPTION, "role": "declaration_options", "meaning": "declaration_option", "count": {"min": 0, "max": 0},
               "options": [], "depends_on_stage": 1, "options_by_choice": {oid: [] for oid in specs}, "distinct": True, "decline": True,
               "order": ORDER_NOT_APPLICABLE, "note": "うらのカードのワザといっしょに選ぶものは示さない（おもてにする前に確かめられない）"}]
    public = {"processability": UNVERIFIED, "reasons": [REASON_FACE_DOWN], "guarantees": guarantees, "choices_format": "[ワザの番号]"}
    return _Candidate("", KIND_USE_ATTACK, public, stages, disclosure=DISCLOSURE_CONFIRMED, ids={oid: (1, spec) for oid, spec in specs.items()},
                      pairs={(oid, ""): True for oid in specs}, min_choices=1, max_choices=1, verify=_not_checked)


def _not_checked(values) -> str | None:
    """うらのカードのワザ: エンジンがおもてにしてから確かめる（最終の判定は apply_command）。"""
    return None


def _attack_input_problem(found: _Candidate, choices: tuple) -> tuple[str | None, tuple]:
    """ワザの宣言の入力（[ワザ, 宣言といっしょに選ぶもの...]。並びは変えない）。組にない・重なり・段の並びの誤りは CANDIDATE_INPUT_INVALID。組み合わせはエンジンの確かめ。"""
    if not choices or any(type(choice) is not str or choice not in found.ids for choice in choices):
        return CANDIDATE_INPUT_INVALID, ()
    stages = [found.ids[choice][0] for choice in choices]
    if stages[0] != 1 or any(stage != 2 for stage in stages[1:]) or len(set(choices)) != len(choices):
        return CANDIDATE_INPUT_INVALID, ()
    attack = choices[0]
    if any((attack, choice) not in found.pairs for choice in choices[1:]):
        return CANDIDATE_INPUT_INVALID, ()  # そのワザといっしょに選べない（ゲーム上できない組）
    if not found.pairs[(attack, "")] or not all(found.pairs[(attack, choice)] for choice in choices[1:]):
        return CANDIDATE_NOT_EXECUTABLE, ()
    values = tuple(found.ids[choice][1] for choice in choices)
    code = found.verify(values)
    return (code, ()) if code is not None else (None, values)


# ---------------------------------------------------------------- 場のポケモン 1 匹を指す操作（U7-5a・U7-5b。docs/legal-actions-u7-5ab.md）

GUARANTEE_BOARD_ACTION = {
    "preconditions": "番・段階と、選べる場のポケモンごとに、エンジンが受け付ける前の確かめ（engine.check_remove_disguise・check_discard_from_play・check_reveal_face_down。"
                     "コマンドの処理と同じ関数・同じ順番。読むのは番・自分の場・「ばける」でのせたカード・場での役割・バトル場をはなれられない効果・うらであること）を候補の作成に使う",
    "acceptance": "eligible の選べるものだけで作り、入力の検査に合った入力は、エンジンが受け付ける前の確かめを満たす（最終の判定は apply_command。コマンドの項目の確かめ・"
                  "うらのカードの割り当ての確かめはエンジンの入口）",
    "after_acceptance": "「ばける」の解除は、元の姿の最大HPの確かめ（MH1・TK1）と反応を評価していない。おもてにする操作は、本当のカードで残るか・トラッシュするかが決まり、"
                        "それを評価・予告しない。すてる・トラッシュでバトル場が空けば、勝ち負けとバトル場に出す決定（promote_active の候補）に進む",
    "supported_scope": "supported は、なにかの化石・ピッピ人形をすてる操作で、受理のあとの反応・決定・停止のもとが場にないことを公開の情報で確かめた場合だけ（U7-3 と同じ条件）。"
                       "ほかは may_stop_later",
}
_UNUSABLE_GUARANTEES = {KIND_USE_ATTACK: GUARANTEE_ATTACK, **dict.fromkeys(BOARD_KINDS, GUARANTEE_BOARD_ACTION)}
_BOARD_COMMANDS = {KIND_REMOVE_DISGUISE: RemoveDisguise, KIND_DISCARD_FROM_PLAY: DiscardFromPlay, KIND_REVEAL_FACE_DOWN: RevealFaceDown}
# 種類ごとの (エンジンの確かめ, 段の role)。処理可能性の理由はどれも既存の語彙（GUI の契約の reason_codes にある語）
_BOARD_CHECKS = {KIND_REMOVE_DISGUISE: (check_remove_disguise, "disguised"), KIND_DISCARD_FROM_PLAY: (check_discard_from_play, "discard"),
                 KIND_REVEAL_FACE_DOWN: (check_reveal_face_down, "face_down")}


def _board_after(kind: str, quiet: bool) -> tuple[str, list[str]]:
    """確かめを通ったときの処理可能性。受理のあとを評価していないものは may_stop_later（根拠のない supported にしない）。"""
    if kind == KIND_REMOVE_DISGUISE:
        return MAY_STOP_LATER, [REASON_CONTINUATION]  # 元の姿の最大HP（MH1・TK1）・反応は処理のあとの確かめ
    if kind == KIND_REVEAL_FACE_DOWN:
        return MAY_STOP_LATER, [REASON_FACE_DOWN]  # 残るか・トラッシュするかは本当のカードで決まる（候補では評価・予告しない）
    return _after(quiet)  # すてる操作: U7-3 と同じ条件


def _board_candidates(state: GameState, actor: int) -> list[_Candidate]:
    """場のポケモン 1 匹を指す操作の候補（種類の順。ゲーム上できない種類は候補を作らない）。選べるものは本人の場の並び（バトル場 → ベンチ）。

    選べるものは公開の値だけで作る（``_pokemon_option``。本人のうらのカードは ``face_down`` で示し、カード id・名前を出さない）。エンジンの確かめが UnsupportedError
    （本人のうらのカードをすてようとしたときの FD1 など）なら、選べるものとして示し、実行できない区分にする（ゲーム上の禁止とは別。U7-3 と同じ）。"""
    quiet = _quiet(state)
    out = []
    for kind in BOARD_KINDS:
        check, role = _BOARD_CHECKS[kind]
        options, values, executable, found_all = [], [], [], []
        for pokemon, base in _field(state, actor):
            verdict, code = _probe(check, state, _BOARD_COMMANDS[kind](actor, pokemon.pokemon_id))
            if verdict == ILLEGAL:
                continue
            found = (_stop_processability(code), [REASON_STOPS]) if verdict == STOP else _board_after(kind, quiet)
            values.append(pokemon.pokemon_id)
            executable.append(found[0] in EXECUTABLE)
            found_all.append(found)
            options.append(_option({"id": f"o{len(values)}", **base}, *found))
        if not options:
            continue
        processability, reasons = _best(found_all)
        stage = {"stage": 1, "input": INPUT_CHOOSE_OPTION, "role": role, "meaning": "pokemon", "count": {"min": 1, "max": 1}, "options": options,
                 "order": ORDER_NOT_APPLICABLE}
        public = {"processability": processability, "reasons": reasons, "guarantees": dict(GUARANTEE_BOARD_ACTION), "choices_format": "[場のポケモンの番号]"}
        out.append(_Candidate("", kind, public, [stage], disclosure=DISCLOSURE_CONFIRMED, values=tuple(values), executable=tuple(executable),
                              min_choices=1, max_choices=1))
    return out


# ---------------------------------------------------------------- 手札のトレーナー（U7-5c。docs/legal-actions-u7-5c.md）

REASON_USE_CONDITION = "use_condition_not_evaluated"  # カードごとの使うための条件を、読む情報を確かめていないので候補の作成・入力の検査で呼んでいない（使えるかは送信でエンジンが決める）
GUARANTEE_TRAINER = {
    "preconditions": "番・段階と、手札のトレーナーカードごとに、エンジンが手札から出す前の確かめ（engine.check_play_trainer。番・手札・トレーナーカードであること・トレーナーの使用の禁止・"
                     "登録表・カードごとの使うための条件・リムーブ禁止ジムの追加の条件・MG1。コマンドの処理と同じ関数・同じ順番）を候補の作成に使う。使うための条件のうち、状態の複製の上で"
                     "実際の山札から引いて試すもの（PLAYABLE_NOT_EVALUATED）は呼ばない（unverified）",
    "acceptance": "保証しない。エンジンは受け付ける前に、［ちえくらべ］を使わない続き・効果の途中の決定の答えの続きを状態の複製の上で試し（_trainer_reaction_decline_check・_trainer_dead_end）、"
                  "効果の処理の途中の未裁定・未対応で拒否することがある（状態は変わらない）。候補の作成・入力の検査は、これらを呼ばない。最終の判定は apply_command",
    "after_acceptance": "評価していない（錯乱ジムのコイン・相手の［ちえくらべ］の決定・リムーブ禁止ジムの追加の条件・効果の対象や枚数や山札の検索・サイキックコントロールの使うカードは、どれも受理の"
                        "あとの決定で、answer_decision の候補で答える。決めるのが相手のこともある。番を終えるトレーナーは番を終える）",
    "supported_scope": "トレーナーの候補は supported にしない（受理の前の先読みと受理のあとを評価していないため）",
}
# 使うための条件（TrainerEffect.check_playable）のうち、候補の作成・入力の検査で呼ばないもの。条件を定義した型（effects.py）の名前。状態の複製の上で、実際の山札から引いて
# 結果を試す（読む値をたどっていない。U7-5 の設計の PT-5e のうちの 5 つ）。effects.py の外で定義した条件も呼ばない（_use_condition_evaluated）
PLAYABLE_NOT_EVALUATED = frozenset({"BlainesHeightQuiz", "BlainesQuiz", "GuessOpponentPrizeKind", "SetAsideGuessKindQuiz", "SwapPleaseTrainer"})
# PT-5e のうち、試すのが場の処理だけ（入れ替え・特殊状態・回復。読むのは場・カードの定義・番・場の効果の記録。山札・サイド・手札・うらのカードの中身を読まない）とたどったもの。
# 候補の作成で呼ぶ（docs/legal-actions-u7-5c.md 4 章）
PLAYABLE_BOARD_TRIALS = frozenset({"CoinHealAndCureOwnActive", "CoinHealBothElseSleepBoth", "CoinStatusOnOpponentActiveTrainer", "ConditionOwnActiveTrainer",
                                   "SwitchOpponentWithBench", "SwitchWithBench"})
_UNUSABLE_GUARANTEES[KIND_PLAY_TRAINER] = GUARANTEE_TRAINER


def _use_condition_owner(effect) -> type | None:
    """使うための条件（``check_playable``）を定義した型（継承をたどる）。"""
    return next((cls for cls in type(effect).__mro__ if "check_playable" in vars(cls)), None)


def _use_condition_evaluated(effect) -> bool:
    """候補の作成で、使うための条件を呼んでよいか（effects.py で定義し、PLAYABLE_NOT_EVALUATED でないもの）。登録のないカードは、check_play_trainer が条件の前に未対応として止める。"""
    if effect is None:
        return True
    owner = _use_condition_owner(effect)
    return owner is not None and owner.__module__ == "kyuura_engine.effects" and owner.__name__ not in PLAYABLE_NOT_EVALUATED


def _trainer_candidate(state: GameState, actor: int) -> _Candidate | None:
    """手札のトレーナーカードを使う（1 段。手札のカード 1 枚。``PlayTrainer``）。選べるものは本人の手札の並び。対象・枚数・費用・検索・任意の選択は、受理のあとの決定。

    ゲーム上できない（エンジンの確かめが ``IllegalActionError``）カードは出さない。未裁定・未対応（``UnsupportedError``）は選べるものとして示し、実行できない区分にする。
    使うための条件を呼ばないカード（``_use_condition_evaluated``）は unverified（使えるかを示さない。選べるものの数・並びは条件の結果によらない）。"""
    p = state.players[actor]
    options, values, executable, found_all = [], [], [], []
    for uid in p.hand:
        definition = state.card_def(uid)
        if definition.category != "trainer":
            continue
        evaluated = _use_condition_evaluated(state.effects.trainer_effect(definition))
        verdict, code = _probe(partial(check_play_trainer, use_condition=evaluated), state, PlayTrainer(actor, uid))
        if verdict == ILLEGAL:
            continue
        if verdict == STOP:
            found = (_stop_processability(code), [REASON_STOPS])
        elif evaluated:
            found = (MAY_STOP_LATER, [REASON_PREFLIGHT, REASON_CONTINUATION])
        else:
            found = (UNVERIFIED, [REASON_USE_CONDITION, REASON_PREFLIGHT, REASON_CONTINUATION])
        values.append(uid)
        executable.append(found[0] in EXECUTABLE)
        found_all.append(found)
        options.append(_option({"id": f"o{len(values)}", **_card_option(state, uid)}, found[0], sorted(found[1])))
    if not options:
        return None  # 手札にトレーナーカードがない・使えない（トレーナーの使用の禁止など。ゲーム上できない）
    processability, reasons = _best(found_all)
    stage = {"stage": 1, "input": INPUT_CHOOSE_OPTION, "role": "trainer", "meaning": "card", "count": {"min": 1, "max": 1}, "options": options,
             "order": ORDER_NOT_APPLICABLE}
    public = {"processability": processability, "reasons": reasons, "guarantees": dict(GUARANTEE_TRAINER), "choices_format": "[手札のカードの番号]"}
    return _Candidate("", KIND_PLAY_TRAINER, public, [stage], disclosure=DISCLOSURE_CONFIRMED, values=tuple(values), executable=tuple(executable),
                      min_choices=1, max_choices=1)
