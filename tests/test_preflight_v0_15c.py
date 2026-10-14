"""v0.15c: 宣言の前の先読みの安全性と効率（docs/preflight-optimization-v0.15c.md）。

- 試す範囲の完全さ: コイン（ワザのコイン・こんらんのコイン・「とうめい」のコイン）、ワザの途中の決定のすべての答え（エナジーへんかんの
  カード・ふきとばしの入れ替え先・2 段階の決定）。v0.14 のエナジーへんかんは枚数ごとの代表だけを試していた（3 章）。
- 実際の処理を先に行う ``derived``（v0.15c）が、すべてを先に試す ``derived_full``（v0.14 の方法）・v0.13 の経路と同じ結果（受け付けた状態・
  乱数・拒否の種類・コード・理由の文）になること。試さなかった結果を区別する 4 つの条件（結果が 1 つ・乱数を使わない・決定がない・未解決の
  問いに当たらない）と、実際の処理を 1 回だけ行うこと（状態・コインを二重に変えない）。
- 上限（``MAX_BRANCHES``）: 途中までの結果を使わず、v0.13 の止める関数で確かめたワザは v0.13 の止める関数で、ほかは拒否する（4 章）。

原典で決められない場合の根拠は各裁定の文書（C18: docs/counterattack-v0.10.md・p.324、W24: docs/rocket-moltres-v0.12.md・p.82、
v0.4b: docs/persistent-damage-v0.4b.md・p.321、H4: docs/haunter-line-v0.9.md・p.158。kyuura の NEO-2000-OFFICIAL-RULES）。先読みは裁定を
変えない。盤面は ``build_test_state`` で直接作る（1 か所の規定を確かめるテスト）。テスト専用のワザの要素の並びは、試験のときだけ
``programs.BUILDERS`` に加える。
"""

from __future__ import annotations

import itertools
import pickle
import random
import unittest
from dataclasses import dataclass
from typing import ClassVar
from unittest import mock

from kyuura_engine import DEFAULT_EFFECTS, EngineError, UnsupportedError, UseAttack, check_invariants, state_to_dict
from kyuura_engine import effects as E
from kyuura_engine.effects import AttackEntry, AttackKey
from kyuura_engine.engine import apply_command_traced
from kyuura_engine.resolution import events, programs, v013_checks
from kyuura_engine.rng import rng_fingerprint

from tests.helpers import (
    BUTTERFREE, CATERPIE, DODUO, FIGHTING, FIRE, GASTLY, GRASS, H, MACHOP, METAPOD, PSYCHIC, RATTATA, T, WATER, apply_kernel,
    ATTACK_TYPES_SINCE_V0_17, build_test_state, with_coin_results,
)
from tests import legacy_reference
from tests.test_event_kernel_v0_14 import MACHAMP_, PONYTA_, TURN, UnresolvedTest, board
from tests.test_kernel_integration_v0_15 import MessageTest

COINS = [()] + [sides for count in (1, 2, 3) for sides in itertools.product((H, T), repeat=count)]


def full(state):
    return state_to_dict(state, format_version=9)


def outcome(apply, state, command, **options):
    try:
        new = apply(state, command, **options)
    except EngineError as error:
        return ("rejected", type(error), error.code, error.message)
    return ("ok", full(new), rng_fingerprint(new.rng))


def preflight_results(state, command, mode="derived"):
    _, trace = apply_command_traced(state, command, preflight=mode)
    return trace.of(events.PreflightResult)


def machop_with(effect, opponent=RATTATA, *, discard=(), bench=(RATTATA,), opponent_bench=(RATTATA,), damage=0):
    """ワンリキーの「けたぐり」（説明文のないワザ）をテスト専用の実装に置きかえた盤面。"""
    effects = DEFAULT_EFFECTS.with_attacks("test-preflight", {AttackKey(MACHOP, 0): AttackEntry(effect, "けたぐり")})
    return build_test_state([
        {"active": {"card": MACHOP, "energy": [FIGHTING], "damage": damage}, "bench": list(bench), "discard": list(discard)},
        {"active": opponent, "bench": list(opponent_bench)},
    ], turn_number=TURN, effects=effects)


# ---------------------------------------------------------------- テスト専用の実装と要素


class TestOnlyAttack(E.AttackEffect):
    """テスト専用: 経路 KERNEL の要素の並び（``BUILDERS`` に試験のときだけ加える）で処理するワザ。v0.13 の ``resolve`` は使わない。"""

    implementation_id = "test_preflight_program"

    def __init__(self, program):
        self.program = program

    def resolve(self, state, use):
        raise AssertionError("テスト専用のワザは経路 KERNEL の要素の並びで処理する")


@dataclass(frozen=True)
class AskIf(programs.Element):
    """テスト専用: ``predicate(run)`` が真なら、既知の問い（G37 のキー）に当たる（どの結果で当たるかを決められる要素）。"""

    predicate: object
    phase: ClassVar[programs.Phase] = programs.Phase.EFFECT

    def run(self, run) -> bool:
        if self.predicate(run):
            raise run.res.question("ko_prevention_attack_effect", "テスト専用の問い")
        return False


def program_patch(*classes):
    return mock.patch.dict(programs.BUILDERS, {cls: (lambda e: e.program) for cls in classes})


def water_in_hand(run) -> bool:
    return any(run.state.card_def(uid).id == WATER for uid in run.state.players[run.player].hand)


class ManyCoins(E.CoinFlipDamage):
    """テスト専用: コインの数が多いみだれづき（v0.13 の ``CoinFlipDamage`` の部分型。上限を確かめる）。"""

    implementation_id = "test_many_coins"

    def check(self, attack):
        return []  # テスト専用（説明文のないワザ「けたぐり」に登録する）


def many_coins_patch():
    return mock.patch.dict(programs.BUILDERS, {ManyCoins: lambda e: (programs.Damage(programs.OPP, programs.HeadsTimes(e.coins, e.damage_per_heads)),)})


# ---------------------------------------------------------------- 実際の処理を先に行う derived と、すべてを先に試す derived_full


class EquivalenceTest(unittest.TestCase):
    def test_derived_matches_derived_full_and_the_v0_13_route(self):
        """止める場合・止めない場合の盤面と、コインのいろいろな結果で、``derived``・``derived_full``・v0.13 の経路の結果（受け付けた状態（形式 9。
        ログ・乱数の指紋を含む）・拒否の種類・コード・理由の文）が同じ（試さなかった結果があっても、結果は変わらない）。"""
        compared = 0
        for name, make, command in MessageTest().cases():
            for sides in COINS:
                with self.subTest(case=name, coins=sides):
                    state = with_coin_results(make(), *sides)
                    self.assertEqual(check_invariants(state), [])
                    expected = legacy_reference.expected(self, state, command)  # v0.13 の経路の結果（参照データ。v0.16a）
                    self.assertEqual(legacy_reference.outcome_of(apply_kernel, state, command, preflight="derived"), expected)
                    self.assertEqual(legacy_reference.outcome_of(apply_kernel, state, command, preflight="derived_full"), expected)
                    compared += 1
        self.assertGreater(compared, 900)

    def test_the_real_run_happens_once(self):
        """実際の処理は 1 回だけ（コインを二重に投げない・状態を二重に変えない）。返す状態の乱数は元の型で、保存できる。渡した状態は変わらない。"""
        for state, command in ((board({"card": DODUO, "energy": [FIRE]}, RATTATA), UseAttack(0, 0)),
                               (board({**PONYTA_, "confusion": True}, RATTATA), UseAttack(0, 1)),
                               (board(PONYTA_, MACHAMP_), UseAttack(0, 1))):
            for sides in COINS:
                with self.subTest(attacker=state.players[0].active.card, coins=sides):
                    seeded = with_coin_results(state, *sides)
                    before, fingerprint = full(seeded), rng_fingerprint(seeded.rng)
                    new = apply_kernel(seeded, command)
                    self.assertEqual((full(seeded), rng_fingerprint(seeded.rng)), (before, fingerprint))
                    self.assertIs(type(new.rng), random.Random)
                    flips = [e for e in new.log[len(seeded.log):] if e["kind"] == "coin_flip"]
                    draws = new.rng.getstate() != seeded.rng.getstate()
                    # v0.13 の経路と同じ結果（形式 9 の全体。コインのログ・乱数の指紋を含む。参照データ。v0.16a）
                    self.assertEqual(("ok", legacy_reference.digest(new)), legacy_reference.expected(self, seeded, command))
                    self.assertEqual(draws, bool(flips))  # コインを投げたときだけ乱数が進む
                    pickle.loads(pickle.dumps(new))


class StrategyTest(unittest.TestCase):
    """試す範囲（docs 2 章の 4 つの条件）。"""

    def test_single_when_no_coin_no_decision_no_question(self):
        """コインを投げず・決定を出さず・問いに当たらない（結果が 1 つ）なら、状態の複製の上では試さない。"""
        (result,) = preflight_results(board(PONYTA_, MACHAMP_), UseAttack(0, 1))
        self.assertEqual((result.mode, result.strategy, result.branches, result.questions), ("derived", "single", 1, ()))

    def test_siblings_after_coins(self):
        """コインを投げたら、実際の処理のコインの並び以外の結果をすべて試す（みだれづき 2 枚: 実際の 1 つ + 3）。"""
        for sides in itertools.product((H, T), repeat=2):
            with self.subTest(coins=sides):
                (result,) = preflight_results(with_coin_results(board({"card": DODUO, "energy": [FIRE]}, RATTATA), *sides), UseAttack(0, 0))
                self.assertEqual((result.strategy, result.branches), ("siblings", 4))
        (full_result,) = preflight_results(board({"card": DODUO, "energy": [FIRE]}, RATTATA), UseAttack(0, 0), "derived_full")
        self.assertEqual((full_result.strategy, full_result.branches), ("full", 4))

    def test_confusion_coin_is_a_coin(self):
        """こんらんのコインも試す（「うら」ならワザの要素はない。こんらんしたみだれづき: 「うら」1 + 「おもて」4 = 5）。"""
        doduo = {"card": DODUO, "energy": [FIRE], "confusion": True}
        for sides in ((H, H, H), (T,)):
            with self.subTest(coins=sides):
                (result,) = preflight_results(with_coin_results(board(doduo, RATTATA), *sides), UseAttack(0, 0))
                self.assertEqual((result.strategy, result.branches), ("siblings", 5))

    def test_full_when_a_decision_comes_first(self):
        """先読みの範囲で決定を出したら（ふきとばし）、すべての答えを試す（ベンチ 2 匹）。"""
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}
        (result,) = preflight_results(board(butterfree, RATTATA, defender_bench=(RATTATA, DODUO)), UseAttack(0, 0))
        self.assertEqual((result.strategy, result.branches), ("full", 2))

    def test_full_when_the_real_run_hits_a_question(self):
        """実際の処理が問いに当たったら、すべての結果を試してから、``derived_full`` と同じ問いで止める（実際の処理の結果は捨てる）。"""
        for name, (make, command, code) in UnresolvedTest.CASES.items():
            with self.subTest(case=name):
                state = make()
                expected = outcome(apply_kernel, state, command, preflight="derived_full")
                self.assertEqual(outcome(apply_kernel, state, command), expected)
                self.assertEqual(expected[2], code)

    def test_question_found_only_in_a_sibling(self):
        """実際のコインでは当たらず、ほかのコインの結果で当たる（C18。みだれづきの「おもて」2 枚だけでカイリキーがきぜつ）ときは、すべての
        結果を試し直して ``derived_full`` と同じ問い・理由の文で止める。"""
        state = with_coin_results(board({"card": DODUO, "energy": [FIRE], "damage": 40}, {**MACHAMP_, "damage": 80}), T, T)
        expected = outcome(apply_kernel, state, UseAttack(0, 0), preflight="derived_full")
        self.assertEqual(expected[2], "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")
        with self.assertRaises(EngineError):
            apply_command_traced(state, UseAttack(0, 0))
        self.assertEqual(outcome(apply_kernel, state, UseAttack(0, 0)), expected)


# ---------------------------------------------------------------- 試す範囲の完全さ


class CompletenessTest(unittest.TestCase):
    def test_every_recover_energy_answer_is_tried(self):
        """エナジーへんかん（最大 2 枚）は、1 枚以上のすべての答え（選ぶカードと順番）を試す: トラッシュのエネルギー 3 枚なら 3 + 3 × 2 = 9。
        0 枚（H4。決定の答えのときに止める）は宣言の前には試さない。"""
        gastly = {"card": GASTLY, "energy": [PSYCHIC, PSYCHIC]}
        state = build_test_state([
            {"active": gastly, "bench": [RATTATA], "discard": [FIRE, FIRE, WATER]},
            {"active": RATTATA, "bench": [RATTATA]},
        ], turn_number=TURN)
        for mode in ("derived", "derived_full"):
            with self.subTest(mode=mode):
                (result,) = preflight_results(state, UseAttack(0, 1), mode)
                self.assertEqual((result.strategy, result.branches), ("full", 9))
        new = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual((new.decision.min_choices, new.decision.max_choices), (0, 2))  # 0 枚の答えは決定を待つ間に止める（H4）

    def test_a_question_reached_only_by_a_non_representative_answer_is_found(self):
        """最初のカードからの代表（v0.14）では試さない答え（3 枚目の「水」）でだけ当たる問いを、宣言の前に見つける。代表だけを試す方法に
        もどすと見落とす（v0.15c で直したこと）。"""
        attack = TestOnlyAttack((programs.RecoverEnergy(2), AskIf(water_in_hand)))
        state = machop_with(attack, discard=(FIRE, FIRE, WATER))
        before = full(state)
        with program_patch(TestOnlyAttack):
            for mode in ("derived", "derived_full"):
                with self.subTest(mode=mode), self.assertRaises(UnsupportedError) as ctx:
                    apply_kernel(state, UseAttack(0, 0), preflight=mode)
                self.assertEqual(ctx.exception.code, "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT")
            representative = lambda self, run, decision: [tuple(decision.options[:n]) for n in range(1, decision.max_choices + 1)]  # noqa: E731
            with mock.patch.object(programs.RecoverEnergy, "dry_choices", representative):
                apply_kernel(state, UseAttack(0, 0), preflight="derived_full")  # v0.14 の代表だけでは見落として受け付ける
        self.assertEqual(full(state), before)

    def test_two_decisions_are_tried_in_every_combination(self):
        """2 段階の決定（エナジーへんかんの答え × 相手の入れ替え先）は、すべての組を試す（9 × 2 = 18）。組の 1 つ（「水」を手札に加え、
        ドードーと入れ替える）でだけ当たる問いを見つける。"""
        def combination(run):
            active = run.state.players[1 - run.player].active
            return water_in_hand(run) and run.state.card_def(active.card).id == DODUO

        neutral = TestOnlyAttack((programs.RecoverEnergy(2), programs.Damage(programs.OPP, programs.Fixed(10)), programs.ForceSwitch(),
                                  AskIf(lambda run: False)))
        asking = TestOnlyAttack((programs.RecoverEnergy(2), programs.Damage(programs.OPP, programs.Fixed(10)), programs.ForceSwitch(),
                                 AskIf(combination)))
        with program_patch(TestOnlyAttack):
            (result,) = preflight_results(machop_with(neutral, discard=(FIRE, FIRE, WATER), opponent_bench=(RATTATA, DODUO)), UseAttack(0, 0))
            self.assertEqual((result.strategy, result.branches), ("full", 18))
            with self.assertRaises(UnsupportedError) as ctx:
                apply_kernel(machop_with(asking, discard=(FIRE, FIRE, WATER), opponent_bench=(RATTATA, DODUO)), UseAttack(0, 0))
            self.assertEqual(ctx.exception.code, "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT")

    def test_transparency_coin_is_tried(self):
        """「とうめい」のコインも試す（どくばり → ゴースト。「おもて」で受けないとき、そのあとのワザのコインが決められない。T19b）。"""
        make, command, code = UnresolvedTest.CASES["T19b"]
        for sides in ((T, T), (T, H), (H,)):
            with self.subTest(coins=sides):
                with self.assertRaises(UnsupportedError) as ctx:
                    apply_kernel(with_coin_results(make(), *sides), command)
                self.assertEqual(ctx.exception.code, code)


# ---------------------------------------------------------------- 上限


class LimitTest(unittest.TestCase):
    def board(self, coins, defender=RATTATA, **extra):
        return machop_with(ManyCoins(coins=coins, damage_per_heads=10), defender, **extra)

    def test_over_the_limit_without_a_verified_fallback_is_refused(self):
        """13 枚（8,192 通り）は上限（4,096）を超える。v0.13 の止める関数で確かめていない実装は、途中までの結果を使わずに拒否する。"""
        state = self.board(13)
        before, fingerprint = full(state), rng_fingerprint(state.rng)
        with many_coins_patch():
            for mode in ("derived", "derived_full"):
                with self.subTest(mode=mode), self.assertRaises(UnsupportedError) as ctx:
                    apply_kernel(state, UseAttack(0, 0), preflight=mode)
                self.assertEqual(ctx.exception.code, "UNSUPPORTED_PREFLIGHT_LIMIT")
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))

    def test_partial_results_are_not_evidence(self):
        """上限を超えたら、途中までに当たった問いも使わない（C18 に当たる盤面（ワンリキー HP 50・ダメージ 40、カイリキーのダメージ 80。
        「おもて」2 枚以上でカイリキーがきぜつし、はんげきの 10 でワンリキーもきぜつ）でも、確かめていない実装は上限の拒否）。v0.13 の
        止める関数で確かめた実装として扱うと、v0.13 の止める関数（C18）で止める。"""
        state = self.board(13, {**MACHAMP_, "damage": 80}, damage=40)
        with many_coins_patch():
            with self.assertRaises(UnsupportedError) as ctx:
                apply_kernel(state, UseAttack(0, 0))
            self.assertEqual(ctx.exception.code, "UNSUPPORTED_PREFLIGHT_LIMIT")
            with mock.patch.object(v013_checks, "VERIFIED", v013_checks.VERIFIED | {ManyCoins}):
                for mode in ("derived", "derived_full"):
                    with self.subTest(mode=mode), self.assertRaises(UnsupportedError) as ctx:
                        apply_kernel(state, UseAttack(0, 0), preflight=mode)
                    self.assertEqual(ctx.exception.code, "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")

    def test_verified_fallback_accepts_like_the_v0_13_route(self):
        """v0.13 の止める関数で確かめた実装として扱うと、上限を超えても v0.13 の止める関数で確かめ、v0.13 の経路と同じ結果になる。"""
        state = with_coin_results(self.board(13), *([H] * 13))
        with many_coins_patch(), mock.patch.object(v013_checks, "VERIFIED", v013_checks.VERIFIED | {ManyCoins}):
            for mode in ("derived", "derived_full"):
                with self.subTest(mode=mode):
                    self.assertEqual(legacy_reference.outcome_of(apply_kernel, state, UseAttack(0, 0), preflight=mode),
                                     legacy_reference.expected(self, state, UseAttack(0, 0)))  # v0.13 の経路の結果（参照データ。v0.16a）
            (result, fallback) = preflight_results(state, UseAttack(0, 0))
            self.assertEqual((result.strategy, fallback.mode), ("limit", "legacy_after_limit"))

    def test_the_limit_itself_is_allowed(self):
        """12 枚（4,096 通り）はちょうど上限で、すべてを試す。"""
        state = self.board(12)
        with many_coins_patch():
            (result,) = preflight_results(state, UseAttack(0, 0), "derived_full")
            self.assertEqual((result.strategy, result.branches), ("full", 4096))
            (result,) = preflight_results(state, UseAttack(0, 0))
            self.assertEqual((result.strategy, result.branches), ("siblings", 4096))

    def test_verified_implementations_are_the_v0_13_ones(self):
        """上限を超えたときに v0.13 の止める関数で確かめる実装は、v0.13 の 24 種類（製品の登録表のワザの実装）だけ。v0.17 から加えた型
        （``ATTACK_TYPES_SINCE_V0_17``）は入れない（v0.13 の止める関数で確かめていない。上限を超えたら ``UNSUPPORTED_PREFLIGHT_LIMIT``）。"""
        registered = {type(DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect) for k in DEFAULT_EFFECTS.attack_keys()}
        self.assertEqual(v013_checks.VERIFIED, registered - set(ATTACK_TYPES_SINCE_V0_17))
        self.assertEqual(len(v013_checks.VERIFIED), 24)
        self.assertFalse(v013_checks.VERIFIED & set(ATTACK_TYPES_SINCE_V0_17))


if __name__ == "__main__":
    unittest.main()
