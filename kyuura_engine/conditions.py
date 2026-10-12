"""特殊状態（v0.3a。p.322「10 ポケモンの特殊状態」）を付ける・消す処理。

v0.3a で扱うのは「どく」だけです。ねむり・マヒ・こんらんは状態の項目もなく、付ける効果もありません。

- 特殊状態になるのはバトル場のポケモン（対戦ポケモン）だけ。ベンチのポケモンは特殊状態にならない（p.322）。
- 特殊状態のポケモンがバトル場をはなれたら（ベンチに戻ったら）、すべての特殊状態は消える（p.311・p.322）。
  にげる・ポケモンいれかえ（どちらも「ポケモンの入れ替え」。p.325）は、ここの ``clear_special_conditions`` を呼ぶ。
  きぜつしたポケモンは場からいなくなるので、特殊状態もいっしょになくなる（場のポケモンが持つため）。
- どく状態のポケモンが再びどく状態になる効果を受けても、二重のどく状態にはならない（p.322）。
- 特殊状態を与えたポケモンが場をはなれても、受けた特殊状態は消えない（p.322）。
- どくのダメージ（ポケモンチェックの 2）は、ワザによるダメージではない（p.321「8」・p.322）。エンジンの
  ``_pokemon_check`` が与える（ここではない）。

ログ:

- ``special_condition``: 特殊状態にする効果を受けた（``player``・``pokemon``・``pokemon_id``・``condition``・
  ``effect``、どくなら ``damage``。もうその状態だったときだけ ``already``）
- ``special_conditions_removed``: 特殊状態が消えた（``player``・``pokemon``・``pokemon_id``・``conditions``・``reason``）
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .state import NO_SPECIAL_CONDITIONS, Poison

if TYPE_CHECKING:
    from .state import GameState, PokemonInPlay

POISON = "poison"
# 通常のどく（p.322「ポケモンチェックのたびに、「弱点」「抵抗力」に関係なく、10ダメージを受けます。」）
NORMAL_POISON = Poison(damage=10)

# 特殊状態が消えた理由（ログの ``reason``）
RETREAT = "retreat"  # にげる（p.311）
SWITCH = "switch"  # トレーナーの効果によるポケモンの入れ替え（ポケモンいれかえ。p.322・p.325）


def poison(state: GameState, owner: int, pokemon: PokemonInPlay, *, effect: str) -> None:
    """``owner`` の対戦ポケモン ``pokemon`` を、通常のどく状態にする（p.322）。

    - もうどく状態なら、二重のどく状態にはならない（p.322「どく状態が積み重なることはありません」）。
    - p.322 は、特殊などく状態（ダメージが 20 など）のポケモンが通常のどく状態にする効果を受けたら、通常の
      どく状態になると書く。どちらの場合も結果は「通常のどく状態」なので、どく状態を ``NORMAL_POISON`` にする。
      特殊などく状態にする効果は未実装（受ける側の扱いが決まらない場合があるので、加えるときに照合する）。
    - ``effect``: どく状態にした効果の識別子（ワザなら ``AttackKey`` の文字列）。ログにだけ残す。

    ベンチのポケモンは特殊状態にならない（p.322）ので、バトル場のポケモンでなければエンジンの不具合として止める。
    """
    if state.players[owner].active is not pokemon:
        raise RuntimeError(f"バトル場にいないポケモン {pokemon.pokemon_id} をどく状態にしようとした（エンジンの不具合。p.322）")
    already = pokemon.conditions.poison is not None
    pokemon.conditions = replace(pokemon.conditions, poison=NORMAL_POISON)
    extra = {"already": True} if already else {}
    state.add_event(
        "special_condition",
        player=owner,
        pokemon=pokemon.card,
        pokemon_id=pokemon.pokemon_id,
        condition=POISON,
        damage=NORMAL_POISON.damage,
        effect=effect,
        **extra,
    )


def clear_special_conditions(state: GameState, owner: int, pokemon: PokemonInPlay, reason: str) -> None:
    """バトル場からベンチに戻ったポケモンの特殊状態を、すべて消す（p.311・p.322）。特殊状態がなければ何もしない。

    「どく」なら、どくマーカーを取りのぞくことにあたる（p.322）。ダメージカウンター・ついているカード・
    場のポケモンの番号はそのまま（p.311）。一度消えた特殊状態は、バトル場にもどっても復活しない（p.322）。
    """
    names = pokemon.conditions.names()
    if not names:
        return
    pokemon.conditions = NO_SPECIAL_CONDITIONS
    state.add_event(
        "special_conditions_removed",
        player=owner,
        pokemon=pokemon.card,
        pokemon_id=pokemon.pokemon_id,
        conditions=names,
        reason=reason,
    )
