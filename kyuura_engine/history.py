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

このモジュールは ``engine.py``・``resolution`` を読み込まない（``state``・``effects`` だけ。``effects`` は使うときに読み込む）。
"""

from __future__ import annotations

import dataclasses

from .state import AttackReceived, AttackUsed, GameState, OtherReceived, PokemonInPlay

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
    """この対戦に、履歴を読むワザ（効果の登録の ``reads_history``）を持つカードがあるか。対戦のカードの定義（両方のデッキ）と効果の登録表から求める（状態に持たない）。
    ないときは履歴を記録しない（v0.61 までと同じ状態・書き出し）。相手のカードのワザを自分のワザとして使う（「ゆびをふる」）ときも、そのワザは対戦のカードにある。"""
    for definition in state.definitions.values():
        for attack in definition.attacks:
            effect = state.effects.attack_effect(definition.id, attack, definition.attacks)
            if effect is not None and getattr(effect, "reads_history", False):
                return True
    return False


def _key(key) -> tuple[str, int]:
    return (key.card_id, key.attack_index)


def note_used(state: GameState, pokemon: PokemonInPlay, key) -> None:
    """ワザの宣言（p.309 の手順 3）のときに、使ったワザ（A）を記録する。"""
    if not history_needed(state):
        return
    pokemon.history = pokemon.history + (AttackUsed(state.turn_number, pokemon.card, _key(key)),)


def note_processed(state: GameState, pokemon: PokemonInPlay, key) -> None:
    """宣言したワザが、相手のワザ・受けたワザを自分のワザとして使った（切りかえた）ときに、処理したワザを今の番の記録に書く。"""
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
    相手のときだけ記録する（自分へのダメージ・自分の控えへの効果・返す効果のダメージは記録しない）。1 つの番に受ける相手のワザは 1 つ（ワザは番に 1 回）。"""
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
        record = AttackReceived(turn, pokemon.card, attacker_player, source, _key(declared), _key(processed))
        index = len(pokemon.history)
        pokemon.history = pokemon.history + (record,)
    if damage is not None:
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
    """番の最初に、2 つ前の番より古い記録を消す（読む効果は 1 つ前・2 つ前の番だけを読む）。"""
    oldest = state.turn_number - KEPT_TURNS
    for p in state.players:
        for pokemon in p.in_play():
            if pokemon.history and any(record.turn < oldest for record in pokemon.history):
                pokemon.history = tuple(record for record in pokemon.history if record.turn >= oldest)


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
