"""v0.16b: v0.13 の約束で書いたワザの実装のアダプタ（kyuura_engine/resolution/contract.py。docs/kernel-consolidation-v0.16b.md 3 章）。

v0.16b で v0.13 の経路を外したあとも、``AttackEffect.resolve``・``resume`` の約束で書いたワザの実装（テスト・外の登録表の実装）を解決の基盤が
処理することを確かめます。

- どの実装に使うか: 対応表（``programs.BUILDERS``）の型は要素の並び、v0.13 の約束で処理できる実装だけアダプタ、どちらでもなければ状態を
  変える前に ``UNSUPPORTED_ATTACK``（黙って効果のないワザとして処理しない）。
- 補助関数は解決の基盤の部品に委ねるので、ダメージ・ダメージを受けたときの効果（はんげき）は、標準のワザと同じ窓を通り、同じログになる。
  順番（送る効果はダメージ以外の効果の前。p.89）を守らない実装は止める。
- 宣言の前の確認は実装の宣言（``problem`` と v0.13 の止める関数）で、``resolve`` は 1 回だけ呼ぶ（先読みの方法によらない）。
- 決定（2 段階・保存と復元）・標準の実装の部分型（``super().resolve``・既定の ``resume``）。
- 枠の外で補助関数を呼ぶと ``RuntimeError``。

盤面は ``build_test_state`` で直接作る（1 か所の規定を確かめるテスト。ワザはテスト専用で、製品の登録表には入れない）。
"""

from __future__ import annotations

import copy
import pickle
import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS, EngineError, ResolveDecision, UnsupportedError, UseAttack, apply_command, load_card_pool, state_to_dict,
)
from kyuura_engine.coins import flip_coins
from kyuura_engine.conditions import SLEEP
from kyuura_engine.decisions import push_attack_decision
from kyuura_engine.effects import (
    OPPONENT_ACTIVE, AttackEffect, AttackEntry, AttackKey, AttackUse, DamageAndForceSwitch, DamageOnly, attack_reaches, damage_opponent_active,
    deal_attack_damage, finish_damage_elements,
)
from kyuura_engine.engine import apply_command_traced
from kyuura_engine.resolution import events, open_attack, program_for
from kyuura_engine.resolution.contract import is_contract
from kyuura_engine.rng import rng_fingerprint

from tests.helpers import (
    BUTTERFREE, CATERPIE, FIGHTING, GRASS, H, MACHAMP, MACHOKE, MACHOP, METAPOD, PONYTA, RATTATA, T, build_test_state, coin_events,
    two_step_effects, with_coin_results,
)

TURN = 7
MACHAMP_ = {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE]}


def full(state):
    return state_to_dict(state, format_version=9)


def registry(effect):
    return DEFAULT_EFFECTS.with_attacks("test-contract", {AttackKey(MACHOP, 0): AttackEntry(effect, "けたぐり")})


def board(effect=None, defender=RATTATA, *, attacker=None, defender_bench=(RATTATA,)):
    """ワンリキー（けたぐり 20 = テスト専用の実装）の番。``effect`` が None なら製品の登録表（けたぐりは DamageOnly）。"""
    return build_test_state([
        {"active": {"card": MACHOP, "energy": [FIGHTING], **(attacker or {})}, "bench": [RATTATA]},
        {"active": defender, "bench": list(defender_bench)},
    ], turn_number=TURN, effects=DEFAULT_EFFECTS if effect is None else registry(effect))


class Jab(AttackEffect):
    """テスト専用（v0.13 の約束）: 相手の対戦ポケモンに 20（けたぐりと同じ量）。"""

    implementation_id = "test_contract_jab"

    def resolve(self, state, use):
        damage_opponent_active(state, use, 20)


class NoResolve(AttackEffect):
    """テスト専用: 要素の並びも v0.13 の約束の ``resolve`` も持たない実装。"""

    implementation_id = "test_contract_no_resolve"


class Unchanged(unittest.TestCase):
    def assert_rejected(self, state, command, error, code=None):
        before, fingerprint, log = full(state), rng_fingerprint(state.rng), state.log
        with self.assertRaises(error) as ctx:
            apply_command(state, command)
        if code is not None:
            self.assertEqual(ctx.exception.code, code)
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
        self.assertIs(state.log, log)
        return ctx.exception


class SelectionTest(Unchanged):
    def test_which_implementations_use_the_adapter(self):
        self.assertFalse(is_contract(program_for(DamageOnly())))  # 対応表の型（要素の並び）
        self.assertTrue(is_contract(program_for(Jab())))  # resolve を上書き

        class Subclass(DamageOnly):
            implementation_id = "test_contract_subclass"

        self.assertTrue(is_contract(program_for(Subclass())))  # 対応表の型の部分型（親の要素の並びを枠の中で）
        with self.assertRaises(UnsupportedError) as ctx:
            program_for(NoResolve(), "けたぐり")
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_ATTACK")

    def test_unprocessable_implementation_is_refused_before_anything(self):
        """要素の並びも v0.13 の約束の ``resolve`` もない実装は、宣言・こんらんのコインの前に ``UNSUPPORTED_ATTACK``（黙って効果のない
        ワザとして処理しない。渡した状態・乱数・ログは変わらない）。"""
        for attacker in ({}, {"confusion": True}):
            with self.subTest(attacker=attacker):
                state = with_coin_results(board(NoResolve(), attacker=attacker), T)
                error = self.assert_rejected(state, UseAttack(0, 0), UnsupportedError, "UNSUPPORTED_ATTACK")
                self.assertIn("test_contract_no_resolve", error.message)


class WindowTest(Unchanged):
    def test_helpers_go_through_the_kernel_windows(self):
        """v0.13 の約束の実装の ``damage_opponent_active`` は、標準のけたぐり（DamageOnly。要素の並び）と同じ窓を通る: カイリキーの
        「はんげき」（ダメージの要素のあとの窓）・ログ・きぜつの判定まで同じ（C1〜。p.89・p.192）。"""
        for defender in (RATTATA, {**MACHAMP_}, {**MACHAMP_, "damage": 90}):
            with self.subTest(defender=defender):
                standard = apply_command(board(None, defender), UseAttack(0, 0))
                adapted = apply_command(board(Jab(), defender), UseAttack(0, 0))
                self.assertEqual(adapted.log, standard.log)
                self.assertEqual([p.active.damage if p.active else None for p in adapted.players],
                                 [p.active.damage if p.active else None for p in standard.players])
                self.assertEqual(adapted.decision, standard.decision)

    def test_effects_before_the_deferred_window_are_refused(self):
        """ダメージを受けたときの効果（はんげき）を処理する前に、ダメージ以外の効果に進む実装は止める（順番を黙って変えない。p.89）。
        渡した状態は変わらない。"""

        class SkipsTheWindow(AttackEffect):
            implementation_id = "test_contract_skips_the_window"

            def resolve(self, state, use):
                damage_opponent_active(state, use, 20)
                attack_reaches(state, use, 1 - use.player, state.players[1 - use.player].active, SLEEP)

        self.assert_rejected(board(SkipsTheWindow(), {**MACHAMP_}), UseAttack(0, 0), RuntimeError)

        class Finishes(SkipsTheWindow):
            implementation_id = "test_contract_finishes"

            def resolve(self, state, use):
                damage_opponent_active(state, use, 20)
                finish_damage_elements(state, use)
                attack_reaches(state, use, 1 - use.player, state.players[1 - use.player].active, SLEEP)

        new = apply_command(board(Finishes(), {**MACHAMP_}), UseAttack(0, 0))
        kinds = [e["kind"] for e in new.log]
        self.assertLess(kinds.index("damage"), kinds.index("counterattack"))

    def test_a_different_state_is_refused(self):
        """補助関数に、処理中の状態とは別の状態を渡す実装は止める。"""

        class OtherState(AttackEffect):
            implementation_id = "test_contract_other_state"

            def resolve(self, state, use):
                damage_opponent_active(state.clone(), use, 20)

        self.assert_rejected(board(OtherState()), UseAttack(0, 0), RuntimeError)


class PreflightTest(Unchanged):
    class Counting(AttackEffect):
        implementation_id = "test_contract_counting"

        def __init__(self, calls, problem=None):
            self.calls = calls
            self._problem = problem

        def problem(self, state, use):
            self.calls.append(("problem", len(state.log), rng_fingerprint(state.rng)))
            return self._problem

        def resolve(self, state, use):
            self.calls.append(("resolve", len(state.log)))
            flips = flip_coins(state, use.player, 2, source="attack", effect=str(use.key), card=0)
            damage_opponent_active(state, use, 10 * flips.heads)

    def test_resolve_once_and_contract_checks_whatever_the_preflight_mode(self):
        """``resolve`` は実際の処理で 1 回だけ（状態の複製の上で試さない）。宣言の前の確認は実装の宣言（``problem`` が宣言・乱数の前）で、
        先読みの方法によらない（解決の記録の先読みは ``contract``）。"""
        from kyuura_engine import resolution

        for mode in resolution.PREFLIGHT_MODES:
            for sides in ((H, H), (H, T), (T, T)):
                with self.subTest(mode=mode, sides=sides):
                    calls = []
                    state = with_coin_results(board(self.Counting(calls)), *sides)
                    start, fingerprint = len(state.log), rng_fingerprint(state.rng)
                    new, trace = apply_command_traced(state, UseAttack(0, 0), preflight=mode)
                    self.assertEqual(calls, [("problem", start, fingerprint), ("resolve", start + 1)])
                    self.assertEqual([e.mode for e in trace.of(events.PreflightResult)], ["contract"])
                    self.assertEqual(len(coin_events(new, start)), 2)

    def test_problem_stops_before_the_declaration(self):
        calls = []
        state = board(self.Counting(calls, UnsupportedError("UNRESOLVED_TEST", "テスト専用")))
        self.assert_rejected(state, UseAttack(0, 0), UnsupportedError, "UNRESOLVED_TEST")
        self.assertEqual([c[0] for c in calls], ["problem"])


class DecisionTest(unittest.TestCase):
    def test_two_step_decisions_with_save_and_restore(self):
        """2 段階の決定（tests/helpers.py の TwoStepTestEffect）: 決定の形は v0.13 と同じ（``context`` の最初が ``("use", …)``）。保存と復元
        （pickle・deepcopy）のあとも同じに続き、ワザのあとのきぜつの判定（サイド）まで進む。"""
        state = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING]}, "bench": [RATTATA]},
            {"active": {"card": PONYTA, "damage": 20}, "bench": [RATTATA]},
        ], turn_number=TURN, effects=two_step_effects())
        first = apply_command(state, UseAttack(0, 0))
        d = first.decision
        self.assertEqual((d.kind, d.resume, d.context[0][0], d.context_value("step")), ("test_choose_targets", "attack", "use", 1))
        results = []
        for saved in (first, pickle.loads(pickle.dumps(first)), copy.deepcopy(first)):
            ponyta = saved.players[1].active.pokemon_id
            second = apply_command(saved, ResolveDecision(0, saved.decision.id, (ponyta,)))
            self.assertEqual((second.decision.kind, second.decision.context_value("targets")), ("test_choose_amount", (ponyta,)))
            second = pickle.loads(pickle.dumps(second))
            third = apply_command(second, ResolveDecision(0, second.decision.id, (20,)))
            self.assertEqual(third.decision.kind, "take_prize")  # 40 で HP 以上 → きぜつの処理（解決の基盤）
            self.assertIn("knock_out", [e["kind"] for e in third.log])
            results.append(full(third))
        self.assertTrue(all(result == results[0] for result in results))


class BuiltinTest(unittest.TestCase):
    def test_subclass_without_resolve_uses_the_parent_program(self):
        """標準の実装（ふきとばし。``DamageAndForceSwitch``）の部分型で ``resolve``・``resume`` を上書きしないものは、既定の ``resolve``・
        ``resume`` が親の要素の並び（ダメージ → 相手が選ぶ入れ替え）を枠の中で処理する。結果は標準の実装と同じ。"""

        class Whirl(DamageAndForceSwitch):
            implementation_id = "test_contract_whirl"

        text = load_card_pool().get(BUTTERFREE).attacks[0].text_ja
        effects = DEFAULT_EFFECTS.with_attacks("test-whirl", {AttackKey(BUTTERFREE, 0): AttackEntry(Whirl(), "ふきとばし", text_ja=text)})
        self.assertTrue(is_contract(program_for(Whirl())))

        def run(effects_):
            state = build_test_state([
                {"active": {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}},
                {"active": RATTATA, "bench": [PONYTA, RATTATA]},
            ], turn_number=TURN, effects=effects_)
            waiting = apply_command(state, UseAttack(0, 0))
            self.assertEqual((waiting.decision.kind, waiting.decision.player), ("forced_switch", 1))
            return apply_command(waiting, ResolveDecision(1, waiting.decision.id, (waiting.decision.options[0],)))

        standard, adapted = run(DEFAULT_EFFECTS), run(effects)
        self.assertEqual(adapted.log, standard.log)
        self.assertEqual(adapted.players[1].active.card, standard.players[1].active.card)


class OutsideFrameTest(unittest.TestCase):
    def test_helpers_need_the_kernel_frame(self):
        """解決の基盤のワザの枠の外（``runtime`` のない ``AttackUse``）で補助関数を呼ぶと ``RuntimeError``（解決の基盤を通らずにダメージを
        のせない）。枠（``resolution.open_attack``）の中なら使える。"""
        state = board(None, RATTATA)
        plain = AttackUse(0, state.players[0].active.pokemon_id, AttackKey(MACHOP, 0))
        target = state.players[1].active
        calls = (
            lambda: deal_attack_damage(state, plain, OPPONENT_ACTIVE, 20),
            lambda: damage_opponent_active(state, plain, 20),
            lambda: attack_reaches(state, plain, 1, target, SLEEP),
            lambda: finish_damage_elements(state, plain),
            lambda: push_attack_decision(state, plain, kind="test", player=0, options=(1,)),
            lambda: plain.reception,
            lambda: DamageOnly().resolve(state, plain),
        )
        before = full(state)
        for index, call in enumerate(calls):
            with self.subTest(call=index), self.assertRaises(RuntimeError):
                call()
        self.assertEqual(full(state), before)
        use = open_attack(state, 0)
        self.assertEqual(deal_attack_damage(state, use, OPPONENT_ACTIVE, 20).amount, 40)  # コラッタの弱点（闘 ×2）

    def test_engine_errors_are_not_runtime_errors(self):
        """補助関数の ``RuntimeError`` はエンジン（または実装）の不具合で、プレイヤーの操作の誤り（``EngineError``）とは区別する。"""
        self.assertFalse(issubclass(RuntimeError, EngineError))


if __name__ == "__main__":
    unittest.main()
