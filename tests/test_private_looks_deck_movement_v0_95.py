"""v0.95（docs/private-looks-deck-movement-v0.95.md）: 手札・山札を見る効果とカードを動かすポケモン 11 枚（ワザ 20・特殊能力 2）。

根拠は kyuura データの採用（kyuura ``7d3f4ca`` の data/cards.json の日本語の印刷の文面）と、既存の規定・読み方の記録（v0.31 の HC6・v0.44 の FC1・v0.47 の［スパイ］の PW3・みらいよち・
おどろかす・v0.55 のロケット団のおねーさん・v0.73 の熱血!の FV1・v0.74 のポケモンタワー・v0.75 のもえあがる・v0.79 の L・v0.83 の LT1・v0.85 のミラクルエネルギー）。英語版の文面・
現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像・pcg-search.com との照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を
確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.95``）。
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
    EvolvePokemon,
    PlayTrainer,
    PowerKey,
    ResolveDecision,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    ARRANGE_DECK_TOP,
    OPPONENT_HAND_TO_DECK,
    OPTIONAL_SHUFFLE,
    SELECT_ATTACHED_TRAINER,
    SELECT_ATTACK,
    SELECT_DECK_OWNER,
)
from kyuura_engine.engine import apply_command_traced
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.observation import (
    HIDDEN_COUNT_KINDS,
    OPTION_MEANINGS,
    PRIVATE_FIELDS,
    PUBLIC_EVENTS,
    observe,
    visible_log,
)
from kyuura_engine.resolution import events as resolution_events
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.release_catalog import cards_after, cards_before
from tests.test_active_leave_locks_v0_93 import locked
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_power_suppression_lasting_locks_v0_92 import board, mon, uid

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "private-looks-deck-movement-v0.95.md"
RULES_DOC = ROOT / "docs" / "rules-2000-02-14.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, R, F, PS, G = H.WATER, H.FIRE, H.FIGHTING, H.PSYCHIC, H.GRASS
XATU, NOCTOWL, SENTRET, ABRA = H.XATU_NEO1, H.NOCTOWL_NEO1, H.SENTRET_NEO2, H.SABRINAS_ABRA_GD6
HAUNTER, HAUNTER_QSG, SCIZOR, SLOWKING = H.HAUNTER_ES3, H.HAUNTER_QSG, H.DARK_SCIZOR_NEO4, H.DARK_SLOWKING_NEO4
QUILAVA, RHYDON, AIPOM = H.DARK_QUILAVA_NEO4, H.RHYDON_ES3, H.AIPOM_NEO3
GASTLY_ES3, SCYTHER_NEO4 = H.GASTLY_ES3, H.SCYTHER_NEO4
POTION, DEFENDER = H.POTION, H.DEFENDER
RAINBOW, MIRACLE, TOWER = H.RAINBOW_ENERGY, H.MIRACLE_ENERGY, H.POKEMON_TOWER
FOCUS_BAND = "neo1-088"  # きあいのハチマキ（ポケモンのどうぐ。場をはなれるまでついたまま）
EFFECT_GUARD = "ES2-033"  # エフェクトガード（相手のワザによる「ダメージ以外の効果」を受けない。次の相手の番の終わりにトラッシュ）
BELOW = {XATU: H.NATU_NEO1, NOCTOWL: H.HOOTHOOT_NEO1, HAUNTER: GASTLY_ES3, HAUNTER_QSG: H.GASTLY_QSG, SCIZOR: SCYTHER_NEO4, SLOWKING: H.SLOWPOKE_NEO1,
         QUILAVA: H.CYNDAQUIL_NEO1, RHYDON: H.RHYHORN, H.OMANYTE: H.MYSTERIOUS_FOSSIL, H.HAUNTER: H.GASTLY, H.MUK: H.GRIMER}
V095_ATTACKS = [AttackKey(c, i) for c in H.V0_95_POKEMON for i in range(len(load_card_pool().definitions[c].attacks))]
V095_POWERS = [PowerKey(NOCTOWL, 0), PowerKey(SLOWKING, 0)]
LT1, FC1, PW3, HC6, FV1 = ("UNRESOLVED_ATTACK_DECK_TOP_SHORT", "UNRESOLVED_STATED_CARDS_SHORT", "UNRESOLVED_POWER_ZERO_CARDS", "UNRESOLVED_DISCARD_DECK_SHORT",
                           "UNRESOLVED_FERVOR_RAINBOW_ENERGY")
SC1 = "UNRESOLVED_SCRAM_TIMING"


def m(card, energy=(), **extra):
    """場のポケモンの指定（進化ポケモンには進化元を付ける）。"""
    spec = mon(card, energy, **extra)
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def attack(state, index, *coins, player=None):
    player = state.current_player if player is None else player
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UseAttack(player, index))


def power(state, pokemon_id=None, *coins):
    player = state.current_player
    pokemon_id = state.players[player].active.pokemon_id if pokemon_id is None else pokemon_id
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UsePokemonPower(player, pokemon_id, 0))


def answer(state, choices, player=None):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player if player is None else player, d.id, tuple(choices)))


def kinds(before, after, *names):
    return [e["kind"] for e in new_events(before, after, *names)]


def written(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log], repr(state.rng.getstate())


def shuffles(before, after):
    return [e for e in new_events(before, after, "shuffle")]


def card_ids(state, uids):
    return [state.cards[u].card_id for u in uids]


def preflight_results(state, command):
    _, trace = apply_command_traced(state, command)
    return [(r.strategy, r.branches) for r in trace.of(resolution_events.PreflightResult)]


def deck_board(active, deck, *, prizes=(W,) * 6, discard=(), opponent=None):
    """自分の山札・サイドを決めた盤面（マグマラッシュ・やまくずしの、山札とサイドの中身から決まるありうる枚数を確かめるため）。"""
    me = {"active": active, "bench": [H.RATTATA], "hand": [], "deck": list(deck), "discard": list(discard), "prizes": list(prizes)}
    them = {"active": opponent or mon(H.ONIX, (F,)), "bench": [H.RATTATA], "hand": [], "deck": [W] * 10, "discard": [], "prizes": 6}
    return H.build_test_state([me, them], turn_number=7, current_player=0)


def question_at_base(amount):
    """テスト専用: 相手の対戦ポケモンへの基本となるダメージが ``amount`` のときだけ、既存の問い（SC1）に当たるようにする ``deal_damage``（量でだけ当たる問いの代わり）。"""
    original = P.deal_damage

    def patched(res, fs, target, base, **kw):
        if base == amount:
            raise res.question("scram_timing", f"テスト専用（基本となるダメージ {base}）")
        return original(res, fs, target, base, **kw)

    return mock.patch.object(P, "deal_damage", patched)


# ---------------------------------------------------------------- 1〜3 章: 対象・登録・文面


class RegistrationTest(unittest.TestCase):
    def test_every_attack_and_power_is_registered(self):
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_95"]), H.V0_95_CARDS)
        self.assertEqual(len(V095_ATTACKS), 20)
        for key in V095_ATTACKS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
                printed = pool.definitions[key.card_id].attacks[key.attack_index]
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja), (printed.name_ja, printed.text_ja, printed.text_ja))
                self.assertEqual(entry.effect.check(printed), [])
                self.assertIsNone(DEFAULT_EFFECTS.attack_problem(key.card_id, printed, pool.definitions[key.card_id].attacks))
        for key in V095_POWERS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.power_entry(key.card_id, key.power_index)
                printed = pool.definitions[key.card_id].powers[key.power_index]
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja), (printed.name_ja, printed.text_ja, printed.text_ja))
                self.assertEqual(entry.effect.check(printed), [])
                self.assertIsNone(DEFAULT_EFFECTS.power_problem(key.card_id, printed))
        for card in H.V0_95_CARDS:
            self.assertIn(card, pool.playable_ids)
        self.assertEqual([c for c in H.V0_95_CARDS if pool.definitions[c].powers], [NOCTOWL, SLOWKING])

    def test_types(self):
        effect = lambda card, i: DEFAULT_EFFECTS.attack_entry(card, i).effect
        self.assertEqual(effect(XATU, 0), E.ArrangeDeckTopExactlyEffect(3))
        self.assertEqual(effect(XATU, 1), E.ConfuseOnHeads())
        self.assertIs(effect(NOCTOWL, 0), E.DAMAGE_ONLY)
        self.assertEqual(effect(SENTRET, 0), E.LookOpponentHandAttack())
        self.assertIs(effect(SENTRET, 1), E.DAMAGE_ONLY)
        self.assertEqual(effect(ABRA, 0), E.LookOpponentHandAttack())
        self.assertEqual(effect(ABRA, 1), E.CoinBonusDamage(20))
        self.assertEqual(effect(HAUNTER, 0), E.DamageTimesLookedHandTrainers(10))
        self.assertEqual(effect(HAUNTER, 1), E.DamageThenStatusByCoin(E.SLEEP, E.CONFUSION))
        self.assertEqual(effect(SCIZOR, 0), E.CoinLookOpponentHandTrainerToDeck())
        self.assertIs(effect(SCIZOR, 1), E.DAMAGE_ONLY)
        self.assertEqual(effect(SLOWKING, 0), E.DamageIgnoringWeaknessResistance())
        self.assertEqual(effect(QUILAVA, 0), E.OpponentDeckTopDiscardIfTrainer())
        self.assertEqual(effect(QUILAVA, 1), E.MillSelfThenDamage(5, E.EnergyType.FIRE, 20))
        self.assertEqual(effect(RHYDON, 0), E.DamageThenMillReturnTypeEnergy(5, E.EnergyType.FIGHTING))
        self.assertEqual(effect(RHYDON, 1), E.CoinBonusDamage(20))
        self.assertEqual(effect(AIPOM, 0), E.ReturnOpponentAttachedTrainerToDeck())
        self.assertIs(effect(AIPOM, 1), E.DAMAGE_ONLY)
        self.assertEqual(DEFAULT_EFFECTS.power_entry(NOCTOWL, 0).effect, E.CoinLookOpponentHandMayReturnTrainer())
        self.assertEqual(DEFAULT_EFFECTS.power_entry(SLOWKING, 0).effect, E.CoinPeekOpponentDeckTopMayShuffle())
        self.assertTrue(E.CoinLookOpponentHandMayReturnTrainer.once_per_turn and E.CoinPeekOpponentDeckTopMayShuffle.once_per_turn)

    def test_the_haunter_pair_shares_one_registration(self):
        """ゴースト（ES3-024・QSG-029）はゲーム用データが同じ組（SC-ES3-024）。id ごとに登録し、同じ登録の値を使う。"""
        self.assertEqual(dict(E.SAME_DATA_CARDS_V0_95), {HAUNTER_QSG: HAUNTER})
        extract = {c["id"]: c for c in read_extract()["cards"]}
        self.assertEqual(extract[HAUNTER_QSG]["same_card_group"], extract[HAUNTER]["same_card_group"])
        self.assertEqual(extract[HAUNTER_QSG]["pokemon"], extract[HAUNTER]["pokemon"])
        for i in range(2):
            self.assertIs(DEFAULT_EFFECTS.attack_entry(HAUNTER_QSG, i), DEFAULT_EFFECTS.attack_entry(HAUNTER, i))

    def test_unregistered_without_the_v0_95_entries(self):
        """今回の登録を除くと対戦に使えなくなるのは、ちょうど 11 枚（ほかのカードは失われない）。過去の範囲は ``cards_before`` で切り出す。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V095_ATTACKS)
        registry = registry.without_powers(registry.id, V095_POWERS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(H.V0_95_CARDS))
        self.assertEqual(set(H.V0_95_CARDS) & set(cards_before(read_extract(), "0.95")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.94")), set(H.V0_95_CARDS))

    def test_evolution_bases_exist(self):
        pool = load_card_pool()
        for card, base in ((XATU, "ネイティ"), (NOCTOWL, "ホーホー"), (HAUNTER, "ゴース"), (HAUNTER_QSG, "ゴース"), (SCIZOR, "ストライク"), (SLOWKING, "ヤドン"),
                           (QUILAVA, "ヒノアラシ"), (RHYDON, "サイホーン")):
            with self.subTest(card=card):
                self.assertEqual(pool.definitions[card].evolves_from, base)
                state = board(m(BELOW[card], played_turn=3), hand=(card,))
                evolved = apply_kernel(state, EvolvePokemon(0, uid(state, card), state.players[0].active.pokemon_id))
                self.assertEqual(evolved.cards[evolved.players[0].active.card].card_id, card)
                audited(self, evolved)
        for card in (SENTRET, ABRA, AIPOM):
            self.assertEqual(pool.definitions[card].stage, "basic")


class TextTest(unittest.TestCase):
    """既存の型に加えた全文は、意味と引数が同じものだけ（マインドショック・マグマラッシュ・カツラのブーバー GD5-011 の書き方）。新しい型は全文を照らし、似た形の別の文面を通さない。"""

    def test_reused_types_accept_exactly_the_added_texts(self):
        pool = load_card_pool()
        attack = lambda card, i: pool.definitions[card].attacks[i]
        self.assertEqual(E.DamageIgnoringWeaknessResistance().check(attack(SLOWKING, 0)), [])
        self.assertEqual(attack(SLOWKING, 0).text_ja, E.MIND_SHOCK_IGNORING_TEXT)
        for card in ("PMCG6-031", "GD5-011", QUILAVA):
            with self.subTest(card=card):
                index = 1
                self.assertEqual(E.MillSelfThenDamage(5, E.EnergyType.FIRE, 20).check(attack(card, index)), [])
                self.assertTrue(E.MillSelfThenDamage(5, E.EnergyType.FIRE, 30).check(attack(card, index)))  # 1 枚あたりのダメージを照らす
                self.assertTrue(E.MillSelfThenDamage(5, E.EnergyType.WATER, 20).check(attack(card, index)))  # 色を照らす
                self.assertTrue(E.MillSelfThenDamage(3, E.EnergyType.FIRE, 20).check(attack(card, index)))  # 枚数を照らす
        self.assertEqual(attack(XATU, 1).text_ja, DEFAULT_EFFECTS.attack_entry("ES3-004", 1).text_ja)  # あやしいひかり（既存のサイケこうせんと同じ全文）
        self.assertEqual(attack(HAUNTER, 1).text_ja, E.PSYCHIC_HORROR_TEXT)
        self.assertEqual(attack(ABRA, 1).text_ja, attack(RHYDON, 1).text_ja)

    def test_new_texts_are_not_interchanged(self):
        pool = load_card_pool()
        attack = lambda card, i: pool.definitions[card].attacks[i]
        self.assertTrue(E.ArrangeDeckTopEffect(3).check(attack(XATU, 0)))  # 「3枚まで」の型で通さない
        self.assertTrue(E.ArrangeDeckTopExactlyEffect(3).check(pool.definitions["PMCG3-032"].attacks[0]))  # スリーパーの「3枚まで」をちょうどの型で通さない
        self.assertTrue(E.LookOpponentHandCardToDeck().check(attack(SCIZOR, 0)))  # おどろかすの型で通さない
        self.assertTrue(E.CoinLookOpponentHandTrainerToDeck().check(attack(SENTRET, 0)))
        self.assertTrue(E.CoinOpponentDeckTopDiscardTrainerElseHand().check(attack(QUILAVA, 0)))  # てつだうふり（コイン・手札に加える）の型で通さない
        self.assertTrue(E.DamageThenMillOwnDeck(5).check(attack(RHYDON, 0)))  # 手札に加える部分を落とさない
        self.assertTrue(E.DamageTimesLookedHandTrainers(20).check(attack(HAUNTER, 0)))
        self.assertTrue(E.ReturnOpponentAttachedTrainerToDeck().check(attack(SCIZOR, 0)))
        rocket = DEFAULT_EFFECTS.trainer_entry("PMCG4-061")
        self.assertIn("あれば", rocket.text_ja)
        self.assertNotIn("あれば", attack(SCIZOR, 0).text_ja)
        self.assertIn("あれば", DEFAULT_EFFECTS.power_entry(NOCTOWL, 0).text_ja)


class RulesDocumentTest(unittest.TestCase):
    def test_reference_section(self):
        text = RULES_DOC.read_text(encoding="utf-8")
        for word in ("private-looks-deck-movement-v0.95.md", "LT1", "FV1", "PW3", "HC6", "根拠のある規定", "未解決", "実装上の読み方"):
            self.assertIn(word, text)


# ---------------------------------------------------------------- 4 章: 見る効果の共通の処理


class LookHandTest(unittest.TestCase):
    """さぐる（オタチ）・とうし（ナツメのケーシィ）: 相手の手札を見るだけ。見たプレイヤーと持ち主だけに見え、観戦者には見せない。続けて見せる効果ではない。0 枚でも使える。"""

    def test_look_is_private_and_moves_nothing(self):
        for card, energy in ((SENTRET, W), (ABRA, PS)):
            with self.subTest(card=card):
                state = board(m(card, (energy,)), opponent_hand=(POTION, W, POTION))
                done = attack(state, 0)
                (look,) = new_events(state, done, "look_at_hand")
                self.assertEqual((look["player"], look["owner"], look["effect"], look["cards"]), (0, 1, f"{card}#0", tuple(state.players[1].hand)))
                self.assertNotIn("trainer_card", look)
                self.assertEqual(done.players[1].hand[:3], state.players[1].hand)
                for viewer in (0, 1):
                    self.assertEqual([e for e in visible_log(done, viewer) if e["kind"] == "look_at_hand"][-1]["cards"], look["cards"])
                self.assertEqual([e for e in visible_log(done, None) if e["kind"] == "look_at_hand"][-1]["hidden"], {"cards": 3})
                self.assertFalse([e for e in new_events(state, done) if e["kind"] in ("coin_flip", "shuffle", "damage")])
                audited(self, done)

    def test_snapshot_not_a_continuing_reveal(self):
        state = board(m(SENTRET, (W,)), opponent_hand=(POTION,))
        done = attack(state, 0)
        for viewer in (0, None):
            self.assertIsNone(observe(done, viewer)["players"][1]["hand"]["cards"])  # 見たあとも、観測の手札は枚数だけ（続けて見せる効果ではない）

    def test_empty_hand(self):
        state = board(m(ABRA, (PS,)), opponent_hand=())
        done = attack(state, 0)
        self.assertEqual([e["cards"] for e in new_events(state, done, "look_at_hand")], [()])
        audited(self, done)

    def test_trainer_logs_keep_their_shape(self):
        state = board(m(SENTRET, (W,)), hand=("PMCG4-061",), opponent_hand=(POTION, W))
        played = apply_kernel(state, PlayTrainer(0, uid(state, "PMCG4-061")))
        (look,) = new_events(state, played, "look_at_hand")
        self.assertEqual(sorted(look), sorted(["kind", "turn", "player", "owner", "cards", "trainer_card"]))
        with self.assertRaises(RuntimeError):
            from kyuura_engine.zones import look_at_hand
            look_at_hand(state.clone(), 0, 1, effect="x", power="y")


class PoltergeistTest(unittest.TestCase):
    """ポルターガイスト（ゴースト）: 見た手札のトレーナーカードの枚数 × 10 が基本となるダメージ（0 枚なら 0。失敗ではない）。宣言の前の先読みは枚数のすべてを試す。"""

    def test_base_is_trainers_times_ten(self):
        for hand, expected in (((POTION, W, DEFENDER), 20), ((W, W), 0), ((), 0), ((H.CLEFAIRY_DOLL, H.MYSTERIOUS_FOSSIL, POTION), 30)):
            with self.subTest(hand=hand):
                state = board(m(HAUNTER, (PS,)), opponent=m(H.ONIX, (F,)), opponent_hand=hand)
                done = attack(state, 0)
                self.assertEqual(kinds(state, done, "look_at_hand", "damage"), ["look_at_hand", "damage"])
                (damage,) = new_events(state, done, "damage")
                self.assertEqual(damage["steps"][0], ("1 基本となる計算", expected))
                self.assertFalse(new_events(state, done, "attack_failed"))
                audited(self, done)

    def test_acceptance_does_not_depend_on_the_hand_contents(self):
        """同じ手札の枚数で、トレーナーカードの枚数だけが違う 2 つの盤面: 基本となるダメージが 30 のときだけ当たる問いを置くと、どちらも宣言の前に止まる（3 枚のトレーナーが
        ない盤面でも止まる）。手札が 2 枚なら 30 にならないので受け付ける。止めたときは状態・ログ・乱数を変えない。"""
        with question_at_base(30):
            for hand in ((POTION, POTION, POTION), (W, W, W), (POTION, W, W)):
                with self.subTest(hand=hand):
                    rejects(self, board(m(HAUNTER, (PS,)), opponent=m(H.ONIX, (F,)), opponent_hand=hand), UseAttack(0, 0), SC1)
            audited(self, attack(board(m(HAUNTER, (PS,)), opponent=m(H.ONIX, (F,)), opponent_hand=(POTION, POTION)), 0))
        state = board(m(HAUNTER, (PS,)), opponent=m(H.ONIX, (F,)), opponent_hand=(W, W, W))
        self.assertEqual(preflight_results(state, UseAttack(0, 0)), [("siblings", 4)])  # 実際の 0 枚と、ほかの 3 通り（1〜3 枚）
        self.assertEqual(preflight_results(board(m(HAUNTER, (PS,)), opponent=m(H.ONIX, (F,)), opponent_hand=()), UseAttack(0, 0)), [("single", 1)])

    def test_pre_look_observation_is_the_same(self):
        a = board(m(HAUNTER, (PS,)), opponent_hand=(POTION, POTION))
        b = board(m(HAUNTER, (PS,)), opponent_hand=(W, W))
        for viewer in (0, None):
            self.assertEqual(observe(a, viewer)["players"][1]["hand"], observe(b, viewer)["players"][1]["hand"])

    def test_undealt_amount_is_hidden_from_spectators_only(self):
        """「とうめい」で受けなかったダメージの量は、観戦者には見せない（見たプレイヤーと持ち主は知っている）。ほかのワザ（マインドショック）の量は今までどおり全員に見える。
        ダメージを無効にする状態（ログ ``damage_prevented``）には量を書かない。"""
        state = board(m(HAUNTER, (PS,)), opponent=m(H.HAUNTER, (PS,)), opponent_hand=(POTION, POTION))
        done = attack(state, 0, HD)
        (evaded,) = new_events(state, done, "attack_evaded")
        self.assertEqual((evaded["amount"], evaded["amount_private"]), (20, True))
        index = done.log.index(evaded)
        self.assertEqual(visible_log(done, None)[index]["hidden"], {"amount": None})
        for viewer in (0, 1):
            self.assertEqual(visible_log(done, viewer)[index]["amount"], 20)
        other = board(m(SLOWKING, (PS, PS)), opponent=m(H.HAUNTER, (PS,)))
        shocked = attack(other, 0, HD)
        (plain,) = new_events(other, shocked, "attack_evaded")
        self.assertNotIn("amount_private", plain)
        self.assertEqual(visible_log(shocked, None)[shocked.log.index(plain)]["amount"], 30)
        self.assertEqual(PRIVATE_FIELDS["attack_evaded"][0], ("amount",))
        for kind in ("damage_guard_check", "reflect_shield_check"):
            self.assertEqual(PRIVATE_FIELDS[kind][0], ("amount",))
            self.assertNotIn(kind, PUBLIC_EVENTS)
        audited(self, done)

    def test_copied_and_transformed_use_look_at_the_opponent_of_the_user(self):
        """ゆびをふる（ピクシー）で相手のゴーストのポルターガイストを使う・［へんしん］のメタモンが使う: 見るのはワザを使ったプレイヤー、見る手札はその相手の手札。"""
        state = board(m(H.CLEFABLE, (W, W, W), evolved_from=H.CLEFAIRY), opponent=m(HAUNTER, (PS,)), opponent_hand=(POTION, W))
        asked = attack(state, 0)
        self.assertEqual(asked.decision.kind, SELECT_ATTACK)
        done = answer(asked, (0,))
        (look,) = new_events(asked, done, "look_at_hand")
        self.assertEqual((look["player"], look["owner"]), (0, 1))
        self.assertEqual(new_events(asked, done, "damage")[0]["steps"][0], ("1 基本となる計算", 10))
        ditto = board(m(H.DITTO, (PS,)), opponent=m(HAUNTER, (PS,)), opponent_hand=(POTION, POTION, W))
        used = attack(ditto, 0)
        self.assertEqual(new_events(ditto, used, "damage")[0]["steps"][0], ("1 基本となる計算", 20))
        audited(self, done)
        audited(self, used)


class ThreatenTest(unittest.TestCase):
    """おどす（わるいハッサム）: コインの「おもて」で相手の手札を見て、トレーナーカードを 1 枚選んで相手の山札にもどし、切る。トレーナーカードがなければ、もどさずに切る
    （v0.75・v0.79 の読み方）。コインは手札の中身によらず投げる。"""

    def test_heads_returns_the_chosen_trainer_then_shuffles_once(self):
        state = board(m(SCIZOR, (W, W)), opponent_hand=(POTION, W, DEFENDER))
        asked = attack(state, 0, HD)
        hand = state.players[1].hand
        self.assertEqual((asked.decision.kind, asked.decision.player, asked.decision.options), (OPPONENT_HAND_TO_DECK, 0, (hand[0], hand[2])))
        self.assertEqual(asked.decision.context_value("owner"), 1)
        done = answer(asked, (hand[2],))
        self.assertEqual([e["card"] for e in new_events(asked, done, "opponent_hand_to_deck")], [hand[2]])
        self.assertEqual([e["player"] for e in shuffles(asked, done)], [1])
        self.assertIn(hand[2], done.players[1].deck)
        self.assertNotIn(hand[2], done.players[1].hand)
        returned = [e for e in done.log if e["kind"] == "opponent_hand_to_deck"][-1]
        for viewer, sees in ((0, True), (1, True), (None, False)):
            self.assertEqual("card" in visible_log(done, viewer)[done.log.index(returned)], sees)
        audited(self, done)

    def test_no_trainer_or_empty_hand_still_flips_and_shuffles(self):
        for hand in ((W, W), ()):
            with self.subTest(hand=hand):
                state = board(m(SCIZOR, (W, W)), opponent_hand=hand)
                done = attack(state, 0, HD)
                self.assertIsNone(done.decision)
                self.assertEqual(kinds(state, done, "coin_flip", "look_at_hand", "opponent_hand_to_deck", "shuffle"), ["coin_flip", "look_at_hand", "shuffle"])
                audited(self, done)
        tails = attack(board(m(SCIZOR, (W, W)), opponent_hand=(POTION,)), 0, TL)
        self.assertFalse([e for e in tails.log if e["kind"] in ("look_at_hand", "shuffle", "opponent_hand_to_deck") and e.get("effect")])
        empty = board(m(SCIZOR, (W, W)), opponent_hand=(), opponent_deck=[])
        done = attack(empty, 0)
        self.assertFalse(new_events(empty, done, "coin_flip", "look_at_hand", "shuffle"))  # 手札も山札も 0 枚なら処理の対象がない

    def test_pair_boards_accept_and_observe_the_same_before_the_look(self):
        """手札の枚数が同じで中身だけが違う 2 つの盤面: 宣言を受け付け、コインまでの観測（ワザを使ったプレイヤー・観戦者）が同じ。見たあとの違い（決定があるか・もどしたか）は
        ワザの処理の結果として許す。"""
        with_trainer = board(m(SCIZOR, (W, W)), opponent_hand=(POTION, W))
        without = board(m(SCIZOR, (W, W)), opponent_hand=(W, W))
        for viewer in (0, None):
            self.assertEqual(json.dumps(observe(with_trainer, viewer)["players"][1]["hand"]), json.dumps(observe(without, viewer)["players"][1]["hand"]))
        a, b = attack(with_trainer, 0, HD), attack(without, 0, HD)
        self.assertEqual(kinds(with_trainer, a)[:3], kinds(without, b)[:3])
        self.assertEqual(preflight_results(with_trainer, UseAttack(0, 0))[0][0], "full")
        self.assertIsNotNone(a.decision)
        self.assertIsNone(b.decision)

    def test_invalid_answers_and_copies(self):
        state = board(m(SCIZOR, (W, W)), opponent_hand=(POTION, W, DEFENDER))
        asked = attack(state, 0, HD)
        before = written(asked)
        for choices in ((state.players[1].hand[1],), (), state.players[1].hand[:1] + state.players[1].hand[2:]):
            with self.assertRaises(IllegalActionError):
                answer(asked, choices)
        with self.assertRaises(IllegalActionError):
            answer(asked, asked.decision.options[:1], player=1)
        self.assertEqual(written(asked), before)
        results = []
        for copied in (asked.clone(), copy.deepcopy(asked), pickle.loads(pickle.dumps(asked))):
            self.assertEqual(state_to_dict(copied, format_version=max(FORMAT_VERSIONS)), state_to_dict(asked, format_version=max(FORMAT_VERSIONS)))
            done = answer(copied, asked.decision.options[:1])
            results.append(written(done))
            self.assertEqual(len(shuffles(asked, done)), 1)
            self.assertEqual(len(new_events(asked, done, "opponent_hand_to_deck", "look_at_hand", "coin_flip")), 1)
        self.assertEqual(len(set(map(repr, results))), 1)
        self.assertEqual(observe(asked, 1)["decision"], {"kind": OPPONENT_HAND_TO_DECK, "player": 0})
        self.assertEqual(observe(asked, None)["decision"], {"kind": OPPONENT_HAND_TO_DECK, "player": 0})
        self.assertEqual([o.get("card_id") for o in observe(asked, 0)["decision"]["options"]], [POTION, DEFENDER])
        self.assertIn(OPPONENT_HAND_TO_DECK, HIDDEN_COUNT_KINDS)


class GlaringGazeTest(unittest.TestCase):
    """［みやぶる］（ヨルノズク）: 自分の番ごとに 1 回。「うら」でも使ったことになる。「おもて」で相手の手札を見て、トレーナーカードがあれば 1 枚を相手の山札にもどして切る。
    なければもどさず切らない（「あれば」）。手札 0 枚でも使える。ねむり・マヒ・こんらん・特殊能力を消す効果では使えない。"""

    def state(self, hand=(POTION, W, DEFENDER), **kw):
        return board(m(NOCTOWL, ()), opponent_hand=hand, **kw)

    def test_heads_returns_one_trainer_and_shuffles(self):
        state = self.state()
        asked = power(state, None, HD)
        hand = state.players[1].hand
        self.assertEqual((asked.decision.kind, asked.decision.resume, asked.decision.options), (OPPONENT_HAND_TO_DECK, "power", (hand[0], hand[2])))
        (look,) = new_events(state, asked, "look_at_hand")
        self.assertEqual(look["power"], f"{NOCTOWL}@power0")
        done = answer(asked, (hand[0],))
        self.assertEqual([e.get("power") for e in new_events(asked, done, "opponent_hand_to_deck", "shuffle")], [f"{NOCTOWL}@power0"] * 2)
        self.assertEqual([e["player"] for e in shuffles(asked, done)], [1])
        rejects(self, done, UsePokemonPower(0, done.players[0].active.pokemon_id, 0), "POWER_ALREADY_USED", IllegalActionError)
        audited(self, done)

    def test_tails_none_and_empty_hand(self):
        state = self.state()
        tails = power(state, None, TL)
        self.assertEqual(kinds(state, tails), ["pokemon_power", "coin_flip"])
        rejects(self, tails, UsePokemonPower(0, tails.players[0].active.pokemon_id, 0), "POWER_ALREADY_USED", IllegalActionError)
        for hand in ((W, W), ()):
            with self.subTest(hand=hand):
                s = self.state(hand)
                done = power(s, None, HD)
                self.assertEqual(kinds(s, done), ["pokemon_power", "coin_flip", "look_at_hand"])  # もどさず、切らない
                self.assertIsNone(done.decision)
                audited(self, done)

    def test_status_and_suppression_block_use(self):
        for spec, code in (({"sleep": True}, "POKEMON_ASLEEP"), ({"paralysis": 6}, "POKEMON_PARALYZED"), ({"confusion": True}, "POKEMON_CONFUSED")):
            with self.subTest(spec=spec):
                state = board(m(NOCTOWL, (), **spec), opponent_hand=(POTION,))
                rejects(self, state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0), code, IllegalActionError)
        gas = board(m(NOCTOWL, ()), opponent=m(H.MUK, (G,)), opponent_hand=(POTION,))
        with self.assertRaises(IllegalActionError) as caught:
            power(gas, None, HD)
        self.assertEqual(caught.exception.code, "POWER_SUPPRESSED")

    def test_pair_boards_are_accepted_alike(self):
        for hand in ((POTION, POTION), (W, W)):
            state = self.state(hand)
            done = power(state, None, HD)
            self.assertEqual(kinds(state, done)[:3], ["pokemon_power", "coin_flip", "look_at_hand"])

    def test_invalid_answer_keeps_state(self):
        asked = power(self.state(), None, HD)
        before = written(asked)
        for choices in ((asked.players[1].hand[1],), ()):
            with self.assertRaises(IllegalActionError):
                answer(asked, choices)
        self.assertEqual(written(asked), before)
        for copied in (asked.clone(), copy.deepcopy(asked), pickle.loads(pickle.dumps(asked))):
            done = answer(copied, asked.decision.options[:1])
            self.assertEqual(len(shuffles(asked, done)), 1)


class CunningTest(unittest.TestCase):
    """［わるぢえ］（わるいヤドキング）: 自分の番ごとに 1 回。「おもて」で相手の山札の一番上を見てもどし、のぞむなら切る。切らないなら並び・乱数は変わらない。山札 0 枚は PW3。"""

    def state(self, deck=(POTION, W, R, F), **kw):
        return board(m(SLOWKING, (PS,)), opponent_deck=list(deck), **kw)

    def test_heads_look_then_choose_to_shuffle(self):
        state = self.state()
        asked = power(state, None, HD)
        (look,) = new_events(state, asked, "look_at_card")
        self.assertEqual((look["owner"], look["zone"], look["position"], look["card"]), (1, "deck", 0, state.players[1].deck[0]))
        index = asked.log.index(look)
        self.assertIn("card", visible_log(asked, 0)[index])
        for viewer in (1, None):
            self.assertNotIn("card", visible_log(asked, viewer)[index])
        self.assertEqual((asked.decision.kind, asked.decision.options, asked.decision.min_choices, asked.decision.max_choices), (OPTIONAL_SHUFFLE, (1,), 0, 1))
        declined = answer(asked, ())
        self.assertEqual(kinds(asked, declined), ["shuffle_declined"])
        self.assertEqual((declined.players[1].deck, declined.rng.getstate()), (asked.players[1].deck, asked.rng.getstate()))
        shuffled = answer(asked, (1,))
        self.assertEqual([e["power"] for e in shuffles(asked, shuffled)], [f"{SLOWKING}@power0"])
        rejects(self, shuffled, UsePokemonPower(0, shuffled.players[0].active.pokemon_id, 0), "POWER_ALREADY_USED", IllegalActionError)
        for done in (declined, shuffled):
            audited(self, done)

    def test_tails_and_empty_deck(self):
        state = self.state()
        tails = power(state, None, TL)
        self.assertEqual(kinds(state, tails), ["pokemon_power", "coin_flip"])
        self.assertIsNone(tails.decision)
        empty = self.state(())
        rejects(self, empty, UsePokemonPower(0, empty.players[0].active.pokemon_id, 0), PW3)  # コインの前（状態・乱数を変えない）
        asleep = board(m(SLOWKING, (PS,), sleep=True), opponent_deck=[W])
        rejects(self, asleep, UsePokemonPower(0, asleep.players[0].active.pokemon_id, 0), "POKEMON_ASLEEP", IllegalActionError)

    def test_invalid_answers_and_copies(self):
        asked = power(self.state(), None, HD)
        before = written(asked)
        for choices in ((0,), (1, 1)):
            with self.assertRaises(IllegalActionError):
                answer(asked, choices)
        with self.assertRaises(IllegalActionError):
            answer(asked, (), player=1)
        self.assertEqual(written(asked), before)
        for copied in (asked.clone(), copy.deepcopy(asked), pickle.loads(pickle.dumps(asked))):
            self.assertEqual(len(shuffles(asked, answer(copied, (1,)))), 1)
            self.assertEqual(shuffles(asked, answer(copied, ())), [])
        self.assertEqual(OPTION_MEANINGS[OPTIONAL_SHUFFLE], "number")


class ProphecyTest(unittest.TestCase):
    """みらいよち（ネイティオ）: 自分または相手の山札の上からちょうど 3 枚を見て、好きな順番でもどす（切らない）。3 枚より少ない山札は LT1 で選ぶと止める（もう一方は止めない）。"""

    def test_look_exactly_three_and_arrange(self):
        state = board(m(XATU, (PS,)), opponent_deck=[W, R, F, G, W])
        asked = attack(state, 0)
        self.assertEqual((asked.decision.kind, asked.decision.options, asked.decision.context_value("unresolved_choices", ())), (SELECT_DECK_OWNER, (0, 1), ()))
        looked = answer(asked, (1,))
        top = tuple(state.players[1].deck[:3])
        (look,) = new_events(asked, looked, "look_at_deck_top")
        self.assertEqual((look["owner"], look["count"], look["cards"]), (1, 3, top))
        self.assertEqual((looked.decision.kind, looked.decision.options, looked.decision.min_choices), (ARRANGE_DECK_TOP, top, 3))
        for viewer in (1, None):
            self.assertNotIn("cards", visible_log(looked, viewer)[looked.log.index(look)])
        done = answer(looked, tuple(reversed(top)))
        self.assertEqual([e["cards"] for e in new_events(looked, done, "arrange_deck_top")], [tuple(reversed(top))])
        # 番が終わり、相手は並べかえたあとの一番上を引く。見た部分より下の並びは変わらない
        self.assertEqual((done.players[1].hand[-1], done.players[1].deck[:4]), (top[2], [top[1], top[0], *state.players[1].deck[3:5]]))
        self.assertEqual([e for e in new_events(looked, done, "shuffle")], [])
        self.assertFalse(new_events(state, done, "shuffle", "select_look_count"))
        audited(self, done)

    def test_short_deck_is_selectable_but_stops_and_both_short_stop_before_declaration(self):
        state = board(m(XATU, (PS,)), deck=[W] * 6, opponent_deck=[W, R])
        asked = attack(state, 0)
        self.assertEqual(asked.decision.context_value("unresolved_choices"), (1,))
        self.assertEqual(asked.decision.context_value("unresolved_code"), LT1)
        rejects(self, asked, lambda s: ResolveDecision(0, s.decision.id, (1,)), LT1)
        audited(self, answer(answer(asked, (0,)), tuple(asked.players[0].deck[:3])))
        rejects(self, board(m(XATU, (PS,)), deck=[W, W], opponent_deck=[]), UseAttack(0, 0), LT1)

    def test_invalid_arrangements(self):
        looked = answer(attack(board(m(XATU, (PS,)), deck=[W, R, F, G]), 0), (0,))
        options = looked.decision.options
        before = written(looked)
        for choices in (options[:2], (options[0], options[0], options[1]), (options[0], options[1], looked.players[0].deck[3])):
            with self.assertRaises(IllegalActionError):
                answer(looked, choices)
        self.assertEqual(written(looked), before)
        self.assertEqual(E.ArrangeDeckTopExactlyEffect(3).decision_problems(looked, E.AttackUse(0, 1, AttackKey(XATU, 0)), looked.decision), [])


class ScorchTest(unittest.TestCase):
    """もやす（わるいマグマラシ）: 相手の山札の一番上を見て、トレーナーカードならトラッシュ、でなければそのまま（手札に加えない・切らない）。山札 0 枚は見るカードがない。"""

    def test_trainer_is_discarded_other_kept(self):
        state = board(m(QUILAVA, (R,)), opponent_deck=[POTION, W, W])
        done = attack(state, 0)
        top = state.players[1].deck[0]
        self.assertEqual(kinds(state, done, "look_at_card", "discard_from_deck"), ["look_at_card", "discard_from_deck"])
        self.assertIn(top, done.players[1].discard)
        kept = board(m(QUILAVA, (R,)), opponent_deck=[W, POTION])
        after = attack(kept, 0)
        self.assertEqual(kinds(kept, after, "look_at_card", "deck_top_returned", "discard_from_deck", "shuffle"), ["look_at_card", "deck_top_returned"])
        self.assertEqual((after.players[1].hand[-1], after.players[1].deck[0]), tuple(kept.players[1].deck[:2]))  # 相手が番の始めにもとの一番上を引く
        look = new_events(kept, after, "look_at_card")[0]
        for viewer in (1, None):
            self.assertNotIn("card", visible_log(after, viewer)[after.log.index(look)])
        empty = board(m(QUILAVA, (R,)), opponent_deck=[])
        none = attack(empty, 0)
        self.assertEqual(kinds(empty, none, "look_at_deck_top_none", "look_at_card"), ["look_at_deck_top_none"])
        for s in (done, after, none):
            audited(self, s)


class MagmaRushTest(unittest.TestCase):
    """マグマラッシュ（わるいマグマラシ）・マグマふんしゅつ（カツラのブーバー）: 山札の上から 5 枚をトラッシュし、その中の炎の基本エネルギーカードの枚数 × 20。HC6・FV1。数は先読みで
    すべて試す。"""

    def test_counts_fire_energy_cards_in_the_milled_five(self):
        state = board(m(QUILAVA, (R, R)), opponent=m(H.ONIX, (F,)), deck=[R, W, R, MIRACLE, W, R, R], discard=[R])
        done = attack(state, 1)
        milled = tuple(state.players[0].deck[:5])
        self.assertEqual([e["cards"] for e in new_events(state, done, "discard_from_deck")], [milled])
        self.assertEqual(new_events(state, done, "damage")[0]["steps"][0], ("1 基本となる計算", 40))  # ミラクルエネルギーは場の外では色がない
        self.assertEqual(kinds(state, done, "discard_from_deck", "damage"), ["discard_from_deck", "damage"])
        audited(self, done)

    def test_short_deck_and_rainbow_stop_before_declaration(self):
        rejects(self, board(m(QUILAVA, (R, R)), deck=[R, W, W, W]), UseAttack(0, 1), HC6)
        rejects(self, board(m(QUILAVA, (R, R)), deck=[W] * 8 + [RAINBOW]), UseAttack(0, 1), FV1)  # 一番下のレインボーエネルギーでも止める（上の 5 枚によらない）
        rejects(self, deck_board(m(QUILAVA, (R, R)), [W] * 8, prizes=(RAINBOW,) + (W,) * 5), UseAttack(0, 1), FV1)  # サイドのレインボーエネルギーも
        eruption = board(m("PMCG6-031", (R, R, R)), deck=[W] * 8 + [RAINBOW])
        rejects(self, eruption, UseAttack(0, 1), FV1)  # マグマふんしゅつにも同じに当てはまる（意図した既存の動きの変化）
        self.assertEqual(QUESTIONS["milled_rainbow_energy"].code, FV1)

    def test_acceptance_does_not_depend_on_the_deck_order(self):
        """同じ山札の中身で並びだけが違う 2 つの盤面: 基本となるダメージが 40 のときだけ当たる問いを置くと、上の 5 枚に炎エネルギーがない並びでも止まる。山札とサイドの炎エネルギーが
        1 枚なら 40 にならないので受け付ける。"""
        with question_at_base(40):
            for deck in ([R, R, W, W, W, W, W], [W, W, W, W, W, R, R]):
                with self.subTest(deck=deck):
                    rejects(self, deck_board(m(QUILAVA, (R, R)), deck), UseAttack(0, 1), SC1)
            rejects(self, deck_board(m(QUILAVA, (R, R)), [R] + [W] * 6, prizes=(R,) + (W,) * 5), UseAttack(0, 1), SC1)  # サイドの 1 枚も山札の上にありえた
            audited(self, attack(deck_board(m(QUILAVA, (R, R)), [R] + [W] * 6), 1))
        self.assertEqual(preflight_results(deck_board(m(QUILAVA, (R, R)), [R, R, W, W, W, W, W]), UseAttack(0, 1)), [("siblings", 3)])
        self.assertEqual(preflight_results(deck_board(m(QUILAVA, (R, R)), [W] * 7), UseAttack(0, 1)), [("single", 1)])


class LandslideTest(unittest.TestCase):
    """やまくずし（サイドン）: 10 ダメージ → 山札の上から 5 枚をトラッシュ → その中の闘の基本エネルギーカードを手札に（前からトラッシュにあったカードは加えない）。ポケモンタワーは
    手札に加える部分だけを消す。HC6・FV1（タワーがあれば FV1 に当たらない）。"""

    def test_damage_then_mill_then_return_only_the_milled_fighting_energy(self):
        state = board(m(RHYDON, (F,)), deck=[F, W, F, MIRACLE, W, F, F], discard=[F])
        done = attack(state, 0)
        self.assertEqual(kinds(state, done, "damage", "discard_from_deck", "milled_to_hand"), ["damage", "discard_from_deck", "milled_to_hand"])
        milled = state.players[0].deck[:5]
        (returned,) = new_events(state, done, "milled_to_hand")
        self.assertEqual(returned["cards"], (milled[0], milled[2]))
        self.assertTrue(set(returned["cards"]) <= set(done.players[0].hand))
        self.assertIn(state.players[0].discard[0], done.players[0].discard)
        self.assertEqual(new_events(state, done, "damage")[0]["steps"][0], ("1 基本となる計算", 10))
        audited(self, done)

    def test_tower_suppresses_only_the_return(self):
        state = board(m(RHYDON, (F,)), hand=(TOWER,), deck=[F, W, F, W, W, RAINBOW, F])
        placed = apply_kernel(state, PlayTrainer(0, uid(state, TOWER)))
        done = attack(placed, 0)
        self.assertEqual(kinds(placed, done, "damage", "discard_from_deck", "discard_to_hand_suppressed", "milled_to_hand"),
                         ["damage", "discard_from_deck", "discard_to_hand_suppressed"])
        self.assertFalse(set(placed.players[0].deck[:5]) & set(done.players[0].hand))
        audited(self, done)

    def test_short_deck_and_rainbow(self):
        rejects(self, board(m(RHYDON, (F,)), deck=[F, F]), UseAttack(0, 0), HC6)
        rejects(self, board(m(RHYDON, (F,)), deck=[W] * 6 + [RAINBOW]), UseAttack(0, 0), FV1)


class SnatchTest(unittest.TestCase):
    """とりさる（エイパム）: 相手の場のポケモンについているトレーナーカードを 1 枚選び、相手の山札にもどして切る。進化のもとのなにかの化石・エネルギーは選べない。受けない状態なら
    何もしない（切らない）。選べるカードがなければ、もどさずに切る。はなれられない効果では止めない。"""

    def test_options_cover_active_and_bench_attached_trainers_only(self):
        state = board(m(AIPOM, (W,)), opponent=m(H.OMANYTE, (W,), trainers=[(FOCUS_BAND, None)]), opponent_bench=(m(H.RATTATA, trainers=[(DEFENDER, 7)]), H.RATTATA))
        asked = attack(state, 0)
        expected = (state.players[1].active.trainers[0].card, state.players[1].bench[0].trainers[0].card)
        self.assertEqual((asked.decision.kind, asked.decision.player, asked.decision.options), (SELECT_ATTACHED_TRAINER, 0, expected))
        self.assertNotIn(state.players[1].active.evolution_stack[0], asked.decision.options)  # 進化のもとのなにかの化石（トレーナーカード）はついているトレーナーではない
        done = answer(asked, (expected[1],))
        self.assertEqual([(e["card"], e["pokemon_id"], e["chooser"]) for e in new_events(asked, done, "attached_trainer_to_deck")],
                         [(expected[1], state.players[1].bench[0].pokemon_id, 0)])
        self.assertEqual([e["player"] for e in shuffles(asked, done)], [1])
        self.assertIn(expected[1], done.players[1].deck)
        self.assertEqual(done.players[1].bench[0].trainers, [])
        self.assertEqual(len(done.players[1].active.trainers), 1)
        self.assertEqual([o["card_id"] for o in observe(asked, 0)["decision"]["options"]], [FOCUS_BAND, DEFENDER])
        self.assertEqual(observe(asked, 1)["decision"]["option_count"], 2)
        audited(self, done)

    def test_no_attached_trainer_shuffles_and_effect_guard_prevents(self):
        state = board(m(AIPOM, (W,)))
        done = attack(state, 0)
        self.assertEqual(kinds(state, done, "shuffle", "attached_trainer_to_deck"), ["shuffle"])
        guarded = board(m(AIPOM, (W,)), opponent=m(H.RATTATA, trainers=[(EFFECT_GUARD, 7)]))
        asked = attack(guarded, 0)
        after = answer(asked, asked.decision.options)
        self.assertEqual(kinds(asked, after, "effect_prevented", "attached_trainer_to_deck", "shuffle"), ["effect_prevented"])
        audited(self, done)
        audited(self, after)

    def test_leave_lock_does_not_stop_and_invalid_answers_keep_state(self):
        state = locked(board(m(AIPOM, (W,)), opponent=m(H.RATTATA, trainers=[(DEFENDER, 7)])), 1)
        asked = attack(state, 0)
        before = written(asked)
        for choices in ((), (state.players[1].active.card,), (state.players[0].active.energy[0],)):
            with self.assertRaises(IllegalActionError):
                answer(asked, choices)
        self.assertEqual(written(asked), before)
        for copied in (asked.clone(), copy.deepcopy(asked), pickle.loads(pickle.dumps(asked))):
            done = answer(copied, asked.decision.options)
            self.assertEqual(len(shuffles(asked, done)), 1)
            self.assertEqual(len(new_events(asked, done, "attached_trainer_to_deck")), 1)

    def test_copied_snatch_targets_the_opponent_of_the_copier(self):
        state = board(m(H.CLEFABLE, (W, W, W), evolved_from=H.CLEFAIRY), opponent=m(AIPOM, (W,), trainers=[(DEFENDER, 7)]))
        asked = answer(attack(state, 0), (0,))
        self.assertEqual((asked.decision.kind, asked.decision.options), (SELECT_ATTACHED_TRAINER, (state.players[1].active.trainers[0].card,)))
        audited(self, answer(asked, asked.decision.options))


class ObservationTableTest(unittest.TestCase):
    def test_new_events_and_decisions_are_classified(self):
        for kind in ("attached_trainer_to_deck", "deck_top_returned", "shuffle_declined"):
            self.assertIn(kind, PUBLIC_EVENTS)
        self.assertEqual(OPTION_MEANINGS[SELECT_ATTACHED_TRAINER], "card")
        self.assertNotIn(SELECT_ATTACHED_TRAINER, HIDDEN_COUNT_KINDS)
        self.assertNotIn(OPTIONAL_SHUFFLE, HIDDEN_COUNT_KINDS)
        self.assertEqual(QUESTIONS["attack_deck_top_short"].code, LT1)


class NoCardIdBranchTest(unittest.TestCase):
    def test_engine_and_resolution_have_no_card_id_branches(self):
        for path in [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]:
            text = path.read_text(encoding="utf-8")
            for card in H.V0_95_CARDS:
                with self.subTest(path=path.name, card=card):
                    self.assertNotIn(f'"{card}"', text)


class DocumentTest(unittest.TestCase):
    def test_document_lists_the_cards_rulings_and_counts(self):
        text = DOC.read_text(encoding="utf-8")
        for card in H.V0_95_CARDS:
            self.assertIn(card, text)
        for word in ("1,160", "hidden_choice", "amount_private", "select_attached_trainer", "optional_shuffle", "LT1", "FV1", "PW3", "HC6", "FC1",
                     "rules-2000-02-14.md", "look_at_hand"):
            self.assertIn(word, text)
        self.assertNotIn("v0.95", (ROOT / "CLAUDE.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
