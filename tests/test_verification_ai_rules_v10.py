"""検証用 AI の試験の方策 rules-v10 のテスト（docs/hydro-pump-rainbow-rules-v10-v0.200.md）。

rules-v10 は rules-v9 に、［エナジートランス］の費用評価を基本エネルギーカードの移動だけでも行う規則を加える。rules-v8・rules-v9 は、移動できるカードに
基本エネルギーカードでないもの（レインボーエネルギーなど）があると入力全体を unevaluable:moved_card_not_basic にしていた。
小さな JSON の観測・段（tests/test_verification_ai_rules_v8.py の道具）で、混ざった入力で基本の有効な移動を選ぶ・改善する組がなければレインボーエネルギーも
選べる（絞らない）・基本だけの入力は rules-v8 と同じ・全部が基本でなければ評価しない・単位や色の決まらない費用は見送る、と、方式・計画の記録を確かめる。
"""

from __future__ import annotations

import unittest

from tests.test_verification_ai_rules_v8 import CARDS, E1_MOVES, BUL, G, TAN, VEN, allowed_after, et_stages, mon, retreat_item, run_policy, view
from tools.verification_ai import batch as B
from tools.verification_ai import runner as V
from tools.verification_ai.policies import (ENERGY_TRANS_BASIC_MOVES, RULES10_DISTRIBUTION, RULES10_VERSION, BasicMovesProgressRulePolicy,
                                            EnergyTransProgressRulePolicy, RefusedInputRulePolicy)

RE = "PMCG4-065"  # レインボーエネルギー（基本エネルギーカードではない）


def v10():
    return BasicMovesProgressRulePolicy("s", cards=CARDS)


class BasicMovesTest(unittest.TestCase):
    def test_card_table_marks_rainbow_as_not_basic(self):
        self.assertFalse(CARDS[RE].get("basic_energy"))
        self.assertTrue(CARDS[G].get("basic_energy"))

    def test_mixed_inputs_choose_an_effective_basic_move(self):
        """控えのフシギダネに草 2 枚とレインボーエネルギー。バトル場（草 0・にげる 2）への草の移動が優先 2（不足 2 → 1）。rules-v9 は入力全体を評価しない。"""
        v = view(mon(1, VEN), [mon(3, BUL, [(31, G), (32, RE), (33, G)]), mon(4, BUL)])
        moves = [(3, 31, G, 1), (3, 32, RE, 1), (3, 33, G, 1), (3, 31, G, 4), (3, 32, RE, 4), (3, 33, G, 4)]
        st = et_stages(moves)
        p9, r9 = run_policy(v, st, [retreat_item({}, 2)], policy=RefusedInputRulePolicy("s", cards=CARDS))
        self.assertEqual((p9.last_progress["result"], r9), ("unevaluable:moved_card_not_basic", None))
        p, restriction = run_policy(v, st, [retreat_item({}, 2)], policy=v10())
        rec = p.last_progress
        self.assertEqual((rec["result"], rec["restricted"], rec["special_moves"], rec["chosen_set"]), ("tier2", True, 2, 2))
        self.assertEqual(allowed_after(st, restriction), frozenset({(3, 31, 1), (3, 33, 1)}))  # 草をバトル場へ移す組だけ（レインボーエネルギーは採点の外）
        self.assertEqual(p.loop_counts["progress_tier2"], 1)

    def test_tier1_basic_move_completes_the_retreat(self):
        v = view(mon(1, VEN, [(11, G)]), [mon(3, BUL, [(31, G), (32, RE)])])
        moves = [(3, 31, G, 1), (3, 32, RE, 1)]
        st = et_stages(moves)
        p, restriction = run_policy(v, st, [retreat_item({11: 1}, 2)], policy=v10())
        self.assertEqual(p.last_progress["result"], "tier1")
        self.assertEqual(allowed_after(st, restriction), frozenset({(3, 31, 1)}))

    def test_no_improving_basic_move_keeps_rainbow_selectable(self):
        """基本エネルギーカードの移動が控えどうしだけで、優先 1・2 にならない。絞らない（レインボーエネルギーをバトル場へ移す組も選べる）。"""
        v = view(mon(1, VEN), [mon(3, BUL, [(31, G), (32, RE)]), mon(4, BUL)])
        moves = [(3, 31, G, 4), (3, 32, RE, 1)]
        st = et_stages(moves)
        p, restriction = run_policy(v, st, [retreat_item({}, 2)], policy=v10())
        rec = p.last_progress
        self.assertEqual((rec["result"], rec["restricted"], rec.get("fallback"), restriction), ("tier3", False, "special_included", None))
        self.assertIn((3, 32, 1), allowed_after(st, restriction))

    def test_basic_only_inputs_match_rules_v8(self):
        v = view(mon(1, VEN), [mon(3, BUL, [(c, G) for c in (31, 32, 33)]), mon(4, BUL, [(c, G) for c in (41, 42, 43)]), mon(5, TAN, [(51, G)])])
        st = et_stages(E1_MOVES)
        p8, r8 = run_policy(v, st, [retreat_item({}, 2)], policy=EnergyTransProgressRulePolicy("s", cards=CARDS))
        p10, r10 = run_policy(v, st, [retreat_item({}, 2)], policy=v10())
        self.assertEqual((p10.last_progress, r10), (p8.last_progress, r8))
        self.assertNotIn("special_moves", p10.last_progress)

    def test_only_special_moves_stay_unevaluable(self):
        v = view(mon(1, VEN), [mon(3, BUL, [(32, RE)])])
        st = et_stages([(3, 32, RE, 1)])
        p, restriction = run_policy(v, st, [retreat_item({}, 2)], policy=v10())
        self.assertEqual((p.last_progress["result"], restriction), ("unevaluable:moved_card_not_basic", None))

    def test_attack_goals_with_special_energy_on_the_active_are_still_skipped(self):
        """バトル場にレインボーエネルギー（色が 1 つに決まらない）: ワザの目標は今までどおり見送り、「にげる」の目標で評価する。"""
        v = view(mon(1, VEN, [(12, RE)], units=[["fighting", "fire", "grass", "lightning", "psychic", "water"]]), [mon(3, BUL, [(31, G), (32, RE)])])
        moves = [(3, 31, G, 1), (3, 32, RE, 1)]
        st = et_stages(moves)
        p, _restriction = run_policy(v, st, [retreat_item({12: 1}, 2)], policy=v10())
        rec = p.last_progress
        self.assertEqual(rec["skipped"].get("attack_special_energy_on_active"), 1)
        self.assertEqual([g["kind"] for g in rec["goals"]], ["retreat"])
        self.assertEqual(rec["result"], "tier1")


class WiringTest(unittest.TestCase):
    def test_policy_identity_and_flags(self):
        p = v10()
        self.assertEqual((p.version, p.distribution, RULES10_VERSION), (10, RULES10_DISTRIBUTION, 10))
        self.assertIs(p.energy_trans_basic_moves, ENERGY_TRANS_BASIC_MOVES)
        self.assertTrue(BasicMovesProgressRulePolicy.progress_basic_moves_only)
        self.assertFalse(RefusedInputRulePolicy.progress_basic_moves_only)
        self.assertFalse(EnergyTransProgressRulePolicy.progress_basic_moves_only)
        self.assertIn("energy_trans_basic_moves", p.loop_summary())
        self.assertIn("refused_input_avoidance", p.loop_summary())  # rules-v9 の記録はそのまま

    def test_mode_and_factory(self):
        self.assertEqual(B.MODES["rules-v10"], {"policy": "rules", "rules_version": 10, "repeat_threshold": 2})
        self.assertEqual(B.TOOL_VERSION, 21)
        config = V.Config(policy="rules", rules_version=10, repeat_threshold=2, policy_seed=1, host_seed=1, game_seed=1)
        players = V.make_policies(config)
        self.assertIsInstance(players[0], BasicMovesProgressRulePolicy)
        self.assertIsInstance(players[1], BasicMovesProgressRulePolicy)
        config9 = V.Config(policy="rules", rules_version=9, repeat_threshold=2, policy_seed=1, host_seed=1, game_seed=1)
        self.assertNotIsInstance(V.make_policies(config9)[0], BasicMovesProgressRulePolicy)


if __name__ == "__main__":
    unittest.main()
