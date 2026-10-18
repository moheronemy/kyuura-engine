"""場に出ているスタジアムカードの問い合わせ（v0.57。docs/stadiums-v0.57.md 2 章）。

場のスタジアムは状態の ``GameState.stadium``（実際のカード 1 枚）だけに持ち、効果は問い合わせのたびに、効果の登録表のそのカードの実装から求める（効果の結果を
状態・カードの定義・共有するルールの値に写さない。スタジアムが場をはなれたら、効果も問い合わせから消える）。このモジュールは状態だけを読み込み、効果の実装の型を
読まない（ゾーンの処理・エンジン・効果の実装のどこからでも読める。型ごとの問い合わせは ``effects.py``）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .state import GameState, StadiumInPlay


def stadium_in_play(state: GameState) -> tuple[StadiumInPlay, Any] | None:
    """場のスタジアム (``StadiumInPlay``, 効果の登録表の実装)。なければ None。場のスタジアムの実装が登録されていなければエンジンの不具合（不変条件で拒否する）。"""
    stadium = state.stadium
    if stadium is None:
        return None
    entry = state.effects.trainer_entry(state.cards[stadium.card].card_id)
    if entry is None or not entry.effect.is_stadium:
        raise RuntimeError(f"場のスタジアム {stadium} の実装が登録されていない（エンジンの不具合）")
    return stadium, entry.effect


def bench_limit(state: GameState, player: int) -> int:
    """プレイヤー ``player`` のベンチに出しておける控えポケモンの数（v0.57）。共通のルールの値（``rules.max_bench``。5 匹。p.308・p.312）に、場のスタジアムの
    「ベンチに出しておける控えポケモンの数」（せまいジムの「4匹まで」。実装の ``bench_limit``）を当てはめた数。共有するルールの値（``RuleSet``）は変えない。
    ベンチに出すどの経路（手札から・山札から・トラッシュから・効果で出させる・ポケモンとして出すトレーナー）も、ベンチに空きがあるかをこれで確かめる。"""
    limit = state.rules.max_bench
    found = stadium_in_play(state)
    if found is not None and found[1].bench_limit is not None:
        limit = min(limit, found[1].bench_limit)
    return limit


def bench_has_room(state: GameState, player: int, count: int = 1) -> bool:
    """プレイヤー ``player`` のベンチに、あと ``count`` 匹出せるか（``bench_limit``）。"""
    return len(state.players[player].bench) + count <= bench_limit(state, player)
