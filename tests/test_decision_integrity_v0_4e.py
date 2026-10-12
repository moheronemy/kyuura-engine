"""保留中の決定（PendingDecision）の整合性の監査（v0.4e。docs/integration-audit-v0.4e.md 7 章）。

- 複数段階の決定で、段階ごとに決定するプレイヤーが変わる場合（1 段階目はワザを使ったプレイヤー、2 段階目は相手）を、テスト専用の
  効果で確かめる（製品の登録表には入れない。複数段階の決定が要る実在のカードは加えていない）。番のプレイヤー・番の番号は
  変わらず、決定を待つ間はその決定への正しい答えだけを受け付け、答えは乱数を使わず、ワザのあとの処理は 1 回だけ。
- 決定を待つ状態の複製（``clone``・``copy.deepcopy``・``pickle``）: 1 段階目・2 段階目・相手の決定（ふきとばし）・サイドを取る・
  バトル場に出すの各決定で、複製に答えても元は変わらず、同じ答えなら同じ結果になる。
- 決定の種類と答えのコマンドの組み合わせ: v0.1 の ``TakePrize``・``PromoteActive`` は、それぞれの段階の決定にだけ使える
  （ほかの決定を待つ間は ``WRONG_PHASE``）。

根拠: p.309「ワザを使っている最中に、他のことをしてはいけません」・p.310（トレーナーも同じ）・p.312・p.313・p.323（サイド・
交代）・p.19・p.213（ふきとばしで入れ替わるポケモンは相手が選ぶ）。kyuura NEO-2000-OFFICIAL-RULES。
"""

import copy
import pickle
import unittest

from kyuura_engine import (
    AttachEnergy, EndTurn, EngineError, EvolvePokemon, IllegalActionError, PlayBasicToBench, PlayTrainer, PromoteActive,
    ResolveDecision, Retreat, TakePrize, UseAttack, apply_command, check_invariants, state_to_dict,
)
from kyuura_engine.decisions import push_attack_decision
from kyuura_engine.effects import DEFAULT_EFFECTS, AttackEffect, AttackEntry, AttackKey
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import Phase

from tests.helpers import (
    BILL, BUTTERFREE, CATERPIE, FIGHTING, GRASS, MACHOP, METAPOD, PONYTA, RATTATA, SEEL, build_test_state, uids,
)


class AttackerThenOpponentTestEffect(AttackEffect):
    """テスト専用: 2 段階の決定を出すワザの効果。決定するプレイヤーが段階ごとに違う（実在のワザではない）。

    1. ワザを使ったプレイヤーが、相手の場のポケモンを 1 匹選ぶ（``test_choose_target``）
    2. 相手（ワザを使われた側）が、のせるダメージ 10 か 20 を選ぶ（``test_opponent_amount``）
    選んだポケモンに、選んだダメージをそのままのせる（計算しない。テスト専用）。決定の形は ``decision_problems`` で宣言する
    （v0.4d の考え方。宣言しなければ、既定の「決定するのはワザを使ったプレイヤー」で 2 段階目が不変条件の違反になる）。
    """

    implementation_id = "test_attacker_then_opponent"

    def resolve(self, state, use):
        targets = [pokemon.pokemon_id for pokemon in state.players[1 - use.player].in_play()]
        push_attack_decision(state, use, kind="test_choose_target", player=use.player, options=targets, context=(("step", 1),))

    def resume(self, state, use, decision, choices):
        if decision.context_value("step") == 1:
            push_attack_decision(state, use, kind="test_opponent_amount", player=1 - use.player, options=(10, 20),
                                 context=(("step", 2), ("target", choices[0])))
            return
        _, pokemon = state.find_pokemon(decision.context_value("target"))
        pokemon.damage += choices[0]
        state.add_event("test_opponent_amount", target=pokemon.pokemon_id, amount=choices[0])

    def decision_problems(self, state, use, decision):
        step = decision.context_value("step")
        expected = {1: ("test_choose_target", use.player), 2: ("test_opponent_amount", 1 - use.player)}.get(step)
        if expected is None or (decision.kind, decision.player) != expected:
            return [f"テスト専用の決定の段階 {step!r} の種類・決定するプレイヤー {(decision.kind, decision.player)} が {expected} ではない"]
        return []


class UndeclaredOpponentStepTestEffect(AttackerThenOpponentTestEffect):
    """テスト専用: 相手が決定する段階を ``decision_problems`` で宣言しない（既定の確認のまま）。"""

    implementation_id = "test_undeclared_opponent_step"

    def decision_problems(self, state, use, decision):
        return AttackEffect.decision_problems(self, state, use, decision)


def effects(effect):
    return DEFAULT_EFFECTS.with_attacks("test-decision-integrity", {AttackKey(MACHOP, 0): AttackEntry(effect, "けたぐり")})


def board(effect=None, *, opponent_active=None, opponent_bench=(PONYTA,)):
    """ワンリキー（けたぐり = テスト専用の効果）の番。相手の場: バトル場とベンチ。手札にマサキ・エネルギー・たねポケモン・進化カード。"""
    return build_test_state([
        {"active": {"card": MACHOP, "energy": [FIGHTING]}, "bench": [RATTATA], "hand": [BILL, FIGHTING, SEEL, METAPOD]},
        {"active": opponent_active or {"card": RATTATA}, "bench": list(opponent_bench)},
    ], turn_number=5, effects=effects(effect or AttackerThenOpponentTestEffect()))


def full(state):
    return state_to_dict(state, format_version=8)


def other_commands(state):
    """決定を待つ間に送るほかの操作（番のプレイヤー・相手プレイヤーの両方から）。"""
    p = state.players[0]
    commands = [
        EndTurn(0), EndTurn(1), UseAttack(0, 0), UseAttack(1, 0), PlayTrainer(0, uids(state, 0, "hand", BILL)[0]),
        AttachEnergy(0, uids(state, 0, "hand", FIGHTING)[0], p.active.card), PlayBasicToBench(0, uids(state, 0, "hand", SEEL)[0]),
        EvolvePokemon(0, uids(state, 0, "hand", METAPOD)[0], p.active.pokemon_id),
        Retreat(0, (), p.bench[0].card), TakePrize(0, 0), TakePrize(1, 0),
        PromoteActive(1, state.players[1].bench[0].card) if state.players[1].bench else PromoteActive(1, 0),
    ]
    return commands


class TwoPlayerMultiStepDecisionTest(unittest.TestCase):
    def assert_rejected(self, state, command, code):
        before, fingerprint, log = full(state), rng_fingerprint(state.rng), state.log
        with self.assertRaises(EngineError) as ctx:
            apply_command(state, command)
        self.assertEqual(ctx.exception.code, code, command)
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
        self.assertIs(state.log, log)

    def test_steps_change_the_deciding_player_but_not_the_turn(self):
        state = board()
        fingerprint = rng_fingerprint(state.rng)
        first = apply_command(state, UseAttack(0, 0))
        d1 = first.decision
        self.assertEqual((first.phase, d1.kind, d1.player, first.current_player, first.turn_number),
                         (Phase.DECISION, "test_choose_target", 0, 0, 5))
        self.assertEqual(check_invariants(first), [])
        target = first.players[1].active.pokemon_id
        second = apply_command(first, ResolveDecision(0, d1.id, (target,)))
        d2 = second.decision
        self.assertEqual((second.phase, d2.kind, d2.player, d2.id, second.current_player, second.turn_number),
                         (Phase.DECISION, "test_opponent_amount", 1, d1.id + 1, 0, 5))
        self.assertEqual(check_invariants(second), [])
        done = apply_command(second, ResolveDecision(1, d2.id, (10,)))
        self.assertEqual((done.phase, done.current_player, done.turn_number), (Phase.MAIN, 1, 6))
        self.assertEqual(done.players[1].active.damage, 10)
        kinds = [e["kind"] for e in done.log[len(state.log):]]
        self.assertEqual((kinds.count("attack"), kinds.count("turn_end"), kinds.count("pokemon_check")), (1, 1, 1))
        self.assertEqual(rng_fingerprint(done.rng), fingerprint)  # 決定への答えは乱数を使わない

    def test_wrong_answers_at_each_step(self):
        first = apply_command(board(), UseAttack(0, 0))
        d1 = first.decision
        target = first.players[1].active.pokemon_id
        for command, code in (
            (ResolveDecision(1, d1.id, (target,)), "NOT_YOUR_DECISION"),
            (ResolveDecision(0, d1.id + 1, (target,)), "WRONG_DECISION"),
            (ResolveDecision(0, d1.id, (first.players[0].active.pokemon_id,)), "INVALID_CHOICE"),
            (ResolveDecision(0, d1.id, ()), "INVALID_CHOICE_COUNT"),
            (ResolveDecision(0, d1.id, (target, target)), "INVALID_CHOICE_COUNT"),
            (ResolveDecision(2, d1.id, (target,)), "INVALID_PLAYER"),
        ):
            self.assert_rejected(first, command, code)
        second = apply_command(first, ResolveDecision(0, d1.id, (target,)))
        d2 = second.decision
        for command, code in (
            (ResolveDecision(0, d2.id, (10,)), "NOT_YOUR_DECISION"),  # ワザを使ったプレイヤーは 2 段階目を決定しない
            (ResolveDecision(0, d1.id, (target,)), "NOT_YOUR_DECISION"),
            (ResolveDecision(1, d1.id, (target,)), "WRONG_DECISION"),  # 1 段階目の番号（閉じた決定）にはもう答えられない
            (ResolveDecision(1, d2.id, (30,)), "INVALID_CHOICE"),
            (ResolveDecision(1, d2.id, (10, 20)), "INVALID_CHOICE_COUNT"),
        ):
            self.assert_rejected(second, command, code)

    def test_other_commands_wait_at_each_step(self):
        first = apply_command(board(), UseAttack(0, 0))
        second = apply_command(first, ResolveDecision(0, first.decision.id, (first.players[1].active.pokemon_id,)))
        for state in (first, second):
            for command in other_commands(state):
                with self.subTest(step=state.decision.kind, command=type(command).__name__, player=command.player):
                    self.assert_rejected(state, command, "WRONG_PHASE")

    def test_undeclared_opponent_step_is_an_integrity_error(self):
        """相手が決定する段階を宣言しない効果は、2 段階目を出した時点で不変条件の違反（StateIntegrityError）。番のプレイヤーが
        答えるべき決定だと既定の確認が見るため（v0.4d の decision_problems の役割）。"""
        from kyuura_engine.errors import StateIntegrityError

        first = apply_command(board(UndeclaredOpponentStepTestEffect()), UseAttack(0, 0))
        with self.assertRaises(StateIntegrityError):
            apply_command(first, ResolveDecision(0, first.decision.id, (first.players[1].active.pokemon_id,)))

    def test_knock_out_after_the_second_step_then_prize_and_promotion(self):
        """2 段階目のあとで相手の対戦ポケモンがきぜつしたら、ワザのあとの処理（サイド → 交代 → 番の終わり）が 1 回だけ続く（p.323）。"""
        state = board(opponent_active={"card": RATTATA, "damage": 10})
        first = apply_command(state, UseAttack(0, 0))
        second = apply_command(first, ResolveDecision(0, first.decision.id, (first.players[1].active.pokemon_id,)))
        prize = apply_command(second, ResolveDecision(1, second.decision.id, (20,)))
        self.assertEqual((prize.phase, prize.decision.player), (Phase.TAKE_PRIZE, 0))
        promote = apply_command(prize, TakePrize(0, 0))
        self.assertEqual((promote.phase, promote.decision.player), (Phase.PROMOTE_ACTIVE, 1))
        done = apply_command(promote, PromoteActive(1, promote.players[1].bench[0].card))
        kinds = [e["kind"] for e in done.log[len(state.log):]]
        self.assertEqual((kinds.count("knock_out"), kinds.count("take_prize"), kinds.count("promote_active"), kinds.count("turn_end")), (1, 1, 1, 1))
        self.assertEqual((done.phase, done.current_player), (Phase.MAIN, 1))


def decision_states():
    """決定を待つ状態の一覧: (名前, 状態, 正しい答え 2 つ（違う結果になるもの。なければ 1 つ）)。"""
    first = apply_command(board(opponent_active={"card": RATTATA, "damage": 10}), UseAttack(0, 0))
    targets = first.decision.options
    second = apply_command(first, ResolveDecision(0, first.decision.id, (targets[0],)))
    prize = apply_command(second, ResolveDecision(1, second.decision.id, (20,)))
    promote = apply_command(prize, TakePrize(0, 0))
    whirlwind = build_test_state([
        {"active": {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}, "bench": [RATTATA]},
        {"active": RATTATA, "bench": [PONYTA, SEEL]},
    ], turn_number=7)
    forced = apply_command(whirlwind, UseAttack(0, 0))
    return (
        ("1 段階目（ワザを使ったプレイヤー）", first, [ResolveDecision(0, first.decision.id, (t,)) for t in targets]),
        ("2 段階目（相手）", second, [ResolveDecision(1, second.decision.id, (a,)) for a in (10, 20)]),
        ("サイドを取る", prize, [TakePrize(0, 0), TakePrize(0, 5)]),
        ("バトル場に出す", promote, [ResolveDecision(1, promote.decision.id, (o,)) for o in promote.decision.options]),
        ("ふきとばし（相手）", forced, [ResolveDecision(1, forced.decision.id, (o,)) for o in forced.decision.options]),
    )


class DecisionCopyTest(unittest.TestCase):
    """決定を待つ状態の複製は、元と状態を共有しない。複製に答えても元は変わらず、同じ答えなら同じ結果（p.309 の再現性）。"""

    def test_copies_at_every_decision(self):
        for name, state, answers in decision_states():
            with self.subTest(decision=name):
                self.assertEqual(check_invariants(state), [])
                original = full(state)
                expected = [full(apply_command(state, answer)) for answer in answers]
                for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
                    self.assertEqual(full(copied), original)
                    results = [full(apply_command(copied, answer)) for answer in answers]
                    self.assertEqual(results, expected)
                    advanced = apply_command(copied, answers[-1])
                    advanced.players[0].hand.clear()  # 複製から進めた状態を書きかえても、元は変わらない
                    self.assertEqual(full(state), original)
                    self.assertEqual(full(copied), original)
                if len(answers) > 1:
                    self.assertNotEqual(expected[0], expected[-1])

    def test_v0_1_answer_commands_only_fit_their_own_phase(self):
        """TakePrize はサイドを取る段階、PromoteActive はバトル場に出す段階だけ。ほかの決定（ワザの途中・ふきとばし）を待つ間は
        段階が違う（WRONG_PHASE）。ResolveDecision はどの決定にも使える。"""
        for name, state, answers in decision_states():
            with self.subTest(decision=name):
                for command in (TakePrize(state.decision.player, 0),
                                PromoteActive(state.decision.player, state.players[state.decision.player].bench[0].card)):
                    fits = (state.phase is Phase.TAKE_PRIZE and isinstance(command, TakePrize)) or (
                        state.phase is Phase.PROMOTE_ACTIVE and isinstance(command, PromoteActive))
                    if fits:
                        apply_command(state, command)
                        continue
                    before = full(state)
                    with self.assertRaises(IllegalActionError) as ctx:
                        apply_command(state, command)
                    self.assertEqual(ctx.exception.code, "WRONG_PHASE")
                    self.assertEqual(full(state), before)


if __name__ == "__main__":
    unittest.main()
