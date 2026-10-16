"""v0.38: 控えへのダメージ・入れ替え・同じコインの複数の効果・軽減・山札にもどる効果の 15 枚（docs/bench-switch-combined-v0.38.md）。

カードの登録と記録（``CardDataTest``）、説明の文面の受け付けと拒否（``TextTest``）、進化（``EvolutionTest``）、相手の控えを選ぶダメージ（``ChosenBenchTest``）、
控え全員へのダメージ（``SpreadTest``）、相手が選ぶ入れ替え（``ForceSwitchTest``）、げきとつと GK1（``RamTest``）、自分の控えとの入れ替え（``SelfSwitchTest``）、
同じコインの複数の効果（``SameCoinTest``）、受けるダメージの軽減（``BarrierAttackTest``）、いなくなる（``VanishTest``）、でんれい（``MessengerTest``）、
まねるワザ（``CopyTest``）、不変条件・書き出し・保存と再開・拒否で状態が変わらない（``IntegrityTest``）、先読みの方法ごとの一致（``PreflightParityTest``）に分けた。

根拠は kyuura データの採用（kyuura の印刷の文面。``card_sources.json``）と、既存の記録の再利用（p.309 のワザの手順と「処理の対象がない」・p.320 の要素の順番・
p.321 のダメージの計算の段階・p.322・p.323 の持続する効果・p.325 の入れ替え・CR-COUNTERATTACK-TIMING・CR-ENERGY-CONVERSION-ORDER・v0.36 の RD2）。ガイドブックは
読んでいない。
"""

from __future__ import annotations

import copy
import pathlib
import pickle
import re
import unittest

from kyuura_engine import (
    EngineError,
    EvolvePokemon,
    IllegalActionError,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    check_invariants,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, read_extract
from kyuura_engine.decisions import FORCED_SWITCH, PROMOTE_ACTIVE, SEARCH_DECK, SELECT_ATTACK, SELECT_POKEMON
from kyuura_engine.persistent import attack_barrier, damage_reduction
from kyuura_engine.resolution import PREFLIGHT_MODES, v013_checks
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import AttackBarrier, DamageReduction
from scripts import check_card_sources as cs
from scripts.extract_kyuura_cards import KYUURA_COMMIT
from tests.helpers import (
    ABRA,
    ARBOK,
    ARTICUNO,
    ATTACK_TYPES_SINCE_V0_17,
    BLAINES_PONYTA,
    BLAINES_RAPIDASH,
    BLAINES_RHYHORN,
    BROCKS_GOLBAT,
    BROCKS_RHYHORN,
    BROCKS_VULPIX,
    BROCKS_VULPIX_50,
    BROCKS_ZUBAT,
    CATERPIE,
    CLEFABLE,
    CLEFAIRY,
    DEFENDER,
    ERIKAS_TANGELA,
    FIGHTING,
    FIRE,
    FOSSIL_EKANS,
    FOSSIL_ZUBAT,
    GASTLY,
    GIOVANNIS_NIDORAN_F,
    GIOVANNIS_NIDORINA,
    GRASS,
    HAUNTER,
    HITMONCHAN,
    HITMONLEE,
    KOGAS_KOFFING,
    KOGAS_PIDGEOTTO,
    KOGAS_PIDGEY,
    KOGAS_PIDGEY_40,
    KOGAS_WEEDLE,
    LIGHTNING,
    MACHAMP,
    MACHOKE,
    MACHOP,
    METAPOD,
    MISTYS_PSYDUCK,
    NIDORAN_F,
    PIKACHU,
    PLUSPOWER,
    PONYTA,
    PSYCHIC,
    RATTATA,
    RHYDON,
    RHYHORN,
    ROCKET_ABRA,
    ROCKET_EKANS,
    ROCKET_ZUBAT,
    ROCKETS_MOLTRES,
    SABRINAS_PORYGON,
    TANGELA,
    V0_38_POKEMON,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.test_barrier_resume_coin_bonus_v0_34 import assert_stops, coins, events, first, full, kinds, play, with_barrier

ROOT = pathlib.Path(__file__).resolve().parent.parent
TURN = 7
DOC = ROOT / "docs" / "bench-switch-combined-v0.38.md"
BELOW = {BROCKS_GOLBAT: BROCKS_ZUBAT, ARBOK: FOSSIL_EKANS, RHYDON: RHYHORN, BLAINES_RAPIDASH: BLAINES_PONYTA, KOGAS_PIDGEOTTO: KOGAS_PIDGEY,
         GIOVANNIS_NIDORINA: GIOVANNIS_NIDORAN_F, CLEFABLE: CLEFAIRY, MACHAMP: [MACHOP, MACHOKE], HAUNTER: GASTLY}
# ワザを使うのに足りるエネルギー
ENERGY = {ARTICUNO: (WATER,) * 4, HITMONLEE: (FIGHTING,) * 3, ERIKAS_TANGELA: (GRASS,) * 3, BROCKS_VULPIX_50: (FIRE, FIRE), BROCKS_GOLBAT: (GRASS,) * 3,
          ARBOK: (GRASS,) * 3, RHYDON: (FIGHTING,) * 4, BLAINES_PONYTA: (FIRE, FIRE), BLAINES_RAPIDASH: (FIRE,) * 3, KOGAS_PIDGEOTTO: (LIGHTNING,) * 4,
          KOGAS_WEEDLE: (GRASS, GRASS), GIOVANNIS_NIDORINA: (GRASS,) * 3, SABRINAS_PORYGON: (LIGHTNING, LIGHTNING), ROCKET_ABRA: (PSYCHIC,),
          KOGAS_PIDGEY_40: (LIGHTNING, LIGHTNING)}
# 登録の実装の型と値（カード id, ワザの位置）
EXPECTED = {
    (ARTICUNO, 0): (E.ParalyzeOnHeads, {}),
    (ARTICUNO, 1): (E.DamageThenCoinBenchDamageEitherSide, {"bench_damage": 10}),
    (HITMONLEE, 0): (E.ChooseOpponentBenchDamage, {"damage": 20, "requires_bench": True}),
    (HITMONLEE, 1): (E.DamageOnly, {}),
    (ERIKAS_TANGELA, 0): (E.DamageOnly, {}),
    (ERIKAS_TANGELA, 1): (E.ChooseOpponentBenchDamage, {"damage": 20, "requires_bench": False}),
    (BROCKS_VULPIX_50, 0): (E.PutToSleep, {}),
    (BROCKS_VULPIX_50, 1): (E.DamageThenChosenBenchDamage, {"bench_damage": 10}),
    (BROCKS_GOLBAT, 0): (E.DamageOnly, {}),
    (BROCKS_GOLBAT, 1): (E.SpreadDamage, {"damage": 10}),
    (ARBOK, 0): (E.DamageThenForceSwitchOnHeads, {}),
    (ARBOK, 1): (E.PoisonOpponent, {}),
    (RHYDON, 0): (E.DamageOnly, {}),
    (RHYDON, 1): (E.DamageThenForceSwitchThenSelfDamage, {"self_damage": 20}),
    (BLAINES_PONYTA, 0): (E.DamageThenSelfSwitchOnHeads, {}),
    (BLAINES_RAPIDASH, 0): (E.DamageOnly, {}),
    (BLAINES_RAPIDASH, 1): (E.CoinBonusDamageAndBenchDamage, {"bonus": 10, "bench_damage": 10}),
    (KOGAS_PIDGEOTTO, 0): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 30}),
    (KOGAS_PIDGEOTTO, 1): (E.CoinBonusDamageAndSelfBarrier, {"bonus": 30}),
    (KOGAS_WEEDLE, 0): (E.DamageOnly, {}),
    (KOGAS_WEEDLE, 1): (E.DamageThenPoisonOrParalyze, {}),
    (GIOVANNIS_NIDORINA, 0): (E.DamageAndSelfDamageThenPoisonOnHeads, {"self_damage": 20}),
    (GIOVANNIS_NIDORINA, 1): (E.ParalyzeOnHeads, {}),
    (SABRINAS_PORYGON, 0): (E.DamageOnly, {}),
    (SABRINAS_PORYGON, 1): (E.DamageThenReduceDamageNextTurn, {"amount": 10}),
    (ROCKET_ABRA, 0): (E.DiscardAttachedAndReturnSelfToDeck, {}),
    (ROCKET_ABRA, 1): (E.ParalyzeOnHeads, {}),
    (KOGAS_PIDGEY_40, 0): (E.ReturnSelfToDeckThenSearchPokemon, {"excluded": ("キョウのポッポ",)}),
    (KOGAS_PIDGEY_40, 1): (E.DamageOnly, {}),
}
# pcg-search.com の対象の版（サイトの一覧の番号。kyuura の id の番号とは違うことがある）
EDITIONS = {ARTICUNO: "023/048", HITMONLEE: "038/048", ERIKAS_TANGELA: "016/096", BROCKS_VULPIX_50: "019/096", BROCKS_GOLBAT: "003/096",
            ARBOK: "002/048", RHYDON: "033/048", BLAINES_PONYTA: "032/098", BLAINES_RAPIDASH: "033/098", KOGAS_PIDGEOTTO: "066/098",
            KOGAS_WEEDLE: "005/098", GIOVANNIS_NIDORINA: "019/098", SABRINAS_PORYGON: "063/098", ROCKET_ABRA: "031/065", KOGAS_PIDGEY_40: "064/098"}


def mon(card, energy=None, **extra):
    spec = {"card": card, "energy": list(ENERGY.get(card, ()) if energy is None else energy), **extra}
    if BELOW.get(card) is not None and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), deck=None, opponent_deck=None, turn=TURN):
    me = {"active": active, "bench": list(bench)}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent or mon(HITMONCHAN, (FIGHTING, FIGHTING)), "bench": list(opponent_bench)}
    if opponent_deck is not None:
        them["deck"] = list(opponent_deck)
    return build_test_state([me, them], turn_number=turn)


def snapshot(state):
    return full(state), rng_fingerprint(state.rng), [dict(e) for e in state.log]


def attack(state, index, *sides, answers=(), player=0, mode="derived"):
    return play(with_coin_results(state, *sides), UseAttack(player, index), answers, mode=mode)


def pid_of(state, player, card):
    """プレイヤー ``player`` の場の ``card``（カード id）のポケモンの番号（最初の 1 匹）。"""
    return next(p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card)


def bench_damage(state, since, target="opponent_bench"):
    return {e["pokemon_id"]: e["amount"] for e in events(state, since, "damage") if e.get("target") == target}


def opponent_damage(state, since):
    return [e["amount"] for e in events(state, since, "damage") if e.get("target") is None and not e.get("retaliation")]


def assert_rejected(test, state, command, code, exception=EngineError):
    before = snapshot(state)
    with test.assertRaises(exception) as raised:
        apply_kernel(state, command)
    test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def card_count(state, player):
    """プレイヤーのカードの枚数（ゾーンのすべて。カードの保存則）。"""
    p = state.players[player]
    in_play = sum(len(x.cards()) + len(x.energy) + len(x.trainers) for x in p.in_play())
    return len(p.hand) + len(p.deck) + len(p.discard) + len(p.prizes) + in_play


class CardDataTest(unittest.TestCase):
    """15 枚の登録・写し・採用の記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_fifteen_requested_cards(self):
        """対象は依頼の 15 枚（ほかの候補に広げていない）。写しの組 pool_v0_38 は 15 枚で、どれも対戦に使える。同じ名前の別のカード（タケシのロコン PMCG5-018・
        キョウのポッポ PMCG6-062・第1弾のケーシィ PMCG1-043）とは別の id で、ワザも HP も違う。"""
        self.assertEqual(len(V0_38_POKEMON), 15)
        self.assertEqual(list(read_extract()["pool_v0_38"]), list(V0_38_POKEMON))
        for card in V0_38_POKEMON:
            with self.subTest(card=card):
                self.assertTrue(self.pool.is_playable(card))
        for ours, other in ((BROCKS_VULPIX_50, BROCKS_VULPIX), (KOGAS_PIDGEY_40, KOGAS_PIDGEY), (ROCKET_ABRA, ABRA)):
            with self.subTest(card=ours):
                a, b = self.pool.get(ours), self.pool.get(other)
                self.assertEqual(a.name_ja, b.name_ja)
                self.assertNotEqual((a.hp, [x.name_ja for x in a.attacks]), (b.hp, [x.name_ja for x in b.attacks]))

    def test_every_attack_is_registered_with_the_expected_implementation(self):
        """29 のワザがどれも登録され、型と値が説明に合う。説明文のあるワザは、写しの文面（照合用）と処理に使う文面（kyuura の印刷の文面）が同じ。"""
        attacks = [(card, a.index) for card in V0_38_POKEMON for a in self.pool.get(card).attacks]
        self.assertEqual(sorted(attacks), sorted(EXPECTED))
        self.assertEqual(len(attacks), 29)
        for (card, index), (cls, values) in EXPECTED.items():
            with self.subTest(card=card, index=index):
                entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
                self.assertIs(type(entry.effect), cls)
                for name, value in values.items():
                    self.assertEqual(getattr(entry.effect, name), value)
                printed = self.pool.get(card).attacks[index]
                self.assertEqual(entry.name_ja, printed.name_ja)
                self.assertEqual(entry.text_ja, printed.text_ja)
                self.assertEqual(entry.play_text_ja, printed.text_ja)
                self.assertEqual(entry.effect.check(printed), [])

    def test_new_types_are_kernel_programs_outside_the_v013_contract(self):
        """v0.38 の型は解決の基盤の要素の並び（``programs.BUILDERS``）で処理し、v0.13 の約束（``resolve``・``resume``）を上書きしない。``v013_checks.VERIFIED`` に
        入れない（tests/helpers.py の ``ATTACK_TYPES_SINCE_V0_17`` に加えた）。"""
        from kyuura_engine.resolution import programs

        new = {cls for cls, _ in EXPECTED.values() if cls.implementation_id in {
            "choose_opponent_bench_damage", "damage_then_chosen_bench_damage", "spread_damage", "damage_then_coin_bench_damage_either_side",
            "coin_bonus_damage_and_bench_damage", "damage_then_force_switch_on_heads", "damage_then_force_switch_then_self_damage",
            "damage_then_self_switch_on_heads", "coin_bonus_damage_and_self_barrier", "damage_then_poison_or_paralyze",
            "damage_and_self_damage_then_poison_on_heads", "damage_then_reduce_damage_next_turn", "discard_attached_and_return_self_to_deck",
            "return_self_to_deck_then_search_pokemon"}}
        self.assertEqual(len(new), 14)
        for cls in new:
            with self.subTest(cls=cls.__name__):
                self.assertIn(cls, programs.BUILDERS)
                self.assertIn(cls, ATTACK_TYPES_SINCE_V0_17)
                self.assertNotIn(cls, v013_checks.VERIFIED)
                self.assertIs(cls.resolve, E.AttackEffect.resolve)
                self.assertIs(cls.resume, E.AttackEffect.resume)

    def test_adoption_records_and_external_checks(self):
        """15 枚はどれも kyuura データの採用の記録（写しの元のコミット・説明文のあるワザの処理に使う文面の根拠）を持ち、pcg-search.com の同じ版のページと
        照合して match（違いなし）。kyuura に LD-・エラッタ・裁定の記録はない（``kyuura_records`` は空）。過去の原典照合の記録（card_verification.json）には入れない。"""
        sources = cs.load_sources()["cards"]
        verification = __import__("json").loads((ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8"))["cards"]
        links = cs.load_links()["latest_descriptions"]["adopted_printed_text"]
        for card in V0_38_POKEMON:
            with self.subTest(card=card):
                record = sources[card]
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]), ("kyuura_data", "adopted", KYUURA_COMMIT))
                self.assertEqual(record["kyuura_records"], [])
                with_text = {f"attack/{a.index}" for a in self.pool.get(card).attacks if a.text_ja}
                self.assertEqual(set(record["play_text"]), with_text)
                self.assertTrue(all(v == "kyuura_printed_text" for v in record["play_text"].values()))
                self.assertTrue(with_text <= {k.split("/", 1)[1] for k in links if k.startswith(card + "/")})
                [check] = record["external_checks"]
                self.assertEqual((check["site"], check["result"], check["differences"]), ("pcg-search.com", "match", []))
                self.assertEqual(check["edition"]["list_number"], EDITIONS[card])
                self.assertNotIn(card, verification)

    def test_no_card_specific_branch_in_the_engine(self):
        """engine.py・resolution/ に v0.38 のカード id での分岐を加えていない（効果の型と要素の項目で表す）。"""
        for path in [ROOT / "kyuura_engine" / "engine.py", *(ROOT / "kyuura_engine" / "resolution").glob("*.py")]:
            text = path.read_text(encoding="utf-8")
            for card in V0_38_POKEMON:
                with self.subTest(path=path.name, card=card):
                    self.assertNotIn(card, text)

    def test_gk1_is_a_new_question_with_one_code(self):
        """GK1 は新しい問い（既存の問いのどれとも違う: C18・W24 は同時のきぜつ、C34/C35 は 2 つ以上の効果、Z23 はダメージを与えた後）。コードは 1 つで、
        研究の対応表では kyuura の未解決の一覧にない（not_in_kyuura）。文書に根拠と影響の範囲を書いた。"""
        question = QUESTIONS["damage_trigger_timing"]
        self.assertEqual((question.code, question.rulings), ("UNRESOLVED_DAMAGE_TRIGGER_TIMING", ("GK1",)))
        self.assertEqual([q.key for q in QUESTIONS.values() if q.code == question.code], ["damage_trigger_timing"])
        links = cs.load_links()
        self.assertEqual(links["stop_codes"]["UNRESOLVED_DAMAGE_TRIGGER_TIMING"]["kyuura_disposition"], "not_in_kyuura")
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (44, 45))
        self.assertIn("GK1", DOC.read_text(encoding="utf-8"))


class TextTest(unittest.TestCase):
    """型の ``check`` は、登録したワザの印刷の文面と同じ書き方だけを受け付ける（似たワザの文面を推測で同じ型にしない）。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def printed(self, card, index):
        return self.pool.get(card).attacks[index]

    def test_bench_choice_condition_is_part_of_the_text(self):
        """のびるキック（使えない、の記述あり）とのびるつる（なし）は、同じ型の別の値で、もう一方の文面は受け付けない。"""
        kick, vine = self.printed(HITMONLEE, 0), self.printed(ERIKAS_TANGELA, 1)
        self.assertEqual(E.ChooseOpponentBenchDamage(20, requires_bench=True).check(kick), [])
        self.assertNotEqual(E.ChooseOpponentBenchDamage(20, requires_bench=True).check(vine), [])
        self.assertEqual(E.ChooseOpponentBenchDamage(20, requires_bench=False).check(vine), [])
        self.assertNotEqual(E.ChooseOpponentBenchDamage(20, requires_bench=False).check(kick), [])
        self.assertNotEqual(E.ChooseOpponentBenchDamage(30, requires_bench=True).check(kick), [])

    def test_other_texts_are_rejected(self):
        """量・面・名前の違う書き方は受け付けない（ふぶきの面の入れ替え・ほかのダメージ・除く名前の違い）。"""
        import dataclasses

        blizzard = self.printed(ARTICUNO, 1)
        swapped = dataclasses.replace(blizzard, text_ja=blizzard.text_ja.replace("「おもて」なら相手", "「おもて」なら自分").replace("「うら」なら自分", "「うら」なら相手"))
        self.assertNotEqual(E.DamageThenCoinBenchDamageEitherSide(10).check(swapped), [])
        self.assertNotEqual(E.DamageThenCoinBenchDamageEitherSide(20).check(blizzard), [])
        messenger = self.printed(KOGAS_PIDGEY_40, 0)
        self.assertNotEqual(E.ReturnSelfToDeckThenSearchPokemon(("ポッポ",)).check(messenger), [])
        self.assertNotEqual(E.DamageThenReduceDamageNextTurn(20).check(self.printed(SABRINAS_PORYGON, 1)), [])
        # 同じ「自分を山札にもどす」でも、くもがくれガス（ついているカードも山札へ）の文面は、いなくなる（トラッシュ）の型で受け付けない
        cloud = self.printed(KOGAS_KOFFING, 1)
        self.assertNotEqual(E.DiscardAttachedAndReturnSelfToDeck().check(cloud), [])
        self.assertNotEqual(E.DamageThenReturnSelfToDeckOnHeads().check(self.printed(ROCKET_ABRA, 0)), [])


class EvolutionTest(unittest.TestCase):
    """進化元は名前の完全一致（収録の弾で制限しない）。名前の一部・形容詞で比べない。"""

    def evolve(self, basic, stage1):
        state = build_test_state([{"active": mon(basic, (), played_turn=1), "bench": [RATTATA], "hand": [stage1]},
                                  {"active": mon(HITMONCHAN, ()), "bench": [RATTATA]}], turn_number=TURN)
        return apply_kernel(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].active.pokemon_id))

    def test_evolves_from_every_card_with_the_exact_name(self):
        """アーボックは化石の秘密とロケット団の「アーボ」の両方から、キョウのピジョンは 2 種類の「キョウのポッポ」から進化する。カツラのギャロップは同じ作業で
        加えたカツラのポニータから。"""
        for basic, stage1 in ((FOSSIL_EKANS, ARBOK), (ROCKET_EKANS, ARBOK), (KOGAS_PIDGEY, KOGAS_PIDGEOTTO), (KOGAS_PIDGEY_40, KOGAS_PIDGEOTTO),
                              (BLAINES_PONYTA, BLAINES_RAPIDASH), (BROCKS_ZUBAT, BROCKS_GOLBAT), (RHYHORN, RHYDON), (GIOVANNIS_NIDORAN_F, GIOVANNIS_NIDORINA)):
            with self.subTest(basic=basic, stage1=stage1):
                state = self.evolve(basic, stage1)
                self.assertEqual(state.cards[state.players[0].active.card].card_id, stage1)
                self.assertEqual(check_invariants(state), [])

    def test_names_that_only_look_alike_are_rejected(self):
        """名前が違えば進化しない（ポニータ → カツラのギャロップ・ズバット → タケシのゴルバット・タケシ／カツラのサイホーン → サイドン・ニドラン♀ → サカキの
        ニドリーナ）。"""
        for basic, stage1 in ((PONYTA, BLAINES_RAPIDASH), (FOSSIL_ZUBAT, BROCKS_GOLBAT), (ROCKET_ZUBAT, BROCKS_GOLBAT), (BROCKS_RHYHORN, RHYDON),
                              (BLAINES_RHYHORN, RHYDON), (NIDORAN_F, GIOVANNIS_NIDORINA)):
            with self.subTest(basic=basic, stage1=stage1), self.assertRaises(IllegalActionError) as raised:
                self.evolve(basic, stage1)
            self.assertEqual(raised.exception.code, "EVOLUTION_NAME_MISMATCH")


class ChosenBenchTest(unittest.TestCase):
    """相手の控えを 1 匹選ぶダメージ（のびるキック・のびるつる・ほのおのわ）。選ぶのはワザを使ったプレイヤー。弱点・抵抗力は説明に明記のとおり計算しない。"""

    def test_stretch_kick_chooser_candidates_and_calculation(self):
        """のびるキック: 相手の対戦ポケモンにダメージを与えない。選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``）、選べるものは相手の控えの全員。闘に
        弱点のあるピカチュウ（控え）にも 20（弱点を計算しない）。コインを投げない。"""
        state = board(mon(HITMONLEE), opponent_bench=(RATTATA, PIKACHU))
        after = attack(state, 0)
        d = after.decision
        self.assertEqual((d.kind, d.player, d.options), (SELECT_POKEMON, 0, tuple(p.pokemon_id for p in after.players[1].bench)))
        pikachu = pid_of(after, 1, PIKACHU)
        done = apply_kernel(after, ResolveDecision(0, d.id, (pikachu,)))
        since = len(state.log)
        self.assertEqual(bench_damage(done, since), {pikachu: 20})
        self.assertEqual(opponent_damage(done, since), [])
        self.assertEqual(coins(done, since), [])

    def test_stretch_kick_cannot_be_used_without_opponent_bench(self):
        """のびるキック: 相手に控えポケモンがいないとき、このワザは使えない（ワザを使うための条件。必要なエネルギーの確認のあと・コインの前）。状態・乱数・ログは
        変わらない。"""
        assert_rejected(self, board(mon(HITMONLEE), opponent_bench=()), UseAttack(0, 0), "NO_OPPONENT_BENCH", IllegalActionError)

    def test_stretch_vine_without_opponent_bench_is_usable_and_does_nothing(self):
        """のびるつる: 使えない、の記述がないので使える。処理の対象がないので何もしない（p.309。v0.31 のかどわかすと同じ読み方）。ワザは使ったことになり、番は
        終わる。"""
        state = board(mon(ERIKAS_TANGELA), opponent_bench=())
        after = attack(state, 1)
        self.assertEqual(kinds(after, len(state.log))[:2], ["attack", "turn_end"])
        self.assertEqual(after.current_player, 1)

    def test_plus_power_does_not_change_bench_damage_but_defender_does(self):
        """控えへのダメージ: プラスパワーは変えない（p.257）、受ける控えのディフェンダーは変える（v0.33 のかけぬけると同じ計算）。"""
        state = board(mon(HITMONLEE, trainers=[(PLUSPOWER, TURN)]), opponent_bench=({"card": RATTATA, "trainers": [(DEFENDER, TURN)]}, PIKACHU))
        rattata, pikachu = [p.pokemon_id for p in state.players[1].bench]
        for target, expected in ((rattata, 0), (pikachu, 20)):
            with self.subTest(target=target):
                done = attack(state, 0, answers=[(target,)])
                self.assertEqual(bench_damage(done, len(state.log)), {target: expected})

    def test_fire_ring_damages_active_then_chosen_bench(self):
        """ほのおのわ: 相手の対戦ポケモンに 20（炎に弱点のあるモンジャラは 40）→ 控えを選んで 10（弱点・抵抗力なし）。控えがいなければ対戦ポケモンへのダメージだけ。"""
        state = board(mon(BROCKS_VULPIX_50), mon(TANGELA, ()), opponent_bench=(PIKACHU,))
        done = attack(state, 1, answers=[first])
        since = len(state.log)
        self.assertEqual(opponent_damage(done, since), [40])
        self.assertEqual(list(bench_damage(done, since).values()), [10])
        alone = attack(board(mon(BROCKS_VULPIX_50), mon(TANGELA, ()), opponent_bench=()), 1)
        self.assertEqual(alone.decision, None)
        self.assertEqual(opponent_damage(alone, len(state.log)), [40])

    def test_counterattack_after_the_bench_damage(self):
        """ほのおのわ: 相手のカイリキーの「はんげき」は、控えへのダメージ（決定のあと）のあとに処理する（ダメージの処理をすべてのせたあと。CR-COUNTERATTACK-TIMING。
        v0.34 の続きの情報で運ぶ）。"""
        state = board(mon(BROCKS_VULPIX_50), mon(MACHAMP, (FIGHTING,)), opponent_bench=(PIKACHU,))
        done = attack(state, 1, answers=[first])
        order = [k for k in kinds(done, len(state.log)) if k in ("damage", "counterattack")]
        self.assertEqual(order, ["damage", "damage", "counterattack"])
        self.assertEqual(done.players[0].active.damage, 10)


class SpreadTest(unittest.TestCase):
    """控え全員へのダメージ（かいてんひこう・ふぶき・ふみあらす）。"""

    def test_spin_flight_hits_active_and_every_bench(self):
        """かいてんひこう: 相手の対戦ポケモン（草に弱点のあるサイホーンにも 10。弱点・抵抗力なし）と控えの全員に 10。プラスパワーは対戦ポケモンへのダメージだけ
        変える。"""
        state = board(mon(BROCKS_GOLBAT, trainers=[(PLUSPOWER, TURN)]), mon(RHYHORN, ()), opponent_bench=(RATTATA, PIKACHU))
        done = attack(state, 1)
        since = len(state.log)
        self.assertEqual(opponent_damage(done, since), [20])
        self.assertEqual(sorted(bench_damage(done, since).values()), [10, 10])
        plain = attack(board(mon(BROCKS_GOLBAT), mon(RHYHORN, ()), opponent_bench=(RATTATA, PIKACHU)), 1)
        self.assertEqual(opponent_damage(plain, since), [10])

    def test_blizzard_heads_hits_opponent_bench_tails_hits_own_bench(self):
        """ふぶき: 1 枚のコインで「おもて」なら相手の控え全員、「うら」なら自分の控え全員に 10（弱点・抵抗力なし）。相手の対戦ポケモンへの 50 はコインによらない。"""
        state = board(mon(ARTICUNO), bench=(RATTATA, PIKACHU), opponent_bench=(RATTATA, PIKACHU))
        since = len(state.log)
        heads = attack(state, 1, H)
        self.assertEqual(coins(heads, since), ["heads"])
        self.assertEqual(sorted(bench_damage(heads, since).values()), [10, 10])
        self.assertEqual(bench_damage(heads, since, "self_bench"), {})
        tails = attack(state, 1, T)
        self.assertEqual(bench_damage(tails, since), {})
        self.assertEqual(sorted(bench_damage(tails, since, "self_bench").values()), [10, 10])
        self.assertEqual(opponent_damage(heads, since), opponent_damage(tails, since))

    def test_blizzard_without_any_bench_does_not_flip(self):
        """ふぶき: 自分にも相手にも控えがいなければ、このコインが決める要素のどれにも対象がないので投げない（p.309）。片方にだけいれば投げる。"""
        state = board(mon(ARTICUNO), bench=(), opponent_bench=())
        done = attack(state, 1)
        self.assertEqual(coins(done, len(state.log)), [])
        one = board(mon(ARTICUNO), bench=(RATTATA,), opponent_bench=())
        heads = attack(one, 1, H)
        self.assertEqual((coins(heads, len(one.log)), bench_damage(heads, len(one.log), "self_bench")), (["heads"], {}))
        tails = attack(one, 1, T)
        self.assertEqual(list(bench_damage(tails, len(one.log), "self_bench").values()), [10])

    def test_blizzard_own_bench_knockout_is_processed_after_the_attack(self):
        """ふぶきの「うら」で自分の控えが HP 以上になったら、ワザのあとのきぜつの処理できぜつし、相手がサイドを取る（ワザの途中できぜつさせない）。"""
        state = board(mon(ARTICUNO), bench=({"card": RATTATA, "damage": 20}, PIKACHU))
        done = attack(state, 1, T, answers=[first])
        log = kinds(done, len(state.log))
        self.assertLess(log.index("damage"), log.index("knock_out"))
        self.assertIn("take_prize", log)
        self.assertEqual(len(done.players[1].prizes), len(state.players[1].prizes) - 1)

    def test_coin_is_flipped_when_only_bench_damage_remains(self):
        """「ワザをうけない」状態（バリアー）の相手の対戦ポケモンへのダメージは無効でも、控えへのダメージは残るので、ふぶき・ふみあらすのコインは投げる（v0.34 の
        ``void_coin_question``）。"""
        for card, index in ((ARTICUNO, 1), (BLAINES_RAPIDASH, 1)):
            with self.subTest(card=card):
                state = with_barrier(mon(card))
                since = len(state.log)
                done = attack(state, index, H, player=1)
                self.assertEqual(coins(done, since), ["heads"])
                self.assertIn("damage_prevented", kinds(done, since))
                self.assertEqual(list(bench_damage(done, since).values()), [10])

    def test_trample_without_opponent_bench_against_prevented_damage_stops(self):
        """ふみあらすを、控えのいない相手の「ダメージを受けない」（かたまる）・「ワザをうけない」（バリアー）状態の対戦ポケモンに使うと、コインが決める要素は
        無効な追加のダメージと対象のない控えへのダメージだけで、投げても場は変わらないので、v0.4b の問い（``UNRESOLVED_PREVENTED_COIN_DAMAGE``）で宣言の前に
        止める（v0.34 の ``void_coin_question``。対象のない要素は数えない）。控えがいれば、控えへのダメージが残るので投げる（上のテスト）。"""
        prevented = board(mon(BLAINES_RAPIDASH), {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": TURN - 1}, opponent_bench=())
        assert_stops(self, prevented, UseAttack(0, 1), "UNRESOLVED_PREVENTED_COIN_DAMAGE")
        with_bench = board(mon(BLAINES_RAPIDASH), {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": TURN - 1})
        done = attack(with_bench, 1, H)
        since = len(with_bench.log)
        self.assertEqual((coins(done, since), list(bench_damage(done, since).values())), (["heads"], [10]))
        self.assertIn("damage_prevented", kinds(done, since))

    def test_trample_same_coin_decides_bonus_and_bench_damage(self):
        """ふみあらす: 1 枚のコインの「おもて」で相手に 30 + 10 と、相手の控え全員に 10（弱点・抵抗力なし）。「うら」なら 30 だけ。コインは 1 枚。"""
        state = board(mon(BLAINES_RAPIDASH), opponent_bench=(RATTATA, PIKACHU))
        since = len(state.log)
        heads = attack(state, 1, H)
        self.assertEqual((coins(heads, since), opponent_damage(heads, since), sorted(bench_damage(heads, since).values())), (["heads"], [40], [10, 10]))
        tails = attack(state, 1, T)
        self.assertEqual((coins(tails, since), opponent_damage(tails, since), bench_damage(tails, since)), (["tails"], [30], {}))


class ForceSwitchTest(unittest.TestCase):
    """アーボックの「いかくこうげき」: ダメージ → コインの「おもて」で相手が選ぶ控えと入れ替える。"""

    def test_heads_opponent_chooses_and_switch_clears_conditions(self):
        """「おもて」: 入れ替わるポケモンを選ぶのは相手（決定 ``FORCED_SWITCH`` の ``player`` は相手）。ベンチにもどったポケモンの特殊状態は消える（p.311・p.322）。
        「うら」: 入れ替えない（ログ forced_switch がない）。"""
        state = board(mon(ARBOK), mon(HITMONCHAN, (), poison=10), opponent_bench=(RATTATA, PIKACHU))
        since = len(state.log)
        after = attack(state, 0, H)
        d = after.decision
        self.assertEqual((d.kind, d.player, d.options), (FORCED_SWITCH, 1, tuple(p.pokemon_id for p in state.players[1].bench)))
        old = state.players[1].active.pokemon_id
        done = apply_kernel(after, ResolveDecision(1, d.id, (d.options[1],)))
        self.assertEqual(done.players[1].active.pokemon_id, d.options[1])
        moved = next(p for p in done.players[1].bench if p.pokemon_id == old)
        self.assertIsNone(moved.conditions.poison)
        self.assertEqual(kinds(done, since)[:4], ["attack", "damage", "coin_flip", "forced_switch"])
        tails = attack(state, 0, T)
        self.assertNotIn("forced_switch", kinds(tails, since))

    def test_no_bench_or_knocked_out_target_means_no_coin(self):
        """相手に控えがいない・相手の対戦ポケモンがこのワザのダメージで HP 以上なら、入れ替えの対象がないのでコインを投げない（p.309。ログ forced_switch_skipped）。"""
        for opponent, bench, reason in ((mon(HITMONCHAN, ()), (), E.NO_BENCH), (mon(RATTATA, (), damage=20), (PIKACHU,), E.TARGET_KNOCKED_OUT)):
            with self.subTest(reason=reason):
                state = board(mon(ARBOK), opponent, opponent_bench=bench)
                done = attack(state, 0, answers=[first] if reason == E.TARGET_KNOCKED_OUT else [])
                since = len(state.log)
                attack_events = kinds(done, since)[:kinds(done, since).index("forced_switch_skipped") + 1]
                self.assertNotIn("coin_flip", attack_events)
                self.assertEqual(events(done, since, "forced_switch_skipped")[0]["reason"], reason)

    def test_barrier_and_transparency_stop_before_the_declaration(self):
        """コインは入れ替え（相手への効果）だけを決めるので、「ワザをうけない」相手には HC3、「とうめい」で受けないと決まりうる相手には T19b で、宣言の前に
        止める（どの先読みの方法でも。状態・乱数・ログは変わらない）。"""
        assert_stops(self, with_barrier(mon(ARBOK)), UseAttack(1, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")
        assert_stops(self, board(mon(ARBOK), mon(HAUNTER, (PSYCHIC,))), UseAttack(0, 0), "UNRESOLVED_EVADED_EFFECT_COIN")


class RamTest(unittest.TestCase):
    """サイドンの「げきとつ」: ダメージ → 相手が選ぶ入れ替え → 自分にも 20（説明の順。CR-ENERGY-CONVERSION-ORDER と同じく書かれた順）。"""

    def test_order_and_self_damage_after_the_switch(self):
        """相手へのダメージ → 入れ替え（相手の決定）→ 自分へのダメージ。入れ替えるのは相手の場なので、自分へのダメージを受けるのはサイドンのまま。"""
        state = board(mon(RHYDON), opponent_bench=(RATTATA, PIKACHU))
        since = len(state.log)
        after = attack(state, 1)
        d = after.decision
        self.assertEqual((d.kind, d.player), (FORCED_SWITCH, 1))
        self.assertEqual(after.players[0].active.damage, 0)  # 自分へのダメージは入れ替えのあと
        done = apply_kernel(after, ResolveDecision(1, d.id, first(d)))
        self.assertEqual([k for k in kinds(done, since) if k in ("damage", "forced_switch")], ["damage", "forced_switch", "damage"])
        self.assertEqual(done.players[0].active.damage, 20)
        self.assertEqual(events(done, since, "damage")[-1]["target"], "self")

    def test_no_bench_still_deals_self_damage(self):
        """相手に控えがいなければ入れ替えは起こらない（ログ forced_switch_skipped）が、自分への 20 は与える。"""
        state = board(mon(RHYDON), opponent_bench=())
        done = attack(state, 1)
        since = len(state.log)
        self.assertIn("forced_switch_skipped", kinds(done, since))
        self.assertEqual(done.players[0].active.damage, 20)

    def test_simultaneous_knockout_by_the_same_attack(self):
        """相手がこのワザの 50 で、サイドンが自分への 20 で HP 以上になると、入れ替えず（対象がいない）、ワザのあとのきぜつの判定で両方がきぜつする（同じワザの
        中のきぜつは同時。p.324）。ワザの途中できぜつさせない。"""
        state = board(mon(RHYDON, damage=80), mon(HITMONCHAN, (), damage=20), bench=(RATTATA,), opponent_bench=(PIKACHU,))
        done = play(state, UseAttack(0, 1), [first, first, first, first])
        log = kinds(done, len(state.log))
        self.assertEqual(log.count("knock_out"), 2)
        self.assertLess(max(i for i, k in enumerate(log) if k == "damage"), log.index("knock_out"))
        self.assertIn("forced_switch_skipped", log)

    def test_damage_trigger_stops_before_the_declaration(self):
        """GK1: 相手の対戦ポケモンが「ダメージを受けたとき」の効果（はたらいている「はんげき」・ほのおのかべの持続する効果）を持つと、その効果を処理する時点が
        決められない（ダメージの処理（自分へのダメージを含む）をすべてのせたあと、かつダメージ以外の効果の前、という記録の時点が、入れ替えをはさむこの並びにない）
        ので、宣言の前に止める。"""
        assert_stops(self, board(mon(RHYDON), mon(MACHAMP, (FIGHTING,))), UseAttack(0, 1), "UNRESOLVED_DAMAGE_TRIGGER_TIMING")
        assert_stops(self, board(mon(RHYDON), mon(ROCKETS_MOLTRES, (FIRE,), retaliation=TURN - 1)), UseAttack(0, 1), "UNRESOLVED_DAMAGE_TRIGGER_TIMING")

    def test_proceeds_without_a_damage_trigger(self):
        """隣の止まらない場合: カイリキーがねむり状態なら「はんげき」ははたらかない（候補にならない）ので止めない（入れ替えの決定に進む）。"""
        state = board(mon(RHYDON), mon(MACHAMP, (FIGHTING,), sleep=True))
        after = attack(state, 1)
        self.assertEqual(after.decision.kind, FORCED_SWITCH)


class SelfSwitchTest(unittest.TestCase):
    """カツラのポニータの「けりにげ」: ダメージ → コインの「おもて」で自分の控えを選んで入れ替える。"""

    def test_heads_attacker_chooses_and_tails_does_nothing(self):
        """「おもて」: 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。選べるものは自分の控え）。入れ替えはポケモンいれかえと同じ処理（ログ switch に
        ワザの effect）。「うら」: 入れ替えない。"""
        state = board(mon(BLAINES_PONYTA), bench=(RATTATA, PIKACHU))
        since = len(state.log)
        after = attack(state, 0, H)
        d = after.decision
        self.assertEqual((d.kind, d.player, d.options), (SELECT_POKEMON, 0, tuple(p.pokemon_id for p in state.players[0].bench)))
        done = apply_kernel(after, ResolveDecision(0, d.id, (d.options[1],)))
        self.assertEqual(done.players[0].active.pokemon_id, d.options[1])
        self.assertEqual(events(done, since, "switch")[0]["effect"], f"{BLAINES_PONYTA}#0")
        tails = attack(state, 0, T)
        self.assertNotIn("switch", kinds(tails, since))

    def test_no_bench_or_knocked_out_attacker_means_no_coin(self):
        """自分に控えがいない・このカードが相手の「はんげき」で HP 以上になったなら、処理の対象がないのでコインを投げない（p.309。CR-COUNTERATTACK-KO-ATTACKER）。
        HP 以上になったポニータは、ワザのあとのきぜつの判定できぜつする。"""
        alone = board(mon(BLAINES_PONYTA), bench=())
        self.assertEqual(coins(attack(alone, 0), len(alone.log)), [])
        state = board(mon(BLAINES_PONYTA, damage=40), mon(MACHAMP, (FIGHTING,)))
        done = play(state, UseAttack(0, 0), [first, first])
        since = len(state.log)
        self.assertEqual(coins(done, since), [])
        self.assertIn("counterattack", kinds(done, since))
        self.assertEqual(events(done, since, "knock_out")[0]["pokemon"], state.players[0].active.card)


class SameCoinTest(unittest.TestCase):
    """同じコインで複数の効果を決めるワザ（こうそくひこう・きけんなはり・どくばりタックル）。要素ごとに投げ直さない。"""

    def test_agility_flight_heads_bonus_and_barrier(self):
        """こうそくひこう: 1 枚のコインの「おもて」で 10 + 30 と、このカードに ``AttackBarrier``（次の相手の番、相手のワザによるダメージや効果を受けない）。
        「うら」なら 10 だけで効果なし。"""
        state = board(mon(KOGAS_PIDGEOTTO))
        since = len(state.log)
        heads = attack(state, 1, H)
        pidgeotto = heads.players[0].active
        self.assertEqual((coins(heads, since), opponent_damage(heads, since)), (["heads"], [40]))
        self.assertIsInstance(attack_barrier(heads, pidgeotto) or next(e for e in pidgeotto.persistent_effects if isinstance(e, AttackBarrier)),
                              AttackBarrier)
        tails = attack(state, 1, T)
        self.assertEqual((coins(tails, since), opponent_damage(tails, since), tails.players[0].active.persistent_effects), (["tails"], [10], ()))

    def test_agility_flight_flips_against_a_barrier(self):
        """相手が「ワザをうけない」状態でも、自分への効果が残るので投げる（v0.34 の ``void_coin_question``）。追加のダメージは無効、バリアーは与える。"""
        state = with_barrier(mon(KOGAS_PIDGEOTTO))
        since = len(state.log)
        done = attack(state, 1, H, player=1)
        self.assertEqual(coins(done, since), ["heads"])
        self.assertIn("damage_prevented", kinds(done, since))
        self.assertTrue(any(isinstance(e, AttackBarrier) for e in done.players[1].active.persistent_effects))

    def test_agility_flight_barrier_skipped_when_knocked_out_by_counterattack(self):
        """このカードが相手の「はんげき」で HP 以上になったら、自分への効果は与えない（ログ persistent_effect_skipped）。"""
        state = board(mon(KOGAS_PIDGEOTTO, damage=50), mon(MACHAMP, (FIGHTING,)))
        done = play(with_coin_results(state, H), UseAttack(0, 1), [first, first])
        since = len(state.log)
        log = kinds(done, since)
        self.assertLess(log.index("counterattack"), log.index("persistent_effect_skipped"))
        self.assertNotIn("persistent_effect_added", log)

    def test_dangerous_needle_one_coin_poison_or_paralysis(self):
        """きけんなはり: 1 枚のコインで「おもて」ならどく、「うら」ならマヒ（投げ直さない）。「ワザをうけない」相手には HC3、ダメージで HP 以上なら投げない。"""
        state = board(mon(KOGAS_WEEDLE))
        since = len(state.log)
        heads = attack(state, 1, H)
        self.assertEqual((coins(heads, since), [e["condition"] for e in events(heads, since, "special_condition")]), (["heads"], ["poison"]))
        tails = attack(state, 1, T)
        self.assertEqual((coins(tails, since), [e["condition"] for e in events(tails, since, "special_condition")]), (["tails"], ["paralysis"]))
        assert_stops(self, with_barrier(mon(KOGAS_WEEDLE)), UseAttack(1, 1), "UNRESOLVED_PREVENTED_EFFECT_COIN")
        ko = board(mon(KOGAS_WEEDLE), mon(RATTATA, (), damage=20), opponent_bench=(PIKACHU,))
        self.assertEqual(coins(attack(ko, 1, answers=[first, first]), len(ko.log)), [])

    def test_poison_tackle_order_and_counterattack(self):
        """どくばりタックル: 相手へのダメージ → 自分にも 20 →「はんげき」（ダメージの処理をすべてのせたあと）→ コイン → どく。サカキのニドリーナが自分への 20 で
        HP 以上なら「はんげき」は与えない（counterattack_skipped。C15）が、相手へのどくは処理する（CR-COUNTERATTACK-KO-ATTACKER）。"""
        state = board(mon(GIOVANNIS_NIDORINA), mon(MACHAMP, (FIGHTING,)))
        since = len(state.log)
        done = attack(state, 0, H)
        order = [k for k in kinds(done, since) if k in ("damage", "counterattack", "coin_flip", "special_condition")]
        self.assertEqual(order, ["damage", "damage", "counterattack", "coin_flip", "special_condition"])
        dying = board(mon(GIOVANNIS_NIDORINA, damage=60), mon(MACHAMP, (FIGHTING,)))
        after = play(with_coin_results(dying, H), UseAttack(0, 0), [first, first])
        log = kinds(after, len(dying.log))
        self.assertIn("counterattack_skipped", log)
        self.assertEqual(events(after, len(dying.log), "special_condition")[0]["condition"], "poison")

    def test_poison_tackle_barrier_stops(self):
        """どくばりタックルのコインはどく（相手への効果）だけを決める。相手が「ワザをうけない」状態なら、自分へのダメージが残っても、コインを投げるかは決められない
        （HC3）。"""
        assert_stops(self, with_barrier(mon(GIOVANNIS_NIDORINA)), UseAttack(1, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")


class BarrierAttackTest(unittest.TestCase):
    """ナツメのポリゴンの「バリアアタック」: ダメージ → 次の相手の番、このカードがワザによって受けるダメージは −10（v0.31 のちいさくなると同じ ``DamageReduction``）。"""

    def test_reduction_step_expiry_and_removal(self):
        """効果は p.321 の 8 段階で、次の相手の番のワザのダメージを 10 へらす（エビワラーのジャブ 20 → ポリゴン（闘に弱点）は 40 − 10 = 30）。次の相手の番の終わりに
        消える（v0.31 と同じ期限）。"""
        state = board(mon(SABRINAS_PORYGON), mon(HITMONCHAN, (FIGHTING,)))
        done = attack(state, 1)
        porygon = done.players[0].active
        reduction = damage_reduction(done, porygon) or next(e for e in porygon.persistent_effects if isinstance(e, DamageReduction))
        self.assertEqual((reduction.amount, reduction.active_turn), (10, TURN + 1))
        since = len(done.log)
        hit = play(done, UseAttack(1, 0))
        damage = events(hit, since, "damage")[0]
        self.assertEqual(damage["amount"], 30)
        self.assertIn(8, [step for step, _, _ in damage["modifiers"]])
        self.assertEqual(hit.players[0].active.persistent_effects, ())

    def test_skipped_when_knocked_out_by_counterattack(self):
        """このカードが相手の「はんげき」で HP 以上になったら与えない（ログ persistent_effect_skipped）。"""
        state = board(mon(SABRINAS_PORYGON, damage=30), mon(MACHAMP, (FIGHTING,)))
        done = play(state, UseAttack(0, 1), [first, first])
        self.assertIn("persistent_effect_skipped", kinds(done, len(state.log)))


class VanishTest(unittest.TestCase):
    """ケーシィ（ロケット団）の「いなくなる」: カウンターをとりのぞき、ついているカードをトラッシュ → このカードを山札にもどして切る。"""

    def board(self, **extra):
        return board(mon(ROCKET_ABRA, damage=20, trainers=[(PLUSPOWER, TURN)], **extra), bench=(RATTATA, PIKACHU))

    def test_order_destinations_and_single_shuffle(self):
        """順番: remove_all_damage_counters → discard_attached_cards（エネルギー・プラスパワーはトラッシュ）→ return_in_play_to_deck（このカードだけ。山札の一番下）→
        持続する効果の消去 → shuffle（1 回）。きぜつではない（knock_out・サイドなし）。カードの枚数は変わらない。"""
        state = self.board(poison=10)
        abra = state.players[0].active
        energy = tuple(abra.energy)
        since = len(state.log)
        after = attack(state, 0)
        log = kinds(after, since)
        self.assertEqual(log[:5], ["attack", "remove_all_damage_counters", "discard_attached_cards", "return_in_play_to_deck", "shuffle"])
        discarded = events(after, since, "discard_attached_cards")[0]
        self.assertEqual((discarded["energy"], len(discarded["trainers"])), (energy, 1))
        returned = events(after, since, "return_in_play_to_deck")[0]
        self.assertEqual((returned["cards"], returned["energy"], returned["trainers"], returned["damage"]), ((abra.card,), (), (), 0))
        self.assertEqual(log.count("shuffle"), 1)
        self.assertNotIn("knock_out", log)
        self.assertIn(abra.card, after.players[0].deck)
        self.assertTrue(set(energy) <= set(after.players[0].discard))
        self.assertEqual(card_count(after, 0), card_count(state, 0))
        self.assertEqual(len(after.players[1].prizes), len(state.players[1].prizes))

    def test_replacement_after_the_attack(self):
        """バトル場が空くので、ワザのあとのバトル場に出す決定（``PROMOTE_ACTIVE``。選ぶのはワザを使ったプレイヤー。v0.36 のくもがくれガスと同じ）。控えがいなければ
        負け（p.311）。"""
        state = self.board()
        after = attack(state, 0)
        d = after.decision
        self.assertEqual((d.kind, d.player, d.resume), (PROMOTE_ACTIVE, 0, "promote_active"))
        lone = board(mon(ROCKET_ABRA), bench=())
        over = attack(lone, 0)
        self.assertEqual(over.result.winner, 1)
        self.assertEqual([c[1] for c in over.result.conditions], ["OPPONENT_CANNOT_FIELD_ACTIVE"])

    def test_attached_cards_go_to_deck_for_cloud_gas_but_to_discard_here(self):
        """ついているカードの行き先は、くもがくれガス（自分とついているカードを山札に）と違う（いなくなるはトラッシュ）。"""
        abra = attack(self.board(), 0)
        koffing_state = board(mon(KOGAS_KOFFING, (GRASS, GRASS)), bench=(RATTATA,))
        koffing = attack(koffing_state, 1, H)
        returned = events(koffing, len(koffing_state.log), "return_in_play_to_deck")[0]
        self.assertEqual(len(returned["energy"]), 2)
        self.assertEqual(events(abra, 0, "return_in_play_to_deck")[-1]["energy"], ())


class MessengerTest(unittest.TestCase):
    """キョウのポッポ（PMCG6-067）の「でんれい」: 自分とついているカードを山札にもどす → 控えから対戦ポケモンを出す → 「キョウのポッポ」以外のポケモンを見せて
    手札に加える → 切る（1 回）。"""

    def board(self, *, bench=(RATTATA, PIKACHU), deck=(KOGAS_PIDGEY, RATTATA, GRASS, PIKACHU, KOGAS_PIDGEY_40)):
        return board(mon(KOGAS_PIDGEY_40, trainers=[(PLUSPOWER, TURN)]), bench=bench, deck=deck)

    def test_order_owners_and_resume_points(self):
        """もどす（ついているエネルギー・プラスパワーも山札へ。ここでは切らない）→ 決定 1（``SELECT_POKEMON``。ワザを使ったプレイヤー。選べるものは自分の控え）→
        決定 2（``SEARCH_DECK``。選べるものは山札のポケモンで名前が「キョウのポッポ」でないもの。2 種類のキョウのポッポとエネルギーは選べない）→ reveal_from_deck
        （公開）→ shuffle（1 回）。"""
        state = self.board()
        pidgey = state.players[0].active
        since = len(state.log)
        first_step = attack(state, 0)
        self.assertEqual(kinds(first_step, since), ["attack", "return_in_play_to_deck"])
        self.assertIsNone(first_step.players[0].active)
        returned = events(first_step, since, "return_in_play_to_deck")[0]
        self.assertEqual(set(returned["cards"]), {pidgey.card, *pidgey.energy, *(t.card for t in pidgey.trainers)})
        d1 = first_step.decision
        self.assertEqual((d1.kind, d1.player, d1.resume, d1.options), (SELECT_POKEMON, 0, "attack", tuple(p.pokemon_id for p in state.players[0].bench)))
        self.assertEqual(check_invariants(first_step), [])
        second = apply_kernel(first_step, ResolveDecision(0, d1.id, (d1.options[1],)))
        self.assertEqual(second.players[0].active.pokemon_id, d1.options[1])
        d2 = second.decision
        deck = second.players[0].deck
        allowed = sorted(uid for uid in deck if second.card_def(uid).category == "pokemon" and second.card_def(uid).name_ja != "キョウのポッポ")
        self.assertEqual((d2.kind, d2.player, d2.resume, list(d2.options)), (SEARCH_DECK, 0, "attack", allowed))
        self.assertEqual({second.cards[uid].card_id for uid in d2.options}, {RATTATA, PIKACHU})
        self.assertEqual(check_invariants(second), [])
        done = apply_kernel(second, ResolveDecision(0, d2.id, (d2.options[0],)))
        log = kinds(done, since)
        self.assertEqual(log[:5], ["attack", "return_in_play_to_deck", "promote_active", "reveal_from_deck", "shuffle"])
        self.assertEqual(log.count("shuffle"), 1)
        self.assertEqual(events(done, since, "reveal_from_deck")[0]["card"], d2.options[0])
        self.assertIn(d2.options[0], done.players[0].hand)
        self.assertNotIn("knock_out", log)
        self.assertEqual(card_count(done, 0), card_count(state, 0))

    def test_invalid_answers_are_rejected_without_change(self):
        """不正な答え（控えでないポケモン・キョウのポッポのカード・2 枚）は拒否し、状態・乱数・ログは変わらない（決定は待ったまま）。"""
        first_step = attack(self.board(), 0)
        d1 = first_step.decision
        assert_rejected(self, first_step, ResolveDecision(0, d1.id, (999,)), "INVALID_CHOICE", IllegalActionError)
        second = apply_kernel(first_step, ResolveDecision(0, d1.id, first(d1)))
        d2 = second.decision
        pidgeys = [uid for uid in second.players[0].deck if second.card_def(uid).name_ja == "キョウのポッポ"]
        self.assertEqual(len(pidgeys), 3)  # 山札の 2 枚ともどしたこのカード
        assert_rejected(self, second, ResolveDecision(0, d2.id, (pidgeys[0],)), "INVALID_CHOICE", IllegalActionError)
        assert_rejected(self, second, ResolveDecision(1, d2.id, first(d2)), "NOT_YOUR_DECISION", IllegalActionError)

    def test_no_bench_skips_replacement_and_loses_after_the_search(self):
        """控えがいなければ、かわりの対戦ポケモンは出せず（決定なし）、山札をさがして切ってから、ワザのあとの勝ち負けの判定で負ける（p.311）。"""
        state = self.board(bench=())
        after = attack(state, 0)
        self.assertEqual(after.decision.kind, SEARCH_DECK)
        self.assertEqual(check_invariants(after), [])
        done = apply_kernel(after, ResolveDecision(0, after.decision.id, first(after.decision)))
        self.assertEqual(done.result.winner, 1)
        self.assertEqual(kinds(done, len(state.log))[-3:], ["reveal_from_deck", "shuffle", "game_end"])

    def test_no_candidates_shuffles_once_without_a_decision(self):
        """山札に選べるポケモンがなければ（キョウのポッポとエネルギーだけ）、加えずに切る（ログ reveal_from_deck_none。p.309）。"""
        state = self.board(deck=(KOGAS_PIDGEY, GRASS, GRASS))
        after = attack(state, 0, answers=[first])
        log = kinds(after, len(state.log))
        self.assertEqual(log[:5], ["attack", "return_in_play_to_deck", "promote_active", "reveal_from_deck_none", "shuffle"])

    def test_save_and_restore_at_each_decision(self):
        """決定を待つ状態を書き出し・pickle でもどしてから答えても、同じ結果（決定の続きは状態だけで決まる）。"""
        first_step = attack(self.board(), 0)
        for state in (first_step, apply_kernel(first_step, ResolveDecision(0, first_step.decision.id, first(first_step.decision)))):
            with self.subTest(kind=state.decision.kind):
                restored = pickle.loads(pickle.dumps(state))
                self.assertEqual(full(restored), full(state))
                a = play(state, ResolveDecision(0, state.decision.id, first(state.decision)), [first] if state.decision.kind == SELECT_POKEMON else [])
                b = play(restored, ResolveDecision(0, restored.decision.id, first(restored.decision)),
                         [first] if restored.decision.kind == SELECT_POKEMON else [])
                self.assertEqual(snapshot(a), snapshot(b))


class CopyTest(unittest.TestCase):
    """相手のワザを自分のワザとして使う効果（ピクシー・ピッピの「ゆびをふる」・カスミのコダックの「ちょうのうりょく」）での v0.38 のワザ。"""

    def copier(self, card, target, *, bench=(RATTATA,), deck=None, opponent_bench=(RATTATA,)):
        energy = {CLEFABLE: (PSYCHIC,), CLEFAIRY: (PSYCHIC,) * 3, MISTYS_PSYDUCK: (PSYCHIC,)}[card]
        return board(mon(card, energy), mon(target, ()), bench=bench, deck=deck, opponent_bench=opponent_bench)

    def test_stretch_kick_without_bench_by_clause(self):
        """のびるキックの使うための条件（相手に控えがいない）は、ピクシー（ほかの条件がたりなければ使えない）・ピッピ（説明にしたがう）では選べず（ILLEGAL）、
        カスミのコダック（条件を書かない）では選べるが選ぶと HC9。"""
        for card, index, expected in ((CLEFABLE, 0, "illegal"), (CLEFAIRY, 1, "illegal")):
            with self.subTest(card=card):
                state = attack(self.copier(card, HITMONLEE, opponent_bench=()), index)
                self.assertEqual(state.decision.kind, SELECT_ATTACK)
                self.assertNotIn(0, state.decision.options)
        psyduck = attack(self.copier(MISTYS_PSYDUCK, HITMONLEE, opponent_bench=()), 0, H, H, H)
        self.assertIn(0, psyduck.decision.context_value("unresolved_choices"))

    def test_messenger_copied_by_an_evolved_copier_returns_the_whole_stack(self):
        """ピクシー（ピッピから進化）がでんれいを使うと、重なったカード（ピッピ・ピクシー）とついているカードを山札にもどし（v0.36 の RD2）、そのあとさがす
        ポケモンにピッピ・ピクシーを選べる（名前が「キョウのポッポ」でない）。"""
        state = self.copier(CLEFABLE, KOGAS_PIDGEY_40, deck=(GRASS,))
        clefable = state.players[0].active
        after = attack(state, 0, answers=[(0,), first])
        returned = events(after, len(state.log), "return_in_play_to_deck")[0]
        self.assertEqual(set(returned["evolution_stack"]) | {returned["pokemon"]}, set(clefable.cards()))
        options = {after.cards[uid].card_id for uid in after.decision.options}
        self.assertEqual(options, {CLEFAIRY, CLEFABLE})
        done = apply_kernel(after, ResolveDecision(0, after.decision.id, first(after.decision)))
        log = kinds(done, len(state.log))
        start = log.index("promote_active")
        self.assertEqual(log[start:start + 3], ["promote_active", "reveal_from_deck", "shuffle"])

    def test_vanish_copied_by_an_evolved_copier(self):
        """ピクシーがいなくなるを使うと、重なったカードはポケモン自身（「このカード」）として山札に、ついているエネルギーはトラッシュに（v0.36 の RD2 と同じ読み方）。"""
        state = self.copier(CLEFABLE, ROCKET_ABRA)
        clefable = state.players[0].active
        after = attack(state, 0, answers=[(0,)])
        since = len(state.log)
        self.assertEqual(events(after, since, "discard_attached_cards")[0]["energy"], tuple(clefable.energy))
        self.assertEqual(set(events(after, since, "return_in_play_to_deck")[0]["cards"]), set(clefable.cards()))

    def test_ram_and_blizzard_copied(self):
        """げきとつ・ふぶきも、まねたポケモンのワザとして処理する（自分へのダメージ・自分の控えは、まねたポケモンの側）。"""
        ram = attack(self.copier(CLEFABLE, RHYDON, opponent_bench=()), 0, answers=[(1,)])
        self.assertEqual(ram.players[0].active.damage, 20)
        blizzard_state = self.copier(CLEFABLE, ARTICUNO, bench=(PIKACHU,))
        blizzard = attack(blizzard_state, 0, T, answers=[(1,)])
        self.assertEqual(list(bench_damage(blizzard, len(blizzard_state.log), "self_bench")), [pid_of(blizzard, 0, PIKACHU)])


class IntegrityTest(unittest.TestCase):
    """不変条件・書き出し・拒否で状態が変わらないこと・渡した状態を変えないこと。"""

    CASES = (
        (mon(ARTICUNO), 1, (H,), ()), (mon(HITMONLEE), 0, (), (first,)), (mon(ERIKAS_TANGELA), 1, (), (first,)), (mon(BROCKS_VULPIX_50), 1, (), (first,)),
        (mon(BROCKS_GOLBAT), 1, (), ()), (mon(ARBOK), 0, (H,), (first,)), (mon(RHYDON), 1, (), (first,)), (mon(BLAINES_PONYTA), 0, (H,), (first,)),
        (mon(BLAINES_RAPIDASH), 1, (H,), ()), (mon(KOGAS_PIDGEOTTO), 1, (H,), ()), (mon(KOGAS_WEEDLE), 1, (T,), ()), (mon(GIOVANNIS_NIDORINA), 0, (H,), ()),
        (mon(SABRINAS_PORYGON), 1, (), ()), (mon(ROCKET_ABRA), 0, (), (first,)), (mon(KOGAS_PIDGEY_40), 0, (), (first, first)),
    )

    def test_every_step_keeps_invariants_and_does_not_mutate_the_input(self):
        """どのワザも、途中の決定ごとに不変条件が通り、書き出し（形式 10）と pickle で同じ状態にもどる。``apply_command`` は渡した状態を変えない。"""
        for active, index, sides, answers in self.CASES:
            with self.subTest(card=active["card"], index=index):
                state = board(active, opponent_bench=(RATTATA, PIKACHU), deck=(RATTATA, PIKACHU, GRASS))
                before = copy.deepcopy(full(state))
                current = apply_kernel(with_coin_results(state, *sides), UseAttack(0, index))
                self.assertEqual(full(state), before)
                for answer in answers:
                    self.assertEqual(check_invariants(current), [])
                    self.assertEqual(full(pickle.loads(pickle.dumps(current))), full(current))
                    d = current.decision
                    current = apply_kernel(current, ResolveDecision(d.player, d.id, answer(d)))
                self.assertEqual(check_invariants(current), [])
                self.assertIsNone(current.decision if current.decision is None or current.decision.resume != "attack" else "attack decision left")

    def test_rejections_keep_the_state(self):
        """拒否（使うための条件・GK1・HC3）で状態・乱数・ログが変わらない。"""
        assert_rejected(self, board(mon(HITMONLEE), opponent_bench=()), UseAttack(0, 0), "NO_OPPONENT_BENCH", IllegalActionError)
        assert_rejected(self, board(mon(RHYDON), mon(MACHAMP, (FIGHTING,))), UseAttack(0, 1), "UNRESOLVED_DAMAGE_TRIGGER_TIMING", UnsupportedError)


class PreflightParityTest(unittest.TestCase):
    """先読みの方法（derived・derived_full・legacy）によらず、同じコインの結果で同じ結果になる（v0.38 の型はどれも ``VERIFIED`` に入れていないので、legacy も
    すべての結果を試す方法）。同じコインに対応する結果の組（ふみあらすの追加のダメージと控えへのダメージ・こうそくひこうの追加のダメージとバリアー）を、
    先読みも 1 枚のコインとして扱う。"""

    def test_same_result_in_every_mode(self):
        for active, index, sides, answers in IntegrityTest.CASES:
            with self.subTest(card=active["card"], index=index):
                state = board(active, mon(MACHAMP, (FIGHTING,), sleep=True), opponent_bench=(RATTATA, PIKACHU), deck=(RATTATA, PIKACHU, GRASS))
                results = set()
                for mode in PREFLIGHT_MODES:
                    done = play(with_coin_results(state, *sides), UseAttack(0, index), answers, mode=mode)
                    results.add(repr(snapshot(done)))
                self.assertEqual(len(results), 1)

    def test_coin_count_matches_the_text(self):
        """要素ごとにコインを投げ直さない: ふぶき・ふみあらす・こうそくひこう・きけんなはり・どくばりタックル・いかくこうげき・けりにげのコインは 1 枚。"""
        for active, index, sides, answers in IntegrityTest.CASES:
            if not sides:
                continue
            with self.subTest(card=active["card"]):
                state = board(active, opponent_bench=(RATTATA, PIKACHU))
                done = play(with_coin_results(state, *sides), UseAttack(0, index), answers)
                self.assertEqual(len([e for e in events(done, len(state.log), "coin_flip") if e["source"] == "attack"]), 1)


class DocumentTest(unittest.TestCase):
    def test_document_records_the_decisions(self):
        """文書に、カードごとの結果・GK1 の根拠と影響の範囲・のびるキックとのびるつるの違い・ついているカードの行き先・でんれいの順番を書いた。"""
        text = DOC.read_text(encoding="utf-8")
        for needle in ("GK1", "UNRESOLVED_DAMAGE_TRIGGER_TIMING", "NO_OPPONENT_BENCH", "のびるつる", "discard_attached_cards", "reveal_from_deck_none",
                       "CR-COUNTERATTACK-TIMING", "RD2"):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)
        self.assertTrue(re.search(r"pcg-search\.com", text))


if __name__ == "__main__":
    unittest.main()
