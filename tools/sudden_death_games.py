"""v0.134: サドン・デスの延長戦を通す正式な対戦（docs/sudden-death-v0.134.md 10 章）。

使い方::

    python tools/sudden_death_games.py --corpus pikachu --seeds 0:1500 --out <作業用の場所>/sd_pikachu.json
    python tools/sudden_death_games.py --corpus swap --seeds 0:2000 --out <作業用の場所>/sd_swap.json
    python tools/sudden_death_games.py --corpus magnemite --seeds 0:200 --out <作業用の場所>/sd_magnemite.json

- ``pikachu``: v0.2f のピカチュウのデッキ（tests/helpers.py の ``PIKACHU_DECK`` 対 ``PIKACHU_DECK_B``）。「でんげき」の同時のきぜつでサドン・デスになる
- ``swap``: その一部をとりかえっこプリーズ 4 枚にかえた組（tests/sudden_death_games.py）。交換・再交換したカードが場・手札・トラッシュに散らばったままサドン・デスになる
- ``magnemite``: コイル（じばく）を入れた雷のデッキ同士。サイド 1 枚の延長戦がまたサドン・デスになる

new_game から終わるまで進め、サドン・デスになったら ``StartSuddenDeath`` で延長戦を始めて続ける（区間の数の上限 ``MAX_SEGMENTS`` は道具の上限で、エンジンの規則ではない）。
延長戦を始める前後で、入力の状態が変わらないこと・不変条件・ログの監査（区間の確かめ ``segment_problems`` を含む）・観測・書き出しを確かめ、最後に受け付けた操作の列を
new_game からやり直して同じ状態・ログになることを確かめる。局ごとの記録と集計を JSON に書く。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kyuura_engine import (
    Phase,
    apply_command,
    check_invariants,
    new_game,
    state_to_dict,
)
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests.helpers import PIKACHU_DECK, PIKACHU_DECK_B
from tests.log_audit import (
    initial_owners,
    log_problems,
    observation_problems,
    segment_problems,
    serialization_problems,
)
from tests.sudden_death_games import (
    MAGNEMITE_DECK,
    MAX_SEGMENTS,
    SWAP_PIKACHU_DECK,
    SWAP_PIKACHU_DECK_B,
    play_segments,
    status_aware_policy,
    swap_policy_command,
)

LATEST = max(FORMAT_VERSIONS)
CORPORA = {
    "pikachu": ((PIKACHU_DECK, PIKACHU_DECK_B), swap_policy_command),
    "swap": ((SWAP_PIKACHU_DECK, SWAP_PIKACHU_DECK_B), swap_policy_command),
    "magnemite": ((MAGNEMITE_DECK, MAGNEMITE_DECK), status_aware_policy),
}


def _snapshot(state):
    return state_to_dict(state, format_version=LATEST), state.rng.getstate(), tuple(dict(e) for e in state.log)


def _audit(state, *, boundary: bool) -> Counter:
    failures = Counter()
    failures["invariants"] += bool(check_invariants(state))
    failures["log"] += bool(log_problems(state))
    failures["observation"] += bool(observation_problems(state))
    failures["serialization"] += bool(serialization_problems(state))
    if boundary:
        failures["segment"] += bool(segment_problems(state))
    return failures


def play(corpus: str, seed: int) -> dict:
    decks, policy = CORPORA[corpus]
    result = {"corpus": corpus, "seed": seed}
    failures = Counter()
    boundaries = []

    def boundary(before, after):
        snap = _snapshot(before)
        failures.update(_audit(before, boundary=False))
        failures.update(_audit(after, boundary=True))
        swapped = [uid for uid, card in before.cards.items() if card.owner != card.deck_owner]
        reswapped = [uid for uid, n in Counter(c.card for c in before.ownership_changes).items() if n > 1]
        initial = initial_owners(before)
        failures["owner_reset"] += any(after.cards[uid].owner != initial[uid] or after.cards[uid].origin is not None for uid in after.cards)
        boundaries.append({"segment": after.segment_index, "ownership_changes": len(before.ownership_changes), "swapped_at_end": len(swapped),
                           "reswapped": len(reswapped), "result": [list(c) for c in before.result.conditions], "turns": before.turn_number,
                           "next_phase": after.phase.value, "halt_code": after.halt.code if after.halt is not None else None,
                           "mulligan_rounds": len(after.mulligan_rounds)})
        failures["input_changed"] += _snapshot(before) != snap

    try:
        state, commands, ends = play_segments(decks, seed, policy=policy, boundary=boundary)
        result["outcome"] = state.phase.value
        result["segments"] = [e.phase.value for e in ends]
        result["segment_limit"] = state.phase is Phase.SUDDEN_DEATH and len(ends) >= MAX_SEGMENTS
        result["steps"] = len(commands)
        result["prize_counts"] = [r.prize_count for r in state.segments] + [state.initial_prize_count]
        result["set_prizes"] = [[e["count"] for e in r.log if e["kind"] == "set_prizes"] for r in state.segments] + [
            [e["count"] for e in state.log if e["kind"] == "set_prizes"]]
        if state.result is not None:
            result["winner"] = state.result.winner
            result["conditions"] = [list(c) for c in state.result.conditions]
        if state.halt is not None:
            result["halt_code"] = state.halt.code
        failures.update(_audit(state, boundary=True))
        replayed = new_game(*decks, seed)
        for command in commands:
            replayed = apply_command(replayed, command)
        failures["replay_mismatch"] += (state_to_dict(replayed, format_version=LATEST), replayed.log, replayed.segments) != (
            state_to_dict(state, format_version=LATEST), state.log, state.segments)
    except Exception as error:  # noqa: BLE001  内部エラー・道具の上限も集計から落とさない
        result["outcome"] = "error"
        result["error"] = "".join(traceback.format_exception_only(type(error), error))[:500]
    result["boundaries"] = boundaries
    result["audit"] = {k: v for k, v in failures.items() if v}
    return result


def summarize(games: list[dict]) -> dict:
    with_extension = [g for g in games if len(g.get("segments", ())) > 1]
    return {
        "games": len(games),
        "outcomes": dict(Counter(g["outcome"] for g in games)),
        "games_with_extension": len(with_extension),
        "segment_patterns": dict(Counter(" > ".join(g["segments"]) for g in with_extension)),
        "extensions_started": sum(len(g["boundaries"]) for g in games),
        "max_segment": max((g["boundaries"][-1]["segment"] for g in games if g["boundaries"]), default=0),
        "boundaries_with_swapped_cards": sum(1 for g in games for b in g["boundaries"] if b["swapped_at_end"]),
        "swapped_cards_returned": sum(b["swapped_at_end"] for g in games for b in g["boundaries"]),
        "reswapped_cards": sum(b["reswapped"] for g in games for b in g["boundaries"]),
        "extension_setup_halts": dict(Counter(b["halt_code"] for g in games for b in g["boundaries"] if b["halt_code"])),
        "extension_mulligans": sum(1 for g in games for b in g["boundaries"] if b["mulligan_rounds"]),
        "segment_limit": sum(1 for g in games if g.get("segment_limit")),
        "errors": [g for g in games if g["outcome"] == "error"],
        "audit_failures": dict(sum((Counter(g["audit"]) for g in games), Counter())),
        "extension_set_prizes": dict(Counter(",".join(map(str, counts)) for g in with_extension for counts in g["set_prizes"][1:])),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", choices=sorted(CORPORA), required=True)
    parser.add_argument("--seeds", default="0:100", help="start:stop（stop は含まない）")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--conventions", default=None, help="v0.143: 対戦の規約集合（ID@版。省略は今の挙動の集合）。道具だけの選び方で、エンジンの既定は変えない")
    args = parser.parse_args(argv)
    from tools.convention_choice import use_conventions

    conventions = use_conventions(args.conventions)
    start, stop = (int(x) for x in args.seeds.split(":"))
    began = time.time()
    games = [play(args.corpus, seed) for seed in range(start, stop)]
    summary = summarize(games)
    summary["elapsed"] = round(time.time() - began, 1)
    if conventions:
        summary["conventions"] = conventions
    text = json.dumps({"summary": summary, "games": games}, ensure_ascii=False, indent=1)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 1 if summary["errors"] or summary["audit_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
