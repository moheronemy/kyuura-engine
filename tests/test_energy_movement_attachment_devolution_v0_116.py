"""v0.116（docs/energy-movement-attachment-devolution-v0.116.md）: エネルギーの付け替え・ついた時に発動するワザの持続効果・付属カードの回収と退化のポケモン 13 枚（ワザ 25）。
ハネッコ（neo1-005）・レディアン（neo1-010）・ニョロゾ（neo2-016）・ネイティオ（neo2-024）・クロバット（neo3-006）・わるいオムスター（neo4-038）・わるいゴースト（neo4-055）・ウツドン
（ES3-006）・ユンゲラー（ES3-020・QSG-027。SC-ES3-020）・ピジョン（ES3-032）・ミュウツー（PR1-022）・フーディン（PR1-055）。

根拠は kyuura データの採用（kyuura ``e519b99`` の data/cards.json の日本語の印刷の文面。わるいオムスターは UQ-NEO-TEXT-BABY-CATEGORIES の事例。ほかの 12 枚を指す LD-・CC-・CR-・UQ-・
エラッタはない）と、既存の規定と読み方の記録（GR-2000-P325-SAME-TIMING・GR-2000-P320-COUNTER-MOVE・CR-ENERGY-TRANS-NOT-ATTACHMENT・CR-TRANSPARENCY-ENERGY-BOMB（T36）・v0.4b の問い・
HC1・HC3・HC4・CX1・CB1・DV5・FC1・A3・NB1・NB2・RB3・T19b・GR-2000-P315-EVOLVED-BABY・GR-2000-P325-PRE-NEO-BABY）。英語の欄・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの
新しい読み直し・カードの画像の照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は
tools/existing_effect_games.py の ``--batch v0.116``）。
"""

from __future__ import annotations

import copy
import inspect
import json
import pathlib
import pickle
import re
import unittest
from unittest import mock

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttachEnergy,
    EvolvePokemon,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine import reactions as R
from kyuura_engine.cards import EnergyType, load_card_pool, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    ATTACH_FROM_DECK,
    BENCH_FROM_DISCARD,
    ESP_REDO,
    MOVE_OPPONENT_ENERGY,
    REACTION_ORDER,
    RECOVER_ENERGY,
    SELECT_POKEMON,
)
from kyuura_engine.engine import check_invariants
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import PUBLIC_EVENTS, observe
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import (
    MARKER_COLOR,
    CannotRetreat,
    EvolutionLock,
    StatusOnEnergyAttach,
)
from tests import helpers as H
from tests import test_variable_coins_search_attachments_v0_113 as V113
from tests.helpers import apply_kernel, build_test_state, with_coin_results
from tests.log_audit import LATEST_FORMAT
from tests.release_catalog import cards_after, cards_before
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_unown_family_powers_v0_96 import TURN, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "energy-movement-attachment-devolution-v0.116.md"
COMMIT = "e519b99e2adcc6c2cd0998569ae5ee1101de6e89"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, FR, L, PS, G, F = H.WATER, H.FIRE, H.LIGHTNING, H.PSYCHIC, H.GRASS, H.FIGHTING
DCE, FULL_HEAL, RAINBOW = H.DOUBLE_COLORLESS_ENERGY, H.FULL_HEAL_ENERGY, H.RAINBOW_ENERGY
RECYCLE = "neo1-096"
HOPPIP, LEDIAN, POLIWHIRL, XATU, CROBAT = "neo1-005", "neo1-010", "neo2-016", "neo2-024", "neo3-006"
DARK_OMASTAR, DARK_HAUNTER, WEEPINBELL, KADABRA, KADABRA_Q = "neo4-038", "neo4-055", "ES3-006", "ES3-020", "QSG-027"
PIDGEOTTO, MEWTWO_PR, ALAKAZAM_PR = "ES3-032", "PR1-022", "PR1-055"
V0116 = (HOPPIP, LEDIAN, POLIWHIRL, XATU, CROBAT, DARK_OMASTAR, DARK_HAUNTER, WEEPINBELL, KADABRA, PIDGEOTTO, KADABRA_Q, MEWTWO_PR, ALAKAZAM_PR)
LEDYBA, POLIWAG_N2, NATU, ZUBAT_N3, GOLBAT_N3, DARK_OMANYTE = "neo1-003", "neo2-013", "neo2-022", "neo3-001", "neo3-004", "neo4-035"
GASTLY_N4, BELLSPROUT_ES3, ABRA_ES1, ABRA_Q, PIDGEY_ES1, KADABRA_ES3_019 = "neo4-048", "ES3-005", "ES1-020", "QSG-026", "ES1-024", "ES3-019"
PICHU, PIKACHU = "neo1-042", H.PIKACHU
BELOW = {LEDIAN: [LEDYBA], POLIWHIRL: [POLIWAG_N2], XATU: [NATU], CROBAT: [ZUBAT_N3, GOLBAT_N3], DARK_OMASTAR: [H.MYSTERIOUS_FOSSIL, DARK_OMANYTE],
         DARK_HAUNTER: [GASTLY_N4], WEEPINBELL: [BELLSPROUT_ES3], KADABRA: [ABRA_ES1], KADABRA_Q: [ABRA_Q], PIDGEOTTO: [PIDGEY_ES1],
         ALAKAZAM_PR: [ABRA_ES1, KADABRA_ES3_019], H.VENUSAUR: [H.BULBASAUR, H.IVYSAUR], H.BLASTOISE: ["PMCG1-023", "PMCG1-027"],
         H.BLAINES_NINETALES: [H.BLAINES_VULPIX], H.HAUNTER: [H.GASTLY], H.BUZZAP_ELECTRODE: [H.VOLTORB]}
EXPECTED = {
    (HOPPIP, 0): E.DAMAGE_ONLY, (HOPPIP, 1): E.PutNamedBasicFromDeckOntoBenchOrFail(("ハネッコ",)),
    (LEDIAN, 0): E.DamageThenMoveAllEnergyToTypeBenchThenSwitch(EnergyType.GRASS),
    (POLIWHIRL, 0): E.SelfCountersThenAttachBasicEnergyFromDeck(3, 2), (POLIWHIRL, 1): E.ExtraEnergyDamageMixed(EnergyType.WATER, 10, 2),
    (XATU, 0): E.CoinMoveOpponentEnergyCardToBenchOrFail(), (XATU, 1): E.DAMAGE_ONLY,
    (CROBAT, 0): E.DamageThenStatusOnEnergyAttach("poison"), (CROBAT, 1): E.CoinsTimesDamageThenConfuseIfAtLeast(4, 20, 2),
    (DARK_OMASTAR, 0): E.CoinDevolveOpponentEvolvedToDeck(), (DARK_OMASTAR, 1): E.DamageThenEvolutionLock(),
    (DARK_HAUNTER, 0): E.BenchBabyOrBasicFromOpponentDiscardOrFail(1), (DARK_HAUNTER, 1): E.DamageThenSleepOnHeadsElseRetreatLock(),
    (WEEPINBELL, 0): E.HealAllThenRegressToBasic(), (WEEPINBELL, 1): E.DamageThenDiscardOpponentEnergy(on_heads=True),
    (KADABRA, 0): E.RecoverSpecialEnergyFromDiscard(), (KADABRA, 1): E.DamageThenStatusOnEnergyAttach("paralysis"),
    (KADABRA_Q, 0): E.RecoverSpecialEnergyFromDiscard(), (KADABRA_Q, 1): E.DamageThenStatusOnEnergyAttach("paralysis"),
    (PIDGEOTTO, 0): E.DamageThenCoinReturnAttachedCardsToHand(), (PIDGEOTTO, 1): E.FailOnTailsDamageThenSelfBarrier(),
    (MEWTWO_PR, 0): E.FailOnTailsMoveOpponentFieldEnergy(), (MEWTWO_PR, 1): E.ChooseOpponentPokemonDamage(30),
    (ALAKAZAM_PR, 0): E.DamageSetAgainstType(EnergyType.PSYCHIC, 60), (ALAKAZAM_PR, 1): E.DiscardAllEnergyThenMoveAllSelfCountersToOpponent(),
}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, *, bench=(H.RATTATA,), opponent=None, opponent_bench=(H.RATTATA,), hand=(), opponent_hand=(), deck=None, discard=(), opponent_deck=None,
          opponent_discard=(), current=0, turn=TURN):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": list(deck if deck is not None else [W] * 10), "discard": list(discard), "prizes": 6}
    them = {"active": opponent or mon(H.HITMONCHAN), "bench": list(opponent_bench), "hand": list(opponent_hand),
            "deck": list(opponent_deck if opponent_deck is not None else [W] * 10), "discard": list(opponent_discard), "prizes": 6}
    return build_test_state([me, them], turn_number=turn, current_player=current)


def attack(state, index=0, *coins):
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UseAttack(state.current_player, index))


def answer(state, choices, *coins):
    d = state.decision
    return apply_kernel(with_coin_results(state, *coins) if coins else state, ResolveDecision(d.player, d.id, tuple(choices)))


def same_answers(test, state, choices, *coins):
    """待っている決定のある状態を clone・deepcopy・pickle しても、同じ答え（と同じコインの結果）で同じ結果になる。"""
    expected = answer(state, choices, *coins)
    for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
        test.assertEqual(snap(answer(other, choices, *coins)), snap(expected))
    return expected


def uid(state, card_id, player=0, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def attach(state, card_id, target, player=None):
    """手札からつける通常の操作（``target`` は場のポケモン）。"""
    player = state.current_player if player is None else player
    return apply_kernel(state, AttachEnergy(player, uid(state, card_id, player), target.card))


def kinds(before, after, *names):
    return [e["kind"] for e in new_events(before, after, *names)]


def shocked(defender=None, *, hand=(W, W), bench=(H.RATTATA,), condition="paralysis", coins=()):
    """自分（プレイヤー 0）のユンゲラー（エナジーショック）かクロバット（しこみどく）が相手の ``defender`` にワザを使い、相手の番になった盤面（相手の手札 ``hand``）。"""
    user = mon(KADABRA, (PS, PS)) if condition == "paralysis" else mon(CROBAT, (G, G, W))
    state = board(user, opponent=defender or mon(H.LAPRAS), opponent_hand=hand, opponent_bench=bench)
    after = attack(state, 1 if condition == "paralysis" else 0, *coins)
    if after.current_player != 1:
        raise AssertionError("ワザのあとに相手の番になっていない")
    return after


# ---------------------------------------------------------------- 1. 登録と文面


class RegistrationTest(unittest.TestCase):
    """2 章: 13 枚の 25 ワザの登録・全文・引数、写し・採用の記録・研究の対応表。"""

    def test_registrations_are_exactly_the_expected_types(self):
        pool = load_card_pool()
        for (card, index), effect in EXPECTED.items():
            with self.subTest(card=card, index=index):
                definition = pool.definitions[card]
                attack_ = definition.attacks[index]
                self.assertEqual(DEFAULT_EFFECTS.attack_entry(card, index).effect, effect)
                self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card, attack_, definition.attacks))
                self.assertTrue(definition.supported)
        self.assertEqual({key.card_id for key in DEFAULT_EFFECTS.attack_keys() if key.card_id in V0116}, set(V0116))
        self.assertEqual(sum(1 for key in DEFAULT_EFFECTS.attack_keys() if key.card_id in V0116), 25)

    def test_play_text_is_the_printed_text(self):
        pool = load_card_pool()
        for card, index in EXPECTED:
            entry = DEFAULT_EFFECTS.attack_entry(card, index)
            text = pool.definitions[card].attacks[index].text_ja
            with self.subTest(card=card, index=index):
                self.assertEqual(entry.text_ja, text)
                self.assertEqual(entry.play_text_ja, text)
                self.assertEqual(entry.source, None if text is None else "kyuura data/cards.json")

    def test_same_data_pair_shares_the_registration(self):
        self.assertEqual(dict(E.SAME_DATA_CARDS_V0_116), {KADABRA_Q: KADABRA})
        for index in (0, 1):
            self.assertIs(DEFAULT_EFFECTS.attack_entry(KADABRA_Q, index), DEFAULT_EFFECTS.attack_entry(KADABRA, index))
        cards = {c["id"]: c for c in read_extract()["cards"]}
        fields = lambda c: (c["name"]["ja"], c["pokemon"]["hp"], c["pokemon"]["stage"], c["pokemon"]["types"], c["pokemon"]["weaknesses"],
                            c["pokemon"]["resistances"], c["pokemon"]["retreat_cost"], [(a["name"]["ja"], a["cost"], a["damage"], a["text"]["ja"]) for a in c["pokemon"]["attacks"]])
        self.assertEqual(fields(cards[KADABRA]), fields(cards[KADABRA_Q]))

    def test_rejected_variants_are_not_accepted_by_nearby_types(self):
        """名前の近い既存の型に渡すと拒否される（マヒの型・控えから集める型）。文面の違う 3 つは、その全文 1 通りだけを加えた（ほかの書き方を受け付けない）。"""
        pool = load_card_pool()
        cross = pool.definitions[CROBAT].attacks[1]
        self.assertTrue(E.CoinsTimesDamageThenParalyzeIfAtLeast(4, 20, 2).check(cross))
        trans = pool.definitions[ALAKAZAM_PR].attacks[1]
        self.assertTrue(E.MoveOwnCountersToOpponent().check(trans))
        self.assertIn(E.MULTIPLY_OR_FAIL_TEXT.format(name="ハネッコ"), (pool.definitions[HOPPIP].attacks[1].text_ja,))
        self.assertEqual(E.FLY_TEXTS[-1], pool.definitions[PIDGEOTTO].attacks[1].text_ja)
        water = pool.definitions[POLIWHIRL].attacks[1]
        self.assertEqual(water.text_ja, E.EXTRA_ENERGY_PIECES_TEXT.format(t="水", n=10, m=2))
        self.assertIn(EnergyType.COLORLESS, water.cost)  # 水水無色: 多いエネルギーの数え方は HC4（水だけの型にしない）

    def test_adoption_records_and_research_links(self):
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        for card in V0116:
            record = sources[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]), ("kyuura_data", "adopted", COMMIT))
                self.assertEqual(record["kyuura_records"], ["UQ-NEO-TEXT-BABY-CATEGORIES"] if card == DARK_OMASTAR else [])
                self.assertEqual(record["external_checks"], [])
        printed = {f"{card}/attack/{index}" for (card, index), effect in EXPECTED.items() if effect is not E.DAMAGE_ONLY}
        self.assertEqual(len(printed), 23)
        self.assertTrue(printed <= set(links["latest_descriptions"]["adopted_printed_text"]))
        self.assertEqual(links["stop_codes"]["UNRESOLVED_ATTACH_TRIGGER_SCOPE"]["engine_rulings"],
                         [{"version": "v0.116", "document": "docs/energy-movement-attachment-devolution-v0.116.md", "ruling_id": "AT1"}])
        case = next(c for c in links["kyuura_cases_without_engine_ruling"]["cases"] if c["card_id"] == DARK_OMASTAR)
        self.assertEqual(case["engine"], {"stop_codes": ["UNRESOLVED_NEO_TEXT_EVOLUTION_CARD_BABY"]})

    def test_text_eras_of_the_new_readers(self):
        self.assertEqual(E.TEXT_ERAS[DARK_OMASTAR], E.TEXT_NEO)
        self.assertEqual(E.TEXT_ERAS[WEEPINBELL], E.TEXT_PRE_NEO)

    def test_catalog_slices(self):
        extract = read_extract()
        self.assertEqual(set(extract["pool_v0_116"]), set(V0116))
        self.assertEqual(cards_after(extract, "0.115") - cards_after(extract, "0.116"), set(V0116))  # あとの版の組を除いて切り出す
        self.assertFalse(set(V0116) & cards_before(extract, "0.116"))


# ---------------------------------------------------------------- 2. ついた時に発動するワザの持続効果（4 章）


class AttachTriggerTest(unittest.TestCase):
    """4 章: しこみどく・エナジーショックの持続する効果。ワザを受けたときは特殊状態にせず、次の相手の番にエネルギーカードがつくたびにはたらく。"""

    def test_the_attack_gives_the_effect_but_no_condition_now(self):
        for condition in ("poison", "paralysis"):
            with self.subTest(condition=condition):
                after = shocked(condition=condition)
                defender = after.players[1].active
                effects = [e for e in defender.persistent_effects if isinstance(e, StatusOnEnergyAttach)]
                self.assertEqual([(e.condition, e.active_turn, e.created_turn) for e in effects], [(condition, TURN + 1, TURN)])
                self.assertEqual(defender.conditions.names(), ())
                self.assertEqual(defender.damage, 20)
                audited(self, after)

    def test_normal_attach_triggers_and_a_second_attach_in_the_same_turn_triggers_again(self):
        """手札からつける通常の操作 → どく。同じ番のあまごい（2 枚目）でももう一度はたらく（どくは重ならない。効果は 1 度で消えない）。"""
        state = shocked(mon(H.LAPRAS), hand=(W, W), bench=(mon(H.BLASTOISE),), condition="poison")
        first = attach(state, W, state.players[1].active)
        self.assertEqual(kinds(state, first, "attach_status_triggered", "special_condition"), ["attach_status_triggered", "special_condition"])
        self.assertEqual(first.players[1].active.conditions.names(), ("poison",))
        blastoise = first.players[1].bench[0]
        second = apply_kernel(first, UsePokemonPower(1, blastoise.pokemon_id, 0, uid(first, W, 1), None, first.players[1].active.pokemon_id))
        triggered = new_events(first, second, "attach_status_triggered")
        self.assertEqual([e["energy"] for e in triggered], [second.players[1].active.energy[-1]])
        self.assertEqual(second.players[1].active.conditions.names(), ("poison",))
        self.assertTrue(any(isinstance(e, StatusOnEnergyAttach) for e in second.players[1].active.persistent_effects))
        audited(self, second)

    def test_the_effect_expires_and_ends_on_evolution(self):
        from kyuura_engine import EndTurn

        state = shocked(mon(H.CHARMANDER), hand=(W, H.CHARMELEON, W), bench=(H.RATTATA,))
        ended = apply_kernel(state, EndTurn(1))
        removed = new_events(state, ended, "persistent_effect_removed")
        self.assertEqual([(e["persistent_effect"], e["reason"]) for e in removed], [("status_on_energy_attach", "expired")])
        evolved = apply_kernel(state, EvolvePokemon(1, uid(state, H.CHARMELEON, 1), state.players[1].active.pokemon_id))
        self.assertFalse(evolved.players[1].active.persistent_effects)
        after = attach(evolved, W, evolved.players[1].active)
        self.assertEqual(kinds(evolved, after, "attach_status_triggered", "special_condition"), [])

    def test_damage_only_prevention_still_gives_the_effect_but_evasion_does_not(self):
        """ダメージだけを受けない状態（かたまる）は効果を受ける。「とうめい」の「おもて」はワザを受けない（ダメージも効果もない）。"""
        prevented = shocked(mon(H.HITMONCHAN, prevent_damage=TURN - 1))
        self.assertEqual(prevented.players[1].active.damage, 0)
        self.assertTrue(any(isinstance(e, StatusOnEnergyAttach) for e in prevented.players[1].active.persistent_effects))
        evaded = shocked(mon(H.HAUNTER, (PS,)), coins=(HD,))
        self.assertFalse(evaded.players[1].active.persistent_effects)
        hit = shocked(mon(H.HAUNTER, (PS,)), coins=(TL,))
        self.assertTrue(any(isinstance(e, StatusOnEnergyAttach) for e in hit.players[1].active.persistent_effects))

    def test_a_knocked_out_defender_gets_no_effect(self):
        state = board(mon(KADABRA, (PS, PS)), opponent=mon(H.SHELLDER, damage=20))
        after = attack(state, 1)
        self.assertFalse([e for e in after.log if e.get("persistent_effect") == "status_on_energy_attach"])


class AttachOrderTest(unittest.TestCase):
    """4 章: エナジーショックとなんでもなおし配合エネルギー（GR-2000-P325-SAME-TIMING の例）。番のプレイヤーが順番を決め、回復 → マヒとマヒ → 回復で結果が違う。"""

    def test_order_decides_whether_the_pokemon_stays_paralyzed(self):
        state = shocked(hand=(FULL_HEAL, W))
        attached = attach(state, FULL_HEAL, state.players[1].active)
        d = attached.decision
        self.assertEqual((d.kind, d.player, d.options), (REACTION_ORDER, 1, (0, 1)))
        order = d.context_value(R.REACTION)[2]
        self.assertEqual([r[0] for r in order], [R.ENERGY, R.ATTACH_STATUS])
        cure_first = same_answers(self, attached, (0,))
        self.assertTrue(cure_first.players[1].active.conditions.paralyzed)
        paralysis_first = same_answers(self, attached, (1,))
        self.assertFalse(paralysis_first.players[1].active.conditions.paralyzed)
        self.assertEqual(kinds(attached, paralysis_first, "special_condition", "special_conditions_removed"), ["special_condition", "special_conditions_removed"])
        for after in (cure_first, paralysis_first):
            audited(self, after)

    def test_invalid_answers_do_not_change_the_waiting_state(self):
        state = shocked(hand=(FULL_HEAL, W))
        attached = attach(state, FULL_HEAL, state.players[1].active)
        d = attached.decision
        for choices in ((2,), (0, 1), ()):
            with self.subTest(choices=choices):
                before = snap(attached)
                with self.assertRaises(IllegalActionError):
                    apply_kernel(attached, ResolveDecision(d.player, d.id, choices))
                self.assertEqual(snap(attached), before)

    def test_heal_on_attach_and_paralysis_by_hand_and_by_other_routes(self):
        """［ほのおでかいふく］（つけたカードが炎）とマヒ: 手札からなら順番の決定（マヒを先にすると、回復がはたらくかが変わるので RA2）。ほかの経路ではエンジンの未対応で止める。"""
        state = shocked(mon(H.BLAINES_NINETALES, (FR,), damage=30), hand=(FR, W))
        attached = attach(state, FR, state.players[1].active)
        order = attached.decision.context_value(R.REACTION)[2]
        self.assertEqual([r[0] for r in order], [R.HEAL, R.ATTACH_STATUS])
        heal_first = answer(attached, (0,))
        self.assertEqual((heal_first.players[1].active.damage, heal_first.players[1].active.conditions.paralyzed), (40, True))
        with self.assertRaises(UnsupportedError) as caught:
            answer(attached, (1,))
        self.assertEqual(caught.exception.code, R.REACTION_CONDITION_CHANGED_CODE)
        ninetales = state.players[1].active
        self.assertEqual(E.attach_trigger_problem(state, ninetales, uid(state, FR, 1), moved=False, how="x")[0], E.ATTACH_TRIGGER_ORDER_CODE)
        self.assertIsNone(E.attach_trigger_problem(state, ninetales, uid(state, W, 1), moved=False, how="x"))
        poisoned = shocked(mon(H.BLAINES_NINETALES, (FR,), damage=30), hand=(FR, W), condition="poison")
        self.assertIsNone(E.attach_trigger_problem(poisoned, poisoned.players[1].active, uid(poisoned, FR, 1), moved=False, how="x"))


class AttachRoutesTest(unittest.TestCase):
    """4 章: つく入口。山札・トラッシュ・手札から新しくついたカードは「ついたとき」（ワザ・特殊能力の経路も）。場のつけ替え・［エネエネ］は AT1。手札からの反応は広げない。"""

    def test_belly_drum_by_the_affected_pokemon_triggers_for_each_card(self):
        """相手の番（効果がはたらく番）に、効果を受けたニョロゾが自分の「はらだいこ」で山札から 2 枚つける: 1 枚ずつマヒ（2 枚目は同じ番の 2 度目。回復する番は変わらない）。"""
        state = shocked(mon(POLIWHIRL, (W,)), hand=(), bench=(H.RATTATA,))
        used = attack(state, 0)
        self.assertEqual(used.decision.kind, ATTACH_FROM_DECK)
        done = answer(used, used.decision.options[:2])
        triggered = new_events(used, done, "attach_status_triggered")
        self.assertEqual([e["condition"] for e in triggered], ["paralysis", "paralysis"])
        audited(self, done)

    def test_field_moves_onto_the_affected_pokemon_stop_with_at1(self):
        state = shocked(mon(H.HITMONCHAN), hand=(), bench=(mon(H.VENUSAUR, (G,)),))
        venusaur = state.players[1].bench[0]
        command = UsePokemonPower(1, venusaur.pokemon_id, 0, venusaur.energy[0], venusaur.pokemon_id, state.players[1].active.pokemon_id)
        rejects(self, state, command, E.ATTACH_TRIGGER_SCOPE_CODE)
        self.assertEqual(QUESTIONS["attach_trigger_scope"].rulings, ("AT1",))

    def test_buzzap_target_holding_the_effect_is_a_stopped_choice(self):
        state = shocked(mon(H.LAPRAS), hand=(), bench=(mon(H.BUZZAP_ELECTRODE), H.RATTATA))
        electrode = state.players[1].bench[0]
        used = apply_kernel(state, UsePokemonPower(1, electrode.pokemon_id, 0))
        stops = {pid: code for pid, code, _ in used.decision.context_value("unresolved_detail", ())}
        self.assertEqual(stops.get(state.players[1].active.pokemon_id), E.ATTACH_TRIGGER_SCOPE_CODE)

    def test_moving_rainbow_energy_does_not_repeat_the_hand_effect(self):
        """場のつけ替え（バトンタッチ）でレインボーエネルギーを動かしても、手札から出したときの 10 ダメージは起こらない（CR-ENERGY-TRANS-NOT-ATTACHMENT の範囲）。"""
        state = board(mon(LEDIAN, (G, G, RAINBOW)), bench=(mon(LEDYBA),))
        used = attack(state, 0)
        moved = answer(used, (state.players[0].bench[0].pokemon_id,))
        self.assertEqual(moved.players[0].active.damage, 0)
        self.assertEqual(len(new_events(used, moved, "attack_attach_energy")), 3)

    def test_every_route_calls_the_common_entry(self):
        """``effects.after_energy_attached`` を直接呼ぶのは、手札からつける経路（v0.85 までの 1 枚ずつの処理・あまごい。ついた時の持続効果は ``reactions`` が処理する）と、共通の入口
        ``energy_attached_by_effect`` だけ（ほかの経路が持続効果を見落とさない）。"""
        import kyuura_engine.engine as engine_module

        callers = set()
        for module in (E, P, engine_module, R):
            current = None
            for line in inspect.getsource(module).splitlines():
                found = re.match(r"(?:class|def) (\w+)", line)
                if found:
                    current = found.group(1)
                if "after_energy_attached(" in line and not line.lstrip().startswith(("def ", "#")) and "``" not in line:
                    callers.add((module.__name__, current))
        self.assertEqual(callers, {("kyuura_engine.effects", "AttachEnergyFromHand"), ("kyuura_engine.effects", "energy_attached_by_effect"),
                                   ("kyuura_engine.engine", "_attach_energy")})


# ---------------------------------------------------------------- 3. 付け替えと付属カードの移動（5 章）


class BatonPassTest(unittest.TestCase):
    """5 章: バトンタッチ。草の控えを選び、すべてのエネルギーカードを 1 匹に付け替えてから入れ替える。"""

    def test_all_cards_move_to_the_chosen_pokemon_then_switch(self):
        state = board(mon(LEDIAN, (G, G, DCE)), bench=(H.RATTATA, mon(LEDYBA), mon(H.BULBASAUR, (G,))))
        used = attack(state, 0)
        d = used.decision
        self.assertEqual((d.kind, d.options), (SELECT_POKEMON, (state.players[0].bench[1].pokemon_id, state.players[0].bench[2].pokemon_id)))
        cards = tuple(state.players[0].active.energy)
        target = state.players[0].bench[2].pokemon_id
        done = same_answers(self, used, (target,))
        new_active = done.players[0].active
        self.assertEqual(new_active.pokemon_id, target)
        self.assertEqual(tuple(new_active.energy), (state.players[0].bench[2].energy[0], *cards))
        self.assertEqual({done.cards[u].owner for u in cards}, {0})
        self.assertEqual(kinds(used, done, "attack_attach_energy", "switch")[-1], "switch")
        self.assertEqual(done.energy_attachments_this_turn, state.energy_attachments_this_turn)
        self.assertFalse(new_events(used, done, "retreat", "discard_energy"))
        audited(self, done)

    def test_no_grass_bench_means_no_move_and_no_switch(self):
        state = board(mon(LEDIAN, (G, G)), bench=(H.RATTATA,))
        used = attack(state, 0)
        self.assertEqual(used.players[0].active.card, state.players[0].active.card)
        self.assertEqual(len(used.players[0].active.energy), 2)
        self.assertEqual([e["reason"] for e in new_events(state, used, "effect_skipped")], ["no_target"])
        audited(self, used)

    def test_the_type_is_the_current_type_when_choosing(self):
        """選べるのは選ぶ時の今のタイプが「草」の控え（印刷のタイプ・名前で固定しない）。ほかのタイプの控えは選べない。"""
        state = board(mon(LEDIAN, (G, G)), bench=(mon(LEDYBA), H.RATTATA, mon(H.BULBASAUR)))
        options, stops = E.baton_pass_targets(state, 0, EnergyType.GRASS)
        self.assertEqual((options, stops), ((state.players[0].bench[0].pokemon_id, state.players[0].bench[2].pokemon_id), ()))

    def test_trans_damage_copied_uses_the_copier(self):
        """ピッピが「ゆびをふる」でトランスダメージを使う: トラッシュするのはピッピのエネルギーカード、のせかえるのはピッピのカウンター（借りたワザの元のカード側を参照しない）。"""
        state = board(mon(H.CLEFAIRY, (W, W, W), damage=20), opponent=mon(ALAKAZAM_PR, (PS,), damage=30))
        done = answer(attack(state, 1), (1,))
        self.assertEqual((done.players[0].active.damage, done.players[0].active.energy), (0, []))
        self.assertEqual((done.players[1].active.damage, len(done.players[1].active.energy)), (50, 1))
        audited(self, done)


class EnergyCycleTest(unittest.TestCase):
    """5 章: エナジーサイクル。控えなしは明記された失敗（コインを投げない）。「うら」は失敗ではない。特殊エネルギーも選べる。"""

    def test_no_bench_fails_without_a_coin(self):
        state = board(mon(XATU, (PS,)), opponent=mon(H.LAPRAS, (W,)), opponent_bench=())
        used = attack(state, 0)
        self.assertEqual([e["reason"] for e in new_events(state, used, "attack_failed")], [E.ENTANGLE_NO_BENCH])
        self.assertFalse(new_events(state, used, "coin_flip"))

    def test_tails_does_nothing_and_is_not_a_failure(self):
        state = board(mon(XATU, (PS,)), opponent=mon(H.LAPRAS, (W,)))
        used = attack(state, 0, TL)
        self.assertFalse(new_events(state, used, "attack_failed", "move_opponent_energy"))
        self.assertEqual(len(used.players[1].active.energy), 1)

    def test_heads_moves_a_special_energy_card_to_the_bench(self):
        state = board(mon(XATU, (PS,)), opponent=mon(H.LAPRAS, (W, DCE)))
        used = attack(state, 0, HD)
        dce = state.players[1].active.energy[1]
        self.assertEqual((used.decision.kind, used.decision.options), (MOVE_OPPONENT_ENERGY, tuple(state.players[1].active.energy)))
        chosen = answer(used, (dce,))
        done = answer(chosen, (state.players[1].bench[0].pokemon_id,))
        self.assertIn(dce, done.players[1].bench[0].energy)
        self.assertEqual(done.cards[dce].owner, 1)
        audited(self, done)

    def test_no_energy_means_no_coin(self):
        state = board(mon(XATU, (PS,)), opponent=mon(H.LAPRAS))
        used = attack(state, 0)
        self.assertFalse(new_events(state, used, "coin_flip", "attack_failed"))


class EnergyControlTest(unittest.TestCase):
    """5 章: エナジーコントロール。「うら」は失敗。相手の場全体の基本エネルギーカードから選び、相手の場のポケモン（はがしたポケモン自身も）につける。"""

    def test_tails_fails(self):
        state = board(mon(MEWTWO_PR, (PS,)), opponent=mon(H.LAPRAS, (W,)))
        used = attack(state, 0, TL)
        self.assertEqual([e["reason"] for e in new_events(state, used, "attack_failed")], ["coin"])

    def test_bench_cards_and_any_destination(self):
        state = board(mon(MEWTWO_PR, (PS,)), opponent=mon(H.LAPRAS, (W, DCE)), opponent_bench=(mon(H.RATTATA, (FR,)),))
        used = attack(state, 0, HD)
        bench_fire = state.players[1].bench[0].energy[0]
        self.assertEqual(used.decision.options, (state.players[1].active.energy[0], bench_fire))  # 特殊エネルギー（無色2個）は選べない
        chosen = answer(used, (bench_fire,))
        self.assertEqual(chosen.decision.options, tuple(p.pokemon_id for p in state.players[1].in_play()))
        same = answer(chosen, (state.players[1].bench[0].pokemon_id,))
        self.assertEqual(same.players[1].bench[0].energy, [bench_fire])
        moved = answer(chosen, (state.players[1].active.pokemon_id,))
        self.assertIn(bench_fire, moved.players[1].active.energy)
        self.assertEqual(moved.energy_attachments_this_turn, state.energy_attachments_this_turn)
        audited(self, moved)

    def test_rainbow_on_the_field_is_a_stopped_choice(self):
        state = board(mon(MEWTWO_PR, (PS,)), opponent=mon(H.LAPRAS, (W, RAINBOW)))
        used = attack(state, 0, HD)
        rainbow = state.players[1].active.energy[1]
        self.assertEqual(used.decision.context_value("unresolved_choices"), (rainbow,))
        rejects(self, used, ResolveDecision(0, used.decision.id, (rainbow,)), E.RAINBOW_BASIC_CODE)


class TwisterTest(unittest.TestCase):
    """5 章: ツイスター。相手がきぜつしなければコイン。「おもて」なら、ついているエネルギーカードとトレーナーカードを持ち主の手札に（トラッシュを通さない）。"""

    def test_heads_returns_energy_and_trainers_to_the_owners_hand(self):
        state = board(mon(PIDGEOTTO, (W, W)), opponent=mon(H.LAPRAS, (W, RECYCLE), trainers=[(H.DEFENDER, TURN)]))
        cards = tuple(state.players[1].active.energy)
        trainer = state.players[1].active.trainers[0].card
        used = attack(state, 0, HD)
        self.assertEqual(used.players[1].active.energy, [])
        self.assertEqual(used.players[1].active.trainers, [])
        self.assertTrue(set(cards) | {trainer} <= set(used.players[1].hand))
        self.assertFalse(new_events(state, used, "discard_energy", "energy_returned_to_hand"))
        self.assertEqual(used.players[1].active.card, state.players[1].active.card)
        audited(self, used)

    def test_tails_or_knocked_out_or_nothing_attached(self):
        state = board(mon(PIDGEOTTO, (W, W)), opponent=mon(H.LAPRAS, (W,)))
        tails = attack(state, 0, TL)
        self.assertEqual(len(tails.players[1].active.energy), 1)
        knocked = attack(board(mon(PIDGEOTTO, (W, W)), opponent=mon(H.SHELLDER, (W,), damage=20)), 0)
        self.assertFalse([e for e in knocked.log if e["kind"] == "coin_flip" and e.get("source") == "attack"])
        bare = board(mon(PIDGEOTTO, (W, W)), opponent=mon(H.LAPRAS))
        self.assertFalse(new_events(bare, attack(bare, 0), "coin_flip"))

    def test_brocks_protection_keeps_the_energy(self):
        state = board(mon(PIDGEOTTO, (W, W)), opponent=mon(H.LAPRAS, (W,), trainers=[(H.BROCKS_PROTECTION, None)]))
        used = attack(state, 0, HD)
        self.assertEqual(len(used.players[1].active.energy), 1)
        self.assertEqual(used.players[1].active.trainers, [])


# ---------------------------------------------------------------- 4. 退化・配置・カウンター（6 章）


class PrimalDropTest(unittest.TestCase):
    """6 章: げんしのしずく。「おもて」なら相手の場の進化ポケモンのいちばん上の進化カードを相手の山札にもどして退化させ、山札を切る。"""

    def test_heads_returns_the_top_card_to_the_owners_deck(self):
        state = board(mon(DARK_OMASTAR, (W,)), opponent=mon(H.LAPRAS), opponent_bench=(mon(LEDIAN, damage=50),), opponent_deck=[W] * 3)
        used = attack(state, 0, HD)
        ledian = state.players[1].bench[0]
        self.assertEqual((used.decision.kind, used.decision.options), (SELECT_POKEMON, (ledian.pokemon_id,)))
        done = same_answers(self, used, (ledian.pokemon_id,))
        self.assertIn(ledian.card, done.players[1].deck)
        self.assertNotIn(ledian.card, done.players[1].hand + done.players[1].discard)
        self.assertEqual(kinds(used, done, "devolve", "shuffle", "knock_out")[:2], ["devolve", "shuffle"])
        self.assertEqual(new_events(used, done, "devolve")[0]["destination"], "deck")
        self.assertIn("knock_out", kinds(used, done))  # レディバ（HP 40）にダメージ 50 がのったまま（ワザのあとのきぜつの判定）
        audited(self, done)

    def test_tails_or_no_evolved_pokemon(self):
        state = board(mon(DARK_OMASTAR, (W,)), opponent=mon(LEDIAN))
        self.assertFalse(new_events(state, attack(state, 0, TL), "devolve"))
        bare = board(mon(DARK_OMASTAR, (W,)), opponent=mon(H.LAPRAS))
        self.assertFalse([e for e in attack(bare, 0).log[len(bare.log):] if e["kind"] == "coin_flip" and e.get("source") == "attack"])

    def test_evolved_baby_is_a_stopped_choice_and_own_side_is_not_selectable(self):
        state = board(mon(DARK_OMASTAR, (W,)), bench=(mon(LEDIAN),), opponent=mon(PIKACHU, evolved_from=[PICHU]), opponent_bench=(mon(LEDIAN),))
        used = attack(state, 0, HD)
        pikachu, ledian = state.players[1].active, state.players[1].bench[0]
        self.assertEqual(used.decision.options, (pikachu.pokemon_id, ledian.pokemon_id))
        self.assertEqual(used.decision.context_value("unresolved_choices"), (pikachu.pokemon_id,))
        rejects(self, used, ResolveDecision(0, used.decision.id, (pikachu.pokemon_id,)), E.NEO_EVOLUTION_CARD_BABY_CODE)


class DarkTentacleTest(unittest.TestCase):
    """6 章: やみのしょくしゅ。次の相手の番、手札・トレーナーの効果で進化させられない。ワザ・特殊能力の進化は止めない。"""

    def locked(self, defender, hand=()):
        state = board(mon(DARK_OMASTAR, (W, W)), opponent=defender, opponent_hand=hand)
        after = attack(state, 1)
        self.assertTrue(any(isinstance(e, EvolutionLock) for e in after.players[1].active.persistent_effects))
        return after

    def test_hand_and_trainer_evolution_are_prevented(self):
        from kyuura_engine.evolution import evolution_block

        state = self.locked(mon(H.BULBASAUR), hand=(H.IVYSAUR, H.POKEMON_BREEDER, H.VENUSAUR))
        target = state.players[1].active
        rejects(self, state, EvolvePokemon(1, uid(state, H.IVYSAUR, 1), target.pokemon_id), "EVOLUTION_PREVENTED", error=IllegalActionError)
        ivysaur = state.card_def(uid(state, H.IVYSAUR, 1))
        self.assertEqual(evolution_block(state, target, ivysaur)[0], "EVOLUTION_PREVENTED")
        self.assertIsNone(evolution_block(state, target, ivysaur, from_deck=True))  # ワザ・特殊能力の効果（山札から重ねる）は止めない
        self.assertNotIn(target.pokemon_id, E.skip_evolution_pairs(state, 1))  # ポケモン育て屋さん（トレーナーの効果）は止める
        rejects(self, state, PlayTrainer(1, uid(state, H.POKEMON_BREEDER, 1)), "NO_EVOLUTION_TARGET", error=IllegalActionError)

    def test_power_evolution_is_allowed(self):
        """［エナジーしんか］（特殊能力。手札からつけた事実への反応で山札から重ねる）は、やみのしょくしゅの効果を受けていても進化させられる（進化したら効果は消える）。"""
        deck_state = board(mon(DARK_OMASTAR, (W, W)), opponent=mon(H.EEVEE_NEO2), opponent_hand=(FR,), opponent_deck=[W, "PMCG2-020", W])  # 相手の番の最初に山札の上の 1 枚を引く
        locked = attack(deck_state, 1)
        attached = attach(locked, FR, locked.players[1].active)
        self.assertEqual(attached.decision.kind, "reaction_power")
        used = answer(attached, (attached.players[1].active.pokemon_id,), HD)
        self.assertEqual(used.decision.kind, "search_deck")
        evolved = answer(used, used.decision.options[:1])
        self.assertEqual(evolved.cards[evolved.players[1].active.card].card_id, "PMCG2-020")
        self.assertFalse(evolved.players[1].active.persistent_effects)
        audited(self, evolved)

    def test_the_lock_ends_when_the_pokemon_leaves_the_active_spot(self):
        state = self.locked(mon(H.BULBASAUR), hand=(H.IVYSAUR, H.SWITCH))
        switched = apply_kernel(state, PlayTrainer(1, uid(state, H.SWITCH, 1)))
        if switched.decision is not None:
            switched = answer(switched, (switched.decision.options[0],))
        moved = next(p for p in switched.players[1].bench if p.card == state.players[1].active.card)
        self.assertFalse(moved.persistent_effects)
        evolved = apply_kernel(switched, EvolvePokemon(1, uid(switched, H.IVYSAUR, 1), moved.pokemon_id))
        self.assertEqual(evolved.cards[next(p for p in evolved.players[1].bench if p.pokemon_id == moved.pokemon_id).card].card_id, H.IVYSAUR)


class CallBackTest(unittest.TestCase):
    """6 章: よびもどす。相手のトラッシュのベイビィ・たねポケモンを、カウンター 1 個をのせた状態で相手のベンチに出す。相手のベンチに空きがなければ失敗。"""

    def test_places_the_card_on_the_opponents_bench_with_a_counter(self):
        state = board(mon(DARK_HAUNTER, (PS,)), opponent_discard=(H.RATTATA, PICHU, W, H.CHARMELEON))
        used = attack(state, 0)
        rattata, pichu = state.players[1].discard[0], state.players[1].discard[1]
        self.assertEqual((used.decision.kind, used.decision.player, used.decision.options), (BENCH_FROM_DISCARD, 0, (rattata, pichu)))
        done = same_answers(self, used, (pichu,))
        placed = done.players[1].bench[-1]
        self.assertEqual((placed.card, placed.damage, done.cards[pichu].owner), (pichu, 10, 1))
        logged = new_events(used, done, "bench_from_discard")[0]
        self.assertEqual((logged["player"], logged["by_player"], logged["counters"], logged["damage"]), (1, 0, 1, 10))
        self.assertFalse(new_events(used, done, "damage"))
        audited(self, done)

    def test_full_bench_fails_and_empty_discard_does_nothing(self):
        full = board(mon(DARK_HAUNTER, (PS,)), opponent_bench=(H.RATTATA,) * 5, opponent_discard=(H.RATTATA,))
        self.assertEqual([e["reason"] for e in new_events(full, attack(full, 0), "attack_failed")], ["opponent_bench_full"])
        empty = board(mon(DARK_HAUNTER, (PS,)), opponent_discard=(W,))
        self.assertEqual(kinds(empty, attack(empty, 0), "bench_from_discard_none"), ["bench_from_discard_none"])


class SurroundTest(unittest.TestCase):
    """7 章: とりかこむ。1 枚のコインで「おもて」ならねむり、「うら」なら次の相手の番の「にげる」の禁止（両方は与えない。「うら」は失敗ではない）。"""

    def test_one_coin_decides_one_effect(self):
        state = board(mon(DARK_HAUNTER, (PS, PS)), opponent=mon(H.LAPRAS, (W, W)))
        heads = attack(state, 1, HD)
        self.assertTrue(heads.players[1].active.conditions.asleep)
        self.assertFalse(heads.players[1].active.persistent_effects)
        tails = attack(state, 1, TL)
        self.assertFalse(tails.players[1].active.conditions.asleep)
        self.assertEqual([type(e) for e in tails.players[1].active.persistent_effects], [CannotRetreat])
        self.assertFalse(new_events(state, tails, "attack_failed"))
        lapras = tails.players[1].active
        rejects(self, tails, Retreat(1, tuple(lapras.energy[:2]), tails.players[1].bench[0].card), "RETREAT_PREVENTED", error=IllegalActionError)


class RegenerateTest(unittest.TestCase):
    """6 章: さいせい。ダメージカウンターをすべてとりのぞき、進化カードとエネルギーカードをすべてトラッシュしてたねポケモンにもどる（トレーナーは残す）。"""

    def test_heal_then_devolve_and_discard_energy(self):
        state = board(mon(WEEPINBELL, (G, RECYCLE), damage=40, trainers=[(H.DEFENDER, TURN + 1)]))
        used = attack(state, 0)
        me = used.players[0].active
        self.assertEqual((used.cards[me.card].card_id, me.damage, me.energy, len(me.trainers)), (BELLSPROUT_ES3, 0, [], 1))
        self.assertEqual(kinds(state, used, "remove_all_damage_counters", "devolve", "discard_energy")[:3], ["remove_all_damage_counters", "devolve", "discard_energy"])
        self.assertIn(state.players[0].active.energy[1], used.players[0].hand)  # リサイクルエネルギー（自分のワザでトラッシュに置かれた）は手札にもどる
        self.assertIn(state.players[0].active.card, used.players[0].discard)
        audited(self, used)

    def test_copied_by_a_pokemon_evolved_from_a_baby(self):
        """ピィから進化したピッピが「ゆびをふる」でさいせいを使う: 実際に使ったポケモン（ピッピ）の重なり・エネルギー・カウンターを使い（相手のウツドンのものではない）、ES3 の説明は
        ネオより前なので、ベイビィを進化させたたねポケモンカードも「進化カード」、ベイビィも「たねポケモン」（GR-2000-P325-PRE-NEO-BABY）としてピィにもどる。"""
        state = board(mon(H.CLEFAIRY, (W, W, W), evolved_from=["neo1-070"], damage=20), opponent=mon(WEEPINBELL, (G,), damage=10))
        used = attack(state, 1)
        done = answer(used, (0,))
        me = done.players[0].active
        self.assertEqual((done.cards[me.card].card_id, me.damage, me.energy, me.evolution_stack), ("neo1-070", 0, [], ()))
        self.assertEqual((done.players[1].active.damage, len(done.players[1].active.energy)), (10, 1))
        self.assertEqual(E.text_era(WEEPINBELL), E.TEXT_PRE_NEO)
        audited(self, done)


class TransDamageTest(unittest.TestCase):
    """6 章: トランスダメージ。エネルギーカードをすべてトラッシュ（HC1）し、自分のダメージカウンターをすべて相手にのせかえる（ダメージではない。CX1）。"""

    def test_moves_all_own_counters_without_damage_modifiers(self):
        state = board(mon(ALAKAZAM_PR, (PS, PS, PS), damage=50), opponent=mon(H.LAPRAS, trainers=[(H.DEFENDER, TURN)]))
        used = attack(state, 1)
        self.assertEqual((used.players[0].active.damage, used.players[0].active.energy), (0, []))
        self.assertEqual(used.players[1].active.damage, 50)  # ディフェンダーは減らさない（ダメージではない）
        self.assertFalse(new_events(state, used, "damage"))
        self.assertEqual(len(new_events(state, used, "discard_energy")), 3)
        audited(self, used)

    def test_zero_counters_and_protected_receiver_and_confusion(self):
        state = board(mon(ALAKAZAM_PR, (PS, PS, PS)), opponent=mon(H.LAPRAS))
        self.assertFalse(new_events(state, attack(state, 1), "place_damage_counters"))
        evading = board(mon(ALAKAZAM_PR, (PS, PS, PS), damage=30), opponent=mon(H.HAUNTER))
        rejects(self, evading, UseAttack(0, 1), "UNRESOLVED_COUNTER_TRANSFER_PROTECTED")
        confused = board(mon(ALAKAZAM_PR, (PS, PS, PS), damage=30, confusion=True), opponent=mon(H.LAPRAS))
        rejects(self, confused, UseAttack(0, 1), "UNRESOLVED_DISCARD_ENERGY_TIMING")


class BellyDrumTest(unittest.TestCase):
    """6 章: はらだいこ。ダメージカウンター 3 個（ダメージではない）→ 山札の基本エネルギーカードちょうど 2 枚を自分につけ、切る。"""

    def test_counters_are_not_damage_and_two_cards_are_attached(self):
        state = board(mon(POLIWHIRL, (W,), trainers=[(H.DEFENDER, TURN + 1)]), deck=[F, G, RAINBOW, W])
        used = attack(state, 0)
        self.assertEqual(used.players[0].active.damage, 30)  # ディフェンダーは減らさない
        rainbow = next(u for u in state.players[0].deck if state.cards[u].card_id == RAINBOW)
        self.assertNotIn(rainbow, used.decision.options)  # 山札のレインボーエネルギーは基本エネルギーカードではない
        self.assertEqual((used.decision.min_choices, used.decision.max_choices), (2, 2))
        done = same_answers(self, used, used.decision.options[:2])
        self.assertEqual(len(done.players[0].active.energy), 3)
        self.assertEqual(kinds(used, done, "shuffle"), ["shuffle"])
        self.assertEqual(done.energy_attachments_this_turn, state.energy_attachments_this_turn)
        audited(self, done)

    def test_boundaries(self):
        ko = board(mon(POLIWHIRL, (W,), damage=40), deck=[F, G])
        knocked = attack(ko, 0)
        self.assertFalse(new_events(ko, knocked, "attach_energy_from_deck", "shuffle"))
        self.assertIn("knock_out", kinds(ko, knocked))
        empty = board(mon(POLIWHIRL, (W,)), deck=[H.RATTATA, H.RATTATA])
        none = attack(empty, 0)
        self.assertEqual((none.decision.options, none.decision.min_choices, none.decision.max_choices), ((), 0, 0))
        short = board(mon(POLIWHIRL, (W,)), deck=[F, H.RATTATA])
        rejects(self, short, UseAttack(0, 0), "UNRESOLVED_STATED_CARDS_SHORT")


class SimpleAttacksTest(unittest.TestCase):
    """7 章: そのほかのワザ（既存の型・小さな拡張）。"""

    def test_cross_attack_uses_one_heads_count(self):
        state = board(mon(CROBAT, (G, G, W)), opponent=mon(H.LAPRAS))
        two = attack(state, 1, HD, TL, HD, TL)
        self.assertEqual((two.players[1].active.damage, two.players[1].active.conditions.confused), (40, True))
        one = attack(state, 1, HD, TL, TL, TL)
        self.assertEqual((one.players[1].active.damage, one.players[1].active.conditions.confused), (20, False))
        self.assertEqual(len([e for e in two.log[len(state.log):] if e["kind"] == "coin_flip"]), 4)

    def test_multiply_fails_when_the_bench_is_full(self):
        full = board(mon(HOPPIP, (G,)), bench=(H.RATTATA,) * 5, deck=[HOPPIP, W])
        self.assertEqual([e["reason"] for e in new_events(full, attack(full, 1), "attack_failed")], ["bench_full"])

    def test_water_gun_counts_extra_water_with_hc4(self):
        state = board(mon(POLIWHIRL, (W, W, W, W, W)), opponent=mon(H.LAPRAS))
        used = attack(state, 1)
        self.assertEqual(used.players[1].active.damage, 50)

    def test_fly_fails_on_tails_and_guards_on_heads(self):
        state = board(mon(PIDGEOTTO, (W, W, W)), opponent=mon(H.LAPRAS))
        self.assertEqual(attack(state, 1, TL).players[1].active.damage, 0)
        heads = attack(state, 1, HD)
        self.assertEqual(heads.players[1].active.damage, 30)
        self.assertEqual([e.kind for e in heads.players[0].active.persistent_effects], ["attack_barrier"])

    def test_telekinesis_and_psychic_panic(self):
        tele = board(mon(MEWTWO_PR, (PS, PS, PS)), opponent=mon(H.HITMONCHAN))
        used = attack(tele, 1)
        self.assertEqual(used.decision.options, tuple(p.pokemon_id for p in tele.players[1].in_play()))
        done = answer(used, (tele.players[1].active.pokemon_id,))
        self.assertEqual(done.players[1].active.damage, 30)  # 弱点（超）を計算しない
        panic = board(mon(ALAKAZAM_PR, (PS, PS)), opponent=mon(MEWTWO_PR))
        self.assertEqual([e["steps"][0] for e in new_events(panic, attack(panic, 0), "damage")], [("1 基本となる計算", 60)])

    def test_energy_recycle_and_pokemon_tower(self):
        state = board(mon(KADABRA, (PS,)), discard=(FULL_HEAL, W, DCE))
        used = attack(state, 0)
        self.assertEqual((used.decision.kind, len(used.decision.options)), (RECOVER_ENERGY, 2))
        towered = state.clone()
        tower = board(mon(KADABRA, (PS,)), discard=(FULL_HEAL,), hand=(H.POKEMON_TOWER,))
        played = apply_kernel(tower, PlayTrainer(0, uid(tower, H.POKEMON_TOWER)))
        suppressed = attack(played, 0)
        self.assertEqual(kinds(played, suppressed, "discard_to_hand_suppressed"), ["discard_to_hand_suppressed"])
        self.assertIsNotNone(towered)

    def test_yokai_discards_on_heads(self):
        state = board(mon(WEEPINBELL, (G, G)), opponent=mon(H.LAPRAS, (W,)))
        used = attack(state, 1, HD)
        done = answer(used, used.decision.options)
        self.assertEqual(done.players[1].active.energy, [])


# ---------------------------------------------------------------- 8. ESP・保存・監査・文書


class EspAndPsychoLinkTest(unittest.TestCase):
    """ナツメのフーディン（PMCG6-053）が、超の色マーカーをのせた控えのクロバットのワザを［サイコリンク］で使い、手札から通常の操作でつけたナツメのESPでやり直す（v0.113・v0.115 の
    ``esp_board`` と同じ手順）。クロスアタックは 4 枚のまとまりを投げ終えたあとに 1 回だけ聞き、ダメージとこんらんは、やり直したあとの同じ「おもて」の数で決める（docs 7 章）。"""

    @staticmethod
    def esp_board(energy=(G, G, G)):
        state = board(mon(V113.ALAKAZAM, energy, evolved_from=V113.BELOW[V113.ALAKAZAM]),
                      bench=(mon(CROBAT, markers=[(MARKER_COLOR, EnergyType.PSYCHIC)]),), opponent=mon(H.LAPRAS), hand=(V113.ESP_CARD,))
        played = apply_kernel(state, PlayTrainer(0, uid(state, V113.ESP_CARD)))
        return answer(played, (played.players[0].active.pokemon_id,))

    def test_cross_attack_redo_decides_damage_and_confusion_together(self):
        state = self.esp_board()
        card = V113.provider_card(state, CROBAT)
        asked = V113.attack(state, 1, HD, TL, TL, TL, card=card)
        self.assertEqual(asked.decision.kind, ESP_REDO)
        self.assertEqual(new_events(state, asked, "damage"), [])  # ダメージはコインのまとまりのあと
        for redo, coins, base, confused in (((), (), 20, []), ((1,), (HD, HD, HD, TL), 60, ["confusion"]), ((1,), (TL, TL, TL, TL), 0, [])):
            with self.subTest(redo=redo, coins=coins):
                after = same_answers(self, asked, redo, *coins)
                self.assertEqual([e["steps"][0][1] for e in new_events(asked, after, "damage")] or [0], [base])
                self.assertEqual([e["condition"] for e in new_events(asked, after, "special_condition")], confused)
                redone = new_events(asked, after, "esp_redo")
                self.assertEqual([(e["original"], e["redone"]) for e in redone],
                                 [(("heads", "tails", "tails", "tails"), tuple(c.value for c in coins))] if redo else [])
                audited(self, after)

    def test_poison_seed_through_psycho_link_records_the_user_and_the_attack(self):
        """［サイコリンク］で使ったしこみどくの効果の発生源は、実際に使ったナツメのフーディン（いちばん上のカード）、ワザはクロバットのワザ。"""
        state = self.esp_board()
        card = V113.provider_card(state, CROBAT)
        after = V113.attack(state, 0, card=card)
        while after.decision is not None:
            after = answer(after, ())  # ESP のやり直しを聞かれたら、やり直さない
        effect = next(e for e in after.players[1].active.persistent_effects if isinstance(e, StatusOnEnergyAttach))
        self.assertEqual((effect.source_card, effect.attack, effect.condition), (state.players[0].active.card, f"{CROBAT}#0", "poison"))
        audited(self, after)


class SaveAndObservationTest(unittest.TestCase):
    def test_format_unchanged_and_public_logs(self):
        """保存の形式は 26 のまま（新しい持続する効果の種類は ``effect`` と項目を書く。形式を上げない）。新しいログは公開（場・トラッシュ・手札にもどすカードは公開の情報）。"""
        self.assertIn(26, FORMAT_VERSIONS)  # この版で形式を上げていない。今の最新の形式は tests/test_catalog_contract.py（docs/testing.md）
        self.assertEqual(max(FORMAT_VERSIONS), LATEST_FORMAT)
        self.assertTrue({"attach_status_triggered", "attached_cards_to_hand"} <= PUBLIC_EVENTS)
        after = shocked(condition="poison")
        written = state_to_dict(after, format_version=26)
        effects = [e for e in written["players"][1]["active"]["persistent_effects"] if e["effect"] == "status_on_energy_attach"]
        self.assertEqual([(e["condition"], e["attack"]) for e in effects], [("poison", f"{CROBAT}#0")])
        locked = attack(board(mon(DARK_OMASTAR, (W, W)), opponent=mon(H.LAPRAS)), 1)
        written = state_to_dict(locked, format_version=26)
        self.assertEqual([e["effect"] for e in written["players"][1]["active"]["persistent_effects"]], ["evolution_lock"])
        audited(self, locked)

    def test_hidden_deck_choices_are_not_shown_to_the_opponent(self):
        """はらだいこの山札のカードの決定は、選ぶプレイヤーにだけ選べるものが見える（相手・観戦者には種類とプレイヤーだけ）。"""
        state = board(mon(POLIWHIRL, (W,)), deck=[W, G, F, W, PS])
        asked = attack(state, 0)
        self.assertEqual(asked.decision.kind, ATTACH_FROM_DECK)
        for viewer in (1, None):
            self.assertEqual(observe(asked, viewer)["decision"], {"kind": ATTACH_FROM_DECK, "player": 0})
        self.assertIn("options", observe(asked, 0)["decision"])
        audited(self, asked)

    def test_invariants_reject_a_wrong_effect(self):
        """不変条件: 登録のワザ・ログと合わない持続する効果（特殊状態の違うしこみどく）を見つける。"""
        import dataclasses

        after = shocked(condition="poison")
        broken = after.clone()
        defender = broken.players[1].active
        defender.persistent_effects = tuple(dataclasses.replace(e, condition="paralysis") if isinstance(e, StatusOnEnergyAttach) else e
                                            for e in defender.persistent_effects)
        self.assertTrue(check_invariants(broken))
        with self.assertRaises(ValueError):
            StatusOnEnergyAttach(source_card=1, source_player=0, created_turn=1, active_turn=2, condition="sleep", attack=f"{CROBAT}#0")


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v116_problems``）は、エンジンの登録・計算を読まずに、処理したワザの印刷の文面と、ログから組み立てた場・コイン・カードの動きで確かめる。
    エンジンの処理を一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py の局。開発用の seed 50・51。正式な対戦の seed 0〜3 とは別）で、監査がそれを見つける。"""

    GAMES = ((("G116", "P116"), 51), (("G116", "W116"), 50), (("C116", "G116"), 50), (("W116", "P116"), 51))

    @classmethod
    def problems_for(cls, patcher, *needles):
        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        found = []
        with patcher:
            for labels, seed in cls.GAMES:
                try:
                    result = games.play(labels, seed, keep_state=True)
                except Exception as error:  # noqa: BLE001  誤らせた処理が不変条件で止まっても、監査とは別の理由（ここでは数えない）
                    found.append(f"stopped: {error}") if "stopped" in needles else None
                    continue
                if result.get("state") is not None:
                    found += [p for p in log_problems(result["state"]) if any(n in p for n in needles)]
        return found

    def test_the_unpatched_games_pass_the_audit(self):
        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        used = set()
        for labels, seed in self.GAMES:
            result = games.play(labels, seed, keep_state=True)
            with self.subTest(labels=labels, seed=seed):
                self.assertIn(result["outcome"], ("game_over", "sudden_death"))
                self.assertEqual((result["audit"], log_problems(result["state"])), ({}, []))
            used |= {k[len("attack_"):] for k, v in result["v116"].items() if k.startswith("attack_") and v}
        self.assertTrue({f"{LEDIAN}#0", f"{WEEPINBELL}#0", f"{KADABRA}#1", f"{CROBAT}#0", f"{ALAKAZAM_PR}#1", f"{PIDGEOTTO}#0"} <= used)

    def test_audit_accepts_the_trigger_first_order(self):
        """手札からつけたレインボーエネルギーの 10 ダメージとエナジーショックのマヒ（同じ時点の反応）を、番のプレイヤーがマヒを先に処理する順番にしても、監査は誤りとしない
        （v0.58 の「つけたすぐあとの特殊エネルギーの効果」の確かめは、あいだのそのポケモン・そのカードの持続効果のログを許す。正式な対戦の P116 対 R58 の seed 0・1 で、この順番を
        監査が誤りとしたので直した。12.3 節）。開発用の seed 50 の C116 対 R58 で、順番の決定の答えだけを変える。"""
        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        original = games._v086_decision

        def status_first(state, counts):
            d = state.decision
            if d is not None and d.kind == REACTION_ORDER:
                names = [reaction[0] for reaction in d.context_value(R.REACTION)[2]]
                if R.ATTACH_STATUS in names:
                    return ResolveDecision(d.player, d.id, (names.index(R.ATTACH_STATUS),))
            return original(state, counts)

        with mock.patch.object(games, "_v086_decision", status_first):
            result = games.play(("C116", "R58"), 50, keep_state=True)
        log = result["state"].log
        self.assertTrue([i for i, e in enumerate(log) if e["kind"] == "energy_damage" and log[i - 1]["kind"] == "special_condition"
                         and log[i - 2]["kind"] == "attach_status_triggered"])
        self.assertEqual((result["outcome"], result["audit"], log_problems(result["state"])), ("game_over", {}, []))

    def test_audit_finds_missing_triggers_and_partial_moves(self):
        """ついた時の効果がはたらかない・バトンタッチで 1 枚だけ付け替えた。"""
        self.assertTrue(self.problems_for(mock.patch.object(E, "apply_attach_status", lambda *args, **kw: None), "attach_status_triggered がない"))
        original = P.BatonPass.resume

        def one_card(self, run, decision, choices):
            attacker = run.attacker()
            kept = list(attacker.energy[1:])
            del attacker.energy[1:]
            try:
                original(self, run, decision, choices)
            finally:
                attacker.energy.extend(kept)

        self.assertTrue(self.problems_for(mock.patch.object(P.BatonPass, "resume", one_card), "のすべてではない"))

    def test_audit_finds_wrong_counts(self):
        """さいせいでエネルギーカードを 1 枚残した・トランスダメージで 1 個少なくのせかえた・クロスアタックで「おもて」1 枚でもこんらんにした。"""
        original_regress = P.RegressToBasic.run

        def keep_one(self, run):
            attacker = run.attacker()
            kept = attacker.energy[:1]
            del attacker.energy[:1]
            try:
                return original_regress(self, run)
            finally:
                attacker.energy[:0] = kept

        self.assertTrue(self.problems_for(mock.patch.object(P.RegressToBasic, "run", keep_one), "トラッシュしたカード"))
        original_move = P.MoveAllSelfCountersToOpponent.run

        def one_less(self, run):
            attacker = run.attacker()
            if attacker.damage:
                attacker.damage -= run.state.rules.damage_per_counter
                try:
                    return original_move(self, run)
                finally:
                    attacker.damage += run.state.rules.damage_per_counter
            return original_move(self, run)

        self.assertTrue(self.problems_for(mock.patch.object(P.MoveAllSelfCountersToOpponent, "run", one_less), "のせかえた数"))
        confuse = {E.CoinsTimesDamageThenConfuseIfAtLeast: lambda e: (
            P.Coin("coin", count=e.coins), P.Damage(P.OPP, P.HeadsOfCoin("coin", e.per)), P.Status(P.CONFUSION, gate=("coin", P.AtLeast(1))))}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, confuse), "こんらん"))


class DocumentTest(unittest.TestCase):
    def test_document_records(self):
        text = DOC.read_text(encoding="utf-8")
        for word in ("AT1", "UNRESOLVED_ATTACH_TRIGGER_SCOPE", "UNSUPPORTED_ATTACH_TRIGGER_ORDER", "GR-2000-P325-SAME-TIMING", "GR-2000-P320-COUNTER-MOVE", "CX1", "HC1", "NB2",
                     "RB3", "FC1", "DV5", "T36", "CR-ENERGY-TRANS-NOT-ATTACHMENT", "UQ-NEO-TEXT-BABY-CATEGORIES", "SC-ES3-020", "1,289", "(88, 35, 53)", "489",
                     "## 12. 検証", "lockstep", "単体のテストだけ", "エンジンは画像を見ていない"):
            self.assertIn(word, text)
        for card in V0116:
            self.assertIn(card, text)
        v0115 = (ROOT / "docs" / "spread-damage-allocation-v0.115.md").read_text(encoding="utf-8")
        self.assertIn("6,408", v0115)  # v0.115 の全体のテストの記録はそのまま
        status = (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(int(re.search(r"^# 実装状況（v0\.1〜v0\.(\d+)）", status, re.MULTILINE).group(1)), 116)
        self.assertIn("## v0.116: エネルギーの付け替え・ついた時の効果・付属カードの回収と退化", status)
        self.assertRegex((ROOT / "README.md").read_text(encoding="utf-8"), r"\n- v0\.116（(今のエンジンの版。)?`kyuura_engine` の版は 0\.116\.0）: エネルギーの付け替え")
        self.assertIn("### v0.116: エネルギーの付け替え", (ROOT / "docs" / "rules-2000-02-14.md").read_text(encoding="utf-8"))
        self.assertIn("## v0.116: エネルギーの付け替え", (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
