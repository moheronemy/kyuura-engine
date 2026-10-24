"""v0.34: バリアーに対するコインの扱いの見直し・ダメージのあとの決定をまたぐ処理と、14 枚（docs/barrier-resume-coin-bonus-v0.34.md）。

カードごとに同じテストを書かず、共通の仕組みの境界（``BarrierCoinTest``・``CarryAcrossDecisionTest``・``SpecialPoisonTest``・``GrowlTest``）と、
カードごとの処理（``CoinBonusOrSelfDamageTest`` ほか）と、カードごとの登録の確かめ（``CardDataTest``）と、すべてのワザの先読みの方法ごとの一致
（``PreflightParityTest``）に分けた。

根拠はどれも kyuura データの採用（kyuura の印刷の文面。``card_sources.json``）と、既存の記録（p.309 の手順 6 と「処理の対象がなくなってしまっている
場合」、p.320 のダメージ・効果の分類、p.321 の計算の段階と「ダメージを受けない」状態、p.322 の特殊状態（docs/special-conditions-v0.3a.md の 13〜15）、
p.323 のワザの失敗、p.89 の「ダメージを受けたとき」の効果の時点、kyuura の UQ-COIN-IN-NULLIFIED-ELEMENT・CR-STICKY-VS-PREVENTED・
RUL-ENERGY-DISCARD-ATTACKS）の再利用。ガイドブックは読んでいない。
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import pickle
import unittest

from kyuura_engine import (
    EngineError,
    EvolvePokemon,
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    apply_command,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, read_extract
from kyuura_engine.conditions import NORMAL_POISON
from kyuura_engine.decisions import BENCH_FROM_DECK, DISCARD_ENERGY, SELECT_ATTACK, SELECT_POKEMON
from kyuura_engine.engine import check_invariants
from kyuura_engine.persistent import attack_barrier, reduced_damage_to_source
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import PERSISTENT_EFFECT_TYPES, Poison, ReducedDamageToSource
from scripts import check_card_sources as cs
from scripts.extract_kyuura_cards import PREVIOUS_KYUURA_COMMIT as ADOPTED_COMMIT  # v0.69: 採用したときのデータのコミット（採用の記録は書き換えない）
from tests.helpers import (
    kyuura_records_since_v0_69,
    BLAINES_KANGASKHAN,
    BLAINES_RHYHORN,
    BROCKS_VULPIX,
    CHARMANDER,
    CLEFAIRY,
    CUBONE,
    DIGLETT,
    EEVEE,
    ELECTABUZZ,
    EXEGGCUTE,
    EXEGGUTOR,
    FIGHTING,
    FIRE,
    FLAREON,
    GIOVANNIS_MACHOKE,
    GIOVANNIS_MACHOP,
    GIOVANNIS_PINSIR,
    GRASS,
    GRIMER,
    GUST,
    HAUNTER,
    GASTLY,
    HITMONCHAN,
    JOLTEON,
    KANGASKHAN,
    KOFFING,
    LIGHTNING,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MAROWAK,
    METAPOD,
    CATERPIE,
    MEWTWO,
    NIDOKING,
    NIDORAN_M,
    NIDORINA,
    NIDORAN_F,
    NIDORINO,
    NINETALES,
    PINSIR,
    PONYTA,
    PSYCHIC,
    RAPIDASH,
    RATTATA,
    ROCKET_PONYTA,
    SCYTHER,
    TAUROS,
    V0_34_POKEMON,
    V0_34_POOL,
    VAPOREON,
    VULPIX,
    WATER,
    WEEDLE,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
TURN = 7
DOC = ROOT / "docs" / "barrier-resume-coin-bonus-v0.34.md"
# 進化しているカードの下のカード
BELOW = {RAPIDASH: PONYTA, FLAREON: EEVEE, VAPOREON: EEVEE, JOLTEON: EEVEE, NIDOKING: [NIDORAN_M, NIDORINO], EXEGGUTOR: EXEGGCUTE,
         MAROWAK: CUBONE, NIDORINO: NIDORAN_M, MACHAMP: [MACHOP, MACHOKE], GIOVANNIS_MACHOKE: GIOVANNIS_MACHOP, HAUNTER: GASTLY,
         METAPOD: CATERPIE}
# 登録の実装の型（カード id, ワザの位置）
EXPECTED = {
    (RAPIDASH, 0): (E.CoinBonusDamage, {"bonus": 10}),
    (RAPIDASH, 1): (E.DamageThenSelfBarrierOnHeads, {}),
    (FLAREON, 0): (E.CoinBonusDamage, {"bonus": 20}),
    (FLAREON, 1): (E.DiscardEnergyBeforeDamage, {"energy_type": EnergyType.FIRE, "count": 1, "timing": "effect", "when_lacking": "fail"}),
    (VAPOREON, 0): (E.CoinBonusDamage, {"bonus": 20}),
    (VAPOREON, 1): (E.ExtraEnergyDamageMixed, {"energy_type": EnergyType.WATER, "per_energy": 10, "max_extra": 2}),
    (JOLTEON, 0): (E.CoinBonusDamage, {"bonus": 20}),
    (JOLTEON, 1): (E.CoinFlipDamage, {"coins": 4, "damage_per_heads": 20}),
    (ELECTABUZZ, 0): (E.ParalyzeOnHeads, {}),
    (ELECTABUZZ, 1): (E.CoinBonusOrSelfDamage, {"bonus": 10, "self_damage": 10}),
    (TAUROS, 0): (E.CoinBonusDamage, {"bonus": 10}),
    (TAUROS, 1): (E.DamagePlusOwnCountersThenSelfConfuseOnTails, {"per": 10}),
    (BROCKS_VULPIX, 0): (E.DamageOnly, {}),
    (BROCKS_VULPIX, 1): (E.CoinBonusDamage, {"bonus": 20}),
    (GIOVANNIS_PINSIR, 0): (E.CoinBonusDamage, {"bonus": 20}),
    (GIOVANNIS_PINSIR, 1): (E.DamageThenCoinOwnBenchDamage, {"bench_damage": 20}),
    (BLAINES_KANGASKHAN, 0): (E.FailOnTailsDamage, {"coins": 1}),
    (BLAINES_KANGASKHAN, 1): (E.CoinBonusDamage, {"bonus": 10}),
    (KOFFING, 0): (E.DamageThenPoisonOrConfuse, {}),
    (NIDOKING, 0): (E.CoinBonusOrSelfDamage, {"bonus": 10, "self_damage": 10}),
    (NIDOKING, 1): (E.DamageAndSpecialPoison, {"poison_damage": 20}),
    (EXEGGUTOR, 0): (E.SwitchSelfWithBench, {}),
    (EXEGGUTOR, 1): (E.CoinsPerAttachedEnergyDamage, {"per": 20}),
    (CUBONE, 0): (E.ReduceDamageToSelf, {"amount": 20}),
    (CUBONE, 1): (E.DamagePlusOwnCounters, {"per": 10}),
    (MAROWAK, 0): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 30}),
    (MAROWAK, 1): (E.PutTypeBasicFromDeckOntoBench, {"pokemon_type": EnergyType.FIGHTING}),
}
# pcg-search.com の対象の版（サイトの一覧の番号）
EDITIONS = {
    RAPIDASH: "019/048", FLAREON: "020/048", VAPOREON: "023/048", JOLTEON: "026/048", ELECTABUZZ: "041/096", TAUROS: "045/048",
    BROCKS_VULPIX: "018/096", GIOVANNIS_PINSIR: "024/098", BLAINES_KANGASKHAN: "069/098", KOFFING: "012/096", NIDOKING: "011/096",
    EXEGGUTOR: "016/048", CUBONE: "030/048", MAROWAK: "031/048",
}
# ワザに必要なエネルギーを払うエネルギーカード（無色は 1 つめのタイプで払う）
ENERGY = {EnergyType.FIRE: FIRE, EnergyType.WATER: WATER, EnergyType.LIGHTNING: LIGHTNING, EnergyType.GRASS: GRASS, EnergyType.PSYCHIC: PSYCHIC,
          EnergyType.FIGHTING: FIGHTING}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, opponent=None, *, bench=(), opponent_bench=(RATTATA,), hand=(), opponent_hand=(), deck=None, turn=TURN):
    me = {"active": active, "bench": list(bench), "hand": list(hand)}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent or mon(HITMONCHAN, (FIGHTING,)), "bench": list(opponent_bench), "hand": list(opponent_hand)}
    return build_test_state([me, them], turn_number=turn)


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


def first(d):
    return tuple(d.options[:1])


def events(state, since, kind=None):
    return [dict(e) for e in state.log[since:] if kind is None or e["kind"] == kind]


def kinds(state, since):
    return [e["kind"] for e in state.log[since:]]


def coins(state, since):
    return [e["result"] for e in events(state, since, "coin_flip")]


def assert_stops(test, state, command, code, *, exception=UnsupportedError):
    """どの先読みの方法でも ``code`` で拒否し、状態・乱数・ログが変わらない（宣言の前に止める）。"""
    snapshot = (full(state), rng_fingerprint(state.rng), len(state.log))
    for mode in PREFLIGHT_MODES:
        with test.subTest(mode=mode), test.assertRaises(exception) as raised:
            apply_kernel(state, command, preflight=mode)
        test.assertEqual(raised.exception.code, code)
    test.assertEqual((full(state), rng_fingerprint(state.rng), len(state.log)), snapshot)


def with_barrier(attacker, *, attacker_bench=(RATTATA,)):
    """相手（プレイヤー 1）の対戦ポケモンを「ワザをうけない」状態（ミュウツーの「バリアー」。v0.31 の ``AttackBarrier``）にしてから、プレイヤー 1 の番に
    する。``attacker`` はバリアーのあとにワザを使うプレイヤー 1 のポケモン。"""
    state = build_test_state([
        {"active": mon(MEWTWO, (PSYCHIC, PSYCHIC, PSYCHIC)), "bench": [RATTATA]},
        {"active": attacker, "bench": list(attacker_bench)},
    ], turn_number=TURN)
    return play(state, UseAttack(0, 1), [first])


def counter_board(attacker, *, attacker_bench=(RATTATA,), machamp_damage=0):
    """プレイヤー 0 のワザを使うポケモンが、はたらいている「はんげき」を持つカイリキー（PMCG1-057）にワザを使う盤面。"""
    return board(attacker, mon(MACHAMP, (FIGHTING,), damage=machamp_damage), bench=attacker_bench)


def cost_energy(card, index):
    """ワザに必要なエネルギーちょうどのエネルギーカード。無色は、そのワザの色のエネルギーと別のタイプで払う（シャワーズのみずでっぽうの HC4 を
    起こさない）。"""
    attack = load_card_pool().get(card).attacks[index]
    typed = {t for t in attack.cost if t is not EnergyType.COLORLESS}
    other = EnergyType.FIGHTING if EnergyType.FIGHTING not in typed else EnergyType.PSYCHIC
    return [ENERGY[other if t is EnergyType.COLORLESS else t] for t in attack.cost]


class CardDataTest(unittest.TestCase):
    """14 枚の登録・写し・採用の記録・進化の関係と、保留のガルーラ。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_fourteen_cards_and_kangaskhan_is_on_hold(self):
        """対象は依頼の 15 枚（ほかの候補に広げていない）。写しの組 pool_v0_34 は 15 枚で、14 枚は対戦に使える。ガルーラ（PMCG2-046）は pcg-search.com
        との照合で挙動に影響する違いがあるので保留（登録しない・対戦に使えない）。"""
        self.assertEqual(len(V0_34_POKEMON), 14)
        self.assertEqual(list(read_extract()["pool_v0_34"]), list(V0_34_POOL))
        self.assertEqual(set(V0_34_POOL) - set(V0_34_POKEMON), {KANGASKHAN})
        for card in V0_34_POKEMON:
            with self.subTest(card=card):
                self.assertTrue(self.pool.is_playable(card))
        # v0.68: 利用者が示した修正（こどものおつかいにコインはない）を写しに当てはめ、保留を解いた（docs/final-pmcg-cards-v0.68.md 2 章）
        self.assertTrue(self.pool.is_playable(KANGASKHAN))
        self.assertEqual(len([k for k in E.DEFAULT_EFFECTS.attack_keys() if k.card_id == KANGASKHAN]), 2)

    def test_every_attack_is_registered_with_the_expected_type(self):
        """27 のワザがどれも登録され、型と値が表のとおり。名前・文面は写しと同じで、処理に使う文面は kyuura の印刷の文面（説明文のあるワザ）。特殊能力を
        持つカードはない。"""
        seen = set()
        for card in V0_34_POKEMON:
            definition = self.pool.get(card)
            self.assertEqual(definition.powers, ())
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
        self.assertEqual(len(seen), 27)

    def test_adoption_records(self):
        """14 枚はどれも kyuura データの採用の記録（adopted。研究の基準のコミットにこれらのカードを指す kyuura の記録はない）と pcg-search.com の照合（同じ版の
        一覧の番号）を持ち、過去の原典照合の記録には加えていない。違いはサンダースの「ミサイルばり」（サイトの脱字）とケンタロスの「【自分】」の書き方の
        2 件で、どちらも処理に影響しない。ガルーラは挙動に影響する違い（こどものおつかいのコイン）で保留。"""
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        verification = (ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8")
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        adopted = set(links["latest_descriptions"]["adopted_printed_text"])
        differences = {}
        for card in V0_34_POKEMON:
            record = sources[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]), ("kyuura_data", "adopted", ADOPTED_COMMIT))
                self.assertEqual(record["kyuura_records"], kyuura_records_since_v0_69(card))  # v0.69: 研究の基準を上げて加わった kyuura の記録（tests/helpers.py の V0_69_KYUURA_RECORDS_ADDED）
                self.assertNotIn(f'"{card}"', verification)
                [check] = record["external_checks"]
                self.assertEqual((check["site"], check["edition"]["list_number"]), ("pcg-search.com", EDITIONS[card]))
                self.assertFalse(any(d["affects_behavior"] for d in check["differences"]))
                differences[card] = [d["field"] for d in check["differences"]]
                for attack in self.pool.get(card).attacks:
                    key = f"attack/{attack.index}"
                    if attack.text_ja is not None:
                        self.assertEqual(record["play_text"][key], "kyuura_printed_text")
                        self.assertIn(f"{card}/{key}", adopted)
                    else:
                        self.assertNotIn(key, record["play_text"])
        self.assertEqual({card: fields for card, fields in differences.items() if fields},
                         {JOLTEON: ["pokemon.attacks[1].text.ja"], TAUROS: ["pokemon.attacks[1].text.ja"]})
        # v0.68: 保留したガルーラは、利用者が示した訂正（写しの作り直しの USER_PROVIDED_CORRECTIONS）を当てはめて採用した。外部照合の記録（違いの記録）は変えていない
        hold = sources[KANGASKHAN]
        self.assertEqual((hold["status"], hold["play_text"]),
                         ("adopted", {"attack/0": "user_provided_correction", "attack/1": "kyuura_printed_text"}))
        [check] = hold["external_checks"]
        self.assertEqual(check["edition"]["list_number"], "044/048")
        self.assertEqual([d["field"] for d in check["differences"] if d["affects_behavior"]], ["pokemon.attacks[0].text.ja"])
        self.assertEqual(hold["issues"], [])

    def test_evolution_by_exact_name(self):
        """進化先 7 枚は、進化元の名前と完全に一致するポケモンからだけ、通常の進化の操作で進化する（ギャロップは第1弾・第4弾のどちらのポニータからも。
        ニドキングは 1 進化のニドリーノから）。名前の違うカードからは進化できない（ニドリーナ → ニドキング・タケシのロコン → キュウコン）。"""
        pairs = [(RAPIDASH, PONYTA, None), (RAPIDASH, ROCKET_PONYTA, None), (FLAREON, EEVEE, None), (VAPOREON, EEVEE, None), (JOLTEON, EEVEE, None),
                 (EXEGGUTOR, EXEGGCUTE, None), (MAROWAK, CUBONE, None), (NIDOKING, NIDORINO, NIDORAN_M)]
        for upper, below, base in pairs:
            with self.subTest(upper=upper, below=below):
                self.assertEqual(self.pool.get(upper).evolves_from, self.pool.get(below).name_ja)
                spec = mon(below, played_turn=1, **({"evolved_from": base, "evolved_turn": 3} if base else {}))
                state = board(mon(RATTATA), bench=[spec], hand=[upper])
                new = apply_command(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].bench[0].pokemon_id))
                self.assertEqual(new.cards[new.players[0].bench[0].card].card_id, upper)
        for upper, below in ((NIDOKING, NIDORINA), (NINETALES, BROCKS_VULPIX), (MAROWAK, DIGLETT)):
            spec = mon(below, played_turn=1, **({"evolved_from": NIDORAN_F, "evolved_turn": 3} if below == NIDORINA else {}))
            state = board(mon(RATTATA), bench=[spec], hand=[upper])
            with self.subTest(upper=upper, below=below), self.assertRaises(IllegalActionError) as raised:
                apply_command(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].bench[0].pokemon_id))
            self.assertEqual(raised.exception.code, "EVOLUTION_NAME_MISMATCH")

    def test_same_name_cards_keep_separate_registrations(self):
        """タケシのロコン・サカキのカイロス・カツラのガルーラは、名前の似た別のカード（ロコン・カイロス・ガルーラ）と別の登録（カード id で引く）。"""
        for new, old in ((BROCKS_VULPIX, VULPIX), (GIOVANNIS_PINSIR, PINSIR), (BLAINES_KANGASKHAN, KANGASKHAN)):
            with self.subTest(new=new):
                self.assertNotEqual(self.pool.get(new).name_ja, self.pool.get(old).name_ja)
                self.assertNotEqual([a.name_ja for a in self.pool.get(new).attacks], [a.name_ja for a in self.pool.get(old).attacks])


class BarrierCoinTest(unittest.TestCase):
    """1 部: 「ワザをうけない」状態（バリアー）の相手へのコイン。コインが決めるものが、どれも相手の対戦ポケモンへのダメージ・効果の要素で、それが無効なら、
    投げるかが決められない（ダメージだけなら v0.4b の ``UNRESOLVED_PREVENTED_COIN_DAMAGE``、効果を含むなら HC3 の ``UNRESOLVED_PREVENTED_EFFECT_COIN``）。
    コインが決めるものに有効なもの（自分へのダメージ・自分への効果・ダメージを受けない状態の相手への効果）があれば投げる。カード id では分けない。"""

    def test_sticky_and_iron_grip_stop_against_barrier(self):
        """ねばりつく・じごくがため（1 枚のコインで追加ダメージとマヒ）: バリアーではダメージもマヒも無効なので、からではさむ（v0.33）と同じく止める。
        v0.33 まではコインを投げていた（v0.34 で変えた既存の動作。docs 2 章）。"""
        for attacker, index in ((mon(GRIMER, (GRASS, GRASS)), 1), (mon(GIOVANNIS_MACHOKE, (FIGHTING, FIGHTING, FIGHTING)), 1)):
            with self.subTest(card=attacker["card"]):
                assert_stops(self, with_barrier(attacker), UseAttack(1, index), "UNRESOLVED_PREVENTED_EFFECT_COIN")

    def test_sticky_still_flips_against_prevented_damage(self):
        """「ダメージを受けない」状態（かたまる）の相手には、ダメージだけが無効でマヒは有効なので、ねばりつくはコインを投げ、「おもて」ならマヒ（kyuura の
        CR-STICKY-VS-PREVENTED。v0.33 と同じ）。"""
        state = with_coin_results(board(mon(GRIMER, (GRASS, GRASS)), mon(METAPOD, prevent_damage=TURN - 1)), H)
        new = play(state, UseAttack(0, 1))
        self.assertEqual(coins(new, len(state.log)), ["heads"])
        self.assertEqual(len(events(new, len(state.log), "damage_prevented")), 1)
        self.assertTrue(new.players[1].active.conditions.paralyzed)

    def test_coins_that_decide_something_valid_still_flip(self):
        """コインが自分へのダメージ・自分への効果も決めるワザは、バリアーの相手にも投げる（かみなりパンチの「うら」の自分への 10・いちかばちかの「うら」の
        自分への 100・こうそくいどうの自分のバリアー・いかりくるうの自分のこんらん）。相手へのダメージは無効。"""
        cases = [(mon(ELECTABUZZ, (LIGHTNING, LIGHTNING)), 1, T, "self_damage"), (mon(GIOVANNIS_MACHOKE, (FIGHTING,), damage=0), 0, T, "self_damage"),
                 (mon(RAPIDASH, (FIRE, FIRE, FIRE)), 1, H, "barrier"), (mon(TAUROS, (FIGHTING, FIGHTING, FIGHTING)), 1, T, "confusion")]
        for attacker, index, side, effect in cases:
            with self.subTest(card=attacker["card"]):
                state = with_coin_results(with_barrier(attacker), side)
                new = play(state, UseAttack(1, index))
                since = len(state.log)
                self.assertEqual(len(coins(new, since)), 1)
                self.assertEqual([e for e in events(new, since, "damage") if e.get("target") is None], [])
                if effect == "self_damage":
                    self.assertEqual(len([e for e in events(new, since, "damage") if e.get("target") == "self"]), 1)
                elif effect == "barrier":
                    self.assertIsNotNone(attack_barrier(new, new.players[1].active))
                else:
                    self.assertTrue(new.players[1].active.conditions.confused)

    def test_damage_only_coin_attacks_keep_v0_4b_code(self):
        """コインがダメージの要素だけを決めるワザ（失敗するワザ・ミサイルばり・たまなげMAX・でんこうせっか）は、バリアー・かたまるの相手に v0.4b の
        ``UNRESOLVED_PREVENTED_COIN_DAMAGE``（v0.33 と同じ）。"""
        cases = [(mon(BLAINES_KANGASKHAN, (FIGHTING,)), 0), (mon(JOLTEON, (LIGHTNING, LIGHTNING, LIGHTNING)), 1), (mon(EXEGGUTOR, (GRASS, GRASS)), 1),
                 (mon(FLAREON, (FIRE, FIRE)), 0)]
        for attacker, index in cases:
            with self.subTest(card=attacker["card"]):
                assert_stops(self, with_barrier(attacker), UseAttack(1, index), "UNRESOLVED_PREVENTED_COIN_DAMAGE")
                assert_stops(self, board(attacker, mon(METAPOD, prevent_damage=TURN - 1)), UseAttack(0, index), "UNRESOLVED_PREVENTED_COIN_DAMAGE")

    def test_effect_coin_against_barrier_is_hc3(self):
        """くさいガス（1 枚のコインでどくかこんらん）: どちらも相手への効果なので、バリアーの相手には HC3。かたまるの相手には効果が有効なので投げる。"""
        assert_stops(self, with_barrier(mon(KOFFING, (GRASS, GRASS))), UseAttack(1, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")
        state = with_coin_results(board(mon(KOFFING, (GRASS, GRASS)), mon(METAPOD, prevent_damage=TURN - 1)), T)
        new = play(state, UseAttack(0, 0))
        self.assertTrue(new.players[1].active.conditions.confused)

    def test_stopping_types_follow_from_the_programs(self):
        """製品のどの登録でも、バリアーで止まるコインは、コインが決める要素がどれも相手の対戦ポケモンへのダメージ・効果のもの（要素の並びから求める。
        カード id の表ではない）。止まる型は 4 つ（ねばりつく・じごくがための型・からではさむの型・失敗するワザの型・v0.40 のラブラリアットの型）で、ほかのコインは投げる。"""
        stopping, flipping = set(), set()
        for key in E.DEFAULT_EFFECTS.attack_keys():
            effect = E.DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).effect
            program = P.compile_attack(effect)
            for index, element in enumerate(program):
                if isinstance(element, P.Coin):
                    decided = [e for e in program if e.coin_dependent(element.name)]
                elif isinstance(element, P.FailOnTails):
                    decided = list(program[index + 1:])
                else:
                    continue
                # v0.56: 控えへのダメージの要素（"bench"）はバリアーでは無効にならない（見えない壁だけ）ので、バリアーの分類では有効な要素と同じに数える
                roles = [None if e.coin_receiver() == "bench" else e.coin_receiver() for e in decided]
                (stopping if roles and None not in roles else flipping).add(type(effect).__name__)
        # v0.40: サカキのニドクインの「ラブラリアット」（FailOnTailsAmountIfBenchNamed。失敗のコインのあとはダメージだけ。
        # docs/count-condition-switch-return-v0.40.md の LR2）。v0.41: ナツメのモルフォンの「げんかくおんぱ」（DamageThenConfuseOnAnyHeads。ダメージのあとの
        # コイン 2 枚は相手のこんらんだけを決める。docs/heal-counter-status-v0.41.md）。v0.44: キョウのスピアーの「どくばり」（DamageThenPoisonAndParalyzeOnHeads。
        # ダメージのあとの 1 枚のコインは相手のどくとマヒだけを決める。docs/search-evolution-once-attacks-v0.44.md）。v0.45: キョウのアーボの「とつぜんどく」
        # （DamageThenPoisonAndConfuseOnAllHeads。ダメージのあとの 2 枚のコインは相手のどくとこんらんだけを決める。docs/conditional-damage-energy-v0.45.md）。
        # v0.48: モルフォンの「りんぷん」（DamageThenPoisonAndConfuseOnHeads。ダメージのあとの 1 枚のコインは相手のどくとこんらんだけを決める）・ナツメのゲンガーの
        # 「やみのこえ」（DamageThenCoinsReturnOpponentToDeck。ダメージのあとの 2 枚のコインは相手の対戦ポケモンを山札にもどすことだけを決める。
        # docs/effective-pokemon-properties-v0.48.md）
        self.assertEqual(stopping, {"CoinBonusDamageAndParalyze", "DamageAndParalyzeOnHeadsElseFail", "FailOnTailsDamage", "FailOnTailsAmountIfBenchNamed",
                                    "DamageThenConfuseOnAnyHeads", "DamageThenPoisonAndParalyzeOnHeads", "DamageThenPoisonAndConfuseOnAllHeads",
                                    "DamageThenPoisonAndConfuseOnHeads", "DamageThenCoinsReturnOpponentToDeck",
                                    # v0.79: ルージュラの「あやしいおどり」（CoinBonusDamageAndConfuse。1 枚のコインが追加のダメージとこんらんを決める。ねばりつくと同じ形）
                                    "CoinBonusDamageAndConfuse",
                                    # v0.83: ひかるギャラドスの「げきりん」（FailOnTailsPlusOwnCounters。失敗のコインのあとはダメージだけ）・ひかるセレビィの「ミラクルリーフ」
                                    # （CoinsPerDefenderEnergyChosenStatus。コインは選んだ特殊状態だけを決める）・ひかるヨルノズクの「フラッシュアイ」（ThreeCoinsStatusByHeads。
                                    # 3 枚のコインは相手の特殊状態だけを決める。docs/shining-gentle-pokemon-v0.83.md）
                                    "FailOnTailsPlusOwnCounters", "CoinsPerDefenderEnergyChosenStatus", "ThreeCoinsStatusByHeads",
                                    # v0.84: やさしいサンダースの「サンダーニードル」（3 枚のコインは相手へのダメージと相手のマヒだけを決める。
                                    # docs/light-powers-evolution-v0.84.md）
                                    "CoinsTimesDamageThenParalyzeIfAtLeast",
                                    # v0.86: スイクンの「オーロラウェーブ」（2 枚のコインは相手のマヒかねむりだけを決める。docs/entry-energy-evolution-reactions-v0.86.md 7 章）
                                    "DamageThenParalyzeOrSleepByTwoCoins",
                                    # v0.90: ドーブルの「ペイント」（1 枚のコインは相手への色マーカーだけを決める。色を選ぶ要素は数えない。docs/markers-counters-v0.90.md 6 章）
                                    "CoinPaintOpponent",
                                    # v0.92: イトマルの「こわいかお」（1 枚のコインは相手の対戦ポケモンへのワザと「にげる」の禁止だけを決める。docs/power-suppression-lasting-locks-v0.92.md 5 章）
                                    "CoinAttackAndRetreatLock"})
        self.assertIn("CoinBonusOrSelfDamage", flipping)
        self.assertIn("SelfDamageInsteadOnTails", flipping)


class CarryAcrossDecisionTest(unittest.TestCase):
    """2 部: ダメージの要素のあとに決定を出すワザ（うしろなげ・かけぬける）で、相手の対戦ポケモンへのダメージで「ダメージを受けたとき」の効果（はんげき）が
    はたらいていても、決定をまたいで運び、控えへのダメージのあと・ダメージ以外の効果の前に処理する（p.89）。v0.33 の
    ``UNSUPPORTED_DECISION_AFTER_DAMAGE_TRIGGER`` を解消した。"""

    def waiting(self):
        state = with_coin_results(counter_board(mon(GIOVANNIS_PINSIR, (GRASS, GRASS, GRASS)), attacker_bench=(RATTATA, CHARMANDER)), T)
        return state, play(state, UseAttack(0, 1))

    def test_pending_counterattack_is_carried_and_fires_after_bench_damage(self):
        """「うら」: 相手に 40 → コイン → 自分の控えを選ぶ決定（はんげきを運ぶ）→ 控えに 20 → はんげき 10。はんげきは 1 回だけで、決定の前には処理しない。"""
        state, waiting = self.waiting()
        d = waiting.decision
        self.assertEqual((d.kind, d.player, tuple(d.options)), (SELECT_POKEMON, 0, tuple(p.pokemon_id for p in state.players[0].bench)))
        frame = dict(d.context_value("frame"))
        self.assertEqual(len(frame["pending"]), 1)
        owner, pid, name, received = frame["pending"][0]
        self.assertEqual((owner, pid, received), (1, state.players[1].active.pokemon_id, 40))
        self.assertEqual(kinds(waiting, len(state.log)), ["attack", "damage", "coin_flip"])
        done = play(waiting, ResolveDecision(0, d.id, (state.players[0].bench[1].pokemon_id,)))
        tail = [e for e in kinds(done, len(waiting.log)) if e in ("damage", "counterattack", "coin_flip")]
        self.assertEqual(tail, ["damage", "counterattack"])  # 控えへのダメージ → はんげき（10 は counterattack のログに書く）
        self.assertEqual(done.players[0].bench[1].damage, 20)
        self.assertEqual(done.players[0].active.damage, 10)
        self.assertEqual(len(events(done, len(state.log), "counterattack")), 1)
        self.assertEqual(len(events(done, len(state.log), "coin_flip")), 1)

    def test_heads_has_no_decision_and_counterattack_follows_the_coin(self):
        state = with_coin_results(counter_board(mon(GIOVANNIS_PINSIR, (GRASS, GRASS, GRASS))), H)
        done = play(state, UseAttack(0, 1))
        self.assertIsNone(done.decision)
        self.assertEqual([k for k in kinds(done, len(state.log)) if k in ("damage", "coin_flip", "counterattack")],
                         ["damage", "coin_flip", "counterattack"])

    def test_invalid_answers_keep_the_decision_and_the_pending_effect(self):
        """不正な答え（相手のプレイヤー・相手の控え・2 匹・0 匹・古い決定 id）は拒否し、決定と運んでいる効果はそのまま（状態・乱数・ログが変わらない）。"""
        state, waiting = self.waiting()
        d = waiting.decision
        snapshot = (full(waiting), rng_fingerprint(waiting.rng), len(waiting.log))
        bad = [ResolveDecision(1, d.id, (d.options[0],)), ResolveDecision(0, d.id, (state.players[1].bench[0].pokemon_id,)),
               ResolveDecision(0, d.id, tuple(d.options[:2])), ResolveDecision(0, d.id, ()), ResolveDecision(0, d.id + 1, (d.options[0],))]
        for command in bad:
            with self.subTest(command=command), self.assertRaises(EngineError):
                apply_kernel(waiting, command)
            self.assertEqual((full(waiting), rng_fingerprint(waiting.rng), len(waiting.log)), snapshot)

    def test_resume_after_copy_and_pickle_is_identical(self):
        """決定を待つ状態を複製・pickle で保存して再開しても、結果（形式 10 の全体・乱数・ログ）は同じ。書き出しの監査も通る（運ぶ効果は既存の決定の
        ``context`` の明示的なデータ）。"""
        _, waiting = self.waiting()
        self.assertEqual(serialization_problems(waiting), [])
        d = waiting.decision
        answer = ResolveDecision(0, d.id, (d.options[0],))
        results = [play(s, answer) for s in (waiting, waiting.clone(), copy.deepcopy(waiting), pickle.loads(pickle.dumps(waiting)))]
        reference = (full(results[0]), rng_fingerprint(results[0].rng), [dict(e) for e in results[0].log])
        for other in results[1:]:
            self.assertEqual((full(other), rng_fingerprint(other.rng), [dict(e) for e in other.log]), reference)

    def test_broken_carried_effect_is_an_invariant_violation(self):
        """運ぶ効果の記録が場とログに合わなければ不変条件の違反（受けたダメージの数・持ち主・効果の名前）。"""
        _, waiting = self.waiting()
        d = waiting.decision
        context = dict(d.context)
        frame = dict(context["frame"])
        owner, pid, name, received = frame["pending"][0]
        for broken in ((owner, pid, name, received + 10), (1 - owner, pid, name, received), (owner, pid, "存在しない効果", received)):
            with self.subTest(broken=broken):
                frame2 = tuple((k, ((broken,) if k == "pending" else v)) for k, v in context["frame"])
                bad = waiting.clone()
                bad.decision = dataclasses.replace(d, context=tuple((k, frame2 if k == "frame" else v) for k, v in d.context))
                self.assertTrue(check_invariants(bad))

    def test_double_knockout_across_the_decision_is_c18(self):
        """カイリキーがワザ（40）で、ワザを使ったポケモンがはんげき（10）できぜつする場合は、決定をまたいでも宣言の前に C18 で止める（先読みが決定のすべての
        答えを試す）。"""
        state = counter_board(mon(GIOVANNIS_PINSIR, (GRASS, GRASS, GRASS), damage=60), machamp_damage=60)
        assert_stops(self, state, UseAttack(0, 1), "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")

    def test_preflight_modes_agree(self):
        """先読みの方法（derived・derived_full・legacy）で、受け付け・結果（形式 10・乱数・ログ）が同じ（v0.34 の型は legacy でもすべての結果を試す）。"""
        for side in (H, T):
            state = with_coin_results(counter_board(mon(GIOVANNIS_PINSIR, (GRASS, GRASS, GRASS))), side)
            results = []
            for mode in PREFLIGHT_MODES:
                new = play(state, UseAttack(0, 1), [first] if side is T else [], mode=mode)
                results.append((full(new), rng_fingerprint(new.rng)))
            with self.subTest(side=side):
                self.assertTrue(all(r == results[0] for r in results))


class CoinBonusOrSelfDamageTest(unittest.TestCase):
    """かみなりパンチ・あばれる: 1 枚のコインで「おもて」なら相手に追加 10、「うら」なら自分に 10（投げ直さない）。"""

    def test_one_coin_decides_bonus_or_self_damage(self):
        for card, energy in ((ELECTABUZZ, (LIGHTNING, LIGHTNING)), (NIDOKING, (GRASS, GRASS, GRASS))):
            index = 1 if card == ELECTABUZZ else 0
            state = board(mon(card, energy))
            heads = play(with_coin_results(state, H), UseAttack(0, index))
            tails = play(with_coin_results(state, T), UseAttack(0, index))
            with self.subTest(card=card):
                self.assertEqual([(e.get("target"), e["amount"]) for e in events(heads, len(state.log), "damage")], [(None, 40)])
                self.assertEqual([(e.get("target"), e["amount"]) for e in events(tails, len(state.log), "damage")], [(None, 30), ("self", 10)])
                self.assertEqual((len(coins(heads, len(state.log))), len(coins(tails, len(state.log)))), (1, 1))

    def test_self_damage_with_counterattack_and_c18(self):
        """「うら」の自分への 10 とはんげきの 10 は両方受ける。両方できぜつしうる組（「うら」の場合）なら、宣言の前に C18。"""
        state = with_coin_results(counter_board(mon(ELECTABUZZ, (LIGHTNING, LIGHTNING))), T)
        new = play(state, UseAttack(0, 1))
        self.assertEqual(new.players[0].active.damage, 20)
        assert_stops(self, counter_board(mon(ELECTABUZZ, (LIGHTNING, LIGHTNING), damage=50), machamp_damage=70), UseAttack(0, 1),
                     "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")


class RapidashTest(unittest.TestCase):
    """こうそくいどう: ダメージのあと、コインが「おもて」なら自分に「ワザをうけない」状態（バリアーと同じ持続する効果）。"""

    def test_heads_gives_attack_barrier_for_the_next_opponent_turn(self):
        state = with_coin_results(board(mon(RAPIDASH, (FIRE, FIRE, FIRE))), H)
        new = play(state, UseAttack(0, 1))
        self.assertEqual([e["amount"] for e in events(new, len(state.log), "damage")], [30])
        barrier = attack_barrier(new, new.players[0].active)
        self.assertIsNotNone(barrier)
        self.assertEqual((barrier.created_turn, barrier.active_turn), (TURN, TURN + 1))
        hit = play(new, UseAttack(1, 0))  # 相手のジャブはダメージも効果も受けない
        self.assertEqual(hit.players[0].active.damage, 0)
        self.assertTrue(events(hit, len(new.log), "damage_prevented") or events(hit, len(new.log), "effect_prevented"))

    def test_tails_gives_nothing(self):
        state = with_coin_results(board(mon(RAPIDASH, (FIRE, FIRE, FIRE))), T)
        new = play(state, UseAttack(0, 1))
        self.assertIsNone(attack_barrier(new, new.players[0].active))

    def test_attacker_knocked_out_by_counterattack_flips_no_coin(self):
        """相手のはんげきで HP 以上になったら、処理の対象がいないのでコインを投げない（p.309）。"""
        state = counter_board(mon(RAPIDASH, (FIRE, FIRE, FIRE), damage=60))
        new = play(state, UseAttack(0, 1))
        self.assertEqual(coins(new, len(state.log)), [])
        self.assertTrue(events(new, len(state.log), "knock_out"))


class FlareonTest(unittest.TestCase):
    """かえんほうしゃ: 炎エネルギーカードを 1 枚トラッシュ（ワザの効果。RUL-ENERGY-DISCARD-ATTACKS の範囲）→ 60。トラッシュできなければ失敗。"""

    def test_discard_then_damage(self):
        state = board(mon(FLAREON, (FIRE, FIRE, LIGHTNING, FIRE)))
        waiting = play(state, UseAttack(0, 1))
        d = waiting.decision
        self.assertEqual((d.kind, len(d.options)), (DISCARD_ENERGY, 3))
        done = play(waiting, ResolveDecision(0, d.id, (d.options[0],)))
        self.assertEqual([k for k in kinds(done, len(state.log)) if k in ("discard_energy", "damage")], ["discard_energy", "damage"])
        self.assertEqual(len(done.players[0].active.energy), 3)

    def test_confused_tails_does_not_discard(self):
        """トラッシュの時点はワザの効果なので、こんらんの「うら」ではトラッシュしない（HC1 で止めない）。"""
        state = with_coin_results(board(mon(FLAREON, (FIRE, FIRE, FIRE, FIRE), confusion=True)), T)
        new = play(state, UseAttack(0, 1))
        self.assertEqual(events(new, len(state.log), "discard_energy"), [])
        self.assertEqual(len(new.players[0].active.energy), 4)

    def test_copied_without_fire_energy_fails(self):
        """ピッピの「ゆびをふる」でまねて、炎エネルギーカードがなければ、説明のとおりワザの失敗（p.323）。"""
        state = board(mon(CLEFAIRY, (WATER, WATER, WATER)), mon(FLAREON, (FIRE, FIRE)))
        new = play(state, UseAttack(0, 1), [lambda d: (1,) if d.kind == SELECT_ATTACK else first(d)])
        self.assertEqual(len(events(new, len(state.log), "attack_failed")), 1)
        self.assertEqual(new.players[1].active.damage, 0)


class VaporeonTest(unittest.TestCase):
    def test_extra_water_with_colorless_is_hc4(self):
        """みずでっぽう（水水無）: 多い水エネルギーの数が無色の払い方で変わるときだけ HC4 で止める（v0.31 の第4弾のコダックと同じ型）。"""
        assert_stops(self, board(mon(VAPOREON, (WATER, WATER, WATER))), UseAttack(0, 1), "UNRESOLVED_EXTRA_ENERGY_COLORLESS")
        state = board(mon(VAPOREON, (WATER, WATER, FIRE)))
        new = play(state, UseAttack(0, 1))
        self.assertEqual([e["amount"] for e in events(new, len(state.log), "damage")], [30])


class TaurosTest(unittest.TestCase):
    """いかりくるう: 目安 + 自分のダメージカウンター × 10 → その後コインが「うら」なら自分がこんらん。"""

    def test_counters_and_self_confusion(self):
        state = board(mon(TAUROS, (FIGHTING, FIGHTING, FIGHTING), damage=30))
        heads = play(with_coin_results(state, H), UseAttack(0, 1))
        tails = play(with_coin_results(state, T), UseAttack(0, 1))
        self.assertEqual([e["amount"] for e in events(heads, len(state.log), "damage")], [50])
        self.assertFalse(heads.players[0].active.conditions.confused)
        self.assertTrue(tails.players[0].active.conditions.confused)

    def test_coin_is_flipped_even_if_no_damage_was_dealt(self):
        """「その後」は順番で、ダメージを与えたことを条件にしない（Z23 の「ダメージを与えた後」とは別の言い方）。ダメージを受けない相手にも投げる。"""
        state = with_coin_results(board(mon(TAUROS, (FIGHTING, FIGHTING, FIGHTING)), mon(METAPOD, prevent_damage=TURN - 1)), T)
        new = play(state, UseAttack(0, 1))
        self.assertTrue(new.players[0].active.conditions.confused)

    def test_knocked_out_attacker_flips_no_coin(self):
        state = counter_board(mon(TAUROS, (FIGHTING, FIGHTING, FIGHTING), damage=50))
        new = play(state, UseAttack(0, 1))
        self.assertEqual(coins(new, len(state.log)), [])


class KoffingTest(unittest.TestCase):
    """くさいガス: 1 枚のコインで「おもて」ならどく、「うら」ならこんらん。"""

    def test_one_coin_decides_poison_or_confusion(self):
        state = board(mon(KOFFING, (GRASS, GRASS)))
        heads = play(with_coin_results(state, H), UseAttack(0, 0))
        tails = play(with_coin_results(state, T), UseAttack(0, 0))
        self.assertEqual(heads.players[1].active.conditions.poison, NORMAL_POISON)
        self.assertFalse(heads.players[1].active.conditions.confused)
        self.assertTrue(tails.players[1].active.conditions.confused)
        self.assertIsNone(tails.players[1].active.conditions.poison)
        self.assertEqual((len(coins(heads, len(state.log))), len(coins(tails, len(state.log)))), (1, 1))

    def test_confusion_replaces_sleep_and_keeps_poison(self):
        state = with_coin_results(board(mon(KOFFING, (GRASS, GRASS)), mon(HITMONCHAN, sleep=True, poison=10)), T)
        new = play(state, UseAttack(0, 0))
        conditions = new.players[1].active.conditions
        self.assertTrue(conditions.confused)
        self.assertFalse(conditions.asleep)
        self.assertEqual(conditions.poison, NORMAL_POISON)

    def test_evaded_damage_stops_before_the_effect_coin(self):
        """「とうめい」で前のダメージを受けないと決まりうるなら、効果だけを決めるコインを投げるかは決められない（T19b）。"""
        assert_stops(self, board(mon(KOFFING, (GRASS, GRASS)), mon(HAUNTER)), UseAttack(0, 0), "UNRESOLVED_EVADED_EFFECT_COIN")

    def test_knocked_out_target_gets_no_coin(self):
        state = board(mon(KOFFING, (GRASS, GRASS)), mon(HITMONCHAN, damage=60))
        new = play(state, UseAttack(0, 0))
        self.assertEqual(coins(new, len(state.log)), [])


class SpecialPoisonTest(unittest.TestCase):
    """どくどく: ポケモンチェックごとに 20 のどくダメージを受ける特殊などく（p.322 の「どく状態にかかる」もの。v0.3a の 13）。通常のどくの 2 倍の処理では
    ない。"""

    def nidoking(self, **extra):
        return mon(NIDOKING, (GRASS, GRASS, GRASS), **extra)

    def test_new_special_poison_deals_20_in_pokemon_check(self):
        state = board(self.nidoking())
        new = play(state, UseAttack(0, 1))
        self.assertEqual(new.players[1].active.conditions.poison, Poison(damage=20))
        [poisoned] = events(new, len(state.log), "special_condition")
        self.assertEqual((poisoned["condition"], poisoned["damage"]), ("poison", 20))
        self.assertEqual([e["amount"] for e in events(new, len(state.log), "poison_damage")], [20])
        self.assertEqual(new.players[1].active.damage, 40)

    def test_same_special_poison_is_not_stacked(self):
        state = board(self.nidoking(), mon(HITMONCHAN, poison=20))
        new = play(state, UseAttack(0, 1))
        [poisoned] = events(new, len(state.log), "special_condition")
        self.assertTrue(poisoned["already"])
        self.assertEqual(new.players[1].active.conditions.poison, Poison(damage=20))

    def test_normal_poison_to_special_is_unresolved(self):
        """通常のどく状態のポケモンを特殊などくにする向きは p.322 に書かれていない（v0.3a の 15）ので、宣言の前に止める（TP3）。"""
        assert_stops(self, board(self.nidoking(), mon(HITMONCHAN, poison=10)), UseAttack(0, 1), "UNRESOLVED_SPECIAL_POISON_OVERWRITE")
        self.assertEqual(QUESTIONS["special_poison_overwrite"].code, "UNRESOLVED_SPECIAL_POISON_OVERWRITE")

    def test_special_to_normal_poison_becomes_normal(self):
        """特殊などく状態のポケモンが通常のどくを受けたら、通常のどく状態になる（p.322。v0.3a の 14。既存の処理）。"""
        state = with_coin_results(board(mon(WEEDLE, (GRASS,)), mon(HITMONCHAN, poison=20)), H)
        new = play(state, UseAttack(0, 0))
        self.assertEqual(new.players[1].active.conditions.poison, NORMAL_POISON)

    def test_special_poison_coexists_with_sleep_and_paralysis(self):
        """どくはほかの特殊状態と重複する（p.322）ので、ねむり・マヒ・こんらんを置きかえない（ねむりはそのあとのポケモンチェックのコインで回復しうる）。"""
        for spec, name in (({"sleep": True}, "sleep"), ({"paralysis": TURN - 1}, "paralysis"), ({"confusion": True}, "confusion")):
            state = board(self.nidoking(), mon(HITMONCHAN, **spec))
            new = play(with_coin_results(state, T), UseAttack(0, 1))
            with self.subTest(spec=spec):
                self.assertEqual(new.players[1].active.conditions.poison, Poison(damage=20))
                self.assertEqual([e for e in events(new, len(state.log), "special_conditions_removed") if e["reason"] == "replaced"], [])
                self.assertIn(name, new.players[1].active.conditions.names())

    def test_knock_out_in_pokemon_check_and_double_knockout(self):
        """ポケモンチェックの 20 できぜつする。両方の対戦ポケモンがどくできぜつする場合は、どくの量が違っても v0.3a の
        ``UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`` で止める。"""
        state = board(self.nidoking(), mon(HITMONCHAN, damage=40))
        new = play(state, UseAttack(0, 1))
        self.assertTrue([e for e in events(new, len(state.log), "knock_out")])
        both = board(self.nidoking(damage=80, poison=10), mon(HITMONCHAN, damage=40))
        halted = play(both, UseAttack(0, 1))
        self.assertEqual(halted.phase.value, "halted")
        self.assertEqual(events(halted, len(both.log), "halted")[0]["code"], "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT")

    def test_evolution_and_bench_clear_special_poison(self):
        state = board(mon(NIDORAN_M, (GRASS,), poison=20, played_turn=1), hand=[NIDORINO])
        evolved = apply_command(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].active.pokemon_id))
        self.assertIsNone(evolved.players[0].active.conditions.poison)

    def test_serialization_keeps_the_amount(self):
        state = board(self.nidoking(), mon(HITMONCHAN, poison=20))
        self.assertEqual(full(state)["players"][1]["active"]["special_conditions"]["poison"], {"damage": 20})
        with self.assertRaises(ValueError):
            state_to_dict(state, format_version=4)


class ExeggutorTest(unittest.TestCase):
    """テレポート（自分の控えと入れ替える）・たまなげMAX（ついているエネルギーの数だけコイン）。"""

    def test_teleport_switches_with_a_chosen_bench_pokemon(self):
        state = board(mon(EXEGGUTOR, (PSYCHIC,), poison=10), bench=(RATTATA, CHARMANDER))
        waiting = play(state, UseAttack(0, 0))
        d = waiting.decision
        self.assertEqual((d.kind, d.player, tuple(d.options)), (SELECT_POKEMON, 0, tuple(p.pokemon_id for p in state.players[0].bench)))
        target = state.players[0].bench[1].pokemon_id
        done = play(waiting, ResolveDecision(0, d.id, (target,)))
        self.assertEqual(done.players[0].active.pokemon_id, target)
        self.assertIsNone(next(p for p in done.players[0].bench if p.pokemon_id == state.players[0].active.pokemon_id).conditions.poison)
        [switch] = events(done, len(state.log), "switch")
        self.assertEqual(switch["effect"], f"{EXEGGUTOR}#0")
        removed = events(done, len(state.log), "special_conditions_removed")
        self.assertEqual([e["reason"] for e in removed], ["switch"])

    def test_teleport_without_bench_does_nothing(self):
        state = board(mon(EXEGGUTOR, (PSYCHIC,)), bench=())
        new = play(state, UseAttack(0, 0))
        self.assertIsNone(new.decision)
        self.assertEqual(events(new, len(state.log), "switch"), [])
        self.assertEqual(new.current_player, 1)

    def test_teleport_can_be_copied(self):
        """ピッピの「ゆびをふる」でまねると、ピッピが自分の控えと入れ替わる。"""
        state = board(mon(CLEFAIRY, (WATER, WATER, WATER)), mon(EXEGGUTOR, (PSYCHIC,)), bench=(RATTATA,))
        waiting = play(state, UseAttack(0, 1), [lambda d: (0,)])  # まねるワザ: テレポート（位置 0）
        self.assertEqual(waiting.decision.kind, SELECT_POKEMON)
        new = play(waiting, ResolveDecision(0, waiting.decision.id, first(waiting.decision)))
        self.assertEqual(new.cards[new.players[0].bench[0].card].card_id, CLEFAIRY)
        self.assertEqual(events(new, len(state.log), "switch")[0]["effect"], f"{EXEGGUTOR}#0")

    def test_egg_toss_flips_one_coin_per_energy(self):
        state = with_coin_results(board(mon(EXEGGUTOR, (GRASS, PSYCHIC, GRASS))), H, T, H)
        new = play(state, UseAttack(0, 1))
        self.assertEqual(coins(new, len(state.log)), ["heads", "tails", "heads"])
        self.assertEqual([e["amount"] for e in events(new, len(state.log), "damage")], [40])

    def test_branch_limit(self):
        """v0.34: 先読みは 2 のエネルギーの数乗の結果を試し、12 枚（4,096 通り）までは受け付け、13 枚で ``UNSUPPORTED_PREFLIGHT_LIMIT`` だった。
        v0.35 で、結果を「おもて」の数だけで使うコインを先読みが「おもて」の数でまとめるようにした（エネルギーの数 + 1 通り）ので、13 枚以上も
        受け付ける（従来拒否していた場面を受け付ける変更。境界・試した結果の数・実際の処理のコインの数は
        tests/test_coin_groups_damage_order_v0_35.py で確かめる。docs/coin-groups-damage-order-v0.35.md 2 章）。"""
        play(board(mon(EXEGGUTOR, (GRASS,) * 12)), UseAttack(0, 1))
        play(board(mon(EXEGGUTOR, (GRASS,) * 13)), UseAttack(0, 1))


class GrowlTest(unittest.TestCase):
    """なきつく: 受けた相手がこのカードにワザでダメージを与えるとき、p.321 の 2 段階で 20 へる。次の自分の番の始めに消える。"""

    def growled(self, opponent):
        state = board(mon(CUBONE, (FIGHTING,)), opponent, bench=(RATTATA,))
        return state, play(state, UseAttack(0, 0))

    def test_reduction_at_step_two_before_weakness(self):
        """ニドキングのあばれる（草）: 「おもて」40 → 2 段階で 20 → カラカラの弱点（草）で 40。「うら」30 → 10 → 20。"""
        _, growled = self.growled(mon(NIDOKING, (GRASS, GRASS, GRASS)))
        effect = reduced_damage_to_source(growled, growled.players[1].active)
        self.assertEqual((effect.amount, effect.active_turn), (20, TURN + 1))
        heads = play(with_coin_results(growled, H), UseAttack(1, 0))
        [damage] = [e for e in events(heads, len(growled.log), "damage") if e.get("target") is None]
        self.assertEqual(damage["steps"][:3], (("1 基本となる計算", 40), ("2 カラカラ（reduced_damage_to_source）", 20), ("3 弱点", 40)))
        tails = play(with_coin_results(growled, T), UseAttack(1, 0))
        self.assertEqual([e["amount"] for e in events(tails, len(growled.log), "damage") if e.get("target") is None], [20])

    def test_zero_or_less_at_step_two_deals_no_damage(self):
        """2 段階で 0 以下になったら計算を終え、ダメージを与えなかったことになる（p.321）。ダメージ以外の効果（くさいガスのコイン）は処理する。"""
        _, growled = self.growled(mon(KOFFING, (GRASS, GRASS)))
        new = play(with_coin_results(growled, H), UseAttack(1, 0))
        [damage] = [e for e in events(new, len(growled.log), "damage") if e.get("target") is None]
        self.assertEqual((damage["amount"], damage["steps"]), (0, (("1 基本となる計算", 10), ("2 カラカラ（reduced_damage_to_source）", -10))))
        self.assertEqual(new.players[0].active.conditions.poison, NORMAL_POISON)
        self.assertEqual(new.players[0].active.damage, 10)  # ポケモンチェックのどくだけ

    def test_only_this_card_and_expires_at_the_start_of_the_next_turn(self):
        """ほかのポケモンへのダメージは変えない。効果はなきつくを使ったプレイヤーの次の番の始め（turn_start のすぐあと）に消える。"""
        _, growled = self.growled(mon(HITMONCHAN, (FIGHTING, FIGHTING, FIGHTING), damage=0))
        hit = play(growled, UseAttack(1, 1))
        self.assertEqual(hit.players[0].active.damage, 20)  # 40 → 20
        start = next(i for i, e in enumerate(hit.log) if e["kind"] == "turn_start" and e["turn"] == TURN + 2)
        self.assertEqual(hit.log[start + 1]["kind"], "persistent_effect_removed")
        self.assertEqual(hit.log[start + 1]["reason"], "expired")
        self.assertIsNone(reduced_damage_to_source(hit, hit.players[1].active))

    def test_bench_target_is_unresolved(self):
        """なきつくを使ったポケモンが控えにいるとき、受けたポケモンが控えにダメージを与えうる（かけぬける）なら、決められない（NK5）。"""
        state = board(mon(CUBONE, (FIGHTING,)), mon(BLAINES_RHYHORN, (FIGHTING, FIGHTING, FIGHTING)), bench=(RATTATA,), opponent_hand=(GUST,))
        growled = play(state, UseAttack(0, 0))
        gusted = play(growled, PlayTrainer(1, growled.players[1].hand[0]), [first])
        self.assertEqual(gusted.cards[gusted.players[0].bench[0].card].card_id, CUBONE)
        assert_stops(self, gusted, UseAttack(1, 1), "UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET")

    def test_with_swords_dance_is_unsupported(self):
        """v0.34: 同じ 2 段階に「その数にする」効果（つるぎのまい）と、へらす効果が重なると、計算の順番を選ぶ決定（p.321）がエンジンの未対応なので
        ``UNSUPPORTED_DAMAGE_STEP_ORDER`` で止めていた。v0.35 で順番の決定に対応したので、ワザを使うプレイヤー（2 段階。p.321・SC15）が順番を選ぶ
        決定を出す（従来拒否していた場面を受け付ける変更。順番ごとの最終ダメージ・保存と復元・不正な答えは tests/test_coin_groups_damage_order_v0_35.py）。"""
        state = board(mon(CUBONE, (FIGHTING,)), mon(SCYTHER, (GRASS, GRASS, GRASS), next_turn_attack_damage=(TURN - 1, 0, 1, 60)))
        growled = play(state, UseAttack(0, 0))
        for mode in PREFLIGHT_MODES:
            with self.subTest(mode=mode):
                waiting = play(growled, UseAttack(1, 1), mode=mode)
                self.assertEqual((waiting.decision.kind, waiting.decision.player, waiting.decision.options), ("damage_step_order", 1, (0, 1)))

    def test_barrier_voids_growl(self):
        """「ワザをうけない」状態の相手には、なきつくの効果は無効（相手に与える効果）。"""
        state = with_barrier(mon(CUBONE, (FIGHTING,)))
        new = play(state, UseAttack(1, 0))
        self.assertIsNone(reduced_damage_to_source(new, new.players[0].active))
        self.assertTrue(events(new, len(state.log), "effect_prevented"))

    def test_evolution_of_the_affected_pokemon_clears_growl(self):
        """受けたポケモンが進化したら、持続する効果は消える（p.310・p.323。v0.4b と同じ消える契機）。"""
        state = board(mon(CUBONE, (FIGHTING,)), mon(NIDORINO, (GRASS, GRASS, GRASS), played_turn=1), opponent_hand=(NIDOKING,))
        growled = play(state, UseAttack(0, 0))
        evolved = apply_command(growled, EvolvePokemon(1, growled.players[1].hand[0], growled.players[1].active.pokemon_id))
        self.assertIsNone(reduced_damage_to_source(evolved, evolved.players[1].active))
        self.assertEqual(events(evolved, len(growled.log), "persistent_effect_removed")[0]["reason"], "evolve")

    def test_type_is_registered(self):
        """持続する効果の型の一覧にあり、相手に与える効果・番の始めに消える効果（書き出しは形式 8 から。量を書く）。"""
        self.assertIn(ReducedDamageToSource, PERSISTENT_EFFECT_TYPES)
        self.assertTrue(ReducedDamageToSource.on_opponent and ReducedDamageToSource.expires_at_turn_start)


class MarowakTest(unittest.TestCase):
    """たすけをよぶ: 山札から「闘」のたねポケモンを 1 匹選んでベンチに出す（進化カードは選べない）。ベンチに空きがなければ使えない。"""

    def test_only_fighting_basic_pokemon_can_be_chosen(self):
        state = board(mon(MAROWAK, (FIGHTING, FIGHTING, FIGHTING)), deck=[DIGLETT, MACHOP, HITMONCHAN, CUBONE, MAROWAK, CHARMANDER, FIGHTING, MACHOKE])
        waiting = play(state, UseAttack(0, 1))
        d = waiting.decision
        expected = sorted(uid for uid in state.players[0].deck if state.cards[uid].card_id in (DIGLETT, MACHOP, HITMONCHAN, CUBONE))
        self.assertEqual((d.kind, list(d.options)), (BENCH_FROM_DECK, expected))
        done = play(waiting, ResolveDecision(0, d.id, (d.options[0],)))
        self.assertEqual([k for k in kinds(done, len(waiting.log)) if k in ("bench_from_deck", "shuffle")], ["bench_from_deck", "shuffle"])

    def test_full_bench_cannot_use(self):
        state = board(mon(MAROWAK, (FIGHTING, FIGHTING, FIGHTING)), bench=(RATTATA,) * 5, deck=[DIGLETT])
        assert_stops(self, state, UseAttack(0, 1), "BENCH_FULL", exception=IllegalActionError)

    def test_no_candidate_shuffles_without_benching(self):
        state = board(mon(MAROWAK, (FIGHTING, FIGHTING, FIGHTING)), deck=[CHARMANDER, MAROWAK, FIGHTING])
        new = play(state, UseAttack(0, 1))
        none = events(new, len(state.log), "bench_from_deck_none")
        self.assertEqual(len(none), 1)
        self.assertEqual(none[0]["pokemon_type"], "fighting")
        self.assertEqual(len(new.players[0].bench), 0)


class PreflightParityTest(unittest.TestCase):
    def test_every_attack_agrees_across_preflight_modes(self):
        """27 のワザのどれも、先読みの方法（derived・derived_full・legacy）で、受け付けるか・拒否のコード・結果（形式 10・乱数）が同じ（コインの両方の
        結果で）。v0.34 の型は v013_checks.VERIFIED に入れていないので、legacy でもすべての結果を試す。"""
        for card in V0_34_POKEMON:
            for attack in load_card_pool().get(card).attacks:
                energy = cost_energy(card, attack.index)
                for side in (H, T):
                    state = with_coin_results(board(mon(card, energy), bench=(RATTATA,), deck=[DIGLETT, FIGHTING, RATTATA]), side, side, side)
                    results = []
                    for mode in PREFLIGHT_MODES:
                        try:
                            new = play(state, UseAttack(0, attack.index), mode=mode)
                            while new.decision is not None and new.decision.resume == "attack":
                                new = play(new, ResolveDecision(new.decision.player, new.decision.id, first(new.decision)), mode=mode)
                            results.append((full(new), rng_fingerprint(new.rng)))
                        except EngineError as error:
                            results.append(("rejected", error.code))
                    with self.subTest(card=card, attack=attack.name_ja, side=side):
                        self.assertTrue(all(r == results[0] for r in results))
                        self.assertNotEqual(results[0][0], "rejected")


class DocumentTest(unittest.TestCase):
    def test_document_records_the_rulings(self):
        text = DOC.read_text(encoding="utf-8")
        for word in ("TP3", "NK5", "UNRESOLVED_SPECIAL_POISON_OVERWRITE", "UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET", "UNSUPPORTED_DAMAGE_STEP_ORDER",
                     "UNSUPPORTED_DECISION_AFTER_DAMAGE_TRIGGER", "ねばりつく", "じごくがため", "ガルーラ"):
            with self.subTest(word=word):
                self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()
