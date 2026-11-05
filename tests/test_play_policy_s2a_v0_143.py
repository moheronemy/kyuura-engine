"""v0.143（docs/play-policy-s2a-v0.143.md）: S2a の続行規約 5 件（開発用の部分的な集合 CS-KYUURA-PLAY-S2A@1）。

厳密側（今の挙動の集合 CS-KYUURA-CURRENT@1）と続行側を、同じ盤面・同じ乱数の状態で比べる。各クラスの説明に、``new_game`` からの合法な操作の列で確かめたか（legal）、
盤面を直接作った状態・補助関数だけで確かめたか（constructed）を書く。
"""

from __future__ import annotations

import copy
import dataclasses
import pickle
import unittest
from types import MappingProxyType
from unittest import mock

from kyuura_engine import (
    DrawMulliganCards,
    EndTurn,
    PlaceStartingPokemon,
    PlayTrainer,
    ReportJankenResult,
    apply_command,
    check_invariants,
    new_game,
)
from kyuura_engine import conventions as C
from kyuura_engine import effects as E
from kyuura_engine.coins import CoinSide
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.interruption import check_quantity
from kyuura_engine.observation import visible_log
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import Phase
from tests import helpers as H
from tests import test_deferred_shortage_user_promos_v0_127 as V127
from tests import test_marker_check_field_reset_v0_91 as V91
from tests import test_sudden_death_v0_134 as SD
from tests.helpers import build_test_state, expand_decklist, with_coin_results
from tests.log_audit import (
    S2A_PLAY_AS_CARDS,
    log_problems,
    observation_problems,
    s2a_problems,
    serialization_problems,
    v127_problems,
)

PLAY = f"{C.S2A_SET_ID}@1"
STRICT = f"{C.CURRENT_SET_ID}@1"
LATEST = max(FORMAT_VERSIONS)
HD, TL = CoinSide.HEADS, CoinSide.TAILS
MULLIGAN = "UNRESOLVED_MULLIGAN_COMPENSATION"
PLAY_AS = E.PLAY_AS_POKEMON_SETUP_CODE
SLEEP = "UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER"
KK1 = "UNRESOLVED_POKEMON_CHECK_CHAR_COIN_ORDER"
PK1 = "UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT"
DRATINI = H.DRATINI  # たねポケモン（v0.142 の試験と同じ: たね 1 枚のデッキで切り直しがよく起こる）
FEW_BASICS = expand_decklist({DRATINI: 1, H.LIGHTNING: 59})
FOSSIL_DECK = expand_decklist({"PMCG1-091": 3, "PMCG3-046": 3, DRATINI: 1, H.LIGHTNING: 53})


def play_identity():
    return C.registered_identity((C.S2A_SET_ID, 1))


def as_play(state):
    """盤面を直接作った状態（今の挙動の集合）を、同じ盤面・同じ乱数の続行側の状態にする（constructed。規約集合だけを置きかえる）。"""
    new = state.clone()
    new.conventions = play_identity()
    return new


def applied(state, since=0):
    return [dict(e) for e in state.log[since:] if e["kind"] == "convention_applied"]


def kinds(state, since=0):
    return [e["kind"] for e in state.log[since:]]


def snapshot(state):
    return (repr(state_to_dict(state, format_version=LATEST)), state.rng.getstate(), len(state.log))


def rounds_of(state):
    return [len(r) for r in state.mulligan_rounds]


def audited(test, state, *, legal=False):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])
    test.assertEqual(s2a_problems(state), [])
    if legal:
        test.assertEqual(log_problems(state), [])


def seeds_where(deck, predicate, limit=400):
    return [seed for seed in range(limit) if predicate(new_game(deck, deck, seed))]


# ---------------------------------------------------------------- S2a-0: 登録・照会（constructed: 登録表と集合の確かめだけ）


class RegistrationTest(unittest.TestCase):
    def test_play_set_is_a_partial_development_set(self):
        spec = C.SETS[(C.S2A_SET_ID, 1)]
        self.assertEqual((spec.usage, spec.completeness), (C.USAGE_DEVELOPMENT, C.COMPLETENESS_HALTS))  # 完成したプレイ用の集合ではない
        self.assertEqual(spec.members, C.SETS[C.DEFAULT_SET].members + C.S2A_MEMBERS)
        self.assertEqual(C.validate(spec), [])
        self.assertEqual(C.identity_of(spec).digest, C.PINNED_SET_DIGESTS[(C.S2A_SET_ID, 1)])
        for key in C.S2A_MEMBERS:
            convention = C.CONVENTIONS[key]
            self.assertEqual((convention.layer, convention.approval), (C.LAYER_CONTINUATION, C.APPROVAL_USER_AGREED))
            self.assertEqual(C.convention_digest(convention), C.PINNED_CONVENTION_DIGESTS[key])
        # v0.145: この版が処理を持つ続行規約に PO の 3 件が加わった（別の集合 CS-KYUURA-PLAY-PO@1 だけ）。S2a の集合の中の続行規約は S2a の 5 件のまま
        self.assertEqual(C.DEFAULT_REGISTRY.implemented_continuations & frozenset(spec.members), frozenset(C.S2A_MEMBERS))
        self.assertNotIn("完成", spec.description.replace("完成したプレイ用の集合ではない", ""))

    def test_strict_set_is_unchanged(self):
        spec = C.SETS[C.DEFAULT_SET]
        self.assertEqual(C.identity_of(spec).digest, "sha256:9a9b95c689d86fa01a5b710984560efda3c08f4dbf1d7c6218094ac8666f3cee")  # v0.142 の固定の値のまま
        self.assertFalse(set(spec.members) & set(C.S2A_MEMBERS))
        self.assertEqual(C.default_identity().key, C.DEFAULT_SET)

    def test_scenes_do_not_overlap_and_are_known(self):
        scenes = [s for key in C.S2A_MEMBERS for s in C.CONVENTIONS[key].scenes]
        self.assertEqual(len(scenes), len(set(scenes)))
        known = {s["id"] for s in C.scene_index()["scenes"]}
        self.assertLessEqual(set(scenes), known)
        self.assertNotIn("UNRESOLVED_POKEMON_CHECK_BERRY_ORDER", scenes)  # BY1 は対象外
        self.assertNotIn("UNSUPPORTED_POKEMON_CHECK_CHAR_COINS", scenes)  # 技術的上限は外さない

    def test_lookup_only_in_the_play_set(self):
        strict, play = build_test_state([{"active": H.RATTATA}, {"active": H.RATTATA}]), None
        play = as_play(strict)
        cases = [(MULLIGAN, "initial-setup"), (MULLIGAN, "sudden-death-segment"), (PLAY_AS, "initial-setup"), (PLAY_AS, "sudden-death-segment"),
                 (PLAY_AS, "setup-placement"), (SLEEP, None), (KK1, None), (PK1, None), (E.DRY_UP_SHORT_CODE, None), (E.THOUGHT_WAVE_SHORT_CODE, None)]
        for code, case in cases:
            with self.subTest(code=code, case=case):
                self.assertIsNone(C.continuation_for(strict, code, case))
                found = C.continuation_for(play, code, case)
                self.assertIsNotNone(found)
                self.assertEqual(found.scene, code if case is None else f"{code}#{case}")
                with self.assertRaises(RuntimeError):  # 続ける分岐を通らずに止めようとしたらエンジンの不具合
                    C.stop_without_continuation(play, code, case)
        self.assertIsNone(C.continuation_for(play, MULLIGAN))  # 事例を渡さなければ、コードだけで規約を決めない
        for code in ("UNRESOLVED_POKEMON_CHECK_BERRY_ORDER", "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT", "UNSUPPORTED_POKEMON_CHECK_CHAR_COINS",
                     "UNRESOLVED_THOUGHT_WAVE_MACHINE_WITHOUT_TARGET", "UNRESOLVED_SCRAM_TIMING"):
            self.assertIsNone(C.continuation_for(play, code, "pokemon-check" if code == "UNRESOLVED_SCRAM_TIMING" else None), code)

    def test_registration_inconsistencies_are_rejected(self):
        from tests.test_conventions_v0_142 import make_registry

        convention = C.CONVENTIONS[(C.MULLIGAN_COUNT_ID, 1)]
        partial = C.ConventionSet("CS-TEST-PARTIAL", 1, C.USAGE_DEVELOPMENT, C.SETS[C.DEFAULT_SET].members + ((C.MULLIGAN_COUNT_ID, 1),))
        registry = make_registry(sets=(partial,), implemented=C.IMPLEMENTED_CONTINUATIONS)
        self.assertEqual(C.validate(partial, registry), [])  # 規約の一部だけの集合（試験の登録表だけ）
        unimplemented = make_registry(sets=(partial,))
        self.assertTrue(any("処理を持たない" in p for p in C.validate(partial, unimplemented)))
        changed = dataclasses.replace(convention, statement=convention.statement + "（変えた）")
        moved = make_registry(changed, sets=(partial,), pin=False, implemented=C.IMPLEMENTED_CONTINUATIONS)
        self.assertTrue(any("固定した照合値と違う" in p for p in C.validate(partial, moved)))
        lost = dataclasses.replace(convention, version=2, scenes=("UNRESOLVED_MULLIGAN_COMPENSATION#nowhere",))
        lost_set = C.ConventionSet("CS-TEST-LOST", 1, C.USAGE_DEVELOPMENT, C.SETS[C.DEFAULT_SET].members + ((C.MULLIGAN_COUNT_ID, 2),))
        registry = make_registry(lost, sets=(lost_set,), implemented={(C.MULLIGAN_COUNT_ID, 2)})
        self.assertTrue(any("台帳の場面にない" in p for p in C.validate(lost_set, registry)))
        twice = dataclasses.replace(C.CONVENTIONS[(C.KO_POINT_ID, 1)], id="PC-TEST-TWICE")
        both = C.ConventionSet("CS-TEST-TWICE", 1, C.USAGE_DEVELOPMENT, C.SETS[(C.S2A_SET_ID, 1)].members + (("PC-TEST-TWICE", 1),))
        registry = make_registry(twice, sets=(both,), implemented=C.IMPLEMENTED_CONTINUATIONS | {("PC-TEST-TWICE", 1)})
        self.assertTrue(any("2 つ以上の規約" in p for p in C.validate(both, registry)))
        standard = dataclasses.replace(C.SETS[(C.S2A_SET_ID, 1)], usage=C.USAGE_STANDARD)
        self.assertTrue(any("中身が、登録した同じ ID・版の集合と違う" in p for p in C.validate(standard)))  # 同じ ID・版の区分は変えられない

    def test_record_rejects_unknown_fields(self):
        play = as_play(build_test_state([{"active": H.RATTATA}, {"active": H.RATTATA}]))
        lookup = C.continuation_for(play, SLEEP)
        with self.assertRaises(RuntimeError):
            C.record_application(play, lookup, hand=(1, 2))  # 秘密の情報の項目は書けない
        with self.assertRaises(RuntimeError):
            C.record_application(play, None)


# ---------------------------------------------------------------- S2a-1: 切り直しの補償（legal: new_game からの準備）


class MulliganCompensationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.by_shape = {}
        for seed in range(400):
            state = new_game(FEW_BASICS, FEW_BASICS, seed, conventions=PLAY)
            both = sum(1 for r in state.mulligan_rounds if len(r) == 2)
            single = sum(1 for r in state.mulligan_rounds if len(r) == 1)
            cls.by_shape.setdefault((min(both, 3), min(single, 3)), seed)

    def test_shapes_found(self):
        for shape in ((1, 1), (1, 2), (2, 1), (0, 1), (0, 2), (1, 0)):
            self.assertIn(shape, self.by_shape, shape)

    def test_both_then_single_gets_one_per_single_round(self):
        for shape in ((1, 1), (1, 2), (2, 1)):
            seed = self.by_shape[shape]
            with self.subTest(shape=shape, seed=seed):
                strict = new_game(FEW_BASICS, FEW_BASICS, seed)
                play = new_game(FEW_BASICS, FEW_BASICS, seed, conventions=PLAY)
                self.assertEqual((strict.phase, strict.halt.code), (Phase.HALTED, MULLIGAN))
                self.assertIs(play.phase, Phase.SETUP_PLACEMENT)
                self.assertEqual(play.rng.getstate(), strict.rng.getstate())  # 乱数の位置は同じ（新しい決定・乱数の消費がない）
                self.assertEqual([dict(e) for e in play.log[:len(strict.log) - 1]], [dict(e) for e in strict.log[:-1]])  # 止める直前まで同じ
                single_player = next(r[0] for r in play.mulligan_rounds if len(r) == 1)
                record = applied(play)
                self.assertEqual(record, [{"kind": "convention_applied", "turn": 0, "convention": C.MULLIGAN_COUNT_ID, "version": 1,
                                           "scene": f"{MULLIGAN}#initial-setup", "code": MULLIGAN, "rounds_both": shape[0], "rounds_single": shape[1],
                                           "player": 1 - single_player}])
                self.assertEqual([p.mulligan_draws_remaining for p in play.players][1 - single_player], shape[1])
                self.assertEqual(play.players[single_player].mulligan_draws_remaining, 0)
                audited(self, play, legal=True)
                self.compensate(play, 1 - single_player, shape[1])

    def compensate(self, state, receiver, count):
        """最初のポケモンを出してサイドを置いたあと、補償を受けるプレイヤーだけが 1 回ずつ 0〜2 枚を選ぶ（3 枚・相手は拒否。状態・乱数・ログは変えない）。"""
        for player in (0, 1):
            basic = next(uid for uid in state.players[player].hand if state.card_def(uid).is_baby_or_basic_pokemon)
            state = apply_command(state, PlaceStartingPokemon(player, basic))
        self.assertIs(state.phase, Phase.SETUP_MULLIGAN_DRAW)
        before = snapshot(state)
        for bad in (DrawMulliganCards(receiver, 3), DrawMulliganCards(1 - receiver, 1)):
            with self.assertRaises(IllegalActionError):
                apply_command(state, bad)
            self.assertEqual(snapshot(state), before)
        for i in range(count):
            state = apply_command(state, DrawMulliganCards(receiver, i % 3))
        self.assertIs(state.phase, Phase.SETUP_FIRST_PLAYER)
        self.assertEqual([e["count"] for e in state.log if e["kind"] == "mulligan_draw"], [i % 3 for i in range(count)])
        state = apply_command(state, ReportJankenResult(0))
        audited(self, state, legal=True)

    def test_only_one_kind_of_round_is_unchanged(self):
        for shape in ((0, 1), (0, 2), (1, 0)):
            seed = self.by_shape[shape]
            with self.subTest(shape=shape):
                strict = new_game(FEW_BASICS, FEW_BASICS, seed)
                play = new_game(FEW_BASICS, FEW_BASICS, seed, conventions=PLAY)
                self.assertEqual([dict(e) for e in play.log], [dict(e) for e in strict.log])
                self.assertEqual([p.mulligan_draws_remaining for p in play.players], [p.mulligan_draws_remaining for p in strict.players])
                self.assertEqual(applied(play), [])

    def test_strict_halt_is_unchanged(self):
        seed = self.by_shape[(1, 1)]
        strict = new_game(FEW_BASICS, FEW_BASICS, seed, conventions=STRICT)
        self.assertEqual(state_to_dict(strict, format_version=34), state_to_dict(new_game(FEW_BASICS, FEW_BASICS, seed), format_version=34))
        self.assertEqual(strict.log[-1]["kind"], "halted")
        self.assertEqual(applied(strict), [])

    def test_compensation_basics_are_not_placed(self):
        """補償で引いたたね・ベイビィは手札に加わるだけ（最初のポケモンの配置は終わっている。切り直しの回にも数えない）。"""
        seed = self.by_shape[(1, 1)]
        state = new_game(FEW_BASICS, FEW_BASICS, seed, conventions=PLAY)
        for player in (0, 1):
            basic = next(uid for uid in state.players[player].hand if state.card_def(uid).is_baby_or_basic_pokemon)
            state = apply_command(state, PlaceStartingPokemon(player, basic))
        receiver = next(p for p in (0, 1) if state.players[p].mulligan_draws_remaining)
        rounds = state.mulligan_rounds
        drawn = apply_command(state, DrawMulliganCards(receiver, 2))
        self.assertEqual(drawn.mulligan_rounds, rounds)
        self.assertEqual(len(drawn.players[receiver].bench), 0)


# ---------------------------------------------------------------- S2a-1: 化石・人形の初手（legal: new_game からの準備。配置の拒否も同じ）


class PlayAsPokemonTest(unittest.TestCase):
    def test_target_cards_by_registration(self):
        cards = sorted(c for c in E.DEFAULT_EFFECTS.trainer_ids() if isinstance(E.DEFAULT_EFFECTS.trainer_entry(c).effect, E.PlayAsPokemon))
        self.assertEqual(cards, sorted(S2A_PLAY_AS_CARDS))  # 今の対象（登録の型で識別）が、監査の一覧と同じ

    def test_fossil_only_hand_is_mulliganed(self):
        shapes = {}
        for seed in range(300):
            strict = new_game(FOSSIL_DECK, FOSSIL_DECK, seed)
            play = new_game(FOSSIL_DECK, FOSSIL_DECK, seed, conventions=PLAY)
            if strict.phase is not Phase.HALTED:
                self.assertEqual([dict(e) for e in play.log], [dict(e) for e in strict.log])
                continue
            if strict.halt.code == MULLIGAN:  # 化石・人形のない手札の両方 → 片方（補償の規約。MulliganCompensationTest）
                self.assertEqual([e["convention"] for e in applied(play)], [C.MULLIGAN_COUNT_ID])
                continue
            self.assertEqual(strict.halt.code, PLAY_AS)
            self.assertEqual([dict(e) for e in play.log[:len(strict.log) - 1]], [dict(e) for e in strict.log[:-1]])
            first = play.log[len(strict.log) - 1]
            self.assertEqual((first["kind"], first["convention"], first["scene"]), ("convention_applied", C.PLAY_AS_POKEMON_ID, f"{PLAY_AS}#initial-setup"))
            self.assertEqual(tuple(first["players"]), strict.log[-1]["players"])
            self.assertEqual(play.log[len(strict.log)]["kind"], "mulligan")
            self.assertNotEqual(play.phase, Phase.HALTED)
            names = tuple(sorted({e["convention"] for e in applied(play)}))
            shapes.setdefault(names, seed)
            audited(self, play, legal=True)
        self.assertIn((C.PLAY_AS_POKEMON_ID,), shapes)
        self.assertIn(tuple(sorted((C.PLAY_AS_POKEMON_ID, C.MULLIGAN_COUNT_ID))), shapes)  # 化石・人形の切り直しのあと両方 → 片方になり、補償の規約も当たる
        self.combined = shapes

    def test_combination_without_mulligan_rule_still_halts(self):
        """化石・人形の規約だけの開発用の集合（試験の登録表）: 化石・人形の手札は切り直すが、両方 → 片方の並びでは UNRESOLVED_MULLIGAN_COMPENSATION で止まる。"""
        from tests.test_conventions_v0_142 import make_registry

        partial = C.ConventionSet("CS-TEST-PLAY-AS", 1, C.USAGE_DEVELOPMENT, C.SETS[C.DEFAULT_SET].members + ((C.PLAY_AS_POKEMON_ID, 1),))
        registry = make_registry(sets=(partial,), implemented=C.IMPLEMENTED_CONTINUATIONS)
        found = None
        for seed in range(300):
            play = new_game(FOSSIL_DECK, FOSSIL_DECK, seed, conventions=PLAY)
            if {e["convention"] for e in applied(play)} == {C.PLAY_AS_POKEMON_ID, C.MULLIGAN_COUNT_ID}:
                found = seed
                break
        self.assertIsNotNone(found)
        from kyuura_engine import engine

        with mock.patch.object(C, "DEFAULT_REGISTRY", registry), mock.patch.object(C, "_IDENTITY_CACHE", {}):
            identity = C.identity_of(partial, registry)
            with mock.patch.object(engine, "resolve_for_new_game", lambda conventions: identity):
                partial_state = new_game(FOSSIL_DECK, FOSSIL_DECK, found)
        self.assertEqual((partial_state.phase, partial_state.halt.code), (Phase.HALTED, MULLIGAN))
        self.assertEqual({e["convention"] for e in applied(partial_state)}, {C.PLAY_AS_POKEMON_ID})

    def test_placement_rejects_fossil(self):
        seed = next(s for s in range(300) if (st := new_game(FOSSIL_DECK, FOSSIL_DECK, s)).phase is Phase.SETUP_PLACEMENT
                    and any(st.cards[u].card_id in S2A_PLAY_AS_CARDS for u in st.players[0].hand))
        for conventions, error, code in ((None, UnsupportedError, PLAY_AS), (PLAY, IllegalActionError, "NOT_BASIC_POKEMON")):
            with self.subTest(conventions=conventions):
                state = new_game(FOSSIL_DECK, FOSSIL_DECK, seed, conventions=conventions)
                fossil = next(u for u in state.players[0].hand if state.cards[u].card_id in S2A_PLAY_AS_CARDS)
                basic = next(u for u in state.players[0].hand if state.card_def(u).is_baby_or_basic_pokemon)
                before = snapshot(state)
                for command in (PlaceStartingPokemon(0, fossil), PlaceStartingPokemon(0, basic, (fossil,))):
                    with self.assertRaises(error) as caught:
                        apply_command(state, command)
                    self.assertEqual(caught.exception.code, code)
                    self.assertEqual(snapshot(state), before)  # 状態・乱数・ログを変えない（規約を当てた記録も残さない）
                placed = apply_command(state, PlaceStartingPokemon(0, basic))
                self.assertEqual(applied(placed, len(state.log)), [])
                self.assertIn(fossil, placed.players[0].hand)

    def test_in_game_bench_use_is_unchanged(self):
        """constructed: 対戦が始まってから手札の化石をベンチに出す処理（v0.47）は両側で同じ。"""
        state = build_test_state([{"active": H.RATTATA, "hand": ["PMCG3-046"]}, {"active": H.RATTATA}])
        fossil = state.players[0].hand[0]
        strict = apply_command(state, PlayTrainer(0, fossil))
        play = apply_command(as_play(state), PlayTrainer(0, fossil))
        self.assertEqual([dict(e) for e in play.log], [dict(e) for e in strict.log])
        self.assertEqual(len(play.players[0].bench), 1)


# ---------------------------------------------------------------- S2a-1: サドン・デスの延長戦の区間（constructed: 延長戦の状態を作り、StartSuddenDeath から）


class SuddenDeathSegmentTest(unittest.TestCase):
    def test_segment_setup_uses_the_same_rules(self):
        found = {}
        for seed in range(200):
            for deck in ([SD.PIKA] + [SD.FIRE] * 30, [SD.FOSSIL] * 4 + [SD.PIKA] + [SD.FIRE] * 26):
                state = build_test_state([{"active": SD.PIKA, "deck": deck, "prizes": 0}, {"active": SD.PIKA, "deck": [SD.PIKA] + [SD.FIRE] * 30, "prizes": 0}],
                                         current_player=0, seed=seed)
                base = SD.constructed_sudden_death(SD.with_decklists(state))
                strict = SD.start(base)
                if strict.phase is not Phase.HALTED or strict.halt.code in found:
                    continue
                play = SD.start(as_play(base))
                self.assertEqual(play.conventions, play_identity())  # 延長戦も同じ集合
                self.assertNotEqual(play.phase, Phase.HALTED)
                scenes = {e["scene"] for e in applied(play)}
                expected = f"{MULLIGAN}#sudden-death-segment" if strict.halt.code == MULLIGAN else f"{PLAY_AS}#sudden-death-segment"
                self.assertIn(expected, scenes)
                self.assertEqual([dict(e) for e in play.log[:len(strict.log) - 1]], [dict(e) for e in strict.log[:-1]])
                audited(self, play)
                found[strict.halt.code] = seed
            if len(found) == 2:
                break
        self.assertEqual(set(found), {MULLIGAN, PLAY_AS})


# ---------------------------------------------------------------- S2a-2: コインで決まる枚数の不足（constructed: v0.127 の盤面。ESP は v0.113 の盤面）


class CoinCountShortTest(unittest.TestCase):
    def test_boundaries_both_sides(self):
        for water in (0, 1, 2, 5):
            for heads in (0, water, water + 1, water + 9):
                with self.subTest(water=water, heads=heads):
                    base = V127.dry_board(water)
                    strict = V127.dry_up(base, heads)
                    play = V127.dry_up(as_play(base), heads)
                    trashed = [e for e in play.log if e["kind"] == "discard_attached_energy"]
                    if heads <= water:
                        self.assertEqual([dict(e) for e in play.log], [dict(e) for e in strict.log])
                        self.assertEqual(applied(play), [])
                    else:
                        self.assertIsNotNone(strict.halt.interruption)
                        self.assertIsNone(play.halt)
                        self.assertEqual(len(trashed), water)  # min(H, N)
                        record = applied(play)
                        self.assertEqual([(r["convention"], r["scene"], r["heads"], r["available"], r["processed"], r["element"]) for r in record],
                                         [(C.COIN_COUNT_SHORT_ID, E.DRY_UP_SHORT_CODE, heads, water, water, "discard_water_energy_cards")])
                        coins = [e for e in play.log if e["kind"] == "coin_flip"]
                        self.assertEqual(len(coins), heads + 1)  # コインを打ち切らない（H は丸めない）
                        self.assertEqual(coins, [e for e in strict.log if e["kind"] == "coin_flip"])
                        self.assertNotIn("halted", kinds(play))
                    audited(self, play)
                    self.assertEqual(v127_problems(play), [])

    def test_thought_wave_returns_all_and_ends_the_turn(self):
        for energy, heads in ((1, 2), (2, 5), (2, 2), (2, 1)):
            with self.subTest(energy=energy, heads=heads):
                base = V127.twm_board(energy)
                card = H.uids(base, 0, "hand", V127.TWM)[0]
                strict = V127.play_twm(base, heads)
                play = V127.play_twm(as_play(base), heads)
                if heads <= energy:
                    self.assertEqual([dict(e) for e in play.log], [dict(e) for e in strict.log])
                    continue
                self.assertIsNotNone(strict.halt.interruption)
                self.assertEqual(len(play.players[1].active.energy), 0)
                self.assertEqual(sum(len(e["cards"]) for e in play.log if e["kind"] == "trainer_return_energy"), energy)
                self.assertIn(card, play.players[0].discard)
                self.assertIsNone(play.trainer_in_use)
                self.assertEqual(play.current_player, 1)  # 番を終えた（ポケモンチェックのあと相手の番）
                self.assertEqual(applied(play)[0]["processed"], energy)
                audited(self, play)
                self.assertEqual(v127_problems(play), [])

    def test_esp_uses_the_last_sequence(self):
        from kyuura_engine import ResolveDecision, UseAttack
        from tests.helpers import with_coin_bits
        from tests.test_variable_coins_search_attachments_v0_113 import (
            esp_board,
            mon,
            provider_card,
        )

        state = as_play(esp_board(V127.MOLTRES, (V127.FIRE, V127.FIRE), opponent=mon(V127.CHANSEY, (V127.WATER, V127.WATER))))
        asked = apply_command(state, UseAttack(0, 0, card=provider_card(state, V127.MOLTRES)))
        flipped = V127.choose(asked, asked.players[1].active.pokemon_id, V127.run(3))
        self.assertEqual(applied(flipped), [])  # 最初の並び（H = 3 > N = 2）では決めない（やり直しを聞く）
        redone_short = apply_command(with_coin_bits(flipped, *V127.run(1)), ResolveDecision(0, flipped.decision.id, (1,)))
        self.assertEqual((applied(redone_short), redone_short.decision.min_choices), ([], 1))  # やり直して H = 1 ≤ N
        kept = apply_command(flipped, ResolveDecision(0, flipped.decision.id, ()))
        self.assertEqual([r["heads"] for r in applied(kept)], [3])
        again = apply_command(with_coin_bits(flipped, *V127.run(4)), ResolveDecision(0, flipped.decision.id, (1,)))
        self.assertEqual([r["heads"] for r in applied(again)], [4])  # 最後に確定した並び
        for done in (kept, again):
            self.assertIsNone(done.halt)
            self.assertEqual(len([e for e in done.log if e["kind"] == "discard_attached_energy"]), 2)
            audited(self, done)
            self.assertEqual(v127_problems(done), [])

    def test_checkpoint_returns_the_count(self):
        fields = {"code": E.DRY_UP_SHORT_CODE, "message": "m", "references": (), "source": "s", "player": 0, "target_owner": 1, "target": 1,
                  "element": "discard_water_energy_cards", "pending": ("p",)}
        play = as_play(V127.dry_board(2))
        self.assertEqual(check_quantity(play, required=1, available=2, **fields), 1)
        self.assertEqual(applied(play), [])
        self.assertEqual(check_quantity(play, required=5, available=2, **fields), 2)
        self.assertEqual(len(applied(play)), 1)
        other = {**fields, "code": "UNRESOLVED_X"}  # 規約の場面でないコード（ほかのカードへ広げない）
        from kyuura_engine.interruption import DeferredShortage

        with self.assertRaises(DeferredShortage):
            check_quantity(play, required=5, available=2, **other)

    def test_tw2_is_still_rejected(self):
        base = V127.twm_board(opponent_energy=[])
        card = H.uids(base, 0, "hand", V127.TWM)[0]
        for state in (base, as_play(base)):
            with self.assertRaises(UnsupportedError) as caught:
                apply_command(state, PlayTrainer(0, card))
            self.assertEqual(caught.exception.code, E.THOUGHT_WAVE_WITHOUT_TARGET_CODE)

    def test_interrupted_strict_state_is_not_resumed(self):
        halted = V127.dry_up(V127.dry_board(1), 3)
        self.assertIsNotNone(halted.halt.interruption)
        self.assertEqual(halted.conventions.key, C.DEFAULT_SET)
        with self.assertRaises(UnsupportedError):
            apply_command(halted, EndTurn(0))  # 途中停止の状態は、続行側の規約で再開しない（規約集合は対戦の中で変えない）

    def test_audit_finds_tampered_counts(self):
        play = V127.dry_up(as_play(V127.dry_board(1)), 3)
        tampered = copy.copy(play)
        log = [dict(e) for e in play.log]
        i = next(k for k, e in enumerate(log) if e["kind"] == "convention_applied")
        tampered.log = tuple(MappingProxyType({**e, "processed": 0} if k == i else e) for k, e in enumerate(log))
        self.assertTrue(v127_problems(tampered))
        removed = copy.copy(play)
        removed.log = tuple(MappingProxyType(e) for k, e in enumerate(log) if k != i)
        self.assertTrue(v127_problems(removed))


# ---------------------------------------------------------------- S2a-3: ポケモンチェック（constructed: v0.91・v0.48・v0.3b の盤面）


def both_asleep(current=0):
    return build_test_state([{"active": {"card": H.RATTATA, "sleep": True}, "bench": [H.RATTATA]},
                             {"active": {"card": H.RATTATA, "sleep": True}, "bench": [H.RATTATA]}], current_player=current, turn_number=3 + current)


class SideOrderTest(unittest.TestCase):
    def test_both_asleep_turn_player_first(self):
        for current in (0, 1):
            for coins in ((HD, TL), (TL, HD), (HD, HD), (TL, TL)):
                with self.subTest(current=current, coins=coins):
                    base = with_coin_results(both_asleep(current), *coins)
                    strict = apply_command(base, EndTurn(current))
                    self.assertEqual((strict.phase, strict.halt.code), (Phase.HALTED, SLEEP))
                    play = apply_command(as_play(base), EndTurn(current))
                    start = len(base.log)
                    record = applied(play, start)
                    self.assertEqual([(r["convention"], r["scene"], tuple(r["order"])) for r in record], [(C.SIDE_ORDER_ID, SLEEP, (current, 1 - current))])
                    checks = [e for e in play.log[start:] if e["kind"] == "sleep_check"]
                    self.assertEqual([(e["player"], e["result"]) for e in checks], [(current, coins[0].value), (1 - current, coins[1].value)])
                    seq = [k for k in kinds(play, start) if k in ("convention_applied", "coin_flip", "sleep_check")]
                    self.assertEqual(seq, ["convention_applied", "coin_flip", "sleep_check", "coin_flip", "sleep_check"])
                    for player, side in ((current, coins[0]), (1 - current, coins[1])):
                        self.assertEqual(play.players[player].active.conditions.asleep, side is TL)
                    self.assertIs(play.phase, Phase.MAIN)
                    audited(self, play)

    def test_one_side_is_unchanged(self):
        state = build_test_state([{"active": {"card": H.RATTATA, "sleep": True}}, {"active": {"card": H.RATTATA, "confusion": True}}])
        state = with_coin_results(state, TL)
        strict = apply_command(state, EndTurn(0))
        play = apply_command(as_play(state), EndTurn(0))
        self.assertEqual([dict(e) for e in play.log], [dict(e) for e in strict.log])

    def test_recovery_stop_is_checked_before_coins(self):
        """両方がねむりで、回復の組のどれかで MH1（ベトベトンが目を覚ますと［ガスのからだ］が消える）なら、続行側でもコインの前にその停止コードで止める。"""
        from tests import test_effective_pokemon_properties_v0_48 as V48

        state = V48.board(V48.mon(V48.MUK, sleep=True), V48.mon(V48.SABRINAS_GASTLY, (V48.P, V48.P), damage=50, sleep=True))
        strict = V48.end_turn(state)
        self.assertEqual(strict.halt.code, SLEEP)
        play = V48.end_turn(as_play(state))
        self.assertEqual((play.phase, play.halt.code), (Phase.HALTED, V48.MH1))
        self.assertEqual([e for e in play.log[len(state.log):] if e["kind"] in ("coin_flip", "convention_applied")], [])

    def test_both_char_markers_turn_player_first(self):
        mon = V91.mon
        for current in (0, 1):
            base = V91.board(mon(H.CHANSEY, markers=[V91.MARKER_CHAR]), opponent=mon(H.CHANSEY, markers=[V91.MARKER_CHAR]), current=current, turn=V91.TURN + current)
            for coins in ((TL, HD), (HD, TL)):
                with self.subTest(current=current, coins=coins):
                    strict = V91.end_turn(base, *coins, player=current)
                    self.assertEqual(strict.halt.code, KK1)
                    play = V91.end_turn(as_play(base), *coins, player=current)
                    start = len(base.log)
                    record = applied(play, start)
                    self.assertEqual([(r["scene"], tuple(r["order"])) for r in record], [(KK1, (current, 1 - current))])
                    checks = [(e["player"], e["result"]) for e in play.log[start:] if e["kind"] == "char_check"]
                    self.assertEqual(checks, [(current, coins[0].value), (1 - current, coins[1].value)])
                    damaged = [e["player"] for e in play.log[start:] if e["kind"] == "char_damage"]
                    self.assertEqual(damaged, [p for p, side in ((current, coins[0]), (1 - current, coins[1])) if side is TL])
                    audited(self, play)

    def test_char_prechecks_and_limit_stay(self):
        mon = V91.mon
        both_ko = V91.board(mon(H.RATTATA, poison=10, damage=20, markers=[V91.MARKER_CHAR]), opponent=mon(H.RATTATA, damage=20, markers=[V91.MARKER_CHAR]))
        play = V91.end_turn(as_play(both_ko))
        self.assertEqual((play.halt.code, kinds(play, len(both_ko.log)).count("coin_flip")), (V91.DOUBLE_KO, 0))  # 両方のきぜつの組はコインの前に止める
        berry = V91.board(mon(H.CHANSEY, markers=[V91.MARKER_CHAR]), opponent=mon(H.CHANSEY, trainers=[(V91.BERRY, None)], markers=[V91.MARKER_CHAR]))
        self.assertEqual(V91.end_turn(as_play(berry)).halt.code, V91.BY1)  # BY1 は対象外
        many = V91.board(mon(H.CHANSEY, markers=[V91.MARKER_CHAR]), bench=[mon(H.RATTATA, markers=[V91.MARKER_CHAR]) for _ in range(3)],
                         opponent=mon(H.CHANSEY, markers=[V91.MARKER_CHAR]), opponent_bench=[mon(H.RATTATA, markers=[V91.MARKER_CHAR]) for _ in range(3)])
        self.assertEqual(V91.end_turn(as_play(many)).halt.code, "UNSUPPORTED_POKEMON_CHECK_CHAR_COINS")  # 技術的上限は外さない


class KnockOutPointTest(unittest.TestCase):
    """v0.79・v0.80・v0.91 の PK1 の盤面（constructed）。"""

    @staticmethod
    def v79():
        from tests import test_shared_checks_pokemon_reuse_v0_79 as V79

        return V79

    def test_gas_source_stays_until_after_poison(self):
        """悪エネルギーで HP 以上になったかがくへんかガスのベトベトンは、2 のあとの判定まで場に残る（カブトのどくは、ガスがはたらく場の量。KA1 は当たらない）。"""
        V79 = self.v79()
        base = V79.board(active=V79.gas_muk(energy=[V79.DK], damage=60), opponent_active=V79.kabuto(poison=10))
        strict = V79.end(base)
        self.assertEqual(strict.halt.code, PK1)
        play = V79.end(as_play(base))
        start = len(base.log)
        muk_id, kabuto_id = base.players[0].active.pokemon_id, base.players[1].active.pokemon_id
        self.assertEqual([(r["convention"], tuple(r["pokemon_ids"])) for r in applied(play, start)], [(C.KO_POINT_ID, (muk_id,))])
        seq = [(e["kind"], e.get("pokemon_id")) for e in play.log[start:] if e["kind"] in ("convention_applied", "darkness_energy_damage", "poison_damage", "knock_out")]
        self.assertEqual([k for k, _ in seq], ["convention_applied", "darkness_energy_damage", "poison_damage", "knock_out"])
        poison = next(e for e in play.log[start:] if e["kind"] == "poison_damage")
        self.assertEqual((poison["pokemon_id"], poison["amount"]), (kabuto_id, 10))
        self.assertIs(play.phase, Phase.TAKE_PRIZE)
        audited(self, play)

    def test_transform_revert_keeps_a_stop_before_damage(self):
        """v0.79 の盤面: 写しているバトル場のポケモンが 2 のあとにきぜつすると、メタモンの姿がもどって HP がダメージ以下になる（TK1）。そのきぜつの処理で止まるので、続行側でも規約を
        当てずに、ダメージの前に TK1 で止める（保守的な制限。今は［へんしん］がきぜつの判定の時点を決めない）。"""
        V79 = self.v79()
        base = V79.board(active=V79.mon(H.HITMONCHAN, (V79.DK,), damage=60), opponent_active=V79.mon(H.DITTO, damage=50, poison=10))
        self.assertEqual(V79.end(base).halt.code, PK1)
        play = V79.end(as_play(base))
        self.assertEqual((play.phase, play.halt.code), (Phase.HALTED, E.TRANSFORM_REVERT_KO_CODE))
        self.assertIn("PC-CHECK-KO-POINT", play.halt.message)
        self.assertEqual([e for e in play.log[len(base.log):] if e["kind"] in ("darkness_energy_damage", "poison_damage", "convention_applied")], [])
        audited(self, play)

    def test_controls_do_not_apply_the_rule(self):
        V79 = self.v79()
        for base in (V79.board(active=V79.gas_muk(energy=[V79.DK], damage=60), opponent_active=V79.kabuto()),
                     V79.board(active=V79.mon(H.HITMONCHAN, damage=60), opponent_active=V79.mon(H.HITMONCHAN, poison=10, damage=60))):
            strict, play = V79.end(base), V79.end(as_play(base))
            self.assertEqual([dict(e) for e in play.log], [dict(e) for e in strict.log])
            self.assertEqual(applied(play), [])

    def test_later_scram_restoration_keeps_the_stop(self):
        """v0.91 の盤面: 場に残る読み方では、きぜつの処理でベトベトンが場をはなれ、残りHP「10」で消えていた［ずらかる］の力がもどる（SC2）。その停止はダメージのあとに起こるので、
        続行側では規約を当てずに、コインとダメージの前に SC2 の停止コードで止める（保守的な制限。くろこげマーカーのコインの前の確かめが、すべての結果で確かめる）。"""
        from tests.test_type_energy_colors_v0_88 import muk

        gas = muk()
        gas.update(damage=60, markers=[V91.MARKER_CHAR])
        primeape = V91.mon(H.BROCKS_PRIMEAPE, played_turn=2, evolved_from="PMCG5-045", evolved_turn=4, damage=50, poison=10)
        base = V91.board(V91.mon(H.CHANSEY), opponent=primeape, opponent_bench=(gas,))
        for state, code in ((base, PK1), (as_play(base), E.SCRAM_RESTORED_CODE)):
            done = V91.end_turn(state)
            self.assertEqual((done.phase, done.halt.code), (Phase.HALTED, code))
            self.assertEqual([e for e in done.log[len(base.log):] if e["kind"] in ("coin_flip", "convention_applied", "char_damage", "poison_damage")], [])
            audited(self, done)
        self.assertIn("PC-CHECK-KO-POINT", V91.end_turn(as_play(base)).halt.message)

    def test_side_order_and_ko_point_together(self):
        """両方の場のくろこげマーカー（両側のコイン）と、1 のあいだに HP 以上（きぜつ判定）。続行側では両方の規約が当たる。両側のコインの規約だけの開発用の集合（試験の登録表）
        では、コインの前の確かめで PK1 の組が止める理由になり、コインの前に止まる。"""
        from tests.test_conventions_v0_142 import make_registry

        V79 = self.v79()
        base = V79.board(active=V79.gas_muk(damage=60, markers=[V91.MARKER_CHAR]), opponent_active=V79.kabuto(poison=10),
                         opponent_bench=(V79.mon(H.CHANSEY, markers=[V91.MARKER_CHAR]),))
        self.assertEqual(V79.end(base).halt.code, KK1)
        play = V79.end(with_coin_results(as_play(base), TL, HD))
        self.assertEqual([r["convention"] for r in applied(play, len(base.log))], [C.SIDE_ORDER_ID, C.KO_POINT_ID])
        audited(self, play)
        heads = V79.end(with_coin_results(as_play(base), HD, HD))
        self.assertEqual([r["convention"] for r in applied(heads, len(base.log))], [C.SIDE_ORDER_ID])  # 「おもて」なら HP 以上にならない
        partial = C.ConventionSet("CS-TEST-SIDE", 1, C.USAGE_DEVELOPMENT, C.SETS[C.DEFAULT_SET].members + ((C.SIDE_ORDER_ID, 1),))
        registry = make_registry(sets=(partial,), implemented=C.IMPLEMENTED_CONTINUATIONS)
        with mock.patch.object(C, "DEFAULT_REGISTRY", registry), mock.patch.object(C, "_IDENTITY_CACHE", {}):
            state = base.clone()
            state.conventions = C.identity_of(partial, registry)
            stopped = V79.end(with_coin_results(state, TL, HD))
        self.assertEqual(stopped.halt.code, PK1)
        self.assertEqual([e for e in stopped.log[len(base.log):] if e["kind"] in ("coin_flip", "convention_applied")], [])

    def test_double_knock_out_still_halts(self):
        mon = V91.mon
        both = V91.board(mon(H.RATTATA, poison=10, damage=20), opponent=mon(H.RATTATA, damage=20, markers=[V91.MARKER_CHAR]))
        for state in (both, as_play(both)):
            done = V91.end_turn(state)
            self.assertEqual(done.halt.code, V91.DOUBLE_KO)
            self.assertEqual(applied(done, len(both.log)), [])


# ---------------------------------------------------------------- 保存・観測・ログ（constructed と legal）


class PersistenceTest(unittest.TestCase):
    def test_save_restore_and_formats(self):
        play = V127.dry_up(as_play(V127.dry_board(1)), 3)
        for copied in (play.clone(), copy.deepcopy(play), pickle.loads(pickle.dumps(play))):
            self.assertEqual(copied.conventions, play_identity())
        data = state_to_dict(play, format_version=LATEST)
        self.assertEqual(data["convention_set"]["id"], C.S2A_SET_ID)
        with self.assertRaises(ValueError):
            state_to_dict(play, format_version=34)  # 形式 34 までは続行側の集合を表せない（黙って厳密側にしない）
        seed = MulliganCompensationTest.by_shape[(1, 1)] if hasattr(MulliganCompensationTest, "by_shape") else None
        if seed is None:
            MulliganCompensationTest.setUpClass()
            seed = MulliganCompensationTest.by_shape[(1, 1)]
        state = new_game(FEW_BASICS, FEW_BASICS, seed, conventions=PLAY)
        self.assertEqual(pickle.loads(pickle.dumps(state)).conventions, play_identity())

    def test_records_are_public(self):
        play = V91.end_turn(as_play(both_asleep()), TL, TL)
        self.assertEqual(len(applied(play)), 1)
        for viewer in (0, 1, None):
            events = [e for e in visible_log(play, viewer) if e["kind"] == "convention_applied"]
            self.assertEqual(len(events), 1)
            self.assertEqual(set(events[0]) - {"kind", "turn", "convention", "version", "scene", "code"}, {"order"})
        self.assertLessEqual({k for e in applied(play) for k in e} - {"kind", "turn", "convention", "version", "scene", "code"}, C.APPLIED_FIELDS)

    def test_rejected_and_preflight_leave_no_record(self):
        """拒否した操作・先読み（ドライアップの宣言の前の確かめ）は、規約を当てた記録を残さない（記録は受け付けた処理の状態だけ）。"""
        base = as_play(V127.dry_board(0))
        asked = V127.declare(base)
        self.assertEqual(applied(asked), [])  # 宣言（先読みで H > N の枝を通る）
        before = snapshot(asked)
        with self.assertRaises((IllegalActionError, UnsupportedError)):
            apply_command(asked, EndTurn(1))
        self.assertEqual(snapshot(asked), before)

    def test_prize_retaken_after_deck_top_swap_is_not_flagged(self):
        """legal（続行側の計測 v0.47 F47-H47 seed 2）: 化石の手札の切り直しのあとの対戦で、取ったサイドのカードが手札から山札にもどり、山札の上とサイドを入れかえる特殊能力で
        サイドに置かれて、もう一度取られた。監査の「同じサイドのカードを 2 回取った」の誤検出（エンジンの誤りではない）を直した回帰テスト。入れかえのない 2 回目の取得は見つける。"""
        from tests.log_audit import _retaken_without_return
        from tools import existing_effect_games as G
        from tools.convention_choice import restore_conventions, use_conventions

        self.addCleanup(restore_conventions)
        use_conventions(PLAY)
        result = G.play(("H47", "F47"), 2, keep_state=True)
        state = result["state"]
        taken = [e["card"] for e in state.log if e["kind"] == "take_prize"]
        self.assertGreater(len(taken), len(set(taken)))
        self.assertEqual(result["audit"], {})
        log = [dict(e) for e in state.log]
        without_swap = [e for e in log if e["kind"] != "swap_prize_with_deck_top"]
        self.assertTrue(_retaken_without_return(without_swap))

    def test_audit_detects_missing_or_misplaced_records(self):
        play = V91.end_turn(as_play(both_asleep()), TL, TL)
        log = [dict(e) for e in play.log]
        i = next(k for k, e in enumerate(log) if e["kind"] == "convention_applied")
        for change in ({"order": (1, 0)}, {"convention": "PC-UNKNOWN"}, {"hand": [1]}, {"scene": KK1}):
            tampered = copy.copy(play)
            tampered.log = tuple(MappingProxyType({**e, **change} if k == i else e) for k, e in enumerate(log))
            self.assertTrue(s2a_problems(tampered), change)
        removed = copy.copy(play)
        removed.log = tuple(MappingProxyType(e) for k, e in enumerate(log) if k != i)
        self.assertTrue(s2a_problems(removed))
        strict_like = copy.copy(play)
        strict_like.conventions = C.default_identity()  # 状態の集合にない規約の記録
        self.assertTrue(s2a_problems(strict_like))


if __name__ == "__main__":
    unittest.main()
