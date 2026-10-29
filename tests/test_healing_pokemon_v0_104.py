"""v0.104（docs/healing-pokemon-v0.104.md）: 回復のワザを持つポケモンの 12 枚（ワザ 24）と、回復の量・対象・とりのぞくかの選択の共通の処理。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面。12 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録
（GR-2000-P320-RECOVERY・GR-2000-P309-ATTACK-PROCEDURE・GR-2000-P321-PREVENTED-ELEMENTS、v0.9 の T4・T8、v0.41 の ``HealCounters``、v0.89 の ``TargetHeal``、v0.90 の
``cure_conditions``、v0.41 の ``SelfAttackLock``、v0.103 の発生元）。英語版の文面・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合は
していない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の
``--batch v0.104``）。
"""

from __future__ import annotations

import dataclasses
import pathlib
import unittest
from unittest import mock

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttackKey,
    EndTurn,
    ResolveDecision,
    UseAttack,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.conditions import CONFUSION, PARALYSIS, POISON, SLEEP
from kyuura_engine.decisions import OPTIONAL_HEAL, SELECT_ATTACK, SELECT_POKEMON
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.resolution import kernel as K
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.preflight import MAX_BRANCHES
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import AttackBarrier, CannotUseOwnAttack
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.log_audit import LATEST_FORMAT, log_problems
from tests.release_catalog import cards_after, cards_before
from tests.test_counter_keep_energy_protection_v0_101 import attack, pid, play
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_unown_family_powers_v0_96 import TURN, board, same_answers, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "healing-pokemon-v0.104.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, PS, G, F_, L = H.WATER, H.PSYCHIC, H.GRASS, H.FIGHTING, H.LIGHTNING
BELLOSSOM, MILTANK, TEDDIURSA, PILOSWINE = "neo1-015", "neo1-069", "neo2-048", "neo3-041"
BULBASAUR, BULBASAUR_QSG, BULBASAUR_IP1 = "ES1-001", "QSG-001", "IP1-018"
DEWGONG, DEWGONG_QSG, JIGGLYPUFF, JIGGLYPUFF_BOOK, LAPRAS = "ES2-007", "QSG-018", "PR1-002", "PR1-004", "SI-018"
V0104 = (BELLOSSOM, MILTANK, TEDDIURSA, PILOSWINE, BULBASAUR, BULBASAUR_QSG, BULBASAUR_IP1, DEWGONG, DEWGONG_QSG, JIGGLYPUFF, JIGGLYPUFF_BOOK, LAPRAS)
V0104_ATTACKS = [AttackKey(card, index) for card in V0104 for index in (0, 1)]
NEO_ODDISH, NEO_GLOOM, PRN_BELLOSSOM, SEEL, SWINUB = "neo1-001", "neo1-008", "PRN-043", "ES2-006", "neo3-038"
MEW, MEWTWO, HAUNTER, GASTLY = "PR1-005", "PMCG1-050", H.HAUNTER, H.GASTLY
PIDGEY, PIDGEOTTO, CLEFAIRY, CLEFABLE, RATTATA, GUST = H.PIDGEY, H.PIDGEOTTO, H.CLEFAIRY, H.CLEFABLE, H.RATTATA, H.GUST
BELOW = {BELLOSSOM: [NEO_ODDISH, NEO_GLOOM], PRN_BELLOSSOM: [NEO_ODDISH, NEO_GLOOM], NEO_GLOOM: NEO_ODDISH, DEWGONG: SEEL, DEWGONG_QSG: SEEL, PILOSWINE: SWINUB,
         PIDGEOTTO: PIDGEY, HAUNTER: GASTLY, CLEFABLE: CLEFAIRY}

# 依頼で示された固定データの日本語（写しの文面と照らす。広い正規化をしない）。(名前, 必要なエネルギー, ダメージの目安, 説明)
SWEET_NECTAR = "コインを投げて「おもて」なら、自分の場にいるポケモンを1匹選び、そのポケモンにのっているダメージカウンターを、すべてとりのぞく。"
FIRST_AID_ONE = "このカードにダメージカウンターがのっていれば、それを1つ取りのぞく"
QUOTED = {
    BELLOSSOM: (70, ("あまいみつ", ("grass",), None, SWEET_NECTAR), ("フラワーダンス", ("grass", "grass", "colorless"), "30×", "自分の場にいる「キレイハナ」の数×30のダメージ。")),
    MILTANK: (70, ("ミルクのみ", ("colorless",), None, "コインを2枚投げ、「おもて」の数×2個のダメージカウンターを、自分からとりのぞく。"),
              ("のしかかり", ("colorless",) * 3, "20", "コインを投げて「おもて」なら、相手を「マヒ」状態にする。")),
    TEDDIURSA: (40, ("ひっかく", ("colorless",), "10", None),
                ("おひるね", ("colorless",) * 2, None, "自分にのっているダメージカウンターを、すべてとりのぞく。その後、自分を「ねむり」状態にする。")),
    PILOSWINE: (90, ("ひとやすみ", ("colorless",) * 2, None, "自分にのっているダメージカウンターを、3個とりのぞく。"),
                ("もうとっしん", ("fighting", "fighting", "colorless", "colorless"), "80", "自分にも30ダメージ。次の自分の番、このカードは「もうとっしん」を使うことができない。")),
    **{card: (50, ("かいふく", ("colorless",), None, FIRST_AID_ONE + ("。" if card == BULBASAUR_IP1 else "")), ("どくのたね", ("grass",), None, "相手を「どく」状態にする。"))
       for card in (BULBASAUR, BULBASAUR_QSG, BULBASAUR_IP1)},
    **{card: (60, ("ねむる", ("colorless",) * 2, None,
                   "自分にのっているダメージカウンターをすべてとりのぞき、自分の「どく・ねむり・マヒ・こんらん」状態を、すべて回復させる。その後、自分を「ねむり」状態にする。"),
              ("オーロラウェーブ", ("water",) * 3, "30", "コインを投げて「おもて」なら、相手を「こんらん」状態にする。")) for card in (DEWGONG, DEWGONG_QSG)},
    **{card: (50, ("かいふく", ("colorless",), None, "自分についているダメージカウンターを1つ取り除くことができる。"),
              ("すてみタックル", ("colorless",) * 3, "40", "自分にも20ダメージ。")) for card in (JIGGLYPUFF, JIGGLYPUFF_BOOK)},
    LAPRAS: (70, ("やさしいうた", ("colorless",), None, "自分と相手にのっているダメージカウンターを、それぞれ2つずつ、とりのぞく。その後、相手を「ねむり」状態にする。"),
             ("れいとうビーム", ("water",) * 2, "20", "コインを投げて「おもて」なら、相手を「マヒ」状態にする。")),
}
EXPECTED = {
    (BELLOSSOM, 0): E.CoinChooseOwnPokemonHealAll(), (BELLOSSOM, 1): E.OwnNamedPokemonCountDamage(("キレイハナ",), 30),
    (MILTANK, 0): E.CoinsHealSelfTimes(2, 2), (MILTANK, 1): E.ParalyzeOnHeads(),
    (TEDDIURSA, 0): E.DamageOnly(), (TEDDIURSA, 1): E.HealAllSelfThenSelfSleep(),
    (PILOSWINE, 0): E.HealSelfWithoutDamage(3), (PILOSWINE, 1): E.DamageAndSelfDamageThenLockSelf(30),
    **{(card, 0): E.HealSelfWithoutDamage(1) for card in (BULBASAUR, BULBASAUR_QSG, BULBASAUR_IP1)},
    **{(card, 1): E.PoisonWithoutDamage() for card in (BULBASAUR, BULBASAUR_QSG, BULBASAUR_IP1)},
    **{(card, 0): E.HealAllSelfThenSelfSleep(E.REST_CURES) for card in (DEWGONG, DEWGONG_QSG)},
    **{(card, 1): E.ConfuseOnHeads() for card in (DEWGONG, DEWGONG_QSG)},
    **{(card, 0): E.OptionalHealSelf(1) for card in (JIGGLYPUFF, JIGGLYPUFF_BOOK)},
    **{(card, 1): E.DamageAndSelfDamage(20) for card in (JIGGLYPUFF, JIGGLYPUFF_BOOK)},
    (LAPRAS, 0): E.HealBothActivesThenSleep(2), (LAPRAS, 1): E.ParalyzeOnHeads(),
}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def heals(before, after):
    """とりのぞいたログの (ポケモン, 数, あとのダメージ)。"""
    return [(e["pokemon_id"], e["counters"], e["total_damage"]) for e in new_events(before, after, "attack_heal")]


def kinds(before, after, *names):
    """ワザの効果のログ（``effect`` がワザ）の種類。番の間のポケモンチェック（ねむりのコイン）のログは入れない。"""
    return [e["kind"] for e in new_events(before, after, *names) if "#" in str(e.get("effect", ""))]


def slept(before, after):
    """ワザの効果でねむりにしたポケモン（そのあとの番の間に目を覚ましても数える）。"""
    return [e["pokemon_id"] for e in new_events(before, after, "special_condition") if e["condition"] == SLEEP and "#" in str(e.get("effect", ""))]


def answer(state, choices, *coins):
    d = state.decision
    return apply_kernel(with_coin_results(state, *coins) if coins else state, ResolveDecision(d.player, d.id, tuple(choices)))


def coins_of(before, after):
    return [e["result"] for e in new_events(before, after, "coin_flip") if e.get("source") == "attack"]


# ---------------------------------------------------------------- 2・3 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_entries_and_printed_texts(self):
        """12 枚・24 のワザの名前・必要なエネルギー・ダメージの目安・説明は依頼の日本語と同じ（目安なしは null で、0 ダメージではない）。特殊能力は 0。"""
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_104"]), V0104)
        for card, (hp, *attacks) in QUOTED.items():
            definition = pool.definitions[card]
            self.assertEqual((definition.hp, definition.powers), (hp, ()))
            self.assertIn(card, pool.playable_ids)
            for index, (name, cost, display, text) in enumerate(attacks):
                printed = definition.attacks[index]
                with self.subTest(card=card, index=index):
                    self.assertEqual((printed.name_ja, tuple(t.value for t in printed.cost), printed.damage_display, printed.text_ja), (name, cost, display, text))
                    entry = DEFAULT_EFFECTS.attack_entry(card, index)
                    self.assertEqual(entry.effect, EXPECTED[(card, index)])
                    self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                                     (name, text, text, None if text is None else "kyuura data/cards.json"))
                    self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card, printed, definition.attacks))
            self.assertEqual(len(definition.attacks), 2)

    def test_same_data_groups_share_the_registration(self):
        """同じカードの組 SC-ES1-001（3 枚）・SC-ES2-007・SC-PR1-002（2 枚ずつ）。日本語の pokemon 欄の同じ組は同じ登録の値にまとめ、IP1-018 はかいふくの句点だけが違うので、id の
        登録（文面は写しのまま）を置き、処理の値を同じにする。原文は直さない。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        self.assertEqual(E.SAME_DATA_CARDS_V0_104, {BULBASAUR_QSG: BULBASAUR, DEWGONG_QSG: DEWGONG, JIGGLYPUFF_BOOK: JIGGLYPUFF})
        groups = {"SC-ES1-001": (BULBASAUR, BULBASAUR_QSG, BULBASAUR_IP1), "SC-ES2-007": (DEWGONG, DEWGONG_QSG), "SC-PR1-002": (JIGGLYPUFF, JIGGLYPUFF_BOOK)}
        for group, members in groups.items():
            self.assertEqual({cards[c]["same_card_group"] for c in members}, {group})
        for new, original in E.SAME_DATA_CARDS_V0_104.items():
            self.assertEqual((cards[new]["pokemon"], cards[new]["name"]["ja"]), (cards[original]["pokemon"], cards[original]["name"]["ja"]))
            for index in (0, 1):
                self.assertEqual(DEFAULT_EFFECTS.attack_entry(new, index), DEFAULT_EFFECTS.attack_entry(original, index))
        ip1, es1 = cards[BULBASAUR_IP1]["pokemon"], cards[BULBASAUR]["pokemon"]
        self.assertEqual(ip1["attacks"][0]["text"]["ja"], es1["attacks"][0]["text"]["ja"] + "。")
        self.assertEqual({**ip1, "attacks": [{**ip1["attacks"][0], "text": es1["attacks"][0]["text"]}, ip1["attacks"][1]]}, es1)
        self.assertNotEqual(DEFAULT_EFFECTS.attack_entry(BULBASAUR_IP1, 0), DEFAULT_EFFECTS.attack_entry(BULBASAUR, 0))
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(BULBASAUR_IP1, 0).effect, DEFAULT_EFFECTS.attack_entry(BULBASAUR, 0).effect)
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(BULBASAUR_IP1, 1), DEFAULT_EFFECTS.attack_entry(BULBASAUR, 1))
        self.assertNotIn(BULBASAUR_IP1, E.SAME_DATA_CARDS_V0_104)

    def test_programs(self):
        """新しい型の要素の並び（既存の要素とその小さな拡張）。カードの id による分岐はない。"""
        builders = {
            E.CoinChooseOwnPokemonHealAll(): (P.Coin("coin"), P.ChooseEffectTarget(side=E.TARGET_SIDE_OWN, gate=("coin", HD)),
                                              P.TargetHeal(every=True, gate=("coin", HD), side=E.TARGET_SIDE_OWN)),
            E.OwnNamedPokemonCountDamage(("キレイハナ",), 30): (P.Damage(P.OPP, P.PokemonCountTimes(30, P.SCOPE_OWN_IN_PLAY, ("キレイハナ",))),),
            E.CoinsHealSelfTimes(2, 2): (P.Coin("coin", count=2), P.HealCounters(heads_of="coin", per_heads=2)),
            E.HealAllSelfThenSelfSleep(): (P.HealCounters(every=True), P.Status(SLEEP, target=P.SELF)),
            E.HealAllSelfThenSelfSleep(E.REST_CURES): (P.HealCounters(every=True), P.CureOwnConditions(E.REST_CURES, reach=True), P.Status(SLEEP, target=P.SELF)),
            E.DamageAndSelfDamageThenLockSelf(30): (P.Damage(P.OPP, P.Printed()), P.Damage(P.SELF, P.Fixed(30), name="self_damage"), P.SelfAttackLock(None)),
            E.OptionalHealSelf(1): (P.OptionalHealSelf(1),),
            E.HealBothActivesThenSleep(2): (P.HealCounters(2, scope=E.HEAL_BOTH_ACTIVE), P.Status(SLEEP)),
            E.HealSelfWithoutDamage(1): (P.HealCounters(1),),
        }
        for effect, program in builders.items():
            with self.subTest(effect=effect):
                self.assertEqual(P.BUILDERS[type(effect)](effect), program)
        self.assertEqual(E.REST_CURES, (POISON, SLEEP, PARALYSIS, CONFUSION))
        self.assertEqual(E.DamageAndSelfDamageThenLockSelf(30).attack_lock_terms(), (CannotUseOwnAttack, None))
        self.assertEqual(set(E.HealBothActivesThenSleep(2).opponent_effect_elements), {E.HEAL_ELEMENT, SLEEP})
        self.assertEqual(E.CoinChooseOwnPokemonHealAll().opponent_effect_elements, ())
        for cls in {type(e) for e in EXPECTED.values()} - {E.DamageOnly, E.ParalyzeOnHeads, E.PoisonWithoutDamage, E.ConfuseOnHeads, E.DamageAndSelfDamage, E.HealSelfWithoutDamage}:
            self.assertIn(cls, H.ATTACK_TYPES_SINCE_V0_17)
            self.assertIs(cls.resolve, E.AttackEffect.resolve)

    def test_reused_types_match_the_printed_text(self):
        """既存の型のチェックは形だけのもの（DamageAndSelfDamage・ParalyzeOnHeads など）があるので、原文と処理の対応を照らす: 同じ型・同じ文面の登録がほかにあり、文面の数がその
        型の値と同じ。"""
        registered = {}
        for key in DEFAULT_EFFECTS.attack_keys():
            if key.card_id in V0104:
                continue
            entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
            registered.setdefault((entry.effect, entry.play_text_ja), key)
        for (card, index), effect in EXPECTED.items():
            if type(effect) in (E.ParalyzeOnHeads, E.ConfuseOnHeads, E.PoisonWithoutDamage, E.DamageAndSelfDamage):
                text = DEFAULT_EFFECTS.attack_entry(card, index).play_text_ja
                with self.subTest(card=card, index=index):
                    self.assertIn((effect, text), registered)
        self.assertEqual(E.DamageAndSelfDamage(20).self_damage, int(QUOTED[JIGGLYPUFF][2][3].removeprefix("自分にも").removesuffix("ダメージ。")))
        self.assertEqual(load_card_pool().definitions[TEDDIURSA].attacks[0].text_ja, None)
        self.assertEqual(E.DamageOnly().check(load_card_pool().definitions[TEDDIURSA].attacks[0]), [])

    def test_texts_are_not_normalized(self):
        """書き方は対象・数・条件と結び付けた完全な一致だけ（一律の正規化・部分一致で通さない）。"""
        pool = load_card_pool()
        first_aid = pool.definitions[BULBASAUR].attacks[0]
        for changed in (FIRST_AID_ONE.replace("1つ", "2つ"), FIRST_AID_ONE.replace("のっていれば、", ""), FIRST_AID_ONE + "。。", "自分" + FIRST_AID_ONE[5:],
                        FIRST_AID_ONE.replace("取りのぞく", "とりのぞく")):
            with self.subTest(changed=changed):
                self.assertNotEqual(E.HealSelfWithoutDamage(1).check(dataclasses.replace(first_aid, text_ja=changed)), [])
        self.assertNotEqual(E.HealSelfWithoutDamage(2).check(first_aid), [])
        self.assertEqual(E.HealSelfWithoutDamage(1).check(first_aid), [])
        jiggly = pool.definitions[JIGGLYPUFF].attacks[0]
        self.assertNotEqual(E.OptionalHealSelf(1).check(dataclasses.replace(jiggly, text_ja="自分についているダメージカウンターを1つ取り除く。")), [])
        self.assertNotEqual(E.HealSelfWithoutDamage(1).check(jiggly), [])  # 選べる回復を必ずの回復に登録しない
        self.assertNotEqual(E.OptionalHealSelf(1).check(first_aid), [])
        dance = pool.definitions[BELLOSSOM].attacks[1]
        self.assertNotEqual(E.OwnNamedPokemonCountDamage(("クサイハナ",), 30).check(dance), [])
        self.assertNotEqual(E.OwnNamedPokemonCountDamage(("キレイハナ",), 20).check(dance), [])
        nap, rest = pool.definitions[TEDDIURSA].attacks[1], pool.definitions[DEWGONG].attacks[0]
        self.assertNotEqual(E.HealAllSelfThenSelfSleep().check(rest), [])
        self.assertNotEqual(E.HealAllSelfThenSelfSleep(E.REST_CURES).check(nap), [])
        with self.assertRaises(ValueError):
            E.HealAllSelfThenSelfSleep((POISON, CONFUSION))
        with self.assertRaises(ValueError):
            P.HealCounters(counters=3, every=True)
        with self.assertRaises(ValueError):
            P.HealCounters(counters=3, per_heads=2)
        with self.assertRaises(ValueError):
            P.TargetHeal()

    def test_unregistered_without_the_v0_104_entries(self):
        """今回の登録だけを除くと、ちょうど 12 枚が未対応にもどる（同じデータの組も id ごとに数える）。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V0104_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V0104))
        self.assertEqual(set(V0104) & set(cards_before(read_extract(), "0.104")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.103")) & set(cards_before(read_extract(), "0.105")), set(V0104))

    def test_extract_keeps_sources_and_gaps(self):
        """転記元は 8 枚が pcg-search.com・キレイハナ・ミルタンク・ヒメグマが nazonobasho.com・イノムーがポケモンWiki。レベル・図鑑番号の欠けは補わない。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        sources = {card: cards[card]["ja_text_source"].split("/")[2] for card in V0104}
        self.assertEqual({card for card, host in sources.items() if host == "pcg-search.com"},
                         {BULBASAUR, BULBASAUR_QSG, BULBASAUR_IP1, DEWGONG, DEWGONG_QSG, JIGGLYPUFF, JIGGLYPUFF_BOOK, LAPRAS})
        self.assertEqual({card for card, host in sources.items() if host == "nazonobasho.com"}, {BELLOSSOM, MILTANK, TEDDIURSA})
        self.assertEqual(sources[PILOSWINE], "wiki.pokemonwiki.com")
        for card in (BULBASAUR, BULBASAUR_QSG, BULBASAUR_IP1, DEWGONG, DEWGONG_QSG):
            self.assertEqual(cards[card]["data_gaps"], ["pokemon.dex", "jp_print.level"])
        for card in (JIGGLYPUFF, JIGGLYPUFF_BOOK):
            self.assertEqual(cards[card]["data_gaps"], ["jp_print.level"])
            self.assertEqual(cards[card]["pokemon"]["attacks"][0]["text"]["en"], "Remove 1 damage counter from Jigglypuff.")  # 英語の欄は選ばない。日本語で置きかえない

    def test_adoption_records(self):
        """12 件の採用の記録（kyuura 73a1690・外部照合なし・kyuura の記録なし）。処理に使う文面は印刷の文面（説明文のないひっかくは持たない）。"""
        import json

        sources = json.loads((ROOT / "kyuura_engine/data/card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine/data/research_links.json").read_text(encoding="utf-8"))["latest_descriptions"]["adopted_printed_text"]
        for card in V0104:
            record = sources[card]
            self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"], record["external_checks"], record["issues"]),
                             ("kyuura_data", "adopted", "73a169063463bbf7bcaa3137d70cbf9721d11534", [], [], []))
            parts = ("attack/1",) if card == TEDDIURSA else ("attack/0", "attack/1")
            self.assertEqual(record["play_text"], {part: "kyuura_printed_text" for part in parts})
            for part in parts:
                self.assertIn(f"{card}/{part}", links)
        self.assertNotIn(f"{TEDDIURSA}/attack/0", links)


# ---------------------------------------------------------------- 4.1・4.2 節: 量・対象・順番


class HealAmountTest(unittest.TestCase):
    def test_fixed_count_takes_at_most_what_is_on(self):
        """ひとやすみ（3 個）・フシギダネのかいふく（1 個）: 0 個なら何もしない（とりのぞく処理がない。ログもない）、少なければすべて、多ければ決まった数。"""
        for card, energy, damages in ((PILOSWINE, (F_, F_), {0: 0, 20: 0, 50: 20}), (BULBASAUR, (G,), {0: 0, 10: 0, 30: 20}),
                                      (BULBASAUR_IP1, (G,), {0: 0, 10: 0, 30: 20})):
            for before_damage, left in damages.items():
                state = board(mon(card, energy, damage=before_damage))
                after = attack(state, 0)
                with self.subTest(card=card, damage=before_damage):
                    expected = [] if before_damage == 0 else [(state.players[0].active.pokemon_id, (before_damage - left) // 10, left)]
                    self.assertEqual(heals(state, after), expected)
                    self.assertEqual(after.players[0].active.damage, left)
                    self.assertEqual(coins_of(state, after), [])
                    audited(self, after)

    def test_milk_drink_flips_two_coins_and_removes_twice_the_heads(self):
        """ミルクのみ: コインはいつも 2 枚（0 個でも、とりのぞける数が少なくても減らさない）。とりのぞくのは「おもて」の数 × 2 個（のっている数まで）。"""
        for damage in (0, 10, 30, 50):
            for flips in ((TL, TL), (HD, TL), (TL, HD), (HD, HD)):
                state = board(mon(MILTANK, (W,), damage=damage))
                after = attack(state, 0, *flips)
                heads = flips.count(HD)
                removed = min(2 * heads, damage // 10)
                with self.subTest(damage=damage, flips=flips):
                    self.assertEqual(len(coins_of(state, after)), 2)
                    self.assertEqual(after.players[0].active.damage, damage - 10 * removed)
                    self.assertEqual(heals(state, after), [(state.players[0].active.pokemon_id, removed, damage - 10 * removed)] if removed else [])

    def test_nap_time_heals_all_then_sleeps(self):
        """おひるね: すべてとりのぞく（大きな数で代用しない）→ 自分をねむり。0 個でもねむりは省かない。"""
        for damage in (0, 10, 30):
            state = board(mon(TEDDIURSA, (W, W), damage=damage))
            after = attack(state, 1)
            with self.subTest(damage=damage):
                self.assertEqual(heals(state, after), [(1, damage // 10, 0)] if damage else [])
                self.assertEqual(kinds(state, after, "attack_heal", "special_condition")[-1], "special_condition")
                self.assertEqual(slept(state, after), [1])
                audited(self, after)

    def test_gentle_song_heals_both_actives_then_sleeps_the_opponent(self):
        """やさしいうた: 自分 → 相手の対戦ポケモンの順に、それぞれ 2 個まで。控えは含めない。どちらかが 0 個でも、もう一方とねむりは省かない。"""
        for mine, theirs in ((0, 30), (10, 10), (30, 0), (50, 50)):
            state = board(mon(LAPRAS, (W,), damage=mine), bench=(mon(RATTATA, damage=10),), opponent=mon(H.CHANSEY, damage=theirs),
                          opponent_bench=(mon(RATTATA, damage=20),))
            after = attack(state, 0)
            me, them = state.players[0].active.pokemon_id, state.players[1].active.pokemon_id
            expected = [(p, min(2, d // 10), d - 10 * min(2, d // 10)) for p, d in ((me, mine), (them, theirs)) if d]
            with self.subTest(mine=mine, theirs=theirs):
                self.assertEqual(heals(state, after), expected)
                self.assertTrue(all("attacker" in e for e in new_events(state, after, "attack_heal") if e["pokemon_id"] == them))
                self.assertEqual(slept(state, after), [them])
                self.assertEqual((after.players[0].bench[0].damage, after.players[1].bench[0].damage), (10, 20))
                audited(self, after)

    def test_sweet_nectar_flips_first_then_chooses_any_own_pokemon(self):
        """あまいみつ: コイン →「おもて」なら自分の場（バトル場 → ベンチ）から 1 匹を選ぶ（先に選ばない。のっていないポケモンも選べる）→ すべてとりのぞく。"""
        state = board(mon(BELLOSSOM, (G,), damage=30), bench=(mon(RATTATA, damage=20), mon(RATTATA)), opponent_bench=(mon(RATTATA, damage=10),))
        tails = attack(state, 0, TL)
        self.assertIsNone(tails.decision)
        self.assertEqual(heals(state, tails), [])
        asked = attack(state, 0, HD)
        own = [p.pokemon_id for p in state.players[0].in_play()]
        self.assertEqual((asked.decision.kind, asked.decision.player, asked.decision.options, asked.decision.min_choices, asked.decision.max_choices),
                         (SELECT_POKEMON, 0, tuple(own), 1, 1))
        self.assertEqual(coins_of(state, asked), ["heads"])
        audited(self, asked)
        for target, damage in zip(own, (30, 20, 0)):
            done = answer(asked, (target,))
            with self.subTest(target=target):
                self.assertEqual(heals(asked, done), [(target, damage // 10, 0)] if damage else [])
                self.assertEqual(coins_of(asked, done), [])  # 選んだあとにコインを投げ直さない
                audited(self, done)

    def test_first_aid_is_optional_and_needs_counters(self):
        """プリンのかいふく: のっていなければ決定を出さない。のっていれば、取り除くか（0〜1）。取り除かないなら attack_heal_declined。「ダメージを与えたら」の条件はない。"""
        state = board(mon(JIGGLYPUFF, (W,)))
        nothing = attack(state, 0)
        self.assertIsNone(nothing.decision)
        self.assertEqual(kinds(state, nothing, "attack_heal", "attack_heal_declined"), [])
        state = board(mon(JIGGLYPUFF, (W,), damage=20))
        asked = attack(state, 0)
        me = state.players[0].active.pokemon_id
        self.assertEqual((asked.decision.kind, asked.decision.options, asked.decision.min_choices, asked.decision.max_choices, asked.decision.context_value("counters")),
                         (OPTIONAL_HEAL, (me,), 0, 1, 1))
        audited(self, asked)
        yes, no = answer(asked, (me,)), answer(asked, ())
        self.assertEqual((heals(asked, yes), yes.players[0].active.damage), ([(me, 1, 10)], 10))
        self.assertEqual([(e["kind"], e["counters"]) for e in new_events(asked, no, "attack_heal", "attack_heal_declined")], [("attack_heal_declined", 1)])
        self.assertEqual(no.players[0].active.damage, 20)
        for done in (yes, no):
            audited(self, done)


class ConditionOrderTest(unittest.TestCase):
    def test_nap_time_replaces_confusion_and_keeps_poison(self):
        """おひるね: 回復させる特殊状態は書かれていないので、こんらんはねむりで置きかわり（p.322）、どくは残る。"""
        state = board(mon(TEDDIURSA, (W, W), damage=20, confusion=True, poison=10))
        after = attack(state, 1, HD, TL)  # こんらんのコインは「おもて」、番の間のねむりのコインは「うら」
        conditions = after.players[0].active.conditions
        self.assertTrue(conditions.asleep)
        self.assertIsNotNone(conditions.poison)
        self.assertEqual([e["reason"] for e in new_events(state, after, "special_conditions_removed")], ["replaced"])  # 置きかえのログは effect を持たない
        self.assertEqual(heals(state, after), [(1, 2, 0)])
        audited(self, after)

    def test_rest_cures_the_listed_conditions_then_sleeps_and_keeps_other_effects(self):
        """ねむる: すべてとりのぞく → 説明の「どく・ねむり・マヒ・こんらん」を回復させる → 自分をねむり。マーカー・持続する効果は消さない（完全な初期化にしない）。"""
        state = board(mon(DEWGONG, (W, W), damage=30, confusion=True, poison=20, prevent_damage=TURN - 1, markers=("bone",)))
        after = attack(state, 0, HD, TL)
        dewgong = after.players[0].active
        self.assertEqual(kinds(state, after, "attack_heal", "special_conditions_removed", "special_condition"),
                         ["attack_heal", "special_conditions_removed", "special_condition"])
        cured = new_events(state, after, "special_conditions_removed")[0]
        self.assertEqual((cured["reason"], set(cured["conditions"])), ("cured", {POISON, CONFUSION}))
        self.assertTrue(dewgong.conditions.asleep)
        self.assertIsNone(dewgong.conditions.poison)
        self.assertEqual(dewgong.damage, 0)
        self.assertEqual([m.kind for m in dewgong.markers], ["bone"])
        # 持続する効果（かたまる。はたらく番はこの番）は、ねむるでは消えず、この番の終わりに期限で消える
        self.assertEqual([(e["persistent_effect"], e["reason"]) for e in new_events(state, after, "persistent_effect_removed")], [("prevent_damage", "expired")])
        self.assertEqual(new_events(state, after, "marker_removed"), [])
        audited(self, after)

    def test_rest_without_counters_or_conditions_still_sleeps(self):
        state = board(mon(DEWGONG_QSG, (W, W)))
        after = attack(state, 0, TL)
        self.assertEqual(kinds(state, after, "attack_heal", "special_conditions_removed", "special_condition"), ["special_condition"])
        self.assertTrue(after.players[0].active.conditions.asleep)

    def test_sleep_and_paralysis_cures_are_reached_only_by_the_element(self):
        """ねむり・マヒのポケモンはワザを宣言できない（通常は「ねむる」が回復させるのはどく・こんらん）。ねむり・マヒからの回復は、要素を直接処理して確かめる（合法な対戦の経路では
        起こらない。相手のワザとして使うポケモンも、ワザを使う時にねむり・マヒではない）。"""
        for spec, code in (({"sleep": True}, "POKEMON_ASLEEP"), ({"paralysis": TURN - 1}, "POKEMON_PARALYZED")):
            state = board(mon(DEWGONG, (W, W), damage=10, **spec))
            rejects(self, state, UseAttack(0, 0), code, IllegalActionError)
            res = K.Resolution(state.clone())
            attacker = res.state.players[0].active
            fs = res.open_frame(K.FrameKind.ATTACK, parent=None, player=0, source_pid=attacker.pokemon_id, attack_key=AttackKey(DEWGONG, 0))
            attacker.persistent_effects = (AttackBarrier(attacker.card, 0, TURN - 1, TURN + 1),)
            run = P.AttackRun(res, fs, (P.CureOwnConditions(E.REST_CURES, reach=True),), res.state.definitions[DEWGONG].attacks[0])
            with self.subTest(spec=spec):
                self.assertFalse(P.CureOwnConditions(E.REST_CURES, reach=True).run(run))
                self.assertEqual(attacker.conditions.names(), ())
                self.assertEqual((res.state.log[-1]["kind"], res.state.log[-1]["reason"]), ("special_conditions_removed", "cured"))
                self.assertEqual(len(attacker.persistent_effects), 1)  # 持続する効果は回復させる特殊状態ではない


class ReachTest(unittest.TestCase):
    def test_transparency_is_judged_once_for_the_heal_and_the_sleep(self):
        """相手のゴースト（「とうめい」）へのとりのぞく効果とねむりは、1 つのワザで 1 回の判定（T4）。「おもて」なら両方を受けない。自分からとりのぞく効果は残る。"""
        for coin, received in ((HD, False), (TL, True)):
            state = board(mon(LAPRAS, (W,), damage=20), opponent=mon(HAUNTER, (PS,), damage=20))
            after = attack(state, 0, coin)
            them = state.players[1].active.pokemon_id
            with self.subTest(coin=coin):
                self.assertEqual(len(new_events(state, after, "evade_check")), 1)
                self.assertEqual(after.players[0].active.damage, 0)
                self.assertEqual(after.players[1].active.damage, 0 if received else 20)
                self.assertEqual(slept(state, after), [them] if received else [])
                self.assertEqual([e["element"] for e in new_events(state, after, "attack_evaded")], [] if received else [E.HEAL_ELEMENT, SLEEP])
                self.assertEqual(new_events(state, after, "evade_check")[0]["pokemon_id"], them)

    def test_own_bench_transparency_for_sweet_nectar(self):
        """自分の控えのゴースト（「とうめい」）を選んでも、とりのぞく前に判定する（自分のワザでもはたらく。T8）。0 個のポケモンを選んだら判定しない。"""
        state = board(mon(BELLOSSOM, (G,)), bench=(mon(HAUNTER, (PS,), damage=30), mon(H.GASTLY)))
        asked = attack(state, 0, HD)
        haunter, gastly = state.players[0].bench[0].pokemon_id, state.players[0].bench[1].pokemon_id
        evaded = answer(asked, (haunter,), HD)
        self.assertEqual((len(new_events(asked, evaded, "evade_check")), heals(asked, evaded)), (1, []))
        received = answer(asked, (haunter,), TL)
        self.assertEqual(heals(asked, received), [(haunter, 3, 0)])
        empty = answer(asked, (gastly,))
        self.assertEqual(new_events(asked, empty, "evade_check", "attack_heal"), [])

    def test_barrier_voids_only_the_opponent_parts(self):
        """相手が「ワザをうけない」状態（バリアー）なら、相手からとりのぞく効果とねむりは無効（effect_prevented）。自分からとりのぞく効果は有効。"""
        state = board(mon(LAPRAS, (W,), damage=20), opponent=mon(MEWTWO, (PS, PS), damage=20))
        target = state.players[1].active
        target.persistent_effects = (AttackBarrier(target.card, 1, TURN - 1, TURN),)
        after = attack(state, 0)
        self.assertEqual([(e["element"], e["persistent_effect"]) for e in new_events(state, after, "effect_prevented")],
                         [(E.HEAL_ELEMENT, "attack_barrier"), (SLEEP, "attack_barrier")])
        self.assertEqual((after.players[0].active.damage, after.players[1].active.damage, slept(state, after)), (0, 20, []))

    def test_damage_only_protection_does_not_stop_the_heal_or_the_sleep(self):
        """「ダメージを受けない」状態（かたまる）はダメージ以外の効果を止めない（GR-2000-P321-PREVENTED-ELEMENTS）。"""
        state = board(mon(LAPRAS, (W,)), opponent=mon(H.CHANSEY, damage=40, prevent_damage=TURN - 1))
        after = attack(state, 0)
        self.assertEqual((after.players[1].active.damage, slept(state, after)), (20, [state.players[1].active.pokemon_id]))

    def test_heals_are_not_damage(self):
        """とりのぞく効果はダメージではない（GR-2000-P320-RECOVERY）: 弱点・抵抗力・軽減を計算せず、「ダメージを受けたとき」の反応（カイリキーの［はんげき］）を起こさない。"""
        state = board(mon(LAPRAS, (W,), damage=20), opponent=mon(H.MACHAMP, (F_,), damage=30, evolved_from=[H.MACHOP, H.MACHOKE]))
        after = attack(state, 0)
        self.assertEqual(new_events(state, after, "damage", "counterattack", "damage_prevented"), [])
        self.assertEqual((after.players[0].active.damage, after.players[1].active.damage), (0, 10))
        audited(self, after)

    def test_coins_that_decide_own_heals_are_flipped_even_against_a_barrier(self):
        """ミルクのみ・あまいみつのコインは自分のポケモンへの回復だけを決めるので、相手の状態（バリアー）によらず投げる（HC3 にしない）。"""
        for card, index, energy, flips in ((MILTANK, 0, (W,), 2), (BELLOSSOM, 0, (G,), 1)):
            state = board(mon(card, energy, damage=20), opponent=mon(MEWTWO, (PS, PS)))
            target = state.players[1].active
            target.persistent_effects = (AttackBarrier(target.card, 1, TURN - 1, TURN),)
            after = attack(state, index, *(TL,) * flips)
            with self.subTest(card=card):
                self.assertEqual(len(coins_of(state, after)), flips)

    def test_neutral_shield_follows_the_actual_user(self):
        """たねのラプラス自身のやさしいうたは、相手のミュウも受ける。進化したピジョンが受けた記録から同じワザを出す（オウムがえし）と、ミュウの［ニュートラルシールド］で相手への
        とりのぞく効果とねむりは無効（ワザを印刷したラプラスがたねであることでは防護を外さない）。ピジョン自身からとりのぞく効果は残る。"""
        lapras = board(mon(LAPRAS, (W,)), opponent=mon(MEW, (PS,), damage=20))
        by_lapras = attack(lapras, 0)
        self.assertEqual((by_lapras.players[1].active.damage, slept(lapras, by_lapras)), (0, [lapras.players[1].active.pokemon_id]))
        # 前の相手の番: 相手のラプラスがやさしいうたを使い、ピジョンが受ける（ねむりは番の間のコインで「おもて」）
        state = board(mon(PIDGEOTTO, (W, W, W), damage=50), bench=(mon(RATTATA),), opponent=mon(LAPRAS, (W,)), opponent_bench=(mon(MEW, (PS,), damage=20),),
                      current=1, turn=TURN - 1, hand=(GUST,))
        received = attack(state, 0, HD)
        self.assertEqual((received.current_player, received.players[0].active.damage, received.players[0].active.conditions.asleep), (0, 30, False))
        gusted = play(received, GUST)
        gusted = answer(gusted, (pid(gusted, MEW, 1),))
        self.assertEqual(gusted.cards[gusted.players[1].active.card].card_id, MEW)
        after = attack(gusted, 1)
        mew = after.players[1].active
        self.assertEqual([e["copied"] for e in new_events(gusted, after, "copy_attack")], [f"{LAPRAS}#0"])
        self.assertEqual([(e["element"], e["persistent_effect"], e.get("attacker"), e.get("attacker_pokemon_id")) for e in new_events(gusted, after, "effect_prevented")],
                         [(E.HEAL_ELEMENT, "neutral_shield", 0, gusted.players[0].active.pokemon_id), (SLEEP, "neutral_shield", 0, gusted.players[0].active.pokemon_id)])
        self.assertEqual((mew.damage, slept(gusted, after), after.players[0].active.damage), (20, [], 10))
        audited(self, after)
        # オウムがえしの既存の境界: 受けたオーロラウェーブ（水水水）をピジョンのエネルギー（草）で払えなければ MM2（v0.62 のまま）
        state = board(mon(PIDGEOTTO, (G, G, G), damage=20), bench=(mon(RATTATA),), opponent=mon(DEWGONG, (W, W, W)), current=1, turn=TURN - 1)
        rejects(self, attack(state, 1, TL), UseAttack(0, 1), "UNRESOLVED_MIRROR_MOVE_ATTACK_CONDITIONS")
        # 進化したジュゴンのオーロラウェーブ: ダメージも効果も無効なので、こんらんだけを決めるコインは既存の HC3 で止まる（v0.103 のまま）
        rejects(self, with_coin_results(board(mon(DEWGONG, (W, W, W)), opponent=mon(MEW, (PS,))), HD), UseAttack(0, 1), "UNRESOLVED_PREVENTED_EFFECT_COIN")


class FlowerDanceTest(unittest.TestCase):
    def test_counts_own_pokemon_by_current_name(self):
        """フラワーダンス: 自分の場の、今の姿の名前が「キレイハナ」のポケモン（ワザを使ったポケモン・名前の同じ別のカード PRN-043 も）× 30。相手の場・ほかの名前は数えない。"""
        state = board(mon(BELLOSSOM, (G, G, G)), bench=(mon(PRN_BELLOSSOM), mon(NEO_GLOOM), mon(RATTATA)),
                      opponent=mon(H.CHANSEY), opponent_bench=(mon(BELLOSSOM), mon(PRN_BELLOSSOM)))
        after = attack(state, 1)
        damage = new_events(state, after, "damage")[0]
        self.assertEqual(damage["steps"][0], ("1 基本となる計算", 60))
        self.assertEqual(after.players[1].active.damage, 60)
        effect = E.OwnNamedPokemonCountDamage(("キレイハナ",), 30)
        self.assertEqual(effect.damage_profile(state, E.AttackUse(0, state.players[0].active.pokemon_id, AttackKey(BELLOSSOM, 1))).opponent, (60,))
        audited(self, after)

    def test_copied_flower_dance_counts_the_copiers_side(self):
        """相手のワザとして使う（ピクシーのゆびをふる）と、数えるのはワザを使ったポケモンの持ち主の場。キレイハナがいなければ 0（ダメージを与えない）。"""
        state = board(mon(CLEFABLE, (W,)), opponent=mon(BELLOSSOM, (G, G, G)), opponent_bench=(mon(PRN_BELLOSSOM),))
        asked = attack(state, 0)
        self.assertEqual(asked.decision.kind, SELECT_ATTACK)
        after = answer(asked, (1,))
        self.assertEqual(after.players[1].active.damage, 0)
        self.assertTrue(all(e["amount"] == 0 for e in new_events(asked, after, "damage")))


class HighSpeedChargeTest(unittest.TestCase):
    def test_order_and_only_this_attack_is_locked(self):
        """もうとっしん: 相手に 80 → 自分にも 30 → 次の自分の番、このワザだけを使えない（ひとやすみは使える。すべてのワザの禁止ではない）。その番のあとに消える。"""
        state = board(mon(PILOSWINE, (F_, F_, W, W)), opponent=mon(PILOSWINE, (W,)))
        after = attack(state, 1)
        self.assertEqual([(e["player"], e["amount"]) for e in new_events(state, after, "damage")], [(1, 80), (0, 30)])
        lock = [e for e in after.players[0].active.persistent_effects if isinstance(e, CannotUseOwnAttack)]
        self.assertEqual([(e.attack_index, e.target_attack_index, e.active_turn) for e in lock], [(1, 1, TURN + 2)])
        audited(self, after)
        theirs = apply_kernel(after, EndTurn(1))
        self.assertEqual(theirs.current_player, 0)
        rejects(self, theirs, UseAttack(0, 1), "ATTACK_LOCKED", IllegalActionError)
        rested = attack(theirs, 0)
        self.assertEqual(rested.players[0].active.damage, 0)
        later = apply_kernel(rested, EndTurn(1))
        self.assertFalse(any(isinstance(e, CannotUseOwnAttack) for e in later.players[0].active.persistent_effects))
        self.assertEqual([e["amount"] for e in new_events(later, attack(later, 1), "damage")], [80, 30])

    def test_no_lock_when_the_attacker_is_knocked_out_by_its_own_damage(self):
        """自分への 30 で HP 以上なら、使えなくする効果は与えない（ログ persistent_effect_skipped。v0.41 と同じ）。"""
        state = board(mon(PILOSWINE, (F_, F_, W, W), damage=70), opponent=mon(PILOSWINE, (W,)))
        after = attack(state, 1)
        self.assertEqual([e["persistent_effect"] for e in new_events(state, after, "persistent_effect_skipped")], ["cannot_use_own_attack"])

    def test_copying_keeps_the_existing_unsupported_boundary(self):
        """相手のワザとして使う（ゆびをふる）もうとっしんは、番をまたぐ効果をワザの位置で表せないので、既存のエンジンの未対応のまま（選ぶと止める）。ひとやすみは選べる。"""
        state = board(mon(CLEFABLE, (W,)), opponent=mon(PILOSWINE, (F_, F_, W, W)))
        asked = attack(state, 0)
        self.assertEqual((asked.decision.kind, asked.decision.context_value("unsupported_choices")), (SELECT_ATTACK, (1,)))
        before = snap(asked)
        with self.assertRaises(UnsupportedError) as raised:
            answer(asked, (1,))
        self.assertEqual(raised.exception.code, "UNSUPPORTED_COPIED_ATTACK")
        self.assertEqual(snap(asked), before)
        done = answer(asked, (0,))
        self.assertEqual(new_events(asked, done, "attack_heal"), [])  # ピクシーにはのっていない


# ---------------------------------------------------------------- 4.3 節: 決定・再開・先読み・保存


class DecisionTest(unittest.TestCase):
    def test_invalid_answers_change_nothing(self):
        """不正な答え（ほかのポケモン・2 つ）では、状態・乱数・ログ・決定が変わらない（拒否。HALTED にしない）。"""
        asked = attack(board(mon(JIGGLYPUFF, (W,), damage=20), bench=(mon(RATTATA, damage=10),)), 0)
        me, other = asked.players[0].active.pokemon_id, asked.players[0].bench[0].pokemon_id
        for choices in ((other,), (me, me), (me, other)):
            with self.subTest(choices=choices):
                before = snap(asked)
                with self.assertRaises(IllegalActionError):
                    apply_kernel(asked, ResolveDecision(0, asked.decision.id, choices))
                self.assertEqual(snap(asked), before)
        with self.assertRaises(IllegalActionError):
            apply_kernel(asked, ResolveDecision(1, asked.decision.id, ()))
        nectar = attack(board(mon(BELLOSSOM, (G,), damage=20)), 0, HD)
        before = snap(nectar)
        with self.assertRaises(IllegalActionError):
            apply_kernel(nectar, ResolveDecision(0, nectar.decision.id, (nectar.players[1].active.pokemon_id,)))
        self.assertEqual(snap(nectar), before)

    def test_clone_copy_and_pickle_resume_once(self):
        """待っている決定のある状態を clone・deepcopy・pickle しても、同じ答えで同じ結果になり、とりのぞく・コイン・ねむりは 1 度だけ。"""
        asked = attack(board(mon(JIGGLYPUFF, (W,), damage=20)), 0)
        for choices in ((asked.players[0].active.pokemon_id,), ()):
            done = same_answers(self, asked, choices)
            self.assertEqual(len(new_events(asked, done, "attack_heal", "attack_heal_declined")), 1)
        nectar = attack(board(mon(BELLOSSOM, (G,), damage=20), bench=(mon(RATTATA, damage=10),)), 0, HD)
        for target in nectar.decision.options:
            done = same_answers(self, nectar, (target,))
            self.assertEqual(coins_of(nectar, done), [])
            self.assertLessEqual(len(new_events(nectar, done, "attack_heal")), 1)
        self.assertEqual(max(FORMAT_VERSIONS), LATEST_FORMAT)
        self.assertIn(26, FORMAT_VERSIONS)  # この版で形式を上げていない。今の最新の形式は tests/test_catalog_contract.py（docs/testing.md）

    def test_milk_drink_keeps_the_same_coins_across_a_decision(self):
        """ミルクのみの 2 枚のコインは、決定をまたいでも同じ組を使う（投げ直さない）。盤面は直接作った（ナツメのESP はふつう「ナツメのポケモン」につけるので、つけたミルタンクでは
        やり直しを選ぶと既存の ES3 で止まり、やり直さない答えだけが進む）。複製・deepcopy・pickle から同じ答えで続けても、とりのぞくのは 1 度で、数は最初のコインの「おもて」1 枚 × 2。"""
        asked = attack(board(mon(MILTANK, (W,), damage=30, trainers=[(H.SABRINAS_ESP, TURN)])), 0, HD, TL)
        self.assertEqual((asked.decision.kind, asked.decision.context_value("unresolved_code")), ("esp_redo", "UNRESOLVED_ESP_HOLDER_NOT_SABRINAS"))
        done = same_answers(self, asked, ())
        self.assertEqual(coins_of(asked, done), [])
        self.assertEqual(heals(asked, done), [(asked.players[0].active.pokemon_id, 2, 10)])

    def test_copied_optional_heal_asks_the_copier(self):
        """相手のワザとして使う（ゆびをふる）プリンのかいふくは、使ったピクシー自身から取り除くかを、使ったプレイヤーが選ぶ。"""
        state = board(mon(CLEFABLE, (W,), damage=30), opponent=mon(JIGGLYPUFF, (W,)))
        asked = answer(attack(state, 0), (0,))
        self.assertEqual((asked.decision.kind, asked.decision.player, asked.decision.options), (OPTIONAL_HEAL, 0, (state.players[0].active.pokemon_id,)))
        audited(self, asked)
        done = answer(asked, (state.players[0].active.pokemon_id,))
        self.assertEqual(done.players[0].active.damage, 20)
        audited(self, done)

    def test_preflight_methods_agree(self):
        """先読みの方法（derived・derived_full・legacy）は同じ結果（新しい型は v0.13 の止める関数の確かめた型ではないので、legacy でもすべての結果を試す）。上限は変えていない。"""
        self.assertEqual(MAX_BRANCHES, 4096)
        cases = ((mon(MILTANK, (W,), damage=30), 0, (HD, TL)), (mon(LAPRAS, (W,), damage=10), 0, ()), (mon(DEWGONG, (W, W), damage=20, confusion=True), 0, (HD,)),
                 (mon(BELLOSSOM, (G, G, G)), 1, ()), (mon(PILOSWINE, (F_, F_, W, W)), 1, ()), (mon(JIGGLYPUFF, (W,), damage=10), 0, ()))
        for spec, index, flips in cases:
            state = board(spec)
            results = [snap(apply_kernel(with_coin_results(state, *flips), UseAttack(0, index), preflight=mode)) for mode in ("derived", "derived_full", "legacy")]
            with self.subTest(card=spec["card"]):
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0], results[2])


# ---------------------------------------------------------------- 6 章: ログの監査


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v104_problems``）は、エンジンの ``HealCounters``・``OptionalHealSelf`` を読まずにログから組み立てた場とコインで確かめる。エンジンの処理を
    一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py の ``GAMES`` の 3 局。おひるね・ねむる・ミルクのみ・あまいみつ・かいふくが出る組と seed）で、監査がそれを
    見つける（誤らせなければ、同じ局は監査を通る）。"""

    GAMES = ((("M103", "W104"), 0), (("W104", "G104"), 1), (("G104", "M103"), 1))

    @classmethod
    def problems(cls, target, name, fake):
        from tools import existing_effect_games as games

        found = []
        with mock.patch.object(target, name, fake):
            for labels, seed in cls.GAMES:
                state = games.play(labels, seed, keep_state=True).get("state")
                if state is not None:
                    found += log_problems(state)
        return found

    def test_the_unpatched_games_pass_the_audit(self):
        from tools import existing_effect_games as games

        for labels, seed in self.GAMES:
            result = games.play(labels, seed, keep_state=True)
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual((result["outcome"], result["audit"], log_problems(result["state"])), ("game_over", {}, []))

    def test_audit_finds_a_short_full_heal(self):
        """すべてとりのぞくはずが 1 個だけ（おひるね・ねむる）。"""
        original = P.HealCounters.run

        def short(self, run):
            return original(dataclasses.replace(self, every=False, counters=1) if self.every else self, run)

        self.assertTrue([p for p in self.problems(P.HealCounters, "run", short) if "合わない" in p])

    def test_audit_finds_a_missing_sleep(self):
        """とりのぞいたあとの自分のねむりを省いた。"""
        original = P.Status.run

        def skip_self(self, run):
            return False if self.target == P.SELF else original(self, run)

        self.assertTrue([p for p in self.problems(P.Status, "run", skip_self) if "「ねむり」にしていない" in p])

    def test_audit_finds_a_skipped_optional_heal(self):
        """のっているのに、取り除くかの決定を出さない。"""
        self.assertTrue([p for p in self.problems(P.OptionalHealSelf, "run", lambda self, run: False) if "取り除かなかった" in p])


class DocumentTest(unittest.TestCase):
    def test_document_names_the_shared_parts(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("HealCounters", "TargetHeal", "OptionalHealSelf", "OPTIONAL_HEAL", "attack_heal_declined", "HEAL_BOTH_ACTIVE", "every", "per_heads",
                       "CureOwnConditions", "reach", "SelfAttackLock", "CannotUseOwnAttack", "PokemonCountTimes", "HEAL_ONE_IF_DAMAGED_TEXTS", "Incoming",
                       "b84fab2", "73a1690", "GR-2000-P320-RECOVERY", "GR-2000-P309-ATTACK-PROCEDURE", "GR-2000-P321-PREVENTED-ELEMENTS", "T27", "MM2"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
