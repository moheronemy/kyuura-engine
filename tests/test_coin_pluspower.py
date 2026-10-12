"""コインを投げるワザとプラスパワー（v0.2d）: ドードーの「みだれづき」（p.231）× プラスパワー（p.257）。

根拠:

- p.321 ダメージ計算の順番: 1 基本となるダメージ（「おもて」の数×10）→ 2（ここまでで 0 以下なら計算を終え、
  「ダメージを与えなかった」）→ 3 弱点 → 4 抵抗力 → 5 ワザを使うポケモンについているトレーナー（プラスパワー）。
  途中で 0・マイナスになってもよい
- p.257 プラスパワーの最新の説明と解説「相手の対戦ポケモンにワザのダメージが与えられなかったら、「プラスパワー」の
  効果はなくなります」。使った番の終わりにトラッシュ
- kyuura の記録: NEO-2000-OFFICIAL-RULES、ERR-PLUSPOWER、カード PMCG1-061・PMCG1-081
"""

import unittest

from kyuura_engine import IllegalActionError, Phase, PlayTrainer, TakePrize, UseAttack, apply_command
from kyuura_engine.rng import rng_fingerprint

from tests.helpers import H, PLUSPOWER, RATTATA, STARYU, T
from tests.test_coin_attacks import RESISTANT, WEAK, attack, doduo_vs, full


def with_pluspowers(defender, *sides, count=1, **kwargs):
    state = doduo_vs(defender, *sides, hand=[PLUSPOWER] * count, **kwargs)
    fingerprint = rng_fingerprint(state.rng)
    cards = list(state.players[0].hand)
    for card in cards:
        state = apply_command(state, PlayTrainer(0, card))
    assert rng_fingerprint(state.rng) == fingerprint  # トレーナーは乱数を使わない
    return state, cards


class OnePlusPowerTest(unittest.TestCase):
    def test_plus_ten_after_the_coins(self):
        for sides, amount in (((H, T), 20), ((T, H), 20), ((H, H), 30)):
            with self.subTest(sides=sides):
                state, (pluspower,) = with_pluspowers(STARYU, *sides)
                _, _, damage = attack(state)
                base = amount - 10
                self.assertEqual(damage["amount"], amount)
                self.assertEqual(damage["steps"], (("1 基本となる計算", base), ("5 プラスパワー", amount)))
                self.assertEqual(damage["modifiers"], ((5, pluspower, 10),))

    def test_all_tails_with_pluspower_is_no_damage(self):
        """「おもて」0 枚: 2 段階までで 0 なので計算を終え、5 段階のプラスパワーは計算しない（p.321・p.257）。

        「0 + 10 = 10」にはならない。プラスパワーは、使った番の終わりにトラッシュする（効果がなくても同じ）。
        """
        state, (pluspower,) = with_pluspowers(STARYU, T, T)
        new, events, damage = attack(state)
        self.assertEqual((damage["amount"], damage["stopped_after_step_2"]), (0, True))
        self.assertEqual(damage["steps"], (("1 基本となる計算", 0),))
        self.assertNotIn("modifiers", damage)  # 計算に使っていない
        self.assertEqual(new.players[1].active.damage, 0)
        discard = [e for e in events if e["kind"] == "discard_attached_trainer"]
        self.assertEqual([(e["card"], e["reason"]) for e in discard], [(pluspower, "end_of_turn")])
        self.assertIn(pluspower, new.players[0].discard)
        self.assertEqual((new.phase, new.current_player), (Phase.MAIN, 1))


class SeveralPlusPowersTest(unittest.TestCase):
    def test_two_pluspowers(self):
        state, cards = with_pluspowers(STARYU, H, T, count=2)
        _, _, damage = attack(state)
        self.assertEqual(damage["amount"], 30)
        self.assertEqual(damage["modifiers"], tuple((5, card, 10) for card in cards))

    def test_two_pluspowers_and_all_tails(self):
        state, _ = with_pluspowers(STARYU, T, T, count=2)
        new, _, damage = attack(state)
        self.assertEqual((damage["amount"], damage["stopped_after_step_2"]), (0, True))
        self.assertEqual(new.players[0].active.trainers, [])  # 2 枚とも番の終わりにトラッシュした


class WeaknessResistanceWithPlusPowerTest(unittest.TestCase):
    """弱点・抵抗力（無色が弱点・抵抗力のテスト専用のカード）とプラスパワー。"""

    def test_weakness_then_pluspower(self):
        state, _ = with_pluspowers(WEAK, H, T)
        _, _, damage = attack(state)
        self.assertEqual(damage["steps"], (("1 基本となる計算", 10), ("3 弱点", 20), ("5 プラスパワー", 30)))
        self.assertEqual(damage["amount"], 30)

    def test_weakness_and_all_tails(self):
        state, _ = with_pluspowers(WEAK, T, T)
        _, _, damage = attack(state)
        self.assertEqual((damage["amount"], damage["weakness"], damage["stopped_after_step_2"]), (0, False, True))

    def test_resistance_then_pluspower_keeps_the_negative_value(self):
        """抵抗力でマイナスになっても計算を続け、5 段階でプラスパワーを足す（p.321）。"""
        cases = (
            ((H, T), 1, (("1 基本となる計算", 10), ("4 抵抗力", -20), ("5 プラスパワー", -10)), 0),
            ((H, H), 1, (("1 基本となる計算", 20), ("4 抵抗力", -10), ("5 プラスパワー", 0)), 0),
            ((H, H), 2, (("1 基本となる計算", 20), ("4 抵抗力", -10), ("5 プラスパワー", 0), ("5 プラスパワー", 10)), 10),
        )
        for sides, count, steps, amount in cases:
            with self.subTest(sides=sides, count=count):
                state, _ = with_pluspowers(RESISTANT, *sides, count=count)
                _, _, damage = attack(state)
                self.assertEqual((damage["steps"], damage["amount"], damage["resistance"]), (steps, amount, True))
                self.assertNotIn("stopped_after_step_2", damage)


class KnockOutWithPlusPowerTest(unittest.TestCase):
    def test_exactly_hp_knocks_out(self):
        """コラッタ（HP30）: 「おもて」2 枚 20 + プラスパワー 10 = 30 で、ちょうど HP → きぜつ（p.319・p.323）。"""
        state, _ = with_pluspowers(RATTATA, H, H)
        new, events, damage = attack(state)
        self.assertEqual(damage["total_damage"], 30)
        self.assertIn("knock_out", [e["kind"] for e in events])
        self.assertEqual(new.phase, Phase.TAKE_PRIZE)

    def test_one_head_is_one_short(self):
        state, _ = with_pluspowers(RATTATA, H, T)
        _, events, damage = attack(state)
        self.assertEqual(damage["total_damage"], 20)
        self.assertNotIn("knock_out", [e["kind"] for e in events])

    def test_last_prize_wins_and_pluspower_stays(self):
        """最後のサイドで勝ち。勝敗が決まった番は番の終わりが来ないので、プラスパワーはついたまま（v0.2c と同じ）。"""
        state, (pluspower,) = with_pluspowers(RATTATA, H, H, prizes=1)
        new, _, _ = attack(state)
        new = apply_command(new, TakePrize(0, 0))
        self.assertEqual((new.phase, new.result.winner), (Phase.GAME_OVER, 0))
        self.assertEqual([t.card for t in new.players[0].active.trainers], [pluspower])


class RejectedAttackKeepsPlusPowerTest(unittest.TestCase):
    def test_rejected_attack_after_pluspower(self):
        state, (pluspower,) = with_pluspowers(STARYU, H, H)
        before, fingerprint = full(state), rng_fingerprint(state.rng)
        with self.assertRaises(IllegalActionError):
            apply_command(state, UseAttack(0, 3))
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
        self.assertEqual([t.card for t in state.players[0].active.trainers], [pluspower])
        _, _, damage = attack(state)
        self.assertEqual(damage["amount"], 30)


if __name__ == "__main__":
    unittest.main()
