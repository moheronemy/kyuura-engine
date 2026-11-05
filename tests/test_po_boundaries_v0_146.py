"""v0.146（docs/play-set-verification-v0.146.md 4 章）: PO の集合（CS-KYUURA-PLAY-PO@1）の、v0.145 で確かめていなかった境界・組み合わせ。新しい規約は加えない。

どれもテスト専用の盤面（``build_test_state``。constructed）で、合法な操作の列で着けることは確かめていない（到達可能性は未確認）。同じ盤面・同じ乱数で、規約集合だけを
置きかえて厳密側・S2a・PO を比べる。ログの独立した監査（``log_problems`` の v0.145 のどくの量の検査）は ``new_game`` からのログを前提にするので、ここでは使わず（盤面を直接作った
ログでは使えない。技術的な制限）、記録の形と置き場所の検査（``s2a_problems``）・状態の確かめ・期待値で確かめる。合法な対戦での独立した監査は、道具の対戦（一括の計測）でする。

主張と確かめの対応（docs 4.1 節の表と同じ）:

- B1 特殊などく 30（neo2-010 さんばいどく）と［ポイズンミスト］: 性質 → ［ポイズンミスト］→ 鋼エネルギー（20、鋼エネルギーがあれば 10）。厳密側・S2a は PO1
- B2 複数の発生源: 2 匹とも場をはなれた（10・``ended_mists`` に 2 匹）／1 匹が場をはなれ 1 匹がはたらき、使う前からのどく（20・当てはまる相手の規約だけ。発生源の規約は結果を
  変えないので記録しない）／1 匹が場をはなれ 1 匹がはたらき、鋼エネルギー（量が 1 つに決まる。どの集合も同じ 10・記録なし）
- B3 へんしん: メタモンが写した［ポイズンミスト］は、使う宣言で ``UNSUPPORTED_TRANSFORM_COPIED_POWER``（記録ができる前に止まる。へんしんの #power-lost の盤面には着かない。エンジンの未対応）
- B4 続けたあとに既存の停止: 両方のバトル場のポケモンがどくできぜつする盤面は、PO の集合では PO2 を越えて ``UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`` で、ダメージの前に整合した状態で
  止まる（規約の記録は残らない。先読みだけで使った）。S2a の続行規約ではない場面（研究上の未決）
- B5 規約を当てたあとの決定（サイドを取る）で保存・復元を挟んでも同じ
- B6 延長戦: ［ポイズンミスト］の記録は新しい区間で消え（``SEGMENT_FIELD_POLICY`` の reset）、集合は引き継ぐ
"""

from __future__ import annotations

import pickle
import unittest

from kyuura_engine import (
    StartSuddenDeath,
    TakePrize,
    UsePokemonPower,
    apply_command,
    check_invariants,
    sudden_death,
)
from kyuura_engine import conventions as C
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from tests import helpers as H
from tests import test_sudden_death_v0_134 as SD
from tests import test_virtual_attacks_transformation_v0_49 as V49
from tests.helpers import with_coin_results
from tests.log_audit import command_outcome, s2a_problems
from tests.test_damage_reactions_poison_sleep_v0_119 import (
    HD,
    WEEZING,
    F,
    G,
    attack,
    board,
    end_turn,
    mist,
    mon,
    weezing_board,
)
from tests.test_poison_mist_play_po_v0_145 import (
    ORDER,
    PO,
    PO1,
    PO2,
    PO3,
    SOURCE_LEFT,
    TARGETS,
    applied,
    each_set,
    play_trainer,
    snapshot,
    use_mist,
    with_set,
)

BEEDRILL_NEO2 = "neo2-010"  # スピアー（ネオ2）。さんばいどく（草）10。おもてなら、このワザのどくのダメージは 30
DOUBLE_KO = "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT"
LATEST = max(FORMAT_VERSIONS)


def poison_damages(state, since):
    return [(e["pokemon_id"], e["amount"], e.get("amount_before"), e.get("poison_mists")) for e in state.log[since:] if e["kind"] == "poison_damage"]


def records(state, since):
    return [(e["convention"], e.get("amount"), e.get("ended_mists"), e.get("poison_mists")) for e in applied(state, since)]


def checked(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(s2a_problems(state), [])


def two_weezings(hand, opponent):
    state = board(mon(H.WEEDLE, (G,)), bench=(mon(WEEZING), mon(WEEZING), mon(H.GRIMER)), opponent=opponent, hand=hand)
    first, second = (p.pokemon_id for p in state.players[0].bench[:2])
    return use_mist(use_mist(state, first), second), first, second


class SpecialPoison30Test(unittest.TestCase):
    """B1: 特殊などく 30 と［ポイズンミスト］・鋼エネルギー（v0.145 はコードを読んだだけで、盤面を作っていなかった）。"""

    def beedrill(self, opponent):
        return mist(weezing_board(mon(BEEDRILL_NEO2, (G, G, G), evolved_from=("PMCG1-004", "PMCG1-009")), opponent=opponent))

    def test_order_gives_20_and_10_with_metal(self):
        for name, opponent, amount, before in (("mist", mon(H.HITMONCHAN), 20, None), ("mist+metal", mon(H.HITMONCHAN, (H.METAL_ENERGY_NIP1X,)), 10, 20)):
            base = self.beedrill(opponent)
            results = {label: attack(state, 0, HD) for label, state in each_set(base).items()}
            with self.subTest(name=name):
                for label in ("strict", "s2a"):
                    self.assertEqual((results[label].phase.value, results[label].halt.code), ("halted", PO1))
                    self.assertEqual(poison_damages(results[label], len(base.log)), [])
                done = results["po"]
                target = done.players[1].active.pokemon_id
                self.assertEqual(poison_damages(done, len(base.log)), [(target, amount, before, (base.poison_mists[0].pokemon_id,))])
                self.assertEqual(records(done, len(base.log)), [(ORDER, amount, None, (base.poison_mists[0].pokemon_id,))])
                checked(self, done)


class MultipleSourcesBoundaryTest(unittest.TestCase):
    """B2: 発生源が 2 匹のときの組（v0.145 は 1 匹が場をはなれ 1 匹がはたらく・場をはなれた 1 匹と力の消えた 1 匹）。"""

    def test_both_sources_left(self):
        misted, first, second = two_weezings((H.MR_FUJI, H.MR_FUJI), mon(H.HITMONCHAN))
        both = play_trainer(play_trainer(misted, H.MR_FUJI, (first,)), H.MR_FUJI, (second,))
        self.assertEqual([(r.pokemon_id, r.interrupted) for r in both.poison_mists], [(first, True), (second, True)])
        self.assertTrue(all(both.find_pokemon(r.pokemon_id) is None for r in both.poison_mists))
        results = {label: attack(state, 0, HD) for label, state in each_set(both).items()}
        for label in ("strict", "s2a"):
            self.assertEqual(results[label].halt.code, PO3)
        done = results["po"]
        self.assertEqual([(a, b) for _, a, b, _ in poison_damages(done, len(both.log))], [(10, None)])
        self.assertEqual(records(done, len(both.log)), [(SOURCE_LEFT, 10, (first, second), None)])
        checked(self, done)

    def test_left_working_and_earlier_poison_records_only_the_deciding_rule(self):
        """1 匹が場をはなれ、1 匹がはたらき、相手は使う前からどく: 厳密側・S2a は PO2 で止まる。PO は 20 で、記録は当てはまる相手の規約だけ（場をはなれた記録を当てはめても
        当てはめなくても、はたらく記録で 20。発生源の規約は結果を変えない）。"""
        misted, first, second = two_weezings((H.MR_FUJI,), mon(H.HITMONCHAN, poison=10))
        left = play_trainer(misted, H.MR_FUJI, (first,))
        results = {label: end_turn(state) for label, state in each_set(left).items()}
        for label in ("strict", "s2a"):
            self.assertEqual(results[label].halt.code, PO2)
        done = results["po"]
        self.assertEqual([(a, b, m) for _, a, b, m in poison_damages(done, len(left.log))], [(20, None, (second,))])
        self.assertEqual(records(done, len(left.log)), [(TARGETS, 20, None, (second,))])
        checked(self, done)

    def test_left_working_and_metal_is_already_decided(self):
        """1 匹が場をはなれ、1 匹がはたらき、相手に鋼エネルギー（新しいどく）: 場をはなれた記録の扱いによらず 20 − 10 = 10 なので、どの集合も止めず、同じログで、規約の記録はない。"""
        misted, first, second = two_weezings((H.MR_FUJI,), mon(H.HITMONCHAN, (H.METAL_ENERGY_NIP1X,)))
        left = play_trainer(misted, H.MR_FUJI, (first,))
        results = {label: attack(state, 0, HD) for label, state in each_set(left).items()}
        logs = {label: [dict(e) for e in done.log] for label, done in results.items()}
        self.assertEqual(logs["strict"], logs["po"])
        self.assertEqual(logs["s2a"], logs["po"])
        self.assertEqual([(a, b, m) for _, a, b, m in poison_damages(results["po"], len(left.log))], [(10, 20, (second,))])
        self.assertEqual(applied(results["po"], len(left.log)), [])


class TransformTest(unittest.TestCase):
    def test_copied_poison_mist_is_unsupported_before_any_record(self):
        """B3: メタモン（［へんしん］）が相手のマタドガスを写した姿で［ポイズンミスト］を使う宣言は、どの集合でも UNSUPPORTED_TRANSFORM_COPIED_POWER（状態・乱数・ログは変わらない）。
        記録ができないので、へんしんで発生源の力が消える #power-lost の盤面には、今のエンジンでは着かない（エンジンの未対応。研究の答えではない）。"""
        state = V49.ditto_board(mon(WEEZING))
        ditto = state.players[0].active
        for label, st in each_set(state).items():
            with self.subTest(set=label):
                ready = with_coin_results(st, HD)
                before = snapshot(ready)
                outcome = command_outcome(ready, UsePokemonPower(0, ditto.pokemon_id, 0))[0]
                self.assertEqual(outcome[:2], ("UnsupportedError", "UNSUPPORTED_TRANSFORM_COPIED_POWER"))
                self.assertEqual(snapshot(ready), before)
                self.assertEqual(ready.poison_mists, ())


class OtherStopAfterContinuationTest(unittest.TestCase):
    def test_double_knockout_stops_consistently_without_records(self):
        """B4: 両方のバトル場のポケモンが使う前からどく（10）で、［ポイズンミスト］の 20 で両方きぜつする盤面。厳密側・S2a は PO2、PO は PO2 を越えて、ポケモンチェックの両方のきぜつ
        （研究上の未決。S2a・PO の続行規約の対象ではない）でダメージの前に止まる。止まったので、規約の記録・どくのダメージは残らない（確かめの先読みでだけ規約を使った）。"""
        base = mist(board(mon(H.HITMONCHAN, (F,), poison=10, damage=60), bench=(mon(WEEZING),), opponent=mon(H.HITMONCHAN, poison=10, damage=60)))
        results = {label: end_turn(state) for label, state in each_set(base).items()}
        for label in ("strict", "s2a"):
            self.assertEqual(results[label].halt.code, PO2)
        done = results["po"]
        self.assertEqual((done.phase.value, done.halt.code), ("halted", DOUBLE_KO))
        self.assertEqual(applied(done, len(base.log)), [])
        self.assertEqual(poison_damages(done, len(base.log)), [])
        self.assertEqual([p.damage for p in (done.players[0].active, done.players[1].active)], [60, 60])  # ダメージの前
        checked(self, done)


class SaveRestoreAfterApplicationTest(unittest.TestCase):
    def test_pending_prize_after_the_rule_survives_save_and_restore(self):
        """B5: 当てはまる相手の規約で 20 になり相手がきぜつ → サイドを取る決定。その決定で保存・復元（pickle・複製）しても、続きの処理・ログ・乱数は同じ。規約の記録は 1 回だけ。"""
        base = mist(board(mon(H.HITMONCHAN, (F,)), bench=(mon(WEEZING),), opponent=mon(H.HITMONCHAN, poison=10, damage=60), opponent_bench=(mon(H.RATTATA),)))
        pending = end_turn(with_set(base, PO))
        self.assertEqual((pending.decision.kind, pending.decision.player), ("take_prize", 0))
        self.assertEqual([c for c, _, _, _ in records(pending, len(base.log))], [TARGETS])
        expected = apply_command(pending, TakePrize(0, 0))
        for copied in (pickle.loads(pickle.dumps(pending)), pending.clone()):
            self.assertEqual(copied.conventions, C.registered_identity(PO))
            after = apply_command(copied, TakePrize(0, 0))
            self.assertEqual(state_to_dict(after, format_version=LATEST), state_to_dict(expected, format_version=LATEST))
            self.assertEqual([dict(e) for e in after.log], [dict(e) for e in expected.log])
            self.assertEqual(after.rng.getstate(), expected.rng.getstate())
            self.assertEqual(len(records(after, len(base.log))), 1)
        checked(self, expected)


class SuddenDeathResetTest(unittest.TestCase):
    def test_mist_records_reset_and_the_set_is_kept(self):
        """B6: 新しい区間では［ポイズンミスト］の記録が消え（区間の項目の扱い reset。reset の項目が既定の値になることは v0.134 の
        ``test_every_field_is_reset_kept_or_rebuilt`` が自然な対戦で確かめる）、規約集合は同じ（keep）。PO の集合の延長戦の区間でも続行規約がはたらく状態のまま。
        ［ポイズンミスト］の記録のある盤面を直接作ってサドン・デスにすることはできなかった（構築の盤面の進化のログの不変条件。docs 4.2 節）。"""
        self.assertEqual(sudden_death.SEGMENT_FIELD_POLICY["poison_mists"], "reset")
        self.assertEqual(sudden_death.SEGMENT_FIELD_POLICY["conventions"], "keep")
        state = H.build_test_state([{"active": SD.PIKA, "deck": [SD.PIKA] + [SD.FIRE] * 30, "prizes": 0},
                                    {"active": SD.PIKA, "deck": [SD.PIKA] + [SD.FIRE] * 30, "prizes": 0}])
        started = apply_command(with_set(SD.constructed_sudden_death(SD.with_decklists(state)), PO), StartSuddenDeath())
        self.assertEqual((started.poison_mists, started.conventions), ((), C.registered_identity(PO)))
        self.assertEqual(C.continuation_lookup(started.conventions, PO2).convention, (TARGETS, 1))
        self.assertEqual(check_invariants(started), [])


if __name__ == "__main__":
    unittest.main()
