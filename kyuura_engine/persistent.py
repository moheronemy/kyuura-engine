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
  相手の番の最後」「この相手の番の最後に…効果は消える」）。番の終わり（``procedures.expire_at_turn_end``）でポケモンチェックの前に消す
- ``RETREAT``・``SWITCH``: バトル場からベンチに戻った（p.311「ベンチに戻ったら、そのポケモンの…「持続する効果」は、
  すべて消えてなくなります」・p.322）。「にげる」に失敗した（こんらん）ポケモンはベンチに戻っていないので消えない
- ``FORCED_SWITCH``（v0.4d）: 相手のワザの効果（バタフリーの「ふきとばし」）でベンチにもどされた（p.311・p.322。p.89 の
  わるいカメールの「こうらがえし」の解説は、「ふきとばし」でベンチにもどったポケモンの持続する効果が消える例）
- ``EVOLVE``: 進化した（p.310 の進化の手順 3・p.323「「持続する効果」を受けているポケモンが進化したら…消えてなくなります」）
- ``KNOCK_OUT``: きぜつして場をはなれた（p.322「「持続する効果」を受けているポケモンが場をはなれたら…消えてなくなります」）

持続する効果は物理的なカードではないので、消えてもトラッシュには何も置かない。乱数も使わない。一度消えた効果は、
ベンチから再びバトル場に出ても復活しない（p.322）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .conditions import EVOLVE, FORCED_SWITCH, RETREAT, SWITCH
from .state import AttackBarrier, CannotAttack, DamageReduction, DestinyBond, NextTurnAttackDamage, PreventDamage, Retaliation

if TYPE_CHECKING:
    from .state import GameState, PokemonInPlay

EXPIRED = "expired"  # 効果がはたらく番の終わり（p.236・p.18 のワザ解説）
KNOCK_OUT = "knock_out"  # きぜつして場をはなれた（p.322）
REMOVAL_REASONS = (EXPIRED, RETREAT, SWITCH, EVOLVE, KNOCK_OUT, FORCED_SWITCH)  # FORCED_SWITCH は v0.4d


def add_persistent_effect(state: GameState, owner: int, pokemon: PokemonInPlay, effect, *, attack: str) -> None:
    """``pokemon``（``owner`` の場のポケモン）に、ワザ ``attack``（``AttackKey`` の文字列）による持続する効果を与える。

    ログ ``persistent_effect_added``（``player``・``pokemon``・``pokemon_id``・``persistent_effect``（種類）・``source_card``・
    ``source_player``・``active_turn``・``effect``（ワザ））。ログの ``turn`` が効果を与えた番（``created_turn``）。
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
            expired = tuple(e for e in pokemon.persistent_effects if e.active_turn == state.turn_number)
            remove_persistent_effects(state, owner, pokemon, EXPIRED, expired)


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


def next_turn_attack_damage(state: GameState, pokemon: PokemonInPlay, attack_index: int) -> NextTurnAttackDamage | None:
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
            and effect.target_attack_index == attack_index
        ):
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


def destiny_bond(state: GameState, pokemon: PokemonInPlay) -> DestinyBond | None:
    """今の番に ``pokemon`` の「みちづれ」（v0.31。第1弾のゴース）の効果がはたらいているなら、その効果。"""
    return _active(state, pokemon, DestinyBond)


def cannot_attack(state: GameState, pokemon: PokemonInPlay) -> CannotAttack | None:
    """今の番に ``pokemon`` がワザを使えない効果（v0.31。イーブイの「しっぽをふる」を受けた）がはたらいているなら、その効果。"""
    return _active(state, pokemon, CannotAttack)
