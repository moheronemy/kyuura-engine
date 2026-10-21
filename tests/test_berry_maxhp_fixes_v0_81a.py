"""v0.81a: v0.81 の修正（docs/berry-maxhp-fixes-v0.81a.md）。

1. ポケモンチェックの 1（「指示されたこと」。GR-2000-P323-POKEMON-CHECK）のきのみ（きせきのみ）で回復したあとの場で、悪エネルギーの効果の対象・2 の「どく」の KA1・
   最大HPの低下（MH1）を判断する（v0.81 は回復の前の場で判断していた）。
2. 最大HPをその数にする効果（キョウのメタモンの「きょだいか」）と、大きくする効果（ロケット団のアジト・［ガスのからだ］）が同じポケモンにはたらく状態（v0.81 は
   ``effects.max_hp`` の ``RuntimeError`` に届いていた）を、新しい問い MH2 で状態を変える前に止める。
3. ログの監査の観測と照らす最大HP（``_effective_from_state``）に、ロケット団のアジトの + 20 を加える。

カードはどれも前の版で登録したもの（kyuura データの採用・過去の原典照合）。ガイドブックは読んでいない。
"""

from __future__ import annotations

import unittest

from kyuura_engine import (
    EndTurn,
    Phase,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
)
from kyuura_engine import effects as E
from kyuura_engine.coins import CoinSide
from kyuura_engine.observation import observe
from tests import helpers as H
from tests.helpers import apply_kernel, build_test_state, with_coin_results
from tests.log_audit import observation_problems
from tests.test_neo_trainer_components_v0_80 import audited, mon, new_events, snapshot

TURN = 7
W, FT = H.WATER, H.FIGHTING
DK = H.DARKNESS_ENERGY_NEO1
MIRACLE_BERRY = "neo1-081"
ROCKETS_HIDEOUT = "neo3-057"
BY1 = "UNRESOLVED_POKEMON_CHECK_BERRY_ORDER"
KA1 = "UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER"
MH1 = "UNRESOLVED_MAX_HP_DROP"
MH2 = "UNRESOLVED_MAX_HP_SET_AND_INCREASE"


def berry():
    return (MIRACLE_BERRY, None)


def check_board(mine, theirs, *, my_bench=(H.RATTATA,), their_bench=(H.RATTATA,)):
    """番のプレイヤー 0 が番を終えるとポケモンチェックになる盤面（両方にベンチ・山札・サイドがある）。"""
    return build_test_state([
        {"active": mine, "bench": list(my_bench), "deck": [W] * 10, "prizes": 6},
        {"active": theirs, "bench": list(their_bench), "deck": [W] * 10, "prizes": 6},
    ], turn_number=TURN)


def gas_muk(**extra):
    return {"card": H.MUK, "evolved_from": H.GRIMER, "evolved_turn": TURN - 2, "played_turn": TURN - 4, **extra}


def kabuto(**extra):
    return {"card": H.KABUTO, "evolved_from": H.MYSTERIOUS_FOSSIL, "evolved_turn": TURN - 1, "played_turn": TURN - 3, **extra}


def end(state):
    return apply_kernel(state, EndTurn(0))


def halted_before_change(test, state, after, code):
    """ダメージ・回復の前に止まった（ログは ``pokemon_check`` と ``halted`` のほかに、番の終わりのものだけ）。"""
    test.assertEqual((after.phase, after.halt.code), (Phase.HALTED, code))
    for owner in (0, 1):
        before = {p.pokemon_id: (p.damage, p.conditions, tuple(t.card for t in p.trainers)) for p in state.players[owner].in_play()}
        now = {p.pokemon_id: (p.damage, p.conditions, tuple(t.card for t in p.trainers)) for p in after.players[owner].in_play()}
        test.assertEqual(now, before)
    kinds = [e["kind"] for e in after.log[len(state.log):]]
    for kind in ("darkness_energy_damage", "tool_heal", "special_conditions_removed", "poison_damage", "knock_out"):
        test.assertNotIn(kind, kinds)


class DarknessTargetAfterCureTest(unittest.TestCase):
    """A: こんらん状態のメタモン（［へんしん］がはたらかない。無色）に悪エネルギーときせきのみ。相手の対戦ポケモンは悪タイプのデルビル（neo4-081）。悪エネルギーが先なら
    無色のメタモンが 10 を受け、きせきのみが先なら回復して［へんしん］がはたらき、悪タイプになって受けない。結果が変わるので BY1（v0.81 は回復の前の対象で 10 をのせていた）。"""

    def test_cure_changes_the_darkness_target_is_by1(self):
        state = check_board(mon(H.DITTO, (DK,), confusion=True, trainers=[berry()]), mon(H.HOUNDOUR_NEO4, (DK,)))
        before = snapshot(state)
        after = end(state)
        self.assertEqual(snapshot(state), before)
        halted_before_change(self, state, after, BY1)

    def test_without_berry_the_confused_ditto_takes_ten(self):
        state = check_board(mon(H.DITTO, (DK,), confusion=True), mon(H.HOUNDOUR_NEO4, (DK,)))
        after = end(state)
        ditto = after.find_pokemon(state.players[0].active.pokemon_id)[1]
        self.assertEqual(ditto.damage, 10)
        self.assertEqual([e["amount"] for e in new_events(state, after, "darkness_energy_damage")], [10])
        audited(self, after)

    def test_without_darkness_the_berry_cures_safely(self):
        state = check_board(mon(H.DITTO, (W,), confusion=True, trainers=[berry()]), mon(H.HOUNDOUR_NEO4, (DK,)))
        after = end(state)
        self.assertIs(after.phase, Phase.MAIN)
        ditto = after.find_pokemon(state.players[0].active.pokemon_id)[1]
        self.assertEqual((ditto.damage, ditto.conditions.names(), ditto.trainers), (0, (), []))
        audited(self, after)

    def test_cured_dark_ditto_with_darkness_and_no_change_proceeds(self):
        """回復しても色が変わらない（相手が無色のコラッタ）なら、どちらの順番でも 10 なので止めない（全部の場面を止めない）。"""
        state = check_board(mon(H.DITTO, (DK,), confusion=True, trainers=[berry()]), mon(H.RATTATA))
        after = end(state)
        self.assertIs(after.phase, Phase.MAIN)
        ditto = after.find_pokemon(state.players[0].active.pokemon_id)[1]
        self.assertEqual((ditto.damage, ditto.conditions.names()), (10, ()))
        audited(self, after)


class GasReturnsAfterCureTest(unittest.TestCase):
    """B: こんらん状態のベトベトン（かがくへんかガスが消えている）にきせきのみ。相手のカブト（［カブトアーマー］）がどく 10。1 でベトベトンが回復すると、2 の「どく」の
    ときにはかがくへんかガスがはたらき、カブトアーマーが消えているので、KA1 ではなく 10 をのせる（v0.81 は回復の前の場で KA1 にしていた）。"""

    def test_cured_gas_suppresses_kabuto_armor(self):
        state = check_board(gas_muk(confusion=True, trainers=[berry()]), kabuto(poison=10))
        after = end(state)
        self.assertIs(after.phase, Phase.MAIN)
        muk = after.find_pokemon(state.players[0].active.pokemon_id)[1]
        armor = after.find_pokemon(state.players[1].active.pokemon_id)[1]
        self.assertEqual((muk.conditions.names(), muk.trainers), ((), []))
        self.assertEqual(armor.damage, 10)
        self.assertEqual([e["amount"] for e in new_events(state, after, "poison_damage")], [10])
        audited(self, after)

    def test_without_berry_it_is_still_ka1(self):
        state = check_board(gas_muk(confusion=True), kabuto(poison=10))
        after = end(state)
        halted_before_change(self, state, after, KA1)

    def test_cure_on_another_pokemon_changes_the_darkness_result_is_by1(self):
        """ちがうポケモンの効果どうしでも結果が変わる（v0.81 の文書の「たがいの結果を変えない」は誤り）: カブトに悪エネルギー。悪エネルギーが先なら、ガスが消えている
        のでカブトアーマーが 10 に当てはまりうる（DE1）。ベトベトンのきせきのみが先なら、ガスがもどってカブトアーマーが消え、10 を受ける。結果が変わるので BY1。"""
        state = check_board(gas_muk(confusion=True, trainers=[berry()]), kabuto(energy=[DK]))
        after = end(state)
        halted_before_change(self, state, after, BY1)

    def test_without_berry_it_is_de1(self):
        state = check_board(gas_muk(confusion=True), kabuto(energy=[DK]))
        after = end(state)
        halted_before_change(self, state, after, "UNRESOLVED_DARKNESS_DAMAGE_RECEIVED_POWER")


class MaxHpDropAfterCureTest(unittest.TestCase):
    """C: こんらん状態のメタモン（最大HP 50）にダメージ 30 ときせきのみ。相手の対戦ポケモンはラッタ（HP 30）。回復すると［へんしん］で最大HP 30 になり、のっているダメージ
    以下になる（ダメージ以外の原因。MH1）。v0.81 はそのまま回復してきぜつ・サイドに進んでいた。状態を変える前に止める（ねむり・マヒの回復の確かめと同じ形）。"""

    def test_cure_drops_max_hp_is_mh1(self):
        state = check_board(mon(H.DITTO, (W,), damage=30, confusion=True, trainers=[berry()]), mon(H.RATTATA))
        after = end(state)
        halted_before_change(self, state, after, MH1)

    def test_damage_below_the_new_hp_proceeds(self):
        state = check_board(mon(H.DITTO, (W,), damage=20, confusion=True, trainers=[berry()]), mon(H.RATTATA))
        after = end(state)
        self.assertIs(after.phase, Phase.MAIN)
        ditto = after.find_pokemon(state.players[0].active.pokemon_id)[1]
        self.assertEqual((ditto.damage, ditto.conditions.names(), E.max_hp(after, ditto)), (20, (), 30))
        audited(self, after)


def arbok():
    return {"card": H.DARK_ARBOK, "evolved_from": H.ROCKET_EKANS, "evolved_turn": TURN - 1, "played_turn": TURN - 3}


def grow_board(*, their_bench, hand=(ROCKETS_HIDEOUT,)):
    """自分（プレイヤー 0）のバトル場は基本エネルギー 2 枚のメタモン（相手のキョウのメタモンに［へんしん］）。相手のベンチにわるいアーボック、手札にポケモンいれかえ。"""
    return build_test_state([
        {"active": mon(H.DITTO, (W, W)), "bench": [H.RATTATA], "hand": list(hand), "deck": [W] * 10, "prizes": 6},
        {"active": mon(H.KOGAS_DITTO, (W,)), "bench": list(their_bench), "hand": [H.SWITCH], "deck": [W] * 10, "prizes": 6},
    ], turn_number=TURN)


def grow(state, *, hideout=True):
    """（ロケット団のアジトを出してから）メタモンが今の姿の「きょだいか」を使い、「おもて」で最大HP 80。番が相手に移る。"""
    if hideout:
        uid = next(u for u in state.players[0].hand if state.cards[u].card_id == ROCKETS_HIDEOUT)
        state = apply_kernel(state, PlayTrainer(0, uid))
    after = apply_kernel(with_coin_results(state, CoinSide.HEADS), UseAttack(0, 0))
    assert after.phase is Phase.MAIN and after.current_player == 1, after.phase
    return after


def play_switch(state):
    uid = next(u for u in state.players[1].hand if state.cards[u].card_id == H.SWITCH)
    return apply_kernel(state, PlayTrainer(1, uid))


def answer_bench(state, pokemon_id):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, (pokemon_id,)))


class HideoutAndGrowTest(unittest.TestCase):
    """2: きょだいかで最大HP 80 のメタモンが、相手の入れ替えで「わるい」ポケモン（わるいアーボック）に［へんしん］すると、ロケット団のアジトの + 20 と、その数にする効果が
    同時にはたらく（80 か 100 かは記録から決まらない。MH2）。v0.81 はポケモンいれかえで ``RuntimeError`` になっていた。"""

    def test_switch_with_a_safe_target_is_usable_and_the_unsafe_answer_is_rejected(self):
        state = grow(grow_board(their_bench=(arbok(), H.RATTATA)))
        ditto = state.players[0].active
        self.assertEqual(E.max_hp(state, ditto), 80)
        waiting = play_switch(state)
        self.assertIsNotNone(waiting.decision)
        arbok_id, rattata_id = (p.pokemon_id for p in waiting.players[1].bench)
        before = snapshot(waiting)
        with self.assertRaises(UnsupportedError) as caught:
            answer_bench(waiting, arbok_id)
        self.assertEqual(caught.exception.code, MH2)
        self.assertEqual(snapshot(waiting), before)
        done = answer_bench(waiting, rattata_id)
        self.assertEqual(done.players[1].active.pokemon_id, rattata_id)
        self.assertEqual(E.max_hp(done, done.players[0].active), 80)
        audited(self, done)

    def test_switch_with_only_the_unsafe_target_is_rejected_before_any_change(self):
        state = grow(grow_board(their_bench=(arbok(),)))
        before = snapshot(state)
        with self.assertRaises(UnsupportedError) as caught:
            play_switch(state)
        self.assertEqual(caught.exception.code, MH2)
        self.assertEqual(snapshot(state), before)

    def test_without_hideout_the_switch_proceeds(self):
        state = grow(grow_board(their_bench=(arbok(),), hand=()), hideout=False)
        done = answer_bench(play_switch(state), state.players[1].bench[0].pokemon_id)
        self.assertEqual(E.form_def(done, done.players[0].active).id, H.DARK_ARBOK)
        self.assertEqual(E.max_hp(done, done.players[0].active), 80)
        audited(self, done)

    def test_without_fixed_hp_the_switch_proceeds_with_the_bonus(self):
        state = grow_board(their_bench=(arbok(),))
        uid = next(u for u in state.players[0].hand if state.cards[u].card_id == ROCKETS_HIDEOUT)
        state = apply_kernel(apply_kernel(state, PlayTrainer(0, uid)), EndTurn(0))
        done = answer_bench(play_switch(state), state.players[1].bench[0].pokemon_id)
        self.assertEqual(E.max_hp(done, done.players[0].active), 80)  # わるいアーボック 60 + 20
        self.assertEqual(observe(done, None)["players"][0]["active"]["hp"], 80)
        audited(self, done)

    def test_max_hp_query_never_raises_runtime_error(self):
        """その数にする効果と大きくする効果が同時にはたらく状態を直接作っても、問い合わせは ``RuntimeError`` ではなく、決まった問い（MH2）で止まる。"""
        state = grow(grow_board(their_bench=(arbok(),)))
        trial = state.clone()
        E._switch_active_with_bench(trial, 1, trial.players[1].bench[0].pokemon_id)
        with self.assertRaises(UnsupportedError) as caught:
            E.max_hp(trial, trial.players[0].active)
        self.assertEqual(caught.exception.code, MH2)
        self.assertIn(MH2, [code for code, _ in E.form_problems(trial)])


class HideoutAndGrowOtherPathsTest(unittest.TestCase):
    """2 の同じ状態になるほかの経路: 相手の「にげる」（決定のないコマンド）は受け付けない。ポケモンチェックのきぜつのあとにバトル場に出す決定は、受け付けられる答えが
    あれば止める答えだけを受け付けず、どの答えでもその状態になるなら、その前の状態で対戦を止める（答えのない決定を残さない）。"""

    def test_retreat_into_the_dark_pokemon_is_rejected(self):
        state = grow(grow_board(their_bench=(arbok(), H.RATTATA)))
        from kyuura_engine import Retreat
        koga = state.players[1].active
        command = Retreat(1, (koga.energy[0],), state.players[1].bench[0].card)
        before = snapshot(state)
        with self.assertRaises(UnsupportedError) as caught:
            apply_kernel(state, command)
        self.assertEqual(caught.exception.code, MH2)
        self.assertEqual(snapshot(state), before)

    def _knocked_board(self, their_bench):
        state = build_test_state([
            {"active": mon(H.DITTO, (W, W)), "bench": [H.RATTATA], "hand": [ROCKETS_HIDEOUT], "deck": [W] * 10, "prizes": 6},
            {"active": mon(H.KOGAS_DITTO, (W,), damage=30, poison=10), "bench": list(their_bench), "deck": [W] * 10, "prizes": 6},
        ], turn_number=TURN)
        uid = next(u for u in state.players[0].hand if state.cards[u].card_id == ROCKETS_HIDEOUT)
        state = apply_kernel(state, PlayTrainer(0, uid))
        return apply_kernel(with_coin_results(state, CoinSide.HEADS), UseAttack(0, 0))  # きょだいか → ポケモンチェックのどくでキョウのメタモンがきぜつ

    def _until_promotion(self, their_bench):
        after = self._knocked_board(their_bench)
        while after.phase is not Phase.PROMOTE_ACTIVE:
            d = after.decision
            self.assertIsNotNone(d, after.phase)
            after = apply_kernel(after, ResolveDecision(d.player, d.id, d.options[:d.min_choices or 1]))
        return after

    def test_promotion_with_only_the_dark_pokemon_halts_before_it(self):
        from kyuura_engine import PromoteActive
        after = self._until_promotion((arbok(),))
        halted = apply_kernel(after, PromoteActive(1, after.players[1].bench[0].card))
        self.assertEqual((halted.phase, halted.halt.code), (Phase.HALTED, MH2))
        self.assertIsNone(halted.players[1].active)  # その前の状態で止めた
        audited(self, halted)

    def test_promotion_with_a_safe_choice_rejects_only_the_dark_pokemon(self):
        from kyuura_engine import PromoteActive
        after = self._until_promotion((arbok(), H.RATTATA))
        dark, plain = after.players[1].bench
        before = snapshot(after)
        with self.assertRaises(UnsupportedError) as caught:
            apply_kernel(after, PromoteActive(1, dark.card))
        self.assertEqual(caught.exception.code, MH2)
        self.assertEqual(snapshot(after), before)
        done = apply_kernel(after, PromoteActive(1, plain.card))
        self.assertEqual(done.players[1].active.pokemon_id, plain.pokemon_id)
        audited(self, done)


class LogAuditHideoutTest(unittest.TestCase):
    """3: 観測の最大HPと照らす監査の値に、ロケット団のアジトの + 20 を含める（ある・ないの両方）。"""

    def test_observation_audit_counts_the_hideout(self):
        base = grow_board(their_bench=(arbok(),))
        uid = next(u for u in base.players[0].hand if base.cards[u].card_id == ROCKETS_HIDEOUT)
        with_hideout = apply_kernel(base, PlayTrainer(0, uid))
        bench_arbok = with_hideout.players[1].bench[0]
        self.assertEqual(observe(with_hideout, None)["players"][1]["bench"][0]["hp"], 80)
        self.assertEqual(E.max_hp(with_hideout, bench_arbok), 80)
        self.assertEqual(observation_problems(with_hideout), [])
        self.assertEqual(observe(base, None)["players"][1]["bench"][0]["hp"], 60)
        self.assertEqual(observation_problems(base), [])


if __name__ == "__main__":
    unittest.main()
