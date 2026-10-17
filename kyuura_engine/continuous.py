"""常にはたらいている特殊能力の効果を、今の状態から求める（v0.8。docs/continuous-effects-v0.8.md）。

「常にはたらいているため、使用を宣言しない特殊能力もあります」（p.311・p.323）。v0.8 で扱うのは、ベトベトンの「かがくへんかガス」
（``effects.SuppressOtherPowers``。p.48・p.323 の最新の説明「このカードが場にいるかぎり、「かがくへんかガス」以外のすべての
「特殊能力」は使えず、その力も消える。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は消える。」）だけ。

効果がはたらいているかは、場のポケモン（いちばん上のカード）・特殊状態・効果の登録表だけから、その都度求める。状態に「はたらいて
いる」という印や一覧を持たず、過去のログも読まない。そのため:

- 進化（ベトベターからベトベトンへ）・きぜつ（場をはなれる）・ねむり・マヒ・こんらんになる／回復する・ベンチに戻る（特殊状態が
  消える）など、どの変化のあとでも、次に聞いたときの答えが変化を反映している（覚えておいた値が古くなることがない）。
- 保存と復元（pickle・``clone``・書き出し）のあとも、場と特殊状態が同じなら同じ答えになる。書き出しの形式は変わらない（形式 9）。

求めるのは、特殊能力の使用を受け付けるとき（``engine._use_pokemon_power``）だけ。v0.8 の対応カードには、ほかに常にはたらく・自動的に
はたらく特殊能力がないので、「その力も消える」がほかに影響する処理はない（加えるときは、その効果を使う前にここで聞く）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .effects import SuppressOtherPowers

if TYPE_CHECKING:
    from .cards import Power
    from .state import GameState, PokemonInPlay


def _suppressor(state: GameState, pokemon: PokemonInPlay) -> tuple[SuppressOtherPowers, ...]:
    """場のポケモン ``pokemon`` の今持つ特殊能力（v0.49 から ``effects.powers_of``。いちばん上のカードと「ばける」でのせたカード。メタモンの［へんしん］で写した
    カードの特殊能力は入らない（TF1。写した特殊能力を持つかは決まらないので、``effects.form_problems`` がその状態にしない））のうち、ほかの特殊能力を消す実装が
    登録されたもの。［へんしん］がはたらいているかはこの答えを聞くので、［へんしん］で決まる姿を聞かない（循環しない）。"""
    from .effects import powers_of

    return tuple(slot.effect for slot in powers_of(state, pokemon) if isinstance(slot.effect, SuppressOtherPowers))


def working_power_suppressors(state: GameState) -> tuple[int, ...]:
    """今はたらいている「ほかの特殊能力を消す」特殊能力（かがくへんかガス）を持つ場のポケモンの番号（両方のプレイヤー。プレイヤー 0 →
    1、それぞれバトル場 → ベンチの順）。場（バトル場・ベンチ。p.308）にいて、ねむり・マヒ・こんらんでないもの。"""
    working = []
    for player in state.players:
        for pokemon in player.in_play():
            if any(effect.is_working(pokemon) for effect in _suppressor(state, pokemon)):
                working.append(pokemon.pokemon_id)
    return tuple(working)


def suppressors_of(state: GameState, power: Power) -> tuple[int, ...]:
    """特殊能力 ``power`` を、今消している場のポケモンの番号（消されていなければ空）。

    「かがくへんかガス」は名前で除かれる（「「かがくへんかガス」以外の」）ので、かがくへんかガスどうしは消し合わない。はたらいているかの
    判定（``SuppressOtherPowers.is_working``）はほかの特殊能力を見ないので、循環しない。
    """
    found = []
    for player in state.players:
        for pokemon in player.in_play():
            if any(effect.is_working(pokemon) and effect.suppresses(power) for effect in _suppressor(state, pokemon)):
                found.append(pokemon.pokemon_id)
    return tuple(found)


def power_suppressors(state: GameState, pokemon_id: int, power_index: int = 0) -> tuple[int, ...]:
    """場のポケモン ``pokemon_id`` の ``power_index`` 番目の特殊能力（いちばん上のカード）を、今消している場のポケモンの番号。

    空なら消されていない（使えるかは、ほかの条件（番・特殊状態・選ぶものなど）による）。場にいないポケモン・ない特殊能力なら
    ``ValueError``。状態は変えない（コマンドを送らずに、使えるかの理由を調べるための公開の関数）。
    """
    found = state.find_pokemon(pokemon_id)
    if found is None:
        raise ValueError(f"場のポケモンの番号 {pokemon_id!r} は場にいない")
    definition = state.card_def(found[1].card)  # いちばん上のカードの特殊能力（v0.48 までと同じ呼び方。「ばける」でのせたカードの特殊能力は ``suppressors_of`` で聞く）
    if not 0 <= power_index < len(definition.powers):
        raise ValueError(f"場のポケモン {pokemon_id}（{definition.name_ja}）に {power_index!r} 番目の特殊能力はない")
    return suppressors_of(state, definition.powers[power_index])
