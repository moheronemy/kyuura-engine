"""コマンドの処理（プロトタイプの入口）。docs/event-model-v0.14.md 3 章・5 章。

プロトタイプが受け持つのは、効果の解決の流れが通るコマンドだけです。

- ``UseAttack``: 宣言の前の確認 → 先読み → 宣言 → こんらん → ワザの要素（``programs``）→ きぜつの判定 → きぜつの処理 → サイド・勝ち負け・
  ふしちょう・交代 → 番の終わり（ポケモンチェック）
- ``EndTurn``: 番の終わり（期限）→ ポケモンチェック（どく → きぜつ → … → ねむり・マヒ）→ 次の番
- 再開先が ``attack``・``knock_out``・``take_prize``・``post_knockout``・``promote_active`` の決定への答え（``ResolveDecision``・
  ``TakePrize``・``PromoteActive``）

ほかのコマンド（対戦準備・ベンチ・進化・エネルギー・にげる・トレーナー・宣言する特殊能力・トレーナーの決定）は、v0.13 のエンジンの
``apply_command`` にそのまま渡します（効果の解決の流れを通らないので、プロトタイプの比べる対象ではない）。

状態を変える部品（きぜつの処理 ``_knock_out``・勝ち負けの判定・番の始まり・ポケモンチェックの 3・4・こんらんのコイン）は v0.13 の
エンジンの関数をそのまま呼びます（実験のため、非公開の関数を使っている。移行するなら公開の部品にする）。``apply_command`` と同じく、
渡された状態を変えず（複製の上で処理する）、返す状態を v0.13 の不変条件（``check_invariants``）で確かめます。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kyuura_engine import engine as ENG
from kyuura_engine import judge
from kyuura_engine.cards import can_pay_cost
from kyuura_engine.commands import UNSUPPORTED_COMMANDS, EndTurn, PromoteActive, ResolveDecision, TakePrize, UseAttack, check_command_fields
from kyuura_engine.decisions import DECISION_PHASES, PROMOTE_ACTIVE, TAKE_PRIZE, check_choices
from kyuura_engine.effects import AttackKey, AttackUse, PowerKey, attack_damage_modifiers
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.persistent import remove_expired_persistent_effects
from kyuura_engine.state import Halt, Phase

from . import catalog as C
from . import codec
from . import preflight as P
from .events import Delegated, FrameKind, Suspended, Trace, Window, WindowOpened
from .kernel import DryRunComplete, Resolution, capture_post_knockout, check_simultaneous, knocked_out, ko_prevention_offers, track_ko
from .programs import AttackRun, compile_attack, decision_index, run_elements
from .questions import OpenQuestion, to_error

PREFLIGHT_MODES = ("derived", "legacy")
NEXT_TURN = ENG.NEXT_TURN


@dataclass
class Context:
    preflight: str
    catalog: C.Catalog
    trace: Trace = field(default_factory=Trace)


def owned(state, command) -> bool:
    """プロトタイプが受け持つコマンドか（受け持たないものは v0.13 のエンジンに渡す）。"""
    if isinstance(command, (UseAttack, EndTurn)):
        return True
    if isinstance(command, (ResolveDecision, TakePrize, PromoteActive)):
        return state.decision is not None and state.decision.resume in codec.RESUMES
    return False


def apply_command(state, command, *, preflight: str = "derived", catalog: C.Catalog = C.DEFAULT_CATALOG):
    """``kyuura_engine.apply_command`` と同じ使い方。新しい状態を返し、渡した状態は変えない。"""
    return apply_command_traced(state, command, preflight=preflight, catalog=catalog)[0]


def apply_command_traced(state, command, *, preflight: str = "derived", catalog: C.Catalog = C.DEFAULT_CATALOG):
    """``apply_command`` と同じ処理をして、(新しい状態, 解決の記録) を返す。解決の記録は状態に保存しない。"""
    if preflight not in PREFLIGHT_MODES:
        raise ValueError(f"先読みの方法 {preflight!r} は {PREFLIGHT_MODES} のどれか")
    trace = Trace()
    if not owned(state, command):
        trace.record(Delegated(type(command).__name__))
        return ENG.apply_command(state, command), trace
    if isinstance(command, UNSUPPORTED_COMMANDS):
        raise UnsupportedError("UNSUPPORTED_ACTION", f"{type(command).__name__} は未対応")
    check_command_fields(command)
    if state.phase is Phase.GAME_OVER:
        raise IllegalActionError("GAME_OVER", "対戦は終わっている")
    if state.phase is Phase.SUDDEN_DEATH:
        raise UnsupportedError("SUDDEN_DEATH_NOT_IMPLEMENTED", "サドン・デス（延長戦）の開始は v0.1 では未実装")
    if state.phase is Phase.HALTED:
        raise UnsupportedError(state.halt.code, state.halt.message)
    new = state.clone()
    ctx = Context(preflight, catalog, trace)
    try:
        _HANDLERS[type(command)](ctx, new, command)
    except OpenQuestion as question:
        raise to_error(question.key, question.detail, question.error) from None
    ENG._require_integrity(new)
    return new, trace


# ---------------------------------------------------------------- ワザ


def _use_attack(ctx: Context, state, cmd: UseAttack) -> None:
    """v0.13 の ``engine._use_attack`` と同じ確認（同じ順番・同じコード）のあと、先読みと解決。"""
    p = ENG._require_turn(state, cmd.player)
    attacker = p.active
    attacker_def = state.card_def(attacker.card)
    if not 0 <= cmd.attack_index < len(attacker_def.attacks):
        raise IllegalActionError("INVALID_ATTACK", f"{attacker_def.name_ja} に {cmd.attack_index!r} 番目のワザはない")
    ENG._require_not_asleep_or_paralyzed(attacker, "ワザを使うことができない（p.309・p.322）")
    attack = attacker_def.attacks[cmd.attack_index]
    effect = state.effects.attack_effect(attacker_def.id, attack)
    if effect is None:
        problem = state.effects.attack_problem(attacker_def.id, attack)
        raise UnsupportedError("UNSUPPORTED_ATTACK", f"ワザ「{attack.name_ja}」は未対応（{problem}）")
    if not can_pay_cost(attack.cost, state.energy_types(attacker)):
        raise IllegalActionError("INSUFFICIENT_ENERGY", f"ワザ「{attack.name_ja}」に必要なエネルギーが足りない")
    program = compile_attack(effect)
    key = AttackKey(attacker_def.id, cmd.attack_index)
    pid = attacker.pokemon_id

    def body(res: Resolution) -> None:
        _attack_body(res, cmd.player, res.state.find_pokemon(pid)[1], key, attack, program)

    if ctx.preflight == "legacy":
        P.legacy(state, AttackUse(cmd.player, pid, key), effect, attacker, ctx.trace)
    else:
        P.derived(state, body, ctx.catalog, ctx.trace)
    body(Resolution(state, catalog=ctx.catalog, trace=ctx.trace))


def _attack_body(res: Resolution, player: int, attacker, key: AttackKey, attack, program) -> None:
    state = res.state
    state.add_event("attack", player=player, pokemon=attacker.card, attack=attack.name_ja, attack_index=key.attack_index)
    use = (player, attacker.pokemon_id, key.card_id, key.attack_index)
    if attacker.conditions.confused and not ENG._confusion_check(state, player, attacker, action="attack", effect=str(key)):
        fs = res.open_frame(FrameKind.CONFUSION, parent=None, player=player, source_pid=attacker.pokemon_id, attack_key=key)
        if attack_damage_modifiers(state, attacker, attacker):
            raise res.question("confusion_damage_modifiers", f"ポケモン {attacker.pokemon_id}")
        before = attacker.damage
        ENG._confusion_damage(state, player, attacker, effect=str(key))
        track_ko(res, fs, attacker, before)
        _finish_attack(res, use)
        return
    fs = res.open_frame(FrameKind.ATTACK, parent=None, player=player, source_pid=attacker.pokemon_id, attack_key=key)
    if run_elements(AttackRun(res, fs, program, attack), 0):
        return
    _finish_attack(res, use)


def _finish_attack(res: Resolution, use: tuple[int, int, str, int]) -> None:
    """ワザの要素のあと: きぜつの判定の窓（同時のきぜつの原因・任意の効果の候補）→ 決定か、きぜつの処理。"""
    state = res.state
    res.trace.record(WindowOpened(Window.KO_CHECK, None))
    check_simultaneous(res)
    offers = ko_prevention_offers(res)
    if res.dry_run:
        raise DryRunComplete()
    if offers:
        owner, pokemon, instance = offers[0]
        cont = codec.KoCheckContinuation(use, (instance.power_key.card_id, instance.power_key.power_index))
        codec.ko_check_decision(state, cont, player=owner, pokemon_id=pokemon.pokemon_id)
        res.trace.record(Suspended(codec.KNOCK_OUT, state.decision.kind, owner))
        return
    _knock_out_after_attack(res)


def _knock_out_after_attack(res: Resolution) -> None:
    state = res.state
    knocked = knocked_out(state)
    candidates = capture_post_knockout(res, knocked)
    prize_takers = []
    for owner, pokemon in knocked:
        ENG._knock_out(state, owner, pokemon, simultaneous=len(knocked) > 1)
        prize_takers.append(1 - owner)
    _after_knockouts(res, prize_takers, None, candidates)


# ---------------------------------------------------------------- きぜつのあと（サイド → 勝ち負け → ふしちょう → 交代 → 続き）


def _after_knockouts(res: Resolution, prize_takers, then, post_knockout) -> None:
    state = res.state
    budget = {player: len(state.players[player].prizes) for player in ENG.PLAYERS}
    queue = []
    for player in prize_takers:
        if budget[player] > 0:
            queue.append(player)
            budget[player] -= 1
    _next_prize_or_judge(res, tuple(queue), then, tuple(post_knockout))


def _next_prize_or_judge(res: Resolution, queue: tuple, then, post_knockout: tuple) -> None:
    state = res.state
    if queue:
        codec.prize_decision(state, queue[0], codec.AftermathContinuation(TAKE_PRIZE, queue[1:], then, post_knockout))
        res.trace.record(Suspended(TAKE_PRIZE, TAKE_PRIZE, queue[0]))
        return
    result = judge.decide(
        all_prizes_taken=[not state.players[p].prizes for p in ENG.PLAYERS],
        cannot_field_active=[state.players[p].active is None and not state.players[p].bench for p in ENG.PLAYERS],
    )
    if result is not None:
        ENG._finish(state, result)
        return
    if post_knockout:
        _offer_post_knockout(res, post_knockout, then)
        return
    _promotions_after_judge(res, then)


def _offer_post_knockout(res: Resolution, post_knockout: tuple, then) -> None:
    """勝ち負けのあとの窓: きぜつの処理の前に写した任意の効果（ふしちょう）を、持ち主に決定で聞く（正規化した順番。v0.12 と同じ）。"""
    state = res.state
    res.trace.record(WindowOpened(Window.AFTER_JUDGE, None))
    if len(post_knockout) != 1:
        raise RuntimeError(f"勝ち負けのあとの任意の効果の候補 {post_knockout!r} が 1 つではない（エンジンの不具合）")
    owner, card, card_id, power_index = post_knockout[0]
    if card not in state.players[owner].discard:
        raise RuntimeError(f"候補のカード {card} が持ち主 {owner} のトラッシュにない（エンジンの不具合）")
    codec.post_knockout_decision(state, owner, card, codec.AftermathContinuation(codec.POST_KNOCKOUT, (), then, (), (card_id, power_index)))
    res.trace.record(Suspended(codec.POST_KNOCKOUT, state.decision.kind, owner))


def _promotions_after_judge(res: Resolution, then) -> None:
    state = res.state
    order = (1 - state.current_player, state.current_player)
    queue = tuple(p for p in order if state.players[p].active is None)
    if then == NEXT_TURN and len(queue) > 1:
        raise RuntimeError("ポケモンチェックのあとで両方のプレイヤーがバトル場に出そうとした（エンジンの不具合）")
    _next_promotion_or_end(res, queue, then)


def _next_promotion_or_end(res: Resolution, queue: tuple, then) -> None:
    state = res.state
    if queue:
        codec.promote_decision(state, queue[0], codec.AftermathContinuation(PROMOTE_ACTIVE, queue[1:], then))
        res.trace.record(Suspended(PROMOTE_ACTIVE, PROMOTE_ACTIVE, queue[0]))
        return
    if then == NEXT_TURN:
        ENG._pokemon_check_sleep_and_paralysis(state)  # ポケモンチェックの 3・4 と次の番（v0.13 の部品）
    else:
        _end_turn(res)


# ---------------------------------------------------------------- 番の終わり・ポケモンチェック

POKEMON_CHECK_DOUBLE_KNOCKOUT = Halt(
    code="UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT",
    message=(
        "ポケモンチェックの「どく」のダメージで、両方のプレイヤーのポケモンがきぜつする。"
        "同時のきぜつか（p.324）、バトル場に出す順番（pp.323〜324。ポケモンチェックはどちらの番でもない。p.323）、"
        "サイドを取る順番を決めるプレイヤー（p.325）が公式ルール 2000.02.14版から決められないので、対戦を止める。"
    ),
    references=("P43 p.322", "P43 p.323", "P43 p.324", "P43 p.325", "NEO-2000-OFFICIAL-RULES", "knockout_timing"),
)


def _end_turn(res: Resolution) -> None:
    """番の終わりの窓（期限: ついているトレーナー → 持続する効果 → にげるの失敗の記録。v0.13 と同じ順番）→ ポケモンチェック。"""
    state = res.state
    res.trace.record(WindowOpened(Window.TURN_END, None))
    ENG._discard_expired_attachments(state)
    remove_expired_persistent_effects(state)
    for p in state.players:
        for pokemon in p.in_play():
            pokemon.retreat_failed_turn = None
    state.add_event("turn_end", player=state.current_player)
    _pokemon_check(res)


def _pokemon_check(res: Resolution) -> None:
    """ポケモンチェック（p.323）。どくのきぜつのあとは、ワザのあとと同じきぜつの処理の窓（ふしちょうの写し）を通る。"""
    state = res.state
    state.add_event("pokemon_check")
    order = (state.current_player, 1 - state.current_player)
    poisoned = [(owner, pokemon) for owner in order for pokemon in state.players[owner].in_play() if pokemon.conditions.poison is not None]
    knocked_owners = {
        owner for owner, pokemon in poisoned if pokemon.damage + pokemon.conditions.poison.damage >= state.card_def(pokemon.card).hp
    }
    if len(knocked_owners) > 1:
        ENG._halt(state, POKEMON_CHECK_DOUBLE_KNOCKOUT)
        return
    for owner, pokemon in poisoned:
        amount = pokemon.conditions.poison.damage
        pokemon.damage += amount
        state.add_event("poison_damage", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, amount=amount,
                        total_damage=pokemon.damage)
    knocked = [(owner, pokemon) for owner in order for pokemon in state.players[owner].in_play()
               if pokemon.damage >= state.card_def(pokemon.card).hp]
    if not knocked:
        ENG._pokemon_check_sleep_and_paralysis(state)
        return
    candidates = capture_post_knockout(res, knocked)
    prize_takers = []
    for owner, pokemon in knocked:
        ENG._knock_out(state, owner, pokemon, timing="pokemon_check")
        prize_takers.append(1 - owner)
    _after_knockouts(res, prize_takers, NEXT_TURN, candidates)


def _end_turn_command(ctx: Context, state, cmd: EndTurn) -> None:
    ENG._require_turn(state, cmd.player)
    state.add_event("end_turn_without_attack", player=cmd.player)
    _end_turn(Resolution(state, catalog=ctx.catalog, trace=ctx.trace))


# ---------------------------------------------------------------- 決定への答え（v0.13 と同じ確認のあと、続きの情報から再開）


def _resolve_decision(ctx: Context, state, cmd: ResolveDecision) -> None:
    ENG._require_phase(state, *DECISION_PHASES)
    player = ENG._require_player(cmd.player)
    decision = ENG._current_decision(state)
    if decision.player != player:
        raise IllegalActionError("NOT_YOUR_DECISION", f"この決定をするのはプレイヤー {decision.player}")
    if cmd.decision != decision.id:
        raise IllegalActionError("WRONG_DECISION", f"今の決定の番号は {decision.id}（{cmd.decision} を指している）")
    check_choices(decision, cmd.choices)
    _resume(ctx, state, cmd.choices)


def _take_prize(ctx: Context, state, cmd: TakePrize) -> None:
    ENG._require_phase(state, Phase.TAKE_PRIZE)
    player = ENG._require_player(cmd.player)
    decision = ENG._current_decision(state)
    if decision.player != player:
        raise IllegalActionError("NOT_YOUR_DECISION", f"プレイヤー {player} が取るサイドはない")
    if cmd.index not in decision.options:
        raise IllegalActionError("INVALID_PRIZE_INDEX", f"サイドの位置は 0〜{len(decision.options) - 1}")
    _resume(ctx, state, (cmd.index,))


def _promote_active(ctx: Context, state, cmd: PromoteActive) -> None:
    ENG._require_phase(state, Phase.PROMOTE_ACTIVE)
    player = ENG._require_player(cmd.player)
    decision = ENG._current_decision(state)
    if decision.player != player:
        raise IllegalActionError("NOT_YOUR_DECISION", f"今バトル場にポケモンを出すのはプレイヤー {decision.player}")
    p = state.players[player]
    index = p.bench_index(cmd.pokemon)
    if index is None:
        raise IllegalActionError("NOT_ON_BENCH", f"{cmd.pokemon!r} は自分のベンチにいない")
    _resume(ctx, state, (p.bench[index].pokemon_id,))


def _resume(ctx: Context, state, choices: tuple[int, ...]) -> None:
    decision = state.decision
    state.decision = None
    cont = codec.decode(decision)
    res = Resolution(state, catalog=ctx.catalog, trace=ctx.trace)
    if isinstance(cont, codec.AttackContinuation):
        _resume_attack(res, decision, cont, choices)
    elif isinstance(cont, codec.KoCheckContinuation):
        _resume_ko_check(res, decision, cont, choices)
    elif cont.stage == TAKE_PRIZE:
        _resume_take_prize(res, decision, cont, choices)
    elif cont.stage == codec.POST_KNOCKOUT:
        _resume_post_knockout(res, decision, cont, choices)
    else:
        _resume_promote(res, decision, cont, choices)


def _resume_attack(res: Resolution, decision, cont: codec.AttackContinuation, choices) -> None:
    """ワザの途中の決定のあと: 決定を出した要素の続きから（宣言・コイン・それまでの要素は繰り返さない）。"""
    state = res.state
    player, pokemon_id, card_id, attack_index = cont.use
    key = AttackKey(card_id, attack_index)
    entry = state.effects.attack_entry(card_id, attack_index)
    program = compile_attack(entry.effect)
    _, attacker = state.find_pokemon(pokemon_id)
    attack = state.card_def(attacker.card).attacks[attack_index]
    fs = res.open_frame(FrameKind.ATTACK, parent=None, player=player, source_pid=pokemon_id, attack_key=key)
    run = AttackRun(res, fs, program, attack)
    run.carried = dict(cont.extra)  # 要素の値は続きの情報から読む（決定の context を直接読まない）
    index = decision_index(program, decision.kind)
    program[index].resume(run, decision, choices)
    if run_elements(run, index + 1):
        return
    _finish_attack(res, cont.use)


def _offer_effect(res: Resolution, card_id: str, power_index: int):
    """任意の効果の決定の、v0.13 の実装（効果の中身）と定義。"""
    definition = res.state.definitions[card_id]
    implementation = res.state.effects.power_effect(definition.id, definition.powers[power_index])
    effect_definition = C.definition_for(implementation, res.catalog.powers)
    if effect_definition is None or effect_definition.timing is not C.Timing.OFFER:
        raise RuntimeError(f"任意の効果の決定のパワー {card_id}@power{power_index} に、任意の効果の定義がない（エンジンの不具合）")
    return implementation, effect_definition


def _resume_ko_check(res: Resolution, decision, cont: codec.KoCheckContinuation, choices) -> None:
    """きぜつの判定の任意の効果（こんじょう）の答えのあと: 宣言と効果の中身（v0.13 の実装の ``prevent``）→ きぜつの処理。"""
    state = res.state
    owner = decision.player
    pokemon_id = decision.options[0]
    _, pokemon = state.find_pokemon(pokemon_id)
    card_id, power_index = cont.power
    key = PowerKey(card_id, power_index)
    implementation, effect_definition = _offer_effect(res, state.cards[pokemon.card].card_id, power_index)
    base = {"player": owner, "pokemon": pokemon.card, "pokemon_id": pokemon_id, "power": str(key)}
    if not choices:
        state.add_event("ko_prevention_declined", **base, total_damage=pokemon.damage)
    else:
        state.add_event("ko_prevention_declared", **base, total_damage=pokemon.damage, hp=state.card_def(pokemon.card).hp)
        OFFER_ACTIONS[effect_definition.action](state, owner, pokemon, key, implementation)
    _knock_out_after_attack(res)


def _resume_post_knockout(res: Resolution, decision, cont: codec.AftermathContinuation, choices) -> None:
    """勝ち負けのあとの任意の効果（ふしちょう）の答えのあと: 宣言と効果の中身（v0.13 の実装の ``recover``）→ 交代。"""
    state = res.state
    owner = decision.player
    card = decision.options[0]
    card_id, power_index = cont.power
    key = PowerKey(card_id, power_index)
    implementation, effect_definition = _offer_effect(res, card_id, power_index)
    base = {"player": owner, "card": card, "card_id": card_id, "power": str(key)}
    if not choices:
        state.add_event("post_knockout_power_declined", **base)
    else:
        state.add_event("post_knockout_power_declared", **base)
        OFFER_ACTIONS[effect_definition.action](state, owner, card, key, implementation)
    _promotions_after_judge(res, cont.then)


def _resume_take_prize(res: Resolution, decision, cont: codec.AftermathContinuation, choices) -> None:
    state = res.state
    player = decision.player
    prizes = state.players[player].prizes
    uid = prizes.pop(choices[0])
    state.players[player].hand.append(uid)
    state.add_event("take_prize", player=player, card=uid, remaining=len(prizes))
    _next_prize_or_judge(res, cont.remaining, cont.then, cont.post_knockout)


def _resume_promote(res: Resolution, decision, cont: codec.AftermathContinuation, choices) -> None:
    state = res.state
    p = state.players[decision.player]
    index = next(i for i, pokemon in enumerate(p.bench) if pokemon.pokemon_id == choices[0])
    p.active = p.bench.pop(index)
    state.add_event("promote_active", player=decision.player, pokemon=p.active.card)
    _next_promotion_or_end(res, cont.remaining, cont.then)


# 任意の効果の中身（v0.13 の実装のメソッドをそのまま呼ぶ。効果の中身はここに複製しない）
OFFER_ACTIONS = {
    "coin_then_remaining_hp": lambda state, owner, pokemon, key, impl: impl.prevent(state, owner, pokemon, key),
    "return_card_to_hand": lambda state, owner, card, key, impl: impl.recover(state, owner, card, key),
}

_HANDLERS = {
    UseAttack: _use_attack,
    EndTurn: _end_turn_command,
    ResolveDecision: _resolve_decision,
    TakePrize: _take_prize,
    PromoteActive: _promote_active,
}
