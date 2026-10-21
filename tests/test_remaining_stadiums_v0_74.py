"""v0.74: 拡張パック以外の商品のスタジアム 13 枚（docs/remaining-stadiums-v0.74.md）。

13 枚（4 つの名前・印刷の文面 6 組）: ポケモンタワー（ES3-036）・キョウの忍者ジム（PR1-067）・エネルギースタジアム（NIP1X-009）・ラッキースタジアム（NIP2X-009・PRN-015〜PRN-022・
PRN-027）。どれも kyuura データの採用（採用したデータのコミット 7d3f4ca）で、処理に使う文面は kyuura の印刷の文面。kyuura の日本語の文面は pcg-search.com の転記なので、外部照合は
していない。英語版の文面（PRN-027 の併記を含む）・現代のルール・2003 年以後のスタジアムの使用の制限で、日本語版の条件を補わない。

新しい停止コードは 5: RS1（「自分の番ごとに1回」のスタジアムを、同じ名前の別のカードに入れかわったあとにもう一度使う）・LK1（「自分の番ごとに1回」のない PRN-027 の同じ番の再使用）・
EN1（エネルギースタジアムでトラッシュに基本エネルギーカードがない）・NJ1（キョウの忍者ジムで山札に「キョウのたねポケモン」がない・ベンチに空きがない）・PT1（ポケモンタワーで効果が
すべて消えるトレーナー）。セキチクシティジムの FG1 は、v0.74 から同じ名前の別のカードの使用の記録だけで止める（名前の違うスタジアムの記録では止めない）。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import unittest

from kyuura_engine import (
    EndTurn,
    EvolvePokemon,
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    UseStadium,
    check_invariants,
    observe,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    BENCH_FROM_DECK,
    POST_KNOCKOUT_POWER,
    RETRIEVE_ENERGY,
)
from kyuura_engine.observation import HIDDEN_COUNT_KINDS, PUBLIC_EVENTS
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests.helpers import (
    CHAOS_GYM,
    CLEFAIRY,
    DARK_SLOWBRO,
    ENERGY_RETRIEVAL,
    ENERGY_STADIUM,
    FERVOR,
    FIGHTING,
    FIRE,
    FOSSIL_EXCAVATION,
    FUCHSIA_CITY_GYM,
    GASTLY,
    GRASS,
    HITMONCHAN,
    ITEM_FINDER,
    KOGAS_ARBOK,
    KOGAS_EKANS,
    KOGAS_KOFFING,
    KOGAS_NINJA_GYM,
    LUCKY_STADIUM,
    LUCKY_STADIUM_027,
    LUCKY_STADIUM_NIP2X,
    LUCKY_STADIUM_PRN,
    MAX_REVIVE,
    NIGHTLY_GARBAGE_RUN,
    POKEMON_TOWER,
    PSYCHIC,
    RAINBOW_ENERGY,
    RATTATA,
    RECYCLE,
    ROCKETS_EXPERIMENT,
    ROCKETS_MOLTRES,
    SLOWPOKE,
    SUPER_ENERGY_RETRIEVAL,
    SUPER_SCOOP_UP,
    V0_74_CARDS,
    WATER,
    apply_kernel,
    assert_stop_code_counts_since,
    with_coin_results,
)
from tests.log_audit import observation_problems, serialization_problems
from tests.test_instant_trainers_v0_55 import answer, board, card_of, mon, use

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "remaining-stadiums-v0.74.md"
H, T = CoinSide.HEADS, CoinSide.TAILS
NEW_CODES = {
    "RS1": "UNRESOLVED_STADIUM_REUSE_AFTER_REPLACEMENT",
    "LK1": "UNRESOLVED_LUCKY_STADIUM_UNSTATED_REPEAT",
    "EN1": "UNRESOLVED_ENERGY_STADIUM_WITHOUT_TARGET",
    "NJ1": "UNRESOLVED_NINJA_GYM_WITHOUT_TARGET",
    "PT1": "UNRESOLVED_POKEMON_TOWER_TRAINER_WITHOUT_EFFECT",
}
REUSE, REPEAT, EN1, NJ1, PT1 = NEW_CODES.values()


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def snapshot(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log], repr(state.rng.getstate())


def assert_rejects(test, state, command, code, error=UnsupportedError):
    before = snapshot(state)
    with test.assertRaises(error) as caught:
        apply_kernel(state, command)
    test.assertEqual(caught.exception.code, code)
    test.assertEqual(snapshot(state), before)  # 状態・ログ・乱数・決定は変わらない
    return caught.exception


def placed(stadium, hand=(), **kw):
    """スタジアムを場に出した（プレイヤー 0 の番）盤面。"""
    state = use(board([stadium, *hand], **kw), stadium)
    assert state.stadium is not None and state.decision is None, state.decision
    return state


def stadium_use(state, player=0, *coins):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, UseStadium(player))


def kinds_since(state, kind):
    start = max(i for i, e in enumerate(state.log) if e["kind"] == kind)
    return [e["kind"] for e in state.log[start:]]


def events(state, kind):
    return [e for e in state.log if e["kind"] == kind]


class RegistrationTest(unittest.TestCase):
    def test_registered_and_classified(self):
        """13 枚とも、写しの組 pool_v0_74 にあり、スタジアムだけの種類のトレーナーとして登録した（全文と登録の値を照らす）。"""
        extract = json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text(encoding="utf-8"))
        self.assertEqual(tuple(extract["pool_v0_74"]), V0_74_CARDS)
        pool = load_card_pool()
        for card_id in V0_74_CARDS:
            with self.subTest(card=card_id):
                definition = pool.get(card_id)
                self.assertEqual(definition.trainer_kinds, ("stadium",))
                self.assertIn(card_id, pool.playable_ids)
                self.assertIsNone(E.DEFAULT_EFFECTS.trainer_problem(definition))
                entry = E.DEFAULT_EFFECTS.trainer_entry(card_id)
                self.assertTrue(entry.effect.is_stadium)
                self.assertEqual(entry.effect.check(definition), [])
                self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (definition.trainer_text_ja, definition.trainer_text_ja, "kyuura data/cards.json"))
        types = {card: type(E.DEFAULT_EFFECTS.trainer_entry(card).effect) for card in V0_74_CARDS}
        self.assertEqual(types[POKEMON_TOWER], E.DiscardToHandSuppressionStadium)
        self.assertEqual(types[KOGAS_NINJA_GYM], E.CoinBenchOwnerBasicFromDeckStadium)
        self.assertEqual(types[ENERGY_STADIUM], E.CoinRetrieveBasicEnergyStadium)
        self.assertTrue(all(types[c] is E.CoinDrawStadium for c in (LUCKY_STADIUM_NIP2X, *LUCKY_STADIUM_PRN, LUCKY_STADIUM_027)))

    def test_prn_versions_share_one_registration_and_others_do_not(self):
        """PRN-015〜PRN-022 は同じ文面で、登録の値まで同じなので同じ登録を共有する。NIP2X-009・PRN-027 は文面が違うので、それぞれの登録を保つ。"""
        registry = E.DEFAULT_EFFECTS
        shared = registry.trainer_entry(LUCKY_STADIUM)
        for card in LUCKY_STADIUM_PRN:
            self.assertIs(registry.trainer_entry(card), shared)
        for card in (LUCKY_STADIUM_NIP2X, LUCKY_STADIUM_027):
            self.assertIsNot(registry.trainer_entry(card), shared)
            self.assertNotEqual(registry.trainer_entry(card).text_ja, shared.text_ja)
        self.assertTrue(shared.effect.once_stated)
        self.assertTrue(registry.trainer_entry(LUCKY_STADIUM_NIP2X).effect.once_stated)
        self.assertFalse(registry.trainer_entry(LUCKY_STADIUM_027).effect.once_stated)
        self.assertIn("(During each player's turn", registry.trainer_entry(LUCKY_STADIUM_027).text_ja)  # 英語の併記は原データのまま照らす
        self.assertNotIn("自分の番ごとに1回", registry.trainer_entry(LUCKY_STADIUM_027).text_ja)

    def test_counts_from_the_registry(self):
        """対応するカード 826（ポケモン 585・トレーナー 211・エネルギー 30）、スタジアムの登録 33、ワザ 995・特殊能力 74（v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた。登録から数える。v0.74 は 787・546・917。v0.75 で
        拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた）。"""
        pool = load_card_pool()
        categories = [pool.get(card).category for card in pool.playable_ids]
        self.assertEqual((len(categories), categories.count("pokemon"), categories.count("trainer"), categories.count("energy")), (943, 695, 213, 35))  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた
        registry = E.DEFAULT_EFFECTS
        self.assertEqual(len(registry.trainer_ids()), 213)  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた
        self.assertEqual(sum(1 for c in registry.trainer_ids() if registry.trainer_entry(c).effect.is_stadium), 33)
        self.assertEqual((len(registry.attack_keys()), len(registry.power_keys())), (1182, 74))  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた

    def test_non_pack_unsupported_count(self):
        """kyuura data/engine_targets.json（7d3f4ca）の対象のうち、拡張パック以外の商品で対応していないカードは 228 枚（v0.75 は 252 枚・v0.74 は 267 枚・v0.73 は 280 枚。v0.75 で 15 枚を加えた）。"""
        import subprocess
        raw = subprocess.run(["git", "-C", str(ROOT.parent / "kyuura"), "show", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3:data/engine_targets.json"],
                             capture_output=True, text=True, check=False)
        if raw.returncode != 0:
            self.skipTest("../kyuura がない")
        data = json.loads(raw.stdout)
        targets = data["cards"] if isinstance(data, dict) else data
        pool = load_card_pool()
        self.assertEqual(sum(1 for x in targets if x["product_group"] != "expansion_pack" and x["id"] not in pool.playable_ids), 207)  # v0.79 で拡張パック以外の 16 枚を加えた  # v0.78 で拡張パック以外の 5 枚（イントロパック・プロモ）を加えた（v0.77 までは 228）

    def test_text_and_values_are_checked_together(self):
        """登録の値と印刷の文面を照らす（ほかの版の文面・ちがう値の登録・持ち主の名前は受け付けない）。広い言い回しで受け付けない。"""
        pool = load_card_pool()
        prn = pool.get(LUCKY_STADIUM)
        nip = pool.get(LUCKY_STADIUM_NIP2X)
        p027 = pool.get(LUCKY_STADIUM_027)
        self.assertEqual(E.CoinDrawStadium(E.LUCKY_STADIUM_PRN_TEXT).check(prn), [])
        self.assertTrue(E.CoinDrawStadium(E.LUCKY_STADIUM_PRN_TEXT, once_stated=False).check(prn))  # PRN-015 は「自分の番ごとに1回」がある
        self.assertTrue(E.CoinDrawStadium(E.LUCKY_STADIUM_PRN027_TEXT).check(p027))  # PRN-027 にはない
        self.assertTrue(E.CoinDrawStadium(E.LUCKY_STADIUM_PRN_TEXT).check(nip))  # 版の文面が違う
        self.assertTrue(E.CoinBenchOwnerBasicFromDeckStadium(E.KOGAS_NINJA_GYM_TEXT, owner="サカキ").check(pool.get(KOGAS_NINJA_GYM)))
        self.assertTrue(E.CoinRetrieveBasicEnergyStadium(E.LUCKY_STADIUM_PRN_TEXT).check(prn))
        self.assertTrue(E.DiscardToHandSuppressionStadium(E.FUCHSIA_GYM_TEXT).check(pool.get(POKEMON_TOWER)))
        # 置き方の段落は全文で照らす（英語の併記を除いた PRN-027 の文面・段落の一部だけでは受け付けない）
        for placement in E.STADIUM_PLACEMENT_PARAGRAPHS:
            self.assertTrue(placement.endswith(("。", ")")))
        changed = p027.trainer_text_ja.replace("(This card stays in play after being played. Discard this card if another Stadium card comes into play.)", "")
        self.assertNotEqual(changed, p027.trainer_text_ja)
        self.assertTrue(E.CoinDrawStadium(changed, once_stated=False).check(dataclasses.replace(p027, trainer_text_ja=changed)))

    def test_stop_codes_and_research_links(self):
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        assert_stop_code_counts_since(self, links, 161, 163)  # v0.75 で RB5・DB1 を加えた（その版の数を下限として確かめる）
        text = DOC.read_text(encoding="utf-8")
        for ruling, code in NEW_CODES.items():
            with self.subTest(code=code):
                entry = links["stop_codes"][code]
                self.assertEqual(entry["engine_rulings"], [{"version": "v0.74", "document": "docs/remaining-stadiums-v0.74.md", "ruling_id": ruling}])
                self.assertEqual((entry["kyuura_issue"], entry["kyuura_disposition"]), (None, "not_in_kyuura"))
                self.assertIn(ruling, text)
                self.assertIn(code, text)

    def test_adoption_records(self):
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        for card in V0_74_CARDS:
            with self.subTest(card=card):
                record = sources[card]
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]), ("kyuura_data", "adopted", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3"))
                self.assertEqual((record["play_text"], record["external_checks"]), ({"trainer": "kyuura_printed_text"}, []))
                self.assertNotIn("page", json.dumps(record))

    def test_observation_tables(self):
        for kind in ("discard_to_hand_suppressed", "stadium_retrieve_energy", "stadium_bench_from_deck"):
            self.assertIn(kind, PUBLIC_EVENTS)
        self.assertIn(BENCH_FROM_DECK, HIDDEN_COUNT_KINDS)


class UseCountTest(unittest.TestCase):
    """「自分の番ごとに1回」の回数は (使ったプレイヤー, スタジアムカード) の記録で数え、同じ名前の別のカードを同じ効果の系統として見る。名前の違うスタジアムの使用は数えない。"""

    def test_lucky_heads_draws_and_tails_counts_as_use(self):
        state = placed(LUCKY_STADIUM, deck=[GRASS] * 5)
        hand = len(state.players[0].hand)
        after = stadium_use(state, 0, H)
        self.assertEqual(kinds_since(after, "stadium_used"), ["stadium_used", "coin_flip", "draw"])
        self.assertEqual(len(after.players[0].hand), hand + 1)
        self.assertEqual(events(after, "coin_flip")[-1]["source"], "stadium")  # ワザの説明文のコインではない（ナツメのESPの対象ではない）
        audited(self, after)
        assert_rejects(self, after, UseStadium(0), "STADIUM_ALREADY_USED", IllegalActionError)
        tails = stadium_use(state, 0, T)
        self.assertEqual(kinds_since(tails, "stadium_used"), ["stadium_used", "coin_flip"])
        self.assertEqual(len(tails.players[0].hand), hand)
        assert_rejects(self, tails, UseStadium(0), "STADIUM_ALREADY_USED", IllegalActionError)  # 「うら」でも使ったことになる
        audited(self, tails)

    def test_empty_deck_draws_nothing_and_does_not_lose(self):
        state = placed(LUCKY_STADIUM, deck=[])
        after = stadium_use(state, 0, H)
        self.assertEqual(events(after, "draw")[-1]["cards"], ())
        self.assertIsNone(after.result)
        audited(self, after)

    def test_each_player_on_own_turn_and_next_turn(self):
        """カードの持ち主でないプレイヤーも、自分の番に使える。番が変われば、また使える。番でなければ使えない。"""
        state = placed(LUCKY_STADIUM, deck=[GRASS] * 6, opponent_deck=[GRASS] * 6)
        state = stadium_use(state, 0, T)
        assert_rejects(self, state, UseStadium(1), "NOT_YOUR_TURN", IllegalActionError)
        state = apply_kernel(state, EndTurn(0))
        state = stadium_use(state, 1, H)
        self.assertEqual(state.stadium_uses_this_turn, ((1, state.stadium.card),))
        audited(self, state)
        state = apply_kernel(state, EndTurn(1))
        state = stadium_use(state, 0, H)
        self.assertEqual(state.stadium_uses_this_turn, ((0, state.stadium.card),))
        self.assertEqual(state_to_dict(state, format_version=17)["stadium_uses_this_turn"], [[0, state.stadium.card]])
        audited(self, state)

    def test_energy_choice_is_not_used(self):
        state = placed(LUCKY_STADIUM, deck=[GRASS] * 3)
        assert_rejects(self, state, UseStadium(0, 7), "STADIUM_CHOICE_NOT_USED", IllegalActionError)

    def test_same_name_other_card_stops_and_other_names_do_not(self):
        """同じ名前の別のカードに入れかわったあとの再使用は RS1（コインの前）。名前の違うスタジアムへの入れかえは止めない（ラッキー → セキチク → エネルギー → 忍者）。"""
        state = placed(LUCKY_STADIUM, hand=[LUCKY_STADIUM_PRN[1]], deck=[GRASS] * 5)
        state = stadium_use(state, 0, T)
        state = use(state, LUCKY_STADIUM_PRN[1])
        assert_rejects(self, state, UseStadium(0), REUSE)
        state = placed(LUCKY_STADIUM, hand=[FUCHSIA_CITY_GYM, ENERGY_STADIUM, KOGAS_NINJA_GYM], deck=[GRASS, KOGAS_KOFFING] * 3, discard=[FIRE],
                       bench=(KOGAS_EKANS,))
        state = stadium_use(state, 0, T)
        state = use(state, FUCHSIA_CITY_GYM)
        state = stadium_use(state, 0, T)  # セキチクシティジム（ラッキースタジアムの記録では FG1 にしない。v0.73 まで止めていた）
        state = use(state, ENERGY_STADIUM)
        state = stadium_use(state, 0, T)
        state = use(state, KOGAS_NINJA_GYM)
        state = stadium_use(state, 0, T)
        self.assertEqual(len(state.stadium_uses_this_turn), 4)
        audited(self, state)

    def test_fuchsia_fg1_kept(self):
        """セキチクシティジム A を使ったあと、セキチクシティジム B に入れかわったら FG1 のまま（決めない）。"""
        state = placed(FUCHSIA_CITY_GYM, hand=[FUCHSIA_CITY_GYM], bench=(KOGAS_EKANS,))
        state = stadium_use(state, 0, T)
        state = use(state, FUCHSIA_CITY_GYM)
        assert_rejects(self, state, UseStadium(0), "UNRESOLVED_FUCHSIA_GYM_AFTER_REPLACEMENT")

    def test_trainer_ban_is_stb1(self):
        state = placed(LUCKY_STADIUM, hand=[ROCKETS_EXPERIMENT], deck=[GRASS] * 5)
        state = use(state, ROCKETS_EXPERIMENT, coins=(T,))
        assert_rejects(self, state, UseStadium(0), "UNRESOLVED_STADIUM_ACTIVATION_UNDER_TRAINER_BAN")

    def test_prn027_first_use_and_repeat_boundary(self):
        """PRN-027（日本語に「自分の番ごとに1回」がない）: この番の最初の 1 回は使える。同じ番の再使用は LK1（回数を決めない）。次の番はまた使える。"""
        state = placed(LUCKY_STADIUM_027, deck=[GRASS] * 6, opponent_deck=[GRASS] * 6)
        first = stadium_use(state, 0, H)
        self.assertEqual(kinds_since(first, "stadium_used"), ["stadium_used", "coin_flip", "draw"])
        audited(self, first)
        assert_rejects(self, first, UseStadium(0), REPEAT)
        tails = stadium_use(state, 0, T)
        assert_rejects(self, tails, UseStadium(0), REPEAT)  # 「うら」のあとも同じ
        later = apply_kernel(apply_kernel(first, EndTurn(0)), EndTurn(1))
        audited(self, stadium_use(later, 0, H))

    def test_prn027_after_other_lucky_versions(self):
        """ラッキースタジアム（PRN-015）を使ったあとの PRN-027 は LK1、PRN-027 を使ったあとの PRN-015 は RS1（同じ名前の別のカード）。"""
        state = placed(LUCKY_STADIUM, hand=[LUCKY_STADIUM_027], deck=[GRASS] * 5)
        state = use(stadium_use(state, 0, T), LUCKY_STADIUM_027)
        assert_rejects(self, state, UseStadium(0), REPEAT)
        state = placed(LUCKY_STADIUM_027, hand=[LUCKY_STADIUM_NIP2X], deck=[GRASS] * 5)
        state = use(stadium_use(state, 0, T), LUCKY_STADIUM_NIP2X)
        assert_rejects(self, state, UseStadium(0), REUSE)


class EnergyStadiumTest(unittest.TestCase):
    def test_heads_choose_one_basic_energy_from_own_discard(self):
        """「おもて」: 自分のトラッシュの基本エネルギーカードからちょうど 1 枚（レインボーエネルギー・相手のトラッシュは選べない。同じ名前の別のカードは別のカード）。"""
        state = placed(ENERGY_STADIUM, discard=[FIRE, FIRE, RAINBOW_ENERGY, RATTATA])
        state = stadium_use(state, 0, H)
        d = state.decision
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices), (RETRIEVE_ENERGY, 0, 1, 1))
        self.assertEqual([state.cards[u].card_id for u in d.options], [FIRE, FIRE])
        audited(self, state)
        assert_rejects(self, state, ResolveDecision(1, d.id, (d.options[0],)), "NOT_YOUR_DECISION", IllegalActionError)
        assert_rejects(self, state, ResolveDecision(0, d.id, d.options), "INVALID_CHOICE_COUNT", IllegalActionError)
        assert_rejects(self, state, ResolveDecision(0, d.id, ()), "INVALID_CHOICE_COUNT", IllegalActionError)
        rainbow = next(u for u in state.players[0].discard if state.cards[u].card_id == RAINBOW_ENERGY)
        assert_rejects(self, state, ResolveDecision(0, d.id, (rainbow,)), "INVALID_CHOICE", IllegalActionError)
        coins = len(events(state, "coin_flip"))
        after = answer(state, (d.options[1],))
        self.assertIn(d.options[1], after.players[0].hand)
        self.assertEqual(events(after, "stadium_retrieve_energy")[-1]["card"], d.options[1])
        self.assertEqual(len(events(after, "coin_flip")), coins)  # 答えのあとでコインを投げ直さない
        audited(self, after)

    def test_one_candidate_still_asks(self):
        state = stadium_use(placed(ENERGY_STADIUM, discard=[WATER]), 0, H)
        self.assertEqual(len(state.decision.options), 1)

    def test_tails_and_without_target(self):
        state = placed(ENERGY_STADIUM, discard=[FIRE])
        tails = stadium_use(state, 0, T)
        self.assertIsNone(tails.decision)
        assert_rejects(self, tails, UseStadium(0), "STADIUM_ALREADY_USED", IllegalActionError)
        assert_rejects(self, placed(ENERGY_STADIUM, discard=[RAINBOW_ENERGY, RATTATA]), UseStadium(0), EN1)

    def test_opponent_discard_is_not_used(self):
        state = placed(ENERGY_STADIUM, discard=[FIRE])
        state = apply_kernel(state, EndTurn(0))
        assert_rejects(self, state, UseStadium(1), EN1)  # 相手（プレイヤー 1）のトラッシュには基本エネルギーカードがない

    def test_decision_survives_clone_and_serialization(self):
        state = stadium_use(placed(ENERGY_STADIUM, discard=[FIRE]), 0, H)
        self.assertEqual(state_to_dict(state.clone(), format_version=max(FORMAT_VERSIONS)), state_to_dict(state, format_version=max(FORMAT_VERSIONS)))
        self.assertEqual(state_to_dict(state, format_version=max(FORMAT_VERSIONS))["decision"]["resume"], "stadium")


class NinjaGymTest(unittest.TestCase):
    def test_heads_benches_a_kogas_basic_and_shuffles(self):
        """「おもて」: 山札の「キョウのたねポケモン」から 1 枚（ほかの名前のたねポケモン・キョウの進化カードは選べない）を手札を通さずにベンチへ → 山札を 1 回切る。"""
        state = placed(KOGAS_NINJA_GYM, deck=[KOGAS_KOFFING, RATTATA, KOGAS_ARBOK, GRASS, KOGAS_EKANS])
        state = stadium_use(state, 0, H)
        d = state.decision
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices), (BENCH_FROM_DECK, 0, 1, 1))
        self.assertEqual(sorted(state.cards[u].card_id for u in d.options), sorted([KOGAS_KOFFING, KOGAS_EKANS]))
        for viewer in (1, None):
            seen = observe(state, viewer)["decision"]
            self.assertNotIn("options", seen)  # 選べるものの数は山札の中身を漏らすので、相手に見せない
        audited(self, state)
        assert_rejects(self, state, ResolveDecision(0, d.id, d.options), "INVALID_CHOICE_COUNT", IllegalActionError)
        after = answer(state, (d.options[0],))
        self.assertEqual(kinds_since(after, "stadium_used")[-2:], ["stadium_bench_from_deck", "shuffle"])
        benched = after.players[0].bench[-1]
        self.assertEqual((benched.card, benched.played_turn), (d.options[0], after.turn_number))
        self.assertNotIn(d.options[0], after.players[0].hand)
        audited(self, after)

    def test_benched_pokemon_cannot_evolve_this_turn(self):
        state = placed(KOGAS_NINJA_GYM, hand=[KOGAS_ARBOK], deck=[KOGAS_EKANS, GRASS])
        state = answer(stadium_use(state, 0, H), (card_of(state, KOGAS_EKANS, "deck"),))
        target = state.players[0].bench[-1].pokemon_id
        assert_rejects(self, state, EvolvePokemon(0, card_of(state, KOGAS_ARBOK), target), "PLAYED_THIS_TURN", IllegalActionError)

    def test_tails_does_not_shuffle(self):
        state = stadium_use(placed(KOGAS_NINJA_GYM, deck=[KOGAS_EKANS, GRASS]), 0, T)
        self.assertEqual(kinds_since(state, "stadium_used"), ["stadium_used", "coin_flip"])

    def test_without_target_or_bench_room(self):
        assert_rejects(self, placed(KOGAS_NINJA_GYM, deck=[GRASS, RATTATA, KOGAS_ARBOK]), UseStadium(0), NJ1)
        assert_rejects(self, placed(KOGAS_NINJA_GYM, deck=[]), UseStadium(0), NJ1)
        full = placed(KOGAS_NINJA_GYM, deck=[KOGAS_EKANS], bench=(RATTATA,) * 5)
        assert_rejects(self, full, UseStadium(0), NJ1)  # 印刷の文面に「ベンチに空きがない時、使えない」はない（使えるかが決まらない）


class PokemonTowerTest(unittest.TestCase):
    """ポケモンタワー: お互いの「トラッシュからカードを取り出して手札に加える」効果だけを消す。ほかの部分は残す。"""

    def test_attack_energy_conversion_keeps_self_damage(self):
        """ゴースの「エナジーへんかん」: 手札に加える部分は消え（決定を出さない）、自分への 10 ダメージは残る。先読みの方式で結果は同じ。"""
        results = []
        for preflight in ("derived", "derived_full", "legacy"):
            state = placed(POKEMON_TOWER, active=mon(GASTLY, (PSYCHIC, PSYCHIC)), discard=[FIRE, GRASS])
            after = apply_kernel(state, UseAttack(0, 1), preflight=preflight)
            results.append(snapshot(after))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])
        state = placed(POKEMON_TOWER, active=mon(GASTLY, (PSYCHIC, PSYCHIC)), discard=[FIRE, GRASS])
        after = apply_kernel(state, UseAttack(0, 1))
        suppressed = events(after, "discard_to_hand_suppressed")[-1]
        self.assertEqual((suppressed["player"], suppressed["stadium_card"], suppressed["effect"]), (0, state.stadium.card, f"{GASTLY}#1"))
        self.assertEqual(len(after.players[0].discard), 2)
        self.assertEqual([e["target"] for e in events(after, "damage")][-1:], ["self"])
        audited(self, after)

    def test_rummage_keeps_energy_cost(self):
        """ヤドンの「ゴミあさり」: 超エネルギーのトラッシュ（使うための条件）は残り、トレーナーカードを手札に加える部分だけが消える。"""
        state = placed(POKEMON_TOWER, active=mon(SLOWPOKE, (PSYCHIC, PSYCHIC)), discard=[ENERGY_RETRIEVAL])
        state = apply_kernel(state, UseAttack(0, 1))
        state = answer(state, (state.decision.options[0],))  # トラッシュする超エネルギー
        self.assertIn("discard_energy", [e["kind"] for e in state.log[-8:]])
        self.assertTrue(events(state, "discard_to_hand_suppressed"))
        self.assertNotIn(card_of(state, ENERGY_RETRIEVAL, "discard"), state.players[0].hand)
        audited(self, state)

    def test_copied_attack_and_opponent(self):
        """相手のワザとして使った（ゆびをふる）エナジーへんかんにも、相手プレイヤーのワザにも同じに当てはまる。"""
        state = placed(POKEMON_TOWER, active=mon(CLEFAIRY, (PSYCHIC,) * 3), opponent_active=mon(GASTLY), discard=[FIRE])
        state = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual((state.decision.kind, state.decision.options), ("select_attack", (0, 1)))
        state = answer(state, (1,))  # ゴースのエナジーへんかん
        self.assertEqual(events(state, "discard_to_hand_suppressed")[-1]["player"], 0)
        self.assertIn(FIRE, [state.cards[u].card_id for u in state.players[0].discard])
        audited(self, state)
        mine = placed(POKEMON_TOWER, opponent_active=mon(GASTLY, (PSYCHIC, PSYCHIC)))
        mine = apply_kernel(mine, EndTurn(0))
        after = apply_kernel(mine, UseAttack(1, 1))  # 相手プレイヤー（ポケモンタワーの持ち主でない）のワザにも同じに当てはまる
        self.assertEqual(events(after, "discard_to_hand_suppressed")[-1]["player"], 1)
        audited(self, after)

    def test_trainers_whose_whole_effect_vanishes_stop_before_use(self):
        """効果がすべて消えるトレーナー（エネルギー回収・再録・超エネルギー回収・ダウジングマシーン）は PT1（手札から出す前。使うための条件の確かめのあと）。"""
        for card in (ENERGY_RETRIEVAL, "GD1-014", SUPER_ENERGY_RETRIEVAL, ITEM_FINDER):
            with self.subTest(card=card):
                state = placed(POKEMON_TOWER, hand=[card, GRASS, GRASS], discard=[FIRE, ENERGY_RETRIEVAL])
                assert_rejects(self, state, PlayTrainer(0, card_of(state, card)), PT1)
        short = placed(POKEMON_TOWER, hand=[ENERGY_RETRIEVAL], discard=[FIRE])
        assert_rejects(self, short, PlayTrainer(0, card_of(short, ENERGY_RETRIEVAL)), "INSUFFICIENT_CARDS_IN_HAND", IllegalActionError)

    def test_fervor_discards_and_skips_fv1(self):
        """熱血!: 上 3 枚のトラッシュは残り、「炎」を手札に加える部分だけが消える（山札・サイドのレインボーエネルギーで FV1 にしない）。山札 3 枚未満は HC6 のまま。"""
        state = placed(POKEMON_TOWER, hand=[FERVOR], deck=[FIRE, RAINBOW_ENERGY, FIRE, GRASS])
        hand = len(state.players[0].hand)
        after = use(state, FERVOR)
        self.assertEqual(len(after.players[0].deck), 1)
        self.assertEqual(len(after.players[0].hand), hand - 1)
        self.assertEqual(kinds_since(after, "play_trainer"), ["play_trainer", "deck_top_to_discard", "discard_to_hand_suppressed", "discard_trainer"])
        audited(self, after)
        short = placed(POKEMON_TOWER, hand=[FERVOR], deck=[FIRE, FIRE])
        assert_rejects(self, short, PlayTrainer(0, card_of(short, FERVOR)), "UNRESOLVED_DISCARD_DECK_SHORT")
        plain = board([FERVOR], deck=[FIRE, RAINBOW_ENERGY, FIRE, GRASS])
        assert_rejects(self, plain, PlayTrainer(0, card_of(plain, FERVOR)), "UNRESOLVED_FERVOR_RAINBOW_ENERGY")  # タワーのない場面の FV1 は変えない

    def test_fossil_excavation_keeps_deck_branch(self):
        state = placed(POKEMON_TOWER, hand=[FOSSIL_EXCAVATION], deck=["PMCG3-046", GRASS], discard=["PMCG3-046"])
        state = use(state, FOSSIL_EXCAVATION)
        self.assertEqual(state.decision.options, (card_of(state, "PMCG3-046", "deck"),))
        trashed = card_of(state, "PMCG3-046", "discard")
        assert_rejects(self, state, ResolveDecision(0, state.decision.id, (trashed,)), "INVALID_CHOICE", IllegalActionError)
        after = answer(state, ())
        self.assertEqual(kinds_since(after, "play_trainer")[-3:], ["trainer_take_none", "shuffle", "discard_trainer"])
        audited(self, after)

    def test_other_destinations_are_not_suppressed(self):
        """場 → 手札（スーパーポケモン回収）・トラッシュ → ベンチ（元気のかたまり）・トラッシュ → 山札（夜の廃品回収・リサイクル）は消さない。"""
        state = placed(POKEMON_TOWER, hand=[SUPER_SCOOP_UP])
        state = use(state, SUPER_SCOOP_UP, coins=(H,))
        state = answer(state, (state.players[0].bench[0].pokemon_id,))
        self.assertIn(RATTATA, [state.cards[u].card_id for u in state.players[0].hand])
        state = placed(POKEMON_TOWER, hand=[MAX_REVIVE, FIRE, WATER], discard=[RATTATA])
        state = use(state, MAX_REVIVE)
        state = answer(state, tuple(u for u in state.decision.options if state.cards[u].card_id in (FIRE, WATER)))
        state = answer(state, (state.decision.options[0],))
        self.assertEqual(state.cards[state.players[0].bench[-1].card].card_id, RATTATA)
        state = placed(POKEMON_TOWER, hand=[NIGHTLY_GARBAGE_RUN], discard=[RATTATA])
        state = answer(use(state, NIGHTLY_GARBAGE_RUN), (card_of(state, RATTATA, "discard"),))
        self.assertIn(card_of(state, RATTATA, "deck"), state.players[0].deck)
        state = placed(POKEMON_TOWER, hand=[RECYCLE], discard=[FIRE])
        state = answer(use(state, RECYCLE, coins=(H,)), (card_of(state, FIRE, "discard"),))
        self.assertEqual(state.cards[state.players[0].deck[0]].card_id, FIRE)
        self.assertFalse(events(state, "discard_to_hand_suppressed"))

    def test_phoenix_is_not_offered(self):
        """ふしちょう（トラッシュから手札に加える。CR-PHOENIX-RETURN）: 効果が消えるので使う機会を出さない。きぜつ・トラッシュ・サイドはそのまま。"""
        state = placed(POKEMON_TOWER, active=mon(HITMONCHAN, (FIGHTING, FIGHTING, FIGHTING)), opponent_active=mon(ROCKETS_MOLTRES, damage=50), opponent_bench=(RATTATA,))
        state = apply_kernel(state, UseAttack(0, 1))
        while state.decision is not None and state.decision.kind != POST_KNOCKOUT_POWER and state.decision.kind in ("take_prize", "promote_active"):
            state = answer(state, (state.decision.options[0],))
        self.assertTrue(state.decision is None or state.decision.kind != POST_KNOCKOUT_POWER)
        moltres = next(u for u in state.players[1].discard if state.cards[u].card_id == ROCKETS_MOLTRES)
        self.assertIn(moltres, state.players[1].discard)
        self.assertEqual(events(state, "discard_to_hand_suppressed")[-1]["power"], f"{ROCKETS_MOLTRES}@power0")
        self.assertEqual(len(events(state, "take_prize")), 1)
        audited(self, state)
        normal = board([], active=mon(HITMONCHAN, (FIGHTING, FIGHTING, FIGHTING)), opponent_active=mon(ROCKETS_MOLTRES, damage=50), opponent_bench=(RATTATA,))
        normal = apply_kernel(normal, UseAttack(0, 1))
        while normal.decision is not None and normal.decision.kind == "take_prize":
            normal = answer(normal, (normal.decision.options[0],))
        self.assertEqual(normal.decision.kind, POST_KNOCKOUT_POWER)

    def test_entry_power_reel_in_is_not_offered(self):
        state = placed(POKEMON_TOWER, hand=[DARK_SLOWBRO], active=mon(SLOWPOKE, played_turn=1), discard=[RATTATA])
        after = apply_kernel(state, EvolvePokemon(0, card_of(state, DARK_SLOWBRO), state.players[0].active.pokemon_id))
        self.assertIsNone(after.decision)
        self.assertEqual(events(after, "discard_to_hand_suppressed")[-1]["power"], f"{DARK_SLOWBRO}@power0")
        audited(self, after)
        normal = board([DARK_SLOWBRO], active=mon(SLOWPOKE, played_turn=1), discard=[RATTATA])
        normal = apply_kernel(normal, EvolvePokemon(0, card_of(normal, DARK_SLOWBRO), normal.players[0].active.pokemon_id))
        self.assertEqual(normal.decision.kind, "entry_power")

    def test_replacing_the_tower_restores_effects(self):
        """ポケモンタワーが場をはなれたら（別のスタジアムに入れかわった）、通常の効果にもどる（印を状態に残さない）。そのあとエネルギースタジアムを使える。"""
        state = placed(POKEMON_TOWER, hand=[ENERGY_STADIUM, ENERGY_RETRIEVAL, GRASS], discard=[FIRE])
        state = use(state, ENERGY_STADIUM)
        self.assertIsNone(E.discard_to_hand_suppressor(state))
        state = stadium_use(state, 0, H)
        state = answer(state, (state.decision.options[0],))
        self.assertIn(FIRE, [state.cards[u].card_id for u in state.players[0].hand])
        audited(self, state)
        state = placed(POKEMON_TOWER, hand=[CHAOS_GYM, ENERGY_RETRIEVAL, GRASS], discard=[FIRE])
        state = use(state, CHAOS_GYM)
        state = use(state, ENERGY_RETRIEVAL, coins=(H,))
        self.assertEqual(state.decision.kind, "discard_from_hand")
