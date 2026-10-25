"""v0.94（docs/switch-return-attacks-v0.94.md）: 入れ替え・帰還のワザのポケモン 13 枚（ワザ 21）と、前段のふきとばしの型の照合の全文化・記録先の参照。

根拠は kyuura データの採用（kyuura ``7d3f4ca`` の data/cards.json の日本語の印刷の文面）と、既存の規定の記録（v0.4d のふきとばし・v0.31 のかどわかす・v0.40 の DO1〜DO4・v0.62 の
ハリケーン・v0.65 の RX1・NT2・v0.87 のこうそくスピン・v0.93 のはなれられない効果）。英語版の文面・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・
カードの画像・pcg-search.com との照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は
tools/existing_effect_games.py の ``--batch v0.94``）。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttackKey,
    EvolvePokemon,
    ResolveDecision,
    UseAttack,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import FORCED_SWITCH, SELECT_POKEMON
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import visible_log
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.release_catalog import cards_before
from tests.test_active_leave_locks_v0_93 import locked
from tests.test_barrier_resume_coin_bonus_v0_34 import with_barrier
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_power_suppression_lasting_locks_v0_92 import answer, board, mon, uid

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "switch-return-attacks-v0.94.md"
RULES_DOC = ROOT / "docs" / "rules-2000-02-14.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
TURN = 7
G, R, W, L, PS, F = H.GRASS, H.FIRE, H.WATER, H.LIGHTNING, H.PSYCHIC, H.FIGHTING
CLEFAIRY, CLEFAIRY_QSG, JIGGLYPUFF, SNUBBULL = H.CLEFAIRY_ES1, H.CLEFAIRY_QSG, H.JIGGLYPUFF_SI, H.SNUBBULL_NEO1
VENOMOTH, DONPHAN, TOGEPI, BELLOSSOM = H.VENOMOTH_ES2, H.DONPHAN_NEO1, H.TOGEPI_PRN, H.BELLOSSOM_PRN
TAUROS, MACHAMP, VULPIX, VULPIX_QSG, DARK_DONPHAN = H.TAUROS_ES3, H.MACHAMP_PR1, H.VULPIX_ES3, H.VULPIX_QSG, H.DARK_DONPHAN
ONIX = "PMCG1-054"  # イワーク（第1弾。HP 90・闘・弱点 草。受ける側の丈夫なたねポケモン）
MAGCARGO, SLUGMA = H.MAGCARGO_NEO3, "neo3-008"  # マグカルゴ（［やけのこり］）・マグマッグ
FORRETRESS, PINECO = H.FORRETRESS_NEO2, "neo4-005"  # フォレトス（［まきびし］）・クヌギダマ
BELOW = {VENOMOTH: H.VENONAT, DONPHAN: H.PHANPY_NEO4, BELLOSSOM: [H.ODDISH_NEO1, H.GLOOM_NEO1], MACHAMP: [H.MACHOP, H.MACHOKE], DARK_DONPHAN: H.PHANPY_NEO4,
         MAGCARGO: SLUGMA, FORRETRESS: PINECO, H.HAUNTER: H.GASTLY, H.DARK_MACHOKE: H.ROCKET_MACHOP}
V094_ATTACKS = [AttackKey(c, i) for c in H.V0_94_POKEMON for i in range(len(load_card_pool().definitions[c].attacks))]
RX1 = "UNRESOLVED_REACTIVE_SWITCH_TRANSFORMED_ATTACKER"
AL2, HC3, T27, NT2 = "UNRESOLVED_LEAVE_LOCK_NO_EFFECT", "UNRESOLVED_PREVENTED_EFFECT_COIN", "UNRESOLVED_TRANSPARENCY_COIN_ORDER", "UNRESOLVED_NINJA_TRICK_LEAVES_WITH_POKEMON"


def m(card, energy=(), **extra):
    """場のポケモンの指定（進化ポケモンには進化元を付ける）。"""
    spec = mon(card, energy, **extra)
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def attack(state, index, *coins, player=None):
    player = state.current_player if player is None else player
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UseAttack(player, index))


def kinds(before, after, *names):
    return [e["kind"] for e in new_events(before, after, *names)]


def stopped(test, state, command, code, error=UnsupportedError):
    return rejects(test, state, command, code, error)


def written(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log], repr(state.rng.getstate())


# ---------------------------------------------------------------- 1〜3 章: 対象・登録・前段の照合


class RegistrationTest(unittest.TestCase):
    def test_every_attack_is_registered(self):
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_94"]), H.V0_94_CARDS)
        self.assertEqual(len(V094_ATTACKS), 21)
        for key in V094_ATTACKS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
                printed = pool.definitions[key.card_id].attacks[key.attack_index]
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja), (printed.name_ja, printed.text_ja, printed.text_ja))
                self.assertEqual(entry.effect.check(printed), [])
                self.assertIsNone(DEFAULT_EFFECTS.attack_problem(key.card_id, printed, pool.definitions[key.card_id].attacks))
        for card in H.V0_94_CARDS:
            self.assertIn(card, pool.playable_ids)
            self.assertEqual(pool.definitions[card].powers, ())

    def test_types(self):
        effect = lambda card, i: DEFAULT_EFFECTS.attack_entry(card, i).effect
        self.assertEqual(effect(CLEFAIRY, 0), E.SwitchOpponentActiveRequiringBench())
        self.assertEqual(effect(CLEFAIRY, 1), E.SleepOpponent())
        self.assertEqual(effect(JIGGLYPUFF, 0), E.SwitchOpponentActive())
        self.assertEqual(effect(JIGGLYPUFF, 1), E.SleepOnHeadsWithoutDamage())
        self.assertEqual(effect(SNUBBULL, 0), E.ForceSwitchOnHeadsWithoutDamage())
        self.assertEqual(effect(SNUBBULL, 1), E.ParalyzeOnHeads())
        self.assertEqual(effect(VENOMOTH, 0), E.DamageThenSwitchBothActives())
        self.assertEqual(effect(VENOMOTH, 1), E.DamageThenStatusByCoin(E.PARALYSIS, E.POISON))
        self.assertEqual(effect(DONPHAN, 0), E.DamageTimesOwnCounters(10))
        self.assertEqual(effect(DONPHAN, 1), E.DamageThenSwitchBothActives())
        self.assertEqual(effect(TOGEPI, 0), E.DamageThenSelfSwitch())
        self.assertEqual(effect(BELLOSSOM, 0), E.DamageThenStatusOnHeadsElseSelfSwitch(E.SLEEP))
        self.assertEqual(effect(TAUROS, 0), E.CoinBonusDamageElseForceSwitch(10))
        self.assertEqual(effect(MACHAMP, 0), E.CoinsPerOwnCountersBonusDamage(10))
        self.assertEqual(effect(MACHAMP, 1), E.DamageAndForceSwitch())
        self.assertEqual(effect(VULPIX, 0), E.OptionalSwitchOpponentThenDamage())
        self.assertEqual(effect(DARK_DONPHAN, 0), E.CoinReturnOpponentToHandElseForceSwitch())
        self.assertIs(effect(DARK_DONPHAN, 1), E.DAMAGE_ONLY)

    def test_the_two_pairs_share_one_registration(self):
        """ピッピ（ES1-026・QSG-040）・ロコン（ES3-009・QSG-008）はゲーム用データが同じ組。id ごとに登録し、同じ登録の値を使う。"""
        self.assertEqual(dict(E.SAME_DATA_CARDS_V0_94), {CLEFAIRY_QSG: CLEFAIRY, VULPIX_QSG: VULPIX})
        extract = {c["id"]: c for c in read_extract()["cards"]}
        for new, original in E.SAME_DATA_CARDS_V0_94.items():
            with self.subTest(card=new):
                self.assertEqual(extract[new]["same_card_group"], extract[original]["same_card_group"])
                self.assertEqual(extract[new]["pokemon"], extract[original]["pokemon"])
                for i in range(len(extract[new]["pokemon"]["attacks"])):
                    self.assertIs(DEFAULT_EFFECTS.attack_entry(new, i), DEFAULT_EFFECTS.attack_entry(original, i))

    def test_unregistered_without_the_v0_94_entries(self):
        """今回の登録を除くと対戦に使えなくなるのは、ちょうど 13 枚（ほかのカードは失われない）。過去の範囲は ``cards_before`` で切り出す。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V094_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(H.V0_94_CARDS))
        self.assertEqual(set(H.V0_94_CARDS) & set(cards_before(read_extract(), "0.94")), set())

    def test_evolution_bases_exist(self):
        pool = load_card_pool()
        for card, base in ((VENOMOTH, "コンパン"), (DONPHAN, "ゴマゾウ"), (BELLOSSOM, "クサイハナ"), (MACHAMP, "ゴーリキー"), (DARK_DONPHAN, "ゴマゾウ")):
            with self.subTest(card=card):
                self.assertEqual(pool.definitions[card].evolves_from, base)
                below = BELOW[card]
                state = board(m(below[-1] if isinstance(below, list) else below, played_turn=3, **({"evolved_from": below[:-1]} if isinstance(below, list) else {})),
                              hand=(card,))
                evolved = apply_kernel(state, EvolvePokemon(0, uid(state, card), state.players[0].active.pokemon_id))
                self.assertEqual(evolved.cards[evolved.players[0].active.card].card_id, card)
                audited(self, evolved)


class StrictForceSwitchTextTest(unittest.TestCase):
    """2 章（前段）: ふきとばしの型（``DamageAndForceSwitch``）は、既存の 9 登録・7 通りの処理用の全文（照らすのは印刷の文面）と v0.94 のなげとばすだけを受け付ける。ダメージの前・
    任意の入れ替え（きつねび）は、形が同じでも拒否する。正しい型では全文が通る。"""

    def test_existing_registrations_keep_their_texts_and_play_texts(self):
        pool = load_card_pool()
        registered = [(k, DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index)) for k in DEFAULT_EFFECTS.attack_keys()
                      if type(DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect) is E.DamageAndForceSwitch]
        old = [(k, entry) for k, entry in registered if k.card_id != MACHAMP]
        self.assertEqual(len(old), 9)
        self.assertEqual(len({entry.play_text_ja for _, entry in old}), 7)  # 処理に使う文面 7 通り（PMCG2-007 は p.19 の最新の説明。v0.93 までと同じ）
        self.assertEqual({entry.text_ja for _, entry in registered}, set(E.DamageAndForceSwitch.TEXTS))
        self.assertEqual(len(E.DamageAndForceSwitch.TEXTS), 8)
        for key, _ in registered:
            with self.subTest(key=key):
                self.assertEqual(E.DamageAndForceSwitch().check(pool.definitions[key.card_id].attacks[key.attack_index]), [])
        self.assertEqual(DEFAULT_EFFECTS.attack_entry("PMCG2-007", 0).play_text_ja, "相手を控えポケモンと入れ替える。入れ替わるポケモンは、相手が選ぶ。（相手に控えがいないとき、入れ替えはおこらない）")

    def test_fox_fire_is_rejected_by_the_wrong_types_and_accepted_by_the_right_one(self):
        fox = load_card_pool().definitions[VULPIX].attacks[0]
        self.assertTrue(E.DamageAndForceSwitch().check(fox))  # 形（目安 10・説明文あり）だけなら通っていた
        self.assertTrue(E.SwitchOpponentThenDamage().check(fox))  # 必須の入れ替えに文面を足さない
        self.assertEqual(E.OptionalSwitchOpponentThenDamage().check(fox), [])

    def test_other_new_texts_are_not_interchanged(self):
        pool = load_card_pool()
        attack = lambda card, i: pool.definitions[card].attacks[i]
        self.assertTrue(E.SwitchOpponentActive().check(attack(CLEFAIRY, 0)))  # 「使えない」のない型で通さない
        self.assertTrue(E.SwitchOpponentActiveOnHeads().check(attack(CLEFAIRY, 0)))  # コインの型で通さない
        self.assertTrue(E.SwitchOpponentActiveRequiringBench().check(attack(JIGGLYPUFF, 0)))
        self.assertTrue(E.DamageThenForceSwitchOnHeads().check(attack(SNUBBULL, 0)))  # ダメージのある型で通さない
        self.assertTrue(E.SwitchOpponentActiveOnHeads().check(attack(SNUBBULL, 0)))  # 選ぶ側の違う型で通さない
        self.assertTrue(E.DamageThenOptionalSelfSwitch().check(attack(TOGEPI, 0)))  # 任意の型（テレポートブラスト）で通さない
        self.assertTrue(E.DamageThenSelfSwitchOnHeads().check(attack(TOGEPI, 0)))
        self.assertTrue(E.DamageThenReturnOpponentToHand().check(attack(DARK_DONPHAN, 0)))
        self.assertTrue(E.CoinBonusDamageThenLeaveLock(10).check(attack(TAUROS, 0)))
        self.assertTrue(E.DamageThenSleepOnHeads().check(attack(BELLOSSOM, 0)))
        self.assertTrue(E.DamageAndForceSwitch().check(attack(VENOMOTH, 0)))  # 自分の入れ替えを落とさない
        self.assertEqual(E.SWITCH_BOTH_ACTIVES_TEXTS, (E.RAPID_SPIN_TEXT, attack(DONPHAN, 1).text_ja))
        self.assertEqual(attack(VENOMOTH, 0).text_ja, attack(DONPHAN, 1).text_ja)
        self.assertEqual(E.CoinsPerOwnCountersBonusDamage(10).check(attack(MACHAMP, 0)), [])
        self.assertTrue(E.CoinsPerOwnCountersBonusDamage(20).check(attack(MACHAMP, 0)))
        with self.assertRaises(ValueError):
            E.CoinBonusDamageElseForceSwitch(5)

    def test_shape_only_reused_types_match_existing_registrations_exactly(self):
        """形だけを確かめる既存の型（ねむり・コインのねむり・じたばた）は、同じ型の既存の登録と全文が同じこと（意味を照らした）を確かめる。"""
        pool = load_card_pool()
        for card, index in ((CLEFAIRY, 1), (JIGGLYPUFF, 1), (DONPHAN, 0)):
            with self.subTest(card=card):
                kind = type(DEFAULT_EFFECTS.attack_entry(card, index).effect)
                text = pool.definitions[card].attacks[index].text_ja
                others = {pool.definitions[k.card_id].attacks[k.attack_index].text_ja for k in DEFAULT_EFFECTS.attack_keys()
                          if k.card_id not in H.V0_94_CARDS and type(DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect) is kind}
                self.assertIn(text, others)


class RulesDocumentTest(unittest.TestCase):
    """前段: 裁定の根拠と実装上の仮定の記録先（docs/rules-2000-02-14.md）から、v0.93・v0.94 の論点と実装上の読み方へ辿れる（規定・未解決・読み方を分ける）。"""

    def test_reference_section(self):
        text = RULES_DOC.read_text(encoding="utf-8")
        self.assertIn("後続版の裁定・実装上の読み方への参照", text)
        for word in ("active-leave-locks-v0.93.md", "switch-return-attacks-v0.94.md", "AL1", "AL2", "AL3", "JC1", "JC2", "CJ1", "RX1", "DO3",
                     "根拠のある規定", "未解決", "実装上の読み方"):
            self.assertIn(word, text)


# ---------------------------------------------------------------- 4 章: 選ぶ側・使うための条件・コイン


class LureTest(unittest.TestCase):
    """このゆびとまれ（ピッピ）: ワザを使ったプレイヤーが選ぶ。相手に控えがいない時は使えない（こんらんのコインの前）。"""

    def test_attacker_chooses_and_no_bench_cannot_be_used(self):
        state = board(m(CLEFAIRY, (W,)), opponent=m(ONIX, (F,)), opponent_bench=(H.RATTATA, H.CHANSEY))
        asked = attack(state, 0)
        self.assertEqual((asked.decision.kind, asked.decision.player, asked.decision.min_choices), (FORCED_SWITCH, 0, 1))
        self.assertFalse(new_events(state, asked, "coin_flip", "damage"))
        done = answer(asked, (asked.decision.options[1],))
        self.assertEqual(done.players[1].active.pokemon_id, asked.decision.options[1])
        self.assertEqual([e.get("chosen_by") for e in new_events(asked, done, "forced_switch")], ["attacker"])
        audited(self, done)
        rejects(self, asked, ResolveDecision(0, asked.decision.id, ()), "INVALID_CHOICE_COUNT", IllegalActionError)  # 必須（0 匹の答えはない）
        rejects(self, asked, ResolveDecision(1, asked.decision.id, (asked.decision.options[0],)), "NOT_YOUR_DECISION", IllegalActionError)
        alone = board(m(CLEFAIRY, (W,), confusion=True), opponent=m(ONIX, (F,)), opponent_bench=())
        rejects(self, alone, UseAttack(0, 0), "NO_OPPONENT_BENCH", IllegalActionError)

    def test_glowing_finger_sleeps_without_a_coin(self):
        state = board(m(CLEFAIRY_QSG, (W, W)), opponent=m(ONIX, (F,)))
        done = attack(state, 1)
        self.assertEqual(kinds(state, done, "damage", "special_condition")[:2], ["damage", "special_condition"])
        self.assertFalse([e for e in new_events(state, done, "coin_flip") if e["source"] == "attack"])  # ワザのコインはない（ポケモンチェックのねむりのコインは別）

    def test_copied_lure_follows_the_usage_condition(self):
        """ゆびをふる（第1弾のピッピ。「ワザに必要なエネルギー以外はワザの説明にしたがう」）: 相手に控えがいなければ、このゆびとまれは選べない（v0.40 の DO1 の写しと同じ扱い）。
        控えがいれば、まねたプレイヤーが選ぶ入れ替え。"""
        alone = board(m(H.CLEFAIRY, (R, R, R), played_turn=1), opponent=m(CLEFAIRY, (W,)), opponent_bench=())
        self.assertEqual(attack(alone, 1).decision.options, (1,))
        state = board(m(H.CLEFAIRY, (R, R, R), played_turn=1), opponent=m(CLEFAIRY, (W,)), opponent_bench=(H.RATTATA,))
        asked = answer(attack(state, 1), (0,))
        self.assertEqual((asked.decision.kind, asked.decision.player), (FORCED_SWITCH, 0))
        audited(self, answer(asked, asked.decision.options))


class TemptingEyesTest(unittest.TestCase):
    """ひとみでさそう（プリン）: ワザを使ったプレイヤーが選ぶ。使えない条件はない（控えがいなければ入れ替えない）。うたうは既存のコインのねむり。"""

    def test_attacker_chooses_and_no_bench_is_still_usable(self):
        state = board(m(JIGGLYPUFF, (W,)), opponent=m(ONIX, (F,)), opponent_bench=(H.RATTATA,))
        asked = attack(state, 0)
        self.assertEqual((asked.decision.kind, asked.decision.player), (FORCED_SWITCH, 0))
        alone = attack(board(m(JIGGLYPUFF, (W,)), opponent=m(ONIX, (F,)), opponent_bench=()), 0)
        self.assertEqual([e["reason"] for e in new_events(state, alone, "forced_switch_skipped")], [E.NO_BENCH])
        self.assertIsNone(alone.decision)
        sing = attack(board(m(JIGGLYPUFF, (W,)), opponent=m(ONIX, (F,))), 1, HD)
        self.assertEqual([e["condition"] for e in new_events(state, sing, "special_condition")], ["sleep"])


class RoarTest(unittest.TestCase):
    """ほえる（ブルー）: この要素のコインの「おもて」で、相手が選ぶ。控えがいなければコインを投げない。はなれられない・ワザをうけない相手はコインの前に止める。"""

    def test_heads_opponent_chooses_tails_nothing(self):
        state = board(m(SNUBBULL, (W,)), opponent=m(ONIX, (F,)), opponent_bench=(H.RATTATA,))
        heads = attack(state, 0, HD)
        self.assertEqual((heads.decision.kind, heads.decision.player), (FORCED_SWITCH, 1))
        tails = attack(state, 0, TL)
        self.assertIsNone(tails.decision)
        self.assertFalse(new_events(state, tails, "forced_switch", "damage"))
        alone = attack(board(m(SNUBBULL, (W,)), opponent=m(ONIX, (F,)), opponent_bench=()), 0)
        self.assertFalse(new_events(state, alone, "coin_flip"))
        audited(self, answer(heads, heads.decision.options))

    def test_locked_or_barrier_stops_before_the_coin_and_lick(self):
        state = board(m(SNUBBULL, (W,)), opponent=m(ONIX, (F,)), opponent_bench=(H.RATTATA,))
        stopped(self, locked(state, 1), UseAttack(0, 0), AL2)
        stopped(self, with_barrier(m(SNUBBULL, (W,))), UseAttack(1, 0), HC3)
        lick = attack(board(m(SNUBBULL, (W, W)), opponent=m(ONIX, (F,))), 1, HD)
        self.assertEqual([e["condition"] for e in new_events(state, lick, "special_condition")], ["paralysis"])


# ---------------------------------------------------------------- 5 章: モルフォン・ドンファン・トゲピー・カイリキー


class SwitchBothTest(unittest.TestCase):
    """たつまきおこし（モルフォン）・こうそくスピン（ドンファン）: ダメージ → 相手が選ぶ相手の入れ替え → ワザを使ったプレイヤーが選ぶ自分の入れ替え。片側の控えがない・はなれられない
    だけで、もう一方は止めない。"""

    def spin(self, **kw):
        return board(m(DONPHAN, (F, F, F)), opponent=m(ONIX, (F,)), opponent_bench=kw.pop("opponent_bench", (H.RATTATA,)), bench=kw.pop("bench", (H.CHANSEY,)), **kw)

    def test_order_damage_opponent_then_self(self):
        for card, index, energy in ((VENOMOTH, 0, (G, G)), (DONPHAN, 1, (F, F, F))):
            with self.subTest(card=card):
                state = board(m(card, energy), opponent=m(ONIX, (F,)), opponent_bench=(H.RATTATA,), bench=(H.CHANSEY,))
                first = attack(state, index)
                self.assertEqual((first.decision.kind, first.decision.player), (FORCED_SWITCH, 1))
                second = answer(first, first.decision.options)
                self.assertEqual((second.decision.kind, second.decision.player, second.decision.min_choices), (SELECT_POKEMON, 0, 1))
                done = answer(second, second.decision.options)
                self.assertEqual(kinds(state, done, "damage", "forced_switch", "switch"), ["damage", "forced_switch", "switch"])
                audited(self, done)

    def test_one_side_missing_or_locked_does_not_stop_the_other(self):
        no_opponent_bench = attack(self.spin(opponent_bench=()), 1)
        self.assertEqual((no_opponent_bench.decision.kind, no_opponent_bench.decision.player), (SELECT_POKEMON, 0))
        asked = attack(self.spin(bench=()), 1)
        self.assertEqual((asked.decision.kind, asked.decision.player), (FORCED_SWITCH, 1))
        self.assertIsNone(answer(asked, asked.decision.options).decision)
        opponent_locked = attack(locked(self.spin(), 1), 1)
        self.assertEqual([e["cause"] for e in new_events(self.spin(), opponent_locked, "leave_prevented")], [E.LEAVE_FORCED_SWITCH])
        self.assertEqual((opponent_locked.decision.kind, opponent_locked.decision.player), (SELECT_POKEMON, 0))
        self_locked = locked(self.spin(), 0)
        asked = attack(self_locked, 1)
        done = answer(asked, asked.decision.options)
        self.assertEqual(kinds(self_locked, done, "forced_switch", "leave_prevented"), ["forced_switch", "leave_prevented"])
        self.assertIsNone(done.decision)
        audited(self, done)

    def test_resume_from_copies_does_not_repeat_damage_or_switch(self):
        first = attack(self.spin(), 1)
        expected = state_to_dict(answer(answer(first, first.decision.options), (first.players[0].bench[0].pokemon_id,)), format_version=24)
        for copied in (first.clone(), copy.deepcopy(first), pickle.loads(pickle.dumps(first))):
            second = answer(copied, copied.decision.options)
            self.assertEqual(state_to_dict(answer(second, second.decision.options), format_version=24), expected)

    def test_spikes_on_the_own_switch(self):
        """［まきびし］（相手のフォレトス。相手の番に相手の控えがバトル場に出てくるたび）: 自分の入れ替えで出てきた自分のポケモンに 10。入れ替えのあとの反応を、次の移動・ワザの終わりの
        前に処理する。"""
        state = board(m(DONPHAN, (F, F, F)), opponent=m(FORRETRESS, (G,)), opponent_bench=(), bench=(H.CHANSEY,))
        asked = attack(state, 1)
        done = answer(asked, asked.decision.options)
        self.assertEqual(kinds(asked, done, "switch", "spikes_damage"), ["switch", "spikes_damage"])
        self.assertEqual(done.players[0].active.damage, 10)
        audited(self, done)


class FlailTest(unittest.TestCase):
    def test_counters_times_ten_and_zero_is_not_a_failure(self):
        state = board(m(DONPHAN, (F,), damage=30), opponent=m(H.CHANSEY))
        self.assertEqual([e["amount"] for e in new_events(state, attack(state, 0), "damage")], [60])  # 30 × 弱点 2（闘）
        clean = board(m(DONPHAN, (F,)), opponent=m(H.CHANSEY))
        done = attack(clean, 0)
        self.assertFalse(new_events(clean, done, "attack_failed"))
        self.assertEqual([e["amount"] for e in new_events(clean, done, "damage")], [0])


class FrolicTest(unittest.TestCase):
    """はしゃぐ（トゲピー）: ダメージのあと、控えがいれば必ず自分を入れ替える（0 匹の答えはない）。"""

    def test_mandatory_self_switch(self):
        state = board(m(TOGEPI, (W,)), opponent=m(ONIX, (F,)), bench=(H.CHANSEY, H.RATTATA))
        asked = attack(state, 0)
        self.assertEqual((asked.decision.kind, asked.decision.player, asked.decision.min_choices, asked.decision.max_choices), (SELECT_POKEMON, 0, 1, 1))
        rejects(self, asked, ResolveDecision(0, asked.decision.id, ()), "INVALID_CHOICE_COUNT", IllegalActionError)
        done = answer(asked, asked.decision.options[1:])
        self.assertEqual(done.players[0].active.pokemon_id, asked.decision.options[1])
        self.assertFalse(new_events(asked, done, "switch_declined"))
        audited(self, done)
        alone = attack(board(m(TOGEPI, (W,)), opponent=m(ONIX, (F,)), bench=()), 0)
        self.assertIsNone(alone.decision)
        self_locked = attack(locked(state, 0), 0)
        self.assertEqual([e["cause"] for e in new_events(state, self_locked, "leave_prevented")], [E.LEAVE_SWITCH])


class SeethingAngerAndFlingTest(unittest.TestCase):
    def test_coins_per_own_counters(self):
        state = board(m(MACHAMP, (F, F), damage=30), opponent=m(ONIX, (F,)))
        done = attack(state, 0, HD, TL, HD)
        self.assertEqual(len(new_events(state, done, "coin_flip")), 3)
        self.assertEqual([e["amount"] for e in new_events(state, done, "damage")], [40])
        clean = board(m(MACHAMP, (F, F)), opponent=m(ONIX, (F,)))
        zero = attack(clean, 0)
        self.assertFalse(new_events(clean, zero, "coin_flip"))
        self.assertEqual([e["amount"] for e in new_events(clean, zero, "damage")], [20])

    def test_fling_damage_then_opponent_chooses(self):
        state = board(m(MACHAMP, (F, F, F, F)), opponent=m(H.CHANSEY), opponent_bench=(H.RATTATA,))
        asked = attack(state, 1)
        self.assertEqual((asked.decision.kind, asked.decision.player), (FORCED_SWITCH, 1))
        self.assertEqual(kinds(state, asked, "damage"), ["damage"])
        alone = attack(board(m(MACHAMP, (F, F, F, F)), opponent=m(H.CHANSEY), opponent_bench=()), 1)
        self.assertEqual([e["reason"] for e in new_events(state, alone, "forced_switch_skipped")], [E.NO_BENCH])


# ---------------------------------------------------------------- 6 章: 同じコインで分かれるワザ


class FloralSpinTest(unittest.TestCase):
    """フローラルスピン（キレイハナ）: ダメージのあとの 1 枚のコインで、「おもて」は相手のねむり、「うら」は自分の入れ替え。"""

    def state(self, **kw):
        return board(m(BELLOSSOM, (G, G, G)), opponent=m(ONIX, (F,)), bench=kw.pop("bench", (H.CHANSEY,)), **kw)

    def test_one_coin_after_damage(self):
        state = self.state()
        heads = attack(state, 0, HD)
        self.assertEqual(kinds(state, heads, "damage", "coin_flip", "special_condition")[:3], ["damage", "coin_flip", "special_condition"])
        self.assertIsNone(heads.decision)
        tails = attack(state, 0, TL)
        self.assertEqual((tails.decision.kind, tails.decision.player), (SELECT_POKEMON, 0))
        self.assertEqual(len([e for e in new_events(state, tails, "coin_flip") if e["source"] == "attack"]), 1)
        audited(self, answer(tails, tails.decision.options))
        alone = attack(self.state(bench=()), 0, TL)
        self.assertIsNone(alone.decision)
        self.assertFalse(new_events(state, alone, "attack_failed"))

    def test_no_target_for_either_side_skips_the_coin(self):
        hp = load_card_pool().definitions[ONIX].hp
        state = board(m(BELLOSSOM, (G, G, G)), opponent=m(ONIX, (F,), damage=hp - 60), bench=())
        done = attack(state, 0)
        self.assertFalse([e for e in new_events(state, done, "coin_flip") if e["source"] == "attack"])

    def test_opponent_barrier_still_flips_for_the_own_switch_and_locked_self_with_barrier_is_hc3(self):
        barrier = with_barrier(m(BELLOSSOM, (G, G, G)), attacker_bench=(H.CHANSEY,))
        tails = apply_kernel(with_coin_results(barrier, TL), UseAttack(1, 0))
        self.assertEqual((tails.decision.kind, tails.decision.player), (SELECT_POKEMON, 1))
        stopped(self, locked(barrier, 1), UseAttack(1, 0), HC3)

    def test_locked_self_flips_for_the_sleep(self):
        state = locked(self.state(), 0)
        tails = attack(state, 0, TL)
        self.assertEqual([e["cause"] for e in new_events(state, tails, "leave_prevented")], [E.LEAVE_SWITCH])
        heads = attack(state, 0, HD)
        self.assertEqual([e["condition"] for e in new_events(state, heads, "special_condition")], ["sleep"])
        audited(self, tails)


class TrampleTest(unittest.TestCase):
    """ふんだりけったり（ケンタロス）: ダメージの前の 1 枚のコインで、「おもて」は +10、「うら」はダメージのあとに相手が選ぶ入れ替え。"""

    def state(self, **kw):
        return board(m(TAUROS, (W, W)), opponent=m(ONIX, (F,)), opponent_bench=kw.pop("opponent_bench", (H.RATTATA,)), **kw)

    def test_coin_before_damage(self):
        state = self.state()
        heads = attack(state, 0, HD)
        self.assertEqual(kinds(state, heads, "coin_flip", "damage")[:2], ["coin_flip", "damage"])
        self.assertEqual([e["amount"] for e in new_events(state, heads, "damage")], [30])
        self.assertIsNone(heads.decision)
        tails = attack(state, 0, TL)
        self.assertEqual([e["amount"] for e in new_events(state, tails, "damage")], [20])
        self.assertEqual((tails.decision.kind, tails.decision.player), (FORCED_SWITCH, 1))
        audited(self, answer(tails, tails.decision.options))

    def test_no_bench_or_locked_keeps_the_bonus_coin(self):
        alone = self.state(opponent_bench=())
        tails = attack(alone, 0, TL)
        self.assertEqual([e["reason"] for e in new_events(alone, tails, "forced_switch_skipped")], [E.NO_BENCH])
        locked_state = locked(self.state(), 1)
        tails = attack(locked_state, 0, TL)
        self.assertEqual([e["cause"] for e in new_events(locked_state, tails, "leave_prevented")], [E.LEAVE_FORCED_SWITCH])
        self.assertEqual([e["amount"] for e in new_events(locked_state, attack(locked_state, 0, HD), "damage")], [30])

    def test_barrier_is_hc3_and_damage_prevention_still_flips(self):
        stopped(self, with_barrier(m(TAUROS, (W, W))), UseAttack(1, 0), HC3)
        shielded = board(m(TAUROS, (W, W)), opponent=m(ONIX, (F,), prevent_damage=TURN - 1), opponent_bench=(H.RATTATA,))
        tails = attack(shielded, 0, TL)
        self.assertEqual((tails.decision.kind, tails.decision.player), (FORCED_SWITCH, 1))


# ---------------------------------------------------------------- 7 章: きつねび（ダメージの前の任意の入れ替え）


class FoxFireTest(unittest.TestCase):
    """きつねび（ロコン）: 入れ替えるかをワザを使ったプレイヤーが選び（0〜1 匹）、そのあとのバトル場のポケモンにダメージ。"""

    def state(self, **kw):
        return board(m(VULPIX, (R, R)), opponent=kw.pop("opponent", m(ONIX, (F,))), opponent_bench=kw.pop("opponent_bench", (H.VENONAT, H.RATTATA)), **kw)

    def test_switch_or_not_and_the_new_active_takes_its_own_damage(self):
        state = self.state()
        asked = attack(state, 0)
        d = asked.decision
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices, d.options), (FORCED_SWITCH, 0, 0, 1, tuple(p.pokemon_id for p in state.players[1].bench)))
        self.assertFalse(new_events(state, asked, "damage"))  # ダメージは入れ替えのあと
        declined = answer(asked, ())
        self.assertEqual(kinds(asked, declined, "forced_switch_declined", "damage"), ["forced_switch_declined", "damage"])
        self.assertEqual([(e["pokemon"], e["amount"]) for e in new_events(asked, declined, "damage")], [(state.players[1].active.card, 10)])
        switched = answer(asked, (d.options[0],))  # コンパン（弱点 炎）
        self.assertEqual(kinds(asked, switched, "forced_switch", "damage"), ["forced_switch", "damage"])
        self.assertEqual([(e["pokemon"], e["amount"]) for e in new_events(asked, switched, "damage")], [(switched.players[1].active.card, 20)])
        for done in (declined, switched):
            audited(self, done)
        rejects(self, asked, ResolveDecision(0, d.id, tuple(d.options)), "INVALID_CHOICE_COUNT", IllegalActionError)
        rejects(self, asked, ResolveDecision(0, d.id, (state.players[1].active.pokemon_id,)), "INVALID_CHOICE", IllegalActionError)

    def test_no_bench_locked_and_barrier_damage_the_unchanged_active(self):
        alone = self.state(opponent_bench=())
        done = attack(alone, 0)
        self.assertIsNone(done.decision)
        self.assertEqual(kinds(alone, done, "forced_switch_skipped", "damage"), ["forced_switch_skipped", "damage"])
        locked_state = locked(self.state(), 1)
        done = attack(locked_state, 0)
        self.assertIsNone(done.decision)
        self.assertEqual(kinds(locked_state, done, "leave_prevented", "damage"), ["leave_prevented", "damage"])
        barrier = with_barrier(m(VULPIX, (R, R)))
        done = apply_kernel(barrier, UseAttack(1, 0))
        self.assertIsNone(done.decision)
        self.assertFalse(new_events(barrier, done, "forced_switch", "damage"))

    def test_burnout_moves_energy_before_the_damage(self):
        """［やけのこり］（相手のマグカルゴ）: 入れ替えでベンチにもどった時、炎エネルギーカードを新しく出てきた対戦ポケモンにつけ替える。ダメージより前。"""
        state = self.state(opponent=m(MAGCARGO, (R, R)), opponent_bench=(H.VENONAT,))
        asked = attack(state, 0)
        magma = answer(asked, asked.decision.options)
        self.assertEqual((magma.decision.player, magma.decision.kind), (1, "magma_pool_energy"))
        self.assertFalse(new_events(asked, magma, "damage"))
        done = answer(magma, magma.decision.options[:1])
        self.assertEqual(kinds(magma, done, "magma_pool", "damage")[:2], ["magma_pool", "damage"])
        self.assertEqual(len(done.players[1].active.energy), 1)
        audited(self, done)

    def test_two_transparencies_stop_only_the_switch_to_the_second_ghost(self):
        """T27: 入れ替える前と後のポケモンがどちらも「とうめい」なら、その控えへの入れ替えだけを選ぶと止める（入れ替えない・ほかの控えは止めない。選ばなかった枝で一律に止めない）。"""
        state = self.state(opponent=m(H.HAUNTER, (PS,)), opponent_bench=(m(H.HAUNTER, (PS,)), H.RATTATA))
        asked = attack(state, 0, TL)  # 入れ替える前のゴーストの「とうめい」（入れ替えの効果を受けるとき。「うら」なら受ける）
        d = asked.decision
        ghost, rattata = d.options
        self.assertEqual(d.context_value("unresolved_choices"), (ghost,))
        self.assertEqual([item[:2] for item in d.context_value("unresolved_detail")], [(ghost, T27)])
        audited(self, asked)
        stopped(self, asked, ResolveDecision(0, d.id, (ghost,)), T27)
        for answer_ in ((), (rattata,)):
            for coin in (HD, TL):
                with self.subTest(answer=answer_, coin=coin):
                    done = apply_kernel(with_coin_results(asked, coin), ResolveDecision(0, d.id, answer_))
                    self.assertEqual(len(new_events(asked, done, "damage")), 1)

    def test_transformed_ditto_rx1_keeps_the_decline_answer(self):
        """RX1: ［へんしん］のメタモンがきつねびを使うと、入れ替えで今の姿が変わる控えは選ぶと止める（同じゲーム用データでも id の違うカードは変わるとする）。入れ替えない答えは残る。"""
        state = board(m(H.DITTO, (R, R)), opponent=m(VULPIX, (R,)), opponent_bench=(H.RATTATA, VULPIX_QSG))
        asked = attack(state, 0)
        d = asked.decision
        self.assertEqual(set(d.context_value("unresolved_choices")), set(d.options))
        self.assertEqual(d.context_value("unresolved_code"), RX1)
        stopped(self, asked, ResolveDecision(0, d.id, (d.options[0],)), RX1)
        done = answer(asked, ())
        self.assertEqual(kinds(asked, done, "forced_switch_declined", "damage"), ["forced_switch_declined", "damage"])
        audited(self, done)

    def test_resume_from_copies(self):
        asked = attack(self.state(), 0)
        chosen = asked.decision.options[1]
        expected = state_to_dict(answer(asked, (chosen,)), format_version=24)
        for copied in (asked.clone(), copy.deepcopy(asked), pickle.loads(pickle.dumps(asked))):
            self.assertEqual(state_to_dict(answer(copied, (chosen,)), format_version=24), expected)


class DragOutTransformTest(unittest.TestCase):
    """RX1 をワザの効果の入れ替えにも当てはめた（意図した既存の動きの変化。docs 7 章）: ［へんしん］のメタモンがひきずりだす（必須）を使い、選べるどの控えでも姿が変わるなら宣言の前に
    止める。同じカードの控えがあれば、それだけを選べる。あとにダメージのないこうそくスピンは聞かない。"""

    def test_drag_out(self):
        state = board(m(H.DITTO, (F, F, F)), opponent=m(H.DARK_MACHOKE, (F,)), opponent_bench=(H.RATTATA,))
        stopped(self, state, UseAttack(0, 0), RX1)
        same = board(m(H.DITTO, (F, F, F)), opponent=m(H.DARK_MACHOKE, (F,)), opponent_bench=(H.RATTATA, m(H.DARK_MACHOKE)))
        asked = attack(same, 0)
        rattata, machoke = asked.decision.options
        self.assertEqual(asked.decision.context_value("unresolved_choices"), (rattata,))
        audited(self, answer(asked, (machoke,)))
        spin = board(m(H.DITTO, (F, F, F)), opponent=m(DONPHAN, (F,)), opponent_bench=(H.RATTATA,), bench=(H.CHANSEY,))
        asked = attack(spin, 1)
        self.assertEqual(asked.decision.context_value("unresolved_choices", ()), ())


# ---------------------------------------------------------------- 8 章: すくいなげ（帰還と入れ替え）


class TuskTossTest(unittest.TestCase):
    """すくいなげ（わるいドンファン）: 相手に控えがいなければワザの失敗。1 枚のコインで、「おもて」は相手とついているカードを手札に、「うら」は相手が選ぶ入れ替え。"""

    def state(self, **kw):
        return board(m(DARK_DONPHAN, (F, F)), opponent=kw.pop("opponent", m(ONIX, (F, F), damage=20)), opponent_bench=kw.pop("opponent_bench", (H.RATTATA,)), **kw)

    def test_heads_returns_to_hand_without_knock_out(self):
        state = self.state()
        target = state.players[1].active
        cards = {target.card, *target.energy}
        done = attack(state, 0, HD)
        self.assertEqual(kinds(state, done, "coin_flip", "return_in_play_to_hand")[:2], ["coin_flip", "return_in_play_to_hand"])
        self.assertFalse(new_events(state, done, "knock_out", "take_prize", "damage"))
        self.assertLessEqual(cards, set(done.players[1].hand))
        self.assertEqual((done.decision.kind, done.decision.player), ("promote_active", 1))
        audited(self, done)

    def test_tails_opponent_chooses_the_switch(self):
        state = self.state()
        done = attack(state, 0, TL)
        self.assertEqual((done.decision.kind, done.decision.player), (FORCED_SWITCH, 1))
        self.assertFalse(new_events(state, done, "return_in_play_to_hand"))
        audited(self, answer(done, done.decision.options))

    def test_no_bench_fails_without_a_coin(self):
        """括弧書き「(相手に控えがいないとき、このワザは失敗する。)」はワザ全体にかかる（「うら」のときだけに狭めない）。ワザを使うための条件の「使えない」でもない。"""
        state = self.state(opponent_bench=())
        done = attack(state, 0)
        self.assertEqual([e["reason"] for e in new_events(state, done, "attack_failed")], [E.ENTANGLE_NO_BENCH])
        self.assertFalse(new_events(state, done, "coin_flip", "return_in_play_to_hand"))

    def test_locked_or_barrier_stops_before_the_coin(self):
        stopped(self, locked(self.state(), 1), UseAttack(0, 0), AL2)
        stopped(self, with_barrier(m(DARK_DONPHAN, (F, F))), UseAttack(1, 0), HC3)

    def test_recycle_energy_goes_to_hand_without_the_trash_trigger(self):
        """もどしたカードはトラッシュしていないので、トラッシュにかかわる効果（リサイクルエネルギー）ははたらかない。"""
        state = self.state(opponent=m(ONIX, (H.RECYCLE_ENERGY,)))
        done = attack(state, 0, HD)
        recycle = next(u for u in state.players[1].active.energy)
        self.assertIn(recycle, done.players[1].hand)
        self.assertFalse(new_events(state, done, "energy_returned_to_hand", "discard_energy"))

    def test_ninja_trick_nt2_is_found_before_declaration(self):
        """NT2: 変わり身の術のついたキョウのドガースを「おもて」で手札にもどす枝（変わり身の術をいっしょにもどすか、トラッシュするかが決まらない）は、宣言の前の先読みが見つける。"""
        from tests.test_reactive_decisions_v0_65 import trick_board

        state, _ = trick_board(opponent=m(DARK_DONPHAN, (F, F)))
        stopped(self, state, UseAttack(1, 0), NT2)

    def test_giant_tusk(self):
        state = board(m(DARK_DONPHAN, (F, F, F)), opponent=m(H.CHANSEY))
        self.assertEqual([e["amount"] for e in new_events(state, attack(state, 1), "damage")], [100])  # 50 × 弱点 2（闘）


# ---------------------------------------------------------------- 9 章: 決定・保存・見えない情報・先読み


class CoinAl2ScopeTest(unittest.TestCase):
    """移動だけを決めるコインの AL2 は、コインが決める要素の全体で判断する（有効な要素も決めるコインには当てはめない）。v0.93 のやみのこえは同じ結果。"""

    def test_scope(self):
        trample = locked(board(m(TAUROS, (W, W)), opponent=m(ONIX, (F,)), opponent_bench=(H.RATTATA,)), 1)
        self.assertTrue(new_events(trample, attack(trample, 0, TL), "coin_flip"))
        tusk = locked(board(m(DARK_DONPHAN, (F, F)), opponent=m(ONIX, (F,)), opponent_bench=(H.RATTATA,)), 1)
        stopped(self, tusk, UseAttack(0, 0), AL2)
        program = P.compile_attack(E.CoinBonusDamageElseForceSwitch(10))
        self.assertEqual([e.coin_receiver() for e in program if e.coin_dependent("coin")], ["damage", "effect"])
        self.assertEqual(QUESTIONS["attack_switch_transformed_attacker"].code, RX1)


class StateTest(unittest.TestCase):
    def test_export_observation_and_copies(self):
        asked = attack(board(m(VULPIX, (R, R)), opponent=m(ONIX, (F,)), opponent_bench=(H.RATTATA,)), 0)
        declined = answer(asked, ())
        for state in (asked, declined):
            for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
                self.assertEqual(state_to_dict(copied, format_version=24), state_to_dict(state, format_version=24))
        self.assertIn(24, FORMAT_VERSIONS)  # v0.99: 今の最新の形式（25）は tests/test_catalog_contract.py。この版の項目は形式 24 で表す（形式を増やしていない）
        for viewer in (0, 1):
            self.assertIn("forced_switch_declined", [e["kind"] for e in visible_log(declined, viewer)])
        self.assertEqual(json.loads(json.dumps(state_to_dict(asked, format_version=24)))["decision"]["min_choices"], 0)

    def test_rejected_answers_keep_state_log_and_rng(self):
        asked = attack(board(m(TOGEPI, (W,)), opponent=m(ONIX, (F,)), bench=(H.CHANSEY,)), 0)
        before = written(asked)
        for command in (ResolveDecision(0, asked.decision.id, ()), ResolveDecision(1, asked.decision.id, asked.decision.options)):
            with self.assertRaises(IllegalActionError):
                apply_kernel(asked, command)
        self.assertEqual(written(asked), before)


class HiddenCardTest(unittest.TestCase):
    """相手のうらのカード（マチスの秘策）: きつねびで選べるもの・止める選択は本当のカードによらない。なげとばすで相手が選んで入れ替えても、入れ替えだけではおもてにしない。"""

    def setUp(self):
        from tests import test_secret_plan_v0_67 as SP

        self.SP = SP

    def hidden_board(self, hidden, attacker):
        SP = self.SP
        return SP.opponent_turn(SP.place(SP.board(hand=(hidden,), opponent=attacker, turn_number=TURN), hidden))

    def test_fox_fire_choices_do_not_depend_on_the_face_down_card(self):
        seen = {}
        for hidden in (H.PLUSPOWER, H.RATTATA):
            with self.subTest(hidden=hidden):
                asking = apply_kernel(self.hidden_board(hidden, m(VULPIX, (R, R))), UseAttack(1, 0))
                seen[hidden] = (asking.decision.options, asking.decision.context_value("unresolved_choices", ()), asking.decision.min_choices)
        self.assertEqual(seen[H.PLUSPOWER], seen[H.RATTATA])

    def test_fling_switch_alone_does_not_reveal(self):
        state = self.hidden_board(H.RATTATA, m(MACHAMP, (F, F, F, F)))
        asking = apply_kernel(state, UseAttack(1, 1))
        pid = self.SP.face_down(state)[0].pokemon_id
        done = apply_kernel(asking, ResolveDecision(0, asking.decision.id, (pid,)))
        self.assertEqual(done.players[0].active.pokemon_id, pid)
        self.assertFalse(new_events(asking, done, "secret_plan_revealed"))
        self.assertTrue(done.is_face_down(done.players[0].active))
        audited(self, done)


class NoCardIdBranchTest(unittest.TestCase):
    def test_engine_and_resolution_have_no_card_id_branches(self):
        for path in [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]:
            text = path.read_text(encoding="utf-8")
            for card in H.V0_94_CARDS:
                with self.subTest(path=path.name, card=card):
                    self.assertNotIn(f'"{card}"', text)


class DocumentTest(unittest.TestCase):
    def test_document_lists_the_cards_rulings_and_counts(self):
        text = DOC.read_text(encoding="utf-8")
        for card in H.V0_94_CARDS:
            self.assertIn(card, text)
        for word in ("1,149", "forced_switch_declined", "RX1", "T27", "DO3", "AL2", "HC3", "NT2", "G37", "rules-2000-02-14.md", "DamageAndForceSwitch"):
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()
