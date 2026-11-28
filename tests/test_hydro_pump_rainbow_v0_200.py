"""v0.200: カメックス（PMCG1-032）の［ハイドロポンプ］で、場で「水」を供給するレインボーエネルギーを「水」エネルギーとして数える。

カード文面「「水」エネルギーを1つ追加すると、10ダメージ追加できる。(追加は2つまで)」と p.90 の最新の説明（「ワザに必要なエネルギーよりも多く「水」エネルギーが
ついているとき、多い「水」エネルギー1個につき」）は、エネルギー（供給の単位）を数える。場のレインボーエネルギーは「どの色の基本エネルギーカードとして使っても
よい」（1 枚 1 個）。カード文面と既存のルールに基づく実装解釈で、当時の直接裁定は未確認（docs/hydro-pump-rainbow-rules-v10-v0.200.md）。

- 基本の「水」だけの場と、同じ「水」の供給をレインボーエネルギーが担う場で、追加のダメージが同じ（費用の分・追加の分・上限 2・同じカードの二重計上なし）
- 適用はこのワザだけ: 同じ ExtraEnergyDamage のみずでっぽうは RB1 のまま、［あまごい］は RB2 のまま、［エナジーコントロール］（特殊エネルギーカードか）は v0.199 のまま
"""
from __future__ import annotations

import pathlib
import re
import unittest

from kyuura_engine import UnsupportedError, UseAttack, UsePokemonPower
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType
from kyuura_engine.coins import CoinSide
from tests.helpers import apply_kernel, build_test_state, with_coin_results

ROOT = pathlib.Path(__file__).resolve().parents[1]
W, G, P, RE, DCE, PE, FHE = "PMCG1-099", "PMCG1-097", "PMCG1-101", "PMCG4-065", "PMCG1-096", "PMCG4-063", "PMCG4-064"
BLASTOISE, SQUIRTLE, WARTORTLE = "PMCG1-032", "PMCG1-023", "PMCG1-027"
MEWTWO_EC, MISTYS_STARMIE, MISTYS_STARYU, RATTATA, BULBASAUR = "PR1-022", "GD2-014", "GD2-013", "PMCG1-060", "PMCG1-001"
RB1, RB2 = "UNRESOLVED_RAINBOW_ENERGY_TYPE", "UNRESOLVED_RAINBOW_ATTACH_AS_TYPE"


def blastoise(energy):
    return {"card": BLASTOISE, "energy": list(energy), "evolved_from": [SQUIRTLE, WARTORTLE]}


def board(active, opponent=None, *, hand=(), opponent_bench=(RATTATA,)):
    return build_test_state([{"active": active, "bench": [RATTATA], "hand": list(hand)},
                             {"active": opponent or {"card": MEWTWO_EC, "energy": []}, "bench": list(opponent_bench)}], turn_number=5)


def damage(test, state, command):
    after = apply_kernel(state, command)
    return [e["amount"] for e in after.log[len(state.log):] if e["kind"] == "damage"]


def stops(test, state, command, code):
    with test.assertRaises(UnsupportedError) as caught:
        apply_kernel(state, command)
    test.assertEqual(caught.exception.code, code)


class HydroPumpRainbowTest(unittest.TestCase):
    def test_same_water_supply_gives_the_same_extra_damage(self):
        for basic, rainbow, amount in (((W, W, W), (W, W, RE), 40),          # レインボーエネルギーが費用の分を払う（追加 0）
                                       ((W, W, W, W), (W, W, W, RE), 50),    # 追加 1
                                       ((W,) * 5, (W, W, W, W, RE), 60),     # 追加 2
                                       ((W,) * 5, (W, W, W, RE, RE), 60),    # 2 枚とも 1 個ずつ
                                       ((W,) * 6, (W,) * 5 + (RE,), 60)):    # 上限 2
            with self.subTest(basic=basic, rainbow=rainbow):
                self.assertEqual(damage(self, board(blastoise(basic)), UseAttack(0, 0)), [amount])
                self.assertEqual(damage(self, board(blastoise(rainbow)), UseAttack(0, 0)), [amount])

    def test_one_rainbow_counts_once_and_other_special_energy_is_not_water(self):
        self.assertEqual(damage(self, board(blastoise((W, W, W, RE))), UseAttack(0, 0)), [50])
        self.assertEqual(damage(self, board(blastoise((W, W, W, RE, DCE))), UseAttack(0, 0)), [50])
        self.assertEqual(damage(self, board(blastoise((W, W, W, RE, PE, FHE))), UseAttack(0, 0)), [50])
        blast = board(blastoise((W, W, RE)))
        self.assertEqual(E.rainbow_typed_unit_count(blast, blast.players[0].active, EnergyType.WATER), 1)
        self.assertEqual(E.rainbow_typed_unit_count(blast, blast.players[0].active, EnergyType.GRASS), 1)

    def test_boards_of_the_9094_refusals_are_accepted(self):
        """0.199.0 の seed 9094 で RB1 で拒否された 2 つの盤面（カメックスのエネルギーの並び）。v0.200 は受理し、「水」5 個 → 60・4 個 → 50。"""
        self.assertEqual(damage(self, board(blastoise((FHE, W, W, PE, G, W, G, G, PE, W, RE, G))), UseAttack(0, 0)), [60])
        self.assertEqual(damage(self, board(blastoise((W, W, PE, G, G, G, W, RE, G))), UseAttack(0, 0)), [50])

    def test_only_this_registration_counts_rainbow(self):
        self.assertTrue(E.DEFAULT_EFFECTS.attack_entry(BLASTOISE, 0).effect.rainbow_provides_type)
        others = [(k.card_id, k.attack_index) for k in E.DEFAULT_EFFECTS.attack_keys()
                  if isinstance(E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect, E.ExtraEnergyDamage)
                  and E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect.rainbow_provides_type]
        self.assertEqual(sorted(others), [("IPH-002", 0), (BLASTOISE, 0), ("PR1-028", 0)])  # PMCG1-032 と、その再録（Reprint）の 2 枚だけ

    def test_no_card_id_branch_in_engine_or_resolution(self):
        for path in [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]:
            self.assertNotIn("PMCG1-032", path.read_text(encoding="utf-8"), path.name)
        self.assertIsNone(re.search(r"rainbow_provides_type\s*=\s*True", (ROOT / "kyuura_engine" / "resolution" / "programs.py").read_text(encoding="utf-8")))


class ControlTest(unittest.TestCase):
    def test_water_gun_with_rainbow_still_stops_rb1(self):
        stops(self, board({"card": MISTYS_STARMIE, "energy": [W, RE], "evolved_from": MISTYS_STARYU}), UseAttack(0, 0), RB1)

    def test_rain_dance_with_rainbow_still_stops_rb2(self):
        state = board(blastoise((W, W, W)), hand=(RE,))
        b = state.players[0].active
        re_uid = next(u for u in state.players[0].hand if state.cards[u].card_id == RE)
        stops(self, state, UsePokemonPower(0, b.pokemon_id, 0, energy=re_uid, target=b.pokemon_id), RB2)

    def test_energy_control_keeps_the_v0_199_behaviour(self):
        for side in (CoinSide.HEADS, CoinSide.TAILS):
            with self.subTest(side=side):
                state = with_coin_results(board({"card": MEWTWO_EC, "energy": [P]}, {"card": BULBASAUR, "energy": []},
                                                opponent_bench=({"card": BULBASAUR, "energy": [DCE, RE]},)), side)
                after = apply_kernel(state, UseAttack(0, 0))
                self.assertIsNone(after.decision)
                self.assertEqual([e for e in after.log[len(state.log):] if e["kind"] == "move_opponent_energy"], [])


if __name__ == "__main__":
    unittest.main()
