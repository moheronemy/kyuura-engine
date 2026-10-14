"""v0.14: v0.13 の経路（``Route.LEGACY``）と解決の基盤（``Route.KERNEL``。v0.14 のプロトタイプ）を、同じ対戦の 1 歩ごとに比べる（C 段階の道具）。

ふだんのテスト（``python3 -m unittest``）では走らせません。B 段階の小さな比較は tests/test_event_kernel_games_v0_14.py です。

比べるもの（1 歩ごと）: 拒否するか・拒否の例外の種類とコード、受け付けたら状態（書き出しの形式 9。ログ・乱数の指紋・決定・
特殊状態・持続する効果を含む）。どちらの場合も渡した状態が変わらないこと。プロトタイプの先読みは ``--mode`` で選ぶ
（``derived``: 仕組みの共通の検出（v0.15c から、実際の処理を先に行い、試していない結果だけを試す）、``legacy``: v0.13 の止める関数、
``derived_full``: v0.14 の方法（すべての結果を先に試す。v0.15c）、``both``: ``derived`` と ``legacy``、``all``: 3 つすべて）。

対戦の作り方は 2 つ:

- ``stress``: tools/stress_engine.py の 26 組と ``choose_command``（拒否されるコマンドも混ぜる）。
- ``natural``: tests の対戦のテスト（23 個の ``play_game``）の方針。モジュールの ``apply_command`` を比べる関数に差しかえる。

``--mixed`` を付けると、次の歩の状態を、本番とプロトタイプの結果から交互に選ぶ（保存の形の互換性。どちらの状態からでも
続けられること）。``--timing`` は 1 歩の時間（プロトタイプが処理するコマンドだけ）を測る。

例::

    python3 tools/event_kernel_compare.py --stress-seeds 10 --natural-seeds 20 --mode both
    python3 tools/event_kernel_compare.py --corpus natural --modules test_moltres_games_v0_12 --natural-seeds 100
"""

from __future__ import annotations

import argparse
import importlib
import random
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for path in (ROOT, ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import kyuura_engine as engine  # noqa: E402
from kyuura_engine.rng import rng_fingerprint  # noqa: E402
from kyuura_engine.engine import Route, apply_command_via  # noqa: E402

from experiments import event_kernel as K  # noqa: E402
from experiments.event_kernel import events as EV  # noqa: E402

NATURAL_MODULES = (
    "test_alakazam_games_v0_7", "test_blastoise_games_v0_6", "test_bulbasaur_games_v0_5", "test_butterfree_games_v0_4d",
    "test_coin_games", "test_combined_games_v0_4e", "test_confusion_games", "test_dark_wartortle_games_v0_13",
    "test_defender_games", "test_evolution_games_v0_4a", "test_giovanni_games_v0_11", "test_harden_games_v0_4b",
    "test_haunter_games_v0_9", "test_machamp_games_v0_10", "test_moltres_games_v0_12", "test_muk_games_v0_8",
    "test_pikachu_games", "test_pluspower_games", "test_sleep_paralysis_games", "test_stage2_games_v0_4c",
    "test_status_games_v0_3d", "test_trainer_games", "test_weedle_games",
)
MODES = ("derived", "legacy", "derived_full")
GROUPS = {"both": ("derived", "legacy"), "all": MODES}


class Divergence(BaseException):
    """本番とプロトタイプの答えが違う（``BaseException`` なので、対戦のテストの ``except EngineError`` を通り抜ける）。"""


def full(state):
    return engine.state_to_dict(state, format_version=9)


def _legacy_apply(state, command):
    """比較の基準: v0.13 の経路（v0.15b から。標準の経路が KERNEL になっても、v0.13 の経路と比べる）。"""
    return apply_command_via(state, command, route=Route.LEGACY)


def _run(apply, state, command):
    try:
        return apply(state, command), None
    except engine.EngineError as error:
        return None, error


class Comparator:
    """1 歩を本番と、プロトタイプ（``modes`` の先読みそれぞれ）で処理して比べる。数を ``counts`` に足す。"""

    def __init__(self, modes=("derived",), *, mixed=False, timing=False, counts: Counter | None = None):
        self.modes = tuple(modes)
        self.mixed = mixed
        self.timing = timing
        self.counts = counts if counts is not None else Counter()
        self.time = Counter()
        self.step = 0

    def __call__(self, state, command):
        before, rng = full(state), rng_fingerprint(state.rng)
        owned = K.owned(state, command)
        t0 = time.perf_counter()
        expected, expected_error = _run(_legacy_apply, state, command)
        t1 = time.perf_counter()
        results = []
        for mode in self.modes:
            t2 = time.perf_counter()
            try:
                (actual, trace), error = K.apply_command_traced(state, command, preflight=mode), None
            except engine.EngineError as caught:
                actual, trace, error = None, None, caught
            t3 = time.perf_counter()
            if self.timing and owned:
                self.time[mode] += t3 - t2
            results.append((mode, actual, trace, error))
        if self.timing and owned:
            self.time["production"] += t1 - t0
            self.time["owned_steps"] += 1
        if (full(state), rng_fingerprint(state.rng)) != (before, rng):
            raise Divergence(f"渡した状態が変わった: {engine.command_to_dict(command)}")
        for mode, actual, trace, error in results:
            if (expected_error is None) != (error is None) or (
                    error is not None and (type(error), error.code, error.message) != (type(expected_error), expected_error.code, expected_error.message)):
                raise Divergence(f"[{mode}] {engine.command_to_dict(command)}: v0.13={expected_error!r} prototype={error!r}")
            if expected_error is None and full(actual) != full(expected):
                raise Divergence(f"[{mode}] {engine.command_to_dict(command)}: 状態が違う ({_first_difference(expected, actual)})")
        self.counts["steps"] += 1
        if owned:
            self.counts["owned"] += 1
            if expected_error is not None:
                self.counts[f"rejected:{expected_error.code}"] += 1
        for mode, _, mode_trace, _ in results:  # v0.15c: 先読みの試す範囲（docs/preflight-optimization-v0.15c.md）
            for event in () if mode_trace is None else mode_trace.of(EV.PreflightResult):
                self.counts[f"preflight:{mode}:{event.mode}:{event.strategy}"] += 1
                self.counts[f"preflight_branches:{mode}"] += event.branches
                self.counts[f"preflight_max_branches:{mode}"] = max(self.counts[f"preflight_max_branches:{mode}"], event.branches)
        trace = results[0][2]
        if trace is not None:
            for event in trace.events:
                if isinstance(event, EV.Activated):
                    self.counts[f"activated:{event.definition}"] += 1
                elif isinstance(event, EV.Suspended):
                    self.counts[f"suspended:{event.kind}"] += 1
                elif isinstance(event, EV.FrameOpened):
                    self.counts[f"frame:{event.frame.kind.value}"] += 1
                elif isinstance(event, EV.CandidateFound) and event.window in (EV.Window.KO_CHECK, EV.Window.KO_PROCESS):
                    self.counts[f"candidate:{event.window.value}:{event.definition}"] += 1
        if expected_error is not None:
            raise expected_error
        self.step += 1
        if self.mixed and self.step % 2:
            return results[0][1]  # プロトタイプの結果の状態から続ける
        return expected


def _first_difference(expected, actual):
    a, b = full(expected), full(actual)
    keys = [k for k in a if a.get(k) != b.get(k)]
    la, lb = expected.log, actual.log
    n = next((i for i in range(min(len(la), len(lb))) if dict(la[i]) != dict(lb[i])), min(len(la), len(lb)))
    return f"項目 {keys}; ログの最初の違い {n}: v0.13={dict(la[n]) if n < len(la) else None} prototype={dict(lb[n]) if n < len(lb) else None}"


def stress_game(comparator: Comparator, scenario, seed: int, *, steps: int = 600, illegal_rate: float = 0.05):
    """tools/stress_engine.py の組と選び方で 1 つの対戦を進める（拒否されたコマンドは状態を変えずに次へ）。"""
    import compat_driver as driver
    import stress_engine as stress
    rng = random.Random(f"kyuura-stress:{scenario.name}:{seed}")
    state = engine.new_game(driver._deck(scenario.deck0), driver._deck(scenario.deck1), seed)
    for _ in range(steps):
        if state.phase in engine.TERMINAL_PHASES:
            break
        command = stress.choose_command(state, rng, illegal_rate)
        try:
            state = comparator(state, command)
        except engine.EngineError:
            continue
    comparator.counts["games"] += 1
    return state


def natural_games(comparator: Comparator, module_name: str, seeds) -> None:
    """tests の対戦のテストの ``play_game`` を、モジュールの ``apply_command`` を差しかえて走らせる。"""
    module = importlib.import_module(f"tests.{module_name}")
    original = module.apply_command
    module.apply_command = comparator
    try:
        for seed in seeds:
            module.play_game(seed)
            comparator.counts["games"] += 1
    finally:
        module.apply_command = original


def main(argv=None) -> int:
    import stress_engine as stress
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", choices=("stress", "natural", "all"), default="all")
    parser.add_argument("--stress-seeds", type=int, default=10)
    parser.add_argument("--natural-seeds", type=int, default=20)
    parser.add_argument("--scenarios", default="", help="組の名前（, 区切り。既定はすべて）")
    parser.add_argument("--modules", default="", help="対戦のテストのモジュール（, 区切り。既定はすべて）")
    parser.add_argument("--mode", choices=(*MODES, *GROUPS), default="both")
    parser.add_argument("--mixed", action="store_true")
    parser.add_argument("--timing", action="store_true")
    args = parser.parse_args(argv)

    modes = GROUPS.get(args.mode, (args.mode,))
    counts: Counter = Counter()
    comparator = Comparator(modes, mixed=args.mixed, timing=args.timing, counts=counts)
    divergences = 0
    started = time.perf_counter()
    if args.corpus in ("stress", "all"):
        names = set(args.scenarios.split(",")) if args.scenarios else None
        for scenario in stress.ALL_SCENARIOS:
            if names is not None and scenario.name not in names:
                continue
            for seed in range(args.stress_seeds):
                try:
                    stress_game(comparator, scenario, seed)
                except Divergence as divergence:
                    divergences += 1
                    print(f"DIVERGENCE stress {scenario.name} seed={seed}: {divergence}")
                except Exception as error:
                    divergences += 1
                    print(f"ERROR stress {scenario.name} seed={seed}: {type(error).__name__}: {str(error)[:300]}")
    if args.corpus in ("natural", "all"):
        modules = args.modules.split(",") if args.modules else NATURAL_MODULES
        for name in modules:
            for seed in range(args.natural_seeds):
                try:
                    natural_games(comparator, name, [seed])
                except Divergence as divergence:
                    divergences += 1
                    print(f"DIVERGENCE natural {name} seed={seed}: {divergence}")
                except Exception as error:  # 対戦のテスト自身の確認（不変条件・監査）の失敗も数える
                    divergences += 1
                    print(f"ERROR natural {name} seed={seed}: {type(error).__name__}: {str(error)[:300]}")
    elapsed = time.perf_counter() - started
    for key in sorted(counts):
        print(f"{key}: {counts[key]}")
    if args.timing and comparator.time["owned_steps"]:
        n = comparator.time["owned_steps"]
        for key in ("production", *modes):
            print(f"time/{key}: {comparator.time[key] / n * 1000:.3f} ms per owned step ({n} steps)")
    print(f"modes={','.join(modes)} mixed={args.mixed} divergences={divergences} elapsed={elapsed:.1f}s")
    return 1 if divergences else 0


if __name__ == "__main__":
    raise SystemExit(main())
