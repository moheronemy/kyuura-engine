"""v0.51: トラッシュのたねポケモンを持ち主のベンチに出す共通の処理と、それを使う 3 枚（docs/discard-to-bench-v0.51.md）。

3 枚: ナツメのスリーパー（PMCG6-051。よみがえらせる・ふりこののろい）・元気のかけら（PMCG1-078。トレーナー）・ポケモンの笛（PMCG1-084。トレーナー）。どれも kyuura データの採用
（処理に使う文面は kyuura の印刷の文面。採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合。ガイドブックは読んでいない。英語版の文面・のちの版の
文面で、日本語版の条件を補わない。

根拠にした既存の記録（研究の基準のコミットの kyuura の記録。``research_links.json`` の ``applied_rule_records``）: GR-2000-P309-ATTACK-PROCEDURE（ワザの内容の処理の対象が
なければ、その部分は何もしない）・GR-2000-P319-HP-AND-DAMAGE（ダメージカウンター 1 個は 10 ダメージ）・GR-2000-P320-COUNTER-MOVE（ダメージカウンターをのせる効果はワザによる
ダメージではない）と、エンジンの v0.2b（トレーナーの決定）・v0.4a（場に出た番と進化の制限）・v0.32（山札からベンチに出す ``zones.enter_play``）・v0.35（コインを「おもて」の数で
まとめる先読み）・v0.41（ダメージカウンターをのせるログ ``place_damage_counters``）・v0.43（場に出たときの特殊能力の経路）・v0.44（サカキの許可）・v0.46（トレーナーの使用の禁止）・
v0.47（なにかの化石・ピッピ人形はトラッシュではトレーナーカード・期限のあるトレーナーの使用の禁止）・v0.48（今有効な最大HP）・v0.49（ワザの出どころ）の記録。

新しい停止コードは 2: RV1・FT1（docs 6 章）。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import unittest
from unittest import mock

from kyuura_engine import (
    EndTurn,
    EvolvePokemon,
    IllegalActionError,
    Phase,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    check_invariants,
    max_hp,
    observe,
    state_to_dict,
    visible_log,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, pool_from_extract, read_extract
from kyuura_engine.decisions import BENCH_FROM_DISCARD, SELECT_ATTACK, SELECT_POKEMON
from kyuura_engine.observation import OPTION_MEANINGS, PUBLIC_EVENTS
from kyuura_engine.resolution import PREFLIGHT_MODES, contract, programs, v013_checks
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.zones import bench_from_discard
from scripts import check_card_sources as cs
from tests.helpers import assert_stop_code_counts_since
from tests.helpers import (
    V0_69_STOP_CODE_ISSUES,
    kyuura_records_since_v0_69,
    ABRA,
    ATTACK_TYPES_SINCE_V0_17,
    CATERPIE,
    CHANSEY,
    CLEFAIRY,
    CLEFAIRY_DOLL,
    DARK_DRAGONITE,
    DARK_GLOOM,
    DARK_VILEPLUME,
    DEFENDER,
    DITTO,
    FIGHTING,
    FOSSIL_PSYDUCK,
    GIOVANNI,
    GIOVANNIS_GYARADOS,
    GIOVANNIS_MAGIKARP,
    GIOVANNIS_PERSIAN,
    HITMONCHAN,
    KADABRA,
    MAGIKARP,
    METAPOD,
    MYSTERIOUS_FOSSIL,
    POKEMON_FLUTE,
    PSYCHIC,
    RATICATE,
    RATTATA,
    REVIVE,
    ROCKET_ODDISH,
    SABRINAS_ABRA,
    SABRINAS_ALAKAZAM,
    SABRINAS_DROWZEE,
    SABRINAS_GASTLY,
    SABRINAS_HYPNO,
    SABRINAS_KADABRA,
    V0_51_CARDS,
    V0_51_POKEMON,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import observation_problems, serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "discard-to-bench-v0.51.md"
TURN = 7
P, W, F = PSYCHIC, WATER, FIGHTING
RV1 = "UNRESOLVED_REVIVE_WITHOUT_TARGET"
FT1 = "UNRESOLVED_POKEMON_FLUTE_WITHOUT_TARGET"
PREVENTED = "UNRESOLVED_PREVENTED_COIN_DAMAGE"
NEW_CODES = (RV1, FT1)
APPLIED_RECORDS = ("GR-2000-P309-ATTACK-PROCEDURE", "GR-2000-P319-HP-AND-DAMAGE", "GR-2000-P320-COUNTER-MOVE")
# pcg-search.com の対象の版（サイトの一覧の番号）
EDITIONS = {SABRINAS_HYPNO: "053/098", REVIVE: "075/096", POKEMON_FLUTE: "092/096"}
RESULTS = {SABRINAS_HYPNO: "differences", REVIVE: "match", POKEMON_FLUTE: "match"}
# 進化しているポケモンの下のカード（build_test_state の "evolved_from"）
BELOW = {SABRINAS_HYPNO: SABRINAS_DROWZEE, KADABRA: ABRA, RATICATE: RATTATA, METAPOD: CATERPIE, DARK_VILEPLUME: [ROCKET_ODDISH, DARK_GLOOM],
         SABRINAS_KADABRA: SABRINAS_ABRA, SABRINAS_ALAKAZAM: [SABRINAS_ABRA, SABRINAS_KADABRA], GIOVANNIS_GYARADOS: GIOVANNIS_MAGIKARP}
FULL_BENCH = (RATTATA,) * 5


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def bench_spec(b):
    return mon(b) if isinstance(b, str) else b


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), hand=(), opponent_hand=(), discard=(), opponent_discard=(),
          turn=TURN, current=0):
    me = {"active": active, "bench": [bench_spec(b) for b in bench], "hand": list(hand), "discard": list(discard)}
    them = {"active": opponent or mon(HITMONCHAN, (F, F, F)), "bench": [bench_spec(b) for b in opponent_bench], "hand": list(opponent_hand),
            "discard": list(opponent_discard)}
    return build_test_state([me, them], turn_number=turn, current_player=current)


def full(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS))


def snapshot(state):
    return full(state), [dict(e) for e in state.log], repr(state.rng.getstate())


def audited(test, state):
    """不変条件・書き出し・観測の監査（盤面を直接作ったテスト。ログの監査は正式な対戦のテストで確かめる）。"""
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])
    return state


def events(state, since, kind=None):
    return [dict(e) for e in state.log[since:] if kind is None or e["kind"] == kind]


def kinds(state, since):
    return [e["kind"] for e in state.log[since:]]


def answer(state, choices, *, mode="derived"):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)), preflight=mode)


def assert_rejected(test, state, command, code, exception=IllegalActionError, *, modes=("derived",)):
    """``code`` で拒否し、状態・乱数・ログが変わらない。"""
    before = snapshot(state)
    for mode in modes:
        with test.subTest(mode=mode), test.assertRaises(exception) as raised:
            apply_kernel(state, command, preflight=mode)
        test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def discard_uid(state, player, card, nth=0):
    return [u for u in state.players[player].discard if state.cards[u].card_id == card][nth]


def hand_uid(state, player, card):
    return [u for u in state.players[player].hand if state.cards[u].card_id == card][0]


def by_id(state, pid):
    return state.find_pokemon(pid)[1]


def invigorate(state, *, player=0, card=None, mode="derived"):
    """よみがえらせる（ワザの位置 0）を宣言する（決定を待つ状態を返す）。"""
    return apply_kernel(state, UseAttack(player, 0, card=card), preflight=mode)


def play(state, trainer, *, player=0):
    return apply_kernel(state, PlayTrainer(player, hand_uid(state, player, trainer)))


# ---------------------------------------------------------------- 登録・写し・記録


class CardDataTest(unittest.TestCase):
    """3 枚の写し・登録・記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_three_requested_cards(self):
        """写しの組 pool_v0_51 は依頼の 3 枚（並び）。どれも対応で、どのワザも、どのトレーナーの効果も登録した。ナツメのスリープ（進化元）は v0.37 から対応。"""
        self.assertEqual(read_extract()["pool_v0_51"], list(V0_51_CARDS))
        self.assertEqual(V0_51_POKEMON, (SABRINAS_HYPNO,))
        hypno = self.pool.get(SABRINAS_HYPNO)
        self.assertEqual((hypno.name_ja, hypno.stage, hypno.evolves_from, hypno.hp, hypno.pokemon_type, hypno.weakness, hypno.retreat_cost),
                         ("ナツメのスリーパー", "stage1", "ナツメのスリープ", 70, EnergyType.PSYCHIC, EnergyType.PSYCHIC, 2))
        self.assertEqual([(a.name_ja, a.damage, a.damage_modifier) for a in hypno.attacks], [("よみがえらせる", None, None), ("ふりこののろい", 20, "×")])
        self.assertEqual(hypno.powers, ())
        self.assertTrue(self.pool.is_playable(SABRINAS_DROWZEE))
        for card, name in ((REVIVE, "元気のかけら"), (POKEMON_FLUTE, "ポケモンの笛")):
            definition = self.pool.get(card)
            self.assertEqual((definition.name_ja, definition.category), (name, "trainer"))
        for card in V0_51_CARDS:
            with self.subTest(card=card):
                self.assertTrue(self.pool.is_playable(card))
        # どれかの登録を除くと対応にならない
        for key in (E.AttackKey(SABRINAS_HYPNO, 0), E.AttackKey(SABRINAS_HYPNO, 1)):
            with self.subTest(key=key):
                effects = E.DEFAULT_EFFECTS.without_attacks(f"test-no-{key}", [key])
                self.assertFalse(pool_from_extract(read_extract(), effects).is_playable(SABRINAS_HYPNO))
        for card in (REVIVE, POKEMON_FLUTE):
            with self.subTest(card=card):
                effects = E.DEFAULT_EFFECTS.without_trainers(f"test-no-{card}", [card])
                self.assertFalse(pool_from_extract(read_extract(), effects).is_playable(card))

    def test_registrations_use_kyuura_printed_text(self):
        """処理に使う文面は kyuura の印刷の文面（LD-・エラッタはない）。実装の型の ``check`` は文面と値の組を確かめる。"""
        hypno = self.pool.get(SABRINAS_HYPNO)
        invig = E.DEFAULT_EFFECTS.attack_entry(SABRINAS_HYPNO, 0)
        curse = E.DEFAULT_EFFECTS.attack_entry(SABRINAS_HYPNO, 1)
        self.assertEqual(invig.effect, E.BenchBasicFromEitherDiscard())
        self.assertEqual(curse.effect, E.CoinsPerDefenderCountersDamage(20))
        for entry, attack in ((invig, hypno.attacks[0]), (curse, hypno.attacks[1])):
            with self.subTest(attack=attack.name_ja):
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                                 (attack.name_ja, attack.text_ja, attack.text_ja, cs.PRINTED_TEXT_SOURCE))
                self.assertEqual(entry.effect.check(attack), [])
                self.assertTrue(entry.effect.check(dataclasses.replace(attack, text_ja=attack.text_ja + "あ")))
        # ふりこののろいは「×」のワザ（目安の数字 20 が「おもて」1 回あたりの数）。「+」・数の違う登録は受け付けない
        self.assertTrue(curse.effect.check(dataclasses.replace(hypno.attacks[1], damage_modifier="+")))
        self.assertTrue(E.CoinsPerDefenderCountersDamage(10).check(hypno.attacks[1]))
        # よみがえらせるはダメージの目安のないワザ
        self.assertTrue(invig.effect.check(dataclasses.replace(hypno.attacks[0], damage=10)))
        for card, effect_type in ((REVIVE, E.BenchBasicFromOwnDiscardWithCounters), (POKEMON_FLUTE, E.BenchBasicFromOpponentDiscard)):
            with self.subTest(card=card):
                trainer = E.DEFAULT_EFFECTS.trainer_entry(card)
                printed = self.pool.get(card).trainer_text_ja
                self.assertIsInstance(trainer.effect, effect_type)
                self.assertEqual((trainer.text_ja, trainer.play_text_ja, trainer.source), (printed, printed, cs.PRINTED_TEXT_SOURCE))
                self.assertEqual(trainer.effect.check(self.pool.get(card)), [])
                self.assertTrue(trainer.effect.check(dataclasses.replace(self.pool.get(card), trainer_text_ja=printed + "あ")))
                # 使い終えたあとのきぜつの処理はしない（カウンターは HP の半分で、きぜつしない）。v0.50 の after_trainer を一律に当てはめない
                self.assertFalse(trainer.effect.may_knock_out)
        # 2 枚のトレーナーは同じ部品の別の型で、文面を取りちがえて登録できない
        self.assertTrue(E.BenchBasicFromOpponentDiscard().check(self.pool.get(REVIVE)))
        self.assertTrue(E.BenchBasicFromOwnDiscardWithCounters().check(self.pool.get(POKEMON_FLUTE)))

    def test_new_attack_types_stay_outside_the_v013_contract(self):
        """v0.51 のワザの型は要素の並び（BUILDERS）で処理する。v0.13 の約束の型（``v013_checks.VERIFIED``）には入れない。"""
        for effect_type in (E.BenchBasicFromEitherDiscard, E.CoinsPerDefenderCountersDamage):
            with self.subTest(effect_type=effect_type.__name__):
                self.assertIn(effect_type, ATTACK_TYPES_SINCE_V0_17)
                self.assertNotIn(effect_type, v013_checks.VERIFIED)
                self.assertIn(effect_type, programs.BUILDERS)
        for index in (0, 1):
            self.assertFalse(contract.is_contract(contract.program_for(E.DEFAULT_EFFECTS.attack_entry(SABRINAS_HYPNO, index).effect)))
        # よみがえらせるのダメージカウンターは場のポケモンへのワザの効果（「ワザをうけない」状態・「とうめい」を評価する。相手のポケモンにも与える）
        self.assertEqual(E.BenchBasicFromEitherDiscard.opponent_effect_elements, (E.COUNTERS_ELEMENT,))
        self.assertEqual(programs.BUILDERS[E.CoinsPerDefenderCountersDamage](E.CoinsPerDefenderCountersDamage(20)),
                         (programs.Damage(programs.OPP, programs.HeadsPerDefenderCounters(20)),))
        self.assertTrue(programs.HeadsPerDefenderCounters.by_heads)
        # 「いかりのスーパーパンチ」（コイン 1 枚・自分のカウンター）とは別の値・別の型
        self.assertIsNot(programs.HeadsPerDefenderCounters, programs.HeadsOwnCounters)

    def test_adoption_records_and_external_checks(self):
        """採用の記録（kyuura データの採用）と pcg-search.com の同じ版との照合。ガイドブックの項目は書かない。"""
        records = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        for card in V0_51_CARDS:
            with self.subTest(card=card):
                record = records[card]
                self.assertEqual((record["basis"], record["status"]), ("kyuura_data", "adopted"))
                self.assertEqual(record["kyuura_records"], kyuura_records_since_v0_69(card))  # v0.69: 研究の基準を上げて加わった kyuura の記録（tests/helpers.py の V0_69_KYUURA_RECORDS_ADDED）
                checks = record["external_checks"]
                self.assertEqual(len(checks), 1)
                self.assertTrue(checks[0]["url"].startswith("https://pcg-search.com/"))
                self.assertEqual(checks[0]["edition"]["list_number"], EDITIONS[card])
                self.assertEqual(checks[0]["result"], RESULTS[card])
                for forbidden in ("page", "pdf_page", "latest_description_ja", "card_image_text_ja"):
                    self.assertNotIn(forbidden, json.dumps(record, ensure_ascii=False).replace("list_number", ""))
        # ナツメのスリーパーの違いは「切り捨て」と「切りすて」の表記だけで、処理は変わらない
        (difference,) = records[SABRINAS_HYPNO]["external_checks"][0]["differences"]
        self.assertEqual((difference["field"], difference["affects_behavior"]), ("pokemon.attacks[0].text.ja", False))
        self.assertEqual(difference["kyuura"].replace("切り捨て", "切りすて"), difference["pcg_search"])
        self.assertEqual(cs.problems(), [])

    def test_research_links(self):
        """新しい停止コード 2 は kyuura の未解決の一覧にない（``not_in_kyuura``）。再利用した 3 つの記録は ``applied_rule_records`` に id だけで結ぶ。"""
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        for code in NEW_CODES:
            with self.subTest(code=code):
                self.assertEqual((links["stop_codes"][code]["kyuura_disposition"], links["stop_codes"][code]["kyuura_issue"]), ("issue", V0_69_STOP_CODE_ISSUES[code]))  # v0.69: kyuura が論点に結んだ（v0.68 までは not_in_kyuura。tests/helpers.py の V0_69_STOP_CODE_ISSUES）
                self.assertEqual([(r["version"], r["document"]) for r in links["stop_codes"][code]["engine_rulings"]],
                                 [("v0.51", "docs/discard-to-bench-v0.51.md")])
        assert_stop_code_counts_since(self, links, 149, 151)  # v0.72: 総数の等号は test_research_links_v0_18e が確かめる。  # v0.68 で DR8・DR13 を加えた。v0.52 で FJ1・SU1・SU2、v0.53 で ST1・NG1 を加えた、v0.55 で MW1・EM1・SP1・FH1・GL1・GL2・SB1・SB2 を加えた、v0.56 で LS1・RT1・RG1・MY1・MS1・KG1 を加えた、v0.57 で STB1・TG1・FG1・FG2・EX1・VG1・VM1・CH1、v0.58 で RB1〜RB4・TE2・RT1 を加えた、v0.59 で GG1・BL1・CB1・BZ1〜BZ4 を加えた。v0.60 で TS1 を加え、コードのない SS1 を数えた。v0.61 で SH1・SC1・SC2・TD1 を加え、Z9 に停止コードを付けた。v0.62 で MM1・MM2・OM1・OM2 を加え、コードのない ED1 を数えた。v0.63 で QZ1 を加えた  # v0.65 で NT1〜NT3・RX1・FL1・BG1・BG2・KD1 を加えた。v0.66 で CA1・ES1〜ES3 を加えた  # v0.67 で FD1・FD2 を加えた
        applied = [record["kyuura_record"] for record in links["applied_rule_records"]
                   if any(engine["version"] == "v0.51" for engine in record["engine"])]
        self.assertEqual(sorted(applied), sorted(APPLIED_RECORDS))
        adopted = links["latest_descriptions"]["adopted_printed_text"]
        self.assertTrue({f"{SABRINAS_HYPNO}/attack/0", f"{SABRINAS_HYPNO}/attack/1"} <= set(adopted))

    def test_public_events_and_option_meaning(self):
        """出したカード・出さなかったこと・出せるカードがなかったことは公開（トラッシュと場は公開の情報）。決定の選べるものはトラッシュのカード。"""
        self.assertTrue({"bench_from_discard", "bench_from_discard_declined", "bench_from_discard_none"} <= PUBLIC_EVENTS)
        self.assertEqual(OPTION_MEANINGS[BENCH_FROM_DISCARD], "card")

    def test_no_basic_pokemon_has_an_entry_power(self):
        """場に出たときに使える特殊能力（``EntryPower``）を持つカードは、v0.85 までどれも進化カード（トラッシュから出せるたねポケモンにはない）だった。v0.86 でエンテイ
        （neo3-010）の［おたけび］を加えたが「手札から場に出した時」（``from_hand_only``）なので、トラッシュから出しても使う機会はない（``discard_entry_power_guard`` は止めない）。
        「場に出た時」の使う機会を決める場面は、今の対応カードでは起こらない（「場に出た時」の特殊能力を持つたねポケモンはない）。v0.96 のアンノーン[E]（PF2-002。［ENGAGE］）・
        アンノーン[R]（PRN-035。［REASSURE］）も「手札から場に出したとき」なので同じ（docs/unown-family-powers-v0.96.md 4 章）。v0.97 のアンノーンI（neo2-023。［INCREASE］）も
        同じ（docs/unown-research-idfnj-v0.97.md 6 章）。v0.98 のアンノーンV（neo4-053。［VANISH］）も同じ（docs/unown-bear-yield-vanish-give-v0.98.md 5 章）。"""
        entry_cards = set()
        for key in E.DEFAULT_EFFECTS.power_keys():
            entry = E.DEFAULT_EFFECTS.power_entry(key.card_id, key.power_index)
            if isinstance(entry.effect, E.EntryPower):
                entry_cards.add(key.card_id)
        self.assertTrue(entry_cards)
        for card in sorted(entry_cards):
            with self.subTest(card=card):
                if self.pool.get(card).stage == "basic":
                    self.assertIn(card, ("neo3-010", "PF2-002", "PRN-035", "neo2-023", "neo4-053"))
                    self.assertTrue(E.DEFAULT_EFFECTS.power_entry(card, 0).effect.from_hand_only)
                else:
                    self.assertNotEqual(self.pool.get(card).stage, "basic")


# ---------------------------------------------------------------- 共通の処理


class CommonProcessingTest(unittest.TestCase):
    """``zones.bench_from_discard`` と ``effects`` の共通の部品（3 枚で共通）。"""

    def test_moves_the_same_card_and_issues_a_new_pokemon(self):
        """同じ uid・持ち主のまま、持ち主のトラッシュから持ち主のベンチの最後へ。新しい場のポケモンの番号・場に出た番は今の番。ダメージ・特殊状態・エネルギー・
        ついているカード・持続する効果・使用の記録はない（トラッシュに置かれる前のものを引き継がない）。手札・山札・乱数・ログは変えない（ログは呼ぶ側）。"""
        state = board(mon(HITMONCHAN), opponent_discard=(RATTATA, HITMONCHAN))
        card = discard_uid(state, 1, HITMONCHAN)
        before = (list(state.players[1].hand), list(state.players[1].deck), repr(state.rng.getstate()), len(state.log), state.next_pokemon_id)
        pokemon = bench_from_discard(state, card)
        p = state.players[1]
        self.assertIs(p.bench[-1], pokemon)
        self.assertEqual((pokemon.card, state.cards[card].owner, pokemon.pokemon_id, pokemon.played_turn), (card, 1, before[4], TURN))
        self.assertEqual((pokemon.damage, pokemon.energy, pokemon.trainers, pokemon.evolution_stack, pokemon.persistent_effects, pokemon.attacks_used_once),
                         (0, [], [], (), (), ()))
        self.assertEqual(pokemon.conditions.names(), ())
        self.assertNotIn(card, p.discard)
        self.assertEqual([state.cards[u].card_id for u in p.discard], [RATTATA])
        self.assertEqual((list(p.hand), list(p.deck), repr(state.rng.getstate()), len(state.log), state.next_pokemon_id),
                         (before[0], before[1], before[2], before[3], before[4] + 1))
        audited(self, state)

    def test_counters_are_placed_before_entering(self):
        """``counters``: ベンチに出す前にのせる数（元気のかけら）。"""
        state = board(mon(HITMONCHAN), discard=(HITMONCHAN,))
        pokemon = bench_from_discard(state, discard_uid(state, 0, HITMONCHAN), counters=3)
        self.assertEqual(pokemon.damage, 30)

    def test_rejects_calls_outside_its_contract(self):
        """カードが持ち主のトラッシュにない・たねポケモンでない（進化カード・エネルギー・なにかの化石・ピッピ人形・トレーナー）・持ち主のベンチに空きがない・のせる数が負・
        知らない uid は、確認の漏れなので ``RuntimeError``（状態を変える前）。"""
        state = board(mon(HITMONCHAN), hand=(RATTATA,), bench=FULL_BENCH[:4],
                      discard=(RATICATE, P, MYSTERIOUS_FOSSIL, CLEFAIRY_DOLL, REVIVE, RATTATA), opponent_bench=FULL_BENCH, opponent_discard=(RATTATA,))
        cases = {
            "hand": hand_uid(state, 0, RATTATA),
            "stage1": discard_uid(state, 0, RATICATE),
            "energy": discard_uid(state, 0, P),
            "fossil": discard_uid(state, 0, MYSTERIOUS_FOSSIL),
            "doll": discard_uid(state, 0, CLEFAIRY_DOLL),
            "trainer": discard_uid(state, 0, REVIVE),
            "owner_bench_full": discard_uid(state, 1, RATTATA),
            "unknown": 10_000,
        }
        before = snapshot(state)
        for label, card in cases.items():
            with self.subTest(label=label), self.assertRaises(RuntimeError):
                bench_from_discard(state, card)
        with self.assertRaises(RuntimeError):
            bench_from_discard(state, discard_uid(state, 0, RATTATA), counters=-1)
        self.assertEqual(snapshot(state), before)
        # ベンチが 4 匹ならもう 1 匹出せる（共通のルールの値 rules.max_bench = 5）
        self.assertEqual(state.rules.max_bench, 5)
        bench_from_discard(state, discard_uid(state, 0, RATTATA))
        self.assertEqual(len(state.players[0].bench), 5)

    def test_candidates_and_half_hp(self):
        """選べるのはトラッシュにある間の定義がたねポケモンのカード（トラッシュの並び）。持ち主のベンチに空きのないカードは入らない（持ち主の側で確かめる）。
        HP の半分はダメージカウンターの単位で切り捨て。"""
        state = board(mon(HITMONCHAN), discard=(P, RATTATA, RATICATE, MYSTERIOUS_FOSSIL, CLEFAIRY_DOLL, HITMONCHAN), opponent_discard=(MAGIKARP, KADABRA),
                      opponent_bench=FULL_BENCH)
        own = (discard_uid(state, 0, RATTATA), discard_uid(state, 0, HITMONCHAN))
        # v0.114: 説明の版（v0.51 のカードはどれもネオより前。effects.TEXT_ERAS）を渡す
        self.assertEqual(E.discard_basic_pokemon(state, 0, E.TEXT_PRE_NEO), own)
        self.assertEqual(E.discard_basic_pokemon(state, 1, E.TEXT_PRE_NEO), (discard_uid(state, 1, MAGIKARP),))
        self.assertEqual(E.bench_from_discard_candidates(state, (0, 1), E.TEXT_PRE_NEO), own)
        self.assertEqual(E.bench_from_discard_candidates(state, (1, 0), E.TEXT_PRE_NEO), own)
        for hp, counters in ((30, 1), (40, 2), (50, 2), (60, 3), (70, 3), (120, 6), (10, 0)):
            with self.subTest(hp=hp):
                self.assertEqual(E.half_hp_counters(state, hp), counters)
        for hp in (None, 0, -10, 55):
            with self.subTest(hp=hp), self.assertRaises(RuntimeError):
                E.half_hp_counters(state, hp)

    def test_entry_power_guard(self):
        """「手札から出した時」の特殊能力はトラッシュからの経路では機会がない（止めない）。「場に出た時」の特殊能力のカードをトラッシュから出すことは今の対応カードでは
        起こらない（来たら RuntimeError）。どちらも進化カードなので、ここではトラッシュに置いて関数だけを確かめる。"""
        state = board(mon(HITMONCHAN), discard=(GIOVANNIS_PERSIAN, DARK_DRAGONITE, RATTATA))
        self.assertTrue(E.entry_power(state, discard_uid(state, 0, GIOVANNIS_PERSIAN))[1].from_hand_only)
        E.discard_entry_power_guard(state, discard_uid(state, 0, GIOVANNIS_PERSIAN))
        E.discard_entry_power_guard(state, discard_uid(state, 0, RATTATA))
        self.assertFalse(E.entry_power(state, discard_uid(state, 0, DARK_DRAGONITE))[1].from_hand_only)
        with self.assertRaises(RuntimeError):
            E.discard_entry_power_guard(state, discard_uid(state, 0, DARK_DRAGONITE))

    def test_printed_hp_equals_effective_max_hp_on_entry_for_every_basic(self):
        """元気のかけら（「のせた状態でベンチに出す」。出す前の HP）とよみがえらせる（「ベンチに出す。そして、…のせる」。出したあとの今有効な最大HP）の順番の違いは、
        今の対応カードのたねポケモンでは結果を変えない: 登録のどのたねポケモンも、ベンチに出した直後の今有効な最大HP（``max_hp``）は印刷の HP と同じ（［ガスのからだ］の
        ナツメのゴースも、エネルギーがついていないので同じ）。"""
        pool = load_card_pool()
        basics = sorted(c for c, d in pool.definitions.items() if pool.is_playable(c) and d.is_basic_pokemon)
        self.assertGreater(len(basics), 100)
        self.assertIn(SABRINAS_GASTLY, basics)
        self.assertIn(DITTO, basics)
        for card in basics:
            state = board(mon(HITMONCHAN), opponent=mon(SABRINAS_HYPNO), bench=(), discard=(card,))
            pokemon = bench_from_discard(state, state.players[0].discard[0])
            with self.subTest(card=card):
                self.assertEqual(max_hp(state, pokemon), pool.get(card).hp)


# ---------------------------------------------------------------- よみがえらせる


class InvigorateTest(unittest.TestCase):
    """ナツメのスリーパーの「よみがえらせる」（超）: 自分または相手のトラッシュから「たねポケモン」を 1 枚選び出し、持ち主のベンチに出す。そして、そのポケモンに、
    HP の半分（切り捨て）のダメージカウンターをのせる。"""

    def test_options_are_basics_from_both_trashes(self):
        """選ぶのはワザを使ったプレイヤー。選べるものは自分のトラッシュ → 相手のトラッシュの、たねポケモンのカード（トラッシュの並び。進化カード・エネルギー・
        トレーナー・なにかの化石・ピッピ人形は入らない）。1 枚（省略できない）。"""
        state = board(mon(SABRINAS_HYPNO, (P,)), discard=(RATICATE, P, RATTATA, MYSTERIOUS_FOSSIL, HITMONCHAN),
                      opponent_discard=(CLEFAIRY_DOLL, MAGIKARP, W, KADABRA))
        state = audited(self, invigorate(state))
        d = state.decision
        expected = (discard_uid(state, 0, RATTATA), discard_uid(state, 0, HITMONCHAN), discard_uid(state, 1, MAGIKARP))
        self.assertEqual((d.kind, d.player, d.options, d.resume, d.min_choices, d.max_choices), (BENCH_FROM_DISCARD, 0, expected, "attack", 1, 1))
        for choices, code in (((), "INVALID_CHOICE_COUNT"), ((expected[0], expected[1]), "INVALID_CHOICE_COUNT"),
                              ((discard_uid(state, 0, RATICATE),), "INVALID_CHOICE"), ((discard_uid(state, 1, KADABRA),), "INVALID_CHOICE"),
                              ((discard_uid(state, 0, MYSTERIOUS_FOSSIL),), "INVALID_CHOICE")):
            with self.subTest(choices=choices):
                assert_rejected(self, state, ResolveDecision(0, d.id, choices), code)

    def test_own_card_goes_to_own_bench_with_half_hp_counters(self):
        """自分のカード（エビワラー。HP 70）は自分のベンチの最後に、新しい場のポケモンの番号で出る（場に出た番は今の番）。そのあと 3 個（70 の半分 35 を切り捨て）の
        ダメージカウンターをのせる（ダメージではない。ログ ``place_damage_counters``）。ワザなので番は終わる。"""
        state = invigorate(board(mon(SABRINAS_HYPNO, (P,)), discard=(HITMONCHAN,)))
        card = discard_uid(state, 0, HITMONCHAN)
        hypno = state.players[0].active
        new_id = state.next_pokemon_id
        since = len(state.log)
        state = audited(self, answer(state, [card]))
        pokemon = state.players[0].bench[-1]
        self.assertEqual((pokemon.card, pokemon.pokemon_id, pokemon.played_turn, pokemon.damage, pokemon.energy), (card, new_id, TURN, 30, []))
        self.assertNotIn(card, state.players[0].discard)
        moved, placed = events(state, since, "bench_from_discard")[0], events(state, since, "place_damage_counters")[0]
        self.assertEqual({k: moved[k] for k in ("player", "by_player", "card", "from_zone", "to_zone", "to_pokemon_id", "pokemon", "pokemon_id", "effect")},
                         {"player": 0, "by_player": 0, "card": card, "from_zone": "discard", "to_zone": "bench", "to_pokemon_id": new_id,
                          "pokemon": hypno.card, "pokemon_id": hypno.pokemon_id, "effect": f"{SABRINAS_HYPNO}#0"})
        self.assertNotIn("counters", moved)
        self.assertEqual((placed["player"], placed["pokemon_id"], placed["counters"], placed["amount"], placed["damage_before"], placed["total_damage"]),
                         (0, new_id, 3, 30, 0, 30))
        self.assertEqual(kinds(state, since)[:3], ["bench_from_discard", "place_damage_counters", "turn_end"])
        self.assertEqual(events(state, since, "damage"), [])  # ダメージではない

    def test_opponent_card_goes_to_opponent_bench(self):
        """相手のカード（コイキング。HP 30）は相手のベンチに出る（自分のベンチではない）。ダメージカウンターは 1 個（15 を切り捨て）。ログの ``player`` は持ち主（相手）、
        ``by_player`` はワザを使ったプレイヤー。"""
        state = invigorate(board(mon(SABRINAS_HYPNO, (P,)), opponent_discard=(MAGIKARP,)))
        card = discard_uid(state, 1, MAGIKARP)
        since = len(state.log)
        state = audited(self, answer(state, [card]))
        pokemon = state.players[1].bench[-1]
        self.assertEqual((pokemon.card, pokemon.damage, len(state.players[0].bench)), (card, 10, 1))
        moved, placed = events(state, since, "bench_from_discard")[0], events(state, since, "place_damage_counters")[0]
        self.assertEqual((moved["player"], moved["by_player"], placed["player"], placed["counters"]), (1, 0, 1, 1))
        # 相手から見ても公開（観測のログに出す。決定の選べるものは決めるプレイヤーだけ）
        self.assertIn("bench_from_discard", [e["kind"] for e in visible_log(state, 1)])

    def test_bench_space_is_checked_on_the_owners_side(self):
        """ベンチの空きはカードの持ち主の側で確かめる: 自分のベンチがいっぱいなら相手のトラッシュのカードだけ、相手のベンチがいっぱいなら自分のトラッシュのカードだけ。"""
        state = invigorate(board(mon(SABRINAS_HYPNO, (P,)), bench=FULL_BENCH, discard=(RATTATA,), opponent_discard=(MAGIKARP,)))
        self.assertEqual(state.decision.options, (discard_uid(state, 1, MAGIKARP),))
        state = invigorate(board(mon(SABRINAS_HYPNO, (P,)), opponent_bench=FULL_BENCH, discard=(RATTATA,), opponent_discard=(MAGIKARP,)))
        self.assertEqual(state.decision.options, (discard_uid(state, 0, RATTATA),))

    def test_no_target_does_nothing(self):
        """出せるカードがない（どちらのトラッシュにもたねポケモンのカードがない・あっても持ち主のベンチがいっぱい）なら、決定を出さずに何もしない（p.309。
        GR-2000-P309-ATTACK-PROCEDURE。ログ ``bench_from_discard_none``）。ワザは使ったことになり、番は終わる。元気のかけら・ポケモンの笛の RV1・FT1 とは別の扱い。"""
        cases = {
            "empty": board(mon(SABRINAS_HYPNO, (P,)), discard=(RATICATE, P), opponent_discard=(KADABRA, MYSTERIOUS_FOSSIL)),
            "both_full": board(mon(SABRINAS_HYPNO, (P,)), bench=FULL_BENCH, opponent_bench=FULL_BENCH, discard=(RATTATA,), opponent_discard=(MAGIKARP,)),
        }
        for label, state in cases.items():
            with self.subTest(label=label):
                since = len(state.log)
                state = audited(self, invigorate(state))
                self.assertIsNone(state.decision)
                none = events(state, since, "bench_from_discard_none")
                self.assertEqual([(e["player"], e["effect"]) for e in none], [(0, f"{SABRINAS_HYPNO}#0")])
                self.assertEqual(kinds(state, since)[:3], ["attack", "bench_from_discard_none", "turn_end"])

    def test_counters_follow_reach(self):
        """のせる前に「ワザをうけない」状態・「とうめい」を評価する（``reaches`` の ``damage_counters``。自分のポケモンも相手のポケモンも）。出したばかりのたねポケモンは
        持続する効果を持たず、「とうめい」のカード（1 進化）はトラッシュから出せないので、今の対応カードでは受けないことはない。受けない場合の分岐は ``reaches`` を
        差しかえて確かめる（出す処理はする・カウンターはのせない）。"""
        real = programs.reaches
        seen = []

        def blocked(res, fs, owner, pokemon, element, **kw):
            if element == E.COUNTERS_ELEMENT:
                seen.append((owner, pokemon.pokemon_id))
                return False
            return real(res, fs, owner, pokemon, element, **kw)

        for player, kwargs in ((0, {"discard": (HITMONCHAN,)}), (1, {"opponent_discard": (HITMONCHAN,)})):
            with self.subTest(owner=player):
                state = invigorate(board(mon(SABRINAS_HYPNO, (P,)), **kwargs))
                since = len(state.log)
                seen.clear()
                with mock.patch.object(programs, "reaches", blocked):
                    state = answer(state, [discard_uid(state, player, HITMONCHAN)])
                pokemon = state.players[player].bench[-1]
                self.assertEqual(seen, [(player, pokemon.pokemon_id)])
                self.assertEqual((pokemon.damage, events(state, since, "place_damage_counters")), (0, []))
                audited(self, state)

    def test_every_preflight_mode_gives_the_same_result(self):
        """宣言の前の先読みの方法（v0.15c）で結果が変わらない（選べるすべてのカードを試す。選んだカードは場のポケモンになるので、カード id でまとめない）。"""
        results = []
        for mode in PREFLIGHT_MODES:
            state = invigorate(board(mon(SABRINAS_HYPNO, (P,)), discard=(RATTATA, RATTATA), opponent_discard=(MAGIKARP,)), mode=mode)
            state = answer(state, [state.decision.options[1]], mode=mode)
            results.append(snapshot(state))
        self.assertTrue(all(r == results[0] for r in results))

    def test_metronome_copies_invigorate(self):
        """ピッピの「ゆびをふる」で、相手のナツメのスリーパーのよみがえらせるを自分のワザとして使える（選ぶのはピッピを使ったプレイヤー。自分のトラッシュ → 相手の
        トラッシュ。相手のカードは相手のベンチ）。"""
        state = board(mon(CLEFAIRY, (P, P, P)), mon(SABRINAS_HYPNO, (P,)), discard=(RATTATA,), opponent_discard=(MAGIKARP,))
        state = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual(state.decision.kind, SELECT_ATTACK)
        state = answer(state, [0])
        self.assertEqual((state.decision.kind, state.decision.player), (BENCH_FROM_DISCARD, 0))
        self.assertEqual(state.decision.options, (discard_uid(state, 0, RATTATA), discard_uid(state, 1, MAGIKARP)))
        since = len(state.log)
        state = audited(self, answer(state, [discard_uid(state, 1, MAGIKARP)]))
        moved = events(state, since, "bench_from_discard")[0]
        self.assertEqual((moved["player"], moved["by_player"], moved["effect"]), (1, 0, f"{SABRINAS_HYPNO}#0"))
        self.assertEqual(state.players[1].bench[-1].damage, 10)

    def test_psylink_needs_its_own_energy(self):
        """ナツメのフーディンの［サイコリンク］で持つよみがえらせる: ワザを使うのはフーディンで、必要なエネルギー（超）はフーディンが払う（免除しない）。ログの出どころは
        フーディン（``pokemon``）、ワザは印刷したカードのワザ（``effect``）。"""
        state = board(mon(SABRINAS_ALAKAZAM), bench=(mon(SABRINAS_HYPNO),), discard=(RATTATA,))
        alakazam = state.players[0].active
        option = [o for o in E.available_attacks(state, alakazam) if o.card_id == SABRINAS_HYPNO and o.attack_index == 0][0]
        self.assertEqual(option.route, "psylink")
        assert_rejected(self, state, UseAttack(0, 0, card=option.card), "INSUFFICIENT_ENERGY")
        state = board(mon(SABRINAS_ALAKAZAM, (P,)), bench=(mon(SABRINAS_HYPNO),), discard=(RATTATA,))
        alakazam = state.players[0].active
        option = [o for o in E.available_attacks(state, alakazam) if o.card_id == SABRINAS_HYPNO and o.attack_index == 0][0]
        state = invigorate(state, card=option.card)
        since = len(state.log)
        state = audited(self, answer(state, [discard_uid(state, 0, RATTATA)]))
        moved = events(state, since, "bench_from_discard")[0]
        self.assertEqual((moved["pokemon"], moved["pokemon_id"], moved["effect"]), (alakazam.card, alakazam.pokemon_id, f"{SABRINAS_HYPNO}#0"))
        self.assertEqual(state.players[0].bench[-1].damage, 10)

    def test_transformed_ditto_uses_invigorate(self):
        """［へんしん］のメタモン（相手のナツメのスリーパーの姿）がよみがえらせるを使える（どの色としても使えるエネルギーで払う）。出したメタモン（たねポケモン）は
        ベンチでは印刷の姿（HP 50 → 2 個）。"""
        state = board(mon(DITTO, (W,)), mon(SABRINAS_HYPNO, (P,)), discard=(DITTO,))
        state = invigorate(state)
        state = audited(self, answer(state, [discard_uid(state, 0, DITTO)]))
        self.assertEqual(state.players[0].bench[-1].damage, 20)


# ---------------------------------------------------------------- ふりこののろい


class PendulumCurseTest(unittest.TestCase):
    """ナツメのスリーパーの「ふりこののろい」（超超。20×）: 相手にのっているダメージカウンターの数だけコインを投げ、「おもて」の数 × 20 のダメージ。"""

    def curse(self, state, *sides, mode="derived", player=0):
        state = with_coin_results(state, *sides) if sides else state
        since = len(state.log)
        state = apply_kernel(state, UseAttack(player, 1), preflight=mode)
        return state, since

    def test_coins_equal_the_defenders_counters(self):
        """コインの枚数は相手の対戦ポケモンのダメージカウンターの数（ここでは 3）。「おもて」の数 × 20 が基本となるダメージ（p.321 の 1 段階）で、弱点はそのあとの段階
        （ユンゲラーは弱点 超 で 2 倍）。実際の対戦では 1 枚ずつ投げる。"""
        state, since = self.curse(board(mon(SABRINAS_HYPNO, (P, P)), mon(KADABRA, damage=30)), H, T, H)
        flips = events(state, since, "coin_flip")
        self.assertEqual(len(flips), 3)
        damage = events(state, since, "damage")[0]
        self.assertEqual((damage["steps"][:2], damage["amount"]), ((("1 基本となる計算", 40), ("3 弱点", 80)), 80))
        audited(self, state)

    def test_zero_counters_flips_nothing(self):
        """カウンターがなければコインを投げず、基本となるダメージは 0（2 段階で計算を終える。ダメージを与えない）。控えのカウンターは数えない。"""
        state = board(mon(SABRINAS_HYPNO, (P, P)), mon(KADABRA), opponent_bench=(mon(RATTATA, damage=20),))
        state, since = self.curse(state)
        self.assertEqual(events(state, since, "coin_flip"), [])
        damage = events(state, since, "damage")[0]
        self.assertEqual((damage["amount"], damage["stopped_after_step_2"]), (0, True))
        self.assertEqual(state.players[1].active.damage, 0)

    def test_defender_and_weakness_apply_after_the_base(self):
        """ディフェンダー（7 段階）は基本となるダメージのあと（H・H で 40 → 弱点・抵抗力が超でないコイキング → − 20 = 20）。最終ダメージに直接足さない。"""
        state = board(mon(SABRINAS_HYPNO, (P, P)), mon(MAGIKARP, damage=20, trainers=[(DEFENDER, TURN)]))
        state, since = self.curse(state, H, H)
        damage = events(state, since, "damage")[0]
        self.assertEqual((damage["steps"][0], damage["amount"]), (("1 基本となる計算", 40), 20))

    def test_prevented_defender_with_counters_is_unresolved(self):
        """「ダメージを受けない」相手（かたまる）にカウンターがあれば、コインがこのダメージの量だけを決めるので投げるかが決められない（v0.4b の問い。どの先読みの方法でも
        コインの前に止める。状態・乱数・ログは変えない）。カウンターがなければコインを投げないので止めない。"""
        state = board(mon(SABRINAS_HYPNO, (P, P)), {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": TURN - 1, "damage": 20})
        before = snapshot(state)
        for mode in PREFLIGHT_MODES:
            with self.subTest(mode=mode), self.assertRaises(UnsupportedError) as raised:
                apply_kernel(state, UseAttack(0, 1), preflight=mode)
            self.assertEqual(raised.exception.code, PREVENTED)
        self.assertEqual(snapshot(state), before)
        state = board(mon(SABRINAS_HYPNO, (P, P)), {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": TURN - 1})
        state, since = self.curse(state)
        self.assertEqual(events(state, since, "coin_flip"), [])
        self.assertEqual(len(events(state, since, "damage_prevented")), 1)

    def test_many_coins_are_grouped_in_preflight(self):
        """カウンター 11 個（ラッキー。HP 120）で 11 枚。先読みは「おもて」の数でまとめる（v0.35）。どの先読みの方法でも同じ結果で、実際の対戦では 11 枚を 1 枚ずつ投げる。"""
        sides = (H, T) * 5 + (H,)
        results = []
        for mode in PREFLIGHT_MODES:
            state, since = self.curse(board(mon(SABRINAS_HYPNO, (P, P)), mon(CHANSEY, damage=110)), *sides, mode=mode)
            self.assertEqual(len(events(state, since, "coin_flip")), 11)
            self.assertEqual(events(state, since, "damage")[0]["steps"][0], ("1 基本となる計算", 120))
            results.append(snapshot(state))
        self.assertTrue(all(r == results[0] for r in results))

    def test_metronome_copies_the_curse(self):
        """ピッピの「ゆびをふる」で、相手のナツメのスリーパーのふりこののろいを使える（数えるのは相手の対戦ポケモン、ここではスリーパー自身のカウンター）。"""
        state = with_coin_results(board(mon(CLEFAIRY, (P, P, P)), mon(SABRINAS_HYPNO, (P,), damage=30)), H, T, T)
        state = apply_kernel(state, UseAttack(0, 1))
        since = len(state.log)
        state = answer(state, [1])
        self.assertEqual(len(events(state, since, "coin_flip")), 3)
        self.assertEqual(events(state, since, "damage")[0]["steps"][0], ("1 基本となる計算", 20))


# ---------------------------------------------------------------- 元気のかけら


class ReviveTest(unittest.TestCase):
    """元気のかけら: トラッシュからポケモンカードを 1 枚選んで、HP の半分（きりすて）のダメージカウンターをのせた状態でベンチに出すことができる。進化カードを選ぶことは
    できない。"""

    def test_options_are_own_basics_only(self):
        """選ぶのは使ったプレイヤー。選べるものは自分のトラッシュのたねポケモンのカード（相手のトラッシュは入らない）。0〜1 枚。"""
        state = board(mon(HITMONCHAN), hand=(REVIVE,), discard=(RATICATE, RATTATA, MYSTERIOUS_FOSSIL, HITMONCHAN), opponent_discard=(MAGIKARP,))
        state = audited(self, play(state, REVIVE))
        d = state.decision
        self.assertEqual((d.kind, d.player, d.resume, d.min_choices, d.max_choices), (BENCH_FROM_DISCARD, 0, "trainer", 0, 1))
        self.assertEqual(d.options, (discard_uid(state, 0, RATTATA), discard_uid(state, 0, HITMONCHAN)))
        assert_rejected(self, state, ResolveDecision(0, d.id, (discard_uid(state, 1, MAGIKARP),)), "INVALID_CHOICE")

    def test_benches_with_counters_and_the_turn_continues(self):
        """出すカード（エビワラー。HP 70）に 3 個のダメージカウンターをのせた状態で自分のベンチに出す（ログ ``bench_from_discard`` の ``counters``・``damage``。別の
        ``place_damage_counters`` はない）。トレーナーはトラッシュ、番は続く（同じ番の MAIN）。"""
        state = play(board(mon(HITMONCHAN), hand=(REVIVE,), discard=(HITMONCHAN,)), REVIVE)
        card = discard_uid(state, 0, HITMONCHAN)
        trainer = state.trainer_in_use.card
        since = len(state.log)
        state = audited(self, answer(state, [card]))
        pokemon = state.players[0].bench[-1]
        self.assertEqual((pokemon.card, pokemon.damage, pokemon.played_turn), (card, 30, TURN))
        moved = events(state, since, "bench_from_discard")[0]
        self.assertEqual({k: moved[k] for k in ("player", "by_player", "card", "to_pokemon_id", "trainer_card", "trainer", "counters", "damage")},
                         {"player": 0, "by_player": 0, "card": card, "to_pokemon_id": pokemon.pokemon_id, "trainer_card": trainer, "trainer": REVIVE,
                          "counters": 3, "damage": 30})
        self.assertEqual(events(state, since, "place_damage_counters"), [])
        self.assertIn(trainer, state.players[0].discard)
        self.assertEqual((state.phase, state.current_player, state.turn_number), (Phase.MAIN, 0, TURN))

    def test_declining_benches_nothing(self):
        """0 枚は「ことができる」の、出さないこと（ログ ``bench_from_discard_declined``）。カードはトラッシュに残り、元気のかけらはトラッシュ。"""
        state = play(board(mon(HITMONCHAN), hand=(REVIVE,), discard=(HITMONCHAN,)), REVIVE)
        since = len(state.log)
        state = audited(self, answer(state, []))
        self.assertEqual([(e["player"], e["by_player"], e["trainer"]) for e in events(state, since, "bench_from_discard_declined")], [(0, 0, REVIVE)])
        self.assertEqual(len(state.players[0].bench), 1)
        self.assertEqual([state.cards[u].card_id for u in state.players[0].discard], [HITMONCHAN, REVIVE])

    def test_rv1_without_a_target(self):
        """自分のトラッシュにたねポケモンのカードがない（相手のトラッシュにあっても）・自分のベンチに空きがないときは、使えるかが決まらない（RV1）。手札から出す前に
        止める（状態・乱数・ログを変えない）。のちの版の「…このカードは使えない」・英語版の文面を補わない。"""
        cases = {
            "no_basic": board(mon(HITMONCHAN), hand=(REVIVE,), discard=(RATICATE, MYSTERIOUS_FOSSIL, P), opponent_discard=(MAGIKARP,)),
            "bench_full": board(mon(HITMONCHAN), hand=(REVIVE,), bench=FULL_BENCH, discard=(HITMONCHAN,)),
        }
        for label, state in cases.items():
            with self.subTest(label=label):
                assert_rejected(self, state, PlayTrainer(0, hand_uid(state, 0, REVIVE)), RV1, UnsupportedError)

    def test_trainer_lock_comes_before_rv1(self):
        """トレーナーの使用の禁止（［アレルギーかふん］・ずつう）は、使えるかを決める前に、共通の入口で拒否する（``TRAINER_PREVENTED``。RV1 より先）。"""
        pollen = board(mon(HITMONCHAN), mon(DARK_VILEPLUME), hand=(REVIVE,))
        assert_rejected(self, pollen, PlayTrainer(0, hand_uid(pollen, 0, REVIVE)), "TRAINER_PREVENTED")
        # ずつう: 相手（プレイヤー 1）の番にコダックが使い、次の自分の番にトレーナーを使えない
        headache = board(mon(HITMONCHAN), mon(FOSSIL_PSYDUCK, (P,)), hand=(REVIVE,), discard=(HITMONCHAN,), turn=TURN - 1, current=1)
        headache = apply_kernel(headache, UseAttack(1, 0))
        self.assertEqual((headache.turn_number, headache.current_player, headache.phase), (TURN, 0, Phase.MAIN))
        self.assertTrue(headache.trainer_locks)
        assert_rejected(self, headache, PlayTrainer(0, hand_uid(headache, 0, REVIVE)), "TRAINER_PREVENTED")

    def test_revived_pokemon_cannot_evolve_this_turn_without_permission(self):
        """出したポケモンはこの番に場に出たので、この番には進化できない（``PLAYED_THIS_TURN``。共通の進化の判定）。サカキの許可（「サカキの」ポケモン）があれば進化できる。"""
        state = play(board(mon(HITMONCHAN), hand=(REVIVE, GIOVANNI, GIOVANNIS_GYARADOS), discard=(GIOVANNIS_MAGIKARP,)), REVIVE)
        state = answer(state, [discard_uid(state, 0, GIOVANNIS_MAGIKARP)])
        magikarp = state.players[0].bench[-1]
        evolve = EvolvePokemon(0, hand_uid(state, 0, GIOVANNIS_GYARADOS), magikarp.pokemon_id)
        assert_rejected(self, state, evolve, "PLAYED_THIS_TURN")
        state = play(state, GIOVANNI)
        self.assertEqual(state.decision.kind, SELECT_POKEMON)
        state = answer(state, [magikarp.pokemon_id])
        state = audited(self, apply_kernel(state, evolve))
        self.assertEqual(state.cards[by_id(state, magikarp.pokemon_id).card].card_id, GIOVANNIS_GYARADOS)
        self.assertEqual(by_id(state, magikarp.pokemon_id).damage, 10)

    def test_knocked_out_pokemon_comes_back_without_its_history(self):
        """きぜつしてトラッシュに置かれたポケモン（ダメージ・どく・エネルギーがあった）を出すと、同じカードの新しい場のポケモン（番号は新しい・場に出た番は今の番）で、
        前のダメージ・特殊状態・エネルギーは引き継がない（エネルギーはトラッシュに残る）。のるのは HP の半分のダメージカウンターだけ。"""
        state = board(mon(RATTATA, (W,), damage=10, poison=10), mon(HITMONCHAN, (F,)), hand=(REVIVE,), turn=TURN - 1, current=1)
        old_id = state.players[0].active.pokemon_id
        card = state.players[0].active.card
        state = apply_kernel(state, UseAttack(1, 0))
        while state.decision is not None:  # サイドを取る（相手）→ バトル場に出す（自分）
            state = answer(state, [state.decision.options[0]])
        self.assertEqual((state.turn_number, state.current_player), (TURN, 0))
        self.assertIn(card, state.players[0].discard)
        state = play(state, REVIVE)
        state = audited(self, answer(state, [card]))
        pokemon = state.players[0].bench[-1]
        self.assertNotEqual(pokemon.pokemon_id, old_id)
        self.assertEqual((pokemon.card, pokemon.damage, pokemon.energy, pokemon.played_turn), (card, 10, [], TURN))
        self.assertEqual(pokemon.conditions.names(), ())
        self.assertIn(W, [state.cards[u].card_id for u in state.players[0].discard])


# ---------------------------------------------------------------- ポケモンの笛


class PokemonFluteTest(unittest.TestCase):
    """ポケモンの笛: 相手のトラッシュからポケモンカードを 1 枚選び、相手のベンチに出させることができる。ただし進化カードを選ぶことはできない。"""

    def test_user_chooses_from_opponent_trash_into_opponent_bench(self):
        """選ぶのは使ったプレイヤー（出される側の相手ではない）。選べるものは相手のトラッシュのたねポケモンのカード（自分のトラッシュは入らない）。相手のベンチに、
        ダメージカウンターをのせずに出る（ログ ``bench_from_discard`` の ``player`` は相手、``by_player`` は使ったプレイヤー。``counters`` は書かない）。"""
        state = board(mon(HITMONCHAN), hand=(POKEMON_FLUTE,), discard=(RATTATA,), opponent_discard=(KADABRA, MAGIKARP, CLEFAIRY_DOLL))
        state = play(state, POKEMON_FLUTE)
        d = state.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (BENCH_FROM_DISCARD, 0, (discard_uid(state, 1, MAGIKARP),), 0, 1))
        self.assertEqual(observe(state, 0)["decision"]["options"], [{"value": discard_uid(state, 1, MAGIKARP), "card_id": MAGIKARP}])
        since = len(state.log)
        state = audited(self, answer(state, [discard_uid(state, 1, MAGIKARP)]))
        pokemon = state.players[1].bench[-1]
        self.assertEqual((pokemon.damage, pokemon.played_turn, len(state.players[0].bench)), (0, TURN, 1))
        moved = events(state, since, "bench_from_discard")[0]
        self.assertEqual((moved["player"], moved["by_player"], moved["trainer"]), (1, 0, POKEMON_FLUTE))
        self.assertNotIn("counters", moved)
        self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 0))

    def test_declining(self):
        state = play(board(mon(HITMONCHAN), hand=(POKEMON_FLUTE,), opponent_discard=(MAGIKARP,)), POKEMON_FLUTE)
        since = len(state.log)
        state = audited(self, answer(state, []))
        self.assertEqual([(e["player"], e["by_player"]) for e in events(state, since, "bench_from_discard_declined")], [(1, 0)])
        self.assertEqual(len(state.players[1].bench), 1)

    def test_ft1_without_a_target(self):
        """相手のトラッシュにたねポケモンのカードがない（自分のトラッシュにあっても）・相手のベンチに空きがないときは、使えるかが決まらない（FT1。RV1 とは別の問い）。"""
        cases = {
            "no_basic": board(mon(HITMONCHAN), hand=(POKEMON_FLUTE,), discard=(RATTATA,), opponent_discard=(KADABRA,)),
            "bench_full": board(mon(HITMONCHAN), hand=(POKEMON_FLUTE,), opponent_bench=FULL_BENCH, opponent_discard=(MAGIKARP,)),
        }
        for label, state in cases.items():
            with self.subTest(label=label):
                assert_rejected(self, state, PlayTrainer(0, hand_uid(state, 0, POKEMON_FLUTE)), FT1, UnsupportedError)

    def test_benched_pokemon_evolves_on_its_owners_next_turn(self):
        """相手のベンチに出したポケモンは、この番（使ったプレイヤーの番）に場に出たので、相手の次の番には進化できる（場に出た番より後の持ち主の番）。"""
        state = play(board(mon(HITMONCHAN), hand=(POKEMON_FLUTE,), opponent_hand=(RATICATE,), opponent_discard=(RATTATA,)), POKEMON_FLUTE)
        state = answer(state, [discard_uid(state, 1, RATTATA)])
        rattata = state.players[1].bench[-1]
        state = apply_kernel(state, EndTurn(0))
        self.assertEqual((state.turn_number, state.current_player), (TURN + 1, 1))
        state = audited(self, apply_kernel(state, EvolvePokemon(1, hand_uid(state, 1, RATICATE), rattata.pokemon_id)))
        self.assertEqual(state.cards[by_id(state, rattata.pokemon_id).card].card_id, RATICATE)


# ---------------------------------------------------------------- 書き出し・観測


class StateAndObservationTest(unittest.TestCase):
    def test_no_new_state_or_format(self):
        """状態の項目・書き出しの形式は加えていない（形式 15 のまま。出したポケモンは場に出た番を持つ、ふつうのたねポケモン）。古い形式（場に出た番をログから分かる形）でも
        書き出せる。"""
        state = play(board(mon(HITMONCHAN), hand=(REVIVE,), discard=(HITMONCHAN,)), REVIVE)
        state = answer(state, [discard_uid(state, 0, HITMONCHAN)])
        audited(self, state)
        self.assertIsInstance(state_to_dict(state, format_version=1), dict)

    def test_observation_shows_the_revived_pokemon(self):
        """観測: どちらのプレイヤーからも、出したポケモン（場）と、トラッシュから出したこと（ログ）が見える。"""
        state = invigorate(board(mon(SABRINAS_HYPNO, (P,)), opponent_discard=(MAGIKARP,)))
        state = answer(state, [discard_uid(state, 1, MAGIKARP)])
        for viewer in (0, 1):
            with self.subTest(viewer=viewer):
                view = observe(state, viewer)
                self.assertEqual(len(view["players"][1]["bench"]), 2)
                log = [e for e in visible_log(state, viewer) if e["kind"] == "bench_from_discard"]
                self.assertEqual(len(log), 1)
                self.assertEqual(log[0]["card_id"] if "card_id" in log[0] else state.cards[log[0]["card"]].card_id, MAGIKARP)


# ---------------------------------------------------------------- 正式な対戦


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.51 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.51 の 4 組を 2 seed ずつ（席を入れかえて 16 局）。どれも監査の失敗（やり直し・不変条件・ログ・書き出し・観測）・想定外の拒否・内部エラー・手数の上限がなく、
        3 枚の処理（よみがえらせるで自分・相手のカードを出す・出せるカードがない・ふりこののろいでコインを投げる・ほかのポケモンがまねて使う・元気のかけらで出す／出さない・
        ポケモンの笛で出す）と、出したポケモンのそのあとの行動（エネルギー・ワザ・進化）が起こる（勝敗は判断に使わない）。"""
        from tools import existing_effect_games as games

        results = games.run(range(2), pairings=games.PAIRINGS_V0_51)
        totals = {}
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"), game.get("error"))
                if game["outcome"] == "halted":
                    self.assertEqual(game["halt_code"], "UNRESOLVED_MULLIGAN_COMPENSATION")
                for card, uses in game.get("card_uses", {}).items():
                    for key, count in uses.items():
                        totals[(card, key)] = totals.get((card, key), 0) + count
        for card, key in ((SABRINAS_HYPNO, "attack#0"), (SABRINAS_HYPNO, "attack#1"), (SABRINAS_HYPNO, "bench_from_discard_own"),
                          (SABRINAS_HYPNO, "bench_from_discard_opponent"), (SABRINAS_HYPNO, "bench_from_discard_none"), (SABRINAS_HYPNO, "invigorate_counters"),
                          (SABRINAS_HYPNO, "copied#0"), (SABRINAS_HYPNO, "copied#1"), (SABRINAS_HYPNO, "revived_then_attack"),
                          (REVIVE, "bench_from_discard_with_counters"), (REVIVE, "bench_from_discard_declined"), (REVIVE, "revived_then_attach_energy"),
                          (REVIVE, "revived_then_attack"), (REVIVE, "revived_then_promote_active"), (POKEMON_FLUTE, "bench_from_discard_opponent"),
                          (POKEMON_FLUTE, "revived_then_attack")):
            with self.subTest(card=card, key=key):
                self.assertGreater(totals.get((card, key), 0), 0)
        # ふりこののろいで「おもて」があった（基本となるダメージが 0 でない）
        self.assertTrue(any(card == SABRINAS_HYPNO and key.startswith("base#1=") and key != "base#1=0" for card, key in totals))


class DocumentTest(unittest.TestCase):
    def test_document_names_the_stop_codes_and_records(self):
        text = DOC.read_text(encoding="utf-8")
        for code in NEW_CODES:
            self.assertIn(code, text)
        for record in APPLIED_RECORDS:
            self.assertIn(record, text)


if __name__ == "__main__":
    unittest.main()
