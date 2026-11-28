"""v0.204: ［バリアー］（「次の相手の番の「ワザ」をうけない」）の相手に、ダメージのあとに特殊状態を決めるコインのワザ（ミニリュウの［まきつく］など）を使うとき、宣言を受け付け、
この要素のコインを通常どおり 1 回投げる。バリアーが、相手へのダメージと特殊状態を無効にする（v0.31〜v0.203 は HC3 ``UNRESOLVED_PREVENTED_EFFECT_COIN`` で止めた）。
「ワザをうけない」を、ワザを受けるポケモンへの処理に当てた実装解釈（docs/barrier-effect-coin-v0.204.md。当時の直接裁定は未確認）。

- 範囲: 相手の対戦ポケモンへの、この要素のコインで特殊状態を決める要素（ほかの条件なし）で、同じワザの前に相手へのダメージの要素があるもの（``Status.barrier_effect_coin_path``）
- 範囲の外（今までどおり止める）: コインでダメージの量を決めるワザ（［いしなげ］）、ダメージのない効果のコイン（［なめる］）、バリアーでない効果の要素を無効にする効果
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
F, P, G = "PMCG1-102", "PMCG1-101", "PMCG1-097"
MEWTWO, DRATINI, WEEDLE, GEODUDE, LICKITUNG = "PMCG1-050", "PMCG4-051", "PMCG1-004", "PMCG5-046", "ES1-030"
HC3 = "UNRESOLVED_PREVENTED_EFFECT_COIN"


def board(attacker, *, barrier=True):
    """主体 1 のミュウツー（ダメージ 20）が［バリアー］を使う（または番を終える）、主体 0 の番。"""
    st = build_test_state([{"active": attacker, "bench": [RATTATA]}, {"active": {"card": MEWTWO, "energy": [P, P, P], "damage": 20}, "bench": [RATTATA]}],
                          current_player=1, turn_number=6)
    if not barrier:
        return apply_command(st, EndTurn(1))
    st = apply_command(st, UseAttack(1, 1))
    while st.decision is not None and st.decision.player == 1:
        st = apply_command(st, ResolveDecision(1, st.decision.id, (st.decision.options[0],)))
    return st


def attack(state, *sides):
    st = with_coin_results(state, *sides)
    return st, apply_command(st, UseAttack(0, 0))


def events(before, after):
    return [dict(e) for e in after.log[len(before.log):]]


def full(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log]


class BarrierEffectCoinTest(unittest.TestCase):
    def test_wrap_is_accepted_and_flips_once_against_barrier(self):
        for side in (H, T):
            with self.subTest(side=side):
                st, after = attack(board({"card": DRATINI, "energy": [F, F]}), side)
                ev = events(st, after)
                self.assertEqual([(e["source"], e["result"]) for e in ev if e["kind"] == "coin_flip"], [("attack", side.value)])
                expected = ["attack", "damage_prevented", "coin_flip"] + (["effect_prevented"] if side is H else [])  # 「うら」なら無効にする効果がない
                self.assertEqual([e["kind"] for e in ev][:len(expected)], expected)
                self.assertNotIn("special_condition", [e["kind"] for e in ev])
                mewtwo = after.players[1].active
                self.assertEqual((mewtwo.damage, mewtwo.conditions.paralyzed), (20, False))  # ダメージもマヒもない
                self.assertEqual((after.decision, after.current_player), (None, 1))  # 番が相手へ移る

    def test_without_barrier_damage_and_paralysis_as_usual(self):
        for side, paralyzed in ((H, True), (T, False)):
            with self.subTest(side=side):
                st, after = attack(board({"card": DRATINI, "energy": [F, F]}, barrier=False), side)
                mewtwo = after.players[1].active
                self.assertEqual((mewtwo.damage, mewtwo.conditions.paralyzed), (30, paralyzed))

    def test_same_path_for_poison(self):
        st, after = attack(board({"card": WEEDLE, "energy": [G]}), H)
        self.assertIsNone(after.players[1].active.conditions.poison)
        self.assertEqual(sum(1 for e in events(st, after) if e["kind"] == "coin_flip"), 1)

    def test_every_preflight_mode_matches_the_direct_command(self):
        for side in (H, T):
            st = with_coin_results(board({"card": DRATINI, "energy": [F, F]}), side)
            direct = full(apply_command(st, UseAttack(0, 0)))
            for mode in PREFLIGHT_MODES:
                with self.subTest(side=side, mode=mode):
                    self.assertEqual(full(apply_kernel(st, UseAttack(0, 0), preflight=mode)), direct)


class ScopeTest(unittest.TestCase):
    def test_coin_damage_and_effect_only_coins_still_stop(self):
        for attacker, sides, code in (({"card": GEODUDE, "energy": [F, F]}, (H, H, H), "UNRESOLVED_PREVENTED_COIN_DAMAGE"),  # いしなげ（コインでダメージの量）
                                      ({"card": LICKITUNG, "energy": [F]}, (H,), HC3)):  # なめる（ダメージのない「おもて」ならマヒ）
            with self.subTest(card=attacker["card"]), self.assertRaises(EngineError) as caught:
                attack(board(attacker), *sides)
            self.assertEqual(caught.exception.code, code)

    def test_affected_registrations(self):
        """この経路の要素を持つ登録の型（v0.204 の範囲。docs/barrier-effect-coin-v0.204.md）。"""
        found = {}
        for key in E.DEFAULT_EFFECTS.attack_keys():
            effect = E.DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).effect
            builder = PR.BUILDERS.get(type(effect))
            if builder is None:
                continue
            elements = builder(effect)
            for i, element in enumerate(elements):
                if (isinstance(element, PR.Status) and element.target == PR.OPP and element.local_coin is not None and element.otherwise is None
                        and element.gate is None and element.if_result is None and element.after_switch is None and element.after_damage is None
                        and element.poison_damage is None and element.poison_multiplier == 1
                        and i > 0 and all(isinstance(x, PR.Damage) and x.target == PR.OPP for j, x in enumerate(elements) if j != i)):
                    found[type(effect).__name__] = found.get(type(effect).__name__, 0) + 1
        # 自分への効果を含むワザ（ねころぶ・ほねこんぼう・どくばりタックル）は範囲の外（今までどおり HC3）
        self.assertEqual(found, {"ParalyzeOnHeads": 95, "PoisonOnHeads": 30, "ConfuseOnHeads": 31, "DamageThenSleepOnHeads": 7})

    def test_no_card_id_branch_in_engine_or_resolution(self):
        for path in [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]:
            text = path.read_text(encoding="utf-8")
            for card in (MEWTWO, DRATINI):
                self.assertIsNone(re.search(rf"[\"']{card}[\"']", text), (path.name, card))


if __name__ == "__main__":
    unittest.main()
