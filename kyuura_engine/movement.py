"""v0.87（docs/movement-damage-reactions-v0.87.md 3 章）: 場の移動の事実と、その事実への反応（［まきびし］・［やけのこり］・［ヒートプレート］・ロケット団の爆発ジム）。

事実の種類（どれも「新しく場に出た」こととは別。入れ替えは場に出ることではない）:

- 控え → バトル場（にげる・入れ替えのトレーナー・特殊能力・ワザの入れ替え・きぜつや場をはなれたあとに出す）: ``note_switch``（``old`` はベンチにもどったポケモン。出したあとなら None）
- 手札 → バトル場（マチス）: ``note_switch(..., from_hand=True)``（もどったポケモンはベンチへ）
- 手札 → ベンチ（ベンチに出す通常の操作・エリカの香水）: ``note_from_hand``
- 山札・トラッシュ → 場・進化・退化・「ばける」・うらのカードをおもてにすること・姿だけの変化は、この 3 つの反応の事実ではない（記録しない）

反応は記述（primitive のタプル）で、事実のすぐあとに集め（その時点で場にいる・はたらいている発生源）、``GameState.pending_moves`` に ``reactions`` の同じ時点の段
（``("same", "moved", 反応の並び, 情報)``）として加える。事実を起こした処理の流れ（トレーナー・特殊能力・にげる・ワザの要素のあいだ・バトル場に出したあと）が、同じコマンドの中で
処理する（``take``）。同じ時点に 2 つ以上の反応があれば、その時に番を行っているプレイヤーが順番を決める（GR-2000-P325-SAME-TIMING。``reactions``）。

反応の記述:

- ``(SPIKES, 持ち主, ポケモンの番号, 発生源, 1)``: ［まきびし］。発生源は ((持ち主, 番号), …)（はたらいているものを場の並びの順）。量はどれも同じなので 1 つの反応にまとめる
  （v0.61 の 2 つの［おとしあな］と同じ扱い。途中で HP 以上になれば残りは処理の対象がない。［ずらかる］の残りHPが途中で「10」を通るなら SC1）
- ``(HOT_PLATE, 持ち主, ポケモンの番号, 発生源, 1)``: ［ヒートプレート］（同じまとめ方）
- ``(MAGMA, 持ち主, ポケモンの番号, カード id, 特殊能力の位置, つけ替える先の番号, 1)``: ［やけのこり］
- ``(MINEFIELD, 持ち主, ポケモンの番号, スタジアムカード, 1)``: ロケット団の爆発ジム（［ヒートプレート］と同じ時点のときだけ反応として扱う。ほかは v0.57 のまま ``bench_entry_damage``）

v0.117（docs/retreat-return-active-powers-v0.117.md 3 章・4 章）: 「にげる」の事実への反応（にげたポケモンが受ける。どれも「にげる」の入れ替えのあと、ベンチにもどったポケモンに）:

- ``(CHASE, にげたプレイヤー, にげたポケモンの番号, 持ち主, 持つポケモンの番号, カード id, 特殊能力の位置, 1)``: 相手のバトル場のアンノーンC の［CHASE］（持ち主のコイン → ダメージカウンター）
- ``(PURSUIT, にげたプレイヤー, にげたポケモンの番号, 効果を与えたカード, 効果を与えたプレイヤー, 与えた番, 量, ワザ, 1)``: にげたポケモンが受けていた「おいうち」の効果（入れ替えの前に写した
  ``PursuitOnRetreat``。入れ替えでベンチにもどると消えるので、効果の値を記述に持つ）

v0.122（docs/unown-fossil-retreat-reactions-v0.122.md 5 章）: にげたポケモン自身の特殊能力の反応:

- ``(VINE_PULL, にげたプレイヤー, にげたポケモンの番号, 特殊能力を印刷したカード, 特殊能力の位置, 1)``: わるいフシギソウの［つるでひっぱる］（ベンチにもどったこのカードの力。相手プレイヤーが選ぶ
  相手の控えと、相手の対戦ポケモンを入れ替える。処理は ``reactions``）
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import effects as E
from .coins import CoinSide, flip_coins
from .errors import UnsupportedError

if TYPE_CHECKING:
    from .state import GameState, PokemonInPlay

SAME = "same"  # ``reactions.SAME`` と同じ値（reactions はこのモジュールを読み込む）

SPIKES = "spikes"
HOT_PLATE = "hot_plate"
MAGMA = "magma_pool"
MINEFIELD = "minefield"
SINKHOLE = "sinkhole"
CHASE = "chase"  # v0.117: ［CHASE］
PURSUIT = "pursuit"  # v0.117: おいうち
VINE_PULL = "vine_pull"  # v0.122: ［つるでひっぱる］
KINDS = (SPIKES, HOT_PLATE, MAGMA, MINEFIELD, SINKHOLE, CHASE, PURSUIT, VINE_PULL)
DAMAGING = (SPIKES, HOT_PLATE, MINEFIELD, SINKHOLE, CHASE, PURSUIT)


# ---------------------------------------------------------------- 事実を記録する


def _push(state: GameState, reactions: list[tuple], info: tuple) -> None:
    """反応の段を加える。情報の 3 つめは、その時点ですでに HP 以上のポケモンの番号（RA1 の比べは、この段の反応で新しく HP 以上になったポケモンだけを数える。ワザの途中・
    トレーナーの効果の途中は、きぜつの処理の前に HP 以上のポケモンが場に残る）。"""
    if reactions:
        baseline = tuple(sorted(p.pokemon_id for side in state.players for p in side.in_play() if not state.is_face_down(p) and E.knocked_by_hp(state, p)))
        state.pending_moves = state.pending_moves + ((SAME, "moved", tuple(reactions), info + (baseline,)),)


def _sources(found) -> tuple[tuple[int, int], ...]:
    return tuple((owner, holder.pokemon_id) for owner, holder, _key, _effect in found)


def note_switch(state: GameState, owner: int, old: PokemonInPlay | None, new: PokemonInPlay, *, from_hand: bool = False) -> None:
    """プレイヤー ``owner`` のバトル場に ``new`` が出た（``from_hand`` なら手札から直接。ほかは控えから）。``old`` はそのときバトル場からベンチにもどったポケモン（なければ None）。"""
    found: list[tuple] = []
    if old is not None:
        for _, holder, key, _effect in E.benching_magma(state, owner, old):
            found.append((MAGMA, owner, holder.pokemon_id, key.card_id, key.power_index, new.pokemon_id, 1))
    if from_hand:
        plates = E.hot_plates(state)
        if plates:
            found.append((HOT_PLATE, owner, new.pokemon_id, _sources(plates), 1))
    else:
        spikes = E.promotion_spikes(state, owner)
        if spikes:
            found.append((SPIKES, owner, new.pokemon_id, _sources(spikes), 1))
    _push(state, found, (owner, new.pokemon_id))


def note_from_hand(state: GameState, owner: int, pokemon: PokemonInPlay, *, minefield: bool, entry: bool) -> bool:
    """プレイヤー ``owner`` が手札からたねポケモン ``pokemon`` をベンチに出した。はたらいている［ヒートプレート］があるときだけ反応の段を加えて真を返す（爆発ジム（``minefield``）・
    手札から場に出したときの特殊能力の機会（``entry``）も同じ時点の反応に入れる）。なければ何もしないで偽（呼ぶ側が v0.86 までの処理をする。ログ・乱数を変えない）。"""
    plates = E.hot_plates(state)
    if not plates:
        return False
    found: list[tuple] = [(HOT_PLATE, owner, pokemon.pokemon_id, _sources(plates), 1)]
    if minefield:
        stadium = E.stadium_of(state, E.BenchEntryDamageStadium)
        if stadium is not None:
            found.append((MINEFIELD, owner, pokemon.pokemon_id, stadium[0].card, 1))
    if entry:
        from .reactions import collect_placed

        found.extend(collect_placed(state, owner, pokemon))
    _push(state, found, (owner, pokemon.pokemon_id))
    return True


def note_retreat(state: GameState, owner: int, new: PokemonInPlay, reactions: tuple) -> tuple:
    """v0.117: 「にげる」の事実への反応（［CHASE］・おいうち・同じ時点の［おとしあな］）の段を加え、まだ処理していない段を返す（入れ替えの事実への反応 ``note_switch`` がないとき。
    ある場合は呼ぶ側がその段に加える）。"""
    _push(state, list(reactions), (owner, new.pokemon_id))
    return take(state)


def take(state: GameState) -> tuple:
    """まだ処理していない反応の段を返し、状態から除く（処理するのは呼ぶ側）。"""
    steps = state.pending_moves
    state.pending_moves = ()
    return steps


def damaging(steps: tuple) -> bool:
    """段にダメージを与えうる反応があるか（処理の流れのきぜつの処理が要るか）。"""
    return any(reaction[0] in DAMAGING for step in steps if step[0] == SAME for reaction in step[2])


# ---------------------------------------------------------------- 反応が今はたらくか（同じ時点の順番の決定・RA2 の比べ）


def _locate(state: GameState, owner: int, pid: int) -> PokemonInPlay | None:
    found = state.find_pokemon(pid)
    return found[1] if found is not None and found[0] == owner else None


def _working_sources(state: GameState, reaction: tuple) -> tuple[tuple[int, int], ...]:
    kind, owner = reaction[0], reaction[1]
    if kind == SPIKES:
        working = _sources(E.promotion_spikes(state, owner))
    else:
        working = _sources(E.hot_plates(state))
    return tuple(source for source in reaction[3] if source in working)


def still_working(state: GameState, reaction: tuple) -> int | None:
    """反応が今はたらくか（1・0）。対象がいなくなったら None（その反応はなくなる）。"""
    kind = reaction[0]
    target = _locate(state, reaction[1], reaction[2]) if kind != MAGMA else _locate(state, reaction[1], reaction[5])
    if target is None:
        return None
    if kind in (SPIKES, HOT_PLATE):
        return int(_working_sources(state, reaction) == tuple(reaction[3]))
    if kind == MINEFIELD:
        found = E.stadium_of(state, E.BenchEntryDamageStadium)
        return int(found is not None and found[0].card == reaction[3])
    if kind == SINKHOLE:
        return int(bool(E.retreat_trap_powers(state, reaction[1])))
    if kind == CHASE:
        holder = _locate(state, reaction[3], reaction[4])
        if holder is None:
            return None
        return int(any(found[1] is holder and found[2] == E.PowerKey(reaction[5], reaction[6]) for found in E.retreat_chase_holders(state, reaction[1])))
    if kind == PURSUIT:
        return 1  # 効果は入れ替えの前に写した（受けたポケモンが場にいるかぎり、はたらく）
    if kind == VINE_PULL:
        # v0.122: ベンチにもどったこのカードが今持つ［つるでひっぱる］がはたらくか（力が消えていない・この番にまだはたらいていない）。場をはなれた・進化して力がないなら反応はなくなる
        holder = _locate(state, reaction[1], reaction[2])
        if holder is None or not any(slot.card == reaction[3] and slot.key.power_index == reaction[4] for slot in E.powers_of(state, holder)):
            return None
        return int(any(slot.card == reaction[3] and slot.key.power_index == reaction[4] for slot in E.retreat_vine_pulls(state, reaction[1], holder)))
    holder = _locate(state, reaction[1], reaction[2])
    if holder is None or state.players[reaction[1]].active is not target:
        return None
    return int(any(key.card_id == reaction[3] and key.power_index == reaction[4] for _, _, key, _ in E.benching_magma(state, reaction[1], holder)))


# ---------------------------------------------------------------- 反応を処理する（ワザの外・ワザの中で共通）


def designate(state: GameState, owner: int, pokemon: PokemonInPlay, by_player: int, cause: str) -> PokemonInPlay:
    """反応の対象のうらのカード（マチスの秘策）をおもてにする（ダメージや効果を受ける時。「たねポケモン」でなくトラッシュする場合は扱わない ``UNSUPPORTED_SECRET_PLAN_LOST_TARGET``）。"""
    from .zones import designate_face_down

    return designate_face_down(state, owner, pokemon, by_player=by_player, cause=cause, can_lose=False)


def _scram_crossing(state: GameState, owner: int, target: PokemonInPlay, amounts: list[int]) -> None:
    """2 つ以上の発生源のダメージの途中で、［ずらかる］の残りHPが「10」を通る（すべて与えてからか、1 つずつかで結果が変わる。v0.61 の SC1 と同じ問い）なら止める。"""
    if len(amounts) < 2:
        return
    for _, pokemon, slot in E.scram_slots(state):
        if pokemon is not target or not E.scram_working(state, pokemon, slot):
            continue
        remaining = E.max_hp(state, pokemon) - pokemon.damage
        total = 0
        for amount in amounts[:-1]:
            total += amount
            if remaining - total == slot.effect.remaining_hp:
                raise UnsupportedError(E.SCRAM_TIMING_CODE, f"ポケモン {target.pokemon_id}・発生源 {len(amounts)} つの特殊能力のダメージ: {E.SCRAM_TIMING_REASON}")


def power_damage(state: GameState, reaction: tuple, *, track=None) -> None:
    """［まきびし］・［ヒートプレート］: 対象に、はたらいている発生源ごと（場の並び）に特殊能力のダメージ（ワザのダメージの計算・弱点・抵抗力をしない。受けるダメージを変える
    常にはたらく特殊能力・鋼エネルギーは ``received_power_damage``）。対象がすでに HP 以上なら、残りは処理の対象がない（ログ ``movement_damage_skipped``）。``track`` は
    ワザの中の処理で、HP 以上になったポケモンをきぜつの判定に入れる関数（(ポケモン, 前のダメージ)）。"""
    kind, owner, pid, sources = reaction[0], reaction[1], reaction[2], reaction[3]
    target = _locate(state, owner, pid)
    target = designate(state, owner, target, sources[0][0], "damage")
    holders = []
    for src_owner, src_pid in sources:
        holder = _locate(state, src_owner, src_pid)
        if holder is None:
            raise RuntimeError(f"反応 {reaction!r} の発生源 {src_pid} が場にいない（エンジンの不具合）")
        holders.append((src_owner, holder))
    effect_type = E.DamageOnOpponentPromotion if kind == SPIKES else E.DamageOnHandBasicWhileActive
    amounts = []
    for src_owner, holder in holders:
        slot = next(s for s in E.powers_of(state, holder) if isinstance(s.effect, effect_type))
        amount, _ = E.received_power_damage(state, owner, target, holder, slot.effect.amount)
        amounts.append(amount)
    _scram_crossing(state, owner, target, amounts)
    for src_owner, holder in holders:
        slot = next(s for s in E.powers_of(state, holder) if isinstance(s.effect, effect_type))
        if E.knocked_by_hp(state, target):
            state.add_event("movement_damage_skipped", player=src_owner, pokemon=holder.card, pokemon_id=holder.pokemon_id, power=str(slot.key),
                            target_player=owner, target_pokemon_id=target.pokemon_id, reason=E.EFFECT_TARGET_KNOCKED_OUT)
            continue
        amount, applied = E.received_power_damage(state, owner, target, holder, slot.effect.amount)
        E.bench_guard_outside_attack_check(state, owner, target, amount)  # v0.65: 控えポケモンへのワザでないダメージの［ベンチガード］（エンジンの未対応）
        before = target.damage
        target.damage += amount
        extra = {} if not applied else {"amount_before": slot.effect.amount, "received_modifiers": E.received_modifiers_log(applied)}
        state.add_event("spikes_damage" if kind == SPIKES else "hot_plate_damage", player=src_owner, pokemon=holder.card, pokemon_id=holder.pokemon_id,
                        power=str(slot.key), target_player=owner, target=target.card, target_pokemon_id=target.pokemon_id, amount=amount,
                        total_damage=target.damage, knocked_out=E.knocked_by_hp(state, target), **extra)
        E.remove_on_damage(state, owner, target, amount)
        if track is not None:
            track(target, before)


def minefield_damage(state: GameState, reaction: tuple, *, track=None) -> None:
    """ロケット団の爆発ジム（v0.57 の ``bench_entry_damage`` と同じ処理。［ヒートプレート］と同じ時点のときの反応）。"""
    _, owner, pid, _stadium, _ = reaction
    pokemon = _locate(state, owner, pid)
    before = pokemon.damage
    E.bench_entry_damage(state, owner, pokemon)
    if track is not None and pokemon.damage != before:
        track(pokemon, before)


def sinkhole_damage(state: GameState, reaction: tuple) -> None:
    """「にげる」のほかの反応と同じ時点の、相手の［おとしあな］（v0.61 の ``resolution.after_retreat`` と同じ処理: 発生源ごとに、にげたプレイヤーのコイン 1 枚 → 「うら」なら
    ベンチにもどったポケモンに特殊能力のダメージ。ログ ``sinkhole_check``・``sinkhole_damage``）。2 つ以上の［おとしあな］の途中の［ずらかる］は、にげる前に確かめている（SC1）。"""
    _, player, pid, _ = reaction
    retreated = _locate(state, player, pid)
    for owner, holder, slot in E.retreat_trap_powers(state, player):
        key = str(slot.key)
        flips = flip_coins(state, player, 1, source="power", effect=key, card=holder.card, pokemon_id=holder.pokemon_id)
        tails = flips.results[0] is CoinSide.TAILS
        state.add_event("sinkhole_check", player=owner, pokemon=holder.card, pokemon_id=holder.pokemon_id, power=key, flipper=player,
                        target_pokemon_id=pid, result=flips.results[0].value)
        if retreated is None or not tails or E.knocked_by_hp(state, retreated):
            continue
        amount, applied = E.received_power_damage(state, player, retreated, holder, slot.effect.amount)
        retreated.damage += amount
        extra = {} if not applied else {"amount_before": slot.effect.amount, "received_modifiers": E.received_modifiers_log(applied)}
        state.add_event("sinkhole_damage", player=owner, pokemon=holder.card, pokemon_id=holder.pokemon_id, power=key, target_player=player,
                        target_pokemon=retreated.card, target_pokemon_id=pid, amount=amount, total_damage=retreated.damage,
                        knocked_out=E.knocked_by_hp(state, retreated), **extra)
        E.remove_on_damage(state, player, retreated, amount)


def chase_counters(state: GameState, reaction: tuple) -> None:
    """v0.117: ［CHASE］: 特殊能力を持つポケモンの持ち主がコインを 1 枚投げ（``source="power"``。ログ ``chase_check``）、「おもて」なら、にげたポケモン（ベンチにもどった）にダメージカウンターを
    のせる（ダメージではない。弱点・抵抗力・鋼エネルギー・受けるダメージを変える効果・「ダメージを受けたとき」の効果は当てはめない。ログ ``chase_counters``）。にげたポケモンがすでに
    HP 以上なら、コインのあと、のせない（処理の対象がない。ログ ``chase_skipped``）。"""
    _, player, pid, owner, holder_pid, card_id, index, _ = reaction
    retreated = _locate(state, player, pid)
    holder = _locate(state, owner, holder_pid)
    key = E.PowerKey(card_id, index)
    slot = next(s for s in E.powers_of(state, holder) if s.key == key)
    flips = flip_coins(state, owner, 1, source="power", effect=str(key), card=holder.card, pokemon_id=holder.pokemon_id)
    state.add_event("chase_check", player=owner, pokemon=holder.card, pokemon_id=holder.pokemon_id, power=str(key), target_player=player, target_pokemon_id=pid,
                    result=flips.results[0].value)
    if flips.results[0] is not CoinSide.HEADS:
        return
    if retreated is None or E.knocked_by_hp(state, retreated):
        state.add_event("chase_skipped", player=owner, pokemon=holder.card, pokemon_id=holder.pokemon_id, power=str(key), target_player=player, target_pokemon_id=pid,
                        reason=E.EFFECT_TARGET_KNOCKED_OUT)
        return
    counters = slot.effect.counters
    per = state.rules.damage_per_counter
    before = retreated.damage
    retreated.damage = before + counters * per
    state.add_event("chase_counters", player=owner, pokemon=holder.card, pokemon_id=holder.pokemon_id, power=str(key), target_player=player, target=retreated.card,
                    target_pokemon_id=pid, counters=counters, amount=counters * per, damage_before=before, total_damage=retreated.damage,
                    knocked_out=E.knocked_by_hp(state, retreated))


def pursuit_effect(reaction: tuple):
    """v0.117: おいうちの反応の記述から、入れ替えの前に写した効果（``PursuitOnRetreat``）を作り直す。"""
    from .state import PursuitOnRetreat

    _, _, _, source_card, source_player, created_turn, amount, attack, _ = reaction
    return PursuitOnRetreat(source_card=source_card, source_player=source_player, created_turn=created_turn,
                            active_turn=created_turn + PursuitOnRetreat.turns_until_active, amount=amount, attack=attack)


def pursuit_damage(state: GameState, reaction: tuple) -> None:
    """v0.117: おいうち: にげたポケモン（ベンチにもどった）に、効果を与えたワザによるダメージ（ワザの分類。弱点・抵抗力なし。``kernel.pursuit_amount``）。受けるときの効果を「にげる」の
    中で処理できないなら止める（``kernel.pursuit_problems``。にげる前にも確かめている）。すでに HP 以上なら処理の対象がない（ログ ``pursuit_skipped``）。無効にする効果があれば
    のせない（ログ ``pursuit_prevented``）。ログ ``pursuit_damage``（公開）。"""
    from .resolution.kernel import pursuit_amount, pursuit_problems

    _, player, pid, source_card, source_player, _, amount, attack, _ = reaction
    retreated = _locate(state, player, pid)
    base = {"player": source_player, "pokemon": source_card, "attack": attack, "target_player": player, "target_pokemon_id": pid}
    if retreated is None or E.knocked_by_hp(state, retreated):
        state.add_event("pursuit_skipped", **base, reason=E.EFFECT_TARGET_KNOCKED_OUT)
        return
    effect = pursuit_effect(reaction)
    final, void = pursuit_amount(state, player, retreated, effect, bench=state.players[player].active is not retreated)
    if void is not None:
        state.add_event("pursuit_prevented", **base, target=retreated.card, prevented_by=void)
        return
    pursuit_problems(state, player, retreated, final)
    before = retreated.damage
    retreated.damage = before + final
    state.add_event("pursuit_damage", **base, target=retreated.card, amount=final, amount_before=amount, damage_before=before, total_damage=retreated.damage,
                    knocked_out=E.knocked_by_hp(state, retreated))
    if final > 0:
        E.remove_on_damage(state, player, retreated, final)


class MagmaChoice:
    """［やけのこり］でつけ替えるカードを持ち主に選ばせる（候補が 2 枚以上。選ぶと止めるカードは ``unresolved``）。"""

    def __init__(self, player: int, options: tuple[int, ...], unresolved: tuple[tuple[int, ...], str | None, str | None]):
        self.player = player
        self.options = options
        self.unresolved = unresolved


def magma_choice(state: GameState, reaction: tuple) -> MagmaChoice | int | None:
    """［やけのこり］のつけ替えるカード: 1 枚に決まればその uid、選ばせるなら ``MagmaChoice``、つけ替えるカードがなければ None。決められない場合は ``UnsupportedError``。"""
    _, owner, pid, card_id, power_index, target_pid, _ = reaction
    holder = _locate(state, owner, pid)
    target = _locate(state, owner, target_pid)
    effect = state.effects.power_entry(card_id, power_index).effect
    definite, ambiguous = E.magma_candidates(state, holder, effect.energy_type)
    if not definite and not ambiguous:
        return None
    if not definite:
        raise ambiguous[0][1]
    if E.energy_attach_block(state, target) is not None:
        raise E.attach_block_scope_error(target, "［やけのこり］でつけ替える先")  # v0.59 の CB1（つけ替えがクリスタルビームの「つける」に当たるか）
    E.attach_trigger_move_check(state, target, "［やけのこり］でつけ替える先")  # v0.116: AT1（つけ替える先はベンチから出た新しい対戦ポケモンなので、今の写しでは起こらない）
    options = tuple(definite) + tuple(uid for uid, _ in ambiguous)
    if len(options) == 1:
        return options[0]
    blocked = tuple(uid for uid, _ in ambiguous)
    code = reason = None
    if ambiguous:
        code, reason = ambiguous[0][1].code, ambiguous[0][1].message
    return MagmaChoice(owner, options, (blocked, code, reason))


def magma_move(state: GameState, reaction: tuple, card: int) -> None:
    """［やけのこり］: ``card`` をベンチにもどったこのカードからはがし、新しい対戦ポケモンにつけ替える（同じ uid のカードを動かすだけ。トラッシュ・手札からつける操作ではない。
    ログ ``magma_pool``）。"""
    _, owner, pid, card_id, power_index, target_pid, _ = reaction
    holder = _locate(state, owner, pid)
    target = _locate(state, owner, target_pid)
    if card not in holder.energy:
        raise RuntimeError(f"［やけのこり］でつけ替えるカード {card} が、ポケモン {pid} についていない（エンジンの不具合）")
    target = designate(state, owner, target, owner, "energy_move")
    holder.energy.remove(card)
    target.energy.append(card)
    state.add_event("magma_pool", player=owner, pokemon=holder.card, pokemon_id=holder.pokemon_id, power=str(E.PowerKey(card_id, power_index)), card=card,
                    to_pokemon_id=target.pokemon_id)


def magma_none(state: GameState, reaction: tuple) -> None:
    _, owner, pid, card_id, power_index, target_pid, _ = reaction
    holder = _locate(state, owner, pid)
    state.add_event("magma_pool_none", player=owner, pokemon=holder.card, pokemon_id=pid, power=str(E.PowerKey(card_id, power_index)), to_pokemon_id=target_pid)


def promotion_spikes_now(state: GameState, owner: int, promoted: PokemonInPlay, *, track=None) -> bool:
    """きぜつ・場をはなれたあとにバトル場に出したポケモン ``promoted`` への［まきびし］を、すぐに処理する（同じ時点のほかの反応はない。もどったポケモンがいないので［やけのこり］は
    ない）。処理したら真。"""
    spikes = E.promotion_spikes(state, owner)
    if not spikes:
        return False
    power_damage(state, (SPIKES, owner, promoted.pokemon_id, _sources(spikes), 1), track=track)
    return True


__all__ = ["DAMAGING", "KINDS", "MagmaChoice", "chase_counters", "damaging", "magma_choice", "magma_move", "note_from_hand", "note_retreat", "note_switch", "power_damage",
           "promotion_spikes_now", "pursuit_damage", "still_working", "take"]
