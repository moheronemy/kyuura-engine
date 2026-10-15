"""ワザのダメージ・きぜつ・サイド・勝敗（『オフィシャルブック2000』pp.311〜323）。

kyuura の記録 id: weakness_resistance・knockout_timing・sudden_death（data/rule_differences.json）、
NEO-2000-OFFICIAL-RULES・NEO-2000-PLAYRULE（data/rule_history.json）。
"""

import dataclasses
import unittest

from kyuura_engine import (
    EndTurn, IllegalActionError, Phase, PromoteActive, TakePrize, UnsupportedError, UseAttack, apply_command,
    check_invariants, load_card_pool, state_to_dict,
)
from kyuura_engine.cards import EnergyType
from kyuura_engine.damage import calculate_attack_damage
from kyuura_engine.rules import RULES_2000_02_14

from tests.helpers import (
    CHARMANDER, DIGLETT, FIGHTING, FIRE, GROWLITHE, HITMONCHAN, LIGHTNING, MACHOP, NO_EMBER_EFFECTS, PONYTA, RATTATA, SEEL,
    STARYU, VOLTORB, WATER, active, build_test_state,
)


def attack_once(attacker, defender, *, defender_bench=(), attacker_prizes=6, defender_damage=0):
    state = build_test_state([
        {"active": attacker, "prizes": attacker_prizes},
        {"active": {"card": defender, "damage": defender_damage}, "bench": list(defender_bench)},
    ])
    return state, apply_command(state, UseAttack(0, attacker.get("attack", 0) if isinstance(attacker, dict) else 0))


class DamageTest(unittest.TestCase):
    """ダメージ計算の順番（p.321）と弱点・抵抗力（p.315）。"""

    def test_basic_damage(self):
        """説明のないワザは、ダメージの目安の数字ぶんを相手の対戦ポケモンに与える（p.309, p.320）。"""
        _, state = attack_once({"card": MACHOP, "energy": [FIGHTING]}, GROWLITHE)
        self.assertEqual(active(state, 1).damage, 20)

    def test_weakness_doubles(self):
        """ワザを使うポケモンのタイプが弱点なら2倍（p.321 の 3）。ヒトデマン（水）→ ガーディ（弱点 水）。"""
        _, state = attack_once({"card": STARYU, "energy": [WATER]}, GROWLITHE)
        self.assertEqual(active(state, 1).damage, 40)
        damage = [e for e in state.log if e["kind"] == "damage"][-1]
        self.assertTrue(damage["weakness"])

    def test_resistance_subtracts_and_floors_at_zero(self):
        """抵抗力の数字をマイナス。0 以下なら「ダメージを与えなかった」（p.319, p.321 の 4）。

        ビリリダマ（雷）の たいあたり 10 → ディグダ（抵抗力 雷 -30）。
        """
        _, state = attack_once({"card": VOLTORB, "energy": [LIGHTNING]}, DIGLETT)
        self.assertEqual(active(state, 1).damage, 0)
        damage = [e for e in state.log if e["kind"] == "damage"][-1]
        self.assertEqual((damage["amount"], damage["resistance"]), (0, True))

    def test_other_types_are_not_affected(self):
        """弱点・抵抗力のタイプでなければそのまま。ワンリキー（闘）→ ディグダ（弱点 草・抵抗力 雷）。"""
        _, state = attack_once({"card": MACHOP, "energy": [FIGHTING]}, DIGLETT, defender_bench=[RATTATA])
        self.assertEqual(active(state, 1).damage, 20)  # ディグダ HP30 なのできぜつしない
        damage = [e for e in state.log if e["kind"] == "damage"][-1]
        self.assertEqual((damage["weakness"], damage["resistance"]), (False, False))

    def test_weakness_is_calculated_before_resistance(self):
        """弱点（3）→ 抵抗力（4）の順。順番が逆なら 0 になる組み合わせで確かめる（p.321）。"""
        pool = load_card_pool()
        attacker = pool.get(MACHOP)
        defender = dataclasses.replace(pool.get(RATTATA), weakness=EnergyType.FIGHTING, resistance=EnergyType.FIGHTING, resistance_value=30)
        calc = calculate_attack_damage(20, attacker, defender, RULES_2000_02_14)
        self.assertEqual(calc.final, 10)  # (20 × 2) − 30。逆なら (20 − 30) × 2 → 0
        self.assertEqual([s[1] for s in calc.steps], [20, 40, 10])

    def test_damage_accumulates(self):
        state = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING]}},
            {"active": {"card": SEEL, "energy": [WATER]}},
        ])
        state = apply_command(state, UseAttack(0, 0))  # けたぐり 20
        state = apply_command(state, UseAttack(1, 0))  # ずつき 10
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual(active(state, 1).damage, 40)
        self.assertEqual(active(state, 0).damage, 10)


class KnockOutTest(unittest.TestCase):
    """きぜつ・サイド・バトル場のポケモンの交代（p.312, p.313, p.323）。"""

    def setUp(self):
        self.before = build_test_state([
            {"active": {"card": HITMONCHAN, "energy": [FIGHTING, FIGHTING, WATER]}},
            {"active": {"card": PONYTA, "energy": [FIRE, FIRE], "damage": 10}, "bench": [GROWLITHE, RATTATA]},
        ], turn_number=7)
        self.state = apply_command(self.before, UseAttack(0, 1))  # スペシャルパンチ 40（10 + 40 ≥ HP40）
        self.ponyta = active(self.before, 1)

    def test_knocked_out_pokemon_and_energy_go_to_discard(self):
        """HP以上のダメージできぜつ。ダメージカウンターを取りのぞき、ポケモンとついていたカードをトラッシュ（p.323）。"""
        p1 = self.state.players[1]
        self.assertIsNone(p1.active)
        self.assertEqual(sorted(p1.discard), sorted([self.ponyta.card, *self.ponyta.energy]))
        self.assertEqual(self.state.phase, Phase.TAKE_PRIZE)
        self.assertEqual(self.state.pending_prizes, {0: 1})
        self.assertEqual(check_invariants(self.state), [])

    def test_exactly_hp_damage_knocks_out(self):
        """ダメージがHPと同じか、それより大きくなったらきぜつ（p.319）。"""
        _, state = attack_once({"card": MACHOP, "energy": [FIGHTING]}, PONYTA, defender_damage=20, defender_bench=[GROWLITHE])
        self.assertIsNone(active(state, 1))

    def test_attacker_takes_one_prize(self):
        """相手のポケモンが1匹きぜつするごとに、サイドから表を見ないで1枚を選び、手札に加える（p.312, p.323）。"""
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(self.state, TakePrize(1, 0))
        self.assertEqual(ctx.exception.code, "NOT_YOUR_DECISION")
        prizes = list(self.state.players[0].prizes)
        hand = len(self.state.players[0].hand)
        state = apply_command(self.state, TakePrize(0, 3))
        self.assertEqual(state.players[0].hand[-1], prizes[3])
        self.assertEqual(len(state.players[0].hand), hand + 1)
        self.assertEqual(len(state.players[0].prizes), 5)
        self.assertEqual(state.phase, Phase.PROMOTE_ACTIVE)
        self.assertEqual(state.pending_promotions, [1])

    def test_prize_index_out_of_range(self):
        for index in (-1, len(self.state.players[0].prizes)):
            with self.assertRaises(IllegalActionError) as ctx:
                apply_command(self.state, TakePrize(0, index))
            self.assertEqual(ctx.exception.code, "INVALID_PRIZE_INDEX")

    def test_defender_promotes_from_bench_then_turn_passes(self):
        """ベンチからすぐに代わりのポケモンを出す（p.313）。その後、番が終わる（p.309）。"""
        state = apply_command(self.state, TakePrize(0, 0))
        growlithe, rattata = state.players[1].bench
        with self.assertRaises(IllegalActionError):
            apply_command(state, PromoteActive(0, growlithe.card))
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, PromoteActive(1, 999))
        self.assertEqual(ctx.exception.code, "NOT_ON_BENCH")
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, EndTurn(0))
        self.assertEqual(ctx.exception.code, "WRONG_PHASE")
        state = apply_command(state, PromoteActive(1, rattata.card))
        self.assertEqual(active(state, 1).card, rattata.card)
        self.assertEqual([b.card for b in state.players[1].bench], [growlithe.card])
        self.assertEqual((state.phase, state.current_player, state.turn_number), (Phase.MAIN, 1, 8))
        self.assertEqual(check_invariants(state), [])


class SimultaneousKnockOutOrderTest(unittest.TestCase):
    """両方の対戦ポケモンが同時にきぜつしたら、今が自分の番でないプレイヤーが先に出す（pp.323-324）。

    v0.1 の対応カードでは同時のきぜつは起こらない（ワザは相手のバトル場のポケモンにしかダメージを
    与えない）。ここでは、ワザの処理の後の手順（v0.16b から解決の基盤の ``flow._after_knockouts``。v0.15 までは v0.13 の経路の
    ``engine._after_knockouts``）を直接呼んで順番だけを確かめる。
    """

    def test_non_turn_player_promotes_first(self):
        from kyuura_engine.resolution import flow
        from kyuura_engine.resolution.kernel import Resolution

        state = build_test_state([
            {"active": None, "bench": [GROWLITHE]},
            {"active": None, "bench": [STARYU]},
        ], current_player=0)
        flow._after_knockouts(Resolution(state), (), None, ())
        self.assertEqual((state.phase, state.pending_promotions), (Phase.PROMOTE_ACTIVE, [1, 0]))
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, PromoteActive(0, state.players[0].bench[0].card))
        self.assertEqual(ctx.exception.code, "NOT_YOUR_DECISION")
        state = apply_command(state, PromoteActive(1, state.players[1].bench[0].card))
        state = apply_command(state, PromoteActive(0, state.players[0].bench[0].card))
        self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 1))

    def test_both_cannot_field_is_sudden_death_and_not_continued(self):
        """両方とも出せないときはサドン・デス（p.311, p.324）。延長戦の開始は v0.1 では未実装。"""
        from kyuura_engine.resolution import flow
        from kyuura_engine.resolution.kernel import Resolution

        state = build_test_state([{"active": None}, {"active": None}], current_player=0)
        flow._after_knockouts(Resolution(state), (), None, ())
        self.assertEqual(state.phase, Phase.SUDDEN_DEATH)
        self.assertEqual(state.result.outcome, "sudden_death")
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, EndTurn(0))
        self.assertEqual(ctx.exception.code, "SUDDEN_DEATH_NOT_IMPLEMENTED")


class WinLossTest(unittest.TestCase):
    """勝ち負けが決まるとき（p.311）。"""

    def test_taking_last_prize_wins(self):
        _, state = attack_once({"card": HITMONCHAN, "energy": [FIGHTING]}, RATTATA, attacker_prizes=1, defender_bench=[PONYTA])
        state = apply_command(state, TakePrize(0, 0))
        self.assertEqual(state.phase, Phase.GAME_OVER)
        self.assertEqual(state.result.winner, 0)
        self.assertEqual(state.result.conditions, ((0, "ALL_PRIZES_TAKEN"),))

    def test_no_pokemon_to_promote_loses(self):
        """きぜつしてベンチにポケモンがいなければ負け（p.311, p.313）。"""
        _, state = attack_once({"card": MACHOP, "energy": [FIGHTING]}, RATTATA)
        state = apply_command(state, TakePrize(0, 0))
        self.assertEqual(state.phase, Phase.GAME_OVER)
        self.assertEqual(state.result.winner, 0)
        self.assertEqual(state.result.conditions, ((0, "OPPONENT_CANNOT_FIELD_ACTIVE"),))

    def test_last_prize_and_no_bench_together(self):
        """勝敗の表の「あなたがサイドを取った・相手が出せない」の行（p.311）→ あなたの勝ち。"""
        _, state = attack_once({"card": MACHOP, "energy": [FIGHTING]}, RATTATA, attacker_prizes=1)
        state = apply_command(state, TakePrize(0, 0))
        self.assertEqual(state.result.winner, 0)
        self.assertEqual(state.result.conditions, ((0, "ALL_PRIZES_TAKEN"), (0, "OPPONENT_CANNOT_FIELD_ACTIVE")))

    def test_deck_out_at_start_of_turn_loses(self):
        """番の最初に山札にカードが1枚もなければ、その時点で負け（p.309, p.311, p.312）。"""
        state = build_test_state([{"active": GROWLITHE}, {"active": STARYU, "deck": []}])
        state = apply_command(state, EndTurn(0))
        self.assertEqual(state.phase, Phase.GAME_OVER)
        self.assertEqual(state.result.winner, 0)
        self.assertEqual(state.result.conditions, ((0, "OPPONENT_DECK_EMPTY"),))

    def test_drawing_last_card_is_not_a_loss(self):
        """最後の1枚を引いて山札がなくなった段階では、まだ負けではない（p.311, p.312）。"""
        state = build_test_state([{"active": GROWLITHE, "deck": [FIRE, FIRE]}, {"active": STARYU, "deck": [WATER]}])
        state = apply_command(state, EndTurn(0))
        self.assertEqual((state.phase, state.current_player, len(state.players[1].deck)), (Phase.MAIN, 1, 0))
        state = apply_command(state, EndTurn(1))
        state = apply_command(state, EndTurn(0))
        self.assertEqual(state.phase, Phase.GAME_OVER)
        self.assertEqual(state.result.winner, 0)

    def test_no_commands_after_game_over(self):
        state = build_test_state([{"active": GROWLITHE}, {"active": STARYU, "deck": []}])
        state = apply_command(state, EndTurn(0))
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, EndTurn(1))
        self.assertEqual(ctx.exception.code, "GAME_OVER")


class UnsupportedAttackTest(unittest.TestCase):
    """効果のあるワザを、ダメージだけのワザとして処理しない。"""

    def test_attack_with_effect_is_refused_and_state_unchanged(self):
        # v0.30 で「ひのこ」を登録したので、その登録だけを除いた登録表で、ワザ単位の検査を確かめる（盤面を直接作る）
        state = build_test_state([
            {"active": {"card": CHARMANDER, "energy": [FIRE, FIRE]}},
            {"active": GROWLITHE},
        ], effects=NO_EMBER_EFFECTS)
        before = state_to_dict(state)
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, UseAttack(0, 1))  # ひのこ（炎エネルギーをトラッシュする効果）
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_ATTACK")
        self.assertEqual(state_to_dict(state), before)
        # 効果のないワザ（ひっかく 10）は使える
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual(active(state, 1).damage, 10)


if __name__ == "__main__":
    unittest.main()
