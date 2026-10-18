"""v0.52: 場のポケモンを場から手札・山札にもどす共通の処理と、それを使う 3 枚（docs/field-return-v0.52.md）。

3 枚: フジろうじん（PMCG3-048。トレーナー）・ポケモン回収（PMCG1-092。トレーナー）・エリカのハクリュー（PMCG5-066。ふぶき・つれさる）。どれも kyuura データの採用
（処理に使う文面は kyuura の印刷の文面。採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合（3 枚とも match）。ガイドブックは読んでいない。英語版の
文面（「Shuffle it … into your deck」「return its Basic Pokémon card to your hand. (Discard all cards attached to that card.)」「Then, your opponent …」）で、日本語版の条件を
補わない。

根拠にした既存の記録（研究の基準のコミットの kyuura の記録。``research_links.json`` の ``applied_rule_records``）: GR-2000-P322-PERSISTENT-EFFECTS（場をはなれたら持続する効果は
消える）・GR-2000-P312-FIELD（手札・山札・トラッシュは場にふくまれない）と、エンジンの v0.36（``zones.return_in_play_to_deck``）・v0.38（フリーザーの「ふぶき」の型）・v0.42
（特殊能力のあとの勝ち負けの判定とバトル場に出す決定）・v0.47（なにかの化石）・v0.49（「ばける」・［へんしん］・思い出させる・［サイコリンク］）・v0.50（トレーナーのあとの
処理 ``resolution.after_trainer``）の記録。

新しい停止コードは 3: FJ1・SU1・SU2（docs 6 章）。
"""

from __future__ import annotations

import json
import pathlib
import unittest

from kyuura_engine import (
    EndTurn,
    EvolvePokemon,
    IllegalActionError,
    Phase,
    PlayBasicToBench,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    check_invariants,
    observe,
    state_to_dict,
    visible_log,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.decisions import PROMOTE_ACTIVE, SELECT_POKEMON
from kyuura_engine.observation import PUBLIC_EVENTS
from kyuura_engine.resolution import programs
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests.helpers import (
    AERODACTYL,
    ATTACK_TYPES_SINCE_V0_17,
    BROCKS_NINETALES,
    BROCKS_VULPIX,
    BULBASAUR,
    CHANSEY,
    CHARMELEON,
    CLEFAIRY,
    DARK_GLOOM,
    DARK_VILEPLUME,
    DEFENDER,
    DITTO,
    ERIKAS_DRAGONAIR,
    ERIKAS_DRATINI,
    FIGHTING,
    FIRE,
    GASTLY,
    HAUNTER,
    HITMONCHAN,
    IVYSAUR,
    MR_FUJI,
    MYSTERIOUS_FOSSIL,
    OMANYTE,
    PLUSPOWER,
    POKEMON_BREEDER,
    PSYCHIC,
    RATICATE,
    RATTATA,
    ROCKET_ODDISH,
    SCOOP_UP,
    V0_52_CARDS,
    V0_52_POKEMON,
    VENUSAUR,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import observation_problems, serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "field-return-v0.52.md"
TURN = 7
W, F = WATER, FIGHTING
FJ1 = "UNRESOLVED_MR_FUJI_WITHOUT_BENCH"
SU1 = "UNRESOLVED_SCOOP_UP_ATTACHED_TRAINER"
SU2 = "UNRESOLVED_SCOOP_UP_LAST_POKEMON"
NEW_CODES = (FJ1, SU1, SU2)
APPLIED_RECORDS = ("GR-2000-P322-PERSISTENT-EFFECTS", "GR-2000-P312-FIELD")
EDITIONS = {MR_FUJI: "047/048", SCOOP_UP: "087/096", ERIKAS_DRAGONAIR: "066/096"}
BELOW = {ERIKAS_DRAGONAIR: ERIKAS_DRATINI, RATICATE: RATTATA, IVYSAUR: BULBASAUR, BROCKS_NINETALES: BROCKS_VULPIX,
         DARK_VILEPLUME: [ROCKET_ODDISH, DARK_GLOOM], OMANYTE: MYSTERIOUS_FOSSIL}
BLIZZARD_TEXT = "コインを投げ、「おもて」なら相手の控えポケモン全員に、「うら」なら自分の控えポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。"


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def bench_spec(b):
    return mon(b) if isinstance(b, str) else b


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), hand=(), opponent_hand=(), deck=None, turn=TURN, current=0):
    me = {"active": active, "bench": [bench_spec(b) for b in bench], "hand": list(hand)}
    them = {"active": opponent or mon(HITMONCHAN, (F, F)), "bench": [bench_spec(b) for b in opponent_bench], "hand": list(opponent_hand)}
    if deck is not None:
        me["deck"] = list(deck)
    return build_test_state([me, them], turn_number=turn, current_player=current)


def dragonair(energy=(W, W, W, W), **extra):
    return mon(ERIKAS_DRAGONAIR, energy, **extra)


def full(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS))


def snapshot(state):
    return full(state), [dict(e) for e in state.log], repr(state.rng.getstate())


def answer(state, choices, player=None):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player if player is None else player, d.id, tuple(choices)))


def card_of(state, player, card_id, zone="hand"):
    return next(uid for uid in getattr(state.players[player], zone) if state.cards[uid].card_id == card_id)


def events(state, since, kind=None):
    return [e for e in state.log[since:] if kind is None or e["kind"] == kind]


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def assert_stops(test, state, command, code, error=UnsupportedError):
    before = snapshot(state)
    with test.assertRaises(error) as caught:
        apply_kernel(state, command)
    test.assertEqual(caught.exception.code, code)
    test.assertEqual(snapshot(state), before)


def cards_total(state):
    total = 0
    for p in state.players:
        total += len(p.hand) + len(p.deck) + len(p.discard) + len(p.prizes)
        for pokemon in p.in_play():
            total += len(pokemon.cards()) + len(pokemon.energy) + len(pokemon.trainers)
    if state.trainer_in_use is not None:
        total += 1
    return total


def use_trainer(state, card_id, player=0):
    return apply_kernel(state, PlayTrainer(player, card_of(state, player, card_id)))


# ---------------------------------------------------------------- 登録・資料


class RegistrationTest(unittest.TestCase):
    """3 枚の登録・写し・採用の記録・研究の対応表。"""

    def test_pool_and_registrations(self):
        pool = load_card_pool()
        for card_id in V0_52_CARDS:
            self.assertTrue(pool.definitions[card_id].supported, card_id)
        dragonair_def = pool.definitions[ERIKAS_DRAGONAIR]
        self.assertEqual([(a.name_ja, a.supported) for a in dragonair_def.attacks], [("ふぶき", True), ("つれさる", True)])
        self.assertEqual(V0_52_POKEMON, (ERIKAS_DRAGONAIR,))
        entries = E.DEFAULT_EFFECTS
        self.assertIsInstance(entries.trainer_entry(MR_FUJI).effect, E.ReturnBenchedPokemonToDeck)
        self.assertIsInstance(entries.trainer_entry(SCOOP_UP).effect, E.ReturnOwnPokemonBasicToHand)
        self.assertIsInstance(entries.attack_entry(ERIKAS_DRAGONAIR, 0).effect, E.DamageThenCoinBenchDamageEitherSide)
        self.assertIsInstance(entries.attack_entry(ERIKAS_DRAGONAIR, 1).effect, E.ReturnBothActivesToDeck)
        self.assertIn(E.ReturnBothActivesToDeck, ATTACK_TYPES_SINCE_V0_17)
        self.assertIn(E.ReturnBothActivesToDeck, programs.BUILDERS)
        self.assertEqual(json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text())["pool_v0_52"], list(V0_52_CARDS))

    def test_blizzard_text_variant(self):
        """ふぶきは v0.38 のフリーザーと同じ型。書き方（「コインを投げ、」・かっこのない「「弱点・抵抗力」に関係なく、」）を同じ意味として受け付ける。ほかの書き方は拒否する。"""
        attack = load_card_pool().definitions[ERIKAS_DRAGONAIR].attacks[0]
        self.assertEqual(attack.text_ja, BLIZZARD_TEXT)
        effect = E.DamageThenCoinBenchDamageEitherSide(10)
        self.assertEqual(effect.check(attack), [])
        for wrong in (BLIZZARD_TEXT.replace("「うら」なら自分", "「うら」なら相手"), BLIZZARD_TEXT.replace("「弱点・抵抗力」に関係なく、", ""),
                      BLIZZARD_TEXT.replace("10ダメージ", "20ダメージ")):
            self.assertNotEqual(effect.check(type(attack)(**{**attack.__dict__, "text_ja": wrong})), [], wrong)

    def test_card_sources_and_research_links(self):
        """採用の記録（kyuura_records は空。処理に使う文面は kyuura の印刷の文面）・pcg-search.com の照合（3 枚とも match。一覧の番号の違いは番号の体系の違い）・
        研究の対応表（新しい停止コード 3 は not_in_kyuura。ワザの 2 は adopted_printed_text。再利用した 2 つの記録は applied_rule_records）。"""
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text())["cards"]
        for card_id in V0_52_CARDS:
            record = sources[card_id]
            self.assertEqual((record["basis"], record["status"], record["kyuura_records"]), ("kyuura_data", "adopted", []))
            (check,) = record["external_checks"]
            self.assertEqual((check["site"], check["result"], check["edition"]["list_number"]), ("pcg-search.com", "match", EDITIONS[card_id]))
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text())
        for code in NEW_CODES:
            self.assertEqual(links["stop_codes"][code]["kyuura_disposition"], "not_in_kyuura")
            self.assertEqual(links["stop_codes"][code]["engine_rulings"][0]["document"], "docs/field-return-v0.52.md")
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (132, 134))  # v0.53 で ST1・NG1 を加えた、v0.55 で MW1・EM1・SP1・FH1・GL1・GL2・SB1・SB2 を加えた、v0.56 で LS1・RT1・RG1・MY1・MS1・KG1 を加えた、v0.57 で STB1・TG1・FG1・FG2・EX1・VG1・VM1・CH1、v0.58 で RB1〜RB4・TE2・RT1 を加えた、v0.59 で GG1・BL1・CB1・BZ1〜BZ4 を加えた。v0.60 で TS1 を加え、コードのない SS1 を数えた。v0.61 で SH1・SC1・SC2・TD1 を加え、Z9 に停止コードを付けた。v0.62 で MM1・MM2・OM1・OM2 を加え、コードのない ED1 を数えた
        self.assertTrue({"PMCG5-066/attack/0", "PMCG5-066/attack/1"} <= set(links["latest_descriptions"]["adopted_printed_text"]))
        applied = {r["kyuura_record"] for r in links["applied_rule_records"] if r["engine"][0]["version"] == "v0.52"}
        self.assertEqual(applied, set(APPLIED_RECORDS))

    def test_observation_tables(self):
        self.assertIn("return_basic_to_hand", PUBLIC_EVENTS)
        self.assertIn("return_in_play_to_deck", PUBLIC_EVENTS)

    def test_document_lists_the_new_codes(self):
        text = DOC.read_text()
        for code in NEW_CODES:
            self.assertIn(code, text)


# ---------------------------------------------------------------- フジろうじん


class MrFujiTest(unittest.TestCase):
    """フジろうじん: 自分の控えポケモンを 1 匹選び、そのカードとついているカード全てを自分の山札にもどし、切る（docs 3 章）。"""

    def test_returns_whole_stack_and_attachments_to_deck(self):
        """重なったカード・エネルギー・トレーナー（ディフェンダー）を、同じ uid のまま自分の山札にもどして切る。ダメージカウンター・持続する効果はなくなる。
        きぜつではない（サイドは取られない）。トレーナーのカードはトラッシュ。選べるのは自分の控えだけ（バトル場・相手のポケモンは選べない）。"""
        raticate = mon(RATICATE, (F,), damage=30, trainers=[(DEFENDER, TURN + 1)])
        state = board(mon(CHANSEY), bench=(raticate, RATTATA), hand=(MR_FUJI,))
        target = state.players[0].bench[0]
        cards = (*target.cards(), *target.energy, *(t.card for t in target.trainers))
        total = cards_total(state)
        deck_before = len(state.players[0].deck)
        state = use_trainer(state, MR_FUJI)
        self.assertEqual((state.decision.kind, state.decision.player), (SELECT_POKEMON, 0))
        self.assertEqual(state.decision.options, tuple(b.pokemon_id for b in state.players[0].bench))
        since = len(state.log)
        state = answer(state, [target.pokemon_id])
        self.assertEqual(state.phase, Phase.MAIN)
        self.assertIsNone(state.players[0].find_by_pokemon_id(target.pokemon_id))
        self.assertTrue(set(cards) <= set(state.players[0].deck))
        self.assertEqual(len(state.players[0].deck), deck_before + len(cards))
        self.assertEqual(cards_total(state), total)
        self.assertEqual(len(state.players[1].prizes), 6)
        self.assertEqual([e["kind"] for e in events(state, since)], ["return_in_play_to_deck", "shuffle", "discard_trainer"])
        returned = events(state, since, "return_in_play_to_deck")[0]
        self.assertEqual((returned["player"], returned["trainer_card"], returned["damage"], tuple(returned["cards"])),
                         (0, card_of(state, 0, MR_FUJI, "discard"), 30, cards))
        self.assertNotIn("effect", returned)
        self.assertNotIn("knock_out", [e["kind"] for e in state.log])
        audited(self, state)

    def test_disguise_and_fossil_go_with_the_stack(self):
        """「ばける」でのせたカード・なにかの化石の上の進化カードも、そのカードの一部としてもどす。"""
        state = board(mon(CHANSEY), bench=(mon(OMANYTE),), hand=(MR_FUJI, CHARMELEON))
        omanyte = state.players[0].bench[0]
        stack = omanyte.cards()
        state = answer(use_trainer(state, MR_FUJI), [omanyte.pokemon_id])
        self.assertTrue(set(stack) <= set(state.players[0].deck))
        self.assertEqual(len(stack), 2)
        audited(self, state)

    def test_without_bench_stops(self):
        """FJ1: 自分に控えポケモンがいないとき（相手には控えがいる）。カードは手札に残り、状態・乱数・ログは変わらない。"""
        state = board(mon(CHANSEY), bench=(), hand=(MR_FUJI,))
        assert_stops(self, state, PlayTrainer(0, card_of(state, 0, MR_FUJI)), FJ1)

    def test_trainer_lock_prevents_use(self):
        """［アレルギーかふん］がはたらいていれば使えない（v0.46。手札から出す前）。"""
        state = board(mon(CHANSEY), bench=(RATTATA,), opponent_bench=(mon(DARK_VILEPLUME),), hand=(MR_FUJI,))
        assert_stops(self, state, PlayTrainer(0, card_of(state, 0, MR_FUJI)), "TRAINER_PREVENTED", IllegalActionError)


# ---------------------------------------------------------------- ポケモン回収


class ScoopUpTest(unittest.TestCase):
    """ポケモン回収: いちばん下のカードを手札に、進化カード・エネルギーカードをトラッシュに。ダメージカウンターはなくなる（docs 3 章）。"""

    def test_benched_evolved_pokemon(self):
        """ベンチの 1 進化ポケモン: たねポケモンのカードは手札、進化カードとエネルギーはトラッシュ。カードの保存則・サイドは取られない。"""
        state = board(mon(CHANSEY), bench=(mon(RATICATE, (F, W), damage=20),), hand=(SCOOP_UP,))
        raticate = state.players[0].bench[0]
        basic, evolution = raticate.evolution_stack[0], raticate.card
        energy = tuple(raticate.energy)
        total = cards_total(state)
        state = use_trainer(state, SCOOP_UP)
        self.assertEqual(state.decision.options, (state.players[0].active.pokemon_id, raticate.pokemon_id))
        since = len(state.log)
        state = answer(state, [raticate.pokemon_id])
        self.assertEqual(state.phase, Phase.MAIN)
        self.assertIn(basic, state.players[0].hand)
        self.assertTrue({evolution, *energy} <= set(state.players[0].discard))
        self.assertEqual(cards_total(state), total)
        self.assertEqual(len(state.players[1].prizes), 6)
        event = events(state, since, "return_basic_to_hand")[0]
        self.assertEqual((event["zone"], event["card"], tuple(event["evolution_cards"]), tuple(event["energy"]), event["damage"]),
                         ("bench", basic, (evolution,), energy, 20))
        self.assertEqual([e["kind"] for e in events(state, since)], ["return_basic_to_hand", "discard_trainer"])
        audited(self, state)

    def test_active_then_promote_and_continue_the_turn(self):
        """バトル場のポケモン: 使い終えて（カードをトラッシュして）から、使ったプレイヤーが控えからバトル場に出す（promote_active）。そのあとも同じ番が続く
        （エネルギーをつけてワザを使える）。特殊状態・持続する効果は消える。もどしたたねポケモンは新しいポケモン（新しい番号・その番には進化できない）。"""
        state = board(mon(RATICATE, (F,), damage=10, confusion=True), bench=(mon(RATTATA), mon(RATTATA)), hand=(SCOOP_UP, F, RATICATE))
        active = state.players[0].active
        basic = active.evolution_stack[0]
        state = use_trainer(state, SCOOP_UP)
        since = len(state.log)
        state = answer(state, [active.pokemon_id])
        self.assertEqual([e["kind"] for e in events(state, since)], ["return_basic_to_hand", "discard_trainer"])
        self.assertEqual((state.phase, state.decision.kind, state.decision.player), (Phase.PROMOTE_ACTIVE, PROMOTE_ACTIVE, 0))
        audited(self, state)
        new_active = state.players[0].bench[1]
        state = answer(state, [new_active.pokemon_id])
        self.assertEqual((state.phase, state.current_player, state.players[0].active.pokemon_id), (Phase.MAIN, 0, new_active.pokemon_id))
        audited(self, state)
        state = apply_kernel(state, PlayBasicToBench(0, basic))
        replayed = state.players[0].bench[-1]
        self.assertGreater(replayed.pokemon_id, max(active.pokemon_id, new_active.pokemon_id))
        self.assertEqual((replayed.damage, replayed.energy, replayed.played_turn, replayed.conditions.names()), (0, [], TURN, ()))
        with self.assertRaises(IllegalActionError):
            apply_kernel(state, EvolvePokemon(0, card_of(state, 0, RATICATE), replayed.pokemon_id))  # その番に場に出したポケモン（p.310）
        state = apply_kernel(state, EndTurn(0))
        self.assertEqual(state.current_player, 1)
        audited(self, state)

    def test_persistent_effect_and_rejections(self):
        """場をはなれたポケモンの持続する効果は消える（理由 return_in_play_to_hand。GR-2000-P322-PERSISTENT-EFFECTS）。決定を待つ間は使用中のカードがあり、選べない
        ポケモン（相手のポケモン）を選ぶと拒否して状態は変わらない。"""
        state = board(mon(CHANSEY), mon("PMCG1-051", (F,)), bench=(RATTATA,), hand=(SCOOP_UP,), current=1, turn=TURN - 1)
        state = apply_kernel(state, UseAttack(1, 0))  # サンドの「すなかけ」（相手に与える持続する効果。次の相手の番にはたらく）
        chansey = state.players[0].active
        self.assertTrue(chansey.persistent_effects)
        self.assertEqual(state.current_player, 0)
        state = use_trainer(state, SCOOP_UP)
        self.assertIsNotNone(state.trainer_in_use)
        with self.assertRaises(IllegalActionError):
            apply_kernel(state, ResolveDecision(0, state.decision.id, (state.players[1].active.pokemon_id,)))
        since = len(state.log)
        state = answer(state, [chansey.pokemon_id])
        removed = events(state, since, "persistent_effect_removed")
        self.assertEqual([(e["pokemon_id"], e["reason"]) for e in removed], [(chansey.pokemon_id, "return_in_play_to_hand")])
        self.assertIsNone(state.trainer_in_use)
        audited(self, state)

    def test_breeder_stack(self):
        """ポケモン育て屋さんで重ねた たね + 2 進化: たねポケモンを手札に、2 進化カードをトラッシュに（飛ばした 1 進化カードは作らない）。"""
        state = board(mon(CHANSEY), bench=(mon(BULBASAUR, played_turn=TURN - 2),), hand=(POKEMON_BREEDER, VENUSAUR, SCOOP_UP))
        bulbasaur = state.players[0].bench[0]
        state = use_trainer(state, POKEMON_BREEDER)
        state = answer(state, [bulbasaur.pokemon_id])
        state = answer(state, [card_of(state, 0, VENUSAUR)])
        venusaur = state.players[0].bench[0]
        self.assertEqual(venusaur.evolution_stack, (bulbasaur.card,))
        state = answer(use_trainer(state, SCOOP_UP), [venusaur.pokemon_id])
        self.assertIn(bulbasaur.card, state.players[0].hand)
        self.assertIn(venusaur.card, state.players[0].discard)
        audited(self, state)

    def test_fossil_alone_and_with_evolution(self):
        """なにかの化石だけ: そのトレーナーカードが手札にもどる（手札ではトレーナーカード）。オムナイトがのっていれば、化石が手札、オムナイトがトラッシュ。"""
        state = board(mon(CHANSEY), bench=(mon(MYSTERIOUS_FOSSIL), mon(OMANYTE)), hand=(SCOOP_UP, SCOOP_UP))
        fossil, omanyte = state.players[0].bench
        state = answer(use_trainer(state, SCOOP_UP), [fossil.pokemon_id])
        self.assertIn(fossil.card, state.players[0].hand)
        self.assertEqual(state.card_def(fossil.card).category, "trainer")
        state = answer(use_trainer(state, SCOOP_UP), [omanyte.pokemon_id])
        self.assertIn(omanyte.evolution_stack[0], state.players[0].hand)
        self.assertIn(omanyte.card, state.players[0].discard)
        audited(self, state)

    def test_disguised_ninetales(self):
        """「ばける」でのせたカードも進化カードとしてトラッシュ。手札にもどるのはいちばん下のタケシのロコン。"""
        state = board(mon(BROCKS_NINETALES, (FIRE,)), bench=(RATTATA,), hand=(CHARMELEON, SCOOP_UP))
        ninetales = state.players[0].active
        state = apply_kernel(state, UsePokemonPower(0, ninetales.pokemon_id, 0))
        charmeleon = card_of(state, 0, CHARMELEON)
        state = answer(state, [charmeleon])
        self.assertEqual(state.players[0].active.disguise, charmeleon)
        since = len(state.log)
        state = answer(use_trainer(state, SCOOP_UP), [ninetales.pokemon_id])
        event = events(state, since, "return_basic_to_hand")[0]
        self.assertEqual((event["card"], event["disguise"], tuple(event["evolution_cards"])), (ninetales.evolution_stack[0], charmeleon, (ninetales.card, charmeleon)))
        self.assertTrue({ninetales.card, charmeleon} <= set(state.players[0].discard))
        audited(self, state)

    def test_transformed_ditto(self):
        """［へんしん］のメタモン: 実際のカードはメタモンなので、メタモンのカードが手札にもどる（相手のカードではない）。"""
        state = board(mon(DITTO, (W,)), bench=(RATTATA,), hand=(SCOOP_UP,))
        ditto = state.players[0].active
        state = answer(use_trainer(state, SCOOP_UP), [ditto.pokemon_id])
        self.assertIn(ditto.card, state.players[0].hand)
        self.assertEqual(state.cards[ditto.card].card_id, DITTO)
        audited(self, state)

    def test_attached_trainer_stops(self):
        """SU1: トレーナーカードがついているポケモンは選べるが選ぶと止める（行き先が日本語の文面にない）。どのポケモンもそうなら使う前に止める。"""
        state = board(mon(CHANSEY, trainers=[(PLUSPOWER, TURN)]), bench=(mon(RATTATA, trainers=[(DEFENDER, TURN + 1)]),), hand=(SCOOP_UP,))
        assert_stops(self, state, PlayTrainer(0, card_of(state, 0, SCOOP_UP)), SU1)
        state = board(mon(CHANSEY, trainers=[(PLUSPOWER, TURN)]), bench=(RATTATA,), hand=(SCOOP_UP,))
        state = use_trainer(state, SCOOP_UP)
        active = state.players[0].active
        self.assertEqual(state.decision.context_value("unresolved_choices"), (active.pokemon_id,))
        assert_stops(self, state, ResolveDecision(0, state.decision.id, (active.pokemon_id,)), SU1)
        state = answer(state, [state.players[0].bench[0].pokemon_id])
        audited(self, state)

    def test_last_pokemon_stops(self):
        """SU2: 控えがいないときのバトル場のポケモン（自分の場のポケモンはその 1 匹）。使う前に止める。"""
        state = board(mon(CHANSEY), bench=(), hand=(SCOOP_UP,))
        assert_stops(self, state, PlayTrainer(0, card_of(state, 0, SCOOP_UP)), SU2)

    def test_chemical_gas_source_leaves(self):
        """かがくへんかガスのベトベトンを手札にもどすと、ガスはその時点でなくなる（はたらいているかは今の場から求める）。"""
        state = board(mon(CHANSEY), bench=(mon("PMCG3-007", evolved_from="PMCG3-003"),), opponent=mon(HAUNTER, evolved_from=GASTLY), hand=(SCOOP_UP,))
        muk = state.players[0].bench[0]
        haunter = state.players[1].active
        self.assertIsNone(E.working_evasion_power(state, haunter.pokemon_id))  # ガスが消している
        state = answer(use_trainer(state, SCOOP_UP), [muk.pokemon_id])
        self.assertIsNotNone(E.working_evasion_power(state, haunter.pokemon_id))
        audited(self, state)

    def test_primal_power_source_leaves(self):
        """［げんしのちから］のプテラ（化石の上）を回収すると、化石が手札・プテラがトラッシュで、進化をまた止めなくなる。"""
        state = board(mon(CHANSEY), bench=(mon(AERODACTYL, evolved_from=MYSTERIOUS_FOSSIL), mon(BULBASAUR, played_turn=TURN - 2)), hand=(SCOOP_UP, IVYSAUR))
        aerodactyl, bulbasaur = state.players[0].bench
        with self.assertRaises(IllegalActionError) as caught:
            apply_kernel(state, EvolvePokemon(0, card_of(state, 0, IVYSAUR), bulbasaur.pokemon_id))
        self.assertEqual(caught.exception.code, "EVOLUTION_PREVENTED")
        state = answer(use_trainer(state, SCOOP_UP), [aerodactyl.pokemon_id])
        state = apply_kernel(state, EvolvePokemon(0, card_of(state, 0, IVYSAUR), bulbasaur.pokemon_id))
        self.assertEqual(state.cards[state.players[0].bench[0].card].card_id, IVYSAUR)
        audited(self, state)

    def test_allergy_pollen_off_while_asleep_then_removed(self):
        """［アレルギーかふん］はねむりで消える（v0.46）。そのときにわるいラフレシア自身を回収すれば、そのあとも使える（場から求め直す）。"""
        state = board(mon(DARK_VILEPLUME, sleep=True), bench=(RATTATA, RATTATA), hand=(SCOOP_UP, SCOOP_UP))
        vileplume = state.players[0].active
        state = answer(use_trainer(state, SCOOP_UP), [vileplume.pokemon_id])
        state = answer(state, [state.players[0].bench[0].pokemon_id])
        state = use_trainer(state, SCOOP_UP)
        self.assertEqual(state.decision.kind, SELECT_POKEMON)

    def test_psylink_loses_the_attacks_of_the_returned_pokemon(self):
        """［サイコリンク］で持つワザは今の場から求める。供給していた超のポケモンを回収したら、そのワザはなくなる。"""
        state = board(mon("PMCG6-053", (PSYCHIC,) * 4, evolved_from=["PMCG6-043", "PMCG6-047"]), bench=(mon("PMCG1-046", evolved_from="PMCG1-043"),),
                      hand=(SCOOP_UP,))
        alakazam, kadabra = state.players[0].active, state.players[0].bench[0]
        before = {(o.key.card_id, o.key.attack_index) for o in E.available_attacks(state, alakazam)}
        self.assertTrue(any(card_id == "PMCG1-046" for card_id, _ in before))
        state = answer(use_trainer(state, SCOOP_UP), [kadabra.pokemon_id])
        after = {(o.key.card_id, o.key.attack_index) for o in E.available_attacks(state, state.players[0].active)}
        self.assertFalse(any(card_id == "PMCG1-046" for card_id, _ in after))

    def test_opponent_ditto_max_hp_drop_is_mh1(self):
        """回収で相手の［へんしん］のメタモンの最大HPが下がり（バトル場が空くと同じカードとしてあつかう相手がいない）、のっているダメージ以下になる場面は、トレーナーの
        効果で最大HPが下がる v0.48 の MH1（その答えを受け付けない。状態は変わらない）。ほかの答え（ベンチのポケモン）は受け付ける。内部エラーにならない。"""
        state = board(mon(CHANSEY), opponent=mon(DITTO, (W,), damage=60), bench=(RATTATA,), hand=(SCOOP_UP,))
        state = use_trainer(state, SCOOP_UP)
        assert_stops(self, state, ResolveDecision(0, state.decision.id, (state.players[0].active.pokemon_id,)), "UNRESOLVED_MAX_HP_DROP")
        after = answer(state, [state.players[0].bench[0].pokemon_id])
        self.assertEqual(after.phase, Phase.MAIN)
        audited(self, after)

    def test_every_answer_stops_then_the_trainer_is_not_played(self):
        """どの答えも止まる（バトル場は MH1、ベンチは SU1）なら、使用中のトレーナーを残して止まらないよう、使う前に受け付けない（v0.49 の ``_trainer_dead_end``）。"""
        state = board(mon(CHANSEY), opponent=mon(DITTO, (W,), damage=60), bench=(mon(RATTATA, trainers=[(DEFENDER, TURN + 1)]),), hand=(SCOOP_UP,))
        before = snapshot(state)
        with self.assertRaises(UnsupportedError):
            apply_kernel(state, PlayTrainer(0, card_of(state, 0, SCOOP_UP)))
        self.assertEqual(snapshot(state), before)


# ---------------------------------------------------------------- エリカのハクリュー


class BlizzardTest(unittest.TestCase):
    """ふぶき（v0.38 のフリーザーと同じ型）: 30 のあと、1 枚のコインで「おもて」なら相手の控え全員、「うら」なら自分の控え全員に 10（弱点・抵抗力なし）。"""

    def _use(self, coins, *, bench=(RATTATA, RATTATA), opponent_bench=(RATTATA, RATTATA), opponent=None):
        state = board(dragonair((W, W, W)), opponent, bench=bench, opponent_bench=opponent_bench)
        state = with_coin_results(state, *coins)
        since = len(state.log)
        return state, apply_kernel(state, UseAttack(0, 0)), since

    def test_heads_and_tails(self):
        for coin, damaged_side in ((H, 1), (T, 0)):
            _, after, since = self._use([coin])
            self.assertEqual(len(events(after, since, "coin_flip")), 1)
            self.assertEqual(after.players[1].active.damage if after.players[1].active else None, 30)
            for player in (0, 1):
                expected = 10 if player == damaged_side else 0
                self.assertEqual([b.damage for b in after.players[player].bench], [expected, expected])

    def test_no_bench_on_either_side_no_coin(self):
        """自分にも相手にも控えがいなければ、コインが決める要素のどれにも処理の対象がないので投げない（v0.38 と同じ）。"""
        _, after, since = self._use([], bench=(), opponent_bench=())
        self.assertEqual(events(after, since, "coin_flip"), [])
        self.assertEqual(after.players[1].active.damage, 30)

    def test_bench_on_one_side_only(self):
        """片方だけに控えがいれば投げる。もう一方の面では何もしない。"""
        _, after, _ = self._use([T], bench=(), opponent_bench=(RATTATA,))
        self.assertEqual([b.damage for b in after.players[1].bench], [0])
        _, after, _ = self._use([H], bench=(), opponent_bench=(RATTATA,))
        self.assertEqual([b.damage for b in after.players[1].bench], [10])

    def test_bench_knockout(self):
        """控えの 10 で HP 以上になったポケモンは、ワザのあとにきぜつする（サイドを取る）。"""
        _, after, since = self._use([H], opponent_bench=(mon(RATTATA, damage=20),))
        knocked = events(after, since, "knock_out")
        self.assertEqual(len(knocked), 1)
        self.assertEqual(after.decision.kind, "take_prize")


class TakeAwayTest(unittest.TestCase):
    """つれさる: 自分と相手の対戦ポケモンを、ついているすべてのカードとともにそれぞれの山札にもどし、それぞれの山札を切る（docs 4 章）。"""

    def test_both_return_and_both_promote(self):
        """両方に控えがいる: 自分 → 相手の順にもどし、自分 → 相手の順に切る。きぜつではない（サイドなし）。ワザのあと、番でないプレイヤー → 番のプレイヤーの順に
        バトル場に出し、番が終わる。"""
        state = board(dragonair(damage=30, confusion=False), mon(RATICATE, (F, F), damage=10, trainers=[(DEFENDER, TURN)]))
        mine, theirs = state.players[0].active, state.players[1].active
        my_cards = (*mine.cards(), *mine.energy)
        their_cards = (*theirs.cards(), *theirs.energy, *(t.card for t in theirs.trainers))
        total = cards_total(state)
        since = len(state.log)
        state = apply_kernel(state, UseAttack(0, 1))
        kinds = [e["kind"] for e in events(state, since)]
        self.assertEqual(kinds, ["attack", "return_in_play_to_deck", "return_in_play_to_deck", "shuffle", "shuffle"])
        returned = events(state, since, "return_in_play_to_deck")
        self.assertEqual([(e["player"], e["pokemon_id"], tuple(e["cards"])) for e in returned],
                         [(0, mine.pokemon_id, my_cards), (1, theirs.pokemon_id, their_cards)])
        self.assertEqual([e["player"] for e in events(state, since, "shuffle")], [0, 1])
        self.assertTrue(set(my_cards) <= set(state.players[0].deck) and set(their_cards) <= set(state.players[1].deck))
        self.assertEqual(cards_total(state), total)
        self.assertEqual([len(p.prizes) for p in state.players], [6, 6])
        self.assertEqual((state.decision.kind, state.decision.player), (PROMOTE_ACTIVE, 1))
        audited(self, state)
        state = answer(state, [state.decision.options[0]])
        self.assertEqual((state.decision.kind, state.decision.player), (PROMOTE_ACTIVE, 0))
        state = answer(state, [state.decision.options[0]])
        self.assertEqual((state.current_player, state.phase), (1, Phase.MAIN))
        audited(self, state)

    def test_opponent_without_bench_loses(self):
        """相手に控えがいなくても使える（わるいカイリキーの「つまみだす」の条件を持ち込まない）。相手は場にポケモンがいなくなり、勝ち負けの判定で負ける。"""
        state = board(dragonair(), opponent_bench=())
        state = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual((state.phase, state.result.outcome, state.result.winner), (Phase.GAME_OVER, "win", 0))

    def test_neither_has_bench(self):
        """どちらにも控えがいなければ、両方とも場にポケモンがいなくなる（p.311 の表。サドンデス）。"""
        state = board(dragonair(), bench=(), opponent_bench=())
        state = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual((state.phase, state.result.outcome), (Phase.SUDDEN_DEATH, "sudden_death"))

    def test_only_self_without_bench(self):
        """自分にだけ控えがいない: 自分が負ける（相手はバトル場に出す前に勝ち負けが決まる）。"""
        state = board(dragonair(), bench=())
        state = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual((state.result.outcome, state.result.winner), ("win", 1))

    def test_only_self_returns_when_opponent_has_barrier(self):
        """相手が「ワザをうけない」状態（ミュウツーの「バリアー」。v0.31。実際にワザを使って与える）: 相手はもどらず（effect_prevented）、相手の山札は切らない。
        自分だけもどる（自分の処理のあとも、相手の処理を続ける）。"""
        state = board(dragonair(), mon("PMCG1-050", (PSYCHIC, PSYCHIC, PSYCHIC)), current=1, turn=TURN + 1)
        names = [a.name_ja for a in state.card_def(state.players[1].active.card).attacks]
        state = apply_kernel(state, UseAttack(1, names.index("バリアー")))
        while state.decision is not None:
            state = answer(state, [state.decision.options[0]])
        self.assertEqual(state.current_player, 0)
        since = len(state.log)
        state = apply_kernel(state, UseAttack(0, 1))
        kinds = [e["kind"] for e in events(state, since)]
        self.assertIn("effect_prevented", kinds)
        self.assertEqual([e["player"] for e in events(state, since, "return_in_play_to_deck")], [0])
        self.assertEqual([e["player"] for e in events(state, since, "shuffle")], [0])
        self.assertIsNotNone(state.players[1].active)
        self.assertEqual((state.decision.kind, state.decision.player), (PROMOTE_ACTIVE, 0))
        audited(self, state)

    def test_only_one_returns_with_transparency(self):
        """相手が「とうめい」（化石の秘密のゴースト）: 「おもて」なら相手はもどらない（自分だけもどる）。「うら」なら両方もどる。"""
        for coin, players in ((H, [0]), (T, [0, 1])):
            state = board(dragonair(), mon(HAUNTER, evolved_from=GASTLY))
            state = with_coin_results(state, coin)
            since = len(state.log)
            state = apply_kernel(state, UseAttack(0, 1))
            self.assertEqual([e["player"] for e in events(state, since, "return_in_play_to_deck")], players)
            self.assertEqual([e["player"] for e in events(state, since, "shuffle")], players)
            audited(self, state)

    def test_copied_by_metronome(self):
        """ピッピの「ゆびをふる」で相手のエリカのハクリューの「つれさる」を使う: もどるのはピッピ（ワザを使ったポケモン）と相手のエリカのハクリュー。"""
        state = board(mon(CLEFAIRY, ("PMCG1-097", "PMCG1-097", "PMCG1-097")), dragonair())
        clefairy, target = state.players[0].active, state.players[1].active
        attacks = [a.name_ja for a in state.card_def(clefairy.card).attacks]
        index = attacks.index("ゆびをふる")
        state = apply_kernel(state, UseAttack(0, index))
        if state.decision is not None and state.decision.kind == "select_attack":
            option = next(o for o in state.decision.options if state.decision.options.index(o) == 1) if len(state.decision.options) > 1 else state.decision.options[0]
            state = answer(state, [option])
        returned = [e["pokemon_id"] for e in state.log if e["kind"] == "return_in_play_to_deck"]
        self.assertEqual(returned, [clefairy.pokemon_id, target.pokemon_id])
        audited(self, state)

    def test_transformed_ditto_uses_take_away(self):
        """［へんしん］のメタモンが相手のエリカのハクリューとして「つれさる」を使う: もどるのはメタモン（実際のカード）と相手のエリカのハクリュー。"""
        state = board(mon(DITTO, (W, F, FIRE, PSYCHIC)), dragonair())
        ditto, target = state.players[0].active, state.players[1].active
        state = apply_kernel(state, UseAttack(0, 1))
        returned = [(e["pokemon_id"], tuple(e["cards"])) for e in state.log if e["kind"] == "return_in_play_to_deck"]
        self.assertEqual(returned[0], (ditto.pokemon_id, (ditto.card, *ditto.energy)))
        self.assertEqual(returned[1][0], target.pokemon_id)
        audited(self, state)

    def test_disguised_ninetales_uses_take_away(self):
        """「ばける」でエリカのハクリューをのせたタケシのキュウコンが「つれさる」を使う: のせたカードも重なったカードといっしょに山札にもどる。"""
        state = board(mon(BROCKS_NINETALES, (W, W, W, W)), bench=(RATTATA,), hand=(ERIKAS_DRAGONAIR,))
        ninetales = state.players[0].active
        state = apply_kernel(state, UsePokemonPower(0, ninetales.pokemon_id, 0))
        overlay = card_of(state, 0, ERIKAS_DRAGONAIR)
        state = answer(state, [overlay])
        since = len(state.log)
        state = apply_kernel(state, UseAttack(0, 1, card=overlay))
        mine = events(state, since, "return_in_play_to_deck")[0]
        self.assertEqual(mine["disguise"], overlay)
        self.assertIn(overlay, mine["cards"])
        self.assertIn(overlay, state.players[0].deck)
        audited(self, state)

    def test_fossil_opponent_returns_to_deck(self):
        """相手のバトル場のなにかの化石（場ではポケモン）も、そのトレーナーカードが持ち主の山札にもどる（きぜつではないのでカウントの問題もない）。"""
        state = board(dragonair(), mon(MYSTERIOUS_FOSSIL))
        fossil = state.players[1].active
        state = apply_kernel(state, UseAttack(0, 1))
        self.assertIn(fossil.card, state.players[1].deck)
        self.assertEqual(state.card_def(fossil.card).category, "trainer")
        audited(self, state)

    def test_recall_record_of_a_returned_pokemon(self):
        """思い出させるの記録（今の番だけ）は、記録したポケモンが山札にもどったあと、バトル場に出す決定を待つ間も残ってよく、番の終わりに消える。"""
        from tests.helpers import RECALL

        state = board(dragonair(), hand=(RECALL,))
        state = use_trainer(state, RECALL)
        while state.decision is not None and state.decision.kind != PROMOTE_ACTIVE:
            state = answer(state, [state.decision.options[0]])
        self.assertTrue(state.recalls)
        state = apply_kernel(state, UseAttack(0, 1))
        self.assertTrue(state.recalls)
        audited(self, state)
        while state.decision is not None:
            state = answer(state, [state.decision.options[0]])
        self.assertEqual((state.current_player, state.recalls), (1, ()))
        audited(self, state)

    def test_observation_does_not_reveal_deck_order(self):
        """もどしたカードは場にあったので公開。山札の並び・中身は観測に出さない（枚数だけ）。"""
        state = apply_kernel(board(dragonair()), UseAttack(0, 1))
        for viewer in (0, 1):
            seen = observe(state, viewer)
            for p in (0, 1):
                self.assertEqual(seen["players"][p]["deck"], {"count": len(state.players[p].deck)})  # 山札は枚数だけ（自分の山札も）
            kinds = [e["kind"] for e in visible_log(state, viewer)]
            self.assertIn("return_in_play_to_deck", kinds)
        audited(self, state)


if __name__ == "__main__":
    unittest.main()
