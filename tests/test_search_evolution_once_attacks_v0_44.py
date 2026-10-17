"""v0.44: 検索・進化・1 度だけ使えるワザのポケモン 14 枚とトレーナーのサカキ（docs/search-evolution-once-attacks-v0.44.md）。

ディグダ（PMCG4-038）・ニャース（PMCG4-047）・エリカのフシギダネ（PMCG5-007）・カスミのヒトデマン（PMCG5-027）・コイキング（PMCG4-020）・キョウのコクーン（PMCG6-011。
［うか］）・キョウのスピアー（PMCG6-018）・カモネギ（PMCG1-063）・サカキのコイキング（PMCG6-037）・サカキのギャラドス（PMCG6-040）・ナツメのバリヤード（PMCG6-046）・
カツラのマンキー（PMCG6-056）・_____のラッキー（PMCG6-075）・サカキのペルシアン（PMCG6-071。［ボスをよぶ］）と、トレーナーのサカキ（PMCG6-095）。どれも kyuura データの
採用（処理に使う文面は kyuura の印刷の文面。スターブーメランだけ kyuura の最新の説明 LD-PMCG5-027-ATK0。採用したデータのコミット ecb2d69）と pcg-search.com の同じ版の
ページとの照合。ガイドブックは読んでいない。

根拠にした既存の記録: p.323 の 12（「ワザを使った」ことになる場合。v0.3d の A12）・GR-2000-P307-CARD-OVER-RULE（カードの文面がルールに優先する）・
GR-2000-P309-ATTACK-PROCEDURE（対象のない内容は無視する）・GR-2000-P309-EVOLUTION-BY-NAME・CR-SHELL-ATTACK-STAR-BOOMERANG と、エンジンの v0.4a（進化）・v0.24（見せて
手札に加える）・v0.25（ポケモン育て屋さん）・v0.36（RD9）・v0.39（GS1）・v0.42（つきのちから）・v0.43（場に出たときの特殊能力・PW3）の記録。新しい未解決は FC1
（``UNRESOLVED_STATED_CARDS_SHORT``）・TR1（``UNRESOLVED_TRAINER_WITHOUT_TARGET``）と、v0.44 ではコードのない問いとした GV1（v0.45 で、つきのちからで起こることが
分かり、停止コード ``UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK`` を付けた。tests/test_conditional_damage_energy_v0_45.py の ``Gv1Test``）。
"""

from __future__ import annotations

import copy
import pathlib
import pickle
import re
import unittest

from kyuura_engine import (
    EndTurn,
    EngineError,
    EvolvePokemon,
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine import evolution
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.decisions import (
    DISCARD_TO_DECK_TOP,
    TAKE_PRIZE,
    ENTRY_POWER,
    HAND_TO_DECK,
    SEARCH_DECK,
    SELECT_ATTACK,
    SELECT_POKEMON,
)
from kyuura_engine.resolution import PREFLIGHT_MODES, programs, v013_checks
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.state import Phase
from scripts import check_card_sources as cs
from scripts.extract_kyuura_cards import KYUURA_COMMIT
from tests.helpers import (
    ATTACK_TYPES_SINCE_V0_17,
    BLAINES_MANKEY,
    BLANK_CHANSEY,
    CHANSEY,
    CLEFAIRY,
    DARK_PERSIAN,
    DIGLETT,
    ERIKAS_BULBASAUR,
    FARFETCHD,
    FIGHTING,
    FIRE,
    GIOVANNI,
    GIOVANNIS_GYARADOS,
    GIOVANNIS_MACHAMP,
    GIOVANNIS_MACHOKE,
    GIOVANNIS_MACHOP,
    GIOVANNIS_MAGIKARP,
    GIOVANNIS_MEOWTH,
    GIOVANNIS_PERSIAN,
    GRASS,
    GYARADOS,
    HITMONCHAN,
    KOGAS_BEEDRILL,
    KOGAS_KAKUNA,
    KOGAS_WEEDLE,
    LIGHTNING,
    MAGIKARP,
    MEOWTH,
    MISTYS_MAGIKARP,
    MISTYS_STARYU,
    MUK,
    PERSIAN,
    PLUSPOWER,
    POKEMON_BREEDER,
    POTION,
    PSYCHIC,
    RATTATA,
    ROCKET_DIGLETT,
    ROCKET_MAGIKARP,
    ROCKET_MEOWTH,
    SABRINAS_MR_MIME,
    STARYU,
    SWITCH,
    V0_44_CARDS,
    V0_44_POKEMON,
    WATER,
    H,
    T,
    apply_kernel,
    with_coin_results,
)
from tests.log_audit import serialization_problems
from tests.test_barrier_resume_coin_bonus_v0_34 import assert_stops, events
from tests.test_declared_entry_powers_v0_43 import (
    answer,
    attack,
    board,
    card_count,
    card_of,
    cards_in,
    kinds,
    mon as mon43,
    pid_of,
    pokemon_of,
    power,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "search-evolution-once-attacks-v0.44.md"
TURN = 7
F, W, G, P, R, L = FIGHTING, WATER, GRASS, PSYCHIC, FIRE, LIGHTNING
FC1 = "UNRESOLVED_STATED_CARDS_SHORT"
TR1 = "UNRESOLVED_TRAINER_WITHOUT_TARGET"
RD9 = "UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT"
GS1 = "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE"
PW3 = "UNRESOLVED_POWER_ZERO_CARDS"
# 登録の実装の型と値（カード id, ワザの位置）
EXPECTED = {
    (ROCKET_DIGLETT, 0): (E.ChooseOpponentPokemonDamage, {"damage": 10}),
    (ROCKET_DIGLETT, 1): (E.DamageOnly, {}),
    (ROCKET_MEOWTH, 0): (E.CoinChooseOpponentPokemonDamage, {"damage": 20}),
    (ERIKAS_BULBASAUR, 0): (E.SleepOpponent, {}),
    (ERIKAS_BULBASAUR, 1): (E.SearchTrainerOnHeads, {}),
    (MISTYS_STARYU, 0): (E.DamageThenReturnSelfToHandOnHeads, {}),
    (ROCKET_MAGIKARP, 0): (E.DamageOnly, {}),
    (ROCKET_MAGIKARP, 1): (E.EvolveSelfFromDeck, {"evolves_from": "コイキング"}),
    (KOGAS_KAKUNA, 0): (E.SpecialPoisonOnHeadsWithoutDamage, {"poison_damage": 20}),
    (KOGAS_BEEDRILL, 0): (E.DamageThenPoisonAndParalyzeOnHeads, {}),
    (KOGAS_BEEDRILL, 1): (E.OnceAfterEntryNoDamageOnTails, {}),
    (FARFETCHD, 0): (E.OnceAfterEntryNoDamageOnTails, {}),
    (FARFETCHD, 1): (E.DamageOnly, {}),
    (GIOVANNIS_MAGIKARP, 0): (E.OnceAfterEntryNoDamageOnTails, {}),
    (GIOVANNIS_MAGIKARP, 1): (E.CoinFlipDamage, {"coins": 3, "damage_per_heads": 10}),
    (GIOVANNIS_GYARADOS, 0): (E.CoinsAllHeadsSpreadDamageExceptSelf, {"coins": 2, "damage": 20}),
    (GIOVANNIS_GYARADOS, 1): (E.DamageThenSwitchOpponentIfNotKnockedOut, {}),
    (SABRINAS_MR_MIME, 0): (E.ReturnHandThenRevealBasicEnergy, {"max_cards": 3}),
    (SABRINAS_MR_MIME, 1): (E.DamageOnly, {}),
    (BLAINES_MANKEY, 0): (E.CoinPutOpponentDiscardOnDeckTop, {}),
    (BLAINES_MANKEY, 1): (E.CoinFlipDamage, {"coins": 3, "damage_per_heads": 10}),
    (BLANK_CHANSEY, 0): (E.CoinDrawOrReturnHandToDeck, {"draw": 2, "count": 2}),
    (BLANK_CHANSEY, 1): (E.CoinBonusDamage, {"bonus": 30}),
    (GIOVANNIS_PERSIAN, 0): (E.CoinBonusDamage, {"bonus": 20}),
}
ONCE = {(KOGAS_BEEDRILL, 1), (FARFETCHD, 0), (GIOVANNIS_MAGIKARP, 0)}
# pcg-search.com の対象の版（サイトの一覧の番号）
EDITIONS = {ROCKET_DIGLETT: "038/065", ROCKET_MEOWTH: "047/065", ERIKAS_BULBASAUR: "004/096", MISTYS_STARYU: "033/096", ROCKET_MAGIKARP: "023/065",
            KOGAS_KAKUNA: "006/098", KOGAS_BEEDRILL: "007/098", FARFETCHD: "064/096", GIOVANNIS_MAGIKARP: "039/098", GIOVANNIS_GYARADOS: "040/098",
            SABRINAS_MR_MIME: "054/098", BLAINES_MANKEY: "057/098", BLANK_CHANSEY: "097/098", GIOVANNIS_PERSIAN: "073/098", GIOVANNI: "090/098"}


# 進化しているポケモンの下のカード（build_test_state の "evolved_from"）
BELOW = {KOGAS_KAKUNA: KOGAS_WEEDLE, KOGAS_BEEDRILL: [KOGAS_WEEDLE, KOGAS_KAKUNA], GIOVANNIS_GYARADOS: GIOVANNIS_MAGIKARP,
         GIOVANNIS_PERSIAN: GIOVANNIS_MEOWTH, GYARADOS: MAGIKARP, GIOVANNIS_MACHOKE: GIOVANNIS_MACHOP,
         GIOVANNIS_MACHAMP: [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE]}


def mon(card, energy=(), **extra):
    spec = mon43(card, energy, **extra)
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def find(state, player, card, nth=0):
    return state.find_pokemon(pid_of(state, player, card, nth))[1]


def play_trainer(state, card, player=0):
    return apply_kernel(state, PlayTrainer(player, card_of(state, player, card)))


def evolve_pid(state, card, pid, player=0):
    return apply_kernel(state, EvolvePokemon(player, card_of(state, player, card), pid))


def end_turns(state, count):
    for _ in range(count):
        state = apply_kernel(state, EndTurn(state.current_player))
        while state.decision is not None:  # ポケモンチェックのあとの決定はない盤面だけを使う
            raise AssertionError(f"番の終わりに決定がある: {state.decision}")
    return state


def snapshot(state):
    return state_to_dict(state, format_version=11), [dict(e) for e in state.log], repr(state.rng.getstate())


def assert_rejected(test, state, command, code, exception=EngineError):
    """``code`` で拒否され、状態・乱数・ログが変わらない（形式 11 で比べる）。"""
    before = snapshot(state)
    with test.assertRaises(exception) as raised:
        apply_kernel(state, command)
    test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def assert_refused(test, state, command):
    """拒否され（コードによらない）、状態・乱数・ログが変わらない。"""
    before = snapshot(state)
    with test.assertRaises(EngineError):
        apply_kernel(state, command)
    test.assertEqual(snapshot(state), before)


def audited(test, state):
    """不変条件と書き出しの監査（盤面を直接作ったテストなので、ログの監査（対戦の最初からのログが要る）は正式な対戦のテストで確かめる）。"""
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    return state


# ---------------------------------------------------------------- 登録・写し・記録


class CardDataTest(unittest.TestCase):
    """15 枚の登録・写し・採用の記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_fifteen_requested_cards(self):
        """対象は依頼の 15 枚（ポケモン 14 枚とトレーナー 1 枚）。写しの組 pool_v0_44 の並びも同じで、どれも対戦に使える。同じ名前・似た名前の別のカードとは
        別の id で、取りちがえない。"""
        self.assertEqual(len(V0_44_POKEMON), 14)
        self.assertEqual(list(V0_44_CARDS), [*V0_44_POKEMON, GIOVANNI])
        self.assertEqual(list(read_extract()["pool_v0_44"]), list(V0_44_CARDS))
        for card in V0_44_CARDS:
            with self.subTest(card=card):
                self.assertTrue(self.pool.is_playable(card))
        self.assertEqual(self.pool.get(GIOVANNI).category, "trainer")
        same_name = ((ROCKET_DIGLETT, DIGLETT), (ROCKET_MEOWTH, MEOWTH), (ROCKET_MAGIKARP, MAGIKARP))
        for ours, other in same_name:
            with self.subTest(card=ours, other=other):
                self.assertEqual(self.pool.get(ours).name_ja, self.pool.get(other).name_ja)
                self.assertNotEqual([a.name_ja for a in self.pool.get(ours).attacks], [a.name_ja for a in self.pool.get(other).attacks])
        for ours, other in ((MISTYS_STARYU, STARYU), (BLANK_CHANSEY, CHANSEY), (GIOVANNIS_PERSIAN, PERSIAN), (GIOVANNIS_PERSIAN, DARK_PERSIAN),
                            (GIOVANNIS_GYARADOS, GYARADOS), (GIOVANNIS_MAGIKARP, MAGIKARP), (GIOVANNIS_MAGIKARP, MISTYS_MAGIKARP),
                            (ROCKET_MEOWTH, GIOVANNIS_MEOWTH)):
            with self.subTest(card=ours, other=other):
                self.assertNotEqual(self.pool.get(ours).name_ja, self.pool.get(other).name_ja)
        # 進化元は名前の完全一致: キョウのコクーンはキョウのビードル、キョウのスピアーはキョウのコクーン、サカキのギャラドスはサカキのコイキング、サカキのペルシアンは
        # サカキのニャースから（ニャース・コイキングからは進化しない）
        for upper, below in ((KOGAS_KAKUNA, KOGAS_WEEDLE), (KOGAS_BEEDRILL, KOGAS_KAKUNA), (GIOVANNIS_GYARADOS, GIOVANNIS_MAGIKARP),
                             (GIOVANNIS_PERSIAN, GIOVANNIS_MEOWTH)):
            with self.subTest(upper=upper):
                self.assertEqual(self.pool.get(upper).evolves_from, self.pool.get(below).name_ja)

    def test_every_attack_is_registered_with_the_expected_implementation(self):
        """24 のワザがどれも登録され、型と値が説明に合う。説明文のあるワザは、写しの文面（照合用）と処理に使う文面（kyuura の印刷の文面。スターブーメランは
        kyuura の最新の説明 LD-PMCG5-027-ATK0）を持つ。1 度だけ使えるワザは 3 つ（場に出てから 1 回）。"""
        attacks = [(card, a.index) for card in V0_44_POKEMON for a in self.pool.get(card).attacks]
        self.assertEqual(sorted(attacks), sorted(EXPECTED))
        self.assertEqual(len(attacks), 24)
        for (card, index), (cls, values) in EXPECTED.items():
            with self.subTest(card=card, index=index):
                entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
                self.assertIs(type(entry.effect), cls)
                for name, value in values.items():
                    self.assertEqual(getattr(entry.effect, name), value)
                printed = self.pool.get(card).attacks[index]
                self.assertEqual((entry.name_ja, entry.text_ja), (printed.name_ja, printed.text_ja))
                self.assertEqual(entry.effect.check(printed), [])
                self.assertEqual(entry.effect.once_after_entering_play, (card, index) in ONCE)
                if (card, index) == (MISTYS_STARYU, 0):
                    self.assertEqual((entry.play_text_ja, entry.source),
                                     ("コインを投げて「おもて」なら、自分と自分についているすべてのカードを手札にもどす。", "LD-PMCG5-027-ATK0"))
                elif printed.text_ja:
                    self.assertEqual(entry.play_text_ja, printed.text_ja)

    def test_powers_and_trainer_are_registered(self):
        """［うか］は宣言して使う自分の番ごとに 1 回の特殊能力、［ボスをよぶ］は手札から場に出したときに 1 度だけ使える特殊能力、サカキは「サカキの」ポケモンに許可を
        与えるトレーナー。"""
        kakuna = E.DEFAULT_EFFECTS.power_entry(KOGAS_KAKUNA, 0).effect
        self.assertIs(type(kakuna), E.CoinEvolveSelfFromDeck)
        self.assertEqual((kakuna.name, kakuna.declared, kakuna.once_per_turn), ("キョウのスピアー", True, True))
        persian = E.DEFAULT_EFFECTS.power_entry(GIOVANNIS_PERSIAN, 0).effect
        self.assertIs(type(persian), E.SearchNamedTrainerOnEntry)
        self.assertIsInstance(persian, E.EntryPower)
        self.assertEqual((persian.name, persian.from_hand_only), ("サカキ", True))
        trainer = E.DEFAULT_EFFECTS.trainer_entry(GIOVANNI)
        self.assertIs(type(trainer.effect), E.EvolutionPermissionForOwnerPokemon)
        self.assertEqual(trainer.effect.owner, "サカキ")
        self.assertEqual(trainer.play_text_ja, self.pool.get(GIOVANNI).trainer_text_ja)
        for card in (KOGAS_KAKUNA, GIOVANNIS_PERSIAN):
            with self.subTest(card=card):
                [printed] = self.pool.get(card).powers
                self.assertEqual(E.DEFAULT_EFFECTS.power_entry(card, 0).effect.check(printed), [])

    def test_without_the_power_or_trainer_registration_the_card_is_not_supported(self):
        """一部だけを登録してカード全体を対応と数えない: 特殊能力の登録を除くとキョウのコクーン・サカキのペルシアンは、トレーナーの登録を除くとサカキは、デッキに入らない。"""
        effects = E.DEFAULT_EFFECTS.without_powers("test-no-v044-powers", [E.PowerKey(KOGAS_KAKUNA, 0), E.PowerKey(GIOVANNIS_PERSIAN, 0)])
        pool = pool_from_extract(read_extract(), effects)
        for card in (KOGAS_KAKUNA, GIOVANNIS_PERSIAN):
            with self.subTest(card=card):
                self.assertFalse(pool.is_playable(card))
                self.assertTrue(all(a.supported for a in pool.get(card).attacks))
        pool = pool_from_extract(read_extract(), E.DEFAULT_EFFECTS.without_trainers("test-no-giovanni", [GIOVANNI]))
        self.assertFalse(pool.is_playable(GIOVANNI))

    def test_types_are_new_kernel_types(self):
        """v0.44 のワザの型は解決の基盤の要素の並び（BUILDERS）で処理し、v0.13 の約束（resolve）を上書きしない。v013_checks.VERIFIED に入れない。"""
        for (card, index), (cls, _values) in EXPECTED.items():
            if cls in (E.DamageOnly, E.SleepOpponent, E.CoinFlipDamage, E.CoinBonusDamage, E.ChooseOpponentPokemonDamage):
                continue
            with self.subTest(cls=cls.__name__):
                self.assertIn(cls, programs.BUILDERS)
                self.assertIn(cls, ATTACK_TYPES_SINCE_V0_17)
                self.assertNotIn(cls, v013_checks.VERIFIED)
                self.assertNotIn("resolve", cls.__dict__)

    def test_no_card_specific_branch_in_engine_or_kernel(self):
        """engine.py・resolution/ に v0.44 のカード id での分岐を加えていない。"""
        for path in [ROOT / "kyuura_engine" / "engine.py", *(ROOT / "kyuura_engine" / "resolution").glob("*.py")]:
            text = path.read_text(encoding="utf-8")
            for card in V0_44_CARDS:
                with self.subTest(path=path.name, card=card):
                    self.assertNotIn(card, text)

    def test_adoption_records(self):
        """採用の記録（kyuura データの採用・写しの元のコミット・処理に使う文面の根拠）と pcg-search.com の同じ版のページとの照合。違いは _____のラッキーの名前の
        空欄の下線の数だけ（処理に影響しない）。採用したカードを過去の原典照合の記録に入れない。ガイドブックの項目を書かない。"""
        sources = cs.load_sources()["cards"]
        self.assertEqual(cs.problems(), [])
        for card in V0_44_CARDS:
            record = sources[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]), (cs.KYUURA_DATA, cs.ADOPTED, KYUURA_COMMIT))
                [check] = record["external_checks"]
                self.assertEqual(check["edition"]["list_number"], EDITIONS[card])
                self.assertTrue(check["url"].startswith("https://pcg-search.com/card/"))
                self.assertFalse({"page", "pdf_page", "latest_description_ja", "card_image_text_ja"} & set(record))
        self.assertEqual([d["field"] for d in sources[BLANK_CHANSEY]["external_checks"][0]["differences"]], ["name.ja"])
        self.assertEqual(sources[MISTYS_STARYU]["kyuura_records"], ["CR-SHELL-ATTACK-STAR-BOOMERANG", "LD-PMCG5-027-ATK0"])


# ---------------------------------------------------------------- 相手のポケモンを選ぶダメージ


class ChooseTargetTest(unittest.TestCase):
    """ディグダの「じめんにもぐる」・ニャースの「こばんなげ」（v0.43 の ``ChooseOpponentPokemonDamage`` と同じ要素。こばんなげは要素のコイン）。"""

    def test_dig_under_damages_the_chosen_pokemon_ignoring_weakness(self):
        """相手の場のポケモン（対戦ポケモン・控え）から選ぶ。弱点・抵抗力に関係なく 10（相手の対戦ポケモンの弱点が闘でも 10）。"""
        state = board(mon(ROCKET_DIGLETT, (F,)), mon(RATTATA, ()), opponent_bench=(RATTATA, MEOWTH))
        waiting = attack(state, 0)
        d = waiting.decision
        self.assertEqual((d.kind, d.player), (SELECT_POKEMON, 0))
        self.assertEqual(set(d.options), {p.pokemon_id for p in state.players[1].in_play()})
        for target in d.options:
            with self.subTest(target=target):
                done = audited(self, answer(waiting, (target,)))
                self.assertEqual(pokemon_of(done, target).damage, 10)
                self.assertEqual(sum(p.damage for p in done.players[1].in_play()), 10)

    def test_invalid_target_is_rejected_without_change(self):
        """自分のポケモン・2 匹・0 匹は選べない（決定は待ったまま、状態は変わらない）。"""
        waiting = attack(board(mon(ROCKET_DIGLETT, (F,))), 0)
        d = waiting.decision
        for choices in ((waiting.players[0].active.pokemon_id,), tuple(d.options[:2]), ()):
            with self.subTest(choices=choices):
                assert_refused(self, waiting, ResolveDecision(0, d.id, choices))

    def test_coin_toss_heads_chooses_and_tails_does_nothing(self):
        """こばんなげ: 「おもて」なら選んで 20、「うら」なら決定も ダメージもない（ワザは使ったことになり番は終わる）。"""
        state = board(mon(ROCKET_MEOWTH, (F, F)))
        heads = attack(state, 0, H)
        self.assertEqual(heads.decision.kind, SELECT_POKEMON)
        target = heads.decision.options[-1]
        done = audited(self, answer(heads, (target,)))
        self.assertEqual(pokemon_of(done, target).damage, 20)
        tails = audited(self, attack(state, 0, T))
        self.assertIsNone(tails.decision)
        self.assertEqual(sum(p.damage for p in tails.players[1].in_play()), 0)
        self.assertEqual(tails.current_player, 1)


# ---------------------------------------------------------------- 山札から見せて手札に加える・山札の上にのせる


class SearchTest(unittest.TestCase):
    """おつかい（トレーナーを見せて手札に加える）・わるいいたずら（相手のトラッシュのカードを相手の山札の上にのせる）。"""

    def test_errand_reveals_a_trainer_and_shuffles(self):
        """「おもて」: 山札のトレーナーカードから 0〜1 枚。見せて手札に加え（ログ ``reveal_from_deck`` は公開）、山札を切る。選ばなくてもよい（「加えてよい」）。"""
        state = board(mon(ERIKAS_BULBASAUR, (G, G)), deck=[GRASS, POTION, GIOVANNI, WATER])
        waiting = attack(state, 1, H)
        d = waiting.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (SEARCH_DECK, 0, 1))
        self.assertEqual(sorted(state.cards[u].card_id for u in d.options), sorted([POTION, GIOVANNI]))
        since = len(waiting.log)
        chosen = audited(self, answer(waiting, (d.options[0],)))
        self.assertIn(d.options[0], chosen.players[0].hand)
        self.assertEqual(kinds(chosen, since)[:2], ["reveal_from_deck", "shuffle"])
        declined = audited(self, answer(waiting, ()))
        self.assertEqual(kinds(declined, since)[:2], ["reveal_from_deck_declined", "shuffle"])
        tails = audited(self, attack(state, 1, T))
        self.assertNotIn("shuffle", kinds(tails, len(state.log)))

    def test_errand_without_trainers_shuffles(self):
        """「おもて」で山札にトレーナーがなければ選ぶものはなく（p.309）、山札を切る。"""
        done = audited(self, attack(board(mon(ERIKAS_BULBASAUR, (G, G)), deck=[GRASS, WATER]), 1, H))
        self.assertIsNone(done.decision)
        self.assertEqual([e for e in kinds(done, 0) if e in ("reveal_from_deck_none", "shuffle")][-2:], ["reveal_from_deck_none", "shuffle"])

    def test_mischief_puts_opponent_discard_on_their_deck_top(self):
        """わるいいたずら: 「おもて」なら相手のトラッシュから 1 枚を選び、相手の山札の一番上にのせる（切らない）。相手のトラッシュが空ならコインも投げない。"""
        state = board(mon(BLAINES_MANKEY, (F,)))
        state.players[1].discard.extend(state.players[1].deck[:2])
        del state.players[1].deck[:2]
        waiting = attack(state, 0, H)
        d = waiting.decision
        self.assertEqual((d.kind, d.player, tuple(d.options)), (DISCARD_TO_DECK_TOP, 0, tuple(state.players[1].discard)))
        done = audited(self, answer(waiting, (d.options[1],)))
        # 山札の一番上にのせたので、相手は次の番の最初にそのカードを引く（切らない）
        self.assertNotIn("shuffle", kinds(done, len(waiting.log)))
        self.assertEqual(events(done, len(waiting.log), "put_discard_on_deck_top")[0]["card"], d.options[1])
        self.assertEqual(events(done, len(waiting.log), "draw")[0]["cards"], (d.options[1],))
        empty = audited(self, attack(board(mon(BLAINES_MANKEY, (F,))), 0))
        self.assertNotIn("coin_flip", kinds(empty, 0))


# ---------------------------------------------------------------- 手札を山札にもどす（てじな・ラッキーたまご）


class HandToDeckTest(unittest.TestCase):
    """てじな（最大 3 枚もどし、同じ枚数の基本エネルギーを見せて手札に加える）・ラッキーたまご（「うら」なら 2 枚もどす）。"""

    def mime(self, hand, deck):
        return board(mon(SABRINAS_MR_MIME, (P,)), hand=hand, deck=deck)

    def test_sleight_returns_cards_and_reveals_as_many_basic_energies(self):
        """もどしたのと同じ枚数の基本エネルギーカードを山札から選び、見せて手札に加え、山札を切る。もどしたカードは山札に入る（選べる）。"""
        state = self.mime([POTION, SWITCH, PLUSPOWER], [GRASS, WATER, RATTATA])
        waiting = attack(state, 0)
        d = waiting.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (HAND_TO_DECK, 0, 3))
        stage2 = answer(waiting, tuple(d.options[:2]))
        d2 = stage2.decision
        self.assertEqual((d2.kind, d2.min_choices, d2.max_choices), (SEARCH_DECK, 2, 2))
        self.assertEqual(sorted(stage2.cards[u].card_id for u in d2.options), sorted([GRASS, WATER]))
        done = audited(self, answer(stage2, tuple(d2.options)))
        self.assertEqual(sorted(cards_in(done, 0, "hand")), sorted([PLUSPOWER, GRASS, WATER]))
        self.assertEqual(card_count(done, 0), card_count(state, 0))
        hidden = events(done, len(waiting.log), "hand_to_deck")
        self.assertEqual(len(hidden), 1)

    def test_zero_cards_is_gs1_and_short_energy_is_fc1(self):
        """0 枚は GS1（v0.39 と同じ問い）、山札の基本エネルギーカードがもどす枚数より少ない（1 枚以上）なら FC1。どちらも決定は待ったまま、状態は変わらない。
        足りる枚数・基本エネルギーカードが 0 枚（選び出すものがない）は止めない。"""
        state = self.mime([POTION, SWITCH, PLUSPOWER], [GRASS, RATTATA])
        waiting = attack(state, 0)
        d = waiting.decision
        for choices, code in (((), GS1), (tuple(d.options[:2]), FC1), (tuple(d.options), FC1)):
            with self.subTest(choices=choices):
                assert_rejected(self, waiting, ResolveDecision(0, d.id, choices), code, exception=UnsupportedError)
        audited(self, answer(answer(waiting, tuple(d.options[:1])), (card_of(waiting, 0, GRASS, "deck"),)))
        none = self.mime([POTION, SWITCH], [RATTATA])
        waiting = attack(none, 0)
        done = audited(self, answer(waiting, tuple(waiting.decision.options)))
        self.assertIn("reveal_from_deck_none", kinds(done, len(waiting.log)))
        # もどすカードが基本エネルギーなら、そのカードを選び出せる（足りる）
        energy = self.mime([GRASS, POTION], [RATTATA])
        waiting = attack(energy, 0)
        stage2 = answer(waiting, (card_of(waiting, 0, GRASS),))
        self.assertEqual(stage2.decision.kind, SEARCH_DECK)

    def test_sleight_without_hand_only_shuffles(self):
        """手札がなければ決定を出さず、山札を切る（p.309）。"""
        done = audited(self, attack(self.mime([], [GRASS]), 0))
        self.assertIsNone(done.decision)
        self.assertIn("shuffle", kinds(done, 0))

    def test_lucky_egg_heads_draws_and_tails_returns_two(self):
        """ラッキーたまご: 「おもて」なら 2 枚引く、「うら」なら手札から 2 枚選んで山札にもどし切る。手札が 2 枚より少なければ FC1（宣言の前。どの先読みでも）。"""
        state = board(mon(BLANK_CHANSEY, (F,)), hand=[POTION, SWITCH, PLUSPOWER])
        heads = audited(self, attack(state, 0, H))
        self.assertEqual(len(heads.players[0].hand), 5)
        tails = attack(state, 0, T)
        d = tails.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (HAND_TO_DECK, 2, 2))
        done = audited(self, answer(tails, tuple(d.options[:2])))
        self.assertEqual(len(done.players[0].hand), 1)
        self.assertEqual(kinds(done, len(tails.log))[:2], ["hand_to_deck", "shuffle"])
        for hand in ([], [POTION]):
            with self.subTest(hand=hand):
                assert_stops(self, board(mon(BLANK_CHANSEY, (F,)), hand=hand), UseAttack(0, 0), FC1)
        audited(self, attack(board(mon(BLANK_CHANSEY, (F,)), hand=[POTION, SWITCH]), 0, T, answers=[lambda d: tuple(d.options)]))


# ---------------------------------------------------------------- スターブーメラン


class StarBoomerangTest(unittest.TestCase):
    """ダメージのあと「おもて」なら、自分とついているすべてのカードを手札にもどす（LD-PMCG5-027-ATK0）。きぜつではない。"""

    def test_heads_returns_staryu_and_attached_cards_to_hand(self):
        state = board(mon(MISTYS_STARYU, (W,)), mon(HITMONCHAN, (F, F)), bench=(RATTATA,))
        state = with_coin_results(state, H)
        waiting = apply_kernel(state, UseAttack(0, 0))
        # 空いたバトル場は、ワザのあとに控えから出す（控えが 1 匹なら決定）
        self.assertEqual(sorted(cards_in(waiting, 0, "hand")), sorted([MISTYS_STARYU, WATER]))
        self.assertEqual(pokemon_of(waiting, waiting.players[1].active.pokemon_id).damage, 20)
        self.assertNotIn("knock_out", kinds(waiting, len(state.log)))
        self.assertEqual(len(waiting.players[1].prizes), len(state.players[1].prizes))
        if waiting.decision is not None:
            waiting = answer(waiting, (waiting.decision.options[0],))
        audited(self, waiting)

    def test_knockout_by_the_same_attack_is_rd9(self):
        """同じワザで相手の対戦ポケモンが HP 以上になりうるなら、RD9 と同じ問いで宣言の前に止める（新しい問いにしない）。"""
        state = board(mon(MISTYS_STARYU, (W,)), {"card": RATTATA, "damage": 20})
        assert_stops(self, state, UseAttack(0, 0), RD9)
        self.assertEqual(QUESTIONS["return_in_play_to_deck_with_knockout"].code, RD9)

    def test_without_bench_returning_loses(self):
        """控えがいないとき「おもて」で手札にもどれば、ワザのあとの勝ち負けの判定で負け（v0.36 のくもがくれガスと同じ）。"""
        state = board(mon(MISTYS_STARYU, (W,)), mon(HITMONCHAN, (F, F)), bench=())
        done = audited(self, attack(state, 0, H))
        self.assertIs(done.phase, Phase.GAME_OVER)
        self.assertEqual(done.result.winner, 1)


# ---------------------------------------------------------------- 山札から進化（たきのぼりしんか・［うか］）


class DeckEvolutionTest(unittest.TestCase):
    """コイキングの「たきのぼりしんか」（ワザ）・キョウのコクーンの［うか］（特殊能力）。通常の進化の制限を免除しない。"""

    def test_waterfall_evolution_evolves_itself_and_ends_the_turn(self):
        """「コイキング」から進化するカードを山札から 0〜1 枚選んで重ね、山札を切る。ワザなので番は終わる。"""
        state = board(mon(ROCKET_MAGIKARP, (W, W, W)), deck=[GYARADOS, GRASS])
        waiting = attack(state, 1)
        d = waiting.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (SEARCH_DECK, 0, 1))
        done = audited(self, answer(waiting, tuple(d.options)))
        self.assertEqual(done.cards[done.players[0].active.card].card_id, GYARADOS)
        evolve = events(done, len(waiting.log), "evolve")[0]
        self.assertEqual((evolve["source_zone"], evolve["effect"]), ("deck", f"{ROCKET_MAGIKARP}#1"))
        self.assertEqual(done.current_player, 1)
        declined = audited(self, answer(waiting, ()))
        self.assertEqual(declined.cards[declined.players[0].active.card].card_id, ROCKET_MAGIKARP)
        self.assertIn("evolve_from_deck_declined", kinds(declined, len(waiting.log)))

    def test_waterfall_evolution_keeps_the_normal_restrictions(self):
        """この番に場に出したコイキング・おたがいの最初の番は進化できない（重ねられるカードがなく、山札を切るだけ）。"""
        for spec, turn in (({"played_turn": TURN}, TURN), ({}, 1)):
            with self.subTest(spec=spec, turn=turn):
                state = board(mon(ROCKET_MAGIKARP, (W, W, W), **spec), deck=[GYARADOS], turn=turn)
                done = audited(self, attack(state, 1))
                self.assertEqual(done.cards[done.players[0].active.card].card_id, ROCKET_MAGIKARP)
                self.assertIn("evolve_from_deck_none", kinds(done, len(state.log)))

    def test_metamorphosis_power(self):
        """［うか］: 自分の番ごとに 1 回、コイン「おもて」でキョウのスピアーを山札から重ね、山札を切る。特殊能力なので番は終わらない。「うら」でも使ったことになる。"""
        state = board(mon(KOGAS_KAKUNA, (G,)), deck=[KOGAS_BEEDRILL, GRASS])
        pid = state.players[0].active.pokemon_id
        waiting = power(state, pid, H)
        self.assertEqual(waiting.decision.kind, SEARCH_DECK)
        done = audited(self, answer(waiting, tuple(waiting.decision.options)))
        self.assertEqual(done.cards[done.players[0].active.card].card_id, KOGAS_BEEDRILL)
        self.assertEqual(done.current_player, 0)
        self.assertEqual(events(done, len(state.log), "evolve")[0]["power"], f"{KOGAS_KAKUNA}@power0")
        tails = audited(self, power(state, pid, T))
        self.assertIn((pid, 0), tails.power_uses_this_turn)
        assert_rejected(self, tails, UsePokemonPower(0, pid, 0), "POWER_ALREADY_USED")
        none = audited(self, power(board(mon(KOGAS_KAKUNA, (G,)), deck=[GRASS]), pid, H))
        self.assertIn("evolve_from_deck_none", kinds(none, 0))

    def test_metamorphosis_keeps_the_normal_restrictions(self):
        """この番に進化したコクーンは「おもて」でも重ねられない（その番の最初から場にいない）。眠り・マヒ・こんらんのコクーンは使えない。"""
        state = board(mon(KOGAS_KAKUNA, (G,), evolved_turn=TURN), deck=[KOGAS_BEEDRILL])
        done = audited(self, power(state, state.players[0].active.pokemon_id, H))
        self.assertIn("evolve_from_deck_none", kinds(done, 0))
        for status in ({"sleep": True}, {"paralysis": TURN - 1}, {"confusion": True}):
            with self.subTest(status=status):
                asleep = board(mon(KOGAS_KAKUNA, (G,), **status), deck=[KOGAS_BEEDRILL])
                with self.assertRaises(EngineError):
                    apply_kernel(asleep, UsePokemonPower(0, asleep.players[0].active.pokemon_id, 0))

    def test_gv1_is_a_stop_code_and_self_evolution_cannot_reach_it(self):
        """GV1（サカキの許可のあるポケモンを山札から重ねる効果で進化させる）。v0.44 はコードのない問いとしたが、つきのちから（エリカのピッピ）は自分の場のほかの
        ポケモン（許可のあるサカキのコイキング）を進化させうるので、v0.45 で停止コードを付けた（裁定は未解決のまま。再現と隣の場合は v0.45 のテスト）。
        ``evolution_block`` が返す印は停止コードではない（呼ぶ側が止める）。自分自身を進化させる効果（たきのぼりしんか・［うか］）のカードは「サカキの」ポケモン
        ではないので、自分自身からは起こらない。"""
        self.assertEqual(QUESTIONS["evolution_permission_from_deck"].code, "UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK")
        self.assertFalse(evolution.PERMISSION_FROM_DECK_CODE.startswith("UNRESOLVED_"))
        for card in (ROCKET_MAGIKARP, KOGAS_KAKUNA):
            with self.subTest(card=card):
                self.assertFalse(load_card_pool().get(card).name_ja.startswith("サカキの"))


# ---------------------------------------------------------------- 場に出てから 1 度しか使えないワザ


class OnceAfterEntryTest(unittest.TestCase):
    """ネギでたたく・りゅうのきおく・ひっさつばり。場のポケモンの記録 ``attacks_used_once``（宣言のときに記録。ログを読み直さない）。"""

    def test_record_is_set_at_declaration_even_on_tails(self):
        """「うら」でダメージを与えなくても使ったことになる（p.323 の 12・v0.3d の A12）。次の自分の番は ``ATTACK_ALREADY_USED`` で拒否し、状態は変わらない。"""
        for card, index, energy in ((FARFETCHD, 0, (F, F, F)), (GIOVANNIS_MAGIKARP, 0, (W, W)), (KOGAS_BEEDRILL, 1, (G, G, G))):
            with self.subTest(card=card):
                state = board(mon(card, energy), mon(HITMONCHAN, (F, F)))
                tails = audited(self, attack(state, index, T))
                pokemon = find(tails, 0, card)
                self.assertEqual(pokemon.attacks_used_once, ((pokemon.card, index),))
                self.assertEqual(sum(e["amount"] for e in events(tails, len(state.log), "damage")), 0)
                again = end_turns(tails, 1)
                assert_rejected(self, again, UseAttack(0, index), "ATTACK_ALREADY_USED", exception=IllegalActionError)
                other = 1 - index
                self.assertIsNotNone(apply_kernel(again, UseAttack(0, other)))

    def test_confusion_tails_also_uses_it(self):
        """こんらんの「うら」でも使ったことになる（記録はこんらんのコインより前、宣言のとき）。"""
        state = board(mon(FARFETCHD, (F,), confusion=True), mon(HITMONCHAN, (F, F)))
        done = audited(self, attack(state, 0, T))
        self.assertIn("confusion_damage", kinds(done, len(state.log)))
        self.assertEqual(len(find(done, 0, FARFETCHD).attacks_used_once), 1)

    def test_record_survives_bench_and_ends_when_leaving_play(self):
        """ベンチにもどっても同じポケモン（記録は残る）。進化したポケモンの下のカードの記録も残るが、上のカードのワザではない。"""
        state = board(mon(FARFETCHD, (F,)), mon(HITMONCHAN, (F, F)), bench=(RATTATA,), hand=[SWITCH])
        used = end_turns(attack(state, 0, T), 1)
        switched = audited(self, answer(apply_kernel(used, PlayTrainer(0, card_of(used, 0, SWITCH))), (pid_of(used, 0, RATTATA),)))
        benched = find(switched, 0, FARFETCHD)
        self.assertIn(benched, switched.players[0].bench)
        self.assertEqual(len(benched.attacks_used_once), 1)
        magikarp = board(mon(GIOVANNIS_MAGIKARP, (W, W)), mon(HITMONCHAN, (F, F)), hand=[GIOVANNIS_GYARADOS])
        used = end_turns(attack(magikarp, 0, T), 1)
        evolved = audited(self, evolve_pid(used, GIOVANNIS_GYARADOS, used.players[0].active.pokemon_id))
        self.assertEqual(len(evolved.players[0].active.attacks_used_once), 1)
        audited(self, attack(evolved, 0, H, H))

    def test_copying_a_once_attack_is_engine_unsupported(self):
        """相手のワザとして使う（ゆびをふる）とき、1 度だけ使えるワザは選べない（エンジンの未対応。``unsupported_choices``）。ほかのワザは選べる。"""
        state = board(mon(CLEFAIRY, (P, P, P)), mon(FARFETCHD, (F,)))
        waiting = attack(state, 1)
        d = waiting.decision
        self.assertEqual(d.kind, SELECT_ATTACK)
        self.assertEqual(d.context_value("unsupported_choices"), (0,))
        with self.assertRaises(UnsupportedError) as raised:
            answer(waiting, (0,))
        self.assertEqual(raised.exception.code, "UNSUPPORTED_COPIED_ATTACK")
        audited(self, answer(waiting, (1,)))

    def test_format_11_and_older_formats(self):
        """記録は書き出しの形式 11 の ``attacks_used_once``。形式 10 以前は記録があると ``ValueError``。写した状態でも同じに拒否する。"""
        state = audited(self, attack(board(mon(FARFETCHD, (F,)), mon(HITMONCHAN, (F, F))), 0, T))
        data = state_to_dict(state, format_version=11)
        self.assertEqual(data["players"][0]["active"]["attacks_used_once"], [[state.players[0].active.card, 0]])
        for version in (1, 9, 10):
            with self.subTest(version=version), self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)
        again = end_turns(state, 1)
        for copied in (again.clone(), copy.deepcopy(again), pickle.loads(pickle.dumps(again))):
            with self.assertRaises(IllegalActionError):
                apply_kernel(copied, UseAttack(0, 0))


# ---------------------------------------------------------------- サカキと［ボスをよぶ］


class GiovanniTest(unittest.TestCase):
    """トレーナーのサカキ（今の番に場に出した・進化した「サカキの」ポケモンでも進化させてよい）と、サカキのペルシアンの［ボスをよぶ］。"""

    def giovanni_board(self, *, played=TURN, hand=(GIOVANNI, GIOVANNIS_GYARADOS), turn=TURN, bench=None):
        bench = bench if bench is not None else [{"card": GIOVANNIS_MAGIKARP, "played_turn": played}]
        return board(mon(RATTATA, ()), bench=bench, hand=list(hand), turn=turn)

    def test_permission_lets_a_pokemon_played_this_turn_evolve(self):
        """この番に場に出したサカキのコイキングは、ふつうは進化できない（PLAYED_THIS_TURN）。サカキで選ぶと進化させてよい（許可は場のポケモンの記録 ``evolution_permission_turn``）。"""
        state = self.giovanni_board()
        target = pid_of(state, 0, GIOVANNIS_MAGIKARP)
        assert_rejected(self, state, EvolvePokemon(0, card_of(state, 0, GIOVANNIS_GYARADOS), target), "PLAYED_THIS_TURN", exception=IllegalActionError)
        waiting = play_trainer(state, GIOVANNI)
        d = waiting.decision
        self.assertEqual((d.kind, d.player, tuple(d.options)), (SELECT_POKEMON, 0, (target,)))
        permitted = audited(self, answer(waiting, (target,)))
        self.assertEqual(pokemon_of(permitted, target).evolution_permission_turn, TURN)
        self.assertEqual(events(permitted, len(state.log), "evolution_permission")[0]["pokemon_id"], target)
        self.assertIn(GIOVANNI, cards_in(permitted, 0, "discard"))
        evolved = audited(self, evolve_pid(permitted, GIOVANNIS_GYARADOS, target))
        self.assertEqual(evolved.cards[pokemon_of(evolved, target).card].card_id, GIOVANNIS_GYARADOS)
        # 許可はその番だけ（番の終わりに消える）
        later = end_turns(evolved, 1)
        self.assertIsNone(pokemon_of(later, target).evolution_permission_turn)

    def test_evolved_this_turn_can_evolve_again(self):
        """進化したそのポケモンを、同じ番にさらに進化させてよい（サカキのワンリキー → ゴーリキー → カイリキー）。"""
        state = board(mon(RATTATA, ()), bench=[{"card": GIOVANNIS_MACHOP}], hand=[GIOVANNI, GIOVANNIS_MACHOKE, GIOVANNIS_MACHAMP])
        target = pid_of(state, 0, GIOVANNIS_MACHOP)
        once = evolve_pid(state, GIOVANNIS_MACHOKE, target)
        assert_rejected(self, once, EvolvePokemon(0, card_of(once, 0, GIOVANNIS_MACHAMP), target), "EVOLVED_THIS_TURN", exception=IllegalActionError)
        permitted = answer(play_trainer(once, GIOVANNI), (target,))
        twice = audited(self, evolve_pid(permitted, GIOVANNIS_MACHAMP, target))
        self.assertEqual(twice.cards[pokemon_of(twice, target).card].card_id, GIOVANNIS_MACHAMP)
        self.assertEqual(len(pokemon_of(twice, target).evolution_stack), 2)

    def test_first_turn_restriction_is_kept(self):
        """おたがいの最初の番は、許可があっても進化できない（日本語の文面に最初の番の記述はない。英語版の文面を持ち込まない）。"""
        state = self.giovanni_board(turn=1, played=1)
        target = pid_of(state, 0, GIOVANNIS_MAGIKARP)
        permitted = answer(play_trainer(state, GIOVANNI), (target,))
        assert_rejected(self, permitted, EvolvePokemon(0, card_of(permitted, 0, GIOVANNIS_GYARADOS), target), "FIRST_TURN_EVOLUTION",
                        exception=IllegalActionError)

    def test_only_owner_pokemon_and_tr1(self):
        """選べるのは自分の場の「サカキの」ポケモンだけ（名前の完全一致の前の部分。ほかのポケモンは選べない）。いなければ、使えるかは決められない（TR1。使う前に止める）。"""
        state = board(mon(RATTATA, ()), bench=[{"card": GIOVANNIS_MAGIKARP}, MAGIKARP], hand=[GIOVANNI])
        waiting = play_trainer(state, GIOVANNI)
        self.assertEqual(tuple(waiting.decision.options), (pid_of(state, 0, GIOVANNIS_MAGIKARP),))
        assert_refused(self, waiting, ResolveDecision(0, waiting.decision.id, (pid_of(state, 0, MAGIKARP),)))
        none = board(mon(RATTATA, ()), bench=[MAGIKARP], hand=[GIOVANNI])
        assert_rejected(self, none, PlayTrainer(0, card_of(none, 0, GIOVANNI)), TR1, exception=UnsupportedError)

    def test_breeder_uses_the_permission(self):
        """ポケモン育て屋さんも手札から重ねる進化なので、許可でこの番に場に出したサカキのワンリキーをカイリキーにできる。"""
        state = board(mon(RATTATA, ()), bench=[{"card": GIOVANNIS_MACHOP, "played_turn": TURN}], hand=[GIOVANNI, POKEMON_BREEDER, GIOVANNIS_MACHAMP])
        target = pid_of(state, 0, GIOVANNIS_MACHOP)
        assert_refused(self, state, PlayTrainer(0, card_of(state, 0, POKEMON_BREEDER)))  # 許可がなければ重ねられる組がない
        permitted = answer(play_trainer(state, GIOVANNI), (target,))
        waiting = play_trainer(permitted, POKEMON_BREEDER)
        self.assertIn(target, waiting.decision.options)
        done = answer(answer(waiting, (target,)), (card_of(waiting, 0, GIOVANNIS_MACHAMP),))
        self.assertEqual(audited(self, done).cards[pokemon_of(done, target).card].card_id, GIOVANNIS_MACHAMP)

    def test_format_11_permission(self):
        """許可は書き出しの形式 11 の ``evolution_permission_turn``。形式 10 以前は許可があると ``ValueError``。"""
        state = self.giovanni_board()
        permitted = answer(play_trainer(state, GIOVANNI), (pid_of(state, 0, GIOVANNIS_MAGIKARP),))
        data = state_to_dict(permitted, format_version=11)
        self.assertEqual([p["evolution_permission_turn"] for p in data["players"][0]["bench"]], [TURN])
        with self.assertRaises(ValueError):
            state_to_dict(permitted, format_version=10)

    def test_call_for_boss_searches_giovanni_when_evolving_from_hand(self):
        """［ボスをよぶ］: 手札から進化させたときに使う機会（使うかは持ち主）。使えば山札のサカキを手札に加え（ログ ``search_deck`` は非公開）、山札を切る。
        山札にサカキがなければ、使うことを選ぶと止める（PW3）。使わないことは選べる。"""
        state = board(mon(GIOVANNIS_MEOWTH, ()), hand=[GIOVANNIS_PERSIAN], deck=[GIOVANNI, POTION])
        target = state.players[0].active.pokemon_id
        offer = evolve_pid(state, GIOVANNIS_PERSIAN, target)
        d = offer.decision
        self.assertEqual((d.kind, tuple(d.options), d.min_choices, d.max_choices), (ENTRY_POWER, (target,), 0, 1))
        waiting = answer(offer, (target,))
        self.assertEqual((waiting.decision.kind, [waiting.cards[u].card_id for u in waiting.decision.options]), (SEARCH_DECK, [GIOVANNI]))
        done = audited(self, answer(waiting, tuple(waiting.decision.options)))
        self.assertIn(GIOVANNI, cards_in(done, 0, "hand"))
        self.assertEqual(kinds(done, len(waiting.log))[:2], ["search_deck", "shuffle"])
        declined = audited(self, answer(offer, ()))
        self.assertIn("entry_power_declined", kinds(declined, len(offer.log)))
        empty = board(mon(GIOVANNIS_MEOWTH, ()), hand=[GIOVANNIS_PERSIAN], deck=[POTION])
        offer = evolve_pid(empty, GIOVANNIS_PERSIAN, empty.players[0].active.pokemon_id)
        self.assertEqual(offer.decision.context_value("unresolved_code"), PW3)
        assert_rejected(self, offer, ResolveDecision(0, offer.decision.id, (empty.players[0].active.pokemon_id,)), PW3, exception=UnsupportedError)
        audited(self, answer(offer, ()))


# ---------------------------------------------------------------- そのほかのワザ


class OtherAttackTest(unittest.TestCase):
    """どくばり系・あらしをよぶ・りゅうのたつまき・ねむりのたね。"""

    def test_toxic_fluid_and_nerve_poison(self):
        """どくどくえき: 「おもて」なら特殊などく（20）。しんけいどく: 20 のあと「おもて」ならどくとマヒの両方（1 枚のコイン）。"""
        done = audited(self, attack(board(mon(KOGAS_KAKUNA, (G,)), mon(HITMONCHAN, (F, F))), 0, H))
        self.assertEqual(done.players[1].active.conditions.poison.damage, 20)
        done = audited(self, attack(board(mon(KOGAS_BEEDRILL, (G, G)), mon(HITMONCHAN, (F, F))), 0, H))
        conditions = done.players[1].active.conditions
        self.assertTrue(conditions.poison is not None and conditions.paralyzed)
        self.assertEqual(events(done, 0, "coin_flip").__len__(), 1)
        tails = audited(self, attack(board(mon(KOGAS_BEEDRILL, (G, G)), mon(HITMONCHAN, (F, F))), 0, T))
        self.assertIsNone(tails.players[1].active.conditions.poison)

    def test_storm_damages_every_other_pokemon_on_all_heads(self):
        """あらしをよぶ: コイン 2 枚がすべて「おもて」なら、自分以外の場のポケモン全員に弱点・抵抗力に関係なく 20。1 枚でも「うら」なら何もしない。"""
        state = board(mon(GIOVANNIS_GYARADOS, (W,), evolved_from=GIOVANNIS_MAGIKARP), mon(HITMONCHAN, (F, F)), bench=(RATTATA,),
                      opponent_bench=(RATTATA, MEOWTH))
        done = audited(self, attack(state, 0, H, H))
        self.assertEqual(done.players[0].active.damage, 0)
        self.assertEqual([p.damage for p in done.players[0].bench], [20])
        self.assertEqual([p.damage for p in done.players[1].in_play()], [20, 20, 20])
        for sides in ((H, T), (T, H), (T, T)):
            with self.subTest(sides=sides):
                none = audited(self, attack(state, 0, *sides))
                self.assertEqual(sum(p.damage for side in none.players for p in side.in_play()), 0)

    def test_dragon_whirlwind_switches_unless_knocked_out(self):
        """りゅうのたつまき: 40 のあと、相手がきぜつしなければ、ワザを使ったプレイヤーが相手の控えを選んで入れ替える。きぜつしたら入れ替えない。"""
        state = board(mon(GIOVANNIS_GYARADOS, (W, W, W, W), evolved_from=GIOVANNIS_MAGIKARP), mon(HITMONCHAN, (F, F)), opponent_bench=(RATTATA, MEOWTH))
        waiting = attack(state, 1)
        d = waiting.decision
        self.assertEqual(d.player, 0)
        chosen = d.options[-1]
        done = audited(self, answer(waiting, (chosen,)))
        self.assertEqual(done.players[1].active.pokemon_id, chosen)
        ko = board(mon(GIOVANNIS_GYARADOS, (W, W, W, W), evolved_from=GIOVANNIS_MAGIKARP), {"card": RATTATA, "damage": 10}, opponent_bench=(MEOWTH,))
        done = attack(ko, 1)
        self.assertNotIn("forced_switch", kinds(done, len(ko.log)))

    def test_preflight_modes_agree(self):
        """v0.44 のワザの宣言の前の答え（受け付けるか・止めるコード）は、先読みの方法によらない（ラッキーたまごの FC1・スターブーメランの RD9）。"""
        for state, code in ((board(mon(BLANK_CHANSEY, (F,)), hand=[POTION]), FC1),
                            (board(mon(MISTYS_STARYU, (W,)), {"card": RATTATA, "damage": 20}), RD9)):
            outcomes = set()
            for mode in PREFLIGHT_MODES:
                try:
                    apply_kernel(state, UseAttack(0, 0), preflight=mode)
                    outcomes.add("accepted")
                except UnsupportedError as error:
                    outcomes.add(error.code)
            self.assertEqual(outcomes, {code})


# ---------------------------------------------------------------- かがくへんかガス・きぜつ・保存と再開


class InteractionTest(unittest.TestCase):
    """かがくへんかガス（特殊能力を消す）・きぜつとサイド・決定の途中の保存と再開・カードの保存則。"""

    def test_chemical_gas_suppresses_both_powers(self):
        """はたらいているかがくへんかガスは［うか］を消し（POWER_SUPPRESSED。状態は変わらない）、［ボスをよぶ］の使う機会を出さない（v0.8 の G4・v0.43 と同じ）。"""
        state = board(mon(KOGAS_KAKUNA, (G,)), mon(MUK, (), evolved_from="PMCG4-004"), deck=[KOGAS_BEEDRILL])
        assert_rejected(self, state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0), "POWER_SUPPRESSED")
        gas = board(mon(GIOVANNIS_MEOWTH, ()), mon(MUK, (), evolved_from="PMCG4-004"), hand=[GIOVANNIS_PERSIAN], deck=[GIOVANNI])
        done = audited(self, evolve_pid(gas, GIOVANNIS_PERSIAN, gas.players[0].active.pokemon_id))
        self.assertIsNone(done.decision)
        self.assertNotIn(GIOVANNI, cards_in(done, 0, "hand"))

    def test_dig_under_can_knock_out_a_benched_pokemon(self):
        """じめんにもぐるで控えポケモンが HP 以上になれば、ワザのあとにきぜつし、ワザを使ったプレイヤーがサイドを取る。"""
        state = board(mon(ROCKET_DIGLETT, (F,)), mon(HITMONCHAN, (F, F)), opponent_bench=({"card": RATTATA, "damage": 20},))
        target = pid_of(state, 1, RATTATA)
        done = attack(state, 0, answers=[(target,)])
        self.assertEqual(done.decision.kind, TAKE_PRIZE)
        self.assertEqual(done.decision.player, 0)
        self.assertIn("knock_out", kinds(done, len(state.log)))
        audited(self, answer(done, (done.decision.options[0],)))

    def test_storm_knocks_out_benched_pokemon_on_both_sides(self):
        """あらしをよぶ（「おもて」2 枚）で自分の控えもきぜつしうる。きぜつしたポケモンの持ち主の相手がサイドを取る。"""
        state = board(mon(GIOVANNIS_GYARADOS, (W,)), mon(HITMONCHAN, (F, F)), bench=({"card": RATTATA, "damage": 20},),
                      opponent_bench=({"card": RATTATA, "damage": 20},))
        done = attack(state, 0, H, H)
        knocked = events(done, len(state.log), "knock_out")
        self.assertEqual(sorted(e["player"] for e in knocked), [0, 1])
        while done.decision is not None:
            done = answer(done, (done.decision.options[0],))
        audited(self, done)
        self.assertEqual(len(done.players[0].prizes), 5)
        self.assertEqual(len(done.players[1].prizes), 5)

    def test_save_and_restore_in_the_middle_of_sleight(self):
        """てじなの段階 2 の決定を待つ状態を写して（clone・deepcopy・pickle）も、同じ答えで同じ結果（形式 11 の全体と乱数）。段階 1 でもどしたカードは山札にある。"""
        state = board(mon(SABRINAS_MR_MIME, (P,)), hand=[POTION, SWITCH], deck=[GRASS, WATER])
        stage2 = answer(attack(state, 0), tuple(card_of(state, 0, c) for c in (POTION, SWITCH)))
        self.assertEqual(stage2.decision.context_value("count"), 2)
        self.assertEqual(sorted(cards_in(stage2, 0, "deck")), sorted([GRASS, WATER, POTION, SWITCH]))
        expected = snapshot(answer(stage2, tuple(stage2.decision.options)))
        for copied in (stage2.clone(), copy.deepcopy(stage2), pickle.loads(pickle.dumps(stage2))):
            self.assertEqual(snapshot(answer(copied, tuple(copied.decision.options))), expected)
        self.assertEqual(card_count(stage2, 0), card_count(state, 0))

    def test_cards_are_conserved(self):
        """スターブーメラン・わるいいたずら・ラッキーたまご・おつかいで、カードの枚数（プレイヤーごとのすべてのゾーン）は変わらない。"""
        cases = [
            (board(mon(MISTYS_STARYU, (W,)), mon(HITMONCHAN, (F, F)), bench=(RATTATA,)), (H,)),
            (board(mon(BLANK_CHANSEY, (F,)), hand=[POTION, SWITCH]), (T,)),
            (board(mon(ERIKAS_BULBASAUR, (G, G)), deck=[POTION, GRASS]), (H,)),
        ]
        for state, sides in cases:
            with self.subTest(card=state.cards[state.players[0].active.card].card_id):
                done = attack(state, 0 if state.cards[state.players[0].active.card].card_id != ERIKAS_BULBASAUR else 1, *sides)
                while done.decision is not None:
                    d = done.decision
                    done = answer(done, tuple(d.options[:max(d.min_choices, 1)]))
                for player in (0, 1):
                    self.assertEqual(card_count(done, player), card_count(state, player))


class InvariantTest(unittest.TestCase):
    """2 つの記録は状態に持ち、ログと照らす不変条件（engine._once_attack_problems・_evolution_permission_problems）で確かめる。ログを読み直して決めない。"""

    def test_records_without_log_are_invariant_violations(self):
        """ログ（once_attack_recorded・evolution_permission）のない記録、1 度だけ使えるワザでないワザの記録、サカキのポケモンでないポケモンの許可、
        前の番の許可は、不変条件の違反。"""
        state = board(mon(FARFETCHD, (F, F, F)), bench=[{"card": GIOVANNIS_MAGIKARP}, MAGIKARP])
        farfetchd = state.players[0].active
        broken = state.clone()
        broken.players[0].active.attacks_used_once = ((farfetchd.card, 0),)
        self.assertTrue(check_invariants(broken))
        broken = state.clone()
        broken.players[0].active.attacks_used_once = ((farfetchd.card, 1),)  # ナベでたたくは 1 度だけ使えるワザではない
        self.assertTrue(check_invariants(broken))
        broken = state.clone()
        find(broken, 0, GIOVANNIS_MAGIKARP).evolution_permission_turn = TURN
        self.assertTrue(check_invariants(broken))
        permitted = answer(play_trainer(board(mon(RATTATA, ()), bench=[{"card": GIOVANNIS_MAGIKARP}, MAGIKARP], hand=[GIOVANNI]), GIOVANNI),
                           (pid_of(board(mon(RATTATA, ()), bench=[{"card": GIOVANNIS_MAGIKARP}, MAGIKARP], hand=[GIOVANNI]), 0, GIOVANNIS_MAGIKARP),))
        self.assertEqual(check_invariants(permitted), [])
        broken = permitted.clone()
        find(broken, 0, MAGIKARP).evolution_permission_turn = TURN  # サカキのポケモンではない
        self.assertTrue(check_invariants(broken))
        broken = permitted.clone()
        find(broken, 0, GIOVANNIS_MAGIKARP).evolution_permission_turn = TURN - 2  # 前の番の許可
        self.assertTrue(check_invariants(broken))


# ---------------------------------------------------------------- 正式な対戦開始からの対戦


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.44 の組の手順）。"""

    def test_persian_searches_giovanni_then_giovanni_lets_a_new_pokemon_evolve(self):
        """サカキのペルシアンの［ボスをよぶ］で山札から手札に加えたサカキ（同じ uid）を使い、その許可で、その番に場に出した・進化したサカキのポケモンを同じ番に
        進化させる流れが、正式な対戦（new_game・60 枚・サイド 6 枚）の中で起こる（V44 対 W44 の seed 0・1）。ログの監査・不変条件・書き出し・やり直しも確かめる。"""
        from tools import existing_effect_games as games

        found = []
        for seed, labels in ((0, ("V44", "W44")), (1, ("V44", "W44"))):
            result = games.play(labels, seed, keep_state=True)
            self.assertEqual(result["audit"], {}, (labels, seed))
            self.assertNotIn(result["outcome"], ("internal_error", "unexpected_rejection", "step_limit"))
            log = result["state"].log
            for i, e in enumerate(log):
                if e["kind"] != "search_deck" or not str(e.get("power", "")).startswith(GIOVANNIS_PERSIAN):
                    continue
                self.assertEqual(result["state"].cards[e["card"]].card_id, GIOVANNI)
                used = next((k for k in range(i, len(log)) if log[k]["kind"] == "play_trainer" and log[k]["card"] == e["card"]), None)
                permit = None if used is None else next(
                    (k for k in range(used, len(log)) if log[k]["kind"] == "evolution_permission" and log[k]["trainer"] == e["card"]), None)
                if permit is None:
                    continue
                pid, turn = log[permit]["pokemon_id"], log[permit]["turn"]
                evolved = [x for x in log[permit:] if x["kind"] == "evolve" and x["pokemon_id"] == pid and x["turn"] == turn]
                # 許可がなければ進化できなかった（その番に場に出した・進化した）ポケモン
                before = any(x["kind"] == "evolve" and x["pokemon_id"] == pid and x["turn"] == turn for x in log[:permit]) or any(
                    x["kind"] == "play_to_bench" and x["card"] == log[permit]["pokemon"] and x["turn"] == turn for x in log[:permit])
                if evolved and before:
                    found.append((seed, turn))
        self.assertTrue(found, "［ボスをよぶ］→ サカキ → 許可のある進化の流れが起こらない")

    def test_batch_runs_without_audit_failures(self):
        """v0.44 の 4 組を 4 seed ずつ（席を入れかえて 32 局）。どれも監査の失敗・想定外の拒否・内部エラーがなく、14 枚のどのワザも 1 度は使われる。"""
        from tools import existing_effect_games as games

        results = games.run(range(4), pairings=games.PAIRINGS_V0_44)
        used = set()
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"))
                for card, uses in game.get("card_uses", {}).items():
                    used |= {(card, int(k.split("#")[1])) for k in uses if re.fullmatch(r"attack#\d", k)}
        self.assertEqual(set(EXPECTED) - used, set())


if __name__ == "__main__":
    unittest.main()
