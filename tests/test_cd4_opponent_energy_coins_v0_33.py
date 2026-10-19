"""v0.33: CD4 の再検討と、相手のエネルギーカードをトラッシュするワザ・コインで失敗する／ダメージを与えられないワザ・控えポケモンにもダメージを
与えるワザの 15 枚（docs/cd4-opponent-energy-coins-v0.33.md）。

カードごとに同じテストを書かず、共通の仕組みの境界（``OpponentEnergyDiscardTest``・``CoinGateTest``・``CloysterTest``・``OwnBenchDamageTest``・
``CoinBenchDamageTest``）と、カードごとの登録の確かめ（``CardDataTest``）と、すべてのワザの先読みの方法ごとの一致（``PreflightParityTest``）に分けた。
CD4（ルージュラの「ヨガのポーズ」）は記録で決まらないので未解決のまま（``Cd4Test``。止める場面と処理する場面の境界）。

根拠はどれも kyuura データの採用（kyuura の印刷の文面。``card_sources.json``）と、既存の記録（p.309 の手順 6 と「処理の対象がなくなってしまっている
場合」、p.320 のダメージの分類、p.321 の計算の段階と「ダメージを受けない」状態、p.323 のワザの失敗、p.257 のプラスパワー・ディフェンダーの最新の説明の
エンジン・kyuura の記録。kyuura の CR-EFFECTS-AFTER-KO・CR-TRANSPARENCY-NOT-FAILURE・CR-STICKY-VS-PREVENTED・UQ-COIN-IN-NULLIFIED-ELEMENT）の
再利用。ガイドブックは読んでいない。
"""

from __future__ import annotations

import itertools
import json
import pathlib
import unittest

from kyuura_engine import (
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
from kyuura_engine.decisions import BENCH_FROM_DECK, DISCARD_OPPONENT_ENERGY, FORCED_SWITCH, SELECT_POKEMON
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.resolution.programs import (
    BUILDERS,
    BenchDamage,
    ChosenBenchDamage,
    Damage,
    DiscardOpponentEnergy,
    FailOnTails,
    Printed,
    ReparalysisGuard,
    Status,
)
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.rng import rng_fingerprint
from scripts import check_card_sources as cs
from scripts.extract_kyuura_cards import KYUURA_COMMIT
from tests.helpers import (
    BLAINES_DODUO,
    BLAINES_RHYHORN,
    BROCKS_DIGLETT,
    BROCKS_RHYHORN,
    CHARMANDER,
    CLOYSTER,
    DARK_RATICATE,
    DARK_VAPOREON,
    DARK_WARTORTLE,
    DEFENDER,
    DRAGONAIR,
    DRATINI,
    EEVEE,
    FIGHTING,
    FIRE,
    FOSSIL_GOLDUCK,
    GASTLY,
    GIOVANNIS_MACHAMP,
    GIOVANNIS_MACHOKE,
    GIOVANNIS_MACHOP,
    GIOVANNIS_NIDORAN_F,
    GRASS,
    HAUNTER,
    HITMONCHAN,
    JYNX,
    LIGHTNING,
    LT_SURGES_MAGNEMITE,
    LT_SURGES_MAGNEMITE_30,
    LT_SURGES_SPEAROW,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MEWTWO,
    MISTYS_PSYDUCK,
    NIDORAN_F,
    NIDORAN_M,
    NIDORINA,
    NIDORINO,
    PLUSPOWER,
    PSYCHIC,
    PSYDUCK,
    RATTATA,
    ROCKET_DRATINI,
    ROCKET_SQUIRTLE,
    ROCKET_ZUBAT,
    SABRINAS_VENONAT,
    SHELLDER,
    V0_33_POKEMON,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
TURN = 7
DOC = ROOT / "docs" / "cd4-opponent-energy-coins-v0.33.md"
# 進化しているカードの下のカード
BELOW = {DRAGONAIR: DRATINI, FOSSIL_GOLDUCK: PSYDUCK, DARK_VAPOREON: EEVEE, NIDORINO: NIDORAN_M, CLOYSTER: SHELLDER, DARK_RATICATE: RATTATA,
         MACHAMP: [MACHOP, MACHOKE], GIOVANNIS_MACHAMP: [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE], HAUNTER: GASTLY, DARK_WARTORTLE: ROCKET_SQUIRTLE}
# 登録の実装の型（カード id, ワザの位置）。説明文のないワザは DamageOnly
EXPECTED = {
    (DRAGONAIR, 0): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 30}),
    (DRAGONAIR, 1): (E.DamageThenDiscardOpponentEnergy, {"on_heads": False}),
    (FOSSIL_GOLDUCK, 0): (E.ParalyzeOnHeads, {}),
    (FOSSIL_GOLDUCK, 1): (E.DamageThenDiscardOpponentEnergy, {"on_heads": False}),
    (DARK_VAPOREON, 0): (E.DamageOnly, {}),
    (DARK_VAPOREON, 1): (E.DamageThenDiscardOpponentEnergy, {"on_heads": False}),
    (LT_SURGES_MAGNEMITE_30, 0): (E.DamageThenDiscardOpponentEnergy, {"on_heads": True}),
    (LT_SURGES_MAGNEMITE_30, 1): (E.ConfuseOnHeads, {}),
    (SABRINAS_VENONAT, 0): (E.PoisonWithoutDamage, {}),
    (SABRINAS_VENONAT, 1): (E.DamageThenDiscardOpponentEnergy, {"on_heads": True}),
    (NIDORAN_M, 0): (E.NoDamageOnTails, {}),
    (NIDORINO, 0): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 30}),
    (NIDORINO, 1): (E.DamageOnly, {}),
    (CLOYSTER, 0): (E.DamageAndParalyzeOnHeadsElseFail, {}),
    (CLOYSTER, 1): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 30}),
    (DARK_RATICATE, 0): (E.DamageOnly, {}),
    (DARK_RATICATE, 1): (E.FailOnTailsDamage, {"coins": 1}),
    (BROCKS_DIGLETT, 0): (E.FailOnTailsDamage, {"coins": 1}),
    (BROCKS_DIGLETT, 1): (E.DamageAndOwnBenchDamage, {"bench_damage": 10}),
    (BROCKS_RHYHORN, 0): (E.FailOnTailsDamage, {"coins": 2}),
    (LT_SURGES_SPEAROW, 0): (E.DamageAndForceSwitch, {}),
    (LT_SURGES_SPEAROW, 1): (E.FailOnTailsDamage, {"coins": 1}),
    (GIOVANNIS_NIDORAN_F, 0): (E.FailOnTailsDamage, {"coins": 1}),
    (GIOVANNIS_NIDORAN_F, 1): (E.DamageAndSelfDamage, {"self_damage": 20}),
    (BLAINES_RHYHORN, 0): (E.FailOnTailsDamage, {"coins": 1}),
    (BLAINES_RHYHORN, 1): (E.DamageThenCoinBenchDamage, {"bench_damage": 20}),
    (BLAINES_DODUO, 0): (E.FailOnTailsDamage, {"coins": 1}),
    (BLAINES_DODUO, 1): (E.DamageTimesOwnCounters, {"per": 10}),
}
# pcg-search.com の対象の版（サイトの一覧の番号）
EDITIONS = {
    DRAGONAIR: "069/096", FOSSIL_GOLDUCK: "011/048", DARK_VAPOREON: "025/065", LT_SURGES_MAGNEMITE_30: "037/096", SABRINAS_VENONAT: "003/098",
    NIDORAN_M: "009/096", NIDORINO: "010/096", CLOYSTER: "015/048", DARK_RATICATE: "046/065", BROCKS_DIGLETT: "046/096",
    BROCKS_RHYHORN: "054/096", LT_SURGES_SPEAROW: "059/096", GIOVANNIS_NIDORAN_F: "018/098", BLAINES_RHYHORN: "058/098", BLAINES_DODUO: "068/098",
}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, opponent=None, *, bench=(), opponent_bench=(RATTATA,), hand=(), deck=None, opponent_prizes=6):
    me = {"active": active, "bench": list(bench), "hand": list(hand)}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent or mon(HITMONCHAN, (FIGHTING,)), "bench": list(opponent_bench), "prizes": opponent_prizes}
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


def first(d):
    return tuple(d.options[:1])


def settle(state, *, mode="derived"):
    """残っている決定（サイドを取る・バトル場に出す）に、最初の選べるものから答えていく。"""
    while state.decision is not None:
        d = state.decision
        state = apply_kernel(state, ResolveDecision(d.player, d.id, tuple(d.options[:max(1, d.min_choices)])), preflight=mode)
    return state


def events(state, since, kind=None):
    return [dict(e) for e in state.log[since:] if kind is None or e["kind"] == kind]


def kinds(state, since):
    return [e["kind"] for e in state.log[since:]]


def total_cards(state):
    """両方のプレイヤーの、どこかのゾーンにあるカードの数（カードの保存則）。"""
    count = 0
    for p in state.players:
        count += len(p.deck) + len(p.hand) + len(p.discard) + len(p.prizes)
        count += sum(len(pokemon.cards()) + len(pokemon.energy) + len(pokemon.trainers) for pokemon in p.in_play())
    return count


def assert_stops(test, state, command, code, *, exception=UnsupportedError):
    """どの先読みの方法でも ``code`` で拒否し、状態・乱数・ログが変わらない（宣言の前に止める）。"""
    snapshot = (full(state), rng_fingerprint(state.rng), len(state.log))
    for mode in PREFLIGHT_MODES:
        with test.subTest(mode=mode), test.assertRaises(exception) as raised:
            apply_kernel(state, command, preflight=mode)
        test.assertEqual(raised.exception.code, code)
    test.assertEqual((full(state), rng_fingerprint(state.rng), len(state.log)), snapshot)


def with_barrier(attacker, defender_spec, *, defender_bench=(RATTATA,)):
    """相手（プレイヤー 1）の対戦ポケモンを「ワザをうけない」状態（ミュウツーの「バリアー」。v0.31 の ``AttackBarrier``）にしてから、プレイヤー 0 の番に
    する（ミュウツーが前の番に「バリアー」を使う。ログと持続する効果は対戦の手順で作る）。``defender_spec`` はバリアーを使うミュウツー。"""
    state = build_test_state([
        {"active": defender_spec, "bench": list(defender_bench)},
        {"active": attacker, "bench": [RATTATA]},
    ], turn_number=TURN)
    state = play(state, UseAttack(0, 1), [first])
    return state


class CardDataTest(unittest.TestCase):
    """15 枚の登録・写し・採用の記録・進化の関係（カードごとの登録の確かめ。処理の境界は下の共通の仕組みのテスト）。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_fifteen_cards_and_playable(self):
        """対象は依頼の 15 枚だけ（ほかの候補に広げていない）。どれも写しの組 pool_v0_33 にあり、対戦に使える。"""
        self.assertEqual(len(V0_33_POKEMON), 15)
        self.assertEqual(list(read_extract()["pool_v0_33"]), list(V0_33_POKEMON))
        for card in V0_33_POKEMON:
            with self.subTest(card=card):
                self.assertTrue(self.pool.is_playable(card))

    def test_every_attack_is_registered_with_the_expected_type(self):
        """28 のワザがどれも登録され、型と値が表のとおり。名前・文面は写しと同じで、処理に使う文面は kyuura の印刷の文面（説明文のあるワザ）。特殊能力を
        持つカードはない。"""
        seen = set()
        for card in V0_33_POKEMON:
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
        self.assertEqual(len(seen), 28)

    def test_adoption_records(self):
        """15 枚はどれも kyuura データの採用の記録（adopted。kyuura の記録はない）と pcg-search.com の照合（同じ版の一覧の番号）を持ち、過去の原典照合の
        記録には加えていない。違いはハクリューの名前（サイトは「ハクリュウ」。kyuura への報告事項）とマチスのオニスズメの「ふきとばし」の書き方の 2 件で、
        どちらも処理に影響しない。"""
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        verification = (ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8")
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        adopted = set(links["latest_descriptions"]["adopted_printed_text"])
        differences = {}
        for card in V0_33_POKEMON:
            record = sources[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]), ("kyuura_data", "adopted", KYUURA_COMMIT))
                self.assertEqual(record["kyuura_records"], [])
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
                         {DRAGONAIR: ["name.ja"], LT_SURGES_SPEAROW: ["pokemon.attacks[0].text.ja"]})
        self.assertEqual([i["fields"] for i in sources[DRAGONAIR]["issues"]], [["name.ja"]])

    def test_evolution_by_exact_name(self):
        """進化先 6 枚は、進化元の名前と完全に一致するたねポケモンからだけ、通常の進化の操作で進化する。弾で制限しない（ハクリューは第1弾・第4弾の
        どちらのミニリュウからも）。名前の違うカード（カスミのコダック・ニドラン♀・サカキのニドラン♀）からは進化できない。"""
        pairs = [(DRAGONAIR, DRATINI), (DRAGONAIR, ROCKET_DRATINI), (FOSSIL_GOLDUCK, PSYDUCK), (DARK_VAPOREON, EEVEE), (NIDORINO, NIDORAN_M),
                 (CLOYSTER, SHELLDER), (DARK_RATICATE, RATTATA)]
        for upper, below in pairs:
            with self.subTest(upper=upper, below=below):
                self.assertEqual(self.pool.get(upper).evolves_from, self.pool.get(below).name_ja)
                state = board(mon(RATTATA), bench=[mon(below, played_turn=1)], hand=[upper])
                target = state.players[0].bench[0].pokemon_id
                new = apply_command(state, EvolvePokemon(0, state.players[0].hand[0], target))
                self.assertEqual(new.cards[new.players[0].bench[0].card].card_id, upper)
        for upper, below in ((FOSSIL_GOLDUCK, MISTYS_PSYDUCK), (NIDORINO, NIDORAN_F), (NIDORINA, GIOVANNIS_NIDORAN_F), (NIDORINO, GIOVANNIS_NIDORAN_F)):
            state = board(mon(RATTATA), bench=[mon(below, played_turn=1)], hand=[upper])
            with self.subTest(upper=upper, below=below), self.assertRaises(IllegalActionError) as raised:
                apply_command(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].bench[0].pokemon_id))
            self.assertEqual(raised.exception.code, "EVOLUTION_NAME_MISMATCH")

    def test_same_name_cards_keep_separate_registrations(self):
        """マチスのコイル（PMCG5-039）は v0.29 のマチスのコイル（PMCG5-037）と同じ名前の別のカードで、登録は別（カード id で引く）。"""
        self.assertEqual(self.pool.get(LT_SURGES_MAGNEMITE).name_ja, self.pool.get(LT_SURGES_MAGNEMITE_30).name_ja)
        self.assertEqual((self.pool.get(LT_SURGES_MAGNEMITE).hp, self.pool.get(LT_SURGES_MAGNEMITE_30).hp), (40, 30))
        old = [type(E.DEFAULT_EFFECTS.attack_entry(LT_SURGES_MAGNEMITE, i).effect) for i in range(2)]
        self.assertNotIn(E.DamageThenDiscardOpponentEnergy, old)

    def test_nidoran_m_can_be_called_by_nidoran_f(self):
        """第2弾のニドラン♀の「なかまをよぶ」（説明の名前「ニドラン♂」「ニドラン♀」。v0.32）は、v0.33 で加えたニドラン♂も選べる（サカキのニドラン♀は
        名前が違うので選べない）。"""
        state = board(mon(NIDORAN_F, (GRASS, GRASS)), deck=[NIDORAN_M, GIOVANNIS_NIDORAN_F, NIDORAN_F, GRASS])
        waiting = play(state, UseAttack(0, 1))
        self.assertEqual(waiting.decision.kind, BENCH_FROM_DECK)
        self.assertEqual([waiting.cards[u].card_id for u in waiting.decision.options], [NIDORAN_M, NIDORAN_F])

    def test_registration_checks_reject_wrong_data(self):
        """登録の確かめ（``check``）: 説明・ダメージの目安・コインの枚数が合わないワザには登録できない。"""
        get = self.pool.get
        self.assertTrue(E.FailOnTailsDamage(coins=2).check(get(DARK_RATICATE).attacks[1]))
        self.assertTrue(E.FailOnTailsDamage().check(get(BROCKS_RHYHORN).attacks[0]))
        self.assertEqual(E.FailOnTailsDamage(coins=2).check(get(BROCKS_RHYHORN).attacks[0]), [])
        self.assertTrue(E.NoDamageOnTails().check(get(DARK_RATICATE).attacks[1]))
        self.assertTrue(E.DamageThenDiscardOpponentEnergy(on_heads=True).check(get(DRAGONAIR).attacks[1]))
        self.assertTrue(E.DamageThenDiscardOpponentEnergy().check(get(SABRINAS_VENONAT).attacks[1]))
        self.assertTrue(E.DamageAndParalyzeOnHeadsElseFail().check(get(FOSSIL_GOLDUCK).attacks[0]))
        self.assertTrue(E.DamageAndOwnBenchDamage(20).check(get(BROCKS_DIGLETT).attacks[1]))
        self.assertTrue(E.DamageThenCoinBenchDamage(10).check(get(BLAINES_RHYHORN).attacks[1]))
        for make in (lambda: E.FailOnTailsDamage(coins=0), lambda: E.DamageAndOwnBenchDamage(15), lambda: E.DamageThenCoinBenchDamage(0)):
            with self.assertRaises(ValueError):
                make()

    def test_programs(self):
        """解決の基盤の要素の並び。「失敗」（ワザ全体のコイン ``FailOnTails``）と「ダメージを与えられない」（ダメージの要素のコイン ``local_gate``）を
        別の要素で表す。パルシェンはマヒの再付与の確かめ → 1 枚のコイン → ダメージ → マヒ（マヒのコインはない）。"""
        self.assertEqual(BUILDERS[E.NoDamageOnTails](E.NoDamageOnTails()), (Damage(E.OPPONENT_ACTIVE, Printed(), local_gate=H),))
        self.assertEqual(BUILDERS[E.FailOnTailsDamage](E.FailOnTailsDamage(coins=2))[0], FailOnTails(count=2))
        cloyster = BUILDERS[E.DamageAndParalyzeOnHeadsElseFail](E.DamageAndParalyzeOnHeadsElseFail())
        self.assertEqual([type(e) for e in cloyster], [ReparalysisGuard, FailOnTails, Damage, Status])
        # v0.34: バリアーの相手で止めるか（HC3）は、印（v0.33 の with_effect）でなく、コインが決める残りの要素（ダメージとマヒ）から求める
        self.assertEqual((cloyster[1].count, cloyster[3].local_coin, cloyster[3].gate), (1, None, None))
        self.assertEqual([e.coin_receiver() for e in cloyster[2:]], ["damage", "effect"])
        self.assertEqual(BUILDERS[E.DamageThenDiscardOpponentEnergy](E.DamageThenDiscardOpponentEnergy(on_heads=True))[1],
                         DiscardOpponentEnergy(local_coin=H))
        own_bench = BUILDERS[E.DamageAndOwnBenchDamage](E.DamageAndOwnBenchDamage(10))[1]
        self.assertIsInstance(own_bench, BenchDamage)
        self.assertEqual(own_bench.own, True)
        self.assertIsInstance(BUILDERS[E.DamageThenCoinBenchDamage](E.DamageThenCoinBenchDamage(20))[1], ChosenBenchDamage)
        self.assertEqual(BUILDERS[E.FailOnTailsDamage](E.FailOnTailsDamage())[0], FailOnTails())  # v0.31 のゴッドバードと同じ

    def test_document_lists_the_cards(self):
        text = DOC.read_text(encoding="utf-8")
        for card in V0_33_POKEMON:
            self.assertIn(card, text)


class Cd4Test(unittest.TestCase):
    """CD4（v0.32）の再検討の結論: 記録（kyuura の研究の基準のコミットとエンジンの記録）では決まらないので、未解決のまま。止めるのは、相手の控え
    ポケモンにカウンターがのっていて、読み方（相手の対戦ポケモンだけ／相手の場のポケモンすべて）で基本となるダメージが変わるときだけ。"""

    def test_cd4_is_still_registered_as_unresolved(self):
        question = QUESTIONS["opponent_pokemon_counters"]
        self.assertEqual((question.code, question.rulings), ("UNRESOLVED_OPPONENT_POKEMON_COUNTERS", ("CD4",)))
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        self.assertIn("UNRESOLVED_OPPONENT_POKEMON_COUNTERS", links["stop_codes"])
        # v0.34 で 2 件（TP3・NK5）、v0.36 で 2 件（AC6・RD9）、v0.37 で 1 件（JS1）、v0.38 で 1 件（GK1）、v0.39 で 1 件（GS1）、v0.40 で 1 件（SG1）、
        # v0.41 で 1 件（CX1）、v0.42 で 2 件（PW1・PW2）、v0.43 で 2 件（PW3・PW4）、v0.44 で停止コード 2 件（FC1・TR1）とコードのない未解決 1 件（GV1）、
        # v0.45 で GV1 に停止コードを付け（未解決の裁定の数は同じ）、起こるようになった AC13 を停止コード・未解決の裁定に加えた。v0.46 で 2 件（CP1・CP2）、v0.47 で 4 件（PF1・PF2・PF3・KA1）、
        # v0.48 で 3 件（VS1・PG1・MH1）、v0.49 で 11 件（TE1・TF1・TF2・DG1〜DG3・VA1・RC1〜RC4）、v0.50 で 5 件（DV1〜DV5）、v0.51 で 2 件（RV1・FT1）（CD4 はそのまま。docs/barrier-resume-coin-bonus-v0.34.md・docs/sand-attack-retreat-lock-v0.36.md・
        # docs/fifteen-reused-effects-v0.37.md・docs/bench-switch-combined-v0.38.md・docs/selfdestruct-spread-count-v0.39.md・
        # docs/count-condition-switch-return-v0.40.md・docs/heal-counter-status-v0.41.md・docs/power-decisions-v0.42.md・docs/declared-entry-powers-v0.43.md・
        # docs/search-evolution-once-attacks-v0.44.md・docs/conditional-damage-energy-v0.45.md・docs/continuous-powers-v0.46.md・docs/fossil-hidden-info-v0.47.md・
        # docs/effective-pokemon-properties-v0.48.md・docs/virtual-attacks-transformation-v0.49.md・docs/mew-devolution-spray-v0.50.md・docs/discard-to-bench-v0.51.md）
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (149, 151))  # v0.68 で DR8・DR13 を加えた。v0.52 で FJ1・SU1・SU2、v0.53 で ST1・NG1 を加えた、v0.55 で MW1・EM1・SP1・FH1・GL1・GL2・SB1・SB2 を加えた、v0.56 で LS1・RT1・RG1・MY1・MS1・KG1 を加えた、v0.57 で STB1・TG1・FG1・FG2・EX1・VG1・VM1・CH1、v0.58 で RB1〜RB4・TE2・RT1 を加えた、v0.59 で GG1・BL1・CB1・BZ1〜BZ4 を加えた。v0.60 で TS1 を加え、コードのない SS1 を数えた。v0.61 で SH1・SC1・SC2・TD1 を加え、Z9 に停止コードを付けた。v0.62 で MM1・MM2・OM1・OM2 を加え、コードのない ED1 を数えた。v0.63 で QZ1 を加えた  # v0.65 で NT1〜NT3・RX1・FL1・BG1・BG2・KD1 を加えた。v0.66 で CA1・ES1〜ES3 を加えた  # v0.67 で FD1・FD2 を加えた

    def test_boundary(self):
        """相手の控えのカウンターが 0 なら（控えがいない・控えにカウンターがない）、相手の対戦ポケモンのカウンターだけで処理する。控えに 1 個でも
        のっていれば止める（相手の対戦ポケモンのカウンターの数・自分のカウンターに関係なく）。"""
        jynx = mon(JYNX, (PSYCHIC, PSYCHIC, PSYCHIC))
        for bench in ((), (RATTATA,), (RATTATA, RATTATA)):
            state = board(jynx, mon(HITMONCHAN, (FIGHTING,), damage=20), opponent_bench=bench)
            new = play(state, UseAttack(0, 1))
            self.assertEqual([e["amount"] for e in events(new, len(state.log), "damage")], [(20 + 20) * 2])  # エビワラーの弱点 超
        for opponent_damage, bench_damage in ((0, 10), (20, 10), (20, 50)):
            state = board(jynx, mon(HITMONCHAN, (FIGHTING,), damage=opponent_damage), opponent_bench=(RATTATA, mon(RATTATA, damage=bench_damage)))
            with self.subTest(opponent_damage=opponent_damage, bench_damage=bench_damage):
                assert_stops(self, state, UseAttack(0, 1), "UNRESOLVED_OPPONENT_POKEMON_COUNTERS")


class OpponentEnergyDiscardTest(unittest.TestCase):
    """ダメージのあと、相手の対戦ポケモンのエネルギーカードを 1 枚、ワザを使ったプレイヤーが選んでトラッシュする（はかいこうせん 2・うずしお・はかいでんぱ・
    はかいビーム）。はかいでんぱ・はかいビームはコインの「おもて」のときだけ。"""

    ATTACKS = [(DRAGONAIR, 1, (FIRE,) * 4, False), (FOSSIL_GOLDUCK, 1, (WATER, WATER, WATER), False), (DARK_VAPOREON, 1, (WATER, WATER, WATER), False),
               (LT_SURGES_MAGNEMITE_30, 0, (LIGHTNING,), True), (SABRINAS_VENONAT, 1, (PSYCHIC, GRASS), True)]

    def test_choice_after_damage(self):
        """決めるのはワザを使ったプレイヤー。選べるのは相手の対戦ポケモンについているエネルギーカード（ついている順）。ダメージのあとに決定を出し、選んだ
        カードを相手のトラッシュに置く（ログ ``discard_attached_energy``）。カードの数は変わらない。"""
        for card, index, energy, on_heads in self.ATTACKS:
            defender = mon(HITMONCHAN, (FIGHTING, WATER, FIGHTING))
            state = with_coin_results(board(mon(card, energy), defender), H)
            waiting = play(state, UseAttack(0, index))
            d = waiting.decision
            with self.subTest(card=card):
                self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices, d.resume), (DISCARD_OPPONENT_ENERGY, 0, 1, 1, "attack"))
                self.assertEqual(list(d.options), list(state.players[1].active.energy))
                order = [k for k in kinds(waiting, len(state.log)) if k in ("damage", "coin_flip")]
                self.assertEqual(order, ["damage", "coin_flip"] if on_heads else ["damage"])  # ダメージ → （コイン）→ 決定
                chosen = d.options[1]
                new = apply_kernel(waiting, ResolveDecision(0, d.id, (chosen,)))
                self.assertNotIn(chosen, new.players[1].active.energy)
                self.assertEqual(new.players[1].discard[-1], chosen)
                self.assertEqual(len(new.players[1].active.energy), 2)
                [log] = events(new, len(waiting.log), "discard_attached_energy")
                self.assertEqual((log["player"], log["energy"], log["attacker"]), (1, chosen, 0))
                self.assertEqual(total_cards(new), total_cards(state))
                self.assertEqual(len(events(new, len(state.log), "coin_flip")), 1 if on_heads else 0)

    def test_coin_tails_keeps_the_energy(self):
        """コインのあるワザは、「うら」ならトラッシュしない（ダメージは与える）。"""
        for card, index, energy, on_heads in self.ATTACKS:
            if not on_heads:
                continue
            state = with_coin_results(board(mon(card, energy), mon(HITMONCHAN, (FIGHTING,))), T)
            new = play(state, UseAttack(0, index))
            with self.subTest(card=card):
                self.assertIsNone(new.decision)
                self.assertEqual(len(new.players[1].active.energy), 1)
                self.assertEqual(len(events(new, len(state.log), "damage")), 1)

    def test_no_energy_no_effect_and_no_coin(self):
        """相手の対戦ポケモンにエネルギーカードがついていなければ、処理の対象がないので、トラッシュしない（ゴルダックの説明「この効果はない」。ほかも
        p.309）。コインのあるワザも、そのときコインを投げない（v0.31 のスーパーデストロイと同じ）。ダメージは与える。"""
        for card, index, energy, on_heads in self.ATTACKS:
            state = board(mon(card, energy), mon(HITMONCHAN))
            new = play(state, UseAttack(0, index))
            with self.subTest(card=card):
                self.assertIsNone(new.decision)
                self.assertEqual(events(new, len(state.log), "coin_flip"), [])
                self.assertEqual(len(events(new, len(state.log), "damage")), 1)
                self.assertEqual(new.turn_number, TURN + 1)

    def test_knocked_out_by_the_damage(self):
        """ダメージで相手の対戦ポケモンが HP 以上になったら、トラッシュしない（コインも投げない。p.309・kyuura の CR-EFFECTS-AFTER-KO）。"""
        for card, index, energy, on_heads in self.ATTACKS:
            state = board(mon(card, energy), mon(HITMONCHAN, (FIGHTING,), damage=60), opponent_bench=(RATTATA,))
            new = play(state, UseAttack(0, index))
            with self.subTest(card=card):
                self.assertEqual(events(new, len(state.log), "coin_flip"), [])
                self.assertEqual(events(new, len(state.log), "discard_attached_energy"), [])
                self.assertTrue(events(new, len(state.log), "knock_out"))

    def test_prevented_damage_still_discards(self):
        """「ダメージを受けない」状態（かたまる）の相手: ダメージの要素だけが無効で、トラッシュはダメージ以外の効果なので有効（p.321）。コインのある
        ワザもコインを投げる（効果を決めるコイン）。"""
        for card, index, energy, on_heads in self.ATTACKS:
            state = with_coin_results(board(mon(card, energy), mon(HITMONCHAN, (FIGHTING,), prevent_damage=TURN - 1)), H)
            new = play(state, UseAttack(0, index), [first])
            with self.subTest(card=card):
                self.assertEqual(len(events(new, len(state.log), "damage_prevented")), 1)
                self.assertEqual(len(events(new, len(state.log), "discard_attached_energy")), 1)

    def test_barrier(self):
        """「ワザをうけない」状態（バリアー）の相手: トラッシュも無効（``effect_prevented``）。コインのあるワザは、コインが決める効果が無効なので、投げるかが
        決められない（HC3 ``UNRESOLVED_PREVENTED_EFFECT_COIN``。宣言の前に止める）。"""
        for card, index, energy, on_heads in self.ATTACKS:
            state = with_barrier(mon(card, energy), mon(MEWTWO, (PSYCHIC, PSYCHIC, PSYCHIC)))
            with self.subTest(card=card):
                if on_heads:
                    assert_stops(self, state, UseAttack(1, index), "UNRESOLVED_PREVENTED_EFFECT_COIN")
                else:
                    new = play(state, UseAttack(1, index))
                    self.assertEqual([e["element"] for e in events(new, len(state.log), "effect_prevented")], [E.ENERGY_DISCARD_ELEMENT])
                    self.assertEqual(len(new.players[0].active.energy), 2)

    def test_transparency(self):
        """「とうめい」（化石の秘密のゴースト）: ダメージの要素で判定し、「おもて」なら同じワザのトラッシュも受けない（T4）。コインのあるワザで「おもて」に
        なると、そのあとのワザのコインを投げるかが決められない（T19b ``UNRESOLVED_EVADED_EFFECT_COIN``）ので、宣言の前に止める。「うら」なら
        トラッシュする。"""
        ghost = mon(HAUNTER, (PSYCHIC, PSYCHIC))
        for card, index, energy, on_heads in self.ATTACKS:
            state = board(mon(card, energy), ghost)
            with self.subTest(card=card):
                if on_heads:
                    assert_stops(self, state, UseAttack(0, index), "UNRESOLVED_EVADED_EFFECT_COIN")
                    continue
                evaded = play(with_coin_results(state, H), UseAttack(0, index))
                self.assertIsNone(evaded.decision)
                self.assertEqual(len(evaded.players[1].active.energy), 2)
                hit = play(with_coin_results(state, T), UseAttack(0, index))
                self.assertEqual(hit.decision.kind, DISCARD_OPPONENT_ENERGY)

    def test_invalid_answers_keep_the_decision(self):
        """相手の答え・選べるもの以外（自分のエネルギー）・0 枚・2 枚は拒否し、決定は待ったまま（状態は変わらない）。"""
        state = board(mon(DRAGONAIR, (FIRE,) * 4), mon(HITMONCHAN, (FIGHTING, FIGHTING)))
        waiting = play(state, UseAttack(0, 1))
        d = waiting.decision
        snapshot = full(waiting)
        own = waiting.players[0].active.energy[0]
        for player, choice, code in ((1, d.options[:1], "NOT_YOUR_DECISION"), (0, (own,), "INVALID_CHOICE"),
                                     (0, (), "INVALID_CHOICE_COUNT"), (0, tuple(d.options), "INVALID_CHOICE_COUNT")):
            with self.subTest(player=player, choice=choice), self.assertRaises(IllegalActionError) as raised:
                apply_command(waiting, ResolveDecision(player, d.id, tuple(choice)))
            self.assertEqual(raised.exception.code, code)
        self.assertEqual(full(waiting), snapshot)

    def test_confusion_tails(self):
        """こんらんの「うら」なら、ダメージもトラッシュもない（こんらんの 20 だけ）。"""
        state = with_coin_results(board(mon(DRAGONAIR, (FIRE,) * 4, confusion=True), mon(HITMONCHAN, (FIGHTING,))), T)
        new = play(state, UseAttack(0, 1))
        self.assertIn("confusion_damage", kinds(new, len(state.log)))
        self.assertEqual(len(new.players[1].active.energy), 1)


class CoinGateTest(unittest.TestCase):
    """コインの「うら」で、ワザが失敗する（``FailOnTailsDamage``。p.323）ワザと、相手にダメージを与えられない（``NoDamageOnTails``）ワザ。"""

    FAIL = [(DARK_RATICATE, 1, (FIRE,) * 3, 50), (BROCKS_DIGLETT, 0, (FIGHTING,), 20), (LT_SURGES_SPEAROW, 1, (FIRE, FIRE), 40),
            (GIOVANNIS_NIDORAN_F, 0, (GRASS,), 20), (BLAINES_RHYHORN, 0, (FIGHTING,), 30), (BLAINES_DODUO, 0, (FIRE,), 20)]

    def test_fail_on_tails(self):
        """「おもて」ならダメージの目安の数字ぶん、「うら」ならワザは失敗する（ログ ``attack_failed``。ダメージはない。ワザは使ったことになり、番は終わる）。
        コインは 1 枚。"""
        for card, index, energy, damage in self.FAIL:
            state = board(mon(card, energy), mon(RATTATA, damage=0))
            heads = play(with_coin_results(state, H), UseAttack(0, index))
            tails = play(with_coin_results(state, T), UseAttack(0, index))
            with self.subTest(card=card):
                self.assertEqual([e["amount"] for e in events(heads, len(state.log), "damage")], [damage * (2 if card in (BROCKS_DIGLETT, BLAINES_RHYHORN) else 1)])
                self.assertEqual(events(tails, len(state.log), "damage"), [])
                self.assertEqual([e["reason"] for e in events(tails, len(state.log), "attack_failed")], ["coin"])
                self.assertEqual(len(events(tails, len(state.log), "coin_flip")), 1)
                self.assertEqual(tails.turn_number, TURN + 1)

    def test_drill_tackle_needs_both_heads(self):
        """ドリルタックル: コインを 2 枚投げ、2 枚とも「おもて」のときだけ 70（コラッタは闘 ×2 で 140）。1 枚でも「うら」なら失敗（「おもて」の数 × の
        ダメージではない）。どの結果でもコインは 2 枚投げる。"""
        for coins, expected in (((H, H), [140]), ((H, T), []), ((T, H), []), ((T, T), [])):
            state = with_coin_results(board(mon(BROCKS_RHYHORN, (FIGHTING, FIGHTING)), mon(RATTATA)), *coins)
            new = play(state, UseAttack(0, 0))
            with self.subTest(coins=coins):
                self.assertEqual([e["amount"] for e in events(new, len(state.log), "damage")], expected)
                self.assertEqual(len(events(new, len(state.log), "coin_flip")), 2)
                self.assertEqual(bool(events(new, len(state.log), "attack_failed")), not expected)

    def test_horn_hazard_is_not_a_failure(self):
        """つのでつつく: 「うら」なら相手にダメージを与えない。ワザの失敗ではない（説明に「失敗」がない。v0.2d の CoinFlipDamage・kyuura の
        CR-TRANSPARENCY-NOT-FAILURE と同じ読み方）ので、``attack_failed`` を残さない。ワザは使ったことになり、番は終わる。"""
        state = board(mon(NIDORAN_M, (GRASS,)), mon(HITMONCHAN, (FIGHTING,)))
        heads = play(with_coin_results(state, H), UseAttack(0, 0))
        tails = play(with_coin_results(state, T), UseAttack(0, 0))
        self.assertEqual([e["amount"] for e in events(heads, len(state.log), "damage")], [30])
        self.assertEqual(events(tails, len(state.log), "damage"), [])
        self.assertEqual(events(tails, len(state.log), "attack_failed"), [])
        self.assertEqual([e["kind"] for e in events(tails, len(state.log)) if e["kind"] in ("attack", "coin_flip", "turn_end")],
                         ["attack", "coin_flip", "turn_end"])
        self.assertEqual(tails.turn_number, TURN + 1)

    def test_coin_that_only_decides_void_damage(self):
        """「ダメージを受けない」状態の相手に、ダメージの要素だけを決めるコイン（失敗するワザ 7・つのでつつく）を投げるかは決められない（v0.4b の
        ``UNRESOLVED_PREVENTED_COIN_DAMAGE``。kyuura の UQ-COIN-IN-NULLIFIED-ELEMENT）。こんらんのコインの前に止める。"""
        cases = [(card, index, energy) for card, index, energy, _ in self.FAIL] + [(BROCKS_RHYHORN, 0, (FIGHTING, FIGHTING)), (NIDORAN_M, 0, (GRASS,))]
        for (card, index, energy), confused in itertools.product(cases, (False, True)):
            extra = {"confusion": True} if confused else {}
            state = board(mon(card, energy, **extra), mon(HITMONCHAN, (FIGHTING,), prevent_damage=TURN - 1))
            with self.subTest(card=card, confused=confused):
                assert_stops(self, state, UseAttack(0, index), "UNRESOLVED_PREVENTED_COIN_DAMAGE")

    def test_transparency_coin_after_the_attack_coin(self):
        """「とうめい」のゴーストには、ワザのコイン（失敗・ダメージを与えられない）を先に投げ、「おもて」でダメージの要素を処理するときに「とうめい」の
        コインを投げる（T40）。"""
        for card, index, energy in ((NIDORAN_M, 0, (GRASS,)), (DARK_RATICATE, 1, (FIRE, FIRE, FIRE))):
            state = with_coin_results(board(mon(card, energy), mon(HAUNTER, (PSYCHIC,))), H, H)
            new = play(state, UseAttack(0, index))
            with self.subTest(card=card):
                flips = events(new, len(state.log), "coin_flip")
                self.assertEqual([f["source"] for f in flips], ["attack", "power"])
                self.assertTrue(events(new, len(state.log), "attack_evaded"))


class CloysterTest(unittest.TestCase):
    """からではさむ: 1 枚のコインで、「おもて」ならダメージとマヒ、「うら」ならワザの失敗。マヒのためにコインを投げ直さない。"""

    def cloyster(self, **extra):
        return mon(CLOYSTER, (WATER, WATER), **extra)

    def test_one_coin_decides_damage_and_paralysis(self):
        state = board(self.cloyster(), mon(HITMONCHAN, (FIGHTING,)))
        heads = play(with_coin_results(state, H), UseAttack(0, 0))
        self.assertEqual([e["amount"] for e in events(heads, len(state.log), "damage")], [30])
        self.assertTrue(heads.players[1].active.conditions.paralyzed)
        self.assertEqual(len(events(heads, len(state.log), "coin_flip")), 1)
        tails = play(with_coin_results(state, T), UseAttack(0, 0))
        self.assertEqual(events(tails, len(state.log), "damage"), [])
        self.assertFalse(tails.players[1].active.conditions.paralyzed)
        self.assertEqual(len(events(tails, len(state.log), "attack_failed")), 1)
        self.assertEqual(len(events(tails, len(state.log), "coin_flip")), 1)

    def test_prevented_damage_still_paralyzes(self):
        """「ダメージを受けない」状態の相手には、ダメージだけが無効で、マヒは有効なので、コインを投げる（kyuura の CR-STICKY-VS-PREVENTED と同じ形）。"""
        state = with_coin_results(board(self.cloyster(), mon(HITMONCHAN, (FIGHTING,), prevent_damage=TURN - 1)), H)
        new = play(state, UseAttack(0, 0))
        self.assertEqual(len(events(new, len(state.log), "damage_prevented")), 1)
        self.assertTrue(new.players[1].active.conditions.paralyzed)

    def test_barrier_stops(self):
        """「ワザをうけない」状態（バリアー）の相手には、コインが決めるダメージとマヒがどちらも無効なので、投げるかが決められない（HC3）。"""
        state = with_barrier(self.cloyster(), mon(MEWTWO, (PSYCHIC, PSYCHIC, PSYCHIC)))
        assert_stops(self, state, UseAttack(1, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")

    def test_already_paralyzed_defender(self):
        """相手がすでにマヒ状態（前の自分の番にマヒ状態になった）なら、マヒの再付与で回復する番は変わらないので、止めずに処理する（二重のマヒ状態には
        ならない。p.322。マヒになった番は変えない）。回復する番が変わる場合（v0.3b の ``UNRESOLVED_REPARALYSIS_RECOVERY_TURN``）は、要素の並びの最初の
        ``ReparalysisGuard`` がコインの前に確かめる（``test_programs``。自然な対戦では起こらない。v0.3b）。"""
        state = with_coin_results(board(self.cloyster(), mon(HITMONCHAN, (FIGHTING,), paralysis=TURN - 1)), H)
        new = play(state, UseAttack(0, 0))
        self.assertEqual(new.players[1].active.conditions.exclusive.turn, TURN - 1)
        self.assertEqual([e["amount"] for e in events(new, len(state.log), "damage")], [30])

    def test_knocked_out_target_is_not_paralyzed(self):
        state = with_coin_results(board(self.cloyster(), mon(RATTATA, damage=10)), H)
        new = play(state, UseAttack(0, 0))
        self.assertEqual(events(new, len(state.log), "special_condition"), [])
        self.assertTrue(events(new, len(state.log), "knock_out"))


class OwnBenchDamageTest(unittest.TestCase):
    """ミニじしん: 相手の対戦ポケモンに 40。自分の控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ 10（p.320 のダメージの (4)）。"""

    def diglett(self, **extra):
        return mon(BROCKS_DIGLETT, (FIGHTING, FIGHTING), **extra)

    def bench_logs(self, new, since):
        return [(e["pokemon_id"], e["amount"]) for e in events(new, since, "damage") if e.get("target") == "self_bench"]

    def test_every_own_bench_pokemon_takes_10_without_weakness_or_resistance(self):
        """自分の控えの全員に 10（並びの順）。コラッタ（弱点 闘）も第4弾のズバット（抵抗力 闘 -30）も 10（弱点・抵抗力は計算しない）。ワザを使った
        ディグダと相手の控えは受けない。ログの ``target`` は ``self_bench``。"""
        state = board(self.diglett(), mon(HITMONCHAN, (FIGHTING,)), bench=(RATTATA, ROCKET_ZUBAT, CHARMANDER), opponent_bench=(RATTATA,))
        new = play(state, UseAttack(0, 1))
        bench = state.players[0].bench
        self.assertEqual(self.bench_logs(new, len(state.log)), [(p.pokemon_id, 10) for p in bench])
        self.assertTrue(all(e.get("ignore_weakness_resistance") for e in events(new, len(state.log), "damage") if e.get("target") == "self_bench"))
        self.assertEqual([p.damage for p in new.players[0].bench], [10, 10, 10])
        self.assertEqual(new.players[0].active.damage, 0)
        self.assertEqual(new.players[1].bench[0].damage, 0)

    def test_no_bench(self):
        state = board(self.diglett(), mon(HITMONCHAN, (FIGHTING,)))
        new = play(state, UseAttack(0, 1))
        self.assertEqual([e.get("target") for e in events(new, len(state.log), "damage")], [None])

    def test_pluspower_and_defender(self):
        """ディグダのプラスパワーは相手の対戦ポケモンへのダメージだけに足す（p.257「(控えポケモンへのダメージは、そのまま)」）。ディフェンダーのついた
        自分の控えは 10 − 20 で 0（「ダメージを受けなかった」）。"""
        state = board(self.diglett(trainers=[(PLUSPOWER, TURN)]), mon(HITMONCHAN, (FIGHTING,)),
                      bench=(RATTATA, mon(RATTATA, trainers=[(DEFENDER, TURN)])))
        new = play(state, UseAttack(0, 1))
        self.assertEqual([e["amount"] for e in events(new, len(state.log), "damage") if e.get("target") is None], [50])
        self.assertEqual([amount for _, amount in self.bench_logs(new, len(state.log))], [10, 0])

    def test_own_bench_knock_out_gives_the_opponent_a_prize(self):
        """自分の控えがきぜつしたら、相手（きぜつしたポケモンの相手側のプレイヤー）がサイドを取る（p.323）。相手の対戦ポケモンもきぜつすれば、1 つのワザ
        による同時のきぜつで、両方が取る。"""
        state = board(self.diglett(), mon(HITMONCHAN, (FIGHTING,), damage=30), bench=(mon(RATTATA, damage=30),), opponent_bench=(RATTATA,))
        new = play(state, UseAttack(0, 1), [first, first])
        knocked = [(e["player"], e["pokemon"]) for e in events(new, len(state.log), "knock_out")]
        self.assertEqual(len(knocked), 2)
        self.assertEqual(sorted(len(p.prizes) for p in new.players), [5, 5])
        self.assertEqual(new.players[0].bench, [])

    def test_own_attack_does_not_trigger_counterattack_or_guts(self):
        """自分のワザのダメージなので、自分の控えのカイリキーの「はんげき」・サカキのカイリキーの「こんじょう」ははたらかない（「相手のワザによって」）。"""
        state = board(self.diglett(), mon(HITMONCHAN, (FIGHTING,)), bench=(mon(MACHAMP, damage=0), mon(GIOVANNIS_MACHAMP, damage=90)))
        new = play(state, UseAttack(0, 1), [first])
        self.assertEqual(events(new, len(state.log), "counterattack"), [])
        self.assertEqual(events(new, len(state.log), "ko_prevention_declared"), [])
        self.assertEqual(len(events(new, len(state.log), "knock_out")), 1)  # サカキのカイリキー（HP 100）が 100 できぜつ

    def test_transparency_on_own_bench(self):
        """自分の控えの「とうめい」のゴーストも判定する（自分のワザでもはたらく。T8）。相手の対戦ポケモンもゴーストなら、2 匹の「とうめい」のコインの順番が
        決められない（T27 ``UNRESOLVED_TRANSPARENCY_COIN_ORDER``）。"""
        state = with_coin_results(board(self.diglett(), mon(HITMONCHAN, (FIGHTING,)), bench=(mon(HAUNTER),)), H)
        new = play(state, UseAttack(0, 1))
        self.assertEqual([e["pokemon_id"] for e in events(new, len(state.log), "attack_evaded")], [state.players[0].bench[0].pokemon_id])
        both = board(self.diglett(), mon(HAUNTER, (PSYCHIC,)), bench=(mon(HAUNTER),))
        assert_stops(self, both, UseAttack(0, 1), "UNRESOLVED_TRANSPARENCY_COIN_ORDER")

    def test_serialization_and_cards(self):
        state = board(self.diglett(), mon(HITMONCHAN, (FIGHTING,)), bench=(RATTATA,))
        new = play(state, UseAttack(0, 1))
        self.assertEqual(serialization_problems(new), [])
        self.assertEqual(total_cards(new), total_cards(state))


class CoinBenchDamageTest(unittest.TestCase):
    """かけぬける: 相手の対戦ポケモンに 20 → コインが「おもて」なら、相手の控えポケモンを 1 匹（ワザを使ったプレイヤーが）選び、20（弱点・抵抗力なし）。"""

    def rhyhorn(self, **extra):
        return mon(BLAINES_RHYHORN, (FIRE, FIRE, FIRE), **extra)

    def test_heads_choose_one_bench_pokemon(self):
        """「おもて」なら決定 ``SELECT_POKEMON``（決めるのはワザを使ったプレイヤー。選べるのは相手の控えの並び。1 匹）。選んだポケモンに 20（コラッタは
        弱点 闘だが 20）。相手の対戦ポケモンへのダメージが先。"""
        state = with_coin_results(board(self.rhyhorn(), mon(HITMONCHAN, (FIGHTING,)), opponent_bench=(RATTATA, ROCKET_ZUBAT)), H)
        waiting = play(state, UseAttack(0, 1))
        d = waiting.decision
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices), (SELECT_POKEMON, 0, 1, 1))
        self.assertEqual(list(d.options), [p.pokemon_id for p in state.players[1].bench])
        self.assertEqual([e["kind"] for e in events(waiting, len(state.log)) if e["kind"] in ("damage", "coin_flip")], ["damage", "coin_flip"])
        new = apply_kernel(waiting, ResolveDecision(0, d.id, (d.options[0],)))
        [log] = [e for e in events(new, len(waiting.log), "damage")]
        self.assertEqual((log["target"], log["pokemon_id"], log["amount"]), ("opponent_bench", d.options[0], 20))
        self.assertEqual([p.damage for p in new.players[1].bench], [20, 0])

    def test_tails_and_empty_bench(self):
        """「うら」なら控えへのダメージはない。相手に控えがいなければ、処理の対象がないのでコインを投げない（p.309）。"""
        tails = with_coin_results(board(self.rhyhorn(), mon(HITMONCHAN, (FIGHTING,))), T)
        new = play(tails, UseAttack(0, 1))
        self.assertIsNone(new.decision)
        self.assertEqual(len(events(new, len(tails.log), "coin_flip")), 1)
        empty = board(self.rhyhorn(), mon(HITMONCHAN, (FIGHTING,)), opponent_bench=())
        new = play(empty, UseAttack(0, 1))
        self.assertEqual(events(new, len(empty.log), "coin_flip"), [])
        self.assertEqual(len(events(new, len(empty.log), "damage")), 1)

    def test_defender_knocked_out_still_hits_the_bench(self):
        """相手の対戦ポケモンが 20 できぜつしても、控えへのダメージは処理する（対象が違う。p.309）。控えも HP 以上なら同時のきぜつ。"""
        state = with_coin_results(board(self.rhyhorn(), mon(RATTATA, damage=20), opponent_bench=(mon(RATTATA, damage=20), RATTATA)), H)
        new = settle(play(state, UseAttack(0, 1), [first]))
        self.assertEqual(len(events(new, len(state.log), "knock_out")), 2)
        self.assertEqual(len(new.players[0].prizes), 4)

    def test_pluspower_and_defender(self):
        state = with_coin_results(board(self.rhyhorn(trainers=[(PLUSPOWER, TURN)]), mon(HITMONCHAN, (FIGHTING,)),
                                        opponent_bench=(mon(RATTATA, trainers=[(DEFENDER, TURN)]),)), H)
        new = play(state, UseAttack(0, 1), [first])
        amounts = [(e.get("target"), e["amount"]) for e in events(new, len(state.log), "damage")]
        self.assertEqual(amounts, [(None, 30), ("opponent_bench", 0)])

    def test_decision_after_damage_trigger_is_carried(self):
        """相手の対戦ポケモンへのダメージで「ダメージを受けたとき」の効果（カイリキーの「はんげき」・わるいカメールの「こうらがえし」）がはたらいたあとに
        控えを選ぶ場面。v0.33 はエンジンの未対応として宣言の前に止めていた（``UNSUPPORTED_DECISION_AFTER_DAMAGE_TRIGGER``）。v0.34 から、その効果を決定を
        またいで運び、控えへのダメージのあと（ダメージの要素がすべて終わったあと。p.89）に処理する（境界は tests/test_barrier_resume_coin_bonus_v0_34.py）。"""
        for defender, kind in ((mon(MACHAMP, (FIGHTING,)), "counterattack"), (mon(DARK_WARTORTLE, (WATER,), retaliation_received=TURN - 1), "retaliation")):
            state = with_coin_results(board(self.rhyhorn(), defender, opponent_bench=(RATTATA,)), H)
            with self.subTest(defender=defender["card"]):
                waiting = play(state, UseAttack(0, 1))
                self.assertEqual(waiting.decision.kind, SELECT_POKEMON)
                new = apply_kernel(waiting, ResolveDecision(0, waiting.decision.id, first(waiting.decision)))
                after = [e["kind"] for e in events(new, len(waiting.log)) if e["kind"] in ("damage", kind)]
                self.assertEqual(after[:2], ["damage", kind])

    def test_guts_survives_the_bench_choice(self):
        """相手の対戦ポケモン（サカキのカイリキー）がワザのダメージで HP 以上になったあとに控えを選ぶ決定をはさんでも、きぜつの判定で「こんじょう」を
        使えるか（受けたときの特殊状態の写し）は決定をまたいで運ぶ（``carry``）。決定のあと、持ち主に「こんじょう」の決定を出す。"""
        state = with_coin_results(board(self.rhyhorn(), mon(GIOVANNIS_MACHAMP, (FIGHTING,), damage=80), opponent_bench=(RATTATA,)), H)
        waiting = play(state, UseAttack(0, 1))
        self.assertEqual(waiting.decision.kind, SELECT_POKEMON)
        new = apply_kernel(waiting, ResolveDecision(0, waiting.decision.id, first(waiting.decision)))
        self.assertEqual((new.decision.kind, new.decision.player), ("ko_prevention", 1))

    def test_invalid_answers_keep_the_decision(self):
        state = with_coin_results(board(self.rhyhorn(), mon(HITMONCHAN, (FIGHTING,)), opponent_bench=(RATTATA, RATTATA)), H)
        waiting = play(state, UseAttack(0, 1))
        d = waiting.decision
        snapshot = full(waiting)
        own = waiting.players[0].active.pokemon_id
        for player, choice, code in ((1, d.options[:1], "NOT_YOUR_DECISION"), (0, (own,), "INVALID_CHOICE"),
                                     (0, (), "INVALID_CHOICE_COUNT"), (0, tuple(d.options), "INVALID_CHOICE_COUNT")):
            with self.subTest(player=player, choice=choice), self.assertRaises(IllegalActionError) as raised:
                apply_command(waiting, ResolveDecision(player, d.id, tuple(choice)))
            self.assertEqual(raised.exception.code, code)
        self.assertEqual(full(waiting), snapshot)


class ReusedTypeTest(unittest.TestCase):
    """既存の型で登録したワザの、v0.33 のカードでの値（ふきとばしは相手が選ぶ・しかえしは自分のカウンター × 10・すてみタックルは自分に 20）。"""

    def test_whirlwind_is_chosen_by_the_opponent(self):
        state = board(mon(LT_SURGES_SPEAROW, (FIRE,)), mon(HITMONCHAN, (FIGHTING,)), opponent_bench=(RATTATA, ROCKET_ZUBAT))
        waiting = play(state, UseAttack(0, 0))
        self.assertEqual((waiting.decision.kind, waiting.decision.player), (FORCED_SWITCH, 1))
        alone = board(mon(LT_SURGES_SPEAROW, (FIRE,)), mon(HITMONCHAN, (FIGHTING,)), opponent_bench=())
        new = play(alone, UseAttack(0, 0))
        self.assertEqual([e["reason"] for e in events(new, len(alone.log), "forced_switch_skipped")], [E.NO_BENCH])

    def test_revenge_counts_own_counters(self):
        for damage, expected in ((0, []), (20, [20]), (40, [40])):
            state = board(mon(BLAINES_DODUO, (FIRE, FIRE), damage=damage), mon(HITMONCHAN, (FIGHTING,)))
            new = play(state, UseAttack(0, 1))
            with self.subTest(damage=damage):
                self.assertEqual([e["amount"] for e in events(new, len(state.log), "damage") if e["amount"] > 0], expected)

    def test_take_down(self):
        state = board(mon(GIOVANNIS_NIDORAN_F, (FIRE, FIRE)), mon(HITMONCHAN, (FIGHTING,)))
        new = play(state, UseAttack(0, 1))
        self.assertEqual((new.players[1].active.damage, new.players[0].active.damage), (30, 20))


# 先読みの方法ごとの一致を確かめる相手の盤面（相手の対戦ポケモン, 相手の控え）
PARITY_OPPONENTS = {
    "plain": (mon(HITMONCHAN, (FIGHTING, FIGHTING)), (RATTATA,)),
    "hurt": (mon(HITMONCHAN, (FIGHTING,), damage=50), (RATTATA,)),
    "prevented": (mon(HITMONCHAN, (FIGHTING,), prevent_damage=TURN - 1), (RATTATA,)),
    "no bench": (mon(HITMONCHAN), ()),
    "machamp": (mon(MACHAMP, (FIGHTING,)), (RATTATA,)),
    "ghost": (mon(HAUNTER, (PSYCHIC,)), (mon(RATTATA, damage=50),)),
}


class PreflightParityTest(unittest.TestCase):
    """28 のワザを、相手の状態・自分のダメージ・こんらん・コインの組み合わせで使い、先読みの方法のどれでも結果（受け付けたら形式 10 の書き出しと乱数、
    拒否したら例外の型とコード）が同じ（決定には最初の選べるものから答える）。"""

    def outcome(self, state, command, mode):
        try:
            new = apply_kernel(state, command, preflight=mode)
            out = [(full(new), rng_fingerprint(new.rng))]
            while new.decision is not None and new.decision.resume == "attack":
                d = new.decision
                new = apply_kernel(new, ResolveDecision(d.player, d.id, tuple(d.options[:max(1, d.min_choices)])), preflight=mode)
                out.append((full(new), rng_fingerprint(new.rng)))
            return out
        except EngineError as error:
            return [(type(error).__name__, error.code)]

    def test_every_attack_in_every_mode(self):
        pool = load_card_pool()
        energy_of = {"water": WATER, "psychic": PSYCHIC, "grass": GRASS, "fighting": FIGHTING, "lightning": LIGHTNING}
        checked = 0
        for (card, index), (name, (opponent, opponent_bench)), damage, confused, coins in itertools.product(
                EXPECTED, PARITY_OPPONENTS.items(), (0, 30), (False, True), ((H,) * 4, (T,) * 4, (H, T, T, H))):
            cost = pool.get(card).attacks[index].cost
            energy = [energy_of.get(t.value, FIRE) for t in cost]
            attacker = mon(card, energy, damage=damage, **({"confusion": True} if confused else {}))
            state = with_coin_results(build_test_state([
                {"active": attacker, "bench": [RATTATA, mon(RATTATA, damage=30)]},
                {"active": opponent, "bench": list(opponent_bench)},
            ], turn_number=TURN), *coins)
            results = [self.outcome(state, UseAttack(0, index), mode) for mode in PREFLIGHT_MODES]
            with self.subTest(card=card, attack=index, opponent=name, damage=damage, confused=confused, coins=coins[:2]):
                self.assertEqual(results[1], results[0])
                self.assertEqual(results[2], results[0])
            checked += 1
        self.assertEqual(checked, 28 * 6 * 2 * 2 * 3)


if __name__ == "__main__":
    unittest.main()
