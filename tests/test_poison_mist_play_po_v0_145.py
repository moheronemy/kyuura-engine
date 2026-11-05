"""v0.145（docs/poison-mist-play-po-v0.145.md）: ［ポイズンミスト］とどくの量の続行規約 3 件（PC-POISON-AMOUNT-ORDER@1・PC-POISON-MIST-TARGETS@1・PC-POISON-MIST-SOURCE-LEFT@1）と、
開発用の部分的な集合 CS-KYUURA-PLAY-PO@1。

- 新しい規約の確かめ（PO の集合だけが対象の場面で続く・量・記録）と、変えていない挙動の確かめ（厳密側・S2a の集合・#power-lost・量が 1 つに決まる組）を分けて書く
- 盤面は直接作った盤面（constructed）。合法な操作の列（legal）の確かめは、道具の対戦（v0.144 の仕様案の 19 局のうち 1 局）でする
- 規約集合だけを置きかえた同じ盤面・同じ乱数で、厳密側・S2a・PO を比べる
"""

from __future__ import annotations

import copy
import pickle
import unittest
from types import MappingProxyType
from unittest import mock

from kyuura_engine import (
    EvolvePokemon,
    PlayTrainer,
    UseAttack,
    UsePokemonPower,
    check_invariants,
)
from kyuura_engine import conventions as C
from kyuura_engine import effects as E
from kyuura_engine import procedures as PR
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import visible_log
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from tests import helpers as H
from tests import test_marker_check_field_reset_v0_91 as V91
from tests import test_sc2_integrity_v0_144 as SC2
from tests import test_sudden_death_v0_134 as SD
from tests.helpers import apply_kernel, with_coin_results
from tests.log_audit import (
    log_problems,
    observation_problems,
    s2a_problems,
    serialization_problems,
)
from tests.test_damage_reactions_poison_sleep_v0_119 import (
    HD,
    SHUCKLE,
    TL,
    WEEZING,
    F,
    G,
    answer,
    attack,
    board,
    end_turn,
    last,
    mist,
    mon,
    pid,
    uid,
    weezing_board,
)

PO1, PO2, PO3 = "UNRESOLVED_POISON_CHANGE_ORDER", "UNRESOLVED_POISON_MIST_EARLIER_POISON", "UNRESOLVED_POISON_MIST_SOURCE"
ORDER, TARGETS, SOURCE_LEFT = C.POISON_AMOUNT_ORDER_ID, C.POISON_MIST_TARGETS_ID, C.POISON_MIST_SOURCE_LEFT_ID
PO = (C.PO_SET_ID, 1)
SETS = {"strict": C.DEFAULT_SET, "s2a": (C.S2A_SET_ID, 1), "po": PO}
LATEST = max(FORMAT_VERSIONS)


def with_set(state, key):
    """直接作った盤面（今の挙動の集合）の規約集合だけを置きかえる（同じ盤面・同じ乱数）。"""
    new = state.clone()
    new.conventions = C.registered_identity(key)
    return new


def each_set(base):
    return {label: with_set(base, key) for label, key in SETS.items()}


def applied(state, since=0):
    return [dict(e) for e in state.log[since:] if e["kind"] == "convention_applied"]


def po_applied(state, since=0):
    return [(e["convention"], e["pokemon_id"], e["amount"]) for e in applied(state, since) if e["convention"].startswith("PC-POISON")]


def snapshot(state):
    return (repr(state_to_dict(state, format_version=LATEST)), state.rng.getstate(), len(state.log))


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])
    test.assertEqual(s2a_problems(state), [])


def play_trainer(state, card, *answers):
    played = apply_kernel(state, PlayTrainer(0, uid(state, card)))
    for choice in answers:
        played = answer(played, choice)
    return played


def use_mist(state, pokemon_id):
    return apply_kernel(with_coin_results(state, HD), UsePokemonPower(0, pokemon_id, 0))


# 盤面: どれも番のプレイヤー 0 が［ポイズンミスト］（おもて）を使い、そのあとのポケモンチェックで相手（1）のバトル場のポケモンがどくのダメージを受ける


def earlier_poison():
    """PO2: 使う前からどく状態（通常のどく 10）の相手。当てはめれば 20。"""
    return mist(weezing_board(mon(H.HITMONCHAN, (F,)), opponent=mon(H.HITMONCHAN, poison=10)))


def toxic_mist():
    """PO1: どくどくエキス（かける数 2）のどくと［ポイズンミスト］。性質 → ［ポイズンミスト］なら 20、逆なら 40。"""
    return mist(weezing_board(mon(SHUCKLE, (G, G)), opponent=mon(H.HITMONCHAN)))


def toxic_metal():
    """PO1（［ポイズンミスト］なし）: どくどくエキスと鋼エネルギー。性質 → 鋼エネルギーなら 20 - 10 = 10、逆なら 0。"""
    return weezing_board(mon(SHUCKLE, (G, G)), opponent=mon(H.HITMONCHAN, (H.METAL_ENERGY_NIP1X,)))


def source_left(opponent=None):
    """PO3 #source-left: 使ったマタドガスを、フジろうじんで山札にもどした（場をはなれた）あと、どくばりでどくにする。"""
    state = board(mon(H.WEEDLE, (G,)), bench=(mon(WEEZING),), opponent=opponent or mon(H.HITMONCHAN), hand=(H.MR_FUJI,))
    misted = mist(state)
    return play_trainer(misted, H.MR_FUJI, (pid(misted, WEEZING),))


def gas_power_lost():
    """PO3 #power-lost: 使ったマタドガスが場にいるまま、かがくへんかガスで力が消えた。"""
    state = weezing_board(mon(H.WEEDLE, (G,)), opponent=mon(H.HITMONCHAN), bench_extra=(mon(H.GRIMER),), hand=(H.MUK,))
    misted = mist(state)
    return apply_kernel(misted, EvolvePokemon(0, uid(misted, H.MUK), pid(misted, H.GRIMER)))


def devolved_power_lost():
    """PO3 #power-lost: 使ったマタドガスを退化スプレーでドガースにもどした（同じ場のポケモン。場をはなれていない）。"""
    state = board(mon(H.WEEDLE, (G,)), bench=(mon(WEEZING),), opponent=mon(H.HITMONCHAN), hand=(H.DEVOLUTION_SPRAY,))
    misted = mist(state)
    return play_trainer(misted, H.DEVOLUTION_SPRAY, (pid(misted, WEEZING),), (1,))


# ---------------------------------------------------------------- 登録・集合


class RegistrationTest(unittest.TestCase):
    def test_po_set_is_a_partial_development_set(self):
        spec = C.SETS[PO]
        self.assertEqual((spec.usage, spec.completeness), (C.USAGE_DEVELOPMENT, C.COMPLETENESS_HALTS))
        self.assertEqual(spec.members, C.SETS[(C.S2A_SET_ID, 1)].members + C.PO_MEMBERS)  # S2a の 5 規約・基礎集合・今の挙動の記録を引き継ぐ
        self.assertEqual(C.validate(spec), [])
        self.assertEqual(C.identity_of(spec).digest, C.PINNED_SET_DIGESTS[PO])
        for key in C.PO_MEMBERS:
            convention = C.CONVENTIONS[key]
            self.assertEqual((convention.layer, convention.approval), (C.LAYER_CONTINUATION, C.APPROVAL_USER_AGREED))
            self.assertEqual(C.convention_digest(convention), C.PINNED_CONVENTION_DIGESTS[key])
            self.assertIn("公式の裁定", convention.content["adoption"])
        self.assertEqual(C.CONVENTIONS[(SOURCE_LEFT, 1)].scenes, ("UNRESOLVED_POISON_MIST_SOURCE#source-left",))  # #power-lost は入れない
        self.assertNotIn("完成", spec.description.replace("完成したプレイ用の集合ではない", ""))

    def test_existing_sets_are_unchanged(self):
        """厳密側（既定）と S2a の集合は、同じ ID・版・中身・照合値（v0.142・v0.143 の固定の値）。PO の規約を含まない。"""
        self.assertEqual(C.DEFAULT_SET, ("CS-KYUURA-CURRENT", 1))
        for key, digest in ((C.DEFAULT_SET, "sha256:9a9b95c689d86fa01a5b710984560efda3c08f4dbf1d7c6218094ac8666f3cee"),
                            ((C.S2A_SET_ID, 1), "sha256:b317a3f050206577bff35ac05c87fdb4224ee28c6c0222e4e7f8460b5e9410c4")):
            self.assertEqual(C.registered_identity(key).digest, digest)
            self.assertFalse(set(C.PO_MEMBERS) & set(C.SETS[key].members))

    def test_lookup_needs_the_case_for_po3(self):
        """PO3 の場面は 2 つの事例。コードだけでは規約を決めず、#source-left だけが規約に当たる（#power-lost は続行規約なし）。"""
        identity = C.registered_identity(PO)
        self.assertEqual(C.continuation_lookup(identity, PO3).status, "case_not_identified")
        self.assertEqual(C.continuation_lookup(identity, PO3, "source-left").convention, (SOURCE_LEFT, 1))
        self.assertEqual(C.continuation_lookup(identity, PO3, "power-lost").status, "no_continuation")
        for code, convention in ((PO1, ORDER), (PO2, TARGETS)):
            self.assertEqual(C.continuation_lookup(identity, code).convention, (convention, 1))
            self.assertIsNone(C.continuation_lookup(C.registered_identity((C.S2A_SET_ID, 1)), code).convention)


# ---------------------------------------------------------------- 変えていない挙動: 厳密側・S2a は今のまま止まる


class UnchangedStopsTest(unittest.TestCase):
    CASES = (
        ("PO2", earlier_poison, end_turn, PO2),
        ("PO1 toxic+mist", toxic_mist, lambda s: attack(s, 0, HD), PO1),
        ("PO1 toxic+metal", toxic_metal, lambda s: attack(s, 0, HD), PO1),
        ("PO3 source-left", source_left, lambda s: attack(s, 0, HD), PO3),
    )

    def test_strict_and_s2a_halt_as_before(self):
        for name, make, act, code in self.CASES:
            base = make()
            for label in ("strict", "s2a"):
                with self.subTest(name=name, set=label):
                    done = act(with_set(base, SETS[label]))
                    self.assertEqual((done.phase.value, done.halt.code), ("halted", code))
                    self.assertEqual(applied(done, len(base.log)), [])
                    self.assertEqual([e for e in done.log[len(base.log):] if e["kind"] == "poison_damage"], [])  # ダメージの前に止まる

    def test_power_lost_halts_in_every_set(self):
        """#power-lost（かがくへんかガス・退化スプレー）は、PO の集合でも同じ停止コードで止まる（規約の対象外）。"""
        for name, make in (("gas", gas_power_lost), ("devolution", devolved_power_lost)):
            base = make()
            self.assertTrue(base.poison_mists[0].interrupted)
            self.assertIsNotNone(base.find_pokemon(base.poison_mists[0].pokemon_id))  # 発生源は場にいる
            for label, state in each_set(base).items():
                with self.subTest(name=name, set=label):
                    done = attack(state, 0, HD)
                    self.assertEqual(done.halt.code, PO3)
                    self.assertEqual(applied(done, len(base.log)), [])

    def test_amount_fixed_cases_are_the_same_in_every_set(self):
        """量が 1 つに決まる組（使ったあとのどく・特殊などく 20・通常のどくと鋼エネルギー・発生源のバトル場とベンチの移動）は、どの集合でも同じ量・同じログで、規約の記録がない。"""
        switched = board(mon(WEEZING), bench=(mon(H.WEEDLE, (G,)),), opponent=mon(H.HITMONCHAN), hand=(H.SWITCH,))
        cases = {
            "new poison": (weezing_board(mon(H.WEEDLE, (G,)), opponent=mon(H.HITMONCHAN)), lambda s: attack(mist(s), 0, HD), 20),
            "earlier special 20": (weezing_board(mon(H.HITMONCHAN, (F,)), opponent=mon(H.HITMONCHAN, poison=20)), lambda s: end_turn(mist(s)), 20),
            "normal+metal": (weezing_board(mon(H.HITMONCHAN, (F,)), opponent=mon(H.HITMONCHAN, (H.METAL_ENERGY_NIP1X,), poison=10)), end_turn, 0),
            "switch (not left)": (switched, lambda s: attack(play_trainer(mist(s), H.SWITCH, (s.players[0].bench[0].pokemon_id,)), 0, HD), 20),
        }
        for name, (base, act, amount) in cases.items():
            results = {label: act(state) for label, state in each_set(base).items()}
            with self.subTest(name=name):
                logs = {label: [dict(e) for e in st.log] for label, st in results.items()}
                self.assertEqual(logs["strict"], logs["po"])
                self.assertEqual(logs["s2a"], logs["po"])
                self.assertEqual(last(results["po"], "poison_damage")["amount"], amount)
                self.assertEqual(applied(results["po"]), [])


# ---------------------------------------------------------------- 新しい規約: PO の集合だけが続く


class ContinuationTest(unittest.TestCase):
    def test_targets_applies_to_earlier_poison(self):
        base = earlier_poison()
        done = end_turn(with_set(base, PO))
        checked = last(done, "poison_damage")
        self.assertEqual((checked["amount"], checked["poison_mists"]), (20, (pid(base, WEEZING),)))
        self.assertEqual(po_applied(done, len(base.log)), [(TARGETS, checked["pokemon_id"], 20)])
        record = applied(done, len(base.log))[0]
        self.assertEqual((record["scene"], record["code"], record["poison_mists"]), (PO2, PO2, (pid(base, WEEZING),)))
        audited(self, done)

    def test_targets_follows_poison_at_check_time(self):
        """使ったあとにどくになった・回復した・またどくになったポケモンは、ポケモンチェックの時点の状態で決める（どれも 20。記録 poisoned_before は量の判断に使わない）。"""
        misted = mist(weezing_board(mon(H.WEEDLE, (G,)), opponent=mon(H.HITMONCHAN, poison=10)))
        self.assertEqual(misted.poison_mists[0].poisoned_before, (misted.players[1].active.pokemon_id,))
        # 回復してまたどくになったポケモンは、記録 poisoned_before から除かれる（conditions.poison）。その状態を、記録だけを置きかえた複製で作る（constructed）
        renewed = misted.clone()
        renewed.poison_mists = (E._dataclass_replace(renewed.poison_mists[0], poisoned_before=()),)
        for label, state in (("earlier", misted), ("re-poisoned", renewed)):
            with self.subTest(label=label):
                done = attack(with_set(state, PO), 0, HD)
                self.assertEqual(last(done, "poison_damage")["amount"], 20)
                self.assertEqual([c for c, _, _ in po_applied(done, len(state.log))], [TARGETS] if label == "earlier" else [])

    def test_amount_order_with_mist_and_metal(self):
        cases = {
            "toxic+mist": (toxic_mist(), 20, None),
            "toxic+metal": (toxic_metal(), 10, 20),
            "toxic+mist+metal": (mist(weezing_board(mon(SHUCKLE, (G, G)), opponent=mon(H.HITMONCHAN, (H.METAL_ENERGY_NIP1X,)))), 10, 20),
        }
        for name, (base, amount, before) in cases.items():
            with self.subTest(name=name):
                done = attack(with_set(base, PO), 0, HD)
                checked = last(done, "poison_damage")
                self.assertEqual((checked["amount"], checked.get("amount_before"), checked["multiplier"]), (amount, before, 2))
                self.assertEqual([c for c, _, _ in po_applied(done, len(base.log))], [ORDER])
                audited(self, done)

    def test_source_left_ends_only_that_record(self):
        for name, opponent in (("new poison", None), ("earlier poison", mon(H.HITMONCHAN, poison=10))):
            base = source_left(opponent)
            record = base.poison_mists[0]
            self.assertTrue(record.interrupted)
            self.assertIsNone(base.find_pokemon(record.pokemon_id))
            with self.subTest(name=name):
                done = attack(with_set(base, PO), 0, HD)
                checked = last(done, "poison_damage")
                self.assertEqual((checked["amount"], checked.get("poison_mists")), (10, None))
                records = applied(done, len(base.log))
                self.assertEqual([(r["convention"], r["scene"], r["ended_mists"]) for r in records],
                                 [(SOURCE_LEFT, f"{PO3}#source-left", (record.pokemon_id,))])
                self.assertEqual(done.poison_mists, base.poison_mists)  # 記録・中断の印は変えない（使ったプレイヤーの次の番の始めに今までどおり消える）
                audited(self, done)


class MultipleSourcesTest(unittest.TestCase):
    def two_weezings(self, hand):
        state = board(mon(H.WEEDLE, (G,)), bench=(mon(WEEZING), mon(WEEZING), mon(H.GRIMER)), opponent=mon(H.HITMONCHAN), hand=hand)
        first, second = (p.pokemon_id for p in state.players[0].bench[:2])
        return use_mist(use_mist(state, first), second), first, second

    def test_one_source_leaves_and_the_other_stays(self):
        """発生源ごとに記録を分ける。1 匹だけが場をはなれても、もう 1 匹の記録ははたらく（どの集合でも 20。止めない・規約の記録もない）。"""
        misted, first, second = self.two_weezings((H.MR_FUJI,))
        left = play_trainer(misted, H.MR_FUJI, (first,))
        self.assertEqual([(r.pokemon_id, r.interrupted) for r in left.poison_mists], [(first, True), (second, False)])
        for label, state in each_set(left).items():
            with self.subTest(set=label):
                done = attack(state, 0, HD)
                checked = last(done, "poison_damage")
                self.assertEqual((checked["amount"], checked["poison_mists"]), (20, (second,)))
                self.assertEqual(applied(done, len(left.log)), [])

    def test_left_and_power_lost_sources_still_halt(self):
        """1 匹は場をはなれ、もう 1 匹はかがくへんかガスで力が消えた: 場をはなれた記録は当てはめないが、力の消えた記録（#power-lost）で量が変わるので、PO の集合でも止める。"""
        misted, first, second = self.two_weezings((H.MR_FUJI, H.MUK))
        left = play_trainer(misted, H.MR_FUJI, (first,))
        gassed = apply_kernel(left, EvolvePokemon(0, uid(left, H.MUK), pid(left, H.GRIMER)))
        self.assertEqual([(r.pokemon_id, r.interrupted) for r in gassed.poison_mists], [(first, True), (second, True)])
        for label, state in each_set(gassed).items():
            with self.subTest(set=label):
                before = snapshot(state)
                done = attack(state, 0, HD)
                self.assertEqual(done.halt.code, PO3)
                self.assertIn(f"記録 [{second}]" if label == "po" else f"記録 [{first}, {second}]", done.halt.message)
                self.assertEqual(applied(done, len(gassed.log)), [])
                self.assertEqual(snapshot(state), before)
                self.assertEqual(check_invariants(done), [])  # 整合した状態で止まる（ダメージの前）

    def test_source_left_with_earlier_poison_records_only_what_decided(self):
        """場をはなれた発生源の記録と、使う前からのどく: 当てはめない読み方だけで量が決まるので、記録は発生源の規約だけ（当てはまる相手の規約は結果を変えない）。"""
        done = attack(with_set(source_left(mon(H.HITMONCHAN, poison=10)), PO), 0, HD)
        self.assertEqual([c for c, _, _ in po_applied(done)], [SOURCE_LEFT])


# ---------------------------------------------------------------- 組み合わせ・安全対策


class CombinationTest(unittest.TestCase):
    def test_with_side_order_and_knockout(self):
        """S2a の両側のコイン（両方のねむり）・くろこげマーカーのコインときぜつと、どくの量の規約が同じポケモンチェックで当たる。"""
        both = mist(board(mon(H.HITMONCHAN, sleep=True), bench=(mon(WEEZING),), opponent=mon(H.HITMONCHAN, poison=10, sleep=True)))
        done = end_turn(with_set(both, PO), TL, TL)
        self.assertEqual([e["convention"] for e in applied(done, len(both.log))], [TARGETS, "PC-CHECK-SIDE-ORDER"])
        audited(self, done)
        self.assertEqual(end_turn(with_set(both, SETS["s2a"]), TL, TL).halt.code, PO2)
        knocked = mist(board(mon(H.HITMONCHAN, (F,)), bench=(mon(WEEZING),), opponent=mon(H.HITMONCHAN, poison=10, damage=50, markers=[V91.MARKER_CHAR])))
        done = end_turn(with_set(knocked, PO), TL)
        self.assertTrue([e for e in done.log[len(knocked.log):] if e["kind"] == "knock_out" and e["player"] == 1])
        self.assertEqual([c for c, _, _ in po_applied(done, len(knocked.log))], [TARGETS])
        audited(self, done)

    def test_sc2_safety_stop_is_kept(self):
        """v0.144 の SC2 の安全対策（ダメージの前の停止）は、PO の集合でも同じ。"""
        base = SC2.reported()
        done = V91.end_turn(with_set(base, PO))
        self.assertEqual(done.halt.code, "UNRESOLVED_SCRAM_POWER_RESTORED")
        self.assertEqual(SC2.damage_of(done), SC2.damage_of(base))


# ---------------------------------------------------------------- 先読みと実行・拒否・保存・延長戦・ログ


class ConsistencyTest(unittest.TestCase):
    def test_precheck_and_execution_use_the_same_amount_and_record_once(self):
        base = with_set(toxic_mist(), PO)
        seen = []
        original = E.poison_check_amount

        def spy(state, owner, pokemon):
            found = original(state, owner, pokemon)
            seen.append((found.amount, found.before_metal, found.conventions))
            return found

        with mock.patch.object(PR, "poison_check_amount", spy):
            done = attack(base, 0, HD)
        self.assertGreaterEqual(len(seen), 2)  # 確かめ（複製の上）と実際の処理
        self.assertEqual(len(set(seen)), 1)
        self.assertEqual(len(po_applied(done, len(base.log))), 1)

    def test_rejected_command_changes_nothing(self):
        for make in (earlier_poison, toxic_mist):
            state = with_set(make(), PO)
            before = snapshot(state)
            with self.assertRaises((IllegalActionError, UnsupportedError)):
                apply_kernel(state, UseAttack(1, 0))  # 番でないプレイヤーのワザ
            self.assertEqual(snapshot(state), before)

    def test_halted_state_is_not_resumed(self):
        """厳密側・S2a で止まった状態は、そのまま止まっている（規約集合を置きかえて再開する操作はない。止まった状態への操作は断る）。"""
        halted = end_turn(with_set(earlier_poison(), SETS["s2a"]))
        before = snapshot(halted)
        with self.assertRaises((IllegalActionError, UnsupportedError)):
            end_turn(halted)
        self.assertEqual(snapshot(halted), before)

    def test_save_restore_and_formats(self):
        base = with_set(earlier_poison(), PO)
        for copied in (base.clone(), copy.deepcopy(base), pickle.loads(pickle.dumps(base))):
            self.assertEqual(copied.conventions, C.registered_identity(PO))
            self.assertEqual(copied.poison_mists, base.poison_mists)
            done = end_turn(copied)
            self.assertEqual((last(done, "poison_damage")["amount"], po_applied(done, len(base.log))[0][0]), (20, TARGETS))
        data = state_to_dict(base, format_version=LATEST)
        self.assertEqual((data["convention_set"]["id"], data["convention_set"]["version"]), PO)
        with self.assertRaises(ValueError):
            state_to_dict(base, format_version=34)  # 形式 34 までは続行側の集合を表せない（黙って厳密側にしない）

    def test_sudden_death_keeps_the_set(self):
        state = H.build_test_state([{"active": SD.PIKA, "deck": [SD.PIKA] + [SD.FIRE] * 30, "prizes": 0},
                                    {"active": SD.PIKA, "deck": [SD.PIKA] + [SD.FIRE] * 30, "prizes": 0}])
        base = SD.constructed_sudden_death(SD.with_decklists(state))
        started = SD.start(with_set(base, PO))
        self.assertEqual(started.conventions, C.registered_identity(PO))

    def test_records_are_public_and_complete(self):
        done = attack(with_set(source_left(), PO), 0, HD)
        for viewer in (0, 1, None):
            events = [e for e in visible_log(done, viewer) if e["kind"] == "convention_applied"]
            self.assertEqual(len(events), 1)
            self.assertEqual(set(events[0]) - {"kind", "turn", "convention", "version", "scene", "code"}, {"pokemon_id", "amount", "ended_mists"})
        self.assertLessEqual({k for e in applied(done) for k in e} - {"kind", "turn", "convention", "version", "scene", "code"}, C.APPLIED_FIELDS)

    def test_audit_detects_misplaced_or_foreign_records(self):
        done = attack(with_set(source_left(), PO), 0, HD)
        log = [dict(e) for e in done.log]
        i = next(k for k, e in enumerate(log) if e["kind"] == "convention_applied")
        for change in ({"pokemon_id": 99}, {"amount": 20}, {"convention": "PC-UNKNOWN"}, {"hand": [1]}):
            tampered = copy.copy(done)
            tampered.log = tuple(MappingProxyType({**e, **change} if k == i else e) for k, e in enumerate(log))
            self.assertTrue(s2a_problems(tampered), change)
        moved = copy.copy(done)
        moved.log = tuple(MappingProxyType(e) for e in log[:i] + log[i + 1:-1] + [log[i], log[-1]])
        self.assertTrue(s2a_problems(moved))
        s2a_like = copy.copy(done)
        s2a_like.conventions = C.registered_identity(SETS["s2a"])  # 状態の集合にない規約の記録
        self.assertTrue(s2a_problems(s2a_like))


# ---------------------------------------------------------------- 合法な操作の列（道具の対戦。v0.144 の仕様案の 19 局のうち 1 局）


class LegalSequenceTest(unittest.TestCase):
    """v0.119 P119-D119 seed 2（席 P119 → D119）: S2a の集合では PO3 で止まり、PO の集合では発生源の規約と当てはまる相手の規約で終局まで進む。ログの監査
    （v145_poison_problems: エンジンの記録を読まずに量・規約を求め直す）が通り、規約の記録を消す・変えると見つける。"""

    @classmethod
    def setUpClass(cls):
        from tools import existing_effect_games as G
        from tools.convention_choice import restore_conventions, use_conventions

        cls.results = {}
        try:
            for label in ("s2a", "po"):
                use_conventions(f"{SETS[label][0]}@1")
                cls.results[label] = G.play(("P119", "D119"), 2, keep_state=True)
                restore_conventions()
        finally:
            restore_conventions()

    def test_s2a_halts_and_po_continues(self):
        s2a, po = self.results["s2a"], self.results["po"]
        self.assertEqual((s2a["state"].phase.value, s2a["state"].halt.code), ("halted", PO3))
        self.assertEqual(po["state"].phase.value, "game_over")
        self.assertEqual((s2a["audit"], po["audit"]), ({}, {}))
        found = {e["convention"] for e in po["state"].log if e["kind"] == "convention_applied"}
        self.assertTrue({SOURCE_LEFT, TARGETS} <= found)
        # 最初の規約の記録の前までは、S2a の対戦と同じログ（最初の意図した差は規約の記録）
        first = next(k for k, e in enumerate(po["state"].log) if e["kind"] == "convention_applied")
        self.assertEqual([dict(e) for e in po["state"].log[:first]], [dict(e) for e in s2a["state"].log[:first]])

    def test_log_audit_rebuilds_the_decisions(self):
        state = self.results["po"]["state"]
        self.assertEqual(log_problems(state), [])
        log = [dict(e) for e in state.log]
        i = next(k for k, e in enumerate(log) if e["kind"] == "convention_applied" and e["convention"].startswith("PC-POISON"))
        removed = copy.copy(state)
        removed.log = tuple(MappingProxyType(e) for k, e in enumerate(log) if k != i)
        self.assertTrue(log_problems(removed))
        swapped = copy.copy(state)
        other = TARGETS if log[i]["convention"] != TARGETS else ORDER
        swapped.log = tuple(MappingProxyType({**e, "convention": other} if k == i else e) for k, e in enumerate(log))
        self.assertTrue(log_problems(swapped))


if __name__ == "__main__":
    unittest.main()
