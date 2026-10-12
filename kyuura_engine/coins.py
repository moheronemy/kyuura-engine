"""コイントス（v0.2d。『ポケモンカードオフィシャルブック2000』p.319「5 コイントス」）。

公式ルールの記述（p.319）:

- ワザなどを使うとき、コインを投げて「おもて」か「うら」かを判定するときがある。これを「コイントス」と呼ぶ。
- コインは何でもかまわない（スターターパックのコインでも 10 円玉でも）。
- 両方のプレイヤーに見えないところに落ちたら、投げなおす（実物のコインの話。エンジンのコインは必ず
  どちらかに決まり、両方のプレイヤーに見えるので、投げなおしは起こらない）。

エンジンでの扱い:

- 結果は対戦の乱数 ``GameState.rng`` だけで決める（``seed`` から作る。モジュールの ``random`` は使わない）。
  コイン 1 枚につき ``rng.getrandbits(1)`` を 1 回。1 なら「おもて」、0 なら「うら」（同じ確からしさ）。
- 「コインを 2 枚投げ」は、1 枚ずつ 2 回投げることとして、投げた順に乱数を使う。結果の数え方（「おもて」の数）は
  順番によらない。
- プレイヤーが結果を選ぶコマンドはない。結果を外から渡す API もない（テストで結果を決めたいときは、
  テストの中で ``GameState.rng`` を差し替える。tests/helpers.py の ``with_coin_results``）。
- 1 枚ごとに ``coin_flip`` のイベントをログに残す（誰の・どの効果の・何枚目の・結果）。コインの結果は
  両方のプレイヤーが見るので、隠す情報はない。

コインを投げる効果は、投げる前に、使えるかどうか・原典で決められない場合を確かめ終えておくこと
（不正な操作で乱数を進めないため）。``apply_command`` は複製した状態で処理するので、途中で例外に
なっても、渡した状態の乱数は進まない。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import GameState


class CoinSide(str, Enum):
    HEADS = "heads"  # おもて
    TAILS = "tails"  # うら


@dataclass(frozen=True)
class CoinFlips:
    """何枚かのコインを投げた結果（投げた順）。"""

    results: tuple[CoinSide, ...]

    @property
    def heads(self) -> int:
        """「おもて」の数。"""
        return sum(1 for side in self.results if side is CoinSide.HEADS)

    @property
    def tails(self) -> int:
        """「うら」の数。"""
        return sum(1 for side in self.results if side is CoinSide.TAILS)


def flip_coins(
    state: GameState,
    player: int,
    count: int,
    *,
    source: str,
    effect: str,
    card: int,
    pokemon_id: int | None = None,
) -> CoinFlips:
    """コインを ``count`` 枚、1 枚ずつ投げて、結果を返す。1 枚ごとに ``coin_flip`` をログに残す。

    - ``player``: コインを投げるプレイヤー（その効果を使っている側。ワザならワザを使うポケモン側）
    - ``source``: コインを投げる理由の種類（``"attack"``: ワザの説明。将来はトレーナー・特殊状態など）
    - ``effect``: 効果の識別子（ワザなら ``AttackKey`` の文字列 ``"PMCG1-061#0"``）
    - ``card``: 効果を持つカードの uid（ワザならワザを使うポケモンのカード）
    - ``pokemon_id``: 効果を持つ場のポケモンの番号（場のポケモンでなければ None）

    枚数・プレイヤーが正しくなければ、乱数を使う前に ``ValueError``（効果の実装の誤り。プレイヤーの
    操作の誤りではない）。
    """
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError(f"投げるコインの枚数は 1 以上の整数（{count!r}）")
    if player not in (0, 1):
        raise ValueError(f"コインを投げるプレイヤーは 0 か 1（{player!r}）")
    results = []
    for number in range(1, count + 1):
        side = CoinSide.HEADS if state.rng.getrandbits(1) else CoinSide.TAILS
        results.append(side)
        state.add_event(
            "coin_flip",
            player=player,
            source=source,
            effect=effect,
            card=card,
            pokemon_id=pokemon_id,
            number=number,  # 何枚目か（1 から）
            count=count,  # この効果で投げる枚数
            result=side.value,
        )
    return CoinFlips(tuple(results))
