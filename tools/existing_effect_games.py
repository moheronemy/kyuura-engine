"""v0.28・v0.29: 既存の効果の型の登録だけで加えたポケモン（v0.28 の 10 枚・v0.29 の 14 枚）の検証用デッキの対戦
（docs/existing-effect-pokemon-v0.28.md 5 章・docs/existing-effect-pokemon-v0.29.md 4.2）。

C 段階の道具（ふだんのテストは tests/test_existing_effect_games_v0_28.py・tests/test_existing_effect_games_v0_29.py が数局だけ走らせる）。対戦相手の AI ではなく、カードの強さ・採用価値・
釣り合いを判断する道具でもない。勝敗は、対戦が通常の終わり方をしたかの確かめにだけ使う。

使い方::

    python3 tools/existing_effect_games.py --seeds 10 --out <作業用の場所>/existing.json   # 3 組 × 2 席 × 10 seed = 60 局
    python3 tools/existing_effect_games.py --batch v0.29 --seeds 10 --out <作業用の場所>/existing29.json   # v0.29 の 3 組（60 局）

検証用デッキ（``DECKS``。公開の固定のデッキ ``kyuura_engine.decks`` には入れない。どれも対応済みのカードと基本エネルギーだけの 60 枚）:

- ``W28``（水・無色）: ラプラス 3・ヒトデマン 3・スターミー 2・トサキント 3・アズマオウ 2・シェルダー 3・ラッキー 2、トレーナー 12（マサキ・
  ポケモンいれかえ・きずぐすり・プラスパワー・ディフェンダー・突風 2 枚ずつ）、水エネルギー 30。
- ``G28``（草・超・無色）: カイロス 4・タマタマ 4・プリン 4・スリープ 4、トレーナーは ``W28`` と同じ 12、草エネルギー 16・超エネルギー 16。
- 組（``PAIRINGS``）: ``W28`` 対 ``G28``（新しいカードどうし）・``W28`` 対 ``B2``（第2版のフシギバナ・パラセクト）・``G28`` 対 ``A2``（第2版の
  エビワラー・ジュゴン）。どれも同じ seed で、席を入れかえて 1 局ずつ（先攻・後攻は seed の偶奇）。
- v0.29（``--batch v0.29``。``PAIRINGS_V0_29``）: ``GW29``（草・水）: アーボ・ズバット・ナゾノクサ・ドガース・タケシのズバット・ニョロモ・
  カスミのトサキント 3 枚ずつ、トレーナーは ``W28`` と同じ 12、草エネルギー 16・水エネルギー 11。``LF29``（雷・闘・無色）: ビリリダマ・マチスの
  コイル・マチスのビリリダマ・ワンリキー・タケシのイシツブテ・ミニリュウ・タケシのベロリンガ 3 枚ずつ、同じトレーナー 12、雷エネルギー 14・
  闘エネルギー 13。組は ``GW29`` 対 ``LF29``・``GW29`` 対 ``B2``・``LF29`` 対 ``A2``。v0.28 のデッキに v0.29 のカードは入っていないので、
  v0.28 の組の結果は v0.28 と同じ。

手順: tools/preset_deck_games.py の ``make_policy``（v0.26 から変えていない手順。決定ごとの持ち主・使用中のカードの確かめ ``check_…`` も数える）に、
v0.28・v0.29 のカード（``TARGETS``）のワザの選び方だけを重ねる（``make_policy``）。バトル場がそのカードで、元の手順がワザか番の終わりを選んだとき、払えるワザ
（この番に拒否されたワザを除く）のうち、その局でそのカードがまだ使った回数の少ないワザを選ぶ（同じなら、ダメージの目安の数字が大きいもの →
位置の小さいもの）。ダメージを与えないワザ（さいみんじゅつ・こもりうた・ちょうおんぱ・まるまる・からをとじる・じこさいせい）も使うための手順で、
強さを目指したものではない。そのほかの判断（エネルギー・進化・トレーナー・にげる・決定への答え）は元の手順のまま。

終わり方の分類は tools/preset_deck_games.py と同じ（通常の勝敗・サドンデス・既知の未解決の裁定による停止・手数の上限・想定外の拒否・内部エラー）。
原典で決められないとして拒否された操作（``UNRESOLVED_…``）のあと別の操作で続けた回数は、終わり方とは別に数える。監査（``audit``）は、
受け付けた操作の列を ``new_game`` からやり直してログが同じか・不変条件・ログの監査・書き出しの監査・トレーナーのログの並び・決定ごとの確かめ。
v0.28 のカードの動きはログだけから数える（``card_uses``。選ぶ操作を変えない）。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kyuura_engine import (  # noqa: E402
    EndTurn, IllegalActionError, Phase, UnsupportedError, UseAttack, apply_command, check_invariants, new_game, preset_deck,
)
from kyuura_engine.cards import can_pay_cost  # noqa: E402
from tests.log_audit import log_problems, serialization_problems  # noqa: E402
from tests.v017_games import play_game  # noqa: E402
from tools import preset_deck_games as driver  # noqa: E402

LAPRAS, STARMIE, GOLDEEN, SEAKING, PINSIR = "PMCG3-022", "PMCG1-026", "PMCG2-021", "PMCG2-022", "PMCG2-018"
EXEGGCUTE, JIGGLYPUFF, CHANSEY, DROWZEE, SHELLDER = "PMCG2-006", "PMCG2-035", "PMCG1-068", "PMCG1-045", "PMCG3-012"
V0_28 = (LAPRAS, STARMIE, GOLDEEN, SEAKING, PINSIR, EXEGGCUTE, JIGGLYPUFF, CHANSEY, DROWZEE, SHELLDER)
# v0.29（kyuura データの採用。どれもたねポケモン）
POLIWAG, ROCKET_EKANS, ROCKET_ZUBAT, ROCKET_ODDISH, ROCKET_KOFFING = "PMCG1-024", "PMCG4-001", "PMCG4-002", "PMCG4-003", "PMCG4-005"
ROCKET_VOLTORB, ROCKET_MACHOP, ROCKET_DRATINI, BROCKS_ZUBAT, MISTYS_GOLDEEN = "PMCG4-027", "PMCG4-040", "PMCG4-051", "PMCG5-001", "PMCG5-026"
LT_SURGES_MAGNEMITE, LT_SURGES_VOLTORB, BROCKS_GEODUDE, BROCKS_LICKITUNG = "PMCG5-037", "PMCG5-038", "PMCG5-046", "PMCG5-061"
V0_29 = (POLIWAG, ROCKET_EKANS, ROCKET_ZUBAT, ROCKET_ODDISH, ROCKET_KOFFING, ROCKET_VOLTORB, ROCKET_MACHOP, ROCKET_DRATINI, BROCKS_ZUBAT,
         MISTYS_GOLDEEN, LT_SURGES_MAGNEMITE, LT_SURGES_VOLTORB, BROCKS_GEODUDE, BROCKS_LICKITUNG)
TARGETS = V0_28 + V0_29  # ワザの選び方を重ね、動きを数えるカード
STARYU = "PMCG1-025"
GRASS, WATER, LIGHTNING, PSYCHIC, FIGHTING = "PMCG1-097", "PMCG1-099", "PMCG1-100", "PMCG1-101", "PMCG1-102"
SWITCH = "PMCG1-073"
TRAINERS = ((driver.BILL, 2), (SWITCH, 2), (driver.POTION, 2), (driver.PLUSPOWER, 2), (driver.DEFENDER, 2), (driver.GUST, 2))
# 検証用デッキ（(カード id, 枚数) の並び）。第2版の固定のデッキはそのまま使う
DECKS = {
    "W28": ((LAPRAS, 3), (STARYU, 3), (STARMIE, 2), (GOLDEEN, 3), (SEAKING, 2), (SHELLDER, 3), (CHANSEY, 2), *TRAINERS, (WATER, 30)),
    "G28": ((PINSIR, 4), (EXEGGCUTE, 4), (JIGGLYPUFF, 4), (DROWZEE, 4), *TRAINERS, (GRASS, 16), (PSYCHIC, 16)),
    "GW29": ((ROCKET_EKANS, 3), (ROCKET_ZUBAT, 3), (ROCKET_ODDISH, 3), (ROCKET_KOFFING, 3), (BROCKS_ZUBAT, 3), (POLIWAG, 3), (MISTYS_GOLDEEN, 3),
             *TRAINERS, (GRASS, 16), (WATER, 11)),
    "LF29": ((ROCKET_VOLTORB, 3), (LT_SURGES_MAGNEMITE, 3), (LT_SURGES_VOLTORB, 3), (ROCKET_MACHOP, 3), (BROCKS_GEODUDE, 3), (ROCKET_DRATINI, 3),
             (BROCKS_LICKITUNG, 3), *TRAINERS, (LIGHTNING, 14), (FIGHTING, 13)),
}
PRESETS = {"A2": driver.DECK_A2, "B2": driver.DECK_B2}
PAIRINGS = (("W28", "G28"), ("W28", "B2"), ("G28", "A2"))
PAIRINGS_V0_29 = (("GW29", "LF29"), ("GW29", "B2"), ("LF29", "A2"))
BATCHES = {"v0.28": PAIRINGS, "v0.29": PAIRINGS_V0_29}
CHECK_FAILURES = ("check_decision_player_mismatch", "check_in_use_mismatch", "check_in_use_left_in_main")
# ワザの結果として数えるログ（v0.28・v0.29 のカードのワザの中に出たもの）
RESULT_EVENTS = ("special_condition", "persistent_effect_added", "discard_energy", "remove_all_damage_counters", "drain_heal",
                 "damage_prevented", "confusion_damage", "attack_evaded")


def deck_cards(label):
    """60 枚のカード id の並び。検証用デッキは ``DECKS`` の順、第2版は公開の固定のデッキのまま。"""
    if label in PRESETS:
        return preset_deck(PRESETS[label]).cards()
    if label not in DECKS:
        raise ValueError(f"知らないデッキ {label!r}（{sorted(DECKS) + sorted(PRESETS)}）")
    cards = [card for card, count in DECKS[label] for _ in range(count)]
    if len(cards) != 60:
        raise ValueError(f"{label} は {len(cards)} 枚")
    return cards


def _uses_so_far(state, player, card_id):
    """その局でプレイヤーが ``card_id`` のポケモンで宣言したワザの回数（ワザの位置ごと）。"""
    used = Counter()
    for e in state.log:
        if e["kind"] == "attack" and e["player"] == player and state.cards[e["pokemon"]].card_id == card_id:
            used[e["attack_index"]] += 1
    return used


def make_policy(seen: dict, counts: Counter):
    """tools/preset_deck_games.py の手順（``checks=True``）に、v0.28・v0.29 のカードのワザの選び方を重ねる（モジュールの説明）。"""
    base = driver.make_policy(seen, counts, checks=True)

    def policy(state, *, janken_winner, cure, tried):
        command = base(state, janken_winner=janken_winner, cure=cure, tried=tried)
        if state.phase is not Phase.MAIN or not isinstance(command, (UseAttack, EndTurn)) or "attack" in tried:
            return command
        player = state.current_player
        active = state.players[player].active
        card_id = state.cards[active.card].card_id
        if card_id not in TARGETS:
            return command
        attacks = state.card_def(active.card).attacks
        provided = state.energy_types(active)
        usable = [a.index for a in attacks if can_pay_cost(a.cost, provided) and ("attack_index", a.index) not in tried]
        if not usable:
            return command
        used = _uses_so_far(state, player, card_id)
        choice = min(usable, key=lambda i: (used[i], -(attacks[i].damage or 0), i))
        chosen = UseAttack(player, choice)
        if chosen != command:
            counts[f"coverage_choice_{card_id}#{choice}"] += 1
        return chosen

    return policy


def play(labels, seed, *, max_steps=8000, keep_state=False):
    """1 局を進め、終わり方と動きを返す（終わり方の分類は tools/preset_deck_games.py の ``play`` と同じ）。"""
    seen, counts = {}, Counter()
    decks = tuple(deck_cards(label) for label in labels)
    result = {"seed": seed, "decks": list(labels), "first": seed % 2}
    commands = []
    try:
        state, commands, observed = play_game(decks, seed, policy=make_policy(seen, counts), max_steps=max_steps)
        outcome = state.phase.value
        if state.phase is Phase.HALTED:
            outcome = "halted"
            result["halt_code"] = next((e["code"] for e in reversed(state.log) if e["kind"] == "halted"), None)
    except AssertionError as error:
        state, observed = seen.get("state"), Counter()
        outcome = "step_limit" if str(error) == driver.STEP_LIMIT else "internal_error"
        result["error"] = str(error)[:500]
    except (IllegalActionError, UnsupportedError) as error:
        state, observed = seen.get("state"), Counter()
        outcome = "unexpected_rejection"
        result["error"] = f"{error.code}: {error}"[:500]
    except Exception as error:  # noqa: BLE001  内部エラーも集計から落とさない
        state, observed = seen.get("state"), Counter()
        outcome = "internal_error"
        result["error"] = "".join(traceback.format_exception_only(type(error), error))[:500]
    result["outcome"] = outcome
    result["steps"] = len(commands)
    result["observed"] = dict(observed)
    result["unresolved_rejections"] = {k: v for k, v in observed.items() if "UNRESOLVED_" in k}
    result["policy"] = dict(counts)
    if state is not None:
        result["turns"] = state.turn_number
        if state.result is not None:
            result["winner_deck"] = labels[state.result.winner] if state.result.winner is not None else None
            result["conditions"] = [c[1] for c in state.result.conditions]
        result["card_uses"] = card_uses(state)
        result["trainer_sequence_problems"] = driver.trainer_sequence_problems(state)
    result["audit"] = audit(result, state, commands)
    if keep_state:
        result["state"] = state
        result["commands"] = commands
    return result


def audit(result, state, commands):
    """監査の失敗の数（失敗がなければ空）。やり直しと監査は、終わりまで進んだ局（通常の勝敗・サドンデス・停止）だけ。"""
    failures = Counter()
    if state is None or result["outcome"] not in ("game_over", "sudden_death", "halted"):
        return {"not_audited": 1}
    current = new_game(*(deck_cards(label) for label in result["decks"]), result["seed"])
    for command in commands:
        current = apply_command(current, command)
    failures["replay_mismatch"] += [dict(e) for e in current.log] != [dict(e) for e in state.log]
    failures["invariants"] += bool(check_invariants(state))
    failures["log"] += bool(log_problems(state))
    failures["serialization"] += bool(serialization_problems(state))
    failures["trainer_sequence"] += bool(result.get("trainer_sequence_problems"))
    for key in CHECK_FAILURES:
        failures[key] += result["policy"].get(key, 0)
    return {k: v for k, v in failures.items() if v}


def card_uses(state):
    """ログから数えた v0.28・v0.29 のカードの動き（カード id ごと）。

    - ``in_play``: 場に出した枚数（対戦準備・ベンチに出す）。``evolved_to``: そのカードに進化した回数（``evolve`` の ``to_card``）
    - ``attack#i``: ワザの宣言の回数（こんらんのコインで「うら」だったワザも数える）。``confused_failed#i``: そのうちこんらんの 20 になったもの
    - ``damage#i``: そのワザで相手に与えたダメージのログ（``damage_prevented`` は数えない）。``self_damage#i``: 自分へのダメージのログ
    - ``base#i=N``: 相手へのダメージの基本となるダメージ（p.321 の 1 段階。「みずでっぽう」の追加・コインのダメージの「おもて」の数を見る）
    - ``<ログの種類>#i``: そのワザの中に出た結果のログ（``RESULT_EVENTS``。特殊状態は ``special_condition_<状態>#i``）
    - ``protected_by_own_effect``: 自分のワザ（まるまる・からをとじる）の効果で、相手のワザのダメージを受けなかった回数（``damage_prevented``）。
      ``effect_removed_<理由>``: そのカードの持続する効果が消えた回数（``expired``・``retreat``・``switch``・``knock_out`` など）
    - ``knocked_out``: きぜつした回数
    """
    card = {uid: c.card_id for uid, c in state.cards.items()}
    uses = {cid: Counter() for cid in TARGETS}
    current = None  # (カード id, ワザの位置)
    for e in state.log:
        kind = e["kind"]
        if kind == "place_starting_pokemon":
            for uid in (e["active"], *e["bench"]):
                if card[uid] in uses:
                    uses[card[uid]]["in_play"] += 1
        elif kind == "play_to_bench" and card[e["card"]] in uses:
            uses[card[e["card"]]]["in_play"] += 1
        elif kind == "evolve" and card[e["to_card"]] in uses:
            uses[card[e["to_card"]]]["evolved_to"] += 1
        elif kind == "knock_out" and card.get(e.get("pokemon")) in uses:
            uses[card[e["pokemon"]]]["knocked_out"] += 1
        elif kind == "damage_prevented" and card[e["pokemon"]] in uses and e.get("source_card") == e["pokemon"]:
            uses[card[e["pokemon"]]]["protected_by_own_effect"] += 1  # 「まるまる」「からをとじる」の効果で、相手のワザのダメージを受けなかった
        elif kind == "persistent_effect_removed" and card[e["pokemon"]] in uses:
            uses[card[e["pokemon"]]][f"effect_removed_{e['reason']}"] += 1
        if kind == "attack":
            current = (card[e["pokemon"]], e["attack_index"]) if card[e["pokemon"]] in uses else None
            if current is not None:
                uses[current[0]][f"attack#{current[1]}"] += 1
        elif kind in ("turn_end", "turn_start"):
            current = None
        elif current is not None:
            cid, index = current
            if kind == "confusion_damage":
                uses[cid][f"confused_failed#{index}"] += 1
            elif kind == "damage" and not e.get("retaliation") and e.get("target") == "self":
                uses[cid][f"self_damage#{index}"] += 1
            elif kind == "damage" and not e.get("retaliation") and "target" not in e:
                uses[cid][f"damage#{index}"] += 1
                uses[cid][f"base#{index}={e['steps'][0][1]}"] += 1
            elif kind == "special_condition" and e.get("effect") == f"{cid}#{index}":
                uses[cid][f"special_condition_{e['condition']}#{index}"] += 1
            elif kind in RESULT_EVENTS and kind != "special_condition":
                uses[cid][f"{kind}#{index}"] += 1
    return {cid: dict(c) for cid, c in uses.items() if c}


def summarize(games):
    """1 組（または全体）の集計。終わり方・停止のコード・``UNRESOLVED_…`` のあと続けた回数・監査の失敗・対象のカードの動きの合計と局数。"""
    s = {"games": len(games), "outcomes": Counter(r["outcome"] for r in games), "halt_codes": Counter(r["halt_code"] for r in games
                                                                                                     if r.get("halt_code")),
         "unresolved_rejections": Counter(), "audit_failures": Counter(), "end_conditions": Counter(), "wins": Counter(),
         "cards": {}, "games_with": {}}
    for r in games:
        s["unresolved_rejections"].update(r["unresolved_rejections"])
        s["audit_failures"].update(r["audit"])
        s["end_conditions"].update(r.get("conditions", []))
        if r.get("winner_deck"):
            s["wins"][r["winner_deck"]] += 1
        for cid, counts in r.get("card_uses", {}).items():
            s["cards"].setdefault(cid, Counter()).update(counts)
            s["games_with"].setdefault(cid, Counter()).update({k: 1 for k, v in counts.items() if v})
    return json.loads(json.dumps(s))


def run(seeds, *, max_steps=8000, pairings=PAIRINGS):
    results = {}
    for a, b in pairings:
        games = [play(seat, seed, max_steps=max_steps) for seat in ((a, b), (b, a)) for seed in seeds]
        results[f"{a}-{b}"] = {"games": games, "summary": summarize(games)}
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--batch", choices=sorted(BATCHES), default="v0.28", help="組の一覧（v0.28 の 3 組か v0.29 の 3 組）")
    parser.add_argument("--seeds", type=int, default=10, help="組ごと・席ごとの seed の数（1 組の局数はこの 2 倍。1 以上）")
    parser.add_argument("--start", type=int, default=0, help="最初の seed")
    parser.add_argument("--max-steps", type=int, default=8000)
    parser.add_argument("--out", type=Path, help="1 局ごとの記録と集計を書き出す JSON")
    args = parser.parse_args(argv)
    if args.seeds < 1:
        parser.error("--seeds は 1 以上")
    seeds = range(args.start, args.start + args.seeds)
    began = time.time()
    results = run(seeds, max_steps=args.max_steps, pairings=BATCHES[args.batch])
    total = summarize([g for v in results.values() for g in v["games"]])
    elapsed = round(time.time() - began, 1)
    if args.out:
        args.out.write_text(json.dumps({"batch": args.batch, "seeds": [args.start, args.start + args.seeds], "elapsed": elapsed, "runs": results, "total": total},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
    brief = {name: {k: v["summary"][k] for k in ("games", "outcomes", "halt_codes", "unresolved_rejections", "audit_failures")}
             for name, v in results.items()}
    print(json.dumps({"elapsed": elapsed, "runs": brief, "total_cards": total["cards"]}, ensure_ascii=False))
    bad = sum(total["outcomes"].get(k, 0) for k in ("internal_error", "unexpected_rejection", "step_limit"))
    bad += sum(total["audit_failures"].values())
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
