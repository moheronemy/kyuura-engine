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


# v0.44: トレーナー「サカキ」の許可のあるポケモン（今の番に場に出した・進化した）を、山札から重ねる効果（ワザ・特殊能力）で進化させられるか（GV1）。
# 説明の「(ポケモンを進化させる時には、あなたの手札から「進化カード」を出して、そのポケモンの上にのせる)」が、許可を手札から重ねる進化に限るのか、進化の
# 手順の説明なのかが決められない（docs/search-evolution-once-attacks-v0.44.md 4 章）。v0.44 では、山札から重ねる効果はどれも「サカキの」ポケモンではない自分自身を
# 進化させるとして、コードのない問いにしたが、エリカのピッピの「つきのちから」は自分の場のほかのポケモン（サカキのコイキング）も進化させられるので起こる（v0.45 で
# 停止コード ``UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK`` を付けた。裁定は未解決のまま。docs/conditional-damage-energy-v0.45.md 2 章）。呼ぶ側がその停止コードで止める。
# この値は ``evolution_block`` が返す「重ねられない理由」の印で、停止コードではない
PERMISSION_FROM_DECK_CODE = "PERMISSION_ONLY_FROM_DECK"
PERMISSION_FROM_DECK_REASON = (
    "トレーナー「サカキ」で今の番に進化させてよいポケモン（今の番に場に出した・進化した）を、山札から重ねる効果で進化させられるかは、説明の「(ポケモンを進化させる"
    "時には、あなたの手札から「進化カード」を出して、そのポケモンの上にのせる)」が許可を手札から重ねる進化に限るのかが決められないので扱わない（GV1）"
)


def has_evolution_permission(state: GameState, target: PokemonInPlay) -> bool:
    """v0.44: 場のポケモン ``target`` が、トレーナー「サカキ」で選ばれ、今の番は場に出た番・進化した番でも進化させてよい（``evolution_permission_turn``）か。"""
    return target.evolution_permission_turn is not None and target.evolution_permission_turn == state.turn_number


def turn_restriction(state: GameState, target: PokemonInPlay) -> tuple[str, str] | None:
    """p.310 の「その番の最初から場に出ていた」ポケモンでないなら、その理由（``EVOLVED_THIS_TURN``・``PLAYED_THIS_TURN``）。手札から重ねる進化（通常の操作・
    ポケモン育て屋さん）で共通（v0.44 で関数にした。v0.43 までと同じコード・同じ文）。

    v0.44: トレーナー「サカキ」の許可のあるポケモン（``has_evolution_permission``）は、今の番に場に出した・進化したポケモンでも進化させてよい（「そのポケモンが場に
    出たのが今の番でも、そのポケモンを進化させてよい。また、進化したそのポケモンを、同じ番で、さらに進化させてもよい。」。kyuura の印刷の文面。カードの文面が
    ルールに優先する。GR-2000-P307-CARD-OVER-RULE）。変えるのはこの 2 つの制限だけで、おたがいの最初の番（``FIRST_TURN_EVOLUTION``）・名前・段階は変えない
    （日本語の文面に最初の番の記述はない。英語版の「or if this is your first turn」を持ち込まない）。"""
    if target.current_form_turn < state.turn_number or has_evolution_permission(state, target):
        return None
    if target.evolved_turn is not None:
        return "EVOLVED_THIS_TURN", f"場のポケモン {target.pokemon_id} はこの番に進化したので、もう一度は進化させられない（p.310）"
    return "PLAYED_THIS_TURN", f"場のポケモン {target.pokemon_id} はこの番に場に出したので、進化させられない（p.310）"


def evolution_block(state: GameState, target: PokemonInPlay, definition: CardDefinition, *, from_deck: bool = False) -> tuple[str, str] | None:
    """進化カード ``definition`` を、自分の場のポケモン ``target`` に今重ねられない理由（コード, 理由の文）。重ねられるなら None（v0.42。v0.41 までの
    ``engine._evolve_pokemon`` の確認（番・名前・その番の最初から場にいたか・段階）を、同じ順番・同じコード・同じ文のまま関数にした。通常の操作
    （手札から）とワザの効果（エリカのピッピの「つきのちから」。山札から）で共通。ワザによる進化でも、p.310 の進化の制限を免除しない）。

    v0.44: ``from_deck`` は、山札から重ねる効果（ワザ・特殊能力。つきのちから・コイキングの「たきのぼりしんか」・キョウのコクーンの［うか］）。トレーナー「サカキ」の
    許可だけで制限が外れる組は、手札から重ねる進化なら重ねられ（``turn_restriction``）、山札から重ねる効果なら決められない（GV1。``PERMISSION_FROM_DECK_CODE``。
    呼ぶ側が止める。v0.45 から停止コード ``UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK``。つきのちからでほかのポケモンを進化させるときに起こる）。

    確かめないもの: 進化したあとの HP がダメージ以下になるか（呼ぶ側。``UNRESOLVED_EVOLUTION_HP``）・カードが対応しているか（呼ぶ側）。状態は変えない。"""
    if state.turn_number <= 2:
        # 番は先攻から交互に進むので、1 番は先攻の、2 番は後攻の最初の番（p.309・p.310）
        return "FIRST_TURN_EVOLUTION", "おたがいのプレイヤーの最初の番には、ポケモンを進化させられない（p.310）"
    current = state.card_def(target.card)
    if current.name_ja != definition.evolves_from:
        return (
            "EVOLUTION_NAME_MISMATCH",
            f"「{definition.name_ja}」は「{definition.evolves_from}」から進化する。場のポケモン {target.pokemon_id} は「{current.name_ja}」",
        )
    restriction = turn_restriction(state, target)
    if restriction is not None:
        return restriction
    if from_deck and target.current_form_turn >= state.turn_number:
        return PERMISSION_FROM_DECK_CODE, PERMISSION_FROM_DECK_REASON  # 許可だけで制限が外れる組（GV1）
    below_stage = "basic" if definition.is_stage1_pokemon else "stage1"
    if current.stage != below_stage:
        return (
            "EVOLUTION_STAGE_MISMATCH",
            f"「{definition.name_ja}」（{definition.stage}）は {below_stage} のポケモンに重ねる。場のポケモン {target.pokemon_id} の"
            f"「{current.name_ja}」は {current.stage}（p.316・p.319）",
        )
    return None


def place_evolution_card(state: GameState, player: int, target: PokemonInPlay, card: int, *, trainer: int | None = None,
                         effect: str | None = None, power: str | None = None) -> None:
    """手札の進化カード ``card`` を、自分の場のポケモン ``target`` の上に置いて進化させる（p.310 の手順 1〜5）。

    1・2. 手札から出して見せ、進化するポケモンの上に置く（下のカードはトラッシュしない。いちばん上のカードの内容がそのポケモンを
    表す）→ 3. 特殊状態と持続する効果から回復させる（``clear_special_conditions`` と ``remove_persistent_effects`` の ``EVOLVE``。
    別々の処理）→ 4. マーカー・カウンター（ダメージカウンター以外）・5. 進化によって引き起こされること（対応カードにない）。
    受け継ぐもの（ダメージカウンター・エネルギー・ついているトレーナー・場のポケモンの番号・場に出た番）は変えない。

    ログ ``evolve``（``player``・``pokemon_id``・進化前と進化後のカードの uid とカード id）。``trainer`` 引数は、トレーナーの効果で 1 進化を
    飛ばして重ねたとき（v0.25。ポケモン育て屋さん）の、使っているトレーナーのカードの uid で、そのときだけログの ``trainer_card`` に書く
    （通常の操作のログは v0.24 と同じ形）。乱数は使わない。

    v0.42: ``effect`` は、ワザの効果で山札の進化カードを重ねたとき（エリカのピッピの「つきのちから」）のワザ（``AttackKey`` の文字列）。そのときは
    カードを手札ではなく山札から出し、ログに ``effect`` と ``source_zone``（``"deck"``）を書く（どこに重ねてよいかの確認は、通常の操作と同じ
    ``evolution_block``。呼ぶ側）。v0.44: ``power`` は、特殊能力の効果で山札の進化カードを重ねたとき（キョウのコクーンの［うか］）の特殊能力（``PowerKey`` の
    文字列）。山札から出し、ログに ``power`` と ``source_zone``（``"deck"``）を書く。
    """
    p = state.players[player]
    if effect is not None and power is not None:
        raise RuntimeError("ワザと特殊能力の両方の効果で進化させることはない（エンジンの不具合）")
    if effect is None and power is None:
        p.hand.remove(card)
    else:
        p.deck.remove(card)
    previous = target.card
    target.evolution_stack = (*target.evolution_stack, previous)
    target.card = card
    target.evolved_turn = state.turn_number
    extra = {} if trainer is None else {"trainer_card": trainer}
    if effect is not None:
        extra.update(effect=effect, source_zone="deck")
    if power is not None:
        extra.update(power=power, source_zone="deck")
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
