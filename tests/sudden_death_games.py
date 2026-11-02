"""v0.134: サドン・デスの延長戦を通す対戦の道具（docs/sudden-death-v0.134.md 10 章）。テスト・ツールから使う（ファイル名が ``test_`` で始まらないので、``unittest`` は読み込まない）。

- ``SWAP_PIKACHU_DECK``・``SWAP_PIKACHU_DECK_B``: v0.2f のピカチュウのデッキ（tests/helpers.py の ``PIKACHU_DECK``・``PIKACHU_DECK_B``）の一部をとりかえっこプリーズ（PR1-027）4 枚にかえたもの。
  「でんげき」の自分へのダメージで同時のきぜつ・サドン・デスが起こり、交換で所有者の変わったカードが場・手札・トラッシュに散らばる
- ``swap_policy_command``: ``helpers.trainer_policy_command`` に、とりかえっこプリーズを使う（番ごとに 1 回まで・自分の手札が 2 枚以上・相手の手札がある）・選ぶ（いつも最初のカード）・
  答える（いつもオーケー）を重ねた手順
- ``MAGNEMITE_DECK``: コイル（PMCG1-036。「じばく」で自分もきぜつし、HP 40 以下の相手のバトル場のポケモンもきぜつさせる）を入れた雷のデッキ。両方が同時にサイドを取り、
  サイド 1 枚の延長戦でもまたサドン・デスになりやすい（``status_aware_policy`` で両方に使う）
- ``play_segments``: 終わるまで進め、サドン・デスになったら ``StartSuddenDeath`` で延長戦を始めて続ける（区間の数の上限は道具の上限で、エンジンの規則ではない）。区間の境界ごとの状態を返す
"""

from __future__ import annotations

from kyuura_engine import (
    EndTurn,
    IllegalActionError,
    Phase,
    PlayTrainer,
    ResolveDecision,
    StartSuddenDeath,
    UnsupportedError,
    UseAttack,
    apply_command,
    check_invariants,
    new_game,
)
from kyuura_engine.decisions import ACCEPT_REQUEST, SELECT_EXCHANGE_CARD
from kyuura_engine.deck import expand_decklist
from kyuura_engine.state import Asleep, Paralyzed
from tests.helpers import (
    DEFENDER,
    DIGLETT,
    DODUO,
    DRATINI,
    FIGHTING,
    HITMONCHAN,
    LIGHTNING,
    MACHOP,
    PIKACHU,
    PLUSPOWER,
    RATTATA,
    VOLTORB,
    trainer_policy_command,
)

SWAP = "PR1-027"
SWAP_PIKACHU_DECK = expand_decklist({PIKACHU: 4, RATTATA: 4, VOLTORB: 4, DRATINI: 4, DODUO: 4, PLUSPOWER: 4, DEFENDER: 4, SWAP: 4, LIGHTNING: 28})
SWAP_PIKACHU_DECK_B = expand_decklist({PIKACHU: 4, DIGLETT: 4, MACHOP: 4, HITMONCHAN: 4, RATTATA: 4, PLUSPOWER: 2, DEFENDER: 2, SWAP: 4, LIGHTNING: 16, FIGHTING: 16})
MAGNEMITE = "PMCG1-036"
MAGNEMITE_DECK = expand_decklist({MAGNEMITE: 4, PIKACHU: 4, VOLTORB: 4, RATTATA: 4, LIGHTNING: 44})
TERMINAL = (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED)
# 道具の上限（エンジンの規則ではない。延長戦の回数の上限・勝者の決め方はエンジンにない）
MAX_STEPS_PER_SEGMENT = 4000
MAX_SEGMENTS = 8


def swap_policy_command(state, *, janken_winner: int, played: set):
    """``trainer_policy_command`` にとりかえっこプリーズの使用・選択・答えを重ねた手順。``played`` は使った (番, プレイヤー) の集まり（区間ごとに空から）。"""
    d = state.decision
    if d is not None and d.kind == SELECT_EXCHANGE_CARD:
        return ResolveDecision(d.player, d.id, (d.options[0],))
    if d is not None and d.kind == ACCEPT_REQUEST:
        return ResolveDecision(d.player, d.id, (1,))
    if state.phase is Phase.MAIN and d is None:
        player = state.current_player
        hand = state.players[player].hand
        swaps = [uid for uid in hand if state.cards[uid].card_id == SWAP]
        key = (state.turn_number, player)
        if swaps and key not in played and len(hand) >= 2 and state.players[1 - player].hand:
            played.add(key)
            return PlayTrainer(player, swaps[0])
    return trainer_policy_command(state, janken_winner=janken_winner)


def status_aware_policy(state, *, janken_winner: int, played: set):
    """``swap_policy_command`` の、バトル場のポケモンがねむり・マヒ状態ならワザを使わずに番を終える形（コイルの「でんじは」のマヒ。tests/helpers.py の手順は確かめない）。"""
    command = swap_policy_command(state, janken_winner=janken_winner, played=played)
    if isinstance(command, UseAttack) and isinstance(state.players[command.player].active.conditions.exclusive, (Asleep, Paralyzed)):
        return EndTurn(command.player)
    return command


def play_segment(state, *, janken_winner: int, policy=swap_policy_command, check=None, max_steps: int = MAX_STEPS_PER_SEGMENT):
    """今の区間を終わる（GAME_OVER・SUDDEN_DEATH・HALTED）まで進める。(状態, 受け付けた操作の列)。手順の出したトレーナーが受け付けられなければ、その番は使わずに続ける。"""
    played: set = set()
    commands = []
    for _ in range(max_steps):
        if state.phase in TERMINAL:
            return state, commands
        command = policy(state, janken_winner=janken_winner, played=played)
        try:
            state = apply_command(state, command)
        except (IllegalActionError, UnsupportedError):
            if isinstance(command, PlayTrainer):
                continue
            raise
        commands.append(command)
        if check is not None:
            check(state)
    raise AssertionError("道具の手数の上限で区間が終わらなかった（エンジンの規則ではない）")


def play_segments(decks, seed: int, *, policy=swap_policy_command, check=None, boundary=None, max_segments: int = MAX_SEGMENTS):
    """``new_game`` から終わるまで進め、サドン・デスになったら延長戦を始めて続ける。(最後の状態, 受け付けた操作の列（``StartSuddenDeath`` を含む）, 区間ごとの終わりの状態の並び)。

    ``boundary(before, after)`` は、延長戦を始める直前（サドン・デスの状態）と直後の状態で呼ぶ。区間の数が ``max_segments`` に達したら、サドン・デスのまま返す（道具の上限）。"""
    state = new_game(*decks, seed)
    commands: list = []
    ends = []
    while True:
        state, done = play_segment(state, janken_winner=seed % 2, policy=policy, check=check)
        commands.extend(done)
        ends.append(state)
        if state.phase is not Phase.SUDDEN_DEATH or len(ends) >= max_segments:
            return state, commands, ends
        before = state
        state = apply_command(state, StartSuddenDeath())
        commands.append(StartSuddenDeath())
        if check is not None:
            check(state)
        if boundary is not None:
            boundary(before, state)


def invariant_check(state) -> None:
    problems = check_invariants(state)
    if problems:
        raise AssertionError(problems)
