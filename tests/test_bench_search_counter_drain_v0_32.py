"""v0.32: 山札から名前の決まったたねポケモンをベンチに出すワザ・ダメージカウンターの数でダメージが決まるワザ・与えたぶん回復するワザの 13 枚
（docs/bench-search-counter-drain-v0.32.md）。

カードごとに同じテストを書かず、共通の仕組みの境界（``BenchFromDeckTest``・``CounterDamageTest``・``FullDrainTest``）と、カードごとの登録の確かめ
（``CardDataTest``）と、すべてのワザの先読みの方法ごとの一致（``PreflightParityTest``）に分けた。根拠はどれも kyuura データの採用（kyuura の印刷の
文面。``card_sources.json``）と、既存の記録（p.309・p.310・p.319〜p.321 の一般の規定のエンジン・kyuura の記録。v0.4d のメガドレイン・v0.11 の
いかりのスーパーパンチ・v0.9 の H5 の読み方）の再利用。ガイドブックは読んでいない。
"""

from __future__ import annotations

import itertools
import json
import pathlib
import unittest

from kyuura_engine import (
    EndTurn,
    EngineError,
    EvolvePokemon,
    IllegalActionError,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    apply_command,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, read_extract
from kyuura_engine.decisions import BENCH_FROM_DECK, SELECT_ATTACK
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.resolution.programs import BUILDERS, BenchFromDeck, Drain
from kyuura_engine.rng import rng_fingerprint
from scripts import check_card_sources as cs
from scripts.extract_kyuura_cards import (
    PREVIOUS_KYUURA_COMMIT as ADOPTED_COMMIT,  # v0.69: 採用したときのデータのコミット（採用の記録は書き換えない）
)
from tests.helpers import (
    BELLSPROUT,
    BROCKS_ZUBAT,
    BUTTERFREE,
    CATERPIE,
    CHARMANDER,
    CLEFABLE,
    CLEFAIRY,
    DEFENDER,
    FIGHTING,
    FOSSIL_ZUBAT,
    GOLBAT,
    GRASS,
    GYARADOS,
    HITMONCHAN,
    JUNGLE_ODDISH,
    JYNX,
    KINGLER,
    KRABBY,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MAGIKARP,
    METAPOD,
    MISTYS_PSYDUCK,
    NIDORAN_F,
    NIDORINA,
    PLUSPOWER,
    POLIWAG,
    PSYCHIC,
    RATTATA,
    ROCKET_ODDISH,
    ROCKET_ZUBAT,
    V0_32_POKEMON,
    VENONAT,
    WATER,
    WEEPINBELL,
    H,
    T,
    apply_kernel,
    build_test_state,
    kyuura_records_since_v0_69,
    with_coin_results,
)
from tests.log_audit import serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
TURN = 7
DOC = ROOT / "docs" / "bench-search-counter-drain-v0.32.md"
# 進化しているカードの下のカード
BELOW = {NIDORINA: NIDORAN_F, WEEPINBELL: BELLSPROUT, GYARADOS: MAGIKARP, KINGLER: KRABBY, GOLBAT: FOSSIL_ZUBAT, CLEFABLE: CLEFAIRY,
         BUTTERFREE: [CATERPIE, METAPOD], MACHAMP: [MACHOP, MACHOKE]}
# 登録の実装の型（カード id, ワザの位置）。説明文のないワザは DamageOnly
EXPECTED = {
    (NIDORAN_F, 0): (E.CoinFlipDamage, {"coins": 3, "damage_per_heads": 10}),
    (NIDORAN_F, 1): (E.PutBasicFromDeckOntoBench, {"names": ("ニドラン♂", "ニドラン♀")}),
    (JUNGLE_ODDISH, 0): (E.ParalyzeOnHeads, {}),
    (JUNGLE_ODDISH, 1): (E.PutBasicFromDeckOntoBench, {"names": ("ナゾノクサ",)}),
    (BELLSPROUT, 0): (E.DamageOnly, {}),
    (BELLSPROUT, 1): (E.PutBasicFromDeckOntoBench, {"names": ("マダツボミ",)}),
    (KRABBY, 0): (E.PutBasicFromDeckOntoBench, {"names": ("クラブ",)}),
    (KRABBY, 1): (E.DamageOnly, {}),
    (NIDORINA, 0): (E.ConfuseOnHeadsWithoutDamage, {}),
    (NIDORINA, 1): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 30}),
    (WEEPINBELL, 0): (E.PoisonOnHeads, {}),
    (WEEPINBELL, 1): (E.DamageOnly, {}),
    (MAGIKARP, 0): (E.DamageOnly, {}),
    (MAGIKARP, 1): (E.DamageTimesOwnCounters, {"per": 10}),
    (GYARADOS, 0): (E.DamageOnly, {}),
    (GYARADOS, 1): (E.ParalyzeOnHeads, {}),
    (KINGLER, 0): (E.DamageTimesOwnCounters, {"per": 10}),
    (KINGLER, 1): (E.DamageOnly, {}),
    (JYNX, 0): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 10}),
    (JYNX, 1): (E.DamagePlusDefenderCounters, {"per": 10}),
    (VENONAT, 0): (E.ParalyzeOnHeads, {}),
    (VENONAT, 1): (E.DamageAndFullDrain, {}),
    (FOSSIL_ZUBAT, 0): (E.ConfuseOnHeadsWithoutDamage, {}),
    (FOSSIL_ZUBAT, 1): (E.DamageAndFullDrain, {}),
    (GOLBAT, 0): (E.DamageOnly, {}),
    (GOLBAT, 1): (E.DamageAndFullDrain, {}),
}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, opponent=None, *, bench=(), opponent_bench=(RATTATA,), hand=(), deck=None, discard=(), opponent_deck=None):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "discard": list(discard)}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent or mon(HITMONCHAN, (FIGHTING,)), "bench": list(opponent_bench)}
    if opponent_deck is not None:
        them["deck"] = list(opponent_deck)
    return build_test_state([me, them], turn_number=TURN)


def full(state):
    return state_to_dict(state, format_version=10)


def play(state, command, answers=(), *, mode="derived"):
    state = apply_kernel(state, command, preflight=mode)
    for answer in answers:
        d = state.decision
        assert d is not None, "決定がない"
        choice = answer(d) if callable(answer) else tuple(answer)
        state = apply_kernel(state, ResolveDecision(d.player, d.id, choice), preflight=mode)
    return state


def events(state, since, kind=None):
    return [dict(e) for e in state.log[since:] if kind is None or e["kind"] == kind]


def dealt(state, since, player=1):
    """そのあとのログで、プレイヤー ``player`` の対戦ポケモンが受けたワザのダメージ（最終ダメージ）の並び。"""
    return [e["amount"] for e in state.log[since:] if e["kind"] == "damage" and "target" not in e and e["player"] == player]


def card_ids(state, uids):
    return [state.cards[uid].card_id for uid in uids]


def total_cards(state):
    """両方のプレイヤーの、どこかのゾーンにあるカードの数（カードの保存則）。"""
    count = 0
    for p in state.players:
        count += len(p.deck) + len(p.hand) + len(p.discard) + len(p.prizes)
        count += sum(len(pokemon.cards()) + len(pokemon.energy) + len(pokemon.trainers) for pokemon in p.in_play())
    return count


class CardDataTest(unittest.TestCase):
    """13 枚の登録・写し・採用の記録・進化の関係（カードごとの登録の確かめ。処理の境界は下の共通の仕組みのテスト）。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()
        cls.copy = {c["id"]: c for c in read_extract()["cards"]}

    def test_targets_are_the_thirteen_cards_and_playable(self):
        """対象は依頼の 13 枚だけ（ほかの候補に広げていない）。どれも写しの組 pool_v0_32 にあり、対戦に使える。"""
        self.assertEqual(len(V0_32_POKEMON), 13)
        self.assertEqual(list(read_extract()["pool_v0_32"]), list(V0_32_POKEMON))
        for card in V0_32_POKEMON:
            with self.subTest(card=card):
                self.assertTrue(self.pool.is_playable(card))

    def test_every_attack_is_registered_with_the_expected_type(self):
        """26 のワザがどれも登録され、型と値が表のとおり。名前・文面は写しと同じで、処理に使う文面は kyuura の印刷の文面（説明文のあるワザ）。"""
        seen = set()
        for card in V0_32_POKEMON:
            definition = self.pool.get(card)
            for attack in definition.attacks:
                key = (card, attack.index)
                seen.add(key)
                entry = E.DEFAULT_EFFECTS.attack_entry(card, attack.index)
                expected_type, values = EXPECTED[key]
                with self.subTest(card=card, attack=attack.name_ja):
                    self.assertIs(type(entry.effect), expected_type)
                    for name, value in values.items():
                        self.assertEqual(getattr(entry.effect, name), value)
                    self.assertEqual(entry.name_ja, attack.name_ja)
                    self.assertIsNone(E.DEFAULT_EFFECTS.attack_problem(card, attack, definition.attacks))
                    if attack.text_ja is None:
                        self.assertIsNone(entry.play_text_ja)
                    else:
                        self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (attack.text_ja, attack.text_ja, cs.PRINTED_TEXT_SOURCE))
        self.assertEqual(seen, set(EXPECTED))
        self.assertEqual(len(seen), 26)

    def test_adoption_records(self):
        """13 枚はどれも kyuura データの採用の記録（adopted）と pcg-search.com の照合（同じ版の一覧の番号）を持ち、過去の原典照合の記録には加えていない。"""
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        verification = json.loads((ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8"))
        verified = {r["card_id"] for r in verification["records"]} if isinstance(verification, dict) and "records" in verification else set()
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        adopted = set(links["latest_descriptions"]["adopted_printed_text"])
        for card in V0_32_POKEMON:
            record = sources[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]), ("kyuura_data", "adopted", ADOPTED_COMMIT))
                self.assertEqual(record["kyuura_records"], kyuura_records_since_v0_69(card))  # v0.69: 研究の基準を上げて加わった kyuura の記録（tests/helpers.py の V0_69_KYUURA_RECORDS_ADDED）
                self.assertNotIn(card, verified)
                [check] = record["external_checks"]
                self.assertEqual(check["site"], "pcg-search.com")
                self.assertIn(check["result"], ("match", "differences"))
                self.assertFalse(any(d["affects_behavior"] for d in check["differences"]))
                for attack in self.pool.get(card).attacks:
                    key = f"attack/{attack.index}"
                    if attack.text_ja is not None:
                        self.assertEqual(record["play_text"][key], "kyuura_printed_text")
                        self.assertIn(f"{card}/{key}", adopted)
                    else:
                        self.assertNotIn(key, record["play_text"])

    def test_evolution_by_exact_name(self):
        """進化先 5 枚は、進化元の名前と完全に一致するたねポケモンからだけ、通常の進化の操作で進化する（ゴルバットは名前「ズバット」なので第4弾の
        ズバットからも進化でき、名前の違うタケシのズバットからは進化できない）。"""
        pairs = [(NIDORINA, NIDORAN_F), (WEEPINBELL, BELLSPROUT), (GYARADOS, MAGIKARP), (KINGLER, KRABBY), (GOLBAT, FOSSIL_ZUBAT),
                 (GOLBAT, ROCKET_ZUBAT)]
        for upper, below in pairs:
            with self.subTest(upper=upper, below=below):
                self.assertEqual(self.pool.get(upper).evolves_from, self.pool.get(below).name_ja)
                state = board(mon(RATTATA), bench=[mon(below, played_turn=1)], hand=[upper])
                target = state.players[0].bench[0].pokemon_id
                new = apply_command(state, EvolvePokemon(0, state.players[0].hand[0], target))
                self.assertEqual(new.cards[new.players[0].bench[0].card].card_id, upper)
        state = board(mon(RATTATA), bench=[mon(BROCKS_ZUBAT, played_turn=1)], hand=[GOLBAT])
        with self.assertRaises(IllegalActionError) as raised:
            apply_command(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].bench[0].pokemon_id))
        self.assertEqual(raised.exception.code, "EVOLUTION_NAME_MISMATCH")

    def test_same_name_cards_keep_separate_registrations(self):
        """第2弾のナゾノクサと第4弾のナゾノクサ、化石の秘密のズバットと第4弾のズバットは、同じ名前の別のカードで、登録は別（カード id で引く）。"""
        for new, old in ((JUNGLE_ODDISH, ROCKET_ODDISH), (FOSSIL_ZUBAT, ROCKET_ZUBAT)):
            self.assertEqual(self.pool.get(new).name_ja, self.pool.get(old).name_ja)
            self.assertNotEqual([a.name_ja for a in self.pool.get(new).attacks], [a.name_ja for a in self.pool.get(old).attacks])
            for attack in self.pool.get(old).attacks:
                self.assertIsNot(type(E.DEFAULT_EFFECTS.attack_entry(old, attack.index).effect), E.PutBasicFromDeckOntoBench)

    def test_registration_checks_reject_wrong_data(self):
        """登録の確かめ（``check``）: 名前・説明の形・ダメージの目安が合わないワザには登録できない。"""
        oddish, magikarp, jynx, venonat = (self.pool.get(c) for c in (JUNGLE_ODDISH, MAGIKARP, JYNX, VENONAT))
        self.assertTrue(E.PutBasicFromDeckOntoBench(("ニドラン♀",)).check(oddish.attacks[1]))
        self.assertTrue(E.PutBasicFromDeckOntoBench(("ナゾノクサ",)).check(oddish.attacks[0]))
        self.assertEqual(E.PutBasicFromDeckOntoBench(("ナゾノクサ",)).check(oddish.attacks[1]), [])
        self.assertTrue(E.DamageTimesOwnCounters(20).check(magikarp.attacks[1]))
        self.assertTrue(E.DamageTimesOwnCounters(10).check(magikarp.attacks[0]))
        self.assertTrue(E.DamagePlusDefenderCounters(10).check(jynx.attacks[0]))
        self.assertTrue(E.DamageAndFullDrain().check(magikarp.attacks[1]))
        self.assertEqual(E.DamageAndFullDrain().check(venonat.attacks[1]), [])
        with self.assertRaises(ValueError):
            E.PutBasicFromDeckOntoBench(())

    def test_programs(self):
        """解決の基盤の要素の並び: 山札からベンチに出す要素だけ・自分のカウンター × 10・目安 + 相手のカウンター × 10・与えたぶんの回復（``Drain`` の
        ``full``）。メガドレインは同じ ``Drain`` の半分のまま（``full`` が偽）。"""
        program = BUILDERS[E.PutBasicFromDeckOntoBench](E.PutBasicFromDeckOntoBench(("クラブ",)))
        self.assertEqual(program, (BenchFromDeck(("クラブ",)),))
        drain = BUILDERS[E.DamageAndFullDrain](E.DamageAndFullDrain())[-1]
        self.assertEqual((type(drain), drain.full, drain.counters), (Drain, True, None))
        mega = BUILDERS[E.DamageAndDrain](E.DamageAndDrain())[-1]
        self.assertEqual((type(mega), mega.full, mega.counters), (Drain, False, None))

    def test_document_lists_the_cards(self):
        text = DOC.read_text(encoding="utf-8")
        for card in V0_32_POKEMON:
            self.assertIn(card, text)


class BenchFromDeckTest(unittest.TestCase):
    """山札から名前の決まったたねポケモンを 1 匹さがしてベンチに出す（なかまをよぶ・ふえる）。kyuura の印刷の文面「自分の山札から「○○」を1匹さがして
    ベンチに出す。その後、その山札をよくきる。自分のベンチに空きがなければ（、このワザは）使えない。」"""

    def oddish_board(self, deck, *, bench=(), confused=False, hand=()):
        extra = {"confusion": True} if confused else {}
        return board(mon(JUNGLE_ODDISH, (GRASS, GRASS), **extra), bench=bench, deck=deck, hand=hand)

    def test_candidates_are_basic_pokemon_with_a_named_name(self):
        """選べるものは山札の、説明の名前と同じ名前のたねポケモン（uid の小さい順）。同じ名前の別のカード（第4弾のナゾノクサ）も選べ、名前の違う
        たねポケモン・進化カード・エネルギーは選べない。ニドラン♀の「なかまをよぶ」は「ニドラン♂」「ニドラン♀」の 2 つの名前。"""
        state = self.oddish_board([GRASS, ROCKET_ODDISH, NIDORAN_F, JUNGLE_ODDISH, WEEPINBELL, JUNGLE_ODDISH])
        new = play(state, UseAttack(0, 1))
        d = new.decision
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices, d.resume), (BENCH_FROM_DECK, 0, 1, 1, "attack"))
        self.assertEqual(card_ids(new, d.options), [ROCKET_ODDISH, JUNGLE_ODDISH, JUNGLE_ODDISH])
        self.assertEqual(list(d.options), sorted(d.options))
        nidoran = board(mon(NIDORAN_F, (GRASS, GRASS)), deck=[NIDORINA, JUNGLE_ODDISH, NIDORAN_F, GRASS])
        self.assertEqual(card_ids(nidoran, play(nidoran, UseAttack(0, 1)).decision.options), [NIDORAN_F])

    def test_put_directly_onto_the_bench_and_shuffle(self):
        """選んだカードは手札を通らずにベンチの最後に出る（新しい場のポケモンの番号・場に出た番は今の番）。そのあと山札を切る（``zones.shuffle_deck``
        と同じ乱数の使い方）。ログは ``bench_from_deck`` → ``shuffle``。カードの数は変わらない。"""
        state = self.oddish_board([GRASS, ROCKET_ODDISH, WATER, JUNGLE_ODDISH, GRASS], bench=[mon(RATTATA)])
        before_hand, before_total, next_id = list(state.players[0].hand), total_cards(state), state.next_pokemon_id
        waiting = play(state, UseAttack(0, 1))
        chosen = waiting.decision.options[0]
        new = play(waiting, None) if False else apply_kernel(waiting, ResolveDecision(0, waiting.decision.id, (chosen,)))
        bench = new.players[0].bench
        self.assertEqual([p.card for p in bench][-1], chosen)
        self.assertEqual((bench[-1].pokemon_id, bench[-1].played_turn), (next_id, TURN))
        self.assertNotIn(chosen, new.players[0].deck)
        self.assertEqual(new.players[0].hand, before_hand)
        self.assertEqual(total_cards(new), before_total)
        log = events(new, len(waiting.log))
        self.assertEqual([e["kind"] for e in log[:2]], ["bench_from_deck", "shuffle"])
        self.assertEqual((log[0]["card"], log[0]["to_pokemon_id"], log[0]["effect"]), (chosen, next_id, f"{JUNGLE_ODDISH}#1"))
        expected = waiting.clone()
        expected.players[0].deck.remove(chosen)
        expected.rng.shuffle(expected.players[0].deck)
        self.assertEqual(new.players[0].deck, expected.players[0].deck)
        self.assertEqual(new.turn_number, TURN + 1)  # ワザを使ったので番は終わる

    def test_the_benched_pokemon_follows_the_normal_evolution_rule(self):
        """山札から出したポケモンの場に出た番は、ワザを使った番（手札から出したときと同じ）。次の自分の番には進化できる（その番の最初から場にいる）。"""
        state = board(mon(BELLSPROUT, (GRASS,)), deck=[BELLSPROUT, GRASS, GRASS, GRASS], hand=[WEEPINBELL])
        new = play(state, UseAttack(0, 1), [lambda d: d.options[:1]])
        benched = new.players[0].bench[-1]
        self.assertEqual(benched.played_turn, TURN)
        new = apply_command(new, EndTurn(1))
        self.assertEqual((new.current_player, new.turn_number), (0, TURN + 2))
        evolved = apply_command(new, EvolvePokemon(0, next(u for u in new.players[0].hand if new.cards[u].card_id == WEEPINBELL), benched.pokemon_id))
        self.assertEqual(evolved.cards[evolved.players[0].bench[-1].card].card_id, WEEPINBELL)

    def test_no_target_in_the_deck(self):
        """山札に選べるものがない（山札 0 枚を含む）: 決定を出さず、ベンチに出さない（p.309 の「処理の対象がない」内容は無視。H5・ゴミあさりと
        同じ読み方）。そのあと山札を切る（0・1 枚なら乱数を使わない）。ワザは使ったことになり、番は終わる。"""
        for deck in ([GRASS, WATER, NIDORAN_F], [GRASS], []):
            state = self.oddish_board(deck)
            new = play(state, UseAttack(0, 1))
            with self.subTest(deck=deck):
                self.assertIsNone(new.decision)
                log = events(new, len(state.log))
                self.assertEqual([e["kind"] for e in log[:3]], ["attack", "bench_from_deck_none", "shuffle"])
                self.assertEqual(len(new.players[0].bench), 0)
                self.assertEqual(new.turn_number, TURN + 1)
                if len(deck) <= 1:
                    probe = state.clone()
                    probe.rng.shuffle(probe.players[0].deck)
                    self.assertEqual(rng_fingerprint(probe.rng), rng_fingerprint(state.rng))

    def test_bench_space_boundary(self):
        """ベンチが 4 匹なら使え、5 匹になる。5 匹（空きがない）なら使えない（``BENCH_FULL``。必要なエネルギーの確認のあと・こんらんのコインの前。
        状態・乱数・ログは変わらない）。"""
        four = self.oddish_board([JUNGLE_ODDISH], bench=[RATTATA] * 4)
        new = play(four, UseAttack(0, 1), [lambda d: d.options[:1]])
        self.assertEqual(len(new.players[0].bench), 5)
        for confused in (False, True):
            full_bench = self.oddish_board([JUNGLE_ODDISH], bench=[RATTATA] * 5, confused=confused)
            snapshot = (full(full_bench), rng_fingerprint(full_bench.rng))
            for mode in PREFLIGHT_MODES:
                with self.subTest(confused=confused, mode=mode), self.assertRaises(IllegalActionError) as raised:
                    apply_kernel(full_bench, UseAttack(0, 1), preflight=mode)
                self.assertEqual(raised.exception.code, "BENCH_FULL")
            self.assertEqual((full(full_bench), rng_fingerprint(full_bench.rng)), snapshot)
        no_energy = board(mon(JUNGLE_ODDISH, (GRASS,)), bench=[RATTATA] * 5, deck=[JUNGLE_ODDISH])
        with self.assertRaises(IllegalActionError) as raised:
            apply_command(no_energy, UseAttack(0, 1))
        self.assertEqual(raised.exception.code, "INSUFFICIENT_ENERGY")

    def test_invalid_answers_keep_the_decision(self):
        """決めるのはワザを使ったプレイヤー。相手の答え・選べるもの以外・0 匹・2 匹は拒否し、決定は待ったまま（状態は変わらない）。"""
        waiting = play(self.oddish_board([JUNGLE_ODDISH, GRASS, JUNGLE_ODDISH]), UseAttack(0, 1))
        d = waiting.decision
        snapshot = full(waiting)
        not_option = waiting.players[0].deck[1]
        for player, choice, code in ((1, d.options[:1], "NOT_YOUR_DECISION"), (0, (not_option,), "INVALID_CHOICE"),
                                     (0, (), "INVALID_CHOICE_COUNT"), (0, tuple(d.options), "INVALID_CHOICE_COUNT")):
            with self.subTest(player=player, choice=choice), self.assertRaises(IllegalActionError) as raised:
                apply_command(waiting, ResolveDecision(player, d.id, tuple(choice)))
            self.assertEqual(raised.exception.code, code)
        self.assertEqual(full(waiting), snapshot)

    def test_confusion(self):
        """こんらん状態: コインが「うら」なら探さず・切らない（こんらんの 20）。「おもて」ならふつうに処理する。"""
        state = self.oddish_board([JUNGLE_ODDISH, GRASS], confused=True)
        tails = play(with_coin_results(state, T), UseAttack(0, 1))
        kinds = [e["kind"] for e in events(tails, len(state.log))]
        self.assertIn("confusion_damage", kinds)
        self.assertFalse({"bench_from_deck", "bench_from_deck_none", "shuffle"} & set(kinds))
        heads = play(with_coin_results(state, H), UseAttack(0, 1), [lambda d: d.options[:1]])
        self.assertEqual(len(heads.players[0].bench), 1)

    def test_hidden_deck_contents_stay_out_of_the_log(self):
        """選べたほかの山札のカードはログに書かない（出したカードは場に出るので公開）。"""
        state = self.oddish_board([JUNGLE_ODDISH, ROCKET_ODDISH, JUNGLE_ODDISH, GRASS])
        waiting = play(state, UseAttack(0, 1))
        chosen = waiting.decision.options[0]
        new = apply_command(waiting, ResolveDecision(0, waiting.decision.id, (chosen,)))
        log = events(new, len(state.log))
        benched = next(e for e in log if e["kind"] == "bench_from_deck")
        self.assertEqual(set(benched), {"kind", "turn", "player", "pokemon", "pokemon_id", "effect", "card", "to_pokemon_id"})
        self.assertEqual(benched["card"], chosen)
        self.assertFalse(any({"options", "cards", "candidates"} & set(e) for e in log if e["kind"] in ("bench_from_deck", "shuffle", "attack")))

    def test_every_search_attack_in_every_preflight_mode(self):
        """4 つのワザ（なかまをよぶ 3・ふえる）を、対象あり（どの答えでも）・対象なし・こんらんで、先読みの方法のどれでも同じ結果。"""
        cases = [(NIDORAN_F, 1, (GRASS, GRASS), [NIDORAN_F, GRASS, NIDORAN_F]), (JUNGLE_ODDISH, 1, (GRASS, GRASS), [ROCKET_ODDISH, JUNGLE_ODDISH]),
                 (BELLSPROUT, 1, (GRASS,), [BELLSPROUT, GRASS]), (KRABBY, 0, (WATER,), [WATER, KRABBY, KRABBY])]
        for (card, index, energy, deck), confused, empty in itertools.product(cases, (False, True), (False, True)):
            extra = {"confusion": True} if confused else {}
            state = board(mon(card, energy, **extra), deck=[] if empty else deck)
            for coins in ((H,), (T,)):
                seeded = with_coin_results(state, *coins)
                results = []
                for mode in PREFLIGHT_MODES:
                    new = apply_kernel(seeded, UseAttack(0, index), preflight=mode)
                    trail = [(full(new), rng_fingerprint(new.rng))]
                    if new.decision is not None:
                        for option in new.decision.options:
                            after = apply_kernel(new, ResolveDecision(0, new.decision.id, (option,)), preflight=mode)
                            trail.append((full(after), rng_fingerprint(after.rng)))
                    results.append(trail)
                with self.subTest(card=card, confused=confused, empty=empty, coins=coins):
                    self.assertEqual(results[1], results[0])
                    self.assertEqual(results[2], results[0])

    def test_copied_search_attack(self):
        """相手のワザを自分のワザとして使う（ピッピ・ピクシーの「ゆびをふる」・カスミのコダックの「ちょうのうりょく」）: ベンチに空きがあれば、使った
        ポケモンの持ち主の山札から説明の名前のたねポケモンを出す。空きがなければ、説明にしたがうピッピ・使えないとするピクシーでは選べず（ほかのワザを
        選ぶ）、条件を書かないカスミのコダックでは決められない（HC9。``UNRESOLVED_COPIED_ATTACK``）。"""
        opponent = mon(KRABBY, (WATER,))
        state = board(mon(CLEFAIRY, (WATER, WATER, WATER)), opponent, deck=[KRABBY, GRASS])
        new = play(state, UseAttack(0, 1), [(0,), lambda d: d.options[:1]])
        self.assertEqual(new.cards[new.players[0].bench[-1].card].card_id, KRABBY)
        self.assertEqual([e["kind"] for e in events(new, len(state.log)) if e["kind"] in ("copy_attack", "bench_from_deck", "shuffle")],
                         ["copy_attack", "bench_from_deck", "shuffle"])
        for copier, energy in ((CLEFAIRY, (WATER, WATER, WATER)), (CLEFABLE, (WATER, WATER, WATER))):
            crowded = board(mon(copier, energy), opponent, bench=[RATTATA] * 5, deck=[KRABBY])
            index = 1 if copier == CLEFAIRY else 0
            waiting = play(crowded, UseAttack(0, index))
            with self.subTest(copier=copier):
                self.assertEqual((waiting.decision.kind, tuple(waiting.decision.options)), (SELECT_ATTACK, (1,)))
        psyduck = with_coin_results(board(mon(MISTYS_PSYDUCK, (PSYCHIC,)), opponent, bench=[RATTATA] * 5, deck=[KRABBY]), H, H, H)
        waiting = play(psyduck, UseAttack(0, 0))
        self.assertEqual(waiting.decision.context_value("unresolved_choices"), (0,))
        with self.assertRaises(UnsupportedError) as raised:
            apply_command(waiting, ResolveDecision(0, waiting.decision.id, (0,)))
        self.assertEqual(raised.exception.code, "UNRESOLVED_COPIED_ATTACK")

    def test_serialization(self):
        """山札から出したポケモンは、どの書き出しの形式でも表せる（場に出た番は形式 7 から。形式 1〜6 はログの ``bench_from_deck`` の番で分かる）。"""
        new = play(self.oddish_board([JUNGLE_ODDISH, GRASS]), UseAttack(0, 1), [lambda d: d.options[:1]])
        self.assertEqual(serialization_problems(new), [])


class CounterDamageTest(unittest.TestCase):
    """ダメージカウンターの数で基本となるダメージ（p.321 の 1 段階）が決まるワザ。じたばた: 自分のカウンターの数 × 10（目安「10×」。コインはない）。
    ヨガのポーズ: 目安 20 + 相手の対戦ポケモンのカウンターの数 × 10（目安「20+」）。弱点・抵抗力・プラスパワー・ディフェンダーはそのあとの段階。"""

    def test_flail_counts_own_counters(self):
        """0 個なら基本となるダメージ 0 で、2 段階までで 0 以下なのでダメージを与えない（プラスパワーも計算しない）。1 個・3 個なら 10・30。弱点は
        そのあと（ヒトカゲは水 ×2）。コインは投げない。キングラーは進化前からのっているカウンターも数える。"""
        cases = [(MAGIKARP, 0, HITMONCHAN, 0), (MAGIKARP, 10, HITMONCHAN, 10), (MAGIKARP, 20, CHARMANDER, 40), (KINGLER, 30, HITMONCHAN, 30),
                 (KINGLER, 50, CHARMANDER, 100)]
        for card, damage, target, expected in cases:
            index = 1 if card == MAGIKARP else 0
            state = board(mon(card, (WATER,), damage=damage), mon(target, (FIGHTING,)))
            new = play(state, UseAttack(0, index))
            with self.subTest(card=card, damage=damage, target=target):
                self.assertEqual(dealt(new, len(state.log)), [expected])
                [log] = events(new, len(state.log), "damage")
                self.assertEqual(log["steps"][0][1], damage)
                self.assertFalse(events(new, len(state.log), "coin_flip"))

    def test_flail_with_pluspower_and_zero_counters(self):
        """0 個のじたばたにプラスパワーがついていても、2 段階までで 0 以下なので計算を終える（ダメージを与えない。v0.11 のいかりのスーパーパンチと
        同じ p.321 の読み方）。1 個ならプラスパワーを足す。"""
        for damage, expected in ((0, 0), (10, 20)):
            state = board(mon(MAGIKARP, (WATER,), damage=damage, trainers=[(PLUSPOWER, TURN)]))
            new = play(state, UseAttack(0, 1))
            with self.subTest(damage=damage):
                self.assertEqual(dealt(new, len(state.log)), [expected])

    def test_flail_can_knock_out(self):
        state = board(mon(KINGLER, (WATER,), damage=50), mon(RATTATA, damage=0))
        new = play(state, UseAttack(0, 0))
        self.assertTrue(any(e["kind"] == "knock_out" for e in events(new, len(state.log))))

    def test_meditate_counts_the_defending_pokemon(self):
        """20 + 相手の対戦ポケモンのカウンター × 10。弱点（エビワラーは超 ×2）。自分のカウンター・自分のベンチのカウンターは数えない。相手の控えに
        カウンターがなければ、読み方（CD4）で答えは変わらないので処理する。"""
        cases = [(0, 0, (), 40), (30, 0, (), 100), (30, 40, (), 100), (30, 0, (mon(RATTATA, damage=20),), 100)]
        for opponent_damage, own_damage, own_bench, expected in cases:
            state = board(mon(JYNX, (PSYCHIC, PSYCHIC, PSYCHIC), damage=own_damage), mon(HITMONCHAN, (FIGHTING,), damage=opponent_damage),
                          bench=own_bench, opponent_bench=(RATTATA, RATTATA))
            new = play(state, UseAttack(0, 1))
            with self.subTest(opponent_damage=opponent_damage, own_damage=own_damage, own_bench=bool(own_bench)):
                self.assertEqual(dealt(new, len(state.log)), [expected])

    def test_meditate_stops_when_the_reading_matters(self):
        """相手の控えポケモンにカウンターがのっていると、「相手のポケモン」が相手の対戦ポケモンか場のポケモンすべてかで基本となるダメージが変わるので、
        決められない（CD4。``UNRESOLVED_OPPONENT_POKEMON_COUNTERS``）。どの先読みの方法でも、こんらんのコインの前に止め、状態・乱数は変わらない。"""
        for confused, opponent_damage in itertools.product((False, True), (0, 30)):
            extra = {"confusion": True} if confused else {}
            state = board(mon(JYNX, (PSYCHIC, PSYCHIC, PSYCHIC), **extra), mon(HITMONCHAN, (FIGHTING,), damage=opponent_damage),
                          opponent_bench=(mon(RATTATA, damage=10),))
            snapshot = (full(state), rng_fingerprint(state.rng))
            for mode in PREFLIGHT_MODES:
                with self.subTest(confused=confused, opponent_damage=opponent_damage, mode=mode), self.assertRaises(UnsupportedError) as raised:
                    apply_kernel(state, UseAttack(0, 1), preflight=mode)
                self.assertEqual(raised.exception.code, "UNRESOLVED_OPPONENT_POKEMON_COUNTERS")
            self.assertEqual((full(state), rng_fingerprint(state.rng)), snapshot)
        # おうふくびんた（同じカードの別のワザ）は止まらない
        state = board(mon(JYNX, (PSYCHIC,)), opponent_bench=(mon(RATTATA, damage=10),))
        self.assertIsNotNone(play(with_coin_results(state, H, T), UseAttack(0, 0)))

    def test_counter_damage_is_not_a_coin_effect(self):
        """じたばた・ヨガのポーズにはコインがないので、「ダメージを受けない」状態の相手でもコインの問い（v0.4b の ``UNRESOLVED_PREVENTED_COIN_DAMAGE``）
        にならず、ダメージの要素が無効になるだけ。"""
        for card, index, energy in ((MAGIKARP, 1, (WATER,)), (JYNX, 1, (PSYCHIC, PSYCHIC, PSYCHIC))):
            state = board(mon(card, energy, damage=20), mon(HITMONCHAN, (FIGHTING,), prevent_damage=TURN - 1))
            new = play(state, UseAttack(0, index))
            with self.subTest(card=card):
                self.assertEqual([e["kind"] for e in events(new, len(state.log), "damage_prevented")], ["damage_prevented"])


class FullDrainTest(unittest.TestCase):
    """きゅうけつ: 「相手にダメージを与えたら、与えたぶんのダメージカウンターを自分からとりのぞく。」与えたダメージ（最終ダメージ。p.319・p.321。
    v0.4d）÷ 10 個を、のっている数まで（p.320）。メガドレイン（半分の切り上げ）とは数だけが違う。"""

    def heal(self, new, since):
        return [(e["dealt"], e["drain_counters"], e["counters"], e["amount"], e["total_damage"]) for e in events(new, since, "drain_heal")]

    def test_heal_amount_follows_the_final_damage(self):
        """与えたダメージは弱点・プラスパワー・ディフェンダーのあとの最終ダメージ（ニョロモは草 ×2）。のっている数まで。相手がきぜつしても回復する
        （与えたダメージは相手の残りの HP で小さくしない）。のっていなければ 0 個（ログは残す）。"""
        cases = [
            ("plain", mon(GOLBAT, (GRASS, GRASS, GRASS), damage=50), mon(HITMONCHAN, (FIGHTING,)), (20, 2, 2, 20, 30)),
            ("weakness", mon(GOLBAT, (GRASS, GRASS, GRASS), damage=50), mon(POLIWAG, (WATER,)), (40, 4, 4, 40, 10)),
            ("pluspower", mon(VENONAT, (GRASS, GRASS), damage=30, trainers=[(PLUSPOWER, TURN)]), mon(HITMONCHAN, (FIGHTING,)), (20, 2, 2, 20, 10)),
            ("cap", mon(FOSSIL_ZUBAT, (GRASS, GRASS), damage=10), mon(POLIWAG, (WATER,)), (20, 2, 1, 10, 0)),
            ("no counters", mon(VENONAT, (GRASS, GRASS)), mon(HITMONCHAN, (FIGHTING,)), (10, 1, 0, 0, 0)),
            ("knock out", mon(GOLBAT, (GRASS, GRASS, GRASS), damage=50), mon(POLIWAG, (WATER,), damage=30), (40, 4, 4, 40, 10)),
        ]
        for name, attacker, opponent, expected in cases:
            state = board(attacker, opponent)
            new = play(state, UseAttack(0, 1))
            with self.subTest(case=name):
                self.assertEqual(self.heal(new, len(state.log)), [expected])
                if name == "knock out":
                    self.assertTrue(events(new, len(state.log), "knock_out"))

    def test_no_heal_without_damage(self):
        """ダメージを与えなかったら（ディフェンダーで最終ダメージ 0・「ダメージを受けない」状態）、とりのぞかない。「ダメージを与えたら」の条件で、
        Z23（「ダメージを与えた後、…」）の問いにはならない（止めない）。"""
        for name, opponent in (("defender", mon(HITMONCHAN, (FIGHTING,), trainers=[(DEFENDER, TURN)])),
                               ("prevented", mon(HITMONCHAN, (FIGHTING,), prevent_damage=TURN - 1))):
            state = board(mon(VENONAT, (GRASS, GRASS), damage=30), opponent)
            new = play(state, UseAttack(0, 1))
            with self.subTest(case=name):
                self.assertEqual(self.heal(new, len(state.log)), [])
                self.assertEqual(new.players[0].active.damage, 30)

    def test_attacker_knocked_out_by_counterattack(self):
        """相手のカイリキーの「はんげき」でワザを使ったポケモンが HP 以上になったら、回復しない（``drain_heal_skipped``。v0.10 の C16）。"""
        state = board(mon(GOLBAT, (GRASS, GRASS, GRASS), damage=50), mon(MACHAMP, (FIGHTING,)))
        new = play(state, UseAttack(0, 1))
        self.assertEqual(self.heal(new, len(state.log)), [])
        self.assertEqual([e["kind"] for e in events(new, len(state.log), "drain_heal_skipped")], ["drain_heal_skipped"])

    def test_mega_drain_keeps_the_half(self):
        """メガドレインは与えたダメージの半分（切り上げ）のまま（v0.4d。``Drain`` の ``full`` は偽）。"""
        state = board(mon(BUTTERFREE, (GRASS, GRASS, GRASS, GRASS), damage=60), mon(HITMONCHAN, (FIGHTING,)))
        new = play(state, UseAttack(0, 1))
        self.assertEqual(self.heal(new, len(state.log)), [(40, 2, 2, 20, 40)])


# 先読みの方法ごとの一致を確かめる相手の盤面（相手の対戦ポケモン, 相手の控え）
PARITY_OPPONENTS = {
    "plain": (mon(HITMONCHAN, (FIGHTING, FIGHTING)), (RATTATA,)),
    "hurt": (mon(HITMONCHAN, (FIGHTING,), damage=50), (RATTATA,)),
    "defender": (mon(HITMONCHAN, (FIGHTING,), trainers=[(DEFENDER, TURN)]), (RATTATA,)),
    "hurt bench": (mon(POLIWAG, (WATER,), damage=20), (mon(RATTATA, damage=10),)),
    "machamp": (mon(MACHAMP, (FIGHTING,)), ()),
}


class PreflightParityTest(unittest.TestCase):
    """26 のワザを、相手の状態・自分のダメージ・こんらん・コインの組み合わせで使い、先読みの方法のどれでも結果（受け付けたら形式 10 の書き出しと乱数、
    拒否したら例外の型とコード）が同じ（決定には最初の選べるものから答える）。"""

    def outcome(self, state, command, mode):
        try:
            new = apply_kernel(state, command, preflight=mode)
            out = [(full(new), rng_fingerprint(new.rng))]
            if new.decision is not None and new.decision.resume == "attack":
                d = new.decision
                new = apply_kernel(new, ResolveDecision(d.player, d.id, tuple(d.options[:max(1, d.min_choices)])), preflight=mode)
                out.append((full(new), rng_fingerprint(new.rng)))
            return out
        except EngineError as error:
            return [(type(error).__name__, error.code)]

    def test_every_attack_in_every_mode(self):
        pool = load_card_pool()
        energy_of = {"water": WATER, "psychic": PSYCHIC, "grass": GRASS, "fighting": FIGHTING}
        checked = 0
        for (card, index), (name, (opponent, opponent_bench)), damage, confused, coins in itertools.product(
                EXPECTED, PARITY_OPPONENTS.items(), (0, 30), (False, True), ((H,) * 4, (T,) * 4, (H, T, T, H))):
            cost = pool.get(card).attacks[index].cost
            energy = [energy_of.get(t.value, GRASS) for t in cost]
            attacker = mon(card, energy, damage=damage, **({"confusion": True} if confused else {}))
            state = with_coin_results(build_test_state([
                {"active": attacker, "bench": [RATTATA], "deck": [GRASS, card, WATER, NIDORAN_F, KRABBY, JUNGLE_ODDISH, BELLSPROUT]},
                {"active": opponent, "bench": list(opponent_bench), "deck": [GRASS] * 6},
            ], turn_number=TURN), *coins)
            results = [self.outcome(state, UseAttack(0, index), mode) for mode in PREFLIGHT_MODES]
            with self.subTest(card=card, attack=index, opponent=name, damage=damage, confused=confused, coins=coins[:2]):
                self.assertEqual(results[1], results[0])
                self.assertEqual(results[2], results[0])
            checked += 1
        self.assertEqual(checked, 26 * 5 * 2 * 2 * 3)


if __name__ == "__main__":
    unittest.main()
