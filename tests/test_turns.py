"""番の進行と自分の番の操作（『オフィシャルブック2000』pp.309〜311）。"""

import unittest

from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, Phase, PlayBasicToBench, PlayTrainer, Retreat,
    UnsupportedError, UseAttack, UsePokemonPower, apply_command, check_invariants, command_from_dict,
    command_to_dict, new_game, state_to_dict,
)

from tests.helpers import (
    DIGLETT, FIGHTING, FIRE, FIRE_DECK, GROWLITHE, HITMONCHAN, MACHOP, PONYTA, RATTATA, STARYU, WATER,
    WATER_FIGHTING_DECK, active, build_test_state, find_seed, finish_setup, place_all,
)


def started_game():
    seed = find_seed(FIRE_DECK, WATER_FIGHTING_DECK, lambda s: s.mulligan_rounds == ())
    state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, seed)
    state = place_all(place_all(state, 0), 1)
    return state


class DrawTest(unittest.TestCase):
    """自分の番が来たら、まず山札から1枚引く。先攻の最初の番も引く（p.309、kyuura first_turn_draw）。"""

    def test_first_player_draws_on_first_turn(self):
        state = started_game()
        hand, deck = len(state.players[1].hand), len(state.players[1].deck)
        state = finish_setup(state, janken_winner=1)
        self.assertEqual(state.turn_number, 1)
        self.assertEqual(len(state.players[1].hand), hand + 1)
        self.assertEqual(len(state.players[1].deck), deck - 1)

    def test_each_turn_starts_with_a_draw(self):
        state = finish_setup(started_game(), janken_winner=0)
        hand, deck = len(state.players[1].hand), len(state.players[1].deck)
        state = apply_command(state, EndTurn(0))
        self.assertEqual((state.current_player, state.turn_number), (1, 2))
        self.assertEqual(len(state.players[1].hand), hand + 1)
        self.assertEqual(len(state.players[1].deck), deck - 1)
        self.assertEqual([e["kind"] for e in state.log[-4:]], ["turn_end", "pokemon_check", "turn_start", "draw"])


class EnergyTest(unittest.TestCase):
    """エネルギーカードは1回の自分の番ごとに1枚だけ（p.310）。"""

    def setUp(self):
        self.state = build_test_state([
            {"active": GROWLITHE, "bench": [PONYTA], "hand": [FIRE, FIRE]},
            {"active": STARYU, "hand": [WATER]},
        ])

    def test_only_one_energy_per_turn(self):
        e1, e2 = self.state.players[0].hand
        state = apply_command(self.state, AttachEnergy(0, e1, active(self.state, 0).card))
        self.assertEqual(active(state, 0).energy, [e1])
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, AttachEnergy(0, e2, state.players[0].bench[0].card))
        self.assertEqual(ctx.exception.code, "ENERGY_ALREADY_ATTACHED")

        # 次の自分の番にはまたつけられる
        state = apply_command(state, EndTurn(0))
        state = apply_command(state, EndTurn(1))
        state = apply_command(state, AttachEnergy(0, e2, state.players[0].bench[0].card))
        self.assertEqual(state.players[0].bench[0].energy, [e2])

    def test_energy_can_go_to_bench(self):
        e1 = self.state.players[0].hand[0]
        state = apply_command(self.state, AttachEnergy(0, e1, self.state.players[0].bench[0].card))
        self.assertEqual(state.players[0].bench[0].energy, [e1])

    def test_cannot_attach_to_opponent_pokemon(self):
        e1 = self.state.players[0].hand[0]
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(self.state, AttachEnergy(0, e1, active(self.state, 1).card))
        self.assertEqual(ctx.exception.code, "TARGET_NOT_YOURS")


class TurnOwnershipTest(unittest.TestCase):
    """相手の番には操作できない。"""

    def test_opponent_cannot_act(self):
        state = build_test_state([
            {"active": GROWLITHE, "hand": [FIRE]},
            {"active": {"card": STARYU, "energy": [WATER]}, "hand": [WATER, MACHOP]},
        ])
        water, machop = state.players[1].hand
        for command in (EndTurn(1), UseAttack(1, 0), AttachEnergy(1, water, active(state, 1).card), PlayBasicToBench(1, machop)):
            with self.assertRaises(IllegalActionError) as ctx:
                apply_command(state, command)
            self.assertEqual(ctx.exception.code, "NOT_YOUR_TURN", command)

    def test_invalid_player(self):
        state = build_test_state([{"active": GROWLITHE}, {"active": STARYU}])
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, EndTurn(2))
        self.assertEqual(ctx.exception.code, "INVALID_PLAYER")


class AfterTurnEndTest(unittest.TestCase):
    def test_previous_player_cannot_act_after_end_turn(self):
        state = build_test_state([{"active": GROWLITHE, "hand": [FIRE, PONYTA]}, {"active": STARYU}])
        fire, ponyta = state.players[0].hand
        state = apply_command(state, EndTurn(0))
        for command in (EndTurn(0), PlayBasicToBench(0, ponyta), AttachEnergy(0, fire, active(state, 0).card), UseAttack(0, 0)):
            with self.assertRaises(IllegalActionError) as ctx:
                apply_command(state, command)
            self.assertEqual(ctx.exception.code, "NOT_YOUR_TURN", command)


class BenchTest(unittest.TestCase):
    """ベンチは5匹まで。1回の番で出す数に制限はない（p.309）。"""

    def test_bench_limit(self):
        state = build_test_state([
            {"active": GROWLITHE, "hand": [PONYTA, PONYTA, RATTATA, RATTATA, MACHOP, DIGLETT]},
            {"active": STARYU},
        ])
        hand = list(state.players[0].hand)
        for uid in hand[:5]:
            state = apply_command(state, PlayBasicToBench(0, uid))
        self.assertEqual(len(state.players[0].bench), 5)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, PlayBasicToBench(0, hand[5]))
        self.assertEqual(ctx.exception.code, "BENCH_FULL")

    def test_same_card_cannot_be_played_twice(self):
        state = build_test_state([{"active": GROWLITHE, "hand": [PONYTA]}, {"active": STARYU}])
        ponyta = state.players[0].hand[0]
        state = apply_command(state, PlayBasicToBench(0, ponyta))
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, PlayBasicToBench(0, ponyta))
        self.assertEqual(ctx.exception.code, "CARD_NOT_IN_HAND")

    def test_energy_cannot_go_to_bench(self):
        state = build_test_state([{"active": GROWLITHE, "hand": [FIRE]}, {"active": STARYU}])
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, PlayBasicToBench(0, state.players[0].hand[0]))
        self.assertEqual(ctx.exception.code, "NOT_BASIC_POKEMON")


class AttackTest(unittest.TestCase):
    """ワザ（p.309、p.320）。"""

    def test_insufficient_energy(self):
        """必要なエネルギーがついていなければ、ワザは使えない。"""
        state = build_test_state([
            {"active": {"card": GROWLITHE, "energy": [WATER]}},  # ほのお: 炎 + 無色
            {"active": STARYU},
        ])
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, "INSUFFICIENT_ENERGY")

    def test_colorless_part_paid_by_other_type(self):
        state = build_test_state([
            {"active": {"card": GROWLITHE, "energy": [FIRE, WATER]}},
            {"active": MACHOP},
        ])
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual(active(state, 1).damage, 20)

    def test_attack_ends_the_turn(self):
        """ワザを使ってそれによって起こることがすんだら、番は自動的に終わる（p.309）。"""
        state = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING]}, "hand": [FIGHTING]},
            {"active": GROWLITHE},
        ], turn_number=5)
        hand1 = len(state.players[1].hand)
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual((state.phase, state.current_player, state.turn_number), (Phase.MAIN, 1, 6))
        self.assertEqual(len(state.players[1].hand), hand1 + 1)
        # 攻撃した側はもう操作できない
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, AttachEnergy(0, state.players[0].hand[0], active(state, 0).card))
        self.assertEqual(ctx.exception.code, "NOT_YOUR_TURN")

    def test_energy_stays_after_attack(self):
        """ワザを使っても、エネルギーはついたまま（p.309、p.320）。"""
        state = build_test_state([{"active": {"card": MACHOP, "energy": [FIGHTING]}}, {"active": GROWLITHE}])
        energy = list(active(state, 0).energy)
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual(active(state, 0).energy, energy)

    def test_invalid_attack_index(self):
        state = build_test_state([{"active": {"card": MACHOP, "energy": [FIGHTING]}}, {"active": GROWLITHE}])
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, UseAttack(0, 1))
        self.assertEqual(ctx.exception.code, "INVALID_ATTACK")

    def test_first_player_may_attack_on_first_turn(self):
        """先攻の最初の番のワザの制限は、公式ルール 2000.02.14版の本文にない（kyuura first_turn_actions）。"""
        state = build_test_state([{"active": {"card": MACHOP, "energy": [FIGHTING]}}, {"active": GROWLITHE}], turn_number=1)
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual(active(state, 1).damage, 20)


class RetreatTest(unittest.TestCase):
    """にげる（pp.310〜311、kyuura retreat_count）。"""

    def setUp(self):
        self.state = build_test_state([
            {"active": {"card": HITMONCHAN, "energy": [FIGHTING, FIGHTING, FIGHTING], "damage": 30},
             "bench": [{"card": DIGLETT}, {"card": MACHOP, "energy": [FIGHTING]}]},
            {"active": STARYU},
        ])
        self.hitmonchan = active(self.state, 0)
        self.diglett, self.machop = self.state.players[0].bench

    def test_retreat_discards_cost_and_swaps(self):
        e = self.hitmonchan.energy
        state = apply_command(self.state, Retreat(0, (e[0], e[1]), self.diglett.card))
        p = state.players[0]
        self.assertEqual(p.active.card, self.diglett.card)
        moved = p.bench[0]
        self.assertEqual(moved.card, self.hitmonchan.card)
        self.assertEqual(moved.energy, [e[2]])  # 残りのエネルギーといっしょに移動
        self.assertEqual(moved.damage, 30)  # ダメージもそのまま
        self.assertEqual(p.discard, [e[0], e[1]])
        self.assertEqual(check_invariants(state), [])

    def test_retreat_many_times_in_one_turn(self):
        """「にげる」の宣言は、1回の自分の番の中で、何度でもできる（p.311）。"""
        e = self.hitmonchan.energy
        state = apply_command(self.state, Retreat(0, (e[0], e[1]), self.diglett.card))
        state = apply_command(state, Retreat(0, (), self.hitmonchan.card))  # ディグダはにげる 0
        self.assertEqual(active(state, 0).card, self.hitmonchan.card)
        self.assertEqual(state.players[0].discard, [e[0], e[1]])

    def test_wrong_number_of_energy(self):
        e = self.hitmonchan.energy
        for discard in ((e[0],), tuple(e)):
            with self.assertRaises(IllegalActionError) as ctx:
                apply_command(self.state, Retreat(0, discard, self.diglett.card))
            self.assertEqual(ctx.exception.code, "WRONG_RETREAT_COST")

    def test_cannot_discard_energy_of_other_pokemon(self):
        e = self.hitmonchan.energy
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(self.state, Retreat(0, (e[0], self.machop.energy[0]), self.diglett.card))
        self.assertEqual(ctx.exception.code, "ENERGY_NOT_ATTACHED")

    def test_cannot_retreat_without_bench(self):
        """ベンチに控えポケモンがいないときには、「にげる」を宣言できない（p.311）。"""
        state = build_test_state([{"active": {"card": GROWLITHE, "energy": [FIRE]}}, {"active": STARYU}])
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, Retreat(0, tuple(active(state, 0).energy), 999))
        self.assertEqual(ctx.exception.code, "NO_BENCH")

    def test_retreat_with_full_bench(self):
        """ベンチが控えポケモンでいっぱい（5 匹）でも、にげられる（p.311）。"""
        state = build_test_state([
            {"active": {"card": GROWLITHE, "energy": [FIRE]}, "bench": [PONYTA, RATTATA, DIGLETT, MACHOP, STARYU]},
            {"active": STARYU},
        ])
        target = state.players[0].bench[2].card
        state = apply_command(state, Retreat(0, tuple(active(state, 0).energy), target))
        self.assertEqual(active(state, 0).card, target)
        self.assertEqual(len(state.players[0].bench), 5)

    def test_not_enough_energy_to_retreat(self):
        """にげるエネルギーぶんのエネルギーがついていなければ、にげられない（p.310）。"""
        state = build_test_state([
            {"active": {"card": HITMONCHAN, "energy": [FIGHTING]}, "bench": [DIGLETT]},  # にげる 2
            {"active": STARYU},
        ])
        diglett = state.players[0].bench[0].card
        for discard in ((), tuple(active(state, 0).energy)):
            with self.assertRaises(IllegalActionError) as ctx:
                apply_command(state, Retreat(0, discard, diglett))
            self.assertEqual(ctx.exception.code, "WRONG_RETREAT_COST")

    def test_cannot_retreat_on_opponents_turn(self):
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(self.state, Retreat(1, (), 0))
        self.assertEqual(ctx.exception.code, "NOT_YOUR_TURN")


class IllegalCommandsDoNotChangeStateTest(unittest.TestCase):
    """不正な操作ではゲーム状態が変わらない。"""

    def test_failed_commands_leave_state_unchanged(self):
        state = build_test_state([
            {"active": {"card": GROWLITHE, "energy": [WATER]}, "hand": [FIRE, PONYTA]},
            {"active": STARYU, "hand": [WATER]},
        ])
        before = state_to_dict(state)
        bad = [
            UseAttack(0, 0),  # エネルギー不足
            AttachEnergy(1, state.players[1].hand[0], active(state, 1).card),  # 相手の番
            Retreat(0, (), 12345),  # ベンチなし
            PlayBasicToBench(0, state.players[0].hand[0]),  # エネルギーはベンチに出せない
            EvolvePokemon(0, 1, 2),  # 未対応
        ]
        for command in bad:
            with self.assertRaises((IllegalActionError, UnsupportedError)):
                apply_command(state, command)
            self.assertEqual(state_to_dict(state), before)

    def test_successful_command_does_not_modify_input(self):
        state = build_test_state([{"active": GROWLITHE, "hand": [FIRE]}, {"active": STARYU}])
        before = state_to_dict(state)
        new = apply_command(state, AttachEnergy(0, state.players[0].hand[0], active(state, 0).card))
        self.assertEqual(state_to_dict(state), before)
        self.assertNotEqual(state_to_dict(new), before)


class UnsupportedActionsTest(unittest.TestCase):
    """未対応の操作は、黙って無視せず UnsupportedError にする。

    v0.2b で PlayTrainer を対応にしたので、この一覧から外した（トレーナーの検査は test_trainers.py）。
    """

    def test_unsupported_commands(self):
        state = build_test_state([{"active": GROWLITHE}, {"active": STARYU}])
        for command in (EvolvePokemon(0, 0, 1), UsePokemonPower(0, 0)):
            with self.assertRaises(UnsupportedError) as ctx:
                apply_command(state, command)
            self.assertEqual(ctx.exception.code, "UNSUPPORTED_ACTION")
        # PlayTrainer は v0.2b から処理する（手札にないカードは CARD_NOT_IN_HAND）
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, PlayTrainer(0, 0))
        self.assertEqual(ctx.exception.code, "CARD_NOT_IN_HAND")


class CommandDictTest(unittest.TestCase):
    def test_round_trip(self):
        for command in (Retreat(0, (1, 2), 3), UseAttack(1, 0), EndTurn(0)):
            data = command_to_dict(command)
            self.assertEqual(command_from_dict(data), command)

    def test_unknown_or_bad_command(self):
        with self.assertRaises(IllegalActionError) as ctx:
            command_from_dict({"type": "draw_extra_card", "player": 0})
        self.assertEqual(ctx.exception.code, "UNKNOWN_COMMAND")
        with self.assertRaises(IllegalActionError) as ctx:
            command_from_dict({"type": "use_attack", "player": 0})
        self.assertEqual(ctx.exception.code, "BAD_COMMAND")

    def test_non_string_type_is_unknown_command(self):
        """JSON から来た type が文字列でない（リストなど）ときも、TypeError ではなくエンジンの例外にする。"""
        for name in (["use_attack"], None, 3):
            with self.assertRaises(IllegalActionError) as ctx:
                command_from_dict({"type": name, "player": 0})
            self.assertEqual(ctx.exception.code, "UNKNOWN_COMMAND")


if __name__ == "__main__":
    unittest.main()


class CommandFieldTypeTest(unittest.TestCase):
    def test_bool_or_string_is_not_a_uid(self):
        state = build_test_state([{"active": GROWLITHE, "hand": [PONYTA, FIRE]}, {"active": STARYU}])
        for command in (PlayBasicToBench(0, True), UseAttack(0, "0"), Retreat(0, [1], 2), EndTurn(False),
                        PlayBasicToBench(0, PONYTA)):  # カード id（文字列）は uid ではない
            with self.assertRaises(IllegalActionError) as ctx:
                apply_command(state, command)
            self.assertEqual(ctx.exception.code, "BAD_COMMAND", command)
