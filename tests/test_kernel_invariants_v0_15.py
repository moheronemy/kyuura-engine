"""v0.15d: 解決の基盤（経路 ``KERNEL``）の独立した不変条件（docs/event-integration-verification-v0.15d.md 3 章）。

比較のテスト（v0.13 の経路と同じ結果か）とは別に、解決の基盤そのものが守るべき性質を、解決の記録（``Trace``）と、v0.13 の公開の
問い合わせ（``effects.working_evasion_power``・``effects.working_counterattack_power``・``persistent.retaliation``・
``persistent.damage_prevention``。解決の基盤の判定とは別の実装）で、ストレス実行の対戦の 1 歩ごとに確かめる。

1. 窓の順番（枠ごとに、ダメージの要素の窓は「ダメージの要素のあと」の窓より前。受けるときの窓の前に適用の前の窓。きぜつの判定の
   窓は 1 コマンドに 1 回まで、番の終わりより前）
2. 枠の表（``events.SPAWNS``）にある連鎖だけ。根の枠はワザかこんらん
3. 許されない連鎖がない（返す効果の枠の下に返す効果の枠がない。特殊能力のダメージ・こんらんの枠は子を持たない）
4. 同じ効果を二重に処理しない（送る効果の発動は (定義, 持ち主, 枠) ごとに 1 回。子の枠の数は発動の数以下）
5. かがくへんかガスなどではたらいていない特殊能力が発動しない（コマンドの前の状態で、v0.13 の問い合わせがはたらいていると答える）
6. 持続する効果ははたらく番だけ（返す効果の発動は、効果のはたらく番。無効にする効果は「ダメージを受けない」状態のときだけ）
7. きぜつの順番（番でないプレイヤー → 番のプレイヤー、それぞれバトル場 → ベンチ。p.323〜p.324 の規定。v0.13 と同じ）
8. 決定を待つ状態（再開先が解決の基盤のものなら、続きの情報に読みかえられ、解決の記録の最後の中断と種類・プレイヤーが合う）
9. 保存・復元の連続性（決定を待つ状態を pickle で保存・復元して答えても同じ結果）
10. 不正な操作の原子性（拒否したら、渡した状態・乱数・ログが変わらない）
11. 未解決の裁定を推測しない（受け付けた処理の記録に問いがない。原典で決められない場合の拒否は、先読みか実際の処理の検出による）
12. 解決の記録は結果に影響しない（記録をとらずに処理しても同じ結果）
"""

from __future__ import annotations

import pickle
import random
import sys
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

import kyuura_engine as engine
from kyuura_engine import EngineError, state_to_dict
from kyuura_engine.decisions import DECISION_PHASES
from kyuura_engine.effects import working_counterattack_power, working_evasion_power
from kyuura_engine.engine import apply_command_traced, apply_command_with
from kyuura_engine.persistent import damage_prevention, retaliation
from kyuura_engine.resolution import codec, events, processes
from kyuura_engine.resolution.events import FrameKind, Window
from kyuura_engine.rng import rng_fingerprint

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

# 対戦の集まり: 特殊能力・持続する効果がはたらく対戦のテストの方針（v0.4b〜v0.13）と、ストレス実行のすべての組（拒否されるコマンドを混ぜる）
NATURAL_MODULES = ("test_machamp_games_v0_10", "test_moltres_games_v0_12", "test_dark_wartortle_games_v0_13", "test_haunter_games_v0_9",
                   "test_giovanni_games_v0_11", "test_muk_games_v0_8", "test_butterfree_games_v0_4d", "test_harden_games_v0_4b")
NATURAL_SEEDS = range(10)
STRESS_SEEDS = range(2)
STEPS = 400


def full(state):
    return state_to_dict(state, format_version=9)


FRAME_WINDOWS = (Window.BEFORE_DAMAGE, Window.DAMAGE_RECEIVING, Window.AFTER_DAMAGE_ELEMENTS)


def window_problems(trace) -> list[str]:
    """1. 窓の順番。"""
    problems = []
    per_frame: dict[int, list[Window]] = {}
    global_windows: list[Window] = []
    frames_before_ko_check: set[int] | None = None
    opened: set[int] = set()
    for event in trace.events:
        if isinstance(event, events.FrameOpened):
            opened.add(event.frame.id)
        if not isinstance(event, events.WindowOpened):
            continue
        if event.frame is None:
            global_windows.append(event.window)
            if event.window is Window.KO_CHECK:
                frames_before_ko_check = set(opened)
            continue
        if frames_before_ko_check is not None and event.frame in frames_before_ko_check:
            problems.append(f"きぜつの判定の窓のあとに、枠 {event.frame} の窓 {event.window.value}")
        sequence = per_frame.setdefault(event.frame, [])
        if event.window in (Window.BEFORE_DAMAGE, Window.DAMAGE_RECEIVING) and Window.AFTER_DAMAGE_ELEMENTS in sequence:
            problems.append(f"枠 {event.frame}: ダメージの要素のあとの窓のあとに {event.window.value}")
        if event.window is Window.DAMAGE_RECEIVING and (not sequence or sequence[-1] is not Window.BEFORE_DAMAGE):
            problems.append(f"枠 {event.frame}: 受けるときの窓の直前が適用の前の窓でない")
        sequence.append(event.window)
    if global_windows.count(Window.KO_CHECK) > 1 or global_windows.count(Window.TURN_END) > 1:
        problems.append(f"きぜつの判定・番の終わりの窓が 2 回以上: {global_windows}")
    if Window.KO_CHECK in global_windows and Window.TURN_END in global_windows and \
            global_windows.index(Window.TURN_END) < global_windows.index(Window.KO_CHECK):
        problems.append(f"番の終わりのあとにきぜつの判定の窓: {global_windows}")
    return problems


def frame_problems(trace) -> list[str]:
    """2・3・4. 枠の表・許されない連鎖・二重の処理。"""
    problems = []
    frames: dict[int, events.Frame] = {}
    for event in trace.of(events.FrameOpened):
        frame = event.frame
        frames[frame.id] = frame
        if frame.parent is None:
            if frame.kind not in (FrameKind.ATTACK, FrameKind.CONFUSION):
                problems.append(f"根の枠 {frame.kind.value}")
            continue
        parent = frames.get(frame.parent)
        if parent is None:
            problems.append(f"枠 {frame.id} の親 {frame.parent} が先に開いていない")
            continue
        if frame.kind not in events.SPAWNS[parent.kind]:
            problems.append(f"表にない連鎖 {parent.kind.value} → {frame.kind.value}")
        if parent.kind in (FrameKind.POWER_DAMAGE, FrameKind.CONFUSION):
            problems.append(f"子を持たない枠 {parent.kind.value} の子")
        ancestor = parent
        while ancestor is not None:
            if frame.kind is FrameKind.RETALIATION and ancestor.kind is FrameKind.RETALIATION:
                problems.append("返す効果の枠の下に返す効果の枠")
            ancestor = frames.get(ancestor.parent) if ancestor.parent is not None else None
    deferred = Counter((e.definition, e.holder_pid, e.frame) for e in trace.of(events.Activated) if e.window is Window.AFTER_DAMAGE_ELEMENTS)
    for key, count in deferred.items():
        if count > 1:
            problems.append(f"送る効果の二重の発動 {key}")
    children = Counter(frame.parent for frame in frames.values() if frame.parent is not None)
    for parent, count in children.items():
        if count > sum(n for (_, _, frame), n in deferred.items() if frame == parent):
            problems.append(f"枠 {parent} の子の枠 {count} が、発動した送る効果より多い")
    return problems


def effect_problems(before, trace) -> list[str]:
    """5・6. はたらいていない特殊能力・持続する効果が発動しない（コマンドの前の状態で、v0.13 の公開の問い合わせで確かめる）。"""
    problems = []
    for event in trace.of(events.Activated):
        found = before.find_pokemon(event.holder_pid) if event.holder_pid is not None else None
        if found is None:
            continue  # コマンドの中で場に出たポケモン（今の対応カードでは起こらない）
        pokemon = found[1]
        if event.definition == "transparency" and working_evasion_power(before, event.holder_pid) is None:
            problems.append(f"はたらいていない「とうめい」の発動（ポケモン {event.holder_pid}）")
        if event.definition == "strikes_back" and working_counterattack_power(before, event.holder_pid) is None:
            problems.append(f"はたらいていない「はんげき」の発動（ポケモン {event.holder_pid}）")
        if event.definition == "retaliation" and retaliation(before, pokemon) is None:
            problems.append(f"はたらく番でない返す効果の発動（ポケモン {event.holder_pid}）")
    for event in trace.of(events.DamageVoided):
        found = before.find_pokemon(event.target_pid)
        if found is not None and damage_prevention(before, found[1]) is None:
            problems.append(f"「ダメージを受けない」状態でないポケモン {event.target_pid} のダメージを無効にした")
    return problems


def knock_out_problems(before, after) -> list[str]:
    """7. きぜつの順番（番でないプレイヤー → 番のプレイヤー、それぞれバトル場 → ベンチ）。"""
    current = before.current_player
    order = []
    for event in after.log[len(before.log):]:
        if event["kind"] != "knock_out":
            continue
        found = [(owner, pokemon) for owner, player in enumerate(before.players) for pokemon in player.in_play() if pokemon.card == event["pokemon"]]
        if len(found) != 1:
            return [f"きぜつしたカード {event['pokemon']} がコマンドの前の場にない"]
        active = before.players[found[0][0]].active is found[0][1]
        order.append((event["player"] != 1 - current, not active))
    return [] if order == sorted(order) else [f"きぜつの順番 {order}"]


def decision_problems(before, after, trace) -> list[str]:
    """8. 決定を待つ状態。"""
    decision = after.decision
    if decision is None or decision.resume not in codec.RESUMES:
        return []
    problems = []
    if after.phase not in DECISION_PHASES:
        problems.append(f"決定を待つのに段階が {after.phase}")
    codec.decode(decision)  # 続きの情報に読みかえられる（読めなければ例外）
    if before.decision is None or before.decision.id != decision.id:
        suspended = trace.of(events.Suspended)
        if not suspended or (suspended[-1].resume, suspended[-1].kind, suspended[-1].player) != (decision.resume, decision.kind, decision.player):
            problems.append(f"決定 {decision.kind} と解決の記録の中断 {suspended[-1:] }が合わない")
    return problems


class Recorder:
    """経路 KERNEL（標準の先読み）で 1 歩を処理し、不変条件を確かめる。"""

    def __init__(self, test: unittest.TestCase):
        self.test = test
        self.counts: Counter = Counter()

    def __call__(self, state, command):
        before_full, before_rng, before_log = full(state), rng_fingerprint(state.rng), state.log
        owned = processes(state, command)
        # 12. 解決の記録は結果に影響しない（記録をとらずに処理した結果と比べる。拒否も、例外の種類・コード・理由の文を比べる）
        quiet = None
        if owned:
            with mock.patch.object(events.Trace, "record", lambda self, event: None):
                quiet = outcome(lambda: apply_command_with(state, command))
        try:
            after, trace = apply_command_traced(state, command)
        except EngineError as error:
            # 10. 不正な操作の原子性
            self.test.assertEqual((full(state), rng_fingerprint(state.rng)), (before_full, before_rng))
            self.test.assertIs(state.log, before_log)
            if quiet is not None:
                self.test.assertEqual(quiet, ("rejected", type(error), error.code, error.message), "記録をとらないと結果が変わった")
            self.counts["rejected"] += 1
            if owned and error.code.startswith("UNRESOLVED_"):
                self.counts["unresolved"] += 1
            raise
        self.test.assertEqual((full(state), rng_fingerprint(state.rng)), (before_full, before_rng))
        if quiet is not None:
            self.test.assertEqual(quiet, ("ok", full(after), rng_fingerprint(after.rng)), "記録をとらないと結果が変わった")
        problems = window_problems(trace) + frame_problems(trace) + effect_problems(state, trace) + knock_out_problems(state, after) + \
            decision_problems(state, after, trace)
        # 11. 受け付けた処理の記録に問いがない
        if trace.of(events.QuestionHit):
            problems.append(f"受け付けた処理の記録に問い {trace.of(events.QuestionHit)}")
        self.test.assertEqual(problems, [], f"{engine.command_to_dict(command)}")
        if owned:
            self.counts["owned"] += 1
            self.counts["activated"] += len(trace.of(events.Activated))
            self.counts["frames"] += len(trace.of(events.FrameOpened))
        # 9. 保存・復元の連続性（決定を待つ状態）
        if after.decision is not None and after.decision.resume in codec.RESUMES:
            self.counts["decisions"] += 1
            restored = pickle.loads(pickle.dumps(after))
            self.test.assertEqual(full(restored), full(after))
        self.counts["steps"] += 1
        return after


def outcome(apply):
    try:
        new = apply()
    except EngineError as error:
        return ("rejected", type(error), error.code, error.message)
    return ("ok", full(new), rng_fingerprint(new.rng))


class KernelInvariantGameTest(unittest.TestCase):
    def test_invariants_in_natural_games(self):
        """対戦のテストの方針（特殊能力・持続する効果がはたらく 8 つ × seed 0〜9）。モジュールの ``apply_command`` を確かめる関数に差しかえる。"""
        import importlib
        recorder = Recorder(self)
        for name in NATURAL_MODULES:
            module = importlib.import_module(f"tests.{name}")
            original = module.apply_command
            module.apply_command = recorder
            try:
                for seed in NATURAL_SEEDS:
                    with self.subTest(module=name, seed=seed):
                        module.play_game(seed)
            finally:
                module.apply_command = original
        self.assertGreater(recorder.counts["owned"], 3000)
        self.assertGreater(recorder.counts["activated"], 60)
        self.assertGreater(recorder.counts["decisions"], 600)
        self.assertGreater(recorder.counts["unresolved"], 15)

    def test_invariants_in_stress_games(self):
        """ストレス実行のすべての組 × seed 0〜1（拒否されるコマンドを 5% 混ぜる）。"""
        import compat_driver as driver
        import stress_engine as stress
        recorder = Recorder(self)
        for spec in stress.ALL_SCENARIOS:
            for seed in STRESS_SEEDS:
                with self.subTest(scenario=spec.name, seed=seed):
                    rng = random.Random(f"kyuura-stress:{spec.name}:{seed}")
                    state = engine.new_game(driver._deck(spec.deck0), driver._deck(spec.deck1), seed)
                    for _ in range(STEPS):
                        if state.phase in engine.TERMINAL_PHASES:
                            break
                        command = stress.choose_command(state, rng, 0.05)
                        try:
                            state = recorder(state, command)
                        except EngineError:
                            continue
        self.assertGreater(recorder.counts["owned"], 2500)
        self.assertGreater(recorder.counts["activated"], 15)
        self.assertGreater(recorder.counts["decisions"], 300)
        self.assertGreater(recorder.counts["rejected"], 5000)


class SaveRestoreContinuityTest(unittest.TestCase):
    """9. 決定を待つ状態を保存・復元してから答えても、そのまま答えたのと同じ結果。"""

    def test_resume_after_pickle(self):
        import compat_driver as driver
        import stress_engine as stress
        resumed = 0
        for spec, seed in ((spec, seed) for spec in stress.ALL_SCENARIOS
                           if spec.name in ("moltres_mixed", "giovanni_mixed", "machamp_mixed", "butterfree", "haunter") for seed in range(3)):
            rng = random.Random(f"kyuura-stress:{spec.name}:{seed}")
            state = engine.new_game(driver._deck(spec.deck0), driver._deck(spec.deck1), seed)
            for _ in range(STEPS):
                if state.phase in engine.TERMINAL_PHASES:
                    break
                command = stress.choose_command(state, rng, 0.0)
                waiting = state.decision is not None and state.decision.resume in codec.RESUMES
                try:
                    after, _ = apply_command_traced(state, command)
                except EngineError:
                    continue
                if waiting:
                    restored, _ = apply_command_traced(pickle.loads(pickle.dumps(state)), command)
                    self.assertEqual((full(restored), rng_fingerprint(restored.rng)), (full(after), rng_fingerprint(after.rng)))
                    resumed += 1
                state = after
        self.assertGreater(resumed, 60)


class CheckerTest(unittest.TestCase):
    """不変条件の確かめ方そのものが、壊れた記録を見つけること（確かめ方が何も見ないことを防ぐ）。"""

    def frame(self, id_, kind, parent=None):
        return events.FrameOpened(events.Frame(id_, kind, parent, 0, 1, None))

    def trace(self, *items):
        trace = events.Trace()
        for item in items:
            trace.record(item)
        return trace

    def test_window_checker(self):
        self.assertTrue(window_problems(self.trace(self.frame(1, FrameKind.ATTACK), events.WindowOpened(Window.AFTER_DAMAGE_ELEMENTS, 1),
                                                   events.WindowOpened(Window.BEFORE_DAMAGE, 1))))
        self.assertTrue(window_problems(self.trace(self.frame(1, FrameKind.ATTACK), events.WindowOpened(Window.DAMAGE_RECEIVING, 1))))
        self.assertTrue(window_problems(self.trace(self.frame(1, FrameKind.ATTACK), events.WindowOpened(Window.KO_CHECK, None),
                                                   events.WindowOpened(Window.BEFORE_DAMAGE, 1))))
        self.assertEqual(window_problems(self.trace(self.frame(1, FrameKind.ATTACK), events.WindowOpened(Window.BEFORE_DAMAGE, 1),
                                                    events.WindowOpened(Window.DAMAGE_RECEIVING, 1),
                                                    events.WindowOpened(Window.AFTER_DAMAGE_ELEMENTS, 1),
                                                    events.WindowOpened(Window.KO_CHECK, None))), [])

    def test_frame_checker(self):
        self.assertTrue(frame_problems(self.trace(self.frame(1, FrameKind.ATTACK), self.frame(2, FrameKind.RETALIATION, 1),
                                                  self.frame(3, FrameKind.RETALIATION, 2))))
        self.assertTrue(frame_problems(self.trace(self.frame(1, FrameKind.RETALIATION))))
        self.assertTrue(frame_problems(self.trace(self.frame(1, FrameKind.ATTACK), self.frame(2, FrameKind.POWER_DAMAGE, 1))))
        twice = events.Activated(Window.AFTER_DAMAGE_ELEMENTS, "strikes_back", 3, 1)
        self.assertTrue(frame_problems(self.trace(self.frame(1, FrameKind.ATTACK), twice, twice, self.frame(2, FrameKind.POWER_DAMAGE, 1),
                                                  self.frame(3, FrameKind.POWER_DAMAGE, 1))))


if __name__ == "__main__":
    unittest.main()
