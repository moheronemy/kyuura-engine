"""v0.15b: 解決の基盤（``kyuura_engine/resolution``）の本番への統合（docs/kernel-integration-v0.15b.md）。

- v0.16b: 経路（v0.15b の ``engine.Route``）を外した。公開の ``apply_command`` の呼び方は変えず、解決の設定（先読みの方法）は内部の入口
  ``engine.apply_command_with`` で明示して選ぶ。v0.13 の経路の名前が戻っていないことも確かめる。
- 依存の向き: engine → resolution → checks・procedures（解決の基盤は engine を読み込まない。範囲外のコマンドの処理は解決の基盤を使わない）。
- コマンドの振り分け: ワザ・番の終わりと、再開先が ``resolution.RESUMES`` の決定への答えは解決の基盤。対応表（``BUILDERS``）にないワザの
  実装は v0.13 の約束のアダプタ（v0.16b。``resolution.contract``）。
- 止める理由の文は v0.13 と同じ（``effects`` の共通の関数で作る。参照データと比べる）。
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
    DEFAULT_EFFECTS, EndTurn, EngineError, ResolveDecision, UnsupportedError, UseAttack,
    check_invariants, state_to_dict,
)
from kyuura_engine import engine
from kyuura_engine import resolution
from kyuura_engine.conditions import POISON, SLEEP
from kyuura_engine.effects import AttackEntry, AttackKey, DamageOnly
from kyuura_engine.engine import apply_command_traced, apply_command_with
from kyuura_engine.resolution import codec, contract, events, programs
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import GameState

from tests.helpers import (
    BUTTERFREE, CATERPIE, DODUO, FIGHTING, FIRE, GRASS, H, MACHOP, METAPOD, POTION, PSYCHIC, RATTATA, T, WATER, WEEDLE, apply_kernel,
    build_test_state, two_step_effects, with_coin_results,
)
from tests import legacy_reference
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


# ---------------------------------------------------------------- 入口（v0.16b から経路はない）

# v0.16b で外した v0.13 の経路の名前（engine.py）と旧ダメージ処理境界の実装（effects.py）。戻っていないことを確かめる
REMOVED_ENGINE_NAMES = (
    "Route", "DEFAULT_ROUTE", "apply_command_via", "_use_attack", "_resume_attack", "_finish_attack", "_ko_prevention_offer",
    "_resume_knock_out", "_knock_out_after_attack", "_post_knockout_candidates", "_after_knockouts", "_then_context",
    "_post_knockout_context", "_next_prize_or_judge", "_promotions_after_judge", "_offer_post_knockout", "_resume_post_knockout",
    "_next_promotion_or_end", "_resume_take_prize", "_resume_promote_active", "_end_turn_command", "_end_turn", "_pokemon_check",
    "_resolve", "_resolve_decision", "_take_prize", "_promote_active", "_RESUMERS",
)
REMOVED_EFFECTS_NAMES = (
    "PendingCounterattack", "PendingRetaliation", "_apply_counterattack", "_apply_retaliation", "_require_damage_elements_finished",
    "_skip_heal_of_knocked_out_attacker", "_remove_attacker_counters",
)


class EntryTest(unittest.TestCase):
    """v0.16b: 経路（``Route``）を外し、公開の ``apply_command`` はいつも解決の基盤を使う。解決の設定（先読みの方法・効果の定義の対応表）を
    選ぶ内部の入口は ``engine.apply_command_with``・``apply_command_traced``（v0.15b の ``RouteTest`` の確かめを、経路のない形で引き継ぐ）。"""

    def test_public_apply_command_is_unchanged(self):
        """公開の ``apply_command`` の呼び方（引数）は変えない。内部の入口は公開の API に加えない。v0.13 の経路の名前は残っていない。"""
        self.assertEqual(list(inspect.signature(kyuura_engine.apply_command).parameters), ["state", "command"])
        self.assertIs(kyuura_engine.apply_command, engine.apply_command)
        for name in ("apply_command_with", "apply_command_traced", "resolution", "Route", "apply_command_via"):
            self.assertNotIn(name, kyuura_engine.__all__)
        for name in REMOVED_ENGINE_NAMES:
            with self.subTest(engine=name):
                self.assertFalse(hasattr(engine, name))
        for name in REMOVED_EFFECTS_NAMES:
            with self.subTest(effects=name):
                self.assertFalse(hasattr(kyuura_engine.effects, name))

    def test_settings_are_chosen_explicitly(self):
        """先読みの方法は引数で選ぶ。公開の ``apply_command`` は標準の先読み（``derived``）と同じ結果。知らない方法は ValueError。"""
        state = board(PONYTA_, MACHAMP_)
        command = UseAttack(0, 1)
        public = outcome(lambda s, c: kyuura_engine.apply_command(s, c), state, command)
        for mode in resolution.PREFLIGHT_MODES:
            with self.subTest(mode=mode):
                self.assertEqual(outcome(apply_command_with, state, command, preflight=mode), public)
        self.assertEqual(outcome(apply_command_with, state, command), public)
        with self.assertRaises(ValueError):
            apply_command_with(state, command, preflight="fast")

    def test_preflight_modes_give_the_same_result(self):
        """どの先読みの方法も同じ結果。解決の記録は先読みの方法を記録する。"""
        state = board({**PONYTA_, "damage": 30}, {**MACHAMP_, "damage": 80})  # C18 で止まる
        accepted = board(PONYTA_, MACHAMP_)
        for sample, command in ((state, UseAttack(0, 1)), (accepted, UseAttack(0, 1)), (accepted, EndTurn(0))):
            results = [outcome(apply_command_with, sample, command, preflight=mode) for mode in resolution.PREFLIGHT_MODES]
            self.assertTrue(all(result == results[0] for result in results))
        for mode in resolution.PREFLIGHT_MODES:
            _, trace = apply_command_traced(accepted, UseAttack(0, 1), preflight=mode)
            self.assertEqual([e.mode for e in trace.of(events.PreflightResult)], [mode])

    def test_no_module_state_changes(self):
        """設定を選んでも、モジュールの値は変わらない（グローバルな可変フラグで切り替えない）。"""
        names = dict(vars(engine))
        resolution_names = dict(vars(resolution))
        for mode in resolution.PREFLIGHT_MODES:
            apply_command_with(board(PONYTA_, MACHAMP_), UseAttack(0, 1), preflight=mode)
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

    def test_out_of_scope_handlers_do_not_use_the_kernel(self):
        """範囲外のコマンドの処理（engine.py のトレーナー・特殊能力・進化・にげる・エネルギー・対戦準備）は解決の基盤を使わない。
        ``resolution`` を使うのは、入口と振り分け（型の注釈を含む）だけ（v0.15b の「v0.13 の経路の処理は解決の基盤を使わない」の引き継ぎ）。
        v0.42: 特殊能力の処理のあとのきぜつ・サイド・勝ち負け・バトル場に出す（p.323 の手順）は、ワザのあとと同じ解決の基盤の処理を使う
        （``resolution.after_power``。docs/power-decisions-v0.42.md）。特殊能力の処理が使う解決の基盤の名前は、その入口と型の注釈
        （``resolution.Context``）だけで、特殊能力そのものの処理（宣言・確認・``resolve``・``resume``）は engine.py と effects.py のまま。
        v0.47: なにかの化石・ピッピ人形を場からすてる操作（``_discard_from_play``）も、空いたバトル場の勝ち負け・バトル場に出す決定に同じ
        ``resolution.after_power`` を使う（きぜつはない。docs/fossil-hidden-info-v0.47.md 2.4 節）。すてる処理そのものは engine.py と zones.py のまま。
        v0.49: 決定への答えを状態の複製の上で試す確かめ（``_decision_has_unstopped_answer``・``_trainer_dead_end``。答えのない決定を残さない。
        docs/virtual-attacks-transformation-v0.49.md 7.1 節）は、答えの処理を決定への答えの入口（``_HANDLERS[ResolveDecision]``）に渡し、解決の基盤の名前は
        型の注釈（``resolution.Context``）だけを使う（答えの一覧は ``resolution.programs.all_answers`` を読み込む）。
        v0.50: トレーナーの使用（``_play_trainer``・``_resume_trainer``）のあと、退化スプレーで最大HPがのっているダメージ以下になったポケモンのきぜつ・サイド・
        勝ち負け・バトル場に出す（p.323 の手順）は、特殊能力のあとと同じ解決の基盤の処理を使う（``_finish_trainer`` の ``resolution.after_trainer``。
        ``TrainerEffect.may_knock_out`` の実装だけ。docs/mew-devolution-spray-v0.50.md 4 章）。トレーナーの処理そのもの（確認・``resolve``・``resume``）は
        engine.py と effects.py のまま。
        v0.56: ロケット団員の「うら」（使い終えてトラッシュしてから番を終える）は、ワザのあとの番の終わりと同じ解決の基盤の処理を使う（``_finish_trainer`` の
        ``resolution.end_turn_after_trainer``。ログ ``trainer_turn_end`` → 番の終わり → ポケモンチェック → 次の番。``TrainerEffect.may_end_turn`` の実装が ``resume`` で
        ``END_TURN`` を返したときだけ）。マチスの交渉のサイドを取ったあとの勝ち負けの判定は ``resolution.after_trainer``（``takes_prizes``）。
        docs/trainer-decisions-turn-effects-v0.56.md 3 章。
        v0.58: 手札からつけたレインボーエネルギーの 10 ダメージのきぜつは、特殊能力のあとと同じ形の ``resolution.after_energy``（``_attach_energy``）。トレーナーの
        使用の始まりと続き（``_start_trainer_use``・``_after_trainer_step``・``_start_nested_trainer``。サイキックコントロールの内側の使用）は型の注釈
        （``resolution.Context``）だけ。docs/stadium-reuse-special-energy-v0.58.md 2 章・4 章。
        v0.61: 「にげる」のあとの［おとしあな］は ``resolution.after_retreat``（``_retreat``）。docs/reactive-powers-trainer-damage-v0.61.md 3 章。
        v0.62: ワザ以外で受けたことの比べを開くか（``_probes_receipts``）は、ワザの途中の決定の再開先（``resolution.RESUMES``）を読むだけ（解決の基盤の処理を
        呼ばない）。docs/history-attacks-v0.62.md 2.3。"""
        tree = ast.parse((PACKAGE / "engine.py").read_text(encoding="utf-8"))
        functions = [function for function in tree.body if isinstance(function, ast.FunctionDef)]
        users = {
            function.name
            for function in functions
            for node in ast.walk(function) if isinstance(node, ast.Name) and node.id == "resolution"
        }
        self.assertEqual(users, {"_apply", "_context", "apply_command_with", "apply_command_traced", "_answer_decision", "_engine",
                                 "_use_pokemon_power", "_after_power_step", "_resume_power", "_discard_from_play",
                                 "_decision_has_unstopped_answer", "_trainer_dead_end", "_play_trainer", "_resume_trainer", "_finish_trainer",
                                 "_resolve_trainer", "_chaos_tails", "_use_stadium", "_resume_stadium",
                                 "_attach_energy", "_start_trainer_use", "_after_trainer_step", "_start_nested_trainer", "_retreat",
                                 "_probes_receipts"})
        trial_names = {
            node.attr
            for function in functions if function.name in ("_decision_has_unstopped_answer", "_trainer_dead_end")
            for node in ast.walk(function)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "resolution"
        }
        self.assertEqual(trial_names, {"Context"})
        power_names = {
            node.attr
            for function in functions if function.name in ("_use_pokemon_power", "_after_power_step", "_resume_power", "_discard_from_play")
            for node in ast.walk(function)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "resolution"
        }
        self.assertEqual(power_names, {"Context", "after_power"})
        trainer_names = {
            node.attr
            for function in functions if function.name in ("_play_trainer", "_resume_trainer", "_finish_trainer", "_resolve_trainer", "_chaos_tails")
            for node in ast.walk(function)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "resolution"
        }
        self.assertEqual(trainer_names, {"Context", "after_trainer", "end_turn_after_trainer"})
        # v0.57: スタジアムの効果を使う（``_use_stadium``）・その決定への答え（``_resume_stadium``）のあと、空いたバトル場の勝ち負け・バトル場に出す決定は、
        # 特殊能力のあとと同じ形の ``resolution.after_stadium``（セキチクシティジムで対戦ポケモンを山札にもどしたとき。docs/stadiums-v0.57.md 3 章）。スタジアムの効果の処理
        # そのもの（確認・``activate``・``resume_stadium``）は engine.py と effects.py のまま
        stadium_names = {
            node.attr
            for function in functions if function.name in ("_use_stadium", "_resume_stadium")
            for node in ast.walk(function)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "resolution"
        }
        self.assertEqual(stadium_names, {"Context", "after_stadium"})
        # v0.61: 「にげる」（``_retreat``）のあとの相手の［おとしあな］（コイン・20 ダメージ・きぜつ・バトル場に出す）は、特殊能力のあとと同じ形の
        # ``resolution.after_retreat``（docs/reactive-powers-trainer-damage-v0.61.md 3 章）。「にげる」の処理そのもの（確認・トラッシュ・入れ替え）は engine.py のまま
        retreat_names = {
            node.attr
            for function in functions if function.name == "_retreat"
            for node in ast.walk(function)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "resolution"
        }
        self.assertEqual(retreat_names, {"Context", "after_retreat"})

    def test_no_copy_of_the_kernel_remains(self):
        """解決の基盤の実装は ``kyuura_engine/resolution`` だけ（コードの複製がない）。v0.15b〜v0.16c は v0.14 の名前の互換の層
        （``experiments/event_kernel/__init__.py``。``sys.modules`` に同じモジュールを別の名前で登録していた）があったが、v0.16d で外し、
        テスト・道具は本番の部品と内部の入口を直接使う。どのコードも ``experiments`` を読み込まず、本番のモジュールを別の名前で
        ``sys.modules`` に登録しない（読み込んだあとのすべてのモジュールで、登録の名前とモジュールの名前が同じ）。"""
        self.assertFalse((ROOT / "experiments").exists())
        roots = [PACKAGE, ROOT / "tests", ROOT / "tools", ROOT / "scripts"]
        for path in sorted(p for root in roots if root.exists() for p in root.rglob("*.py")):
            with self.subTest(module=path.relative_to(ROOT).as_posix()):
                self.assertFalse([name for name in imports_of(path) if name == "experiments" or name.startswith("experiments.")])
        import sys
        aliases = sorted(name for name, module in list(sys.modules.items())
                         if getattr(module, "__name__", name).startswith("kyuura_engine") and module.__name__ != name)
        self.assertEqual(aliases, [])
        self.assertIn("kyuura_engine.resolution.kernel", sys.modules)  # 解決の基盤のモジュールを読み込んだあとで確かめている


# ---------------------------------------------------------------- コマンドの振り分け


class SubclassedDamage(DamageOnly):
    """テスト専用: 要素の並びの対応表にある実装（DamageOnly）の部分型。対応表は型が完全に一致するものだけなので、親の型の並びとしては
    処理しない。v0.16b から、v0.13 の約束のアダプタ（``resolution.contract``）で ``resolve`` を処理し、``super().resolve`` は親の型の要素の
    並びを今の枠の中で処理する（v0.15 までは v0.13 の経路）。"""

    implementation_id = "test_subclassed_damage"

    def resolve(self, state, use):
        super().resolve(state, use)
        state.add_event("test_subclassed_damage", pokemon_id=use.pokemon_id)


class DispatchTest(unittest.TestCase):
    def test_every_registered_attack_is_handled_by_the_kernel(self):
        """製品の登録表のワザの実装は、どれも要素の並びの対応表にある（v0.13 の約束のアダプタを使うのは、試験の登録表の実装だけ）。"""
        for key in DEFAULT_EFFECTS.attack_keys():
            effect = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).effect
            with self.subTest(attack=str(key)):
                self.assertIn(type(effect), resolution.BUILDERS)
                self.assertFalse(contract.is_contract(resolution.program_for(effect)))

    def test_opponent_effect_elements_come_from_the_program(self):
        """G37 の理由の文に書く効果の要素の種類は、解決の基盤では要素の並びから求める。どの登録されたワザでも、v0.13 の実装の宣言
        （``AttackEffect.opponent_effect_elements``。v0.11）と同じ（G37 の判定と理由の文が、上限を超えたときの v0.13 の止める関数と同じ）。"""
        for key in DEFAULT_EFFECTS.attack_keys():
            effect = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).effect
            with self.subTest(attack=str(key)):
                self.assertEqual(programs.opponent_effect_elements(resolution.compile_attack(effect)), effect.opponent_effect_elements)

    def test_target_commands(self):
        """解決の基盤が処理するのは、ワザ・番の終わり（``resolution.COMMANDS``）と、再開先が ``resolution.RESUMES``（attack・knock_out・
        post_knockout・take_prize・promote_active）の決定への答え。トレーナーの決定（trainer）・特殊能力の途中の決定（power。v0.42）への答えと、
        範囲外のコマンドは engine.py。"""
        self.assertEqual(set(resolution.COMMANDS), {UseAttack, EndTurn})
        self.assertEqual(resolution.RESUMES, {"attack", "knock_out", "post_knockout", "take_prize", "promote_active"})
        self.assertEqual(engine.DECISION_RESUMES, resolution.RESUMES | {"trainer", "power", "stadium"})  # v0.57: スタジアムの効果の途中の決定（stadium）
        for command in (UseAttack, EndTurn):
            self.assertIs(engine._HANDLERS[command], resolution.handle)
        waiting = kyuura_engine.apply_command(board(PONYTA_, {**GIOVANNI_, "damage": 80}), UseAttack(0, 1))  # こんじょうの決定（knock_out）
        self.assertEqual(waiting.decision.resume, codec.KNOCK_OUT)
        _, trace = apply_command_traced(waiting, ResolveDecision(1, waiting.decision.id, ()))
        self.assertTrue(trace.events)  # 解決の基盤が続けた
        potion = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING], "damage": 20}, "hand": [POTION]},
            {"active": RATTATA},
        ])
        potion = kyuura_engine.apply_command(potion, kyuura_engine.PlayTrainer(0, potion.players[0].hand[0]))
        self.assertEqual(potion.decision.resume, "trainer")
        _, trace = apply_command_traced(potion, ResolveDecision(0, potion.decision.id, (potion.decision.options[0],)))
        self.assertEqual(trace.events, [])  # トレーナーの決定は engine.py が続ける（解決の記録は空）

    def test_effects_outside_the_table_use_the_v0_13_path(self):
        """対応表にない実装（試験の 2 段階の決定。v0.13 の約束の ``resolve``・``resume``）は、v0.16b から v0.13 の約束のアダプタで解決の基盤が
        処理し、決定の答え（2 段階）も解決の基盤で続く。結果は v0.13 の処理（参照データ。v0.15 までは v0.13 の経路で処理していた）と同じ。"""
        state = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING]}, "bench": [RATTATA]},
            {"active": RATTATA, "bench": [RATTATA]},
        ], effects=two_step_effects())
        self.assertTrue(contract.is_contract(resolution.program_for(state.effects.attack_entry(MACHOP, 0).effect)))
        # v0.13 の処理の結果は参照データ（tests/legacy_reference.py。v0.16a）
        expected = legacy_reference.expected(self, state, UseAttack(0, 0))
        kernel = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(("ok", legacy_reference.digest(kernel)), expected)
        for step in range(2):
            decision = kernel.decision
            command = ResolveDecision(0, decision.id, (decision.options[0],))
            self.assertEqual(decision.resume, codec.ATTACK)
            expected = legacy_reference.expected(self, kernel, command)
            kernel = apply_kernel(kernel, command)
            self.assertEqual(("ok", legacy_reference.digest(kernel)), expected)
        self.assertEqual([e["kind"] for e in kernel.log if e["kind"] == "test_two_step"], ["test_two_step"])

    def test_subclass_of_a_table_entry_is_not_compiled(self):
        """対応表の型の部分型は、親の型の並びとしては処理しない（部分型の resolve をアダプタで使う。v0.16b。v0.15 までは v0.13 の経路）。
        ``super().resolve`` は親の型の要素の並び。結果は v0.13 の処理と同じ（参照データ）。"""
        effects = DEFAULT_EFFECTS.with_attacks("test-subclass", {AttackKey(MACHOP, 0): AttackEntry(SubclassedDamage(), "けたぐり")})
        state = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING]}, "bench": [RATTATA]},
            {"active": RATTATA, "bench": [RATTATA]},
        ], effects=effects)
        self.assertTrue(contract.is_contract(resolution.program_for(SubclassedDamage())))
        expected = legacy_reference.expected(self, state, UseAttack(0, 0))  # v0.13 の処理の結果（参照データ。v0.16a）
        new = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(("ok", legacy_reference.digest(new)), expected)
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
        """原典で決められない場合に止めるときの例外の種類・コード・理由の文が、v0.13 の経路と同じ（2 つの先読みとも）。v0.13 の経路の
        結果は参照データ（tests/legacy_reference.py。v0.16a）。"""
        stopped = 0
        for name, make, command in self.cases():
            with self.subTest(case=name):
                self.assertEqual(check_invariants(make()), [])
                expected = legacy_reference.expected(self, make(), command)
                stopped += expected[0] == "error"
                for mode in resolution.PREFLIGHT_MODES:
                    self.assertEqual(legacy_reference.outcome_of(apply_kernel, make(), command, preflight=mode), expected, mode)
        self.assertGreaterEqual(stopped, 30)

    def test_refused_chain_names_the_assumption(self):
        """返すダメージで返す効果がはたらく壊れた盤面（v0.13 の S45）は、解決の基盤でも番の進み方の前提を書いた RuntimeError で止まる。"""
        state = build_test_state([
            {"active": {**DARK_, "energy": [WATER], "retaliation_received": TURN - 1}, "bench": [RATTATA]},
            {"active": {**DARK_, "retaliation_received": TURN - 1}, "bench": [PONYTA_["card"]]},
        ], turn_number=TURN)
        before = full(state)
        with self.assertRaisesRegex(RuntimeError, "番の進み方の前提"):  # v0.15 までは v0.13 の経路も同じ前提の RuntimeError
            apply_kernel(with_coin_results(state, H, H), UseAttack(0, 0))
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
                with patch, self.assertRaises(RuntimeError) as ctx:
                    apply_kernel(state, command, preflight=mode)
                self.assertIn("注入した誤り", str(ctx.exception))  # 差しかえた所を処理が通った（v0.16d）
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
        no_preflight.enter_context(mock.patch("kyuura_engine.resolution.v013_checks.check", lambda *args, **kwargs: None))
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
