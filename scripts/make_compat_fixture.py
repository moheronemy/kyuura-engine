#!/usr/bin/env python3
"""v0.1 の対戦結果の参照データ（互換性の確認用）を作る。

決まった入力（デッキ・seed・ジャンケンの結果・コマンドの列）について、各コマンドが受け付けられたか
（拒否されたならエラーコード）と、最後の状態（``state_to_dict``。イベントログを含む）を記録する。

``tests/test_compat_v0_1.py`` は、この記録を今のエンジンで再生し、同じ結果になることを確かめる。
記録は v0.1（コミット 6068785）で作った。エンジンを変えたあとにこのスクリプトを実行し直すと、
その時点の結果で上書きしてしまうので、互換性を確かめる目的では実行し直さないこと。

使い方::

    python3 scripts/make_compat_fixture.py   # tests/fixtures/v0_1_reference.json を書き出す
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kyuura_engine import EngineError, Phase, Retreat, apply_command, command_to_dict, new_game, state_to_dict  # noqa: E402
from kyuura_engine.commands import COMMAND_TYPES  # noqa: E402
from kyuura_engine.errors import StateIntegrityError  # noqa: E402
from tests.helpers import FEW_BASICS, FIRE_DECK, ONE_BASIC, WATER_FIGHTING_DECK, find_seed, scripted_command  # noqa: E402

OUTPUT = ROOT / "tests" / "fixtures" / "v0_1_reference.json"
END = (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED)


def random_command(rng: random.Random, state):
    """でたらめなコマンド（v0.1 にあるコマンドの種類だけ）。"""
    cls = rng.choice(list(COMMAND_TYPES.values()))
    uids = list(state.cards) + [-1, 10_000]
    values = {}
    for f in fields(cls):
        if f.type == "int":
            small = f.name in ("player", "winner", "count", "index", "attack_index")
            values[f.name] = rng.choice([-1, 0, 1, 2, 3] if small else uids)
        else:
            values[f.name] = tuple(rng.choice(uids) for _ in range(rng.randint(0, 3)))
    return cls(**values)


def retreating_command(state, **policy):
    """決まった手順に「ダメージを受けたバトル場のポケモンは、にげられるならにげる」を加えたもの。"""
    if state.phase is Phase.MAIN:
        p = state.players[state.current_player]
        cost = state.card_def(p.active.card).retreat_cost
        if p.active.damage and p.bench and len(p.active.energy) >= cost and not any(
            e.get("kind") == "retreat" and e.get("turn") == state.turn_number for e in state.log
        ):
            return Retreat(state.current_player, tuple(p.active.energy[:cost]), p.bench[-1].card)
    return scripted_command(state, **policy)


def run(name, deck0, deck1, seed, *, policy=None, random_seed=None, max_steps=3000, chooser=None):
    state = new_game(deck0, deck1, seed)
    rng = random.Random(random_seed) if random_seed is not None else None
    steps = []
    for _ in range(max_steps):
        if state.phase in END:
            break
        if rng is not None and rng.random() >= 0.35:
            command = random_command(rng, state)
        else:
            command = (chooser or scripted_command)(state, **(policy or {}))
        try:
            state = apply_command(state, command)
            steps.append({"command": command_to_dict(command)})
        except StateIntegrityError:
            raise
        except EngineError as error:
            steps.append({"command": command_to_dict(command), "error": error.code})
    return {
        "name": name,
        "deck0": list(deck0),
        "deck1": list(deck1),
        "seed": seed,
        "steps": steps,
        "final_state": state_to_dict(state),
    }


def main() -> int:
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    scenarios = [
        run("scripted_seed42", FIRE_DECK, WATER_FIGHTING_DECK, 42),
        run("scripted_seed1_janken1", FIRE_DECK, WATER_FIGHTING_DECK, 1, policy={"janken_winner": 1}),
        run("scripted_seed4_mulligan_draws", FIRE_DECK, WATER_FIGHTING_DECK, 4),
        run("scripted_seed8_all_prizes", FIRE_DECK, WATER_FIGHTING_DECK, 8),
        *[run(f"retreats_seed{s}", FIRE_DECK, WATER_FIGHTING_DECK, s, chooser=retreating_command) for s in (5, 6)],
        run("deck_out_seed3", FIRE_DECK, WATER_FIGHTING_DECK, 3, policy={"attack": False}),
        run("no_bench_seed0", FIRE_DECK, WATER_FIGHTING_DECK, 0, policy={"bench": False}),
        run("one_basic_mulligans", ONE_BASIC, FIRE_DECK,
            find_seed(ONE_BASIC, FIRE_DECK, lambda s: s.players[0].mulligans >= 2 and s.players[1].mulligans == 0)),
        run("both_mulligan_once", FEW_BASICS, FEW_BASICS, find_seed(FEW_BASICS, FEW_BASICS, lambda s: s.mulligan_rounds == ((0, 1),))),
        run("halted_few_basics", FEW_BASICS, FEW_BASICS, find_seed(FEW_BASICS, FEW_BASICS, lambda s: s.phase is Phase.HALTED)),
        *[run(f"random_commands_seed{s}", FIRE_DECK, WATER_FIGHTING_DECK, s, random_seed=s) for s in range(4)],
    ]
    data = {
        "description": "v0.1 の対戦結果の参照データ。tests/test_compat_v0_1.py が今のエンジンで再生して比べる。",
        "generated_by": "scripts/make_compat_fixture.py",
        "generated_at_commit": commit,
        "python": sys.version.split()[0],
        "scenarios": scenarios,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    phases = {s["name"]: s["final_state"]["phase"] for s in scenarios}
    print(f"{OUTPUT} を書き出しました（{len(scenarios)} 件、{OUTPUT.stat().st_size} バイト、コミット {commit[:7]}）")
    print(phases)
    return 0


if __name__ == "__main__":
    sys.exit(main())
