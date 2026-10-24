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

import itertools
from typing import TYPE_CHECKING

from . import judge
from .coins import CoinSide, flip_coins
from .conditions import CONFUSION_DAMAGE, paralysis_recovery_turn, recover_from_paralysis, recover_from_sleep
from .damage import calculate_confusion_damage
from .effects import (
    DARKNESS_BONUS, DARKNESS_RECEIVED_POWER_CODE, PENALTY_DAMAGE, bench_guard_outside_attack_check, darkness_penalties, darkness_received_power_problem,
    energy_received_damage, energy_reduction_log, scram_watch, SCRAM_TIMING_CODE,
    knocked_by_hp, discard_expiring_energy, miracle_turn_end_problem,
    EXPIRE_TO_HAND,
    TypeReadingsDiffer, attack_damage_modifiers, confusion_power_modifiers, cursed_weakness_multiplier, definition_views, max_hp, poison_received_power_problem,
    same_for_type_readings, shift_duration_error, MAX_HP_DROP_CODE, state_stop_after, stadium_attack_damage_modifiers,
    pokemon_check_berries, special_energy_effect,
    DISCARD_BY_KNOCK_OUT, energy_discard_plan, return_discarded_energy,
    bench_guard_holders, char_check_targets,
)
from .errors import UnsupportedError
from .persistent import (KNOCK_OUT, USED, remove_expired_persistent_effects, remove_on_damage, remove_persistent_effects,
                         remove_turn_start_expired_persistent_effects)
from .state import OPPONENT_POWER_SUPPRESSION, POWER_SUPPRESSION, Halt, Phase
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

# v0.91: FA1（v0.89 のだましうち）の停止コード。くろこげマーカーのダメージの「「弱点・抵抗力・特殊能力・その他の効果」に関係なく」でも同じ問い
IGNORED_EFFECTS_SCOPE_CODE = "UNRESOLVED_IGNORED_EFFECTS_SCOPE"

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
    if any(record.kind in (POWER_SUPPRESSION, OPPONENT_POWER_SUPPRESSION) and record.expires_turn == state.turn_number for record in state.trainer_effects):
        trial = state.clone()
        _expire_at_turn_end(trial)
        stop = state_stop_after(state, trial)
        if stop is not None:
            code, message = stop
            halt(state, Halt(code=code, message=f"番の終わりに特殊能力を消す効果（まきちらせ!ベトベトガス・ふしぎなガス）が消えると: {message}",
                             references=("GR-2000-P323-KNOCKOUT", "CR-POWER-BACK-AFTER-RECOVERY", "docs/energy-control-power-suppression-v0.59.md")))
            return False
    miracle = miracle_turn_end_problem(state)
    if miracle is not None:
        # v0.85（MEW1）: ［きせきのかぜ］で効果の消えたミラクルエネルギーが、番の終わりに場にある（「つけた番の終わりにトラッシュする」が消えるか決まらない）。番の終わりは
        # どの操作でも来るのでコマンドを拒否せず、期限の処理の前に止める
        code, message = miracle
        halt(state, Halt(code=code, message=message, references=("docs/entry-powers-energy-lifecycle-v0.85.md",)))
        return False
    _expire_at_turn_end(state)
    return True


def _expire_at_turn_end(state: GameState) -> None:
    discard_expired_attachments(state)
    discard_expiring_energy(state)  # v0.85: ミラクルエネルギー（「つけた番の終わりにトラッシュする」）
    remove_expired_persistent_effects(state)
    for p in state.players:
        for pokemon in p.in_play():
            pokemon.retreat_failed_turn = None
            # v0.44: トレーナー「サカキ」の、今の番だけの進化の許可（説明の「今の番」「同じ番で」）
            pokemon.evolution_permission_turn = None
    # v0.31: 「エナジーバーン」で「炎」エネルギーになったエネルギーは、自分の番の終わりにもとにもどる（TXT-CHARIZARD の最新の説明）
    state.energy_burn = ()
    remove_expired_color_effects(state)  # v0.88: ［せんすい］・［エナジーコンバーター］の「この番が終わるまで」
    # v0.49: 「思い出させる」の「この番だけ」（docs/virtual-attacks-transformation-v0.49.md 6 章）。ログ ``recall`` の番で分かるので、消すログは出さない
    state.recalls = ()
    remove_expired_trainer_locks(state)  # v0.47
    remove_expired_trainer_effects(state)  # v0.56
    return_expired_set_aside(state)  # v0.63: くすぐりマシーンで置いておいたカード（「次の相手の番の終わりまで」）
    state.add_event("turn_end", player=state.current_player)


def remove_expired_color_effects(state: GameState) -> None:
    """v0.88（docs/type-energy-colors-v0.88.md 2 章）: 特殊能力で色を変える効果（``GameState.color_effects``。［せんすい］・［エナジーコンバーター］の「この番が終わるまで」）を
    この番の終わりの窓で消す（番の終わり方によらない）。1 つにつきログ ``color_effect_removed``（``reason`` は ``expired``）。勝敗が決まった番は番の終わりが来ないので残る。"""
    for record in state.color_effects:
        if record.turn != state.turn_number:
            raise RuntimeError(f"前の番の色を変える効果 {record} が残っている（番の終わりに消していない。エンジンの不具合）")
        state.add_event("color_effect_removed", player=record.player, pokemon_id=record.source, color_effect=record.kind, target=record.target,
                        color=record.color.value, reason="expired")
    state.color_effects = ()


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

    v0.91（docs/marker-check-field-reset-v0.91.md 4 章）: 1 の「指示されたこと」に、くろこげマーカーのコイン（ログ ``char_check``）と「うら」の 20 ダメージ（ログ ``char_damage``。
    弱点・抵抗力・特殊能力・その他の効果に関係なく）を加えた。両方のプレイヤーが投げるなら KK1、どのコインの結果でも 1・2 の確かめ（``_pokemon_check_plan``）で止めないことを
    コインの前に確かめる（``_char_coin_stop``）。実際の処理の順番は 悪エネルギー → くろこげマーカー → きのみ → どく。くろこげマーカーがなければ v0.90 までと同じ。
    """
    state.add_event("pokemon_check")
    order = (state.current_player, 1 - state.current_player)  # ログの順（番を終えたプレイヤーの場から）
    # v0.91（docs/marker-check-field-reset-v0.91.md 4 章）: くろこげマーカーのコイン（1 の「指示されたこと」）。どのコインの結果でも止めないことを、コインを投げる前に確かめる
    chars = char_check_targets(state, order)
    char_damages: tuple[tuple[int, int], ...] = ()
    if chars:
        stop = _char_coin_stop(state, order, chars)
        if stop is not None:
            halt(state, stop)
            return None
        char_damages = _flip_char_coins(state, chars)
    plan = _pokemon_check_plan(state, order, char_damages)
    if isinstance(plan, Halt):
        if chars:
            raise RuntimeError(f"くろこげマーカーのコインのあとに止める理由 {plan.code} が見つかった（コインの前にすべての結果を確かめた。エンジンの不具合）")
        halt(state, plan)
        return None
    poisoned_ids = plan
    penalties = darkness_penalties(state, order)
    berries = pokemon_check_berries(state, order)
    per = state.rules.damage_per_counter
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
    for pid, amount in char_damages:
        # v0.91: くろこげマーカーの「うら」の「「弱点・抵抗力・特殊能力・その他の効果」に関係なく、20ダメージ」（ワザによるダメージではない。鋼エネルギー・受けるダメージを変える
        # 特殊能力も当てはめない。ログ ``char_damage``）。「かげぶんしん」はダメージを受けたら消える（どくと同じ）
        owner, pokemon = state.find_pokemon(pid)
        pokemon.damage += amount
        state.add_event("char_damage", player=owner, pokemon=pokemon.card, pokemon_id=pid, amount=amount, total_damage=pokemon.damage)
        remove_on_damage(state, owner, pokemon, amount)
    for owner, pokemon, attached, effect in berries:
        if effect.triggers(state, pokemon):  # 悪エネルギーのあとの今の場で（読み方で結果が変わらないことは BY1 で確かめた）
            effect.consume(state, owner, pokemon, attached)
    poisoned = [state.find_pokemon(pid) for pid in poisoned_ids]  # 1 のあと（きのみで回復したあと）にどく状態のポケモン
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


def _pokemon_check_plan(state: GameState, order: tuple[int, int], char_damages: tuple[tuple[int, int], ...] = ()) -> Halt | list[int]:
    """ポケモンチェックの 1・2 を、状態の複製の上で確かめる（v0.91 に ``pokemon_check_poison`` から分けた。中身は v0.82 までと同じ）。止める理由があれば ``Halt``、なければ 1 のあとに
    どく状態のポケモンの番号（2 でダメージを受ける）。``char_damages`` は、くろこげマーカーのコインの「うら」で 1 の中でダメージを受けるポケモンの (番号, 量)。状態を変えない。"""
    # v0.81a（docs/berry-maxhp-fixes-v0.81a.md 2 章）: 1 の「指示されたこと」（悪エネルギーの効果・きのみ）を、決まらない順番の読み方ごとに状態の複製の上で処理し、
    # どの効果もそれを処理する時点の場で判断する（回復の前の場で求めた対象・止める理由を、回復のあとに使い回さない）。結果・止める理由が読み方で変わるなら BY1
    try:
        readings = _step_one_readings(state, order, char_damages)
    except UnsupportedError as error:  # v0.82: 順番を比べるきのみが上限より多い（エンジンの未対応）
        return Halt(code=error.code, message=error.message, references=("GR-2000-P323-POKEMON-CHECK", "docs/energy-discard-return-v0.82.md 2 章"))
    stop = _step_one_stop(readings)
    if stop is not None:
        return stop
    canonical = readings[0]  # 悪エネルギーが先（実際の処理の順番。どの読み方でも結果が同じことを確かめた）
    after_one = canonical.state
    poisoned_ids = [p.pokemon_id for o in order for p in after_one.players[o].in_play() if p.conditions.poison is not None]
    for pid in poisoned_ids:
        # v0.47（KA1）: 受けるダメージを変える常にはたらく特殊能力（カブトアーマー）を、どくのダメージに当てはめるかは決められない。当てはめると量が変わるなら、
        # ダメージを与える前に対戦を止める。v0.81a: 1 のあと（きのみで回復したあと。かがくへんかガスがもどるなど）の場で判断する
        owner, pokemon = after_one.find_pokemon(pid)
        problem = poison_received_power_problem(after_one, owner, pokemon, pokemon.conditions.poison.damage)
        if problem is not None:
            return Halt(code=POISON_RECEIVED_POWER.code, message=f"{problem}。{POISON_RECEIVED_POWER.message}", references=POISON_RECEIVED_POWER.references)
    if canonical.penalties or canonical.chars:  # v0.91: くろこげマーカーのダメージで 1 のあとに HP 以上になるポケモンも
        divergence = mid_check_knockout_divergence(after_one, order)
        if divergence is not None:
            return Halt(code=MID_CHECK_KNOCKOUT_CODE, message=divergence,
                        references=("GR-2000-P323-POKEMON-CHECK", "docs/darkness-metal-energy-v0.78.md 6 章", "docs/shared-checks-pokemon-reuse-v0.79.md 2 章"))
    # 1・2 の処理ごとの (のっているダメージ, 今有効な最大HP, ［ずらかる］がはたらくか) を、処理する時点の場で記録する（v0.81a: 回復で最大HP・特殊能力が変わる）
    after_two = after_one.clone()
    track = _StepTrack(canonical.track)
    for pid in poisoned_ids:
        owner, pokemon = after_two.find_pokemon(pid)
        pokemon.damage += energy_received_damage(after_two, pokemon, pokemon.conditions.poison.damage)[0]  # v0.78: 鋼エネルギー（NIP1X-010）
        track.record(after_two, order)
    for owner in order:
        for pokemon in after_two.players[owner].in_play():
            if track.passes_ten(pokemon.pokemon_id):
                # v0.78: ［ずらかる］（残りHPが「10」になった時）。1・2 の途中で「10」を通る（そのあと変わる）なら、はたらく時点が決まらない（SC1。v0.61 と同じ問い）
                return Halt(code=SCRAM_TIMING_CODE, message=f"ポケモンチェックの悪エネルギー・「どく」の途中で、ポケモン {pokemon.pokemon_id} の残りHPが「10」を通る（SC1）",
                            references=("GR-2000-P323-POKEMON-CHECK", "docs/reactive-powers-trainer-damage-v0.61.md", "docs/darkness-metal-energy-v0.78.md 5 章"))
    knocked_owners = {owner for owner in order for pokemon in after_two.players[owner].in_play() if knocked_by_hp(after_two, pokemon)}  # v0.48: 今有効な最大HP
    if len(knocked_owners) > 1:
        if not canonical.penalties and not canonical.chars:
            return POKEMON_CHECK_DOUBLE_KNOCKOUT
        what = "（v0.78: 悪エネルギーの効果を含む）" if not canonical.chars else "（v0.91: くろこげマーカーのダメージを含む）"
        return Halt(code=POKEMON_CHECK_DOUBLE_KNOCKOUT.code, message=what + POKEMON_CHECK_DOUBLE_KNOCKOUT.message,
                    references=POKEMON_CHECK_DOUBLE_KNOCKOUT.references + ("docs/darkness-metal-energy-v0.78.md 5 章",))
    return poisoned_ids


# v0.91（KK1。docs/marker-check-field-reset-v0.91.md 4 章）: 両方のプレイヤーが、自分の場のくろこげマーカーのポケモンについてコインを投げる（どちらが先に投げるか）
CHAR_COIN_ORDER_CODE = "UNRESOLVED_POKEMON_CHECK_CHAR_COIN_ORDER"
# v0.91: コインを投げる前に試す結果の組の上限（くろこげマーカーのポケモンの数。組は 2 の数乗）。多ければ試さずに止める（エンジンの未対応）
MAX_CHAR_COINS = 6
CHAR_COIN_LIMIT_CODE = "UNSUPPORTED_POKEMON_CHECK_CHAR_COINS"


def _char_coin_stop(state: GameState, order: tuple[int, int], chars: list[tuple[int, PokemonInPlay, int]]) -> Halt | None:
    """v0.91: くろこげマーカーのコインを投げる前に止める理由。

    - 両方のプレイヤーがコインを投げるなら、どちらが先に投げるかは公式ルール 2000.02.14版（p.323。ポケモンチェックはどちらの番でもないので、p.325 の番のプレイヤーが順番を決める規定は
      当てはめられない）と記録から決められず、順番で乱数の割り当てが変わる（KK1。v0.3b の両方のねむりのコインと同じ形）。1 人のプレイヤーのコインは、そのプレイヤーが場の並び
      （バトル場 → ベンチ）の順に投げる（あいだにほかのコインが入らないので、結果の分布も割り当ても変わらない。v0.60 のサンダーストームと同じ）
    - どの結果の組でも、1・2 の確かめ（``_pokemon_check_plan``。BY1・PK1・SC1・両方のきぜつ・FA1 など）で止めないこと。止める組があれば、コインの結果で止めるかが変わらないように、
      コインを投げる前に止める（ほかのコイン・状態は変えない）"""
    owners = sorted({owner for owner, _, _ in chars})
    if len(owners) > 1:
        return Halt(code=CHAR_COIN_ORDER_CODE,
                    message=("ポケモンチェックの 1 で、両方のプレイヤーが自分の場のくろこげマーカーののったポケモン（"
                             f"{[(owner, pokemon.pokemon_id) for owner, pokemon, _ in chars]}）それぞれに対してコインを投げる。どちらが先に投げるかは、公式ルール 2000.02.14版（p.323。"
                             "ポケモンチェックはどちらの番でもない。p.325 の番のプレイヤーが決める規定は当てはめられない）と記録から決められず、投げる順番で乱数の割り当てが変わるので、"
                             "コインを投げる前に対戦を止める（KK1）"),
                    references=("GR-2000-P323-POKEMON-CHECK", "GR-2000-P325-SAME-TIMING", "docs/pokemon-check-v0.3b.md", "docs/marker-check-field-reset-v0.91.md 4 章"))
    if len(chars) > MAX_CHAR_COINS:
        return Halt(code=CHAR_COIN_LIMIT_CODE,
                    message=f"ポケモンチェックのくろこげマーカーのコインが {len(chars)} 枚あり、コインの前に試す結果の組の上限（{MAX_CHAR_COINS} 枚）を超える（エンジンの未対応）",
                    references=("docs/marker-check-field-reset-v0.91.md 4 章",))
    for outcome in itertools.product((False, True), repeat=len(chars)):
        damages = tuple((pokemon.pokemon_id, amount) for (_, pokemon, amount), tails in zip(chars, outcome) if tails)
        plan = _pokemon_check_plan(state, order, damages)
        if isinstance(plan, Halt):
            sides = "・".join(f"ポケモン {pokemon.pokemon_id} が{'うら' if tails else 'おもて'}" for (_, pokemon, _), tails in zip(chars, outcome))
            return Halt(code=plan.code, message=f"くろこげマーカーのコインが（{sides}）なら: {plan.message}。コインの結果で対戦を止めるかが変わらないよう、コインを投げる前に止める",
                        references=tuple(plan.references) + ("docs/marker-check-field-reset-v0.91.md 4 章",))
    return None


def _flip_char_coins(state: GameState, chars: list[tuple[int, PokemonInPlay, int]]) -> tuple[tuple[int, int], ...]:
    """v0.91: くろこげマーカーのポケモンの持ち主が、1 匹に 1 枚ずつコインを投げる（ログ ``coin_flip`` の ``source`` は ``pokemon_check``・``effect`` は ``char``、ログ ``char_check``
    （``player``・``pokemon``・``pokemon_id``・``result``・``damaged``））。「うら」のポケモンの (番号, ダメージ) を返す（ダメージは 1 の処理で与える）。"""
    damages = []
    for owner, pokemon, amount in chars:
        flips = flip_coins(state, owner, 1, source="pokemon_check", effect="char", card=pokemon.card, pokemon_id=pokemon.pokemon_id)
        tails = flips.results[0] is CoinSide.TAILS
        state.add_event("char_check", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, result=flips.results[0].value, damaged=tails)
        if tails:
            damages.append((pokemon.pokemon_id, amount))
    return tuple(damages)


# v0.81（BY1。docs/pokemon-tools-stadiums-v0.81.md 4 章）: ポケモンチェックの 1 の「指示されたこと」の中の、悪エネルギーの効果ときのみの順番
BERRY_ORDER_CODE = "UNRESOLVED_POKEMON_CHECK_BERRY_ORDER"


class _StepTrack:
    """ポケモンチェックの 1・2 の処理ごとの、場のポケモンの (のっているダメージ, 今有効な最大HP, ［ずらかる］がはたらくか) の並び（v0.81a。処理する時点の場で記録する。
    ［ずらかる］の SC1 の確かめに使う）。"""

    def __init__(self, base: _StepTrack | None = None):
        self.seq: dict[int, list[tuple[int, int, bool]]] = {pid: list(values) for pid, values in base.seq.items()} if base else {}

    def record(self, state: GameState, order: tuple[int, int]) -> None:
        for owner in order:
            for pokemon in state.players[owner].in_play():
                if state.is_face_down(pokemon):
                    continue  # v0.67: うらのカードは HP を読まない（ダメージがのらない）
                entry = (pokemon.damage, max_hp(state, pokemon), scram_watch(state, pokemon))
                values = self.seq.setdefault(pokemon.pokemon_id, [])
                if not values or values[-1][:2] != entry[:2]:
                    values.append(entry)

    def passes_ten(self, pid: int) -> bool:
        """途中（最初と最後を除く）で残りHPが「10」になり、［ずらかる］がはたらき、そのあと変わるか。"""
        values = self.seq.get(pid, [])
        return any(hp - damage == 10 and watch and (damage, hp) != values[-1][:2] for damage, hp, watch in values[1:-1])


class _StepOneReading:
    """ポケモンチェックの 1 の「指示されたこと」の、ある順番の読み方の結果（v0.81a）。``first`` のきのみ（場のポケモンの番号）を先に、悪エネルギーの効果を次に、残りの
    きのみを最後に、状態の複製の上で処理した。``stop`` は止める理由（その読み方の処理の途中で、DE1・VS1・［ベンチガード］の未対応・受け付けられない状態になった）。

    v0.91: くろこげマーカーのダメージ（``chars``）もあれば、``blocks`` は悪エネルギーの効果（``"darkness"``）とくろこげマーカーのダメージ（``"char"``）を処理する順番、``groups`` は
    それぞれのまとまりの前・あいだ・あとに処理するきのみ（``first`` は ``groups`` の最初）。"""

    def __init__(self, first: frozenset[int], blocks: tuple[str, ...] = ("darkness",), groups: tuple[frozenset[int], ...] | None = None):
        self.first = first
        self.blocks = blocks
        self.groups = groups
        self.state: GameState | None = None
        self.stop: Halt | None = None
        self.penalties: list[tuple[int, int, int, str, int]] = []
        self.chars: list[tuple[int, int, int]] = []  # v0.91: (持ち主, 番号, 量)
        self.passed: tuple[int, ...] = ()
        self.track = _StepTrack()
        self.plans: tuple = ((), ())

    def signature(self) -> tuple:
        if self.stop is not None:
            return ("stop", self.stop.code)
        field = tuple((p.pokemon_id, p.damage, p.conditions, tuple(t.card for t in p.trainers)) for player in self.state.players for p in player.in_play())
        return ("done", field, self.passed)


def _run_berries(state: GameState, order: tuple[int, int], pids: frozenset[int]) -> None:
    """``pids`` の場のポケモンのきのみを、処理する時点の場で、はたらく条件を満たすなら処理する（状態の複製の上で。ログも複製に残る）。"""
    for owner, pokemon, attached, effect in pokemon_check_berries(state, order):
        if pokemon.pokemon_id in pids and effect.triggers(state, pokemon):
            effect.consume(state, owner, pokemon, attached)


def _run_berry_plan(state: GameState, order: tuple[int, int], plan: tuple[frozenset[int], ...], reading: _StepOneReading) -> None:
    """きのみを ``plan`` のまとまりの順に処理し、まとまりごとに受け付けられない状態を確かめる（v0.82。止める理由は ``UnsupportedError``）。"""
    for group in plan:
        before = state.clone()
        _run_berries(state, order, group)
        reading.track.record(state, order)
        found = state_stop_after(before, state)
        if found is not None:
            raise UnsupportedError(*found)


def _berry_view(state: GameState, order: tuple[int, int], skip: int) -> tuple:
    """きのみの順番に関わる、場のポケモン（``skip`` の番号を除く）の問い合わせの答え（v0.82）: 今有効な最大HP（求めると止まるならその停止コード）・今の姿・特殊能力が
    消えているか・きのみがはたらくか。状態を変えない。"""
    from .continuous import power_suppressed
    from .effects import current_form, powers_of

    triggers = {p.pokemon_id: effect.triggers(state, p) for _, p, _, effect in pokemon_check_berries(state, order)}
    view = []
    for owner in order:
        for pokemon in state.players[owner].in_play():
            if pokemon.pokemon_id == skip or state.is_face_down(pokemon):
                continue
            try:
                hp = max_hp(state, pokemon)
                form = repr(current_form(state, pokemon))
                powers = tuple(power_suppressed(state, slot.power, pokemon) for slot in powers_of(state, pokemon))
            except UnsupportedError as error:
                hp, form, powers = error.code, None, None
            view.append((pokemon.pokemon_id, hp, form, powers, triggers.get(pokemon.pokemon_id)))
    # v0.84: はたらいている［きせきのかぜ］（場の特殊エネルギーカードの効果（悪エネルギーのポケモンチェックの効果など）が消えるか。きのみで特殊状態が回復すると、はたらき始める）
    from .effects import miraculous_wind_sources

    view.append(("miraculous_wind", miraculous_wind_sources(state)))
    return tuple(view)


def _influential_berries(state: GameState, order: tuple[int, int], pids: frozenset[int]) -> list[int]:
    """``pids`` のきのみのうち、それだけを先に処理すると、ほかの場のポケモンの最大HP・姿・特殊能力・きのみがはたらくかが変わるもの（v0.82。かがくへんかガス・
    ［へんしん］のポケモンの回復など）。ほかのきのみはつけているポケモンのダメージ・特殊状態・どうぐだけを変え、ほかのポケモンの問い合わせを変えないので、たがいの順番で
    結果は変わらない。状態を変えない。"""
    found = []
    for pid in sorted(pids):
        trial = state.clone()
        before = _berry_view(trial, order, pid)
        try:
            _run_berries(trial, order, frozenset({pid}))
            after = _berry_view(trial, order, pid)
        except UnsupportedError:
            after = None
        if after != before:
            found.append(pid)
    return found


# v0.82: 順番を比べるきのみ（ほかのポケモンの問い合わせを変えるきのみ）の数の上限。並べ方は（数）! ×（数 + 1）通りなので、場に 4 つ以上あれば比べずに止める（エンジンの未対応）
MAX_INFLUENTIAL_BERRIES = 3
BERRY_ORDER_LIMIT_CODE = "UNSUPPORTED_BERRY_ORDER_LIMIT"


def _berry_plans(state: GameState, order: tuple[int, int], pids: frozenset[int]) -> list[tuple[frozenset[int], ...]]:
    """``pids`` のきのみの、比べる処理の順番（v0.82。docs/energy-discard-return-v0.82.md 2 章）。ほかのポケモンの問い合わせを変えるきのみ（``_influential_berries``）が
    なければ、まとめて 1 つ。あれば、それらのすべての並べ方と、ほかのきのみのまとまりをはさむ位置のすべて（ほかのきのみの結果は、先に処理した変えるきのみの組だけで
    決まり、どの組も並べ方の先頭の部分になる）。変えるきのみが ``MAX_INFLUENTIAL_BERRIES`` より多ければ、比べずに止める（エンジンの未対応）。"""
    from itertools import permutations

    if not pids:
        return [()]
    influential = _influential_berries(state, order, pids)
    if not influential:
        return [(pids,)]
    if len(influential) > MAX_INFLUENTIAL_BERRIES:
        raise UnsupportedError(BERRY_ORDER_LIMIT_CODE,
                               f"ポケモンチェックの 1 で、ほかのポケモンの問い合わせを変えるきのみが {len(influential)} つあり、比べる順番の上限（{MAX_INFLUENTIAL_BERRIES}）を超える（エンジンの未対応）")
    others = pids - frozenset(influential)
    plans = []
    for perm in permutations(influential):
        for cut in range(len(perm) + 1):
            groups = [frozenset({pid}) for pid in perm[:cut]] + ([others] if others else []) + [frozenset({pid}) for pid in perm[cut:]]
            plan = tuple(groups)
            if plan not in plans:
                plans.append(plan)
    return plans


def _run_penalties(state: GameState, order: tuple[int, int], reading: _StepOneReading) -> None:
    """悪エネルギーの効果を、処理する時点の場で求めて（対象・DE1・［ベンチガード］）、状態の複製の上でのせる。止める理由は ``UnsupportedError``。"""
    per = state.rules.damage_per_counter
    penalties = darkness_penalties(state, order)
    for owner, pokemon, _, kind in penalties:
        if kind != PENALTY_DAMAGE:
            continue
        problem = darkness_received_power_problem(state, pokemon, DARKNESS_BONUS)
        if problem is not None:
            raise UnsupportedError(DARKNESS_RECEIVED_POWER_CODE, problem)
        if state.players[owner].active is not pokemon:
            bench_guard_outside_attack_check(state, owner, pokemon, energy_received_damage(state, pokemon, DARKNESS_BONUS)[0])
    for owner, pokemon, uid, kind in penalties:
        amount = energy_received_damage(state, pokemon, DARKNESS_BONUS)[0] if kind == PENALTY_DAMAGE else per
        pokemon.damage += amount
        reading.penalties.append((owner, pokemon.pokemon_id, uid, kind, amount))
        reading.track.record(state, order)


def _run_char(state: GameState, order: tuple[int, int], damages: tuple[tuple[int, int], ...], reading: _StepOneReading) -> None:
    """v0.91: くろこげマーカーの「うら」のダメージを、状態の複製の上でのせる（「弱点・抵抗力・特殊能力・その他の効果」に関係なく。量は変えない）。控えのポケモンに、ほかの控えの
    ［ベンチガード］を使えるなら、だれの効果を除くか（受けるポケモン自身の効果だけか、ほかのポケモンの特殊能力も除くか）で結果が変わるので止める（FA1。v0.89 のだましうちと同じ問い。
    止める理由は ``UnsupportedError``）。"""
    for pid, amount in damages:
        found = state.find_pokemon(pid)
        if found is None:
            raise RuntimeError(f"くろこげマーカーのポケモン {pid} が、1 の途中で場にいない（1 ではポケモンは場をはなれない。エンジンの不具合）")
        owner, pokemon = found
        if state.players[owner].active is not pokemon and bench_guard_holders(state, owner, pokemon):
            raise UnsupportedError(IGNORED_EFFECTS_SCOPE_CODE,
                                   f"控えのポケモン {pid} がくろこげマーカーの {amount} ダメージを受けるとき、ほかの控えの［ベンチガード］を使える。「「弱点・抵抗力・特殊能力・"
                                   "その他の効果」に関係なく」が、受けるポケモン自身の持っている効果だけを除くのか、ほかのポケモンの特殊能力も除くのかは、印刷の文面・kyuura の記録から"
                                   "決められない（FA1）")
        pokemon.damage += amount
        reading.chars.append((owner, pid, amount))
        reading.track.record(state, order)


def _read_step_one(state: GameState, order: tuple[int, int], first: frozenset[int], first_plan: tuple[frozenset[int], ...],
                   rest_plan: tuple[frozenset[int], ...]) -> _StepOneReading:
    reading = _StepOneReading(first)
    reading.plans = (first_plan, rest_plan)
    trial = state.clone()
    reading.track.record(trial, order)
    stage = "berry"
    try:
        _run_berry_plan(trial, order, first_plan, reading)
        stage = "darkness"
        _run_penalties(trial, order, reading)
        stage = "berry"
        after_darkness = trial.clone()
        _run_berry_plan(trial, order, rest_plan, reading)
        # 悪エネルギーのあとに HP 以上になり、そのあとのきのみで HP より小さくなる（1 の途中のきぜつの判定の時点で結果が変わる）ポケモン
        reading.passed = tuple(sorted(p.pokemon_id for player in trial.players for p in player.in_play()
                                      if not knocked_by_hp(trial, p) and after_darkness.find_pokemon(p.pokemon_id) is not None
                                      and knocked_by_hp(after_darkness, after_darkness.find_pokemon(p.pokemon_id)[1])))
    except UnsupportedError as error:
        if stage == "darkness":
            reading.stop = Halt(code=error.code, message=f"ポケモンチェックの悪エネルギーで: {error.message}",
                                references=("GR-2000-P323-POKEMON-CHECK", "docs/darkness-metal-energy-v0.78.md 5 章"))
        else:
            reading.stop = Halt(code=error.code, message=f"ポケモンチェックの 1 のきのみ（どうぐ）で回復すると: {error.message}",
                                references=("GR-2000-P323-POKEMON-CHECK", "GR-2000-P323-KNOCKOUT", "docs/berry-maxhp-fixes-v0.81a.md 2 章",
                                            "docs/energy-discard-return-v0.82.md 2 章"))
        return reading
    reading.state = trial
    return reading


def _read_step_one_blocks(state: GameState, order: tuple[int, int], blocks: tuple[str, ...], groups: tuple[frozenset[int], ...],
                          plans: tuple[tuple[frozenset[int], ...], ...], char_damages: tuple[tuple[int, int], ...]) -> _StepOneReading:
    """v0.91: くろこげマーカーのダメージのある 1 の読み方。``groups[i]`` のきのみ（``plans[i]`` の順番）を ``blocks[i]`` の前に、最後の ``groups`` を最後に処理する。途中のまとまり
    （悪エネルギー・くろこげマーカー）のあとに HP 以上で、最後に HP より小さくなるポケモンを ``passed`` に入れる（1 の途中のきぜつの判定の時点で結果が変わる）。"""
    reading = _StepOneReading(groups[0], blocks, groups)
    reading.plans = plans
    trial = state.clone()
    reading.track.record(trial, order)
    stage = "berry"
    snapshots = []
    try:
        for index, block in enumerate(blocks):
            stage = "berry"
            _run_berry_plan(trial, order, plans[index], reading)
            stage = block
            if block == "darkness":
                _run_penalties(trial, order, reading)
            else:
                _run_char(trial, order, char_damages, reading)
            snapshots.append(trial.clone())
        stage = "berry"
        _run_berry_plan(trial, order, plans[-1], reading)
        reading.passed = tuple(sorted(p.pokemon_id for player in trial.players for p in player.in_play()
                                      if not knocked_by_hp(trial, p) and any(snap.find_pokemon(p.pokemon_id) is not None
                                                                             and knocked_by_hp(snap, snap.find_pokemon(p.pokemon_id)[1]) for snap in snapshots)))
    except UnsupportedError as error:
        if stage == "darkness":
            reading.stop = Halt(code=error.code, message=f"ポケモンチェックの悪エネルギーで: {error.message}",
                                references=("GR-2000-P323-POKEMON-CHECK", "docs/darkness-metal-energy-v0.78.md 5 章"))
        elif stage == "char":
            reading.stop = Halt(code=error.code, message=f"ポケモンチェックのくろこげマーカーで: {error.message}",
                                references=("GR-2000-P323-POKEMON-CHECK", "docs/marker-check-field-reset-v0.91.md 4 章"))
        else:
            reading.stop = Halt(code=error.code, message=f"ポケモンチェックの 1 のきのみ（どうぐ）で回復すると: {error.message}",
                                references=("GR-2000-P323-POKEMON-CHECK", "GR-2000-P323-KNOCKOUT", "docs/berry-maxhp-fixes-v0.81a.md 2 章",
                                            "docs/energy-discard-return-v0.82.md 2 章"))
        return reading
    reading.state = trial
    return reading


def _char_step_one_readings(state: GameState, order: tuple[int, int], everyone: frozenset[int], has_darkness: bool,
                            char_damages: tuple[tuple[int, int], ...]) -> list[_StepOneReading]:
    """v0.91: くろこげマーカーのダメージのある 1 の読み方。悪エネルギーの効果もあれば、2 つのまとまりの順番（悪エネルギーが先・くろこげマーカーが先）のどちらでも、きのみを
    それぞれのまとまりの前・あいだ・あとのどこで処理するか（きのみの数を k として 3^k 通り）と、まとまりの中のきのみの順番（``_berry_plans``）をすべて比べる。悪エネルギーの
    効果がなければ、くろこげマーカーの前・あとの 2^k 通り。最初は実際の処理の順番（悪エネルギー → くろこげマーカー → きのみ）。悪エネルギーの効果とくろこげマーカーのダメージは、
    どちらもほかの効果の対象・量を変えない（のせるダメージ・カウンターだけ）が、途中の［ずらかる］・きのみがはたらくかで変わるので比べる。"""
    block_orders = [("darkness", "char"), ("char", "darkness")] if has_darkness else [("char",)]
    ids = sorted(everyone)
    readings = []
    for blocks in block_orders:
        slots = len(blocks) + 1
        assignments = [tuple(slots - 1 for _ in ids)] + [a for a in itertools.product(range(slots), repeat=len(ids)) if a != tuple(slots - 1 for _ in ids)]
        for assignment in assignments:
            groups = tuple(frozenset(pid for pid, slot in zip(ids, assignment) if slot == index) for index in range(slots))
            for plans in itertools.product(*(_berry_plans(state, order, group) for group in groups)):
                readings.append(_read_step_one_blocks(state, order, blocks, groups, plans, char_damages))
    return readings


def _step_one_readings(state: GameState, order: tuple[int, int], char_damages: tuple[tuple[int, int], ...] = ()) -> list[_StepOneReading]:
    """ポケモンチェックの 1 の「指示されたこと」の、比べる読み方（v0.81a。docs/berry-maxhp-fixes-v0.81a.md 2 章）。最初は悪エネルギーが先（実際の処理の順番）。

    悪エネルギーの効果どうしは、のせるダメージ・カウンターがほかの悪エネルギーの効果の対象・量を変えないので、まとめて処理する。悪エネルギーの効果は、
    きのみの回復（特殊状態がなくなる → かがくへんかガス・［へんしん］がもどる）で対象・量・止める理由が変わり、きのみはつけているポケモンの悪エネルギーのダメージで
    はたらくかが変わるので、場に悪エネルギーの効果があるときは、悪エネルギーより先に処理するきのみの組をすべて比べる（きのみの数を k として 2^k 通り。場のポケモンの
    数までなので有限）。

    v0.82（docs/energy-discard-return-v0.82.md 2 章）: きのみどうしも、回復でかがくへんかガス・［へんしん］がもどって、ほかのポケモンの最大HP・特殊能力・きのみが
    はたらくかが変わるなら、順番で結果（受け付けられない状態になるか）が変わる。そのようなきのみ（``_influential_berries``）があれば、まとまりの中の順番を
    ``_berry_plans`` のとおり比べる（v0.81a はまとめた前後だけを確かめていた）。状態を変えない。"""
    everyone = frozenset(p.pokemon_id for _, p, _, _ in pokemon_check_berries(state, order))
    has_darkness = any(state.card_def(uid).is_special_energy and special_energy_effect(state, uid).pokemon_check_penalty
                       for o in order for p in state.players[o].in_play() for uid in p.energy)
    if char_damages:
        return _char_step_one_readings(state, order, everyone, has_darkness, char_damages)  # v0.91
    subsets = [frozenset()]
    if everyone and has_darkness:
        ids = sorted(everyone)
        subsets += [frozenset(pid for bit, pid in enumerate(ids) if mask >> bit & 1) for mask in range(1, 1 << len(ids))]
    readings = []
    for first in subsets:
        for first_plan in _berry_plans(state, order, first):
            for rest_plan in _berry_plans(state, order, everyone - first):
                readings.append(_read_step_one(state, order, first, first_plan, rest_plan))
    return readings


def _step_one_stop(readings: list[_StepOneReading]) -> Halt | None:
    """読み方の結果から止める理由（v0.81a）: 読み方で結果（のっているダメージ・特殊状態・残るきのみ・止める理由）が変わる、または途中で HP 以上になってから最後に HP より
    小さくなるなら BY1。どの読み方も同じ理由で止まるなら、その理由（DE1・MH1 など）。"""
    signatures = {reading.signature() for reading in readings}
    passed = [reading for reading in readings if reading.stop is None and reading.passed]
    if len(signatures) == 1 and not passed:
        return readings[0].stop
    detail = "・".join(
        (f"きのみ {sorted(r.first) or 'なし'} を先" if r.groups is None else f"順番 {list(r.blocks)}・きのみ {[sorted(g) for g in r.groups]}")
        + (f"（順番 {[sorted(g) for plan in r.plans for g in plan]}）" if len(readings) > 1 else "") + ": " + (f"止まる（{r.stop.code}）" if r.stop is not None else
                                                    f"ダメージ {[(p.pokemon_id, p.damage) for pl in r.state.players for p in pl.in_play()]}"
                                                    + (f"・途中で HP 以上 {list(r.passed)}" if r.passed else ""))
        for r in readings)
    return Halt(code=BERRY_ORDER_CODE,
                message=(f"ポケモンチェックの 1 の「指示されたこと」で、悪エネルギーの効果・きのみを処理する順番で結果が変わる（{detail}）。ポケモンチェックはどちらの番でもない"
                         "（p.323）ので、番のプレイヤーが順番を決める規定（p.325）は当てはめられず、順番は公式ルール 2000.02.14版と記録から決められないので、対戦を止める（BY1）"),
                references=("GR-2000-P323-POKEMON-CHECK", "GR-2000-P325-SAME-TIMING", "docs/pokemon-tools-stadiums-v0.81.md 4 章", "docs/berry-maxhp-fixes-v0.81a.md 2 章",
                            "docs/energy-discard-return-v0.82.md 2 章"))


# v0.79（PK1。docs/shared-checks-pokemon-reuse-v0.79.md 2 章）: ポケモンチェックの 1（悪エネルギー）でポケモンが HP 以上になったとき、1 と 2 のあいだにきぜつの判定をする
# （そのポケモンが場をはなれてから 2 の「どく」を処理する）か、2 のあとにまとめて判定するかは、公式ルール 2000.02.14版の p.323 の順番（指示されたこと → どく → ねむり →
# マヒ）と記録から決まらない。v0.78 は、どの時点でも結果が変わらない場合だけを処理するとしていたが、そのポケモンが場をはなれると 2 の処理・2 のあとのきぜつの判定の
# 問い合わせ（かがくへんかガスで消えていた特殊能力がもどる・［へんしん］の姿が変わる など）が変わる場合を確かめていなかった
MID_CHECK_KNOCKOUT_CODE = "UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT"


def _mid_check_view(state: GameState, order: tuple[int, int], keep: frozenset[int]) -> dict[int, tuple]:
    """ポケモンチェックの 2 の「どく」と 2 のあとのきぜつの判定が使う問い合わせの答え（v0.79。``keep`` の番号の場のポケモンごと）: どくのダメージ（KA1 で止めるか・
    鋼エネルギーを当てはめた量）・2 のあとに今有効な最大HP以上になるか・2 のあとに［ずらかる］の残りHP「10」になるか、と、2 のあとに HP 以上になるポケモンの特殊能力が消えているか（きぜつするときに使える
    特殊能力の機会）。答えを求めると止まる（VS1 など）なら、その停止コード。状態を変えない。"""
    from .continuous import power_suppressed
    from .effects import powers_of

    view: dict[int, tuple] = {}
    for owner in order:
        for pokemon in state.players[owner].in_play():
            if pokemon.pokemon_id not in keep:
                continue
            try:
                poison = pokemon.conditions.poison
                if poison is None:
                    received = None
                elif poison_received_power_problem(state, owner, pokemon, poison.damage) is not None:
                    received = POISON_RECEIVED_POWER.code
                else:
                    received = energy_received_damage(state, pokemon, poison.damage)[0]
                final = pokemon.damage + (received if isinstance(received, int) else 0)
                hp = max_hp(state, pokemon)
                knocked = final >= hp
                powers = tuple((str(slot.key), power_suppressed(state, slot.power, pokemon)) for slot in powers_of(state, pokemon)) if knocked else ()
                view[pokemon.pokemon_id] = (received, knocked, hp - final == 10 and scram_watch(state, pokemon), powers)
            except (UnsupportedError, TypeReadingsDiffer) as error:
                view[pokemon.pokemon_id] = ("stop", getattr(error, "code", type(error).__name__))
    return view


def mid_check_knockout_divergence(after: GameState, order: tuple[int, int]) -> str | None:
    """1 の悪エネルギーのあとに HP 以上のポケモンがいるとき、そのポケモンが 1 と 2 のあいだに場をはなれる読み方と、2 のあとまで場に残る読み方で、ほかのポケモンの 2 の処理・
    2 のあとのきぜつの判定の問い合わせ（``_mid_check_view``）が変わるなら、止める理由（PK1。v0.79）。変わらないなら None（v0.78 と同じに処理する）。

    ``after`` は 1 の結果をのせた状態の複製（悪エネルギーのダメージ・ダメージカウンター・きのみ。v0.81a から呼ぶ側が渡す）。場をはなれる読み方の複製では、HP 以上の
    ポケモンを場から除く。v0.80
    （docs/neo-trainer-components-v0.80.md 2 章）: 場をはなれる読み方では、バトル場が空いたプレイヤーが 2 の前にバトル場に出しうるポケモン（控えのどれか）を、
    出しうるすべての組で出してから比べる（出したポケモンで［へんしん］の姿・最大HP・特殊能力が変わる）。控えがいなければ空のまま。また、場をはなれる読み方で 2 の前に
    対戦が終わりうる（ポケモンがいなくなる・サイドがなくなる）のに、場に残る読み方の 2 のあとに HP 以上になるポケモンがいれば、勝ち負けが変わりうるので止める。
    カード id で分けず、場の問い合わせだけで比べる。状態を変えない。"""
    knocked = {p.pokemon_id for o in order for p in after.players[o].in_play() if p.damage >= max_hp(after, p)}
    if not knocked:
        return None
    keep = frozenset(p.pokemon_id for o in order for p in after.players[o].in_play()) - knocked
    stay = _mid_check_view(after, order, keep)
    for promoted, left in _mid_check_leave_readings(after, order, knocked):
        leave = _mid_check_view(left, order, keep)
        changed = sorted(pid for pid in keep if stay.get(pid) != leave.get(pid))
        where = f"（バトル場に出すポケモン {promoted}）" if promoted else ""
        if changed:
            return (f"ポケモンチェックの 1（悪エネルギー）でポケモン {sorted(knocked)} が HP 以上になり、1 と 2 のあいだにきぜつの判定をする（場をはなれる）かで、ポケモン {changed} の"
                    f" 2 の「どく」・きぜつの判定の問い合わせが変わる{where}（場に残る: {[stay.get(pid) for pid in changed]}、場をはなれる: {[leave.get(pid) for pid in changed]}）。"
                    "1 と 2 のあいだのきぜつの判定の時点は公式ルール 2000.02.14版（p.323）と記録から決められないので、ダメージを与える前に対戦を止める（PK1）")
        later = sorted(pid for pid in keep if isinstance(stay.get(pid), tuple) and len(stay[pid]) == 4 and stay[pid][1])
        if later and _mid_check_game_ends(after, left, order, knocked):
            return (f"ポケモンチェックの 1（悪エネルギー）でポケモン {sorted(knocked)} が HP 以上になり、1 と 2 のあいだにきぜつの判定をする（場をはなれる）と 2 の前に対戦が"
                    f"終わりうるが、2 のあとまで場に残るなら 2 のあとにポケモン {later} も HP 以上になる（勝ち負けが変わりうる）。1 と 2 のあいだのきぜつの判定の時点は公式ルール"
                    " 2000.02.14版（p.323）と記録から決められないので、ダメージを与える前に対戦を止める（PK1）")
    return None


def _mid_check_leave_readings(after: GameState, order: tuple[int, int], knocked: set[int]):
    """v0.80: 場をはなれる読み方の複製（HP 以上のポケモンを除き、バトル場が空いたプレイヤーは控えのどれかを出す）を、出しうるすべての組で返す（(出したポケモンの番号の並び,
    状態)）。控えのいないプレイヤーのバトル場は空のまま。"""
    import itertools

    choices = []
    for owner in order:
        player = after.players[owner]
        bench = [p.pokemon_id for p in player.bench if p.pokemon_id not in knocked]
        emptied = player.active is not None and player.active.pokemon_id in knocked
        choices.append([(owner, pid) for pid in bench] if emptied and bench else [None])
    for combination in itertools.product(*choices):
        left = after.clone()
        for owner in order:
            player = left.players[owner]
            if player.active is not None and player.active.pokemon_id in knocked:
                player.active = None
            player.bench = [p for p in player.bench if p.pokemon_id not in knocked]
        promoted = []
        for pick in combination:
            if pick is None:
                continue
            owner, pid = pick
            player = left.players[owner]
            player.active = next(p for p in player.bench if p.pokemon_id == pid)
            player.bench = [p for p in player.bench if p.pokemon_id != pid]
            promoted.append(pid)
        yield tuple(promoted), left


def _mid_check_game_ends(after: GameState, left: GameState, order: tuple[int, int], knocked: set[int]) -> bool:
    """v0.80: 場をはなれる読み方で、2 の前に対戦が終わりうるか（ポケモンがいなくなったプレイヤーがいる、またはきぜつで取るサイドがサイドの枚数以上になる。p.311）。"""
    from .effects import counts_as_knockout

    for owner in order:
        if not left.players[owner].in_play():
            return True
        taken = sum(1 for p in after.players[1 - owner].in_play() if p.pokemon_id in knocked and counts_as_knockout(after, p))
        if taken and taken >= len(after.players[owner].prizes):
            return True
    return False


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

    v0.90: 同じ問いで、のろいマーカーののっているポケモンの 20 ダメージに自分の弱点が当てはまる（自分のタイプが自分の弱点のタイプ）なら止める。のろいマーカーは「弱点のタイプの
    ポケモンからワザのダメージを受ける時」の効果で、こんらんの 20 が「ワザによるダメージ」かで「×2」か「×4」かが変わる。弱点が当てはまらなければ止めない（docs/markers-counters-v0.90.md 5 章）
    """
    modifiers = attack_damage_modifiers(state, pokemon, pokemon)
    if modifiers:
        return UnsupportedError(
            "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS",
            f"こんらん状態のポケモン {pokemon.pokemon_id} に、ダメージを変えるカードがついている。こんらんしたワザで自分が受ける 20 "
            "ダメージに、プラスパワー・ディフェンダーの効果を計算するか（こんらんのダメージが「ワザによるダメージ」か）は"
            "『オフィシャルブック2000』（p.257・p.309・p.321・p.322）から決められないので扱わない",
        )
    if cursed_weakness_multiplier(state, pokemon) is not None:
        try:
            weak = same_for_type_readings(state, (pokemon,), lambda views: calculate_confusion_damage(views[0], state.rules, CONFUSION_DAMAGE).weakness_applied)
        except TypeReadingsDiffer:
            weak = True  # 読み方のどれかで弱点が当てはまる（読み方の違いそのものは、下の確かめが VS1・CE1・CE2・CM1 で止める）
        if weak:
            return UnsupportedError(
                "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS",
                f"こんらん状態のポケモン {pokemon.pokemon_id} にのろいマーカーがのっていて、こんらんしたワザで自分が受ける 20 ダメージに自分の弱点が当てはまる。のろいマーカーの"
                "「弱点のタイプのポケモンからワザのダメージを受ける時、弱点の計算を「×2」ではなく、「×4」でおこなう」が、この 20 ダメージに当てはまるか（こんらんのダメージが"
                "「ワザによるダメージ」か）は、公式ルール 2000.02.14版（p.309・p.321・p.322）と kyuura の記録から決められないので扱わない（docs/markers-counters-v0.90.md 5 章）",
            )
    try:
        # v0.48: 自分のタイプ（色）と自分の弱点・抵抗力（今有効な値。``effects.definition_views``）。［へんしょく］で変えた色の読み方（VS1）で 20 ダメージの計算が
        # 変わるなら、コインを投げる前に止める（こんらん状態のモルフォンでは［へんしょく］の力が消えているので、変えた色が続くかが決まらない）
        same_for_type_readings(state, (pokemon,), lambda views: calculate_confusion_damage(views[0], state.rules, CONFUSION_DAMAGE))
    except TypeReadingsDiffer:
        return shift_duration_error(pokemon, "こんらんしたワザで自分が受ける 20 ダメージの弱点・抵抗力の計算", state=state)
    try:
        # v0.81: 場のスタジアムの、ワザのダメージの変更効果（マダツボミのとう。「無色」ポケモンの使ったワザ）。こんらんの 20 が「ワザによるダメージ」かは決まらない
        # （プラスパワー・ディフェンダーと同じ問い）ので、当てはまりうるならコインの前に止める
        towered = same_for_type_readings(state, (pokemon,), lambda views: bool(stadium_attack_damage_modifiers(state, views[0])))
    except TypeReadingsDiffer:
        return shift_duration_error(pokemon, "こんらんしたワザで自分が受ける 20 ダメージに、スタジアムの効果（「無色」ポケモンの使ったワザ）を当てはめるか", state=state)
    if towered:
        return UnsupportedError(
            "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS",
            f"こんらん状態のポケモン {pokemon.pokemon_id} のワザがこんらんしたとき、場のスタジアムが「無色」ポケモンの使ったワザのダメージを変える。こんらんしたワザで自分が受ける"
            " 20 ダメージが、そのスタジアムの書く「ワザが、ポケモンにダメージを与えるとき」のダメージか（こんらんのダメージが「ワザによるダメージ」か）は、公式ルール"
            " 2000.02.14版（p.309・p.321・p.322）と kyuura の記録から決められないので扱わない（docs/pokemon-tools-stadiums-v0.81.md 6 章）",
        )
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
    returns = energy_discard_plan(state, pokemon, pokemon.energy, cause=DISCARD_BY_KNOCK_OUT)  # v0.82: リサイクルエネルギー（場をはなれる前の場で決める）
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
    return_discarded_energy(state, returns)  # v0.82: トラッシュに置いたあと（ログ knock_out のあと）

