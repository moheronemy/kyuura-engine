"""v0.144: ポケモンチェックのどくのきぜつで、かがくへんかガスの発生源が場をはなれ、残りHP「10」で消えていた［ずらかる］の力がもどる（SC2）盤面の、状態の整合の不具合の修正
（docs/sc2-integrity-fix-v0.144.md）。

v0.143 までは、SC2 の問いをきぜつの判定の窓（どくのダメージのあと）で確かめ、HP 以上のポケモンが場に残ったまま止めたので、状態の確かめ（``StateIntegrityError``）がコマンドを
受け付けなかった（厳密側・S2a の続行側の両方）。v0.144 では、同じ判定（``effects.scram_restored_by_leaving``）をポケモンチェックの 1・2 の確かめ（``procedures._pokemon_check_plan``）で
状態の複製の上で行い、ダメージを与える前に、今と同じ SC2 のコード（``UNRESOLVED_SCRAM_POWER_RESTORED``）で止める。SC2 の答え（はたらくか）は決めない（新しい裁定ではない。安全に止めるための
修正）。

盤面はすべて直接作った盤面（constructed）。new_game からの合法な操作列での再現は、文書 3 章の探索の結果を見る。
"""

from __future__ import annotations

import pickle
import unittest
from unittest import mock

from kyuura_engine import EndTurn, apply_command, check_invariants
from kyuura_engine import effects as E
from kyuura_engine import procedures as PR
from kyuura_engine.coins import CoinSide
from kyuura_engine.errors import StateIntegrityError, UnsupportedError
from kyuura_engine.state import Phase
from tests import helpers as H
from tests import test_marker_check_field_reset_v0_91 as V91
from tests.helpers import with_coin_results
from tests.log_audit import observation_problems, s2a_problems, serialization_problems
from tests.test_play_policy_s2a_v0_143 import applied, as_play, snapshot
from tests.test_type_energy_colors_v0_88 import muk

SC2 = E.SCRAM_RESTORED_CODE
DOUBLE_KO = V91.DOUBLE_KO
HD, TL = CoinSide.HEADS, CoinSide.TAILS


def gas(mine=False, **extra):
    """かがくへんかガスのベトベトン（HP 70）。``mine`` なら番を終えるプレイヤー（0）の場（その番の手前の自分の番に進化した盤面）。"""
    pokemon = muk() if not mine else V91.mon(H.MUK, played_turn=3, evolved_from=H.GRIMER, evolved_turn=5)
    pokemon.update(extra)
    return pokemon


def primeape(damage=60, **extra):
    """相手の場のタケシのオコリザル（HP 70・［ずらかる］）。ダメージ 60 なら残りHP「10」（かがくへんかガスで力が消えている）。"""
    return V91.mon(H.BROCKS_PRIMEAPE, played_turn=2, evolved_from=H.BROCKS_MANKEY, evolved_turn=4, damage=damage, **extra)


def reported(**gas_extra):
    """報告された盤面: 番を終えるプレイヤー 0、相手のバトル場にどくのダメージできぜつするかがくへんかガスのベトベトン、相手のベンチに残りHP「10」のタケシのオコリザル。"""
    return V91.board(V91.mon(H.CHANSEY), opponent=gas(damage=60, poison=10, **gas_extra), opponent_bench=(primeape(),))


def both_sets(base):
    return (("strict", base), ("play", as_play(base)))


def damage_of(state):
    return [(p.pokemon_id, p.damage) for player in state.players for p in player.in_play()]


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])
    test.assertEqual(s2a_problems(state), [])


class ReportedBoardTest(unittest.TestCase):
    def test_halts_before_damage_with_the_same_code(self):
        base = reported()
        for name, state in both_sets(base):
            with self.subTest(name):
                done = V91.end_turn(state)
                self.assertEqual((done.phase, done.halt.code), (Phase.HALTED, SC2))
                self.assertIn("ダメージを与える前に止める", done.halt.message)
                self.assertEqual([e["kind"] for e in done.log[len(base.log):]], ["end_turn_without_attack", "turn_end", "pokemon_check", "halted"])
                self.assertEqual(damage_of(done), damage_of(base))  # どくのダメージは与えていない
                self.assertEqual(done.rng.getstate(), base.rng.getstate())  # 乱数を使っていない
                self.assertEqual(applied(done, len(base.log)), [])  # 規約は当てていない（SC2 は続行規約がない）
                audited(self, done)

    def test_strict_and_play_halt_the_same(self):
        base = reported()
        strict, play = (V91.end_turn(state) for _, state in both_sets(base))
        self.assertEqual([dict(e) for e in play.log], [dict(e) for e in strict.log])
        self.assertEqual(play.rng.getstate(), strict.rng.getstate())

    def test_given_state_is_unchanged(self):
        base = reported()
        before = snapshot(base)
        V91.end_turn(base)
        self.assertEqual(snapshot(base), before)

    def test_without_the_precheck_the_old_error_remains(self):
        """先読みと実行の整合: ダメージの前の確かめを外すと、きぜつの判定の窓の問い（同じ判定 ``scram_restored_by_leaving``）がダメージのあとに止め、v0.143 までと同じ
        ``StateIntegrityError`` になる（修正前の失敗の形。修正はこの経路の止める位置だけを前にする）。"""
        with mock.patch.object(PR, "_knockout_scram_restored_stop", return_value=None):
            for name, state in both_sets(reported()):
                with self.subTest(name), self.assertRaises(StateIntegrityError):
                    V91.end_turn(state)

    def test_precheck_and_window_use_the_same_judgement(self):
        base = reported()
        calls = []
        real = E.scram_restored_by_leaving

        def spy(state, gone):
            found = real(state, gone)
            calls.append((frozenset(gone), found))
            return found

        with mock.patch.object(E, "scram_restored_by_leaving", spy):
            V91.end_turn(base)
        muk_id, ape_id = base.players[1].active.pokemon_id, base.players[1].bench[0].pokemon_id
        self.assertEqual(calls, [(frozenset({muk_id}), (ape_id, [muk_id]))])

    def test_save_and_restore(self):
        base = reported()
        restored = pickle.loads(pickle.dumps(base))
        self.assertEqual(snapshot(V91.end_turn(restored)), snapshot(V91.end_turn(base)))
        halted = pickle.loads(pickle.dumps(V91.end_turn(base)))
        self.assertEqual((halted.phase, halted.halt.code), (Phase.HALTED, SC2))
        audited(self, halted)


class BoundaryTest(unittest.TestCase):
    def assert_runs(self, base, phase):
        for name, state in both_sets(base):
            with self.subTest(name):
                done = V91.end_turn(state)
                self.assertIs(done.phase, phase)
                self.assertNotIn("halted", [e["kind"] for e in done.log[len(base.log):]])
                audited(self, done)

    def test_gas_source_survives(self):
        """ガスの発生源がきぜつしない（どくのダメージのあと残りHP 10 のまま）: 止めない。［ずらかる］の力は消えたまま。"""
        base = V91.board(V91.mon(H.CHANSEY), opponent=gas(damage=50, poison=10), opponent_bench=(primeape(),))
        self.assert_runs(base, Phase.MAIN)

    def test_scram_not_at_ten(self):
        """［ずらかる］のポケモンの残りHPが「10」でない: ガスの発生源がきぜつしても止めない（サイドを取る）。"""
        self.assert_runs(V91.board(V91.mon(H.CHANSEY), opponent=gas(damage=60, poison=10), opponent_bench=(primeape(damage=50),)), Phase.TAKE_PRIZE)

    def test_scram_still_unable(self):
        """［ずらかる］のポケモン（相手のバトル場）がこんらん（力がはたらかない）: ガスの発生源（番を終えたプレイヤーのバトル場）がきぜつしても力はもどらないので止めない。
        こんらんでなければ同じ盤面で止める（発生源と［ずらかる］が別のプレイヤーの場でも同じ判定）。"""
        self.assert_runs(V91.board(gas(mine=True, damage=60, poison=10), opponent=primeape(confusion=True)), Phase.TAKE_PRIZE)
        for name, state in both_sets(V91.board(gas(mine=True, damage=60, poison=10), opponent=primeape())):
            with self.subTest(name):
                self.assertEqual(V91.end_turn(state).halt.code, SC2)

    def test_another_gas_source_remains(self):
        """かがくへんかガスの発生源が 2 匹で、1 匹だけきぜつする: 力は消えたままなので止めない。"""
        self.assert_runs(V91.board(V91.mon(H.CHANSEY), opponent=gas(damage=60, poison=10), opponent_bench=(primeape(), gas())), Phase.TAKE_PRIZE)

    def test_knocked_out_pokemon_is_not_the_source(self):
        """きぜつするのはガスの発生源でない（番を終えたプレイヤーのポケモン）: 止めない。"""
        base = V91.board(V91.mon(H.RATTATA, damage=20, poison=10), opponent=gas(), opponent_bench=(primeape(),))
        self.assert_runs(base, Phase.TAKE_PRIZE)

    def test_both_sides_knock_out_keeps_the_double_knockout_stop(self):
        """両方のプレイヤーのポケモンがきぜつする: 今までどおり両方のきぜつの停止（先に確かめる）。"""
        base = V91.board(V91.mon(H.RATTATA, damage=20, poison=10), opponent=gas(damage=60, poison=10), opponent_bench=(primeape(),))
        for name, state in both_sets(base):
            with self.subTest(name):
                done = V91.end_turn(state)
                self.assertEqual(done.halt.code, DOUBLE_KO)
                self.assertEqual(damage_of(done), damage_of(base))

    def test_char_coin_that_could_knock_out_the_source_halts_before_coins(self):
        """くろこげマーカーの「うら」とどくでガスの発生源が 2 のあとにきぜつする結果があれば、コインの前のすべての結果の確かめが SC2 を見つけ、コインを投げる前に止める（v0.143 までは「うら」なら
        ダメージのあとに StateIntegrityError、「おもて」なら続いた）。"""
        base = V91.board(V91.mon(H.CHANSEY), opponent=gas(damage=40, poison=10, markers=[V91.MARKER_CHAR]), opponent_bench=(primeape(),))
        for coin in (HD, TL):
            for name, state in both_sets(base):
                with self.subTest(name, coin=coin):
                    done = V91.end_turn(with_coin_results(state, coin))
                    self.assertEqual((done.phase, done.halt.code), (Phase.HALTED, SC2))
                    self.assertEqual([e for e in done.log[len(base.log):] if e["kind"] in ("coin_flip", "char_check", "char_damage")], [])
                    self.assertEqual(damage_of(done), damage_of(base))
                    audited(self, done)


class UnchangedPathsTest(unittest.TestCase):
    def test_ko_point_conservative_stop_keeps_its_message(self):
        """S2a の保守的な制限（PC-CHECK-KO-POINT のきぜつで SC2 になるなら規約を当てずに止める）は、今の止め方・文のまま（v0.143 の試験と同じ盤面）。"""
        g = muk()
        g.update(damage=60, markers=[V91.MARKER_CHAR])
        ape = primeape(damage=50, poison=10)
        base = V91.board(V91.mon(H.CHANSEY), opponent=ape, opponent_bench=(g,))
        self.assertEqual(V91.end_turn(base).halt.code, "UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT")
        play = V91.end_turn(as_play(base))
        self.assertEqual(play.halt.code, SC2)
        self.assertIn("PC-CHECK-KO-POINT", play.halt.message)

    def test_commands_after_the_halt_are_refused_with_the_stop_code(self):
        """修正の経路はコマンドの拒否ではなく、整合した途中停止（HALTED）。停止のあとのコマンドは、今までの停止と同じく停止のコードで受け付けない（状態は変えない）。"""
        done = V91.end_turn(reported())
        before = snapshot(done)
        with self.assertRaises(UnsupportedError) as caught:
            apply_command(done, EndTurn(1))
        self.assertEqual(caught.exception.code, SC2)
        self.assertEqual(snapshot(done), before)


if __name__ == "__main__":
    unittest.main()
