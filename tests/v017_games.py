"""v0.17 の新しいカードを含む 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで進める共通の手順（対戦相手の AI ではない）。

手順は tests/test_dark_wartortle_games_v0_13.py の ``policy_command``（v0.4e〜v0.13 の手順を順に重ねたもの）をそのまま使い、拒否された
操作の扱いも同じにする（どの拒否も、エンジンとは別に場から確かめてから数える。知らない拒否は失敗）。v0.17 のカードのための違いは
引数で渡す:

- ``not_declarable``: 使用を宣言しない特殊能力（``POWER_NOT_DECLARABLE``）を持つカード（v0.17b の R団のカビゴン）。
- ``extra_stop``: v0.17 で加えた止める理由（``UnsupportedError`` のコード → 場から確かめる関数）。関数は (拒否の前の状態, コマンド) を受け取り、
  止まるのが正しいなら True を返す。

数えた結果は、ログの監査（tests/log_audit.py）・書き出しの監査・不変条件とは別に、各テストが確かめる。
"""

from __future__ import annotations

from collections import Counter
from typing import Callable

from kyuura_engine.commands import RemoveDisguise  # v0.49
from kyuura_engine import (
    AttachEnergy, EvolvePokemon, IllegalActionError, PlayTrainer, Retreat, UnsupportedError, UseAttack, UsePokemonPower, apply_command, check_invariants,
    new_game, state_to_dict,
)
from kyuura_engine.effects import MAX_HP_DROP_CODE, PLAY_AS_POKEMON_RETREAT_CODE, evolution_preventers, max_hp, retreat_cost, trainer_use_blockers
from kyuura_engine.continuous import goop_gas_effects  # v0.59
from kyuura_engine.effects import GOOP_GAS_SCOPE_CODE, blaine_effects, energy_attach_block, energy_unit_count  # v0.59
from kyuura_engine.effects import retreat_trap_powers, scram_slots  # v0.61
from kyuura_engine.effects import POKEMON_TOWER_TRAINER_CODE, discard_to_hand_suppressor  # v0.74
from kyuura_engine.effects import STRANGE_GAS_SCOPE_CODE, retreat_guards, strange_gas_effects  # v0.87
from kyuura_engine.continuous import attack_field_power_suppressions  # v0.92
from kyuura_engine import effects as _E  # v0.117
from kyuura_engine.persistent import retreat_pursuits  # v0.117
from kyuura_engine.effects import DARK_WAVE_SCOPE_CODE, MEAN_LOOK_SOURCE_FORM_CODE  # v0.92
from kyuura_engine.persistent import source_bound_effects  # v0.92
from kyuura_engine.engine import LEAVE_ACTIVE_PREVENTED  # v0.93
from kyuura_engine.effects import (CLAMPING_JAW_SOURCE_DEVOLVED_CODE, JAW_CLAMP_SOURCE_EVOLVED_CODE, JAW_CLAMP_SOURCE_RETURNED_CODE,  # v0.93
                                   LEAVE_LOCK_KNOCKOUT_CODE, LEAVE_LOCK_NO_EFFECT_CODE, LEAVE_LOCK_SCRAM_CODE)
from kyuura_engine.state import PeriodAttackCoinCheck, PeriodLeaveLock  # v0.93
from kyuura_engine.persistent import cannot_retreat, powers_use_prevented
from kyuura_engine.effects import ATTACH_TRIGGER_ORDER_CODE, ATTACH_TRIGGER_SCOPE_CODE  # v0.116
from kyuura_engine.persistent import attach_status_triggers, evolution_lock  # v0.116
from tests.helpers import GIOVANNIS_MACHAMP, HAUNTER, MACHAMP, MUK, ROCKETS_MOLTRES
from tests.test_alakazam_games_v0_7 import POWER_REJECTIONS
from tests.test_blastoise_games_v0_6 import R13
from tests.test_confusion_games import TERMINAL
from tests.test_dark_wartortle_games_v0_13 import RETALIATION_STOP, retaliation_on
from tests.test_dark_wartortle_games_v0_13 import policy_command as base_policy_command
from tests.test_evolution_games_v0_4a import EVOLUTION_REJECTIONS
from tests.test_giovanni_games_v0_11 import EFFECT_STOP, guts_available
from tests.test_harden_games_v0_4b import REJECTIONS
from tests.test_haunter_games_v0_9 import EVADED_COIN, card_id, gas_on
from tests.test_haunter_games_v0_9 import working as evasion_working
from tests.test_machamp_games_v0_10 import DOUBLE_KO
from tests.test_machamp_games_v0_10 import working as counter_working
from tests.test_stage2_games_v0_4c import STAGE2_REJECTIONS

NOT_DECLARABLE = (MUK, MACHAMP, HAUNTER)  # v0.8〜v0.10（tests/test_dark_wartortle_games_v0_13.py と同じ）
USABLE_ONLY_WHEN = (ROCKETS_MOLTRES, GIOVANNIS_MACHAMP)  # v0.11・v0.12（決められたときにしか使えない）
EVOLUTION_HP_CODE = "UNRESOLVED_EVOLUTION_HP"  # v0.4a の H1（v0.48 から、［ガスのからだ］で最大HPが上がったポケモンの進化で自然な対戦でも起こる）


def full(state):
    return state_to_dict(state, format_version=9)


# v0.49（docs/virtual-attacks-transformation-v0.49.md）: 姿が変わりうるカードがあるときに、操作を受け付けない理由のコード
V049_FORM_CODES = ("UNRESOLVED_TRANSFORM_COPIED_POWER", "UNRESOLVED_TRANSFORM_MODIFIED_DEFENDER", "UNRESOLVED_SHAPESHIFT_SUPPRESSED",
                   "UNRESOLVED_SHAPESHIFT_ENTRY_POWER", "UNRESOLVED_SHAPESHIFT_AGAIN", MAX_HP_DROP_CODE)
FORM_CARDS = ("PMCG3-042", "PMCG5-019")  # メタモン（［へんしん］）・タケシのキュウコン（「ばける」）


def form_cards_in_play(state) -> bool:
    return any(state.cards[pokemon.card].card_id in FORM_CARDS for player in state.players for pokemon in player.in_play())


# v0.50（docs/mew-devolution-spray-v0.50.md）: 退化したポケモンの進化（DV2）・退化でいちばん上にもどったカードの「自分の番ごとに1回」の特殊能力（DV3）
V050_DEVOLUTION_CODES = ("UNRESOLVED_EVOLVE_AFTER_DEVOLUTION", "UNRESOLVED_POWER_REUSE_AFTER_DEVOLUTION")


def devolved_this_turn_in_play(state, command) -> bool:
    """v0.50: 操作の対象（進化させるポケモン・特殊能力を使うポケモン。ポケモン育て屋さんなら使うプレイヤーの場）に、この番に退化したポケモンがいる。"""
    if isinstance(command, EvolvePokemon):
        found = state.find_pokemon(command.target)
        return found is not None and found[1].devolved_turn == state.turn_number
    if isinstance(command, UsePokemonPower):
        found = state.find_pokemon(command.pokemon)
        return found is not None and found[1].devolved_turn == state.turn_number
    return any(pokemon.devolved_turn == state.turn_number for pokemon in state.players[command.player].in_play())


# v0.58: 特殊エネルギーで決まらない場面のコード（docs/stadium-reuse-special-energy-v0.58.md）
V058_ENERGY_CODES = ("UNRESOLVED_RAINBOW_ENERGY_TYPE", "UNRESOLVED_RAINBOW_ATTACH_AS_TYPE", "UNRESOLVED_RAINBOW_AS_BASIC_ENERGY_CARD",
                     "UNRESOLVED_RAINBOW_DAMAGE_RECEIVED_POWER", "UNRESOLVED_TRANSFORM_SPECIAL_ENERGY", "UNRESOLVED_RETREAT_OVERPAY")


def special_energy_in_game(state) -> bool:
    """v0.58: 特殊エネルギーカードが、どちらかのプレイヤーの場（ついている）か手札にある。"""
    return any(state.card_def(uid).is_special_energy for player in state.players
               for uid in [*player.hand, *(u for pokemon in player.in_play() for u in pokemon.energy)])


# v0.59: クリスタルビームでつけられないポケモンへの手札からつける通常の操作・カツラの 2 枚目（BL1）
V059_ATTACH_CODES = ("ENERGY_ATTACH_PREVENTED", "UNRESOLVED_BLAINE_SECOND_ATTACH")


# v0.61（docs/reactive-powers-trainer-damage-v0.61.md）: ［おとしあな］の時点（SH1）・［ずらかる］の時点（SC1）・［ずらかる］の力がもどる時（SC2）・
# バトル場は穴だらけ!のダメージの変更（TD1）
V061_CODES = ("UNRESOLVED_SINKHOLE_TIMING", "UNRESOLVED_SCRAM_TIMING", "UNRESOLVED_SCRAM_POWER_RESTORED", "UNRESOLVED_TRAINER_DAMAGE_REDUCTION")


def v061_stop_expected(state, command, code) -> bool:
    """v0.61: 場から確かめる。SH1 は「にげる」で、相手の場にはたらく［おとしあな］がある。SC1・SC2 は場に［ずらかる］を持つポケモンがいる。TD1 はバトル場は
    穴だらけ!を使う。"""
    if code == "UNRESOLVED_SINKHOLE_TIMING":
        return isinstance(command, Retreat) and bool(retreat_trap_powers(state, command.player))
    if code in ("UNRESOLVED_SCRAM_TIMING", "UNRESOLVED_SCRAM_POWER_RESTORED"):
        return bool(scram_slots(state))
    return isinstance(command, PlayTrainer) and state.cards[command.card].card_id == "PMCG4-055"


# v0.117（docs/retreat-return-active-powers-v0.117.md）: ［CHASE］・おいうち（RR1・「にげる」の中で扱えないおいうちのダメージ）、［ときわたり］（TW1・TW2）、［QUICKEN］（QK1）、
# ［でんせつのからだ］（LB1・LB2・決定を待つあいだのトラッシュ）、ぱっときえる（VH1）、もちさるとESP（ES4）で止まる場面
V117_CODES = ("UNRESOLVED_RETREAT_REACTION_TIMING", "UNSUPPORTED_PURSUIT_DAMAGE_REACTION", "UNRESOLVED_TIME_TRAVEL_TIMING", "UNRESOLVED_TIME_TRAVEL_OVERLAP",
              "UNRESOLVED_QUICKEN_EFFECT_SUPPRESSED", "UNRESOLVED_LEGEND_BODY_TRAINER_TARGET", "UNRESOLVED_LEGEND_BODY_GOOP_GAS", "UNSUPPORTED_LEGEND_BODY_PENDING_DISCARD",
              "UNRESOLVED_VANISH_OTHER_ATTACHED", "UNRESOLVED_ESP_LEFT_BEFORE_COIN")


def _v117_holders(state, kind) -> list:
    return [p for side in state.players for p in side.in_play() if not state.is_face_down(p)
            and any(isinstance(slot.effect, kind) for slot in _E.powers_of(state, p))]


def v117_stop_expected(state, command, code) -> bool:
    """v0.117: 場から確かめる（エンジンの問い合わせの答えではなく、場のカード・効果の有無で）。RR1・おいうちの未対応は「にげる」で、相手のバトル場に［CHASE］のアンノーンC がいるか、
    にげるポケモンがおいうちの効果を受けている。TW1・TW2 は場に［ときわたり］のポケモンがいる。QK1 は［QUICKEN］の効果がはたらく番。LB1・決定を待つあいだのトラッシュは場に
    ［でんせつのからだ］のポケモンがいる（LB2 はさらにまきちらせ!ベトベトガスの効果か、それを使う）。VH1・ES4 はぱっときえる・もちさるで、使うポケモンにエネルギーでないカード・ESPがつく。"""
    if code in ("UNRESOLVED_RETREAT_REACTION_TIMING", "UNSUPPORTED_PURSUIT_DAMAGE_REACTION"):
        if not isinstance(command, Retreat):
            return False
        active = state.players[command.player].active
        return bool(_E.retreat_chase_holders(state, command.player) or retreat_pursuits(state, active))
    if code in ("UNRESOLVED_TIME_TRAVEL_TIMING", "UNRESOLVED_TIME_TRAVEL_OVERLAP"):
        return bool(_v117_holders(state, _E.ReturnToDeckOnHeadsInsteadOfKnockOut))
    if code == "UNRESOLVED_QUICKEN_EFFECT_SUPPRESSED":
        return any(r.kind == "group_attack_immunity" and r.created_turn + 1 == state.turn_number for r in state.trainer_effects)
    if code in ("UNRESOLVED_LEGEND_BODY_TRAINER_TARGET", "UNSUPPORTED_LEGEND_BODY_PENDING_DISCARD"):
        return bool(_v117_holders(state, _E.ImmuneToTrainersWhileActive))
    if code == "UNRESOLVED_LEGEND_BODY_GOOP_GAS":
        plays_gas = isinstance(command, PlayTrainer) and state.cards[command.card].card_id == "PMCG4-056"
        return bool(_v117_holders(state, _E.ImmuneToTrainersWhileActive)) and (plays_gas or bool(goop_gas_effects(state)))
    if not isinstance(command, UseAttack):
        return False
    attacker = state.players[command.player].active
    if code == "UNRESOLVED_VANISH_OTHER_ATTACHED":
        return bool(attacker.trainers) or any(state.card_def(uid).category != "energy" for uid in attacker.energy)
    return bool(_E.esp_cards(state, attacker))  # ES4


# v0.93（docs/active-leave-locks-v0.93.md）: 「バトル場をはなれられない」効果（にげる・すてるの拒否・AL1〜AL3）・くいつく（JC1・JC2）・かぶりつく（CJ1）で止まる・拒否する場面
V093_LEAVE_CODES = (LEAVE_ACTIVE_PREVENTED, LEAVE_LOCK_KNOCKOUT_CODE, LEAVE_LOCK_NO_EFFECT_CODE, LEAVE_LOCK_SCRAM_CODE, JAW_CLAMP_SOURCE_RETURNED_CODE,
                    JAW_CLAMP_SOURCE_EVOLVED_CODE, CLAMPING_JAW_SOURCE_DEVOLVED_CODE)


def v093_lock_in_play(state) -> bool:
    """v0.93: 場のポケモンが、はなれられない効果か期間を明示した手順 4 のコイン（かぶりつく）を受けている（止める理由を場から確かめる）。"""
    return any(isinstance(effect, (PeriodLeaveLock, PeriodAttackCoinCheck)) for side in state.players for pokemon in side.in_play()
               for effect in pokemon.persistent_effects)


def play_game(decks, seed, *, cure=True, max_steps=10000, not_declarable=(), extra_stop: dict[str, Callable] | None = None,
              double_ko_check: Callable | None = None, policy=None):
    """``decks``（2 つの 60 枚）・``seed`` の対戦を終わるまで進める。受け付けた操作の列と、拒否された操作・場面の観測を返す。

    ``double_ko_check`` は ``UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT``（C18）で止まったときに、場から確かめる関数（既定は「相手の
    対戦ポケモンに、はたらいている「はんげき」がある」。v0.17b は「わるいねぞう」も確かめる関数を渡す）。"""
    extra_stop = extra_stop or {}
    policy = policy or base_policy_command
    state = new_game(*decks, seed)
    commands, observed, tried = [], Counter(), {}
    for _ in range(max_steps):
        if state.phase in TERMINAL:
            return state, commands, observed
        while True:
            turn_tried = tried.setdefault(state.turn_number, set())
            command = policy(state, janken_winner=seed % 2, cure=cure, tried=turn_tried)
            try:
                new = apply_command(state, command)
                break
            except (IllegalActionError, UnsupportedError) as error:
                observed["rejected"] += 1
                if error.code in V049_FORM_CODES and isinstance(command, (Retreat, PlayTrainer, EvolvePokemon, UsePokemonPower, RemoveDisguise)) \
                        and form_cards_in_play(state):
                    # v0.49: 決められない姿（TF1・TF2・DG1）・「ばける」（DG2・DG3）・思い出させる（RC1・RC4）・［へんしん］・「ばける」で最大HPが下がる（MH1）。
                    # 場から確かめる（メタモン・タケシのキュウコンが場にいる。思い出させるは対戦ポケモンが進化していない・ばけている）。同じ操作を繰り返さない
                    kind = type(command).__name__
                    observed[f"stopped_{kind}_{error.code}"] += 1
                    turn_tried.add("retreat" if kind == "Retreat" else ("max_hp_drop_card", command.card) if kind in ("PlayTrainer", "EvolvePokemon")
                                   else ("max_hp_drop_command", command))
                    continue
                if error.code in V058_ENERGY_CODES and special_energy_in_game(state):
                    # v0.58: 特殊エネルギーで決まらない場面（RB1〜RB4・TE2・RT1）。場から確かめる（特殊エネルギーが場か手札にある）。同じ操作を繰り返さない
                    kind = type(command).__name__
                    observed[f"stopped_{kind}_{error.code}"] += 1
                    turn_tried.add(("attack_index", command.attack_index) if kind == "UseAttack" else "retreat" if kind == "Retreat"
                                   else ("max_hp_drop_card", command.card) if kind in ("PlayTrainer", "EvolvePokemon") else ("max_hp_drop_command", command))
                    continue
                if error.code in ("UNRESOLVED_RECALL_WITHOUT_PRE_EVOLUTION_ATTACK", "UNRESOLVED_RECALL_FORM") and isinstance(command, PlayTrainer):
                    active = state.players[command.player].active
                    if active.evolution_stack and active.disguise is None:
                        raise AssertionError(f"対戦ポケモンが進化していて「ばける」でもないのに {error.code}: {command}")
                    observed[f"stopped_PlayTrainer_{error.code}"] += 1
                    turn_tried.add(("max_hp_drop_card", command.card))
                    continue
                if error.code == POKEMON_TOWER_TRAINER_CODE and isinstance(command, PlayTrainer):
                    # v0.74: ポケモンタワーで効果がすべて消えるトレーナー（エネルギー回収・ダウジングマシーンなど。PT1）。場から確かめる（場のスタジアムがポケモンタワー）。
                    # この番はそのカードを使わない
                    if discard_to_hand_suppressor(state) is None:
                        raise AssertionError(f"場のスタジアムがポケモンタワーでないのに {error.code}: {command}")
                    observed[f"stopped_PlayTrainer_{error.code}"] += 1
                    turn_tried.add(("max_hp_drop_card", command.card))
                    continue
                if error.code == GOOP_GAS_SCOPE_CODE and goop_gas_effects(state):
                    # v0.59: まきちらせ!ベトベトガスの効果がはたらいている間に、特殊能力を持つポケモンを場に出す・進化・退化させる（GG1）。場から確かめる
                    # （効果がはたらいている）。同じカード・操作を繰り返さない
                    kind = type(command).__name__
                    observed[f"stopped_{kind}_{error.code}"] += 1
                    card = getattr(command, "card", None)
                    turn_tried.add(("max_hp_drop_card", card) if card is not None and card in state.players[command.player].hand
                                   else ("max_hp_drop_command", command))
                    continue
                if error.code in (DARK_WAVE_SCOPE_CODE, "POWER_SUPPRESSED") and attack_field_power_suppressions(state) and not isinstance(command, UseAttack):
                    # v0.92: ナツメのゲンガーの「やみのはどう」の効果がはたらいている間に、特殊能力を持つポケモンを場に出す・進化させる（DW1）・特殊能力を使う（止まっている）。
                    # 場から確かめる（効果がはたらいている）。同じカード・操作を繰り返さない
                    kind = type(command).__name__
                    observed[f"stopped_{kind}_{error.code}"] += 1
                    card = getattr(command, "card", None)
                    turn_tried.add(("max_hp_drop_card", card) if card is not None and card in state.players[command.player].hand
                                   else ("max_hp_drop_command", command))
                    continue
                if error.code == MEAN_LOOK_SOURCE_FORM_CODE and getattr(command, "target", None) is not None:
                    # v0.92: くろいまなざしの発生源（まねた場合はまねたポケモン）を進化・退化させる（ML2）。場から確かめる（その場のポケモンが発生源の効果がある）
                    found = state.find_pokemon(command.target)
                    if found is None or not source_bound_effects(state, found[0], found[1]):
                        raise AssertionError(f"くろいまなざしの発生源でないのに {error.code}: {command}")
                    observed[f"stopped_{type(command).__name__}_{error.code}"] += 1
                    turn_tried.add(("max_hp_drop_card", command.card))
                    continue
                if error.code in V093_LEAVE_CODES:
                    # v0.93: 「バトル場をはなれられない」効果を受けたポケモンの「にげる」・すてる（LEAVE_ACTIVE_PREVENTED）、移動だけが効果の使用・選択・コイン（AL2）、きぜつ（AL1）、
                    # ［ずらかる］（AL3）、くいつく・かぶりつくの発生源（JC1・JC2・CJ1）。場から確かめる（その効果を受けているポケモンがいる）。同じ操作を繰り返さない
                    if not v093_lock_in_play(state):
                        raise AssertionError(f"はなれられない効果・かぶりつくの効果がないのに {error.code}: {command}")
                    if error.code == LEAVE_ACTIVE_PREVENTED and not any(isinstance(e, PeriodLeaveLock) for e in state.players[command.player].active.persistent_effects):
                        raise AssertionError(f"バトル場のポケモンがはなれられない効果を受けていないのに {error.code}: {command}")
                    kind = type(command).__name__
                    observed[f"stopped_{kind}_{error.code}"] += 1
                    turn_tried.add("retreat" if kind == "Retreat" else ("attack_index", command.attack_index) if kind == "UseAttack"
                                   else ("max_hp_drop_card", command.card) if kind in ("PlayTrainer", "EvolvePokemon") else ("max_hp_drop_command", command))
                    if kind == "UseAttack":
                        turn_tried.add(error.code)
                    continue
                if error.code in (STRANGE_GAS_SCOPE_CODE, "POWER_SUPPRESSED") and strange_gas_effects(state, command.player) \
                        and not isinstance(command, UseAttack):
                    # v0.87: ドガースの「ふしぎなガス」の効果がはたらいている側で、特殊能力を持つポケモンを場に出す・進化させる（MG1）・特殊能力を使う（止まっている）。
                    # 場から確かめる（その側にふしぎなガスがはたらいている）。同じカード・操作を繰り返さない
                    kind = type(command).__name__
                    observed[f"stopped_{kind}_{error.code}"] += 1
                    card = getattr(command, "card", None)
                    turn_tried.add(("max_hp_drop_card", card) if card is not None and card in state.players[command.player].hand
                                   else ("max_hp_drop_command", command))
                    continue
                if error.code == "UNRESOLVED_CONDUCTIVITY_MULTIPLE_SOURCES" and sum(
                        state.cards[p.card].card_id == "neo4-046" for pl in state.players for p in pl.in_play()) >= 2:
                    # v0.86 の CV1（わるいデンリュウの［かんでん］の発生源が 2 匹以上）。v0.87 の組で手札からつける通常の操作に当たった。場から確かめる。同じ操作を繰り返さない
                    kind = type(command).__name__
                    observed[f"stopped_{kind}_{error.code}"] += 1
                    turn_tried.add(("attack_index", command.attack_index) if kind == "UseAttack" else ("max_hp_drop_card", getattr(command, "energy", None))
                                   if kind == "AttachEnergy" else ("max_hp_drop_command", command))
                    continue
                if error.code in V061_CODES and v061_stop_expected(state, command, error.code):
                    # v0.61: ［おとしあな］の時点（SH1）・［ずらかる］の時点（SC1）・力がもどる時（SC2）・バトル場は穴だらけ!のダメージの変更（TD1）。場から確かめる
                    # （［おとしあな］・［ずらかる］を持つポケモンが場にいる、バトル場は穴だらけ!を使う）。同じ操作を繰り返さない
                    kind = type(command).__name__
                    observed[f"stopped_{kind}_{error.code}"] += 1
                    turn_tried.add("retreat" if kind == "Retreat" else ("max_hp_drop_card", command.card) if kind in ("PlayTrainer", "EvolvePokemon")
                                   else ("attack_index", command.attack_index) if kind == "UseAttack" else ("max_hp_drop_command", command))
                    if kind == "UseAttack":
                        turn_tried.add(error.code)
                    continue
                if error.code in V117_CODES:
                    # v0.117: 場から確かめる（``v117_stop_expected``）。同じ操作を繰り返さない
                    if not v117_stop_expected(state, command, error.code):
                        raise AssertionError(f"場から確かめると止まらないはずなのに {error.code}: {command}")
                    kind = type(command).__name__
                    observed[f"stopped_{kind}_{error.code}"] += 1
                    turn_tried.add("retreat" if kind == "Retreat" else ("max_hp_drop_card", command.card) if kind in ("PlayTrainer", "EvolvePokemon")
                                   else ("attack_index", command.attack_index) if kind == "UseAttack" else ("max_hp_drop_command", command))
                    if kind == "UseAttack":
                        turn_tried.add(error.code)
                    continue
                if error.code == MAX_HP_DROP_CODE and isinstance(command, (Retreat, PlayTrainer, EvolvePokemon, UsePokemonPower)):
                    # v0.48: 最大HPが、ダメージ以外の原因（「きょだいか」の効果が消える・かがくへんかガスで［ガスのからだ］が消える）でのっているダメージ以下に
                    # 下がる（MH1）。場から確かめる（今有効な最大HPがカードの HP より大きく、のっているダメージがカードの HP 以上のポケモンがいる）
                    if not any(p.damage >= state.card_def(p.card).hp and max_hp(state, p) > state.card_def(p.card).hp
                               for player in state.players for p in player.in_play()):
                        raise AssertionError(f"最大HPがのっているダメージより大きいポケモンがいないのに {error.code}: {command}")
                    kind = type(command).__name__
                    observed[f"stopped_{kind}_{error.code}"] += 1
                    # 同じ操作を繰り返さない（「にげる」は "retreat"、手札のカードを使う操作はそのカード、特殊能力は操作そのもの。手順が見る）
                    turn_tried.add("retreat" if kind == "Retreat" else ("max_hp_drop_card", command.card) if kind in ("PlayTrainer", "EvolvePokemon")
                                   else ("max_hp_drop_command", command))
                    continue
                if error.code in V050_DEVOLUTION_CODES and isinstance(command, (EvolvePokemon, PlayTrainer, UsePokemonPower)):
                    # v0.50: この番に退化したポケモンを進化させる（DV2。手札からの進化・ポケモン育て屋さん・［うか］）・この番に使った「自分の番ごとに1回」の特殊能力を、
                    # 退化でいちばん上にもどったカードでもう一度使う（DV3）。場から確かめる（この番に退化したポケモンがいる）。同じ操作を繰り返さない
                    if not devolved_this_turn_in_play(state, command):
                        raise AssertionError(f"この番に退化したポケモンがいないのに {error.code}: {command}")
                    kind = type(command).__name__
                    observed[f"stopped_{kind}_{error.code}"] += 1
                    turn_tried.add(("max_hp_drop_card", command.card) if kind in ("PlayTrainer", "EvolvePokemon") else ("max_hp_drop_command", command))
                    continue
                if error.code == EVOLUTION_HP_CODE and isinstance(command, EvolvePokemon):
                    # v0.48: ［ガスのからだ］で最大HPが印刷の HP より大きいポケモンを、のっているダメージ以下の HP のカードに進化させる（v0.4a の H1 と同じ問い）。
                    # 場から確かめる（進化先の HP がのっているダメージ以下）。同じカードを繰り返さない
                    target = state.find_pokemon(command.target)
                    if target is None or target[1].damage < state.card_def(command.card).hp:
                        raise AssertionError(f"進化先の HP がのっているダメージより大きいのに {error.code}: {command}")
                    observed[f"stopped_EvolvePokemon_{error.code}"] += 1
                    turn_tried.add(("max_hp_drop_card", command.card))
                    continue
                if isinstance(command, UsePokemonPower):
                    kind = card_id(state, state.find_pokemon(command.pokemon)[1])
                    if error.code == "POWER_NOT_USABLE_NOW" and kind in USABLE_ONLY_WHEN and not gas_on(state):
                        observed[f"rejected_declare_{kind}"] += 1
                        continue
                    if error.code == "POWER_NOT_DECLARABLE" and kind in NOT_DECLARABLE + tuple(not_declarable):
                        observed[f"rejected_declare_{kind}"] += 1
                        continue
                    if error.code == "POWER_SUPPRESSED" and gas_on(state):
                        observed["suppressed_power"] += 1
                        continue
                    if error.code == "POWER_SUPPRESSED" and goop_gas_effects(state):
                        # v0.59: まきちらせ!ベトベトガスの効果がはたらいている。この番は特殊能力を使わない
                        observed["suppressed_power_goop_gas"] += 1
                        turn_tried.add(("max_hp_drop_command", command))
                        continue
                    if error.code in ("ENERGY_ATTACH_PREVENTED", "UNRESOLVED_ATTACH_BLOCK_SCOPE") and any(
                            energy_attach_block(state, pk) is not None for pl in state.players for pk in pl.in_play()):
                        # v0.59: クリスタルビームを受けたポケモンに、あまごいでつける（ENERGY_ATTACH_PREVENTED）・エナジートランスなどでつけかえる（CB1）
                        observed[f"stopped_power_{error.code}"] += 1
                        turn_tried.add(("max_hp_drop_command", command))
                        continue
                    if error.code in (ATTACH_TRIGGER_SCOPE_CODE, ATTACH_TRIGGER_ORDER_CODE, "UNRESOLVED_REPARALYSIS_RECOVERY_TURN") and any(
                            attach_status_triggers(state, pk) for pl in state.players for pk in pl.in_play()):
                        # v0.116: しこみどく・エナジーショックの効果がはたらいているポケモンに、エナジートランスなどでつけ替える（AT1）・山札やトラッシュからつける特殊能力で、マヒと
                        # ［ほのおでかいふく］が同じ時点にはたらく（エンジンの未対応）・あまごいなどでマヒ状態のポケモンにつけ、再びマヒになる（v0.3b の問い）。場から確かめる。
                        # この番はその使用をくり返さない
                        observed[f"stopped_power_{error.code}"] += 1
                        turn_tried.add(("max_hp_drop_command", command))
                        continue
                    if error.code == "POWER_USE_PREVENTED" and powers_use_prevented(state, state.find_pokemon(command.pokemon)[1]) is not None:
                        # v0.59: 「ショックアイ」を受けたポケモン。この番はその使用をくり返さない
                        observed["stopped_power_POWER_USE_PREVENTED"] += 1
                        turn_tried.add(("max_hp_drop_command", command))
                        continue
                    if error.code not in POWER_REJECTIONS:
                        raise
                    observed[f"rejected_power_{error.code}"] += 1
                    continue
                if isinstance(command, UseAttack) and error.code in extra_stop:
                    if not extra_stop[error.code](state, command):
                        raise AssertionError(f"場から確かめると止まらないはずなのに {error.code}: {command}")
                    observed[f"stopped_attack_{error.code}"] += 1
                    turn_tried.update({error.code, ("attack_index", command.attack_index)})
                    continue
                if isinstance(command, UseAttack) and error.code == RETALIATION_STOP:
                    target = state.players[1 - state.current_player].active
                    if not retaliation_on(state, target):
                        raise AssertionError(f"ダメージを返す効果がはたらいていないのに {RETALIATION_STOP}: {command}")
                    observed[f"stopped_attack_{RETALIATION_STOP}"] += 1
                    turn_tried.update({"retaliation_double", ("attack_index", command.attack_index)})
                    continue
                if isinstance(command, UseAttack) and error.code == EFFECT_STOP:
                    target = state.players[1 - state.current_player].active
                    if not guts_available(state, target):
                        raise AssertionError(f"「こんじょう」を使えないのに {EFFECT_STOP}: {command}")
                    observed[f"stopped_attack_{EFFECT_STOP}"] += 1
                    turn_tried.update({"guts_effect", ("attack_index", command.attack_index)})
                    continue
                if isinstance(command, UseAttack) and error.code == DOUBLE_KO:
                    target = state.players[1 - state.current_player].active
                    if not (double_ko_check or (lambda s, t: counter_working(s, t)))(state, target):
                        raise AssertionError(f"ダメージを受けたときにはたらく特殊能力がないのに {DOUBLE_KO}: {command}")
                    observed[f"stopped_attack_{DOUBLE_KO}"] += 1
                    turn_tried.update({"counter_double", ("attack_index", command.attack_index)})
                    continue
                if isinstance(command, UseAttack) and error.code == EVADED_COIN:
                    target = state.players[1 - state.current_player].active
                    if not evasion_working(state, target):
                        raise AssertionError(f"「とうめい」がはたらいていないのに {EVADED_COIN}: {command}")
                    observed[f"stopped_attack_{EVADED_COIN}"] += 1
                    turn_tried.update({"evaded_coin", ("attack_index", command.attack_index)})
                    continue
                if isinstance(command, Retreat) and error.code == "RETREAT_PREVENTED":
                    # v0.36: 「にげる」ことができない効果（アイスバーン・わしづかみ）を受けたポケモン。場から確かめる（エネルギー・コインの前に拒否）
                    # v0.87: 相手のバトル場の［とおせんぼ］（カビゴン）も
                    if cannot_retreat(state, state.players[command.player].active) is None and not retreat_guards(state, command.player):
                        raise AssertionError(f"「にげる」ことができない効果がないのに RETREAT_PREVENTED: {command}")
                    observed["stopped_retreat_RETREAT_PREVENTED"] += 1
                    turn_tried.add("retreat")
                    continue
                if isinstance(command, Retreat) and error.code == "WRONG_RETREAT_COST":
                    # v0.46: 常にはたらく特殊能力（［ねんちゃくえき］・［にげるサポート］）で「にげる」のエネルギーの数が変わり、印刷の数で宣言した。場から確かめる
                    # （特殊能力がなければ、今までどおり想定外の拒否）
                    cost = retreat_cost(state, command.player)
                    # v0.59: ［エネエネ］でエネルギーとして残ったカード（2 個）は、枚数とエネルギーの個数が違う。印刷の数の枚数で選ぶ手順は余計に選ぶ
                    units = energy_unit_count(state, command.discard, state.players[command.player].active)
                    if (not cost.modified and units == len(command.discard)) or cost.allows(units):
                        raise
                    observed["stopped_retreat_WRONG_RETREAT_COST"] += 1
                    turn_tried.add("retreat")
                    continue
                if isinstance(command, Retreat) and error.code == "UNRESOLVED_RETREAT_COST_FLOOR":
                    # v0.46: 少なくする数と増やす数の当てはめ方で、トラッシュしてよい数が変わる（CP2）。場から確かめる
                    if not retreat_cost(state, command.player).floor_ambiguous(len(command.discard)):
                        raise AssertionError(f"にげるエネルギーの読み方で答えが変わらないのに {error.code}: {command}")
                    observed[f"stopped_retreat_{error.code}"] += 1
                    turn_tried.add("retreat_floor")
                    continue
                if isinstance(command, Retreat) and error.code == PLAY_AS_POKEMON_RETREAT_CODE:
                    # v0.47: バトル場のなにかの化石・ピッピ人形の「にげる」は決まらない（PF2）。場から確かめる（エネルギー・コインの前に拒否）
                    if state.card_def(state.players[command.player].active.card).play_role is None:
                        raise AssertionError(f"バトル場がなにかの化石・ピッピ人形でないのに {error.code}: {command}")
                    observed[f"stopped_retreat_{error.code}"] += 1
                    turn_tried.add("retreat")
                    continue
                if isinstance(command, PlayTrainer) and error.code == "TRAINER_PREVENTED":
                    # v0.46: はたらいている［アレルギーかふん］（わるいラフレシア）。v0.47 から、期限のあるトレーナーの使用の禁止（ずつう・こうしゅうは）も。
                    # 場と状態から確かめる（手札から出す前に拒否）
                    if not trainer_use_blockers(state, command.player):
                        raise AssertionError(f"トレーナーカードを使えなくする特殊能力がはたらいていないのに TRAINER_PREVENTED: {command}")
                    observed["stopped_trainer_TRAINER_PREVENTED"] += 1
                    turn_tried.add("trainer_locked")
                    continue
                if isinstance(command, AttachEnergy) and error.code == "UNRESOLVED_REPARALYSIS_RECOVERY_TURN":
                    # v0.116: エナジーショックの効果がはたらいているマヒ状態のポケモンにつける（ついたことで再びマヒ状態になる効果を受け、回復する番が変わる。v0.3b の問い）。
                    # 場から確かめる（つける先がマヒ状態で、マヒの、ついた時に発動する持続効果がはたらいている）。この番はつけない
                    target = next((pk for pl in state.players for pk in pl.in_play() if pk.card == command.target), None)
                    if target is None or not target.conditions.paralyzed or not any(effect.condition == "paralysis" for effect in attach_status_triggers(state, target)):
                        raise AssertionError(f"マヒの、ついた時に発動する効果がはたらいていないのに {error.code}: {command}")
                    observed[f"stopped_attach_{error.code}"] += 1
                    turn_tried.add("attach_blocked")
                    continue
                if isinstance(command, AttachEnergy) and error.code in V059_ATTACH_CODES:
                    # v0.59: クリスタルビームでエネルギーカードをつけることができないポケモン（ENERGY_ATTACH_PREVENTED）・カツラの 1 枚目のあとの 2 枚目（BL1）。
                    # 場から確かめる（受けているポケモン・この番のカツラの効果）。この番はつけない
                    target = next((pk for pl in state.players for pk in pl.in_play() if pk.card == command.target), None)
                    blocked = target is not None and energy_attach_block(state, target) is not None
                    if not (blocked if error.code == "ENERGY_ATTACH_PREVENTED" else blaine_effects(state, command.player)):
                        raise AssertionError(f"場から確かめると止まらないはずなのに {error.code}: {command}")
                    observed[f"stopped_attach_{error.code}"] += 1
                    turn_tried.add("attach_blocked")
                    continue
                if isinstance(command, AttachEnergy):
                    if error.code != R13:
                        raise
                    observed[f"stopped_attach_{error.code}"] += 1
                    turn_tried.add("attach_blocked")
                    continue
                if isinstance(command, EvolvePokemon) and error.code == "EVOLUTION_PREVENTED" and not evolution_preventers(state) and evolution_lock(
                        state, state.find_pokemon(command.target)[1]) is not None:
                    # v0.116: やみのしょくしゅの効果を受けたポケモン（次の相手の番、手札・トレーナーの効果で進化させることができない）。場から確かめる。この番はそのカードを使わない
                    # （ほかのポケモンへの進化は止めない）
                    observed["stopped_evolve_EVOLUTION_PREVENTED_lock"] += 1
                    turn_tried.add(("max_hp_drop_card", command.card))
                    continue
                if isinstance(command, EvolvePokemon) and error.code == "EVOLUTION_PREVENTED":
                    # v0.47: はたらいている［げんしのちから］（プテラ）。場から確かめる（重ねる前に拒否）
                    # v0.80: 退化スプレーHYPER でその番に退化させたポケモン（evolution_ban）も、同じコードで拒否する
                    banned = any(record.kind == "evolution_ban" and record.pokemon_id == command.target for record in state.trainer_effects)
                    if not evolution_preventers(state) and not banned:
                        raise AssertionError(f"進化できなくする特殊能力がはたらいていないのに EVOLUTION_PREVENTED: {command}")
                    observed["stopped_evolve_EVOLUTION_PREVENTED_ban" if banned else "stopped_evolve_EVOLUTION_PREVENTED"] += 1
                    turn_tried.update({"evolution_prevented", "evolve", "evolve2"})
                    continue
                if isinstance(command, EvolvePokemon):
                    stage2 = state.card_def(command.card).is_stage2_pokemon
                    if error.code in (STAGE2_REJECTIONS if stage2 else EVOLUTION_REJECTIONS):
                        observed[f"rejected_{'evolve2' if stage2 else 'evolve'}_{error.code}"] += 1
                        turn_tried.add("evolve2" if stage2 else "evolve")
                        continue
                if error.code not in REJECTIONS:
                    raise
                kind = "attack" if isinstance(command, UseAttack) else "retreat"
                observed[f"rejected_{kind}_{error.code}"] += 1
                turn_tried.add(kind)
        problems = check_invariants(new)
        if problems:
            raise AssertionError(problems)
        observed["accepted"] += 1
        if isinstance(command, UseAttack):
            attacker = state.players[command.player].active
            observed[f"attack_{state.cards[attacker.card].card_id}#{command.attack_index}"] += 1  # v0.67: うらのカードでも数える
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def events_of(state, kind):
    return [dict(e) for e in state.log if e["kind"] == kind]
