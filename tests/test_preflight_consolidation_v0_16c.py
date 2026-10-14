"""v0.16c: 宣言の前の確認の整理（docs/preflight-consolidation-v0.16c.md）。

- 依存（2 章）: v0.13 の止める関数（``effects`` の ``counterattack_double_knockout_problem``・``ko_prevention_attack_effect_problem``・
  ``retaliation_double_knockout_problem`` と、ワザの実装の ``problem``）を呼ぶのは、限定的な互換の部品 ``resolution/v013_checks.py``
  だけ。先読み（``preflight``）・解決の基盤の処理（``kernel``・``programs``）・アダプタ（``contract``）は呼ばない。``v013_checks`` を使う所は
  ``flow._use_attack`` の 3 か所（アダプタの実装・上限を超えたとき・比べるための方法 ``legacy``）だけ。
- 試す結果の数の境界（4 章）: 1・2・16・4,096・4,097 以上・8,192 通りを、コインだけ・決定だけ・コインと決定の組・複数を選ぶ決定・2 段階の
  決定で作り、原典で決められない場合に当たる結果がない・最初の結果だけで当たる・最後の結果だけで当たる場合に、``derived`` と
  ``derived_full`` が同じ答え（受け付ける・問いのコード・``UNSUPPORTED_PREFLIGHT_LIMIT``）になること。上限を超えたら途中までの結果を
  使わないこと（最初の結果で問いに当たっていても、問いのコードにも受け付けにもしない）。拒否で状態・乱数を変えないこと。v0.15c の
  ``derived`` は、ちょうど 4,097 通りのコインだけの木を受け付けていた（実際の処理の結果を上限に数えていなかった。v0.16c で直した）。
- 上限を超えたときの v0.13 の止める関数での確かめ（``VERIFIED``）と、製品のワザが正しい盤面で上限に届かないこと（エナジーへんかん）。

原典で決められない場合の根拠は各裁定の文書（C18: docs/counterattack-v0.10.md・p.324、W24: docs/rocket-moltres-v0.12.md・p.82、
G37: docs/guts-v0.11.md・p.100。kyuura の NEO-2000-OFFICIAL-RULES）。この整理は裁定を変えない。
"""

from __future__ import annotations

import ast
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar
from unittest import mock

from kyuura_engine import UnsupportedError, UseAttack
from kyuura_engine.resolution import preflight, programs, v013_checks
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import PendingDecision

from tests.helpers import GASTLY, PSYCHIC, RATTATA, H, T, apply_kernel, build_test_state, with_coin_results
from tests.test_event_kernel_v0_14 import TURN
from tests.test_kernel_integration_v0_15 import imports_of
from tests.test_preflight_v0_15c import AskIf, TestOnlyAttack, full, machop_with, preflight_results, program_patch

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "kyuura_engine"

# v0.13 の止める関数（v0.13 の engine._use_attack が宣言の前に呼んでいたもの。effects で定義する）
V013_PREDICATES = ("counterattack_double_knockout_problem", "ko_prevention_attack_effect_problem", "retaliation_double_knockout_problem")


def names_used(path: Path) -> set[str]:
    """モジュールの中で使う名前（変数・属性・読み込む名前）。"""
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            found.update(alias.name for alias in node.names)
    return found


def problem_calls(path: Path) -> int:
    """``<何か>.problem(...)`` の呼び出しの数（ワザの実装の宣言の前の確認）。"""
    return sum(
        1 for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "problem"
    )


def check_modes_in_flow() -> list[str]:
    """``flow.py`` の ``v013_checks.check(..., mode=...)`` の呼び出しの方法（並びの順番）。"""
    modes = []
    for node in ast.walk(ast.parse((PACKAGE / "resolution" / "flow.py").read_text(encoding="utf-8"))):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "check"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "v013_checks"):
            (mode,) = [keyword.value for keyword in node.keywords if keyword.arg == "mode"]
            modes.append(mode.value)
    return modes


class DependencyTest(unittest.TestCase):
    def test_only_the_compatibility_module_calls_the_v0_13_predicates(self):
        """v0.13 の止める関数を使う（呼ぶ・読み込む）のは、互換の部品 ``resolution/v013_checks.py`` だけ（定義する ``effects.py`` の中でも
        呼ばない。ほかの本番のコードは、先読み・解決の基盤の問いで確かめる）。"""
        users = {
            path.relative_to(PACKAGE).as_posix()
            for path in PACKAGE.rglob("*.py")
            if names_used(path) & set(V013_PREDICATES)
        }
        self.assertEqual(users, {"resolution/v013_checks.py"})

    def test_only_the_compatibility_module_asks_the_implementation_problem(self):
        """ワザの実装の ``problem``（v0.3c の宣言の前の確認）を呼ぶのも、``effects.py`` の中（実装どうし）と ``v013_checks`` だけ。"""
        users = {path.relative_to(PACKAGE).as_posix() for path in PACKAGE.rglob("*.py") if problem_calls(path)}
        self.assertEqual(users - {"effects.py"}, {"resolution/v013_checks.py"})
        self.assertEqual(problem_calls(PACKAGE / "resolution" / "v013_checks.py"), 1)

    def test_preflight_and_kernel_do_not_use_the_compatibility_module(self):
        """先読み・解決の基盤の処理・アダプタは ``v013_checks`` を読み込まない。読み込むのは振り分け（``flow.py``）だけ。"""
        module = "kyuura_engine.resolution.v013_checks"
        users = {
            path.name for path in (PACKAGE / "resolution").glob("*.py")
            if any(name == module or name.startswith(module + ".") for name in imports_of(path))
        }
        self.assertEqual(users, {"flow.py"})
        engine_imports = imports_of(PACKAGE / "engine.py")
        self.assertFalse([name for name in engine_imports if "v013_checks" in name])

    def test_the_three_uses_are_the_documented_ones(self):
        """``flow._use_attack`` の 3 か所が、それぞれ別の方法（上限を超えたとき・アダプタの実装・比べるための ``legacy``）で使う。"""
        self.assertEqual(sorted(check_modes_in_flow()), sorted(v013_checks.MODES))
        self.assertEqual(len(v013_checks.MODES), 3)

    def test_unknown_mode_is_refused(self):
        """方法の名前を間違えたら、黙って確かめずに進まない。"""
        with self.assertRaises(ValueError):
            v013_checks.check(None, None, None, None, None, mode="derived")



# ---------------------------------------------------------------- 試す結果の数の境界（4 章）

QUESTION = "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT"  # テスト専用の要素 AskIf が当たる問い（G37 のキーを借りる。裁定は変えない）
LIMIT = "UNSUPPORTED_PREFLIGHT_LIMIT"
REAL_RUN_COINS = (H,) + (T,) * 12  # derived の実際の処理のコイン（最初と最後の結果にならないように、1 枚目だけ「おもて」）


@dataclass(frozen=True)
class Flips(programs.Element):
    """テスト専用: ワザ全体のコインを ``count`` 枚投げる（2^count 通り）。"""

    count: int
    phase: ClassVar[programs.Phase] = programs.Phase.NEUTRAL

    def run(self, run) -> bool:
        if self.count:
            run.fs.coins["flips"] = run.flip(self.count)
        return False


@dataclass(frozen=True)
class Lopsided(programs.Element):
    """テスト専用: 1 枚投げ、「おもて」ならさらに ``extra`` 枚投げる（2^extra + 1 通りの偏ったコインの木。``extra`` 12 で 4,097 通り）。"""

    extra: int
    phase: ClassVar[programs.Phase] = programs.Phase.NEUTRAL

    def run(self, run) -> bool:
        first = run.flip(1)
        sides = tuple(first.results)
        if sides[0] is programs.HEADS:
            sides += tuple(run.flip(self.extra).results)
        run.carried["lopsided"] = sides
        return False


@dataclass(frozen=True)
class Pick(programs.Element):
    """テスト専用: ワザを使ったプレイヤーが ``options`` 個から選ぶ決定（``up_to`` 個まで、順番つき。``all_answers`` で 1〜``up_to`` 個）。
    ``only_if_heads`` なら ``Flips`` の 1 枚目が「おもて」のときだけ出す。答えは ``run.carried["picked"]`` に並べる。"""

    options: int
    up_to: int = 1
    only_if_heads: bool = False
    phase: ClassVar[programs.Phase] = programs.Phase.EFFECT
    decision_kind: ClassVar[str] = "test_pick"

    def run(self, run) -> bool:
        if self.only_if_heads and run.fs.coins["flips"].results[0] is not programs.HEADS:
            return False
        run.suspend(kind=self.decision_kind, player=run.player, options=range(self.options), max_choices=self.up_to)
        return True

    def resume(self, run, decision, choices) -> None:
        run.carried["picked"] = run.carried.get("picked", ()) + (tuple(choices),)

    def dry_choices(self, run, decision):
        if self.up_to == 1:
            return OneEach(decision.options)  # all_answers(decision, minimum=1) と同じ並び（作る費用だけを減らす）
        return programs.all_answers(decision, minimum=1)


class OneEach:
    """``all_answers`` の 1 個だけを選ぶ答え ``[(o,) for o in options]`` と同じ並び（先読みは ``len`` と添字だけを使う）。結果ごとに答えの
    一覧を作り直すと、選択肢 n の決定で n² の費用になるので、テストの時間のために使う（``test_one_each_is_all_answers`` が同じことを確かめる）。"""

    def __init__(self, options):
        self.options = tuple(options)

    def __len__(self) -> int:
        return len(self.options)

    def __getitem__(self, index: int) -> tuple:
        return (self.options[index],)


def sides_of(run) -> tuple:
    flips = run.fs.coins.get("flips")
    return (tuple(flips.results) if flips is not None else ()) + run.carried.get("lopsided", ())


def first_result(run) -> bool:
    """深さ優先で最初に試す結果（コインがすべて「うら」、決定の答えがどれも最初の答え ``(0,)``）。"""
    return all(side is programs.TAILS for side in sides_of(run)) and all(answer == (0,) for answer in run.carried.get("picked", ()))


def last_result(last_answers: tuple):
    """深さ優先で最後に試す結果（コインがすべて「おもて」、決定の答えがどれも最後の答え ``last_answers``）。"""
    return lambda run: all(side is programs.HEADS for side in sides_of(run)) and run.carried.get("picked", ()) == last_answers


@dataclass(frozen=True)
class Case:
    name: str
    elements: tuple
    total: int  # 試す結果の数（葉の数）
    last_answers: tuple = ()
    variants: tuple = ("none", "first", "last")

    def program(self, variant: str) -> TestOnlyAttack:
        ask = {"none": lambda run: False, "first": first_result, "last": last_result(self.last_answers)}[variant]
        return TestOnlyAttack(self.elements + (AskIf(ask),))


CASES = (
    # 1 通り
    Case("結果 1（コインも決定もない）", (Flips(0),), 1),
    Case("決定 1（選択肢 1）", (Pick(1),), 1, ((0,),)),
    # 2 通り
    Case("コイン 1 枚", (Flips(1),), 2),
    Case("決定 2", (Pick(2),), 2, ((1,),)),
    Case("コイン 1 枚 × 決定 1", (Flips(1), Pick(1)), 2, ((0,),)),
    # 16 通り
    Case("コイン 4 枚", (Flips(4),), 16),
    Case("決定 16", (Pick(16),), 16, ((15,),)),
    Case("コイン 2 枚 × 決定 4", (Flips(2), Pick(4)), 16, ((3,),)),
    Case("1〜2 個を選ぶ決定（選択肢 4。4 + 4 × 3）", (Pick(4, up_to=2),), 16, ((3, 2),)),
    # 4,096 通り（ちょうど上限）
    Case("コイン 12 枚", (Flips(12),), 4096, (), ("none", "last")),
    Case("決定 4,096", (Pick(4096),), 4096, ((4095,),), ("none", "last")),
    Case("コイン 2 枚 × 決定 1,024", (Flips(2), Pick(1024)), 4096, ((1023,),), ("none", "last")),
    Case("1〜2 個を選ぶ決定（選択肢 64。64 + 64 × 63）", (Pick(64, up_to=2),), 4096, ((63, 62),), ("none",)),
    Case("2 段階の決定 64 × 64", (Pick(64), Pick(64)), 4096, ((63,), (63,)), ("none",)),
    # 4,097 通り以上
    Case("偏ったコインの木（1 + 2^12 = 4,097）", (Lopsided(12),), 4097),
    Case("決定 4,097", (Pick(4097),), 4097, ((4096,),)),
    Case("コイン 1 枚 ×「おもて」だけの決定 4,096（4,097）", (Flips(1), Pick(4096, only_if_heads=True)), 4097, ((4095,),)),
    Case("コイン 2 枚 × 決定 1,025（4,100）", (Flips(2), Pick(1025)), 4100, ((1024,),), ("none",)),
    Case("1〜2 個を選ぶ決定（選択肢 65。4,225）", (Pick(65, up_to=2),), 4225, ((64, 63),), ("none",)),
    # 8,192 通り
    Case("コイン 13 枚", (Flips(13),), 8192, (), ("none", "first")),
    Case("決定 8,192", (Pick(8192),), 8192, ((8191,),), ("none",)),
    Case("コイン 1 枚 × 決定 4,096", (Flips(1), Pick(4096)), 8192, ((4095,),), ("none",)),
    Case("コイン 3 枚 × 決定 1,024", (Flips(3), Pick(1024)), 8192, ((1023,),), ("none", "first")),
)


def case_board(program):
    return with_coin_results(machop_with(program), *REAL_RUN_COINS)


class BranchLimitBoundaryTest(unittest.TestCase):
    def assert_refused(self, state, mode, code):
        before = (full(state), rng_fingerprint(state.rng))
        with self.assertRaises(UnsupportedError) as ctx:
            apply_kernel(state, UseAttack(0, 0), preflight=mode)
        self.assertEqual(ctx.exception.code, code)
        self.assertEqual((full(state), rng_fingerprint(state.rng)), before)  # 拒否で状態・乱数を変えない

    def test_cases_cover_the_requested_counts(self):
        """依頼の数（1・2・16・4,096・4,097 以上・8,192）と組（コイン・決定・コインと決定・複数の選択肢）がそろっている。"""
        totals = {case.total for case in CASES}
        self.assertTrue({1, 2, 16, 4096, 4097, 8192} <= totals)
        self.assertEqual(preflight.MAX_BRANCHES, 4096)

    def test_derived_and_derived_full_agree_at_every_count(self):
        """上限以下なら、問いに当たる結果がなければ受け付けて試した結果の数を残し（``derived`` は実際の処理の結果も数える）、最初・最後の
        どちらの結果だけで当たっても問いのコードで止める。上限を超えたら、問いの有無・位置によらず ``UNSUPPORTED_PREFLIGHT_LIMIT``
        （途中までの結果で当たっていても使わない。上限より後の結果で当たる場合も受け付けない）。どれも ``derived`` と ``derived_full`` が
        同じ。"""
        with program_patch(TestOnlyAttack):
            for case in CASES:
                for variant in case.variants:
                    state = case_board(case.program(variant))
                    for mode in ("derived", "derived_full"):
                        with self.subTest(case=case.name, variant=variant, mode=mode):
                            if case.total > preflight.MAX_BRANCHES:
                                self.assert_refused(state, mode, LIMIT)
                            elif variant != "none":
                                self.assert_refused(state, mode, QUESTION)
                            else:
                                (result,) = preflight_results(state, UseAttack(0, 0), mode)
                                self.assertEqual(result.branches, case.total)
                                self.assertLessEqual(result.branches, preflight.MAX_BRANCHES)

    def test_v0_15c_off_by_one_is_fixed(self):
        """v0.15c の ``derived`` は、コインだけの木（``siblings``）で実際の処理の結果を上限に数えず、ちょうど 4,097 通りを受け付けていた
        （``derived_full`` は拒否）。v0.16c から、実際の処理の結果が「おもて」の側でも「うら」の側でも拒否する。"""
        with program_patch(TestOnlyAttack):
            for real in ((T,), (H,) * 13):
                state = with_coin_results(machop_with(TestOnlyAttack((Lopsided(12),))), *real)
                for mode in ("derived", "derived_full"):
                    with self.subTest(real=real[:1], mode=mode):
                        self.assert_refused(state, mode, LIMIT)
            (result,) = preflight_results(with_coin_results(machop_with(TestOnlyAttack((Flips(12),))), *REAL_RUN_COINS), UseAttack(0, 0))
            self.assertEqual((result.strategy, result.branches), ("siblings", 4096))  # ちょうど上限は、実際の処理を含めて 4,096

    def test_one_each_is_all_answers(self):
        """テスト専用の答えの並び（``OneEach``）は、``all_answers``（1 個だけを選ぶ決定）と同じ。"""
        for n in (1, 2, 16):
            decision = PendingDecision(id=0, kind="test_pick", player=0, options=tuple(range(n)), min_choices=1, max_choices=1,
                                       resume="attack", context=())
            self.assertEqual([OneEach(decision.options)[i] for i in range(len(OneEach(decision.options)))],
                             programs.all_answers(decision, minimum=1))

    def test_strategy_of_the_real_run(self):
        """``derived`` の試す範囲: コインも決定もなければ試さない（``single``）、コインだけなら実際の処理以外（``siblings``）、決定があれば
        すべて（``full``）。どれも試した結果の数は同じ。"""
        expected = {"結果 1（コインも決定もない）": "single", "コイン 4 枚": "siblings", "決定 16": "full", "コイン 2 枚 × 決定 4": "full"}
        with program_patch(TestOnlyAttack):
            for case in CASES:
                if case.name in expected:
                    with self.subTest(case=case.name):
                        (result,) = preflight_results(case_board(case.program("none")), UseAttack(0, 0))
                        self.assertEqual((result.strategy, result.branches), (expected[case.name], case.total))


class VerifiedFallbackTest(unittest.TestCase):
    def test_over_the_limit_uses_the_v0_13_predicates_only_for_verified_types(self):
        """上限を超えたとき、``VERIFIED`` の型なら v0.13 の止める関数で確かめる（解決の記録: 上限 → 方法 ``legacy_after_limit``）。"""
        state = case_board(TestOnlyAttack((Flips(13),)))
        with program_patch(TestOnlyAttack), mock.patch.object(v013_checks, "VERIFIED", v013_checks.VERIFIED | {TestOnlyAttack}):
            (limit, fallback) = preflight_results(state, UseAttack(0, 0))
        self.assertEqual((limit.mode, limit.strategy, fallback.mode, fallback.branches), ("derived", "limit", "legacy_after_limit", 0))

    def test_the_v0_13_predicates_do_not_see_program_questions(self):
        """（負の対照）v0.13 の止める関数は、ワザの実装の宣言（``problem``・``damage_profile``・``opponent_effect_elements``）だけを見て、
        要素の並びの中の問いを見ない。``VERIFIED`` に確かめていない型を入れると、上限を超えた木の、実際の処理が通らなかった結果の問い
        （最後の結果）を見落として受け付ける。だから ``VERIFIED`` を自動で広げない（``test_preflight_v0_15c`` の
        ``test_verified_implementations_are_the_v0_13_ones`` が 24 種類に固定している）。"""
        case = next(case for case in CASES if case.name == "コイン 13 枚")
        state = case_board(case.program("last"))
        with program_patch(TestOnlyAttack):
            with self.assertRaises(UnsupportedError) as ctx:
                apply_kernel(state, UseAttack(0, 0))
            self.assertEqual(ctx.exception.code, LIMIT)  # 正しい VERIFIED では拒否
            with mock.patch.object(v013_checks, "VERIFIED", v013_checks.VERIFIED | {TestOnlyAttack}):
                apply_kernel(state, UseAttack(0, 0))  # 誤って広げると見落とす


def gastly_board(energies: int, *, confused: bool):
    """ゴース（エナジーへんかん。最大 2 枚）と、トラッシュの基本エネルギー ``energies`` 枚（盤面を直接作る）。"""
    gastly = {"card": GASTLY, "energy": [PSYCHIC, PSYCHIC], **({"confusion": True} if confused else {})}
    return build_test_state([
        {"active": gastly, "bench": [RATTATA], "discard": [PSYCHIC] * energies},
        {"active": RATTATA, "bench": [RATTATA]},
    ], turn_number=TURN)


class ProductBoundTest(unittest.TestCase):
    def test_recover_energy_on_a_legal_board_stays_below_the_limit(self):
        """製品のワザでいちばん多いのは、こんらんのゴースのエナジーへんかん（「うら」1 + 「おもて」n²）。60 枚のデッキでトラッシュの
        エネルギーカードは 57 枚以下（ゴースとついているエネルギー 2 枚のほか。サイドを数えない上界）なので 1 + 57² = 3,250 で、上限に
        届かない（上限を超えたときの v0.13 の止める関数での確かめは、正しい盤面では使わない）。"""
        for coin in (H, T):
            state = with_coin_results(gastly_board(57, confused=True), coin)
            for mode in ("derived", "derived_full"):
                with self.subTest(confusion_coin=coin, mode=mode):
                    (result,) = preflight_results(state, UseAttack(0, 1), mode)
                    self.assertEqual(result.branches, 3250)

    def test_recover_energy_reaches_the_limit_only_on_an_impossible_board(self):
        """こんらんでなければ n²: 64 枚で 4,096（ちょうど上限。すべて試す）、65 枚（60 枚のデッキではありえない盤面）で上限を超え、
        ``VERIFIED`` の型なので v0.13 の止める関数で確かめて受け付ける（v0.13・v0.15 と同じ）。"""
        (result,) = preflight_results(gastly_board(64, confused=False), UseAttack(0, 1), "derived_full")
        self.assertEqual((result.strategy, result.branches), ("full", 4096))
        (limit, fallback) = preflight_results(gastly_board(65, confused=False), UseAttack(0, 1))
        self.assertEqual((limit.mode, limit.strategy, fallback.mode, fallback.branches), ("derived", "limit", "legacy_after_limit", 0))


if __name__ == "__main__":
    unittest.main()
