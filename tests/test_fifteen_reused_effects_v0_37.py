"""v0.37: 既存の効果の再利用を中心にした 15 枚（docs/fifteen-reused-effects-v0.37.md）。

カードの登録と記録（``CardDataTest``）、文面の違いの受け付けと拒否（``TextVariantTest``）、コインで相手がワザを使えなくなるワザ（``CannotAttackTest``）、
化石の秘密のベトベター（``FossilGrimerTest``）、v0.36 の効果の再利用（``SandTest``）、ライチュウ（``RaichuTest``）、ダグトリオの「じしん」と JS1
（``EarthquakeTest``）、ニョロゾ・ニョロボン（``PoliwagLineTest``）、ダメージのないコインの特殊状態（``StatusWithoutDamageTest``）、コインで引く
（``DrawTest``）、しんだふり（``PlayDeadTest``）、かみつく（``BiteTest``）、まねるワザ（``CopyTest``）、進化（``EvolutionTest``）、不変条件・書き出し・
保存と再開（``IntegrityTest``）、先読みの方法ごとの一致（``PreflightParityTest``）に分けた。

根拠は kyuura データの採用（kyuura の印刷の文面。``card_sources.json``）と、化石の秘密のベトベターの過去の原典照合の記録（v0.8。p.47）と、既存の
記録の再利用（p.309 のワザの手順・p.312 の「引けるだけ引く」・p.321 のダメージの計算の段階・p.322・p.323 の持続する効果）。ガイドブックは読んでいない。
"""

from __future__ import annotations

import copy
import pathlib
import pickle
import unittest
from collections import Counter

from kyuura_engine import (
    EndTurn,
    EngineError,
    EvolvePokemon,
    IllegalActionError,
    ResolveDecision,
    UseAttack,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import Attack, load_card_pool, read_extract
from kyuura_engine.persistent import attack_barrier, cannot_attack, damage_prevention, damage_reduction, reduced_damage_to_source
from kyuura_engine.resolution import PREFLIGHT_MODES, v013_checks
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import AttackBarrier, CannotAttack, CannotUseAttack, DamageReduction, ReducedDamageToSource
from scripts import check_card_sources as cs
from scripts.extract_kyuura_cards import KYUURA_COMMIT
from tests.helpers import (
    BROCKS_ONIX,
    BROCKS_SANDSHREW,
    CATERPIE,
    CLEFABLE,
    CLEFAIRY,
    DARK_JOLTEON,
    DEFENDER,
    DIGLETT,
    DUGTRIO,
    EEVEE,
    FIGHTING,
    FIRE,
    FOSSIL_EKANS,
    FOSSIL_GRIMER,
    GRASS,
    GRIMER,
    HITMONCHAN,
    KOGAS_PIDGEY,
    KOGAS_TANGELA,
    LIGHTNING,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MEOWTH,
    METAPOD,
    MISTYS_MAGIKARP,
    MISTYS_PSYDUCK,
    PERSIAN,
    PIKACHU,
    PLUSPOWER,
    POLIWAG,
    POLIWHIRL,
    POLIWRATH,
    PSYCHIC,
    RAICHU,
    RATTATA,
    RHYHORN,
    ROCKET_EEVEE,
    STARYU,
    SABRINAS_DROWZEE,
    V0_37_ADOPTED,
    V0_37_POKEMON,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import serialization_problems
from tests.test_barrier_resume_coin_bonus_v0_34 import assert_stops, coins, events, full, kinds, play, with_barrier

ROOT = pathlib.Path(__file__).resolve().parent.parent
TURN = 7
DOC = ROOT / "docs" / "fifteen-reused-effects-v0.37.md"
BELOW = {RAICHU: PIKACHU, DUGTRIO: DIGLETT, POLIWHIRL: POLIWAG, POLIWRATH: [POLIWAG, POLIWHIRL], PERSIAN: MEOWTH, METAPOD: CATERPIE,
         CLEFABLE: CLEFAIRY, MACHAMP: [MACHOP, MACHOKE], DARK_JOLTEON: EEVEE}
# ワザを使うのに足りるエネルギー（ニョロボンの「みずでっぽう」は HC4 を起こさない払い方。HC4 は PoliwagLineTest）
ENERGY = {RHYHORN: (FIGHTING,) * 3, FOSSIL_GRIMER: (GRASS,), ROCKET_EEVEE: (FIGHTING, FIGHTING), BROCKS_SANDSHREW: (FIGHTING, FIGHTING),
          SABRINAS_DROWZEE: (PSYCHIC, PSYCHIC), RAICHU: (LIGHTNING,) * 4, DUGTRIO: (FIGHTING,) * 4, POLIWHIRL: (WATER,) * 3,
          POLIWRATH: (WATER, WATER, FIRE, FIRE), FOSSIL_EKANS: (GRASS, GRASS), BROCKS_ONIX: (FIGHTING,) * 3, MEOWTH: (FIGHTING, FIGHTING),
          KOGAS_TANGELA: (GRASS, GRASS), MISTYS_MAGIKARP: (WATER,), PERSIAN: (FIGHTING,) * 3}
# 登録の実装の型と値（カード id, ワザの位置）
EXPECTED = {
    (RHYHORN, 0): (E.CannotAttackOnHeads, {}),
    (RHYHORN, 1): (E.DamageOnly, {}),
    (FOSSIL_GRIMER, 0): (E.ParalyzeOnHeads, {}),
    (FOSSIL_GRIMER, 1): (E.ReduceDamageNextTurn, {"amount": 20}),
    (ROCKET_EEVEE, 0): (E.DamageOnly, {}),
    (ROCKET_EEVEE, 1): (E.DamageThenAttackCoinCheck, {"single_use": False}),
    (BROCKS_SANDSHREW, 0): (E.DamageThenRetreatLock, {}),
    (SABRINAS_DROWZEE, 0): (E.CannotAttackOnHeads, {}),
    (SABRINAS_DROWZEE, 1): (E.DamageOnly, {}),
    (RAICHU, 0): (E.DamageThenSelfBarrierOnHeads, {}),
    (RAICHU, 1): (E.SelfDamageOnTails, {"self_damage": 30}),
    (DUGTRIO, 0): (E.DamageOnly, {}),
    (DUGTRIO, 1): (E.DamageAndOwnBenchDamage, {"bench_damage": 10, "weakness_resistance_stated": False}),
    (POLIWHIRL, 0): (E.LockOpponentAttack, {}),
    (POLIWHIRL, 1): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 30}),
    (POLIWRATH, 0): (E.ExtraEnergyDamageMixed, {"energy_type": E.EnergyType.WATER, "per_energy": 10, "max_extra": 2}),
    (POLIWRATH, 1): (E.DamageThenDiscardOpponentEnergy, {"on_heads": False}),
    (FOSSIL_EKANS, 0): (E.PoisonOnHeadsWithoutDamage, {}),
    (FOSSIL_EKANS, 1): (E.ParalyzeOnHeads, {}),
    (BROCKS_ONIX, 0): (E.ParalyzeOnHeadsWithoutDamage, {}),
    (BROCKS_ONIX, 1): (E.DamageOnly, {}),
    (MEOWTH, 0): (E.DamageThenDrawOnHeads, {"count": 1}),
    (KOGAS_TANGELA, 0): (E.SleepOpponent, {}),
    (KOGAS_TANGELA, 1): (E.DrawOnHeads, {"count": 2}),
    (MISTYS_MAGIKARP, 0): (E.SelfBarrierOnHeads, {}),
    (MISTYS_MAGIKARP, 1): (E.DamageOnly, {}),
    (PERSIAN, 0): (E.DamageOnly, {}),
    (PERSIAN, 1): (E.DamageThenReduceDamageToSelf, {"amount": 10}),
}
# pcg-search.com の対象の版（サイトの一覧の番号）。化石の秘密のベトベターは過去の原典照合の記録のあるカード（照合だけを書く）
EDITIONS = {RHYHORN: "032/048", FOSSIL_GRIMER: "005/048", ROCKET_EEVEE: "049/065", BROCKS_SANDSHREW: "044/096", SABRINAS_DROWZEE: "052/098",
            RAICHU: "036/096", DUGTRIO: "053/096", POLIWHIRL: "027/096", POLIWRATH: "028/096", FOSSIL_EKANS: "001/048", BROCKS_ONIX: "053/096",
            MEOWTH: "040/048", KOGAS_TANGELA: "017/098", MISTYS_MAGIKARP: "034/096", PERSIAN: "041/048"}


def mon(card, energy=None, **extra):
    spec = {"card": card, "energy": list(ENERGY.get(card, ()) if energy is None else energy), **extra}
    if BELOW.get(card) is not None and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), hand=(), opponent_hand=(), deck=None, turn=TURN):
    me = {"active": active, "bench": list(bench), "hand": list(hand)}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent or mon(HITMONCHAN, (FIGHTING, FIGHTING)), "bench": list(opponent_bench), "hand": list(opponent_hand)}
    return build_test_state([me, them], turn_number=turn)


def snapshot(state):
    return full(state), rng_fingerprint(state.rng), [dict(e) for e in state.log]


def attack_with(state, player, index, *sides, mode="derived"):
    return apply_kernel(with_coin_results(state, *sides), UseAttack(player, index), preflight=mode)


def opponent_damage(state, since):
    return [e for e in events(state, since, "damage") if e.get("target") is None]


def assert_rejected(test, state, command, code, exception=EngineError):
    before = snapshot(state)
    with test.assertRaises(exception) as raised:
        apply_kernel(state, command)
    test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def printed(card, index):
    return load_card_pool().get(card).attacks[index]


def with_text(attack: Attack, text: str) -> Attack:
    """文面だけを変えたワザ（写しは変えない。登録の ``check`` が受け付けるかを確かめるだけ）。"""
    import dataclasses

    return dataclasses.replace(attack, text_ja=text)


class CardDataTest(unittest.TestCase):
    """15 枚の登録・写し・採用の記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_fifteen_requested_cards(self):
        """対象は依頼の 15 枚（ほかの候補に広げていない）。写しの組 pool_v0_37 は 15 枚で、どれも対戦に使える。化石の秘密のベトベターは v0.36 まで参照
        カードだった（参照カードの一覧から外した）。同じ名前の別のカードとは別の id で、ワザも違う。"""
        self.assertEqual(len(V0_37_POKEMON), 15)
        self.assertEqual(list(read_extract()["pool_v0_37"]), list(V0_37_POKEMON))
        self.assertNotIn(FOSSIL_GRIMER, read_extract()["reference_only"])
        for card in V0_37_POKEMON:
            with self.subTest(card=card):
                self.assertTrue(self.pool.is_playable(card))
        from tests.helpers import BROCKS_RHYHORN, DROWZEE, GIOVANNIS_MEOWTH, MAGIKARP, ROCKET_EKANS, SANDSHREW, TANGELA

        for ours, other in ((RHYHORN, BROCKS_RHYHORN), (FOSSIL_GRIMER, GRIMER), (ROCKET_EEVEE, EEVEE), (BROCKS_SANDSHREW, SANDSHREW),
                            (SABRINAS_DROWZEE, DROWZEE), (FOSSIL_EKANS, ROCKET_EKANS), (MEOWTH, GIOVANNIS_MEOWTH), (KOGAS_TANGELA, TANGELA),
                            (MISTYS_MAGIKARP, MAGIKARP)):
            with self.subTest(card=ours):
                self.assertNotEqual(ours, other)
                self.assertNotEqual([a.name_ja for a in self.pool.get(ours).attacks], [a.name_ja for a in self.pool.get(other).attacks])

    def test_every_attack_is_registered_with_the_expected_type(self):
        """28 のワザがどれも登録され、型と値が表のとおり。名前・文面は写しと同じ。処理に使う文面は kyuura の印刷の文面で、化石の秘密のベトベターの
        「ちいさくなる」だけは過去の原典照合の記録の最新の説明（kyuura の LD-PMCG3-003-ATK1 と同じ）。特殊能力を持つカードはない。"""
        seen = set()
        verification = __import__("kyuura_engine.cards", fromlist=["read_verification"]).read_verification()
        for card in V0_37_POKEMON:
            definition = self.pool.get(card)
            self.assertEqual(definition.powers, ())
            for attack in definition.attacks:
                key = (card, attack.index)
                seen.add(key)
                entry = E.DEFAULT_EFFECTS.attack_entry(card, attack.index)
                kind, values = EXPECTED[key]
                with self.subTest(key=key):
                    self.assertIs(type(entry.effect), kind)
                    for name, value in values.items():
                        self.assertEqual(getattr(entry.effect, name), value)
                    self.assertEqual((entry.name_ja, entry.text_ja), (attack.name_ja, attack.text_ja))
                    if card == FOSSIL_GRIMER:
                        recorded = verification["cards"][card]["latest_description_ja"][str(attack.index)]
                        self.assertEqual((entry.play_text_ja, entry.source), (recorded, "P43 p.47"))
                    else:
                        self.assertEqual(entry.play_text_ja, attack.text_ja)
                        if attack.text_ja is not None:
                            self.assertEqual(entry.source, "kyuura data/cards.json")
        self.assertEqual(seen, set(EXPECTED))
        self.assertNotEqual(E.DEFAULT_EFFECTS.attack_entry(FOSSIL_GRIMER, 1).play_text_ja, printed(FOSSIL_GRIMER, 1).text_ja)

    def test_records(self):
        """採用の記録（kyuura データ・写しの元のコミット）は 14 枚。化石の秘密のベトベターは過去の原典照合の記録（card_verification.json）で登録し、
        card_sources.json には pcg-search.com の照合だけを書く（読んでいない原典を確かめたことにする記録を作らない）。pcg-search.com の同じ版のページとの
        違いはペルシアンの「【相手】」だけで、処理に影響しない。ガイドブックの項目はない。"""
        sources = cs.load_sources()
        self.assertEqual(cs.problems(), [])
        for card in V0_37_POKEMON:
            record = sources["cards"][card]
            with self.subTest(card=card):
                if card == FOSSIL_GRIMER:
                    self.assertEqual(record["basis"], cs.GUIDEBOOK_RECORD)
                else:
                    self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]), (cs.KYUURA_DATA, cs.ADOPTED, KYUURA_COMMIT))
                    self.assertEqual(record["kyuura_records"], ["CC-PMCG5-048-P200"] if card == BROCKS_ONIX else [])
                [check] = record["external_checks"]
                self.assertEqual((check["site"], check["edition"]["list_number"], check["checked_on"]), ("pcg-search.com", EDITIONS[card], "2026-10-16"))
                self.assertFalse(any(d["affects_behavior"] for d in check["differences"]))
        changed = {card for card in V0_37_POKEMON if sources["cards"][card]["external_checks"][0]["differences"]}
        self.assertEqual(changed, {PERSIAN})
        self.assertEqual(sorted(V0_37_ADOPTED), sorted(set(V0_37_POKEMON) - {FOSSIL_GRIMER}))

    def test_document_lists_every_card_and_unresolved_id(self):
        text = DOC.read_text(encoding="utf-8")
        for card in V0_37_POKEMON:
            self.assertIn(card, text)
        for word in ("JS1", "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE", "HC4", "LOCK_OPPONENT_ATTACK_TEXTS", "SELF_BARRIER_ON_HEADS_TEXTS"):
            self.assertIn(word, text)

    def test_counts(self):
        """登録したワザは 28（説明文のあるワザ 21）。v0.37 で加えた型は 6 つで、v0.13 の止める関数の型（``VERIFIED``）に入れていない。"""
        keys = [k for k in E.DEFAULT_EFFECTS.attack_keys() if k.card_id in V0_37_POKEMON]
        self.assertEqual(len(keys), 28)
        self.assertEqual(sum(1 for k in keys if E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).text_ja), 21)
        types = Counter(type(E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect).__name__ for k in keys)
        self.assertEqual(types["DamageOnly"], 7)
        for cls in (E.PoisonOnHeadsWithoutDamage, E.ParalyzeOnHeadsWithoutDamage, E.DamageThenDrawOnHeads, E.DrawOnHeads, E.SelfBarrierOnHeads,
                    E.DamageThenReduceDamageToSelf):
            self.assertNotIn(cls, v013_checks.VERIFIED)
        # 登録表の全体の数（v0.37 で 314）は tests/test_effects.py が確かめる（v0.38 で 343。後の版で増えるので、ここでは確かめない）


class TextVariantTest(unittest.TestCase):
    """文面の違い: 同じ意味の書き方だけを、登録の ``check`` が受け付ける（写し・採用した印刷の文面は変えていない。文面の確かめを外していない）。"""

    def test_accepted_variants(self):
        """v0.37 の写しの文面を、それぞれの型が受け付ける（登録されていて対戦に使える）。"""
        for (card, index), (kind, values) in EXPECTED.items():
            with self.subTest(card=card, index=index):
                self.assertEqual(kind(**values).check(printed(card, index)), [])

    def test_raichu_agility(self):
        """ライチュウの「こうそくいどう」は、主語のない書き方（「次の相手の番の「ワザ」をうけない。」）だけを加えた。ほかの「おもて」の自分の効果
        （「ダメージを受けない」状態・特殊状態の回復など）の書き方は受け付けない。"""
        attack = printed(RAICHU, 0)
        self.assertIn(attack.text_ja, E.SELF_BARRIER_ON_HEADS_TEXTS)
        effect = E.DamageThenSelfBarrierOnHeads()
        for text in ("コインを投げて「おもて」なら、次の相手の番、このカードはダメージを受けない。",
                     "コインを投げて「おもて」なら、次の相手の番の「ワザ」のダメージをうけない。",
                     "コインを投げて「おもて」なら、次の番の「ワザ」をうけない。",
                     "コインを投げて「うら」なら、次の相手の番の「ワザ」をうけない。"):
            with self.subTest(text=text):
                self.assertTrue(effect.check(with_text(attack, text)))

    def test_dugtrio_earthquake(self):
        """ダグトリオの「じしん」は、説明に「弱点・抵抗力」の書いていない書き方として、別の値（``weakness_resistance_stated=False``）でだけ受け付ける。
        値と書き方が食い違う登録・ダメージの数の違う書き方は受け付けない。"""
        attack = printed(DUGTRIO, 1)
        self.assertEqual(E.DamageAndOwnBenchDamage(10, weakness_resistance_stated=False).check(attack), [])
        self.assertTrue(E.DamageAndOwnBenchDamage(10).check(attack))
        self.assertTrue(E.DamageAndOwnBenchDamage(20, weakness_resistance_stated=False).check(attack))
        from tests.helpers import BROCKS_DIGLETT

        mini = printed(BROCKS_DIGLETT, 1)  # v0.33 のミニじしん（「弱点・抵抗力」に関係なく）
        self.assertEqual(E.DamageAndOwnBenchDamage(10).check(mini), [])
        self.assertTrue(E.DamageAndOwnBenchDamage(10, weakness_resistance_stated=False).check(mini))
        self.assertTrue(E.DamageAndOwnBenchDamage(10, weakness_resistance_stated=False).check(with_text(attack, "相手の控えポケモン全員にも10ダメージ。")))
        with self.assertRaises(ValueError):
            E.DamageAndOwnBenchDamage(10, weakness_resistance_stated=None)

    def test_poliwhirl_amnesia(self):
        """ニョロゾの「ドわすれ」は「相手の対戦ポケモンの「ワザ」を1つ選ぶ。次の相手の番でその「ワザ」はつかえない。」を加えた（v0.35 のカスミの
        ニョロモと同じ意味。``LOCK_OPPONENT_ATTACK_TEXTS``）。選ぶプレイヤー・期限・対象の違う書き方は受け付けない。"""
        attack = printed(POLIWHIRL, 0)
        self.assertIn(attack.text_ja, E.LOCK_OPPONENT_ATTACK_TEXTS)
        effect = E.LockOpponentAttack()
        for text in ("相手は、自分の対戦ポケモンの「ワザ」を1つ選ぶ。次の相手の番でその「ワザ」はつかえない。",
                     "相手の対戦ポケモンの「ワザ」を1つ選ぶ。次の番でその「ワザ」はつかえない。",
                     "相手の対戦ポケモンの「ワザ」をすべて選ぶ。次の相手の番でその「ワザ」はつかえない。"):
            with self.subTest(text=text):
                self.assertTrue(effect.check(with_text(attack, text)))

    def test_persian_bite(self):
        """ペルシアンの「かみつく」は、なきつく（v0.34）と同じ形で、「【相手】」・「あたえる」の書き方の違いだけを受け付ける（pcg-search.com は「相手」）。
        へる数・期限の違う書き方は受け付けない。ダメージのないワザ（なきつく）の型とは別。"""
        attack = printed(PERSIAN, 1)
        effect = E.DamageThenReduceDamageToSelf(10)
        self.assertEqual(effect.check(with_text(attack, attack.text_ja.replace("【相手】", "相手"))), [])
        self.assertEqual(effect.check(with_text(attack, attack.text_ja.replace("あたえる", "与える"))), [])
        self.assertTrue(effect.check(with_text(attack, attack.text_ja.replace("10へる", "20へる"))))
        self.assertTrue(effect.check(with_text(attack, attack.text_ja.replace("次の自分の番の始めに", "次の相手の番の終わりに"))))
        self.assertTrue(E.DamageThenReduceDamageToSelf(20).check(attack))
        self.assertTrue(E.ReduceDamageToSelf(10).check(attack))  # ダメージのあるワザ

    def test_reused_form_only_types_now_check_the_text(self):
        """v0.36 まで形だけを確かめていた型（``CannotAttackOnHeads``・``ReduceDamageNextTurn``・``ExtraEnergyDamageMixed``）も、v0.37 から説明の書き方を
        確かめる。受け付けるのは登録済みのカードと v0.37 のカードの書き方だけで、意味の違う書き方は受け付けない。"""
        rhyhorn = printed(RHYHORN, 0)
        for text in ("コインを投げて「おもて」なら「にらみつける」を受けた相手の対戦ポケモンは、次の相手の番に「にげる」ことができない。",
                     "コインを投げて「おもて」なら、次の相手の番、このワザを受けた相手は、ワザを使えず、「にげる」こともできない。",
                     "コインを投げて「おもて」なら「しっぽをふる」を受けた相手の対戦ポケモンは、次の相手の番にワザをつかえない。"):
            with self.subTest(text=text):
                self.assertTrue(E.CannotAttackOnHeads().check(with_text(rhyhorn, text)))  # 3 つめは名前が別のワザ
        shrink = printed(FOSSIL_GRIMER, 1)
        self.assertTrue(E.ReduceDamageNextTurn(30).check(shrink))
        self.assertTrue(E.ReduceDamageNextTurn(20).check(with_text(shrink, "次の相手の番でこのカードが受けるダメージは20へる。(ダメージも効果も受けない)")))
        water = printed(POLIWRATH, 0)
        self.assertTrue(E.ExtraEnergyDamageMixed(E.EnergyType.WATER, 20, 2).check(water))
        self.assertTrue(E.ExtraEnergyDamageMixed(E.EnergyType.WATER, 10, 3).check(water))
        from tests.helpers import CLEFABLE as _CLEFABLE, EEVEE as _EEVEE, PSYDUCK, VAPOREON

        for card, index in ((_EEVEE, 0), (_CLEFABLE, 1), (PSYDUCK, 1), (VAPOREON, 1)):  # 登録済みの書き方は変わらず受け付ける
            with self.subTest(card=card):
                self.assertTrue(load_card_pool().is_playable(card))
                entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
                self.assertEqual(entry.effect.check(printed(card, index)), [])

    def test_unregistered_attacks_with_the_old_text_stay_unsupported(self):
        """文面の確かめを外していないので、登録を除いた登録表では、どのカードも対戦に使えない（未実装のワザを効果がないものとして扱わない）。"""
        from kyuura_engine.cards import pool_from_extract
        from kyuura_engine.effects import AttackKey

        keys = [AttackKey(card, index) for card, index in EXPECTED]
        pool = pool_from_extract(read_extract(), E.DEFAULT_EFFECTS.without_attacks("test-no-v037", keys))
        for card in V0_37_POKEMON:
            with self.subTest(card=card):
                self.assertFalse(pool.is_playable(card))


class CannotAttackTest(unittest.TestCase):
    """サイホーンの「にらみつける」・ナツメのスリープの「あんじをかける」（v0.31 の ``CannotAttackOnHeads``。相手に与える持続する効果 ``CannotAttack``）。"""

    def test_heads_locks_the_next_opponent_turn_and_tails_does_nothing(self):
        """ダメージはない（ログ ``damage`` なし）。「おもて」なら相手の対戦ポケモンが次の相手の番にワザを使えない（``ATTACK_PREVENTED``。状態・乱数・
        ログは変わらない）。にげる・トレーナーは制限しない。その番の終わりに消え、次の番からは使える。「うら」なら何もしない。"""
        for card in (RHYHORN, SABRINAS_DROWZEE):
            with self.subTest(card=card):
                state = board(mon(card))
                heads = attack_with(state, 0, 0, H)
                self.assertEqual(kinds(heads, len(state.log))[:3], ["attack", "coin_flip", "persistent_effect_added"])
                self.assertEqual(events(heads, len(state.log), "damage"), [])
                effect = cannot_attack(heads, heads.players[1].active)
                self.assertEqual((type(effect), effect.active_turn), (CannotAttack, TURN + 1))
                assert_rejected(self, heads, UseAttack(1, 0), "ATTACK_PREVENTED", IllegalActionError)
                passed = apply_kernel(apply_kernel(heads, EndTurn(1)), EndTurn(0))
                self.assertIsNone(cannot_attack(passed, passed.players[1].active))
                self.assertTrue(events(attack_with(passed, 1, 0), len(passed.log), "damage"))
                tails = attack_with(state, 0, 0, T)
                self.assertEqual(kinds(tails, len(state.log))[:3], ["attack", "coin_flip", "turn_end"])
                self.assertIsNone(cannot_attack(tails, tails.players[1].active))

    def test_barrier_stops_before_the_coin_and_prevented_damage_does_not(self):
        """「ワザをうけない」状態の相手には、コインが相手への効果だけを決めるので HC3（``UNRESOLVED_PREVENTED_EFFECT_COIN``）。「ダメージを受けない」
        状態（かたまる）の相手には、効果の要素は有効なのでコインを投げて効果を与える（p.321）。"""
        for card in (RHYHORN, SABRINAS_DROWZEE):
            with self.subTest(card=card):
                assert_stops(self, with_barrier(mon(card)), UseAttack(1, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")
                state = board(mon(card), mon(METAPOD, (GRASS,), prevent_damage=TURN - 1))
                heads = attack_with(state, 0, 0, H)
                self.assertIsNotNone(cannot_attack(heads, heads.players[1].active))

    def test_damage_attacks(self):
        """つのでつく 30・ずつき 20（説明文なし）。"""
        for card, index, amount in ((RHYHORN, 1, 30), (SABRINAS_DROWZEE, 1, 20)):
            with self.subTest(card=card):
                state = board(mon(card), mon(STARYU, ()))  # 弱点 雷・抵抗力なし
                self.assertEqual([e["amount"] for e in opponent_damage(attack_with(state, 0, index), len(state.log))], [amount])


class FossilGrimerTest(unittest.TestCase):
    """化石の秘密のベトベター（v0.8 の照合の記録の最新の説明で登録）。"""

    def test_sticky_paralysis_and_damage(self):
        """ベトベト: 10 のあとコインの「おもて」でマヒ（既存の ``ParalyzeOnHeads``）。「うら」ならマヒしない。"""
        state = board(mon(FOSSIL_GRIMER))
        heads = attack_with(state, 0, 0, H)
        self.assertEqual(kinds(heads, len(state.log))[:4], ["attack", "damage", "coin_flip", "special_condition"])
        self.assertTrue(heads.players[1].active.conditions.paralyzed)
        tails = attack_with(state, 0, 0, T)
        self.assertFalse(tails.players[1].active.conditions.paralyzed)
        self.assertEqual([e["amount"] for e in opponent_damage(tails, len(state.log))], [10])

    def test_minimize_reduces_attack_damage_only_on_the_next_opponent_turn(self):
        """ちいさくなる: 次の相手の番、このカードがワザによって受けるダメージを p.321 の 8 段階で 20 へらす（v0.31 の ``DamageReduction``）。ダメージ以外の
        効果は受ける（キャタピーの「いとをはく」のマヒ）。ポケモンチェックのどくのダメージは変えない（ワザではない）。その番の終わりに消える。"""
        state = board(mon(FOSSIL_GRIMER), mon(HITMONCHAN, (FIGHTING, FIGHTING, FIGHTING)))
        shrunk = attack_with(state, 0, 1)
        self.assertEqual(events(shrunk, len(state.log), "damage"), [])
        self.assertEqual(coins(shrunk, len(state.log)), [])
        effect = damage_reduction(shrunk, shrunk.players[0].active)
        self.assertEqual((type(effect), effect.amount, effect.active_turn), (DamageReduction, 20, TURN + 1))
        hit = attack_with(shrunk, 1, 1)  # スペシャルパンチ 40 → 8 段階で 20
        [damage] = opponent_damage(hit, len(shrunk.log))
        self.assertEqual((damage["amount"], damage["steps"][-1]), (20, ("8 ベトベター（damage_reduction）", 20)))
        self.assertIsNone(damage_reduction(hit, hit.players[0].active))  # はたらく番の終わりに消えた
        from tests.helpers import CATERPIE as _CATERPIE

        stringy = board(mon(FOSSIL_GRIMER), mon(_CATERPIE, (GRASS,)))
        shrunk = attack_with(stringy, 0, 1)
        spun = attack_with(shrunk, 1, 0, H)  # いとをはく 10 → 0。マヒは受ける
        self.assertEqual(spun.players[0].active.damage, 0)
        self.assertTrue(spun.players[0].active.conditions.paralyzed)
        poisoned = attack_with(board(mon(FOSSIL_GRIMER, poison=10)), 0, 1)
        self.assertEqual(poisoned.players[0].active.damage, 10)  # 効果を与えた番のポケモンチェックのどく（変えない）

    def test_minimize_is_removed_by_retreat_and_evolution(self):
        """ベンチにもどる（にげる）・進化すると消える（p.311・p.310・p.323）。化石の秘密のベトベターからは、名前が同じなのでベトベトンに進化できる。"""
        from tests.helpers import MUK

        state = board(mon(FOSSIL_GRIMER, (GRASS, GRASS), played_turn=1), hand=(MUK,))
        shrunk = attack_with(state, 0, 1)
        back = apply_kernel(shrunk, EndTurn(1))
        muk = next(uid for uid in back.players[0].hand if back.cards[uid].card_id == MUK)
        evolved = apply_kernel(back, EvolvePokemon(0, muk, back.players[0].active.pokemon_id))
        self.assertEqual(evolved.card_def(evolved.players[0].active.card).id, MUK)


class SandTest(unittest.TestCase):
    """ロケット団のイーブイの「すなかけ」（v0.36 の ``AttackCoinCheck``）・タケシのサンドの「すなじごく」（v0.36 の ``CannotRetreat``）。"""

    def test_eevee_sand_attack_flips_on_the_next_opponent_attack(self):
        """10 のあと相手に効果（「1回できえる」ではない書き方）。相手が次の番にワザを使うとき、コインの「うら」で失敗する。"""
        state = board(mon(ROCKET_EEVEE), mon(STARYU, (WATER,)))  # ヒトデマンの「たいあたり」20 ではイーブイはきぜつしない
        done = attack_with(state, 0, 1)
        [added] = events(done, len(state.log), "persistent_effect_added")
        self.assertEqual((added["persistent_effect"], added["single_use"], added["active_turn"]), ("attack_coin_check", False, TURN + 1))
        tails = attack_with(done, 1, 0, T)
        self.assertEqual(kinds(tails, len(done.log))[:4], ["attack", "coin_flip", "attack_check", "attack_failed"])
        heads = attack_with(done, 1, 0, H)
        self.assertEqual(kinds(heads, len(done.log))[:4], ["attack", "coin_flip", "attack_check", "damage"])
        self.assertEqual([e["reason"] for e in events(heads, len(done.log), "persistent_effect_removed")], ["expired"])

    def test_sandshrew_sand_pit_locks_retreat(self):
        """20 のあと相手は次の番に「にげる」ことができない（``RETREAT_PREVENTED``）。ワザは使える。次の番からはにげられる。"""
        state = board(mon(BROCKS_SANDSHREW))
        done = attack_with(state, 0, 0)
        self.assertEqual([e["amount"] for e in opponent_damage(done, len(state.log))], [20])
        from kyuura_engine import Retreat

        active = done.players[1].active
        retreat = Retreat(1, tuple(active.energy[:done.card_def(active.card).retreat_cost]), done.players[1].bench[0].card)
        assert_rejected(self, done, retreat, "RETREAT_PREVENTED", IllegalActionError)
        self.assertTrue(events(attack_with(done, 1, 0), len(done.log), "damage"))
        passed = apply_kernel(apply_kernel(done, EndTurn(1)), EndTurn(0))
        active = passed.players[1].active
        apply_kernel(passed, Retreat(1, tuple(active.energy[:passed.card_def(active.card).retreat_cost]), passed.players[1].bench[0].card))


class RaichuTest(unittest.TestCase):
    """ライチュウの「こうそくいどう」（v0.34 のギャロップと同じ ``DamageThenSelfBarrierOnHeads``）と「かみなり」（``SelfDamageOnTails``）。"""

    def test_agility_heads_blocks_damage_and_effects_on_the_next_opponent_turn(self):
        """20 のあと、コインの「おもて」で次の相手の番にワザによるダメージも効果も受けない（ねむりごなの 10 もねむりも受けない）。「うら」なら何もしない。"""
        state = board(mon(RAICHU), mon(KOGAS_TANGELA))
        heads = attack_with(state, 0, 0, H)
        self.assertEqual(kinds(heads, len(state.log))[:4], ["attack", "damage", "coin_flip", "persistent_effect_added"])
        barrier = attack_barrier(heads, heads.players[0].active)
        self.assertEqual((type(barrier), barrier.active_turn), (AttackBarrier, TURN + 1))
        hit = attack_with(heads, 1, 0)
        self.assertEqual(hit.players[0].active.damage, 0)
        self.assertEqual([len(events(hit, len(heads.log), k)) for k in ("damage_prevented", "effect_prevented", "special_condition")], [1, 1, 0])
        tails = attack_with(state, 0, 0, T)
        self.assertIsNone(attack_barrier(tails, tails.players[0].active))

    def test_thunder_tails_damages_itself(self):
        """かみなり: 60 のあとコインの「うら」で自分にも 30。「おもて」なら自分へのダメージはない。"""
        state = board(mon(RAICHU), mon(MACHOP, (FIGHTING,)), opponent_bench=(RATTATA,))
        tails = attack_with(state, 0, 1, T)
        self.assertEqual([(e.get("target"), e["amount"]) for e in events(tails, len(state.log), "damage")], [(None, 60), ("self", 30)])
        heads = attack_with(state, 0, 1, H)
        self.assertEqual([e.get("target") for e in events(heads, len(state.log), "damage")], [None])


class EarthquakeTest(unittest.TestCase):
    """ダグトリオの「じしん」: 相手に 70、自分の控えポケモン全員に 10。説明に「弱点・抵抗力」に関係なくがないので、読み方で受けるダメージが変わる
    ときだけ JS1 で止める。"""

    def test_bench_damage_and_own_pokemon_rules(self):
        """控えのポケモンが闘に弱点・抵抗力を持たなければ、相手に 70 → 控え全員に 10（自分のワザのダメージ。相手がサイドを取る対象になる）。
        プラスパワーは控えへのダメージを変えない・ディフェンダーは変える（v0.33 のミニじしんと同じ計算）。"""
        state = board(mon(DUGTRIO, trainers=[(PLUSPOWER, TURN)]), bench=(MACHOP, {"card": MACHOP, "trainers": [(DEFENDER, TURN + 1)]}))
        done = attack_with(state, 0, 1)
        damages = events(done, len(state.log), "damage")
        self.assertEqual([(e.get("target"), e["amount"]) for e in damages], [(None, 80), ("self_bench", 10), ("self_bench", 0)])
        self.assertEqual([p.damage for p in done.players[0].bench], [10, 0])

    def test_stops_when_weakness_or_resistance_would_change_the_damage(self):
        """控えに、闘に弱点（コラッタ ×2 で 20）・抵抗力（キョウのポッポ −30 で 0）を持つポケモンがいると、読み方で受けるダメージが変わるので、どの
        先読みの方法でも宣言の前に ``UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE`` で止める（状態・乱数・ログは変わらない）。"""
        for bench in ((RATTATA,), (KOGAS_PIDGEY,), (MACHOP, RATTATA)):
            with self.subTest(bench=bench):
                assert_stops(self, board(mon(DUGTRIO), bench=bench), UseAttack(0, 1), "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE")
        question = QUESTIONS["bench_damage_weakness_resistance"]
        self.assertEqual((question.code, question.rulings), ("UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE", ("JS1",)))

    def test_proceeds_when_both_readings_give_the_same_damage(self):
        """控えがいない・控えが闘に弱点・抵抗力を持たない・弱点があってもディフェンダーでどちらの読み方も 0 になるなら、止めない（読み方で結果が
        変わらない）。"""
        for bench in ((), (MACHOP,), ({"card": RATTATA, "trainers": [(DEFENDER, TURN + 1)]},)):
            with self.subTest(bench=bench):
                state = board(mon(DUGTRIO), bench=bench)
                done = attack_with(state, 0, 1)
                self.assertEqual(len([e for e in events(done, len(state.log), "damage") if e.get("target") == "self_bench"]), len(bench))

    def test_mini_earthquake_is_not_affected(self):
        """説明に「弱点・抵抗力」に関係なくのあるワザ（タケシのディグダの「ミニじしん」）は、控えに弱点のポケモンがいても止めない（v0.33 のまま）。"""
        from tests.helpers import BROCKS_DIGLETT

        state = board(mon(BROCKS_DIGLETT, (FIGHTING, FIGHTING)), bench=(RATTATA,))
        done = attack_with(state, 0, 1)
        self.assertEqual([e["amount"] for e in events(done, len(state.log), "damage") if e.get("target") == "self_bench"], [10])

    def test_slash(self):
        state = board(mon(DUGTRIO))
        self.assertEqual([e["amount"] for e in opponent_damage(attack_with(state, 0, 0), len(state.log))], [40])


class PoliwagLineTest(unittest.TestCase):
    """ニョロゾ（ドわすれ・おうふくびんた）・ニョロボン（みずでっぽう・うずしお）。"""

    def test_amnesia_decision_and_lock(self):
        """ドわすれ: ダメージはない。ワザを使ったプレイヤーが相手の対戦ポケモンのワザを 1 つ選ぶ（決定 ``select_opponent_attack``。選べるものは相手の
        ワザの位置）。選んだワザだけを次の相手の番に使えない（``ATTACK_LOCKED``）。ほかのワザは使え、その番の終わりに消える。"""
        state = board(mon(POLIWHIRL))
        waiting = attack_with(state, 0, 0)
        d = waiting.decision
        self.assertEqual((d.kind, d.player, d.options), ("select_opponent_attack", 0, (0, 1)))
        locked = apply_kernel(waiting, ResolveDecision(0, d.id, (1,)))
        [effect] = locked.players[1].active.persistent_effects
        self.assertEqual((type(effect), effect.attack_index, effect.target_attack_index, effect.active_turn), (CannotUseAttack, 0, 1, TURN + 1))
        assert_rejected(self, locked, UseAttack(1, 1), "ATTACK_LOCKED", IllegalActionError)
        other = attack_with(locked, 1, 0)
        self.assertEqual([e["reason"] for e in events(other, len(locked.log), "persistent_effect_removed")], ["expired"])

    def test_amnesia_invalid_answers_and_resume(self):
        """不正な答え（選ばない・2 つ・ない位置・相手のプレイヤー）は拒否し、決定は待ったまま（状態・乱数・ログは変わらない）。複製・保存してから
        答えても同じ結果。"""
        waiting = attack_with(board(mon(POLIWHIRL)), 0, 0)
        d = waiting.decision
        for player, choice in ((0, ()), (0, (0, 1)), (0, (2,)), (1, (0,))):
            with self.subTest(player=player, choice=choice):
                before = snapshot(waiting)
                with self.assertRaises(EngineError):
                    apply_kernel(waiting, ResolveDecision(player, d.id, choice))
                self.assertEqual(snapshot(waiting), before)
        answer = ResolveDecision(0, d.id, (0,))
        results = [apply_kernel(s, answer) for s in (waiting, waiting.clone(), copy.deepcopy(waiting), pickle.loads(pickle.dumps(waiting)))]
        self.assertEqual(len({str(snapshot(r)) for r in results}), 1)

    def test_double_slap(self):
        """おうふくびんた: コイン 2 枚の「おもて」の数 × 30（0・30・60）。"""
        for sides, amount in (((T, T), None), ((H, T), 30), ((H, H), 60)):
            with self.subTest(sides=sides):
                state = board(mon(POLIWHIRL), mon(HITMONCHAN, (FIGHTING,)))
                done = attack_with(state, 0, 1, *sides)
                self.assertEqual(len(coins(done, len(state.log))), 2)
                self.assertEqual(done.players[1].active.damage, amount or 0)

    def test_water_gun_follows_hc4(self):
        """みずでっぽう（水水無）30+: 第4弾のコダック・シャワーズと同じ ``ExtraEnergyDamageMixed``。多い「水」エネルギーの数が無色の払い方で変わるときだけ
        HC4（``UNRESOLVED_EXTRA_ENERGY_COLORLESS``）で止める（新しいコードにしていない）。「水」が必要な 2 つだけなら 30。"""
        for energy in ((WATER, WATER, WATER), (WATER, WATER, WATER, FIRE), (WATER,) * 4):
            with self.subTest(energy=energy):
                assert_stops(self, board(mon(POLIWRATH, energy)), UseAttack(0, 0), "UNRESOLVED_EXTRA_ENERGY_COLORLESS")
        # どちらの読み方でも同じなら止めない（「水」2 つ + ほかのタイプは追加なし。「水」5 つはどちらの読み方でも上限の 2 つぶん）
        for energy, amount in (((WATER, WATER, FIRE), 30), ((WATER, WATER, FIRE, FIRE), 30), ((WATER,) * 5, 50)):
            with self.subTest(energy=energy):
                state = board(mon(POLIWRATH, energy), mon(STARYU, ()))
                self.assertEqual([e["amount"] for e in opponent_damage(attack_with(state, 0, 0), len(state.log))], [amount])

    def test_whirlpool_discards_an_opponent_energy(self):
        """うずしお: 40 のあと、ワザを使ったプレイヤーが相手の対戦ポケモンのエネルギーカードを 1 枚選んでトラッシュ（コインなし）。エネルギーがなければ
        決定もトラッシュもない。相手がこのワザできぜつしたら効果を処理しない（p.309）。"""
        state = board(mon(POLIWRATH), mon(HITMONCHAN, (FIGHTING, PSYCHIC)))
        waiting = attack_with(state, 0, 1)
        d = waiting.decision
        self.assertEqual((d.kind, d.player, d.options), ("discard_opponent_energy", 0, tuple(state.players[1].active.energy)))
        done = apply_kernel(waiting, ResolveDecision(0, d.id, (d.options[1],)))
        self.assertEqual(done.players[1].active.energy, [state.players[1].active.energy[0]])
        self.assertIn(d.options[1], done.players[1].discard)
        self.assertEqual(coins(done, len(state.log)), [])
        bare = board(mon(POLIWRATH), mon(HITMONCHAN, ()))
        self.assertIsNone(attack_with(bare, 0, 1).decision)
        knocked = attack_with(board(mon(POLIWRATH), mon(HITMONCHAN, (FIGHTING,), damage=40)), 0, 1)
        self.assertEqual(knocked.decision.kind, "take_prize")


class StatusWithoutDamageTest(unittest.TestCase):
    """アーボの「どくえき」・タケシのイワークの「うなりごえ」（ダメージのないコインの特殊状態。v0.37 の型）と、ダメージのある同じ文面のワザ。"""

    def test_no_damage_heads_status_tails_nothing(self):
        """ダメージの要素がない（ログ ``damage`` なし）。コイン 1 枚の「おもて」でどく・マヒ、「うら」なら何もしない。"""
        for card, check in ((FOSSIL_EKANS, lambda p: p.conditions.poison is not None), (BROCKS_ONIX, lambda p: p.conditions.paralyzed)):
            with self.subTest(card=card):
                state = board(mon(card))
                heads = attack_with(state, 0, 0, H)
                self.assertEqual(kinds(heads, len(state.log))[:3], ["attack", "coin_flip", "special_condition"])
                self.assertTrue(check(heads.players[1].active))
                tails = attack_with(state, 0, 0, T)
                self.assertEqual(kinds(tails, len(state.log))[:3], ["attack", "coin_flip", "turn_end"])
                self.assertFalse(check(tails.players[1].active))

    def test_same_text_with_damage_uses_the_damage_type(self):
        """同じ説明の文面でも、ダメージの目安のあるワザ（アーボの「まきつく」20・化石の秘密のベトベターの「ベトベト」10）はダメージのあとにコイン
        （``ParalyzeOnHeads``）。ダメージのない型はダメージのあるワザを、ダメージのある型はダメージのないワザを受け付けない。"""
        self.assertEqual(printed(BROCKS_ONIX, 0).text_ja, printed(FOSSIL_EKANS, 1).text_ja)
        state = board(mon(FOSSIL_EKANS))
        heads = attack_with(state, 0, 1, H)
        self.assertEqual(kinds(heads, len(state.log))[:4], ["attack", "damage", "coin_flip", "special_condition"])
        self.assertTrue(E.ParalyzeOnHeadsWithoutDamage().check(printed(FOSSIL_EKANS, 1)))
        self.assertTrue(E.ParalyzeOnHeads().check(printed(BROCKS_ONIX, 0)))
        self.assertTrue(E.PoisonOnHeadsWithoutDamage().check(printed(BROCKS_ONIX, 0)))  # マヒの文面
        from tests.helpers import ROCKET_KOFFING

        self.assertTrue(E.PoisonOnHeadsWithoutDamage().check(printed(ROCKET_KOFFING, 0)))  # ダメージのないコインなしのどく（どくガス）

    def test_barrier_stops_and_prevented_damage_still_flips(self):
        """「ワザをうけない」状態の相手には HC3（コインが相手への効果だけを決める）。「ダメージを受けない」状態（かたまる）は効果を止めないので、コインを
        投げて特殊状態にする（p.321）。"""
        for card in (FOSSIL_EKANS, BROCKS_ONIX):
            with self.subTest(card=card):
                assert_stops(self, with_barrier(mon(card)), UseAttack(1, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")
                state = board(mon(card), mon(METAPOD, (GRASS,), prevent_damage=TURN - 1))
                heads = attack_with(state, 0, 0, H)
                self.assertTrue(heads.players[1].active.conditions.poison is not None or heads.players[1].active.conditions.paralyzed)

    def test_rock_throw_and_wrap_damage(self):
        state = board(mon(BROCKS_ONIX), mon(MACHOP, (FIGHTING,)))
        self.assertEqual([e["amount"] for e in opponent_damage(attack_with(state, 0, 1), len(state.log))], [30])


class DrawTest(unittest.TestCase):
    """ニャースの「ねこにこばん」（ダメージ → コイン → 引く）・キョウのモンジャラの「つるでさがす」（ダメージなし。コイン → 2 枚引く）。"""

    def test_cat_coin_damage_then_draw(self):
        """10 → コイン → 「おもて」なら山札の上から 1 枚引く（ログ ``draw``）。「うら」なら引かない。ダメージだけ・引くだけのワザとは別（順番は
        ダメージが先）。"""
        state = board(mon(MEOWTH))
        heads = attack_with(state, 0, 0, H)
        self.assertEqual(kinds(heads, len(state.log))[:4], ["attack", "damage", "coin_flip", "draw"])
        [drawn] = events(heads, len(state.log), "draw")[:1]
        self.assertEqual((drawn["player"], len(drawn["cards"])), (0, 1))
        self.assertEqual(len(heads.players[0].hand), len(state.players[0].hand) + 1)
        tails = attack_with(state, 0, 0, T)
        self.assertEqual(kinds(tails, len(state.log))[:4], ["attack", "damage", "coin_flip", "turn_end"])

    def test_vine_search_draws_two_on_heads(self):
        """ダメージはない。コインの「おもて」で 2 枚引く。「うら」なら引かない。"""
        state = board(mon(KOGAS_TANGELA))
        heads = attack_with(state, 0, 1, H)
        self.assertEqual(kinds(heads, len(state.log))[:3], ["attack", "coin_flip", "draw"])
        self.assertEqual(len(events(heads, len(state.log), "draw")[0]["cards"]), 2)
        self.assertEqual(events(heads, len(state.log), "damage"), [])
        tails = attack_with(state, 0, 1, T)
        self.assertEqual(kinds(tails, len(state.log))[:3], ["attack", "coin_flip", "turn_end"])

    def test_short_deck_draws_what_it_can(self):
        """山札が足りなければ引けるだけ引く（p.312。v0.2b のマサキと同じ）。0 枚でも負けではない（負けは番の最初に引けないときだけ）。"""
        for card, index, deck, expected in ((MEOWTH, 0, (), 0), (KOGAS_TANGELA, 1, (GRASS,), 1), (KOGAS_TANGELA, 1, (), 0)):
            with self.subTest(card=card, deck=len(deck)):
                state = board(mon(card), deck=deck)
                done = attack_with(state, 0, index, H)
                self.assertEqual(len(events(done, len(state.log), "draw")[0]["cards"]), expected)
                self.assertEqual(done.players[0].deck, [])
                self.assertIsNone(done.result)

    def test_draw_is_a_self_effect(self):
        """引くのは自分の効果なので、相手が「ワザをうけない」状態でもコインを投げて引く（相手へのダメージは無効）。相手がこのワザのダメージできぜつしても
        引く。"""
        barrier = with_barrier(mon(MEOWTH))
        done = attack_with(barrier, 1, 0, H)
        self.assertEqual(kinds(done, len(barrier.log))[:4], ["attack", "damage_prevented", "coin_flip", "draw"])
        barrier = with_barrier(mon(KOGAS_TANGELA))
        done = attack_with(barrier, 1, 1, H)
        self.assertEqual(kinds(done, len(barrier.log))[:3], ["attack", "coin_flip", "draw"])
        state = board(mon(MEOWTH), mon(HITMONCHAN, (FIGHTING,), damage=60))
        knocked = attack_with(state, 0, 0, H)
        self.assertEqual(kinds(knocked, len(state.log))[:5], ["attack", "damage", "coin_flip", "draw", "knock_out"])

    def test_sleep_powder(self):
        """ねむりごな: 10 のあとコインなしでねむり（v0.9 の ``SleepOpponent``）。"""
        state = board(mon(KOGAS_TANGELA))
        done = attack_with(state, 0, 0, T)  # 「うら」はポケモンチェックのねむりのコイン（さめない）
        self.assertEqual([e["source"] for e in events(done, len(state.log), "coin_flip")], ["pokemon_check"])
        self.assertEqual(kinds(done, len(state.log))[:3], ["attack", "damage", "special_condition"])
        self.assertTrue(done.players[1].active.conditions.asleep)


class PlayDeadTest(unittest.TestCase):
    """カスミのコイキングの「しんだふり」（ダメージなし。コインの「おもて」で ``AttackBarrier``）と「はねる」。"""

    def test_heads_blocks_damage_and_effects(self):
        """ダメージはない。「おもて」で次の相手の番にワザによるダメージも効果も受けない（ねむりごなの 10 もねむりも受けない）。「ダメージを受けない」
        効果（かたまる。効果は受ける）とは別。「うら」なら何もしない。"""
        state = board(mon(MISTYS_MAGIKARP), mon(KOGAS_TANGELA))
        heads = attack_with(state, 0, 0, H)
        self.assertEqual(kinds(heads, len(state.log))[:3], ["attack", "coin_flip", "persistent_effect_added"])
        self.assertEqual(events(heads, len(state.log), "damage"), [])
        self.assertIsNotNone(attack_barrier(heads, heads.players[0].active))
        self.assertIsNone(damage_prevention(heads, heads.players[0].active))
        hit = attack_with(heads, 1, 0)
        self.assertEqual(hit.players[0].active.damage, 0)
        self.assertEqual([len(events(hit, len(heads.log), k)) for k in ("damage_prevented", "effect_prevented", "special_condition")], [1, 1, 0])
        tails = attack_with(state, 0, 0, T)
        self.assertIsNone(attack_barrier(tails, tails.players[0].active))
        hardened = apply_kernel(board(mon(METAPOD, (GRASS,), prevent_damage=TURN), mon(KOGAS_TANGELA)), EndTurn(0))
        hit = attack_with(hardened, 1, 0)  # かたまる: ダメージは受けないが、ねむりは受ける
        self.assertEqual(hit.players[0].active.damage, 0)
        self.assertEqual([len(events(hit, len(hardened.log), k)) for k in ("damage_prevented", "effect_prevented", "special_condition")], [1, 0, 1])

    def test_splash(self):
        state = board(mon(MISTYS_MAGIKARP))
        self.assertEqual([e["amount"] for e in opponent_damage(attack_with(state, 0, 1), len(state.log))], [10])


class BiteTest(unittest.TestCase):
    """ペルシアンの「かみつく」（v0.34 のなきつくと同じ ``ReducedDamageToSource``。ダメージのあとに与える）と「ひっかく」（効果なし）。"""

    def test_damage_then_reduction_for_this_card_only(self):
        """30 のあと、相手の対戦ポケモンがこのカードにワザでダメージを与えるとき p.321 の 2 段階（弱点の前）で 10 へる。ペルシアン以外へのダメージは
        変えない。効果はペルシアンの持ち主の次の番の始めに消える。"""
        state = board(mon(PERSIAN))
        bitten = attack_with(state, 0, 1)
        self.assertEqual(kinds(bitten, len(state.log))[:3], ["attack", "damage", "persistent_effect_added"])
        effect = reduced_damage_to_source(bitten, bitten.players[1].active)
        self.assertEqual((type(effect), effect.amount, effect.active_turn), (ReducedDamageToSource, 10, TURN + 1))
        hit = attack_with(bitten, 1, 0)
        [damage] = opponent_damage(hit, len(bitten.log))  # ジャブ 20 → 2 段階で 10 → ペルシアンの弱点（闘）で 20
        self.assertEqual(damage["steps"][:3], (("1 基本となる計算", 20), ("2 ペルシアン（reduced_damage_to_source）", 10), ("3 弱点", 20)))
        self.assertEqual(damage["amount"], 20)
        start = next(i for i, e in enumerate(hit.log) if e["kind"] == "turn_start" and e["turn"] == TURN + 2)
        self.assertEqual((hit.log[start + 1]["kind"], hit.log[start + 1]["reason"]), ("persistent_effect_removed", "expired"))

    def test_other_pokemon_takes_full_damage(self):
        """ペルシアンがベンチにもどったあと（にげる）、バトル場の別のポケモンへのダメージは変えない。"""
        from kyuura_engine import Retreat

        state = board(mon(PERSIAN))
        bitten = attack_with(state, 0, 1)
        back = apply_kernel(bitten, EndTurn(1))
        moved = apply_kernel(back, Retreat(0, (), back.players[0].bench[0].card))
        passed = apply_kernel(moved, EndTurn(0))
        hit = attack_with(passed, 1, 0)
        self.assertEqual([e["amount"] for e in opponent_damage(hit, len(passed.log))], [40])  # コラッタ（弱点 闘）: 20 × 2

    def test_not_given_when_knocked_out_or_protected(self):
        """相手がこのワザで HP 以上になったら効果を与えない（p.309）。「ワザをうけない」相手には効果の要素も無効。ひっかくは効果なし。"""
        state = board(mon(PERSIAN), mon(HITMONCHAN, (FIGHTING,), damage=40))
        knocked = attack_with(state, 0, 1)
        self.assertEqual(kinds(knocked, len(state.log))[:3], ["attack", "damage", "knock_out"])
        self.assertEqual(events(knocked, len(state.log), "persistent_effect_added"), [])
        barrier = with_barrier(mon(PERSIAN))
        done = attack_with(barrier, 1, 1)
        self.assertIsNone(reduced_damage_to_source(done, done.players[0].active))
        self.assertTrue(events(done, len(barrier.log), "effect_prevented"))
        scratch = attack_with(board(mon(PERSIAN)), 0, 0)
        self.assertIsNone(reduced_damage_to_source(scratch, scratch.players[1].active))


class CopyTest(unittest.TestCase):
    """相手のワザを自分のワザとして使う効果（ピッピの「ゆびをふる」）で、v0.37 のワザを使う。"""

    def copy(self, defender, choice, *sides):
        state = board(mon(CLEFAIRY, (PSYCHIC, PSYCHIC, PSYCHIC)), defender)
        waiting = play(state, UseAttack(0, 1))
        return state, waiting, ResolveDecision(0, waiting.decision.id, (choice,)), sides

    def test_copying_amnesia_is_rejected_and_the_decision_waits(self):
        """ニョロゾの「ドわすれ」をまねるのはエンジンの未対応（v0.36 の ``OpponentAttackLock.copy_problem``。内部エラーではなく
        ``UNSUPPORTED_COPIED_ATTACK``）。決定は待ったままで、おうふくびんたは選べる。"""
        _, waiting, answer, _ = self.copy(mon(POLIWHIRL), 0)
        assert_rejected(self, waiting, answer, "UNSUPPORTED_COPIED_ATTACK")
        done = apply_kernel(with_coin_results(waiting, H, H), ResolveDecision(0, waiting.decision.id, (1,)))
        self.assertEqual([e["amount"] for e in opponent_damage(done, len(waiting.log))], [60])

    def test_copied_self_effects_go_to_the_copier(self):
        """まねた「しんだふり」「ちいさくなる」は、ワザを使ったポケモン（ピッピ）に効果を与える。まねた「かみつく」の効果は相手が受け、発生源は
        ピッピ。まねた「つるでさがす」はピッピの持ち主が引く。"""
        for defender, choice, check in ((mon(MISTYS_MAGIKARP), 0, lambda s: attack_barrier(s, s.players[0].active)),
                                        (mon(FOSSIL_GRIMER), 1, lambda s: damage_reduction(s, s.players[0].active)),
                                        (mon(PERSIAN), 1, lambda s: reduced_damage_to_source(s, s.players[1].active))):
            with self.subTest(defender=defender["card"]):
                state, waiting, answer, _ = self.copy(defender, choice)
                done = apply_kernel(with_coin_results(waiting, H), answer)
                effect = check(done)
                self.assertIsNotNone(effect)
                self.assertEqual(effect.source_card, state.players[0].active.card)
                self.assertEqual(check_invariants(done), [])
        state, waiting, answer, _ = self.copy(mon(KOGAS_TANGELA), 1)
        done = apply_kernel(with_coin_results(waiting, H), answer)
        self.assertEqual(events(done, len(waiting.log), "draw")[0]["player"], 0)

    def test_psyduck_copies_earthquake_and_bench_reading(self):
        """カスミのコダックの「ちょうのうりょく」（「おもて」3 枚）でまねた「じしん」は、ワザを使ったポケモン（水）のタイプで JS1 を確かめる。控えに
        水の弱点のヒトカゲがいれば、「おもて」3 枚の先のワザでも宣言の前に止める。闘の弱点のコラッタは読み方で変わらないので止めず、控えに 10。"""
        from tests.helpers import CHARMANDER

        assert_stops(self, board(mon(MISTYS_PSYDUCK, (PSYCHIC,)), mon(DUGTRIO), bench=(CHARMANDER,)), UseAttack(0, 0),
                     "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE")
        state = board(mon(MISTYS_PSYDUCK, (PSYCHIC,)), mon(DUGTRIO), bench=(RATTATA,))
        waiting = attack_with(state, 0, 0, H, H, H)
        done = apply_kernel(waiting, ResolveDecision(0, waiting.decision.id, (1,)))
        self.assertEqual([e["amount"] for e in events(done, len(state.log), "damage") if e.get("target") == "self_bench"], [10])


class EvolutionTest(unittest.TestCase):
    """進化元は「○○から進化」と名前が完全に一致するポケモン（収録の弾で制限しない）。"""

    def test_evolution_by_exact_name(self):
        for evolved, below in ((RAICHU, PIKACHU), (DUGTRIO, DIGLETT), (POLIWHIRL, POLIWAG), (PERSIAN, MEOWTH)):
            with self.subTest(card=evolved):
                state = board(mon(below, (), played_turn=1), hand=(evolved,))
                done = apply_kernel(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].active.pokemon_id))
                self.assertEqual(done.card_def(done.players[0].active.card).id, evolved)
        state = board(mon(POLIWHIRL, (), played_turn=1, evolved_turn=2), hand=(POLIWRATH,))
        done = apply_kernel(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].active.pokemon_id))
        self.assertEqual(done.card_def(done.players[0].active.card).id, POLIWRATH)
        pool = load_card_pool()
        self.assertEqual(pool.get(PERSIAN).evolves_from, pool.get(MEOWTH).name_ja)
        from tests.helpers import GIOVANNIS_MEOWTH

        rejected = board(mon(GIOVANNIS_MEOWTH, (), played_turn=1), hand=(PERSIAN,))  # サカキのニャースは名前が違う
        with self.assertRaises(EngineError):
            apply_kernel(rejected, EvolvePokemon(0, rejected.players[0].hand[0], rejected.players[0].active.pokemon_id))


class IntegrityTest(unittest.TestCase):
    """不変条件・書き出し・拒否の原子性。"""

    def test_serialization_of_the_effects(self):
        """v0.37 のワザが与える持続する効果（どれも既存の型）は形式 8 から書き出せ、書き出しの監査が通る。"""
        waiting = attack_with(board(mon(POLIWHIRL)), 0, 0)
        cases = [attack_with(board(mon(RHYHORN)), 0, 0, H), attack_with(board(mon(FOSSIL_GRIMER)), 0, 1),
                 attack_with(board(mon(MISTYS_MAGIKARP)), 0, 0, H), attack_with(board(mon(PERSIAN)), 0, 1),
                 apply_kernel(waiting, ResolveDecision(0, waiting.decision.id, (0,)))]
        for state in cases:
            with self.subTest(effects=[type(e).__name__ for p in state.players for e in (p.active.persistent_effects if p.active else ())]):
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(serialization_problems(state), [])
                state_to_dict(state, format_version=8)
                with self.assertRaises(ValueError):
                    state_to_dict(state, format_version=7)

    def test_rejections_keep_the_state_in_every_mode(self):
        """拒否（JS1・HC3・HC4・ドわすれを受けたワザ）は、どの先読みの方法でも状態・乱数・ログを変えない。"""
        assert_stops(self, board(mon(DUGTRIO), bench=(RATTATA,)), UseAttack(0, 1), "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE")
        assert_stops(self, with_barrier(mon(FOSSIL_EKANS)), UseAttack(1, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")
        assert_stops(self, board(mon(POLIWRATH, (WATER,) * 3)), UseAttack(0, 0), "UNRESOLVED_EXTRA_ENERGY_COLORLESS")
        waiting = attack_with(board(mon(POLIWHIRL)), 0, 0)
        locked = apply_kernel(waiting, ResolveDecision(0, waiting.decision.id, (0,)))
        assert_stops(self, locked, UseAttack(1, 0), "ATTACK_LOCKED", exception=IllegalActionError)

    def test_coin_count_and_rng(self):
        """コインの数は説明のとおり（ダメージのないワザも 1 枚）。乱数はコインだけに使う（コインのないワザは乱数を変えない）。"""
        for (card, index), count in (((RHYHORN, 0), 1), ((FOSSIL_EKANS, 0), 1), ((BROCKS_ONIX, 0), 1), ((MEOWTH, 0), 1), ((KOGAS_TANGELA, 1), 1),
                                     ((MISTYS_MAGIKARP, 0), 1), ((POLIWHIRL, 1), 2), ((RAICHU, 0), 1), ((RAICHU, 1), 1),
                                     ((FOSSIL_GRIMER, 0), 1), ((FOSSIL_GRIMER, 1), 0), ((KOGAS_TANGELA, 0), 0), ((PERSIAN, 1), 0), ((DUGTRIO, 1), 0)):
            with self.subTest(card=card, index=index):
                state = board(mon(card), mon(MACHOP, (FIGHTING,)), bench=(MACHOP,))
                done = attack_with(state, 0, index, *([H] * count))
                self.assertEqual(len([e for e in events(done, len(state.log), "coin_flip") if e["source"] == "attack"]), count)
                if not events(done, len(state.log), "coin_flip"):  # ねむりごなはポケモンチェックのねむりのコインを使う
                    self.assertEqual(rng_fingerprint(apply_kernel(state, UseAttack(0, index)).rng), rng_fingerprint(state.rng))


class PreflightParityTest(unittest.TestCase):
    """28 のワザで、先読みの方法（``derived``・``derived_full``・``legacy``）の結果（状態・乱数・ログ、または拒否の型・コード・理由の文）が同じ。"""

    def test_every_attack(self):
        for (card, index) in EXPECTED:
            for sides in ((H,) * 4, (T,) * 4):
                for bench in ((MACHOP,), (RATTATA,)):
                    with self.subTest(card=card, index=index, sides=sides[0], bench=bench):
                        state = board(mon(card), mon(HITMONCHAN, (FIGHTING, FIGHTING)), bench=bench)
                        results = set()
                        for mode in PREFLIGHT_MODES:
                            try:
                                results.add(str(snapshot(attack_with(state, 0, index, *sides, mode=mode))))
                            except EngineError as error:
                                results.add((type(error).__name__, error.code, str(error)))
                        self.assertEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()
