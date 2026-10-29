"""ワザによる「持続する効果」（v0.4b。p.322「11 特殊状態以外の「持続する効果」」・p.323）。

持続する効果は、ワザを受けたポケモン（「すなかけ」など）や、ワザを使ったポケモン自身（「まるまる」など）に与えられ、
そのポケモンが持つ（p.322）。特殊状態（``conditions.py``）とも、ポケモンについているトレーナーカード
（``AttachedTrainer``。物理的なカードで、トラッシュする）とも別のものなので、別の項目（``PokemonInPlay.persistent_effects``）
に持ち、付ける・消す処理もここに分ける（docs/persistent-effects-v0.4b.md）。

v0.4b で扱う効果は ``PreventDamage``（「次の相手の番、このカードはダメージを受けない。（ダメージ以外の効果は受ける）」。
トランセル・コクーンの「かたまる」。p.18・p.21 の最新の説明）だけ。v0.12 で ``Retaliation``（「次の相手の番、このカードが相手のワザに
よるダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）相手に10ダメージを与える。」。R団のファイヤーの「ほのおのかべ」。
p.82 の最新の説明。p.89 のワザ解説の「相手の番ではたらく効果」）を加えた。どちらも自分自身に与え、次の相手の番の終わりに消える。消える
契機・ログ・置き場所は同じで、はたらき方（ダメージを受けない・ダメージを受けたら与える）だけが違う（docs/temporary-attack-effects-v0.12.md）。
v0.27 で ``NextTurnAttackDamage``（「次の自分の番、このカードが使う「きりさく」のダメージは「60」になる。」。ストライクの「つるぎのまい」。
p.56・p.321 の最新の説明。p.57 のワザ解説）を加えた。自分自身に与え、はたらく番は次の自分の番（与えた番 + 2）で、その番の終わりに消える。
消える契機・ログ・置き場所はほかの効果と同じで、はたらき方（p.321 の 2 段階でワザのダメージを変える）だけが違う（docs/scyther-v0.27.md）。

消える契機（どれもログ ``persistent_effect_removed`` の ``reason``）:

- ``EXPIRED``: 効果がはたらく番（``active_turn``。「次の相手の番」。v0.27 の ``NextTurnAttackDamage`` は「次の自分の番」）の終わり（p.236・p.18 のワザ解説「効果の持続：次の
  相手の番の最後」「この相手の番の最後に…効果は消える」）。番の終わり（``procedures.expire_at_turn_end``）でポケモンチェックの前に消す。v0.34 の
  ``ReducedDamageToSource``（「なきつく」。説明が「この状態は次の自分の番の始めに消える」）は型の ``expires_at_turn_start`` で、はたらく番の次の番の
  最初（``procedures.begin_turn`` のログ ``turn_start`` のすぐあと）に消す（``remove_turn_start_expired_persistent_effects``）
- ``RETREAT``・``SWITCH``: バトル場からベンチに戻った（p.311「ベンチに戻ったら、そのポケモンの…「持続する効果」は、
  すべて消えてなくなります」・p.322）。「にげる」に失敗した（こんらん）ポケモンはベンチに戻っていないので消えない
- ``FORCED_SWITCH``（v0.4d）: 相手のワザの効果（バタフリーの「ふきとばし」）でベンチにもどされた（p.311・p.322。p.89 の
  わるいカメールの「こうらがえし」の解説は、「ふきとばし」でベンチにもどったポケモンの持続する効果が消える例）
- ``EVOLVE``: 進化した（p.310 の進化の手順 3・p.323「「持続する効果」を受けているポケモンが進化したら…消えてなくなります」）
- ``KNOCK_OUT``: きぜつして場をはなれた（p.322「「持続する効果」を受けているポケモンが場をはなれたら…消えてなくなります」）
- ``RETURN_IN_PLAY_TO_DECK``（v0.36）: ワザの効果で、そのポケモンが山札にもどって場をはなれた（キョウのドガースの「くもがくれガス」。p.322 の「場をはなれたら」。
  きぜつではない）
- ``USED``（v0.36）: 説明が「効果は1回できえる」と書く効果を使った（サンドの「すなかけ」の手順 4 のコインを投げた。``AttackCoinCheck.single_use``）

v0.45: 期限のない効果（``AttackCoinCheck.lasting``。カスミのタッツーの「スミをかける」の「それ以後」）は ``EXPIRED`` で消えない（``lasting``）。ほかの契機
（ベンチ・進化・きぜつ・山札や手札にもどる）では、ほかの効果と同じに消える。

v0.92（docs/power-suppression-lasting-locks-v0.92.md 4 章）: 期間と消える契機を明示した効果（``state.PERIOD_EFFECT_TYPES``）。期間は ``active_turn``（はたらき始める番）〜
``end_turn``（その番の終わりに ``EXPIRED``。None なら期限なし）。説明が「このカード…がバトル場をはなれたとき、この効果は消える」と書く効果（``ends_on`` の
``SOURCE_LEAVES_ACTIVE``）は、発生源がバトル場をはなれた時点で消す（``SOURCE_LEFT_ACTIVE``。``remove_source_left_effects``。場のポケモンをバトル場から動かすすべての処理が、
動かしたすぐあとに呼ぶ）。「このカードがバトル場にいるかぎり」（``while_source_active``）は問い合わせのときに発生源の場所を確かめる。前者は一度消したら、同じ番に発生源が
もどっても復活しない。既存の型（v0.91 まで）は、期間の始まり・終わりがどちらも ``active_turn``（``lasting`` なら終わりがない）の既定の値で、v0.40 の「すごむ」の SG1 などは変えない。

持続する効果は物理的なカードではないので、消えてもトラッシュには何も置かない。乱数も使わない。一度消えた効果は、
ベンチから再びバトル場に出ても復活しない（p.322）。
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from .conditions import DEVOLVE, EVOLVE, FORCED_SWITCH, RETREAT, SWITCH
from .state import (
    PERIOD_EFFECT_TYPES,
    SOURCE_LEAVES_ACTIVE,
    AttackBarrier,
    AttackCoinCheck,
    AttackEffectGuard,
    BenchAttackDamageGuard,
    BenchPowersStopped,
    BenchProtection,
    CannotAttachEnergy,
    CannotAttack,
    CannotAttackWhileSourceActive,
    CannotRetreat,
    CannotUseAttack,
    CannotUseOwnAttack,
    CannotUsePowers,
    DamageReduction,
    DealtAttackDamageReduction,
    DestinyBond,
    DoubledDamage,
    EvolutionLock,
    HalvedDamage,
    KnockOutSurvival,
    MaxHpSet,
    NextTurnAttackDamage,
    PeriodAttackCoinCheck,
    PeriodAttackLock,
    PeriodLeaveLock,
    PeriodRetreatLock,
    PowersStopped,
    PreventDamage,
    PursuitOnRetreat,
    ReceivedAttackDamageBonus,
    ReducedDamageToSource,
    ReflectShield,
    ResistanceChange,
    Retaliation,
    RetreatCostIncrease,
    StatusImmunityNextTurn,
    StatusImmunityWhileActive,
    StatusOnEnergyAttach,
    TailsDamageGuard,
    TimedDamageGuard,
    WeaknessChange,
    ZeroDamageAtLeast,
    ZeroDamageBelow,
)

if TYPE_CHECKING:
    from .state import GameState, PokemonInPlay

EXPIRED = "expired"  # 効果がはたらく番の終わり（p.236・p.18 のワザ解説）
KNOCK_OUT = "knock_out"  # きぜつして場をはなれた（p.322）
RETURN_IN_PLAY_TO_DECK = "return_in_play_to_deck"  # v0.36: ワザの効果で山札にもどって場をはなれた（p.322。くもがくれガス）
USED = "used"  # v0.36: 「効果は1回できえる」効果を使った（サンドの「すなかけ」）
# v0.42: 特殊能力・ワザの効果で手札にもどって場をはなれた（p.322。メノクラゲの「おくびょう」・エリカのピクシーの「ようせいのきせき」）
RETURN_IN_PLAY_TO_HAND = "return_in_play_to_hand"
# FORCED_SWITCH は v0.4d、RETURN_IN_PLAY_TO_DECK・USED は v0.36、RETURN_IN_PLAY_TO_HAND は v0.42
# v0.47: なにかの化石・ピッピ人形を、自分の番に自分の場からトラッシュにすてた（場をはなれた。きぜつではない。p.322）
DISCARD_FROM_PLAY = "discard_from_play"
# v0.48: 同じ種類の効果を新しく与えたので、前の効果を消した（「テクスチャー1」をもう一度受けて弱点の色が変わる・「きょだいか」をもう一度「おもて」で使う。
# 期限のない効果（``lasting``）だけ。新しい効果のログ ``persistent_effect_added`` のすぐ前に残す）
REPLACED = "replaced"
# v0.50: 退化した（p.324「19」。CR-SHELL-ATTACK-ENDS-ON-DEVOLUTION。理由の値は特殊状態の ``conditions.DEVOLVE`` と同じ）
# v0.60: 効果を持つポケモンがダメージを受けた（R団のストライクの「かげぶんしん」の「このカードがダメージを受けるか…この効果は消える」。``remove_on_damage``）
DAMAGED = "damaged"
# v0.91: ワザの効果で「その他の効果」から回復させた（ポリゴンの「オールクリア」の「おたがいの場にいるポケモン全員を「どく・ねむり・マヒ・こんらん」状態や「その他の効果」から、
# すべて回復させる」。理由の値は特殊状態の ``conditions.CURED`` と同じ）
CURED = "cured"
# v0.92: 説明が「このカード…がバトル場をはなれたとき、この効果は消える」と書く効果の発生源が、バトル場をはなれた（``remove_source_left_effects``）
SOURCE_LEFT_ACTIVE = "source_left_active"
# v0.114: 説明が「そのポケモンがバトル場に出てきたとき、この効果は消える」と書く効果を受けているポケモンが、バトル場に出た（［じっとみる］。``remove_on_entering_active``）
ENTERED_ACTIVE = "entered_active"
REMOVAL_REASONS = (EXPIRED, RETREAT, SWITCH, EVOLVE, KNOCK_OUT, FORCED_SWITCH, RETURN_IN_PLAY_TO_DECK, USED, RETURN_IN_PLAY_TO_HAND, DISCARD_FROM_PLAY,
                   REPLACED, DEVOLVE, DAMAGED, CURED, SOURCE_LEFT_ACTIVE, ENTERED_ACTIVE)


def add_persistent_effect(state: GameState, owner: int, pokemon: PokemonInPlay, effect, *, attack: str, **extra) -> None:
    """``pokemon``（``owner`` の場のポケモン）に、ワザ ``attack``（``AttackKey`` の文字列）による持続する効果を与える。

    ログ ``persistent_effect_added``（``player``・``pokemon``・``pokemon_id``・``persistent_effect``（種類）・``source_card``・
    ``source_player``・``active_turn``・``effect``（ワザ））。ログの ``turn`` が効果を与えた番（``created_turn``）。v0.35: ``extra`` はその効果の
    種類だけの項目（「あわあわ」・「ドわすれ」の使えなくなるワザの位置 ``target_attack_index``。v0.34 までの種類のログの形は変えない）。
    """
    pokemon.persistent_effects = (*pokemon.persistent_effects, effect)
    state.add_event(
        "persistent_effect_added",
        player=owner,
        pokemon=pokemon.card,
        pokemon_id=pokemon.pokemon_id,
        persistent_effect=effect.kind,
        source_card=effect.source_card,
        source_player=effect.source_player,
        active_turn=effect.active_turn,
        effect=attack,
        **extra,
    )


def remove_persistent_effects(
    state: GameState,
    owner: int,
    pokemon: PokemonInPlay,
    reason: str,
    effects: tuple | None = None,
) -> None:
    """``pokemon`` の持続する効果（``effects`` を省略したらすべて）を消す。1 つにつきログ ``persistent_effect_removed``
    （``player``・``pokemon``・``pokemon_id``・``persistent_effect``・``source_card``・``created_turn``・``active_turn``・``reason``）。
    消すものがなければ何もしない（ログも残さない）。"""
    if reason not in REMOVAL_REASONS:
        raise ValueError(f"持続する効果が消える理由 {reason!r} は {REMOVAL_REASONS} のどれか")
    removed = pokemon.persistent_effects if effects is None else effects
    if not removed:
        return
    pokemon.persistent_effects = tuple(e for e in pokemon.persistent_effects if e not in removed)
    for effect in removed:
        state.add_event(
            "persistent_effect_removed",
            player=owner,
            pokemon=pokemon.card,
            pokemon_id=pokemon.pokemon_id,
            persistent_effect=effect.kind,
            source_card=effect.source_card,
            created_turn=effect.created_turn,
            active_turn=effect.active_turn,
            reason=reason,
        )


def remove_expired_persistent_effects(state: GameState) -> None:
    """番の終わりに、効果がはたらく番（``active_turn``）が今の番の持続する効果を消す（``EXPIRED``）。

    番のプレイヤーの場（バトル場 → ベンチ）、相手の場の順（``engine._discard_expired_attachments`` と同じ順）。
    ついているトレーナーのトラッシュとは別の処理（持続する効果はカードではない）。
    """
    for owner in (state.current_player, 1 - state.current_player):
        for pokemon in state.players[owner].in_play():
            expired = tuple(e for e in pokemon.persistent_effects
                            if end_turn(e) == state.turn_number and not expires_at_turn_start(e) and not lasting(e))
            remove_persistent_effects(state, owner, pokemon, EXPIRED, expired)


def end_turn(effect) -> int | None:
    """効果がはたらく最後の番（その番の終わりに ``EXPIRED`` で消える。v0.92）。期間を明示した効果（``PERIOD_EFFECT_TYPES``）と v0.110 の ``KnockOutSurvival`` は ``end_turn``、
    期限のない効果は None、ほかの型は v0.91 までと同じ ``active_turn``（「なきつく」の次の番の始めに消える型も、はたらく番は ``active_turn``）。"""
    if lasting(effect):
        return None
    if isinstance(effect, (*PERIOD_EFFECT_TYPES, KnockOutSurvival)):
        return effect.end_turn  # v0.110: 「きぜつ」しない効果（こらえる・こうてつか）も最後の番を持つ
    return effect.active_turn


def period_active(state: GameState, effect) -> bool:
    """期間を明示した効果（v0.92）が今の番にはたらいているか: はたらき始める番〜最後の番（期限なしなら以後のすべての番）で、``while_source_active`` なら発生源（場の番号
    ``source_pokemon``）が ``source_player`` のバトル場にいる（問い合わせのときに確かめる。同じ位置の別のポケモンを発生源にしない）。"""
    turn = state.turn_number
    if turn < effect.active_turn or (effect.end_turn is not None and turn > effect.end_turn):
        return False
    if effect.while_source_active:
        active = state.players[effect.source_player].active
        return active is not None and active.pokemon_id == effect.source_pokemon
    return True


def remove_on_entering_active(state: GameState, owner: int, pokemon: PokemonInPlay) -> None:
    """v0.114: プレイヤー ``owner`` のベンチのポケモン ``pokemon`` がバトル場に出た（入れ替え・にげる・ワザの入れ替え・きぜつのあとなどに出す）。説明が「そのポケモンがバトル場に
    出てきたとき、この効果は消える」と書く効果（``BenchPowersStopped``。［じっとみる］）を理由 ``ENTERED_ACTIVE`` で消す。ベンチからバトル場に動かすすべての処理が、動かしたすぐあとに
    呼ぶ（状態だけを変え、乱数を使わない）。"""
    found = tuple(e for e in pokemon.persistent_effects if getattr(e, "bench_only", False))
    remove_persistent_effects(state, owner, pokemon, ENTERED_ACTIVE, found)


def remove_source_left_effects(state: GameState, owner: int, pokemon: PokemonInPlay) -> None:
    """v0.92: プレイヤー ``owner`` の場のポケモン ``pokemon`` がバトル場をはなれた（ベンチにもどる・きぜつ・山札や手札にもどる・トラッシュ）。説明が「このカード…がバトル場を
    はなれたとき、この効果は消える」と書く効果（``ends_on`` の ``SOURCE_LEAVES_ACTIVE``）のうち、発生源がこのポケモンのものを、受けているポケモン（おたがいの場）から理由
    ``SOURCE_LEFT_ACTIVE`` で消す。番のプレイヤーの場（バトル場 → ベンチ）、相手の場の順。発生源がはなれても消えると書かれていない効果は消さない（p.322）。バトル場から動かす
    すべての処理が、動かしたすぐあと（受けているポケモンの効果を消すのと同じ時点）に呼ぶ。動かす前の確かめの複製の上で呼んでもよい（状態だけを変え、乱数を使わない）。"""
    for side in (state.current_player, 1 - state.current_player):
        for holder in state.players[side].in_play():
            found = tuple(e for e in holder.persistent_effects
                          if isinstance(e, PERIOD_EFFECT_TYPES) and SOURCE_LEAVES_ACTIVE in e.ends_on
                          and e.source_player == owner and e.source_pokemon == pokemon.pokemon_id)
            remove_persistent_effects(state, side, holder, SOURCE_LEFT_ACTIVE, found)
            _mark_source_left(state, side, holder, owner, pokemon)


def _mark_source_left(state: GameState, side: int, holder: PokemonInPlay, owner: int, pokemon: PokemonInPlay) -> None:
    """v0.93（docs/active-leave-locks-v0.93.md 6.2 節）: 「このカードがバトル場にいるかぎり」で、発生源がはなれても消えると書かれていない「バトル場をはなれられない」効果（アリゲイツの
    「くいつく」）の発生源がはなれたら、効果を消さずに印（``source_left``）を付ける（ログ ``persistent_effect_source_left``）。はなれているあいだははたらかず、もどってきたら JC1
    （``leave_locks``）。一度付けた印は外さない。"""
    for effect in holder.persistent_effects:
        if (isinstance(effect, PeriodLeaveLock) and effect.while_source_active and SOURCE_LEAVES_ACTIVE not in effect.ends_on and not effect.source_left
                and effect.source_player == owner and effect.source_pokemon == pokemon.pokemon_id):
            marked = dataclasses.replace(effect, source_left=True)
            holder.persistent_effects = tuple(marked if e is effect else e for e in holder.persistent_effects)
            state.add_event("persistent_effect_source_left", player=side, pokemon=holder.card, pokemon_id=holder.pokemon_id, persistent_effect=effect.kind,
                            source_card=effect.source_card, source_player=effect.source_player, source_pokemon=effect.source_pokemon,
                            created_turn=effect.created_turn, active_turn=effect.active_turn)


def source_bound_effects(state: GameState, owner: int, pokemon: PokemonInPlay) -> tuple:
    """v0.92: 発生源の場所で決まる期間を明示した効果（``while_source_active``）のうち、発生源がプレイヤー ``owner`` の ``pokemon`` のもの（受けているポケモンはおたがいの場）。
    v0.93: アリゲイツの「くいつく」（``PeriodLeaveLock``）は含めない（発生源の姿が変わる問いは、はなれようとしたときの JC2。``leave_locks``）。"""
    return tuple(e for side in state.players for holder in side.in_play() for e in holder.persistent_effects
                 if isinstance(e, PERIOD_EFFECT_TYPES) and not isinstance(e, PeriodLeaveLock) and e.while_source_active and e.source_player == owner
                 and e.source_pokemon == pokemon.pokemon_id)


def _source_in_play(state: GameState, effect) -> PokemonInPlay | None:
    """効果の発生源（``source_player`` の場の番号 ``source_pokemon``）が今バトル場にいれば、そのポケモン。"""
    active = state.players[effect.source_player].active
    return active if active is not None and active.pokemon_id == effect.source_pokemon else None


def leave_locks(state: GameState, pokemon: PokemonInPlay) -> tuple[PeriodLeaveLock, ...]:
    """v0.93（docs/active-leave-locks-v0.93.md 4 章）: ``pokemon`` が今受けている、はたらいている「バトル場をはなれられない」効果（``PeriodLeaveLock``。受けた順）。

    - 期間（``period_active``）。「このカードがバトル場にいるかぎり」（くいつく）は、発生源（場の番号）が今バトル場にいるときだけ
    - 発生源が与えたあとにバトル場をはなれた（``source_left``）効果は、はなれているあいだははたらかない。同じ発生源がバトル場にもどっていたら、またはたらくかが決まらない（JC1）
    - 発生源がバトル場にいても、そのいちばん上のカードが与えたときのカードと違う（進化・退化した）なら、「このカード」がバトル場にいることになるかが決まらない（JC2）
    決められない場合は ``UnsupportedError``（呼ぶ側の状態・乱数・ログを変える前）。"""
    found = []
    for effect in pokemon.persistent_effects:
        if not isinstance(effect, PeriodLeaveLock):
            continue
        turn = state.turn_number
        if turn < effect.active_turn or (effect.end_turn is not None and turn > effect.end_turn):
            continue
        if effect.while_source_active:
            source = _source_in_play(state, effect)
            if source is None:
                continue
            # effects.py は persistent.py を読み込むので、使うときに読み込む
            from .effects import jaw_clamp_source_error

            if effect.source_left:
                raise jaw_clamp_source_error(pokemon, effect, returned=True)
            if source.card != effect.source_card:
                raise jaw_clamp_source_error(pokemon, effect, returned=False)
        found.append(effect)
    return tuple(found)


def leave_lock(state: GameState, owner: int, pokemon: PokemonInPlay, *, knock_out: bool = False) -> PeriodLeaveLock | None:
    """v0.93: プレイヤー ``owner`` の ``pokemon`` がバトル場をはなれることを止める効果（``leave_locks`` の最初のもの）。``pokemon`` が ``owner`` のバトル場にいなければ None
    （ベンチのポケモンは受けていない。受けた効果はバトル場をはなれると消える）。

    ``knock_out``: きぜつの処理ではなれる（p.323）。説明が「(「きぜつ」した時（場合）をのぞく)」と書く効果（``knockout_exception``）は止めない（発生源の場所を確かめずに除く）。
    書かない効果を受けていれば、その効果を返す（呼ぶ側が AL1 で止める）。ダメージが HP 以上になっているだけ（ワザの途中・きぜつの判定の前）は、きぜつの処理ではない
    （呼ぶ側は ``knock_out`` を渡さない）。"""
    if state.players[owner].active is not pokemon:
        return None
    if knock_out:
        if all(e.knockout_exception for e in pokemon.persistent_effects if isinstance(e, PeriodLeaveLock)):
            return None
        return next((e for e in leave_locks(state, pokemon) if not e.knockout_exception), None)
    locks = leave_locks(state, pokemon)
    return locks[0] if locks else None


def require_can_leave(state: GameState, owner: int, pokemon: PokemonInPlay, *, knock_out: bool = False) -> None:
    """v0.93: 場のポケモンをバトル場から動かす処理（「にげる」・入れ替え・手札や山札にもどす・トラッシュ・きぜつ）の、動かす直前の確かめ。止める効果が残っていれば
    ``RuntimeError``（動かす前の確かめ（``leave_lock``）の漏れ。エンジンの不具合）。"""
    lock = leave_lock(state, owner, pokemon, knock_out=knock_out)
    if lock is not None:
        raise RuntimeError(f"バトル場をはなれられない効果 {lock!r} を受けたポケモン {pokemon.pokemon_id} を動かそうとした（動かす前の確かめの漏れ。エンジンの不具合）")


def source_card_left(state: GameState, effect) -> bool:
    """v0.93（CJ1）: 発生源がはなれたら消える効果（``SOURCE_LEAVES_ACTIVE``）の発生源のポケモンはバトル場にいるが、与えたときのいちばん上のカード（「このカード」）が、そのポケモンの
    重なりにもうない（退化ではがれた）。"""
    if not isinstance(effect, PERIOD_EFFECT_TYPES) or SOURCE_LEAVES_ACTIVE not in effect.ends_on:
        return False  # v0.91 までの型（発生源の消える契機を持たない）は当たらない
    source = _source_in_play(state, effect)
    return source is not None and effect.source_card not in (source.card, *source.evolution_stack)


def require_source_card_present(state: GameState, effect, pokemon: PokemonInPlay) -> None:
    """v0.93（CJ1）: ``source_card_left`` なら、「このカード…がバトル場をはなれたとき、この効果は消える」が当てはまるかが決まらないので ``UnsupportedError``（効果を読む前）。"""
    if source_card_left(state, effect):
        # effects.py は persistent.py を読み込むので、使うときに読み込む
        from .effects import clamping_jaw_source_error

        raise clamping_jaw_source_error(pokemon, effect)


def lasting(effect) -> bool:
    """期限のない効果か（v0.45。``AttackCoinCheck.lasting``。「スミをかける」の「それ以後」。v0.48 の ``WeaknessChange``・``ResistanceChange``・``MaxHpSet`` は型で
    期限がない）。期限（``EXPIRED``）では消えない。"""
    return getattr(effect, "lasting", False) is True


def replace_persistent_effect(state: GameState, owner: int, pokemon: PokemonInPlay, effect, *, attack: str, **extra) -> None:
    """``pokemon`` に、期限のない効果（v0.48。``WeaknessChange``・``ResistanceChange``・``MaxHpSet``）を与える。同じ型の効果がすでにあれば、それを理由
    ``REPLACED`` で消してから与える（受けているポケモンに同じ型の効果は 1 つ。新しく受けた色・最大HPが今有効な値）。"""
    if not lasting(effect):
        raise ValueError(f"前の効果と置きかえるのは期限のない効果だけ（{effect!r}）")
    remove_persistent_effects(state, owner, pokemon, REPLACED, tuple(e for e in pokemon.persistent_effects if type(e) is type(effect)))
    add_persistent_effect(state, owner, pokemon, effect, attack=attack, **extra)


def expires_at_turn_start(effect) -> bool:
    """期限が「はたらく番の次の番の始め」の型か（v0.34。``ReducedDamageToSource``）。ほかの型は、はたらく番の終わり。"""
    return getattr(type(effect), "expires_at_turn_start", False)


def remove_turn_start_expired_persistent_effects(state: GameState) -> None:
    """番の最初（ログ ``turn_start`` のすぐあと）に、期限が「次の自分の番の始め」の持続する効果のうち、はたらく番が前の番のものを消す（``EXPIRED``。
    v0.34。「なきつく」の「この状態は次の自分の番の始めに消える」）。番のプレイヤーの場（バトル場 → ベンチ）、相手の場の順。"""
    for owner in (state.current_player, 1 - state.current_player):
        for pokemon in state.players[owner].in_play():
            expired = tuple(e for e in pokemon.persistent_effects if expires_at_turn_start(e) and e.active_turn < state.turn_number)
            remove_persistent_effects(state, owner, pokemon, EXPIRED, expired)


def reduced_damage_to_source(state: GameState, pokemon: PokemonInPlay) -> ReducedDamageToSource | None:
    """今の番に ``pokemon`` が「なきつく」を受けていて（v0.34。``ReducedDamageToSource``）、その効果がはたらいているなら、その効果。"""
    for effect in pokemon.persistent_effects:
        if isinstance(effect, ReducedDamageToSource) and effect.active_turn == state.turn_number:
            return effect
    return None


def damage_prevention(state: GameState, pokemon: PokemonInPlay) -> PreventDamage | None:
    """今の番に ``pokemon`` が「ダメージを受けない」状態なら、その効果（``PreventDamage``）。そうでなければ None。

    効果がはたらくのは ``active_turn``（次の相手の番）の間だけ。効果を与えた番の残り（「かたまる」はワザなので、その番は
    すぐに終わる）と、ポケモンチェック（どちらの番でもない。p.323）でははたらかない。ポケモンチェックのどくのダメージは
    ここを通さない（``procedures.pokemon_check_poison``）。
    """
    for effect in pokemon.persistent_effects:
        if isinstance(effect, PreventDamage) and effect.active_turn == state.turn_number:
            return effect
    return None


def retaliation(state: GameState, pokemon: PokemonInPlay) -> Retaliation | None:
    """今の番に ``pokemon`` の「相手のワザによるダメージを受けたとき、相手にダメージを与える」効果（``Retaliation``。v0.12 の
    「ほのおのかべ」、v0.13 の「こうらがえし」（与えるダメージは受けたダメージ。``Retaliation.basis``））がはたらいているなら、その効果。
    そうでなければ None。

    はたらくのは ``active_turn``（次の相手の番）の間だけ（``damage_prevention`` と同じ）。効果を与えた番の残り（ワザなので、その番は
    すぐに終わる）と、ポケモンチェック（どちらの番でもない。p.323）でははたらかない（ポケモンチェックのどくのダメージはワザによる
    ダメージでもない。p.321）。同じポケモンが 2 つ持つことはない（はたらく番の終わりに消えてから、次のワザを使える。不変条件で確かめて
    いる）。
    """
    for effect in pokemon.persistent_effects:
        if isinstance(effect, Retaliation) and effect.active_turn == state.turn_number:
            return effect
    return None


def effect_attack_card(state: GameState, effect) -> str:
    """持続する効果を与えたワザ（と ``target_attack_index`` のワザ）を印刷したカードの id（v0.49）。効果の ``attack_card`` があればそれ、なければ ``source_card`` の
    カードの id（v0.48 までと同じ。ワザの出どころがいちばん上のカードのとき）。"""
    return effect.attack_card if effect.attack_card is not None else state.cards[effect.source_card].card_id


def _attack_pair(state: GameState, pokemon: PokemonInPlay, key) -> tuple[str, int]:
    """ワザの (印刷したカードの id, 位置)（v0.49）。``key`` は ``AttackKey``。整数（v0.48 までの呼び方）なら、いちばん上のカードのワザの位置。"""
    if isinstance(key, int):
        return state.cards[pokemon.card].card_id, key
    return key.card_id, key.attack_index


def next_turn_attack_damage(state: GameState, pokemon: PokemonInPlay, key) -> NextTurnAttackDamage | None:
    """今の番に、``pokemon`` が使う ``attack_index`` 番目のワザ（いちばん上のカードの）のダメージを変える効果（``NextTurnAttackDamage``。
    v0.27 のストライクの「つるぎのまい」）がはたらいているなら、その効果。そうでなければ None。

    はたらくのは ``active_turn``（次の自分の番）の間だけ。効果を与えた番の残り（「つるぎのまい」はワザなので、その番はすぐに終わる）と、
    あいだの相手の番でははたらかない。変わるのは、効果を与えたカード（``source_card``。自分自身）の ``target_attack_index`` のワザだけ
    （ワザの名前では探さない。ほかのポケモンの同じ名前のワザ・このカードのほかのワザは変えない）。同じ番にはたらく効果は 1 つまで（効果を
    与えた番の 2 番あとにはたらき、その番の終わりに消える。ワザは 1 番に 1 回なので、同じ番にはたらく 2 つ目はない。不変条件で確かめている）。
    """
    for effect in pokemon.persistent_effects:
        if (
            isinstance(effect, NextTurnAttackDamage)
            and effect.active_turn == state.turn_number
            and effect.source_card == pokemon.card
            and (effect_attack_card(state, effect), effect.target_attack_index) == _attack_pair(state, pokemon, key)
        ):
            # v0.49: 変わるワザは ``AttackKey``（印刷したカードの id と位置）で探す。v0.48 までの効果（``attack_card`` が None）は、いちばん上のカードのワザ
            return effect
    return None


def _active(state: GameState, pokemon: PokemonInPlay, kind: type):
    """今の番にはたらいている ``kind`` の持続する効果（v0.31。はたらく番が今の番のもの）。なければ None。"""
    for effect in pokemon.persistent_effects:
        if isinstance(effect, kind) and effect.active_turn == state.turn_number:
            return effect
    return None


def attack_barrier(state: GameState, pokemon: PokemonInPlay) -> AttackBarrier | None:
    """今の番に ``pokemon`` が「ワザをうけない」状態（v0.31。ミュウツーの「バリアー」）なら、その効果。はたらくのは次の相手の番だけ。"""
    return _active(state, pokemon, AttackBarrier)


def damage_reduction(state: GameState, pokemon: PokemonInPlay) -> DamageReduction | None:
    """今の番に ``pokemon`` が受けるワザのダメージを減らす効果（v0.31。ピクシーの「ちいさくなる」）がはたらいているなら、その効果。"""
    return _active(state, pokemon, DamageReduction)


def zero_damage_below(state: GameState, pokemon: PokemonInPlay) -> ZeroDamageBelow | None:
    """今の番に ``pokemon`` が受けるワザのダメージを、決まった数より小さければ 0 にする効果（v0.45。イワークの「かたくなる」）がはたらいているなら、その効果。"""
    return _active(state, pokemon, ZeroDamageBelow)


def halved_damage(state: GameState, pokemon: PokemonInPlay) -> HalvedDamage | None:
    """今の番に ``pokemon`` が受けるワザのダメージを半分（切りすて）にする効果（v0.46。エリカのタマタマの「リフレクター」）がはたらいているなら、その効果。"""
    return _active(state, pokemon, HalvedDamage)


def doubled_damage(state: GameState, pokemon: PokemonInPlay) -> DoubledDamage | None:
    """今の番に ``pokemon`` が受けるワザのダメージを 2 倍にする効果（v0.75。キングラーの「もろばバサミ」）がはたらいているなら、その効果。"""
    return _active(state, pokemon, DoubledDamage)


def destiny_bond(state: GameState, pokemon: PokemonInPlay) -> DestinyBond | None:
    """今の番に ``pokemon`` の「みちづれ」（v0.31。第1弾のゴース）の効果がはたらいているなら、その効果。"""
    return _active(state, pokemon, DestinyBond)


def cannot_attack(state: GameState, pokemon: PokemonInPlay) -> CannotAttack | PeriodAttackLock | None:
    """今の番に ``pokemon`` がワザを使えない効果（v0.31。イーブイの「しっぽをふる」を受けた）がはたらいているなら、その効果。v0.92: 期間を明示した「ワザを使えない」効果
    （``PeriodAttackLock``。ヨーギラスの「にらみつける」。``period_active``）も同じ問い合わせで返す。"""
    found = _active(state, pokemon, CannotAttack)
    if found is not None:
        return found
    return next((e for e in pokemon.persistent_effects if isinstance(e, PeriodAttackLock) and period_active(state, e)), None)


def cannot_attack_while_source_active(state: GameState, pokemon: PokemonInPlay) -> CannotAttackWhileSourceActive | None:
    """今の番に ``pokemon`` がワザを使えない効果（v0.40。サカキのニドキングの「すごむ」の「次の相手の番、このカードがバトル場にいる限り、ワザを使えない」）が
    はたらいているなら、その効果。はたらく番が今の番で、効果を与えたポケモン（``source_card`` のカードがいちばん上のポケモン）が持ち主（``source_player``）の
    バトル場にいるときだけ（いないなら None。ワザを使える）。確かめるのは問い合わせのとき（ワザの宣言のとき）。"""
    effect = _active(state, pokemon, CannotAttackWhileSourceActive)
    if effect is None:
        return None
    active = state.players[effect.source_player].active
    return effect if active is not None and active.card == effect.source_card else None


def attack_locked(state: GameState, pokemon: PokemonInPlay, key) -> CannotUseOwnAttack | CannotUseAttack | None:
    """今の番に、``pokemon`` が ``attack_index`` 番目のワザ（いちばん上のカードの）を使えない効果がはたらいているなら、その効果（v0.35）。

    - ``CannotUseOwnAttack``（カスミのニョロモの「あわあわ」の「次の自分の番、このカードは「あわあわ」を使えない」）: 自分自身の効果。効果を与えた
      カード（``source_card``）がいちばん上のカードのときだけ（進化すると効果は消える。p.310・p.323）
    - ``CannotUseAttack``（「ドわすれ」の「次の相手の番、そのポケモンは、そのワザを使えない」）: 相手に与えられた効果
    どちらも、ワザの位置で探す（ワザの名前では探さない。ほかのワザは使える）。

    v0.49: ``key`` は使おうとするワザの ``AttackKey``（印刷したカードの id と位置）。使えなくなるワザも (カードの id, 位置) で持つ（``attack_card``・
    ``target_attack_card``。None ならいちばん上のカード。v0.48 までと同じ）。ワザの一覧（［サイコリンク］・［へんしん］・「ばける」・「思い出させる」）が変わっても、
    同じワザ（同じカードの同じ位置）に当てはまる。出どころ（どのポケモンが供給したか）は問わない。"""
    for effect in pokemon.persistent_effects:
        if not isinstance(effect, (CannotUseOwnAttack, CannotUseAttack)) or effect.active_turn != state.turn_number:
            continue
        if isinstance(effect, CannotUseOwnAttack):
            if effect.source_card != pokemon.card:
                continue
            target = (effect_attack_card(state, effect), effect.target_attack_index)
        else:
            target_card = effect.target_attack_card if effect.target_attack_card is not None else state.cards[pokemon.card].card_id
            target = (target_card, effect.target_attack_index)
        if target != _attack_pair(state, pokemon, key):
            continue
        return effect
    return None


def attack_coin_checks(state: GameState, pokemon: PokemonInPlay) -> tuple[AttackCoinCheck | PeriodAttackCoinCheck, ...]:
    """今の番に ``pokemon`` がワザを使うときに、p.309 の手順 4 のコインを投げる効果（v0.36。``AttackCoinCheck``。「すなかけ」・「えんまく」など）のうち、
    はたらいているもの（はたらく番が今の番。v0.45 の期限のない効果（「スミをかける」の「それ以後」）は、はたらく番とそれ以後の番。``AttackCoinCheck.active_on``）。
    v0.36 の効果だけなら 0 か 1 つ（効果を与えたワザは前の番の 1 回だけで、効果は次の番の終わりまで）。v0.45 から、期限のない効果を受けたポケモンが
    もう 1 つの効果を受けると 2 つ以上になる（その状態でワザを使うときは AC13。``flow._attack_check_failed``）。
    v0.93: 期間を明示した手順 4 の効果（``PeriodAttackCoinCheck``。わるいアリゲイツの「かぶりつく」。``period_active``）も、受けた順に含める。その発生源の「このカード」が退化で
    はがれていたら CJ1（``require_source_card_present``）。"""
    found = []
    for effect in pokemon.persistent_effects:
        if isinstance(effect, AttackCoinCheck) and effect.active_on(state.turn_number):
            found.append(effect)
        elif isinstance(effect, PeriodAttackCoinCheck) and period_active(state, effect):
            require_source_card_present(state, effect, pokemon)
            found.append(effect)
    return tuple(found)


def reflect_shield(state: GameState, pokemon: PokemonInPlay) -> ReflectShield | None:
    """``pokemon`` の今はたらいている「リフレクトシールド」の効果（v0.83。``ReflectShield``。はたらく番が今の番）。なければ None。"""
    return next((e for e in pokemon.persistent_effects if isinstance(e, ReflectShield) and e.active_turn == state.turn_number), None)


def status_immunity_while_active(pokemon: PokemonInPlay) -> StatusImmunityWhileActive | None:
    """``pokemon`` の「きらめきタッチ」で受けた「バトル場にいるかぎり、特殊状態にならない」効果（v0.84。``StatusImmunityWhileActive``）。与えたときからはたらき、期限はない
    （バトル場をはなれると消える）。なければ None。"""
    return next((e for e in pokemon.persistent_effects if isinstance(e, StatusImmunityWhileActive)), None)


def bench_attack_damage_guard(state: GameState, pokemon: PokemonInPlay) -> BenchAttackDamageGuard | None:
    """バトル場の ``pokemon`` の、今の番にはたらく「こおりのはしら」の効果（v0.84。``BenchAttackDamageGuard``。持ち主の控えポケモンが受けるワザのダメージを無効にする）。"""
    return _active(state, pokemon, BenchAttackDamageGuard)


def zero_damage_at_least(state: GameState, pokemon: PokemonInPlay) -> ZeroDamageAtLeast | None:
    """今の番に ``pokemon`` が受けるワザのダメージが決まった数以上なら 0 にする効果（v0.84。やさしいサンダースの「パルスガード」）がはたらいているなら、その効果。"""
    return _active(state, pokemon, ZeroDamageAtLeast)


def status_immunity_next_turn(state: GameState, pokemon: PokemonInPlay) -> StatusImmunityNextTurn | None:
    """今の番に ``pokemon`` が特殊状態にならない効果（v0.85。ベイリーフの「しんぴのこな」。次の相手の番）がはたらいているなら、その効果。"""
    return _active(state, pokemon, StatusImmunityNextTurn)


def attack_effect_guard(state: GameState, pokemon: PokemonInPlay) -> AttackEffectGuard | None:
    """今の番に ``pokemon`` がワザによる「ダメージ以外の効果」を受けない効果（v0.84。やさしいカイリューの「ひかりのはどう」）がはたらいているなら、その効果。"""
    return _active(state, pokemon, AttackEffectGuard)


def tails_damage_guard(pokemon: PokemonInPlay) -> TailsDamageGuard | None:
    """``pokemon`` の「かげぶんしん」の効果（v0.60。``TailsDamageGuard``）。なければ None。与えたときからはたらき、期限はない。"""
    return next((e for e in pokemon.persistent_effects if isinstance(e, TailsDamageGuard)), None)


def timed_damage_guards(state: GameState, pokemon: PokemonInPlay) -> tuple[TimedDamageGuard, ...]:
    """v0.109: ``pokemon`` の今はたらいている、受けるときのコインでダメージを防ぐ期限つきの効果（``TimedDamageGuard``。ぬるぬる・かわす・ブリンク。はたらく番が今の番）。受けた順。
    与えた番の残りにははたらかない。「かげぶんしん」（``tails_damage_guard``）とは別の問い合わせ（互いに拾わない）。"""
    return tuple(e for e in pokemon.persistent_effects if isinstance(e, TimedDamageGuard) and e.active_turn == state.turn_number)


def knockout_survivals(state: GameState, pokemon: PokemonInPlay) -> tuple[KnockOutSurvival, ...]:
    """v0.110: ``pokemon`` の今はたらいている、残りHPがなくなっても「きぜつ」しない効果（``KnockOutSurvival``。こらえる・こうてつか。はたらき始める番〜最後の番が今の番を含む）。
    受けた順。当てはまるダメージの範囲・原因は呼ぶ側（``resolution.kernel.knockout_survivals_of``）が決める。"""
    turn = state.turn_number
    return tuple(e for e in pokemon.persistent_effects if isinstance(e, KnockOutSurvival) and e.active_turn <= turn <= e.end_turn)


def remove_on_damage(state: GameState, owner: int, pokemon: PokemonInPlay, amount: int) -> None:
    """``pokemon`` が実際にダメージを受けた（``amount`` が 0 より大きい）ときに消える持続する効果（v0.60。「かげぶんしん」の「このカードがダメージを受けるか…この効果は
    消える」）を、理由 ``damaged`` で消す。ダメージをのせるすべての処理（ワザ・特殊能力・こんらん・どく・特殊エネルギー・スタジアムのダメージ）が、のせたすぐあとに呼ぶ。
    ダメージの出どころ・だれのワザかは問わない（説明は「相手のワザによる」と限っていない）。ダメージカウンターをのせる・移す効果はダメージではない
    （GR-2000-P320-COUNTER-MOVE）ので呼ばない。0 以下（ダメージを受けなかった）なら何もしない。"""
    if amount <= 0:
        return
    found = tuple(e for e in pokemon.persistent_effects if isinstance(e, TailsDamageGuard))
    remove_persistent_effects(state, owner, pokemon, DAMAGED, found)


def max_hp_set(pokemon: PokemonInPlay) -> MaxHpSet | None:
    """``pokemon`` の最大HPを決まった数にする効果（v0.48。キョウのメタモンの「きょだいか」）。与えたときからはたらき、期限はない（バトル場をはなれる・進化で消える）。
    最大HP（``effects.max_hp``）と「はたく」のダメージ（``programs.AmountIfSelfMaxHpSet``）が、同じこの問い合わせで「きょだいか」の効果の有無を見る。"""
    return next((e for e in pokemon.persistent_effects if isinstance(e, MaxHpSet)), None)


def weakness_change(pokemon: PokemonInPlay) -> WeaknessChange | None:
    """``pokemon`` の弱点の色を変える効果（v0.48。「テクスチャー1」）。与えたときからはたらき、期限はない。"""
    return next((e for e in pokemon.persistent_effects if isinstance(e, WeaknessChange)), None)


def resistance_change(pokemon: PokemonInPlay) -> ResistanceChange | None:
    """``pokemon`` の抵抗力の色を変える効果（v0.48。「テクスチャー2」）。与えたときからはたらき、期限はない。"""
    return next((e for e in pokemon.persistent_effects if isinstance(e, ResistanceChange)), None)


def cannot_retreat(state: GameState, pokemon: PokemonInPlay) -> CannotRetreat | PeriodRetreatLock | None:
    """今の番に ``pokemon`` が「にげる」ことができない効果（v0.36。``CannotRetreat``。「アイスバーン」・「わしづかみ」を受けた）がはたらいているなら、
    その効果。v0.92: 期間を明示した「にげる」ことができない効果（``PeriodRetreatLock``。クモのす・くろいまなざし。``period_active``）も同じ問い合わせで返す。"""
    found = _active(state, pokemon, CannotRetreat)
    if found is not None:
        return found
    return next((e for e in pokemon.persistent_effects if isinstance(e, PeriodRetreatLock) and period_active(state, e)), None)


def received_attack_damage_bonuses(state: GameState, pokemon: PokemonInPlay) -> tuple[ReceivedAttackDamageBonus, ...]:
    """v0.92: 今の番に ``pokemon`` が受けるワザによるダメージを増やす効果（``ReceivedAttackDamageBonus``。いやなおと）のうち、はたらいているもの（受けた順）。重なっていれば
    それぞれがはたらく（p.323「持続する効果は重複することがある」。加算なので順番で結果は変わらない）。"""
    return tuple(e for e in pokemon.persistent_effects if isinstance(e, ReceivedAttackDamageBonus) and period_active(state, e))


def dealt_attack_damage_reductions(state: GameState, pokemon: PokemonInPlay) -> tuple[DealtAttackDamageReduction, ...]:
    """v0.108: 今の番に ``pokemon`` が使うワザによるダメージを減らす効果（``DealtAttackDamageReduction``。マイナスイオン・あまえる）のうち、はたらいているもの（受けた順）。だれが
    受けるダメージかを限らない（v0.34 の ``reduced_damage_to_source`` は「このカード」へのダメージだけを見る別の問い合わせ）。重なっていればそれぞれがはたらく（p.323。加算）。"""
    return tuple(e for e in pokemon.persistent_effects if isinstance(e, DealtAttackDamageReduction) and period_active(state, e))


def powers_use_prevented(state: GameState, pokemon: PokemonInPlay) -> CannotUsePowers | None:
    """今 ``pokemon`` が特殊能力を使うことができない効果（v0.59。``CannotUsePowers``。「ショックアイ」を受けた）がはたらいているなら、その効果。はたらくのは
    与えた番から次の相手の番（``active_turn``）の終わりまで（「次の相手の番の終わりまで」）。宣言して使う特殊能力の使用だけを止める（呼ぶ側が決める）。"""
    for effect in pokemon.persistent_effects:
        if isinstance(effect, CannotUsePowers) and effect.created_turn <= state.turn_number <= effect.active_turn:
            return effect
    return None


def powers_stopped(state: GameState, pokemon: PokemonInPlay) -> PowersStopped | BenchPowersStopped | None:
    """今 ``pokemon`` の特殊能力が「使うことができず、その効果も消え」ている効果（v0.86。``PowersStopped``。わるいモココの「スタンウェーブ」を受けた）がはたらいているなら、
    その効果。はたらくのは与えた番から、効果を与えたプレイヤーの次の番（``active_turn``）の終わりまで。宣言して使う特殊能力の使用も、常にはたらく・自動的にはたらく特殊能力の
    力も止める（``continuous.power_suppressed`` の ``holder``・``continuous._suppressor``・``catalog.stopped``）。v0.114: ［じっとみる］の ``BenchPowersStopped``（与えた番だけ）も
    同じ範囲で止める。"""
    for effect in pokemon.persistent_effects:
        if isinstance(effect, (PowersStopped, BenchPowersStopped)) and effect.created_turn <= state.turn_number <= effect.active_turn:
            return effect
    return None


def bench_protection(state: GameState, pokemon: PokemonInPlay) -> BenchProtection | None:
    """今 ``pokemon`` が「ほのおのまもり」の効果（v0.86。``BenchProtection``。ワザによるダメージや効果を受けない）を受けているなら、その効果。はたらくのは与えた番から次の相手の番の
    終わりまで。当てはめる場所（控え・バトル場）は呼ぶ側（``kernel`` の効果の定義 ``PROTECTIVE_FLAME`` と PL1）が決める。"""
    for effect in pokemon.persistent_effects:
        if isinstance(effect, BenchProtection) and effect.created_turn <= state.turn_number <= effect.active_turn:
            return effect
    return None


def energy_attach_blocked(state: GameState, pokemon: PokemonInPlay) -> CannotAttachEnergy | None:
    """今の番に ``pokemon`` にエネルギーカードをつけることができない効果（v0.59。``CannotAttachEnergy``。「クリスタルビーム」の「おもて」）がはたらいているなら、
    その効果。はたらくのは次の相手の番だけ。"""
    return _active(state, pokemon, CannotAttachEnergy)


def attach_status_triggers(state: GameState, pokemon: PokemonInPlay) -> tuple[StatusOnEnergyAttach, ...]:
    """v0.116（docs/energy-movement-attachment-devolution-v0.116.md 4 章）: 今の番に、``pokemon`` にエネルギーカードがついたときにはたらく効果（``StatusOnEnergyAttach``。しこみどく・
    エナジーショック）。はたらくのは次の相手の番（``active_turn``）だけ。受けた順。状態を変えず、乱数を使わない。"""
    return tuple(effect for effect in pokemon.persistent_effects if isinstance(effect, StatusOnEnergyAttach) and effect.active_turn == state.turn_number)


def retreat_cost_increases(state: GameState, pokemon: PokemonInPlay) -> tuple[RetreatCostIncrease, ...]:
    """v0.118（docs/unbounded-coins-heal-allocation-v0.118.md 6 章）: 今の番に、``pokemon`` の「にげる」ときに必要なエネルギーを増やす効果（``RetreatCostIncrease``。しめつづける。受けた順）。"""
    return tuple(effect for effect in pokemon.persistent_effects if isinstance(effect, RetreatCostIncrease) and effect.active_turn == state.turn_number)


def retreat_pursuits(state: GameState, pokemon: PokemonInPlay) -> tuple[PursuitOnRetreat, ...]:
    """v0.117（docs/retreat-return-active-powers-v0.117.md 3 章）: 今の番に、``pokemon`` が「にげる」ときにはたらく効果（``PursuitOnRetreat``。おいうち。受けた順）。「にげる」の入れ替えで
    ベンチにもどると消えるので、``engine._retreat`` が入れ替えの前に写す。"""
    return tuple(effect for effect in pokemon.persistent_effects if isinstance(effect, PursuitOnRetreat) and effect.active_turn == state.turn_number)


def evolution_lock(state: GameState, pokemon: PokemonInPlay) -> EvolutionLock | None:
    """v0.116（docs 6 章）: 今の番に ``pokemon`` を手札・トレーナーの効果で進化させられない効果（``EvolutionLock``。やみのしょくしゅ）がはたらいているなら、その効果。はたらくのは
    次の相手の番だけ。ワザ・特殊能力の効果による進化は止めない（呼ぶ側の ``effects.evolution_forbidden`` の ``by_effect``）。"""
    return _active(state, pokemon, EvolutionLock)
