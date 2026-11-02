"""サドン・デスの延長戦の開始（v0.134。docs/sudden-death-v0.134.md）。

基準: 公式ルール 2000.02.14版『ポケモンカードオフィシャルブック2000』p.324「17 サドン・デス」。原典の文は、既存の確認記録 docs/simultaneous-ko-v0.2f.md 2 章（v0.2f の照合）の
引用を再利用する（この版で原典の画像をあらためて読んではいない）:

- 「それぞれ自分の山札、トラッシュ、サイドカード、場にあるカード、手札のすべてをまとめて、最初のデッキの状態に戻します。」
- 「延長戦として、もう一度初めから対戦をやり直します。ただし、サイドカードは、1枚だけしかセットしません。」

この部品は、開始を受け付ける状態か（``start_problems``）・最初のデッキの復元（``initial_deck_owners``）・区間の記録（``archive``）と、``GameState`` の項目ごとの
扱い（``SEGMENT_FIELD_POLICY``）を持つ。状態を作り直す処理は ``engine``（``new_game`` と共通の準備）にある。カードの id で分岐しない。
"""

from __future__ import annotations

from dataclasses import dataclass

from . import judge
from .errors import UnsupportedError
from .state import GameResult, GameState, SegmentRecord

PLAYERS = (0, 1)

# 拒否のコード
NOT_SUDDEN_DEATH_CODE = "NOT_SUDDEN_DEATH"  # サドン・デスに移っていない段階（MAIN・GAME_OVER・HALTED・途中停止・決定待ち・準備など）
SUDDEN_DEATH_NOT_STARTED_CODE = "SUDDEN_DEATH_NOT_STARTED"  # サドン・デスに移った状態に、延長戦を始める操作以外のコマンドを送った
INITIAL_DECK_UNKNOWN_CODE = "UNSUPPORTED_SUDDEN_DEATH_INITIAL_DECK"  # 最初のデッキ（デッキリストと uid・出所の対応）を状態から復元できない

REFERENCES = ("P43 p.324", "NEO-2000-OFFICIAL-RULES", "sudden_death", "docs/simultaneous-ko-v0.2f.md 2 章（既存の原典確認記録の再利用）",
              "docs/sudden-death-v0.134.md")


@dataclass(frozen=True)
class UserSpecifiedSegmentRule:
    """利用者が指定した、対戦の区間をまたぐ扱い（v0.134）。カード 1 枚の登録の記録（``effects.USER_SPECIFIED_RULES``。対象 ``<カード id>/trainer``）とは別の種類の記録で、
    公式の裁定・エラッタ・最新の説明ではない。"""

    id: str
    specified_on: str
    statement: str
    rule: str
    scope: str
    not_decided: tuple[str, ...]
    unresolved: tuple[str, ...]
    document: str


# 利用者の指定（2026-11-02。この版の依頼）。p.324 の「それぞれ自分の…最初のデッキの状態に戻します」の「自分の」を、v0.130 の所有者の簡略化（交換が成立した 2 枚は受け取った
# プレイヤーが所有者）で読むと、交換したカードが受け取ったプレイヤーのデッキに入ってしまう。原典の「最初のデッキの状態」と、利用者のこの指定にしたがい、出所にもどす
USER_SUDDEN_DEATH_OWNERSHIP_RESET = UserSpecifiedSegmentRule(
    id="USER-SUDDEN-DEATH-OWNERSHIP-RESET",
    specified_on="2026-11-02",
    statement="とりかえっこプリーズで交換したカードは、元の所有者へ戻す。",
    rule=("サドン・デスの延長戦を始めるとき、とりかえっこプリーズで対戦の中の所有者が変わったカードを、そのカードを最初のデッキに入れたプレイヤー（追跡用の出所 origin）の"
          "デッキにもどす。交換の直前の所有者ではなく、再交換があっても最初の出所にもどす。新しい区間では、カードの表の所有者は出所と同じで、所有者の変更の記録は空から始める"),
    scope="延長戦を始める操作（StartSuddenDeath）だけ。同じ区間の中の交換の扱い（USER-SWAP-OWNERSHIP-RECEIVER。v0.130）は変えない",
    not_decided=("実物の所有権・対戦の外の返し方（CR-SWAP-PLEASE-REAL-TRADE-SEPARATE のまま）",),
    unresolved=("UQ-SWAP-PLEASE-OWNERSHIP",),
    document="docs/sudden-death-v0.134.md 2 章",
)

# GameState の項目ごとの、延長戦を始めるときの扱い（v0.134。docs/sudden-death-v0.134.md 5 章）。
# - "keep": 同じ値を使う（ルールの組・写しの元・最初の seed・カードの定義・デッキリスト・効果の登録表）
# - "continue": 入力の状態から続ける（乱数。最初の seed にもどさない）
# - "rebuild": 新しい区間の値を作る（カードの表は出所にもどし、プレイヤーは山札だけから、段階は準備、ログは区間の始まりのイベントから、区間の記録は前の区間を加える）
# - "reset": 項目の既定の値にもどす（ほかのすべて。番・先攻・決定・持続する効果・回数・履歴・所有者の変更・結果・停止など）。準備の処理（切る・配る・切り直し）が
#   そのあと通常どおり書く
# GameState に項目を加えたら、ここに分類を加える（tests/test_sudden_death_v0_134.py が、分類のない項目・ない項目の分類を見つける）
SEGMENT_FIELD_POLICY: dict[str, str] = {
    "rules": "keep", "card_data": "keep", "seed": "keep", "definitions": "keep", "decklists": "keep", "effects": "keep",
    "rng": "continue",
    "cards": "rebuild", "players": "rebuild", "phase": "rebuild", "log": "rebuild", "segments": "rebuild",
    "turn_number": "reset", "current_player": "reset", "first_player": "reset", "energy_attachments_this_turn": "reset", "mulligan_rounds": "reset",
    "result": "reset", "halt": "reset", "next_pokemon_id": "reset", "decision": "reset", "next_decision_id": "reset", "trainer_in_use": "reset",
    "energy_attached_by_powers_this_turn": "reset", "power_uses_this_turn": "reset", "energy_burn": "reset", "trainer_locks": "reset", "recalls": "reset",
    "trainer_effects": "reset", "stadium": "reset", "stadium_uses_this_turn": "reset", "trainer_stack": "reset", "energy_roles": "reset", "set_aside": "reset",
    "face_up_prizes": "reset", "face_down_cards": "reset", "color_effects": "reset", "turn_history": "reset", "poison_mists": "reset",
    "replacement_poisons": "reset", "frozen_forms": "reset", "face_up_deck": "reset", "ownership_changes": "reset", "pending_moves": "reset",
}


def start_problems(state: GameState) -> list[str]:
    """延長戦を始められるサドン・デスの状態でない理由（段階はサドン・デスとして、結果・ログ・残った処理の整合）。なければ空。不変条件（``engine.check_invariants``）とは別に
    確かめる（不変条件はカードの保存則・場の形などで、ここは開始の前提）。"""
    problems: list[str] = []
    result = state.result
    if not isinstance(result, GameResult) or result.outcome != "sudden_death" or result.winner is not None or not result.conditions:
        problems.append(f"サドン・デスの段階なのに、結果 {result!r} がサドン・デス（勝者なし・満たした条件あり）ではない")
    else:
        prizes = [any(p == player and c == judge.ALL_PRIZES_TAKEN for p, c in result.conditions) for player in PLAYERS]
        cannot = [any(p == 1 - player and c == judge.OPPONENT_CANNOT_FIELD_ACTIVE for p, c in result.conditions) for player in PLAYERS]
        known = all(p in PLAYERS and c in (judge.ALL_PRIZES_TAKEN, judge.OPPONENT_CANNOT_FIELD_ACTIVE) for p, c in result.conditions)
        if not known or judge.decide(prizes, cannot) != result:
            problems.append(f"結果の満たした条件 {result.conditions!r} が、勝ち負けの表（p.311）のサドン・デスと合わない")
    if state.halt is not None:
        problems.append("サドン・デスの段階なのに、止めた理由がある")
    if state.decision is not None or state.trainer_in_use is not None or state.trainer_stack or state.pending_moves:
        problems.append("サドン・デスの段階なのに、決定・使用中のトレーナー・処理の続きが残っている")
    ends = [event for event in state.log if event["kind"] == "game_end"]
    if len(ends) != 1 or (isinstance(result, GameResult) and (ends[0].get("outcome"), ends[0].get("winner"), tuple(ends[0].get("conditions", ())))
                          != (result.outcome, result.winner, tuple(result.conditions))):
        problems.append(f"今の区間のログの対戦の終わり（game_end）が 1 つで結果と同じ、になっていない（{len(ends)} 個）")
    return problems


def initial_deck_owners(state: GameState) -> dict[int, int]:
    """カードごとの、最初のデッキに入れたプレイヤー（uid → プレイヤー）。復元できなければ ``UnsupportedError``（``INITIAL_DECK_UNKNOWN_CODE``。推測でデッキを作らない）。

    2 つの記録が同じことを確かめる: カードの表の出所（``CardInstance.deck_owner``。所有者が変わったカードは ``origin``、ほかは ``owner``。v0.129 までの写しには ``origin`` が
    なく、所有者を変える処理もなかったので ``owner``）と、デッキリスト（``GameState.decklists``）の並びの uid の付け方（``new_game`` はプレイヤー 0 のデッキ、続けてプレイヤー 1 の
    デッキの順に 0 から付ける）。デッキリストのない状態（盤面を直接作った状態）・uid の付け方と合わない状態は復元できない。"""
    decklists = state.decklists
    if not (isinstance(decklists, tuple) and len(decklists) == 2 and all(decklists)):
        raise UnsupportedError(INITIAL_DECK_UNKNOWN_CODE, "デッキリストのない状態（盤面を直接作った状態など）は、最初のデッキを復元できないので、延長戦を始めない")
    sizes = len(decklists[0]), len(decklists[1])
    if sorted(state.cards) != list(range(sizes[0] + sizes[1])):
        raise UnsupportedError(INITIAL_DECK_UNKNOWN_CODE, "カードの uid が、デッキリストの並びの付け方（0 から通し番号）と合わないので、最初のデッキを復元できない")
    owners: dict[int, int] = {}
    for uid, card in state.cards.items():
        player, index = (0, uid) if uid < sizes[0] else (1, uid - sizes[0])
        if decklists[player][index] != card.card_id or card.deck_owner != player:
            raise UnsupportedError(INITIAL_DECK_UNKNOWN_CODE,
                                   f"カード {uid} の id・出所が、デッキリストの並び（プレイヤー {player} の {index} 番目）と合わないので、最初のデッキを復元できない")
        owners[uid] = player
    return owners


def archive(state: GameState) -> SegmentRecord:
    """今の区間を、終わった区間の記録にする（状態は変えない）。"""
    return SegmentRecord(
        index=state.segment_index,
        prize_count=state.initial_prize_count,
        first_player=state.first_player,
        turn_number=state.turn_number,
        mulligan_rounds=tuple(state.mulligan_rounds),
        result=state.result,
        log=tuple(state.log),
        ownership_changes=tuple(state.ownership_changes),
        face_down_cards=tuple(state.face_down_cards),
    )
