"""v0.43: 宣言して使う特殊能力 6 つと、場に出たときに使う特殊能力 3 つを持つ 9 枚（docs/declared-entry-powers-v0.43.md）。

わるいクサイハナ（PMCG4-006。［くさいかふん］）・スリープ（PMCG4-033。［えんかくさいみん］）・ヒトカゲ（PMCG4-012。［ほのおをもらう］）・エリカのマダツボミ
（PMCG5-010。［ようぶんきゅうしゅう］）・マチスのレアコイル（PMCG5-040。［エナジーチャージ］）・わるいハクリュー（PMCG4-052。［しんかのひかり］）と、場に出たときに
使う わるいゴルバット（PMCG4-009。［こっそりかみつく］）・わるいヤドラン（PMCG4-036。［つりあげる］）・わるいカイリュー（PMCG4-053。［てしたをよぶ］）。どれも
kyuura データの採用（処理に使う文面は kyuura の印刷の文面。採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合。ガイドブックは読んでいない。

根拠にした既存の記録: p.311・p.323（特殊能力の使い方。エンジンの v0.5 の記録）・p.309（ワザの最中に特殊能力を宣言しない）・p.322（特殊状態の重複）・
CR-COUNTERATTACK-IS-POWER-DAMAGE・CR-RESTLESS-SLEEP-NOT-ATTACK-CALCULATION（特殊能力によるダメージはワザのダメージの計算をしない）・GR-2000-P323-KNOCKOUT（きぜつ）と、
エンジンの v0.5（エナジートランス）・v0.8（かがくへんかガス）・v0.24（見せて手札に加える）・v0.25（ポケモン育て屋さん）・v0.31（HC10）・v0.32（山札からベンチに出す）・
v0.42（特殊能力の決定・再開・使用後の処理）の記録。新しい未解決は PW3（``UNRESOLVED_POWER_ZERO_CARDS``）・PW4（``UNRESOLVED_ENTRY_POWER_DURING_ATTACK``）。
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import pickle
import unittest
from unittest import mock

from kyuura_engine import (
    EndTurn,
    EngineError,
    EvolvePokemon,
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, read_extract
from kyuura_engine.conditions import CONFUSION, SLEEP
from kyuura_engine.decisions import (
    BENCH_FROM_DECK,
    ENTRY_POWER,
    MOVE_ENERGY,
    PROMOTE_ACTIVE,
    RECOVER_POKEMON,
    SEARCH_DECK,
    SELECT_POKEMON,
    TAKE_PRIZE,
)
from kyuura_engine.resolution import PREFLIGHT_MODES, programs, v013_checks
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.state import Phase
from scripts import check_card_sources as cs
from scripts.extract_kyuura_cards import PREVIOUS_KYUURA_COMMIT as ADOPTED_COMMIT  # v0.69: 採用したときのデータのコミット（採用の記録は書き換えない）
from tests.helpers import (
    V0_69_STOP_CODE_ISSUES,
    kyuura_records_since_v0_69,
    ATTACK_TYPES_SINCE_V0_17,
    BULBASAUR,
    CHARIZARD,
    CHARMANDER,
    CHARMELEON,
    CLEFABLE,
    CLEFAIRY,
    DARK_DRAGONAIR,
    DARK_DRAGONITE,
    DARK_GLOOM,
    DARK_GOLBAT,
    DARK_SLOWBRO,
    DEFENDER,
    DRAGONAIR,
    DRATINI,
    DROWZEE,
    ERIKAS_BELLSPROUT,
    ERIKAS_BELLSPROUT_40,
    ERIKAS_CLEFABLE,
    ERIKAS_CLEFAIRY,
    ERIKAS_GLOOM,
    ERIKAS_ODDISH,
    ERIKAS_VILEPLUME,
    FIGHTING,
    FIRE,
    FOSSIL_ZUBAT,
    GASTLY,
    GIOVANNIS_MACHAMP,
    GIOVANNIS_MACHOKE,
    GIOVANNIS_MACHOP,
    GLOOM,
    GOLBAT,
    GRASS,
    GRIMER,
    HAUNTER,
    HITMONCHAN,
    JUNGLE_ODDISH,
    LIGHTNING,
    LT_SURGES_MAGNEMITE,
    LT_SURGES_MAGNEMITE_30,
    LT_SURGES_MAGNETON,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MAGNEMITE,
    MAGNETON,
    MEWTWO,
    MISTYS_PSYDUCK,
    MUK,
    POKEMON_BREEDER,
    POTION,
    PSYCHIC,
    RATTATA,
    ROCKET_CHARMANDER,
    ROCKET_DRATINI,
    ROCKET_DROWZEE,
    ROCKET_ODDISH,
    ROCKET_SLOWPOKE,
    ROCKET_ZUBAT,
    SABRINAS_SLOWPOKE,
    SANDSHREW,
    SLOWBRO,
    SLOWPOKE,
    V0_43_POKEMON,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.test_barrier_resume_coin_bonus_v0_34 import assert_stops, events, first, full, play

ROOT = pathlib.Path(__file__).resolve().parent.parent
TURN = 7
DOC = ROOT / "docs" / "declared-entry-powers-v0.43.md"
F, W, G, P, R, L = FIGHTING, WATER, GRASS, PSYCHIC, FIRE, LIGHTNING
BELOW = {DARK_GLOOM: ROCKET_ODDISH, LT_SURGES_MAGNETON: LT_SURGES_MAGNEMITE, DARK_DRAGONAIR: ROCKET_DRATINI, DARK_GOLBAT: ROCKET_ZUBAT,
         DARK_SLOWBRO: ROCKET_SLOWPOKE, DARK_DRAGONITE: [ROCKET_DRATINI, DARK_DRAGONAIR], MACHAMP: [MACHOP, MACHOKE],
         GIOVANNIS_MACHAMP: [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE], MUK: GRIMER, HAUNTER: GASTLY, ERIKAS_VILEPLUME: [ERIKAS_ODDISH, ERIKAS_GLOOM],
         CHARIZARD: [CHARMANDER, CHARMELEON], ERIKAS_CLEFABLE: ERIKAS_CLEFAIRY, CLEFABLE: CLEFAIRY}
# どのワザも使えるエネルギー（無色は別のタイプで払う）
ENERGY = {DARK_GLOOM: (G, G), ROCKET_DROWZEE: (P, F), ROCKET_CHARMANDER: (R,), ERIKAS_BELLSPROUT_40: (G,), LT_SURGES_MAGNETON: (L, L, L, F),
          DARK_DRAGONAIR: (F, F, F), DARK_GOLBAT: (G, G), DARK_SLOWBRO: (P, P), DARK_DRAGONITE: (F, F, F, F), ERIKAS_CLEFAIRY: (F, F)}
# 登録の実装の型と値（カード id, ワザの位置）
EXPECTED = {
    (DARK_GLOOM, 0): (E.PoisonOpponent, {}),
    (ROCKET_DROWZEE, 0): (E.SleepOpponent, {}),
    (ROCKET_CHARMANDER, 0): (E.DamageOnly, {}),
    (ERIKAS_BELLSPROUT_40, 0): (E.ChooseOpponentBenchDamage, {"damage": 10, "requires_bench": False}),
    (LT_SURGES_MAGNETON, 0): (E.SelfDamageOnTails, {"self_damage": 20}),
    (DARK_DRAGONAIR, 0): (E.CoinBonusDamage, {"bonus": 20}),
    (DARK_GOLBAT, 0): (E.ChooseOpponentPokemonDamage, {"damage": 20}),
    (DARK_SLOWBRO, 0): (E.FailOnTailsDamage, {"coins": 1}),
    (DARK_DRAGONITE, 0): (E.FailOnTailsDamage, {"coins": 1}),
}
# 特殊能力の登録（カード id → (型, 値, 自分の番ごとに 1 回か, 処理で「きぜつ」させうるか, 場に出たときに使うなら「手札から」だけか（宣言する特殊能力は None））
POWERS = {
    DARK_GLOOM: (E.CoinConditionOnEitherActive, {"condition": CONFUSION}, True, False, None),  # ［くさいかふん］
    ROCKET_DROWZEE: (E.CoinConditionOnEitherActive, {"condition": SLEEP}, True, False, None),  # ［えんかくさいみん］
    ROCKET_CHARMANDER: (E.TakeEnergyToSelf, {"energy_type": EnergyType.FIRE}, True, False, None),  # ［ほのおをもらう］
    ERIKAS_BELLSPROUT_40: (E.TakeEnergiesToSelf, {"energy_type": EnergyType.GRASS, "max_cards": 2}, True, False, None),  # ［ようぶんきゅうしゅう］
    LT_SURGES_MAGNETON: (E.ChargeBenchEnergyToSelf, {"energy_type": EnergyType.LIGHTNING}, False, False, None),  # ［エナジーチャージ］
    DARK_DRAGONAIR: (E.SearchEvolutionCardToHand, {}, True, False, None),  # ［しんかのひかり］
    DARK_GOLBAT: (E.DamageOpponentPokemonOnEntry, {"amount": 10}, False, True, True),  # ［こっそりかみつく］
    DARK_SLOWBRO: (E.RecoverPokemonFromDiscardOnEntry, {"max_cards": 3}, False, False, True),  # ［つりあげる］
    DARK_DRAGONITE: (E.BenchBasicsFromDeckOnEntry, {"max_cards": 2}, False, False, False),  # ［てしたをよぶ］
}
# pcg-search.com の対象の版（サイトの一覧の番号）と、違いのあった欄
EDITIONS = {DARK_GLOOM: "006/065", ROCKET_DROWZEE: "036/065", ROCKET_CHARMANDER: "012/065", ERIKAS_BELLSPROUT_40: "010/096", LT_SURGES_MAGNETON: "039/096",
            DARK_DRAGONAIR: "052/065", DARK_GOLBAT: "004/065", DARK_SLOWBRO: "035/065", DARK_DRAGONITE: "053/065"}
DIFFERENCES = {DARK_GOLBAT: ["pokemon.powers[0].text.ja"]}
PW3 = "UNRESOLVED_POWER_ZERO_CARDS"
PW4 = "UNRESOLVED_ENTRY_POWER_DURING_ATTACK"


def mon(card, energy=None, **extra):
    spec = {"card": card, "energy": list(ENERGY.get(card, ()) if energy is None else energy), **extra}
    if BELOW.get(card) is not None and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), deck=None, hand=(), discard=(), opponent_hand=(), turn=TURN,
          prizes=6):
    def spec(b):
        return mon(b, ()) if isinstance(b, str) and b in BELOW else b

    me = {"active": active, "bench": [spec(b) for b in bench], "hand": list(hand), "discard": list(discard), "prizes": prizes}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent or mon(HITMONCHAN, (F, F)), "bench": [spec(b) for b in opponent_bench], "hand": list(opponent_hand)}
    return build_test_state([me, them], turn_number=turn)


def snapshot(state):
    return full(state), [dict(e) for e in state.log], repr(state.rng.getstate())


def pid_of(state, player, card, nth=0):
    return [p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card][nth]


def pokemon_of(state, pid):
    return state.find_pokemon(pid)[1]


def card_of(state, player, card, zone="hand", nth=0):
    return [u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card][nth]


def cards_in(state, player, zone):
    return [state.cards[u].card_id for u in getattr(state.players[player], zone)]


def answer(state, choices):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)))


def power(state, pokemon, *sides, player=0, **choices):
    state = with_coin_results(state, *sides) if sides else state
    return apply_kernel(state, UsePokemonPower(player, pokemon, 0, **choices))


def attack(state, index, *sides, answers=(), player=0, mode="derived"):
    return play(with_coin_results(state, *sides) if sides else state, UseAttack(player, index), answers, mode=mode)


def evolve(state, card, target_card, *, player=0):
    """手札の ``card`` を、場の ``target_card`` のポケモン（最初の 1 匹）に重ねる（通常の進化の操作）。"""
    return apply_kernel(state, EvolvePokemon(player, card_of(state, player, card), pid_of(state, player, target_card)))


def assert_rejected(test, state, command, code, exception=EngineError):
    before = snapshot(state)
    with test.assertRaises(exception) as raised:
        apply_kernel(state, command)
    test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def card_count(state, player):
    """プレイヤーのカードの枚数（ゾーンのすべて。カードの保存則）。"""
    p = state.players[player]
    in_play = sum(len(x.cards()) + len(x.energy) + len(x.trainers) for x in p.in_play())
    return len(p.hand) + len(p.deck) + len(p.discard) + len(p.prizes) + in_play


def kinds(state, since):
    return [e["kind"] for e in state.log[since:]]


def with_context(decision, **changes):
    """決定の ``context`` の値を置きかえた決定（不変条件のテスト）。"""
    context = dict(decision.context)
    for key, value in changes.items():
        if value is None:
            context.pop(key, None)
        else:
            context[key] = value
    return dataclasses.replace(decision, context=tuple(context.items()))


# ---------------------------------------------------------------- 登録・写し・記録


class CardDataTest(unittest.TestCase):
    """9 枚の登録・写し・採用の記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_nine_requested_cards(self):
        """対象は依頼の 9 枚。写しの組 pool_v0_43 は 9 枚で、どれも対戦に使える（ワザだけでなく、特殊能力も登録したカード全体が対応）。同じ名前の別のカード
        （スリープ・ヒトカゲ・エリカのマダツボミ）は別の id・別のワザで、名前の似た別のカード（クサイハナ・レアコイル・ハクリュー・ゴルバット・ヤドラン・
        カイリュー）は別の名前。"""
        self.assertEqual(len(V0_43_POKEMON), 9)
        self.assertEqual(list(read_extract()["pool_v0_43"]), list(V0_43_POKEMON))
        for card in V0_43_POKEMON:
            with self.subTest(card=card):
                self.assertTrue(self.pool.is_playable(card))
                self.assertEqual(len(self.pool.get(card).powers), 1)
        for ours, other in ((ROCKET_DROWZEE, DROWZEE), (ROCKET_CHARMANDER, CHARMANDER), (ERIKAS_BELLSPROUT_40, ERIKAS_BELLSPROUT)):
            with self.subTest(card=ours, other=other):
                self.assertEqual(self.pool.get(ours).name_ja, self.pool.get(other).name_ja)
                self.assertNotEqual([a.name_ja for a in self.pool.get(ours).attacks], [a.name_ja for a in self.pool.get(other).attacks])
                self.assertFalse(self.pool.get(other).powers)
        for ours, other in ((DARK_GLOOM, GLOOM), (DARK_GLOOM, ERIKAS_GLOOM), (LT_SURGES_MAGNETON, MAGNETON), (DARK_DRAGONAIR, DRAGONAIR),
                            (DARK_GOLBAT, GOLBAT), (DARK_SLOWBRO, SLOWBRO), (DARK_DRAGONITE, "PMCG3-043")):
            with self.subTest(card=ours, other=other):
                self.assertNotEqual(self.pool.get(ours).name_ja, self.pool.get(other).name_ja)

    def test_without_the_power_registration_the_card_is_not_supported(self):
        """ワザだけを登録して、特殊能力を持つカードを対応と数えない: 特殊能力の登録を除いた登録表では、9 枚のどれもデッキに入らない（分類が未対応）。"""
        from kyuura_engine.cards import pool_from_extract

        keys = [E.PowerKey(card, 0) for card in V0_43_POKEMON]
        effects = E.DEFAULT_EFFECTS.without_powers("test-no-v043-powers", keys)
        pool = pool_from_extract(read_extract(), effects)
        for card in V0_43_POKEMON:
            with self.subTest(card=card):
                self.assertFalse(pool.is_playable(card))
                self.assertTrue(all(a.supported for a in pool.get(card).attacks))

    def test_every_attack_is_registered_with_the_expected_implementation(self):
        """9 のワザがどれも登録され、型と値が説明に合う。説明文のあるワザは、写しの文面（照合用）と処理に使う文面（kyuura の印刷の文面）が同じ。"""
        attacks = [(card, a.index) for card in V0_43_POKEMON for a in self.pool.get(card).attacks]
        self.assertEqual(sorted(attacks), sorted(EXPECTED))
        self.assertEqual(len(attacks), 9)
        for (card, index), (cls, values) in EXPECTED.items():
            with self.subTest(card=card, index=index):
                entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
                self.assertIs(type(entry.effect), cls)
                for name, value in values.items():
                    self.assertEqual(getattr(entry.effect, name), value)
                printed = self.pool.get(card).attacks[index]
                self.assertEqual((entry.name_ja, entry.text_ja), (printed.name_ja, printed.text_ja))
                if printed.text_ja:
                    self.assertEqual(entry.play_text_ja, printed.text_ja)
                self.assertEqual(entry.effect.check(printed), [])

    def test_every_power_is_registered(self):
        """9 つの特殊能力がどれも宣言して使う特殊能力として登録され、自分の番ごとに 1 回か・処理で「きぜつ」させうるか・場に出たときに使うか（使う経路）が
        説明に合う。エナジーチャージは日本語の説明に回数の制限がないので数えない。処理に使う文面は kyuura の印刷の文面。"""
        for card, (cls, values, once, knocks, from_hand_only) in POWERS.items():
            definition = self.pool.get(card)
            with self.subTest(card=card):
                [printed] = definition.powers
                entry = E.DEFAULT_EFFECTS.power_entry(card, 0)
                self.assertIs(type(entry.effect), cls)
                for name, value in values.items():
                    self.assertEqual(getattr(entry.effect, name), value)
                self.assertEqual((entry.effect.declared, entry.effect.once_per_turn, entry.effect.may_knock_out), (True, once, knocks))
                self.assertEqual(isinstance(entry.effect, E.EntryPower), from_hand_only is not None)
                if from_hand_only is not None:
                    self.assertEqual(entry.effect.from_hand_only, from_hand_only)
                self.assertEqual((entry.name_ja, entry.text_ja), (printed.name_ja, printed.text_ja))
                self.assertEqual(entry.play_text_ja, printed.text_ja)
                self.assertEqual(entry.source, "kyuura data/cards.json")
                self.assertEqual(entry.effect.check(printed), [])
        self.assertNotIn("自分の番ごとに1回", self.pool.get(LT_SURGES_MAGNETON).powers[0].text_ja)
        # 場に出たときの「手札から出した時」「手札から場に出した時」と「場に出た時」
        self.assertIn("手札から出した時", self.pool.get(DARK_GOLBAT).powers[0].text_ja)
        self.assertIn("手札から場に出した時", self.pool.get(DARK_SLOWBRO).powers[0].text_ja)
        self.assertIn("場に出た時", self.pool.get(DARK_DRAGONITE).powers[0].text_ja)
        self.assertNotIn("手札から", self.pool.get(DARK_DRAGONITE).powers[0].text_ja)

    def test_power_text_checks_reject_other_wording(self):
        """特殊能力の実装の ``check`` は、登録の値と説明の書き方を照らす（ほかのタイプ・枚数・ダメージは受け付けない）。"""
        cases = ((ROCKET_CHARMANDER, E.TakeEnergyToSelf(EnergyType.WATER)), (ERIKAS_BELLSPROUT_40, E.TakeEnergiesToSelf(EnergyType.GRASS, 3)),
                 (LT_SURGES_MAGNETON, E.ChargeBenchEnergyToSelf(EnergyType.WATER)), (DARK_GOLBAT, E.DamageOpponentPokemonOnEntry(20)),
                 (DARK_SLOWBRO, E.RecoverPokemonFromDiscardOnEntry(2)), (DARK_DRAGONITE, E.BenchBasicsFromDeckOnEntry(3)),
                 (DARK_GLOOM, E.CoinConditionOnEitherActive(SLEEP)), (ROCKET_DROWZEE, E.CoinConditionOnEitherActive(CONFUSION)))
        for card, effect in cases:
            with self.subTest(card=card, effect=effect):
                self.assertTrue(effect.check(self.pool.get(card).powers[0]))
        with self.assertRaises(ValueError):
            E.CoinConditionOnEitherActive("poison")
        # ほかのカードの特殊能力の文面も受け付けない
        self.assertTrue(E.SearchEvolutionCardToHand().check(self.pool.get(DARK_GOLBAT).powers[0]))

    def test_new_attack_type_is_a_kernel_program_outside_the_v013_contract(self):
        """v0.43 のワザの型（相手の場のポケモンを 1 匹選ぶダメージ）は解決の基盤の要素の並び（``programs.BUILDERS``）で処理し、v0.13 の約束（``resolve``・
        ``resume``）を上書きしない。``v013_checks.VERIFIED`` に入れない。"""
        cls = E.ChooseOpponentPokemonDamage
        self.assertIn(cls, programs.BUILDERS)
        self.assertIn(cls, ATTACK_TYPES_SINCE_V0_17)
        self.assertNotIn(cls, v013_checks.VERIFIED)
        self.assertIs(cls.resolve, E.AttackEffect.resolve)
        self.assertIs(cls.resume, E.AttackEffect.resume)
        # 説明の書き方（「(「弱点・抵抗力」に関係なく)」）と量を照らす
        printed = self.pool.get(DARK_GOLBAT).attacks[0]
        self.assertEqual(cls(20).check(printed), [])
        self.assertTrue(cls(30).check(printed))
        self.assertTrue(cls(20).check(self.pool.get(ERIKAS_BELLSPROUT_40).attacks[0]))

    def test_opponent_effect_elements_match_the_programs(self):
        for (card, index), _ in EXPECTED.items():
            effect = E.DEFAULT_EFFECTS.attack_entry(card, index).effect
            with self.subTest(card=card, index=index):
                program = programs.BUILDERS[type(effect)](effect)
                self.assertEqual(set(effect.opponent_effect_elements), set(programs.opponent_effect_elements(program)))

    def test_adoption_records_and_external_checks(self):
        """9 枚はどれも kyuura データの採用の記録を持ち、pcg-search.com の同じ版のページと照合した（特殊能力の欄も）。違いはわるいゴルバットの特殊能力の書き方
        （「手札から出した時」と「手札から場に出した時」）だけで、処理に影響しない（論点として記録した）。処理に使う文面の根拠は、特殊能力と説明文のあるワザごと
        （kyuura の印刷の文面）。過去の原典照合の記録には入れない。"""
        sources = cs.load_sources()["cards"]
        verification = json.loads((ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8"))["cards"]
        links = cs.load_links()["latest_descriptions"]
        for card in V0_43_POKEMON:
            with self.subTest(card=card):
                record = sources[card]
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"]),
                                 ("kyuura_data", "adopted", ADOPTED_COMMIT, kyuura_records_since_v0_69(card)))  # v0.69: 研究の基準を上げて加わった kyuura の記録（tests/helpers.py の V0_69_KYUURA_RECORDS_ADDED）
                expected = {f"attack/{a.index}" for a in self.pool.get(card).attacks if a.text_ja} | {"power/0"}
                self.assertEqual(set(record["play_text"]), expected)
                for target, basis in record["play_text"].items():
                    self.assertEqual(basis, "kyuura_printed_text")
                    self.assertIn(f"{card}/{target}", links["adopted_printed_text"])
                [check] = record["external_checks"]
                self.assertEqual((check["site"], check["edition"]["list_number"]), ("pcg-search.com", EDITIONS[card]))
                self.assertIn("pokemon.powers[0].text.ja", check["checked_fields"])
                if card in DIFFERENCES:
                    self.assertEqual(check["result"], "differences")
                    self.assertEqual([d["field"] for d in check["differences"]], DIFFERENCES[card])
                    self.assertFalse(any(d["affects_behavior"] for d in check["differences"]))
                    [issue] = record["issues"]
                    self.assertFalse(issue["affects_behavior"])
                else:
                    self.assertEqual((check["result"], check["differences"]), ("match", []))
                self.assertNotIn(card, verification)

    def test_no_card_specific_branch_in_the_engine(self):
        """engine.py・resolution/ に v0.43 のカード id での分岐を加えていない（効果の型・特殊能力の型の項目で表す）。"""
        for path in [ROOT / "kyuura_engine" / "engine.py", *(ROOT / "kyuura_engine" / "resolution").glob("*.py")]:
            text = path.read_text(encoding="utf-8")
            for card in V0_43_POKEMON:
                with self.subTest(path=path.name, card=card):
                    self.assertNotIn(card, text)

    def test_new_and_reused_questions(self):
        """新しい停止コードは PW3・PW4 の 2 つ（研究の対応表では kyuura の未解決の一覧にない）。PW3 は 0 枚になる 3 つの特殊能力（ようぶんきゅうしゅう・
        しんかのひかり・てしたをよぶ）で共通の 1 つの問い（カードごとに分けない）。ほかは既存のコード（HC10・UNRESOLVED_EVOLUTION_HP）を使う。"""
        links = cs.load_links()["stop_codes"]
        for code, ruling in ((PW3, "PW3"), (PW4, "PW4")):
            entry = links[code]
            self.assertEqual((entry["kyuura_disposition"], entry["kyuura_issue"], entry["engine_rulings"][0]["ruling_id"]),
                             ("issue", V0_69_STOP_CODE_ISSUES[code], ruling))  # v0.69: kyuura が論点に結んだ（v0.68 までは not_in_kyuura。tests/helpers.py の V0_69_STOP_CODE_ISSUES）
            self.assertEqual(entry["engine_rulings"][0]["document"], "docs/declared-entry-powers-v0.43.md")
        self.assertEqual(QUESTIONS["entry_power_during_attack"].code, PW4)
        self.assertEqual(QUESTIONS["evolution_hp_every_card"].code, "UNRESOLVED_EVOLUTION_HP")
        self.assertIn("UNRESOLVED_ENERGY_BURN_TRANSFER", links)
        self.assertEqual(E.POWER_ZERO_CARDS_CODE, PW3)
        zero_card_powers = {type(E.DEFAULT_EFFECTS.power_entry(card, 0).effect) for card in (ERIKAS_BELLSPROUT_40, DARK_DRAGONAIR, DARK_DRAGONITE)}
        self.assertEqual(len(zero_card_powers), 3)
        self.assertEqual(sum(1 for code in links if code == PW3), 1)


class EvolutionTest(unittest.TestCase):
    """進化先は、通常の進化の操作で、進化元の名前（完全一致。収録の弾で制限しない）のポケモンから進化する。"""

    PAIRS = ((DARK_GLOOM, JUNGLE_ODDISH), (DARK_GLOOM, ROCKET_ODDISH), (LT_SURGES_MAGNETON, LT_SURGES_MAGNEMITE), (LT_SURGES_MAGNETON, LT_SURGES_MAGNEMITE_30),
             (DARK_DRAGONAIR, DRATINI), (DARK_DRAGONAIR, ROCKET_DRATINI), (DARK_GOLBAT, FOSSIL_ZUBAT), (DARK_GOLBAT, ROCKET_ZUBAT),
             (DARK_SLOWBRO, SLOWPOKE), (DARK_SLOWBRO, ROCKET_SLOWPOKE))

    def test_evolves_from_every_card_with_the_exact_name(self):
        for card, base in self.PAIRS:
            with self.subTest(card=card, base=base):
                done = evolve(board({"card": base, "energy": []}, hand=[card]), card, base)
                if done.decision is not None:  # 場に出たときの特殊能力の使う機会は使わない
                    done = answer(done, ())
                self.assertEqual(done.cards[done.players[0].active.card].card_id, card)
        done = evolve(board(mon(DARK_DRAGONAIR, ()), hand=[DARK_DRAGONITE]), DARK_DRAGONITE, DARK_DRAGONAIR)
        done = answer(done, ())
        self.assertEqual(len(done.players[0].active.evolution_stack), 2)

    def test_names_that_only_look_alike_are_rejected(self):
        """エリカのナゾノクサからわるいクサイハナ・コイルからマチスのレアコイル・ナツメのヤドンからわるいヤドラン・ハクリューからわるいカイリューへは
        進化できない（名前が違う）。"""
        cases = ((DARK_GLOOM, {"card": ERIKAS_ODDISH, "energy": []}), (LT_SURGES_MAGNETON, {"card": MAGNEMITE, "energy": []}),
                 (DARK_SLOWBRO, {"card": SABRINAS_SLOWPOKE, "energy": []}), (DARK_DRAGONITE, {"card": DRAGONAIR, "energy": [], "evolved_from": DRATINI}))
        for card, spec in cases:
            with self.subTest(card=card, base=spec["card"]):
                state = board(spec, hand=[card])
                assert_rejected(self, state, EvolvePokemon(0, card_of(state, 0, card), state.players[0].active.pokemon_id),
                                "EVOLUTION_NAME_MISMATCH", IllegalActionError)


# ---------------------------------------------------------------- 宣言して使う特殊能力


class CoinConditionTest(unittest.TestCase):
    """わるいクサイハナの［くさいかふん］・スリープの［えんかくさいみん］（コインの「おもて」で相手の、「うら」で自分の対戦ポケモンを特殊状態にする）。"""

    CARDS = {DARK_GLOOM: "confused", ROCKET_DROWZEE: "asleep"}

    def test_heads_affects_the_opponent_and_tails_the_own_active(self):
        """コインは使ったプレイヤーが 1 枚（``source`` は ``power``）。特殊状態にするのは、その時点のバトル場のポケモン（このカードがベンチにいても）。ログは
        宣言 → コイン → ``special_condition``（``effect`` は特殊能力）。"""
        for card, flag in self.CARDS.items():
            with self.subTest(card=card):
                state = board(mon(RATTATA, ()), bench=(mon(card),))
                user = pid_of(state, 0, card)
                heads = power(state, user, H)
                self.assertEqual(kinds(heads, len(state.log)), ["pokemon_power", "coin_flip", "special_condition"])
                [coin] = events(heads, len(state.log), "coin_flip")
                self.assertEqual((coin["player"], coin["source"]), (0, "power"))
                [condition] = events(heads, len(state.log), "special_condition")
                self.assertEqual((condition["player"], condition["effect"]), (1, f"{card}@power0"))
                self.assertTrue(getattr(heads.players[1].active.conditions, flag))
                self.assertIsNone(heads.players[0].active.conditions.exclusive)
                tails = power(state, user, T)
                self.assertTrue(getattr(tails.players[0].active.conditions, flag))
                self.assertIsNone(tails.players[1].active.conditions.exclusive)
                self.assertEqual((heads.phase, tails.phase, heads.turn_number), (Phase.MAIN, Phase.MAIN, TURN))

    def test_tails_while_active_affects_the_card_itself(self):
        """このカードがバトル場にいて「うら」なら、このカード自身がその状態になる（その後は使えない特殊状態になる）。"""
        for card, flag in self.CARDS.items():
            with self.subTest(card=card):
                state = board(mon(card))
                done = power(state, pid_of(state, 0, card), T)
                self.assertTrue(getattr(done.players[0].active.conditions, flag))

    def test_once_per_turn_even_on_tails(self):
        """自分の番ごとに 1 回（宣言のときに記録する。「うら」でも使ったことになる）。次の自分の番には、また使える。"""
        for card in self.CARDS:
            with self.subTest(card=card):
                state = board(mon(RATTATA, ()), bench=(mon(card),))
                user = pid_of(state, 0, card)
                tails = power(state, user, T)
                self.assertEqual(tails.power_uses_this_turn, ((user, 0),))
                assert_rejected(self, tails, UsePokemonPower(0, user, 0), "POWER_ALREADY_USED", IllegalActionError)

    def test_status_restrictions_and_choices(self):
        """ねむり・マヒ・こんらんのこのカードは使えない（どくは使える）。選ぶものはない（``POWER_CHOICE_NOT_USED``）。"""
        for card in self.CARDS:
            for condition, code in (({"sleep": True}, "POKEMON_ASLEEP"), ({"paralysis": TURN - 1}, "POKEMON_PARALYZED"),
                                    ({"confusion": True}, "POKEMON_CONFUSED")):
                with self.subTest(card=card, code=code):
                    state = board(mon(card, **condition))
                    assert_rejected(self, state, UsePokemonPower(0, pid_of(state, 0, card), 0), code, IllegalActionError)
            with self.subTest(card=card, condition="poison"):
                state = board(mon(card, poison=10))
                self.assertTrue(events(power(state, pid_of(state, 0, card), H), len(state.log), "special_condition"))
            with self.subTest(card=card, choice="target"):
                state = board(mon(card))
                assert_rejected(self, state, UsePokemonPower(0, pid_of(state, 0, card), 0, target=state.players[1].active.pokemon_id),
                                "POWER_CHOICE_NOT_USED", IllegalActionError)

    def test_not_an_attack(self):
        """特殊能力はワザではない: こんらんのコイン・ワザのログはなく、番は終わらない。ワザを防ぐ効果（「ダメージを受けない」状態・「とうめい」）は
        関係しない（判定のコインもない）。ねむり・こんらんの重複は p.322 のとおり置きかわり、どくは消えない。"""
        state = board(mon(RATTATA, (), confusion=True), mon(HAUNTER, (), prevent_damage=TURN - 1, poison=10, confusion=True),
                      bench=(mon(ROCKET_DROWZEE),))
        done = power(state, pid_of(state, 0, ROCKET_DROWZEE), H)
        self.assertFalse({"attack", "confusion_check", "evade_check", "turn_end"} & set(kinds(done, len(state.log))))
        self.assertTrue(done.players[1].active.conditions.asleep)
        self.assertFalse(done.players[1].active.conditions.confused)
        self.assertIsNotNone(done.players[1].active.conditions.poison)
        self.assertEqual(check_invariants(done), [])

    def test_barrier_does_not_block_a_power(self):
        """「ワザをうけない」状態（ミュウツーの「バリアー」）は、ワザの効果だけを防ぐ。特殊能力のこんらんは受ける。"""
        state = build_test_state([{"active": mon(MEWTWO, (P, P, P)), "bench": [RATTATA]},
                                  {"active": mon(RATTATA, ()), "bench": [mon(DARK_GLOOM)]}], turn_number=TURN)
        barrier = play(state, UseAttack(0, 1), [first])
        self.assertEqual((barrier.current_player, barrier.phase), (1, Phase.MAIN))
        done = power(barrier, pid_of(barrier, 1, DARK_GLOOM), H, player=1)
        self.assertTrue(done.players[0].active.conditions.confused)


class EnergyMoveTest(unittest.TestCase):
    """ヒトカゲの［ほのおをもらう］（1 枚。コマンドで選ぶ）。つけかえは手札からつけることではない（通常の操作の回数を変えない）。"""

    def test_moves_one_fire_energy_onto_itself(self):
        state = board(mon(ROCKET_CHARMANDER, ()), bench=(mon(RATTATA, (R, W)),))
        rat = state.players[0].bench[0]
        done = power(state, pid_of(state, 0, ROCKET_CHARMANDER), energy=rat.energy[0], source=rat.pokemon_id)
        self.assertEqual(kinds(done, len(state.log)), ["pokemon_power", "move_energy"])
        [move] = events(done, len(state.log), "move_energy")
        self.assertEqual((move["energy"], move["from_pokemon_id"], move["to_pokemon_id"], move["power"]),
                         (rat.energy[0], rat.pokemon_id, pid_of(state, 0, ROCKET_CHARMANDER), f"{ROCKET_CHARMANDER}@power0"))
        self.assertEqual(done.players[0].active.energy, [rat.energy[0]])
        self.assertEqual(done.players[0].bench[0].energy, [rat.energy[1]])
        self.assertEqual(done.energy_attachments_this_turn, state.energy_attachments_this_turn)
        self.assertEqual(done.power_uses_this_turn, ((pid_of(state, 0, ROCKET_CHARMANDER), 0),))
        assert_rejected(self, done, UsePokemonPower(0, pid_of(state, 0, ROCKET_CHARMANDER), 0, energy=rat.energy[1], source=rat.pokemon_id),
                        "POWER_ALREADY_USED", IllegalActionError)

    def test_rejections(self):
        """「炎」エネルギーカードでない（``WRONG_ENERGY_TYPE``）・このカード自身から（``SAME_POKEMON``）・ついていない・相手のポケモン・選ぶものの不足と余分は
        拒否する（状態は変わらない）。"""
        state = board(mon(ROCKET_CHARMANDER, (R,)), mon(HITMONCHAN, (R, F)), bench=(mon(RATTATA, (R, W)),))
        me = pid_of(state, 0, ROCKET_CHARMANDER)
        rat = state.players[0].bench[0]
        own = state.players[0].active.energy[0]
        theirs = state.players[1].active
        assert_rejected(self, state, UsePokemonPower(0, me, 0, energy=rat.energy[1], source=rat.pokemon_id), "WRONG_ENERGY_TYPE", IllegalActionError)
        assert_rejected(self, state, UsePokemonPower(0, me, 0, energy=own, source=me), "SAME_POKEMON", IllegalActionError)
        assert_rejected(self, state, UsePokemonPower(0, me, 0, energy=own, source=rat.pokemon_id), "ENERGY_NOT_ATTACHED", IllegalActionError)
        assert_rejected(self, state, UsePokemonPower(0, me, 0, energy=theirs.energy[0], source=theirs.pokemon_id), "SOURCE_NOT_YOURS", IllegalActionError)
        assert_rejected(self, state, UsePokemonPower(0, me, 0, energy=rat.energy[0]), "POWER_CHOICE_MISSING", IllegalActionError)
        assert_rejected(self, state, UsePokemonPower(0, me, 0, energy=rat.energy[0], source=rat.pokemon_id, target=me), "POWER_CHOICE_NOT_USED",
                        IllegalActionError)

    def test_energy_burn_is_hc10(self):
        """この番に「エナジーバーン」で「炎」になっているエネルギーカード: もとが基本「炎」エネルギーカードなら当たる（どちらの読み方でも「炎」）。ほかの
        タイプのカードは、説明の「「炎」エネルギーカード」に当たるかが決められない（エナジートランスの HC10 と同じ問い・同じコード）。"""
        state = board(mon(ROCKET_CHARMANDER, ()), bench=(mon(CHARIZARD, (W, R)),))
        burned = power(state, pid_of(state, 0, CHARIZARD))
        charizard = burned.players[0].bench[0]
        me = pid_of(state, 0, ROCKET_CHARMANDER)
        assert_rejected(self, burned, UsePokemonPower(0, me, 0, energy=charizard.energy[0], source=charizard.pokemon_id),
                        "UNRESOLVED_ENERGY_BURN_TRANSFER", UnsupportedError)
        done = power(burned, me, energy=charizard.energy[1], source=charizard.pokemon_id)
        self.assertEqual(done.players[0].active.energy, [charizard.energy[1]])


class SoakUpTest(unittest.TestCase):
    """エリカのマダツボミの［ようぶんきゅうしゅう］（最大 2 枚を 1 回の使用で。決定で選ぶ）。0 枚になる場合は PW3。"""

    def test_moves_up_to_two_cards_in_one_use(self):
        """宣言 → 決定（``MOVE_ENERGY``。このカード以外の自分の場のポケモンについている基本「草」エネルギーカード。場の並び・ついている順。0〜2 枚）→ 選んだ
        カードを場の並びの順につけかえる（ログ ``move_energy`` を 1 枚ずつ）。1 回の使用で 2 枚（自分の番ごとに 1 回）。"""
        state = board(mon(RATTATA, (G, W)), bench=(mon(ERIKAS_BELLSPROUT_40, (G,)), mon(BULBASAUR, (G, G))))
        me = pid_of(state, 0, ERIKAS_BELLSPROUT_40)
        waiting = power(state, me)
        d = waiting.decision
        options = (state.players[0].active.energy[0], *state.players[0].bench[1].energy)
        self.assertEqual((d.kind, d.resume, d.player, d.options, d.min_choices, d.max_choices), (MOVE_ENERGY, "power", 0, options, 0, 2))
        self.assertEqual(waiting.power_uses_this_turn, ((me, 0),))
        self.assertEqual(check_invariants(waiting), [])
        done = answer(waiting, (options[2], options[0]))
        moves = events(done, len(waiting.log), "move_energy")
        self.assertEqual([m["energy"] for m in moves], [options[0], options[2]])
        self.assertEqual(len(pokemon_of(done, me).energy), 3)
        self.assertEqual((done.phase, done.turn_number), (Phase.MAIN, TURN))
        assert_rejected(self, done, UsePokemonPower(0, me, 0), "POWER_ALREADY_USED", IllegalActionError)
        one = answer(waiting, (options[1],))
        self.assertEqual(len(events(one, len(waiting.log), "move_energy")), 1)

    def test_zero_cards_is_pw3(self):
        """0 枚を選ぶ答えは決められない（PW3。決定は待ったまま）。選べるカードがなければ宣言の前に止める（回数も記録しない）。隣の止まらない場合: 選べるカードが
        1 枚（最大 1 枚）。"""
        state = board(mon(RATTATA, (G,)), bench=(mon(ERIKAS_BELLSPROUT_40, (G,)),))
        waiting = power(state, pid_of(state, 0, ERIKAS_BELLSPROUT_40))
        self.assertEqual(waiting.decision.max_choices, 1)
        assert_rejected(self, waiting, ResolveDecision(0, waiting.decision.id, ()), PW3, UnsupportedError)
        self.assertEqual(len(answer(waiting, waiting.decision.options).players[0].bench[0].energy), 2)
        none = board(mon(RATTATA, (W,)), bench=(mon(ERIKAS_BELLSPROUT_40, (G,)),))
        assert_rejected(self, none, UsePokemonPower(0, pid_of(none, 0, ERIKAS_BELLSPROUT_40), 0), PW3, UnsupportedError)

    def test_invalid_answers(self):
        state = board(mon(RATTATA, (G, G, G)), bench=(mon(ERIKAS_BELLSPROUT_40, ()),))
        waiting = power(state, pid_of(state, 0, ERIKAS_BELLSPROUT_40))
        d = waiting.decision
        assert_rejected(self, waiting, ResolveDecision(0, d.id, d.options), "INVALID_CHOICE_COUNT", IllegalActionError)
        assert_rejected(self, waiting, ResolveDecision(0, d.id, (d.options[0], d.options[0])), "DUPLICATE_CHOICE", IllegalActionError)
        assert_rejected(self, waiting, ResolveDecision(1, d.id, d.options[:1]), "NOT_YOUR_DECISION", IllegalActionError)
        assert_rejected(self, waiting, UseAttack(0, 0), "WRONG_PHASE", IllegalActionError)

    def test_energy_burn_is_hc10(self):
        """「エナジーバーン」で「炎」になっている基本「草」エネルギーカードは、選べるが選ぶと止める（HC10）。選べるカードがどれもそうなら宣言の前に止める。"""
        state = board(mon(RATTATA, (G,)), bench=(mon(ERIKAS_BELLSPROUT_40, ()), mon(CHARIZARD, (G,))))
        burned = power(state, pid_of(state, 0, CHARIZARD))
        waiting = power(burned, pid_of(state, 0, ERIKAS_BELLSPROUT_40))
        ambiguous = burned.players[0].bench[1].energy[0]
        self.assertEqual(waiting.decision.context_value("unresolved_choices"), (ambiguous,))
        assert_rejected(self, waiting, ResolveDecision(0, waiting.decision.id, (ambiguous,)), "UNRESOLVED_ENERGY_BURN_TRANSFER", UnsupportedError)
        self.assertTrue(events(answer(waiting, (state.players[0].active.energy[0],)), len(waiting.log), "move_energy"))
        only = board(mon(RATTATA, ()), bench=(mon(ERIKAS_BELLSPROUT_40, ()), mon(CHARIZARD, (G,))))
        burned = power(only, pid_of(only, 0, CHARIZARD))
        assert_rejected(self, burned, UsePokemonPower(0, pid_of(only, 0, ERIKAS_BELLSPROUT_40), 0), "UNRESOLVED_ENERGY_BURN_TRANSFER", UnsupportedError)


class EnergyChargeTest(unittest.TestCase):
    """マチスのレアコイルの［エナジーチャージ］（バトル場にいるときだけ。控えの「雷」を好きなだけ。回数の制限はない）。"""

    def test_moves_any_number_from_the_bench(self):
        state = board(mon(LT_SURGES_MAGNETON, ()), bench=(mon(RATTATA, (L, L, W)), mon(BULBASAUR, (L,))))
        me = pid_of(state, 0, LT_SURGES_MAGNETON)
        waiting = power(state, me)
        d = waiting.decision
        options = (*state.players[0].bench[0].energy[:2], state.players[0].bench[1].energy[0])
        self.assertEqual((d.kind, d.options, d.min_choices, d.max_choices), (MOVE_ENERGY, options, 1, 3))
        self.assertEqual(waiting.power_uses_this_turn, ())
        done = answer(waiting, options)
        self.assertEqual(len(events(done, len(waiting.log), "move_energy")), 3)
        self.assertEqual(len(done.players[0].active.energy), 3)
        assert_rejected(self, done, UsePokemonPower(0, me, 0), "NO_ENERGY_TO_MOVE", IllegalActionError)
        assert_rejected(self, waiting, ResolveDecision(0, d.id, ()), "INVALID_CHOICE_COUNT", IllegalActionError)

    def test_can_be_used_again_in_the_same_turn(self):
        """回数の制限は説明にないので、同じ番にもう一度使える（記録もしない）。"""
        state = board(mon(LT_SURGES_MAGNETON, ()), bench=(mon(RATTATA, (L, L)),))
        me = pid_of(state, 0, LT_SURGES_MAGNETON)
        once = answer(power(state, me), (state.players[0].bench[0].energy[0],))
        twice = answer(power(once, me), (state.players[0].bench[0].energy[1],))
        self.assertEqual((len(twice.players[0].active.energy), twice.power_uses_this_turn), (2, ()))

    def test_only_while_active(self):
        """ベンチでは使えない（``POKEMON_NOT_ACTIVE``）。バトル場のポケモンのエネルギーは選べない（控えだけ）。"""
        state = board(mon(RATTATA, (L,)), bench=(mon(LT_SURGES_MAGNETON, ()), mon(BULBASAUR, (L,))))
        assert_rejected(self, state, UsePokemonPower(0, pid_of(state, 0, LT_SURGES_MAGNETON), 0), "POKEMON_NOT_ACTIVE", IllegalActionError)
        none = board(mon(LT_SURGES_MAGNETON, (L,)), bench=(mon(RATTATA, (W,)),))
        assert_rejected(self, none, UsePokemonPower(0, pid_of(none, 0, LT_SURGES_MAGNETON), 0), "NO_ENERGY_TO_MOVE", IllegalActionError)
        asleep = board(mon(LT_SURGES_MAGNETON, (), sleep=True), bench=(mon(RATTATA, (L,)),))
        assert_rejected(self, asleep, UsePokemonPower(0, pid_of(asleep, 0, LT_SURGES_MAGNETON), 0), "POKEMON_ASLEEP", IllegalActionError)


class EvolutionaryLightTest(unittest.TestCase):
    """わるいハクリューの［しんかのひかり］（山札の進化カードを見せて手札に加え、山札を切る）。山札に進化カードがなければ PW3。"""

    def test_search_reveal_add_and_shuffle(self):
        """選べるものは山札の進化カード（uid の小さい順）。今進化できるかでしぼらない（エリカのピクシーは場にエリカのピッピがいなくても選べる）。たねポケモン・
        エネルギーは選べない。見せて手札に加え（``reveal_from_deck``。``power``）、山札を切る（``shuffle``。``power``）。"""
        state = board(mon(DARK_DRAGONAIR, ()), deck=(FIRE, DARK_DRAGONITE, RATTATA, ERIKAS_CLEFABLE, GRASS))
        me = pid_of(state, 0, DARK_DRAGONAIR)
        waiting = power(state, me)
        d = waiting.decision
        evolution = tuple(sorted(u for u in state.players[0].deck if state.cards[u].card_id in (DARK_DRAGONITE, ERIKAS_CLEFABLE)))
        self.assertEqual((d.kind, d.resume, d.options, d.min_choices, d.max_choices), (SEARCH_DECK, "power", evolution, 1, 1))
        self.assertEqual(kinds(waiting, len(state.log)), ["pokemon_power"])
        clefable = card_of(state, 0, ERIKAS_CLEFABLE, "deck")
        done = answer(waiting, (clefable,))
        self.assertEqual(kinds(done, len(waiting.log)), ["reveal_from_deck", "shuffle"])
        reveal, shuffle = events(done, len(waiting.log))
        self.assertEqual((reveal["card"], reveal["power"], shuffle["power"]), (clefable, f"{DARK_DRAGONAIR}@power0", f"{DARK_DRAGONAIR}@power0"))
        self.assertIn(ERIKAS_CLEFABLE, cards_in(done, 0, "hand"))
        self.assertEqual(sorted(done.players[0].deck), sorted(u for u in state.players[0].deck if u != clefable))
        self.assertEqual(card_count(done, 0), card_count(state, 0))
        assert_rejected(self, done, UsePokemonPower(0, me, 0), "POWER_ALREADY_USED", IllegalActionError)

    def test_no_evolution_card_is_pw3(self):
        """山札に進化カードがない（山札が 0 枚を含む）ときは、宣言の前に止める（PW3）。隣の止まらない場合: 進化カードが 1 枚。"""
        for deck in ((FIRE, RATTATA), ()):
            with self.subTest(deck=deck):
                state = board(mon(DARK_DRAGONAIR, ()), deck=deck)
                assert_rejected(self, state, UsePokemonPower(0, pid_of(state, 0, DARK_DRAGONAIR), 0), PW3, UnsupportedError)
        state = board(mon(DARK_DRAGONAIR, ()), deck=(FIRE, DARK_GOLBAT))
        self.assertEqual(len(power(state, pid_of(state, 0, DARK_DRAGONAIR)).decision.options), 1)


# ---------------------------------------------------------------- 場に出たときに使う特殊能力


class EntryPowerTest(unittest.TestCase):
    """場に出たときに 1 度だけ使える特殊能力の使う機会（決定 ``ENTRY_POWER``）・使わない・再開・もとの処理へのもどり方。"""

    def golbat(self, **extra):
        return board(mon(ROCKET_ZUBAT, (G, G)), mon(SANDSHREW, ()), hand=[DARK_GOLBAT], opponent_bench=(mon(RATTATA, ()),), **extra)

    def test_opportunity_after_evolving_from_the_hand(self):
        """手札から進化させたら、進化のすぐあとに持ち主に使うかを聞く（段階 DECISION。決定するのは持ち主。選べるものはそのポケモンの番号 1 つ・0〜1 個。
        再開先 ``"power"``。``context`` の ``"entry"`` は ``"hand"``）。待つ間はほかの操作をしない。書き出し（形式 10）と pickle で同じ状態にもどり、形式 1 は
        書き出せない。"""
        state = self.golbat()
        waiting = evolve(state, DARK_GOLBAT, ROCKET_ZUBAT)
        d = waiting.decision
        pid = waiting.players[0].active.pokemon_id
        self.assertEqual((waiting.phase, d.kind, d.resume, d.player, d.options, d.min_choices, d.max_choices),
                         (Phase.DECISION, ENTRY_POWER, "power", 0, (pid,), 0, 1))
        self.assertEqual(d.context_value("entry"), "hand")
        self.assertIsNone(d.context_value("return_to"))
        self.assertEqual(kinds(waiting, len(state.log)), ["evolve"])
        self.assertEqual(check_invariants(waiting), [])
        self.assertEqual(full(pickle.loads(pickle.dumps(waiting))), full(waiting))
        with self.assertRaises(ValueError):
            state_to_dict(waiting, format_version=1)
        for command, code in ((UseAttack(0, 0), "WRONG_PHASE"), (EndTurn(0), "WRONG_PHASE"), (UsePokemonPower(0, pid, 0), "WRONG_PHASE"),
                              (ResolveDecision(1, d.id, d.options), "NOT_YOUR_DECISION")):
            with self.subTest(command=command):
                assert_rejected(self, waiting, command, code, IllegalActionError)

    def test_decline_then_the_opportunity_is_gone(self):
        """使わない（0 個）を選ぶと、ログ ``entry_power_declined`` を残して番のプレイヤーの MAIN にもどる（回数の記録はない）。そのあと（同じ番・次の番）に
        ``UsePokemonPower`` では使えない（``POWER_NOT_USABLE_NOW``）。"""
        state = self.golbat()
        waiting = evolve(state, DARK_GOLBAT, ROCKET_ZUBAT)
        declined = answer(waiting, ())
        [event] = events(declined, len(waiting.log))
        self.assertEqual((event["kind"], event["power"], event["power_index"]), ("entry_power_declined", "こっそりかみつく", 0))
        self.assertEqual((declined.phase, declined.current_player, declined.power_uses_this_turn), (Phase.MAIN, 0, ()))
        pid = declined.players[0].active.pokemon_id
        assert_rejected(self, declined, UsePokemonPower(0, pid, 0), "POWER_NOT_USABLE_NOW", IllegalActionError)
        later = apply_kernel(apply_kernel(declined, EndTurn(0)), EndTurn(1))
        assert_rejected(self, later, UsePokemonPower(0, pid, 0), "POWER_NOT_USABLE_NOW", IllegalActionError)

    def test_accept_declares_once_and_cannot_be_used_again(self):
        """使うを選ぶと、宣言のログ ``pokemon_power``（``entry`` は ``"hand"``）→ 説明の処理（決定・再開は宣言する特殊能力と同じ）→ 番のプレイヤーの MAIN。
        同じ機会で 2 度は使えず（決定は 1 度だけ）、そのあとも ``UsePokemonPower`` では使えない。"""
        state = self.golbat()
        waiting = evolve(state, DARK_GOLBAT, ROCKET_ZUBAT)
        accepted = answer(waiting, waiting.decision.options)
        [declared] = events(accepted, len(waiting.log))
        self.assertEqual((declared["kind"], declared["entry"], declared["power"]), ("pokemon_power", "hand", "こっそりかみつく"))
        self.assertEqual((accepted.decision.kind, accepted.decision.resume), (SELECT_POKEMON, "power"))
        self.assertEqual(check_invariants(accepted), [])
        done = answer(accepted, (pid_of(state, 1, RATTATA),))
        self.assertEqual((done.phase, done.current_player, done.turn_number), (Phase.MAIN, 0, TURN))
        self.assertEqual(len([e for e in done.log if e["kind"] == "pokemon_power"]), 1)
        assert_rejected(self, done, UsePokemonPower(0, done.players[0].active.pokemon_id, 0), "POWER_NOT_USABLE_NOW", IllegalActionError)
        self.assertIn("attack", kinds(attack(done, 0, answers=[first]), len(done.log)))

    def test_no_opportunity_without_an_entry_power_or_under_chemical_gas(self):
        """場に出たときの特殊能力がない進化（わるいクサイハナ）・はたらいているかがくへんかガスに消されている（ベトベトン）なら、使う機会はない（決定を出さない）。"""
        plain = evolve(board(mon(ROCKET_ODDISH, ()), hand=[DARK_GLOOM]), DARK_GLOOM, ROCKET_ODDISH)
        self.assertEqual((plain.phase, plain.decision), (Phase.MAIN, None))
        gas = board(mon(ROCKET_ZUBAT, ()), mon(MUK, ()), hand=[DARK_GOLBAT])
        done = evolve(gas, DARK_GOLBAT, ROCKET_ZUBAT)
        self.assertEqual((done.phase, done.decision), (Phase.MAIN, None))
        self.assertEqual(kinds(done, len(gas.log)), ["evolve"])

    def test_the_invariants_check_the_opportunity(self):
        """使う機会の決定の不変条件: 経路（``entry``）・使うことを選ぶと止める選択・もどる先・決定の形・直前の進化のログを確かめる（壊すと違反を報告する）。"""
        waiting = evolve(self.golbat(), DARK_GOLBAT, ROCKET_ZUBAT)
        d = waiting.decision
        broken = {
            "route": with_context(d, entry="play"),
            "unresolved": with_context(d, unresolved_choices=d.options, unresolved_code=PW3, unresolved_reason="x"),
            "return_to": with_context(d, return_to=("trainer", 0, 1, POKEMON_BREEDER)),
            "form": dataclasses.replace(d, min_choices=1),
            "player": dataclasses.replace(d, player=1),
        }
        for name, decision in broken.items():
            with self.subTest(case=name):
                state = copy.deepcopy(waiting)
                state.decision = decision
                self.assertTrue(check_invariants(state))
        moved = copy.deepcopy(waiting)
        moved.log = moved.log[:-1]
        self.assertTrue(check_invariants(moved))


class SneakAttackTest(unittest.TestCase):
    """わるいゴルバットの［こっそりかみつく］（特殊能力によるダメージ。弱点・抵抗力・ワザのダメージの計算・ワザを防ぐ効果・ダメージを受けたときの効果は
    関係しない。HP 以上になったら特殊能力の処理のあとにきぜつ）。"""

    def use(self, opponent, opponent_bench=(), *, target=None, prizes=6, hand=()):
        state = board(mon(ROCKET_ZUBAT, (G, G)), opponent, hand=[DARK_GOLBAT, *hand], opponent_bench=opponent_bench, prizes=prizes)
        waiting = answer(evolve(state, DARK_GOLBAT, ROCKET_ZUBAT), (state.players[0].active.pokemon_id,))
        self.assertEqual(waiting.decision.options, tuple(p.pokemon_id for p in state.players[1].in_play()))
        chosen = target(state) if target else state.players[1].active.pokemon_id
        return state, answer(waiting, (chosen,))

    def test_ten_damage_without_weakness_resistance_or_attack_calculation(self):
        """相手の場のポケモン（バトル場・ベンチ）を 1 匹選び 10（弱点 草のサンドにも 10）。ディフェンダー・「ダメージを受けない」状態は関係しない（ワザのダメージの
        計算ではない）。ログ ``power_damage``。"""
        state, done = self.use(mon(SANDSHREW, (), prevent_damage=TURN - 1, trainers=[(DEFENDER, TURN)]), (mon(SANDSHREW, ()),))
        self.assertEqual(done.players[1].active.damage, 10)
        [hit] = events(done, len(state.log), "power_damage")
        self.assertEqual((hit["target_player"], hit["amount"], hit["total_damage"], hit["knocked_out"], hit["power"]),
                         (1, 10, 10, False, f"{DARK_GOLBAT}@power0"))
        self.assertFalse(events(done, len(state.log), "damage") + events(done, len(state.log), "damage_prevented"))
        _, bench = self.use(mon(HITMONCHAN, ()), (mon(SANDSHREW, ()),), target=lambda s: s.players[1].bench[0].pokemon_id)
        self.assertEqual((bench.players[1].bench[0].damage, bench.players[1].active.damage), (10, 0))
        self.assertEqual((done.phase, done.turn_number), (Phase.MAIN, TURN))

    def test_attack_protections_and_damage_reactions_do_not_apply(self):
        """「とうめい」（ゴースト）の判定のコインはなく、はんげき（カイリキー）・ぼうぎょかふん（エリカのラフレシア）ははたらかない（相手のワザによるダメージではない）。"""
        for opponent, banned in ((mon(HAUNTER, ()), ("evade_check", "coin_flip")), (mon(MACHAMP, ()), ("counterattack",)),
                                 (mon(ERIKAS_VILEPLUME, ()), ("power_confusion", "coin_flip"))):
            with self.subTest(opponent=opponent["card"]):
                state, done = self.use(opponent)
                self.assertFalse(set(banned) & set(kinds(done, len(state.log))))
                self.assertEqual((done.players[1].active.damage, done.players[0].active.damage), (10, 0))

    def test_knock_out_on_the_bench_then_the_turn_continues(self):
        """控えのポケモンが HP 以上になったら、特殊能力の処理のあとにきぜつ（``timing`` は ``power``）→ サイドを取る決定（続きは ``continue_turn``）→ 番の
        プレイヤーの MAIN（ワザを使える）。"""
        state, done = self.use(mon(HITMONCHAN, ()), (mon(RATTATA, (), damage=20),), target=lambda s: s.players[1].bench[0].pokemon_id)
        [ko] = events(done, len(state.log), "knock_out")
        self.assertEqual((ko["timing"], done.decision.kind, done.decision.player, done.decision.context_value("then")),
                         ("power", TAKE_PRIZE, 0, "continue_turn"))
        taken = answer(done, first(done.decision))
        self.assertEqual((taken.phase, taken.current_player, taken.turn_number, len(taken.players[0].prizes)), (Phase.MAIN, 0, TURN, 5))
        self.assertIn("attack", kinds(attack(taken, 0, answers=[first]), len(taken.log)))

    def test_knock_out_of_the_active_and_promotion(self):
        state, done = self.use(mon(RATTATA, (), damage=20), (BULBASAUR,))
        taken = answer(done, first(done.decision))
        self.assertEqual((taken.decision.kind, taken.decision.player), (PROMOTE_ACTIVE, 1))
        promoted = answer(taken, first(taken.decision))
        self.assertEqual((promoted.phase, promoted.current_player, promoted.turn_number), (Phase.MAIN, 0, TURN))

    def test_guts_cannot_be_used_and_the_last_prize_wins(self):
        """こんじょう（相手のワザによるダメージで「きぜつ」するとき）は使えない（決定を出さない）。最後のサイドを取ったら勝ち。"""
        state, done = self.use(mon(HITMONCHAN, ()), (mon(GIOVANNIS_MACHAMP, (), damage=90),), target=lambda s: s.players[1].bench[0].pokemon_id)
        self.assertEqual(done.decision.kind, TAKE_PRIZE)
        self.assertFalse(events(done, len(state.log), "ko_prevention_declared"))
        _, last = self.use(mon(RATTATA, (), damage=20), (), prizes=1)
        won = answer(last, first(last.decision))
        self.assertEqual((won.phase, won.result.winner), (Phase.GAME_OVER, 0))


class ReelInTest(unittest.TestCase):
    """わるいヤドランの［つりあげる］（トラッシュのポケモンのカードを最大 3 枚、見せて手札に加える）。"""

    def use(self, discard):
        state = board(mon(ROCKET_SLOWPOKE, ()), hand=[DARK_SLOWBRO], discard=discard)
        waiting = evolve(state, DARK_SLOWBRO, ROCKET_SLOWPOKE)
        return state, answer(waiting, waiting.decision.options)

    def test_choose_up_to_three_pokemon_cards(self):
        """選べるものはトラッシュのポケモンのカード（たねポケモン・進化カード。トラッシュの並び）。同じ名前の別のカード（2 枚のズバット）も別々に選べる。
        エネルギー・トレーナーは選べない。1〜min(3, 枚数) 枚。選んだカードをトラッシュの並びの順に手札に加える（ログ ``recover_pokemon``。``cards`` は公開）。"""
        state, waiting = self.use([RATTATA, FIRE, FOSSIL_ZUBAT, POTION, ROCKET_ZUBAT, DARK_GOLBAT])
        d = waiting.decision
        options = tuple(u for u in state.players[0].discard if state.cards[u].card_id in (RATTATA, FOSSIL_ZUBAT, ROCKET_ZUBAT, DARK_GOLBAT))
        self.assertEqual((d.kind, d.resume, d.options, d.min_choices, d.max_choices), (RECOVER_POKEMON, "power", options, 1, 3))
        zubats = (options[1], options[2])
        done = answer(waiting, (zubats[1], options[0], zubats[0]))
        [recovered] = events(done, len(waiting.log), "recover_pokemon")
        self.assertEqual(recovered["cards"], (options[0], *zubats))
        self.assertEqual(cards_in(done, 0, "hand"), [RATTATA, FOSSIL_ZUBAT, ROCKET_ZUBAT])
        self.assertEqual(cards_in(done, 0, "discard"), [FIRE, POTION, DARK_GOLBAT])
        self.assertEqual((done.phase, card_count(done, 0)), (Phase.MAIN, card_count(state, 0)))
        for choice, code in (((), "INVALID_CHOICE_COUNT"), (options, "INVALID_CHOICE_COUNT"), ((options[0], options[0]), "DUPLICATE_CHOICE"),
                             ((state.players[0].discard[1],), "INVALID_CHOICE")):
            with self.subTest(choice=choice):
                assert_rejected(self, waiting, ResolveDecision(0, d.id, choice), code, IllegalActionError)

    def test_fewer_cards_and_an_empty_discard(self):
        """ポケモンのカードが 2 枚なら最大 2 枚。1 枚もなければ、使っても何もしない（ログ ``recover_pokemon_none``。決定はない）。"""
        _, two = self.use([RATTATA, GRASS, BULBASAUR])
        self.assertEqual(two.decision.max_choices, 2)
        state, none = self.use([GRASS, POTION])
        self.assertEqual((none.phase, none.decision), (Phase.MAIN, None))
        self.assertEqual(kinds(none, len(state.log)), ["evolve", "pokemon_power", "recover_pokemon_none"])


class SummonMinionsTest(unittest.TestCase):
    """わるいカイリューの［てしたをよぶ］（山札のたねポケモンを最大 2 枚、手札を通さずにベンチに出し、山札を切る）。0 枚になる場合は PW3。"""

    DECK = (FIRE, RATTATA, DARK_GOLBAT, DRATINI, GRASS, BULBASAUR)

    def evolved(self, *, bench=(RATTATA,), deck=DECK):
        state = board(mon(DARK_DRAGONAIR, ()), bench=bench, hand=[DARK_DRAGONITE], deck=deck)
        return state, evolve(state, DARK_DRAGONITE, DARK_DRAGONAIR)

    def test_bench_up_to_two_basics_from_the_deck(self):
        """選べるものは山札のたねポケモンのカード（uid の小さい順）。0〜min(2, ベンチの空き, 枚数) 枚。手札を通さずにベンチに出し（場に出た番は今の番。
        ログ ``bench_from_deck`` に ``power``）、山札を切る（``shuffle`` に ``power``）。手札は変わらない。"""
        state, waiting = self.evolved()
        accepted = answer(waiting, waiting.decision.options)
        d = accepted.decision
        basics = tuple(sorted(u for u in state.players[0].deck if state.cards[u].card_id in (RATTATA, DRATINI, BULBASAUR)))
        self.assertEqual((d.kind, d.resume, d.options, d.min_choices, d.max_choices), (BENCH_FROM_DECK, "power", basics, 0, 2))
        hand = list(accepted.players[0].hand)
        done = answer(accepted, basics[1:])
        self.assertEqual(kinds(done, len(accepted.log)), ["bench_from_deck", "bench_from_deck", "shuffle"])
        self.assertTrue(all(e["power"] == f"{DARK_DRAGONITE}@power0" for e in events(done, len(accepted.log))))
        self.assertEqual([done.cards[p.card].card_id for p in done.players[0].bench], [RATTATA, DRATINI, BULBASAUR])
        self.assertTrue(all(p.played_turn == TURN for p in done.players[0].bench[1:]))
        self.assertEqual(done.players[0].hand, hand)
        self.assertEqual((done.phase, card_count(done, 0)), (Phase.MAIN, card_count(state, 0)))

    def test_benched_basics_entered_play_this_turn(self):
        """ベンチに出したたねポケモンは、この番に場に出したので、この番には進化できない（p.310。手札から出したときと同じ ``PLAYED_THIS_TURN``）。"""
        state = board(mon(DARK_DRAGONAIR, ()), hand=[DARK_DRAGONITE, DARK_DRAGONAIR], deck=(FIRE, DRATINI))
        waiting = evolve(state, DARK_DRAGONITE, DARK_DRAGONAIR)
        done = answer(answer(waiting, waiting.decision.options), (card_of(state, 0, DRATINI, "deck"),))
        dratini = pid_of(done, 0, DRATINI)
        assert_rejected(self, done, EvolvePokemon(0, card_of(done, 0, DARK_DRAGONAIR), dratini), "PLAYED_THIS_TURN", IllegalActionError)

    def test_zero_cards_is_pw3(self):
        """0 枚を選ぶ答えは決められない（PW3。決定は待ったまま）。ベンチに空きがない・山札にたねポケモンがないなら、使うことを選ぶと止める（使う機会の決定の
        ``unresolved_choices``。使わないことは選べる）。隣の止まらない場合: 空きが 1 つ・たねポケモンが 1 枚（最大 1 枚）。"""
        _, waiting = self.evolved()
        accepted = answer(waiting, waiting.decision.options)
        assert_rejected(self, accepted, ResolveDecision(0, accepted.decision.id, ()), PW3, UnsupportedError)
        for bench, deck in (((RATTATA,) * 5, self.DECK), ((RATTATA,), (FIRE, DARK_GOLBAT)), ((RATTATA,), ())):
            with self.subTest(bench=len(bench), deck=deck):
                state, offered = self.evolved(bench=bench, deck=deck)
                d = offered.decision
                self.assertEqual((d.kind, d.context_value("unresolved_choices"), d.context_value("unresolved_code")), (ENTRY_POWER, d.options, PW3))
                self.assertEqual(check_invariants(offered), [])
                assert_rejected(self, offered, ResolveDecision(0, d.id, d.options), PW3, UnsupportedError)
                declined = answer(offered, ())
                self.assertEqual((declined.phase, kinds(declined, len(offered.log))), (Phase.MAIN, ["entry_power_declined"]))
        for bench, deck in (((RATTATA,) * 4, self.DECK), ((RATTATA,), (FIRE, DRATINI))):
            with self.subTest(bench=len(bench), deck=deck):
                _, offered = self.evolved(bench=bench, deck=deck)
                self.assertIsNone(offered.decision.context_value("unresolved_choices"))
                self.assertEqual(answer(offered, offered.decision.options).decision.max_choices, 1)

    def test_through_pokemon_breeder_returns_to_the_trainer(self):
        """ポケモン育て屋さんでたねポケモンに重ねたときも「場に出た時」（手札から出した 2 進化カード）。使う機会の決定の ``return_to`` は使っているトレーナーで、
        特殊能力の処理（使う・使わない）のあとにトレーナーの処理（トラッシュ）にもどる。待つ間、トレーナーは使用中のまま。"""
        state = board(mon(ROCKET_DRATINI, ()), hand=[DARK_DRAGONITE, POKEMON_BREEDER], deck=self.DECK)
        current = apply_kernel(state, PlayTrainer(0, card_of(state, 0, POKEMON_BREEDER)))
        while current.decision is not None and current.decision.resume == "trainer":
            current = answer(current, first(current.decision))
        d = current.decision
        breeder = card_of(state, 0, POKEMON_BREEDER)
        self.assertEqual((d.kind, d.context_value("return_to")), (ENTRY_POWER, ("trainer", 0, breeder, POKEMON_BREEDER)))
        self.assertEqual(current.trainer_in_use.card, breeder)
        self.assertEqual(check_invariants(current), [])
        [evolved] = events(current, len(state.log), "evolve")
        self.assertEqual(evolved["trainer_card"], breeder)
        declined = answer(current, ())
        self.assertIsNone(declined.trainer_in_use)
        self.assertIn(POKEMON_BREEDER, cards_in(declined, 0, "discard"))
        self.assertEqual(declined.phase, Phase.MAIN)
        accepted = answer(current, d.options)
        self.assertEqual(accepted.decision.context_value("return_to"), ("trainer", 0, breeder, POKEMON_BREEDER))
        self.assertEqual(check_invariants(accepted), [])
        done = answer(accepted, accepted.decision.options[:2])
        self.assertIsNone(done.trainer_in_use)
        self.assertIn(POKEMON_BREEDER, cards_in(done, 0, "discard"))
        after = kinds(done, len(accepted.log))
        self.assertEqual(after[:3], ["bench_from_deck", "bench_from_deck", "shuffle"])
        self.assertEqual((done.phase, card_count(done, 0)), (Phase.MAIN, card_count(state, 0)))


class MoonPowerRouteTest(unittest.TestCase):
    """エリカのピッピの「つきのちから」（ワザの効果で山札から進化カードを重ねる）で、場に出たときの特殊能力を持つ進化カードを重ねる場合（PW4）。"""

    def test_only_an_entry_power_card_stops_before_the_declaration(self):
        """重ねられる進化カードがどれも場に出たときの特殊能力を持つ（わるいカイリューだけ）なら、ワザの宣言の前に止める（PW4。どの先読みの方法でも、コインの前）。"""
        state = board(mon(ERIKAS_CLEFAIRY), bench=(mon(DARK_DRAGONAIR, ()),), deck=(DARK_DRAGONITE, GRASS))
        assert_stops(self, state, UseAttack(0, 0), PW4)

    def test_choosing_the_entry_power_card_stops(self):
        """ほかの進化カード（エリカのピクシー）もあれば、わるいカイリューは選べるが選ぶと止める（``entry_power_choices``。状態は変わらない）。隣の止まらない場合:
        エリカのピクシーを選ぶ。"""
        state = board(mon(ERIKAS_CLEFAIRY), bench=(mon(DARK_DRAGONAIR, ()),), deck=(DARK_DRAGONITE, ERIKAS_CLEFABLE, GRASS))
        waiting = attack(state, 0, H)
        d = waiting.decision
        dragonite = card_of(state, 0, DARK_DRAGONITE, "deck")
        self.assertEqual((d.kind, d.context_value("entry_power_choices")), (SEARCH_DECK, (dragonite,)))
        assert_rejected(self, waiting, ResolveDecision(0, d.id, (dragonite,)), PW4, UnsupportedError)
        done = answer(waiting, (card_of(state, 0, ERIKAS_CLEFABLE, "deck"),))
        self.assertTrue(events(done, len(waiting.log), "evolve"))
        self.assertFalse(events(done, len(waiting.log), "pokemon_power"))

    def test_a_from_hand_entry_power_has_no_opportunity_from_the_deck(self):
        """「手札から出した時」の特殊能力（わるいゴルバットの［こっそりかみつく］）は、山札から重ねる進化では使う機会がない（決定を出さず、PW4 でもない）。
        「場に出た時」（わるいカイリューの［てしたをよぶ］）だけが PW4。"""
        state = board(mon(ERIKAS_CLEFAIRY), bench=(mon(ROCKET_ZUBAT, ()),), deck=(DARK_GOLBAT, GRASS))
        waiting = attack(state, 0, H)
        self.assertIsNone(waiting.decision.context_value("entry_power_choices"))
        done = answer(waiting, first(waiting.decision))
        [evolved] = events(done, len(state.log), "evolve")
        self.assertEqual((evolved["source_zone"], done.cards[evolved["to_card"]].card_id), ("deck", DARK_GOLBAT))
        self.assertFalse(events(done, len(state.log), "pokemon_power") + events(done, len(state.log), "entry_power_declined"))
        self.assertTrue(done.decision is None or done.decision.kind != ENTRY_POWER)
        self.assertIsNone(E.applicable_entry_power(done, card_of(state, 0, DARK_GOLBAT, "deck"), from_hand=False))
        self.assertIsNotNone(E.applicable_entry_power(done, card_of(state, 0, DARK_GOLBAT, "deck"), from_hand=True))

    def test_a_declared_power_card_is_not_pw4(self):
        """宣言して使う特殊能力を持つ進化カード（わるいハクリューの［しんかのひかり］）は、ワザで重ねても使う機会はないので止めない。"""
        state = board(mon(ERIKAS_CLEFAIRY), bench=(mon(ROCKET_DRATINI, ()),), deck=(DARK_DRAGONAIR, GRASS))
        done = attack(state, 0, H, answers=[first])
        [evolved] = events(done, len(state.log), "evolve")
        self.assertEqual((evolved["source_zone"], done.cards[evolved["to_card"]].card_id), ("deck", DARK_DRAGONAIR))
        self.assertFalse(events(done, len(state.log), "pokemon_power"))

    def test_every_card_blocked_by_evolution_hp_stops_before_the_declaration(self):
        """重ねられる進化カードがどれも、重ねると HP がのっているダメージ以下になるなら、選べる答えのない決定にせず、ワザの宣言の前に止める（v0.4a の H1 と
        同じ ``UNRESOLVED_EVOLUTION_HP``。v0.42 では先読みで内部のエラーになっていた。今のカードの HP では起こらないので、判定を差しかえて確かめる）。"""
        state = board(mon(ERIKAS_CLEFAIRY), bench=(), deck=(ERIKAS_CLEFABLE, GRASS))
        with mock.patch.object(E, "evolution_hp_problem_targets", lambda state, card, targets: list(targets)):
            assert_stops(self, state, UseAttack(0, 0), "UNRESOLVED_EVOLUTION_HP")


class ChemicalGasTest(unittest.TestCase):
    def test_gas_suppresses_every_declared_power(self):
        """かがくへんかガス（相手のベトベトン）がはたらいていると、宣言する 6 つの特殊能力は ``POWER_SUPPRESSED``（コイン・決定の前）。"""
        cases = {DARK_GLOOM: {}, ROCKET_DROWZEE: {}, ERIKAS_BELLSPROUT_40: {}, LT_SURGES_MAGNETON: {}, DARK_DRAGONAIR: {}}
        for card, extra in cases.items():
            with self.subTest(card=card):
                state = board(mon(card, ()), mon(MUK, ()), bench=(mon(RATTATA, (G, L)),), deck=(DARK_DRAGONITE, FIRE))
                assert_rejected(self, state, UsePokemonPower(0, pid_of(state, 0, card), 0, **extra), "POWER_SUPPRESSED", IllegalActionError)
        state = board(mon(ROCKET_CHARMANDER, ()), mon(MUK, ()), bench=(mon(RATTATA, (R,)),))
        rat = state.players[0].bench[0]
        assert_rejected(self, state, UsePokemonPower(0, pid_of(state, 0, ROCKET_CHARMANDER), 0, energy=rat.energy[0], source=rat.pokemon_id),
                        "POWER_SUPPRESSED", IllegalActionError)


# ---------------------------------------------------------------- ワザ


class AttackTest(unittest.TestCase):
    def test_flitter_chooses_any_opponent_pokemon(self):
        """ふらふらとぶ: 相手の場のポケモン（バトル場 → ベンチ）を 1 匹選び、弱点・抵抗力に関係なく 20。バトル場を選んだら p.320 の (1)（プラスパワーを計算する）、
        控えを選んだら (2)（プラスパワーは変えない）。"""
        state = board(mon(DARK_GOLBAT), mon(SANDSHREW, ()), opponent_bench=(mon(SANDSHREW, ()),))
        waiting = attack(state, 0)
        d = waiting.decision
        self.assertEqual((d.kind, d.player, d.options), (SELECT_POKEMON, 0, tuple(p.pokemon_id for p in state.players[1].in_play())))
        active = answer(waiting, (state.players[1].active.pokemon_id,))
        self.assertEqual(active.players[1].active.damage, 20)
        bench = answer(waiting, (state.players[1].bench[0].pokemon_id,))
        self.assertEqual((bench.players[1].bench[0].damage, bench.players[1].active.damage), (20, 0))

    def test_flitter_with_pluspower(self):
        from tests.helpers import PLUSPOWER

        state = board(mon(DARK_GOLBAT, trainers=[(PLUSPOWER, TURN)]), mon(SANDSHREW, ()), opponent_bench=(mon(SANDSHREW, ()),))
        waiting = attack(state, 0)
        self.assertEqual(answer(waiting, (state.players[1].active.pokemon_id,)).players[1].active.damage, 30)
        self.assertEqual(answer(waiting, (state.players[1].bench[0].pokemon_id,)).players[1].bench[0].damage, 20)

    def test_stretch_vine_and_the_others(self):
        """のびるつる: 相手の控えを 1 匹選び 10（控えがいなければ何もしない）。メガショック・しっぽでつく・きまぐれこうげき・きょだいなしっぽ・どくのこな・
        あくむ・ほのおのしっぽは既存の型。"""
        state = board(mon(ERIKAS_BELLSPROUT_40), mon(HITMONCHAN, ()), opponent_bench=(mon(SANDSHREW, ()),))
        vine = attack(state, 0, answers=[first])
        self.assertEqual(vine.players[1].bench[0].damage, 10)
        alone = board(mon(ERIKAS_BELLSPROUT_40), opponent_bench=())
        self.assertFalse(events(attack(alone, 0), len(alone.log), "damage"))
        self.assertEqual(attack(board(mon(LT_SURGES_MAGNETON)), 0, T).players[0].active.damage, 20)
        self.assertEqual(attack(board(mon(DARK_DRAGONAIR)), 0, H).players[1].active.damage, 40)
        self.assertEqual(attack(board(mon(DARK_SLOWBRO)), 0, T).players[1].active.damage, 0)
        self.assertEqual(attack(board(mon(DARK_DRAGONITE), mon(DRAGONAIR, (), evolved_from=DRATINI)), 0, H).players[1].active.damage, 70)
        self.assertIsNotNone(attack(board(mon(DARK_GLOOM)), 0).players[1].active.conditions.poison)
        self.assertTrue(attack(board(mon(ROCKET_DROWZEE)), 0, T).players[1].active.conditions.asleep)  # ポケモンチェックのねむりのコインは「うら」
        self.assertEqual(attack(board(mon(ROCKET_CHARMANDER)), 0).players[1].active.damage, 20)


# ---------------------------------------------------------------- 整合性


class IntegrityTest(unittest.TestCase):
    """不変条件・書き出し・渡した状態を変えないこと・先読みの方法によらないこと（ワザ）・カードの保存則（特殊能力）。"""

    CASES = (
        (DARK_GLOOM, 0, (), ()), (ROCKET_DROWZEE, 0, (), ()), (ROCKET_CHARMANDER, 0, (), ()), (ERIKAS_BELLSPROUT_40, 0, (), (first,)),
        (LT_SURGES_MAGNETON, 0, (T,), ()), (DARK_DRAGONAIR, 0, (H,), ()), (DARK_GOLBAT, 0, (), (first,)), (DARK_SLOWBRO, 0, (H,), ()),
        (DARK_DRAGONITE, 0, (T,), ()),
    )

    def state(self, card):
        return board(mon(card, damage=10), mon(HITMONCHAN, (F, F), damage=20), bench=(mon(RATTATA, damage=10), BULBASAUR),
                     opponent_bench=(mon(RATTATA, damage=10), BULBASAUR), deck=(PSYCHIC, FIRE, PSYCHIC, RATTATA))

    def test_cases_cover_every_attack(self):
        self.assertEqual(sorted((card, index) for card, index, _, _ in self.CASES), sorted(EXPECTED))

    def test_every_step_keeps_invariants_and_does_not_mutate_the_input(self):
        for card, index, sides, answers in self.CASES:
            with self.subTest(card=card, index=index):
                state = self.state(card)
                before = copy.deepcopy(full(state))
                current = apply_kernel(with_coin_results(state, *sides), UseAttack(0, index))
                self.assertEqual(full(state), before)
                for answer_of in answers:
                    self.assertEqual(check_invariants(current), [])
                    self.assertEqual(full(pickle.loads(pickle.dumps(current))), full(current))
                    d = current.decision
                    current = apply_kernel(current, ResolveDecision(d.player, d.id, answer_of(d)))
                self.assertEqual(check_invariants(current), [])
                self.assertTrue(current.decision is None or current.decision.resume != "attack")
                self.assertEqual(card_count(current, 0) + card_count(current, 1), card_count(state, 0) + card_count(state, 1))

    def test_same_result_in_every_preflight_mode(self):
        for card, index, sides, answers in self.CASES:
            with self.subTest(card=card, index=index):
                state = self.state(card)
                results = {repr(snapshot(play(with_coin_results(state, *sides), UseAttack(0, index), answers, mode=mode))) for mode in PREFLIGHT_MODES}
                self.assertEqual(len(results), 1)

    def test_powers_keep_invariants_and_do_not_mutate_the_input(self):
        """特殊能力の宣言・使う機会・決定への答えのどの段階でも不変条件が通り、pickle で同じ状態にもどり、渡した状態を変えない。カードの枚数は変わらない。"""
        def declared(card, **choices):
            return lambda s: UsePokemonPower(0, pid_of(s, 0, card), 0, **{k: v(s) for k, v in choices.items()})

        def evolving(card, base):
            return lambda s: EvolvePokemon(0, card_of(s, 0, card), pid_of(s, 0, base))

        cases = (
            (board(mon(DARK_GLOOM)), declared(DARK_GLOOM), (H,), ()),
            (board(mon(ROCKET_DROWZEE)), declared(ROCKET_DROWZEE), (T,), ()),
            (board(mon(ROCKET_CHARMANDER, ()), bench=(mon(RATTATA, (R,)),)),
             declared(ROCKET_CHARMANDER, energy=lambda s: s.players[0].bench[0].energy[0], source=lambda s: s.players[0].bench[0].pokemon_id), (), ()),
            (board(mon(ERIKAS_BELLSPROUT_40, ()), bench=(mon(RATTATA, (G, G)),)), declared(ERIKAS_BELLSPROUT_40), (), (lambda d: d.options,)),
            (board(mon(LT_SURGES_MAGNETON, ()), bench=(mon(RATTATA, (L, L)),)), declared(LT_SURGES_MAGNETON), (), (lambda d: d.options,)),
            (board(mon(DARK_DRAGONAIR, ()), deck=(FIRE, DARK_DRAGONITE)), declared(DARK_DRAGONAIR), (), (first,)),
            (board(mon(ROCKET_ZUBAT, ()), hand=[DARK_GOLBAT], opponent_bench=(mon(RATTATA, (), damage=20),)), evolving(DARK_GOLBAT, ROCKET_ZUBAT), (),
             (lambda d: d.options, lambda d: d.options[-1:], first)),
            (board(mon(ROCKET_SLOWPOKE, ()), hand=[DARK_SLOWBRO], discard=[RATTATA, FIRE, BULBASAUR]), evolving(DARK_SLOWBRO, ROCKET_SLOWPOKE), (),
             (lambda d: d.options, lambda d: d.options)),
            (board(mon(DARK_DRAGONAIR, ()), hand=[DARK_DRAGONITE], deck=(FIRE, RATTATA, DRATINI)), evolving(DARK_DRAGONITE, DARK_DRAGONAIR), (),
             (lambda d: d.options, lambda d: d.options)),
        )
        for state, command_of, sides, answers in cases:
            with self.subTest(command=command_of(state)):
                before = copy.deepcopy(full(state))
                current = apply_kernel(with_coin_results(state, *sides) if sides else state, command_of(state))
                self.assertEqual(full(state), before)
                for answer_of in answers:
                    self.assertEqual(check_invariants(current), [])
                    self.assertEqual(full(pickle.loads(pickle.dumps(current))), full(current))
                    d = current.decision
                    snap = copy.deepcopy(full(current))
                    nxt = apply_kernel(current, ResolveDecision(d.player, d.id, tuple(answer_of(d))))
                    self.assertEqual(full(current), snap)
                    current = nxt
                self.assertEqual(check_invariants(current), [])
                self.assertIsNone(current.decision)
                self.assertEqual(current.phase, Phase.MAIN)
                self.assertEqual(card_count(current, 0) + card_count(current, 1), card_count(state, 0) + card_count(state, 1))


class CopyTest(unittest.TestCase):
    """相手のワザを自分のワザとして使う効果（ピクシー・ピッピの「ゆびをふる」・カスミのコダックの「ちょうのうりょく」）での v0.43 のワザ。"""

    COPIERS = {CLEFABLE: ((P,), 0, ()), CLEFAIRY: ((P, P, P), 1, ()), MISTYS_PSYDUCK: ((P,), 0, (H, H, H))}

    def test_every_attack_can_be_copied_without_internal_errors(self):
        """9 のワザのどれをまねても、エンジンの内部のエラーにならない（処理するか、決まったコードで拒否する）。ふらふらとぶは相手の場のどのポケモンも選べる。"""
        for (card, index) in EXPECTED:
            for copier, (energy, attack_index, sides) in self.COPIERS.items():
                with self.subTest(card=card, index=index, copier=copier):
                    state = board(mon(copier, energy, damage=20), mon(card, ()), bench=(mon(RATTATA, damage=10),), opponent_bench=(RATTATA, BULBASAUR),
                                  deck=(PSYCHIC, FIRE, RATTATA))
                    try:
                        current = play(with_coin_results(state, *sides, H, H, H, H), UseAttack(0, attack_index), [])
                        if current.decision is not None and current.decision.kind == "select_attack":
                            self.assertIn(index, current.decision.options)
                            current = apply_kernel(current, ResolveDecision(0, current.decision.id, (index,)))
                        while current.decision is not None and current.decision.resume == "attack":
                            d = current.decision
                            if card == DARK_GOLBAT:
                                self.assertEqual(d.options, tuple(p.pokemon_id for p in state.players[1].in_play()))
                            current = apply_kernel(current, ResolveDecision(d.player, d.id, first(d)))
                    except EngineError as error:
                        self.assertTrue(error.code.startswith(("UNRESOLVED_", "UNSUPPORTED_")), error.code)
                        continue
                    self.assertEqual(check_invariants(current), [])


class DocumentTest(unittest.TestCase):
    def test_document_records_the_decisions(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("PW3", "PW4", PW3, PW4, "HC10", "UNRESOLVED_ENERGY_BURN_TRANSFER", "UNRESOLVED_EVOLUTION_HP", "entry_power", "entry_power_declined",
                       "return_to", "continue_turn", "power_uses_this_turn", "may_knock_out", "from_hand_only", "CR-COUNTERATTACK-IS-POWER-DAMAGE",
                       "pcg-search.com", "くさいかふん", "えんかくさいみん", "ほのおをもらう", "ようぶんきゅうしゅう", "エナジーチャージ", "しんかのひかり",
                       "こっそりかみつく", "つりあげる", "てしたをよぶ", "ふらふらとぶ", "のびるつる", "手札から出した時", "場に出た時", "ポケモン育て屋さん",
                       "つきのちから"):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
