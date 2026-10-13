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
  ダメージカウンターをすべてとりのぞく処理（``remove_all_damage_counters``）も組み立て直しに含める。ログは記録で、状態の正本では
  ない（状態とログが食い違えば、どちらかの不具合として報告する）。
- ``serialization_problems(state)``: 形式 1〜9 の書き出しが、表せない状態では ``ValueError``（黙って落とさない）、表せる状態では
  形式 9 の書き出しから後の形式の項目を除いたものと同じになることを確かめる。形式 10 はない。
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
TOP_FIELDS_SINCE = {
    "format_version": 2, "effects": 2, "next_pokemon_id": 2, "next_decision_id": 2, "decision": 2, "trainer_in_use": 3,
    "energy_attached_by_powers_this_turn": 9,
}
LATEST_FORMAT = 9


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
    d = state.decision
    not_v0_1 = d is not None and (d.context_value("then") is not None or d.resume == "attack")
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
        problems.append(f"形式 {LATEST_FORMAT + 1} を書き出せた（v0.6 では形式 {LATEST_FORMAT + 1} を加えない）")
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
            for once in ("forced_switch", "drain_heal", "confusion_check", "confusion_damage", "persistent_effect_added", "discard_energy",
                         "remove_all_damage_counters"):
                if window[once] > 1:
                    problems.append(f"1 回のワザで {once} が {window[once]} 回")
            if window["forced_switch"] + window["forced_switch_skipped"] > 1:
                problems.append("1 回のワザで入れ替えの結果が 2 回以上")
            if window["discard_energy"] != window["remove_all_damage_counters"]:
                problems.append("1 回のワザで、エネルギーのトラッシュとダメージカウンターをすべてとりのぞく処理の数が違う（じこさいせい）")
            window = None
            continue
        if kind in ("pokemon_power", "move_energy", "power_attach_energy", "move_damage_counter"):
            # v0.5: ワザを使ったら番は終わる（p.309）ので、ワザのあと（番の終わりまで）に特殊能力の使用はない（v0.6 のあまごい・
            # v0.7 のダメージスワップも）
            problems.append(f"{e['turn']} 番のワザのあとに特殊能力の使用（{kind}）がある")
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

    pokemon_owner: dict[int, int] = {}  # 場のポケモンの番号 → 持ち主（v0.5。エネルギーの移動は自分の場のポケモンのあいだだけ）
    top: dict[int, int] = {}  # 場のポケモンの番号 → いちばん上のカードの uid（v0.6。つける先のタイプを見る）
    turn_player: int | None = None  # 今の番のプレイヤー（最後の turn_start）
    hand: dict[int, list[int]] = {0: [], 1: []}  # 手札（v0.6。引いた・取ったサイド → 場に出した・つけた・使った）
    attached_this_turn = 0  # この番の、手札からつける通常の操作（attach_energy）の数（v0.6）
    power_attached_this_turn = 0  # この番の、特殊能力で手札からつけた数（power_attach_energy。v0.6）

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
    declared = None  # 直前の特殊能力の宣言（番・プレイヤー・ポケモン）。移動のログはその直後に続く（v0.5）
    for e in log:
        kind = e["kind"]
        if kind not in ("move_energy", "power_attach_energy", "move_damage_counter"):
            if declared is not None:
                problems.append(
                    f"{declared[0]} 番の特殊能力の宣言（ポケモン {declared[2]}）のすぐあとに、その処理（move_energy・power_attach_energy・"
                    "move_damage_counter）がない"
                )
            declared = None
        if kind == "turn_start":
            turn_player = e["player"]
            attached_this_turn = power_attached_this_turn = 0
        if kind == "draw":
            hand[e["player"]].extend(e["cards"])
        elif kind == "mulligan":
            if sorted(e["revealed_hand"]) != sorted(hand[e["player"]]):
                problems.append(f"プレイヤー {e['player']} の切り直しで見せた手札が、ログから組み立てた手札と違う")
            hand[e["player"]] = []
        elif kind == "play_trainer":
            from_hand(e, e["player"], e["card"])
        if kind == "place_starting_pokemon":
            for uid in (e["active"], *e["bench"]):
                from_hand(e, e["player"], uid)
                enter(uid)
        elif kind == "play_to_bench":
            from_hand(e, e["player"], e["card"])
            enter(e["card"])
        elif kind == "evolve":
            from_hand(e, e["player"], e["to_card"])
            ids[e["to_card"]] = e["pokemon_id"]
            top[e["pokemon_id"]] = e["to_card"]
            evolve_turns.setdefault(e["pokemon_id"], []).append(e["turn"])
        elif kind in ("damage", "poison_damage", "confusion_damage", "drain_heal", "remove_damage_counters", "remove_all_damage_counters"):
            pid = e["pokemon_id"] if "pokemon_id" in e else ids[e["pokemon"]]
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
            if e["player"] != turn_player or pokemon_owner.get(e["pokemon_id"]) != e["player"] or e["pokemon_id"] not in in_play:
                problems.append(f"{e['turn']} 番の特殊能力の宣言（ポケモン {e['pokemon_id']}）が、番のプレイヤーの場のポケモンではない")
            continue
        elif kind == "move_energy":
            # v0.5: 特殊能力（エナジートランス）で、同じ uid のエネルギーを移動元から移動先へ（トラッシュには置かない）
            if declared != (e["turn"], e["player"], e["pokemon_id"]):
                problems.append(f"{e['turn']} 番のエネルギーの移動 {e['energy']} の直前に、同じポケモンの特殊能力の宣言（pokemon_power）がない")
            declared = None  # 1 回の宣言で 1 枚（v0.5 のエナジートランス）
            source, target = e["from_pokemon_id"], e["to_pokemon_id"]
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
                if state.card_def(e["energy"]).provides is not effect.energy_type:
                    problems.append(f"{e['turn']} 番の手札からのエネルギー {e['energy']} が「{effect.energy_type.ja}」エネルギーではない")
                if state.card_def(top[target]).pokemon_type is not effect.pokemon_type:
                    problems.append(f"{e['turn']} 番の手札からのエネルギー {e['energy']} のつける先 {target} が「{effect.pokemon_type.ja}」ポケモンではない")
        elif kind == "move_damage_counter":
            # v0.7: 特殊能力（ダメージスワップ）で、自分の場のポケモンのダメージカウンターを、自分の場の別のポケモンへ（1 回に 1 個）
            if declared != (e["turn"], e["player"], e["pokemon_id"]):
                problems.append(f"{e['turn']} 番のダメージカウンターの移動の直前に、同じポケモンの特殊能力の宣言（pokemon_power）がない")
            declared = None  # 1 回の宣言で 1 個（v0.7 のダメージスワップ。実装上の仮定）
            source, target, count = e["from_pokemon_id"], e["to_pokemon_id"], e["count"]
            card_id, _, index = e["power"].partition("@power")
            entry = state.effects.power_entry(card_id, int(index)) if index.isdigit() else None
            if entry is None or entry.effect.implementation_id != "move_damage_counter" or state.cards[top[e["pokemon_id"]]].card_id != card_id:
                problems.append(f"{e['turn']} 番のダメージカウンターの移動の特殊能力 {e['power']} が、使ったポケモンのダメージカウンターを移す特殊能力ではない")
            if count != 1:
                problems.append(f"{e['turn']} 番のダメージカウンターの移動が 1 回に {count} 個（1 個のはず）")
            if pokemon_owner.get(source) != e["player"] or pokemon_owner.get(target) != e["player"]:
                problems.append(f"{e['turn']} 番のダメージカウンターの移動（{source} → {target}）が、自分の場のポケモンのあいだではない")
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
            if damage[target] >= state.card_def(top[target]).hp:
                problems.append(f"{e['turn']} 番のダメージカウンターの移動で、移動先 {target} がきぜつするダメージ {damage[target]} になった")
        elif kind == "discard_energy":
            # v0.7: ワザ（じこさいせい）で、ワザを使ったポケモンについているエネルギーカードをトラッシュ
            pid = e["pokemon_id"]
            if pid not in in_play or pokemon_owner.get(pid) != e["player"] or e["energy"] not in energy.get(pid, []):
                problems.append(f"{e['turn']} 番のエネルギーのトラッシュ {e['energy']} が、ログから組み立てたポケモン {pid} のエネルギーにない")
            else:
                energy[pid].remove(e["energy"])
                discard[e["player"]].append(e["energy"])
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
            hand[e["player"]].append(e["card"])
        elif kind == "persistent_effect_added":
            added[(e["pokemon_id"], e["turn"])] = added.get((e["pokemon_id"], e["turn"]), 0) + 1
        elif kind == "persistent_effect_removed":
            removed[(e["pokemon_id"], e["created_turn"])] += 1

    if declared is not None:
        problems.append(f"{declared[0]} 番の特殊能力の宣言（ポケモン {declared[2]}）のあとに、その処理がない（ログの最後）")
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
