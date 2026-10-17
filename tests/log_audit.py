"""ログと状態の整合・書き出しの形式の監査（v0.4e。docs/integration-audit-v0.4e.md 8 章・9 章）。テスト・ツールから使う道具。

ファイル名が ``test_`` で始まらないので、``python3 -m unittest`` はこのファイルを読み込まない（テストはしない）。

- ``log_problems(state)``: ``new_game`` から進めた対戦のログ（内部の完全な記録）だけから、場のポケモンのダメージ・ついている
  エネルギー・トラッシュ・サイドの枚数を組み立て直し、状態と同じかを確かめる。番の進行（番の始まりが 1 つずつ交互・番と番の
  あいだに番の終わりとポケモンチェックが 1 回ずつ）・ワザ 1 回あたりの要素の数（同じポケモンへのダメージの要素は 1 回）・
  サイドとカードの重複・持続する効果の付与と解除の対応・進化の番も確かめる。v0.5 から、特殊能力（エナジートランス）の
  エネルギーの移動（``move_energy``。直前に同じポケモンの宣言 ``pokemon_power`` が 1 つ）も組み立て直しに含める。v0.6 から、
  手札（引いた・取ったサイド → 場に出した・つけた・使った）と、特殊能力（あまごい）で手札からつけたエネルギー
  （``power_attach_energy``。直前に同じポケモンの宣言が 1 つ。手札にあった自分のカードを自分の場のポケモンへ）も組み立て直し、
  手札からつける通常の操作（``attach_energy``）が 1 番に 1 回までで、特殊能力でつけたあと（通常の操作をまだしていない番）に
  ないこと（R13 はエンジンが止める）も確かめる。宣言（``pokemon_power``）のすぐあとには、その処理（``move_energy``・
  ``power_attach_energy``・``move_damage_counter``）が 1 つある（v0.5〜v0.7 の特殊能力は決定を出さず、1 回の宣言で 1 回処理する。
  p.311）。v0.7 から、特殊能力（ダメージスワップ）のダメージカウンターの移動（``move_damage_counter``。移動元から 1 個へり、
  移動先に 1 個ふえる。自分の場のポケモンのあいだだけ・移動元と移動先が別・移動元にカウンターがあった・移動先がきぜつしない・
  登録された実装がダメージカウンターを移す特殊能力）と、ワザ（じこさいせい）のエネルギーのトラッシュ（``discard_energy``）・
  ダメージカウンターをすべてとりのぞく処理（``remove_all_damage_counters``）も組み立て直しに含める。v0.8 から、場のポケモンの
  ねむり・マヒ・こんらん（``special_condition``・``special_conditions_removed``・きぜつ）も組み立て直し、特殊能力の宣言
  （``pokemon_power``）のたびに、その時点の場（いちばん上のカード・特殊状態）から、はたらいている「かがくへんかガス」
  （``SuppressOtherPowers``）を求めて、消されている特殊能力・宣言しない特殊能力の宣言がないことを確かめる（最後の状態だけから過去の
  使用を決めない）。v0.9 から、ワザを受けるときに自動的にはたらく特殊能力（ゴーストの「とうめい」。``AttackImmunityOnHeads``）の
  ログ（``evade_check``・``attack_evaded``）を、その時点の場（いちばん上のカード・ねむり・マヒ・こんらん・かがくへんかガス）と比べる:
  はたらいている「とうめい」を持つポケモンがワザのダメージ（0 より大きい）・効果（特殊状態・入れ替え）を受ける前に判定がある・
  判定はワザ 1 回につき 1 匹 1 回（T4）・直前にゴースト側のプレイヤーの ``source: "power"`` のコインがあり結果が同じ（T33）・
  判定したポケモンがはたらいている「とうめい」を持つ（T9〜T14）・ワザの中だけ・「おもて」なら、そのワザのダメージ・効果を受けず
  （``attack_evaded`` が続く。T5）、「うら」なら、その要素をすぐに処理する・``attack_evaded`` のダメージは 0 より大きい（T21）。
  ワザ（エナジーへんかん）でトラッシュから手札に加えたエネルギーカード（``recover_energy``）も組み立て直しに含める（v0.23 からトレーナー
  （エネルギー回収）の ``retrieve_energy`` も。基本エネルギーカード・1〜2 枚・そのトレーナーを使うためにトラッシュしたカードでないこと）。
  v0.25 から、進化（``evolve``）の名前（通常の進化）と、``trainer_card`` のある進化（ポケモン育て屋さん。使っている最中のトレーナーの効果で、
  たねポケモンに系統の合う 2 進化カードを重ねた）を確かめる。
  v0.24 から、トレーナー（ポケモン交換おじさん）の ``return_to_deck``（手札 → 山札）・``reveal_from_deck``（山札 → 手札）も手札の組み立て直しに
  含める（どちらもたねポケモン・進化カード。山札は組み立て直さないので、山札にあったかは持ち主・手札とトラッシュにないことで確かめる）。
  v0.10 から、ダメージを受けたときに自動的にはたらく特殊能力（カイリキーの「はんげき」。``CounterattackDamage``）のログ
  （``counterattack``・``counterattack_skipped``）を、その時点の場と比べる: 相手のワザのダメージ（0 より大きい）を、そのときに
  はたらいている「はんげき」を持つポケモン（いちばん上のカード・ねむり・マヒ・こんらんでない・かがくへんかガスに消されていない）が
  受けたら、そのワザの中に 1 回ある（C2・C8・C19〜C24）・それ以外のダメージ（自分のワザ・どく・こんらん・移動・はんげき）では
  ない（C3〜C6・C14）・与える相手はワザを使ったポケモン・量は登録の数（10）・そのワザのダメージのあと（あとにダメージの要素が
  ない）で、ダメージ以外の効果（特殊状態・入れ替え・回復）・きぜつの前（p.89）・ダメージの組み立て直し・与えなかったのは相手が
  すでに HP 以上のとき（C15）・「はんげき」できぜつしたポケモンへの回復がない（C16）・「はんげき」できぜつしたワザのときに、
  ほかのポケモンのきぜつがない（C18。エンジンが止めるはず）。
  v0.11 から、相手のワザによるダメージで「きぜつ」するときに使える特殊能力（サカキのカイリキーの「こんじょう」。
  ``PreventKnockOutOnHeads``）のログ（``ko_prevention_declined``・``ko_prevention_declared``・``ko_prevented``・
  ``ko_prevention_failed``）を、その時点の場と比べる: 相手のワザのダメージ（0 より大きい）を受けたときにねむり・マヒ・こんらんで
  なく（G25〜G29）、ワザのあと HP 以上で、かがくへんかガスに消されていない（G31）なら、きぜつの前に答えが 1 つある（G2・G10）・
  答えはワザのあと・持ち主・登録がこんじょう・相手のワザのダメージを受けた（G3〜G7）・答えはワザ 1 回につき 1 回まで（G14）・
  宣言のすぐあとに持ち主の ``source: "power"`` のコイン（1 枚）とその結果があり、結果がコインと同じ（G13・G17）・使わない答えの
  あとにコインがない（G11）・「おもて」なら残り HP 10（G18・G20）で、そのワザのあときぜつしない（サイドもない。G33）・「うら」・
  使わないならきぜつする（G19・G34）・ダメージの組み立て直しに ``ko_prevented`` を含める。決定の中身はログにない（v0.2a）ので、
  答えと決定の対応はエンジンの不変条件で確かめる。
  v0.30 から、ワザのエネルギーのトラッシュ（``discard_energy``）の数を、そのワザの登録した実装で確かめる: じこさいせい
  （``DiscardEnergyAndRemoveAllCounters``）はダメージカウンターをすべてとりのぞく処理と同じ数、エネルギーをトラッシュしてダメージを与える
  ワザ（``DiscardEnergyThenDamage``。ひのこ・かえんほうしゃ）は、こんらんで「うら」でなければ 1 回で、そのワザのダメージの要素
  （``damage``・``damage_prevented``・「とうめい」の判定）より前・トラッシュしたのはワザを使ったポケモンについていた登録のタイプの基本
  エネルギーカード（ワザの途中の決定を待っている最後のワザだけは 0 回）。ほかのワザにはエネルギーのトラッシュがない。
  v0.31 から、v0.31 のワザ（docs/held-cards-v0.31.md）のトラッシュは、登録した実装の要素の並び（``resolution.programs.BUILDERS``）で確かめる:
  トラッシュの要素（``DiscardOwnEnergy``・自分に控えがいない／受けなかったときにトラッシュする ``MoveOwnEnergyToBench``）がなければ 0 回、
  決まった枚数の要素だけなら（こんらんの「うら」・ワザの失敗・トラッシュできなかった・効果の対象がいない・決定を待つ最後のワザでなければ）その数、
  トラッシュの要素がダメージの要素より前ならダメージの要素より前・あとならダメージの要素（``damage``・``damage_prevented``・``attack_evaded``）の
  あと、トラッシュしたのはワザを使ったポケモンについていた、要素のタイプ（None ならどのエネルギーカードでも）のエネルギーカード。相手のワザを
  自分のワザとして使ったワザ（``copy_attack``）は、そのあとを使ったワザの登録で確かめる。控えポケモンへのダメージ（``target`` が
  ``opponent_bench``）はポケモンごとに 1 回。新しいイベント（``discard_attached_energy``・``attack_heal``・``power_heal``・``recover_trainer``・
  ``attach_energy_from_discard``・``attack_attach_energy``・``discard_from_deck``・``energy_burn``・``destiny_bond``）を組み立て直しに含め、
  宣言する特殊能力のすぐあとの処理に ``energy_burn``・``power_heal`` を加え、「みちづれ」できぜつしたポケモン（``destiny_bond`` の相手）は HP 未満で
  きぜつしてよい。「とうめい」の判定のあとに続く処理に、相手のエネルギーのトラッシュ・ワザを使えなくする効果・控えへのエネルギーをつける処理を加える。
  v0.32 から、山札からベンチに出したカード（``bench_from_deck``。ワザを使ったプレイヤーの山札（手札・トラッシュにない）の、登録の名前のたねポケモン。
  場のポケモンの番号は次の番号）を場の組み立て直しに含め、``bench_from_deck``・``bench_from_deck_none`` のすぐあとに同じプレイヤーの ``shuffle``
  があること、ワザ 1 回に 1 回までであることを確かめる。``drain_heal`` のとりのぞく数（``drain_counters``）を登録の実装（半分の切り上げ・決まった数・
  与えたぶん）と照らし、実際にとりのぞいた数がのっている数までであることを確かめる。
  ログは記録で、状態の正本ではない（状態とログが食い違えば、どちらかの不具合として報告する）。
- ``serialization_problems(state)``: 形式 1〜10 の書き出しが、表せない状態では ``ValueError``（黙って落とさない）、表せる状態では
  形式 10 の書き出しから後の形式の項目を除いたものと同じになることを確かめる（v0.31 で形式 10 を加えた）。形式 11 はない。
"""

from __future__ import annotations

from collections import Counter

from kyuura_engine import state_to_dict
from kyuura_engine.cards import EnergyType
from kyuura_engine.decisions import DISCARD_ENERGY
from kyuura_engine.effects import (
    Shapeshift,
    TransformIntoDefender,
    ATTACK_ELEMENTS,
    ATTACK_CHECK_ELEMENT,
    COLORS,
    MaxHpPerAttachedEnergyCards,
    PlaceCountersOnDamagedOpponentPokemon,
    ShiftColor,
    ATTACK_LOCK_ELEMENT,
    DAMAGE_ELEMENT,
    ENERGY_ATTACH_ELEMENT,
    ENERGY_DISCARD_ELEMENT,
    FORCED_SWITCH_ELEMENT,
    REDUCED_DAMAGE_ELEMENT,
    RETREAT_LOCK_ELEMENT,
    RETURN_IN_PLAY_TO_DECK_ELEMENT,
    COUNTERS_ELEMENT,
    EVOLVE_ELEMENT,
    HEAL_ELEMENT,
    RETURN_IN_PLAY_TO_HAND_ELEMENT,
    AttachEnergyFromDeckToSelf,
    BenchBasicsFromDeckOnEntry,
    ChargeBenchEnergyToSelf,
    CoinConditionOnEitherActive,
    DamageOpponentPokemonOnEntry,
    EntryPower,
    RecoverPokemonFromDiscardOnEntry,
    SearchEvolutionCardToHand,
    # v0.47（docs/fossil-hidden-info-v0.47.md）
    ArrangeDeckTopEffect,
    DamageThenLockOpponentTrainersOnHeads,
    HalveDamageReceived,
    LockOpponentTrainersNextTurn,
    LookOpponentHandCardToDeck,
    PeekCard,
    PlayAsPokemon,
    PreventEvolution,
    RevealOpponentHand,
    SwapPrizeWithDeckTop,
    # v0.45（docs/conditional-damage-energy-v0.45.md）
    CoinOpponentDeckTopDiscardTrainerElseHand,
    DamageThenMoveOpponentEnergyToBench,
    PutOwnerBasicFromDeckOntoBenchOnHeads,
    ENERGY_MOVE_ELEMENT,
    RETALIATION_COIN_TAILS,
    # v0.44（docs/search-evolution-once-attacks-v0.44.md）
    CoinDrawOrReturnHandToDeck,
    CoinEvolveSelfFromDeck,
    CoinPutOpponentDiscardOnDeckTop,
    DamageThenReturnSelfToHandOnHeads,
    EvolutionPermissionForOwnerPokemon,
    EvolveSelfFromDeck,
    ReturnHandThenRevealBasicEnergy,
    SearchNamedTrainerOnEntry,
    SearchTrainerOnHeads,
    SpecialPoisonOnHeadsWithoutDamage,
    TakeEnergiesToSelf,
    TakeEnergyToSelf,
    ConfuseDamageSourceOnHeads,
    DiscardThenDraw,
    EvolveFromDeckOnHeads,
    HealChosenOpponentThenDraw,
    HealOwnPokemonOnHeads,
    MoveDamageCounter,
    MoveDamageCounterToSelf,
    MoveOpponentDamageCounter,
    PlaceCountersToRemainingHpOnHeads,
    ReturnOwnPokemonToHandOnHeads,
    ReturnSelfToHand,
    SwitchOpponentOnHeads,
    SwitchSelfFromBench,
    CoinsHealOwnPokemon,
    HealAllPokemonBothSides,
    MoveOwnCountersToOpponent,
    SwapCountersOnHeads,
    DamageAndSpecialPoison,
    DamageThenSpecialPoisonOnHeads,
    AttackImmunityOnHeads,
    ConvertAttachedEnergy,
    HealOnEnergyAttach,
    RemoveOwnCounterOncePerTurn,
    CounterattackDamage,
    DamageAndDrain,
    DamageAndFullDrain,
    DamageAndRemoveCounters,
    DiscardEnergyAndRemoveAllCounters,
    DiscardEnergyThenDamage,
    PreventKnockOutOnHeads,
    ReturnToHandOnKnockOut,
    SuppressOtherPowers,
    # v0.46（docs/continuous-powers-v0.46.md）
    CONTINUOUS_ACTIVE,
    CONTINUOUS_BENCH,
    AttachEnergyFromHandOnHeads,
    BonusDamageWhileConfused,
    CapDamageFromBasic,
    ContinuousPower,
    HalveActiveAttackDamage,
    IncreaseOpponentActiveRetreatCost,
    PreventTrainerUse,
    ReduceOwnActiveRetreatCost,
    ShuffleHandIntoDeckThenDraw,
    SpecialConditionImmunity,
    ZeroLargeDamageReceived,
)
from kyuura_engine.damage import ADD, HALVE_DOWN, HALVE_UP, SET_IF_AT_LEAST, ZERO_IF_AT_LEAST
from kyuura_engine.evolution import skipped_stage1_basic
from kyuura_engine.resolution.programs import (
    BUILDERS, Damage, DiscardOwnEnergy, MoveOwnEnergyToBench, OptionalDiscardBenchDamage, ReturnOwnEnergyToHand,
)
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import (
    RETALIATION_FIXED,
    RETALIATION_KINDS,
    RETALIATION_RECEIVED,
    RETALIATION_RECEIVED_SCALED_KIND,
    NEXT_TURN_DAMAGE_KINDS,
    CannotAttack,
    CannotAttackWhileSourceActive,
    AttackCoinCheck,
    CannotRetreat,
    CannotUseAttack,
    CannotUseOwnAttack,
    HalvedDamage,
    MaxHpSet,
    NextTurnAttackDamage,
    Phase,
    ReducedDamageToSource,
    ResistanceChange,
    WeaknessChange,
)

TERMINAL = (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED)
# v0.48: 期限のない（与えた番からはたらき、ベンチにもどる・場をはなれる・進化で消える）効果の種類。テクスチャー1・テクスチャー2・きょだいか
V048_LASTING_KINDS = (WeaknessChange.kind, ResistanceChange.kind, MaxHpSet.kind)

# v0.10: はたらいた「はんげき」より先にあってはならない、ワザのダメージ以外の効果・きぜつ・番の終わり（p.89）
COUNTER_BARRIERS = (
    "special_condition", "forced_switch", "forced_switch_skipped", "drain_heal", "drain_heal_skipped", "knock_out", "turn_end", "game_end",
    "halted", "recover_energy", "discard_energy", "remove_all_damage_counters", "persistent_effect_added", "persistent_effect_skipped",
    # v0.31: ダメージ以外の効果（エネルギーのトラッシュ・つける・回復・トレーナーの回収・山札・引く）と、ワザの失敗・効果を受けない状態
    "discard_attached_energy", "attack_heal", "recover_trainer", "attach_energy_from_discard", "attack_attach_energy", "discard_from_deck",
    "draw", "effect_prevented", "effect_skipped", "destiny_bond",
    # v0.32: 山札からベンチに出す（なかまをよぶ・ふえる）
    "bench_from_deck", "bench_from_deck_none",
    # v0.34: ワザの効果で自分のポケモンを入れ替える（テレポート）
    "switch",
    # v0.41: ダメージカウンターをのせる・取り替える・山札からエネルギーをつける
    "place_damage_counters", "swap_damage_counters", "attach_energy_from_deck", "attach_energy_from_deck_none",
    # v0.46: 特殊状態にならない（めんえき）・手札からエネルギーをつける（せいちょう）
    "special_condition_prevented", "attach_energy_from_hand",
)
# v0.10: ダメージの要素のあとのワザのコインが、ダメージ以外の効果（特殊状態）を決めるワザ（「はんげき」はそのコインより先）。でんげきの
# コインは自分へのダメージ（ダメージの要素）を決めるので含めない
EFFECT_COIN_AFTER_DAMAGE = ("poison_on_heads", "paralyze_on_heads", "confuse_on_heads",
                            # v0.41: ダメージの要素のあとのコインが、ダメージ以外の効果（回復・特殊状態・「にげる」ことができない効果・引く）だけを決めるワザ
                            "damage_then_heal_self", "damage_then_status_by_coin", "damage_then_chosen_status_on_heads",
                            "damage_then_confuse_on_any_heads", "damage_then_sleep_on_heads", "damage_then_retreat_lock_on_heads",
                            "damage_then_draw_on_heads")

# 形式ごとに加わった場のポケモンの項目（serialize.py の説明）
POKEMON_FIELDS_SINCE = {
    "pokemon_id": 2, "trainers": 4, "special_conditions": 5, "retreat_failed_turn": 6, "evolution_stack": 7, "played_turn": 7,
    "evolved_turn": 7, "persistent_effects": 8, "attacks_used_once": 11, "evolution_permission_turn": 11, "type_shift": 13, "disguise": 14,
}
TOP_FIELDS_SINCE = {
    "format_version": 2, "effects": 2, "next_pokemon_id": 2, "next_decision_id": 2, "decision": 2, "trainer_in_use": 3,
    "energy_attached_by_powers_this_turn": 9, "power_uses_this_turn": 10, "energy_burn": 10, "trainer_locks": 12, "recalls": 14,
}
LATEST_FORMAT = 14


def _project(data_latest: dict, version: int) -> dict:
    """最新の形式（9）の書き出しから、形式 ``version`` にない項目を除いたもの。"""
    data = {k: v for k, v in data_latest.items() if TOP_FIELDS_SINCE.get(k, 1) <= version}
    if "format_version" in data:
        data["format_version"] = version

    def pokemon(p):
        return None if p is None else {k: v for k, v in p.items() if POKEMON_FIELDS_SINCE.get(k, 1) <= version}

    data["players"] = [
        {**player, "active": pokemon(player["active"]), "bench": [pokemon(b) for b in player["bench"]]} for player in data_latest["players"]
    ]
    return data


def required_format(state) -> tuple[int, bool]:
    """状態を表すのに要る最小の形式と、形式 1 で表せない決定があるか。"""
    in_play = [pokemon for p in state.players for pokemon in p.in_play()]
    needed = 1
    if state.trainer_in_use is not None:
        needed = max(needed, 3)
    if any(pokemon.trainers for pokemon in in_play):
        needed = max(needed, 4)
    if any(pokemon.conditions.names() for pokemon in in_play):
        needed = max(needed, 5)
    if any(pokemon.retreat_failed_turn is not None for pokemon in in_play):
        needed = max(needed, 6)
    if any(pokemon.evolution_stack for pokemon in in_play):
        needed = max(needed, 7)
    if any(pokemon.persistent_effects for pokemon in in_play):
        needed = max(needed, 8)
    if state.energy_attached_by_powers_this_turn:
        needed = max(needed, 9)
    if state.power_uses_this_turn or state.energy_burn:
        needed = max(needed, 10)  # v0.31
    if any(pokemon.attacks_used_once or pokemon.evolution_permission_turn is not None for pokemon in in_play):
        needed = max(needed, 11)  # v0.44
    if state.trainer_locks:
        needed = max(needed, 12)  # v0.47
    if any(pokemon.type_shift is not None for pokemon in in_play):
        needed = max(needed, 13)  # v0.48: ［へんしょく］の記録
    if (state.recalls or any(len(use) != 2 for use in state.power_uses_this_turn) or any(pokemon.disguise is not None for pokemon in in_play)
            or any(getattr(e, "attack_card", None) is not None or getattr(e, "target_attack_card", None) is not None
                   for pokemon in in_play for e in pokemon.persistent_effects)):
        needed = max(needed, 14)  # v0.49: 「ばける」でのせたカード・「思い出させる」の記録・ワザを印刷したカードを持つ効果・のせたカードの特殊能力の使用の記録
    d = state.decision
    not_v0_1 = d is not None and (
        d.context_value("then") is not None or d.resume in ("attack", "knock_out", "post_knockout", "power")  # v0.42: 特殊能力の途中の決定
        or d.context_value("post_knockout") is not None
    )
    return needed, not_v0_1


def serialization_problems(state) -> list[str]:
    problems = []
    needed, not_v0_1 = required_format(state)
    if max(FORMAT_VERSIONS) != LATEST_FORMAT:
        problems.append(f"形式の一覧 {FORMAT_VERSIONS} の最後が、監査の知っている形式 {LATEST_FORMAT} ではない（監査を更新する）")
    data_latest = state_to_dict(state, format_version=LATEST_FORMAT)
    for version in FORMAT_VERSIONS:
        expected = version >= needed and not (version == 1 and not_v0_1)
        try:
            data = state_to_dict(state, format_version=version)
        except ValueError:
            if expected:
                problems.append(f"形式 {version} で書き出せるはずの状態が ValueError")
            continue
        if not expected:
            problems.append(f"形式 {version} で表せない状態（要る形式 {needed}）を書き出した（黙って落とした）")
        elif data != _project(data_latest, version):
            problems.append(f"形式 {version} の書き出しが、形式 {LATEST_FORMAT} から後の項目を除いたものと違う")
    try:
        state_to_dict(state, format_version=LATEST_FORMAT + 1)
        problems.append(f"形式 {LATEST_FORMAT + 1} を書き出せた（v0.49 では形式 {LATEST_FORMAT + 1} を加えない）")
    except ValueError:
        pass
    return problems


def _effect_of_event(state, e: dict):
    """ワザの効果のログ ``e`` の ``effect``（処理したワザ。相手のワザを自分のワザとして使ったら、そのワザ）の登録の実装（v0.41）。"""
    entry = state.effects.attack_entry(*_attack_key(e["effect"]))
    return None if entry is None else entry.effect


def _same_attack(attack_window: dict | None, e: dict) -> bool:
    """ワザの効果のログ ``e`` の ``effect`` が、今のワザ（``attack_window``）か、そのワザが自分のワザとして使った相手のワザ（``copy_attack`` の ``copied``）か（v0.44）。"""
    return attack_window is not None and e.get("effect") is not None and e.get("effect") in (attack_window["effect"], attack_window.get("copied"))


def _attack_key(text: str) -> tuple[str, int]:
    """ログのワザ（``AttackKey`` の文字列 ``"カード id#位置"``）を (カード id, 位置) にする（v0.12）。"""
    card_id, _, index = text.partition("#")
    return card_id, int(index) if index.isdigit() else -1


def _attack_card_id(state, attack_event: dict) -> str:
    """ログのワザ（``attack``）を印刷したカードの id（v0.49。ワザの出どころがいちばん上のカードと違うときはログの ``card_id``。なければいちばん上のカード）。"""
    return attack_event.get("card_id") or state.in_play_def(attack_event["pokemon"]).id


def _attack_effect_of(state, attack_event: dict | None):
    """ログのワザ（``attack``）の、その対戦の登録表の実装（v0.30。v0.49 からワザを印刷したカードで引く）。"""
    if attack_event is None:
        return None
    entry = state.effects.attack_entry(_attack_card_id(state, attack_event), attack_event["attack_index"])
    return None if entry is None else entry.effect


def _v046_rank(label: str) -> int:
    """ダメージの記録の段階の名前（v0.46）: 0 = v0.45 までの効果、1 = 「リフレクター」（持続する効果 ``halved_damage``）、2 = 常にはたらく特殊能力（名前に［］）。
    計算の順番の決定がない段階では、エンジンが集めた順番（v0.45 までの効果 → リフレクター → 常にはたらく特殊能力）に並ぶ。"""
    if "［" in label:
        return 2
    if label.endswith(f"（{HalvedDamage.kind}）"):
        return 1
    return 0


def _poison_problems(state, e: dict, current: int | None) -> list[str]:
    """ログ ``special_condition``（どく）の量（v0.34）。どく状態にしたワザの登録が特殊などく（``DamageAndSpecialPoison``。v0.39 からキョウのマタドガスの
    ``DamageThenSpecialPoisonOnHeads`` も）ならその量、ほかは通常のどくの 10（p.322）。すでにどく状態なら ``already``。受けるダメージの違うどく状態から特殊などくにすることはない（v0.3a の #15。
    止めるはず）。特殊などく → 通常のどくは通常のどくになる（v0.3a の #14）。"""
    found = []
    entry = state.effects.attack_entry(*_attack_key(e["effect"]))
    effect = entry.effect if entry is not None else None
    # v0.44: キョウのコクーンの「どくどくえき」（SpecialPoisonOnHeadsWithoutDamage）
    expected = effect.poison_damage if isinstance(effect, (DamageAndSpecialPoison, DamageThenSpecialPoisonOnHeads, SpecialPoisonOnHeadsWithoutDamage)) else 10
    if e.get("damage") != expected:
        found.append(f"{e['turn']} 番のどく（ワザ {e['effect']}）の量 {e.get('damage')} が、登録の実装の量 {expected} と違う")
    if current is not None and not e.get("already"):
        found.append(f"{e['turn']} 番のどく（ポケモン {e['pokemon_id']}）の already {e.get('already')} が、ログから組み立てたどく状態 {current} と合わない")
    if current is not None and current != expected and expected != 10:
        found.append(f"{e['turn']} 番に、どくの量 {current} のポケモン {e['pokemon_id']} を、量の違う特殊などく {expected} にした（v0.3a の #15。止めるはず）")
    return found


# v0.31: ワザを使ったポケモンのエネルギーカードをトラッシュしうる要素（トラッシュの要素・自分に控えがいない／受けなかったときにトラッシュする
# エナジーボム・のぞむならトラッシュするひばしら）
DISCARDING_ELEMENTS = (DiscardOwnEnergy, MoveOwnEnergyToBench, OptionalDiscardBenchDamage)


# v0.42: 宣言する特殊能力の宣言（pokemon_power）のすぐあとに続く処理のログ（v0.41 までの move_energy・power_attach_energy・move_damage_counter・
# energy_burn・power_heal は、それぞれの分岐が宣言との対応を確かめる）
DECLARED_FOLLOWERS = ("move_energy", "power_attach_energy", "move_damage_counter", "energy_burn", "power_heal")


def _power_effect(state, key: str | None):
    """ログの特殊能力（``PowerKey`` の文字列 ``"カード id@power位置"``）の登録の実装（v0.42。なければ None）。"""
    card_id, _, index = str(key).partition("@power")
    entry = state.effects.power_entry(card_id, int(index)) if index.isdigit() else None
    return None if entry is None else entry.effect


def _follows_declaration(state, key: str, player: int, pid: int, e: dict) -> bool:
    """v0.42: 特殊能力 ``key``（プレイヤー ``player`` のポケモン ``pid`` が宣言した）の宣言のすぐあとのログ ``e`` が、その処理の最初のログか。コインを投げる
    特殊能力（ヒーリング・かおりのわな）は持ち主のそのコイン、かけつけるは自分の場の入れ替え（``switch`` の ``effect``）、ぶっしつこうかんは手札のトラッシュ
    （``discard_from_hand`` の ``power``。そのあいだに決定がある）、おくびょうはダメージカウンターをすべてとりのぞく処理（``remove_all_damage_counters`` の ``power``）。"""
    effect = _power_effect(state, key)
    kind = e["kind"]
    if isinstance(effect, (HealOwnPokemonOnHeads, SwitchOpponentOnHeads)):
        return kind == "coin_flip" and e["source"] == "power" and e.get("effect") == key and e["player"] == player and e.get("pokemon_id") == pid
    if isinstance(effect, SwitchSelfFromBench):
        return kind == "switch" and e.get("effect") == key and e["player"] == player
    if isinstance(effect, DiscardThenDraw):
        return kind == "discard_from_hand" and e.get("power") == key and e["player"] == player
    if isinstance(effect, ReturnSelfToHand):
        return kind == "remove_all_damage_counters" and e.get("power") == key and e["player"] == player and e["pokemon_id"] == pid
    # v0.43: くさいかふん・えんかくさいみんは持ち主のコイン、しんかのひかりは山札から見せて手札に加える処理（そのあいだに決定がある）、場に出たときの特殊能力は
    # こっそりかみつくの特殊能力のダメージ・つりあげるのトラッシュから手札に加える処理（加えるものがないなら recover_pokemon_none）・てしたをよぶの山札からベンチに
    # 出す処理（つける・つけかえるもの（ほのおをもらう・ようぶんきゅうしゅう・エナジーチャージ）は move_energy の分岐が確かめる）
    if isinstance(effect, CoinConditionOnEitherActive):
        return kind == "coin_flip" and e["source"] == "power" and e.get("effect") == key and e["player"] == player and e.get("pokemon_id") == pid
    if isinstance(effect, SearchEvolutionCardToHand):
        return kind == "reveal_from_deck" and e.get("power") == key and e["player"] == player
    if isinstance(effect, DamageOpponentPokemonOnEntry):
        return kind == "power_damage" and e.get("power") == key and e["player"] == player and e["pokemon_id"] == pid
    if isinstance(effect, RecoverPokemonFromDiscardOnEntry):
        return kind in ("recover_pokemon", "recover_pokemon_none") and e.get("power") == key and e["player"] == player and e["pokemon_id"] == pid
    if isinstance(effect, BenchBasicsFromDeckOnEntry):
        return kind == "bench_from_deck" and e.get("power") == key and e["player"] == player and e["pokemon_id"] == pid
    # v0.44: ［うか］は持ち主のコイン、［ボスをよぶ］は山札のサカキを手札に加える処理（search_deck の power。そのあいだに決定がある）
    if isinstance(effect, CoinEvolveSelfFromDeck):
        return kind == "coin_flip" and e["source"] == "power" and e.get("effect") == key and e["player"] == player and e.get("pokemon_id") == pid
    if isinstance(effect, SearchNamedTrainerOnEntry):
        return kind == "search_deck" and e.get("power") == key and e["player"] == player
    # v0.47: ［スパイ］は見る処理（look_at_card の power）、［わるふざけ］はサイドと山札の一番上の入れかえ（そのあいだに決定がある）
    if isinstance(effect, PeekCard):
        return kind == "look_at_card" and e.get("power") == key and e["player"] == player
    if isinstance(effect, SwapPrizeWithDeckTop):
        return kind == "swap_prize_with_deck_top" and e.get("power") == key and e["player"] == player
    # v0.48: ［へんしょく］は色を変えた記録（type_shift。そのあいだに色を選ぶ決定がある）
    if isinstance(effect, ShiftColor):
        return kind == "type_shift" and e.get("power") == key and e["player"] == player and e["pokemon_id"] == pid
    # v0.49: 「ばける」は手札の進化カードをのせた記録（disguise。そのあいだに手札の進化カードを選ぶ決定がある）
    if isinstance(effect, Shapeshift):
        return kind == "disguise" and e.get("power") == key and e["player"] == player and e["pokemon_id"] == pid
    return False


def _power_coin_follows(state, coin: dict, e: dict) -> bool:
    """特殊能力のコイン（``coin_flip`` の ``source`` が ``power``）のすぐあとのログ ``e`` が、そのコインの結果か。v0.9 の「とうめい」は判定（evade_check）、
    v0.11 の「こんじょう」は結果（ko_prevented・ko_prevention_failed）。v0.42 の「ぼうぎょかふん」は結果（power_confusion）、ヒーリング・かおりのわなは
    「おもて」なら処理（power_heal・switch。そのあいだに決定がある）、「うら」なら何もしない（そのあとに処理がない）。"""
    effect = _power_effect(state, coin.get("effect"))
    kind = e["kind"]
    if isinstance(effect, ConfuseDamageSourceOnHeads):
        return kind == "power_confusion" and e["power"] == coin["effect"] and e["result"] == coin["result"]
    if isinstance(effect, HealOwnPokemonOnHeads):
        return (kind == "power_heal" and e.get("power") == coin["effect"]) if coin["result"] == "heads" else kind != "power_heal"
    if isinstance(effect, SwitchOpponentOnHeads):
        return (kind == "switch" and e.get("effect") == coin["effect"]) if coin["result"] == "heads" else not (
            kind == "switch" and e.get("effect") == coin["effect"])
    if isinstance(effect, CoinConditionOnEitherActive):
        # v0.43: 「おもて」なら相手の、「うら」なら自分の対戦ポケモンが、その特殊状態になる（ほかのねむり・マヒ・こんらんがあれば、それを消してから。p.322）
        side = coin["player"] if coin["result"] == "tails" else 1 - coin["player"]
        if kind == "special_conditions_removed":
            return e["player"] == side and e["reason"] == "replaced"
        # v0.46: その対戦ポケモンが［めんえき］で特殊状態にならない（special_condition_prevented。置きかえる前に防ぐ）
        return kind in ("special_condition", "special_condition_prevented") and e.get("effect") == coin["effect"] and e["player"] == side \
            and e["condition"] == effect.condition
    if isinstance(effect, CoinEvolveSelfFromDeck):
        # v0.44: ［うか］。「おもて」なら山札のカードを重ねる（evolve。そのあいだに決定がある）か、重ねられるカードがない（evolve_from_deck_none）。「うら」なら何もしない
        mine = kind in ("evolve", "evolve_from_deck_none") and e.get("power") == coin["effect"] and e["pokemon_id"] == coin.get("pokemon_id")
        return mine if coin["result"] == "heads" else not (kind in ("evolve", "evolve_from_deck_none") and e.get("power") == coin["effect"])
    return kind in ("evade_check", "ko_prevented", "ko_prevention_failed")


def _returns_without_shuffle(state, effect: str) -> bool:
    """v0.38: ワザ ``effect``（ログの ``AttackKey`` の文字列）の要素の並びの、自分を山札にもどす要素が、もどしたあとに山札を切らない（あとの要素が
    山札をさがしてから切る。キョウのポッポの「でんれい」）か。"""
    card_id, _, index = effect.partition("#")
    entry = state.effects.attack_entry(card_id, int(index)) if index.isdigit() else None
    return any(type(element).__name__ == "ReturnSelfToDeck" and not element.shuffle for element in _program_of(None if entry is None else entry.effect))


def _benches_any_from_deck(state, effect: str) -> bool:
    """v0.40: ワザ ``effect`` の要素の並びに、山札から好きなだけベンチに出す要素（キョウのズバットの「むれでおそう」。``BenchFromDeckAny``）があるか。そのワザの
    ``bench_from_deck`` は 1 回のワザに何回もあり、出したあと 1 回だけ山札を切る。"""
    card_id, _, index = str(effect).partition("#")
    entry = state.effects.attack_entry(card_id, int(index)) if index.isdigit() else None
    return any(type(element).__name__ == "BenchFromDeckAny" for element in _program_of(None if entry is None else entry.effect))


def _damage_element_limits(effect) -> tuple[int, int]:
    """v0.40: 登録した実装の要素の並びの、相手の対戦ポケモン・自分へのダメージの要素の数（1 回のワザで同じポケモンが受けるダメージの要素の上限。わるいマタドガスの
    「みんなでばくはつ」は相手の対戦ポケモンに 2 つ）。並びのない実装は 1 つずつ。"""
    program = _program_of(effect)
    opponent = sum(1 for element in program if isinstance(element, Damage) and element.target == "opponent_active")
    own = sum(1 for element in program if isinstance(element, Damage) and element.target == "self")
    return max(opponent, 1), max(own, 1)


def _program_of(effect) -> tuple:
    """登録した実装の、解決の基盤の要素の並び（v0.31。対応表にない実装は空）。"""
    builder = None if effect is None else BUILDERS.get(type(effect))
    return () if builder is None else tuple(builder(effect))


def _is_discarding(element) -> bool:
    """ワザを使ったポケモンのエネルギーカードをトラッシュしうる要素か（v0.31）。v0.42 のエネループ（``ReturnOwnEnergyToHand``。トラッシュの要素と同じ選び方で、
    行き先が手札。ログ ``return_energy_to_hand``）はトラッシュしない。"""
    return isinstance(element, DISCARDING_ELEMENTS) and not isinstance(element, ReturnOwnEnergyToHand)


def _discard_elements(program) -> list:
    """要素の並びのうち、ワザを使ったポケモンのエネルギーカードをトラッシュしうる要素（v0.31）。"""
    return [element for element in program if _is_discarding(element)]


def _discard_position(program) -> str | None:
    """トラッシュの要素が、相手へのダメージの要素より前（``"before"``）か、あと（``"after"``）か（v0.31。どちらもなければ None）。"""
    discards = [i for i, element in enumerate(program) if _is_discarding(element)]
    damages = [i for i, element in enumerate(program) if isinstance(element, Damage) and element.target != "self"]
    if not discards or not damages:
        return None
    return "before" if discards[0] < damages[0] else "after"


def _discard_energy_window_problems(state, effect, window: Counter, *, log_ended: bool) -> list[str]:
    """ワザ 1 回のエネルギーのトラッシュ（``discard_energy``）の数が、登録した実装と合うか（v0.30。v0.31 から要素の並びで確かめる）。"""
    discarded = window["discard_energy"]
    if isinstance(effect, DiscardEnergyAndRemoveAllCounters):
        if discarded != window["remove_all_damage_counters"]:
            return ["1 回のワザで、エネルギーのトラッシュとダメージカウンターをすべてとりのぞく処理の数が違う（じこさいせい）"]
        return []
    if isinstance(effect, DiscardEnergyThenDamage):
        if window["confusion_damage"]:
            expected = {0}  # こんらんで「うら」なら、もとのワザの要素はない（p.309 の手順 5）
        elif log_ended and state.decision is not None and state.decision.kind == DISCARD_ENERGY:
            expected = {0}  # トラッシュするカードを選ぶ決定を待っている（最後のワザ）
        else:
            expected = {1}
        if discarded not in expected:
            return [f"1 回のワザ（{effect.implementation_id}）で、エネルギーのトラッシュが {discarded} 回（{sorted(expected)} のはず）"]
        return []
    elements = _discard_elements(_program_of(effect))
    if not elements:
        if discarded:
            return [f"エネルギーをトラッシュしないワザ（{type(effect).__name__}）で、エネルギーのトラッシュが {discarded} 回"]
        return []
    exact = [element for element in elements if isinstance(element, DiscardOwnEnergy) and isinstance(element.count, int) and element.gate is None
             and element.local_coin is None and element.heads_of is None and not element.any_number]
    interrupted = (window["confusion_damage"] or window["attack_failed"] or window["discard_energy_failed"] or window["effect_skipped"]
                   or (log_ended and state.decision is not None and state.decision.resume == "attack"))
    if len(exact) == len(elements) and not interrupted and discarded != sum(element.count for element in exact):
        return [f"1 回のワザ（{type(effect).__name__}）で、エネルギーのトラッシュが {discarded} 回（{sum(e.count for e in exact)} のはず）"]
    return []


def log_problems(state) -> list[str]:
    """``new_game`` から進めた対戦のログと状態の整合の問題（なければ空）。"""
    log = [dict(e) for e in state.log]
    problems: list[str] = []

    # 1. 番は増えていき、番の始まりは 1 つずつ交互（p.309）
    turns = [e["turn"] for e in log]
    if turns != sorted(turns):
        problems.append("ログの番が増えていく順になっていない")
    starts = [e for e in log if e["kind"] == "turn_start"]
    janken = next((e for e in log if e["kind"] == "janken"), None)
    for index, event in enumerate(starts):
        expected_player = None if janken is None else (janken["first_player"] + index) % 2
        if event["turn"] != index + 1 or event["player"] != expected_player:
            problems.append(f"{index + 1} 回目の番の始まりが {event['turn']} 番・プレイヤー {event['player']}")
            break

    # 2. 番ごと: 番と番のあいだに turn_end → pokemon_check が 1 回ずつ。ワザ・ワザを使わずに終える は合わせて 1 回まで
    per_turn: dict[int, list[str]] = {}
    for e in log:
        per_turn.setdefault(e["turn"], []).append(e["kind"])
    last_turn = starts[-1]["turn"] if starts else 0
    for turn, kinds in per_turn.items():
        if turn == 0:
            continue
        marks = [k for k in kinds if k in ("turn_end", "pokemon_check")]
        if turn < last_turn and marks != ["turn_end", "pokemon_check"]:
            problems.append(f"{turn} 番の番の終わり・ポケモンチェックが {marks}")
        if turn == last_turn and marks not in ([], ["turn_end", "pokemon_check"]):
            problems.append(f"最後の {turn} 番の番の終わり・ポケモンチェックが {marks}")
        if kinds.count("attack") + kinds.count("end_turn_without_attack") > 1:
            problems.append(f"{turn} 番にワザ・番を終える操作が {kinds.count('attack') + kinds.count('end_turn_without_attack')} 回")

    # 3. ワザ 1 回の要素: 同じポケモンへのダメージの要素は 1 回（相手の対戦ポケモン・自分）。こんらんしたらワザの要素はない
    window = None
    attack_event: dict | None = None
    window_effect = None  # v0.31: 今のワザの登録の実装（相手のワザを自分のワザとして使ったら、そのワザの実装）
    for e in log + [{"kind": "turn_end", "turn": None}]:
        kind = e["kind"]
        if kind == "attack":
            window = Counter()
            attack_event = e
            window_effect = _attack_effect_of(state, e)
            continue
        if window is None:
            continue
        if kind in ("turn_end", "game_end", "halted"):
            problems.extend(_discard_energy_window_problems(state, window_effect, window, log_ended=e["turn"] is None))
            opponent_limit, own_limit = _damage_element_limits(window_effect)  # v0.40: みんなでばくはつは相手の対戦ポケモンに 2 つ
            if window["damage:opponent"] + window["prevented:opponent_active"] > opponent_limit or window["damage:self"] + window["prevented:self"] > own_limit:
                problems.append(f"1 回のワザで同じポケモンへのダメージの要素が、登録の要素の数より多い {dict(window)}")
            if any(count > 1 for key, count in window.items() if key.startswith("damage:bench:") or key.startswith("prevented:bench:")):
                problems.append(f"1 回のワザで同じ控えポケモンへのダメージの要素が 2 回以上 {dict(window)}")
            if window["confusion_damage"] and (window["damage:opponent"] or window["damage:self"] or window["prevented:opponent_active"]):
                problems.append("こんらんしたワザに、もとのワザのダメージの要素がある")
            if window["attack_failed:attack_check"] and (window["confusion_check"] or window["damage:opponent"] or window["damage:self"]
                                                          or window["prevented:opponent_active"] or window["persistent_effect_added"]
                                                          or window["special_condition"] or window["evade_check"]):
                problems.append(f"手順 4 のコインで失敗したワザに、こんらんのコイン・ワザの要素がある {dict(window)}")  # v0.36
            for once in ("forced_switch", "drain_heal", "confusion_check", "confusion_damage", "persistent_effect_added",
                         "remove_all_damage_counters", "recover_energy", "drain_heal_skipped",
                         # v0.31
                         "copy_attack", "attack_failed", "recover_trainer", "attach_energy_from_discard", "destiny_bond",
                         # v0.36
                         "attack_check", "return_in_play_to_deck",
                         # v0.38
                         "discard_attached_cards",
                         # v0.41（v0.48 のダメージぞうふくは、相手の場のポケモンごとに 1 回。下で確かめる）
                         *(() if isinstance(window_effect, PlaceCountersOnDamagedOpponentPokemon) else ("place_damage_counters",)), "swap_damage_counters",
                         # v0.42
                         "return_energy_to_hand", "evolve", "evolve_from_deck_none", "switch_declined", "power_confusion",
                         "power_confusion_skipped",
                         # v0.46
                         "attach_energy_from_hand"):
                if window[once] > 1:
                    problems.append(f"1 回のワザで {once} が {window[once]} 回")
            if any(count > 1 for key, count in window.items() if key.startswith("place_damage_counters:")):
                problems.append(f"1 回のワザで同じポケモンにダメージカウンターをのせる処理が 2 回以上 {dict(window)}")  # v0.48: ダメージぞうふく
            if any(count > 1 for key, count in window.items() if key.startswith("attack_heal:")):
                # v0.31・v0.41: ワザでダメージカウンターをとりのぞくのは、ポケモンごとに 1 回（v0.41 から、複数のポケモンからとりのぞくワザがある）
                problems.append(f"1 回のワザで同じポケモンからダメージカウンターをとりのぞく処理が 2 回以上 {dict(window)}")
            if window["attack_energy_from_deck"] > 1:
                problems.append("1 回のワザで山札からエネルギーをつける処理（attach_energy_from_deck・attach_energy_from_deck_none）が 2 回以上")  # v0.41
            if isinstance(window_effect, ReturnHandThenRevealBasicEnergy):
                # v0.44: てじなは、もどした枚数と同じ枚数を 1 枚ずつ見せる（山札の基本エネルギーカードがなければ reveal_from_deck_none が 1 回。もどさなければどちらもない）
                # （決定を待ったまま対戦が終わったときは、見せる前のことがあるので 0 も許す）
                if window["hand_to_deck"] > 1 or (window["reveal_from_deck_none"] and window["reveal_from_deck"]) or window["reveal_from_deck_none"] > 1 \
                        or window["reveal_from_deck"] not in (0, window["hand_to_deck_cards"]) \
                        or (window["reveal_from_deck"] or window["reveal_from_deck_none"]) and not window["hand_to_deck"]:
                    problems.append(f"てじなで、山札にもどした枚数と見せて手札に加えた枚数・回数が合わない {dict(window)}")
            elif window["reveal_from_deck"] + window["reveal_from_deck_none"] > 1:
                problems.append("1 回のワザで山札から見せて手札に加える処理（reveal_from_deck・reveal_from_deck_none）が 2 回以上")  # v0.38
            if window["bench_from_deck"] + window["bench_from_deck_none"] > 1 and not (
                    attack_event is not None and _benches_any_from_deck(state, f"{_attack_card_id(state, attack_event)}#{attack_event['attack_index']}")
                    and not window["bench_from_deck_none"]):
                # v0.40: むれでおそうは好きなだけ出す（bench_from_deck が何回もあり、bench_from_deck_none はない）
                problems.append("1 回のワザで山札からベンチに出す処理（bench_from_deck・bench_from_deck_none）が 2 回以上")  # v0.32
            if window["forced_switch"] + window["forced_switch_skipped"] > 1:
                problems.append("1 回のワザで入れ替えの結果が 2 回以上")
            if window["counterattack"] + window["counterattack_skipped"] > 1:
                problems.append(f"1 回のワザで「はんげき」が {window['counterattack'] + window['counterattack_skipped']} 回（今の対応カードでは 1 回まで）")
            if window["drain_heal"] + window["drain_heal_skipped"] > 1:
                problems.append("1 回のワザで回復の結果が 2 回以上")
            # v0.11: 「こんじょう」を使うかの決定はワザ 1 回につき 1 回まで（今の対応カードでは、ワザのダメージを受ける相手のポケモンは 1 匹）。
            # 宣言 1 回につき結果（ko_prevented・ko_prevention_failed）が 1 回
            if window["ko_prevention_declined"] + window["ko_prevention_declared"] > 1:
                problems.append(f"1 回のワザで「こんじょう」を使うかの決定が {window['ko_prevention_declined'] + window['ko_prevention_declared']} 回（G14・G40）")
            if window["ko_prevented"] + window["ko_prevention_failed"] != window["ko_prevention_declared"]:
                problems.append("1 回のワザで「こんじょう」の宣言と結果（ko_prevented・ko_prevention_failed）の数が違う")
            # v0.12: 「ほのおのかべ」はワザ 1 回につき 1 回まで（ダメージを受ける相手のポケモンは 1 匹。W25）。そのダメージの要素も 1 回まで
            if window["retaliation"] + window["retaliation_skipped"] > 1 or window["damage:retaliation"] > window["retaliation"]:
                problems.append(f"1 回のワザで「ほのおのかべ」・「こうらがえし」が {window['retaliation'] + window['retaliation_skipped']} 回・そのダメージが {window['damage:retaliation']} 回")
            if window["post_knockout_power_declined"] + window["post_knockout_power_declared"] > 1:
                problems.append("1 回のワザのあとで「ふしちょう」を使うかの答えが 2 回以上")
            window = None
            continue
        if kind in ("pokemon_power", "move_energy", "power_attach_energy", "move_damage_counter"):
            # v0.5: ワザを使ったら番は終わる（p.309）ので、ワザのあと（番の終わりまで）に特殊能力の使用はない（v0.6 のあまごい・
            # v0.7 のダメージスワップも）
            problems.append(f"{e['turn']} 番のワザのあとに特殊能力の使用（{kind}）がある")
        if kind == "copy_attack":
            # v0.31: 相手のワザを自分のワザとして使った。このあとの要素は、そのワザの登録の実装で確かめる
            window_effect = state.effects.attack_entry(*_attack_key(e["copied"])).effect if state.effects.attack_entry(*_attack_key(e["copied"])) else None
        if kind == "discard_energy":
            # v0.30: エネルギーをトラッシュしてダメージを与えるワザは、トラッシュしてからダメージの要素を処理する（RUL-ENERGY-DISCARD-ATTACKS の
            # 最新の説明の順番）。トラッシュしたのは、ワザを使ったポケモンについていた、登録のタイプの基本エネルギーカード。v0.31 から、トラッシュの
            # 要素とダメージの要素の順番・トラッシュするタイプを、登録の要素の並びで確かめる
            effect = window_effect
            program = _program_of(effect)
            damaged = (window["damage:opponent"] + window["damage:self"] + window["prevented:opponent_active"] + window["prevented:self"]
                       + window["evade_check"])
            position = "before" if isinstance(effect, DiscardEnergyThenDamage) else _discard_position(program)
            if position == "before" and damaged:
                problems.append(f"{e['turn']} 番のワザのエネルギーのトラッシュが、そのワザのダメージの要素のあと")
            if position == "after" and not (window["damage:opponent"] + window["prevented:opponent_active"] + window["attack_evaded"]):
                problems.append(f"{e['turn']} 番のワザのエネルギーのトラッシュが、そのワザの相手へのダメージの要素より前")
            if (e["player"], e["pokemon"]) != (attack_event["player"], attack_event["pokemon"]):
                problems.append(f"{e['turn']} 番のワザのエネルギーのトラッシュが、ワザを使ったポケモンのものでない")
            elements = _discard_elements(program)
            types = {getattr(element, "energy_type", None) for element in elements} if elements else {getattr(effect, "energy_type", None)}
            definition = state.printed_def(e["energy"])
            if None in types:
                if definition.category != "energy":
                    problems.append(f"{e['turn']} 番のワザでトラッシュしたカード {e['energy']} が、エネルギーカードでない")
            elif not definition.is_basic_energy or definition.provides not in types:
                problems.append(f"{e['turn']} 番のワザでトラッシュしたカード {e['energy']} が、登録のタイプ {types} の基本エネルギーカードでない")
        if kind == "damage":
            if e.get("target") in ("opponent_bench", "self_bench"):
                window[f"damage:bench:{e['pokemon_id']}"] += 1  # v0.31: 控えポケモンへのダメージ（v0.33 から自分の控えも）
            else:
                window["damage:retaliation" if e.get("retaliation") else "damage:self" if e.get("target") == "self" else "damage:opponent"] += 1
        elif kind == "damage_prevented":
            if e["target"] in ("opponent_bench", "self_bench"):
                window[f"prevented:bench:{e['pokemon_id']}"] += 1
            else:
                window[f"prevented:{e['target']}"] += 1
        else:
            window[kind] += 1
            if kind == "attack_failed" and e.get("reason") == "attack_check":
                window["attack_failed:attack_check"] += 1  # v0.36
            if kind == "attack_heal":
                window[f"attack_heal:{e['pokemon_id']}"] += 1  # v0.41
            if kind == "place_damage_counters":
                window[f"place_damage_counters:{e['pokemon_id']}"] += 1  # v0.48
            if kind == "hand_to_deck":
                window["hand_to_deck_cards"] += len(e["cards"])  # v0.44: てじな・ラッキーたまごで山札にもどした枚数
            if kind in ("attach_energy_from_deck", "attach_energy_from_deck_none"):
                window["attack_energy_from_deck"] += 1  # v0.41

    # 4. ログからの組み立て直し: 場のポケモンの番号・ダメージ・エネルギー・トラッシュ・サイド
    ids: dict[int, int] = {}  # いちばん上のカードの uid → 場のポケモンの番号
    next_id = 1
    damage: Counter = Counter()
    energy: dict[int, list[int]] = {}
    in_play: set[int] = set()
    discard: dict[int, list[int]] = {0: [], 1: []}
    prizes_taken: Counter = Counter()
    taken_cards: list[int] = []
    knocked: Counter = Counter()
    evolve_turns: dict[int, list[int]] = {}
    permitted: set[tuple[int, int]] = set()  # v0.44: トレーナー「サカキ」の許可（場のポケモンの番号, 番）
    once_used: set[tuple[int, int, int]] = set()  # v0.44: 場に出てから 1 度しか使えないワザの記録（場のポケモンの番号, カードの uid, ワザの位置）
    added: dict[tuple, int] = {}
    removed: Counter = Counter()

    pokemon_owner: dict[int, int] = {}  # 場のポケモンの番号 → 持ち主（v0.5。エネルギーの移動は自分の場のポケモンのあいだだけ）
    top: dict[int, int] = {}  # 場のポケモンの番号 → いちばん上のカードの uid（v0.6。つける先のタイプを見る）
    turn_player: int | None = None  # 今の番のプレイヤー（最後の turn_start）
    hand: dict[int, list[int]] = {0: [], 1: []}  # 手札（v0.6。引いた・取ったサイド → 場に出した・つけた・使った）
    # v0.23: 使っている最中のトレーナーの使うための条件でトラッシュした手札（discard_from_hand から discard_trainer まで）
    trainer_discarded: dict[int, tuple[int, ...]] = {0: (), 1: ()}
    using_trainer: dict[int, int | None] = {0: None, 1: None}  # v0.25: 使っている最中のトレーナー（play_trainer から discard_trainer まで）
    attached_this_turn = 0  # この番の、手札からつける通常の操作（attach_energy）の数（v0.6）
    power_attached_this_turn = 0  # この番の、特殊能力で手札からつけた数（power_attach_energy。v0.6）
    exclusive: dict[int, str] = {}  # 場のポケモンの番号 → ねむり・マヒ・こんらんのどれか（v0.8。かがくへんかガスがはたらいているかを見る）
    poisoned: dict[int, int] = {}  # 場のポケモンの番号 → どくで受けるダメージ（v0.34。特殊などく（どくどく）は 20）
    replaced: dict[int, str] = {}  # 特殊状態が置きかわる直前の、ねむり・マヒ・こんらん（v0.9。置きかえたワザの効果を受けた時点の状態）
    attack_window: dict | None = None  # 今の番のワザ（attack から番の終わりまで。v0.9）: 使ったプレイヤー・ポケモン・ワザ・受けるかの判定
    expect: tuple | None = None  # 直前の evade_check のすぐあとに続くはずの処理（場のポケモンの番号, 要素, 受けるか。v0.9）
    previous: dict | None = None  # 1 つ前のイベント（v0.9。evade_check の直前のコイン）
    # v0.12: ログから組み立てた、今ある持続する効果（(場のポケモンの番号, 与えた番) → 種類・はたらく番・ワザ）
    alive: dict[tuple[int, int], dict] = {}
    # v0.12: 直前のきぜつで「ふしちょう」を使えた・使えなかったカード（答えを待つもの）と、その答えのあとの状態
    rebirth_pending: list[dict] = []
    rebirth_answered: dict | None = None  # 直前の答え（宣言なら、すぐあとに return_to_hand が続くはず）
    batch_answered = False  # このきぜつの処理で答えがあった（そのあとにサイド・きぜつ・対戦の終わりはないはず）
    destiny_knocked: set[int] = set()  # v0.31: 「みちづれ」できぜつする相手の対戦ポケモン（HP 未満できぜつしてよい）
    shuffle_due: dict | None = None  # v0.32: 直前の bench_from_deck・bench_from_deck_none（すぐあとに同じプレイヤーの shuffle が続くはず）
    # v0.38: 直前の、山札を切らずにもどした return_in_play_to_deck（キョウのポッポの「でんれい」。かわりの対戦ポケモンを出してから山札をさがし、その
    # すぐあとに切る。もどしたあとに切らない）
    search_due: dict | None = None
    # v0.36: p.309 の手順 4 のコイン（すなかけ・えんまくなど）。ワザの宣言（attack）のときにはたらいている効果（場のポケモンの番号, 与えた番, 1回で消えるか）が
    # あれば、宣言のすぐあとに coin_flip（source attack_check）→ attack_check が続くはず。「うら」なら、そのあと（1回で消える効果は消したログのあと）に
    # attack_failed（reason attack_check）が続き、ワザの要素はない
    check_due: tuple | None = None
    check_failed: dict | None = None
    used_due: tuple | None = None
    # v0.42: 直前の宣言の特殊能力（PowerKey の文字列）。手札をトラッシュした・相手のポケモンのカウンターをとりのぞいたあとに続くはずの引く処理
    # （プレイヤー, 枚数の上限, 番, 前のログ）。特殊能力の処理（のろい）で HP 以上になったポケモン（すぐあとに timing power のきぜつ）。
    # 「ぼうぎょかふん」の「おもて」でこんらんにする相手（すぐあとに、その特殊能力のこんらん）
    declared_key: str | None = None
    draw_due: tuple | None = None
    power_ko_due: int | None = None
    confusion_due: tuple | None = None
    # v0.43: 場に出たときの特殊能力の使う機会（(番, 場のポケモンの番号, 特殊能力の PowerKey の文字列)。進化のすぐあと（進化の手順のログのあと）に、答え（pokemon_power
    # の entry・entry_power_declined）が 1 つ続くはず）。くさいかふん・えんかくさいみんのコインのあとに置きかえたねむり・マヒ・こんらん（すぐあとにその特殊状態）。
    # 1 回の宣言で何枚もつけかえる特殊能力（ようぶんきゅうしゅう・エナジーチャージ）の今の宣言（番, プレイヤー, ポケモン, 特殊能力, つけかえた枚数）
    entry_due: tuple | None = None
    condition_due: tuple | None = None
    moving: tuple | None = None
    # v0.46: 各プレイヤーのバトル場のポケモンの番号（常にはたらく特殊能力の場所の条件を確かめる。場をはなれたら in_play にない）。
    # サイコエクスチェンジ（手札を山札にもどしたあと、切ってから引く）の引く処理（プレイヤー, 枚数の上限, 番）
    active_of: dict[int, int | None] = {0: None, 1: None}
    exchange_due: tuple | None = None
    # v0.47: ログから組み立てた、期限のあるトレーナーの使用の禁止（(禁止されたプレイヤー, 消える番) → 与えたログ）。みらいよちの見たカード（すぐあとに、その並べかえ
    # arrange_deck_top が続くはず）
    trainer_locks_log: dict[tuple[int, int], dict] = {}
    arrange_due: dict | None = None
    # v0.48: ログから組み立てた、特殊能力で色を変えた記録（場のポケモンの番号 → 色・番・使ったときのいちばん上のカード・使ってからベンチにもどったか）。
    # ログから組み立てた今の番（最後の turn_start の番）
    shifts: dict[int, dict] = {}
    current_turn = 0
    # v0.49: ログから組み立てた、「ばける」でのせたカード（場のポケモンの番号 → カードの uid）
    disguised: dict[int, int] = {}

    def power_defs(pid: int) -> list[tuple[object, int, object]]:
        """v0.49: ログから組み立てた今の場の、ポケモン ``pid`` が今持つ特殊能力（``effects.powers_of`` と同じ求め方）: [(印刷したカードの定義, 位置, 特殊能力)]。
        「ばける」でのせたカードがあれば、そのカードの特殊能力（先）といちばん上のカードの特殊能力。［へんしん］で写したカードの特殊能力は持たない（TF1）。"""
        definitions = ([state.in_play_def(disguised[pid])] if pid in disguised else []) + [state.in_play_def(top[pid])]
        return [(definition, index, power) for definition in definitions for index, power in enumerate(definition.powers)]

    def transform_target(pid: int) -> int | None:
        """v0.49: ログから組み立てた今の場で、ポケモン ``pid`` の［へんしん］がはたらいていれば、同じカードとしてあつかう相手の対戦ポケモンの番号（バトル場にいて、
        ねむり・マヒ・こんらんでなく、かがくへんかガスに消されていない。``effects.transform_defender`` と同じ求め方）。"""
        if pid not in in_play or pid in disguised or not is_active(pid) or pid in exclusive:
            return None
        definition = state.in_play_def(top[pid])
        for power in definition.powers:
            if isinstance(state.effects.power_effect(definition.id, power), TransformIntoDefender):
                if [g for _, g in working_gases() if g.suppresses(power)]:
                    return None
                target = active_of.get(1 - pokemon_owner.get(pid))
                return target if target in in_play else None  # 相手のバトル場が空いている（きぜつのあと、出す前・対戦の終わり）なら、はたらく相手がいない
        return None

    def form_def(pid: int):
        """v0.49: ログから組み立てた、ポケモン ``pid`` の今の姿のカードの定義（「ばける」でのせたカード・［へんしん］の相手の対戦ポケモンのカード・いちばん上のカード）。"""
        if pid in disguised:
            return state.in_play_def(disguised[pid])
        target = transform_target(pid)
        if target is not None and target in top:
            return state.in_play_def(top[target])
        return state.in_play_def(top[pid])

    def entry_opportunity(uid: int, *, from_hand: bool) -> str | None:
        """v0.43: カード ``uid`` を重ねた進化（手札から ``from_hand``）で、場に出たときの特殊能力を使う機会があるか（その特殊能力の PowerKey の文字列。経路が
        合わない（「手札から」の特殊能力を山札から重ねた）・ログから組み立てた今の場ではたらいている「かがくへんかガス」に消されているなら None）。"""
        definition = state.in_play_def(uid)
        for index, power in enumerate(definition.powers):
            effect = state.effects.power_effect(definition.id, power)
            if isinstance(effect, EntryPower):
                if (effect.from_hand_only and not from_hand) or [pid for pid, gas in working_gases() if gas.suppresses(power)]:
                    return None
                return f"{definition.id}@power{index}"
        return None

    def working_gases() -> list[tuple[int, SuppressOtherPowers]]:
        """ログから組み立てた今の場で、はたらいている「ほかの特殊能力を消す」特殊能力（v0.8。かがくへんかガス）。"""
        found = []
        for pid in sorted(in_play):
            for definition, _, power in power_defs(pid):  # v0.49: 今持つ特殊能力（「ばける」でのせたカードを含む）
                effect = state.effects.power_effect(definition.id, power)
                if isinstance(effect, SuppressOtherPowers) and pid not in exclusive:
                    found.append((pid, effect))
        return found

    def evasion(pid: int, *, blocked: str | None = None) -> tuple[str | None, str | None]:
        """ログから組み立てた今の場の、ポケモン ``pid`` の「とうめい」（v0.9）: (持っている特殊能力の PowerKey の文字列, はたらいて
        いない理由)。持っていなければ (None, None)。``blocked`` はその時点のねむり・マヒ・こんらん（置きかわる直前の値を渡すため）。"""
        for definition, index, power in power_defs(pid):  # v0.49
            effect = state.effects.power_effect(definition.id, power)
            if isinstance(effect, AttackImmunityOnHeads):
                key = f"{definition.id}@power{index}"
                condition = blocked if blocked is not None else exclusive.get(pid)
                if condition is not None:
                    return key, f"{condition} 状態"
                gases = [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(power)]
                if gases:
                    return key, f"かがくへんかガス（ポケモン {gases}）"
                return key, None
        return None, None

    def counter_power(pid: int) -> tuple[str | None, int | None, str | None]:
        """ログから組み立てた今の場の、ポケモン ``pid`` の「はんげき」（v0.10）・「わるいねぞう」（v0.17b）: (持っている特殊能力の PowerKey の
        文字列, 与える量, はたらいていない理由)。持っていなければ (None, None, None)。ねむり・マヒ・こんらんは、その時点（ダメージを受けるとき）
        の値で、はたらくかは実装の ``works_with`` で決める（はんげきはどれでもないとき、わるいねぞうはねむりのときだけ）。"""
        for definition, index, power in power_defs(pid):  # v0.49
            effect = state.effects.power_effect(definition.id, power)
            if isinstance(effect, CounterattackDamage):
                key = f"{definition.id}@power{index}"
                if not effect.works_with(exclusive.get(pid)):
                    return key, effect.amount, f"{exclusive.get(pid) or '特殊状態なし'}（ねむり・マヒ・こんらん）の状態"
                gases = [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(power)]
                if gases:
                    return key, effect.amount, f"かがくへんかガス（ポケモン {gases}）"
                return key, effect.amount, None
        return None, None, None

    def guts_power(pid: int) -> tuple[str | None, PreventKnockOutOnHeads | None, object | None]:
        """ログから組み立てた今の場の、ポケモン ``pid`` の「こんじょう」（v0.11）: (持っている特殊能力の PowerKey の文字列, 実装,
        特殊能力の定義)。持っていなければ (None, None, None)。"""
        for definition, index, power in power_defs(pid):  # v0.49
            effect = state.effects.power_effect(definition.id, power)
            if isinstance(effect, PreventKnockOutOnHeads):
                return f"{definition.id}@power{index}", effect, power
        return None, None, None

    def rebirth_power(uid: int) -> tuple[str | None, object | None]:
        """カード ``uid`` の「ふしちょう」（v0.12。``ReturnToHandOnKnockOut``）: (PowerKey の文字列, 特殊能力の定義)。なければ (None, None)。"""
        definition = state.in_play_def(uid)
        for index, power in enumerate(definition.powers):
            if isinstance(state.effects.power_effect(definition.id, power), ReturnToHandOnKnockOut):
                return f"{definition.id}@power{index}", power
        return None, None

    def active_retaliation(pid: int, turn: int) -> dict | None:
        """ログから組み立てた、ポケモン ``pid`` の今の番 ``turn`` にはたらく「ほのおのかべ」（v0.12）・「こうらがえし」（v0.13）の効果。"""
        for (effect_pid, _), info in alive.items():
            if effect_pid == pid and info["kind"] in (*RETALIATION_KINDS.values(), RETALIATION_RECEIVED_SCALED_KIND) and info["active_turn"] == turn:
                return info
        return None

    def lasting_value(pid: int, kind: str, field: str):
        """v0.48: ログから組み立てた、ポケモン ``pid`` の期限のない効果（``kind``。テクスチャー1・2・きょだいか）の値（色・最大HP）。なければ None。"""
        values = [info[field] for (effect_pid, _), info in alive.items() if effect_pid == pid and info["kind"] == kind]
        if len(values) > 1:
            problems.append(f"ポケモン {pid} に同じ種類の期限のない効果（{kind}）が 2 つ以上ある（置きかえたはず）")
        return values[-1] if values else None

    def max_hp_now(pid: int) -> int:
        """v0.48: ログから組み立てた今の場の、ポケモン ``pid`` の今有効な最大HP（``effects.max_hp`` と同じ求め方を、ログから組み立てた値で）。「きょだいか」の効果
        （max_hp_set）があればその数、なければいちばん上のカードの HP に、はたらいている［ガスのからだ］（ついている「超」の基本エネルギーカードの枚数 × 10。ねむり・
        マヒ・こんらんでもはたらき、ログから組み立てたかがくへんかガスで消える）を足す。"""
        form = form_def(pid)  # v0.49: 今の姿のカードの HP
        fixed = lasting_value(pid, MaxHpSet.kind, "amount")
        bonus = 0
        for definition, _, power in power_defs(pid):
            effect = state.effects.power_effect(definition.id, power)
            if isinstance(effect, MaxHpPerAttachedEnergyCards) and not [g for _, g in working_gases() if g.suppresses(power)]:
                bonus += effect.per * sum(1 for uid in energy.get(pid, ())
                                          if state.printed_def(uid).is_basic_energy and state.printed_def(uid).provides is effect.energy_type)
        if fixed is not None and bonus:
            problems.append(f"ポケモン {pid} の最大HPを、その数にする効果と大きくする特殊能力が同時に変えている（今の写しでは起こらない）")
        return fixed if fixed is not None else form.hp + bonus

    def hp_of(pid: int) -> int:
        """v0.48: ログから組み立てた今の場のポケモン ``pid`` の今有効な最大HP（場にいなければ 0）。"""
        return max_hp_now(pid) if pid in top and pid in in_play else 0

    def weakness_now(pid: int):
        """v0.48: ログから組み立てた、ポケモン ``pid`` の今有効な弱点の色（「テクスチャー1」の効果があればその色）。"""
        color = lasting_value(pid, WeaknessChange.kind, "color")
        return EnergyType(color) if color is not None else form_def(pid).weakness  # v0.49: 今の姿

    def resistance_now(pid: int):
        """v0.48: ログから組み立てた、ポケモン ``pid`` の今有効な抵抗力の色（「テクスチャー2」の効果があればその色。数は変えない）。"""
        color = lasting_value(pid, ResistanceChange.kind, "color")
        return EnergyType(color) if color is not None else form_def(pid).resistance  # v0.49: 今の姿

    def type_readings_now(pid: int) -> tuple:
        """v0.48: ログから組み立てた、ポケモン ``pid`` の色の読み方（``effects.type_readings`` と同じ求め方。［へんしょく］の記録が、使った番のうちで、ベンチに
        もどっておらず、いちばん上のカードが同じで、この力が消えていない（ねむり・マヒ・こんらん・かがくへんかガス）なら変えた色だけ。記録があって決まらなければ
        （VS1）変えた色と印刷の色の 2 つ）。"""
        printed = form_def(pid).pokemon_type  # v0.49: 今の姿のカードの色
        shift = shifts.get(pid)
        if shift is None:
            return (printed,)
        works = False
        for definition, _, power in power_defs(pid):
            if isinstance(state.effects.power_effect(definition.id, power), ShiftColor):
                works = pid not in exclusive and not [g for _, g in working_gases() if g.suppresses(power)]
        determined = shift["turn"] == current_turn and not shift["returned"] and shift["source_card"] == top[pid] and works
        if determined or shift["color"] is printed:
            return (shift["color"],)
        return (shift["color"], printed)

    def retaliation_damage_problems(e: dict, ret: dict) -> list[str]:
        """「ほのおのかべ」のダメージのログ（v0.12）: 基本となるダメージが効果の量で、弱点・抵抗力は R団のファイヤーのタイプと、受けた
        ポケモン（いちばん上のカード）の弱点・抵抗力で計算した（W15・W16。p.82「この10ダメージは、弱点・抵抗力の影響を受けます」）。
        v0.13 の「こうらがえし」も同じ（基本となるダメージは受けたダメージ。弱点・抵抗力はわるいカメールのタイプで計算する。S20〜S22。p.89）。"""
        found = []
        pid = e.get("pokemon_id")
        steps = e.get("steps") or ()
        if not steps or tuple(steps[0]) != ("1 基本となる計算", ret["amount"]):
            found.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」のダメージの基本となるダメージ {steps[:1]} が {ret['amount']} ではない（W14）")
        if pid in top and ret["pokemon_id"] in top:
            # v0.48: 受けたポケモンの今有効な弱点・抵抗力（テクスチャー1・2）と、効果を持つポケモンの色の読み方（読み方で結果が変わる場合はエンジンが止める）
            readings = type_readings_now(ret["pokemon_id"])
            weakness, resistance = weakness_now(pid), resistance_now(pid)
            if e["weakness"] not in {weakness is not None and weakness is color for color in readings}:
                found.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」のダメージの弱点 {e['weakness']} が、タイプと弱点に合わない（W15）")
            if e["resistance"] not in {resistance is not None and resistance is color for color in readings}:
                found.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」のダメージの抵抗力 {e['resistance']} が、タイプと抵抗力に合わない（W16）")
        return found

    def zero_damage_below_problems(e: dict) -> list[str]:
        """ワザのダメージのログ（v0.45）の p.321 の 8 段階の「決まった数より小さければ 0 にする」効果（イワークの「かたくなる」）の記録。ダメージを受けた
        ポケモンが、今の番にはたらく ``zero_damage_below`` の効果（ログから組み立てた）を持つときだけ記録があり、しきい値は効果を与えたワザの登録の値、
        受けたダメージは 0 かしきい値以上。"""
        pid = e["pokemon_id"] if "pokemon_id" in e else ids.get(e["pokemon"])
        expected = []
        for (effect_pid, _), info in alive.items():
            if effect_pid == pid and info["kind"] == "zero_damage_below" and info["active_turn"] == e["turn"]:
                card_id, index = info["effect"].split("#")
                expected.append((8, info["source_card"], state.effects.attack_entry(card_id, int(index)).effect.threshold_terms()[1]))
        recorded = [tuple(m) for m in e.get("damage_zero_below", ())]
        ended_early = e["amount"] == 0 and not any(str(step[0]).startswith("8 ") for step in (e.get("steps") or ()))
        if expected and not recorded and ended_early:
            return []  # p.321: 途中の段階で 0 以下になって計算を終えた（8 段階まで進まない）
        if recorded != expected:
            return [f"{e['turn']} 番のポケモン {pid} へのダメージの 8 段階の記録 {recorded} が、はたらいている「かたくなる」の効果 {expected} と違う"]
        if recorded and 0 < e["amount"] < recorded[0][2]:
            return [f"{e['turn']} 番のポケモン {pid} へのダメージ {e['amount']} が、0 でもしきい値 {recorded[0][2]} 以上でもない"]
        return []

    def attack_damage_set_problems(e: dict) -> list[str]:
        """ワザのダメージのログ（v0.27）の p.321 の 2 段階の記録。ワザを使ったポケモンが持つ効果（ログから組み立てた）から、そのダメージにはたらく
        2 段階の変更効果を求めて、記録と照らす:

        - 「つるぎのまい」（v0.27。「その数にする」）・「きあいだめ」（v0.35。「数をかける」）: 効果の登録の ``next_turn_terms`` の位置のワザ（名前では
          探さない）のダメージで、はたらく番が今の番。自分へのダメージ（``target`` が ``self``）は、登録が自分へのダメージにも当てはめるときだけ
        - 「なきつく」（v0.34）: 受けたポケモン（ワザを使ったポケモン）が、効果の発生源のカードの対戦ポケモンに与えるダメージ
        はたらく効果がなければ 2 段階の記録はない。あれば、1 段階のすぐあとに効果の数だけ 2 段階の記録が並び、計算した順番に当てはめた数が記録の数と同じ。
        「その数にする」は ``damage_set``、「数をかける」は ``damage_multiplied``、加える数は ``modifiers`` に入る。2 つ以上なら、順番の決定で選んだ順番
        （``step_orders``。v0.35）が記録の並びと同じで、決定がなければ集めた順番（効果の登録 → なきつく）。"""
        target = e.get("target")
        expected: list[tuple[str, str, int, int]] = []  # (名前, 計算, 数, 発生源のカード)。集めた順番
        for (effect_pid, _), info in alive.items():
            if effect_pid != attack_window["pokemon_id"] or info["kind"] not in NEXT_TURN_DAMAGE_KINDS.values() or info["active_turn"] != e["turn"]:
                continue
            card_id, index = info["effect"].split("#")
            entry = state.effects.attack_entry(card_id, int(index))
            terms = entry.effect.next_turn_terms()
            operation, includes_self = (terms[2], terms[3]) if len(terms) == 4 else ("set", False)
            if attack_window["effect"] == f"{card_id}#{terms[0]}" and (target != "self" or includes_self):
                expected.append((entry.name_ja, operation, terms[1], info["source_card"]))
        for (effect_pid, _), info in alive.items():
            # v0.34: 「なきつく」を受けたポケモン（ワザを使ったポケモン）が、なきつくを使ったポケモン（効果の発生源のカード）の対戦ポケモンにワザの
            # ダメージを与えるときは、p.321 の 2 段階で効果の量をへらす
            if (effect_pid == attack_window["pokemon_id"] and info["kind"] == ReducedDamageToSource.kind and info["active_turn"] == e["turn"]
                    and target is None and e["pokemon"] == info["source_card"]):
                card_id, index = info["effect"].split("#")
                amount = state.effects.attack_entry(card_id, int(index)).effect.amount
                expected.append((f"{state.printed_def(info['source_card']).name_ja}（{ReducedDamageToSource.kind}）", "add", -amount, info["source_card"]))
        steps = [tuple(step) for step in (e.get("steps") or ())]
        # v0.46: 常にはたらく特殊能力の 2 段階の記録（くつろぐかおり・きょうぼう）は continuous_damage_problems が確かめる（ここでは並びの位置だけに数える）
        step2_all = [step for step in steps if str(step[0]).startswith("2 ")]
        step2 = [step for step in step2_all if not _v046_rank(str(step[0])[2:])]
        damage_set = tuple(tuple(m) for m in e.get("damage_set", ()))
        multiplied = tuple(tuple(m) for m in e.get("damage_multiplied", ()))
        orders = {step: tuple(labels) for step, labels in e.get("step_orders", ())}
        orders2 = [label for label in orders.get(2, ()) if not _v046_rank(label)]
        where = f"{e['turn']} 番のワザ {attack_window['effect']} のダメージの 2 段階 {step2}"
        if not expected:
            if step2 or damage_set or multiplied or orders2:
                return [f"{where}: はたらいている効果のない 2 段階の記録・{damage_set}・{multiplied}・{orders} がある"]
            return []
        by_label = {label: (operation, amount, source) for label, operation, amount, source in expected}
        applied = [str(step[0])[2:] for step in step2]
        if len(by_label) != len(expected) or sorted(applied) != sorted(by_label) or steps[1:1 + len(step2_all)] != step2_all:
            return [f"{where} が、はたらく効果 {[x[0] for x in expected]} と合わない"]
        value = steps[0][1]
        for label, recorded in ((str(step[0])[2:], step[1]) for step in step2_all):
            if _v046_rank(label):
                value = recorded  # v0.46: 常にはたらく特殊能力のあとの数（continuous_damage_problems が確かめる）
                continue
            operation, amount, _ = by_label[label]
            value = amount if operation == "set" else value * amount if operation == "multiply" else value + amount
            if recorded != value:
                return [f"{where} の「{label}」のあとの数 {recorded} が、計算した {value} と違う"]
        if damage_set != tuple((2, by_label[label][2], by_label[label][1]) for label in applied if by_label[label][0] == "set") \
                or multiplied != tuple((2, by_label[label][2], by_label[label][1]) for label in applied if by_label[label][0] == "multiply") \
                or any((2, by_label[label][2], by_label[label][1]) not in [tuple(m) for m in e.get("modifiers", ())]
                       for label in applied if by_label[label][0] == "add"):
            return [f"{where} の damage_set {damage_set}・damage_multiplied {multiplied}・modifiers が、計算した順番の効果と合わない"]
        if len(expected) > 1:
            if 2 in orders and orders2 != applied:
                return [f"{where} の並びが、順番の決定で選んだ順番 {orders[2]} と違う"]
            if 2 not in orders and applied != [x[0] for x in expected]:
                return [f"{where} が、順番の決定がないのに集めた順番 {[x[0] for x in expected]} でない"]
        elif 2 in orders and len(step2_all) < 2:
            # v0.46: 2 段階の効果が 1 つでも、常にはたらく特殊能力（くつろぐかおり）と重なれば順番の決定がある
            return [f"{where}: 2 段階の効果が 1 つなのに順番の決定の記録 {orders} がある"]
        return []

    def is_active(pid: int | None) -> bool:
        """ログから組み立てた今の場で、ポケモン ``pid`` がバトル場にいるか（v0.46）。"""
        return pid is not None and pid in in_play and active_of.get(pokemon_owner.get(pid)) == pid

    def working_continuous(pid: int | None, types, *, attack_status: frozenset | None = None) -> list[tuple[str, object, object]]:
        """ログから組み立てた今の場で、ポケモン ``pid`` のいちばん上のカードの、はたらいている常にはたらく特殊能力（``types`` の型。v0.46）:
        [(PowerKey の文字列, 実装, 特殊能力の定義)]。場所（バトル場・ベンチ）・特殊状態（説明ごと。［くつろぐかおり］はワザの宣言の時点 ``attack_status``）・
        はたらいているかがくへんかガスで決める（エンジンの ``effects.continuous_powers`` と別に、ログから求める）。"""
        if pid is None or pid not in in_play:
            return []
        found = []
        for definition, index, power in power_defs(pid):  # v0.49: 今持つ特殊能力
            effect = state.effects.power_effect(definition.id, power)
            if not isinstance(effect, types):
                continue
            if (effect.location == CONTINUOUS_ACTIVE and not is_active(pid)) or (effect.location == CONTINUOUS_BENCH and is_active(pid)):
                continue
            if effect.requires_confusion:
                blocked = exclusive.get(pid) != "confusion"
            elif not effect.blocked_by_status:
                blocked = False
            elif effect.status_at_attack and attack_status is not None:
                blocked = pid in attack_status
            else:
                blocked = pid in exclusive
            if blocked or [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(power)]:
                continue
            found.append((f"{definition.id}@power{index}", effect, power))
        return found

    def continuous_expected(attacker_pid: int | None, receiver_pid: int | None, attack_status: frozenset | None) -> list[tuple]:
        """ワザのダメージ（``attacker_pid`` → ``receiver_pid``）に当てはまる、常にはたらく特殊能力と「リフレクター」の変更効果（v0.46）:
        [(段階, 名前, 計算, しきい値, 数, 発生源のカード)]。ログから組み立てた場（場所・特殊状態・かがくへんかガス・持続する効果）で求める。"""
        expected = []
        if attacker_pid not in in_play or receiver_pid not in in_play:
            return expected
        for (effect_pid, _), info in alive.items():
            if effect_pid == receiver_pid and info["kind"] == HalvedDamage.kind and info["active_turn"] == turn_now:
                expected.append((8, f"{state.printed_def(info['source_card']).name_ja}（{HalvedDamage.kind}）", HALVE_DOWN, None, 2, info["source_card"]))
        attacker_active = is_active(attacker_pid)
        for pid in sorted(in_play, key=lambda q: (pokemon_owner.get(q), not is_active(q), q)):
            for key, effect, power in working_continuous(pid, ContinuousPower, attack_status=attack_status):
                label, source = f"{state.definitions[key.partition('@')[0]].name_ja}［{power.name_ja}］", top[pid]  # v0.49: 特殊能力を印刷したカードの名前
                if isinstance(effect, ZeroLargeDamageReceived) and pid == receiver_pid:
                    expected.append((8, label, ZERO_IF_AT_LEAST, None, effect.threshold, source))
                elif isinstance(effect, CapDamageFromBasic) and pid == receiver_pid and form_def(attacker_pid).is_basic_pokemon:
                    expected.append((8, label, SET_IF_AT_LEAST, effect.threshold, effect.amount, source))
                elif isinstance(effect, HalveActiveAttackDamage) and attacker_active:
                    expected.append((2 if pid == attacker_pid else 8 if pid == receiver_pid else 6, label, HALVE_UP, None, 2, source))
                elif isinstance(effect, BonusDamageWhileConfused) and pid == attacker_pid:
                    expected.append((2, label, ADD, None, effect.amount, source))
                elif isinstance(effect, HalveDamageReceived) and pid == receiver_pid:
                    expected.append((8, label, HALVE_DOWN, None, 2, source))  # v0.47: ［カブトアーマー］
        return expected

    def continuous_damage_problems(e: dict) -> list[str]:
        """ワザのダメージのログ（v0.46）の、常にはたらく特殊能力（なぞのかべ・ふしぎなバリアー・くつろぐかおり・きょうぼう）と「リフレクター」の記録。ログから組み立てた
        場で当てはまる効果（``continuous_expected``）が、その段階の記録に 1 回ずつあり（計算が 2 段階で終わったら 3 段階からあとはない）、当てはまらない効果の記録が
        なく、記録の数が直前の数から計算した数（しきい値・その数・半分の丸め・加える数）で、``damage_zero_at_least``・``damage_set_if_at_least``・``damage_halved``・
        ``modifiers`` が記録と合う。計算の順番の決定のない段階では、v0.45 までの効果 → リフレクター → 常にはたらく特殊能力の順。決定があれば選んだ順番。"""
        if e.get("retaliation"):
            ret = attack_window.get("ret")
            attacker_pid = ret["pokemon_id"] if ret is not None else None
        else:
            attacker_pid = attack_window["pokemon_id"]
        receiver_pid = e["pokemon_id"] if "pokemon_id" in e else ids.get(e["pokemon"])
        where = f"{e['turn']} 番のポケモン {attacker_pid} → {receiver_pid} のワザのダメージ"
        steps = [tuple(step) for step in (e.get("steps") or ())]
        early = [step for step in steps if str(step[0])[:2] in ("1 ", "2 ")]
        ended_early = bool(early) and early[-1][1] <= 0 and len(early) == len(steps)
        expected = [x for x in continuous_expected(attacker_pid, receiver_pid, attack_window.get("status_at_attack"))
                    if not ended_early or x[0] <= 2]
        by_label = {f"{x[0]} {x[1]}": x for x in expected}
        recorded = [(i, step) for i, step in enumerate(steps) if _v046_rank(str(step[0]).partition(" ")[2])]
        found = []
        if len(by_label) != len(expected) or sorted(str(step[0]) for _, step in recorded) != sorted(by_label):
            return [f"{where} の記録 {[step[0] for _, step in recorded]} が、当てはまる効果 {sorted(by_label)} と合わない"]
        for i, step in recorded:
            stage, _, operation, threshold, amount, _ = by_label[str(step[0])]
            before = steps[i - 1][1]
            per = state.rules.damage_per_counter
            value = (0 if before >= amount else before) if operation == ZERO_IF_AT_LEAST else \
                (amount if before >= threshold else before) if operation == SET_IF_AT_LEAST else \
                before if before <= 0 and operation in (HALVE_UP, HALVE_DOWN) else \
                ((before // per + 1) // 2 * per) if operation == HALVE_UP else (before // per // 2 * per) if operation == HALVE_DOWN else before + amount
            if step[1] != value:
                found.append(f"{where} の「{step[0]}」のあとの数 {step[1]} が、{before} から計算した {value} と違う")
        applied = [by_label[str(step[0])] for _, step in recorded]
        zero = sorted((x[0], x[5], x[4]) for x in applied if x[2] == ZERO_IF_AT_LEAST)
        capped = sorted((x[0], x[5], x[3], x[4]) for x in applied if x[2] == SET_IF_AT_LEAST)
        halved = sorted((x[0], x[5], "up" if x[2] == HALVE_UP else "down") for x in applied if x[2] in (HALVE_UP, HALVE_DOWN))
        if sorted(tuple(m) for m in e.get("damage_zero_at_least", ())) != zero \
                or sorted(tuple(m) for m in e.get("damage_set_if_at_least", ())) != capped \
                or sorted(tuple(m) for m in e.get("damage_halved", ())) != halved \
                or any((x[0], x[5], x[4]) not in [tuple(m) for m in e.get("modifiers", ())] for x in applied if x[2] == ADD):
            found.append(f"{where} の damage_zero_at_least・damage_set_if_at_least・damage_halved・modifiers が、記録した効果 {[x[1] for x in applied]} と合わない")
        orders = {stage: tuple(labels) for stage, labels in e.get("step_orders", ())}
        for stage in sorted({int(str(step[0]).split(" ")[0]) for step in steps if str(step[0])[0].isdigit()}):
            at = [str(step[0]).partition(" ")[2] for step in steps if str(step[0]).split(" ")[0] == str(stage)]
            if stage in orders:
                if list(orders[stage]) != at or len(at) < 2:
                    found.append(f"{where} の {stage} 段階の並び {at} が、順番の決定で選んだ順番 {orders[stage]} と違う")
            elif [_v046_rank(label) for label in at] != sorted(_v046_rank(label) for label in at):
                found.append(f"{where} の {stage} 段階の並び {at} が、順番の決定がないのに集めた順番（v0.45 までの効果 → リフレクター → 常にはたらく特殊能力）でない")
        return found

    def received_power_expected(receiver_pid: int, source_pid: int | None, amount: int) -> tuple[int, tuple]:
        """特殊能力のダメージ（はんげき・わるいねぞう・こっそりかみつく。v0.46）を ``receiver_pid`` が ``source_pid`` から受けるときの、受けるダメージ全体を書く
        常にはたらく特殊能力（なぞのかべ・ふしぎなバリアー）を当てはめた数と記録（(発生源のカード, 計算, しきい値, 数)）。ログから組み立てた場で求める。"""
        applied = []
        for _, effect, _ in working_continuous(receiver_pid, (ZeroLargeDamageReceived, CapDamageFromBasic, HalveDamageReceived)):
            if isinstance(effect, HalveDamageReceived):
                # v0.47: ［カブトアーマー］（半分。切りすて）
                applied.append((top[receiver_pid], HALVE_DOWN, None, 2))
                amount = amount if amount <= 0 else amount // state.rules.damage_per_counter // 2 * state.rules.damage_per_counter
            elif isinstance(effect, ZeroLargeDamageReceived):
                applied.append((top[receiver_pid], ZERO_IF_AT_LEAST, None, effect.threshold))
                amount = 0 if amount >= effect.threshold else amount
            elif source_pid in in_play and form_def(source_pid).is_basic_pokemon:
                applied.append((top[receiver_pid], SET_IF_AT_LEAST, effect.threshold, effect.amount))
                amount = effect.amount if amount >= effect.threshold else amount
        return amount, tuple(applied)

    def received_power_problems(e: dict, receiver_pid: int, source_pid: int | None, registered: int) -> list[str]:
        """特殊能力のダメージのログ（counterattack・power_damage）の量と、受けるダメージを変える特殊能力の記録（v0.46。``amount_before``・``received_modifiers``。
        当てはめたときだけある）。"""
        expected, applied = received_power_expected(receiver_pid, source_pid, registered)
        recorded = tuple(tuple(m) for m in e.get("received_modifiers", ()))
        if not applied and not recorded and "amount_before" not in e:
            # 当てはめる特殊能力がないときは v0.45 までと同じ確かめと文（登録の量）
            if e["amount"] == registered:
                return []
            if e["kind"] == "counterattack":
                return [f"{e['turn']} 番の「はんげき」の量 {e['amount']} が、登録の {registered} と違う"]
            return [f"{e['turn']} 番の power_damage（{e['power']} → ポケモン {receiver_pid}）が、場に出たときに相手の場のポケモンにダメージを与える特殊能力の処理と合わない"]
        if e["amount"] != expected or recorded != applied or (("amount_before" in e) != bool(applied)) \
                or (applied and e["amount_before"] != registered):
            return [f"{e['turn']} 番の {e['kind']}（→ ポケモン {receiver_pid}）の量 {e['amount']}・記録 {recorded} が、登録の {registered} に受けるポケモンの"
                    f"特殊能力 {applied} を当てはめた {expected} と合わない"]
        return []

    def source_of(e: dict) -> dict | None:
        """イベント ``e``（判定・ダメージ・はんげき）を起こしたワザ（v0.12）: 今の番のワザ（attack_window）か、その中の「ほのおのかべ」
        （attack_window["ret"]。ワザを使ったポケモンは R団のファイヤー）。どちらでもなければ None。"""
        if attack_window is None:
            return None
        keys = (e.get("effect"), e.get("attacker"), e.get("attacker_pokemon_id"))
        if keys == (attack_window["effect"], attack_window["player"], attack_window["pokemon_id"]):
            return attack_window
        ret = attack_window["ret"]
        if ret is not None and keys == (ret["effect"], ret["player"], ret["pokemon_id"]):
            return ret
        return None

    def received(e: dict, pid: int, element: str, *, blocked: str | None = None) -> None:
        """ワザの要素 ``element`` のダメージ・効果を、ポケモン ``pid`` が受けた（v0.9）。はたらいている「とうめい」があれば、その前に
        このワザでの判定があって「受ける」こと。"""
        if attack_window is None or pid not in in_play:
            return
        reception = attack_window["reception"]
        if e.get("retaliation"):
            # v0.12: 「ほのおのかべ」のダメージは R団のファイヤーのワザによるダメージ（「とうめい」の判定は、そのワザで 1 回）
            if attack_window["ret"] is None:
                return
            reception = attack_window["ret"]["reception"]
        if reception.get(pid) is False:
            problems.append(f"{e['turn']} 番のワザで「とうめい」により受けないと決まったポケモン {pid} が {element} を受けた（{e['kind']}）")
        elif pid not in reception:
            key, blocked_by = evasion(pid, blocked=blocked)
            if key is not None and blocked_by is None:
                problems.append(f"{e['turn']} 番のワザの {element} を、はたらいている「とうめい」のポケモン {pid} が判定（evade_check）なしで受けた")

    def window_damaged(window: dict) -> bool:
        """今のワザ（attack_window）に、すでにダメージの要素（damage・damage_prevented・ダメージの attack_evaded）があったか（v0.42）。"""
        return bool(window.get("any_damage"))

    def enter(uid: int) -> None:
        nonlocal next_id
        ids[uid] = next_id
        energy[next_id] = []
        in_play.add(next_id)
        pokemon_owner[next_id] = owner[uid]
        top[next_id] = uid
        next_id += 1

    def from_hand(e: dict, player: int, uid: int) -> None:
        """手札から出たカード（v0.6）。ログから組み立てた手札になければ報告する。"""
        if uid in hand[player]:
            hand[player].remove(uid)
        else:
            problems.append(f"{e['turn']} 番の {e['kind']} のカード {uid} が、ログから組み立てたプレイヤー {player} の手札にない")

    owner = {uid: card.owner for uid, card in state.cards.items()}
    turn_now = 0  # v0.46: 今処理しているイベントの番（continuous_expected が持続する効果のはたらく番を見る）
    declared = None  # 直前の特殊能力の宣言（番・プレイヤー・ポケモン）。移動のログはその直後に続く（v0.5）
    for e in log:
        kind = e["kind"]
        turn_now = e["turn"]
        prior = previous  # 1 つ前のイベント（v0.11。「こんじょう」の宣言・コイン・結果の順番）
        if prior is not None and prior["kind"] == "attack" and kind != "once_attack_recorded":
            # v0.44: 場に出てから 1 度しか使えないワザの宣言のすぐあとには、その記録（once_attack_recorded）がある
            once_entry = state.effects.attack_entry(_attack_card_id(state, prior), prior["attack_index"])
            if once_entry is not None and once_entry.effect.once_after_entering_play:
                problems.append(f"{prior['turn']} 番の 1 度だけ使えるワザの宣言（ポケモン {ids.get(prior['pokemon'])}）のすぐあとに、その記録がない（{kind}）")
        if search_due is not None:
            # v0.38: でんれい。もどしたあと、持続する効果を消したログ・同じワザのかわりの対戦ポケモンを出すログ（promote_active）のあと、同じワザの
            # 山札をさがすログ（reveal_from_deck・reveal_from_deck_none）が続き、そのすぐあとに山札を切る（途中で切らない）
            same = e.get("effect") == search_due["effect"] and e.get("player") == search_due["player"]
            if kind == "persistent_effect_removed" and e["reason"] == "return_in_play_to_deck" and e["pokemon_id"] == search_due["pokemon_id"]:
                pass
            elif kind == "promote_active" and same:
                pass
            elif kind in ("reveal_from_deck", "reveal_from_deck_none") and same:
                search_due, shuffle_due = None, e
            else:
                problems.append(f"{search_due['turn']} 番の {search_due['kind']} のあとに、同じワザの山札をさがす処理がないまま {kind} になった")
                search_due = None
        elif shuffle_due is not None and not (
            # v0.36: 山札にもどしたポケモン（return_in_play_to_deck）の持続する効果を消したログは、もどしたあと・山札を切る前
            shuffle_due["kind"] == "return_in_play_to_deck" and kind == "persistent_effect_removed" and e["reason"] == "return_in_play_to_deck"
            and e["pokemon_id"] == shuffle_due["pokemon_id"]
        ) and not (
            # v0.42: つきのちから。山札から重ねた進化（evolve）の手順（特殊状態・持続する効果・にげるの失敗の記録を消す）のあと、山札を切る
            shuffle_due["kind"] == "evolve" and kind in ("special_conditions_removed", "persistent_effect_removed", "retreat_failure_cleared")
            and e.get("reason") == "evolve" and e["pokemon_id"] == shuffle_due["pokemon_id"]
        ) and not (
            # v0.40: むれでおそうは、好きなだけ出したあと（同じワザの bench_from_deck が続いたあと）に 1 回だけ切る
            shuffle_due["kind"] == "bench_from_deck" and kind == "bench_from_deck" and e.get("effect") == shuffle_due.get("effect")
            and e["player"] == shuffle_due["player"] and "effect" in e and _benches_any_from_deck(state, e["effect"])
        ) and not (
            # v0.43: てしたをよぶは、最大 2 枚を続けて出したあと（同じ特殊能力の bench_from_deck が続いたあと）に 1 回だけ切る
            shuffle_due["kind"] == "bench_from_deck" and kind == "bench_from_deck" and "power" in e and e["power"] == shuffle_due.get("power")
            and e["player"] == shuffle_due["player"]
        ) and shuffle_due is not e:
            due_event, shuffle_due = shuffle_due, None
            if kind != "shuffle" or e["player"] != due_event["player"]:
                problems.append(f"{due_event['turn']} 番の {due_event['kind']} のすぐあとに、プレイヤー {due_event['player']} の山札を切る処理（shuffle）がない")
        if check_due is not None and not (kind == "coin_flip" and e["source"] == "attack_check"):
            due_check, check_due = check_due, None
            if kind != "attack_check" or (e["pokemon_id"], e["created_turn"]) != due_check[:2] or prior is None \
                    or prior["kind"] != "coin_flip" or prior["source"] != "attack_check" or prior["result"] != e["result"] \
                    or prior["player"] != e["player"] or e["succeeded"] != (e["result"] == "heads"):
                problems.append(f"{e['turn']} 番のワザの宣言（ポケモン {due_check[0]}）のすぐあとに、手順 4 のコイン（coin_flip・attack_check）がない（{kind}）")
            elif not e["succeeded"]:
                check_failed = e
            if kind == "attack_check" and due_check[2]:
                used_due = (due_check[0], due_check[1])  # 「1回できえる」効果は、すぐあとに消える（理由 used）
        elif used_due is not None:
            due_used, used_due = used_due, None
            if kind != "persistent_effect_removed" or e["reason"] != "used" or (e["pokemon_id"], e["created_turn"]) != due_used:
                problems.append(f"{e['turn']} 番の手順 4 のコインのあとに、「1回できえる」効果（ポケモン {due_used[0]}）を消したログがない（{kind}）")
        elif kind == "attack_check":
            problems.append(f"{e['turn']} 番の手順 4 のコイン（ポケモン {e['pokemon_id']}）が、ワザの宣言のすぐあとにない・はたらいている効果がない")
        elif check_failed is not None and kind != "attack_check" and not (kind == "persistent_effect_removed" and e["reason"] == "used"):
            failed, check_failed = check_failed, None
            if kind != "attack_failed" or e.get("reason") != "attack_check" or e["pokemon_id"] != failed["pokemon_id"]:
                problems.append(f"{failed['turn']} 番の手順 4 のコインが「うら」（ポケモン {failed['pokemon_id']}）なのに、そのあとに attack_failed がない（{kind}）")
        if kind == "persistent_effect_removed" and e["reason"] == "used":
            info = alive.get((e["pokemon_id"], e["created_turn"]))
            if prior is None or prior["kind"] != "attack_check" or prior["pokemon_id"] != e["pokemon_id"] or info is None \
                    or info["kind"] != AttackCoinCheck.kind or not info.get("single_use"):
                problems.append(f"{e['turn']} 番に「1回できえる」でない効果・手順 4 のコインのあとでない効果（ポケモン {e['pokemon_id']}）を「使った」で消した")
        if kind not in DECLARED_FOLLOWERS:
            # v0.42: 宣言のすぐあとに、その特殊能力の処理の最初のログ（コイン・入れ替え・手札のトラッシュ・ダメージカウンターをとりのぞく処理）がある
            if declared is not None and not _follows_declaration(state, declared_key, declared[1], declared[2], e):
                problems.append(
                    f"{declared[0]} 番の特殊能力の宣言（ポケモン {declared[2]}）のすぐあとに、その処理（move_energy・power_attach_energy・"
                    "move_damage_counter・v0.42 の特殊能力の処理）がない"
                )
            declared = None
        if draw_due is not None:
            due_draw, draw_due = draw_due, None
            if kind != "draw" or e["player"] != due_draw[0] or len(e["cards"]) > due_draw[1]:
                problems.append(f"{due_draw[2]} 番の {due_draw[3]} のすぐあとに、プレイヤー {due_draw[0]} が {due_draw[1]} 枚まで引く処理（draw）がない（{kind}）")
        answers_entry = kind == "entry_power_declined" or (kind == "pokemon_power" and "entry" in e)
        if entry_due is not None and kind not in ("special_conditions_removed", "persistent_effect_removed", "retreat_failure_cleared"):
            due_entry, entry_due = entry_due, None
            if not answers_entry or e["pokemon_id"] != due_entry[1] or e["turn"] != due_entry[0]:
                problems.append(f"{due_entry[0]} 番の進化（ポケモン {due_entry[1]}）のすぐあとに、場に出たときの特殊能力 {due_entry[2]} を使うかの答えがない（{kind}）")
        elif answers_entry:
            problems.append(f"{e['turn']} 番の場に出たときの特殊能力の答え（ポケモン {e['pokemon_id']}）が、使う機会（その特殊能力を持つカードの進化のすぐあと）にない")
        if kind != "move_energy":
            moving = None
        if condition_due is not None:
            due_coin, condition_due = condition_due, None
            if kind != "special_condition" or e["pokemon_id"] != due_coin[1] or e.get("effect") != due_coin[0]["effect"]:
                problems.append(f"{due_coin[0]['turn']} 番の特殊能力のコインのあと、置きかえたポケモン {due_coin[1]} が、その特殊能力の特殊状態にならない（{kind}）")
        if previous is not None and previous["kind"] == "coin_flip" and previous["source"] == "power" and kind == "special_conditions_removed" \
                and isinstance(_power_effect(state, previous.get("effect")), CoinConditionOnEitherActive):
            condition_due = (previous, e["pokemon_id"])
        power_knock_out = False
        if power_ko_due is not None:
            due_pid, power_ko_due = power_ko_due, None
            if kind == "knock_out" and ids.get(e["pokemon"]) == due_pid and e.get("timing") == "power":
                power_knock_out = True
            else:
                problems.append(f"{e['turn']} 番の特殊能力の処理で HP 以上になったポケモン {due_pid} が、すぐあとにきぜつしていない（{kind}）")
        if confusion_due is not None:
            due_pid, due_key = confusion_due
            if kind == "special_conditions_removed" and e["pokemon_id"] == due_pid and e["reason"] == "replaced":
                pass
            else:
                confusion_due = None
                if not (kind == "special_condition" and e["pokemon_id"] == due_pid and e["condition"] == "confusion" and e.get("effect") == due_key):
                    problems.append(f"{e['turn']} 番の「ぼうぎょかふん」の「おもて」のあとに、ダメージを与えたポケモン {due_pid} のこんらんがない（{kind}）")
        # v0.12: 「ふしちょう」。きぜつ（knock_out）のあと、サイド（take_prize）のあとに答え（post_knockout_power_declined・
        # post_knockout_power_declared）が 1 つ。対戦が終わるなら答えはない。宣言のすぐあとに、そのカードの return_to_hand
        if rebirth_answered is not None:
            answered, rebirth_answered = rebirth_answered, None
            if answered["kind"] == "post_knockout_power_declared" and not (
                kind == "return_to_hand" and e["card"] == answered["card"] and e["player"] == answered["player"] and e["power"] == answered["power"]
            ):
                problems.append(f"{answered['turn']} 番の「ふしちょう」の宣言（カード {answered['card']}）のすぐあとに、そのカードの return_to_hand がない（{kind}）")
        if kind == "return_to_hand" and (previous is None or previous["kind"] != "post_knockout_power_declared"):
            problems.append(f"{e['turn']} 番にトラッシュから手札に加えた {e['card']} の直前に、「ふしちょう」の宣言がない（使わなかった・宣言のない回収）")
        if batch_answered and kind in ("take_prize", "knock_out", "game_end"):
            problems.append(f"{e['turn']} 番の「ふしちょう」の答えのあとに {kind} がある（答えは、サイドを取り、対戦が続くと決まったあと。正規化した順番）")
        if kind in ("post_knockout_power_declined", "post_knockout_power_declared"):
            match = next((r for r in rebirth_pending if r["card"] == e["card"]), None)
            if match is None:
                problems.append(f"{e['turn']} 番の「ふしちょう」の答え（カード {e['card']}）が、直前のきぜつの処理の中にない")
            else:
                rebirth_pending.remove(match)
                if match["blocked"] is not None:
                    problems.append(f"{e['turn']} 番に、使えない「ふしちょう」（カード {e['card']}。{match['blocked']}）を使うかを決めた（P13〜P18）")
                if (e["player"], e["power"]) != (match["player"], match["power"]):
                    problems.append(f"{e['turn']} 番の「ふしちょう」の答え（カード {e['card']}）のプレイヤー・特殊能力が、きぜつしたカードの持ち主・特殊能力と違う")
            rebirth_answered = e
            batch_answered = True
        elif rebirth_pending and kind not in ("knock_out", "persistent_effect_removed", "take_prize"):
            if kind != "game_end":
                for r in rebirth_pending:
                    if r["blocked"] is None:
                        problems.append(f"{r['turn']} 番にきぜつした「ふしちょう」を使えるカード {r['card']} に、使うかの答えがないまま {kind} になった（P1・P2）")
            rebirth_pending = []
        if batch_answered and kind in ("promote_active", "turn_end", "pokemon_check", "turn_start"):
            batch_answered = False
        # v0.9: ワザを受けるときに自動的にはたらく特殊能力（ゴーストの「とうめい」）
        if previous is not None and previous["kind"] == "coin_flip" and previous["source"] == "power" and not _power_coin_follows(state, previous, e):
            # v0.9 の「とうめい」の判定・v0.11 の「こんじょう」の結果・v0.42 の「ぼうぎょかふん」の結果・ヒーリング・かおりのわなの「おもて」の処理
            problems.append(
                f"{previous['turn']} 番の特殊能力のコイン（{previous['effect']}）のすぐあとに、その結果（「とうめい」の判定 evade_check・"
                "「こんじょう」の ko_prevented・ko_prevention_failed・v0.42 の特殊能力の結果）がない"
            )
        # v0.11: 「こんじょう」の宣言のすぐあとに持ち主のコイン 1 枚（p.311 の手順。G13・G17）。使わなかったらコインはない（G11）
        if prior is not None and prior["kind"] == "ko_prevention_declared" and not (
            kind == "coin_flip" and e["source"] == "power" and e["player"] == prior["player"] and e["pokemon_id"] == prior["pokemon_id"]
            and e["effect"] == prior["power"]
        ):
            problems.append(f"{prior['turn']} 番の「こんじょう」の宣言（ポケモン {prior['pokemon_id']}）のすぐあとに、持ち主の「こんじょう」のコインがない（{kind}）")
        if prior is not None and prior["kind"] == "ko_prevention_declined" and kind == "coin_flip":
            problems.append(f"{prior['turn']} 番に「こんじょう」を使わなかった（ポケモン {prior['pokemon_id']}）のに、コインを投げた（G11）")
        if expect is not None:
            pid, element, reaches = expect
            expect = None
            if not reaches:
                follows = kind == "attack_evaded" and e["pokemon_id"] == pid and e["element"] == element
            elif element == DAMAGE_ELEMENT:
                follows = kind == "damage" and e.get("pokemon_id", ids.get(e["pokemon"])) == pid and e["amount"] > 0
            elif element == FORCED_SWITCH_ELEMENT:
                follows = kind == "forced_switch" and e["old_active_pokemon_id"] == pid
            elif element == ENERGY_DISCARD_ELEMENT:  # v0.31: 相手のエネルギーカードのトラッシュ（スーパーデストロイ・メラメラ）
                follows = kind == "discard_attached_energy" and e["pokemon_id"] == pid
            elif element == ATTACK_LOCK_ELEMENT:  # v0.31: 次の相手の番にワザを使えなくする効果（しっぽをふる）
                follows = kind == "persistent_effect_added" and e["pokemon_id"] == pid
            elif element == ENERGY_ATTACH_ELEMENT:  # v0.31: 控えポケモンにエネルギーをつける（エナジーボム）
                follows = kind == "attack_attach_energy" and e["to_pokemon_id"] == pid
            elif element in (REDUCED_DAMAGE_ELEMENT, ATTACK_CHECK_ELEMENT, RETREAT_LOCK_ELEMENT):
                # v0.34: 与えるダメージがへる状態にする効果（なきつく）。v0.36: すなかけ・えんまくなど・アイスバーン・わしづかみ
                follows = kind == "persistent_effect_added" and e["pokemon_id"] == pid
            elif element == RETURN_IN_PLAY_TO_DECK_ELEMENT:  # v0.36: 自分を山札にもどす（くもがくれガス）
                follows = kind == "return_in_play_to_deck" and e["pokemon_id"] == pid
            elif element == HEAL_ELEMENT:  # v0.41: ワザでダメージカウンターをとりのぞく（とりのぞくカウンターがあるポケモンだけで判定する）
                follows = kind == "attack_heal" and e["pokemon_id"] == pid
            elif element == COUNTERS_ELEMENT:  # v0.41: ダメージカウンターをのせる・取り替える（受けなければ CX1 で止まる）
                follows = (kind == "place_damage_counters" and e["pokemon_id"] == pid) or (kind == "swap_damage_counters" and e["opponent_pokemon_id"] == pid)
            elif element == EVOLVE_ELEMENT:  # v0.42: 山札の進化カードを重ねる（つきのちから）
                follows = kind == "evolve" and e["pokemon_id"] == pid
            elif element == RETURN_IN_PLAY_TO_HAND_ELEMENT:  # v0.42: 自分の場のポケモンを手札にもどす（ようせいのきせき）
                follows = kind == "return_in_play_to_hand" and e["pokemon_id"] == pid
            elif kind == "special_conditions_removed" and e["pokemon_id"] == pid and e["reason"] == "replaced":
                follows, expect = True, (pid, element, reaches)  # 置きかえてから、その特殊状態になる
            else:
                # v0.46: 効果を受けたが、めんえきで特殊状態にならない（special_condition_prevented）も受けたことになる
                follows = kind in ("special_condition", "special_condition_prevented") and e["pokemon_id"] == pid and e["condition"] == element
            if not follows:
                problems.append(
                    f"{e['turn']} 番の「とうめい」の判定（ポケモン {pid}・{element}・{'受ける' if reaches else '受けない'}）のすぐあとが {kind}"
                )
        # v0.10: ダメージを受けたときに自動的にはたらく特殊能力（カイリキーの「はんげき」）。ワザのダメージを受けたときにはたらいて
        # いたら（due）、そのワザのダメージの要素のあと、ダメージ以外の効果・きぜつの前に、counterattack（か counterattack_skipped）がある
        if attack_window is not None:
            due = attack_window["due"]
            if kind in ("damage", "damage_prevented") or (kind == "attack_evaded" and e["element"] == DAMAGE_ELEMENT):
                attack_window["any_damage"] = True  # v0.42: エネループのもどす処理はダメージの要素より前
            if kind == "damage" and e["amount"] > 0 and not e.get("retaliation"):
                # v0.42: このワザのダメージ（0 より大きい）を受けたポケモン（「ぼうぎょかふん」がはたらく理由）
                attack_window.setdefault("damaged", set()).add(e.get("pokemon_id", ids.get(e["pokemon"])))
            if kind == "damage":
                pid = e.get("pokemon_id", ids.get(e["pokemon"]))
                source = attack_window
                if e.get("retaliation"):
                    # v0.12: 「ほのおのかべ」のダメージ（R団のファイヤーのワザによるダメージ。ワザを使ったポケモンへ）
                    source = attack_window["ret"]
                    if source is None or source["damage_seen"]:
                        problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」のダメージ（ポケモン {pid}）の前に、その「ほのおのかべ」・「こうらがえし」（retaliation）がない・2 回目")
                        source = attack_window
                    else:
                        source["damage_seen"] = True
                        if (pid, e["player"], e.get("effect")) != (attack_window["pokemon_id"], attack_window["player"], source["effect"]):
                            problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」のダメージを受けたのが、ダメージを与えた相手の対戦ポケモン {attack_window['pokemon_id']} ではない（{pid}。W14）")
                        problems.extend(retaliation_damage_problems(e, source))
                elif attack_window["ret_seen"]:
                    problems.append(f"{e['turn']} 番のワザで、「ほのおのかべ」・「こうらがえし」のあとにワザのダメージの要素（ポケモン {pid}）がある（ダメージの処理のあとに与えるはず。p.89・W21）")
                if attack_window["counter_seen"]:
                    problems.append(f"{e['turn']} 番のワザで、「はんげき」のあとにダメージの要素（ポケモン {pid}）がある（ダメージの処理のあとに与えるはず。p.89）")
                if e["amount"] > 0 and pid in in_play and pokemon_owner.get(pid) != source["player"]:
                    key, amount, blocked_by = counter_power(pid)
                    if key is not None and blocked_by is None:
                        due.append((pid, key, amount))
                    if guts_power(pid)[0] is not None:
                        # v0.11: 「こんじょう」を持つポケモンが、相手のワザのダメージを受けたときのねむり・マヒ・こんらん（None なら使える。G29）
                        attack_window["ko_able"][pid] = exclusive.get(pid)
                    info = None if e.get("retaliation") else active_retaliation(pid, e["turn"])
                    if info is not None:
                        # v0.12: 「ほのおのかべ」がはたらく（W11・W13）。v0.13: 受けたダメージ（このログの最終ダメージ）も覚えておく
                        # （「こうらがえし」の返すダメージの基本となるダメージ。S9・S10）
                        attack_window["ret_due"].append((pid, info, e["amount"]))
            elif attack_window["ret_due"] and (
                kind in COUNTER_BARRIERS or (kind == "special_conditions_removed" and e["reason"] == "replaced")
                or (kind == "coin_flip" and e["source"] == "attack" and attack_window["counter_after_coin"])
            ):
                problems.append(f"{e['turn']} 番のワザで、はたらいた「ほのおのかべ」・「こうらがえし」（ポケモン {[d[0] for d in attack_window['ret_due']]}）より先に {kind} がある（p.89・W21）")
                attack_window["ret_due"].clear()
            elif due and (
                kind in COUNTER_BARRIERS or (kind == "special_conditions_removed" and e["reason"] == "replaced")
                or (kind == "coin_flip" and e["source"] == "attack" and attack_window["counter_after_coin"])
            ):
                problems.append(f"{e['turn']} 番のワザで、はたらいた「はんげき」（ポケモン {[d[0] for d in due]}）より先に {kind} がある（p.89）")
                due.clear()
            if kind == "knock_out" and attack_window["counter_ko"] is not None and ids.get(e["pokemon"]) != attack_window["counter_ko"]:
                problems.append(
                    f"{e['turn']} 番のワザで、「はんげき」できぜつしたポケモン {attack_window['counter_ko']} のほかにポケモン {ids.get(e['pokemon'])} が"
                    "きぜつした（同時のきぜつか決められない。UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT で止めるはず）"
                )
            if kind == "drain_heal" and attack_window["counter_ko"] == e["pokemon_id"]:
                problems.append(f"{e['turn']} 番に、「はんげき」できぜつしたポケモン {e['pokemon_id']} のダメージカウンターをとりのぞいた（C16）")
            if kind == "drain_heal_skipped" and (e["pokemon_id"] not in in_play or damage[e["pokemon_id"]] < max_hp_now(e["pokemon_id"])):
                problems.append(f"{e['turn']} 番に、きぜつしていないポケモン {e['pokemon_id']} のとりのぞく効果を処理しなかった")
        if kind == "attack":
            for (effect_pid, _), info in alive.items():
                # v0.35: 「あわあわ」（自分）・「ドわすれ」（相手が選んだワザ）で、はたらく番に使えないワザを使っていない
                if (effect_pid == ids.get(e["pokemon"]) and info["kind"] in (CannotUseOwnAttack.kind, CannotUseAttack.kind)
                        and info["active_turn"] == e["turn"] and info["target_attack_index"] == e["attack_index"]
                        and info["target_attack_card"] == _attack_card_id(state, e)):  # v0.49: ワザは (印刷したカード, 位置) で識別する
                    problems.append(f"{e['turn']} 番に、ポケモン {effect_pid} が使えないワザ（{e['attack_index']} 番目。{info['kind']}）を使った")
            # v0.36: はたらいている手順 4 のコインの効果（すなかけ・えんまくなど）。宣言のすぐあとにコインがあるはず
            due_checks = [(effect_pid, created, bool(info.get("single_use"))) for (effect_pid, created), info in alive.items()
                          if effect_pid == ids.get(e["pokemon"]) and info["kind"] == AttackCoinCheck.kind
                          and (info["active_turn"] <= e["turn"] if info.get("lasting") else info["active_turn"] == e["turn"])]
            if len(due_checks) > 1:
                problems.append(f"{e['turn']} 番のワザを使うポケモン {ids.get(e['pokemon'])} に、手順 4 のコインの効果が 2 つ以上ある")
            check_due = due_checks[0] if due_checks else None
            attack_window = {
                "player": e["player"], "pokemon_id": ids.get(e["pokemon"]), "reception": {},
                "effect": f"{_attack_card_id(state, e)}#{e['attack_index']}",
                # v0.10: はたらいた「はんげき」（場のポケモンの番号, PowerKey, 量）・「はんげき」のログがあったか・「はんげき」で
                # きぜつしたポケモン・効果のコインより前に「はんげき」があるはずか（ダメージのあとのコインが効果を決めるワザ）
                "due": [], "counter_seen": False, "counter_ko": None,
                # v0.11: 「こんじょう」を持つポケモンが相手のワザのダメージを受けたときの特殊状態（ko_able）・決定のあったポケモン（ko_offer）・
                # その結果（declined・declared・heads・tails）・このワザのあとにきぜつしたポケモン（knocked）
                "ko_able": {}, "ko_offer": None, "ko_result": None, "knocked": set(),
                # v0.12: はたらいた「ほのおのかべ」（(場のポケモンの番号, 効果)）・処理中の「ほのおのかべ」（ワザを使ったのは R団のファイヤー）
                "ret_due": [], "ret": None, "ret_seen": False,
                "counter_after_coin": state.effects.attack_entry(_attack_card_id(state, e), e["attack_index"]) is not None
                and state.effects.attack_entry(_attack_card_id(state, e), e["attack_index"]).effect.implementation_id in EFFECT_COIN_AFTER_DAMAGE,
                # v0.46: ワザが使われた時（宣言）にねむり・マヒ・こんらん状態だった場のポケモン（［くつろぐかおり］の「ワザが使われた時、すでに」）
                "status_at_attack": frozenset(exclusive),
            }
        elif kind in ("turn_end", "game_end", "halted"):
            if attack_window is not None and attack_window["ko_offer"] is not None:
                pid, result = attack_window["ko_offer"], attack_window["ko_result"]
                if result == "declared":
                    problems.append(f"{e['turn']} 番の「こんじょう」の宣言（ポケモン {pid}）のあとに結果（ko_prevented・ko_prevention_failed）がない")
                elif result in ("tails", "declined") and pid not in attack_window["knocked"]:
                    problems.append(
                        f"{e['turn']} 番に「こんじょう」が{'「うら」' if result == 'tails' else 'ないまま（使わなかった）'}のポケモン {pid} がきぜつしていない（G11・G19・G34）"
                    )
            attack_window = None
        elif kind == "evade_check":
            pid = e["pokemon_id"]
            source = source_of(e)  # v0.12: 「ほのおのかべ」のダメージ（R団のファイヤーのワザ）の判定もある
            if source is None:
                problems.append(f"{e['turn']} 番の「とうめい」の判定（ポケモン {pid}）が、ワザ（{e['effect']}）の処理の中にない")
            elif pid in source["reception"]:
                problems.append(f"{e['turn']} 番のワザで、ポケモン {pid} の「とうめい」の判定が 2 回以上（1 つのワザにつき 1 回。T4）")
            if pid not in in_play or pokemon_owner.get(pid) != e["player"] or ids.get(e["pokemon"]) != pid:
                problems.append(f"{e['turn']} 番の「とうめい」の判定（ポケモン {pid}）が、判定したプレイヤーの場のポケモンではない（T33）")
            else:
                key, blocked_by = evasion(pid)
                if key is None:
                    problems.append(f"{e['turn']} 番の「とうめい」の判定のポケモン {pid} が、いちばん上のカードに「とうめい」を持っていない")
                elif key != e["power"]:
                    problems.append(f"{e['turn']} 番の「とうめい」の判定の特殊能力 {e['power']} が、ポケモン {pid} の {key} と違う")
                elif blocked_by is not None:
                    problems.append(f"{e['turn']} 番に、{blocked_by} で力が消えている「とうめい」（ポケモン {pid}）の判定がある")
            coin = previous or {}
            if (coin.get("kind"), coin.get("source"), coin.get("player"), coin.get("pokemon_id"), coin.get("effect"), coin.get("result")) != (
                "coin_flip", "power", e["player"], pid, e["power"], e["result"]
            ):
                problems.append(f"{e['turn']} 番の「とうめい」の判定（ポケモン {pid}）の直前に、ゴースト側のプレイヤーの同じ結果のコインがない")
            if e["evaded"] != (e["result"] == "heads") or e["element"] not in ATTACK_ELEMENTS:
                problems.append(f"{e['turn']} 番の「とうめい」の判定（ポケモン {pid}）の結果 {e['result']}・{e['evaded']}・{e['element']} が合わない")
            if source is not None:
                source["reception"].setdefault(pid, not e["evaded"])
            expect = (pid, e["element"], not e["evaded"])
        elif kind == "attack_evaded":
            pid = e["pokemon_id"]
            ret = None if attack_window is None else attack_window["ret"]
            source = ret if ret is not None and e["effect"] == ret["effect"] and pid == attack_window["pokemon_id"] else attack_window
            if source is None or source["reception"].get(pid) is not False or e["effect"] != source["effect"]:
                problems.append(f"{e['turn']} 番のポケモン {pid} の受けなかった要素 {e['element']} の前に、そのワザの「おもて」の判定がない")
            if source is not None and source is ret:
                ret["damage_seen"] = True  # 「ほのおのかべ」のダメージの要素を受けなかった（W19）
            if e["element"] == DAMAGE_ELEMENT and not e.get("amount", 0) > 0:
                problems.append(f"{e['turn']} 番のポケモン {pid} の受けなかったダメージが {e.get('amount')}（0 より大きいはず。T21）")
        elif kind == "damage" and e["amount"] > 0:
            received(e, e.get("pokemon_id", ids.get(e["pokemon"])), DAMAGE_ELEMENT)
        elif kind == "special_condition" and attack_window is not None and e.get("effect") == attack_window["effect"]:
            received(e, e["pokemon_id"], e["condition"], blocked=replaced.get(e["pokemon_id"]))
        elif kind == "forced_switch":
            received(e, e["old_active_pokemon_id"], FORCED_SWITCH_ELEMENT)
        elif kind == "special_condition_prevented" and attack_window is not None and e.get("effect") == attack_window["effect"]:
            received(e, e["pokemon_id"], e["condition"], blocked=replaced.get(e["pokemon_id"]))  # v0.46: 効果を受けて、めんえきで特殊状態にならない
        elif kind == "discard_attached_energy":  # v0.31
            received(e, e["pokemon_id"], ENERGY_DISCARD_ELEMENT)
        elif kind == "attack_attach_energy":
            received(e, e["to_pokemon_id"], ENERGY_ATTACH_ELEMENT)
        elif kind == "persistent_effect_added" and e["persistent_effect"] in (CannotAttack.kind, CannotUseAttack.kind, CannotAttackWhileSourceActive.kind):
            received(e, e["pokemon_id"], ATTACK_LOCK_ELEMENT)  # v0.35: 「ドわすれ」も相手の対戦ポケモンが受ける効果。v0.40: 「すごむ」も
        elif kind == "persistent_effect_added" and e["persistent_effect"] == ReducedDamageToSource.kind:
            received(e, e["pokemon_id"], REDUCED_DAMAGE_ELEMENT)  # v0.34
        elif kind == "persistent_effect_added" and e["persistent_effect"] == AttackCoinCheck.kind:
            received(e, e["pokemon_id"], ATTACK_CHECK_ELEMENT)  # v0.36
        elif kind == "move_opponent_energy":
            received(e, e["pokemon_id"], ENERGY_MOVE_ELEMENT)  # v0.45: はがすのは相手の対戦ポケモンへの効果、つけるのは控えへの効果
            if e["result"] == "attached":
                received(e, e["to_pokemon_id"], ENERGY_ATTACH_ELEMENT)
        elif kind == "persistent_effect_added" and e["persistent_effect"] == CannotRetreat.kind:
            received(e, e["pokemon_id"], RETREAT_LOCK_ELEMENT)  # v0.36
        elif kind == "return_in_play_to_deck":
            received(e, e["pokemon_id"], RETURN_IN_PLAY_TO_DECK_ELEMENT)  # v0.36
        elif kind == "attack_heal":
            received(e, e["pokemon_id"], HEAL_ELEMENT)  # v0.41: ワザでダメージカウンターをとりのぞく効果（自分・控え・相手のポケモン）
        elif kind == "place_damage_counters":
            received(e, e["pokemon_id"], COUNTERS_ELEMENT)  # v0.41: ダメージカウンターをのせる効果（ダメージシフト）
        elif kind == "swap_damage_counters":
            received(e, e["opponent_pokemon_id"], COUNTERS_ELEMENT)  # v0.41: ダメージカウンターを取り替える効果（チェンジダメージ）
        elif kind == "evolve" and "effect" in e:
            received(e, e["pokemon_id"], EVOLVE_ELEMENT)  # v0.42: つきのちから（自分の場のポケモンへの効果）
        elif kind == "return_in_play_to_hand" and "effect" in e:
            received(e, e["pokemon_id"], RETURN_IN_PLAY_TO_HAND_ELEMENT)  # v0.42: ようせいのきせき
        if kind == "copy_attack" and attack_window is not None:
            attack_window["copied"] = e["copied"]  # v0.44: 相手のワザを自分のワザとして使った（そのワザの効果のログの effect は copied）
        if kind == "damage" and attack_window is not None and not e.get("retaliation"):
            problems.extend(attack_damage_set_problems(e))  # v0.27
        if kind == "damage" and attack_window is not None:
            problems.extend(zero_damage_below_problems(e))  # v0.45
            problems.extend(continuous_damage_problems(e))  # v0.46
        if kind == "confusion_damage" and attack_window is not None:
            # v0.46: こんらんの 20 に当てはまりうる常にはたらく特殊能力（くつろぐかおり・きょうぼう・なぞのかべ・ふしぎなバリアー）がはたらいていれば、コインの前に
            # 止まる（UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS）ので、こんらんのダメージはない
            found = continuous_expected(e["pokemon_id"], e["pokemon_id"], attack_window["status_at_attack"])
            if [x for x in found if x[1].count("［")]:
                problems.append(f"{e['turn']} 番のこんらんのダメージ（ポケモン {e['pokemon_id']}）に当てはまりうる常にはたらく特殊能力 {[x[1] for x in found]} がはたらいている")
        if kind == "special_condition" and replaced.get(e["pokemon_id"]) is None and working_continuous(e["pokemon_id"], SpecialConditionImmunity):
            # v0.46: はたらいている［めんえき］のポケモンは、特殊状態にならない（付ける前の、置きかえる前のねむり・マヒ・こんらんで使えないときを除く）
            problems.append(f"{e['turn']} 番に、はたらいている特殊状態にならない特殊能力を持つポケモン {e['pokemon_id']} が {e['condition']} 状態になった")
        if kind == "special_conditions_removed" and e["reason"] == "replaced":
            replaced[e["pokemon_id"]] = exclusive.get(e["pokemon_id"])
        elif kind == "special_condition":
            replaced.pop(e["pokemon_id"], None)
        previous = e

        if kind == "turn_start":
            turn_player = e["player"]
            current_turn = e["turn"]  # v0.48
            attached_this_turn = power_attached_this_turn = 0
        if kind == "draw":
            hand[e["player"]].extend(e["cards"])
        elif kind == "mulligan":
            if sorted(e["revealed_hand"]) != sorted(hand[e["player"]]):
                problems.append(f"プレイヤー {e['player']} の切り直しで見せた手札が、ログから組み立てた手札と違う")
            hand[e["player"]] = []
        elif kind == "play_trainer":
            # v0.46: はたらいている［アレルギーかふん］（場のどこでも。ねむり・マヒ・こんらん・かがくへんかガスで消える）があれば、誰もトレーナーカードを使えない
            locked = [pid for pid in sorted(in_play) if working_continuous(pid, PreventTrainerUse)]
            if locked:
                problems.append(f"{e['turn']} 番に、はたらいているトレーナーカードを使えなくする特殊能力（ポケモン {locked}）があるのに、トレーナー {e['card']} を使った")
            # v0.47: 期限のあるトレーナーの使用の禁止（ずつう・こうしゅうは。与えた番の次の番から、消える番まで）を受けているプレイヤーは使えない
            banned = [key for key, info in trainer_locks_log.items() if key[0] == e["player"] and info["turn"] < e["turn"] <= key[1]]
            if banned:
                problems.append(f"{e['turn']} 番に、トレーナーの使用を禁止されている（{banned}）プレイヤー {e['player']} が、トレーナー {e['card']} を使った")
            from_hand(e, e["player"], e["card"])
            using_trainer[e["player"]] = e["card"]
        if kind == "place_starting_pokemon":
            for uid in (e["active"], *e["bench"]):
                from_hand(e, e["player"], uid)
                enter(uid)
            active_of[e["player"]] = ids[e["active"]]  # v0.46
        elif kind == "play_to_bench":
            from_hand(e, e["player"], e["card"])
            enter(e["card"])
        elif kind == "evolve":
            shifts.pop(e["pokemon_id"], None)  # v0.48: 進化したら［へんしょく］の記録は消える（別のポケモン。p.310）
            # v0.47: はたらいている［げんしのちから］（場のどこでも。ねむり・マヒ・こんらん・かがくへんかガスで消える）があれば、どの方法でも進化できない。重ねる前の場で求める
            preventing = [pid for pid in sorted(in_play) if working_continuous(pid, PreventEvolution)]
            if preventing:
                problems.append(f"{e['turn']} 番に、はたらいている進化できなくする特殊能力（ポケモン {preventing}）があるのに、ポケモン {e['pokemon_id']} が進化した")
            # v0.25: 通常の進化は「○○○○から進化」の名前が進化前のカードの名前（p.309・p.324）。trainer_card のある進化（ポケモン育て屋さん）は、
            # 使っている最中の 1 進化を飛ばして進化させるトレーナーの効果で、たねポケモンに系統の合う 2 進化カードを重ねた（p.259）
            below, upper, via = state.in_play_def(e["from_card"]), state.in_play_def(e["to_card"]), e.get("trainer_card")
            if via is None:
                if upper.evolves_from != below.name_ja:
                    problems.append(f"{e['turn']} 番の進化（{e['from_card']} → {e['to_card']}）で、{upper.name_ja} の進化元 {upper.evolves_from!r} が {below.name_ja} ではない")
            else:
                entry = state.effects.trainer_entry(state.cards[via].card_id) if via in state.cards else None
                if (entry is None or not entry.effect.skips_stage1_evolution or using_trainer.get(e["player"]) != via
                        or not below.is_basic_pokemon or skipped_stage1_basic(upper) != below.name_ja):
                    problems.append(
                        f"{e['turn']} 番の 1 進化を飛ばした進化（{e['from_card']} → {e['to_card']}、trainer_card {via!r}）が、使っている最中の"
                        "トレーナーの効果で、たねポケモンに系統の合う 2 進化カードを重ねたものではない"
                    )
            if e.get("source_zone") == "deck":
                # v0.42: ワザ（つきのちから）で、ワザを使ったプレイヤーの山札の進化カードを、手札を通さずに重ねた（山札は組み立て直さないので、持ち主・手札・
                # トラッシュ・場にないことで確かめる）。すぐあとに（進化の手順のログのあと）山札を切る
                uid = e["to_card"]
                if "power" in e:
                    # v0.44: ［うか］（特殊能力）。直前に持ち主の「おもて」のコイン（そのあいだに決定がある）。重ねるのは説明の名前のカード
                    effect = _power_effect(state, e["power"])
                    valid = isinstance(effect, CoinEvolveSelfFromDeck) and state.printed_def(uid).name_ja == effect.name \
                        and e["power"].partition("@power")[0] == state.cards[e["from_card"]].card_id
                else:
                    # v0.44: たきのぼりしんか（EvolveSelfFromDeck。ワザを使ったポケモン自身を、説明の名前から進化するカードで進化させる）
                    valid = _same_attack(attack_window, e) and e["player"] == attack_window["player"] \
                        and isinstance(_effect_of_event(state, e), (EvolveFromDeckOnHeads, EvolveSelfFromDeck))
                if not valid or owner.get(uid) != e["player"] \
                        or uid in hand[e["player"]] or uid in discard[e["player"]] or uid in ids or pokemon_owner.get(e["pokemon_id"]) != e["player"]:
                    problems.append(f"{e['turn']} 番に山札から重ねた進化カード {uid} が、そのワザ（山札から進化させるワザ）の処理・山札のカードではない")
                shuffle_due = e
            else:
                from_hand(e, e["player"], e["to_card"])
            ids[e["to_card"]] = e["pokemon_id"]
            top[e["pokemon_id"]] = e["to_card"]
            before = evolve_turns.get(e["pokemon_id"], [])
            if before and before[-1] == e["turn"] and (e["pokemon_id"], e["turn"]) not in permitted:
                # v0.44: 同じ番の 2 回目の進化は、その前にトレーナー「サカキ」の許可（evolution_permission）があるときだけ
                problems.append(f"{e['turn']} 番に場のポケモン {e['pokemon_id']} を同じ番に 2 回進化させた（サカキの許可がない）")
            evolve_turns.setdefault(e["pokemon_id"], []).append(e["turn"])
            key = entry_opportunity(e["to_card"], from_hand="source_zone" not in e)
            if key is not None:
                entry_due = (e["turn"], e["pokemon_id"], key)  # v0.43: 場に出たときの特殊能力の使う機会
        elif kind in ("counterattack", "counterattack_skipped"):
            # v0.10: 「はんげき」のダメージ（ワザを使ったポケモンへ。ワザによるダメージではない）
            target = e["attacker_pokemon_id"]
            if source_of(e) is None:
                # v0.12: 「ほのおのかべ」のダメージ（R団のファイヤーのワザ）を受けたポケモンの「はんげき」は、R団のファイヤーに与える
                problems.append(f"{e['turn']} 番の「はんげき」（ポケモン {e['pokemon_id']}）が、ダメージを与えたワザの処理の中にない（与える相手はワザを使ったポケモン）")
            amount = None
            if attack_window is not None:
                attack_window["counter_seen"] = True
                if not attack_window["due"]:
                    problems.append(f"{e['turn']} 番の「はんげき」（ポケモン {e['pokemon_id']}）が、はたらく理由（相手のワザのダメージを、はたらいている「はんげき」で受けた）なしにある")
                else:
                    pid, key, amount = attack_window["due"].pop(0)
                    if (e["pokemon_id"], e["power"]) != (pid, key) or ids.get(e["pokemon"]) != pid or e["player"] != pokemon_owner.get(pid):
                        problems.append(f"{e['turn']} 番の「はんげき」が、ダメージを受けたポケモン {pid} の {key} ではない（{e['pokemon_id']}・{e['power']}）")
            if target not in in_play:
                problems.append(f"{e['turn']} 番の「はんげき」を与える相手 {target} が場にいない")
                continue
            hp = max_hp_now(target)
            if kind == "counterattack_skipped":
                if e["reason"] != "knocked_out" or damage[target] < hp:
                    problems.append(f"{e['turn']} 番に、きぜつしていない相手 {target}（ダメージ {damage[target]}）に「はんげき」を与えなかった（{e['reason']}）")
                continue
            if damage[target] >= hp:
                problems.append(f"{e['turn']} 番に、すでに HP 以上のダメージの相手 {target} に「はんげき」を与えた（対象がいない。C15）")
            if amount is not None:
                # v0.46: 受けるポケモン（ワザを使ったポケモン）の、受けるダメージを変える常にはたらく特殊能力（ふしぎなバリアー・なぞのかべ）を当てはめた量
                problems.extend(received_power_problems(e, target, e["pokemon_id"], amount))
            damage[target] += e["amount"]
            if damage[target] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の counterattack のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[target]} と違う")
            if e["knocked_out"] != (damage[target] >= hp):
                problems.append(f"{e['turn']} 番の「はんげき」のきぜつの印 {e['knocked_out']} が、ログから組み立てたダメージ {damage[target]} と合わない")
            if damage[target] >= hp and attack_window is not None:
                attack_window["counter_ko"] = target
        elif kind in ("retaliation", "retaliation_skipped"):
            # v0.12: 「ほのおのかべ」（相手のワザによるダメージを受けたとき、ダメージを与えた相手の対戦ポケモンに 10。R団のファイヤーのワザ）
            holder, target = e["pokemon_id"], e["attacker_pokemon_id"]
            if attack_window is None or (e["trigger"], e["attacker"], target) != (
                attack_window["effect"], attack_window["player"], attack_window["pokemon_id"]
            ):
                problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」（ポケモン {holder}）が、ダメージを与えたワザの処理の中にない（W14）")
                continue
            if not attack_window["ret_due"] or attack_window["ret_due"][0][0] != holder:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」（ポケモン {holder}）が、はたらく理由（相手のワザのダメージを、効果がはたらいているポケモンが受けた）なしにある（W4・W11・W13）")
                info, received_damage = active_retaliation(holder, e["turn"]), None
            else:
                _, info, received_damage = attack_window["ret_due"].pop(0)
            if info is None or pokemon_owner.get(holder) != e["player"] or ids.get(e["pokemon"]) != holder or info["source_card"] != e["source_card"]:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」（ポケモン {holder}）に、今の番にはたらく効果（ログの persistent_effect_added）がない（W4・W5）")
            elif e["effect"] != info["effect"]:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」のワザ {e['effect']} が、効果を与えたワザ {info['effect']} と違う")
            if target not in in_play:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」を与える相手 {target} が場にいない")
                continue
            hp = max_hp_now(target)
            entry = state.effects.attack_entry(*_attack_key(e["effect"]))
            terms = getattr(entry.effect, "retaliation_terms", None) if entry is not None else None
            # v0.45: 倍数とはたらくときのコインのある効果（クロスカウンター）は 4 つの値（v0.44 までの効果は 2 つ）
            basis, fixed, multiplier, on_heads = (tuple(terms()) + (1, False))[:4] if terms is not None else (None, None, 1, False)
            scaled = multiplier != 1 or on_heads
            coin = prior or {}
            heads_coin = (coin.get("kind"), coin.get("source"), coin.get("player"), coin.get("pokemon_id"), coin.get("effect")) == (
                "coin_flip", "attack", e["player"], holder, e["effect"])
            if kind == "retaliation_skipped":
                if e["reason"] == RETALIATION_COIN_TAILS:
                    # v0.45: クロスカウンターのコインが「うら」（与えない）。直前に効果を持つポケモンの持ち主の「うら」のコインがある
                    if not on_heads or not heads_coin or coin.get("result") != "tails" or e.get("received_damage") != received_damage \
                            or damage[target] >= hp:
                        problems.append(f"{e['turn']} 番のクロスカウンターの「うら」（ポケモン {holder}）の直前に持ち主の「うら」のコインがない・受けたダメージが合わない")
                elif e["reason"] != "knocked_out" or damage[target] < hp:
                    problems.append(f"{e['turn']} 番に、きぜつしていない相手 {target}（ダメージ {damage[target]}）に「ほのおのかべ」・「こうらがえし」を与えなかった（{e['reason']}）")
                elif coin.get("kind") == "coin_flip" and coin.get("effect") == e["effect"] and coin.get("pokemon_id") == holder:
                    problems.append(f"{e['turn']} 番に、すでに HP 以上の相手 {target} への返す効果のコインを投げた（C15）")
                continue
            if damage[target] >= hp:
                problems.append(f"{e['turn']} 番に、すでに HP 以上のダメージの相手 {target} に「ほのおのかべ」・「こうらがえし」を与えた（対象がいない。W23）")
            expected_kind = RETALIATION_RECEIVED_SCALED_KIND if scaled else RETALIATION_KINDS.get(basis)
            if info is not None and basis is not None and info["kind"] != expected_kind:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」の効果の種類 {info['kind']} が、ワザ {e['effect']} の登録と違う")
            if on_heads and (not heads_coin or coin.get("result") != "heads" or e.get("coin") != "heads"):
                problems.append(f"{e['turn']} 番のクロスカウンター（ポケモン {holder}）の直前に、持ち主の「おもて」のコインがない（LD-PMCG5-054-ATK0）")
            if scaled:
                # v0.45: 基本となるダメージは、受けたダメージ（きっかけのダメージのログの最終ダメージ）の multiplier 倍
                if (e.get("basis"), e.get("received_damage"), e.get("multiplier")) != (basis, received_damage, multiplier) \
                        or received_damage is None or e["amount"] != received_damage * multiplier:
                    problems.append(f"{e['turn']} 番のクロスカウンターの量 {e['amount']}（{e.get('received_damage')}・{e.get('multiplier')}）が、受けたダメージ"
                                    f" {received_damage} の {multiplier} 倍と違う")
            elif basis == RETALIATION_FIXED:
                if e["amount"] != fixed or "basis" in e or "received_damage" in e:
                    problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」の量 {e['amount']} が、ワザ {e['effect']} の登録と違う（W14）")
            elif basis == RETALIATION_RECEIVED:
                # v0.13: 「こうらがえし」。基本となるダメージは、きっかけのダメージのログの最終ダメージ（受けたダメージ）と同じ（S9・S10）
                if (e.get("basis"), e.get("received_damage")) != (basis, received_damage) or e["amount"] != received_damage \
                        or "multiplier" in e or "coin" in e:
                    problems.append(
                        f"{e['turn']} 番の「こうらがえし」の量 {e['amount']}（{e.get('basis')}・{e.get('received_damage')}）が、受けたダメージ"
                        f" {received_damage} と違う（S9・S10）"
                    )
            else:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」のワザ {e['effect']} に、ダメージを返す効果が登録されていない（W14）")
            attack_window["ret"] = {
                "effect": e["effect"], "player": e["player"], "pokemon_id": holder, "reception": {}, "amount": e["amount"], "damage_seen": False,
            }
            attack_window["ret_seen"] = True
        elif kind == "persistent_effect_skipped":
            # v0.12: ワザを使ったポケモンが相手の「はんげき」で HP 以上になったので、自分に与える持続する効果を与えなかった
            pid = e["pokemon_id"]
            if attack_window is None or pid != attack_window["pokemon_id"] or pid not in in_play or damage[pid] < max_hp_now(pid):
                problems.append(f"{e['turn']} 番に、きぜつしていないポケモン {pid} の持続する効果（{e['persistent_effect']}）を与えなかった")
        elif kind == "return_to_hand":
            # v0.12: 「ふしちょう」でトラッシュから手札に加えたカード（きぜつしたポケモンのカード 1 枚だけ。P22〜P24）
            if e["card"] not in discard[e["player"]] or owner.get(e["card"]) != e["player"] or state.printed_def(e["card"]).category != "pokemon":
                problems.append(f"{e['turn']} 番に手札に加えたカード {e['card']} が、ログから組み立てたプレイヤー {e['player']} のトラッシュのポケモンのカードにない")
            else:
                discard[e["player"]].remove(e["card"])
                hand[e["player"]].append(e["card"])
        elif kind in ("ko_prevention_declined", "ko_prevention_declared", "ko_prevented", "ko_prevention_failed"):
            # v0.11: 相手のワザによるダメージで「きぜつ」するときに使える特殊能力（サカキのカイリキーの「こんじょう」）
            pid = e["pokemon_id"]
            if attack_window is None:
                problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）が、相手のワザのあとのきぜつの判定の中にない（G3・G7）")
                continue
            by_attacker = e["player"] == attack_window["player"]  # v0.12: 「ほのおのかべ」のダメージで HP 以上になったワザを使ったポケモン
            if pid not in in_play or ids.get(e["pokemon"]) != pid or pokemon_owner.get(pid) != e["player"] or (
                by_attacker and (pid != attack_window["pokemon_id"] or attack_window["ret"] is None)
            ):
                problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）が、相手のワザ（「ほのおのかべ」・「こうらがえし」を含む）のダメージを受けた場のポケモンではない（G4・G15）")
                continue
            gkey, geffect, gpower = guts_power(pid)
            hp = max_hp_now(pid)
            if gkey is None or gkey != e["power"]:
                problems.append(f"{e['turn']} 番の「こんじょう」の {kind} の特殊能力 {e['power']} が、ポケモン {pid} のいちばん上のカードの「こんじょう」ではない")
                continue
            if kind in ("ko_prevention_declined", "ko_prevention_declared"):
                if attack_window["ko_offer"] is not None:
                    problems.append(f"{e['turn']} 番のワザで、「こんじょう」を使うかの決定が 2 回以上（ポケモン {attack_window['ko_offer']}・{pid}。G14）")
                if attack_window["knocked"]:
                    problems.append(f"{e['turn']} 番のワザで、きぜつの処理（ポケモン {sorted(attack_window['knocked'])}）のあとに「こんじょう」の {kind} がある（G32）")
                attack_window["ko_offer"] = pid
                attack_window["ko_result"] = "declined" if kind == "ko_prevention_declined" else "declared"
                if pid not in attack_window["ko_able"]:
                    problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）の前に、そのワザのダメージを受けたログがない（G3〜G7）")
                elif attack_window["ko_able"][pid] is not None:
                    problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）: ダメージを受けるとき {attack_window['ko_able'][pid]} 状態だった（使えない。G25〜G27）")
                gases = [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(gpower)]
                if gases:
                    problems.append(f"{e['turn']} 番に、はたらいている「かがくへんかガス」（ポケモン {gases}）に消されている「こんじょう」（ポケモン {pid}）の {kind} がある（G31）")
                if damage[pid] < hp:
                    problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）: ログから組み立てたダメージ {damage[pid]} が HP {hp} 未満（G2）")
                if e["total_damage"] != damage[pid]:
                    problems.append(f"{e['turn']} 番の {kind} のダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
                continue
            coin = prior or {}
            if attack_window["ko_offer"] != pid or attack_window["ko_result"] != "declared":
                problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）の前に、そのワザでの宣言（ko_prevention_declared）がない")
            attack_window["ko_result"] = "heads" if kind == "ko_prevented" else "tails"
            if (coin.get("kind"), coin.get("source"), coin.get("player"), coin.get("pokemon_id"), coin.get("effect"), coin.get("result")) != (
                "coin_flip", "power", e["player"], pid, e["power"], e["result"]
            ) or e["result"] != attack_window["ko_result"]:
                problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）の直前に、持ち主の同じ結果のコインがない・結果が合わない（G15・G17〜G19）")
            if damage[pid] < hp:
                problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）: ログから組み立てたダメージ {damage[pid]} が HP {hp} 未満")
            if kind == "ko_prevented":
                if e["damage_before"] != damage[pid]:
                    problems.append(f"{e['turn']} 番の ko_prevented の前のダメージ {e['damage_before']} が、ログから組み立てた {damage[pid]} と違う")
                damage[pid] = e["total_damage"]
                if e["total_damage"] != hp - geffect.remaining_hp or e.get("remaining_hp") != geffect.remaining_hp:
                    problems.append(f"{e['turn']} 番の「こんじょう」の「おもて」のあとのダメージ {e['total_damage']} が、残り HP {geffect.remaining_hp}（ダメージ {hp - geffect.remaining_hp}）ではない（G18・G20）")
            elif e["total_damage"] != damage[pid]:
                problems.append(f"{e['turn']} 番の ko_prevention_failed のダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う（「うら」はダメージを変えない。G19）")
        elif kind in ("damage", "poison_damage", "confusion_damage", "drain_heal", "remove_damage_counters", "remove_all_damage_counters"):
            pid = e["pokemon_id"] if "pokemon_id" in e else ids[e["pokemon"]]
            if kind == "drain_heal":
                # v0.32: とりのぞく数は登録の実装で決まる（メガドレインは与えたダメージの半分の切り上げ、やどりぎのタネは決まった数、きゅうけつは与えたぶん）。
                # 実際にとりのぞくのは、のっている数まで
                per = state.rules.damage_per_counter
                entry = state.effects.attack_entry(*_attack_key(e["effect"]))
                effect = entry.effect if entry is not None else None
                expected = (e["dealt"] // per if isinstance(effect, DamageAndFullDrain) else (e["dealt"] // per + 1) // 2 if isinstance(effect, DamageAndDrain)
                            else effect.counters if isinstance(effect, DamageAndRemoveCounters) else None)
                if expected is None or e["drain_counters"] != expected or e["dealt"] <= 0 \
                        or e["counters"] != min(e["drain_counters"], damage[pid] // per) or e["amount"] != e["counters"] * per:
                    problems.append(f"{e['turn']} 番の drain_heal（ワザ {e['effect']}・与えたダメージ {e['dealt']}）のとりのぞく数 {e['drain_counters']}・{e['counters']} が"
                                    f"登録の実装 {type(effect).__name__} と合わない（ログのダメージ {damage[pid]}）")
            if kind in ("drain_heal", "remove_all_damage_counters"):
                damage[pid] -= e["amount"]
            elif kind == "remove_damage_counters":
                damage[pid] -= e["counters"] * state.rules.damage_per_counter
            else:
                damage[pid] += e["amount"]
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の {kind} のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind == "attach_energy":
            from_hand(e, e["player"], e["energy"])
            energy[ids[e["target"]]].append(e["energy"])
            attached_this_turn += 1
            if attached_this_turn > state.rules.energy_attachments_per_turn:
                problems.append(f"{e['turn']} 番に手札からエネルギーをつける通常の操作が {attached_this_turn} 回")
            if attached_this_turn == 1 and power_attached_this_turn:
                # v0.6 の R13（原典で決められない。エンジンは UNRESOLVED_ATTACH_AFTER_POWER_ATTACH で止める）
                problems.append(f"{e['turn']} 番に、特殊能力で手札からつけたあとで通常の操作でつけた（R13 は止めるはず）")
        elif kind == "pokemon_power":
            declared = (e["turn"], e["player"], e["pokemon_id"])
            power_card = e.get("card", top.get(e["pokemon_id"]))  # v0.49: のせたカードの特殊能力ならそのカード（ログの card）
            declared_key = f"{state.cards[power_card].card_id}@power{e['power_index']}" if power_card is not None else None
            if e["player"] != turn_player or pokemon_owner.get(e["pokemon_id"]) != e["player"] or e["pokemon_id"] not in in_play:
                problems.append(f"{e['turn']} 番の特殊能力の宣言（ポケモン {e['pokemon_id']}）が、番のプレイヤーの場のポケモンではない")
                continue
            # v0.8: 宣言した時点の場で、宣言しない特殊能力でないこと・はたらいているかがくへんかガスに消されていないこと
            definition = state.in_play_def(power_card)
            if power_card != top[e["pokemon_id"]] and disguised.get(e["pokemon_id"]) != power_card:
                problems.append(f"{e['turn']} 番の特殊能力の宣言のカード {power_card}（ポケモン {e['pokemon_id']}）が、いちばん上のカードでも「ばける」でのせたカードでもない")
            power = definition.powers[e["power_index"]] if 0 <= e["power_index"] < len(definition.powers) else None
            if power is None or power.name_ja != e["power"]:
                problems.append(f"{e['turn']} 番の特殊能力の宣言 {e['power']!r} が、ポケモン {e['pokemon_id']} のいちばん上のカードの特殊能力ではない")
                continue
            effect = state.effects.power_effect(definition.id, power)
            if effect is not None and not effect.declared:
                problems.append(f"{e['turn']} 番に、常にはたらいていて宣言しない特殊能力「{power.name_ja}」の宣言がある")
            if ("entry" in e) != isinstance(effect, EntryPower):
                # v0.43: 場に出たときの特殊能力は、使う機会の答えとしてだけ宣言する（番の中の宣言（UsePokemonPower）では使えない）
                problems.append(f"{e['turn']} 番の特殊能力「{power.name_ja}」の宣言の entry {e.get('entry')!r} が、場に出たときの特殊能力かと合わない")
            gases = [pid for pid, gas in working_gases() if gas.suppresses(power)]
            if gases:
                problems.append(f"{e['turn']} 番に、はたらいている「かがくへんかガス」（ポケモン {gases}）に消されている特殊能力「{power.name_ja}」を使った")
            continue
        elif kind == "entry_power_declined":
            # v0.43: 場に出たときの特殊能力を使わなかった（使う機会の答え。番のプレイヤーの場のポケモン）
            definition = state.in_play_def(top[e["pokemon_id"]]) if e["pokemon_id"] in top else None
            power = definition.powers[e["power_index"]] if definition is not None and 0 <= e["power_index"] < len(definition.powers) else None
            if power is None or power.name_ja != e["power"] or not isinstance(state.effects.power_effect(definition.id, power), EntryPower) \
                    or e["player"] != turn_player or pokemon_owner.get(e["pokemon_id"]) != e["player"]:
                problems.append(f"{e['turn']} 番の entry_power_declined（ポケモン {e['pokemon_id']}）が、番のプレイヤーの場に出たときの特殊能力ではない")
        elif kind == "power_damage":
            # v0.43: こっそりかみつく。相手の場のポケモン 1 匹に、特殊能力によるダメージ（ワザによるダメージの計算をしない。登録の量）。HP 以上になったら、すぐあとに
            # timing power のきぜつ
            effect = _power_effect(state, e["power"])
            target = e["target_pokemon_id"]
            if not isinstance(effect, DamageOpponentPokemonOnEntry) or target not in in_play \
                    or pokemon_owner.get(target) != 1 - e["player"] or e["target_player"] != 1 - e["player"] or pokemon_owner.get(e["pokemon_id"]) != e["player"]:
                problems.append(f"{e['turn']} 番の power_damage（{e['power']} → ポケモン {target}）が、場に出たときに相手の場のポケモンにダメージを与える特殊能力の処理と合わない")
            else:
                problems.extend(received_power_problems(e, target, e["pokemon_id"], effect.amount))  # v0.46
                damage[target] += e["amount"]
                if damage[target] != e["total_damage"] or (damage[target] >= max_hp_now(target)) != e["knocked_out"]:
                    problems.append(f"{e['turn']} 番の power_damage のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[target]} と違う")
                if damage[target] >= max_hp_now(target):
                    power_ko_due = target
        elif kind in ("recover_pokemon", "recover_pokemon_none"):
            # v0.43: つりあげる。自分のトラッシュのポケモンのカード（同じカードは 1 回まで・最大 3 枚）を見せて手札に加える。加えるものがないのは、トラッシュに
            # ポケモンのカードがないときだけ
            effect = _power_effect(state, e["power"])
            player = e["player"]
            cards = tuple(e.get("cards", ()))
            if not isinstance(effect, RecoverPokemonFromDiscardOnEntry) or pokemon_owner.get(e["pokemon_id"]) != player:
                problems.append(f"{e['turn']} 番の {kind} の特殊能力 {e['power']} が、トラッシュのポケモンのカードを手札に加える特殊能力ではない")
            elif kind == "recover_pokemon_none":
                if any(state.printed_def(uid).category == "pokemon" for uid in discard[player]):
                    problems.append(f"{e['turn']} 番の recover_pokemon_none のとき、ログから組み立てたトラッシュにポケモンのカードがある")
            elif not 1 <= len(cards) <= effect.max_cards or len(set(cards)) != len(cards) or any(
                    uid not in discard[player] or owner.get(uid) != player or state.printed_def(uid).category != "pokemon" for uid in cards):
                problems.append(f"{e['turn']} 番に手札に加えたカード {cards} が、ログから組み立てたトラッシュのポケモンのカード（最大 {effect.max_cards} 枚）ではない")
            else:
                for uid in cards:
                    discard[player].remove(uid)
                    hand[player].append(uid)
        elif kind == "special_condition_prevented":
            # v0.46: ［めんえき］で特殊状態にならなかった（状態は変わらない）。バトル場のポケモンで、その時点ではたらいている特殊能力
            powers = [key for key, _, _ in working_continuous(e["pokemon_id"], SpecialConditionImmunity)]
            if not is_active(e["pokemon_id"]) or e["power"] not in powers or e["condition"] not in ("poison", "sleep", "paralysis", "confusion") \
                    or pokemon_owner.get(e["pokemon_id"]) != e["player"]:
                problems.append(f"{e['turn']} 番の special_condition_prevented（ポケモン {e['pokemon_id']}・{e['power']}）が、はたらいている［めんえき］を持つバトル場のポケモンではない")
        elif kind == "attach_energy_from_hand":
            # v0.46: せいちょう。コインの「おもて」のあと、ワザを使ったプレイヤーの手札の、登録のタイプの基本エネルギーカード（1〜最大枚数）をワザを使ったポケモンにつける
            # （手札からつける通常の操作・特殊能力でつけた枚数には数えない）
            effect = _effect_of_event(state, e) if attack_window is not None else None
            cards = tuple(e["cards"])
            heads = prior is not None and prior["kind"] == "coin_flip" and prior["source"] == "attack" and prior["result"] == "heads"
            if not isinstance(effect, AttachEnergyFromHandOnHeads) or e["pokemon_id"] != attack_window["pokemon_id"] or e["player"] != attack_window["player"] \
                    or not heads or not 1 <= len(cards) <= effect.max_cards or len(set(cards)) != len(cards) \
                    or any(not state.printed_def(uid).is_basic_energy or state.printed_def(uid).provides is not effect.energy_type for uid in cards):
                problems.append(f"{e['turn']} 番の attach_energy_from_hand（{cards}）が、コインの「おもて」のあとに手札の基本エネルギーカードをつけるワザの処理と合わない")
            for uid in cards:
                from_hand(e, e["player"], uid)
                energy.setdefault(e["pokemon_id"], []).append(uid)
        elif kind == "special_condition":
            # v0.8: ねむり・マヒ・こんらんは重複しない（ほかのものは、その前に special_conditions_removed（replaced）で消える）
            if e["condition"] in ("sleep", "paralysis", "confusion") and not e.get("already"):
                if e["pokemon_id"] in exclusive:
                    problems.append(f"{e['turn']} 番に、{exclusive[e['pokemon_id']]} のポケモン {e['pokemon_id']} が、それを消さずに {e['condition']} になった")
                exclusive[e["pokemon_id"]] = e["condition"]
            if e["condition"] == "poison":
                problems.extend(_poison_problems(state, e, poisoned.get(e["pokemon_id"])))
                poisoned[e["pokemon_id"]] = e.get("damage")
        elif kind == "special_conditions_removed":
            if exclusive.get(e["pokemon_id"]) in e["conditions"]:
                del exclusive[e["pokemon_id"]]
            if "poison" in e["conditions"]:
                poisoned.pop(e["pokemon_id"], None)
        elif kind == "poison_damage":
            # v0.34: ポケモンチェックのどくのダメージは、そのポケモンのどくの量（通常 10・特殊などくはその量。p.322・p.323）
            # 盤面を直接作ったテスト（build_test_state）は、どく状態にしたログがないので、ログで組み立てたどくだけを確かめる
            if e["pokemon_id"] in poisoned and poisoned[e["pokemon_id"]] != e["amount"]:
                problems.append(f"{e['turn']} 番のポケモン {e['pokemon_id']} のどくのダメージ {e['amount']} が、ログから組み立てたどくの量 {poisoned.get(e['pokemon_id'])} と違う")
        elif kind == "move_energy":
            # v0.5: 特殊能力（エナジートランス）で、同じ uid のエネルギーを移動元から移動先へ（トラッシュには置かない）
            effect = _power_effect(state, e.get("power"))
            continuing = moving is not None and moving[:4] == (e["turn"], e["player"], e["pokemon_id"], e.get("power"))
            if declared != (e["turn"], e["player"], e["pokemon_id"]) and not continuing:
                problems.append(f"{e['turn']} 番のエネルギーの移動 {e['energy']} の直前に、同じポケモンの特殊能力の宣言（pokemon_power）がない")
            declared = None  # 1 回の宣言で 1 枚（v0.5 のエナジートランス）
            if isinstance(effect, (TakeEnergiesToSelf, ChargeBenchEnergyToSelf)):
                # v0.43: ようぶんきゅうしゅう（最大 2 枚）・エナジーチャージ（好きなだけ）は 1 回の宣言で何枚も（続けて move_energy）
                moving = (e["turn"], e["player"], e["pokemon_id"], e.get("power"), moving[4] + 1 if continuing else 1)
                if isinstance(effect, TakeEnergiesToSelf) and moving[4] > effect.max_cards:
                    problems.append(f"{e['turn']} 番のようぶんきゅうしゅう（ポケモン {e['pokemon_id']}）で、1 回に {moving[4]} 枚つけかえた")
            source, target = e["from_pokemon_id"], e["to_pokemon_id"]
            if isinstance(effect, (TakeEnergyToSelf, TakeEnergiesToSelf, ChargeBenchEnergyToSelf)) and (
                    target != e["pokemon_id"] or not state.printed_def(e["energy"]).is_basic_energy or state.printed_def(e["energy"]).provides is not effect.energy_type):
                # v0.43: つける先は特殊能力を使ったポケモン（このカード）。つけかえるのは登録のタイプの基本エネルギーカード
                problems.append(f"{e['turn']} 番のエネルギーの移動 {e['energy']}（{source} → {target}）が、特殊能力 {e.get('power')} のつけかえ（このカードに・"
                                "登録のタイプの基本エネルギーカード）ではない")
            if pokemon_owner.get(source) != e["player"] or pokemon_owner.get(target) != e["player"] or owner.get(e["energy"]) != e["player"]:
                problems.append(f"{e['turn']} 番のエネルギーの移動 {e['energy']}（{source} → {target}）が、自分の場のポケモンのあいだではない")
            if source == target or source not in in_play or target not in in_play or e["energy"] not in energy.get(source, []):
                problems.append(f"{e['turn']} 番のエネルギーの移動 {e['energy']}（{source} → {target}）が、ログから組み立てた場と合わない")
            else:
                energy[source].remove(e["energy"])
                energy[target].append(e["energy"])
        elif kind == "power_attach_energy":
            # v0.6: 特殊能力（あまごい）で、手札の同じ uid のエネルギーカードを自分の場のポケモンへ
            if declared != (e["turn"], e["player"], e["pokemon_id"]):
                problems.append(f"{e['turn']} 番の手札からのエネルギー {e['energy']} の直前に、同じポケモンの特殊能力の宣言（pokemon_power）がない")
            declared = None  # 1 回の宣言で 1 枚（v0.6 のあまごい。実装上の仮定）
            target = e["to_pokemon_id"]
            power_attached_this_turn += 1
            if pokemon_owner.get(target) != e["player"] or owner.get(e["energy"]) != e["player"] or target not in in_play:
                problems.append(f"{e['turn']} 番の手札からのエネルギー {e['energy']}（→ {target}）が、自分のカードを自分の場のポケモンにつけていない")
                continue
            from_hand(e, e["player"], e["energy"])
            energy[target].append(e["energy"])
            card_id, _, index = e["power"].partition("@power")
            entry = state.effects.power_entry(card_id, int(index)) if index.isdigit() else None
            effect = None if entry is None else entry.effect
            if effect is None or not hasattr(effect, "energy_type"):
                problems.append(f"{e['turn']} 番の手札からのエネルギー {e['energy']} の特殊能力 {e['power']} が、手札からつける特殊能力として登録されていない")
            else:
                if state.printed_def(e["energy"]).provides is not effect.energy_type:
                    problems.append(f"{e['turn']} 番の手札からのエネルギー {e['energy']} が「{effect.energy_type.ja}」エネルギーではない")
                if effect.pokemon_type not in type_readings_now(target):  # v0.49: 今の姿・今有効な色
                    problems.append(f"{e['turn']} 番の手札からのエネルギー {e['energy']} のつける先 {target} が「{effect.pokemon_type.ja}」ポケモンではない")
        elif kind == "move_damage_counter":
            # v0.7: 特殊能力（ダメージスワップ）で、自分の場のポケモンのダメージカウンターを、自分の場の別のポケモンへ（1 回に 1 個）
            if declared != (e["turn"], e["player"], e["pokemon_id"]):
                problems.append(f"{e['turn']} 番のダメージカウンターの移動の直前に、同じポケモンの特殊能力の宣言（pokemon_power）がない")
            declared = None  # 1 回の宣言で 1 個（v0.7 のダメージスワップ。実装上の仮定）
            source, target, count = e["from_pokemon_id"], e["to_pokemon_id"], e["count"]
            card_id, _, index = e["power"].partition("@power")
            entry = state.effects.power_entry(card_id, int(index)) if index.isdigit() else None
            # v0.42: へんなこうどう（MoveDamageCounterToSelf。移動先は使ったポケモン）・のろい（MoveOpponentDamageCounter。相手の場のポケモンのあいだ。
            # ログの owner は相手。説明に「きぜつ」しない範囲の条件がないので、移動先が HP 以上になってよい（すぐあとにきぜつ））
            movers = (MoveDamageCounter, MoveDamageCounterToSelf, MoveOpponentDamageCounter)
            effect = None if entry is None else entry.effect
            if not isinstance(effect, movers) or state.cards[top[e["pokemon_id"]]].card_id != card_id:
                problems.append(f"{e['turn']} 番のダメージカウンターの移動の特殊能力 {e['power']} が、使ったポケモンのダメージカウンターを移す特殊能力ではない")
            if count != 1:
                problems.append(f"{e['turn']} 番のダメージカウンターの移動が 1 回に {count} 個（1 個のはず）")
            side = e.get("owner", e["player"])
            if isinstance(effect, MoveOpponentDamageCounter) != (side != e["player"]) or (
                    isinstance(effect, MoveDamageCounterToSelf) and target != e["pokemon_id"]):
                problems.append(f"{e['turn']} 番のダメージカウンターの移動（{source} → {target}・owner {e.get('owner')}）が、特殊能力 {e['power']} の移す場所と合わない")
            if pokemon_owner.get(source) != side or pokemon_owner.get(target) != side:
                problems.append(f"{e['turn']} 番のダメージカウンターの移動（{source} → {target}）が、{'自分' if side == e['player'] else '相手'}の場のポケモンのあいだではない")
            if source == target or source not in in_play or target not in in_play:
                problems.append(f"{e['turn']} 番のダメージカウンターの移動（{source} → {target}）が、ログから組み立てた場と合わない")
                continue
            amount = count * state.rules.damage_per_counter
            if damage[source] < amount:
                problems.append(f"{e['turn']} 番のダメージカウンターの移動元 {source} に、ログから組み立てたダメージ {damage[source]} しかない")
            damage[source] -= amount
            damage[target] += amount
            if (damage[source], damage[target]) != (e["from_total_damage"], e["to_total_damage"]):
                problems.append(
                    f"{e['turn']} 番のダメージカウンターの移動のあとのダメージ {(e['from_total_damage'], e['to_total_damage'])} が、ログから"
                    f"組み立てた {(damage[source], damage[target])} と違う"
                )
            if damage[target] >= max_hp_now(target):
                if isinstance(effect, MoveOpponentDamageCounter):
                    power_ko_due = target  # v0.42: のろいのあとの「きぜつ」（すぐあとに timing power のきぜつ）
                else:
                    problems.append(f"{e['turn']} 番のダメージカウンターの移動で、移動先 {target} がきぜつするダメージ {damage[target]} になった")
        elif kind == "discard_energy":
            # v0.7: ワザ（じこさいせい）で、ワザを使ったポケモンについているエネルギーカードをトラッシュ
            pid = e["pokemon_id"]
            if pid not in in_play or pokemon_owner.get(pid) != e["player"] or e["energy"] not in energy.get(pid, []):
                problems.append(f"{e['turn']} 番のエネルギーのトラッシュ {e['energy']} が、ログから組み立てたポケモン {pid} のエネルギーにない")
            else:
                energy[pid].remove(e["energy"])
                discard[e["player"]].append(e["energy"])
        elif kind == "recover_energy":
            # v0.9: ワザ（エナジーへんかん）で、ワザを使ったプレイヤーのトラッシュのエネルギーカードを手札に加える
            if attack_window is None or e["pokemon_id"] != attack_window["pokemon_id"] or e["player"] != attack_window["player"]:
                problems.append(f"{e['turn']} 番のトラッシュから手札に加えたエネルギー {e['cards']} が、そのポケモンのワザの処理の中にない")
            for uid in e["cards"]:
                if uid not in discard[e["player"]] or state.printed_def(uid).category != "energy":
                    problems.append(f"{e['turn']} 番に手札に加えたカード {uid} が、ログから組み立てたプレイヤー {e['player']} のトラッシュのエネルギーカードにない")
                    continue
                discard[e["player"]].remove(uid)
                hand[e["player"]].append(uid)
        elif kind in ("retreat", "retreat_failed"):
            pid = e["pokemon_id"] if kind == "retreat_failed" else ids[e["old_active"]]
            # v0.46: トラッシュしたエネルギーの数は、印刷の数に、ログから組み立てた場ではたらく［ねんちゃくえき］（相手のバトル場。決まって増やす）・［にげるサポート］
            # （自分のベンチ。少なくできる）を当てはめた範囲（最後に 0 で下限）。少なくしてから 0 で止める読み方と答えが変わる数は CP2 で止まる
            printed = form_def(pid).retreat_cost  # v0.49: 今の姿のカードのにげるエネルギー
            increases = sorted((hpid, key, eff.amount) for hpid in in_play if pokemon_owner.get(hpid) != e["player"]
                               for key, eff, _ in working_continuous(hpid, IncreaseOpponentActiveRetreatCost))
            reductions = sorted((hpid, key, eff.amount) for hpid in in_play if pokemon_owner.get(hpid) == e["player"]
                                for key, eff, _ in working_continuous(hpid, ReduceOwnActiveRetreatCost))
            maximum = printed + sum(x[2] for x in increases)
            minimum = max(0, maximum - sum(x[2] for x in reductions))
            floor_first = max(0, printed - sum(x[2] for x in reductions)) + sum(x[2] for x in increases)
            count = len(e["discarded"])
            if not is_active(pid) or not minimum <= count <= maximum or count < floor_first:
                problems.append(f"{e['turn']} 番の{kind}（ポケモン {pid}）でトラッシュした {count} 枚が、にげるエネルギーの範囲 {minimum}〜{maximum}"
                                f"（印刷 {printed}・増やす {increases}・少なくできる {reductions}。CP2 の下限 {floor_first}）にない")
            if increases or reductions:
                if (tuple(e.get("retreat_cost", ())), e.get("retreat_cost_printed"), sorted(tuple(x) for x in e.get("retreat_cost_increases", ())),
                        sorted(tuple(x) for x in e.get("retreat_cost_reductions", ()))) != ((minimum, maximum), printed, increases, reductions):
                    problems.append(f"{e['turn']} 番の{kind}のにげるエネルギーの記録が、ログから組み立てた範囲 {minimum}〜{maximum}・{increases}・{reductions} と違う")
            elif any(field in e for field in ("retreat_cost", "retreat_cost_printed", "retreat_cost_increases", "retreat_cost_reductions")):
                problems.append(f"{e['turn']} 番の{kind}に、はたらく特殊能力がないのに、にげるエネルギーの記録がある")
            if kind == "retreat":
                active_of[e["player"]] = ids[e["new_active"]]
                if pid in shifts:
                    shifts[pid]["returned"] = True  # v0.48: ［へんしょく］を使ってからベンチにもどった
            for (effect_pid, _), info in alive.items():
                # v0.36: 「アイスバーン」・「わしづかみ」を受けたポケモンは、はたらく番に「にげる」を宣言しない（エネルギーのトラッシュ・コインの前に拒否）
                if effect_pid == pid and info["kind"] == CannotRetreat.kind and info["active_turn"] == e["turn"]:
                    problems.append(f"{e['turn']} 番に、「にげる」ことができないポケモン {pid} が「にげる」を宣言した（{kind}）")
            for uid in e["discarded"]:
                energy[pid].remove(uid)
                discard[e["player"]].append(uid)
        elif kind == "discard_hand":
            # v0.19: トレーナー（オーキドはかせ）の効果で、手札をすべてトラッシュする。使っているカードは手札から出ている（p.310）
            if sorted(e["cards"]) != sorted(hand[e["player"]]):
                problems.append(f"{e['turn']} 番にトラッシュした手札 {e['cards']} が、ログから組み立てたプレイヤー {e['player']} の手札と違う")
            discard[e["player"]].extend(e["cards"])
            hand[e["player"]] = []
        elif kind == "discard_from_hand":
            # v0.22: トレーナー（パソコン通信）の使うための条件で、手札から選んだカードをトラッシュする（手札の並びの順。使っているカードは
            # 手札から出ている。p.310）
            if len(set(e["cards"])) != len(e["cards"]):
                problems.append(f"{e['turn']} 番にトラッシュした手札 {e['cards']} に同じカードが 2 回ある")
            for uid in e["cards"]:
                from_hand(e, e["player"], uid)
                discard[e["player"]].append(uid)
            if "power" in e:
                # v0.42: 特殊能力（ぶっしつこうかん）で手札を 1 枚トラッシュした。すぐあとに 1 枚まで引く（トレーナーを使うためのトラッシュではない）
                if len(e["cards"]) != 1 or not isinstance(_power_effect(state, e["power"]), DiscardThenDraw):
                    problems.append(f"{e['turn']} 番の特殊能力 {e['power']} でトラッシュした手札 {e['cards']} が、1 枚トラッシュする特殊能力の処理と合わない")
                draw_due = (e["player"], 1, e["turn"], "discard_from_hand（特殊能力）")
            else:
                trainer_discarded[e["player"]] = tuple(e["cards"])
        elif kind == "retrieve_energy":
            # v0.23: トレーナー（エネルギー回収）の効果で、自分のトラッシュの基本エネルギーカード（最大 2 枚）を手札に加える。このカードを使う
            # ためにトラッシュしたカードは選べない（p.257）
            if not 1 <= len(e["cards"]) <= 2 or len(set(e["cards"])) != len(e["cards"]):
                problems.append(f"{e['turn']} 番にトラッシュから手札に加えた基本エネルギーカード {e['cards']} の枚数・重複が合わない")
            for uid in e["cards"]:
                if uid not in discard[e["player"]] or owner.get(uid) != e["player"] or not state.printed_def(uid).is_basic_energy:
                    problems.append(f"{e['turn']} 番に手札に加えたカード {uid} が、ログから組み立てたプレイヤー {e['player']} のトラッシュの基本エネルギーカードにない")
                    continue
                if uid in trainer_discarded[e["player"]]:
                    problems.append(f"{e['turn']} 番に、このカードを使うためにトラッシュしたカード {uid} を手札に加えた（p.257）")
                discard[e["player"]].remove(uid)
                hand[e["player"]].append(uid)
        elif kind == "return_to_deck":
            # v0.24: トレーナー（ポケモン交換おじさん）の使うための条件で、手札のたねポケモン・進化カードを相手に見せてから山札にもどす（p.259）
            uid = e["card"]
            if owner.get(uid) != e["player"] or not (state.printed_def(uid).is_basic_pokemon or state.printed_def(uid).is_evolution_pokemon):
                problems.append(f"{e['turn']} 番に山札にもどしたカード {uid} が、プレイヤー {e['player']} のたねポケモン・進化カードではない")
            from_hand(e, e["player"], uid)
        elif kind == "reveal_from_deck":
            # v0.24: トレーナー（ポケモン交換おじさん）の効果で、山札のたねポケモン・進化カードを相手に見せてから手札に加える（p.259。山札に
            # もどしたカードを選んでもよい）
            uid = e["card"]
            definition = state.printed_def(uid)
            # v0.44: おつかい（SearchTrainerOnHeads）はトレーナーカード、てじな（ReturnHandThenRevealBasicEnergy）は基本エネルギーカードを見せて手札に加える
            revealer = _effect_of_event(state, e) if "effect" in e else None
            if isinstance(revealer, SearchTrainerOnHeads):
                kind_ok = definition.category == "trainer"
            elif isinstance(revealer, ReturnHandThenRevealBasicEnergy):
                kind_ok = definition.is_basic_energy
            else:
                kind_ok = definition.is_basic_pokemon or definition.is_evolution_pokemon
            if owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]] or not kind_ok:
                problems.append(f"{e['turn']} 番に山札から見せて手札に加えたカード {uid} が、プレイヤー {e['player']} の山札のたねポケモン・進化カード"
                                "（おつかいならトレーナー、てじななら基本エネルギーカード）ではない")
            if "power" in e:
                # v0.43: しんかのひかり。山札の進化カードを見せて手札に加え、すぐあとに山札を切る
                if not isinstance(_power_effect(state, e["power"]), SearchEvolutionCardToHand) or not state.printed_def(uid).is_evolution_pokemon:
                    problems.append(f"{e['turn']} 番に特殊能力 {e['power']} で山札から見せて手札に加えたカード {uid} が、しんかのひかりの進化カードではない")
                shuffle_due = e
            hand[e["player"]].append(uid)
        elif kind == "search_deck":
            # v0.22: トレーナー（パソコン通信）の効果で、自分の山札から選び出したカードを手札に加える（「カードを引く」ではない。p.260・p.312）
            uid = e["card"]
            if owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]]:
                problems.append(f"{e['turn']} 番に山札から手札に加えたカード {uid} が、プレイヤー {e['player']} の山札のカードではない（持ち主・手札・トラッシュ）")
            if "power" in e:
                # v0.44: ［ボスをよぶ］。山札の説明の名前のトレーナーカードを手札に加え、すぐあとに山札を切る
                effect = _power_effect(state, e["power"])
                if not isinstance(effect, SearchNamedTrainerOnEntry) or state.printed_def(uid).name_ja != effect.name or state.printed_def(uid).category != "trainer":
                    problems.append(f"{e['turn']} 番に特殊能力 {e['power']} で山札から手札に加えたカード {uid} が、説明の名前のトレーナーカードではない")
                shuffle_due = e
            hand[e["player"]].append(uid)
        elif kind == "evolution_permission":
            # v0.44: トレーナー「サカキ」。使っている最中のそのトレーナーの効果で、使ったプレイヤー（番のプレイヤー）の場の、説明の名前の持ち主のポケモンに許可を与える
            pid = e["pokemon_id"]
            entry = state.effects.trainer_entry(state.cards[e["trainer"]].card_id) if e.get("trainer") in state.cards else None
            effect = None if entry is None else entry.effect
            if not isinstance(effect, EvolutionPermissionForOwnerPokemon) or using_trainer.get(e["player"]) != e["trainer"] or e["player"] != turn_player \
                    or pid not in in_play or pokemon_owner.get(pid) != e["player"] or ids.get(e["pokemon"]) != pid \
                    or not state.in_play_def(e["pokemon"]).name_ja.startswith(f"{effect.owner}の") or e["turn"] <= 2 or (pid, e["turn"]) in permitted:
                problems.append(f"{e['turn']} 番のサカキの許可（ポケモン {pid}）が、使っている最中のサカキの効果・自分の場のサカキのポケモンのものではない")
            permitted.add((pid, e["turn"]))
        elif kind == "once_attack_recorded":
            # v0.44: 場に出てから 1 度しか使えないワザ。ワザの宣言（attack）のすぐあとに、そのポケモン・そのワザの記録。同じ場のポケモンの同じカードのワザは 1 回だけ
            pid = e["pokemon_id"]
            entry = state.effects.attack_entry(_attack_card_id(state, e), e["attack_index"]) if e["pokemon"] in state.cards else None
            if prior is None or prior["kind"] != "attack" or prior["pokemon"] != e["pokemon"] or prior["attack_index"] != e["attack_index"] \
                    or prior["player"] != e["player"] or entry is None or not entry.effect.once_after_entering_play or ids.get(e["pokemon"]) != pid:
                problems.append(f"{e['turn']} 番の 1 度だけ使えるワザの記録（ポケモン {pid}）が、そのワザの宣言のすぐあとにない")
            if (pid, e["pokemon"], e["attack_index"]) in once_used:
                problems.append(f"{e['turn']} 番に、場のポケモン {pid} が 1 度しか使えないワザ {e['attack_index']} をもう一度使った")
            once_used.add((pid, e["pokemon"], e["attack_index"]))
        elif kind == "hand_to_deck" and isinstance(_effect_of_event(state, e), LookOpponentHandCardToDeck):
            # v0.47: おどろかす。見た相手の手札の 1 枚（直前の look_at_card）を、相手が山札にもどし（見せない）、すぐあとに相手の山札を切る
            if not _same_attack(attack_window, e) or e["player"] != 1 - attack_window["player"] or prior is None or prior["kind"] != "look_at_card" \
                    or tuple(e["cards"]) != (prior["card"],) or prior["owner"] != e["player"]:
                problems.append(f"{e['turn']} 番のおどろかすで山札にもどしたカード {e['cards']} が、直前に見た相手の手札のカードではない")
            for uid in e["cards"]:
                from_hand(e, e["player"], uid)
            shuffle_due = e
        elif kind == "hand_to_deck":
            # v0.44: てじな・ラッキーたまご。ワザを使ったプレイヤーの手札のカードを、見せずに山札にもどす（cards は手札の並びの順。山札は組み立て直さない）
            if not _same_attack(attack_window, e) or e["player"] != attack_window["player"] \
                    or not isinstance(_effect_of_event(state, e), (ReturnHandThenRevealBasicEnergy, CoinDrawOrReturnHandToDeck, ShuffleHandIntoDeckThenDraw)) \
                    or not e["cards"] or len(set(e["cards"])) != len(e["cards"]):
                problems.append(f"{e['turn']} 番に手札から山札にもどしたカード {e['cards']} が、そのワザ（てじな・ラッキーたまご）の処理のものではない")
            hand_before = list(hand[e["player"]])
            for uid in e["cards"]:
                from_hand(e, e["player"], uid)
            effect = _effect_of_event(state, e)
            if isinstance(effect, ShuffleHandIntoDeckThenDraw):
                # v0.46: サイコエクスチェンジ。手札をすべてもどす → すぐあとに切る → count 枚まで引く
                if sorted(e["cards"]) != sorted(hand_before):
                    problems.append(f"{e['turn']} 番のサイコエクスチェンジで山札にもどしたカード {e['cards']} が、ログから組み立てた手札 {hand_before} と違う（すべてもどす）")
                shuffle_due, exchange_due = e, (e["player"], effect.count, e["turn"])
            if isinstance(effect, CoinDrawOrReturnHandToDeck):
                if len(e["cards"]) != effect.count:
                    problems.append(f"{e['turn']} 番のラッキーたまごで山札にもどしたカードが {len(e['cards'])} 枚（説明は {effect.count} 枚）")
                shuffle_due = e
        elif kind == "move_opponent_energy":
            # v0.45: じりょくせん。相手の対戦ポケモンの基本エネルギーカード（同じ uid）を、相手の控えポケモンにつける。つける控えが「とうめい」で受けなければ
            # 持ち主のトラッシュ（CR-TRANSPARENCY-ENERGY-BOMB と同じ読み方）
            source, target, uid = e["pokemon_id"], e["to_pokemon_id"], e["energy"]
            if not _same_attack(attack_window, e) or e["attacker"] != attack_window["player"] or e["player"] == e["attacker"] \
                    or not isinstance(_effect_of_event(state, e), DamageThenMoveOpponentEnergyToBench) or uid not in energy.get(source, ()) \
                    or not state.printed_def(uid).is_basic_energy or owner.get(uid) != e["player"] or pokemon_owner.get(target) != e["player"] \
                    or target == source or target not in in_play or e["result"] not in ("attached", "evaded"):
                problems.append(f"{e['turn']} 番のじりょくせんのエネルギー {uid}（{source} → {target}）が、そのワザの処理のものではない")
            else:
                energy[source].remove(uid)
                if e["result"] == "attached":
                    energy[target].append(uid)
                else:
                    discard[e["player"]].append(uid)
                    if attack_window["reception"].get(target) is not False:
                        problems.append(f"{e['turn']} 番のじりょくせんで、「とうめい」で受けないと決まっていない控え {target} のかわりにトラッシュした")
        elif kind == "take_deck_top":
            # v0.45: てつだうふり。相手の山札の一番上のカードを、トレーナーなら相手のトラッシュ、それ以外なら相手の手札へ（カードを引くことではない。山札は組み立て
            # 直さない）。見たのはワザを使ったプレイヤー
            uid = e["card"]
            expected = "discard" if state.printed_def(uid).category == "trainer" else "hand"
            if not _same_attack(attack_window, e) or e["looker"] != attack_window["player"] or e["player"] == e["looker"] \
                    or not isinstance(_effect_of_event(state, e), CoinOpponentDeckTopDiscardTrainerElseHand) or owner.get(uid) != e["player"] \
                    or e["destination"] != expected:
                problems.append(f"{e['turn']} 番のてつだうふりのカード {uid}（{e['destination']}）が、そのワザの処理のものではない")
            (discard if e["destination"] == "discard" else hand)[e["player"]].append(uid)
        elif kind == "put_discard_on_deck_top":
            # v0.44: わるいいたずら。相手（カードの持ち主）のトラッシュのカードを、その山札の上にのせる（切らない）。選んだのはワザを使ったプレイヤー
            uid = e["card"]
            if not _same_attack(attack_window, e) or e["chooser"] != attack_window["player"] \
                    or e["player"] == e["chooser"] or not isinstance(_effect_of_event(state, e), CoinPutOpponentDiscardOnDeckTop) \
                    or owner.get(uid) != e["player"] or uid not in discard[e["player"]]:
                problems.append(f"{e['turn']} 番に山札の上にのせたカード {uid} が、ワザを使ったプレイヤーの相手のトラッシュのカードではない")
            else:
                discard[e["player"]].remove(uid)
        elif kind == "discard_trainer":
            discard[e["player"]].append(e["card"])
            trainer_discarded[e["player"]] = ()
            using_trainer[e["player"]] = None
        elif kind == "play_trainer_as_pokemon":
            # v0.47: なにかの化石・ピッピ人形。使っている最中のこのカード（play_trainer のすぐあと）を、トラッシュせずにベンチにポケモンとして出す
            card = e["card"]
            entry = state.effects.trainer_entry(state.cards[card].card_id) if card in state.cards else None
            if using_trainer.get(e["player"]) != card or entry is None or not isinstance(entry.effect, PlayAsPokemon) or prior is None \
                    or prior["kind"] != "play_trainer" or prior["card"] != card or owner.get(card) != e["player"]:
                problems.append(f"{e['turn']} 番にポケモンとして場に出したカード {card} が、使っている最中のポケモンとして場に出せるトレーナーカードではない")
            using_trainer[e["player"]] = None
            enter(card)
            if ids[card] != e["pokemon_id"]:
                problems.append(f"{e['turn']} 番にポケモンとして場に出したカード {card} の場のポケモンの番号 {e['pokemon_id']} が、ログの順番の番号 {ids[card]} と違う")
        elif kind == "discard_from_play":
            # v0.47: なにかの化石・ピッピ人形（進化カードがのっていない）を、自分の番に、ついているカードといっしょにトラッシュする（きぜつではない）
            pid = e["pokemon_id"]
            if pid not in in_play or pokemon_owner.get(pid) != e["player"] or ids.get(e["pokemon"]) != pid or e["player"] != turn_player \
                    or state.in_play_def(e["pokemon"]).play_role is None or evolve_turns.get(pid):
                problems.append(f"{e['turn']} 番にトラッシュした場のポケモン {pid} が、自分の番の、すてられる場での役割のカード（進化していない）ではない")
            if sorted(e["energy"]) != sorted(energy.get(pid, [])) or e["damage"] != damage[pid] \
                    or tuple(e["cards"]) != (e["pokemon"], *e["energy"], *e["trainers"]):
                problems.append(f"{e['turn']} 番にトラッシュした場のポケモン {pid} のカード {e['cards']}・ダメージ {e['damage']} が、ログの組み立てと違う")
            in_play.discard(pid)
            exclusive.pop(pid, None)
            poisoned.pop(pid, None)
            energy[pid] = []
            damage[pid] = 0
            discard[e["player"]].extend((e["pokemon"], *e["energy"]))
            for uid in e["trainers"]:
                discard[owner[uid]].append(uid)
            if active_of.get(e["player"]) == pid:
                active_of[e["player"]] = None
        elif kind == "trainer_lock_added":
            # v0.47: ずつう・こうしゅうは。ワザを使ったプレイヤーの相手に、次の相手の番の終わりまでの使用の禁止を与える（同じ番に 2 つは与えない）
            if not _same_attack(attack_window, e) or e["source_player"] != attack_window["player"] or e["player"] != 1 - e["source_player"] \
                    or not isinstance(_effect_of_event(state, e), (LockOpponentTrainersNextTurn, DamageThenLockOpponentTrainersOnHeads)) \
                    or e["expires_turn"] != e["turn"] + 1 or (e["player"], e["expires_turn"]) in trainer_locks_log:
                problems.append(f"{e['turn']} 番のトレーナーの使用の禁止（プレイヤー {e['player']}・{e['expires_turn']} 番まで）が、そのワザの処理のものではない")
            trainer_locks_log[(e["player"], e["expires_turn"])] = e
        elif kind == "trainer_lock_removed":
            info = trainer_locks_log.pop((e["player"], e["expires_turn"]), None)
            if info is None or e["reason"] != "expired" or e["turn"] != e["expires_turn"] or e["created_turn"] != info["turn"] \
                    or e["source_player"] != info["source_player"] or e["effect"] != info["effect"]:
                problems.append(f"{e['turn']} 番に消したトレーナーの使用の禁止（プレイヤー {e['player']}・{e['expires_turn']} 番まで）が、与えた禁止の期限と合わない")
        elif kind == "look_at_card":
            # v0.47: ［スパイ］（使ったプレイヤーの番。どちらかの山札の一番上・どちらかのサイド・相手の手札）・おどろかす（相手の手札）。カードは動かない
            zone, holder, card = e["zone"], e["owner"], e["card"]
            if "power" in e:
                valid = isinstance(_power_effect(state, e["power"]), PeekCard) and e["player"] == turn_player and (zone != "hand" or holder != e["player"]) \
                    and (zone != "deck" or e["position"] == 0)
            else:
                valid = _same_attack(attack_window, e) and e["player"] == attack_window["player"] and holder == 1 - e["player"] and zone == "hand" \
                    and isinstance(_effect_of_event(state, e), LookOpponentHandCardToDeck)
            where = hand[holder] if zone == "hand" else None
            if not valid or owner.get(card) != holder or (where is not None and card not in where) \
                    or (where is None and (card in hand[holder] or card in discard[holder])):
                problems.append(f"{e['turn']} 番に見たカード {card}（プレイヤー {holder} の {zone}）が、その特殊能力・ワザで見られるカードではない")
        elif kind in ("look_at_deck_top", "look_at_deck_top_none"):
            # v0.47: みらいよち。ワザを使ったプレイヤーが、自分または相手の山札の上から見る（相手には見せない）
            effect = _effect_of_event(state, e)
            if not _same_attack(attack_window, e) or e["player"] != attack_window["player"] or not isinstance(effect, ArrangeDeckTopEffect) \
                    or e["owner"] not in (0, 1):
                problems.append(f"{e['turn']} 番の {kind} が、山札の上を見て並べかえるワザの処理ではない")
            elif kind == "look_at_deck_top":
                if not 1 <= e["count"] <= effect.max_cards or len(e["cards"]) != e["count"] or len(set(e["cards"])) != e["count"] \
                        or any(owner.get(uid) != e["owner"] or uid in hand[e["owner"]] or uid in discard[e["owner"]] for uid in e["cards"]):
                    problems.append(f"{e['turn']} 番のみらいよちで見たカード {e['cards']}（{e['count']} 枚）が、プレイヤー {e['owner']} の山札の上の {effect.max_cards} 枚までではない")
                arrange_due = e
        elif kind == "arrange_deck_top":
            if arrange_due is None or prior is not arrange_due or (e["player"], e["owner"], e["effect"], e["count"]) \
                    != (arrange_due["player"], arrange_due["owner"], arrange_due["effect"], arrange_due["count"]) \
                    or sorted(e["cards"]) != sorted(arrange_due["cards"]):
                problems.append(f"{e['turn']} 番のみらいよちでもどした並び {e['cards']} が、すぐ前に見たカードの並べかえではない")
            arrange_due = None
        elif kind == "swap_prize_with_deck_top":
            # v0.47: ［わるふざけ］。自分のサイドの位置と山札の一番上を入れかえる（どちらも見ない）
            if not isinstance(_power_effect(state, e["power"]), SwapPrizeWithDeckTop) or e["player"] != turn_player \
                    or not 0 <= e["prize_position"] < state.rules.prize_count - prizes_taken[e["player"]]:
                problems.append(f"{e['turn']} 番のサイドと山札の一番上の入れかえ（位置 {e['prize_position']}）が、その特殊能力の処理ではない")
        elif kind == "discard_attached_trainer":
            discard[owner[e["card"]]].append(e["card"])
        elif kind == "disguise":
            # v0.49: 「ばける」。宣言（pokemon_power）と手札の進化カードを選ぶ決定のあと、使ったポケモンの上に手札の進化カードをのせる（進化ではない。番号・いちばん上の
            # カードは変わらない）
            pid = e["pokemon_id"]
            effect = _power_effect(state, e["power"])
            if not isinstance(effect, Shapeshift) or pid not in in_play or pokemon_owner.get(pid) != e["player"] or e["player"] != turn_player \
                    or ids.get(e["pokemon"]) != pid or pid in disguised or not state.printed_def(e["card"]).is_evolution_pokemon \
                    or e["power"].partition("@")[0] != state.cards[top[pid]].card_id:
                problems.append(f"{e['turn']} 番の disguise（ポケモン {pid}・カード {e['card']}）が、番のプレイヤーの「ばける」の処理ではない")
            from_hand(e, e["player"], e["card"])
            disguised[pid] = e["card"]
        elif kind == "disguise_removed":
            # v0.49: 「ばける」でのせたカードをトラッシュして元にもどした（自分の番の操作・ねむり・マヒ・こんらんになった）
            pid = e["pokemon_id"]
            if disguised.get(pid) != e["card"] or e["reason"] not in ("revert", "special_condition") \
                    or (e["reason"] == "revert" and e["player"] != turn_player):
                problems.append(f"{e['turn']} 番の disguise_removed（ポケモン {pid}・カード {e['card']}）が、ログから組み立てたのせたカード {disguised.get(pid)} と合わない")
            disguised.pop(pid, None)
            discard[e["player"]].append(e["card"])
        elif kind == "recall":
            # v0.49: 「思い出させる」。使っている最中のそのトレーナーの効果で、番のプレイヤーの対戦ポケモン（進化していて、進化前のカードにワザがある）の記録
            if using_trainer.get(e["player"]) != e["card"] or e["player"] != turn_player or active_of.get(e["player"]) != e["pokemon_id"] \
                    or ids.get(e["pokemon"]) != e["pokemon_id"]:
                problems.append(f"{e['turn']} 番の recall（ポケモン {e['pokemon_id']}）が、使っている最中の「思い出させる」・番のプレイヤーの対戦ポケモンのものではない")
        elif kind == "type_shift":
            # v0.48: ［へんしょく］。宣言のすぐあと（色を選ぶ決定のあと）に、使ったポケモンの色を変えた記録。前の記録があれば previous_color・previous_turn
            pid = e["pokemon_id"]
            keys = [] if pid not in top else [f"{definition.id}@power{index}" for definition, index, power in power_defs(pid)
                                               if isinstance(state.effects.power_effect(definition.id, power), ShiftColor)]  # v0.49: 今持つ特殊能力
            if e["power"] not in keys or pid not in in_play or pokemon_owner.get(pid) != e["player"] or e["player"] != turn_player:
                problems.append(f"{e['turn']} 番の type_shift（ポケモン {pid}）が、番のプレイヤーの場のポケモンの［へんしょく］の処理ではない")
            old = shifts.get(pid)
            if (None if old is None else (old["color"].value, old["turn"])) != ((e["previous_color"], e["previous_turn"]) if "previous_color" in e else None):
                problems.append(f"{e['turn']} 番の type_shift（ポケモン {pid}）の前の記録 {e.get('previous_color')} が、ログから組み立てた {old} と違う")
            if EnergyType(e["color"]) not in COLORS:
                problems.append(f"{e['turn']} 番の type_shift の色 {e['color']} が色ではない")
            shifts[pid] = {"color": EnergyType(e["color"]), "turn": e["turn"], "source_card": top.get(pid), "returned": False}
        elif kind == "energy_burn":
            # v0.31: 特殊能力（エナジーバーン）。ついているエネルギーのタイプだけが変わる（カードは動かない）。直前に同じポケモンの宣言
            if declared != (e["turn"], e["player"], e["pokemon_id"]):
                problems.append(f"{e['turn']} 番の energy_burn の直前に、同じポケモンの特殊能力の宣言（pokemon_power）がない")
            declared = None
            card_id, _, index = e["power"].partition("@power")
            entry = state.effects.power_entry(card_id, int(index)) if index.isdigit() else None
            if entry is None or not isinstance(entry.effect, ConvertAttachedEnergy) or e["pokemon_id"] not in top \
                    or state.cards[top[e["pokemon_id"]]].card_id != card_id:
                problems.append(f"{e['turn']} 番の energy_burn の特殊能力 {e['power']} が、使ったポケモンのエネルギーのタイプを変える特殊能力ではない")
            if sorted(e["energies"]) != sorted(energy.get(e["pokemon_id"], [])):
                problems.append(f"{e['turn']} 番の energy_burn のエネルギー {e['energies']} が、ログから組み立てた {energy.get(e['pokemon_id'])} と違う")
        elif kind == "power_heal":
            # v0.31: 特殊能力のダメージカウンターをとりのぞく処理。宣言する（しぜんになおる。直前に同じポケモンの宣言）か、炎エネルギーカードを
            # つけたとき（ほのおでかいふく。trigger はつけたカードで、このポケモンについている炎の基本エネルギーカード）
            pid = e["pokemon_id"]
            card_id, _, index = e["power"].partition("@power")
            entry = state.effects.power_entry(card_id, int(index)) if index.isdigit() else None
            if "trigger" in e:
                if entry is None or not isinstance(entry.effect, HealOnEnergyAttach) or e["trigger"] not in energy.get(pid, []) \
                        or state.printed_def(e["trigger"]).provides is not entry.effect.energy_type:
                    problems.append(f"{e['turn']} 番の power_heal（ポケモン {pid}）が、ついた {e['trigger']} でとりのぞく特殊能力の処理ではない")
                if pid in exclusive:
                    problems.append(f"{e['turn']} 番に、{exclusive[pid]} のポケモン {pid} の「ほのおでかいふく」がはたらいた")
            elif entry is not None and isinstance(entry.effect, HealOwnPokemonOnHeads):
                # v0.42: ヒーリング。直前に使ったプレイヤーの「おもて」のコイン（その特殊能力）があり、とりのぞくのは自分の場のポケモン（使ったポケモン
                # user_pokemon_id は場にいる）から、登録の数まで
                coin = prior or {}
                user = e.get("user_pokemon_id")
                if (coin.get("kind"), coin.get("source"), coin.get("effect"), coin.get("result"), coin.get("player")) != (
                        "coin_flip", "power", e["power"], "heads", e["player"]) or user not in in_play or pokemon_owner.get(user) != e["player"] \
                        or pokemon_owner.get(pid) != e["player"] or state.cards[top[user]].card_id != card_id \
                        or e["counters"] != min(entry.effect.counters, damage[pid] // state.rules.damage_per_counter):
                    problems.append(f"{e['turn']} 番の power_heal（ポケモン {pid}）が、「おもて」のあとの自分の場のポケモンのヒーリングの処理と合わない")
            else:
                if declared != (e["turn"], e["player"], pid):
                    problems.append(f"{e['turn']} 番の power_heal の直前に、同じポケモンの特殊能力の宣言（pokemon_power）がない")
                declared = None
                if entry is None or not isinstance(entry.effect, RemoveOwnCounterOncePerTurn):
                    problems.append(f"{e['turn']} 番の power_heal の特殊能力 {e['power']} が、宣言してとりのぞく特殊能力ではない")
            if e["amount"] <= 0 or e["amount"] != e["counters"] * state.rules.damage_per_counter or e["damage_before"] != damage[pid]:
                problems.append(f"{e['turn']} 番の power_heal の量 {e['amount']}・前のダメージ {e['damage_before']} が合わない（ログ {damage[pid]}）")
            damage[pid] -= e["amount"]
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の power_heal のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind == "bench_from_deck" and "power" in e:
            # v0.43: てしたをよぶ（場に出たときの特殊能力）。自分の山札のたねポケモンを、手札を通さずにベンチに出す（最大 2 枚。続けて出し、そのあとに山札を切る）
            effect = _power_effect(state, e["power"])
            uid = e["card"]
            definition = state.printed_def(uid)
            if not isinstance(effect, BenchBasicsFromDeckOnEntry) or pokemon_owner.get(e["pokemon_id"]) != e["player"] or owner.get(uid) != e["player"] \
                    or uid in hand[e["player"]] or uid in discard[e["player"]] or uid in ids or not definition.is_basic_pokemon:
                problems.append(f"{e['turn']} 番に特殊能力 {e['power']} でベンチに出したカード {uid} が、プレイヤー {e['player']} の山札のたねポケモンではない")
            benched = (shuffle_due["count"] + 1) if shuffle_due is not None and shuffle_due.get("power") == e["power"] and "count" in shuffle_due else 1
            if isinstance(effect, BenchBasicsFromDeckOnEntry) and benched > effect.max_cards:
                problems.append(f"{e['turn']} 番のてしたをよぶで、1 回に {benched} 枚ベンチに出した")
            enter(uid)
            if ids[uid] != e["to_pokemon_id"]:
                problems.append(f"{e['turn']} 番にベンチに出したポケモンの番号 {e['to_pokemon_id']} が、ログから組み立てた {ids[uid]} と違う")
            shuffle_due = {**e, "count": benched}
        elif kind in ("bench_from_deck", "bench_from_deck_none"):
            # v0.32: ワザ（なかまをよぶ・ふえる）で、ワザを使ったプレイヤーの山札の、説明の名前のたねポケモンを、手札を通さずにベンチに出す（山札は組み立て
            # 直さないので、持ち主・手札・トラッシュ・場にないことで確かめる）。どちらのあとにも同じプレイヤーの山札を切る（shuffle）
            # v0.34: たすけをよぶは名前でなくタイプで選ぶ（登録の ``pokemon_type``）
            # v0.45: タケシのイシツブテのたすけをよぶは「(owner)のポケモン」（名前が「(owner)の」で始まるたねポケモン。登録の ``owner``）
            entry = state.effects.attack_entry(*_attack_key(e["effect"]))
            names = getattr(entry.effect, "names", None) if entry is not None else None
            pokemon_type = getattr(entry.effect, "pokemon_type", None) if entry is not None else None
            owner_name = entry.effect.owner if entry is not None and isinstance(entry.effect, PutOwnerBasicFromDeckOntoBenchOnHeads) else None
            if attack_window is None or e["player"] != attack_window["player"] or e["pokemon_id"] != attack_window["pokemon_id"] \
                    or [names, pokemon_type, owner_name].count(None) != 2:
                problems.append(f"{e['turn']} 番の {kind} が、山札からベンチに出すワザ（登録の名前・タイプ）の処理の中にない")
            if kind == "bench_from_deck":
                uid = e["card"]
                definition = state.printed_def(uid)
                if owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]] or uid in ids \
                        or not definition.is_basic_pokemon or (names is not None and definition.name_ja not in names) \
                        or (pokemon_type is not None and definition.pokemon_type is not pokemon_type) \
                        or (owner_name is not None and not definition.name_ja.startswith(f"{owner_name}の")):
                    problems.append(f"{e['turn']} 番にベンチに出したカード {uid} が、プレイヤー {e['player']} の山札の、名前 {names}・タイプ {pokemon_type} の"
                                    "たねポケモンではない")
                enter(uid)
                if ids[uid] != e["to_pokemon_id"]:
                    problems.append(f"{e['turn']} 番にベンチに出したポケモンの番号 {e['to_pokemon_id']} が、ログから組み立てた {ids[uid]} と違う")
            shuffle_due = e
        elif kind == "attack_heal":
            # v0.31: ワザ（ぼーっとする）で、ワザを使ったポケモンのダメージカウンターをとりのぞく。v0.41: 自分の場のポケモン全員（かいふくりんぷん・
            # ダメージシフト）・お互いの場のポケモン全員（みんなでかいふく）からとりのぞくワザもある（とりのぞいてよいポケモンは登録の実装で決める）。
            # とりのぞくのはのっている数まで・1 つ以上（GR-2000-P320-RECOVERY）
            pid = e["pokemon_id"]
            effect = _effect_of_event(state, e) if attack_window is not None else None
            if isinstance(effect, HealAllPokemonBothSides):
                allowed = pid in in_play
            elif isinstance(effect, HealChosenOpponentThenDraw):
                # v0.42: よいおこない。相手の場のポケモン 1 匹から、選んだ数（1 つ以上）。すぐあとに、ワザを使ったプレイヤーがとりのぞいた数まで引く
                allowed = pid in in_play and pokemon_owner.get(pid) != attack_window["player"] and e.get("attacker") == attack_window["player"]
                draw_due = (attack_window["player"], e["counters"], e["turn"], "よいおこないの attack_heal")
            elif isinstance(effect, (CoinsHealOwnPokemon, MoveOwnCountersToOpponent)):
                allowed = pid in in_play and pokemon_owner.get(pid) == attack_window["player"]
            else:
                allowed = attack_window is not None and pid == attack_window["pokemon_id"]
            per = state.rules.damage_per_counter
            if not allowed or e["damage_before"] != damage[pid] or e["player"] != pokemon_owner.get(pid) or e["amount"] != e["counters"] * per \
                    or e["amount"] > damage[pid]:
                problems.append(f"{e['turn']} 番の attack_heal（ポケモン {pid}）が、そのワザでとりのぞけるポケモンでない・前のダメージ・数が合わない")
            if isinstance(effect, MoveOwnCountersToOpponent):
                if e["counters"] != 1:
                    problems.append(f"{e['turn']} 番のダメージシフトでとりのぞいた数 {e['counters']} が 1 つではない")
                attack_window["shifted"] = attack_window.get("shifted", 0) + e["counters"]
            damage[pid] -= e["amount"]
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の attack_heal のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind == "place_damage_counters":
            # v0.41: ワザ（ダメージシフト）で、とりのぞいたダメージカウンターをすべて相手の対戦ポケモンにのせる（ダメージではない。GR-2000-P320-COUNTER-MOVE）
            pid = e["pokemon_id"]
            effect = _effect_of_event(state, e) if attack_window is not None else None
            if isinstance(effect, PlaceCountersOnDamagedOpponentPokemon):
                # v0.48: ダメージぞうふく。相手の場の、ダメージカウンターがのっているポケモンに登録の数ずつ（ダメージではない。最大HPで上限をつけない）
                if pid not in in_play or pokemon_owner.get(pid) != e["player"] or e["player"] == attack_window["player"] or e["damage_before"] != damage[pid] \
                        or damage[pid] <= 0 or e["counters"] != effect.counters or e["amount"] != e["counters"] * state.rules.damage_per_counter:
                    problems.append(f"{e['turn']} 番の place_damage_counters（ポケモン {pid}）が、ダメージカウンターがのっている相手のポケモンに {effect.counters} 個のせる処理と合わない")
                damage[pid] += e["amount"]
                if damage[pid] != e["total_damage"]:
                    problems.append(f"{e['turn']} 番の place_damage_counters のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
                continue
            if isinstance(effect, PlaceCountersToRemainingHpOnHeads):
                # v0.42: ライフダウン。相手の対戦ポケモンの残り HP が登録の数になるまで（ダメージではない）
                hp = hp_of(pid)
                if pid not in in_play or pokemon_owner.get(pid) != e["player"] or e["player"] == attack_window["player"] or e["damage_before"] != damage[pid] \
                        or e["total_damage"] != hp - effect.remaining or e["amount"] != e["counters"] * state.rules.damage_per_counter or e["counters"] <= 0:
                    problems.append(f"{e['turn']} 番の place_damage_counters（ポケモン {pid}）が、残り HP を {effect.remaining} にするライフダウンの処理と合わない")
                damage[pid] += e["amount"]
                continue
            if not isinstance(effect, MoveOwnCountersToOpponent) or pid not in in_play or pokemon_owner.get(pid) != e["player"] \
                    or e["player"] == attack_window["player"] or e["damage_before"] != damage[pid] \
                    or e["counters"] != attack_window.get("shifted", 0) or e["amount"] != e["counters"] * state.rules.damage_per_counter:
                problems.append(f"{e['turn']} 番の place_damage_counters（ポケモン {pid}）が、そのワザでとりのぞいた数を相手のポケモンにのせる処理と合わない")
            damage[pid] += e["amount"]
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の place_damage_counters のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind == "swap_damage_counters":
            # v0.41: ワザ（チェンジダメージ）で、ワザを使ったポケモンと相手の対戦ポケモンのダメージカウンターを、取り替える前の双方の数で取り替える
            own, other = e["pokemon_id"], e["opponent_pokemon_id"]
            effect = _effect_of_event(state, e) if attack_window is not None else None
            if not isinstance(effect, SwapCountersOnHeads) or own != attack_window["pokemon_id"] or pokemon_owner.get(other) != e["opponent"] \
                    or e["opponent"] == e["player"] or (e["damage_before"], e["opponent_damage_before"]) != (damage[own], damage[other]) \
                    or (e["total_damage"], e["opponent_total_damage"]) != (damage[other], damage[own]) or damage[own] == damage[other]:
                problems.append(f"{e['turn']} 番の swap_damage_counters（{own}・{other}）が、取り替える前の双方の数と合わない（ログ {damage[own]}・{damage[other]}）")
            damage[own], damage[other] = e["total_damage"], e["opponent_total_damage"]
        elif kind in ("attach_energy_from_deck", "attach_energy_from_deck_none"):
            # v0.41: ワザ（ひなたぼっこ）で、ワザを使ったプレイヤーの山札の基本エネルギーカードを、ワザを使ったポケモンにつける（手札を通さない）。
            # つけた・つけなかった・選べるものがなかった、のどれでも、すぐあとに山札を切る
            pid = e["pokemon_id"]
            effect = _effect_of_event(state, e) if attack_window is not None else None
            if not isinstance(effect, AttachEnergyFromDeckToSelf) or pid != attack_window["pokemon_id"] or e["player"] != attack_window["player"]:
                problems.append(f"{e['turn']} 番の {kind}（ポケモン {pid}）が、山札からエネルギーをつけるワザの処理の中にない")
            elif kind == "attach_energy_from_deck":
                uid = e["card"]
                definition = state.printed_def(uid)
                if owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]] or not definition.is_basic_energy \
                        or definition.provides is not effect.energy_type:
                    problems.append(f"{e['turn']} 番に山札からつけたカード {uid} が、プレイヤー {e['player']} の山札の「{effect.energy_type.ja}」の基本エネルギーカードではない")
                energy.setdefault(pid, []).append(uid)
            shuffle_due = e
        elif kind == "evolve_from_deck_none":
            # v0.42: つきのちから（「おもて」）で、山札に重ねられる進化カードがなかった。すぐあとに山札を切る
            if "power" in e:
                # v0.44: ［うか］（「おもて」）で、山札に重ねられるカードがなかった。直前に持ち主の「おもて」のコイン。すぐあとに山札を切る
                if not isinstance(_power_effect(state, e["power"]), CoinEvolveSelfFromDeck) or prior is None or prior["kind"] != "coin_flip" \
                        or prior.get("effect") != e["power"] or prior["result"] != "heads":
                    problems.append(f"{e['turn']} 番の evolve_from_deck_none（特殊能力 {e['power']}）が、［うか］の「おもて」のすぐあとにない")
            elif not _same_attack(attack_window, e) or not isinstance(_effect_of_event(state, e), (EvolveFromDeckOnHeads, EvolveSelfFromDeck)):
                problems.append(f"{e['turn']} 番の evolve_from_deck_none が、山札から進化させるワザの処理の中にない")
            shuffle_due = e
        elif kind == "return_energy_to_hand":
            # v0.42: ワザ（エネループ）で、ワザを使ったポケモンについているエネルギーカードを手札にもどす（ダメージの要素より前）
            pid = e["pokemon_id"]
            if attack_window is None or pid != attack_window["pokemon_id"] or e["player"] != attack_window["player"] \
                    or e["energy"] not in energy.get(pid, []) or window_damaged(attack_window):
                problems.append(f"{e['turn']} 番に手札にもどしたエネルギー {e['energy']} が、ワザを使ったポケモンについていた・ダメージの要素より前のものではない")
            else:
                energy[pid].remove(e["energy"])
                hand[e["player"]].append(e["energy"])
        elif kind == "return_in_play_to_hand":
            # v0.42: 特殊能力（おくびょう。ついているカードをトラッシュしたすぐあと）・ワザ（ようせいのきせき）で、自分の場のポケモンを手札にもどす（きぜつでは
            # ない。重なったカードとついているカードもいっしょに手札へ）
            pid = e["pokemon_id"]
            if "power" in e:
                valid = prior is not None and prior["kind"] == "discard_attached_cards" and prior.get("power") == e["power"] and prior["pokemon_id"] == pid \
                    and isinstance(_power_effect(state, e["power"]), ReturnSelfToHand)
            else:
                # v0.44: スターブーメラン（DamageThenReturnSelfToHandOnHeads。ワザを使ったポケモン自身）
                valid = _same_attack(attack_window, e) and e["player"] == attack_window["player"] \
                    and isinstance(_effect_of_event(state, e), (ReturnOwnPokemonToHandOnHeads, DamageThenReturnSelfToHandOnHeads))
            if not valid or pid not in in_play or pokemon_owner.get(pid) != e["player"] or ids.get(e["pokemon"]) != pid:
                problems.append(f"{e['turn']} 番に手札にもどしたポケモン {pid} が、その特殊能力・ワザの処理のものではない")
            if sorted(e["energy"]) != sorted(energy.get(pid, [])) or e["damage"] != damage[pid]:
                problems.append(f"{e['turn']} 番に手札にもどしたポケモン {pid} のエネルギー {e['energy']}・ダメージ {e['damage']} がログの組み立てと違う")
            if sorted(e["cards"]) != sorted([*e["evolution_stack"], e["pokemon"], *(() if "disguise" not in e else (e["disguise"],)), *e["energy"], *e["trainers"]]) \
                    or any(owner.get(uid) != e["player"] for uid in e["cards"]) or e.get("disguise") != disguised.get(pid):
                problems.append(f"{e['turn']} 番に手札にもどしたカード {e['cards']} が、そのポケモンのカード・ついているカードと合わない")
            disguised.pop(pid, None)  # v0.49
            in_play.discard(pid)
            exclusive.pop(pid, None)
            poisoned.pop(pid, None)
            energy[pid] = []
            damage[pid] = 0
            hand[e["player"]].extend(e["cards"])
        elif kind in ("power_confusion", "power_confusion_skipped"):
            # v0.42: 「ぼうぎょかふん」（バトル場で相手のワザのダメージを受けたときに自動的にはたらく。特殊状態でもはたらく。かがくへんかガスは止める）。
            # 直前に持ち主の「ぼうぎょかふん」のコイン。「おもて」なら、すぐあとにダメージを与えたポケモン（ワザを使ったポケモン）をこんらんにする
            holder = e["pokemon_id"]
            effect = _power_effect(state, e["power"])
            if attack_window is None or (e["attacker"], e["attacker_pokemon_id"], e["effect"]) != (
                    attack_window["player"], attack_window["pokemon_id"], attack_window["effect"]) or holder not in in_play \
                    or pokemon_owner.get(holder) != e["player"] or e["player"] == e["attacker"] or not isinstance(effect, ConfuseDamageSourceOnHeads) \
                    or e["power"] not in [f"{d.id}@power{i}" for d, i, _ in power_defs(holder)] or holder not in attack_window.get("damaged", set()):
                problems.append(f"{e['turn']} 番の {kind}（ポケモン {holder}）が、相手のワザのダメージを受けた「ぼうぎょかふん」のポケモンの処理ではない")
            power = next((pw for definition, index, pw in power_defs(holder) if f"{definition.id}@power{index}" == e["power"]), None) if holder in top else None
            if power is not None and [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(power)]:
                problems.append(f"{e['turn']} 番に、かがくへんかガスに消されている「ぼうぎょかふん」（ポケモン {holder}）がはたらいた")
            target = e["attacker_pokemon_id"]
            if kind == "power_confusion_skipped":
                if e["reason"] != "knocked_out" or target not in in_play or damage[target] < max_hp_now(target):
                    problems.append(f"{e['turn']} 番に、きぜつしていない相手 {target} に「ぼうぎょかふん」がはたらかなかった（{e['reason']}）")
            else:
                coin = prior or {}
                if (coin.get("kind"), coin.get("source"), coin.get("player"), coin.get("effect"), coin.get("result")) != (
                        "coin_flip", "power", e["player"], e["power"], e["result"]) or e["confused"] != (e["result"] == "heads"):
                    problems.append(f"{e['turn']} 番の「ぼうぎょかふん」（ポケモン {holder}）の直前に、持ち主の同じ結果のコインがない・結果が合わない")
                if e["confused"]:
                    confusion_due = (target, e["power"])
        elif kind == "discard_attached_energy":
            # v0.31: ワザ（スーパーデストロイ・メラメラ）で、相手のポケモンについているエネルギーカードを持ち主のトラッシュへ
            pid = e["pokemon_id"]
            if pid not in in_play or pokemon_owner.get(pid) != e["player"] or e["energy"] not in energy.get(pid, []) \
                    or attack_window is None or e["attacker"] != attack_window["player"] or e["player"] == attack_window["player"]:
                problems.append(f"{e['turn']} 番の相手のエネルギーのトラッシュ {e['energy']} が、ログから組み立てた相手のポケモン {pid} のエネルギーにない")
            else:
                energy[pid].remove(e["energy"])
                discard[e["player"]].append(e["energy"])
        elif kind == "recover_trainer":
            # v0.31: ワザ（ゴミあさり）で、ワザを使ったプレイヤーのトラッシュのトレーナーカード 1 枚を手札に加える
            uid = e["card"]
            if uid not in discard[e["player"]] or state.printed_def(uid).category != "trainer":
                problems.append(f"{e['turn']} 番に手札に加えたカード {uid} が、ログから組み立てたプレイヤー {e['player']} のトラッシュのトレーナーカードにない")
            else:
                discard[e["player"]].remove(uid)
                hand[e["player"]].append(uid)
        elif kind == "attach_energy_from_discard":
            # v0.31: ワザ（たいでん）で、ワザを使ったプレイヤーのトラッシュの基本エネルギーカードを、ワザを使ったポケモンにつける
            pid = e["pokemon_id"]
            if not 1 <= len(e["cards"]) <= 2 or attack_window is None or pid != attack_window["pokemon_id"]:
                problems.append(f"{e['turn']} 番のトラッシュからつけたエネルギー {e['cards']} の枚数・ポケモンが合わない")
            for uid in e["cards"]:
                if uid not in discard[e["player"]] or not state.printed_def(uid).is_basic_energy:
                    problems.append(f"{e['turn']} 番につけたカード {uid} が、ログから組み立てたプレイヤー {e['player']} のトラッシュの基本エネルギーカードにない")
                    continue
                discard[e["player"]].remove(uid)
                energy.setdefault(pid, []).append(uid)
        elif kind == "attack_attach_energy":
            # v0.31: ワザ（エナジーボム）で、ワザを使ったポケモンのエネルギーカードを、自分の控えポケモンにつける（同じカード）
            source, target = e["pokemon_id"], e["to_pokemon_id"]
            if source == target or target not in in_play or pokemon_owner.get(target) != e["player"] or e["energy"] not in energy.get(source, []):
                problems.append(f"{e['turn']} 番の控えにつけたエネルギー {e['energy']}（{source} → {target}）が、ログから組み立てた場と合わない")
            else:
                energy[source].remove(e["energy"])
                energy[target].append(e["energy"])
        elif kind == "discard_from_deck":
            # v0.31: ワザ（やまやき・マグマふんしゅつ）で、山札の上からカードをトラッシュする（山札は組み立て直さないので、持ち主・手札とトラッシュに
            # ないことで確かめる）
            for uid in e["cards"]:
                if owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]]:
                    problems.append(f"{e['turn']} 番に山札からトラッシュしたカード {uid} が、プレイヤー {e['player']} の山札のカードではない")
                    continue
                discard[e["player"]].append(uid)
        elif kind == "destiny_bond":
            # v0.31: 「みちづれ」の効果のポケモンがきぜつしたので、相手の対戦ポケモンもきぜつする（ダメージではない）
            if e["pokemon_id"] in in_play and damage[e["pokemon_id"]] < max_hp_now(e["pokemon_id"]):
                problems.append(f"{e['turn']} 番の「みちづれ」（ポケモン {e['pokemon_id']}）が、きぜつしていないポケモンの効果ではたらいた")
            destiny_knocked.add(e["target_pokemon_id"])
        elif kind == "return_in_play_to_deck":
            # v0.36: ワザ（くもがくれガス）で、ワザを使ったポケモンと、ついているすべてのカードを持ち主の山札にもどす（きぜつではない。山札は組み立て
            # 直さないので、持ち主・場にあったことで確かめる）。すぐあとに（持続する効果を消したログのあと）同じプレイヤーの山札を切る
            pid = e["pokemon_id"]
            # v0.40: わるいカイリキーの「つまみだす」は、相手の対戦ポケモンを持ち主（相手）の山札にもどす（登録の実装 ReturnOpponentActiveToDeck）。
            # v0.48: ナツメのゲンガーの「やみのこえ」も同じ。相手を山札にもどすワザは、登録の実装の相手への効果の要素（opponent_effect_elements）で決める
            entry = state.effects.attack_entry(*_attack_key(e["effect"]))
            opponent_return = entry is not None and RETURN_IN_PLAY_TO_DECK_ELEMENT in getattr(entry.effect, "opponent_effect_elements", ())
            if pid not in in_play or pokemon_owner.get(pid) != e["player"] or ids.get(e["pokemon"]) != pid or attack_window is None \
                    or (not opponent_return and (pid != attack_window["pokemon_id"] or e["player"] != attack_window["player"])) \
                    or (opponent_return and e["player"] == attack_window["player"]):
                problems.append(f"{e['turn']} 番に山札にもどしたポケモン {pid} が、そのワザを使ったポケモン（つまみだすなら相手のポケモン）ではない")
            if sorted(e["energy"]) != sorted(energy.get(pid, [])) or e["damage"] != damage[pid]:
                problems.append(f"{e['turn']} 番に山札にもどしたポケモン {pid} のエネルギー {e['energy']}・ダメージ {e['damage']} がログの組み立てと違う")
            if sorted(e["cards"]) != sorted([*e["evolution_stack"], e["pokemon"], *(() if "disguise" not in e else (e["disguise"],)), *e["energy"], *e["trainers"]]) \
                    or any(owner.get(uid) != e["player"] for uid in e["cards"]) or e.get("disguise") != disguised.get(pid):
                problems.append(f"{e['turn']} 番に山札にもどしたカード {e['cards']} が、そのポケモンのカード・ついているカードと合わない")
            disguised.pop(pid, None)  # v0.49
            in_play.discard(pid)
            exclusive.pop(pid, None)
            poisoned.pop(pid, None)
            energy[pid] = []
            damage[pid] = 0
            if _returns_without_shuffle(state, e["effect"]):
                search_due = e  # v0.38: でんれい（山札をさがしたあとに切る）
            else:
                shuffle_due = e
        elif kind == "discard_attached_cards":
            # v0.38: ワザ（ケーシィの「いなくなる」）で、ワザを使ったポケモンについているエネルギー・トレーナーを持ち主のトラッシュへ（ダメージカウンターを
            # とりのぞいたあと・山札にもどす前）
            pid = e["pokemon_id"]
            # v0.42: 特殊能力（おくびょう）は、ダメージカウンターをすべてとりのぞいたすぐあとに、使ったポケモンについているカードをトラッシュする
            by_power = "power" in e and prior is not None and prior["kind"] == "remove_all_damage_counters" and prior.get("power") == e["power"] \
                and prior["pokemon_id"] == pid
            if pid not in in_play or pokemon_owner.get(pid) != e["player"] or (not by_power and (attack_window is None or pid != attack_window["pokemon_id"])) \
                    or sorted(e["energy"]) != sorted(energy.get(pid, [])) or damage[pid] != 0 \
                    or any(owner.get(uid) != e["player"] for uid in (*e["energy"], *e["trainers"])):
                problems.append(f"{e['turn']} 番のついているカードのトラッシュ（ポケモン {pid}）が、ログから組み立てたワザを使ったポケモンのカードと合わない")
            else:
                energy[pid] = []
                discard[e["player"]].extend((*e["energy"], *e["trainers"]))
        elif kind == "knock_out":
            pid = ids[e["pokemon"]]
            if pid not in in_play:
                problems.append(f"場にいないポケモン {pid} がきぜつした")
            if (e.get("timing") == "power") != power_knock_out:
                problems.append(f"{e['turn']} 番のきぜつ（ポケモン {pid}・timing {e.get('timing')}）が、特殊能力の処理のすぐあとのきぜつと合わない")
            if attack_window is not None and pid in in_play:
                # v0.11: 「こんじょう」の「おもて」のポケモンはきぜつしない。使えたのに決定がないまま、きぜつしない（使うかは持ち主が決める）
                attack_window["knocked"].add(pid)
                if attack_window["ko_offer"] == pid and attack_window["ko_result"] == "heads":
                    problems.append(f"{e['turn']} 番に「こんじょう」が「おもて」のポケモン {pid} がきぜつした（G18・G33）")
                if attack_window["ko_offer"] != pid and attack_window["ko_able"].get(pid, "なし") is None:
                    gkey, _, gpower = guts_power(pid)
                    if gkey is not None and not [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(gpower)]:
                        problems.append(
                            f"{e['turn']} 番に「こんじょう」を使えるポケモン {pid} が、使うかの決定（ko_prevention_declined・ko_prevention_declared）"
                            "がないまま、きぜつした（G10・A4）"
                        )
            # v0.48: 「きょだいか」の効果があればその最大HP（きぜつのログは効果を消すログより前）。［ガスのからだ］の分は足さない（同じきぜつの判定で、それを消していた
            # かがくへんかガスの持ち主が先にきぜつのログに出ると、ログから組み立てた場ではガスがなくなる。エンジンはきぜつの判定の前の場で最大HPを求める）
            fixed_hp = lasting_value(pid, MaxHpSet.kind, "amount") if pid in top else None
            # v0.49: 今の姿（「ばける」・［へんしん］）の HP。きぜつのログの順番で［へんしん］の相手が先に場をはなれることがあるので、いちばん上のカードの HP との小さいほう
            hp_floor = fixed_hp if fixed_hp is not None else min(state.in_play_def(e["pokemon"]).hp, form_def(pid).hp if pid in top else 10 ** 6)
            if damage[pid] < hp_floor and pid not in destiny_knocked:
                problems.append(f"場のポケモン {pid} が、ログから組み立てたダメージ {damage[pid]}（HP 未満）できぜつした")
            destiny_knocked.discard(pid)
            rkey, rpower = rebirth_power(e["pokemon"])
            if rkey is not None and pid in in_play:
                # v0.12: 「ふしちょう」を使えるか（きぜつするときのねむり・マヒ・こんらん（P13〜P17）・はたらいているかがくへんかガス（P18））
                gases = [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(rpower) and gas_pid != pid]
                blocked = f"{exclusive[pid]} 状態" if pid in exclusive else f"かがくへんかガス（ポケモン {gases}）" if gases else None
                rebirth_pending.append({"card": e["pokemon"], "player": e["player"], "power": rkey, "turn": e["turn"], "blocked": blocked})
            in_play.discard(pid)
            exclusive.pop(pid, None)
            # v0.47: いちばん上がなにかの化石・ピッピ人形（場での役割のあるカード。進化カードがのっていない）の「きぜつ」はカウントされない（counted False。相手は
            # サイドを取らない）。ほかのきぜつは今までどおり（counted を書かない）
            counted = state.in_play_def(e["pokemon"]).play_role is None
            if e.get("counted", True) != counted or ("counted" in e and counted):
                problems.append(f"{e['turn']} 番のきぜつ（ポケモン {pid}）の counted {e.get('counted')!r} が、いちばん上のカードの場での役割と合わない")
            if counted:
                knocked[e["player"]] += 1
            if e.get("disguise") != disguised.get(pid):
                problems.append(f"{e['turn']} 番のきぜつ（ポケモン {pid}）の「ばける」でのせたカード {e.get('disguise')} が、ログから組み立てた {disguised.get(pid)} と違う")
            disguised.pop(pid, None)
            discard[e["player"]].extend([*e.get("evolution_stack", ()), e["pokemon"], *(() if "disguise" not in e else (e["disguise"],)), *e["discarded_energy"]])
            if sorted(e["discarded_energy"]) != sorted(energy.get(pid, [])):
                problems.append(f"きぜつしたポケモン {pid} のトラッシュしたエネルギー {e['discarded_energy']} がログの組み立てと違う")
            for uid in e.get("discarded_trainers", ()):
                discard[owner[uid]].append(uid)
        elif kind == "take_prize":
            prizes_taken[e["player"]] += 1
            taken_cards.append(e["card"])
            hand[e["player"]].append(e["card"])
        elif kind == "persistent_effect_added":
            added[(e["pokemon_id"], e["turn"])] = added.get((e["pokemon_id"], e["turn"]), 0) + 1
            # v0.12: はたらく番は次の相手の番（与えた番 + 1）。その番の終わりまで残り、そのあとは残らない。v0.27 の「つるぎのまい」は
            # 次の自分の番（与えた番 + 2）
            alive[(e["pokemon_id"], e["turn"])] = {
                "kind": e["persistent_effect"], "active_turn": e["active_turn"], "effect": e["effect"], "source_card": e["source_card"],
                "target_attack_index": e.get("target_attack_index"),  # v0.35: 「あわあわ」・「ドわすれ」の使えなくなるワザの位置
                # v0.49: 使えなくなるワザを印刷したカードの id（「あわあわ」は効果を与えたワザのカード、「ドわすれ」はログの target_attack_card か受けたポケモンのカード）
                "target_attack_card": (_attack_key(e["effect"])[0] if e["persistent_effect"] == CannotUseOwnAttack.kind
                                       else e.get("target_attack_card") or state.in_play_def(e["pokemon"]).id),
                "single_use": e.get("single_use"),  # v0.36: 「すなかけ」（PMCG1-051）の「効果は1回できえる」
                "lasting": e.get("lasting", False),  # v0.45: 「スミをかける」の「それ以後」（期限で消えない。場をはなれる・進化で消える）
                "color": e.get("color"), "amount": e.get("amount"),  # v0.48: テクスチャー1・2 の色、きょだいかの最大HP
                # v0.34: 「次の自分の番の始めに消える」効果（なきつく）は、はたらく番の次の番の始めに消える（はたらく番の終わりではない）
                # v0.45: 期限のない効果は期限で消えない。v0.48: テクスチャー1・2・きょだいかも期限がない（ベンチにもどる・場をはなれる・進化で消える）
                "until": (float("inf") if e.get("lasting") or e["persistent_effect"] in V048_LASTING_KINDS else
                          e["active_turn"] + 1 if e["persistent_effect"] == ReducedDamageToSource.kind else e["active_turn"]),
            }
            if e.get("lasting") and (e["persistent_effect"] != AttackCoinCheck.kind or e.get("single_use")):
                problems.append(f"{e['turn']} 番の期限のない持続する効果（ポケモン {e['pokemon_id']}）が、手順 4 のコインの「1回できえる」でない効果ではない")
            # v0.35: 「きあいだめ」（next_turn_attack_damage_multiplier）・「あわあわ」（cannot_use_own_attack）も次の自分の番
            offset = (NextTurnAttackDamage.turns_until_active if e["persistent_effect"] in (*NEXT_TURN_DAMAGE_KINDS.values(), CannotUseOwnAttack.kind)
                      else 0 if e["persistent_effect"] in V048_LASTING_KINDS else 1)
            if e["active_turn"] != e["turn"] + offset:
                problems.append(
                    f"{e['turn']} 番の持続する効果（ポケモン {e['pokemon_id']}）のはたらく番 {e['active_turn']} が、"
                    f"{'次の相手の番' if offset == 1 else '与えた番' if offset == 0 else '次の自分の番'}ではない"
                )
            if e["persistent_effect"] in V048_LASTING_KINDS:
                # v0.48: テクスチャー1（相手の対戦ポケモン）・テクスチャー2・きょだいか（ワザを使ったポケモン）。色は無色以外、最大HPは登録の数。同じ種類の前の効果は
                # すぐ前に理由 replaced で消した（受けているポケモンに同じ種類の効果は 1 つ）
                entry = state.effects.attack_entry(*_attack_key(e["effect"]))
                effect = None if entry is None else entry.effect
                expected = getattr(effect, "color_terms", lambda: None)() or getattr(effect, "max_hp_terms", lambda: None)()
                value = e.get("color") if e["persistent_effect"] != MaxHpSet.kind else e.get("amount")
                if expected is None or expected[0].kind != e["persistent_effect"] or (e["persistent_effect"] == MaxHpSet.kind and value != expected[1]) \
                        or (e["persistent_effect"] != MaxHpSet.kind and (value is None or EnergyType(value) is EnergyType.COLORLESS)):
                    problems.append(f"{e['turn']} 番の期限のない効果 {e['persistent_effect']}（ポケモン {e['pokemon_id']}・{value}）が、登録のワザ {e['effect']} の効果と合わない")
                on_opponent = e["persistent_effect"] == WeaknessChange.kind
                if (pokemon_owner.get(e["pokemon_id"]) != e["source_player"]) != on_opponent or e["source_player"] != turn_player:
                    problems.append(f"{e['turn']} 番の期限のない効果 {e['persistent_effect']} を受けたポケモン {e['pokemon_id']} の持ち主が合わない")
                if len([1 for (pid, _), info in alive.items() if pid == e["pokemon_id"] and info["kind"] == e["persistent_effect"]]) > 1:
                    problems.append(f"{e['turn']} 番に、ポケモン {e['pokemon_id']} の同じ種類の期限のない効果 {e['persistent_effect']} を消さずに重ねた")
        elif kind == "persistent_effect_removed":
            removed[(e["pokemon_id"], e["created_turn"])] += 1
            info = alive.pop((e["pokemon_id"], e["created_turn"]), None)
            if info is not None and e["reason"] == "expired" and e["turn"] != info["until"]:
                problems.append(f"{e['turn']} 番に、はたらく番 {info['active_turn']} の持続する効果（ポケモン {e['pokemon_id']}）が期限で消えた（早すぎる・遅すぎる）")
            if info is not None and e["reason"] == "expired" and info["until"] != info["active_turn"] \
                    and (prior is None or prior["kind"] not in ("turn_start", "persistent_effect_removed")):
                problems.append(f"{e['turn']} 番に、番の始めに消える持続する効果（ポケモン {e['pokemon_id']}）が、番の始め（turn_start のすぐあと）以外で消えた")
        if arrange_due is not None and kind != "arrange_deck_top" and prior is arrange_due:
            problems.append(f"{arrange_due['turn']} 番のみらいよちで見たカードのすぐあとに、その並べかえ（arrange_deck_top）がない（{kind}）")
            arrange_due = None
        if kind == "turn_end":
            for (locked_player, expires), info in trainer_locks_log.items():
                if expires <= e["turn"]:
                    problems.append(f"{e['turn']} 番の終わり（turn_end）に、{expires} 番までのトレーナーの使用の禁止（プレイヤー {locked_player}）が残っている")
            for (pid, created), info in alive.items():
                if info["until"] <= e["turn"]:
                    problems.append(f"{e['turn']} 番の終わり（turn_end）に、はたらく番 {info['active_turn']} の持続する効果（ポケモン {pid}・{created} 番）が残っている")
        # v0.46: バトル場のポケモン（常にはたらく特殊能力の場所の条件）。にげるは retreat の処理で、場をはなれたら in_play からなくなる
        if kind == "promote_active":
            active_of[e["player"]] = ids.get(e["pokemon"])
        elif kind in ("switch", "forced_switch"):
            active_of[e["player"]] = e["new_active_pokemon_id"]
            if e.get("old_active_pokemon_id") in shifts:
                shifts[e["old_active_pokemon_id"]]["returned"] = True  # v0.48: ［へんしょく］を使ってからベンチにもどった
        elif kind == "shuffle" and exchange_due is not None and e["player"] == exchange_due[0]:
            # v0.46: サイコエクスチェンジ。手札を山札にもどして切ったすぐあとに、count 枚まで引く
            draw_due, exchange_due = (exchange_due[0], exchange_due[1], exchange_due[2], "サイコエクスチェンジの shuffle"), None

    if declared is not None and not (state.decision is not None and state.decision.resume == "power"
                                     and (state.decision.context_value("use") or (None, None))[1] == declared[2]):
        # v0.42: 宣言のあと、その特殊能力の決定（ぶっしつこうかんのトラッシュする手札）を待っているなら、処理はまだない
        problems.append(f"{declared[0]} 番の特殊能力の宣言（ポケモン {declared[2]}）のあとに、その処理がない（ログの最後）")
    if draw_due is not None:
        problems.append(f"{draw_due[2]} 番の {draw_due[3]} のあとに、引く処理がない（ログの最後）")
    if power_ko_due is not None:
        problems.append(f"特殊能力の処理で HP 以上になったポケモン {power_ko_due} が、きぜつしていない（ログの最後）")
    if entry_due is not None and not (state.decision is not None and state.decision.kind == "entry_power" and state.decision.options == (entry_due[1],)):
        problems.append(f"{entry_due[0]} 番の進化（ポケモン {entry_due[1]}）の場に出たときの特殊能力を使うかの答えも、その決定もない（ログの最後）")
    if condition_due is not None:
        problems.append(f"特殊能力のコインのあと、置きかえたポケモン {condition_due[1]} の特殊状態がない（ログの最後）")
    if confusion_due is not None:
        problems.append(f"「ぼうぎょかふん」の「おもて」のあとに、ポケモン {confusion_due[0]} のこんらんがない（ログの最後）")
    if expect is not None:
        problems.append(f"「とうめい」の判定（ポケモン {expect[0]}）のあとに、その要素の処理がない（ログの最後）")
    if attack_window is not None and attack_window["due"]:
        problems.append(f"はたらいた「はんげき」（ポケモン {[d[0] for d in attack_window['due']]}）がない（ログの最後。決定の前に与えるはず）")
    if attack_window is not None and attack_window["ret_due"]:
        problems.append(f"はたらいた「ほのおのかべ」・「こうらがえし」（ポケモン {[d[0] for d in attack_window['ret_due']]}）がない（ログの最後。決定の前に与えるはず）")
    if rebirth_answered is not None and rebirth_answered["kind"] == "post_knockout_power_declared":
        problems.append(f"「ふしちょう」の宣言（カード {rebirth_answered['card']}）のあとに、手札に加えた記録がない（ログの最後）")
    d = state.decision
    for r in rebirth_pending:
        waiting = d is not None and d.resume == "post_knockout" and d.options == (r["card"],)
        waiting_prize = d is not None and d.kind == "take_prize" and (r["player"], r["card"]) in [
            (c[0], c[1]) for c in d.context_value("post_knockout", ())
        ]
        if r["blocked"] is None and not (waiting or waiting_prize or state.phase in TERMINAL):
            problems.append(f"きぜつした「ふしちょう」を使えるカード {r['card']} の答えも、それを待つ決定もない（ログの最後）")
        if r["blocked"] is not None and (waiting or waiting_prize):
            problems.append(f"使えない「ふしちょう」（カード {r['card']}。{r['blocked']}）を使うかの決定を出している")
    for (pid, created), info in alive.items():
        if pid not in in_play:
            problems.append(f"場をはなれたポケモン {pid} の持続する効果（{created} 番）を消したログがない（p.322）")
    for p_index, p in enumerate(state.players):
        for pokemon in p.in_play():
            pid = pokemon.pokemon_id
            if pid not in in_play:
                problems.append(f"場のポケモン {pid} がログでは場にいない")
                continue
            if pokemon.damage != damage[pid]:
                problems.append(f"場のポケモン {pid} のダメージ {pokemon.damage} が、ログから組み立てた {damage[pid]} と違う")
            if sorted(pokemon.energy) != sorted(energy[pid]):
                problems.append(f"場のポケモン {pid} のエネルギー {pokemon.energy} が、ログから組み立てた {energy[pid]} と違う")
            if ids.get(pokemon.card) != pid:
                problems.append(f"場のポケモン {pid} のいちばん上のカード {pokemon.card} が、ログの進化と対応しない")
            state_exclusive = pokemon.conditions.exclusive
            if (None if state_exclusive is None else state_exclusive.name) != exclusive.get(pid):
                problems.append(f"場のポケモン {pid} のねむり・マヒ・こんらん {state_exclusive!r} が、ログから組み立てた {exclusive.get(pid)!r} と違う")
            # v0.48: ［へんしょく］の記録と、今有効な最大HP・弱点・抵抗力・色の読み方が、ログから組み立てた値と同じ（エンジンの問い合わせ effects.max_hp など）
            shift, logged = pokemon.type_shift, shifts.get(pid)
            if (None if shift is None else (shift.color, shift.turn, shift.source_card, shift.returned_to_bench)) != (
                    None if logged is None else (logged["color"], logged["turn"], logged["source_card"], logged["returned"])):
                problems.append(f"場のポケモン {pid} の［へんしょく］の記録 {shift} が、ログから組み立てた {logged} と違う")
            from kyuura_engine.effects import max_hp, resistance_of, type_readings, weakness_of
            if (max_hp(state, pokemon), weakness_of(state, pokemon), resistance_of(state, pokemon)[0]) != (max_hp_now(pid), weakness_now(pid), resistance_now(pid)):
                problems.append(f"場のポケモン {pid} の今有効な最大HP・弱点・抵抗力 {(max_hp(state, pokemon), weakness_of(state, pokemon), resistance_of(state, pokemon)[0])} が、"
                                f"ログから組み立てた {(max_hp_now(pid), weakness_now(pid), resistance_now(pid))} と違う")
            if type_readings(state, pokemon) != type_readings_now(pid):
                problems.append(f"場のポケモン {pid} の色の読み方 {type_readings(state, pokemon)} が、ログから組み立てた {type_readings_now(pid)} と違う")
        if sorted(p.hand) != sorted(hand[p_index]):
            problems.append(f"プレイヤー {p_index} の手札 {sorted(p.hand)} が、ログから組み立てた {sorted(hand[p_index])} と違う")
        if sorted(p.discard) != sorted(discard[p_index]):
            problems.append(f"プレイヤー {p_index} のトラッシュ {sorted(p.discard)} が、ログから組み立てた {sorted(discard[p_index])} と違う")
        if starts and len(p.prizes) != state.rules.prize_count - prizes_taken[p_index]:
            problems.append(f"プレイヤー {p_index} のサイド {len(p.prizes)} 枚が、取ったサイドの数 {prizes_taken[p_index]} と合わない")
        if prizes_taken[p_index] > min(knocked[1 - p_index], state.rules.prize_count):
            problems.append(f"プレイヤー {p_index} が、相手のきぜつ {knocked[1 - p_index]} 回より多くサイドを取った")
        if state.phase in TERMINAL and state.phase is not Phase.HALTED and prizes_taken[p_index] != min(knocked[1 - p_index], state.rules.prize_count):
            problems.append(f"プレイヤー {p_index} の取ったサイド {prizes_taken[p_index]} 枚が、相手のきぜつ {knocked[1 - p_index]} 回と合わない")
    if {pokemon.pokemon_id for p in state.players for pokemon in p.in_play()} != in_play:
        problems.append("ログから組み立てた場のポケモンが状態と違う")
    if len(set(taken_cards)) != len(taken_cards):
        problems.append("同じサイドのカードを 2 回取った")
    # v0.47: 状態の期限のあるトレーナーの使用の禁止が、ログで与えてまだ消していない禁止と同じ
    if {(lock.player, lock.expires_turn) for lock in state.trainer_locks} != set(trainer_locks_log):
        problems.append(f"状態のトレーナーの使用の禁止 {state.trainer_locks} が、ログから組み立てた {sorted(trainer_locks_log)} と違う")
    if arrange_due is not None and not (state.decision is not None and state.decision.kind == "arrange_deck_top"):
        problems.append(f"{arrange_due['turn']} 番のみらいよちで見たカードの並べかえも、その決定もない（ログの最後）")
    for p in state.players:
        for pokemon in p.in_play():
            # v0.44: 状態の 1 度だけ使えるワザの記録・サカキの許可が、ログの記録と同じ
            recorded = {(card, index) for pid, card, index in once_used if pid == pokemon.pokemon_id}
            if set(pokemon.attacks_used_once) != recorded:
                problems.append(f"場のポケモン {pokemon.pokemon_id} の 1 度だけ使えるワザの記録 {pokemon.attacks_used_once} が、ログの記録 {sorted(recorded)} と違う")
            if pokemon.evolution_permission_turn is not None and (pokemon.pokemon_id, pokemon.evolution_permission_turn) not in permitted:
                problems.append(f"場のポケモン {pokemon.pokemon_id} のサカキの許可（{pokemon.evolution_permission_turn} 番）が、ログにない")
    for pid, evolved in evolve_turns.items():
        # v0.44: サカキの許可のある番は、同じ番に 2 回進化できる（進化した時点で許可があったことは evolve の分岐が確かめる）
        if len(evolved) > 2 or evolved != sorted(evolved) or any(turn <= 2 for turn in evolved) \
                or any(a == b and (pid, a) not in permitted for a, b in zip(evolved, evolved[1:])):
            problems.append(f"場のポケモン {pid} の進化の番 {evolved} が正しくない")
    for key, count in removed.items():
        if count > added.get(key, 0):
            problems.append(f"持続する効果 {key} を、与えた回数より多く消した")
    # v0.13: 状態の効果の種類（「ほのおのかべ」の retaliation・「こうらがえし」の retaliation_received_damage など）が、ログで与えた効果の種類と同じ
    for p in state.players:
        for pokemon in p.in_play():
            for effect in pokemon.persistent_effects:
                info = alive.get((pokemon.pokemon_id, effect.created_turn))
                if info is not None and info["kind"] != effect.kind:
                    problems.append(f"持続する効果 {(pokemon.pokemon_id, effect.created_turn)} の種類 {effect.kind} が、ログで与えた {info['kind']} と違う")
    remaining = {(pokemon.pokemon_id, e.created_turn) for p in state.players for pokemon in p.in_play() for e in pokemon.persistent_effects}
    for key, count in added.items():
        if count != 1:
            problems.append(f"持続する効果 {key} を {count} 回与えた")
        alive = removed[key] == 0
        if alive and key[0] in in_play and key not in remaining:
            problems.append(f"持続する効果 {key} が、消したログがないのに状態にない")
        if not alive and key in remaining:
            problems.append(f"持続する効果 {key} が、消したあとも状態に残っている")
    return problems


def _card_values(node, found: set) -> set:
    """観測（辞書・並び）の中の、カードの項目（``"card"``）の値（カードの uid）をすべて集める（v0.47）。"""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "card" and isinstance(value, int):
                found.add(value)
            else:
                _card_values(value, found)
    elif isinstance(node, (list, tuple)):
        for value in node:
            _card_values(value, found)
    return found


def _sees_private(event: dict, viewer) -> bool:
    """v0.47: 見えない項目のあるログのイベントで、その項目が ``viewer`` に見えてよいか（observation.PRIVATE_FIELDS とは別に、イベントの意味から書き直した規則）。"""
    kind = event["kind"]
    if kind == "game_created":
        return False  # seed から山札の並び・コインがわかる
    if kind == "look_at_card":
        return viewer is not None and (viewer == event["player"] or (event["zone"] == "hand" and viewer == event["owner"]))
    if kind == "take_deck_top":
        return event.get("destination") == "discard" or (viewer is not None and viewer in (event.get("looker"), event.get("player")))
    return viewer is not None and viewer == event.get("player")


def _effective_from_state(state, pokemon) -> dict:
    """v0.48: 観測と照らす、場のポケモンの今有効な最大HP・色・弱点・抵抗力（エンジンの問い合わせ ``effects.max_hp`` などとは別に、状態の持続する効果・いちばん上の
    カードの特殊能力・特殊状態・かがくへんかガス・［へんしょく］の記録から求める。観測の形の値）。"""
    from kyuura_engine.continuous import suppressors_of

    definition = _form_from_state(state, pokemon)  # v0.49: 今の姿のカード
    effects = {type(effect): effect for effect in pokemon.persistent_effects}
    hp = definition.hp
    shift_works = False
    held = ([state.card_def(pokemon.disguise)] if pokemon.disguise is not None else []) + [state.card_def(pokemon.card)]
    for power, owner_def in ((power, d) for d in held for power in d.powers):
        effect = state.effects.power_effect(owner_def.id, power)
        if isinstance(effect, MaxHpPerAttachedEnergyCards) and not suppressors_of(state, power):
            hp += effect.per * len([uid for uid in pokemon.energy
                                    if state.card_def(uid).is_basic_energy and state.card_def(uid).provides is effect.energy_type])
        if isinstance(effect, ShiftColor):
            shift_works = pokemon.conditions.exclusive is None and not suppressors_of(state, power)
    if MaxHpSet in effects:
        hp = effects[MaxHpSet].amount
    shift = pokemon.type_shift
    if shift is None:
        readings = [definition.pokemon_type]
    elif (shift.turn == state.turn_number and not shift.returned_to_bench and shift.source_card == pokemon.card and shift_works) \
            or shift.color is definition.pokemon_type:
        readings = [shift.color]
    else:
        readings = [shift.color, definition.pokemon_type]
    weakness = effects[WeaknessChange].color if WeaknessChange in effects else definition.weakness
    resistance = effects[ResistanceChange].color if ResistanceChange in effects else definition.resistance

    def color(value):
        return None if value is None else value.value

    return {"hp": hp, "pokemon_type": color(readings[0]) if len(readings) == 1 else None, "pokemon_type_readings": [color(c) for c in readings],
            "weakness": color(weakness), "resistance": color(resistance), "resistance_value": definition.resistance_value}


def _form_from_state(state, pokemon):
    """v0.49: 観測と照らす、場のポケモンの今の姿のカードの定義（エンジンの ``effects.current_form`` とは別に、状態から求める）。「ばける」でのせたカードがあればそのカード、
    いちばん上のカードが［へんしん］を持ち、バトル場にいて、ねむり・マヒ・こんらんでなく、かがくへんかガスに消されていなければ相手の対戦ポケモンのいちばん上の
    カード、どちらでもなければいちばん上のカード。"""
    from kyuura_engine.continuous import suppressors_of

    if pokemon.disguise is not None:
        return state.card_def(pokemon.disguise)
    definition = state.card_def(pokemon.card)
    owner = next(o for o, p in enumerate(state.players) if any(q is pokemon for q in p.in_play()))
    for power in definition.powers:
        if isinstance(state.effects.power_effect(definition.id, power), TransformIntoDefender) and state.players[owner].active is pokemon \
                and pokemon.conditions.exclusive is None and not suppressors_of(state, power) and state.players[1 - owner].active is not None:
            return state.card_def(state.players[1 - owner].active.card)
    return definition


def observation_problems(state) -> list[str]:
    """v0.47: プレイヤー（と観戦者）に渡す観測（``observation.observe``・``visible_log``。docs/fossil-hidden-info-v0.47.md 5 章）が、その人が見てよい情報だけを渡すか。

    - 手札: 持ち主か、相手の［おみとおし］がはたらいているとき（エンジンの ``hand_revealed_by`` とは別に、場のいちばん上のカード・ねむり・マヒ・こんらん・かがくへんかガス
      から求める）だけカードが見え、ほかは枚数だけ。山札・サイドは枚数だけ
    - 観測のどこにも、見えないカード（山札・サイド・見えない手札）の uid がない（uid の付け方からカードがわかる）。対戦準備のポケモンは表にするまで持ち主にだけ見える
    - 保留中の決定の選べるものは決めるプレイヤーだけに渡し、見えないカードの uid は、決めるプレイヤーが効果で見ている山札（``DECK_REVEALING_KINDS``）のときだけ
    - ログの写し: 見えない項目は、イベントの意味から決めた見てよい人（``_sees_private``）だけに残り、ほかには ``hidden`` に名前だけ。ほかのイベントは内部の記録と同じ
    """
    from kyuura_engine.continuous import suppressors_of
    from kyuura_engine.observation import DECK_REVEALING_KINDS, OPTION_MEANINGS, PRIVATE_FIELDS, observe, visible_log

    problems: list[str] = []
    revealed = {0: False, 1: False}
    for owner, p in enumerate(state.players):
        for pokemon in p.in_play():
            held = ([state.card_def(pokemon.disguise)] if pokemon.disguise is not None else []) + [state.card_def(pokemon.card)]  # v0.49
            for definition in held:
                for power in definition.powers:
                    effect = state.effects.power_effect(definition.id, power)
                    if isinstance(effect, RevealOpponentHand) and pokemon.conditions.exclusive is None and not suppressors_of(state, power):
                        revealed[1 - owner] = True
    used = state.trainer_in_use
    public = {uid for p in state.players for uid in p.discard} | ({used.card} if used is not None else set()) | {
        uid for p in state.players for pokemon in p.in_play() for uid in (*pokemon.cards(), *pokemon.energy, *(t.card for t in pokemon.trainers))}
    for viewer in (0, 1, None):
        view = observe(state, viewer)
        visible = set(public)
        for owner, (p, pv) in enumerate(zip(state.players, view["players"])):
            shows = viewer == owner or revealed[owner]
            cards = pv["hand"]["cards"]
            if pv["hand"]["count"] != len(p.hand) or shows != (cards is not None):
                problems.append(f"観測（{viewer}）のプレイヤー {owner} の手札が、見えるか（{shows}）・枚数 {len(p.hand)} と合わない")
            if cards is not None and [c["card"] for c in cards] != list(p.hand):
                problems.append(f"観測（{viewer}）のプレイヤー {owner} の手札のカードが、状態の手札と違う")
            if shows:
                visible.update(p.hand)
            if set(pv["deck"]) != {"count"} or set(pv["prizes"]) != {"count"} or pv["deck"]["count"] != len(p.deck) or pv["prizes"]["count"] != len(p.prizes):
                problems.append(f"観測（{viewer}）のプレイヤー {owner} の山札・サイドが、枚数だけではない")
            if state.turn_number == 0 and viewer != owner and p.active is not None and pv["active"] != {"face_down": True}:
                problems.append(f"観測（{viewer}）で、表にする前のプレイヤー {owner} の対戦準備のポケモンが見える")
            # v0.48: 見える場のポケモンの今有効な値（最大HP・色・弱点・抵抗力）が、状態から求めた値と同じ（観測とエンジンの処理が同じ値を使う）
            for pokemon, shown in zip(p.in_play(), [pv["active"], *pv["bench"]] if pv["active"] is not None else pv["bench"]):
                if shown.get("face_down"):
                    continue
                expected = _effective_from_state(state, pokemon)
                if {key: shown.get(key) for key in expected} != expected or shown.get("printed_hp") != state.card_def(pokemon.card).hp:
                    problems.append(f"観測（{viewer}）の場のポケモン {pokemon.pokemon_id} の今有効な値 {[shown.get(key) for key in expected]} が、"
                                    f"状態から求めた {list(expected.values())} と違う")
        board = {key: value for key, value in view.items() if key != "decision"}
        leaked = _card_values(board, set()) - visible
        if leaked:
            problems.append(f"観測（{viewer}）に、見えないカードの uid {sorted(leaked)} がある")
        d, dv = state.decision, view["decision"]
        if d is not None:
            if viewer != d.player and ("options" in dv or dv.get("option_count") != len(d.options)):
                problems.append(f"観測（{viewer}）に、ほかのプレイヤー {d.player} の決定の選べるものがある")
            if viewer == d.player and OPTION_MEANINGS[d.kind] == "card":
                for option in dv["options"]:
                    uid = option["value"]
                    if uid not in visible and d.kind not in DECK_REVEALING_KINDS:
                        problems.append(f"観測（{viewer}）の決定 {d.kind} の選べるものに、見えないカード {uid} がある")
                    if ("card_id" in option) != (uid in visible or d.kind in DECK_REVEALING_KINDS):
                        problems.append(f"観測（{viewer}）の決定 {d.kind} の選べるもの {uid} のカードの id の有無が、見えるかと合わない")
        for event, shown in zip(state.log, visible_log(state, viewer)):
            if event["kind"] in PRIVATE_FIELDS:
                fields = [name for name in PRIVATE_FIELDS[event["kind"]][0] if name in event]
                if _sees_private(event, viewer):
                    if shown != dict(event):
                        problems.append(f"ログの写し（{viewer}）の {event['kind']} が、見てよい内部の記録と違う")
                elif any(name in shown for name in fields) or set(shown.get("hidden", {})) != set(fields):
                    problems.append(f"ログの写し（{viewer}）の {event['kind']}（{event['turn']} 番）に、見えない項目 {fields} がある・hidden がない")
            elif shown != dict(event):
                problems.append(f"ログの写し（{viewer}）の公開のイベント {event['kind']} が、内部の記録と違う")
    return problems
