"""ワザによる「持続する効果」（v0.4b。p.322「11 特殊状態以外の「持続する効果」」・p.323）。

持続する効果は、ワザを受けたポケモン（「すなかけ」など）や、ワザを使ったポケモン自身（「まるまる」など）に与えられ、
そのポケモンが持つ（p.322）。特殊状態（``conditions.py``）とも、ポケモンについているトレーナーカード
（``AttachedTrainer``。物理的なカードで、トラッシュする）とも別のものなので、別の項目（``PokemonInPlay.persistent_effects``）
に持ち、付ける・消す処理もここに分ける（docs/persistent-effects-v0.4b.md）。

v0.4b で扱う効果は ``PreventDamage``（「次の相手の番、このカードはダメージを受けない。（ダメージ以外の効果は受ける）」。
トランセル・コクーンの「かたまる」。p.18・p.21 の最新の説明）だけ。

消える契機（どれもログ ``persistent_effect_removed`` の ``reason``）:

- ``EXPIRED``: 効果がはたらく番（``active_turn``。「次の相手の番」）の終わり（p.236・p.18 のワザ解説「効果の持続：次の
  相手の番の最後」「この相手の番の最後に…効果は消える」）。番の終わり（``engine._end_turn``）でポケモンチェックの前に消す
- ``RETREAT``・``SWITCH``: バトル場からベンチに戻った（p.311「ベンチに戻ったら、そのポケモンの…「持続する効果」は、
  すべて消えてなくなります」・p.322）。「にげる」に失敗した（こんらん）ポケモンはベンチに戻っていないので消えない
- ``EVOLVE``: 進化した（p.310 の進化の手順 3・p.323「「持続する効果」を受けているポケモンが進化したら…消えてなくなります」）
- ``KNOCK_OUT``: きぜつして場をはなれた（p.322「「持続する効果」を受けているポケモンが場をはなれたら…消えてなくなります」）

持続する効果は物理的なカードではないので、消えてもトラッシュには何も置かない。乱数も使わない。一度消えた効果は、
ベンチから再びバトル場に出ても復活しない（p.322）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .conditions import EVOLVE, RETREAT, SWITCH
from .state import PreventDamage

if TYPE_CHECKING:
    from .state import GameState, PokemonInPlay

EXPIRED = "expired"  # 効果がはたらく番の終わり（p.236・p.18 のワザ解説）
KNOCK_OUT = "knock_out"  # きぜつして場をはなれた（p.322）
REMOVAL_REASONS = (EXPIRED, RETREAT, SWITCH, EVOLVE, KNOCK_OUT)


def add_persistent_effect(state: GameState, owner: int, pokemon: PokemonInPlay, effect: PreventDamage, *, attack: str) -> None:
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
    state: GameState, owner: int, pokemon: PokemonInPlay, reason: str, effects: tuple[PreventDamage, ...] | None = None
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
    ここを通さない（``engine._pokemon_check``）。
    """
    for effect in pokemon.persistent_effects:
        if isinstance(effect, PreventDamage) and effect.active_turn == state.turn_number:
            return effect
    return None
