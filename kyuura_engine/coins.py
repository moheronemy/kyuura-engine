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

v0.35: 結果の使い道が「おもて」の数だけのコイン（``by_heads``。「おもて」の数 × のダメージ・ついているエネルギーの数だけ投げるコインなど）は、
宣言の前の先読み（``resolution.preflight``）が、コインの並びではなく「おもて」の数でまとめて試せる（docs/coin-groups-damage-order-v0.35.md）。
実際の対戦では今までどおり 1 枚ずつ投げる（乱数の使い方・ログ・確からしさは変わらない）。まとめるのは、状態の乱数が ``coin_group`` を持つとき
（先読みの乱数と、先読みの範囲を記録する乱数）だけで、ふつうの ``random.Random`` は持たない。

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
    by_heads: bool = False,
) -> CoinFlips:
    """コインを ``count`` 枚、1 枚ずつ投げて、結果を返す。1 枚ごとに ``coin_flip`` をログに残す。

    - ``player``: コインを投げるプレイヤー（その効果を使っている側。ワザならワザを使うポケモン側）
    - ``source``: コインを投げる理由の種類（``"attack"``: ワザの説明。将来はトレーナー・特殊状態など）
    - ``effect``: 効果の識別子（ワザなら ``AttackKey`` の文字列 ``"PMCG1-061#0"``）
    - ``card``: 効果を持つカードの uid（ワザならワザを使うポケモンのカード）
    - ``pokemon_id``: 効果を持つ場のポケモンの番号（場のポケモンでなければ None）

    - ``by_heads``（v0.35）: 結果を「おもて」の数だけで使うコイン（投げた順番を使わない）。2 枚以上のとき、状態の乱数が ``coin_group`` を
      持てば（先読みの乱数・先読みの範囲を記録する乱数）、それに ``count`` 枚の結果を求める。先読みの乱数は「おもて」の数を 1 つの値で選び、
      決まった並び（「うら」→「おもて」の順）で返す。記録する乱数は、元の乱数で 1 枚ずつ投げた結果をそのまま返し、「おもて」の数を 1 つの
      値として記録する。どちらでも、ここで残すログ・返す結果の形は同じ。ふつうの乱数（``random.Random``）は ``coin_group`` を持たないので、
      実際の対戦では今までどおり 1 枚ずつ ``getrandbits(1)``

    枚数・プレイヤーが正しくなければ、乱数を使う前に ``ValueError``（効果の実装の誤り。プレイヤーの
    操作の誤りではない）。
    """
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError(f"投げるコインの枚数は 1 以上の整数（{count!r}）")
    if player not in (0, 1):
        raise ValueError(f"コインを投げるプレイヤーは 0 か 1（{player!r}）")
    group = getattr(type(state.rng), "coin_group", None) if by_heads and count > 1 else None
    bits = tuple(state.rng.coin_group(count)) if group is not None else None
    if bits is not None and (len(bits) != count or any(bit not in (0, 1) for bit in bits)):
        raise RuntimeError(f"まとめて投げたコインの結果 {bits!r} が {count} 枚の 0・1 ではない（エンジンの不具合）")
    results = []
    for number in range(1, count + 1):
        bit = bits[number - 1] if bits is not None else state.rng.getrandbits(1)
        side = CoinSide.HEADS if bit else CoinSide.TAILS
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


def flip_until_tails(
    state: GameState,
    player: int,
    *,
    source: str,
    effect: str,
    card: int,
    pokemon_id: int | None = None,
    classes=None,
) -> CoinFlips:
    """「うら」が出るまでコインを 1 枚ずつ投げ続けて、結果（最後の 1 枚が「うら」）を返す（v0.64。化石の秘密のイシツブテの「れんぞくいしなげ」。
    docs/geodude-line-unbounded-coins-v0.64.md 2 章）。

    - 実際の対戦（ふつうの乱数）: 1 枚 1 回 ``getrandbits(1)`` を、「うら」（0）が出るまで続ける（枚数・「おもて」の数に上限はない。決まった枚数で
      打ち切らない。分布が同じ別の乱数の使い方にしない）
    - 先読みの乱数（``coin_run`` を持つ。``preflight.Oracle``）: ``classes()``（``resolution.unbounded.HeadClasses``）の代表の「おもて」の数の
      どれかを 1 つの値で選び、「おもて」をその数だけ並べたあとに「うら」を 1 枚（その代表の並び）。代表は先読みの複製の上だけで使う
    - 先読みの範囲を記録する乱数（``record_run`` を持つ。``preflight.RecordingRandom``）: 元の乱数で 1 枚ずつ投げ、実際に出た「おもて」の数の組の位置を
      1 つの値として記録する（乱数の使い方は実際の対戦と同じ）
    - ログは 1 枚ごとの ``coin_flip``（``count`` は投げた枚数。``until`` は ``"tails"``）。投げ終えてからまとめて残す（投げている間にほかの処理はない）
    """
    if player not in (0, 1):
        raise ValueError(f"コインを投げるプレイヤーは 0 か 1（{player!r}）")
    rng = state.rng
    if getattr(type(rng), "coin_run", None) is not None:
        if classes is None:
            raise RuntimeError("先読みで「うら」が出るまで投げるコインに、「おもて」の数の組がない（エンジンの不具合）")
        heads = rng.coin_run(classes)
        bits = (1,) * heads + (0,)
    elif getattr(type(rng), "record_run", None) is not None:
        bits = tuple(rng.record_run(classes))
    else:
        found = []
        while True:
            bit = rng.getrandbits(1)
            found.append(bit)
            if not bit:
                break
        bits = tuple(found)
    if not bits or bits[-1] != 0 or any(bit != 1 for bit in bits[:-1]):
        raise RuntimeError(f"「うら」が出るまで投げたコインの結果 {bits!r} が、「おもて」の並びのあとに「うら」1 枚ではない（エンジンの不具合）")
    results = []
    for number, bit in enumerate(bits, start=1):
        side = CoinSide.HEADS if bit else CoinSide.TAILS
        results.append(side)
        state.add_event("coin_flip", player=player, source=source, effect=effect, card=card, pokemon_id=pokemon_id, number=number, count=len(bits),
                        result=side.value, until="tails")
    return CoinFlips(tuple(results))
