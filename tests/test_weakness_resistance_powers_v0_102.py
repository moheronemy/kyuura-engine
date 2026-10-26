"""v0.102（docs/weakness-resistance-powers-v0.102.md）: トランセル・バリヤードの 4 枚（ワザ 4・特殊能力 4）と、ダメージの計算で弱点・抵抗力を当てはめるかの共通の問い合わせ。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面。4 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録（p.321 の
計算の順番、v0.57 のスタジアムの 3・4 段階、v0.46 の常にはたらく特殊能力、v0.3c のこんらんのダメージ、v0.37 の JS1、v0.17b の Z9）。英語版の文面・現代のルール・後年の裁定は
持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの
自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.102``）。
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
    EvolvePokemon,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.effects import EnergyType, PowerKey
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.observation import observe
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import MARKER_COLOR, MARKER_CURSE
from tests import helpers as H
from tests.helpers import apply_kernel
from tests.log_audit import log_problems
from tests.release_catalog import cards_after, cards_before
from tests.test_counter_keep_energy_protection_v0_101 import attack, pid, play
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_pokemon_tools_stadiums_v0_81 import attach
from tests.test_power_suppression_lasting_locks_v0_92 import mon
from tests.test_sketch_perish_song_history_v0_100 import settle
from tests.test_unown_family_powers_v0_96 import TURN, board, same_answers, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "weakness-resistance-powers-v0.102.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, P, G, F, L, FT = H.WATER, H.PSYCHIC, H.GRASS, H.FIRE, H.LIGHTNING, H.FIGHTING
METAPOD, METAPOD_QSG, MR_MIME, MR_MIME_QSG = "ES1-003", "QSG-003", "ES1-021", "QSG-030"
V0102 = (METAPOD, METAPOD_QSG, MR_MIME, MR_MIME_QSG)
V0102_ATTACKS = [AttackKey(card, 0) for card in V0102]
V0102_POWERS = [PowerKey(card, 0) for card in V0102]
CATERPIE, CATERPIE_ES1, CATERPIE_NEO = "PMCG1-002", "ES1-002", "neo2-001"
BASE_METAPOD = "PMCG1-003"  # 第1弾のトランセル（特殊能力なし。同じ名前の別のカード）
CHARMANDER, BELLSPROUT, DROWZEE, RATTATA, MACHOP = H.CHARMANDER, H.BELLSPROUT, H.DROWZEE, H.RATTATA, H.MACHOP
ZUBAT = "ES1-008"  # ズバット（草・弱点 超・抵抗力 闘）
MUK, GRIMER = "PMCG3-007", "PMCG3-003"  # ［かがくへんかガス］
DUGTRIO, DIGLETT = H.DUGTRIO, H.DIGLETT  # じしん（自分の控え全員に 10。説明に弱点・抵抗力がない。JS1）
DARK_GYARADOS, MAGIKARP = "PMCG4-025", H.MAGIKARP  # ［ファイナルビーム］（Z9）
QWILFISH = "neo3-015"  # はりせんぼん（「うら」が出るまで。上限なしのコイン）
SANDSHREW_QSG = "QSG-033"  # スピードスター（相手の持っている効果を除く）
WOBBUFFET = "neo2-031"  # カウンター（返す効果）
HITMONCHAN, DODUO, PINPOINT_LENS = H.HITMONCHAN, H.DODUO, "neo4-104"
RESISTANCE_GYM = "PMCG5-091"  # 抵抗力低下ジム
PLUSPOWER = "PMCG1-081"
# 依頼で示された固定データの日本語（写しの文面と照らす。広い正規化をしない）
GREEN_SHIELD_QUOTED = ("このカードが場にいる限り、自分の「草」ポケモンがダメージを受ける時に「弱点」の影響を受けない。このカードが「ねむり・マヒ・こんらん」状態の時、"
                       "この力は消える。")
NEUTRAL_QUOTED = "このカードがベンチにいる限り、お互いの対戦ポケモンは、ダメージを受ける時に、「弱点・抵抗力」の影響を受けない。"
POWDER_QUOTED = "コインを投げて「おもて」なら、相手を「こんらん」状態にする。"
JUGGLING_QUOTED = "コインを4枚投げ、「おもて」の数×10のダメージ。"
METAPOD_MON = {"card": METAPOD, "evolved_from": CATERPIE}
METAPOD_QSG_MON = {"card": METAPOD_QSG, "evolved_from": CATERPIE}
CONFUSION_MODIFIERS = "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS"
JS1 = "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE"


def damages(before, after):
    return new_events(before, after, "damage")


def amounts(state, index=0, *coins):
    """``state`` からワザ ``index`` を使ったときの、ログ ``damage`` の量の並び。"""
    return [e["amount"] for e in damages(state, attack(state, index, *coins))]


def ignored(event):
    """ログの、力で影響を受けなかった弱点・抵抗力（(持つポケモンの番号, PowerKey) の並び）。"""
    return ([tuple(s) for s in event.get("weakness_ignored_by_powers", ())], [tuple(s) for s in event.get("resistance_ignored_by_powers", ())])


def receiving(state, player):
    return E.Receiving(player, state.players[player].active)


# ---------------------------------------------------------------- 2 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_entries_and_printed_texts(self):
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_102"]), V0102)
        for card in (METAPOD, METAPOD_QSG):
            definition = pool.definitions[card]
            (attack_def,), (power,) = definition.attacks, definition.powers
            self.assertEqual((definition.name_ja, definition.stage, definition.evolves_from, definition.hp, definition.pokemon_type, definition.weakness,
                              definition.resistance, definition.retreat_cost),
                             ("トランセル", "stage1", "キャタピー", 70, EnergyType.GRASS, EnergyType.FIRE, None, 2))
            self.assertEqual((attack_def.name_ja, attack_def.text_ja, attack_def.damage, attack_def.damage_modifier, tuple(t.value for t in attack_def.cost)),
                             ("ふしぎなこな", POWDER_QUOTED, 20, None, ("grass", "grass")))
            self.assertEqual((power.name_ja, power.text_ja, power.kind), ("グリーンシールド", GREEN_SHIELD_QUOTED, "pokemon_power"))
            entry, power_entry = DEFAULT_EFFECTS.attack_entry(card, 0), DEFAULT_EFFECTS.power_entry(card, 0)
            self.assertEqual((entry.effect, entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                             (E.ConfuseOnHeads(), "ふしぎなこな", POWDER_QUOTED, POWDER_QUOTED, "kyuura data/cards.json"))
            self.assertEqual((power_entry.effect, power_entry.name_ja, power_entry.text_ja, power_entry.play_text_ja, power_entry.source),
                             (E.IgnoreWeaknessForOwnType(), "グリーンシールド", GREEN_SHIELD_QUOTED, GREEN_SHIELD_QUOTED, "kyuura data/cards.json"))
        for card in (MR_MIME, MR_MIME_QSG):
            definition = pool.definitions[card]
            (attack_def,), (power,) = definition.attacks, definition.powers
            self.assertEqual((definition.name_ja, definition.stage, definition.hp, definition.pokemon_type, definition.weakness, definition.resistance,
                              definition.retreat_cost),
                             ("バリヤード", "basic", 50, EnergyType.PSYCHIC, EnergyType.PSYCHIC, None, 1))
            self.assertEqual((attack_def.name_ja, attack_def.text_ja, attack_def.damage, attack_def.damage_modifier, tuple(t.value for t in attack_def.cost)),
                             ("ジャグリング", JUGGLING_QUOTED, 10, "×", ("psychic", "colorless")))
            self.assertEqual((power.name_ja, power.text_ja, power.kind), ("ニュートラルダメージ", NEUTRAL_QUOTED, "pokemon_power"))
            entry, power_entry = DEFAULT_EFFECTS.attack_entry(card, 0), DEFAULT_EFFECTS.power_entry(card, 0)
            self.assertEqual((entry.effect, entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                             (E.CoinFlipDamage(coins=4, damage_per_heads=10), "ジャグリング", JUGGLING_QUOTED, JUGGLING_QUOTED, "kyuura data/cards.json"))
            self.assertEqual((power_entry.effect, power_entry.name_ja, power_entry.text_ja, power_entry.source),
                             (E.IgnoreWeaknessResistanceForActives(), "ニュートラルダメージ", NEUTRAL_QUOTED, "kyuura data/cards.json"))
        for card in V0102:
            self.assertIn(card, pool.playable_ids)
            definition = pool.definitions[card]
            self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card, definition.attacks[0], definition.attacks))

    def test_same_data_pairs_share_the_registration(self):
        """kyuura の同じカードの組（SC-ES1-003・SC-ES1-021）の 2 組は、日本語の名前・pokemon 欄の対戦の値が同じなので、id ごとに登録し同じ値にまとめる（id は消さない）。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        self.assertEqual(E.SAME_DATA_CARDS_V0_102, {METAPOD_QSG: METAPOD, MR_MIME_QSG: MR_MIME})
        for new, original in E.SAME_DATA_CARDS_V0_102.items():
            self.assertEqual(cards[new]["pokemon"], cards[original]["pokemon"])
            self.assertEqual(cards[new]["name"]["ja"], cards[original]["name"]["ja"])
            self.assertEqual(cards[new]["same_card_group"], cards[original]["same_card_group"])
            self.assertEqual(DEFAULT_EFFECTS.attack_entry(new, 0), DEFAULT_EFFECTS.attack_entry(original, 0))
            self.assertEqual(DEFAULT_EFFECTS.power_entry(new, 0), DEFAULT_EFFECTS.power_entry(original, 0))
        self.assertEqual({cards[c]["same_card_group"] for c in (METAPOD, METAPOD_QSG)}, {"SC-ES1-003"})
        self.assertEqual({cards[c]["same_card_group"] for c in (MR_MIME, MR_MIME_QSG)}, {"SC-ES1-021"})

    def test_attack_types_match_the_printed_texts(self):
        """登録した型の処理と印刷の文面を照らす（型の既存の検査は形とコインの枚数だけなので、4 枚の値を明示する）。ふしぎなこなはダメージの目安 20 → コイン 1 枚 →「おもて」で
        相手をこんらん。ジャグリングはコイン 4 枚の「おもて」の数 × 10。違う枚数・違う量の型は検査が拒否する。"""
        pool = load_card_pool()
        powder = pool.definitions[METAPOD].attacks[0]
        juggling = pool.definitions[MR_MIME].attacks[0]
        self.assertEqual(E.ConfuseOnHeads().check(powder), [])
        self.assertEqual(E.CoinFlipDamage(coins=4, damage_per_heads=10).check(juggling), [])
        self.assertEqual(E.CoinFlipDamage(coins=4, damage_per_heads=10).damage_profile(None, None).opponent, (0, 10, 20, 30, 40))
        self.assertNotEqual(E.CoinFlipDamage(coins=3, damage_per_heads=10).check(juggling), [])
        self.assertNotEqual(E.CoinFlipDamage(coins=4, damage_per_heads=20).check(juggling), [])
        self.assertEqual(E.FUSHIGINAKONA_TEXT, POWDER_QUOTED)
        self.assertEqual(E.JUGGLING_TEXT, JUGGLING_QUOTED)

    def test_power_texts_are_not_normalized(self):
        pool = load_card_pool()
        shield, neutral = pool.definitions[METAPOD].powers[0], pool.definitions[MR_MIME].powers[0]
        self.assertEqual(E.IgnoreWeaknessForOwnType().check(shield), [])
        self.assertEqual(E.IgnoreWeaknessResistanceForActives().check(neutral), [])
        self.assertNotEqual(E.IgnoreWeaknessForOwnType(EnergyType.WATER).check(shield), [])
        for changed in (shield.text_ja.replace("「草」", "「水」"), shield.text_ja.replace("「弱点」", "「弱点・抵抗力」"),
                        shield.text_ja.replace("このカードが「ねむり・マヒ・こんらん」状態の時、この力は消える。", ""), shield.text_ja.replace("自分の", "お互いの")):
            with self.subTest(changed=changed):
                self.assertNotEqual(E.IgnoreWeaknessForOwnType().check(dataclasses.replace(shield, text_ja=changed)), [])
        for changed in (neutral.text_ja.replace("ベンチ", "場"), neutral.text_ja.replace("「弱点・抵抗力」", "「弱点」"), neutral.text_ja.replace("お互いの", "自分の")):
            with self.subTest(changed=changed):
                self.assertNotEqual(E.IgnoreWeaknessResistanceForActives().check(dataclasses.replace(neutral, text_ja=changed)), [])

    def test_power_types(self):
        shield, neutral = E.IgnoreWeaknessForOwnType(), E.IgnoreWeaknessResistanceForActives()
        self.assertEqual((shield.declared, shield.location, shield.blocked_by_status, shield.self_excluding, shield.pokemon_type),
                         (False, E.CONTINUOUS_IN_PLAY, True, False, EnergyType.GRASS))
        self.assertEqual((neutral.declared, neutral.location, neutral.blocked_by_status, neutral.self_excluding), (False, E.CONTINUOUS_BENCH, False, False))
        self.assertIsInstance(shield, E.WeaknessResistancePower)
        self.assertIsInstance(neutral, E.WeaknessResistancePower)

    def test_unregistered_without_the_v0_102_entries(self):
        """今回の登録だけを除くと、ちょうど 4 枚が未対応にもどる（同じデータの組も id ごとに数える）。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V0102_ATTACKS).without_powers(DEFAULT_EFFECTS.id, V0102_POWERS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V0102))
        self.assertEqual(set(V0102) & set(cards_before(read_extract(), "0.102")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.101")) & set(cards_before(read_extract(), "0.103")), set(V0102))

    def test_extract_values_keep_the_gaps(self):
        """図鑑番号・レベルの欠けはほかのカード・名前から補わない（対戦に使う値はある）。日本語の文面は pcg-search.com の転記。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        for card in V0102:
            self.assertEqual(cards[card]["data_gaps"], ["pokemon.dex", "jp_print.level"])
            self.assertEqual(cards[card]["pokemon"]["dex"], [])
            self.assertIsNone(cards[card]["jp_print"]["level"])
            self.assertIn("pcg-search.com", cards[card]["ja_text_source"])
            self.assertNotIn("corrections", cards[card])

    def test_evolves_from_any_caterpie(self):
        """トランセルは「キャタピー」から進化する（商品をまたぐ名前の進化。既存の経路）。"""
        for caterpie in (CATERPIE, CATERPIE_ES1, CATERPIE_NEO):
            for metapod in (METAPOD, METAPOD_QSG):
                with self.subTest(caterpie=caterpie, metapod=metapod):
                    state = board(mon(caterpie, (G,)), hand=[metapod])
                    target = state.players[0].active
                    after = apply_kernel(state, EvolvePokemon(0, state.players[0].hand[0], target.pokemon_id))
                    self.assertEqual(after.cards[after.players[0].active.card].card_id, metapod)
                    audited(self, after)

    def test_no_new_codes_or_format(self):
        self.assertEqual(max(FORMAT_VERSIONS), 26)  # 力は今の場から求める。新しい状態・書き出しの形式は加えない
        self.assertFalse([q for q in QUESTIONS.values() if q.code and ("WEAKNESS_RESISTANCE_POWER" in q.code or "GREEN_SHIELD" in q.code or "NEUTRAL" in q.code)])

    def test_powers_are_not_declared(self):
        state = board(mon(BELLSPROUT), bench=(METAPOD_MON, MR_MIME))
        for card in (METAPOD, MR_MIME):
            with self.subTest(card=card):
                rejects(self, state, UsePokemonPower(0, pid(state, card, 0), 0), "POWER_NOT_DECLARABLE", error=IllegalActionError)


# ---------------------------------------------------------------- 3 章: ［グリーンシールド］


def fire_on(receiver, *, receiver_bench=(), attacker=None, attacker_bench=(), **kw):
    """プレイヤー 0 のヒトカゲ（炎）の「ひっかく」（無・10）を、プレイヤー 1 の ``receiver`` が受ける盤面。"""
    return board(attacker or mon(CHARMANDER, (F,)), bench=attacker_bench, opponent=receiver, opponent_bench=receiver_bench, **kw)


class GreenShieldTest(unittest.TestCase):
    def test_own_grass_active_ignores_weakness(self):
        """マダツボミ（草・弱点 炎）。ベンチのトランセルがいれば 10（いなければ 20）。性質（弱点）は残る。"""
        plain = fire_on(mon(BELLSPROUT))
        self.assertEqual([e["amount"] for e in damages(plain, attack(plain, 0))], [20])
        state = fire_on(mon(BELLSPROUT), receiver_bench=(METAPOD_MON,))
        after = attack(state, 0)
        (damage,) = damages(state, after)
        self.assertEqual((damage["amount"], damage["weakness"], damage["resistance"]), (10, False, False))
        self.assertEqual(ignored(damage), ([(pid(state, METAPOD, 1), f"{METAPOD}@power0")], []))
        self.assertEqual([s[0] for s in damage["steps"]], ["1 基本となる計算"])
        self.assertIs(E.weakness_of(after, after.players[1].active), EnergyType.FIRE)
        self.assertEqual(observe(after, 0)["players"][1]["active"]["weakness"], "fire")
        audited(self, after)

    def test_the_holder_itself_and_the_other_print(self):
        """バトル場のトランセル自身も守る（「自分の「草」ポケモン」）。同じ名前の第1弾のトランセル（力なし）は 20。"""
        state = fire_on(METAPOD_MON)
        self.assertEqual([e["amount"] for e in damages(state, attack(state, 0))], [10])
        base = fire_on({"card": BASE_METAPOD, "evolved_from": CATERPIE})
        self.assertEqual([e["amount"] for e in damages(base, attack(base, 0))], [20])

    def test_resistance_is_kept(self):
        """ズバット（草・弱点 超・抵抗力 闘）: ワンリキー（闘）の 20 は抵抗力で 0 のまま。スリープ（超）の「はたく」10 は弱点を当てはめず 10。"""
        state = board(mon(MACHOP, (FT,)), opponent=mon(ZUBAT), opponent_bench=(METAPOD_MON,))
        (damage,) = damages(state, attack(state, 0))
        self.assertEqual((damage["amount"], damage["resistance"]), (0, True))
        self.assertEqual(ignored(damage), ([], []))
        state = board(mon(DROWZEE, (P,)), opponent=mon(ZUBAT), opponent_bench=(METAPOD_MON,))
        (damage,) = damages(state, attack(state, 0))
        self.assertEqual((damage["amount"], damage["weakness"]), (10, False))

    def test_not_for_the_opponent_or_other_types(self):
        """ワザを使う側のトランセルは相手の草ポケモンを守らない。自分の草以外（スリープ。弱点 超）も守らない。"""
        state = fire_on(mon(BELLSPROUT), attacker_bench=(METAPOD_MON,))
        self.assertEqual([e["amount"] for e in damages(state, attack(state, 0))], [20])
        state = board(mon(DROWZEE, (P,)), opponent=mon(DROWZEE), opponent_bench=(METAPOD_MON,))
        self.assertEqual([e["amount"] for e in damages(state, attack(state, 0))], [20])

    def test_holder_status_removes_the_power_but_receiver_status_does_not(self):
        """バトル場のトランセルがねむり・マヒ・こんらんなら力は消える（20）。受けるマダツボミがねむりでも、ベンチのトランセルの力ははたらく（10）。"""
        for status in ({"sleep": True}, {"paralysis": TURN - 1}, {"confusion": True}):
            with self.subTest(status=status):
                state = fire_on({**METAPOD_MON, **status})
                self.assertEqual([e["amount"] for e in damages(state, attack(state, 0))], [20])
        state = fire_on(mon(BELLSPROUT, sleep=True), receiver_bench=(METAPOD_MON,))
        self.assertEqual([e["amount"] for e in damages(state, attack(state, 0))], [10])

    def test_suppression_and_return(self):
        """ベトベトンの［かがくへんかガス］で消える（20）。同じ場からベトベトンがいなくなれば、問い合わせのたびに今の場から求めるので、もどる（古い印を残さない）。"""
        state = fire_on(mon(BELLSPROUT), receiver_bench=(METAPOD_MON,), attacker_bench=({"card": MUK, "evolved_from": GRIMER},))
        self.assertEqual([e["amount"] for e in damages(state, attack(state, 0))], [20])
        self.assertIs(E.weakness_resistance_ignored(state, receiving(state, 1), EnergyType.GRASS), E.NOT_IGNORED)
        lifted = state.clone()
        lifted.players[0].bench.clear()
        self.assertEqual(E.weakness_resistance_ignored(lifted, receiving(lifted, 1), EnergyType.GRASS).weakness, ((pid(state, METAPOD, 1), f"{METAPOD}@power0"),))

    def test_type_changes_use_the_current_type(self):
        """色マーカーで「草」になったスリープ（弱点 超）は守られ（10）、「炎」になったマダツボミ（弱点 炎）は守られない（20）。"""
        state = board(mon(DROWZEE, (P,)), opponent=mon(DROWZEE, markers=[(MARKER_COLOR, EnergyType.GRASS)]), opponent_bench=(METAPOD_MON,))
        self.assertEqual([e["amount"] for e in damages(state, attack(state, 0))], [10])
        state = fire_on(mon(BELLSPROUT, markers=[(MARKER_COLOR, EnergyType.FIRE)]), receiver_bench=(METAPOD_MON,))
        self.assertEqual([e["amount"] for e in damages(state, attack(state, 0))], [20])

    def test_two_shields_and_one_confused(self):
        """2 匹のトランセル（ES1-003・QSG-003）の力は 1 回だけ（同じ 10）。バトル場の 1 匹がこんらんでも、ベンチのもう 1 匹で守る（残る力だけを書く）。"""
        state = fire_on(mon(BELLSPROUT), receiver_bench=(METAPOD_MON, METAPOD_QSG_MON))
        (damage,) = damages(state, attack(state, 0))
        self.assertEqual(damage["amount"], 10)
        self.assertEqual(sorted(s[0] for s in ignored(damage)[0]), sorted((pid(state, METAPOD, 1), pid(state, METAPOD_QSG, 1))))
        state = fire_on({**METAPOD_MON, "confusion": True}, receiver_bench=(METAPOD_QSG_MON,))
        (damage,) = damages(state, attack(state, 0))
        self.assertEqual((damage["amount"], ignored(damage)[0]), (10, [(pid(state, METAPOD_QSG, 1), f"{METAPOD_QSG}@power0")]))


# ---------------------------------------------------------------- 3 章: ［ニュートラルダメージ］


def psychic_on(receiver, *, receiver_bench=(), attacker_bench=(), attacker=None, **kw):
    """プレイヤー 0 のスリープ（超）の「はたく」（無・10）を、プレイヤー 1 の ``receiver`` が受ける盤面。"""
    return board(attacker or mon(DROWZEE, (P,)), bench=attacker_bench, opponent=receiver, opponent_bench=receiver_bench, **kw)


class NeutralDamageTest(unittest.TestCase):
    def test_weakness_of_either_active(self):
        """スリープ（弱点 超）。相手側のベンチのバリヤードでも、ワザを使う側のベンチのバリヤードでも 10（いなければ 20）。"""
        self.assertEqual(amounts(psychic_on(mon(DROWZEE))), [20])
        for kw in ({"receiver_bench": (MR_MIME,)}, {"attacker_bench": (MR_MIME,)}):
            with self.subTest(kw=kw):
                state = psychic_on(mon(DROWZEE), **kw)
                after = attack(state, 0)
                (damage,) = damages(state, after)
                self.assertEqual((damage["amount"], damage["weakness"]), (10, False))
                self.assertEqual(ignored(damage), ([(pid(state, MR_MIME, 1 if "receiver_bench" in kw else 0), f"{MR_MIME}@power0")], []))
                audited(self, after)

    def test_ignoring_resistance_can_raise_the_damage(self):
        """コラッタ（抵抗力 超 -30）。10 - 30 で 0 のところ、抵抗力を当てはめず 10（量が増える）。"""
        self.assertEqual(amounts(psychic_on(mon(RATTATA))), [0])
        state = psychic_on(mon(RATTATA), attacker_bench=(MR_MIME_QSG,))
        (damage,) = damages(state, attack(state, 0))
        self.assertEqual((damage["amount"], damage["resistance"]), (10, False))
        self.assertEqual(ignored(damage), ([], [(pid(state, MR_MIME_QSG, 0), f"{MR_MIME_QSG}@power0")]))

    def test_active_holder_and_bench_receivers(self):
        """バトル場のバリヤード自身の力ははたらかない（20）。ほかのベンチのバリヤードがあれば 10。控えの受け手には当てはまらない（ダグトリオの「じしん」の自分の控え）。"""
        self.assertEqual(amounts(psychic_on(mon(MR_MIME))), [20])
        self.assertEqual(amounts(psychic_on(mon(MR_MIME), receiver_bench=(MR_MIME_QSG,))), [10])
        state = board(mon(DUGTRIO, (FT,) * 4, evolved_from=DIGLETT), bench=(MR_MIME, RATTATA))
        self.assertIs(E.weakness_resistance_ignored(state, E.Receiving(0, state.players[0].bench[1]), EnergyType.COLORLESS), E.NOT_IGNORED)
        rejects(self, state, UseAttack(0, 1), JS1)  # 控えのコラッタ（弱点 闘）。ベンチのバリヤードがいても JS1 のまま

    def test_leaving_and_promotion_end_the_effect(self):
        """場から離れた・バトル場に出たバリヤードの力は、その時点の場から求める問い合わせで消える（状態に印を残さない）。"""
        state = psychic_on(mon(DROWZEE), receiver_bench=(MR_MIME,))
        self.assertTrue(E.weakness_resistance_ignored(state, receiving(state, 1), EnergyType.PSYCHIC).weakness)
        gone = state.clone()
        gone.players[1].bench.clear()
        self.assertIs(E.weakness_resistance_ignored(gone, receiving(gone, 1), EnergyType.PSYCHIC), E.NOT_IGNORED)
        swapped = state.clone()
        side = swapped.players[1]
        side.active, side.bench[0] = side.bench[0], side.active
        self.assertIs(E.weakness_resistance_ignored(swapped, receiving(swapped, 1), EnergyType.PSYCHIC), E.NOT_IGNORED)

    def test_overlapping_powers_are_listed_once_each(self):
        """草のバトル場に［グリーンシールド］と［ニュートラルダメージ］が両方はたらけば、弱点は 1 回だけ当てはめない（両方の力を書く）。2 匹のバリヤードも同じ。"""
        state = fire_on(mon(BELLSPROUT), receiver_bench=(METAPOD_MON, MR_MIME), attacker_bench=(MR_MIME_QSG,))
        (damage,) = damages(state, attack(state, 0))
        self.assertEqual(damage["amount"], 10)
        self.assertEqual(sorted(s[0] for s in ignored(damage)[0]), sorted((pid(state, METAPOD, 1), pid(state, MR_MIME, 1), pid(state, MR_MIME_QSG, 0))))
        self.assertEqual(ignored(damage)[1], [])  # マダツボミに抵抗力はない（書かない）



# ---------------------------------------------------------------- 4 章: 計算の共通処理


class CalculationTest(unittest.TestCase):
    def test_curse_marker_and_plus_power(self):
        """のろいマーカー（弱点の計算を「×4」）ののったスリープも、ベンチのバリヤードで弱点を当てはめない（10。ログに ×4 を書かない）。プラスパワー（5 段階）はそのあと。"""
        cursed = psychic_on(mon(DROWZEE, markers=[MARKER_CURSE]))
        (damage,) = damages(cursed, attack(cursed, 0))
        self.assertEqual((damage["amount"], damage.get("weakness_multiplier")), (40, 4))
        state = psychic_on(mon(DROWZEE, markers=[MARKER_CURSE]), receiver_bench=(MR_MIME,), attacker=mon(DROWZEE, (P,), trainers=[(PLUSPOWER, TURN)]))
        after = attack(state, 0)
        (damage,) = damages(state, after)
        self.assertEqual((damage["amount"], damage.get("weakness_multiplier"), [s[0] for s in damage["steps"]]), (20, None, ["1 基本となる計算", "5 プラスパワー"]))

    def test_existing_stadium_and_lens_are_not_reapplied(self):
        """抵抗力低下ジム（抵抗力 -30 → -10）でも、ベンチのバリヤードで抵抗力を当てはめない（10）。ピントレンズですでに抵抗力を計算しない計算は、力で計算し直さない（力を書かない）。"""
        state = psychic_on(mon(RATTATA), receiver_bench=(MR_MIME,), hand=[RESISTANCE_GYM])
        gym = play(state, RESISTANCE_GYM)
        self.assertEqual(E.resistance_of(gym, gym.players[1].active), (EnergyType.PSYCHIC, 10))
        (damage,) = damages(gym, attack(gym, 0))
        self.assertEqual((damage["amount"], ignored(damage)[1]), (10, [(pid(state, MR_MIME, 1), f"{MR_MIME}@power0")]))
        lens_board = board(mon(HITMONCHAN, (FT,)), opponent=mon(DODUO), opponent_bench=(MR_MIME,), hand=[PINPOINT_LENS])
        lensed = attach(lens_board, PINPOINT_LENS, lens_board.players[0].active.pokemon_id)
        (damage,) = damages(lensed, attack(lensed, 0))
        self.assertEqual((damage["amount"], damage["ignore_resistance"], ignored(damage)), (20, True, ([], [])))

    def test_stopped_at_step_two_and_effect_excluding_attacks(self):
        """ジャグリングの「おもて」0 枚（2 段階で計算を終える）・スピードスター（相手の持っている効果を除き、弱点・抵抗力を計算しない）には力を書かない。"""
        state = psychic_on(mon(DROWZEE), receiver_bench=(MR_MIME_QSG,), attacker=mon(MR_MIME, (P, P)))
        (damage,) = damages(state, attack(state, 0, TL, TL, TL, TL))
        self.assertEqual((damage["amount"], damage.get("stopped_after_step_2"), ignored(damage)), (0, True, ([], [])))
        state = board(mon(SANDSHREW_QSG, (FT,)), opponent=mon(RATTATA), opponent_bench=(MR_MIME,), bench=(MR_MIME_QSG,))
        (damage,) = damages(state, attack(state, 1))
        self.assertEqual((damage["amount"], damage.get("ignore_defender_effects"), ignored(damage)), (20, True, ([], [])))

    def test_preview_and_actual_use_the_same_answer(self):
        """宣言の前の先読み（``preview_attack_damage``）と実際の処理（``kernel.compute_damage``）が同じ問い合わせを使う。"""
        from kyuura_engine.resolution.kernel import compute_damage

        state = fire_on(mon(BELLSPROUT, damage=20), receiver_bench=(METAPOD_MON,))
        attacker, receiver = state.players[0].active, state.players[1].active
        use = E.AttackUse(0, attacker.pokemon_id, AttackKey(CHARMANDER, 0))
        self.assertEqual(E.preview_attack_damage(state, use, E.OPPONENT_ACTIVE, 10), 10)
        self.assertEqual(compute_damage(state, attacker, receiver, 10, ()).final, 10)
        self.assertEqual(compute_damage(state, attacker, receiver, 10, ()).weakness_ignored_by, ((pid(state, METAPOD, 1), f"{METAPOD}@power0"),))
        with self.assertRaises(TypeError):
            E.calculate_with_stadium(state, 10, E.form_def(state, attacker), E.form_def(state, receiver))  # 受ける個体の文脈は省略できない

    def test_receiving_context_is_explicit(self):
        state = psychic_on(mon(DROWZEE), receiver_bench=(MR_MIME,))
        with self.assertRaises(ValueError):
            E.Receiving(1, state.players[1].active, "everything")
        self.assertIs(E.weakness_resistance_ignored(state, E.Receiving(None, state.players[1].active), EnergyType.PSYCHIC), E.NOT_IGNORED)
        with self.assertRaises(RuntimeError):
            E.weakness_resistance_ignored(state, E.Receiving(0, state.players[1].active), EnergyType.PSYCHIC)
        # 除く範囲: 受けるポケモン自身の力・持ち主の場の力（ワザを使う側のベンチの力は残る）
        both = psychic_on(mon(DROWZEE), receiver_bench=(MR_MIME,), attacker_bench=(MR_MIME_QSG,))
        active = both.players[1].active
        held = E.weakness_resistance_ignored(both, E.Receiving(1, active, E.EXCLUDE_DEFENDER_HELD), EnergyType.PSYCHIC)
        side = E.weakness_resistance_ignored(both, E.Receiving(1, active, E.EXCLUDE_DEFENDER_SIDE), EnergyType.PSYCHIC)
        self.assertEqual(len(held.weakness), 2)
        self.assertEqual(side.weakness, ((pid(both, MR_MIME_QSG, 0), f"{MR_MIME_QSG}@power0"),))
        shield = fire_on(METAPOD_MON)
        self.assertIs(E.weakness_resistance_ignored(shield, E.Receiving(1, shield.players[1].active, E.EXCLUDE_DEFENDER_HELD), EnergyType.GRASS), E.NOT_IGNORED)


# ---------------------------------------------------------------- 4 章: 返す効果・こんらん・JS1・Z9・上限なしのコイン


class OtherPathsTest(unittest.TestCase):
    def test_counter_return_damage(self):
        """ソーナンスのカウンターで返すダメージ（返す効果の枠。ワザのダメージ）も、受けるバトル場のスリープ（弱点 超）にベンチのバリヤードがいれば弱点を当てはめない（10）。"""
        state = board(mon(WOBBUFFET, (P,)), opponent=mon(DROWZEE, (P,)), opponent_bench=(MR_MIME,), turn=7)
        given = attack(state, 0)
        after = attack(given, 0, HD)
        returned = [e for e in damages(given, after) if e.get("retaliation")]
        self.assertEqual([(e["amount"], e["weakness"]) for e in returned], [(10, False)])
        self.assertEqual(ignored(returned[0])[0], [(pid(state, MR_MIME, 1), f"{MR_MIME}@power0")])
        audited(self, after)

    def test_confusion_damage(self):
        """こんらんのダメージ（p.322 で弱点・抵抗力の影響を受ける。力の説明はワザのダメージに限らない）も、ベンチのバリヤードでスリープ（弱点 超）の 20 は 20（なければ 40）。"""
        plain = psychic_on(mon(RATTATA), attacker=mon(DROWZEE, (P,), confusion=True))
        (event,) = new_events(plain, attack(plain, 0, TL), "confusion_damage")
        self.assertEqual(event["amount"], 40)
        state = psychic_on(mon(RATTATA), attacker=mon(DROWZEE, (P,), confusion=True), receiver_bench=(MR_MIME,))
        after = attack(state, 0, TL)
        (event,) = new_events(state, after, "confusion_damage")
        self.assertEqual((event["amount"], event["weakness"], ignored(event)[0]), (20, False, [(pid(state, MR_MIME, 1), f"{MR_MIME}@power0")]))
        audited(self, after)

    def test_confusion_with_curse_no_longer_differs(self):
        """のろいマーカーと自分の弱点が当てはまるこんらんは、コインの前に止める（v0.90）。ベンチのバリヤードで弱点が当てはまらなければ、どちらの読み方でも同じなので止めない（隣の例）。"""
        cursed = mon(DROWZEE, (P,), confusion=True, markers=[MARKER_CURSE])
        rejects(self, psychic_on(mon(RATTATA), attacker=cursed), UseAttack(0, 0), CONFUSION_MODIFIERS)
        state = psychic_on(mon(RATTATA), attacker=cursed, attacker_bench=(MR_MIME,))
        (event,) = new_events(state, attack(state, 0, TL), "confusion_damage")
        self.assertEqual(event["amount"], 20)

    def test_every_preflight_mode_uses_the_same_query(self):
        """宣言の前の確認の方法（``derived``・``derived_full``・比べる方法 ``legacy`` の v0.13 の止める関数）のどれも、同じ問い合わせで答える（古い経路で止める範囲を落とさない・
        広げない）。のろいマーカーのこんらん（スリープの「はたく」。``VERIFIED`` の型）で、力がなければ止め、ベンチのバリヤードがあれば進む。"""
        cursed = mon(DROWZEE, (P,), confusion=True, markers=[MARKER_CURSE])
        for mode in ("derived", "derived_full", "legacy"):
            with self.subTest(mode=mode):
                rejects(self, psychic_on(mon(RATTATA), attacker=cursed), UseAttack(0, 0), CONFUSION_MODIFIERS, preflight=mode)
                state = psychic_on(mon(RATTATA), attacker=cursed, attacker_bench=(MR_MIME,))
                after = apply_kernel(H.with_coin_results(state, TL), UseAttack(0, 0), preflight=mode)
                self.assertEqual([e["amount"] for e in new_events(state, after, "confusion_damage")], [20])

    def test_js1_bench_damage_uses_the_same_query(self):
        """ダグトリオの「じしん」の自分の控えへのダメージ（JS1）。色マーカーで「草」にしたコラッタ（弱点 闘）は、自分の場のトランセルで弱点を当てはめないので、どちらの読み方でも 10
        になり止めない（隣の例）。抵抗力（ズバットの闘 -30）は［グリーンシールド］で変わらないので JS1 のまま。"""
        dugtrio = mon(DUGTRIO, (FT,) * 4, evolved_from=DIGLETT)
        painted = mon(RATTATA, markers=[(MARKER_COLOR, EnergyType.GRASS)])
        rejects(self, board(dugtrio, bench=(painted,)), UseAttack(0, 1), JS1)
        state = board(dugtrio, bench=(painted, METAPOD_MON))
        after = attack(state, 1)
        self.assertEqual([e["amount"] for e in damages(state, after) if e.get("target") == "self_bench"], [10, 10])
        rejects(self, board(dugtrio, bench=(mon(ZUBAT), METAPOD_MON)), UseAttack(0, 1), JS1)

    def test_z9_power_damage_compares_with_the_powers(self):
        """わるいギャラドスの［ファイナルビーム］（説明に弱点・抵抗力のない特殊能力のダメージ。Z9）: 受けるヒトカゲ（弱点 水）にベンチのバリヤードの力がはたらけば、弱点・抵抗力を
        計算する読み方でも同じ量になるので止めない。"""
        effect = DEFAULT_EFFECTS.power_entry(DARK_GYARADOS, 0).effect
        state = board(mon(CHARMANDER, (F,)), opponent=mon(DARK_GYARADOS, (W, W), evolved_from=MAGIKARP))
        gyarados, charmander = state.players[1].active, state.players[0].active
        self.assertEqual(effect.use_problem(state, gyarados, charmander)[0], E.POWER_DAMAGE_WR_CODE)
        for bench in ({"bench": (MR_MIME,)}, {"opponent_bench": (MR_MIME,)}):
            with self.subTest(bench=bench):
                state = board(mon(CHARMANDER, (F,)), opponent=mon(DARK_GYARADOS, (W, W), evolved_from=MAGIKARP), **bench)
                self.assertIsNone(effect.use_problem(state, state.players[1].active, state.players[0].active))
        self.assertEqual(E.weakness_resistance_readings(state, 0, state.players[0].active), ((None, None, 0),))

    def test_unbounded_coins_use_the_actual_calculation(self):
        """ハリーセンの「はりせんぼん」（「うら」が出るまで × 20）: 受けるヒトカゲ（弱点 水・HP 50）に、ベンチのバリヤードで弱点を当てはめない。先読みの組は実際の計算と同じ問い合わせで
        分ける（「おもて」2 枚で 40。力がなければ 80 できぜつ）。"""
        plain = board(mon(QWILFISH, (W, W)), opponent=mon(CHARMANDER))
        self.assertEqual([e["amount"] for e in damages(plain, attack(plain, 1, HD, HD, TL))], [80])
        state = board(mon(QWILFISH, (W, W)), opponent=mon(CHARMANDER), opponent_bench=(MR_MIME,))
        after = attack(state, 1, HD, HD, TL)
        (damage,) = damages(state, after)
        self.assertEqual((damage["amount"], damage["weakness"]), (40, False))
        self.assertEqual(after.players[1].active.damage, 40)
        audited(self, after)


# ---------------------------------------------------------------- 5 章: 決定をまたぐ・保存・監査


class DecisionAndCopyTest(unittest.TestCase):
    def test_knock_out_decision_after_ignored_weakness(self):
        """弱点を当てはめない 10 でマダツボミ（残り HP 10）がきぜつしたあとの決定（サイドを取る）を、複製・deepcopy・pickle から同じ答えで同じ結果にする。量・履歴は重ならない。"""
        state = fire_on(mon(BELLSPROUT, damage=30), receiver_bench=(METAPOD_MON,))
        pending = attack(state, 0)
        self.assertIsNotNone(pending.decision)
        after = same_answers(self, pending, pending.decision.options[:max(1, pending.decision.min_choices)])
        after = settle(after)
        self.assertEqual(len(damages(state, after)), 1)
        self.assertEqual([e["amount"] for e in damages(state, after)], [10])
        audited(self, after)

    def test_snapshots_have_no_new_fields(self):
        state = fire_on(mon(BELLSPROUT), receiver_bench=(METAPOD_MON,))
        after = attack(state, 0)
        for other in (after.clone(), copy.deepcopy(after), pickle.loads(pickle.dumps(after))):
            self.assertEqual(snap(other), snap(after))


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v102_problems``・W15・W16）は、エンジンの ``weakness_resistance_ignored`` を読まずにログから組み立てた場で確かめる。エンジンの問い合わせを
    一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py の F30 対 G102・C33 対 N102。seed 0）で、監査がそれを見つける。"""

    @staticmethod
    def problems(fake):
        from tools import existing_effect_games as games

        found = []
        with mock.patch.object(E, "weakness_resistance_ignored", fake):
            for labels in (("F30", "G102"), ("C33", "N102")):
                found += [problem for problem in log_problems(games.play(labels, 0, keep_state=True)["state"])
                          if "［グリーンシールド］" in problem or "［ニュートラルダメージ］" in problem or "影響を受けなかった力" in problem]
        return found

    def test_audit_finds_a_missing_power(self):
        """はたらく［グリーンシールド］・［ニュートラルダメージ］があるのに、エンジンの問い合わせが何も返さない（弱点・抵抗力を当てはめた）。"""
        found = self.problems(lambda *a, **k: E.NOT_IGNORED)
        self.assertTrue([p for p in found if "［グリーンシールド］" in p])
        self.assertTrue([p for p in found if "抵抗力を当てはめた" in p])

    def test_audit_finds_a_wrong_power(self):
        """はたらく力のない受け手にも、エンジンの問い合わせが弱点・抵抗力の影響を受けないと答える。"""
        def everything(state, receiving, receiver_type):
            return E.IgnoredWeaknessResistance(((999, f"{MR_MIME}@power0"),), ((999, f"{MR_MIME}@power0"),))

        self.assertTrue([p for p in self.problems(everything) if "影響を受けなかった力" in p])

    def test_counter_coin_is_not_a_barrier(self):
        """v0.101 の監査の誤り（v0.102 の対戦で見つけた）: カウンターのはたらくときのコインは、ダメージのあとにコインのあるワザ（スリープの「あやしいひかり」）のコインより先に来てよい。
        固定した v0.101 の木では、この対戦（P40 対 C101・seed 0）で W21 などを誤って見つけていた。"""
        from tools import existing_effect_games as games

        state = games.play(("P40", "C101"), 0, keep_state=True)["state"]
        self.assertTrue([e for e in state.log if e["kind"] == "coin_flip" and e.get("effect") == f"{WOBBUFFET}#0"])
        self.assertEqual(log_problems(state), [])


class DocumentTest(unittest.TestCase):
    def test_document_names_the_shared_query(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("weakness_resistance_ignored", "Receiving", "calculate_with_stadium", "IgnoreWeaknessForOwnType", "IgnoreWeaknessResistanceForActives",
                       "JS1", "Z9", "CC-PMCG1-003-P18", "ead0380", "73a1690"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
