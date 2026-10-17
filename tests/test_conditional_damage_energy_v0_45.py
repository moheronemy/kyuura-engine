"""v0.45: 条件つきのダメージ・エネルギーの移動とトラッシュ・受けたダメージを返す効果などのポケモン 15 枚と、GV1 の停止コード
（docs/conditional-damage-energy-v0.45.md）。

第1弾のゴースト（PMCG1-047。v0.9 の過去の原典照合の記録。p.160 の最新の説明）・カスミのタッツー（PMCG5-024）・カスミのジュゴン（PMCG5-031）・キョウのアーボ
（PMCG6-002）・キョウのアーボック（PMCG6-019）・キョウのベトベター（PMCG6-007）・わるいカメックス（PMCG4-024）・わるいレアコイル（PMCG4-030）・カツラのリザードン
（PMCG6-032）・R団のサンダー（PMCG6-042）・イワーク（PMCG1-054）・ラッタ（PMCG1-062）・R団のエビワラー（PMCG5-054）・タケシのイシツブテ（PMCG5-047）・サカキのニャース
（PMCG6-068）。第1弾のゴースト以外は kyuura データの採用（処理に使う文面は kyuura の印刷の文面。クロスカウンターだけ kyuura の最新の説明 LD-PMCG5-054-ATK0。採用した
データのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合。ガイドブックは読んでいない。

根拠にした既存の記録: p.309（ワザの手順。対象のない内容は無視する。GR-2000-P309-ATTACK-PROCEDURE）・p.321（ダメージの計算の段階。GR-2000-P321-DAMAGE-ORDER。
8 段階の例が「かたくなる」）・p.322・p.323（特殊状態・持続する効果・ワザの失敗）・RUL-ENERGY-DISCARD-ATTACKS（炎エネルギーをトラッシュするワザはワザの効果）・
CR-TRANSPARENCY-ENERGY-BOMB（つける相手がとうめいで受けなければトラッシュ）・CR-SHELL-ATTACK-TIMING・CR-SHELL-ATTACK-ATTACKER-PLUSPOWER（返すダメージの時点と
受けたダメージ）と、エンジンの v0.4b（ダメージを受けない状態）・v0.13（こうらがえし。W24/S37）・v0.31（たいでん）・v0.32（山札からベンチ）・v0.34（バリアーの
コイン）・v0.36（手順 4 のコイン・AC6・AC13）・v0.42（つきのちから）・v0.44（サカキの許可・GV1）の記録。

新しい停止コードは 2 つ: GV1（``UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK``。v0.44 はコードのない問いだったが、つきのちからで起こり内部エラーになっていた）と
AC13（``UNRESOLVED_MULTIPLE_ATTACK_CHECKS``。v0.36 は対応カードで起こらず RuntimeError。「スミをかける」の期限のない効果で起こる）。
"""

from __future__ import annotations

import copy
import pathlib
import pickle
import re
import unittest

from kyuura_engine import (
    EndTurn,
    EngineError,
    IllegalActionError,
    PlayBasicToBench,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UnsupportedError,
    UseAttack,
    apply_command,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, read_extract
from kyuura_engine.damage import ZERO_IF_BELOW, DamageModifier
from kyuura_engine.decisions import (
    ATTACH_FROM_DISCARD,
    BENCH_FROM_DECK,
    DISCARD_ENERGY,
    FORCED_SWITCH,
    MOVE_OPPONENT_ENERGY,
    SELECT_ATTACK,
    SELECT_POKEMON,
)
from kyuura_engine.resolution import PREFLIGHT_MODES, contract, programs, v013_checks
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.state import (
    RETALIATION_RECEIVED,
    RETALIATION_RECEIVED_SCALED_KIND,
    AttackCoinCheck,
    PreventDamage,
    Retaliation,
    ZeroDamageBelow,
)
from scripts import check_card_sources as cs
from tests.helpers import (
    ATTACK_TYPES_SINCE_V0_17,
    BASE_GASTLY,
    BASE_HAUNTER,
    BLAINES_CHARIZARD,
    BLAINES_CHARMANDER,
    BLAINES_CHARMELEON,
    BROCKS_GEODUDE,
    BROCKS_GEODUDE_40,
    BROCKS_ONIX,
    BROCKS_ZUBAT,
    CHANSEY,
    CLEFAIRY,
    DARK_BLASTOISE,
    DARK_MAGNETON,
    DARK_WARTORTLE,
    ERIKAS_CLEFAIRY,
    FIGHTING,
    FIRE,
    GASTLY,
    GIOVANNI,
    GIOVANNIS_GYARADOS,
    GIOVANNIS_MAGIKARP,
    GIOVANNIS_MEOWTH,
    GIOVANNIS_MEOWTH_40,
    GRASS,
    HAUNTER,
    HITMONCHAN,
    HORSEA,
    KOGAS_ARBOK,
    KOGAS_EKANS,
    KOGAS_GRIMER,
    LIGHTNING,
    MACHOP,
    MAGNEMITE,
    MEWTWO,
    MISTYS_DEWGONG,
    MISTYS_HORSEA,
    MISTYS_HORSEA_50,
    MISTYS_SEEL,
    ONIX,
    PLUSPOWER,
    POTION,
    PSYCHIC,
    RATICATE,
    RATTATA,
    ROCKET_SQUIRTLE,
    ROCKETS_HITMONCHAN,
    ROCKETS_ZAPDOS,
    SWITCH,
    V0_45_ADOPTED,
    V0_45_POKEMON,
    WATER,
    ZAPDOS,
    H,
    T,
    apply_kernel,
    build_test_state,
    no_base_haunter_pool,
    with_coin_results,
)
from tests.log_audit import serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "conditional-damage-energy-v0.45.md"
TURN = 7
F, W, G, P, R, L = FIGHTING, WATER, GRASS, PSYCHIC, FIRE, LIGHTNING
GV1 = "UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK"
AC13 = "UNRESOLVED_MULTIPLE_ATTACK_CHECKS"
AC6 = "UNRESOLVED_ATTACK_CHECK_CONFUSION"
HC3 = "UNRESOLVED_PREVENTED_EFFECT_COIN"
T19B = "UNRESOLVED_EVADED_EFFECT_COIN"
W24 = "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT"

# 登録の実装の型と値（カード id, ワザの位置）
EXPECTED = {
    (BASE_HAUNTER, 0): (E.PutToSleep, {}),
    (BASE_HAUNTER, 1): (E.DamageFailUnlessOpponentStatus, {"condition": "sleep"}),
    (MISTYS_HORSEA_50, 0): (E.DamageThenLastingAttackCoinCheckOnHeads, {}),
    (MISTYS_DEWGONG, 0): (E.DamageMultipliedAgainstType, {"pokemon_type": EnergyType.FIGHTING, "factor": 2}),
    (MISTYS_DEWGONG, 1): (E.DamageAndSelfDamage, {"self_damage": 20}),
    (KOGAS_EKANS, 0): (E.DamageThenPoisonAndConfuseOnAllHeads, {"coins": 2}),
    (KOGAS_ARBOK, 0): (E.SelfStatusWithoutDamage, {"condition": "poison"}),
    (KOGAS_ARBOK, 1): (E.DamageIfSelfStatusThenOpponentStatus, {"condition": "poison", "amount": 40}),
    (KOGAS_GRIMER, 0): (E.CoinSwitchOpponentThenStatus, {"condition": "poison"}),
    (KOGAS_GRIMER, 1): (E.DamageOnly, {}),
    (DARK_BLASTOISE, 0): (E.ExtraEnergyDamage, {"energy_type": EnergyType.WATER, "per_energy": 20, "max_extra": 2}),
    (DARK_BLASTOISE, 1): (E.DamageAndSelfDamageThenPreventDamageOnHeads, {"self_damage": 10}),
    (DARK_MAGNETON, 0): (E.DamageIgnoringWeaknessResistance, {}),
    (DARK_MAGNETON, 1): (E.DamageThenMoveOpponentEnergyToBench, {}),
    (BLAINES_CHARIZARD, 0): (E.DiscardExcessEnergyForDamage, {"energy_type": EnergyType.FIRE, "per_energy": 20}),
    (BLAINES_CHARIZARD, 1): (E.CoinChooseOpponentPokemonDamage, {"damage": 40}),
    (ROCKETS_ZAPDOS, 0): (E.DamageThenAttachEnergyFromDiscardToSelf, {"energy_type": EnergyType.LIGHTNING}),
    (ROCKETS_ZAPDOS, 1): (E.DamageAndSelfDamagePerAttachedEnergyCard, {"energy_type": EnergyType.LIGHTNING, "per_card": 10}),
    (ONIX, 0): (E.DamageOnly, {}),
    (ONIX, 1): (E.ZeroDamageBelowNextTurn, {"threshold": 40}),
    (RATICATE, 0): (E.DamageOnly, {}),
    (RATICATE, 1): (E.HalfRemainingHpDamage, {}),
    (ROCKETS_HITMONCHAN, 0): (E.ReturnReceivedDamageOnHeads, {"multiplier": 2}),
    (ROCKETS_HITMONCHAN, 1): (E.DamageOnly, {}),
    (BROCKS_GEODUDE_40, 0): (E.PutOwnerBasicFromDeckOntoBenchOnHeads, {"owner": "タケシ"}),
    (BROCKS_GEODUDE_40, 1): (E.DamageIgnoringResistance, {}),
    (GIOVANNIS_MEOWTH_40, 0): (E.CoinOpponentDeckTopDiscardTrainerElseHand, {}),
    (GIOVANNIS_MEOWTH_40, 1): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 20}),
}
# v0.45 で加えた実装の型（tests/helpers.py の ATTACK_TYPES_SINCE_V0_17 の最後の 18）
NEW_TYPES = (
    E.DamageFailUnlessOpponentStatus, E.DamageThenLastingAttackCoinCheckOnHeads, E.DamageMultipliedAgainstType, E.DamageThenPoisonAndConfuseOnAllHeads,
    E.SelfStatusWithoutDamage, E.DamageIfSelfStatusThenOpponentStatus, E.CoinSwitchOpponentThenStatus, E.DamageAndSelfDamageThenPreventDamageOnHeads,
    E.DamageThenMoveOpponentEnergyToBench, E.DiscardExcessEnergyForDamage, E.DamageThenAttachEnergyFromDiscardToSelf,
    E.DamageAndSelfDamagePerAttachedEnergyCard, E.ZeroDamageBelowNextTurn, E.HalfRemainingHpDamage, E.ReturnReceivedDamageOnHeads,
    E.PutOwnerBasicFromDeckOntoBenchOnHeads, E.DamageIgnoringResistance, E.CoinOpponentDeckTopDiscardTrainerElseHand,
)
# pcg-search.com の対象の版（サイトの一覧の番号）
EDITIONS = {BASE_HAUNTER: "047/096", MISTYS_HORSEA_50: "030/096", MISTYS_DEWGONG: "028/096", KOGAS_EKANS: "008/098", KOGAS_ARBOK: "009/098",
            KOGAS_GRIMER: "012/098", DARK_BLASTOISE: "020/065", DARK_MAGNETON: "027/065", BLAINES_CHARIZARD: "027/098", ROCKETS_ZAPDOS: "041/098",
            ONIX: "057/096", RATICATE: "062/096", ROCKETS_HITMONCHAN: "043/096", BROCKS_GEODUDE_40: "049/096", GIOVANNIS_MEOWTH_40: "071/098"}
# 進化しているポケモンの下のカード（build_test_state の "evolved_from"）
BELOW = {BASE_HAUNTER: BASE_GASTLY, MISTYS_DEWGONG: MISTYS_SEEL, KOGAS_ARBOK: KOGAS_EKANS, DARK_BLASTOISE: [ROCKET_SQUIRTLE, DARK_WARTORTLE],
         DARK_MAGNETON: MAGNEMITE, BLAINES_CHARIZARD: [BLAINES_CHARMANDER, BLAINES_CHARMELEON], RATICATE: RATTATA, HAUNTER: GASTLY,
         GIOVANNIS_GYARADOS: GIOVANNIS_MAGIKARP}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def bench_spec(b):
    return mon(b) if isinstance(b, str) and b in BELOW else b


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), deck=None, hand=(), discard=(), opponent_deck=None,
          opponent_hand=(), turn=TURN):
    me = {"active": active, "bench": [bench_spec(b) for b in bench], "hand": list(hand), "discard": list(discard)}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent or mon(HITMONCHAN, (F, F)), "bench": [bench_spec(b) for b in opponent_bench], "hand": list(opponent_hand)}
    if opponent_deck is not None:
        them["deck"] = list(opponent_deck)
    return build_test_state([me, them], turn_number=turn)


def full(state):
    return state_to_dict(state, format_version=11)


def snapshot(state):
    return full(state), [dict(e) for e in state.log], repr(state.rng.getstate())


def audited(test, state):
    """不変条件と書き出しの監査（盤面を直接作ったテスト。ログの監査は正式な対戦のテストで確かめる）。"""
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    return state


def events(state, since, kind=None):
    return [dict(e) for e in state.log[since:] if kind is None or e["kind"] == kind]


def kinds(state, since):
    return [e["kind"] for e in state.log[since:]]


def answer(state, choices, *, mode="derived"):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)), preflight=mode)


def attack(state, index, *sides, player=0, answers=(), mode="derived"):
    state = apply_kernel(with_coin_results(state, *sides) if sides else state, UseAttack(player, index), preflight=mode)
    for a in answers:
        state = answer(state, a(state.decision) if callable(a) else a, mode=mode)
    return state


def end_turn(state):
    state = apply_kernel(state, EndTurn(state.current_player))
    if state.decision is not None:
        raise AssertionError(f"番の終わりに決定がある: {state.decision}")
    return state


def pid_of(state, player, card, nth=0):
    return [p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card][nth]


def find(state, player, card, nth=0):
    return state.find_pokemon(pid_of(state, player, card, nth))[1]


def card_of(state, player, card, zone="hand", nth=0):
    return [u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card][nth]


def cards_in(state, player, zone):
    return [state.cards[u].card_id for u in getattr(state.players[player], zone)]


def assert_stops(test, state, command, code, *, exception=UnsupportedError):
    """どの先読みの方法でも ``code`` で拒否し、状態・乱数・ログが変わらない。"""
    before = snapshot(state)
    for mode in PREFLIGHT_MODES:
        with test.subTest(mode=mode), test.assertRaises(exception) as raised:
            apply_kernel(state, command, preflight=mode)
        test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def assert_rejected(test, state, command, code, exception=EngineError):
    before = snapshot(state)
    with test.assertRaises(exception) as raised:
        apply_kernel(state, command)
    test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def with_barrier(attacker, *, attacker_bench=(RATTATA,), opponent_bench=(RATTATA,)):
    """相手（プレイヤー 0）の対戦ポケモンを「ワザをうけない」状態（ミュウツーの「バリアー」）にしてから、プレイヤー 1 の番にする（v0.34 と同じ盤面）。
    ``attacker`` はバリアーのあとにワザを使うプレイヤー 1 のポケモン。"""
    state = build_test_state([
        {"active": mon(MEWTWO, (P, P, P)), "bench": [bench_spec(b) for b in opponent_bench]},
        {"active": attacker, "bench": [bench_spec(b) for b in attacker_bench]},
    ], turn_number=TURN)
    state = apply_kernel(state, UseAttack(0, 1))
    return answer(state, (state.decision.options[0],)) if state.decision is not None else state


def with_haunter_defender(attacker, *, attacker_bench=(RATTATA,)):
    """相手（プレイヤー 1）の対戦ポケモンが、化石の秘密のゴースト（「とうめい」）の盤面。"""
    return board(attacker, mon(HAUNTER, (P,)), bench=attacker_bench)


# ---------------------------------------------------------------- 登録・写し・記録


class CardDataTest(unittest.TestCase):
    """15 枚の写し・登録・記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_fifteen_requested_cards(self):
        """写しの組 pool_v0_45 は依頼の 15 枚（並び）。どれも対応で、どのワザも登録した（保留なし）。第1弾のゴーストは v0.44 まで参照カードだった。"""
        extract = read_extract()
        self.assertEqual(extract["pool_v0_45"], list(V0_45_POKEMON))
        self.assertNotIn(BASE_HAUNTER, extract["reference_only"])
        names = {BASE_HAUNTER: "ゴースト", MISTYS_HORSEA_50: "カスミのタッツー", MISTYS_DEWGONG: "カスミのジュゴン", KOGAS_EKANS: "キョウのアーボ",
                 KOGAS_ARBOK: "キョウのアーボック", KOGAS_GRIMER: "キョウのベトベター", DARK_BLASTOISE: "わるいカメックス", DARK_MAGNETON: "わるいレアコイル",
                 BLAINES_CHARIZARD: "カツラのリザードン", ROCKETS_ZAPDOS: "R団のサンダー", ONIX: "イワーク", RATICATE: "ラッタ",
                 ROCKETS_HITMONCHAN: "R団のエビワラー", BROCKS_GEODUDE_40: "タケシのイシツブテ", GIOVANNIS_MEOWTH_40: "サカキのニャース"}
        for card in V0_45_POKEMON:
            with self.subTest(card=card):
                definition = self.pool.get(card)
                self.assertEqual(definition.name_ja, names[card])
                self.assertTrue(self.pool.is_playable(card))
                self.assertEqual(definition.powers, ())
                self.assertTrue(all(a.supported for a in definition.attacks))
        # 同じ名前の別のカードと取りちがえない（カード id が違い、ワザが違う）
        for ours, other in ((BASE_HAUNTER, HAUNTER), (MISTYS_HORSEA_50, MISTYS_HORSEA), (BROCKS_GEODUDE_40, BROCKS_GEODUDE),
                            (GIOVANNIS_MEOWTH_40, GIOVANNIS_MEOWTH)):
            with self.subTest(pair=(ours, other)):
                self.assertEqual(self.pool.get(ours).name_ja, self.pool.get(other).name_ja)
                self.assertNotEqual([a.name_ja for a in self.pool.get(ours).attacks], [a.name_ja for a in self.pool.get(other).attacks])

    def test_without_the_registrations_the_base_haunter_is_not_supported(self):
        """登録のないワザを持つカードは対応にならない（第1弾のゴーストは v0.44 までそうだった。登録を除いた登録表で確かめる）。"""
        pool = no_base_haunter_pool()
        self.assertFalse(pool.is_playable(BASE_HAUNTER))
        self.assertTrue(all(not a.supported for a in pool.get(BASE_HAUNTER).attacks))

    def test_evolution_names(self):
        """進化カードは「○○から進化」の名前の完全一致で進化元が決まる（収録の弾で制限しない）。"""
        expected = {BASE_HAUNTER: "ゴース", MISTYS_DEWGONG: "カスミのパウワウ", KOGAS_ARBOK: "キョウのアーボ", DARK_BLASTOISE: "わるいカメール",
                    DARK_MAGNETON: "コイル", BLAINES_CHARIZARD: "カツラのリザード", RATICATE: "コラッタ"}
        for card in V0_45_POKEMON:
            with self.subTest(card=card):
                definition = self.pool.get(card)
                self.assertEqual(definition.evolves_from, expected.get(card))
                self.assertEqual(definition.is_basic_pokemon, card not in expected)
        # ゴースト（第1弾）はどちらのゴース（第1弾・化石の秘密）からも進化できる
        self.assertEqual({self.pool.get(c).name_ja for c in (BASE_GASTLY, GASTLY)}, {"ゴース"})

    def test_every_attack_is_registered_with_the_expected_implementation(self):
        for card in V0_45_POKEMON:
            for index, attack_def in enumerate(self.pool.get(card).attacks):
                with self.subTest(card=card, index=index):
                    entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
                    kind, values = EXPECTED[(card, index)]
                    self.assertIs(type(entry.effect), kind)
                    self.assertEqual(entry.effect, kind(**values))
                    self.assertEqual(entry.name_ja, attack_def.name_ja)
                    self.assertEqual(entry.text_ja, attack_def.text_ja)
                    self.assertEqual(entry.effect.check(attack_def), [])
        self.assertEqual(len([k for k in E.DEFAULT_EFFECTS.attack_keys() if k.card_id in V0_45_POKEMON]), len(EXPECTED))

    def test_processing_texts(self):
        """処理に使う文面: 第1弾のゴーストは v0.9 の照合の記録の最新の説明（p.160。ゆめくいは kyuura の LD-PMCG1-047-ATK1 と同じ文）、クロスカウンターは kyuura の
        最新の説明（LD-PMCG5-054-ATK0）、ほかは kyuura の印刷の文面（写しの説明文と同じ）。"""
        dream = E.DEFAULT_EFFECTS.attack_entry(BASE_HAUNTER, 1)
        self.assertEqual((dream.play_text_ja, dream.source), ("相手が「ねむり」状態でないとき、このワザは失敗する。", "P43 p.160"))
        self.assertNotEqual(dream.play_text_ja, dream.text_ja)  # 印刷の文面（「ダメージをあたえる」条件）は照合だけに使う
        self.assertEqual(E.DEFAULT_EFFECTS.attack_entry(ROCKETS_HITMONCHAN, 0).source, "LD-PMCG5-054-ATK0")
        for (card, index) in EXPECTED:
            entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
            if card in V0_45_ADOPTED and entry.text_ja is not None and (card, index) != (ROCKETS_HITMONCHAN, 0):
                with self.subTest(card=card, index=index):
                    self.assertEqual((entry.play_text_ja, entry.source), (entry.text_ja, cs.PRINTED_TEXT_SOURCE))

    def test_text_checks_reject_other_wording(self):
        """型の ``check`` は登録したワザの文面と完全に同じものだけを受け付ける（v0.37 の約束）。1 文字変えた文面・ダメージの目安の形の違いは拒否する。"""
        for (card, index), (kind, _) in EXPECTED.items():
            if kind not in NEW_TYPES:
                continue
            attack_def = self.pool.get(card).attacks[index]
            effect = E.DEFAULT_EFFECTS.attack_entry(card, index).effect
            with self.subTest(card=card, index=index):
                changed = attack_def.__class__(**{**attack_def.__dict__, "text_ja": attack_def.text_ja + "。"})
                self.assertTrue(effect.check(changed))

    def test_new_types_are_kernel_programs_outside_the_v013_contract(self):
        """v0.45 の型は解決の基盤の要素の並びで処理し（v0.13 の約束のアダプタでない）、v0.13 の止める関数で確かめる型（VERIFIED）に入れない。"""
        self.assertEqual(ATTACK_TYPES_SINCE_V0_17[-len(NEW_TYPES):], NEW_TYPES)
        for kind in NEW_TYPES:
            with self.subTest(kind=kind.__name__):
                self.assertNotIn(kind, v013_checks.VERIFIED)
                self.assertIn(kind, programs.BUILDERS)
                effect = next(E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect for k in E.DEFAULT_EFFECTS.attack_keys()
                              if type(E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect) is kind)
                self.assertFalse(contract.is_contract(contract.program_for(effect)))
                self.assertNotIn("resolve", vars(kind))

    def test_records_and_external_checks(self):
        """採用の記録は 14 枚（kyuura データ。写しの元のコミット）、第1弾のゴーストは v0.9 の過去の原典照合の記録で登録し、card_sources.json には pcg-search.com の
        照合だけを書く。照合は同じ版のページ（一覧の番号）で、違いは処理に影響しない。"""
        sources = cs.load_sources()
        self.assertEqual(cs.problems(), [])
        for card in V0_45_POKEMON:
            record = sources["cards"][card]
            with self.subTest(card=card):
                self.assertEqual(record["basis"], cs.GUIDEBOOK_RECORD if card == BASE_HAUNTER else cs.KYUURA_DATA)
                [check] = record["external_checks"]
                self.assertEqual((check["site"], check["edition"]["list_number"], check["checked_on"]), ("pcg-search.com", EDITIONS[card], "2026-10-16"))
                self.assertFalse(any(d["affects_behavior"] for d in check["differences"]))
                for key in ("page", "pdf_page", "latest_description_ja", "card_image_text_ja"):
                    self.assertNotIn(key, record)

    def test_no_card_specific_branch_in_the_engine(self):
        """engine.py・resolution/ にカード id での分岐を加えていない。"""
        sources = [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]
        for path in sources:
            text = path.read_text(encoding="utf-8")
            for card in V0_45_POKEMON:
                with self.subTest(path=path.name, card=card):
                    self.assertNotIn(card, text)

    def test_new_and_reused_questions(self):
        """新しい停止コードは GV1（v0.44 のコードのない問いに付けた）と AC13（v0.36 の起こらない RuntimeError）。ほかは既存の問い・コード。"""
        self.assertEqual((QUESTIONS["evolution_permission_from_deck"].code, QUESTIONS["evolution_permission_from_deck"].rulings), (GV1, ("GV1",)))
        self.assertEqual((QUESTIONS["multiple_attack_checks"].code, QUESTIONS["multiple_attack_checks"].rulings), (AC13, ("AC13",)))
        text = DOC.read_text(encoding="utf-8")
        for word in (GV1, AC13, "GV1", "AC13", *V0_45_POKEMON):
            self.assertIn(word, text)


# ---------------------------------------------------------------- GV1


def gv1_board(*, magikarp_played_turn=TURN, giovanni=True, deck=(GIOVANNIS_GYARADOS, RATTATA, RATTATA)):
    """プレイヤー 0 のエリカのピッピ（つきのちから）がバトル場、ベンチにサカキのコイキング（``magikarp_played_turn`` に場に出した）、山札にサカキのギャラドス。"""
    return build_test_state([
        {"active": {"card": ERIKAS_CLEFAIRY, "energy": [F]}, "bench": [{"card": GIOVANNIS_MAGIKARP, "played_turn": magikarp_played_turn}, RATTATA],
         "hand": [GIOVANNI] if giovanni else [], "deck": list(deck)},
        {"active": mon(HITMONCHAN, (F, F)), "bench": [RATTATA]},
    ], turn_number=TURN)


def permit(state, card=GIOVANNIS_MAGIKARP):
    """手札のトレーナー「サカキ」で ``card`` のポケモンに今の番の進化の許可を与える（公開の apply_command）。"""
    state = apply_command(state, PlayTrainer(0, card_of(state, 0, GIOVANNI)))
    return apply_command(state, ResolveDecision(0, state.decision.id, (pid_of(state, 0, card),)))


class Gv1Test(unittest.TestCase):
    """GV1: トレーナー「サカキ」の許可だけで制限が外れる組を、山札から重ねる効果で進化させられるかは決まらない（v0.44 の記録）。v0.44 はコードのない問いで、
    対応カードで起こらないとしていたが、エリカのピッピの「つきのちから」が自分の場のほかのポケモンを進化させるので、この番に場に出してサカキの許可を受けた
    サカキのコイキングで起こり、内部エラー（RuntimeError）になっていた。v0.45 で停止コードを付けた（裁定は未解決のまま）。つきのちからの対象は狭めない。"""

    def test_reproduction_stops_with_the_code_and_changes_nothing(self):
        """再現: この番に場に出したサカキのコイキングにサカキの許可を与え、山札にサカキのギャラドスがある状態で、エリカのピッピが「つきのちから」を使う。
        公開の apply_command は GV1 の停止コードで拒否し（内部エラーにならない）、どの先読みの方法でも状態・乱数・ログは変わらない（コインの前に止まる）。"""
        permitted = permit(gv1_board())
        self.assertEqual(find(permitted, 0, GIOVANNIS_MAGIKARP).evolution_permission_turn, TURN)
        before = snapshot(permitted)
        with self.assertRaises(UnsupportedError) as raised:
            apply_command(permitted, UseAttack(0, 0))
        self.assertEqual(raised.exception.code, GV1)
        self.assertEqual(snapshot(permitted), before)
        assert_stops(self, permitted, UseAttack(0, 0), GV1)

    def test_reproduction_from_a_magikarp_played_this_turn(self):
        """再現（手順どおり）: 手札のサカキのコイキングをこの番にベンチに出し、手札のサカキでそのポケモンに許可を与えてから、つきのちからを使う。"""
        state = build_test_state([
            {"active": {"card": ERIKAS_CLEFAIRY, "energy": [F]}, "bench": [RATTATA], "hand": [GIOVANNIS_MAGIKARP, GIOVANNI],
             "deck": [GIOVANNIS_GYARADOS, RATTATA, RATTATA]},
            {"active": mon(HITMONCHAN, (F, F)), "bench": [RATTATA]},
        ], turn_number=TURN)
        state = apply_command(state, PlayBasicToBench(0, card_of(state, 0, GIOVANNIS_MAGIKARP)))
        self.assertEqual(find(state, 0, GIOVANNIS_MAGIKARP).played_turn, TURN)
        permitted = permit(state)
        assert_stops(self, permitted, UseAttack(0, 0), GV1)

    def test_neighbour_magikarp_from_a_previous_turn_evolves(self):
        """隣の場合: 前の番から場にいるサカキのコイキングは、許可がなくても通常の進化の制限に当たらないので、つきのちからの「おもて」でサカキのギャラドスを
        重ねられる（停止しない。つきのちからの対象を狭めていない）。サカキの許可があっても同じ（許可は使わない）。"""
        for giovanni in (False, True):
            with self.subTest(giovanni=giovanni):
                state = gv1_board(magikarp_played_turn=TURN - 2, giovanni=giovanni)
                if giovanni:
                    state = permit(state)
                waiting = attack(state, 0, H)
                self.assertIn(pid_of(state, 0, GIOVANNIS_MAGIKARP), waiting.decision.options if waiting.decision.kind == SELECT_POKEMON else
                              [pid_of(state, 0, GIOVANNIS_MAGIKARP)])
                done = waiting
                while done.decision is not None and done.decision.player == 0:
                    d = done.decision
                    if d.kind == SELECT_POKEMON:
                        done = answer(done, (pid_of(state, 0, GIOVANNIS_MAGIKARP),))
                    else:
                        done = answer(done, (card_of(done, 0, GIOVANNIS_GYARADOS, "deck"),))
                audited(self, done)
                evolve = events(done, len(state.log), "evolve")
                self.assertEqual(len(evolve), 1)
                self.assertEqual(done.cards[find(done, 0, GIOVANNIS_GYARADOS).card].card_id, GIOVANNIS_GYARADOS)

    def test_neighbour_magikarp_played_this_turn_without_permission_is_not_a_target(self):
        """隣の場合: この番に場に出したサカキのコイキングは、許可がなければ通常の進化の制限で重ねられない（選べるものに入らない。止めない）。"""
        state = gv1_board(giovanni=False)
        done = attack(state, 0, H)
        while done.decision is not None and done.decision.player == 0:
            self.assertNotIn(pid_of(state, 0, GIOVANNIS_MAGIKARP), done.decision.options)
            done = answer(done, done.decision.options[:1])
        audited(self, done)
        self.assertEqual(events(done, len(state.log), "evolve"), [])
        self.assertIsNotNone(find(done, 0, GIOVANNIS_MAGIKARP))


# ---------------------------------------------------------------- ゆめくい・さいみんじゅつ


class DreamEaterTest(unittest.TestCase):
    """第1弾のゴースト。ゆめくいは最新の説明（p.160・LD-PMCG1-047-ATK1）のとおり、相手がねむりでないとワザが失敗する（p.323 の 12）。"""

    def test_fails_unless_the_opponent_is_asleep(self):
        """相手がねむりでないと、ワザの失敗（ログ ``attack_failed`` の理由 ``condition``）。ダメージはなく、番は終わる。ねむりなら 50（弱点 超 で 100、
        抵抗力 超 -30 で 20）。"""
        awake = board(mon(BASE_HAUNTER, (P, P)), mon(RATTATA, (F,)))
        done = audited(self, attack(awake, 1))
        self.assertEqual(kinds(done, len(awake.log))[:2], ["attack", "attack_failed"])
        self.assertEqual(events(done, len(awake.log), "attack_failed")[0]["reason"], "condition")
        self.assertEqual(events(done, len(awake.log), "damage"), [])
        self.assertEqual(done.current_player, 1)
        for opponent, amount in ((mon(ONIX, (F,), sleep=True), 50), (mon(RATTATA, (F,), sleep=True), 20), (mon(HITMONCHAN, (F, F), sleep=True), 100)):
            with self.subTest(opponent=opponent["card"]):
                state = board(mon(BASE_HAUNTER, (P, P)), opponent)
                done = audited(self, attack(state, 1))
                self.assertEqual(events(done, len(state.log), "damage")[0]["amount"], amount)
                self.assertEqual(events(done, len(state.log), "attack_failed"), [])

    def test_other_conditions_do_not_count(self):
        """どく・こんらん・マヒでは失敗する（ねむりだけ）。"""
        for status in ({"poison": 10}, {"confusion": True}, {"paralysis": TURN - 1}):
            with self.subTest(status=status):
                state = board(mon(BASE_HAUNTER, (P, P)), mon(RATTATA, (F,), **status))
                done = audited(self, attack(state, 1))
                self.assertEqual(events(done, len(state.log), "attack_failed")[0]["reason"], "condition")

    def test_confusion_tails_comes_first(self):
        """こんらん状態のゴーストの「うら」は、ゆめくいの条件を確かめる前に 20 の自分へのダメージ（p.309 の手順 5。ワザの内容を処理しない）。"""
        state = board(mon(BASE_HAUNTER, (P, P), confusion=True), mon(RATTATA, (F,)))
        done = audited(self, attack(state, 1, T))
        self.assertIn("confusion_damage", kinds(done, len(state.log)))
        self.assertEqual([e["reason"] for e in events(done, len(state.log), "attack_failed")], ["confusion"] if any(
            e["reason"] == "confusion" for e in events(done, len(state.log), "attack_failed")) else [])

    def test_hypnosis_puts_to_sleep_then_dream_eater_works(self):
        """さいみんじゅつ（既存の PutToSleep）でねむりにすると、次の自分の番のゆめくいは失敗しない（相手のねむりのコインが「うら」のまま）。"""
        state = board(mon(BASE_HAUNTER, (P, P)), mon(ONIX, (F,)))
        slept = audited(self, attack(state, 0, T))  # ポケモンチェックのねむりのコインは「うら」（回復しない）
        self.assertTrue(slept.players[1].active.conditions.asleep)
        again = end_turn(with_coin_results(slept, T))
        done = audited(self, attack(again, 1))
        self.assertEqual(events(done, len(again.log), "attack_failed"), [])
        self.assertEqual(events(done, len(again.log), "damage")[0]["amount"], 50)


# ---------------------------------------------------------------- スミをかける（期限のない手順 4 の効果）・AC13


class LastingAttackCheckTest(unittest.TestCase):
    """カスミのタッツー（HP 50）の「スミをかける」。v0.36 の ``AttackCoinCheck`` に「それ以後」（``lasting``）を明示した値。"""

    def inked(self, side=H):
        state = board(mon(MISTYS_HORSEA_50, (W, W)), mon(HITMONCHAN, (F, F)))
        return state, audited(self, attack(state, 0, side))

    def test_heads_gives_a_lasting_effect_and_tails_nothing(self):
        state, done = self.inked(H)
        [effect] = done.players[1].active.persistent_effects
        self.assertEqual(effect, AttackCoinCheck(source_card=state.players[0].active.card, source_player=0, created_turn=TURN, active_turn=TURN + 1,
                                                 single_use=False, lasting=True))
        added = events(done, len(state.log), "persistent_effect_added")[0]
        self.assertEqual((added["persistent_effect"], added["lasting"], added["single_use"]), ("attack_coin_check", True, False))
        state, done = self.inked(T)
        self.assertEqual(done.players[1].active.persistent_effects, ())
        self.assertEqual(events(done, len(state.log), "persistent_effect_added"), [])

    def test_check_works_every_later_turn(self):
        """次の相手の番だけでなく、そのあとの相手の番も、ワザを使うたびに手順 4 のコイン（「うら」なら失敗）。期限で消えない（えんまくとの違い）。"""
        _, done = self.inked(H)
        failed = audited(self, attack(done, 0, T, player=1))
        self.assertEqual(kinds(failed, len(done.log))[:4], ["attack", "coin_flip", "attack_check", "attack_failed"])
        later = end_turn(failed)
        self.assertEqual(len(later.players[1].active.persistent_effects), 1)
        hit = audited(self, attack(later, 0, H, player=1))
        self.assertEqual(kinds(hit, len(later.log))[:4], ["attack", "coin_flip", "attack_check", "damage"])
        self.assertEqual(len(hit.players[1].active.persistent_effects), 1)

    def test_effect_ends_when_the_pokemon_leaves_the_active_spot(self):
        """バトル場をはなれたら消える（にげる・入れ替え。p.322・p.323）。もどっても復活しない。"""
        _, done = self.inked(H)
        active = done.players[1].active
        cost = done.card_def(active.card).retreat_cost
        retreated = audited(self, apply_kernel(done, Retreat(1, tuple(active.energy[:cost]), done.players[1].bench[0].card)))
        hitmonchan = find(retreated, 1, HITMONCHAN)
        self.assertEqual(hitmonchan.persistent_effects, ())
        self.assertEqual(events(retreated, len(done.log), "persistent_effect_removed")[0]["reason"], "retreat")

    def test_effect_ends_on_evolution(self):
        """進化しても消える（p.310・p.323。「別のポケモン」）。"""
        state = board(mon(MISTYS_HORSEA_50, (W, W)), mon(RATTATA, (F,)), opponent_hand=[RATICATE])
        inked = audited(self, attack(state, 0, H))
        from kyuura_engine import EvolvePokemon
        evolved = audited(self, apply_kernel(inked, EvolvePokemon(1, card_of(inked, 1, RATICATE), inked.players[1].active.pokemon_id)))
        self.assertEqual(evolved.players[1].active.persistent_effects, ())
        self.assertEqual(events(evolved, len(inked.log), "persistent_effect_removed")[0]["reason"], "evolve")

    def test_ac13_two_attack_checks_stop_before_the_coin(self):
        """AC13: 同じポケモンが手順 4 の効果を 2 つ受けた状態でワザを使うとき、コインをいくつ投げるかは決まらない。宣言のあと・コインの前に
        ``UNRESOLVED_MULTIPLE_ATTACK_CHECKS``（状態・乱数・ログは変わらない）。v0.36〜v0.44 は対応カードで起こらず RuntimeError だった。効果が 1 つなら止めない。"""
        _, done = self.inked(H)
        second_turn = end_turn(done)  # プレイヤー 1 はワザを使わない
        twice = audited(self, attack(second_turn, 0, H))
        self.assertEqual(len(twice.players[1].active.persistent_effects), 2)
        assert_stops(self, twice, UseAttack(1, 0), AC13)
        # 隣の場合: 効果が 1 つなら止めない（手順 4 のコインを 1 枚）
        once = audited(self, attack(done, 0, H, player=1))
        self.assertEqual(len(events(once, len(done.log), "attack_check")), 1)

    def test_ac13_with_smokescreen(self):
        """「それ以後」の効果と、えんまく（化石の秘密のタッツー。次の相手の番だけ）を両方受けても AC13。"""
        state = board(mon(MISTYS_HORSEA_50, (W, W)), mon(HITMONCHAN, (F, F)), bench=(mon(HORSEA, (W,)),), hand=[SWITCH])
        inked = attack(state, 0, H)
        back = end_turn(inked)
        switched = apply_kernel(back, PlayTrainer(0, card_of(back, 0, SWITCH)))
        switched = answer(switched, (pid_of(switched, 0, HORSEA),))
        smoked = audited(self, attack(switched, 0, H))
        self.assertEqual(sorted(e.lasting for e in smoked.players[1].active.persistent_effects), [False, True])
        assert_stops(self, smoked, UseAttack(1, 0), AC13)

    def test_ac13_comes_before_ac6(self):
        """こんらん状態で 2 つの効果を受けている場合も AC13（AC6 より先に確かめる。どちらも未解決）。効果が 1 つのこんらん状態は AC6（v0.36）。"""
        state = board(mon(MISTYS_HORSEA_50, (W, W)), mon(HITMONCHAN, (F, F), confusion=True))
        once = audited(self, attack(state, 0, H))
        assert_stops(self, once, UseAttack(1, 0), AC6)
        twice = audited(self, attack(end_turn(once), 0, H))
        assert_stops(self, twice, UseAttack(1, 0), AC13)

    def test_effect_coin_questions(self):
        """効果を与えるコインは相手への効果だけを決めるので、「ワザをうけない」相手に HC3（ダメージの要素も無効）、「とうめい」で受けないことがありうる相手に
        T19b（v0.9。宣言の前に止める）。相手がこのワザで HP 以上なら投げない。"""
        barrier = with_barrier(mon(MISTYS_HORSEA_50, (W, W)))
        assert_stops(self, barrier, UseAttack(1, 0), HC3)
        assert_stops(self, with_haunter_defender(mon(MISTYS_HORSEA_50, (W, W))), UseAttack(0, 0), T19B)
        state = board(mon(MISTYS_HORSEA_50, (W, W)), mon(RATTATA, (F,), damage=20))
        done = audited(self, attack(state, 0))
        self.assertEqual(events(done, len(state.log), "coin_flip"), [])
        self.assertIn("knock_out", kinds(done, len(state.log)))


# ---------------------------------------------------------------- こおりのつぶて・とっしん


class IceShardTest(unittest.TestCase):
    """カスミのジュゴン。こおりのつぶては、相手が闘ポケモンなら p.321 の 1 段階で 2 倍（弱点・抵抗力はそのあと）。"""

    def test_fighting_defender_doubles_at_step_1(self):
        for opponent, amount in ((mon(MACHOP, (F,)), 40), (mon(ONIX, (F,)), 40), (mon(RATTATA, (F,)), 20), (mon(ROCKETS_ZAPDOS, (L,)), 20)):
            with self.subTest(opponent=opponent["card"]):
                state = board(mon(MISTYS_DEWGONG, (W, W)), opponent)
                done = audited(self, attack(state, 0))
                self.assertEqual(events(done, len(state.log), "damage")[0]["amount"], amount)
        # プラスパワー（5 段階）は 2 倍にしたあとに加える（最終ダメージを 2 倍にしない）
        state = board(mon(MISTYS_DEWGONG, (W, W), trainers=[(PLUSPOWER, TURN)]), mon(MACHOP, (F,)))
        done = audited(self, attack(state, 0))
        self.assertEqual(events(done, len(state.log), "damage")[0]["amount"], 50)

    def test_take_down_self_damage(self):
        state = board(mon(MISTYS_DEWGONG, (W, W, W, W)), mon(CHANSEY, (F,)))
        done = audited(self, attack(state, 1))
        self.assertEqual([e["amount"] for e in events(done, len(state.log), "damage")], [60, 20])


# ---------------------------------------------------------------- とつぜんどく・どくをためる・ポイズンパワー・ベトベトハンド


class PoisonTest(unittest.TestCase):

    def test_sudden_poison_needs_both_heads(self):
        """2 枚のコインがすべて「おもて」のときだけ、どくとこんらんの両方。1 枚のコイン組で決める（要素ごとに投げ直さない）。"""
        for sides, both in (((H, H), True), ((H, T), False), ((T, H), False), ((T, T), False)):
            with self.subTest(sides=sides):
                state = board(mon(KOGAS_EKANS, (G,)), mon(CHANSEY, (F,)))
                done = audited(self, attack(state, 0, *sides))
                defender = done.players[1].active
                self.assertEqual(len(events(done, len(state.log), "coin_flip")), 2)
                self.assertEqual((defender.conditions.poison is not None, defender.conditions.confused), (both, both))

    def test_sudden_poison_coin_questions(self):
        """コインは相手への効果だけを決めるので、「ワザをうけない」相手は HC3（v0.34）。相手がこのワザで HP 以上なら投げない。"""
        assert_stops(self, with_barrier(mon(KOGAS_EKANS, (G,))), UseAttack(1, 0), HC3)
        state = board(mon(KOGAS_EKANS, (G,)), mon(RATTATA, (F,), damage=20))
        done = audited(self, attack(state, 0))
        self.assertEqual(events(done, len(state.log), "coin_flip"), [])

    def test_poison_buildup_poisons_itself(self):
        """どくをためる: ダメージなしで自分をどく（通常のどく 10）。すでにどくなら二重にしない。特殊などく（20）のポケモンが通常のどくを受けたら通常の
        どく（v0.3a の 14。p.322。CONFIRMED）。"""
        state = board(mon(KOGAS_ARBOK, (G,)), mon(CHANSEY, (F,)))
        done = audited(self, attack(state, 0))
        self.assertEqual(done.players[0].active.conditions.poison.damage, 10)
        self.assertEqual(events(done, len(state.log), "damage"), [])
        state = board(mon(KOGAS_ARBOK, (G,), poison=20), mon(CHANSEY, (F,)))
        done = audited(self, attack(state, 0))
        self.assertEqual(done.players[0].active.conditions.poison.damage, 10)

    def test_poison_power_depends_on_its_own_poison(self):
        """ポイズンパワー: 自分がどく（通常・特殊のどちらでも）なら 40 で相手をどく、どくでなければ 20 で相手はどくにならない。"""
        for status, amount, poisoned in (({}, 20, False), ({"poison": 10}, 40, True), ({"poison": 20}, 40, True)):
            with self.subTest(status=status):
                state = board(mon(KOGAS_ARBOK, (G, G), **status), mon(CHANSEY, (F,)))
                done = audited(self, attack(state, 1))
                self.assertEqual(events(done, len(state.log), "damage")[0]["amount"], amount)
                defender = done.players[1].active
                self.assertEqual(defender.conditions.poison is not None, poisoned)
                if poisoned:
                    self.assertEqual(defender.conditions.poison.damage, 10)

    def test_poison_power_knocked_out_defender_is_not_poisoned(self):
        state = board(mon(KOGAS_ARBOK, (G, G), poison=10), mon(RATTATA, (F,)))
        done = audited(self, attack(state, 1))
        self.assertEqual(events(done, len(state.log), "special_condition"), [])
        self.assertIn("knock_out", kinds(done, len(state.log)))

    def test_sludge_hand_switches_then_poisons_the_new_active(self):
        """ベトベトハンド: 「おもて」なら、ワザを使ったプレイヤーが相手の控えを選んで入れ替え、新しい対戦ポケモンをどく。入れ替える前の対戦ポケモンはどくに
        しない。「うら」・相手に控えがいないなら何もしない（控えがいなければコインも投げない）。"""
        state = board(mon(KOGAS_GRIMER, (G,)), mon(HITMONCHAN, (F, F)), opponent_bench=(RATTATA, MACHOP))
        waiting = attack(state, 0, H)
        d = waiting.decision
        self.assertEqual((d.kind, d.player, d.options), (FORCED_SWITCH, 0, tuple(p.pokemon_id for p in state.players[1].bench)))
        machop = pid_of(state, 1, MACHOP)
        done = audited(self, answer(waiting, (machop,)))
        self.assertEqual(done.players[1].active.pokemon_id, machop)
        self.assertIsNotNone(done.players[1].active.conditions.poison)
        self.assertIsNone(find(done, 1, HITMONCHAN).conditions.poison)
        tails = audited(self, attack(state, 0, T))
        self.assertEqual(tails.players[1].active.card, state.players[1].active.card)
        self.assertEqual(events(tails, len(state.log), "special_condition"), [])
        # 入れ替えのコインは相手への効果だけを決める（入れ替える前の対戦ポケモンが「ワザをうけない」なら HC3）
        assert_stops(self, with_barrier(mon(KOGAS_GRIMER, (G,))), UseAttack(1, 0), HC3)
        alone = board(mon(KOGAS_GRIMER, (G,)), mon(HITMONCHAN, (F, F)), opponent_bench=())
        done = audited(self, attack(alone, 0))
        self.assertEqual(events(done, len(alone.log), "coin_flip"), [])
        self.assertIsNone(done.players[1].active.conditions.poison)


# ---------------------------------------------------------------- ハイドロキャノン・ロケットタックル


class DarkBlastoiseTest(unittest.TestCase):

    def test_hydro_cannon(self):
        """多い「水」エネルギー 1 つにつき 20（2 つぶんまで）。既存の ExtraEnergyDamage。"""
        for energy, amount in (((W, W), 30), ((W, W, W), 50), ((W, W, W, W), 70), ((W, W, W, W, W), 70)):
            with self.subTest(energy=len(energy)):
                state = board(mon(DARK_BLASTOISE, energy), mon(CHANSEY, (F,)))
                done = audited(self, attack(state, 0))
                self.assertEqual(events(done, len(state.log), "damage")[0]["amount"], amount)

    def test_rocket_tackle(self):
        """相手に 40 → 自分に 10 → コインの「おもて」で次の相手の番にダメージを受けない（PreventDamage。ダメージ以外の効果は受ける）。"""
        state = board(mon(DARK_BLASTOISE, (W, W, W)), mon(MACHOP, (F,)))
        done = audited(self, attack(state, 1, H))
        self.assertEqual([e["amount"] for e in events(done, len(state.log), "damage")], [40, 10])
        [effect] = done.players[0].active.persistent_effects
        self.assertIsInstance(effect, PreventDamage)
        # 次の相手の番、ワザのダメージを受けない（ダメージの要素は計算の前に無効。ログ damage_prevented）
        hit = audited(self, attack(done, 0, player=1))
        self.assertIn("damage_prevented", kinds(hit, len(done.log)))
        self.assertEqual(hit.players[0].active.damage, done.players[0].active.damage)
        tails = audited(self, attack(state, 1, T))
        self.assertEqual(tails.players[0].active.persistent_effects, ())

    def test_rocket_tackle_no_coin_if_self_knocked_out(self):
        state = board(mon(DARK_BLASTOISE, (W, W, W), damage=60), mon(CHANSEY, (F,)))
        done = audited(self, attack(state, 1))
        self.assertEqual(events(done, len(state.log), "coin_flip"), [])


# ---------------------------------------------------------------- ソニックブーム・じりょくせん


class DarkMagnetonTest(unittest.TestCase):

    def test_sonic_boom_ignores_weakness_and_resistance(self):
        for opponent in (mon(MACHOP, (F,)), mon(ROCKETS_ZAPDOS, (L,)), mon(CHANSEY, (F,))):
            with self.subTest(opponent=opponent["card"]):
                state = board(mon(DARK_MAGNETON, (L, L)), opponent)
                done = audited(self, attack(state, 0))
                self.assertEqual(events(done, len(state.log), "damage")[0]["amount"], 20)

    def magnetic(self, opponent_bench=(RATTATA, MACHOP)):
        return board(mon(DARK_MAGNETON, (L, L)), mon(CHANSEY, (F, W, F)), opponent_bench=opponent_bench)

    def test_moves_a_chosen_basic_energy_to_a_chosen_bench_pokemon(self):
        """ワザを使ったプレイヤーが、相手の対戦ポケモンの基本エネルギーカード（1 枚でも決定）→ 相手の控えポケモンを選ぶ。同じ uid のカードを動かす。"""
        state = self.magnetic()
        chansey = state.players[1].active
        waiting = attack(state, 1)
        d = waiting.decision
        self.assertEqual((d.kind, d.player, d.options), (MOVE_OPPONENT_ENERGY, 0, tuple(chansey.energy)))
        water = chansey.energy[1]
        second = answer(waiting, (water,))
        self.assertEqual((second.decision.kind, second.decision.options), (SELECT_POKEMON, tuple(p.pokemon_id for p in state.players[1].bench)))
        machop = pid_of(state, 1, MACHOP)
        done = audited(self, answer(second, (machop,)))
        self.assertEqual(done.players[1].active.energy, [u for u in chansey.energy if u != water])
        self.assertEqual(find(done, 1, MACHOP).energy, [water])
        [moved] = events(done, len(state.log), "move_opponent_energy")
        self.assertEqual((moved["player"], moved["energy"], moved["to_pokemon_id"], moved["result"]), (1, water, machop, "attached"))
        self.assertLess(kinds(done, len(state.log)).index("damage"), kinds(done, len(state.log)).index("move_opponent_energy"))

    def test_no_effect_cases(self):
        """相手に控えがいない（説明）・基本エネルギーがない・相手がこのワザで HP 以上なら、はがさない（決定もない）。"""
        cases = (board(mon(DARK_MAGNETON, (L, L)), mon(CHANSEY, (F,)), opponent_bench=()),
                 board(mon(DARK_MAGNETON, (L, L)), mon(CHANSEY, ())),
                 board(mon(DARK_MAGNETON, (L, L)), mon(RATTATA, (F,), damage=20)))
        for state in cases:
            with self.subTest(state=len(state.players[1].bench)):
                done = audited(self, attack(state, 1))
                self.assertEqual(events(done, len(state.log), "move_opponent_energy"), [])
                self.assertTrue(done.decision is None or done.decision.kind != MOVE_OPPONENT_ENERGY)

    def test_transparent_destination_discards_the_card(self):
        """つける控えポケモンが「とうめい」で受けなければ、はがしたカードは持ち主のトラッシュ（CR-TRANSPARENCY-ENERGY-BOMB と同じ読み方）。「うら」ならつける。"""
        state = self.magnetic(opponent_bench=(RATTATA, HAUNTER))
        second = answer(attack(state, 1), (state.players[1].active.energy[0],))
        haunter = pid_of(state, 1, HAUNTER)
        for side, result in ((H, "evaded"), (T, "attached")):
            with self.subTest(side=side):
                done = audited(self, answer(with_coin_results(second, side), (haunter,)))
                [moved] = events(done, len(state.log), "move_opponent_energy")
                self.assertEqual(moved["result"], result)
                energy = state.players[1].active.energy[0]
                self.assertEqual(energy in done.players[1].discard, result == "evaded")
                self.assertEqual(energy in find(done, 1, HAUNTER).energy, result == "attached")

    def test_barrier_blocks_the_move(self):
        """「ワザをうけない」相手からははがさない（ダメージも無効。コインのないワザなので止めない）。"""
        state = with_barrier(mon(DARK_MAGNETON, (L, L)))
        done = audited(self, attack(state, 1, player=1))
        self.assertEqual(events(done, len(state.log), "move_opponent_energy"), [])

    def test_save_and_restore_between_the_decisions(self):
        """2 つの決定のあいだの状態を写して（clone・deepcopy・pickle）も、同じ答えで同じ結果。"""
        state = self.magnetic()
        second = answer(attack(state, 1), (state.players[1].active.energy[0],))
        expected = snapshot(answer(second, (pid_of(state, 1, MACHOP),)))
        for copied in (second.clone(), copy.deepcopy(second), pickle.loads(pickle.dumps(second))):
            self.assertEqual(snapshot(answer(copied, (pid_of(state, 1, MACHOP),))), expected)


# ---------------------------------------------------------------- ファイヤーブレス・かえんひこう


class BlainesCharizardTest(unittest.TestCase):

    def test_fire_breath_discards_the_excess(self):
        """必要なエネルギー（炎 1）より多い炎の基本エネルギーカードをすべてトラッシュし、1 枚につき 20 を 1 段階で追加。選ぶのはワザを使ったプレイヤー
        （多い枚数ちょうど）。多くなければトラッシュも決定もない。"""
        state = board(mon(BLAINES_CHARIZARD, (R, R, R)), mon(CHANSEY, (F,)))
        waiting = attack(state, 0)
        d = waiting.decision
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices, d.options), (DISCARD_ENERGY, 0, 2, 2, tuple(state.players[0].active.energy)))
        keep = state.players[0].active.energy[0]
        done = audited(self, answer(waiting, tuple(u for u in d.options if u != keep)))
        self.assertEqual(done.players[0].active.energy, [keep])
        self.assertEqual(kinds(done, len(state.log))[:4], ["attack", "discard_energy", "discard_energy", "damage"])
        self.assertEqual(events(done, len(state.log), "damage")[0]["amount"], 60)
        one = board(mon(BLAINES_CHARIZARD, (R,)), mon(CHANSEY, (F,)))
        done = audited(self, attack(one, 0))
        self.assertEqual(kinds(done, len(one.log))[:2], ["attack", "damage"])
        self.assertEqual(events(done, len(one.log), "damage")[0]["amount"], 20)

    def test_fire_breath_confusion_tails_does_not_discard(self):
        state = board(mon(BLAINES_CHARIZARD, (R, R, R), confusion=True), mon(CHANSEY, (F,)))
        done = audited(self, attack(state, 0, T))
        self.assertEqual(events(done, len(state.log), "discard_energy"), [])
        self.assertEqual(len(done.players[0].active.energy), 3)

    def test_flame_flight(self):
        """かえんひこう: 「おもて」なら相手の場のポケモンを 1 匹選んで、弱点・抵抗力に関係なく 40（v0.44 の型の書き方を受け付けた）。「うら」なら何もしない。"""
        state = board(mon(BLAINES_CHARIZARD, (R, R)), mon(CHANSEY, (F,)), opponent_bench=(MACHOP,))
        waiting = attack(state, 1, H)
        machop = pid_of(state, 1, MACHOP)
        self.assertIn(machop, waiting.decision.options)
        done = audited(self, answer(waiting, (machop,)))
        self.assertEqual(find(done, 1, MACHOP).damage, 40)
        tails = audited(self, attack(state, 1, T))
        self.assertEqual(events(tails, len(state.log), "damage"), [])


# ---------------------------------------------------------------- プラズマ・エレクトロバーン


class RocketsZapdosTest(unittest.TestCase):

    def test_plasma_attaches_one_lightning_from_the_discard(self):
        """トラッシュに雷のエネルギーカードがあれば 1 枚（ちょうど。1 枚でも決定）を自分につける。なければ何もしない。手札からつける回数に数えない。"""
        state = board(mon(ROCKETS_ZAPDOS, (L,)), mon(CHANSEY, (F,)), discard=[L, L, W])
        waiting = attack(state, 0)
        d = waiting.decision
        lightning = tuple(u for u in state.players[0].discard if state.cards[u].card_id == L)
        self.assertEqual((d.kind, d.min_choices, d.max_choices, d.options), (ATTACH_FROM_DISCARD, 1, 1, lightning))
        done = audited(self, answer(waiting, (lightning[1],)))
        self.assertEqual(done.players[0].active.energy, [state.players[0].active.energy[0], lightning[1]])
        self.assertEqual(done.energy_attachments_this_turn, state.energy_attachments_this_turn)
        empty = board(mon(ROCKETS_ZAPDOS, (L,)), mon(CHANSEY, (F,)), discard=[W])
        done = audited(self, attack(empty, 0))
        self.assertEqual(len(done.players[0].active.energy), 1)

    def test_electroburn_self_damage_counts_lightning_cards(self):
        for energy, self_damage in (((L, L, L, F), 30), ((L, L, L, L), 40), ((L, L, L, L, L), 50)):
            with self.subTest(energy=energy):
                state = board(mon(ROCKETS_ZAPDOS, energy), mon(CHANSEY, (F,)))
                done = audited(self, attack(state, 1))
                self.assertEqual([e["amount"] for e in events(done, len(state.log), "damage")], [70, self_damage])


# ---------------------------------------------------------------- かたくなる・いかりのまえば


class OnixRaticateTest(unittest.TestCase):

    def test_harden_zeroes_damage_below_40_on_the_next_opponent_turn(self):
        """次の相手の番、8 段階のダメージが 40 より小さければ 0（ログ ``damage_zero_below``）、40 以上ならそのまま。ダメージ以外の効果は受ける。
        次の相手の番の終わりに消える。"""
        state = board(mon(ONIX, (F, F)), mon(KOGAS_ARBOK, (G, G), poison=10))
        hardened = audited(self, attack(state, 1))
        [effect] = hardened.players[0].active.persistent_effects
        self.assertEqual(effect, ZeroDamageBelow(source_card=state.players[0].active.card, source_player=0, created_turn=TURN, active_turn=TURN + 1,
                                                 threshold=40))
        # ポイズンパワー（どく状態なので 40。イワークは草の弱点で 80）は 40 以上なのでそのまま。相手をどくにする効果は受ける
        hit = audited(self, attack(hardened, 1, player=1))
        self.assertEqual(events(hit, len(hardened.log), "damage")[0]["amount"], 80)
        onix = state.players[0].active.pokemon_id
        self.assertEqual([(e["pokemon_id"], e["condition"]) for e in events(hit, len(hardened.log), "special_condition")], [(onix, "poison")])
        small = board(mon(ONIX, (F, F)), mon(RATTATA, (F,)))
        hardened = attack(small, 1)
        bitten = audited(self, attack(hardened, 0, player=1))
        [damage] = events(bitten, len(hardened.log), "damage")
        self.assertEqual(damage["amount"], 0)
        self.assertEqual(bitten.players[0].active.damage, 0)
        self.assertEqual(len(events(bitten, len(hardened.log), "persistent_effect_removed")), 1)

    def test_zero_if_below_is_a_step_8_modifier(self):
        """しきい値は 8 段階の値（弱点・抵抗力・プラスパワー・ディフェンダーのあと）。ZERO_IF_BELOW は加算でない変更効果。"""
        modifier = DamageModifier(8, 40, "かたくなる", operation=ZERO_IF_BELOW)
        self.assertEqual((modifier.apply(30), modifier.apply(40), modifier.apply(50)), (0, 40, 50))
        with self.assertRaises(ValueError):
            DamageModifier(8, 0, "かたくなる", operation=ZERO_IF_BELOW)
        # ラッタのかみつく 20 + プラスパワー 10 = 30 < 40 → 0。マチスのコイル… 闘の弱点で 2 倍になれば 40 → そのまま
        small = board(mon(ONIX, (F, F)), mon(RATTATA, (F,), trainers=[(PLUSPOWER, TURN + 1)]))
        hardened = attack(small, 1)
        bitten = audited(self, attack(hardened, 0, player=1))
        self.assertEqual(events(bitten, len(hardened.log), "damage")[0]["amount"], 0)

    def test_super_fang_half_remaining_hp_rounded_up(self):
        """いかりのまえば: 相手の残りの HP の半分（カウンターの単位で切り上げ）が 1 段階の基本となるダメージ。弱点などはそのあと。"""
        for opponent, amount in ((mon(CHANSEY, (F,)), 60), (mon(CHANSEY, (F,), damage=10), 60), (mon(CHANSEY, (F,), damage=20), 50),
                                 (mon(MACHOP, (F,)), 30), (mon(HITMONCHAN, (F, F), damage=40), 20)):
            with self.subTest(opponent=opponent):
                state = board(mon(RATICATE, (F, F, F)), opponent)
                done = audited(self, attack(state, 1))
                self.assertEqual(events(done, len(state.log), "damage")[0]["amount"], amount)


# ---------------------------------------------------------------- クロスカウンター


class CrossCounterTest(unittest.TestCase):
    """R団のエビワラー。こうらがえし（v0.13）の Retaliation に倍数 2 と、はたらくときのコインを明示した値（LD-PMCG5-054-ATK0）。"""

    def countered(self, opponent=None):
        state = board(mon(ROCKETS_HITMONCHAN, (F, F, F)), opponent or mon(RATTATA, (F,)))
        return audited(self, attack(state, 0))

    def test_effect_is_a_scaled_retaliation(self):
        done = self.countered()
        [effect] = done.players[0].active.persistent_effects
        self.assertEqual(effect, Retaliation(source_card=done.players[0].active.card, source_player=0, created_turn=TURN, active_turn=TURN + 1,
                                             attack_index=0, amount=None, basis=RETALIATION_RECEIVED, multiplier=2, on_heads=True))
        self.assertEqual(effect.kind, RETALIATION_RECEIVED_SCALED_KIND)
        self.assertEqual(effect.base_damage(20), 40)
        self.assertEqual(events(done, 0, "coin_flip"), [])  # 効果を与えるときはコインを投げない

    def test_heads_returns_twice_the_received_damage(self):
        """相手のワザのダメージを受けたら、効果を持つポケモンの持ち主がコインを投げ、「おもて」なら受けた最終ダメージの 2 倍を 1 段階に（弱点・抵抗力は
        そのあと。ラッタは闘の弱点で 80）。「うら」なら与えない（ログ ``retaliation_skipped`` の ``coin_tails``）。"""
        done = self.countered()
        hit = audited(self, attack(done, 0, H, player=1))
        coin = events(hit, len(done.log), "coin_flip")[0]
        self.assertEqual(coin["player"], 0)
        [ret] = events(hit, len(done.log), "retaliation")
        self.assertEqual((ret["received_damage"], ret["multiplier"], ret["amount"], ret["coin"]), (20, 2, 40, "heads"))
        self.assertEqual(events(hit, len(done.log), "damage")[-1]["amount"], 80)
        missed = audited(self, attack(done, 0, T, player=1))
        [skipped] = events(missed, len(done.log), "retaliation_skipped")
        self.assertEqual((skipped["reason"], skipped["received_damage"]), (E.RETALIATION_COIN_TAILS, 20))
        self.assertEqual(len(events(missed, len(done.log), "damage")), 1)

    def test_no_coin_when_the_attacker_is_already_knocked_out(self):
        """ワザを使ったポケモンが同じワザの自分へのダメージですでに HP 以上なら、処理の対象がないのでコインを投げない（C15。ログ ``retaliation_skipped`` の
        ``RETALIATION_TARGET_KNOCKED_OUT``）。"""
        state = board(mon(ROCKETS_HITMONCHAN, (F, F, F)), mon(MISTYS_DEWGONG, (W, W, W, W), damage=60))
        done = attack(state, 0)
        hit = audited(self, attack(done, 1, player=1))
        self.assertEqual(events(hit, len(done.log), "coin_flip"), [])
        [skipped] = events(hit, len(done.log), "retaliation_skipped")
        self.assertEqual(skipped["reason"], E.RETALIATION_TARGET_KNOCKED_OUT)

    def test_effect_ends_after_the_next_opponent_turn(self):
        """効果は次の相手の番の終わりに消える（ダメージを受けなくても）。そのあとのダメージには返さない。"""
        done = self.countered()
        passed = end_turn(done)
        self.assertEqual(passed.players[0].active.persistent_effects, ())
        self.assertEqual(events(passed, len(done.log), "persistent_effect_removed")[0]["reason"], "expired")

    def test_double_knockout_is_w24(self):
        """エビワラーがワザのダメージで、ワザを使ったポケモンが返すダメージで、そろってきぜつしうる場合は既存の W24（コインの「おもて」がありうる）。"""
        state = board(mon(ROCKETS_HITMONCHAN, (F, F, F), damage=40), mon(RATTATA, (F,)))
        done = attack(state, 0)
        assert_stops(self, done, UseAttack(1, 0), W24)

    def test_copying_is_engine_unsupported(self):
        """相手のワザとして使う（ゆびをふる）のは、エンジンの未対応（v0.31 の SelfRetaliation と同じ）。"""
        state = board(mon(CLEFAIRY, (P, P, P)), mon(ROCKETS_HITMONCHAN, (F,)))
        waiting = attack(state, 1)
        d = waiting.decision
        self.assertEqual(d.kind, SELECT_ATTACK)
        self.assertIn(0, d.context_value("unsupported_choices"))
        with self.assertRaises(UnsupportedError) as raised:
            answer(waiting, (0,))
        self.assertEqual(raised.exception.code, "UNSUPPORTED_COPIED_ATTACK")


# ---------------------------------------------------------------- たすけをよぶ・スパイラルショット


class BrocksGeodudeTest(unittest.TestCase):

    def test_call_for_family(self):
        """「おもて」: 山札の「タケシの」たねポケモンを 0〜1 匹ベンチに出し、どの場合も山札を切る。「うら」: 何もしない（切らない）。"""
        deck = [BROCKS_ONIX, BROCKS_GEODUDE, BROCKS_ZUBAT, RATTATA, F]
        state = board(mon(BROCKS_GEODUDE_40, (F,)), mon(CHANSEY, (F,)), deck=deck)
        waiting = attack(state, 0, H)
        d = waiting.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (BENCH_FROM_DECK, 0, 1))
        self.assertEqual(sorted(state.cards[u].card_id for u in d.options), sorted([BROCKS_ONIX, BROCKS_GEODUDE, BROCKS_ZUBAT]))
        onix = card_of(state, 0, BROCKS_ONIX, "deck")
        done = audited(self, answer(waiting, (onix,)))
        self.assertIn(onix, [p.card for p in done.players[0].bench])
        self.assertIn("shuffle", kinds(done, len(state.log)))
        declined = audited(self, answer(waiting, ()))
        self.assertEqual(kinds(declined, len(state.log))[:4], ["attack", "coin_flip", "bench_from_deck_declined", "shuffle"])
        tails = audited(self, attack(state, 0, T))
        self.assertNotIn("shuffle", kinds(tails, len(state.log)))
        self.assertEqual(tails.players[0].deck, state.players[0].deck)

    def test_call_for_family_without_candidates_or_bench_space(self):
        state = board(mon(BROCKS_GEODUDE_40, (F,)), mon(CHANSEY, (F,)), deck=[RATTATA, F])
        done = audited(self, attack(state, 0, H))
        self.assertEqual(kinds(done, len(state.log))[:4], ["attack", "coin_flip", "bench_from_deck_none", "shuffle"])
        full_bench = board(mon(BROCKS_GEODUDE_40, (F,)), mon(CHANSEY, (F,)), bench=(RATTATA,) * 5, deck=[BROCKS_ONIX])
        assert_rejected(self, full_bench, UseAttack(0, 0), "BENCH_FULL", exception=IllegalActionError)

    def test_spiral_shot_ignores_only_resistance(self):
        """スパイラルショット: 抵抗力（4 段階）だけを計算しない。弱点は計算する。"""
        for opponent, amount in ((mon(ROCKETS_ZAPDOS, (L,)), 20), (mon(ZAPDOS, (L,)), 20), (mon(RATTATA, (F,)), 40), (mon(CHANSEY, (F,)), 40)):
            with self.subTest(opponent=opponent["card"]):
                state = board(mon(BROCKS_GEODUDE_40, (F, F)), opponent)
                done = audited(self, attack(state, 1))
                self.assertEqual(events(done, len(state.log), "damage")[0]["amount"], amount)


# ---------------------------------------------------------------- てつだうふり・ダブルひっかき


class GiovannisMeowthTest(unittest.TestCase):

    def test_pretend_to_help(self):
        """「おもて」: 相手の山札の一番上がトレーナーなら相手のトラッシュ、それ以外なら相手の手札（カードを引くことではない。山札は切らない）。"""
        for top, zone in ((POTION, "discard"), (RATTATA, "hand"), (F, "hand")):
            with self.subTest(top=top):
                state = board(mon(GIOVANNIS_MEOWTH_40, (F,)), mon(CHANSEY, (F,)), opponent_deck=[top, RATTATA, F])
                card = state.players[1].deck[0]
                done = audited(self, attack(state, 0, H))
                self.assertIn(card, getattr(done.players[1], zone))
                [moved] = events(done, len(state.log), "take_deck_top")
                self.assertEqual((moved["player"], moved["card"], moved["destination"], moved["looker"]), (1, card, zone, 0))
                self.assertNotIn("draw", kinds(done, len(state.log))[:3])
                self.assertNotIn("shuffle", kinds(done, len(state.log)))
        state = board(mon(GIOVANNIS_MEOWTH_40, (F,)), mon(CHANSEY, (F,)), opponent_deck=[RATTATA])
        tails = audited(self, attack(state, 0, T))
        self.assertEqual(events(tails, len(state.log), "take_deck_top"), [])

    def test_pretend_to_help_with_an_empty_deck_flips_no_coin(self):
        state = board(mon(GIOVANNIS_MEOWTH_40, (F,)), mon(CHANSEY, (F,)), opponent_deck=[])
        done = attack(state, 0)
        self.assertEqual(events(done, len(state.log), "coin_flip"), [])

    def test_double_scratch(self):
        for sides, amount in (((H, H), 40), ((H, T), 20), ((T, T), 0)):
            with self.subTest(sides=sides):
                state = board(mon(GIOVANNIS_MEOWTH_40, (F, F)), mon(CHANSEY, (F,)))
                done = audited(self, attack(state, 1, *sides))
                self.assertEqual(sum(e["amount"] for e in events(done, len(state.log), "damage")), amount)


# ---------------------------------------------------------------- 不変条件


class InvariantTest(unittest.TestCase):
    """新しい持続する効果の値は、効果を与えたワザ（ログ ``persistent_effect_added`` の ``effect``）の登録と照らす（engine._persistent_effect_problems）。"""

    def assert_broken(self, state, player, change):
        import dataclasses

        broken = state.clone()
        pokemon = broken.players[player].active
        pokemon.persistent_effects = tuple(dataclasses.replace(e, **change) for e in pokemon.persistent_effects)
        self.assertTrue(check_invariants(broken), change)

    def test_values_must_match_the_registration(self):
        self.assert_broken(attack(board(mon(ONIX, (F, F))), 1), 0, {"threshold": 30})
        self.assert_broken(attack(board(mon(ROCKETS_HITMONCHAN, (F,))), 0), 0, {"multiplier": 3})
        self.assert_broken(attack(board(mon(ROCKETS_HITMONCHAN, (F,))), 0), 0, {"on_heads": False})
        self.assert_broken(attack(board(mon(MISTYS_HORSEA_50, (W, W))), 0, H), 1, {"lasting": False})
        self.assert_broken(attack(board(mon(HORSEA, (W,))), 0, H), 1, {"lasting": True})

    def test_lasting_effect_has_no_expiry(self):
        """期限のない効果は、はたらく番が過ぎても不変条件の違反にならない（ほかの効果は期限が過ぎると違反）。"""
        inked = attack(board(mon(MISTYS_HORSEA_50, (W, W))), 0, H)
        later = end_turn(end_turn(inked))
        self.assertEqual(later.turn_number, TURN + 3)
        self.assertEqual(check_invariants(later), [])
        self.assertEqual(len(later.players[1].active.persistent_effects), 1)


# ---------------------------------------------------------------- 先読み・書き出し・やり直し


class PreflightAndFormatTest(unittest.TestCase):

    def test_every_preflight_mode_gives_the_same_result(self):
        """v0.45 のワザは、どの先読みの方法でも、同じコインの結果で同じ結果（形式 11 の全体）。受け付けるかがコインの結果で変わらない。"""
        cases = [
            (board(mon(MISTYS_HORSEA_50, (W, W))), 0), (board(mon(KOGAS_EKANS, (G,)), mon(CHANSEY, (F,))), 0),
            (board(mon(KOGAS_GRIMER, (G,)), opponent_bench=(RATTATA, MACHOP)), 0), (board(mon(DARK_BLASTOISE, (W, W, W)), mon(CHANSEY, (F,))), 1),
            (board(mon(BLAINES_CHARIZARD, (R, R)), mon(CHANSEY, (F,))), 1), (board(mon(ROCKETS_HITMONCHAN, (F,))), 0),
            (board(mon(BROCKS_GEODUDE_40, (F,)), deck=[BROCKS_ONIX, F]), 0), (board(mon(GIOVANNIS_MEOWTH_40, (F, F)), mon(CHANSEY, (F,))), 1),
        ]
        for state, index in cases:
            for sides in ((H, H), (T, T), (H, T)):
                with self.subTest(card=state.cards[state.players[0].active.card].card_id, sides=sides):
                    results = {mode: full(attack(state, index, *sides, mode=mode)) for mode in PREFLIGHT_MODES}
                    self.assertEqual(len({repr(r) for r in results.values()}), 1)

    def test_new_persistent_effects_are_written_in_format_8_and_later(self):
        """新しい持続する効果（かたくなる・期限のない手順 4・倍数とコインのある返す効果）は形式 8 から書き出す（形式 7 は ``ValueError``）。"""
        made = {
            "zero_damage_below": attack(board(mon(ONIX, (F, F))), 1),
            "attack_coin_check": attack(board(mon(MISTYS_HORSEA_50, (W, W))), 0, H),
            RETALIATION_RECEIVED_SCALED_KIND: attack(board(mon(ROCKETS_HITMONCHAN, (F,))), 0),
        }
        for kind, state in made.items():
            with self.subTest(kind=kind):
                audited(self, state)
                written = [e for p in state_to_dict(state, format_version=8)["players"] for x in [p["active"], *p["bench"]] if x
                           for e in x.get("persistent_effects", [])]
                self.assertEqual([e["effect"] for e in written], [kind])
                with self.assertRaises(ValueError):
                    state_to_dict(state, format_version=7)
                for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
                    self.assertEqual(full(copied), full(state))

    def test_fixed_retaliation_and_attack_checks_keep_the_old_shape(self):
        """ほのおのかべ・こうらがえし・えんまく・すなかけの書き出しとログは v0.44 と同じ形（v0.45 の項目は書かない）。"""
        self.assertEqual(Retaliation(0, 0, 1, 2, 0, 10).terms(), ("fixed", 10))
        self.assertEqual(Retaliation(0, 0, 1, 2, 1, None, RETALIATION_RECEIVED).terms(), (RETALIATION_RECEIVED, None))
        self.assertFalse(AttackCoinCheck(0, 0, 1, 2).lasting)
        state = attack(board(mon(HORSEA, (W,))), 0, H)
        added = events(state, 0, "persistent_effect_added")[0]
        self.assertNotIn("lasting", added)
        written = state_to_dict(state, format_version=8)["players"][1]["active"]["persistent_effects"][0]
        self.assertNotIn("lasting", written)


# ---------------------------------------------------------------- 正式な対戦開始からの対戦


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.45 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.45 の 5 組を 4 seed ずつ（席を入れかえて 40 局）。どれも監査の失敗（やり直し・不変条件・ログ・書き出し）・想定外の拒否・内部エラーがなく、
        15 枚のどのワザも 1 度は使われる。じりょくせんのつけかえ・てつだうふり・たすけをよぶのベンチ・クロスカウンターの「おもて」と「うら」・かたくなるで 0 に
        なったダメージも起こる（勝敗は判断に使わない）。"""
        from tools import existing_effect_games as games

        results = games.run(range(4), pairings=games.PAIRINGS_V0_45)
        used, totals = set(), {}
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"))
                for card, uses in game.get("card_uses", {}).items():
                    used |= {(card, int(k.split("#")[1])) for k in uses if re.fullmatch(r"attack#\d", k)}
                    for key, count in uses.items():
                        totals[(card, key)] = totals.get((card, key), 0) + count
        self.assertEqual(set(EXPECTED) - used, set())
        for card, key in ((DARK_MAGNETON, "move_opponent_energy#1"), (GIOVANNIS_MEOWTH_40, "take_deck_top#0"), (BROCKS_GEODUDE_40, "bench_from_deck#0"),
                          (ROCKETS_HITMONCHAN, "retaliation_heads"), (ROCKETS_HITMONCHAN, "retaliation_skipped_coin_tails"), (ONIX, "zeroed_damage"),
                          (MISTYS_HORSEA_50, "gave_attack_coin_check")):
            with self.subTest(card=card, key=key):
                self.assertGreater(totals.get((card, key), 0), 0)


if __name__ == "__main__":
    unittest.main()
