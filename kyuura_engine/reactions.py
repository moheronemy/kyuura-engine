"""v0.86（docs/entry-energy-evolution-reactions-v0.86.md 2 章）: ワザの外で起こった事実（手札からエネルギーカードをつけた・ポケモンが進化した・手札から場に出した）への
反応を、同じ時点の反応の順番と、決定をまたぐ続きとともに処理する。

- 事実ごとに、その時点ではたらきうる反応を集める（``collect_attach``・``collect_evolution``・``collect_placed``）。反応は記述（primitive のタプル。``Reaction``）で、出どころ
  （手札）・実際に行ったプレイヤー・カードの持ち主・対象の番号・能力を印刷したカード・つける前の特殊状態などを持つ。関数・生成器の参照は持たない
- 同じ事実に 2 つ以上の反応があれば、その時に番を行っているプレイヤーが順番を決める（GR-2000-P325-SAME-TIMING。決定 ``REACTION_ORDER``）。能力の持ち主・つけた側・配列・番号の
  順で決めない。反応の処理が決定を出したら、残りの反応・あとの事実（続き ``followup``）を決定の ``context`` に明示的なデータで持つ（``attach_followup``）。決定への答えのあと、
  エンジンが続きを処理する（``run``。``engine._answer_decision``）
- 同じ時点の反応のうち、先の反応で場が変わり、あとの反応がはたらくか（特殊状態・ガス・ポケモンの所在）が集めた時と変わるなら、どの時点の状態で決めるかは決まらない（RA2）。
  先の反応で HP 以上になったポケモンがあるときに、残りの反応を処理するのも、きぜつの判定の時点が決まらない（RA1）。どちらも、その反応を処理する前（コインの前）に止める
- あとの事実（反応で起こった進化）への反応は、その時に待っている反応のあとに処理する（事実の起こった順。実装上の順番。docs 2.2 節）

続き（``followup``）の各段（step）: ``("same", 名前, 反応の並び, 情報)``（同じ時点の反応）・``("trainer", プレイヤー, カード, カード id)``（使用中のトレーナーを使い終える）・
``("end_turn", プレイヤー, 特殊能力)``（［おたけび］の「使ったら、自分の番は終わる」）・``("settle_energy",)``（つける操作の反応のあとのきぜつの処理）。
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

from . import effects as E
from . import movement as M
from .coins import CoinSide, flip_coins
from .decisions import (
    MAGMA_POOL_ENERGY,
    REACTION_ORDER,
    REACTION_POWER,
    SEARCH_DECK,
    SELECT_POKEMON,
    push_decision,
)
from .errors import UnsupportedError
from .evolution import evolution_block, place_evolution_card
from .persistent import powers_stopped, powers_use_prevented
from .state import Phase
from .zones import shuffle_deck

if TYPE_CHECKING:
    from .state import GameState, PokemonInPlay

RESUME = "reaction"  # 決定の再開先
FOLLOWUP = "followup"  # 決定の ``context`` の続きの項目
REACTION = "reaction"  # 決定の ``context`` の反応の項目

SAME = "same"
TRAINER = "trainer"
END_TURN = "end_turn"
SETTLE_ENERGY = "settle_energy"
# v0.87（docs/movement-damage-reactions-v0.87.md 3 章）: 場の移動の反応のあとの段
RESTORE = "restore"  # ``("restore", (種類, プレイヤー, 選べるもの, 最小, 最大, 再開先, context))``: 反応の前に出ていた決定を、反応のあとに出し直す（トレーナーの 2 つめの入れ替え）
SETTLE_POWER = "settle_power"  # 特殊能力の処理のあとの場の整理（``resolution.after_power``。反応のダメージで HP 以上になったポケモンのきぜつ）
SETTLE_EFFECTS = "settle_effects"  # 手札からベンチに出したあとの場の整理（［ヒートプレート］・爆発ジムのダメージのきぜつ。``resolution.after_effects``）
SETTLE_RETREAT = "settle_retreat"  # ``("settle_retreat", にげたプレイヤー, ベンチにもどったポケモンの番号)``: 「にげる」の反応のあと（［ずらかる］・きぜつ・交代・同じ番）
SINKHOLE = M.SINKHOLE  # 「にげる」の反応のうち、相手の［おとしあな］（v0.61 の処理。ほかの反応と同じ時点のときだけ、反応の 1 つとして扱う）


def restore_step(payload: tuple) -> tuple:
    """反応のあとに、待っていた決定を出し直す段（``engine._stash_decision`` の値）。"""
    return (RESTORE, payload)

# 反応の種類（記述の 1 つめ）
ENERGY = "energy"  # 手札からつけた特殊エネルギーの、つけたときの効果
HEAL = "heal"  # ほのおでかいふく（つけたときの回復）
ENERGY_EVOLUTION = "energy_evolution"  # エナジーしんか
LIGHTNING_BURST = "lightning_burst"  # いなびかり
CONDUCTIVITY = "conductivity"  # かんでん
CHAIN_EVOLUTION = "chain_evolution"  # れんさしんか
ENTRY = "entry"  # 場に出たときに使える特殊能力の機会（v0.43 の ``offer_entry_power``）

# RA1: 同じ時点の反応のうち、先の反応で HP 以上になったポケモンがあるときに、残りの反応を処理する（きぜつの判定の時点が決まらない）
REACTION_AFTER_KNOCKOUT_CODE = "UNRESOLVED_REACTION_AFTER_KNOCKOUT"
REACTION_AFTER_KNOCKOUT_REASON = (
    "同じ時点に起こる反応（手札からつけたエネルギーカード・進化への反応）のうち、先に処理した反応でポケモンが HP 以上になったとき、そのポケモンの「きぜつ」の判定を残りの反応の前に"
    "するか後にするかは、記録（GR-2000-P325-SAME-TIMING は処理の順番を番のプレイヤーが決めることだけを書く）から決められないので扱わない（RA1。順番を変えれば止まらない場合がある）")
# RA2: 同じ時点の反応のうち、先の反応で場が変わり、あとの反応がはたらくか（特殊状態・力が消えているか・ポケモンの所在）が、事実の時点と変わる
REACTION_CONDITION_CHANGED_CODE = "UNRESOLVED_REACTION_CONDITION_CHANGED"
REACTION_CONDITION_CHANGED_REASON = (
    "同じ時点に起こる反応のうち、先に処理した反応（なんでもなおし配合エネルギーの回復・入れ替えなど）で場が変わり、あとの反応の特殊能力がはたらくか（ねむり・マヒ・こんらん・力が"
    "消えているか）が事実の時点と変わるとき、どちらの時点の状態で決めるかは、記録から決められないので扱わない（RA2。説明が時点を書く［いなびかり］の「つけるときすでに」は除く）")


# ---------------------------------------------------------------- 続き（followup）を決定に持たせる・処理する


@dataclasses.dataclass(frozen=True)
class Followup:
    """トレーナー・特殊能力の実装が、処理のあとに続ける段（``steps``）をエンジンに返す印（v0.86。決定の ``context`` に持つ続きと同じ段の並び）。"""

    steps: tuple


APPEND = "append"  # ``answer`` の戻り値の最初にあれば、あとの事実への反応（待っている反応の段のあとに処理する）


def merge(prefix: tuple, followup: tuple) -> tuple:
    """続き ``followup`` の前に、処理の結果の段 ``prefix`` を置く。``prefix`` が ``APPEND`` で始まる（反応で起こった進化への反応）なら、``followup`` の待っている反応の段
    （``SAME``）のあと、ほかの段（つける操作のあとのきぜつの処理・トレーナーを使い終える・番を終える）の前に置く（事実の起こった順。実装上の順番。docs 2.2 節）。"""
    prefix = tuple(prefix)
    followup = tuple(followup)
    if not prefix or prefix[0] != APPEND:
        merged = prefix + followup
    else:
        added = prefix[1:]
        index = next((i for i, step in enumerate(followup) if step[0] != SAME), len(followup))
        merged = followup[:index] + added + followup[index:]
    # 番を終える段（［おたけび］の「使ったら、自分の番は終わる」）は、ほかのすべての段（待っている反応・使用中のトレーナーを使い終える・きぜつの処理）のあと
    return tuple(step for step in merged if step[0] != END_TURN) + tuple(step for step in merged if step[0] == END_TURN)


def attach_followup(state: GameState, steps: tuple) -> None:
    """待っている決定の続きの最後に ``steps`` を加える（決定の ``context`` の ``followup``。決定を出した処理の続きが先、``steps`` があと）。"""
    steps = tuple(steps)
    if not steps:
        return
    decision = state.decision
    if decision is None:
        raise RuntimeError("続きを持たせる決定がない（エンジンの不具合）")
    own = tuple(decision.context_value(FOLLOWUP, ()))
    context = tuple((name, value) for name, value in decision.context if name != FOLLOWUP) + ((FOLLOWUP, own + steps),)
    state.decision = dataclasses.replace(decision, context=context)


def run(state: GameState, steps: tuple, ctx, engine_hooks) -> None:
    """続き ``steps`` を順に処理する。決定が出たら、残りを決定に持たせて止まる。対戦が終わったら残りは処理しない。``engine_hooks`` はエンジンが渡す処理
    （``finish_trainer``・``end_turn``・``settle_energy``。resolution・engine を読み込まないため）。"""
    steps = tuple(steps)
    if state.decision is not None:
        attach_followup(state, steps)
        return
    while steps:
        if state.phase in (Phase.GAME_OVER, Phase.HALTED):
            return
        step, steps = steps[0], steps[1:]
        steps = merge(_run_step(state, step, ctx, engine_hooks), steps)
        if state.decision is not None:
            attach_followup(state, steps)
            return


def _run_step(state: GameState, step: tuple, ctx, hooks) -> tuple:
    kind = step[0]
    if kind == SAME:
        return _process_same(state, step)
    if kind == TRAINER:
        _, player, card, card_id = step
        used = state.trainer_in_use
        if used is None or (used.using_player, used.card) != (player, card):
            raise RuntimeError(f"続きのトレーナー {step!r} が、使用中のトレーナー {used} ではない（エンジンの不具合）")
        hooks.finish_trainer(state, card_id, ctx)
        return ()
    if kind == END_TURN:
        _, player, power = step
        hooks.end_turn(state, player, power, ctx)
        return ()
    if kind == SETTLE_ENERGY:
        hooks.settle_energy(state, ctx)
        return ()
    if kind == RESTORE:
        _, (decision_kind, player, options, low, high, resume, context) = step
        push_decision(state, kind=decision_kind, player=player, options=options, resume=resume, context=context, min_choices=low, max_choices=high)
        return ()
    if kind == SETTLE_POWER:
        hooks.settle_power(state, ctx)
        return ()
    if kind == SETTLE_EFFECTS:
        hooks.settle_effects(state, ctx)
        return ()
    if kind == SETTLE_RETREAT:
        _, player, retreated = step
        hooks.settle_retreat(state, ctx, player, retreated)
        return ()
    raise RuntimeError(f"知らない続きの段 {step!r}（エンジンの不具合）")


# ---------------------------------------------------------------- 反応を集める


def _blocked_status(pokemon: PokemonInPlay) -> bool:
    c = pokemon.conditions
    return bool(c.asleep or c.paralyzed or c.confused)


def _slot(state: GameState, pokemon: PokemonInPlay, power_card: int, power_index: int):
    """場のポケモン ``pokemon`` が今持つ特殊能力のうち、``power_card`` が印刷した ``power_index`` 番目のもの（v0.49 の ``powers_of``）。なければ None（進化・場をはなれた）。"""
    return next((s for s in E.powers_of(state, pokemon) if s.card == power_card and s.key.power_index == power_index), None)


def _stopped(state: GameState, pokemon: PokemonInPlay, slot, *, declared: bool) -> bool:
    """この特殊能力の力が今消えている・使えないか（かがくへんかガス・まきちらせ!ベトベトガス・スタンウェーブ。宣言して使う特殊能力ならショックアイも）。"""
    from .continuous import power_suppressed

    if power_suppressed(state, slot.power, pokemon) or powers_stopped(state, pokemon) is not None:
        return True
    return declared and powers_use_prevented(state, pokemon) is not None


def _locate(state: GameState, owner: int, pid: int) -> PokemonInPlay | None:
    found = state.find_pokemon(pid)
    return found[1] if found is not None and found[0] == owner else None


def card_color(state: GameState, uid: int) -> tuple[Any, tuple[str, str] | None]:
    """手札からつけたエネルギーカード ``uid`` の色（タイプ）と、決められない理由。基本エネルギーは出すタイプ。出すエネルギーが 1 つの色に決まる特殊エネルギーはその色（無色
    2 個エネルギーなどは「無色」）。レインボーエネルギー（どの色にもなる 1 個）は RB1、ミラクルエネルギーは MEC1。"""
    definition = state.card_def(uid)
    if definition.is_basic_energy:
        return definition.provides, None
    effect = E.special_energy_effect(state, uid)
    if effect is None:
        return None, None
    if getattr(effect, "miracle", False):
        return None, (E.MIRACLE_TYPE_CODE, f"ミラクルエネルギー {uid} の色: {E.MIRACLE_TYPE_REASON.format(type='X')}")
    units = effect.units()
    colors = {t for unit in units for t in unit}
    if len(colors) == 1:
        return next(iter(colors)), None
    if any(len(unit) > 1 for unit in units):
        return None, (E.RAINBOW_TYPE_CODE, f"レインボーエネルギー {uid} の色: {E.RAINBOW_TYPE_REASON.format(type='X')}")
    return None, None


def _is_type_card(state: GameState, uid: int, energy_type) -> tuple[bool, tuple[str, str] | None]:
    """「``energy_type``」エネルギーカードか（出すエネルギーがその色 1 つに決まるカード）と、決められない理由（RB1・MEC1）。"""
    color, problem = card_color(state, uid)
    return color is energy_type, problem


def collect_attach(state: GameState, actor: int, target_owner: int, target: PokemonInPlay, card: int, pre_status: tuple[int, int, int]) -> tuple:
    """手札から出してポケモン ``target``（持ち主 ``target_owner``）にエネルギーカード ``card`` をつけた事実（つけたのは ``actor``）への反応を集める（つけたあと、反応の前）。
    記述の最後の値は、集めた時点ではたらいていたか（RA2 の比べ）。``pre_status`` はつける前の (ねむり, マヒ, こんらん)。"""
    found: list[tuple] = []
    effect = E.special_energy_effect(state, card) if state.card_def(card).is_special_energy else None
    if effect is not None and type(effect).on_attached_from_hand is not E.SpecialEnergyEffect.on_attached_from_hand and not E.miraculous_wind_sources(state):
        found.append((ENERGY, target_owner, target.pokemon_id, card, actor, 1))
    for slot in E.powers_of(state, target):
        if isinstance(slot.effect, E.HealOnEnergyAttach):
            definition = state.card_def(card)
            if definition.is_basic_energy and definition.provides is slot.effect.energy_type:
                working = int(not _blocked_status(target) and not _stopped(state, target, slot, declared=False))
                found.append((HEAL, target_owner, target.pokemon_id, slot.card, slot.key.power_index, card, working))
        elif isinstance(slot.effect, E.EvolveFromDeckByAttachedEnergyColor):
            working = int(not _blocked_status(target) and not _stopped(state, target, slot, declared=True))
            found.append((ENERGY_EVOLUTION, target_owner, target.pokemon_id, slot.card, slot.key.power_index, card, working))
        elif isinstance(slot.effect, E.SwitchOpponentOnTypeEnergyAttach):
            matches, problem = _is_type_card(state, card, slot.effect.energy_type)
            if problem is not None:
                raise UnsupportedError(*problem)
            if matches:
                pre = int(any(pre_status))
                working = int(not pre and not _stopped(state, target, slot, declared=False))
                found.append((LIGHTNING_BURST, target_owner, target.pokemon_id, slot.card, slot.key.power_index, card, pre, working))
    # かんでん（相手プレイヤーが手札からつけたら。発生源は ``actor`` の相手の場のわるいデンリュウ）
    sources = []
    for holder in state.players[1 - actor].in_play():
        for slot in E.powers_of(state, holder):
            if isinstance(slot.effect, E.DamageOnOpponentHandEnergyAttach):
                sources.append((holder, slot))
    if sources:
        working = [(h, s) for h, s in sources if not _blocked_status(h) and not _stopped(state, h, s, declared=False)]
        if len(working) > 1:
            raise UnsupportedError(E.CONDUCTIVITY_SOURCES_CODE, f"わるいデンリュウ {[h.pokemon_id for h, _ in working]}: {E.CONDUCTIVITY_SOURCES_REASON}")
        holder, slot = working[0] if working else sources[0]
        found.append((CONDUCTIVITY, 1 - actor, holder.pokemon_id, slot.card, slot.key.power_index, target_owner, target.pokemon_id, card, int(bool(working))))
    return tuple(found)


def attach_steps(state: GameState, actor: int, owner: int, target: PokemonInPlay, cards: tuple[int, ...], pre_status: tuple[int, int, int]) -> tuple | None:
    """手札から出してポケモン ``target`` にエネルギーカード ``cards`` をつけた事実（つけたのは ``actor``。カードをつけてログを残したあと）への反応の段。v0.85 までと同じ処理
    （どのカードも反応が 1 つ以下で、v0.86 の反応（［エナジーしんか］・［いなびかり］・［かんでん］）がない）なら None（呼ぶ側が v0.85 までの処理をする。ログ・乱数を変えない）。
    つけたときの効果・［かんでん］で HP 以上になりうるなら、最後につける操作のあとのきぜつの処理（``SETTLE_ENERGY``）。"""
    found = [(card, collect_attach(state, actor, owner, target, card, pre_status)) for card in cards]
    new_kinds = {ENERGY_EVOLUTION, LIGHTNING_BURST, CONDUCTIVITY}
    if not any(r[0] in new_kinds for _, rs in found for r in rs) and all(len(rs) <= 1 for _, rs in found):
        return None
    steps: tuple = tuple((SAME, "attached", rs, (owner, target.pokemon_id, card)) for card, rs in found if rs)
    damaging = any(r[0] == CONDUCTIVITY or (r[0] == ENERGY and E.special_energy_effect(state, r[3]).may_knock_out) for _, rs in found for r in rs)
    return steps + ((SETTLE_ENERGY,),) if damaging else steps


def chain_holders(state: GameState, owner: int, evolved_pid: int) -> list[tuple[PokemonInPlay, Any]]:
    """持ち主 ``owner`` の場の、［れんさしんか］を持つ「ほかの」ポケモン（進化したポケモン ``evolved_pid`` 以外）と特殊能力（場の並び）。"""
    found = []
    for pokemon in state.players[owner].in_play():
        if pokemon.pokemon_id == evolved_pid:
            continue
        for slot in E.powers_of(state, pokemon):
            if isinstance(slot.effect, E.EvolveFromDeckOnOtherEvolution):
                found.append((pokemon, slot))
    return found


def working_chain_holders(state: GameState, owner: int, evolved_pid: int) -> list[tuple[PokemonInPlay, Any]]:
    """``chain_holders`` のうち、今使える（ねむり・マヒ・こんらんでなく、力が消えていない・使える）もの。ワザの途中の進化の PW4 の確かめに使う。"""
    return [(p, s) for p, s in chain_holders(state, owner, evolved_pid) if not _blocked_status(p) and not _stopped(state, p, s, declared=True)]


def collect_evolution(state: GameState, owner: int, evolved: PokemonInPlay, *, entry_from_hand: bool | None) -> tuple:
    """持ち主 ``owner`` の場のポケモン ``evolved`` が実際に進化した事実への反応を集める: そのポケモンの場に出たときに使える特殊能力の機会（``entry_from_hand`` が None なら
    集めない）と、ほかのポケモンの［れんさしんか］の機会。"""
    found: list[tuple] = []
    if entry_from_hand is not None:
        on_bench = state.players[owner].active is not evolved
        if E.applicable_entry_power(state, evolved.card, from_hand=entry_from_hand, on_bench=on_bench) is not None or (
                E.applicable_entry_power(state, evolved.card, from_hand=entry_from_hand, tower=False, on_bench=on_bench) is not None):
            found.append((ENTRY, owner, evolved.pokemon_id, int(entry_from_hand), 1))
    for pokemon, slot in chain_holders(state, owner, evolved.pokemon_id):
        working = int(not _blocked_status(pokemon) and not _stopped(state, pokemon, slot, declared=True))
        found.append((CHAIN_EVOLUTION, owner, pokemon.pokemon_id, slot.card, slot.key.power_index, evolved.pokemon_id, working))
    return tuple(found)


def collect_placed(state: GameState, owner: int, placed: PokemonInPlay) -> tuple:
    """手札から場に出した事実（たねポケモン）への反応: 場に出たときに使える特殊能力の機会。"""
    if E.applicable_entry_power(state, placed.card, from_hand=True) is None and E.applicable_entry_power(state, placed.card, from_hand=True, tower=False) is None:
        return ()
    return ((ENTRY, owner, placed.pokemon_id, 1, 1),)


def evolution_steps(state: GameState, owner: int, evolved: PokemonInPlay, *, entry_from_hand: bool | None) -> tuple:
    found = collect_evolution(state, owner, evolved, entry_from_hand=entry_from_hand)
    return ((SAME, "evolved", found, (owner, evolved.pokemon_id)),) if found else ()


def has_chain_reactions(state: GameState, owner: int, evolved: PokemonInPlay) -> bool:
    """進化した事実に［れんさしんか］の機会があるか（ないときは v0.85 までと同じ経路で、場に出たときの特殊能力の機会だけを出す）。"""
    return bool(chain_holders(state, owner, evolved.pokemon_id))


# ---------------------------------------------------------------- 同じ時点の反応を処理する


def _still_working(state: GameState, reaction: tuple) -> int | None:
    """反応が今はたらくか（1・0）。反応の発生源・対象がいない（場をはなれた・進化して特殊能力がない）なら None（その反応はなくなる）。"""
    kind = reaction[0]
    if kind in M.KINDS:
        return M.still_working(state, reaction)  # v0.87: 場の移動の反応
    if kind == ENERGY:
        _, owner, pid, card, _, _ = reaction
        target = _locate(state, owner, pid)
        return None if target is None or card not in target.energy else 1
    if kind == ENTRY:
        _, owner, pid, _from_hand, _ = reaction
        pokemon = _locate(state, owner, pid)
        if pokemon is None:
            return None
        return 1
    if kind == CONDUCTIVITY:
        _, src_owner, src_pid, power_card, index, target_owner, target_pid, card, _ = reaction
        holder = _locate(state, src_owner, src_pid)
        target = _locate(state, target_owner, target_pid)
        if holder is None or target is None or card not in target.energy:
            return None
        slot = _slot(state, holder, power_card, index)
        if slot is None:
            return None
        return int(not _blocked_status(holder) and not _stopped(state, holder, slot, declared=False))
    owner, pid, power_card, index = reaction[1], reaction[2], reaction[3], reaction[4]
    holder = _locate(state, owner, pid)
    if holder is None:
        return None
    slot = _slot(state, holder, power_card, index)
    if slot is None:
        return None
    if kind == LIGHTNING_BURST:
        pre = reaction[6]
        return int(not pre and not _stopped(state, holder, slot, declared=False))
    declared = kind in (ENERGY_EVOLUTION, CHAIN_EVOLUTION)
    return int(not _blocked_status(holder) and not _stopped(state, holder, slot, declared=declared))


def _knocked(state: GameState) -> list[int]:
    return [p.pokemon_id for side in state.players for p in side.in_play() if not state.is_face_down(p) and E.knocked_by_hp(state, p)]


# 決定を出さず、すぐに場を変える反応（先に処理すると、あとの反応がはたらくかを変えうる。RA2 の比べ）
_IMMEDIATE = (ENERGY, HEAL, CONDUCTIVITY)


def _revives(state: GameState, reaction: tuple, dead: list[tuple]) -> bool:
    """決定を出さない反応 ``reaction`` を先に処理すると、今はたらかない反応 ``dead`` のどれかがはたらくようになるか（状態の複製の上で処理して確かめる。乱数は使わない）。"""
    if reaction[0] not in _IMMEDIATE or not dead:
        return False
    trial = state.clone()
    process(trial, reaction, ())
    return any(_still_working(trial, d) for d in dead)


def _process_same(state: GameState, step: tuple) -> tuple:
    _, label, pending, info = step
    live, dead = [], []
    for reaction in pending:
        now = _still_working(state, reaction)
        if now is None:
            continue
        if now != reaction[-1]:
            raise UnsupportedError(REACTION_CONDITION_CHANGED_CODE, f"反応 {reaction!r}: {REACTION_CONDITION_CHANGED_REASON}")
        (live if now else dead).append(reaction)
    if not live:
        return ()
    knocked = _knocked(state)
    if label == "moved":
        knocked = [pid for pid in knocked if pid not in info[2]]  # v0.87: 場の移動の反応の段は、その事実の時点ですでに HP 以上のポケモンを除く
    if knocked:
        raise UnsupportedError(REACTION_AFTER_KNOCKOUT_CODE, f"HP 以上のポケモン {knocked}・残りの反応 {[r[0] for r in live]}: {REACTION_AFTER_KNOCKOUT_REASON}")
    # 今はたらかない反応（ねむりのポケモンの［エナジーしんか］など）を、先に処理する反応（なんでもなおし配合エネルギーの回復）がはたらくようにする組だけ、その反応も順番の決定に
    # 入れる（先に選べば、どちらの時点の状態で決めても、はたらかない。あとにすると、どちらの時点で決めるかで結果が変わるので RA2。docs 2.2 節）
    reviving = [i for i, r in enumerate(live) if _revives(state, r, dead)]
    order = live + (dead if reviving else [])
    if len(order) >= 2:
        extra: tuple = ()
        if reviving:
            extra = (("unresolved_choices", tuple(reviving)), ("unresolved_code", REACTION_CONDITION_CHANGED_CODE),
                     ("unresolved_reason", REACTION_CONDITION_CHANGED_REASON))
        push_decision(state, kind=REACTION_ORDER, player=state.current_player, options=range(len(order)), resume=RESUME,
                      context=((REACTION, (SAME, label, tuple(order), info)),) + extra)
        return ()
    return process(state, live[0], ())


def answer_order(state: GameState, decision, choices: tuple[int, ...]) -> tuple:
    """順番の決定の答え: 選んだ反応を処理し、残りの反応の段を続きの最初にする。選んだのが今はたらかない反応なら、処理せずに（はたらかない）残りへ進む。"""
    _, label, order, info = decision.context_value(REACTION)
    if choices[0] in tuple(decision.context_value("unresolved_choices", ())):
        raise UnsupportedError(decision.context_value("unresolved_code"), decision.context_value("unresolved_reason"))
    chosen = order[choices[0]]
    rest = tuple(r for i, r in enumerate(order) if i != choices[0])
    after = ((SAME, label, rest, info),) if rest else ()
    if not _still_working(state, chosen):
        return after
    return process(state, chosen, after)


def process(state: GameState, reaction: tuple, after: tuple) -> tuple:
    """反応 1 つを処理する。決定を出したら、``after``（残りの反応）を続きとして返す（呼ぶ側が決定に持たせる）。出さなければ ``after`` を返す。"""
    kind = reaction[0]
    if kind == ENERGY:
        _, owner, pid, card, actor, _ = reaction
        target = _locate(state, owner, pid)
        E.energy_attached_from_hand(state, actor, card, target)
        return after
    if kind == HEAL:
        _, owner, pid, power_card, index, card, _ = reaction
        holder = _locate(state, owner, pid)
        E.apply_attach_heal(state, owner, holder, _slot(state, holder, power_card, index), card)
        return after
    if kind == CONDUCTIVITY:
        _conductivity(state, reaction)
        return after
    if kind == LIGHTNING_BURST:
        return _lightning_burst(state, reaction, after)
    if kind in (ENERGY_EVOLUTION, CHAIN_EVOLUTION):
        _offer_use(state, reaction)
        return after
    if kind == ENTRY:
        _, owner, pid, from_hand, _ = reaction
        pokemon = _locate(state, owner, pid)
        E.offer_entry_power(state, owner, pokemon, from_hand=bool(from_hand))
        return after
    if kind in (M.SPIKES, M.HOT_PLATE):
        M.power_damage(state, reaction)  # v0.87: ［まきびし］・［ヒートプレート］
        return after
    if kind == M.MINEFIELD:
        M.minefield_damage(state, reaction)  # v0.87: ［ヒートプレート］と同じ時点の爆発ジム
        return after
    if kind == M.SINKHOLE:
        M.sinkhole_damage(state, reaction)  # v0.87: ほかの反応と同じ時点の［おとしあな］
        return after
    if kind == M.MAGMA:
        choice = M.magma_choice(state, reaction)  # v0.87: ［やけのこり］
        if choice is None:
            M.magma_none(state, reaction)
        elif isinstance(choice, M.MagmaChoice):
            blocked, code, reason = choice.unresolved
            extra: tuple = () if not blocked else (("unresolved_choices", blocked), ("unresolved_code", code), ("unresolved_reason", reason))
            push_decision(state, kind=MAGMA_POOL_ENERGY, player=choice.player, options=choice.options, resume=RESUME,
                          context=((REACTION, ("magma", reaction)),) + extra)
        else:
            M.magma_move(state, reaction, choice)
        return after
    raise RuntimeError(f"知らない反応 {reaction!r}（エンジンの不具合）")


def _conductivity(state: GameState, reaction: tuple) -> None:
    """［かんでん］: つけたポケモンに特殊能力のダメージ（弱点・抵抗力を計算しない。受けるダメージを変える特殊能力・鋼エネルギーは ``received_power_damage``）。ログ ``conductivity``。"""
    _, src_owner, src_pid, power_card, index, target_owner, target_pid, card, _ = reaction
    holder = _locate(state, src_owner, src_pid)
    target = _locate(state, target_owner, target_pid)
    slot = _slot(state, holder, power_card, index)
    amount, applied = E.received_power_damage(state, target_owner, target, holder, slot.effect.amount)
    E.bench_guard_outside_attack_check(state, target_owner, target, amount)
    target.damage += amount
    extra = {} if not applied else {"amount_before": slot.effect.amount, "received_modifiers": E.received_modifiers_log(applied)}
    state.add_event("conductivity", player=src_owner, pokemon=holder.card, pokemon_id=holder.pokemon_id, power=str(slot.key), target_player=target_owner,
                    target=target.card, target_pokemon_id=target.pokemon_id, energy=card, amount=amount, total_damage=target.damage,
                    knocked_out=E.knocked_by_hp(state, target), **extra)
    E.remove_on_damage(state, target_owner, target, amount)


def _lightning_burst(state: GameState, reaction: tuple, after: tuple) -> tuple:
    """［いなびかり］: かならずはたらく（ログ ``pokemon_power`` の ``forced``・``trigger``）。相手に控えがいなければ、はたらかない（ログ ``lightning_burst_skipped``）。いれば
    相手プレイヤーが控えを選ぶ（決定 ``SELECT_POKEMON``。再開先 ``"reaction"``）。選ぶと受け付けられない状態になる控えは選べるが選ぶと止める。"""
    _, owner, pid, power_card, index, card, _, _ = reaction
    holder = _locate(state, owner, pid)
    slot = _slot(state, holder, power_card, index)
    opponent = 1 - owner
    if not state.players[opponent].bench:
        state.add_event("lightning_burst_skipped", player=owner, pokemon=holder.card, pokemon_id=pid, power=str(slot.key), energy=card, reason="no_bench")
        return after
    state.add_event("pokemon_power", player=owner, pokemon=holder.card, pokemon_id=pid, power=slot.power.name_ja, power_index=index, forced=True, trigger=card)
    lock = E.active_leave_lock(state, opponent)
    if lock is not None:
        # v0.93: 相手の対戦ポケモンが「バトル場をはなれられない」なら、入れ替える部分は起こらない（相手に選ばせない）
        E.note_leave_prevented(state, opponent, state.players[opponent].active, lock, E.LEAVE_SWITCH, power=str(slot.key))
        return after
    stops = E.switch_choice_stops(state, opponent)
    extra: tuple = ()
    if stops:
        extra = (("unresolved_choices", tuple(s[0] for s in stops)), ("unresolved_detail", tuple(stops)))
    push_decision(state, kind=SELECT_POKEMON, player=opponent, options=[p.pokemon_id for p in state.players[opponent].bench], resume=RESUME,
                  context=((REACTION, ("burst", reaction)),) + extra)
    return after


def _offer_use(state: GameState, reaction: tuple) -> None:
    """［エナジーしんか］・［れんさしんか］の使う機会（決定 ``REACTION_POWER``。決めるのは持ち主。0〜1 個。使うを選ぶと止める場合は ``unresolved_choices``）。"""
    owner, pid = reaction[1], reaction[2]
    problem = use_problem(state, reaction)
    extra: tuple = ()
    if problem is not None:
        extra = (("unresolved_choices", (pid,)), ("unresolved_code", problem[0]), ("unresolved_reason", problem[1]))
    push_decision(state, kind=REACTION_POWER, player=owner, options=(pid,), resume=RESUME, context=((REACTION, ("use", reaction)),) + extra,
                  min_choices=0, max_choices=1)


def use_problem(state: GameState, reaction: tuple) -> tuple[str, str] | None:
    """使うを選ぶと止める場合（コインの前）: エナジーしんかのつけたカードの色が決まらない（RB1・MEC1）。どちらも、今の番に退化したこのカード（DV2）。"""
    owner, pid = reaction[1], reaction[2]
    holder = _locate(state, owner, pid)
    if reaction[0] == ENERGY_EVOLUTION:
        _, problem = card_color(state, reaction[5])
        if problem is not None:
            return problem
    from .evolution import (
        DEVOLVED_THIS_TURN_CODE,
        DEVOLVED_THIS_TURN_REASON,
        devolved_this_turn,
    )

    if devolved_this_turn(state, holder):
        return DEVOLVED_THIS_TURN_CODE, DEVOLVED_THIS_TURN_REASON
    return None


def search_candidates(state: GameState, reaction: tuple) -> list[int]:
    """山札の、このポケモンに今重ねられる進化カード（uid の小さい順。通常の進化の制限 ``evolution_block`` の ``from_deck``）。エナジーしんかは、名前が「(``name``)」から進化し、
    つけたカードと同じ色のもの。れんさしんかは、このカードの今の名前から進化するもの（1 進化を飛ばさない）。"""
    owner, pid = reaction[1], reaction[2]
    holder = _locate(state, owner, pid)
    slot = _slot(state, holder, reaction[3], reaction[4])
    if reaction[0] == ENERGY_EVOLUTION:
        color, _ = card_color(state, reaction[5])
        name = slot.effect.name
    else:
        color, name = None, E.form_def(state, holder).name_ja
    found = []
    for uid in sorted(state.players[owner].deck):
        definition = state.card_def(uid)
        if definition.category != "pokemon" or not definition.is_evolution_pokemon or not definition.supported:
            continue
        if definition.evolves_from != name or (color is not None and definition.pokemon_type is not color):
            continue
        if color is None and reaction[0] == ENERGY_EVOLUTION:
            continue
        if evolution_block(state, holder, definition, from_deck=True) is None:
            found.append(uid)
    return found


def answer(state: GameState, decision, choices: tuple[int, ...]) -> tuple:
    """再開先 ``"reaction"`` の決定への答え。続きの最初に処理する段を返す（順番の決定の残りの反応）。"""
    item = decision.context_value(REACTION)
    if decision.kind == REACTION_ORDER:
        return answer_order(state, decision, choices)
    tag, reaction = item
    if tag == "burst":
        owner, pid = reaction[1], reaction[2]
        opponent = 1 - owner
        holder = _locate(state, owner, pid)
        slot = _slot(state, holder, reaction[3], reaction[4]) if holder is not None else None
        key = str(slot.key) if slot is not None else str(E.PowerKey(state.cards[reaction[3]].card_id, reaction[4]))
        E._switch_active_with_bench(state, opponent, choices[0], power=key)
        return ()
    if tag == "use":
        return _answer_use(state, reaction, choices)
    if tag == "magma":
        if choices[0] in tuple(decision.context_value("unresolved_choices", ())):
            raise UnsupportedError(decision.context_value("unresolved_code"), decision.context_value("unresolved_reason"))
        M.magma_move(state, reaction, choices[0])
        return ()
    if tag == "search":
        return _answer_search(state, reaction, choices)
    raise RuntimeError(f"知らない反応の決定 {item!r}（エンジンの不具合）")


def _answer_use(state: GameState, reaction: tuple, choices: tuple[int, ...]) -> tuple:
    owner, pid, power_card, index = reaction[1], reaction[2], reaction[3], reaction[4]
    holder = _locate(state, owner, pid)
    slot = _slot(state, holder, power_card, index)
    name = slot.power.name_ja
    if not choices:
        state.add_event("reaction_power_declined", player=owner, pokemon=holder.card, pokemon_id=pid, power=name, power_index=index, trigger=reaction[5])
        return ()
    state.add_event("pokemon_power", player=owner, pokemon=holder.card, pokemon_id=pid, power=name, power_index=index, trigger=reaction[5])
    if reaction[0] == ENERGY_EVOLUTION:
        flips = flip_coins(state, owner, 1, source="power", effect=str(slot.key), card=holder.card, pokemon_id=pid)
        if flips.results[0] is not CoinSide.HEADS:
            return ()
    _offer_search(state, reaction)
    return ()


def _offer_search(state: GameState, reaction: tuple) -> None:
    """山札の進化カードを選ぶ決定（``SEARCH_DECK``。再開先 ``"reaction"``）。選べるカードがなくても出して答えを待つ（見えない山札の中身で、決定の有無・選ぶ数の境界を変えない。
    選べるものの数は観測で決めるプレイヤーだけに見せる）。重ねると HP がのっているダメージ以下になるカードは選べるが選ぶと止める（v0.4a の H1）。"""
    owner, pid = reaction[1], reaction[2]
    holder = _locate(state, owner, pid)
    candidates = search_candidates(state, reaction)
    blocked = tuple(uid for uid in candidates if holder.damage >= E.evolution_hp(state, holder, uid))
    extra: tuple = ()
    if blocked:
        extra = (("unresolved_choices", blocked), ("unresolved_code", "UNRESOLVED_EVOLUTION_HP"), ("unresolved_reason", E.EVOLUTION_HP_REASON))
    count = 1 if candidates else 0
    push_decision(state, kind=SEARCH_DECK, player=owner, options=candidates, resume=RESUME, context=((REACTION, ("search", reaction)),) + extra,
                  min_choices=count, max_choices=count)


def _answer_search(state: GameState, reaction: tuple, choices: tuple[int, ...]) -> tuple:
    owner, pid, power_card, index = reaction[1], reaction[2], reaction[3], reaction[4]
    holder = _locate(state, owner, pid)
    slot = _slot(state, holder, power_card, index)
    key = str(slot.key)
    if not choices:
        state.add_event("evolve_from_deck_none", player=owner, pokemon_id=pid, power=key)
        shuffle_deck(state, owner, power=key)
        return ()
    card = choices[0]
    if card not in search_candidates(state, reaction):
        raise RuntimeError(f"選んだ進化カード {card} が、このポケモンに重ねられる山札のカードではない（エンジンの不具合）")
    before_name = E.form_def(state, holder).name_ja
    place_evolution_card(state, owner, holder, card, power=key)
    if E.evolution_heal_terms(state, holder, before_name) is not None:
        raise RuntimeError("特殊能力による進化で、トキワシティジムの機会が来た（イーブイの進化カードは「サカキのポケモン」ではない。エンジンの不具合）")
    shuffle_deck(state, owner, power=key)
    # 山札から重ねた進化（「手札から場に出して」の機会はない。「場に出た時」の特殊能力は機会がある）。この進化の事実への反応は、待っている反応のあと（事実の起こった順）
    return (APPEND,) + evolution_steps(state, owner, holder, entry_from_hand=False)


def answer_problems(state: GameState, decision) -> list[str]:
    """再開先 ``"reaction"`` の決定の形の不変条件（決めるプレイヤー・選べるもの・選ぶ数）。"""
    item = decision.context_value(REACTION)
    if not isinstance(item, tuple) or not item:
        return [f"反応の決定 {decision.kind} の続きの情報 {item!r} が正しくない"]
    if decision.kind == REACTION_ORDER:
        if decision.player != state.current_player:
            return [f"反応の順番の決定をするのが、番のプレイヤー {state.current_player} ではなくプレイヤー {decision.player}"]
        _, _, order, _ = item
        if decision.options != tuple(range(len(order))) or len(order) < 2 or (decision.min_choices, decision.max_choices) != (1, 1):
            return [f"反応の順番の決定の選べるもの {decision.options} が、待っている反応 {len(order)} 個の位置ではない"]
        if not any(_still_working(state, r) for r in order):
            return [f"反応の順番の決定の待っている反応 {order!r} に、はたらく反応がない"]
        return []
    tag, reaction = item
    owner, pid = reaction[1], reaction[2]
    if _locate(state, owner, pid) is None:
        return [f"反応の決定 {decision.kind} の特殊能力を持つポケモン {pid} が、持ち主 {owner} の場にいない"]
    if tag == "burst":
        expected = tuple(p.pokemon_id for p in state.players[1 - owner].bench)
        if decision.kind != SELECT_POKEMON or decision.player != 1 - owner or decision.options != expected:
            return [f"［いなびかり］の決定 {decision.kind} {decision.options} を選ぶのが相手プレイヤー {1 - owner} の控え {expected} ではない"]
        return []
    if tag == "magma":
        # v0.87: ［やけのこり］でつけ替えるカード（決めるのは持ち主。選べるものは今のつけ替えられるカード。1 枚）
        try:
            choice = M.magma_choice(state, reaction)
        except UnsupportedError as error:
            return [f"［やけのこり］の決定 {decision.id} の候補が決められない（{error.code}）"]
        if not isinstance(choice, M.MagmaChoice) or decision.kind != MAGMA_POOL_ENERGY or decision.player != owner or decision.options != choice.options or (
                decision.min_choices, decision.max_choices) != (1, 1):
            return [f"［やけのこり］の決定 {decision.kind} {decision.options} が、持ち主 {owner} のつけ替えられるカードの 1 枚ではない"]
        return []
    if tag == "use":
        if decision.kind != REACTION_POWER or decision.player != owner or decision.options != (pid,) or (decision.min_choices, decision.max_choices) != (0, 1):
            return [f"反応の特殊能力の使う機会 {decision.kind} {decision.options} の形が正しくない"]
        return []
    if tag == "search":
        candidates = tuple(search_candidates(state, reaction))
        count = 1 if candidates else 0
        if decision.kind != SEARCH_DECK or decision.player != owner or decision.options != candidates or (decision.min_choices, decision.max_choices) != (count, count):
            return [f"反応の特殊能力の進化カードを選ぶ決定 {decision.kind} {decision.options} が、重ねられる山札のカード {candidates} ではない"]
        return []
    return [f"知らない反応の決定 {item!r}"]


__all__ = [
    "FOLLOWUP",
    "RESUME",
    "answer",
    "answer_problems",
    "attach_followup",
    "collect_attach",
    "collect_evolution",
    "collect_placed",
    "evolution_steps",
    "run",
]
