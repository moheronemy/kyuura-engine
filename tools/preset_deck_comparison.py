"""v0.26: 固定のデッキの第1版と第2版を、同じ seed・同じ席の入れかえ・同じ決まった手順で 4 組比べる（C 段階の道具。ふだんのテストは
tests/test_preset_decks_v0_26.py が小さく走らせる）。対戦相手の AI ではなく、デッキの強さ・釣り合いを判断する道具でもない。

使い方::

    python3 tools/preset_deck_comparison.py --seeds 10 --out /path/compare.json   # 4 組 × 2 席 × 10 seed = 80 局

比べる組（``PAIRINGS``）: A1 対 B1・A2 対 B1・A1 対 B2・A2 対 B2（A1 = ``hitmonchan-dewgong``、A2 = ``hitmonchan-dewgong-v2``、
B1 = ``venusaur-parasect``、B2 = ``venusaur-parasect-v2``）。どの組も同じ seed（``--start`` から ``--seeds`` 個）を、デッキ A がプレイヤー 0 の
席と 1 の席で 1 局ずつ使う（先攻・後攻は seed の偶奇。tools/preset_deck_games.py と同じ）。

手順: tools/preset_deck_games.py の ``play``（変種 ``preset``・``observe=True``）をそのまま使う。手順は 4 組とも同じ関数（``make_policy``）で、
第1版にも第2版にも同じ判断をする（手札にないカードの手順は何もしない）。この道具は手順を変えず、対戦が終わってから数える。

数え方（docs/preset-decks-v0.26.md 5 章）:

- ログ（``state.log``）から: 切り直し・番・ワザ・ワザを使わずに終えた番・エネルギー（タイプとつけた先）・進化（2 進化はポケモン育て屋さん
  経由か）・トレーナー・エナジートランス・きぜつ・山札切れ・負けた条件。どれもログの記録で、手順の判断から推測したものではない。
- 番の終わりの確かめ（「攻撃できなかった番」）: 受け付けた操作の列を ``new_game`` から同じ seed でやり直し（``apply_command`` は渡された状態を
  変えないので、元の対戦と同じ状態が順に得られる。最後のログが元の対戦と同じことを確かめ、違えば監査の失敗に数える）、ワザを使わずに番を
  終えた（``EndTurn``）直前の状態で、バトル場のポケモンのすべてのワザの ``UseAttack`` をエンジンに渡して、受け付けるか・拒否のコードを見る。
  受け付けるワザがあれば「攻撃できたが使わなかった番」、なければ「攻撃できなかった番」で、理由はエンジンの拒否のコード。確かめるのは
  その時点のバトル場のポケモンだけで、その番のほかの操作（エネルギーのつけ先・にげる・入れ替え）を変えれば攻撃できたかは確かめない。
- エネルギーの不足（拒否のコードが ``INSUFFICIENT_ENERGY`` だけの番）: いちばん少ないエネルギーで使えるワザについて、ついているエネルギーと
  ワザに必要なエネルギーを比べ、「色」（枚数は足りるがタイプが足りない）・「枚数」（タイプは足りるが枚数が足りない）・「両方」に分ける。
  その番に手札からエネルギーをつけたか・手札に足りないタイプの基本エネルギーカードがあったかも記録する（つけていれば足りたかは確かめない）。
- 監査: 終局の状態の不変条件（``check_invariants``）・ログの監査（``log_problems``）・書き出しの監査（``serialization_problems``）・
  トレーナーを使ってからトラッシュするまでのログ（``trainer_sequence_problems``）・決定ごとの持ち主と使用中のカード（``check_…``）・やり直しの一致。
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kyuura_engine import (  # noqa: E402
    EndTurn, IllegalActionError, Phase, UnsupportedError, UseAttack, apply_command, check_invariants, new_game,
)
from kyuura_engine.cards import EnergyType  # noqa: E402
from tests.log_audit import log_problems, serialization_problems  # noqa: E402
from tools import preset_deck_games as driver  # noqa: E402

DECKS = {"A1": "hitmonchan-dewgong", "A2": "hitmonchan-dewgong-v2", "B1": "venusaur-parasect", "B2": "venusaur-parasect-v2"}
LABELS = {deck_id: label for label, deck_id in DECKS.items()}


def label_of(deck_id, variant="preset"):
    """デッキのラベル。v0.27 の第2版の一時的なデッキ（``driver.V2_SUBSTITUTIONS``）で置き換えたデッキは、末尾に「S」（A2S・B2S）。"""
    if deck_id in driver.V2_SUBSTITUTIONS.get(variant, {}):
        return LABELS[deck_id] + "S"
    return LABELS[deck_id]
PAIRINGS = (("A1", "B1"), ("A2", "B1"), ("A1", "B2"), ("A2", "B2"))
OUTCOMES = ("game_over", "sudden_death", "halted", "step_limit", "unexpected_rejection", "internal_error")
CHECK_FAILURES = ("check_decision_player_mismatch", "check_in_use_mismatch", "check_in_use_left_in_main")

VENUSAUR, IVYSAUR, PARASECT, TANGELA, RATTATA = "PMCG1-011", "PMCG1-008", "PMCG2-010", "PMCG1-007", "PMCG1-060"


def _cid(state, uid):
    return state.cards[uid].card_id


def _energy_shortage(state, pokemon):
    """いちばん少ないエネルギーで使えるワザについての不足（"color"・"count"・"both"・None）。"""
    attacks = state.card_def(pokemon.card).attacks
    if not attacks:
        return None
    attack = min(attacks, key=lambda a: len(a.cost))
    have = Counter(state.energy_types(pokemon))
    need = Counter(t for t in attack.cost if t is not EnergyType.COLORLESS)
    typed = sum(max(0, n - have[t]) for t, n in need.items())
    count = len(attack.cost) > len(pokemon.energy)
    if typed and count:
        return "both", {t.name for t, n in need.items() if have[t] < n}
    if typed:
        return "color", {t.name for t, n in need.items() if have[t] < n}
    if count:
        return "count", set()
    return None


def probe_turn_end(state, player):
    """``EndTurn`` の直前の状態で、バトル場のポケモンのワザをエンジンが受け付けるか（状態は変えない）。"""
    active = state.players[player].active
    definition = state.card_def(active.card)
    codes = []
    for index in range(len(definition.attacks)):
        try:
            apply_command(state, UseAttack(player, index))
            codes.append("ok")
        except (IllegalActionError, UnsupportedError) as error:
            codes.append(error.code)
    probe = {"active": definition.id, "codes": codes}
    if "ok" in codes:
        probe["class"] = "could_attack"
    elif not codes:
        probe["class"] = "no_attacks"
    else:
        probe["class"] = "+".join(sorted(set(codes)))
        if set(codes) == {"INSUFFICIENT_ENERGY"}:
            shortage = _energy_shortage(state, active)
            if shortage is not None:
                kind, missing = shortage
                hand = state.players[player].hand
                probe.update(shortage=kind, missing=sorted(missing),
                             attached_this_turn=state.energy_attachments_this_turn > 0,
                             hand_energy=sum(state.card_def(u).is_basic_energy for u in hand),
                             hand_has_missing=any(state.card_def(u).is_basic_energy and state.card_def(u).provides.name in missing
                                                  for u in hand))
    return probe


def replay(result):
    """受け付けた操作の列を new_game からやり直し、番の終わりの確かめ・ベンチの数を記録する。最後のログが元の対戦と同じか（``same``）も返す。"""
    state = result["state"]
    decks = tuple(driver.deck_cards(d, result.get("variant", "preset")) for d in result["decks"])  # v0.27: 一時的なデッキも同じ 60 枚
    current = new_game(*decks, result["seed"])
    probes = {0: [], 1: []}
    empty_bench_turn_ends = Counter()
    max_in_play = Counter()
    for command in result["commands"]:
        if current.phase is Phase.MAIN and isinstance(command, (EndTurn, UseAttack)):
            player = command.player
            if not current.players[player].bench:
                empty_bench_turn_ends[player] += 1
            if isinstance(command, EndTurn):
                probes[player].append({"turn": current.turn_number, **probe_turn_end(current, player)})
        current = apply_command(current, command)
        for p in (0, 1):
            if current.players[p].active is not None:
                max_in_play[p] = max(max_in_play[p], len(current.players[p].in_play()))
    same = [dict(e) for e in current.log] == [dict(e) for e in state.log]
    return probes, empty_bench_turn_ends, max_in_play, same


def _retrieval_origin(log, index, uid):
    """エネルギー回収で手札に加えたカードが、その前にどの処理でトラッシュに置かれたか。"""
    for e in reversed(log[:index]):
        kind = e["kind"]
        if kind in ("discard_hand", "discard_from_hand") and uid in e.get("cards", ()):
            return kind
        if kind == "knock_out" and uid in e.get("discarded_energy", ()):
            return "knock_out"
        if kind == "retreat" and uid in e.get("discarded", ()):
            return "retreat"
    return "unknown"


def deck_metrics(result, player, probes, empty_bench_turn_ends, max_in_play):
    """1 局の 1 人のプレイヤー（デッキ）の数え。どれもログ・やり直しの記録から数える。"""
    state = result["state"]
    log = state.log
    m = Counter()
    lists = {}
    m["mulligans"] = sum(1 for e in log if e["kind"] == "mulligan" and e["player"] == player)
    m["own_turns"] = sum(1 for e in log if e["kind"] == "turn_start" and e["player"] == player)
    m["attack_turns"] = len({e["turn"] for e in log if e["kind"] == "attack" and e["player"] == player})
    m["ended_without_attack"] = sum(1 for e in log if e["kind"] == "end_turn_without_attack" and e["player"] == player)
    m["deck_out"] = int(any(e["kind"] == "deck_out" and e["player"] == player for e in log))
    m["turn_ends_with_empty_bench"] = empty_bench_turn_ends[player]
    m["max_in_play"] = max_in_play[player]
    for probe in probes[player]:
        m[f"probe_{probe['class']}"] += 1
        if "shortage" in probe:
            m[f"shortage_{probe['active']}_{probe['shortage']}"] += 1
            m[f"shortage_{probe['shortage']}"] += 1
            m["shortage_missing_" + "_".join(probe["missing"] or ["none"])] += 1
            m["shortage_attached_this_turn"] += probe["attached_this_turn"]
            m["shortage_hand_has_missing"] += probe["hand_has_missing"]
            # 手札からつけていない・手札に基本エネルギーカードが 1 枚もない番（その番にエネルギーをつける手段がなかった）
            m["shortage_no_energy_in_hand_no_attach"] += not probe["attached_this_turn"] and probe["hand_energy"] == 0
    if state.result is not None:
        for winner, condition in state.result.conditions:
            if winner != player:
                m[f"lost_{condition}"] += 1
            else:
                m[f"won_{condition}"] += 1
    venusaur_first = None
    for i, e in enumerate(log):
        if e.get("player") != player:
            continue
        kind = e["kind"]
        if kind == "place_starting_pokemon":
            for uid in (e["active"], *e["bench"]):
                m["basics_into_play"] += 1
                m[f"placed_{_cid(state, uid)}"] += 1
        elif kind == "play_to_bench":
            m["basics_into_play"] += 1
            m[f"placed_{_cid(state, e['card'])}"] += 1
        elif kind == "attach_energy":
            m[f"attach_{state.card_def(e['energy']).provides.name}"] += 1
            m[f"attach_to_{_cid(state, e['target'])}"] += 1
        elif kind == "evolve":
            to = e["to_card_id"]
            m[f"evolve_{to}"] += 1
            if to == VENUSAUR:
                route = "breeder" if "trainer_card" in e else "stage1"
                m[f"evolve_{to}_{route}"] += 1
                if venusaur_first is None:
                    own = sum(1 for x in log[:i] if x["kind"] == "turn_start" and x["player"] == player)
                    venusaur_first = {"turn": e["turn"], "own_turn": own, "route": route}
        elif kind == "play_trainer":
            m[f"trainer_{_cid(state, e['card'])}"] += 1
        elif kind == "attack":
            m[f"attack_{_cid(state, e['pokemon'])}#{e['attack_index']}"] += 1
            if venusaur_first is not None and _cid(state, e["pokemon"]) == VENUSAUR:
                m["venusaur_attacks_after_complete"] += 1
        elif kind == "move_energy":
            m["energy_trans"] += 1
            if venusaur_first is not None:
                m["energy_trans_after_complete"] += 1
        elif kind == "retreat":
            m["retreat"] += 1
            if _cid(state, e["old_active"]) == RATTATA:
                m["rattata_retreated_from_active"] += 1
            if _cid(state, e["new_active"]) == RATTATA:
                m["rattata_retreated_into_active"] += 1
        elif kind == "promote_active" and _cid(state, e["pokemon"]) == RATTATA:
            m["rattata_promoted"] += 1
        elif kind == "switch" and _cid(state, e["new_active"]) == RATTATA:
            m["rattata_switched_in"] += 1
        elif kind == "knock_out":
            m["own_knocked_out"] += 1
            m[f"knocked_out_{_cid(state, e['pokemon'])}"] += 1
        elif kind == "take_prize":
            m["prizes_taken"] += 1
        elif kind == "discard_hand":
            m["oak_discarded"] += len(e["cards"])
            m["oak_discarded_energy"] += sum(state.card_def(u).is_basic_energy for u in e["cards"])
            m["oak_discarded_evolution"] += sum(state.card_def(u).is_evolution_pokemon for u in e["cards"])
    if venusaur_first is not None:
        lists["venusaur_first"] = venusaur_first
    p = state.players[player]
    leftover = p.hand + p.deck + p.prizes
    m["evolution_cards_left"] = sum(state.card_def(u).is_evolution_pokemon for u in leftover)
    m["trainers_left"] = sum(state.card_def(u).category == "trainer" for u in leftover)
    for key in ("computer_uses", "trader_uses", "retrieval_uses", "breeder_uses", "gust_uses"):
        uses = [u for u in result.get(key, ()) if u["user"] == player]
        if key == "retrieval_uses":
            # retrieval_uses はログの順に並ぶので、このプレイヤーのエネルギー回収の使用（play_trainer）とログの順で対応する
            plays = [i for i, e in enumerate(log) if e["kind"] == "play_trainer" and e["player"] == player
                     and _cid(state, e["card"]) == driver.ENERGY_RETRIEVAL]
            for use, index in zip(uses, plays, strict=True):
                retrieved = next((e["cards"] for e in log[index:index + 5] if e["kind"] == "retrieve_energy"), ())
                use["origins"] = [_retrieval_origin(log, index, uid) for uid in retrieved]
        lists[key] = uses
    return dict(m), lists


def play_pairing(a, b, seeds, *, max_steps=8000, variant="preset", extra=None):
    """1 組（デッキ A・B のラベル）を、席を入れかえて ``seeds`` の seed で対戦させる。``variant``（v0.27）は第2版の一時的なデッキ
    （``driver.V2_SUBSTITUTIONS``）。``extra``（v0.27）は最後の状態から 1 局の記録に加える値を求める関数（``record[name] = f(state)``）。"""
    games = []
    for seat in ((DECKS[a], DECKS[b]), (DECKS[b], DECKS[a])):
        for seed in seeds:
            r = driver.play(seat, seed, max_steps=max_steps, keep_state=True, observe=True, variant=variant)
            record = game_record(r)
            for name, f in (extra or {}).items():
                if r.get("state") is not None:
                    record[name] = f(r["state"])
            games.append(record)
    return games


def game_record(r):
    """1 局の記録（JSON にできる値だけ）。"""
    state = r.get("state")
    record = {k: r[k] for k in ("seed", "decks", "first", "outcome", "steps", "unresolved_rejections") if k in r}
    record.update({k: r[k] for k in ("halt_code", "winner_deck", "conditions", "turns", "error") if k in r})
    variant = r.get("variant", "preset")
    if variant != "preset":
        record["variant"] = variant
    record["labels"] = [label_of(d, variant) for d in r["decks"]]
    record["policy"] = r["policy"]
    audit = Counter()
    # やり直しと監査は、play_game が終わりまで進めた局（通常の勝敗・サドンデス・停止）だけ。手数の上限・想定外の拒否・内部エラーの局は
    # 受け付けた操作の列が残らないので、監査していない局として数える（summarize の audited_games）
    if state is not None and r["outcome"] in ("game_over", "sudden_death", "halted"):
        probes, empty, max_in_play, same = replay(r)
        audit["replay_mismatch"] += not same
        audit["invariants"] += bool(check_invariants(state))
        audit["log"] += bool(log_problems(state))
        audit["serialization"] += bool(serialization_problems(state))
        audit["trainer_sequence"] += bool(r.get("trainer_sequence_problems"))
        for key in CHECK_FAILURES:
            audit[key] += r["policy"].get(key, 0)
        record["per_deck"] = {}
        for player in (0, 1):
            metrics, lists = deck_metrics(r, player, probes, empty, max_in_play)
            record["per_deck"][record["labels"][player]] = {"metrics": metrics, **lists}
    record["audit"] = {k: v for k, v in audit.items() if v}
    return record


def summarize(games):
    """1 組の集計。``games`` は ``game_record`` の並び。値はどれも（回数, 局数, 分母）が分かる形にする。"""
    s = {"games": len(games), "outcomes": Counter(r["outcome"] for r in games), "halt_codes": Counter(r.get("halt_code") for r in games
                                                                                                        if r.get("halt_code")),
         "unresolved_rejections": Counter(), "audit_failures": Counter(), "audited_games": 0, "wins": Counter(),
         "end_conditions": Counter(), "decks": {}}
    labels = list(dict.fromkeys(label for r in games for label in r["labels"]))
    for r in games:
        s["unresolved_rejections"].update(r["unresolved_rejections"])
        s["audit_failures"].update(r["audit"])
        s["audited_games"] += "per_deck" in r
        if r.get("winner_deck"):
            s["wins"][label_of(r["winner_deck"], r.get("variant", "preset"))] += 1
        s["end_conditions"].update(r.get("conditions", []))
    for label in labels:
        played = [r for r in games if label in r.get("per_deck", {}) and r["per_deck"][label]["metrics"].get("own_turns", 0) > 0]
        totals, games_with = Counter(), Counter()
        firsts, uses = [], {k: [] for k in ("computer_uses", "trader_uses", "retrieval_uses", "breeder_uses", "gust_uses")}
        for r in played:
            deck = r["per_deck"][label]
            totals.update(deck["metrics"])
            games_with.update({k: 1 for k, v in deck["metrics"].items() if v})
            if "venusaur_first" in deck:
                firsts.append(deck["venusaur_first"])
            for k in uses:
                uses[k].extend(deck.get(k, ()))
        audited = [r for r in games if "per_deck" in r]
        d = {"games_with_turns": len(played), "totals": totals, "games_with": games_with,
             "wins": s["wins"].get(label, 0), "finished": s["outcomes"].get("game_over", 0),
             # 切り直しは番の始まる前（対戦準備）に起こるので、番のない局（対戦準備で止まった局）も数える（分母は監査した局）
             "mulligans": {"games": len(audited), "mulligans": sum(r["per_deck"][label]["metrics"].get("mulligans", 0) for r in audited),
                           "games_with": sum(r["per_deck"][label]["metrics"].get("mulligans", 0) > 0 for r in audited)}}
        if firsts:
            own = [f["own_turn"] for f in firsts]
            d["venusaur_first"] = {"games": len(firsts), "own_turn_median": statistics.median(own), "own_turn_min": min(own),
                                   "own_turn_max": max(own), "route": Counter(f["route"] for f in firsts)}
        d["search"] = _search_summary(uses)
        s["decks"][label] = d
    return json.loads(json.dumps(s))


def _search_summary(uses):
    out = {}
    comp = uses["computer_uses"]
    out["computer"] = {"uses": len(comp), "searched": Counter(u.get("searched_category", "none") for u in comp),
                       "searched_card": Counter(u.get("searched", "none") for u in comp),
                       "used_same_turn": sum(bool(u.get("used_same_turn")) for u in comp),
                       "used_later": sum("used_as" in u and not u.get("used_same_turn") for u in comp),
                       "not_used": sum("searched" in u and "used_as" not in u for u in comp),
                       "used_as": Counter(u.get("used_as", "not_used") for u in comp)}
    trade = uses["trader_uses"]
    out["trader"] = {"uses": len(trade), "taken_stage": Counter(u.get("taken_stage", "none") for u in trade),
                     "taken_card": Counter(u.get("taken", "none") for u in trade),
                     "took_back": sum(bool(u.get("took_back")) for u in trade),
                     "used_same_turn": sum(bool(u.get("used_same_turn")) for u in trade),
                     "used_later": sum("used_as" in u and not u.get("used_same_turn") for u in trade),
                     "not_used": sum("taken" in u and "used_as" not in u for u in trade)}
    ret = uses["retrieval_uses"]
    out["retrieval"] = {"uses": len(ret), "cards": sum(len(u.get("retrieved", ())) for u in ret),
                        "fates": Counter(f for u in ret for f in u.get("fates", ())),
                        "origins": Counter(o for u in ret for o in u.get("origins", ()))}
    br = uses["breeder_uses"]
    out["breeder"] = {"uses": len(br), "evolutions": Counter(f"{u.get('from_card')}->{u.get('to_card')}" for u in br),
                      "power_same_turn": sum(u.get("powers_same_turn", 0) > 0 for u in br),
                      "attacked_same_turn": sum(bool(u.get("attacked_same_turn")) for u in br),
                      "attacked_next_own_turn": sum(bool(u.get("attacked_next_own_turn")) for u in br)}
    gust = uses["gust_uses"]
    out["gust"] = {"uses": len(gust), "switched": sum(bool(u.get("switched")) for u in gust),
                   "attacked_after": sum(bool(u.get("attacked_after")) for u in gust),
                   "knocked_out_new_active": sum(bool(u.get("knocked_out_new_active")) for u in gust)}
    return out


def compare(seeds, *, max_steps=8000, pairings=PAIRINGS):
    results = {}
    for a, b in pairings:
        games = play_pairing(a, b, seeds, max_steps=max_steps)
        results[f"{a}-{b}"] = {"games": games, "summary": summarize(games)}
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seeds", type=int, default=10, help="組ごと・席ごとの seed の数（1 組の局数はこの 2 倍。1 以上）")
    parser.add_argument("--start", type=int, default=0, help="最初の seed")
    parser.add_argument("--max-steps", type=int, default=8000)
    parser.add_argument("--out", type=Path, help="1 局ごとの記録と集計を書き出す JSON")
    args = parser.parse_args(argv)
    if args.seeds < 1:
        parser.error("--seeds は 1 以上")
    began = time.time()
    results = compare(range(args.start, args.start + args.seeds), max_steps=args.max_steps)
    elapsed = round(time.time() - began, 1)
    if args.out:
        args.out.write_text(json.dumps({"seeds": [args.start, args.start + args.seeds], "elapsed": elapsed, "pairings": results},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
    brief = {name: {k: v["summary"][k] for k in ("games", "outcomes", "halt_codes", "unresolved_rejections", "audit_failures", "wins")}
             for name, v in results.items()}
    print(json.dumps({"elapsed": elapsed, "pairings": brief}, ensure_ascii=False))
    bad = sum(v["summary"]["outcomes"].get(k, 0) for v in results.values() for k in ("internal_error", "unexpected_rejection"))
    bad += sum(sum(v["summary"]["audit_failures"].values()) for v in results.values())
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
