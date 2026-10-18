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

from .conditions import DEVOLVE, EVOLVE, clear_special_conditions
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

# v0.50（docs/mew-devolution-spray-v0.50.md 5 章）: 今の番に退化したポケモン（``PokemonInPlay.devolved_turn``）を、同じ番に進化させられるか（DV2）。退化したポケモンは
# 「退化前とは別のポケモン」（p.324「19」）で、p.310 の「その番の最初から場に出ていた」「その番に進化した」がどちらに当てはまるかが記録で決まらない。どの入口（手札から
# 重ねる通常の操作・ポケモン育て屋さん・山札から重ねるワザと特殊能力）でも、ほかの確かめがすべて通ったあとに止める。トレーナー「サカキ」の許可（「進化したそのポケモンを、
# 同じ番で、さらに進化させてもよい」）も、退化したポケモンが「そのポケモン」かが決まらないので、許可があっても止める
DEVOLVED_THIS_TURN_CODE = "UNRESOLVED_EVOLVE_AFTER_DEVOLUTION"
DEVOLVED_THIS_TURN_REASON = (
    "今の番に退化したポケモンを、同じ番に進化させられるかは、退化したポケモンが「退化前とは別のポケモン」（p.324）であることと、p.310 の「その番の最初から場に出ていた」"
    "「その番に進化した」の関係が記録で決まらないので扱わない（DV2）"
)


def devolved_this_turn(state: GameState, target: PokemonInPlay) -> bool:
    """v0.50: 場のポケモン ``target`` が今の番に退化したか（``devolved_turn``。DV2）。"""
    return target.devolved_turn is not None and target.devolved_turn == state.turn_number


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


def evolution_prevented(state: GameState) -> tuple[str, str] | None:
    """v0.47: 今はたらいている、ポケモンを進化できなくする特殊能力（［げんしのちから］）があれば、進化できない理由（``EVOLUTION_PREVENTED``, 理由の文）。なければ None。
    はたらいているかは問い合わせのたびに今の場から求める（効果の登録表の ``evolution_preventers``。``effects.py`` を読み込まないための入口）。状態は変えない。"""
    preventers = state.effects.evolution_preventers(state)
    if not preventers:
        return None
    holders = "・".join(f"{pid}" for _, pid, _ in preventers)
    return "EVOLUTION_PREVENTED", f"場のポケモン {holders} の特殊能力がはたらいているので、全てのポケモンは進化することができない"


def evolution_block(state: GameState, target: PokemonInPlay, definition: CardDefinition, *, from_deck: bool = False) -> tuple[str, str] | None:
    """進化カード ``definition`` を、自分の場のポケモン ``target`` に今重ねられない理由（コード, 理由の文）。重ねられるなら None（v0.42。v0.41 までの
    ``engine._evolve_pokemon`` の確認（番・名前・その番の最初から場にいたか・段階）を、同じ順番・同じコード・同じ文のまま関数にした。通常の操作
    （手札から）とワザの効果（エリカのピッピの「つきのちから」。山札から）で共通。ワザによる進化でも、p.310 の進化の制限を免除しない）。

    v0.44: ``from_deck`` は、山札から重ねる効果（ワザ・特殊能力。つきのちから・コイキングの「たきのぼりしんか」・キョウのコクーンの［うか］）。トレーナー「サカキ」の
    許可だけで制限が外れる組は、手札から重ねる進化なら重ねられ（``turn_restriction``）、山札から重ねる効果なら決められない（GV1。``PERMISSION_FROM_DECK_CODE``。
    呼ぶ側が止める。v0.45 から停止コード ``UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK``。つきのちからでほかのポケモンを進化させるときに起こる）。

    v0.47: 最初に、ポケモンを進化できなくする常にはたらく特殊能力（プテラの［げんしのちから］。``EffectRegistry.evolution_preventers``）がはたらいていれば
    ``EVOLUTION_PREVENTED``（どの入口でも同じ。手札から重ねる通常の操作・山札から重ねるワザと特殊能力。ポケモン育て屋さんは使う前に同じ問い合わせで止める）。

    v0.50: 今の番に退化したポケモン（``devolved_this_turn``）は、ほかの確かめがすべて通ったあとに ``DEVOLVED_THIS_TURN_CODE``（DV2。停止コード）。p.310 の制限
    （``turn_restriction``）・GV1 の印は当てはめない（どちらに当たるかが決まらないため）。呼ぶ側は ``UnsupportedError`` にする（``IllegalActionError`` にしない）。

    確かめないもの: 進化したあとの HP がダメージ以下になるか（呼ぶ側。``UNRESOLVED_EVOLUTION_HP``）・カードが対応しているか（呼ぶ側）。状態は変えない。"""
    prevented = evolution_prevented(state)
    if prevented is not None:
        return prevented
    # v0.49: カードの説明が進化を禁じている（メタモンの［へんしん］の「このカードに進化カードをつけることはできない」・タケシのキュウコンの「ばける」の「(ただし
    # 「進化・退化」はできない)」）。どの入口（手札・山札から重ねるワザと特殊能力）でも同じ。``EffectRegistry.evolution_forbidden``
    forbidden = state.effects.evolution_forbidden(state, target)
    if forbidden is not None:
        return forbidden
    if state.turn_number <= 2:
        # 番は先攻から交互に進むので、1 番は先攻の、2 番は後攻の最初の番（p.309・p.310）
        return "FIRST_TURN_EVOLUTION", "おたがいのプレイヤーの最初の番には、ポケモンを進化させられない（p.310）"
    current = state.card_def(target.card)
    if current.name_ja != definition.evolves_from:
        return (
            "EVOLUTION_NAME_MISMATCH",
            f"「{definition.name_ja}」は「{definition.evolves_from}」から進化する。場のポケモン {target.pokemon_id} は「{current.name_ja}」",
        )
    devolved = devolved_this_turn(state, target)
    if not devolved:
        # v0.50: 今の番に退化したポケモンは、p.310 の制限（その番に場に出した・進化した）のどちらに当たるかが決まらないので、ここでは当てはめない（DV2。最後に止める）
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
    if devolved:
        return DEVOLVED_THIS_TURN_CODE, f"場のポケモン {target.pokemon_id}: {DEVOLVED_THIS_TURN_REASON}"
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
    # effects.py は evolution.py を読み込むので、使うときに読み込む
    from .effects import goop_gas_entry_check

    goop_gas_entry_check(state, card, how="evolve")  # v0.59: GG1（状態を変える前）
    if effect is None and power is None:
        p.hand.remove(card)
    else:
        p.deck.remove(card)
    previous = target.card
    retag_power_uses(state, target)  # v0.50: いちばん上のカードが変わる前に、そのカードで使った「自分の番ごとに1回」の記録をそのカードの記録にする
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
    # v0.48: 特殊能力で色を変えた記録（モルフォンの［へんしょく］。``TypeShift``）も、進化前のポケモンのものなので消す（進化したポケモンは別のポケモン。p.310。モルフォンから
    # 進化するカードは写しにないので、今の対応カードでは起こらない。ログは残さない）
    target.type_shift = None
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


# ---------------------------------------------------------------- 退化（v0.50。docs/mew-devolution-spray-v0.50.md 3 章）

DEVOLVE_TO_HAND = "hand"  # はがした進化カードを持ち主の手札にもどす（ミュウの「たいかビーム」）
DEVOLVE_TO_DISCARD = "discard"  # はがした進化カードを持ち主のトラッシュにすてる（退化スプレー）
DEVOLVE_DESTINATIONS = (DEVOLVE_TO_HAND, DEVOLVE_TO_DISCARD)


def retag_power_uses(state: GameState, target: PokemonInPlay) -> None:
    """v0.50: 場のポケモン ``target`` のいちばん上のカードが変わる直前（進化・退化）に、そのカードで使った「自分の番ごとに1回」の特殊能力の記録（(場のポケモンの番号,
    特殊能力の位置)。``effects.power_use_record``）を、印刷したカードの記録（(場のポケモンの番号, 特殊能力の位置, そのカードの uid)。v0.49 の「ばける」でのせた
    カードと同じ形）に置きかえる。

    v0.49 は「特殊能力は印刷したカードで区別する」としながら、いちばん上のカードの記録を (番号, 位置) で持っていたので、進化・退化でいちばん上のカードが変わると、前の
    カードで使った記録が新しいいちばん上のカードの同じ位置の特殊能力を止めていた（進化したポケモンは「進化前のポケモンとは別のポケモン」。GR-2000-P310-EVOLUTION）。
    置きかえたあとも、(番号, 位置) の記録はいつも今のいちばん上のカードで使ったもの。退化して前のカードがまたいちばん上になったときに、そのカードで退化の前に使った
    記録があれば、もう一度使えるかは決まらない（DV3。``engine._use_pokemon_power`` が ``effects.power_reuse_after_devolution`` で、パワーごとの確認のあとに止める）。乱数・ログは使わない。"""
    pid = target.pokemon_id
    uses = state.power_uses_this_turn
    if any(len(record) == 2 and record[0] == pid for record in uses):
        state.power_uses_this_turn = tuple((record[0], record[1], target.card) if len(record) == 2 and record[0] == pid else record
                                           for record in uses)


def devolve(state: GameState, owner: int, target: PokemonInPlay, count: int, *, destination: str, by_player: int,
            effect: str | None = None, trainer: int | None = None) -> tuple[int, ...]:
    """場のポケモン ``target``（``owner`` の場のポケモン）から、実際に重なっている進化カードを上から ``count`` 枚はがし、``destination``（持ち主の手札・トラッシュ）に
    置く（退化。p.324「19 ポケモンの退化」。kyuura の GR-2000-P324-DEVOLUTION）。はがしたカード（上から順の uid）を返す。

    - ``count`` は 1 以上、重なっている進化カードの数（``evolution_stack`` の長さ）まで。いちばん上が「ばける」でのせたカード（``disguise``）のポケモン・ほかに退化
      できないポケモン（``EffectRegistry.evolution_forbidden``）の確かめと、はがす枚数の確かめは呼ぶ側が、状態を変える前に済ませる。通常の進化を逆にたどる処理ではなく、
      実際の重なりからはがす（ポケモン育て屋さんで 1 進化を飛ばした 2 進化ポケモンは、1 枚はがすとたねポケモンになる。飛ばした 1 進化のカードを作らない）
    - いちばん上のカードは、はがしたあとの重なりのいちばん上（``evolution_stack`` から外す）。いまの姿・最大HP・タイプ・弱点・抵抗力・ワザ・特殊能力は、問い合わせのたびに
      このカードから求める（退化前の進化カードに書かれている内容のすべては無効。CR-CHEMICAL-GAS-LEAVES の p.324 の引用）。印刷の定義は変えない
    - 退化した番（``devolved_turn``）を今の番にする。重なりがなくなれば進化した番（``evolved_turn``）を None にする（重なりが残れば、最後に進化した番のまま）。場に出た番・
      場のポケモンの番号・ダメージカウンター・エネルギー・ついているトレーナー・トレーナー「サカキ」の許可は変えない（カードの説明が「進化カード」をはがすだけ）
    - 特殊状態と持続する効果から回復させる（理由 ``devolve``。GR-2000-P324-DEVOLUTION・CR-SHELL-ATTACK-ENDS-ON-DEVOLUTION）。にげるの失敗の記録・［へんしょく］の記録
      （退化前のポケモンのもの）も消す。場に出てから 1 度だけ使えるワザの記録（``attacks_used_once``）は、はがしたカードのものだけを消す（そのカードは場をはなれた。
      残るカードの記録は「別のポケモン」だけを理由に消さない）。「自分の番ごとに1回」の記録は ``retag_power_uses``
    - ログ ``devolve``（``player`` は持ち主・``pokemon_id``・``from_card``／``from_card_id``（はがす前のいちばん上）・``to_card``／``to_card_id``（はがしたあと）・
      ``removed``／``removed_ids``（はがしたカード。上から順）・``destination``・``by_player``（はがしたプレイヤー）・ワザなら ``effect``、トレーナーなら ``trainer_card``）
    - きぜつの判定はしない（HP 以上なら、ワザのあと・トレーナーのあとの判定。呼ぶ側）。乱数は使わない
    """
    if destination not in DEVOLVE_DESTINATIONS:
        raise ValueError(f"はがした進化カードの行き先 {destination!r} は {DEVOLVE_DESTINATIONS} のどれか")
    if not 1 <= count <= len(target.evolution_stack) or target.disguise is not None:
        raise RuntimeError(f"場のポケモン {target.pokemon_id} から {count} 枚はがせない（重なり {target.evolution_stack}・のせたカード {target.disguise}。エンジンの不具合）")
    if (effect is None) == (trainer is None):
        raise RuntimeError("退化はワザの効果かトレーナーの効果のどちらか（エンジンの不具合）")
    p = state.players[owner]
    chain = (*target.evolution_stack, target.card)
    removed = tuple(reversed(chain[-count:]))
    # effects.py は evolution.py を読み込むので、使うときに読み込む
    from .effects import goop_gas_entry_check

    goop_gas_entry_check(state, chain[-count - 1], how="devolve")  # v0.59: GG1（状態を変える前）
    previous = target.card
    retag_power_uses(state, target)
    target.card = chain[-count - 1]
    target.evolution_stack = chain[:-count - 1]
    if not target.evolution_stack:
        target.evolved_turn = None
    target.devolved_turn = state.turn_number
    (p.hand if destination == DEVOLVE_TO_HAND else p.discard).extend(removed)
    extra = {"effect": effect} if effect is not None else {"trainer_card": trainer}
    state.add_event(
        "devolve",
        player=owner,
        pokemon_id=target.pokemon_id,
        from_card=previous,
        from_card_id=state.cards[previous].card_id,
        to_card=target.card,
        to_card_id=state.cards[target.card].card_id,
        removed=removed,
        removed_ids=tuple(state.cards[uid].card_id for uid in removed),
        destination=destination,
        by_player=by_player,
        **extra,
    )
    clear_special_conditions(state, owner, target, DEVOLVE)
    remove_persistent_effects(state, owner, target, DEVOLVE)
    if target.retreat_failed_turn is not None:
        target.retreat_failed_turn = None
        state.add_event("retreat_failure_cleared", player=owner, pokemon=target.card, pokemon_id=target.pokemon_id, reason=DEVOLVE)
    target.type_shift = None
    if any(card in removed for card, _ in target.attacks_used_once):
        target.attacks_used_once = tuple(entry for entry in target.attacks_used_once if entry[0] not in removed)
    return removed
