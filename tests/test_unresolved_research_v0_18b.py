"""v0.18b: Z23（「ダメージを与えた後、…」の効果を、ダメージを与えなかったときに与えるか）の場合分け。docs/unresolved-research-v0.18b.md 3 章。

kyuura の論点 UQ-EFFECT-AFTER-NO-DAMAGE（kyuura `adf9710`）は、ダメージを与えなかった場合を 1 つの問いに含めているが、場合ごとに当てはまる規定が違う
（p.321「ダメージを受けない」状態で要素が無効・p.319 最終ダメージが 0・p.159/p.160「とうめい」・p.309 対象がいない）。どれか 1 つの答えで、ほかの
場合を同じに扱う根拠にはならないので、場合ごとに「止まること・状態が変わらないこと・理由の文がその場合を書くこと」を確かめる。成功を仮定するテストは
書かない。

根拠のページ: p.155（ナツメのヤドン「ぐうたらこうげき」の最新の説明と解説）・p.245（R団のカビゴン「たおれこむ」）・p.309・p.319〜p.321・p.159・p.160。
kyuura の記録 id: UQ-EFFECT-AFTER-NO-DAMAGE・LD-PMCG6-073-ATK0（NEO-2000-OFFICIAL-RULES）。
"""

from __future__ import annotations

import unittest

from kyuura_engine import UnsupportedError, UseAttack, apply_command, state_to_dict
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.resolution import PREFLIGHT_MODES, programs
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import (
    ABRA, CATERPIE, DEFENDER, FIRE, GASTLY, H, HAUNTER, MACHOP, METAPOD, PSYCHIC, RATTATA, ROCKETS_SNORLAX, T, apply_kernel,
    build_test_state, with_coin_results,
)

TURN = 7  # プレイヤー 0 の番
NO_DAMAGE = "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE"
PREVENTED = "「ダメージを受けない」状態で無効"  # Z23-a
ZERO = "最終ダメージが 0"  # Z23-b
EVADED = "「とうめい」で受けなかった"  # Z23-c


def board(mine, theirs, **kwargs):
    return build_test_state([{"active": mine, "bench": [RATTATA]}, {"active": theirs, "bench": [RATTATA]}], turn_number=TURN, **kwargs)


def snapshot(state):
    return state_to_dict(state, format_version=9), rng_fingerprint(state.rng), len(state.log)


def snorlax():
    return {"card": ROCKETS_SNORLAX, "energy": [FIRE] * 3}  # たおれこむ（無色）


def psychic_self_sleep_registry():
    """テスト専用: ケーシィの「ねんりき」（超 10）を「ダメージを与えた後、自分を「ねむり」状態にする」（DamageAndSelfSleep）として登録した表。
    抵抗力 超 −30 のコラッタに使うと、最終ダメージが 0 になる（Z23-b の抵抗力の場合。たおれこむは無色なので抵抗力では起こらない）。"""
    attack = load_card_pool().get(ABRA).attacks[0]
    registry = E.DEFAULT_EFFECTS.with_attacks("test-psychic-self-sleep", {
        E.AttackKey(ABRA, 0): E.AttackEntry(E.DamageAndSelfSleep(), attack.name_ja, text_ja=attack.text_ja, play_text_ja="（テスト）", source="test"),
    })
    return registry, pool_from_extract(read_extract(), registry)


class EffectAfterNoDamageSubcaseTest(unittest.TestCase):
    """Z23 の場合ごとに、宣言の前に止まり（こんらんのコインの前）、状態・乱数・ログが変わらず、理由の文がその場合を書く。"""

    def assert_stops(self, state, why, *, coin=None):
        if coin is not None:
            state = with_coin_results(state, coin)
        before = snapshot(state)
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, NO_DAMAGE)
        self.assertIn(f"（{why}）", str(ctx.exception))
        self.assertEqual(snapshot(state), before)

    def test_z23_a_prevented_element(self):
        """Z23-a: 相手が「ダメージを受けない」状態（かたまる）。ダメージの要素そのものが無効（p.321）。"""
        self.assert_stops(board(snorlax(), {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": TURN - 1}), PREVENTED)

    def test_z23_b_zero_by_defender(self):
        """Z23-b: ディフェンダーで 20 − 20 = 0。要素は有効で、最終ダメージが 0（p.319「ダメージを与えなかった」）。"""
        self.assert_stops(board(snorlax(), {"card": MACHOP, "trainers": [(DEFENDER, TURN)]}), ZERO)

    def test_z23_b_zero_by_resistance(self):
        """Z23-b: 抵抗力で 10 − 30 → 0（テスト専用の登録表。v0.18c のナツメのヤドンの「ぐうたらこうげき」でも同じ場合が起こる）。"""
        registry, pool = psychic_self_sleep_registry()
        state = board({"card": ABRA, "energy": [PSYCHIC]}, {"card": RATTATA}, effects=registry, pool=pool)
        self.assert_stops(state, ZERO)

    def test_z23_c_evaded_by_transparency(self):
        """Z23-c: 相手のゴースト（化石の秘密）の「とうめい」。先読みが「おもて」の結果を試すので、コインの結果によらず宣言の前に止まる。"""
        for side in (H, T):
            with self.subTest(coin=side):
                self.assert_stops(board(snorlax(), {"card": HAUNTER, "evolved_from": GASTLY}), EVADED, coin=side)

    def test_every_subcase_stops_in_every_preflight_mode(self):
        """先読みの方法（derived・derived_full・比べる方法 legacy）によらず、場合ごとに同じ理由で止まる。"""
        registry, pool = psychic_self_sleep_registry()
        cases = (
            (board(snorlax(), {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": TURN - 1}), PREVENTED),
            (board(snorlax(), {"card": MACHOP, "trainers": [(DEFENDER, TURN)]}), ZERO),
            (board({"card": ABRA, "energy": [PSYCHIC]}, {"card": RATTATA}, effects=registry, pool=pool), ZERO),
            (board(snorlax(), {"card": HAUNTER, "evolved_from": GASTLY}), EVADED),
        )
        for mode in PREFLIGHT_MODES:
            for state, why in cases:
                with self.subTest(mode=mode, why=why):
                    before = snapshot(state)
                    with self.assertRaises(UnsupportedError) as ctx:
                        apply_kernel(state, UseAttack(0, 0), preflight=mode)
                    self.assertEqual(ctx.exception.code, NO_DAMAGE)
                    self.assertIn(f"（{why}）", str(ctx.exception))
                    self.assertEqual(snapshot(state), before)


class TargetGoneIsUnreachableTest(unittest.TestCase):
    def test_after_damage_effects_follow_an_unconditional_first_damage_element(self):
        """Z23-d（対象がいない。p.309「処理の対象がなくなってしまっている場合、その内容は無視して」）は今のワザでは起こらない。

        製品の登録表で「ダメージを与えた後」の効果（``Status.after_damage``）を持つワザは、名前の指すダメージの要素が並びの最初の要素で、
        ワザのコイン（``gate``）・要素のコイン（``local_gate``）で飛ばされない。ダメージの要素の前に相手の対戦ポケモンを入れ替える要素がないので、
        対象がいない場合と、ダメージの要素を処理しなかった場合は起こらない。この形を壊すワザを加えたら、Z23-d を原典で確かめてから直す。"""
        seen = []
        for key in E.DEFAULT_EFFECTS.attack_keys():
            effect = E.DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).effect
            builder = programs.BUILDERS.get(type(effect))
            if builder is None:
                continue
            program = builder(effect)
            for element in program:
                if isinstance(element, programs.Status) and element.after_damage is not None:
                    seen.append(key)
                    first = program[0]
                    self.assertIsInstance(first, programs.Damage, key)
                    self.assertEqual((first.name, first.gate, first.local_gate, first.base.local_coins),
                                     (element.after_damage, None, None, 0), key)
                    self.assertEqual(first.target, programs.OPP, key)
        self.assertTrue(seen)  # たおれこむ（v0.17b）。v0.18c からぐうたらこうげきも


if __name__ == "__main__":
    unittest.main()
