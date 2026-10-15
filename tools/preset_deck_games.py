"""v0.20: 固定のデッキ（``kyuura_engine.decks``）どうしを、正式な対戦開始（``new_game``・60 枚・サイド 6 枚）から決まった手順で対戦させ、
終わり方を分類し、各デッキの狙った動きが起こったかを数える（C 段階の道具。ふだんのテストは tests/test_preset_decks_v0_20.py が小さく走らせる）。

使い方::

    python3 tools/preset_deck_games.py --games 20 --out /tmp/preset.json   # 席を入れかえて 20 局ずつ（合計 40 局）

駆動の方法（docs/preset-decks-v0.20.md 5 章）:

- 対戦の手順は、既存の統合テストの決まった手順（``tests.v017_games.play_game`` と ``tests.test_dark_wartortle_games_v0_13.policy_command``。
  v0.2b〜v0.13 の手順を重ねたもの: ベンチに出す・エネルギーをつける・進化・トレーナー（マサキ・きずぐすり・ポケモンいれかえ・プラスパワー・
  ディフェンダー）・エナジートランス・ワザの選び方・拒否されたときの扱い）をそのまま使う。対戦相手の AI ではない。
- この道具が加える手順は 2 つだけ（どちらもデッキの考え方を確かめるための決まった手順で、強さを目指したものではない）:
  1. エネルギー: 元の手順は手札の最初のエネルギーをバトル場につける。ここでは、バトル場のポケモンのワザの必要なタイプが足りなければその
     タイプを、足りていればベンチのうちそのデッキで育てる系統（ジュゴンの系統・フシギダネの系統・パラスの系統）で足りないタイプを優先する。
  2. オーキドはかせ: その番のほかの操作が終わった（元の手順がワザか番の終わりを選んだ）ときだけ、山札が 7 枚以上・残りの手札が 2 枚以下で、
     かつ、残りの手札に「場のポケモンから次の番に進化できる進化カード」がないときに使う（進化先を捨てない判断）。
- 先攻・後攻は seed の偶奇（``janken_winner = seed % 2``）で、席（デッキ A がプレイヤー 0 か 1 か）は ``--games`` 局ずつ入れかえる。

終わり方の分類: 通常の勝敗（``game_over``）・サドンデス（``sudden_death``。エンジンは次の対戦を始めない）・既知の未解決の裁定による停止
（``halted``。コード付き）・手数の上限・想定外の拒否（手順が想定していない ``IllegalActionError``・``UnsupportedError``。駆動の誤りか、規定の
確認が要る）・内部エラー（不変条件の違反・そのほかの例外）。原典で決められないとして拒否された操作（``UNRESOLVED_…``）のあと別の操作で
続けた回数は、終わり方とは別に数える。どれも集計から落とさない。
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
    AttachEnergy, EndTurn, IllegalActionError, Phase, PlayTrainer, UnsupportedError, UseAttack, preset_deck,
)
from kyuura_engine.cards import EnergyType  # noqa: E402
from tests.test_dark_wartortle_games_v0_13 import policy_command as base_policy  # noqa: E402
from tests.v017_games import play_game  # noqa: E402

DECK_A, DECK_B = "hitmonchan-dewgong", "venusaur-parasect"
PROFESSOR_OAK = "PMCG1-077"
OAK_MIN_DECK = 7
OAK_MAX_REST = 2
# そのデッキで育てる系統（エネルギーをベンチにつけるときに優先する。デッキの考え方。docs/preset-decks-v0.20.md）
GROWING = {"PMCG1-029", "PMCG1-030", "PMCG1-001", "PMCG1-008", "PMCG1-011", "PMCG2-003", "PMCG2-010"}
STEP_LIMIT = "決まった手数で終わらなかった"


def _card(state, uid):
    return state.cards[uid].card_id


def _missing_types(state, pokemon):
    """そのポケモンのいちばん重いワザに足りないエネルギーのタイプ（無色を除く）。"""
    attacks = state.card_def(pokemon.card).attacks
    if not attacks:
        return set()
    have = Counter(state.energy_types(pokemon))
    need = Counter(t for t in max(attacks, key=lambda a: len(a.cost)).cost if t is not EnergyType.COLORLESS)
    return {t for t, n in need.items() if have[t] < n}


def _has_pending_evolution(state, player, rest):
    p = state.players[player]
    names = {state.card_def(pk.card).name_ja for pk in p.in_play()}
    return any(state.card_def(u).is_evolution_pokemon and state.card_def(u).evolves_from in names for u in rest)


def make_policy(seen: dict, counts: Counter):
    """元の手順に、エネルギーのつけ方とオーキドはかせの使い方を重ねる。``seen`` に最後に見た状態を残す（止まったときの報告のため）。"""

    def policy(state, *, janken_winner, cure, tried):
        seen["state"] = state
        command = base_policy(state, janken_winner=janken_winner, cure=cure, tried=tried)
        if state.phase is not Phase.MAIN:
            return command
        player = state.current_player
        p = state.players[player]
        if isinstance(command, AttachEnergy):
            return _energy_command(state, player, command, counts)
        if isinstance(command, (UseAttack, EndTurn)):
            oak = next((u for u in p.hand if _card(state, u) == PROFESSOR_OAK), None)
            if oak is not None:
                rest = [u for u in p.hand if u != oak]
                marker = ("oak", state.turn_number)
                if len(p.deck) < OAK_MIN_DECK:
                    if marker not in tried:
                        counts["oak_skipped_small_deck"] += 1
                        tried.add(marker)
                elif len(rest) > OAK_MAX_REST:
                    pass
                elif _has_pending_evolution(state, player, rest):
                    if marker not in tried:
                        counts["oak_kept_for_evolution"] += 1
                        tried.add(marker)
                else:
                    return PlayTrainer(player, oak)
        return command

    return policy


def _energy_command(state, player, command, counts):
    p = state.players[player]
    energies = [u for u in p.hand if state.card_def(u).is_basic_energy]
    by_type = {}
    for u in energies:
        by_type.setdefault(state.card_def(u).provides, u)
    for t in sorted(_missing_types(state, p.active), key=lambda t: t.value):
        if t in by_type:
            counts["attach_active_needed"] += 1
            return AttachEnergy(player, by_type[t], p.active.card)
    for pk in p.bench:
        if _card(state, pk.card) in GROWING:
            for t in sorted(_missing_types(state, pk), key=lambda t: t.value):
                if t in by_type:
                    counts["attach_bench_growing"] += 1
                    return AttachEnergy(player, by_type[t], pk.card)
    counts["attach_default"] += 1
    return command


def deck_stats(state, player, commands):
    """1 人のプレイヤー（デッキ）の、ログから数えた動き。"""
    c = Counter()
    starting_bench = next((len(e["bench"]) for e in state.log if e["kind"] == "place_starting_pokemon" and e["player"] == player), 0)
    c["bench_played"] = starting_bench + sum(1 for e in state.log if e["kind"] == "play_to_bench" and e["player"] == player)
    for e in state.log:
        if e.get("player") != player:
            continue
        kind = e["kind"]
        if kind == "attach_energy":
            c[f"attach_{state.card_def(e['energy']).provides.name}"] += 1
        elif kind == "evolve":
            c[f"evolve_{_card(state, e['to_card'])}"] += 1
        elif kind == "play_trainer":
            c[f"trainer_{_card(state, e['card'])}"] += 1
        elif kind == "attack":
            c[f"attack_{_card(state, e['pokemon'])}#{e['attack_index']}"] += 1
        elif kind == "move_energy":
            c["energy_trans"] += 1
        elif kind == "retreat":
            c["retreat"] += 1
        elif kind == "discard_hand":
            c["oak_discarded"] += len(e["cards"])
            c["oak_discarded_evolution"] += sum(state.card_def(u).is_evolution_pokemon for u in e["cards"])
            c["oak_discarded_energy"] += sum(state.card_def(u).is_basic_energy for u in e["cards"])
        elif kind == "take_prize":
            c["prizes_taken"] += 1
    c["turns_ended_without_attack"] = sum(1 for cmd in commands if isinstance(cmd, EndTurn) and cmd.player == player)
    p = state.players[player]
    leftover = [u for u in p.hand + p.deck + p.prizes]
    c["trainers_left"] = sum(state.card_def(u).category == "trainer" for u in leftover)
    c["trainers_left_in_hand"] = sum(state.card_def(u).category == "trainer" for u in p.hand)
    c["evolution_cards_left"] = sum(state.card_def(u).is_evolution_pokemon for u in leftover)
    return c


def play(deck_ids, seed, *, max_steps=8000, keep_state=False):
    """1 局を進め、終わり方と動きを返す。``keep_state`` なら最後の状態を ``"state"`` に入れる（テストの監査のため。JSON にはしない）。"""
    seen, counts = {}, Counter()
    decks = tuple(preset_deck(d).cards() for d in deck_ids)
    result = {"seed": seed, "decks": list(deck_ids), "first": seed % 2}
    commands = []
    try:
        state, commands, observed = play_game(decks, seed, policy=make_policy(seen, counts), max_steps=max_steps)
        outcome = state.phase.value
        if state.phase is Phase.HALTED:
            outcome = "halted"
            result["halt_code"] = next((e["code"] for e in reversed(state.log) if e["kind"] == "halted"), None)
    except AssertionError as error:
        state, observed = seen.get("state"), Counter()
        outcome = "step_limit" if str(error) == STEP_LIMIT else "internal_error"
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
            result["winner_deck"] = deck_ids[state.result.winner] if state.result.winner is not None else None
            result["conditions"] = [c[1] for c in state.result.conditions]
        result["per_deck"] = {deck_ids[p]: dict(deck_stats(state, p, commands)) for p in (0, 1)}
    if keep_state:
        result["state"] = state
        result["commands"] = commands
    return result


def run(games, *, start=0, max_steps=8000, keep_state=False):
    """席を入れかえて ``games`` 局ずつ（seed は start から）。"""
    results = []
    for seat in ((DECK_A, DECK_B), (DECK_B, DECK_A)):
        for seed in range(start, start + games):
            results.append(play(seat, seed, max_steps=max_steps, keep_state=keep_state))
    return results


def summarize(results):
    s = {"games": len(results), "outcomes": Counter(), "halt_codes": Counter(), "unresolved_rejections": Counter(),
         "wins": Counter(), "end_conditions": Counter(), "per_deck": {DECK_A: Counter(), DECK_B: Counter()},
         "policy": Counter(), "games_with": {DECK_A: Counter(), DECK_B: Counter()}}
    for r in results:
        s["outcomes"][r["outcome"]] += 1
        if r.get("halt_code"):
            s["halt_codes"][r["halt_code"]] += 1
        s["unresolved_rejections"].update(r["unresolved_rejections"])
        if r.get("winner_deck"):
            s["wins"][r["winner_deck"]] += 1
        s["end_conditions"].update(r.get("conditions", []))
        s["policy"].update(r["policy"])
        for deck, stats in r.get("per_deck", {}).items():
            s["per_deck"][deck].update(stats)
            for key, value in stats.items():
                if value:
                    s["games_with"][deck][key] += 1
    return json.loads(json.dumps(s))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--games", type=int, default=20, help="席ごとの局数（合計はこの 2 倍）")
    parser.add_argument("--start", type=int, default=0, help="最初の seed")
    parser.add_argument("--max-steps", type=int, default=8000)
    parser.add_argument("--out", type=Path, help="1 局ごとの結果と集計を書き出す JSON")
    args = parser.parse_args(argv)
    began = time.time()
    results = run(args.games, start=args.start, max_steps=args.max_steps)
    summary = summarize(results)
    summary["elapsed"] = round(time.time() - began, 1)
    if args.out:
        args.out.write_text(json.dumps({"summary": summary, "games": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("games", "outcomes", "halt_codes", "unresolved_rejections", "wins", "end_conditions", "elapsed")},
                     ensure_ascii=False))
    return 0 if summary["outcomes"].get("internal_error", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
