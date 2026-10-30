"""v0.121（docs/hand-bench-attack-conditions-v0.121.md）: 手札からの登場とワザの使用条件。

2 章（A0）: 「なきごえ」を受けたエレキッド（neo1-044）が、次の自分の番に［わんぱくパンチ］で、効果を与えたポケモンに特殊能力のダメージを与える盤面。v0.120 までは、この場面を
今の対応カードでは起こらないとして内部エラー（``RuntimeError``）にしていた（v0.114 のエレキッドで起こる）。説明はワザのダメージに限らないが、ワザ以外のダメージを減らすかは記録で
決まらないので止める（GN1）。

盤面は ``build_test_state`` と通常の操作で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない。
"""

from __future__ import annotations

import unittest

from kyuura_engine import effects as E
from kyuura_engine.coins import CoinSide
from kyuura_engine.errors import UnsupportedError
from tests import helpers as H
from tests.test_fossil_basic_virtual_attacks_v0_120 import power_use, spec, table, use
from tests.test_neo_trainer_components_v0_80 import new_events
from tests.test_unown_family_powers_v0_96 import snap

HD, TL = CoinSide.HEADS, CoinSide.TAILS
L, F, W, G = H.LIGHTNING, H.FIRE, H.WATER, H.GRASS
GN1 = E.GROWL_NON_ATTACK_DAMAGE_CODE
ELEKID = "neo1-044"  # エレキッド（［わんぱくパンチ］: コインの「おもて」で相手の対戦ポケモンに 20。使ったら番は終わる）
PIKACHU_IP = "IP1-040"  # ピカチュウ（なきごえ。印刷の文面も新しい書き方）
CHARMANDER = "ES1-013"  # ヒトカゲ（なきごえ）
CHIKORITA = "PF1-001"  # チコリータ（なきごえ）
TOGEPI = "PR1-065"  # トゲピー（なきつく。「-20」で、なきごえと同じ型）
GROWLERS = (PIKACHU_IP, CHARMANDER, CHIKORITA, TOGEPI)


def growled(grower, *, elekid_active=True):
    """``grower`` がバトル場で 1 つ目のワザ（なきごえ・なきつく）を使い、番が終わった盤面（相手の番）。``elekid_active`` でなければ、効果を受けるのはラッキーで、エレキッドはベンチ。"""
    opponent = spec(ELEKID) if elekid_active else spec(H.CHANSEY)
    state = table(spec(grower, (L, L, F, W, G)), opponent=opponent, opponent_bench=() if elekid_active else (spec(ELEKID),))
    after = use(state, 0)
    assert (after.current_player, after.decision) == (1, None), "なきごえのあとは相手の番"
    return after


def elekid(state):
    side = state.players[1]
    return next(p for p in (side.active, *side.bench) if state.cards[p.card].card_id == ELEKID)


class GrowlPowerDamageTest(unittest.TestCase):
    """A0（docs 2 章）: なきごえを受けたポケモンが、はたらく番に、効果を与えたポケモンへ特殊能力のダメージを与える。"""

    def test_bratty_punch_on_the_growl_source_stops_before_the_coin(self):
        """v0.120 では［わんぱくパンチ］の宣言の確かめ（「おもて」のときのダメージ）が RuntimeError にした盤面。今は宣言の前に GN1 で止め、状態・乱数・ログを変えない。
        なきごえの 3 つの書き方と、同じ型の「なきつく」（トゲピー）で同じ。"""
        for grower in GROWLERS:
            with self.subTest(grower=grower):
                state = growled(grower)
                before = snap(state)
                with self.assertRaises(UnsupportedError) as raised:
                    power_use(state, elekid(state).pokemon_id, HD)
                self.assertIs(type(raised.exception), UnsupportedError)
                self.assertEqual(raised.exception.code, GN1)
                self.assertIn("GN1", str(raised.exception))
                self.assertEqual(snap(state), before)
                key = E.PowerKey(ELEKID, 0)
                problem = E.DEFAULT_EFFECTS.power_entry(ELEKID, 0).effect.damage_problem(state, E.PowerUse(1, elekid(state).pokemon_id, key))
                self.assertEqual(problem.code, GN1)  # 「おもて」のときのダメージの問い（コインの前。状態を変えない）

    def test_neighbours(self):
        """隣の例: 効果を受けていないベンチのエレキッドの［わんぱくパンチ］は 20 のまま（ラッキーが受けた）。効果を受けたエレキッドでも、はたらく番（なきごえの次の相手の番）が
        過ぎたあとの自分の番なら 20。「うら」なら何もしない（宣言の確かめは「おもて」のダメージで決めるので、どちらの面でも同じ答え）。"""
        from kyuura_engine import EndTurn

        bench = growled(PIKACHU_IP, elekid_active=False)
        state = growled(PIKACHU_IP)
        later = H.apply_kernel(H.apply_kernel(state, EndTurn(1)), EndTurn(0))
        self.assertEqual((later.current_player, later.turn_number), (1, state.turn_number + 2))
        for label, state in (("bench", bench), ("expired", later)):
            with self.subTest(label):
                target = state.players[0].active
                done = power_use(state, elekid(state).pokemon_id, HD)
                self.assertEqual(done.players[0].active.damage - target.damage, 20)
                self.assertEqual([e["amount"] for e in new_events(state, done, "power_damage")], [20])
                missed = power_use(state, elekid(state).pokemon_id, TL)
                self.assertEqual(missed.players[0].active.damage, target.damage)

    def test_attack_damage_rules_are_unchanged(self):
        """ワザのダメージは今までどおり: 受けた相手のワザがこのカードに与えるダメージは p.321 の 2 段階で引き（v0.76）、控えのこのカードへのワザのダメージは NK5（別の問い）。
        GN1 は特殊能力のダメージだけの問い。"""
        self.assertNotEqual(GN1, "UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET")
        self.assertEqual(GN1, "UNRESOLVED_GROWL_NON_ATTACK_DAMAGE")
        self.assertIn("GN1", E.GROWL_NON_ATTACK_DAMAGE_REASON)


if __name__ == "__main__":
    unittest.main()
