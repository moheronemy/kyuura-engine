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

持続する効果は物理的なカードではないので、消えてもトラッシュには何も置かない。乱数も使わない。一度消えた効果は、
ベンチから再びバトル場に出ても復活しない（p.322）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .conditions import DEVOLVE, EVOLVE, FORCED_SWITCH, RETREAT, SWITCH
from .state import (
    AttackBarrier,
    AttackCoinCheck,
    CannotAttack,
    CannotAttackWhileSourceActive,
    CannotRetreat,
    CannotUseAttack,
    CannotUseOwnAttack,
    DamageReduction,
    DestinyBond,
    HalvedDamage,
    MaxHpSet,
    NextTurnAttackDamage,
    PreventDamage,
    ReducedDamageToSource,
    ResistanceChange,
    Retaliation,
    WeaknessChange,
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
REMOVAL_REASONS = (EXPIRED, RETREAT, SWITCH, EVOLVE, KNOCK_OUT, FORCED_SWITCH, RETURN_IN_PLAY_TO_DECK, USED, RETURN_IN_PLAY_TO_HAND, DISCARD_FROM_PLAY,
                   REPLACED, DEVOLVE)


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
                            if e.active_turn == state.turn_number and not expires_at_turn_start(e) and not lasting(e))
            remove_persistent_effects(state, owner, pokemon, EXPIRED, expired)


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


def destiny_bond(state: GameState, pokemon: PokemonInPlay) -> DestinyBond | None:
    """今の番に ``pokemon`` の「みちづれ」（v0.31。第1弾のゴース）の効果がはたらいているなら、その効果。"""
    return _active(state, pokemon, DestinyBond)


def cannot_attack(state: GameState, pokemon: PokemonInPlay) -> CannotAttack | None:
    """今の番に ``pokemon`` がワザを使えない効果（v0.31。イーブイの「しっぽをふる」を受けた）がはたらいているなら、その効果。"""
    return _active(state, pokemon, CannotAttack)


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


def attack_coin_checks(state: GameState, pokemon: PokemonInPlay) -> tuple[AttackCoinCheck, ...]:
    """今の番に ``pokemon`` がワザを使うときに、p.309 の手順 4 のコインを投げる効果（v0.36。``AttackCoinCheck``。「すなかけ」・「えんまく」など）のうち、
    はたらいているもの（はたらく番が今の番。v0.45 の期限のない効果（「スミをかける」の「それ以後」）は、はたらく番とそれ以後の番。``AttackCoinCheck.active_on``）。
    v0.36 の効果だけなら 0 か 1 つ（効果を与えたワザは前の番の 1 回だけで、効果は次の番の終わりまで）。v0.45 から、期限のない効果を受けたポケモンが
    もう 1 つの効果を受けると 2 つ以上になる（その状態でワザを使うときは AC13。``flow._attack_check_failed``）。"""
    return tuple(e for e in pokemon.persistent_effects if isinstance(e, AttackCoinCheck) and e.active_on(state.turn_number))


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


def cannot_retreat(state: GameState, pokemon: PokemonInPlay) -> CannotRetreat | None:
    """今の番に ``pokemon`` が「にげる」ことができない効果（v0.36。``CannotRetreat``。「アイスバーン」・「わしづかみ」を受けた）がはたらいているなら、
    その効果。"""
    return _active(state, pokemon, CannotRetreat)
