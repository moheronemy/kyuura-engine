"""v0.105（docs/recovery-evolution-coin-branches-v0.105.md）: 回復・山札からの進化・コインの分岐のポケモンの 5 枚（ワザ 8）と、回復のあとの山札からの進化・相手のエネルギーの個数の
ダメージと与えたぶんの回復・3 枚のコインの分岐の共通の処理。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面。5 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録
（GR-2000-P309-EVOLUTION-BY-NAME・GR-2000-P310-EVOLUTION・GR-2000-P312-DECK-HAND-DISCARD・GR-2000-P319-HP-AND-DAMAGE・GR-2000-P320-RECOVERY・GR-2000-P321-DAMAGE-ORDER・
GR-2000-P321-PREVENTED-ELEMENTS、v0.44 の ``EvolveAttackerFromDeck``、v0.82 のあたためるの「山札を見た場合は」、v0.84 の A3、v0.104 の回復、v0.103 の発生元）。英語版の文面・現代のルール・
後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの
自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.105``）。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import unittest
from unittest import mock

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttackKey,
    ResolveDecision,
    UseAttack,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.conditions import CONFUSION, PARALYSIS, POISON, SLEEP
from kyuura_engine.decisions import SEARCH_DECK, SELECT_ATTACK
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.observation import observe, visible_log
from kyuura_engine.resolution import kernel as K
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.preflight import MAX_BRANCHES
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import AttackBarrier
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.log_audit import LATEST_FORMAT, log_problems
from tests.release_catalog import cards_after, cards_before
from tests.test_counter_keep_energy_protection_v0_101 import attack
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_unown_family_powers_v0_96 import TURN, board, same_answers, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "recovery-evolution-coin-branches-v0.105.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, PS, G, F_ = H.WATER, H.PSYCHIC, H.GRASS, H.FIGHTING
METAPOD, SUNKERN, BUTTERFREE, CELEBI, DELIBIRD = "neo2-006", "neo4-003", "neo2-009", "PF3-002", "neo3-050"
V0105 = (METAPOD, SUNKERN, BUTTERFREE, CELEBI, DELIBIRD)
V0105_ATTACKS = [AttackKey(METAPOD, 0), AttackKey(METAPOD, 1), AttackKey(SUNKERN, 0), AttackKey(SUNKERN, 1), AttackKey(BUTTERFREE, 0), AttackKey(BUTTERFREE, 1),
                 AttackKey(CELEBI, 0), AttackKey(DELIBIRD, 0)]
CATERPIE, BUTTERFREE_JUNGLE, SUNFLORA, LIGHT_SUNFLORA, METAPOD_BASE = "neo2-001", "PMCG2-007", "neo1-013", "neo4-004", "PMCG1-003"
DCE, MEGANIUM, CHAIN_EEVEE, MISTYS_TENTACRUEL, FARFETCHD, MEW = "PMCG1-096", "neo1-014", "PRN-024", "GD2-004", "PMCG1-063", "PR1-005"
CHANSEY, MACHAMP, HAUNTER, CLEFABLE, CHARMANDER, RATTATA = H.CHANSEY, H.MACHAMP, H.HAUNTER, H.CLEFABLE, H.CHARMANDER, H.RATTATA
BELOW = {METAPOD: [CATERPIE], METAPOD_BASE: [CATERPIE], BUTTERFREE: [CATERPIE, METAPOD], BUTTERFREE_JUNGLE: [CATERPIE, METAPOD], MEGANIUM: ["neo1-002", "neo1-009"],
         MACHAMP: [H.MACHOP, H.MACHOKE], HAUNTER: [H.GASTLY], CLEFABLE: [H.CLEFAIRY], MISTYS_TENTACRUEL: ["GD2-003"]}
GYARADOS = "PMCG1-034"  # ギャラドス（第1弾。「コイキング」から進化。たきのぼりしんかの選べるカード）

# 依頼で示された固定データの日本語（写しの文面と照らす。広い正規化をしない）。(HP, タイプ, 段階, (名前, 必要なエネルギー, ダメージの目安, 説明), ...)
HARDEN = "次の相手の番、このカードがダメージを受けるとき、そのダメージが20以下なら、このカードはダメージを受けない。(ダメージ以外の効果は受ける。)"
HATCH = ("コインを投げて「おもて」なら、自分にのっているダメージカウンターをすべてとりのぞく。その後、自分の山札から「トランセル」を進化させる「進化カード」を1枚選び出し、"
         "このトランセルの上にのせ、進化させる。山札を見た場合は、その山札をよく切る。")
SUNBATHE = ("コインを投げて「おもて」なら、自分にのっているダメージカウンターを、すべてとりのぞく。その後、自分の山札から、「ヒマナッツ」から進化する「進化カード」を1枚選び出し、"
            "このヒマナッツの上にのせ、進化させる。山札を見た場合は、その山札をよく切る。")
MAGIC_DUST = "コインを投げて「おもて」なら、「どく・ねむり・マヒ・こんらん」の中から1つを選び、相手をその状態にする。"
HYPER_REVERSE = "相手についている「エネルギー」の数×10のダメージ。相手にダメージを与えたら、相手に与えたぶんのダメージカウンターを、自分からとりのぞく。"
PSYCHIC_LEAF = "相手についている「エネルギー」の数ぶんコインを投げ、「おもて」の数×10のダメージを追加する。その後、与えたダメージぶんのダメージカウンターを、自分からとりのぞく。"
PRESENT = ("コインを3枚投げる。すべて「おもて」なら、相手に60ダメージ。「おもて」が2枚なら、相手にのっているダメージカウンターを、3個とりのぞく。「おもて」が1枚なら、相手に40ダメージ。"
           "すべて「うら」なら、相手にのっているダメージカウンターを、すべてとりのぞく。")
QUOTED = {
    METAPOD: (70, "grass", "stage1", ("かたくなる", ("colorless", "colorless"), None, HARDEN), ("からやぶりしんか", ("grass", "grass"), None, HATCH)),
    SUNKERN: (40, "grass", "basic", ("ころがる", ("colorless",), "10", None), ("ひざしをあびる", ("grass", "grass"), None, SUNBATHE)),
    BUTTERFREE: (80, "grass", "stage2", ("ミラクルりんぷん", ("grass", "colorless"), "20", MAGIC_DUST), ("ハイパーリバース", ("grass", "grass", "colorless"), None, HYPER_REVERSE)),
    CELEBI: (50, "grass", "basic", ("サイコリーフ", ("grass", "grass"), "10+", PSYCHIC_LEAF)),
    DELIBIRD: (60, "colorless", "basic", ("プレゼント", ("colorless", "colorless"), None, PRESENT)),
}
EXPECTED = {
    (METAPOD, 0): E.ZeroDamageBelowNextTurn(30), (METAPOD, 1): E.CoinHealAllThenEvolveSelfFromDeck("トランセル", "hatch"),
    (SUNKERN, 0): E.DamageOnly(), (SUNKERN, 1): E.CoinHealAllThenEvolveSelfFromDeck("ヒマナッツ", "sunbathe"),
    (BUTTERFREE, 0): E.DamageThenChosenStatusOnHeads(conditions=(POISON, SLEEP, PARALYSIS, CONFUSION)), (BUTTERFREE, 1): E.DefenderEnergyUnitsDamageAndFullDrain(10),
    (CELEBI, 0): E.CoinsPerDefenderEnergyBonusAndFullDrain(10), (DELIBIRD, 0): E.ThreeCoinDamageOrOpponentHeal(60, 3, 40),
}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def answer(state, choices, *coins):
    d = state.decision
    return apply_kernel(with_coin_results(state, *coins) if coins else state, ResolveDecision(d.player, d.id, tuple(choices)))


def kinds(before, after, *names):
    return [e["kind"] for e in new_events(before, after, *names)]


def coins_of(before, after):
    return [e["result"] for e in new_events(before, after, "coin_flip") if e.get("source") == "attack"]


def mine(before, after, key, *names):
    """ワザ ``key``（カード id#位置）の効果のログ（``effect`` がそのワザ）の種類。"""
    return [e["kind"] for e in new_events(before, after, *names) if e.get("effect") == key]


def base_damages(before, after, player):
    """プレイヤー ``player`` のポケモンが受けた、ワザのダメージの (基本となるダメージ, 最終ダメージ)。"""
    return [(e["steps"][0][1], e["amount"]) for e in new_events(before, after, "damage") if e["player"] == player and not e.get("retaliation")]


def drained(before, after):
    return [(e["dealt"], e["drain_counters"], e["counters"]) for e in new_events(before, after, "drain_heal")]


def shuffles(before, after, player=0):
    return [e for e in new_events(before, after, "shuffle") if e["player"] == player]


# ---------------------------------------------------------------- 1・2 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_entries_and_printed_texts(self):
        """5 枚・8 のワザの名前・必要なエネルギー・ダメージの目安・説明は依頼の日本語と同じ（目安なしは null で、0 ダメージではない）。特殊能力は 0。同じデータの再録群でもない。"""
        pool = load_card_pool()
        cards = {c["id"]: c for c in read_extract()["cards"]}
        self.assertEqual(tuple(read_extract()["pool_v0_105"]), V0105)
        for card, (hp, color, stage, *attacks) in QUOTED.items():
            definition = pool.definitions[card]
            self.assertEqual((definition.hp, definition.pokemon_type.value, definition.stage, definition.powers), (hp, color, stage, ()))
            self.assertIsNone(cards[card]["same_card_group"])
            self.assertIn(card, pool.playable_ids)
            self.assertEqual(len(definition.attacks), len(attacks))
            for index, (name, cost, display, text) in enumerate(attacks):
                printed = definition.attacks[index]
                with self.subTest(card=card, index=index):
                    self.assertEqual((printed.name_ja, tuple(t.value for t in printed.cost), printed.damage_display, printed.text_ja), (name, cost, display, text))
                    entry = DEFAULT_EFFECTS.attack_entry(card, index)
                    self.assertEqual(entry.effect, EXPECTED[(card, index)])
                    self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                                     (name, text, text, None if text is None else "kyuura data/cards.json"))
                    self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card, printed, definition.attacks))
        self.assertIsNone(pool.definitions[BUTTERFREE].attacks[1].damage)  # 目安なし（0 ダメージの目安ではない）
        self.assertIsNone(pool.definitions[DELIBIRD].attacks[0].damage)

    def test_programs(self):
        """新しい型の要素の並び（既存の要素とその小さな拡張）。カードの id による分岐はない。"""
        builders = {
            E.CoinHealAllThenEvolveSelfFromDeck("トランセル", "hatch"): (
                P.Coin("coin"), P.HealCounters(every=True, gate=("coin", HD)),
                P.EvolveAttackerFromDeck("トランセル", gate=("coin", HD), required=True, shuffle_if_looked=True)),
            E.DefenderEnergyUnitsDamageAndFullDrain(10): (P.Damage(P.OPP, P.DefenderEnergyUnitsTimes(10)), P.Drain("damage", full=True, reach=True)),
            E.CoinsPerDefenderEnergyBonusAndFullDrain(10): (P.Coin("coin", per_opponent_energy=True), P.Damage(P.OPP, P.PrintedPlusHeadsOfCoin("coin", 10)),
                                                            P.Drain("damage", full=True, reach=True)),
            E.ThreeCoinDamageOrOpponentHeal(60, 3, 40): (
                P.Coin("coin", count=3), P.Damage(P.OPP, P.Fixed(60), gate=("coin", 3)), P.Damage(P.OPP, P.Fixed(40), name="one_heads_damage", gate=("coin", 1)),
                P.HealCounters(3, scope=E.HEAL_OPPONENT_ACTIVE, gate=("coin", 2)), P.HealCounters(every=True, scope=E.HEAL_OPPONENT_ACTIVE, gate=("coin", 0))),
            E.ZeroDamageBelowNextTurn(30): (P.SelfPersistent("zero_damage_below", amount=30),),
        }
        for effect, program in builders.items():
            with self.subTest(effect=effect):
                self.assertEqual(P.BUILDERS[type(effect)](effect), program)
        # 既定値は v0.104 までと同じ（たきのぼりしんかの任意の進化・メガドレインなどの回復は変えない）
        self.assertEqual((P.EvolveAttackerFromDeck("コイキング").gate, P.EvolveAttackerFromDeck("コイキング").required, P.EvolveAttackerFromDeck("コイキング").shuffle_if_looked),
                         (None, False, False))
        self.assertFalse(P.Drain("damage").reach)
        self.assertEqual(P.BUILDERS[E.EvolveSelfFromDeck](E.EvolveSelfFromDeck("コイキング")), (P.EvolveAttackerFromDeck("コイキング"),))
        self.assertEqual(P.HealCounters(1, scope=E.HEAL_OPPONENT_ACTIVE).opponent_element, E.HEAL_ELEMENT)
        self.assertEqual((P.HealCounters(1, scope=E.HEAL_OPPONENT_ACTIVE).coin_receiver(), P.HealCounters(1).coin_receiver(),
                          P.HealCounters(1, scope=E.HEAL_BOTH_ACTIVE).coin_receiver()), ("effect", None, None))
        self.assertEqual(E.ThreeCoinDamageOrOpponentHeal(60, 3, 40).opponent_effect_elements, (E.HEAL_ELEMENT,))
        for cls in (E.DefenderEnergyUnitsDamageAndFullDrain, E.CoinsPerDefenderEnergyBonusAndFullDrain, E.CoinHealAllThenEvolveSelfFromDeck):
            self.assertEqual(cls.opponent_effect_elements, ())
        for cls in {type(e) for e in EXPECTED.values()} - {E.DamageOnly, E.ZeroDamageBelowNextTurn, E.DamageThenChosenStatusOnHeads}:
            self.assertIn(cls, H.ATTACK_TYPES_SINCE_V0_17)
            self.assertIs(cls.resolve, E.AttackEffect.resolve)

    def test_reused_types_match_the_printed_text(self):
        """既存の型の 3 つ: ころがるは説明文のない固定ダメージ、ミラクルりんぷんは説明の並び（どく・ねむり・マヒ・こんらん）で、選ぶ番号は CHOSEN_CONDITIONS のまま（並べかえない）、
        かたくなるは「20以下」をしきい値 30 の文面として明示して加えた（しきい値と結び付ける。20 を「20未満」のしきい値にしない）。"""
        pool = load_card_pool()
        roll = pool.definitions[SUNKERN].attacks[0]
        self.assertEqual((roll.text_ja, roll.damage, E.DamageOnly().check(roll)), (None, 10, []))
        dust = E.DamageThenChosenStatusOnHeads(conditions=(POISON, SLEEP, PARALYSIS, CONFUSION))
        self.assertEqual(dust.check(pool.definitions[BUTTERFREE].attacks[0]), [])
        self.assertEqual(E.MAGIC_DUST_CONDITIONS, (POISON, SLEEP, PARALYSIS, CONFUSION))
        self.assertEqual(P.ChosenStatus(conditions=E.MAGIC_DUST_CONDITIONS).choices(), (0, 1, 2, 3))
        self.assertEqual(E.CHOSEN_CONDITIONS, (SLEEP, PARALYSIS, CONFUSION, POISON))  # 番号の意味は変えない
        self.assertNotEqual(E.DamageThenChosenStatusOnHeads().check(pool.definitions[BUTTERFREE].attacks[0]), [])  # 既定の並び（ねむり・マヒ・こんらん・どく）では通らない
        harden = pool.definitions[METAPOD].attacks[0]
        self.assertEqual(E.ZeroDamageBelowNextTurn(30).check(harden), [])
        self.assertEqual(E.HARDEN_TEXT, HARDEN)
        for threshold in (20, 40):
            self.assertNotEqual(E.ZeroDamageBelowNextTurn(threshold).check(harden), [])
        for changed in (HARDEN.replace("20以下", "20未満"), HARDEN.replace("(ダメージ以外の効果は受ける。)", ""), HARDEN.replace("(", "（").replace(")", "）")):
            self.assertNotEqual(E.ZeroDamageBelowNextTurn(30).check(dataclasses.replace(harden, text_ja=changed)), [])
        # イワーク・化石の秘密のゴローンの書き方は v0.64 のまま
        self.assertEqual(E.zero_damage_below_texts(40)[:2], ("次の相手の番に受けるダメージが0になる。ただしダメージが40以上の場合は、そのままダメージをうける。",
                                                            "次の相手の番にこのカードが受ける30以下のダメージは0になる。(ダメージ以外の効果はそのまま)。40以上のダメージはそのまま受ける。"))

    def test_damage_values_are_counter_units(self):
        """「20以下」と「30 より小さい」が同じになる計算の範囲: 写しのワザのダメージの目安・抵抗力の数はどれも 10 の倍数、弱点はどれも ×2（8 段階の計算のダメージは 10 の倍数のまま。
        半分にする計算はダメージカウンターの単位で切り上げ・切りすてる）。"""
        for card in read_extract()["cards"]:
            pokemon = card.get("pokemon")
            if not pokemon:
                continue
            for printed in pokemon["attacks"]:
                if printed["damage"] is not None and printed["damage"]["base"] is not None:
                    self.assertEqual(printed["damage"]["base"] % 10, 0, card["id"])
            self.assertTrue(all((w["operator"], w["value"]) == ("×", 2) for w in pokemon["weaknesses"]), card["id"])
            self.assertTrue(all(r["operator"] == "-" and r["value"] % 10 == 0 for r in pokemon["resistances"]), card["id"])

    def test_texts_are_not_normalized(self):
        """書き方は対象・名前・数と結び付けた完全な一致だけ（一律の正規化・部分一致で通さない）。"""
        pool = load_card_pool()
        hatch, sunbathe = pool.definitions[METAPOD].attacks[1], pool.definitions[SUNKERN].attacks[1]
        self.assertNotEqual(E.CoinHealAllThenEvolveSelfFromDeck("トランセル", "sunbathe").check(hatch), [])
        self.assertNotEqual(E.CoinHealAllThenEvolveSelfFromDeck("ヒマナッツ", "hatch").check(sunbathe), [])
        self.assertNotEqual(E.CoinHealAllThenEvolveSelfFromDeck("キャタピー", "hatch").check(hatch), [])
        self.assertNotEqual(E.CoinHealAllThenEvolveSelfFromDeck("トランセル", "hatch").check(dataclasses.replace(hatch, text_ja=HATCH.replace("山札を見た場合は、", ""))), [])
        self.assertNotEqual(E.EvolveSelfFromDeck("トランセル").check(hatch), [])  # 任意の進化の型に登録しない
        reverse, leaf, present = pool.definitions[BUTTERFREE].attacks[1], pool.definitions[CELEBI].attacks[0], pool.definitions[DELIBIRD].attacks[0]
        self.assertNotEqual(E.DefenderEnergyUnitsDamageAndFullDrain(20).check(reverse), [])
        self.assertNotEqual(E.DamageTimesDefenderEnergyCards(10).check(reverse), [])  # カードの枚数の型ではない
        self.assertNotEqual(E.DefenderEnergyUnitsDamageAndFullDrain(10).check(dataclasses.replace(reverse, text_ja=HYPER_REVERSE.replace("「エネルギー」の数", "エネルギーカードの数"))), [])
        self.assertNotEqual(E.CoinsPerDefenderEnergyBonusAndFullDrain(20).check(leaf), [])
        self.assertNotEqual(E.CoinsPerDefenderEnergyChosenStatus().check(leaf), [])
        for values in ((60, 2, 40), (40, 3, 60), (60, 3, 30)):
            self.assertNotEqual(E.ThreeCoinDamageOrOpponentHeal(*values).check(present), [])
        with self.assertRaises(ValueError):
            E.CoinHealAllThenEvolveSelfFromDeck("トランセル", "other")
        with self.assertRaises(ValueError):
            P.HealCounters(1, scope="opponent_bench")

    def test_unregistered_without_the_v0_105_entries(self):
        """今回の登録だけを除くと、ちょうど 5 枚が未対応にもどる。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V0105_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V0105))
        self.assertEqual(set(V0105) & set(cards_before(read_extract(), "0.105")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.104")) & set(cards_before(read_extract(), "0.106")), set(V0105))

    def test_extract_keeps_sources_and_gaps(self):
        """転記元はトランセル・バタフリーが nazonobasho.com、ヒマナッツ・デリバードがポケモンWiki、セレビィが pcg-search.com（neopf3002）。セレビィのレベルの欠けは補わない。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        hosts = {card: cards[card]["ja_text_source"].split("/")[2] for card in V0105}
        self.assertEqual(hosts, {METAPOD: "nazonobasho.com", BUTTERFREE: "nazonobasho.com", SUNKERN: "wiki.pokemonwiki.com", DELIBIRD: "wiki.pokemonwiki.com",
                                 CELEBI: "pcg-search.com"})
        self.assertEqual((cards[CELEBI]["data_gaps"], cards[CELEBI]["jp_print"]["level"], cards[CELEBI]["source_ids"]["pcg_search"]), (["jp_print.level"], None, ["neopf3002"]))
        for card in (METAPOD, SUNKERN, BUTTERFREE, DELIBIRD):
            self.assertEqual(cards[card]["data_gaps"], [])

    def test_adoption_records(self):
        """5 件の採用の記録（kyuura 73a1690・外部照合なし・kyuura の記録なし）。処理に使う文面は印刷の文面（説明文のないころがるは持たない）。"""
        sources = json.loads((ROOT / "kyuura_engine/data/card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine/data/research_links.json").read_text(encoding="utf-8"))["latest_descriptions"]["adopted_printed_text"]
        parts = {METAPOD: ("attack/0", "attack/1"), SUNKERN: ("attack/1",), BUTTERFREE: ("attack/0", "attack/1"), CELEBI: ("attack/0",), DELIBIRD: ("attack/0",)}
        for card in V0105:
            record = sources[card]
            self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"], record["external_checks"], record["issues"]),
                             ("kyuura_data", "adopted", "73a169063463bbf7bcaa3137d70cbf9721d11534", [], [], []))
            self.assertEqual(record["play_text"], {part: "kyuura_printed_text" for part in parts[card]})
            for part in parts[card]:
                self.assertIn(f"{card}/{part}", links)
        self.assertNotIn(f"{SUNKERN}/attack/0", links)


# ---------------------------------------------------------------- 3 章: かたくなる


class HardenTest(unittest.TestCase):
    def harden(self, opponent):
        state = board(mon(METAPOD, (W, W)), opponent=opponent)
        after = attack(state, 0)
        self.assertEqual([e["persistent_effect"] for e in new_events(state, after, "persistent_effect_added")], ["zero_damage_below"])
        self.assertEqual(after.current_player, 1)
        return after

    def test_twenty_or_less_is_zero_after_weakness_and_thirty_passes(self):
        """次の相手の番、p.321 の 8 段階のダメージで決める: ヒトカゲのひっかく 10 は弱点（炎 ×2）で 20 → 0、ひのこ 30 は 60 → そのまま、カモネギのナベでたたく 30 → そのまま。"""
        for opponent, index, expected in ((mon(CHARMANDER, (W,)), 0, 0), (mon(CHARMANDER, (H.FIRE, W)), 1, 60), (mon(FARFETCHD, (W, W, W)), 1, 30)):
            ready = self.harden(opponent)
            after = attack(ready, index)
            if after.decision is not None:
                after = answer(after, after.decision.options[:1])  # ひのこの「炎」エネルギーカードのトラッシュ
            with self.subTest(opponent=opponent["card"], index=index):
                self.assertEqual(after.players[0].active.damage, expected)
                steps = [label for label, _ in new_events(ready, after, "damage")[0]["steps"]]
                self.assertTrue(any("zero_damage_below" in str(label) for label in steps))
                audited(self, after)

    def test_effects_other_than_damage_still_happen(self):
        """「(ダメージ以外の効果は受ける。)」: 第1弾のトランセルのしびれごな 20 は 0 になるが、「おもて」のマヒは受ける（計算の前の一律の防護ではない）。"""
        ready = self.harden(mon(METAPOD_BASE, (G, G)))
        after = attack(ready, 1, HD)
        self.assertEqual((after.players[0].active.damage, after.players[0].active.conditions.paralyzed is not None), (0, True))
        self.assertEqual(new_events(ready, after, "damage_prevented"), [])


# ---------------------------------------------------------------- 4 章: 回復のあとの山札からの進化


class EvolveFromDeckTest(unittest.TestCase):
    def test_heads_heals_all_then_evolves_and_shuffles_once(self):
        """「おもて」: すべてとりのぞく → 山札の「トランセル」から進化するカード（uid の小さい順。2 種類）から必ず 1 枚 → 進化 → 見たので 1 回だけ切る。回復と進化でコインは 1 枚。"""
        for damage in (0, 30):
            state = board(mon(METAPOD, (G, G), damage=damage), deck=[BUTTERFREE, W, BUTTERFREE_JUNGLE, W])
            asked = attack(state, 1, HD)
            uids = [u for u in state.players[0].deck if state.cards[u].card_id in (BUTTERFREE, BUTTERFREE_JUNGLE)]
            d = asked.decision
            with self.subTest(damage=damage):
                self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (SEARCH_DECK, 0, tuple(sorted(uids)), 1, 1))
                self.assertEqual(asked.players[0].active.damage, 0)
                self.assertEqual(mine(state, asked, f"{METAPOD}#1", "attack_heal"), ["attack_heal"] if damage else [])
                self.assertEqual(coins_of(state, asked), ["heads"])
                self.assertEqual(shuffles(state, asked), [])
                audited(self, asked)
                for card in d.options:
                    done = answer(asked, (card,))
                    self.assertEqual(mine(asked, done, f"{METAPOD}#1", "evolve", "shuffle"), ["evolve", "shuffle"])
                    self.assertEqual(done.players[0].active.card, card)
                    self.assertEqual((coins_of(asked, done), done.current_player), ([], 1))  # 投げ直さない。ワザのあと番は終わる
                    audited(self, done)

    def test_tails_does_nothing(self):
        state = board(mon(METAPOD, (G, G), damage=30), deck=[BUTTERFREE, W])
        after = attack(state, 1, TL)
        self.assertIsNone(after.decision)
        self.assertEqual(kinds(state, after, "attack_heal", "evolve", "evolve_from_deck_none", "shuffle"), [])
        self.assertEqual(after.players[0].active.damage, 30)

    def test_no_choosable_card_still_looks_and_waits_for_an_empty_answer(self):
        """山札にカードがあって選べるカードがない（進化カードがない・この番に進化した・おたがいの最初の番）: 選べるもののない決定を出して答えを待ち（v0.84 の A3）、答えのあと切る。
        0 枚を成功にも未解決にもしない（進化しない。ワザは失敗しない）。"""
        cases = ((mon(METAPOD, (G, G), damage=20), [W, W], TURN), (mon(METAPOD, (G, G), damage=20, evolved_turn=TURN), [BUTTERFREE, W], TURN),
                 (mon(SUNKERN, (G, G), damage=20, played_turn=1), [SUNFLORA, W], 1))
        for spec, deck, turn in cases:
            state = board(spec, deck=deck, turn=turn)
            asked = attack(state, 1, HD)
            d = asked.decision
            key = f"{spec['card']}#1"
            with self.subTest(deck=deck, turn=turn, spec=spec):
                self.assertEqual((d.kind, d.options, d.min_choices, d.max_choices), (SEARCH_DECK, (), 0, 0))
                audited(self, asked)
                done = answer(asked, ())
                self.assertEqual(mine(asked, done, key, "evolve_from_deck_none", "shuffle"), ["evolve_from_deck_none", "shuffle"])
                self.assertEqual(done.cards[done.players[0].active.card].card_id, spec["card"])
                self.assertEqual(new_events(asked, done, "attack_failed"), [])

    def test_empty_deck_neither_looks_nor_shuffles(self):
        state = board(mon(SUNKERN, (G, G), damage=20), deck=[])
        after = attack(state, 1, HD)
        self.assertIsNone(after.decision)
        self.assertEqual(mine(state, after, f"{SUNKERN}#1", "attack_heal", "evolve_from_deck_none", "shuffle"), ["attack_heal", "evolve_from_deck_none"])

    def test_sunkern_uses_the_same_processing(self):
        state = board(mon(SUNKERN, (G, G), damage=30), deck=[LIGHT_SUNFLORA, W, SUNFLORA])
        asked = attack(state, 1, HD)
        self.assertEqual(sorted(state.cards[u].card_id for u in asked.decision.options), sorted([SUNFLORA, LIGHT_SUNFLORA]))
        done = answer(asked, (asked.decision.options[0],))
        self.assertEqual((done.players[0].active.damage, len(shuffles(asked, done))), (0, 1))
        audited(self, done)

    def test_the_required_choice_rejects_a_decline(self):
        """選べるカードがあるとき、原文にない辞退（0 枚）・選べないカード・2 枚は拒否（状態・乱数・ログ・決定は変わらない。HALTED にしない）。"""
        state = board(mon(METAPOD, (G, G)), deck=[BUTTERFREE, W, BUTTERFREE_JUNGLE])
        asked = attack(state, 1, HD)
        water = next(u for u in asked.players[0].deck if asked.cards[u].card_id == W)
        for choices in ((), (water,), tuple(asked.decision.options)):
            with self.subTest(choices=choices):
                before = snap(asked)
                with self.assertRaises(IllegalActionError):
                    apply_kernel(asked, ResolveDecision(0, asked.decision.id, choices))
                self.assertEqual(snap(asked), before)
        with self.assertRaises(IllegalActionError):
            apply_kernel(asked, ResolveDecision(1, asked.decision.id, asked.decision.options[:1]))

    def test_waterfall_evolution_stays_optional(self):
        """既存のたきのぼりしんか（ロケット団のコイキング）は v0.44 のまま: 0〜1 枚を選べ、選ばない・選べるものがない場合も切る（任意性と切る条件を変えない）。"""
        state = board(mon(H.ROCKET_MAGIKARP, (W, W, W)), deck=[W, W])
        none = attack(state, 1)
        self.assertEqual(mine(state, none, f"{H.ROCKET_MAGIKARP}#1", "evolve_from_deck_none", "shuffle"), ["evolve_from_deck_none", "shuffle"])
        self.assertIsNone(none.decision)  # 任意の進化は、選べるものがなければ決定を出さない（v0.44 のまま）
        state = board(mon(H.ROCKET_MAGIKARP, (W, W, W)), deck=[GYARADOS, W])
        asked = attack(state, 1)
        self.assertEqual((asked.decision.kind, asked.decision.min_choices, asked.decision.max_choices), (SEARCH_DECK, 0, 1))
        declined = answer(asked, ())
        self.assertEqual(kinds(asked, declined, "evolve_from_deck_declined", "shuffle"), ["evolve_from_deck_declined", "shuffle"])

    def test_public_questions_do_not_depend_on_the_deck(self):
        """山札を見る前に公開の情報で決まる問い（今の番に退化した DV2・ほかのポケモンの［れんさしんか］の PW4）は、山札に選べるカードがあるかによらず、宣言の前に止める（宣言を受け付けるか
        から山札の中身がわからない）。"""
        for deck in ([BUTTERFREE, W, W], [W, W, W]):
            devolved = board(mon(METAPOD, (G, G), damage=20), deck=deck)
            devolved.players[0].active.devolved_turn = TURN
            chain = board(mon(METAPOD, (G, G), damage=20), bench=(CHAIN_EEVEE,), deck=deck)
            with self.subTest(deck=deck):
                rejects(self, with_coin_results(devolved, TL), UseAttack(0, 1), "UNRESOLVED_EVOLVE_AFTER_DEVOLUTION")
                rejects(self, with_coin_results(chain, TL), UseAttack(0, 1), "UNRESOLVED_ENTRY_POWER_DURING_ATTACK")

    def test_hidden_deck_contents_do_not_leak(self):
        """見えない山札の中身だけが違う 2 つの状態（進化カードが山札か手札か）で、宣言は同じく受け付け、相手の観測（決定の種類・決めるプレイヤーだけ。選べるものの数は見せない）と
        ログは決定まで同じ。原文の処理が公開する結果（進化した・しなかった）は答えのあとに分かれる。"""
        in_deck = board(mon(METAPOD, (G, G), damage=20), hand=(W,), deck=[BUTTERFREE, W, W])
        in_hand = board(mon(METAPOD, (G, G), damage=20), hand=(BUTTERFREE,), deck=[W, W, W])
        self.assertEqual(observe(in_deck, 1), observe(in_hand, 1))
        a, b = attack(in_deck, 1, HD), attack(in_hand, 1, HD)
        self.assertEqual((observe(a, 1), visible_log(a, 1)), (observe(b, 1), visible_log(b, 1)))
        self.assertEqual(observe(a, 1)["decision"], {"kind": SEARCH_DECK, "player": 0})
        self.assertEqual([o["card_id"] for o in observe(a, 0)["decision"]["options"]], [BUTTERFREE])
        self.assertEqual(observe(b, 0)["decision"]["options"], [])
        done_a, done_b = answer(a, a.decision.options), answer(b, ())
        self.assertEqual((kinds(a, done_a, "evolve", "evolve_from_deck_none"), kinds(b, done_b, "evolve", "evolve_from_deck_none")), (["evolve"], ["evolve_from_deck_none"]))
        self.assertEqual((len(shuffles(a, done_a)), len(shuffles(b, done_b))), (1, 1))

    def test_copied_hatch_heals_the_copier_and_keeps_the_printed_name(self):
        """相手のワザとして使う（ピクシーのゆびをふる）と、とりのぞくのは使ったピクシー。説明の「トランセル」から進化するカードはピクシーに重ねられない（名前。p.309）ので選べるカードがなく、
        山札を見たので切る（原文にない進化の制限の免除を加えない）。"""
        state = board(mon(CLEFABLE, (W,), damage=30), opponent=mon(METAPOD, (G, G)), deck=[BUTTERFREE, W])
        asked = attack(state, 0)
        self.assertEqual(asked.decision.kind, SELECT_ATTACK)
        searched = answer(asked, (1,), HD)
        self.assertEqual((searched.decision.kind, searched.decision.options), (SEARCH_DECK, ()))
        self.assertEqual(searched.players[0].active.damage, 0)
        done = answer(searched, ())
        self.assertEqual(kinds(searched, done, "evolve", "evolve_from_deck_none", "shuffle"), ["evolve_from_deck_none", "shuffle"])
        self.assertEqual(done.cards[done.players[0].active.card].card_id, CLEFABLE)
        audited(self, done)

    def test_transformed_ditto_cannot_evolve(self):
        """［へんしん］のメタモン（トランセルを写した）のからやぶりしんか: メタモンの説明が進化を禁じる（v0.49）ので選べるカードがない（今の姿で進化の制限を外さない）。"""
        state = board(mon(H.DITTO, (G, G), damage=20), opponent=mon(METAPOD, (G, G)), deck=[BUTTERFREE, W])
        asked = attack(state, 1, HD)
        self.assertEqual((asked.decision.kind, asked.decision.options), (SEARCH_DECK, ()))
        self.assertEqual(asked.players[0].active.damage, 0)


# ---------------------------------------------------------------- 5 章: エネルギーの個数と与えたぶんの回復


class DrainTest(unittest.TestCase):
    def test_hyper_reverse_counts_energy_units_not_cards(self):
        """ハイパーリバース: 相手のエネルギーの個数 × 10（無色2個エネルギーは 2 個。カードの枚数ではない）→ 与えたダメージ ÷ 10 個を自分から（のっている数まで）。0 個なら 0（与えない）。"""
        for energy, base in (((DCE, W), 30), ((W,), 10), ((), 0)):
            state = board(mon(BUTTERFREE, (G, G, G), damage=60), opponent=mon(CHANSEY, energy))
            after = attack(state, 1)
            with self.subTest(energy=energy):
                self.assertEqual(base_damages(state, after, 1), [(base, base)])
                self.assertEqual(drained(state, after), [(base, base // 10, base // 10)] if base else [])
                self.assertEqual(after.players[0].active.damage, 60 - base)
                profile = E.DefenderEnergyUnitsDamageAndFullDrain(10).damage_profile(state, E.AttackUse(0, state.players[0].active.pokemon_id, AttackKey(BUTTERFREE, 1)))
                self.assertEqual(profile.opponent, (base,))
                audited(self, after)

    def test_wild_growth_changes_the_count(self):
        """［おいしげる］の場では「草」エネルギーカード 1 枚が「草」2 個ぶん（個数の問い合わせを共通にする）。"""
        state = board(mon(BUTTERFREE, (G, G, G)), opponent=mon(MEGANIUM, (G, G)))
        after = attack(state, 1)
        self.assertEqual(base_damages(state, after, 1)[0][0], 40)

    def test_dealt_damage_is_the_final_damage(self):
        """とりのぞく数は最終ダメージ（弱点・抵抗力・ディフェンダーのあと。相手の残りの HP で上限を付けない。GR-2000-P319-HP-AND-DAMAGE）。のっている数まで。最終ダメージが 0 なら与えない。"""
        weak = board(mon(BUTTERFREE, (G, G, G), damage=70), opponent=mon(H.ONIX, (F_, W)))  # 草が弱点
        after = attack(weak, 1)
        self.assertEqual((base_damages(weak, after, 1), drained(weak, after), after.players[0].active.damage), ([(20, 40)], [(40, 4, 4)], 30))
        capped = board(mon(CELEBI, (G, G), damage=10), opponent=mon(CHANSEY, (W, W, W)))
        after = attack(capped, 0, HD, HD, HD)
        self.assertEqual((base_damages(capped, after, 1), drained(capped, after), after.players[0].active.damage), ([(40, 40)], [(40, 4, 1)], 0))
        guarded = board(mon(BUTTERFREE, (G, G, G), damage=30), opponent=mon(CHANSEY, (W,), trainers=[(H.DEFENDER, TURN)]))
        after = attack(guarded, 1)
        self.assertEqual((base_damages(guarded, after, 1), drained(guarded, after)), ([(10, 0)], []))

    def test_psychic_leaf_flips_one_coin_per_energy_unit(self):
        """サイコリーフ: コインは相手のエネルギーの個数ぶん（無色2個エネルギーは 2 枚）、目安 10 +「おもて」× 10。0 個なら投げず 10。与えたぶんを自分から。"""
        for energy, flips in (((DCE, W), (HD, TL, HD)), ((), ())):
            state = board(mon(CELEBI, (G, G), damage=40), opponent=mon(CHANSEY, energy))
            after = attack(state, 0, *flips)
            base = 10 + 10 * flips.count(HD)
            with self.subTest(energy=energy):
                self.assertEqual(len(coins_of(state, after)), len(flips))
                self.assertEqual((base_damages(state, after, 1), drained(state, after)), ([(base, base)], [(base, base // 10, base // 10)]))
        profile = E.CoinsPerDefenderEnergyBonusAndFullDrain(10).damage_profile(state, E.AttackUse(0, state.players[0].active.pokemon_id, AttackKey(CELEBI, 0)))
        self.assertEqual(profile.opponent, (10,))

    def test_damage_prevention_keeps_the_existing_coin_question(self):
        """自己回復の要素があるだけでは、相手へのダメージを決めるコインを投げない: 「ダメージを受けない」状態の相手には v0.4b の問い（与えたダメージによる回復は 0 なので、有効な要素に
        数えない）。コインが 0 枚（相手にエネルギーがない）なら投げないので問いはなく、ダメージは無効で回復もない。"""
        rejects(self, board(mon(CELEBI, (G, G), damage=20), opponent=mon(CHANSEY, (W,), prevent_damage=TURN - 1)), UseAttack(0, 0), "UNRESOLVED_PREVENTED_COIN_DAMAGE")
        state = board(mon(CELEBI, (G, G), damage=20), opponent=mon(CHANSEY, prevent_damage=TURN - 1))
        after = attack(state, 0)
        self.assertEqual((kinds(state, after, "damage_prevented"), drained(state, after), coins_of(state, after)), (["damage_prevented"], [], []))

    def test_neutral_shield_voids_the_evolved_butterfree(self):
        """進化したバタフリーのハイパーリバースは、ミュウの［ニュートラルシールド］でダメージが無効（与えていないので回復しない）。たねのセレビィのサイコリーフは受ける。"""
        state = board(mon(BUTTERFREE, (G, G, G), damage=30), opponent=mon(MEW, (PS,)))
        after = attack(state, 1)
        self.assertEqual((kinds(state, after, "damage_prevented"), drained(state, after)), (["damage_prevented"], []))
        state = board(mon(CELEBI, (G, G), damage=30), opponent=mon(MEW, (PS,)))
        after = attack(state, 0, HD)
        self.assertEqual((base_damages(state, after, 1), drained(state, after)), ([(20, 20)], [(20, 2, 2)]))

    def test_counterattack_knocks_out_before_the_heal(self):
        """相手の［はんげき］で使い手が HP 以上になったら、処理の対象がないのでとりのぞかない（既存の drain_heal_skipped）。"""
        state = board(mon(BUTTERFREE, (G, G, G), damage=70), opponent=mon(MACHAMP, (F_,)))
        after = attack(state, 1)
        self.assertEqual(kinds(state, after, "counterattack", "drain_heal", "drain_heal_skipped"), ["counterattack", "drain_heal_skipped"])

    def test_flee_decision_keeps_the_dealt_damage(self):
        """ダメージのあとに相手の決定（カスミのドククラゲの［にげこむ］）をはさんでも、与えたダメージを続きの情報で運び、とりのぞく数を失わない。複製・deepcopy・pickle からも 1 度だけ。"""
        state = board(mon(BUTTERFREE, (G, G, G), damage=50), opponent=mon(MISTYS_TENTACRUEL, (W, W)), opponent_bench=(RATTATA,))
        asked = attack(state, 1)
        self.assertIsNotNone(asked.decision)
        self.assertEqual(asked.decision.player, 1)
        for choices in (asked.decision.options[:asked.decision.max_choices], ()):
            if len(choices) < asked.decision.min_choices:
                continue
            done = same_answers(self, asked, choices)
            self.assertEqual(drained(asked, done), [(20, 2, 2)])

    def test_new_drains_judge_transparency_and_old_drains_do_not(self):
        """新しい与えたぶんの回復は、とりのぞく前に「とうめい」などを評価する（v0.104 の回復とそろえる）。v0.104 までの登録（reach なし）は評価しないまま（v0.104 の docs 9 章の差を変えない）。
        ワザを使ったポケモンが「とうめい」を持つ写しのカードはないので、要素を直接処理して確かめる。"""
        for reach, checks in ((True, 1), (False, 0)):
            state = board(mon(HAUNTER, (PS,), damage=30))
            res = K.Resolution(with_coin_results(state.clone(), HD))
            attacker = res.state.players[0].active
            fs = res.open_frame(K.FrameKind.ATTACK, parent=None, player=0, source_pid=attacker.pokemon_id, attack_key=AttackKey(BUTTERFREE, 1))
            fs.results["damage"] = E.DamageResult(P.OPP, 1, res.state.players[1].active.pokemon_id, True, 20, False)
            run = P.AttackRun(res, fs, (P.Drain("damage", full=True, reach=reach),), load_card_pool().definitions[BUTTERFREE].attacks[1])
            with self.subTest(reach=reach):
                self.assertFalse(P.Drain("damage", full=True, reach=reach).run(run))
                self.assertEqual(len([e for e in res.state.log if e["kind"] == "evade_check"]), checks)
                self.assertEqual(attacker.damage, 30 if reach else 10)


# ---------------------------------------------------------------- 6 章: プレゼント


class PresentTest(unittest.TestCase):
    def test_each_heads_count_runs_one_branch(self):
        """3 枚を 1 組で投げ、「おもて」の数で 1 つだけ: 3 → 60・1 → 40（ダメージ）、2 → 3 個・0 → すべて（相手の対戦ポケモンから。のっている数まで。回復の分岐にダメージのログはない）。"""
        for flips in ((HD, HD, HD), (HD, HD, TL), (HD, TL, TL), (TL, TL, TL)):
            for counters in (0, 2, 5):
                state = board(mon(DELIBIRD, (W, W)), opponent=mon(CHANSEY, damage=10 * counters), opponent_bench=(mon(RATTATA, damage=20),))
                after = attack(state, 0, *flips)
                heads = flips.count(HD)
                with self.subTest(heads=heads, counters=counters):
                    self.assertEqual(len(coins_of(state, after)), 3)
                    if heads in (1, 3):
                        damage = 60 if heads == 3 else 40
                        self.assertEqual(base_damages(state, after, 1), [(damage, damage)])
                        self.assertEqual(kinds(state, after, "attack_heal"), [])
                        self.assertEqual(after.players[1].active.damage, 10 * counters + damage)
                    else:
                        removed = counters if heads == 0 else min(3, counters)
                        self.assertEqual(kinds(state, after, "damage", "damage_prevented"), [])
                        heals = [(e["pokemon_id"], e["counters"], e["attacker"]) for e in new_events(state, after, "attack_heal")]
                        self.assertEqual(heals, [(state.players[1].active.pokemon_id, removed, 0)] if removed else [])
                        self.assertEqual(after.players[1].active.damage, 10 * (counters - removed))
                    self.assertEqual(after.players[1].bench[0].damage, 20)  # 控えは対象ではない
                    audited(self, after)

    def test_damage_only_protection_keeps_the_heal(self):
        """「ダメージを受けない」状態（かたまる）はダメージだけを止める: コインは投げ、ダメージの分岐は無効（damage_prevented）、回復の分岐は有効。ダメージカウンターがなくても回復の要素は
        無効ではない（投げる）。"""
        for counters in (0, 4):
            for flips, prevented in (((HD, HD, HD), True), ((HD, HD, TL), False)):
                state = board(mon(DELIBIRD, (W, W)), opponent=mon(CHANSEY, damage=10 * counters, prevent_damage=TURN - 1))
                after = attack(state, 0, *flips)
                with self.subTest(counters=counters, flips=flips):
                    self.assertEqual(len(coins_of(state, after)), 3)
                    self.assertEqual(kinds(state, after, "damage_prevented"), ["damage_prevented"] if prevented else [])
                    self.assertEqual(after.players[1].active.damage, 10 * counters if prevented else 10 * max(0, counters - 3))

    def test_barrier_voids_both_and_keeps_hc3(self):
        """「ワザをうけない」状態（バリアー）なら、ダメージも回復も無効なので、コインを投げるかが決まらない（既存の HC3）。"""
        state = board(mon(DELIBIRD, (W, W)), opponent=mon(CHANSEY, damage=30))
        target = state.players[1].active
        target.persistent_effects = (AttackBarrier(target.card, 1, TURN - 1, TURN),)
        rejects(self, state, UseAttack(0, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")

    def test_transparency_is_judged_once_in_the_chosen_branch(self):
        """相手のゴースト（「とうめい」）: 選ばれた分岐の要素を受ける前に 1 回だけ判定する（分岐の要素ごとに投げ直さない）。"""
        for flips, before in (((HD, HD, TL), 30), ((HD, TL, TL), 0)):
            for evade in (HD, TL):
                state = board(mon(DELIBIRD, (W, W)), opponent=mon(HAUNTER, (PS,), damage=before))
                after = attack(state, 0, *flips, evade)
                received = evade is TL
                with self.subTest(flips=flips, evade=evade):
                    self.assertEqual(len(new_events(state, after, "evade_check")), 1)
                    self.assertEqual(after.players[1].active.damage, (0 if received else 30) if before else (40 if received else 0))

    def test_counterattack_does_not_meet_the_timing_question(self):
        """「ダメージを受けたとき」の効果（カイリキーの［はんげき］）: ダメージの要素を先に並べたので、処理しない回復の要素で v0.38 の GK1 に当たらない（開発中の対戦で、ダメージの要素のあいだに
        回復の要素を置いた並びが止まった。並びは結果を変えない）。"""
        state = board(mon(DELIBIRD, (W, W)), opponent=mon(MACHAMP, (F_,)))
        after = attack(state, 0, HD, HD, HD)
        self.assertEqual(kinds(state, after, "damage", "counterattack"), ["damage", "counterattack"])
        self.assertEqual((after.players[1].active.damage, after.players[0].active.damage), (60, 10))
        audited(self, after)

    def test_esp_redo_redoes_the_three_coins_together(self):
        """ナツメのESP（ナツメのポケモンでないデリバードにつけた盤面。やり直しを選ぶと既存の ES3 で止まる）: やり直さない答えは、最初の 3 枚の組の分岐を 1 度だけ処理する。"""
        asked = attack(board(mon(DELIBIRD, (W, W), trainers=[(H.SABRINAS_ESP, TURN)]), opponent=mon(CHANSEY, damage=50)), 0, HD, HD, TL)
        self.assertEqual((asked.decision.kind, asked.decision.context_value("unresolved_code")), ("esp_redo", "UNRESOLVED_ESP_HOLDER_NOT_SABRINAS"))
        self.assertEqual(kinds(asked.clone(), asked, "attack_heal", "damage"), [])
        done = same_answers(self, asked, ())
        self.assertEqual(([e["counters"] for e in new_events(asked, done, "attack_heal")], coins_of(asked, done)), ([3], []))

    def test_copied_present_heals_the_copiers_opponent(self):
        """相手のワザとして使う（ピクシーのゆびをふる）プレゼントの「相手」は、使ったピクシーの相手（デリバード）。"""
        state = board(mon(CLEFABLE, (W,)), opponent=mon(DELIBIRD, (W, W), damage=40))
        after = answer(attack(state, 0), (0,), TL, TL, TL)
        self.assertEqual([(e["pokemon_id"], e["counters"], e["attacker"]) for e in new_events(state, after, "attack_heal")],
                         [(state.players[1].active.pokemon_id, 4, 0)])
        audited(self, after)

    def test_mew_receives_the_basic_delibird(self):
        """たねのデリバードのプレゼントは、ミュウ（［ニュートラルシールド］）も受ける（ダメージ・回復とも）。"""
        state = board(mon(DELIBIRD, (W, W)), opponent=mon(MEW, (PS,), damage=30))
        after = attack(state, 0, TL, TL, TL)
        self.assertEqual(after.players[1].active.damage, 0)


# ---------------------------------------------------------------- 8 章: 決定・再開・先読み・保存


class DecisionTest(unittest.TestCase):
    def test_clone_copy_and_pickle_resume_once(self):
        """山札から重ねる決定（選べるもののある・ない）を clone・deepcopy・pickle しても、同じ答えで同じ結果になり、コイン・回復・進化・切る処理は 1 度だけ。"""
        asked = attack(board(mon(METAPOD, (G, G), damage=30), deck=[BUTTERFREE, W]), 1, HD)
        done = same_answers(self, asked, asked.decision.options)
        self.assertEqual((kinds(asked, done, "evolve", "shuffle", "attack_heal"), coins_of(asked, done)), (["evolve", "shuffle"], []))
        empty = attack(board(mon(SUNKERN, (G, G), damage=30), deck=[W, W]), 1, HD)
        done = same_answers(self, empty, ())
        self.assertEqual(kinds(empty, done, "evolve_from_deck_none", "shuffle", "attack_heal"), ["evolve_from_deck_none", "shuffle"])
        self.assertEqual(max(FORMAT_VERSIONS), LATEST_FORMAT)
        self.assertIn(26, FORMAT_VERSIONS)  # この版で形式を上げていない。今の最新の形式は tests/test_catalog_contract.py（docs/testing.md）

    def test_preflight_methods_agree(self):
        """先読みの方法（derived・derived_full・legacy）は同じ結果（新しい型は v0.13 の止める関数の確かめた型ではないので、legacy でもすべての結果を試す）。上限は変えていない。
        サイコリーフの多くのコインは「おもて」の数でまとめる（実際には 1 枚ずつ投げる）。"""
        self.assertEqual(MAX_BRANCHES, 4096)
        many = tuple([W] * 12)
        cases = ((board(mon(METAPOD, (G, G), damage=30), deck=[BUTTERFREE, W]), 1, (HD,)), (board(mon(BUTTERFREE, (G, G, G), damage=30), opponent=mon(CHANSEY, (DCE, W))), 1, ()),
                 (board(mon(CELEBI, (G, G), damage=30), opponent=mon(CHANSEY, many)), 0, (HD,) * 12), (board(mon(DELIBIRD, (W, W)), opponent=mon(CHANSEY, damage=20)), 0, (HD, TL, HD)),
                 (board(mon(METAPOD, (W, W))), 0, ()), (board(mon(BUTTERFREE, (G, W))), 0, (HD,)))
        for state, index, flips in cases:
            results = []
            for mode in ("derived", "derived_full", "legacy"):
                after = apply_kernel(with_coin_results(state, *flips), UseAttack(0, index), preflight=mode)
                results.append(snap(after))
            with self.subTest(card=state.cards[state.players[0].active.card].card_id, index=index):
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0], results[2])


# ---------------------------------------------------------------- 9 章: ログの監査


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v105_problems``・tools/existing_effect_games.py の ``v105_replay_problems``）は、エンジンの ``EvolveAttackerFromDeck``・``Drain``・
    ``HealCounters`` を読まずに、ログから組み立てた場・コイン・ダメージと、やり直しの状態の山札の枚数で確かめる。エンジンの処理を一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py
    の ``GAMES`` の局。からやぶりしんか・ひざしをあびる・ハイパーリバース・サイコリーフ・プレゼントが出る組と seed）で、監査がそれを見つける（誤らせなければ、同じ局は監査を通る）。"""

    GAMES = ((("D105", "B105"), 1), (("M103", "B105"), 1), (("P31", "B105"), 2))

    @classmethod
    def results(cls, target, name, fake):
        from tools import existing_effect_games as games

        found = []
        with mock.patch.object(target, name, fake):
            for labels, seed in cls.GAMES:
                result = games.play(labels, seed, keep_state=True)
                if result.get("state") is not None:
                    found.append((result, log_problems(result["state"])))
        return found

    def test_the_unpatched_games_pass_the_audit(self):
        from tools import existing_effect_games as games

        for labels, seed in self.GAMES:
            result = games.play(labels, seed, keep_state=True)
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual((result["outcome"], result["audit"], log_problems(result["state"])), ("game_over", {}, []))
                v105 = result["v105"]
                self.assertTrue(v105["evolve_heal"] + v105["present_heal"] + v105["drain_coins_per_defender_energy_bonus_and_full_drain"] > 0)

    def test_audit_finds_a_missing_shuffle_after_looking(self):
        """山札を見た（選べるカードがなかった）のに切らない: やり直しの状態の山札の枚数と照らして見つける（監査の失敗の v105_shuffle）。"""

        def never(self, run, attacker):
            run.state.add_event("evolve_from_deck_none", player=run.player, pokemon_id=attacker.pokemon_id, effect=str(run.key))

        self.assertTrue(any(result["audit"].get("v105_shuffle") for result, _ in self.results(P.EvolveAttackerFromDeck, "_none", never)))

    def test_replay_check_finds_a_shuffle_of_an_unlooked_deck(self):
        """山札が 0 枚なのに切った（「山札を見た場合は」を無視していつも切る）: ``v105_replay_problems`` が宣言の直前の山札の枚数と照らして見つける。正式な対戦では山札が 0 枚の場面は
        起こらなかったので、盤面で確かめる（照らす関数は盤面のログでも同じ）。"""
        from tools.existing_effect_games import v105_replay_problems

        state = board(mon(SUNKERN, (G, G), damage=20), deck=[])
        honest = attack(state, 1, HD)
        self.assertEqual(v105_replay_problems(honest, {len(state.log): 0}), [])
        def always(self, run, attacker):
            run.state.add_event("evolve_from_deck_none", player=run.player, pokemon_id=attacker.pokemon_id, effect=str(run.key))
            P.shuffle_in_attack(run, self, run.player)

        with mock.patch.object(P.EvolveAttackerFromDeck, "_none", always):
            wrong = attack(state, 1, HD)
        self.assertEqual(len(shuffles(state, wrong)), 1)
        self.assertTrue(v105_replay_problems(wrong, {len(state.log): 0}))
        looked = board(mon(SUNKERN, (G, G), damage=20), deck=[W, W])
        done = answer(attack(looked, 1, HD), ())
        self.assertEqual(v105_replay_problems(done, {len(looked.log): 2}), [])
        self.assertTrue(v105_replay_problems(done, {len(looked.log): 0}))

    def test_audit_finds_a_short_full_heal_before_evolving(self):
        original = P.HealCounters.run

        def short(self, run):
            return original(dataclasses.replace(self, every=False, counters=1) if self.every and self.scope == E.HEAL_SELF else self, run)

        self.assertTrue([p for _, problems in self.results(P.HealCounters, "run", short) for p in problems if "すべて" in p or "とりのぞいていない" in p])

    def test_audit_finds_a_wrong_drain(self):
        original = P.Drain._remove

        def half(self, run, attacker, dealt, counters):
            return original(self, run, attacker, dealt, (counters + 1) // 2 if self.reach else counters)

        self.assertTrue([p for _, problems in self.results(P.Drain, "_remove", half) for p in problems if "drain_heal" in p or "与えたぶん" in p])

    def test_audit_finds_a_present_branch_mixup(self):
        """「おもて」2 枚の分岐でダメージを与えた（回復の分岐にダメージの要素を処理した）。"""
        original = P.AttackRun.coin_is

        def mixed(self, gate):
            name, side = gate
            if side == 1 and self.fs.coins.get(name) is not None and self.fs.coins[name].heads == 2 and len(self.fs.coins[name].results) == 3:
                return True
            return original(self, gate)

        self.assertTrue([p for _, problems in self.results(P.AttackRun, "coin_is", mixed) for p in problems if "分岐" in p or "プレゼント" in p or "neo3-050" in p])


class DocumentTest(unittest.TestCase):
    def test_document_names_the_shared_parts(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("EvolveAttackerFromDeck", "required", "shuffle_if_looked", "gate", "self_deck_evolution_open_question", "Drain", "reach", "DefenderEnergyUnitsTimes",
                       "HEAL_OPPONENT_ACTIVE", "ZeroDamageBelowNextTurn", "zero_damage_below_texts", "A3", "GK1", "DV2", "GV1", "PW4", "H1", "HC3", "T19b", "G37",
                       "b542bff", "73a1690", "GR-2000-P309-EVOLUTION-BY-NAME", "GR-2000-P310-EVOLUTION", "GR-2000-P312-DECK-HAND-DISCARD", "GR-2000-P319-HP-AND-DAMAGE",
                       "GR-2000-P320-RECOVERY", "GR-2000-P321-DAMAGE-ORDER", "GR-2000-P321-PREVENTED-ELEMENTS"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
