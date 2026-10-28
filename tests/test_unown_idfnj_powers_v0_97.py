"""v0.97（docs/unown-research-idfnj-v0.97.md 4 章〜）: アンノーンI・D・F・[N]・[J] の 5 枚（ワザ 5・特殊能力 5）。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面・ルール文。I・D・F のルール文は kyuura がカードの画像で埋めた訂正）と、kyuura の裁定
（CR-UNOWN-DECK-LIMIT-ALL-LETTERS・CR-UNOWN-DF-PROTECTS-OWN-UNOWN・CR-UNOWN-DF-SOURCE-TYPE・CR-UNOWN-DF-AT-MOST-ONE・CR-UNOWN-DF-DAMAGE-STEP）・既存の規定と読み方の記録
（v0.43 の PW3・v0.60 の SS1・v0.79 の比べ方・v0.89 の FA1・v0.92 のヤミカラスの型・v0.96 の名前のグループ）。英語版の文面・現代のルール・後年の裁定は持ち込まない。
公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの
自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.97``）。
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
    PlayBasicToBench,
    PlayTrainer,
    PowerKey,
    ResolveDecision,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.damage import DamageModifier, calculate_attack_damage
from kyuura_engine.decisions import BENCH_FROM_DECK, ENTRY_POWER, SEARCH_DECK
from kyuura_engine.deck import deck_problems
from kyuura_engine.errors import HiddenPropertyRead, IllegalActionError
from kyuura_engine.observation import observe
from kyuura_engine.resolution import questions
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import PowersStopped
from tests import helpers as H
from tests.helpers import apply_kernel, build_test_state, with_coin_results
from tests.release_catalog import cards_after, cards_before
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_power_suppression_lasting_locks_v0_92 import DK, MURKROW, mon, uid
from tests.test_unown_family_powers_v0_96 import answer, board, deck_of, kinds

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "unown-research-idfnj-v0.97.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, PS, F, G = H.WATER, H.PSYCHIC, H.FIRE, H.GRASS
UI, UD, UF, UN, UJ = "neo2-023", "neo2-025", "neo2-026", "PF2-001", "PRN-034"
UE, UO, UR, UL, UZ = H.UNOWN_E, H.UNOWN_O, H.UNOWN_R, H.UNOWN_L, H.UNOWN_Z
V097 = (UI, UD, UF, UN, UJ)
V097_ATTACKS = [AttackKey(c, 0) for c in V097]
V097_POWERS = [PowerKey(c, 0) for c in V097]
PW3, FD1, GG1 = "UNRESOLVED_POWER_ZERO_CARDS", "UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY", "UNRESOLVED_GOOP_GAS_NEW_POKEMON"
DF1, DF2, SS1, FA1 = ("UNRESOLVED_SELF_EXCLUDING_POWER_COPIES", "UNRESOLVED_POWER_DAMAGE_RECEIVED_POWER", "UNRESOLVED_SPEED_STAR_SCOPE",
                      "UNRESOLVED_IGNORED_EFFECTS_SCOPE")
RULE_TEXT = "「アンノーン」はデッキに4枚までしか入れることができません。"
UMBREON, DARK_DRAGONAIR, ROCKETS_SNORLAX, PIDGEOTTO = H.UMBREON_NEO2, "PMCG4-052", H.ROCKETS_SNORLAX, H.PIDGEOTTO
CYNDAQUIL_PF1, METAL_NIP, SCOPE_LENS, FOSSIL, DOLL = H.CYNDAQUIL_PF1, "NIP1X-010", "neo4-104", H.MYSTERIOUS_FOSSIL, H.CLEFAIRY_DOLL
TURN = 7


def umbreon(energy=(W, W), **extra):
    return mon(UMBREON, energy, played_turn=1, evolved_from=H.EEVEE, evolved_turn=3, **extra)


def declare(state, index, *coins, player=None):
    player = state.current_player if player is None else player
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UseAttack(player, index))


def power(state, pokemon_id, player=0):
    return apply_kernel(state, UsePokemonPower(player, pokemon_id, 0))


def hits(before, after):
    """ダメージのログの (受けたポケモンの番号（相手の対戦ポケモンは None）, 量, 最後の段階)。"""
    return [(e.get("pokemon_id"), e["amount"], e["steps"][-1][0]) for e in new_events(before, after, "damage")]


def ids(state, player):
    return [p.pokemon_id for p in state.players[player].in_play()]


def snap(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log], repr(state.rng.getstate())


def same_answers(test, state, choices):
    """待っている決定のある状態を clone・deepcopy・pickle しても、同じ答えで同じ結果になる（見せる・加える・切る・出すを二重にしない）。"""
    expected = answer(state, choices)
    for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
        test.assertEqual(snap(answer(other, choices)), snap(expected))
    return expected


def stop(state, pokemon):
    """``pokemon``（相手のバトル場のポケモン）の特殊能力を止める（わるいモココの「スタンウェーブ」の効果。そのポケモンだけ。ログとともに与える）。"""
    from kyuura_engine.persistent import add_persistent_effect

    add_persistent_effect(state, 1, pokemon, PowersStopped(state.players[0].active.card, 0, TURN, TURN + 2), attack="neo4-044#1")
    return state


# ---------------------------------------------------------------- 1〜3 章: 対象・登録・文面・デッキの規定


class RegistrationTest(unittest.TestCase):
    def test_every_attack_and_power_is_registered_with_the_printed_text(self):
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_97"]), V097)
        for key in V097_ATTACKS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
                printed = pool.definitions[key.card_id].attacks[0]
                self.assertIs(entry.effect, E.DAMAGE_ONLY)
                self.assertEqual((entry.name_ja, printed.name_ja, printed.text_ja, entry.text_ja, printed.damage, tuple(t.value for t in printed.cost)),
                                 ("めざめるパワー", "めざめるパワー", None, None, 10, ("psychic",)))
        for key in V097_POWERS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.power_entry(key.card_id, key.power_index)
                printed = pool.definitions[key.card_id].powers[0]
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (printed.name_ja, printed.text_ja, printed.text_ja,
                                                                                                   "kyuura data/cards.json"))
                self.assertEqual(entry.effect.check(printed), [])
        for card in V097:
            definition = pool.definitions[card]
            self.assertIn(card, pool.playable_ids)
            self.assertEqual((definition.stage, definition.hp, definition.pokemon_type, definition.weakness, definition.resistance, definition.retreat_cost),
                             ("basic", 40, E.EnergyType.PSYCHIC, E.EnergyType.PSYCHIC, None, 1))
            self.assertEqual((definition.name_group, definition.deck_group_limit), ("アンノーン", 4))
        self.assertEqual({c: pool.definitions[c].name_letter for c in V097}, {UI: "I", UD: "D", UF: "F", UN: "N", UJ: "J"})

    def test_types(self):
        def effect(card):
            return DEFAULT_EFFECTS.power_entry(card, 0).effect

        self.assertEqual(effect(UI), E.BenchNameGroupFromDeckOnEntry("アンノーン"))
        self.assertTrue(isinstance(effect(UI), E.EntryPower) and effect(UI).from_hand_only)
        self.assertEqual((effect(UF).letters, effect(UF).target), (("I", "N", "D"), E.CardFilter("trainer")))
        # v0.114: ［JOIN］の説明は「ベイビィポケモン」と並べて書くので、ベイビィポケモンカードもふくむ（docs/baby-rules-evolution-v0.114.md 5.4 節）
        self.assertEqual((effect(UJ).letters, effect(UJ).target), (("O", "I", "N"), E.CardFilter("pokemon", babies=E.BABY_NAMED)))
        self.assertTrue(type(effect(UF)).once_per_turn and type(effect(UJ)).once_per_turn)
        self.assertEqual((effect(UD).attacker_type, effect(UD).letter, effect(UD).amount), (E.EnergyType.DARKNESS, "D", 30))
        self.assertEqual((effect(UN).attacker_type, effect(UN).letter, effect(UN).amount), (E.EnergyType.COLORLESS, "N", 30))
        for card in (UD, UN):
            self.assertTrue(type(effect(card)).self_excluding)
            self.assertFalse(effect(card).declared)
            self.assertFalse(effect(card).blocked_by_status)  # 日本語の文面に特殊状態の条件はない

    def test_unregistered_without_the_v0_97_entries(self):
        """今回の登録を除くと対戦に使えなくなるのは、ちょうど 5 枚。過去の範囲は ``cards_before``・``cards_after`` で切り出す。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V097_ATTACKS)
        registry = registry.without_powers(registry.id, V097_POWERS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V097))
        self.assertEqual(set(V097) & set(cards_before(read_extract(), "0.97")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.96")) & set(cards_before(read_extract(), "0.98")), set(V097))

    def test_extract_values_and_rule_text_corrections(self):
        """I・D・F のルール文は kyuura がカードの画像で埋めた値（写しの元 73a1690。写しで当てはめ直していない）。[N]・[J] のレベルは kyuura のデータで空のまま（補わない）。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        for card in V097:
            with self.subTest(card=card):
                self.assertEqual(cards[card]["pokemon"]["rules_text"]["ja"], RULE_TEXT)
        for card, fix in (("neo2-023", "FIX-neo2-023-RULES-TEXT-JA"), ("neo2-025", "FIX-neo2-025-RULES-TEXT-JA"), ("neo2-026", "FIX-neo2-026-RULES-TEXT-JA")):
            self.assertEqual([x["id"] for x in cards[card]["corrections"]], [fix])
            self.assertNotIn("pokemon.rules_text.ja", cards[card]["data_gaps"])
        self.assertEqual({c: cards[c]["jp_print"]["level"] for c in V097}, {UI: 10, UD: 14, UF: 16, UN: None, UJ: None})
        self.assertNotIn("corrections", cards[UN])
        self.assertIn("Unown Dragon", cards[UJ]["pokemon"]["powers"][0]["text"]["en"])  # kyuura が直していない英語の名前（日本語の処理には使わない）

    def test_adoption_records_and_research_links(self):
        data = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        expected = {UI: {"CR-UNOWN-DECK-LIMIT-ALL-LETTERS", "UQ-CARD-USE-WITHOUT-TARGET"}, UF: {"CR-UNOWN-DECK-LIMIT-ALL-LETTERS", "UQ-CARD-USE-WITHOUT-TARGET"},
                    UJ: {"CR-UNOWN-DECK-LIMIT-ALL-LETTERS", "UQ-CARD-USE-WITHOUT-TARGET"}}
        df = {"CR-UNOWN-DECK-LIMIT-ALL-LETTERS", "CR-UNOWN-DF-AT-MOST-ONE", "CR-UNOWN-DF-DAMAGE-STEP", "CR-UNOWN-DF-PROTECTS-OWN-UNOWN", "CR-UNOWN-DF-SOURCE-TYPE",
              "UQ-SELF-EXCLUDING-POWER-COPIES"}
        expected[UD] = df
        expected[UN] = df | {"UQ-NON-ATTACK-DAMAGE-MODIFIERS", "UQ-SPEED-STAR-SCOPE"}
        for card in V097:
            with self.subTest(card=card):
                record = data[card]
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["recorded_on"], record["external_checks"], record["issues"]),
                                 ("kyuura_data", "adopted", "73a169063463bbf7bcaa3137d70cbf9721d11534", "2026-10-25", [], []))
                self.assertEqual(set(record["kyuura_records"]), expected[card])
                self.assertEqual(record["play_text"], {"power/0": "kyuura_printed_text"})
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        self.assertEqual([k for k in links["latest_descriptions"]["adopted_printed_text"] if k.split("/")[0] in V097], [f"{c}/power/0" for c in V097])
        codes = links["stop_codes"]
        self.assertEqual((codes[DF1]["kyuura_issue"], codes[DF1]["kyuura_disposition"]), ("UQ-SELF-EXCLUDING-POWER-COPIES", "issue_not_in_index"))
        self.assertEqual((codes[DF2]["kyuura_issue"], codes[DF2]["kyuura_disposition"]), ("UQ-NON-ATTACK-DAMAGE-MODIFIERS", "issue_not_in_index"))
        self.assertEqual((codes[SS1]["kyuura_issue"], codes[SS1]["kyuura_disposition"], codes[SS1]["kyuura_index_engine_key"]), ("UQ-SPEED-STAR-SCOPE", "issue", "SS1"))
        self.assertNotIn("speed_star_scope", links["codeless_questions"])
        # 停止コード・未解決の裁定の今の総数は tests/test_catalog_contract.py（v0.98 で、版ごとのテストに重ねていた今の総数の確かめを外した）
        cases = {(c["kyuura_issue"], c["card_id"]): c for c in links["kyuura_cases_without_engine_ruling"]["cases"]}
        for card in (UI, UF, UJ):  # 候補なしは v0.43 の PW3 を使う（kyuura の一覧では PW3 は UQ-UP-TO-ZERO-CHOICE。kyuura への報告事項）
            self.assertEqual((cases[("UQ-CARD-USE-WITHOUT-TARGET", card)]["engine"], cases[("UQ-CARD-USE-WITHOUT-TARGET", card)]["engine_issue_differs"]),
                             ({"stop_codes": [PW3]}, True))
        self.assertEqual(cases[("UQ-SPEED-STAR-SCOPE", PIDGEOTTO)]["engine"], {"stop_codes": [SS1]})

    def test_questions_table(self):
        self.assertEqual((questions.QUESTIONS["speed_star_scope"].code, questions.QUESTIONS["speed_star_scope"].rulings), (SS1, ("SS1",)))
        self.assertEqual((questions.QUESTIONS["self_excluding_power_copies"].code, questions.QUESTIONS["self_excluding_power_copies"].rulings), (DF1, ("DF1",)))


class DeckLimitTest(unittest.TestCase):
    """CR-UNOWN-DECK-LIMIT-ALL-LETTERS: 文字・商品にかかわらず、デッキのアンノーンは合わせて 4 枚まで（訂正したルール文を持つ I・D・F だけでも同じ）。"""

    def test_mixed_letters(self):
        self.assertEqual(deck_problems(deck_of(UI, UD, UF, UI, H.RATTATA)), [])  # I・D・F だけの 4 枚
        five = deck_problems(deck_of(UI, UD, UF, UI, UD, H.RATTATA))
        self.assertEqual([p for p in five if p.startswith("TOO_MANY")], ["TOO_MANY_GROUP_COPIES: 「アンノーン」のカードが合わせて 5 枚（カードのルール文で、デッキに 4 枚まで）"])
        self.assertEqual(deck_problems(deck_of(UF, UI, UN, UD, H.RATTATA)), [])  # ［FIND］の 4 文字
        self.assertEqual(deck_problems(deck_of(UJ, UO, UI, UN, H.RATTATA)), [])  # ［JOIN］の 4 文字
        self.assertTrue(any(p.startswith("TOO_MANY_GROUP_COPIES") for p in deck_problems(deck_of(UF, UI, UN, UD, UJ))))
        self.assertTrue(any(p.startswith("TOO_MANY_GROUP_COPIES") for p in deck_problems(deck_of(UI, UD, UE, UO, UZ))))  # v0.96 の文字と合わせる

    def test_same_name_and_shining_limits_are_kept(self):
        same = deck_problems(deck_of(*([UI] * 5), H.RATTATA))
        self.assertIn("TOO_MANY_COPIES: 「アンノーンI」が 5 枚（同じ名前は 4 枚まで）", same)
        self.assertIn("TOO_MANY_COPIES: 「ひかるリザードン」が 2 枚（カードのルール文で、デッキに 1 枚まで）", deck_problems(deck_of("neo4-025", "neo4-025", UI)))
        self.assertEqual(deck_problems(deck_of(*([H.RATTATA] * 4), UI, UD, UF, UN)), [])


# ---------------------------------------------------------------- 4 章: ［INCREASE］


def play_i(state, player=0):
    return apply_kernel(state, PlayBasicToBench(player, uid(state, UI, player)))


class IncreaseTest(unittest.TestCase):
    def test_from_hand_benches_one_unown_from_the_deck_and_shuffles(self):
        state = board(mon(H.RATTATA), bench=(), hand=(UI,), deck=[UF, W, UN, W, W])
        offered = play_i(state)
        self.assertEqual((offered.decision.kind, offered.decision.min_choices, offered.decision.max_choices), (ENTRY_POWER, 0, 1))
        self.assertEqual(offered.decision.context_value("unresolved_choices", ()), ())
        used = answer(offered, offered.decision.options)
        self.assertEqual((used.decision.kind, used.decision.min_choices, used.decision.max_choices), (BENCH_FROM_DECK, 1, 1))
        self.assertEqual(sorted(used.cards[o].card_id for o in used.decision.options), sorted([UF, UN]))
        target = next(o for o in used.decision.options if used.cards[o].card_id == UN)
        done = same_answers(self, used, (target,))
        self.assertEqual([done.cards[p.card].card_id for p in done.players[0].bench], [UI, UN])
        self.assertEqual(kinds(used, done), ["bench_from_deck", "shuffle"])
        self.assertIsNone(done.decision)  # 山札から出したアンノーンには「手札から場に出したとき」の機会がない
        audited(self, done)

    def test_placed_from_the_deck_has_no_from_hand_opportunity(self):
        """山札から出した I・E・R には、手札から場に出したときの特殊能力の機会がない（v0.96 の遺跡の石版と同じ）。"""
        for card in (UI, UE, UR):
            with self.subTest(card=card):
                state = board(mon(H.RATTATA), bench=(), hand=(UI,), deck=[card, W, W])
                used = answer(play_i(state), play_i(state).decision.options)
                done = answer(used, used.decision.options)
                self.assertIsNone(done.decision)
                self.assertEqual(new_events(used, done, "pokemon_power"), [])

    def test_full_bench_after_playing_this_card_offers_nothing(self):
        """このカードを出してベンチがいっぱいになったら、この力は使えない（機会を出さない）。出すこと自体は拒否しない。"""
        state = board(mon(H.RATTATA), bench=(H.RATTATA,) * 4, hand=(UI,), deck=[UF, W, W])
        done = play_i(state)
        self.assertIsNone(done.decision)
        self.assertEqual(len(done.players[0].bench), 5)
        self.assertEqual(new_events(state, done, "pokemon_power"), [])
        audited(self, done)
        roomy = play_i(board(mon(H.RATTATA), bench=(H.RATTATA,) * 3, hand=(UI,), deck=[UF, W, W]))
        self.assertEqual(roomy.decision.kind, ENTRY_POWER)  # 空きが 1 つ残る（ちょうど最後の枠）

    def test_no_unown_in_deck_is_pw3_without_leaking_the_deck(self):
        """山札に「アンノーン」がない（山札 0 枚を含む）: 使うを選ぶと PW3（kyuura の UQ-CARD-USE-WITHOUT-TARGET の事例）。使わないは選べる。機会の決定の形は山札の中身で変わらず、
        相手・観戦者の見える決定も同じ。"""
        with_unown = play_i(board(mon(H.RATTATA), bench=(), hand=(UI,), deck=[UF, W, W]))
        for deck in ([W, W, W], []):
            with self.subTest(deck=len(deck)):
                offered = play_i(board(mon(H.RATTATA), bench=(), hand=(UI,), deck=deck))
                self.assertEqual((offered.decision.kind, offered.decision.options, offered.decision.min_choices, offered.decision.max_choices),
                                 (with_unown.decision.kind, with_unown.decision.options, with_unown.decision.min_choices, with_unown.decision.max_choices))
                self.assertEqual(offered.decision.context_value("unresolved_code"), PW3)
                rejects(self, offered, ResolveDecision(0, offered.decision.id, offered.decision.options), PW3)
                for viewer in (1, None):
                    self.assertEqual(observe(offered, viewer)["decision"], observe(with_unown, viewer)["decision"])
                declined = answer(offered, ())
                self.assertIsNone(declined.decision)
                self.assertEqual(new_events(offered, declined, "shuffle"), [])
                audited(self, declined)

    def test_suppressed_power_has_no_opportunity(self):
        gas = board(mon(H.RATTATA), bench=(), hand=(UI,), deck=[UF, W], opponent=mon(H.MUK, evolved_from=H.GRIMER))
        self.assertIsNone(play_i(gas).decision)

    def test_bench_entry_stops_are_kept(self):
        """まきちらせ!ベトベトガスのはたらく間、特殊能力を持つカードを場に出すと止まる（GG1）。このカード自身も止まるので、使う機会のあとにガスが来たときの確かめ（``accept_problem``）
        で、山札のアンノーンがどれも出すと止めるカードなら使うを選ぶと止めることを確かめる（v0.96 の遺跡の石版と同じ）。"""
        state = board(mon(H.RATTATA), bench=(), hand=(UI, H.GOOP_GAS_ATTACK), deck=[UF, W, W])
        rejects(self, apply_kernel(state, PlayTrainer(0, uid(state, H.GOOP_GAS_ATTACK))), PlayBasicToBench(0, uid(state, UI)), GG1)
        declined = answer(play_i(state), ())
        gas = apply_kernel(declined, PlayTrainer(0, uid(declined, H.GOOP_GAS_ATTACK)))
        use = E.PowerUse(0, gas.players[0].bench[0].pokemon_id, PowerKey(UI, 0))
        self.assertEqual(E.BenchNameGroupFromDeckOnEntry().accept_problem(gas, use).code, GG1)

    def test_erikas_perfume_offers_the_owner(self):
        """エリカの香水（相手の手札のたねポケモンを相手のベンチに出させる）で手札から出た I: 持ち主（相手）に機会があり、持ち主の山札から出す（既存の経路）。"""
        state = board(mon(H.RATTATA), hand=(H.ERIKAS_PERFUME, W), opponent_hand=(UI, W, W), opponent_deck=[UN, W, W, W])
        step = apply_kernel(state, PlayTrainer(0, uid(state, H.ERIKAS_PERFUME)))
        while step.decision is not None and step.decision.kind != ENTRY_POWER:
            step = answer(step, step.decision.options[:1])
        self.assertEqual((step.decision.kind, step.decision.player), (ENTRY_POWER, 1))
        used = answer(step, step.decision.options)
        self.assertEqual((used.decision.kind, used.decision.player, [used.cards[o].card_id for o in used.decision.options]), (BENCH_FROM_DECK, 1, [UN]))
        done = answer(used, used.decision.options)
        self.assertEqual([done.cards[p.card].card_id for p in done.players[1].bench][-2:], [UI, UN])
        self.assertEqual((done.current_player, done.trainer_in_use), (0, None))
        audited(self, done)

    def test_invalid_answers_change_nothing(self):
        state = board(mon(H.RATTATA), bench=(), hand=(UI,), deck=[UF, W, W])
        used = answer(play_i(state), play_i(state).decision.options)
        wrong = next(u for u in used.players[0].deck if used.cards[u].card_id == W)
        rejects(self, used, ResolveDecision(0, used.decision.id, (wrong,)), "INVALID_CHOICE", error=IllegalActionError)
        rejects(self, used, ResolveDecision(0, used.decision.id, ()), "INVALID_CHOICE_COUNT", error=IllegalActionError)
        rejects(self, used, ResolveDecision(1, used.decision.id, used.decision.options), "NOT_YOUR_DECISION", error=IllegalActionError)


# ---------------------------------------------------------------- 5 章: ［FIND］・［JOIN］


class FindJoinTest(unittest.TestCase):
    def find_board(self, deck, bench=None, **kw):
        return board(mon(H.RATTATA), bench=bench if bench is not None else (mon(UF), mon(UI), mon(UN), mon(UD)), deck=deck, **kw)

    def test_find_reveals_any_trainer_and_shuffles(self):
        deck = [H.POTION, H.BILL, FOSSIL, DOLL, "neo1-085", "neo1-073", W, H.RATTATA]  # スタジアム（マダツボミのとう）・どうぐ（きのみ）・なにかの化石・ピッピ人形も
        state = self.find_board(deck)
        used = power(state, state.players[0].bench[0].pokemon_id)
        self.assertEqual((used.decision.kind, used.decision.min_choices, used.decision.max_choices), (SEARCH_DECK, 1, 1))
        self.assertEqual(sorted(used.cards[o].card_id for o in used.decision.options), sorted([H.POTION, H.BILL, FOSSIL, DOLL, "neo1-085", "neo1-073"]))
        target = next(o for o in used.decision.options if used.cards[o].card_id == FOSSIL)
        done = same_answers(self, used, (target,))
        self.assertIn(target, done.players[0].hand)
        revealed = new_events(used, done, "reveal_from_deck")
        self.assertEqual([e["card"] for e in revealed], [target])
        self.assertEqual(kinds(used, done), ["reveal_from_deck", "shuffle"])
        for viewer in (1, None):
            self.assertEqual(observe(used, viewer)["decision"], {"kind": SEARCH_DECK, "player": 0})  # 選べるものの数を見せない
        audited(self, done)
        rejects(self, done, UsePokemonPower(0, done.players[0].bench[0].pokemon_id, 0), "POWER_ALREADY_USED", error=IllegalActionError)

    def test_join_picks_basic_or_evolution_cards_only(self):
        deck = [H.RATTATA, H.IVYSAUR, FOSSIL, DOLL, H.POTION, W]
        state = board(mon(H.RATTATA), bench=(mon(UJ), mon(UO), mon(UI), mon(UN)), deck=deck)
        used = power(state, state.players[0].bench[0].pokemon_id)
        self.assertEqual(sorted(used.cards[o].card_id for o in used.decision.options), sorted([H.RATTATA, H.IVYSAUR]))  # 化石・人形は山札ではトレーナー
        done = answer(used, used.decision.options[:1])
        self.assertEqual(kinds(used, done), ["reveal_from_deck", "shuffle"])
        audited(self, done)

    def test_conditions_use_the_own_bench_only(self):
        active = board(mon(UF), bench=(mon(UI), mon(UN), mon(UD)), deck=[H.POTION])
        rejects(self, active, UsePokemonPower(0, active.players[0].active.pokemon_id, 0), "POKEMON_NOT_ON_BENCH", error=IllegalActionError)
        cases = {
            "D がバトル場": board(mon(UD), bench=(mon(UF), mon(UI), mon(UN)), deck=[H.POTION]),
            "D が相手の場": board(mon(H.RATTATA), bench=(mon(UF), mon(UI), mon(UN)), opponent_bench=(mon(UD),), deck=[H.POTION]),
            "N がいない": board(mon(H.RATTATA), bench=(mon(UF), mon(UI), mon(UD), mon(UO)), deck=[H.POTION]),
        }
        for label, state in cases.items():
            with self.subTest(label=label):
                rejects(self, state, UsePokemonPower(0, state.players[0].bench[0].pokemon_id, 0), "REQUIRED_BENCH_POKEMON_MISSING", error=IllegalActionError)

    def test_no_target_is_pw3_before_declaration(self):
        for deck in ([W, H.RATTATA], []):
            with self.subTest(deck=len(deck)):
                state = self.find_board(deck)
                rejects(self, state, UsePokemonPower(0, state.players[0].bench[0].pokemon_id, 0), PW3)
        join = board(mon(H.RATTATA), bench=(mon(UJ), mon(UO), mon(UI), mon(UN)), deck=[FOSSIL, H.POTION, W])
        rejects(self, join, UsePokemonPower(0, join.players[0].bench[0].pokemon_id, 0), PW3)

    def test_status_does_not_block_but_suppression_does(self):
        asleep = board(mon(H.RATTATA, sleep=True), bench=(mon(UF), mon(UI), mon(UN), mon(UD)), deck=[H.POTION])
        self.assertEqual(power(asleep, asleep.players[0].bench[0].pokemon_id).decision.kind, SEARCH_DECK)
        gas = self.find_board([H.POTION], opponent=mon(H.MUK, evolved_from=H.GRIMER))
        rejects(self, gas, UsePokemonPower(0, gas.players[0].bench[0].pokemon_id, 0), "POWER_SUPPRESSED", error=IllegalActionError)

    def test_face_down_bench_card_is_read_only_when_needed(self):
        """うらのカード（マチスの秘策）: おもてのポケモンで足りるなら読まない。足りないときは名前のグループ・文字を読めない（FD1）。"""
        from tests.test_secret_plan_v0_67 import place

        def secret(bench, hidden):
            return place(build_test_state([
                {"active": mon(H.RATTATA), "bench": list(bench), "hand": [H.LT_SURGES_SECRET_PLAN, hidden], "deck": [H.POTION, W], "prizes": 6},
                {"active": mon(H.RATTATA), "deck": [W] * 10, "prizes": 6}], turn_number=TURN), hidden)

        missing = secret((mon(UF), mon(UI), mon(UN)), UD)
        self.assertTrue(missing.is_face_down(missing.players[0].bench[3]))
        rejects(self, missing, UsePokemonPower(0, missing.players[0].bench[0].pokemon_id, 0), FD1, error=HiddenPropertyRead)
        enough = secret((mon(UF), mon(UI), mon(UN), mon(UD)), H.RATTATA)
        self.assertEqual(power(enough, enough.players[0].bench[0].pokemon_id).decision.kind, SEARCH_DECK)


# ---------------------------------------------------------------- 6 章: ［DARK df］・［NORMAL df］


class DarkNormalDfTest(unittest.TestCase):
    def test_protects_own_unowns_from_the_attackers_type(self):
        """守るのは持ち主の場のアンノーンだけ（自身・ベンチも）。与えるのは今のタイプが「悪」（「無色」）のポケモン（CR-UNOWN-DF-PROTECTS-OWN-UNOWN・SOURCE-TYPE）。"""
        cases = [
            ("無色 → N の場の I", board(mon(H.RATTATA, (W,)), opponent=mon(UI), opponent_bench=(mon(UN),)), 0, 0, "6"),
            ("無色 → N 自身", board(mon(H.RATTATA, (W,)), opponent=mon(UN)), 0, 0, "8"),
            ("悪 → D の場の I", board(umbreon(), opponent=mon(UI), opponent_bench=(mon(UD),)), 0, 0, "6"),
            ("悪 → N の場の I（タイプが違う）", board(umbreon(), opponent=mon(UI), opponent_bench=(mon(UN),)), 0, 20, "1"),
            ("無色の「わるい」ポケモン → D の場の I", board(mon(DARK_DRAGONAIR, (W, W, W), played_turn=1, evolved_from=H.DRATINI, evolved_turn=3), opponent=mon(UI), opponent_bench=(mon(UD),)),
             0, 20, "1"),
            ("無色 → N の場のコラッタ（アンノーンでない）", board(mon(H.RATTATA, (W,)), opponent=mon(H.RATTATA), opponent_bench=(mon(UN),)), 0, 20, "1"),
            ("無色 → 自分の場の N（相手のアンノーンは守らない）", board(mon(H.RATTATA, (W,)), bench=(mon(UN),), opponent=mon(UI)), 0, 20, "1"),
        ]
        for label, state, attack, amount, step in cases:
            with self.subTest(label=label):
                done = declare(state, attack, TL)
                (hit,) = new_events(state, done, "damage")
                self.assertEqual((hit["amount"], hit["steps"][-1][0].split()[0]), (amount, step))
                audited(self, done)

    def test_own_attack_on_own_bench_is_reduced(self):
        """自分の「無色」ポケモン（エリカのハクリュー）の「ふぶき」の「うら」が、自分の控えのアンノーンに与えるダメージも「-30」（N は自分の場）。"""
        dragonair = mon(H.ERIKAS_DRAGONAIR, (W, W, W), played_turn=1, evolved_from=H.ERIKAS_DRATINI, evolved_turn=3)
        state = board(dragonair, bench=(mon(UI), mon(UN), mon(H.RATTATA)))
        done = declare(state, 0, TL)
        bench = {e["pokemon_id"]: e["amount"] for e in new_events(state, done, "damage") if e.get("target") == "self_bench"}
        ui, un, rattata = (p.pokemon_id for p in state.players[0].bench)
        self.assertEqual(bench, {ui: 0, un: 0, rattata: 10})
        audited(self, done)

    def test_two_copies_stop_only_when_the_reading_matters(self):
        """同じ力が 2 匹以上ではたらきうるとき、どれがはたらくか（0 か）の読み方で受けるダメージが変われば DF1（状態・乱数・ログを変える前）。-60 にしない。"""
        state = board(mon(H.RATTATA, (W,)), opponent=mon(UI), opponent_bench=(mon(UN), mon(UN)))
        rejects(self, state, UseAttack(0, 0), DF1)
        # 隣の止めない場面: 対象外のタイプ・アンノーンでない相手・能力を消す効果で候補が 1 匹・ほかの効果で結果が同じ（ディフェンダーで 0）
        dark = board(umbreon(), opponent=mon(UI), opponent_bench=(mon(UN), mon(UN)))
        self.assertEqual(hits(dark, declare(dark, 0))[0][1], 20)
        other = board(mon(H.RATTATA, (W,)), opponent=mon(H.RATTATA), opponent_bench=(mon(UN), mon(UN)))
        self.assertEqual(hits(other, declare(other, 0))[0][1], 20)
        both = board(umbreon(), opponent=mon(UD), opponent_bench=(mon(UD),))
        rejects(self, both, UseAttack(0, 0), DF1)  # 受ける D 自身（8 段階）・ベンチの D（6 段階）・0 個のどれか
        one = board(umbreon(), opponent=mon(UD), opponent_bench=(mon(UD),))
        stop(one, one.players[1].active)  # 受ける D の力を消す（スタンウェーブの効果）: はたらきうるのはベンチの D だけ
        done = declare(one, 0)
        self.assertEqual(hits(one, done), [(None, 0, "6 アンノーンD［DARK df[ダーク ディーエフ]］")])
        audited(self, done)
        sides = board(umbreon(), bench=(mon(UD),), opponent=mon(UI), opponent_bench=(mon(UD),))  # 「自分の場のほかの」: 相手の場の D は数えない
        self.assertEqual(hits(sides, declare(sides, 0))[0][1], 0)
        guarded = board(mon(H.RATTATA, (W,)), opponent=mon(UI, trainers=[(H.DEFENDER, TURN)]), opponent_bench=(mon(UN), mon(UN)))
        done = declare(guarded, 0)
        self.assertEqual(hits(guarded, done)[0][1], 0)  # 20 - 20 = 0 で、-30 があってもなくても 0
        audited(self, done)
        # 登場・ほかの操作は止めない（同じ力の 2 匹がいるだけ）
        bench = board(mon(UN), bench=(mon(UN),), hand=(UD,))
        self.assertIsNone(apply_kernel(bench, PlayBasicToBench(0, uid(bench, UD))).decision)

    def test_chemical_gas_suppresses(self):
        state = board(mon(H.RATTATA, (W,)), opponent=mon(UI), opponent_bench=(mon(UN), mon(H.MUK, evolved_from=H.GRIMER)))
        self.assertEqual(hits(state, declare(state, 0))[0][1], 20)

    def test_type_condition_is_per_type_reading(self):
        """ダメージを与えるポケモンのタイプは、色の読み方ごとの計算で決める（``DamageModifier.attacker_type``）。"""
        definitions = load_card_pool().definitions
        reduce = DamageModifier(step=6, amount=-30, label="N", attacker_type=E.EnergyType.COLORLESS)
        rules = build_test_state([{"active": H.RATTATA}, {"active": UI}]).rules
        self.assertEqual(calculate_attack_damage(20, definitions[H.RATTATA], definitions[UI], rules, (reduce,)).final, 0)
        self.assertEqual(calculate_attack_damage(20, definitions[UMBREON], definitions[UI], rules, (reduce,)).final, 20)

    def test_power_damage_is_df2(self):
        """R団のカビゴンの［わるいねぞう］の 20（特殊能力のダメージ）を、ワザを使ったアンノーンが受ける: ［NORMAL df］を当てはめるかで量が変わるなら DF2（自身の N・ベンチの N）。
        鋼エネルギー（NIP1X-010）を含む最終の量で比べ、どちらでも 0 なら止めない。"""
        snorlax = mon(ROCKETS_SNORLAX, sleep=True)
        for label, active, bench in (("自身の N", mon(UN, (PS,), trainers=[(SCOPE_LENS, TURN)]), ()),
                                     ("ベンチの N", mon(UI, (PS,), trainers=[(SCOPE_LENS, TURN)]), (mon(UN),))):
            with self.subTest(label=label):
                state = board(active, bench=bench, opponent=snorlax)
                rejects(self, state, UseAttack(0, 0), DF2)
        # 鋼エネルギー（NIP1X-010）は「鋼」でないポケモンの与えるワザのダメージも -10 するので、プラスパワー 2 枚で 10 を与える（ピントレンズで抵抗力を計算しない）
        metal = board(mon(UN, (PS, METAL_NIP, METAL_NIP), trainers=[(SCOPE_LENS, TURN), (H.PLUSPOWER, TURN), (H.PLUSPOWER, TURN)]), opponent=snorlax)
        done = declare(metal, 0)
        self.assertEqual([e["amount"] for e in new_events(metal, done, "counterattack")], [0])
        audited(self, done)
        plain = board(mon(UI, (PS,), trainers=[(SCOPE_LENS, TURN)]), opponent=snorlax)
        done = declare(plain, 0)
        self.assertEqual([e["amount"] for e in new_events(plain, done, "counterattack")], [20])  # N のいない場は今までどおり


# ---------------------------------------------------------------- 7 章: 効果を除くワザ（SS1・FA1・ヤミカラス）


class IgnoredEffectsTest(unittest.TestCase):
    def mirror_speed_star(self, opponent_bench, gust_index):
        """ピジョン（無色）が前の相手の番にヒノアラシ（PF1-004）のスピードスターを受け、突風で相手の控えのアンノーンを出して「オウムがえし」でスピードスターを出す（kyuura の手順案の
        単体の試し。正式な対戦の再現ではない）。"""
        me = {"active": mon(PIDGEOTTO, (F, F, F), evolved_from=H.PIDGEY), "bench": [H.RATTATA], "deck": [G] * 10, "prizes": 3, "hand": [H.GUST]}
        them = {"active": mon(CYNDAQUIL_PF1, (F, W)), "bench": list(opponent_bench), "deck": [W] * 10, "prizes": 3}
        state = build_test_state([me, them], turn_number=TURN - 1, current_player=1)
        state = declare(state, 1)  # スピードスター
        gusted = apply_kernel(state, PlayTrainer(0, uid(state, H.GUST)))
        target = state.players[1].bench[gust_index].pokemon_id
        return answer(gusted, (target,))

    def test_speed_star_scope_is_a_stop_code(self):
        """(1) 無色が写したスピードスター 20 → ベンチに N がいる相手の別のアンノーン: 受けるポケモン自身の効果だけを除くなら 0、相手の場の特殊能力も除くなら 20（SS1）。"""
        state = self.mirror_speed_star((mon(UI), mon(UN)), 0)
        rejects(self, state, UseAttack(0, 1), SS1)
        alone = self.mirror_speed_star((mon(UN), mon(H.RATTATA)), 0)  # (3) 受けるのが唯一の N 自身: どの読み方でも 20
        done = declare(alone, 1)
        self.assertEqual([e["amount"] for e in new_events(alone, done, "damage")][-1:], [20])
        audited(self, done)
        copies = self.mirror_speed_star((mon(UN), mon(UN)), 0)  # 受ける N とベンチの N: どれがはたらくかで除くかが変わる（DF1）
        rejects(self, copies, UseAttack(0, 1), DF1)

    def test_umbreon_feint_attack_is_fa1(self):
        """(2) ブラッキーのだましうち 30 → ベンチに D がいる相手の別のアンノーン: 0 か 30（FA1。選ぶと止める）。受けるのが D 自身なら 30。"""
        state = board(umbreon((H.DARKNESS_ENERGY_NEO1, H.DARKNESS_ENERGY_NEO1, W)), opponent=mon(H.CHANSEY), opponent_bench=(mon(UI), mon(UD)))
        choosing = declare(state, 1)
        active, ui, ud = ids(state, 1)
        self.assertEqual(set(choosing.decision.context_value("unresolved_choices")), {active, ui})  # 相手の対戦ポケモンは悪エネルギーの +10（v0.89 のまま）
        rejects(self, choosing, ResolveDecision(0, choosing.decision.id, (ui,)), FA1)
        done = answer(choosing, (ud,))
        self.assertEqual(hits(choosing, done), [(ud, 30, "1 基本となる計算")])
        audited(self, done)

    def test_murkrow_feint_attack_excludes_only_the_receivers_own_effects(self):
        """ヤミカラスのだましうち（「そのポケモンの持っている」）: 除くのは受けるポケモン自身の効果だけ（v0.92 の型）。ベンチの D はほかのアンノーンを守る（SS1 の比べをしない）。"""
        state = board(mon(MURKROW, (DK, W)), opponent=mon(H.RATTATA), opponent_bench=(mon(UI), mon(UD)))
        choosing = declare(state, 1)
        self.assertEqual(choosing.decision.context_value("unresolved_choices", ()), ())
        _, ui, ud = ids(state, 1)
        protected = answer(choosing, (ui,))
        self.assertEqual(hits(choosing, protected)[0][:2], (ui, 0))
        own = answer(choosing, (ud,))
        self.assertEqual(hits(choosing, own), [(ud, 20, "1 基本となる計算")])
        audited(self, own)
        # 2 匹の D: 受ける I・受ける D のどちらも、どれがはたらくかで受けるダメージが変わる（DF1。選ぶと止める）
        two = board(mon(MURKROW, (DK, W)), opponent=mon(H.RATTATA), opponent_bench=(mon(UI), mon(UD), mon(UD)))
        choosing = declare(two, 1)
        self.assertEqual(set(choosing.decision.context_value("unresolved_choices")), set(ids(two, 1)[1:]))
        self.assertEqual(choosing.decision.context_value("unresolved_code"), DF1)

    def test_murkrow_with_calming_aroma_no_longer_hits_ss1(self):
        """v0.92〜v0.96 は、相手のバトル場のエリカのフシギソウ［くつろぐかおり］と控えを選ぶだましうちで、コードのない SS1（内部エラー）に当たっていた。v0.97 から、受けるポケモン自身の
        効果だけを除く v0.92 の型のとおり、ほかのポケモンの［くつろぐかおり］は半分にする。"""
        ivysaur = mon(H.ERIKAS_IVYSAUR, played_turn=2, evolved_from=H.ERIKAS_BULBASAUR, evolved_turn=4)
        state = board(mon(MURKROW, (DK, W)), opponent=ivysaur, opponent_bench=(mon(H.RATTATA),))
        choosing = declare(state, 1)
        done = answer(choosing, (state.players[1].bench[0].pokemon_id,))
        self.assertEqual([e["amount"] for e in new_events(choosing, done, "damage")], [10])
        audited(self, done)


class DocumentTest(unittest.TestCase):
    def test_document_mentions_the_rulings(self):
        text = DOC.read_text(encoding="utf-8")
        for word in ("DF1", "DF2", "SS1", "FA1", "PW3", "UNRESOLVED_SELF_EXCLUDING_POWER_COPIES", "UNRESOLVED_POWER_DAMAGE_RECEIVED_POWER", "UNRESOLVED_SPEED_STAR_SCOPE",
                     "IGNORE_RECEIVER_HELD", "CR-UNOWN-DF-DAMAGE-STEP"):
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()
