"""v0.112（docs/energy-coins-draw-v0.112.md）: 水エネルギーの個数によるコインとドロー（ドククラゲ SI-016・オムスター PR1-051 の「しょくしゅをつかう」）、どくばり、コインのマヒと自分のワザの
制限（オムスターの「ふしょくえき」）の 2 枚（ワザ 4）。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面。2 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録（p.311・p.312 の効果で引く
ときの規定・v0.35 の「おもて」の数でまとめる先読み・v0.89 のエネルギーの個数の数え方・v0.66 のESP・v0.35 の「あわあわ」・v0.76 の「きあいいっぱつ」の共有コイン・v0.34 の無効の判定）。
ドククラゲのどくばりは日本語の通常のどく（英語の欄のマヒは採らない。kyuura の jp_en_differences）。英語の欄・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・
カードの画像の照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は
tools/existing_effect_games.py の ``--batch v0.112``）。
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
    DEFAULT_EFFECTS,
    AttackKey,
    EndTurn,
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
from kyuura_engine.decisions import ESP_REDO, SELECT_ATTACK
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.resolution import flow as F
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.preflight import MAX_BRANCHES
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import CannotUseOwnAttack
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.log_audit import LATEST_FORMAT, log_problems
from tests.release_catalog import cards_after, cards_before
from tests.test_coin_groups_damage_order_v0_35 import traced
from tests.test_counter_keep_energy_protection_v0_101 import attack
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_type_energy_colors_v0_88 import convert, porygon2
from tests.test_unown_family_powers_v0_96 import TURN, board, same_answers, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "energy-coins-draw-v0.112.md"
COMMIT = "73a169063463bbf7bcaa3137d70cbf9721d11534"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, PS, L, G = H.WATER, H.PSYCHIC, H.LIGHTNING, H.GRASS
TENTACRUEL, OMASTAR = "SI-016", "PR1-051"
V0112 = (TENTACRUEL, OMASTAR)
V0112_ATTACKS = [AttackKey(card, index) for card in V0112 for index in range(2)]
CHANSEY = H.CHANSEY  # ラッキー（HP 120）。ダメージで「きぜつ」しない受け手
DCE, RAINBOW = H.DOUBLE_COLORLESS_ENERGY, H.RAINBOW_ENERGY
MEGANIUM, BAYLEEF, CHIKORITA = "neo1-014", "neo1-009", "neo1-002"
BELOW = {TENTACRUEL: [H.TENTACOOL], OMASTAR: [H.MYSTERIOUS_FOSSIL, H.OMANYTE], H.CLEFABLE: [H.CLEFAIRY], H.MACHAMP: [H.MACHOP, H.MACHOKE],
         MEGANIUM: [CHIKORITA, BAYLEEF]}

GRIP_TEXT = "自分についている「水」エネルギーの数だけコインを投げ、「おもて」の数×2枚のカードを、自分の山札から引く。"
STING_TEXT = "コインを投げて「おもて」なら、相手を「どく」状態にする。"
ACID_TEXT = "コインを投げて「おもて」なら、相手を「マヒ」状態にする。「うら」なら、次の自分の番、このカードはこのワザを使えない。"
# 依頼で示された固定データの日本語。(HP, 段階, 弱点, にげる, 進化元, (名前, 必要なエネルギー, 目安, 説明), ...)
QUOTED = {
    TENTACRUEL: (60, "stage1", "lightning", 1, "メノクラゲ", ("しょくしゅをつかう", ("water",), None, GRIP_TEXT), ("どくばり", ("water", "water"), "20", STING_TEXT)),
    OMASTAR: (80, "stage2", "grass", 2, "オムナイト", ("しょくしゅをつかう", ("water",), None, GRIP_TEXT), ("ふしょくえき", ("water", "water", "water"), "40", ACID_TEXT)),
}
GRIP = E.CoinsPerOwnTypedEnergyDraw(EnergyType.WATER, 2)
ACID = E.DamageParalyzeOnHeadsElseLockSelf()
EXPECTED = {(TENTACRUEL, 0): GRIP, (TENTACRUEL, 1): E.PoisonOnHeads(), (OMASTAR, 0): GRIP, (OMASTAR, 1): ACID}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def answer(state, choices, *coins):
    d = state.decision
    return apply_kernel(with_coin_results(state, *coins) if coins else state, ResolveDecision(d.player, d.id, tuple(choices)))


def flips(before, after, key=None):
    return [e["result"] for e in new_events(before, after, "coin_flip") if e.get("source") == "attack" and (key is None or e.get("effect") == key)]


def drawn(before, after, player=0):
    """そのワザで引いたカードの枚数（ワザを使ったプレイヤーの最初の ``draw``。番の始めに引くカードを数えない）。"""
    found = [len(e["cards"]) for e in new_events(before, after, "draw") if e["player"] == player]
    return found[0] if found else None


def grip(energy, *coins, deck=None, card=TENTACRUEL, **kw):
    state = board(mon(card, energy), opponent=mon(CHANSEY), deck=deck, **kw)
    return state, attack(state, 0, *coins)


def lock_on(pokemon):
    return [e for e in pokemon.persistent_effects if isinstance(e, CannotUseOwnAttack)]


def barrier_turn(own, *, opponent_energy=(PS, PS, PS)):
    """相手（プレイヤー 1）のミュウツー（第1弾）が ``TURN + 1`` 番に「バリアー」を使い、プレイヤー 0 の番（``TURN + 2``）になった盤面（次の相手の番、ワザをうけない）。"""
    state = board(own, opponent=mon(H.MEWTWO, opponent_energy), current=1, turn=TURN + 1)
    asked = attack(state, 1)  # はがしてすてる「超」エネルギーカードを選ぶ決定
    return answer(asked, asked.decision.options[:asked.decision.min_choices])


# ---------------------------------------------------------------- 1〜2 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_entries_and_printed_texts(self):
        """2 枚・4 つのワザの名前・必要なエネルギー・目安・説明と、HP・タイプ・段階・弱点・抵抗力・にげる・進化元は依頼の日本語・固定データと同じ。特殊能力は 0。"""
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_112"]), V0112)
        for card, (hp, stage, weakness, retreat, below, *attacks) in QUOTED.items():
            definition = pool.definitions[card]
            with self.subTest(card=card):
                self.assertEqual((definition.hp, definition.pokemon_type.value, definition.stage, definition.powers, definition.weakness.value, definition.resistance),
                                 (hp, "water", stage, (), weakness, None))
                self.assertEqual((definition.retreat_cost, definition.evolves_from), (retreat, below))
                self.assertIn(card, pool.playable_ids)
            for index, (name, cost, display, text) in enumerate(attacks):
                printed = definition.attacks[index]
                entry = DEFAULT_EFFECTS.attack_entry(card, index)
                with self.subTest(card=card, index=index):
                    self.assertEqual((printed.name_ja, tuple(t.value for t in printed.cost), printed.damage_display, printed.text_ja), (name, cost, display, text))
                    self.assertEqual(entry.effect, EXPECTED[(card, index)])
                    self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (name, text, text, "kyuura data/cards.json"))
                    self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card, printed, definition.attacks))
        self.assertIn(H.TENTACOOL, pool.playable_ids)
        self.assertIn(H.OMANYTE, pool.playable_ids)

    def test_shared_grip_but_not_the_same_card(self):
        """2 枚の「しょくしゅをつかう」は英語の欄を除くワザのデータが同じなので、型・登録の値を共有する。カード全体は HP・段階・もう 1 つのワザが違うので同じデータの組にしない（登録は
        id ごと）。PR1-051 のデータの欠け（図鑑番号・レベル）は補わない。転記元はどちらも pcg-search.com。SI-016 には日英の違い（どくばり）が記録されている。"""
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(TENTACRUEL, 0), DEFAULT_EFFECTS.attack_entry(OMASTAR, 0))
        self.assertNotEqual(DEFAULT_EFFECTS.attack_entry(TENTACRUEL, 1), DEFAULT_EFFECTS.attack_entry(OMASTAR, 1))
        cards = {c["id"]: c for c in read_extract()["cards"]}
        grips = [{k: v for k, v in cards[card]["pokemon"]["attacks"][0].items()} for card in V0112]
        for attack_data in grips:
            attack_data["name"] = attack_data["name"]["ja"]
            attack_data["text"] = attack_data["text"]["ja"]
        self.assertEqual(grips[0], grips[1])
        self.assertEqual({card: (cards[card]["same_card_group"], cards[card]["data_gaps"]) for card in V0112},
                         {TENTACRUEL: (None, []), OMASTAR: (None, ["pokemon.dex", "jp_print.level"])})
        self.assertEqual({card: cards[card]["ja_text_source"].split("/")[2] for card in V0112}, dict.fromkeys(V0112, "pcg-search.com"))
        differences = cards[TENTACRUEL]["jp_en_differences"]
        self.assertEqual([d["summary"] for d in differences], ["ワザ どくばり（Poison Sting）の特殊状態"])
        self.assertIn("Paralyzed", cards[TENTACRUEL]["pokemon"]["attacks"][1]["text"]["en"])

    def test_programs_and_types(self):
        """しょくしゅをつかうは自分の「水」エネルギーの個数のワザ全体のコイン → その「おもて」の数 × 2 枚を引く。ふしょくえきはダメージ → 1 枚のワザ全体のコイン → 「おもて」でマヒ・
        「うら」で自分のワザの制限。どくばりは既存の ``PoisonOnHeads``（ダメージ → この要素のコインの「おもて」でどく）。"""
        self.assertEqual(P.BUILDERS[type(GRIP)](GRIP), (P.Coin("coin", per_own_typed=EnergyType.WATER), P.Draw(heads_of="coin", per_heads=2)))
        self.assertEqual(P.BUILDERS[type(ACID)](ACID), (P.Damage(P.OPP, P.Printed()), P.Coin("coin"),
                                                        P.Status(P.PARALYSIS, gate=("coin", P.HEADS), reparalysis_check=True),
                                                        P.SelfAttackLock(local_coin=None, gate=("coin", P.TAILS))))
        self.assertEqual(P.BUILDERS[E.PoisonOnHeads](E.PoisonOnHeads()), (P.Damage(P.OPP, P.Printed()), P.Status(P.POISON, local_coin=P.HEADS)))
        self.assertEqual((GRIP.opponent_effect_elements, ACID.opponent_effect_elements), ((), (P.PARALYSIS,)))
        self.assertEqual(ACID.attack_lock_terms(), (CannotUseOwnAttack, None))
        draw = P.Draw(heads_of="coin", per_heads=2)
        self.assertEqual((draw.coin_dependent("coin"), draw.coin_receiver(), P.Draw.reads_deck_order), (True, None, True))
        self.assertIsNone(P.SelfAttackLock(local_coin=None, gate=("coin", P.TAILS)).coin_receiver())

    def test_terms_are_bound_to_the_texts(self):
        """新しい型の確かめは色・1 枚あたりの数・ダメージなし・全文（しょくしゅをつかう）、面・マヒ・期間・対象のワザ・全文（ふしょくえき）を結び付ける。取り違えた登録は拒否する。
        既存の ``ParalyzeOnHeads``・``PoisonOnHeads``・``DamageThenParalyzeOrSelfDamage`` の確かめは形だけなので、登録・動作はテストで照らす（意味の証明にしない）。"""
        pool = load_card_pool()
        grip_attack, sting, acid = pool.definitions[TENTACRUEL].attacks[0], pool.definitions[TENTACRUEL].attacks[1], pool.definitions[OMASTAR].attacks[1]
        self.assertEqual((GRIP.check(grip_attack), ACID.check(acid)), ([], []))
        for wrong in (E.CoinsPerOwnTypedEnergyDraw(EnergyType.GRASS, 2), E.CoinsPerOwnTypedEnergyDraw(EnergyType.WATER, 1), E.DrawOnHeads(2)):
            with self.subTest(wrong=wrong):
                self.assertTrue(wrong.check(grip_attack))
        self.assertTrue(GRIP.check(sting) and ACID.check(sting) and ACID.check(grip_attack))
        self.assertEqual((E.ParalyzeOnHeads().check(sting), E.PoisonOnHeads().check(acid), E.DamageThenParalyzeOrSelfDamage(10).check(acid)), ([], [], []))
        for bad in ((EnergyType.COLORLESS, 2), (EnergyType.WATER, 0)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                E.CoinsPerOwnTypedEnergyDraw(*bad)
        for bad in (lambda: P.Coin("c", per_attached=W, per_own_typed=EnergyType.WATER), lambda: P.Draw(), lambda: P.Draw(2, heads_of="coin"),
                    lambda: P.Draw(heads_of="coin", per_heads=0), lambda: P.Draw(1, per_heads=2)):
            with self.assertRaises(ValueError):
                bad()

    def test_unregistered_without_the_v0_112_entries(self):
        """今回の登録だけを除くと、ちょうど 2 枚が未対応にもどる（ほかのカードは失われない）。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V0112_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V0112))
        self.assertEqual(set(V0112) & set(cards_before(read_extract(), "0.112")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.111")) & set(cards_before(read_extract(), "0.113")), set(V0112))

    def test_adoption_records(self):
        """2 件の採用の記録（kyuura 73a1690・外部照合なし・kyuura の記録なし）。処理に使う文面は 4 つのワザの印刷の文面。新しい停止コードはない。"""
        sources = json.loads((ROOT / "kyuura_engine/data/card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine/data/research_links.json").read_text(encoding="utf-8"))
        for card in V0112:
            record = sources[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"], record["external_checks"], record["issues"],
                                  record["recorded_on"]), ("kyuura_data", "adopted", COMMIT, [], [], [], "2026-10-27"))
                self.assertEqual(record["play_text"], {"attack/0": "kyuura_printed_text", "attack/1": "kyuura_printed_text"})
        self.assertIn("jp_en_differences", sources[TENTACRUEL]["notes"])
        self.assertEqual(sorted(k for k in links["latest_descriptions"]["adopted_printed_text"] if k.split("/")[0] in V0112),
                         sorted(f"{card}/attack/{i}" for card in V0112 for i in range(2)))
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (237, 238))


# ---------------------------------------------------------------- 3 章: しょくしゅをつかう


class TentacleGripTest(unittest.TestCase):
    def test_water_units_coins_then_draw(self):
        """N（「水」エネルギーの個数）枚のコイン、H（「おもて」の数）× 2 枚を引く。N = 3・H = 2 なら 4 枚。コインはワザの説明のコインとしてすべて投げてから 1 回引く。"""
        before, after = grip((W, W, W), HD, TL, HD)
        self.assertEqual(flips(before, after), ["heads", "tails", "heads"])
        self.assertEqual(drawn(before, after), 4)
        self.assertEqual((len(after.players[0].hand), len(after.players[0].deck)), (len(before.players[0].hand) + 4, len(before.players[0].deck) - 4))
        kinds = [e["kind"] for e in new_events(before, after) if e["kind"] in ("coin_flip", "draw")]
        self.assertEqual(kinds[:4], ["coin_flip"] * 3 + ["draw"])
        audited(self, after)

    def test_all_tails_and_short_deck(self):
        """すべて「うら」なら 0 枚（ワザの失敗ではない）。山札が 2H より少なければ引けるだけ引き、効果で引くので負けにしない（p.311・p.312）。山札 0 枚でも、既存のコインで引くワザ
        （``DrawOnHeads``）と同じくコインは投げ、0 枚引く。"""
        before, after = grip((W, W), TL, TL)
        self.assertEqual((flips(before, after), drawn(before, after)), (["tails", "tails"], 0))
        before, after = grip((W, W, W), HD, HD, TL, deck=[W] * 3)
        self.assertEqual((drawn(before, after), len(after.players[0].deck), after.phase.value), (3, 0, "main"))
        before, after = grip((W, W), HD, HD, deck=[])
        self.assertEqual((flips(before, after), drawn(before, after), after.phase.value, after.turn_number), (["heads", "heads"], 0, "main", TURN + 1))

    def test_counts_units_not_cards_other_colors_or_the_opponent(self):
        """数えるのは実際に使ったポケモンの「水」エネルギーの個数。ほかの色・無色2個エネルギー・相手の「水」は数えない。［エナジーコンバーター］で「水」にした雷エネルギーカードは、
        「水」の基本エネルギーカードではないが「水」エネルギー 1 個（v0.88 の確定した読み方。個数とカードの枚数が分かれる例）。"""
        state = board(mon(TENTACRUEL, (W, PS, DCE)), opponent=mon(CHANSEY, (W, W, W, W)))
        self.assertEqual(len(flips(state, attack(state, 0, TL))), 1)
        state = board(mon(TENTACRUEL, (W, L)), bench=(porygon2(),), opponent=mon(CHANSEY))
        tentacruel = state.players[0].active
        changed = convert(state, tentacruel, tentacruel.energy[1], EnergyType.WATER)
        self.assertEqual((len(E.attached_basic_energy(changed, changed.players[0].active, EnergyType.WATER)), E.typed_unit_count(changed, changed.players[0].active, EnergyType.WATER)), (1, 2))
        done = attack(changed, 0, HD, HD)
        self.assertEqual((len(flips(changed, done)), drawn(changed, done)), (2, 4))
        audited(self, done)

    def test_color_questions_and_wild_growth(self):
        """読み方で「水」の個数が変わるなら既存の問いで止める（レインボーエネルギーは RB1。状態・乱数・ログを変えない）。決まっているカード（無色2個エネルギー）は止めない。「水」を
        数えるので［おいしげる］の「草」の問いは当てはめない。"""
        rainbow = board(mon(TENTACRUEL, (W, RAINBOW)), opponent=mon(CHANSEY))
        rejects(self, rainbow, UseAttack(0, 0), QUESTIONS["rainbow_energy_type"].code)
        with mock.patch.object(P, "wild_growth_question", side_effect=AssertionError("おいしげるを聞いた")):
            state = board(mon(TENTACRUEL, (W, DCE)), bench=(mon(MEGANIUM, (G, G)),), opponent=mon(CHANSEY))
            self.assertEqual(len(flips(state, attack(state, 0, TL))), 1)

    def test_copied_grip_counts_the_actual_user(self):
        """ゆびをふるで使うと、実際に使ったピクシーの「水」を数える（借りたドククラゲの「水」ではない）。0 個なら投げず引かない。"""
        for energy, coins, expected in (((PS,), (), 0), ((W, W), (HD, HD), 2)):
            state = board(mon(H.CLEFABLE, energy), opponent=mon(TENTACRUEL, (W, W, W)))
            asked = attack(state, 0)
            self.assertEqual((asked.decision.kind, asked.decision.options), (SELECT_ATTACK, (0, 1)))
            done = answer(asked, (0,), *coins)
            with self.subTest(energy=energy):
                self.assertEqual((len(flips(asked, done)), drawn(asked, done)), (expected, 2 * expected))

    def test_opponent_barrier_does_not_stop_the_draw(self):
        """自分への効果なので、相手の「ワザをうけない」状態（ミュウツーのバリアー）でもコインを投げて引く（v0.34 の無効の判定に当てはまらない）。"""
        state = barrier_turn(mon(TENTACRUEL, (W, W)))
        self.assertEqual(state.turn_number, TURN + 2)
        done = attack(state, 0, HD, TL)
        self.assertEqual(drawn(state, done), 2)

    def test_esp_redo_draws_once_from_the_final_result(self):
        """ナツメのESPのやり直しは、N 枚をすべて投げ直し、確定した H だけで 1 回引く（決定の前に引かない・山札を見せない）。続きは clone・deepcopy・pickle から同じ。不正な答えは状態・
        乱数・ログ・決定を変えない。ESPの関数を差しかえた仕組みの確かめ（v0.113 で訂正: 超の色マーカーのついたドククラゲをベンチに置けば、ナツメのフーディンが［サイコリンク］で
        このワザを持てる。通常の操作を通る確かめは tests/test_variable_coins_search_attachments_v0_113.py の ``EspRealPathTest``）。"""
        state = board(mon(TENTACRUEL, (W, W, W)), opponent=mon(CHANSEY))
        esp = (state.players[0].active.card,)
        with mock.patch.object(E, "esp_cards", lambda s, pokemon: esp if pokemon.pokemon_id == state.players[0].active.pokemon_id else ()), \
                mock.patch.object(E, "esp_redo_problem", lambda *a, **k: None):
            asked = attack(state, 0, HD, TL, TL)
            self.assertEqual((asked.decision.kind, new_events(state, asked, "draw")), (ESP_REDO, []))
            before = snap(asked)
            with self.assertRaises(IllegalActionError):
                apply_kernel(asked, ResolveDecision(1, asked.decision.id, ()))
            self.assertEqual(snap(asked), before)
            redone = same_answers(self, with_coin_results(asked, HD, HD, TL), (1,))
            self.assertEqual([e["redone"] for e in new_events(asked, redone, "esp_redo")], [("heads", "heads", "tails")])
            self.assertEqual(drawn(asked, redone), 4)
            kept = answer(asked, ())
            self.assertEqual(drawn(asked, kept), 2)

    def test_preflight_groups_by_heads_and_modes_agree(self):
        """先読みは「おもて」の数で N + 1 通りにまとめ、まとめない先読みと同じ答え（結果の数は少ないか同じ）。3 つの方法で同じ。v0.13 の止める関数の知らない選択・役割はなく、上限は
        変えていない。"""
        self.assertEqual(MAX_BRANCHES, 4096)
        state = board(mon(TENTACRUEL, (W, W, W, W)), opponent=mon(CHANSEY))
        grouped, grouped_branches = traced(state, UseAttack(0, 0))
        ungrouped, ungrouped_branches = traced(state, UseAttack(0, 0), grouped=False)
        self.assertEqual(grouped, ungrouped)
        self.assertLessEqual(grouped_branches[0], ungrouped_branches[0])
        self.assertEqual(F.legacy_unknown_features(state, state.players[0].active), ())
        results = [snap(apply_kernel(state, UseAttack(0, 0), preflight=mode)) for mode in ("derived", "derived_full", "legacy")]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])

    def test_drawn_cards_stay_hidden(self):
        """引いたカードの id は持ち主にだけ見え、相手・観戦者には枚数だけ（既存の ``draw_cards`` の扱い）。"""
        from kyuura_engine.observation import visible_log

        before, after = grip((W, W), HD, HD)
        own = next(e for e in visible_log(after, 0)[len(before.log):] if e["kind"] == "draw" and e["player"] == 0)
        for viewer in (1, None):
            other = next(e for e in visible_log(after, viewer)[len(before.log):] if e["kind"] == "draw" and e["player"] == 0)
            with self.subTest(viewer=viewer):
                self.assertNotEqual(other.get("cards"), own["cards"])
        self.assertEqual(len(own["cards"]), 4)


# ---------------------------------------------------------------- 4 章: どくばり・ふしょくえき


class PoisonStingTest(unittest.TestCase):
    def test_damage_then_ordinary_poison_on_heads(self):
        """20 のあと、1 枚のコインの「おもて」で通常のどく（ポケモンチェックで 10）。「うら」なら何もしない。英語の欄のマヒにはしない。"""
        state = board(mon(TENTACRUEL, (W, W)), opponent=mon(CHANSEY))
        done = attack(state, 1, HD)
        self.assertEqual(([e["amount"] for e in new_events(state, done, "damage")], done.players[1].active.conditions.poison.damage), ([20], 10))
        self.assertIsNone(done.players[1].active.conditions.exclusive)
        done = attack(state, 1, TL)
        self.assertEqual(([e["amount"] for e in new_events(state, done, "damage")], done.players[1].active.conditions.poison), ([20], None))


class CorrosiveAcidTest(unittest.TestCase):
    def test_heads_paralyzes_tails_locks_only_this_attack(self):
        """40 のあと共有のコイン 1 枚: 「おもて」なら相手をマヒ（自分の制限なし）、「うら」なら実際に使ったオムスター自身に次の自分の番だけ「ふしょくえき」を使えない効果（相手のマヒなし。
        40 は残る）。次の自分の番も「しょくしゅをつかう」は使え、その次の自分の番には「ふしょくえき」も使える。"""
        state = board(mon(OMASTAR, (W, W, W)), opponent=mon(CHANSEY))
        heads = attack(state, 1, HD)
        self.assertEqual((flips(state, heads), [e["amount"] for e in new_events(state, heads, "damage")], lock_on(heads.players[0].active)), (["heads"], [40], []))
        self.assertIsNotNone(heads.players[1].active.conditions.exclusive)
        tails = attack(state, 1, TL)
        self.assertEqual((flips(state, tails), [e["amount"] for e in new_events(state, tails, "damage")]), (["tails"], [40]))
        self.assertIsNone(tails.players[1].active.conditions.exclusive)
        (effect,) = lock_on(tails.players[0].active)
        self.assertEqual((effect.active_turn, effect.attack_index, effect.target_attack_index), (TURN + 2, 1, 1))
        own_turn = apply_kernel(tails, EndTurn(1))
        rejects(self, own_turn, UseAttack(0, 1), "ATTACK_LOCKED", error=IllegalActionError)
        self.assertEqual(drawn(own_turn, attack(own_turn, 0, TL, TL, TL)), 0)
        later = apply_kernel(apply_kernel(own_turn, EndTurn(0)), EndTurn(1))
        self.assertEqual(lock_on(later.players[0].active), [])
        self.assertEqual([e["amount"] for e in new_events(later, attack(later, 1, HD), "damage")], [40])
        audited(self, tails)

    def test_lock_survives_a_void_opponent_effect(self):
        """相手がミュウツーのバリアー（ワザをうけない）でダメージ・マヒが無効でも、自分への制限は有効なので共有コインを投げる（HC3 にしない）。「うら」なら制限、「おもて」なら何もない。"""
        state = barrier_turn(mon(OMASTAR, (W, W, W)))
        tails = attack(state, 1, TL)
        self.assertEqual((flips(state, tails), len(lock_on(tails.players[0].active)), new_events(state, tails, "damage")), (["tails"], 1, []))
        heads = attack(state, 1, HD)
        self.assertEqual((flips(state, heads), lock_on(heads.players[0].active), heads.players[1].active.conditions.exclusive), (["heads"], [], None))

    def test_esp_redo_shares_the_final_result(self):
        """ESPでやり直したら、マヒと自分の制限は同じ確定した結果を使う（別々に投げない）。仕組みの確かめ。"""
        state = board(mon(OMASTAR, (W, W, W)), opponent=mon(CHANSEY))
        esp = (state.players[0].active.card,)
        with mock.patch.object(E, "esp_cards", lambda s, pokemon: esp if pokemon.pokemon_id == state.players[0].active.pokemon_id else ()), \
                mock.patch.object(E, "esp_redo_problem", lambda *a, **k: None):
            asked = attack(state, 1, TL)
            self.assertEqual((asked.decision.kind, new_events(state, asked, "persistent_effect_added")), (ESP_REDO, []))
            redone = same_answers(self, with_coin_results(asked, HD), (1,))
            self.assertEqual((lock_on(redone.players[0].active), redone.players[1].active.conditions.exclusive is not None), ([], True))
            kept = answer(asked, ())
            self.assertEqual((len(lock_on(kept.players[0].active)), kept.players[1].active.conditions.exclusive), (1, None))

    def test_knocked_out_target_or_user(self):
        """相手がこのワザでHP以上なら「おもて」のマヒは処理しないが、共有コインは自分の制限のために投げる（既存の扱い）。反撃（カイリキーの［はんげき］）でオムスター自身がHP以上なら、
        「うら」でも制限を与えない（ログ ``persistent_effect_skipped``）。"""
        state = board(mon(OMASTAR, (W, W, W)), opponent=mon(H.RATTATA))
        tails = attack(state, 1, TL)
        self.assertEqual((flips(state, tails), len(lock_on(tails.players[0].active))), (["tails"], 1))
        state = board(mon(OMASTAR, (W, W, W), damage=70), opponent=mon(H.MACHAMP))
        tails = attack(state, 1, TL)
        self.assertEqual([e["persistent_effect"] for e in new_events(state, tails, "persistent_effect_skipped")], ["cannot_use_own_attack"])
        self.assertEqual((new_events(state, tails, "persistent_effect_added"), [e["pokemon"] for e in new_events(state, tails, "knock_out")]),
                         ([], [state.players[0].active.card]))

    def test_copying_the_lock_stays_unsupported(self):
        """ゆびをふるでふしょくえきを使うのは、番をまたぐ「このワザ」を記録で表せないので、既存のエンジンの未対応（``UNSUPPORTED_COPIED_ATTACK``。歴史的なルールの禁止ではない）。しょくしゅを
        つかうは使える。"""
        state = board(mon(H.CLEFABLE, (W,)), opponent=mon(OMASTAR, (W, W, W)))
        asked = attack(state, 0)
        self.assertEqual(asked.decision.options, (0, 1))
        self.assertEqual(asked.decision.context_value("unsupported_choices", ()), (1,))
        with self.assertRaises(UnsupportedError) as raised:
            apply_kernel(asked, ResolveDecision(0, asked.decision.id, (1,)))
        self.assertEqual(raised.exception.code, "UNSUPPORTED_COPIED_ATTACK")

    def test_saves_and_invariants(self):
        """新しい状態の項目はない（形式 26 のまま）。clone・deepcopy・pickle から同じ結果。不変条件は登録の ``attack_lock_terms`` と照らす（位置を取り違えた効果を見つける）。"""
        from kyuura_engine.engine import check_invariants

        self.assertEqual((max(FORMAT_VERSIONS), LATEST_FORMAT), (26, 26))
        state = board(mon(OMASTAR, (W, W, W)), opponent=mon(CHANSEY))
        expected = attack(state, 1, TL)
        for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            self.assertEqual(snap(attack(other, 1, TL)), snap(expected))
        self.assertEqual(check_invariants(expected), [])
        broken = expected.clone()
        holder = broken.players[0].active
        holder.persistent_effects = tuple(dataclasses.replace(e, target_attack_index=0) if isinstance(e, CannotUseOwnAttack) else e for e in holder.persistent_effects)
        self.assertTrue(check_invariants(broken))


# ---------------------------------------------------------------- 5 章: ログの監査と正式な対戦の道具


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v112_problems``）は、エンジンの登録・計算を読まずに、印刷の文面から読んだ色・数・面と、ログから組み立てたエネルギー・コイン・引いたカード・手札で
    確かめる。エンジンの処理を一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py の局。v0.112 のワザが出る組と開発用の seed）で、監査がそれを見つける。"""

    # 開発用の seed（正式な対戦の seed 0〜3 とは別）のうち、ほかの種類のエネルギーカードのついたポケモンのしょくしゅをつかう・相手の残るふしょくえき（マヒと「うら」の制限）・どくばりが出る局
    GAMES = ((("O112", "T112"), 100), (("T112", "O112"), 100))

    @classmethod
    def problems_for(cls, patcher, *needles):
        from tools import existing_effect_games as games

        found = []
        with patcher:
            for labels, seed in cls.GAMES:
                result = games.play(labels, seed, keep_state=True)
                if result.get("state") is not None:
                    found += [p for p in log_problems(result["state"]) if any(n in p for n in needles)]
        return found

    def test_the_unpatched_games_pass_the_audit(self):
        from tools import existing_effect_games as games

        seen, policy = set(), set()
        for labels, seed in self.GAMES:
            result = games.play(labels, seed, keep_state=True)
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual((result["outcome"], result["audit"], log_problems(result["state"])), ("game_over", {}, []))
            seen |= {key for key, value in result["v112"].items() if value}
            policy |= {key for key, value in result["policy"].items() if value and key.startswith("v112_")}
        self.assertTrue({"tentacle_grip_drawn", "corrosive_acid_locked", "poison_sting_damage"} <= seen, seen)
        self.assertIn("v112_grip_draw_checked", policy)
        self.assertNotIn("v112_grip_draw_mismatch", policy)

    def test_audit_finds_wrong_coin_counts_or_draws(self):
        """コインの枚数をカードの数（ほかの種類を含む）にした・引く枚数を「おもて」の数 × 3 にした。"""
        def all_cards(self, run):
            run.fs.coins[self.name] = run.flip(len(run.attacker().energy), by_heads=True) if run.attacker().energy else P.CoinFlips(())
            return False

        original_run = P.Coin.run
        wrong = mock.patch.object(P.Coin, "run", lambda self, run: all_cards(self, run) if self.per_own_typed is not None else original_run(self, run))
        self.assertTrue(self.problems_for(wrong, "エネルギーの個数"))
        more = mock.patch.dict(P.BUILDERS, {E.CoinsPerOwnTypedEnergyDraw: lambda e: (P.Coin("coin", per_own_typed=e.energy_type), P.Draw(heads_of="coin", per_heads=3))})
        self.assertTrue(self.problems_for(more, "より多い"))

    def test_audit_finds_separate_coins_or_a_wrong_lock(self):
        """ふしょくえきのマヒと制限を別々のコインにした・「おもて」でも制限を与えた。"""
        separate = {E.DamageParalyzeOnHeadsElseLockSelf: lambda e: (P.Damage(P.OPP, P.Printed()), P.Status(P.PARALYSIS, local_coin=P.HEADS),
                                                                    P.SelfAttackLock(local_coin=P.TAILS))}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, separate), "コインが"))
        always = {E.DamageParalyzeOnHeadsElseLockSelf: lambda e: (P.Damage(P.OPP, P.Printed()), P.Coin("coin"), P.Status(P.PARALYSIS, gate=("coin", P.HEADS)),
                                                                  P.SelfAttackLock(local_coin=None))}
        # 制限をコインの結果で分けないと、「おもて」でも与える（相手が残るとき）・相手がHP以上でコインを投げない（コインの決める要素がマヒだけになる）のどちらかで見つかる
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, always), "「おもて」で、自分に", "のコインが 0 枚"))


class DocumentTest(unittest.TestCase):
    def test_document_names_the_shared_parts(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("CoinsPerOwnTypedEnergyDraw", "DamageParalyzeOnHeadsElseLockSelf", "per_own_typed", "typed_units_for", "heads_of", "per_heads", "DrawOnHeads",
                       "PoisonOnHeads", "ParalyzeOnHeads", "DamageThenParalyzeOrSelfDamage", "SelfAttackLock", "CannotUseOwnAttack", "attack_lock_terms", "coin_group",
                       "reads_deck_order", "draw_cards", "AttackRun.flip", "UNSUPPORTED_COPIED_ATTACK", "jp_en_differences", "TE1", "RB1", "BZ2", "MEC1", "CE1", "CE2",
                       "v112_problems", "v112_uses", "_v112_attack_observe", "ea6ab5c", "73a1690"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
