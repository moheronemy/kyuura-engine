"""v0.205: ［バリアー］（「次の相手の番の「ワザ」をうけない」）の相手に、コインでダメージが決まるワザ（［でんこうせっか］型の HeadsBonus・［いしなげ］型の HeadsTimes）を使い、
ワザが相手の対戦ポケモンへのダメージだけで終わるとき、宣言を受け付け、コインを通常どおり投げ、結果のダメージにバリアーを当てる（ダメージ 0）。v0.204 の［まきつく］と同じ、
カード文面に基づく読み方（docs/barrier-coin-damage-v0.205.md。当時の直接裁定は未確認）。v0.4b〜v0.204 は UNRESOLVED_PREVENTED_COIN_DAMAGE で止めた。

- 範囲の外（今までどおり止める）: 自分への効果を含むワザ（［はなびらのまい］）、成否を決めるコイン（［ゴッドバード］）、相手の場から選ぶ［マジックダーツ］、エネルギーの数だけの
  ［たまなげMAX］、バリアーでない無効
"""
from __future__ import annotations

import pathlib
import re
import unittest

from kyuura_engine import EndTurn, EngineError, ResolveDecision, UseAttack, apply_command, state_to_dict
from kyuura_engine import effects as E
from kyuura_engine.coins import CoinSide
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.resolution import programs as PR
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests.helpers import RATTATA, apply_kernel, build_test_state, with_coin_results

ROOT = pathlib.Path(__file__).resolve().parents[1]
H, T = CoinSide.HEADS, CoinSide.TAILS
F, P, G, R, C = "PMCG1-102", "PMCG1-101", "PMCG1-097", "PMCG1-098", "PMCG1-096"
MEWTWO, PIDGEY, GEODUDE = "PMCG1-050", "ES1-024", "PMCG5-046"
QUICK_ATTACK, ROCK_THROW = 1, 0
CODE = "UNRESOLVED_PREVENTED_COIN_DAMAGE"


def board(attacker, *, barrier=True):
    st = build_test_state([{"active": attacker, "bench": [RATTATA]}, {"active": {"card": MEWTWO, "energy": [P, P, P], "damage": 20}, "bench": [RATTATA]}],
                          current_player=1, turn_number=6)
    if not barrier:
        return apply_command(st, EndTurn(1))
    st = apply_command(st, UseAttack(1, 1))  # バリアー
    while st.decision is not None and st.decision.player == 1:
        st = apply_command(st, ResolveDecision(1, st.decision.id, (st.decision.options[0],)))
    return st


def attack(state, index, *sides):
    st = with_coin_results(state, *sides)
    return st, apply_command(st, UseAttack(0, index))


def events(before, after):
    return [dict(e) for e in after.log[len(before.log):]]


def full(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log]


PIDGEY_ = {"card": PIDGEY, "energy": [C, C]}
GEODUDE_ = {"card": GEODUDE, "energy": [F, F]}


class BarrierCoinDamageTest(unittest.TestCase):
    def test_quick_attack_flips_and_barrier_prevents(self):
        for side in (H, T):
            with self.subTest(side=side):
                st, after = attack(board(PIDGEY_), QUICK_ATTACK, side)
                ev = events(st, after)
                self.assertEqual([(e["source"], e["result"]) for e in ev if e["kind"] == "coin_flip"], [("attack", side.value)])
                self.assertEqual([e["kind"] for e in ev][:3], ["attack", "coin_flip", "damage_prevented"])
                self.assertEqual(after.players[1].active.damage, 20)  # ダメージ 0
                self.assertEqual((after.decision, after.current_player), (None, 1))

    def test_rock_throw_flips_three_and_barrier_prevents(self):
        for sides in ((T, T, T), (H, T, T), (H, H, H)):
            with self.subTest(sides=sides):
                st, after = attack(board(GEODUDE_), ROCK_THROW, *sides)
                ev = events(st, after)
                self.assertEqual([e["result"] for e in ev if e["kind"] == "coin_flip"], [s.value for s in sides])
                self.assertEqual([e["kind"] for e in ev][:5], ["attack", "coin_flip", "coin_flip", "coin_flip", "damage_prevented"])
                self.assertNotIn("damage", [e["kind"] for e in ev])
                self.assertEqual(after.players[1].active.damage, 20)

    def test_without_barrier_damage_as_usual(self):
        for attacker, index, sides, amount in ((PIDGEY_, QUICK_ATTACK, (H,), 30), (PIDGEY_, QUICK_ATTACK, (T,), 10), (GEODUDE_, ROCK_THROW, (T, T, T), 0),
                                               (GEODUDE_, ROCK_THROW, (H, T, T), 10), (GEODUDE_, ROCK_THROW, (H, H, H), 30)):
            with self.subTest(card=attacker["card"], sides=sides):
                st, after = attack(board(attacker, barrier=False), index, *sides)
                self.assertEqual([e["amount"] for e in events(st, after) if e["kind"] == "damage"], [amount])

    def test_every_preflight_mode_matches_the_direct_command(self):
        for attacker, index, sides in ((PIDGEY_, QUICK_ATTACK, (H,)), (PIDGEY_, QUICK_ATTACK, (T,)), (GEODUDE_, ROCK_THROW, (H, T, T))):
            st = with_coin_results(board(attacker), *sides)
            direct = full(apply_command(st, UseAttack(0, index)))
            for mode in PREFLIGHT_MODES:
                with self.subTest(card=attacker["card"], mode=mode):
                    self.assertEqual(full(apply_kernel(st, UseAttack(0, index), preflight=mode)), direct)


class ScopeTest(unittest.TestCase):
    def test_user_effect_and_success_coins_still_stop(self):
        vileplume = {"card": "PMCG2-014", "energy": [G, G, G], "evolved_from": ["PMCG2-002", "PMCG2-009"]}  # はなびらのまい（自分のこんらん）
        moltres = {"card": "PMCG3-009", "energy": [R, R, R, R]}  # ゴッドバード（成否を決めるコイン）
        for attacker, index, sides in ((vileplume, 0, (H, H, H)), (moltres, 1, (H,))):
            with self.subTest(card=attacker["card"]), self.assertRaises(EngineError) as caught:
                attack(board(attacker), index, *sides)
            self.assertEqual(caught.exception.code, CODE)

    def test_affected_registrations(self):
        found = {}
        for key in E.DEFAULT_EFFECTS.attack_keys():
            effect = E.DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).effect
            builder = PR.BUILDERS.get(type(effect))
            if builder is None:
                continue
            elements = builder(effect)
            if (any(isinstance(x, PR.Damage) and getattr(type(x.base), "flip_against_damage_only_void", False) and x.local_gate is None for x in elements)
                    and all(isinstance(x, PR.Damage) and x.target == PR.OPP for x in elements)):
                found[type(effect).__name__] = found.get(type(effect).__name__, 0) + 1
        self.assertEqual(found, {"CoinBonusDamage": 63, "CoinFlipDamage": 85, "UserSimplifiedCoinBonusDamage": 2})

    def test_no_card_id_branch_in_engine_or_resolution(self):
        for path in [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]:
            text = path.read_text(encoding="utf-8")
            for card in (MEWTWO, PIDGEY, GEODUDE):
                self.assertIsNone(re.search(rf"[\"']{card}[\"']", text), (path.name, card))


if __name__ == "__main__":
    unittest.main()
