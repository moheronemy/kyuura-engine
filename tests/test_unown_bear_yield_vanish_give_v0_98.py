"""v0.98（docs/unown-bear-yield-vanish-give-v0.98.md）: アンノーンB・Y・V・G の 4 枚（ワザ 4・特殊能力 4）。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面・ルール文。4 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録
（GR-2000-P320-COUNTER-MOVE・v0.42 のカウンターの移動・v0.43 の PW3・v0.52 の場から手札にもどす処理・v0.67 の FD1・v0.82 のリサイクルエネルギー・v0.85 の［ファイヤーリチャージ］・
v0.93 の AL2・v0.96 の名前のグループ・v0.97 のベンチの文字）。英語版の文面・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。
盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.98``）。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttachEnergy,
    AttackKey,
    PlayBasicToBench,
    PlayTrainer,
    PowerKey,
    ResolveDecision,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    ATTACH_FROM_DECK,
    BENCH_FROM_DECK,
    ENTRY_POWER,
    PROMOTE_ACTIVE,
    SELECT_POKEMON,
)
from kyuura_engine.deck import deck_problems
from kyuura_engine.errors import HiddenPropertyRead, IllegalActionError
from kyuura_engine.observation import observe
from kyuura_engine.persistent import add_persistent_effect
from kyuura_engine.state import CannotAttachEnergy
from tests import helpers as H
from tests.helpers import apply_kernel, build_test_state, with_coin_results
from tests.release_catalog import cards_after, cards_before
from tests.test_active_leave_locks_v0_93 import locked
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_power_suppression_lasting_locks_v0_92 import MURKROW, mon, play, uid
from tests.test_unown_family_powers_v0_96 import answer, board, deck_of, kinds
from tests.test_unown_idfnj_powers_v0_97 import same_answers, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "unown-bear-yield-vanish-give-v0.98.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, PS, F, G = H.WATER, H.PSYCHIC, H.FIRE, H.GRASS
UB, UY, UV, UG = "neo3-032", "neo3-033", "neo4-053", "neo4-062"
UI, UD, UF, UN = "neo2-023", "neo2-025", "neo2-026", "PF2-001"
UE, UO, UR = H.UNOWN_E, H.UNOWN_O, H.UNOWN_R
V098 = (UB, UY, UV, UG)
V098_ATTACKS = [AttackKey(c, 0) for c in V098]
V098_POWERS = [PowerKey(c, 0) for c in V098]
BE1, BE2, VN1 = "UNRESOLVED_POWER_COUNTER_MOVE_TO_SAME_POKEMON", "UNRESOLVED_POWER_COUNTER_MOVE_WITHOUT_COUNTERS", "UNRESOLVED_POWER_RETURN_WITHOUT_TARGET"
PW3, FD1, RB2, AL2 = "UNRESOLVED_POWER_ZERO_CARDS", "UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY", "UNRESOLVED_RAINBOW_ATTACH_AS_TYPE", "UNRESOLVED_LEAVE_LOCK_NO_EFFECT"
RULE_TEXT = "「アンノーン」はデッキに4枚までしか入れることができません。"
# 依頼で示された固定データの日本語（写しの文面と照らす。広い正規化をしない）
QUOTED = {
    UB: "この力は、自分の番ごとに1回使うことができる。自分の場の「アンノーン」にのっているダメージカウンターを1個選び、このカードにのせ替える。このカードの残りHPが「10」のとき、この力を使うことはできない。",
    UY: "この力は、自分の番ごとに1回使うことができる。コインを投げて「おもて」なら、自分の山札から「超」エネルギーカードを1枚選び出し、自分の場の「アンノーン」につける。その後、その山札をよく切る。",
    UV: ("この力は、このカードを手札から場に出したとき、1回だけ使うことができる。コインを投げて「おもて」なら、自分の場の、このカード以外の「アンノーン」を1匹選ぶ。その後、"
         "その「アンノーン」についているすべてのカードをトラッシュし、その「アンノーン」を自分の手札にもどす。"),
    UG: ("この力は、自分のベンチに、このカードとアンノーン｢I｣｢V｣｢E｣がいるとき、自分の番ごとに一回使うことができる。コインを投げて「おもて」なら、自分の山札から「基本エネルギーカード」を"
         "1枚選び出し、自分の場のポケモンにつける。その後、その山札をよく切る。"),
}
NAMES = {UB: "BEAR[ベアー]", UY: "YIELD[イールド]", UV: "VANISH[バニッシュ]", UG: "GIVE[ギブ]"}
TURN = 7


def use(state, pokemon_id, *coins, player=0, **choices):
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UsePokemonPower(player, pokemon_id, 0, **choices))


def pid(state, card_id, player=0):
    return next(p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card_id)


def card_ids(state, uids):
    return [state.cards[u].card_id for u in uids]


# ---------------------------------------------------------------- 1〜2 章: 対象・登録・文面・デッキの規定


class RegistrationTest(unittest.TestCase):
    def test_every_attack_and_power_is_registered_with_the_printed_text(self):
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_98"]), V098)
        for key in V098_ATTACKS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
                printed = pool.definitions[key.card_id].attacks[0]
                self.assertIs(entry.effect, E.DAMAGE_ONLY)
                self.assertEqual((entry.name_ja, printed.name_ja, printed.text_ja, entry.text_ja, printed.damage, tuple(t.value for t in printed.cost)),
                                 ("めざめるパワー", "めざめるパワー", None, None, 10, ("psychic",)))
        for key in V098_POWERS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.power_entry(key.card_id, key.power_index)
                printed = pool.definitions[key.card_id].powers[0]
                self.assertEqual((printed.name_ja, printed.text_ja), (NAMES[key.card_id], QUOTED[key.card_id]))
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (printed.name_ja, printed.text_ja, printed.text_ja,
                                                                                                   "kyuura data/cards.json"))
                self.assertEqual(entry.effect.check(printed), [])
        for card in V098:
            definition = pool.definitions[card]
            self.assertIn(card, pool.playable_ids)
            self.assertEqual((definition.stage, definition.hp, definition.pokemon_type, definition.weakness, definition.resistance, definition.retreat_cost),
                             ("basic", 50 if card == UB else 40, E.EnergyType.PSYCHIC, E.EnergyType.PSYCHIC, None, 1))
            self.assertEqual((definition.name_group, definition.deck_group_limit), ("アンノーン", 4))
        self.assertEqual({c: pool.definitions[c].name_letter for c in V098}, {UB: "B", UY: "Y", UV: "V", UG: "G"})

    def test_texts_are_not_normalized(self):
        """［GIVE］の半角のかぎかっこ・「一回」は写しのまま。全角にした文面・「1回」にした文面・ほかのカードの文面は受け付けない（広い正規化をしない）。"""
        pool = load_card_pool()
        give = pool.definitions[UG].powers[0]
        effect = DEFAULT_EFFECTS.power_entry(UG, 0).effect
        for changed in (give.text_ja.replace("｢", "「").replace("｣", "」"), give.text_ja.replace("一回", "1回"), give.text_ja.replace("｢E｣", "｢D｣")):
            with self.subTest(changed=changed):
                self.assertNotEqual(effect.check(dataclasses.replace(give, text_ja=changed)), [])
        yield_ = DEFAULT_EFFECTS.power_entry(UY, 0).effect
        self.assertNotEqual(yield_.check(give), [])
        self.assertNotEqual(effect.check(pool.definitions[UY].powers[0]), [])
        bear = pool.definitions[UB].powers[0]
        self.assertNotEqual(DEFAULT_EFFECTS.power_entry(UB, 0).effect.check(dataclasses.replace(bear, text_ja=bear.text_ja.replace("「10」", "「20」"))), [])

    def test_types(self):
        def effect(card):
            return DEFAULT_EFFECTS.power_entry(card, 0).effect

        self.assertEqual(effect(UB), E.MoveGroupCounterToSelf("アンノーン", 10))
        self.assertTrue(type(effect(UB)).once_per_turn)
        self.assertEqual((effect(UY).energy, effect(UY).group, effect(UY).letters), (E.CardFilter("basic_energy", energy_type=E.EnergyType.PSYCHIC), "アンノーン", ()))
        self.assertEqual((effect(UG).energy, effect(UG).group, effect(UG).letters), (E.CardFilter("basic_energy"), None, ("I", "V", "E")))
        self.assertTrue(type(effect(UY)).once_per_turn and type(effect(UG)).once_per_turn)
        self.assertTrue(isinstance(effect(UV), E.EntryPower) and effect(UV).from_hand_only and not effect(UV).forced)
        for card in V098:
            self.assertTrue(effect(card).declared)
        # 文面にない特殊状態の禁止を、似た型（へんなこうどう・ファイヤーリチャージ）から継承しない（下の各テストで、特殊状態でも使えることを確かめる）
        self.assertNotIsInstance(effect(UB), E.MoveDamageCounterToSelf)
        self.assertNotIsInstance(effect(UY), E.CoinAttachFromDiscardToTypePokemon)

    def test_unregistered_without_the_v0_98_entries(self):
        """今回の登録を除くと対戦に使えなくなるのは、ちょうど 4 枚。過去の範囲は ``cards_before``・``cards_after`` で切り出す。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V098_ATTACKS)
        registry = registry.without_powers(registry.id, V098_POWERS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V098))
        self.assertEqual(set(V098) & set(cards_before(read_extract(), "0.98")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.97")) & set(cards_before(read_extract(), "0.99")), set(V098))

    def test_extract_values(self):
        cards = {c["id"]: c for c in read_extract()["cards"]}
        for card in V098:
            with self.subTest(card=card):
                self.assertEqual(cards[card]["pokemon"]["rules_text"]["ja"], RULE_TEXT)
                self.assertEqual(cards[card]["pokemon"]["attacks"][0]["text"]["ja"], None)  # 説明文のないワザ（文面の出典を作らない）
                self.assertNotIn("corrections", cards[card])
        self.assertEqual({c: cards[c]["jp_print"]["level"] for c in V098}, {UB: 19, UY: 12, UV: 10, UG: 16})
        self.assertEqual(read_extract()["source"]["commit"], "73a169063463bbf7bcaa3137d70cbf9721d11534")  # 写しの元は v0.97 のまま

    def test_adoption_records_and_research_links(self):
        data = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        for card in V098:
            with self.subTest(card=card):
                record = data[card]
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["recorded_on"], record["external_checks"], record["issues"]),
                                 ("kyuura_data", "adopted", "73a169063463bbf7bcaa3137d70cbf9721d11534", "2026-10-25", [], []))
                self.assertEqual(record["kyuura_records"], [])  # kyuura の記録はこの 4 枚を指していない（CR-UNOWN-DECK-LIMIT-ALL-LETTERS の再利用は、直接の記録ではない）
                self.assertEqual(record["play_text"], {"power/0": "kyuura_printed_text"})
                self.assertIn("このカードを直接確かめた記録ではない", record["notes"])
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        self.assertEqual([k for k in links["latest_descriptions"]["adopted_printed_text"] if k.split("/")[0] in V098], [f"{c}/power/0" for c in V098])
        for code, ruling in ((BE1, "BE1"), (BE2, "BE2"), (VN1, "VN1")):
            entry = links["stop_codes"][code]
            self.assertEqual((entry["kyuura_issue"], entry["kyuura_disposition"], [r["ruling_id"] for r in entry["engine_rulings"]]), (None, "not_in_kyuura", [ruling]))
        # 停止コード・未解決の裁定の今の総数は tests/test_catalog_contract.py（ここでは重ねない）
        # kyuura の UQ-CARD-USE-WITHOUT-TARGET の事例に、この 4 枚はない（kyuura への報告事項）。研究の対応表の事例は kyuura と同じまま
        cases = links["kyuura_cases_without_engine_ruling"]["cases"]
        self.assertEqual([c for c in cases if c["card_id"] in V098], [])
        # v0.97 の［INCREASE］・［FIND］・［JOIN］の PW3 の区別（engine_issue_differs）は保つ
        self.assertTrue(all(c["engine_issue_differs"] for c in cases if c["kyuura_issue"] == "UQ-CARD-USE-WITHOUT-TARGET" and c["card_id"] in (UI, UF, "PRN-034")))


class DeckLimitTest(unittest.TestCase):
    """文字・商品にかかわらず、デッキのアンノーンは合わせて 4 枚まで（v0.96 の ``deck_problems``。共通の規定の再利用）。同じ名前の 4 枚までの規定も変えない。"""

    def test_mixed_letters(self):
        self.assertEqual(deck_problems(deck_of(UG, UI, UV, UE, H.RATTATA)), [])  # ［GIVE］の 4 文字
        self.assertEqual(deck_problems(deck_of(UB, UY, UB, UY, H.RATTATA)), [])
        self.assertTrue(any(p.startswith("TOO_MANY_GROUP_COPIES") for p in deck_problems(deck_of(UG, UI, UV, UE, UB))))
        self.assertTrue(any(p.startswith("TOO_MANY_GROUP_COPIES") for p in deck_problems(deck_of(UB, UY, UD, UN, UO))))
        self.assertIn("TOO_MANY_COPIES: 「アンノーンB」が 5 枚（同じ名前は 4 枚まで）", deck_problems(deck_of(*([UB] * 5))))


# ---------------------------------------------------------------- 3 章: ［BEAR］


class BearTest(unittest.TestCase):
    def test_moves_one_counter_from_an_own_unown_to_this_card(self):
        for label, active, bench in (("バトル場のアンノーンから", mon(UI, damage=30), (mon(UB),)), ("ベンチのアンノーンから", mon(H.RATTATA), (mon(UB), mon(UD, damage=20)))):
            with self.subTest(label=label):
                state = board(active, bench=bench)
                source = next(p for p in state.players[0].in_play() if p.damage)
                done = use(state, pid(state, UB), source=source.pokemon_id)
                moved = done.find_pokemon(source.pokemon_id)[1]
                self.assertEqual((moved.damage, done.find_pokemon(pid(state, UB))[1].damage), (source.damage - 10, 10))
                self.assertEqual(kinds(state, done), ["pokemon_power", "move_damage_counter"])  # ダメージの計算・ダメージのログはない
                (event,) = new_events(state, done, "move_damage_counter")
                self.assertEqual((event["count"], event["from_pokemon_id"], event["to_pokemon_id"]), (1, source.pokemon_id, pid(state, UB)))
                audited(self, done)
                rejects(self, done, UsePokemonPower(0, pid(state, UB), 0, source=source.pokemon_id), "POWER_ALREADY_USED", error=IllegalActionError)

    def test_sources_are_own_unowns_only(self):
        state = board(mon(H.RATTATA, damage=20), bench=(mon(UB), mon(UI)), opponent=mon(UD, damage=20))
        b = pid(state, UB)
        rejects(self, state, UsePokemonPower(0, b, 0, source=state.players[0].active.pokemon_id), "SOURCE_NOT_IN_GROUP", error=IllegalActionError)
        rejects(self, state, UsePokemonPower(0, b, 0, source=state.players[1].active.pokemon_id), "SOURCE_NOT_YOURS", error=IllegalActionError)
        rejects(self, state, UsePokemonPower(0, b, 0, source=pid(state, UI)), "NO_DAMAGE_COUNTERS", error=IllegalActionError)
        rejects(self, state, UsePokemonPower(0, b, 0, source=pid(state, UI), target=pid(state, UI)), "POWER_CHOICE_NOT_USED", error=IllegalActionError)

    def test_remaining_hp_10_and_20(self):
        """残りHP（最大HP 50 − ダメージ）が 10 なら使えない（状態・使用の記録・ログを変えない）。20 なら使えて、のせ替えたあと 10（きぜつしない）。"""
        ten = board(mon(UI, damage=20), bench=(mon(UB, damage=40),))
        rejects(self, ten, UsePokemonPower(0, pid(ten, UB), 0, source=ten.players[0].active.pokemon_id), "REMAINING_HP_10", error=IllegalActionError)
        twenty = board(mon(UI, damage=20), bench=(mon(UB, damage=30),))
        done = use(twenty, pid(twenty, UB), source=twenty.players[0].active.pokemon_id)
        self.assertEqual(done.find_pokemon(pid(twenty, UB))[1].damage, 40)
        self.assertEqual(new_events(twenty, done, "knock_out"), [])
        audited(self, done)

    def test_this_card_as_the_source_is_be1_only_for_that_choice(self):
        """このカード自身のカウンターを選ぶのは BE1（ほかのカードの「別のポケモン」を写さない）。同じ盤面で、ほかのアンノーンからの移動は止めない。"""
        state = board(mon(UI, damage=10), bench=(mon(UB, damage=10),))
        rejects(self, state, UsePokemonPower(0, pid(state, UB), 0, source=pid(state, UB)), BE1)
        done = use(state, pid(state, UB), source=state.players[0].active.pokemon_id)
        self.assertEqual(done.find_pokemon(pid(state, UB))[1].damage, 20)
        only_self = board(mon(UI), bench=(mon(UB, damage=10),))
        rejects(self, only_self, UsePokemonPower(0, pid(only_self, UB), 0), "POWER_CHOICE_MISSING", error=IllegalActionError)  # 文面では選べるものがある
        rejects(self, only_self, UsePokemonPower(0, pid(only_self, UB), 0, source=pid(only_self, UB)), BE1)

    def test_no_counters_on_any_own_unown_is_be2(self):
        """どのアンノーンにもカウンターがない（ほかの名前のポケモン・相手のアンノーンにはある）: 移動元を指定せずに使うのは BE2。指定すれば今までどおりの拒否。"""
        state = board(mon(H.RATTATA, damage=20), bench=(mon(UB), mon(UI)), opponent=mon(UD, damage=20))
        rejects(self, state, UsePokemonPower(0, pid(state, UB), 0), BE2)
        with_counters = board(mon(UI, damage=10), bench=(mon(UB),))
        rejects(self, with_counters, UsePokemonPower(0, pid(with_counters, UB), 0), "POWER_CHOICE_MISSING", error=IllegalActionError)

    def test_status_does_not_block_but_suppression_does(self):
        asleep = board(mon(UB, sleep=True), bench=(mon(UI, damage=10),))
        done = use(asleep, pid(asleep, UB), source=pid(asleep, UI))
        self.assertEqual(done.players[0].active.damage, 10)
        confused = board(mon(UB, confusion=True), bench=(mon(UI, damage=10),))
        self.assertEqual(use(confused, pid(confused, UB), source=pid(confused, UI)).players[0].active.damage, 10)
        gas = board(mon(H.RATTATA), bench=(mon(UB), mon(UI, damage=10)), opponent=mon(H.MUK, evolved_from=H.GRIMER))
        rejects(self, gas, UsePokemonPower(0, pid(gas, UB), 0, source=pid(gas, UI)), "POWER_SUPPRESSED", error=IllegalActionError)

    def test_counter_move_is_not_damage(self):
        """のせ替えはダメージではない（GR-2000-P320-COUNTER-MOVE）: 相手の悪のポケモンと自分の［DARK df］がいても、ダメージの計算・反応はない。"""
        state = board(mon(UI, damage=10), bench=(mon(UB), mon(UD)), opponent=mon(MURKROW, (W,)))
        done = use(state, pid(state, UB), source=state.players[0].active.pokemon_id)
        self.assertEqual(new_events(state, done, "damage"), [])
        self.assertEqual(done.find_pokemon(pid(state, UB))[1].damage, 10)


# ---------------------------------------------------------------- 4 章: ［YIELD］・［GIVE］


class YieldTest(unittest.TestCase):
    def test_heads_attaches_a_psychic_energy_from_the_deck_to_an_own_unown(self):
        state = board(mon(UI), bench=(mon(UY), mon(H.RATTATA)), deck=[W, PS, H.FIRE, PS, H.DARKNESS_ENERGY_NEO1, H.MIRACLE_ENERGY, H.DOUBLE_COLORLESS_ENERGY])
        y = pid(state, UY)
        card = use(state, y, HD)
        self.assertEqual((card.decision.kind, card.decision.min_choices, card.decision.max_choices), (ATTACH_FROM_DECK, 1, 1))
        self.assertEqual(card_ids(card, card.decision.options), [PS, PS])  # 「超」の基本エネルギーだけ（ミラクル・悪・無色2個は入らない。ミラクルがあっても止めない）
        self.assertEqual(card.decision.context_value("unresolved_choices", ()), ())
        target = same_answers(self, card, card.decision.options[:1])
        self.assertEqual((target.decision.kind, target.decision.options), (SELECT_POKEMON, (state.players[0].active.pokemon_id, y)))  # このカードも。ラッタは入らない
        for viewer in (1, None):
            self.assertEqual(observe(card, viewer)["decision"], {"kind": ATTACH_FROM_DECK, "player": 0})  # 選べるものの数を見せない
        done = same_answers(self, target, (y,))
        self.assertEqual(card_ids(done, done.find_pokemon(y)[1].energy), [PS])
        self.assertEqual(kinds(target, done), ["power_attach_from_deck", "shuffle"])
        self.assertEqual(kinds(state, card), ["pokemon_power", "coin_flip"])
        self.assertEqual((done.energy_attachments_this_turn, done.energy_attached_by_powers_this_turn), (state.energy_attachments_this_turn, 0))
        audited(self, done)
        rejects(self, done, UsePokemonPower(0, y, 0), "POWER_ALREADY_USED", error=IllegalActionError)

    def test_hand_attachment_is_not_consumed(self):
        state = board(mon(UI), bench=(mon(UY),), hand=(W,), deck=[PS, W])
        y = pid(state, UY)
        card = use(state, y, HD)
        done = answer(answer(card, card.decision.options), (y,))
        attached = apply_kernel(done, AttachEnergy(0, uid(done, W), done.players[0].active.card))
        self.assertEqual(card_ids(attached, attached.players[0].active.energy), [W])

    def test_tails_does_nothing_and_counts_as_used(self):
        state = board(mon(UI), bench=(mon(UY),), deck=[PS, W])
        done = use(state, pid(state, UY), TL)
        self.assertIsNone(done.decision)
        self.assertEqual(kinds(state, done), ["pokemon_power", "coin_flip"])  # 山札を見ない・つけない・切らない
        self.assertEqual(done.players[0].deck, state.players[0].deck)
        rejects(self, done, UsePokemonPower(0, pid(state, UY), 0), "POWER_ALREADY_USED", error=IllegalActionError)

    def test_no_card_or_no_target_is_pw3_before_the_coin(self):
        for label, state in (("山札に「超」がない", board(mon(UI), bench=(mon(UY),), deck=[W, W])), ("山札 0 枚", board(mon(UI), bench=(mon(UY),), deck=[]))):
            with self.subTest(label=label):
                rejects(self, state, UsePokemonPower(0, pid(state, UY), 0), PW3)  # コインを投げない（乱数・ログを変えない）

    def test_rainbow_in_the_deck_is_rb2_when_chosen(self):
        state = board(mon(UI), bench=(mon(UY),), deck=[PS, H.RAINBOW_ENERGY, W])
        card = use(state, pid(state, UY), HD)
        rainbow = next(u for u in card.decision.options if card.cards[u].card_id == H.RAINBOW_ENERGY)
        self.assertEqual((card.decision.context_value("unresolved_choices"), card.decision.context_value("unresolved_code")), ((rainbow,), RB2))
        rejects(self, card, ResolveDecision(0, card.decision.id, (rainbow,)), RB2)
        self.assertEqual(answer(card, (next(u for u in card.decision.options if u != rainbow),)).decision.kind, SELECT_POKEMON)
        only = board(mon(UI), bench=(mon(UY),), deck=[H.RAINBOW_ENERGY, W])
        rejects(self, only, UsePokemonPower(0, pid(only, UY), 0), RB2)  # コインの前

    def test_targets_are_own_unowns_that_can_take_energy(self):
        state = board(mon(UI), bench=(mon(UY), mon(UE)), opponent=mon(UD), deck=[PS])
        beam = state.clone()
        beam.turn_number = TURN - 1  # 相手の番に与えた効果（ログの番と合わせる。自然な対戦で起こらない盤面を作るため）
        add_persistent_effect(beam, 0, beam.players[0].active, CannotAttachEnergy(beam.players[1].active.card, 1, TURN - 1, TURN), attack=f"{H.MISTYS_TENTACOOL}#0")
        beam.turn_number = TURN
        card = use(beam, pid(beam, UY), HD)
        target = answer(card, card.decision.options)
        self.assertEqual(target.decision.options, (pid(beam, UY), pid(beam, UE)))  # クリスタルビームを受けたポケモン・相手のアンノーンは選べない

    def test_face_down_target_is_fd1_when_chosen(self):
        from tests.test_secret_plan_v0_67 import place

        state = place(build_test_state([
            {"active": mon(UI), "bench": [mon(UY)], "hand": [H.LT_SURGES_SECRET_PLAN, UE], "deck": [PS, W], "prizes": 6},
            {"active": mon(H.RATTATA), "deck": [W] * 10, "prizes": 6}], turn_number=TURN), UE)
        hidden = state.players[0].bench[-1]
        self.assertTrue(state.is_face_down(hidden))
        card = use(state, pid(state, UY), HD)
        target = answer(card, card.decision.options)
        self.assertEqual(target.decision.context_value("unresolved_choices"), (hidden.pokemon_id,))
        rejects(self, target, ResolveDecision(0, target.decision.id, (hidden.pokemon_id,)), FD1)

    def test_status_does_not_block(self):
        state = board(mon(UY, paralysis=TURN - 1), deck=[PS])
        self.assertEqual(use(state, pid(state, UY), HD).decision.kind, ATTACH_FROM_DECK)

    def test_invalid_answers_change_nothing(self):
        state = board(mon(UI), bench=(mon(UY),), deck=[PS, W])
        card = use(state, pid(state, UY), HD)
        wrong = next(u for u in card.players[0].deck if card.cards[u].card_id == W)
        rejects(self, card, ResolveDecision(0, card.decision.id, (wrong,)), "INVALID_CHOICE", error=IllegalActionError)
        rejects(self, card, ResolveDecision(0, card.decision.id, ()), "INVALID_CHOICE_COUNT", error=IllegalActionError)
        rejects(self, card, ResolveDecision(1, card.decision.id, card.decision.options), "NOT_YOUR_DECISION", error=IllegalActionError)
        target = answer(card, card.decision.options)
        rejects(self, target, ResolveDecision(0, target.decision.id, (state.players[1].active.pokemon_id,)), "INVALID_CHOICE", error=IllegalActionError)
        self.assertEqual(snap(answer(target, (pid(state, UY),))), snap(answer(target.clone(), (pid(state, UY),))))


class GiveTest(unittest.TestCase):
    def give_board(self, deck, bench=None, active=None, **kw):
        return board(active or mon(H.RATTATA), bench=bench if bench is not None else (mon(UG), mon(UI), mon(UV), mon(UE)), deck=deck, **kw)

    def test_heads_attaches_any_basic_energy_to_any_own_pokemon(self):
        state = self.give_board([W, PS, F, H.RAINBOW_ENERGY, H.DOUBLE_COLORLESS_ENERGY, H.DARKNESS_ENERGY_NEO1])
        g = pid(state, UG)
        card = use(state, g, HD)
        self.assertEqual(sorted(card_ids(card, card.decision.options)), sorted([W, PS, F]))  # 特殊エネルギー（レインボーを含む）は入らない
        self.assertEqual(card.decision.context_value("unresolved_choices", ()), ())
        fire = next(u for u in card.decision.options if card.cards[u].card_id == F)
        target = answer(card, (fire,))
        self.assertEqual(target.decision.options, tuple(p.pokemon_id for p in state.players[0].in_play()))  # アンノーンに限らない
        done = same_answers(self, target, (state.players[0].active.pokemon_id,))
        self.assertEqual(card_ids(done, done.players[0].active.energy), [F])
        self.assertEqual(kinds(target, done), ["power_attach_from_deck", "shuffle"])
        audited(self, done)
        rejects(self, done, UsePokemonPower(0, g, 0), "POWER_ALREADY_USED", error=IllegalActionError)

    def test_conditions_use_this_card_and_the_letters_on_the_own_bench(self):
        active = self.give_board([W], active=mon(UG), bench=(mon(UI), mon(UV), mon(UE)))
        rejects(self, active, UsePokemonPower(0, active.players[0].active.pokemon_id, 0), "POKEMON_NOT_ON_BENCH", error=IllegalActionError)
        cases = {
            "E がバトル場": self.give_board([W], active=mon(UE), bench=(mon(UG), mon(UI), mon(UV))),
            "E が相手の場": self.give_board([W], bench=(mon(UG), mon(UI), mon(UV)), opponent_bench=(mon(UE),)),
            "V がいない（別の文字）": self.give_board([W], bench=(mon(UG), mon(UI), mon(UD), mon(UE))),
        }
        for label, state in cases.items():
            with self.subTest(label=label):
                rejects(self, state, UsePokemonPower(0, pid(state, UG), 0), "REQUIRED_BENCH_POKEMON_MISSING", error=IllegalActionError)

    def test_no_basic_energy_is_pw3_before_the_coin(self):
        for deck in ([H.RAINBOW_ENERGY, H.POTION], []):
            with self.subTest(deck=len(deck)):
                state = self.give_board(deck)
                rejects(self, state, UsePokemonPower(0, pid(state, UG), 0), PW3)

    def test_tails_and_status(self):
        asleep = self.give_board([W, PS], active=mon(H.RATTATA, sleep=True))
        done = use(asleep, pid(asleep, UG), TL)
        self.assertEqual((done.decision, kinds(asleep, done)), (None, ["pokemon_power", "coin_flip"]))

    def test_face_down_bench_card_is_read_only_when_needed(self):
        from tests.test_secret_plan_v0_67 import place

        def secret(bench, hidden):
            return place(build_test_state([
                {"active": mon(H.RATTATA), "bench": list(bench), "hand": [H.LT_SURGES_SECRET_PLAN, hidden], "deck": [W, PS], "prizes": 6},
                {"active": mon(H.RATTATA), "deck": [W] * 10, "prizes": 6}], turn_number=TURN), hidden)

        missing = secret((mon(UG), mon(UI), mon(UV)), UE)
        rejects(self, missing, UsePokemonPower(0, pid(missing, UG), 0), FD1, error=HiddenPropertyRead)
        enough = secret((mon(UG), mon(UI), mon(UV), mon(UE)), H.RATTATA)
        card = use(enough, pid(enough, UG), HD)
        target = answer(card, card.decision.options[:1])
        self.assertIn(enough.players[0].bench[-1].pokemon_id, target.decision.options)  # 「自分の場のポケモン」なのでうらのカードも選べる（選んだら共通の処理がおもてにする）
        self.assertEqual(target.decision.context_value("unresolved_choices", ()), ())


# ---------------------------------------------------------------- 5 章: ［VANISH］


def play_v(state, player=0):
    return apply_kernel(state, PlayBasicToBench(player, uid(state, UV, player)))


class VanishTest(unittest.TestCase):
    def test_heads_discards_all_attached_cards_then_returns_the_unown_to_hand(self):
        state = board(mon(UI, (PS, H.RECYCLE_ENERGY), damage=20, trainers=[(H.PLUSPOWER, TURN)]), bench=(mon(UE),), hand=(UV,))
        offered = play_v(state)
        self.assertEqual((offered.decision.kind, offered.decision.min_choices, offered.decision.max_choices), (ENTRY_POWER, 0, 1))
        self.assertEqual(offered.decision.context_value("unresolved_choices", ()), ())
        chosen = answer(with_coin_results(offered, HD), offered.decision.options)
        v = pid(chosen, UV)
        self.assertEqual((chosen.decision.kind, chosen.decision.options), (SELECT_POKEMON, (pid(state, UI), pid(state, UE))))  # このカード以外（バトル場・ベンチ）
        i = pid(state, UI)
        done = same_answers(self, chosen, (i,))
        self.assertEqual(kinds(chosen, done), ["discard_attached_cards", "energy_returned_to_hand", "return_in_play_to_hand"])  # トラッシュ → もどす（説明の順番）
        (discarded,) = new_events(chosen, done, "discard_attached_cards")
        self.assertEqual((card_ids(done, discarded["energy"]), card_ids(done, discarded["trainers"]), discarded["power"]), ([PS, H.RECYCLE_ENERGY], [H.PLUSPOWER], f"{UV}@power0"))
        (returned,) = new_events(chosen, done, "return_in_play_to_hand")
        self.assertEqual((card_ids(done, returned["cards"]), returned["damage"]), ([UI], 20))  # カード（このアンノーン）だけ。ダメージはなくなる
        self.assertEqual(sorted(card_ids(done, done.players[0].hand)), sorted([UI, H.RECYCLE_ENERGY]))  # リサイクルエネルギーはトラッシュしたあと手札にもどる
        self.assertEqual(sorted(card_ids(done, done.players[0].discard)), sorted([PS, H.PLUSPOWER]))
        self.assertEqual((len(done.players[1].prizes), new_events(chosen, done, "knock_out")), (6, []))  # きぜつではない
        self.assertIsNotNone(done.find_pokemon(v))
        self.assertEqual((done.decision.kind, done.decision.player), (PROMOTE_ACTIVE, 0))  # 空いたバトル場（使用後の処理）
        promoted = answer(done, (v,))
        self.assertIs(promoted.players[0].active, promoted.find_pokemon(v)[1])
        audited(self, promoted)

    def test_tails_does_nothing(self):
        state = board(mon(UI, (PS,)), bench=(), hand=(UV,))
        offered = play_v(state)
        done = answer(with_coin_results(offered, TL), offered.decision.options)
        self.assertIsNone(done.decision)
        self.assertEqual(kinds(offered, done), ["pokemon_power", "coin_flip"])
        rejects(self, done, UsePokemonPower(0, pid(done, UV), 0), "POWER_NOT_USABLE_NOW", error=IllegalActionError)  # あとから使わない

    def test_other_unowns_only_including_another_v(self):
        state = board(mon(H.RATTATA), bench=(mon(UV), mon(UB)), hand=(UV,), opponent=mon(UI))
        offered = play_v(state)
        chosen = answer(with_coin_results(offered, HD), offered.decision.options)
        played = chosen.players[0].bench[-1].pokemon_id
        self.assertEqual(chosen.decision.options, (state.players[0].bench[0].pokemon_id, state.players[0].bench[1].pokemon_id))  # 別のアンノーンV も選べる（ラッタ・相手は入らない）
        self.assertNotIn(played, chosen.decision.options)

    def test_no_other_unown_is_vn1(self):
        state = board(mon(H.RATTATA), bench=(), hand=(UV,), opponent=mon(UI))
        offered = play_v(state)
        self.assertEqual(offered.decision.context_value("unresolved_code"), VN1)
        rejects(self, offered, ResolveDecision(0, offered.decision.id, offered.decision.options), VN1)
        declined = answer(offered, ())
        self.assertIsNone(declined.decision)
        audited(self, declined)

    def test_placed_from_the_deck_or_with_full_bench_paths(self):
        """山札から出した V（［INCREASE］）には手札からの機会がない。"""
        state = board(mon(H.RATTATA), bench=(), hand=(UI,), deck=[UV, W, W])
        offered = apply_kernel(state, PlayBasicToBench(0, uid(state, UI)))
        bench = answer(offered, offered.decision.options)
        self.assertEqual(bench.decision.kind, BENCH_FROM_DECK)
        done = answer(bench, bench.decision.options)
        self.assertIsNone(done.decision)
        self.assertEqual(new_events(bench, done, "pokemon_power"), [])

    def test_returned_unown_replayed_from_hand_has_a_new_opportunity(self):
        """手札にもどした I・V を手札から出し直すと、新しい「手札から場に出したとき」の機会がある（同じ決定の二重の実行ではない）。"""
        state = board(mon(H.RATTATA), bench=(mon(UI), mon(UV)), hand=(UV,), deck=[UE, W, W])
        offered = play_v(state)
        chosen = answer(with_coin_results(offered, HD), offered.decision.options)
        done = answer(chosen, (pid(state, UI),))
        self.assertIn(uid(done, UI), done.players[0].hand)
        replayed = apply_kernel(done, PlayBasicToBench(0, uid(done, UI)))
        self.assertEqual((replayed.decision.kind, card_ids(replayed, [replayed.find_pokemon(replayed.decision.options[0])[1].card])), (ENTRY_POWER, [UI]))
        other = answer(with_coin_results(play_v(state), HD), play_v(state).decision.options)
        back = answer(other, (state.players[0].bench[1].pokemon_id,))  # もう 1 枚の V をもどす
        again = play_v(back)
        self.assertEqual(again.decision.kind, ENTRY_POWER)
        self.assertNotEqual(again.decision.options, offered.decision.options)  # 新しい場のポケモン

    def test_face_down_and_leave_locked_choices_are_stopped(self):
        from tests.test_secret_plan_v0_67 import place

        state = place(build_test_state([
            {"active": mon(UI), "bench": [], "hand": [H.LT_SURGES_SECRET_PLAN, UE, UV], "deck": [W] * 5, "prizes": 6},
            {"active": mon(H.RATTATA), "deck": [W] * 10, "prizes": 6}], turn_number=TURN), UE)
        hidden = state.players[0].bench[-1].pokemon_id
        offered = play_v(state)
        chosen = answer(with_coin_results(offered, HD), offered.decision.options)
        self.assertEqual(chosen.decision.context_value("unresolved_choices"), (hidden,))
        rejects(self, chosen, ResolveDecision(0, chosen.decision.id, (hidden,)), FD1)
        self.assertTrue(new_events(chosen, answer(chosen, (state.players[0].active.pokemon_id,)), "return_in_play_to_hand"))
        lock = locked(board(mon(UI), bench=(mon(H.RATTATA),), hand=(UV,)), 0)
        offered = play_v(lock)
        self.assertEqual(offered.decision.context_value("unresolved_code"), AL2)  # 選べるのがはなれられないバトル場のアンノーンだけ

    def test_erikas_perfume_owner_returns_the_active_during_the_other_turn(self):
        """エリカの香水で相手の手札から出た V: 持ち主（相手）に機会があり、相手のバトル場のアンノーンを手札にもどしたら、持ち主がバトル場に出してから、自分の番が続く。"""
        state = board(mon(H.RATTATA), hand=(H.ERIKAS_PERFUME, W), opponent=mon(UI, (PS,)), opponent_bench=(), opponent_hand=(UV, W, W))
        step = apply_kernel(state, PlayTrainer(0, uid(state, H.ERIKAS_PERFUME)))
        while step.decision is not None and step.decision.kind != ENTRY_POWER:
            step = answer(step, step.decision.options[:1])
        self.assertEqual((step.decision.kind, step.decision.player), (ENTRY_POWER, 1))
        chosen = answer(with_coin_results(step, HD), step.decision.options)
        self.assertEqual((chosen.decision.kind, chosen.decision.player, chosen.decision.options), (SELECT_POKEMON, 1, (state.players[1].active.pokemon_id,)))
        done = answer(chosen, chosen.decision.options)
        while done.decision is not None:
            self.assertEqual(done.decision.player, 1)
            done = answer(done, done.decision.options[:1])
        self.assertEqual(card_ids(done, [done.players[1].active.card]), [UV])
        self.assertIn(uid(done, UI, player=1), done.players[1].hand)
        self.assertEqual((done.current_player, done.trainer_in_use), (0, None))
        audited(self, done)

    def test_lt_surge_puts_v_active_and_returns_the_former_active_from_the_bench(self):
        """マチス（手札のたねポケモンをバトル場に出し、前のポケモンをベンチにもどす）で出した V: トレーナーの途中の機会で、ベンチにもどったアンノーンを手札にもどしてから、トレーナーを
        使い終える（バトル場は V のまま。v0.86 の続きの段）。"""
        state = board(mon(UI, (PS,)), bench=(), hand=(H.LT_SURGE_TRAINER, UV))
        surge = uid(state, H.LT_SURGE_TRAINER)
        step = apply_kernel(state, PlayTrainer(0, surge))
        while step.decision is not None and step.decision.kind != ENTRY_POWER:
            step = answer(step, [o for o in step.decision.options if step.cards.get(o) and step.cards[o].card_id == UV][:1] or step.decision.options[:1])
        self.assertEqual((step.decision.kind, step.decision.player), (ENTRY_POWER, 0))
        self.assertIsNotNone(step.trainer_in_use)
        chosen = answer(with_coin_results(step, HD), step.decision.options)
        self.assertEqual(chosen.decision.options, (pid(state, UI),))
        done = answer(chosen, chosen.decision.options)
        self.assertIsNone(done.decision)
        self.assertEqual((card_ids(done, [done.players[0].active.card]), done.players[0].bench, done.trainer_in_use), ([UV], [], None))
        self.assertIn(surge, done.players[0].discard)
        self.assertIn(uid(done, UI), done.players[0].hand)
        audited(self, done)

    def test_ecogym_does_not_return_own_power_discards(self):
        """エコロジムは相手の効果でトラッシュしたときだけ（持ち主の［VANISH］では基本エネルギーはトラッシュに残る）。リサイクルエネルギーはどちらでももどる。"""
        state = play(board(mon(UI, (PS, H.RECYCLE_ENERGY)), bench=(mon(UE),), hand=(H.ECOGYM, UV)), H.ECOGYM)
        offered = play_v(state)
        chosen = answer(with_coin_results(offered, HD), offered.decision.options)
        done = answer(chosen, (pid(state, UI),))
        returned = new_events(chosen, done, "energy_returned_to_hand")
        self.assertEqual([(card_ids(done, [e["card"]]), e["reasons"]) for e in returned], [([H.RECYCLE_ENERGY], ("recycle_energy",))])
        self.assertIn(PS, card_ids(done, done.players[0].discard))

    def test_tower_does_not_stop_recycle_energy(self):
        """ポケモンタワーはトラッシュから手札に加える効果だけを消し、リサイクルエネルギーの効果は消さない（v0.82 の読み方）。"""
        state = play(board(mon(UI, (H.RECYCLE_ENERGY,)), bench=(mon(UE),), hand=(H.POKEMON_TOWER, UV)), H.POKEMON_TOWER)
        offered = play_v(state)
        chosen = answer(with_coin_results(offered, HD), offered.decision.options)
        done = answer(chosen, (pid(state, UI),))
        self.assertEqual(card_ids(done, [e["card"] for e in new_events(chosen, done, "energy_returned_to_hand")]), [H.RECYCLE_ENERGY])

    def test_invalid_answers_change_nothing(self):
        state = board(mon(UI), bench=(mon(UE),), hand=(UV,))
        offered = play_v(state)
        chosen = answer(with_coin_results(offered, HD), offered.decision.options)
        rejects(self, chosen, ResolveDecision(0, chosen.decision.id, (pid(chosen, UV),)), "INVALID_CHOICE", error=IllegalActionError)
        rejects(self, chosen, ResolveDecision(0, chosen.decision.id, ()), "INVALID_CHOICE_COUNT", error=IllegalActionError)
        rejects(self, chosen, ResolveDecision(1, chosen.decision.id, chosen.decision.options[:1]), "NOT_YOUR_DECISION", error=IllegalActionError)


# ---------------------------------------------------------------- 文書


class DocumentTest(unittest.TestCase):
    def test_document_lists_the_cards_codes_and_unhit_boundaries(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in (*V098, *NAMES.values(), BE1, BE2, VN1, "PW3", "FD1", "RB2", "AL2", "73a1690", "UQ-CARD-USE-WITHOUT-TARGET", "対戦で一度も起こらなかったもの"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
