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
from .state import (
    ATTACK_FIELD_POWER_SUPPRESSION,
    ATTACK_POWER_SUPPRESSION,
    OPPONENT_POWER_SUPPRESSION,
    POWER_SUPPRESSION,
)

if TYPE_CHECKING:
    from .cards import Power
    from .state import GameState, PokemonInPlay, TrainerTurnEffect


def _suppressor(state: GameState, pokemon: PokemonInPlay) -> tuple[SuppressOtherPowers, ...]:
    """場のポケモン ``pokemon`` の今持つ特殊能力（v0.49 から ``effects.powers_of``。いちばん上のカードと「ばける」でのせたカード。メタモンの［へんしん］で写した
    カードの特殊能力は入らない（TF1。写した特殊能力を持つかは決まらないので、``effects.form_problems`` がその状態にしない））のうち、ほかの特殊能力を消す実装が
    登録されたもの。［へんしん］がはたらいているかはこの答えを聞くので、［へんしん］で決まる姿を聞かない（循環しない）。"""
    from .effects import powers_of
    from .persistent import powers_stopped

    found = tuple(slot.effect for slot in powers_of(state, pokemon) if isinstance(slot.effect, SuppressOtherPowers))
    if not found:
        return ()  # v0.119: 消す特殊能力を持たないポケモンの止まる効果は読まない（［いあつ］の問い合わせが、ほかのポケモンの［じっとみる］の発生源を読んで循環しない）
    if powers_stopped(state, pokemon) is not None:
        return ()  # v0.86: スタンウェーブを受けたポケモンの特殊能力（かがくへんかガスも）は「その効果も消える」
    return found


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


def goop_gas_effects(state: GameState) -> tuple[TrainerTurnEffect, ...]:
    """今はたらいている「まきちらせ!ベトベトガス」（v0.59。``TrainerTurnEffect`` の種類 ``POWER_SUPPRESSION``。「次の相手の番が終わるまで、おたがいの場のすべての
    ポケモンは特殊能力を使うことができず、その力も消える。」）。使った番〜消える番（消える番の終わりに ``procedures.expire_at_turn_end`` が消す）。

    止める範囲は使った時点で場にいるポケモン（kyuura の card_differences の PMCG4-056 の二次資料の説明。確度は有力）とも、あとから場に出た・進化した・退化した
    ポケモンも含むとも読めて決まらない（GG1）。特殊能力を持つポケモンが、この効果のはたらく間に場に出る・進化する・退化するコマンドは受け付けない
    （``effects.goop_gas_entry_check``）ので、効果のはたらく間に場にいる特殊能力を持つポケモンは、どれも使った時点で場にいたポケモン（同じ姿）で、どちらの読み方でも
    止まる。そのため、効果がはたらいている間は場のすべての特殊能力を止める（かがくへんかガスも除かない。p.265 の解説「［かがくへんかガス］の力を一時的に消す」）。"""
    turn = state.turn_number
    return tuple(r for r in state.trainer_effects if r.kind == POWER_SUPPRESSION and r.created_turn <= turn <= r.expires_turn)


def attack_power_suppressions(state: GameState) -> tuple[TrainerTurnEffect, ...]:
    """今はたらいている、ワザを使っているあいだの特殊能力の抑止（v0.91。``TrainerTurnEffect`` の種類 ``ATTACK_POWER_SUPPRESSION``。ポリゴンの「オールクリア」の「このワザを使って
    いるあいだ、おたがいの場にいるすべてのポケモンは「特殊能力」を使うことができず、その力も消える」）。ワザの処理の始めに加え、ワザの処理のあと（きぜつの判定の前）に消すので、
    ワザの処理の外にはない（不変条件）。まきちらせ!ベトベトガスと同じく、かがくへんかガスも除かずにすべての特殊能力を止める（説明の「すべてのポケモン」）。"""
    return tuple(r for r in state.trainer_effects if r.kind == ATTACK_POWER_SUPPRESSION)


def attack_field_power_suppressions(state: GameState) -> tuple[TrainerTurnEffect, ...]:
    """今はたらいている、ワザで与えたおたがいの場の特殊能力の抑止（v0.92。``TrainerTurnEffect`` の種類 ``ATTACK_FIELD_POWER_SUPPRESSION``。ナツメのゲンガーの「やみのはどう」の
    「次の相手の番の終わりまで、お互いの場にいるすべてのポケモンは、特殊能力を使うことができず、それらの力も消える」）。与えた番〜消える番（与えた番 + 1。その番の終わりに
    ``procedures.expire_at_turn_end`` が消す）。まきちらせ!ベトベトガスと同じく、かがくへんかガスも除かずにすべての特殊能力を止める（説明の「すべてのポケモン」）。オールクリアの
    ワザを使っているあいだの抑止（``attack_power_suppressions``）とは期限が違う。発生源のポケモンが場をはなれても消えない（説明に書かれていない）。"""
    turn = state.turn_number
    return tuple(r for r in state.trainer_effects if r.kind == ATTACK_FIELD_POWER_SUPPRESSION and r.created_turn <= turn <= r.expires_turn)


def field_powers_suppressed(state: GameState) -> bool:
    """おたがいの場のすべての特殊能力を止める期限のある効果（まきちらせ!ベトベトガス・オールクリアのワザを使っているあいだ・やみのはどう。v0.92 でまとめた）がはたらいているか。
    かがくへんかガス（場の特殊能力）・スタンウェーブ（1 匹）・ふしぎなガス（片方の場）は含まない。"""
    return bool(goop_gas_effects(state) or attack_power_suppressions(state) or attack_field_power_suppressions(state))


def power_suppressed(state: GameState, power: Power, holder: PokemonInPlay | None = None, *, owner: int | None = None) -> bool:
    """特殊能力 ``power``（場のポケモンの特殊能力）が今「使えず、その力も消え」ているか（v0.59）: はたらいているかがくへんかガスに消されている（``suppressors_of``）か、
    まきちらせ!ベトベトガスの効果がはたらいている（``goop_gas_effects``）。宣言して使う特殊能力の使用・常にはたらく・自動的にはたらく特殊能力の力のどちらにも当てはまる
    （kyuura の CR-CHEMICAL-GAS-USE-VS-POWER・CR-CHEMICAL-GAS-ALL-POWERS）。わるいアーボックの「ショックアイ」（使うことだけができない）は含まない
    （``persistent.powers_use_prevented``）。

    v0.86: ``holder``（その特殊能力を持つ場のポケモン）を渡したら、そのポケモンがわるいモココの「スタンウェーブ」を受けている（``persistent.powers_stopped``。「使うことが
    できず、その効果も消える」）ときも消えている。止まるのはそのポケモンの特殊能力だけ。

    v0.87: ドガースの「ふしぎなガス」（``effects.strange_gas_effects``。相手プレイヤーが与えた ``OPPONENT_POWER_SUPPRESSION``）がはたらいているプレイヤーの場のポケモンの特殊能力も
    消えている。止まるのはその側だけなので、特殊能力の持ち主（``holder`` の持ち主か ``owner``）が要る。ふしぎなガスがはたらいているのに、どちらも渡さない問い合わせは
    エンジンの不具合（RuntimeError。持ち主を推測しない）。

    v0.119: ``holder`` が相手の［いあつ］で「ワザ・特殊能力」を使えず、その効果も消えているベイビィポケモン（``effects.scared_by``）なら消えている。"""
    return power_suppressed_except(state, power, holder, owner=owner)


def power_suppressed_except(state: GameState, power: Power, holder: PokemonInPlay | None = None, *, owner: int | None = None,
                            ignore: tuple[TrainerTurnEffect, ...] = ()) -> bool:
    """``power_suppressed`` の本体（v0.119）。``ignore`` の「おたがいの場の特殊能力を止める」ワザの効果（``ATTACK_FIELD_POWER_SUPPRESSION``）は数えない（［いあつ］の循環の確かめ IA1 だけが渡す。
    ``effects.scare_cycle_problem``）。"""
    if holder is not None:
        from .effects import scared_by
        from .persistent import powers_stopped

        if powers_stopped(state, holder) is not None:
            return True
        found = state.find_pokemon(holder.pokemon_id)
        if found is not None and scared_by(state, found[0], holder):
            return True  # v0.119: ［いあつ］
    # v0.91: オールクリアのワザを使っているあいだ。v0.92: やみのはどう（``field_powers_suppressed``）
    if goop_gas_effects(state) or attack_power_suppressions(state) or any(r not in ignore for r in attack_field_power_suppressions(state)) or suppressors_of(state, power):
        return True
    if any(r.kind == OPPONENT_POWER_SUPPRESSION for r in state.trainer_effects):
        from .effects import strange_gas_effects

        if holder is not None:
            found = state.find_pokemon(holder.pokemon_id)
            if found is None:
                raise RuntimeError(f"特殊能力を持つポケモン {holder.pokemon_id} が場にいない（ふしぎなガスの持ち主を決められない。エンジンの不具合）")
            side = found[0]
            if owner is not None and owner != side:
                raise RuntimeError(f"特殊能力の持ち主 {owner} と、ポケモン {holder.pokemon_id} の持ち主 {side} が違う（エンジンの不具合）")
        elif owner is not None:
            side = owner
        else:
            raise RuntimeError("ふしぎなガスがはたらいている場で、特殊能力の持ち主を渡さない問い合わせ（エンジンの不具合）")
        return bool(strange_gas_effects(state, side))
    return False


def scaring_powers(state: GameState, baby_owner: int) -> tuple[tuple[int, str], ...]:
    """v0.119: プレイヤー ``baby_owner`` の場のベイビィポケモンに当たる、相手の今はたらいている［いあつ］（``effects.ScareOpponentBabies``。相手のバトル場のポケモンの。ねむり・マヒ・こんらんでない。
    力が消えていない）の (持つポケモンの番号, ``PowerKey`` の文字列) の並び。状態を変えない。［いあつ］を持つポケモンはベイビィポケモンではないので、その力が消えているかの問い合わせは
    ここにもどらない（循環しない）。"""
    from .effects import ScareOpponentBabies, powers_of

    holder = state.players[1 - baby_owner].active
    if holder is None or state.is_face_down(holder):
        return ()
    return tuple((holder.pokemon_id, str(slot.key)) for slot in powers_of(state, holder)
                 if isinstance(slot.effect, ScareOpponentBabies) and slot.effect.status_allows(holder) and not power_suppressed(state, slot.power, holder))


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
