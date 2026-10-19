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
from ..decisions import BENCH_GUARD, ESP_REDO, KNOCK_OUT_POWER, NINJA_TRICK, PROMOTE_ACTIVE, REACTION_SWITCH, TAKE_PRIZE
from ..coins import CoinSide, flip_coins
from ..effects import (AttackKey, AttackUse, PowerKey, usable_ninja_tricks, attach_converted_energy, attack_rebellion_powers, counts_as_knockout, dormant_scram, max_hp,
                       received_modifiers_log, received_power_damage, retreat_trap_powers, stadium_attack_coin_available, status_at_attack_blocked)
from ..errors import IllegalActionError, UnsupportedError
from ..state import GameState, Phase
from ..history import close_probe, note_used
from ..zones import face_up_fields, prize_left, promote_from_bench, return_in_play_to_deck, shuffle_deck

from . import catalog as C
from . import codec
from . import preflight as P
from . import v013_checks
from .contract import is_contract, program_for
from .events import FrameKind, Suspended, Trace, Window, WindowOpened
from ..persistent import RETURN_IN_PLAY_TO_DECK, attack_coin_checks, destiny_bond, remove_on_damage, remove_persistent_effects
from .kernel import (DryRunComplete, Resolution, capture_post_knockout, check_simultaneous, hp_of, knock_out_beam_problem, knock_out_power_offers, knocked,
                     ko_prevention_offers, scram_restored_question, settle_scram, track_ko)
from .programs import (AttackRun, EspRedoOffer, apply_esp_redo, apply_flee, apply_ninja_trick, decision_index, declare, offer_ninja_trick, program_may_fail, resume_guarded, run_elements,
                       with_stadium_self_damage)
from .questions import OpenQuestion, to_error

PREFLIGHT_MODES = P.PREFLIGHT_MODES
NEXT_TURN = PR.NEXT_TURN
CONTINUE_TURN = PR.CONTINUE_TURN  # v0.42: 特殊能力の処理のあとの決定の続き（終わったら番のプレイヤーの番にもどる）
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

    once = effect.once_after_entering_play  # v0.44: 場に出てから 1 回しか使えないワザ（宣言のときに使った記録を置く）

    option = request.option
    coin_stadium = None
    if cmd.stadium_coin:
        # v0.57: クチバシティジムのコインを投げることを選んだ（ワザの宣言といっしょに選ぶ）。場にクチバシティジムがない・ワザを使うのが「マチスのポケモン」でないなら、
        # 状態を変える前に拒否する。v0.13 の約束で書いた実装（テスト専用）は、要素の並びに自分へのダメージを入れられないので扱わない
        found = stadium_attack_coin_available(state, cmd.player, attacker)
        if found is None:
            raise IllegalActionError("STADIUM_COIN_NOT_AVAILABLE", "場のクチバシティジムのコインを投げられない（場にない・ワザを使うのが「マチスのポケモン」ではない）")
        contract_program = is_contract(program)
        if contract_program:
            raise UnsupportedError("UNSUPPORTED_ATTACK", "v0.13 の約束で書いたワザの実装では、クチバシティジムのコインを扱わない（エンジンの未対応）")
        coin_stadium = found[0].card

    def body(res: Resolution) -> None:
        _attack_body(res, cmd.player, res.state.find_pokemon(pid)[1], key, attack, program, once, option, coin_stadium)

    def on_limit() -> None:
        """先読みで試す結果の数が上限を超えた（途中までの結果は使わない）。v0.13 の止める関数で確かめたワザの実装なら、それで確かめる
        （止めなければ、実際の処理が自分の結果の問いを検出する）。ほかは推測で受け付けず拒否する。"""
        if type(effect) not in v013_checks.VERIFIED or coin_stadium is not None:  # v0.57: クチバシティジムのコインは v0.13 の止める関数が知らない
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
    if ctx.preflight == "legacy" and type(effect) in v013_checks.VERIFIED and coin_stadium is None:
        # v0.57: クチバシティジムのコインを投げるワザは、v0.13 の止める関数が知らない（コインの +10・自分への 10）ので、すべての結果を試す方法で確かめる
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


def _attack_body(res: Resolution, player: int, attacker, key: AttackKey, attack, program, once: bool = False, option=None,
                 coin_stadium: int | None = None) -> None:
    state = res.state
    if option is None or option.card == attacker.card:
        state.add_event("attack", player=player, pokemon=attacker.card, attack=attack.name_ja, attack_index=key.attack_index)
    else:
        # v0.49: ワザの出どころがワザを使うポケモンのいちばん上のカードでない（［へんしん］・「ばける」・［サイコリンク］・「思い出させる」）。ワザを印刷したカード
        # （``card``・``card_id``）・持ち方（``route``）・［サイコリンク］で供給したポケモン（``provider``）を書く。どれも表のカード（公開の情報）。ふつうのワザは v0.48 と同じ形
        extra = {"provider": option.provider} if option.provider is not None else {}
        state.add_event("attack", player=player, pokemon=attacker.card, attack=attack.name_ja, attack_index=key.attack_index, card=option.card,
                        card_id=key.card_id, route=option.route, **extra)
    # v0.46: 「ワザが使われた時、すでに…」の特殊状態（エリカのフシギソウの［くつろぐかおり］）を宣言（p.309 の手順 3）の時点で写す。手順 4・5・ワザの要素で特殊状態が
    # 変わっても、このワザでは変えない（``effects.status_at_attack_blocked``。決定をまたぐときは続きの情報で運ぶ）
    res.attack_status = status_at_attack_blocked(state)
    if once:
        # v0.44: 「このワザは、このカードが場に出てから、1回しか使えない」。使った記録は宣言（p.309 の手順 3）のとき、手順 4（すなかけ）・手順 5（こんらん）・ワザの
        # 要素の前に置く（手順 4 の失敗・こんらんの「うら」・コインの「うら」でも使ったことになる。p.323「12」・v0.3d の A12）。宣言の前に拒否したら（確認・先読み）、
        # 状態ごと捨てるので記録は残らない。記録は場のポケモン（ワザを持つカードの uid とワザの位置）。ログ ``once_attack_recorded``
        attacker.attacks_used_once = attacker.attacks_used_once + ((attacker.card, key.attack_index),)
        state.add_event("once_attack_recorded", player=player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, attack_index=key.attack_index)
    # v0.62（docs/history-attacks-v0.62.md 2 章）: 使ったワザの記録（A）。宣言のとき（手順 4・5・ワザの要素より前）に置く（失敗・こんらんの「うら」でも使ったことになる）
    note_used(state, attacker, key)
    res.attack_declared = key
    use = (player, attacker.pokemon_id, key.card_id, key.attack_index)
    declare(program, res, player, attacker)  # v0.31: 宣言のあと・こんらんのコインの前の確認（トラッシュの時点が決まらないワザ。HC1）
    if usable_ninja_tricks(state, 1 - player) and (attack_coin_checks(state, attacker) or attack_rebellion_powers(state, attacker)
                                                   or attacker.conditions.confused or coin_stadium is not None):
        # v0.65（NT1）: 変わり身の術の「相手がワザを使う時」の入れ替えと、ワザの要素より先に投げるコイン（手順 4・5・クチバシティジム）の順番が決まらない（コインの前）
        raise res.question("ninja_trick_attack_order", f"ポケモン {attacker.pokemon_id} のワザ・変わり身の術 {list(usable_ninja_tricks(state, 1 - player))}")
    if _attack_check_failed(res, player, attacker, key):  # v0.36: p.309 の手順 4（「すなかけ」・「えんまく」など）
        _finish_attack(res, use)
        return
    if attacker.conditions.confused and not PR.confusion_check(state, player, attacker, action="attack", effect=str(key)):
        fs = res.open_frame(FrameKind.CONFUSION, parent=None, player=player, source_pid=attacker.pokemon_id, attack_key=key)
        problem = PR.confusion_damage_problem(state, attacker, res.attack_status)  # v0.13 の経路と同じ判定・理由の文（procedures）。v0.46: 常にはたらく特殊能力も
        if problem is not None:
            raise res.question("confusion_damage_modifiers", f"ポケモン {attacker.pokemon_id}", problem)
        before = attacker.damage
        PR.confusion_damage(state, player, attacker, effect=str(key))
        track_ko(res, fs, attacker, before)
        _finish_attack(res, use)
        return
    if coin_stadium is not None:
        program = _stadium_attack_coin(res, player, attacker, key, program, coin_stadium)
    fs = res.open_frame(FrameKind.ATTACK, parent=None, player=player, source_pid=attacker.pokemon_id, attack_key=key)
    run = AttackRun(res, fs, program, attack)
    # v0.65: 相手がワザを使う時（宣言が受け付けられ、ワザの要素の前）の変わり身の術。入れ替えたら、ワザのダメージや効果は入れ替えのあとでおこる（宣言・コインはやり直さない）
    if offer_ninja_trick(run) or run_elements(run, 0):
        return
    _finish_attack(res, use)


def _stadium_attack_coin(res: Resolution, player: int, attacker, key: AttackKey, program: tuple, stadium: int) -> tuple:
    """クチバシティジムのコイン（v0.57。docs/stadiums-v0.57.md 6 章）。ワザの宣言（p.309 の手順 3）のあと・ワザの要素の前に、ワザを使ったプレイヤーが 1 枚投げる。結果は
    ``res.stadium_coin``（決定をまたいでも運ぶ。投げ直さない）。「おもて」なら相手の対戦ポケモンへのダメージに 6 段階の +10（``kernel.deal_damage``）、「うら」なら
    並びに自分へのダメージの要素を入れる（``programs.with_stadium_self_damage``）。手順 4・5・ワザの失敗との順番が決まらない場合（VM1）はコインの前に止める。"""
    state = res.state
    if attack_coin_checks(state, attacker) or attack_rebellion_powers(state, attacker) or attacker.conditions.confused or program_may_fail(program):
        raise res.question("vermilion_attack_order", f"ポケモン {attacker.pokemon_id}")
    heads = flip_coins(state, player, 1, source="stadium", effect=state.cards[stadium].card_id, card=stadium,
                       pokemon_id=attacker.pokemon_id).results[0] is CoinSide.HEADS
    res.stadium_coin = (stadium, heads)
    state.add_event("stadium_attack_coin", player=player, pokemon_id=attacker.pokemon_id, effect=str(key), stadium_card=stadium, heads=heads)
    return program if heads else with_stadium_self_damage(program, stadium, _stadium_self_damage(state, stadium))


def _stadium_self_damage(state, stadium: int) -> int:
    return state.effects.trainer_entry(state.cards[stadium].card_id).effect.self_damage


def _attack_check_failed(res: Resolution, player: int, attacker, key: AttackKey) -> bool:
    """p.309 のワザを使う手順 4（v0.36。docs/sand-attack-retreat-lock-v0.36.md 2 章）: ワザを使うポケモンが、ワザを失敗させる効果（``AttackCoinCheck``）を
    受けていれば、手順 3（宣言）のあと・手順 5（こんらん）の前に、持ち主がコインを投げる（``PR.attack_coin_check``）。「うら」ならワザは失敗（ログ
    ``attack_failed``。ワザの要素を処理しない。ワザは使ったことになり、番は終わる。p.323「12 ワザの失敗」）で True。

    - 宣言できないワザ（ねむり・マヒ・しっぽをふる・使えないワザ・エネルギー不足・未対応）は、この前に拒否している（コインを投げない）
    - こんらん状態のポケモン: 手順 4 でワザが失敗したとき、手順 5 のこんらんのコイン（「うら」なら自分に 20）をするかは原典から決められない（AC6）ので、
      コインの前に問い ``attack_check_confusion`` で止める（コインの結果によらず止まる。「おもて」なら手順 5 に進むことは決まっているが、宣言の前に
      分からない）
    - 2 つ以上の効果（AC13）: v0.36 では起こらなかった（効果を与えるワザは前の番の 1 回だけで、効果は次の番の終わりまで）。v0.45 の期限のない効果
      （カスミのタッツーの「スミをかける」の「それ以後」）を受けたポケモンが、もう 1 つの効果（もう一度の「スミをかける」・「えんまく」など）を受けると起こる。
      効果ごとにコインを投げるのか、その順番、1 枚で両方を決めるのかが原典（p.309 の手順 4）から決められないので、コインの前に問い
      ``multiple_attack_checks`` で止める（こんらんの AC6 より先に聞く）
    """
    state = res.state
    checks = attack_coin_checks(state, attacker)
    rebellions = attack_rebellion_powers(state, attacker)  # v0.60: ［はんこう］（ワザを使う時にはたらく特殊能力。手順 4 の効果）
    if not checks and not rebellions:
        return False
    if len(checks) + len(rebellions) > 1:
        raise res.question("multiple_attack_checks", f"ポケモン {attacker.pokemon_id}（{len(checks) + len(rebellions)} つの効果）")
    if rebellions:
        return _rebellion_failed(res, player, attacker, key, rebellions[0])
    if attacker.conditions.confused:
        raise res.question("attack_check_confusion", f"ポケモン {attacker.pokemon_id}")
    if PR.attack_coin_check(state, player, attacker, checks[0], effect=str(key)):
        return False
    state.add_event("attack_failed", player=player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(key),
                    reason=PR.ATTACK_CHECK_FAILED)
    return True


REBELLION_FAILED = "power"  # v0.60: ［はんこう］のコインで失敗したワザ（ログ attack_failed の reason）


def _rebellion_failed(res: Resolution, player: int, attacker, key: AttackKey, slot) -> bool:
    """v0.60（docs/coins-defense-rebellion-v0.60.md 4 章）: カスミのギャラドスの［はんこう］（``effects.FailAndReturnOnAttack``）。p.309 の手順 4 の効果として、宣言のあと・こんらんの
    コインの前に、持ち主がコインを ``coins`` 枚投げる（ログ ``coin_flip`` の ``source`` は ``"power"``・``rebellion_check``）。すべて「うら」ならワザは失敗し（ログ
    ``attack_failed`` の ``reason`` ``"power"``）、このポケモンとついているすべてのカードを山札にもどし（``zones.return_in_play_to_deck`` の ``power``。きぜつではない）、持続する
    効果を消して（理由 ``return_in_play_to_deck``）、山札を切る（先読みでは切らない。ワザはこのあと何も処理しない）。True を返す（呼ぶ側がワザのあとの処理に進む）。

    - 「こんらん」状態でもはたらく。失敗しなければ手順 5（こんらんのコイン）に進む。失敗したら、もどしたポケモンにはこんらんのコインを投げない（処理の対象がない。p.309）。
      すなかけなどの手順 4 の効果（v0.36 の AC6）とは違い、どちらの順番でも結果が決まる（手順 4 で失敗すればポケモンは場にいない）ので、こんらんで止めない
    - コインの結果は「おもて」の数だけで使う（``by_heads``。先読みは 3 通り）"""
    state = res.state
    effect = slot.effect
    power = str(slot.key)
    flips = flip_coins(state, player, effect.coins, source="power", effect=power, card=slot.card, pokemon_id=attacker.pokemon_id, by_heads=True)
    failed = flips.heads == 0
    state.add_event("rebellion_check", player=player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, power=power, effect=str(key),
                    heads=flips.heads, failed=failed)
    if not failed:
        return False
    state.add_event("attack_failed", player=player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(key), reason=REBELLION_FAILED, power=power)
    return_in_play_to_deck(state, player, attacker, power=power)
    remove_persistent_effects(state, player, attacker, RETURN_IN_PLAY_TO_DECK)
    if not res.dry_run:
        shuffle_deck(state, player, power=power)
    return True


def _finish_attack(res: Resolution, use: tuple[int, int, str, int]) -> None:
    """ワザの要素のあと: きぜつの判定の窓（同時のきぜつの原因・任意の効果の候補）→ 決定か、きぜつの処理。"""
    state = res.state
    settle_scram(res)  # v0.61: ［ずらかる］（ワザの要素のあとに残りHPが「10」になったポケモン。ワザの要素を処理しない経路（こんらん・手順 4 の失敗）も通る）
    res.trace.record(WindowOpened(Window.KO_CHECK, None))
    check_simultaneous(res)
    bonded = _destiny_bond(res)  # v0.31: 「みちづれ」
    offers = ko_prevention_offers(res)
    beams = knock_out_power_offers(res)  # v0.61: ［ファイナルビーム］
    if bonded and (offers or beams):
        raise res.question("destiny_bond_with_ko_prevention", f"{[o[1].pokemon_id for o in offers + beams]}")
    if len(offers) + len(beams) > 1:
        # v0.61: こんじょうと［ファイナルビーム］・2 匹の［ファイナルビーム］など、きぜつするときに使える特殊能力の候補が 2 つ以上（G40 と同じ問い）
        raise res.question("multiple_ko_prevention", f"{[o[1].pokemon_id for o in offers + beams]}")
    scram_restored_question(res, knocked(res))  # v0.61: きぜつの処理でかがくへんかガスの発生源が場をはなれ、［ずらかる］の力がもどる（SC2）
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
    if beams:
        # v0.61: ［ファイナルビーム］を使うかを持ち主に聞く（こんじょうと同じ続きの情報。context の "source" は「きぜつ」させたポケモン。使うを選ぶと止める場合は
        # ``unresolved_choices``。コインは答えのあと）
        owner, pokemon, instance, source = beams[0]
        cont = codec.KoCheckContinuation(use, (instance.power_key.card_id, instance.power_key.power_index))
        extra: tuple = (("source", source),)
        problem = knock_out_beam_problem(res, owner, pokemon, instance, source)
        if problem is not None:
            extra += (("unresolved_choices", (pokemon.pokemon_id,)), ("unresolved_code", problem[0]), ("unresolved_reason", problem[1]))
        codec.ko_check_decision(state, cont, player=owner, pokemon_id=pokemon.pokemon_id, kind=KNOCK_OUT_POWER, extra=extra)
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
    # v0.47: カウントされないきぜつ（なにかの化石・ピッピ人形）では、相手はサイドを取らない
    taken = {player: sum(1 for owner, pokemon in gone if owner != player and counts_as_knockout(state, pokemon)) for player in PLAYERS}
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
    _after_knockouts(res, _knock_out_all(state, gone, simultaneous=len(gone) > 1), None, candidates)


def _knock_out_all(state: GameState, gone, **how) -> list[int]:
    """きぜつした (持ち主, ポケモン) をきぜつの処理（トラッシュ）に送り、サイドを取るプレイヤーの並びを返す（きぜつ 1 匹につき相手側のプレイヤー 1 人。p.323）。
    v0.47: カウントされないきぜつ（なにかの化石・ピッピ人形。``effects.counts_as_knockout``。トラッシュの前に、場にいるうちに聞く）では、相手はサイドを取らない。"""
    prize_takers = []
    for owner, pokemon in gone:
        counted = counts_as_knockout(state, pokemon)
        PR.knock_out(state, owner, pokemon, counted=counted, **how)
        if counted:
            prize_takers.append(1 - owner)
    return prize_takers


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
    if then in (NEXT_TURN, CONTINUE_TURN) and len(queue) > 1:
        # v0.42: 特殊能力の処理のあと（1 回の使用できぜつする・場をはなれるのは 1 匹）も、両方のバトル場が空くことはない
        raise RuntimeError(f"{'ポケモンチェック' if then == NEXT_TURN else '特殊能力の処理'}のあとで両方のプレイヤーがバトル場に出そうとした（エンジンの不具合）")
    _next_promotion_or_end(res, queue, then)


def _next_promotion_or_end(res: Resolution, queue: tuple, then) -> None:
    state = res.state
    if queue:
        codec.promote_decision(state, queue[0], codec.AftermathContinuation(PROMOTE_ACTIVE, queue[1:], then))
        res.trace.record(Suspended(PROMOTE_ACTIVE, PROMOTE_ACTIVE, queue[0]))
        return
    if then == NEXT_TURN:
        PR.pokemon_check_sleep_and_paralysis(state)  # ポケモンチェックの 3・4 と次の番（v0.13 の部品）
    elif then == CONTINUE_TURN:
        state.phase = Phase.MAIN  # v0.42: 特殊能力の処理のあと。番は終わらない（p.311・p.323）
    else:
        _end_turn(res)


# ---------------------------------------------------------------- 特殊能力の処理のあと（v0.42。docs/power-decisions-v0.42.md 3 章）


def after_power(state: GameState, ctx: Context, *, knock_outs: bool, converted=None) -> None:
    """宣言して使う特殊能力の処理（決定への答えを含む）が終わったあと、場を整える（v0.42）。

    - HP 以上のダメージのポケモンがいれば（ゲンガーの「のろい」でダメージカウンターをのせた。カウンターの移動はワザのダメージではない。
      GR-2000-P320-COUNTER-MOVE）、ワザのあとと同じきぜつの処理（``PR.knock_out``。ログ ``knock_out`` の ``timing`` は ``"power"``）→ サイド → 勝ち負け →
      ふしちょう → バトル場に出す（``_after_knockouts``）。続きは ``CONTINUE_TURN``（終わったら番のプレイヤーの番にもどる）。こんじょう（相手のワザの
      ダメージで「きぜつ」するとき。G3〜G7）・みちづれ（ワザのあと）は候補にしない。きぜつするのは 1 匹（1 回の使用でのせるのは 1 個）
    - きぜつがなく、バトル場が空いたプレイヤーがいれば（メノクラゲの「おくびょう」で自分を手札にもどした。きぜつではないのでサイドはない）、勝ち負けの
      判定（場にポケモンがいない。p.311）→ バトル場に出す（ワザの効果で場をはなれたあとと同じ。v0.36 の RD）
    - どちらもなければ何もしない（番のプレイヤーの ``Phase.MAIN`` のまま）

    ``knock_outs`` は、その特殊能力の説明が「きぜつ」させうるか（``PowerEffect.may_knock_out``。今はのろいだけ）。偽なら HP 以上のポケモンがいても
    きぜつの処理をしない（説明が「きぜつ」させないもの（ダメージスワップ・へんなこうどうの「きぜつ」しない範囲）の確認の漏れを、不変条件で見つける。
    v0.7 の二重の確かめ）。

    渡された状態（コマンドの入口が作った複製）を変える。"""
    res = Resolution(state, catalog=ctx.catalog, trace=ctx.trace, dormant=dormant_scram(ctx.original))
    state.phase = Phase.MAIN
    if converted is not None:
        _knock_out_to_energy(res, converted)
        return
    _settle_outside_attack(res)  # v0.61: ［ずらかる］（ダメージスワップ・のろい・こっそりかみつく・「ばける」で残りHPが「10」になった）
    gone = knocked(res)
    if gone and not knock_outs:
        return  # 不変条件（場のポケモンのダメージは HP 未満）が StateIntegrityError にする
    if gone:
        if len(gone) > 1:
            raise RuntimeError(f"特殊能力の処理のあとで 2 匹以上が HP 以上（{[p.pokemon_id for _, p in gone]}。今の対応カードでは起こらない。エンジンの不具合）")
        try:
            candidates = capture_post_knockout(res, gone)
        except OpenQuestion as question:
            raise to_error(question.key, question.detail, question.error) from None
        _after_knockouts(res, _knock_out_all(state, gone, timing="power"), CONTINUE_TURN, candidates)
        return
    if any(state.players[p].active is None for p in PLAYERS):
        _next_prize_or_judge(res, (), CONTINUE_TURN, ())


def _knock_out_to_energy(res: Resolution, converted) -> None:
    """v0.59: マルマインの［エネエネ］（``effects.SelfKnockOutToEnergy``）。マルマインをきぜつの処理に送り（いちばん上のカードはトラッシュしない。ほかのカードはトラッシュ。
    ログ ``knock_out`` の ``timing`` は ``"power"``・``to_energy``。持続する効果は消える）→ そのカードをつける先のエネルギーとしてつける（``effects.attach_converted_energy``）→
    相手がサイドを取る → 勝ち負け → ふしちょう（マルマインにはない。きぜつするときの状態で写す）→ バトル場に出す → 同じ番（``CONTINUE_TURN``）。
    「きぜつ」してからエネルギーになる順番は説明の順（「みずから「きぜつ」して…エネルギー2個分になり、…つける」）。サイド・勝ち負けはそのあと（ワザのあとと同じく、
    きぜつの処理のあとにまとめる）。どの順番でも、つける先は相手のサイド・勝ち負けにかかわらないので結果は同じ。"""
    state = res.state
    found = state.find_pokemon(converted.pokemon_id)
    if found is None or found[0] != converted.owner:
        raise RuntimeError(f"［エネエネ］のポケモン {converted.pokemon_id} が使ったプレイヤーの場にいない（エンジンの不具合）")
    owner, pokemon = found
    gone = [(owner, pokemon)]
    try:
        candidates = capture_post_knockout(res, gone)
    except OpenQuestion as question:
        raise to_error(question.key, question.detail, question.error) from None
    card = pokemon.card
    counted = counts_as_knockout(state, pokemon)
    PR.knock_out(state, owner, pokemon, counted=counted, timing="power", to_energy=True)
    attach_converted_energy(state, owner, card, converted.pokemon_id, converted.target, converted.energy_type)
    _after_knockouts(res, [1 - owner] if counted else [], CONTINUE_TURN, candidates)


# ---------------------------------------------------------------- 手札からつけたエネルギーの効果のあと（v0.58。docs/stadium-reuse-special-energy-v0.58.md）


def after_energy(state: GameState, ctx: Context) -> None:
    """手札から出してポケモンにつけた特殊エネルギーの効果（レインボーエネルギーの 10 ダメージ。``SpecialEnergyEffect.may_knock_out``）のあと、場を整える（v0.58）。

    - HP 以上のダメージのポケモンがいれば（つけたポケモン 1 匹）、ワザのあとと同じきぜつの処理（ログ ``knock_out`` の ``timing`` は ``"energy"``）→ サイド →
      勝ち負け → ふしちょう → バトル場に出す（``_after_knockouts``）。続きは ``CONTINUE_TURN``（同じ番の ``Phase.MAIN``。エネルギーをつけても番は終わらない）。
      こんじょう（相手のワザのダメージで「きぜつ」するとき）・みちづれ（ワザのあと）は候補にしない。v0.42 の ``after_power`` と同じ形
    - いなければ何もしない
    渡された状態（コマンドの入口が作った複製）を変える。"""
    res = Resolution(state, catalog=ctx.catalog, trace=ctx.trace, dormant=dormant_scram(ctx.original))
    state.phase = Phase.MAIN
    _settle_outside_attack(res)  # v0.61: ［ずらかる］（レインボーエネルギーの 10 ダメージで残りHPが「10」になった）
    gone = knocked(res)
    if not gone:
        if any(state.players[p].active is None for p in PLAYERS):
            _next_prize_or_judge(res, (), CONTINUE_TURN, ())  # v0.61: ［ずらかる］でバトル場が空いた
        return
    if len(gone) > 1:
        raise RuntimeError(f"エネルギーをつけたあとで 2 匹以上が HP 以上（{[p.pokemon_id for _, p in gone]}。1 回でダメージを与えるのは 1 匹。エンジンの不具合）")
    try:
        candidates = capture_post_knockout(res, gone)
    except OpenQuestion as question:
        raise to_error(question.key, question.detail, question.error) from None
    _after_knockouts(res, _knock_out_all(state, gone, timing="energy"), CONTINUE_TURN, candidates)


# ---------------------------------------------------------------- トレーナーの使用のあと（v0.50。docs/mew-devolution-spray-v0.50.md 4 章）


def after_trainer(state: GameState, ctx: Context) -> None:
    """きぜつさせうるトレーナー（``TrainerEffect.may_knock_out``。退化スプレー）を使い終わって、カードをトラッシュしたあと、場を整える（v0.50）。

    - 退化で最大HPがのっているダメージ以下になった、番のプレイヤーのポケモン（今の番に退化した ``devolved_turn``。トレーナーのあとに HP 以上のポケモンは残らないので、
      このコマンドで退化したもの）を、ワザのあとと同じきぜつの処理（``PR.knock_out``。ログ ``knock_out`` の ``timing`` は ``"trainer"``。特殊能力の ``"power"`` と
      分ける）→ サイド → 勝ち負け → ふしちょう → バトル場に出す（``_after_knockouts``）。続きは ``CONTINUE_TURN``（終わったら番のプレイヤーの番にもどる。トレーナーを
      使っても番は終わらない。p.310）。こんじょう（相手のワザのダメージで「きぜつ」するとき）・みちづれ（ワザのあと）は候補にしない
    - ほかのポケモン（［へんしん］で退化したポケモンと同じカードとしてあつかう相手のメタモンなど）の最大HPが下がってダメージ以下になっても、ここではきぜつさせない
      （トレーナーの効果でほかのポケモンの最大HPが下がったときの判定は v0.48 の MH1。コマンドの入口が受け付けない）
    - v0.52: きぜつがなく、バトル場が空いたプレイヤーがいれば（ポケモン回収で自分のバトル場のポケモンを手札にもどした。きぜつではないのでサイドはない）、勝ち負けの判定
      （場にポケモンがいない。p.311）→ バトル場に出す（``promote_active``。ワザ・特殊能力の効果で場をはなれたあとと同じ。v0.42 の ``after_power`` と同じ形）。続きは
      ``CONTINUE_TURN``（同じ番の ``Phase.MAIN``）。トレーナーの効果の途中では出さない（使用中のカードをトラッシュしてから）
    - どちらもなければ何もしない（番のプレイヤーの ``Phase.MAIN`` のまま）

    渡された状態（コマンドの入口が作った複製）を変える。"""
    res = Resolution(state, catalog=ctx.catalog, trace=ctx.trace, dormant=dormant_scram(ctx.original))
    state.phase = Phase.MAIN
    _settle_outside_attack(res)  # v0.61: ［ずらかる］（バトル場は穴だらけ!の 10 ダメージで残りHPが「10」になった）
    # v0.57: 錯乱ジムで相手プレイヤーがかわりに使った退化スプレーは、使ったプレイヤー（番でないプレイヤー）のポケモンを退化させるので、両方のプレイヤーを見る（今の番に
    # 退化したほかのポケモンは、ワザのあとのきぜつの処理で残らない）
    # v0.61: トレーナーのダメージ（バトル場は穴だらけ!。このコマンドのログ ``trainer_damage``）で HP 以上になったポケモンも
    damaged = _trainer_damaged(state)
    gone = [(player, pokemon) for player in PLAYERS for pokemon in state.players[player].in_play()
            if (pokemon.devolved_turn == state.turn_number or pokemon.pokemon_id in damaged) and pokemon.damage >= hp_of(state, pokemon)]
    if not gone:
        # v0.56: 効果でサイドを取ったトレーナー（マチスの交渉）のあと、サイドが 0 枚のプレイヤーがいれば、勝ち負けの判定（p.311 の表。両方が 0 枚でも同じ表）
        if any(state.players[p].active is None or not state.players[p].prizes for p in PLAYERS):
            _next_prize_or_judge(res, (), CONTINUE_TURN, ())
        return
    if len(gone) > 1:
        raise RuntimeError(f"トレーナーの使用のあとで 2 匹以上が HP 以上（{[p.pokemon_id for _, p in gone]}。1 回の使用で退化するのは 1 匹。エンジンの不具合）")
    try:
        scram_restored_question(res, gone)  # v0.61
        candidates = capture_post_knockout(res, gone)
    except OpenQuestion as question:
        raise to_error(question.key, question.detail, question.error) from None
    _after_knockouts(res, _knock_out_all(state, gone, timing="trainer"), CONTINUE_TURN, candidates)


def _trainer_damaged(state: GameState) -> set[int]:
    """v0.61: 今のトレーナーの使用（最後のログ ``play_trainer`` のあと）で、トレーナーのダメージ（ログ ``trainer_damage``）を受けた場のポケモンの番号。"""
    found: set[int] = set()
    for event in reversed(state.log):
        if event["kind"] == "play_trainer":
            break
        if event["kind"] == "trainer_damage":
            found.add(event["pokemon_id"])
    return found


def _settle_outside_attack(res: Resolution) -> None:
    """v0.61: ワザの外（特殊能力・エネルギー・トレーナー・にげるのあと）の［ずらかる］の決まった時点。止めるなら ``UnsupportedError``（コマンドを受け付けない）。"""
    try:
        settle_scram(res)
    except OpenQuestion as question:
        raise to_error(question.key, question.detail, question.error) from None


def trainer_damage_stop(before: GameState, after: GameState) -> tuple[str, str] | None:
    """v0.61: トレーナーのダメージ（バトル場は穴だらけ!）を与えた結果の状態 ``after``（複製）で、使い終えたあとの処理（［ずらかる］・きぜつの写し・SC2・受け付けられない状態）が
    止まるなら (コード, 理由の文)。コインの前に、どちらの対戦ポケモンが受ける結果も確かめるのに使う（コインの結果で受け付けるかが変わらない）。状態 ``before`` は変えない。"""
    from ..effects import state_stop_after

    trial = after.clone()
    res = Resolution(trial, dormant=dormant_scram(before))
    try:
        settle_scram(res)
        damaged = _trainer_damaged(trial)
        gone = [(player, pokemon) for player in PLAYERS for pokemon in trial.players[player].in_play()
                if pokemon.pokemon_id in damaged and pokemon.damage >= hp_of(trial, pokemon)]
        scram_restored_question(res, gone)
        capture_post_knockout(res, gone, record=False)
    except OpenQuestion as question:
        error = to_error(question.key, question.detail, question.error)
        return error.code, error.message
    except UnsupportedError as error:
        return error.code, error.message
    return state_stop_after(before, trial)


def after_retreat(state: GameState, ctx: Context, player: int, retreated) -> None:
    """v0.61（docs/reactive-powers-trainer-damage-v0.61.md 3 章）: 「にげる」が成り立ったあと（入れ替えのあと）の、相手の［おとしあな］。

    はたらいている［おとしあな］（``effects.retreat_trap_powers``。相手の場の並びの順）ごとに、にげたプレイヤーがコインを 1 枚投げ（``source="power"``・ログ ``sinkhole_check``）、
    「うら」ならにげたポケモン（ベンチにもどった）に特殊能力のダメージ（弱点・抵抗力・ワザのダメージを変える効果・「とうめい」を当てはめない。受けるポケモンの受けるダメージを変える
    常にはたらく特殊能力は当てはめる。ログ ``sinkhole_damage``）。すべて処理してから［ずらかる］を確かめ（SC1: 2 つの［おとしあな］の途中で「10」を通る）、HP 以上になった
    ポケモンをきぜつの処理（ログ ``knock_out`` の ``timing`` は ``"retreat"``）→ サイド → 勝ち負け → ふしちょう → バトル場に出す → 同じ番（``CONTINUE_TURN``）。

    コインの前に止める場合（SH1・SC1）は ``engine._retreat`` が確かめ終えている。渡された状態（コマンドの入口が作った複製）を変える。"""
    res = Resolution(state, catalog=ctx.catalog, trace=ctx.trace, dormant=dormant_scram(ctx.original))
    traps = retreat_trap_powers(state, player)
    if not traps:
        return
    frame = res.open_frame(FrameKind.POWER_DAMAGE, parent=None, player=1 - player, source_pid=traps[0][1].pokemon_id, attack_key=None)
    for owner, holder, slot in traps:
        key = str(slot.key)
        flips = flip_coins(state, player, 1, source="power", effect=key, card=holder.card, pokemon_id=holder.pokemon_id)
        tails = flips.results[0] is CoinSide.TAILS
        state.add_event("sinkhole_check", player=owner, pokemon=holder.card, pokemon_id=holder.pokemon_id, power=key, flipper=player,
                        target_pokemon_id=retreated.pokemon_id, result=flips.results[0].value)
        if not tails or retreated.damage >= hp_of(state, retreated):
            continue  # 「うら」でない・もう HP 以上（処理の対象がない。p.309）
        amount, applied = received_power_damage(state, player, retreated, holder, slot.effect.amount)
        before = retreated.damage
        retreated.damage += amount
        extra = {} if not applied else {"amount_before": slot.effect.amount, "received_modifiers": received_modifiers_log(applied)}
        state.add_event("sinkhole_damage", player=owner, pokemon=holder.card, pokemon_id=holder.pokemon_id, power=key, target_player=player,
                        target_pokemon=retreated.card, target_pokemon_id=retreated.pokemon_id, amount=amount, total_damage=retreated.damage,
                        knocked_out=retreated.damage >= hp_of(state, retreated), **extra)
        remove_on_damage(state, player, retreated, amount)
        track_ko(res, frame, retreated, before)
    state.phase = Phase.MAIN
    _settle_outside_attack(res)
    gone = knocked(res)
    if not gone:
        return
    try:
        scram_restored_question(res, gone)
        candidates = capture_post_knockout(res, gone)
    except OpenQuestion as question:
        raise to_error(question.key, question.detail, question.error) from None
    _after_knockouts(res, _knock_out_all(state, gone, timing="retreat"), CONTINUE_TURN, candidates)


def after_stadium(state: GameState, ctx: Context) -> None:
    """場のスタジアムの効果（v0.57。``engine._use_stadium``・``_resume_stadium``）が終わったあと、場を整える。きぜつはない（スタジアムの効果でダメージをのせるのは
    ロケット団の爆発ジムだけで、それはベンチに出す操作の中。今の写しではきぜつしない）。バトル場が空いたプレイヤーがいれば（セキチクシティジムでバトル場の「キョウの
    ポケモン」を山札にもどした。きぜつではないのでサイドはない）、勝ち負けの判定（場にポケモンがいない。p.311）→ バトル場に出す（``promote_active``）→ 同じ番
    （``CONTINUE_TURN``）。なければ番のプレイヤーの ``Phase.MAIN``。"""
    res = Resolution(state, catalog=ctx.catalog, trace=ctx.trace)
    state.phase = Phase.MAIN
    if knocked(res):
        raise RuntimeError("スタジアムの効果のあとに HP 以上のポケモンがいる（今の写しでは起こらない。エンジンの不具合）")
    if any(state.players[p].active is None for p in PLAYERS):
        _next_prize_or_judge(res, (), CONTINUE_TURN, ())


def end_turn_after_trainer(state: GameState, ctx: Context, player: int, card: int) -> None:
    """v0.56: トレーナーの説明の「あなたの番は終わりになる」（ロケット団員の「うら」）。使い終えたカードをトラッシュしたあと（``engine._finish_trainer``）に呼ぶ。ログ
    ``trainer_turn_end``（``player``・``trainer_card``）のあと、ワザ・番を終える操作と同じ番の終わりの窓（期限: ついているトレーナー → 持続する効果 → … → ログ ``turn_end``）
    → ポケモンチェック → 次の番（``_end_turn``）。ワザを使っていないので、ワザのあとのきぜつの処理はない。"""
    require_turn(state, player)
    state.add_event("trainer_turn_end", player=player, trainer_card=card)
    _end_turn(Resolution(state, catalog=ctx.catalog, trace=ctx.trace))


# ---------------------------------------------------------------- 番の終わり・ポケモンチェック

def _end_turn(res: Resolution) -> None:
    """番の終わりの窓（期限: ついているトレーナー → 持続する効果 → にげるの失敗の記録。v0.13 と同じ順番）→ ポケモンチェック。"""
    state = res.state
    close_probe(state)  # v0.62: ワザ以外で受けたこと（番の終わりの前のこのコマンドの変化。``history.close_probe``）
    res.trace.record(WindowOpened(Window.TURN_END, None))
    if not PR.expire_at_turn_end(state):  # v0.13 の経路と同じ手続き
        return  # v0.59: まきちらせ!ベトベトガスの効果が消えると受け付けられない状態になるので、対戦を止めた（``Phase.HALTED``）
    _pokemon_check(res)


def _pokemon_check(res: Resolution) -> None:
    """ポケモンチェック（p.323）。どくのきぜつのあとは、ワザのあとと同じきぜつの処理の窓（ふしちょうの写し）を通る。"""
    state = res.state
    knocked = PR.pokemon_check_poison(state)  # 始まり・2 の「どく」・両方のきぜつで止める処理（v0.13 の経路と同じ手続き）
    if knocked is None:
        return
    try:
        # v0.61: ［ずらかる］（どくのダメージで残りHPが「10」になった）・きぜつでかがくへんかガスの発生源が場をはなれて［ずらかる］の力がもどる（SC2）。ポケモンチェックは
        # どちらの番の操作でもなく、どの操作でも番は終わるので、決められないなら対戦を止める（v0.48 の MH1 と同じ形）
        settle_scram(res)
        scram_restored_question(res, knocked)
    except OpenQuestion as question:
        error = to_error(question.key, question.detail, question.error)
        PR.halt(state, PR.Halt(code=error.code, message=f"ポケモンチェックで: {error.message}",
                               references=("GR-2000-P323-POKEMON-CHECK", "docs/reactive-powers-trainer-damage-v0.61.md")))
        return
    if not knocked:
        if any(state.players[p].active is None for p in PLAYERS):
            _next_prize_or_judge(res, (), NEXT_TURN, ())  # v0.61: ［ずらかる］でバトル場が空いた（交代のあと、ポケモンチェックの 3・4 → 次の番）
            return
        PR.pokemon_check_sleep_and_paralysis(state)
        return
    candidates = capture_post_knockout(res, knocked)
    _after_knockouts(res, _knock_out_all(state, knocked, timing="pokemon_check"), NEXT_TURN, candidates)


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
    coin = carried.get("stadium_coin")
    if coin is not None and not coin[1]:
        # v0.57: クチバシティジムの「うら」の自分へのダメージの要素を、宣言のときと同じ位置に入れる（要素の位置を合わせる）
        program = with_stadium_self_damage(program, coin[0], _stadium_self_damage(state, coin[0]))
    res.attack_declared = declared  # v0.62: 受けた記録の宣言したワザ（決定のあとの要素も同じワザの記録に加える）
    fs = res.open_frame(FrameKind.ATTACK, parent=None, player=player, source_pid=pokemon_id, attack_key=key)
    run = AttackRun(res, fs, program, attack, declared=declared)
    run.carried = carried
    run.restore(carried)  # v0.31: 決定をまたいで運んだコインの結果・枠の値
    esp = carried.get("esp")
    if esp is not None:
        # v0.66: ナツメのESPのやり直しの決定。答え（やり直す・やり直さない）を当てはめて、コインを投げた要素をもう一度処理する（採った結果を使う。それまでの要素・コインは
        # くり返さない）
        if decision.kind != ESP_REDO:
            raise RuntimeError(f"ESPの続きの情報のある決定 {decision.kind} は扱わない（エンジンの不具合）")
        index = apply_esp_redo(run, tuple(esp), choices)
        if run_elements(run, index):
            return
        _finish_attack(res, cont.use)
        return
    boundary = carried.get("boundary")
    if boundary is not None:
        # v0.65: 要素と要素のあいだの決定（変わり身の術はワザの要素の前、［にげこむ］はダメージの要素のあと）。答えを処理して、その位置の要素から続ける（それまでの要素・コインは
        # 繰り返さない）
        if decision.kind == NINJA_TRICK:
            apply_ninja_trick(run, tuple(carried["tricks"]), choices)
        elif decision.kind == REACTION_SWITCH:
            apply_flee(run, tuple(carried["flee"]), choices)
        else:
            raise RuntimeError(f"要素のあいだの決定 {decision.kind} は扱わない（エンジンの不具合）")
        if run_elements(run, boundary):
            return
        _finish_attack(res, cont.use)
        return
    index = carried.get("element")  # v0.35: 決定を出した要素の位置（ダメージの要素の順番の決定。並びにダメージの要素が 2 つ以上あることがある）
    if index is None:
        index = decision_index(program, decision.kind)
    elif not (0 <= index < len(program) and program[index].decides(decision.kind)):
        raise RuntimeError(f"決定 {decision.kind} の続きの要素の位置 {index!r} が、その決定を出す要素ではない（エンジンの不具合）")
    run.index = index
    try:
        if decision.kind == BENCH_GUARD:
            resume_guarded(run, program[index], decision, choices)  # v0.65: ダメージの要素の中の［ベンチガード］の決定
        else:
            program[index].resume(run, decision, choices)
    except EspRedoOffer:
        # v0.66: 決定のあとの続きの中で説明文のコインを投げる要素は、今の写しにない（要素をもう一度処理すると決定の前の処理をくり返す）
        raise RuntimeError(f"決定 {decision.kind} のあとの続きで、ナツメのESPのやり直しを聞くコインを投げた（今の写しでは起こらない。エンジンの不具合）") from None
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
    if decision.kind == KNOCK_OUT_POWER:
        _resume_knock_out_power(res, decision, pokemon, key, choices)  # v0.61: ［ファイナルビーム］
        _knock_out_after_attack(res)
        return
    implementation, effect_definition = _offer_effect(res, state.cards[pokemon.card].card_id, power_index)
    base = {"player": owner, "pokemon": pokemon.card, "pokemon_id": pokemon_id, "power": str(key)}
    if not choices:
        state.add_event("ko_prevention_declined", **base, total_damage=pokemon.damage)
    else:
        state.add_event("ko_prevention_declared", **base, total_damage=pokemon.damage, hp=max_hp(state, pokemon))
        OFFER_ACTIONS[effect_definition.action](state, owner, pokemon, key, implementation)
    _knock_out_after_attack(res)


def _resume_knock_out_power(res: Resolution, decision, pokemon, key: PowerKey, choices) -> None:
    """v0.61（docs/reactive-powers-trainer-damage-v0.61.md 2 章）: ［ファイナルビーム］の答えのあと。使わないならログ ``knock_out_power_declined``。使うならログ
    ``knock_out_power_declared`` → 持ち主がコインを 1 枚投げる（``source="power"``）→「おもて」なら、「きぜつ」させたポケモン（決定の ``source``）に、このポケモンについている
    「水」エネルギーの数 × 20 の特殊能力のダメージ（受けるポケモンの受けるダメージを変える常にはたらく特殊能力は当てはめる。ログ ``knock_out_power_damage``）、「うら」なら
    ログ ``knock_out_power_failed``。そのあと［ずらかる］を確かめる（呼ぶ側がきぜつの処理に進む）。数えるのはきぜつの処理の前（このポケモンはまだ場にいる）。"""
    state = res.state
    owner = decision.player
    effect = state.effects.power_effect(key.card_id, state.definitions[key.card_id].powers[key.power_index])
    source_id = decision.context_value("source")
    base = {"player": owner, "pokemon": pokemon.card, "pokemon_id": pokemon.pokemon_id, "power": str(key)}
    if not choices:
        state.add_event("knock_out_power_declined", **base, total_damage=pokemon.damage)
        return
    state.add_event("knock_out_power_declared", **base, total_damage=pokemon.damage, source_pokemon_id=source_id)
    located = state.find_pokemon(source_id)
    if located is None:
        raise RuntimeError(f"［ファイナルビーム］の相手のポケモン {source_id} が場にいない（決定を待つ間に場は変わらない。エンジンの不具合）")
    source_owner, source = located
    flips = flip_coins(state, owner, 1, source="power", effect=str(key), card=pokemon.card, pokemon_id=pokemon.pokemon_id)
    result = flips.results[0]
    if result is not CoinSide.HEADS:
        state.add_event("knock_out_power_failed", **base, result=result.value)
        return
    count = effect.energy_count(state, pokemon)
    printed = count * effect.per
    amount, applied = received_power_damage(state, source_owner, source, pokemon, printed)
    source.damage += amount
    extra = {} if not applied else {"amount_before": printed, "received_modifiers": received_modifiers_log(applied)}
    state.add_event("knock_out_power_damage", **base, result=result.value, energy=count, amount=amount, target_player=source_owner,
                    target_pokemon=source.card, target_pokemon_id=source.pokemon_id, total_damage=source.damage,
                    knocked_out=source.damage >= hp_of(state, source), **extra)
    remove_on_damage(state, source_owner, source, amount)  # 「かげぶんしん」はダメージを受けたら消える
    settle_scram(res)


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
    face_up = prize_left(state, uid)  # v0.63: おもてのサイド（ロケット団参上!）を取ったら、おもての記録から除く（手札は公開にならない）
    state.players[player].hand.append(uid)
    state.add_event("take_prize", player=player, card=uid, remaining=len(prizes), **face_up_fields(face_up, "card"))
    _next_prize_or_judge(res, cont.remaining, cont.then, cont.post_knockout)


def _resume_promote(res: Resolution, decision, cont: codec.AftermathContinuation, choices) -> None:
    promote_from_bench(res.state, decision.player, choices[0])  # v0.38: ワザの効果で場をはなれたあとの交代と共通（動き・ログは v0.37 と同じ）
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
