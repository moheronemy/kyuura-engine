"""v0.50: 退化の共通の処理と、それを使う 2 枚（docs/mew-devolution-spray-v0.50.md）。

2 枚: ミュウ（PMCG3-033。サイコウェーブ・たいかビーム）・退化スプレー（PMCG1-086。トレーナー）。どちらも kyuura データの採用（処理に使う文面は kyuura の印刷の文面。
採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合。ガイドブックは読んでいない。

根拠にした既存の記録（研究の基準のコミットの kyuura の記録。``research_links.json`` の ``applied_rule_records``）: GR-2000-P324-DEVOLUTION（退化の規定。p.324「19」:
退化前の進化カードに書かれている内容のすべては無効・「別のポケモン」）・CR-SHELL-ATTACK-ENDS-ON-DEVOLUTION（退化で持続する効果が消える）・CR-CHEMICAL-GAS-LEAVES（かがく
へんかガスのポケモンが場をはなれる・いなくなると力が消える）・GR-2000-P323-KNOCKOUT（HP 以上のダメージで「きぜつ」）と、エンジンの v0.4a〜v0.4c（進化の手順・重なり）・
v0.25（ポケモン育て屋さん）・v0.42（特殊能力のあとのきぜつの処理）・v0.44（1 度だけ使えるワザ・サカキの許可）・v0.47（なにかの化石）・v0.48（今有効な最大HP・MH1）・
v0.49（今の姿・ばける・へんしん・思い出させる）の記録。

退化で最大HPがのっているダメージ以下になったポケモンのきぜつ（たいかビームはワザのあとのきぜつの判定、退化スプレーはトレーナーを使い終わったあと）は、2000.02.14 版の
p.323「16」・p.319・p.324「19」から導いた処理（SUPPORTED。第4版の冊子の記述は別の版の記録なので根拠にしない）。

新しい停止コードは 5: DV1・DV2・DV3・DV4・DV5（docs 6 章）。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import unittest

from kyuura_engine import (
    EndTurn,
    PromoteActive,
    TakePrize,
    EngineError,
    EvolvePokemon,
    IllegalActionError,
    Phase,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    check_invariants,
    max_hp,
    observe,
    state_to_dict,
    visible_log,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, pool_from_extract, read_extract
from kyuura_engine.decisions import SELECT_DEVOLVE_COUNT, SELECT_POKEMON
from kyuura_engine.evolution import DEVOLVE_TO_DISCARD, DEVOLVE_TO_HAND, devolve
from kyuura_engine.observation import PUBLIC_EVENTS
from kyuura_engine.resolution import PREFLIGHT_MODES, contract, programs, v013_checks
from kyuura_engine.serialize import FORMAT_VERSIONS
from scripts import check_card_sources as cs
from tests.helpers import (
    ABRA,
    AERODACTYL,
    ATTACK_TYPES_SINCE_V0_17,
    BROCKS_NINETALES,
    BROCKS_VULPIX,
    BULBASAUR,
    CLEFAIRY,
    DARK_WARTORTLE,
    DARK_GLOOM,
    DARK_VILEPLUME,
    DEVOLUTION_SPRAY,
    DITTO,
    ERIKAS_BELLSPROUT_40,
    ERIKAS_CLEFAIRY,
    ERIKAS_VICTREEBEL,
    ERIKAS_WEEPINBELL,
    FIGHTING,
    GASTLY,
    GIOVANNI,
    GRASS,
    GRIMER,
    GYARADOS,
    HAUNTER,
    HITMONCHAN,
    KABUTO,
    KABUTOPS,
    KADABRA,
    KOGAS_BEEDRILL,
    KOGAS_KAKUNA,
    KOGAS_WEEDLE,
    MAGIKARP,
    MEW,
    MEWTWO,
    MUK,
    MYSTERIOUS_FOSSIL,
    PLUSPOWER,
    POKEMON_BREEDER,
    POTION,
    PSYCHIC,
    RATTATA,
    RECALL,
    ROCKET_SQUIRTLE,
    SABRINAS_ABRA,
    SABRINAS_ALAKAZAM,
    SABRINAS_GASTLY,
    SABRINAS_GENGAR,
    SABRINAS_HAUNTER,
    SABRINAS_KADABRA,
    V0_50_CARDS,
    V0_50_POKEMON,
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
DOC = ROOT / "docs" / "mew-devolution-spray-v0.50.md"
TURN = 7
P, W, G, F = PSYCHIC, WATER, GRASS, FIGHTING
DV1 = "UNRESOLVED_DEVOLUTION_INTERMEDIATE_KNOCKOUT"
DV2 = "UNRESOLVED_EVOLVE_AFTER_DEVOLUTION"
DV3 = "UNRESOLVED_POWER_REUSE_AFTER_DEVOLUTION"
DV4 = "UNRESOLVED_DEVOLUTION_SPRAY_WITHOUT_TARGET"
DV5 = "UNRESOLVED_DEVOLUTION_TARGET_DISGUISED"
MH1 = "UNRESOLVED_MAX_HP_DROP"
NEW_CODES = (DV1, DV2, DV3, DV4, DV5)
# pcg-search.com の対象の版（サイトの一覧の番号）
EDITIONS = {MEW: "033/048", DEVOLUTION_SPRAY: "076/096"}
# 進化しているポケモンの下のカード（build_test_state の "evolved_from"）
BELOW = {GYARADOS: MAGIKARP, KADABRA: ABRA, HAUNTER: GASTLY, MUK: GRIMER, SABRINAS_KADABRA: SABRINAS_ABRA, SABRINAS_ALAKAZAM: [SABRINAS_ABRA, SABRINAS_KADABRA],
         SABRINAS_HAUNTER: SABRINAS_GASTLY, SABRINAS_GENGAR: [SABRINAS_GASTLY, SABRINAS_HAUNTER], KOGAS_KAKUNA: KOGAS_WEEDLE,
         KOGAS_BEEDRILL: [KOGAS_WEEDLE, KOGAS_KAKUNA], BROCKS_NINETALES: BROCKS_VULPIX, ERIKAS_WEEPINBELL: ERIKAS_BELLSPROUT_40,
         ERIKAS_VICTREEBEL: [ERIKAS_BELLSPROUT_40, ERIKAS_WEEPINBELL]}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def bench_spec(b):
    return mon(b) if isinstance(b, str) else b


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), hand=(), opponent_hand=(), turn=TURN, current=0, deck=None,
          opponent_deck=None, prizes=6, opponent_prizes=6):
    me = {"active": active, "bench": [bench_spec(b) for b in bench], "hand": list(hand), "prizes": prizes}
    them = {"active": opponent or mon(HITMONCHAN, (F, F, F)), "bench": [bench_spec(b) for b in opponent_bench], "hand": list(opponent_hand),
            "prizes": opponent_prizes}
    if deck is not None:
        me["deck"] = list(deck)
    if opponent_deck is not None:
        them["deck"] = list(opponent_deck)
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


def assert_stops(test, state, command, code, *, exception=UnsupportedError):
    """どの先読みの方法でも ``code`` で拒否し、状態・乱数・ログが変わらない。"""
    before = snapshot(state)
    for mode in PREFLIGHT_MODES:
        with test.subTest(mode=mode), test.assertRaises(exception) as raised:
            apply_kernel(state, command, preflight=mode)
        test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def assert_rejected(test, state, command, code, exception=EngineError):
    before = snapshot(state)
    with test.assertRaises(exception) as raised:
        apply_kernel(state, command)
    test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def card_of(state, player, card, zone="hand", nth=0):
    return [u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card][nth]


def top(state, pokemon):
    return state.cards[pokemon.card].card_id


def stack_ids(state, pokemon):
    return [state.cards[u].card_id for u in (*pokemon.evolution_stack, pokemon.card)]


def by_id(state, pid):
    return state.find_pokemon(pid)[1]


def spray(state, target, count, *, player=0):
    """退化スプレーを使い、``target``（場のポケモンの番号）から ``count`` 枚はがす（決定 2 つへの答え）。"""
    state = apply_kernel(state, PlayTrainer(player, card_of(state, player, DEVOLUTION_SPRAY)))
    assert state.decision.kind == SELECT_POKEMON, state.decision
    state = answer(state, [target])
    assert state.decision.kind == SELECT_DEVOLVE_COUNT, state.decision
    return answer(state, [count])


def by_card(state, card, player, zone):
    return card_of(state, player, card, zone)


def disguise(state, pokemon_id, card_id, *, player=0):
    """タケシのキュウコンの「ばける」で、手札の ``card_id`` をのせる（v0.49。宣言 → 決定への答え）。"""
    state = apply_kernel(state, UsePokemonPower(player, pokemon_id, 0))
    return answer(state, [card_of(state, player, card_id)])


def beam(state, target, *sides, player=0, mode="derived"):
    """ミュウのたいかビーム（ワザの位置 1）で ``target`` を選ぶ。"""
    state = with_coin_results(state, *sides) if sides else state
    state = apply_kernel(state, UseAttack(player, 1), preflight=mode)
    assert state.decision is not None and state.decision.kind == SELECT_POKEMON, state.decision
    return answer(state, [target], mode=mode)


# ---------------------------------------------------------------- 登録・写し・記録


class CardDataTest(unittest.TestCase):
    """2 枚の写し・登録・記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_two_requested_cards(self):
        """写しの組 pool_v0_50 は依頼の 2 枚（並び）。どちらも対応で、どのワザも、トレーナーの効果も登録した。"""
        self.assertEqual(read_extract()["pool_v0_50"], list(V0_50_CARDS))
        self.assertEqual(V0_50_POKEMON, (MEW,))
        mew = self.pool.get(MEW)
        self.assertEqual((mew.name_ja, mew.stage, mew.hp, mew.pokemon_type, mew.weakness, mew.retreat_cost), ("ミュウ", "basic", 50, EnergyType.PSYCHIC, EnergyType.PSYCHIC, 1))
        self.assertEqual([a.name_ja for a in mew.attacks], ["サイコウェーブ", "たいかビーム"])
        self.assertEqual(mew.powers, ())
        spray_def = self.pool.get(DEVOLUTION_SPRAY)
        self.assertEqual((spray_def.name_ja, spray_def.category), ("退化スプレー", "trainer"))
        for card in V0_50_CARDS:
            with self.subTest(card=card):
                self.assertTrue(self.pool.is_playable(card))
        # どちらかの登録を除くと対応にならない（ワザの片方・トレーナーの登録を除いた登録表）
        for key in (E.AttackKey(MEW, 0), E.AttackKey(MEW, 1)):
            effects = E.DEFAULT_EFFECTS.without_attacks(f"test-no-{key}", [key])
            with self.subTest(key=key):
                self.assertFalse(pool_from_extract(read_extract(), effects).is_playable(MEW))

    def test_registrations_use_kyuura_printed_text(self):
        """処理に使う文面は kyuura の印刷の文面（LD-・エラッタはない）。実装の型の ``check`` は文面と値の組を確かめる。"""
        mew = self.pool.get(MEW)
        psywave = E.DEFAULT_EFFECTS.attack_entry(MEW, 0)
        devolution_beam = E.DEFAULT_EFFECTS.attack_entry(MEW, 1)
        self.assertEqual(psywave.effect, E.DamageTimesDefenderEnergyCards(10))
        self.assertEqual(devolution_beam.effect, E.DevolveChosenPokemon())
        for entry, attack in ((psywave, mew.attacks[0]), (devolution_beam, mew.attacks[1])):
            with self.subTest(attack=attack.name_ja):
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                                 (attack.name_ja, attack.text_ja, attack.text_ja, cs.PRINTED_TEXT_SOURCE))
                self.assertEqual(entry.effect.check(attack), [])
                self.assertTrue(entry.effect.check(dataclasses.replace(attack, text_ja=attack.text_ja + "あ")))
        # サイコウェーブは「×」のワザ（目安の数字 10 が 1 枚あたりの数）。「+」や数の違う登録は受け付けない
        self.assertTrue(psywave.effect.check(dataclasses.replace(mew.attacks[0], damage_modifier="+")))
        self.assertTrue(E.DamageTimesDefenderEnergyCards(20).check(mew.attacks[0]))
        trainer = E.DEFAULT_EFFECTS.trainer_entry(DEVOLUTION_SPRAY)
        self.assertIsInstance(trainer.effect, E.DevolveOwnPokemon)
        printed = self.pool.get(DEVOLUTION_SPRAY).trainer_text_ja
        self.assertEqual((trainer.name_ja, trainer.text_ja, trainer.play_text_ja, trainer.source), ("退化スプレー", printed, printed, cs.PRINTED_TEXT_SOURCE))
        self.assertTrue(trainer.effect.may_knock_out)

    def test_new_attack_types_stay_outside_the_v013_contract(self):
        """v0.50 のワザの型は要素の並び（BUILDERS）で処理する。v0.13 の約束の型（``v013_checks.VERIFIED``）には入れない。"""
        for effect_type in (E.DamageTimesDefenderEnergyCards, E.DevolveChosenPokemon):
            with self.subTest(effect_type=effect_type.__name__):
                self.assertIn(effect_type, ATTACK_TYPES_SINCE_V0_17)
                self.assertNotIn(effect_type, v013_checks.VERIFIED)
                self.assertIn(effect_type, programs.BUILDERS)
        for index in (0, 1):
            self.assertFalse(contract.is_contract(contract.program_for(E.DEFAULT_EFFECTS.attack_entry(MEW, index).effect)))
        # たいかビームは相手に効果を与える（「ワザをうけない」状態・「とうめい」を評価する。v0.11 の宣言）
        self.assertEqual(E.DevolveChosenPokemon.opponent_effect_elements, (E.DEVOLVE_ELEMENT,))
        self.assertIn(E.DEVOLVE_ELEMENT, E.ATTACK_ELEMENTS)

    def test_adoption_records_and_external_checks(self):
        """採用の記録（kyuura データの採用）と pcg-search.com の同じ版との照合。ガイドブックの項目は書かない。"""
        records = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        for card in V0_50_CARDS:
            with self.subTest(card=card):
                record = records[card]
                self.assertEqual((record["basis"], record["status"]), ("kyuura_data", "adopted"))
                self.assertEqual(record["kyuura_records"], [])
                checks = record["external_checks"]
                self.assertEqual(len(checks), 1)
                self.assertTrue(checks[0]["url"].startswith("https://pcg-search.com/"))
                self.assertEqual(checks[0]["edition"]["list_number"], EDITIONS[card])
                self.assertEqual(checks[0]["result"], "match")
                for forbidden in ("page", "pdf_page", "latest_description_ja", "card_image_text_ja"):
                    self.assertNotIn(forbidden, json.dumps(record, ensure_ascii=False).replace("list_number", ""))
        self.assertEqual(cs.problems(), [])

    def test_research_links(self):
        """新しい停止コード 5 は kyuura の未解決の一覧にない（``not_in_kyuura``）。再利用した 4 つの記録は ``applied_rule_records`` に id だけで結ぶ。"""
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        for code in NEW_CODES:
            with self.subTest(code=code):
                self.assertEqual(links["stop_codes"][code]["kyuura_disposition"], "not_in_kyuura")
                self.assertEqual([(r["version"], r["document"]) for r in links["stop_codes"][code]["engine_rulings"]],
                                 [("v0.50", "docs/mew-devolution-spray-v0.50.md")])
        # v0.50 で 80・81。v0.51 で RV1・FT1 の 2 件を加えた（docs/discard-to-bench-v0.51.md）
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (87, 88))  # v0.52 で FJ1・SU1・SU2、v0.53 で ST1・NG1 を加えた
        # v0.50 の版で結んだ記録（v0.51 からほかの版の記録も同じ一覧にある）
        applied = [record["kyuura_record"] for record in links["applied_rule_records"]
                   if any(engine["version"] == "v0.50" for engine in record["engine"])]
        self.assertEqual(sorted(applied), sorted(["GR-2000-P324-DEVOLUTION", "CR-SHELL-ATTACK-ENDS-ON-DEVOLUTION", "CR-CHEMICAL-GAS-LEAVES",
                                                  "GR-2000-P323-KNOCKOUT"]))
        adopted = links["latest_descriptions"]["adopted_printed_text"]
        self.assertTrue({f"{MEW}/attack/0", f"{MEW}/attack/1"} <= set(adopted))

    def test_public_events(self):
        self.assertTrue({"devolve", "devolve_declined", "devolve_none"} <= PUBLIC_EVENTS)


# ---------------------------------------------------------------- サイコウェーブ


class PsywaveTest(unittest.TestCase):
    """ミュウの「サイコウェーブ」（超。10×）: 相手についているエネルギーカード × 10 が基本となるダメージ（p.321 の 1 段階）。"""

    def damage_log(self, state):
        since = len(state.log)
        state = apply_kernel(state, UseAttack(0, 0))
        return events(state, since, "damage")[0], state

    def test_counts_energy_cards_attached_to_the_defender(self):
        """数えるのは相手の対戦ポケモンについているエネルギーカードの枚数（タイプ・色を問わない。ミュウツーの「サイコキネシス」（10+）の加算とは別の型）。弱点・抵抗力は
        そのあとの段階。"""
        for energy, expected in (((F,), 10), ((F, F, W), 30), ((W, G, F, P), 40)):
            with self.subTest(energy=energy):
                damage, _ = self.damage_log(board(mon(MEW, (P,)), mon(MAGIKARP, energy)))
                self.assertEqual((damage["steps"][0], damage["amount"]), (("1 基本となる計算", expected), expected))
        # 弱点 超 の相手（ユンゲラー）は 2 倍（基本となるダメージは 30）
        damage, after = self.damage_log(board(mon(MEW, (P,)), mon(KADABRA, (P, W, F))))
        self.assertEqual((damage["steps"], damage["amount"]), ((("1 基本となる計算", 30), ("3 弱点", 60)), 60))
        audited(self, after)
        self.assertIsInstance(E.DEFAULT_EFFECTS.attack_entry(MEWTWO, 0).effect, E.DamagePlusDefenderEnergy)

    def test_zero_cards_ends_the_calculation_at_step_two(self):
        """相手にエネルギーカードがなければ基本となるダメージは 0 で、p.321 の 2 段階で計算を終える（プラスパワー・弱点を計算しない。ダメージを与えない）。"""
        damage, after = self.damage_log(board(mon(MEW, (P,), trainers=[(PLUSPOWER, TURN)]), mon(KADABRA)))
        self.assertEqual((damage["amount"], damage["steps"], damage["stopped_after_step_2"]), (0, (("1 基本となる計算", 0),), True))
        self.assertEqual(by_id(after, after.players[1].active.pokemon_id).damage, 0)

    def test_transformed_ditto_uses_psywave_with_the_card_count(self):
        """［へんしん］のメタモンがミュウの姿で使うサイコウェーブも、相手についているエネルギーカードの枚数で数える（どの色としても使えるエネルギーで払う。タイプの
        エネルギーを数えるワザではないので TE1 に当たらない）。"""
        state = board(mon(DITTO, (W,)), mon(MEW, (P, P, F)))
        damage, after = self.damage_log(state)
        self.assertEqual(damage["steps"][0], ("1 基本となる計算", 30))
        self.assertEqual(events(after, 0, "attack")[-1]["card_id"], MEW)


# ---------------------------------------------------------------- たいかビーム


class DevolutionBeamTest(unittest.TestCase):
    """ミュウの「たいかビーム」（超超）: 自分または相手の場の進化ポケモン 1 匹から、いちばん上の進化カードを 1 枚はがして持ち主の手札にもどす（ワザの効果）。"""

    def test_options_are_evolved_pokemon_on_both_sides(self):
        """選ぶのはワザを使ったプレイヤー。選べるものは自分の場 → 相手の場の、実際に進化カードが重なっているポケモン（たねポケモン・ミュウ自身は入らない）。"""
        state = board(mon(MEW, (P, P)), mon(GYARADOS, (W, W)), bench=(mon(KADABRA), RATTATA), opponent_bench=(mon(HAUNTER), RATTATA))
        state = apply_kernel(state, UseAttack(0, 1))
        d = state.decision
        kadabra, gyarados, haunter = state.players[0].bench[0], state.players[1].active, state.players[1].bench[0]
        self.assertEqual((d.kind, d.player, d.options, d.resume), (SELECT_POKEMON, 0, (kadabra.pokemon_id, gyarados.pokemon_id, haunter.pokemon_id), "attack"))
        self.assertEqual((d.min_choices, d.max_choices), (1, 1))
        audited(self, state)

    def test_devolves_opponent_pokemon_into_its_owners_hand(self):
        """はがした進化カードは持ち主（相手）の手札。ダメージ・エネルギー・場のポケモンの番号・場に出た番は変えない。ログ ``devolve``（ワザの効果。``effect``・``by_player``）。"""
        state = board(mon(MEW, (P, P)), mon(GYARADOS, (W, W), damage=20))
        gyarados = state.players[1].active
        top_card = gyarados.card
        since = len(state.log)
        state = beam(state, gyarados.pokemon_id)
        magikarp = by_id(state, gyarados.pokemon_id)
        self.assertEqual((top(state, magikarp), magikarp.evolution_stack, magikarp.damage, len(magikarp.energy)), (MAGIKARP, (), 20, 2))
        self.assertIn(top_card, state.players[1].hand)
        log = events(state, since, "devolve")[0]
        self.assertEqual((log["player"], log["by_player"], log["effect"], log["removed"], log["destination"]), (1, 0, f"{MEW}#1", (top_card,), DEVOLVE_TO_HAND))
        self.assertEqual(magikarp.devolved_turn, TURN)
        self.assertEqual(kinds(state, since)[:3], ["attack", "devolve", "turn_end"])  # ワザなので番は終わる

    def test_devolves_own_pokemon_into_own_hand(self):
        """自分のポケモンも選べる（はがしたカードは自分の手札）。2 進化ポケモンからは 1 枚だけ（1 進化ポケモンにもどる）。"""
        state = board(mon(MEW, (P, P)), bench=(mon(SABRINAS_ALAKAZAM),))
        alakazam = state.players[0].bench[0]
        state = beam(state, alakazam.pokemon_id)
        kadabra = by_id(state, alakazam.pokemon_id)
        self.assertEqual(stack_ids(state, kadabra), [SABRINAS_ABRA, SABRINAS_KADABRA])
        self.assertIn(alakazam.card, state.players[0].hand)
        self.assertIsNotNone(kadabra.evolved_turn)  # 1 進化ポケモンのまま（重なりが残っている）
        self.assertEqual(kadabra.devolved_turn, TURN)

    def test_no_evolved_pokemon_means_nothing_happens(self):
        """どちらの場にも進化ポケモンがいなければ決定を出さずに何もしない（p.309。ログ ``devolve_none``）。ワザは使ったことになり、番は終わる。"""
        state = board(mon(MEW, (P, P)), mon(HITMONCHAN))
        since = len(state.log)
        state = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual(kinds(state, since)[:3], ["attack", "devolve_none", "turn_end"])

    def test_knocks_out_after_the_attack_when_max_hp_drops(self):
        """退化で最大HPがのっているダメージ以下になったポケモンは、ワザのあとのきぜつの判定できぜつする（GR-2000-P323-KNOCKOUT。ダメージではないので「こんじょう」の
        候補にしない）。サイドはミュウの持ち主が取る。"""
        state = board(mon(MEW, (P, P)), mon(GYARADOS, (W, W), damage=30))
        gyarados = state.players[1].active
        since = len(state.log)
        state = beam(state, gyarados.pokemon_id)
        order = kinds(state, since)
        self.assertLess(order.index("devolve"), order.index("knock_out"))
        knock = events(state, since, "knock_out")[0]
        self.assertEqual((knock["player"], knock["pokemon"]), (1, by_card(state, MAGIKARP, 1, "discard")))
        self.assertEqual((state.phase, state.decision.kind, state.decision.player), (Phase.TAKE_PRIZE, "take_prize", 0))
        self.assertNotIn("ko_prevention_declined", order)
        audited(self, state)

    def test_transparency_is_evaluated_for_both_sides(self):
        """はがす前に「とうめい」（化石の秘密のゴースト）を評価する（自分のポケモンでも）。「おもて」なら受けず、はがさない（ログ ``attack_evaded`` の ``devolve``）。"""
        for owner in (0, 1):
            for side, devolved in ((H, False), (T, True)):
                with self.subTest(owner=owner, side=side):
                    if owner == 1:
                        state = board(mon(MEW, (P, P)), mon(HAUNTER, (P,)))
                        haunter = state.players[1].active
                    else:
                        state = board(mon(MEW, (P, P)), bench=(mon(HAUNTER),))
                        haunter = state.players[0].bench[0]
                    since = len(state.log)
                    state = beam(state, haunter.pokemon_id, side)
                    self.assertEqual(top(state, by_id(state, haunter.pokemon_id)), GASTLY if devolved else HAUNTER)
                    check = events(state, since, "evade_check")[0]
                    self.assertEqual((check["player"], check["element"], check["evaded"]), (owner, E.DEVOLVE_ELEMENT, not devolved))
                    if not devolved:
                        self.assertEqual(events(state, since, "attack_evaded")[0]["element"], E.DEVOLVE_ELEMENT)

    def test_disguised_pokemon_cannot_be_devolved(self):
        """「ばける」でのせたカードのあるタケシのキュウコンは選べるが選ぶと止める（DV5）。どの候補もそうなら、ワザの宣言の前に止める（どの先読みの方法でも、状態が変わらない）。"""
        state = board(mon(MEW, (P, P)), mon(GYARADOS), bench=(BROCKS_NINETALES,), hand=(KADABRA,))
        state = disguise(state, state.players[0].bench[0].pokemon_id, KADABRA)
        ninetales = state.players[0].bench[0]
        self.assertIsNotNone(ninetales.disguise)
        attacked = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual(attacked.decision.context_value("unresolved_choices"), (ninetales.pokemon_id,))
        assert_rejected(self, attacked, ResolveDecision(0, attacked.decision.id, (ninetales.pokemon_id,)), DV5, UnsupportedError)
        only = board(mon(MEW, (P, P)), mon(HITMONCHAN), bench=(BROCKS_NINETALES,), hand=(KADABRA,))
        only = disguise(only, only.players[0].bench[0].pokemon_id, KADABRA)
        assert_stops(self, only, UseAttack(0, 1), DV5)

    def test_barrier_prevents_the_devolution(self):
        """「ワザをうけない」状態（ギャロップの「こうそくいどう」）のポケモンは、たいかビームの効果を受けない（ログ ``effect_prevented`` の ``devolve``。はがさない）。"""
        rapidash, ponyta, fire = "PMCG2-019", "PMCG1-016", "PMCG1-098"
        state = board(mon(MEW, (P, P)), {"card": rapidash, "evolved_from": ponyta, "energy": [fire, fire, fire]}, current=1, turn=8)
        state = apply_kernel(with_coin_results(state, H), UseAttack(1, 1))  # こうそくいどう（「おもて」で、次の相手の番、ワザのダメージと効果を受けない）
        target = state.players[1].active
        since = len(state.log)
        state = beam(state, target.pokemon_id)
        self.assertEqual(top(state, by_id(state, target.pokemon_id)), rapidash)
        prevented = events(state, since, "effect_prevented")[0]
        self.assertEqual((prevented["element"], prevented["persistent_effect"]), (E.DEVOLVE_ELEMENT, "attack_barrier"))
        self.assertEqual(events(state, since, "devolve"), [])

    def test_metronome_copies_the_beam(self):
        """ピッピの「ゆびをふる」で、相手のミュウのたいかビームを自分のワザとして使える（選ぶのはピッピを使ったプレイヤー。ログ ``devolve`` の ``effect`` は使ったワザ）。"""
        state = board(mon(CLEFAIRY, (P, P, P)), mon(MEW, (P,)), opponent_bench=(mon(GYARADOS),))
        gyarados = state.players[1].bench[0]
        since = len(state.log)
        state = apply_kernel(state, UseAttack(0, 1))  # ゆびをふる → まねるワザを選ぶ
        state = answer(state, [1])
        self.assertEqual((state.decision.kind, state.decision.player, state.decision.options), (SELECT_POKEMON, 0, (gyarados.pokemon_id,)))
        state = answer(state, [gyarados.pokemon_id])
        log = events(state, since, "devolve")[0]
        self.assertEqual((log["player"], log["by_player"], log["effect"]), (1, 0, f"{MEW}#1"))
        self.assertEqual(top(state, by_id(state, gyarados.pokemon_id)), MAGIKARP)

    def test_psylink_alakazam_can_devolve_itself(self):
        """ナツメのフーディンの［サイコリンク］で持つミュウのたいかビーム（ワザを使うのはフーディン）。自分自身も選べ、選べばナツメのユンゲラーにもどる（はがしたカードは
        自分の手札。ワザのあとも番は終わる）。"""
        state = board(mon(SABRINAS_ALAKAZAM, (P, P)), bench=(MEW,))
        alakazam = state.players[0].active
        option = [o for o in E.available_attacks(state, alakazam) if o.card_id == MEW and o.attack_index == 1][0]
        self.assertEqual(option.route, "psylink")
        state = apply_kernel(state, UseAttack(0, 1, card=option.card))
        self.assertIn(alakazam.pokemon_id, state.decision.options)
        since = len(state.log)
        state = answer(state, [alakazam.pokemon_id])
        self.assertEqual(top(state, by_id(state, alakazam.pokemon_id)), SABRINAS_KADABRA)
        self.assertIn(alakazam.card, state.players[0].hand)
        self.assertEqual(kinds(state, since)[:2], ["devolve", "turn_end"])

    def test_transformed_ditto_is_not_an_evolved_pokemon(self):
        """［へんしん］のメタモンは、今の姿でなく実際の重なりで決める（進化カードが重なっていないので候補にならない）。ミュウの姿のメタモンがたいかビームを使える。"""
        state = board(mon(DITTO, (W, W)), mon(MEW, (P,)), bench=(mon(KADABRA),))
        ditto, kadabra = state.players[0].active, state.players[0].bench[0]
        self.assertNotIn(ditto.pokemon_id, E.devolution_candidates(state, (0, 1)))
        state = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual(state.decision.options, (kadabra.pokemon_id,))
        state = answer(state, [kadabra.pokemon_id])
        self.assertEqual(top(state, by_id(state, kadabra.pokemon_id)), ABRA)


# ---------------------------------------------------------------- 退化スプレー


class DevolutionSprayTest(unittest.TestCase):
    """退化スプレー: 自分の進化ポケモン 1 匹から、進化カードを上から何枚でもはがしてすてる（はがした枚数ぶん退化する）。"""

    def test_one_card_goes_to_the_discard_pile(self):
        """はがした進化カードは持ち主のトラッシュ（手札にもどさない）。ダメージ・エネルギー・場のポケモンの番号は変えない。ログは ``play_trainer`` → ``devolve`` →
        ``discard_trainer`` で、そのあとも同じ番が続く（MAIN）。"""
        state = board(mon(MEW, (P,)), bench=(mon(KADABRA, (P,), damage=10),), hand=(DEVOLUTION_SPRAY,))
        kadabra = state.players[0].bench[0]
        since = len(state.log)
        state = spray(state, kadabra.pokemon_id, 1)
        abra = by_id(state, kadabra.pokemon_id)
        self.assertEqual((top(state, abra), abra.damage, len(abra.energy), abra.devolved_turn), (ABRA, 10, 1, TURN))
        self.assertIn(kadabra.card, state.players[0].discard)
        self.assertNotIn(kadabra.card, state.players[0].hand)
        self.assertEqual(kinds(state, since), ["play_trainer", "devolve", "discard_trainer"])
        log = events(state, since, "devolve")[0]
        self.assertEqual((log["destination"], log["by_player"], log["trainer_card"], log["removed"]), (DEVOLVE_TO_DISCARD, 0, card_of(state, 0, DEVOLUTION_SPRAY, "discard"),
                                                                                                     (kadabra.card,)))
        self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 0))
        audited(self, state)

    def test_several_cards_and_the_count_decision(self):
        """2 進化ポケモンからは 0〜2 枚を選べる（上から順にはがす）。2 枚ならたねポケモンにもどり、2 枚ともトラッシュ（ログの ``removed`` は上から）。"""
        state = board(mon(SABRINAS_ALAKAZAM, (P,)), hand=(DEVOLUTION_SPRAY,))
        alakazam = state.players[0].active
        stack = alakazam.evolution_stack
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, DEVOLUTION_SPRAY)))
        self.assertEqual((state.decision.kind, state.decision.options), (SELECT_POKEMON, (alakazam.pokemon_id,)))
        state = answer(state, [alakazam.pokemon_id])
        self.assertEqual((state.decision.kind, state.decision.options, state.decision.player), (SELECT_DEVOLVE_COUNT, (0, 1, 2), 0))
        since = len(state.log)
        state = answer(state, [2])
        abra = by_id(state, alakazam.pokemon_id)
        self.assertEqual((top(state, abra), abra.evolution_stack, abra.evolved_turn), (SABRINAS_ABRA, (), None))
        self.assertEqual(events(state, since, "devolve")[0]["removed"], (alakazam.card, stack[1]))
        self.assertTrue({alakazam.card, stack[1]} <= set(state.players[0].discard))
        audited(self, state)

    def test_zero_cards_changes_nothing(self):
        """0 枚は「ことができる」の、はがさないこと（ログ ``devolve_declined``）。退化していないので特殊状態・持続する効果も消さない。"""
        state = board(mon(KADABRA, (P,), confusion=True), hand=(DEVOLUTION_SPRAY,))
        kadabra = state.players[0].active
        since = len(state.log)
        state = spray(state, kadabra.pokemon_id, 0)
        self.assertEqual(kinds(state, since), ["play_trainer", "devolve_declined", "discard_trainer"])
        after = by_id(state, kadabra.pokemon_id)
        self.assertEqual((top(state, after), after.conditions.confused, after.devolved_turn), (KADABRA, True, None))

    def test_special_conditions_and_retreat_failure_end(self):
        """退化したポケモンは特殊状態から回復し（理由 ``devolve``）、こんらんで「にげる」に失敗した記録も消える（GR-2000-P324-DEVOLUTION の「別のポケモン」）。"""
        state = board(mon(KADABRA, (P,), confusion=True, retreat_failed_turn=TURN), hand=(DEVOLUTION_SPRAY,))
        kadabra = state.players[0].active
        since = len(state.log)
        state = spray(state, kadabra.pokemon_id, 1)
        abra = by_id(state, kadabra.pokemon_id)
        self.assertEqual((abra.conditions.confused, abra.retreat_failed_turn), (False, None))
        self.assertEqual(events(state, since, "special_conditions_removed")[0]["reason"], "devolve")
        self.assertEqual(events(state, since, "retreat_failure_cleared")[0]["reason"], "devolve")

    def test_breeder_stack_returns_to_the_basic_pokemon(self):
        """ポケモン育て屋さんで 1 進化を飛ばした重なり（たね + 2 進化）からは、はがせるのは 1 枚で、たねポケモンにもどる（飛ばした 1 進化カードを作らない）。"""
        state = board(mon(BULBASAUR, (G,), played_turn=TURN - 2), hand=(POKEMON_BREEDER, VENUSAUR, DEVOLUTION_SPRAY))
        bulbasaur = state.players[0].active
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, POKEMON_BREEDER)))
        state = answer(state, [bulbasaur.pokemon_id])
        state = answer(state, [card_of(state, 0, VENUSAUR)])
        self.assertEqual(stack_ids(state, by_id(state, bulbasaur.pokemon_id)), [BULBASAUR, VENUSAUR])
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, DEVOLUTION_SPRAY)))
        state = answer(state, [bulbasaur.pokemon_id])
        self.assertEqual(state.decision.options, (0, 1))
        state = answer(state, [1])
        self.assertEqual(stack_ids(state, by_id(state, bulbasaur.pokemon_id)), [BULBASAUR])
        audited(self, state)

    def test_no_evolved_pokemon_is_unresolved(self):
        """自分の場に進化ポケモンがいないとき使えるかは決まらない（DV4。使う前に止める。状態が変わらない）。［へんしん］のメタモンは実際の重なりがないので数えない。"""
        state = board(mon(MEW, (P,)), hand=(DEVOLUTION_SPRAY,))
        assert_rejected(self, state, PlayTrainer(0, card_of(state, 0, DEVOLUTION_SPRAY)), DV4, UnsupportedError)
        ditto = board(mon(DITTO), mon(KADABRA), hand=(DEVOLUTION_SPRAY,))
        self.assertEqual(E.current_form(ditto, ditto.players[0].active).kind, "transform")
        assert_rejected(self, ditto, PlayTrainer(0, card_of(ditto, 0, DEVOLUTION_SPRAY)), DV4, UnsupportedError)

    def test_disguised_ninetales(self):
        """「ばける」でのせたカードのあるタケシのキュウコンは退化させられない（DV5。ほかに候補があれば選べるが選ぶと止める。それしかいなければ使う前）。"""
        state = board(mon(BROCKS_NINETALES, (W,)), hand=(KADABRA, DEVOLUTION_SPRAY), bench=(mon(HAUNTER),))
        state = disguise(state, state.players[0].active.pokemon_id, KADABRA)
        ninetales, haunter = state.players[0].active, state.players[0].bench[0]
        played = apply_kernel(state, PlayTrainer(0, card_of(state, 0, DEVOLUTION_SPRAY)))
        self.assertEqual((played.decision.options, played.decision.context_value("unresolved_choices")),
                         ((ninetales.pokemon_id, haunter.pokemon_id), (ninetales.pokemon_id,)))
        assert_rejected(self, played, ResolveDecision(0, played.decision.id, (ninetales.pokemon_id,)), DV5, UnsupportedError)
        only = board(mon(BROCKS_NINETALES, (W,)), hand=(KADABRA, DEVOLUTION_SPRAY))
        only = disguise(only, only.players[0].active.pokemon_id, KADABRA)
        assert_rejected(self, only, PlayTrainer(0, card_of(only, 0, DEVOLUTION_SPRAY)), DV5, UnsupportedError)

    def test_intermediate_knockout_is_unresolved(self):
        """複数枚をはがすとき、途中の重なりで最大HPがダメージ以下になり、最後の重なりでならない（または、カウントされるきぜつかが違う）枚数は、きぜつするかが決まらない
        （DV1。選べるが選ぶと止める）。途中と最後で同じ結果になる枚数は止めない。

        - ナツメのゲンガー（80。ダメージ 60）→ ナツメのゴースト（50。60 以下）→ ナツメのゴース（［ガスのからだ］で 40 + エネルギーカード 4 枚 × 10 = 80）: 2 枚は DV1
        - カブトプス（60。ダメージ 40）→ カブト（30。カウントされるきぜつ）→ なにかの化石（10。カウントされないきぜつ）: 2 枚は DV1"""
        state = board(mon(SABRINAS_GENGAR, (P, P, P, P), damage=60), hand=(DEVOLUTION_SPRAY,))
        gengar = state.players[0].active
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, DEVOLUTION_SPRAY)))
        state = answer(state, [gengar.pokemon_id])
        self.assertEqual(state.decision.context_value("unresolved_choices"), (2,))
        assert_rejected(self, state, ResolveDecision(0, state.decision.id, (2,)), DV1, UnsupportedError)
        knocked = answer(state, [1])  # 1 枚: ナツメのゴースト（50）できぜつ（途中も最後も同じ）
        self.assertEqual([e["kind"] for e in knocked.log if e["kind"] == "knock_out"][-1:], ["knock_out"])

    def test_fossil_line_intermediate_counted_difference(self):
        state = _fossil_kabutops_board(damage=40)
        kabutops = state.players[0].bench[0]
        self.assertEqual(stack_ids(state, kabutops), [MYSTERIOUS_FOSSIL, KABUTO, KABUTOPS])
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, DEVOLUTION_SPRAY)))
        state = answer(state, [kabutops.pokemon_id])
        self.assertEqual(state.decision.options, (0, 1, 2))
        self.assertEqual(state.decision.context_value("unresolved_choices"), (2,))
        assert_rejected(self, state, ResolveDecision(0, state.decision.id, (2,)), DV1, UnsupportedError)


class AfterTrainerKnockOutTest(unittest.TestCase):
    """退化スプレーで最大HPがのっているダメージ以下になった自分のポケモンは、カードをトラッシュしたあとで「きぜつ」する（``resolution.after_trainer``。ログ ``knock_out`` の
    ``timing`` は ``trainer``）。サイド → 勝ち負け → バトル場に出す のあと、同じ番の続き（MAIN）にもどる（p.323「16」・p.319・p.324「19」から導いた処理。SUPPORTED）。"""

    def test_prize_promote_and_the_turn_continues(self):
        state = board(mon(KADABRA, (P,), damage=30), bench=(mon(MEW, (P, P)),), hand=(DEVOLUTION_SPRAY,), prizes=6, opponent_prizes=6)
        kadabra, mew = state.players[0].active, state.players[0].bench[0]
        since = len(state.log)
        state = spray(state, kadabra.pokemon_id, 1)
        self.assertEqual(kinds(state, since), ["play_trainer", "devolve", "discard_trainer", "knock_out"])
        knock = events(state, since, "knock_out")[0]
        self.assertEqual((knock["player"], knock["timing"]), (0, "trainer"))
        self.assertIsNone(state.trainer_in_use)  # 使い終わってから（使用中のカードを残さない）
        self.assertEqual((state.phase, state.decision.player, state.decision.context_value("then")), (Phase.TAKE_PRIZE, 1, "continue_turn"))
        audited(self, state)
        state = apply_kernel(state, TakePrize(1, 0))
        self.assertEqual((state.phase, state.decision.player), (Phase.PROMOTE_ACTIVE, 0))
        state = apply_kernel(state, PromoteActive(0, mew.card))
        self.assertEqual((state.phase, state.current_player, state.turn_number), (Phase.MAIN, 0, TURN))
        since = len(state.log)
        state = apply_kernel(state, UseAttack(0, 0))  # 同じ番にワザを使える（サイコウェーブ）
        self.assertEqual([(e["kind"], e["turn"]) for e in state.log[since:since + 1]], [("attack", TURN)])

    def test_last_prize_ends_the_game(self):
        """相手の最後のサイドなら、相手の勝ち（バトル場に出す前に勝ち負けを判定する。p.311）。"""
        state = board(mon(KADABRA, (P,), damage=30), bench=(MEW,), hand=(DEVOLUTION_SPRAY,), opponent_prizes=1)
        state = spray(state, state.players[0].active.pokemon_id, 1)
        state = apply_kernel(state, TakePrize(1, 0))
        self.assertEqual((state.phase, state.result.winner), (Phase.GAME_OVER, 1))

    def test_no_bench_loses(self):
        """バトル場のポケモンがきぜつして、控えがいなければ負け（p.311）。"""
        state = board(mon(KADABRA, (P,), damage=30), bench=(), hand=(DEVOLUTION_SPRAY,))
        state = spray(state, state.players[0].active.pokemon_id, 1)
        state = apply_kernel(state, TakePrize(1, 0))
        self.assertEqual((state.phase, state.result.winner), (Phase.GAME_OVER, 1))

    def test_bench_knock_out_keeps_the_active(self):
        """ベンチのポケモンのきぜつなら、サイドのあとすぐに MAIN にもどる（バトル場に出す決定はない）。"""
        state = board(mon(MEW, (P,)), bench=(mon(KADABRA, damage=40), RATTATA), hand=(DEVOLUTION_SPRAY,))
        state = spray(state, state.players[0].bench[0].pokemon_id, 1)
        state = apply_kernel(state, TakePrize(1, 0))
        self.assertEqual((state.phase, state.current_player, [top(state, p) for p in state.players[0].bench]), (Phase.MAIN, 0, [RATTATA]))

    def test_transformed_ditto_max_hp_drop_is_unresolved(self):
        """自分のポケモンの退化で、相手の［へんしん］のメタモンの最大HPがのっているダメージ以下に下がる場合は、きぜつにするかが決まらない（v0.48 の MH1。その答えは
        受け付けない。0 枚は受け付ける）。"""
        state = board(mon(KADABRA, (P,)), mon(DITTO, damage=40), hand=(DEVOLUTION_SPRAY,))
        kadabra = state.players[0].active
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, DEVOLUTION_SPRAY)))
        state = answer(state, [kadabra.pokemon_id])
        assert_rejected(self, state, ResolveDecision(0, state.decision.id, (1,)), MH1, UnsupportedError)
        state = answer(state, [0])
        self.assertEqual(state.phase, Phase.MAIN)


class DevolutionInteractionTest(unittest.TestCase):
    """退化と、既存の処理の組み合わせ。"""

    def test_retaliation_ends_on_devolution(self):
        """わるいカメールの「こうらがえし」の効果は、たいかビームで退化したら消える（CR-SHELL-ATTACK-ENDS-ON-DEVOLUTION。v0.13 の S29 の「到達しない」は退化させるカードが
        未実装だったことの説明）。理由は ``devolve``。"""
        state = board(mon(MEW, (P, P)), mon(DARK_WARTORTLE, (W, W), evolved_from=ROCKET_SQUIRTLE, retaliation_received=TURN - 1))
        wartortle = state.players[1].active
        self.assertEqual(len(wartortle.persistent_effects), 1)
        since = len(state.log)
        state = beam(state, wartortle.pokemon_id)
        squirtle = by_id(state, wartortle.pokemon_id)
        self.assertEqual((top(state, squirtle), squirtle.persistent_effects), (ROCKET_SQUIRTLE, ()))
        self.assertEqual([e["reason"] for e in events(state, since, "persistent_effect_removed")], ["devolve"])

    def test_chemical_gas_ends_when_muk_devolves(self):
        """ベトベトンが退化したら、かがくへんかガスの力はなくなり、同じ番にほかの特殊能力を使える（CR-CHEMICAL-GAS-LEAVES。v0.8 の G16 は退化させるカードがなかった）。"""
        state = board(mon(MUK, (G,)), bench=(mon(ERIKAS_BELLSPROUT_40),), hand=(DEVOLUTION_SPRAY,))
        muk, bellsprout = state.players[0].active, state.players[0].bench[0]
        command = UsePokemonPower(0, bellsprout.pokemon_id, 0)
        assert_rejected(self, state, command, "POWER_SUPPRESSED", IllegalActionError)
        state = spray(state, muk.pokemon_id, 1)
        self.assertEqual(top(state, by_id(state, muk.pokemon_id)), GRIMER)
        self.assertEqual(state.phase, Phase.MAIN)
        apply_kernel(state, command)  # ようぶんきゅうしゅう（受け付ける。決定を出す）

    def test_allergy_pollen_starting_mid_trainer(self):
        """ベトベトンのかがくへんかガスで消えていたわるいラフレシアの［アレルギーかふん］は、退化スプレーでベトベトンを退化させたあとからはたらく。使っている最中の退化スプレーは
        最後まで処理してトラッシュし（使った時点で止めない）、そのあとのトレーナーは使えない（TRAINER_PREVENTED）。"""
        state = board(mon(MUK, (G,)), mon(DARK_VILEPLUME, evolved_from=["PMCG2-002", DARK_GLOOM]), hand=(DEVOLUTION_SPRAY, POTION))
        muk = state.players[0].active
        self.assertFalse(E.trainer_use_blockers(state, 0))
        since = len(state.log)
        state = spray(state, muk.pokemon_id, 1)
        self.assertEqual(kinds(state, since), ["play_trainer", "devolve", "discard_trainer"])
        self.assertTrue(E.trainer_use_blockers(state, 0))
        assert_rejected(self, state, PlayTrainer(0, card_of(state, 0, POTION)), "TRAINER_PREVENTED", IllegalActionError)

    def test_prehistoric_power_does_not_stop_devolution(self):
        """プテラの［げんしのちから］（進化できない）は退化を止めない。退化したポケモンの進化は［げんしのちから］で止まる（EVOLUTION_PREVENTED。DV2 より先）。"""
        state = board(mon(KADABRA, (P,)), mon(AERODACTYL, evolved_from=MYSTERIOUS_FOSSIL), hand=(DEVOLUTION_SPRAY, KADABRA))
        kadabra = state.players[0].active
        self.assertTrue(E.evolution_preventers(state))
        state = spray(state, kadabra.pokemon_id, 1)
        self.assertEqual(top(state, by_id(state, kadabra.pokemon_id)), ABRA)
        assert_rejected(self, state, EvolvePokemon(0, card_of(state, 0, KADABRA), kadabra.pokemon_id), "EVOLUTION_PREVENTED", IllegalActionError)

    def test_gaseous_form_after_devolution(self):
        """退化でナツメのゴースにもどると、［ガスのからだ］の最大HP（40 + ついているエネルギーカード × 10）がはたらく（今の場から求める）。"""
        state = board(mon(SABRINAS_HAUNTER, (P, P, P), damage=40), hand=(DEVOLUTION_SPRAY,))
        haunter = state.players[0].active
        self.assertEqual(max_hp(state, haunter), 50)
        state = spray(state, haunter.pokemon_id, 1)
        gastly = by_id(state, haunter.pokemon_id)
        self.assertEqual((top(state, gastly), max_hp(state, gastly), state.phase), (SABRINAS_GASTLY, 70, Phase.MAIN))

    def test_recall_record_after_devolution(self):
        """思い出させるの記録は、使ったときの対戦ポケモンの重なりについてのもの。退化で重なりが変わったら、そのワザは決まらない（v0.49 の RC3）。"""
        state = board(mon(SABRINAS_ALAKAZAM, (P, P, P)), hand=(RECALL, DEVOLUTION_SPRAY))
        alakazam = state.players[0].active
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, RECALL)))
        recalled = [o for o in E.available_attacks(state, by_id(state, alakazam.pokemon_id)) if o.route == "recall"]
        self.assertTrue(recalled)
        state = spray(state, alakazam.pokemon_id, 1)
        after = [o for o in E.available_attacks(state, by_id(state, alakazam.pokemon_id)) if o.route == "recall"]
        self.assertTrue(all(o.problem is not None and o.problem[0] == "UNRESOLVED_RECALL_TARGET_CHANGED" for o in after), after)

    def test_once_attack_record_of_removed_card_goes_away(self):
        """場に出てから 1 度だけ使えるワザの記録（v0.44。カードの uid とワザの位置）のうち、はがしたカードのものは消える（GR-2000-P324-DEVOLUTION の「退化前の進化カードに
        書かれている内容のすべては無効」。残ったカードの記録は残す。実装上の仮定）。"""
        state = board(mon(KOGAS_BEEDRILL, (G, G, G)), mon(HITMONCHAN, (F,)), hand=(DEVOLUTION_SPRAY,), turn=TURN - 2)
        beedrill = state.players[0].active
        state = apply_kernel(with_coin_results(state, T), UseAttack(0, 1))  # ひっさつばり（記録はワザの宣言のとき）
        state = apply_kernel(state, EndTurn(1))
        self.assertEqual(by_id(state, beedrill.pokemon_id).attacks_used_once, ((beedrill.card, 1),))
        state = spray(state, beedrill.pokemon_id, 1)
        kakuna = by_id(state, beedrill.pokemon_id)
        self.assertEqual((top(state, kakuna), kakuna.attacks_used_once), (KOGAS_KAKUNA, ()))
        audited(self, state)


class EvolveAfterDevolutionTest(unittest.TestCase):
    """この番に退化したポケモンを、同じ番に進化させられるか（p.310 の「その番に場に出した」「その番に進化した」の制限が、退化して別のポケモンになったポケモンに当てはまるか）は
    記録で決まらない（DV2。どの進化の入口でも、サカキの許可があっても止める）。次の番からは通常の進化の規定どおり。"""

    def devolved(self, *, hand=(), bench=(), turn=TURN):
        state = board(mon(KADABRA, (P,)), hand=(DEVOLUTION_SPRAY, *hand), bench=bench, turn=turn)
        kadabra = state.players[0].active
        return spray(state, kadabra.pokemon_id, 1), kadabra.pokemon_id

    def test_hand_evolution_same_turn_and_next_turn(self):
        state, pid = self.devolved(hand=(KADABRA,))
        command = EvolvePokemon(0, card_of(state, 0, KADABRA), pid)
        assert_rejected(self, state, command, DV2, UnsupportedError)
        self.assertEqual(evolution_block_code(state, pid, KADABRA), DV2)
        for _ in range(2):
            state = apply_kernel(state, EndTurn(state.current_player))
        state = apply_kernel(state, EvolvePokemon(0, card_of(state, 0, KADABRA), pid))
        self.assertEqual(top(state, by_id(state, pid)), KADABRA)
        audited(self, state)

    def test_breeder_and_deck_evolution(self):
        """ポケモン育て屋さん（退化したたねポケモンしか対象がなければ使う前、ほかに対象があれば選べるが選ぶと止める）・ワザで山札から重ねる進化（エリカのピッピの
        「つきのちから」）・特殊能力の［うか］も、この番に退化したポケモンには DV2。"""
        state = board(mon(VENUSAUR, (G,), evolved_from=[BULBASAUR, "PMCG1-008"]), hand=(DEVOLUTION_SPRAY, POKEMON_BREEDER, VENUSAUR))
        venusaur = state.players[0].active
        state = spray(state, venusaur.pokemon_id, 2)
        assert_rejected(self, state, PlayTrainer(0, card_of(state, 0, POKEMON_BREEDER)), DV2, UnsupportedError)
        # つきのちから: 山札の進化カードを重ねる（自分の場のこの番に退化したポケモンだけが対象）
        moon = board(mon(ERIKAS_CLEFAIRY, (P,)), bench=(mon(KADABRA),), hand=(DEVOLUTION_SPRAY,), deck=[KADABRA] * 5)
        moon = spray(moon, moon.players[0].bench[0].pokemon_id, 1)
        assert_stops(self, moon, UseAttack(0, 0), DV2)
        # ［うか］（キョウのコクーン。「おもて」で山札のキョウのスピアーを重ねる）
        kakuna = board(mon(KOGAS_BEEDRILL, (G,)), hand=(DEVOLUTION_SPRAY,), deck=[KOGAS_BEEDRILL] * 5)
        pid = kakuna.players[0].active.pokemon_id
        kakuna = spray(kakuna, pid, 1)
        assert_rejected(self, kakuna, UsePokemonPower(0, pid, 0), DV2, UnsupportedError)

    def test_giovanni_permission_does_not_decide_it(self):
        """サカキの許可（「その番に場に出た・進化した」でも進化させてよい）があっても、退化した番の進化は DV2（許可は退化を扱っていない）。"""
        giovanni_magikarp, giovanni_gyarados = "PMCG6-037", "PMCG6-040"
        state = board(mon(giovanni_gyarados, (W,), evolved_from=giovanni_magikarp), hand=(DEVOLUTION_SPRAY, GIOVANNI, giovanni_gyarados))
        pid = state.players[0].active.pokemon_id
        state = spray(state, pid, 1)
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, GIOVANNI)))
        state = answer(state, [pid])
        self.assertEqual(by_id(state, pid).evolution_permission_turn, TURN)
        assert_rejected(self, state, EvolvePokemon(0, card_of(state, 0, giovanni_gyarados), pid), DV2, UnsupportedError)


def evolution_block_code(state, pid, card_id):
    from kyuura_engine.evolution import evolution_block
    found = evolution_block(state, state.find_pokemon(pid)[1], state.card_def(card_of(state, 0, card_id)))
    return None if found is None else found[0]


class PowerUseAfterDevolutionTest(unittest.TestCase):
    """「自分の番ごとに1回」の特殊能力の使用の記録は、それを印刷したカードで区別する（v0.49）。退化でいちばん上にもどったカードが、この番、上に進化される前にすでに使った
    特殊能力をもう一度使えるかは記録で決まらない（DV3）。使っていないカードの特殊能力は使える。"""

    def test_power_of_a_card_that_did_not_use_it(self):
        """エリカのウツボットの［かおりのわな］を使ってから退化スプレーで 2 枚はがすと、エリカのマダツボミ（この番に使っていないカード）の［ようぶんきゅうしゅう］は使える。"""
        state = board(mon(ERIKAS_VICTREEBEL, (G,)), mon(HITMONCHAN), opponent_bench=(RATTATA,), bench=(mon(BULBASAUR, (G, G)),), hand=(DEVOLUTION_SPRAY,))
        pid = state.players[0].active.pokemon_id
        state = apply_kernel(with_coin_results(state, T), UsePokemonPower(0, pid, 0))  # かおりのわな（「うら」）
        self.assertEqual(state.power_uses_this_turn, ((pid, 0),))
        state = spray(state, pid, 2)
        self.assertEqual(top(state, by_id(state, pid)), ERIKAS_BELLSPROUT_40)
        state = apply_kernel(state, UsePokemonPower(0, pid, 0))  # ようぶんきゅうしゅう（受け付ける。決定を出す）
        self.assertEqual(state.decision.resume, "power")
        audited(self, state)

    def test_reuse_after_evolve_and_devolve(self):
        """自分の番の最初から場にいるわるいクサイハナで使ってから進化させる（エリカのマダツボミの［ようぶんきゅうしゅう］ → ポケモン育て屋さんでエリカのウツボット →
        退化スプレーで 2 枚はがす → エリカのマダツボミの［ようぶんきゅうしゅう］をもう一度: DV3）。"""
        state = board(mon(ERIKAS_BELLSPROUT_40, (G,)), bench=(mon(BULBASAUR, (G, G)),),
                      hand=(POKEMON_BREEDER, ERIKAS_VICTREEBEL, DEVOLUTION_SPRAY))
        bellsprout = state.players[0].active
        pid = bellsprout.pokemon_id
        state = apply_kernel(state, UsePokemonPower(0, pid, 0))
        state = answer(state, [state.decision.options[0]])
        self.assertEqual(state.power_uses_this_turn, ((pid, 0),))
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, POKEMON_BREEDER)))
        state = answer(state, [pid])
        state = answer(state, [card_of(state, 0, ERIKAS_VICTREEBEL)])
        # 進化で、使用の記録は使ったカード（エリカのマダツボミ）で区別する形になる（エリカのウツボットの［かおりのわな］は使っていない）
        self.assertEqual(state.power_uses_this_turn, ((pid, 0, bellsprout.card),))
        with self.assertRaises(ValueError):
            state_to_dict(state, format_version=14)  # 使ったカードで区別する記録は形式 15 から
        self.assertEqual(state_to_dict(state, format_version=15)["power_uses_this_turn"], [[pid, 0, bellsprout.card]])
        state = spray(state, pid, 1)
        self.assertEqual(top(state, by_id(state, pid)), ERIKAS_BELLSPROUT_40)
        assert_rejected(self, state, UsePokemonPower(0, pid, 0), DV3, UnsupportedError)

    def test_evolved_card_power_is_not_blocked_by_the_lower_card(self):
        """進化したカードの「自分の番ごとに1回」の特殊能力は、下のカードが同じ番に使ったことでは止まらない（v0.50 の変更。進化は「別のポケモン」。v0.49 までは場のポケモンの
        番号で数え、使えないことにしていた）。"""
        state = board(mon(ERIKAS_BELLSPROUT_40, (G,)), mon(HITMONCHAN), opponent_bench=(RATTATA,), bench=(mon(BULBASAUR, (G, G)),),
                      hand=(POKEMON_BREEDER, ERIKAS_VICTREEBEL))
        pid = state.players[0].active.pokemon_id
        state = apply_kernel(state, UsePokemonPower(0, pid, 0))
        state = answer(state, [state.decision.options[0]])
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, POKEMON_BREEDER)))
        state = answer(state, [pid])
        state = answer(state, [card_of(state, 0, ERIKAS_VICTREEBEL)])
        since = len(state.log)
        state = apply_kernel(with_coin_results(state, T), UsePokemonPower(0, pid, 0))  # かおりのわな（「うら」）
        self.assertEqual(kinds(state, since)[:2], ["pokemon_power", "coin_flip"])
        self.assertIn((pid, 0), state.power_uses_this_turn)  # いちばん上のカード（エリカのウツボット）の使用
        audited(self, state)


class StateAndSerializationTest(unittest.TestCase):
    """状態の項目・書き出しの形式 15・観測・不変条件。"""

    def test_format_15(self):
        """退化した番（``devolved_turn``）は形式 15 で書き出す。形式 1〜14 は、退化したポケモンがいると ``ValueError``（黙って落とさない）。"""
        state = board(mon(KADABRA, (P,)), hand=(DEVOLUTION_SPRAY,))
        pid = state.players[0].active.pokemon_id
        self.assertEqual(max(FORMAT_VERSIONS), 15)
        before = state_to_dict(state, format_version=14)
        self.assertNotIn("devolved_turn", json.dumps(before))
        state = spray(state, pid, 1)
        data = state_to_dict(state, format_version=15)
        active = data["players"][0]["active"]
        self.assertEqual(active["devolved_turn"], TURN)
        for version in (1, 9, 14):
            with self.subTest(version=version), self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)
        audited(self, state)

    def test_observation_shows_devolution(self):
        """観測の場のポケモンに ``devolved_turn``。ログの ``devolve``・``devolve_declined``・``devolve_none`` は公開（だれにでも見える）。"""
        state = board(mon(MEW, (P, P)), mon(GYARADOS))
        state = beam(state, state.players[1].active.pokemon_id)
        for viewer in (0, 1, None):
            with self.subTest(viewer=viewer):
                view = observe(state, viewer)
                self.assertEqual(view["players"][1]["active"]["devolved_turn"], TURN)
                logs = [e for e in visible_log(state, viewer) if e["kind"] == "devolve"]
                self.assertEqual(len(logs), 1)
                self.assertEqual(logs[0]["removed_ids"], (GYARADOS,))

    def test_invariants_reject_inconsistent_devolution_records(self):
        """不変条件: 退化した番は今の番以下で、そのポケモンの退化のログと合う。重なりはログの進化・退化を逆にたどった形と合う。"""
        state = board(mon(MEW, (P, P)), mon(GYARADOS))
        state = beam(state, state.players[1].active.pokemon_id)
        self.assertEqual(check_invariants(state), [])
        broken = state.clone()
        magikarp = broken.players[1].active
        magikarp.devolved_turn = broken.turn_number + 1
        self.assertTrue(check_invariants(broken))
        broken = state.clone()
        broken.players[1].active.devolved_turn = None
        self.assertTrue(check_invariants(broken))


class FossilDevolutionTest(unittest.TestCase):
    """なにかの化石の上の進化カードをすべてはがすと、場での役割（v0.47）のなにかの化石にもどる。"""

    def test_back_to_the_fossil_without_damage(self):
        state = _fossil_kabutops_board(damage=0)
        pid = state.players[0].bench[0].pokemon_id
        state = spray(state, pid, 2)
        fossil = by_id(state, pid)
        self.assertEqual((stack_ids(state, fossil), state.card_def(fossil.card).play_role is not None, max_hp(state, fossil)), ([MYSTERIOUS_FOSSIL], True, 10))
        self.assertEqual(state.phase, Phase.MAIN)
        audited(self, state)

    def test_uncounted_knock_out_after_the_trainer(self):
        """カブトプス（ダメージ 20）から 2 枚: 途中のカブト（30）ではきぜつせず、最後のなにかの化石（10）できぜつする（途中と最後で結果が同じなので DV1 ではない）。
        進化カードがのっていないなにかの化石のきぜつはカウントされない（v0.47）ので、相手はサイドを取らず、同じ番が続く。"""
        state = _fossil_kabutops_board(damage=20)
        pid = state.players[0].bench[0].pokemon_id
        prizes = len(state.players[1].prizes)
        since = len(state.log)
        state = spray(state, pid, 2)
        knock = events(state, since, "knock_out")[0]
        self.assertEqual((knock["timing"], knock["counted"]), ("trainer", False))
        self.assertEqual((state.phase, len(state.players[1].prizes), state.find_pokemon(pid)), (Phase.MAIN, prizes, None))
        audited(self, state)


def _fossil_kabutops_board(*, damage):
    """なにかの化石 → カブト → カブトプスの重なり（実際に場に出して進化させる。なにかの化石を場に出したログが要る）。バトル場はミュウ、カブトプスはベンチ。"""
    state = board(mon(MEW, (P,)), bench=(), hand=(MYSTERIOUS_FOSSIL, KABUTO, KABUTOPS, DEVOLUTION_SPRAY), turn=TURN - 4)
    state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, MYSTERIOUS_FOSSIL)))
    fossil = state.players[0].bench[-1]
    for _ in range(2):
        state = apply_kernel(state, EndTurn(state.current_player))
    state = apply_kernel(state, EvolvePokemon(0, card_of(state, 0, KABUTO), fossil.pokemon_id))
    for _ in range(2):
        state = apply_kernel(state, EndTurn(state.current_player))
    state = apply_kernel(state, EvolvePokemon(0, card_of(state, 0, KABUTOPS), fossil.pokemon_id))
    by_id(state, fossil.pokemon_id).damage = damage
    return state


class CommonDevolveTest(unittest.TestCase):
    """退化の共通の処理 ``evolution.devolve``（たいかビーム・退化スプレーで共通。通常の進化の逆再生・「ばける」をもどす処理は使わない）の前提の確かめ。"""

    def test_rejects_calls_outside_its_contract(self):
        """行き先は手札かトラッシュ、枚数は 1〜重なっている進化カードの数、「ばける」のポケモンは不可、ワザの効果かトレーナーの効果のどちらか一方。どれも状態を変える前に
        例外（呼ぶ側の確認の漏れ。エンジンの不具合）。"""
        state = board(mon(SABRINAS_ALAKAZAM, (P,)))
        alakazam = state.players[0].active
        calls = (
            dict(count=1, destination="deck", effect="x"),
            dict(count=0, destination=DEVOLVE_TO_HAND, effect="x"),
            dict(count=3, destination=DEVOLVE_TO_HAND, effect="x"),
            dict(count=1, destination=DEVOLVE_TO_HAND),
            dict(count=1, destination=DEVOLVE_TO_HAND, effect="x", trainer=1),
        )
        for call in calls:
            with self.subTest(call=call):
                copy = state.clone()
                count = call.pop("count")
                with self.assertRaises((ValueError, RuntimeError)):
                    devolve(copy, 0, copy.players[0].active, count, by_player=0, **call)
                self.assertEqual(snapshot(copy), snapshot(state))
        self.assertEqual(alakazam.evolution_stack, state.players[0].active.evolution_stack)

    def test_keeps_damage_energy_trainers_and_identity(self):
        """ダメージ・エネルギー・ついているトレーナー（有効期限も）・場のポケモンの番号・場に出た番は変えない（いちばん上のカードと重なりだけが変わる）。"""
        state = board(mon(SABRINAS_ALAKAZAM, (P, P), damage=20, trainers=[(PLUSPOWER, TURN)], played_turn=1))
        before = state.players[0].active
        copy = state.clone()
        target = copy.players[0].active
        removed = devolve(copy, 0, target, 2, destination=DEVOLVE_TO_DISCARD, by_player=0, trainer=999)
        self.assertEqual(removed, (before.card, before.evolution_stack[1]))
        self.assertEqual((target.pokemon_id, target.damage, target.energy, target.trainers, target.played_turn),
                         (before.pokemon_id, before.damage, before.energy, before.trainers, before.played_turn))
        self.assertEqual((target.card, target.evolution_stack, target.evolved_turn, target.devolved_turn), (before.evolution_stack[0], (), None, TURN))


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.50 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.50 の 4 組を 2 seed ずつ（席を入れかえて 16 局）。どれも監査の失敗（やり直し・不変条件・ログ・書き出し・観測）・想定外の拒否・内部エラー・手数の上限がなく、
        2 枚の処理（サイコウェーブ・たいかビームで自分・相手のポケモンを退化・退化スプレーで 0・1・2 枚・トレーナーのあとのきぜつ）が使われる（勝敗は判断に使わない）。"""
        from tools import existing_effect_games as games

        results = games.run(range(2), pairings=games.PAIRINGS_V0_50)
        totals = {}
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"), game.get("error"))
                if game["outcome"] == "halted":
                    self.assertIn(game["halt_code"], NEW_CODES + (MH1, "UNRESOLVED_MULLIGAN_COMPENSATION"))
                for card, uses in game.get("card_uses", {}).items():
                    for key, count in uses.items():
                        totals[(card, key)] = totals.get((card, key), 0) + count
        for card, key in ((MEW, "attack#0"), (MEW, "attack#1"), (MEW, "beam_devolve_opponent"), (MEW, "beam_devolve_own"),
                          (DEVOLUTION_SPRAY, "devolve_1"), (DEVOLUTION_SPRAY, "devolve_2"), (DEVOLUTION_SPRAY, "devolve_declined"),
                          (DEVOLUTION_SPRAY, "knock_out_after_spray")):
            with self.subTest(card=card, key=key):
                self.assertGreater(totals.get((card, key), 0), 0)


class DocumentTest(unittest.TestCase):
    def test_document_names_the_stop_codes_and_records(self):
        text = DOC.read_text(encoding="utf-8")
        for code in NEW_CODES:
            self.assertIn(code, text)
        for record in ("GR-2000-P324-DEVOLUTION", "CR-SHELL-ATTACK-ENDS-ON-DEVOLUTION", "CR-CHEMICAL-GAS-LEAVES", "GR-2000-P323-KNOCKOUT"):
            self.assertIn(record, text)


if __name__ == "__main__":
    unittest.main()
