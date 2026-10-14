"""v0.14: プロトタイプ（experiments/event_kernel）と v0.13 のエンジンを、new_game からの対戦の 1 歩ごとに比べる（B 段階。
docs/event-prototype-verification-v0.14.md 3 章）。大きな比較は ``python3 tools/event_kernel_compare.py``（C 段階）。

- 1 歩ごとに、拒否するか（例外の種類とコード）・受け付けた状態（書き出しの形式 9。ログ・乱数の指紋・決定を含む）が同じで、渡した状態が
  変わらない（tools/event_kernel_compare.py の ``Comparator``）。先読みは 2 つ（``derived``・``legacy``）の両方。
- 次の歩の状態を、v0.13 とプロトタイプの結果から交互に選ぶ（``mixed``。どちらの状態からでも、どちらのエンジンで続けても同じ）。
- 特殊能力・番をまたぐ効果の組（とうめい・はんげき・こんじょう・ふしちょう・ほのおのかべ・こうらがえし・かがくへんかガス）と、それぞれの
  対戦のテスト（tests/test_*_games_v0_*.py の方針）を使う。比べた場面の数（窓・枠・決定）が 0 でないことも確かめる。
"""

from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import event_kernel_compare as compare  # noqa: E402
import stress_engine as stress  # noqa: E402

from kyuura_engine import check_invariants  # noqa: E402
from tests.log_audit import log_problems, serialization_problems  # noqa: E402

STRESS = ("haunter", "machamp", "giovanni_mixed", "moltres_mixed", "wartortle_mixed", "muk_mixed")
NATURAL = ("test_haunter_games_v0_9", "test_machamp_games_v0_10", "test_giovanni_games_v0_11", "test_moltres_games_v0_12",
           "test_dark_wartortle_games_v0_13", "test_muk_games_v0_8", "test_butterfree_games_v0_4d", "test_confusion_games")


class LockstepGamesTest(unittest.TestCase):
    def test_stress_scenarios_in_both_modes_with_mixed_states(self):
        """tools/stress_engine.py の組（拒否されるコマンドを混ぜる）。2 つの先読み・交互の状態で、どの歩も同じ。"""
        counts: Counter = Counter()
        comparator = compare.Comparator(compare.MODES, mixed=True, counts=counts)
        by_name = {s.name: s for s in stress.ALL_SCENARIOS}
        for name in STRESS:
            for seed in range(2):
                with self.subTest(scenario=name, seed=seed):
                    final = compare.stress_game(comparator, by_name[name], seed, steps=400)
                    self.assertEqual(check_invariants(final), [])
                    self.assertEqual(log_problems(final), [])
                    self.assertEqual(serialization_problems(final), [])
        self.assertGreater(counts["owned"], 1000)
        for key in ("activated:transparency", "activated:strikes_back", "activated:retaliation", "frame:retaliation",
                    "frame:power_damage", "suspended:take_prize"):
            self.assertGreater(counts[key], 0, key)

    def test_natural_policies_in_both_modes(self):
        """対戦のテストの方針（play_game）。テスト自身の確認（不変条件・ログの監査）もそのまま走る。"""
        counts: Counter = Counter()
        comparator = compare.Comparator(compare.MODES, counts=counts)
        for name in NATURAL:
            with self.subTest(module=name):
                compare.natural_games(comparator, name, range(2))
        self.assertEqual(counts["games"], 2 * len(NATURAL))
        for key in ("activated:transparency", "activated:strikes_back", "activated:retaliation", "candidate:ko_check:guts",
                    "candidate:ko_process:rebirth"):
            self.assertGreater(counts[key], 0, key)

    def test_natural_policies_with_mixed_states(self):
        """次の歩の状態を交互に選んでも、対戦のテストの確認が通り、どの歩も同じ。"""
        comparator = compare.Comparator(("derived",), mixed=True)
        for name in ("test_giovanni_games_v0_11", "test_moltres_games_v0_12"):
            with self.subTest(module=name):
                compare.natural_games(comparator, name, range(2))

    def test_a_divergence_is_reported(self):
        """比べる関数自身の確認: プロトタイプの答えを変えると ``Divergence``（比較が何も見ていない、を防ぐ）。"""
        from experiments.event_kernel import kernel as KN
        original = KN.ACTIONS["power_damage_to_damage_source"]

        def noisy(res, fs, deferred):
            original(res, fs, deferred)
            res.state.add_event("note", text="prototype only")  # 公開のログに 1 つ多い

        KN.ACTIONS["power_damage_to_damage_source"] = noisy
        try:
            with self.assertRaises(compare.Divergence):
                compare.natural_games(compare.Comparator(("derived",)), "test_machamp_games_v0_10", range(3))
        finally:
            KN.ACTIONS["power_damage_to_damage_source"] = original


if __name__ == "__main__":
    unittest.main()
