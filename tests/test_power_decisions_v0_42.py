"""v0.42: 回復・カウンター操作と、特殊能力を持つ進化系統を中心とする 15 枚と、特殊能力の決定・再開・使用後の処理の共通化（docs/power-decisions-v0.42.md）。

ナツメのルージュラ（PMCG6-052）・ラフレシア（PMCG2-014）・ヤドラン（PMCG3-028）・ゲンガー（PMCG3-031）・エリカのラフレシア（PMCG5-014）・ナツメのケーシィ（PMCG6-043）・
ナツメのユンゲラー（PMCG6-047）・カイリュー（PMCG3-043）・エリカのウツボット（PMCG5-015）・わるいユンゲラー（PMCG4-034）・わるいフーディン（PMCG4-035）・
メノクラゲ（PMCG3-011）・ドククラゲ（PMCG3-017）・エリカのピッピ（PMCG5-060）・エリカのピクシー（PMCG5-065）。どれも kyuura データの採用（処理に使う文面は
kyuura の印刷の文面。カイリューの［かけつける］だけは kyuura の data/curation/card_differences.json の PMCG3-043（確度: 確実）の最新の説明。採用したデータの
コミット ecb2d69）と pcg-search.com の同じ版のページとの照合。ガイドブックは読んでいない。

根拠にした既存の記録: p.311・p.323（特殊能力の使い方。エンジンの v0.5 の記録）・GR-2000-P320-COUNTER-MOVE（ダメージカウンターの移動はダメージではない。v0.7 の S19）・
GR-2000-P320-RECOVERY（回復）・GR-2000-P309-ATTACK-PROCEDURE（書かれた順に処理する）・GR-2000-P323-KNOCKOUT（きぜつ）・CR-COUNTERATTACK-TIMING（「ダメージを
受けたとき」の効果の時点）と、エンジンの v0.7（ダメージスワップ）・v0.8（かがくへんかガス）・v0.10（はんげき）・v0.31（しぜんになおる・HC1・HC5・HC8・HC9）・
v0.36（RD）・v0.40（SG1）・v0.17b（Z23）の記録。新しい未解決は PW1（``UNRESOLVED_POWER_SWITCH_WITHOUT_OPPONENT_BENCH``）・PW2（``UNRESOLVED_POWER_DISCARD_WITHOUT_HAND``）。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
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
from kyuura_engine.cards import EnergyType, load_card_pool, read_extract
from kyuura_engine.decisions import DISCARD_FROM_HAND, PROMOTE_ACTIVE, REMOVE_COUNTERS, RETURN_ENERGY, SEARCH_DECK, SELECT_POKEMON, TAKE_PRIZE
from kyuura_engine.resolution import PREFLIGHT_MODES, programs, v013_checks
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.state import Phase
from scripts import check_card_sources as cs
from scripts.extract_kyuura_cards import KYUURA_COMMIT
from tests.helpers import (
    ABRA,
    ALAKAZAM,
    ATTACK_TYPES_SINCE_V0_17,
    BULBASAUR,
    CLEFABLE,
    CLEFAIRY,
    DARK_ALAKAZAM,
    DARK_KADABRA,
    DRAGONAIR,
    DRAGONITE,
    DRATINI,
    ERIKAS_BELLSPROUT,
    ERIKAS_CLEFABLE,
    ERIKAS_CLEFAIRY,
    ERIKAS_GLOOM,
    ERIKAS_ODDISH,
    ERIKAS_VICTREEBEL,
    ERIKAS_VILEPLUME,
    ERIKAS_WEEPINBELL,
    FIGHTING,
    FIRE,
    GASTLY,
    GENGAR,
    GIOVANNIS_NIDOKING,
    GIOVANNIS_NIDORAN_M,
    GIOVANNIS_NIDORINO,
    GLOOM,
    GRIMER,
    GRASS,
    GUST,
    HAUNTER,
    HITMONCHAN,
    JUNGLE_ODDISH,
    KADABRA,
    LIGHTNING,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MEWTWO,
    MISTYS_PSYDUCK,
    MUK,
    PSYCHIC,
    RATTATA,
    ROCKET_ABRA,
    ROCKET_SLOWPOKE,
    SABRINAS_ABRA,
    SABRINAS_JYNX,
    SABRINAS_KADABRA,
    SABRINAS_SLOWBRO,
    SABRINAS_SLOWPOKE,
    SLOWBRO,
    SLOWPOKE,
    TENTACOOL,
    TENTACRUEL,
    V0_42_POKEMON,
    VICTREEBEL,
    VILEPLUME,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.test_barrier_resume_coin_bonus_v0_34 import assert_stops, events, first, full, play

ROOT = pathlib.Path(__file__).resolve().parent.parent
TURN = 7
DOC = ROOT / "docs" / "power-decisions-v0.42.md"
F, W, G, P, R, L = FIGHTING, WATER, GRASS, PSYCHIC, FIRE, LIGHTNING
BELOW = {VILEPLUME: [JUNGLE_ODDISH, GLOOM], SLOWBRO: SLOWPOKE, GENGAR: [GASTLY, HAUNTER], ERIKAS_VILEPLUME: [ERIKAS_ODDISH, ERIKAS_GLOOM],
         SABRINAS_KADABRA: SABRINAS_ABRA, DRAGONITE: [DRATINI, DRAGONAIR], ERIKAS_VICTREEBEL: [ERIKAS_BELLSPROUT, ERIKAS_WEEPINBELL],
         DARK_KADABRA: ABRA, DARK_ALAKAZAM: [ABRA, DARK_KADABRA], TENTACRUEL: TENTACOOL, ERIKAS_CLEFABLE: ERIKAS_CLEFAIRY, HAUNTER: GASTLY,
         MACHAMP: [MACHOP, MACHOKE], GIOVANNIS_NIDOKING: [GIOVANNIS_NIDORAN_M, GIOVANNIS_NIDORINO], ALAKAZAM: [ABRA, KADABRA], KADABRA: ABRA,
         CLEFABLE: CLEFAIRY, MUK: GRIMER}
# どのワザも使えるエネルギー（無色は別のタイプで払う）
ENERGY = {SABRINAS_JYNX: (P, F), VILEPLUME: (G, G, G), SLOWBRO: (P, P), GENGAR: (P, P, P), ERIKAS_VILEPLUME: (G, G, G), SABRINAS_ABRA: (P,),
          SABRINAS_KADABRA: (P, F, F), DRAGONITE: (F, F, F, F), ERIKAS_VICTREEBEL: (G, G, G), DARK_KADABRA: (P, P), DARK_ALAKAZAM: (P, P, P),
          TENTACOOL: (W,), TENTACRUEL: (W, W), ERIKAS_CLEFAIRY: (F, F), ERIKAS_CLEFABLE: (F, F, F)}
# 登録の実装の型と値（カード id, ワザの位置）
EXPECTED = {
    (SABRINAS_JYNX, 0): (E.HealChosenOpponentThenDraw, {}),
    (SABRINAS_JYNX, 1): (E.DamageThenRetreatLockOnHeads, {}),
    (VILEPLUME, 0): (E.CoinFlipDamageThenSelfConfuse, {"coins": 3, "damage_per_heads": 40}),
    (SLOWBRO, 0): (E.ParalyzeOnHeads, {}),
    (GENGAR, 0): (E.DamageThenChosenBenchDamage, {"bench_damage": 10}),
    (ERIKAS_VILEPLUME, 0): (E.DamageAndDrain, {}),
    (SABRINAS_ABRA, 0): (E.ReturnEnergyThenDamage, {"energy_type": EnergyType.PSYCHIC}),
    (SABRINAS_KADABRA, 0): (E.PlaceCountersToRemainingHpOnHeads, {"remaining": 10}),
    (SABRINAS_KADABRA, 1): (E.DamageOnly, {}),
    (DRAGONITE, 0): (E.CoinFlipDamage, {"coins": 2, "damage_per_heads": 40}),
    (ERIKAS_VICTREEBEL, 0): (E.DamageOnly, {}),
    (DARK_KADABRA, 0): (E.DamageIgnoringWeaknessResistance, {}),
    (DARK_ALAKAZAM, 0): (E.DamageThenOptionalSelfSwitch, {}),
    (DARK_ALAKAZAM, 1): (E.DamageIgnoringWeaknessResistance, {}),
    (TENTACOOL, 0): (E.DamageOnly, {}),
    (TENTACRUEL, 0): (E.ConfuseOnHeadsWithoutDamage, {}),
    (TENTACRUEL, 1): (E.PoisonOpponent, {}),
    (ERIKAS_CLEFAIRY, 0): (E.EvolveFromDeckOnHeads, {}),
    (ERIKAS_CLEFAIRY, 1): (E.DamageOnly, {}),
    (ERIKAS_CLEFABLE, 0): (E.ReturnOwnPokemonToHandOnHeads, {}),
    (ERIKAS_CLEFABLE, 1): (E.DamageOnly, {}),
}
# 特殊能力の登録（カード id → (型, 宣言するか, 自分の番ごとに 1 回か, 処理で「きぜつ」させうるか)）
POWERS = {
    VILEPLUME: (E.HealOwnPokemonOnHeads, True, True, False),  # ［ヒーリング］
    SLOWBRO: (E.MoveDamageCounterToSelf, True, False, False),  # ［へんなこうどう］
    GENGAR: (E.MoveOpponentDamageCounter, True, True, True),  # ［のろい］
    ERIKAS_VILEPLUME: (E.ConfuseDamageSourceOnHeads, False, False, False),  # ［ぼうぎょかふん］
    DRAGONITE: (E.SwitchSelfFromBench, True, True, False),  # ［かけつける］
    ERIKAS_VICTREEBEL: (E.SwitchOpponentOnHeads, True, True, False),  # ［かおりのわな］
    DARK_KADABRA: (E.DiscardThenDraw, True, True, False),  # ［ぶっしつこうかん］
    TENTACOOL: (E.ReturnSelfToHand, True, False, False),  # ［おくびょう］
}
NEW_ATTACK_TYPES = {E.HealChosenOpponentThenDraw, E.CoinFlipDamageThenSelfConfuse, E.ReturnEnergyThenDamage, E.PlaceCountersToRemainingHpOnHeads,
                    E.DamageThenOptionalSelfSwitch, E.EvolveFromDeckOnHeads, E.ReturnOwnPokemonToHandOnHeads}
# pcg-search.com の対象の版（サイトの一覧の番号）と、違いのあった欄
EDITIONS = {SABRINAS_JYNX: "055/098", VILEPLUME: "007/048", SLOWBRO: "028/048", GENGAR: "031/048", ERIKAS_VILEPLUME: "008/096", SABRINAS_ABRA: "044/098",
            SABRINAS_KADABRA: "045/098", DRAGONITE: "043/048", ERIKAS_VICTREEBEL: "013/096", DARK_KADABRA: "032/065", DARK_ALAKAZAM: "033/065",
            TENTACOOL: "012/048", TENTACRUEL: "013/048", ERIKAS_CLEFAIRY: "062/096", ERIKAS_CLEFABLE: "063/096"}
DIFFERENCES = {GENGAR: ["pokemon.attacks[0].text.ja"], ERIKAS_VILEPLUME: ["pokemon.powers[0].text.ja", "pokemon.attacks[0].text.ja"],
               DRAGONITE: ["pokemon.powers[0].text.ja"]}


def mon(card, energy=None, **extra):
    spec = {"card": card, "energy": list(ENERGY.get(card, ()) if energy is None else energy), **extra}
    if BELOW.get(card) is not None and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), deck=None, hand=(), opponent_hand=(), turn=TURN,
          opponent_deck=None, prizes=6):
    def spec(b):
        return mon(b, ()) if isinstance(b, str) and b in BELOW else b

    me = {"active": active, "bench": [spec(b) for b in bench], "hand": list(hand), "prizes": prizes}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent or mon(HITMONCHAN, (F, F)), "bench": [spec(b) for b in opponent_bench], "hand": list(opponent_hand)}
    if opponent_deck is not None:
        them["deck"] = list(opponent_deck)
    return build_test_state([me, them], turn_number=turn)


def snapshot(state):
    return full(state), [dict(e) for e in state.log], repr(state.rng.getstate())


def pid_of(state, player, card, nth=0):
    return [p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card][nth]


def pokemon_of(state, pid):
    return state.find_pokemon(pid)[1]


def card_of(state, player, card, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card)


def answer(state, choices):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)))


def power(state, pokemon, *sides, player=0, **choices):
    state = with_coin_results(state, *sides) if sides else state
    return apply_kernel(state, UsePokemonPower(player, pokemon, 0, **choices))


def attack(state, index, *sides, answers=(), player=0, mode="derived"):
    return play(with_coin_results(state, *sides) if sides else state, UseAttack(player, index), answers, mode=mode)


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


def kinds(state, since):
    return [e["kind"] for e in state.log[since:]]


# ---------------------------------------------------------------- 登録・写し・記録


class CardDataTest(unittest.TestCase):
    """15 枚の登録・写し・採用の記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_fifteen_requested_cards(self):
        """対象は依頼の 15 枚。写しの組 pool_v0_42 は 15 枚で、どれも対戦に使える（ワザだけでなく、特殊能力も登録したカード全体が対応）。名前の似た別のカード
        （ナツメのルージュラとルージュラ・ラフレシアとエリカのラフレシア・ヤドランとナツメのヤドラン・ナツメのケーシィとケーシィ・ナツメのユンゲラーとわるい
        ユンゲラーとユンゲラー・エリカのウツボットとウツボット・わるいフーディンとフーディン・エリカのピッピとピッピ・エリカのピクシーとピクシー）は別の名前。"""
        self.assertEqual(len(V0_42_POKEMON), 15)
        self.assertEqual(list(read_extract()["pool_v0_42"]), list(V0_42_POKEMON))
        for card in V0_42_POKEMON:
            with self.subTest(card=card):
                self.assertTrue(self.pool.is_playable(card))
                self.assertEqual(bool(self.pool.get(card).powers), card in POWERS)
        for ours, other in ((SABRINAS_JYNX, "PMCG1-048"), (VILEPLUME, ERIKAS_VILEPLUME), (SLOWBRO, SABRINAS_SLOWBRO), (SABRINAS_ABRA, ABRA),
                            (SABRINAS_KADABRA, DARK_KADABRA), (SABRINAS_KADABRA, KADABRA), (DARK_KADABRA, KADABRA), (ERIKAS_VICTREEBEL, VICTREEBEL),
                            (DARK_ALAKAZAM, ALAKAZAM), (ERIKAS_CLEFAIRY, CLEFAIRY), (ERIKAS_CLEFABLE, CLEFABLE)):
            with self.subTest(card=ours, other=other):
                self.assertNotEqual(self.pool.get(ours).name_ja, self.pool.get(other).name_ja)

    def test_every_attack_is_registered_with_the_expected_implementation(self):
        """21 のワザがどれも登録され、型と値が説明に合う。説明文のあるワザは、写しの文面（照合用）と処理に使う文面（kyuura の印刷の文面）が同じ。"""
        attacks = [(card, a.index) for card in V0_42_POKEMON for a in self.pool.get(card).attacks]
        self.assertEqual(sorted(attacks), sorted(EXPECTED))
        self.assertEqual(len(attacks), 21)
        for (card, index), (cls, values) in EXPECTED.items():
            with self.subTest(card=card, index=index):
                entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
                self.assertIs(type(entry.effect), cls)
                for name, value in values.items():
                    self.assertEqual(getattr(entry.effect, name), value)
                printed = self.pool.get(card).attacks[index]
                self.assertEqual((entry.name_ja, entry.text_ja), (printed.name_ja, printed.text_ja))
                if printed.text_ja:
                    self.assertEqual(entry.play_text_ja, printed.text_ja)
                self.assertEqual(entry.effect.check(printed), [])

    def test_every_power_is_registered(self):
        """8 つの特殊能力がどれも登録され、宣言するか・自分の番ごとに 1 回か・処理で「きぜつ」させうるかが説明に合う。処理に使う文面は kyuura の印刷の文面
        （カイリューの［かけつける］だけ card_differences の最新の説明。特殊状態の記述がない）。"""
        for card, (cls, declared, once, knocks) in POWERS.items():
            definition = self.pool.get(card)
            with self.subTest(card=card):
                [printed] = definition.powers
                entry = E.DEFAULT_EFFECTS.power_entry(card, 0)
                self.assertIs(type(entry.effect), cls)
                self.assertEqual((entry.effect.declared, entry.effect.once_per_turn, entry.effect.may_knock_out), (declared, once, knocks))
                self.assertEqual((entry.name_ja, entry.text_ja), (printed.name_ja, printed.text_ja))
                self.assertEqual(entry.effect.check(printed), [])
                if card == DRAGONITE:
                    self.assertEqual(entry.source, "kyuura data/curation/card_differences.json#PMCG3-043")
                    self.assertNotIn("ねむり", entry.play_text_ja)
                    self.assertIn("ねむり", printed.text_ja)
                else:
                    self.assertEqual(entry.play_text_ja, printed.text_ja)
        # 宣言して使う特殊能力の実装は、決定を出すものだけが resume を上書きする
        for cls in (E.HealOwnPokemonOnHeads, E.SwitchOpponentOnHeads, E.DiscardThenDraw):
            self.assertIsNot(cls.resume, E.PowerEffect.resume)
        for cls in (E.MoveDamageCounterToSelf, E.MoveOpponentDamageCounter, E.SwitchSelfFromBench, E.ReturnSelfToHand):
            self.assertIs(cls.resume, E.PowerEffect.resume)

    def test_new_types_are_kernel_programs_outside_the_v013_contract(self):
        """v0.42 のワザの型（7）は解決の基盤の要素の並び（``programs.BUILDERS``）で処理し、v0.13 の約束（``resolve``・``resume``）を上書きしない。
        ``v013_checks.VERIFIED`` に入れない。"""
        self.assertEqual(len(NEW_ATTACK_TYPES), 7)
        for cls in NEW_ATTACK_TYPES:
            with self.subTest(cls=cls.__name__):
                self.assertIn(cls, programs.BUILDERS)
                self.assertIn(cls, ATTACK_TYPES_SINCE_V0_17)
                self.assertNotIn(cls, v013_checks.VERIFIED)
                self.assertIs(cls.resolve, E.AttackEffect.resolve)
                self.assertIs(cls.resume, E.AttackEffect.resume)

    def test_opponent_effect_elements_match_the_programs(self):
        for (card, index), _ in EXPECTED.items():
            effect = E.DEFAULT_EFFECTS.attack_entry(card, index).effect
            with self.subTest(card=card, index=index):
                program = programs.BUILDERS[type(effect)](effect)
                self.assertEqual(set(effect.opponent_effect_elements), set(programs.opponent_effect_elements(program)))

    def test_adoption_records_and_external_checks(self):
        """15 枚はどれも kyuura データの採用の記録を持ち、pcg-search.com の同じ版のページと照合した（特殊能力の欄も）。違いは書き方・記号だけで、処理に影響しない。
        処理に使う文面の根拠は、特殊能力と説明文のあるワザごと（カイリューの特殊能力は card_differences の記録）。過去の原典照合の記録には入れない。"""
        sources = cs.load_sources()["cards"]
        verification = json.loads((ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8"))["cards"]
        links = cs.load_links()["latest_descriptions"]
        for card in V0_42_POKEMON:
            with self.subTest(card=card):
                record = sources[card]
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"]),
                                 ("kyuura_data", "adopted", KYUURA_COMMIT, []))
                expected = {f"attack/{a.index}" for a in self.pool.get(card).attacks if a.text_ja} | {
                    f"power/{i}" for i, _ in enumerate(self.pool.get(card).powers)}
                self.assertEqual(set(record["play_text"]), expected)
                for target, basis in record["play_text"].items():
                    if (card, target) == (DRAGONITE, "power/0"):
                        self.assertEqual(basis, "kyuura data/curation/card_differences.json#PMCG3-043")
                        self.assertEqual(links["difference_text"][f"{card}/{target}"], basis)
                    else:
                        self.assertEqual(basis, "kyuura_printed_text")
                        self.assertIn(f"{card}/{target}", links["adopted_printed_text"])
                [check] = record["external_checks"]
                self.assertEqual((check["site"], check["edition"]["list_number"]), ("pcg-search.com", EDITIONS[card]))
                if self.pool.get(card).powers:
                    self.assertIn("pokemon.powers[0].text.ja", check["checked_fields"])
                if card in DIFFERENCES:
                    self.assertEqual(check["result"], "differences")
                    self.assertEqual([d["field"] for d in check["differences"]], DIFFERENCES[card])
                    self.assertFalse(any(d["affects_behavior"] for d in check["differences"]))
                else:
                    self.assertEqual((check["result"], check["differences"]), ("match", []))
                self.assertNotIn(card, verification)

    def test_no_card_specific_branch_in_the_engine(self):
        """engine.py・resolution/ に v0.42 のカード id での分岐を加えていない（効果の型・特殊能力の型の項目で表す）。"""
        for path in [ROOT / "kyuura_engine" / "engine.py", *(ROOT / "kyuura_engine" / "resolution").glob("*.py")]:
            text = path.read_text(encoding="utf-8")
            for card in V0_42_POKEMON:
                with self.subTest(path=path.name, card=card):
                    self.assertNotIn(card, text)

    def test_new_and_reused_questions(self):
        """新しい停止コードは PW1・PW2 の 2 つ（特殊能力の確認で、宣言の前に止める。研究の対応表では kyuura の未解決の一覧にない）。ほかは既存の問い・コード
        （HC8・HC5・HC1・Z23・SG1・HC3・T19b・T27・UNRESOLVED_EVOLUTION_HP）を使う。"""
        links = cs.load_links()["stop_codes"]
        for code, ruling in (("UNRESOLVED_POWER_SWITCH_WITHOUT_OPPONENT_BENCH", "PW1"), ("UNRESOLVED_POWER_DISCARD_WITHOUT_HAND", "PW2")):
            entry = links[code]
            self.assertEqual((entry["kyuura_disposition"], entry["kyuura_issue"], entry["engine_rulings"][0]["ruling_id"]),
                             ("not_in_kyuura", None, ruling))
        codes = {q.code for q in QUESTIONS.values()}
        for code in ("UNRESOLVED_DISCARD_ENERGY_TIMING", "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE",
                     "UNRESOLVED_PREVENTED_EFFECT_COIN", "UNRESOLVED_EVADED_EFFECT_COIN", "UNRESOLVED_TRANSPARENCY_COIN_ORDER"):
            self.assertIn(code, codes)
        for code in ("UNRESOLVED_POWER_HEAL_WITHOUT_DAMAGE", "UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED", "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO"):
            self.assertIn(code, links)


class EvolutionTest(unittest.TestCase):
    """進化先は、通常の進化の操作で、進化元の名前（完全一致。収録の弾で制限しない）のポケモンから進化する。"""

    PAIRS = ((SLOWBRO, SLOWPOKE), (SLOWBRO, ROCKET_SLOWPOKE), (SABRINAS_KADABRA, SABRINAS_ABRA), (DARK_KADABRA, ABRA), (DARK_KADABRA, ROCKET_ABRA),
             (TENTACRUEL, TENTACOOL), (ERIKAS_CLEFABLE, ERIKAS_CLEFAIRY))
    STAGE2 = ((VILEPLUME, GLOOM, JUNGLE_ODDISH), (GENGAR, HAUNTER, GASTLY), (ERIKAS_VILEPLUME, ERIKAS_GLOOM, ERIKAS_ODDISH),
              (DRAGONITE, DRAGONAIR, DRATINI), (ERIKAS_VICTREEBEL, ERIKAS_WEEPINBELL, ERIKAS_BELLSPROUT), (DARK_ALAKAZAM, DARK_KADABRA, ABRA))

    def evolve(self, spec, card):
        state = board(spec, hand=[card])
        return apply_kernel(state, EvolvePokemon(0, card_of(state, 0, card), state.players[0].active.pokemon_id))

    def test_evolves_from_every_card_with_the_exact_name(self):
        for card, base in self.PAIRS:
            with self.subTest(card=card, base=base):
                done = self.evolve({"card": base, "energy": []}, card)
                self.assertEqual(done.cards[done.players[0].active.card].card_id, card)
        for card, stage1, basic in self.STAGE2:
            with self.subTest(card=card):
                done = self.evolve({"card": stage1, "energy": [], "evolved_from": basic, "evolved_turn": 3}, card)
                self.assertEqual(done.cards[done.players[0].active.card].card_id, card)
                self.assertEqual(len(done.players[0].active.evolution_stack), 2)

    def test_names_that_only_look_alike_are_rejected(self):
        """ナツメのヤドンからヤドラン・ケーシィからナツメのユンゲラー・ナツメのケーシィからわるいユンゲラー・ピッピからエリカのピクシー・ユンゲラーからわるい
        フーディン・エリカのクサイハナからラフレシア・クサイハナからエリカのラフレシアへは進化できない（名前が違う）。"""
        for card, base in ((SLOWBRO, SABRINAS_SLOWPOKE), (SABRINAS_KADABRA, ABRA), (DARK_KADABRA, SABRINAS_ABRA), (ERIKAS_CLEFABLE, CLEFAIRY)):
            with self.subTest(card=card, base=base):
                state = board({"card": base, "energy": []}, hand=[card])
                assert_rejected(self, state, EvolvePokemon(0, card_of(state, 0, card), state.players[0].active.pokemon_id),
                                "EVOLUTION_NAME_MISMATCH", IllegalActionError)
        for card, stage1, basic in ((DARK_ALAKAZAM, KADABRA, ABRA), (VILEPLUME, ERIKAS_GLOOM, ERIKAS_ODDISH), (ERIKAS_VILEPLUME, GLOOM, JUNGLE_ODDISH)):
            with self.subTest(card=card, stage1=stage1):
                state = board({"card": stage1, "energy": [], "evolved_from": basic, "evolved_turn": 3}, hand=[card])
                assert_rejected(self, state, EvolvePokemon(0, card_of(state, 0, card), state.players[0].active.pokemon_id),
                                "EVOLUTION_NAME_MISMATCH", IllegalActionError)


# ---------------------------------------------------------------- 特殊能力の共通の処理


class PowerFlowTest(unittest.TestCase):
    """宣言して使う特殊能力の共通の処理（宣言・回数・決定・再開・使用後の処理）。"""

    def test_power_is_not_an_attack(self):
        """特殊能力はワザとして処理しない: 使っても番は終わらず（段階 MAIN・番の番号・番のプレイヤーは同じ）、こんらんのコイン・ワザのログはない。使ったあとで
        ワザを使える（p.311）。番のプレイヤーのこんらんの対戦ポケモンがいても、ベンチのポケモンの特殊能力は使える。"""
        state = board(mon(SABRINAS_JYNX, confusion=True), bench=(mon(VILEPLUME), mon(RATTATA, (), damage=20)))
        done = power(state, pid_of(state, 0, VILEPLUME), H)
        done = answer(done, (pid_of(done, 0, RATTATA),))
        self.assertEqual((done.phase, done.turn_number, done.current_player), (Phase.MAIN, TURN, 0))
        self.assertFalse({"attack", "confusion_check", "turn_end"} & set(kinds(done, len(state.log))))
        self.assertEqual(check_invariants(done), [])
        attacked = attack(done, 1, H, H)
        self.assertIn("attack", kinds(attacked, len(done.log)))

    def test_once_per_turn_is_recorded_at_the_declaration(self):
        """「自分の番ごとに1回」の特殊能力は、宣言のときに使った回数を状態（``power_uses_this_turn``）に記録する（コインの「うら」でも使ったことになる）。同じ番の
        2 回目は ``POWER_ALREADY_USED``。次の自分の番には、また使える。ログから回数を数えない。"""
        state = board(mon(VILEPLUME), bench=(mon(RATTATA, (), damage=20),))
        vile = pid_of(state, 0, VILEPLUME)
        tails = power(state, vile, T)
        self.assertEqual(tails.power_uses_this_turn, ((vile, 0),))
        self.assertIsNone(tails.decision)
        assert_rejected(self, tails, UsePokemonPower(0, vile, 0), "POWER_ALREADY_USED", IllegalActionError)
        later = apply_kernel(apply_kernel(tails, EndTurn(0)), EndTurn(1))
        self.assertEqual(later.power_uses_this_turn, ())
        self.assertEqual(kinds(power(later, vile, T), len(later.log)), ["pokemon_power", "coin_flip"])

    def test_unlimited_power_can_be_used_again(self):
        """［へんなこうどう］（回数の制限なし）は同じ番に何度でも使え、回数を記録しない。"""
        state = board(mon(SLOWBRO), bench=(mon(RATTATA, (), damage=20),))
        bro, rat = pid_of(state, 0, SLOWBRO), pid_of(state, 0, RATTATA)
        once = power(state, bro, source=rat)
        twice = power(once, bro, source=rat)
        self.assertEqual((pokemon_of(twice, bro).damage, pokemon_of(twice, rat).damage, twice.power_uses_this_turn), (20, 0, ()))

    def test_power_decision_waits_and_resumes(self):
        """決定を出す特殊能力（ヒーリング・かおりのわな・ぶっしつこうかん）は、再開先 ``"power"`` の決定を出して待つ（段階 DECISION。番のプレイヤー・番の番号は
        同じ）。決定は使ったプレイヤーが答え、答えのあとは宣言・回数・コインを繰り返さず、処理の続きだけを行う。待つ間の状態は書き出し（形式 2 以上）と pickle で
        同じ状態にもどり、形式 1 は書き出せない（黙って落とさない）。"""
        state = board(mon(VILEPLUME), bench=(mon(RATTATA, (), damage=20),))
        waiting = power(state, pid_of(state, 0, VILEPLUME), H)
        d = waiting.decision
        self.assertEqual((waiting.phase, d.resume, d.kind, d.player, d.min_choices, d.max_choices), (Phase.DECISION, "power", SELECT_POKEMON, 0, 1, 1))
        self.assertEqual(d.options, (pid_of(state, 0, RATTATA),))
        self.assertEqual(check_invariants(waiting), [])
        self.assertEqual(full(pickle.loads(pickle.dumps(waiting))), full(waiting))
        with self.assertRaises(ValueError):
            state_to_dict(waiting, format_version=1)
        for version in range(2, 11):
            if version >= 10:
                state_to_dict(waiting, format_version=version)
        done = answer(waiting, d.options)
        self.assertEqual(kinds(done, len(waiting.log)), ["power_heal"])
        self.assertEqual((done.phase, done.turn_number), (Phase.MAIN, TURN))

    def test_invalid_answers_are_rejected_without_change(self):
        """特殊能力の決定への不正な答え（相手のプレイヤー・選べないもの・数・原典で決められない選択）は、状態を変えずに拒否する。"""
        state = board(mon(VILEPLUME), bench=(mon(RATTATA, (), damage=20),))
        waiting = power(state, pid_of(state, 0, VILEPLUME), H)
        d = waiting.decision
        assert_rejected(self, waiting, ResolveDecision(1, d.id, d.options), "NOT_YOUR_DECISION", IllegalActionError)
        assert_rejected(self, waiting, ResolveDecision(0, d.id, (pid_of(waiting, 0, VILEPLUME),)), "INVALID_CHOICE", IllegalActionError)
        assert_rejected(self, waiting, ResolveDecision(0, d.id, ()), "INVALID_CHOICE_COUNT", IllegalActionError)
        assert_rejected(self, waiting, ResolveDecision(0, d.id + 1, d.options), "WRONG_DECISION", IllegalActionError)
        assert_rejected(self, waiting, UseAttack(0, 0), "WRONG_PHASE", IllegalActionError)

    def test_status_restrictions_follow_each_text(self):
        """ねむり・マヒ・こんらんのとき使えない特殊能力（説明に書いてあるもの）は、使うポケモンの特殊状態で拒否する（どくは使える）。ぼうぎょかふんは
        宣言しない（``POWER_NOT_DECLARABLE``）。"""
        cases = ((VILEPLUME, {}), (SLOWBRO, {"source": None}), (GENGAR, {}), (ERIKAS_VICTREEBEL, {}), (DARK_KADABRA, {}), (TENTACOOL, {}))
        for card, _ in cases:
            for condition, code in (({"sleep": True}, "POKEMON_ASLEEP"), ({"paralysis": TURN - 1}, "POKEMON_PARALYZED"),
                                    ({"confusion": True}, "POKEMON_CONFUSED")):
                with self.subTest(card=card, code=code):
                    state = board(mon(card, damage=10, **condition), bench=(mon(RATTATA, (), damage=20),), hand=(RATTATA,),
                                  opponent=mon(HITMONCHAN, (F, F), damage=20))
                    pid = pid_of(state, 0, card)
                    extra = {"source": pid_of(state, 0, RATTATA)} if card == SLOWBRO else {}
                    if card == GENGAR:
                        extra = {"source": pid_of(state, 1, HITMONCHAN), "target": pid_of(state, 1, RATTATA)}
                    assert_rejected(self, state, UsePokemonPower(0, pid, 0, **extra), code, IllegalActionError)
        poisoned = board(mon(VILEPLUME, poison=10), bench=(mon(RATTATA, (), damage=20),))
        self.assertEqual(power(poisoned, pid_of(poisoned, 0, VILEPLUME), H).decision.resume, "power")
        state = board(mon(ERIKAS_VILEPLUME))
        assert_rejected(self, state, UsePokemonPower(0, pid_of(state, 0, ERIKAS_VILEPLUME), 0), "POWER_NOT_DECLARABLE", IllegalActionError)

    def test_chemical_gas_suppresses_every_new_power(self):
        """かがくへんかガス（ベトベトン）がはたらいていると、宣言する特殊能力は ``POWER_SUPPRESSED``（コイン・決定の前）、ぼうぎょかふんははたらかない
        （コインもない）。"""
        for card in (VILEPLUME, SLOWBRO, GENGAR, DRAGONITE, ERIKAS_VICTREEBEL, DARK_KADABRA, TENTACOOL):
            with self.subTest(card=card):
                me = [mon(RATTATA, (), damage=20)]
                active = mon(card, damage=10)
                if card == DRAGONITE:
                    active, me = mon(RATTATA, (), damage=20), [mon(DRAGONITE)]
                state = board(active, opponent=mon(MUK, ()), bench=me, hand=(RATTATA,), opponent_bench=(mon(RATTATA, (), damage=20), BULBASAUR))
                pid = pid_of(state, 0, card)
                extra = {"source": pid_of(state, 0, RATTATA)} if card == SLOWBRO else {}
                if card == GENGAR:
                    extra = {"source": pid_of(state, 1, RATTATA), "target": pid_of(state, 1, BULBASAUR)}
                assert_rejected(self, state, UsePokemonPower(0, pid, 0, **extra), "POWER_SUPPRESSED", IllegalActionError)
        state = board(mon(HITMONCHAN, (F, F)), mon(ERIKAS_VILEPLUME), opponent_bench=(mon(MUK, ()),))
        done = attack(state, 0, H)
        self.assertFalse(events(done, len(state.log), "power_confusion") + [e for e in events(done, len(state.log), "coin_flip") if e["source"] == "power"])
        self.assertIsNone(done.players[0].active.conditions.exclusive)


class AfterPowerTest(unittest.TestCase):
    """特殊能力の処理のあと（きぜつ・サイド・勝ち負け・バトル場に出す）。ワザのあとと同じ解決の基盤の処理を使い、終わったら番のプレイヤーの番にもどる。"""

    def test_curse_knocks_out_a_bench_pokemon_then_the_turn_continues(self):
        """のろいで相手の控えのポケモンが HP 以上になると、きぜつの処理（ログ ``knock_out`` の ``timing`` が ``power``）→ サイドを取る決定（続きは
        ``continue_turn``）→ 番のプレイヤーの MAIN にもどり、ワザを使える。"""
        state = board(mon(GENGAR), mon(HITMONCHAN, (F, F), damage=20), opponent_bench=(mon(RATTATA, (), damage=20),))
        cursed = power(state, pid_of(state, 0, GENGAR), source=pid_of(state, 1, HITMONCHAN), target=pid_of(state, 1, RATTATA))
        ko = events(cursed, len(state.log), "knock_out")
        self.assertEqual([(e["timing"], cursed.cards[e["pokemon"]].card_id) for e in ko], [("power", RATTATA)])
        self.assertEqual((cursed.decision.kind, cursed.decision.player, cursed.decision.context_value("then")), (TAKE_PRIZE, 0, "continue_turn"))
        taken = answer(cursed, first(cursed.decision))
        self.assertEqual((taken.phase, taken.turn_number, taken.current_player, len(taken.players[0].prizes)), (Phase.MAIN, TURN, 0, 5))
        self.assertIn("attack", kinds(attack(taken, 0, H, H, H), len(taken.log)))

    def test_curse_knocks_out_the_active_and_the_opponent_promotes(self):
        """のろいで相手の対戦ポケモンがきぜつしたら、サイドのあと相手がバトル場に出し（続きは ``continue_turn``）、番のプレイヤーの番にもどる。"""
        state = board(mon(GENGAR), mon(HITMONCHAN, (F, F), damage=60), opponent_bench=(mon(RATTATA, (), damage=20), BULBASAUR))
        cursed = power(state, pid_of(state, 0, GENGAR), source=pid_of(state, 1, RATTATA), target=pid_of(state, 1, HITMONCHAN))
        taken = answer(cursed, first(cursed.decision))
        self.assertEqual((taken.decision.kind, taken.decision.player), (PROMOTE_ACTIVE, 1))
        promoted = answer(taken, first(taken.decision))
        self.assertEqual((promoted.phase, promoted.current_player, promoted.turn_number), (Phase.MAIN, 0, TURN))

    def test_curse_can_win_the_game(self):
        """のろいのきぜつで最後のサイドを取ったら、番のプレイヤーの勝ち。相手の場にポケモンがいなくなっても勝ち（p.311）。"""
        state = board(mon(GENGAR), mon(HITMONCHAN, (F, F), damage=60), opponent_bench=(mon(RATTATA, (), damage=20),), prizes=1)
        cursed = power(state, pid_of(state, 0, GENGAR), source=pid_of(state, 1, RATTATA), target=pid_of(state, 1, HITMONCHAN))
        done = answer(cursed, first(cursed.decision))
        self.assertEqual((done.phase, done.result.winner), (Phase.GAME_OVER, 0))

    def test_cowardice_from_the_active_promotes_without_a_prize(self):
        """おくびょうでバトル場のメノクラゲを手札にもどしたら（きぜつではない。サイドはない）、ベンチから出す決定（続きは ``continue_turn``）→ 番のプレイヤーの
        MAIN。控えがいなければ、場にポケモンがいなくなって負け（p.311）。"""
        state = board(mon(TENTACOOL, damage=10), bench=(RATTATA,))
        done = power(state, pid_of(state, 0, TENTACOOL))
        self.assertFalse(events(done, len(state.log), "knock_out") + events(done, len(state.log), "take_prize"))
        self.assertEqual((done.decision.kind, done.decision.player, done.decision.context_value("then")), (PROMOTE_ACTIVE, 0, "continue_turn"))
        promoted = answer(done, first(done.decision))
        self.assertEqual((promoted.phase, promoted.current_player), (Phase.MAIN, 0))
        self.assertEqual(len(promoted.players[0].prizes), 6)
        alone = board(mon(TENTACOOL), bench=())
        lost = power(alone, pid_of(alone, 0, TENTACOOL))
        self.assertEqual((lost.phase, lost.result.winner), (Phase.GAME_OVER, 1))

    def test_a_power_that_must_not_knock_out_is_caught_by_the_invariants(self):
        """きぜつさせない説明の特殊能力（へんなこうどう）の確認が壊れていても、使用後の処理はきぜつを処理せず、不変条件で止める（v0.7 の二重の確かめ）。"""
        from kyuura_engine import StateIntegrityError

        class Broken(E.MoveDamageCounterToSelf):
            def check_usable(self, state, use):
                pass

        entry = E.DEFAULT_EFFECTS.power_entry(SLOWBRO, 0)
        import dataclasses
        effects = E.DEFAULT_EFFECTS.with_powers("test-broken-strange", {E.PowerKey(SLOWBRO, 0): dataclasses.replace(entry, effect=Broken())})
        from kyuura_engine.cards import pool_from_extract
        state = build_test_state([{"active": mon(SLOWBRO, damage=50), "bench": [mon(RATTATA, (), damage=20)]},
                                  {"active": mon(HITMONCHAN, (F, F)), "bench": [RATTATA]}], turn_number=TURN, effects=effects,
                                 pool=pool_from_extract(read_extract(), effects))
        with self.assertRaises(StateIntegrityError):
            apply_kernel(state, UsePokemonPower(0, pid_of(state, 0, SLOWBRO), 0, source=pid_of(state, 0, RATTATA)))


# ---------------------------------------------------------------- 特殊能力ごと


class HealingTest(unittest.TestCase):
    """ラフレシアの［ヒーリング］。"""

    def test_heads_then_choose_and_remove_one(self):
        """コインを投げてから（「おもて」なら）、自分の場のダメージカウンターがのったポケモン（バトル場 → ベンチ。このカードも）を選び、1 つとりのぞく。"""
        state = board(mon(VILEPLUME, damage=10), bench=(mon(RATTATA, (), damage=20), BULBASAUR))
        vile = pid_of(state, 0, VILEPLUME)
        waiting = power(state, vile, H)
        self.assertEqual(kinds(waiting, len(state.log)), ["pokemon_power", "coin_flip"])
        self.assertEqual(waiting.decision.options, (vile, pid_of(state, 0, RATTATA)))
        done = answer(waiting, (pid_of(state, 0, RATTATA),))
        [heal] = events(done, len(waiting.log), "power_heal")
        self.assertEqual((heal["counters"], heal["user_pokemon_id"], pokemon_of(done, pid_of(state, 0, RATTATA)).damage), (1, vile, 10))
        tails = power(state, vile, T)
        self.assertEqual((tails.decision, kinds(tails, len(state.log))), (None, ["pokemon_power", "coin_flip"]))

    def test_hc8_without_any_counter(self):
        """自分の場のどのポケモンにもダメージカウンターがなければ、使えるか（使ったことになるか）は決められない（しぜんになおるの HC8 と同じ問い。コインの前に止める）。"""
        state = board(mon(VILEPLUME))
        assert_rejected(self, state, UsePokemonPower(0, pid_of(state, 0, VILEPLUME), 0), "UNRESOLVED_POWER_HEAL_WITHOUT_DAMAGE", UnsupportedError)

    def test_from_the_bench(self):
        state = board(mon(RATTATA, (), damage=20), bench=(mon(VILEPLUME),))
        done = answer(power(state, pid_of(state, 0, VILEPLUME), H), (state.players[0].active.pokemon_id,))
        self.assertEqual(done.players[0].active.damage, 10)


class StrangeBehaviorTest(unittest.TestCase):
    """ヤドランの［へんなこうどう］（ダメージスワップと同じ 1 個ずつの移動。ダメージではない）。"""

    def test_moves_one_counter_onto_itself(self):
        state = board(mon(SLOWBRO), bench=(mon(RATTATA, (), damage=20),))
        bro, rat = pid_of(state, 0, SLOWBRO), pid_of(state, 0, RATTATA)
        done = power(state, bro, source=rat)
        [move] = events(done, len(state.log), "move_damage_counter")
        self.assertEqual((move["from_pokemon_id"], move["to_pokemon_id"], move["count"]), (rat, bro, 1))
        self.assertFalse(events(done, len(state.log), "damage"))

    def test_rejections(self):
        """きぜつさせる移動（``WOULD_KNOCK_OUT``。「このカードが「きぜつ」しない範囲なら」）・自分自身から（``SAME_POKEMON``）・カウンターのない移動元・相手のポケモン・
        移動元の指定なし・移動先の指定は拒否する（状態は変わらない）。"""
        state = board(mon(SLOWBRO, damage=50), bench=(mon(RATTATA, (), damage=20), BULBASAUR))
        bro, rat, bulba = pid_of(state, 0, SLOWBRO), pid_of(state, 0, RATTATA), pid_of(state, 0, BULBASAUR)
        assert_rejected(self, state, UsePokemonPower(0, bro, 0, source=rat), "WOULD_KNOCK_OUT", IllegalActionError)
        assert_rejected(self, state, UsePokemonPower(0, bro, 0, source=bro), "SAME_POKEMON", IllegalActionError)
        assert_rejected(self, state, UsePokemonPower(0, bro, 0, source=bulba), "NO_DAMAGE_COUNTERS", IllegalActionError)
        assert_rejected(self, state, UsePokemonPower(0, bro, 0), "POWER_CHOICE_MISSING", IllegalActionError)
        assert_rejected(self, state, UsePokemonPower(0, bro, 0, source=rat, target=rat), "POWER_CHOICE_NOT_USED", IllegalActionError)
        assert_rejected(self, state, UsePokemonPower(0, bro, 0, source=state.players[1].active.pokemon_id), "SOURCE_NOT_YOURS", IllegalActionError)


class CurseTest(unittest.TestCase):
    """ゲンガーの［のろい］（相手の場のポケモンのあいだのダメージカウンターの移動。ダメージではない。説明に「きぜつ」しない範囲の条件はない）。"""

    def test_moves_without_damage_calculation_or_triggers(self):
        """ダメージの計算（弱点・抵抗力・ディフェンダー）をせず、「ダメージを受けたとき」の効果（はんげき）もはたらかない。"""
        state = board(mon(GENGAR), mon(MACHAMP, (F,)), opponent_bench=(mon(RATTATA, (), damage=20),))
        done = power(state, pid_of(state, 0, GENGAR), source=pid_of(state, 1, RATTATA), target=pid_of(state, 1, MACHAMP))
        self.assertEqual(kinds(done, len(state.log)), ["pokemon_power", "move_damage_counter"])
        [move] = events(done, len(state.log), "move_damage_counter")
        self.assertEqual(move["owner"], 1)
        self.assertEqual((done.players[1].active.damage, done.players[0].active.damage), (10, 0))

    def test_attack_only_protections_do_not_apply(self):
        """のろいは特殊能力の効果で、ワザの効果ではない。「ダメージを受けない」状態（かたまる）・「とうめい」は「ワザによって」受けるダメージ・効果だけを
        防ぐので、のろいでのせるカウンターは防がない（判定のコインもない）。かおりのわなで「とうめい」のポケモンを入れ替えるときも判定しない（防御を一律に
        当てはめない）。"""
        state = board(mon(GENGAR), mon(HITMONCHAN, (F, F), damage=20, prevent_damage=TURN - 1), opponent_bench=(mon(HAUNTER, ()),))
        done = power(state, pid_of(state, 0, GENGAR), source=pid_of(state, 1, HITMONCHAN), target=pid_of(state, 1, HAUNTER))
        self.assertEqual(kinds(done, len(state.log)), ["pokemon_power", "move_damage_counter"])
        self.assertEqual(pokemon_of(done, pid_of(state, 1, HAUNTER)).damage, 10)
        trap = board(mon(ERIKAS_VICTREEBEL), opponent_bench=(mon(HAUNTER, ()),))
        switched = answer(power(trap, pid_of(trap, 0, ERIKAS_VICTREEBEL), H), (pid_of(trap, 1, HAUNTER),))
        self.assertFalse(events(switched, len(trap.log), "evade_check"))
        self.assertEqual(switched.cards[switched.players[1].active.card].card_id, HAUNTER)

    def test_rejections(self):
        state = board(mon(GENGAR), mon(HITMONCHAN, (F, F), damage=20), opponent_bench=(RATTATA,))
        g, hit, rat = pid_of(state, 0, GENGAR), pid_of(state, 1, HITMONCHAN), pid_of(state, 1, RATTATA)
        assert_rejected(self, state, UsePokemonPower(0, g, 0, source=hit, target=hit), "SAME_POKEMON", IllegalActionError)
        assert_rejected(self, state, UsePokemonPower(0, g, 0, source=rat, target=hit), "NO_DAMAGE_COUNTERS", IllegalActionError)
        assert_rejected(self, state, UsePokemonPower(0, g, 0, source=hit, target=g), "TARGET_NOT_OPPONENTS", IllegalActionError)
        assert_rejected(self, state, UsePokemonPower(0, g, 0, source=hit), "POWER_CHOICE_MISSING", IllegalActionError)


class StepInTest(unittest.TestCase):
    """カイリューの［かけつける］（ベンチにいるときだけ。自分の番ごとに 1 回。にげるではない）。"""

    def test_switches_from_the_bench(self):
        """ポケモンいれかえと同じ入れ替え（にげるエネルギーを払わない・ベンチにもどったポケモンの特殊状態は消える）。ログ ``switch`` の ``effect`` は特殊能力。"""
        state = board(mon(RATTATA, (F,), confusion=True), bench=(mon(DRAGONITE),))
        dragon = pid_of(state, 0, DRAGONITE)
        done = power(state, dragon)
        self.assertEqual(done.players[0].active.pokemon_id, dragon)
        [switch] = events(done, len(state.log), "switch")
        self.assertEqual(switch["effect"], f"{DRAGONITE}@power0")
        self.assertIsNone(done.players[0].bench[0].conditions.exclusive)
        self.assertEqual(len(done.players[0].bench[0].energy), 1)
        assert_rejected(self, done, UsePokemonPower(0, dragon, 0), "POKEMON_NOT_ON_BENCH", IllegalActionError)

    def test_from_the_active_is_rejected(self):
        state = board(mon(DRAGONITE))
        assert_rejected(self, state, UsePokemonPower(0, pid_of(state, 0, DRAGONITE), 0), "POKEMON_NOT_ON_BENCH", IllegalActionError)


class SweetTrapTest(unittest.TestCase):
    """エリカのウツボットの［かおりのわな］。"""

    def test_heads_then_the_user_chooses(self):
        """コインの「おもて」で、使ったプレイヤーが相手の控えを選び、相手の対戦ポケモンと入れ替える（「うら」は何もしない）。隣の止まらない場合: 控えが 1 匹。"""
        state = board(mon(ERIKAS_VICTREEBEL), opponent_bench=(RATTATA,))
        waiting = power(state, pid_of(state, 0, ERIKAS_VICTREEBEL), H)
        d = waiting.decision
        self.assertEqual((d.kind, d.player, d.options), (SELECT_POKEMON, 0, (pid_of(state, 1, RATTATA),)))
        done = answer(waiting, d.options)
        self.assertEqual(done.cards[done.players[1].active.card].card_id, RATTATA)
        self.assertEqual(events(done, len(waiting.log), "switch")[0]["effect"], f"{ERIKAS_VICTREEBEL}@power0")
        tails = power(state, pid_of(state, 0, ERIKAS_VICTREEBEL), T)
        self.assertIsNone(tails.decision)

    def test_pw1_without_an_opponent_bench(self):
        """相手に控えがいないときに使えるか（コインを投げるか・使ったことになるか）は決められない（PW1。コインの前に止める）。"""
        state = board(mon(ERIKAS_VICTREEBEL), opponent_bench=())
        assert_rejected(self, state, UsePokemonPower(0, pid_of(state, 0, ERIKAS_VICTREEBEL), 0), "UNRESOLVED_POWER_SWITCH_WITHOUT_OPPONENT_BENCH",
                        UnsupportedError)

    def test_sg1_choice_is_held(self):
        """すごむの効果を与えたポケモン（相手の控え）を選んでバトル場にもどす答えは SG1（選べるが選ぶと止める）。それしか選べなければ、コインの前に止める。"""
        lock = board(mon(GIOVANNIS_NIDOKING, (G, G, G)), mon(RATTATA, (F,)), bench=(RATTATA, BULBASAUR),
                     opponent_bench=(mon(ERIKAS_VICTREEBEL),), opponent_hand=(GUST,))
        done = attack(lock, 0)
        gusted = play(done, PlayTrainer(1, card_of(done, 1, GUST)), [first])
        trap = pid_of(gusted, 1, ERIKAS_VICTREEBEL)
        king = pid_of(gusted, 0, GIOVANNIS_NIDOKING)
        waiting = power(gusted, trap, H, player=1)
        self.assertEqual(waiting.decision.context_value("unresolved_choices"), (king,))
        assert_rejected(self, waiting, ResolveDecision(1, waiting.decision.id, (king,)), "UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED", UnsupportedError)


class MatterExchangeTest(unittest.TestCase):
    """わるいユンゲラーの［ぶっしつこうかん］。"""

    def test_discard_then_draw(self):
        """手札から 1 枚選んでトラッシュ（決定。ログ ``discard_from_hand`` の ``power``）→ 山札から 1 枚引く。隣の止まらない場合: 手札が 1 枚。山札が 0 枚なら引けない
        （負けではない）。"""
        state = board(mon(DARK_KADABRA), hand=(RATTATA,), deck=(GRASS, WATER))
        waiting = power(state, pid_of(state, 0, DARK_KADABRA))
        d = waiting.decision
        self.assertEqual((d.kind, d.resume, d.options), (DISCARD_FROM_HAND, "power", tuple(state.players[0].hand)))
        done = answer(waiting, d.options)
        self.assertEqual(kinds(done, len(waiting.log)), ["discard_from_hand", "draw"])
        self.assertEqual(events(done, len(waiting.log), "discard_from_hand")[0]["power"], f"{DARK_KADABRA}@power0")
        self.assertEqual([done.cards[u].card_id for u in done.players[0].hand], [GRASS])
        self.assertEqual(card_count(done, 0), card_count(state, 0))
        empty = board(mon(DARK_KADABRA), hand=(RATTATA,), deck=())
        drawn = answer(power(empty, pid_of(empty, 0, DARK_KADABRA)), (card_of(empty, 0, RATTATA),))
        self.assertEqual((drawn.phase, events(drawn, len(empty.log), "draw")[0]["cards"]), (Phase.MAIN, ()))

    def test_pw2_without_a_hand(self):
        state = board(mon(DARK_KADABRA), hand=())
        assert_rejected(self, state, UsePokemonPower(0, pid_of(state, 0, DARK_KADABRA), 0), "UNRESOLVED_POWER_DISCARD_WITHOUT_HAND", UnsupportedError)


class CowardiceTest(unittest.TestCase):
    """メノクラゲの［おくびょう］（自分を手札にもどす。きぜつではない）。"""

    def test_returns_with_counters_removed_and_attached_cards_discarded(self):
        state = board(mon(RATTATA, (F,)), bench=(mon(TENTACOOL, (W,), damage=20),))
        cool = pid_of(state, 0, TENTACOOL)
        done = power(state, cool)
        self.assertEqual(kinds(done, len(state.log)), ["pokemon_power", "remove_all_damage_counters", "discard_attached_cards", "return_in_play_to_hand"])
        self.assertIn(TENTACOOL, [done.cards[u].card_id for u in done.players[0].hand])
        self.assertIn(WATER, [done.cards[u].card_id for u in done.players[0].discard])
        self.assertEqual(card_count(done, 0), card_count(state, 0))
        self.assertEqual(len(done.players[0].prizes), len(state.players[1].prizes))

    def test_not_on_the_turn_it_was_played(self):
        state = board(mon(RATTATA, (F,)), bench=(mon(TENTACOOL, played_turn=TURN),))
        assert_rejected(self, state, UsePokemonPower(0, pid_of(state, 0, TENTACOOL), 0), "PLAYED_THIS_TURN", IllegalActionError)


class DefensivePollenTest(unittest.TestCase):
    """エリカのラフレシアの［ぼうぎょかふん］（バトル場で相手のワザのダメージを受けたときに自動的にはたらく）。"""

    def test_heads_confuses_the_attacker(self):
        """持ち主がコインを投げ（``source`` は ``power``）、「おもて」ならワザを使ったポケモンをこんらんにする。「うら」なら何もしない。"""
        state = board(mon(HITMONCHAN, (F, F)), mon(ERIKAS_VILEPLUME))
        heads = attack(state, 0, H)
        [result] = events(heads, len(state.log), "power_confusion")
        self.assertEqual((result["player"], result["confused"]), (1, True))
        self.assertTrue(heads.players[0].active.conditions.confused)
        tails = attack(state, 0, T)
        self.assertFalse(tails.players[0].active.conditions.confused)

    def test_works_while_asleep_and_even_when_knocked_out(self):
        """ねむり・マヒ・こんらんでも必ずはたらき、このカードが「きぜつ」しても（ダメージで HP 以上）はたらく。"""
        for condition in ({"sleep": True}, {"paralysis": TURN - 1}, {"confusion": True}):
            with self.subTest(condition=condition):
                state = board(mon(HITMONCHAN, (F, F)), mon(ERIKAS_VILEPLUME, **condition))
                done = attack(state, 0, H)
                self.assertTrue(done.players[0].active.conditions.confused)
        state = board(mon(HITMONCHAN, (F, F)), mon(ERIKAS_VILEPLUME, damage=70), opponent_bench=(RATTATA,))
        done = attack(state, 0, H)
        self.assertTrue(events(done, len(state.log), "power_confusion"))
        self.assertTrue(events(done, len(state.log), "knock_out"))

    def test_not_on_the_bench_or_without_damage(self):
        """ベンチで受けたダメージ（ナイトヘッドの控えへのダメージ）・ダメージが 0（受けない）ではたらかない。どく・カウンターをのせる効果（ライフダウン）でも
        はたらかない（ワザのダメージではない）。"""
        state = board(mon(GENGAR), mon(HITMONCHAN, (F, F)), opponent_bench=(mon(ERIKAS_VILEPLUME),))
        done = attack(state, 0, answers=[first])
        self.assertFalse(events(done, len(state.log), "power_confusion"))
        state = board(mon(SABRINAS_KADABRA), mon(ERIKAS_VILEPLUME))
        done = attack(state, 0, H)
        self.assertTrue(events(done, len(state.log), "place_damage_counters"))
        self.assertFalse(events(done, len(state.log), "power_confusion"))

    def test_after_damage_before_the_effect_coin(self):
        """ダメージの処理のあと・ダメージ以外の効果（それを決めるコイン）の前（CR-COUNTERATTACK-TIMING。はんげきと同じ窓）。"""
        state = board(mon(SABRINAS_JYNX), mon(ERIKAS_VILEPLUME))
        done = attack(state, 1, H, H)
        order = [k for k in kinds(done, len(state.log)) if k in ("damage", "power_confusion", "persistent_effect_added")]
        self.assertEqual(order, ["damage", "power_confusion", "persistent_effect_added"])


# ---------------------------------------------------------------- ワザ


class AttackTest(unittest.TestCase):
    def test_good_deed(self):
        """よいおこない: 相手のポケモンを選び → とりのぞく数（1〜のっている数。0 は HC5 と同じ問いで止める）→ とりのぞいた数ぶん引く。"""
        state = board(mon(SABRINAS_JYNX), mon(HITMONCHAN, (F, F), damage=30), deck=(GRASS, WATER, FIRE))
        waiting = attack(state, 0)
        self.assertEqual((waiting.decision.kind, waiting.decision.player), (SELECT_POKEMON, 0))
        count = answer(waiting, (pid_of(state, 1, HITMONCHAN),))
        self.assertEqual((count.decision.kind, count.decision.options), (REMOVE_COUNTERS, (0, 1, 2, 3)))
        assert_rejected(self, count, ResolveDecision(0, count.decision.id, (0,)), "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO", UnsupportedError)
        done = answer(count, (2,))
        self.assertEqual((done.players[1].active.damage, len(events(done, len(count.log), "draw")[0]["cards"])), (10, 2))
        none = board(mon(SABRINAS_JYNX), deck=(GRASS,))
        self.assertIsNone(attack(none, 0).decision)

    def test_petal_dance_confuses_itself(self):
        state = board(mon(VILEPLUME))
        done = attack(state, 0, H, T, T)
        self.assertEqual(done.players[1].active.damage, 40)
        self.assertTrue(done.players[0].active.conditions.confused)

    def test_energy_loop_returns_to_hand_before_damage(self):
        """エネループ: ついている「超」エネルギーカードを手札にもどしてからダメージ。こんらん状態では時点が決められないので HC1 で止める。"""
        state = board(mon(SABRINAS_ABRA))
        waiting = attack(state, 0)
        self.assertEqual(waiting.decision.kind, RETURN_ENERGY)
        done = answer(waiting, first(waiting.decision))
        order = [k for k in kinds(done, len(state.log)) if k in ("return_energy_to_hand", "damage")]
        self.assertEqual(order, ["return_energy_to_hand", "damage"])
        self.assertIn(PSYCHIC, [done.cards[u].card_id for u in done.players[0].hand])
        assert_stops(self, board(mon(SABRINAS_ABRA, confusion=True)), UseAttack(0, 0), "UNRESOLVED_DISCARD_ENERGY_TIMING")

    def test_life_drain_places_counters(self):
        """ライフダウン: 「おもて」なら残り HP 10 になるまでカウンターをのせる（ダメージではない。ディフェンダー・弱点を計算しない）。すでに残り 10 ならのせない。"""
        state = board(mon(SABRINAS_KADABRA), mon(HITMONCHAN, (F, F), damage=20))
        done = attack(state, 0, H)
        self.assertEqual(done.players[1].active.damage, 60)
        self.assertFalse(events(done, len(state.log), "damage"))
        at10 = board(mon(SABRINAS_KADABRA), mon(HITMONCHAN, (F, F), damage=60))
        self.assertFalse(events(attack(at10, 0, H), len(at10.log), "place_damage_counters"))

    def test_mind_shock_ignores_weakness_and_resistance_only(self):
        state = board(mon(DARK_ALAKAZAM), mon(MEWTWO, (P, P, P)))
        done = attack(state, 1)
        self.assertEqual(done.players[1].active.damage, 40)

    def test_teleport_blast_optional_switch(self):
        """テレポートブラスト: ダメージを与えた後、のぞむなら控えと入れ替える（0 匹を選ぶと入れ替えない）。ダメージを与えなかった場合は Z23。"""
        state = board(mon(DARK_ALAKAZAM), bench=(RATTATA,))
        waiting = attack(state, 0)
        self.assertEqual((waiting.decision.min_choices, waiting.decision.max_choices), (0, 1))
        declined = answer(waiting, ())
        self.assertIn("switch_declined", kinds(declined, len(waiting.log)))
        switched = answer(waiting, first(waiting.decision))
        self.assertEqual(switched.cards[switched.players[0].active.card].card_id, RATTATA)

    def test_moon_power_evolves_from_the_deck(self):
        """つきのちから: 「おもて」なら山札の進化カードを選び、重ねるポケモンが 2 匹以上なら選び、進化させて山札を切る（ワザを使ったポケモン自身も選べる）。
        進化の制限は通常の進化と同じ（この番に場に出したポケモンは選べない）。重ねられるものがなければ何もせず切る。"""
        state = board(mon(ERIKAS_CLEFAIRY), bench=(mon(ERIKAS_CLEFAIRY, ()), mon(ERIKAS_CLEFAIRY, (), played_turn=TURN)), deck=(ERIKAS_CLEFABLE, GRASS))
        waiting = attack(state, 0, H)
        self.assertEqual(waiting.decision.kind, SEARCH_DECK)
        target = answer(waiting, first(waiting.decision))
        self.assertEqual(target.decision.options, (state.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id))
        done = answer(target, (state.players[0].active.pokemon_id,))
        [evolve] = events(done, len(target.log), "evolve")
        self.assertEqual((evolve["source_zone"], evolve["effect"]), ("deck", f"{ERIKAS_CLEFAIRY}#0"))
        after = kinds(done, len(target.log))
        self.assertEqual(after[after.index("turn_end") - 1], "shuffle")
        self.assertEqual(card_count(done, 0), card_count(state, 0))
        none = board(mon(ERIKAS_CLEFAIRY), bench=(), deck=(GRASS,))
        after = kinds(attack(none, 0, H), len(none.log))
        self.assertEqual(after[after.index("turn_end") - 2:after.index("turn_end")], ["evolve_from_deck_none", "shuffle"])

    def test_fairy_miracle_returns_to_hand(self):
        """ようせいのきせき: 「おもて」なら自分のポケモンを好きなだけ（1 匹以上。0 匹は HC5 と同じ問い）選び、重なったカード・ついているカードとともに手札にもどす
        （きぜつではない。サイドはない）。バトル場をもどしたら控えから出す。すべてもどしたら負け。"""
        state = board(mon(ERIKAS_CLEFABLE), bench=(mon(RATTATA, (F,), damage=10),))
        waiting = attack(state, 0, H)
        assert_rejected(self, waiting, ResolveDecision(0, waiting.decision.id, ()), "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO", UnsupportedError)
        bench_only = answer(waiting, (pid_of(state, 0, RATTATA),))
        self.assertIn(RATTATA, [bench_only.cards[u].card_id for u in bench_only.players[0].hand])
        self.assertFalse(events(bench_only, len(waiting.log), "take_prize"))
        self.assertEqual(card_count(bench_only, 0), card_count(state, 0))
        all_of_them = answer(waiting, waiting.decision.options)
        self.assertEqual((all_of_them.phase, all_of_them.result.winner), (Phase.GAME_OVER, 1))
        itself = answer(waiting, (state.players[0].active.pokemon_id,))
        self.assertEqual((itself.decision.kind, itself.decision.player), (PROMOTE_ACTIVE, 0))

    def test_hug_and_jellyfish(self):
        hug = attack(board(mon(SABRINAS_JYNX)), 1, H)
        self.assertTrue(events(hug, 0, "persistent_effect_added"))
        jelly = attack(board(mon(TENTACRUEL)), 1)
        self.assertIsNotNone(jelly.players[1].active.conditions.poison)


# ---------------------------------------------------------------- 整合性


class IntegrityTest(unittest.TestCase):
    """不変条件・書き出し・ログの監査・渡した状態を変えないこと・先読みの方法によらないこと（ワザ）。"""

    CASES = (
        (SABRINAS_JYNX, 0, (), (first, lambda d: (1,))), (SABRINAS_JYNX, 1, (H,), ()), (VILEPLUME, 0, (H, T, H), ()), (SLOWBRO, 0, (H,), ()),
        (GENGAR, 0, (), (first,)), (ERIKAS_VILEPLUME, 0, (), ()), (SABRINAS_ABRA, 0, (), (first,)), (SABRINAS_KADABRA, 0, (H,), ()),
        (SABRINAS_KADABRA, 1, (), ()), (DRAGONITE, 0, (H, T), ()), (ERIKAS_VICTREEBEL, 0, (), ()), (DARK_KADABRA, 0, (), ()),
        (DARK_ALAKAZAM, 0, (), (first,)), (DARK_ALAKAZAM, 1, (), ()), (TENTACOOL, 0, (), ()), (TENTACRUEL, 0, (H,), ()), (TENTACRUEL, 1, (), ()),
        (ERIKAS_CLEFAIRY, 0, (T,), ()), (ERIKAS_CLEFAIRY, 1, (), ()), (ERIKAS_CLEFABLE, 0, (H,), (first,)), (ERIKAS_CLEFABLE, 1, (), ()),
    )

    def state(self, card):
        return board(mon(card, damage=10), mon(HITMONCHAN, (F, F), damage=20), bench=(mon(RATTATA, damage=10), BULBASAUR),
                     opponent_bench=(mon(RATTATA, damage=10), BULBASAUR), deck=(PSYCHIC, FIRE, PSYCHIC, RATTATA))

    def test_cases_cover_every_attack(self):
        self.assertEqual(sorted((card, index) for card, index, _, _ in self.CASES), sorted(EXPECTED))

    def test_every_step_keeps_invariants_and_does_not_mutate_the_input(self):
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
                self.assertEqual(card_count(current, 0) + card_count(current, 1), card_count(state, 0) + card_count(state, 1))

    def test_same_result_in_every_preflight_mode(self):
        for card, index, sides, answers in self.CASES:
            with self.subTest(card=card, index=index):
                state = self.state(card)
                results = {repr(snapshot(play(with_coin_results(state, *sides), UseAttack(0, index), answers, mode=mode))) for mode in PREFLIGHT_MODES}
                self.assertEqual(len(results), 1)

    def test_powers_keep_invariants_and_do_not_mutate_the_input(self):
        """特殊能力の宣言・決定への答えのどの段階でも不変条件が通り、渡した状態を変えない。カードの枚数は変わらない。"""
        cases = (
            (board(mon(VILEPLUME), bench=(mon(RATTATA, (), damage=20),)), VILEPLUME, {}, (H,), (first,)),
            (board(mon(SLOWBRO), bench=(mon(RATTATA, (), damage=20),)), SLOWBRO, {"source": RATTATA}, (), ()),
            (board(mon(GENGAR), mon(HITMONCHAN, (F, F), damage=20), opponent_bench=(mon(RATTATA, (), damage=20),)), GENGAR,
             {"source": HITMONCHAN, "target": RATTATA}, (), (first,)),
            (board(mon(RATTATA, (F,)), bench=(mon(DRAGONITE),)), DRAGONITE, {}, (), ()),
            (board(mon(ERIKAS_VICTREEBEL)), ERIKAS_VICTREEBEL, {}, (H,), (first,)),
            (board(mon(DARK_KADABRA), hand=(RATTATA,), deck=(GRASS,)), DARK_KADABRA, {}, (), (first,)),
            (board(mon(TENTACOOL, damage=10), bench=(RATTATA,)), TENTACOOL, {}, (), (first,)),
        )
        for state, card, choices, sides, answers in cases:
            with self.subTest(card=card):
                extra = {}
                if "source" in choices:
                    extra["source"] = pid_of(state, 1 if card == GENGAR else 0, choices["source"])
                if "target" in choices:
                    extra["target"] = pid_of(state, 1, choices["target"])
                before = copy.deepcopy(full(state))
                current = power(state, pid_of(state, 0, card), *sides, **extra)
                self.assertEqual(full(state), before)
                for answer_of in answers:
                    self.assertEqual(check_invariants(current), [])
                    d = current.decision
                    current = apply_kernel(current, ResolveDecision(d.player, d.id, answer_of(d)))
                self.assertEqual(check_invariants(current), [])
                self.assertEqual(card_count(current, 0) + card_count(current, 1), card_count(state, 0) + card_count(state, 1))


class CopyTest(unittest.TestCase):
    """相手のワザを自分のワザとして使う効果（ピクシー・ピッピの「ゆびをふる」・カスミのコダックの「ちょうのうりょく」）での v0.42 のワザ。"""

    COPIERS = {CLEFABLE: ((P,), 0, ()), CLEFAIRY: ((P, P, P), 1, ()), MISTYS_PSYDUCK: ((P,), 0, (H, H, H))}

    def test_every_attack_can_be_copied_without_internal_errors(self):
        """21 のワザのどれをまねても、エンジンの内部のエラーにならない（処理するか、決まったコードで拒否する）。"""
        for (card, index) in EXPECTED:
            for copier, (energy, attack_index, sides) in self.COPIERS.items():
                with self.subTest(card=card, index=index, copier=copier):
                    state = board(mon(copier, energy, damage=20), mon(card, ()), bench=(mon(RATTATA, damage=10),), opponent_bench=(RATTATA, BULBASAUR),
                                  deck=(PSYCHIC, FIRE, RATTATA, ERIKAS_CLEFABLE))
                    try:
                        current = play(with_coin_results(state, *sides, H, H, H, H), UseAttack(0, attack_index), [])
                        if current.decision is not None and current.decision.kind == "select_attack":
                            self.assertIn(index, current.decision.options)
                            current = apply_kernel(current, ResolveDecision(0, current.decision.id, (index,)))
                        while current.decision is not None and current.decision.resume == "attack":
                            d = current.decision
                            choice = first(d) if d.options[:1] != (0,) or d.kind != REMOVE_COUNTERS else (1,)
                            current = apply_kernel(current, ResolveDecision(d.player, d.id, choice))
                    except EngineError as error:
                        self.assertTrue(error.code.startswith(("UNRESOLVED_", "UNSUPPORTED_")), error.code)
                        continue
                    self.assertEqual(check_invariants(current), [])


class DocumentTest(unittest.TestCase):
    def test_document_records_the_decisions(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("PW1", "PW2", "UNRESOLVED_POWER_SWITCH_WITHOUT_OPPONENT_BENCH", "UNRESOLVED_POWER_DISCARD_WITHOUT_HAND", "HC8", "HC5", "HC1", "Z23", "SG1",
                       "continue_turn", "power_uses_this_turn", "may_knock_out", "GR-2000-P320-COUNTER-MOVE", "CR-COUNTERATTACK-TIMING", "pcg-search.com",
                       "ヒーリング", "へんなこうどう", "のろい", "ぼうぎょかふん", "かけつける", "かおりのわな", "ぶっしつこうかん", "おくびょう",
                       "よいおこない", "エネループ", "ライフダウン", "テレポートブラスト", "つきのちから", "ようせいのきせき", "card_differences"):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
