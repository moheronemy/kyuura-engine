"""v0.106（docs/counts-coins-compositions-v0.106.md）: 数とコインを組み合わせるポケモンの 11 枚（ワザ 21）と、自分のカウンターの追加と自分へのダメージ・「おもて」の数の表・
カードの枚数ぶんの上限つきのコイン・相手が取ったサイドの数・同じコインの追加のダメージと自分へのダメージ・名前と範囲で数えるダメージの共通の処理。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面。11 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録
（GR-2000-P309-ATTACK-PROCEDURE・GR-2000-P312-FIELD・GR-2000-P319-HP-AND-DAMAGE・GR-2000-P320-DAMAGE-FIGURE・GR-2000-P321-ATTACK-DAMAGE・GR-2000-P321-DAMAGE-ORDER・
GR-2000-P321-PREVENTED-ELEMENTS・GR-2000-P322-PERSISTENT-EFFECTS・GR-2000-P323-KNOCKOUT、v0.4b・v0.35・v0.39・v0.45・v0.49・v0.67 の FD1・v0.103 の発生元）。英語版の文面・現代のルール・
後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの
自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.106``）。
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
from kyuura_engine import zones as Z
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    DAMAGE_REDUCTION,
    DAMAGE_STEP_ORDER,
    REACTION_SWITCH,
    SELECT_ATTACK,
)
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.resolution import kernel as K
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.preflight import MAX_BRANCHES
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import (
    AttackBarrier,
    CannotUseOwnAttack,
    DamageReduction,
    ZeroDamageBelow,
)
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.log_audit import LATEST_FORMAT, log_problems
from tests.release_catalog import cards_after, cards_before
from tests.test_counter_keep_energy_protection_v0_101 import attack
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_unown_family_powers_v0_96 import TURN, board, same_answers, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "counts-coins-compositions-v0.106.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, F, L, G, PS = H.WATER, H.FIGHTING, H.LIGHTNING, H.GRASS, H.PSYCHIC
GRANBULL, SCYTHER, KABUTOPS, FARFETCHD, GEODUDE = "neo1-068", "neo2-008", "neo2-018", "neo3-046", "ES1-023"
VOLTORB, VOLTORB_QSG, NIDORINA, HAUNTER, SANDSLASH, SANDSLASH_QSG = "ES2-016", "QSG-025", "ES3-002", "ES3-023", "ES3-027", "QSG-034"
V0106 = (GRANBULL, SCYTHER, KABUTOPS, FARFETCHD, GEODUDE, VOLTORB, VOLTORB_QSG, NIDORINA, HAUNTER, SANDSLASH, SANDSLASH_QSG)
V0106_ATTACKS = [AttackKey(card, index) for card in V0106 for index in range(1 if card == SCYTHER else 2)]
DCE, MEW, TENTACRUEL, ELECTRODE = "PMCG1-096", "PR1-005", "GD2-004", "PMCG1-040"
ROCKET_VOLTORB, SURGES_VOLTORB, BASE_VOLTORB = "PMCG4-027", "GD3-007", "PMCG1-037"
NIDORAN_F, NIDORAN_M, JUNGLE_NIDORINA, NIDOKING, GIOVANNIS_NIDORAN_F = "ES1-006", "ES1-007", "PMCG2-008", "PMCG1-013", "PMCG6-003"
CHANSEY, CHARMANDER, RATTATA, CLEFABLE, MACHAMP, DITTO = H.CHANSEY, H.CHARMANDER, H.RATTATA, H.CLEFABLE, H.MACHAMP, H.DITTO
BELOW = {GRANBULL: ["neo1-061"], KABUTOPS: ["PMCG3-046", "PMCG3-035"], NIDORINA: [NIDORAN_F], HAUNTER: ["ES3-022"], SANDSLASH: ["ES2-020"], SANDSLASH_QSG: ["ES2-020"],
         ELECTRODE: [BASE_VOLTORB], JUNGLE_NIDORINA: ["PMCG2-001"], NIDOKING: ["PMCG1-005", "PMCG1-010"], CLEFABLE: [H.CLEFAIRY], MACHAMP: [H.MACHOP, H.MACHOKE],
         TENTACRUEL: ["GD2-003"], H.HAUNTER: [H.GASTLY]}

# 依頼で示された固定データの日本語（写しの文面と照らす。広い正規化をしない）。(HP, タイプ, 段階, (名前, 必要なエネルギー, ダメージの目安, 説明), ...)
RAGING_CHARGE = "自分にのっているダメージカウンターの数×10ダメージを追加する。その後、自分にも20ダメージ。"
FURY_CUTTER = "コインを4枚投げる。「おもて」が1枚なら10ダメージ、「おもて」が2枚なら20ダメージ、3枚なら40ダメージ、「おもて」が4枚なら80ダメージを追加する。"
HYDROCUTTER = "自分についている「エネルギーカード」の数ぶんコインを投げ、「おもて」の数×40のダメージ。このワザで投げることのできるコインは3枚まで。"
LEEK_SLAP = "次の自分の番、このカードは「ネギでつく」を使うことが出来ない。"
HARDEN = "このカードが次の相手の番で受ける20以下のダメージは、0になる。(ダメージ以外の効果はそのまま受ける)"
THUNDERSHOCK = "コインを投げて「おもて」なら、相手を「マヒ」状態にする。"
SPARK = "お互いの場にいる「ビリリダマ」の数×10のダメージを追加する。"
FAMILY = "自分のベンチにいる「ニドラン♂」「ニドラン♀」「ニドリーノ」「ニドリーナ」「ニドキング」「ニドクイン」の数×10のダメージを追加する。"
FURY_SWIPES = "コインを3枚投げ、「おもて」の数×30のダメージ。"
CONFUSE_RAY = "コインを投げて「おもて」なら、相手を「こんらん」状態にする。"
GRUDGE = "相手プレイヤーがすでに取りおえたサイドカードの数×10のダメージを追加する。"
SAND_CLOAK = "コインを投げて「おもて」なら、このカードは次の相手の番にダメージを受けない。(ダメージ以外の効果はそのまま)"
ROLLING_NEEDLE = "コインを3枚投げ、「おもて」の数×10のダメージを追加する。その後、自分にも「おもて」の数×10のダメージ。"
_VOLTORB = (30, "lightning", "basic", ("でんきショック", ("lightning",), "10", THUNDERSHOCK), ("みんなでスパーク", ("lightning", "lightning"), "20+", SPARK))
_SANDSLASH = (70, "fighting", "stage1", ("すながくれ", ("fighting",), None, SAND_CLOAK),
              ("ローリングニードル", ("fighting", "fighting", "fighting"), "40+", ROLLING_NEEDLE))
QUOTED = {
    GRANBULL: (70, "colorless", "stage1", ("たいあたり", ("colorless", "colorless"), "20", None),
               ("いかりのとっしん", ("colorless", "colorless", "colorless"), "10+", RAGING_CHARGE)),
    SCYTHER: (60, "grass", "basic", ("れんぞくぎり", ("grass", "grass"), "10+", FURY_CUTTER)),
    KABUTOPS: (90, "water", "stage2", ("きりさく", ("colorless",), "20", None), ("ハイドロカッター", ("fighting",), "40×", HYDROCUTTER)),
    FARFETCHD: (50, "colorless", "basic", ("かぜおこし", ("colorless",), "10", None), ("ネギでつく", ("colorless", "colorless", "colorless"), "40", LEEK_SLAP)),
    GEODUDE: (50, "fighting", "basic", ("たいあたり", ("colorless",), "10", None), ("かたくなる", ("fighting", "colorless"), None, HARDEN)),
    VOLTORB: _VOLTORB, VOLTORB_QSG: _VOLTORB,
    NIDORINA: (60, "grass", "stage1", ("なかまのちから", ("grass", "grass"), "10+", FAMILY), ("みだれひっかき", ("grass", "grass", "colorless"), "30×", FURY_SWIPES)),
    HAUNTER: (60, "psychic", "stage1", ("ぶきみなひかり", ("psychic",), None, CONFUSE_RAY), ("おんねん", ("psychic", "psychic"), "20+", GRUDGE)),
    SANDSLASH: _SANDSLASH, SANDSLASH_QSG: _SANDSLASH,
}
NIDO = ("ニドラン♂", "ニドラン♀", "ニドリーノ", "ニドリーナ", "ニドキング", "ニドクイン")
_VOLTORB_EFFECTS = (E.ParalyzeOnHeads(), E.DamagePlusPokemonCount(per=10, scope="both_in_play", names=("ビリリダマ",)))
_SANDSLASH_EFFECTS = (E.PreventDamageOnHeads(), E.CoinsBonusAndSelfDamagePerHeads(3, 10, 10))
EXPECTED = {
    (GRANBULL, 0): E.DamageOnly(), (GRANBULL, 1): E.DamagePlusOwnCountersThenSelfDamage(10, 20),
    (SCYTHER, 0): E.CoinsHeadsTableBonusDamage((0, 10, 20, 40, 80)),
    (KABUTOPS, 0): E.DamageOnly(), (KABUTOPS, 1): E.CappedCoinsPerAttachedEnergyCardsDamage(40, 3),
    (FARFETCHD, 0): E.DamageOnly(), (FARFETCHD, 1): E.DamageThenLockSelf(),
    (GEODUDE, 0): E.DamageOnly(), (GEODUDE, 1): E.ZeroDamageBelowNextTurn(30),
    **{(card, index): effect for card in (VOLTORB, VOLTORB_QSG) for index, effect in enumerate(_VOLTORB_EFFECTS)},
    (NIDORINA, 0): E.DamagePlusPokemonCount(per=10, scope="own_bench", names=NIDO), (NIDORINA, 1): E.CoinFlipDamage(coins=3, damage_per_heads=30),
    (HAUNTER, 0): E.ConfuseOnHeadsWithoutDamage(), (HAUNTER, 1): E.DamagePlusOpponentPrizesTaken(10),
    **{(card, index): effect for card in (SANDSLASH, SANDSLASH_QSG) for index, effect in enumerate(_SANDSLASH_EFFECTS)},
}
NEW_TYPES = (E.DamagePlusOwnCountersThenSelfDamage, E.CoinsHeadsTableBonusDamage, E.CappedCoinsPerAttachedEnergyCardsDamage, E.DamagePlusOpponentPrizesTaken,
             E.CoinsBonusAndSelfDamagePerHeads)


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


def damages(before, after, player):
    """プレイヤー ``player`` のポケモンが受けた、ワザのダメージの (基本となるダメージ, 最終ダメージ)。"""
    return [(e["steps"][0][1], e["amount"]) for e in new_events(before, after, "damage") if e["player"] == player and not e.get("retaliation")]


def use(state, card_id, index):
    return E.AttackUse(state.current_player, state.players[state.current_player].active.pokemon_id, AttackKey(card_id, index))


def uid_in_hand(state, card_id, player=0):
    return next(u for u in state.players[player].hand if state.cards[u].card_id == card_id)


def with_effects(state, player, *effects, keys=()):
    """``player`` のバトル場のポケモンに持続する効果を置き、効果を与えたログも置く（tests/helpers.py の build_test_state と同じ形。不変条件は効果とログの対応を確かめる）。"""
    pokemon = state.players[player].active
    pokemon.persistent_effects = (*pokemon.persistent_effects, *effects)
    for effect, key in zip(effects, keys or ("test",) * len(effects)):
        current, state.turn_number = state.turn_number, effect.created_turn
        state.add_event("persistent_effect_added", player=player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, persistent_effect=effect.kind,
                        source_card=effect.source_card, source_player=effect.source_player, active_turn=effect.active_turn, effect=key)
        state.turn_number = current
    return state


def placed_face_down(state, card_id, player=0):
    """マチスの秘策（手札）を使い、手札の ``card_id`` をうらにしてベンチに出す（v0.67）。"""
    played = apply_kernel(state, PlayTrainer(player, uid_in_hand(state, H.LT_SURGES_SECRET_PLAN, player)))
    return apply_kernel(played, ResolveDecision(player, played.decision.id, (uid_in_hand(played, card_id, player),)))


# ---------------------------------------------------------------- 1・2・3 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_entries_and_printed_texts(self):
        """11 枚・21 のワザの名前・必要なエネルギー・ダメージの目安・説明は依頼の日本語と同じ（目安なしは null で、0 ダメージではない）。特殊能力は 0。"""
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_106"]), V0106)
        self.assertEqual(len(V0106_ATTACKS), 21)
        for card, (hp, color, stage, *attacks) in QUOTED.items():
            definition = pool.definitions[card]
            self.assertEqual((definition.hp, definition.pokemon_type.value, definition.stage, definition.powers), (hp, color, stage, ()))
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
                    if display is None:
                        self.assertIsNone(printed.damage)  # 目安なし（0 ダメージの目安ではない）
        # カブトプスは水タイプで、ハイドロカッターの必要なエネルギーは闘 1（型やコストからデータを変えない）
        self.assertEqual((pool.definitions[KABUTOPS].pokemon_type.value, [c.value for c in pool.definitions[KABUTOPS].attacks[1].cost]), ("water", ["fighting"]))

    def test_shared_entries_keep_ids_and_records_apart(self):
        """同じデータの 2 組（SC-ES2-016・SC-ES3-027）は登録の値を共有し、id・採用の記録は別（同じにしない）。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        sources = json.loads((ROOT / "kyuura_engine/data/card_sources.json").read_text(encoding="utf-8"))["cards"]
        self.assertEqual(dict(E.SAME_DATA_CARDS_V0_106), {VOLTORB_QSG: VOLTORB, SANDSLASH_QSG: SANDSLASH})
        for new, original, group in ((VOLTORB_QSG, VOLTORB, "SC-ES2-016"), (SANDSLASH_QSG, SANDSLASH, "SC-ES3-027")):
            with self.subTest(new=new):
                self.assertEqual((cards[new]["same_card_group"], cards[original]["same_card_group"]), (group, group))
                self.assertEqual((cards[new]["name"]["ja"], cards[new]["pokemon"]), (cards[original]["name"]["ja"], cards[original]["pokemon"]))
                for index in range(2):
                    self.assertIs(DEFAULT_EFFECTS.attack_entry(new, index), DEFAULT_EFFECTS.attack_entry(original, index))
                self.assertNotEqual(sources[new]["notes"], sources[original]["notes"])
        for card in V0106:
            if card not in (VOLTORB_QSG, VOLTORB, SANDSLASH_QSG, SANDSLASH):
                self.assertIsNone(cards[card]["same_card_group"], card)

    def test_programs(self):
        """新しい型の要素の並び（既存の要素と小さな新しい値）。カードの id による分岐はない。"""
        builders = {
            E.DamagePlusOwnCountersThenSelfDamage(10, 20): (P.Damage(P.OPP, P.PlusOwnCounters(10)), P.Damage(P.SELF, P.Fixed(20), name="self_damage")),
            E.CoinsHeadsTableBonusDamage((0, 10, 20, 40, 80)): (P.Damage(P.OPP, P.PrintedPlusHeadsTable((0, 10, 20, 40, 80))),),
            E.CappedCoinsPerAttachedEnergyCardsDamage(40, 3): (P.Damage(P.OPP, P.HeadsTimesAttachedEnergyCards(40, 3)),),
            E.DamagePlusOpponentPrizesTaken(10): (P.Damage(P.OPP, P.PrintedPlusOpponentPrizesTaken(10)),),
            E.CoinsBonusAndSelfDamagePerHeads(3, 10, 10): (P.Coin("coin", count=3), P.Damage(P.OPP, P.PrintedPlusHeadsOfCoin("coin", 10)),
                                                           P.Damage(P.SELF, P.HeadsOfCoin("coin", 10), name="self_damage")),
            E.DamagePlusPokemonCount(per=10, scope="both_in_play", names=("ビリリダマ",)): (
                P.Damage(P.OPP, P.PrintedPlusPokemonCount(10, "both_in_play", ("ビリリダマ",))),),
            E.DamagePlusPokemonCount(per=10, scope="own_bench", names=NIDO): (P.Damage(P.OPP, P.PrintedPlusPokemonCount(10, "own_bench", NIDO)),),
            E.ZeroDamageBelowNextTurn(30): (P.SelfPersistent("zero_damage_below", amount=30),),
            E.DamageThenLockSelf(): (P.Damage(P.OPP, P.Printed()), P.SelfAttackLock(None)),
        }
        for effect, program in builders.items():
            with self.subTest(effect=effect):
                self.assertEqual(P.BUILDERS[type(effect)](effect), program)
        for cls in NEW_TYPES:
            self.assertIn(cls, H.ATTACK_TYPES_SINCE_V0_17)
            self.assertIs(cls.resolve, E.AttackEffect.resolve)
            self.assertEqual(cls.opponent_effect_elements, ())
        # コインは「おもて」の数だけを使う（先読みは数でまとめる）。ハイドロカッターの枚数は状態で決まる
        self.assertTrue(P.PrintedPlusHeadsTable.by_heads and P.HeadsTimesAttachedEnergyCards.by_heads)
        self.assertEqual(P.PrintedPlusHeadsTable((0, 10, 20, 40, 80)).local_coins, 4)
        self.assertEqual(P.PrintedPlusOpponentPrizesTaken.local_coins, 0)

    def test_reused_types_match_the_printed_text(self):
        """既存の型の 10 のワザは、既存の書き方のまま。ネギでつく・かたくなるは、ワザの名前・しきい値と結び付けた 1 通りを明示して加えた（一律の正規化・部分一致で通さない）。"""
        pool = load_card_pool()
        leek = pool.definitions[FARFETCHD].attacks[1]
        self.assertEqual(E.DamageThenLockSelf().check(leek), [])
        self.assertEqual(dict(E.LOCK_SELF_NAMED_TEXTS), {"ネギでつく": LEEK_SLAP})
        self.assertNotEqual(E.DamageThenLockSelf().check(dataclasses.replace(leek, name_ja="きあいずつき")), [])  # 名前の違うワザには当てはめない
        for changed in (LEEK_SLAP.replace("出来ない", "できない"), LEEK_SLAP.replace("使うことが出来ない", "使えない") + "。"):
            self.assertNotEqual(E.DamageThenLockSelf().check(dataclasses.replace(leek, text_ja=changed)), [])
        harden = pool.definitions[GEODUDE].attacks[1]
        self.assertEqual(E.ZeroDamageBelowNextTurn(30).check(harden), [])
        self.assertEqual(E.GEODUDE_HARDEN_TEXT, HARDEN)
        for threshold in (20, 40):
            self.assertNotEqual(E.ZeroDamageBelowNextTurn(threshold).check(harden), [])  # 「20以下」を「20未満」のしきい値にしない
        for changed in (HARDEN.replace("20以下", "20未満"), HARDEN.replace("(ダメージ以外の効果はそのまま受ける)", ""), HARDEN.replace("(", "（").replace(")", "）")):
            self.assertNotEqual(E.ZeroDamageBelowNextTurn(30).check(dataclasses.replace(harden, text_ja=changed)), [])
        self.assertEqual(E.zero_damage_below_texts(30)[2], E.HARDEN_TEXT)  # v0.105 のトランセルの書き方は変えない
        spark, family = pool.definitions[VOLTORB].attacks[1], pool.definitions[NIDORINA].attacks[0]
        for scope, names in (("own_in_play", ("ビリリダマ",)), ("own_bench", ("ビリリダマ",)), ("both_in_play", NIDO), ("own_bench", NIDO[:5]), ("own_in_play", NIDO)):
            with self.assertRaises(ValueError):  # 未知の範囲と名前の組は自動で受け付けない
                E.DamagePlusPokemonCount(per=10, scope=scope, names=names)
        self.assertNotEqual(E.DamagePlusPokemonCount(per=20, scope="both_in_play", names=("ビリリダマ",)).check(spark), [])
        self.assertNotEqual(E.DamagePlusPokemonCount(per=10, scope="both_in_play", names=("ビリリダマ",)).check(family), [])
        swipes = pool.definitions[NIDORINA].attacks[1]
        self.assertEqual(E.CoinFlipDamage(coins=3, damage_per_heads=30).check(swipes), [])
        self.assertNotEqual(E.CoinFlipDamage(coins=4, damage_per_heads=30).check(swipes), [])
        self.assertEqual(E.ParalyzeOnHeads().check(pool.definitions[VOLTORB].attacks[0]), [])
        self.assertEqual(E.ConfuseOnHeadsWithoutDamage().check(pool.definitions[HAUNTER].attacks[0]), [])
        self.assertEqual(E.PreventDamageOnHeads().check(pool.definitions[SANDSLASH].attacks[0]), [])
        for card, index in ((GRANBULL, 0), (KABUTOPS, 0), (FARFETCHD, 0), (GEODUDE, 0)):
            self.assertEqual(E.DamageOnly().check(pool.definitions[card].attacks[index]), [])

    def test_new_texts_are_bound_to_their_values(self):
        """新しい型の書き方は、値と結び付けた完全な一致だけ。似た既存の型（エネルギーの個数のコイン・「うら」の数の自分へのダメージ・コインのあるいかりのサンダーなど）には登録できない。"""
        pool = load_card_pool()
        raging = pool.definitions[GRANBULL].attacks[1]
        self.assertNotEqual(E.DamagePlusOwnCountersThenSelfDamage(10, 30).check(raging), [])
        self.assertNotEqual(E.DamagePlusOwnCountersThenSelfDamageOnTails(10, 20).check(raging), [])
        # v0.31 の DamagePlusOwnCounters（わるいブースターの「いかり」）の check は書き方を照らさない（既存の型。反動の要素を持たないので、いかりのとっしんには登録しない。docs 11 章）
        self.assertEqual(E.DamagePlusOwnCounters(10).check(raging), [])
        fury = pool.definitions[SCYTHER].attacks[0]
        with self.assertRaises(ValueError):
            E.CoinsHeadsTableBonusDamage((0, 10, 20, 30, 40))  # 表は書き方のあるものだけ
        with self.assertRaises(ValueError):
            E.CoinsHeadsTableBonusDamage([0, 10, 20, 40, 80])
        self.assertNotEqual(E.CoinsHeadsTimesBonusDamage(4, 10).check(fury), [])
        hydro = pool.definitions[KABUTOPS].attacks[1]
        for wrong in (E.CappedCoinsPerAttachedEnergyCardsDamage(40, 2), E.CappedCoinsPerAttachedEnergyCardsDamage(30, 3), E.CoinsPerAttachedEnergyDamage(40)):
            self.assertNotEqual(wrong.check(hydro), [])
        self.assertNotEqual(E.CappedCoinsPerAttachedEnergyCardsDamage(40, 3).check(dataclasses.replace(hydro, text_ja=HYDROCUTTER.replace("「エネルギーカード」", "「エネルギー」"))), [])
        grudge = pool.definitions[HAUNTER].attacks[1]
        self.assertNotEqual(E.DamagePlusOpponentPrizesTaken(20).check(grudge), [])
        self.assertNotEqual(E.DamagePlusOpponentPrizesTaken(10).check(dataclasses.replace(grudge, text_ja=GRUDGE.replace("相手プレイヤー", "自分"))), [])
        needle = pool.definitions[SANDSLASH].attacks[1]
        for wrong in (E.CoinsBonusAndSelfDamagePerHeads(3, 10, 20), E.CoinsBonusAndSelfDamagePerHeads(2, 10, 10), E.CoinsHeadsTimesBonusDamage(3, 10)):
            self.assertNotEqual(wrong.check(needle), [])
        self.assertNotEqual(E.CoinsBonusAndSelfDamagePerHeads(3, 10, 10).check(dataclasses.replace(needle, text_ja=ROLLING_NEEDLE.replace("自分にも「おもて」", "自分にも「うら」"))), [])

    def test_unregistered_without_the_v0_106_entries(self):
        """今回の登録だけを除くと、ちょうど 11 枚が未対応にもどる（ほかのカードは失われない）。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V0106_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V0106))
        self.assertEqual(set(V0106) & set(cards_before(read_extract(), "0.106")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.105")) & set(cards_before(read_extract(), "0.107")), set(V0106))

    def test_extract_keeps_sources_and_gaps(self):
        """転記元はグランブル・ストライク・カブトプスが nazonobasho.com、カモネギがポケモンWiki、7 枚が pcg-search.com。図鑑番号・レベルの欠けは補わない。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        hosts = {card: cards[card]["ja_text_source"].split("/")[2] for card in V0106}
        self.assertEqual(hosts, {GRANBULL: "nazonobasho.com", SCYTHER: "nazonobasho.com", KABUTOPS: "nazonobasho.com", FARFETCHD: "wiki.pokemonwiki.com",
                                 **{card: "pcg-search.com" for card in (GEODUDE, VOLTORB, VOLTORB_QSG, NIDORINA, HAUNTER, SANDSLASH, SANDSLASH_QSG)}})
        for card in V0106:
            expected = [] if card in (GRANBULL, SCYTHER, KABUTOPS, FARFETCHD) else ["pokemon.dex", "jp_print.level"]
            self.assertEqual(cards[card]["data_gaps"], expected, card)

    def test_adoption_records(self):
        """11 件の採用の記録（kyuura 73a1690・外部照合なし・kyuura の記録なし）。処理に使う文面は印刷の文面（説明文のない 4 つのワザは持たない）。"""
        sources = json.loads((ROOT / "kyuura_engine/data/card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine/data/research_links.json").read_text(encoding="utf-8"))["latest_descriptions"]["adopted_printed_text"]
        for card in V0106:
            record = sources[card]
            parts = [f"attack/{i}" for i, a in enumerate(QUOTED[card][3:]) if a[3] is not None]
            self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"], record["external_checks"], record["issues"]),
                             ("kyuura_data", "adopted", "73a169063463bbf7bcaa3137d70cbf9721d11534", [], [], []))
            self.assertEqual(record["play_text"], {part: "kyuura_printed_text" for part in parts})
            for part in parts:
                self.assertIn(f"{card}/{part}", links)
        for card in (GRANBULL, KABUTOPS, FARFETCHD, GEODUDE):
            self.assertNotIn(f"{card}/attack/0", links)


# ---------------------------------------------------------------- 4.1 節: いかりのとっしん


class RagingChargeTest(unittest.TestCase):
    def test_counters_before_the_recoil(self):
        """目安 10 + 相手へのダメージの時点の自分のカウンターの数 × 10 → その後、自分にも 20（別のダメージの要素）。反動で増えたカウンターから計算し直さない。"""
        for damage in (0, 30):
            state = board(mon(GRANBULL, (W, W, W), damage=damage), opponent=mon(CHANSEY))
            after = attack(state, 1)
            with self.subTest(damage=damage):
                self.assertEqual(kinds(state, after, "damage"), ["damage", "damage"])
                self.assertEqual(damages(state, after, 1), [(10 + damage, 10 + damage)])
                self.assertEqual(damages(state, after, 0), [(20, 20)])
                self.assertEqual(after.players[0].active.damage, damage + 20)
                profile = E.DamagePlusOwnCountersThenSelfDamage(10, 20).damage_profile(state, use(state, GRANBULL, 1))
                self.assertEqual((profile.opponent, profile.self_damage), ((10 + damage,), (20,)))
                audited(self, after)

    def test_base_damage_and_later_steps(self):
        """基本となるダメージ（1 段階）と、そのあとの段階（プラスパワーは相手へのダメージにも自分へのダメージにも 5 段階で +10。v0.10 のじごくぐるまと同じ）を区別する。"""
        state = board(mon(GRANBULL, (W, W, W), damage=30, trainers=[(H.PLUSPOWER, TURN)]), opponent=mon(CHANSEY))
        after = attack(state, 1)
        self.assertEqual((damages(state, after, 1), damages(state, after, 0)), ([(40, 50)], [(20, 30)]))

    def test_recoil_is_kept_when_the_opponent_takes_no_damage(self):
        """相手がダメージを受けない（かたまる・ミュウの［ニュートラルシールド］で 1 進化のグランブルのダメージを無効）ときも、原文にない条件で反動を消さない。"""
        for opponent in (mon(CHANSEY, prevent_damage=TURN - 1), mon(MEW, (PS,))):
            state = board(mon(GRANBULL, (W, W, W), damage=20), opponent=opponent)
            after = attack(state, 1)
            with self.subTest(opponent=opponent["card"]):
                self.assertEqual(kinds(state, after, "damage_prevented", "damage"), ["damage_prevented", "damage"])
                self.assertEqual(damages(state, after, 0), [(20, 20)])
                audited(self, after)

    def test_counterattack_after_both_damage_elements(self):
        """カイリキーの［はんげき］は、相手へのダメージと自分へのダメージのまとまりのあと（反応の窓の順番は既存のまま）。"""
        state = board(mon(GRANBULL, (W, W, W), damage=10), opponent=mon(MACHAMP, (F,)))
        after = attack(state, 1)
        self.assertEqual(kinds(state, after, "damage", "counterattack"), ["damage", "damage", "counterattack"])
        self.assertEqual(after.players[0].active.damage, 10 + 20 + 10)

    def test_flee_between_keeps_the_recoil_once(self):
        """相手の［にげこむ］（カスミのドククラゲ）の決定は、ダメージのまとまりのあと。複製・deepcopy・pickle から同じ答えで続けても、反動は 1 度だけ。"""
        state = board(mon(GRANBULL, (W, W, W), damage=30), opponent=mon(TENTACRUEL, (W, W)), opponent_bench=(RATTATA,))
        asked = attack(state, 1)
        self.assertEqual((asked.decision.kind, asked.decision.player), (REACTION_SWITCH, 1))
        self.assertEqual((damages(state, asked, 1), damages(state, asked, 0)), ([(40, 40)], [(20, 20)]))
        for choices in ((), asked.decision.options[:1]):
            done = same_answers(self, asked, choices)
            self.assertEqual((kinds(asked, done, "damage"), done.players[0].active.damage), ([], 50))

    def test_copied_charge_uses_the_copier(self):
        """相手のワザとして使う（ピクシーのゆびをふる）と、数えるのも反動を受けるのも使ったピクシー（印刷元のグランブルのカウンターで代用しない）。"""
        state = board(mon(CLEFABLE, (W,), damage=40), opponent=mon(GRANBULL, (W, W, W), damage=10))
        asked = attack(state, 0)
        self.assertEqual(asked.decision.kind, SELECT_ATTACK)
        done = answer(asked, (1,))
        self.assertEqual((damages(asked, done, 1), damages(asked, done, 0)), ([(50, 50)], [(20, 20)]))
        self.assertEqual(done.players[0].active.damage, 60)
        audited(self, done)


# ---------------------------------------------------------------- 4.2 節: れんぞくぎり


class FuryCutterTest(unittest.TestCase):
    def test_table_by_heads(self):
        """4 枚を投げ、「おもて」0〜4 枚で目安 10 に 0・10・20・40・80 を追加（基本となるダメージ 10・20・30・50・90。0 枚でも失敗ではない）。"""
        expected = {0: 10, 1: 20, 2: 30, 3: 50, 4: 90}
        for heads, base in expected.items():
            flips = (HD,) * heads + (TL,) * (4 - heads)
            state = board(mon(SCYTHER, (G, G)), opponent=mon(CHANSEY))
            after = attack(state, 0, *flips)
            with self.subTest(heads=heads):
                self.assertEqual(coins_of(state, after), ["heads"] * heads + ["tails"] * (4 - heads))
                self.assertEqual(damages(state, after, 1), [(base, base)])
                self.assertEqual(new_events(state, after, "attack_failed"), [])
                audited(self, after)
        profile = E.CoinsHeadsTableBonusDamage((0, 10, 20, 40, 80)).damage_profile(state, use(state, SCYTHER, 0))
        self.assertEqual(profile.opponent, (10, 20, 30, 50, 90))

    def test_coin_order_does_not_matter(self):
        """「おもて」の数だけを使う（並びで結果を変えない）。"""
        for flips in ((HD, TL, HD, TL), (TL, TL, HD, HD)):
            state = board(mon(SCYTHER, (G, G)), opponent=mon(CHANSEY))
            self.assertEqual(damages(state, attack(state, 0, *flips), 1), [(30, 30)])

    def test_weakness_comes_after_the_table(self):
        """表の値は基本となるダメージ（1 段階）で、弱点（草 ×2。イシツブテ）はそのあと。"""
        state = board(mon(SCYTHER, (G, G)), opponent=mon(GEODUDE, (F,)))
        self.assertEqual(damages(state, attack(state, 0, HD, HD, HD, TL), 1), [(50, 100)])

    def test_prevented_damage_keeps_the_v0_4b_question(self):
        """コインはダメージの量だけを決めるので、「ダメージを受けない」相手には v0.4b の問い（コインの前に止める）。たねのストライクはミュウも受ける。"""
        rejects(self, board(mon(SCYTHER, (G, G)), opponent=mon(CHANSEY, prevent_damage=TURN - 1)), UseAttack(0, 0), "UNRESOLVED_PREVENTED_COIN_DAMAGE")
        state = board(mon(SCYTHER, (G, G)), opponent=mon(MEW, (PS,)))
        self.assertEqual(damages(state, attack(state, 0, HD, HD, TL, TL), 1), [(30, 30)])

    def test_reduction_decision_keeps_the_base_and_coins(self):
        """お上品攻撃の減らす量の決定をまたいでも、確定した基本となるダメージ（50）とコインを運び、投げ直さない（複製・deepcopy・pickle からも 1 度だけ）。"""
        state = board(mon(SCYTHER, (G, G)), hand=(H.CHARITY,), opponent=mon(CHANSEY))
        state = apply_kernel(state, PlayTrainer(0, uid_in_hand(state, H.CHARITY)))
        asked = attack(state, 0, HD, HD, HD, TL)
        self.assertEqual((asked.decision.kind, asked.decision.options), (DAMAGE_REDUCTION, (0, 10, 20, 30, 40, 50)))
        done = same_answers(self, asked, (20,))
        self.assertEqual((damages(asked, done, 1), coins_of(asked, done)), ([(50, 30)], []))


# ---------------------------------------------------------------- 4.3 節: ハイドロカッター


class HydrocutterTest(unittest.TestCase):
    def test_card_count_with_a_cap_of_three(self):
        """自分についているエネルギーカードの枚数 n から min(n, 3) 枚を投げ、「おもて」の数 × 40。4 枚以上でも 3 枚。"""
        for energy, coins in (((F,), 1), ((F, W), 2), ((F, W, W), 3), ((F, W, W, W), 3), ((F, W, W, W, W), 3)):
            state = board(mon(KABUTOPS, energy), opponent=mon(CHANSEY))
            after = attack(state, 1, *(HD,) * coins)
            with self.subTest(energy=len(energy)):
                self.assertEqual(coins_of(state, after), ["heads"] * coins)
                self.assertEqual(damages(state, after, 1)[0][0], 40 * coins)
                profile = E.CappedCoinsPerAttachedEnergyCardsDamage(40, 3).damage_profile(state, use(state, KABUTOPS, 1))
                self.assertEqual(profile.opponent, tuple(40 * h for h in range(coins + 1)))
                audited(self, after)

    def test_cards_not_units(self):
        """無色2個エネルギーは 1 枚（2 個ではない）: 闘 1 枚 + 無色2個エネルギー 1 枚は 2 枚（エネルギーの個数 3 ではない）。「うら」なら 0 で失敗ではない。"""
        state = board(mon(KABUTOPS, (F, DCE)), opponent=mon(CHANSEY))
        self.assertEqual(len(E.attached_units(state, state.players[0].active)), 3)
        after = attack(state, 1, HD, TL)
        self.assertEqual((coins_of(state, after), damages(state, after, 1)), (["heads", "tails"], [(40, 40)]))
        after = attack(state, 1, TL, TL)
        self.assertEqual((damages(state, after, 1), new_events(state, after, "attack_failed")), ([(0, 0)], []))

    def test_zero_cards_flips_nothing_and_does_not_fail(self):
        """エネルギーカードが 0 枚なら投げず、基本となるダメージは 0（原文にない失敗にしない）。今の写しでは闘 1 を払う必要があり宣言では到達しないので、要素を直接処理する。"""
        state = board(mon(KABUTOPS), opponent=mon(CHANSEY))
        res = K.Resolution(state.clone())
        attacker = res.state.players[0].active
        fs = res.open_frame(K.FrameKind.ATTACK, parent=None, player=0, source_pid=attacker.pokemon_id, attack_key=AttackKey(KABUTOPS, 1))
        run = P.AttackRun(res, fs, P.BUILDERS[E.CappedCoinsPerAttachedEnergyCardsDamage](E.CappedCoinsPerAttachedEnergyCardsDamage(40, 3)),
                          load_card_pool().definitions[KABUTOPS].attacks[1])
        self.assertEqual(P.local_coins(run.program[0].base, run), 0)
        before = len(res.state.log)
        self.assertFalse(run.program[0].run(run))
        logged = res.state.log[before:]
        self.assertEqual([e["kind"] for e in logged if e["kind"] in ("coin_flip", "attack_failed")], [])
        self.assertEqual([e["steps"][0][1] for e in logged if e["kind"] == "damage"], [0])
        self.assertFalse(run.failed)

    def test_prevented_damage_keeps_the_v0_4b_question_only_when_flipping(self):
        rejects(self, board(mon(KABUTOPS, (F, W)), opponent=mon(CHANSEY, prevent_damage=TURN - 1)), UseAttack(0, 1), "UNRESOLVED_PREVENTED_COIN_DAMAGE")
        # 必要なエネルギー（闘 1）がなければ宣言を拒否する（状態・乱数・ログは変わらない。水タイプ・闘のコストのデータを変えない）
        rejects(self, board(mon(KABUTOPS, (W, W)), opponent=mon(CHANSEY)), UseAttack(0, 1), "INSUFFICIENT_ENERGY", IllegalActionError)

    def test_copied_cutter_counts_the_copiers_cards(self):
        """相手のワザとして使う（ピクシーのゆびをふる）と、数えるのはピクシーについているエネルギーカード（カブトプスの 3 枚ではない）。"""
        state = board(mon(CLEFABLE, (W,)), opponent=mon(KABUTOPS, (F, W, W)))
        done = answer(attack(state, 0), (1,), HD)
        self.assertEqual((coins_of(state, done), damages(state, done, 1)), (["heads"], [(40, 40)]))
        audited(self, done)


# ---------------------------------------------------------------- 4.5 節: おんねん


class GrudgeTest(unittest.TestCase):
    def test_prizes_the_opponent_has_taken(self):
        """相手プレイヤーがすでに取ったサイドの数 × 10 を目安 20 に追加（0 枚・複数枚）。自分が取った数・残っている数は使わない。"""
        for mine, theirs, base in ((6, 6, 20), (6, 4, 40), (2, 6, 20), (3, 1, 70)):
            state = board(mon(HAUNTER, (PS, PS)), opponent=mon(CHARMANDER), prizes=mine, opponent_prizes=theirs)
            after = attack(state, 1)
            with self.subTest(mine=mine, theirs=theirs):
                self.assertEqual(damages(state, after, 1), [(base, base)])
                self.assertEqual(E.DamagePlusOpponentPrizesTaken(10).damage_profile(state, use(state, HAUNTER, 1)).opponent, (base,))
                audited(self, after)

    def test_prizes_taken_by_a_trainer_count(self):
        """きぜつ以外で取ったサイド（マチスの交渉。お互いに 1 枚ずつ取る）も数える。"""
        state = board(mon(HAUNTER, (PS, PS)), hand=(H.LT_SURGES_TREATY,), opponent=mon(CHARMANDER))
        asked = apply_kernel(state, PlayTrainer(0, uid_in_hand(state, H.LT_SURGES_TREATY)))
        accepted = answer(asked, asked.decision.options)
        while accepted.decision is not None:
            accepted = answer(accepted, accepted.decision.options[:1])
        self.assertEqual((len(accepted.players[0].prizes), len(accepted.players[1].prizes)), (5, 5))
        self.assertEqual(kinds(state, accepted, "trainer_take_prize"), ["trainer_take_prize", "trainer_take_prize"])
        after = attack(accepted, 1)
        self.assertEqual(damages(accepted, after, 1), [(30, 30)])
        audited(self, after)

    def test_swaps_and_reveals_do_not_change_the_count(self):
        """サイドを見せる・入れかえる・同じ枚数をもどして置き直す処理は、取った数に加えない（枚数を変えない）。準備で置く数は規則の値で、6 を直に書かない。"""
        state = board(mon(HAUNTER, (PS, PS)), opponent=mon(CHARMANDER), opponent_prizes=4)
        self.assertEqual(E.prizes_taken(state, 1), 2)
        for change in (lambda s: Z.swap_prize_with_deck_top(s, 1, 0, power="test"),
                       lambda s: Z.reveal_prize(s, 1, 0, trainer=0),
                       lambda s: Z.deck_top_to_prizes(s, 1, len(Z.prizes_to_deck(s, 1, trainer=0, looker=0)), trainer=0)):
            changed = state.clone()
            change(changed)
            self.assertEqual(E.prizes_taken(changed, 1), 2)
        fewer = state.clone()
        fewer.rules = dataclasses.replace(state.rules, prize_count=4)
        self.assertEqual(E.prizes_taken(fewer, 1), 0)

    def test_copied_grudge_uses_the_copiers_opponent(self):
        """相手のワザとして使う（ピクシーのゆびをふる）と、「相手プレイヤー」は使ったピクシーの相手（ゴーストの持ち主）。"""
        state = board(mon(CLEFABLE, (W,)), opponent=mon(HAUNTER, (PS, PS)), prizes=2, opponent_prizes=5)
        done = answer(attack(state, 0), (1,))
        self.assertEqual(damages(state, done, 1), [(30, 30)])  # 自分（ピクシーの持ち主）が取った 4 枚は数えない
        audited(self, done)

    def test_mew_voids_the_evolved_haunter(self):
        """1 進化のゴーストのおんねんは、ミュウの［ニュートラルシールド］でダメージが無効（発生元の今の姿の段階）。"""
        state = board(mon(HAUNTER, (PS, PS)), opponent=mon(MEW, (PS,)), opponent_prizes=3)
        after = attack(state, 1)
        self.assertEqual(kinds(state, after, "damage_prevented", "damage"), ["damage_prevented"])


# ---------------------------------------------------------------- 4.1 節: ローリングニードル


class RollingNeedleTest(unittest.TestCase):
    def test_one_group_for_both_damages(self):
        """3 枚を 1 組で投げ、同じ「おもて」の数 h で相手に 40 + 10h、その後、自分にも 10h（「うら」の数ではない。別のコインを投げない）。h = 0 なら自分への基本は 0。"""
        for heads in range(4):
            flips = (HD,) * heads + (TL,) * (3 - heads)
            state = board(mon(SANDSLASH, (F, F, F)), opponent=mon(RATTATA))
            after = attack(state, 1, *flips)
            with self.subTest(heads=heads):
                self.assertEqual(len(coins_of(state, after)), 3)
                self.assertEqual(kinds(state, after, "damage"), ["damage", "damage"])
                self.assertEqual(damages(state, after, 1)[0][0], 40 + 10 * heads)
                self.assertEqual(damages(state, after, 0), [(10 * heads, 10 * heads)])
                audited(self, after)
        profile = E.CoinsBonusAndSelfDamagePerHeads(3, 10, 10).damage_profile(state, use(state, SANDSLASH, 1))
        self.assertEqual(profile.pairs(), ((40, 0), (50, 10), (60, 20), (70, 30)))

    def test_self_damage_survives_a_void_on_the_opponent(self):
        """コインは自分へのダメージも決めるので、相手が「ダメージを受けない」（かたまる）・「ワザをうけない」（バリアー）・ミュウの［ニュートラルシールド］でも投げ、相手への
        ダメージだけを無効にし、自分へのダメージは受ける（v0.4b・HC3 の問いにならない）。"""
        barrier = board(mon(SANDSLASH, (F, F, F)), opponent=mon(CHANSEY))
        target = barrier.players[1].active
        with_effects(barrier, 1, AttackBarrier(target.card, 1, TURN - 1, TURN), keys=("PMCG1-041#1",))
        for state in (board(mon(SANDSLASH, (F, F, F)), opponent=mon(CHANSEY, prevent_damage=TURN - 1)), barrier,
                      board(mon(SANDSLASH, (F, F, F)), opponent=mon(MEW, (PS,)))):
            after = attack(state, 1, HD, HD, TL)
            with self.subTest(opponent=state.cards[state.players[1].active.card].card_id):
                self.assertEqual(len(coins_of(state, after)), 3)
                self.assertEqual(kinds(state, after, "damage_prevented", "damage"), ["damage_prevented", "damage"])
                self.assertEqual(damages(state, after, 0), [(20, 20)])

    def test_transparency_evades_only_the_opponent_damage(self):
        """相手の化石の秘密のゴースト（「とうめい」）が受けなかった（コインの「おもて」）ときも、同じ組の自分へのダメージは受ける（T19b の問いにならない。コインは自分へのダメージも
        決めるので投げる）。いかりのとっしんの反動も同じ。"""
        for evade, received in ((HD, False), (TL, True)):
            state = board(mon(SANDSLASH, (F, F, F)), opponent=mon(H.HAUNTER, (PS,)))
            after = attack(state, 1, HD, TL, TL, evade)
            with self.subTest(evade=evade):
                self.assertEqual(len(new_events(state, after, "attack_evaded")), 0 if received else 1)
                self.assertEqual(damages(state, after, 0), [(10, 10)])
            state = board(mon(GRANBULL, (W, W, W), damage=10), opponent=mon(H.HAUNTER, (PS,)))
            after = attack(state, 1, evade)
            with self.subTest(evade=evade, attack="raging"):
                self.assertEqual(damages(state, after, 0), [(20, 20)])

    def test_weakness_applies_to_the_opponent_damage_only(self):
        """相手（ラッキー。闘の弱点）への 50 は 100、自分への 10 は自分の弱点・抵抗力で計算（サンドパンは闘に弱点がない）。"""
        state = board(mon(SANDSLASH, (F, F, F)), opponent=mon(CHANSEY))
        after = attack(state, 1, HD, TL, TL)
        self.assertEqual((damages(state, after, 1), damages(state, after, 0)), ([(50, 100)], [(10, 10)]))

    def test_reaction_window_after_the_group(self):
        """［はんげき］・［にげこむ］は、相手と自分へのダメージのまとまりのあと。［にげこむ］の決定をまたいでも、コインを投げ直さず、自分へのダメージは 1 度だけ。"""
        state = board(mon(SANDSLASH, (F, F, F)), opponent=mon(MACHAMP, (F,)))
        after = attack(state, 1, HD, TL, TL)
        self.assertEqual(kinds(state, after, "damage", "counterattack"), ["damage", "damage", "counterattack"])
        state = board(mon(SANDSLASH, (F, F, F)), opponent=mon(TENTACRUEL, (W, W)), opponent_bench=(RATTATA,))
        asked = attack(state, 1, HD, HD, TL)
        self.assertEqual((asked.decision.kind, damages(state, asked, 0)), (REACTION_SWITCH, [(20, 20)]))
        done = same_answers(self, asked, asked.decision.options[:1])
        self.assertEqual((coins_of(asked, done), kinds(asked, done, "damage"), done.players[0].active.damage), ([], [], 20))

    def test_reduction_decision_keeps_the_shared_coins(self):
        """お上品攻撃の減らす量の決定（相手へのダメージ）をまたいでも、同じコインの組で自分へのダメージを決める（投げ直さない）。"""
        state = board(mon(SANDSLASH, (F, F, F)), hand=(H.CHARITY,), opponent=mon(RATTATA))
        state = apply_kernel(state, PlayTrainer(0, uid_in_hand(state, H.CHARITY)))
        asked = attack(state, 1, HD, HD, HD)
        self.assertEqual(asked.decision.kind, DAMAGE_REDUCTION)
        done = same_answers(self, asked, (10,))
        self.assertEqual((coins_of(asked, done), damages(asked, done, 1)[0], damages(asked, done, 0)), ([], (70, 130), [(30, 30)]))  # コラッタは闘の弱点 ×2 のあと −10

    def test_lookahead_keeps_the_pair(self):
        """先読み・宣言の前の候補は、相手と自分へのダメージを同じコインの組として扱う: ダメージ 60 のサンドパン（HP 70）が、ダメージ 30 のカイリキー（［はんげき］）に使うと、
        「おもて」0 枚（40・0）ではカイリキーはきぜつせず、3 枚（70・30）では自分へのダメージで先にきぜつする（C15）ので、C18 には当たらない。組を独立にすると（70・0）で止まってしまう。
        カイリキーのダメージが 60 なら、（40・0）で本当に C18 に当たるので止める。"""
        state = board(mon(SANDSLASH, (F, F, F), damage=60), opponent=mon(MACHAMP, (F,), damage=30))
        effect = DEFAULT_EFFECTS.attack_entry(SANDSLASH, 1).effect
        profile = effect.damage_profile(state, use(state, SANDSLASH, 1))
        self.assertIsNone(E.counterattack_double_knockout_problem(state, use(state, SANDSLASH, 1), effect))
        independent = E.DamageProfile(opponent=profile.opponent, self_damage=profile.self_damage)
        with mock.patch.object(E.CoinsBonusAndSelfDamagePerHeads, "damage_profile", lambda self, s, u: independent):
            self.assertIsNotNone(E.counterattack_double_knockout_problem(state, use(state, SANDSLASH, 1), effect))
        for mode in ("derived", "derived_full", "legacy"):
            tails = apply_kernel(with_coin_results(state, TL, TL, TL), UseAttack(0, 1), preflight=mode)
            heads = apply_kernel(with_coin_results(state, HD, HD, HD), UseAttack(0, 1), preflight=mode)
            with self.subTest(mode=mode):
                self.assertEqual(kinds(state, tails, "damage", "counterattack", "knock_out"), ["damage", "damage", "counterattack", "knock_out"])
                self.assertEqual(kinds(state, heads, "damage", "counterattack", "knock_out"), ["damage", "damage", "knock_out", "knock_out"])
        weak = board(mon(SANDSLASH, (F, F, F), damage=60), opponent=mon(MACHAMP, (F,), damage=60))
        rejects(self, with_coin_results(weak, TL, TL, TL), UseAttack(0, 1), "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")

    def test_esp_redoes_the_group_together(self):
        """ナツメのESP（ナツメのポケモンでないサンドパンにつけた盤面。やり直しを選ぶと既存の ES3）: やり直さない答えは、最初の 3 枚の組で相手と自分を 1 度だけ処理する。"""
        state = board(mon(SANDSLASH, (F, F, F), trainers=[(H.SABRINAS_ESP, TURN)]), opponent=mon(RATTATA))
        asked = attack(state, 1, HD, HD, TL)
        self.assertEqual((asked.decision.kind, asked.decision.context_value("unresolved_code")), ("esp_redo", "UNRESOLVED_ESP_HOLDER_NOT_SABRINAS"))
        self.assertEqual(kinds(state, asked, "damage"), [])
        done = same_answers(self, asked, ())
        self.assertEqual((coins_of(asked, done), damages(asked, done, 1)[0][0], damages(asked, done, 0)), ([], 60, [(20, 20)]))

    def test_copied_needle_hurts_the_copier(self):
        state = board(mon(CLEFABLE, (W,)), opponent=mon(SANDSLASH, (F, F, F)))
        done = answer(attack(state, 0), (1,), HD, TL, HD)
        self.assertEqual((damages(state, done, 1)[0][0], damages(state, done, 0)), (60, [(20, 20)]))
        audited(self, done)

    def test_shared_card_uses_the_same_processing(self):
        state = board(mon(SANDSLASH_QSG, (F, F, F)), opponent=mon(RATTATA))
        after = attack(state, 1, HD, TL, TL)
        self.assertEqual((damages(state, after, 1)[0][0], damages(state, after, 0)), (50, [(10, 10)]))


# ---------------------------------------------------------------- 4.4 節: 名前と範囲で数える


class CountTest(unittest.TestCase):
    def test_spark_counts_both_fields_by_current_name(self):
        """お互いのバトル場とベンチの、今の姿の名前が「ビリリダマ」のポケモン（ワザを使ったポケモンも）1 匹につき 10 を目安 20 へ。所有者名つきの別名（マチスのビリリダマ）・
        進化の下に重なったカード（マルマインの下のビリリダマ）は数えない。"""
        cases = (((), (), 40), ((VOLTORB_QSG,), (), 50), ((VOLTORB_QSG, mon(ELECTRODE)), (SURGES_VOLTORB, ROCKET_VOLTORB), 60))
        for bench, opponent_bench, base in cases:
            state = board(mon(VOLTORB, (L, L)), bench=bench, opponent=mon(VOLTORB), opponent_bench=opponent_bench)
            after = attack(state, 1)
            with self.subTest(bench=bench, opponent_bench=opponent_bench):
                self.assertEqual(damages(state, after, 1)[0][0], base)
                self.assertEqual(E.DamagePlusPokemonCount(per=10, scope="both_in_play", names=("ビリリダマ",)).damage_profile(state, use(state, VOLTORB, 1)).opponent,
                                 (base,))
        alone = board(mon(VOLTORB, (L, L)), bench=(), opponent=mon(CHARMANDER), opponent_bench=())
        self.assertEqual(damages(alone, attack(alone, 1), 1)[0][0], 30)  # 自分だけでも数える

    def test_transformed_ditto_counts_as_its_current_form(self):
        """［へんしん］のメタモン（相手のビリリダマと同じ姿）は、今の姿の名前「ビリリダマ」で数え、みんなでスパークも使える。"""
        state = board(mon(DITTO, (L, L)), bench=(VOLTORB_QSG, mon(ELECTRODE)), opponent=mon(VOLTORB, (L,)), opponent_bench=(SURGES_VOLTORB, ROCKET_VOLTORB))
        after = attack(state, 1)
        self.assertEqual(damages(state, after, 1)[0][0], 60)

    def test_family_counts_only_the_own_bench(self):
        """自分のベンチの、説明の 6 つの名前（完全一致）のポケモンだけ。自分のバトル場（ワザを使ったニドリーナ）・相手の場・サカキのニドラン♀は数えない。"""
        bench = (NIDORAN_F, mon(JUNGLE_NIDORINA), mon(NIDOKING), GIOVANNIS_NIDORAN_F)
        state = board(mon(NIDORINA, (G, G)), bench=bench, opponent=mon(CHANSEY), opponent_bench=(NIDORAN_M,))
        after = attack(state, 0)
        self.assertEqual(damages(state, after, 1), [(40, 40)])
        empty = board(mon(NIDORINA, (G, G)), bench=(RATTATA,), opponent=mon(NIDORAN_F), opponent_bench=(NIDORAN_M,))
        self.assertEqual(damages(empty, attack(empty, 0), 1), [(10, 10)])

    def test_face_down_cards_stop_without_revealing(self):
        """うらのカード（マチスの秘策）の名前は読めないので、範囲にあれば FD1 で止める（本当のカードによらず同じ。都合よく除外しない）。範囲の外（なかまのちからの相手の場）なら止めない。"""
        for hidden in (VOLTORB_QSG, RATTATA):
            state = placed_face_down(board(mon(VOLTORB, (L, L)), bench=(), hand=(H.LT_SURGES_SECRET_PLAN, hidden), opponent=mon(CHARMANDER), opponent_bench=()), hidden)
            with self.subTest(hidden=hidden):
                rejects(self, state, UseAttack(0, 1), "UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY")
        own = placed_face_down(board(mon(NIDORINA, (G, G)), bench=(), hand=(H.LT_SURGES_SECRET_PLAN, NIDORAN_F), opponent=mon(CHARMANDER)), NIDORAN_F)
        rejects(self, own, UseAttack(0, 0), "UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY")
        theirs = board(mon(NIDORINA, (G, G)), bench=(NIDORAN_F,), opponent=mon(CHARMANDER), opponent_hand=(H.LT_SURGES_SECRET_PLAN, NIDORAN_M), opponent_bench=(),
                       current=1, turn=TURN + 1)
        theirs = apply_kernel(placed_face_down(theirs, NIDORAN_M, player=1), EndTurn(1))
        self.assertTrue(any(theirs.is_face_down(p) for p in theirs.players[1].bench))
        after = attack(theirs, 0)
        self.assertEqual(damages(theirs, after, 1), [(20, 20)])  # 自分のベンチのニドラン♀だけ（相手の場のうらのカードは範囲の外なので読まない）

    def test_copied_counts_use_the_copier_side(self):
        """相手のワザとして使う（ピクシーのゆびをふる）なかまのちからは、使ったピクシーの持ち主のベンチを数える。"""
        state = board(mon(CLEFABLE, (W,)), bench=(NIDORAN_F, NIDORAN_M), opponent=mon(NIDORINA, (G, G)), opponent_bench=(NIDORAN_F,))
        done = answer(attack(state, 0), (0,))
        self.assertEqual(damages(state, done, 1), [(30, 30)])
        audited(self, done)


# ---------------------------------------------------------------- 4.6 節: かたくなる・ネギでつく・既存の型


class HardenTest(unittest.TestCase):
    def harden(self, opponent):
        state = board(mon(GEODUDE, (F, W)), opponent=opponent)
        after = attack(state, 1)
        self.assertEqual([e["persistent_effect"] for e in new_events(state, after, "persistent_effect_added")], ["zero_damage_below"])
        return after

    def test_twenty_or_less_is_zero_and_thirty_passes(self):
        """次の相手の番、p.321 の 8 段階のダメージで決める: コラッタのかみつく 20 → 0、プラスパワーで 30 → そのまま（しきい値 30。20 以下が 0）。"""
        for trainers, expected in (((), 0), (((H.PLUSPOWER, TURN + 1),), 30)):
            ready = self.harden(mon(RATTATA, (F,), trainers=list(trainers)))
            after = attack(ready, 0, player=1)
            with self.subTest(trainers=trainers):
                self.assertEqual(after.players[0].active.damage, expected)
                audited(self, after)

    def test_effects_other_than_damage_still_happen(self):
        """「(ダメージ以外の効果はそのまま受ける)」: でんきショック 10 は 0 になるが、「おもて」のマヒは受ける（計算の前の一律の防護ではない）。"""
        ready = self.harden(mon(VOLTORB, (L,)))
        after = attack(ready, 0, HD, player=1)
        self.assertEqual((after.players[0].active.damage, after.players[0].active.conditions.paralyzed is not None), (0, True))
        self.assertEqual(new_events(ready, after, "damage_prevented"), [])

    def test_order_with_another_step_8_effect(self):
        """同じ 8 段階のちいさくなる（−20）があり、順番で結果が変わる（40 → 20 か 0）なら、受けるポケモンの持ち主が順番を選ぶ（v0.35 の決定）。"""
        state = board(mon(SCYTHER, (G, G)), opponent=mon(GEODUDE, (F, W)))
        geodude = state.players[1].active
        with_effects(state, 1, ZeroDamageBelow(geodude.card, 1, TURN - 1, TURN, 30), DamageReduction(geodude.card, 1, TURN - 1, TURN, 20),
                     keys=(f"{GEODUDE}#1", "test"))
        asked = attack(state, 0, HD, TL, TL, TL)
        self.assertEqual((asked.decision.kind, asked.decision.player, asked.decision.options), (DAMAGE_STEP_ORDER, 1, (0, 1)))
        results = {o: answer(asked, (o,)).players[1].active.damage for o in asked.decision.options}
        self.assertEqual(sorted(results.values()), [0, 20])
        done = same_answers(self, asked, (0,))  # 順番の決定をまたいでも、れんぞくぎりのコインを投げ直さず、基本となるダメージ（20）を運ぶ
        self.assertEqual((coins_of(asked, done), [e["steps"][0][1] for e in new_events(asked, done, "damage")]), ([], [20]))


class LeekSlapTest(unittest.TestCase):
    def test_locks_only_this_attack_on_the_next_own_turn(self):
        state = board(mon(FARFETCHD, (W, W, W)), opponent=mon(CHANSEY))
        done = attack(state, 1)
        self.assertEqual(len([e for e in done.players[0].active.persistent_effects if isinstance(e, CannotUseOwnAttack)]), 1)
        mine = apply_kernel(done, EndTurn(1))
        rejects(self, mine, UseAttack(0, 1), "ATTACK_LOCKED", IllegalActionError)
        apply_kernel(mine, UseAttack(0, 0))  # かぜおこしは使える
        later = apply_kernel(apply_kernel(mine, EndTurn(0)), EndTurn(1))
        apply_kernel(later, UseAttack(0, 1))

    def test_returning_to_the_bench_ends_the_lock(self):
        """ベンチにもどると消える（GR-2000-P322-PERSISTENT-EFFECTS）。もう一度バトル場に出れば使える。"""
        state = board(mon(FARFETCHD, (W, W, W)), bench=(RATTATA,), hand=(H.SWITCH, H.SWITCH), opponent=mon(CHANSEY))
        mine = apply_kernel(attack(state, 1), EndTurn(1))
        out = apply_kernel(mine, PlayTrainer(0, uid_in_hand(mine, H.SWITCH)))
        out = answer(out, out.decision.options[:1]) if out.decision is not None else out
        back = apply_kernel(out, PlayTrainer(0, uid_in_hand(out, H.SWITCH)))
        back = answer(back, back.decision.options[:1]) if back.decision is not None else back
        self.assertEqual(back.cards[back.players[0].active.card].card_id, FARFETCHD)
        apply_kernel(back, UseAttack(0, 1))

    def test_flee_decision_keeps_the_lock_once(self):
        """相手の［にげこむ］の決定（ダメージのあと）をまたいでも、禁止は 1 度だけ付ける（複製・deepcopy・pickle からも同じ）。"""
        state = board(mon(FARFETCHD, (W, W, W)), opponent=mon(TENTACRUEL, (W, W)), opponent_bench=(RATTATA,))
        asked = attack(state, 1)
        self.assertEqual((asked.decision.kind, kinds(state, asked, "persistent_effect_added")), (REACTION_SWITCH, []))
        done = same_answers(self, asked, asked.decision.options[:1])
        self.assertEqual([e["persistent_effect"] for e in new_events(asked, done, "persistent_effect_added")], [CannotUseOwnAttack.kind])

    def test_copied_lock_keeps_the_existing_unsupported_stop(self):
        state = board(mon(CLEFABLE, (W,)), opponent=mon(FARFETCHD, (W, W, W)))
        rejects(self, attack(state, 0), lambda s: ResolveDecision(0, s.decision.id, (1,)), "UNSUPPORTED_COPIED_ATTACK")


class ReusedTypeTest(unittest.TestCase):
    def test_existing_types(self):
        """でんきショック（目安 10 →「おもて」でマヒ）・ぶきみなひかり（ダメージなし。「おもて」でこんらん）・みだれひっかき（3 枚の「おもて」× 30）・すながくれ（「おもて」で
        次の相手の番にダメージを受けない。ダメージ以外の効果は受ける）。"""
        state = board(mon(VOLTORB, (L,)), opponent=mon(CHARMANDER))
        after = attack(state, 0, HD)
        self.assertEqual((damages(state, after, 1), after.players[1].active.conditions.paralyzed is not None), ([(10, 10)], True))
        state = board(mon(HAUNTER, (PS,)), opponent=mon(CHARMANDER))
        after = attack(state, 0, HD)
        self.assertEqual((kinds(state, after, "damage"), after.players[1].active.conditions.confused), ([], True))
        state = board(mon(NIDORINA, (G, G, G)), opponent=mon(CHANSEY))
        self.assertEqual(damages(state, attack(state, 1, HD, TL, HD), 1), [(60, 60)])
        state = board(mon(SANDSLASH, (F,)), opponent=mon(VOLTORB, (L,)))
        cloaked = attack(state, 0, HD)
        after = attack(cloaked, 0, HD, player=1)
        self.assertEqual((kinds(cloaked, after, "damage_prevented"), after.players[0].active.damage, after.players[0].active.conditions.paralyzed is not None),
                         (["damage_prevented"], 0, True))


# ---------------------------------------------------------------- 8 章: 決定・再開・先読み・保存


class DecisionTest(unittest.TestCase):
    def test_invalid_answers_change_nothing(self):
        """［にげこむ］の決定への不正な答え（選べないポケモン・答えるプレイヤーの違い）は、状態・乱数・ログ・決定を変えずに拒否する（HALTED にしない）。"""
        asked = attack(board(mon(SANDSLASH, (F, F, F)), opponent=mon(TENTACRUEL, (W, W)), opponent_bench=(RATTATA,)), 1, HD, TL, TL)
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
        cases = ((board(mon(GRANBULL, (W, W, W), damage=30), opponent=mon(CHANSEY)), 1, ()), (board(mon(SCYTHER, (G, G)), opponent=mon(CHANSEY)), 0, (HD, TL, HD, HD)),
                 (board(mon(KABUTOPS, (F, W, W, W)), opponent=mon(CHANSEY)), 1, (HD, HD, TL)), (board(mon(HAUNTER, (PS, PS)), opponent=mon(CHANSEY), opponent_prizes=3), 1, ()),
                 (board(mon(SANDSLASH, (F, F, F)), opponent=mon(MACHAMP, (F,))), 1, (HD, TL, HD)),
                 (board(mon(VOLTORB, (L, L)), bench=(VOLTORB_QSG,), opponent=mon(VOLTORB)), 1, ()), (board(mon(GEODUDE, (F, W))), 1, ()),
                 (board(mon(FARFETCHD, (W, W, W))), 1, ()))
        for state, index, flips in cases:
            results = [snap(apply_kernel(with_coin_results(state, *flips), UseAttack(0, index), preflight=mode)) for mode in ("derived", "derived_full", "legacy")]
            with self.subTest(card=state.cards[state.players[0].active.card].card_id, index=index):
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0], results[2])


# ---------------------------------------------------------------- 9 章: ログの監査


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v106_problems``）は、エンジンの値（``PlusOwnCounters``・``PrintedPlusHeadsTable``・``HeadsTimesAttachedEnergyCards``・``prizes_taken``・
    ``counted_pokemon``）を読まずに、ログから組み立てた場とこのワザのログで確かめる。エンジンの処理を一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py の局。
    v0.106 のワザが出る組と seed）で、監査がそれを見つける（誤らせなければ、同じ局は監査を通る）。"""

    GAMES = ((("C106", "E106"), 0), (("E106", "C106"), 2), (("E106", "F106"), 2), (("C106", "P31"), 2), (("E106", "P31"), 1))

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
                self.assertTrue(any(key.startswith("attack_") for key in result["v106"]))

    def test_audit_finds_a_recomputed_recoil_base(self):
        """いかりのとっしんの相手への基本となるダメージを、反動のあとのカウンター（+2 個）で計算した。"""

        def later(self, run, flips):
            return run.attack.damage + (run.attacker().damage // run.state.rules.damage_per_counter + 2) * self.per

        self.assertTrue([p for _, problems in self.results(P.PlusOwnCounters, "value", later) for p in problems if "neo1-068" in p])

    def test_audit_finds_a_final_value_table(self):
        """れんぞくぎりの表の値を目安に足さずに使った。"""

        def table_only(self, run, flips):
            return self.bonuses[0 if flips is None else flips.heads]

        self.assertTrue([p for _, problems in self.results(P.PrintedPlusHeadsTable, "value", table_only) for p in problems if "neo2-008" in p])

    def test_audit_finds_a_separate_self_coin(self):
        """ローリングニードルの自分へのダメージを、同じ組の「おもて」でなく「うら」の数で決めた。"""

        def tails(self, run, flips):
            return run.fs.coins[self.coin].tails * self.per

        self.assertTrue([p for _, problems in self.results(P.HeadsOfCoin, "value", tails) for p in problems if "ES3-027" in p or "QSG-034" in p])

    def test_audit_finds_a_card_count_off_by_one(self):
        """ハイドロカッターのコインを、ついているエネルギーカードの枚数より 1 枚少なく投げた。"""

        def fewer(self, run):
            return max(0, min(E.attached_energy_cards(run.state, run.attacker()), self.max_coins) - 1)

        self.assertTrue([p for _, problems in self.results(P.HeadsTimesAttachedEnergyCards, "coin_count", fewer) for p in problems if "neo2-018" in p])

    def test_audit_finds_prizes_of_the_wrong_player(self):
        """おんねんで、相手でなく自分が取ったサイドの数を数えた。"""

        def own(self, run, flips):
            return run.attack.damage + E.prizes_taken(run.state, run.player) * self.per

        self.assertTrue([p for _, problems in self.results(P.PrintedPlusOpponentPrizesTaken, "value", own) for p in problems if "ES3-023" in p])

    def test_audit_finds_counts_by_the_wrong_side(self):
        """みんなでスパーク・なかまのちからで、自分の場だけ（・相手の控えも）を数えた。"""
        original = P.counted_pokemon

        def own_only(state, player, scope, names):
            return original(state, player, "own_in_play", names)

        self.assertTrue([p for _, problems in self.results(P, "counted_pokemon", own_only) for p in problems if "ES2-016" in p or "QSG-025" in p or "ES3-002" in p])


class DocumentTest(unittest.TestCase):
    def test_document_names_the_shared_parts(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("DamagePlusOwnCountersThenSelfDamage", "CoinsHeadsTableBonusDamage", "PrintedPlusHeadsTable", "CappedCoinsPerAttachedEnergyCardsDamage",
                       "HeadsTimesAttachedEnergyCards", "DamagePlusOpponentPrizesTaken", "PrintedPlusOpponentPrizesTaken", "prizes_taken", "CoinsBonusAndSelfDamagePerHeads",
                       "DamagePlusPokemonCount", "POKEMON_COUNT_TEXTS", "LOCK_SELF_NAMED_TEXTS", "zero_damage_below_texts", "FD1", "v0.4b", "HC3", "T19b", "G37", "ES3",
                       "f118100", "9e8ca5c", "73a1690", "GR-2000-P309-ATTACK-PROCEDURE", "GR-2000-P312-FIELD", "GR-2000-P319-HP-AND-DAMAGE", "GR-2000-P320-DAMAGE-FIGURE",
                       "GR-2000-P321-ATTACK-DAMAGE", "GR-2000-P321-DAMAGE-ORDER", "GR-2000-P321-PREVENTED-ELEMENTS", "GR-2000-P322-PERSISTENT-EFFECTS",
                       "GR-2000-P323-KNOCKOUT"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
