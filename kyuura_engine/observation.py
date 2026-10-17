"""プレイヤーに渡す観測（v0.47。docs/fossil-hidden-info-v0.47.md 5 章）。

ゲームの状態（``GameState``）とログ（``GameState.log``）は、引いたカード・山札とサイドの中身・相手の手札などの見えない情報を含む、内部の完全な記録
です（エンジンの処理と監査に使う）。この部品は、それをプレイヤー（または観戦者）に渡すときに、その人が見てよい情報だけを取り出します。画面・通信は
作らず、データの形と約束（だれに何が見えるか）だけを決めます。状態を変えず、乱数を使いません。

- ``observe(state, viewer)``: その時点の盤面の観測（``viewer`` は 0・1 のプレイヤー、``None`` は観戦者）。
  - 手札: 持ち主にだけカードが見える（ほかの人は枚数だけ）。相手の［おみとおし］（オムナイト）がはたらいているあいだは、全員に見える
    （``effects.hand_revealed_by``。はたらかなくなったら、その時点から見えない。前の観測で見えていた情報は、その観測の値として残る）
  - 山札・サイド: だれにも中身は見えない（枚数だけ。カードの uid も渡さない。uid の付け方はデッキリストの順で決まるので、uid から中身がわかる）
  - トラッシュ・場のポケモン（重なったカード・ついているカード・ダメージ・特殊状態・持続する効果）・使用中のトレーナー: 全員に見える。対戦準備で
    出したポケモンは、表にする（ログ ``reveal_pokemon``。最初の番の前）までは持ち主にだけ見える
  - 保留中の決定: 種類・決めるプレイヤー・選ぶ数は全員に見える。選べるものは決めるプレイヤーにだけ渡す。選べるものがカードなら、決めるプレイヤーに
    見えるカード（公開のゾーン・自分の手札・山札をさがす効果のその山札・見たカード）にだけカードの id を添える。位置で選ぶ決定（サイド・相手の手札・
    ［スパイ］の見る場所）は位置だけを渡す（選ぶ前に内容を漏らさない）
- ``visible_log(state, viewer)``: ログを、その人が見てよい項目だけにした写し。見えない項目は除き、``"hidden"`` に項目の名前と（並びなら）枚数を書く。
  イベントの種類ごとの見える範囲は ``PRIVATE_FIELDS``（見える人を決める関数）と ``PUBLIC_EVENTS`` に書く。どちらにもない種類は ``ValueError``
  （新しいイベントを加えたら、見える範囲を決めて表に加える。黙って全部を見せない）

内部の完全な記録（``GameState``・``GameState.log``・``state_to_dict``）を、観測のかわりにプレイヤーに渡さないでください。
"""

from __future__ import annotations

from typing import Any, Callable

from .decisions import (
    ARRANGE_DECK_TOP,
    ATTACH_FROM_DECK,
    ATTACH_FROM_DISCARD,
    ATTACH_FROM_HAND,
    ATTACH_TO_BENCH,
    BENCH_FROM_DECK,
    BENCH_FROM_DISCARD,
    DAMAGE_STEP_ORDER,
    DISCARD_ENERGY,
    DISCARD_FROM_HAND,
    DISCARD_OPPONENT_ENERGY,
    DISCARD_TO_DECK,
    DISCARD_TO_DECK_TOP,
    ENTRY_POWER,
    FORCED_SWITCH,
    HAND_TO_DECK,
    KO_PREVENTION,
    MOVE_ENERGY,
    MOVE_OPPONENT_ENERGY,
    PEEK_CARD,
    POST_KNOCKOUT_POWER,
    PROMOTE_ACTIVE,
    RECOVER_ENERGY,
    RECOVER_POKEMON,
    RECOVER_TRAINER,
    REMOVE_COUNTERS,
    RETRIEVE_ENERGY,
    RETURN_ENERGY,
    RETURN_TO_DECK,
    SEARCH_DECK,
    SELECT_ATTACK,
    SELECT_COLOR,
    SELECT_DECK_OWNER,
    SELECT_DEVOLVE_COUNT,
    SELECT_EVOLUTION_CARD,
    SELECT_HAND_CARD,
    SELECT_LOOK_COUNT,
    SELECT_OPPONENT_ATTACK,
    SELECT_POKEMON,
    SELECT_PRIZE_CARD,
    SELECT_SPECIAL_CONDITION,
    TAKE_PRIZE,
)
from .effects import (
    COLORS, attack_of, available_attacks, current_form, hand_revealed_by, max_hp, powers_of, resistance_of, type_readings, type_shift_determined, weakness_of,
)
from .state import GameState, PokemonInPlay

VIEWERS = (0, 1, None)

# 決定の選べるものの意味（決定の種類 → 意味）。``"card"`` はカードの uid、``"pokemon"`` は場のポケモンの番号、``"position"`` は位置（サイド・手札。
# 見えないカードを位置で選ぶ）、``"peek_target"`` は［スパイ］の見る場所の番号（``context`` の ``"targets"`` の位置）、``"number"`` はそのほかの数
# （ワザの位置・順番の番号・枚数・プレイヤーなど）
OPTION_MEANINGS: dict[str, str] = {
    TAKE_PRIZE: "position", SELECT_PRIZE_CARD: "position", SELECT_HAND_CARD: "position",
    PEEK_CARD: "peek_target",
    PROMOTE_ACTIVE: "pokemon", SELECT_POKEMON: "pokemon", FORCED_SWITCH: "pokemon", KO_PREVENTION: "pokemon", ATTACH_TO_BENCH: "pokemon",
    ENTRY_POWER: "pokemon",
    DISCARD_ENERGY: "card", RECOVER_ENERGY: "card", POST_KNOCKOUT_POWER: "card", DISCARD_FROM_HAND: "card", SEARCH_DECK: "card",
    RETURN_TO_DECK: "card", SELECT_EVOLUTION_CARD: "card", RETRIEVE_ENERGY: "card", DISCARD_OPPONENT_ENERGY: "card", RECOVER_TRAINER: "card",
    ATTACH_FROM_DISCARD: "card", BENCH_FROM_DECK: "card", ATTACH_FROM_DECK: "card", RETURN_ENERGY: "card", MOVE_ENERGY: "card",
    RECOVER_POKEMON: "card", HAND_TO_DECK: "card", DISCARD_TO_DECK_TOP: "card", MOVE_OPPONENT_ENERGY: "card", ATTACH_FROM_HAND: "card",
    ARRANGE_DECK_TOP: "card",
    DAMAGE_STEP_ORDER: "number", SELECT_ATTACK: "number", SELECT_OPPONENT_ATTACK: "number", SELECT_SPECIAL_CONDITION: "number",
    REMOVE_COUNTERS: "number", SELECT_DECK_OWNER: "number", SELECT_LOOK_COUNT: "number",
    SELECT_DEVOLVE_COUNT: "number",  # v0.50: 退化スプレーではがす枚数
    BENCH_FROM_DISCARD: "card",  # v0.51: トラッシュ（公開）のたねポケモンのカード
    DISCARD_TO_DECK: "card",  # v0.53: 夜の廃品回収（トラッシュ（公開）のカード）
    SELECT_COLOR: "color",  # v0.48: ``effects.COLORS`` の位置（選べるものに色の名前を添える）
}
# 山札の中身を選べるものにする決定（決めるプレイヤーが、効果でその山札をさがす・見たカードを並べる）。選べるもののカードは、決めるプレイヤーに見える
DECK_REVEALING_KINDS = frozenset({SEARCH_DECK, BENCH_FROM_DECK, ATTACH_FROM_DECK, ARRANGE_DECK_TOP})


def _check_viewer(viewer) -> None:
    if viewer not in VIEWERS:
        raise ValueError(f"観測する人 {viewer!r} は 0・1（プレイヤー）か None（観戦者）")


def hand_visible_to(state: GameState, owner: int, viewer: int | None) -> bool:
    """プレイヤー ``owner`` の手札のカードが ``viewer`` に見えるか（持ち主か、相手の［おみとおし］がはたらいている）。"""
    return viewer == owner or bool(hand_revealed_by(state, owner))


def _card(state: GameState, uid: int) -> dict[str, Any]:
    return {"card": uid, "card_id": state.cards[uid].card_id}


def _pokemon(state: GameState, pokemon: PokemonInPlay) -> dict[str, Any]:
    """場のポケモン。v0.48: ``hp`` は今有効な最大HP（``effects.max_hp``。［ガスのからだ］・「きょだいか」を当てはめた値。エンジンの処理と同じ値）。``pokemon_type``・
    ``weakness``・``resistance`` も今有効な値（テクスチャー・［へんしょく］）。［へんしょく］で変えた色が有効か決まらない（VS1）ときは ``pokemon_type`` は None で、
    ``pokemon_type_readings`` に 2 つの読み方（変えた色・カードの定義の色）を書く（エンジンは読み方で結果が変わる処理を止める）。``type_shift`` は記録そのもの。"""
    definition = state.card_def(pokemon.card)
    readings = type_readings(state, pokemon)
    resistance, resistance_value = resistance_of(state, pokemon)
    shift = pokemon.type_shift
    return {
        "pokemon_id": pokemon.pokemon_id,
        **_card(state, pokemon.card),
        "name_ja": definition.name_ja,
        "play_role": definition.play_role,
        "hp": max_hp(state, pokemon),
        "printed_hp": definition.hp,
        "pokemon_type": _color(readings[0]) if len(readings) == 1 else None,
        "pokemon_type_readings": [_color(color) for color in readings],
        "weakness": _color(weakness_of(state, pokemon)),
        "resistance": _color(resistance),
        "resistance_value": resistance_value,
        "type_shift": None if shift is None else {"color": shift.color.value, "turn": shift.turn, "returned_to_bench": shift.returned_to_bench,
                                                  "determined": type_shift_determined(state, pokemon)},
        "evolution_stack": [_card(state, uid) for uid in pokemon.evolution_stack],
        "damage": pokemon.damage,
        "energy": [_card(state, uid) for uid in pokemon.energy],
        "trainers": [_card(state, t.card) for t in pokemon.trainers],
        "special_conditions": list(pokemon.conditions.names()),
        "persistent_effects": [effect.kind for effect in pokemon.persistent_effects],
        # v0.49（docs/virtual-attacks-transformation-v0.49.md 9 章）: 実際のカード（``card``・``card_id``・``name_ja``。いちばん上のポケモンのカード）と、今の姿
        # （``form``。［へんしん］で同じカードとしてあつかう相手のカード・「ばける」でのせたカード）・のせたカード（``disguise``）・今持つワザ（``attacks``。印刷した
        # カード・位置・持ち方・供給するポケモン・選ぶと止める理由のコード）・今持つ特殊能力（``powers``。印刷したカード・位置）を分けて書く。どれも表のカード
        "form": _form(state, pokemon),
        "disguise": None if pokemon.disguise is None else _card(state, pokemon.disguise),
        # v0.50（docs/mew-devolution-spray-v0.50.md 7 章）: 最後に退化した番（いまの姿になった番の決まり方の材料。退化していなければ None）。進化した番・場に出た番は
        # これまでどおり書かない（ログからわかる）
        "devolved_turn": pokemon.devolved_turn,
        "attacks": [
            {**_card(state, option.card), "attack_index": option.attack_index, "name_ja": attack_of(state, option.key).name_ja, "route": option.route,
             "provider": option.provider, "problem": None if option.problem is None else option.problem[0]}
            for option in available_attacks(state, pokemon)
        ],
        "powers": [{**_card(state, slot.card), "power_index": slot.key.power_index, "name_ja": slot.power.name_ja} for slot in powers_of(state, pokemon)],
    }


def _form(state: GameState, pokemon: PokemonInPlay) -> dict[str, Any]:
    """場のポケモンの今の姿（v0.49。``effects.current_form``）。``kind`` は ``printed``・``transform``・``disguise``。"""
    form = current_form(state, pokemon)
    return {**_card(state, form.card), "name_ja": state.card_def(form.card).name_ja, "kind": form.kind, "defender": form.defender}


def _color(color) -> str | None:
    return None if color is None else color.value


def _visible_to_decider(state: GameState, uid: int, viewer: int, kind: str) -> bool:
    """決定の選べるもののカード ``uid`` が、決めるプレイヤー ``viewer`` に見えるか。"""
    if kind in DECK_REVEALING_KINDS:
        return True  # 効果で山札をさがす・見たカードを並べる（選べるものは決めるプレイヤーが見ているカード）
    for owner, p in enumerate(state.players):
        if uid in p.discard:
            return True
        if uid in p.hand:
            return hand_visible_to(state, owner, viewer)
        if uid in p.deck or uid in p.prizes:
            return False
        for pokemon in p.in_play():
            if (uid == pokemon.card or uid == pokemon.disguise or uid in pokemon.evolution_stack or uid in pokemon.energy
                    or any(t.card == uid for t in pokemon.trainers)):
                return True
    used = state.trainer_in_use
    return used is not None and used.card == uid


def _decision(state: GameState, viewer: int | None) -> dict[str, Any] | None:
    d = state.decision
    if d is None:
        return None
    view: dict[str, Any] = {"kind": d.kind, "player": d.player, "min_choices": d.min_choices, "max_choices": d.max_choices,
                            "option_count": len(d.options)}
    if viewer != d.player:
        return view  # 選べるもの（とその中身）は決めるプレイヤーだけに渡す
    meaning = OPTION_MEANINGS.get(d.kind)
    if meaning is None:
        raise ValueError(f"決定の種類 {d.kind!r} の選べるものの意味が決まっていない（OPTION_MEANINGS に加える）")
    options = []
    for value in d.options:
        option: dict[str, Any] = {"value": value}
        if meaning == "card" and _visible_to_decider(state, value, viewer, d.kind):
            option["card_id"] = state.cards[value].card_id
        elif meaning == "color":
            option["color"] = COLORS[value].value
        elif meaning == "peek_target":
            target = d.context_value("targets")[value]
            option["target"] = {"zone": target[0], "owner": target[1], **({} if target[0] == "deck" else {"position": target[2]})}
        if d.kind in (SELECT_ATTACK, SELECT_OPPONENT_ATTACK):
            # v0.49: 相手のワザを選ぶ決定の選べるものが指すワザ（印刷したカードの id・位置・名前。表のカード）
            key = _chosen_attack(state, d, value)
            if key is not None:
                option["attack"] = {"card_id": key[0], "attack_index": key[1], "name_ja": state.definitions[key[0]].attacks[key[1]].name_ja}
        options.append(option)
    view["options"] = options
    view["meaning"] = meaning
    return view


def _chosen_attack(state: GameState, d, value: int) -> tuple[str, int] | None:
    """相手のワザを選ぶ決定（ゆびをふる・ドわすれ）の選べるもの ``value`` が指すワザの (カードの id, 位置)（v0.49）。決定の続きの情報の並び（``copy_attacks``・
    ``lock_attacks``）があればその位置、なければ v0.48 までの形（``copy_from`` のカード・ドわすれの相手のいちばん上のカードのワザの位置）。"""
    keys = d.context_value("copy_attacks") or d.context_value("lock_attacks")
    if keys is not None:
        return tuple(keys[value])
    copy_from = d.context_value("copy_from")
    if copy_from is not None:
        return copy_from, value
    target = d.context_value("target")
    found = state.find_pokemon(target) if target is not None else None
    if found is None:
        return None
    return state.cards[found[1].card].card_id, value


def observe(state: GameState, viewer: int | None) -> dict[str, Any]:
    """``viewer``（0・1・``None`` は観戦者）に見える、その時点の盤面（モジュールの説明の範囲）。状態を変えない。"""
    _check_viewer(viewer)
    face_down = state.turn_number == 0  # 対戦準備で出したポケモンは、最初の番の前に表にする（ログ reveal_pokemon）
    players = []
    for owner, p in enumerate(state.players):
        visible_hand = hand_visible_to(state, owner, viewer)
        board_visible = not face_down or viewer == owner
        players.append({
            "player": owner,
            "hand": {
                "count": len(p.hand),
                "cards": [_card(state, uid) for uid in p.hand] if visible_hand else None,
                "revealed_by": [list(source) for source in hand_revealed_by(state, owner)],
            },
            "deck": {"count": len(p.deck)},
            "prizes": {"count": len(p.prizes)},
            "discard": [_card(state, uid) for uid in p.discard],
            "active": (_pokemon(state, p.active) if board_visible else {"face_down": True}) if p.active is not None else None,
            "bench": [_pokemon(state, b) if board_visible else {"face_down": True} for b in p.bench],
        })
    used = state.trainer_in_use
    return {
        "viewer": viewer,
        "turn": state.turn_number,
        "current_player": state.current_player,
        "phase": state.phase.value,
        "players": players,
        "trainer_in_use": None if used is None else {"player": used.player, **_card(state, used.card)},
        "trainer_locks": [{"player": lock.player, "source_player": lock.source_player, "effect": lock.effect, "expires_turn": lock.expires_turn}
                          for lock in state.trainer_locks],
        "decision": _decision(state, viewer),
        "result": None if state.result is None else {"outcome": state.result.outcome, "winner": state.result.winner},
    }


# ---------------------------------------------------------------- ログ


def _only_player(event, viewer) -> bool:
    return viewer is not None and viewer == event.get("player")


def _nobody(event, viewer) -> bool:
    return False


def _looked_card(event, viewer) -> bool:
    """見たプレイヤーと、手札のカードならその持ち主（自分の手札のどの位置のカードかを知っている）。"""
    return viewer is not None and (viewer == event.get("player") or (event.get("zone") == "hand" and viewer == event.get("owner")))


def _taken_deck_top(event, viewer) -> bool:
    """てつだうふり（v0.45）: トラッシュに置いたら公開。手札に加えたら、見たプレイヤーと持ち主。"""
    return event.get("destination") == "discard" or (viewer is not None and viewer in (event.get("looker"), event.get("player")))


# 見えない項目のあるイベント: 種類 → (見えない項目, その項目が見える人か)
PRIVATE_FIELDS: dict[str, tuple[tuple[str, ...], Callable[[Any, int | None], bool]]] = {
    "game_created": (("seed",), _nobody),  # seed から山札の並び・コインがわかる
    "draw": (("cards",), _only_player),
    "place_starting_pokemon": (("active", "bench"), _only_player),  # 表にする（reveal_pokemon）までは裏
    "take_prize": (("card",), _only_player),
    "search_deck": (("card",), _only_player),  # 見せる指示がない（v0.22 の CS14）
    "hand_to_deck": (("cards",), _only_player),  # 見せずに山札にもどす（v0.44・v0.46・v0.47）
    "look_at_card": (("card",), _looked_card),  # v0.47 の［スパイ］・おどろかす
    "look_at_deck_top": (("cards",), _only_player),  # v0.47 のみらいよち（見る）
    "arrange_deck_top": (("cards",), _only_player),  # v0.47 のみらいよち（もどす並び）
    "take_deck_top": (("card",), _taken_deck_top),
    "trainer_take_none": (("reason",), _only_player),  # v0.53: 山札をさがして選べるカードがなかったか・選ばなかったかは、山札の中身の情報
}
# 見えない項目のないイベント（どの項目も全員に見える。公開のゾーン・場・コイン・決まった結果）
PUBLIC_EVENTS = frozenset({
    "attach_energy", "attach_energy_from_deck", "attach_energy_from_deck_none", "attach_energy_from_discard",
    "attach_energy_from_hand", "attach_trainer", "attack", "attack_attach_energy", "attack_check", "attack_evaded", "attack_failed", "attack_heal",
    "bench_from_deck", "bench_from_deck_declined", "bench_from_deck_none",
    "bench_from_discard", "bench_from_discard_declined", "bench_from_discard_none",  # v0.51: トラッシュと場は公開の情報
    "coin_flip", "confusion_check", "confusion_damage", "copy_attack",
    "counterattack", "counterattack_skipped", "damage", "damage_prevented", "deck_out", "destiny_bond", "devolve", "devolve_declined", "devolve_none",
    "discard_attached_cards",
    "discard_attached_energy", "discard_attached_trainer", "discard_energy", "discard_energy_failed", "discard_from_deck", "discard_from_hand",
    "discard_from_play", "discard_hand", "discard_trainer", "disguise", "disguise_removed", "drain_heal", "drain_heal_skipped", "effect_prevented", "effect_skipped",
    "end_turn_without_attack", "energy_burn", "entry_power_declined", "evade_check", "evolution_permission", "evolve", "evolve_from_deck_declined",
    "evolve_from_deck_none", "forced_switch", "forced_switch_skipped", "game_end", "halted", "janken", "knock_out", "ko_prevented",
    "ko_prevention_declared", "ko_prevention_declined", "ko_prevention_failed", "look_at_deck_top_none", "move_damage_counter", "move_energy",
    "move_opponent_energy", "mulligan", "mulligan_draw", "once_attack_recorded", "persistent_effect_added", "persistent_effect_removed",
    "persistent_effect_skipped", "place_damage_counters", "play_to_bench", "play_trainer", "play_trainer_as_pokemon", "poison_damage",
    "pokemon_check", "pokemon_power", "post_knockout_power_declared", "post_knockout_power_declined", "power_attach_energy", "power_confusion",
    "power_confusion_skipped", "power_damage", "power_heal", "promote_active", "put_discard_on_deck_top", "recover_energy", "recover_pokemon",
    "recall", "recover_pokemon_none", "recover_trainer", "remove_all_damage_counters", "remove_damage_counters", "retaliation", "retaliation_skipped",
    "retreat", "retreat_failed", "retreat_failure_cleared", "retrieve_energy", "return_energy_to_hand", "return_in_play_to_deck",
    "return_in_play_to_hand",
    "return_basic_to_hand",  # v0.52: ポケモン回収（場のカード → 手札・トラッシュ。手札にもどしたカードは場にあったので公開）
    "discard_to_deck", "retrieve_trainer",  # v0.53: 夜の廃品回収（見せて山札にもどす）・ダウジングマシーン（トラッシュ → 手札）。トラッシュは公開の情報
    "return_to_deck", "return_to_hand", "reveal_from_deck", "reveal_from_deck_declined", "reveal_from_deck_none",
    "reveal_pokemon", "set_prizes", "shuffle", "sleep_check", "special_condition", "special_condition_prevented", "special_conditions_removed",
    "swap_damage_counters", "swap_prize_with_deck_top", "switch", "switch_declined", "trainer_lock_added", "trainer_lock_removed", "turn_end",
    "turn_start", "type_shift",
})


def visible_event(event, viewer: int | None) -> dict[str, Any]:
    """ログのイベント 1 つを、``viewer`` に見える項目だけにした写し。"""
    kind = event["kind"]
    if kind in PRIVATE_FIELDS:
        fields, sees = PRIVATE_FIELDS[kind]
        if sees(event, viewer):
            return dict(event)
        copy = {name: value for name, value in event.items() if name not in fields}
        copy["hidden"] = {name: (len(event[name]) if isinstance(event[name], (tuple, list)) else None) for name in fields if name in event}
        return copy
    if kind in PUBLIC_EVENTS:
        return dict(event)
    raise ValueError(f"ログのイベント {kind!r} の見える範囲が決まっていない（observation.PRIVATE_FIELDS・PUBLIC_EVENTS に加える）")


def visible_log(state: GameState, viewer: int | None) -> list[dict[str, Any]]:
    """ログを、``viewer``（0・1・``None`` は観戦者）に見える項目だけにした写しの並び。状態を変えない。"""
    _check_viewer(viewer)
    return [visible_event(event, viewer) for event in state.log]
