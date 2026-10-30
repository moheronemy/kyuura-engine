"""v0.101（docs/counter-keep-energy-protection-v0.101.md）: ソーナンス・アンノーンK の 2 枚（ワザ 2・特殊能力 1）と、1 倍の反撃・エネルギーカードのトラッシュの事前の無効化。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面。2 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録（v0.13 の
「こうらがえし」・v0.45 の「クロスカウンター」の返す効果、v0.82 のエネルギーカードを場からトラッシュする原因と実際に使ったプレイヤー、v0.96 の「アンノーン」の名前のグループ）。
英語版の文面（「(Any other effects still happen.)」など）・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。盤面は
``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.101``）。
"""

from __future__ import annotations

import copy
import dataclasses
import pathlib
import pickle
import unittest
from unittest import mock

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttackKey,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UseAttack,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.deck import deck_problems
from kyuura_engine.effects import PowerKey
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.resolution.programs import BUILDERS, Coin, DiscardOpponentEnergy
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import (
    RETALIATION_RECEIVED,
    RETALIATION_RECEIVED_SCALED_KIND,
    Retaliation,
)
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.log_audit import log_problems
from tests.release_catalog import cards_after, cards_before
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_power_suppression_lasting_locks_v0_92 import mon, uid
from tests.test_sketch_perish_song_history_v0_100 import opponent_turn, settle
from tests.test_unown_family_powers_v0_96 import board, same_answers, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "counter-keep-energy-protection-v0.101.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, P, G, F, L = H.WATER, H.PSYCHIC, H.GRASS, H.FIRE, H.LIGHTNING
WOBBUFFET, UNOWN_K, UNOWN_D = "neo2-031", "neo3-030", "neo2-025"
V0101 = (WOBBUFFET, UNOWN_K)
V0101_ATTACKS = [AttackKey(WOBBUFFET, 0), AttackKey(UNOWN_K, 0)]
V0101_POWERS = [PowerKey(UNOWN_K, 0)]
KP1, KP2, KP3 = "UNRESOLVED_KEEP_PROTECTED_TARGET", "UNRESOLVED_KEEP_VOIDED_DISCARD_COIN", "UNRESOLVED_KEEP_DETACHED_ENERGY_DISCARD"
FC1, EM1, W24 = "UNRESOLVED_STATED_CARDS_SHORT", "UNRESOLVED_ENERGY_REMOVAL_WITHOUT_TARGET", "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT"
COPY_UNSUPPORTED, HC9 = "UNSUPPORTED_COPIED_ATTACK", "UNRESOLVED_COPIED_ATTACK"
# 依頼で示された固定データの日本語（写しの文面と照らす。広い正規化をしない）
COUNTER_QUOTED = ("次の相手の番、このカードが相手のワザによるダメージを受けたとき(それによって、このカードが「きぜつ」しても)、このカードの持ち主はコインを投げる。「おもて」なら、"
                  "このカードが受けたダメージと同じダメージを相手に与える。(ダメージ以外の効果は与えない。)")
KEEP_QUOTED = ("このカードが場にいるかぎり、相手の「ワザ・特殊能力・トレーナーカード」が、自分の場の「アンノーン」についている「エネルギーカード」をトラッシュする効果は、"
               "すべてなくなる。")
PARAS, RATTATA, PIDGEY, CLEFAIRY, SMEARGLE = "PMCG2-003", H.RATTATA, "PMCG1-059", "PMCG1-067", "neo2-052"
GOLDUCK, PSYDUCK = "PMCG3-016", "PMCG3-010"  # はかいこうせん（水水無・20。相手の対戦ポケモンのエネルギーカードを 1 枚選んでトラッシュ）
SURGES_MAGNEMITE = "PMCG5-039"  # はかいでんぱ（雷・10。コインの「おもて」で相手のエネルギーカードを 1 枚トラッシュ）
BLAINES_CHARMANDER = "PMCG6-025"  # メラメラ（炎・10。自分と相手のエネルギーカードを 1 枚ずつトラッシュ）
MISTYS_GOLDUCK, MISTYS_PSYDUCK = "PMCG5-032", "PMCG5-021"  # スーパーデストロイ（超無。コインの「おもて」で相手と相手の控え全員から 1 枚ずつ）
MAGNETON_ES, MAGNEMITE = "ES2-015", "PMCG1-036"  # マイクロウェーブ（雷雷無。選んだポケモンに 20、コインの「おもて」でそのポケモンのエネルギーカードを 1 枚）
DARK_MAGNETON, DARK_MAGNEMITE = "PMCG4-030", "PMCG4-026"  # じりょくせん（雷雷・30。相手の対戦ポケモンの基本エネルギーカードを相手の控えにつけかえる）
HAUNTER, GASTLY = "PMCG3-030", "PMCG3-029"  # ［とうめい］
KOGAS_MUK, KOGAS_GRIMER = "PMCG6-023", "PMCG6-007"  # ［だつりょくえき］
MUK, GRIMER = "PMCG3-007", "PMCG3-003"  # ［かがくへんかガス］
SHINING_GYARADOS = "neo3-023"  # やきつくす（水水炎炎）
ENERGY_REMOVAL, SUPER_ENERGY_REMOVAL, GUST, DEFENDER = "PMCG1-070", "PMCG1-088", "PMCG1-072", "PMCG1-079"
ECOGYM, RECYCLE = "neo1-086", "neo1-096"
ROCKETS_HITMONCHAN = "PMCG5-054"


def attack(state, index=0, *coins, player=None):
    player = state.current_player if player is None else player
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UseAttack(player, index))


def answer(state, choices, *coins):
    d = state.decision
    return apply_kernel(with_coin_results(state, *coins) if coins else state, ResolveDecision(d.player, d.id, tuple(choices)))


def play(state, card_id, player=0):
    return apply_kernel(state, PlayTrainer(player, uid(state, card_id, player)))


def pid(state, card_id, player):
    return next(p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card_id)


def pokemon(state, card_id, player):
    return state.find_pokemon(pid(state, card_id, player))[1]


def kinds(before, after, *names):
    return [e["kind"] for e in new_events(before, after, *names)]


def voided(before, after):
    return new_events(before, after, "energy_discard_voided")


# ---------------------------------------------------------------- 2 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_entries_and_printed_texts(self):
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_101"]), V0101)
        counter = pool.definitions[WOBBUFFET].attacks[0]
        entry = DEFAULT_EFFECTS.attack_entry(WOBBUFFET, 0)
        self.assertEqual((counter.name_ja, counter.text_ja, counter.damage, counter.damage_display), ("カウンター", COUNTER_QUOTED, None, None))
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), ("カウンター", COUNTER_QUOTED, COUNTER_QUOTED, "kyuura data/cards.json"))
        self.assertEqual(entry.effect, E.ReturnReceivedDamageOnHeads(1))
        self.assertIsNone(DEFAULT_EFFECTS.attack_problem(WOBBUFFET, counter, pool.definitions[WOBBUFFET].attacks))
        hidden = pool.definitions[UNOWN_K].attacks[0]
        self.assertEqual((hidden.name_ja, hidden.text_ja, hidden.damage), ("めざめるパワー", None, 10))
        self.assertIs(DEFAULT_EFFECTS.attack_entry(UNOWN_K, 0).effect, E.DAMAGE_ONLY)
        self.assertIsNone(DEFAULT_EFFECTS.attack_entry(UNOWN_K, 0).text_ja)
        power = pool.definitions[UNOWN_K].powers[0]
        keep = DEFAULT_EFFECTS.power_entry(UNOWN_K, 0)
        self.assertEqual((power.name_ja, power.text_ja), ("KEEP[キープ]", KEEP_QUOTED))
        self.assertEqual((keep.name_ja, keep.text_ja, keep.play_text_ja, keep.source), ("KEEP[キープ]", KEEP_QUOTED, KEEP_QUOTED, "kyuura data/cards.json"))
        self.assertEqual(keep.effect, E.VoidOpponentEnergyDiscardOnGroup())
        wobbuffet, unown = pool.definitions[WOBBUFFET], pool.definitions[UNOWN_K]
        self.assertEqual((wobbuffet.stage, wobbuffet.hp, wobbuffet.pokemon_type, wobbuffet.weakness, wobbuffet.resistance, wobbuffet.retreat_cost, wobbuffet.powers),
                         ("basic", 90, E.EnergyType.PSYCHIC, E.EnergyType.PSYCHIC, None, 3, ()))
        self.assertEqual((unown.stage, unown.hp, unown.pokemon_type, unown.weakness, unown.resistance, unown.retreat_cost, unown.name_group),
                         ("basic", 40, E.EnergyType.PSYCHIC, E.EnergyType.PSYCHIC, None, 1, "アンノーン"))
        self.assertEqual([tuple(t.value for t in a.cost) for a in (counter, hidden)], [("psychic",), ("psychic",)])
        for card in V0101:
            self.assertIn(card, pool.playable_ids)

    def test_texts_are_not_normalized(self):
        """カウンターの倍数 1 はカウンターの文面だけ、倍数 2 以上はクロスカウンターの文面だけを受け付ける（文面の検査を外さない）。"""
        pool = load_card_pool()
        counter = pool.definitions[WOBBUFFET].attacks[0]
        cross = pool.definitions[ROCKETS_HITMONCHAN].attacks[0]
        self.assertEqual(E.ReturnReceivedDamageOnHeads(1).check(counter), [])
        self.assertEqual(E.ReturnReceivedDamageOnHeads(2).check(cross), [])
        self.assertNotEqual(E.ReturnReceivedDamageOnHeads(2).check(counter), [])
        self.assertNotEqual(E.ReturnReceivedDamageOnHeads(1).check(cross), [])
        self.assertNotEqual(E.ReturnReceivedDamageOnHeads(1).check(dataclasses.replace(cross, text_ja=E.CROSS_COUNTER_TEXT.format(multiplier=1))), [])
        for changed in (counter.text_ja.replace("同じダメージ", "2倍のダメージ"), counter.text_ja.replace("このカードの持ち主は", ""),
                        counter.text_ja.replace("(ダメージ以外の効果は与えない。)", ""), counter.text_ja.replace("次の相手の番", "次の自分の番")):
            with self.subTest(changed=changed):
                self.assertNotEqual(E.ReturnReceivedDamageOnHeads(1).check(dataclasses.replace(counter, text_ja=changed)), [])
        keep = pool.definitions[UNOWN_K].powers[0]
        self.assertEqual(E.VoidOpponentEnergyDiscardOnGroup().check(keep), [])
        for changed in (keep.text_ja.replace("「ワザ・特殊能力・トレーナーカード」", "「ワザ」"), keep.text_ja.replace("自分の場", "おたがいの場"),
                        keep.text_ja.replace("トラッシュする", "はがす")):
            with self.subTest(changed=changed):
                self.assertNotEqual(E.VoidOpponentEnergyDiscardOnGroup().check(dataclasses.replace(keep, text_ja=changed)), [])

    def test_multiplier_is_a_positive_int(self):
        for bad in (0, -1, True, 1.0, "1"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                E.ReturnReceivedDamageOnHeads(bad)
        self.assertEqual(E.ReturnReceivedDamageOnHeads(1).retaliation_terms(), (RETALIATION_RECEIVED, None, 1, True))
        self.assertEqual(E.ReturnReceivedDamageOnHeads(2).retaliation_terms(), (RETALIATION_RECEIVED, None, 2, True))
        effect = Retaliation(0, 0, 7, 8, 0, None, RETALIATION_RECEIVED, multiplier=1, on_heads=True)
        self.assertEqual((effect.kind, effect.terms(), effect.base_damage(30)), (RETALIATION_RECEIVED_SCALED_KIND, (RETALIATION_RECEIVED, None, 1, True), 30))

    def test_power_type(self):
        keep = E.VoidOpponentEnergyDiscardOnGroup()
        self.assertEqual((keep.declared, keep.location, keep.blocked_by_status, keep.self_excluding, keep.group),
                         (False, E.CONTINUOUS_IN_PLAY, False, False, "アンノーン"))
        self.assertEqual(E.KEEP_CAUSES, frozenset({E.DISCARD_BY_ATTACK, E.DISCARD_BY_POWER, E.DISCARD_BY_TRAINER}))

    def test_unregistered_without_the_v0_101_entries(self):
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V0101_ATTACKS).without_powers(DEFAULT_EFFECTS.id, V0101_POWERS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V0101))
        self.assertEqual(set(V0101) & set(cards_before(read_extract(), "0.101")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.100")) & set(cards_before(read_extract(), "0.102")), set(V0101))

    def test_extract_values(self):
        cards = {c["id"]: c for c in read_extract()["cards"]}
        for card in V0101:
            self.assertNotIn("corrections", cards[card])
            self.assertEqual(cards[card]["data_gaps"], [])
            self.assertEqual(cards[card]["jp_en_differences"], [])
        self.assertIsNone(cards[WOBBUFFET]["pokemon"]["rules_text"])
        self.assertEqual(cards[UNOWN_K]["pokemon"]["rules_text"]["ja"], "「アンノーン」はデッキに4枚までしか入れることができません。")
        self.assertEqual({c: cards[c]["jp_print"]["level"] for c in V0101}, {WOBBUFFET: 46, UNOWN_K: 14})
        self.assertEqual(cards[WOBBUFFET]["ja_text_source"], "https://nazonobasho.com/neo2-031-sonans/")
        self.assertIn("pokemonwiki.com", cards[UNOWN_K]["ja_text_source"])

    def test_unown_deck_limit_counts_k(self):
        """「アンノーン」は文字の違うカードを合わせて 4 枚まで（v0.96 の共通の規定。K も数える）。"""
        pool = load_card_pool()
        base = [P] * 52 + [RATTATA] * 4
        self.assertEqual(deck_problems(base + [UNOWN_K] * 2 + [UNOWN_D] * 2, pool), [])
        self.assertNotEqual(deck_problems(base[:-1] + [UNOWN_K] * 3 + [UNOWN_D] * 2, pool), [])

    def test_codes_and_abbreviations(self):
        self.assertEqual((QUESTIONS["keep_voided_discard_coin"].code, QUESTIONS["keep_voided_discard_coin"].rulings), (KP2, ("KP2",)))
        self.assertEqual((QUESTIONS["keep_detached_energy_discard"].code, QUESTIONS["keep_detached_energy_discard"].rulings), (KP3, ("KP3",)))
        self.assertEqual(E.KEEP_TARGET_CODE, KP1)
        self.assertIn(26, FORMAT_VERSIONS)  # 新しい状態・書き出しの形式は加えない（KEEP は今の場から、カウンターは既存の Retaliation で表す）。今の最新の形式は tests/test_catalog_contract.py（docs/testing.md）


# ---------------------------------------------------------------- 3 章: カウンター


def counter_board(*, damage=0, opponent=None, bench=(RATTATA,), opponent_bench=(RATTATA,), trainers=None, **kw):
    """7 番（プレイヤー 0）にソーナンスがカウンターを使い、8 番（相手）の盤面。"""
    sonans = mon(WOBBUFFET, (P,), damage=damage, **({"trainers": trainers} if trainers else {}))
    state = board(sonans, bench=bench, opponent=opponent or mon(PARAS, (G, G)), opponent_bench=opponent_bench, turn=7, **kw)
    after = attack(state, 0)
    assert (after.turn_number, after.current_player) == (8, 1)
    return state, after


class CounterTest(unittest.TestCase):
    def test_giving_the_effect_flips_no_coin(self):
        state, after = counter_board()
        self.assertEqual(kinds(state, after, "coin_flip", "damage", "retaliation"), [])
        sonans = pokemon(after, WOBBUFFET, 0)
        self.assertEqual(sonans.persistent_effects, (Retaliation(sonans.card, 0, 7, 8, 0, None, RETALIATION_RECEIVED, multiplier=1, on_heads=True),))
        added = new_events(state, after, "persistent_effect_added")
        self.assertEqual([(e["persistent_effect"], e["effect"]) for e in added], [(RETALIATION_RECEIVED_SCALED_KIND, f"{WOBBUFFET}#0")])
        audited(self, after)

    def test_heads_returns_the_received_damage_once(self):
        _, given = counter_board()
        after = attack(given, 0, HD)  # パラスのひっかく 20
        coins = new_events(given, after, "coin_flip")
        self.assertEqual([(c["player"], c["source"], c["effect"], c["result"]) for c in coins], [(0, "attack", f"{WOBBUFFET}#0", "heads")])
        (ret,) = new_events(given, after, "retaliation")
        self.assertEqual((ret["amount"], ret["received_damage"], ret["multiplier"], ret["coin"]), (20, 20, 1, "heads"))
        self.assertEqual(pokemon(after, PARAS, 1).damage, 20)
        audited(self, after)

    def test_tails_returns_nothing(self):
        _, given = counter_board()
        after = attack(given, 0, TL)
        (skipped,) = new_events(given, after, "retaliation_skipped")
        self.assertEqual((skipped["reason"], skipped["received_damage"]), ("coin_tails", 20))
        self.assertEqual(pokemon(after, PARAS, 1).damage, 0)
        audited(self, after)

    def test_no_damage_or_zero_final_damage_does_not_trigger(self):
        def counter_events(before, after):
            return [e["kind"] for e in new_events(before, after, "coin_flip", "retaliation", "retaliation_skipped") if e.get("effect") == f"{WOBBUFFET}#0"]

        _, given = counter_board()
        after = attack(given, 1, HD)  # キノコのほうし（ダメージなし。あとのコインはポケモンチェックのねむり）
        self.assertEqual(counter_events(given, after), [])
        _, guarded = counter_board(trainers=[(DEFENDER, 8)])  # 20 - 20 = 0（最終ダメージ 0 は受けたことにならない）
        after = attack(guarded, 0)
        self.assertEqual(counter_events(guarded, after), [])
        audited(self, after)

    def test_knocked_out_holder_still_returns_the_full_damage(self):
        """残り HP 10 のソーナンスが 20 を受けてきぜつしても、コインを投げ、受けた 20（HP で上限をつけない）を返す。"""
        _, given = counter_board(damage=80)
        after = settle(attack(given, 0, HD))
        (ret,) = new_events(given, after, "retaliation")
        self.assertEqual((ret["amount"], ret["received_damage"]), (20, 20))
        self.assertIn(pokemon(given, WOBBUFFET, 0).card, [e["pokemon"] for e in new_events(given, after, "knock_out")])
        self.assertEqual(pokemon(after, PARAS, 1).damage, 20)

    def test_simultaneous_knock_out_is_w24(self):
        """返すダメージで相手もきぜつしうる（「おもて」の場合）なら、既存の W24 で宣言の前に止める（そろってのきぜつ）。隣: 相手がきぜつしない量なら使える。"""
        _, given = counter_board(damage=80, opponent=mon(PARAS, (G, G), damage=20))
        rejects(self, given, UseAttack(1, 0), W24)
        _, fine = counter_board(damage=80, opponent=mon(PARAS, (G, G), damage=10))
        attack(fine, 0, HD)

    def test_decision_after_the_return_is_not_repeated(self):
        """ポッポのかぜおこし（10・入れ替え。入れ替える控えはソーナンスの持ち主が選ぶ）。コインと返すダメージは決定の前に 1 回だけ。複製・deepcopy・pickle から同じ答えで同じ結果。"""
        _, given = counter_board(opponent=mon(PIDGEY, (W, W)))
        pending = attack(given, 0, HD)
        self.assertIsNotNone(pending.decision)
        self.assertEqual(len(new_events(given, pending, "retaliation")), 1)
        bench = pending.players[0].bench[0].pokemon_id
        after = same_answers(self, pending, (bench,)) if bench in pending.decision.options else None
        if after is None:
            after = answer(pending, (pending.decision.options[0],))
        self.assertEqual(len([e for e in new_events(given, after, "coin_flip") if e["effect"] == f"{WOBBUFFET}#0"]), 1)
        self.assertEqual(len(new_events(given, after, "retaliation")), 1)
        audited(self, after)

    def test_copying_counter_stays_unsupported(self):
        """まねたワザとしてのカウンターは既存の未対応（v0.31 の ``SelfRetaliation.copy_problem``）。内部エラーにしない。ゆびをふる・スケッチ。"""
        state = board(mon(CLEFAIRY, (W, W, W)), opponent=mon(WOBBUFFET, (P,)), turn=7)
        error = rejects(self, state, UseAttack(0, 1), COPY_UNSUPPORTED)
        self.assertIn("番をまたぐ効果", error.message)
        _, given = counter_board(opponent=mon(SMEARGLE, (W, W)))
        error = rejects(self, given, UseAttack(1, 0), COPY_UNSUPPORTED)
        self.assertIn("番をまたぐ効果", error.message)

    def test_cross_counter_is_unchanged(self):
        entry = DEFAULT_EFFECTS.attack_entry(ROCKETS_HITMONCHAN, 0)
        self.assertEqual((entry.effect, entry.source), (E.ReturnReceivedDamageOnHeads(2), "LD-PMCG5-054-ATK0"))


# ---------------------------------------------------------------- 4 章: ［KEEP］


def keep_board(active, *, protected_active=None, opponent_bench=(), bench=(), hand=(), opponent_hand=(), turn=7):
    """プレイヤー 0 が ``active`` で攻撃し、プレイヤー 1 の場にアンノーンK（ベンチ）がいる盤面。"""
    return board(active, bench=bench, hand=hand, opponent=protected_active or mon(UNOWN_D, (P, P)), opponent_bench=(mon(UNOWN_K), *opponent_bench),
                 opponent_hand=opponent_hand, turn=turn)


GOLDUCK_MON = mon(GOLDUCK, (W, W, W), evolved_from=PSYDUCK)


class KeepAttackTest(unittest.TestCase):
    def test_discard_is_voided_and_damage_stays(self):
        state = keep_board(GOLDUCK_MON)
        after = attack(state, 1)
        self.assertIsNone(after.decision)
        d = pokemon(after, UNOWN_D, 1)
        self.assertEqual((d.damage, len(d.energy)), (20, 2))
        (v,) = voided(state, after)
        self.assertEqual((v["player"], v["pokemon_id"], v["cause"], v["by_player"], v["effect"], v["energy"]),
                         (1, d.pokemon_id, "attack", 0, f"{GOLDUCK}#1", tuple(d.energy)))
        self.assertEqual([tuple(x) for x in v["powers"]], [(pid(state, UNOWN_K, 1), f"{UNOWN_K}@power0")])
        self.assertEqual(kinds(state, after, "discard_attached_energy", "energy_returned_to_hand"), [])
        self.assertEqual(after.players[1].discard, state.players[1].discard)
        audited(self, after)

    def test_k_itself_and_bench_unown_are_protected(self):
        state = board(GOLDUCK_MON, opponent=mon(UNOWN_K, (P,)), opponent_bench=(), turn=7)
        after = attack(state, 1)
        self.assertEqual(len(voided(state, after)), 1)
        self.assertEqual(len(pokemon(after, UNOWN_K, 1).energy), 1)

    def test_neighbours_are_not_protected(self):
        """KEEP のない場・相手（攻撃する側）の KEEP・アンノーンでないポケモン・ガスで消えた KEEP は、今までどおり選ばせてトラッシュする。"""
        cases = {
            "KEEP なし": board(GOLDUCK_MON, opponent=mon(UNOWN_D, (P, P)), opponent_bench=(), turn=7),
            "攻撃する側の KEEP": board(GOLDUCK_MON, bench=(mon(UNOWN_K),), opponent=mon(UNOWN_D, (P, P)), opponent_bench=(), turn=7),
            "アンノーンでない": keep_board(GOLDUCK_MON, protected_active=mon(RATTATA, (W,))),
            "かがくへんかガス": keep_board(GOLDUCK_MON, bench=(mon(MUK, evolved_from=GRIMER),)),
        }
        for label, state in cases.items():
            with self.subTest(label):
                pending = attack(state, 1)
                self.assertEqual(pending.decision.kind, "discard_opponent_energy")
                self.assertEqual(voided(state, pending), [])
                after = answer(pending, (pending.decision.options[0],))
                self.assertEqual(len(new_events(state, after, "discard_attached_energy")), 1)
                audited(self, after)

    def test_partial_attack_keeps_the_own_discard(self):
        """メラメラ: 自分のエネルギーカードのトラッシュ（自分の効果）は残り、相手のアンノーンのトラッシュだけがなくなる。"""
        state = keep_board(mon(BLAINES_CHARMANDER, (F, F)))
        after = settle(attack(state, 0))
        self.assertEqual(len(new_events(state, after, "discard_energy")), 1)
        self.assertEqual(len(voided(state, after)), 1)
        self.assertEqual(len(pokemon(after, UNOWN_D, 1).energy), 2)
        audited(self, after)

    def test_coin_only_for_a_voided_discard_is_kp2(self):
        """はかいでんぱ: コインはトラッシュだけを決め、その効果がなくなるので投げるかが決まらない（KP2。宣言の前）。隣: アンノーンでない相手には使える。"""
        state = keep_board(mon(SURGES_MAGNEMITE, (L,)))
        rejects(self, state, UseAttack(0, 0), KP2)
        fine = keep_board(mon(SURGES_MAGNEMITE, (L,)), protected_active=mon(RATTATA, (W,)))
        after = settle(attack(fine, 0, HD))
        self.assertEqual(len(new_events(fine, after, "discard_attached_energy")), 1)

    def test_each_bench_coin_continues_for_unprotected(self):
        """スーパーデストロイ（コインの「おもて」で相手と控え全員から 1 枚ずつ）: 守られないポケモンがいればコインを投げ、守られるアンノーンはなくなる（ログ）。どれも守られるなら KP2。"""
        psy = mon(MISTYS_GOLDUCK, (P, W), evolved_from=MISTYS_PSYDUCK)
        state = keep_board(psy, opponent_bench=(mon(RATTATA, (W,)),))
        pending = attack(state, 1, HD)
        self.assertEqual(len(voided(state, pending)), 1)  # 対戦ポケモンのアンノーンD（ベンチの K はエネルギーなし）
        self.assertEqual(pending.decision.context_value("target"), pid(state, RATTATA, 1))
        after = same_answers(self, pending, (pending.decision.options[0],))
        self.assertEqual(len(new_events(state, after, "discard_attached_energy")), 1)
        self.assertEqual(len(voided(state, after)), 1)
        audited(self, after)
        rejects(self, keep_board(psy), UseAttack(0, 1), KP2)

    def test_chosen_target_coin_is_choose_to_halt(self):
        """マイクロウェーブ（選んだポケモンに 20、コインでそのポケモンのトラッシュ）: 守られるアンノーンを選ぶと KP2、ほかを選ぶのは止めない。"""
        state = keep_board(mon(MAGNETON_ES, (L, L, W), evolved_from=MAGNEMITE), opponent_bench=(mon(RATTATA, (W,)),))
        pending = attack(state, 0)
        d = pending.decision
        self.assertIn(pid(state, UNOWN_D, 1), d.context_value("unresolved_choices", ()))
        rejects(self, pending, lambda s: ResolveDecision(d.player, d.id, (pid(state, UNOWN_D, 1),)), KP2)
        after = settle(answer(pending, (pid(state, RATTATA, 1),), HD))
        self.assertEqual(len(new_events(state, after, "discard_attached_energy")), 1)

    def test_knocked_out_k_still_protects_until_knock_out_processing(self):
        """やきつくす: 控えの K がこのワザの 10 で HP 以上になっても、きぜつの処理の前は場にいるので、ほかのアンノーンへのトラッシュはなくなる（実際の状態から求める）。"""
        state = board(mon(SHINING_GYARADOS, (W, W, F, F)), opponent=mon(GOLDUCK, (W,), evolved_from=PSYDUCK),
                      opponent_bench=(mon(UNOWN_K, (P,), damage=30), mon(UNOWN_D, (P,))), turn=7)
        pending = attack(state, 1, HD)  # 対戦ポケモンに 50、控えに 10 ずつ
        while pending.decision is not None and pending.decision.player == 0 and pending.decision.kind == "discard_energy":
            pending = answer(pending, tuple(pending.decision.options[:pending.decision.min_choices]))
        after = settle(pending)
        protected = {e["pokemon_id"] for e in voided(state, after)}
        self.assertEqual(protected, {pid(state, UNOWN_D, 1)})
        self.assertIn(pokemon(state, UNOWN_K, 1).card, [e["pokemon"] for e in new_events(state, after, "knock_out")])

    def test_two_keeps_void_once(self):
        state = keep_board(GOLDUCK_MON, opponent_bench=(mon(UNOWN_K),))
        after = attack(state, 1)
        (v,) = voided(state, after)
        self.assertEqual(len(v["powers"]), 2)

    def test_copied_attack_uses_the_actual_user(self):
        """スケッチで、前の相手の番の相手のはかいこうせんを使う: 使うのはプレイヤー 0（相手の効果）なので、相手（K の持ち主）のアンノーンへのトラッシュはなくなる。"""
        state = opponent_turn(mon(SMEARGLE, (W, W, W)), GOLDUCK_MON, index=1, hand=(GUST,), opponent_bench=(mon(UNOWN_D, (P,)), mon(UNOWN_K)))
        pending = play(state, GUST)
        state2 = answer(pending, (pid(state, UNOWN_D, 1),))
        after = settle(attack(state2, 0))
        self.assertEqual([e["copied"] for e in new_events(state2, after, "copy_attack")], [f"{GOLDUCK}#1"])
        (v,) = voided(state2, after)
        self.assertEqual((v["by_player"], v["pokemon_id"]), (0, pid(state, UNOWN_D, 1)))
        audited(self, after)


class KeepOtherCausesTest(unittest.TestCase):
    def test_retreat_and_knock_out_are_not_voided(self):
        state = board(mon(UNOWN_D, (P,)), bench=(mon(UNOWN_K),), opponent=mon(RATTATA, (W,)), turn=7)
        d = pokemon(state, UNOWN_D, 0)
        after = apply_kernel(state, Retreat(0, tuple(d.energy), pokemon(state, UNOWN_K, 0).card))
        self.assertEqual(voided(state, after), [])
        self.assertIn(d.energy[0], after.players[0].discard)
        ko = board(mon(RATTATA, (W,)), opponent=mon(UNOWN_D, (P, P), damage=30), opponent_bench=(mon(UNOWN_K),), turn=7)
        after = settle(attack(ko, 0))
        self.assertEqual(voided(ko, after), [])
        self.assertTrue(set(pokemon(ko, UNOWN_D, 1).energy) <= set(after.players[1].discard))

    def test_own_trainer_cost_is_not_voided(self):
        """超エネルギーリムーブの使うための条件（自分のエネルギーカードをはがしてすてる）は自分の効果。自分のアンノーンのカードもトラッシュする。"""
        state = board(mon(UNOWN_D, (P,)), bench=(mon(UNOWN_K),), hand=(SUPER_ENERGY_REMOVAL,), opponent=mon(RATTATA, (W, W)), opponent_bench=(), turn=7)
        pending = play(state, SUPER_ENERGY_REMOVAL)
        own = pokemon(state, UNOWN_D, 0).energy[0]
        nxt = answer(pending, (own,))
        self.assertIn(own, nxt.players[0].discard)
        self.assertEqual(voided(state, nxt), [])


class KeepTrainerTest(unittest.TestCase):
    def test_energy_removal_all_protected_is_kp1_before_use(self):
        state = keep_board(mon(RATTATA), hand=(ENERGY_REMOVAL,))
        rejects(self, state, PlayTrainer(0, uid(state, ENERGY_REMOVAL)), KP1)
        none = board(mon(RATTATA), hand=(ENERGY_REMOVAL,), opponent=mon(UNOWN_D), opponent_bench=(mon(UNOWN_K),), turn=7)
        rejects(self, none, PlayTrainer(0, uid(none, ENERGY_REMOVAL)), EM1)  # エネルギーカードがない（既存の EM1 のまま）

    def test_energy_removal_mixed_is_choose_to_halt(self):
        state = keep_board(mon(RATTATA), hand=(ENERGY_REMOVAL,), opponent_bench=(mon(RATTATA, (W,)),))
        pending = play(state, ENERGY_REMOVAL)
        d = pending.decision
        protected = tuple(pokemon(state, UNOWN_D, 1).energy)
        self.assertEqual((d.context_value("unresolved_choices"), d.context_value("unresolved_code")), (protected, KP1))
        rejects(self, pending, lambda s: ResolveDecision(0, d.id, (protected[0],)), KP1)
        rejects(self, pending, lambda s: ResolveDecision(0, d.id, (pokemon(state, UNOWN_K, 1).card,)), "INVALID_CHOICE", error=IllegalActionError)  # 不正な答え
        target = pokemon(state, RATTATA, 1).energy[0]
        after = answer(pending, (target,))
        self.assertIn(target, after.players[1].discard)
        audited(self, after)

    def test_super_energy_removal_stops_per_pokemon(self):
        state = keep_board(mon(RATTATA, (W,)), hand=(SUPER_ENERGY_REMOVAL,), opponent_bench=(mon(RATTATA, (W, W)),))
        pending = play(state, SUPER_ENERGY_REMOVAL)
        pending = answer(pending, (pokemon(state, RATTATA, 0).energy[0],))
        d = pending.decision
        unown_d, k = pid(state, UNOWN_D, 1), pid(state, UNOWN_K, 1)
        self.assertEqual(set(d.context_value("unresolved_choices")), {unown_d, k})
        detail = {item[0]: item[1] for item in d.context_value("unresolved_detail")}
        self.assertEqual(detail, {unown_d: KP1, k: FC1})
        rejects(self, pending, lambda s: ResolveDecision(0, d.id, (unown_d,)), KP1)
        rejects(self, pending, lambda s: ResolveDecision(0, d.id, (k,)), FC1)
        nxt = answer(pending, (pid(state, RATTATA, 1),))
        after = answer(nxt, tuple(nxt.decision.options))
        self.assertEqual(len(new_events(state, after, "trainer_discard_energy")), 2)
        audited(self, after)
        only = keep_board(mon(RATTATA, (W,)), hand=(SUPER_ENERGY_REMOVAL,))
        rejects(self, only, PlayTrainer(0, uid(only, SUPER_ENERGY_REMOVAL)), KP1)  # 使うための条件のトラッシュの前に止める

    def test_without_keep_the_decision_is_unchanged(self):
        state = board(mon(RATTATA), hand=(ENERGY_REMOVAL,), opponent=mon(UNOWN_D, (P, P)), opponent_bench=(), turn=7)
        pending = play(state, ENERGY_REMOVAL)
        self.assertIsNone(pending.decision.context_value("unresolved_choices"))


class KeepPowerAndMoveTest(unittest.TestCase):
    def test_energy_drain_coin_is_kp2(self):
        """［だつりょくえき］: ダメージを与えたアンノーンに自分の［KEEP］がはたらくと、トラッシュだけを決めるコインを投げるかが決まらない（KP2。宣言の前）。隣: KEEP がなければ投げる。"""
        state = board(mon(UNOWN_D, (P,)), bench=(mon(UNOWN_K),), opponent=mon(KOGAS_MUK, evolved_from=KOGAS_GRIMER), opponent_bench=(), turn=7)
        rejects(self, state, UseAttack(0, 0), KP2)
        plain = board(mon(UNOWN_D, (P,)), opponent=mon(KOGAS_MUK, evolved_from=KOGAS_GRIMER), opponent_bench=(), turn=7)
        after = attack(plain, 0, HD)
        self.assertIn("energy_drain_check", kinds(plain, after))

    def test_moving_energy_is_not_a_discard(self):
        """じりょくせん: 守られるアンノーンからはがして控えにつけるのはトラッシュではない（そのまま動かす）。受けない控え（とうめい）でトラッシュに置く場合だけ KP3。"""
        dark = mon(DARK_MAGNETON, (L, L), evolved_from=DARK_MAGNEMITE)
        state = board(dark, opponent=mon(UNOWN_K, (P,)), opponent_bench=(mon(RATTATA),), turn=7)
        pending = attack(state, 1)
        moved = settle(answer(answer(pending, (pending.decision.options[0],)), (pid(state, RATTATA, 1),)))
        self.assertEqual([e["result"] for e in new_events(state, moved, "move_opponent_energy")], ["attached"])
        self.assertEqual(voided(state, moved), [])
        haunted = board(dark, opponent=mon(UNOWN_K, (P,)), opponent_bench=(mon(HAUNTER, evolved_from=GASTLY),), turn=7)
        rejects(self, haunted, UseAttack(0, 1), KP3)


class KeepReturnTest(unittest.TestCase):
    def test_ecogym_and_recycle_energy(self):
        """守られるアンノーンのリサイクルエネルギーは、トラッシュされないので手札にももどらない。守られないポケモンは今までどおり（エコロジム・リサイクルエネルギー）。"""
        state = keep_board(GOLDUCK_MON, protected_active=mon(UNOWN_D, (RECYCLE, P)), hand=(ECOGYM,), opponent_bench=(mon(RATTATA, (W,)),))
        state = play(state, ECOGYM)
        after = attack(state, 1)
        self.assertEqual(kinds(state, after, "energy_returned_to_hand", "discard_attached_energy"), [])
        self.assertEqual(len(voided(state, after)), 1)
        plain = board(GOLDUCK_MON, hand=(ECOGYM,), opponent=mon(UNOWN_D, (RECYCLE, P)), opponent_bench=(), turn=7)
        plain = play(plain, ECOGYM)
        pending = attack(plain, 1)
        recycle = pokemon(plain, UNOWN_D, 1).energy[0]
        after = answer(pending, (recycle,))
        self.assertIn(recycle, after.players[1].hand)
        self.assertEqual(new_events(plain, after, "energy_returned_to_hand")[0]["card"], recycle)


class SharedCoinTest(unittest.TestCase):
    def test_no_shared_coin_decides_an_opponent_energy_discard(self):
        """登録表のどのワザでも、相手のエネルギーカードのトラッシュの要素を決めるのはその要素のコイン（``local_coin``）だけで、ワザ全体のコイン（ほかの要素も決める）ではない。
        ワザ全体のコインの役割の分類に［KEEP］を加える場面は、今の写しにない。"""
        found = 0
        for key in DEFAULT_EFFECTS.attack_keys():
            effect = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).effect
            build = BUILDERS.get(type(effect))
            if build is None:
                continue
            program = tuple(build(effect))
            discards = [element for element in program if isinstance(element, DiscardOpponentEnergy)]
            if not discards:
                continue
            found += 1
            for coin in (element for element in program if isinstance(element, Coin)):
                self.assertFalse(any(element.coin_dependent(coin.name) for element in discards), key)
        self.assertGreater(found, 5)


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v101_problems``）は、エンジンの ``energy_discard_void`` を読まずにログから組み立てた場で確かめる。エンジンの問い合わせを一時的に誤らせた
    正式な開始からの対戦（tools/existing_effect_games.py の K101 対 W33・seed 0。両方の席）で、監査がそれを見つける。"""

    @staticmethod
    def problems(fake):
        from tools import existing_effect_games as games

        found = []
        with mock.patch.object(E, "energy_discard_void", fake):
            for labels in (("K101", "W33"), ("W33", "K101")):
                found += [problem for problem in log_problems(games.play(labels, 0, keep_state=True)["state"]) if "［KEEP］" in problem]
        return found

    def test_audit_finds_a_missing_void(self):
        """KEEP のはたらく場のアンノーンのエネルギーカードを、相手のワザでトラッシュした（エンジンの問い合わせが何もしない）。"""
        self.assertTrue(self.problems(lambda *a, **k: None))

    def test_audit_finds_a_wrong_void(self):
        """アンノーンでないポケモンへのトラッシュを、KEEP でなくなったとした（エンジンの問い合わせが相手のワザをすべて無効にする）。"""
        original = E.energy_discard_void

        def everything(state, pokemon, *, cause, by_player):
            found = original(state, pokemon, cause=cause, by_player=by_player)
            owner = state.find_pokemon(pokemon.pokemon_id)[0]
            if found is None and cause == E.DISCARD_BY_ATTACK and by_player is not None and by_player != owner:
                return E.EnergyDiscardVoid(owner, pokemon.pokemon_id, ())
            return found

        self.assertTrue(self.problems(everything))


class StateCopyTest(unittest.TestCase):
    def test_snapshots_have_no_new_fields(self):
        state = keep_board(GOLDUCK_MON)
        after = attack(state, 1)
        for other in (after.clone(), copy.deepcopy(after), pickle.loads(pickle.dumps(after))):
            self.assertEqual(snap(other), snap(after))


class DocumentTest(unittest.TestCase):
    def test_document_names_the_codes(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in (KP1, KP2, KP3, "KP1", "KP2", "KP3", "UQ-TARGET-WITHOUT-EFFECT", "UQ-COIN-IN-NULLIFIED-ELEMENT", "energy_discard_void",
                       "ReturnReceivedDamageOnHeads", "c184b35", "73a1690"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
