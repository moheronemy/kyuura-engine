"""v0.20: 固定のデッキを選んで、正式な対戦開始（new_game）から最初の番の始まりまで進める小さな例。

これは対戦の「開始」だけの例です。人間が最後まで遊べる操作画面ではありません（GUI・Web・通信対戦・対戦相手の AI はありません）。
最初の番から先は、``apply_command`` にコマンドを渡して進めます（README の「使い方」）。

使い方::

    python3 examples/start_preset_game.py --list
    python3 examples/start_preset_game.py --deck0 hitmonchan-dewgong --deck1 venusaur-parasect --seed 1 --first 0
    python3 examples/start_preset_game.py --deck0 hitmonchan-dewgong-v2 --deck1 venusaur-parasect-v2 --seed 1 --first 0   # 第2版（v0.26）

既定のデッキは第1版（``hitmonchan-dewgong``・``venusaur-parasect``）のままです。知らない識別子は引数の誤りとして拒否します（v0.26）。

``--first`` はジャンケンの勝者（先攻）。エンジンはジャンケンを決めないので、外から渡します。対戦準備で場に出すポケモンは、この例では
「手札のたねポケモンの最初の 1 匹をバトル場、残りを 5 匹までベンチ」に決めています（ルールの決まりではなく、この例の決め方）。切り直しの
あとの「引く」は、引ける枚数をすべて引きます。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kyuura_engine import (  # noqa: E402
    DrawMulliganCards, Phase, PlaceStartingPokemon, ReportJankenResult, apply_command, new_game, preset_deck, preset_deck_ids, validate_deck,
)


def start(deck0: str, deck1: str, seed: int, first: int):
    """2 つのデッキを検査し、対戦を始めて、先攻の最初の番（番の最初の 1 枚を引いたあと）の状態を返す。"""
    decks = [preset_deck(deck0).cards(), preset_deck(deck1).cards()]
    for cards in decks:
        validate_deck(cards)
    state = new_game(decks[0], decks[1], seed=seed)
    while state.phase is not Phase.MAIN:
        if state.phase is Phase.SETUP_PLACEMENT:
            player = 0 if not state.players[0].placed_starting_pokemon else 1
            basics = [u for u in state.players[player].hand if state.card_def(u).is_basic_pokemon]
            state = apply_command(state, PlaceStartingPokemon(player, basics[0], tuple(basics[1:6])))
        elif state.phase is Phase.SETUP_MULLIGAN_DRAW:
            player = 0 if state.players[0].mulligan_draws_remaining else 1
            count = min(state.players[player].mulligan_draws_remaining, len(state.players[player].deck))
            state = apply_command(state, DrawMulliganCards(player, count))
        elif state.phase is Phase.SETUP_FIRST_PLAYER:
            state = apply_command(state, ReportJankenResult(first))
        else:
            raise RuntimeError(f"この例が扱わない段階 {state.phase}")
    return state


def describe(state, deck_ids) -> str:
    lines = [f"seed={state.seed} 段階={state.phase.value} 番={state.turn_number} 番のプレイヤー={state.current_player}"]
    for index, p in enumerate(state.players):
        name = preset_deck(deck_ids[index]).name_ja
        active = state.card_def(p.active.card).name_ja
        bench = "・".join(state.card_def(b.card).name_ja for b in p.bench) or "なし"
        lines.append(f"プレイヤー {index}（{name}）: バトル場 {active}／ベンチ {bench}／手札 {len(p.hand)} 枚／山札 {len(p.deck)} 枚／サイド {len(p.prizes)} 枚")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="固定のデッキを選んで対戦を始める（開始だけの例）")
    parser.add_argument("--list", action="store_true", help="選べるデッキを表示する")
    parser.add_argument("--deck0", choices=preset_deck_ids(), default="hitmonchan-dewgong", help="プレイヤー 0 のデッキ（--list の識別子）")
    parser.add_argument("--deck1", choices=preset_deck_ids(), default="venusaur-parasect", help="プレイヤー 1 のデッキ（--list の識別子）")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--first", type=int, choices=(0, 1), default=0, help="ジャンケンの勝者（先攻）")
    args = parser.parse_args(argv)
    if args.list:
        for deck_id in preset_deck_ids():
            deck = preset_deck(deck_id)
            print(f"{deck_id}: {deck.name_ja}（{sum(n for _, n in deck.entries)} 枚）")
        return 0
    state = start(args.deck0, args.deck1, args.seed, args.first)
    print(describe(state, (args.deck0, args.deck1)))
    print("ここから先は apply_command にコマンドを渡して進めます（この例は対戦の開始だけ）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
