"""ワザの宣言の前の先読み（docs/event-model-v0.14.md 7 章・docs/preflight-optimization-v0.15c.md）。

先読みは、原典で決められない場合（``questions.QUESTIONS``）に、コインの結果やワザの途中の決定の選び方によって当たるワザを、宣言の前に
止めるためのものです（受け付けるかがコインの結果で変わらない）。方法（``PREFLIGHT_MODES``。コマンドを処理する経路とは別のもの）:

- ``derived``（既定）: 仕組みの共通の検出が、コイン（こんらんのコイン・ワザのコイン・「とうめい」のコイン）のすべての結果と、ワザの途中の
  決定のすべての答えのどれかで当たるかを確かめる。v0.15c から、実際の処理を先に行い（乱数はそのまま使う。宣言からきぜつの判定まで
  （先読みの範囲）に使ったコインを記録する）、まだ試していない結果だけを状態の複製の上で試す（``after_real_run``。docs 2 章）。どれかの
  結果で当たれば止める（実際の処理の結果は捨てる）。
- ``derived_full``: v0.14 の方法（``derived``）。実際の処理の前に、すべての結果を状態の複製の上で試す。``derived`` と比べるための基準。
- ``legacy``: v0.13 の止める関数を、v0.13 の ``engine._use_attack`` と同じ順番でそのまま呼ぶ（比べるため。v0.16c から
  ``v013_checks.check``）。

状態の複製の上で試すときは乱数を使いません（複製の乱数を ``Oracle`` に差しかえる）。渡した状態は変えません。1 回の先読みで試す結果の数は
``MAX_BRANCHES`` までです。超えたら途中までの結果を使わず（「当たる問いがない」証拠にも、問いを選ぶ材料にもしない）、v0.13 の止める関数で
確かめたワザの実装（``v013_checks.VERIFIED``）なら v0.13 の止める関数で確かめ、ほかは拒否します（``UNSUPPORTED_PREFLIGHT_LIMIT``。
``flow._use_attack`` の ``on_limit``）。v0.13 の止める関数（``v013_checks``）は、この先読みとは別の、限定的な互換の判定です（v0.16c。
docs/preflight-consolidation-v0.16c.md）。この部品は v0.13 の止める関数を使いません。

v0.35: 結果を「おもて」の数だけで使うコイン（``coins.flip_coins`` の ``by_heads``。たまなげMAX・ウォーターパンチ・ぜんりょくとっしんなど）は、
台本の 1 つの値で「おもて」の数（0〜枚数）を選ぶ（``Oracle.coin_group``）。コインの並び（2 の枚数乗）ではなく、枚数 + 1 通りを試す。同じ
「おもて」の数の並びは、そのあとの処理（ダメージ・自分へのダメージ・トラッシュの枚数・問い）が同じになる（まとめてよいのは、結果の使い道が
「おもて」の数だけのコインだけ。どのコインかは要素が決める。docs/coin-groups-damage-order-v0.35.md 2 章）。コインのあとの決定（トラッシュする
カードなど）は今までどおりすべての答えを試す（まとめない）。``derived`` の実際の処理は 1 枚ずつ投げ、記録する乱数（``RecordingRandom``）が
「おもて」の数を 1 つの値として記録する（試していない結果の台本は、値ごとに選べる数（``arity``）を持つ）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from .events import PreflightResult, Trace
from .kernel import DryRunComplete, Resolution
from .questions import OpenQuestion, pick, to_error

if TYPE_CHECKING:
    from ..state import GameState

    from .catalog import Catalog

PREFLIGHT_MODES = ("derived", "legacy", "derived_full")
MAX_BRANCHES = 4096  # 1 回の先読みで試す結果の数の上限（docs/preflight-optimization-v0.15c.md 4 章）

class NeedToken(Exception):
    """先読みの台本が足りない（ここで ``n`` 通りに分かれる）。"""

    def __init__(self, n: int):
        super().__init__(n)
        self.n = n


class BranchLimit(Exception):
    """試す結果の数が ``MAX_BRANCHES`` を超えた（途中までの結果は使わない）。"""


class Oracle:
    """先読みの乱数（コイン 1 枚 = 1 つの値）と選択。台本の値を順に使い、足りなければ ``NeedToken`` で分かれる。

    v0.35: 結果を「おもて」の数だけで使う 2 枚以上のコイン（``coin_group``）は、1 つの値で「おもて」の数を選ぶ（``group`` が False なら、
    今までどおり 1 枚ずつ。まとめた先読みと、まとめない先読みを比べるテストのため）。"""

    def __init__(self, script: tuple[int, ...], group: bool = True):
        self.script = script
        self.used = 0
        self.group = group

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

    def coin_group(self, count: int) -> tuple[int, ...]:
        """結果を「おもて」の数だけで使う ``count`` 枚のコイン（v0.35。``coins.flip_coins`` の ``by_heads``）。台本の 1 つの値（0〜``count``）を
        「おもて」の数とし、決まった並び（「うら」の数だけ 0、そのあと「おもて」の数だけ 1）を返す。この並びは、同じ「おもて」の数の並びのうち、
        1 枚ずつ試す先読みで最初に試すもの（だから、当たる問いと理由の文が 1 枚ずつ試すときと同じになる）。"""
        if not self.group:
            return tuple(self._next(2) for _ in range(count))
        heads = self._next(count + 1)
        return (0,) * (count - heads) + (1,) * heads

    def choose(self, alternatives: list):
        if not alternatives:
            raise RuntimeError("先読みで選べるものがない決定（エンジンの不具合）")
        return alternatives[self._next(len(alternatives))]

    def __getattr__(self, name):
        raise RuntimeError(f"先読みの中で乱数の {name} を使った（エンジンの不具合）")


def explore(state: GameState, body: Callable[[Resolution], None], catalog: Catalog, *, roots: tuple[tuple[int, ...], ...] = ((),),
            limit: int = MAX_BRANCHES, group: bool = True) -> tuple[dict[str, OpenQuestion], int]:
    """``body``（宣言からきぜつの判定まで）を、``roots`` の台本から始まるコインと選択のすべての結果で試す（深さ優先。値の小さい台本から）。
    当たった問い（問いごとに最初に当たった結果のもの）と、試した結果の数を返す。結果の数が ``limit`` を超えたら ``BranchLimit``。
    ``group``（v0.35）: 結果を「おもて」の数だけで使うコインを「おもて」の数でまとめる（既定）。False は比べるテストだけが使う。"""
    found: dict[str, OpenQuestion] = {}
    branches = 0
    stack: list[tuple[int, ...]] = list(reversed(roots))
    while stack:
        script = stack.pop()
        sim = state.clone()
        oracle = Oracle(script, group)
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
        if branches > limit:
            raise BranchLimit(branches)
    return found, branches


def _raise_found(found: dict[str, OpenQuestion]) -> None:
    if found:
        key = pick(found)
        question = found[key]
        raise to_error(key, question.detail, question.error)


def derived(state: GameState, body: Callable[[Resolution], None], catalog: Catalog, trace: Trace) -> None:
    """v0.14 の方法（``derived_full``）: すべての結果を試してから、当たった問いのうち優先度のいちばん高いもので止める。上限を超えたら
    ``BranchLimit``（呼ぶ側が ``on_limit`` で扱う）。"""
    found, branches = explore(state, body, catalog)
    trace.record(PreflightResult("derived_full", branches, tuple(sorted(found)), "full"))
    _raise_found(found)


class RecordingRandom:
    """実際の処理の乱数の前に置き、先読みの範囲（宣言からきぜつの判定まで）に使ったコインを記録する。値・使う順番は元の乱数のまま
    （乱数の使い方を変えない）。範囲の中でコイン（``getrandbits(1)``）以外に乱数を使ったら ``opaque``。範囲の終わり（``stop``）で、状態の
    乱数を元の乱数にもどす（このあとの処理・書き出しは元の乱数だけを見る）。

    記録は台本の値（``tokens``。(値, 選べる数)）: コイン 1 枚は (0 か 1, 2)。v0.35 から、結果を「おもて」の数だけで使う 2 枚以上のコイン
    （``coin_group``）は、元の乱数で 1 枚ずつ投げて（乱数の使い方は変わらない）、(「おもて」の数, 枚数 + 1) を 1 つ記録する（``Oracle.coin_group``
    と同じ値の意味）。"""

    def __init__(self, state: GameState):
        self._state = state
        self._rng = state.rng
        self.tokens: list[tuple[int, int]] = []
        self.opaque = False
        self.stopped = False

    def getrandbits(self, k: int) -> int:
        value = self._rng.getrandbits(k)
        if k == 1:
            self.tokens.append((value, 2))
        else:
            self.opaque = True
        return value

    def coin_group(self, count: int) -> tuple[int, ...]:
        bits = tuple(self._rng.getrandbits(1) for _ in range(count))
        self.tokens.append((sum(bits), count + 1))
        return bits

    def __getattr__(self, name):
        self.opaque = True
        return getattr(self._rng, name)

    def stop(self) -> None:
        self.stopped = True
        self.restore()

    def restore(self) -> None:
        self._state.rng = self._rng


def sibling_roots(tokens: tuple[tuple[int, int], ...]) -> tuple[tuple[int, ...], ...]:
    """実際の処理が通った台本の値 ``tokens``（(値, 選べる数)）以外のすべての結果を覆う台本（i 番目の値だけをほかの値にした台本の、それぞれの
    続きのすべて）。コイン 1 枚（選べる数 2）だけなら v0.34 までと同じ（i 枚目だけを逆にした並び）。"""
    values = tuple(value for value, _ in tokens)
    return tuple(values[:i] + (other,) for i, (value, arity) in enumerate(tokens) for other in range(arity) if other != value)


def after_real_run(state: GameState, original: GameState, body: Callable[[Resolution], None], catalog: Catalog, trace: Trace,
                   on_limit: Callable[[], None]) -> None:
    """``derived``（v0.15c）: 実際の処理を ``state`` の上で先に行い、まだ試していない結果だけを ``original``（コマンドの入口に渡された、
    変えていない状態）の複製の上で試す。どれかの結果で問いに当たれば、``derived_full`` と同じ問い・同じ理由の文で止める。

    1. 実際の処理（記録する乱数で）。例外も捕まえておく（``derived_full`` では先読みが先なので、先読みの答えが優先する）。
    2. 試す範囲を決める（docs/preflight-optimization-v0.15c.md 2 章）:
       - ``single``: 先読みの範囲で、コインを投げず・決定を出さず・コイン以外の乱数を使わず・例外もなかった → 結果は実際の処理の 1 つだけ
         （試さない）
       - ``siblings``: コインを投げたが、決定・コイン以外の乱数・例外はなかった → 実際の処理のコインの並び以外の結果を試す
       - ``full``: 先読みの範囲で決定を出した・コイン以外の乱数を使った・例外が起きた → すべての結果を試す（``derived_full`` と同じ）
    3. ``siblings`` で問いに当たったら、問いの選び方と理由の文の値を ``derived_full`` と同じにするため、すべての結果を試し直す。
    """
    recorder = RecordingRandom(state)
    state.rng = recorder
    error: BaseException | None = None
    try:
        body(Resolution(state, catalog=catalog, trace=trace, on_horizon=recorder.stop))
    except Exception as caught:  # noqa: BLE001 — 先読みの答えを優先するため、いったん捕まえる（あとで投げ直す）
        error = caught
    finally:
        recorder.restore()
    before_horizon = not recorder.stopped
    if recorder.opaque or before_horizon:
        strategy, roots = "full", ((),)
    elif recorder.tokens:
        strategy, roots = "siblings", sibling_roots(tuple(recorder.tokens))
    else:
        strategy, roots = "single", ()
    found: dict[str, OpenQuestion] = {}
    branches = 0
    # 上限は derived_full と同じ「試す結果の数（葉の数）」: siblings は実際の処理の結果も 1 つと数える（v0.16c。v0.15c では数えず、
    # ちょうど 4,097 通りのコインだけの木を、derived_full が拒否するのに受け付けていた。docs/preflight-consolidation-v0.16c.md 4 章）
    limit = MAX_BRANCHES - (1 if strategy == "siblings" else 0)
    try:
        if roots:
            found, branches = explore(original, body, catalog, roots=roots, limit=limit)
        if found and strategy == "siblings":
            strategy = "siblings+full"
            found, branches = explore(original, body, catalog)
    except BranchLimit:
        trace.record(PreflightResult("derived", MAX_BRANCHES, (), "limit"))
        on_limit()
        if error is not None:
            raise error
        return
    trace.record(PreflightResult("derived", branches + (0 if strategy in ("full", "siblings+full") else 1), tuple(sorted(found)), strategy))
    _raise_found(found)
    if error is not None:
        raise error
