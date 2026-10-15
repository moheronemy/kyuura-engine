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
- v0.21: ``--variant gust`` は、固定のデッキのディフェンダー 4 枚のうち 3 枚を突風 3 枚に置き換えた一時的な 60 枚どうしで対戦させる
  （``deck_cards``。公開の固定のデッキ ``kyuura_engine.decks`` は変えない。docs/gust-v0.21.md 6 章）。加える手順は突風だけ:
  その番のほかの操作が終わった（元の手順がワザか番の終わりを選んだ）とき、1 番に 1 回だけ考え、相手の控えポケモンのうち残りの HP が
  いちばん少ないもの（同じならにげるエネルギーが多く、ついているエネルギーが少ないもの、さらに同じなら並びの先）の残りの HP が、相手の
  対戦ポケモンより少なければ使い、決定ではそのポケモンを選ぶ。相手に控えがいなければ使わない（原典で決められない場合。GW5）。
  既定の ``--variant preset`` は v0.20 と同じ（突風のカードがないので、この手順は何もしない）。

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
    AttachEnergy, EndTurn, IllegalActionError, Phase, PlayTrainer, ResolveDecision, UnsupportedError, UseAttack, preset_deck,
)
from kyuura_engine.cards import EnergyType  # noqa: E402
from tests.test_dark_wartortle_games_v0_13 import policy_command as base_policy  # noqa: E402
from tests.v017_games import play_game  # noqa: E402

DECK_A, DECK_B = "hitmonchan-dewgong", "venusaur-parasect"
PROFESSOR_OAK = "PMCG1-077"
GUST = "PMCG1-072"  # v0.21
DEFENDER = "PMCG1-079"
VARIANTS = ("preset", "gust")
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


def deck_cards(deck_id, variant="preset"):
    """対戦に使う 60 枚。``gust`` は固定のデッキのディフェンダー 3 枚を突風 3 枚に置き換えた一時的なデッキ（v0.21。並びの位置はそのまま）。"""
    cards = preset_deck(deck_id).cards()
    if variant == "preset":
        return cards
    if variant != "gust":
        raise ValueError(f"知らない変種 {variant!r}（{VARIANTS}）")
    for _ in range(3):
        cards[cards.index(DEFENDER)] = GUST
    return cards


def _remaining_hp(state, pokemon):
    return state.card_def(pokemon.card).hp - pokemon.damage


def _gust_target(state, options):
    """突風で呼ぶ相手の控えポケモン（決まった手順。強さを目指したものではない）。"""
    def key(pid):
        pokemon = state.find_pokemon(pid)[1]
        return (_remaining_hp(state, pokemon), -state.card_def(pokemon.card).retreat_cost, len(pokemon.energy), options.index(pid))
    return min(options, key=key)


def _gust_command(state, player, tried, counts):
    """v0.21: 突風を使うなら、そのコマンド。1 番に 1 回だけ考える。"""
    p = state.players[player]
    gust = next((u for u in p.hand if _card(state, u) == GUST), None)
    marker = ("gust", state.turn_number)
    if gust is None or marker in tried:
        return None
    tried.add(marker)
    opponent = state.players[1 - player]
    if not opponent.bench:
        counts["gust_kept_no_opponent_bench"] += 1  # 控えがいないときに使えるかは原典で決められない（GW5）ので使わない
        return None
    target = state.find_pokemon(_gust_target(state, [b.pokemon_id for b in opponent.bench]))[1]
    if _remaining_hp(state, target) >= _remaining_hp(state, opponent.active):
        counts["gust_kept_no_better_target"] += 1
        return None
    counts["gust_played"] += 1
    return PlayTrainer(player, gust)


def make_policy(seen: dict, counts: Counter):
    """元の手順に、エネルギーのつけ方とオーキドはかせの使い方（v0.21 から突風の使い方も）を重ねる。``seen`` に最後に見た状態を残す
    （止まったときの報告のため）。"""

    def policy(state, *, janken_winner, cure, tried):
        seen["state"] = state
        d = state.decision
        if state.phase is Phase.DECISION and d.context_value("use", (None, None, None))[2] == GUST:
            # v0.21: 突風の決定は、使ったプレイヤー（番のプレイヤー）が相手の控えポケモンから選ぶ
            chosen = _gust_target(state, list(d.options))
            counts[f"gust_candidates_{len(d.options)}"] += 1
            if len(d.options) > 1:
                counts["gust_chose_among_many"] += 1
                if chosen != d.options[0]:
                    counts["gust_chose_not_first"] += 1
            return ResolveDecision(d.player, d.id, (chosen,))
        command = base_policy(state, janken_winner=janken_winner, cure=cure, tried=tried)
        if state.phase is not Phase.MAIN:
            return command
        player = state.current_player
        p = state.players[player]
        if isinstance(command, AttachEnergy):
            return _energy_command(state, player, command, counts)
        if isinstance(command, (UseAttack, EndTurn)):
            gust = _gust_command(state, player, tried, counts)
            if gust is not None:
                return gust
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


def gust_uses(state):
    """v0.21: 突風を使うたびの、ログから分かる結果（使った番・プレイヤー・入れ替えた相手・その番のワザ・新しい対戦ポケモンへのダメージ・きぜつ）。"""
    uses, log = [], state.log
    for i, e in enumerate(log):
        if e["kind"] != "play_trainer" or _card(state, e["card"]) != GUST:
            continue
        user, turn = e["player"], e["turn"]
        use = {"turn": turn, "user": user, "switched": False}
        uses.append(use)
        switch = log[i + 1] if i + 1 < len(log) and log[i + 1]["kind"] == "switch" else None
        if switch is None:
            continue
        new_card = switch["new_active"]  # ダメージ・きぜつのログはいちばん上のカードで指す（相手のポケモンは自分の番に進化しない）
        use.update(switched=switch["player"] == 1 - user, new_active=_card(state, switch["new_active"]),
                   old_active=_card(state, switch["old_active"]))
        rest = [x for x in log[i + 2:] if x["turn"] == turn]
        attack = next((k for k, x in enumerate(rest) if x["kind"] == "attack" and x["player"] == user), None)
        use["attacked_after"] = attack is not None
        if attack is not None:
            after = rest[attack + 1:]
            use["attack"] = f"{_card(state, rest[attack]['pokemon'])}#{rest[attack]['attack_index']}"
            use["hit_new_active"] = any(x["kind"] == "damage" and x["pokemon"] == new_card and x["amount"] > 0 for x in after)
            use["knocked_out_new_active"] = any(x["kind"] == "knock_out" and x["pokemon"] == new_card for x in after)
    return uses


def play(deck_ids, seed, *, max_steps=8000, keep_state=False, variant="preset"):
    """1 局を進め、終わり方と動きを返す。``keep_state`` なら最後の状態を ``"state"`` に入れる（テストの監査のため。JSON にはしない）。"""
    seen, counts = {}, Counter()
    decks = tuple(deck_cards(d, variant) for d in deck_ids)
    result = {"seed": seed, "decks": list(deck_ids), "first": seed % 2}
    if variant != "preset":
        result["variant"] = variant
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
        if variant == "gust":
            result["gust_uses"] = gust_uses(state)
    if keep_state:
        result["state"] = state
        result["commands"] = commands
    return result


def run(games, *, start=0, max_steps=8000, keep_state=False, variant="preset"):
    """席を入れかえて ``games`` 局ずつ（seed は start から）。"""
    results = []
    for seat in ((DECK_A, DECK_B), (DECK_B, DECK_A)):
        for seed in range(start, start + games):
            results.append(play(seat, seed, max_steps=max_steps, keep_state=keep_state, variant=variant))
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
        if "gust_uses" in r:
            gust = s.setdefault("gust", {"uses": Counter(), "games_with_use": 0, "examples_attack_after": []})
            gust["games_with_use"] += bool(r["gust_uses"])
            for use in r["gust_uses"]:
                gust["uses"].update({"played": 1, "switched": use["switched"], "attacked_after": use.get("attacked_after", False),
                                     "hit_new_active": use.get("hit_new_active", False),
                                     "knocked_out_new_active": use.get("knocked_out_new_active", False)})
                if use.get("hit_new_active") and len(gust["examples_attack_after"]) < 5:
                    gust["examples_attack_after"].append({"seed": r["seed"], "decks": r["decks"], **use})
    return json.loads(json.dumps(s))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--games", type=int, default=20, help="席ごとの局数（合計はこの 2 倍）")
    parser.add_argument("--start", type=int, default=0, help="最初の seed")
    parser.add_argument("--max-steps", type=int, default=8000)
    parser.add_argument("--out", type=Path, help="1 局ごとの結果と集計を書き出す JSON")
    parser.add_argument("--variant", choices=VARIANTS, default="preset", help="gust: ディフェンダー 3 枚を突風 3 枚に置き換えた一時的なデッキ（v0.21）")
    args = parser.parse_args(argv)
    began = time.time()
    results = run(args.games, start=args.start, max_steps=args.max_steps, variant=args.variant)
    summary = summarize(results)
    summary["elapsed"] = round(time.time() - began, 1)
    if args.out:
        args.out.write_text(json.dumps({"summary": summary, "games": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    keys = ("games", "outcomes", "halt_codes", "unresolved_rejections", "wins", "end_conditions", "elapsed") + (("gust",) if "gust" in summary else ())
    print(json.dumps({k: summary[k] for k in keys}, ensure_ascii=False))
    return 0 if summary["outcomes"].get("internal_error", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
