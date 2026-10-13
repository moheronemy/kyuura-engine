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
  ワザ（エナジーへんかん）でトラッシュから手札に加えたエネルギーカード（``recover_energy``）も組み立て直しに含める。
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
  ログは記録で、状態の正本ではない（状態とログが食い違えば、どちらかの不具合として報告する）。
- ``serialization_problems(state)``: 形式 1〜9 の書き出しが、表せない状態では ``ValueError``（黙って落とさない）、表せる状態では
  形式 9 の書き出しから後の形式の項目を除いたものと同じになることを確かめる。形式 10 はない。
"""

from __future__ import annotations

from collections import Counter

from kyuura_engine import state_to_dict
from kyuura_engine.effects import (
    ATTACK_ELEMENTS,
    DAMAGE_ELEMENT,
    FORCED_SWITCH_ELEMENT,
    AttackImmunityOnHeads,
    CounterattackDamage,
    DamageAndRetaliation,
    PreventKnockOutOnHeads,
    ReturnToHandOnKnockOut,
    SuppressOtherPowers,
)
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import Phase

TERMINAL = (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED)

# v0.10: はたらいた「はんげき」より先にあってはならない、ワザのダメージ以外の効果・きぜつ・番の終わり（p.89）
COUNTER_BARRIERS = (
    "special_condition", "forced_switch", "forced_switch_skipped", "drain_heal", "drain_heal_skipped", "knock_out", "turn_end", "game_end",
    "halted", "recover_energy", "discard_energy", "remove_all_damage_counters", "persistent_effect_added", "persistent_effect_skipped",
)
# v0.10: ダメージの要素のあとのワザのコインが、ダメージ以外の効果（特殊状態）を決めるワザ（「はんげき」はそのコインより先）。でんげきの
# コインは自分へのダメージ（ダメージの要素）を決めるので含めない
EFFECT_COIN_AFTER_DAMAGE = ("poison_on_heads", "paralyze_on_heads", "confuse_on_heads")

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
    not_v0_1 = d is not None and (
        d.context_value("then") is not None or d.resume in ("attack", "knock_out", "post_knockout") or d.context_value("post_knockout") is not None
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
        problems.append(f"形式 {LATEST_FORMAT + 1} を書き出せた（v0.6 では形式 {LATEST_FORMAT + 1} を加えない）")
    except ValueError:
        pass
    return problems


def _attack_key(text: str) -> tuple[str, int]:
    """ログのワザ（``AttackKey`` の文字列 ``"カード id#位置"``）を (カード id, 位置) にする（v0.12）。"""
    card_id, _, index = text.partition("#")
    return card_id, int(index) if index.isdigit() else -1


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
                         "remove_all_damage_counters", "recover_energy", "drain_heal_skipped"):
                if window[once] > 1:
                    problems.append(f"1 回のワザで {once} が {window[once]} 回")
            if window["forced_switch"] + window["forced_switch_skipped"] > 1:
                problems.append("1 回のワザで入れ替えの結果が 2 回以上")
            if window["discard_energy"] != window["remove_all_damage_counters"]:
                problems.append("1 回のワザで、エネルギーのトラッシュとダメージカウンターをすべてとりのぞく処理の数が違う（じこさいせい）")
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
                problems.append(f"1 回のワザで「ほのおのかべ」が {window['retaliation'] + window['retaliation_skipped']} 回・そのダメージが {window['damage:retaliation']} 回")
            if window["post_knockout_power_declined"] + window["post_knockout_power_declared"] > 1:
                problems.append("1 回のワザのあとで「ふしちょう」を使うかの答えが 2 回以上")
            window = None
            continue
        if kind in ("pokemon_power", "move_energy", "power_attach_energy", "move_damage_counter"):
            # v0.5: ワザを使ったら番は終わる（p.309）ので、ワザのあと（番の終わりまで）に特殊能力の使用はない（v0.6 のあまごい・
            # v0.7 のダメージスワップも）
            problems.append(f"{e['turn']} 番のワザのあとに特殊能力の使用（{kind}）がある")
        if kind == "damage":
            window["damage:retaliation" if e.get("retaliation") else "damage:self" if e.get("target") == "self" else "damage:opponent"] += 1
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
    exclusive: dict[int, str] = {}  # 場のポケモンの番号 → ねむり・マヒ・こんらんのどれか（v0.8。かがくへんかガスがはたらいているかを見る）
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

    def working_gases() -> list[tuple[int, SuppressOtherPowers]]:
        """ログから組み立てた今の場で、はたらいている「ほかの特殊能力を消す」特殊能力（v0.8。かがくへんかガス）。"""
        found = []
        for pid in sorted(in_play):
            definition = state.card_def(top[pid])
            for power in definition.powers:
                effect = state.effects.power_effect(definition.id, power)
                if isinstance(effect, SuppressOtherPowers) and pid not in exclusive:
                    found.append((pid, effect))
        return found

    def evasion(pid: int, *, blocked: str | None = None) -> tuple[str | None, str | None]:
        """ログから組み立てた今の場の、ポケモン ``pid`` の「とうめい」（v0.9）: (持っている特殊能力の PowerKey の文字列, はたらいて
        いない理由)。持っていなければ (None, None)。``blocked`` はその時点のねむり・マヒ・こんらん（置きかわる直前の値を渡すため）。"""
        definition = state.card_def(top[pid])
        for index, power in enumerate(definition.powers):
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
        """ログから組み立てた今の場の、ポケモン ``pid`` の「はんげき」（v0.10）: (持っている特殊能力の PowerKey の文字列, 与える量,
        はたらいていない理由)。持っていなければ (None, None, None)。ねむり・マヒ・こんらんは、その時点（ダメージを受けるとき）の値。"""
        definition = state.card_def(top[pid])
        for index, power in enumerate(definition.powers):
            effect = state.effects.power_effect(definition.id, power)
            if isinstance(effect, CounterattackDamage):
                key = f"{definition.id}@power{index}"
                if exclusive.get(pid) is not None:
                    return key, effect.amount, f"{exclusive[pid]} 状態"
                gases = [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(power)]
                if gases:
                    return key, effect.amount, f"かがくへんかガス（ポケモン {gases}）"
                return key, effect.amount, None
        return None, None, None

    def guts_power(pid: int) -> tuple[str | None, PreventKnockOutOnHeads | None, object | None]:
        """ログから組み立てた今の場の、ポケモン ``pid`` の「こんじょう」（v0.11）: (持っている特殊能力の PowerKey の文字列, 実装,
        特殊能力の定義)。持っていなければ (None, None, None)。"""
        definition = state.card_def(top[pid])
        for index, power in enumerate(definition.powers):
            effect = state.effects.power_effect(definition.id, power)
            if isinstance(effect, PreventKnockOutOnHeads):
                return f"{definition.id}@power{index}", effect, power
        return None, None, None

    def rebirth_power(uid: int) -> tuple[str | None, object | None]:
        """カード ``uid`` の「ふしちょう」（v0.12。``ReturnToHandOnKnockOut``）: (PowerKey の文字列, 特殊能力の定義)。なければ (None, None)。"""
        definition = state.card_def(uid)
        for index, power in enumerate(definition.powers):
            if isinstance(state.effects.power_effect(definition.id, power), ReturnToHandOnKnockOut):
                return f"{definition.id}@power{index}", power
        return None, None

    def active_retaliation(pid: int, turn: int) -> dict | None:
        """ログから組み立てた、ポケモン ``pid`` の今の番 ``turn`` にはたらく「ほのおのかべ」の効果（v0.12）。"""
        for (effect_pid, _), info in alive.items():
            if effect_pid == pid and info["kind"] == "retaliation" and info["active_turn"] == turn:
                return info
        return None

    def retaliation_damage_problems(e: dict, ret: dict) -> list[str]:
        """「ほのおのかべ」のダメージのログ（v0.12）: 基本となるダメージが効果の量で、弱点・抵抗力は R団のファイヤーのタイプと、受けた
        ポケモン（いちばん上のカード）の弱点・抵抗力で計算した（W15・W16。p.82「この10ダメージは、弱点・抵抗力の影響を受けます」）。"""
        found = []
        pid = e.get("pokemon_id")
        steps = e.get("steps") or ()
        if not steps or tuple(steps[0]) != ("1 基本となる計算", ret["amount"]):
            found.append(f"{e['turn']} 番の「ほのおのかべ」のダメージの基本となるダメージ {steps[:1]} が {ret['amount']} ではない（W14）")
        if pid in top and ret["pokemon_id"] in top:
            attacker_type = state.card_def(top[ret["pokemon_id"]]).pokemon_type
            receiver = state.card_def(top[pid])
            if e["weakness"] != (receiver.weakness is not None and receiver.weakness is attacker_type):
                found.append(f"{e['turn']} 番の「ほのおのかべ」のダメージの弱点 {e['weakness']} が、タイプと弱点に合わない（W15）")
            if e["resistance"] != (receiver.resistance is not None and receiver.resistance is attacker_type):
                found.append(f"{e['turn']} 番の「ほのおのかべ」のダメージの抵抗力 {e['resistance']} が、タイプと抵抗力に合わない（W16）")
        return found

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
        prior = previous  # 1 つ前のイベント（v0.11。「こんじょう」の宣言・コイン・結果の順番）
        if kind not in ("move_energy", "power_attach_energy", "move_damage_counter"):
            if declared is not None:
                problems.append(
                    f"{declared[0]} 番の特殊能力の宣言（ポケモン {declared[2]}）のすぐあとに、その処理（move_energy・power_attach_energy・"
                    "move_damage_counter）がない"
                )
            declared = None
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
        if previous is not None and previous["kind"] == "coin_flip" and previous["source"] == "power" and kind not in (
            "evade_check", "ko_prevented", "ko_prevention_failed"
        ):
            # v0.9 の「とうめい」の判定・v0.11 の「こんじょう」の結果
            problems.append(
                f"{previous['turn']} 番の特殊能力のコイン（{previous['effect']}）のすぐあとに、その結果（「とうめい」の判定 evade_check・"
                "「こんじょう」の ko_prevented・ko_prevention_failed）がない"
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
            elif kind == "special_conditions_removed" and e["pokemon_id"] == pid and e["reason"] == "replaced":
                follows, expect = True, (pid, element, reaches)  # 置きかえてから、その特殊状態になる
            else:
                follows = kind == "special_condition" and e["pokemon_id"] == pid and e["condition"] == element
            if not follows:
                problems.append(
                    f"{e['turn']} 番の「とうめい」の判定（ポケモン {pid}・{element}・{'受ける' if reaches else '受けない'}）のすぐあとが {kind}"
                )
        # v0.10: ダメージを受けたときに自動的にはたらく特殊能力（カイリキーの「はんげき」）。ワザのダメージを受けたときにはたらいて
        # いたら（due）、そのワザのダメージの要素のあと、ダメージ以外の効果・きぜつの前に、counterattack（か counterattack_skipped）がある
        if attack_window is not None:
            due = attack_window["due"]
            if kind == "damage":
                pid = e.get("pokemon_id", ids.get(e["pokemon"]))
                source = attack_window
                if e.get("retaliation"):
                    # v0.12: 「ほのおのかべ」のダメージ（R団のファイヤーのワザによるダメージ。ワザを使ったポケモンへ）
                    source = attack_window["ret"]
                    if source is None or source["damage_seen"]:
                        problems.append(f"{e['turn']} 番の「ほのおのかべ」のダメージ（ポケモン {pid}）の前に、その「ほのおのかべ」（retaliation）がない・2 回目")
                        source = attack_window
                    else:
                        source["damage_seen"] = True
                        if (pid, e["player"], e.get("effect")) != (attack_window["pokemon_id"], attack_window["player"], source["effect"]):
                            problems.append(f"{e['turn']} 番の「ほのおのかべ」のダメージを受けたのが、ダメージを与えた相手の対戦ポケモン {attack_window['pokemon_id']} ではない（{pid}。W14）")
                        problems.extend(retaliation_damage_problems(e, source))
                elif attack_window["ret_seen"]:
                    problems.append(f"{e['turn']} 番のワザで、「ほのおのかべ」のあとにワザのダメージの要素（ポケモン {pid}）がある（ダメージの処理のあとに与えるはず。p.89・W21）")
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
                        attack_window["ret_due"].append((pid, info))  # v0.12: 「ほのおのかべ」がはたらく（W11・W13）
            elif attack_window["ret_due"] and (
                kind in COUNTER_BARRIERS or (kind == "special_conditions_removed" and e["reason"] == "replaced")
                or (kind == "coin_flip" and e["source"] == "attack" and attack_window["counter_after_coin"])
            ):
                problems.append(f"{e['turn']} 番のワザで、はたらいた「ほのおのかべ」（ポケモン {[d[0] for d in attack_window['ret_due']]}）より先に {kind} がある（p.89・W21）")
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
            if kind == "drain_heal_skipped" and (e["pokemon_id"] not in in_play or damage[e["pokemon_id"]] < state.card_def(top[e["pokemon_id"]]).hp):
                problems.append(f"{e['turn']} 番に、きぜつしていないポケモン {e['pokemon_id']} のとりのぞく効果を処理しなかった")
        if kind == "attack":
            attack_window = {
                "player": e["player"], "pokemon_id": ids.get(e["pokemon"]), "reception": {},
                "effect": f"{state.cards[e['pokemon']].card_id}#{e['attack_index']}",
                # v0.10: はたらいた「はんげき」（場のポケモンの番号, PowerKey, 量）・「はんげき」のログがあったか・「はんげき」で
                # きぜつしたポケモン・効果のコインより前に「はんげき」があるはずか（ダメージのあとのコインが効果を決めるワザ）
                "due": [], "counter_seen": False, "counter_ko": None,
                # v0.11: 「こんじょう」を持つポケモンが相手のワザのダメージを受けたときの特殊状態（ko_able）・決定のあったポケモン（ko_offer）・
                # その結果（declined・declared・heads・tails）・このワザのあとにきぜつしたポケモン（knocked）
                "ko_able": {}, "ko_offer": None, "ko_result": None, "knocked": set(),
                # v0.12: はたらいた「ほのおのかべ」（(場のポケモンの番号, 効果)）・処理中の「ほのおのかべ」（ワザを使ったのは R団のファイヤー）
                "ret_due": [], "ret": None, "ret_seen": False,
                "counter_after_coin": state.effects.attack_entry(state.cards[e["pokemon"]].card_id, e["attack_index"]) is not None
                and state.effects.attack_entry(state.cards[e["pokemon"]].card_id, e["attack_index"]).effect.implementation_id in EFFECT_COIN_AFTER_DAMAGE,
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
        if kind == "special_conditions_removed" and e["reason"] == "replaced":
            replaced[e["pokemon_id"]] = exclusive.get(e["pokemon_id"])
        elif kind == "special_condition":
            replaced.pop(e["pokemon_id"], None)
        previous = e

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
            hp = state.card_def(top[target]).hp
            if kind == "counterattack_skipped":
                if e["reason"] != "knocked_out" or damage[target] < hp:
                    problems.append(f"{e['turn']} 番に、きぜつしていない相手 {target}（ダメージ {damage[target]}）に「はんげき」を与えなかった（{e['reason']}）")
                continue
            if damage[target] >= hp:
                problems.append(f"{e['turn']} 番に、すでに HP 以上のダメージの相手 {target} に「はんげき」を与えた（対象がいない。C15）")
            if amount is not None and e["amount"] != amount:
                problems.append(f"{e['turn']} 番の「はんげき」の量 {e['amount']} が、登録の {amount} と違う")
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
                problems.append(f"{e['turn']} 番の「ほのおのかべ」（ポケモン {holder}）が、ダメージを与えたワザの処理の中にない（W14）")
                continue
            if not attack_window["ret_due"] or attack_window["ret_due"][0][0] != holder:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」（ポケモン {holder}）が、はたらく理由（相手のワザのダメージを、効果がはたらいているポケモンが受けた）なしにある（W4・W11・W13）")
                info = active_retaliation(holder, e["turn"])
            else:
                info = attack_window["ret_due"].pop(0)[1]
            if info is None or pokemon_owner.get(holder) != e["player"] or ids.get(e["pokemon"]) != holder or info["source_card"] != e["source_card"]:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」（ポケモン {holder}）に、今の番にはたらく効果（ログの persistent_effect_added）がない（W4・W5）")
            elif e["effect"] != info["effect"]:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」のワザ {e['effect']} が、効果を与えたワザ {info['effect']} と違う")
            if target not in in_play:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」を与える相手 {target} が場にいない")
                continue
            hp = state.card_def(top[target]).hp
            if kind == "retaliation_skipped":
                if e["reason"] != "knocked_out" or damage[target] < hp:
                    problems.append(f"{e['turn']} 番に、きぜつしていない相手 {target}（ダメージ {damage[target]}）に「ほのおのかべ」を与えなかった（{e['reason']}）")
                continue
            if damage[target] >= hp:
                problems.append(f"{e['turn']} 番に、すでに HP 以上のダメージの相手 {target} に「ほのおのかべ」を与えた（対象がいない。W23）")
            entry = state.effects.attack_entry(*_attack_key(e["effect"]))
            if entry is None or not isinstance(entry.effect, DamageAndRetaliation) or e["amount"] != entry.effect.retaliation:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」の量 {e['amount']} が、ワザ {e['effect']} の登録と違う（W14）")
            attack_window["ret"] = {
                "effect": e["effect"], "player": e["player"], "pokemon_id": holder, "reception": {}, "amount": e["amount"], "damage_seen": False,
            }
            attack_window["ret_seen"] = True
        elif kind == "persistent_effect_skipped":
            # v0.12: ワザを使ったポケモンが相手の「はんげき」で HP 以上になったので、自分に与える持続する効果を与えなかった
            pid = e["pokemon_id"]
            if attack_window is None or pid != attack_window["pokemon_id"] or pid not in in_play or damage[pid] < state.card_def(top[pid]).hp:
                problems.append(f"{e['turn']} 番に、きぜつしていないポケモン {pid} の持続する効果（{e['persistent_effect']}）を与えなかった")
        elif kind == "return_to_hand":
            # v0.12: 「ふしちょう」でトラッシュから手札に加えたカード（きぜつしたポケモンのカード 1 枚だけ。P22〜P24）
            if e["card"] not in discard[e["player"]] or owner.get(e["card"]) != e["player"] or state.card_def(e["card"]).category != "pokemon":
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
                problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）が、相手のワザ（「ほのおのかべ」を含む）のダメージを受けた場のポケモンではない（G4・G15）")
                continue
            gkey, geffect, gpower = guts_power(pid)
            hp = state.card_def(top[pid]).hp
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
            # v0.8: 宣言した時点の場で、宣言しない特殊能力でないこと・はたらいているかがくへんかガスに消されていないこと
            definition = state.card_def(top[e["pokemon_id"]])
            power = definition.powers[e["power_index"]] if 0 <= e["power_index"] < len(definition.powers) else None
            if power is None or power.name_ja != e["power"]:
                problems.append(f"{e['turn']} 番の特殊能力の宣言 {e['power']!r} が、ポケモン {e['pokemon_id']} のいちばん上のカードの特殊能力ではない")
                continue
            effect = state.effects.power_effect(definition.id, power)
            if effect is not None and not effect.declared:
                problems.append(f"{e['turn']} 番に、常にはたらいていて宣言しない特殊能力「{power.name_ja}」の宣言がある")
            gases = [pid for pid, gas in working_gases() if gas.suppresses(power)]
            if gases:
                problems.append(f"{e['turn']} 番に、はたらいている「かがくへんかガス」（ポケモン {gases}）に消されている特殊能力「{power.name_ja}」を使った")
            continue
        elif kind == "special_condition":
            # v0.8: ねむり・マヒ・こんらんは重複しない（ほかのものは、その前に special_conditions_removed（replaced）で消える）
            if e["condition"] in ("sleep", "paralysis", "confusion") and not e.get("already"):
                if e["pokemon_id"] in exclusive:
                    problems.append(f"{e['turn']} 番に、{exclusive[e['pokemon_id']]} のポケモン {e['pokemon_id']} が、それを消さずに {e['condition']} になった")
                exclusive[e["pokemon_id"]] = e["condition"]
        elif kind == "special_conditions_removed":
            if exclusive.get(e["pokemon_id"]) in e["conditions"]:
                del exclusive[e["pokemon_id"]]
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
        elif kind == "recover_energy":
            # v0.9: ワザ（エナジーへんかん）で、ワザを使ったプレイヤーのトラッシュのエネルギーカードを手札に加える
            if attack_window is None or e["pokemon_id"] != attack_window["pokemon_id"] or e["player"] != attack_window["player"]:
                problems.append(f"{e['turn']} 番のトラッシュから手札に加えたエネルギー {e['cards']} が、そのポケモンのワザの処理の中にない")
            for uid in e["cards"]:
                if uid not in discard[e["player"]] or state.card_def(uid).category != "energy":
                    problems.append(f"{e['turn']} 番に手札に加えたカード {uid} が、ログから組み立てたプレイヤー {e['player']} のトラッシュのエネルギーカードにない")
                    continue
                discard[e["player"]].remove(uid)
                hand[e["player"]].append(uid)
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
            if damage[pid] < state.card_def(e["pokemon"]).hp:
                problems.append(f"場のポケモン {pid} が、ログから組み立てたダメージ {damage[pid]}（HP 未満）できぜつした")
            rkey, rpower = rebirth_power(e["pokemon"])
            if rkey is not None and pid in in_play:
                # v0.12: 「ふしちょう」を使えるか（きぜつするときのねむり・マヒ・こんらん（P13〜P17）・はたらいているかがくへんかガス（P18））
                gases = [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(rpower) and gas_pid != pid]
                blocked = f"{exclusive[pid]} 状態" if pid in exclusive else f"かがくへんかガス（ポケモン {gases}）" if gases else None
                rebirth_pending.append({"card": e["pokemon"], "player": e["player"], "power": rkey, "turn": e["turn"], "blocked": blocked})
            in_play.discard(pid)
            exclusive.pop(pid, None)
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
            # v0.12: はたらく番は次の相手の番（与えた番 + 1）。その番の終わりまで残り、そのあとは残らない
            alive[(e["pokemon_id"], e["turn"])] = {
                "kind": e["persistent_effect"], "active_turn": e["active_turn"], "effect": e["effect"], "source_card": e["source_card"],
            }
            if e["active_turn"] != e["turn"] + 1:
                problems.append(f"{e['turn']} 番の持続する効果（ポケモン {e['pokemon_id']}）のはたらく番 {e['active_turn']} が、次の相手の番ではない")
        elif kind == "persistent_effect_removed":
            removed[(e["pokemon_id"], e["created_turn"])] += 1
            info = alive.pop((e["pokemon_id"], e["created_turn"]), None)
            if info is not None and e["reason"] == "expired" and e["turn"] != info["active_turn"]:
                problems.append(f"{e['turn']} 番に、はたらく番 {info['active_turn']} の持続する効果（ポケモン {e['pokemon_id']}）が期限で消えた（早すぎる・遅すぎる）")
        if kind == "turn_end":
            for (pid, created), info in alive.items():
                if info["active_turn"] <= e["turn"]:
                    problems.append(f"{e['turn']} 番の終わり（turn_end）に、はたらく番 {info['active_turn']} の持続する効果（ポケモン {pid}・{created} 番）が残っている")

    if declared is not None:
        problems.append(f"{declared[0]} 番の特殊能力の宣言（ポケモン {declared[2]}）のあとに、その処理がない（ログの最後）")
    if expect is not None:
        problems.append(f"「とうめい」の判定（ポケモン {expect[0]}）のあとに、その要素の処理がない（ログの最後）")
    if attack_window is not None and attack_window["due"]:
        problems.append(f"はたらいた「はんげき」（ポケモン {[d[0] for d in attack_window['due']]}）がない（ログの最後。決定の前に与えるはず）")
    if attack_window is not None and attack_window["ret_due"]:
        problems.append(f"はたらいた「ほのおのかべ」（ポケモン {[d[0] for d in attack_window['ret_due']]}）がない（ログの最後。決定の前に与えるはず）")
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
