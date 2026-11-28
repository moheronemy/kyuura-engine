"""v0.202: 「コインを N 枚投げ、「おもて」の数×M のダメージ」のワザ（``CoinFlipDamage`` などの ×のコイン → 解決の基盤の ``HeadsTimes``）を、ダメージだけを
無効にする効果（「からにこもる」「かたまる」。効果の窓を持たない）のある相手に使うとき、通常どおりコインを投げ、結果で決まるダメージに無効を当てる
（v0.4b〜v0.201 は ``UNRESOLVED_PREVENTED_COIN_DAMAGE`` で止めた）。v0.201 の ``HeadsBonus`` と同じ、カード文面と既存のルールに基づく実装解釈。当時の直接裁定は
未確認（docs/coin-times-prevented-damage-v0.202.md）。0.201.0 の拡大監査で、タケシのイシツブテの［いしなげ］がこの組で 10 回拒否された。
登録の側の判定（``CoinFlipDamage.problem``。先読みの方法 legacy と v0.13 の経路）も止めない（解決の基盤と同じ答え）。

- ワザ全体を受けない効果（バリアー。効果の窓も持つ）は今までどおり止める
- エネルギーの数だけコインを投げる［たまなげMAX］（``HeadsTimesAttachedEnergy``）、相手の場から選ぶ［マジックダーツ］（別の経路）、失敗を決めるコイン（ゴッドバード）、
  同じ登録の側の関数を使う［いかりのスーパーパンチ］（``CoinHeadsDamagePerOwnCounter``）は変えない
- 後に効果のあるワザ（［はなびらのまい］の自分のこんらん）は、ダメージの無効のあとも文面どおり処理する
"""
from __future__ import annotations

import pathlib
import re
import unittest

from kyuura_engine import EndTurn, EngineError, ResolveDecision, UnsupportedError, UseAttack, apply_command, state_to_dict
from kyuura_engine import effects as E
from kyuura_engine.coins import CoinSide
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.resolution import programs as PR
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests.helpers import apply_kernel, build_test_state, with_coin_results

ROOT = pathlib.Path(__file__).resolve().parents[1]
H, T = CoinSide.HEADS, CoinSide.TAILS
F, P, W, G, R = "PMCG1-102", "PMCG1-101", "PMCG1-099", "PMCG1-097", "PMCG1-098"
GEODUDE, WARTORTLE, SQUIRTLE, MEWTWO, METAPOD, RATTATA = "PMCG5-046", "PMCG1-027", "PMCG1-023", "PMCG1-050", "PMCG1-009", "PMCG1-060"
CODE = "UNRESOLVED_PREVENTED_COIN_DAMAGE"
ROCK_THROW = 0  # タケシのイシツブテの［いしなげ］（コイン 3 枚・「おもて」の数×10）


def after_defense(defender, attack_index, side, attacker=None):
    """主体 1 のバトル場が attack_index のワザを side のコインで使い（None なら番を終える）、主体 0 の番にする。"""
    st = build_test_state([{"active": attacker or {"card": GEODUDE, "energy": [F, F]}, "bench": [RATTATA]},
                           {"active": defender, "bench": [RATTATA]}], current_player=1, turn_number=6)
    if attack_index is None:
        return apply_command(st, EndTurn(1))
    st = apply_command(with_coin_results(st, side) if side else st, UseAttack(1, attack_index))
    while st.decision is not None and st.decision.player == 1:
        st = apply_command(st, ResolveDecision(1, st.decision.id, (st.decision.options[0],)))
    return st


def attack(state, sides, index=ROCK_THROW):
    st = with_coin_results(state, *sides)
    return st, apply_command(st, UseAttack(0, index))


def new_events(before, after):
    return [dict(e) for e in after.log[len(before.log):]]


WITHDRAW = ({"card": WARTORTLE, "energy": [W, W], "evolved_from": SQUIRTLE}, 0, H)  # カメールの［からにこもる］（「おもて」）


class DamageOnlyPreventionTest(unittest.TestCase):
    def test_withdraw_flips_all_coins_and_prevents_the_damage(self):
        base = after_defense(*WITHDRAW)
        for sides in ((H, H, H), (H, T, T), (T, T, T)):
            with self.subTest(sides=sides):
                st, after = attack(base, sides)
                ev = new_events(st, after)
                kinds = [e["kind"] for e in ev]
                self.assertEqual([(e["source"], e["result"]) for e in ev if e["kind"] == "coin_flip"], [("attack", s.value) for s in sides])  # 3 枚、ワザのコイン
                self.assertEqual(kinds[:5], ["attack", "coin_flip", "coin_flip", "coin_flip", "damage_prevented"])  # コインのあとに無効
                self.assertNotIn("damage", kinds)
                self.assertEqual(after.players[1].active.damage, 0)
                self.assertEqual((after.decision, after.current_player), (None, 1))  # 番が相手へ移る

    def test_harden_is_also_damage_only(self):
        base = after_defense({"card": METAPOD, "energy": [G, G], "evolved_from": "PMCG1-004"}, 0, H)  # トランセルの［かたまる］（「おもて」）
        st, after = attack(base, (H, H, T))
        kinds = [e["kind"] for e in new_events(st, after)]
        self.assertEqual(kinds[:5], ["attack", "coin_flip", "coin_flip", "coin_flip", "damage_prevented"])

    def test_without_prevention_the_coins_decide_the_damage(self):
        base = after_defense(WITHDRAW[0], None, None)
        for sides, amount in (((H, H, H), 30), ((H, T, T), 10), ((T, T, T), 0)):
            with self.subTest(sides=sides):
                st, after = attack(base, sides)
                self.assertEqual([e["amount"] for e in new_events(st, after) if e["kind"] == "damage"], [amount])


def full(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log]


class ModeParityTest(unittest.TestCase):
    def test_every_preflight_mode_matches_the_direct_command(self):
        """先読みの 3 つの方法（登録の側の判定を使う legacy を含む）で、受け付け・状態・記録が直接のコマンドと同じ。"""
        for defense in (WITHDRAW, (WITHDRAW[0], None, None)):
            base = after_defense(*defense)
            for sides in ((H, H, H), (H, T, T), (T, T, T)):
                st = with_coin_results(base, *sides)
                direct = full(apply_command(st, UseAttack(0, ROCK_THROW)))
                for mode in PREFLIGHT_MODES:
                    with self.subTest(prevented=defense[1] is not None, sides=sides, mode=mode):
                        self.assertEqual(full(apply_kernel(st, UseAttack(0, ROCK_THROW), preflight=mode)), direct)

    def test_registration_check_no_longer_stops(self):
        base = after_defense(*WITHDRAW)
        use = E.AttackUse(0, base.players[0].active.pokemon_id, E.AttackKey(GEODUDE, ROCK_THROW))
        self.assertIsNone(E.CoinFlipDamage(coins=3, damage_per_heads=10).problem(base, use))
        self.assertIsNotNone(E.prevented_coin_damage_problem(base, use))  # 同じ盤面で、ほかの型（いかりのスーパーパンチ）が使う関数は今までどおり止める


class FollowUpEffectTest(unittest.TestCase):
    def test_petal_dance_confuses_the_user_after_the_prevented_damage(self):
        vileplume = {"card": "PMCG2-014", "energy": [G, G, G], "evolved_from": ["PMCG2-002", "PMCG2-009"]}  # ラフレシアの［はなびらのまい］
        base = after_defense(*WITHDRAW, attacker=vileplume)
        for sides in ((T, T, T), (H, H, T)):
            with self.subTest(sides=sides):
                st, after = attack(base, sides, 0)
                kinds = [e["kind"] for e in new_events(st, after)]
                self.assertEqual(kinds[:6], ["attack", "coin_flip", "coin_flip", "coin_flip", "damage_prevented", "special_condition"])
                self.assertTrue(after.players[0].active.conditions.confused)  # 「その後、自分は「こんらん」状態になる」
                self.assertEqual(after.players[1].active.damage, 0)


class WholeAttackPreventionTest(unittest.TestCase):
    def test_barrier_still_stops_before_the_coins(self):
        base = after_defense({"card": MEWTWO, "energy": [P, P, P]}, 1, None)  # バリアー（ワザを受けない）
        for sides in ((H, H, H), (T, T, T)):
            with self.subTest(sides=sides), self.assertRaises(UnsupportedError) as caught:
                attack(base, sides)
            self.assertEqual(caught.exception.code, CODE)


class ScopeTest(unittest.TestCase):
    def test_flag_is_on_heads_times_and_heads_bonus_only(self):
        self.assertTrue(PR.HeadsTimes.flip_against_damage_only_void)
        self.assertTrue(PR.HeadsBonus.flip_against_damage_only_void)  # v0.201
        for name in ("HeadsTimesAttachedEnergy", "OpponentTailsBonus", "PrintedPlusHeadsTimes"):
            self.assertFalse(getattr(getattr(PR, name), "flip_against_damage_only_void", False), name)
        self.assertEqual(PR.BUILDERS[E.CoinFlipDamage](E.CoinFlipDamage(coins=3, damage_per_heads=10))[0].base, PR.HeadsTimes(3, 10))

    def test_energy_count_coins_still_stop_against_withdraw(self):
        exeggutor = next(k for k in E.DEFAULT_EFFECTS.attack_keys() if E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).name_ja == "たまなげMAX")
        base = after_defense(*WITHDRAW, attacker={"card": exeggutor.card_id, "energy": [G, G, G], "evolved_from": "PMCG2-006"})
        with self.assertRaises(UnsupportedError) as caught:
            attack(base, (H, H, H), exeggutor.attack_index)
        self.assertEqual(caught.exception.code, CODE)

    def test_other_coin_paths_still_stop_against_withdraw(self):
        darts = next(k for k in E.DEFAULT_EFFECTS.attack_keys() if E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).name_ja == "マジックダーツ")
        for attacker, index, sides in (({"card": darts.card_id, "energy": [P, P]}, darts.attack_index, (H, H, H)),  # 相手の場から選ぶ（別の経路）
                                       ({"card": "PMCG3-009", "energy": [R, R, R, R]}, 1, (H,)),  # ゴッドバード（失敗を決めるコイン）
                                       ({"card": "PMCG6-057", "energy": [F, F]}, 1, (H,))):  # いかりのスーパーパンチ（登録の側の同じ関数）
            with self.subTest(card=attacker["card"]):
                base = after_defense(*WITHDRAW, attacker=attacker)
                with self.assertRaises(EngineError) as caught:
                    st, after = attack(base, sides, index)
                    while after.decision is not None and after.decision.resume == "attack":  # マジックダーツは選ぶときに止まる
                        d = after.decision
                        after = apply_command(after, ResolveDecision(d.player, d.id, tuple(d.options[:max(1, d.min_choices)])))
                self.assertEqual(caught.exception.code, CODE)

    def test_no_card_id_branch_in_engine_or_resolution(self):
        for path in [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]:
            self.assertIsNone(re.search(r"[\"']PMCG5-046[\"']", path.read_text(encoding="utf-8")), path.name)


if __name__ == "__main__":
    unittest.main()
