"""v0.40: 場の数・条件付きの効果・入れ替え・カードの移動を中心とする 15 枚（docs/count-condition-switch-return-v0.40.md）。

カードの登録と記録（``CardDataTest``）、説明の文面の受け付けと拒否（``TextTest``）、進化（``EvolutionTest``）、山札から好きなだけ出して場の数でダメージ
（``GroupAttackTest``）、お互いの場の名前の合うポケモンの数とそれぞれへのダメージ（``ExplosionTest``）、相手が投げるコインの「うら」の数（``OpponentCoinsTest``）、
ダメージカウンターが使うための条件（``CountersConditionTest``）、相手にカウンターがのっていれば追加（``HornDrillTest``）、条件つきでワザを使えなくする持続する効果
（``IntimidateTest``）、コインで失敗しベンチでダメージが決まる（``LoveLariatTest``）、入れ替えてからダメージ（``DragOutTest``）、相手を山札にもどす
（``FlingTest``）、コインがすべて「おもて」で追加（``StingTest``）、山札を切る（``ShuffleTest``）、自分がこんらん（``RampageTest``）、まねるワザ（``CopyTest``）、
不変条件・書き出し・保存と再開・拒否で状態が変わらない（``IntegrityTest``）、先読みの方法ごとの一致（``PreflightParityTest``）に分けた。

根拠は kyuura データの採用（kyuura の印刷の文面。``card_sources.json``）と、既存の記録の再利用（p.309 のワザの手順と「処理の対象がない」・p.310 の進化と
「別のポケモン」・p.311 と p.322 のベンチにもどる・p.320 の要素の順番とダメージの (1)〜(4)・p.321 のダメージの計算の段階・p.323 のワザの失敗・pp.323〜325 の
きぜつ・サイド・バトル場に出す順番・v0.31 のかどわかす（入れ替えは相手の対戦ポケモンへの効果）・v0.36 の自分を山札にもどす処理・v0.37 の JS1・v0.4b の
「ダメージを受けない」相手のコイン・v0.9 の T4・T27）。ガイドブックは読んでいない。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import unittest
from typing import ClassVar

from kyuura_engine import (
    EngineError,
    EvolvePokemon,
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UnsupportedError,
    UseAttack,
    check_invariants,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, read_extract
from kyuura_engine.decisions import BENCH_FROM_DECK, FORCED_SWITCH, PROMOTE_ACTIVE, SELECT_ATTACK, TAKE_PRIZE
from kyuura_engine.persistent import cannot_attack_while_source_active
from kyuura_engine.resolution import PREFLIGHT_MODES, programs, v013_checks
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.serialize import state_to_dict
from kyuura_engine.state import PERSISTENT_EFFECT_TYPES, CannotAttackWhileSourceActive
from scripts import check_card_sources as cs
from scripts.extract_kyuura_cards import KYUURA_COMMIT
from tests.helpers import (
    ATTACK_TYPES_SINCE_V0_17,
    BROCKS_MANKEY,
    BULBASAUR,
    CATERPIE,
    CLEFABLE,
    CLEFAIRY,
    DARK_HYPNO,
    DARK_MACHAMP,
    DARK_MACHOKE,
    DARK_WEEZING,
    DROWZEE,
    ERIKAS_BELLSPROUT,
    ERIKAS_WEEPINBELL,
    FIGHTING,
    FIRE,
    FOSSIL_WEEZING,
    GASTLY,
    GIOVANNIS_NIDOKING,
    GIOVANNIS_NIDOQUEEN,
    GIOVANNIS_NIDORAN_F,
    GIOVANNIS_NIDORAN_M,
    GIOVANNIS_NIDORINA,
    GIOVANNIS_NIDORINO,
    GRASS,
    GUST,
    HAUNTER,
    HITMONCHAN,
    KOFFING,
    KOGAS_GOLBAT,
    KOGAS_KOFFING,
    KOGAS_WEEZING,
    KOGAS_ZUBAT,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MANKEY,
    METAPOD,
    MEWTWO,
    MISTYS_HORSEA,
    MISTYS_PSYDUCK,
    MISTYS_SEADRA,
    NIDOKING,
    NIDORAN_M,
    NIDORINO,
    PLUSPOWER,
    PRIMEAPE,
    PSYCHIC,
    RATTATA,
    ROCKET_KOFFING,
    ROCKET_MACHOP,
    SABRINAS_DROWZEE,
    V0_40_POKEMON,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.test_barrier_resume_coin_bonus_v0_34 import assert_stops, events, first, full, play, with_barrier

ROOT = pathlib.Path(__file__).resolve().parent.parent
TURN = 7
DOC = ROOT / "docs" / "count-condition-switch-return-v0.40.md"
F, W, G, P = FIGHTING, WATER, GRASS, PSYCHIC
BELOW = {KOGAS_GOLBAT: KOGAS_ZUBAT, DARK_WEEZING: KOFFING, DARK_HYPNO: DROWZEE, GIOVANNIS_NIDORINO: GIOVANNIS_NIDORAN_M,
         GIOVANNIS_NIDOKING: [GIOVANNIS_NIDORAN_M, GIOVANNIS_NIDORINO], GIOVANNIS_NIDOQUEEN: [GIOVANNIS_NIDORAN_F, GIOVANNIS_NIDORINA],
         DARK_MACHOKE: MACHOP, DARK_MACHAMP: [MACHOP, DARK_MACHOKE], ERIKAS_WEEPINBELL: ERIKAS_BELLSPROUT, MISTYS_SEADRA: MISTYS_HORSEA,
         PRIMEAPE: MANKEY, HAUNTER: GASTLY, MACHAMP: [MACHOP, MACHOKE], METAPOD: CATERPIE, CLEFABLE: CLEFAIRY, GIOVANNIS_NIDORINA: GIOVANNIS_NIDORAN_F,
         FOSSIL_WEEZING: KOFFING, NIDOKING: [NIDORAN_M, NIDORINO]}
# ワザを使うのに足りるエネルギー（無色は別のタイプで払う）
ENERGY = {KOGAS_ZUBAT: (G, G), KOGAS_GOLBAT: (G, G, G), DARK_WEEZING: (G, G, G), DARK_HYPNO: (P, P, P), GIOVANNIS_NIDORAN_M: (G,),
          GIOVANNIS_NIDORINO: (G, G, G), GIOVANNIS_NIDOKING: (G, G, G, G), GIOVANNIS_NIDOQUEEN: (G, G, G, G), DARK_MACHOKE: (F, F, F),
          DARK_MACHAMP: (F, F, F, F), ERIKAS_WEEPINBELL: (G, G), MISTYS_SEADRA: (W, W, W), BROCKS_MANKEY: (F, F), MANKEY: (F, F), PRIMEAPE: (F, F, F)}
# 登録の実装の型と値（カード id, ワザの位置）
EXPECTED = {
    (KOGAS_ZUBAT, 0): (E.GroupAttackFromDeck, {"names": ("キョウのズバット",), "per": 10}),
    (KOGAS_GOLBAT, 0): (E.DamageOnly, {}),
    (KOGAS_GOLBAT, 1): (E.ConfuseOnHeads, {}),
    (DARK_WEEZING, 0): (E.NamedPokemonExplosion, {"names": ("ドガース", "マタドガス", "わるいマタドガス"), "per": 20, "each": 20}),
    (DARK_WEEZING, 1): (E.DamageThenPoisonOrParalyze, {}),
    (DARK_HYPNO, 0): (E.DamageOnly, {}),
    (DARK_HYPNO, 1): (E.OpponentFlipsTailsDamage, {"per": 20}),
    (GIOVANNIS_NIDORAN_M, 0): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 10}),
    (GIOVANNIS_NIDORAN_M, 1): (E.DamageRequiringOwnCounters, {"minimum": 2}),
    (GIOVANNIS_NIDORINO, 0): (E.DamagePlusIfDefenderDamaged, {"bonus": 20}),
    (GIOVANNIS_NIDOKING, 0): (E.AttackLockWhileSourceActive, {"max_hp": 50}),
    (GIOVANNIS_NIDOKING, 1): (E.CoinBonusDamage, {"bonus": 30}),
    (GIOVANNIS_NIDOQUEEN, 0): (E.DamageOnly, {}),
    (GIOVANNIS_NIDOQUEEN, 1): (E.FailOnTailsAmountIfBenchNamed, {"names": ("サカキのニドキング",), "amount": 100}),
    (DARK_MACHOKE, 0): (E.SwitchOpponentThenDamage, {}),
    (DARK_MACHOKE, 1): (E.DamageAndForceSwitch, {}),
    (DARK_MACHAMP, 0): (E.DamageOnly, {}),
    (DARK_MACHAMP, 1): (E.ReturnOpponentActiveToDeck, {}),
    (ERIKAS_WEEPINBELL, 0): (E.DamageOnly, {}),
    (ERIKAS_WEEPINBELL, 1): (E.SwitchOpponentThenDamage, {}),
    (MISTYS_SEADRA, 0): (E.DamageOnly, {}),
    (MISTYS_SEADRA, 1): (E.CoinsAllHeadsBonusDamage, {"coins": 2, "bonus": 60}),
    (BROCKS_MANKEY, 0): (E.ShuffleDeckAttack, {"own": True}),
    (BROCKS_MANKEY, 1): (E.DamageReducedByOwnCounters, {"reduction_per_counter": 10}),
    (MANKEY, 0): (E.ShuffleDeckAttack, {"own": False}),
    (MANKEY, 1): (E.CoinBonusDamage, {"bonus": 20}),
    (PRIMEAPE, 0): (E.CoinFlipDamage, {"coins": 3, "damage_per_heads": 20}),
    (PRIMEAPE, 1): (E.DamageThenSelfConfuseOnTails, {}),
}
NEW_TYPES = {E.GroupAttackFromDeck, E.NamedPokemonExplosion, E.OpponentFlipsTailsDamage, E.DamageRequiringOwnCounters, E.DamagePlusIfDefenderDamaged,
             E.AttackLockWhileSourceActive, E.FailOnTailsAmountIfBenchNamed, E.SwitchOpponentThenDamage, E.ReturnOpponentActiveToDeck,
             E.CoinsAllHeadsBonusDamage, E.ShuffleDeckAttack, E.DamageThenSelfConfuseOnTails}
# pcg-search.com の対象の版（サイトの一覧の番号。kyuura の id の番号とは違うことがある）と、違いのあった欄
EDITIONS = {KOGAS_ZUBAT: "010/098", KOGAS_GOLBAT: "011/098", DARK_WEEZING: "011/065", DARK_HYPNO: "037/065", GIOVANNIS_NIDORAN_M: "021/098",
            GIOVANNIS_NIDORINO: "022/098", GIOVANNIS_NIDOKING: "023/098", GIOVANNIS_NIDOQUEEN: "020/098", DARK_MACHOKE: "043/065",
            DARK_MACHAMP: "044/065", ERIKAS_WEEPINBELL: "012/096", MISTYS_SEADRA: "031/096", BROCKS_MANKEY: "047/096", MANKEY: "040/065",
            PRIMEAPE: "029/048"}
DIFFERENCES = {KOGAS_ZUBAT: ["pokemon.attacks[0].text.ja"], DARK_WEEZING: ["pokemon.attacks[0].text.ja"], DARK_HYPNO: ["pokemon.attacks[1].text.ja"],
               GIOVANNIS_NIDORAN_M: ["pokemon.attacks[0].text.ja"], GIOVANNIS_NIDORINO: ["pokemon.attacks[0].text.ja"],
               GIOVANNIS_NIDOQUEEN: ["pokemon.attacks[1].damage"], DARK_MACHOKE: ["pokemon.attacks[0].text.ja", "pokemon.attacks[1].text.ja"]}


def mon(card, energy=None, **extra):
    spec = {"card": card, "energy": list(ENERGY.get(card, ()) if energy is None else energy), **extra}
    if BELOW.get(card) is not None and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), deck=None, hand=(), opponent_hand=(), turn=TURN):
    def spec(b):
        return mon(b, ()) if isinstance(b, str) and b in BELOW else b

    me = {"active": active, "bench": [spec(b) for b in bench], "hand": list(hand)}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent or mon(HITMONCHAN, (F, F)), "bench": [spec(b) for b in opponent_bench], "hand": list(opponent_hand)}
    return build_test_state([me, them], turn_number=turn)


def snapshot(state):
    return full(state), rng_fingerprint(state.rng), [dict(e) for e in state.log]


def attack(state, index, *sides, answers=(), player=0, mode="derived"):
    return play(with_coin_results(state, *sides), UseAttack(player, index), answers, mode=mode)


def pid_of(state, player, card):
    """プレイヤー ``player`` の場の ``card``（カード id）のポケモンの番号（最初の 1 匹）。"""
    return next(p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card)


def card_of(state, player, card, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card)


def opponent_damage(state, since):
    return [e["amount"] for e in events(state, since, "damage") if e.get("target") is None and not e.get("retaliation")]


def damage_of(state, since, target):
    return {e.get("pokemon_id"): e["amount"] for e in events(state, since, "damage") if e.get("target") == target and not e.get("retaliation")}


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


def answer(state, choices):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)))


class CardDataTest(unittest.TestCase):
    """15 枚の登録・写し・採用の記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_fifteen_requested_cards(self):
        """対象は依頼の 15 枚（ほかの候補に広げていない）。写しの組 pool_v0_40 は 15 枚で、どれも対戦に使える。名前の似た別のカード（ズバット・ゴルバット・
        マタドガス・キョウのマタドガス・スリーパー（写しにない）・ニドラン♂・ニドリーノ・ニドキング・ニドクイン・ゴーリキー・カイリキー・ウツドン・タケシのマンキーと
        マンキー）とは別の名前・別の id。"""
        self.assertEqual(len(V0_40_POKEMON), 15)
        self.assertEqual(list(read_extract()["pool_v0_40"]), list(V0_40_POKEMON))
        for card in V0_40_POKEMON:
            with self.subTest(card=card):
                self.assertTrue(self.pool.is_playable(card))
                self.assertEqual(self.pool.get(card).powers, ())
        for ours, other in ((DARK_WEEZING, FOSSIL_WEEZING), (DARK_WEEZING, KOGAS_WEEZING), (GIOVANNIS_NIDORAN_M, NIDORAN_M),
                            (GIOVANNIS_NIDORINO, NIDORINO), (GIOVANNIS_NIDOKING, NIDOKING), (DARK_MACHOKE, MACHOKE), (DARK_MACHAMP, MACHAMP),
                            (BROCKS_MANKEY, MANKEY), (DARK_HYPNO, SABRINAS_DROWZEE)):
            with self.subTest(card=ours, other=other):
                self.assertNotEqual(self.pool.get(ours).name_ja, self.pool.get(other).name_ja)

    def test_every_attack_is_registered_with_the_expected_implementation(self):
        """28 のワザがどれも登録され、型と値が説明に合う。説明文のあるワザは、写しの文面（照合用）と処理に使う文面（kyuura の印刷の文面）が同じ。"""
        attacks = [(card, a.index) for card in V0_40_POKEMON for a in self.pool.get(card).attacks]
        self.assertEqual(sorted(attacks), sorted(EXPECTED))
        self.assertEqual(len(attacks), 28)
        for (card, index), (cls, values) in EXPECTED.items():
            with self.subTest(card=card, index=index):
                entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
                self.assertIs(type(entry.effect), cls)
                for name, value in values.items():
                    self.assertEqual(getattr(entry.effect, name), value)
                printed = self.pool.get(card).attacks[index]
                self.assertEqual(entry.name_ja, printed.name_ja)
                self.assertEqual(entry.text_ja, printed.text_ja)
                if printed.text_ja:
                    self.assertEqual(entry.play_text_ja, printed.text_ja)
                self.assertEqual(entry.effect.check(printed), [])

    def test_new_types_are_kernel_programs_outside_the_v013_contract(self):
        """v0.40 の型は解決の基盤の要素の並び（``programs.BUILDERS``）で処理し、v0.13 の約束（``resolve``・``resume``）を上書きしない。``v013_checks.VERIFIED`` に
        入れない（tests/helpers.py の ``ATTACK_TYPES_SINCE_V0_17`` に加えた）。"""
        self.assertEqual(len(NEW_TYPES), 12)
        for cls in NEW_TYPES:
            with self.subTest(cls=cls.__name__):
                self.assertIn(cls, programs.BUILDERS)
                self.assertIn(cls, ATTACK_TYPES_SINCE_V0_17)
                self.assertNotIn(cls, v013_checks.VERIFIED)
                self.assertIs(cls.resolve, E.AttackEffect.resolve)
                self.assertIs(cls.resume, E.AttackEffect.resume)

    def test_adoption_records_and_external_checks(self):
        """15 枚はどれも kyuura データの採用の記録（写しの元のコミット・説明文のあるワザの処理に使う文面の根拠）を持ち、pcg-search.com の同じ版のページと照合した。
        違いは 7 枚の 8 欄で、どれも処理に影響しない（書き方・記号の違いと、サカキのニドクインのラブラリアットのダメージの表示の「+」）。研究の基準のコミットで
        15 枚を指す kyuura の記録はない（わるいカイリキーは CC-PMCG1-057-P43 の not_confused_with に名前が出るだけ）。過去の原典照合の記録には入れない。"""
        sources = cs.load_sources()["cards"]
        verification = json.loads((ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8"))["cards"]
        links = cs.load_links()["latest_descriptions"]["adopted_printed_text"]
        for card in V0_40_POKEMON:
            with self.subTest(card=card):
                record = sources[card]
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"]),
                                 ("kyuura_data", "adopted", KYUURA_COMMIT, []))
                with_text = {f"attack/{a.index}" for a in self.pool.get(card).attacks if a.text_ja}
                self.assertEqual(set(record["play_text"]), with_text)
                self.assertTrue(all(v == "kyuura_printed_text" for v in record["play_text"].values()))
                self.assertTrue(with_text <= {k.split("/", 1)[1] for k in links if k.startswith(card + "/")})
                [check] = record["external_checks"]
                self.assertEqual(check["site"], "pcg-search.com")
                self.assertEqual(check["edition"]["list_number"], EDITIONS[card])
                if card in DIFFERENCES:
                    self.assertEqual(check["result"], "differences")
                    self.assertEqual([d["field"] for d in check["differences"]], DIFFERENCES[card])
                    self.assertFalse(any(d["affects_behavior"] for d in check["differences"]))
                else:
                    self.assertEqual((check["result"], check["differences"]), ("match", []))
                self.assertNotIn(card, verification)

    def test_no_card_specific_branch_in_the_engine(self):
        """engine.py・resolution/ に v0.40 のカード id での分岐を加えていない（効果の型と要素の項目で表す）。"""
        for path in [ROOT / "kyuura_engine" / "engine.py", *(ROOT / "kyuura_engine" / "resolution").glob("*.py")]:
            text = path.read_text(encoding="utf-8")
            for card in V0_40_POKEMON:
                with self.subTest(path=path.name, card=card):
                    self.assertNotIn(card, text)

    def test_sg1_is_the_only_new_stop_code_and_existing_questions_are_reused(self):
        """SG1（すごむの効果を与えたポケモンが同じ番にバトル場にもどる）は新しい停止コード 1 つで、突風の選択で止める（宣言の前の問い ``QUESTIONS`` には入れない）。
        研究の対応表では kyuura の未解決の一覧にない（not_in_kyuura）。みんなでばくはつの控えへのダメージは v0.37 の JS1、つまみだすの同時のきぜつは v0.36 の RD9、
        ベンチをあやつる・きぜつばり・ラブラリアットの「ダメージを受けない」相手は v0.4b の問いで、新しい問いを加えていない。"""
        codes = {q.code for q in QUESTIONS.values()}
        self.assertNotIn("UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED", codes)
        for code in ("UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE", "UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT", "UNRESOLVED_PREVENTED_COIN_DAMAGE"):
            self.assertIn(code, codes)
        entry = cs.load_links()["stop_codes"]["UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED"]
        self.assertEqual((entry["kyuura_disposition"], entry["kyuura_issue"]), ("not_in_kyuura", None))
        self.assertEqual(entry["engine_rulings"][0]["ruling_id"], "SG1")
        self.assertIn(CannotAttackWhileSourceActive, PERSISTENT_EFFECT_TYPES)


class TextTest(unittest.TestCase):
    """型の ``check`` は、登録したワザの印刷の文面と同じ書き方だけを受け付ける（似たワザの文面を推測で同じ型にしない）。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def printed(self, card, index):
        return self.pool.get(card).attacks[index]

    def test_both_paren_styles_are_the_same_switch_then_damage(self):
        """ひきずりだす（全角のかっこ）・さそってとかす（半角のかっこ）は同じ型。ダメージを与えてから入れ替える文面（なぐりとばす）は受け付けない。"""
        effect = E.SwitchOpponentThenDamage()
        self.assertEqual(effect.check(self.printed(DARK_MACHOKE, 0)), [])
        self.assertEqual(effect.check(self.printed(ERIKAS_WEEPINBELL, 1)), [])
        self.assertNotEqual(effect.check(self.printed(DARK_MACHOKE, 1)), [])

    def test_other_values_and_texts_are_rejected(self):
        """値と文面の組が違う登録は受け付けない（名前・数・自分か相手か・最大 HP）。"""
        bad = [
            (E.GroupAttackFromDeck(names=("ズバット",), per=10), KOGAS_ZUBAT, 0),
            (E.GroupAttackFromDeck(names=("キョウのズバット",), per=20), KOGAS_ZUBAT, 0),
            (E.NamedPokemonExplosion(names=("ドガース", "マタドガス"), per=20, each=20), DARK_WEEZING, 0),
            (E.NamedPokemonExplosion(names=("ドガース", "マタドガス", "わるいマタドガス"), per=20, each=10), DARK_WEEZING, 0),
            (E.OpponentFlipsTailsDamage(per=10), DARK_HYPNO, 1),
            (E.DamageRequiringOwnCounters(minimum=3), GIOVANNIS_NIDORAN_M, 1),
            (E.DamagePlusIfDefenderDamaged(bonus=30), GIOVANNIS_NIDORINO, 0),
            (E.AttackLockWhileSourceActive(max_hp=60), GIOVANNIS_NIDOKING, 0),
            (E.FailOnTailsAmountIfBenchNamed(names=("ニドキング",), amount=100), GIOVANNIS_NIDOQUEEN, 1),
            (E.CoinsAllHeadsBonusDamage(coins=3, bonus=60), MISTYS_SEADRA, 1),
            (E.ShuffleDeckAttack(own=False), BROCKS_MANKEY, 0),
            (E.ShuffleDeckAttack(own=True), MANKEY, 0),
            (E.DamageThenSelfConfuseOnTails(), GIOVANNIS_NIDOKING, 1),
            (E.ReturnOpponentActiveToDeck(), DARK_MACHAMP, 0),
            (E.CoinBonusDamage(bonus=30), MANKEY, 1),
        ]
        for effect, card, index in bad:
            with self.subTest(effect=effect, card=card, index=index):
                self.assertNotEqual(effect.check(self.printed(card, index)), [])
        for bad_value in (lambda: E.GroupAttackFromDeck(names=(), per=10), lambda: E.CoinsAllHeadsBonusDamage(coins=1, bonus=60),
                          lambda: E.DamageRequiringOwnCounters(minimum=0), lambda: E.AttackLockWhileSourceActive(max_hp=0)):
            with self.assertRaises(ValueError):
                bad_value()


class EvolutionTest(unittest.TestCase):
    """進化先 11 枚（1 進化 8 枚・2 進化 3 枚）は、通常の進化の操作（``EvolvePokemon``）で、進化元の名前（完全一致）のポケモンから進化する。収録の弾の違いは
    進化の条件にしない。"""

    PAIRS = ((KOGAS_GOLBAT, KOGAS_ZUBAT), (DARK_WEEZING, KOFFING), (DARK_WEEZING, ROCKET_KOFFING), (DARK_HYPNO, DROWZEE),
             (GIOVANNIS_NIDORINO, GIOVANNIS_NIDORAN_M), (DARK_MACHOKE, MACHOP), (DARK_MACHOKE, ROCKET_MACHOP),
             (ERIKAS_WEEPINBELL, ERIKAS_BELLSPROUT), (MISTYS_SEADRA, MISTYS_HORSEA), (PRIMEAPE, MANKEY))
    STAGE2 = ((GIOVANNIS_NIDOKING, [GIOVANNIS_NIDORAN_M], GIOVANNIS_NIDORINO), (GIOVANNIS_NIDOQUEEN, [GIOVANNIS_NIDORAN_F], GIOVANNIS_NIDORINA),
              (DARK_MACHAMP, [MACHOP], DARK_MACHOKE))

    def evolve(self, base, card, below=None):
        spec = {"card": base, "energy": []}
        if below:
            spec["evolved_from"] = below
            spec["evolved_turn"] = 3
        state = board(spec, hand=[card])
        return apply_kernel(state, EvolvePokemon(0, card_of(state, 0, card), state.players[0].active.pokemon_id))

    def test_evolves_from_every_card_with_the_exact_name(self):
        for card, base in self.PAIRS:
            with self.subTest(card=card, base=base):
                done = self.evolve(base, card)
                self.assertEqual(done.cards[done.players[0].active.card].card_id, card)
        for card, below, base in self.STAGE2:
            with self.subTest(card=card):
                done = self.evolve(base, card, below)
                self.assertEqual(done.cards[done.players[0].active.card].card_id, card)
                self.assertEqual(len(done.players[0].active.evolution_stack), 2)

    def test_names_that_only_look_alike_are_rejected(self):
        """ナツメのスリープからわるいスリーパー・タケシのマンキーからオコリザル・ニドラン♂（第1弾）からサカキのニドリーノ・キョウのドガースからわるいマタドガスへは
        進化できない（名前が違う）。"""
        for card, base in ((DARK_HYPNO, SABRINAS_DROWZEE), (PRIMEAPE, BROCKS_MANKEY), (GIOVANNIS_NIDORINO, NIDORAN_M), (DARK_WEEZING, KOGAS_KOFFING)):
            with self.subTest(card=card, base=base):
                state = board({"card": base, "energy": []}, hand=[card])
                assert_rejected(self, state, EvolvePokemon(0, card_of(state, 0, card), state.players[0].active.pokemon_id),
                                "EVOLUTION_NAME_MISMATCH", IllegalActionError)


class GroupAttackTest(unittest.TestCase):
    """むれでおそう（``GroupAttackFromDeck``）: のぞむなら山札から「キョウのズバット」を好きなだけベンチに出し、出したら 1 回切る → 自分の場の数 × 10。"""

    def state(self, *, bench=(RATTATA,), deck=(KOGAS_ZUBAT, FIRE, KOGAS_ZUBAT, FIRE, KOGAS_ZUBAT)):
        return board(mon(KOGAS_ZUBAT), bench=bench, deck=deck)

    def test_decision_shape(self):
        """選ぶのはワザを使ったプレイヤー。選べるものは山札の「キョウのズバット」（uid の小さい順）、選ぶ数は 0〜min(ベンチの空き, 選べるものの数)。"""
        state = self.state()
        after = attack(state, 0)
        d = after.decision
        zubats = sorted(u for u in state.players[0].deck if state.cards[u].card_id == KOGAS_ZUBAT)
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (BENCH_FROM_DECK, 0, tuple(zubats), 0, 3))
        crowded = attack(self.state(bench=(RATTATA,) * 4), 0)
        self.assertEqual(crowded.decision.max_choices, 1)  # ベンチの空きは 1

    def test_choose_all_then_one_shuffle_then_count(self):
        """3 枚を出すと、ログ ``bench_from_deck`` が 3 つ、そのあと山札を 1 回だけ切り（ログ ``shuffle`` にワザの ``effect``）、場の数 4 × 10 = 40。出した
        ポケモンの場に出た番は今の番（その番には進化できない。p.310）。"""
        state = self.state()
        since = len(state.log)
        done = play(state, UseAttack(0, 0), [lambda d: tuple(d.options)])
        kinds = [e["kind"] for e in done.log[since:]]
        self.assertEqual(kinds[:6], ["attack", "bench_from_deck", "bench_from_deck", "bench_from_deck", "shuffle", "damage"])
        shuffles = events(done, since, "shuffle")
        self.assertEqual([(e["player"], e.get("effect")) for e in shuffles[:1]], [(0, f"{KOGAS_ZUBAT}#0")])
        self.assertEqual(len([e for e in shuffles if e.get("effect")]), 1)
        self.assertEqual(opponent_damage(done, since), [40])
        placed = [p for p in done.players[0].bench if done.cards[p.card].card_id == KOGAS_ZUBAT]
        self.assertEqual([p.played_turn for p in placed], [TURN] * 3)
        self.assertEqual(card_count(done, 0), card_count(state, 0))

    def test_choose_none_or_one(self):
        """0 枚なら出さず、山札を切らず（ログ ``bench_from_deck_declined``）、ワザを使ったポケモンだけで 10。1 枚なら 20。"""
        state = self.state()
        since = len(state.log)
        none = play(state, UseAttack(0, 0), [()])
        self.assertEqual([e["kind"] for e in none.log[since:since + 3]], ["attack", "bench_from_deck_declined", "damage"])
        self.assertFalse([e for e in events(none, since, "shuffle") if e.get("effect")])
        self.assertEqual(opponent_damage(none, since), [10])
        one = play(state, UseAttack(0, 0), [first])
        self.assertEqual(opponent_damage(one, since), [20])

    def test_counts_only_the_exact_name_in_play(self):
        """数えるのは自分の場の「キョウのズバット」（名前の完全一致・いちばん上のカード）だけ。ベンチのキョウのゴルバット（進化した）・相手の場の
        キョウのズバットは数えない。"""
        state = board(mon(KOGAS_ZUBAT), mon(KOGAS_ZUBAT, ()), bench=(mon(KOGAS_ZUBAT, ()), mon(KOGAS_GOLBAT, ())), deck=(FIRE,) * 5)
        since = len(state.log)
        done = attack(state, 0)
        self.assertIsNone(done.decision if done.decision and done.decision.kind == BENCH_FROM_DECK else None)
        self.assertEqual(opponent_damage(done, since), [20])

    def test_no_decision_without_candidates_or_space(self):
        """山札に選べるものがない・ベンチに空きがないなら、決定を出さず、山札も切らない。"""
        for state in (self.state(deck=(FIRE,) * 5), self.state(bench=(RATTATA,) * 5)):
            since = len(state.log)
            done = attack(state, 0)
            self.assertNotIn("bench_from_deck", [e["kind"] for e in done.log[since:]])
            self.assertFalse([e for e in events(done, since, "shuffle") if e.get("effect")])

    def test_invalid_answers_are_rejected_and_the_decision_waits(self):
        """同じカードを 2 回・選べない数・山札にないカードは拒否（状態・乱数・ログは変わらない）。決定は待ったまま。"""
        roomy = attack(self.state(), 0)  # 空きは 4・選べるものは 3
        d = roomy.decision
        assert_rejected(self, roomy, ResolveDecision(0, d.id, (d.options[0], d.options[0])), "DUPLICATE_CHOICE", IllegalActionError)
        state = self.state(bench=(RATTATA,) * 4)  # 空きは 1
        after = attack(state, 0)
        d = after.decision
        assert_rejected(self, after, ResolveDecision(0, d.id, d.options[:2]), "INVALID_CHOICE_COUNT", IllegalActionError)
        assert_rejected(self, after, ResolveDecision(0, d.id, (after.players[0].active.card,)), "INVALID_CHOICE", IllegalActionError)
        assert_rejected(self, after, ResolveDecision(1, d.id, ()), "NOT_YOUR_DECISION", IllegalActionError)

    def test_save_and_restore_at_the_decision(self):
        """決定を待つ状態を pickle・書き出し（形式 10）で保存して再開しても、同じ結果になる。"""
        after = attack(self.state(), 0)
        restored = pickle.loads(pickle.dumps(after))
        self.assertEqual(full(restored), full(after))
        a = answer(after, after.decision.options[:2])
        b = answer(restored, restored.decision.options[:2])
        self.assertEqual(snapshot(a), snapshot(b))


class ExplosionTest(unittest.TestCase):
    """みんなでばくはつ（``NamedPokemonExplosion``）: お互いの場の「ドガース」「マタドガス」「わるいマタドガス」の数 × 20 → 名前の合うポケモンそれぞれに 20。"""

    def test_counts_both_sides_by_exact_name(self):
        """数えるのはお互いの場の名前の合うポケモン（ワザを使ったわるいマタドガス・進化したマタドガスは 1 匹）。キョウのドガースは数えない。相手の対戦ポケモンが
        名前の合わないエビワラーなら、相手が受けるのは数 × 20 の 1 回だけ。"""
        state = board(mon(DARK_WEEZING), bench=(ROCKET_KOFFING, KOGAS_KOFFING), opponent_bench=(mon(FOSSIL_WEEZING, ()), KOFFING, RATTATA))
        since = len(state.log)
        done = attack(state, 0)
        self.assertEqual(opponent_damage(done, since), [80])  # わるいマタドガス・ドガース（ロケット団）・マタドガス・ドガース（第1弾）
        weezing = done.players[0].active.pokemon_id
        self.assertEqual(damage_of(done, since, "self"), {weezing: 20})
        self.assertEqual(set(damage_of(done, since, "self_bench")), {pid_of(done, 0, ROCKET_KOFFING)})
        self.assertEqual(set(damage_of(done, since, "opponent_bench")), {pid_of(done, 1, FOSSIL_WEEZING), pid_of(done, 1, KOFFING)})

    def test_named_opponent_active_takes_two_damage_elements(self):
        """相手の対戦ポケモンがドガースなら、数 × 20 のあとに、もう一度 20 を受ける（ダメージの要素が 2 つ。弱点・抵抗力はどちらも計算する）。"""
        state = board(mon(DARK_WEEZING), mon(KOFFING, (G,)), bench=(), opponent_bench=(RATTATA,))
        since = len(state.log)
        done = attack(state, 0)
        self.assertEqual(opponent_damage(done, since), [40, 20])
        self.assertEqual([e["kind"] for e in done.log[since:since + 4]], ["attack", "damage", "damage", "damage"])

    def test_each_damage_element_is_calculated_separately(self):
        """相手の対戦ポケモンへの 2 つのダメージ（数 × 20 と 20）と自分への 20 は、どれも p.321 の段階で別々に計算する（ダメージの要素ごと。v0.2c・v0.2e の
        プラスパワー・ディフェンダーの最新の説明「ダメージを与えるとき」「ダメージを受けるとき」。自分へのダメージは v0.2f・v0.3d）。1 つのワザで相手の対戦ポケモンに
        ダメージの要素が 2 つあるのは、対応カードでこのワザだけ。"""
        from tests.helpers import DEFENDER

        state = board(mon(DARK_WEEZING, trainers=[(PLUSPOWER, TURN)]), mon(KOFFING, (G,), trainers=[(DEFENDER, TURN)]), bench=(), opponent_bench=(RATTATA,))
        since = len(state.log)
        done = attack(state, 0)
        self.assertEqual(opponent_damage(done, since), [40 + 10 - 20, 20 + 10 - 20])
        self.assertEqual(list(damage_of(done, since, "self").values()), [20 + 10])
        def opponent_damage_elements(key):
            effect = E.DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).effect
            builder = programs.BUILDERS.get(type(effect))
            return [] if builder is None else [e for e in builder(effect) if isinstance(e, programs.Damage) and e.target == programs.OPP]

        twice = [key for key in E.DEFAULT_EFFECTS.attack_keys() if len(opponent_damage_elements(key)) >= 2]
        self.assertEqual([str(key) for key in twice], [f"{DARK_WEEZING}#0"])

    def test_simultaneous_knock_outs_and_prizes(self):
        """ダメージをすべてのせてから、きぜつの処理（p.309）。相手の対戦ポケモンと控え、自分の控えがそろってきぜつし、お互いにサイドを取る（番のプレイヤーから）。"""
        state = board(mon(DARK_WEEZING), mon(KOFFING, (G,), damage=20), bench=(mon(ROCKET_KOFFING, (), damage=30),),
                      opponent_bench=(mon(KOFFING, (), damage=40), RATTATA))
        since = len(state.log)
        done = attack(state, 0)
        knocked = [done.cards[e["pokemon"]].card_id for e in events(done, since, "knock_out")]
        self.assertEqual(sorted(knocked), sorted([KOFFING, KOFFING, ROCKET_KOFFING]))
        self.assertEqual((done.decision.kind, done.decision.player), (TAKE_PRIZE, 0))

    def test_counterattack_comes_after_every_damage_element(self):
        """相手の対戦ポケモン（カイリキー。名前は合わない）の「はんげき」は、自分・控えへのダメージをすべてのせたあと（p.89。CR-COUNTERATTACK-TIMING）。"""
        state = board(mon(DARK_WEEZING), mon(MACHAMP, (F,)), bench=(ROCKET_KOFFING,), opponent_bench=(KOFFING,))
        since = len(state.log)
        done = attack(state, 0)
        kinds = [e["kind"] for e in done.log[since:]]
        self.assertEqual(kinds[:6], ["attack", "damage", "damage", "damage", "damage", "counterattack"])

    def test_bench_damage_is_the_js1_reading(self):
        """控えへのダメージは説明が弱点・抵抗力について書いていない（v0.37 の JS1。``BenchDamage`` の ``weakness_resistance`` が None）。相手の対戦ポケモン・自分への
        ダメージは弱点・抵抗力を計算する（英語版の文面では決めない）。"""
        program = programs.BUILDERS[E.NamedPokemonExplosion](E.DEFAULT_EFFECTS.attack_entry(DARK_WEEZING, 0).effect)
        benches = [element for element in program if isinstance(element, programs.BenchDamage)]
        self.assertEqual([(b.own, b.weakness_resistance, b.names) for b in benches],
                         [(False, None, ("ドガース", "マタドガス", "わるいマタドガス")), (True, None, ("ドガース", "マタドガス", "わるいマタドガス"))])
        self.assertTrue(all(e.weakness_resistance for e in program if isinstance(e, programs.Damage)))


class OpponentCoinsTest(unittest.TestCase):
    """ベンチをあやつる（``OpponentFlipsTailsDamage``）: 相手が相手の控えの数だけコインを投げ、「うら」の数 × 20（相手の弱点・抵抗力を計算しない）。"""

    def test_opponent_flips_and_tails_count(self):
        """コインを投げるのは相手（ログ ``coin_flip`` の ``player`` が 1）。枚数は相手の控えの数 3。「うら」2 枚で 40。相手（スリープ）の弱点の超を計算しない。"""
        state = board(mon(DARK_HYPNO), mon(DROWZEE, (P,)), opponent_bench=(RATTATA, RATTATA, RATTATA))
        since = len(state.log)
        done = attack(state, 1, T, H, T)
        flips = events(done, since, "coin_flip")
        self.assertEqual([(e["player"], e["source"], e["count"]) for e in flips], [(1, "attack", 3)] * 3)
        self.assertEqual(opponent_damage(done, since), [40])
        self.assertTrue(events(done, since, "damage")[0]["ignore_weakness_resistance"])

    def test_no_bench_no_coin_no_damage(self):
        """相手に控えがいなければ投げず、0 で「ダメージを与えなかった」（p.321 の 2 段階まで）。"""
        state = board(mon(DARK_HYPNO), opponent_bench=())
        since = len(state.log)
        done = attack(state, 1)
        self.assertEqual(events(done, since, "coin_flip"), [])
        self.assertEqual(done.players[1].active.damage, 0)

    def test_prevented_opponent_stops_only_when_coins_are_flipped(self):
        """相手が「ダメージを受けない」状態（かたまる）で控えがいれば、ダメージの量だけを決めるコインなので v0.4b の問いで止める。控えがいなければ投げないので
        止めない（無効のログ ``damage_prevented``）。"""
        guarded = mon(METAPOD, (G, G), prevent_damage=TURN - 1)
        assert_stops(self, board(mon(DARK_HYPNO), guarded, opponent_bench=(RATTATA,)), UseAttack(0, 1), "UNRESOLVED_PREVENTED_COIN_DAMAGE")
        state = board(mon(DARK_HYPNO), guarded, opponent_bench=())
        done = attack(state, 1)
        self.assertEqual(len(events(done, len(state.log), "damage_prevented")), 1)


class CountersConditionTest(unittest.TestCase):
    """いかりのいちげき（``DamageRequiringOwnCounters``）: 自分にダメージカウンターが 2 つ以上のっているときだけ使える。"""

    def test_boundary(self):
        """0・1 個は ``NOT_ENOUGH_DAMAGE_COUNTERS``（状態・乱数・ログは変わらない）。2・3 個なら 30。"""
        for damage in (0, 10):
            with self.subTest(damage=damage):
                assert_rejected(self, board(mon(GIOVANNIS_NIDORAN_M, damage=damage)), UseAttack(0, 1), "NOT_ENOUGH_DAMAGE_COUNTERS", IllegalActionError)
        for damage in (20, 30):
            with self.subTest(damage=damage):
                state = board(mon(GIOVANNIS_NIDORAN_M, damage=damage))
                self.assertEqual(opponent_damage(attack(state, 1), len(state.log)), [30])

    def test_condition_is_checked_before_the_confusion_coin(self):
        """条件はワザを使うための条件で、こんらんのコインより先に確かめる（拒否で乱数を使わない）。"""
        assert_rejected(self, board(mon(GIOVANNIS_NIDORAN_M, confusion=True)), UseAttack(0, 1), "NOT_ENOUGH_DAMAGE_COUNTERS", IllegalActionError)


class HornDrillTest(unittest.TestCase):
    """つのでえぐる（``DamagePlusIfDefenderDamaged``）: 相手（相手の対戦ポケモン）にダメージカウンターがのっていれば + 20。"""

    def test_bonus_only_when_the_defender_has_counters(self):
        for damage, expected in ((0, 20), (10, 40), (40, 40)):
            with self.subTest(damage=damage):
                state = board(mon(GIOVANNIS_NIDORINO), mon(HITMONCHAN, (F,), damage=damage))
                self.assertEqual(opponent_damage(attack(state, 0), len(state.log)), [expected])

    def test_bench_counters_do_not_count(self):
        """相手の控えのカウンターは見ない（「相手」は相手の対戦ポケモン。CD4 の「相手のポケモン」とは書き方が違う）。"""
        state = board(mon(GIOVANNIS_NIDORINO), opponent_bench=(mon(RATTATA, (), damage=10),))
        self.assertEqual(opponent_damage(attack(state, 0), len(state.log)), [20])


class IntimidateTest(unittest.TestCase):
    """すごむ（``AttackLockWhileSourceActive``・持続する効果 ``CannotAttackWhileSourceActive``）。"""

    def state(self, opponent, *, bench=(RATTATA,), opponent_bench=(RATTATA, DROWZEE), opponent_hand=(GUST, GUST)):
        return board(mon(GIOVANNIS_NIDOKING), opponent, bench=bench, opponent_bench=opponent_bench, opponent_hand=opponent_hand)

    def test_max_hp_condition(self):
        """最大 HP 50 以下（ドガース 50・コラッタ 30）なら効果を与え、60 以上（ミュウツー 60・エビワラー 70）なら何もしない。最大 HP はダメージを引かない。"""
        for card, expected in ((KOFFING, True), (RATTATA, True), (MEWTWO, False), (HITMONCHAN, False)):
            with self.subTest(card=card):
                state = self.state(mon(card, (), damage=20 if card != RATTATA else 0))
                done = attack(state, 0)
                added = events(done, len(state.log), "persistent_effect_added")
                self.assertEqual(bool(added), expected)
                if added:
                    self.assertEqual((added[0]["persistent_effect"], added[0]["active_turn"], added[0]["source_card"]),
                                     (CannotAttackWhileSourceActive.kind, TURN + 1, state.players[0].active.card))

    def test_locked_while_the_source_is_active(self):
        """次の相手の番、効果を与えたポケモンがバトル場にいる間は、ワザを使えない（``ATTACK_PREVENTED``。状態は変わらない）。突風で効果を与えたポケモンを控えに
        もどすと、ワザを使える（「バトル場にいる限り」）。"""
        done = attack(self.state(mon(RATTATA, (F,))), 0)
        assert_rejected(self, done, UseAttack(1, 0), "ATTACK_PREVENTED", IllegalActionError)
        gusted = play(done, PlayTrainer(1, card_of(done, 1, GUST)), [lambda d: (d.options[0],)])
        self.assertIsNone(cannot_attack_while_source_active(gusted, gusted.players[1].active))
        attacked = apply_kernel(gusted, UseAttack(1, 0))
        self.assertIn("damage", [e["kind"] for e in attacked.log[len(gusted.log):]])

    def test_sg1_returning_the_source_by_a_second_gust(self):
        """2 枚目の突風で、効果を与えたポケモンを選んでバトル場にもどすことは、SG1（``UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED``）で止める（選べるが選ぶと止める）。
        ほかの控えを選ぶ答えは受け付ける。選べる控えがそのポケモンだけなら、突風を使う前に止める。"""
        done = attack(self.state(mon(RATTATA, (F,)), bench=(RATTATA, DROWZEE)), 0)
        gusted = play(done, PlayTrainer(1, card_of(done, 1, GUST)), [lambda d: (d.options[0],)])
        second = apply_kernel(gusted, PlayTrainer(1, card_of(gusted, 1, GUST)))
        d = second.decision
        king = pid_of(second, 0, GIOVANNIS_NIDOKING)
        self.assertEqual(d.context_value("unresolved_choices"), (king,))
        assert_rejected(self, second, ResolveDecision(1, d.id, (king,)), "UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED", UnsupportedError)
        other = next(o for o in d.options if o != king)
        self.assertEqual(check_invariants(answer(second, (other,))), [])
        lone = attack(self.state(mon(RATTATA, (F,)), bench=(RATTATA,)), 0)
        lone = play(lone, PlayTrainer(1, card_of(lone, 1, GUST)), [lambda d: (d.options[0],)])
        assert_rejected(self, lone, PlayTrainer(1, card_of(lone, 1, GUST)), "UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED", UnsupportedError)

    def test_evolution_or_retreat_of_the_locked_pokemon_removes_the_effect(self):
        """効果を受けたポケモンが進化する（p.310 の「別のポケモン」）・にげてベンチにもどる（p.311・p.322）と、効果は消える（ほかの持続する効果と同じ）。"""
        done = attack(self.state(mon(KOFFING, (G,)), opponent_hand=(FOSSIL_WEEZING,)), 0)
        koffing = done.players[1].active.pokemon_id
        evolved = apply_kernel(done, EvolvePokemon(1, card_of(done, 1, FOSSIL_WEEZING), koffing))
        removed = events(evolved, len(done.log), "persistent_effect_removed")
        self.assertEqual([e["reason"] for e in removed], ["evolve"])
        self.assertIsNone(cannot_attack_while_source_active(evolved, evolved.players[1].active))
        retreated = apply_kernel(done, Retreat(1, tuple(done.players[1].active.energy[:1]), done.players[1].bench[0].card))
        self.assertEqual([e["reason"] for e in events(retreated, len(done.log), "persistent_effect_removed")], ["retreat"])

    def test_expires_at_the_end_of_the_opponents_turn(self):
        from kyuura_engine import EndTurn

        done = attack(self.state(mon(RATTATA, (F,))), 0)
        ended = apply_kernel(done, EndTurn(1))
        removed = events(ended, len(done.log), "persistent_effect_removed")
        self.assertEqual([(e["reason"], e["persistent_effect"]) for e in removed], [("expired", CannotAttackWhileSourceActive.kind)])

    def test_transparency_and_barrier(self):
        """相手に与える効果なので「とうめい」を評価する（ゴースト HP 50。「おもて」なら受けない）。最大 HP が 50 より大きいポケモンには、与える効果がないので
        「ワザをうけない」状態（ミュウツーのバリアー）も評価しない（ログ ``effect_prevented`` がない）。"""
        state = self.state(mon(HAUNTER, (P,)))
        evaded = attack(state, 0, H)
        self.assertEqual([e["kind"] for e in evaded.log[len(state.log):len(state.log) + 4]], ["attack", "coin_flip", "evade_check", "attack_evaded"])
        self.assertFalse(events(evaded, len(state.log), "persistent_effect_added"))
        received = attack(state, 0, T)
        self.assertTrue(events(received, len(state.log), "persistent_effect_added"))
        barrier = with_barrier(mon(GIOVANNIS_NIDOKING))  # ワザを使うのはプレイヤー 1。相手はバリアーのミュウツー（最大 HP 60）
        done = attack(barrier, 0, player=1)
        kinds = [e["kind"] for e in done.log[len(barrier.log):]]
        self.assertNotIn("effect_prevented", kinds)
        self.assertNotIn("persistent_effect_added", kinds)

    def test_serialized_effect(self):
        done = attack(self.state(mon(RATTATA, (F,))), 0)
        data = state_to_dict(done, format_version=10)["players"][1]["active"]["persistent_effects"]
        self.assertEqual([e["effect"] for e in data], [CannotAttackWhileSourceActive.kind])
        with self.assertRaises(ValueError):
            state_to_dict(done, format_version=7)


class LoveLariatTest(unittest.TestCase):
    """ラブラリアット（``FailOnTailsAmountIfBenchNamed``）: 「うら」なら失敗。自分のベンチに「サカキのニドキング」がいればダメージは 100（p.321 の 1 段階）。"""

    def test_tails_fails_heads_without_and_with_the_named_bench(self):
        cases = (((), T, None), ((), H, 50), ((mon(GIOVANNIS_NIDOKING, ()),), H, 100),
                 ((mon(GIOVANNIS_NIDOKING, ()), mon(GIOVANNIS_NIDOKING, ())), H, 100), ((mon(NIDOKING, ()),), H, 50))
        for bench, side, expected in cases:
            with self.subTest(bench=[b["card"] for b in bench], side=side):
                state = board(mon(GIOVANNIS_NIDOQUEEN), mon(MACHAMP, (F,)), bench=bench)
                done = attack(state, 1, side)
                since = len(state.log)
                if expected is None:
                    self.assertEqual(events(done, since, "attack_failed")[0]["reason"], "coin")
                    self.assertEqual(opponent_damage(done, since), [])
                else:
                    self.assertEqual(events(done, since, "damage")[0]["steps"][0][1], expected)

    def test_prevented_opponent_stops_before_the_coin(self):
        """「ダメージを受けない」相手には、残りの要素がダメージだけなので v0.4b の問い（ゴッドバードと同じ）。"""
        guarded = mon(METAPOD, (G, G), prevent_damage=TURN - 1)
        assert_stops(self, board(mon(GIOVANNIS_NIDOQUEEN), guarded), UseAttack(0, 1), "UNRESOLVED_PREVENTED_COIN_DAMAGE")


class DragOutTest(unittest.TestCase):
    """ひきずりだす・さそってとかす（``SwitchOpponentThenDamage``）: 相手の控えを選んで入れ替えてから、新しい対戦ポケモンにダメージ。"""

    def test_usage_requires_opponent_bench(self):
        for card, index in ((DARK_MACHOKE, 0), (ERIKAS_WEEPINBELL, 1)):
            with self.subTest(card=card):
                assert_rejected(self, board(mon(card), opponent_bench=()), UseAttack(0, index), "NO_OPPONENT_BENCH", IllegalActionError)

    def test_attacker_chooses_and_new_active_takes_the_damage(self):
        """選ぶのはワザを使ったプレイヤー（決定 ``FORCED_SWITCH``、選べるものは相手のベンチ）。入れ替えたあとのポケモン（コラッタ。弱点 闘）が、そのポケモンの
        弱点で 40 を受ける。ベンチにもどったポケモンのこんらんは消え、ダメージ・エネルギーは残る。"""
        state = board(mon(DARK_MACHOKE), mon(HITMONCHAN, (F, F), damage=30, confusion=True), opponent_bench=(DROWZEE, RATTATA))
        after = attack(state, 0)
        d = after.decision
        self.assertEqual((d.kind, d.player, d.options), (FORCED_SWITCH, 0, tuple(p.pokemon_id for p in state.players[1].bench)))
        rattata = pid_of(after, 1, RATTATA)
        done = answer(after, (rattata,))
        since = len(state.log)
        switched = events(done, since, "forced_switch")
        self.assertEqual((switched[0]["chosen_by"], switched[0]["new_active_pokemon_id"]), ("attacker", rattata))
        damage = events(done, since, "damage")
        self.assertEqual((damage[0]["amount"], damage[0]["weakness"]), (40, True))
        old = next(p for p in done.players[1].bench if done.cards[p.card].card_id == HITMONCHAN)
        self.assertEqual((old.damage, len(old.energy), old.conditions.confused), (30, 2, False))

    def test_protection_of_the_new_active_applies(self):
        """新しい対戦ポケモンが「ダメージを受けない」状態ならダメージは無効。カイリキー（はんげき）なら、ダメージのあとに 10 を返す。"""
        guarded = board(mon(ERIKAS_WEEPINBELL), opponent_bench=(mon(MACHAMP, (F,)),))
        done = play(guarded, UseAttack(0, 1), [first])
        kinds = [e["kind"] for e in done.log[len(guarded.log):]]
        self.assertEqual(kinds[:4], ["attack", "forced_switch", "damage", "counterattack"])

    def test_barrier_on_the_old_active_blocks_the_switch(self):
        """入れ替える前の相手の対戦ポケモンが「ワザをうけない」状態なら、入れ替えは無効（v0.31 のかどわかすと同じく、入れ替えは相手の対戦ポケモンへの効果）。ダメージは
        そのままのバトル場のポケモンに与え、それも無効。"""
        state = with_barrier(mon(DARK_MACHOKE))  # ワザを使うのはプレイヤー 1
        since = len(state.log)
        done = attack(state, 0, player=1)
        kinds = [e["kind"] for e in done.log[since:]]
        self.assertEqual(kinds[:3], ["attack", "effect_prevented", "damage_prevented"])
        self.assertNotIn("forced_switch", kinds)
        self.assertNotEqual(done.decision and done.decision.kind, FORCED_SWITCH)

    def test_two_transparency_pokemon_stop_with_t27(self):
        """入れ替える前のポケモンと新しいポケモンがどちらも「とうめい」を持つなら、1 つのワザで 2 匹の「とうめい」（T27。``UNRESOLVED_TRANSPARENCY_COIN_ORDER``）で、
        宣言の前に止まる（決定をまたいで「とうめい」の結果を運ぶ。``ForceSwitch`` の ``carry``）。わるいゴーリキーの「ひきずりだす」（闘 20）は、ゴースト（抵抗力 闘）
        への最終ダメージが 0 なので新しい対戦ポケモンの「とうめい」を評価せず（v0.9 の T21）、止まらない。"""
        state = board(mon(ERIKAS_WEEPINBELL), mon(HAUNTER, (P,)), opponent_bench=(mon(HAUNTER, ()),))
        assert_stops(self, state, UseAttack(0, 1), "UNRESOLVED_TRANSPARENCY_COIN_ORDER")
        resisted = board(mon(DARK_MACHOKE), mon(HAUNTER, (P,)), opponent_bench=(mon(HAUNTER, ()),))
        for mode in PREFLIGHT_MODES:
            with self.subTest(mode=mode):
                after = apply_kernel(with_coin_results(resisted, T), UseAttack(0, 0), preflight=mode)
                done = answer(after, after.decision.options[:1])
                self.assertEqual([e["amount"] for e in events(done, len(resisted.log), "damage")], [0])
                self.assertEqual(len(events(done, len(resisted.log), "evade_check")), 1)

    def test_invalid_answer_and_save_restore(self):
        state = board(mon(DARK_MACHOKE), opponent_bench=(DROWZEE, RATTATA))
        after = attack(state, 0)
        d = after.decision
        assert_rejected(self, after, ResolveDecision(0, d.id, (after.players[1].active.pokemon_id,)), "INVALID_CHOICE", IllegalActionError)
        assert_rejected(self, after, ResolveDecision(1, d.id, (d.options[0],)), "NOT_YOUR_DECISION", IllegalActionError)
        restored = pickle.loads(pickle.dumps(after))
        self.assertEqual(snapshot(answer(after, d.options[:1])), snapshot(answer(restored, d.options[:1])))


class FlingTest(unittest.TestCase):
    """つまみだす（``ReturnOpponentActiveToDeck``）: 相手の対戦ポケモンとついているカードを持ち主の山札にもどし、切る。きぜつではない。"""

    def state(self, opponent=None, *, opponent_bench=(DROWZEE, RATTATA)):
        opponent = opponent or mon(MACHAMP, (F, F), damage=30, confusion=True, trainers=[(PLUSPOWER, TURN - 1)])
        return board(mon(DARK_MACHAMP), opponent, opponent_bench=opponent_bench)

    def test_usage_requires_opponent_bench(self):
        assert_rejected(self, self.state(opponent_bench=()), UseAttack(0, 1), "NO_OPPONENT_BENCH", IllegalActionError)

    def test_returns_every_card_shuffles_and_the_owner_promotes(self):
        """もどすのは重なったカード 3 枚・エネルギー 2 枚・トレーナー 1 枚（持ち主の山札。カードの保存則）。ログは ``return_in_play_to_deck`` → 持ち主の山札の
        ``shuffle``（ワザの ``effect``）。きぜつ・サイドはない。ワザのあと、相手が控えから選んでバトル場に出す（``PROMOTE_ACTIVE``）。"""
        state = self.state()
        old = state.players[1].active
        cards = set(old.cards()) | set(old.energy) | {t.card for t in old.trainers}
        since = len(state.log)
        after = attack(state, 1)
        kinds = [e["kind"] for e in after.log[since:]]
        self.assertEqual(kinds[:3], ["attack", "return_in_play_to_deck", "shuffle"])
        self.assertEqual((events(after, since, "shuffle")[0]["player"], events(after, since, "shuffle")[0]["effect"]), (1, f"{DARK_MACHAMP}#1"))
        self.assertTrue(cards <= set(after.players[1].deck))
        self.assertEqual(card_count(after, 1), card_count(state, 1))
        self.assertNotIn("knock_out", kinds)
        self.assertEqual(len(after.players[1].prizes), len(state.players[1].prizes))
        d = after.decision
        self.assertEqual((d.kind, d.player, d.options), (PROMOTE_ACTIVE, 1, tuple(p.pokemon_id for p in after.players[1].bench)))
        self.assertEqual(check_invariants(after), [])
        restored = pickle.loads(pickle.dumps(after))
        done = answer(restored, d.options[:1])
        self.assertEqual(check_invariants(done), [])
        self.assertEqual(snapshot(done), snapshot(answer(after, d.options[:1])))

    def test_persistent_effects_on_the_returned_pokemon_are_removed(self):
        """もどしたポケモンの持続する効果は理由 ``return_in_play_to_deck`` で消える（かたまるの「ダメージを受けない」。ダメージ以外の効果は受ける）。"""
        state = self.state(mon(METAPOD, (G, G), prevent_damage=TURN - 1))
        done = attack(state, 1)
        removed = events(done, len(state.log), "persistent_effect_removed")
        self.assertEqual([e["reason"] for e in removed], ["return_in_play_to_deck"])

    def test_transparency_and_barrier_block_the_return(self):
        """「とうめい」で受けない・「ワザをうけない」状態なら、もどさず、山札も切らない（相手に与える効果）。"""
        state = self.state(mon(HAUNTER, (P,)))
        evaded = attack(state, 1, H)
        self.assertNotIn("return_in_play_to_deck", [e["kind"] for e in evaded.log[len(state.log):]])
        barrier = with_barrier(mon(DARK_MACHAMP))
        done = attack(barrier, 1, player=1)
        kinds = [e["kind"] for e in done.log[len(barrier.log):]]
        self.assertIn("effect_prevented", kinds)
        self.assertNotIn("return_in_play_to_deck", kinds)


class StingTest(unittest.TestCase):
    """きぜつばり（``CoinsAllHeadsBonusDamage``）: コイン 2 枚がすべて「おもて」なら + 60（「おもて」の数に比例しない）。"""

    def test_only_both_heads_adds(self):
        for sides, expected in (((H, H), 90), ((H, T), 30), ((T, H), 30), ((T, T), 30)):
            with self.subTest(sides=sides):
                state = board(mon(MISTYS_SEADRA), mon(MACHAMP, (F,)))
                done = attack(state, 1, *sides)
                self.assertEqual(events(done, len(state.log), "damage")[0]["steps"][0][1], expected)


class ShuffleTest(unittest.TestCase):
    """ひまつぶし・いたずら（``ShuffleDeckAttack``）: 自分の・相手の山札を切る（乱数の並べかえ 1 回。ログ ``shuffle`` の ``player`` は持ち主）。"""

    def test_own_and_opponent_deck(self):
        for card, owner in ((BROCKS_MANKEY, 0), (MANKEY, 1)):
            with self.subTest(card=card):
                state = board(mon(card), deck=(FIRE, WATER, GRASS, P, F))
                since = len(state.log)
                done = attack(state, 0)
                shuffles = [e for e in events(done, since, "shuffle") if e.get("effect")]
                self.assertEqual([(e["player"], e["effect"]) for e in shuffles], [(owner, f"{card}#0")])
                # 山札のカードは変わらない（番が終わって相手が 1 枚引くので、手札と合わせて比べる）
                cards = sorted(done.players[owner].deck + done.players[owner].hand)
                self.assertEqual(cards, sorted(state.players[owner].deck + state.players[owner].hand))
                self.assertFalse(events(done, since, "damage"))

    def test_barrier_does_not_stop_shuffling_the_opponents_deck(self):
        """相手の山札を切ることは相手の対戦ポケモンへの効果ではない（「ワザをうけない」状態でも切る）。"""
        state = with_barrier(mon(MANKEY))
        done = attack(state, 0, player=1)
        self.assertEqual([e["player"] for e in events(done, len(state.log), "shuffle") if e.get("effect")], [0])


class RampageTest(unittest.TestCase):
    """あばれまわる（``DamageThenSelfConfuseOnTails``）: ダメージ → コインの「うら」で自分がこんらん（相手に与えるこんらんではない）。"""

    def test_tails_confuses_the_attacker(self):
        state = board(mon(PRIMEAPE), mon(MACHAMP, (F,)))
        tails = attack(state, 1, T)
        self.assertTrue(tails.players[0].active.conditions.confused)
        self.assertFalse(tails.players[1].active.conditions.confused)
        heads = attack(state, 1, H)
        self.assertFalse(heads.players[0].active.conditions.confused)

    def test_prevented_opponent_still_flips(self):
        """コインは自分への効果だけを決めるので、相手が「ダメージを受けない」状態でも投げる。"""
        state = board(mon(PRIMEAPE), mon(METAPOD, (G, G), prevent_damage=TURN - 1))
        done = attack(state, 1, T)
        self.assertEqual(len([e for e in events(done, len(state.log), "coin_flip") if e["source"] == "attack"]), 1)
        self.assertTrue(done.players[0].active.conditions.confused)


class CopyTest(unittest.TestCase):
    """相手のワザを自分のワザとして使う効果（ピクシー・ピッピの「ゆびをふる」・カスミのコダックの「ちょうのうりょく」）での v0.40 のワザ。"""

    COPIERS: ClassVar[dict] = {CLEFABLE: ((P,), 0, ()), CLEFAIRY: ((P, P, P), 1, ()), MISTYS_PSYDUCK: ((P,), 0, (H, H, H))}

    def copier(self, card, target, *, bench=(RATTATA,), opponent_bench=(RATTATA,), damage=0):
        return board(mon(card, self.COPIERS[card][0], damage=damage), mon(target, ()), bench=bench, opponent_bench=opponent_bench,
                     deck=(KOGAS_ZUBAT, FIRE, FIRE))

    def test_every_attack_can_be_copied_without_internal_errors(self):
        """28 のワザのどれをまねても、エンジンの内部のエラーにならない（処理するか、決まったコードで拒否する）。まねたワザの処理のあとも不変条件が通る。"""
        for (card, index) in EXPECTED:
            for copier, (energy, attack_index, sides) in self.COPIERS.items():
                with self.subTest(card=card, index=index, copier=copier):
                    # いかりのいちげきは自分のカウンター 2 つ以上が使うための条件なので、まねるポケモンにカウンターを 2 つのせる
                    damage = 20 if (card, index) == (GIOVANNIS_NIDORAN_M, 1) else 0
                    state = self.copier(copier, card, bench=(RATTATA, KOFFING), opponent_bench=(RATTATA, BULBASAUR), damage=damage)
                    try:
                        current = play(with_coin_results(state, *sides, H, H, H), UseAttack(0, attack_index), [])
                        if current.decision is not None and current.decision.kind == SELECT_ATTACK:
                            self.assertIn(index, current.decision.options)
                            current = apply_kernel(current, ResolveDecision(0, current.decision.id, (index,)))
                        while current.decision is not None and current.decision.resume == "attack":
                            d = current.decision
                            current = apply_kernel(current, ResolveDecision(d.player, d.id, first(d)))
                    except EngineError as error:
                        self.assertTrue(error.code.startswith(("UNRESOLVED_", "UNSUPPORTED_")), error.code)
                        continue
                    self.assertEqual(check_invariants(current), [])

    def test_usage_conditions_follow_the_copier_clause(self):
        """いかりのいちげき（自分のカウンター 2 つ以上）・ひきずりだす・つまみだす（相手の控え）を、条件のたりないときにまねる: ピクシー・ピッピは選べない、
        カスミのコダックは選べるが選ぶと HC9（``UNRESOLVED_COPIED_ATTACK``）。"""
        for card, index, kwargs in ((GIOVANNIS_NIDORAN_M, 1, {}), (DARK_MACHOKE, 0, {"opponent_bench": ()}), (DARK_MACHAMP, 1, {"opponent_bench": ()})):
            for copier, (energy, attack_index, sides) in self.COPIERS.items():
                with self.subTest(card=card, copier=copier):
                    state = self.copier(copier, card, **kwargs)
                    after = play(with_coin_results(state, *sides), UseAttack(0, attack_index), [])
                    d = after.decision
                    if copier == MISTYS_PSYDUCK:
                        self.assertIn(index, d.context_value("unresolved_choices", ()))
                        self.assertEqual(d.context_value("unresolved_code"), "UNRESOLVED_COPIED_ATTACK")
                    else:
                        self.assertNotIn(index, d.options)

    def test_intimidate_copied_has_no_effect_on_the_nidoking(self):
        """すごむをまねるとき、相手の対戦ポケモンはまねる元のサカキのニドキング（最大 HP 50 より大きい）なので、効果を与えない（まねること自体はできる）。"""
        state = self.copier(CLEFABLE, GIOVANNIS_NIDOKING)
        self.assertGreater(load_card_pool().get(GIOVANNIS_NIDOKING).hp, 50)
        done = play(state, UseAttack(0, 0), [(0,)])
        self.assertFalse(events(done, len(state.log), "persistent_effect_added"))
        self.assertEqual(check_invariants(done), [])


class IntegrityTest(unittest.TestCase):
    """不変条件・書き出し・拒否で状態が変わらないこと・渡した状態を変えないこと。"""

    CASES = (
        (KOGAS_ZUBAT, 0, (), (lambda d: tuple(d.options),)), (KOGAS_GOLBAT, 0, (), ()), (KOGAS_GOLBAT, 1, (H,), ()), (DARK_WEEZING, 0, (), ()),
        (DARK_WEEZING, 1, (T,), ()), (DARK_HYPNO, 0, (), ()), (DARK_HYPNO, 1, (T, H), ()), (GIOVANNIS_NIDORAN_M, 0, (H, T), ()),
        (GIOVANNIS_NIDORAN_M, 1, (), ()), (GIOVANNIS_NIDORINO, 0, (), ()), (GIOVANNIS_NIDOKING, 0, (), ()), (GIOVANNIS_NIDOKING, 1, (H,), ()),
        (GIOVANNIS_NIDOQUEEN, 0, (), ()), (GIOVANNIS_NIDOQUEEN, 1, (H,), ()), (DARK_MACHOKE, 0, (), (first,)), (DARK_MACHOKE, 1, (), (first,)),
        (DARK_MACHAMP, 0, (), ()), (DARK_MACHAMP, 1, (), (first,)), (ERIKAS_WEEPINBELL, 0, (), ()), (ERIKAS_WEEPINBELL, 1, (), (first,)),
        (MISTYS_SEADRA, 0, (), ()), (MISTYS_SEADRA, 1, (H, H), ()), (BROCKS_MANKEY, 0, (), ()), (BROCKS_MANKEY, 1, (), ()), (MANKEY, 0, (), ()),
        (MANKEY, 1, (H,), ()), (PRIMEAPE, 0, (H, T, H), ()), (PRIMEAPE, 1, (T,), ()),
    )

    def state(self, card):
        return board(mon(card, damage=20 if card == GIOVANNIS_NIDORAN_M else 0), mon(KOFFING, (G,), damage=10), bench=(RATTATA, ROCKET_KOFFING),
                     opponent_bench=(RATTATA, DROWZEE), deck=(KOGAS_ZUBAT, FIRE, KOGAS_ZUBAT, FIRE))

    def test_cases_cover_every_attack(self):
        self.assertEqual(sorted((card, index) for card, index, _, _ in self.CASES), sorted(EXPECTED))

    def test_every_step_keeps_invariants_and_does_not_mutate_the_input(self):
        """どのワザも、途中の決定ごとに不変条件が通り、書き出し（形式 10）と pickle で同じ状態にもどる。``apply_command`` は渡した状態を変えない。"""
        for card, index, sides, answers in self.CASES:
            with self.subTest(card=card, index=index):
                state = self.state(card)
                before = copy.deepcopy(full(state))
                current = apply_kernel(with_coin_results(state, *sides), UseAttack(0, index))
                self.assertEqual(full(state), before)
                for answer_of in answers:
                    self.assertEqual(check_invariants(current), [])
                    self.assertEqual(full(pickle.loads(pickle.dumps(current))), full(current))
                    d = current.decision
                    current = apply_kernel(current, ResolveDecision(d.player, d.id, answer_of(d)))
                self.assertEqual(check_invariants(current), [])
                self.assertTrue(current.decision is None or current.decision.resume != "attack")


class PreflightParityTest(unittest.TestCase):
    """先読みの方法（derived・derived_full・legacy）によらず、同じコインの結果で同じ結果になる（v0.40 の型はどれも ``VERIFIED`` に入れていないので、legacy も
    すべての結果を試す方法）。山札を切る要素は先読みでは切らない（実際の処理だけが乱数で切る）。"""

    def test_same_result_in_every_mode(self):
        for card, index, sides, answers in IntegrityTest.CASES:
            with self.subTest(card=card, index=index):
                state = IntegrityTest().state(card)
                results = set()
                for mode in PREFLIGHT_MODES:
                    done = play(with_coin_results(state, *sides), UseAttack(0, index), answers, mode=mode)
                    results.add(repr(snapshot(done)))
                self.assertEqual(len(results), 1)


class DocumentTest(unittest.TestCase):
    def test_document_records_the_decisions(self):
        """文書に、カードごとの結果・SG1 の根拠と影響の範囲・既存の問いの再利用・照合の違いを書いた。"""
        text = DOC.read_text(encoding="utf-8")
        for needle in ("SG1", "UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED", "JS1", "RD9", "T27", "pcg-search.com", "むれでおそう", "みんなでばくはつ",
                       "ベンチをあやつる", "すごむ", "ラブラリアット", "ひきずりだす", "つまみだす", "きぜつばり", "ひまつぶし", "いたずら", "あばれまわる"):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
