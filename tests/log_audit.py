"""ログと状態の整合・書き出しの形式の監査（v0.4e。docs/integration-audit-v0.4e.md 8 章・9 章）。テスト・ツールから使う道具。

ファイル名が ``test_`` で始まらないので、``python3 -m unittest`` はこのファイルを読み込まない（テストはしない）。

- ``log_problems(state)``: ``new_game`` から進めた対戦のログ（内部の完全な記録）だけから、場のポケモンのダメージ・ついている
  エネルギー・トラッシュ・サイドの枚数を組み立て直し、状態と同じかを確かめる。番の進行（番の始まりが 1 つずつ交互・番と番の
  あいだに番の終わりとポケモンチェックが 1 回ずつ）・ワザ 1 回あたりの要素の数（同じポケモンへのダメージの要素は 1 回）・
  サイドとカードの重複・持続する効果の付与と解除の対応・進化の番も確かめる。ログは記録で、状態の正本ではない（状態と
  ログが食い違えば、どちらかの不具合として報告する）。
- ``serialization_problems(state)``: 形式 1〜8 の書き出しが、表せない状態では ``ValueError``（黙って落とさない）、表せる状態では
  形式 8 の書き出しから後の形式の項目を除いたものと同じになることを確かめる。形式 9 はない。
"""

from __future__ import annotations

from collections import Counter

from kyuura_engine import state_to_dict
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import Phase

TERMINAL = (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED)

# 形式ごとに加わった場のポケモンの項目（serialize.py の説明）
POKEMON_FIELDS_SINCE = {
    "pokemon_id": 2, "trainers": 4, "special_conditions": 5, "retreat_failed_turn": 6, "evolution_stack": 7, "played_turn": 7,
    "evolved_turn": 7, "persistent_effects": 8,
}
TOP_FIELDS_SINCE = {"format_version": 2, "effects": 2, "next_pokemon_id": 2, "next_decision_id": 2, "decision": 2, "trainer_in_use": 3}


def _project(data8: dict, version: int) -> dict:
    """形式 8 の書き出しから、形式 ``version`` にない項目を除いたもの。"""
    data = {k: v for k, v in data8.items() if TOP_FIELDS_SINCE.get(k, 1) <= version}
    if "format_version" in data:
        data["format_version"] = version

    def pokemon(p):
        return None if p is None else {k: v for k, v in p.items() if POKEMON_FIELDS_SINCE.get(k, 1) <= version}

    data["players"] = [
        {**player, "active": pokemon(player["active"]), "bench": [pokemon(b) for b in player["bench"]]} for player in data8["players"]
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
    d = state.decision
    not_v0_1 = d is not None and (d.context_value("then") is not None or d.resume == "attack")
    return needed, not_v0_1


def serialization_problems(state) -> list[str]:
    problems = []
    needed, not_v0_1 = required_format(state)
    data8 = state_to_dict(state, format_version=8)
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
        elif data != _project(data8, version):
            problems.append(f"形式 {version} の書き出しが、形式 8 から後の項目を除いたものと違う")
    try:
        state_to_dict(state, format_version=9)
        problems.append("形式 9 を書き出せた（v0.4e では形式 9 を加えない）")
    except ValueError:
        pass
    return problems


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
    for e in log + [{"kind": "turn_end", "turn": None}]:
        kind = e["kind"]
        if kind == "attack":
            window = Counter()
            continue
        if window is None:
            continue
        if kind in ("turn_end", "game_end", "halted"):
            if window["damage:opponent"] + window["prevented:opponent_active"] > 1 or window["damage:self"] + window["prevented:self"] > 1:
                problems.append(f"1 回のワザで同じポケモンへのダメージの要素が 2 回以上 {dict(window)}")
            if window["confusion_damage"] and (window["damage:opponent"] or window["damage:self"] or window["prevented:opponent_active"]):
                problems.append("こんらんしたワザに、もとのワザのダメージの要素がある")
            for once in ("forced_switch", "drain_heal", "confusion_check", "confusion_damage", "persistent_effect_added"):
                if window[once] > 1:
                    problems.append(f"1 回のワザで {once} が {window[once]} 回")
            if window["forced_switch"] + window["forced_switch_skipped"] > 1:
                problems.append("1 回のワザで入れ替えの結果が 2 回以上")
            window = None
            continue
        if kind == "damage":
            window["damage:self" if e.get("target") == "self" else "damage:opponent"] += 1
        elif kind == "damage_prevented":
            window[f"prevented:{e['target']}"] += 1
        else:
            window[kind] += 1

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
    added: dict[tuple, int] = {}
    removed: Counter = Counter()

    def enter(uid: int) -> None:
        nonlocal next_id
        ids[uid] = next_id
        energy[next_id] = []
        in_play.add(next_id)
        next_id += 1

    owner = {uid: card.owner for uid, card in state.cards.items()}
    for e in log:
        kind = e["kind"]
        if kind == "place_starting_pokemon":
            for uid in (e["active"], *e["bench"]):
                enter(uid)
        elif kind == "play_to_bench":
            enter(e["card"])
        elif kind == "evolve":
            ids[e["to_card"]] = e["pokemon_id"]
            evolve_turns.setdefault(e["pokemon_id"], []).append(e["turn"])
        elif kind in ("damage", "poison_damage", "confusion_damage", "drain_heal", "remove_damage_counters"):
            pid = e["pokemon_id"] if "pokemon_id" in e else ids[e["pokemon"]]
            if kind == "drain_heal":
                damage[pid] -= e["amount"]
            elif kind == "remove_damage_counters":
                damage[pid] -= e["counters"] * state.rules.damage_per_counter
            else:
                damage[pid] += e["amount"]
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の {kind} のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind == "attach_energy":
            energy[ids[e["target"]]].append(e["energy"])
        elif kind in ("retreat", "retreat_failed"):
            pid = e["pokemon_id"] if kind == "retreat_failed" else ids[e["old_active"]]
            for uid in e["discarded"]:
                energy[pid].remove(uid)
                discard[e["player"]].append(uid)
        elif kind == "discard_trainer":
            discard[e["player"]].append(e["card"])
        elif kind == "discard_attached_trainer":
            discard[owner[e["card"]]].append(e["card"])
        elif kind == "knock_out":
            pid = ids[e["pokemon"]]
            if pid not in in_play:
                problems.append(f"場にいないポケモン {pid} がきぜつした")
            if damage[pid] < state.card_def(e["pokemon"]).hp:
                problems.append(f"場のポケモン {pid} が、ログから組み立てたダメージ {damage[pid]}（HP 未満）できぜつした")
            in_play.discard(pid)
            knocked[e["player"]] += 1
            discard[e["player"]].extend([*e.get("evolution_stack", ()), e["pokemon"], *e["discarded_energy"]])
            if sorted(e["discarded_energy"]) != sorted(energy.get(pid, [])):
                problems.append(f"きぜつしたポケモン {pid} のトラッシュしたエネルギー {e['discarded_energy']} がログの組み立てと違う")
            for uid in e.get("discarded_trainers", ()):
                discard[owner[uid]].append(uid)
        elif kind == "take_prize":
            prizes_taken[e["player"]] += 1
            taken_cards.append(e["card"])
        elif kind == "persistent_effect_added":
            added[(e["pokemon_id"], e["turn"])] = added.get((e["pokemon_id"], e["turn"]), 0) + 1
        elif kind == "persistent_effect_removed":
            removed[(e["pokemon_id"], e["created_turn"])] += 1

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
    for pid, evolved in evolve_turns.items():
        if len(evolved) > 2 or evolved != sorted(set(evolved)) or any(turn <= 2 for turn in evolved):
            problems.append(f"場のポケモン {pid} の進化の番 {evolved} が正しくない")
    for key, count in removed.items():
        if count > added.get(key, 0):
            problems.append(f"持続する効果 {key} を、与えた回数より多く消した")
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
