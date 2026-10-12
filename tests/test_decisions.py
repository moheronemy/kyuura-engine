"""保留中の決定（v0.2a、M4）。

- サイドを取る・バトル場に出すは、共通の決定（PendingDecision）として出る。v0.1 からある TakePrize・
  PromoteActive は、その決定に答える形（アダプタ）として残っている。
- ResolveDecision は、どの種類の決定にも答えられる。
- 複数段階の決定は、テスト専用の効果（tests/helpers.py の TwoStepTestEffect）で確かめる。
"""

import copy
import pickle
import unittest

from kyuura_engine import (
    AttachEnergy, EndTurn, IllegalActionError, Phase, PromoteActive, ResolveDecision, TakePrize, UseAttack,
    apply_command, check_invariants, state_to_dict,
)
from kyuura_engine.state import PendingDecision

from tests.helpers import (
    FIGHTING, GROWLITHE, HITMONCHAN, MACHOP, PONYTA, SEEL, STARYU, build_test_state, two_step_effects,
)


def knocked_out_state():
    """エビワラーのスペシャルパンチでポニータがきぜつし、サイドを取る決定を待つ状態。"""
    state = build_test_state([
        {"active": {"card": HITMONCHAN, "energy": [FIGHTING, FIGHTING, FIGHTING]}, "bench": [MACHOP]},
        {"active": PONYTA, "bench": [SEEL, GROWLITHE]},
    ])
    return apply_command(state, UseAttack(0, 1))


def two_step_state():
    """テスト専用の 2 段階の効果のワザを使い、1 つ目の決定を待つ状態。"""
    state = build_test_state([
        {"active": {"card": MACHOP, "energy": [FIGHTING]}, "hand": [FIGHTING]},
        {"active": {"card": PONYTA, "damage": 20}, "bench": [SEEL]},
    ], effects=two_step_effects())
    return apply_command(state, UseAttack(0, 0))


class EngineDecisionsTest(unittest.TestCase):
    def test_take_prize_is_a_pending_decision(self):
        state = knocked_out_state()
        d = state.decision
        self.assertIsInstance(d, PendingDecision)
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices, d.resume),
                         ("take_prize", 0, (0, 1, 2, 3, 4, 5), 1, 1, "take_prize"))
        self.assertEqual(state.phase, Phase.TAKE_PRIZE)
        self.assertEqual(state.pending_prizes, {0: 1})  # v0.1 と同じ形の読み取り

    def test_resolve_decision_is_the_same_as_take_prize(self):
        state = knocked_out_state()
        a = apply_command(state, TakePrize(0, 3))
        b = apply_command(state, ResolveDecision(0, state.decision.id, (3,)))
        self.assertEqual(state_to_dict(a), state_to_dict(b))
        self.assertEqual(state_to_dict(a, format_version=2), state_to_dict(b, format_version=2))

    def test_promote_by_pokemon_id_is_the_same_as_by_card_uid(self):
        state = apply_command(knocked_out_state(), TakePrize(0, 0))
        d = state.decision
        bench = state.players[1].bench
        self.assertEqual((d.kind, d.player, d.options), ("promote_active", 1, tuple(p.pokemon_id for p in bench)))
        a = apply_command(state, PromoteActive(1, bench[1].card))
        b = apply_command(state, ResolveDecision(1, d.id, (bench[1].pokemon_id,)))
        self.assertEqual(state_to_dict(a, format_version=2), state_to_dict(b, format_version=2))
        self.assertEqual(a.players[1].active.pokemon_id, bench[1].pokemon_id)

    def test_decision_ids_increase_and_are_not_reused(self):
        state = knocked_out_state()
        first = state.decision.id
        state = apply_command(state, TakePrize(0, 0))
        self.assertGreater(state.decision.id, first)
        state = apply_command(state, PromoteActive(1, state.players[1].bench[0].card))
        self.assertIsNone(state.decision)
        self.assertEqual(state.next_decision_id, first + 2)


class InvalidDecisionTest(unittest.TestCase):
    """不正な決定は受け付けず、状態は変わらない。"""

    def assert_rejected(self, state, command, code):
        before = state_to_dict(state, format_version=2)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, command)
        self.assertEqual(ctx.exception.code, code, command)
        self.assertEqual(state_to_dict(state, format_version=2), before)

    def test_only_the_deciding_player(self):
        state = knocked_out_state()
        self.assert_rejected(state, ResolveDecision(1, state.decision.id, (0,)), "NOT_YOUR_DECISION")
        self.assert_rejected(state, TakePrize(1, 0), "NOT_YOUR_DECISION")

    def test_wrong_decision_id(self):
        state = knocked_out_state()
        self.assert_rejected(state, ResolveDecision(0, state.decision.id + 1, (0,)), "WRONG_DECISION")
        self.assert_rejected(state, ResolveDecision(0, state.decision.id - 1, (0,)), "WRONG_DECISION")

    def test_choice_not_in_options(self):
        state = knocked_out_state()
        self.assert_rejected(state, ResolveDecision(0, state.decision.id, (6,)), "INVALID_CHOICE")
        self.assert_rejected(state, ResolveDecision(0, state.decision.id, (-1,)), "INVALID_CHOICE")

    def test_knocked_out_pokemon_id_cannot_be_chosen(self):
        """きぜつして場を離れたポケモンの番号は、バトル場に出す決定で選べない。"""
        state = build_test_state([
            {"active": {"card": HITMONCHAN, "energy": [FIGHTING, FIGHTING, FIGHTING]}, "bench": [MACHOP]},
            {"active": PONYTA, "bench": [SEEL, GROWLITHE]},
        ])
        ponyta_id = state.players[1].active.pokemon_id
        state = apply_command(apply_command(state, UseAttack(0, 1)), TakePrize(0, 0))
        self.assertIsNone(state.find_pokemon(ponyta_id))
        self.assertNotIn(ponyta_id, state.decision.options)
        self.assert_rejected(state, ResolveDecision(1, state.decision.id, (ponyta_id,)), "INVALID_CHOICE")

    def test_choice_count_and_duplicates(self):
        state = two_step_state()
        d = state.decision
        a, b = d.options
        self.assert_rejected(state, ResolveDecision(0, d.id, ()), "INVALID_CHOICE_COUNT")
        self.assert_rejected(state, ResolveDecision(0, d.id, (a, b, a)), "INVALID_CHOICE_COUNT")
        self.assert_rejected(state, ResolveDecision(0, d.id, (a, a)), "DUPLICATE_CHOICE")
        self.assert_rejected(state, ResolveDecision(0, d.id, (a, 999)), "INVALID_CHOICE")

    def test_unrelated_commands_while_waiting(self):
        for state in (two_step_state(), knocked_out_state()):
            hand = state.players[0].hand[0] if state.players[0].hand else 0
            for command in (EndTurn(0), UseAttack(0, 0), AttachEnergy(0, hand, state.players[0].active.card)):
                self.assert_rejected(state, command, "WRONG_PHASE")
        state = two_step_state()
        self.assert_rejected(state, TakePrize(0, 0), "WRONG_PHASE")
        self.assert_rejected(state, PromoteActive(0, 0), "WRONG_PHASE")

    def test_resolve_decision_outside_a_decision(self):
        state = build_test_state([{"active": GROWLITHE}, {"active": STARYU}])
        self.assert_rejected(state, ResolveDecision(0, 1, (0,)), "WRONG_PHASE")


class MultiStepDecisionTest(unittest.TestCase):
    """1 つのワザの効果が 2 回の決定を求め、選ばれたら続きから処理を再開する。"""

    def test_two_step_effect_resumes_and_finishes_the_attack(self):
        state = two_step_state()
        self.assertEqual(state.phase, Phase.DECISION)
        first = state.decision
        self.assertEqual((first.kind, first.player, first.resume, first.min_choices, first.max_choices),
                         ("test_choose_targets", 0, "attack", 1, 2))
        ponyta, seel = state.players[1].active, state.players[1].bench[0]
        self.assertEqual(first.options, (ponyta.pokemon_id, seel.pokemon_id))
        self.assertEqual(state.log[-1]["kind"], "attack")  # まだ番は終わっていない

        state = apply_command(state, ResolveDecision(0, first.id, (ponyta.pokemon_id, seel.pokemon_id)))
        second = state.decision
        self.assertEqual((second.kind, second.options, second.context_value("targets")),
                         ("test_choose_amount", (10, 20), (ponyta.pokemon_id, seel.pokemon_id)))
        self.assertEqual(state.phase, Phase.DECISION)
        self.assertGreater(second.id, first.id)

        state = apply_command(state, ResolveDecision(0, second.id, (20,)))
        # 続きを処理した: ポニータ（20 + 20 = HP40）はきぜつ、パウワウは 20 ダメージ。その後サイドを取る決定
        self.assertEqual(state.log[-2]["kind"], "test_two_step")
        self.assertEqual(state.log[-1]["kind"], "knock_out")
        self.assertIsNone(state.players[1].active)
        self.assertEqual(state.players[1].bench[0].damage, 20)
        self.assertEqual((state.phase, state.decision.kind, state.decision.player), (Phase.TAKE_PRIZE, "take_prize", 0))
        state = apply_command(state, TakePrize(0, 0))
        state = apply_command(state, PromoteActive(1, state.players[1].bench[0].card))
        self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 1))

    def test_decision_survives_clone_deepcopy_and_pickle(self):
        state = two_step_state()
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.decision.options[0],)))
        finish = ResolveDecision(0, state.decision.id, (10,))
        expected = state_to_dict(apply_command(state, finish), format_version=2)
        for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            self.assertEqual(copied.decision, state.decision)
            self.assertEqual(state_to_dict(apply_command(copied, finish), format_version=2), expected)


class UpToChoicesTest(unittest.TestCase):
    def test_max_choices_may_exceed_the_number_of_options(self):
        """「2 匹まで選ぶ」決定で、選べるものが 1 つしかなくてもよい（選べる数は選べるものの数までになる）。

        でたらめな答えの検査（RandomAnswersTest）で見つけた不変条件の誤り（max_choices が選べるものの数を
        超えると状態が壊れていると判定していた）の再現テスト。
        """
        state = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING]}},
            {"active": PONYTA},  # 相手の場のポケモンは 1 匹だけ
        ], effects=two_step_effects())
        state = apply_command(state, UseAttack(0, 0))
        d = state.decision
        self.assertEqual((len(d.options), d.max_choices), (1, 2))
        self.assertEqual(check_invariants(state), [])
        state = apply_command(state, ResolveDecision(0, d.id, d.options))
        self.assertEqual(state.decision.kind, "test_choose_amount")


class DecisionInvariantTest(unittest.TestCase):
    def assert_detects(self, state, fragment):
        problems = check_invariants(state)
        self.assertTrue(any(fragment in p for p in problems), problems)

    def test_inconsistent_decisions_are_detected(self):
        base = knocked_out_state()
        d = base.decision
        cases = [
            (lambda s: setattr(s, "phase", Phase.MAIN), "決定が残っている"),
            (lambda s: setattr(s, "phase", Phase.PROMOTE_ACTIVE), "段階"),
            (lambda s: setattr(s, "decision", PendingDecision(d.id, d.kind, d.player, (0, 1), 1, 1, d.resume)), "サイドの枚数"),
            (lambda s: setattr(s, "decision", PendingDecision(d.id, d.kind, d.player, d.options, 1, 1, "nowhere")), "再開先"),
            (lambda s: setattr(s, "decision", PendingDecision(s.next_decision_id, d.kind, d.player, d.options, 1, 1, d.resume)), "決定の番号"),
            (lambda s: setattr(s, "decision", PendingDecision(d.id, d.kind, d.player, d.options, 2, 1, d.resume)), "選ぶ数"),
            (lambda s: setattr(s, "decision", PendingDecision(d.id, d.kind, d.player, d.options, 7, 7, d.resume)), "選ぶ数"),
        ]
        for mutate, fragment in cases:
            state = base.clone()
            mutate(state)
            self.assert_detects(state, fragment)


if __name__ == "__main__":
    unittest.main()


class RandomAnswersTest(unittest.TestCase):
    """決定を待つ間に、でたらめな答え（番号・プレイヤー・選択）を送っても、状態は壊れない。"""

    def test_random_answers_never_break_the_state(self):
        import random

        from kyuura_engine import EngineError, new_game
        from kyuura_engine.cards import pool_from_extract, read_extract
        from kyuura_engine.errors import StateIntegrityError

        from tests.helpers import FIRE_DECK, WATER_FIGHTING_DECK, scripted_command

        pool = pool_from_extract(read_extract(), two_step_effects())
        decisions_seen = 0
        for seed in range(8):
            rng = random.Random(seed)
            state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, seed, pool=pool)
            for _ in range(800):
                if state.phase.value in ("game_over", "halted", "sudden_death"):
                    break
                d = state.decision
                if d is not None and (d.kind.startswith("test_") or rng.random() < 0.5):
                    decisions_seen += 1
                    pool_of_values = list(d.options) + [-1, 0, 99, d.options[0] if d.options else 1]
                    command = ResolveDecision(rng.choice([d.player, d.player, 1 - d.player]),
                                              rng.choice([d.id, d.id, d.id - 1, d.id + 1]),
                                              tuple(rng.choice(pool_of_values) for _ in range(rng.randint(0, 3))))
                else:
                    command = scripted_command(state, janken_winner=seed % 2)
                before = state_to_dict(state, format_version=2)
                try:
                    state = apply_command(state, command)
                except StateIntegrityError:
                    raise
                except EngineError:
                    self.assertEqual(state_to_dict(state, format_version=2), before)
                    continue
                self.assertEqual(check_invariants(state), [])
        self.assertGreater(decisions_seen, 50)


class CorruptedDecisionStateTest(unittest.TestCase):
    def test_decision_phase_without_decision_is_an_integrity_error(self):
        from kyuura_engine.errors import StateIntegrityError

        state = knocked_out_state().clone()
        state.decision = None  # 呼び出し側が書き換えた
        for command in (TakePrize(0, 0), ResolveDecision(0, 1, (0,))):
            with self.assertRaises(StateIntegrityError):
                apply_command(state, command)
