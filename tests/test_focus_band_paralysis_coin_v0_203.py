"""v0.203: きあいのハチマキ（neo1-088）のついたポケモンが相手のワザのダメージで残りHPがなくなり、同じワザのあとの処理がそのポケモンをマヒにするかを決めるコインを投げる
とき（ゼニガメの［あわ］など ``ParalyzeOnHeads``）、残りHPがなくなった時点できあいのハチマキのコインを投げる（v0.81〜v0.202 は FB1 ``UNRESOLVED_FOCUS_BAND_TIMING`` で止めた）。
カード文面の「残りHPがなくなったとき、コインを投げる」に沿った実装解釈（利用者が選んだ読み方 A。docs/focus-band-paralysis-coin-v0.203.md）。

- ハチマキが「おもて」: 残りHP 10 のポケモンにワザの処理を続ける（マヒのコインを投げ、「おもて」ならマヒ）。ハチマキはトラッシュ
- ハチマキが「うら」: 残りHPがないまま。マヒのコインは投げず、きぜつ（きぜつの判定の窓でハチマキのコインを投げ直さない）
- 範囲の外（あとのダメージ・ダメージカウンター・ほかの効果（どくなど）・［こらえる］の KS1）は今までどおり止める
"""
from __future__ import annotations

import pathlib
import re
import unittest

from kyuura_engine import UnsupportedError, UseAttack, apply_command, state_to_dict
from kyuura_engine.coins import CoinSide
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests.helpers import RATTATA, SQUIRTLE, WEEDLE, apply_kernel, build_test_state, with_coin_results

ROOT = pathlib.Path(__file__).resolve().parents[1]
H, T = CoinSide.HEADS, CoinSide.TAILS
W, G, P = "PMCG1-099", "PMCG1-097", "PMCG1-101"
MEWTWO, BAND = "PR1-022", "neo1-088"  # ミュウツー（HP 60）。seed 9099 の盤面と同じ形（ダメージ 50）
FB1 = "UNRESOLVED_FOCUS_BAND_TIMING"


def board(attacker=None, *, damage=50, band=True):
    defender = {"card": MEWTWO, "energy": [P], "damage": damage, **({"trainers": [(BAND, None)]} if band else {})}
    return build_test_state([{"active": defender, "bench": [RATTATA], "deck": [W] * 10, "prizes": 6},
                             {"active": attacker or {"card": SQUIRTLE, "energy": [W]}, "bench": [RATTATA], "deck": [W] * 10, "prizes": 6}],
                            current_player=1, turn_number=8)


def bubble(state, *sides):
    st = with_coin_results(state, *sides)
    return st, apply_command(st, UseAttack(1, 0))


def events(before, after):
    return [dict(e) for e in after.log[len(before.log):]]


def full(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log]


class FocusBandBeforeParalysisCoinTest(unittest.TestCase):
    def test_heads_band_continues_bubble_on_the_survivor(self):
        for second, paralyzed in ((H, True), (T, False)):
            with self.subTest(bubble=second):
                st, after = bubble(board(), H, second)
                ev = events(st, after)
                self.assertEqual([(e["source"], e["result"]) for e in ev if e["kind"] == "coin_flip"], [("trainer", "heads"), ("attack", second.value)])
                self.assertEqual([e["kind"] for e in ev][:6], ["attack", "damage", "coin_flip", "focus_band", "discard_attached_trainer", "coin_flip"])
                mewtwo = after.players[0].active
                self.assertEqual((mewtwo.damage, mewtwo.conditions.paralyzed), (50, paralyzed))  # 残りHP 10
                self.assertNotIn("knock_out", [e["kind"] for e in ev])
                self.assertEqual((after.decision, after.current_player), (None, 0))  # 番が相手へ移る

    def test_tails_band_knocks_out_without_the_bubble_coin(self):
        st, after = bubble(board(), T, H)
        ev = events(st, after)
        self.assertEqual([(e["source"], e["result"]) for e in ev if e["kind"] == "coin_flip"], [("trainer", "tails")])  # あわのコインは投げない
        self.assertEqual([e["survived"] for e in ev if e["kind"] == "focus_band"], [False])  # きぜつの判定の窓で投げ直さない
        self.assertEqual(sum(1 for e in ev if e["kind"] == "knock_out"), 1)

    def test_every_preflight_mode_matches_the_direct_command(self):
        for sides in ((H, H), (H, T), (T, H)):
            st = with_coin_results(board(), *sides)
            direct = full(apply_command(st, UseAttack(1, 0)))
            for mode in PREFLIGHT_MODES:
                with self.subTest(sides=sides, mode=mode):
                    self.assertEqual(full(apply_kernel(st, UseAttack(1, 0), preflight=mode)), direct)

    def test_without_band_or_with_hp_left_nothing_changes(self):
        st, after = bubble(board(band=False), H)
        self.assertEqual([e["kind"] for e in events(st, after) if e["kind"] in ("coin_flip", "knock_out")], ["knock_out"])
        st, after = bubble(board(damage=40), H)  # 残りHPが残る（ハチマキははたらかない）
        self.assertTrue(after.players[0].active.conditions.paralyzed)
        self.assertNotIn("focus_band", [e["kind"] for e in events(st, after)])


class ScopeTest(unittest.TestCase):
    def test_other_effects_after_damage_still_stop(self):
        with self.assertRaises(UnsupportedError) as caught:  # ビードルの［どくばり］（「おもて」ならどく。マヒでない）
            bubble(board({"card": WEEDLE, "energy": [G]}), H, H)
        self.assertEqual(caught.exception.code, FB1)

    def test_no_card_id_branch_in_engine_or_resolution(self):
        for path in [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]:
            text = path.read_text(encoding="utf-8")
            for card in (BAND, SQUIRTLE, MEWTWO):
                self.assertIsNone(re.search(rf"[\"']{card}[\"']", text), (path.name, card))


if __name__ == "__main__":
    unittest.main()
