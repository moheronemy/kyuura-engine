"""大規模なストレス実行（v0.4e のテストの段階 C。docs/integration-audit-v0.4e.md 10 章）。ふだんの単体テストでは走らせない。

使い方（リポジトリの直下で）::

    python3 tools/stress_engine.py                         # すべての組 × 40 seed × 600 手
    python3 tools/stress_engine.py --seeds 200 --steps 800 --report stress.json
    python3 tools/stress_engine.py --scenario butterfree --start 1000 --seeds 50

- 今の作業ツリーのエンジンを、tools/compat_driver.py の組（デッキ）と駆動（ルール上できそうな操作と、わざと不正な操作を混ぜる。
  ``--illegal-rate`` で割合を変える）で動かす。
- 1 手ごとに: 受け付けたら、返った状態は ``apply_command`` が不変条件で確かめている。拒否したら、渡した状態・乱数・ログが
  変わっていないことを確かめる。書き出しの監査（tests/log_audit.py の ``serialization_problems``）は ``--serialize-every`` 手ごと。
  対戦の終わりに、ログと状態の整合（``log_problems``）を確かめる。
- 結果を分類して数える: 受け付けた操作・ルール上できない操作（``IllegalActionError``）・未対応の操作（``UNSUPPORTED_…``）・原典で
  決められない裁定（``UNRESOLVED_…``。拒否）・止めた対戦（``HALTED``）・勝敗（``GAME_OVER``）・サドン・デス・内部の誤り。
  拒否と HALTED は別に数える。
- 問題（内部の誤り・壊れた状態・拒否で変わった状態・ログや書き出しの問題）のあった seed を ``--report`` に書く。終了コード 1。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import time
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import kyuura_engine as engine  # noqa: E402
from kyuura_engine.rng import rng_fingerprint  # noqa: E402

from tests.log_audit import log_problems, serialization_problems  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
import compat_driver as driver  # noqa: E402


def classify(error: Exception) -> str:
    if isinstance(error, engine.StateIntegrityError):
        return "internal_state_integrity"
    if isinstance(error, engine.UnsupportedError):
        if error.code.startswith("UNRESOLVED_"):
            return "rejected_unresolved"
        return "rejected_unsupported"
    if isinstance(error, engine.IllegalActionError):
        return "rejected_illegal"
    return "internal_error"


def run_game(scenario, seed: int, *, steps: int, illegal_rate: float, serialize_every: int) -> tuple[Counter, list[str]]:
    """1 局を進め、数えた結果と問題を返す。"""
    counted, problems = Counter(), []
    rng = random.Random(f"kyuura-stress:{scenario.name}:{seed}")
    state = engine.new_game(driver._deck(scenario.deck0), driver._deck(scenario.deck1), seed)
    for index in range(steps):
        if state.phase in engine.TERMINAL_PHASES:
            break
        command = driver.choose_command(engine, state, rng, illegal_rate)
        before = engine.state_to_dict(state, format_version=8)
        fingerprint, log = rng_fingerprint(state.rng), state.log
        try:
            new = engine.apply_command(state, command)
        except engine.EngineError as error:
            category = classify(error)
            counted[category] += 1
            counted[f"code:{error.code}"] += 1
            if category.startswith("internal"):
                problems.append(f"{index} 手目 {engine.command_to_dict(command)}: {error}")
                break
            if engine.state_to_dict(state, format_version=8) != before or rng_fingerprint(state.rng) != fingerprint or state.log is not log:
                problems.append(f"{index} 手目 {engine.command_to_dict(command)}: 拒否（{error.code}）で渡した状態が変わった")
            continue
        except Exception as error:  # noqa: BLE001  内部の誤り
            counted["internal_error"] += 1
            problems.append(f"{index} 手目 {engine.command_to_dict(command)}: {type(error).__name__}: {error}")
            break
        counted["accepted"] += 1
        counted[f"accepted:{type(command).__name__}"] += 1
        if new.phase is engine.Phase.HALTED and state.phase is not engine.Phase.HALTED:
            counted[f"halted:{new.halt.code}"] += 1
        if serialize_every and index % serialize_every == 0:
            counted["serialization_audits"] += 1
            problems.extend(f"{index} 手目のあと: {p}" for p in serialization_problems(new))
        state = new
    counted[f"final:{state.phase.value}"] += 1
    if state.phase is engine.Phase.HALTED:
        counted[f"final_halted:{state.halt.code}"] += 1
    problems.extend(f"対戦の終わり: {p}" for p in log_problems(state))
    problems.extend(f"対戦の終わり: {p}" for p in engine.check_invariants(state))
    return counted, problems


def run(scenarios, seeds, *, steps: int, illegal_rate: float, serialize_every: int) -> dict:
    total, failures = Counter(), []
    for scenario in scenarios:
        for seed in seeds:
            counted, problems = run_game(scenario, seed, steps=steps, illegal_rate=illegal_rate, serialize_every=serialize_every)
            total.update(counted)
            total["games"] += 1
            if problems:
                failures.append({"scenario": scenario.name, "seed": seed, "problems": problems[:20]})
    return {"counts": dict(sorted(total.items())), "failures": failures}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="大規模なストレス実行（ふだんの単体テストでは走らせない）")
    parser.add_argument("--scenario", action="append", help="組（tools/compat_driver.py の SCENARIOS。省略ですべて）")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--seeds", type=int, default=40)
    parser.add_argument("--steps", type=int, default=600)
    parser.add_argument("--illegal-rate", type=float, default=0.25)
    parser.add_argument("--serialize-every", type=int, default=25, help="書き出しの監査をする間隔（0 でしない）")
    parser.add_argument("--report", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    scenarios = [s for s in driver.SCENARIOS if not args.scenario or s.name in args.scenario]
    started = time.time()
    result = run(scenarios, range(args.start, args.start + args.seeds), steps=args.steps, illegal_rate=args.illegal_rate,
                 serialize_every=args.serialize_every)
    result["seconds"] = round(time.time() - started, 1)
    result["arguments"] = vars(args) | {"report": str(args.report) if args.report else None}
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    counts = result["counts"]
    print(f"対戦 {counts.get('games', 0)}・受け付けた {counts.get('accepted', 0)}・できない {counts.get('rejected_illegal', 0)}・"
          f"未対応 {counts.get('rejected_unsupported', 0)}・原典で決められない（拒否） {counts.get('rejected_unresolved', 0)}・"
          f"HALTED {sum(v for k, v in counts.items() if k.startswith('final_halted:'))}・GAME_OVER {counts.get('final:game_over', 0)}・"
          f"SUDDEN_DEATH {counts.get('final:sudden_death', 0)}・内部の誤り {counts.get('internal_error', 0) + counts.get('internal_state_integrity', 0)}"
          f"（{result['seconds']} 秒）")
    for failure in result["failures"]:
        print(f"- {failure['scenario']} seed {failure['seed']}: {failure['problems'][0]}")
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
