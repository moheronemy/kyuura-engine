"""v0.27: ストライク（PMCG2-017）を入れた一時的なデッキの対戦（構成 A・構成 B）と、ストライクの動きの数え（docs/scyther-v0.27.md 6〜8 章）。

- 構成 A: 第2版のデッキ A2 のコラッタ 2 枚をストライク 2 枚に置き換えた一時的なデッキ（A2S。``tools/preset_deck_games.py`` の変種 ``scyther``。
  ほかのカード・エネルギー（闘 12・水 10）は同じなので「つるぎのまい」（草）は使えない）と第2版のデッキ B2 の対戦を、元の A2 と B2 の対戦と、
  同じ手順・同じ seed・席の入れかえで比べる（``tools/preset_deck_comparison.py`` の ``play_pairing``）。
- 構成 B: 第2版のデッキ B2 のモンジャラ 2 枚をストライク 2 枚に置き換えた検証用のデッキ（B2S。変種 ``scyther_grass``。草エネルギー 19 枚で
  「つるぎのまい」「きりさく」の両方を使える）と A2 の対戦。正式な開始（``new_game``）から「つるぎのまい」→ 次の自分の番の「きりさく」を確かめる。

公開の固定のデッキ（``kyuura_engine.decks``）は変えない。手順（``make_policy``）は v0.26 と同じで、ストライクのための手順は加えていない（ワザは
使えるうちダメージの目安の数字のいちばん大きいもの。目安のない「つるぎのまい」は 0 として比べる。「にげる」の操作はない）。勝率でデッキの
良し悪しを判断しない。

ストライクの動きは、最後の状態のログだけから数える（``scyther_uses``。選ぶ操作を変えない）。

    python3 tools/scyther_games.py --seeds 10 --out <作業用の場所>/scyther.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import preset_deck_comparison as comparison  # noqa: E402
from tools.preset_deck_games import GUST, SCYTHER  # noqa: E402

SWORDS_DANCE, SLASH = 0, 1  # ストライクのワザの位置
NEXT_TURN_KIND = "next_turn_attack_damage"
# (名前, デッキ A・B のラベル, 変種)。どれも同じ seed・席の入れかえ
RUNS = (
    ("A2-B2", "A2", "B2", "preset"),  # 構成 A の比べる相手（元の A2）
    ("A2S-B2", "A2", "B2", "scyther"),  # 構成 A
    ("A2-B2S", "A2", "B2", "scyther_grass"),  # 構成 B
)


def scyther_uses(state):
    """ログから数えたストライクの動き（プレイヤーごと）。ストライクのいないプレイヤーは数えない。

    - ``in_play``: 場に出したストライクの枚数（対戦準備・ベンチに出す）
    - ``swords_dance``・``slash``: ワザの宣言の回数（こんらんしたワザも数える）。``slash_boosted``: 2 段階の記録（``damage_set``）のある
      「きりさく」のダメージ
    - ``effect_added``・``effect_removed_<理由>``: 「つるぎのまい」の効果を与えた回数と、消えた理由（``expired``: 次の自分の番の終わり、
      ``retreat``・``switch``・``forced_switch``: ベンチにもどった、``knock_out``: きぜつ）。``expired_unused``: 期限で消えた効果のうち、
      はたらく番に強化した「きりさく」がなかったもの。``again_on_active_turn``: 前の効果のはたらく番に、同じポケモンがもう一度「つるぎのまい」を
      使った回数
    - ``retreated_from``: ストライクがバトル場からにげた回数。``switched_from``: 自分のポケモンいれかえ・相手の「ふきとばし」で
      ベンチにもどった回数。``gusted_from``: 相手の突風でベンチにもどった回数（``switch`` のログはどちらも持ち主のプレイヤーなので、直前の
      トレーナーの使用で分ける）
    - ``knocked_out``: きぜつしたストライク
    - ``examples``: 「つるぎのまい」→ 強化した「きりさく」の（与えた番, 強化した番, ダメージ）
    """
    card = {uid: c.card_id for uid, c in state.cards.items()}
    scyther_uids = {uid for uid, cid in card.items() if cid == SCYTHER}
    counts = {p: Counter() for p in (0, 1) if any(state.cards[u].owner == p for u in scyther_uids)}
    examples = {p: [] for p in counts}
    pid_of = {}  # ストライクのカードの uid → 効果を与えたときの場のポケモンの番号（ストライクは進化しないので、場にいる間は同じ）
    added = {}  # (場のポケモンの番号, 与えた番) → はたらく番
    boosted_turns = set()  # (場のポケモンの番号, 番)
    current_attack = None
    last_trainer = None  # 直前に使ったトレーナー（プレイヤー, カード id）
    for e in state.log:
        kind = e["kind"]
        if kind == "place_starting_pokemon":
            for uid in (e["active"], *e["bench"]):
                if uid in scyther_uids:
                    counts[e["player"]]["in_play"] += 1
        elif kind == "play_to_bench" and e["card"] in scyther_uids:
            counts[e["player"]]["in_play"] += 1
        elif kind == "attack":
            current_attack = (e["player"], e["pokemon"], e["attack_index"]) if e["pokemon"] in scyther_uids else None
            if current_attack is not None:
                counts[e["player"]]["swords_dance" if e["attack_index"] == SWORDS_DANCE else "slash"] += 1
        elif kind == "damage" and current_attack is not None and not e.get("retaliation") and e.get("damage_set"):
            player, uid, index = current_attack
            counts[player]["slash_boosted"] += 1
            pid = pid_of.get(uid)
            boosted_turns.add((pid, e["turn"]))
            created = next((c for (p, c), active in added.items() if p == pid and active == e["turn"]), None)
            examples[player].append((created, e["turn"], e["amount"]))
        elif kind == "persistent_effect_added" and e["persistent_effect"] == NEXT_TURN_KIND:
            counts[e["player"]]["effect_added"] += 1
            pid_of[e["pokemon"]] = e["pokemon_id"]
            if added.get((e["pokemon_id"], e["turn"] - 2)) == e["turn"]:
                counts[e["player"]]["again_on_active_turn"] += 1
            added[(e["pokemon_id"], e["turn"])] = e["active_turn"]
        elif kind == "persistent_effect_removed" and e["persistent_effect"] == NEXT_TURN_KIND:
            counts[e["player"]][f"effect_removed_{e['reason']}"] += 1
            if e["reason"] == "expired" and (e["pokemon_id"], e["turn"]) not in boosted_turns:
                counts[e["player"]]["expired_unused"] += 1
        elif kind == "retreat" and e["old_active"] in scyther_uids:
            counts[e["player"]]["retreated_from"] += 1
        elif kind in ("switch", "forced_switch") and e.get("old_active") in scyther_uids:
            gusted = kind == "switch" and last_trainer == (1 - e["player"], GUST)
            counts[e["player"]]["gusted_from" if gusted else "switched_from"] += 1
        elif kind == "knock_out" and e["pokemon"] in scyther_uids:
            counts[e["player"]]["knocked_out"] += 1
        if kind == "play_trainer":
            last_trainer = (e["player"], card[e["card"]])
        if kind == "turn_end":
            current_attack = None
    return {str(p): {**dict(c), "examples": examples[p]} for p, c in counts.items()}


def summarize_scyther(games):
    """ストライクの数えを、デッキのラベルごとに合計する（局数・ストライクを場に出した局数も）。"""
    totals = {}
    for r in games:
        for player, uses in r.get("scyther", {}).items():
            label = r["labels"][int(player)]
            t = totals.setdefault(label, {"games": 0, "games_with_scyther_in_play": 0, "games_with_boosted_slash": 0, "counts": Counter(),
                                          "examples": []})
            t["games"] += 1
            t["games_with_scyther_in_play"] += uses.get("in_play", 0) > 0
            t["games_with_boosted_slash"] += uses.get("slash_boosted", 0) > 0
            t["counts"].update({k: v for k, v in uses.items() if k != "examples"})
            t["examples"].extend({"seed": r["seed"], "labels": r["labels"], "created": c, "turn": turn, "damage": amount}
                                 for c, turn, amount in uses["examples"])
    return totals


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seeds", type=int, default=10, help="組ごと・席ごとの seed の数（1 組の局数はこの 2 倍。1 以上）")
    parser.add_argument("--start", type=int, default=0, help="最初の seed")
    parser.add_argument("--max-steps", type=int, default=8000)
    parser.add_argument("--out", type=Path, help="1 局ごとの記録と集計を書き出す JSON")
    args = parser.parse_args(argv)
    if args.seeds < 1:
        parser.error("--seeds は 1 以上")
    seeds = range(args.start, args.start + args.seeds)
    began = time.time()
    results = {}
    for name, a, b, variant in RUNS:
        games = comparison.play_pairing(a, b, seeds, max_steps=args.max_steps, variant=variant, extra={"scyther": scyther_uses})
        results[name] = {"variant": variant, "games": games, "summary": comparison.summarize(games), "scyther": summarize_scyther(games)}
    elapsed = round(time.time() - began, 1)
    if args.out:
        args.out.write_text(json.dumps({"seeds": [args.start, args.start + args.seeds], "elapsed": elapsed, "runs": results},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
    brief = {name: {**{k: v["summary"][k] for k in ("games", "outcomes", "halt_codes", "unresolved_rejections", "audit_failures", "wins")},
                    "scyther": {label: {k: t[k] for k in ("games", "games_with_scyther_in_play", "games_with_boosted_slash", "counts")}
                                for label, t in v["scyther"].items()}}
             for name, v in results.items()}
    print(json.dumps({"elapsed": elapsed, "runs": brief}, ensure_ascii=False))
    bad = sum(v["summary"]["outcomes"].get(k, 0) for v in results.values() for k in ("internal_error", "unexpected_rejection"))
    bad += sum(sum(v["summary"]["audit_failures"].values()) for v in results.values())
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
