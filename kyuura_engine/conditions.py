"""特殊状態（v0.3a〜v0.3c。p.322「10 ポケモンの特殊状態」）を付ける・消す処理。

v0.3a で「どく」、v0.3b で「ねむり」「マヒ」、v0.3c で「こんらん」を加えた。こんらんによるワザのコイン・20 ダメージ・
にげるのコインはエンジン（``engine._use_attack``・``_retreat``）が行う（ここにあるのは付ける処理と、20 ダメージの量）。

- 特殊状態になるのはバトル場のポケモン（対戦ポケモン）だけ。ベンチのポケモンは特殊状態にならない（p.322）。
- 特殊状態のポケモンがバトル場をはなれたら（ベンチに戻ったら）、すべての特殊状態は消える（p.311・p.322）。
  にげる・ポケモンいれかえ（どちらも「ポケモンの入れ替え」。p.325）は、ここの ``clear_special_conditions`` を呼ぶ。
  きぜつしたポケモンは場からいなくなるので、特殊状態もいっしょになくなる（場のポケモンが持つため）。
- どく状態のポケモンが再びどく状態になる効果を受けても、二重のどく状態にはならない（p.322）。ねむり・マヒ・こんらんも同じ
  （p.322「ねむり状態が積み重なることはありません」「マヒ状態が積み重なることはありません」「こんらん状態が積み重なることは
  ありません」）。
- 「ねむり」「マヒ」「こんらん」は重複しない（p.322「特殊状態の重複」）。p.322 の例「マヒ状態のポケモンがねむり状態に
  なったら、マヒ状態から自動的に回復して、ねむり状態になります」のとおり、新しい状態が前の状態に置きかわる
  （``SpecialConditions.exclusive``。前の状態は ``REPLACED`` の理由で消えたとログに残す）。どくはほかの特殊状態と
  重複する（p.322）ので、ねむり・マヒになっても、ねむり・マヒが消えても、どくはそのまま。
- 特殊状態を与えたポケモンが場をはなれても、受けた特殊状態は消えない（p.322）。
- どくのダメージ（ポケモンチェックの 2）・ねむりのコイン（3）・マヒの回復（4）は、エンジンの ``_pokemon_check`` が行う
  （ここにあるのは、そこから呼ぶ「消す」処理と、マヒの回復する番の計算）。

ログ:

- ``special_condition``: 特殊状態にする効果を受けた（``player``・``pokemon``・``pokemon_id``・``condition``・
  ``effect``、どくなら ``damage``、マヒなら ``paralyzed_turn``（マヒ状態になった番）・``recovery_turn``（回復する番）。
  もうその状態だったときだけ ``already``）
- ``special_conditions_removed``: 特殊状態が消えた（``player``・``pokemon``・``pokemon_id``・``conditions``・``reason``）。
  ``reason`` は ``RETREAT``・``SWITCH``（v0.3a）、``SLEEP_COIN``・``PARALYSIS_END``・``REPLACED``（v0.3b）
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .errors import UnsupportedError
from .state import ASLEEP, CONFUSED, NO_SPECIAL_CONDITIONS, Paralyzed, Poison, turn_owner

if TYPE_CHECKING:
    from .state import GameState, PokemonInPlay

POISON = "poison"
SLEEP = "sleep"  # v0.3b
PARALYSIS = "paralysis"  # v0.3b
CONFUSION = "confusion"  # v0.3c
# こんらん状態のポケモンのワザがこんらんしたとき（コインが「うら」）、ワザを使ったポケモン自身が受けるダメージ（p.309 の
# 手順 5「もとのワザの内容に関わらず、ワザを使ったポケモン自身が20ダメージを受けます」・p.322。v0.3c）
CONFUSION_DAMAGE = 20
# 通常のどく（p.322「ポケモンチェックのたびに、「弱点」「抵抗力」に関係なく、10ダメージを受けます。」）
NORMAL_POISON = Poison(damage=10)

# 特殊状態が消えた理由（ログの ``reason``）
RETREAT = "retreat"  # にげる（p.311）
SWITCH = "switch"  # トレーナーの効果によるポケモンの入れ替え（ポケモンいれかえ。p.322・p.325）
SLEEP_COIN = "sleep_coin"  # ポケモンチェックの 3 のコインが「おもて」でねむりから回復した（p.322・p.323。v0.3b）
PARALYSIS_END = "paralysis_end"  # ポケモンチェックの 4 でマヒから自動的に回復した（p.322・p.323。v0.3b）
REPLACED = "replaced"  # ほかの「ねむり」「マヒ」「こんらん」になったので消えた（p.322「特殊状態の重複」。v0.3b）


def _require_active(state: GameState, owner: int, pokemon: PokemonInPlay, condition: str) -> None:
    # ベンチのポケモンは特殊状態にならない（p.322）ので、バトル場のポケモンでなければエンジンの不具合として止める
    if state.players[owner].active is not pokemon:
        raise RuntimeError(f"バトル場にいないポケモン {pokemon.pokemon_id} を {condition} 状態にしようとした（エンジンの不具合。p.322）")


def poison(state: GameState, owner: int, pokemon: PokemonInPlay, *, effect: str) -> None:
    """``owner`` の対戦ポケモン ``pokemon`` を、通常のどく状態にする（p.322）。

    - もうどく状態なら、二重のどく状態にはならない（p.322「どく状態が積み重なることはありません」）。
    - p.322 は、特殊などく状態（ダメージが 20 など）のポケモンが通常のどく状態にする効果を受けたら、通常の
      どく状態になると書く。どちらの場合も結果は「通常のどく状態」なので、どく状態を ``NORMAL_POISON`` にする。
      特殊などく状態にする効果は未実装（受ける側の扱いが決まらない場合があるので、加えるときに照合する）。
    - どくはほかの特殊状態と重複する（p.322）ので、ねむり・マヒはそのまま（v0.3b）。
    - ``effect``: どく状態にした効果の識別子（ワザなら ``AttackKey`` の文字列）。ログにだけ残す。
    """
    _require_active(state, owner, pokemon, POISON)
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


def put_to_sleep(state: GameState, owner: int, pokemon: PokemonInPlay, *, effect: str) -> None:
    """``owner`` の対戦ポケモン ``pokemon`` を、ねむり状態にする（v0.3b。p.322「2. ねむり状態」）。

    - もうねむり状態なら、二重のねむり状態にはならない（p.322「ねむり状態が積み重なることはありません」）。
      ねむり状態は持つ情報がないので、状態は変わらない（ログに ``already``）。
    - マヒ状態なら、マヒ状態から自動的に回復して、ねむり状態になる（p.322「特殊状態の重複」の例）。こんらん状態でも、
      こんらんは消えてねむり状態になる（同じ規定。v0.3c）。
    - どく状態はそのまま（どくはほかの特殊状態と重複する。p.322）。
    """
    _require_active(state, owner, pokemon, SLEEP)
    current = pokemon.conditions.exclusive
    already = pokemon.conditions.asleep
    if not already:
        if current is not None:
            _remove_exclusive(state, owner, pokemon, REPLACED)
        pokemon.conditions = replace(pokemon.conditions, exclusive=ASLEEP)
    extra = {"already": True} if already else {}
    state.add_event(
        "special_condition",
        player=owner,
        pokemon=pokemon.card,
        pokemon_id=pokemon.pokemon_id,
        condition=SLEEP,
        effect=effect,
        **extra,
    )


def confuse(state: GameState, owner: int, pokemon: PokemonInPlay, *, effect: str) -> None:
    """``owner`` の対戦ポケモン ``pokemon`` を、こんらん状態にする（v0.3c。p.322「4. こんらん状態」）。

    - もうこんらん状態なら、二重のこんらん状態にはならない（p.322「こんらん状態が積み重なることはありません」）。
      こんらん状態は持つ情報がないので、状態は変わらない（ログに ``already``）。
    - ねむり・マヒ状態なら、それは消えてこんらん状態になる（p.322「「ねむり」「マヒ」「こんらん」状態が重複することは
      ありません」と、マヒからねむりの例から。docs/confusion-v0.3c.md）。
    - どく状態はそのまま（p.322「こんらん状態のポケモンがどく状態になったら、そのポケモンは「どく」と「こんらん」の両方の
      状態になります」）。
    """
    _require_active(state, owner, pokemon, CONFUSION)
    current = pokemon.conditions.exclusive
    already = pokemon.conditions.confused
    if not already:
        if current is not None:
            _remove_exclusive(state, owner, pokemon, REPLACED)
        pokemon.conditions = replace(pokemon.conditions, exclusive=CONFUSED)
    extra = {"already": True} if already else {}
    state.add_event(
        "special_condition",
        player=owner,
        pokemon=pokemon.card,
        pokemon_id=pokemon.pokemon_id,
        condition=CONFUSION,
        effect=effect,
        **extra,
    )


def paralysis_recovery_turn(state: GameState, owner: int, turn: int) -> int:
    """``turn`` 番にマヒ状態になった ``owner`` のポケモンが、自動的に回復する番（v0.3b）。

    「ポケモンのマヒ状態は、マヒ状態になった番の「次の自分（そのポケモンの持ち主）の番」の終わりのポケモンチェックで
    自動的に回復します」（p.323 の 4。p.322 にも同じ記述）。``turn`` より後の番のうち、持ち主（``owner``）の最初の番を
    返す（番の数を 1 つ足すとは決めない）。相手の番にマヒ状態になったら次の番、自分の番になったら 2 つ後の番になる。
    """
    recovery = turn + 1
    while turn_owner(state, recovery) != owner:
        recovery += 1
    return recovery


def paralysis_problem(state: GameState, owner: int, pokemon: PokemonInPlay) -> UnsupportedError | None:
    """``pokemon`` をいまマヒ状態にすると、原典で決められない場合なら、その理由（v0.3b）。

    マヒ状態のポケモンが再びマヒ状態になる効果を受けても、二重のマヒ状態にはならない（p.322）。ただし、そのとき
    回復する番が最初の「マヒ状態になった番」で決まるのか、あとの効果を受けた番で決まるのかは、原典に書かれていない。
    2 つの番から決まる回復の番が同じなら、どちらでも結果は同じなので扱える（状態は変えない）。違うなら決められない。

    v0.3b の対応カードでは起こらない（マヒにするワザは相手の対戦ポケモンにだけ効き、マヒ状態のポケモンは次の自分の
    番の終わりに回復するので、相手の番にマヒ状態のままでいることがない）。起こったら推測で処理せずに止める。
    """
    current = pokemon.conditions.exclusive
    if not isinstance(current, Paralyzed):
        return None
    before = paralysis_recovery_turn(state, owner, current.turn)
    after = paralysis_recovery_turn(state, owner, state.turn_number)
    if before == after:
        return None
    return UnsupportedError(
        "UNRESOLVED_REPARALYSIS_RECOVERY_TURN",
        f"マヒ状態のポケモン {pokemon.pokemon_id}（{current.turn} 番にマヒ状態になり、{before} 番の終わりに回復する）が、"
        f"{state.turn_number} 番に再びマヒ状態になる効果を受けた。二重のマヒ状態にはならない（p.322）が、回復する番を"
        "最初の番で決めるか、あとの番で決めるかは『オフィシャルブック2000』（p.322・p.323）から決められないので扱わない",
    )


def paralyze(state: GameState, owner: int, pokemon: PokemonInPlay, *, effect: str) -> None:
    """``owner`` の対戦ポケモン ``pokemon`` を、マヒ状態にする（v0.3b。p.322「3. マヒ状態」）。

    - マヒ状態になった番（``GameState.turn_number``）を ``Paralyzed.turn`` に持つ（回復する番を決めるため。
      ``paralysis_recovery_turn``）。
    - もうマヒ状態なら、二重のマヒ状態にはならない（p.322）。回復する番が変わらない場合だけ扱い、状態は変えない
      （ログに ``already``）。変わる場合は原典で決められないので ``UnsupportedError``（``paralysis_problem``）。
      コインを投げる効果は、投げる前に ``paralysis_problem`` を確かめておくこと。
    - ねむり状態なら、ねむり状態は消えてマヒ状態になる（p.322「「ねむり」「マヒ」「こんらん」状態が重複することは
      ありません」と、マヒからねむりの例から。docs/sleep-paralysis-v0.3b.md）。こんらん状態でも同じ（v0.3c）。
    - どく状態はそのまま（p.322）。
    """
    _require_active(state, owner, pokemon, PARALYSIS)
    problem = paralysis_problem(state, owner, pokemon)
    if problem is not None:
        raise problem
    current = pokemon.conditions.exclusive
    already = isinstance(current, Paralyzed)
    if not already:
        if current is not None:
            _remove_exclusive(state, owner, pokemon, REPLACED)
        pokemon.conditions = replace(pokemon.conditions, exclusive=Paralyzed(turn=state.turn_number))
    paralyzed = pokemon.conditions.exclusive
    extra = {"already": True} if already else {}
    state.add_event(
        "special_condition",
        player=owner,
        pokemon=pokemon.card,
        pokemon_id=pokemon.pokemon_id,
        condition=PARALYSIS,
        paralyzed_turn=paralyzed.turn,
        recovery_turn=paralysis_recovery_turn(state, owner, paralyzed.turn),
        effect=effect,
        **extra,
    )


def recover_from_sleep(state: GameState, owner: int, pokemon: PokemonInPlay) -> None:
    """ポケモンチェックの 3 のコインが「おもて」: ねむり状態から回復する（p.322・p.323）。どく状態はそのまま。"""
    if not pokemon.conditions.asleep:
        raise RuntimeError(f"ねむり状態でないポケモン {pokemon.pokemon_id} をねむりから回復させようとした（エンジンの不具合）")
    _remove_exclusive(state, owner, pokemon, SLEEP_COIN)


def recover_from_paralysis(state: GameState, owner: int, pokemon: PokemonInPlay) -> None:
    """ポケモンチェックの 4: マヒ状態から自動的に回復する（p.322・p.323）。どく状態はそのまま。"""
    if not pokemon.conditions.paralyzed:
        raise RuntimeError(f"マヒ状態でないポケモン {pokemon.pokemon_id} をマヒから回復させようとした（エンジンの不具合）")
    _remove_exclusive(state, owner, pokemon, PARALYSIS_END)


def _remove_exclusive(state: GameState, owner: int, pokemon: PokemonInPlay, reason: str) -> None:
    """「ねむり」「マヒ」「こんらん」（``SpecialConditions.exclusive``）だけを消す。どく状態は残す（p.322 の重複の規定）。"""
    name = pokemon.conditions.exclusive.name
    pokemon.conditions = replace(pokemon.conditions, exclusive=None)
    state.add_event(
        "special_conditions_removed",
        player=owner,
        pokemon=pokemon.card,
        pokemon_id=pokemon.pokemon_id,
        conditions=(name,),
        reason=reason,
    )


def clear_special_conditions(state: GameState, owner: int, pokemon: PokemonInPlay, reason: str) -> None:
    """バトル場からベンチに戻ったポケモンの特殊状態を、すべて消す（p.311・p.322）。特殊状態がなければ何もしない。

    「ベンチに戻ったら、そのポケモンの「どく」「ねむり」「マヒ」「こんらん」状態や、「持続する効果」は、すべて消えて
    なくなります」（p.311）。「どく」なら、どくマーカーを取りのぞくことにあたる（p.322）。ダメージカウンター・
    ついているカード・場のポケモンの番号はそのまま（p.311）。一度消えた特殊状態は、バトル場にもどっても復活しない（p.322）。
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
