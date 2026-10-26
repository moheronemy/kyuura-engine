"""R団のファイヤー（v0.12）を含む 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで。

R団のファイヤーのポケモンパワー「ふしちょう」（このカードが「きぜつ」したとき、使える。このカードをトラッシュからとり出し、相手プレイヤー
に見せてから、手札に加える。「ねむり・マヒ・こんらん」状態のまま「きぜつ」するときは使えない。p.82）と、ワザ「ほのおのかべ」（40。次の相手の
番、このカードが相手のワザによるダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）相手に10ダメージを与える。p.82）が、
自然な対戦の中で、

- きぜつしたあと、サイドを取ってから、対戦が続くときに使うかを持ち主が決め（使う・使わない）、使えばそのカードだけがトラッシュから手札に
  もどり（エネルギーはトラッシュに残る）、相手はサイドを取り、手札にもどったカードを再び場に出せること、
- 特殊状態（ねむり・マヒ・こんらん）・かがくへんかガス（v0.8）で使えないこと、どくのきぜつ（ポケモンチェック）でも使えること、
- 「ほのおのかべ」の効果が次の相手の番にだけはたらき、相手のワザによるダメージを受けたとき、ダメージを与えた相手の対戦ポケモンに 10（弱点・
  抵抗力・ディフェンダー・「とうめい」を計算する。「はんげき」がはたらく）を与え、その番の終わり・ベンチにもどったとき・きぜつしたときに
  消えること、原典で決められない場合（W24）で止まること

を確かめる（docs/v0.12-verification.md）。

- 一方のデッキは、R団のファイヤーと炎のたねポケモン（ポニータ・ガーディ・ロコン（こんらん））。
- もう一方のデッキは、R団のファイヤーに使うワザ・特殊能力の種類を多くした（カイリキー（はんげき）、ゴースト（とうめい・あくむ（ねむり））、
  ロケット団のベトベター・ベトベトン（どくガス・かがくへんかガス）、キャタピー・トランセル・バタフリー（いとをはく（マヒ）・ふきとばし・
  メガドレイン。弱点 炎）、ビードル（どくばり）、ケーシィ・ユンゲラー（ちょうねんりき 50）、ピカチュウ（でんげき）、サカキのワンリキー・
  ゴーリキー・カイリキー（こんじょう）、R団のファイヤー（ミラー）、ディフェンダー）。

盤面を直接作ったテスト（tests/test_phoenix_v0_12.py・tests/test_rocket_moltres_v0_12.py）とは別に数える。根拠のページは
docs/phoenix-v0.12.md・docs/rocket-moltres-v0.12.md（p.82・p.89・p.309・p.311・p.320〜p.325）。手順は
tests/test_giovanni_games_v0_11.py の ``policy_command`` に、次を加えたもの（対戦相手の AI ではない）:

- 「ふしちょう」を使うかの決定には、番の番号が ``DECLINE_EVERY`` の倍数なら使わない、それ以外は使うと答える（手順の決まりごと。ルール
  ではない。どちらの答えも受け付けることを確かめるため）。
- 番の番号を 7 で割った余りが 5 の番は、自分の場に R団のファイヤーがいれば一度だけ、UsePokemonPower で「ふしちょう」を試す（決められた
  とき以外なので POWER_NOT_USABLE_NOW。かがくへんかガスがはたらいていれば POWER_SUPPRESSED）。
- ワザが ``UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT``（W24）で止まったら、その番はほかの使えるワザ（試していないもの）を 1 度だけ試し、
  なければ番を終える。

「ふしちょう」を使えるかは、エンジンの関数を使わずに場から求める（``rebirth_available``。R団のファイヤー（いちばん上のカード）が、きぜつの
直前にねむり・マヒ・こんらんでなく、はたらいているベトベトンが場に残る（いっしょにきぜつしない）ことがない）。受け付けるたびに、受け付ける
前の場と比べて、決定が出るのは使える R団のファイヤーがきぜつして対戦が続くときだけで、使えるのに決定がないまま対戦が続いていないことを
確かめる。
"""

import hashlib
import json
import pickle
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, Phase, ResolveDecision, UnsupportedError, UseAttack, UsePokemonPower,
    apply_command, check_invariants, new_game, state_to_dict,
)
from kyuura_engine.decisions import POST_KNOCKOUT_POWER
from kyuura_engine.rng import copy_rng, rng_fingerprint
from tests.helpers import (
    CARD_DATA_COMMIT,
    with_card_data_commit_before_v0_69,
    ABRA, KADABRA, BILL, BUTTERFREE, CATERPIE, DEFENDER, FIGHTING, FIRE, GASTLY, GIOVANNIS_MACHAMP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHOP, GRASS, GRIMER,
    GROWLITHE, HAUNTER, LIGHTNING, MACHAMP, MACHOKE, MACHOP, METAPOD, MUK, PIKACHU, PLUSPOWER, PONYTA, POTION, PSYCHIC, ROCKETS_MOLTRES,
    SWITCH, VULPIX, WEEDLE, coin_events, expand_decklist,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_alakazam_games_v0_7 import POWER_REJECTIONS
from tests.test_blastoise_games_v0_6 import R13
from tests.test_confusion_games import TERMINAL
from tests.test_evolution_games_v0_4a import EVOLUTION_REJECTIONS
from tests.test_giovanni_games_v0_11 import EFFECT_STOP, guts_available
from tests.test_giovanni_games_v0_11 import policy_command as giovanni_policy_command
from tests.test_harden_games_v0_4b import REJECTIONS
from tests.test_haunter_games_v0_9 import EVADED_COIN, card_id, gas_on
from tests.test_haunter_games_v0_9 import working as evasion_working
from tests.test_machamp_games_v0_10 import DOUBLE_KO, alternative_attack
from tests.test_machamp_games_v0_10 import working as counter_working
from tests.test_stage2_games_v0_4c import STAGE2_REJECTIONS

# R団のファイヤーと炎のたねポケモン（ロコンはあやしいひかり（こんらん））
MOLTRES_DECK_A = expand_decklist({
    ROCKETS_MOLTRES: 4, PONYTA: 3, GROWLITHE: 3, VULPIX: 2, SWITCH: 2, POTION: 2, BILL: 4, DEFENDER: 2, PLUSPOWER: 2, FIRE: 36,
})
# R団のファイヤーに使うワザ・特殊能力の種類を多くしたデッキ
MOLTRES_DECK_B = expand_decklist({
    MACHOP: 2, MACHOKE: 2, MACHAMP: 2, GASTLY: 2, HAUNTER: 2, GRIMER: 2, MUK: 1, CATERPIE: 2, METAPOD: 1, BUTTERFREE: 1, WEEDLE: 2,
    ABRA: 2, KADABRA: 2, PIKACHU: 2, GIOVANNIS_MACHOP: 1, GIOVANNIS_MACHOKE: 1, GIOVANNIS_MACHAMP: 1, ROCKETS_MOLTRES: 2, PLUSPOWER: 2,
    BILL: 4, DEFENDER: 2, FIGHTING: 6, PSYCHIC: 8, GRASS: 6, LIGHTNING: 2,
})
SEEDS = tuple(range(100))
DECLINE_EVERY = 3  # 手順の決まりごと（ルールの制限ではない）
RETALIATION_STOP = "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT"
REBIRTH_EVENTS = ("post_knockout_power_declined", "post_knockout_power_declared", "return_to_hand")
FIRE_WALL = f"{ROCKETS_MOLTRES}#0"


def full(state):
    return state_to_dict(state, format_version=9)


def decks(seed):
    return (MOLTRES_DECK_A, MOLTRES_DECK_B) if seed % 2 == 0 else (MOLTRES_DECK_B, MOLTRES_DECK_A)


def retaliation_on(state, pokemon):
    """今の番にはたらく「ほのおのかべ」の効果を持つか（エンジンの関数を使わない。持続する効果の値と番だけを見る）。"""
    return pokemon is not None and any(e.kind == "retaliation" and e.active_turn == state.turn_number for e in pokemon.persistent_effects)


def rebirth_blocked(condition, field, knocked_ids):
    """きぜつする R団のファイヤーの「ふしちょう」を使えない理由（エンジンの関数を使わない。p.82・p.48）。使えるなら None。
    ``condition`` はきぜつするときのねむり・マヒ・こんらん（なければ None）、``field`` はきぜつの直前の場（場のポケモンの番号 →
    (カード id, ねむり・マヒ・こんらん)）、``knocked_ids`` は同じきぜつの処理できぜつするポケモン。"""
    if condition is not None:
        return "condition"
    gases = [pid for pid, (kind, exclusive) in field.items() if kind == MUK and exclusive is None]
    if gases and any(pid not in knocked_ids for pid in gases):
        return "gas"
    return None


def policy_command(state, *, janken_winner, cure, tried):
    if state.phase is Phase.DECISION and state.decision.kind == POST_KNOCKOUT_POWER:
        d = state.decision
        use = state.turn_number % DECLINE_EVERY != 0
        return ResolveDecision(d.player, d.id, d.options[:1] if use else ())
    command = giovanni_policy_command(state, janken_winner=janken_winner, cure=cure, tried=tried)
    if state.phase is not Phase.MAIN:
        return command
    player = state.current_player
    if isinstance(command, (UseAttack, EndTurn)) and state.turn_number % 7 == 5 and "declare_rebirth" not in tried:
        moltres = next((pk for pk in state.players[player].in_play() if card_id(state, pk) == ROCKETS_MOLTRES), None)
        if moltres is not None:
            tried.add("declare_rebirth")
            return UsePokemonPower(player, moltres.pokemon_id, 0)
    if isinstance(command, UseAttack) and ("retaliation_double" in tried or ("attack_index", command.attack_index) in tried):
        return alternative_attack(state, player, tried) or EndTurn(player)
    return command


def play_game(seed, *, cure=True, max_steps=10000):
    """終わるまで進める。受け付けた操作の列と、拒否された操作・場面の観測を返す。"""
    state = new_game(*decks(seed), seed)
    commands, observed, tried = [], Counter(), {}
    returned: set[int] = set()  # 「ふしちょう」で手札にもどったカード
    for _ in range(max_steps):
        if state.phase in TERMINAL:
            return state, commands, observed
        while True:
            turn_tried = tried.setdefault(state.turn_number, set())
            command = policy_command(state, janken_winner=seed % 2, cure=cure, tried=turn_tried)
            try:
                new = apply_command(state, command)
                break
            except (IllegalActionError, UnsupportedError) as error:
                observed["rejected"] += 1
                if isinstance(command, UsePokemonPower):
                    kind = card_id(state, state.find_pokemon(command.pokemon)[1])
                    if error.code == "POWER_NOT_USABLE_NOW" and kind in (ROCKETS_MOLTRES, GIOVANNIS_MACHAMP) and not gas_on(state):
                        observed[f"rejected_declare_{kind}"] += 1
                        continue
                    if error.code == "POWER_NOT_DECLARABLE" and kind in (MUK, MACHAMP, HAUNTER):
                        observed[f"rejected_declare_{kind}"] += 1
                        continue
                    if error.code == "POWER_SUPPRESSED" and gas_on(state):
                        observed["suppressed_power"] += 1
                        continue
                    if error.code not in POWER_REJECTIONS:
                        raise
                    observed[f"rejected_power_{error.code}"] += 1
                    continue
                if isinstance(command, UseAttack) and error.code == RETALIATION_STOP:
                    # W24: 相手の対戦ポケモンに、今の番にはたらく「ほのおのかべ」があるとき（エンジンとは別に場から確かめる）
                    target = state.players[1 - state.current_player].active
                    if not retaliation_on(state, target):
                        raise AssertionError(f"「ほのおのかべ」がはたらいていないのに {RETALIATION_STOP}: {command}")
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
                    if not counter_working(state, target):
                        raise AssertionError(f"「はんげき」がはたらいていないのに {DOUBLE_KO}: {command}")
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
        observe(state, new, command, observed, returned)
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def observe(state, new, command, observed, returned):
    """受け付けた操作のログ・決定を、操作の前の場から求めた「ふしちょう」「ほのおのかべ」と比べて数える。"""
    events = [dict(e) for e in new.log[len(state.log):]]
    by_card = {pk.card: pk for p in state.players for pk in p.in_play()}
    if new.decision is not None and new.decision.kind == POST_KNOCKOUT_POWER:
        if state.decision is not None and state.decision.kind == POST_KNOCKOUT_POWER:
            raise AssertionError("「ふしちょう」の決定が続けて出た")
        observed["rebirth_offered"] += 1
    # 操作の前の場から、この操作のログで場（カード・ねむり・マヒ・こんらん）を進める（きぜつするときの特殊状態とかがくへんかガスを求める）
    field = {pk.pokemon_id: (card_id(state, pk), None if pk.conditions.exclusive is None else pk.conditions.exclusive.name)
             for p in state.players for pk in p.in_play()}
    batches, batch = [], set()  # 同じきぜつの処理（続いた knock_out）できぜつしたポケモン
    for e in events:
        if e["kind"] == "knock_out" and e["pokemon"] in by_card:
            batch.add(by_card[e["pokemon"]].pokemon_id)
        elif e["kind"] != "persistent_effect_removed" and batch:
            batches.append(batch)
            batch = set()
    if batch:
        batches.append(batch)
    if state.decision is not None and state.decision.kind == "take_prize" and state.decision.context_value("post_knockout") is not None \
            and new.phase in TERMINAL:
        observed["rebirth_not_offered_game_over"] += 1  # サイドを取り終えて対戦が終わった（決めさせない。P30）
    in_retaliation = False  # 直前のイベントが「ほのおのかべ」（そのあとのダメージの要素は R団のファイヤーのワザ）
    for e in events:
        kind = e["kind"]
        if kind == "attack_evaded" and in_retaliation:
            observed["retaliation_evaded"] += 1
        if kind in ("damage", "attack_evaded", "damage_prevented"):
            in_retaliation = False
        if kind == "retaliation":
            in_retaliation = True
        if kind in REBIRTH_EVENTS or kind in ("retaliation", "retaliation_skipped", "persistent_effect_skipped"):
            observed[kind] += 1
        if kind == "return_to_hand":
            returned.add(e["card"])
            if e["card"] not in new.players[e["player"]].hand and new.phase not in TERMINAL:
                raise AssertionError(f"手札に加えたカードが手札にない: {e}")
        if kind == "play_to_bench" and e["card"] in returned:
            observed["rebirth_card_played_again"] += 1
            returned.discard(e["card"])
        if kind == "place_starting_pokemon":
            continue
        if kind == "damage" and e.get("retaliation"):
            observed["retaliation_damage_events"] += 1
            observed["retaliation_damage_total"] += e["amount"]
            if e["weakness"]:
                observed["retaliation_weakness"] += 1
            if e["resistance"]:
                observed["retaliation_resistance"] += 1
            if e.get("modifiers"):
                observed["retaliation_defender"] += 1
            if e["total_damage"] >= new.card_def(e["pokemon"]).hp:
                observed["retaliation_knock_out"] += 1
        if kind == "counterattack" and e["effect"] == FIRE_WALL:
            observed["counterattack_after_retaliation"] += 1
        if kind == "persistent_effect_added" and e["persistent_effect"] == "retaliation":
            observed["retaliation_effect_added"] += 1
        if kind == "persistent_effect_removed" and e["persistent_effect"] == "retaliation":
            observed[f"retaliation_effect_removed_{e['reason']}"] += 1
        if kind == "special_condition" and e["condition"] in ("sleep", "paralysis", "confusion") and e["pokemon_id"] in field:
            field[e["pokemon_id"]] = (field[e["pokemon_id"]][0], e["condition"])
        if kind == "special_conditions_removed" and e["pokemon_id"] in field and field[e["pokemon_id"]][1] in e["conditions"]:
            field[e["pokemon_id"]] = (field[e["pokemon_id"]][0], None)
        if kind == "knock_out":
            pokemon = by_card.get(e["pokemon"])
            if pokemon is None:
                continue
            knocked_ids = next(b for b in batches if pokemon.pokemon_id in b)
            condition = field[pokemon.pokemon_id][1]
            snapshot = dict(field)
            field.pop(pokemon.pokemon_id)
            if card_id(state, pokemon) != ROCKETS_MOLTRES:
                continue
            observed["knock_out_rockets_moltres"] += 1
            if e.get("timing") == "pokemon_check":
                observed["knock_out_rockets_moltres_poison"] += 1
            # 同じきぜつの処理で先にきぜつしたポケモンも、きぜつの直前の場にいた
            for pid in knocked_ids:
                if pid not in snapshot and pid in {pk.pokemon_id for p in state.players for pk in p.in_play()}:
                    other = next(pk for p in state.players for pk in p.in_play() if pk.pokemon_id == pid)
                    snapshot[pid] = (card_id(state, other), None if other.conditions.exclusive is None else other.conditions.exclusive.name)
            reason = rebirth_blocked(condition, snapshot, knocked_ids)
            answered = [r for r in events if r["kind"] in ("post_knockout_power_declined", "post_knockout_power_declared") and r["card"] == e["pokemon"]]
            offered = new.decision is not None and new.decision.kind == POST_KNOCKOUT_POWER and new.decision.options == (e["pokemon"],)
            waiting_prize = new.decision is not None and new.decision.kind == "take_prize" and any(
                c[1] == e["pokemon"] for c in new.decision.context_value("post_knockout", ()))
            if reason is not None:
                observed[f"rebirth_blocked_{reason}"] += 1
                if answered or offered or waiting_prize:
                    raise AssertionError(f"「ふしちょう」を使えないのに決定: {command} {e}")
            elif not (answered or offered or waiting_prize):
                if new.phase is not Phase.GAME_OVER and new.phase is not Phase.SUDDEN_DEATH:
                    raise AssertionError(f"「ふしちょう」を使えるのに決定がないまま: {command} {e}")
                observed["rebirth_not_offered_game_over"] += 1


def count_events(state):
    """ログから数える。"""
    counted = Counter()
    for e in state.log:
        kind = e["kind"]
        if kind == "attack" and state.cards[e["pokemon"]].card_id == ROCKETS_MOLTRES:
            counted["attack_ほのおのかべ"] += 1
        elif kind == "take_prize":
            counted["take_prize"] += 1
        elif kind == "knock_out" and e.get("simultaneous"):
            counted["knock_out_simultaneous"] += 1
    counted = Counter({k: v for k, v in counted.items() if v})
    counted[f"phase_{state.phase.value}"] += 1
    if state.phase is Phase.GAME_OVER:
        counted["decisive"] += 1
    if state.phase is Phase.HALTED:
        counted[f"halted_{state.halt.code}"] += 1
    return counted


# 自然な対戦（SEEDS の 100 局）で数えた回数（v0.12）。手順・デッキ・乱数の使い方が変わると変わる。100 局すべて勝敗が決まった。
# R団のファイヤーのきぜつ 79 回: 「ふしちょう」を使うかの決定 32 回（使う 21 回・使わない 11 回）、特殊状態のまま（ねむり・マヒ・こんらん）で
# 使えない 34 回、かがくへんかガスで使えない 4 回、サイドを取り終えて対戦が終わった（決めさせない）9 回。どくのきぜつ（ポケモンチェック）3 回。
# 手札にもどしたカードを再び場に出した 19 回。「ほのおのかべ」199 回（効果を与えた 198 回。1 回は相手の「はんげき」で HP 以上になって
# 与えなかった）。効果がはたらいた 27 回（ダメージ 17 回・合計 220。弱点 5 回。「とうめい」で受けなかった 10 回。そのダメージでワザを
# 使ったポケモンが HP 以上 6 回。そのダメージで「はんげき」16 回）。効果が期限で消えた 170 回・きぜつで消えた 2 回（残りは対戦の終わり）。
# W24（UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT）で止めたワザ 1 回。
EXPECTED_COUNTS = {
    "accepted": 12266, "attack_ほのおのかべ": 199, "counterattack_after_retaliation": 16, "decisive": 100, "knock_out_rockets_moltres": 79,
    "knock_out_rockets_moltres_poison": 3, "knock_out_simultaneous": 2, "persistent_effect_skipped": 1, "phase_game_over": 100,
    "post_knockout_power_declared": 21, "post_knockout_power_declined": 11, "rebirth_blocked_condition": 34, "rebirth_blocked_gas": 4,
    "rebirth_card_played_again": 19, "rebirth_not_offered_game_over": 9, "rebirth_offered": 32, "rejected": 1388,
    "rejected_attack_POKEMON_ASLEEP": 72, "rejected_attack_POKEMON_PARALYZED": 55, "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS": 9,
    "rejected_declare_PMCG1-057": 67, "rejected_declare_PMCG3-007": 41, "rejected_declare_PMCG3-030": 154, "rejected_declare_PMCG5-020": 355,
    "rejected_declare_PMCG6-061": 15, "rejected_evolve2_EVOLVED_THIS_TURN": 56, "rejected_evolve_FIRST_TURN_EVOLUTION": 39,
    "rejected_evolve_PLAYED_THIS_TURN": 143, "rejected_retreat_POKEMON_ASLEEP": 86, "rejected_retreat_POKEMON_PARALYZED": 59,
    "rejected_retreat_RETREAT_ALREADY_FAILED": 30, "retaliation": 27, "retaliation_damage_events": 17, "retaliation_damage_total": 220,
    "retaliation_effect_added": 198, "retaliation_effect_removed_expired": 170, "retaliation_effect_removed_knock_out": 2,
    "retaliation_evaded": 10, "retaliation_knock_out": 6, "retaliation_weakness": 5, "return_to_hand": 21,
    "stopped_attack_UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT": 23, "stopped_attack_UNRESOLVED_EVADED_EFFECT_COIN": 125,
    "stopped_attack_UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT": 1, "suppressed_power": 58, "take_prize": 564,
}

# 「ふしちょう」を使う 1 回・使わない 1 回、「ほのおのかべ」の効果がはたらき「とうめい」で受けなかった 1 回、期限で消えた 15 回の対戦
GOLDEN_SEED = 28
GOLDEN_SHAPE = (110, 35, Phase.GAME_OVER)
GOLDEN_DIGEST = "791c5afabfdd39c9368891135d9fe6bd2a024d4da1b70346c987b6581b1b76fb"
# 「ほのおのかべ」のダメージ（弱点・「はんげき」）がある対戦（ログの監査の自己テストに使う）
RETALIATION_SEED = 85


class FullGameWithRocketsMoltresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play_game(seed, cure=seed % 3 != 0) for seed in SEEDS}

    def total(self):
        counted = Counter()
        for state, _, observed in self.games.values():
            counted.update(count_events(state))
            counted.update(observed)
        return counted

    def test_counts(self):
        """自然な対戦の中で、R団のファイヤーがきぜつし、「ふしちょう」を使うか決め（使う・使わない）、手札にもどしたカードを再び場に出し、
        特殊状態・かがくへんかガスで使えず、「ほのおのかべ」の効果を与え、はたらき（ダメージ・弱点・「とうめい」・「はんげき」・きぜつ）、期限で
        消える（1 回も起こらない試験を成功と数えない）。"""
        counted = self.total()
        for key in ("knock_out_rockets_moltres", "rebirth_offered", "post_knockout_power_declared", "post_knockout_power_declined",
                    "return_to_hand", "rebirth_card_played_again", "rebirth_blocked_condition", "rebirth_blocked_gas",
                    "knock_out_rockets_moltres_poison", "rebirth_not_offered_game_over", "attack_ほのおのかべ", "retaliation_effect_added",
                    "retaliation", "retaliation_damage_events", "retaliation_weakness", "retaliation_evaded", "retaliation_knock_out",
                    "counterattack_after_retaliation", "retaliation_effect_removed_expired", "rejected_declare_PMCG5-020", "phase_game_over"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertEqual(counted["rebirth_offered"], counted["post_knockout_power_declared"] + counted["post_knockout_power_declined"])
        self.assertEqual(counted["return_to_hand"], counted["post_knockout_power_declared"])
        self.assertEqual(counted["knock_out_rockets_moltres"], counted["rebirth_offered"] + counted["rebirth_blocked_condition"]
                         + counted["rebirth_blocked_gas"] + counted["rebirth_not_offered_game_over"])
        self.assertEqual(counted["retaliation"], counted["retaliation_damage_events"] + counted["retaliation_evaded"])
        self.assertEqual(counted["attack_ほのおのかべ"], counted["retaliation_effect_added"] + counted["persistent_effect_skipped"])
        self.assertEqual(dict(counted), EXPECTED_COUNTS)

    def test_states_logs_and_serialization(self):
        """どの対戦も、不変条件・ログの監査（「ふしちょう」の答え・回収・サイド・「ほのおのかべ」の効果・ダメージ・期限を含む）・書き出しの監査
        （形式 1〜9）に通る。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, TERMINAL)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_randomness_is_only_coins(self):
        """対戦準備のあとの乱数はコインだけ（「ふしちょう」・「ほのおのかべ」は乱数を使わない。「とうめい」のコインは受けるときに 1 枚）。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                expected = copy_rng(new_game(*decks(seed), seed).rng)
                for event in coin_events(state):
                    self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
                self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected))

    def test_replay_and_save_restore_at_the_decision(self):
        """同じ seed と同じ操作の列で同じ結果。「ふしちょう」を使うかの決定（と、その前のサイドを取る決定）・「ほのおのかべ」の効果がはたらく
        番の状態で保存して（pickle）再開しても、結果は同じ（D5 の 1〜9）。"""
        restored = Counter()
        for seed, (state, commands, _) in self.games.items():
            kinds = {e["kind"] for e in state.log}
            if not kinds & {"post_knockout_power_declined", "post_knockout_power_declared", "retaliation"} and seed > 2:
                continue
            replayed = new_game(*decks(seed), seed)
            for command in commands:
                d = replayed.decision
                if d is not None and (d.kind == POST_KNOCKOUT_POWER or d.context_value("post_knockout") is not None):
                    replayed = pickle.loads(pickle.dumps(replayed))
                    restored["decision"] += 1
                elif any(retaliation_on(replayed, pk) for p in replayed.players for pk in p.in_play()):
                    replayed = pickle.loads(pickle.dumps(replayed))
                    restored["retaliation_active"] += 1
                replayed = apply_command(replayed, command)
            with self.subTest(seed=seed):
                self.assertEqual(full(replayed), full(state))
        self.assertGreaterEqual(restored["decision"], EXPECTED_COUNTS["rebirth_offered"])
        self.assertGreater(restored["retaliation_active"], 0)


class GoldenMoltresGameTest(unittest.TestCase):
    """「ふしちょう」を使う・使わない、「ほのおのかべ」の効果がある対戦（GOLDEN_SEED）の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.12）。"""

    def test_seed(self):
        state, commands, observed = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        kinds = Counter(e["kind"] for e in state.log)
        self.assertEqual((kinds["post_knockout_power_declared"], kinds["post_knockout_power_declined"], kinds["return_to_hand"]), (1, 1, 1))
        data = full(state)
        # v0.69・v0.97: 写しの元を上げた（7d3f4ca・73a1690）。固定値は変えず、写しの元の 2 か所だけを確かめた移行でもどして比べる（tests/helpers.py）
        self.assertEqual(data["card_data"]["commit"], CARD_DATA_COMMIT)
        data = with_card_data_commit_before_v0_69(data)
        self.assertEqual(data.pop("effects"), "kyuura-engine-0.13")  # v0.13 で登録表の id だけ変わった（結果は同じ）
        self.assertEqual(hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), GOLDEN_DIGEST)



def replay_until(seed, stop):
    """``seed`` の対戦を、操作のあとの状態が ``stop(state)`` になるまで進めた状態（同じ手順・同じ操作の列）。"""
    _, commands, _ = play_game(seed, cure=seed % 3 != 0)
    state = new_game(*decks(seed), seed)
    for command in commands:
        state = apply_command(state, command)
        if stop(state):
            return state
    raise AssertionError("その状態にならなかった")


class LogAuditMoltresTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py）が、「ふしちょう」「ほのおのかべ」のログ・状態の食い違い（D6 の 16 種類）を見つけること（監査が何でも
    通すのではないことの確認）。GOLDEN_SEED の対戦（使う → 手札にもどす、使わない）と RETALIATION_SEED の対戦（「ほのおのかべ」のダメージ・
    期限）のログ・途中の状態を書きかえて、それぞれの種類の誤りを報告することを確かめる。"""

    @classmethod
    def setUpClass(cls):
        cls.state = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)[0]
        log = cls.state.log
        cls.declared = next(i for i, e in enumerate(log) if e["kind"] == "post_knockout_power_declared")
        cls.declined = next(i for i, e in enumerate(log) if e["kind"] == "post_knockout_power_declined")
        cls.card = log[cls.declared]["card"]
        cls.knock_out = max(i for i in range(cls.declared) if log[i]["kind"] == "knock_out")
        cls.attack = max(i for i in range(cls.knock_out) if log[i]["kind"] == "attack")
        # 回収した直後の状態（バトル場に出す決定を待っている）
        cls.recovered = replay_until(GOLDEN_SEED, lambda s: any(e["kind"] == "return_to_hand" for e in s.log))
        cls.fire = play_game(RETALIATION_SEED, cure=RETALIATION_SEED % 3 != 0)[0]
        fire_log = cls.fire.log
        cls.retaliation = next(i for i, e in enumerate(fire_log) if e["kind"] == "retaliation")
        cls.retaliation_damage = cls.retaliation + 1
        effect = (fire_log[cls.retaliation]["pokemon_id"], fire_log[cls.retaliation]["turn"] - 1)
        cls.effect_added = next(i for i, e in enumerate(fire_log) if e["kind"] == "persistent_effect_added" and (e["pokemon_id"], e["turn"]) == effect)
        cls.effect_removed = next(i for i, e in enumerate(fire_log) if e["kind"] == "persistent_effect_removed"
                                  and (e["pokemon_id"], e["created_turn"]) == effect)

    def broken(self, change_log, state=None):
        state = (state or self.state).clone()
        log = [dict(e) for e in state.log]
        change_log(log)
        state.log = tuple(log)
        return self.audit(state)

    @staticmethod
    def audit(state):
        try:
            return log_problems(state)
        except (KeyError, ValueError, StopIteration, AttributeError, IndexError, TypeError) as error:
            return [f"組み立て直せない（{type(error).__name__}）"]

    def assert_reported(self, problems, text):
        self.assertTrue(any(text in p for p in problems), problems)

    def test_original_passes(self):
        self.assertEqual(log_problems(self.state), [])
        self.assertEqual(log_problems(self.recovered), [])
        self.assertEqual(log_problems(self.fire), [])
        log = self.state.log
        self.assertEqual([log[i]["kind"] for i in range(self.knock_out, self.declared + 3)],
                         ["knock_out", "take_prize", "post_knockout_power_declared", "return_to_hand", "promote_active"])
        self.assertEqual(self.fire.log[self.retaliation_damage]["kind"], "damage")

    def test_1_missing_declaration(self):
        """ふしちょうの宣言が欠ける（回収だけがある）。"""
        def drop(log):
            del log[self.declared]

        self.assert_reported(self.broken(drop), "直前に、「ふしちょう」の宣言がない")

    def test_2_recovered_after_declining(self):
        """使用しない選択なのに回収した。"""
        def recover(log):
            event = log[self.declined]
            log.insert(self.declined + 1, {"kind": "return_to_hand", "turn": event["turn"], "player": event["player"], "card": event["card"],
                                           "card_id": event["card_id"], "power": event["power"], "revealed": True})

        self.assert_reported(self.broken(recover), "直前に、「ふしちょう」の宣言がない")

    def test_3_wrong_card_recovered(self):
        """違うカード（いっしょにトラッシュしたエネルギー）を回収した。"""
        energy = self.state.log[self.knock_out]["discarded_energy"][0]

        def wrong(log):
            log[self.declared + 1] = {**log[self.declared + 1], "card": energy}

        self.assert_reported(self.broken(wrong), "そのカードの return_to_hand がない")

    def test_4_recovered_card_stays_in_discard(self):
        """回収したカードがトラッシュにも残る（状態の食い違い）。"""
        state = self.recovered.clone()
        owner = self.state.cards[self.card].owner
        state.players[owner].discard.append(self.card)
        self.assert_reported(self.audit(state), f"プレイヤー {owner} のトラッシュ")

    def test_5_energy_also_recovered(self):
        """ついていたエネルギーまで手札にもどった（状態の食い違い。P23）。"""
        state = self.recovered.clone()
        owner = self.state.cards[self.card].owner
        energy = self.state.log[self.knock_out]["discarded_energy"][0]
        state.players[owner].discard.remove(energy)
        state.players[owner].hand.append(energy)
        problems = self.audit(state)
        self.assert_reported(problems, f"プレイヤー {owner} の手札")
        self.assert_reported(problems, f"プレイヤー {owner} のトラッシュ")

    def test_6_wrong_hand_size(self):
        """手札の枚数が違う（回収したカードが手札にない）。"""
        state = self.recovered.clone()
        owner = self.state.cards[self.card].owner
        state.players[owner].hand.remove(self.card)
        self.assert_reported(self.audit(state), f"プレイヤー {owner} の手札")

    def test_7_used_while_asleep(self):
        """ねむり状態のままきぜつしたのに使った（P13）。"""
        _, commands, _ = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)
        before = new_game(*decks(GOLDEN_SEED), GOLDEN_SEED)
        for command in commands:
            after = apply_command(before, command)
            if len(after.log) > self.attack:
                break
            before = after
        pokemon_id = next(pk.pokemon_id for p in before.players for pk in p.in_play() if pk.card == self.card)

        def asleep(log):
            event = log[self.attack]
            log.insert(self.attack, {"kind": "special_condition", "turn": event["turn"], "player": self.state.cards[self.card].owner,
                                     "pokemon": self.card, "pokemon_id": pokemon_id, "condition": "sleep", "effect": "test"})

        self.assert_reported(self.broken(asleep), "使えない「ふしちょう」")

    def test_8_used_under_gas(self):
        """はたらいているかがくへんかガスが場に残るのに使った（P18）。"""
        def gas(log):
            muk = next(uid for uid, c in self.state.cards.items() if c.card_id == MUK)
            log.insert(self.attack, {"kind": "play_to_bench", "turn": log[self.attack]["turn"], "player": self.state.cards[muk].owner, "card": muk})

        self.assert_reported(self.broken(gas), "かがくへんかガス")

    def test_9_wrong_prize(self):
        """サイドが不正（きぜつの数より多く取った）。"""
        def prize(log):
            taken = log[self.knock_out + 1]
            other = next(uid for uid, c in self.state.cards.items() if c.owner == taken["player"] and uid != taken["card"])
            log.insert(self.knock_out + 2, {**taken, "card": other})

        self.assert_reported(self.broken(prize), "より多くサイドを取った")

    def test_10_promotion_before_answer(self):
        """バトル場に出すのが「ふしちょう」の答えより先（正規化した順番と違う）。"""
        def move(log):
            promote = log.pop(self.declared + 2)
            log.insert(self.declared, promote)

        self.assert_reported(self.broken(move), "答えがないまま promote_active")

    def test_11_wrong_retaliation_damage(self):
        """「ほのおのかべ」のダメージ（基本となるダメージ）が違う（W14）。"""
        def double(log):
            event = log[self.retaliation_damage]
            log[self.retaliation_damage] = {**event, "amount": event["amount"] * 2, "steps": (("1 基本となる計算", 20),),
                                            "total_damage": event["total_damage"] + event["amount"]}

        self.assert_reported(self.broken(double, self.fire), "基本となるダメージ")

    def test_12_wrong_retaliation_target(self):
        """「ほのおのかべ」のダメージを受けたのが、ダメージを与えた相手の対戦ポケモンではない。"""
        def target(log):
            holder = log[self.retaliation]["pokemon_id"]
            log[self.retaliation_damage] = {**log[self.retaliation_damage], "pokemon_id": holder}

        self.assert_reported(self.broken(target, self.fire), "ダメージを与えた相手の対戦ポケモン")

    def test_13_effect_survives_its_turn(self):
        """効果が期限（はたらく番の終わり）のあとも残る。"""
        def keep(log):
            del log[self.effect_removed]

        self.assert_reported(self.broken(keep, self.fire), "が残っている")

    def test_14_effect_removed_too_early(self):
        """効果が早すぎる時点（与えた番）で期限で消える。"""
        def early(log):
            removed = log.pop(self.effect_removed)
            log.insert(self.effect_added + 1, {**removed, "turn": log[self.effect_added]["turn"]})

        self.assert_reported(self.broken(early, self.fire), "期限で消えた（早すぎる")

    def test_15_save_restore_changes_the_effect(self):
        """保存・復元（pickle）で効果の状態は変わらない。変わった状態（与えた番が違う）は監査が見つける。"""
        alive = replay_until(RETALIATION_SEED, lambda s: any(retaliation_on(s, pk) for p in s.players for pk in p.in_play()))
        restored = pickle.loads(pickle.dumps(alive))
        self.assertEqual(full(restored), full(alive))
        self.assertEqual(log_problems(restored), [])
        import dataclasses
        for p in restored.players:
            for pk in p.in_play():
                pk.persistent_effects = tuple(dataclasses.replace(e, created_turn=e.created_turn - 2, active_turn=e.active_turn - 2)
                                              for e in pk.persistent_effects)
        self.assert_reported(self.audit(restored), "消したログがないのに状態にない")

    def test_16_recovery_before_knock_out(self):
        """きぜつと回収のログの順番が逆（答えと回収がきぜつより先）。"""
        def move(log):
            answer = log.pop(self.declared)
            recovered = log.pop(self.declared)
            log.insert(self.knock_out, recovered)
            log.insert(self.knock_out, answer)

        self.assert_reported(self.broken(move), "直前のきぜつの処理の中にない")


if __name__ == "__main__":
    unittest.main()
