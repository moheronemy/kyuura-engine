"""コマンドの確認（v0.15a。docs/integration-dependencies-v0.15a.md）。

v0.13 まで ``engine.py`` の中にあった、コマンドを受け付けるかの確認です。v0.13 の解決の経路（``engine.py``）と、v0.15 の解決の基盤
（``kyuura_engine/resolution/``）の両方が、同じ確認を同じ順番で使います（拒否のコード・メッセージ・順番を 1 か所で決める）。

ここにある関数は状態・乱数・ログを変えません（確かめて、だめなら例外を投げるだけ）。``engine.py`` を読み込みません。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .commands import PromoteActive, ResolveDecision, TakePrize
from .decisions import DECISION_PHASE_ORDER, check_choices
from .effects import (
    AttackKey,
    attack_cost_payable,
    attack_cost_problem,
    find_attack_option,
    form_def,
)
from .errors import IllegalActionError, StateIntegrityError, UnsupportedError
from .persistent import attack_locked, cannot_attack, cannot_attack_while_source_active
from .state import Phase

if TYPE_CHECKING:
    from .cards import Attack, CardDefinition
    from .commands import UseAttack
    from .effects import AttackEffect, AttackOption
    from .state import GameState, PendingDecision, PlayerState, PokemonInPlay

PLAYERS = (0, 1)


def require_phase(state: GameState, *phases: Phase) -> None:
    if state.phase not in phases:
        names = ", ".join(p.value for p in phases)
        raise IllegalActionError("WRONG_PHASE", f"今は {state.phase.value}。この操作は {names} のときだけ")


def require_player(player: Any) -> int:
    if player not in PLAYERS:
        raise IllegalActionError("INVALID_PLAYER", f"プレイヤーは 0 か 1（{player!r}）")
    return player


def require_turn(state: GameState, player: Any) -> PlayerState:
    require_phase(state, Phase.MAIN)
    require_player(player)
    if player != state.current_player:
        raise IllegalActionError("NOT_YOUR_TURN", f"今はプレイヤー {state.current_player} の番")
    return state.players[player]


def require_not_asleep_or_paralyzed(pokemon: PokemonInPlay, what: str) -> None:
    """ねむり状態・マヒ状態のバトル場のポケモンは、ワザを使えず、「にげる」を宣言できない（p.309・p.311・p.322。v0.3b）。"""
    if pokemon.conditions.asleep:
        raise IllegalActionError("POKEMON_ASLEEP", f"バトル場のポケモン {pokemon.pokemon_id} はねむり状態なので、{what}")
    if pokemon.conditions.paralyzed:
        raise IllegalActionError("POKEMON_PARALYZED", f"バトル場のポケモン {pokemon.pokemon_id} はマヒ状態なので、{what}")


def current_decision(state: GameState) -> PendingDecision:
    """決定を待つ段階の、保留中の決定。段階と決定が合わない状態（呼び出し側が書き換えた）は受け付けない。"""
    if state.decision is None:
        raise StateIntegrityError([f"{state.phase.value} なのに決定がない"])
    return state.decision


# ---------------------------------------------------------------- ワザ


@dataclass(frozen=True)
class AttackRequest:
    """受け付けたワザの宣言（確認が終わったもの）。"""

    player: int
    attacker: PokemonInPlay
    attacker_def: CardDefinition
    attack: Attack
    effect: AttackEffect
    key: AttackKey
    option: AttackOption | None = None  # v0.49: 選んだワザの出どころ（印刷したカード・持ち方・供給するポケモン）


def attack_request(state: GameState, cmd: UseAttack) -> AttackRequest:
    """ワザを使えるかの確認（p.309 の手順 1・2。v0.13 の ``engine._use_attack`` の前半と同じ順番・同じコード）。

    番 → ワザの位置 → ねむり・マヒ（手順 1。エネルギーの確認より前）→ 効果の登録 → 必要なエネルギー（手順 2）。原典で決められない場合
    （``UNRESOLVED_…``）の確認は、ここではしない（どちらの経路も、このあとに先読み・止める関数で確かめる）。
    """
    p = require_turn(state, cmd.player)
    attacker = p.active
    # v0.49（docs/virtual-attacks-transformation-v0.49.md 2 章）: 使うワザは、今持つワザ（``effects.available_attacks``）から、印刷したカード（``cmd.card``。None なら
    # 今の姿のカード）と位置で探す。今の姿（［へんしん］・「ばける」）・［サイコリンク］・「思い出させる」のワザも、ここで同じに確かめる
    option = find_attack_option(state, attacker, cmd.card, cmd.attack_index)
    if option is None:
        name = form_def(state, attacker).name_ja
        where = "" if cmd.card is None else f"（カード {cmd.card!r} の）"
        raise IllegalActionError("INVALID_ATTACK", f"{name} に{where} {cmd.attack_index!r} 番目のワザはない")
    attacker_def = state.definitions[option.card_id]
    require_not_asleep_or_paralyzed(attacker, "ワザを使うことができない（p.309・p.322）")
    if cannot_attack(state, attacker) is not None:
        # v0.31: イーブイの「しっぽをふる」を受けた（次の相手の番にワザをつかえない）。ねむり・マヒと同じ場所（宣言の前・エネルギーの確認より前）
        raise IllegalActionError("ATTACK_PREVENTED", f"バトル場のポケモン {attacker.pokemon_id} は、この番はワザを使えない（相手のワザの効果）")
    if cannot_attack_while_source_active(state, attacker) is not None:
        # v0.40: サカキのニドキングの「すごむ」を受けた（次の相手の番、効果を与えたポケモンがバトル場にいる限り、ワザを使えない）。効果を与えたポケモンが
        # 今バトル場にいるときだけ。「しっぽをふる」と同じ場所・同じコード（宣言の前・エネルギーの確認より前）
        raise IllegalActionError("ATTACK_PREVENTED", f"バトル場のポケモン {attacker.pokemon_id} は、効果を与えたポケモンがバトル場にいる間、この番はワザを使えない"
                                 "（相手のワザの効果）")
    if attack_locked(state, attacker, option.key) is not None:
        # v0.35: カスミのニョロモの「あわあわ」（自分）・「ドわすれ」（相手が選んだワザ）で、この番はこのワザを使えない。ほかのワザは使える。
        # 「しっぽをふる」と同じ場所（宣言の前・エネルギーの確認より前）。v0.49: ワザは ``AttackKey`` で探す（出どころによらない。「メガバーン」）
        raise IllegalActionError("ATTACK_LOCKED", f"バトル場のポケモン {attacker.pokemon_id} は、この番は {cmd.attack_index} 番目のワザを使えない（ワザの効果）")
    attack = attacker_def.attacks[option.attack_index]
    effect = state.effects.attack_effect(attacker_def.id, attack, attacker_def.attacks)
    if effect is None:
        problem = state.effects.attack_problem(attacker_def.id, attack, attacker_def.attacks)
        raise UnsupportedError("UNSUPPORTED_ATTACK", f"ワザ「{attack.name_ja}」は未対応（{problem}）")
    if effect.once_after_entering_play and option.problem is None and (option.card, option.attack_index) in attacker.attacks_used_once:
        # v0.44: 「このワザは、このカードが場に出てから、1回しか使えない」ワザを、この場のポケモンがもう使った（記録は場のポケモンの ``attacks_used_once``。
        # 宣言のときに記録する。ログから数えない）。エネルギーの確認の前（説明が使えないとするワザなので、必要なエネルギーがあっても使えない）
        raise IllegalActionError("ATTACK_ALREADY_USED", f"バトル場のポケモン {attacker.pokemon_id} は、ワザ「{attack.name_ja}」を場に出てからもう使った"
                                 "（場に出てから1回しか使えない）")
    cost_problem = attack_cost_problem(state, attacker, attack)  # v0.58: TE2（［へんしん］のメタモンの無色の特殊エネルギー。ほかの確認がすべて通ったあとに止める）
    if cost_problem is None and not attack_cost_payable(state, attacker, attack):
        # v0.49: 必要なエネルギーはどのワザの出どころでも同じに確かめる（［へんしん］のメタモンはエネルギーカードをどの色としても払える。``effects.attack_cost_payable``）
        # v0.58: 出すエネルギーの個数と色で払う（無色2個エネルギー・レインボーエネルギー）
        raise IllegalActionError("INSUFFICIENT_ENERGY", f"ワザ「{attack.name_ja}」に必要なエネルギーが足りない")
    problem = effect.usage_problem(state, attacker)  # v0.31: 説明が書くワザを使うための条件（「ぼーっとする」）
    if problem is not None:
        raise problem
    if cost_problem is not None:
        raise cost_problem
    if option.problem is not None:
        # v0.49: 選ぶと止めるワザ（VS1・RC2〜RC4・VA1）。原典で決められない理由はほかの確認がすべて通ったあと（API の約束）
        raise UnsupportedError(option.problem[0], f"ワザ「{attack.name_ja}」（カード {option.card}）: {option.problem[1]}")
    return AttackRequest(cmd.player, attacker, attacker_def, attack, effect, option.key, option)


# ---------------------------------------------------------------- 保留中の決定への答え


def resolve_decision_choices(state: GameState, cmd: ResolveDecision) -> tuple[int, ...]:
    """``ResolveDecision`` の確認（どの種類の決定にも使える）。確かめ終わった選択を返す。"""
    require_phase(state, *DECISION_PHASE_ORDER)  # 理由の文の段階の並びは決まった順番（v0.16d）
    player = require_player(cmd.player)
    decision = current_decision(state)
    if decision.player != player:
        raise IllegalActionError("NOT_YOUR_DECISION", f"この決定をするのはプレイヤー {decision.player}")
    if cmd.decision != decision.id:
        raise IllegalActionError("WRONG_DECISION", f"今の決定の番号は {decision.id}（{cmd.decision} を指している）")
    check_choices(decision, cmd.choices)
    return cmd.choices


def take_prize_choices(state: GameState, cmd: TakePrize) -> tuple[int, ...]:
    """サイドを取る決定に、サイドの位置で答える（v0.1 からある形）。確かめ終わった選択を返す。"""
    require_phase(state, Phase.TAKE_PRIZE)
    player = require_player(cmd.player)
    decision = current_decision(state)
    if decision.player != player:
        raise IllegalActionError("NOT_YOUR_DECISION", f"プレイヤー {player} が取るサイドはない")
    if cmd.index not in decision.options:
        raise IllegalActionError("INVALID_PRIZE_INDEX", f"サイドの位置は 0〜{len(decision.options) - 1}")
    return (cmd.index,)


def promote_active_choices(state: GameState, cmd: PromoteActive) -> tuple[int, ...]:
    """バトル場に出す決定に、ベンチのポケモンのカードの uid で答える（v0.1 からある形）。場のポケモンの番号にした選択を返す。"""
    require_phase(state, Phase.PROMOTE_ACTIVE)
    player = require_player(cmd.player)
    decision = current_decision(state)
    if decision.player != player:
        raise IllegalActionError("NOT_YOUR_DECISION", f"今バトル場にポケモンを出すのはプレイヤー {decision.player}")
    p = state.players[player]
    index = p.bench_index(cmd.pokemon)
    if index is None:
        raise IllegalActionError("NOT_ON_BENCH", f"{cmd.pokemon!r} は自分のベンチにいない")
    return (p.bench[index].pokemon_id,)


DECISION_ANSWERS = {
    ResolveDecision: resolve_decision_choices,
    TakePrize: take_prize_choices,
    PromoteActive: promote_active_choices,
}


def decision_choices(state: GameState, cmd: Any) -> tuple[int, ...]:
    """決定への答えのコマンド（``ResolveDecision``・``TakePrize``・``PromoteActive``）を確かめて、選択を返す。"""
    return DECISION_ANSWERS[type(cmd)](state, cmd)
