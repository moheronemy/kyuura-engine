"""v0.111（docs/field-energy-card-counts-v0.111.md）: 場のエネルギーカードの枚数でダメージ・ワザの使用条件が決まるポケモンの 4 枚（ワザ 8。同じデータの 2 組）。ミュウツー（ES1-022・QSG-032）の
「サイコクラッシュ」（相手の場の「超」エネルギーカードの枚数 × 10）と、ナツメのケーシィ（GD6-001・PR1-060）の「シンクロウェーブ」（自分と相手に同じ数のエネルギーカードがついている時だけ使える）。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面。4 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録（GR-2000-P321-ATTACK-DAMAGE・
v0.50 のエネルギーカードの枚数の数え方・v0.40 の相手のワザとして使うときの条件の扱い・v0.58〜v0.88 の色の問い）。英語の欄・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい
読み直し・カードの画像の照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は
tools/existing_effect_games.py の ``--batch v0.111``）。
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
    AttackKey,
    EndTurn,
    PlayTrainer,
    ResolveDecision,
    UseAttack,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import (
    EnergyType,
    load_card_pool,
    pool_from_extract,
    read_extract,
)
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import NINJA_TRICK, SELECT_ATTACK
from kyuura_engine.effects import AttackUse
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.resolution import flow as F
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.preflight import MAX_BRANCHES
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import EnergyRole
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.log_audit import LATEST_FORMAT, _project, log_problems
from tests.release_catalog import cards_after, cards_before
from tests.test_counter_keep_energy_protection_v0_101 import attack
from tests.test_counts_coins_compositions_v0_106 import placed_face_down
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_unown_family_powers_v0_96 import TURN, board, same_answers, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "field-energy-card-counts-v0.111.md"
COMMIT = "73a169063463bbf7bcaa3137d70cbf9721d11534"
PS, W, G, F_, L = H.PSYCHIC, H.WATER, H.GRASS, H.FIGHTING, H.LIGHTNING
MEWTWO, MEWTWO_Q, ABRA_GD, ABRA_PR = "ES1-022", "QSG-032", "GD6-001", "PR1-060"
V0111 = (MEWTWO, MEWTWO_Q, ABRA_GD, ABRA_PR)
V0111_ATTACKS = [AttackKey(card, index) for card in V0111 for index in range(2)]
GROUPS = {MEWTWO: "SC-ES1-022", MEWTWO_Q: "SC-ES1-022", ABRA_GD: "SC-PR1-060", ABRA_PR: "SC-PR1-060"}
ONIX = "PMCG1-054"  # イワーク（HP 90・弱点 草・抵抗力なし）。基本となるダメージがそのまま最終ダメージになる受け手
MACHOP = H.MACHOP  # ワンリキー（HP 50・弱点 超）
RATTATA = H.RATTATA  # コラッタ（抵抗力 超 -30）
RAINBOW, DCE, MIRACLE, BUZZAP = H.RAINBOW_ENERGY, H.DOUBLE_COLORLESS_ENERGY, H.MIRACLE_ENERGY, H.BUZZAP_ELECTRODE
MEGANIUM, BAYLEEF, CHIKORITA = "neo1-014", "neo1-009", "neo1-002"  # メガニウム（［おいしげる］）
GENTLE_VENOMOTH, VENONAT = "neo4-006", "neo4-001"  # やさしいモルフォン（v0.83。使ってから失敗するシンクロウェーブ）
BELOW = {H.CLEFABLE: [H.CLEFAIRY], H.HAUNTER: [H.GASTLY], MEGANIUM: [CHIKORITA, BAYLEEF], GENTLE_VENOMOTH: [VENONAT]}

CRUSH_TEXT = "相手の場のポケモンについている「超」エネルギーカードの数×10のダメージ。"
SYNCHRO_TEXT = "自分と相手に同じ数のエネルギーカードがついている時だけ、このワザは使える。"
# 依頼で示された固定データの日本語（写しの文面と照らす）。(HP, タイプ, 弱点, にげる, 図鑑番号, (名前, 必要なエネルギー, ダメージの目安, 説明), ...)
QUOTED = {
    MEWTWO: (80, "psychic", "psychic", 2, (), ("サイコクラッシュ", ("psychic",), "10×", CRUSH_TEXT), ("ちょうねんりき", ("psychic", "psychic", "colorless"), "50", None)),
    ABRA_PR: (40, "psychic", "psychic", 0, (63,), ("はたく", ("colorless",), "10", None), ("シンクロウェーブ", ("psychic", "colorless"), "40", SYNCHRO_TEXT)),
}
QUOTED[MEWTWO_Q], QUOTED[ABRA_GD] = QUOTED[MEWTWO], QUOTED[ABRA_PR]
CRUSH = E.DamageTimesOpponentFieldEnergyCards(EnergyType.PSYCHIC, 10)
SYNCHRO = E.DamageRequiringEqualEnergyCards()
EXPECTED = {(MEWTWO, 0): CRUSH, (MEWTWO, 1): E.DAMAGE_ONLY, (ABRA_PR, 0): E.DAMAGE_ONLY, (ABRA_PR, 1): SYNCHRO}
EXPECTED[(MEWTWO_Q, 0)], EXPECTED[(MEWTWO_Q, 1)] = EXPECTED[(MEWTWO, 0)], EXPECTED[(MEWTWO, 1)]
EXPECTED[(ABRA_GD, 0)], EXPECTED[(ABRA_GD, 1)] = EXPECTED[(ABRA_PR, 0)], EXPECTED[(ABRA_PR, 1)]


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def answer(state, choices, *coins):
    d = state.decision
    return apply_kernel(with_coin_results(state, *coins) if coins else state, ResolveDecision(d.player, d.id, tuple(choices)))


def crush(opponent, opponent_bench=(), mewtwo=None, **kw):
    """ミュウツー（プレイヤー 0）がサイコクラッシュを使う前と使ったあと。"""
    state = board(mewtwo or mon(MEWTWO, (PS,)), opponent=opponent, opponent_bench=opponent_bench, **kw)
    return state, attack(state, 0)


def base_and_final(before, after):
    """相手の対戦ポケモンへのダメージの (基本となるダメージ（1 段階）, 最終ダメージ)。"""
    (e,) = [e for e in new_events(before, after, "damage") if (e.get("target") or "opponent_active") == "opponent_active"]
    return e["steps"][0][1], e["amount"]


def with_role(state, player, slot, card_id, energy_type=EnergyType.PSYCHIC):
    """場のポケモン（``slot`` は "active" か控えの位置）についている ``card_id`` のカードを、［エネエネ］で ``energy_type`` 2 個になったカードにする（v0.59 の ``EnergyRole``）。"""
    trial = state.clone()
    side = trial.players[player]
    pokemon = side.active if slot == "active" else side.bench[slot]
    uid = next(u for u in pokemon.energy if trial.cards[u].card_id == card_id)
    trial.energy_roles = (*trial.energy_roles, EnergyRole(uid, energy_type, 2, player, trial.turn_number))
    trial.add_event("energy_conversion", player=player, card=uid, pokemon_id=None, target_player=player, target_pokemon_id=pokemon.pokemon_id, target=pokemon.card,
                    energy_type=energy_type.value, units=2)  # 不変条件: 役割はログと対応する
    return trial


# ---------------------------------------------------------------- 1〜3 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_entries_and_printed_texts(self):
        """4 枚・8 つのワザの名前・必要なエネルギー・ダメージの目安・説明と、HP・タイプ・弱点・にげるは依頼の日本語・固定データと同じ。特殊能力は 0。ちょうねんりき・はたくは
        ``DAMAGE_ONLY``（文面・出典を書かない）。"""
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_111"]), V0111)
        for card, (hp, color, weakness, retreat, dex, *attacks) in QUOTED.items():
            definition = pool.definitions[card]
            with self.subTest(card=card):
                self.assertEqual((definition.hp, definition.pokemon_type.value, definition.stage, definition.powers, definition.weakness.value, definition.resistance),
                                 (hp, color, "basic", (), weakness, None))
                self.assertEqual((definition.retreat_cost, definition.evolves_from), (retreat, None))
                self.assertIn(card, pool.playable_ids)
            for index, (name, cost, display, text) in enumerate(attacks):
                printed = definition.attacks[index]
                entry = DEFAULT_EFFECTS.attack_entry(card, index)
                with self.subTest(card=card, index=index):
                    self.assertEqual((printed.name_ja, tuple(t.value for t in printed.cost), printed.damage_display, printed.text_ja), (name, cost, display, text))
                    self.assertEqual(entry.effect, EXPECTED[(card, index)])
                    expected_texts = (text, text, "kyuura data/cards.json") if text is not None else (None, None, None)
                    self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (name, *expected_texts))
                    self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card, printed, definition.attacks))

    def test_same_data_groups_share_values_not_records(self):
        """同じデータの 2 組（SC-ES1-022・SC-PR1-060）は、登録の値だけを共有し（新しい id → 組の名前の id）、id・採用の記録は id ごと。データの欠け（図鑑番号・レベル）は補わない。
        転記元はどれも pcg-search.com。新しい名前はない（ミュウツー・ナツメのケーシィは既存のカードにある）。"""
        self.assertEqual(dict(E.SAME_DATA_CARDS_V0_111), {MEWTWO_Q: MEWTWO, ABRA_GD: ABRA_PR})
        for new, original in E.SAME_DATA_CARDS_V0_111.items():
            for index in range(2):
                with self.subTest(card=new, index=index):
                    self.assertEqual(DEFAULT_EFFECTS.attack_entry(new, index), DEFAULT_EFFECTS.attack_entry(original, index))
        cards = {c["id"]: c for c in read_extract()["cards"]}
        self.assertEqual({card: cards[card]["same_card_group"] for card in V0111}, GROUPS)
        self.assertEqual({card: cards[card]["data_gaps"] for card in V0111},
                         {MEWTWO: ["pokemon.dex", "jp_print.level"], MEWTWO_Q: ["pokemon.dex", "jp_print.level"], ABRA_GD: ["jp_print.level"], ABRA_PR: ["jp_print.level"]})
        self.assertEqual({card: cards[card]["ja_text_source"].split("/")[2] for card in V0111}, dict.fromkeys(V0111, "pcg-search.com"))
        self.assertEqual([cards[card]["pokemon"]["dex"] for card in V0111], [[], [], [63], [63]])
        pool = load_card_pool()
        before = {d.name_ja for c, d in pool.definitions.items() if c in pool.playable_ids and c not in V0111 and d.category == "pokemon"}
        self.assertEqual({pool.definitions[c].name_ja for c in V0111} - before, set())

    def test_programs_and_types(self):
        """サイコクラッシュは相手の対戦ポケモンへの 1 つのダメージの要素（量が場のカードの枚数 × 10）。シンクロウェーブは条件の要素（相手のワザとして使うときの扱いだけ）と目安のダメージ。
        v0.50 のサイコウェーブ（相手の対戦ポケモン 1 匹・色を問わない）・v0.83 のやさしいモルフォン（使ってから失敗する）の型とは別。"""
        self.assertEqual(P.BUILDERS[type(CRUSH)](CRUSH), (P.Damage(P.OPP, P.OpponentFieldEnergyCardsTimes(EnergyType.PSYCHIC, 10)),))
        self.assertEqual(P.BUILDERS[type(SYNCHRO)](SYNCHRO), (P.EqualEnergyCardsRequired(), P.Damage(P.OPP, P.Printed())))
        self.assertEqual((CRUSH.opponent_effect_elements, SYNCHRO.opponent_effect_elements), ((), ()))
        self.assertNotIsInstance(CRUSH, E.DamageTimesDefenderEnergyCards)
        self.assertNotIsInstance(SYNCHRO, E.FailUnlessEqualEnergyCardsDamage)
        self.assertEqual(P.EqualEnergyCardsRequired.phase, P.Phase.NEUTRAL)

    def test_terms_are_bound_to_the_texts(self):
        """型の確かめは全文と目安の数字を照らす: 色・数の違う文面、目安の違うワザ、v0.50・v0.83 の文面を受け付けない。無色・10 の倍数でない数は作れない。"""
        pool = load_card_pool()
        crush_attack, synchro = pool.definitions[MEWTWO].attacks[0], pool.definitions[ABRA_PR].attacks[1]
        self.assertEqual((CRUSH.check(crush_attack), SYNCHRO.check(synchro)), ([], []))
        self.assertTrue(E.DamageTimesOpponentFieldEnergyCards(EnergyType.WATER, 10).check(crush_attack))
        self.assertTrue(E.DamageTimesOpponentFieldEnergyCards(EnergyType.PSYCHIC, 20).check(crush_attack))
        self.assertTrue(CRUSH.check(synchro) and SYNCHRO.check(crush_attack))
        self.assertTrue(SYNCHRO.check(pool.definitions[GENTLE_VENOMOTH].attacks[1]))
        self.assertTrue(CRUSH.check(pool.definitions[H.MEW].attacks[0]))  # v0.50 のサイコウェーブ（相手についているエネルギーカード×10）
        for bad in ((EnergyType.COLORLESS, 10), (EnergyType.PSYCHIC, 15), (EnergyType.PSYCHIC, 0)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                E.DamageTimesOpponentFieldEnergyCards(*bad)

    def test_unregistered_without_the_v0_111_entries(self):
        """今回の登録だけを除くと、ちょうど 4 枚が未対応にもどる（ほかのカードは失われない）。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V0111_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V0111))
        self.assertEqual(set(V0111) & set(cards_before(read_extract(), "0.111")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.110")) & set(cards_before(read_extract(), "0.112")), set(V0111))

    def test_adoption_records(self):
        """4 件の採用の記録（kyuura 73a1690・外部照合なし・kyuura の記録なし）。処理に使う文面は説明のある 2 つのワザの印刷の文面だけ。新しい停止コードはない（色の問いは既存の TE1・RB1・
        BZ2・MEC1・CE3）。"""
        sources = json.loads((ROOT / "kyuura_engine/data/card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine/data/research_links.json").read_text(encoding="utf-8"))
        adopted = links["latest_descriptions"]["adopted_printed_text"]
        texts = {MEWTWO: "attack/0", MEWTWO_Q: "attack/0", ABRA_GD: "attack/1", ABRA_PR: "attack/1"}
        for card in V0111:
            record = sources[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"], record["external_checks"], record["issues"],
                                  record["recorded_on"]), ("kyuura_data", "adopted", COMMIT, [], [], [], "2026-10-27"))
                self.assertEqual(record["play_text"], {texts[card]: "kyuura_printed_text"})
                self.assertIn(GROUPS[card], record["notes"])
        self.assertEqual(sorted(key for key in adopted if key.split("/")[0] in V0111), sorted(f"{card}/{part}" for card, part in texts.items()))
        for key, code in (("transform_energy_count", "TE1"), ("rainbow_energy_type", "RB1"), ("buzzap_energy_type", "BZ2"), ("miracle_energy_type", "MEC1"),
                          ("color_changed_energy_card", "CE3")):
            self.assertEqual(QUESTIONS[key].rulings, (code,))
        self.assertNotIn(E.ENERGY_CARD_COUNTS_DIFFER_CODE, links["stop_codes"])


# ---------------------------------------------------------------- 4 章: サイコクラッシュ


class PsychoCrushTest(unittest.TestCase):
    def test_active_bench_and_both(self):
        """数えるのは相手の場（バトル場と控え）のポケモンについている「超」エネルギーカード。バトル場だけ・控えだけ・両方。枚数 × 10 が基本となるダメージ（目安の 10 を加えない）。"""
        for opponent, bench, expected in ((mon(ONIX, (PS, PS, W)), (mon(RATTATA),), 20), (mon(ONIX, (W,)), (mon(RATTATA, (PS, PS, PS)),), 30),
                                          (mon(ONIX, (PS,)), (mon(RATTATA, (PS, G)), mon(RATTATA, (PS, PS))), 40)):
            before, after = crush(opponent, bench)
            with self.subTest(expected=expected):
                self.assertEqual(base_and_final(before, after), (expected, expected))
                self.assertEqual(after.players[1].active.damage, expected)
                self.assertEqual([p.damage for p in after.players[1].bench], [0] * len(bench))
                audited(self, after)

    def test_other_colors_own_side_and_units_are_not_counted(self):
        """ほかの色・自分の場・手札・トラッシュのカードは数えない。無色2個エネルギーは「超」エネルギーカードではなく、出すエネルギーの個数でも数えない。0 枚なら 0 で、ダメージを与えない。"""
        before, after = crush(mon(ONIX, (W, G, F_, DCE)), (mon(RATTATA, (L,)),), mewtwo=mon(MEWTWO, (PS, PS, PS)), bench=(mon(RATTATA, (PS, PS)),),
                              opponent_hand=(PS, PS))
        self.assertEqual(base_and_final(before, after), (0, 0))
        self.assertEqual(after.players[1].active.damage, 0)
        before, after = crush(mon(ONIX, (DCE, PS)))
        self.assertEqual(base_and_final(before, after), (10, 10))

    def test_weakness_and_resistance_after_the_base(self):
        """弱点・抵抗力は基本となるダメージのあとに（p.321）。弱点 超のワンリキーに 1 枚で 10 → 20、抵抗力 超のコラッタに 4 枚で 40 → 10。0 枚なら弱点でも 0。"""
        before, after = crush(mon(MACHOP, (PS,)))
        self.assertEqual(base_and_final(before, after), (10, 20))
        before, after = crush(mon(RATTATA, (PS, PS)), (mon(RATTATA, (PS, PS)),))
        self.assertEqual(base_and_final(before, after), (40, 10))
        before, after = crush(mon(MACHOP, (F_,)))
        self.assertEqual(base_and_final(before, after), (0, 0))

    def test_bench_protection_does_not_remove_cards_from_the_count(self):
        """数えることは控えへのワザの効果ではないので、控えの「とうめい」（ゴーストの［とうめい］）のポケモンについているカードも数える（コインを投げない）。"""
        before, after = crush(mon(ONIX, (PS,)), (mon(H.HAUNTER, (PS, PS)),))
        self.assertEqual(base_and_final(before, after), (30, 30))
        self.assertEqual(new_events(before, after, "coin_flip"), [])

    def test_color_questions_stop_per_pokemon(self):
        """カードとしての色が決まらないカードは、そのポケモンごとに既存の問いで止める（状態・乱数・ログを変えない）: 控えのレインボーエネルギー（RB1）・バトル場のミラクルエネルギー
        （MEC1）・［エネエネ］で「超」になったカード（BZ2）。エネルギー移動の HC10 の名前は使わない。"""
        rainbow = board(mon(MEWTWO, (PS,)), opponent=mon(ONIX, (W,)), opponent_bench=(mon(RATTATA, (RAINBOW, PS)),))
        rejects(self, rainbow, UseAttack(0, 0), QUESTIONS["rainbow_energy_type"].code)
        miracle = board(mon(MEWTWO, (PS,)), opponent=mon(GENTLE_VENOMOTH, (MIRACLE,)), opponent_bench=())
        rejects(self, miracle, UseAttack(0, 0), QUESTIONS["miracle_energy_type"].code)
        converted = with_role(board(mon(MEWTWO, (PS,)), opponent=mon(ONIX, (BUZZAP,)), opponent_bench=()), 1, "active", BUZZAP)
        rejects(self, converted, UseAttack(0, 0), QUESTIONS["buzzap_energy_type"].code)
        other = with_role(board(mon(MEWTWO, (PS,)), opponent=mon(ONIX, (BUZZAP, PS)), opponent_bench=()), 1, "active", BUZZAP, EnergyType.WATER)
        self.assertEqual(base_and_final(other, attack(other, 0)), (10, 10))  # 「水」になったカードは「超」に当たらない（問わない）

    def test_unrelated_wild_growth_is_not_asked(self):
        """［おいしげる］（「草」2 個ぶん）は「超」エネルギーカードの枚数に関係しないので聞かない。レインボーエネルギーがあれば RB1（カードの色の問い）で止まる。"""
        with mock.patch.object(P, "wild_growth_question", side_effect=AssertionError("おいしげるを聞いた")):
            before, after = crush(mon(ONIX, (PS,)), (mon(MEGANIUM, (G, G)),))
            self.assertEqual(base_and_final(before, after), (10, 10))
            state = board(mon(MEWTWO, (PS,)), opponent=mon(ONIX, (PS,)), opponent_bench=(mon(MEGANIUM, (G, RAINBOW)),))
            rejects(self, state, UseAttack(0, 0), QUESTIONS["rainbow_energy_type"].code)

    def test_void_damage_does_not_ask(self):
        """受ける相手の対戦ポケモンにとってダメージの要素が無効（かたまるの「ダメージを受けない」）なら、量は使われないので色の問いで止めない。"""
        state = board(mon(MEWTWO, (PS,)), opponent=mon(ONIX, (PS,), prevent_damage=TURN - 1), opponent_bench=(mon(RATTATA, (RAINBOW,)),))
        after = attack(state, 0)
        self.assertEqual([e["kind"] for e in new_events(state, after, "damage", "damage_prevented")], ["damage_prevented"])
        audited(self, after)

    def test_energy_burn_guard_and_helpers(self):
        """エナジーバーンで「炎」になったカード（使った番の自分のポケモンだけ）は、数え方で答えが違うので候補に入る（相手の場には起こらないので、処理はエンジンの不具合として止まる）。
        ``damage_profile`` は実際の処理と同じ数え方で、色の決まらないカードは数える・数えないの両方を候補にする。"""
        state = board(mon(MEWTWO, (PS,)), opponent=mon(ONIX, (PS, W)), opponent_bench=(mon(RATTATA, (RAINBOW, PS)),))
        self.assertEqual(E.field_energy_cards_of_type(state, 1, EnergyType.PSYCHIC), 2)
        self.assertEqual(len(E.field_energy_card_ambiguities(state, 1, EnergyType.PSYCHIC)), 1)
        use = AttackUse(0, state.players[0].active.pokemon_id, AttackKey(MEWTWO, 0))
        self.assertEqual(CRUSH.damage_profile(state, use).opponent, (20, 30))
        burned = state.clone()
        pokemon = burned.players[1].active
        burned.energy_burn = ((pokemon.pokemon_id, pokemon.energy[0]),)  # 状態の形（(場のポケモンの番号, カード), ...）
        self.assertIn(pokemon.energy[0], E.field_energy_card_ambiguities(burned, 1, EnergyType.PSYCHIC))


# ---------------------------------------------------------------- 5 章: シンクロウェーブ


class SynchroWaveTest(unittest.TestCase):
    def test_equal_counts_deal_the_printed_damage(self):
        """自分と相手の対戦ポケモンについているエネルギーカードの枚数が同じなら使え、目安の 40（弱点・抵抗力はふつうに）。色・出す個数は見ない（無色2個エネルギーは 1 枚）。"""
        for own, theirs in (((PS, W), (G, F_)), ((PS, DCE), (PS, W)), ((PS, W, W), (DCE, DCE, L))):
            state = board(mon(ABRA_GD, own), opponent=mon(ONIX, theirs))
            after = attack(state, 1)
            with self.subTest(own=own, theirs=theirs):
                self.assertEqual(base_and_final(state, after), (40, 40))
                audited(self, after)

    def test_unequal_counts_are_rejected_before_anything(self):
        """枚数が違えば ``ENERGY_CARD_COUNTS_DIFFER``（通常の不正な操作。研究上の未解決ではない）で、状態・乱数・ログ・番を変えない。こんらんでもコインを投げる前に拒否する。控えの枚数は
        比べない。"""
        for spec in (mon(ABRA_PR, (PS, W)), mon(ABRA_PR, (PS, W), confusion=True)):
            state = board(spec, opponent=mon(ONIX, (PS,)), opponent_bench=(mon(RATTATA, (PS,)),))
            with self.subTest(spec=spec):
                error = rejects(self, state, UseAttack(0, 1), E.ENERGY_CARD_COUNTS_DIFFER_CODE, error=IllegalActionError)
                self.assertIn("2 枚", str(error))
        self.assertFalse(E.ENERGY_CARD_COUNTS_DIFFER_CODE.startswith("UNRESOLVED_"))

    def test_units_and_buzzap_cards_count_as_cards(self):
        """無色2個エネルギーは 1 枚（「無色」2 個でも 2 枚にしない）。［エネエネ］で場でエネルギーカードとしてあつかうカードも 1 枚。"""
        state = board(mon(ABRA_GD, (PS, DCE)), opponent=mon(ONIX, (PS, W, W)))
        rejects(self, state, UseAttack(0, 1), E.ENERGY_CARD_COUNTS_DIFFER_CODE, error=IllegalActionError)
        state = with_role(board(mon(ABRA_GD, (PS, W)), opponent=mon(ONIX, (BUZZAP, W))), 1, "active", BUZZAP)
        self.assertEqual(E.energy_card_counts(state, state.players[0].active), (2, 2))
        self.assertEqual(base_and_final(state, attack(state, 1)), (40, 40))

    def test_both_zero_still_needs_the_energy(self):
        """どちらも 0 枚でも、必要なエネルギー（超無）の確かめが先（条件はそのあと）。"""
        state = board(mon(ABRA_GD), opponent=mon(ONIX))
        rejects(self, state, UseAttack(0, 1), "INSUFFICIENT_ENERGY", error=IllegalActionError)

    def test_old_gentle_venomoth_still_fails_after_use(self):
        """v0.83 のやさしいモルフォンのシンクロウェーブ（「…ついていないとき、このワザは失敗する」）は、変えずに使ってから失敗し、番は進む。"""
        state = board(mon(GENTLE_VENOMOTH, (PS, G, G)), opponent=mon(ONIX, (W,)))
        after = attack(state, 1)
        self.assertEqual([e["kind"] for e in new_events(state, after, "attack", "attack_failed")], ["attack", "attack_failed"])
        self.assertEqual((after.players[1].active.damage, after.turn_number), (0, TURN + 1))


# ---------------------------------------------------------------- 6〜8 章: コピー・うらのカード・決定・保存・先読み


class CopyAndStateTest(unittest.TestCase):
    def test_copied_psycho_crush_counts_the_copiers_opponent(self):
        """ピクシーがゆびをふるでサイコクラッシュを使うと、実際に使ったピクシーの相手（ミュウツーの側）の場を数える（ピクシーの側の「超」エネルギーカードは数えない）。"""
        state = board(mon(H.CLEFABLE, (W,)), bench=(mon(RATTATA, (PS, PS)),), opponent=mon(MEWTWO, (PS, PS)), opponent_bench=(mon(RATTATA, (PS,)),))
        asked = attack(state, 0)
        self.assertEqual((asked.decision.kind, asked.decision.options), (SELECT_ATTACK, (0, 1)))
        done = answer(asked, (0,))
        self.assertEqual(base_and_final(asked, done), (30, 30))
        audited(self, done)

    def test_copied_synchro_wave_follows_the_copier_clause(self):
        """相手のワザとして使うときは、実際に使うポケモンとその相手の対戦ポケモンで比べる。違えば、ピクシー・ピッピ（説明が「使えない」「説明にしたがう」）は選べず、カスミのコダック
        （書かない）は選べるが選ぶと HC9。同じなら選べる。"""
        heads = (CoinSide.HEADS,) * 3  # カスミのコダックのちょうのうりょく（コイン 3 枚がどれも「おもて」なら選ぶ）
        for copier, energy, index, coins in ((H.CLEFABLE, (W,), 0, ()), (H.CLEFAIRY, (W, W, W), 1, ()), (H.MISTYS_PSYDUCK, (PS,), 0, heads)):
            with self.subTest(copier=copier):
                d = attack(board(mon(copier, energy), opponent=mon(ABRA_GD, (PS,) * (len(energy) + 1))), index, *coins).decision  # 1 枚多い
                if copier == H.MISTYS_PSYDUCK:
                    self.assertIn(1, d.context_value("unresolved_choices", ()))
                    self.assertEqual(d.context_value("unresolved_code"), "UNRESOLVED_COPIED_ATTACK")
                else:
                    self.assertNotIn(1, d.options)
                d = attack(board(mon(copier, energy), opponent=mon(ABRA_GD, (PS,) * len(energy))), index, *coins).decision  # 同じ枚数
                self.assertIn(1, d.options)
                self.assertNotIn(1, d.context_value("unresolved_choices", ()))

    def test_ninja_trick_switch_after_declaration_is_not_rechecked(self):
        """条件は宣言のときに確かめる（必要なエネルギーの確認のあと）。相手が変わり身の術で宣言のあとに控え（枚数の違うポケモン）と入れ替えても、比べ直さない（「そのワザのダメージや効果は、
        入れ替えの後でおこる」。宣言はやり直さない。実装上の読み方）。"""
        state = board(mon(H.KOGAS_KOFFING, (G, W)), bench=(mon(ONIX, (W,)),), opponent=mon(ABRA_GD, (PS, W)), opponent_bench=(), hand=(H.KOGAS_NINJA_TRICK,))
        state = apply_kernel(apply_kernel(state, PlayTrainer(0, state.players[0].hand[0])), EndTurn(0))
        asked = attack(state, 1)
        self.assertEqual((asked.decision.kind, asked.decision.player), (NINJA_TRICK, 0))
        onix = state.players[0].bench[0]
        done = answer(asked, asked.decision.options)
        self.assertEqual([(e["pokemon"], e["amount"]) for e in new_events(asked, done, "damage")], [(onix.card, 40)])
        self.assertEqual(new_events(asked, done, "attack"), [])
        audited(self, done)

    def test_face_down_cards_do_not_stop_or_leak(self):
        """相手の控えのうらのカード（マチスの秘策）は、エネルギーカードがつかない（つけるとおもてになる）ので、数えるために名前・定義を読まない（FD1 で止めない・本当のカードによらない）。"""
        results = []
        for hidden in (RATTATA, H.ABRA):
            theirs = board(mon(MEWTWO, (PS,)), bench=(), opponent=mon(ONIX, (PS, PS)), opponent_hand=(H.LT_SURGES_SECRET_PLAN, hidden), opponent_bench=(),
                           current=1, turn=TURN + 1)
            theirs = apply_kernel(placed_face_down(theirs, hidden, player=1), EndTurn(1))
            self.assertTrue(any(theirs.is_face_down(p) for p in theirs.players[1].bench))
            after = attack(theirs, 0)
            results.append(base_and_final(theirs, after))
            self.assertTrue(any(after.is_face_down(p) for p in after.players[1].bench))
        self.assertEqual(results, [(20, 20), (20, 20)])

    def test_decision_after_damage_resumes_the_same(self):
        """サイコクラッシュで相手をきぜつさせたあとの決定（サイドを取る・バトル場に出す）は、clone・deepcopy・pickle から同じ答えで同じ続き。不正な答えは状態・乱数・ログ・決定を変えない。"""
        state = board(mon(MEWTWO, (PS,)), opponent=mon(H.ABRA, (PS, PS)), opponent_bench=(mon(RATTATA, (PS,)), mon(RATTATA)))
        done = attack(state, 0)
        self.assertIsNotNone(done.decision)
        before = snap(done)
        with self.assertRaises(IllegalActionError):
            apply_kernel(done, ResolveDecision(done.decision.player, done.decision.id, (999,)))
        self.assertEqual(snap(done), before)
        resumed = same_answers(self, done, done.decision.options[:done.decision.min_choices])
        audited(self, resumed)

    def test_serialization_and_copies(self):
        """新しい状態の項目はない（形式は 26 のまま）。clone・deepcopy・pickle から同じ結果。"""
        self.assertIn(26, FORMAT_VERSIONS)  # この版で形式を上げていない。今の最新の形式は tests/test_catalog_contract.py（docs/testing.md）
        self.assertEqual(max(FORMAT_VERSIONS), LATEST_FORMAT)
        state = board(mon(MEWTWO, (PS,)), opponent=mon(ONIX, (PS,)), opponent_bench=(mon(RATTATA, (PS, PS)),))
        expected = attack(state, 0)
        for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            self.assertEqual(snap(attack(other, 0)), snap(expected))
        self.assertEqual(state_to_dict(expected, format_version=26), _project(state_to_dict(expected, format_version=max(FORMAT_VERSIONS)), 26))

    def test_preflight_modes_agree(self):
        """先読みは 3 つの方法で同じ結果（v0.13 の止める関数はこれらの盤面で知らない選択・役割がなく、legacy への切りかえを要しない）。上限は変えていない。"""
        self.assertEqual(MAX_BRANCHES, 4096)
        for state, index in ((board(mon(MEWTWO, (PS,)), opponent=mon(ONIX, (PS,)), opponent_bench=(mon(RATTATA, (PS, PS)),)), 0),
                             (board(mon(ABRA_GD, (PS, W)), opponent=mon(ONIX, (PS, PS))), 1)):
            self.assertEqual(F.legacy_unknown_features(state, state.players[0].active), ())
            results = [snap(apply_kernel(state, UseAttack(0, index), preflight=mode)) for mode in ("derived", "derived_full", "legacy")]
            with self.subTest(index=index):
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0], results[2])


# ---------------------------------------------------------------- 9 章: ログの監査と正式な対戦の道具


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v111_problems``）は、エンジンの登録・計算を読まずに、印刷の文面から読んだ色・1 枚あたりの数・条件と、ログから組み立てた場のカードで確かめる。
    エンジンの処理を一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py の局。v0.111 のワザが出る組と開発用の seed）で、監査がそれを見つける。"""

    # 開発用の seed（正式な対戦の seed 0〜3 とは別）のうち、控えにカードのあるサイコクラッシュ・シンクロウェーブ（ゆびをふるでも）が出る局
    GAMES = ((("P111", "B98"), 102), (("P31", "P111"), 104))

    def test_the_unpatched_games_pass_the_audit(self):
        from tools import existing_effect_games as games

        seen, policy = set(), set()
        for labels, seed in self.GAMES:
            result = games.play(labels, seed, keep_state=True)
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual((result["outcome"], result["audit"], log_problems(result["state"])), ("game_over", {}, []))
            seen |= {key for key, value in result["v111"].items() if value}
            policy |= {key for key, value in result["policy"].items() if value and key.startswith("v111_")}
        self.assertTrue({"psycho_crush_damage", "synchro_wave_used", "copied_PR1-060#0"} <= seen, seen)
        self.assertTrue({"v111_psycho_crush_with_bench_cards"} <= policy, policy)
        self.assertNotIn("v111_synchro_wave_declared_unequal", policy)

    def test_found_audit_false_positives_are_fixed(self):
        """直した監査の不足（エンジンの不具合ではない。v0.111 の正式な対戦の 1 回目で見つけた）: P111 対 L85 の seed 3 は、［きせきのかぜ］の場で無色2個エネルギー 1 枚（「無色」1 個）で
        にげるエネルギー 1 を払った正しい「にげる」を 2 個と数えていた。P111 対 R88 の seed 3・R88 対 P111 の seed 0 は、テクスチャーマジックで自分の抵抗力を変えた正しい効果を、最初の種類
        （相手の弱点）とだけ照らしていた。どちらも前の版の組では起こらなかった場面。"""
        from tools import existing_effect_games as games

        seen = []
        for labels, seed in ((("P111", "L85"), 3), (("P111", "R88"), 3), (("R88", "P111"), 0)):
            result = games.play(labels, seed, keep_state=True)
            state = result["state"]
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual((result["outcome"], result["audit"], log_problems(state)), ("game_over", {}, []))
            seen += ["dce_retreat" for e in state.log if e["kind"] == "retreat" and any(state.cards[u].card_id == DCE for u in e["discarded"])]
            seen += ["resistance_change" for e in state.log if e["kind"] == "persistent_effect_added" and e.get("persistent_effect") == "resistance_change"]
        self.assertEqual(set(seen), {"dce_retreat", "resistance_change"})

    def test_tool_knows_the_rejection_and_checks_the_field(self):
        """道具の既知の拒否（``V031_STOPS``）の ENERGY_CARD_COUNTS_DIFFER は、道具が場のカードの枚数を別に数えて違うときだけ認める。"""
        from tools import existing_effect_games as games

        unequal = board(mon(ABRA_GD, (PS, W)), opponent=mon(ONIX, (PS,)))
        equal = board(mon(ABRA_GD, (PS, W)), opponent=mon(ONIX, (PS, PS)))
        stop = games.V031_STOPS[E.ENERGY_CARD_COUNTS_DIFFER_CODE]
        self.assertEqual((stop(unequal, UseAttack(0, 1)), stop(equal, UseAttack(0, 1))), (True, False))
        result = games.play(("P31", "P111"), 104)
        self.assertGreater(result["observed"].get(f"stopped_attack_{E.ENERGY_CARD_COUNTS_DIFFER_CODE}", 0), 0)

    def test_audit_finds_a_missing_bench_count(self):
        """控えのカードを数えなかった（相手の対戦ポケモンだけ）。"""
        from tools import existing_effect_games as games

        def active_only(self, run, flips):
            defender = run.opponent_active()
            return 0 if defender is None else len(E.attached_basic_energy(run.state, defender, self.energy_type)) * self.per

        with mock.patch.object(P.OpponentFieldEnergyCardsTimes, "value", active_only):
            result = games.play(("P111", "B98"), 102, keep_state=True)
        self.assertTrue([p for p in log_problems(result["state"]) if "基本となるダメージ" in p and "基本エネルギーカード" in p])

    def test_audit_finds_a_missing_condition(self):
        """枚数の違うときにも使えた（使うための条件を確かめなかった）。"""
        from tools import existing_effect_games as games

        with mock.patch.object(E.DamageRequiringEqualEnergyCards, "usage_problem", lambda self, state, attacker: None):
            result = games.play(("P31", "P111"), 104, keep_state=True)
        self.assertTrue([p for p in log_problems(result["state"]) if "エネルギーカードの枚数が違うのに" in p])
        self.assertGreater(result["policy"].get("v111_synchro_wave_declared_unequal", 0), 0)


class DocumentTest(unittest.TestCase):
    def test_document_names_the_shared_parts(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("DamageTimesOpponentFieldEnergyCards", "OpponentFieldEnergyCardsTimes", "field_energy_cards_of_type", "field_energy_card_ambiguities",
                       "DamageRequiringEqualEnergyCards", "EqualEnergyCardsRequired", "energy_card_counts", "ENERGY_CARD_COUNTS_DIFFER", "usage_problem", "copy_problem",
                       "DamageTimesDefenderEnergyCards", "FailUnlessEqualEnergyCardsDamage", "attached_energy_cards", "transform_energy_question", "wild_growth_question",
                       "first_void", "TE1", "RB1", "BZ2", "MEC1", "CE3", "HC9", "HC10", "FD1", "SC-ES1-022", "SC-PR1-060", "SAME_DATA_CARDS_V0_111",
                       "Silver_Bible_structured.md", "v111_problems", "v111_uses", "_v111_attack_observe", "46f7c32", "73a1690"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
