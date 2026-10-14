"""ワザの宣言の前の先読み（docs/event-model-v0.14.md 7 章）。

- ``derived``（既定）: 状態の複製の上で、コイン（こんらんのコイン・ワザのコイン・「とうめい」のコイン）のすべての結果と、ワザの途中の
  決定の選び方を順に試し、仕組みの共通の検出が既知の問い（``questions.QUESTIONS``）に当たるかを集める。どれかの結果で当たれば、
  宣言の前に止める（受け付けるかがコインの結果で変わらない）。v0.13 の止める関数（5 つ）と、ワザの実装の補助の情報
  （``damage_profile``・``opponent_effect_elements``）は使わない。
- ``legacy``: v0.13 の止める関数を、v0.13 の ``engine._use_attack`` と同じ順番でそのまま呼ぶ（比べるため）。

先読みは乱数を使いません（複製の乱数を ``Oracle`` に差しかえる）。渡した状態は変えません。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ..procedures import confusion_damage_problem
from ..effects import (
    AttackUse,
    counterattack_double_knockout_problem,
    ko_prevention_attack_effect_problem,
    retaliation_double_knockout_problem,
)

from .events import PreflightResult, Trace
from .kernel import DryRunComplete, Resolution
from .questions import OpenQuestion, pick, to_error

if TYPE_CHECKING:
    from ..errors import UnsupportedError
    from ..state import GameState

    from .catalog import Catalog


class NeedToken(Exception):
    """先読みの台本が足りない（ここで ``n`` 通りに分かれる）。"""

    def __init__(self, n: int):
        super().__init__(n)
        self.n = n


class Oracle:
    """先読みの乱数（コイン 1 枚 = 1 つの値）と選択。台本の値を順に使い、足りなければ ``NeedToken`` で分かれる。"""

    def __init__(self, script: tuple[int, ...]):
        self.script = script
        self.used = 0

    def _next(self, n: int) -> int:
        if self.used < len(self.script):
            value = self.script[self.used]
            self.used += 1
            return value
        raise NeedToken(n)

    def getrandbits(self, k: int) -> int:
        if k != 1:
            raise RuntimeError(f"先読みの中でコイン以外の乱数（getrandbits({k})）を使った（エンジンの不具合）")
        return self._next(2)

    def choose(self, alternatives: list):
        if not alternatives:
            raise RuntimeError("先読みで選べるものがない決定（エンジンの不具合）")
        return alternatives[self._next(len(alternatives))]

    def __getattr__(self, name):
        raise RuntimeError(f"先読みの中で乱数の {name} を使った（エンジンの不具合）")


def explore(state: GameState, body: Callable[[Resolution], None], catalog: Catalog) -> tuple[dict[str, OpenQuestion], int]:
    """``body``（宣言からきぜつの判定まで）を、コインと選択のすべての結果で試す。当たった問いと、試した結果の数を返す。"""
    found: dict[str, OpenQuestion] = {}
    branches = 0
    stack: list[tuple[int, ...]] = [()]
    while stack:
        script = stack.pop()
        sim = state.clone()
        oracle = Oracle(script)
        sim.rng = oracle
        res = Resolution(sim, catalog=catalog, trace=Trace(), dry_run=True, oracle=oracle)
        try:
            body(res)
            branches += 1
        except DryRunComplete:
            branches += 1
        except NeedToken as need:
            stack.extend(script + (token,) for token in reversed(range(need.n)))
        except OpenQuestion as question:
            found.setdefault(question.key, question)
            branches += 1
    return found, branches


def derived(state: GameState, body: Callable[[Resolution], None], catalog: Catalog, trace: Trace) -> None:
    found, branches = explore(state, body, catalog)
    trace.record(PreflightResult("derived", branches, tuple(sorted(found))))
    if found:
        key = pick(found)
        question = found[key]
        raise to_error(key, question.detail, question.error)


def legacy(state: GameState, use: AttackUse, effect, attacker, trace: Trace) -> None:
    """v0.13 の ``engine._use_attack`` の確認（engine.py:881-891）を、同じ順番でそのまま呼ぶ。"""
    problem: UnsupportedError | None = effect.problem(state, use)
    if problem is None and attacker.conditions.confused:
        problem = confusion_damage_problem(state, attacker)
    if problem is None:
        problem = counterattack_double_knockout_problem(state, use, effect)
    if problem is None:
        problem = ko_prevention_attack_effect_problem(state, use, effect)
    if problem is None:
        problem = retaliation_double_knockout_problem(state, use, effect)
    trace.record(PreflightResult("legacy", 0, () if problem is None else (problem.code,)))
    if problem is not None:
        raise problem
