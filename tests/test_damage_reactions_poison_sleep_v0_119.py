"""v0.119（docs/damage-reactions-poison-sleep-v0.119.md）: 受けるダメージの選択・どくとねむり・場の効果の 11 枚（ワザ 13・特殊能力 7）。コクーン（neo2-007）・パラセクト（neo3-005）・
ツボツボ（neo3-040）・レディバ（neo4-002）・わるいオーダイル（neo4-039）・わるいゲンガー（neo4-066）・カスミのパルシェン（GD2-007）・マタドガス（ES3-007）・ヒトデマン（ES3-017）・
ムウマ（PRN-036）・サカキのニドキング（PR1-068）。

根拠は kyuura データの採用（kyuura ``e519b99`` の data/cards.json の日本語の印刷の文面。11 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録（p.309 の処理の対象・
p.321 のダメージの計算の順番・p.322 のどく・p.323 のポケモンチェック・p.324 の同時のきぜつ・v0.34 の TP3・v0.38 の ``has_target``・v0.74 のポケモンタワー・v0.78 の鋼エネルギー・v0.94 の
任意の入れ替え・v0.114 のベイビィポケモン・v0.117 の LB2・v0.118 の［XXXXX］）。英語の欄・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合は
していない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.119``）。
プクリン（ES1-027）は文面の確認待ちで登録しない（docs 2 章）。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import unittest
from unittest import mock

from kyuura_engine import (
    DEFAULT_EFFECTS,
    EndTurn,
    EvolvePokemon,
    PlayBasicToBench,
    ResolveDecision,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import damage as D
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import DAMAGE_OPTION, FORCED_SWITCH
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.rules import RULES_2000_02_14
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import REPLACEMENT_KNOCKED, Poison
from tests import helpers as H
from tests.helpers import apply_kernel, build_test_state, with_coin_results
from tests.log_audit import LATEST_FORMAT, log_problems
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_unown_family_powers_v0_96 import snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "damage-reactions-poison-sleep-v0.119.md"
COMMIT = "e519b99e2adcc6c2cd0998569ae5ee1101de6e89"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
G, W, PS, F, L, R = H.GRASS, H.WATER, H.PSYCHIC, H.FIGHTING, H.LIGHTNING, H.FIRE
KAKUNA, PARASECT, SHUCKLE, LEDYBA = "neo2-007", "neo3-005", "neo3-040", "neo4-002"
FERALIGATR, GENGAR, CLOYSTER, WEEZING = "neo4-039", "neo4-066", "GD2-007", "ES3-007"
STARYU, MISDREAVUS, NIDOKING = "ES3-017", "PRN-036", "PR1-068"
V0119 = (KAKUNA, PARASECT, SHUCKLE, LEDYBA, FERALIGATR, GENGAR, CLOYSTER, WEEZING, STARYU, MISDREAVUS, NIDOKING)
KOFFING, NIDORAN, NIDORINO = "PMCG1-006", "PMCG6-004", "PMCG6-013"
ELEKID, MAGBY = "neo1-044", "neo1-022"
TYPHLOSION, PORYGON2, SLOWBRO, MOLTRES_R, ENTEI = "neo1-021", "neo4-097", "PMCG4-036", "PMCG5-020", "neo3-010"
TURN = 7
BELOW = {KAKUNA: ["neo2-002"], PARASECT: ["neo3-002"], FERALIGATR: ["neo4-028", "neo4-036"], GENGAR: ["neo4-048", "neo4-055"], CLOYSTER: ["GD2-006"],
         WEEZING: [KOFFING], NIDOKING: [NIDORAN, NIDORINO], NIDORINO: [NIDORAN], H.MUK: [H.GRIMER], TYPHLOSION: ["neo1-018", "neo1-020"],
         PORYGON2: ["PMCG1-064"], SLOWBRO: ["PMCG3-027"], "neo4-036": ["neo4-028"], "neo4-055": ["neo4-048"]}

PAIN_SPLIT = "自分にのっているダメージカウンターと同じ数のダメージカウンターを、相手にのせる。"
TOXIC = ("コインを投げて「おもて」なら、相手を「どく」状態にする。このワザによって「どく」状態になったポケモンは、ポケモンチェックのときにのせる「どく」によるダメージカウンターの数が、"
         "2倍になる。")
SECRETE = ("次の相手の番、このカードが相手のワザによるダメージを受けたとき(それによって、このカードが「きぜつ」しても)、相手を「どく」状態にし、相手の控えポケモン全員に、"
           "「弱点・抵抗力」に関係なく、それぞれ10ダメージ。")
GAS = "自分にも30ダメージ。このワザによって相手が「きぜつ」したなら、そのかわりに出てくる対戦ポケモンを「どく」状態にする。"
PULL_IN = "相手を「ねむり」状態にする。のぞむなら、ダメージと効果を与える前に、相手の控えポケモンを1匹選び、相手と入れ替えてよい。"
BEAM = "次の相手の番、自分の場の「水」ポケモンは「弱点」の影響を受けない。"
SWIFT = "このワザは、相手の「弱点・抵抗力・その他の効果」に関係なく、ダメージを与える。"
QUOTED = {
    KAKUNA: ("grass", 70, "stage1", "ビードル", (("どくをだす", ("grass", "grass"), None, SECRETE),), ()),
    PARASECT: ("grass", 60, "stage1", "パラス", (("ねむりバサミ", ("grass", "grass"), "30", "コインを投げて「おもて」なら、相手を「ねむり」状態にする。"),),
               (("アレルギーほうし", E.ALLERGY_SPORES_TEXT),)),
    SHUCKLE: ("fighting", 40, "basic", None, (("どくどくエキス", ("grass", "grass"), None, TOXIC),), (("かたいから", E.SetSmallAttackDamageReceived(40, 10).texts()[0]),)),
    LEDYBA: ("grass", 40, "basic", None, (("スピードスター", ("grass", "colorless"), "20", SWIFT),), ()),
    FERALIGATR: ("water", 80, "stage2", "わるいアリゲイツ", (("はかいのいちげき", ("water",) * 3, "50", "コインを投げて「おもて」なら、相手についている「エネルギーカード」を1枚トラッシュする。"),),
                 (("いあつ", E.SCARE_TEXT),)),
    GENGAR: ("psychic", 70, "stage2", "わるいゴースト", (("ひきずりこむ", ("psychic",) * 3, "30", PULL_IN),), (("ふかいねむり", E.DEEP_SLEEP_TEXT.format(n=2)),)),
    CLOYSTER: ("water", 70, "stage1", "カスミのシェルダー", (("トリプルキャノン", ("water", "water", "colorless"), "20×", "コインを3枚投げて「おもて」の数×20のダメージ。"),),
               (("シェルアーマー", E.SHELL_ARMOR_TEXT.format(n=10)),)),
    WEEZING: ("grass", 60, "stage1", "ドガース", (("ガスばくはつ", ("grass",) * 3, "40", GAS),), (("ポイズンミスト", E.POISON_MIST_TEXT.format(amount=20)),)),
    STARYU: ("water", 50, "basic", None, (("なぞのこうせん", ("water",), "10", BEAM), ("かいてんアタック", ("water", "colorless"), "20", None)), ()),
    MISDREAVUS: ("psychic", 50, "basic", None, (("いたみわけ", ("psychic",), None, PAIN_SPLIT),
                                               ("あやしいひかり", ("psychic", "psychic"), "10", "コインを投げて「おもて」なら、相手を「こんらん」状態にする。")), ()),
    NIDOKING: ("grass", 100, "stage2", "サカキのニドリーノ", (("じひびき", ("grass", "grass", "colorless", "colorless"), "50", E.RETREAT_LOCK_TEXT),),
               (("めいれい", E.CommandBonusToNamedAttackers().texts()[0]),)),
}
EXPECTED = {
    (KAKUNA, 0): E.SecretePoisonNextTurn(10), (PARASECT, 0): E.DamageThenSleepOnHeads(), (SHUCKLE, 0): E.ToxicPoisonOnHeadsWithoutDamage(2),
    (LEDYBA, 0): E.DamageIgnoringDefenderEffects(), (FERALIGATR, 0): E.DamageThenDiscardOpponentEnergy(on_heads=True),
    (GENGAR, 0): E.OptionalSwitchOpponentThenDamageAndSleep(), (CLOYSTER, 0): E.CoinFlipDamage(3, 20), (WEEZING, 0): E.DamageAndSelfDamageThenPoisonReplacement(30),
    (STARYU, 0): E.DamageThenOwnTypeWeaknessImmunityNextTurn(E.EnergyType.WATER), (STARYU, 1): E.DAMAGE_ONLY,
    (MISDREAVUS, 0): E.PlaceOwnCounterCountOnOpponent(), (MISDREAVUS, 1): E.ConfuseOnHeads(), (NIDOKING, 0): E.DamageThenRetreatLock(),
}
EXPECTED_POWERS = {PARASECT: E.DiscardPileImmunityToPokemonEffects(), SHUCKLE: E.SetSmallAttackDamageReceived(40, 10), FERALIGATR: E.ScareOpponentBabies(),
                   GENGAR: E.SleepCheckCoins(2), CLOYSTER: E.OptionalReduceAttackDamageReceived(10), WEEZING: E.CoinPoisonMistUntilNextTurn(20),
                   NIDOKING: E.CommandBonusToNamedAttackers()}
STOP_CODES = (("UNRESOLVED_SHELL_ARMOR_TIMING", "AM1"), ("UNRESOLVED_HARD_SHELL_NONPOSITIVE", "HS1"), ("UNRESOLVED_POISON_CHANGE_ORDER", "PO1"),
              ("UNRESOLVED_POISON_MIST_EARLIER_POISON", "PO2"), ("UNRESOLVED_POISON_MIST_SOURCE", "PO3"), ("UNRESOLVED_SECRETE_POISON_TARGET", "PX1"),
              ("UNRESOLVED_SCARE_SUPPRESSION_CYCLE", "IA1"), ("UNRESOLVED_DISCARD_PROTECTED_COIN", "AP1"), ("UNRESOLVED_DISCARD_PROTECTED_POWER_USE", "AP2"),
              ("UNRESOLVED_COMMAND_DAMAGE_SCOPE", "MD1"))


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, *, bench=(H.RATTATA,), opponent=None, opponent_bench=(H.RATTATA,), hand=(), deck=None, discard=(), opponent_deck=None, opponent_discard=(),
          opponent_hand=(), turn=TURN, current=0):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": list(deck if deck is not None else [W] * 10), "discard": list(discard), "prizes": 6}
    them = {"active": opponent or mon(H.RATTATA), "bench": list(opponent_bench), "hand": list(opponent_hand),
            "deck": list(opponent_deck if opponent_deck is not None else [W] * 10), "discard": list(opponent_discard), "prizes": 6}
    return build_test_state([me, them], turn_number=turn, current_player=current)


def attack(state, index=0, *coins, **kw):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, UseAttack(state.current_player, index, **kw))


def answer(state, choices, *coins):
    d = state.decision
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)))


def power(state, pid, index=0, *coins):
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UsePokemonPower(state.current_player, pid, index))


def end_turn(state, *coins):
    return apply_kernel(with_coin_results(state, *coins) if coins else state, EndTurn(state.current_player))


def last(state, kind):
    found = [e for e in state.log if e["kind"] == kind]
    return found[-1] if found else None


def pid(state, card_id, player=0):
    return next(p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card_id)


def uid(state, card_id, player=0, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def damage_of(state, player, which="active"):
    target = state.players[player].active if which == "active" else state.players[player].bench[which]
    return target.damage


def same_answers(test, state, choices, *coins):
    expected = answer(state, choices, *coins)
    for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
        test.assertEqual(snap(answer(other, choices, *coins)), snap(expected))
    return expected


# ---------------------------------------------------------------- 2 章・3 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_entries_and_printed_texts(self):
        """11 枚・13 のワザ・7 つの特殊能力の名前・必要なエネルギー・目安・説明と、タイプ・HP・段階・進化元は固定データと同じ。登録の型・引数も同じ。カスミのパルシェンの「ねむリ」は写しの値。"""
        pool = load_card_pool()
        self.assertEqual(set(read_extract()["pool_v0_119"]), set(V0119))
        self.assertEqual(sum(len(q[4]) for q in QUOTED.values()), 13)
        self.assertEqual(sum(len(q[5]) for q in QUOTED.values()), 7)
        self.assertIn("ねむリ", E.SHELL_ARMOR_TEXT)
        for card, (color, hp, stage, below, attacks, powers) in QUOTED.items():
            definition = pool.definitions[card]
            with self.subTest(card=card):
                self.assertIn(card, pool.playable_ids)
                self.assertEqual((definition.pokemon_type.value, definition.hp, definition.stage, definition.evolves_from), (color, hp, stage, below))
                self.assertEqual(len(definition.attacks), len(attacks))
                self.assertEqual(tuple((p.name_ja, p.text_ja) for p in definition.powers), powers)
            for index, (name, cost, display, text) in enumerate(attacks):
                printed = definition.attacks[index]
                entry = DEFAULT_EFFECTS.attack_entry(card, index)
                with self.subTest(card=card, index=index):
                    self.assertEqual((printed.name_ja, tuple(t.value for t in printed.cost), printed.damage_display, printed.text_ja), (name, cost, display, text))
                    self.assertEqual(entry.effect, EXPECTED[(card, index)])
                    if text is None:
                        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (name, None, None, None))
                    else:
                        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (name, text, text, "kyuura data/cards.json"))
                    self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card, printed, definition.attacks))
            for index, (name, text) in enumerate(powers):
                entry = DEFAULT_EFFECTS.power_entry(card, index)
                with self.subTest(card=card, power=index):
                    self.assertEqual(entry.effect, EXPECTED_POWERS[card])
                    self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (name, text, text, "kyuura data/cards.json"))
                    self.assertEqual(entry.effect.check(definition.powers[index]), [])

    def test_purin_is_not_registered_and_excluded_cards_stay_out(self):
        """プクリン（ES1-027）は文面の確認待ちで登録しない（採用の記録・保留の記録もない）。依頼の対象外のカードも登録しない。v0.122 で登録した 9 枚（GD3-003 など）は、v0.119 の
        範囲（v0.122 より前の写しの組）に入っていないことで確かめる（今の対応の有無は v0.122 のテスト）。"""
        from tests.release_catalog import cards_before

        pool = load_card_pool()
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        self.assertNotIn("neo4-082", pool.playable_ids)
        self.assertNotIn("neo4-082", sources)
        # v0.127: 怪電波マシーン（neo4-108）・ファイヤー（ES2-005・QSG-055）は、途中停止の基盤を加えて v0.127 で登録した（v0.119 の範囲の外。
        # tests/test_deferred_shortage_user_promos_v0_127.py）。v0.119 の範囲（v0.127 より前の写しの組）には入っていない
        before_v0_127 = cards_before(read_extract(), "0.127")
        for card in ("neo4-108", "ES2-005", "QSG-055"):
            with self.subTest(card=card):
                self.assertNotIn(card, before_v0_127)
                self.assertIn("v0.127 で加えた", sources[card]["notes"])
        # v0.125: プクリン（ES1-027）は、kyuura が p.226 の最新の説明を読んだ記録（LD-ES1-027-ATK0・PWR0）で v0.125 に登録した（v0.119 の範囲の外。
        # tests/test_wigglytuff_helping_hand_v0_125.py）。v0.119 の範囲（v0.125 より前の写しの組）には入っていない
        self.assertNotIn("ES1-027", cards_before(read_extract(), "0.125"))
        # v0.124: GR団のミュウツー（PRN-041）は v0.124 で登録した（v0.119 の範囲の外。tests/test_super_transform_dark_pulse_v0_124.py）
        self.assertNotIn("PRN-041", cards_before(read_extract(), "0.124"))
        before_v0_122 = cards_before(read_extract(), "0.122")
        for card in ("GD3-003", "ES2-011", "ES2-028", "ES2-029", "ES3-018", "PRN-030", "PRN-039", "PRN-040", "PRN-045"):
            with self.subTest(card=card):
                self.assertNotIn(card, before_v0_122)
                self.assertIn("v0.122 で加えた", sources[card]["notes"])

    def test_unregistered_without_the_v0_119_entries(self):
        """v0.119 の登録を除くと、対戦に使えなくなるのはちょうどこの 11 枚（ほかのカードは失われない）。"""
        registry = DEFAULT_EFFECTS.without_attacks("test-no-v0-119", E.V0_119_ATTACKS).without_powers("test-no-v0-119", E.V0_119_POWERS)
        before = load_card_pool().playable_ids
        after = pool_from_extract(read_extract(), registry).playable_ids
        self.assertEqual(before - after, set(V0119))
        self.assertLessEqual(after, before)

    def test_records_and_research_links(self):
        """採用の記録 11 件（kyuura_data・adopted・e519b99・2026-10-29・kyuura_records なし・外部照合なし）。研究の対応表の adopted_printed_text に説明文のある 12 のワザと 7 つの
        特殊能力。新しい停止コード 10 は not_in_kyuura で、この版の文書の略号に結ぶ。"""
        data = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        texts = []
        for card in V0119:
            record = data[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["recorded_on"], record["kyuura_records"], record["external_checks"],
                                  record["issues"]), ("kyuura_data", "adopted", COMMIT, "2026-10-29", list(H.V0_124_KYUURA_RECORDS_ADDED.get(card, ())), [], []))
                # v0.124: 研究の基準を b9e7cff に上げて、わるいオーダイル（neo4-039）に UQ-SUPER-TRANSFORM-SUPPRESSED-FORM の事例が加わった（tests/helpers.py）
                self.assertEqual(set(record["play_text"].values()), {"kyuura_printed_text"})
                texts += [f"{card}/{key}" for key in record["play_text"]]
        self.assertEqual(len(texts), 19)
        self.assertLessEqual(set(texts), set(links["latest_descriptions"]["adopted_printed_text"]))
        self.assertIn("UQ-SPEED-STAR-SCOPE", data[LEDYBA]["notes"])  # 到達性の欄の言及（事例ではない）を記録した
        for code, ruling in STOP_CODES:
            with self.subTest(code=code):
                self.assertEqual(links["stop_codes"][code], {"engine_rulings": [{"version": "v0.119", "document": "docs/damage-reactions-poison-sleep-v0.119.md",
                                                                                   "ruling_id": ruling}], "kyuura_issue": None, "kyuura_disposition": "not_in_kyuura"})

    def test_text_variants_are_exact(self):
        """既存の型に加えた書き方は全文 1 通りだけ（スピードスターの「その他の効果」）。決まった量の特殊などく（SpecialPoisonOnHeadsWithoutDamage）はどくどくエキスを受け付けない
        （量ではなくカウンターの数の倍）。近い文面・違う数は拒否する。"""
        import dataclasses

        pool = load_card_pool()
        swift = pool.definitions[LEDYBA].attacks[0]
        self.assertEqual(E.DamageIgnoringDefenderEffects().check(swift), [])
        self.assertNotEqual(E.DamageIgnoringDefenderEffects().check(dataclasses.replace(swift, text_ja=SWIFT.replace("その他の効果", "特殊能力"))), [])
        toxic = pool.definitions[SHUCKLE].attacks[0]
        self.assertNotEqual(E.SpecialPoisonOnHeadsWithoutDamage(20).check(toxic), [])
        self.assertEqual(E.ToxicPoisonOnHeadsWithoutDamage(2).check(toxic), [])
        self.assertNotEqual(E.ToxicPoisonOnHeadsWithoutDamage(3).check(toxic), [])
        self.assertNotEqual(E.SecretePoisonNextTurn(20).check(pool.definitions[KAKUNA].attacks[0]), [])
        self.assertNotEqual(E.DamageAndSelfDamageThenPoisonReplacement(20).check(pool.definitions[WEEZING].attacks[0]), [])
        shell = pool.definitions[SHUCKLE].powers[0]
        self.assertEqual(E.SetSmallAttackDamageReceived(40, 10).check(shell), [])
        self.assertNotEqual(E.SetSmallAttackDamageReceived(30, 10).check(shell), [])
        self.assertNotEqual(E.SleepCheckCoins(3).check(pool.definitions[GENGAR].powers[0]), [])
        self.assertNotEqual(E.OptionalReduceAttackDamageReceived(20).check(pool.definitions[CLOYSTER].powers[0]), [])
        self.assertNotEqual(E.CoinPoisonMistUntilNextTurn(30).check(pool.definitions[WEEZING].powers[0]), [])

    def test_programs_and_declared_elements(self):
        """要素の並び。相手の対戦ポケモンへの効果の宣言は、いたみわけのカウンター・どくどくエキスのどく・ひきずりこむの入れ替えとねむり。"""
        compile_attack = P.compile_attack
        self.assertEqual(compile_attack(E.OptionalSwitchOpponentThenDamageAndSleep()), (
            P.ForceSwitch(chooser="attacker", optional=True, carry=True), P.Damage(P.OPP, P.Printed()), P.Status(E.SLEEP)))
        self.assertEqual(compile_attack(E.ToxicPoisonOnHeadsWithoutDamage(2)), (P.Status(E.POISON, local_coin=HD, poison_multiplier=2),))
        self.assertEqual(compile_attack(E.DamageAndSelfDamageThenPoisonReplacement(30)), (
            P.Damage(P.OPP, P.Printed()), P.Damage(P.SELF, P.Fixed(30), name="self_damage"), P.ReplacementPoisonOnKnockOut()))
        self.assertEqual(compile_attack(E.DamageThenOwnTypeWeaknessImmunityNextTurn(E.EnergyType.WATER)), (P.Damage(P.OPP, P.Printed()), P.FieldWeaknessImmunity()))
        self.assertEqual(E.OptionalSwitchOpponentThenDamageAndSleep.opponent_effect_elements, (E.FORCED_SWITCH_ELEMENT, E.SLEEP))
        self.assertEqual(E.PlaceOwnCounterCountOnOpponent.opponent_effect_elements, (E.COUNTERS_ELEMENT,))
        for effect in (E.SecretePoisonNextTurn(10), E.DamageAndSelfDamageThenPoisonReplacement(30), E.DamageThenOwnTypeWeaknessImmunityNextTurn(E.EnergyType.WATER)):
            self.assertEqual(effect.opponent_effect_elements, ())

    def test_new_attack_types_are_kernel_programs(self):
        """新しいワザの型 6 つは解決の基盤の要素の並びで処理する（tests/helpers.py の ``ATTACK_TYPES_SINCE_V0_17``。v0.13 の止める関数で確かめる型に入れない）。"""
        from kyuura_engine.resolution import v013_checks

        new = (E.PlaceOwnCounterCountOnOpponent, E.DamageThenOwnTypeWeaknessImmunityNextTurn, E.ToxicPoisonOnHeadsWithoutDamage,
               E.OptionalSwitchOpponentThenDamageAndSleep, E.SecretePoisonNextTurn, E.DamageAndSelfDamageThenPoisonReplacement)
        start = H.ATTACK_TYPES_SINCE_V0_17.index(new[0])
        self.assertEqual(H.ATTACK_TYPES_SINCE_V0_17[start:start + len(new)], new)
        self.assertEqual({type(entry.effect) for entry in E.V0_119_ATTACKS.values()} - {type(E.DAMAGE_ONLY), E.DamageThenSleepOnHeads, E.DamageIgnoringDefenderEffects,
                                                                                     E.DamageThenDiscardOpponentEnergy, E.CoinFlipDamage, E.ConfuseOnHeads,
                                                                                     E.DamageThenRetreatLock}, set(new))
        for cls in new:
            with self.subTest(cls=cls.__name__):
                self.assertIn(cls, P.BUILDERS)
                self.assertNotIn(cls, v013_checks.VERIFIED)


# ---------------------------------------------------------------- 3 章: ［シェルアーマー］・［かたいから］・スピードスター


class ShellArmorTest(unittest.TestCase):
    """［シェルアーマー］: ワザによるダメージを受けるたびに、受けるポケモンの持ち主が使うかを選ぶ 8 段階の「-10」。"""

    def board(self, **cloyster):
        return board(mon(H.HITMONCHAN, (F,)), opponent=mon(CLOYSTER, **cloyster))

    def test_owner_chooses_before_the_damage_is_placed(self):
        asked = attack(self.board(), 0)  # ジャブ 20
        d = asked.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (DAMAGE_OPTION, 1, (pid(asked, CLOYSTER, 1),), 0, 1))
        self.assertEqual(damage_of(asked, 1), 0)
        for viewer in (0, 1, None):
            self.assertEqual(observe(asked, viewer)["decision"]["kind"], DAMAGE_OPTION)
        used = same_answers(self, asked, d.options)
        declined = answer(asked, ())
        self.assertEqual((damage_of(used, 1), damage_of(declined, 1)), (10, 20))
        card = asked.players[1].active.card
        self.assertEqual(last(used, "damage")["damage_option"], ((8, card, -10, 1),))
        self.assertEqual(last(declined, "damage")["damage_option"], ((8, card, -10, 0),))
        self.assertIn("8 カスミのパルシェン［シェルアーマー］", [s[0] for s in last(used, "damage")["steps"]])
        self.assertNotIn("8 カスミのパルシェン［シェルアーマー］", [s[0] for s in last(declined, "damage")["steps"]])
        for done in (used, declined):
            audited(self, done)
        with self.assertRaises(IllegalActionError):
            apply_kernel(asked, ResolveDecision(0, d.id, d.options))  # 選ぶのは受けるポケモンの持ち主

    def test_no_choice_when_nothing_to_reduce_asleep_or_suppressed(self):
        """使わない計算の最終ダメージが 0 以下（ディフェンダー）・受ける時にねむり・かがくへんかガスでは、聞かない（選ぶ意味がない・使えない）。"""
        zero = attack(self.board(trainers=[(H.DEFENDER, TURN)]), 0)
        self.assertIsNone(zero.decision)
        self.assertEqual(damage_of(zero, 1), 0)
        asleep = attack(self.board(sleep=True), 0)
        self.assertIsNone(asleep.decision)
        self.assertEqual(damage_of(asleep, 1), 20)
        gas = attack(board(mon(H.HITMONCHAN, (F,)), bench=(mon(H.MUK),), opponent=mon(CLOYSTER)), 0)
        self.assertIsNone(gas.decision)
        self.assertEqual(damage_of(gas, 1), 20)

    def test_order_ambiguity_is_am1_and_a_plain_offer(self):
        """8 段階のほかの効果の順番で、使わないときの最終ダメージが 0 にも 0 より大きくもなるなら、選べるかが決まらない（AM1。``OPTION_AMBIGUOUS``）。加算だけなら選ばせる（``OPTION_OFFER``）。"""
        pool = load_card_pool()
        attacker, defender = pool.definitions[H.HITMONCHAN], pool.definitions[CLOYSTER]
        armor = D.DamageModifier(8, -10, "armor", source=1, optional=True)
        doubled = D.DamageModifier(8, 2, "doubled", source=2, operation=D.MULTIPLY)
        minus = D.DamageModifier(8, -20, "defender", source=3)
        with self.assertRaises(D.DamageOptionRequired) as raised:
            D.calculate_attack_damage(20, attacker, defender, RULES_2000_02_14, (doubled, minus, armor))
        self.assertEqual((raised.exception.reason, raised.exception.finals), (D.OPTION_AMBIGUOUS, frozenset({0, 20})))
        with self.assertRaises(D.DamageOptionRequired) as offered:
            D.calculate_attack_damage(20, attacker, defender, RULES_2000_02_14, (D.DamageModifier(8, -10, "metal", source=3), armor))
        self.assertEqual(offered.exception.reason, D.OPTION_OFFER)
        self.assertEqual(D.calculate_attack_damage(20, attacker, defender, RULES_2000_02_14, (minus, armor)).final, 0)  # 使わなくても 0（聞かない）
        self.assertEqual(QUESTIONS["damage_option_timing"].code, "UNRESOLVED_SHELL_ARMOR_TIMING")

    def test_return_damage_frames_cannot_ask_and_stop(self):
        """返す効果のダメージ（R団のファイヤーの「ほのおのかべ」）を受けるときは、ワザの途中で決定を出せないので扱わない（``UNSUPPORTED_DAMAGE_OPTION_ELEMENT``。状態を変える前に止める）。"""
        state = board(mon(CLOYSTER, (W, W, W)), opponent=mon(MOLTRES_R, retaliation=TURN - 1))
        rejects(self, state, UseAttack(0, 0), "UNSUPPORTED_DAMAGE_OPTION_ELEMENT")


class HardShellTest(unittest.TestCase):
    """［かたいから］: ワザによって受ける 40 以下のダメージは、すべて 10（8 段階の SET_IF_AT_MOST）。"""

    def test_boundaries(self):
        cases = ((mon(H.HITMONCHAN, (F,)), 0, 10),  # 20 → 10
                 (mon(H.HITMONCHAN, (F, F, F)), 1, 10),  # 40 → 10
                 (mon(H.HITMONCHAN, (F, F, F), trainers=[(H.PLUSPOWER, TURN)]), 1, 50),  # 50 は変わらない
                 (mon(H.PARAS, (G, G)), 0, 10))  # 20 × 2（弱点）= 40 → 10
        for attacker, index, expected in cases:
            with self.subTest(attacker=attacker["card"], index=index, trainers=attacker.get("trainers")):
                done = attack(board(attacker, opponent=mon(SHUCKLE)), index)
                self.assertEqual(last(done, "damage")["amount"], expected)
                self.assertTrue(last(done, "damage").get("damage_set_if_at_most"))
                audited(self, done)

    def test_metal_energy_crosses_the_threshold_first(self):
        """鋼エネルギー（7 段階の「-10」）で 50 が 40 になってから、8 段階で 10。"""
        done = attack(board(mon(H.HITMONCHAN, (F, F, F), trainers=[(H.PLUSPOWER, TURN)]), opponent=mon(SHUCKLE, (H.METAL_ENERGY_NEO1,))), 1)
        self.assertEqual(damage_of(done, 1), 10)
        self.assertEqual([s[0][:1] for s in last(done, "damage")["steps"]][-2:], ["7", "8"])

    def test_zero_or_less_is_hs1_and_the_neighbour_passes(self):
        """計算の途中で 0 以下になったダメージに当てはめるかで結果が変わるなら HS1。0 より大きければ当てはめる（隣の止まらない場合）。"""
        rejects(self, board(mon(H.HITMONCHAN, (F,)), opponent=mon(SHUCKLE, trainers=[(H.DEFENDER, TURN)])), UseAttack(0, 0), "UNRESOLVED_HARD_SHELL_NONPOSITIVE")
        passed = attack(board(mon(H.HITMONCHAN, (F, F, F)), opponent=mon(SHUCKLE, trainers=[(H.DEFENDER, TURN)])), 1)  # 40 - 20 = 20 → 10
        self.assertEqual(damage_of(passed, 1), 10)

    def test_not_while_asleep_and_not_for_poison(self):
        asleep = attack(board(mon(H.HITMONCHAN, (F,)), opponent=mon(SHUCKLE, sleep=True)), 0)
        self.assertEqual(damage_of(asleep, 1), 20)
        poisoned = end_turn(board(mon(H.HITMONCHAN, (F,)), opponent=mon(SHUCKLE, poison=10)))
        self.assertEqual(last(poisoned, "poison_damage")["amount"], 10)


class SwiftTest(unittest.TestCase):
    def test_ledyba_ignores_the_receivers_own_effects(self):
        """レディバのスピードスターは、受けるポケモン自身の弱点・抵抗力・持っている効果（［かたいから］・［シェルアーマー］）に関係なく 20。場のほかのポケモンの効果で変わる場面は既存の SS1。"""
        done = attack(board(mon(LEDYBA, (G, G)), opponent=mon(SHUCKLE)), 0)
        self.assertEqual(damage_of(done, 1), 20)
        self.assertTrue(last(done, "damage").get("ignore_defender_effects"))
        armored = attack(board(mon(LEDYBA, (G, G)), opponent=mon(CLOYSTER)), 0)
        self.assertIsNone(armored.decision)
        self.assertEqual(damage_of(armored, 1), 20)


# ---------------------------------------------------------------- 9 章: ［めいれい］・なぞのこうせん・いたみわけ


class CommandTest(unittest.TestCase):
    def test_plus_ten_at_step_six_for_the_named_attackers(self):
        state = board(mon(NIDORINO, (G, G, G)), bench=(mon(NIDOKING),), opponent=mon(H.RATTATA))
        king = pid(state, NIDOKING)
        used = attack(state, 0, with_power=king)
        plain = attack(state, 0)
        self.assertEqual((last(used, "damage")["amount"], last(plain, "damage")["amount"]), (30, 20))
        self.assertIn("6 ［めいれい］", [s[0] for s in last(used, "damage")["steps"]])
        self.assertEqual(last(used, "damage")["modifiers"], ((6, state.players[0].bench[0].card, 10),))
        self.assertFalse([e for e in used.trainer_effects if e.kind == "group_attack_power_used"])  # 使った記録は持たない（［XXXXX］の記録とは別）
        audited(self, used)

    def test_exact_names_and_two_kings(self):
        """ニドキング自身・名前の違うポケモンのワザには使えない（拒否。状態を変えない）。2 匹いても 1 回のワザに 1 匹（どちらでも同じ量）。説明に特殊状態の条件はない（使い手はベンチに
        いるので、特殊状態にならない。p.322）。"""
        state = board(mon(NIDOKING, (G, G, G, G)), bench=(mon(NIDOKING),), opponent=mon(H.HITMONCHAN))
        with self.assertRaises(IllegalActionError):
            apply_kernel(state, UseAttack(0, 0, with_power=state.players[0].bench[0].pokemon_id))
        other = board(mon(H.HITMONCHAN, (F,)), bench=(mon(NIDOKING),), opponent=mon(H.HITMONCHAN))
        with self.assertRaises(IllegalActionError):
            apply_kernel(other, UseAttack(0, 0, with_power=other.players[0].bench[0].pokemon_id))
        two = board(mon(NIDORINO, (G, G, G)), bench=(mon(NIDOKING), mon(NIDOKING)), opponent=mon(H.HITMONCHAN))
        first, second = (p.pokemon_id for p in two.players[0].bench)
        self.assertEqual(damage_of(attack(two, 0, with_power=first), 1), 30)
        self.assertEqual(damage_of(attack(two, 0, with_power=second), 1), 30)


class MysteryBeamAndPainSplitTest(unittest.TestCase):
    def test_water_weakness_ignored_only_next_opponent_turn(self):
        state = board(mon(STARYU, (W,)), bench=(mon(H.STARYU),), opponent=mon(H.PIKACHU, (L,)))
        beamed = attack(state, 0)
        record = [e for e in beamed.trainer_effects if e.kind == "attack_field_weakness_immunity"]
        self.assertEqual(len(record), 1)
        self.assertEqual((record[0].player, record[0].expires_turn), (0, TURN + 1))
        hit = apply_kernel(beamed, UseAttack(1, 0))  # ピカチュウのかじる 10（雷）。ヒトデマンの弱点は雷
        self.assertFalse(last(hit, "damage")["weakness"])
        self.assertEqual(last(hit, "damage")["weakness_ignored_by_powers"], ((pid(state, STARYU), f"{STARYU}#0"),))
        audited(self, hit)

    def test_pain_split_places_counters_not_damage(self):
        state = board(mon(MISDREAVUS, (PS,), damage=30), opponent=mon(H.HITMONCHAN, trainers=[(H.DEFENDER, TURN)]))
        done = attack(state, 0)
        self.assertEqual(damage_of(done, 1), 30)  # ディフェンダー（ダメージを減らす）は、カウンターをのせることに当たらない
        self.assertEqual(damage_of(done, 0), 30)  # 自分からはとりのぞかない
        self.assertEqual(last(done, "place_damage_counters")["counters"], 3)
        empty = board(mon(MISDREAVUS, (PS,)), opponent=mon(H.HITMONCHAN))
        self.assertEqual(new_events(empty, attack(empty, 0), "place_damage_counters"), [])
        audited(self, done)


# ---------------------------------------------------------------- 5 章: どくの量（どくどくエキス・［ポイズンミスト］）


def weezing_board(active, *, opponent, bench_extra=(), hand=()):
    """自分のベンチに［ポイズンミスト］のマタドガス（使える状態）を置いた盤面。"""
    return board(active, bench=(mon(WEEZING), *bench_extra), opponent=opponent, hand=hand)


def mist(state, *coins):
    return power(state, pid(state, WEEZING), 0, *(coins or (HD,)))


class ToxicPoisonTest(unittest.TestCase):
    def test_heads_poisons_with_double_counters(self):
        state = board(mon(SHUCKLE, (G, G)), opponent=mon(H.HITMONCHAN))
        done = attack(state, 0, HD)  # ワザのあとの番の終わりのポケモンチェック
        condition = last(done, "special_condition")
        self.assertEqual((condition["condition"], condition["damage"], condition["multiplier"]), ("poison", 10, 2))
        self.assertEqual(done.players[1].active.conditions.poison, Poison(10, 2))
        checked = last(done, "poison_damage")
        self.assertEqual((checked["amount"], checked["multiplier"]), (20, 2))
        tails = attack(state, 0, TL)
        self.assertIsNone(tails.players[1].active.conditions.poison)
        self.assertNotIn("multiplier", last(end_turn(board(mon(H.HITMONCHAN, (F,)), opponent=mon(H.HITMONCHAN, poison=10))), "poison_damage"))
        audited(self, done)

    def test_overwrite_rules(self):
        """性質の違うどく状態（通常のどく）への「どくどくエキス」は既存の TP3。どくどくエキスのどく状態に通常のどくを与えると、通常のどくになる（p.322。特殊などく → 通常のどく）。"""
        rejects(self, board(mon(SHUCKLE, (G, G)), opponent=mon(H.HITMONCHAN, poison=10)), UseAttack(0, 0), "UNRESOLVED_SPECIAL_POISON_OVERWRITE")
        from kyuura_engine.conditions import poison

        state = attack(board(mon(SHUCKLE, (G, G)), opponent=mon(H.HITMONCHAN)), 0, HD)
        target = state.players[1].active
        poison(state, 1, target, effect="test")
        self.assertEqual(target.conditions.poison, Poison(10, 1))

    def test_check_knockout_uses_the_same_amount(self):
        """ポケモンチェックの前の見積もり（きぜつの判定）と実際のどくが同じ量（20）。残り HP 20 のポケモンはどくできぜつする。"""
        state = board(mon(SHUCKLE, (G, G)), opponent=mon(H.HITMONCHAN, damage=50), opponent_bench=(H.RATTATA,))
        done = attack(state, 0, HD)
        self.assertTrue([e for e in new_events(state, done, "knock_out") if e["player"] == 1])
        self.assertEqual(last(done, "poison_damage")["amount"], 20)


class PoisonMistTest(unittest.TestCase):
    def test_new_poison_takes_twenty(self):
        state = weezing_board(mon(H.WEEDLE, (G,)), opponent=mon(H.HITMONCHAN))
        misted = mist(state)
        added = last(misted, "poison_mist_added")
        self.assertEqual((added["amount"], added["created_turn"], added["expires_turn"], added["poisoned_before"]), (20, TURN, TURN + 2, ()))
        done = attack(misted, 0, HD)  # どくばり 10。「おもて」でどく（使ったあとのどく）
        checked = last(done, "poison_damage")
        self.assertEqual((checked["amount"], checked["poison_mists"]), (20, (pid(state, WEEZING),)))
        audited(self, done)
        no_heads = mist(state, TL)
        self.assertIsNone(last(no_heads, "poison_mist_added"))
        self.assertEqual(last(attack(no_heads, 0, HD), "poison_damage")["amount"], 10)

    def test_earlier_poison_is_po2_only_when_the_amount_differs(self):
        """使う前からどく状態のポケモンに当てはまるかで量が変わるなら PO2（ポケモンチェックで対戦を止める）。特殊などくの 20 なら量は同じなので止めない（隣の通る例）。"""
        earlier = end_turn(mist(weezing_board(mon(H.HITMONCHAN, (F,)), opponent=mon(H.HITMONCHAN, poison=10))))
        self.assertEqual((earlier.phase.value, earlier.halt.code), ("halted", "UNRESOLVED_POISON_MIST_EARLIER_POISON"))
        same = end_turn(mist(weezing_board(mon(H.HITMONCHAN, (F,)), opponent=mon(H.HITMONCHAN, poison=20))))
        self.assertEqual(last(same, "poison_damage")["amount"], 20)

    def test_doubled_poison_with_mist_is_po1_and_metal_is_fixed_last(self):
        """かける数のどくと［ポイズンミスト］は、当てはめる順番で 40・20 になるので PO1。鋼エネルギー（受けるダメージの「-10」）は［ポイズンミスト］のあと（既存の量の扱い）なので止めない。"""
        toxic = attack(mist(weezing_board(mon(SHUCKLE, (G, G)), opponent=mon(H.HITMONCHAN))), 0, HD)
        self.assertEqual((toxic.phase.value, toxic.halt.code), ("halted", "UNRESOLVED_POISON_CHANGE_ORDER"))
        metal = attack(mist(weezing_board(mon(H.WEEDLE, (G,)), opponent=mon(H.HITMONCHAN, (H.METAL_ENERGY_NIP1X,)))), 0, HD)
        checked = last(metal, "poison_damage")
        self.assertEqual((checked["amount"], checked["amount_before"]), (10, 20))

    def test_ends_on_status_and_expires_at_the_next_own_turn(self):
        state = board(mon(WEEZING, (G,)), opponent=mon(H.PARAS, (G, G)))
        misted = mist(state)
        slept = apply_kernel(end_turn(misted), UseAttack(1, 1))  # キノコのほうし（相手の番）
        removed = last(slept, "poison_mist_removed")
        self.assertEqual((removed["reason"], slept.poison_mists), ("special_condition", ()))
        expired = end_turn(end_turn(misted))
        self.assertEqual(last(expired, "poison_mist_removed")["reason"], "expired")
        self.assertEqual((expired.turn_number, expired.poison_mists), (TURN + 2, ()))
        asleep = board(mon(WEEZING, (G,), sleep=True), opponent=mon(H.HITMONCHAN))
        with self.assertRaises(IllegalActionError):
            apply_kernel(asleep, UsePokemonPower(0, pid(asleep, WEEZING), 0))  # ねむり・マヒ・こんらんの時は使えない

    def test_source_suppressed_is_po3(self):
        """使ったポケモンの特殊能力が消えた（かがくへんかガス）あと、効果が続くかで量が変わるなら PO3。"""
        state = weezing_board(mon(H.WEEDLE, (G,)), opponent=mon(H.HITMONCHAN), bench_extra=(mon(H.GRIMER),), hand=(H.MUK,))
        misted = mist(state)
        gassed = apply_kernel(misted, EvolvePokemon(0, uid(misted, H.MUK), pid(misted, H.GRIMER)))
        self.assertTrue(gassed.poison_mists[0].interrupted)
        self.assertEqual(last(gassed, "poison_mist_interrupted")["pokemon_id"], pid(state, WEEZING))
        done = attack(gassed, 0, HD)
        self.assertEqual((done.phase.value, done.halt.code), ("halted", "UNRESOLVED_POISON_MIST_SOURCE"))

    def test_save_formats(self):
        misted = mist(weezing_board(mon(H.WEEDLE, (G,)), opponent=mon(H.HITMONCHAN)))
        written = state_to_dict(misted, format_version=27)["poison_mists"]
        self.assertEqual([(r["pokemon_id"], r["created_turn"], r["interrupted"]) for r in written], [(pid(misted, WEEZING), TURN, False)])
        with self.assertRaises(ValueError):
            state_to_dict(misted, format_version=26)
        toxic = attack(board(mon(SHUCKLE, (G, G)), opponent=mon(H.HITMONCHAN, damage=0)), 0, HD)
        self.assertEqual(state_to_dict(toxic, format_version=27)["players"][1]["active"]["special_conditions"]["poison"], {"damage": 10, "multiplier": 2})
        with self.assertRaises(ValueError):
            state_to_dict(toxic, format_version=26)
        self.assertEqual(observe(misted, 1)["poison_mists"], written)
        # v0.120: 今の最新の形式は tests/test_catalog_contract.py（docs/testing.md）。ここは形式 27 があり、最新が監査の形式と同じことを確かめる
        self.assertIn(27, FORMAT_VERSIONS)
        self.assertEqual(max(FORMAT_VERSIONS), LATEST_FORMAT)


# ---------------------------------------------------------------- 7 章: ［ふかいねむり］・ひきずりこむ・［いあつ］


class DeepSleepTest(unittest.TestCase):
    def test_two_coins_and_all_heads(self):
        state = board(mon(H.HITMONCHAN, (F,)), bench=(mon(GENGAR),), opponent=mon(H.HITMONCHAN, sleep=True))
        for coins, recovered in (((HD, HD), True), ((HD, TL), False), ((TL, HD), False), ((TL, TL), False)):
            with self.subTest(coins=coins):
                done = end_turn(state, *coins)
                check = last(done, "sleep_check")
                self.assertEqual((check["coins"], check["results"], check["recovered"]), (2, tuple(c.value for c in coins), recovered))
                self.assertEqual(check["deep_sleep"], ((pid(state, GENGAR), f"{GENGAR}@power0"),))
                audited(self, done)

    def test_sleeping_source_and_two_sources(self):
        """持つポケモン自身がねむりならはたらかない（1 枚）。2 匹いても 2 枚（足さない）。両方の対戦ポケモンがねむりなら既存の Z29（順番）で止める。"""
        own = end_turn(board(mon(GENGAR, (PS,), sleep=True), opponent=mon(H.HITMONCHAN)), HD)
        self.assertEqual((last(own, "sleep_check")["result"], "coins" in last(own, "sleep_check")), ("heads", False))
        two = end_turn(board(mon(H.HITMONCHAN, (F,)), bench=(mon(GENGAR), mon(GENGAR)), opponent=mon(H.HITMONCHAN, sleep=True)), HD, HD)
        self.assertEqual(last(two, "sleep_check")["coins"], 2)
        both = end_turn(board(mon(H.HITMONCHAN, (F,), sleep=True), bench=(mon(GENGAR),), opponent=mon(H.HITMONCHAN, sleep=True)))
        self.assertEqual((both.phase.value, both.halt.code), ("halted", "UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER"))


class PullInTest(unittest.TestCase):
    def test_switch_before_damage_and_sleep(self):
        state = board(mon(GENGAR, (PS, PS, PS)), opponent=mon(H.HITMONCHAN), opponent_bench=(mon(H.HITMONCHAN),))
        asked = attack(state, 0)
        d = asked.decision
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices), (FORCED_SWITCH, 0, 0, 1))
        switched = same_answers(self, asked, (d.options[0],))
        self.assertEqual((switched.players[1].active.damage, switched.players[1].active.conditions.asleep), (60, True))  # 入れ替えたあとの相手（超の弱点）で計算する
        self.assertEqual((switched.players[1].bench[0].damage, switched.players[1].bench[0].conditions.names()), (0, ()))
        kept = answer(asked, ())
        self.assertEqual((kept.players[1].active.damage, kept.players[1].active.conditions.asleep), (60, True))
        alone = attack(board(mon(GENGAR, (PS, PS, PS)), opponent=mon(H.HITMONCHAN), opponent_bench=()), 0)
        self.assertIsNone(alone.decision)
        self.assertTrue(alone.players[1].active.conditions.asleep)
        audited(self, switched)

    def test_baby_rule_coin_is_flipped_once_for_the_declared_target(self):
        """ベイビィポケモンのルールのコインは、宣言のあと・説明の処理の前に、そのときのバトル場のベイビィポケモンで 1 回だけ（入れ替えで出てきたポケモンのために投げ直さない）。"""
        state = board(mon(GENGAR, (PS, PS, PS)), opponent=mon(ELEKID), opponent_bench=(mon(H.HITMONCHAN),))
        asked = attack(state, 0, HD)
        switched = answer(asked, (asked.decision.options[0],))
        self.assertEqual(len([e for e in new_events(state, switched, "coin_flip") if e.get("source") == "baby_rule"]), 1)
        self.assertEqual(switched.players[1].active.damage, 60)


class ScareTest(unittest.TestCase):
    def test_opponent_babies_cannot_use_attacks_or_powers(self):
        flipped = build_test_state([{"active": mon(FERALIGATR), "deck": [W] * 6}, {"active": mon(ELEKID, (L,)), "bench": [H.RATTATA], "deck": [W] * 6}],
                                   turn_number=TURN - 1, current_player=1)
        rejects(self, flipped, UsePokemonPower(1, flipped.players[1].active.pokemon_id, 0), "POWER_SUPPRESSED", error=IllegalActionError)
        magby = build_test_state([{"active": mon(FERALIGATR), "deck": [W] * 6}, {"active": mon(MAGBY, (R,)), "deck": [W] * 6}], turn_number=TURN - 1, current_player=1)
        rejects(self, magby, UseAttack(1, 0), "ATTACK_PREVENTED", error=IllegalActionError)
        asleep = build_test_state([{"active": mon(FERALIGATR, sleep=True), "deck": [W] * 6}, {"active": mon(ELEKID, (L,)), "deck": [W] * 6}],
                                  turn_number=TURN - 1, current_player=1)
        self.assertIsNotNone(apply_kernel(asleep, UsePokemonPower(1, asleep.players[1].active.pokemon_id, 0)))

    def test_lasting_effects_of_scared_babies_are_ignored_while_scared(self):
        """ベイビィポケモンが与えた持続する効果（［じっとみる］の BenchPowersStopped）は、［いあつ］がはたらく間は当てはめない（記録は消さない）。"""
        from kyuura_engine.persistent import powers_stopped
        from kyuura_engine.state import BenchPowersStopped

        state = build_test_state([{"active": mon(FERALIGATR), "bench": [mon(GENGAR)], "deck": [W] * 6},
                                  {"active": mon("neo2-050"), "deck": [W] * 6}], turn_number=TURN - 1, current_player=1)
        target = state.players[0].bench[0]
        target.persistent_effects = (BenchPowersStopped(source_card=state.players[1].active.card, source_player=1, created_turn=TURN - 1, active_turn=TURN - 1),)
        self.assertIsNone(powers_stopped(state, target))
        calm = build_test_state([{"active": mon(H.HITMONCHAN), "bench": [mon(GENGAR)], "deck": [W] * 6},
                                 {"active": mon("neo2-050"), "deck": [W] * 6}], turn_number=TURN - 1, current_player=1)
        calm.players[0].bench[0].persistent_effects = (BenchPowersStopped(source_card=calm.players[1].active.card, source_player=1, created_turn=TURN - 1,
                                                                           active_turn=TURN - 1),)
        self.assertIsNotNone(powers_stopped(calm, calm.players[0].bench[0]))

    def test_cycle_with_magby_smokescreen_is_ia1(self):
        """相手のブビィの「モクモク」（おたがいの場の特殊能力を止める）がはたらく間に、［いあつ］のわるいオーダイルがバトル場に出ると循環なので IA1。ほかのポケモンなら通る。"""
        state = build_test_state([{"active": mon(H.RATTATA), "bench": [mon(FERALIGATR), mon(H.HITMONCHAN)], "deck": [W] * 6},
                                  {"active": mon(MAGBY, (R,)), "deck": [W] * 6}], turn_number=TURN - 1, current_player=1)
        smoked = attack(state, 0)
        self.assertEqual(smoked.current_player, 0)
        rattata = smoked.players[0].active
        from kyuura_engine import Retreat

        rejects(self, smoked, Retreat(0, tuple(rattata.energy), smoked.players[0].bench[0].card), "UNRESOLVED_SCARE_SUPPRESSION_CYCLE")
        passed = apply_kernel(smoked, Retreat(0, tuple(rattata.energy), smoked.players[0].bench[1].card))
        self.assertEqual(passed.cards[passed.players[0].active.card].card_id, H.HITMONCHAN)

    def test_stare_on_a_gas_holder_is_the_same_cycle(self):
        """［いあつ］の力を消すかがくへんかガスのポケモンが、相手のベイビィポケモンの［じっとみる］を受けていると、答えが自分にもどるので IA1（計算の順番で片方を勝たせない）。"""
        from kyuura_engine.persistent import powers_stopped
        from kyuura_engine.state import BenchPowersStopped

        state = build_test_state([{"active": mon(FERALIGATR), "bench": [mon(H.MUK)], "deck": [W] * 6},
                                  {"active": mon("neo2-050"), "deck": [W] * 6}], turn_number=TURN - 1, current_player=1)
        muk = state.players[0].bench[0]
        muk.persistent_effects = (BenchPowersStopped(source_card=state.players[1].active.card, source_player=1, created_turn=TURN - 1, active_turn=TURN - 1),)
        with self.assertRaises(UnsupportedError) as caught:
            powers_stopped(state, muk)
        self.assertEqual(caught.exception.code, "UNRESOLVED_SCARE_SUPPRESSION_CYCLE")


# ---------------------------------------------------------------- 6 章: どくをだす・ガスばくはつ


class SecretePoisonTest(unittest.TestCase):
    def given(self, **kakuna):
        state = board(mon(KAKUNA, (G, G), **kakuna), opponent=mon(H.HITMONCHAN, (F,)), opponent_bench=(mon(SHUCKLE), mon(H.RATTATA)))
        return attack(state, 0)

    def test_poisons_the_attacker_and_damages_every_bench(self):
        given = self.given()
        self.assertEqual(given.current_player, 1)
        hit = apply_kernel(given, UseAttack(1, 0))  # ジャブ 20
        fired = last(hit, "secrete_poison")
        self.assertEqual((fired["received_damage"], fired["trigger"]), (20, f"{H.HITMONCHAN}#0"))
        self.assertIsNotNone(hit.players[1].active.conditions.poison)
        bench = [e for e in new_events(given, hit, "damage") if e.get("secrete_poison")]
        self.assertEqual([(e["amount"], e["weakness"], e["resistance"]) for e in bench], [(10, False, False), (10, False, False)])  # ツツボツの弱点（草）に関係なく
        audited(self, hit)

    def test_works_when_knocked_out_not_on_zero_damage(self):
        knocked = apply_kernel(self.given(damage=60), UseAttack(1, 0))
        self.assertTrue(last(knocked, "secrete_poison"))
        self.assertTrue([e for e in knocked.log if e["kind"] == "knock_out" and e["player"] == 0])
        guarded = apply_kernel(self.given(trainers=[(H.DEFENDER, TURN + 1)]), UseAttack(1, 0))  # 20 - 20 = 0
        self.assertIsNone(last(guarded, "secrete_poison"))

    def test_copy_is_unsupported(self):
        """相手のワザとして使う（ゆびをふる）と、効果を持つポケモンのカードのワザの位置で記録するので表せない（エンジンの未対応。v0.12 の返す効果と同じ）。"""
        rejects(self, board(mon(H.CLEFAIRY, (W, W, W)), opponent=mon(KAKUNA)), UseAttack(0, 1), "UNSUPPORTED_COPIED_ATTACK")

    def test_only_next_opponent_turn(self):
        given = self.given()
        record = [e for e in given.players[0].active.persistent_effects if e.kind == "secrete_poison"]
        self.assertEqual((record[0].created_turn, record[0].active_turn), (TURN, TURN + 1))
        later = end_turn(end_turn(given))
        self.assertFalse([e for e in later.players[0].active.persistent_effects if e.kind == "secrete_poison"])


class GasExplosionTest(unittest.TestCase):
    def given(self, **target):
        return board(mon(WEEZING, (G, G, G)), opponent=mon(H.HITMONCHAN, **target), opponent_bench=(mon(H.HITMONCHAN),))

    def promote(self, state):
        while state.decision is not None and state.decision.kind != "promote_active":
            d = state.decision
            state = apply_kernel(state, ResolveDecision(d.player, d.id, (d.options[0],)))
        return state

    def test_the_replacement_is_poisoned(self):
        knocked = self.promote(attack(self.given(damage=40), 0))
        self.assertEqual(knocked.decision.kind, "promote_active")
        self.assertEqual([r.status for r in knocked.replacement_poisons], [REPLACEMENT_KNOCKED])
        written = state_to_dict(knocked, format_version=27)["replacement_poisons"]
        self.assertEqual([(r["player"], r["status"]) for r in written], [(1, "knocked")])
        with self.assertRaises(ValueError):
            state_to_dict(knocked, format_version=26)
        self.assertEqual(observe(knocked, 0)["replacement_poisons"], written)
        promoted = same_answers(self, knocked, knocked.decision.options[:1])
        self.assertIsNotNone(promoted.players[1].active.conditions.poison)
        self.assertEqual(promoted.replacement_poisons, ())
        self.assertEqual(last(promoted, "replacement_poison")["effect"], f"{WEEZING}#0")
        audited(self, promoted)

    def test_survivor_and_game_over(self):
        survived = attack(self.given(), 0)
        self.assertEqual((survived.replacement_poisons, [e["kind"] for e in survived.log if e["kind"].startswith("replacement_poison")]), ((), []))
        last_one = attack(board(mon(WEEZING, (G, G, G)), opponent=mon(H.HITMONCHAN, damage=40), opponent_bench=()), 0)
        while last_one.decision is not None:
            d = last_one.decision
            last_one = apply_kernel(last_one, ResolveDecision(d.player, d.id, (d.options[0],)))
        self.assertEqual((last_one.phase.value, last_one.replacement_poisons, last(last_one, "replacement_poison_removed")["reason"]), ("game_over", (), "game_over"))


# ---------------------------------------------------------------- 8 章: ［アレルギーほうし］


class AllergySporesTest(unittest.TestCase):
    """おたがいのトラッシュのカードは、ポケモンのワザ・特殊能力の効果を受けない（場のどこでも。ねむり・マヒ・こんらんでは、はたらかない）。経路ごとに、トラッシュのカードを動かす部分だけを
    起こさない。トレーナー・スタジアム・エネルギー自身の効果、数えること、トラッシュに置くことは当たらない。"""

    PARASECT_BENCH = mon(PARASECT)

    def test_attack_parts_on_the_discard_do_not_happen_the_rest_stays(self):
        """エナジーへんかん（手札に加える）は起こらず、自分への 10 は残る。ぎゃくりゅう（数える・山札にもどす）は、数えたダメージは残り、もどさずに切る。"""
        state = board(mon(H.GASTLY, (PS, PS)), discard=(PS, PS), opponent=mon(H.HITMONCHAN), opponent_bench=(self.PARASECT_BENCH,))
        done = attack(state, 1)
        protected = last(done, "discard_protected")
        self.assertEqual((protected["element"], protected["protected_by"]), ("recover_energy", [[pid(state, PARASECT, 1), f"{PARASECT}@power0"]]))
        self.assertEqual((len(done.players[0].discard), done.players[0].active.damage), (2, 10))
        audited(self, done)
        backflow = board(mon("PF1-009", (W, W, W), evolved_from=["PF1-007", "PF1-008"]), discard=(W, W), opponent=mon(H.HITMONCHAN),
                         opponent_bench=(self.PARASECT_BENCH,))
        flowed = attack(backflow, 0)
        self.assertEqual(last(flowed, "damage")["amount"], 30)  # 目安 + トラッシュの「水」2 枚 × 10（数えることは効果を受けることではない）
        self.assertEqual((len(flowed.players[0].discard), last(flowed, "attack_discard_to_deck")["cards"]), (2, ()))

    def test_coin_only_for_protected_cards_is_ap1_but_no_target_flips_nothing(self):
        """コインが決めるのが効果を受けないトラッシュのカードを動かすことだけなら、投げるかが決まらない（AP1）。選べるカードがないなら、今までどおり投げない（処理の対象がない）。
        カードがなくても投げる今までの読み方のワザ（もちさる）は、どちらの読み方でも投げるので止めない。"""
        wisp = board(mon("GD5-003", (R,)), discard=(R, R), opponent=mon(H.HITMONCHAN), opponent_bench=(self.PARASECT_BENCH,))
        rejects(self, wisp, UseAttack(0, 1), "UNRESOLVED_DISCARD_PROTECTED_COIN")
        empty = board(mon("GD5-003", (R,)), discard=(G,), opponent=mon(H.HITMONCHAN), opponent_bench=(self.PARASECT_BENCH,))
        quiet = attack(empty, 1)
        self.assertEqual(new_events(empty, quiet, "coin_flip"), [])
        mischief = board(mon("PMCG6-056", (G,)), opponent=mon(H.HITMONCHAN), opponent_bench=(self.PARASECT_BENCH,), opponent_discard=(G,))
        rejects(self, mischief, UseAttack(0, 0), "UNRESOLVED_DISCARD_PROTECTED_COIN")
        aipom = board(mon("neo1-067", (G,)), bench=(mon(H.RATTATA),), discard=(G, R), opponent=mon(H.HITMONCHAN), opponent_bench=(self.PARASECT_BENCH,))
        taken = attack(aipom, 0, HD)
        self.assertEqual((len(taken.players[0].discard), last(taken, "discard_protected")["element"]), (2, "discard_to_deck"))
        asleep = board(mon("GD5-003", (R,)), discard=(R, R, R), opponent=mon(PARASECT, sleep=True))
        woke = attack(asleep, 1, HD, TL, TL)  # ねむりのパラセクトの力ははたらかない（「おもて」1 枚ぶんを手札に加える）
        self.assertEqual(len(answer(woke, woke.decision.options[:1]).players[0].discard), 2)

    def test_powers_whole_part_and_offers(self):
        """効果がすべてトラッシュのカードを動かす宣言する特殊能力は AP2（トラッシュに対象がないときは既存の PW3・SX1）。［おたけび］はトラッシュすることと番の終わりが残る。
        ［つりあげる］・ふしちょうは、使っても同じなので機会を出さない（ログ discard_protected）。"""
        typhlosion = board(mon(TYPHLOSION), bench=(self.PARASECT_BENCH,), discard=(R,), opponent=mon(H.HITMONCHAN))
        rejects(self, typhlosion, lambda s: UsePokemonPower(0, pid(s, TYPHLOSION), 0), "UNRESOLVED_DISCARD_PROTECTED_POWER_USE")
        no_fire = board(mon(TYPHLOSION), bench=(self.PARASECT_BENCH,), discard=(G,), opponent=mon(H.HITMONCHAN))
        rejects(self, no_fire, lambda s: UsePokemonPower(0, pid(s, TYPHLOSION), 0), "UNRESOLVED_POWER_ZERO_CARDS")
        porygon = board(mon(PORYGON2), discard=("neo1-086",), opponent=mon(H.HITMONCHAN), opponent_bench=(self.PARASECT_BENCH,))
        rejects(self, porygon, lambda s: UsePokemonPower(0, pid(s, PORYGON2), 0), "UNRESOLVED_DISCARD_PROTECTED_POWER_USE")
        entei = board(mon(H.HITMONCHAN), bench=(self.PARASECT_BENCH,), hand=(ENTEI,), deck=[R, G, R, G, G, G, G], opponent=mon(H.HITMONCHAN))
        offered = apply_kernel(entei, PlayBasicToBench(0, uid(entei, ENTEI)))
        howled = answer(offered, offered.decision.options)
        self.assertEqual((len(last(howled, "deck_top_to_discard")["cards"]), last(howled, "discard_protected")["cards"]), (5, tuple(
            u for u in last(howled, "deck_top_to_discard")["cards"] if howled.card_def(u).id == R)))
        self.assertEqual(howled.current_player, 1)  # 番は終わる
        reel = board(mon("PMCG3-027"), bench=(self.PARASECT_BENCH,), hand=(SLOWBRO,), discard=(H.HITMONCHAN,), opponent=mon(H.HITMONCHAN))
        evolved = apply_kernel(reel, EvolvePokemon(0, uid(reel, SLOWBRO), reel.players[0].active.pokemon_id))
        self.assertIsNone(evolved.decision)
        self.assertEqual(last(evolved, "discard_protected")["power"], f"{SLOWBRO}@power0")

    def test_phoenix_offer_follows_the_window_after_knockouts(self):
        """ふしちょうの機会は、サイド・勝ち負けのあとの窓の場で決める（いっしょにきぜつしたパラセクトは、もう場にいない）。"""
        protected = board(mon(NIDORINO, (G, G, G)), bench=(self.PARASECT_BENCH,),
                          opponent=mon(MOLTRES_R, damage=50), opponent_bench=(mon(H.HITMONCHAN),))
        done = attack(protected, 0)
        while done.decision is not None and done.decision.kind != "promote_active":
            d = done.decision
            done = apply_kernel(done, ResolveDecision(d.player, d.id, (d.options[0],)))
        self.assertEqual(last(done, "discard_protected")["power"], f"{MOLTRES_R}@power0")
        self.assertFalse([e for e in done.log if e["kind"].startswith("post_knockout_power")])

    def test_trainers_and_energy_effects_are_not_pokemon_effects(self):
        """エネルギー回収（トレーナー）は［アレルギーほうし］の場でも、トラッシュから手札に加える。"""
        from kyuura_engine import PlayTrainer

        state = board(mon(H.HITMONCHAN, (F,)), bench=(self.PARASECT_BENCH,), hand=(H.ENERGY_RETRIEVAL, F), discard=(F, F), opponent=mon(H.HITMONCHAN))
        card = uid(state, H.ENERGY_RETRIEVAL)
        used = apply_kernel(state, PlayTrainer(0, card))
        while used.decision is not None:
            d = used.decision
            used = apply_kernel(used, ResolveDecision(d.player, d.id, tuple(d.options[:max(d.min_choices, 1)])))
        self.assertIsNone(last(used, "discard_protected"))
        self.assertTrue(last(used, "retrieve_energy"))


# ---------------------------------------------------------------- 4 章: 上限なしコインの組と、使うかを選ぶ・その数にする 8 段階


class UnboundedClassesTest(unittest.TestCase):
    """［XXXXX］（「うら」が出るまでのコインの追加。v0.118）の先読みの組は、8 段階の［かたいから］（1〜40 → 10）・［シェルアーマー］（使うかを選ぶ）でも、実際の量と合う。"""

    def x_board(self, defender):
        return board(mon("neo4-065", (PS,)), bench=(mon("neo4-065"),), opponent=defender)

    def test_hard_shell_keys_and_real_damage(self):
        for heads, expected in ((0, 10), (1, 10), (3, 10), (4, 50)):
            with self.subTest(heads=heads):
                state = self.x_board(mon(SHUCKLE))
                done = apply_kernel(H.with_coin_bits(state, *((HD,) * heads + (TL,))), UseAttack(0, 0, with_power=state.players[0].bench[0].pokemon_id))
                self.assertEqual(last(done, "damage")["amount"], expected)

    def test_shell_armor_is_asked_after_the_coins(self):
        state = self.x_board(mon(CLOYSTER))
        asked = apply_kernel(H.with_coin_bits(state, HD, HD, TL), UseAttack(0, 0, with_power=state.players[0].bench[0].pokemon_id))
        self.assertEqual(asked.decision.kind, DAMAGE_OPTION)
        self.assertEqual(damage_of(answer(asked, asked.decision.options), 1), 20)  # 10 + 20 - 10
        self.assertEqual(damage_of(answer(asked, ()), 1), 30)


# ---------------------------------------------------------------- 11 章: ログの監査


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v119_problems``・``v119_close`` と、本体の 8 段階の効果・どくのダメージ・トラッシュの保護・ふしちょうの機会の分岐）は、エンジンの登録・計算を読まずに、
    処理したワザ・特殊能力の印刷の文面と、ログから組み立てた場・コイン・カードの動きで確かめる。エンジンの処理を一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py の局。
    開発用の seed 50〜53。正式な対戦の seed 0〜3 とは別）で、監査がそれを見つける。"""

    GAMES = ((("M85", "W119"), 50), (("W119", "D119"), 51), (("P119", "D119"), 53), (("L114", "D119"), 50), (("P119", "D119"), 51), (("W119", "M85"), 51),
             (("T74", "W119"), 51))

    @classmethod
    def problems_for(cls, patcher, *needles, games_=None):
        from tools import existing_effect_games as games

        found = []
        with patcher:
            for labels, seed in games_ or cls.GAMES:
                try:
                    result = games.play(labels, seed, keep_state=True)
                except Exception as error:  # noqa: BLE001  誤らせた処理が不変条件で止まっても、監査とは別の理由（ここでは数えない）
                    found.append(f"stopped: {error}") if "stopped" in needles else None
                    continue
                if result.get("state") is not None:
                    found += [p for p in log_problems(result["state"]) if any(n in p for n in needles)]
        return found

    def test_the_unpatched_games_pass_the_audit_and_use_the_new_mechanics(self):
        from collections import Counter

        from tools import existing_effect_games as games

        used = Counter()
        for labels, seed in self.GAMES:
            result = games.play(labels, seed, keep_state=True)
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual(result["outcome"], "game_over")
                self.assertEqual((result["audit"], log_problems(result["state"])), ({}, []))
            used.update({k for k, v in result["v119"].items() if v})
        self.assertTrue({"armor_used", "armor_declined", "hard_shell_set", "poison_multiplied", "poison_with_mist", "poison_mist_added", "poison_mist_removed",
                         "sleep_check_2coins_recovered", "sleep_check_2coins_asleep", "pull_in_switched", "pull_in_declined", "secrete_poison",
                         "secrete_poison_bench_damage", "replacement_poison_applied", "pain_split_1", "weakness_immunity_added", "discard_protected_power"} <= set(used))

    def test_audit_finds_a_wrong_hard_shell_amount(self):
        original = E.SetSmallAttackDamageReceived.attack_damage_modifiers

        def twenty(self, *args, **kwargs):
            return tuple(D.DamageModifier(m.step, 20, m.label, source=m.source, operation=m.operation, threshold=m.threshold) for m in original(self, *args, **kwargs))

        self.assertTrue(self.problems_for(mock.patch.object(E.SetSmallAttackDamageReceived, "attack_damage_modifiers", twenty), "のあとの数", "damage_set_if_at_most",
                                          games_=((("M85", "W119"), 50),)))

    def test_audit_finds_a_wrong_shell_armor_amount(self):
        original = E.OptionalReduceAttackDamageReceived.attack_damage_modifiers

        def twenty(self, *args, **kwargs):
            return tuple(D.DamageModifier(m.step, -20, m.label, source=m.source, optional=True) for m in original(self, *args, **kwargs))

        self.assertTrue(self.problems_for(mock.patch.object(E.OptionalReduceAttackDamageReceived, "attack_damage_modifiers", twenty), "damage_option",
                                          games_=((("W119", "D119"), 51),)))

    def test_audit_finds_a_poison_amount_without_the_multiplier(self):
        from kyuura_engine import procedures

        original = procedures.poison_check_amount

        def plain(state, owner, pokemon):
            found = original(state, owner, pokemon)
            return E.PoisonCheckAmount(10, 10, found.cards, found.mists, found.multiplier) if found.multiplier != 1 else found

        self.assertTrue(self.problems_for(mock.patch.object(procedures, "poison_check_amount", plain), "どくのダメージ", games_=((("M85", "W119"), 50),)))

    def test_audit_finds_one_sleep_coin_under_deep_sleep(self):
        from kyuura_engine import procedures

        self.assertTrue(self.problems_for(mock.patch.object(procedures, "sleep_check_coins", lambda state: (1, ())), "ねむりのコイン", games_=((("L114", "D119"), 50),)))

    def test_audit_finds_a_discard_move_under_protection(self):
        self.assertTrue(self.problems_for(mock.patch.object(E, "discard_protection", lambda state: ()), "アレルギーほうし",
                                          games_=((("T74", "W119"), 51), (("W119", "D119"), 50))))


# ---------------------------------------------------------------- 文書


class DocumentTest(unittest.TestCase):
    def test_document_records(self):
        import re

        text = DOC.read_text(encoding="utf-8")
        for word in ("AM1", "HS1", "PO1", "PO2", "PO3", "PX1", "IA1", "AP1", "AP2", "MD1", *(code for code, _ in STOP_CODES), "UNSUPPORTED_DAMAGE_OPTION_ELEMENT",
                     "SET_IF_AT_MOST", "poison_check_amount", "DAMAGE_OPTION", "0.119.0", "GR-2000-P321-DAMAGE-ORDER", "CR-BABY-RULE-NOT-POWER", "UQ-SPEED-STAR-SCOPE",
                     "1,322", "(55, 18, 37)", "499", "1,235", "1,338", "(1,107, 515, 13)", "## 13. 検証", "lockstep", "単体のテストだけ",
                     "外部照合・カード画像・ガイドブックの読み直しをしていません", "ES1-027", "neo4-082", "neo4-108", "ES2-005", "QSG-055", "PRN-041", "ねむリ", "6,635"):
            self.assertIn(word, text)
        for card in V0119:
            self.assertIn(card, text)
        v0118 = (ROOT / "docs" / "unbounded-coins-heal-allocation-v0.118.md").read_text(encoding="utf-8")
        self.assertIn("6,635", v0118)  # v0.118 の全体のテストの記録はそのまま
        status = (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(int(re.search(r"^# 実装状況（v0\.1〜v0\.(\d+)）", status, re.MULTILINE).group(1)), 119)
        self.assertIn("## v0.119: 受けるダメージの選択・どくとねむり・場の効果", status)
        self.assertRegex((ROOT / "README.md").read_text(encoding="utf-8"), r"\n- v0\.119（(今のエンジンの版。)?`kyuura_engine` の版は 0\.119\.0）: 受けるダメージの選択")
        self.assertIn("### v0.119: 受けるダメージの選択", (ROOT / "docs" / "rules-2000-02-14.md").read_text(encoding="utf-8"))
        self.assertIn("## v0.119: 受けるダメージの選択", (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8"))
