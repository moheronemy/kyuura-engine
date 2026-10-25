"""場のポケモンのワザの履歴（v0.62。docs/history-attacks-v0.62.md 2 章）。

前の番のことを読むワザ（タケシのダグトリオの「ドリルホール」・ピジョンとオニスズメの「オウムがえし」）のために、場のポケモンごとに 3 種類の記録を分けて持つ
（``PokemonInPlay.history``）。

- A（``AttackUsed``）: このポケモンが使ったワザ。宣言したとき（``resolution.flow``）に作り、相手のワザ・受けたワザを自分のワザとして使ったら、処理したワザを書く
- B・C（``AttackReceived``）: このポケモンが相手の番に受けた相手のワザ（B）と、実際に受けたダメージ・効果（C）。解決の基盤のダメージの要素（``deal_damage``）と
  効果の要素（``reaches``）がこのポケモンを対象にしたときに作る。相手のワザの自分へのダメージ・相手の控えへの効果（受けるポケモンの持ち主がワザを使ったプレイヤー）・
  返す効果のダメージ（番のプレイヤーのポケモンが受ける）は記録しない
- ``OtherReceived``: 相手の番にワザ以外で受けたこと（コマンドの前後の比べ。``open_probe``・``close_probe``）

記録は状態に持ち（書き出しの形式 20）、ログ・過去のコマンドから作り直さない。過去のカードの uid を新しい対象として使わない（記録の uid は「このカード」の確かめにだけ使う）。
履歴を読む効果のカードが対戦にあるときだけ記録する（``history_needed``。ないときは v0.61 と同じ状態）。

v0.99（docs/unown-perform-help-history-v0.99.md 3 章）: 受けたダメージを、受けた時にバトル場にいた分（``AttackReceived.active_damage``）とベンチにいた分に分けて持つ（アンノーンP の
［PERFORM］の「バトル場で相手のワザによるダメージを受けていたなら」。書き出しの形式 25）。履歴を読む効果に特殊能力（``PowerEffect.reads_history``）を加えた。

v0.100（docs/sketch-perish-song-history-v0.100.md 3 章）: 場のポケモンの履歴とは別に、プレイヤーの番ごとの記録（``GameState.turn_history``）を持つ。

- ``TurnAttack``: 番のプレイヤーがその番に使ったワザ（ドーブルの「スケッチ」の「前の相手の番に、相手のポケモンがワザを使っていたなら」）。宣言のとき（``note_used``）に作り、
  切りかえたら処理したワザを書く（``note_processed``）。場のポケモンの記録と同じ時点で、ワザを使ったポケモンが場をはなれても残る（今の相手の場から探さない）
- ``TurnField``: 番でないプレイヤーの場に、その番にいたポケモンのカード（「スケッチ」の「前の相手の番、このカードが場に出ていなければ」）。番の始め（``note_turn_start``）と、
  その番に場に出たとき（``note_entered``）に作る

プレイヤーの記録を読む効果（``AttackEffect.reads_turn_history``）のカードが対戦にあるときだけ記録する（``turn_history_needed``。場のポケモンの履歴の ``history_needed`` とは
別に決める。ないときは v0.99 と同じ状態）。保持するのは場のポケモンの履歴と同じ 2 つ前の番まで（``prune``）。

このモジュールは ``engine.py``・``resolution`` を読み込まない（``state``・``effects`` だけ。``effects`` は使うときに読み込む）。
"""

from __future__ import annotations

import dataclasses

from .errors import UnsupportedError
from .state import (
    AttackReceived,
    AttackUsed,
    GameState,
    OtherReceived,
    PokemonInPlay,
    TurnAttack,
    TurnField,
)

# 受けなかった要素の理由（``AttackReceived.voided``）
VOID_ATTACK_BARRIER = "attack_barrier"  # ダメージと効果の要素を無効にする効果（「ワザをうけない」「ワザによるダメージや効果を受けない」。``AttackBarrier``）
VOID_DAMAGE_ONLY = "damage_only"  # ダメージの要素だけを無効にする効果（「ダメージを受けない」状態・見えない壁など）
VOID_EVADED = "evaded"  # 「とうめい」で受けなかった（「ダメージや効果を受けない」）
VOID_DODGED = "dodged"  # 「かげぶんしん」で受けなかった（ダメージだけ）
VOID_IMMUNE = "immune"  # 特殊状態にならない（［めんえき］。効果の要素は受けたが特殊状態にならなかった）
VOID_FLED = "fled"  # v0.65: ［にげこむ］で入れ替えたので、そのワザの「ダメージ以外の効果」を受けなかった
VOID_EFFECT_ONLY = "effect_only"  # v0.80: 効果の要素だけを無効にする効果（エフェクトガード。「ダメージは、そのまま受ける」）
VOID_REFLECTED = "reflected"  # v0.83: 「リフレクトシールド」の「おもて」で受けなかった（ダメージだけ。ダメージ以外の効果は受ける）
VOID_REASONS = (VOID_ATTACK_BARRIER, VOID_DAMAGE_ONLY, VOID_EVADED, VOID_DODGED, VOID_IMMUNE, VOID_FLED, VOID_EFFECT_ONLY, VOID_REFLECTED)

# 記録を残す番の数（今の番・前の番・2 つ前の番。「前の自分の番」は 2 つ前、「前の相手の番」は 1 つ前）
KEPT_TURNS = 2


def history_needed(state: GameState) -> bool:
    """この対戦に、履歴を読むワザ・特殊能力（効果の登録の ``reads_history``）を持つカードがあるか。対戦のカードの定義（両方のデッキ）と効果の登録表から求める（状態に持たない）。
    ないときは履歴を記録しない（v0.61 までと同じ状態・書き出し）。相手のカードのワザを自分のワザとして使う（「ゆびをふる」）ときも、そのワザは対戦のカードにある。

    v0.99: 特殊能力だけが履歴を読む対戦（アンノーンP の［PERFORM］）でも記録する。特殊能力がはたらいているか（かがくへんかガス・場所・特殊状態）では決めない（記録するのは対戦に
    カードがあるかだけで決め、受けた時に特殊能力が消えていても、使う時にはたらいていれば読む）。"""
    for definition in state.definitions.values():
        for attack in definition.attacks:
            effect = state.effects.attack_effect(definition.id, attack, definition.attacks)
            if effect is not None and getattr(effect, "reads_history", False):
                return True
        for power in definition.powers:
            effect = state.effects.power_effect(definition.id, power)
            if effect is not None and getattr(effect, "reads_history", False):
                return True
    return False


def turn_history_needed(state: GameState) -> bool:
    """v0.100: この対戦に、プレイヤーの番ごとの記録を読むワザ（効果の登録の ``reads_turn_history``。「スケッチ」）を持つカードがあるか。``history_needed`` と同じく、対戦の
    カードの定義と効果の登録表から求める（状態に持たない）。ないときはプレイヤーの記録を作らない（v0.99 までと同じ状態・書き出し）。"""
    for definition in state.definitions.values():
        for attack in definition.attacks:
            effect = state.effects.attack_effect(definition.id, attack, definition.attacks)
            if effect is not None and getattr(effect, "reads_turn_history", False):
                return True
    return False


def _key(key) -> tuple[str, int]:
    return (key.card_id, key.attack_index)


def note_used(state: GameState, pokemon: PokemonInPlay, key) -> None:
    """ワザの宣言（p.309 の手順 3）のときに、使ったワザ（A）を記録する。v0.100: プレイヤーの記録（``TurnAttack``）も同じ時点で作る（宣言のあとの失敗・こんらんの「うら」でも
    使ったことになる。宣言の前に拒否したワザは状態ごと捨てるので残らない）。"""
    if turn_history_needed(state):
        state.turn_history = state.turn_history + (TurnAttack(state.turn_number, state.current_player, pokemon.pokemon_id, pokemon.card, _key(key)),)
    if not history_needed(state):
        return
    pokemon.history = pokemon.history + (AttackUsed(state.turn_number, pokemon.card, _key(key)),)


def note_processed(state: GameState, pokemon: PokemonInPlay, key) -> None:
    """宣言したワザが、相手のワザ・受けたワザを自分のワザとして使った（切りかえた）ときに、処理したワザを今の番の記録に書く。v0.100: プレイヤーの記録（``TurnAttack``）にも書く。"""
    if turn_history_needed(state):
        found = [i for i, record in enumerate(state.turn_history) if isinstance(record, TurnAttack) and record.turn == state.turn_number]
        if len(found) > 1 or (not found and any(isinstance(record, TurnField) and record.turn == state.turn_number for record in state.turn_history)):
            raise RuntimeError(f"今の番のワザのプレイヤーの記録が {len(found)} つ（切りかえの前に宣言の記録がない。エンジンの不具合）")
        if found:  # 記録がなく、今の番の始めの記録もない（v0.99 までの状態の写しで宣言したワザ）なら、記録を作らない
            index = found[0]
            state.turn_history = (*state.turn_history[:index], dataclasses.replace(state.turn_history[index], processed=_key(key)),
                                  *state.turn_history[index + 1:])
    if not history_needed(state):
        return
    found = [i for i, record in enumerate(pokemon.history) if isinstance(record, AttackUsed) and record.turn == state.turn_number]
    if len(found) != 1:
        raise RuntimeError(f"ポケモン {pokemon.pokemon_id} の今の番のワザの記録が {len(found)} つ（切りかえの前に宣言の記録がない。エンジンの不具合）")
    index = found[0]
    pokemon.history = (*pokemon.history[:index], dataclasses.replace(pokemon.history[index], processed=_key(key)), *pokemon.history[index + 1:])


def note_received(state: GameState, *, attacker_player: int, source: int, declared, processed, owner: int, pokemon: PokemonInPlay,
                  damage: int | None = None, reached: str | None = None, voided: tuple[str, str] | None = None) -> None:
    """相手のワザの要素が ``pokemon``（``owner`` の場のポケモン）を対象にしたことを、受けた記録（B・C）に加える。番のプレイヤーのワザで、受けるポケモンの持ち主が
    相手のときだけ記録する（自分へのダメージ・自分の控えへの効果・返す効果のダメージは記録しない）。1 つの番に受ける相手のワザは 1 つ（ワザは番に 1 回）。

    v0.99: ``damage``（のせた最終ダメージ。0 も受けた要素）は、のせた時に ``pokemon`` が持ち主のバトル場にいれば ``active_damage`` にも加える（ダメージの要素ごとに、その時の
    場所で分ける。今の場所・あとの場所からは決めない）。"""
    if owner == attacker_player or attacker_player != state.current_player or not history_needed(state):
        return
    turn = state.turn_number
    found = [i for i, record in enumerate(pokemon.history) if isinstance(record, AttackReceived) and record.turn == turn]
    if found:
        index = found[0]
        record = pokemon.history[index]
        if (record.player, record.source, record.declared, record.processed) != (attacker_player, source, _key(declared), _key(processed)):
            raise RuntimeError(f"ポケモン {pokemon.pokemon_id} が同じ番に 2 つの相手のワザを受けた（ワザは番に 1 回。エンジンの不具合）")
    else:
        record = AttackReceived(turn, pokemon.card, attacker_player, source, _key(declared), _key(processed), active_damage=0)
        index = len(pokemon.history)
        pokemon.history = pokemon.history + (record,)
    if damage is not None:
        if record.active_damage is not None and state.players[owner].active is pokemon:
            record = dataclasses.replace(record, active_damage=record.active_damage + damage)
        record = dataclasses.replace(record, damage=record.damage + damage)
        if "damage" not in record.reached:
            record = dataclasses.replace(record, reached=record.reached + ("damage",))
    if reached is not None and reached not in record.reached:
        record = dataclasses.replace(record, reached=record.reached + (reached,))
    if voided is not None:
        if voided[1] not in VOID_REASONS:
            raise ValueError(f"受けなかった理由 {voided[1]!r} は未定義")
        record = dataclasses.replace(record, voided=record.voided + (voided,))
    pokemon.history = (*pokemon.history[:index], record, *pokemon.history[index + 1:])


def unreach(state: GameState, owner: int, pokemon: PokemonInPlay, element: str, reason: str) -> None:
    """効果の要素を受けたと記録したあとで、その効果が起こらなかった（［めんえき］で特殊状態にならなかった）ときに、受けた要素から除き、受けなかった要素に移す。"""
    turn = state.turn_number
    for index, record in enumerate(pokemon.history):
        if isinstance(record, AttackReceived) and record.turn == turn and element in record.reached:
            pokemon.history = (*pokemon.history[:index],
                               dataclasses.replace(record, reached=tuple(k for k in record.reached if k != element), voided=record.voided + ((element, reason),)),
                               *pokemon.history[index + 1:])
            return


def clear_history(pokemon: PokemonInPlay) -> None:
    """進化・退化したポケモンの履歴を消す（p.310「進化前のポケモンとは別のポケモンとしてあつかわれ」。kyuura の GR-2000-P310-EVOLUTION・GR-2000-P324-DEVOLUTION）。"""
    pokemon.history = ()


def prune(state: GameState) -> None:
    """番の最初に、2 つ前の番より古い記録を消す（読む効果は 1 つ前・2 つ前の番だけを読む）。v0.100: プレイヤーの記録（``turn_history``）も同じ範囲だけ残す。"""
    oldest = state.turn_number - KEPT_TURNS
    for p in state.players:
        for pokemon in p.in_play():
            if pokemon.history and any(record.turn < oldest for record in pokemon.history):
                pokemon.history = tuple(record for record in pokemon.history if record.turn >= oldest)
    if state.turn_history and any(record.turn < oldest for record in state.turn_history):
        state.turn_history = tuple(record for record in state.turn_history if record.turn >= oldest)


def _field_of(state: GameState, player: int) -> tuple[tuple[int, ...], int]:
    """``player`` の場のポケモンのカード（おもてのポケモンの重なり・のせたカード。場の順）と、うらのカードの数。"""
    cards: list[int] = []
    face_down = 0
    for pokemon in state.players[player].in_play():
        if state.is_face_down(pokemon):
            face_down += 1
        else:
            cards.extend(pokemon.cards())
    return tuple(cards), face_down


def note_turn_start(state: GameState) -> None:
    """v0.100: 番の最初（``procedures.begin_turn``。番の数・番のプレイヤーを変え、古い記録を消したあと）に、番でないプレイヤーの場のポケモンのカードを記録する（``TurnField``）。
    プレイヤーの記録を読むカードがなければ何もしない。"""
    if state.current_player is None or state.turn_number < 1 or not turn_history_needed(state):
        return
    owner = 1 - state.current_player
    cards, face_down = _field_of(state, owner)
    state.turn_history = state.turn_history + (TurnField(state.turn_number, owner, cards, face_down),)


def note_entered(state: GameState, owner: int, pokemon: PokemonInPlay) -> None:
    """v0.100: 番でないプレイヤー ``owner`` のポケモンが、その番に場に出た（相手のポケモンの笛・エリカの香水。``zones.enter_play`` のあと）ことを、今の番の ``TurnField`` に
    加える。番のプレイヤーのポケモン・対戦準備（番が 1 より前）・プレイヤーの記録を読むカードのない対戦では何もしない。"""
    if state.current_player is None or state.turn_number < 1 or owner == state.current_player or not turn_history_needed(state):
        return
    found = [i for i, record in enumerate(state.turn_history)
             if isinstance(record, TurnField) and record.turn == state.turn_number and record.player == owner]
    if not found:
        # 今の番の始めの記録がない（v0.99 までの状態の写し・番の途中から作った状態）。途中から記録を作らない（番の始めの場を表せない）。読むときにエンジンの情報の不足として止める
        return
    if len(found) != 1:
        raise RuntimeError(f"今の番の場のカードの記録が {len(found)} つ（エンジンの不具合）")
    index = found[0]
    record = state.turn_history[index]
    if state.is_face_down(pokemon):
        record = dataclasses.replace(record, face_down=record.face_down + 1)
    else:
        record = dataclasses.replace(record, cards=record.cards + tuple(uid for uid in pokemon.cards() if uid not in record.cards))
    state.turn_history = (*state.turn_history[:index], record, *state.turn_history[index + 1:])


def turn_attack(state: GameState, turn: int) -> TurnAttack | None:
    """v0.100: 番 ``turn`` に番のプレイヤーが使ったワザの記録（なければ None。ワザを使わなかったか、記録していない。区別は ``turn_field`` があるかで決める）。"""
    found = [record for record in state.turn_history if isinstance(record, TurnAttack) and record.turn == turn]
    return found[0] if found else None


def turn_field(state: GameState, turn: int, player: int) -> TurnField | None:
    """v0.100: 番 ``turn``（``player`` の相手の番）に ``player`` の場にいたポケモンのカードの記録（記録していなければ None）。"""
    found = [record for record in state.turn_history if isinstance(record, TurnField) and record.turn == turn and record.player == player]
    return found[0] if found else None


def _this_card(pokemon: PokemonInPlay, record) -> bool:
    """記録が今の「このカード」のものか（いちばん上のカードが同じで、今の姿になった番より前でない）。進化・退化で消しているので、不変条件が二重に確かめる。"""
    return record.card == pokemon.card and record.turn >= pokemon.current_form_turn


def used_on(pokemon: PokemonInPlay, turn: int) -> list[AttackUsed]:
    """``turn`` の番にこのポケモン（このカード）が使ったワザの記録。"""
    return [record for record in pokemon.history if isinstance(record, AttackUsed) and record.turn == turn and _this_card(pokemon, record)]


def received_on(pokemon: PokemonInPlay, turn: int) -> AttackReceived | None:
    """``turn`` の番にこのポケモン（このカード）が受けた相手のワザの記録（なければ None）。"""
    found = [record for record in pokemon.history if isinstance(record, AttackReceived) and record.turn == turn and _this_card(pokemon, record)]
    return found[0] if found else None


# v0.99: 受けたダメージの場所が分からない記録（v0.98 までの記録の写し。``AttackReceived.active_damage`` が None）を、場所で分けて読む必要があるとき。エンジンの持つ情報の
# 不足で、研究上の未解決（裁定の問い）ではない
DAMAGE_PLACE_UNKNOWN_CODE = "UNSUPPORTED_HISTORY_DAMAGE_PLACE_UNKNOWN"


def damage_places(record: AttackReceived) -> tuple[int, int]:
    """受けた記録の、ワザによるダメージの (バトル場で受けた分, ベンチで受けた分)（v0.99）。どちらも最終ダメージの合計で、0 は「受けなかった」（p.319・p.321）。

    合計が 0 なら、場所が分からない記録でも (0, 0)（のせた量はどれも 0 以上なので、どの分け方でも 0）。合計が 0 より大きく場所が分からない記録は、バトル場・ベンチのどちらかに
    寄せず（合計をバトル場の分・0 にしない）、``UnsupportedError``（``DAMAGE_PLACE_UNKNOWN_CODE``）。"""
    if record.active_damage is None:
        if record.damage == 0:
            return 0, 0
        raise UnsupportedError(DAMAGE_PLACE_UNKNOWN_CODE, f"受けた記録（{record.turn} 番・カード {record.card}）のダメージ {record.damage} を受けた場所が記録にない（v0.98 までの"
                               "記録の写し）。バトル場で受けた分を、合計・0 で代用しない（エンジンの持つ情報の不足。docs/unown-perform-help-history-v0.99.md 6 章）")
    return record.active_damage, record.damage - record.active_damage


# v0.100（docs/sketch-perish-song-history-v0.100.md 5 章）: 名前の決まったワザを受けていたか（``named_attack_received``）
RECEIVED = "received"  # 受けた（どれかの要素を受けた。［めんえき］で特殊状態にならなかった効果の要素も受けた。v0.62 の記録の意味）
NOT_RECEIVED = "not_received"  # 受けていない（記録がない・ほかのワザ・どの要素も「ワザをうけない」状態・「とうめい」で受けなかった）
RECEIVED_UNDETERMINED = "undetermined"  # 受けたことになるかが決まらない（効果だけを無効にする効果で受けなかった・まねたワザ）


def named_attack_received(state: GameState, pokemon: PokemonInPlay, turn: int, name: str) -> tuple[str, str]:
    """v0.100: ``turn`` の番に、このポケモン（このカード）が名前 ``name`` の相手のワザを受けていたか（``RECEIVED``・``NOT_RECEIVED``・``RECEIVED_UNDETERMINED``, 理由の文）。ムウマの
    「ほろびのうた」の「前の自分の番に「やみのひとみ」を受けていたなら」。受けた記録（``received_on``。使った記録・今の特殊状態からは決めない）の、ワザの名前と受けた要素で決める。

    - ワザは、受けた記録の処理したワザの名前で照らす（同じ名前の別のカードのワザも同じ。ワザの位置・カードで限らない）。宣言したワザと処理したワザが違う（「ゆびをふる」「スケッチ」で
      まねたワザ）なら、どちらかがその名前のとき、受けたワザがどちらかが決まらない（v0.62 のピジョンの MM1 と同じ記録の性質）
    - どれかの要素を受けた・［めんえき］で特殊状態にならなかった（効果の要素は受けた）なら受けた。どの要素も「ワザをうけない」状態・「とうめい」で受けなかったなら受けていない（v0.62 の
      ピジョンの「オウムがえし」の「受けた」と同じ記録の意味）。ほかの理由（効果だけを無効にする効果など）で受けなかったなら決まらない"""
    record = received_on(pokemon, turn)
    if record is None:
        return NOT_RECEIVED, f"{turn} 番に受けた相手のワザの記録がない"

    def name_of(key) -> str:
        return state.definitions[key[0]].attacks[key[1]].name_ja

    if record.declared != record.processed:
        if name in (name_of(record.declared), name_of(record.processed)):
            return RECEIVED_UNDETERMINED, (f"{turn} 番に受けたワザは、宣言したワザ「{name_of(record.declared)}」が処理したワザ「{name_of(record.processed)}」"
                                           "（まねたワザ。どちらを受けたかが決まらない）")
        return NOT_RECEIVED, f"{turn} 番に受けたワザは「{name_of(record.processed)}」"
    if name_of(record.processed) != name:
        return NOT_RECEIVED, f"{turn} 番に受けたワザは「{name_of(record.processed)}」"
    if record.reached or any(reason == VOID_IMMUNE for _, reason in record.voided):
        return RECEIVED, f"{turn} 番に「{name}」を受けた（受けた要素 {list(record.reached)}・受けなかった要素 {list(record.voided)}）"
    if all(reason in (VOID_ATTACK_BARRIER, VOID_EVADED) for _, reason in record.voided):
        return NOT_RECEIVED, f"{turn} 番の「{name}」の要素を、どれも受けなかった（{list(record.voided)}）"
    return RECEIVED_UNDETERMINED, f"{turn} 番の「{name}」の要素を受けなかった（{list(record.voided)}。受けたことになるかが決まらない）"


def other_received_on(pokemon: PokemonInPlay, turn: int) -> bool:
    """``turn`` の番にこのポケモン（このカード）がワザ以外でダメージ・効果を受けたか。"""
    return any(isinstance(record, OtherReceived) and record.turn == turn and _this_card(pokemon, record) for record in pokemon.history)


# ---------------------------------------------------------------- ワザ以外で受けたこと（コマンドの前後の比べ）

_PROBE = "_history_probe"


def _snapshot(state: GameState, owner: int) -> dict[int, tuple]:
    p = state.players[owner]
    pokemon = {}
    for zone, items in (("active", [p.active] if p.active is not None else []), ("bench", p.bench)):
        for item in items:
            pokemon[item.pokemon_id] = (zone, item.card, item.evolution_stack, item.disguise, item.damage, item.conditions, tuple(item.energy),
                                        tuple(t.card for t in item.trainers), item.persistent_effects, item.type_shift)
    return pokemon


def open_probe(state: GameState) -> None:
    """ワザ・番の終わり以外のコマンドの前に、番でないプレイヤーの場のポケモンの状態を写す（``engine._apply``）。番が 1 より前・履歴を読むカードがなければ何もしない。"""
    if state.current_player is None or state.turn_number < 1 or not history_needed(state):
        return
    owner = 1 - state.current_player
    setattr(state, _PROBE, (state.turn_number, owner, _snapshot(state, owner)))


def close_probe(state: GameState) -> None:
    """``open_probe`` の写しと今の状態を比べ、変わった場のポケモン（両方にいる）に ``OtherReceived`` を記録する（番の終わりの前・コマンドの終わり。``resolution.flow``・
    ``engine._apply``）。写しがなければ何もしない。"""
    probe = state.__dict__.pop(_PROBE, None)
    if probe is None:
        return
    turn, owner, before = probe
    if state.turn_number != turn:
        raise RuntimeError("ワザ以外で受けたことの比べの前に番が変わった（番の終わりで比べていない。エンジンの不具合）")
    after = _snapshot(state, owner)
    for p in state.players[owner].in_play():
        old = before.get(p.pokemon_id)
        new = after.get(p.pokemon_id)
        if old is not None and new is not None and old != new and not other_received_on(p, turn):
            p.history = p.history + (OtherReceived(turn, p.card),)
