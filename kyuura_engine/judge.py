"""勝ち負けの判定（『オフィシャルブック2000』p.311「勝ち負けが決まるとき」の表、p.324 サドン・デス）。

表は、2 人のプレイヤーが同時に満たした勝利条件を並べて、条件の数が多いほうを勝ち、
同じならサドン・デスとしています。ここでは、各プレイヤーについて

- 自分がサイドカードをすべて取った
- 相手がバトル場にポケモンを出せない

の数を数えて比べます（表の 9 行はすべてこの数え方と一致する。tests/test_judge.py）。

「番の最初に山札がない」は番の最初の 1 枚を引くときにだけ起こるので、この表とは別に
``engine`` がその場で負けにします（p.309, p.311）。
"""

from __future__ import annotations

from typing import Sequence

from .state import GameResult

ALL_PRIZES_TAKEN = "ALL_PRIZES_TAKEN"
OPPONENT_CANNOT_FIELD_ACTIVE = "OPPONENT_CANNOT_FIELD_ACTIVE"
OPPONENT_DECK_EMPTY = "OPPONENT_DECK_EMPTY"


def decide(all_prizes_taken: Sequence[bool], cannot_field_active: Sequence[bool]) -> GameResult | None:
    """同時に満たした勝利条件から結果を決める。どちらも満たしていなければ None。

    all_prizes_taken[p]: プレイヤー p がサイドをすべて取り終えた
    cannot_field_active[p]: プレイヤー p がバトル場にポケモンを出せない
    """
    conditions: list[tuple[int, str]] = []
    for player in (0, 1):
        if all_prizes_taken[player]:
            conditions.append((player, ALL_PRIZES_TAKEN))
        if cannot_field_active[1 - player]:
            conditions.append((player, OPPONENT_CANNOT_FIELD_ACTIVE))
    if not conditions:
        return None
    score = [sum(1 for p, _ in conditions if p == player) for player in (0, 1)]
    if score[0] == score[1]:
        return GameResult(outcome="sudden_death", winner=None, conditions=tuple(conditions))
    winner = 0 if score[0] > score[1] else 1
    return GameResult(outcome="win", winner=winner, conditions=tuple(conditions))


def deck_out(loser: int) -> GameResult:
    """番の最初に山札から引けなかったプレイヤーの負け（p.309, p.311, p.312）。"""
    winner = 1 - loser
    return GameResult(outcome="win", winner=winner, conditions=((winner, OPPONENT_DECK_EMPTY),))
