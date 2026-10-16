"""コマンドの処理（解決の基盤の入口。v0.15b）。docs/kernel-integration-v0.15b.md・docs/kernel-consolidation-v0.16b.md・docs/event-model-v0.14.md 3 章・5 章。

v0.16b から、ワザ・番の終わり・きぜつのあとの決定は、この基盤だけが処理します（v0.13 の経路は外した）。

- ``UseAttack``（``handle``）: 確認（``checks.attack_request``）→ 要素の並び（``contract.program_for``。対応表になく、v0.13 の約束でも処理
  できない実装は拒否）→ 先読み → 宣言 → こんらん → ワザの要素（``programs``）→ きぜつの判定 → きぜつの処理 → サイド・勝ち負け・
  ふしちょう・交代 → 番の終わり（ポケモンチェック）
- ``EndTurn``（``handle``）: 番の終わり（期限）→ ポケモンチェック（どく → きぜつ → … → ねむり・マヒ）→ 次の番
- 再開先が ``attack``・``knock_out``・``take_prize``・``post_knockout``・``promote_active``（``RESUMES``）の決定への答え
  （``resume_decision``。``ResolveDecision``・``TakePrize``・``PromoteActive`` の確認 ``checks.decision_choices`` は ``engine.py`` が済ませる）

コマンドの入口（未対応のコマンド・項目の型・終わった対戦・状態の複製・不変条件の確認）と、トレーナーの決定（再開先 ``trainer``）への
答えは ``engine.py`` が行います。``handle``・``resume_decision`` は、渡された状態（コマンドの入口が作った複製）を変えます。

この基盤は ``engine.py`` を読み込みません（``checks``・``procedures`` と、効果・状態の部品だけを使う。docs/integration-dependencies-v0.15a.md）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .. import judge
from .. import procedures as PR
from ..checks import PLAYERS, attack_request, require_turn
from ..commands import EndTurn, PromoteActive, ResolveDecision, TakePrize, UseAttack
from ..decisions import PROMOTE_ACTIVE, TAKE_PRIZE
from ..effects import AttackKey, AttackUse, PowerKey
from ..errors import UnsupportedError
from ..state import GameState

from . import catalog as C
from . import codec
from . import preflight as P
from . import v013_checks
from .contract import is_contract, program_for
from .events import FrameKind, Suspended, Trace, Window, WindowOpened
from ..persistent import attack_coin_checks, destiny_bond
from .kernel import DryRunComplete, Resolution, capture_post_knockout, check_simultaneous, knocked, ko_prevention_offers, track_ko
from .programs import AttackRun, decision_index, declare, run_elements
from .questions import OpenQuestion, to_error

PREFLIGHT_MODES = P.PREFLIGHT_MODES
NEXT_TURN = PR.NEXT_TURN
RESUMES = codec.RESUMES  # この基盤が続ける決定の再開先（ほかは engine.py。トレーナーの ``trainer``）


@dataclass
class Context:
    """1 つのコマンドの解決の設定。

    - ``original``: コマンドの入口に渡された状態（変えない。v0.15c の先読み ``derived`` は、実際の処理のあと、これの複製の上で、まだ
      試していない結果を試す。上限を超えたときの v0.13 の止める関数もこれで確かめる）
    - ``preflight``: 先読みの方法（``PREFLIGHT_MODES``。v0.13 の約束で書いたワザの実装（アダプタ）には使わない。v0.16b）
    - ``catalog``: 効果の定義の対応表（試験で差しかえる。既定は ``DEFAULT_CATALOG``）
    - ``trace``: 解決の記録（状態に保存しない）
    """

    original: GameState
    preflight: str = "derived"
    catalog: C.Catalog = C.DEFAULT_CATALOG
    trace: Trace = field(default_factory=Trace)

    def __post_init__(self) -> None:
        if self.preflight not in PREFLIGHT_MODES:
            raise ValueError(f"先読みの方法 {self.preflight!r} は {PREFLIGHT_MODES} のどれか")


def handle(state: GameState, command, ctx: Context) -> None:
    """ワザ・番の終わり（``UseAttack``・``EndTurn``）を、渡された状態（コマンドの入口が作った複製）の上で処理する。原典で決められない
    場合に当たったら、v0.13 と同じ ``UnsupportedError``（コードのない問いはエンジンの不具合として ``RuntimeError``）。"""
    try:
        _HANDLERS[type(command)](ctx, state, command)
    except OpenQuestion as question:
        raise to_error(question.key, question.detail, question.error) from None


def processes(state: GameState, command) -> bool:
    """この基盤が処理するコマンドか（ワザ・番の終わりと、再開先が ``RESUMES`` の決定への答え）。数を数える・試験のための問い合わせで、
    振り分けには使わない（振り分けは ``engine.py`` の ``_HANDLERS`` と ``_answer_decision``）。状態を変えない。"""
    if isinstance(command, COMMANDS):
        return True
    if isinstance(command, (ResolveDecision, TakePrize, PromoteActive)):
        return state.decision is not None and state.decision.resume in RESUMES
    return False


def resume_decision(state: GameState, choices: tuple[int, ...], ctx: Context) -> None:
    """再開先が ``RESUMES`` の決定に、確かめ終わった選択（``checks.decision_choices``）で答え、続きから処理する。"""
    if state.decision is None or state.decision.resume not in RESUMES:
        raise RuntimeError(f"この基盤が続けない決定 {state.decision!r}（engine.py の振り分けの誤り）")
    try:
        _resume(ctx, state, choices)
    except OpenQuestion as question:
        raise to_error(question.key, question.detail, question.error) from None


# ---------------------------------------------------------------- ワザ


def _use_attack(ctx: Context, state, cmd: UseAttack) -> None:
    """v0.13 の ``engine._use_attack`` と同じ確認（同じ順番・同じコード）のあと、先読みと解決。"""
    request = attack_request(state, cmd)  # v0.13 の経路と同じ確認（checks.attack_request）
    attacker, attack, effect, key = request.attacker, request.attack, request.effect, request.key
    program = program_for(effect, attack.name_ja)  # 対応表にもなく v0.13 の約束でも処理できない実装は、ここで拒否（状態を変える前）
    pid = attacker.pokemon_id
    use = AttackUse(cmd.player, pid, key)

    def body(res: Resolution) -> None:
        _attack_body(res, cmd.player, res.state.find_pokemon(pid)[1], key, attack, program)

    def on_limit() -> None:
        """先読みで試す結果の数が上限を超えた（途中までの結果は使わない）。v0.13 の止める関数で確かめたワザの実装なら、それで確かめる
        （止めなければ、実際の処理が自分の結果の問いを検出する）。ほかは推測で受け付けず拒否する。"""
        if type(effect) not in v013_checks.VERIFIED:
            raise UnsupportedError(
                "UNSUPPORTED_PREFLIGHT_LIMIT",
                f"ワザ「{attack.name_ja}」の宣言の前の先読みで試す結果の数が上限（{P.MAX_BRANCHES}）を超えた。原典で決められない場合に当たる結果が"
                "ないことを確かめられないので扱わない",
            )
        v013_checks.check(ctx.original, use, effect, ctx.original.find_pokemon(pid)[1], ctx.trace, mode="legacy_after_limit")

    if is_contract(program):
        # v0.13 の約束で書いた実装（v0.16b のアダプタ。contract.py）: 宣言の前の確認は実装の宣言（problem と v0.13 の止める関数）だけ。
        # resolve の中身は先読みから見えず、副作用のある resolve を何度も呼ばない（v0.13・v0.15 と同じ確認。先読みの方法によらない）
        v013_checks.check(state, use, effect, attacker, ctx.trace, mode="contract")
        body(Resolution(state, catalog=ctx.catalog, trace=ctx.trace))
        return
    if ctx.preflight == "derived":
        P.after_real_run(state, ctx.original, body, ctx.catalog, ctx.trace, on_limit)  # 実際の処理を含む
        return
    if ctx.preflight == "legacy" and type(effect) in v013_checks.VERIFIED:
        v013_checks.check(state, use, effect, attacker, ctx.trace, mode="legacy")
    else:
        # derived_full。v0.17d から、比べる方法 legacy でも、v0.13 の止める関数で確かめていない型（VERIFIED にない。v0.17 から加えた型）は
        # ここで確かめる（v0.13 の止める関数は v0.17 の問い（Z23 など）を知らず、コインの結果で受け付けるかが変わってしまう。
        # docs/card-extensibility-verification-v0.17d.md 6 章）
        try:
            P.derived(state, body, ctx.catalog, ctx.trace)
        except P.BranchLimit:
            on_limit()
    body(Resolution(state, catalog=ctx.catalog, trace=ctx.trace))


def _attack_body(res: Resolution, player: int, attacker, key: AttackKey, attack, program) -> None:
    state = res.state
    state.add_event("attack", player=player, pokemon=attacker.card, attack=attack.name_ja, attack_index=key.attack_index)
    use = (player, attacker.pokemon_id, key.card_id, key.attack_index)
    declare(program, res, player, attacker)  # v0.31: 宣言のあと・こんらんのコインの前の確認（トラッシュの時点が決まらないワザ。HC1）
    if _attack_check_failed(res, player, attacker, key):  # v0.36: p.309 の手順 4（「すなかけ」・「えんまく」など）
        _finish_attack(res, use)
        return
    if attacker.conditions.confused and not PR.confusion_check(state, player, attacker, action="attack", effect=str(key)):
        fs = res.open_frame(FrameKind.CONFUSION, parent=None, player=player, source_pid=attacker.pokemon_id, attack_key=key)
        problem = PR.confusion_damage_problem(state, attacker)  # v0.13 の経路と同じ判定・理由の文（procedures）
        if problem is not None:
            raise res.question("confusion_damage_modifiers", f"ポケモン {attacker.pokemon_id}", problem)
        before = attacker.damage
        PR.confusion_damage(state, player, attacker, effect=str(key))
        track_ko(res, fs, attacker, before)
        _finish_attack(res, use)
        return
    fs = res.open_frame(FrameKind.ATTACK, parent=None, player=player, source_pid=attacker.pokemon_id, attack_key=key)
    if run_elements(AttackRun(res, fs, program, attack), 0):
        return
    _finish_attack(res, use)


def _attack_check_failed(res: Resolution, player: int, attacker, key: AttackKey) -> bool:
    """p.309 のワザを使う手順 4（v0.36。docs/sand-attack-retreat-lock-v0.36.md 2 章）: ワザを使うポケモンが、ワザを失敗させる効果（``AttackCoinCheck``）を
    受けていれば、手順 3（宣言）のあと・手順 5（こんらん）の前に、持ち主がコインを投げる（``PR.attack_coin_check``）。「うら」ならワザは失敗（ログ
    ``attack_failed``。ワザの要素を処理しない。ワザは使ったことになり、番は終わる。p.323「12 ワザの失敗」）で True。

    - 宣言できないワザ（ねむり・マヒ・しっぽをふる・使えないワザ・エネルギー不足・未対応）は、この前に拒否している（コインを投げない）
    - こんらん状態のポケモン: 手順 4 でワザが失敗したとき、手順 5 のこんらんのコイン（「うら」なら自分に 20）をするかは原典から決められない（AC6）ので、
      コインの前に問い ``attack_check_confusion`` で止める（コインの結果によらず止まる。「おもて」なら手順 5 に進むことは決まっているが、宣言の前に
      分からない）
    - 2 つ以上の効果（順番が決まらない）は、今の対応カードでは起こらない（効果を与えるワザは前の番の 1 回だけで、効果は次の番の終わりまで。不変条件で
      同じ種類は 1 つまで）ので、エンジンの不具合
    """
    state = res.state
    checks = attack_coin_checks(state, attacker)
    if not checks:
        return False
    if len(checks) > 1:
        raise RuntimeError(f"ワザを使うポケモン {attacker.pokemon_id} に手順 4 のコインの効果が 2 つ以上ある（エンジンの不具合）")
    if attacker.conditions.confused:
        raise res.question("attack_check_confusion", f"ポケモン {attacker.pokemon_id}")
    if PR.attack_coin_check(state, player, attacker, checks[0], effect=str(key)):
        return False
    state.add_event("attack_failed", player=player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(key),
                    reason=PR.ATTACK_CHECK_FAILED)
    return True


def _finish_attack(res: Resolution, use: tuple[int, int, str, int]) -> None:
    """ワザの要素のあと: きぜつの判定の窓（同時のきぜつの原因・任意の効果の候補）→ 決定か、きぜつの処理。"""
    state = res.state
    res.trace.record(WindowOpened(Window.KO_CHECK, None))
    check_simultaneous(res)
    bonded = _destiny_bond(res)  # v0.31: 「みちづれ」
    offers = ko_prevention_offers(res)
    if bonded and offers:
        raise res.question("destiny_bond_with_ko_prevention", f"{[o[1].pokemon_id for o in offers]}")
    # v0.31: きぜつの処理の窓の問い（P19・P32）を、先読みの範囲の中で確かめる（控えポケモンへのダメージで起こるようになった。記録は残さない。
    # 実際の写しはきぜつの処理の前に ``_knock_out_after_attack`` が行う）
    capture_post_knockout(res, knocked(res), record=False)
    if res.dry_run:
        raise DryRunComplete()
    res.horizon()
    if offers:
        owner, pokemon, instance = offers[0]
        cont = codec.KoCheckContinuation(use, (instance.power_key.card_id, instance.power_key.power_index))
        codec.ko_check_decision(state, cont, player=owner, pokemon_id=pokemon.pokemon_id)
        res.trace.record(Suspended(codec.KNOCK_OUT, state.decision.kind, owner))
        return
    _knock_out_after_attack(res)


def _destiny_bond(res: Resolution) -> bool:
    """v0.31: きぜつの判定の窓で、「みちづれ」（``DestinyBond``）の効果がはたらいているポケモン（番でないプレイヤーの。はたらく番は次の相手の番）が
    HP 以上なら、相手の対戦ポケモン（番のプレイヤーのバトル場のポケモン）も「きぜつ」する（``res.forced``。ログ ``destiny_bond``）。

    同時のきぜつか（p.324）は決められない（C18 と同じ形）。どちらの読み方でも、サイドを取る順番（番のプレイヤーから）・バトル場に出す順番（番でない
    プレイヤーから）は同じで、結果が変わるのは勝ち負けが決まる場合（サイドを取り終える・場にポケモンがいなくなる）だけなので、そのときだけ止める（HC2）。
    相手の対戦ポケモンがすでに HP 以上なら、何もしない。"""
    state = res.state
    current = state.current_player
    target = state.players[current].active
    triggered = [(owner, pokemon) for owner, pokemon in knocked(res) if owner != current and destiny_bond(state, pokemon) is not None]
    if not triggered or target is None or any(pokemon is target for _, pokemon in knocked(res)):
        return False
    res.forced.add(target.pokemon_id)
    gone = knocked(res)
    taken = {player: sum(1 for owner, _ in gone if owner != player) for player in PLAYERS}
    ends = [
        (taken[player] and taken[player] >= len(state.players[player].prizes))
        or not [p for p in state.players[player].in_play() if all(p is not k for _, k in gone)]
        for player in PLAYERS
    ]
    if any(ends):
        raise res.question("destiny_bond_knockout", f"ポケモン {[p.pokemon_id for _, p in triggered]} → {target.pokemon_id}")
    for owner, pokemon in triggered:
        state.add_event("destiny_bond", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, target_player=current,
                        target_pokemon=target.card, target_pokemon_id=target.pokemon_id)
    return True


def _knock_out_after_attack(res: Resolution) -> None:
    state = res.state
    gone = knocked(res)
    candidates = capture_post_knockout(res, gone)
    prize_takers = []
    for owner, pokemon in gone:
        PR.knock_out(state, owner, pokemon, simultaneous=len(gone) > 1)
        prize_takers.append(1 - owner)
    _after_knockouts(res, prize_takers, None, candidates)


# ---------------------------------------------------------------- きぜつのあと（サイド → 勝ち負け → ふしちょう → 交代 → 続き）


def _after_knockouts(res: Resolution, prize_takers, then, post_knockout) -> None:
    state = res.state
    budget = {player: len(state.players[player].prizes) for player in PLAYERS}
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
        all_prizes_taken=[not state.players[p].prizes for p in PLAYERS],
        cannot_field_active=[state.players[p].active is None and not state.players[p].bench for p in PLAYERS],
    )
    if result is not None:
        PR.finish(state, result)
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
        PR.pokemon_check_sleep_and_paralysis(state)  # ポケモンチェックの 3・4 と次の番（v0.13 の部品）
    else:
        _end_turn(res)


# ---------------------------------------------------------------- 番の終わり・ポケモンチェック

def _end_turn(res: Resolution) -> None:
    """番の終わりの窓（期限: ついているトレーナー → 持続する効果 → にげるの失敗の記録。v0.13 と同じ順番）→ ポケモンチェック。"""
    state = res.state
    res.trace.record(WindowOpened(Window.TURN_END, None))
    PR.expire_at_turn_end(state)  # v0.13 の経路と同じ手続き
    _pokemon_check(res)


def _pokemon_check(res: Resolution) -> None:
    """ポケモンチェック（p.323）。どくのきぜつのあとは、ワザのあとと同じきぜつの処理の窓（ふしちょうの写し）を通る。"""
    state = res.state
    knocked = PR.pokemon_check_poison(state)  # 始まり・2 の「どく」・両方のきぜつで止める処理（v0.13 の経路と同じ手続き）
    if knocked is None:
        return
    if not knocked:
        PR.pokemon_check_sleep_and_paralysis(state)
        return
    candidates = capture_post_knockout(res, knocked)
    prize_takers = []
    for owner, pokemon in knocked:
        PR.knock_out(state, owner, pokemon, timing="pokemon_check")
        prize_takers.append(1 - owner)
    _after_knockouts(res, prize_takers, NEXT_TURN, candidates)


def _end_turn_command(ctx: Context, state, cmd: EndTurn) -> None:
    require_turn(state, cmd.player)
    state.add_event("end_turn_without_attack", player=cmd.player)
    _end_turn(Resolution(state, catalog=ctx.catalog, trace=ctx.trace))


# ---------------------------------------------------------------- 決定への答え（v0.13 と同じ確認のあと、続きの情報から再開）


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
    declared = AttackKey(card_id, attack_index)
    carried = dict(cont.extra)  # 要素の値は続きの情報から読む（決定の context を直接読まない）
    copied = carried.get("copied")  # v0.31: 相手のワザを自分のワザとして使っている途中の決定（選んだワザ）
    key = declared if copied is None else AttackKey(*copied)
    entry = state.effects.attack_entry(key.card_id, key.attack_index)
    attack = state.definitions[key.card_id].attacks[key.attack_index]
    program = program_for(entry.effect, attack.name_ja)
    fs = res.open_frame(FrameKind.ATTACK, parent=None, player=player, source_pid=pokemon_id, attack_key=key)
    run = AttackRun(res, fs, program, attack, declared=declared)
    run.carried = carried
    run.restore(carried)  # v0.31: 決定をまたいで運んだコインの結果・枠の値
    index = carried.get("element")  # v0.35: 決定を出した要素の位置（ダメージの要素の順番の決定。並びにダメージの要素が 2 つ以上あることがある）
    if index is None:
        index = decision_index(program, decision.kind)
    elif not (0 <= index < len(program) and program[index].decides(decision.kind)):
        raise RuntimeError(f"決定 {decision.kind} の続きの要素の位置 {index!r} が、その決定を出す要素ではない（エンジンの不具合）")
    program[index].resume(run, decision, choices)
    if run.suspended is not None:  # 答えのあとで、もう一度決定を出した（v0.13 の約束の 2 段階の決定。v0.16b）
        return
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
}
COMMANDS = tuple(_HANDLERS)  # ``handle`` が処理するコマンド（決定への答えは ``resume_decision``）
