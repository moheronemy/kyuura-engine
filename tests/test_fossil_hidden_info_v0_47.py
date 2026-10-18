"""v0.47: なにかの化石・ピッピ人形（ポケモンとして場に出せるトレーナーカード）と化石のポケモン、見えない情報を扱う 4 枚、トレーナーの使用を禁止する 2 枚
（docs/fossil-hidden-info-v0.47.md）。

13 枚: なにかの化石（PMCG3-046）・ピッピ人形（PMCG1-091）・オムナイト（PMCG3-015［おみとおし］）・オムスター（PMCG3-021）・カブト（PMCG3-035［カブトアーマー］）・
カブトプス（PMCG3-040）・プテラ（PMCG3-041［げんしのちから］）・マンキー（PMCG2-028［スパイ］）・コラッタ（PMCG4-045［わるふざけ］）・スリーパー（PMCG3-032。
みらいよち）・マチスのイーブイ（PMCG5-062。おどろかす）・マチスのサンダース（PMCG5-042。こうしゅうは）・コダック（PMCG3-010。ずつう）。どれも kyuura データの採用
（処理に使う文面は kyuura の印刷の文面。採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合（なにかの化石・ピッピ人形の場での HP 10・
弱点なし・抵抗力なしは同じページの値）。ガイドブックは読んでいない。

根拠にした既存の記録: GR-2000-P307-CARD-OVER-RULE（カードの文面がルールに優先する）・GR-2000-P321-DAMAGE-ORDER（受けるポケモンの効果は 8 段階）・
GR-2000-P319-HP-AND-DAMAGE・GR-2000-P320-COUNTER-MOVE・GR-2000-P309-ATTACK-PROCEDURE・p.308（対戦準備）・p.310（進化）・p.311（にげる・勝ち負け）・p.313（きぜつ）・
p.322（特殊状態・どく）・p.325（ポケモンいれかえ）と、エンジンの v0.3c（こんらんの 20）・v0.39（GS1）・v0.43（PW3）・v0.44（FC1）・v0.46（常にはたらく特殊能力・
［アレルギーかふん］・TRAINER_PREVENTED）の記録。

新しい停止コードは 4 つ: PF1（``UNRESOLVED_PLAY_AS_POKEMON_SETUP``）・PF2（``UNRESOLVED_PLAY_AS_POKEMON_RETREAT``）・PF3（``UNRESOLVED_BREEDER_ON_PLAY_AS_POKEMON``）・
KA1（``UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER``）。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import re
import unittest

from kyuura_engine import (
    DiscardFromPlay,
    EndTurn,
    EngineError,
    EvolvePokemon,
    IllegalActionError,
    Phase,
    PlaceStartingPokemon,
    PlayBasicToBench,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    check_invariants,
    new_game,
    observe,
    state_to_dict,
    visible_log,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.decisions import (
    ARRANGE_DECK_TOP,
    PEEK_CARD,
    PROMOTE_ACTIVE,
    SELECT_DECK_OWNER,
    SELECT_HAND_CARD,
    SELECT_LOOK_COUNT,
    SELECT_POKEMON,
    SELECT_PRIZE_CARD,
)
from kyuura_engine.observation import PRIVATE_FIELDS, PUBLIC_EVENTS
from kyuura_engine.resolution import PREFLIGHT_MODES, contract, programs, v013_checks
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import TrainerUseLock
from scripts import check_card_sources as cs
from tests.helpers import (
    AERODACTYL,
    ATTACK_TYPES_SINCE_V0_17,
    BILL,
    CLEFAIRY,
    CLEFAIRY_DOLL,
    DARK_GLOOM,
    DARK_VILEPLUME,
    DROWZEE,
    ERIKAS_CLEFABLE,
    ERIKAS_CLEFAIRY,
    FIGHTING,
    FOSSIL_PSYDUCK,
    GIOVANNIS_GYARADOS,
    GIOVANNIS_MAGIKARP,
    GRIMER,
    GUST,
    HITMONCHAN,
    HYPNO,
    JUNGLE_MANKEY,
    KABUTO,
    KABUTOPS,
    KOGAS_BEEDRILL,
    KOGAS_KAKUNA,
    KOGAS_WEEDLE,
    LIGHTNING,
    LT_SURGES_EEVEE,
    LT_SURGES_JOLTEON,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MUK,
    MYSTERIOUS_FOSSIL,
    OMANYTE,
    OMASTAR,
    POKEMON_BREEDER,
    POKEMON_TRADER,
    POTION,
    PSYCHIC,
    RATTATA,
    ROCKET_ODDISH,
    ROCKET_RATTATA,
    SWITCH,
    V0_47_CARDS,
    V0_47_POKEMON,
    V0_47_TRAINERS,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    expand_decklist,
    with_coin_results,
)
from tests.log_audit import log_problems, observation_problems, serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "fossil-hidden-info-v0.47.md"
TURN = 7
F, W, P, L = FIGHTING, WATER, PSYCHIC, LIGHTNING
PF1 = "UNRESOLVED_PLAY_AS_POKEMON_SETUP"
PF2 = "UNRESOLVED_PLAY_AS_POKEMON_RETREAT"
PF3 = "UNRESOLVED_BREEDER_ON_PLAY_AS_POKEMON"
KA1 = "UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER"
FC1 = "UNRESOLVED_STATED_CARDS_SHORT"
GS1 = "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE"
PW3 = "UNRESOLVED_POWER_ZERO_CARDS"
CONFUSION_MODIFIERS = "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS"

# 登録の実装の型と値
ATTACKS = {
    (OMANYTE, 0): (E.ExtraEnergyDamage, {"energy_type": E.EnergyType.WATER, "per_energy": 10, "max_extra": 2}),
    (OMASTAR, 0): (E.ExtraEnergyDamageMixed, {"energy_type": E.EnergyType.WATER, "per_energy": 10, "max_extra": 2}),
    (OMASTAR, 1): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 30}),
    (KABUTO, 0): (E.DamageOnly, {}),
    (KABUTOPS, 0): (E.DamageOnly, {}),
    (KABUTOPS, 1): (E.DamageAndDrain, {}),
    (AERODACTYL, 0): (E.DamageOnly, {}),
    (JUNGLE_MANKEY, 0): (E.DamageOnly, {}),
    (ROCKET_RATTATA, 0): (E.CoinBonusDamage, {"bonus": 10}),
    (HYPNO, 0): (E.ArrangeDeckTopEffect, {"max_cards": 3}),
    (HYPNO, 1): (E.DamageThenChosenBenchDamage, {"bench_damage": 10}),
    (LT_SURGES_EEVEE, 0): (E.LookOpponentHandCardToDeck, {}),
    (LT_SURGES_EEVEE, 1): (E.DamageOnly, {}),
    (LT_SURGES_JOLTEON, 0): (E.DamageThenLockOpponentTrainersOnHeads, {}),
    (LT_SURGES_JOLTEON, 1): (E.DamagePlusOwnCountersThenSelfDamageOnTails, {"per": 10, "self_damage": 30}),
    (FOSSIL_PSYDUCK, 0): (E.LockOpponentTrainersNextTurn, {}),
    (FOSSIL_PSYDUCK, 1): (E.CoinFlipDamage, {"coins": 3, "damage_per_heads": 10}),
}
POWERS = {
    OMANYTE: E.RevealOpponentHand(),
    KABUTO: E.HalveDamageReceived(),
    AERODACTYL: E.PreventEvolution(),
    JUNGLE_MANKEY: E.PeekCard(),
    ROCKET_RATTATA: E.SwapPrizeWithDeckTop(),
}
TRAINERS = {MYSTERIOUS_FOSSIL: E.PlayAsPokemon(hp=10, role="fossil"), CLEFAIRY_DOLL: E.PlayAsPokemon(hp=10, role="doll")}
# v0.47 で加えたワザの型（tests/helpers.py の ATTACK_TYPES_SINCE_V0_17 の最後の 5）
NEW_TYPES = (E.ArrangeDeckTopEffect, E.LookOpponentHandCardToDeck, E.LockOpponentTrainersNextTurn, E.DamageThenLockOpponentTrainersOnHeads,
             E.DamagePlusOwnCountersThenSelfDamageOnTails)
# pcg-search.com の対象の版（サイトの一覧の番号）
EDITIONS = {MYSTERIOUS_FOSSIL: "046/048", CLEFAIRY_DOLL: "084/096", OMANYTE: "021/048", OMASTAR: "022/048", KABUTO: "039/048", KABUTOPS: "040/048",
            AERODACTYL: "041/048", JUNGLE_MANKEY: "028/048", ROCKET_RATTATA: "045/065", HYPNO: "032/048", LT_SURGES_EEVEE: "061/096",
            LT_SURGES_JOLTEON: "042/096", FOSSIL_PSYDUCK: "010/048"}
# 照合で文面の書き方の違いがあったカード（挙動に影響しない。kyuura への報告事項）
TEXT_DIFFERENCES = {CLEFAIRY_DOLL: "trainer.text.ja", HYPNO: "pokemon.attacks[1].text.ja", LT_SURGES_EEVEE: "pokemon.attacks[0].text.ja"}
# 進化しているポケモンの下のカード（build_test_state の "evolved_from"）
BELOW = {OMANYTE: MYSTERIOUS_FOSSIL, KABUTO: MYSTERIOUS_FOSSIL, AERODACTYL: MYSTERIOUS_FOSSIL, OMASTAR: [MYSTERIOUS_FOSSIL, OMANYTE],
         KABUTOPS: [MYSTERIOUS_FOSSIL, KABUTO], HYPNO: DROWZEE, LT_SURGES_JOLTEON: LT_SURGES_EEVEE, MUK: GRIMER, DARK_VILEPLUME: [ROCKET_ODDISH, DARK_GLOOM],
         MACHAMP: [MACHOP, MACHOKE], KOGAS_KAKUNA: KOGAS_WEEDLE}
FOSSIL = {"card": MYSTERIOUS_FOSSIL}
DOLL = {"card": CLEFAIRY_DOLL}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def bench_spec(b):
    return mon(b) if isinstance(b, str) and b in BELOW else b


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), deck=None, opponent_deck=None, hand=(), opponent_hand=(),
          prizes=None, turn=TURN, current=0):
    me = {"active": active, "bench": [bench_spec(b) for b in bench], "hand": list(hand)}
    them = {"active": opponent or mon(HITMONCHAN, (F, F, F)), "bench": [bench_spec(b) for b in opponent_bench], "hand": list(opponent_hand)}
    if deck is not None:
        me["deck"] = list(deck)
    if opponent_deck is not None:
        them["deck"] = list(opponent_deck)
    if prizes is not None:
        me["prizes"] = prizes
        them["prizes"] = prizes
    return build_test_state([me, them], turn_number=turn, current_player=current)


def full(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS))


def snapshot(state):
    return full(state), [dict(e) for e in state.log], repr(state.rng.getstate())


def audited(test, state):
    """不変条件・書き出し・観測の監査（盤面を直接作ったテスト。ログの監査は正式な対戦のテストで確かめる）。"""
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])
    return state


def events(state, since, kind=None):
    return [dict(e) for e in state.log[since:] if kind is None or e["kind"] == kind]


def answer(state, choices, *, mode="derived"):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)), preflight=mode)


def attack(state, index, *sides, player=0, mode="derived"):
    return apply_kernel(with_coin_results(state, *sides) if sides else state, UseAttack(player, index), preflight=mode)


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


def card_of(state, player, card, zone="hand", nth=0):
    return [u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card][nth]


def pid_of(state, player, card, nth=0):
    return [p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card][nth]


def _keys(node):
    """記録（辞書・並び）の中のすべての項目の名前。"""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from _keys(value)


def end_turn(state, player):
    """番を終える（ポケモンチェックのあと次の番）。"""
    return apply_kernel(state, EndTurn(player))


# ---------------------------------------------------------------- 登録・写し・記録


class CardDataTest(unittest.TestCase):
    """13 枚の写し・登録・記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_thirteen_requested_cards(self):
        """写しの組 pool_v0_47 は依頼の 13 枚（並び）。どれも対応で、どのワザも、どの特殊能力も、トレーナーも登録した。"""
        self.assertEqual(read_extract()["pool_v0_47"], list(V0_47_CARDS))
        names = {MYSTERIOUS_FOSSIL: "なにかの化石", CLEFAIRY_DOLL: "ピッピ人形", OMANYTE: "オムナイト", OMASTAR: "オムスター", KABUTO: "カブト",
                 KABUTOPS: "カブトプス", AERODACTYL: "プテラ", JUNGLE_MANKEY: "マンキー", ROCKET_RATTATA: "コラッタ", HYPNO: "スリーパー",
                 LT_SURGES_EEVEE: "マチスのイーブイ", LT_SURGES_JOLTEON: "マチスのサンダース", FOSSIL_PSYDUCK: "コダック"}
        for card in V0_47_CARDS:
            with self.subTest(card=card):
                definition = self.pool.get(card)
                self.assertEqual(definition.name_ja, names[card])
                self.assertTrue(self.pool.is_playable(card))
                self.assertEqual(definition.category, "trainer" if card in V0_47_TRAINERS else "pokemon")
                self.assertIsNone(definition.play_role)  # 写し（印刷）の定義には場での役割を書かない
                self.assertTrue(all(a.supported for a in definition.attacks))
        # 特殊能力・トレーナーの登録を除くと対応にならない（特殊能力を持つカードを、ワザだけの登録で対応と数えない）
        for card in POWERS:
            effects = E.DEFAULT_EFFECTS.without_powers(f"test-no-{card}", [E.PowerKey(card, 0)])
            with self.subTest(card=card):
                self.assertFalse(pool_from_extract(read_extract(), effects).is_playable(card))

    def test_evolution_names(self):
        """進化元は「○○から進化」の名前の完全一致: オムナイト・カブト・プテラは「なにかの化石」、オムスターはオムナイト、カブトプスはカブト、スリーパーはスリープ、
        マチスのサンダースはマチスのイーブイ。似た名前の別のカード（第4弾・リーダーズスタジアムのマンキー・コラッタ・コダック・イーブイ）と取りちがえない。"""
        expected = {OMANYTE: "なにかの化石", KABUTO: "なにかの化石", AERODACTYL: "なにかの化石", OMASTAR: "オムナイト", KABUTOPS: "カブト",
                    HYPNO: "スリープ", LT_SURGES_JOLTEON: "マチスのイーブイ"}
        for card in V0_47_POKEMON:
            with self.subTest(card=card):
                definition = self.pool.get(card)
                self.assertEqual(definition.evolves_from, expected.get(card))
                self.assertEqual(definition.is_basic_pokemon, card not in expected)
        self.assertEqual(self.pool.get(OMASTAR).stage, "stage2")
        self.assertEqual(self.pool.get(KABUTOPS).stage, "stage2")
        for ours, other in ((JUNGLE_MANKEY, "PMCG4-039"), (ROCKET_RATTATA, RATTATA), (FOSSIL_PSYDUCK, "PMCG4-019"), (LT_SURGES_EEVEE, "PMCG2-037")):
            with self.subTest(pair=(ours, other)):
                self.assertNotEqual(ours, other)
                self.assertNotEqual(self.pool.get(ours).attacks, self.pool.get(other).attacks)

    def test_every_attack_power_and_trainer_is_registered_with_the_expected_implementation(self):
        for card in V0_47_POKEMON:
            definition = self.pool.get(card)
            for index, attack_def in enumerate(definition.attacks):
                with self.subTest(card=card, index=index):
                    entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
                    kind, values = ATTACKS[(card, index)]
                    self.assertIs(type(entry.effect), kind)
                    self.assertEqual(entry.effect, kind(**values))
                    self.assertEqual((entry.name_ja, entry.text_ja), (attack_def.name_ja, attack_def.text_ja))
                    self.assertEqual(entry.effect.check(attack_def), [])
                    if attack_def.text_ja:
                        self.assertEqual((entry.play_text_ja, entry.source), (attack_def.text_ja, cs.PRINTED_TEXT_SOURCE))
            for index, power in enumerate(definition.powers):
                with self.subTest(card=card, power=index):
                    entry = E.DEFAULT_EFFECTS.power_entry(card, index)
                    self.assertEqual(entry.effect, POWERS[card])
                    self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                                     (power.name_ja, power.text_ja, power.text_ja, cs.PRINTED_TEXT_SOURCE))
                    self.assertEqual(entry.effect.check(power), [])
            self.assertEqual(len(definition.powers), 1 if card in POWERS else 0)
        for card, effect in TRAINERS.items():
            with self.subTest(trainer=card):
                entry = E.DEFAULT_EFFECTS.trainer_entry(card)
                definition = self.pool.get(card)
                self.assertEqual(entry.effect, effect)
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                                 (definition.name_ja, definition.trainer_text_ja, definition.trainer_text_ja, cs.PRINTED_TEXT_SOURCE))
                self.assertEqual(entry.effect.check(definition), [])
        # 宣言して使うもの（スパイ・わるふざけ。自分の番ごとに 1 回）と、常にはたらくもの（おみとおし・カブトアーマー・げんしのちから）
        for card in (JUNGLE_MANKEY, ROCKET_RATTATA):
            self.assertTrue(POWERS[card].declared and POWERS[card].once_per_turn)
        for card in (OMANYTE, KABUTO, AERODACTYL):
            self.assertIsInstance(POWERS[card], E.ContinuousPower)
            self.assertFalse(POWERS[card].declared)

    def test_text_checks_reject_other_wording(self):
        """型の ``check`` は登録した文面と完全に同じものだけを受け付ける（ワザ・特殊能力・トレーナーとも）。"""
        for (card, index), (kind, _) in ATTACKS.items():
            if kind not in NEW_TYPES:
                continue
            attack_def = self.pool.get(card).attacks[index]
            effect = E.DEFAULT_EFFECTS.attack_entry(card, index).effect
            with self.subTest(card=card, index=index):
                self.assertTrue(effect.check(dataclasses.replace(attack_def, text_ja=attack_def.text_ja + "あ")))
        for card, effect in POWERS.items():
            power = self.pool.get(card).powers[0]
            with self.subTest(card=card):
                self.assertTrue(effect.check(dataclasses.replace(power, text_ja=power.text_ja + "あ")))
        for card, effect in TRAINERS.items():
            definition = self.pool.get(card)
            with self.subTest(trainer=card):
                self.assertTrue(effect.check(dataclasses.replace(definition, trainer_text_ja=definition.trainer_text_ja + "あ")))
        # なにかの化石の文面にピッピ人形の役割を当てはめない
        self.assertTrue(E.PlayAsPokemon(hp=10, role="doll").check(self.pool.get(MYSTERIOUS_FOSSIL)))
        with self.assertRaises(ValueError):
            E.PlayAsPokemon(hp=10, role="statue")

    def test_new_types_are_kernel_programs_outside_the_v013_contract(self):
        # v0.48 からうしろに型が加わるので、v0.47 の型が続けて並んでいることを確かめる（v0.46 の確かめ方と同じ）
        start = ATTACK_TYPES_SINCE_V0_17.index(NEW_TYPES[0])
        self.assertEqual(ATTACK_TYPES_SINCE_V0_17[start:start + len(NEW_TYPES)], NEW_TYPES)
        for kind in NEW_TYPES:
            with self.subTest(kind=kind.__name__):
                self.assertNotIn(kind, v013_checks.VERIFIED)
                self.assertIn(kind, programs.BUILDERS)
                effect = next(E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect for k in E.DEFAULT_EFFECTS.attack_keys()
                              if type(E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect) is kind)
                self.assertFalse(contract.is_contract(contract.program_for(effect)))

    def test_adoption_records_and_external_checks(self):
        """採用の記録（kyuura データの採用。処理に使う文面は kyuura の印刷の文面）と pcg-search.com の同じ版との照合。ガイドブックの項目は書かない。"""
        records = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        for card in V0_47_CARDS:
            with self.subTest(card=card):
                record = records[card]
                self.assertEqual((record["basis"], record["status"]), ("kyuura_data", "adopted"))
                self.assertEqual(record["kyuura_records"], [])
                checks = record["external_checks"]
                self.assertEqual(len(checks), 1)
                self.assertTrue(checks[0]["url"].startswith("https://pcg-search.com/"))
                self.assertEqual(checks[0]["edition"]["list_number"], EDITIONS[card])
                if card in TEXT_DIFFERENCES:
                    self.assertEqual(checks[0]["result"], "differences")
                    self.assertEqual([(x["field"], x["affects_behavior"]) for x in checks[0]["differences"]], [(TEXT_DIFFERENCES[card], False)])
                else:
                    self.assertEqual((checks[0]["result"], checks[0]["differences"]), ("match", []))
                self.assertFalse({"page", "pdf_page", "latest_description_ja", "card_image_text_ja"} & set(_keys(record)))
        # なにかの化石・ピッピ人形の場での HP は kyuura の写しのトレーナーのデータにないので、pcg-search.com のページの値を採用の記録に書く
        for card in V0_47_TRAINERS:
            self.assertIn("HP", records[card]["notes"])
        self.assertEqual(cs.main([]), 0)


# ---------------------------------------------------------------- なにかの化石・ピッピ人形（印刷の分類と場での役割）


class PlayAsPokemonTest(unittest.TestCase):
    """手札・山札・サイド・トラッシュではトレーナーカード、場に出ているあいだだけポケモン（場での役割の定義）。"""

    def test_printed_classification_outside_play_and_role_in_play(self):
        state = board(mon(HITMONCHAN, (F,)), hand=[MYSTERIOUS_FOSSIL, CLEFAIRY_DOLL])
        for card in (MYSTERIOUS_FOSSIL, CLEFAIRY_DOLL):
            uid = card_of(state, 0, card)
            with self.subTest(card=card, zone="hand"):
                self.assertEqual(state.card_def(uid).category, "trainer")
                self.assertIsNone(state.card_def(uid).play_role)
        before = len(state.log)
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, MYSTERIOUS_FOSSIL)))
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, CLEFAIRY_DOLL)))
        audited(self, state)
        self.assertEqual([e["kind"] for e in events(state, before)], ["play_trainer", "play_trainer_as_pokemon"] * 2)
        self.assertIsNone(state.trainer_in_use)
        self.assertEqual(state.players[0].discard, [])
        for role, pokemon in zip(("fossil", "doll"), state.players[0].bench[1:]):
            with self.subTest(role=role):
                definition = state.card_def(pokemon.card)
                self.assertEqual((definition.category, definition.stage, definition.hp, definition.pokemon_type, definition.weakness,
                                  definition.resistance, definition.attacks, definition.powers, definition.play_role),
                                 ("pokemon", "basic", 10, None, None, None, (), (), role))
                self.assertEqual(state.printed_def(pokemon.card).category, "trainer")  # 印刷の定義は変えない
                self.assertEqual(pokemon.played_turn, TURN)

    def test_bench_full_is_rejected_before_leaving_the_hand(self):
        state = board(mon(HITMONCHAN), bench=[RATTATA] * 5, hand=[MYSTERIOUS_FOSSIL])
        assert_rejected(self, state, PlayTrainer(0, card_of(state, 0, MYSTERIOUS_FOSSIL)), "BENCH_FULL")

    def test_not_a_basic_pokemon_in_the_hand(self):
        """手札ではトレーナーカードなので、たねポケモンとしてベンチに出す操作・対戦準備の最初のポケモン（PF1）にはならない。"""
        state = board(mon(HITMONCHAN), hand=[CLEFAIRY_DOLL])
        with self.assertRaises(IllegalActionError):
            apply_kernel(state, PlayBasicToBench(0, card_of(state, 0, CLEFAIRY_DOLL)))

    def test_knock_out_is_not_counted_and_cards_go_to_the_discard(self):
        """場の役割のまま「きぜつ」したらトラッシュするが、カウントされない（相手はサイドを取らない。ログ knock_out の counted が False）。"""
        state = board(mon(MACHAMP, (F, F, F, F)), mon(MYSTERIOUS_FOSSIL, (W,)), current=0)
        state = attack(state, 0)  # ちきゅうなげ 60
        audited(self, state)
        ko = events(state, 0, "knock_out")
        self.assertEqual(len(ko), 1)
        self.assertIs(ko[0]["counted"], False)
        self.assertNotIn("take_prize", [e["kind"] for e in state.log])
        self.assertIn(state.cards[ko[0]["pokemon"]].card_id, [state.cards[u].card_id for u in state.players[1].discard])
        self.assertEqual(len(state.players[1].prizes), len(state.players[0].prizes))
        self.assertEqual(state.decision.kind, PROMOTE_ACTIVE)  # バトル場に出す（控えのコラッタ）

    def test_evolved_fossil_counts_as_a_knock_out(self):
        """進化カードがのったら（いちばん上が進化カード）ふつうのポケモンで、きぜつはカウントされる。"""
        state = board(mon(MACHAMP, (F, F, F, F)), mon(OMANYTE, (W,)))
        state = attack(state, 0)
        ko = events(state, 0, "knock_out")
        self.assertNotIn("counted", ko[0])
        self.assertEqual(state.decision.kind, "take_prize")
        audited(self, state)

    def test_poisoned_doll_knocked_out_at_the_pokemon_check_is_not_counted(self):
        state = board(mon(HITMONCHAN), {"card": CLEFAIRY_DOLL, "poison": 10})
        state = end_turn(state, 0)
        ko = events(state, 0, "knock_out")
        self.assertEqual(len(ko), 1)
        self.assertIs(ko[0]["counted"], False)
        self.assertNotIn("take_prize", [e["kind"] for e in state.log])
        audited(self, state)

    def test_discard_from_play(self):
        """自分の番の好きなときに（進化カードがのっていなければ）すてる。ついているカードもトラッシュ。きぜつではない（サイドを取られない）。"""
        state = board(mon(HITMONCHAN), bench=[RATTATA, mon(CLEFAIRY_DOLL, (W,))])
        pid = state.players[0].bench[1].pokemon_id
        before = len(state.log)
        state = apply_kernel(state, DiscardFromPlay(0, pid))
        audited(self, state)
        self.assertEqual([e["kind"] for e in events(state, before)], ["discard_from_play"])
        self.assertEqual(sorted(state.cards[u].card_id for u in state.players[0].discard), sorted([CLEFAIRY_DOLL, W]))
        self.assertEqual(state.phase, Phase.MAIN)
        self.assertEqual(state.card_def(card_of(state, 0, CLEFAIRY_DOLL, "discard")).category, "trainer")

    def test_discarding_the_active_fossil_promotes_a_bench_pokemon_or_loses(self):
        state = board(FOSSIL, bench=[RATTATA])
        state = apply_kernel(state, DiscardFromPlay(0, state.players[0].active.pokemon_id))
        self.assertEqual((state.decision.kind, state.decision.player), (PROMOTE_ACTIVE, 0))
        state = answer(state, (state.decision.options[0],))
        self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 0))
        audited(self, state)
        # 控えがいなければ、場にポケモンがいないので負け（p.311）
        lone = board(FOSSIL, bench=[])
        lone = apply_kernel(lone, DiscardFromPlay(0, lone.players[0].active.pokemon_id))
        self.assertEqual(lone.phase, Phase.GAME_OVER)
        self.assertEqual(lone.result.winner, 1)

    def test_discard_rejections(self):
        state = board(mon(OMANYTE), bench=[FOSSIL], opponent_bench=[DOLL])
        assert_rejected(self, state, DiscardFromPlay(0, state.players[0].active.pokemon_id), "NOT_DISCARDABLE")  # 進化カードがのっている
        assert_rejected(self, state, DiscardFromPlay(0, pid_of(state, 1, CLEFAIRY_DOLL)), "POKEMON_NOT_YOURS")
        assert_rejected(self, state, DiscardFromPlay(0, 999), "POKEMON_NOT_IN_PLAY")
        assert_rejected(self, state, DiscardFromPlay(1, pid_of(state, 1, CLEFAIRY_DOLL)), "NOT_YOUR_TURN")
        normal = board(mon(HITMONCHAN), bench=[RATTATA])
        assert_rejected(self, normal, DiscardFromPlay(0, normal.players[0].bench[0].pokemon_id), "NOT_DISCARDABLE")

    def test_discard_is_not_a_trainer_use_or_a_power(self):
        """トレーナーの使用の禁止（［アレルギーかふん］・ずつう）・かがくへんかガスは、すてることを止めない。"""
        state = board(mon(HITMONCHAN), bench=[DOLL, mon(DARK_VILEPLUME), mon(MUK)])
        state = apply_kernel(state, DiscardFromPlay(0, pid_of(state, 0, CLEFAIRY_DOLL)))
        audited(self, state)

    def test_retreat_of_the_active_fossil_is_unresolved(self):
        """「にげる」ことができるか（にげるエネルギーの数）は決まらない（PF2）。エネルギーのトラッシュ・こんらんのコインの前に止める。ポケモンいれかえは「にげる」では
        ないので使える（p.325）。"""
        state = board(mon(MYSTERIOUS_FOSSIL, (W,), confusion=True), bench=[RATTATA], hand=[SWITCH])
        assert_stops(self, state, Retreat(0, (), state.players[0].bench[0].card), PF2)
        assert_stops(self, state, Retreat(0, tuple(state.players[0].active.energy), state.players[0].bench[0].card), PF2)
        with self.assertRaises(UnsupportedError) as raised:
            E.retreat_cost(state, 0)
        self.assertEqual(raised.exception.code, PF2)
        switched = apply_kernel(state, PlayTrainer(0, card_of(state, 0, SWITCH)))
        switched = answer(switched, (switched.decision.options[0],))
        self.assertEqual(switched.card_def(switched.players[0].active.card).id, RATTATA)
        audited(self, switched)

    def test_evolving_onto_the_fossil_and_damage_energy_inheritance(self):
        state = board({"card": MYSTERIOUS_FOSSIL, "energy": [W], "damage": 0}, hand=[OMANYTE])
        state = apply_kernel(state, EvolvePokemon(0, card_of(state, 0, OMANYTE), state.players[0].active.pokemon_id))
        active = state.players[0].active
        self.assertEqual(state.card_def(active.card).name_ja, "オムナイト")
        self.assertEqual(len(active.evolution_stack), 1)
        self.assertEqual(state.card_def(active.evolution_stack[0]).play_role, "fossil")  # 重なったカードも場にあるので場での役割
        self.assertEqual(len(active.energy), 1)
        audited(self, state)
        # 手札のオムナイトをピッピ人形には重ねられない（名前が違う）
        doll = board(DOLL, hand=[OMANYTE])
        assert_rejected(self, doll, EvolvePokemon(0, card_of(doll, 0, OMANYTE), doll.players[0].active.pokemon_id), "EVOLUTION_NAME_MISMATCH")
        # その番に場に出したなにかの化石には、たねポケモンと同じく進化カードを重ねられない（p.310）
        fresh = board(mon(HITMONCHAN), hand=[MYSTERIOUS_FOSSIL, OMANYTE])
        fresh = apply_kernel(fresh, PlayTrainer(0, card_of(fresh, 0, MYSTERIOUS_FOSSIL)))
        assert_rejected(self, fresh, EvolvePokemon(0, card_of(fresh, 0, OMANYTE), pid_of(fresh, 0, MYSTERIOUS_FOSSIL)), "PLAYED_THIS_TURN")

    def test_breeder_onto_the_fossil_is_unresolved(self):
        """ポケモン育て屋さんで、場のなにかの化石（印刷のたねポケモンではない）にオムスター・カブトプスを重ねるか（PF3）。組がそれだけなら使う前に止め、ほかに
        進化させられる組があれば、なにかの化石を選ぶ答えだけを止める。"""
        state = board(FOSSIL, bench=[RATTATA], hand=[POKEMON_BREEDER, OMASTAR])
        assert_stops(self, state, PlayTrainer(0, card_of(state, 0, POKEMON_BREEDER)), PF3)
        both = board(FOSSIL, bench=[mon("PMCG1-001")], hand=[POKEMON_BREEDER, OMASTAR, "PMCG1-011"])
        both = apply_kernel(both, PlayTrainer(0, card_of(both, 0, POKEMON_BREEDER)))
        d = both.decision
        self.assertEqual(d.kind, SELECT_POKEMON)
        self.assertEqual(tuple(d.context_value("unresolved_choices")), (both.players[0].active.pokemon_id,))
        assert_stops(self, both, ResolveDecision(0, d.id, (both.players[0].active.pokemon_id,)), PF3)

    def test_setup_with_a_fossil_and_no_basic_pokemon_halts(self):
        """手札にたねポケモンがなく、なにかの化石・ピッピ人形があるときに切り直すか、最初のポケモンとして出せるかは決められない（PF1）。切り直す前に止める。
        seed は、この 2 つのデッキで先攻の手札がその形になる決まった値（探索ではなく、テストの前提として固定した値）。"""
        deck_a = expand_decklist({MYSTERIOUS_FOSSIL: 4, HITMONCHAN: 1, F: 55})
        deck_b = expand_decklist({HITMONCHAN: 4, F: 56})
        state = new_game(deck_a, deck_b, SETUP_SEED)
        self.assertEqual(state.phase, Phase.HALTED)
        self.assertEqual(state.halt.code, PF1)
        self.assertEqual(log_problems(state), [])
        hand = [state.cards[u].card_id for u in state.players[0].hand]
        self.assertNotIn(HITMONCHAN, hand)
        self.assertIn(MYSTERIOUS_FOSSIL, hand)

    def test_fossil_cannot_be_placed_as_a_starting_pokemon(self):
        deck_a = expand_decklist({MYSTERIOUS_FOSSIL: 4, HITMONCHAN: 4, MACHOP: 4, RATTATA: 4, DROWZEE: 4, F: 40})
        deck_b = expand_decklist({HITMONCHAN: 4, F: 56})
        state = new_game(deck_a, deck_b, PLACE_SEED)
        self.assertNotEqual(state.phase, Phase.HALTED)
        fossil = card_of(state, 0, MYSTERIOUS_FOSSIL)
        basic = card_of(state, 0, HITMONCHAN)
        assert_stops(self, state, PlaceStartingPokemon(0, fossil, ()), PF1)
        assert_stops(self, state, PlaceStartingPokemon(0, basic, (fossil,)), PF1)

    def test_gust_onto_a_benched_doll_and_trader_does_not_return_it(self):
        """突風で相手のベンチのピッピ人形を対戦ポケモンにできる（場のポケモン）。ポケモン交換おじさんは手札のピッピ人形（トレーナーカード）をもどせない。"""
        state = board(mon(HITMONCHAN), opponent_bench=[DOLL], hand=[GUST, POKEMON_TRADER, CLEFAIRY_DOLL])
        gusted = apply_kernel(state, PlayTrainer(0, card_of(state, 0, GUST)))
        gusted = answer(gusted, (pid_of(gusted, 1, CLEFAIRY_DOLL),))
        self.assertEqual(gusted.card_def(gusted.players[1].active.card).play_role, "doll")
        audited(self, gusted)
        assert_rejected(self, state, PlayTrainer(0, card_of(state, 0, POKEMON_TRADER)), "NO_POKEMON_CARD_IN_HAND")


# 対戦準備の seed（デッキと seed から決まる。tests の前提として固定した値。変えたら同じ性質の手札になる値を選び直す）
SETUP_SEED = 1
PLACE_SEED = 1


# ---------------------------------------------------------------- ［げんしのちから］（プテラ）


class PreventEvolutionTest(unittest.TestCase):
    """プテラが場にいる限り、全てのポケモンは（どの方法でも）進化できない。ねむり・マヒ・こんらん・かがくへんかガスで消える。"""

    def test_every_evolution_entry_point_is_blocked(self):
        state = board(mon(KOGAS_KAKUNA), mon(HITMONCHAN), bench=[mon(AERODACTYL), FOSSIL, DROWZEE, ERIKAS_CLEFAIRY, GIOVANNIS_MAGIKARP],
                      hand=[OMANYTE, HYPNO, POKEMON_BREEDER, KABUTOPS], deck=[ERIKAS_CLEFABLE, GIOVANNIS_GYARADOS, KOGAS_BEEDRILL] + [W] * 5)
        self.assertEqual(E.evolution_preventers(state), ((0, pid_of(state, 0, AERODACTYL), f"{AERODACTYL}@power0"),))
        assert_rejected(self, state, EvolvePokemon(0, card_of(state, 0, OMANYTE), pid_of(state, 0, MYSTERIOUS_FOSSIL)), "EVOLUTION_PREVENTED")
        assert_rejected(self, state, EvolvePokemon(0, card_of(state, 0, HYPNO), pid_of(state, 0, DROWZEE)), "EVOLUTION_PREVENTED")
        assert_rejected(self, state, PlayTrainer(0, card_of(state, 0, POKEMON_BREEDER)), "EVOLUTION_PREVENTED")
        # 相手のポケモンも
        theirs = board(mon(HITMONCHAN), mon(DROWZEE), bench=[mon(AERODACTYL)], opponent_hand=[HYPNO], current=1, turn=TURN + 1)
        assert_rejected(self, theirs, EvolvePokemon(1, card_of(theirs, 1, HYPNO), theirs.players[1].active.pokemon_id), "EVOLUTION_PREVENTED")
        # 山札から重ねる特殊能力（［うか］）: 「おもて」でも重ねられるカードがない
        coin = apply_kernel(with_coin_results(state, H), UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        self.assertIn("evolve_from_deck_none", [e["kind"] for e in coin.log])
        self.assertEqual(coin.card_def(coin.players[0].active.card).id, KOGAS_KAKUNA)
        audited(self, coin)

    def test_moon_power_evolves_nothing(self):
        state = board(mon(ERIKAS_CLEFAIRY, ("PMCG1-097",)), bench=[mon(AERODACTYL)], deck=[ERIKAS_CLEFABLE] + [W] * 5)
        after = attack(state, 0, H)
        self.assertNotIn("evolve", [e["kind"] for e in after.log])
        audited(self, after)

    def test_status_and_gas_switch_the_power_off(self):
        for spec, reason in ((mon(AERODACTYL, sleep=True), "ねむり"), (mon(AERODACTYL, confusion=True), "こんらん")):
            state = board(spec, bench=[DROWZEE], hand=[HYPNO])
            with self.subTest(reason=reason):
                self.assertEqual(E.evolution_preventers(state), ())
                evolved = apply_kernel(state, EvolvePokemon(0, card_of(state, 0, HYPNO), pid_of(state, 0, DROWZEE)))
                audited(self, evolved)
        gas = board(mon(HITMONCHAN), bench=[mon(AERODACTYL), mon(MUK), DROWZEE], hand=[HYPNO])
        self.assertEqual(E.evolution_preventers(gas), ())
        audited(self, apply_kernel(gas, EvolvePokemon(0, card_of(gas, 0, HYPNO), pid_of(gas, 0, DROWZEE))))

    def test_already_evolved_pokemon_stay_and_aerodactyl_blocks_another_aerodactyl(self):
        state = board(mon(HYPNO), bench=[mon(AERODACTYL), FOSSIL], hand=[AERODACTYL])
        self.assertEqual(state.card_def(state.players[0].active.card).id, HYPNO)
        assert_rejected(self, state, EvolvePokemon(0, card_of(state, 0, AERODACTYL), pid_of(state, 0, MYSTERIOUS_FOSSIL)), "EVOLUTION_PREVENTED")
        # プテラがいなければ、なにかの化石にプテラを重ねられ、そのあとはほかのポケモンが進化できない
        free = board(mon(HITMONCHAN), bench=[FOSSIL, DROWZEE], hand=[AERODACTYL, HYPNO])
        free = apply_kernel(free, EvolvePokemon(0, card_of(free, 0, AERODACTYL), pid_of(free, 0, MYSTERIOUS_FOSSIL)))
        assert_rejected(self, free, EvolvePokemon(0, card_of(free, 0, HYPNO), pid_of(free, 0, DROWZEE)), "EVOLUTION_PREVENTED")
        audited(self, free)


# ---------------------------------------------------------------- ［おみとおし］（オムナイト）と観測


class RevealHandTest(unittest.TestCase):
    """オムナイトが場にいる限り、相手の手札が全員（両方のプレイヤーと観戦者）に見える。観測（observation）だけが変わり、ゲームの処理は変わらない。"""

    def test_opponent_hand_is_visible_to_everyone_while_working(self):
        state = board(mon(HITMONCHAN), bench=[mon(OMANYTE)], hand=[POTION], opponent_hand=[BILL, W])
        self.assertEqual(E.hand_revealed_by(state, 1), ((0, pid_of(state, 0, OMANYTE), f"{OMANYTE}@power0"),))
        self.assertEqual(E.hand_revealed_by(state, 0), ())
        for viewer in (0, 1, None):
            with self.subTest(viewer=viewer):
                view = observe(state, viewer)
                self.assertEqual([c["card_id"] for c in view["players"][1]["hand"]["cards"]], [BILL, W])
                self.assertEqual(view["players"][0]["hand"]["cards"] is None, viewer != 0)  # オムナイトの持ち主の手札は見せない
        audited(self, state)

    def test_hidden_when_asleep_gassed_evolved_or_gone(self):
        cases = {
            "asleep": board(mon(OMANYTE, sleep=True), opponent_hand=[BILL]),
            "gas": board(mon(HITMONCHAN), bench=[mon(OMANYTE), mon(MUK)], opponent_hand=[BILL]),
            "evolved": board(mon(OMASTAR), opponent_hand=[BILL]),
            "absent": board(mon(HITMONCHAN), opponent_hand=[BILL]),
        }
        for name, state in cases.items():
            with self.subTest(case=name):
                self.assertEqual(E.hand_revealed_by(state, 1), ())
                self.assertIsNone(observe(state, 0)["players"][1]["hand"]["cards"])
                self.assertIsNone(observe(state, None)["players"][1]["hand"]["cards"])
                self.assertEqual(observe(state, 0)["players"][1]["hand"]["count"], 1)
                audited(self, state)

    def test_revealing_stops_at_the_moment_omanyte_evolves(self):
        """観測はその時点の場で決める（状態に「見た」記録を持たない）。オムスターに進化したら（いちばん上のカードに［おみとおし］がない）、その時点から見えない。
        前の観測で見えていた値は、その観測の値として残る。"""
        state = board(mon(HITMONCHAN), bench=[mon(OMANYTE)], hand=[OMASTAR], opponent_hand=[BILL])
        seen = observe(state, 0)
        self.assertEqual(seen["players"][1]["hand"]["cards"][0]["card_id"], BILL)
        evolved = apply_kernel(state, EvolvePokemon(0, card_of(state, 0, OMASTAR), pid_of(state, 0, OMANYTE)))
        self.assertIsNone(observe(evolved, 0)["players"][1]["hand"]["cards"])
        self.assertEqual(seen["players"][1]["hand"]["cards"][0]["card_id"], BILL)
        audited(self, evolved)

    def test_observation_hides_decks_prizes_and_setup(self):
        deck_a = expand_decklist({HITMONCHAN: 4, MACHOP: 4, RATTATA: 4, DROWZEE: 4, F: 44})
        state = new_game(deck_a, deck_a, 3)
        self.assertEqual(observation_problems(state), [])
        for viewer in (0, 1, None):
            view = observe(state, viewer)
            for owner in (0, 1):
                self.assertEqual(set(view["players"][owner]["deck"]), {"count"})
                self.assertEqual(set(view["players"][owner]["prizes"]), {"count", "face_up"})  # v0.63: おもてのサイド（ロケット団参上!）の一覧
                self.assertEqual(view["players"][owner]["prizes"]["face_up"], [])
                self.assertEqual(view["players"][owner]["hand"]["cards"] is None, viewer != owner)
        logged = visible_log(state, None)
        self.assertTrue(all("cards" not in e for e in logged if e["kind"] == "draw"))
        self.assertTrue(all("seed" not in e for e in logged if e["kind"] == "game_created"))
        with self.assertRaises(ValueError):
            observe(state, 2)

    def test_every_log_event_kind_has_a_visibility_rule(self):
        """ログのイベントの種類は、見えない項目のあるもの（PRIVATE_FIELDS）か公開のもの（PUBLIC_EVENTS）のどちらかちょうど一方。エンジンが出す種類はどれも
        どちらかにある（新しいイベントを加えたら決める。決めていない種類は visible_event が ValueError）。"""
        self.assertEqual(set(PRIVATE_FIELDS) & PUBLIC_EVENTS, set())
        source = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "kyuura_engine").rglob("*.py"))
        kinds = set(re.findall(r"add_event\(\s*\"([a-z_]+)\"", source))
        self.assertGreater(len(kinds), 100)
        self.assertEqual(kinds - set(PRIVATE_FIELDS) - PUBLIC_EVENTS, set())


# ---------------------------------------------------------------- ［カブトアーマー］とどくのダメージ


class KabutoArmorTest(unittest.TestCase):
    """受けるダメージは半分（切りすて）。p.321 の 8 段階。ダメージ以外の効果はそのまま。ねむり・マヒ・こんらんで使えない。"""

    def test_attack_damage_is_halved_rounding_down(self):
        state = board(mon(HITMONCHAN, (F, F, F)), mon(KABUTO))
        state = attack(state, 1)  # スペシャルパンチ 40 + 弱点 草なし → 40 → 20
        damage = events(state, 0, "damage")[-1]
        self.assertEqual(damage["amount"], 20)
        self.assertEqual([tuple(x) for x in damage["damage_halved"]], [(8, state.players[1].active.card, "down")])
        audited(self, state)
        odd = board(mon(JUNGLE_MANKEY, (F,)), mon(KABUTO))
        odd = attack(odd, 0)  # 10 → 半分の 5 を切りすて → 0
        self.assertEqual(events(odd, 0, "damage")[-1]["amount"], 0)
        self.assertEqual(odd.players[1].active.damage, 0)

    def test_not_while_asleep(self):
        state = board(mon(HITMONCHAN, (F, F, F)), mon(KABUTO, sleep=True))
        state = attack(state, 1)
        self.assertEqual(events(state, 0, "damage")[-1]["amount"], 40)

    def test_power_damage_is_halved(self):
        """ワザでない特殊能力のダメージ（はんげき）も受けるダメージなので半分にする（v0.46 の received_power_damage）。"""
        state = board(mon(KABUTO, (F,)), mon(MACHAMP, (F, F, F, F)), current=0)
        state = attack(state, 0)
        counter = events(state, 0, "counterattack")
        self.assertEqual(len(counter), 1)
        self.assertEqual(counter[0]["amount"], 0)
        self.assertEqual(counter[0]["amount_before"], 10)
        audited(self, state)

    def test_confused_kabuto_takes_the_full_confusion_damage(self):
        """こんらん状態のカブトはこの力を使えないので、こんらんの 20 に当てはめるか（v0.3c の問い）は起こらない（20 をそのまま受ける。弱点・抵抗力は自分のタイプ）。"""
        state = board(mon(KABUTO, (F,), confusion=True))
        state = attack(state, 0, T)
        self.assertEqual([e["amount"] for e in events(state, 0, "confusion_damage")], [20])
        audited(self, state)

    def test_poison_damage_on_kabuto_is_unresolved(self):
        """どくのダメージ（ワザのダメージではない）に「受けるダメージは半分」を当てはめるか（KA1）。当てはめると量が変わるので、ダメージを与える前に止める。"""
        state = board(mon(HITMONCHAN), {"card": KABUTO, "evolved_from": MYSTERIOUS_FOSSIL, "poison": 10}, deck=[W] * 3)
        halted = end_turn(state, 0)
        self.assertEqual(halted.phase, Phase.HALTED)
        self.assertEqual(halted.halt.code, KA1)
        self.assertNotIn("poison_damage", [e["kind"] for e in halted.log])
        audited(self, halted)
        # ねむりのカブト（使えない）なら止めず、どくのダメージ 10 を受ける
        asleep = board(mon(HITMONCHAN), {"card": KABUTO, "evolved_from": MYSTERIOUS_FOSSIL, "poison": 10, "sleep": True}, deck=[W] * 3)
        after = end_turn(asleep, 0)
        self.assertNotEqual(after.phase, Phase.HALTED)
        self.assertEqual([e["amount"] for e in events(after, 0, "poison_damage")], [10])

    def test_kabutops_absorb_heals_half_of_the_dealt_damage(self):
        """カブトプスのすいとる（kyuura の印刷の文面「相手にあたえたダメージの半分(切り上げ)のダメージカウンターを自分からとりのぞく。」。v0.4d の
        メガドレインと同じ型 ``DamageAndDrain``）: 与えたダメージ（最終ダメージ）40 の半分 → 2 個。のっている数まで。検証用の対戦では使われなかったので、
        ここで処理を確かめる。"""
        for damage, removed in ((30, 2), (10, 1), (0, 0)):
            with self.subTest(damage=damage):
                state = board(mon(KABUTOPS, (F, F, F, F), damage=damage))
                state = attack(state, 1)
                self.assertEqual(events(state, 0, "damage")[-1]["amount"], 40)
                heal = events(state, 0, "drain_heal")
                self.assertEqual([(h["dealt"], h["counters"]) for h in heal], [(40, removed)])
                self.assertEqual(state.players[0].active.damage, damage - removed * 10)
                audited(self, state)


# ---------------------------------------------------------------- ［スパイ］・［わるふざけ］


class PeekAndSwapTest(unittest.TestCase):
    def test_peek_targets_and_looking_does_not_move_cards(self):
        state = board(mon(JUNGLE_MANKEY), deck=[W, P], opponent_deck=[F], hand=[BILL], opponent_hand=[POTION, SWITCH], prizes=2)
        targets = E.peek_targets(state, 0)
        self.assertEqual(targets, (("deck", 0), ("deck", 1), ("prize", 0, 0), ("prize", 0, 1), ("prize", 1, 0), ("prize", 1, 1),
                                   ("hand", 1, 0), ("hand", 1, 1)))
        used = apply_kernel(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        d = used.decision
        self.assertEqual((d.kind, d.player, d.options), (PEEK_CARD, 0, tuple(range(8))))
        view = observe(used, 0)["decision"]
        self.assertEqual(view["options"][6], {"value": 6, "target": {"zone": "hand", "owner": 1, "position": 0}})
        self.assertNotIn("options", observe(used, 1)["decision"])
        looked = answer(used, (7,))
        look = events(looked, 0, "look_at_card")[-1]
        self.assertEqual((look["zone"], look["owner"], look["position"], looked.cards[look["card"]].card_id), ("hand", 1, 1, SWITCH))
        self.assertEqual(looked.players[1].hand, state.players[1].hand)  # 動かない
        self.assertEqual(looked.players[1].deck, state.players[1].deck)
        # 見たプレイヤーと（手札なら）持ち主にだけ見える。観戦者には見えない
        for viewer, sees in ((0, True), (1, True), (None, False)):
            shown = [e for e in visible_log(looked, viewer) if e["kind"] == "look_at_card"][-1]
            self.assertEqual("card" in shown, sees)
        audited(self, looked)
        # 自分の番に 1 回だけ
        assert_rejected(self, looked, UsePokemonPower(0, looked.players[0].active.pokemon_id, 0), "POWER_ALREADY_USED")

    def test_peek_at_a_prize_is_hidden_from_the_owner_opponent(self):
        state = board(mon(JUNGLE_MANKEY), prizes=2)
        used = answer(apply_kernel(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0)), (E.peek_targets(state, 0).index(("prize", 1, 0)),))
        shown = {viewer: [e for e in visible_log(used, viewer) if e["kind"] == "look_at_card"][-1] for viewer in (0, 1, None)}
        self.assertIn("card", shown[0])
        self.assertNotIn("card", shown[1])
        self.assertEqual(shown[1]["hidden"], {"card": None})
        self.assertNotIn("card", shown[None])

    def test_peek_is_blocked_by_status_and_gas(self):
        asleep = board(mon(JUNGLE_MANKEY, sleep=True))
        with self.assertRaises(IllegalActionError):
            apply_kernel(asleep, UsePokemonPower(0, asleep.players[0].active.pokemon_id, 0))
        gas = board(mon(JUNGLE_MANKEY), bench=[mon(MUK)])
        assert_rejected(self, gas, UsePokemonPower(0, gas.players[0].active.pokemon_id, 0), "POWER_SUPPRESSED")

    def test_swap_prize_with_deck_top(self):
        state = board(mon(ROCKET_RATTATA), deck=[W, P, F], prizes=3)
        p = state.players[0]
        prizes, deck = list(p.prizes), list(p.deck)
        used = apply_kernel(state, UsePokemonPower(0, p.active.pokemon_id, 0))
        d = used.decision
        self.assertEqual((d.kind, d.options), (SELECT_PRIZE_CARD, (0, 1, 2)))
        self.assertNotIn("card_id", json.dumps(observe(used, 0)["decision"]))  # 位置だけ
        swapped = answer(used, (1,))
        q = swapped.players[0]
        self.assertEqual(q.prizes, [prizes[0], deck[0], prizes[2]])
        self.assertEqual(q.deck, [prizes[1], *deck[1:]])
        swap = events(swapped, 0, "swap_prize_with_deck_top")[-1]
        self.assertEqual(set(swap), {"kind", "turn", "player", "prize_position", "power"})  # カードを書かない
        audited(self, swapped)
        assert_rejected(self, swapped, UsePokemonPower(0, q.active.pokemon_id, 0), "POWER_ALREADY_USED")

    def test_swap_without_prizes_or_deck_is_unresolved(self):
        no_deck = board(mon(ROCKET_RATTATA), deck=[], prizes=2)
        assert_stops(self, no_deck, UsePokemonPower(0, no_deck.players[0].active.pokemon_id, 0), PW3)
        no_prizes = board(mon(ROCKET_RATTATA), deck=[W], prizes=0)
        assert_stops(self, no_prizes, UsePokemonPower(0, no_prizes.players[0].active.pokemon_id, 0), PW3)


# ---------------------------------------------------------------- みらいよち・おどろかす


class ProphecyAndSurpriseTest(unittest.TestCase):
    def test_prophecy_arranges_the_top_cards(self):
        state = board(mon(HYPNO, (P,)), opponent_deck=[W, F, P, L, BILL])
        state = attack(state, 0)
        d = state.decision
        self.assertEqual((d.kind, d.options), (SELECT_DECK_OWNER, (0, 1)))
        state = answer(state, (1,))
        self.assertEqual((state.decision.kind, state.decision.options), (SELECT_LOOK_COUNT, (0, 1, 2, 3)))
        before = list(state.players[1].deck)
        # 0 枚は GS1（決定は待ったまま）
        assert_stops(self, state, ResolveDecision(0, state.decision.id, (0,)), GS1)
        state = answer(state, (3,))
        self.assertEqual((state.decision.kind, state.decision.options), (ARRANGE_DECK_TOP, tuple(before[:3])))
        state = answer(state, (before[2], before[0], before[1]))
        arranged = events(state, 0, "arrange_deck_top")[-1]
        self.assertEqual(tuple(arranged["cards"]), (before[2], before[0], before[1]))
        # ワザのあと番が終わり、相手は番の最初に一番上（並べかえた 1 枚目）を引く。その下の並びは見た部分のあとも変わらない
        self.assertEqual(events(state, 0, "draw")[-1]["cards"], (before[2],))
        self.assertEqual(state.players[1].deck, [before[0], before[1], *before[3:]])
        self.assertNotIn("shuffle", [e["kind"] for e in state.log])
        for viewer, sees in ((0, True), (1, False), (None, False)):
            logged = [e for e in visible_log(state, viewer) if e["kind"] in ("look_at_deck_top", "arrange_deck_top")]
            self.assertTrue(all(("cards" in e) == sees for e in logged))
        audited(self, state)

    def test_prophecy_one_card_and_empty_deck(self):
        one = board(mon(HYPNO, (P,)), deck=[W, F])
        one = answer(answer(attack(one, 0), (0,)), (1,))
        kinds = [e["kind"] for e in one.log]
        at = kinds.index("look_at_deck_top")
        self.assertEqual(kinds[at + 1], "arrange_deck_top")  # 1 枚なら並べかえの決定はない
        empty = board(mon(HYPNO, (P,)), opponent_deck=[])
        empty = answer(attack(empty, 0), (1,))
        self.assertIn("look_at_deck_top_none", [e["kind"] for e in empty.log])
        audited(self, empty)

    def test_surprise_looks_at_a_hand_card_and_returns_it(self):
        state = board(mon(LT_SURGES_EEVEE, (W,)), opponent_hand=[BILL, POTION])
        state = attack(state, 0)
        d = state.decision
        self.assertEqual((d.kind, d.options), (SELECT_HAND_CARD, (0, 1)))
        self.assertNotIn("card_id", json.dumps(observe(state, 0)["decision"]))
        target = state.players[1].hand[1]
        state = answer(state, (1,))
        kinds = [e["kind"] for e in state.log]
        at = kinds.index("look_at_card")
        self.assertEqual(kinds[at:at + 3], ["look_at_card", "hand_to_deck", "shuffle"])
        self.assertEqual(state.log[at + 2]["player"], 1)  # 相手の山札を切る
        self.assertNotIn(target, state.players[1].hand)
        self.assertIn(target, state.players[1].deck)
        hidden = [e for e in visible_log(state, None) if e["kind"] in ("look_at_card", "hand_to_deck")]
        self.assertTrue(all("card" not in e and "cards" not in e for e in hidden))
        audited(self, state)

    def test_surprise_with_an_empty_hand_is_unresolved(self):
        state = board(mon(LT_SURGES_EEVEE, (W,)), opponent_hand=[])
        assert_stops(self, state, UseAttack(0, 0), FC1)


# ---------------------------------------------------------------- ずつう・こうしゅうは（期限のあるトレーナーの使用の禁止）


class TrainerLockTest(unittest.TestCase):
    def locked(self):
        state = board(mon(FOSSIL_PSYDUCK, (P,)), opponent_hand=[POTION, CLEFAIRY_DOLL, SWITCH], opponent_deck=[W] * 5, deck=[W] * 5)
        state = attack(state, 0)
        return state

    def test_lock_is_given_to_the_opponent_player_until_the_end_of_the_next_turn(self):
        state = self.locked()
        self.assertEqual(state.trainer_locks, (TrainerUseLock(1, 0, state.players[0].active.card, f"{FOSSIL_PSYDUCK}#0", TURN, TURN + 1),))
        self.assertEqual(state.turn_number, TURN + 1)
        self.assertEqual(E.trainer_use_blockers(state, 1), (("lock", 0, f"{FOSSIL_PSYDUCK}#0", TURN + 1),))
        self.assertEqual(E.trainer_use_blockers(state, 0), ())
        for card in (POTION, CLEFAIRY_DOLL, SWITCH):
            with self.subTest(card=card):
                assert_rejected(self, state, PlayTrainer(1, card_of(state, 1, card)), "TRAINER_PREVENTED")
        audited(self, state)
        after = end_turn(state, 1)
        self.assertEqual(after.trainer_locks, ())
        removed = events(after, len(state.log), "trainer_lock_removed")
        self.assertEqual([(e["player"], e["reason"]) for e in removed], [(1, "expired")])
        audited(self, after)

    def test_lock_is_player_level(self):
        """場のポケモンではなくプレイヤーに与える: 効果を与えたポケモンが場をはなれても、相手の対戦ポケモンが入れかわっても消えない。「ワザをうけない」状態
        （バリアー）や「とうめい」の評価もしない。"""
        state = self.locked()
        self.assertEqual(state.players[1].active.persistent_effects, ())
        swapped = apply_kernel(state, Retreat(1, tuple(state.players[1].active.energy[:2]), state.players[1].bench[0].card))
        self.assertEqual(len(swapped.trainer_locks), 1)
        audited(self, swapped)

    def test_coexists_with_allergic_pollen(self):
        state = board(mon(FOSSIL_PSYDUCK, (P,)), bench=[mon(DARK_VILEPLUME)], opponent_hand=[POTION], opponent_deck=[W] * 5, deck=[W] * 5)
        state = attack(state, 0)
        blockers = E.trainer_use_blockers(state, 1)
        self.assertEqual([b[0] for b in blockers], ["power", "lock"])
        assert_rejected(self, state, PlayTrainer(1, card_of(state, 1, POTION)), "TRAINER_PREVENTED")

    def test_high_voltage_locks_only_on_heads(self):
        tails = attack(board(mon(LT_SURGES_JOLTEON, (L, W)), deck=[W] * 3, opponent_deck=[W] * 3), 0, T)
        self.assertEqual(tails.trainer_locks, ())
        heads = attack(board(mon(LT_SURGES_JOLTEON, (L, W)), deck=[W] * 3, opponent_deck=[W] * 3), 0, H)
        self.assertEqual(len(heads.trainer_locks), 1)
        self.assertEqual(heads.trainer_locks[0].effect, f"{LT_SURGES_JOLTEON}#0")
        audited(self, heads)

    def test_angry_thunder(self):
        state = board(mon(LT_SURGES_JOLTEON, (L, L, L), damage=30), mon(MACHAMP, damage=0))
        heads = attack(state, 1, H)
        self.assertEqual([e["amount"] for e in events(heads, 0, "damage")], [60])  # 30 + 3 × 10
        tails = attack(state, 1, T)
        self.assertEqual([(e.get("target", "opponent"), e["amount"]) for e in events(tails, 0, "damage")], [("opponent", 60), ("self", 30)])

    def test_format_12_carries_trainer_locks(self):
        state = self.locked()
        self.assertIn(12, FORMAT_VERSIONS)  # v0.48 で形式 13（type_shift）を加えた。禁止は形式 12 から書ける
        data = state_to_dict(state, format_version=12)
        self.assertEqual(data["trainer_locks"][0]["player"], 1)
        with self.assertRaises(ValueError):
            state_to_dict(state, format_version=11)
        plain = board(mon(HITMONCHAN))
        self.assertEqual(state_to_dict(plain, format_version=12)["trainer_locks"], [])
        self.assertEqual({k: v for k, v in state_to_dict(plain, format_version=12).items() if k not in ("trainer_locks", "format_version")},
                         {k: v for k, v in state_to_dict(plain, format_version=11).items() if k != "format_version"})

    def test_copied_headache(self):
        """ピッピの「ゆびをふる」で相手のずつうを自分のワザとして使うと、ピッピの相手（コダックの持ち主）に禁止を与える。"""
        state = board(mon(CLEFAIRY, (P, P, P)), mon(FOSSIL_PSYDUCK, (P,)), opponent_hand=[POTION], deck=[W] * 3, opponent_deck=[W] * 3)
        state = attack(state, 1)
        if state.decision is not None:
            state = answer(state, (0,))
        self.assertEqual([(lock.player, lock.source_player) for lock in state.trainer_locks], [(1, 0)])
        audited(self, state)


# ---------------------------------------------------------------- 正式な対戦開始からの対戦


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.47 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.47 の 4 組を 3 seed ずつ（席を入れかえて 24 局）。どれも監査の失敗（やり直し・不変条件・ログ・書き出し・観測）・想定外の拒否・内部エラーがなく、
        13 枚が場に出て使われる（勝敗は判断に使わない）。"""
        from tools import existing_effect_games as games

        results = games.run(range(3), pairings=games.PAIRINGS_V0_47)
        totals, observed = {}, {}
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"))
                if game["outcome"] == "halted":
                    self.assertEqual(game["halt_code"], PF1)
                for key, count in game["observed"].items():
                    observed[key] = observed.get(key, 0) + count
                for card, uses in game.get("card_uses", {}).items():
                    for key, count in uses.items():
                        totals[(card, key)] = totals.get((card, key), 0) + count
        for card, key in ((MYSTERIOUS_FOSSIL, "played_as_pokemon"), (CLEFAIRY_DOLL, "played_as_pokemon"), (CLEFAIRY_DOLL, "discarded_from_play"),
                          (MYSTERIOUS_FOSSIL, f"evolved_into_{OMANYTE}"), (MYSTERIOUS_FOSSIL, f"evolved_into_{KABUTO}"),
                          (MYSTERIOUS_FOSSIL, f"evolved_into_{AERODACTYL}"), (OMASTAR, "evolved_to"), (KABUTOPS, "evolved_to"),
                          (KABUTO, "armor_halved"), (JUNGLE_MANKEY, "peek_hand_opponent"), (ROCKET_RATTATA, "swap_prize"),
                          (HYPNO, "arrange_deck_top#0"), (LT_SURGES_EEVEE, "hand_to_deck#0"), (FOSSIL_PSYDUCK, "trainer_lock_added#0"),
                          (LT_SURGES_JOLTEON, "attack#1")):
            with self.subTest(card=card, key=key):
                self.assertGreater(totals.get((card, key), 0), 0)
        self.assertGreater(totals.get((MYSTERIOUS_FOSSIL, "knocked_out_uncounted"), 0) + totals.get((CLEFAIRY_DOLL, "knocked_out_uncounted"), 0), 0)
        self.assertGreater(observed.get("stopped_evolve_EVOLUTION_PREVENTED", 0), 0)
        self.assertGreater(observed.get("stopped_trainer_TRAINER_PREVENTED", 0), 0)
        self.assertGreater(observed.get(f"stopped_retreat_{PF2}", 0), 0)


class DocumentTest(unittest.TestCase):
    def test_document_names_the_stop_codes(self):
        text = DOC.read_text(encoding="utf-8")
        for code in (PF1, PF2, PF3, KA1):
            self.assertIn(code, text)


if __name__ == "__main__":
    unittest.main()
