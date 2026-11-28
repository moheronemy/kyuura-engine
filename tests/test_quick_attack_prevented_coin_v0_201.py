"""v0.201: 「コインを投げて「おもて」なら、N ダメージを追加する」ワザ（``CoinBonusDamage`` → 解決の基盤の ``HeadsBonus``）を、ダメージだけを無効にする効果
（「からにこもる」「かたまる」。効果の窓を持たない）のある相手に使うとき、通常どおりコインを投げ、結果で決まるダメージに無効を当てる（v0.4b〜v0.200 は
``UNRESOLVED_PREVENTED_COIN_DAMAGE`` で止めた）。カード文面と既存のルールに基づく実装解釈。当時の直接裁定は未確認（docs/quick-attack-prevented-coin-v0.201.md）。

- ワザ全体を受けない効果（バリアー。効果の窓も持つ）は今までどおり止める
- ほかのコインのダメージ（×の CoinFlipDamage・つのでつつく・相手が投げるコイン・ゴッドバードの FailOnTails）は変えない
"""
from __future__ import annotations

import pathlib
import re
import unittest

from kyuura_engine import EndTurn, ResolveDecision, UnsupportedError, UseAttack, apply_command
from kyuura_engine import effects as E
from kyuura_engine.coins import CoinSide
from kyuura_engine.resolution import programs as PR
from tests.helpers import build_test_state, with_coin_results

ROOT = pathlib.Path(__file__).resolve().parents[1]
H, T = CoinSide.HEADS, CoinSide.TAILS
P, W, G = "PMCG1-101", "PMCG1-099", "PMCG1-097"
PIDGEY, SQUIRTLE, MEWTWO, METAPOD, RATTATA = "ES1-024", "PMCG1-023", "PMCG1-050", "PMCG1-009", "PMCG1-060"
CODE = "UNRESOLVED_PREVENTED_COIN_DAMAGE"


def after_defense(defender, attack_index, side):
    """主体 1 のバトル場が attack_index のワザを side のコインで使い（None なら番を終える）、主体 0 の番にする。"""
    st = build_test_state([{"active": {"card": PIDGEY, "energy": [P, P]}, "bench": [RATTATA]},
                           {"active": defender, "bench": [RATTATA]}], current_player=1, turn_number=4)
    if attack_index is None:
        return apply_command(st, EndTurn(1))
    st = apply_command(with_coin_results(st, side) if side else st, UseAttack(1, attack_index))
    while st.decision is not None and st.decision.player == 1:
        st = apply_command(st, ResolveDecision(1, st.decision.id, (st.decision.options[0],)))
    return st


def quick_attack(state, side):
    st = with_coin_results(state, side)
    return st, apply_command(st, UseAttack(0, 1))


def new_events(before, after):
    return [dict(e) for e in after.log[len(before.log):]]


class DamageOnlyPreventionTest(unittest.TestCase):
    def test_withdraw_flips_the_coin_and_prevents_the_damage(self):
        base = after_defense({"card": SQUIRTLE, "energy": [W, W]}, 1, H)  # からにこもる（「おもて」）
        for side in (H, T):
            with self.subTest(side=side):
                st, after = quick_attack(base, side)
                ev = new_events(st, after)
                kinds = [e["kind"] for e in ev]
                self.assertEqual([(e["source"], e["result"]) for e in ev if e["kind"] == "coin_flip"], [("attack", side.value)])  # 1 枚だけ、ワザのコイン
                self.assertEqual(kinds[:3], ["attack", "coin_flip", "damage_prevented"])  # コインのあとに無効
                self.assertNotIn("damage", kinds)
                self.assertEqual(after.players[1].active.damage, 0)
                self.assertEqual((after.decision, after.current_player), (None, 1))  # 番が相手へ移る
                self.assertIn("turn_end", kinds)

    def test_harden_is_also_damage_only(self):
        base = after_defense({"card": METAPOD, "energy": [G, G], "evolved_from": "PMCG1-004"}, 0, H)  # かたまる（「おもて」）
        st, after = quick_attack(base, H)
        kinds = [e["kind"] for e in new_events(st, after)]
        self.assertEqual(kinds[:3], ["attack", "coin_flip", "damage_prevented"])

    def test_without_prevention_the_coin_decides_the_damage(self):
        base = after_defense({"card": SQUIRTLE, "energy": [W, W]}, None, None)
        for side, amount in ((H, 30), (T, 10)):
            with self.subTest(side=side):
                st, after = quick_attack(base, side)
                self.assertEqual([e["amount"] for e in new_events(st, after) if e["kind"] == "damage"], [amount])


class WholeAttackPreventionTest(unittest.TestCase):
    def test_barrier_flips_the_coin_and_prevents_the_damage(self):
        """v0.205（docs/barrier-coin-damage-v0.205.md）: でんこうせっかはダメージだけで終わるワザなので、バリアー（ワザを受けない）の相手にもコインを投げ、
        バリアーがダメージを無効にする（v0.201〜v0.204 は止めた）。"""
        base = after_defense({"card": MEWTWO, "energy": [P, P, P]}, 1, None)  # バリアー（ワザを受けない）
        for side in (H, T):
            with self.subTest(side=side):
                st, after = quick_attack(base, side)
                self.assertEqual([e["kind"] for e in new_events(st, after)][:3], ["attack", "coin_flip", "damage_prevented"])
                self.assertEqual(after.players[1].active.damage, 0)


class ScopeTest(unittest.TestCase):
    def test_only_heads_bonus_flips(self):
        self.assertTrue(PR.HeadsBonus.flip_against_damage_only_void)
        for name in ("OpponentTailsBonus",):
            self.assertFalse(getattr(getattr(PR, name), "flip_against_damage_only_void", False), name)
        self.assertEqual(PR.BUILDERS[E.CoinBonusDamage](E.CoinBonusDamage(20))[0].base, PR.HeadsBonus(20))

    def test_no_card_id_branch_in_engine_or_resolution(self):
        for path in [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]:
            self.assertIsNone(re.search(r"[\"']ES1-024[\"']", path.read_text(encoding="utf-8")), path.name)


if __name__ == "__main__":
    unittest.main()
