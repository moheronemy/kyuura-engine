"""v0.57: スタジアム 14 枚と、その共通の処理（docs/stadiums-v0.57.md）。

14 枚: ニビシティジム（PMCG5-079）・ハナダシティジム（PMCG5-080）・抵抗力低下ジム（PMCG5-091）・ロケット団の特訓ジム（PMCG5-095）・グレンタウンジム（PMCG6-085）・
タマムシシティジム（PMCG5-078）・セキチクシティジム（PMCG6-086）・ヤマブキシティジム（PMCG6-090）・せまいジム（PMCG5-070）・ロケット団の爆発ジム（PMCG6-092）・
トキワシティジム（PMCG6-097）・クチバシティジム（PMCG5-076）・リムーブ禁止ジム（PMCG5-094）・錯乱ジム（PMCG5-087）。
どれも kyuura データの採用（処理に使う文面は kyuura の印刷の文面。採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合（違いはどれも処理に
影響しない）。スタジアムの一般の扱いは kyuura の rule_differences の「stadium」の 2000.02.14 版の行・GR-2000-P312-FIELD・GR-2000-P321-DAMAGE-ORDER（6 段階）。
2003 年の「スタジアムは 1 番に 1 枚」（MIX-ADV-RULES-2003）は持ち込まない。ガイドブックは読んでいない。英語版の文面・のちの規定で日本語版の条件を補わない。

新しい停止コード: STB1・TG1・FG1・FG2・EX1・VG1・VM1・CH1。
"""

from __future__ import annotations

import json
import pathlib
import unittest

from kyuura_engine import (
    EndTurn,
    EvolvePokemon,
    IllegalActionError,
    PlayBasicToBench,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UnsupportedError,
    UseAttack,
    UseStadium,
    check_invariants,
    command_from_dict,
    command_to_dict,
    observe,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    ACCEPT_REQUEST,
    DISCARD_FROM_HAND,
    EVOLUTION_HEAL,
    SELECT_POKEMON,
    STADIUM_RETURN_BENCH,
)
from kyuura_engine.effects import resistance_of, retreat_cost
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.stadiums import bench_limit
from tests.helpers import (
    BLAINES_CHARMANDER,
    BLAINES_DODUO,
    BROCKS_GEODUDE,
    CELADON_CITY_GYM,
    CERULEAN_CITY_GYM,
    CHAOS_GYM,
    CHARMANDER,
    CINNABAR_CITY_GYM,
    ENERGY_REMOVAL,
    ERIKAS_ODDISH,
    FIGHTING,
    FUCHSIA_CITY_GYM,
    GIOVANNIS_GYARADOS,
    GIOVANNIS_MAGIKARP,
    GRASS,
    HITMONCHAN,
    INVISIBLE_WALL,
    KOGA_TRAINER,
    KOGAS_KOFFING,
    LT_SURGES_RATTATA,
    MISTYS_SEEL,
    NARROW_GYM,
    NO_REMOVAL_GYM,
    PEWTER_CITY_GYM,
    PLUSPOWER,
    POTION,
    PSYCHIC,
    RATTATA,
    RESISTANCE_GYM,
    ROCKETS_EXPERIMENT,
    ROCKETS_MINEFIELD_GYM,
    ROCKETS_TRAINING_GYM,
    SABRINAS_ABRA,
    SAFFRON_CITY_GYM,
    V0_57_CARDS,
    VERMILION_CITY_GYM,
    VIRIDIAN_CITY_GYM,
    WATER,
    apply_kernel,
    with_coin_results,
)
from tests.log_audit import LATEST_FORMAT, observation_problems, serialization_problems
from tests.test_instant_trainers_v0_55 import answer, board, card_of, mon, use

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "stadiums-v0.57.md"
H, T = CoinSide.HEADS, CoinSide.TAILS
F, W, G, P = FIGHTING, WATER, GRASS, PSYCHIC
NEW_CODES = {
    "STB1": "UNRESOLVED_STADIUM_ACTIVATION_UNDER_TRAINER_BAN",
    "TG1": "UNRESOLVED_CELADON_GYM_WITHOUT_CONDITION",
    "FG1": "UNRESOLVED_FUCHSIA_GYM_AFTER_REPLACEMENT",
    "FG2": "UNRESOLVED_FUCHSIA_GYM_WITHOUT_TARGET",
    "EX1": "UNRESOLVED_MINEFIELD_DAMAGE_RECEIVED_POWER",
    "VG1": "UNRESOLVED_VIRIDIAN_GYM_ONE_COUNTER",
    "VM1": "UNRESOLVED_VERMILION_GYM_ATTACK_ORDER",
    "CH1": "UNRESOLVED_CHAOS_GYM_BORROWED_TURN",
}


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def snapshot(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log], repr(state.rng.getstate())


def assert_stops(test, state, command, code, error=UnsupportedError):
    before = snapshot(state)
    with test.assertRaises(error) as caught:
        apply_kernel(state, command)
    test.assertEqual(caught.exception.code, code)
    test.assertEqual(snapshot(state), before)  # 状態・ログ・乱数は変わらない


def placed(stadium, hand=(), **kw):
    """スタジアムを場に出した（プレイヤー 0 の番）盤面。"""
    state = use(board([stadium, *hand], **kw), stadium)
    assert state.stadium is not None and state.decision is None, state.decision
    return state


def last(state, kind):
    return [e for e in state.log if e["kind"] == kind][-1]


def damage_of(state, kind="damage"):
    return [e for e in state.log if e["kind"] == kind]


class CardDataTest(unittest.TestCase):
    def test_registered_and_classified(self):
        """14 枚とも、写しの組 pool_v0_57 にあり、スタジアムだけの種類のトレーナーとして登録した（分類に問題がない）。"""
        extract = json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text(encoding="utf-8"))
        self.assertEqual(tuple(extract["pool_v0_57"]), V0_57_CARDS)
        pool = load_card_pool()
        for card_id in V0_57_CARDS:
            with self.subTest(card=card_id):
                definition = pool.get(card_id)
                self.assertEqual(definition.trainer_kinds, ("stadium",))
                self.assertIn(card_id, pool.playable_ids)
                self.assertIsNone(E.DEFAULT_EFFECTS.trainer_problem(definition))
                effect = E.DEFAULT_EFFECTS.trainer_effect(definition)
                self.assertTrue(effect.is_stadium)
                self.assertEqual(effect.check(definition), [])
        self.assertEqual(len(E.DEFAULT_EFFECTS.trainer_ids()), 90)  # v0.65 で変わり身の術を加えた。v0.63 で 4 枚を加えた。 v0.58 でナツメのサイキックコントロールを加えて 81、v0.59 でカツラ・タケシの保護・まきちらせ!ベトベトガスを加えて 84、v0.61 でバトル場は穴だらけ!を加えた

    def test_adoption_records_and_external_checks(self):
        """採用の記録（kyuura_data）と pcg-search.com の照合。違いはどれも処理に影響しない（スタジアムの出し方とトラッシュの文の有無・1枚と1匹・別のとこのカード以外）。"""
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        for card_id in V0_57_CARDS:
            with self.subTest(card=card_id):
                record = sources[card_id]
                self.assertEqual((record["basis"], record["status"], record["kyuura_records"]), ("kyuura_data", "adopted", []))
                check = record["external_checks"][0]
                self.assertEqual(check["site"], "pcg-search.com")
                self.assertIn(check["result"], ("match", "differences"))
                self.assertTrue(all(not d["affects_behavior"] for d in check["differences"]))

    def test_research_links(self):
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (141, 143))  # v0.58 で 6 件を加えた、v0.59 で GG1・BL1・CB1・BZ1〜BZ4 を加えた。v0.60 で TS1 を加え、コードのない SS1 を数えた。v0.61 で SH1・SC1・SC2・TD1 を加え、Z9 に停止コードを付けた。v0.62 で MM1・MM2・OM1・OM2 を加え、コードのない ED1 を数えた。v0.63 で QZ1 を加えた  # v0.65 で NT1〜NT3・RX1・FL1・BG1・BG2・KD1 を加えた
        for ruling, code in NEW_CODES.items():
            with self.subTest(code=code):
                entry = links["stop_codes"][code]
                self.assertEqual(entry["kyuura_disposition"], "not_in_kyuura")
                self.assertEqual(entry["engine_rulings"], [{"version": "v0.57", "document": "docs/stadiums-v0.57.md", "ruling_id": ruling}])

    def test_doc_names_every_new_code(self):
        text = DOC.read_text(encoding="utf-8")
        for ruling, code in NEW_CODES.items():
            self.assertIn(ruling, text)
            self.assertIn(code, text)


class PlacementTest(unittest.TestCase):
    """スタジアムは 1 枚。手札から使うと場に出し（トラッシュしない）、新しいスタジアムが場に出たら古いものを持ち主のトラッシュにすてる。"""

    def test_place_and_replace_by_opponent(self):
        state = placed(PEWTER_CITY_GYM, opponent_hand=[CHAOS_GYM])
        pewter = state.stadium.card
        self.assertEqual((state.stadium.owner, state.stadium.placed_turn), (0, state.turn_number))
        self.assertNotIn(pewter, state.players[0].discard)
        audited(self, state)
        state = apply_kernel(state, EndTurn(0))
        state = use(state, CHAOS_GYM, player=1)
        self.assertEqual(state.stadium.owner, 1)
        self.assertIn(pewter, state.players[0].discard)  # 持ち主（プレイヤー 0）のトラッシュ
        self.assertEqual([e["kind"] for e in state.log[-3:]], ["play_trainer", "stadium_placed", "stadium_discarded"])
        self.assertEqual(last(state, "stadium_discarded")["by_card"], state.stadium.card)
        audited(self, state)

    def test_same_name_and_same_turn_are_not_limited(self):
        """2000.02.14 版には「1 番に 1 枚」・同じ名前の禁止はない（2003 年の規定は持ち込まない）。同じ番に同じ名前のスタジアムを出すと入れかわる。"""
        state = board([PEWTER_CITY_GYM, PEWTER_CITY_GYM, CERULEAN_CITY_GYM])
        first = state.players[0].hand[0]
        state = apply_kernel(state, PlayTrainer(0, first))
        state = use(state, PEWTER_CITY_GYM)
        self.assertIn(first, state.players[0].discard)
        state = use(state, CERULEAN_CITY_GYM)
        self.assertEqual(state.cards[state.stadium.card].card_id, CERULEAN_CITY_GYM)
        audited(self, state)

    def test_trainer_lock_blocks_playing(self):
        state = board([PEWTER_CITY_GYM, ROCKETS_EXPERIMENT], deck=[G] * 5)
        state = use(state, ROCKETS_EXPERIMENT, coins=(T,))  # 「うら」: 使ったプレイヤー自身にトレーナーの使用の禁止
        with self.assertRaises(IllegalActionError) as caught:
            apply_kernel(state, PlayTrainer(0, card_of(state, PEWTER_CITY_GYM)))
        self.assertEqual(caught.exception.code, "TRAINER_PREVENTED")

    def test_format_17_observation_and_command_dict(self):
        state = placed(NARROW_GYM)
        self.assertEqual((max(FORMAT_VERSIONS), LATEST_FORMAT), (21, 21))  # v0.63 で形式 21。 v0.58 で形式 18、v0.59 で形式 19 を加えた
        data = state_to_dict(state, format_version=17)
        self.assertEqual(data["stadium"]["card_id"], NARROW_GYM)
        for version in range(1, 17):
            with self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)
        for viewer in (0, 1, None):
            self.assertEqual(observe(state, viewer)["stadium"]["card_id"], NARROW_GYM)
        plain = board([POTION])  # スタジアムがなければ、形式 16 は形式 17 から stadium・stadium_uses_this_turn を除いたもの
        self.assertEqual(state_to_dict(plain, format_version=16),
                         {k: v for k, v in state_to_dict(plain, format_version=17).items()
                          if k not in ("stadium", "stadium_uses_this_turn", "format_version")} | {"format_version": 16})
        attack = UseAttack(0, 1, stadium_coin=True)
        self.assertEqual(command_from_dict(command_to_dict(attack)), attack)
        self.assertNotIn("stadium_coin", command_to_dict(UseAttack(0, 1)))  # v0.56 までと同じ形
        self.assertEqual(command_from_dict(command_to_dict(UseStadium(0, 7))), UseStadium(0, 7))


class ContinuousTest(unittest.TestCase):
    def test_pewter_ignores_resistance_for_brocks_pokemon(self):
        """ニビシティジム: タケシのイシツブテ（闘）のワザは、カツラのドードー（抵抗力 闘 −30）の抵抗力の影響を受けない。"""
        for stadium, expected in ((PEWTER_CITY_GYM, 30), (CERULEAN_CITY_GYM, 0)):
            state = placed(stadium, active=mon(BROCKS_GEODUDE, (F,)), opponent_active=mon(BLAINES_DODUO))
            state = apply_kernel(with_coin_results(state, H, H, H), UseAttack(0, 0))
            self.assertEqual(damage_of(state)[-1]["amount"], expected)

    def test_resistance_gym_reduces_resistance_value(self):
        """抵抗力低下ジム: 抵抗力 −30 は −10 になる（色は変わらない。抵抗力のないポケモンには作らない）。"""
        state = placed(RESISTANCE_GYM, opponent_active=mon(BLAINES_DODUO))
        doduo = state.players[1].active
        self.assertEqual(resistance_of(state, doduo), (doduo and state.card_def(doduo.card).resistance, 10))
        self.assertEqual(resistance_of(state, state.players[0].active)[0], state.card_def(state.players[0].active.card).resistance)
        state = apply_kernel(with_coin_results(state, H), UseAttack(0, 0))  # エビワラー（闘）のワザ 20 − 10
        self.assertEqual(damage_of(state)[-1]["amount"], 10)

    def test_cinnabar_ignores_weakness_from_water_for_blaines_pokemon(self):
        for defender, expected in ((BLAINES_CHARMANDER, 10), (CHARMANDER, 20)):
            state = placed(CINNABAR_CITY_GYM, active=mon(MISTYS_SEEL, (W,)), opponent_active=mon(defender))
            state = apply_kernel(state, UseAttack(0, 0))
            self.assertEqual(damage_of(state)[-1]["amount"], expected)

    def test_retreat_costs(self):
        """ハナダシティジム: カスミのパウワウ（にげる 1）は 0。ロケット団の特訓ジム: お互いの対戦ポケモンは + 1（範囲外は WRONG_RETREAT_COST）。"""
        state = placed(CERULEAN_CITY_GYM, active=mon(MISTYS_SEEL, (W,)))
        self.assertEqual((retreat_cost(state, 0).minimum, retreat_cost(state, 0).maximum), (0, 0))
        moved = apply_kernel(state, Retreat(0, (), state.players[0].bench[0].card))
        self.assertEqual(last(moved, "retreat")["retreat_cost_stadium"], ((state.stadium.card, -1),))
        audited(self, moved)
        state = placed(ROCKETS_TRAINING_GYM, active=mon(RATTATA, (F,)))
        self.assertEqual(retreat_cost(state, 0).maximum, 1)
        with self.assertRaises(IllegalActionError) as caught:
            apply_kernel(state, Retreat(0, (), state.players[0].bench[0].card))
        self.assertEqual(caught.exception.code, "WRONG_RETREAT_COST")
        moved = apply_kernel(state, Retreat(0, tuple(state.players[0].active.energy), state.players[0].bench[0].card))
        audited(self, moved)


class ActivatedTest(unittest.TestCase):
    def test_celadon_cures_by_discarding_energy(self):
        state = placed(CELADON_CITY_GYM, active=mon(ERIKAS_ODDISH, (G,), poison=10))
        energy = state.players[0].active.energy[0]
        state = apply_kernel(state, UseStadium(0, energy))
        self.assertFalse(state.players[0].active.conditions.names())
        self.assertIn(energy, state.players[0].discard)
        audited(self, state)
        healthy = placed(CELADON_CITY_GYM, active=mon(ERIKAS_ODDISH, (G,)))
        assert_stops(self, healthy, UseStadium(0, healthy.players[0].active.energy[0]), NEW_CODES["TG1"])
        other = placed(CELADON_CITY_GYM, active=mon(HITMONCHAN, (F,), poison=10))
        assert_stops(self, other, UseStadium(0, other.players[0].active.energy[0]), "NOT_STADIUM_TARGET", IllegalActionError)
        assert_stops(self, other, UseStadium(0), "STADIUM_CHOICE_REQUIRED", IllegalActionError)

    def test_fuchsia_coin_and_once_per_turn(self):
        state = placed(FUCHSIA_CITY_GYM, bench=(KOGAS_KOFFING,), deck=[G] * 5)
        tails = apply_kernel(with_coin_results(state, T), UseStadium(0))
        self.assertEqual(len(tails.players[0].bench), 1)
        assert_stops(self, tails, UseStadium(0), "STADIUM_ALREADY_USED", IllegalActionError)  # 「うら」でも使ったことになる
        heads = apply_kernel(with_coin_results(state, H), UseStadium(0))
        self.assertEqual(heads.decision.kind, SELECT_POKEMON)
        heads = answer(heads, heads.decision.options)
        self.assertEqual(len(heads.players[0].bench), 0)
        self.assertEqual(len(heads.players[0].deck), 6)
        audited(self, heads)
        nothing = placed(FUCHSIA_CITY_GYM)
        assert_stops(self, nothing, UseStadium(0), NEW_CODES["FG2"])  # コインの前
        # この番に別のセキチクシティジムのカードで使ってから入れかえると FG1
        twice = placed(FUCHSIA_CITY_GYM, hand=[FUCHSIA_CITY_GYM], bench=(KOGAS_KOFFING,))
        twice = apply_kernel(with_coin_results(twice, T), UseStadium(0))
        twice = use(twice, FUCHSIA_CITY_GYM)
        assert_stops(self, twice, UseStadium(0), NEW_CODES["FG1"])

    def test_saffron_returns_basic_energy_any_number_of_times(self):
        state = placed(SAFFRON_CITY_GYM, active=mon(SABRINAS_ABRA, (P, P)))
        hand = len(state.players[0].hand)
        for _ in range(2):
            state = apply_kernel(state, UseStadium(0, state.players[0].active.energy[0]))
        self.assertEqual((len(state.players[0].active.energy), len(state.players[0].hand)), (0, hand + 2))
        self.assertEqual(state.energy_attachments_this_turn, 0)
        audited(self, state)

    def test_no_stadium_and_stadium_without_activation(self):
        assert_stops(self, board([]), UseStadium(0), "NO_STADIUM", IllegalActionError)
        assert_stops(self, placed(PEWTER_CITY_GYM), UseStadium(0), "STADIUM_NOT_USABLE", IllegalActionError)

    def test_stb1_under_trainer_lock(self):
        state = placed(SAFFRON_CITY_GYM, hand=[ROCKETS_EXPERIMENT], active=mon(SABRINAS_ABRA, (P,)), deck=[G] * 5)
        state = use(state, ROCKETS_EXPERIMENT, coins=(T,))
        assert_stops(self, state, UseStadium(0, state.players[0].active.energy[0]), NEW_CODES["STB1"])


class ReactionTest(unittest.TestCase):
    def test_narrow_gym_returns_bench_and_limits_all_paths(self):
        state = use(board([NARROW_GYM, RATTATA], bench=(RATTATA,) * 5, opponent_bench=(RATTATA,) * 5), NARROW_GYM)
        self.assertEqual((state.decision.kind, state.decision.player), (STADIUM_RETURN_BENCH, 1))  # 番でないプレイヤーが先
        state = answer(state, state.decision.options[:1])
        self.assertEqual((state.decision.kind, state.decision.player), (STADIUM_RETURN_BENCH, 0))
        state = answer(state, state.decision.options[-1:])
        self.assertEqual((len(state.players[0].bench), len(state.players[1].bench)), (4, 4))
        self.assertEqual((bench_limit(state, 0), bench_limit(state, 1)), (4, 4))
        assert_stops(self, state, PlayBasicToBench(0, card_of(state, RATTATA)), "BENCH_FULL", IllegalActionError)
        audited(self, state)

    def test_minefield_damage_is_not_counters_and_only_on_tails(self):
        for coin, expected in ((T, 20), (H, 0)):
            state = placed(ROCKETS_MINEFIELD_GYM, hand=[RATTATA], bench=())
            state = apply_kernel(with_coin_results(state, coin), PlayBasicToBench(0, card_of(state, RATTATA)))
            self.assertEqual(state.players[0].bench[0].damage, expected)
            audited(self, state)

    def test_viridian_heals_two_counters_when_evolving_giovannis_pokemon(self):
        state = placed(VIRIDIAN_CITY_GYM, hand=[GIOVANNIS_GYARADOS], active=mon(GIOVANNIS_MAGIKARP, damage=20))
        state = apply_kernel(state, EvolvePokemon(0, card_of(state, GIOVANNIS_GYARADOS), state.players[0].active.pokemon_id))
        self.assertEqual((state.decision.kind, state.decision.min_choices), (EVOLUTION_HEAL, 0))
        declined = answer(state, ())
        self.assertEqual(declined.players[0].active.damage, 20)
        healed = answer(state, state.decision.options)
        self.assertEqual(healed.players[0].active.damage, 0)
        audited(self, healed)
        one = placed(VIRIDIAN_CITY_GYM, hand=[GIOVANNIS_GYARADOS], active=mon(GIOVANNIS_MAGIKARP, damage=10))
        one = apply_kernel(one, EvolvePokemon(0, card_of(one, GIOVANNIS_GYARADOS), one.players[0].active.pokemon_id))
        d = one.decision
        assert_stops(self, one, ResolveDecision(d.player, d.id, d.options), NEW_CODES["VG1"])
        self.assertEqual(answer(one, ()).players[0].active.damage, 10)  # とりのぞかないことはいつも選べる


class DeclarationTest(unittest.TestCase):
    def test_vermilion_heads_bonus_and_tails_self_damage(self):
        for coin, opponent, own in ((H, 20, 0), (T, 10, 10)):
            state = placed(VERMILION_CITY_GYM, active=mon(LT_SURGES_RATTATA, (F, F)))
            state = apply_kernel(with_coin_results(state, coin, T), UseAttack(0, 1, stadium_coin=True))  # 2 枚目はでんこうせっかの「うら」
            self.assertEqual(last(state, "stadium_attack_coin")["heads"], coin is H)
            self.assertEqual(state.players[1].active.damage, opponent)
            self.assertEqual(state.players[0].active.damage, own)

    def test_vermilion_coin_needs_the_stadium_and_surges_pokemon(self):
        state = board([], active=mon(LT_SURGES_RATTATA, (F, F)))
        assert_stops(self, state, UseAttack(0, 1, stadium_coin=True), "STADIUM_COIN_NOT_AVAILABLE", IllegalActionError)
        other = placed(VERMILION_CITY_GYM)
        assert_stops(self, other, UseAttack(0, 0, stadium_coin=True), "STADIUM_COIN_NOT_AVAILABLE", IllegalActionError)

    def test_no_removal_gym_adds_two_card_cost(self):
        state = placed(NO_REMOVAL_GYM, hand=[ENERGY_REMOVAL, RATTATA, G], opponent_active=mon(HITMONCHAN, (F,)))
        state = use(state, ENERGY_REMOVAL)
        self.assertEqual((state.decision.kind, state.decision.min_choices, state.decision.max_choices), (DISCARD_FROM_HAND, 2, 2))
        state = answer(state, state.decision.options[:2])
        while state.decision is not None:
            state = answer(state, state.decision.options[:1])
        self.assertEqual(state.players[1].active.energy, [])
        audited(self, state)
        short = placed(NO_REMOVAL_GYM, hand=[ENERGY_REMOVAL, RATTATA], opponent_active=mon(HITMONCHAN, (F,)))
        assert_stops(self, short, PlayTrainer(0, card_of(short, ENERGY_REMOVAL)), "INSUFFICIENT_CARDS_IN_HAND", IllegalActionError)


class ChaosTest(unittest.TestCase):
    def test_tails_lets_the_opponent_borrow_and_discards_to_owner(self):
        state = placed(CHAOS_GYM, hand=[POTION], active=mon(HITMONCHAN, (F,), damage=20), opponent_active=mon(HITMONCHAN, (F,), damage=30))
        potion = card_of(state, POTION)
        state = use(state, POTION, coins=(T,))
        self.assertEqual((state.decision.kind, state.decision.player), (ACCEPT_REQUEST, 1))
        declined = answer(state, ())
        self.assertIn(potion, declined.players[0].discard)
        self.assertEqual((declined.players[0].active.damage, declined.players[1].active.damage), (20, 30))
        borrowed = answer(state, (1,))
        self.assertEqual(borrowed.trainer_in_use.using_player, 1)
        while borrowed.decision is not None:
            self.assertEqual(borrowed.decision.player, 1)
            borrowed = answer(borrowed, borrowed.decision.options[:1])
        self.assertEqual(borrowed.players[1].active.damage, 10)  # 相手が自分のポケモンから 20 をとりのぞく
        self.assertIn(potion, borrowed.players[0].discard)  # 持ち主のトラッシュ
        self.assertEqual(borrowed.current_player, 0)
        audited(self, borrowed)

    def test_heads_uses_normally(self):
        state = placed(CHAOS_GYM, hand=[POTION], active=mon(HITMONCHAN, (F,), damage=20))
        state = use(state, POTION, coins=(H,))
        while state.decision is not None:
            state = answer(state, state.decision.options[:1])
        self.assertEqual(state.players[0].active.damage, 0)

    def test_attached_cards_cannot_be_borrowed(self):
        state = placed(CHAOS_GYM, hand=[PLUSPOWER])
        state = use(state, PLUSPOWER, coins=(T,))
        self.assertIsNone(state.decision)
        self.assertEqual(last(state, "chaos_not_borrowable")["player"], 1)
        self.assertIn(card_of(state, PLUSPOWER, zone="discard"), state.players[0].discard)

    def test_ch1_for_trainers_that_refer_to_the_users_turn(self):
        state = placed(CHAOS_GYM, hand=[KOGA_TRAINER, INVISIBLE_WALL])
        for trainer in (KOGA_TRAINER, INVISIBLE_WALL):
            waiting = use(state, trainer, coins=(T,))
            d = waiting.decision
            self.assertEqual(d.kind, ACCEPT_REQUEST)
            assert_stops(self, waiting, ResolveDecision(d.player, d.id, (1,)), NEW_CODES["CH1"])
            self.assertIsNone(answer(waiting, ()).decision)  # 借りないことはいつも選べる


if __name__ == "__main__":
    unittest.main()
