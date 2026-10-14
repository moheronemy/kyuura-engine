"""v0.15b: 解決の基盤（``kyuura_engine/resolution``）の本番への統合（docs/kernel-integration-v0.15b.md）。

- 経路（``engine.Route``。v0.13 の経路 ``LEGACY``・解決の基盤 ``KERNEL``）は、公開の ``apply_command`` の呼び方を変えずに、内部の入口
  ``engine.apply_command_via`` で明示して選ぶ。先読みの方法（``derived``・``legacy``）とは別のもの。
- 依存の向き: engine → resolution → checks・procedures（解決の基盤は engine を読み込まない。v0.13 の経路の処理は解決の基盤を使わない）。
- 受け持つコマンドの振り分け（``resolution.handles``）: ワザの実装の型が要素の並びの対応表（``BUILDERS``）にないワザは v0.13 の経路。
- 止める理由の文は両方の経路で同じ（``effects`` の共通の関数で作る）。
- 解決の基盤の経路の原子性と、先読みを外しても推測で進めないこと（v0.13 の経路の内部の関数を差しかえるテスト（v0.9・v0.10）の、解決の
  基盤の経路での対応）。

裁定の根拠は各文書のまま（C18: docs/counterattack-v0.10.md・p.324、W24: docs/rocket-moltres-v0.12.md・p.82、S37: docs/shell-attack-v0.13.md・
p.89、G37: docs/guts-v0.11.md・p.193、T19b: docs/transparency-v0.9.md・p.159、v0.4b: docs/persistent-damage-v0.4b.md・p.321、こんらんの
変更効果: docs/confusion-attacks-v0.3c.md・p.322。どれも kyuura の NEO-2000-OFFICIAL-RULES）。盤面は ``build_test_state`` で直接作る
（1 か所の規定を確かめるテスト）。
"""

from __future__ import annotations

import ast
import contextlib
import inspect
import unittest
from pathlib import Path
from unittest import mock

import kyuura_engine
from kyuura_engine import (
    DEFAULT_EFFECTS, AttachEnergy, EndTurn, EngineError, PromoteActive, ResolveDecision, TakePrize, UnsupportedError, UseAttack,
    UsePokemonPower, check_invariants, state_to_dict,
)
from kyuura_engine import engine
from kyuura_engine import resolution
from kyuura_engine.conditions import POISON, SLEEP
from kyuura_engine.effects import AttackEntry, AttackKey, DamageOnly
from kyuura_engine.engine import Route, apply_command_traced, apply_command_via
from kyuura_engine.resolution import codec, events, programs
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import GameState

from tests.helpers import (
    BUTTERFREE, CATERPIE, DODUO, FIGHTING, FIRE, GRASS, H, MACHOP, METAPOD, PSYCHIC, RATTATA, T, WATER, WEEDLE, apply_kernel, apply_legacy,
    build_test_state, two_step_effects, with_coin_results,
)
from tests import test_counterattack_v0_10 as CA
from tests import test_transparency_v0_9 as TR
from tests.test_event_kernel_v0_14 import DARK_, GIOVANNI_, MACHAMP_, PONYTA_, TURN, UnresolvedTest, board

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "kyuura_engine"


def full(state):
    return state_to_dict(state, format_version=9)


def outcome(apply, state, command, **options):
    """受け付けたら形式 9 の全体と乱数の指紋、拒否なら例外の種類・コード・理由の文。"""
    try:
        new = apply(state, command, **options)
    except EngineError as error:
        return ("rejected", type(error), error.code, error.message)
    return ("ok", full(new), rng_fingerprint(new.rng))


def imports_of(path: Path) -> set[str]:
    """モジュールが読み込む名前（相対の読み込みは、パッケージの中の名前に直す）。"""
    package = path.relative_to(ROOT).with_suffix("").parts[:-1]
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = list(package[: len(package) - node.level + 1]) if node.level else []
            module = ".".join(base + ([node.module] if node.module else []))
            found.add(module)
            found.update(f"{module}.{alias.name}" for alias in node.names)
    return found


# ---------------------------------------------------------------- 経路の選び方


class RouteTest(unittest.TestCase):
    def test_public_apply_command_is_unchanged(self):
        """公開の ``apply_command`` の呼び方（引数）は変えない。経路を選ぶ入口は公開の API に加えない。"""
        self.assertEqual(list(inspect.signature(kyuura_engine.apply_command).parameters), ["state", "command"])
        self.assertIs(kyuura_engine.apply_command, engine.apply_command)
        for name in ("Route", "apply_command_via", "apply_command_traced", "DEFAULT_ROUTE", "resolution"):
            self.assertNotIn(name, kyuura_engine.__all__)
        self.assertIsInstance(engine.DEFAULT_ROUTE, Route)

    def test_routes_are_chosen_explicitly(self):
        """経路は引数で選ぶ（名前の文字列でも同じ）。標準の経路は ``DEFAULT_ROUTE``。知らない経路・先読みの方法は ValueError。"""
        state = board(PONYTA_, MACHAMP_)
        command = UseAttack(0, 1)
        legacy = outcome(apply_command_via, state, command, route=Route.LEGACY)
        for route in (Route.LEGACY, "legacy", Route.KERNEL, "kernel"):
            with self.subTest(route=route):
                self.assertEqual(outcome(apply_command_via, state, command, route=route), legacy)
        self.assertEqual(outcome(lambda s, c: kyuura_engine.apply_command(s, c), state, command),
                         outcome(apply_command_via, state, command, route=engine.DEFAULT_ROUTE))
        for bad in ({"route": "other"}, {"route": Route.KERNEL, "preflight": "fast"}, {"route": Route.LEGACY, "preflight": "fast"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                apply_command_via(state, command, **bad)

    def test_route_and_preflight_are_different_settings(self):
        """経路と先読みの方法は別の設定: どの組み合わせも同じ結果。解決の記録は解決の基盤の経路だけが作り、先読みの方法を記録する。"""
        state = board({**PONYTA_, "damage": 30}, {**MACHAMP_, "damage": 80})  # C18 で止まる
        accepted = board(PONYTA_, MACHAMP_)
        for sample, command in ((state, UseAttack(0, 1)), (accepted, UseAttack(0, 1)), (accepted, EndTurn(0))):
            results = [outcome(apply_command_via, sample, command, route=route, preflight=mode)
                       for route in Route for mode in resolution.PREFLIGHT_MODES]
            self.assertTrue(all(result == results[0] for result in results))
        for mode in resolution.PREFLIGHT_MODES:
            _, trace = apply_command_traced(accepted, UseAttack(0, 1), preflight=mode)
            self.assertEqual([e.mode for e in trace.of(events.PreflightResult)], [mode])

    def test_no_module_state_selects_the_route(self):
        """経路を選んでも、モジュールの値（標準の経路など）は変わらない（グローバルな可変フラグで切り替えない）。"""
        names = dict(vars(engine))
        resolution_names = dict(vars(resolution))
        for route in Route:
            apply_command_via(board(PONYTA_, MACHAMP_), UseAttack(0, 1), route=route)
        self.assertEqual({k: v for k, v in vars(engine).items() if names.get(k) is not v}, {})
        self.assertEqual({k: v for k, v in vars(resolution).items() if resolution_names.get(k) is not v}, {})


# ---------------------------------------------------------------- 依存の向き


class DependencyTest(unittest.TestCase):
    def test_resolution_and_shared_parts_do_not_import_the_engine(self):
        """解決の基盤と共通の部品（checks・procedures）は engine を読み込まない（engine → resolution → engine の循環がない）。"""
        paths = sorted((PACKAGE / "resolution").glob("*.py")) + [PACKAGE / "checks.py", PACKAGE / "procedures.py"]
        for path in paths:
            with self.subTest(module=path.name):
                found = imports_of(path)
                self.assertFalse([name for name in found if name == "kyuura_engine.engine" or name.startswith("kyuura_engine.engine.")])
        self.assertIn("kyuura_engine.checks", imports_of(PACKAGE / "resolution" / "flow.py"))  # 相対の読み込みを数えられている
        for path in (PACKAGE / "checks.py", PACKAGE / "procedures.py"):
            with self.subTest(shared=path.name):
                self.assertFalse(any(name.startswith("kyuura_engine.resolution") for name in imports_of(path)))

    def test_legacy_handlers_do_not_use_the_kernel(self):
        """v0.13 の経路の処理（engine.py のコマンドの処理）は解決の基盤を使わない。``resolution`` を使うのは、経路を選ぶ入口だけ
        （型の注釈を含む）。"""
        tree = ast.parse((PACKAGE / "engine.py").read_text(encoding="utf-8"))
        users = {
            function.name
            for function in tree.body if isinstance(function, ast.FunctionDef)
            for node in ast.walk(function) if isinstance(node, ast.Name) and node.id == "resolution"
        }
        self.assertEqual(users, {"_apply", "_kernel_options", "apply_command_via", "apply_command_traced"})

    def test_compatibility_layer_is_not_a_copy(self):
        """v0.14 の名前（``experiments.event_kernel``）は本番の部品そのものを指す（コードの複製がない）。"""
        from experiments import event_kernel as K
        from experiments.event_kernel import kernel
        self.assertIs(kernel, resolution.kernel)
        self.assertIs(K.BUILDERS, resolution.BUILDERS)
        self.assertEqual(sorted(p.name for p in (ROOT / "experiments" / "event_kernel").glob("*.py")), ["__init__.py"])


# ---------------------------------------------------------------- 受け持つコマンドの振り分け


class SubclassedDamage(DamageOnly):
    """テスト専用: 要素の並びの対応表にある実装（DamageOnly）の部分型。対応表は型が完全に一致するものだけなので、v0.13 の経路で処理する。"""

    implementation_id = "test_subclassed_damage"

    def resolve(self, state, use):
        super().resolve(state, use)
        state.add_event("test_subclassed_damage", pokemon_id=use.pokemon_id)


class DispatchTest(unittest.TestCase):
    def test_every_registered_attack_is_handled_by_the_kernel(self):
        """製品の登録表のワザの実装は、どれも解決の基盤が受け持つ（v0.13 の経路にまかせるのは、試験の登録表の実装だけ）。"""
        for key in DEFAULT_EFFECTS.attack_keys():
            effect = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).effect
            with self.subTest(attack=str(key)):
                self.assertIn(type(effect), resolution.BUILDERS)

    def test_opponent_effect_elements_come_from_the_program(self):
        """G37 の理由の文に書く効果の要素の種類は、解決の基盤では要素の並びから求める。どの登録されたワザでも、v0.13 の実装の宣言
        （``AttackEffect.opponent_effect_elements``。v0.11）と同じ（G37 の判定と理由の文が両方の経路で同じになる前提）。"""
        for key in DEFAULT_EFFECTS.attack_keys():
            effect = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).effect
            with self.subTest(attack=str(key)):
                self.assertEqual(programs.opponent_effect_elements(resolution.compile_attack(effect)), effect.opponent_effect_elements)

    def test_target_commands(self):
        """受け持つのは、ワザ・番の終わり・再開先が attack・knock_out・post_knockout・take_prize・promote_active の決定への答えだけ。"""
        state = board(PONYTA_, MACHAMP_)
        self.assertTrue(resolution.handles(state, UseAttack(0, 1)))
        self.assertTrue(resolution.handles(state, UseAttack(1, 0)))  # 確認で拒否されるワザも受け持つ（同じ checks で拒否する）
        self.assertTrue(resolution.handles(state, EndTurn(0)))
        for command in (AttachEnergy(0, 0, 0), UsePokemonPower(0, 1, 0), ResolveDecision(0, 1, ()), TakePrize(0, 0), PromoteActive(0, 0)):
            with self.subTest(command=type(command).__name__):
                self.assertFalse(resolution.handles(state, command))
        waiting = apply_legacy(board(PONYTA_, {**GIOVANNI_, "damage": 80}), UseAttack(0, 1))  # こんじょうの決定（knock_out）
        self.assertEqual(waiting.decision.resume, codec.KNOCK_OUT)
        self.assertTrue(resolution.handles(waiting, ResolveDecision(1, waiting.decision.id, ())))

    def test_effects_outside_the_table_use_the_v0_13_path(self):
        """対応表にない実装（試験の 2 段階の決定）は、経路 KERNEL でも v0.13 の処理になり、決定の答えも v0.13 の処理で続く。"""
        state = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING]}, "bench": [RATTATA]},
            {"active": RATTATA, "bench": [RATTATA]},
        ], effects=two_step_effects())
        self.assertFalse(resolution.handles(state, UseAttack(0, 0)))
        legacy, kernel = apply_legacy(state, UseAttack(0, 0)), apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(full(kernel), full(legacy))
        for step in range(2):
            decision = kernel.decision
            command = ResolveDecision(0, decision.id, (decision.options[0],))
            self.assertEqual(decision.resume, codec.ATTACK)
            self.assertFalse(resolution.handles(kernel, command))
            legacy, kernel = apply_legacy(legacy, command), apply_kernel(kernel, command)
            self.assertEqual(full(kernel), full(legacy))
        self.assertEqual([e["kind"] for e in kernel.log if e["kind"] == "test_two_step"], ["test_two_step"])

    def test_subclass_of_a_table_entry_is_not_compiled(self):
        """対応表の型の部分型は、親の型の並びで処理しない（部分型の resolve を使う。v0.13 の経路）。"""
        effects = DEFAULT_EFFECTS.with_attacks("test-subclass", {AttackKey(MACHOP, 0): AttackEntry(SubclassedDamage(), "けたぐり")})
        state = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING]}, "bench": [RATTATA]},
            {"active": RATTATA, "bench": [RATTATA]},
        ], effects=effects)
        self.assertFalse(resolution.handles(state, UseAttack(0, 0)))
        new = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(full(new), full(apply_legacy(state, UseAttack(0, 0))))
        self.assertIn("test_subclassed_damage", [e["kind"] for e in new.log])


# ---------------------------------------------------------------- 止める理由の文


class MessageTest(unittest.TestCase):
    def cases(self):
        yield from ((name, make, command) for name, (make, command, _) in UnresolvedTest.CASES.items())
        # 返す量・はんげきがコインの結果で変わる盤面（理由の文の数は、v0.13 と同じ結果の組から求める）
        for damage in range(0, 50, 10):
            for held in range(0, 60, 10):
                yield (f"S37 みだれづき {damage}/{held}",
                       lambda d=damage, h=held: board({"card": DODUO, "energy": [FIRE], "damage": d},
                                                     {**DARK_, "damage": h, "retaliation_received": TURN - 1}), UseAttack(0, 0))
                yield (f"S37 ハリケーンパンチ {damage}/{held}",
                       lambda d=damage, h=held: board({**GIOVANNI_, "energy": [FIGHTING] * 4, "damage": d},
                                                     {**DARK_, "damage": h, "retaliation_received": TURN - 1}), UseAttack(0, 1))
                yield (f"C18 みだれづき {damage}/{held}",
                       lambda d=damage, h=held: board({"card": DODUO, "energy": [FIRE], "damage": d}, {**MACHAMP_, "damage": h + 40}),
                       UseAttack(0, 0))

    def test_stop_messages_are_the_same_on_both_routes(self):
        """原典で決められない場合に止めるときの例外の種類・コード・理由の文が、v0.13 の経路と同じ（2 つの先読みとも）。"""
        stopped = 0
        for name, make, command in self.cases():
            with self.subTest(case=name):
                self.assertEqual(check_invariants(make()), [])
                expected = outcome(apply_legacy, make(), command)
                stopped += expected[0] == "rejected"
                for mode in resolution.PREFLIGHT_MODES:
                    self.assertEqual(outcome(apply_kernel, make(), command, preflight=mode), expected, mode)
        self.assertGreaterEqual(stopped, 30)

    def test_refused_chain_names_the_assumption(self):
        """返すダメージで返す効果がはたらく壊れた盤面（v0.13 の S45）は、解決の基盤でも番の進み方の前提を書いた RuntimeError で止まる。"""
        state = build_test_state([
            {"active": {**DARK_, "energy": [WATER], "retaliation_received": TURN - 1}, "bench": [RATTATA]},
            {"active": {**DARK_, "retaliation_received": TURN - 1}, "bench": [PONYTA_["card"]]},
        ], turn_number=TURN)
        before = full(state)
        for apply in (apply_legacy, apply_kernel):
            with self.subTest(route=apply.__name__), self.assertRaisesRegex(RuntimeError, "番の進み方の前提"):
                apply(with_coin_results(state, H, H), UseAttack(0, 0))
        self.assertEqual(full(state), before)


# ---------------------------------------------------------------- 解決の基盤の経路の原子性・止める確認


def boom(*args, **kwargs):
    raise RuntimeError("注入した誤り")


def failing_event(kind):
    """``add_event`` で ``kind`` のイベントを書くところで誤りを起こす（どちらの経路でも同じ所）。"""
    original = GameState.add_event

    def add_event(self, event_kind, **data):
        if event_kind == kind:
            raise RuntimeError("注入した誤り")
        return original(self, event_kind, **data)

    return mock.patch.object(GameState, "add_event", add_event)


class KernelAtomicityTest(unittest.TestCase):
    """v0.10 の ``AtomicityTest.test_internal_error_after_the_counter``・v0.9 の ``test_internal_error_after_the_power_coin`` と同じ盤面で、
    解決の基盤の経路の同じ所（ログ・回復・入れ替えの決定・特殊状態）に誤りを注入する。渡した状態・乱数・ログは変わらない。先読み
    ``legacy`` では注入した所に実際の処理だけが来るので、両方の先読みで確かめる。"""

    def assert_unchanged(self, state, command, patch):
        for mode in resolution.PREFLIGHT_MODES:
            with self.subTest(mode=mode):
                before, fingerprint, log = full(state), rng_fingerprint(state.rng), state.log
                with patch, self.assertRaises(RuntimeError):
                    apply_kernel(state, command, preflight=mode)
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
                self.assertIs(state.log, log)

    def test_internal_error_after_the_counter(self):
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD]}
        self.assert_unchanged(CA.board(CA.HITMONCHAN_JAB), UseAttack(0, 0), failing_event("counterattack"))
        self.assert_unchanged(CA.board({**butterfree, "energy": [GRASS] * 4}), UseAttack(0, 1), failing_event("drain_heal"))
        self.assert_unchanged(CA.board({**butterfree, "energy": [GRASS, GRASS]}), UseAttack(0, 0),
                              mock.patch.object(codec, "push_decision", boom))
        self.assert_unchanged(with_coin_results(CA.board({"card": WEEDLE, "energy": [GRASS]}), H), UseAttack(0, 0),
                              mock.patch.dict(programs.APPLY_CONDITION, {POISON: boom}))

    def test_internal_error_after_the_power_coin(self):
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD]}
        self.assert_unchanged(with_coin_results(TR.board(TR.haunter(energy=[PSYCHIC, PSYCHIC])), T), UseAttack(0, 0),
                              mock.patch.dict(programs.APPLY_CONDITION, {SLEEP: boom}))
        self.assert_unchanged(with_coin_results(TR.board({**butterfree, "energy": [GRASS, GRASS]}), T), UseAttack(0, 0),
                              mock.patch.object(codec, "push_decision", boom))
        self.assert_unchanged(with_coin_results(TR.board({"card": RATTATA, "energy": [FIRE]}), H), UseAttack(0, 0),
                              failing_event("attack_evaded"))


class KernelGuardTest(unittest.TestCase):
    """先読みを外しても（宣言の前の確認をしない）、実際の処理が同じ検出で同じコードの拒否にする（推測で進めない）。v0.10 の
    ``test_double_knock_out_guard_after_the_preflight`` の解決の基盤での対応（v0.13 の経路は RuntimeError で止める。解決の基盤は、先読みと
    同じ検出なので、同じコードの UnsupportedError になる）。渡した状態は変わらない。"""

    # 実際の処理で問いに当たる結果のコイン（こんらんは「うら」でこんらんのダメージ、とうめいは「おもて」で受けない）
    COINS = {"T19b": (H,), "confusion_modifiers": (T,)}

    def test_questions_are_detected_in_the_real_run(self):
        no_preflight = contextlib.ExitStack()
        no_preflight.enter_context(mock.patch("kyuura_engine.resolution.preflight.derived", lambda *args, **kwargs: None))
        no_preflight.enter_context(mock.patch("kyuura_engine.resolution.preflight.legacy", lambda *args, **kwargs: None))
        with no_preflight:
            for name, (make, command, code) in UnresolvedTest.CASES.items():
                state = with_coin_results(make(), *self.COINS.get(name, ()))
                before, fingerprint = full(state), rng_fingerprint(state.rng)
                for mode in resolution.PREFLIGHT_MODES:
                    with self.subTest(case=name, mode=mode):
                        with self.assertRaises(UnsupportedError) as ctx:
                            apply_kernel(state, command, preflight=mode)
                        self.assertEqual(ctx.exception.code, code)
                        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))


if __name__ == "__main__":
    unittest.main()
