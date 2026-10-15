"""進化の手順の共通の部分（v0.25。docs/pokemon-breeder-v0.25.md）。

v0.24 までは ``engine._evolve_pokemon``（手札の進化カードを重ねる通常の操作。p.309・p.310）の中にあった、確認が済んだあとの
状態を変える手順（p.310 の手順 1〜5）を関数にしたものです。通常の操作と、1 進化を飛ばして 2 進化させるトレーナー（ポケモン育て屋さん。
``effects.EvolveBasicToStage2``）が同じ関数を使います（中身・ログの形と順番は v0.24 の ``_evolve_pokemon`` と同じ）。

- ``place_evolution_card``: 手札の進化カードを場のポケモンの上に置き、特殊状態・持続する効果・にげるの失敗の記録を消す。
  どこに重ねてよいか（名前・段階・番）の確認は呼ぶ側が、状態を変える前にすべて済ませる。
- ``skipped_stage1_basic``: 2 進化カードを、1 進化を飛ばして重ねてよいたねポケモンの名前（写しのカードのデータで決まらなければ None）。

``engine.py`` を読み込みません（``effects.py`` からも使うため）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .conditions import EVOLVE, clear_special_conditions
from .persistent import remove_persistent_effects

if TYPE_CHECKING:
    from .cards import CardDefinition
    from .state import GameState, PokemonInPlay


def place_evolution_card(state: GameState, player: int, target: PokemonInPlay, card: int, *, trainer: int | None = None) -> None:
    """手札の進化カード ``card`` を、自分の場のポケモン ``target`` の上に置いて進化させる（p.310 の手順 1〜5）。

    1・2. 手札から出して見せ、進化するポケモンの上に置く（下のカードはトラッシュしない。いちばん上のカードの内容がそのポケモンを
    表す）→ 3. 特殊状態と持続する効果から回復させる（``clear_special_conditions`` と ``remove_persistent_effects`` の ``EVOLVE``。
    別々の処理）→ 4. マーカー・カウンター（ダメージカウンター以外）・5. 進化によって引き起こされること（対応カードにない）。
    受け継ぐもの（ダメージカウンター・エネルギー・ついているトレーナー・場のポケモンの番号・場に出た番）は変えない。

    ログ ``evolve``（``player``・``pokemon_id``・進化前と進化後のカードの uid とカード id）。``trainer`` 引数は、トレーナーの効果で 1 進化を
    飛ばして重ねたとき（v0.25。ポケモン育て屋さん）の、使っているトレーナーのカードの uid で、そのときだけログの ``trainer_card`` に書く
    （通常の操作のログは v0.24 と同じ形）。乱数は使わない。
    """
    p = state.players[player]
    p.hand.remove(card)
    previous = target.card
    target.evolution_stack = (*target.evolution_stack, previous)
    target.card = card
    target.evolved_turn = state.turn_number
    extra = {} if trainer is None else {"trainer_card": trainer}
    state.add_event(
        "evolve",
        player=player,
        pokemon_id=target.pokemon_id,
        from_card=previous,
        from_card_id=state.cards[previous].card_id,
        to_card=card,
        to_card_id=state.cards[card].card_id,
        **extra,
    )
    # 3. 特殊状態から回復させる
    clear_special_conditions(state, player, target, EVOLVE)
    # 3. その他の「持続する効果」から回復させる（p.310・p.323。v0.4b）。特殊状態とは別の処理。ついているトレーナーは
    # 受け継ぐ（p.310。持続する効果ではない。v0.4a の E8'）
    remove_persistent_effects(state, player, target, EVOLVE)
    # 進化したポケモンは別のポケモンなので、にげるの失敗の記録を消す（特殊状態の解除とは別）
    if target.retreat_failed_turn is not None:
        target.retreat_failed_turn = None
        state.add_event("retreat_failure_cleared", player=player, pokemon=target.card, pokemon_id=target.pokemon_id, reason=EVOLVE)
    # 4. マーカー・カウンター（ダメージカウンター以外）・5. 進化によって引き起こされること: 対応カードにない


def skipped_stage1_basic(definition: CardDefinition) -> str | None:
    """2 進化カード ``definition`` を、1 進化を飛ばして重ねるたねポケモンの名前（v0.25。p.259 のポケモン育て屋さん）。

    2 進化カードの「○○○○から進化」の名前の 1 進化カードが「△△から進化」とする名前（``stage1_evolves_from``。同じ写しのカードの
    データ）が 1 つに決まれば、その名前。写しにその 1 進化カードがない・同じ名前の 1 進化カードで進化元が食い違うときは、確かめられない
    ので None（推測しない。名前の一部・形容詞で比べない）。2 進化カードでなければ None。
    """
    if not definition.is_stage2_pokemon or len(definition.stage1_evolves_from) != 1:
        return None
    return definition.stage1_evolves_from[0]
