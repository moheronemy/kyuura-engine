"""v0.118（docs/unbounded-coins-heal-allocation-v0.118.md）: 上限なしコイン・攻撃時の能力・回復の配分の 9 枚（ワザ 14・特殊能力 3）。わるいオクタン（neo4-037）・わるいナッシー（neo4-056）・
アンノーンX（neo4-065）・わるいポリゴン2（neo4-097）・フシギソウ（SI-008）・ラフレシア（SI-011）・ニャース（PR1-025）・カイリュー（PR1-043）・ルギア（PF3-008）。

根拠は kyuura データの採用（kyuura ``e519b99`` の data/cards.json の日本語の印刷の文面。9 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録（GR-2000-P309-ATTACK-PROCEDURE・
GR-2000-P320-RECOVERY・GR-2000-P321-DAMAGE-ORDER・p.312 の引く・p.323 のワザの失敗・v0.38 の ``has_target``・v0.4b の問い・v0.34 の HC3・v0.66 のESP（ES1）・v0.94 の答えごとの先読み・
v0.104 の回復・v0.115 の配分・v0.57 のスタジアム）。英語の欄・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。盤面は ``build_test_state``
で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.118``）。A0 は tests/test_esp_until_tails_v0_118.py。
"""

from __future__ import annotations

import copy
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
    UsePokemonPower,
    UseStadium,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import (
    EnergyType,
    load_card_pool,
    pool_from_extract,
    read_extract,
)
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    DECK_TOP_FROM_HAND,
    ESP_REDO,
    HEAL_ALLOCATION,
    OPTIONAL_COIN,
    SELECT_POKEMON,
    STADIUM_FROM_DISCARD,
)
from kyuura_engine.engine import apply_command_traced, check_invariants
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe, visible_log
from kyuura_engine.resolution import kernel as K
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution import unbounded
from kyuura_engine.resolution.events import FrameKind, PreflightResult
from kyuura_engine.serialize import state_to_dict
from kyuura_engine.state import MARKER_COLOR, RetreatCostIncrease
from tests import helpers as H
from tests import test_variable_coins_search_attachments_v0_113 as V113
from tests.helpers import (
    apply_kernel,
    build_test_state,
    with_coin_bits,
    with_coin_results,
)
from tests.test_barrier_resume_coin_bonus_v0_34 import with_barrier
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_unown_family_powers_v0_96 import snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "unbounded-coins-heal-allocation-v0.118.md"
COMMIT = "e519b99e2adcc6c2cd0998569ae5ee1101de6e89"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, G, PS, F, L = H.WATER, H.GRASS, H.PSYCHIC, H.FIGHTING, H.LIGHTNING
DCE = H.DOUBLE_COLORLESS_ENERGY
OCTILLERY, EXEGGUTOR, UNOWN_X, PORYGON2, IVYSAUR, VILEPLUME, MEOWTH, DRAGONITE, LUGIA = (
    "neo4-037", "neo4-056", "neo4-065", "neo4-097", "SI-008", "SI-011", "PR1-025", "PR1-043", "PF3-008")
V0118 = (OCTILLERY, EXEGGUTOR, UNOWN_X, PORYGON2, IVYSAUR, VILEPLUME, MEOWTH, DRAGONITE, LUGIA)
BUMPY_GYM = "neo4-110"  # でこぼこジム（スタジアム）
TURN = 7
BELOW = {OCTILLERY: ["neo4-030"], EXEGGUTOR: ["neo4-049"], PORYGON2: ["neo4-086"], IVYSAUR: [H.BULBASAUR], VILEPLUME: ["neo1-001", "neo1-008"],
         DRAGONITE: ["PMCG1-065", "PMCG1-069"]}

INK_TEXT = "ワザに必要な｢エネルギー｣よりも多く｢エネルギー｣がついているとき、多い「エネルギー」1個につき、10ダメージを追加する。ダメージ追加は2個ぶんまで。"
CONSTRICT_TEXT = "コインを投げて「おもて」なら、相手を「マヒ」状態にする。「うら」なら、次の相手の番、このワザを受けた相手は、「にげる」ときに必要な「エネルギー」が、1個ぶん多くなる。"
TRIPLE_TEXT = "コインを3枚投げ、「おもて」の数×10のダメージ。"
DARK_MAX_TEXT = "相手の場のポケモン全員についている「エネルギー」の数ぶんコインを投げ、「おもて」の数×20のダメージ。"
X_TEXT = ("この力は、自分の場の「アンノーン」が「めざめるパワー」を使うとき、使うことができる。「うら」が出るまでコインを投げつづけ、その間に出た「おもて」の数×10のダメージを、その「めざめるパワー」の"
          "ダメージに追加する。この番に、すでに自分の場のほかのアンノーン「X」の「XXXXX」を使っていたなら、この力を使うことはできない。")
ROLLING_TEXT = "コインを投げて「おもて」なら、次の相手の番、このカードはワザによるダメージを受けない(ダメージ以外の効果は受ける)。"
TIME_SHIFT_TEXT = ("この力は、自分の番ごとに1回使うことができる。コインを投げて「おもて」なら、自分のトラッシュから「スタジアムカード」を1枚選び出し、場に出す(すでに場にある「スタジアムカード」は、"
                   "トラッシュする)。このカードが「ねむり・マヒ・こんらん」状態のとき、この力を使うことはできない。")
AROMA_TEXT = ("お互いのプレイヤーは、それぞれコインを投げる。「おもて」を出したプレイヤーは、自分の場のポケモンにのっているダメージカウンターを、最大3つとりのぞく。(合計が3つ以下なら、2匹以上の"
              "ポケモンから、とりのぞいてもよい)")
BLISS_TEXT = "コインを投げて「おもて」なら、自分の控えポケモンを1匹選び、そのポケモンにのっているダメージカウンター最大2つと、自分にのっているダメージカウンター最大2つを、それぞれ、とりのぞく。"
WORST_TEXT = "コインを投げて「おもて」なら、相手を「マヒ」状態に、「うら」なら「こんらん」状態にする。"
WINDFALL_TEXT = "「うら」が出るまでコインを投げつづけ、その間に出た「おもて」の数だけ、カードを引く。"
MACH_TEXT = "コインを投げ「うら」なら、このワザは失敗する。"
TRANSPORT_TEXT = ("この力は、自分の番ごとに1回使える。自分の山札からカードを1枚引いて、手札に加える。その後、自分の手札からカードを1枚選び、山札の上に置く。このカードが「ねむり・マヒ・こんらん」状態の時、"
                  "この力は使えない。")
AERO_TEXT = "のぞむなら、コインを投げてよい。コインを投げて「おもて」なら、このワザのダメージは「80」になる。「うら」なら、このワザは失敗する。"
# 依頼で示された固定データの日本語。(タイプ, HP, 段階, 進化元, ワザ ((名前, 必要なエネルギー, 目安, 説明), ...), 特殊能力 ((名前, 説明), ...))
QUOTED = {
    OCTILLERY: ("water", 60, "stage1", "テッポウオ", (("スミでっぽう", ("water",), "20+", INK_TEXT), ("しめつづける", ("water", "colorless"), "20", CONSTRICT_TEXT)), ()),
    EXEGGUTOR: ("psychic", 60, "stage1", "タマタマ", (("トリプルずつき", ("colorless",), "10×", TRIPLE_TEXT), ("わるわるMAX", ("psychic", "colorless"), "20×", DARK_MAX_TEXT)), ()),
    UNOWN_X: ("psychic", 50, "basic", None, (("めざめるパワー", ("psychic",), "10", None),), (("XXXXX[?????]", X_TEXT),)),
    PORYGON2: ("colorless", 60, "stage1", "ポリゴン", (("まるまるアタック", ("colorless",) * 3, "20", ROLLING_TEXT),), (("じくうへんかん", TIME_SHIFT_TEXT),)),
    IVYSAUR: ("grass", 60, "stage1", "フシギダネ", (("ふしぎなかおり", ("grass",), None, AROMA_TEXT), ("はっぱカッター", ("grass", "grass"), "30", None)), ()),
    VILEPLUME: ("grass", 70, "stage2", "クサイハナ", (("ごくらくかふん", ("grass",), None, BLISS_TEXT), ("さいあくかふん", ("grass", "grass", "colorless"), "30", WORST_TEXT)), ()),
    MEOWTH: ("colorless", 50, "basic", None, (("ひっかく", ("colorless",), "10", None), ("まるもうけ", ("colorless",), None, WINDFALL_TEXT)), ()),
    DRAGONITE: ("colorless", 90, "stage2", "ハクリュー", (("マッハひこう", ("colorless",) * 3, "60", MACH_TEXT),), (("トランスポート", TRANSPORT_TEXT),)),
    LUGIA: ("psychic", 90, "basic", None, (("エアロウイング", ("colorless",) * 4, "40", AERO_TEXT),), ()),
}
EXPECTED = {
    (OCTILLERY, 0): E.ExtraEnergyUnitsDamage(10, 2), (OCTILLERY, 1): E.DamageThenParalyzeOnHeadsElseRetreatCost(1),
    (EXEGGUTOR, 0): E.CoinFlipDamage(3, 10), (EXEGGUTOR, 1): E.CoinsPerOpponentFieldEnergyDamage(20),
    (UNOWN_X, 0): E.DAMAGE_ONLY, (PORYGON2, 0): E.DamageThenPreventAttackDamageOnHeads(),
    (IVYSAUR, 0): E.EachPlayerCoinHealOwnField(3), (IVYSAUR, 1): E.DAMAGE_ONLY,
    (VILEPLUME, 0): E.CoinHealChosenBenchAndSelf(2), (VILEPLUME, 1): E.DamageThenStatusByCoin(E.PARALYSIS, E.CONFUSION),
    (MEOWTH, 0): E.DAMAGE_ONLY, (MEOWTH, 1): E.CoinsUntilTailsDraw(),
    (DRAGONITE, 0): E.FailOnTailsDamage(), (LUGIA, 0): E.OptionalCoinSetDamageElseFail(80),
}
EXPECTED_POWERS = {UNOWN_X: E.CoinsUntilTailsBonusToGroupAttack("X", "XXXXX"), PORYGON2: E.CoinPutStadiumFromDiscard(), DRAGONITE: E.DrawThenPutHandCardOnDeckTop()}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, *, bench=(H.RATTATA,), opponent=None, opponent_bench=(H.RATTATA,), hand=(), deck=None, discard=(), opponent_deck=None, opponent_hand=(),
          turn=TURN, current=0, effects=None):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": list(deck if deck is not None else [W] * 10), "discard": list(discard), "prizes": 6}
    them = {"active": opponent or mon(H.RATTATA), "bench": list(opponent_bench), "hand": list(opponent_hand),
            "deck": list(opponent_deck if opponent_deck is not None else [W] * 10), "discard": [], "prizes": 6}
    return build_test_state([me, them], turn_number=turn, current_player=current, effects=effects)


def attack(state, index=0, *coins, bits=False, **kw):
    if coins:
        state = (with_coin_bits if bits else with_coin_results)(state, *coins)
    return apply_kernel(state, UseAttack(state.current_player, index, **kw))


def answer(state, choices, *coins, bits=False):
    d = state.decision
    if coins:
        state = (with_coin_bits if bits else with_coin_results)(state, *coins)
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)))


def power(state, pid, index=0, *coins):
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UsePokemonPower(state.current_player, pid, index))


def same_answers(test, state, choices, *coins, bits=False):
    """待っている決定のある状態を clone・deepcopy・pickle しても、同じ答え（と同じコイン）で同じ結果になる。"""
    expected = answer(state, choices, *coins, bits=bits)
    for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
        test.assertEqual(snap(answer(other, choices, *coins, bits=bits)), snap(expected))
    return expected


def run(heads: int) -> tuple[CoinSide, ...]:
    return (HD,) * heads + (TL,)


def last(state, kind):
    found = [e for e in state.log if e["kind"] == kind]
    return found[-1] if found else None


def bases(before, after, target="opponent_active"):
    return [dict(e["steps"]).get("1 基本となる計算") for e in new_events(before, after, "damage") if (e.get("target") or "opponent_active") == target]


def steps(before, after):
    return [dict(e["steps"]) for e in new_events(before, after, "damage")]


def flips(before, after, source="attack"):
    return [(e["player"], e["result"]) for e in new_events(before, after, "coin_flip") if e.get("source") == source]


def pid(state, card_id, player=0):
    return next(p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card_id)


def uid(state, card_id, player=0, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def preflight_branches(state, command, mode="derived_full"):
    _, trace = apply_command_traced(state, command, preflight=mode)
    return [r.branches for r in trace.of(PreflightResult)]


def esp_board(provider, energy, **kw):
    """ナツメのフーディンのベンチに超の色マーカーの ``provider`` を置き、手札のナツメのESPを通常の操作でつけた盤面（v0.113 の ``esp_board``。進化元はこのモジュールの表）。"""
    with mock.patch.dict(V113.BELOW, BELOW):
        return V113.esp_board(provider, energy, **kw)


# ---------------------------------------------------------------- 3 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_entries_and_printed_texts(self):
        """9 枚・14 のワザ・3 つの特殊能力の名前・必要なエネルギー・目安・説明と、タイプ・HP・段階・進化元は依頼の日本語・固定データと同じ。登録の型・引数も同じ。"""
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_118"]), V0118)
        self.assertEqual(sum(len(q[4]) for q in QUOTED.values()), 14)
        self.assertEqual(sum(len(q[5]) for q in QUOTED.values()), 3)
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

    def test_data_gaps_sources_and_groups(self):
        """同じカードの組はない。データの欠けは PR1-025 の図鑑番号・レベル、PR1-043・PF3-008 のレベルで、補わない。転記元は neo4 が Pokemon Wiki、ほかは pcg-search.com。
        アンノーンX のルール文（4 枚まで）は写しの値。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        self.assertEqual({card: cards[card]["same_card_group"] for card in V0118}, dict.fromkeys(V0118))
        self.assertEqual({card: cards[card]["data_gaps"] for card in V0118},
                         {**{card: [] for card in V0118}, MEOWTH: ["pokemon.dex", "jp_print.level"], DRAGONITE: ["jp_print.level"], LUGIA: ["jp_print.level"]})
        self.assertEqual({card: cards[card]["ja_text_source"].split("/")[2] for card in V0118},
                         {**{card: "wiki.pokemonwiki.com" for card in V0118[:4]}, **{card: "pcg-search.com" for card in V0118[4:]}})
        self.assertEqual(cards[UNOWN_X]["pokemon"]["rules_text"]["ja"], "「アンノーン」はデッキに4枚までしか入れることができません。")
        self.assertEqual({card: cards[card]["pokemon"]["rules_text"] for card in V0118 if card != UNOWN_X}, dict.fromkeys(set(V0118) - {UNOWN_X}))

    def test_unregistered_without_the_v0_118_entries(self):
        """v0.118 の登録を除くと、対戦に使えなくなるのはちょうどこの 9 枚（ほかのカードは失われない）。"""
        registry = DEFAULT_EFFECTS.without_attacks("test-no-v0-118", E.V0_118_ATTACKS).without_powers("test-no-v0-118", E.V0_118_POWERS)
        before = load_card_pool().playable_ids
        after = pool_from_extract(read_extract(), registry).playable_ids
        self.assertEqual(before - after, set(V0118))
        self.assertLessEqual(after, before)

    def test_records_and_research_links(self):
        """採用の記録 9 件（kyuura_data・adopted・e519b99・2026-10-29・kyuura_records なし・外部照合なし）。研究の対応表の adopted_printed_text に説明文のある 11 のワザと 3 つの特殊能力。"""
        import json

        data = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        texts = []
        for card in V0118:
            record = data[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["recorded_on"], record["kyuura_records"], record["external_checks"],
                                  record["issues"]), ("kyuura_data", "adopted", COMMIT, "2026-10-29", [], [], []))
                self.assertEqual(set(record["play_text"].values()), {"kyuura_printed_text"})
                texts += [f"{card}/{key}" for key in record["play_text"]]
        self.assertEqual(len(texts), 14)
        self.assertLessEqual(set(texts), set(links["latest_descriptions"]["adopted_printed_text"]))
        for code, ruling in (("UNRESOLVED_HEAL_UP_TO_ZERO", "HZ1"), ("UNRESOLVED_GROUP_POWER_COIN_ORDER", "XP1"), ("UNRESOLVED_TIME_SHIFT_WITHOUT_TARGET", "SX1"),
                             ("UNRESOLVED_STADIUM_REUSE_AFTER_RETURN", "SX2"), ("UNRESOLVED_TRANSPORT_WITHOUT_CARDS", "TN1")):
            with self.subTest(code=code):
                self.assertEqual(links["stop_codes"][code], {"engine_rulings": [{"version": "v0.118", "document": "docs/unbounded-coins-heal-allocation-v0.118.md",
                                                                                   "ruling_id": ruling}], "kyuura_issue": None, "kyuura_disposition": "not_in_kyuura"})

    def test_text_variants_are_exact(self):
        """既存の型に加えた書き方は全文 1 通りだけ（マッハひこうの「投げ」は 1 枚のときだけ・まるまるアタックの補足の括弧）。近い文面・違う数は拒否する。スミでっぽうは水だけを数える
        既存の ExtraEnergyDamage の形の確かめには通るが、意味の違う型なので使わない（登録は ExtraEnergyUnitsDamage。新しい型は水の文面を拒否する）。"""
        import dataclasses

        pool = load_card_pool()
        mach = pool.definitions[DRAGONITE].attacks[0]
        self.assertEqual(E.FailOnTailsDamage().check(mach), [])
        self.assertNotEqual(E.FailOnTailsDamage(2).check(dataclasses.replace(mach, text_ja="コインを2枚投げ「うら」なら、このワザは失敗する。")), [])
        self.assertNotEqual(E.FailOnTailsDamage().check(dataclasses.replace(mach, text_ja="コインを投げ「うら」なら、このワザは失敗しない。")), [])
        rolling = pool.definitions[PORYGON2].attacks[0]
        self.assertEqual(E.DamageThenPreventAttackDamageOnHeads().check(rolling), [])
        self.assertNotEqual(E.DamageThenPreventAttackDamageOnHeads().check(dataclasses.replace(rolling, text_ja=ROLLING_TEXT.replace("(ダメージ以外の効果は受ける)", "(ダメージ以外の効果も受けない)"))), [])
        ink = pool.definitions[OCTILLERY].attacks[0]
        self.assertEqual(E.ExtraEnergyDamage(EnergyType.WATER, 10, 2).check(ink), [])  # 形だけの確かめは通る（意味が違うので使わない）
        self.assertEqual(E.ExtraEnergyUnitsDamage(10, 2).check(ink), [])
        water = pool.definitions["neo4-028"].attacks[0]  # ワニノコの「みずでっぽう」（「水」エネルギー）
        self.assertNotEqual(E.ExtraEnergyUnitsDamage(10, 2).check(water), [])
        self.assertNotEqual(E.ExtraEnergyUnitsDamage(10, 3).check(ink), [])
        self.assertNotEqual(E.CoinsPerOpponentFieldEnergyDamage(10).check(pool.definitions[EXEGGUTOR].attacks[1]), [])
        self.assertNotEqual(E.EachPlayerCoinHealOwnField(2).check(pool.definitions[IVYSAUR].attacks[0]), [])
        self.assertNotEqual(E.CoinHealChosenBenchAndSelf(3).check(pool.definitions[VILEPLUME].attacks[0]), [])
        self.assertNotEqual(E.OptionalCoinSetDamageElseFail(60).check(pool.definitions[LUGIA].attacks[0]), [])

    def test_programs_and_declared_elements(self):
        """要素の並び（新しい型の組み合わせ）。相手の対戦ポケモンへの効果の宣言は、しめつづけるのマヒ・「にげる」エネルギーと、ふしぎなかおりの回復（相手の場）。"""
        compile_attack = P.compile_attack
        self.assertEqual(compile_attack(E.ExtraEnergyUnitsDamage(10, 2)), (P.Damage(P.OPP, P.ExtraUnits(10, 2)),))
        self.assertEqual(compile_attack(E.DamageThenParalyzeOnHeadsElseRetreatCost(1)), (
            P.Damage(P.OPP, P.Printed()), P.Coin("coin"), P.Status(E.PARALYSIS, gate=("coin", HD), reparalysis_check=True),
            P.OpponentRetreatCostIncrease(1, gate=("coin", TL))))
        self.assertEqual(compile_attack(E.CoinsUntilTailsDraw()), (P.DrawUntilTails(),))
        self.assertEqual(compile_attack(E.OptionalCoinSetDamageElseFail(80)), (P.OptionalCoin("choice"), P.ChosenCoinFailOnTails("choice", "coin"),
                                                                              P.Damage(P.OPP, P.SetOnHeads("coin", 80))))
        self.assertEqual(E.DamageThenParalyzeOnHeadsElseRetreatCost.opponent_effect_elements, (E.PARALYSIS, E.RETREAT_COST_ELEMENT))
        self.assertEqual(E.EachPlayerCoinHealOwnField.opponent_effect_elements, (E.HEAL_ELEMENT,))
        for effect in (E.CoinHealChosenBenchAndSelf(2), E.CoinsUntilTailsDraw(), E.OptionalCoinSetDamageElseFail(80), E.ExtraEnergyUnitsDamage(10, 2),
                       E.CoinsPerOpponentFieldEnergyDamage(20)):
            self.assertEqual(effect.opponent_effect_elements, ())
        self.assertIn(E.RETREAT_COST_ELEMENT, E.ATTACK_ELEMENTS)

    def test_new_attack_types_are_kernel_programs(self):
        """新しいワザの型 7 つは解決の基盤の要素の並び（``programs.BUILDERS``）で処理し、v0.13 の約束（``resolve``・``resume``）を上書きしない（tests/helpers.py の
        ``ATTACK_TYPES_SINCE_V0_17`` に加えた。v0.13 の止める関数で確かめる型に入れない）。"""
        from kyuura_engine.resolution import v013_checks

        new = (E.ExtraEnergyUnitsDamage, E.DamageThenParalyzeOnHeadsElseRetreatCost, E.CoinsPerOpponentFieldEnergyDamage, E.EachPlayerCoinHealOwnField,
               E.CoinHealChosenBenchAndSelf, E.CoinsUntilTailsDraw, E.OptionalCoinSetDamageElseFail)
        start = H.ATTACK_TYPES_SINCE_V0_17.index(new[0])
        self.assertEqual(H.ATTACK_TYPES_SINCE_V0_17[start:start + len(new)], new)
        self.assertEqual({type(entry.effect) for entry in E.V0_118_ATTACKS.values()} - {type(E.DAMAGE_ONLY), E.CoinFlipDamage, E.DamageThenStatusByCoin,
                                                                                     E.FailOnTailsDamage, E.DamageThenPreventAttackDamageOnHeads}, set(new))
        for cls in new:
            with self.subTest(cls=cls.__name__):
                self.assertIn(cls, P.BUILDERS)
                self.assertNotIn(cls, v013_checks.VERIFIED)


# ---------------------------------------------------------------- 6 章: エネルギーの数とコインで分かれる効果


class InkShotTest(unittest.TestCase):
    def test_counts_every_color_and_caps_at_two(self):
        """スミでっぽう（水 1）: 多い「エネルギー」は色を問わない個数（無色2個エネルギーは 2 個）。目安 20 + 10 × min(多い数, 2)。"""
        for energy, base in (((W,), 20), ((W, F), 30), ((W, L, G), 40), ((W, DCE), 40), ((W, W, W, W), 40), ((F,), 20)):
            state = board(mon(OCTILLERY, energy), opponent=mon(H.CHANSEY))
            if energy == (F,):
                with self.assertRaises(IllegalActionError):
                    attack(state, 0)  # 水 1 を払えない
                continue
            with self.subTest(energy=energy):
                self.assertEqual(bases(state, attack(state, 0)), [base])

    def test_not_the_water_only_type(self):
        """水だけを数える ExtraEnergyDamage(水) なら、闘エネルギーは多い数にならない（同じ盤面で 20）。登録の型は 30。"""
        state = board(mon(OCTILLERY, (W, F)), opponent=mon(H.CHANSEY))
        self.assertEqual(bases(state, attack(state, 0)), [30])
        water_only = DEFAULT_EFFECTS.with_attacks("test-water-only", {AttackKey(OCTILLERY, 0): E.AttackEntry(E.ExtraEnergyDamage(EnergyType.WATER, 10, 2), "スミでっぽう",
                                                                                                           INK_TEXT, INK_TEXT, "kyuura data/cards.json")})
        other = board(mon(OCTILLERY, (W, F)), opponent=mon(H.CHANSEY), effects=water_only)
        self.assertEqual(bases(other, attack(other, 0)), [20])


class ConstrictTest(unittest.TestCase):
    def test_one_coin_heads_paralysis_tails_retreat_cost(self):
        """しめつづける: 目安 20 のあと 1 枚のコイン。「おもて」でマヒ（「にげる」エネルギーは変えない）。「うら」はワザの失敗でもマヒでもなく、次の相手の番だけ「にげる」エネルギー +1。"""
        state = board(mon(OCTILLERY, (W, W)), opponent=mon(H.CHANSEY))
        heads = attack(state, 1, HD)
        self.assertTrue(heads.players[1].active.conditions.paralyzed)
        self.assertEqual(heads.players[1].active.persistent_effects, ())
        tails = attack(state, 1, TL)
        self.assertFalse(tails.players[1].active.conditions.paralyzed)
        self.assertEqual(new_events(state, tails, "attack_failed"), [])
        (effect,) = tails.players[1].active.persistent_effects
        self.assertEqual((type(effect), effect.amount, effect.attack, effect.active_turn), (RetreatCostIncrease, 1, f"{OCTILLERY}#1", TURN + 1))
        self.assertEqual(E.retreat_cost(tails, 1).maximum, E.retreat_cost(heads, 1).maximum + 1)
        audited(self, tails)

    def test_retreat_pays_one_more_only_next_turn(self):
        """次の相手の番に「にげる」なら、印刷の数（ラッキー 1）+ 1 = 2 個をトラッシュする。1 個では拒否。効果による入れ替え（ポケモンいれかえ）はエネルギーをトラッシュしない。"""
        state = board(mon(OCTILLERY, (W, W)), opponent=mon(H.CHANSEY, (W, W, W)), opponent_hand=(H.SWITCH,))
        tails = attack(state, 1, TL)
        energy = tails.players[1].active.energy
        rattata = tails.players[1].bench[0].card
        rejects(self, tails, Retreat(1, tuple(energy[:1]), rattata), "WRONG_RETREAT_COST", IllegalActionError)
        retreated = apply_kernel(tails, Retreat(1, tuple(energy[:2]), rattata))
        self.assertEqual(len(retreated.players[1].bench[0].energy), 1)
        self.assertEqual(retreated.players[1].bench[0].persistent_effects, ())  # ベンチにもどったら消える
        switched = apply_kernel(tails, PlayTrainer(1, uid(tails, H.SWITCH, 1)))
        switched = answer(switched, (switched.decision.options[0],))
        self.assertEqual(len(switched.players[1].bench[0].energy), 3)

    def test_barrier_stops_the_coin_as_hc3(self):
        """相手が「ワザをうけない」状態（バリアー）なら、コインはマヒと「にげる」の効果だけを決めるので、投げるかが決められない（既存の HC3。状態を変えない）。"""
        state = with_barrier(mon(OCTILLERY, (W, W)))
        rejects(self, state, UseAttack(1, 1), "UNRESOLVED_PREVENTED_EFFECT_COIN")


class DarkMaxTest(unittest.TestCase):
    def test_counts_opponent_field_units(self):
        """わるわるMAX: 相手の場（バトル場・ベンチ）のポケモン全員の「エネルギー」の個数ぶんコインを投げる（無色2個エネルギーは 2 個）。自分の場・カードの枚数ではない。「おもて」の数 × 20。"""
        state = board(mon(EXEGGUTOR, (PS, W, W)), opponent=mon(H.CHANSEY, (W, DCE)), opponent_bench=(mon(H.RATTATA, (W,)), H.RATTATA))
        after = attack(state, 1, HD, TL, HD, TL)
        self.assertEqual(len(flips(state, after)), 4)
        self.assertEqual(bases(state, after), [40])

    def test_zero_energy_no_coin_no_failure(self):
        """相手の場にエネルギーがなければ 0 枚・基本となるダメージ 0（2 段階で終える）。ワザの失敗ではない。"""
        state = board(mon(EXEGGUTOR, (PS, W)), opponent=mon(H.CHANSEY))
        after = attack(state, 1)
        self.assertEqual((flips(state, after), bases(state, after), new_events(state, after, "attack_failed")), ([], [0], []))

    def test_prevented_damage_question_only_with_coins(self):
        """相手がダメージを受けない状態なら、コインはダメージの量だけを決めるので v0.4b の問い（エネルギーが 0 個なら投げないので止めない）。"""
        state = board(mon(EXEGGUTOR, (PS, W)), opponent=mon(H.CHANSEY, (W,), prevent_damage=TURN - 1))
        rejects(self, state, UseAttack(0, 1), "UNRESOLVED_PREVENTED_COIN_DAMAGE")
        empty = board(mon(EXEGGUTOR, (PS, W)), opponent=mon(H.CHANSEY, prevent_damage=TURN - 1))
        self.assertIsNone(attack(empty, 1).decision)

    def test_esp_redo_uses_the_last_heads(self):
        """ナツメのESP（わるいナッシーは超なので［サイコリンク］で使える）: 既存のやり直し（同じ枚数）。最後の「おもて」の数だけを使う。"""
        state = esp_board(EXEGGUTOR, (PS, W), opponent=mon(H.CHANSEY, (W, W)))
        card = V113.provider_card(state, EXEGGUTOR)
        asked = attack(state, 1, TL, TL, card=card)
        self.assertEqual(asked.decision.kind, ESP_REDO)
        redone = same_answers(self, asked, (1,), HD, HD)
        self.assertEqual(bases(asked, redone), [40])


class WorstPollenTest(unittest.TestCase):
    def test_one_coin_paralysis_or_confusion(self):
        """さいあくかふん: 目安 30 のあと 1 枚のコインで「おもて」マヒ・「うら」こんらん（既存の DamageThenStatusByCoin。どく／こんらんの型ではない）。"""
        state = board(mon(VILEPLUME, (G, G, W)), opponent=mon(H.CHANSEY))
        self.assertTrue(attack(state, 1, HD).players[1].active.conditions.paralyzed)
        self.assertTrue(attack(state, 1, TL).players[1].active.conditions.confused)
        self.assertEqual(len(flips(state, attack(state, 1, TL))), 1)


class FlightTest(unittest.TestCase):
    def test_mach_flight_and_rolling_attack(self):
        """マッハひこう: 「うら」でワザの失敗（ダメージなし）、「おもて」で 60。まるまるアタック: 「おもて」で次の相手の番にワザのダメージだけを受けない（PreventAttackDamage）。"""
        state = board(mon(DRAGONITE, (W, W, W)), opponent=mon(H.CHANSEY))
        self.assertEqual(bases(state, attack(state, 0, HD)), [60])
        failed = attack(state, 0, TL)
        self.assertEqual((bases(state, failed), last(failed, "attack_failed")["reason"]), ([], "coin"))
        rolling = board(mon(PORYGON2, (W, W, W)), opponent=mon(H.CHANSEY))
        heads = attack(rolling, 0, HD)
        self.assertEqual([type(e).__name__ for e in heads.players[0].active.persistent_effects], ["PreventAttackDamage"])
        self.assertEqual(attack(rolling, 0, TL).players[0].active.persistent_effects, ())


# ---------------------------------------------------------------- 4 章: まるもうけ（上限なしコインのドロー）


class WindfallTest(unittest.TestCase):
    def test_draws_heads_up_to_the_deck(self):
        """「おもて」の数 H と山札の枚数 D の小さいほうを引く。H > D でも、投げるのは「うら」まで（山札の枚数で止めない）。山札がなくなっても負けにしない。"""
        for deck, heads, drawn in ((5, 3, 3), (3, 6, 3), (0, 2, 0), (4, 0, 0)):
            state = board(mon(MEOWTH, (W,)), deck=[W] * deck)
            after = attack(state, 1, *run(heads), bits=True)
            with self.subTest(deck=deck, heads=heads):
                self.assertEqual(len(flips(state, after)), heads + 1)
                draw = new_events(state, after, "draw")[0]
                self.assertEqual(len(draw["cards"]), drawn)
                self.assertEqual(len(after.players[0].deck), deck - drawn)
                self.assertNotEqual(after.phase.value, "game_over")
                audited(self, after)

    def test_draw_is_private(self):
        """引いたカードは相手に見せない（枚数だけ）。"""
        state = board(mon(MEOWTH, (W,)), deck=[W, G, PS])
        after = attack(state, 1, *run(2), bits=True)
        mine = [e for e in visible_log(after, 0) if e["kind"] == "draw" and e["player"] == 0][-1]
        theirs = [e for e in visible_log(after, 1) if e["kind"] == "draw" and e["player"] == 0][-1]
        self.assertEqual(len(mine["cards"]), 2)
        self.assertNotIn("cards", theirs)

    def test_preflight_classes_by_deck_size(self):
        """先読みの組は 0〜D と D 以上（D + 1 の代表）。ESPのない盤面は D + 1、ESPのある盤面は (D + 1) + (D + 1)²。実際の数は代表によらない。"""
        for deck in (0, 3, 7):
            state = board(mon(MEOWTH, (W,)), deck=[W] * deck)
            self.assertEqual(P.draw_classes(deck).representatives, tuple(range(deck + 1)))
            with self.subTest(deck=deck):
                self.assertEqual(preflight_branches(state, UseAttack(0, 1)), [deck + 1])
        esp = esp_board(MEOWTH, (W, W), deck=[W] * 4)
        card = V113.provider_card(esp, MEOWTH)
        self.assertEqual(preflight_branches(esp, UseAttack(0, 1, card=card)), [5 + 25])

    def test_esp_redo_changes_the_final_heads(self):
        """ナツメのESP（色マーカーのニャース）: 最初の「おもて」2 で決定（まだ引かない）。やり直さなければ 2 枚、やり直して 5 枚の「おもて」なら山札 4 枚をすべて引く。"""
        state = esp_board(MEOWTH, (W, W), deck=[W] * 4)
        card = V113.provider_card(state, MEOWTH)
        asked = attack(state, 1, *run(2), bits=True, card=card)
        self.assertEqual(asked.decision.kind, ESP_REDO)
        self.assertEqual(asked.decision.context_value("esp")[6], ("until", "tails"))
        self.assertEqual(new_events(state, asked, "draw"), [])
        kept = same_answers(self, asked, ())
        self.assertEqual(len(new_events(asked, kept, "draw")[0]["cards"]), 2)
        redone = same_answers(self, asked, (1,), *run(5), bits=True)
        self.assertEqual(len(new_events(asked, redone, "draw")[0]["cards"]), 4)
        self.assertEqual(len(redone.players[0].deck), 0)


# ---------------------------------------------------------------- 5 章: アンノーンX


class XPowerTest(unittest.TestCase):
    def x_board(self, *, bench=None, active=None, opponent=None, **kw):
        bench = (mon(UNOWN_X),) if bench is None else bench
        return board(active or mon(UNOWN_X, (PS,)), bench=bench, opponent=opponent or mon(H.CHANSEY), **kw)

    def test_bench_x_adds_at_step_six_and_self_x_at_step_two(self):
        """ベンチのX: 6 段階（弱点・抵抗力のあと）に「おもて」の数 × 10。ワザを使うX 自身: 2 段階（弱点・抵抗力の前）。どちらも特殊能力のコイン（source power）。"""
        state = self.x_board(opponent=mon(H.ONIX))
        holder = state.players[0].bench[0].pokemon_id
        bench = attack(state, 0, *run(2), bits=True, with_power=holder)
        self.assertEqual(steps(state, bench), [{"1 基本となる計算": 10, "6 ［XXXXX[?????]］": 30}])
        self.assertEqual([r for _, r in flips(state, bench, "power")], ["heads", "heads", "tails"])
        self.assertEqual(flips(state, bench, "attack"), [])
        me = state.players[0].active.pokemon_id
        own = attack(state, 0, *run(2), bits=True, with_power=me)
        self.assertEqual(steps(state, own), [{"1 基本となる計算": 10, "2 ［XXXXX[?????]］": 30}])
        audited(self, bench)

    def test_zero_heads_adds_nothing(self):
        state = self.x_board(opponent=mon(H.ONIX))
        after = attack(state, 0, *run(0), bits=True, with_power=state.players[0].bench[0].pokemon_id)
        self.assertEqual(steps(state, after), [{"1 基本となる計算": 10}])
        self.assertEqual(last(after, "group_attack_power_coins")["heads"], 0)

    def test_without_the_power_the_attack_is_plain(self):
        state = self.x_board(opponent=mon(H.ONIX))
        after = attack(state, 0)
        self.assertEqual((steps(state, after), flips(state, after, "power")), ([{"1 基本となる計算": 10}], []))

    def test_who_can_use_it(self):
        """使い手は今の名前が「アンノーン」で、ワザが「めざめるパワー」。非アンノーン（ナツメのフーディンの［サイコリンク］でXのめざめるパワー）・ほかのワザ・相手の場のX・Xでない
        ポケモンは拒否（状態を変えない）。"""
        state = self.x_board(bench=(mon(UNOWN_X), mon(H.RATTATA)))
        rattata = state.players[0].bench[1].pokemon_id
        rejects(self, state, UseAttack(0, 0, with_power=rattata), "ATTACK_POWER_NOT_AVAILABLE", IllegalActionError)
        rejects(self, state, UseAttack(0, 0, with_power=state.players[1].active.pokemon_id), "ATTACK_POWER_NOT_AVAILABLE", IllegalActionError)
        alakazam = board(mon(V113.ALAKAZAM, (PS, PS)), bench=(mon(UNOWN_X, markers=[(MARKER_COLOR, EnergyType.PSYCHIC)]),), opponent=mon(H.CHANSEY))
        holder = alakazam.players[0].bench[0].pokemon_id
        rejects(self, alakazam, UseAttack(0, 0, card=V113.provider_card(alakazam, UNOWN_X), with_power=holder), "ATTACK_POWER_NOT_AVAILABLE", IllegalActionError)
        other_unown = board(mon("neo4-057", (PS,)), bench=(mon(UNOWN_X),), opponent=mon(H.CHANSEY))
        self.assertIsNotNone(last(attack(other_unown, 0, *run(1), bits=True, with_power=other_unown.players[0].bench[0].pokemon_id), "group_attack_power_coins"))

    def test_suppressed_and_history(self):
        """発生源の力が消えている（かがくへんかガス）なら使えない。この番にほかのXの使用の記録があれば使えない（同じ個体の記録には広げない）。"""
        gas = self.x_board(opponent=mon(H.MUK, evolved_from=H.GRIMER))
        rejects(self, gas, UseAttack(0, 0, with_power=gas.players[0].bench[0].pokemon_id), "POWER_SUPPRESSED", IllegalActionError)
        state = self.x_board(bench=(mon(UNOWN_X), mon(UNOWN_X)), opponent=mon(H.ONIX))
        first, second = (b.pokemon_id for b in state.players[0].bench)
        used = state.clone()
        used.trainer_effects = used.trainer_effects + (E.TrainerTurnEffect(kind="group_attack_power_used", player=0, source_card=used.players[0].bench[0].card,
                                                                           card_id=UNOWN_X, created_turn=TURN, expires_turn=TURN, pokemon_id=first),)
        rejects(self, used, UseAttack(0, 0, with_power=second), "POWER_ALREADY_USED", IllegalActionError)
        self.assertIsNotNone(last(attack(used, 0, *run(1), bits=True, with_power=first), "group_attack_power_coins"))

    def test_pre_attack_coins_stop_as_xp1_and_ninja_trick_as_nt1(self):
        """使い手がこんらん（手順 5 のコイン）なら、［XXXXX］のコインとの順番が決まらない（XP1。使わない同じワザは受け付ける）。"""
        confused = self.x_board(active=mon(UNOWN_X, (PS,), confusion=True))
        rejects(self, confused, UseAttack(0, 0, with_power=confused.players[0].bench[0].pokemon_id), "UNRESOLVED_GROUP_POWER_COIN_ORDER")
        self.assertIsNone(attack(confused, 0, HD).decision)

    def test_prevented_damage_question(self):
        """相手がダメージを受けない状態なら、［XXXXX］のコインはダメージの量だけを決めるので v0.4b の問い（使わないなら止めない）。"""
        state = self.x_board(opponent=mon(H.CHANSEY, prevent_damage=TURN - 1))
        rejects(self, state, UseAttack(0, 0, with_power=state.players[0].bench[0].pokemon_id), "UNRESOLVED_PREVENTED_COIN_DAMAGE")
        self.assertIsNone(attack(state, 0).decision)

    def test_record_and_logs(self):
        """宣言のときに使った記録（GROUP_ATTACK_POWER_USED。使った番の終わりに消える）とログ group_attack_power（公開）。"""
        state = self.x_board(opponent=mon(H.ONIX))
        holder = state.players[0].bench[0].pokemon_id
        after = attack(state, 0, *run(1), bits=True, with_power=holder)
        declared = last(after, "group_attack_power")
        self.assertEqual((declared["pokemon_id"], declared["attacker_pokemon_id"], declared["power"]), (holder, state.players[0].active.pokemon_id, "XXXXX[?????]"))
        for viewer in (0, 1, None):
            self.assertTrue(any(e["kind"] == "group_attack_power_coins" for e in visible_log(after, viewer)))


class XClassesTest(unittest.TestCase):
    """［XXXXX］の先読みの組: 追加の段階で key を求める（基本となるダメージの飽和だけで丸めない）。小さい全列挙・長い連続・境目。"""

    def classes(self, state, holder, step):
        res = K.Resolution(state.clone())
        attacker = res.state.players[0].active
        fs = res.open_frame(FrameKind.ATTACK, parent=None, player=0, source_pid=attacker.pokemon_id, attack_key=AttackKey(UNOWN_X, 0))
        element = P.Damage(P.OPP, P.Printed())
        run_ = P.AttackRun(res, fs, (element,), res.state.definitions[UNOWN_X].attacks[0])
        card = res.state.find_pokemon(holder)[1].card
        return unbounded.bonus_classes(run_, element, 10, step, "［XXXXX[?????]］", card)

    def test_keys_cover_every_heads_and_match_real_damage(self):
        """代表の組は 0〜79 のどの数の key もふくむ。同じ key の数は、実際の対戦のダメージ・きぜつが同じ（残りHP 40 のイワークは、ベンチのXの 6 段階で 3 枚以上の「おもて」できぜつ）。"""
        state = board(mon(UNOWN_X, (PS,)), bench=(mon(UNOWN_X),), opponent=mon(H.ONIX, damage=50))
        holder = state.players[0].bench[0].pokemon_id
        classes = self.classes(state, holder, 6)
        for heads in range(80):
            self.assertIn(classes.key_of(heads), classes.keys)
        outcomes = {}
        for heads in range(8):
            after = attack(state, 0, *run(heads), bits=True, with_power=holder)
            outcomes.setdefault(classes.key_of(heads), set()).add(after.players[1].active is None or after.players[1].active.damage)
        self.assertTrue(all(len(values) == 1 for values in outcomes.values()))
        self.assertEqual(classes.key_of(3), classes.key_of(40))
        self.assertNotEqual(classes.key_of(2), classes.key_of(3))
        long = attack(state, 0, *run(30), bits=True, with_power=holder)
        self.assertEqual(last(long, "group_attack_power_coins")["amount"], 300)

    def test_step_two_keys_see_weakness(self):
        """2 段階（X 自身）は弱点の前に入るので、弱点 ×2 の相手では 1 枚ごとに 20 増える。6 段階と同じ key にしない。"""
        weak = board(mon(UNOWN_X, (PS,)), bench=(mon(UNOWN_X),), opponent=mon(H.MACHOP, (F,)))  # ワンリキー（弱点 超・抵抗力なし）
        me = weak.players[0].active.pokemon_id
        holder = weak.players[0].bench[0].pokemon_id
        self.assertEqual(steps(weak, attack(weak, 0, *run(1), bits=True, with_power=me))[0], {"1 基本となる計算": 10, "2 ［XXXXX[?????]］": 20, "3 弱点": 40})
        self.assertEqual(steps(weak, attack(weak, 0, *run(1), bits=True, with_power=holder))[0], {"1 基本となる計算": 10, "3 弱点": 20, "6 ［XXXXX[?????]］": 30})
        self.assertNotEqual(self.classes(weak, me, 2).key_of(1), self.classes(weak, holder, 6).key_of(1))

    def test_preflight_branches_follow_the_classes(self):
        state = board(mon(UNOWN_X, (PS,)), bench=(mon(UNOWN_X),), opponent=mon(H.CHANSEY))
        holder = state.players[0].bench[0].pokemon_id
        reps = self.classes(state, holder, 6).representatives
        self.assertEqual(preflight_branches(state, UseAttack(0, 0, with_power=holder)), [len(reps)])


# ---------------------------------------------------------------- 7 章: 回復の配分と二人のコイン


class WonderAromaTest(unittest.TestCase):
    def aroma(self, me_damage=(20, 20), them_damage=(40,), bench_card=H.RATTATA):
        mine = [mon(IVYSAUR, (G,), damage=me_damage[0])] + [mon(bench_card, damage=d) for d in me_damage[1:]]
        theirs = [mon(H.CHANSEY, damage=them_damage[0])] + [mon(bench_card, damage=d) for d in them_damage[1:]]
        return board(mine[0], bench=mine[1:], opponent=theirs[0], opponent_bench=theirs[1:])

    def test_each_player_flips_and_chooses_their_own(self):
        """使ったプレイヤー → 相手プレイヤーの順に 1 枚ずつ。HH なら、使ったプレイヤーが自分の場の配分を選び、そのあと相手プレイヤーが自分の場の配分を選ぶ（代わりに選ばない）。"""
        state = self.aroma()
        first = attack(state, 0, HD, HD)
        self.assertEqual(flips(state, first), [(0, "heads"), (1, "heads")])
        self.assertEqual((first.decision.kind, first.decision.player), (HEAL_ALLOCATION, 0))
        table = first.decision.context_value("table")
        self.assertEqual(table[0], (2, 1))
        second = same_answers(self, first, (0,))
        self.assertEqual((second.decision.kind, second.decision.player, second.decision.context_value("table")), (HEAL_ALLOCATION, 1, ((3,), (2,), (1,), (0,))))
        done = same_answers(self, second, (1,))
        self.assertEqual(([p.damage for p in done.players[0].in_play()], [p.damage for p in done.players[1].in_play()]), ([0, 10], [20]))
        heals = new_events(state, done, "attack_heal")
        self.assertEqual([(e["player"], e["counters"], e.get("attacker")) for e in heals], [(0, 2, None), (0, 1, None), (1, 2, 0)])
        audited(self, done)

    def test_ht_and_th_are_different(self):
        state = self.aroma()
        ht = attack(state, 0, HD, TL)
        self.assertEqual(ht.decision.player, 0)
        self.assertIsNone(answer(ht, (0,)).decision)
        th = attack(state, 0, TL, HD)
        self.assertEqual(th.decision.player, 1)
        tt = attack(state, 0, TL, TL)
        self.assertIsNone(tt.decision)
        self.assertEqual(new_events(state, tt, "attack_heal"), [])

    def test_zero_is_hz1_and_partial_amounts_are_kept(self):
        """とりのぞけるのに 0 個（表の最後の組）は選べるが選ぶと止める（HZ1。決定は待ったまま）。1 個・2 個（最大より少ない数）は選べる。"""
        state = self.aroma()
        first = attack(state, 0, HD, TL)
        table = first.decision.context_value("table")
        zero = table.index((0, 0))
        self.assertEqual(first.decision.context_value("unresolved_choices")[0], zero)
        self.assertEqual(first.decision.context_value("unresolved_code"), "UNRESOLVED_HEAL_UP_TO_ZERO")
        before = snap(first)
        with self.assertRaises(UnsupportedError) as raised:
            answer(first, (zero,))
        self.assertEqual(raised.exception.code, "UNRESOLVED_HEAL_UP_TO_ZERO")
        self.assertEqual(snap(first), before)
        one = answer(first, (table.index((0, 1)),))
        self.assertEqual([p.damage for p in one.players[0].in_play()], [20, 10])

    def test_no_counters_no_coin(self):
        """自分の場にとりのぞけるカウンターがなければ、そのプレイヤーのコインは決める処理の対象がないので投げない。どちらにもなければ投げない。"""
        mine = board(mon(IVYSAUR, (G,)), opponent=mon(H.CHANSEY, damage=30))
        after = attack(mine, 0, HD)
        self.assertEqual(flips(mine, after), [(1, "heads")])
        self.assertEqual(after.decision.player, 1)
        nobody = board(mon(IVYSAUR, (G,)), opponent=mon(H.CHANSEY))
        self.assertEqual(flips(nobody, attack(nobody, 0)), [])

    def test_caps_and_table_size(self):
        """1 匹からはのっている数まで、合計 3 つまで。6 匹のどれにも 3 つ以上なら、片側の表は 0 をふくめて 84 組（0 を除いて 83）。"""
        self.assertEqual(len(E.heal_allocations((3,) * 6, 3)), 84)
        self.assertEqual(len(E.heal_allocations((1, 3), 3)), 7)
        self.assertEqual(E.heal_zero_rows(E.heal_allocations((1, 3), 3), (1, 3), 3), (6,))
        self.assertEqual(len(E.heal_allocations((2, 2), None)), 9)

    def test_opponent_barrier_blocks_only_that_heal(self):
        """相手のポケモンへの回復は、このワザの効果（``reaches``）。相手の対戦ポケモンが「ワザをうけない」状態なら、相手が選んだ配分でもそのポケモンからはとりのぞかない（ほかは続ける）。"""
        state = with_barrier(mon(IVYSAUR, (G,), damage=20))
        state.players[0].active.damage, state.players[0].bench[0].damage = 40, 20  # バリアーのミュウツーとコラッタ
        first = attack(state, 0, TL, HD)
        self.assertEqual((first.decision.player, first.decision.context_value("heal")[1]), (0, (3, 2)))
        table = first.decision.context_value("table")
        done = answer(first, (table.index((2, 1)),))
        self.assertEqual([p.damage for p in done.players[0].in_play()], [40, 10])
        self.assertEqual([e["pokemon_id"] for e in new_events(first, done, "attack_heal")], [done.players[0].bench[0].pokemon_id])
        audited(self, done)

    def test_preflight_tries_the_first_rows_and_marks_the_others(self):
        """宣言の前の先読みは、配分ごとにはじめの組だけ（両方のコインの 4 通り × はじめの組）。ほかの組の続きは決定を出すときに試し、問いに当たる組は選ぶと止める（v0.94 の答えごとの
        先読み。ここでは、ある組で問いに当たるように一時的に置きかえて確かめる）。6 匹ずつの盤面でも、宣言の前の分岐は 4。"""
        state = self.aroma(me_damage=(30, 30, 30, 30, 30, 20), them_damage=(30, 30, 30, 30, 30, 30), bench_card=H.CHANSEY)
        self.assertEqual(preflight_branches(state, UseAttack(0, 0)), [4])
        original = P.AllocateHeal.resume

        def stopping(self, run, decision, choices):
            if decision.player == 0 and tuple(decision.context_value("table"))[choices[0]] == (1, 0, 0, 0, 0, 0):
                raise run.res.question("prevented_effect_coin", "テストの問い")
            return original(self, run, decision, choices)

        with mock.patch.object(P.AllocateHeal, "resume", stopping):
            first = attack(state, 0, HD, TL)
        table = first.decision.context_value("table")
        marked = {choice: code for choice, code, _ in first.decision.context_value("unresolved_detail")}
        self.assertEqual(marked[table.index((1, 0, 0, 0, 0, 0))], "UNRESOLVED_PREVENTED_EFFECT_COIN")
        self.assertEqual(marked[table.index((0, 0, 0, 0, 0, 0))], "UNRESOLVED_HEAL_UP_TO_ZERO")
        self.assertEqual(len(marked), 2)

    def test_esp_includes_the_opponent_coin(self):
        """ナツメのESP（色マーカーのフシギソウ）: お互いのコインは 1 つのコイントスなので、やり直しは 2 枚を投げ終えてから 1 回だけ聞き、相手のコインを含むのでやり直すは ES1（やり直さないは
        処理する）。"""
        state = esp_board(IVYSAUR, (G, W), opponent=mon(H.CHANSEY, damage=20))
        state.players[0].active.damage = 30
        card = V113.provider_card(state, IVYSAUR)
        asked = attack(state, 0, HD, HD, card=card)
        self.assertEqual(asked.decision.kind, ESP_REDO)
        self.assertEqual(asked.decision.context_value("esp")[6], ("players", (0, 1)))
        self.assertEqual(asked.decision.context_value("unresolved_code"), E.ESP_OPPONENT_COINS_CODE)
        with self.assertRaises(UnsupportedError):
            answer(asked, (1,))
        kept = same_answers(self, asked, ())
        self.assertEqual((kept.decision.kind, kept.decision.player), (HEAL_ALLOCATION, 0))


class BlissPollenTest(unittest.TestCase):
    def test_two_plus_two(self):
        """「おもて」なら自分の控えを 1 匹選び、その控えと自分からそれぞれ 2 つまで（合わせて 4 つまで）。1 つだけも選べる。"""
        state = board(mon(VILEPLUME, (G,), damage=40), bench=(mon(H.RATTATA, damage=20), H.RATTATA))
        chosen = attack(state, 0, HD)
        self.assertEqual((chosen.decision.kind, chosen.decision.options), (SELECT_POKEMON, tuple(b.pokemon_id for b in state.players[0].bench)))
        amounts = same_answers(self, chosen, (state.players[0].bench[0].pokemon_id,))
        table = amounts.decision.context_value("table")
        self.assertEqual(table[0], (2, 2))
        done = same_answers(self, amounts, (0,))
        self.assertEqual([p.damage for p in done.players[0].in_play()], [20, 0, 0])
        one = answer(amounts, (table.index((1, 1)),))
        self.assertEqual([p.damage for p in one.players[0].in_play()], [30, 10, 0])
        for row in ((0, 2), (2, 0), (0, 0)):
            self.assertIn(table.index(row), amounts.decision.context_value("unresolved_choices"))
        audited(self, done)

    def test_parts_that_have_no_target(self):
        """控えがいなければ選ばず自分だけ。選んだ控えにカウンターがなければ自分だけ。自分にカウンターがなければ控えだけ。控えもいなく自分にもなければコインを投げない。"""
        alone = board(mon(VILEPLUME, (G,), damage=30), bench=())
        after = attack(alone, 0, HD)
        self.assertEqual((after.decision.kind, after.decision.context_value("table")), (HEAL_ALLOCATION, ((2,), (1,), (0,))))
        clean = board(mon(VILEPLUME, (G,), damage=30), bench=(H.RATTATA,))
        after = answer(attack(clean, 0, HD), (clean.players[0].bench[0].pokemon_id,))
        self.assertEqual(after.decision.context_value("heal")[0], (clean.players[0].active.pokemon_id,))
        healthy = board(mon(VILEPLUME, (G,)), bench=(mon(H.RATTATA, damage=20),))
        after = answer(attack(healthy, 0, HD), (healthy.players[0].bench[0].pokemon_id,))
        self.assertEqual(after.decision.context_value("table"), ((2,), (1,), (0,)))
        nothing = board(mon(VILEPLUME, (G,)), bench=())
        self.assertEqual(flips(nothing, attack(nothing, 0)), [])
        tails = attack(board(mon(VILEPLUME, (G,), damage=30), bench=(H.RATTATA,)), 0, TL)
        self.assertIsNone(tails.decision)


# ---------------------------------------------------------------- 8 章: トランスポート・じくうへんかん・エアロウイング


class TransportTest(unittest.TestCase):
    def test_draw_then_put_any_card_on_top(self):
        """1 枚引いてから、引いたあとの手札の 1 枚（引いたカードも）を見せずに山札の上に置く。山札は切らない。決定を保存して答えても引くのは 1 回。"""
        state = board(mon(DRAGONITE, (W,)), hand=(W,), deck=[G, PS, L])
        dragonite = state.players[0].active.pokemon_id
        asked = power(state, dragonite)
        self.assertEqual(asked.decision.kind, DECK_TOP_FROM_HAND)
        drawn = new_events(state, asked, "draw")[0]["cards"]
        self.assertEqual(len(drawn), 1)
        self.assertEqual(asked.decision.options, tuple(asked.players[0].hand))
        done = same_answers(self, asked, (drawn[0],))
        self.assertEqual(done.players[0].deck[0], drawn[0])
        self.assertEqual(len(new_events(state, done, "draw")), 1)
        self.assertEqual(len(done.players[0].deck), 3)
        audited(self, done)

    def test_private_choice(self):
        """相手・観戦者には決定の種類と決めるプレイヤーだけ（選べる数・カードを見せない）。置いたカードもログで見せない。"""
        state = board(mon(DRAGONITE, (W,)), hand=(W, G), deck=[PS])
        asked = power(state, state.players[0].active.pokemon_id)
        self.assertEqual(set(observe(asked, 1)["decision"]), {"kind", "player"})
        done = answer(asked, (asked.decision.options[0],))
        theirs = [e for e in visible_log(done, 1) if e["kind"] == "hand_to_deck_top"][-1]
        self.assertNotIn("card", theirs)

    def test_empty_deck_and_empty_hand(self):
        """山札が 0 枚でも手札があれば、引かずに 1 枚を山札の上に置く。山札も手札も 0 枚なら TN1（使う前に止める）。ねむり・マヒ・こんらんなら使えない。番ごとに 1 回。"""
        empty_deck = board(mon(DRAGONITE, (W,)), hand=(W,), deck=[])
        asked = power(empty_deck, empty_deck.players[0].active.pokemon_id)
        self.assertEqual(len(new_events(empty_deck, asked, "draw")[0]["cards"]), 0)
        self.assertEqual(answer(asked, asked.decision.options).players[0].deck, [asked.decision.options[0]])
        nothing = board(mon(DRAGONITE, (W,)), hand=(), deck=[])
        rejects(self, nothing, UsePokemonPower(0, nothing.players[0].active.pokemon_id, 0), "UNRESOLVED_TRANSPORT_WITHOUT_CARDS")
        asleep = board(mon(DRAGONITE, (W,), sleep=True), hand=(W,))
        rejects(self, asleep, UsePokemonPower(0, asleep.players[0].active.pokemon_id, 0), "POKEMON_ASLEEP", IllegalActionError)
        state = board(mon(DRAGONITE, (W,)), hand=(W,), deck=[G, PS])
        once = answer(power(state, state.players[0].active.pokemon_id), (state.players[0].hand[0],))
        rejects(self, once, UsePokemonPower(0, once.players[0].active.pokemon_id, 0), "POWER_ALREADY_USED", IllegalActionError)


class TimeShiftTest(unittest.TestCase):
    def test_heads_puts_a_stadium_from_discard(self):
        """「おもて」なら、トラッシュのスタジアムカードを 1 枚選び、直接場に出す（前のスタジアムはトラッシュ）。「うら」でも使ったことになる。"""
        state = board(mon(PORYGON2, (W,)), discard=(BUMPY_GYM, H.NARROW_GYM), hand=(H.LUCKY_STADIUM,))
        state = apply_kernel(state, PlayTrainer(0, uid(state, H.LUCKY_STADIUM)))
        lucky = state.stadium.card
        porygon = state.players[0].active.pokemon_id
        tails = power(state, porygon, 0, TL)
        self.assertIsNone(tails.decision)
        rejects(self, tails, UsePokemonPower(0, porygon, 0), "POWER_ALREADY_USED", IllegalActionError)
        asked = power(state, porygon, 0, HD)
        self.assertEqual((asked.decision.kind, asked.decision.options), (STADIUM_FROM_DISCARD, tuple(uid(state, c, zone="discard") for c in (BUMPY_GYM, H.NARROW_GYM))))
        done = same_answers(self, asked, (uid(state, BUMPY_GYM, zone="discard"),))
        self.assertEqual(done.cards[done.stadium.card].card_id, BUMPY_GYM)
        self.assertIn(lucky, done.players[0].discard)
        placed = last(done, "stadium_placed")
        self.assertEqual((placed["power"], placed["from_zone"], placed["replaces"]), (f"{PORYGON2}@power0", "discard", lucky))
        self.assertNotIn(done.stadium.card, done.players[0].hand)
        audited(self, done)

    def test_no_stadium_in_discard_is_sx1(self):
        state = board(mon(PORYGON2, (W,)), discard=(W,))
        rejects(self, state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0), "UNRESOLVED_TIME_SHIFT_WITHOUT_TARGET")
        confused = board(mon(PORYGON2, (W,), confusion=True), discard=(BUMPY_GYM,))
        rejects(self, confused, UsePokemonPower(0, confused.players[0].active.pokemon_id, 0), "POKEMON_CONFUSED", IllegalActionError)

    def test_narrow_gym_entry_decision_after_the_power(self):
        """せまいジムを出すと、手札から出したときと同じ「場に出た時」の決定（控えが 5 匹のプレイヤーは 1 匹を手札にもどす）。その答えで特殊能力の処理は終わる。"""
        state = board(mon(PORYGON2, (W,)), bench=(H.RATTATA,) * 5, discard=(H.NARROW_GYM,))
        asked = power(state, state.players[0].active.pokemon_id, 0, HD)
        narrow = answer(asked, asked.decision.options)
        self.assertEqual((narrow.decision.kind, narrow.decision.resume, narrow.decision.context_value("stage")), ("stadium_return_bench", "stadium", "narrow"))
        done = same_answers(self, narrow, (narrow.decision.options[0],))
        self.assertIsNone(done.decision)
        self.assertEqual(len(done.players[0].bench), 4)
        audited(self, done)

    def test_reuse_after_return_is_sx2_and_other_card_is_rs1(self):
        """この番に使ったラッキースタジアムが、別のスタジアムで場をはなれ、［じくうへんかん］で同じ番にもどったら、もう一度使えるかは SX2。同じ名前の別のカードは既存の RS1。"""
        state = board(mon(PORYGON2, (W,)), hand=(H.LUCKY_STADIUM, BUMPY_GYM, H.LUCKY_STADIUM), deck=[W] * 10)
        state = apply_kernel(state, PlayTrainer(0, uid(state, H.LUCKY_STADIUM)))
        used = apply_kernel(with_coin_results(state, TL), UseStadium(0))
        replaced = apply_kernel(used, PlayTrainer(0, uid(used, BUMPY_GYM)))
        asked = power(replaced, replaced.players[0].active.pokemon_id, 0, HD)
        back = answer(asked, (used.stadium.card,))
        self.assertEqual(back.stadium.card, used.stadium.card)
        rejects(self, back, UseStadium(0), "UNRESOLVED_STADIUM_REUSE_AFTER_RETURN")
        other = apply_kernel(used, PlayTrainer(0, uid(used, H.LUCKY_STADIUM)))
        rejects(self, other, UseStadium(0), "UNRESOLVED_STADIUM_REUSE_AFTER_REPLACEMENT")


class AeroWingTest(unittest.TestCase):
    def test_three_outcomes(self):
        """投げない: 目安 40。投げて「おもて」: 基本となるダメージを 80 にしてから弱点（ワンリキーは超の弱点で 160）。「うら」: ワザの失敗（ダメージなし）。投げないならコインはない。"""
        state = board(mon(LUGIA, (W, W, W, W)), opponent=mon(H.MACHOP))
        asked = attack(state, 0)
        self.assertEqual((asked.decision.kind, asked.decision.options, asked.decision.min_choices), (OPTIONAL_COIN, (1,), 0))
        self.assertEqual(new_events(state, asked, "coin_flip"), [])
        declined = same_answers(self, asked, ())
        self.assertEqual((steps(asked, declined), flips(asked, declined)), ([{"1 基本となる計算": 40, "3 弱点": 80}], []))
        heads = same_answers(self, asked, (1,), HD)
        self.assertEqual(steps(asked, heads), [{"1 基本となる計算": 80, "3 弱点": 160}])
        tails = answer(asked, (1,), TL)
        self.assertEqual((steps(asked, tails), last(tails, "attack_failed")["reason"]), ([], "coin"))
        audited(self, heads)

    def test_only_the_flip_answer_stops(self):
        """相手がダメージを受けない状態: 投げるとコインがダメージとワザの失敗だけを決めるので v0.4b の問い（投げるを選ぶと止める）。投げない答えは宣言の前に拒否しない。"""
        state = board(mon(LUGIA, (W, W, W, W)), opponent=mon(H.CHANSEY, prevent_damage=TURN - 1))
        asked = attack(state, 0)
        self.assertEqual(asked.decision.context_value("unresolved_choices"), (1,))
        self.assertEqual(asked.decision.context_value("unresolved_code"), "UNRESOLVED_PREVENTED_COIN_DAMAGE")
        with self.assertRaises(UnsupportedError):
            answer(asked, (1,))
        self.assertIsNone(answer(asked, ()).decision)
        self.assertEqual(preflight_branches(board(mon(LUGIA, (W, W, W, W)), opponent=mon(H.CHANSEY)), UseAttack(0, 0)), [1])

    def test_esp_redo_does_not_reopen_the_choice(self):
        """ナツメのESP（ルギアは超）: 投げると選んだあとに 1 回だけやり直しを聞く。やり直すかだけで、投げる・投げないは選び直さない（運んだ答えを読む）。"""
        with mock.patch.dict(V113.BELOW, BELOW):
            state = V113.board(V113.mon(V113.ALAKAZAM, (W, W, W, W)), bench=(V113.mon(LUGIA),), opponent=mon(H.CHANSEY), hand=(V113.ESP_CARD,))
        played = apply_kernel(state, PlayTrainer(0, uid(state, V113.ESP_CARD)))
        state = answer(played, (played.players[0].active.pokemon_id,))
        card = V113.provider_card(state, LUGIA)
        asked = attack(state, 0, card=card)
        chose = answer(asked, (1,), TL)
        self.assertEqual(chose.decision.kind, ESP_REDO)
        self.assertEqual(chose.decision.context_value("chosen_options"), (("choice", 1),))
        redone = same_answers(self, chose, (1,), HD)
        self.assertEqual(bases(chose, redone), [80])
        kept = answer(chose, ())
        self.assertEqual(last(kept, "attack_failed")["reason"], "coin")


# ---------------------------------------------------------------- 9 章: 保存・観測・形式


class SaveAndFormatTest(unittest.TestCase):
    def test_new_records_write_in_format_26(self):
        """しめつづけるの持続する効果（retreat_cost_increase）と［XXXXX］の使った記録（group_attack_power_used）は、形式 26 で書き出せる（形式を上げない）。"""
        state = board(mon(OCTILLERY, (W, W)), opponent=mon(H.CHANSEY))
        tails = attack(state, 1, TL)
        written = state_to_dict(tails, format_version=26)["players"][1]["active"]["persistent_effects"]
        self.assertEqual([(e["effect"], e["amount"], e["attack"]) for e in written], [("retreat_cost_increase", 1, f"{OCTILLERY}#1")])
        x = board(mon(UNOWN_X, (PS,)), bench=(mon(UNOWN_X),), opponent=mon(H.ONIX))
        after = attack(x, 0, *run(1), bits=True, with_power=x.players[0].bench[0].pokemon_id)
        self.assertEqual(check_invariants(after), [])
        audited(self, after)



class DocumentTest(unittest.TestCase):
    def test_document_records(self):
        import re

        text = DOC.read_text(encoding="utf-8")
        for word in ("A0", "HZ1", "XP1", "SX1", "SX2", "TN1", "UNRESOLVED_HEAL_UP_TO_ZERO", "UNRESOLVED_GROUP_POWER_COIN_ORDER", "UNRESOLVED_TIME_SHIFT_WITHOUT_TARGET",
                     "UNRESOLVED_STADIUM_REUSE_AFTER_RETURN", "UNRESOLVED_TRANSPORT_WITHOUT_CARDS", "_mark_branch_questions", "bonus_classes", "draw_classes", "0.118.0",
                     "GR-2000-P321-DAMAGE-ORDER", "GR-2000-P320-RECOVERY", "UQ-UP-TO-ZERO-CHOICE", "UQ-CARD-USE-WITHOUT-TARGET", "UQ-STATED-COUNT-SHORT", "裁定調査待ち",
                     "1,311", "(66, 24, 42)", "496", "84 組", "7,056", "4,096", "## 13. 検証", "lockstep", "単体のテストだけ",
                     "外部照合・カード画像・ガイドブックの読み直しをしていません", "neo4-082", "neo4-108", "ES2-005", "QSG-055"):
            self.assertIn(word, text)
        for card in V0118:
            self.assertIn(card, text)
        v0117 = (ROOT / "docs" / "retreat-return-active-powers-v0.117.md").read_text(encoding="utf-8")
        self.assertIn("6,558", v0117)  # v0.117 の全体のテストの記録はそのまま
        status = (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(int(re.search(r"^# 実装状況（v0\.1〜v0\.(\d+)）", status, re.MULTILINE).group(1)), 118)
        self.assertIn("## v0.118: 上限なしコイン・攻撃時の能力・回復の配分", status)
        self.assertRegex((ROOT / "README.md").read_text(encoding="utf-8"), r"\n- v0\.118（(今のエンジンの版。)?`kyuura_engine` の版は 0\.118\.0）: 上限なしコイン")
        self.assertIn("### v0.118: 上限なしコイン", (ROOT / "docs" / "rules-2000-02-14.md").read_text(encoding="utf-8"))
        self.assertIn("## v0.118: 上限なしコイン", (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8"))
        optional = (ROOT / "docs" / "optional-trainers-v0.66.md").read_text(encoding="utf-8")
        self.assertEqual(optional.count("v0.118 で訂正"), 2)  # v0.66 の前提の誤りの訂正（過去の記述は消さない）


# ---------------------------------------------------------------- 11 章: ログの監査


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v118_problems``・``v118_close`` と、本体の［じくうへんかん］・［トランスポート］・しめつづけるの「にげる」・回復の分岐）は、エンジンの登録・計算を
    読まずに、処理したワザ・特殊能力の印刷の文面と、ログから組み立てた場・コイン・カードの動きで確かめる。エンジンの処理を一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py
    の局。開発用の seed 50・51。正式な対戦の seed 0〜3 とは別）で、監査がそれを見つける。"""

    GAMES = ((("G118", "X118"), 50), (("W118", "X118"), 50), (("X118", "S118"), 51), (("W118", "G118"), 50), (("M60", "G118"), 51))

    @classmethod
    def problems_for(cls, patcher, *needles, games_=None):
        from tests.log_audit import log_problems
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

        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        used = Counter()
        for labels, seed in self.GAMES:
            result = games.play(labels, seed, keep_state=True)
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual(result["outcome"], "game_over")
                self.assertEqual((result["audit"], log_problems(result["state"])), ({}, []))
            used.update({k for k, v in result["v118"].items() if v})
        self.assertTrue({"x_power_bench", "x_power_self", "heal_own_2", "heal_opponent_2", "heal_two_targets", "retreat_paid_more", "aero_chosen", "aero_wing_heads",
                         "transport_used", "time_shift_placed", "constrict_tails", "bliss_pollen_heads", "windfall_short", "windfall_drew_5"} <= set(used))

    def test_audit_finds_an_extra_windfall_card(self):
        from types import MappingProxyType

        original = P.DrawUntilTails.run

        def one_more(self, run):
            result = original(self, run)
            state = run.state
            last = state.log[-1]
            deck = state.players[run.player].deck
            if last["kind"] == "draw" and deck:
                uid = deck.pop(0)
                state.players[run.player].hand.append(uid)
                state.log = state.log[:-1] + (MappingProxyType({**last, "cards": tuple(last["cards"]) + (uid,)}),)
            return result

        self.assertTrue(self.problems_for(mock.patch.object(P.DrawUntilTails, "run", one_more), "で引いた"))

    def test_audit_finds_a_wrong_x_power_amount(self):
        original = E.group_attack_power_modifier

        def doubled(state, attacker, carried):
            found = original(state, attacker, carried)
            return None if found is None else dataclasses.replace(found, amount=found.amount * 2)

        import dataclasses

        self.assertTrue(self.problems_for(mock.patch.object(E, "group_attack_power_modifier", doubled), "ダメージの記録の変更"))

    def test_audit_finds_a_zero_heal_after_heads(self):
        """エンジンが HZ1（とりのぞけるのに 0 個の組）を止めなければ、「おもて」を出したプレイヤーが 1 つもとりのぞかないログになり、監査が見つける（試験だけ: 表を逆の順にして、
        対戦の手順がはじめに選ぶ組を 0 個の組にする）。"""
        original = E.heal_allocations

        def reversed_table(caps, total):
            return tuple(reversed(original(caps, total)))

        with mock.patch.object(E, "heal_allocations", reversed_table):
            self.assertTrue(self.problems_for(mock.patch.object(E, "heal_zero_rows", lambda table, caps, total: ()), "1 つもとりのぞいていない"))

    def test_audit_finds_a_wrong_retreat_cost_effect(self):
        """しめつづけるの「おもて」でも「にげる」エネルギーをふやす効果を与える・「にげる」で効果を数えない（エンジンの不変条件は量の誤りを先に止めるので、ここでは使わない）。"""
        import dataclasses

        original = P.OpponentRetreatCostIncrease.run

        def ungated(self, run):
            return original(dataclasses.replace(self, gate=None), run)

        constrict_heads = ((("S118", "W118"), 50), (("W118", "S118"), 51), (("P31", "W118"), 50))  # しめつづけるの「おもて」のある局
        self.assertTrue(self.problems_for(mock.patch.object(P.OpponentRetreatCostIncrease, "run", ungated), "の「おもて」で、「にげる」エネルギーをふやす効果を与えた",
                                          games_=constrict_heads))
        original_increase = E.RetreatCost._increase

        def not_counted(self):  # 効果は記録するが、増やす数に数えない（対戦の手順は、数の変わる「にげる」を宣言する）
            return original_increase.fget(self) - sum(amount for _, amount in self.effect_increases)

        self.assertTrue(self.problems_for(mock.patch.object(E.RetreatCost, "_increase", property(not_counted)), "にげるエネルギー"))

    def test_audit_finds_time_shift_on_tails_and_transport_drawing_two(self):
        from kyuura_engine.zones import draw_cards

        def always(self, state, use):
            E._power_coin(state, use)
            E.push_power_decision(state, use, kind=STADIUM_FROM_DISCARD, player=use.player, options=self.candidates(state, use.player))

        self.assertTrue(self.problems_for(mock.patch.object(E.CoinPutStadiumFromDiscard, "resolve", always), "じくうへんかん", "特殊能力のコイン（neo4-097@power0）"))

        def two(self, state, use):
            side = state.players[use.player]
            draw_cards(state, use.player, min(2, len(side.deck)))
            E.push_power_decision(state, use, kind=DECK_TOP_FROM_HAND, player=use.player, options=tuple(side.hand))

        self.assertTrue(self.problems_for(mock.patch.object(E.DrawThenPutHandCardOnDeckTop, "resolve", two), "特殊能力の宣言"))

    def test_audit_finds_aero_wing_heads_without_the_set_damage(self):
        original = P.SetOnHeads.value

        def printed(self, run, flips):
            return run.attack.damage if original(self, run, flips) == self.amount else original(self, run, flips)

        self.assertTrue(self.problems_for(mock.patch.object(P.SetOnHeads, "value", printed), "「おもて」の基本となるダメージ"))


if __name__ == "__main__":
    unittest.main()
