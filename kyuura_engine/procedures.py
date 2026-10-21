"""対戦の進行の共通の手続き（v0.15a。docs/integration-dependencies-v0.15a.md）。

v0.13 まで ``engine.py`` の中にあった、状態を変える手続きのうち、v0.13 の解決の経路（``engine.py``）と v0.15 の解決の基盤
（``kyuura_engine/resolution/``）の両方が使うものです。中身（ルールの意味・ログの形と順番・乱数の使い方）は v0.13 と同じで、
名前の先頭の ``_`` をとっただけです（``engine.py`` は v0.13 の名前で読み込む）。``engine.py`` を読み込みません。

- 番の始まり・終わり: ``begin_turn``・``expire_at_turn_end``（番の終わりの期限）・``discard_expired_attachments``
- ポケモンチェック: ``pokemon_check_poison``（2 の「どく」）・``pokemon_check_sleep_and_paralysis``（3・4 と次の番）
- こんらん: ``confusion_check``・``confusion_damage``・``confusion_damage_problem``
- きぜつ・対戦の終わり・止める: ``knock_out``・``finish``・``halt``

きぜつのあとの流れ（サイド・勝ち負け・交代・決定）は、解決の基盤（``resolution/flow.py``）が持ちます（v0.16b で v0.13 の経路
（``engine.py``）を外し、1 つになった）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import judge
from .coins import CoinSide, flip_coins
from .conditions import CONFUSION_DAMAGE, paralysis_recovery_turn, recover_from_paralysis, recover_from_sleep
from .damage import calculate_confusion_damage
from .effects import (
    DARKNESS_BONUS, DARKNESS_RECEIVED_POWER_CODE, PENALTY_DAMAGE, bench_guard_outside_attack_check, darkness_penalties, darkness_received_power_problem,
    energy_received_damage, energy_reduction_log, scram_watch, SCRAM_TIMING_CODE,
    knocked_by_hp,
    EXPIRE_TO_HAND,
    TypeReadingsDiffer, attack_damage_modifiers, confusion_power_modifiers, definition_views, max_hp, poison_received_power_problem,
    same_for_type_readings, shift_duration_error, MAX_HP_DROP_CODE, state_stop_after,
)
from .errors import UnsupportedError
from .persistent import (KNOCK_OUT, USED, remove_expired_persistent_effects, remove_on_damage, remove_persistent_effects,
                         remove_turn_start_expired_persistent_effects)
from .state import POWER_SUPPRESSION, Halt, Phase
from .history import prune as prune_history
from .zones import draw_cards, return_expired_set_aside

if TYPE_CHECKING:
    from .state import GameResult, GameState, PokemonInPlay

# きぜつのあとの決定の続き（context の "then"）: ポケモンチェックの中（2 の「どく」）のきぜつのあとの決定（v0.3a）。
# 交代が終わったら、ポケモンチェックの残り（3 の「ねむり」・4 の「マヒ」。v0.3b）をしてから次の番を始める。
# 値は v0.3a と同じ（ポケモンチェックの中で、次の番はまだ始まっていないことを表す。書き出しの形を変えないため）
NEXT_TURN = "next_turn"
# v0.42: 特殊能力の処理のあと（きぜつ・場をはなれて空いたバトル場）の決定の続き。サイド・勝ち負け・ふしちょう・交代が終わったら、番のプレイヤーの番に
# もどる（``Phase.MAIN``。特殊能力を使っても番は終わらない。p.311・p.323）。ワザのあと（続きなし = 番の終わり）・ポケモンチェックの中（NEXT_TURN）と区別する
CONTINUE_TURN = "continue_turn"

# v0.47（KA1。docs/fossil-hidden-info-v0.47.md 4 章）: ポケモンチェックの「どく」のダメージ（ワザによるダメージではない。p.321・p.322）に、受けるダメージを変える
# 常にはたらく特殊能力（カブトの［カブトアーマー］「このカードが受けるダメージは半分(切りすて)になる。(ダメージ以外の効果はそのまま)」）を当てはめるか
POISON_RECEIVED_POWER = Halt(
    code="UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER",
    message=(
        "説明の「受けるダメージ」がポケモンチェックの「どく」のダメージを含むかは、公式ルール 2000.02.14版（p.321 のダメージの計算はワザによるダメージ・p.322 の"
        "「どく」）とカードの文面から決められないので、ダメージを与える前に対戦を止める（KA1）"
    ),
    references=("P43 p.321", "P43 p.322", "P43 p.323", "NEO-2000-OFFICIAL-RULES", "docs/fossil-hidden-info-v0.47.md 4 章"),
)

POKEMON_CHECK_DOUBLE_KNOCKOUT = Halt(
    code="UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT",
    message=(
        "ポケモンチェックの「どく」のダメージで、両方のプレイヤーのポケモンがきぜつする。"
        "同時のきぜつか（p.324）、バトル場に出す順番（pp.323〜324。ポケモンチェックはどちらの番でもない。p.323）、"
        "サイドを取る順番を決めるプレイヤー（p.325）が公式ルール 2000.02.14版から決められないので、対戦を止める。"
    ),
    references=("P43 p.322", "P43 p.323", "P43 p.324", "P43 p.325", "NEO-2000-OFFICIAL-RULES", "knockout_timing"),
)


def expire_at_turn_end(state: GameState) -> bool:
    """番の終わりの期限（v0.13 の ``engine._end_turn`` の前半と同じ順番）: ついているトレーナーのトラッシュ（v0.2c）→ ワザによる持続する
    効果（v0.4b）→ こんらんで「にげる」に失敗した記録（v0.3c）→ ログ ``turn_end``。このあとにポケモンチェック。

    v0.59: この番の終わりに、まきちらせ!ベトベトガスの効果（``POWER_SUPPRESSION``）が消えるなら、消えたあと（特殊能力がまたはたらく。CR-POWER-BACK-AFTER-RECOVERY と同じ
    読み方）の状態が受け付けられない状態（決められない姿・ダメージ以外の原因で最大HPがのっているダメージ以下。``effects.state_stop_after``）になるかを、期限の処理の前に
    状態の複製の上で確かめ、なるなら対戦を止めて（``Phase.HALTED``）偽を返す（番の終わりのあとにきぜつの判定はなく、どの操作でも番は終わるので、コマンドを拒否しない。
    v0.48 のポケモンチェックの MH1 と同じ形）。ほかは期限の処理をして真を返す。"""
    if any(record.kind == POWER_SUPPRESSION and record.expires_turn == state.turn_number for record in state.trainer_effects):
        trial = state.clone()
        _expire_at_turn_end(trial)
        stop = state_stop_after(state, trial)
        if stop is not None:
            code, message = stop
            halt(state, Halt(code=code, message=f"番の終わりにまきちらせ!ベトベトガスの効果が消えると: {message}",
                             references=("GR-2000-P323-KNOCKOUT", "CR-POWER-BACK-AFTER-RECOVERY", "docs/energy-control-power-suppression-v0.59.md")))
            return False
    _expire_at_turn_end(state)
    return True


def _expire_at_turn_end(state: GameState) -> None:
    discard_expired_attachments(state)
    remove_expired_persistent_effects(state)
    for p in state.players:
        for pokemon in p.in_play():
            pokemon.retreat_failed_turn = None
            # v0.44: トレーナー「サカキ」の、今の番だけの進化の許可（説明の「今の番」「同じ番で」）
            pokemon.evolution_permission_turn = None
    # v0.31: 「エナジーバーン」で「炎」エネルギーになったエネルギーは、自分の番の終わりにもとにもどる（TXT-CHARIZARD の最新の説明）
    state.energy_burn = ()
    # v0.49: 「思い出させる」の「この番だけ」（docs/virtual-attacks-transformation-v0.49.md 6 章）。ログ ``recall`` の番で分かるので、消すログは出さない
    state.recalls = ()
    remove_expired_trainer_locks(state)  # v0.47
    remove_expired_trainer_effects(state)  # v0.56
    return_expired_set_aside(state)  # v0.63: くすぐりマシーンで置いておいたカード（「次の相手の番の終わりまで」）
    state.add_event("turn_end", player=state.current_player)


def remove_expired_trainer_locks(state: GameState) -> None:
    """v0.47: 消える番（``expires_turn``）が今の番の、期限のあるトレーナーの使用の禁止（``GameState.trainer_locks``。ずつう・こうしゅうはの「次の相手の番の終わりまで」）
    を消す。1 つにつきログ ``trainer_lock_removed``（``player``・``source_player``・``effect``・``created_turn``・``expires_turn``・``reason`` は ``expired``）。常にはたらく
    特殊能力による禁止（［アレルギーかふん］）は状態に持たないので関係しない。"""
    kept = []
    for lock in state.trainer_locks:
        if lock.expires_turn == state.turn_number:
            origin = {} if lock.origin == "attack" else {"origin": lock.origin}  # v0.56: トレーナーの効果の禁止だけ書く（ワザの禁止のログの形は v0.55 と同じ）
            state.add_event("trainer_lock_removed", player=lock.player, source_player=lock.source_player, effect=lock.effect,
                            created_turn=lock.created_turn, expires_turn=lock.expires_turn, reason="expired", **origin)
        else:
            kept.append(lock)
    state.trainer_locks = tuple(kept)


def remove_expired_trainer_effects(state: GameState) -> None:
    """v0.56: 消える番（``expires_turn``）が今の番の、プレイヤーに与えた期限のあるトレーナーの効果（``GameState.trainer_effects``。カスミ・キョウの「この番」、見えない壁の
    「次の相手の番が終わるまで」）を消す。1 つにつきログ ``trainer_effect_removed``（``player``・``effect_kind``・``trainer_card``・``card_id``・``created_turn``・``expires_turn``・
    ``reason`` は ``expired``）。番の終わり方（ワザ・番を終える操作・ロケット団員の「うら」）によらず、この番の終わりの窓で消す。"""
    kept = []
    for record in state.trainer_effects:
        if record.expires_turn == state.turn_number:
            state.add_event("trainer_effect_removed", player=record.player, effect_kind=record.kind, trainer_card=record.source_card, card_id=record.card_id,
                            created_turn=record.created_turn, expires_turn=record.expires_turn, reason="expired")
        else:
            kept.append(record)
    state.trainer_effects = tuple(kept)


def pokemon_check_poison(state: GameState) -> list[tuple[int, PokemonInPlay]] | None:
    """ポケモンチェック（p.323）の始まりと 1 の「指示されたこと」（v0.78 の悪エネルギー）と 2 の「どく」のダメージ（v0.13 の ``engine._pokemon_check`` の前半と同じ）。

    ログ ``pokemon_check`` →（v0.78）悪エネルギーの効果（ログ ``darkness_energy_damage``・``darkness_energy_counters``）→ どく状態のポケモンにダメージ（ログ ``poison_damage``）。
    HP 以上のダメージのポケモン（番を終えたプレイヤーの場から。バトル場 → ベンチ）を返す。両方のプレイヤーのポケモンがきぜつする場合は、ダメージを与える前に対戦を止め
    （``UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT``）、None を返す。

    v0.78（docs/darkness-metal-energy-v0.78.md 5 章）: 1 と 2 のあいだのきぜつの判定の時点は決めない（どの時点でも結果が変わらない場合だけを処理する: 両方のプレイヤーの
    ポケモンがきぜつするなら 1・2 を合わせて止める）。［ずらかる］のポケモンの残りHPが、1・2 の途中で「10」になってそのあと変わるなら、はたらく時点で結果が変わるので、
    ダメージを与える前に止める（SC1）。悪エネルギーの効果は、ワザによるダメージではないので「ダメージを受けない」状態・持続する効果（どちらの番でもない。p.323）を
    見ない（どくと同じ）。受けるダメージを変える常にはたらく特殊能力で量が変わるなら DE1、控えの［ベンチガード］は v0.65 のエンジンの未対応、「悪」「わるい」ポケモンかが
    VS1 で決まらなければ VS1 で、どれもダメージを与える前に止める。鋼エネルギー（NIP1X-010）は悪エネルギーのダメージ（カードごと）・どくのダメージを「-10」する。
    """
    state.add_event("pokemon_check")
    order = (state.current_player, 1 - state.current_player)  # ログの順（番を終えたプレイヤーの場から）
    try:
        penalties = darkness_penalties(state, order)
        for owner, pokemon, _, kind in penalties:
            if kind != PENALTY_DAMAGE:
                continue
            problem = darkness_received_power_problem(state, pokemon, DARKNESS_BONUS)
            if problem is not None:
                raise UnsupportedError(DARKNESS_RECEIVED_POWER_CODE, problem)
            if state.players[owner].active is not pokemon:
                bench_guard_outside_attack_check(state, owner, pokemon, energy_received_damage(state, pokemon, DARKNESS_BONUS)[0])
    except UnsupportedError as error:
        halt(state, Halt(code=error.code, message=f"ポケモンチェックの悪エネルギーで: {error.message}",
                         references=("GR-2000-P323-POKEMON-CHECK", "docs/darkness-metal-energy-v0.78.md 5 章")))
        return None
    poisoned = [
        (owner, pokemon)
        for owner in order
        for pokemon in state.players[owner].in_play()
        if pokemon.conditions.poison is not None
    ]
    for owner, pokemon in poisoned:
        # v0.47（KA1）: 受けるダメージを変える常にはたらく特殊能力（カブトアーマー）を、どくのダメージに当てはめるかは決められない。当てはめると量が変わるなら、
        # ダメージを与える前に対戦を止める
        problem = poison_received_power_problem(state, owner, pokemon, pokemon.conditions.poison.damage)
        if problem is not None:
            halt(state, Halt(code=POISON_RECEIVED_POWER.code, message=f"{problem}。{POISON_RECEIVED_POWER.message}", references=POISON_RECEIVED_POWER.references))
            return None
    per = state.rules.damage_per_counter
    steps: dict[int, list[int]] = {}  # ポケモンの番号 → 1・2 の処理ごとののっている数（はじめの数から）
    for _, pokemon, _, kind in penalties:
        seq = steps.setdefault(pokemon.pokemon_id, [pokemon.damage])
        seq.append(seq[-1] + (energy_received_damage(state, pokemon, DARKNESS_BONUS)[0] if kind == PENALTY_DAMAGE else per))
    for _, pokemon in poisoned:
        seq = steps.setdefault(pokemon.pokemon_id, [pokemon.damage])
        seq.append(seq[-1] + energy_received_damage(state, pokemon, pokemon.conditions.poison.damage)[0])
    projected = {pid: seq[-1] for pid, seq in steps.items()}
    for owner in order:
        for pokemon in state.players[owner].in_play():
            seq = steps.get(pokemon.pokemon_id, ())
            if any(max_hp(state, pokemon) - value == 10 and value != seq[-1] for value in seq[1:-1]) and scram_watch(state, pokemon):
                # v0.78: ［ずらかる］（残りHPが「10」になった時）。1・2 の途中で「10」を通る（そのあときぜつする）なら、はたらく時点が決まらない（SC1。v0.61 と同じ問い）
                halt(state, Halt(code=SCRAM_TIMING_CODE, message=f"ポケモンチェックの悪エネルギー・「どく」の途中で、ポケモン {pokemon.pokemon_id} の残りHPが「10」を通る（SC1）",
                                 references=("GR-2000-P323-POKEMON-CHECK", "docs/reactive-powers-trainer-damage-v0.61.md", "docs/darkness-metal-energy-v0.78.md 5 章")))
                return None
    knocked_owners = {
        owner for owner in order for pokemon in state.players[owner].in_play()
        if pokemon.pokemon_id in projected and projected[pokemon.pokemon_id] >= max_hp(state, pokemon)  # v0.48: 今有効な最大HP
    }
    if len(knocked_owners) > 1:
        if not penalties:
            halt(state, POKEMON_CHECK_DOUBLE_KNOCKOUT)
        else:
            halt(state, Halt(code=POKEMON_CHECK_DOUBLE_KNOCKOUT.code, message="（v0.78: 悪エネルギーの効果を含む）" + POKEMON_CHECK_DOUBLE_KNOCKOUT.message,
                             references=POKEMON_CHECK_DOUBLE_KNOCKOUT.references + ("docs/darkness-metal-energy-v0.78.md 5 章",)))
        return None
    for owner, pokemon, uid, kind in penalties:
        if kind == PENALTY_DAMAGE:
            amount, cards = energy_received_damage(state, pokemon, DARKNESS_BONUS)
            pokemon.damage += amount
            state.add_event("darkness_energy_damage", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, energy=uid, amount=amount,
                            total_damage=pokemon.damage, **energy_reduction_log(DARKNESS_BONUS, amount, cards))
            remove_on_damage(state, owner, pokemon, amount)
        else:
            pokemon.damage += per
            state.add_event("darkness_energy_counters", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, energy=uid, counters=1,
                            total_damage=pokemon.damage)
    for owner, pokemon in poisoned:
        printed = pokemon.conditions.poison.damage
        amount, cards = energy_received_damage(state, pokemon, printed)  # v0.78: 鋼エネルギー（NIP1X-010）
        pokemon.damage += amount
        state.add_event(
            "poison_damage",
            player=owner,
            pokemon=pokemon.card,
            pokemon_id=pokemon.pokemon_id,
            amount=amount,
            total_damage=pokemon.damage,
            **energy_reduction_log(printed, amount, cards),
        )
        remove_on_damage(state, owner, pokemon, amount)  # v0.60: 「かげぶんしん」はダメージを受けたら消える（どくのダメージも「ダメージ」）
    return [
        (owner, pokemon)
        for owner in order
        for pokemon in state.players[owner].in_play()
        if knocked_by_hp(state, pokemon)
    ]


def finish(state: GameState, result: GameResult) -> None:
    state.result = result
    state.phase = Phase.SUDDEN_DEATH if result.outcome == "sudden_death" else Phase.GAME_OVER
    state.decision = None
    state.add_event("game_end", outcome=result.outcome, winner=result.winner, conditions=result.conditions)


def halt(state: GameState, halt: Halt) -> None:
    """原典で決められない処理に当たったので、対戦を止める（``Phase.HALTED``。終端）。"""
    state.phase = Phase.HALTED
    state.halt = halt
    state.decision = None
    state.add_event("halted", code=halt.code)


def begin_turn(state: GameState, player: int) -> None:
    """番の最初に山札から必ず 1 枚引く。引けなければその時点で負け（p.309）。"""
    state.turn_number += 1
    state.current_player = player
    state.energy_attachments_this_turn = 0
    state.energy_attached_by_powers_this_turn = 0  # v0.6（ポケモンパワーで手札からつけた枚数）
    state.power_uses_this_turn = ()  # v0.31（「自分の番ごとに1回使える」特殊能力を使ったポケモン）
    state.stadium_uses_this_turn = ()  # v0.57（「自分の番ごとに1回」のスタジアムの効果。セキチクシティジム）
    state.phase = Phase.MAIN
    state.add_event("turn_start", player=player)
    remove_turn_start_expired_persistent_effects(state)  # v0.34: 「次の自分の番の始めに消える」持続する効果（「なきつく」）
    prune_history(state)  # v0.62: 2 つ前の番より古いワザの履歴を消す（ログは残さない）
    if state.turn_number == 1 and not state.rules.first_player_draws_on_first_turn:
        return
    if not state.players[player].deck:
        state.add_event("deck_out", player=player)
        finish(state, judge.deck_out(player))
        return
    draw_cards(state, player, 1)


def discard_expired_attachments(state: GameState) -> None:
    """有効期限（``AttachedTrainer.discard_at_end_of_turn``）が今の番のついているトレーナーをトラッシュする。

    番のプレイヤーの場（バトル場 → ベンチ）、相手の場の順。トラッシュにあるカードには順番がない（p.312）。
    """
    for owner in (state.current_player, 1 - state.current_player):
        for pokemon in state.players[owner].in_play():
            expired = [t for t in pokemon.trainers if t.discard_at_end_of_turn == state.turn_number]
            for attached in expired:
                pokemon.trainers.remove(attached)
                card_owner = state.cards[attached.card].owner
                destination = state.effects.trainer_entry(state.cards[attached.card].card_id).effect.expiry_destination
                if destination == EXPIRE_TO_HAND:
                    # v0.66: お上品攻撃の「相手の番が終わったら、手札にもどす」。つけたプレイヤー（``attached.player``）と持ち主は同じ（つけて使うトレーナーは錯乱ジム・
                    # サイキックコントロールで借りて使えない）。違えば、もどす手札が決まらないのでエンジンの不具合
                    if card_owner != attached.player:
                        raise RuntimeError(f"ついているトレーナー {attached.card} をつけたプレイヤー {attached.player} が持ち主 {card_owner} と違う（エンジンの不具合）")
                    state.players[card_owner].hand.append(attached.card)
                    state.add_event("return_attached_trainer", player=card_owner, card=attached.card, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id,
                                    reason="end_of_turn")
                    continue
                state.players[attached.player].discard.append(attached.card)
                state.add_event(
                    "discard_attached_trainer",
                    player=attached.player,
                    card=attached.card,
                    pokemon=pokemon.card,
                    pokemon_id=pokemon.pokemon_id,
                    reason="end_of_turn",
                )


def pokemon_check_sleep_and_paralysis(state: GameState) -> None:
    """ポケモンチェックの 3（ねむり）・4（マヒ）をして、次の番を始める（v0.3b。p.322・p.323）。

    2 の「どく」のあと（きぜつがあれば、サイド・判定・交代のあと）に 1 回だけ呼ぶ。3・4 ではダメージを与えないので、
    きぜつは起こらず、プレイヤーの決定も出ない。

    3. ねむり状態のポケモンの側のプレイヤーが、コインを 1 枚投げる（``flip_coins``。``source`` は ``"pokemon_check"``、
       ``effect`` は ``"sleep"``）。「おもて」ならねむり状態から回復し、「うら」ならねむり状態は続く（p.322・p.323）。
       どちらのプレイヤーの番のあとのポケモンチェックでも投げる（p.322「ポケモンチェックのたびに」）。
       ログ ``sleep_check``（``player``・``pokemon``・``pokemon_id``・``result``・``recovered``）。
       両方のプレイヤーの対戦ポケモンがねむり状態なら、どちらが先にコインを投げるか（順番を決める人がいるか）が
       原典で決まらず、順番で乱数の割り当て（どちらのコインがどの結果になるか）が変わるので、コインを投げる前に
       対戦を止める（``UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER``）。v0.3b の対応カードでは起こらない
       （docs/pokemon-check-v0.3b.md）。
    4. マヒ状態のポケモンは、マヒ状態になった番の「次の自分（そのポケモンの持ち主）の番」の終わりのポケモンチェックで
       自動的に回復する（p.322・p.323）。コインは投げない。回復する番は ``conditions.paralysis_recovery_turn``。
    """
    order = (state.current_player, 1 - state.current_player)  # ログの順（番を終えたプレイヤーの場から）
    # 3. 「ねむり」からさめるかどうか（特殊状態になるのはバトル場のポケモンだけ。p.322）
    asleep = [
        (owner, state.players[owner].active)
        for owner in order
        if state.players[owner].active is not None and state.players[owner].active.conditions.asleep
    ]
    if len(asleep) > 1:
        halt(
            state,
            Halt(
                code="UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER",
                message=(
                    "ポケモンチェックで、両方のプレイヤーの対戦ポケモンがねむり状態。p.323 の 3 は「ねむり状態になっている"
                    "ポケモンの側のプレイヤーは、コインを投げます」とだけ書き、どちらが先に投げるか（順番を決めるプレイヤー）を"
                    "公式ルール 2000.02.14版から決められない（ポケモンチェックはどちらの番でもない。p.323・p.325）。投げる順番で"
                    "乱数の割り当てが変わるので、コインを投げる前に対戦を止める。"
                ),
                references=("P43 p.322", "P43 p.323", "P43 p.325", "NEO-2000-OFFICIAL-RULES"),
            ),
        )
        return
    # v0.48（MH1）: ねむり・マヒから回復すると、そのポケモンの特殊能力（かがくへんかガス）がはたらきはじめ、ほかのポケモンの最大HP（［ガスのからだ］）が下がって、のっている
    # ダメージ以下になる場合がある。ポケモンチェックの 3・4 のあとに、きぜつの判定はない（p.323）ので決められない。ねむりのコイン・マヒの回復の前に止める
    paralyzed_now = [
        (owner, state.players[owner].active)
        for owner in order
        if state.players[owner].active is not None and state.players[owner].active.conditions.paralyzed
        and paralysis_recovery_turn(state, owner, state.players[owner].active.conditions.exclusive.turn) == state.turn_number
    ]
    # v0.49: 回復すると、決められない姿（［へんしん］がはたらきはじめて写す特殊能力（TF1）・写すカード（TF2）、かがくへんかガスがはたらきはじめて「ばける」が消える
    # （DG1））になる場合も、同じくコインの前に止める（``effects.state_stop_after``。MH1 と合わせて確かめる）
    for owner, pokemon, recover in [(o, p, recover_from_sleep) for o, p in asleep] + [(o, p, recover_from_paralysis) for o, p in paralyzed_now]:
        stop = _recovery_stop(state, owner, pokemon, recover)
        if stop is not None:
            code, message = stop
            references = (("P43 p.322", "P43 p.323", "GR-2000-P323-POKEMON-CHECK", "GR-2000-P323-KNOCKOUT") if code == MAX_HP_DROP_CODE
                          else ("P43 p.322", "P43 p.323", "GR-2000-P323-POKEMON-CHECK", "docs/virtual-attacks-transformation-v0.49.md"))
            halt(state, Halt(code=code, message=f"ポケモンチェックで、プレイヤー {owner} のポケモン {pokemon.pokemon_id} が回復すると: {message}",
                             references=references))
            return
    for owner, pokemon in asleep:
        flips = flip_coins(state, owner, 1, source="pokemon_check", effect="sleep", card=pokemon.card, pokemon_id=pokemon.pokemon_id)
        recovered = flips.results[0] is CoinSide.HEADS
        state.add_event(
            "sleep_check",
            player=owner,
            pokemon=pokemon.card,
            pokemon_id=pokemon.pokemon_id,
            result=flips.results[0].value,
            recovered=recovered,
        )
        if recovered:
            recover_from_sleep(state, owner, pokemon)
    # 4. 「マヒ」がなおるかどうか
    for owner in order:
        pokemon = state.players[owner].active
        if pokemon is None or not pokemon.conditions.paralyzed:
            continue
        if paralysis_recovery_turn(state, owner, pokemon.conditions.exclusive.turn) == state.turn_number:
            recover_from_paralysis(state, owner, pokemon)
    begin_turn(state, 1 - state.current_player)


def _recovery_stop(state: GameState, owner: int, pokemon: PokemonInPlay, recover) -> tuple[str, str] | None:
    """``pokemon`` がねむり・マヒから回復したとしたら受け付けられない状態になるなら、その (コード, 理由の文)（v0.48 の MH1（最大HPがのっているダメージ以下に下がる）、
    v0.49 の決められない姿（TF1・TF2・DG1）。``effects.state_stop_after``。複製の上で回復させて比べる。状態を変えない）。"""
    trial = state.clone()
    recover(trial, owner, trial.players[owner].active)
    return state_stop_after(state, trial)


def confusion_check(state: GameState, player: int, pokemon: PokemonInPlay, *, action: str, effect: str) -> bool:
    """こんらん状態のポケモンがワザを使う・にげるときのコイン（v0.3c。p.309 の手順 5・p.311 の手順 3・p.322）。

    持ち主（ワザを使う・「にげる」を宣言したポケモン側のプレイヤー）がコインを 1 枚投げ、「おもて」なら成功（True）。
    ログ ``coin_flip``（``source: "confusion"``、``effect`` はワザなら ``AttackKey`` の文字列、にげるなら ``"retreat"``）と
    ``confusion_check``（``player``・``pokemon``・``pokemon_id``・``action``（``attack``／``retreat``）・``result``・
    ``succeeded``）。ワザの説明のコイン（``source: "attack"``）・ねむりのコイン（``"pokemon_check"``）と区別できる。
    """
    flips = flip_coins(state, player, 1, source="confusion", effect=effect, card=pokemon.card, pokemon_id=pokemon.pokemon_id)
    succeeded = flips.results[0] is CoinSide.HEADS
    state.add_event(
        "confusion_check",
        player=player,
        pokemon=pokemon.card,
        pokemon_id=pokemon.pokemon_id,
        action=action,
        result=flips.results[0].value,
        succeeded=succeeded,
    )
    return succeeded


ATTACK_CHECK_FAILED = "attack_check"  # v0.36: p.309 の手順 4 のコインで失敗したワザ（ログ attack_failed の reason）


def attack_coin_check(state: GameState, player: int, pokemon: PokemonInPlay, check, *, effect: str) -> bool:
    """p.309 のワザを使う手順 4（v0.36）: ワザを使うポケモンが、ワザを失敗させる効果（``state.AttackCoinCheck``。「すなかけ」・「えんまく」など）を
    受けているときのコイン。

    手順 3（宣言）のあと、手順 5（こんらん）の前。効果を受けているポケモン側のプレイヤー（ワザを使うプレイヤー。説明の「…を受けた相手は、…ワザを
    使うときにコインを投げ」）が 1 枚投げ、「おもて」なら成功（True）。ログ ``coin_flip``（``source: "attack_check"``、``effect`` は宣言したワザの
    ``AttackKey`` の文字列）と ``attack_check``（``player``・``pokemon``・``pokemon_id``・``effect``・``persistent_effect``・``source_card``・``created_turn``・
    ``result``・``succeeded``）。ワザの説明のコイン（``"attack"``）・こんらんのコイン（``"confusion"``）と区別できる。説明が「効果は1回できえる」と書く
    効果（``check.single_use``。サンドの「すなかけ」）は、コインを投げたら消す（理由 ``used``。「おもて」でも「うら」でも）。
    """
    flips = flip_coins(state, player, 1, source="attack_check", effect=effect, card=pokemon.card, pokemon_id=pokemon.pokemon_id)
    succeeded = flips.results[0] is CoinSide.HEADS
    state.add_event(
        "attack_check",
        player=player,
        pokemon=pokemon.card,
        pokemon_id=pokemon.pokemon_id,
        effect=effect,
        persistent_effect=check.kind,
        source_card=check.source_card,
        created_turn=check.created_turn,
        result=flips.results[0].value,
        succeeded=succeeded,
    )
    if check.single_use:
        remove_persistent_effects(state, player, pokemon, USED, (check,))
    return succeeded


def confusion_damage_problem(state: GameState, pokemon: PokemonInPlay, attack_status: frozenset[int] | None = None) -> UnsupportedError | None:
    """こんらんしたワザの 20 ダメージを、原典で決められる形で計算できないなら、その理由（v0.3c）。

    p.322 は「このダメージは「弱点・抵抗力」の影響を受けます」とだけ書く。こんらんのダメージが「ワザによるダメージ」
    （p.321「8」）かは書かれていないので、ワザを使うポケモンについているプラスパワー（「このカードをつけているポケモンの
    ワザが…ダメージを与えるとき」）・ディフェンダー（「ワザによるダメージを受けるとき」。p.257）の効果を計算するかを決め
    られない。それらのカードがついていなければ問題はない。ついていれば、コインを投げる前に止める（コインが「おもて」なら
    問題はないが、投げる前には分からない）。

    v0.46: 同じ問いで、場の常にはたらく特殊能力が、こんらんの 20 をワザのダメージ（このポケモンが与えるダメージ）として扱うなら当てはまるとき（エリカのフシギソウの
    ［くつろぐかおり］の「すべてのワザのダメージ」・わるいオコリザルの［きょうぼう］の「このカードがポケモンに与えるダメージ」。``effects.confusion_power_modifiers``。
    ``attack_status`` はワザが使われた時の特殊状態）も止める（新しい問いにしない）。
    """
    modifiers = attack_damage_modifiers(state, pokemon, pokemon)
    if modifiers:
        return UnsupportedError(
            "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS",
            f"こんらん状態のポケモン {pokemon.pokemon_id} に、ダメージを変えるカードがついている。こんらんしたワザで自分が受ける 20 "
            "ダメージに、プラスパワー・ディフェンダーの効果を計算するか（こんらんのダメージが「ワザによるダメージ」か）は"
            "『オフィシャルブック2000』（p.257・p.309・p.321・p.322）から決められないので扱わない",
        )
    try:
        # v0.48: 自分のタイプ（色）と自分の弱点・抵抗力（今有効な値。``effects.definition_views``）。［へんしょく］で変えた色の読み方（VS1）で 20 ダメージの計算が
        # 変わるなら、コインを投げる前に止める（こんらん状態のモルフォンでは［へんしょく］の力が消えているので、変えた色が続くかが決まらない）
        same_for_type_readings(state, (pokemon,), lambda views: calculate_confusion_damage(views[0], state.rules, CONFUSION_DAMAGE))
    except TypeReadingsDiffer:
        return shift_duration_error(pokemon, "こんらんしたワザで自分が受ける 20 ダメージの弱点・抵抗力の計算")
    powers = confusion_power_modifiers(state, pokemon, attack_status)
    if powers:
        return UnsupportedError(
            "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS",
            f"こんらん状態のポケモン {pokemon.pokemon_id} のワザがこんらんしたとき、ダメージを変える特殊能力（{'・'.join(powers)}）がはたらいている。こんらんしたワザで"
            "自分が受ける 20 ダメージが、その特殊能力の書く「ワザのダメージ」「このカードがポケモンに与えるダメージ」か（こんらんのダメージが「ワザによるダメージ」か）は"
            "『オフィシャルブック2000』（p.309・p.321・p.322）と kyuura の記録から決められないので扱わない",
        )
    return None


def confusion_damage(state: GameState, player: int, pokemon: PokemonInPlay, *, effect: str) -> None:
    """ワザがこんらんしたとき、ワザを使ったポケモン自身に 20 ダメージ（v0.3c。p.309 の手順 5・p.322）。

    弱点・抵抗力の影響を受ける（``damage.calculate_confusion_damage``）。ワザの説明による自分へのダメージ
    （``effects.deal_attack_damage`` の ``SELF``。v0.2f）とは別の規定なので、そちらを通さない。ログは ``confusion_damage``
    （``player``・``pokemon``・``pokemon_id``・``effect``（こんらんしたワザの ``AttackKey``）・``amount``・``steps``・
    ``weakness``・``resistance``・``total_damage``）。``damage`` のログ（ワザによるダメージ）とは種類を分ける。
    きぜつはワザのあとと同じきぜつの判定（解決の基盤の ``flow._finish_attack``）で判定する（サイドは相手が取る。p.323）。
    """
    calc = calculate_confusion_damage(definition_views(state, pokemon)[0], state.rules, CONFUSION_DAMAGE)  # v0.48: 今有効な値（読み方は宣言の前に確かめた）
    pokemon.damage += calc.final
    state.add_event(
        "confusion_damage",
        player=player,
        pokemon=pokemon.card,
        pokemon_id=pokemon.pokemon_id,
        effect=effect,
        amount=calc.final,
        steps=calc.steps,
        weakness=calc.weakness_applied,
        resistance=calc.resistance_applied,
        total_damage=pokemon.damage,
    )
    remove_on_damage(state, player, pokemon, calc.final)  # v0.60: 「かげぶんしん」はダメージを受けたら消える（こんらんの 20 も「ダメージ」）


def knock_out(state: GameState, owner: int, pokemon: PokemonInPlay, simultaneous: bool = False, timing: str | None = None, counted: bool = True,
              to_energy: bool = False) -> None:
    """きぜつ: ダメージカウンターを取りのぞき、ポケモンとついていたカードをすべてトラッシュする（p.323）。

    場を離れたので、このポケモンの番号（pokemon_id）は無効になり、特殊状態もいっしょになくなる（p.322）。
    進化ポケモン（v0.4a）は、重なっているカード（たねポケモンと進化カード。2 進化（v0.4c）なら 3 枚）をすべてトラッシュ
    する。きぜつしたのは 1 匹なので、サイドは 1 枚（重なったカードの数では増えない。p.323）。ログの ``pokemon`` は
    いちばん上のカード、``evolution_stack`` は下のカード（進化していれば。下から順）。
    ``timing``: ポケモンチェックの中のきぜつなら ``"pokemon_check"``（ログに書く。v0.3a）。ワザのあとは None。
    ``counted``: きぜつしたポケモンとしてカウントされるか（v0.47。偽ならなにかの化石・ピッピ人形の「「きぜつ」しても「きぜつ」とカウントされない」。トラッシュは
    同じで、相手はサイドを取らない。ログに ``counted`` が False と書く。真なら書かない（v0.46 までと同じ形））。サイドを取るプレイヤーを決めるのは呼ぶ側。
    """
    p = state.players[owner]
    if p.active is pokemon:
        p.active = None
    else:
        p.bench.remove(pokemon)
    # 進化していれば、重なっているポケモンのカードもすべてトラッシュする（p.313・p.319・p.323。v0.4a）。サイドは 1 匹ぶん
    # v0.59: ``to_energy`` なら、いちばん上のカードはトラッシュしない（マルマインの［エネエネ］。呼ぶ側がすぐにエネルギーとしてつける。``effects.attach_converted_energy``）
    p.discard.extend(uid for uid in pokemon.cards() if not (to_energy and uid == pokemon.card))
    p.discard.extend(pokemon.energy)
    # ついていたトレーナーカードもいっしょにトラッシュする（「それについていたすべてのカード」p.323。v0.2c）
    extra = {}
    if pokemon.evolution_stack:
        extra["evolution_stack"] = pokemon.evolution_stack  # v0.4a: いちばん上のカード（pokemon）の下にあったカード
    if pokemon.disguise is not None:
        extra["disguise"] = pokemon.disguise  # v0.49: 「ばける」でのせていた進化カード（いっしょにトラッシュする）
    if pokemon.trainers:
        for attached in pokemon.trainers:
            state.players[attached.player].discard.append(attached.card)
        extra["discarded_trainers"] = tuple(t.card for t in pokemon.trainers)
    if simultaneous:
        extra["simultaneous"] = True  # v0.2f: 同じワザでほかのポケモンもきぜつした（p.324）
    if timing is not None:
        extra["timing"] = timing  # v0.3a: ポケモンチェック（どく）できぜつした。v0.42: 特殊能力の処理のあと（ゲンガーの「のろい」）は "power"
    if not counted:
        extra["counted"] = False  # v0.47: なにかの化石・ピッピ人形（進化カードがのっていない）。相手はサイドを取らない
    if to_energy:
        extra["to_energy"] = pokemon.card  # v0.59: トラッシュしないで、エネルギーとしてつけるカード（［エネエネ］）
    state.add_event("knock_out", player=owner, pokemon=pokemon.card, discarded_energy=tuple(pokemon.energy), **extra)
    # 場をはなれたので、ワザによる持続する効果も消える（p.322。v0.4b）。カードではないので、トラッシュには何も置かない
    remove_persistent_effects(state, owner, pokemon, KNOCK_OUT)

