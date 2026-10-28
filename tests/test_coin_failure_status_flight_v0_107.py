"""v0.107（docs/coin-failure-status-flight-v0.107.md）: コインによる成否・特殊状態・防護のポケモンの 9 枚（ワザ 16）と、失敗のコインで決まるどく・じばく・防護、ダメージのあとのコインで
相手か自分がこんらんになる処理、(マヒ, どく) の組の 1 枚のコインの特殊状態。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面。9 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録
（GR-2000-P309-ATTACK-PROCEDURE・GR-2000-P321-ATTACK-DAMAGE・GR-2000-P321-PREVENTED-ELEMENTS・GR-2000-P322-PERSISTENT-EFFECTS・p.323 の「12 ワザの失敗」・CR-EFFECTS-AFTER-KO・
CR-STICKY-VS-PREVENTED・CR-GAMBLE-VS-PREVENTED・CR-TRANSPARENCY-NOT-FAILURE・UQ-COIN-IN-NULLIFIED-ELEMENT（v0.4b・HC3・T19b）・v0.103 の発生元）。英語版の文面・現代のルール・後年の裁定は
持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の
結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.107``）。
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
    EndTurn,
    PlayTrainer,
    ResolveDecision,
    UseAttack,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    DAMAGE_REDUCTION,
    DAMAGE_STEP_ORDER,
    ENERGY_DRAIN_DISCARD,
    ESP_REDO,
    REACTION_SWITCH,
    SELECT_ATTACK,
    SPLIT_FROM_DECK,
)
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.preflight import MAX_BRANCHES
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import AttackBarrier, DamageReduction, ZeroDamageBelow
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.log_audit import LATEST_FORMAT, log_problems
from tests.release_catalog import cards_after, cards_before
from tests.test_counter_keep_energy_protection_v0_101 import attack
from tests.test_counts_coins_compositions_v0_106 import with_effects
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_unown_family_powers_v0_96 import TURN, board, same_answers, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "coin-failure-status-flight-v0.107.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, F, L, G, PS = H.WATER, H.FIGHTING, H.LIGHTNING, H.GRASS, H.PSYCHIC
WEEDLE, PINECO, URSARING, PSYDUCK, SHELLDER = "neo2-002", "neo2-005", "neo2-051", "neo4-026", "GD2-006"
FLYING_18, FLYING_42, FLYING_63, BUTTERFREE = "PR1-018", "PR1-042", "PR1-063", "SI-003"
V0107 = (WEEDLE, PINECO, URSARING, PSYDUCK, SHELLDER, FLYING_18, FLYING_42, FLYING_63, BUTTERFREE)
V0107_ATTACKS = [AttackKey(card, index) for card in V0107 for index in range(1 if card in (WEEDLE, PINECO) else 2)]
FLIERS = ((FLYING_18, 1), (FLYING_42, 1), (FLYING_63, 1), (BUTTERFREE, 0))
MEW, TENTACRUEL, KOFFING, KOGAS_MUK, SABRINAS_JYNX, GEODUDE, VOLTORB = "PR1-005", "GD2-004", H.KOFFING_ES2, H.KOGAS_MUK, "GD6-012", "ES1-023", "ES2-016"
CHANSEY, RATTATA, MACHOP, MACHAMP, CLEFABLE, CLEFAIRY, HAUNTER = H.CHANSEY, H.RATTATA, H.MACHOP, H.MACHAMP, H.CLEFABLE, H.CLEFAIRY, H.HAUNTER
BELOW = {URSARING: ["neo2-048"], BUTTERFREE: ["ES1-002", "ES1-003"], TENTACRUEL: ["GD2-003"], KOGAS_MUK: [H.KOGAS_GRIMER], MACHAMP: [MACHOP, H.MACHOKE],
         CLEFABLE: [CLEFAIRY], HAUNTER: [H.GASTLY]}

# 依頼で示された固定データの日本語（写しの文面と照らす。広い正規化をしない）。(HP, タイプ, 段階, 弱点, 抵抗力, にげる, 進化元, (名前, 必要なエネルギー, ダメージの目安, 説明), ...)
SPIKE_STAB = "相手を「どく」状態にする。コインを投げて「うら」なら、このワザは失敗する。"
SUDDEN_EXPLOSION = "自分にも40ダメージ。おたがいの控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。コインを投げて「うら」なら、このワザは失敗する。"
PARALYZE_ELSE_FAIL = "相手を「マヒ」状態にする。コインを投げて「うら」なら、このワザは失敗する。"
DOUBLE_LARIAT = "コインを2枚投げ、「おもて」の数×40のダメージ。"
MIGRAINE = "コインを投げて「おもて」なら、相手を「こんらん」状態にする。「うら」なら、自分を「こんらん」状態にする。"
THUNDERSHOCK = "コインを投げて「おもて」なら、相手を「マヒ」状態にする。"
THUNDER_JOLT = "コインを投げて「うら」なら、自分にも10ダメージ。"
FLY_18 = "次の相手の番に、このカードは相手のワザをうけない。コインを投げて「うら」なら、このワザは失敗する。"
FLY_42 = "コインを投げて「うら」ならこのワザは失敗する。「おもて」なら、次の相手の番、このカードはワザによるダメージや効果を受けない。"
FLY_63 = "コインを投げて「うら」なら、このワザは失敗する。「おもて」なら次の相手の番、このカードは相手のワザによるダメージや効果を受けない。"
FLY_SI = "コインを投げて「うら」なら、このワザは失敗する。「おもて」なら、次の相手の番、このカードはワザによるダメージや効果を受けない。"
RAINBOW_POWDER = "コインを投げる「おもて」なら、相手を「マヒ」状態に、「うら」ならどく状態にする。"
C3 = ("colorless",) * 3
QUOTED = {
    WEEDLE: (40, "grass", "basic", "fire", None, 1, None, ("とげでつつく", ("grass",), "20", SPIKE_STAB)),
    PINECO: (40, "grass", "basic", "fire", None, 2, None, ("とつぜんじばく", ("grass",), "40", SUDDEN_EXPLOSION)),
    URSARING: (80, "colorless", "stage1", "fighting", ("psychic", 30), 3, "ヒメグマ", ("ヘッドプレス", ("colorless",) * 2, "20", PARALYZE_ELSE_FAIL),
               ("ダブルラリアット", ("colorless",) * 4, "40×", DOUBLE_LARIAT)),
    PSYDUCK: (50, "water", "basic", "lightning", None, 1, None, ("みずかけ", ("water",), "10", None), ("へんずつう", ("psychic", "colorless"), "20", MIGRAINE)),
    SHELLDER: (40, "water", "basic", "lightning", None, 1, None, ("たいあたり", ("colorless",), "10", None), ("からではさむ", ("water", "colorless"), "20", PARALYZE_ELSE_FAIL)),
    FLYING_18: (40, "lightning", "basic", None, ("fighting", 30), 1, None, ("でんきショック", ("lightning",), "10", THUNDERSHOCK), ("そらをとぶ", C3, "30", FLY_18)),
    FLYING_42: (40, "lightning", "basic", None, ("fighting", 30), 1, None, ("でんげき", ("lightning",), "20", THUNDER_JOLT), ("そらをとぶ", C3, "30", FLY_42)),
    FLYING_63: (40, "lightning", "basic", None, ("fighting", 30), 1, None, ("でんきショック", ("lightning",), "10", THUNDERSHOCK), ("そらをとぶ", C3, "30", FLY_63)),
    BUTTERFREE: (80, "grass", "stage2", "fire", ("fighting", 30), 1, "トランセル", ("そらをとぶ", C3, "30", FLY_SI),
                 ("レインボーパウダー", ("grass", "grass", "colorless"), "20", RAINBOW_POWDER)),
}
EXPECTED = {
    (WEEDLE, 0): E.FailOnTailsDamageThenPoison(), (PINECO, 0): E.FailOnTailsSelfDestruct(40, 10),
    (URSARING, 0): E.DamageAndParalyzeOnHeadsElseFail(), (URSARING, 1): E.CoinFlipDamage(coins=2, damage_per_heads=40),
    (PSYDUCK, 0): E.DamageOnly(), (PSYDUCK, 1): E.DamageThenConfuseOpponentOrSelf(),
    (SHELLDER, 0): E.DamageOnly(), (SHELLDER, 1): E.DamageAndParalyzeOnHeadsElseFail(),
    (FLYING_18, 0): E.ParalyzeOnHeads(), (FLYING_18, 1): E.FailOnTailsDamageThenSelfBarrier(),
    (FLYING_42, 0): E.SelfDamageOnTails(10), (FLYING_42, 1): E.FailOnTailsDamageThenSelfBarrier(),
    (FLYING_63, 0): E.ParalyzeOnHeads(), (FLYING_63, 1): E.FailOnTailsDamageThenSelfBarrier(),
    (BUTTERFREE, 0): E.FailOnTailsDamageThenSelfBarrier(), (BUTTERFREE, 1): E.DamageThenStatusByCoin(E.PARALYSIS, E.POISON),
}
NEW_TYPES = (E.FailOnTailsDamageThenPoison, E.FailOnTailsSelfDestruct, E.FailOnTailsDamageThenSelfBarrier, E.DamageThenConfuseOpponentOrSelf)


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def answer(state, choices, *coins, player=None):
    d = state.decision
    return apply_kernel(with_coin_results(state, *coins) if coins else state, ResolveDecision(d.player if player is None else player, d.id, tuple(choices)))


def kinds(before, after, *names):
    return [e["kind"] for e in new_events(before, after, *names)]


def coins_of(before, after):
    return [e["result"] for e in new_events(before, after, "coin_flip") if e.get("source") == "attack"]


def pid_of(state):
    """場のポケモンのいちばん上のカード → 場のポケモンの番号（ログ ``damage`` は ``pokemon_id`` を持たないので、ワザの前の場から引く）。"""
    return {p.card: p.pokemon_id for player in state.players for p in player.in_play()}


def damages(before, after):
    """ワザのダメージの (受けたプレイヤー, ポケモンの番号, 基本となるダメージ, 最終ダメージ)（返す効果のダメージを除く。ログの順）。"""
    ids = pid_of(before)
    return [(e["player"], ids.get(e["pokemon"]), e["steps"][0][1], e["amount"]) for e in new_events(before, after, "damage") if not e.get("retaliation")]


def amounts(before, after, player):
    """プレイヤー ``player`` のポケモンが受けた、ワザのダメージの (基本となるダメージ, 最終ダメージ)。"""
    return [(base, amount) for owner, _, base, amount in damages(before, after) if owner == player]


def conditions(before, after):
    """付けた特殊状態の (ポケモンの番号, 特殊状態)。"""
    return [(e["pokemon_id"], e["condition"]) for e in new_events(before, after, "special_condition") if not e.get("already")]


def barriers(before, after):
    return [e["pokemon_id"] for e in new_events(before, after, "persistent_effect_added") if e["persistent_effect"] == AttackBarrier.kind]


def with_barrier(state, player=1):
    """プレイヤー ``player`` のバトル場のポケモンに、今の番にはたらくバリアー（「ワザをうけない」）を置く（v0.106 のテストの ``with_effects`` と同じ形）。"""
    pokemon = state.players[player].active
    effect = AttackBarrier(pokemon.card, player, TURN - 1, TURN)
    pokemon.persistent_effects = (*pokemon.persistent_effects, effect)
    current, state.turn_number = state.turn_number, effect.created_turn
    state.add_event("persistent_effect_added", player=player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, persistent_effect=effect.kind,
                    source_card=effect.source_card, source_player=effect.source_player, active_turn=effect.active_turn, effect="PMCG1-041#1")
    state.turn_number = current
    return state


def use(state, card_id, index):
    return E.AttackUse(state.current_player, state.players[state.current_player].active.pokemon_id, AttackKey(card_id, index))


def uid_in_hand(state, card_id, player=0):
    return next(u for u in state.players[player].hand if state.cards[u].card_id == card_id)


def charity(state):
    """お上品攻撃（手札）をプレイヤー 1 の対戦ポケモンにつける（ワザのダメージを減らす量の決定を出す）。"""
    return apply_kernel(state, PlayTrainer(0, uid_in_hand(state, H.CHARITY)))


# ---------------------------------------------------------------- 1・2・3 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_entries_and_printed_texts(self):
        """9 枚・16 のワザの名前・必要なエネルギー・ダメージの目安・説明と、HP・タイプ・段階・弱点・抵抗力・にげる・進化元は依頼の日本語・固定データと同じ。特殊能力は 0。
        コダックのへんずつうの必要なエネルギーは「超無」のまま（タイプから直さない）。"""
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_107"]), V0107)
        self.assertEqual(len(V0107_ATTACKS), 16)
        for card, (hp, color, stage, weakness, resistance, retreat, below, *attacks) in QUOTED.items():
            definition = pool.definitions[card]
            with self.subTest(card=card):
                self.assertEqual((definition.hp, definition.pokemon_type.value, definition.stage, definition.powers), (hp, color, stage, ()))
                self.assertEqual((None if definition.weakness is None else definition.weakness.value, definition.weakness_multiplier), (weakness, None))
                self.assertEqual(None if definition.resistance is None else (definition.resistance.value, definition.resistance_value), resistance)
                self.assertEqual((definition.retreat_cost, definition.evolves_from), (retreat, below))
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
        self.assertEqual(pool.definitions[PSYDUCK].pokemon_type.value, "water")

    def test_names_and_evolution_sources(self):
        """「そらをとぶピカチュウ」を「ピカチュウ」に正規化しない。リングマ（ヒメグマから）・バタフリー（トランセルから）の進化元は登録済み。プロモのレベル・図鑑番号の欠けは補わない。"""
        pool = load_card_pool()
        cards = {c["id"]: c for c in read_extract()["cards"]}
        for card in (FLYING_18, FLYING_42, FLYING_63):
            self.assertEqual(pool.definitions[card].name_ja, "そらをとぶピカチュウ")
        names = {d.name_ja: c for c, d in pool.definitions.items() if c in pool.playable_ids}
        self.assertIn("ヒメグマ", names)
        self.assertIn("トランセル", names)
        self.assertEqual(pool.definitions[BUTTERFREE].stage1_evolves_from, ("キャタピー",))
        self.assertEqual({card: cards[card]["data_gaps"] for card in V0107},
                         {WEEDLE: [], PINECO: [], URSARING: [], PSYDUCK: [], SHELLDER: ["jp_print.level"], FLYING_18: ["jp_print.level"],
                          FLYING_42: ["pokemon.dex", "jp_print.level"], FLYING_63: ["jp_print.level"], BUTTERFREE: []})

    def test_same_group_shares_only_the_same_text(self):
        """PR1-018 と PR1-063 は同じカードの組（SC-PR1-018）だが、そらをとぶの文面が違う（日本語の pokemon 欄は完全一致しない）。登録ごと複製せず、文面の同じでんきショックの登録だけを
        共有し、そらをとぶはそれぞれの原文で同じ処理の値を登録する。PR1-042 はどの組にも入らない。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        self.assertEqual((cards[FLYING_18]["same_card_group"], cards[FLYING_63]["same_card_group"], cards[FLYING_42]["same_card_group"]),
                         ("SC-PR1-018", "SC-PR1-018", None))
        self.assertNotEqual(cards[FLYING_18]["pokemon"], cards[FLYING_63]["pokemon"])
        self.assertIs(DEFAULT_EFFECTS.attack_entry(FLYING_18, 0), DEFAULT_EFFECTS.attack_entry(FLYING_63, 0))
        self.assertIsNot(DEFAULT_EFFECTS.attack_entry(FLYING_18, 1), DEFAULT_EFFECTS.attack_entry(FLYING_63, 1))
        texts = {card: DEFAULT_EFFECTS.attack_entry(card, index).text_ja for card, index in FLIERS}
        self.assertEqual(texts, {FLYING_18: FLY_18, FLYING_42: FLY_42, FLYING_63: FLY_63, BUTTERFREE: FLY_SI})
        self.assertEqual(len(set(texts.values())), 4)
        # v0.116: ピジョン（ES3-032）の書き方を受け付ける文のあとに加えた（docs/energy-movement-attachment-devolution-v0.116.md 2.2 節）。v0.107 の 4 つは変えない
        self.assertEqual(E.FLY_TEXTS[:4], (FLY_18, FLY_42, FLY_63, FLY_SI))
        for table in (E.SAME_DATA_CARDS_V0_104, E.SAME_DATA_CARDS_V0_106):
            self.assertFalse(set(V0107) & (set(table) | set(table.values())))
        for card in (WEEDLE, PINECO, URSARING, PSYDUCK, SHELLDER, BUTTERFREE):
            self.assertIsNone(cards[card]["same_card_group"], card)

    def test_programs(self):
        """新しい型の要素の並び（既存の要素だけ）。とつぜんじばくは失敗のコインのあとに、じばく（弱点・抵抗力に関係ない書き方）と同じダメージのまとまり。カードの id による分岐はない。"""
        self_destruct = P.BUILDERS[E.SelfDestruct](E.SelfDestruct(40, 10, True))
        builders = {
            E.FailOnTailsDamageThenPoison(): (P.FailOnTails(), P.Damage(P.OPP, P.Printed()), P.Status(E.POISON)),
            E.FailOnTailsSelfDestruct(40, 10): (P.FailOnTails(), *self_destruct),
            E.FailOnTailsDamageThenSelfBarrier(): (P.FailOnTails(), P.Damage(P.OPP, P.Printed()), P.SelfPersistent(AttackBarrier.kind)),
            E.DamageThenConfuseOpponentOrSelf(): (P.Damage(P.OPP, P.Printed()), P.Coin("coin"), P.Status(E.CONFUSION, gate=("coin", HD)),
                                                  P.Status(E.CONFUSION, target=P.SELF, gate=("coin", TL))),
            E.DamageAndParalyzeOnHeadsElseFail(): (P.ReparalysisGuard(), P.FailOnTails(), P.Damage(P.OPP, P.Printed()), P.Status(E.PARALYSIS)),
            E.DamageThenStatusByCoin(E.PARALYSIS, E.POISON): (P.Damage(P.OPP, P.Printed()),
                                                             P.Status(E.PARALYSIS, local_coin=HD, otherwise=E.POISON, reparalysis_check=True)),
        }
        self.assertEqual(self_destruct, (P.Damage(P.OPP, P.Printed()), P.Damage(P.SELF, P.Fixed(40), name="self_damage"),
                                         P.BenchDamage(P.Fixed(10), weakness_resistance=False), P.BenchDamage(P.Fixed(10), weakness_resistance=False, own=True)))
        for effect, program in builders.items():
            with self.subTest(effect=effect):
                self.assertEqual(P.BUILDERS[type(effect)](effect), program)
                self.assertEqual(P.compile_attack(effect), program)
        for cls in NEW_TYPES:
            self.assertIn(cls, H.ATTACK_TYPES_SINCE_V0_17)
            self.assertIs(cls.resolve, E.AttackEffect.resolve)
        # 相手への効果の宣言（G37 の確かめに使う）に、どく・こんらんを漏らさない。防護・自分へのダメージ・控えへのダメージは相手の対戦ポケモンへの効果ではない
        self.assertEqual({cls.__name__: cls.opponent_effect_elements for cls in NEW_TYPES},
                         {"FailOnTailsDamageThenPoison": (E.POISON,), "FailOnTailsSelfDestruct": (), "FailOnTailsDamageThenSelfBarrier": (),
                          "DamageThenConfuseOpponentOrSelf": (E.CONFUSION,)})
        self.assertEqual(E.DamageThenStatusByCoin(E.PARALYSIS, E.POISON).opponent_effect_elements, (E.PARALYSIS, E.POISON))
        # 失敗のコインがあることは、要素の並びから求める（クチバシティジムの VM1 などの既存の確かめ）
        for effect in (E.FailOnTailsDamageThenPoison(), E.FailOnTailsSelfDestruct(40, 10), E.FailOnTailsDamageThenSelfBarrier()):
            self.assertTrue(P.program_may_fail(P.compile_attack(effect)))
        self.assertFalse(P.program_may_fail(P.compile_attack(E.DamageThenConfuseOpponentOrSelf())))

    def test_reused_types_match_the_printed_text(self):
        """既存の型の 6 つのワザ。でんきショック（ParalyzeOnHeads）・でんげき（SelfDamageOnTails）の確かめは形だけなので、意味は全文で照らす（既存の型の確かめは一括で直さない）。
        ヘッドプレス・からではさむは、DamageAndParalyzeOnHeadsElseFail の書き方に明示して加えた 1 通りだけで通る。"""
        pool = load_card_pool()
        lariat = pool.definitions[URSARING].attacks[1]
        self.assertEqual(E.CoinFlipDamage(coins=2, damage_per_heads=40).check(lariat), [])
        for wrong in (E.CoinFlipDamage(coins=3, damage_per_heads=40), E.CoinFlipDamage(coins=2, damage_per_heads=30)):
            self.assertNotEqual(wrong.check(lariat), [])
        for card in (FLYING_18, FLYING_63):
            self.assertEqual(pool.definitions[card].attacks[0].text_ja, THUNDERSHOCK)  # 既存の ParalyzeOnHeads の登録と同じ全文
            self.assertEqual(E.ParalyzeOnHeads().check(pool.definitions[card].attacks[0]), [])
        self.assertEqual(pool.definitions[FLYING_42].attacks[0].text_ja, THUNDER_JOLT)  # 第1弾のピカチュウのでんげき（p.125 の最新の説明）と同じ全文
        self.assertEqual(E.SelfDamageOnTails(10).check(pool.definitions[FLYING_42].attacks[0]), [])
        self.assertEqual(E.PARALYZE_ELSE_FAIL_TEXTS[1], PARALYZE_ELSE_FAIL)
        for card in (URSARING, SHELLDER):
            printed = pool.definitions[card].attacks[0 if card == URSARING else 1]
            self.assertEqual(E.DamageAndParalyzeOnHeadsElseFail().check(printed), [])
            for changed in (PARALYZE_ELSE_FAIL.replace("「うら」", "「おもて」"), PARALYZE_ELSE_FAIL.replace("「マヒ」", "「どく」"),
                            PARALYZE_ELSE_FAIL.replace("このワザは失敗する", "相手にダメージを与えない"), PARALYZE_ELSE_FAIL[:-1]):
                self.assertNotEqual(E.DamageAndParalyzeOnHeadsElseFail().check(dataclasses.replace(printed, text_ja=changed)), [])
        for card, index in ((PSYDUCK, 0), (SHELLDER, 0)):
            self.assertEqual(E.DamageOnly().check(pool.definitions[card].attacks[index]), [])

    def test_new_texts_are_bound_to_their_values(self):
        """新しい型・書き方は値と結び付けた完全な一致だけ。こうそくいどうとそらをとぶ・「うら」で相手へダメージなし（こまったねんりき）とへんずつう・「おもて」どく／「うら」マヒと
        レインボーパウダーの取り違えを拒否する。"""
        pool = load_card_pool()
        stab = pool.definitions[WEEDLE].attacks[0]
        self.assertEqual(E.FailOnTailsDamageThenPoison().check(stab), [])
        self.assertNotEqual(E.DamageAndParalyzeOnHeadsElseFail().check(stab), [])
        self.assertNotEqual(E.FailOnTailsDamage().check(stab), [])
        self.assertNotEqual(E.FailOnTailsDamageThenPoison().check(pool.definitions[URSARING].attacks[0]), [])
        boom = pool.definitions[PINECO].attacks[0]
        self.assertEqual(E.FailOnTailsSelfDestruct(40, 10).check(boom), [])
        for wrong in (E.FailOnTailsSelfDestruct(40, 20), E.FailOnTailsSelfDestruct(30, 10), E.SelfDestruct(40, 10, True), E.FailOnTailsSpreadBothThenSelfCannotAttack(10)):
            self.assertNotEqual(wrong.check(boom), [])
        self.assertNotEqual(E.FailOnTailsSelfDestruct(40, 10).check(dataclasses.replace(boom, text_ja=SUDDEN_EXPLOSION.replace("おたがい", "お互い"))), [])
        quick_attack = "コインを投げて「おもて」なら、次の相手の番、このカードはワザによるダメージや効果を受けない。"  # こうそくいどう（v0.70 の書き方）
        self.assertIn(quick_attack, E.SELF_BARRIER_ON_HEADS_TEXTS)
        for card, index in FLIERS:
            fly = pool.definitions[card].attacks[index]
            with self.subTest(card=card):
                self.assertEqual(E.FailOnTailsDamageThenSelfBarrier().check(fly), [])
                self.assertNotEqual(E.DamageThenSelfBarrierOnHeads().check(fly), [])
                self.assertNotEqual(E.FailOnTailsDamage().check(fly), [])
                self.assertNotEqual(E.FailOnTailsDamageThenSelfBarrier().check(dataclasses.replace(fly, text_ja=quick_attack)), [])
        self.assertNotEqual(E.FailOnTailsDamageThenSelfBarrier().check(dataclasses.replace(pool.definitions[FLYING_18].attacks[1],
                                                                                          text_ja=FLY_18.replace("「うら」", "「おもて」"))), [])
        migraine = pool.definitions[PSYDUCK].attacks[1]
        sabrinas = pool.definitions[H.SABRINAS_PSYDUCK].attacks[1]  # ナツメのコダックの「こまったねんりき」（「うら」なら相手にダメージを与えない）
        self.assertEqual(E.DamageThenConfuseOpponentOrSelf().check(migraine), [])
        self.assertNotEqual(E.CoinDamageAndConfuseElseSelfConfuse().check(migraine), [])
        self.assertNotEqual(E.DamageThenConfuseOpponentOrSelf().check(sabrinas), [])
        self.assertNotEqual(E.DamageThenConfuseBoth().check(migraine), [])
        rainbow = pool.definitions[BUTTERFREE].attacks[1]
        self.assertEqual(E.DamageThenStatusByCoin(E.PARALYSIS, E.POISON).check(rainbow), [])
        for wrong in (E.DamageThenStatusByCoin(E.POISON, E.PARALYSIS), E.DamageThenPoisonOrParalyze(), E.DamageThenStatusByCoin(E.PARALYSIS, E.SLEEP)):
            self.assertNotEqual(wrong.check(rainbow), [])
        self.assertEqual(dict(E.RAINBOW_POWDER_TEXTS), {(E.PARALYSIS, E.POISON): (RAINBOW_POWDER,)})
        # 既存のへんなこなの書き方（v0.93。(こんらん, ねむり) の組だけ）は変えない
        self.assertEqual(dict(E.STRANGE_POWDER_COMMA_TEXTS), {(E.CONFUSION, E.SLEEP): ("コインを投げ、「おもて」なら相手を「こんらん」状態に、「うら」なら「ねむり」状態にする。",)})

    def test_unregistered_without_the_v0_107_entries(self):
        """今回の登録だけを除くと、ちょうど 9 枚が未対応にもどる（ほかのカードは失われない）。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V0107_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V0107))
        self.assertEqual(set(V0107) & set(cards_before(read_extract(), "0.107")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.106")) & set(cards_before(read_extract(), "0.108")), set(V0107))

    def test_extract_keeps_sources(self):
        """転記元はビードル・クヌギダマ・リングマが nazonobasho.com、コダックがポケモンWiki、5 枚が pcg-search.com（同じ転記元との一致を独立した照合にしない）。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        hosts = {card: cards[card]["ja_text_source"].split("/")[2] for card in V0107}
        self.assertEqual(hosts, {WEEDLE: "nazonobasho.com", PINECO: "nazonobasho.com", URSARING: "nazonobasho.com", PSYDUCK: "wiki.pokemonwiki.com",
                                 **{card: "pcg-search.com" for card in (SHELLDER, FLYING_18, FLYING_42, FLYING_63, BUTTERFREE)}})

    def test_adoption_records(self):
        """9 件の採用の記録（kyuura 73a1690・外部照合なし・kyuura の記録なし）。処理に使う文面は印刷の文面（説明文のないみずかけ・たいあたりは持たない）。"""
        sources = json.loads((ROOT / "kyuura_engine/data/card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine/data/research_links.json").read_text(encoding="utf-8"))["latest_descriptions"]["adopted_printed_text"]
        for card in V0107:
            record = sources[card]
            parts = [f"attack/{i}" for i, a in enumerate(QUOTED[card][7:]) if a[3] is not None]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"], record["external_checks"], record["issues"]),
                                 ("kyuura_data", "adopted", "73a169063463bbf7bcaa3137d70cbf9721d11534", [], [], []))
                self.assertEqual(record["play_text"], {part: "kyuura_printed_text" for part in parts})
                for part in parts:
                    self.assertIn(f"{card}/{part}", links)
        for card in (PSYDUCK, SHELLDER):
            self.assertNotIn(f"{card}/attack/0", links)
        self.assertEqual(len([key for key in links if key.split("/")[0] in V0107]), 14)


# ---------------------------------------------------------------- 4.1 節: ワザ全体の失敗（とげでつつく・ヘッドプレス・からではさむ）


class FailureStatusTest(unittest.TestCase):
    CASES = ((WEEDLE, 0, (G,), E.POISON), (URSARING, 0, (W, W), E.PARALYSIS), (SHELLDER, 1, (W, W), E.PARALYSIS))

    def test_heads_damage_then_status_tails_fails(self):
        """「おもて」なら目安のダメージのあとに特殊状態、「うら」ならワザ全体が失敗（ダメージも特殊状態もない。ワザは使ったことになり番が終わる。エネルギーはトラッシュしない）。"""
        for card, index, energy, condition in self.CASES:
            state = board(mon(card, energy), opponent=mon(CHANSEY))
            target = state.players[1].active.pokemon_id
            heads = attack(state, index, HD)
            tails = attack(state, index, TL)
            with self.subTest(card=card):
                self.assertEqual(coins_of(state, heads), ["heads"])
                self.assertEqual((amounts(state, heads, 1), conditions(state, heads)), ([(20, 20)], [(target, condition)]))
                self.assertEqual(kinds(state, heads, "attack_failed"), [])
                self.assertEqual(coins_of(state, tails), ["tails"])
                self.assertEqual([(e["reason"]) for e in new_events(state, tails, "attack_failed")], ["coin"])
                self.assertEqual(kinds(state, tails, "damage", "damage_prevented", "special_condition", "discard_energy"), [])
                self.assertEqual((tails.current_player, len(tails.players[0].active.energy)), (1, len(energy)))
                audited(self, heads)
                audited(self, tails)

    def test_damage_only_prevention_keeps_the_status(self):
        """「ダメージを受けない」状態（かたまる）の相手には、ダメージの要素だけが無効で、特殊状態は有効なので投げる（CR-STICKY-VS-PREVENTED と同じ形）。"""
        for card, index, energy, condition in self.CASES:
            state = board(mon(card, energy), opponent=mon(CHANSEY, prevent_damage=TURN - 1))
            after = attack(state, index, HD)
            with self.subTest(card=card):
                self.assertEqual(kinds(state, after, "coin_flip", "damage_prevented", "damage", "special_condition"),
                                 ["coin_flip", "damage_prevented", "special_condition"])
                self.assertEqual(conditions(state, after), [(state.players[1].active.pokemon_id, condition)])

    def test_whole_attack_prevention_keeps_hc3(self):
        """「ワザをうけない」状態（バリアー）の相手には、コインが決める要素がどれも無効なので、投げるかが決まらない（HC3。コインの前・宣言の前に止める。状態・乱数・ログは変えない）。
        1 進化のリングマのヘッドプレスは、ミュウの［ニュートラルシールド］でも同じ（実際の使い手の今の姿の段階）。"""
        for card, index, energy, _ in self.CASES:
            with self.subTest(card=card):
                rejects(self, with_barrier(board(mon(card, energy), opponent=mon(CHANSEY))), UseAttack(0, index), "UNRESOLVED_PREVENTED_EFFECT_COIN")
        rejects(self, board(mon(URSARING, (W, W)), opponent=mon(MEW, (PS,))), UseAttack(0, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")
        for card, index, energy, condition in ((WEEDLE, 0, (G,), E.POISON), (SHELLDER, 1, (W, W), E.PARALYSIS)):  # たねのビードル・カスミのシェルダーはミュウも受ける
            state = board(mon(card, energy), opponent=mon(MEW, (PS,)))
            after = attack(state, index, HD)
            self.assertEqual((amounts(state, after, 1), conditions(state, after)), ([(20, 20)], [(state.players[1].active.pokemon_id, condition)]))

    def test_knocked_out_target_gets_no_status(self):
        """ダメージで相手が HP 以上なら、特殊状態にしない（p.309・CR-EFFECTS-AFTER-KO。コインは失敗の判定のために先に投げている）。"""
        state = board(mon(WEEDLE, (G,)), opponent=mon(RATTATA, damage=20))
        after = attack(state, 0, HD)
        self.assertEqual((coins_of(state, after), conditions(state, after), kinds(state, after, "knock_out")), (["heads"], [], ["knock_out"]))

    def test_transparency_is_not_a_failure(self):
        """化石の秘密のゴーストの「とうめい」で受けなかった（「おもて」）ときは、ワザの失敗ではなく（CR-TRANSPARENCY-NOT-FAILURE）、どくも受けない（特殊状態のコインはないので T19b にならない）。"""
        for evade, received in ((HD, False), (TL, True)):
            state = board(mon(WEEDLE, (G,)), opponent=mon(HAUNTER, (PS,)))
            after = attack(state, 0, HD, evade)
            with self.subTest(evade=evade):
                self.assertEqual(kinds(state, after, "attack_failed"), [])
                self.assertEqual(conditions(state, after), [(state.players[1].active.pokemon_id, E.POISON)] if received else [])
                audited(self, after)

    def test_poison_coexists_with_another_condition(self):
        """どくはほかの特殊状態と重なる（p.322）。ねむりの相手をどく、どくの相手をマヒにしても、元の状態は残る。"""
        state = board(mon(WEEDLE, (G,)), opponent=mon(CHANSEY, sleep=True))
        after = attack(state, 0, HD)
        self.assertEqual((after.players[1].active.conditions.poison is not None, after.players[1].active.conditions.asleep), (True, True))
        state = board(mon(SHELLDER, (W, W)), opponent=mon(CHANSEY, poison=10))
        after = attack(state, 1, HD)
        self.assertEqual((after.players[1].active.conditions.poison is not None, after.players[1].active.conditions.paralyzed is not None), (True, True))

    def test_split_decision_keeps_the_status_once(self):
        """相手のドガースの［ぶんれつ］（ダメージを受けたあとの、要素のあいだの決定）をまたいでも、コインを投げ直さず、どくは 1 度だけ（複製・deepcopy・pickle からも同じ）。"""
        state = board(mon(WEEDLE, (G,)), opponent=mon(KOFFING), opponent_deck=[KOFFING, W, W])
        asked = attack(state, 0, HD)
        self.assertEqual(asked.decision.kind, SPLIT_FROM_DECK)
        for choices in ((asked.decision.options[0],), ()):
            done = same_answers(self, asked, choices)
            self.assertEqual((coins_of(asked, done), conditions(asked, done)), ([], [(state.players[1].active.pokemon_id, E.POISON)]))
            audited(self, done)

    def test_copied_stab_poisons_from_the_copier(self):
        """相手のワザとして使う（ピクシーのゆびをふる）と、失敗のコイン・ダメージ・どくは使ったピクシーのワザとして処理する。1 進化のピクシーが使えばミュウは HC3。"""
        state = board(mon(CLEFABLE, (W,)), opponent=mon(WEEDLE, (G,)))
        asked = attack(state, 0)
        self.assertEqual(asked.decision.kind, SELECT_ATTACK)
        done = answer(asked, (0,), HD)
        self.assertEqual((amounts(asked, done, 1), conditions(asked, done)), ([(20, 20)], [(state.players[1].active.pokemon_id, E.POISON)]))
        failed = answer(asked, (0,), TL)
        self.assertEqual((kinds(asked, failed, "damage", "special_condition"), [e["reason"] for e in new_events(asked, failed, "attack_failed")]), ([], ["coin"]))
        audited(self, done)


# ---------------------------------------------------------------- 4.2 節: とつぜんじばく


class SuddenExplosionTest(unittest.TestCase):
    def board(self, **kw):
        kw.setdefault("bench", (RATTATA, GEODUDE))
        kw.setdefault("opponent_bench", (GEODUDE,))
        kw.setdefault("opponent", mon(CHANSEY))
        return board(mon(PINECO, (G,)), **kw)

    def test_heads_is_the_self_destruct_group(self):
        """「おもて」: 相手に 40 → 自分に 40（ワザによるダメージ）→ 相手の控え全員 → 自分の控え全員に 10（弱点・抵抗力に関係なく。草に弱いイシツブテも 10）。じばくと同じ並び・計算。"""
        state = self.board()
        after = attack(state, 0, HD)
        me, them = state.players[0], state.players[1]
        self.assertEqual(damages(state, after), [(1, them.active.pokemon_id, 40, 40), (0, me.active.pokemon_id, 40, 40), (1, them.bench[0].pokemon_id, 10, 10),
                                                 (0, me.bench[0].pokemon_id, 10, 10), (0, me.bench[1].pokemon_id, 10, 10)])
        self.assertTrue(all(e.get("ignore_weakness_resistance") for e in new_events(state, after, "damage")[2:]))
        self.assertEqual(kinds(state, after, "attack_failed"), [])
        self.assertIsNone(after.players[0].active)  # クヌギダマ（HP 40）は自分へのダメージ 40 で HP 以上になり、ワザのあとにきぜつした
        audited(self, after)

    def test_tails_leaves_nothing(self):
        """「うら」ならワザ全体の失敗（自分へのダメージ・控えへのダメージも残さない。先に与えて取り消すことはしない）。"""
        state = self.board()
        after = attack(state, 0, TL)
        self.assertEqual((coins_of(state, after), kinds(state, after, "damage", "damage_prevented", "knock_out")), (["tails"], []))
        self.assertEqual([e["reason"] for e in new_events(state, after, "attack_failed")], ["coin"])
        self.assertEqual((after.players[0].active.damage, [p.damage for p in after.players[0].bench], [p.damage for p in after.players[1].bench]), (0, [0, 0], [0]))

    def test_self_and_bench_survive_a_void_on_the_opponent(self):
        """相手が「ワザをうけない」（バリアー）・「ダメージを受けない」・ミュウの［ニュートラルシールド］（相手のワザとして使ったピクシー）でも、コインが決める要素に自分へのダメージが
        あるので投げる（v0.4b・HC3 にならない）。相手へのダメージだけが無効で、自分と控えへのダメージは残る。"""
        barrier = with_barrier(self.board())
        prevented = self.board(opponent=mon(CHANSEY, prevent_damage=TURN - 1))
        for state in (barrier, prevented):
            after = attack(state, 0, HD)
            with self.subTest(prevented=state is prevented):
                self.assertEqual(kinds(state, after, "coin_flip", "damage_prevented")[:2], ["coin_flip", "damage_prevented"])
                self.assertEqual([owner for owner, *_ in damages(state, after)], [0, 1, 0, 0])
                self.assertIsNone(after.players[0].active)
        # 控えのミュウ（［ニュートラルシールド］は場のどこでも）: 1 進化のピクシーがゆびをふるで使うと、ミュウへの控えのダメージだけが無効。たねのピッピが使えばミュウも受ける
        for user, index, voided in ((CLEFABLE, 0, True), (CLEFAIRY, 1, False)):
            state = board(mon(user, (W, W, W)), bench=(RATTATA,), opponent=mon(PINECO, (G,)), opponent_bench=(MEW, RATTATA))
            mew = state.players[1].bench[0].pokemon_id
            done = answer(attack(state, index), (0,), HD)
            with self.subTest(user=user):
                self.assertEqual([e["pokemon_id"] for e in new_events(state, done, "damage_prevented")], [mew] if voided else [])
                self.assertEqual([(owner, base) for owner, _, base, _ in damages(state, done)],
                                 [(1, 40), (0, 40), (1, 10), (0, 10)] if voided else [(1, 40), (0, 40), (1, 10), (1, 10), (0, 10)])

    def test_transparency_keeps_self_and_bench(self):
        """相手の「とうめい」で相手へのダメージを受けなかったときも、ワザは失敗ではなく、自分と控えへのダメージは処理する（CR-TRANSPARENCY-NOT-FAILURE）。"""
        state = self.board(opponent=mon(HAUNTER, (PS,)))
        after = attack(state, 0, HD, HD)
        self.assertEqual(len(new_events(state, after, "attack_evaded")), 1)
        self.assertEqual([owner for owner, *_ in damages(state, after)], [0, 1, 0, 0])
        self.assertEqual(kinds(state, after, "attack_failed"), [])

    def test_simultaneous_knock_outs(self):
        """自分へのダメージは強制のきぜつではなくワザによるダメージ: ダメージ 0 のクヌギダマ（HP 40）は 40 で HP 以上になる。相手の対戦ポケモンと同時のきぜつ（p.324）で、サイド・
        補充は既存のワザのあとの処理。"""
        state = self.board(opponent=mon(RATTATA), opponent_bench=(RATTATA,))
        after = attack(state, 0, HD)
        self.assertEqual(len(new_events(state, after, "knock_out")), 2)
        audited(self, after)

    def test_reduction_decision_keeps_recoil_and_bench_once(self):
        """お上品攻撃の減らす量の決定（相手へのダメージ）をまたいでも、コインを投げ直さず、自分と控えへのダメージは 1 度だけ（複製・deepcopy・pickle からも同じ）。"""
        state = charity(self.board(hand=(H.CHARITY,)))
        asked = attack(state, 0, HD)
        self.assertEqual(asked.decision.kind, DAMAGE_REDUCTION)
        done = same_answers(self, asked, (20,))
        self.assertEqual((coins_of(asked, done), [(owner, amount) for owner, _, _, amount in damages(asked, done)]), ([], [(1, 20), (0, 40), (1, 10), (0, 10), (0, 10)]))
        audited(self, done)

    def test_energy_drain_after_the_group(self):
        """相手の控えのキョウのベトベトンが控えへのダメージで［だつりょくえき］の「おもて」: すべてのダメージのあとに、ダメージを与えたポケモンのエネルギーを持ち主が選んで
        トラッシュする決定。答えのあとでコイン・ダメージ・反動をくり返さない。クヌギダマ自身（HP 40）は自分へのダメージ 40 で、その時点で HP 以上なので、既存の DR8
        （UNRESOLVED_ENERGY_DRAIN_ATTACKER_KNOCKED_OUT）で宣言の前に止める。HP の残るピクシーがゆびをふるで使う場面で、決定をまたぐ再開を確かめる。"""
        rejects(self, with_coin_results(self.board(bench=(RATTATA,), opponent_bench=(mon(KOGAS_MUK, (G,)),)), HD, HD), UseAttack(0, 0),
                "UNRESOLVED_ENERGY_DRAIN_ATTACKER_KNOCKED_OUT")
        state = board(mon(CLEFABLE, (W, W)), bench=(RATTATA,), opponent=mon(PINECO, (G,)), opponent_bench=(mon(KOGAS_MUK, (G,)),))
        asked = answer(attack(state, 0), (0,), HD, HD)
        self.assertEqual((asked.decision.kind, asked.decision.player), (ENERGY_DRAIN_DISCARD, 1))
        self.assertEqual([owner for owner, *_ in damages(state, asked)], [1, 0, 1, 0])
        done = same_answers(self, asked, asked.decision.options[:1])
        self.assertEqual((coins_of(asked, done), kinds(asked, done, "damage"), done.players[0].active.damage), ([], [], 40))
        self.assertEqual(len(done.players[0].active.energy), 1)
        audited(self, done)

    def test_profile_keeps_the_pair(self):
        """宣言の前の候補は、同じコインの (40, 40)（「おもて」）と (なし, 0)（「うら」の失敗）だけ。失敗して自分へのダメージだけが残る組は作らない。"""
        state = self.board()
        profile = E.FailOnTailsSelfDestruct(40, 10).damage_profile(state, use(state, PINECO, 0))
        self.assertEqual(profile.pairs(), ((40, 40), (None, 0)))

    def test_copied_explosion_hurts_the_copier(self):
        """相手のワザとして使う（ピクシーのゆびをふる）と、自分へのダメージ・自分の控えへのダメージは使ったピクシーとその持ち主の控え。"""
        state = board(mon(CLEFABLE, (W,)), bench=(RATTATA,), opponent=mon(PINECO, (G,)), opponent_bench=(RATTATA, RATTATA))
        done = answer(attack(state, 0), (0,), HD)
        me = state.players[0]
        self.assertEqual([(owner, pid) for owner, pid, _, _ in damages(state, done)],
                         [(1, state.players[1].active.pokemon_id), (0, me.active.pokemon_id), (1, state.players[1].bench[0].pokemon_id),
                          (1, state.players[1].bench[1].pokemon_id), (0, me.bench[0].pokemon_id)])
        self.assertEqual(done.players[0].active.damage, 40)
        audited(self, done)


# ---------------------------------------------------------------- 4.3 節: そらをとぶ


class FlyTest(unittest.TestCase):
    def fly(self, card, index, flip, **kw):
        kw.setdefault("opponent", mon(SABRINAS_JYNX, (PS,)))
        state = board(mon(card, (W, W, W)), **kw)
        return state, attack(state, index, flip)

    def test_heads_gives_damage_then_barrier_once(self):
        """4 つのそらをとぶ: 1 枚のコインの「おもて」で相手に 30、そのあと（同じコイン。投げ直さない）自分にバリアー。「うら」ならワザ全体が失敗し、ダメージも防護もない。"""
        for card, index in FLIERS:
            state, heads = self.fly(card, index, HD)
            _, tails = self.fly(card, index, TL)
            pid = state.players[0].active.pokemon_id
            with self.subTest(card=card):
                self.assertEqual((coins_of(state, heads), amounts(state, heads, 1), barriers(state, heads)), (["heads"], [(30, 30)], [pid]))
                self.assertEqual(kinds(state, heads, "damage", "persistent_effect_added"), ["damage", "persistent_effect_added"])
                self.assertEqual((coins_of(state, tails), kinds(state, tails, "damage", "persistent_effect_added")), (["tails"], []))
                self.assertEqual([e["reason"] for e in new_events(state, tails, "attack_failed")], ["coin"])
                audited(self, heads)

    def test_barrier_blocks_damage_and_effects_next_turn_then_expires(self):
        """次の相手の番に、相手のワザのダメージと効果（ナツメのルージュラのおやすみのキッスの 10 とねむり）を受けない（ダメージだけを防ぐ状態ではない）。その次の相手の番には受ける。"""
        for card, index in FLIERS:
            _, heads = self.fly(card, index, HD)
            hit = attack(heads, 0, player=1)
            with self.subTest(card=card):
                self.assertEqual(kinds(heads, hit, "damage_prevented", "damage", "special_condition"), ["damage_prevented"])
                self.assertEqual(hit.players[0].active.damage, 0)
                mine = apply_kernel(hit, EndTurn(0))
                later = attack(mine, 0, player=1)
                self.assertEqual(kinds(mine, later, "damage_prevented", "damage", "special_condition"), ["damage", "special_condition"])
                self.assertEqual(later.players[0].active.damage, 10)
                audited(self, later)

    def test_tails_gives_no_barrier(self):
        _, tails = self.fly(FLYING_18, 1, TL)
        hit = attack(tails, 0, player=1)
        self.assertEqual((kinds(tails, hit, "damage_prevented", "damage", "special_condition"), hit.players[0].active.damage), (["damage", "special_condition"], 10))

    def test_returning_to_the_bench_ends_the_barrier(self):
        """ベンチにもどったら消える（GR-2000-P322-PERSISTENT-EFFECTS。バリアーと同じ）: 次の相手の番に相手が突風でそらをとぶピカチュウをベンチにもどすと、防護は消え、もう一度バトル場に
        出ても（ポケモンいれかえ）その番のワザを受ける。"""
        state = board(mon(FLYING_42, (W, W, W)), bench=(RATTATA,), opponent=mon(SABRINAS_JYNX, (PS,)), opponent_hand=(H.GUST, H.SWITCH))
        pikachu = state.players[0].active.pokemon_id
        heads = attack(state, 1, HD)
        self.assertEqual(barriers(state, heads), [pikachu])
        gusted = apply_kernel(heads, PlayTrainer(1, uid_in_hand(heads, H.GUST, 1)))
        gusted = answer(gusted, gusted.decision.options[:1])
        self.assertEqual([p.pokemon_id for p in gusted.players[0].bench], [pikachu])
        self.assertEqual([e["persistent_effect"] for e in new_events(heads, gusted, "persistent_effect_removed") if e["pokemon_id"] == pikachu], [AttackBarrier.kind])
        self.assertFalse(any(isinstance(e, AttackBarrier) for e in gusted.players[0].bench[0].persistent_effects))
        audited(self, gusted)

    def test_counterattack_hits_first_and_knocked_out_user_gets_no_barrier(self):
        """カイリキーの［はんげき］はダメージのまとまりのあと・防護の前（同じ番の返す効果を先に無効にしない。防護は次の相手の番から）。はんげきで HP 以上になったら防護は与えない
        （p.309。ログ persistent_effect_skipped）。"""
        state = board(mon(FLYING_18, (W, W, W)), opponent=mon(MACHAMP, (F,)))
        after = attack(state, 1, HD)
        self.assertEqual(kinds(state, after, "damage", "counterattack", "persistent_effect_added"), ["damage", "counterattack", "persistent_effect_added"])
        self.assertEqual(after.players[0].active.damage, 10)
        state = board(mon(FLYING_18, (W, W, W), damage=30), opponent=mon(MACHAMP, (F,)))
        after = attack(state, 1, HD)
        self.assertEqual((barriers(state, after), [e["reason"] for e in new_events(state, after, "persistent_effect_skipped")]), ([], [E.EFFECT_TARGET_KNOCKED_OUT]))

    def test_void_on_the_opponent_still_flips_for_the_barrier(self):
        """相手が「ワザをうけない」・「ダメージを受けない」状態、2 進化のバタフリーのワザをミュウの［ニュートラルシールド］で無効にするときも、自分への防護が残るので投げる。たねの
        そらをとぶピカチュウのワザはミュウも受ける（発生元の今の姿の段階）。"""
        for state, index in ((with_barrier(board(mon(FLYING_63, (W, W, W)), opponent=mon(CHANSEY))), 1),
                             (board(mon(FLYING_63, (W, W, W)), opponent=mon(CHANSEY, prevent_damage=TURN - 1)), 1),
                             (board(mon(BUTTERFREE, (W, W, W)), opponent=mon(MEW, (PS,))), 0)):
            after = attack(state, index, HD)
            with self.subTest(card=state.cards[state.players[0].active.card].card_id):
                self.assertEqual(kinds(state, after, "coin_flip", "damage_prevented", "damage", "persistent_effect_added"),
                                 ["coin_flip", "damage_prevented", "persistent_effect_added"])
        state = board(mon(FLYING_18, (W, W, W)), opponent=mon(MEW, (PS,), damage=0), opponent_bench=(RATTATA,))
        self.assertEqual(amounts(state, attack(state, 1, HD), 1), [(30, 30)])

    def test_flee_decision_keeps_the_barrier_once(self):
        """相手の［にげこむ］（カスミのドククラゲ）の決定は、ダメージのまとまりのあと・防護の前。答えのあとに防護を 1 度だけ与える（複製・deepcopy・pickle からも同じ）。"""
        state = board(mon(BUTTERFREE, (W, W, W)), opponent=mon(TENTACRUEL, (W, W)), opponent_bench=(RATTATA,))
        asked = attack(state, 0, HD)
        self.assertEqual((asked.decision.kind, barriers(state, asked)), (REACTION_SWITCH, []))
        for choices in ((), asked.decision.options[:1]):
            done = same_answers(self, asked, choices)
            self.assertEqual((coins_of(asked, done), barriers(asked, done)), ([], [state.players[0].active.pokemon_id]))

    def test_step_order_decision_keeps_the_coin_and_barrier_once(self):
        """8 段階の順番の決定（相手のかたくなる（20 以下は 0）とちいさくなる（−20）で 30 が 10 か 0）をまたいでも、失敗のコインを投げ直さず、防護は答えのあとに 1 度だけ（複製・deepcopy・
        pickle からも同じ）。"""
        state = board(mon(FLYING_42, (W, W, W)), opponent=mon(GEODUDE, (F, W)))
        geodude = state.players[1].active
        with_effects(state, 1, ZeroDamageBelow(geodude.card, 1, TURN - 1, TURN, 30), DamageReduction(geodude.card, 1, TURN - 1, TURN, 20), keys=(f"{GEODUDE}#1", "test"))
        asked = attack(state, 1, HD)
        self.assertEqual((asked.decision.kind, asked.decision.player, barriers(state, asked)), (DAMAGE_STEP_ORDER, 1, []))
        results = {o: answer(asked, (o,)).players[1].active.damage for o in asked.decision.options}
        self.assertEqual(sorted(results.values()), [0, 10])
        done = same_answers(self, asked, asked.decision.options[:1])
        self.assertEqual((coins_of(asked, done), barriers(asked, done)), ([], [state.players[0].active.pokemon_id]))
        audited(self, done)

    def test_copied_fly_protects_the_copier(self):
        """相手のワザとして使う（ピクシーのゆびをふる）と、防護は使ったピクシーに与える（コピー元のバタフリーではない）。"""
        state = board(mon(CLEFABLE, (W,)), opponent=mon(BUTTERFREE, (W, W, W)))
        done = answer(attack(state, 0), (0,), HD)
        self.assertEqual(barriers(state, done), [state.players[0].active.pokemon_id])
        self.assertFalse(any(isinstance(e, AttackBarrier) for e in done.players[1].active.persistent_effects))
        audited(self, done)


# ---------------------------------------------------------------- 4.4 節: へんずつう


class MigraineTest(unittest.TestCase):
    def test_damage_on_both_sides_of_the_coin(self):
        """相手に 20（コインの前。どちらの面でも与える）→ コイン 1 枚 →「おもて」なら相手、「うら」なら自分をこんらん（「うら」をワザの失敗にしない）。"""
        for flip, confused in ((HD, 1), (TL, 0)):
            state = board(mon(PSYDUCK, (PS, W)), opponent=mon(CHANSEY))
            after = attack(state, 1, flip)
            with self.subTest(flip=flip):
                self.assertEqual(kinds(state, after, "damage", "coin_flip", "special_condition"), ["damage", "coin_flip", "special_condition"])
                self.assertEqual(amounts(state, after, 1), [(20, 20)])
                self.assertEqual(conditions(state, after), [(state.players[confused].active.pokemon_id, E.CONFUSION)])
                self.assertEqual(kinds(state, after, "attack_failed"), [])
                audited(self, after)

    def test_opponent_knocked_out_still_flips_for_self(self):
        """相手がこのワザのダメージで HP 以上でも、自分へのこんらんが残るので投げる。「おもて」なら何もしない（相手の対象がない）、「うら」なら自分がこんらん。"""
        for flip, expected in ((HD, []), (TL, [0])):
            state = board(mon(PSYDUCK, (PS, W)), opponent=mon(RATTATA, damage=20))
            after = attack(state, 1, flip)
            with self.subTest(flip=flip):
                self.assertEqual(coins_of(state, after), [flip.value])
                self.assertEqual(conditions(state, after), [(state.players[p].active.pokemon_id, E.CONFUSION) for p in expected])

    def test_void_on_the_opponent_keeps_self_confusion(self):
        """相手が効果を受けない（「ワザをうけない」状態・「とうめい」で受けなかった）ときも、自分へのこんらんまで消さない（コインを投げる。HC3・T19b にならない）。"""
        for flip in (HD, TL):
            barrier = with_barrier(board(mon(PSYDUCK, (PS, W)), opponent=mon(CHANSEY)))
            after = attack(barrier, 1, flip)
            with self.subTest(flip=flip, barrier=True):
                self.assertEqual(kinds(barrier, after, "damage_prevented", "coin_flip"), ["damage_prevented", "coin_flip"])
                self.assertEqual(conditions(barrier, after), [] if flip is HD else [(barrier.players[0].active.pokemon_id, E.CONFUSION)])
            ghost = board(mon(PSYDUCK, (PS, W)), opponent=mon(HAUNTER, (PS,)))
            after = attack(ghost, 1, HD, flip)  # 「とうめい」の「おもて」で受けなかった
            with self.subTest(flip=flip, transparency=True):
                self.assertEqual([e["element"] for e in new_events(ghost, after, "attack_evaded")][:1], ["damage"])
                self.assertEqual(coins_of(ghost, after)[-1], flip.value)
                self.assertEqual(conditions(ghost, after), [] if flip is HD else [(ghost.players[0].active.pokemon_id, E.CONFUSION)])
                audited(self, after)

    def test_self_knocked_out_flips_for_the_opponent(self):
        """自分がカイリキーの［はんげき］で HP 以上になっても、相手へのこんらんが残るので投げる（はんげきはコインの前）。「おもて」なら相手がこんらん、「うら」なら何もしない。"""
        for flip, expected in ((HD, [1]), (TL, [])):
            state = board(mon(PSYDUCK, (PS, W), damage=40), opponent=mon(MACHAMP, (F,)))
            after = attack(state, 1, flip)
            with self.subTest(flip=flip):
                self.assertEqual(kinds(state, after, "damage", "counterattack", "coin_flip"), ["damage", "counterattack", "coin_flip"])
                self.assertEqual(conditions(state, after), [(state.players[p].active.pokemon_id, E.CONFUSION) for p in expected])

    def test_double_knock_out_keeps_c18(self):
        """相手がこのワザで HP 以上になり、自分が［はんげき］だけで HP 以上になりうるなら、既存の C18 で宣言の前に止める（そろってのきぜつ）。"""
        rejects(self, board(mon(PSYDUCK, (PS, W), damage=40), opponent=mon(MACHAMP, (F,), damage=80)), UseAttack(0, 1), "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")

    def test_flee_then_coin_once(self):
        """相手の［にげこむ］で入れ替わったら、相手へのこんらんは対象がない（かわりに出たポケモンに移さない）が、自分へのこんらんが残るので投げる。答えのあとに 1 度だけ。"""
        state = board(mon(PSYDUCK, (PS, W)), opponent=mon(TENTACRUEL, (W, W)), opponent_bench=(RATTATA,))
        asked = attack(state, 1)
        self.assertEqual((asked.decision.kind, coins_of(state, asked)), (REACTION_SWITCH, []))
        for flip in (HD, TL):
            fled = answer(asked, asked.decision.options[:1], flip)
            with self.subTest(flip=flip):
                self.assertEqual(coins_of(asked, fled), [flip.value])
                self.assertEqual(conditions(asked, fled), [] if flip is HD else [(state.players[0].active.pokemon_id, E.CONFUSION)])
        stay = same_answers(self, with_coin_results(asked, TL), ())
        self.assertEqual(conditions(asked, stay), [(state.players[0].active.pokemon_id, E.CONFUSION)])

    def test_copied_and_neutral_shield(self):
        """相手のワザとして使う（ピッピのゆびをふる）と、自分へのこんらんは使ったポケモン（印刷元のコダックではない）。たねのコダックのワザはミュウの［ニュートラルシールド］で
        無効にならない（発生元の今の姿の段階。ゆびをふるは相手の対戦ポケモンのワザを選ぶので、進化ポケモンがへんずつうをミュウに使う場面は今の写しにない）。"""
        state = board(mon(CLEFAIRY, (W, W, W)), opponent=mon(PSYDUCK, (PS, W)))
        asked = attack(state, 1)
        self.assertEqual(asked.decision.kind, SELECT_ATTACK)
        done = answer(asked, (1,), TL)
        self.assertEqual((amounts(state, done, 1), conditions(state, done)), ([(20, 20)], [(state.players[0].active.pokemon_id, E.CONFUSION)]))
        self.assertEqual(done.players[1].active.conditions.confused, False)
        audited(self, done)
        state = board(mon(PSYDUCK, (PS, W)), opponent=mon(MEW, (PS,)))
        after = attack(state, 1, HD)
        self.assertEqual((amounts(state, after, 1), conditions(state, after)), ([(20, 20)], [(state.players[1].active.pokemon_id, E.CONFUSION)]))


# ---------------------------------------------------------------- 4.5 節: レインボーパウダー


class RainbowPowderTest(unittest.TestCase):
    def test_heads_paralysis_tails_poison(self):
        """20 ダメージのあとに 1 枚だけ投げ、「おもて」ならマヒ、「うら」ならどく（どちらか一方。v0.38 のきけんなはりとは面と特殊状態が逆）。"""
        for flip, condition in ((HD, E.PARALYSIS), (TL, E.POISON)):
            state = board(mon(BUTTERFREE, (G, G, W)), opponent=mon(CHANSEY))
            after = attack(state, 1, flip)
            with self.subTest(flip=flip):
                self.assertEqual(kinds(state, after, "damage", "coin_flip", "special_condition"), ["damage", "coin_flip", "special_condition"])
                self.assertEqual(conditions(state, after), [(state.players[1].active.pokemon_id, condition)])
                audited(self, after)

    def test_knocked_out_target_flips_nothing(self):
        state = board(mon(BUTTERFREE, (G, G, W)), opponent=mon(RATTATA, damage=20))
        after = attack(state, 1)
        self.assertEqual((coins_of(state, after), conditions(state, after)), ([], []))

    def test_existing_boundaries(self):
        """コインは相手への効果だけを決めるので、「ワザをうけない」相手・2 進化のバタフリーのワザをミュウが受けないときは HC3、「とうめい」で受けないと決まりうる相手は T19b（どれも
        宣言の前に止める）。「ダメージを受けない」相手には投げる。"""
        rejects(self, with_barrier(board(mon(BUTTERFREE, (G, G, W)), opponent=mon(CHANSEY))), UseAttack(0, 1), "UNRESOLVED_PREVENTED_EFFECT_COIN")
        rejects(self, board(mon(BUTTERFREE, (G, G, W)), opponent=mon(MEW, (PS,))), UseAttack(0, 1), "UNRESOLVED_PREVENTED_EFFECT_COIN")
        rejects(self, board(mon(BUTTERFREE, (G, G, W)), opponent=mon(HAUNTER, (PS,))), UseAttack(0, 1), "UNRESOLVED_EVADED_EFFECT_COIN")
        state = board(mon(BUTTERFREE, (G, G, W)), opponent=mon(CHANSEY, prevent_damage=TURN - 1))
        after = attack(state, 1, TL)
        self.assertEqual((kinds(state, after, "damage_prevented"), conditions(state, after)), (["damage_prevented"], [(state.players[1].active.pokemon_id, E.POISON)]))

    def test_poison_coexists(self):
        """「うら」のどくはこんらんと重なり、「おもて」のマヒはどくと重なる（p.322）。"""
        state = board(mon(BUTTERFREE, (G, G, W)), opponent=mon(CHANSEY, confusion=True))
        after = attack(state, 1, TL)
        self.assertEqual((after.players[1].active.conditions.poison is not None, after.players[1].active.conditions.confused), (True, True))
        state = board(mon(BUTTERFREE, (G, G, W)), opponent=mon(CHANSEY, poison=10))
        after = attack(state, 1, HD)
        self.assertEqual((after.players[1].active.conditions.poison is not None, after.players[1].active.conditions.paralyzed is not None), (True, True))


# ---------------------------------------------------------------- 3 章: 既存の型の 6 つのワザ


class ReusedTypeTest(unittest.TestCase):
    def test_double_lariat(self):
        """コイン 2 枚の「おもて」0・1・2 枚で 0・40・80（0 枚は失敗ではない）。「ダメージを受けない」相手には v0.4b。"""
        for flips, base in (((TL, TL), 0), ((HD, TL), 40), ((HD, HD), 80)):
            state = board(mon(URSARING, (W, W, W, W)), opponent=mon(CHANSEY))
            after = attack(state, 1, *flips)
            with self.subTest(flips=flips):
                self.assertEqual(len(coins_of(state, after)), 2)
                self.assertEqual(amounts(state, after, 1)[0][0], base)
                self.assertEqual(kinds(state, after, "attack_failed"), [])
        rejects(self, board(mon(URSARING, (W, W, W, W)), opponent=mon(CHANSEY, prevent_damage=TURN - 1)), UseAttack(0, 1), "UNRESOLVED_PREVENTED_COIN_DAMAGE")

    def test_plain_damage_and_coin_attacks(self):
        """みずかけ・たいあたり（説明文なし）は目安のダメージだけ。でんきショックは「おもて」でマヒ。でんげきは「うら」で自分にも 10。"""
        for card, index, energy, base in ((PSYDUCK, 0, (W,), 10), (SHELLDER, 0, (W,), 10)):
            state = board(mon(card, energy), opponent=mon(CHANSEY))
            after = attack(state, index)
            self.assertEqual((amounts(state, after, 1), coins_of(state, after)), ([(base, base)], []))
        for card in (FLYING_18, FLYING_63):
            state = board(mon(card, (L,)), opponent=mon(CHANSEY))
            after = attack(state, 0, HD)
            self.assertEqual(conditions(state, after), [(state.players[1].active.pokemon_id, E.PARALYSIS)])
        for flip, own in ((HD, []), (TL, [(10, 10)])):
            state = board(mon(FLYING_42, (L,)), opponent=mon(CHANSEY))
            after = attack(state, 0, flip)
            self.assertEqual((amounts(state, after, 1), amounts(state, after, 0)), ([(20, 20)], own))


# ---------------------------------------------------------------- 6 章: 決定・ESP・先読み・保存


class DecisionTest(unittest.TestCase):
    def test_esp_without_sabrinas_pokemon_stops_or_keeps_the_first_coin(self):
        """ナツメのESP（ナツメのポケモンでないカードにつけた盤面）: やり直すと既存の ES3 で止まる。やり直さない答えは、最初のコインで成否・防護・こんらんを 1 度だけ処理する（決定の
        再開でコインを投げ直さない）。"""
        for card, index, energy, flip in ((FLYING_18, 1, (W, W, W), TL), (PSYDUCK, 1, (PS, W), TL), (PINECO, 0, (G,), HD)):
            state = board(mon(card, energy, trainers=[(H.SABRINAS_ESP, TURN)]), opponent=mon(CHANSEY))
            asked = attack(state, index, flip)
            with self.subTest(card=card):
                self.assertEqual((asked.decision.kind, asked.decision.context_value("unresolved_code")), (ESP_REDO, "UNRESOLVED_ESP_HOLDER_NOT_SABRINAS"))
                rejects(self, asked, lambda s: ResolveDecision(0, s.decision.id, (1,)), "UNRESOLVED_ESP_HOLDER_NOT_SABRINAS")
                kept = same_answers(self, asked, ())
                self.assertEqual(coins_of(asked, kept), [])
                self.assertEqual(kinds(asked, kept, "attack_failed"), ["attack_failed"] if card == FLYING_18 else [])
                audited(self, kept)

    def test_esp_redo_replaces_the_coin_for_every_element(self):
        """ESP の正規の投げ直し（持ち主の確かめ ES3 を試験の中だけ外した盤面。仕組みの確かめ）: やり直した結果だけで、そらをとぶの成否・ダメージ・防護、とつぜんじばくの反動・控え、
        へんずつうのこんらんの対象を決める（最初の「うら」で失敗にしない・ダメージをくり返さない）。"""
        with mock.patch.object(E, "esp_redo_problem", lambda *args: None):
            for card, index, energy in ((FLYING_42, 1, (W, W, W)), (PINECO, 0, (G,)), (PSYDUCK, 1, (PS, W))):
                state = board(mon(card, energy, trainers=[(H.SABRINAS_ESP, TURN)]), opponent=mon(CHANSEY))
                asked = attack(state, index, TL)
                self.assertEqual(asked.decision.kind, ESP_REDO)
                redone = answer(asked, (1,), HD)
                with self.subTest(card=card):
                    self.assertEqual([e["redone"] for e in new_events(asked, redone, "esp_redo")], [("heads",)])
                    self.assertEqual(kinds(state, redone, "attack_failed"), [])
                    if card == FLYING_42:
                        self.assertEqual((amounts(asked, redone, 1), barriers(asked, redone)), ([(30, 30)], [state.players[0].active.pokemon_id]))
                    elif card == PINECO:
                        self.assertEqual([owner for owner, *_ in damages(asked, redone)], [1, 0, 1, 0])
                    else:
                        self.assertEqual((amounts(state, redone, 1), conditions(asked, redone)), ([(20, 20)], [(state.players[1].active.pokemon_id, E.CONFUSION)]))

    def test_invalid_answers_change_nothing(self):
        """［にげこむ］の決定への不正な答え（選べないポケモン・答えるプレイヤーの違い）は、状態・乱数・ログ・決定を変えずに拒否する（HALTED にしない）。"""
        asked = attack(board(mon(FLYING_63, (W, W, W)), opponent=mon(TENTACRUEL, (W, W)), opponent_bench=(RATTATA,)), 1, HD)
        for player, choices in ((1, (999,)), (0, asked.decision.options[:1])):
            before = snap(asked)
            with self.subTest(player=player, choices=choices), self.assertRaises(IllegalActionError):
                apply_kernel(asked, ResolveDecision(player, asked.decision.id, choices))
            self.assertEqual(snap(asked), before)
        self.assertEqual(max(FORMAT_VERSIONS), LATEST_FORMAT)
        self.assertEqual(LATEST_FORMAT, 26)

    def test_preflight_methods_agree(self):
        """先読みの方法（derived・derived_full・legacy）は同じ結果（新しい型は v0.13 の止める関数の確かめた型ではないので、legacy でもすべての結果を試す）。上限は変えていない。"""
        self.assertEqual(MAX_BRANCHES, 4096)
        cases = ((board(mon(WEEDLE, (G,)), opponent=mon(CHANSEY)), 0, (HD,)), (board(mon(PINECO, (G,)), opponent=mon(CHANSEY)), 0, (TL,)),
                 (board(mon(URSARING, (W, W)), opponent=mon(CHANSEY)), 0, (HD,)), (board(mon(PSYDUCK, (PS, W)), opponent=mon(MACHAMP, (F,))), 1, (TL,)),
                 (board(mon(FLYING_18, (W, W, W)), opponent=mon(MACHAMP, (F,))), 1, (HD,)), (board(mon(BUTTERFREE, (G, G, W)), opponent=mon(CHANSEY)), 1, (TL,)),
                 (board(mon(PINECO, (G,)), opponent=mon(HAUNTER, (PS,))), 0, (HD, TL)))
        for state, index, flips in cases:
            results = [snap(apply_kernel(with_coin_results(state, *flips), UseAttack(0, index), preflight=mode)) for mode in ("derived", "derived_full", "legacy")]
            with self.subTest(card=state.cards[state.players[0].active.card].card_id, index=index):
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0], results[2])


# ---------------------------------------------------------------- 8 章: ログの監査


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v107_problems``）は、エンジンの ``FailOnTails``・``Status``・``SelfPersistent``・``void_coin_question`` を読まずに、ログから組み立てた場とこのワザの
    ログの並びで確かめる。エンジンの処理を一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py の局。v0.107 のワザが出る組と seed）で、監査がそれを見つける（誤らせなければ、
    同じ局は監査を通る）。"""

    GAMES = ((("W107", "B107"), 2), (("B107", "E107"), 2), (("W107", "P31"), 0), (("E107", "B107"), 0))

    @classmethod
    def results(cls, patcher):
        from tools import existing_effect_games as games

        found = []
        with patcher:
            for labels, seed in cls.GAMES:
                result = games.play(labels, seed, keep_state=True)
                if result.get("state") is not None:
                    found.append((result, log_problems(result["state"])))
        return found

    def problems_for(self, patcher, *cards):
        return [p for _, problems in self.results(patcher) for p in problems if any(card in p for card in cards)]

    def test_the_unpatched_games_pass_the_audit(self):
        from tools import existing_effect_games as games

        for labels, seed in self.GAMES:
            result = games.play(labels, seed, keep_state=True)
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual((result["outcome"], result["audit"], log_problems(result["state"])), ("game_over", {}, []))
                self.assertTrue(any(key.startswith("attack_") for key in result["v107"]))

    def test_audit_finds_elements_left_after_tails(self):
        """失敗のコインの「うら」でワザを失敗させなかった（ダメージ・特殊状態・反動・控え・防護が残る）。"""

        def no_failure(self, run):
            run.fs.coins[self.name] = run.flip(self.count, by_heads=True)
            return False

        self.assertTrue(self.problems_for(mock.patch.object(P.FailOnTails, "run", no_failure), WEEDLE, PINECO, URSARING, SHELLDER, *(card for card, _ in FLIERS)))

    def test_audit_finds_a_barrier_before_the_damage(self):
        """そらをとぶの防護を、相手へのダメージの要素より先に与えた。"""
        early = {E.FailOnTailsDamageThenSelfBarrier: lambda e: (P.FailOnTails(), P.SelfPersistent(AttackBarrier.kind), P.Damage(P.OPP, P.Printed()))}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, early), *(card for card, _ in FLIERS)))

    def test_audit_finds_damage_only_on_heads(self):
        """へんずつうを、「うら」なら相手にダメージを与えない型（ナツメのコダックのこまったねんりき）で処理した。"""
        wrong = {E.DamageThenConfuseOpponentOrSelf: lambda e: P.BUILDERS[E.CoinDamageAndConfuseElseSelfConfuse](E.CoinDamageAndConfuseElseSelfConfuse())}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, wrong), PSYDUCK))

    def test_audit_finds_a_swapped_rainbow_powder(self):
        """レインボーパウダーの面と特殊状態の対応を逆にした（「おもて」どく・「うら」マヒ）。"""
        swapped = {E.DamageThenStatusByCoin: lambda e: (P.Damage(P.OPP, P.Printed()), P.Status(e.tails, local_coin=HD, otherwise=e.heads, reparalysis_check=True))}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, swapped), BUTTERFREE))

    def test_audit_finds_bench_weakness_and_a_missing_recoil(self):
        """とつぜんじばくの控えへのダメージに弱点・抵抗力を計算した・自分へのダメージを落とした。"""
        weak = {E.FailOnTailsSelfDestruct: lambda e: (P.FailOnTails(), P.Damage(P.OPP, P.Printed()), P.Damage(P.SELF, P.Fixed(e.self_damage), name="self_damage"),
                                                      P.BenchDamage(P.Fixed(e.bench_damage), weakness_resistance=True),
                                                      P.BenchDamage(P.Fixed(e.bench_damage), weakness_resistance=True, own=True))}
        self.assertTrue([p for p in self.problems_for(mock.patch.dict(P.BUILDERS, weak), PINECO) if "弱点・抵抗力" in p])
        no_recoil = {E.FailOnTailsSelfDestruct: lambda e: (P.FailOnTails(), P.Damage(P.OPP, P.Printed()), P.BenchDamage(P.Fixed(e.bench_damage)),
                                                           P.BenchDamage(P.Fixed(e.bench_damage), own=True))}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, no_recoil), PINECO))


class DocumentTest(unittest.TestCase):
    def test_document_names_the_shared_parts(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("FailOnTailsDamageThenPoison", "FailOnTailsSelfDestruct", "FailOnTailsDamageThenSelfBarrier", "DamageThenConfuseOpponentOrSelf",
                       "PARALYZE_ELSE_FAIL_TEXTS", "RAINBOW_POWDER_TEXTS", "FLY_TEXTS", "DamageAndParalyzeOnHeadsElseFail", "DamageThenStatusByCoin",
                       "FailOnTails", "AttackBarrier", "SelfPersistent", "void_coin_question", "v0.4b", "HC3", "T19b", "C18", "ES3", "G37",
                       "84a1523", "9e8ca5c", "73a1690", "SC-PR1-018", "GR-2000-P309-ATTACK-PROCEDURE", "GR-2000-P321-ATTACK-DAMAGE", "GR-2000-P321-PREVENTED-ELEMENTS",
                       "GR-2000-P322-PERSISTENT-EFFECTS", "CR-EFFECTS-AFTER-KO", "CR-STICKY-VS-PREVENTED", "CR-GAMBLE-VS-PREVENTED", "CR-TRANSPARENCY-NOT-FAILURE",
                       "UQ-COIN-IN-NULLIFIED-ELEMENT"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
