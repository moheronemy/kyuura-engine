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
from ..decisions import BENCH_GUARD, DAMAGE_OPTION, ENERGY_DRAIN_DISCARD, ESP_REDO, EXP_ALL_ENERGY, KNOCK_OUT_POWER, NINJA_TRICK, PROMOTE_ACTIVE, REACTION_SWITCH, SPLIT_FROM_DECK, TAKE_PRIZE
from ..coins import CoinSide, flip_coins
from .. import effects as E
from ..effects import (AttackKey, AttackUse, PowerKey, usable_ninja_tricks, attach_converted_energy, attack_rebellion_powers, counts_as_knockout, dormant_scram, max_hp,
                       received_modifiers_log, received_power_damage, retreat_trap_powers, stadium_attack_coin_available, status_at_attack_blocked)
from ..errors import IllegalActionError, UnsupportedError
from ..state import AttackEffectGuard, BenchAttackDamageGuard, BenchPowersStopped, BenchProtection, GameState, Phase, PowersStopped, StatusImmunityNextTurn, ZeroDamageAtLeast
from ..state import MARKER_COLOR, MARKER_CURSE, PERIOD_EFFECT_TYPES, KnockOutSurvival, PeriodAttackCoinCheck, PeriodLeaveLock, SecretePoison, TimedDamageGuard
from ..history import close_probe, note_used
from ..zones import face_up_fields, prize_left, promote_from_bench, return_in_play_to_deck, shuffle_deck
from ..movement import promotion_spikes_now

from . import catalog as C
from . import codec
from . import preflight as P
from . import v013_checks
from .contract import is_contract, program_for
from .events import FrameKind, Suspended, Trace, Window, WindowOpened
from ..persistent import RETURN_IN_PLAY_TO_DECK, attack_coin_checks, destiny_bond, leave_lock, remove_on_damage, remove_persistent_effects
from .kernel import effect_ko_entries, restore_effect_ko
from .kernel import (DryRunComplete, Resolution, apply_energy_drain, apply_split, capture_post_knockout, check_simultaneous, exp_all_offers, exp_all_options, exp_all_unresolved,
                     focus_band_offers, hp_of, knock_out_beam_problem, knock_out_power_offers, knocked, knockout_survival_candidates, knockout_survival_overlap,
                     knockout_survivals_of, ko_prevention_offers, scram_restored_question, settle_scram, time_travel_due, track_ko)
from .programs import (
    resume_moves,AttackRun, EspRedoOffer, apply_esp_redo, apply_flee, apply_ninja_trick, decision_index, declare, offer_ninja_trick, program_may_fail, resume_guarded, run_elements,
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
    if cmd.attack_power:
        # v0.88: ワザといっしょに使える特殊能力（［すいりょくはつでん］）を使うことを選んだ。持たない・使えない状態・数え方が決まらないなら、状態を変える前に拒否する。v0.13 の約束で
        # 書いた実装（テスト専用）は扱わない
        E.attack_power_check(state, attacker, key)
        if is_contract(program):
            raise UnsupportedError("UNSUPPORTED_ATTACK", "v0.13 の約束で書いたワザの実装では、ワザといっしょに使う特殊能力を扱わない（エンジンの未対応）")
    if cmd.with_power is not None:
        # v0.118（docs/unbounded-coins-heal-allocation-v0.118.md 5 章）: ワザといっしょに、自分の場のポケモンの［XXXXX］を使うことを選んだ。使えないなら、状態を変える前に拒否する
        E.group_attack_power_check(state, cmd.player, attacker, key, cmd.with_power)
        if is_contract(program):
            raise UnsupportedError("UNSUPPORTED_ATTACK", "v0.13 の約束で書いたワザの実装では、ワザといっしょに使うほかのポケモンの特殊能力を扱わない（エンジンの未対応）")

    def body(res: Resolution) -> None:
        _attack_body(res, cmd.player, res.state.find_pokemon(pid)[1], key, attack, program, once, option, coin_stadium, cmd.attack_power, cmd.with_power)

    # v0.67（docs/secret-plan-preflight-v0.67.md 8 章）: v0.13 の止める関数（``v013_checks``）が知らない選択・役割がある盤面。ワザの型が ``VERIFIED`` でも、それらの安全の
    # 根拠にならないので、v0.13 の止める関数で確かめる経路（上限を超えたあとのフォールバック・比べる方法 legacy・v0.13 の約束の実装）を使わない
    unknown = legacy_unknown_features(state, attacker)
    if cmd.attack_power:
        unknown = (*unknown, "ワザといっしょに使う特殊能力")  # v0.88: v0.13 の止める関数は［すいりょくはつでん］の追加を知らない
    if cmd.with_power is not None:
        unknown = (*unknown, "ワザといっしょに使うほかのポケモンの特殊能力")  # v0.118: v0.13 の止める関数は［XXXXX］のコインと追加を知らない

    def on_limit() -> None:
        """先読みで試す結果の数が上限を超えた（途中までの結果は使わない）。v0.13 の止める関数で確かめたワザの実装なら、それで確かめる
        （止めなければ、実際の処理が自分の結果の問いを検出する）。ほかは推測で受け付けず拒否する。v0.67: v0.13 の止める関数が知らない選択・役割（お上品攻撃の
        減らす量・うらのカード）がある盤面では、v0.13 の止める関数で確かめず拒否する（試していない結果があることを、安全とみなさない）。"""
        if type(effect) not in v013_checks.VERIFIED or coin_stadium is not None or unknown:  # v0.57: クチバシティジムのコインは v0.13 の止める関数が知らない
            extra = f"（v0.13 の止める関数が知らない {'・'.join(unknown)} があるので、それでも確かめない）" if unknown and type(effect) in v013_checks.VERIFIED else ""
            raise UnsupportedError(
                "UNSUPPORTED_PREFLIGHT_LIMIT",
                f"ワザ「{attack.name_ja}」の宣言の前の先読みで試す結果の数が上限（{P.MAX_BRANCHES}）を超えた。原典で決められない場合に当たる結果が"
                f"ないことを確かめられないので扱わない{extra}",
            )
        v013_checks.check(ctx.original, use, effect, ctx.original.find_pokemon(pid)[1], ctx.trace, mode="legacy_after_limit")

    if is_contract(program) and unknown:
        raise UnsupportedError("UNSUPPORTED_LEGACY_PREFLIGHT",
                               f"v0.13 の約束で書いたワザの実装は、宣言の前に v0.13 の止める関数だけで確かめるが、その関数が知らない {'・'.join(unknown)} がある（エンジンの未対応）")
    if is_contract(program):
        # v0.13 の約束で書いた実装（v0.16b のアダプタ。contract.py）: 宣言の前の確認は実装の宣言（problem と v0.13 の止める関数）だけ。
        # resolve の中身は先読みから見えず、副作用のある resolve を何度も呼ばない（v0.13・v0.15 と同じ確認。先読みの方法によらない）
        v013_checks.check(state, use, effect, attacker, ctx.trace, mode="contract")
        body(Resolution(state, catalog=ctx.catalog, trace=ctx.trace))
        return
    if ctx.preflight == "derived":
        P.after_real_run(state, ctx.original, body, ctx.catalog, ctx.trace, on_limit)  # 実際の処理を含む
        return
    if ctx.preflight == "legacy" and type(effect) in v013_checks.VERIFIED and coin_stadium is None and not unknown:  # v0.67: 知らない選択・役割があればすべての結果を試す
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


def legacy_unknown_features(state, attacker) -> tuple[str, ...]:
    """v0.67: v0.13 の止める関数（``v013_checks``。v0.13 までの選択と役割だけを知る）が知らない、この盤面の選択・役割の名前。ないなら ()。

    - ワザを使うポケモンについているお上品攻撃（v0.66。``reduces_attack_damage``）: 減らす量をワザを使ったプレイヤーが選ぶ。v0.13 の止める関数が使う
      ``preview_attack_damage`` は減らす量を 0 として計算するので、減らした量でだけ当たる問い（CA1・返す効果・そろってのきぜつ）を見落とす
    - 場のうらのカード（v0.67。マチスの秘策）: ワザがダメージや効果を与える時におもてにし、「たねポケモン」でなければトラッシュする。v0.13 の止める関数はうらのカードの
      定義を読めず（FD1）、おもてにしたあとの結果も試さない
    - 場の［だつりょくえき］（v0.68。キョウのベトベトン）: ダメージの要素のあとにコインと持ち主の決定があり、DR8・DR13 で止める。v0.13 の止める関数は知らない
    - 場の悪・鋼エネルギー（v0.78）: ワザでないダメージの「-10」（NIP1X-010）を、v0.13 の止める関数の特殊能力のダメージの見積もりは知らない
    """
    found = []
    if any(state.effects.trainer_entry(state.cards[t.card].card_id).effect.reduces_attack_damage for t in attacker.trainers):
        found.append("お上品攻撃の減らす量")
    if state.face_down_cards:
        found.append("うらのカード")
    if any(state.card_def(uid).is_special_energy and E.special_energy_effect(state, uid).affects_damage
           for side in state.players for pokemon in side.in_play() for uid in pokemon.energy):
        # v0.78: 場の悪・鋼エネルギー（ワザのダメージの 5・7 段階・ワザでないダメージの「-10」）。v0.13 の止める関数の特殊能力のダメージの見積もり（はんげきの 10 など）は、
        # 鋼エネルギー（NIP1X-010）で減らした量を知らない
        found.append("悪・鋼エネルギー")
    if E.energy_drain_holders(state):
        # v0.68: キョウのベトベトンの［だつりょくえき］（ダメージの要素のあとのコイン・持ち主が選ぶトラッシュ・DR8・DR13）。v0.13 の止める関数は知らない
        found.append("だつりょくえき")
    if any(E.tool_effect_of(state, pokemon, (E.FocusBand, E.CounterClaw, E.ExpAll)) for side in state.players for pokemon in side.in_play()):
        # v0.81: きあいのハチマキ（きぜつの判定のコイン・FB1）・はんげきのツメ（ダメージのあとのコインとダメージカウンター）・学習装置（きぜつの判定の決定）。v0.13 の止める関数は
        # 知らない
        found.append("ワザに反応するポケモンのどうぐ")
    if E.miraculous_wind_sources(state) and any(state.card_def(uid).is_special_energy for side in state.players for pokemon in side.in_play() for uid in pokemon.energy):
        # v0.84: ［きせきのかぜ］で役割の変わった場の特殊エネルギーカード（「無色」1 個・効果なし）。v0.13 の止める関数は知らない
        found.append("きせきのかぜ")
    if any(isinstance(slot.effect, E.SleepDamageSourceOnHeads) for side in state.players for pokemon in side.in_play() for slot in E.powers_of(state, pokemon)):
        # v0.84: ［ふかふかなからだ］（ダメージの要素のあとのコインとねむり）。v0.13 の止める関数は知らない
        found.append("ふかふかなからだ")
    v084 = (BenchAttackDamageGuard, AttackEffectGuard, ZeroDamageAtLeast, StatusImmunityNextTurn)  # v0.85: しんぴのこな
    if any(isinstance(effect, v084) for side in state.players for pokemon in side.in_play() for effect in pokemon.persistent_effects):
        # v0.84: こおりのはしら（控えへのワザのダメージを無効にする）・ひかりのはどう（効果の要素を無効にする）・パルスガード（8 段階）。v0.13 の止める関数は知らない
        found.append("v0.84 の持続する効果")
    if any(isinstance(slot.effect, (E.ReturnToDeckOnHeadsAfterDamage, E.OpponentAttackEffectImmunity))
           for side in state.players for pokemon in side.in_play() for slot in E.powers_of(state, pokemon)):
        # v0.86: ［はしりさる］（ダメージの要素のあとのコインと山札にもどる）・［クリスタルボディ］（効果の要素を無効にする）。v0.13 の止める関数は知らない
        found.append("はしりさる・クリスタルボディ")
    if any(isinstance(effect, (PowersStopped, BenchProtection, BenchPowersStopped)) for side in state.players for pokemon in side.in_play()
           for effect in pokemon.persistent_effects):
        # v0.86: スタンウェーブ（特殊能力を止める）・ほのおのまもり（控えへのワザのダメージと効果を無効にする）。v0.13 の止める関数は知らない。v0.114: じっとみる
        found.append("v0.86 の持続する効果")
    v087 = (E.CoinDamageBothActivesOnAttackDamage, E.PoisonDamageSourceOnAttackDamage, E.BenchNamedFromDeckOnAttackDamage, E.OwnBenchAttackImmunityWhileActive,
            E.BenchAttackDamageImmunity, E.DamageOnOpponentPromotion, E.MoveTypeEnergyOnBenching, E.DamageOnHandBasicWhileActive)
    if any(isinstance(slot.effect, v087) for side in state.players for pokemon in side.in_play() for slot in E.powers_of(state, pokemon)):
        # v0.87: ダメージを受けたとき（［ショックボム］・［どくのたいえき］・［ぶんれつ］）・場の移動（［まきびし］・［やけのこり］・［ヒートプレート］）に反応する特殊能力と、
        # ワザから守る特殊能力（［オーロラヴェール］・［もぐる］）。v0.13 の止める関数は知らない
        found.append("v0.87 の反応・守る特殊能力")
    if any(r.kind == E.OPPONENT_POWER_SUPPRESSION for r in state.trainer_effects):
        found.append("ふしぎなガス")  # v0.87: 相手の場の特殊能力だけを止める効果（v0.13 の止める関数は知らない）
    if any(r.kind == E.ATTACK_FIELD_POWER_SUPPRESSION for r in state.trainer_effects):
        found.append("やみのはどう")  # v0.92: ワザで与えた、おたがいの場の特殊能力を止める効果（v0.13 の止める関数は知らない）
    if E.optional_damage_power_holders(state):
        # v0.119: ［シェルアーマー］（ワザによるダメージを受けるたびに、受けるポケモンの持ち主が使うかを選ぶ）。v0.13 の止める関数の見積もり（``preview_attack_damage``）は使わない計算だけを
        # 見るので、それで確かめない
        found.append("シェルアーマー")
    if any(r.kind == E.ATTACK_FIELD_WEAKNESS_IMMUNITY for r in state.trainer_effects):
        found.append("なぞのこうせん")  # v0.119: ワザで与えた、自分の場のタイプのポケモンの弱点の影響を受けない効果（v0.13 の止める関数は確かめたことがない）
    if E.continuous_powers(state, E.SetSmallAttackDamageReceived):
        found.append("かたいから")  # v0.119: 受ける 40 以下のダメージを 10 にする（0 以下に当てはめるかの HS1 を v0.13 の止める関数は知らない）
    if E.discard_protection(state):
        found.append("アレルギーほうし")  # v0.119: トラッシュのカードを動かす要素が起こらない・そのコインの AP1（v0.13 の止める関数は知らない）
    if any(isinstance(effect, SecretePoison) for side in state.players for pokemon in side.in_play() for effect in pokemon.persistent_effects):
        found.append("どくをだす")  # v0.119: 相手のワザのダメージを受けたときの、どくと控え全員へのダメージの反応（PX1 を v0.13 の止める関数は知らない）
    v093 = (PeriodLeaveLock, PeriodAttackCoinCheck)
    if any(isinstance(effect, PERIOD_EFFECT_TYPES) and not isinstance(effect, v093) for side in state.players for pokemon in side.in_play() for effect in pokemon.persistent_effects):
        # v0.92: 期間を明示した持続する効果（いやなおとの 8 段階の +20・発生源がはなれたら消える禁止）。v0.13 の止める関数は知らない
        found.append("v0.92 の持続する効果")
    if any(isinstance(effect, v093) for side in state.players for pokemon in side.in_play() for effect in pokemon.persistent_effects):
        # v0.93: 「バトル場をはなれられない」効果（入れ替え・もどす要素が起こらない・AL1〜AL3・JC1・JC2）・期間を明示した手順 4 のコイン（かぶりつく・CJ1）。v0.13 の止める関数は知らない
        found.append("v0.93 のバトル場をはなれられない効果・手順 4 のコイン")
    if any(marker.kind in (MARKER_CURSE, MARKER_COLOR) for side in state.players for pokemon in side.in_play() for marker in pokemon.markers):
        # v0.90: のろいマーカー（弱点の「×4」）・色マーカー（タイプ。CM1）。v0.13 の止める関数は、このマーカーで変わる計算と問いを確かめたことがない
        found.append("のろいマーカー・色マーカー")
    if any(isinstance(effect, TimedDamageGuard) for side in state.players for pokemon in side.in_play() for effect in pokemon.persistent_effects):
        # v0.109: 受けるときのコインでダメージを防ぐ期限つきの効果（ぬるぬる・かわす・ブリンク。受けるときのコインの両面・GO1・RF1・「うら」で受けなかったあとの Z23）。v0.13 の止める関数の
        # 見積もり（``preview_attack_damage``）は受けるときのコインを知らない（コインで受けなかった場合を試さない）ので、それで確かめない
        found.append("受けるときのコインで防ぐ期限つきの効果")
    if any(isinstance(effect, KnockOutSurvival) for side in state.players for pokemon in side.in_play() for effect in pokemon.persistent_effects):
        # v0.110: 残りHPがなくなっても「きぜつ」しない効果（こらえる・こうてつか。きぜつの判定の窓の生存・KS1・KS2・こんらんの 20 の問い）。v0.13 の止める関数は「きぜつ」しない効果を知らない
        # （HP 以上で「きぜつ」すると見積もる）ので、それで確かめない
        found.append("残りHPがなくなっても「きぜつ」しない効果")
    if any(E.evolved_from_baby(state, pokemon) or state.card_def(pokemon.card).is_baby_pokemon for side in state.players for pokemon in side.in_play()
           if not state.is_face_down(pokemon)):
        # v0.114: 場のベイビィポケモン・ベイビィから進化したポケモン（ワザの前のルールのコイン・場の分類）。v0.13 の止める関数はベイビィのルールのコインと場の分類を知らないので、
        # それで確かめない
        found.append("ベイビィポケモン")
    if E.neutral_shield_holders(state):
        # v0.103: ［ニュートラルシールド］（発生元が相手の進化ポケモンのワザのダメージと効果の要素を無効にする）。v0.13 の止める関数の見積もり（``preview_attack_damage``）は発生元で
        # 無効にするかを知らない（「ダメージを受けない」状態・バリアーだけを見る）ので、それで確かめない（情報のない経路で黙って無視しない）
        found.append("ニュートラルシールド")
    return tuple(found)


def _attack_body(res: Resolution, player: int, attacker, key: AttackKey, attack, program, once: bool = False, option=None,
                 coin_stadium: int | None = None, attack_power: bool = False, with_power: int | None = None) -> None:
    state = res.state
    if option is None or option.card == attacker.card:
        state.add_event("attack", player=player, pokemon=attacker.card, attack=attack.name_ja, attack_index=key.attack_index)
    else:
        # v0.49: ワザの出どころがワザを使うポケモンのいちばん上のカードでない（［へんしん］・「ばける」・［サイコリンク］・「思い出させる」）。ワザを印刷したカード
        # （``card``・``card_id``）・持ち方（``route``）・［サイコリンク］で供給したポケモン（``provider``）を書く。どれも表のカード（公開の情報）。ふつうのワザは v0.48 と同じ形
        extra = {"provider": option.provider} if option.provider is not None else {}
        if option.payer is not None:
            extra["payer"] = option.payer  # v0.120: 必要なエネルギーを満たしたポケモン（［にんぎょうつかい］のスリーパー）
        if option.grantors:
            extra["grantors"] = tuple(option.grantors)  # v0.120: 許可を与えた特殊能力を持つポケモン（［げんしのきおく］・［にんぎょうつかい］・［ものまね］）
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
    if attack_power:
        # v0.88（docs/type-energy-colors-v0.88.md 5.1 節）: ワザといっしょに使う特殊能力の宣言（p.311 の手順 1。ワザの宣言と同じ時点。宣言の前に確かめた）。ログ ``attack_power``
        slot = E.attack_power_slot(state, attacker, key)
        state.add_event("attack_power", player=player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, power=slot.power.name_ja,
                        power_index=slot.key.power_index, card=slot.card, effect=str(key))
        res.attack_power = True
    if with_power is not None:
        _declare_group_power(res, player, attacker, key, with_power, coin_stadium, program)
    use = (player, attacker.pokemon_id, key.card_id, key.attack_index)
    declare(program, res, player, attacker)  # v0.31: 宣言のあと・こんらんのコインの前の確認（トラッシュの時点が決まらないワザ。HC1）
    baby = baby_rule_holder(res, player)  # v0.114: ワザを受ける側のバトル場のベイビィポケモン（ベイビィポケモンのルール）
    # v0.119: ワザといっしょに使う特殊能力のうち、コインで追加を決めるもの（［XXXXX］）だけが XP1・NT1 の時点の問いにかかわる（［めいれい］の決まった量の追加はコインを投げない）
    power_coins = res.group_power is not None and res.group_power[4] is None
    if power_coins and (attack_coin_checks(state, attacker) or attack_rebellion_powers(state, attacker) or attacker.conditions.confused
                        or coin_stadium is not None or baby is not None):
        # v0.118（XP1）: ［XXXXX］のコインと、ワザの要素より先に投げるコイン（手順 4・5・ベイビィポケモンのルール・クチバシティジム）の順番、ワザが失敗したときに使ったことになるかが
        # 決まらない（コインの前。使わない答え（with_power なしの同じワザ）は止めない）
        raise res.question("group_power_coin_order", f"ポケモン {attacker.pokemon_id} のワザ {key}・［XXXXX］を持つポケモン {with_power}")
    if usable_ninja_tricks(state, 1 - player) and (attack_coin_checks(state, attacker) or attack_rebellion_powers(state, attacker)
                                                   or attacker.conditions.confused or coin_stadium is not None or baby is not None
                                                   or power_coins or E.ninja_trick_baby_candidates(state, 1 - player)):
        # v0.65（NT1）: 変わり身の術の「相手がワザを使う時」の入れ替えと、ワザの要素より先に投げるコイン（手順 4・5・クチバシティジム）の順番が決まらない（コインの前）。v0.114: ベイビィ
        # ポケモンのルールのコインも、ワザの要素より先に投げるコイン（入れ替えで控えのベイビィポケモンがバトル場に出うるなら、コインがあるかも順番で変わる）
        raise res.question("ninja_trick_attack_order", f"ポケモン {attacker.pokemon_id} のワザ・変わり身の術 {list(usable_ninja_tricks(state, 1 - player))}")
    if baby is not None and _baby_rule_failed(res, player, attacker, key, baby, coin_stadium):  # v0.114: GR-2000-P314-BABY-RULE
        _finish_attack(res, use)
        return
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


BABY_RULE_FAILED = "baby_rule"  # v0.114: ベイビィポケモンのルールのコインの「うら」で失敗したワザ（ログ attack_failed の reason）


def _declare_group_power(res: Resolution, player: int, attacker, key: AttackKey, holder_id: int, coin_stadium: int | None, program: tuple = ()) -> None:
    """v0.118（docs/unbounded-coins-heal-allocation-v0.118.md 5 章）: ワザといっしょに使う自分の場のポケモンの［XXXXX］の宣言（p.311 の手順 1。ワザの宣言と同じ時点。宣言の前に確かめた）。
    ログ ``group_attack_power``（公開）と、使った記録（プレイヤーの記録 ``GROUP_ATTACK_POWER_USED``。使った番の終わりに消える。「この番に、すでに…ほかのアンノーン「X」の…」の確かめ）を
    残し、``Resolution.group_power`` に発生源と特殊能力を置く（コインはワザのダメージの要素で投げる。``programs.group_power_coins``）。"""
    from ..state import GROUP_ATTACK_POWER_USED, TrainerTurnEffect

    state = res.state
    holder, slot = E.group_attack_power_check(state, player, attacker, key, holder_id)
    effect = slot.effect
    if not effect.uses_coins:
        # v0.119（MD1）: 決まった量の追加（［めいれい］の「そのワザによるダメージは、「+10」される」）を、相手の対戦ポケモン以外へのダメージの要素（控え・自分）のあるワザといっしょに使う。
        # 「そのワザによるダメージ」の範囲が決まらない（宣言の前。使わない同じワザは受け付ける）
        from .programs import OPP
        from .programs import Phase as ElementPhase

        others = [type(element).__name__ for element in program if getattr(element, "phase", None) is ElementPhase.DAMAGE and getattr(element, "target", None) != OPP]
        if others:
            raise res.question("command_damage_scope", f"ポケモン {attacker.pokemon_id} のワザ {key}・ほかのダメージの要素 {others}・特殊能力を持つポケモン {holder_id}")
    state.add_event("group_attack_power", player=player, pokemon=holder.card, pokemon_id=holder.pokemon_id, power=slot.power.name_ja, power_index=slot.key.power_index,
                    card=slot.card, card_id=slot.key.card_id, attacker=attacker.card, attacker_pokemon_id=attacker.pokemon_id, effect=str(key))
    if effect.records_turn_use:
        record = TrainerTurnEffect(kind=GROUP_ATTACK_POWER_USED, player=player, source_card=holder.card, card_id=slot.key.card_id, created_turn=state.turn_number,
                                   expires_turn=state.turn_number, pokemon_id=holder.pokemon_id)
        state.trainer_effects = state.trainer_effects + (record,)
        state.add_event("trainer_effect_added", player=player, effect_kind=GROUP_ATTACK_POWER_USED, trainer_card=holder.card, card_id=slot.key.card_id,
                        expires_turn=state.turn_number, pokemon_id=holder.pokemon_id, power=str(slot.key))
    # v0.119: 「おもて」の数（コインで決める追加は投げるまで None。決まった量の追加は 0。``effects.group_attack_power_modifier`` が実装ごとに量を求める）
    res.group_power = (holder.pokemon_id, holder.card, slot.key.card_id, slot.key.power_index, None if effect.uses_coins else 0)


def baby_rule_holder(res: Resolution, player: int):
    """v0.114: ワザを使うプレイヤー ``player`` の相手のバトル場のポケモンが、ベイビィポケモンのルールを持つ進化していないベイビィポケモン（``effects.is_baby_in_play``）なら、その
    ポケモン。なければ None。［へんしん］で相手のベイビィポケモンと同じカードとしてあつかわれるメタモンなら、ベイビィポケモンのルールを持つかが決まらないので止める（BX1。コインの前）。
    うらのカード（マチスの秘策）は「たねポケモン」としてあつかうので None（本当のカードの段階を読まない。コインの有無から本当のカードを漏らさない）。状態を変えない。"""
    defender = res.state.players[1 - player].active
    if defender is None:
        return None
    problem = E.transform_baby_question(res.state, defender)
    if problem is not None:
        raise problem
    return defender if E.is_baby_in_play(res.state, defender) else None


def _baby_rule_failed(res: Resolution, player: int, attacker, key: AttackKey, baby, coin_stadium: int | None) -> bool:
    """v0.114（docs/baby-rules-evolution-v0.114.md 5.2 節）: ベイビィポケモンのルール。相手のバトル場にベイビィポケモンがいるので、ワザを使うプレイヤー（``player``）が、宣言（p.309 の手順 3）の
    あと・ワザの説明の処理の前にコインを 1 枚投げる（GR-2000-P314-BABY-RULE・CR-BABY-RULE-COIN・CR-BABY-RULE-COIN-STEP）。「うら」ならワザは失敗する（ログ ``attack_failed`` の ``reason``
    ``baby_rule``。説明のダメージ・効果・説明のコインは処理しない。ワザは使ったことになり、番は終わる。GR-2000-P323-ATTACK-FAILURE）で True。

    - ルールは特殊能力ではない（CR-BABY-RULE-NOT-POWER）。特殊能力を止める効果では止まらない。ナツメのESPがやり直す説明のコインではない（``AttackRun.flip`` を通さない。ログ ``coin_flip``
      の ``source`` は ``baby_rule``）。決定・保存をまたいでも投げ直さない（ワザの要素の前に 1 度だけ投げる）
    - 宣言の前の確かめ（使えないワザ・エネルギー不足・未対応）で拒否したワザでは投げない（この関数の前に拒否している）
    - 手順 4 の効果（すなかけなど・［はんこう］）・手順 5 のこんらんのコインとの順番、「うら」のあとに手順 5 などをするかは決まらない（UQ-ATTACK-PRE-DAMAGE-COIN-ORDER。BQ1）。クチバシ
      シティジムのコインとの順番・失敗したときの自分への 10 は VM1（既存の問い。ワザの失敗の順番）。どちらもコインの前に止める"""
    state = res.state
    if attack_coin_checks(state, attacker) or attack_rebellion_powers(state, attacker) or attacker.conditions.confused:
        raise res.question("baby_rule_coin_order", f"ポケモン {attacker.pokemon_id} のワザ・相手のバトル場のベイビィポケモン {baby.pokemon_id}")
    if coin_stadium is not None:
        raise res.question("vermilion_attack_order", f"ポケモン {attacker.pokemon_id}（相手のバトル場のベイビィポケモン {baby.pokemon_id} のルールのコインでワザが失敗しうる）")
    heads = flip_coins(state, player, 1, source=BABY_RULE_FAILED, effect=str(key), card=baby.card, pokemon_id=baby.pokemon_id).results[0] is CoinSide.HEADS
    state.add_event("baby_rule_coin", player=player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(key), baby=baby.card,
                    baby_pokemon_id=baby.pokemon_id, heads=heads)
    if heads:
        return False
    state.add_event("attack_failed", player=player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(key), reason=BABY_RULE_FAILED)
    return True


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
    lock = leave_lock(state, player, attacker)
    if lock is not None:
        # v0.93: 「バトル場をはなれられない」なら、ワザは失敗する（コインの結果）が、山札にもどる部分は起こらない（山札も切らない）
        E.note_leave_prevented(state, player, attacker, lock, E.LEAVE_TO_DECK, power=power)
        return True
    return_in_play_to_deck(state, player, attacker, power=power)
    remove_persistent_effects(state, player, attacker, RETURN_IN_PLAY_TO_DECK)
    if not res.dry_run:
        shuffle_deck(state, player, power=power)
    return True


def end_attack_power_suppression(res: Resolution) -> None:
    """v0.91（docs/marker-check-field-reset-v0.91.md 7 章）: ワザを使っているあいだの特殊能力の抑止（``ATTACK_POWER_SUPPRESSION``。ポリゴンの「オールクリア」）を、ワザの処理のあと・
    きぜつの判定の前に消す（「このワザを使っているあいだ」の終わり）。1 つにつきログ ``trainer_effect_removed``（``reason`` は ``attack_end``）。消したあと（特殊能力がまたはたらく）の
    状態が受け付けられない（決められない姿・［ずらかる］の力がもどる。``effects.attack_state_stop_after``）なら、``UnsupportedError``（先読みが宣言の前に見つけ、ワザの宣言を
    受け付けない）。最大HP がのっているダメージ以下になったポケモンは、このあとのきぜつの判定がきぜつにする。抑止がなければ何もしない（ほかのワザの経路は変わらない）。"""
    from ..continuous import attack_power_suppressions

    state = res.state
    records = attack_power_suppressions(state)
    if not records:
        return
    E.poison_mist_upkeep(state)  # v0.119: 抑止のあいだに［ポイズンミスト］の特殊能力が消えていたこと（PO3）を、抑止を消す前に書く
    before = state.peek()
    # v0.110（KS1）: 「きぜつ」しない効果の候補の最大HPが抑止の終わりで変わるなら、すぐあとに残りHP 10 にする読み方（変わる前の最大HP）と結果が変わる
    survivors = {pokemon.pokemon_id: max_hp(state, pokemon) for _, pokemon in knocked(res) if knockout_survivals_of(res, pokemon)}
    state.trainer_effects = tuple(r for r in state.trainer_effects if r not in records)
    for record in records:
        state.add_event("trainer_effect_removed", player=record.player, effect_kind=record.kind, trainer_card=record.source_card, card_id=record.card_id,
                        created_turn=record.created_turn, expires_turn=record.expires_turn, reason="attack_end")
    stop = E.attack_state_stop_after(before, state)  # 最大HP が下がるのは、このあとのきぜつの判定がきぜつにする
    if stop is not None:
        raise UnsupportedError(stop[0], f"ワザを使っているあいだの特殊能力の抑止が終わると: {stop[1]}")
    for pid, hp in survivors.items():
        found = state.find_pokemon(pid)
        if found is None or max_hp(state, found[1]) != hp:
            raise res.question("knockout_survival_timing", f"ポケモン {pid}・ワザを使っているあいだの特殊能力の抑止が終わって最大HPが変わる")


def _finish_attack(res: Resolution, use: tuple[int, int, str, int]) -> None:
    """ワザの要素のあと: きぜつの判定の窓（同時のきぜつの原因・任意の効果の候補）→ 決定か、きぜつの処理。"""
    state = res.state
    end_attack_power_suppression(res)  # v0.91: 「このワザを使っているあいだ」の特殊能力の抑止の終わり（きぜつの判定の前）
    settle_scram(res)  # v0.61: ［ずらかる］（ワザの要素のあとに残りHPが「10」になったポケモン。ワザの要素を処理しない経路（こんらん・手順 4 の失敗）も通る）
    res.trace.record(WindowOpened(Window.KO_CHECK, None))
    _time_travel(res)  # v0.117: ［ときわたり］（きぜつのかわりにコインで山札にもどる。ほかのきぜつの判定の効果とかかわるなら TW2）
    _survive_knockouts(res)  # v0.110: こらえる・こうてつか（同時のきぜつ・みちづれ・こんじょうなどの候補は、「きぜつ」しなかった結果で求める）
    check_simultaneous(res)
    bonded = _destiny_bond(res)  # v0.31: 「みちづれ」
    offers = ko_prevention_offers(res)
    beams = knock_out_power_offers(res)  # v0.61: ［ファイナルビーム］
    bands = focus_band_offers(res)  # v0.81: きあいのハチマキ
    exps = exp_all_offers(res)  # v0.81: 学習装置
    if bonded and (offers or beams or bands):
        raise res.question("destiny_bond_with_ko_prevention", f"{[o[1].pokemon_id for o in offers + beams + bands]}")
    if len(offers) + len(beams) + len(bands) + len(exps) > 1:
        # v0.61: こんじょうと［ファイナルビーム］・2 匹の［ファイナルビーム］など、きぜつするときに使える特殊能力の候補が 2 つ以上（G40 と同じ問い）。v0.81: きあいのハチマキ・
        # 学習装置（きぜつの判定の窓ではたらくどうぐ）も同じ窓の候補として数える（どれを先に処理するかで結果・コインの割り当てが変わる。ポケモンの番号・学習装置をつけたポケモン）
        raise res.question("multiple_ko_prevention", f"{[o[1].pokemon_id for o in offers + beams + bands]}・学習装置 {[e[2].pokemon_id for e in exps]}")
    scram_restored_question(res, knocked(res))  # v0.61: きぜつの処理でかがくへんかガスの発生源が場をはなれ、［ずらかる］の力がもどる（SC2）
    leave_lock_knockout_question(res, knocked(res))  # v0.93: AL1（きぜつの例外を書いていない「バトル場をはなれられない」効果。こんじょう・きあいのハチマキでまぬがれない答えもある）
    # v0.31: きぜつの処理の窓の問い（P19・P32）を、先読みの範囲の中で確かめる（控えポケモンへのダメージで起こるようになった。記録は残さない。
    # 実際の写しはきぜつの処理の前に ``_knock_out_after_attack`` が行う）
    capture_post_knockout(res, knocked(res), record=False)
    if res.dry_run:
        raise DryRunComplete()
    res.horizon()
    # v0.100: ワザの効果で「きぜつ」させたポケモン（``kernel.knock_out_by_effect``）を、きぜつの判定の決定の続きの情報で運ぶ（答えのあとのきぜつの処理でも「きぜつ」する）。なければ書かない
    # （v0.99 までの決定の形は変えない）
    effect_ko = (("effect_ko", effect_ko_entries(res)),) if res.effect_ko else ()
    if offers:
        owner, pokemon, instance = offers[0]
        cont = codec.KoCheckContinuation(use, (instance.power_key.card_id, instance.power_key.power_index))
        codec.ko_check_decision(state, cont, player=owner, pokemon_id=pokemon.pokemon_id, extra=effect_ko)
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
        extra += effect_ko
        codec.ko_check_decision(state, cont, player=owner, pokemon_id=pokemon.pokemon_id, kind=KNOCK_OUT_POWER, extra=extra)
        res.trace.record(Suspended(codec.KNOCK_OUT, state.decision.kind, owner))
        return
    if bands:
        _focus_band(res, *bands[0])  # v0.81: きあいのハチマキ（決定を出さない。コインはここ）
    if exps:
        # v0.81: 学習装置（つけ替えるかを持ち主に聞く。選ぶと止めるカードは ``unresolved_choices``。つけ替えない（0 個）はいつも答えになる）
        owner, active, holder, attached = exps[0]
        unresolved, code, reason = exp_all_unresolved(state, active, holder)
        extra = (() if not unresolved else (("unresolved_choices", unresolved), ("unresolved_code", code), ("unresolved_reason", reason))) + effect_ko
        codec.exp_all_decision(state, codec.KoCheckContinuation(use, None), player=owner, options=exp_all_options(state, active), tool=attached.card,
                               holder=holder.pokemon_id, source=active.pokemon_id, extra=extra)
        res.trace.record(Suspended(codec.KNOCK_OUT, state.decision.kind, owner))
        return
    _knock_out_after_attack(res)


def _survive_knockouts(res: Resolution) -> None:
    """v0.110（docs/endure-armor-up-v0.110.md 5 章）: きぜつの判定の窓の始め（同時のきぜつ・みちづれ・こんじょう・［ファイナルビーム］・きあいのハチマキ・学習装置の候補を求める前）に、
    残りHPがなくなっても「きぜつ」しない効果（``state.KnockOutSurvival``。こらえる・こうてつか）の範囲のワザのダメージで HP 以上になったポケモン（``kernel.knockout_survival_candidates``）を
    「きぜつ」させず、のっているダメージを今有効な最大HP − 残りHP（10）にする（ログ ``knockout_survived``）。

    - ダメージは受けたまま（ワザの ``damage`` のログ・受けた記録・「ダメージを受けたとき」の効果はそのまま）。回復のイベント・反応は起こさない（残りHPを「10」にすることを回復とみなす
      根拠がない。CR-GUTS-REMAINING-HP でも kyuura は判断していない）。コインも使う選択もない。効果は消えない（期間のうちは、また「きぜつ」しない）
    - 時点は記録で決まらない（残りHPがなくなったすぐあとか、ワザのあとのきぜつの判定か）。HP 以上になったあとに同じワザの処理がこのポケモンにかかわる場面は、その処理の前に KS1 で止めて
      いる（``kernel.knockout_survival_timing``）。ここで、同じきぜつの判定の効果がこのポケモンにかかわるなら KS2（``kernel.knockout_survival_overlap``）、［ずらかる］を持つなら（すぐあとの
      読み方では、ワザの残りの処理の前に山札にもどりうる）KS1 で、状態・乱数・ログを変える前に止める。どちらもなければ、どちらの時点でも結果は同じ
    - 「きぜつ」しなかったポケモンのきぜつの原因の記録（``knocked_by``・``damage_ko``・``ko_carried``）を消す（このあとの候補・決定の続きの情報に古い記録を残さない）"""
    state = res.state
    candidates = knockout_survival_candidates(res)
    if not candidates:
        return
    knockout_survival_overlap(res, candidates)
    scram = {pokemon.pokemon_id for _, pokemon, _ in E.scram_slots(state)}
    for _, pokemon, _ in candidates:
        if pokemon.pokemon_id in scram:
            raise res.question("knockout_survival_timing", f"ポケモン {pokemon.pokemon_id}・残りHP「10」ではたらく［ずらかる］")
        if len({e.remaining_hp for e in knockout_survivals_of(res, pokemon)}) != 1:
            raise RuntimeError(f"ポケモン {pokemon.pokemon_id} の「きぜつ」しない効果の残りHPが 1 つに決まらない（文面の組は 10 だけ。エンジンの不具合）")
    for owner, pokemon, effects in candidates:
        pid = pokemon.pokemon_id
        attacker, attacker_pid = res.damage_ko[pid]
        remaining = effects[0].remaining_hp
        before = pokemon.damage
        pokemon.damage = max(0, max_hp(state, pokemon) - remaining)  # 今有効な最大HP（v0.48。こんじょう・きあいのハチマキと同じ値）
        state.add_event("knockout_survived", player=owner, pokemon=pokemon.card, pokemon_id=pid, persistent_effect=KnockOutSurvival.kind,
                        created_turns=tuple(e.created_turn for e in effects), scopes=tuple(e.scope for e in effects), attacker=attacker, attacker_pokemon_id=attacker_pid,
                        damage_before=before, total_damage=pokemon.damage, remaining_hp=remaining)
        for record in (res.knocked_by, res.damage_ko, res.ko_carried):
            record.pop(pid, None)


def _time_travel(res: Resolution) -> None:
    """v0.117（docs/retreat-return-active-powers-v0.117.md 7 章）: きぜつの判定の窓の始め（こらえる・こうてつか・同時のきぜつ・みちづれ・こんじょうなどの候補を求める前）に、［ときわたり］の
    候補（``kernel.time_travel_due``。相手のワザの分類のダメージで HP 以上・受けたときに特殊状態でない・今力が消えていない。場所は問わない）の持ち主がコインを 1 枚投げる（``source="power"``。
    ログ ``time_travel``）。「おもて」なら、きぜつの処理をせず（サイドは取られない）、重なったカード・ついているカードをすべて持ち主の山札にもどし（``zones.return_in_play_to_deck`` の
    ``power``）、持続する効果を消し、山札を切る（先読みでは切らない）。きぜつの原因の記録を消す（このあとの候補に残さない）。「うら」なら今までどおりきぜつする。

    - 止める場面（状態・乱数・ログを変える前）: 候補が 2 匹以上（コインと山札を切る順番。TW2）・同じポケモンが同じきぜつの判定の効果（こらえる・こうてつか・こんじょう・［ファイナル
      ビーム］・きあいのハチマキ・学習装置・みちづれ）にかかわる（TW2）・持ち主の番（自分のワザの中の返す効果のダメージ。すぐあとの読み方ではワザの途中で場をはなれる。TW1）・
      ［ずらかる］を持つ（TW1）。HP 以上になったあとに同じワザの処理がかかわる場面は、その処理の前に TW1 で止めている（``kernel.time_travel_timing``）"""
    state = res.state
    found = []
    for owner, pokemon in knocked(res):
        instance = time_travel_due(res, owner, pokemon)
        if instance is not None:
            found.append((owner, pokemon, instance))
    if not found:
        return
    if len(found) > 1:
        raise res.question("time_travel_overlap", f"［ときわたり］のポケモン {[p.pokemon_id for _, p, _ in found]}")
    owner, pokemon, instance = found[0]
    pid = pokemon.pokemon_id
    if owner == state.current_player:
        raise res.question("time_travel_timing", f"ポケモン {pid}・自分のワザの中の返す効果のダメージ")
    if any(p is pokemon for _, p, _ in E.scram_slots(state)):
        raise res.question("time_travel_timing", f"ポケモン {pid}・［ずらかる］")
    involved = ["こらえる・こうてつか"] if knockout_survivals_of(res, pokemon) else []
    involved += [f"こんじょう {o[1].pokemon_id}" for o in ko_prevention_offers(res, record=False) if o[1].pokemon_id == pid]
    involved += [f"ファイナルビーム {b[1].pokemon_id}" for b in knock_out_power_offers(res, record=False) if b[1].pokemon_id == pid or b[3] == pid]
    involved += [f"きあいのハチマキ {b[1].pokemon_id}" for b in focus_band_offers(res, record=False) if b[1].pokemon_id == pid]
    involved += [f"学習装置 {e[1].pokemon_id}" for e in exp_all_offers(res, record=False) if e[1].pokemon_id == pid]
    target = state.players[state.current_player].active
    bonds = [p for o, p in knocked(res) if o != state.current_player and destiny_bond(state, p) is not None]
    if bonds and target is not None and (target.pokemon_id == pid or any(p.pokemon_id == pid for p in bonds)):
        involved.append(f"みちづれ {[p.pokemon_id for p in bonds]}")
    if involved:
        raise res.question("time_travel_overlap", f"ポケモン {pid}（{' / '.join(involved)}）")
    key = str(instance.power_key)
    attacker, attacker_pid = res.damage_ko[pid]
    flips = flip_coins(state, owner, 1, source="power", effect=key, card=pokemon.card, pokemon_id=pid)
    heads = flips.results[0] is CoinSide.HEADS
    state.add_event("time_travel", player=owner, pokemon=pokemon.card, pokemon_id=pid, power=key, result=flips.results[0].value, attacker=attacker,
                    attacker_pokemon_id=attacker_pid)
    if not heads:
        return
    return_in_play_to_deck(state, owner, pokemon, power=key)
    remove_persistent_effects(state, owner, pokemon, RETURN_IN_PLAY_TO_DECK)
    if not res.dry_run:
        shuffle_deck(state, owner, power=key)
    for record in (res.knocked_by, res.damage_ko, res.ko_carried, res.ko_prevention_able):
        record.pop(pid, None)


def _focus_band(res: Resolution, owner: int, pokemon, attached, effect) -> None:
    """v0.81（docs/pokemon-tools-stadiums-v0.81.md 5 章）: きあいのハチマキ。持ち主がコインを 1 枚投げ（``source="trainer"``）、「おもて」ならのっているダメージを今有効な最大HP
    − ``remaining_hp`` にして（「きぜつ」せず、残りHPは「10」。ログ ``focus_band`` の ``survived``）、このカードをトラッシュする（``reason`` ``used``）。「うら」ならそのまま
    （きぜつの処理でほかのついているカードといっしょにトラッシュする）。そのあと［ずらかる］を確かめる（残りHPが「10」になった）。"""
    state = res.state
    flips = flip_coins(state, owner, 1, source="trainer", effect=state.cards[attached.card].card_id, card=attached.card, pokemon_id=pokemon.pokemon_id)
    survived = flips.results[0] is CoinSide.HEADS
    if survived:
        pokemon.damage = max(0, max_hp(state, pokemon) - effect.remaining_hp)
    state.add_event("focus_band", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, card=attached.card, result=flips.results[0].value,
                    survived=survived, total_damage=pokemon.damage)
    if survived:
        E.discard_attached_tool(state, pokemon, attached, E.TOOL_USED)
        settle_scram(res)


def _resume_exp_all(res: Resolution, decision, choices) -> None:
    """v0.81: 学習装置の答えのあと。選ばなければ何もしない（ログ ``exp_all_declined``。学習装置はついたまま）。選んだら、そのエネルギーカードを学習装置をつけたポケモンに
    つけ替え（手札からつける操作ではない。ログ ``tool_move_energy``）、学習装置をトラッシュする。"""
    state = res.state
    owner = decision.player
    tool = decision.context_value("tool")
    holder = state.find_pokemon(decision.context_value("holder"))
    source = state.find_pokemon(decision.context_value("source"))
    if holder is None or source is None:
        raise RuntimeError("学習装置の決定のポケモンが場にいない（決定を待つ間に場は変わらない。エンジンの不具合）")
    base = {"player": owner, "card": tool, "pokemon_id": holder[1].pokemon_id, "source_pokemon_id": source[1].pokemon_id}
    if not choices:
        state.add_event("exp_all_declined", **base)
        return
    card = choices[0]
    source[1].energy.remove(card)
    holder[1].energy.append(card)
    state.add_event("tool_move_energy", **base, energy=card)
    attached = next(a for a in holder[1].trainers if a.card == tool)
    E.discard_attached_tool(state, holder[1], attached, E.TOOL_USED)


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
    settle_replacement_poisons(state, gone)  # v0.119: 「ガスばくはつ」の記録（このワザで「きぜつ」したポケモンだけ残す）
    candidates = capture_post_knockout(res, gone)
    _after_knockouts(res, _knock_out_all(state, gone, simultaneous=len(gone) > 1), None, candidates)


def leave_lock_knockout_question(res: Resolution, gone) -> None:
    """v0.93（AL1。docs/active-leave-locks-v0.93.md 4.3 節）: きぜつの処理に送るポケモンのうち、きぜつの例外を書いていない「バトル場をはなれられない」効果（キャタピーの「からまるいと」・
    クサイハナの「ねばるみつ」）を受けたバトル場のポケモンがいれば、問い ``leave_lock_knockout``（きぜつの処理の前。ワザなら先読みが宣言の前に見つける）。例外を書いた効果
    （モンジャラ・アリゲイツ・わるいアリアドス）はきぜつの処理を止めない。"""
    for owner, pokemon in gone:
        lock = leave_lock(res.state, owner, pokemon, knock_out=True)
        if lock is not None:
            raise res.question("leave_lock_knockout", f"ポケモン {pokemon.pokemon_id}（{lock.kind}・与えた番 {lock.created_turn}）")


def _leave_lock_knockout_error(state: GameState, gone) -> UnsupportedError | None:
    """``leave_lock_knockout_question`` と同じ確かめ（``Resolution`` を持たないきぜつの処理の入口。止める理由の文を返す）。"""
    for owner, pokemon in gone:
        lock = leave_lock(state, owner, pokemon, knock_out=True)
        if lock is not None:
            return UnsupportedError(E.LEAVE_LOCK_KNOCKOUT_CODE, f"ポケモン {pokemon.pokemon_id}（{lock.kind}・与えた番 {lock.created_turn}）: {E.LEAVE_LOCK_KNOCKOUT_REASON}")
    return None


def settle_replacement_poisons(state: GameState, gone) -> None:
    """v0.119（docs/damage-reactions-poison-sleep-v0.119.md 6 章）: ワザのあとのきぜつの処理の前に、「ガスばくはつ」の記録（``state.ReplacementPoison``）のうち、ワザで HP 以上になったポケモンが
    このきぜつの処理で「きぜつ」するものを ``REPLACEMENT_KNOCKED`` にし（ログ ``replacement_poison_knocked``）、きぜつの判定で「きぜつ」しなかった（こんじょうなど）ものを消す（ログ
    ``replacement_poison_removed`` の ``reason`` ``not_knocked_out``）。"""
    from dataclasses import replace

    from ..state import REPLACEMENT_KNOCKED, REPLACEMENT_PENDING

    if not state.replacement_poisons:
        return
    knocked_ids = {pokemon.pokemon_id for _, pokemon in gone}
    kept = []
    for record in state.replacement_poisons:
        if record.status != REPLACEMENT_PENDING:
            kept.append(record)
        elif record.knocked_pokemon_id in knocked_ids:
            kept.append(replace(record, status=REPLACEMENT_KNOCKED))
            state.add_event("replacement_poison_knocked", player=record.player, pokemon_id=record.knocked_pokemon_id, effect=str(AttackKey(record.card_id, record.attack_index)))
        else:
            state.add_event("replacement_poison_removed", player=record.player, pokemon_id=record.knocked_pokemon_id,
                            effect=str(AttackKey(record.card_id, record.attack_index)), reason="not_knocked_out")
    state.replacement_poisons = tuple(kept)


def apply_replacement_poison(res: Resolution, owner: int, promoted) -> None:
    """v0.119（docs 6 章）: プレイヤー ``owner`` が控えからバトル場に出したポケモン ``promoted`` が、「ガスばくはつ」で「きぜつ」したポケモンのかわりに出てくる対戦ポケモンなら、そのワザの効果として
    「どく」状態にし、記録を消す（ログ ``replacement_poison``）。効果を受けるかは、そのワザの枠（ワザの分類。使い手はワザを使ったプレイヤー、発生元はワザを使ったポケモン。場をはなれていれば
    記録したワザを使ったときの姿）で ``reaches``（「ワザをうけない」状態・「とうめい」・［ニュートラルシールド］など）を評価する。［めんえき］は ``conditions.poison``。"""
    from ..conditions import poison
    from ..state import REPLACEMENT_KNOCKED
    from .events import FrameKind
    from .kernel import reaches

    state = res.state
    records = [r for r in state.replacement_poisons if r.player == owner and r.status == REPLACEMENT_KNOCKED]
    if not records:
        return
    if len(records) > 1:
        raise RuntimeError(f"プレイヤー {owner} のかわりの対戦ポケモンへのどくの記録が 2 つ以上ある（1 つのワザで相手の対戦ポケモンは 1 匹。エンジンの不具合）")
    record = records[0]
    state.replacement_poisons = tuple(r for r in state.replacement_poisons if r is not record)
    key = AttackKey(record.card_id, record.attack_index)
    state.add_event("replacement_poison", player=owner, pokemon=promoted.card, pokemon_id=promoted.pokemon_id, knocked_pokemon_id=record.knocked_pokemon_id,
                    effect=str(key), attacker=record.attacker_player, attacker_pokemon_id=record.attacker_pokemon_id)
    res.source_forms.setdefault(record.attacker_pokemon_id, record.attacker_evolved)
    fs = res.open_frame(FrameKind.ATTACK, parent=None, player=record.attacker_player, source_pid=record.attacker_pokemon_id, attack_key=key)
    if reaches(res, fs, owner, promoted, E.POISON):
        poison(state, owner, promoted, effect=str(key))


def _knock_out_all(state: GameState, gone, **how) -> list[int]:
    """きぜつした (持ち主, ポケモン) をきぜつの処理（トラッシュ）に送り、サイドを取るプレイヤーの並びを返す（きぜつ 1 匹につき相手側のプレイヤー 1 人。p.323）。
    v0.47: カウントされないきぜつ（なにかの化石・ピッピ人形。``effects.counts_as_knockout``。トラッシュの前に、場にいるうちに聞く）では、相手はサイドを取らない。
    v0.93: AL1 のポケモンがいれば、どれもトラッシュに送る前に止める（ワザのあとは ``_finish_attack`` が先に問いにする。ポケモンチェックは ``procedures._pokemon_check_plan`` がダメージの前に対戦を止める）。"""
    error = _leave_lock_knockout_error(state, gone)
    if error is not None:
        raise error
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
        for record in state.replacement_poisons:
            # v0.119: 勝ち負けが決まったら、かわりに出てくる対戦ポケモンはいない（架空の対象を作らない）
            state.add_event("replacement_poison_removed", player=record.player, pokemon_id=record.knocked_pokemon_id,
                            effect=str(AttackKey(record.card_id, record.attack_index)), reason="game_over")
        state.replacement_poisons = ()
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
    implementation, _ = _offer_effect(res, card_id, power_index)
    if getattr(implementation, "discard_cards_effect", None) == E.DISCARD_EFFECT_WHOLE and E.discard_protection(state):
        # v0.119: ［アレルギーほうし］で、トラッシュのこのカードが効果を受けない（使っても状態は同じなので機会を出さない。v0.74 のポケモンタワーと同じ扱い）。はたらくかは、この窓
        # （きぜつの処理・サイド・勝ち負けのあと）の場で決める。いっしょにきぜつしたパラセクトはもう場にいない
        E.log_discard_protected(state, owner, power=str(PowerKey(card_id, power_index)), card=card)
        _promotions_after_judge(res, then)
        return
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
        # v0.87: 特殊能力の効果の入れ替えへの反応（［まきびし］）のダメージで HP 以上になったポケモンも、同じきぜつの処理（同時。p.324）
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
    error = _leave_lock_knockout_error(state, gone)  # v0.93: AL1（みずから「きぜつ」する）
    if error is not None:
        raise error
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
    # v0.87: トレーナーの効果の入れ替え・手札から場に出させたことへの反応のダメージ（［まきびし］・［ヒートプレート］・爆発ジム）で HP 以上になったポケモンも
    gone = [(player, pokemon) for player in PLAYERS for pokemon in state.players[player].in_play()
            if (pokemon.devolved_turn == state.turn_number or pokemon.pokemon_id in damaged) and pokemon.damage >= hp_of(state, pokemon)]
    if not gone:
        # v0.56: 効果でサイドを取ったトレーナー（マチスの交渉）のあと、サイドが 0 枚のプレイヤーがいれば、勝ち負けの判定（p.311 の表。両方が 0 枚でも同じ表）
        if any(state.players[p].active is None or not state.players[p].prizes for p in PLAYERS):
            _next_prize_or_judge(res, (), CONTINUE_TURN, ())
        return
    if len(gone) > 1 and not all(pokemon.pokemon_id in damaged for _, pokemon in gone):
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
        elif event["kind"] in MOVEMENT_DAMAGE_EVENTS:
            found.add(event.get("target_pokemon_id", event.get("pokemon_id")))  # v0.87
    return found


# v0.87: 場の移動への反応のダメージのログ（［まきびし］・［ヒートプレート］・爆発ジム）
MOVEMENT_DAMAGE_EVENTS = frozenset({"spikes_damage", "hot_plate_damage", "stadium_damage"})


def after_effects(state: GameState, ctx: Context) -> None:
    """v0.87（docs/movement-damage-reactions-v0.87.md 4.3 節）: 手札からたねポケモンをベンチに出したあと（［ヒートプレート］・ロケット団の爆発ジムのダメージ）、場を整える。
    HP 以上のポケモンがいれば、きぜつの処理（ログ ``knock_out`` の ``timing`` は ``"entry"``。1 つの操作で起こったきぜつは同時。p.324）→ サイド → 勝ち負け → ふしちょう →
    バトル場に出す → 同じ番（``CONTINUE_TURN``）。いなければ番のプレイヤーの ``Phase.MAIN``（決定を待っていなければ）。"""
    res = Resolution(state, catalog=ctx.catalog, trace=ctx.trace, dormant=dormant_scram(ctx.original))
    if state.decision is None:
        state.phase = Phase.MAIN
    _settle_outside_attack(res)
    gone = knocked(res)
    if not gone:
        if any(state.players[p].active is None for p in PLAYERS):
            _next_prize_or_judge(res, (), CONTINUE_TURN, ())
        return
    try:
        scram_restored_question(res, gone)
        candidates = capture_post_knockout(res, gone)
    except OpenQuestion as question:
        raise to_error(question.key, question.detail, question.error) from None
    _after_knockouts(res, _knock_out_all(state, gone, timing="entry"), CONTINUE_TURN, candidates)


def settle_after_retreat(state: GameState, ctx: Context, player: int, retreated: int) -> None:
    """v0.87: 「にげる」の反応（［やけのこり］・［まきびし］・同じ時点の［おとしあな］。``reactions``）のあと、v0.61 の ``after_retreat`` の後半と同じく場を整える（［ずらかる］→
    きぜつ（``timing`` は ``"retreat"``）→ サイド → 勝ち負け → ふしちょう → バトル場に出す → 同じ番）。"""
    res = Resolution(state, catalog=ctx.catalog, trace=ctx.trace, dormant=dormant_scram(ctx.original))
    state.phase = Phase.MAIN
    _settle_outside_attack(res)
    gone = knocked(res)
    if not gone:
        if any(state.players[p].active is None for p in PLAYERS):
            _next_prize_or_judge(res, (), CONTINUE_TURN, ())
        return
    try:
        scram_restored_question(res, gone)
        candidates = capture_post_knockout(res, gone)
    except OpenQuestion as question:
        raise to_error(question.key, question.detail, question.error) from None
    _after_knockouts(res, _knock_out_all(state, gone, timing="retreat"), CONTINUE_TURN, candidates)


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


def end_turn_after_power(state: GameState, ctx: Context, player: int, power: str) -> None:
    """v0.86: 特殊能力の説明の「使ったら、自分の番は終わる」（エンテイの［おたけび］）。特殊能力の処理・続き（使用中のトレーナーを使い終える）のあとに呼ぶ。ログ ``power_turn_end``
    （``player``・``power``）のあと、トレーナーの番の終わり（``end_turn_after_trainer``）と同じ番の終わりの窓 → ポケモンチェック → 次の番。ワザを使っていないので、ワザのあとの
    きぜつの処理はない。持ち主の番でないときは使う機会で止めている（OT1）。"""
    require_turn(state, player)
    state.add_event("power_turn_end", player=player, power=power)
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
    knocked = PR.pokemon_check_poison(state)  # 始まり・1 の悪エネルギー（v0.78）・2 の「どく」・両方のきぜつで止める処理（v0.13 の経路と同じ手続き）
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
        if "move_order" in carried or "move_magma" in carried:
            # v0.87: 場の移動への反応の決定（同じ時点の反応の順番・［やけのこり］でつけ替えるカード）。答えを処理し、残りの反応を続けてから、その位置の要素から続ける
            if resume_moves(run, boundary, decision, carried, choices):
                return
        elif decision.kind == NINJA_TRICK:
            apply_ninja_trick(run, tuple(carried["tricks"]), choices)
        elif decision.kind == REACTION_SWITCH:
            apply_flee(run, tuple(carried["flee"]), choices)
        elif decision.kind == ENERGY_DRAIN_DISCARD:
            # v0.68: ［だつりょくえき］のトラッシュするカード（コインはもう投げた。送る効果はもう処理したので、続きの位置で窓を開き直しても何もしない）
            apply_energy_drain(state, tuple(carried["drain"]), choices)
        elif decision.kind == SPLIT_FROM_DECK:
            # v0.87: ［ぶんれつ］の答え（出すなら山札を切る。送る効果はもう処理した）
            apply_split(state, tuple(carried["split"]), choices)
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
        if decision.kind == BENCH_GUARD or (decision.kind == DAMAGE_OPTION and "bench_guard" in carried):
            # v0.65: ダメージの要素の中の［ベンチガード］の決定。v0.119: 控えポケモンへのダメージの［シェルアーマー］を使うかの決定（同じ続きの情報）
            resume_guarded(run, program[index], decision, choices)
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
    restore_effect_ko(res, decision.context_value("effect_ko", ()))  # v0.100: ワザの効果で「きぜつ」させたポケモン（決定の前の解決から運んだ）
    if decision.kind == EXP_ALL_ENERGY:
        _resume_exp_all(res, decision, choices)  # v0.81: 学習装置
        _knock_out_after_attack(res)
        return
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
    state = res.state
    promoted = promote_from_bench(state, decision.player, choices[0])  # v0.38: ワザの効果で場をはなれたあとの交代と共通（動き・ログは v0.37 と同じ）
    apply_replacement_poison(res, decision.player, promoted)  # v0.119: 「ガスばくはつ」で「きぜつ」したポケモンのかわりに出てくる対戦ポケモンをどく（［まきびし］の前）
    # v0.87（docs/movement-damage-reactions-v0.87.md 4.1 節）: 控えから出たポケモンへの相手の［まきびし］（その相手の番の中だけ。ポケモンチェックのあとの交代はどちらの番でもない）。
    # 同じ時点のほかの反応はない（もどったポケモンがいない）。HP 以上になったら、きぜつの処理をもう一度して、同じ続きに進む（そのあとの交代も同じ続き）
    if cont.then != NEXT_TURN and promotion_spikes_now(state, decision.player, promoted):
        _settle_outside_attack(res)
        gone = knocked(res)
        if gone:
            if cont.remaining:
                raise RuntimeError(f"［まきびし］で HP 以上になったあとに、ほかのプレイヤーの交代 {cont.remaining} が残っている（番のプレイヤーの交代は最後。エンジンの不具合）")
            try:
                scram_restored_question(res, gone)
                candidates = capture_post_knockout(res, gone)
            except OpenQuestion as question:
                raise to_error(question.key, question.detail, question.error) from None
            _after_knockouts(res, _knock_out_all(state, gone, timing="power"), cont.then, candidates)
            return
        if state.players[decision.player].active is None:
            _next_prize_or_judge(res, cont.remaining, cont.then, ())
            return
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
