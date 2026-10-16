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

from kyuura_engine import (
    AttachEnergy, EvolvePokemon, IllegalActionError, Retreat, UnsupportedError, UseAttack, UsePokemonPower, apply_command, check_invariants, new_game,
    state_to_dict,
)
from kyuura_engine.persistent import cannot_retreat
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


def full(state):
    return state_to_dict(state, format_version=9)


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
                    if cannot_retreat(state, state.players[command.player].active) is None:
                        raise AssertionError(f"「にげる」ことができない効果がないのに RETREAT_PREVENTED: {command}")
                    observed["stopped_retreat_RETREAT_PREVENTED"] += 1
                    turn_tried.add("retreat")
                    continue
                if isinstance(command, AttachEnergy):
                    if error.code != R13:
                        raise
                    observed[f"stopped_attach_{error.code}"] += 1
                    turn_tried.add("attach_blocked")
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
            observed[f"attack_{state.card_def(attacker.card).id}#{command.attack_index}"] += 1
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def events_of(state, kind):
    return [dict(e) for e in state.log if e["kind"] == kind]
