"""v0.58: スタジアムの処理を再利用するカード 3 枚と特殊エネルギー 4 枚（docs/stadium-reuse-special-energy-v0.58.md）。

7 枚: タケシのゴローン（PMCG5-052）・タケシのゴローニャ（PMCG5-053）・ナツメのサイキックコントロール（PMCG6-088）・無色2個エネルギー（PMCG1-096）・
きずぐすり配合エネルギー（PMCG4-063）・なんでもなおし配合エネルギー（PMCG4-064）・レインボーエネルギー（PMCG4-065）。どれも kyuura データの採用
（採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合。無色2個エネルギーは kyuura の日本語の説明が null・``energy.provides`` が空なので、
カードの名前と同じ版のカードの「無色」の記号 2 つで個数を決めた（英語の説明は根拠にしない）。

再利用した kyuura の記録: GR-2000-P310-ATTACH-ENERGY（手札からつけたことで引き起こされること）・GR-2000-P325-SAME-TIMING・CR-ENERGY-TRANS-RAINBOW（エナジー
トランスでレインボーエネルギーを「草」として移せる。移動で 10 ダメージは受けない）・CR-ENERGY-TRANS-NOT-ATTACHMENT・ERR-ENERGY-RETRIEVAL（手札・山札・トラッシュの
特殊エネルギーは基本エネルギーカードではない）・GR-2000-P308-SAME-NAME（基本エネルギーだけが枚数の制限なし）。ガイドブックは読んでいない。

新しい停止コード: RB1・RB2・RB3・RB4・TE2・RT1。
"""

from __future__ import annotations

import pathlib
import unittest

from kyuura_engine import (
    AttachEnergy,
    DeckValidationError,
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    check_invariants,
    new_game,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import USE_DISCARD_TRAINER
from kyuura_engine.effects import (
    attached_units,
    attack_cost_payable,
    energy_unit_count,
    retreat_cost,
)
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests.helpers import (
    BLASTOISE,
    BROCKS_GEODUDE,
    BROCKS_GOLEM,
    BROCKS_GRAVELER,
    BULBASAUR,
    CHAOS_GYM,
    CLEFAIRY_DOLL,
    DARK_GLOOM,
    DARK_VILEPLUME,
    DITTO,
    DOUBLE_COLORLESS_ENERGY,
    ENERGY_REMOVAL,
    ENERGY_RETRIEVAL,
    FIGHTING,
    FULL_HEAL_ENERGY,
    GRASS,
    HITMONCHAN,
    IVYSAUR,
    KABUTO,
    MYSTERIOUS_FOSSIL,
    NO_REMOVAL_GYM,
    PEWTER_CITY_GYM,
    PLUSPOWER,
    POTION,
    POTION_ENERGY,
    RAINBOW_ENERGY,
    RATTATA,
    ROCKET_GRUNT,
    ROCKET_ODDISH,
    SABRINAS_PSYCHIC_CONTROL,
    SQUIRTLE,
    SUPER_ENERGY_REMOVAL,
    V0_58_CARDS,
    V0_58_ENERGIES,
    V0_58_POKEMON,
    VENUSAUR,
    WARTORTLE,
    WATER,
    apply_kernel,
    build_test_state,
    expand_decklist,
)
from tests.log_audit import LATEST_FORMAT, observation_problems, serialization_problems
from tests.test_instant_trainers_v0_55 import (
    TURN,
    answer,
    board,
    card_of,
    pid,
    pokemon,
    use,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "stadium-reuse-special-energy-v0.58.md"
H, T = CoinSide.HEADS, CoinSide.TAILS
F, W, G = FIGHTING, WATER, GRASS
DCE, PE, FHE, RE = DOUBLE_COLORLESS_ENERGY, POTION_ENERGY, FULL_HEAL_ENERGY, RAINBOW_ENERGY
NEW_CODES = {
    "RB1": "UNRESOLVED_RAINBOW_ENERGY_TYPE",
    "RB2": "UNRESOLVED_RAINBOW_ATTACH_AS_TYPE",
    "RB3": "UNRESOLVED_RAINBOW_AS_BASIC_ENERGY_CARD",
    "RB4": "UNRESOLVED_RAINBOW_DAMAGE_RECEIVED_POWER",
    "TE2": "UNRESOLVED_TRANSFORM_SPECIAL_ENERGY",
    "RT1": "UNRESOLVED_RETREAT_OVERPAY",
}


BELOW = {BROCKS_GRAVELER: BROCKS_GEODUDE, BROCKS_GOLEM: [BROCKS_GEODUDE, BROCKS_GRAVELER], VENUSAUR: [BULBASAUR, IVYSAUR],
         BLASTOISE: [SQUIRTLE, WARTORTLE], DARK_VILEPLUME: [ROCKET_ODDISH, DARK_GLOOM], KABUTO: MYSTERIOUS_FOSSIL}


def mon(card, energy=(), **extra):
    """場のポケモン（進化ポケモンは下に重なったカードを置く。tests/helpers.py の ``build_test_state`` の ``evolved_from``）。"""
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


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


def events(state, kind):
    return [e for e in state.log if e["kind"] == kind]


def attach(state, card_id, target_card_id=None, player=0):
    target = state.players[player].active if target_card_id is None else next(
        p for p in state.players[player].in_play() if state.cards[p.card].card_id == target_card_id)
    return AttachEnergy(player, card_of(state, card_id, player=player), target.card)


class CardDataTest(unittest.TestCase):
    def test_seven_cards_are_supported(self):
        pool = load_card_pool()
        for card_id in V0_58_CARDS:
            self.assertTrue(pool.get(card_id).supported, card_id)
        self.assertEqual(V0_58_POKEMON, (BROCKS_GRAVELER, BROCKS_GOLEM))
        for card_id in V0_58_ENERGIES:
            definition = pool.get(card_id)
            self.assertTrue(definition.is_special_energy and not definition.is_basic_energy, card_id)

    def test_special_energy_is_classified_through_the_registry(self):
        """登録を除くと、特殊エネルギーは未対応（名前・説明文・kyuura の provides で一括に対応にしない）。"""
        registry = E.DEFAULT_EFFECTS.without_energies("test-without-energies", V0_58_ENERGIES)
        from kyuura_engine.cards import pool_from_extract, read_extract

        pool = pool_from_extract(read_extract(), registry)
        for card_id in V0_58_ENERGIES:
            self.assertFalse(pool.get(card_id).supported, card_id)

    def test_special_energy_is_limited_to_four_copies(self):
        """GR-2000-P308-SAME-NAME: 枚数の制限がないのは基本エネルギーだけ。特殊エネルギーは同じ名前 4 枚まで。"""
        deck = expand_decklist({BROCKS_GEODUDE: 4, RATTATA: 4, DCE: 5, F: 47})
        with self.assertRaises(DeckValidationError):
            new_game(deck, expand_decklist({BROCKS_GEODUDE: 4, F: 56}), 0)

    def test_ruling_ids_are_in_the_document(self):
        text = DOC.read_text(encoding="utf-8")
        for ruling, code in NEW_CODES.items():
            self.assertIn(ruling, text)
            self.assertIn(code, text)
        self.assertEqual(LATEST_FORMAT, 22)  # v0.67 で 22  # v0.59 で 19（energy_roles）を加えた
        self.assertEqual(max(FORMAT_VERSIONS), 22)  # v0.67 で 22（face_down_cards）


class EnergyUnitsTest(unittest.TestCase):
    """カードの枚数・エネルギーの個数・色の割り当てを分ける（docs 2 章）。"""

    def test_units_per_card(self):
        state = board(active=mon(BROCKS_GRAVELER, (DCE, PE, FHE, RE, F)))
        active = state.players[0].active
        units = attached_units(state, active)
        self.assertEqual(len(active.energy), 5)
        self.assertEqual(len(units), 6)  # 無色2個エネルギーは 2 個、レインボーエネルギーは 1 個
        self.assertEqual(units[:2], [E.COLORLESS_UNIT, E.COLORLESS_UNIT])
        self.assertEqual(units[4], E.BASIC_ENERGY_COLORS)

    def test_double_colorless_pays_colorless_but_not_fighting(self):
        state = board(active=mon(BROCKS_GRAVELER, (DCE,)))
        tackle, explosion = load_card_pool().get(BROCKS_GRAVELER).attacks
        active = state.players[0].active
        self.assertTrue(attack_cost_payable(state, active, tackle))  # たいあたり（無色 2 個）
        self.assertFalse(attack_cost_payable(state, active, explosion))
        after = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(events(after, "attack")[-1]["attack"], "たいあたり")
        audited(self, after)
        with self.assertRaises(IllegalActionError) as caught:
            apply_kernel(state, UseAttack(0, 1))
        self.assertEqual(caught.exception.code, "INSUFFICIENT_ENERGY")

    def test_rainbow_is_one_unit_of_any_color(self):
        """レインボーエネルギーは合計 1 個（各色を別の 1 個として数えない）。闘 2 + レインボー 1 で闘 3 を払える。闘 1 + レインボー 1 では払えない。"""
        explosion = load_card_pool().get(BROCKS_GRAVELER).attacks[1]
        state = board(active=mon(BROCKS_GRAVELER, (F, F, RE)))
        self.assertTrue(attack_cost_payable(state, state.players[0].active, explosion))
        state = board(active=mon(BROCKS_GRAVELER, (F, RE, PE)))
        self.assertFalse(attack_cost_payable(state, state.players[0].active, explosion))

    def test_land_crush_with_three_cards(self):
        """ランドクラッシュ（闘 2・無色 2）を、闘 1・レインボー 1・無色2個エネルギー 1 の 3 枚で払える。"""
        land_crush = load_card_pool().get(BROCKS_GOLEM).attacks[1]
        state = board(active=mon(BROCKS_GOLEM, (F, RE, DCE)))
        self.assertTrue(attack_cost_payable(state, state.players[0].active, land_crush))
        self.assertEqual(energy_unit_count(state, state.players[0].active.energy, state.players[0].active), 4)


class RetreatTest(unittest.TestCase):
    def test_double_colorless_pays_retreat_cost_two(self):
        state = board(active=mon(BROCKS_GRAVELER, (DCE,)), bench=(RATTATA,))
        dce = state.players[0].active.energy[0]
        after = apply_kernel(state, Retreat(0, (dce,), state.players[0].bench[0].card))
        self.assertIn(dce, after.players[0].discard)
        self.assertEqual(state.cards[after.players[0].active.card].card_id, RATTATA)
        audited(self, after)

    def test_double_colorless_for_retreat_cost_one_is_rt1(self):
        """無色2個エネルギーは分けてトラッシュできない。にげるエネルギー 1 に 1 枚で 2 個を払えるかは決まらない（RT1）。エネルギー・コインの前に止める。"""
        state = board(active=mon(BROCKS_GEODUDE, (DCE,)), bench=(RATTATA,))
        self.assertEqual(retreat_cost(state, 0).maximum, 1)
        dce = state.players[0].active.energy[0]
        assert_stops(self, state, Retreat(0, (dce,), state.players[0].bench[0].card), NEW_CODES["RT1"])

    def test_extra_card_is_wrong_retreat_cost(self):
        """余計なカードを除いても足りる選び方（にげる 2 に無色2個エネルギー + 闘）は、今までどおり WRONG_RETREAT_COST。"""
        state = board(active=mon(BROCKS_GRAVELER, (DCE, F)), bench=(RATTATA,))
        active = state.players[0].active
        with self.assertRaises(IllegalActionError) as caught:
            apply_kernel(state, Retreat(0, tuple(active.energy), state.players[0].bench[0].card))
        self.assertEqual(caught.exception.code, "WRONG_RETREAT_COST")
        self.assertIn("2 枚・3 個", caught.exception.message)

    def test_basic_energy_message_is_unchanged(self):
        state = board(active=mon(BROCKS_GRAVELER, (F,)), bench=(RATTATA,))
        with self.assertRaises(IllegalActionError) as caught:
            apply_kernel(state, Retreat(0, tuple(state.players[0].active.energy), state.players[0].bench[0].card))
        self.assertEqual(caught.exception.code, "WRONG_RETREAT_COST")
        self.assertIn("（1 枚選んでいる）", caught.exception.message)


class AttachEffectTest(unittest.TestCase):
    def test_potion_energy_removes_one_counter(self):
        state = board([PE], active=mon(BROCKS_GRAVELER, (), damage=30))
        after = apply_kernel(state, attach(state, PE))
        self.assertEqual(after.players[0].active.damage, 20)
        self.assertEqual(events(after, "energy_heal")[-1]["counters"], 1)
        self.assertEqual(after.energy_attachments_this_turn, 1)
        audited(self, after)

    def test_potion_energy_without_damage_does_nothing(self):
        state = board([PE], active=mon(BROCKS_GRAVELER))
        after = apply_kernel(state, attach(state, PE))
        self.assertEqual(after.players[0].active.damage, 0)
        self.assertEqual(events(after, "energy_heal"), [])

    def test_full_heal_energy_cures_all_special_conditions(self):
        """なんでもなおし配合エネルギーの対象はつけたポケモン（説明に書かれている。トレーナーのなんでもなおしの FH1 は当てはまらない）。"""
        state = board([FHE], active=mon(BROCKS_GRAVELER, (), poison=10, confused=True))
        after = apply_kernel(state, attach(state, FHE))
        conditions = after.players[0].active.conditions
        self.assertIsNone(conditions.poison)
        self.assertFalse(conditions.confused)
        removed = events(after, "special_conditions_removed")[-1]
        self.assertEqual(removed["reason"], "cured")
        self.assertEqual(removed["energy_card"], card_of(state, FHE))
        audited(self, after)

    def test_full_heal_energy_on_bench_does_nothing(self):
        state = board([FHE], active=mon(BROCKS_GRAVELER, (), poison=10), bench=(RATTATA,))
        after = apply_kernel(state, attach(state, FHE, RATTATA))
        self.assertIsNotNone(after.players[0].active.conditions.poison)

    def test_rainbow_energy_deals_ten_ignoring_weakness(self):
        """10 ダメージは弱点・抵抗力に関係なく、ワザのダメージではない（ログ ``energy_damage``）。"""
        state = board([RE], active=mon(BROCKS_GRAVELER))
        after = apply_kernel(state, attach(state, RE))
        self.assertEqual(after.players[0].active.damage, 10)
        self.assertEqual(events(after, "energy_damage")[-1]["amount"], 10)
        self.assertEqual(events(after, "damage"), [])
        audited(self, after)

    def test_rainbow_energy_can_knock_out(self):
        """そのダメージで HP 以上になったら、つけたあとにきぜつの処理（timing ``energy``）。相手がサイドを取る。"""
        state = board([RE], active=mon(BROCKS_GRAVELER), bench=(mon(RATTATA, (), damage=20),))
        after = apply_kernel(state, attach(state, RE, RATTATA))
        knock = events(after, "knock_out")[-1]
        self.assertEqual(knock["timing"], "energy")
        self.assertIsNotNone(after.decision)
        self.assertEqual(after.decision.player, 1)  # 相手がサイドを取る
        self.assertEqual(len(after.players[0].bench), 0)
        audited(self, after)

    def test_moving_rainbow_does_not_deal_damage(self):
        """CR-ENERGY-TRANS-RAINBOW: エナジートランスで「草」としてつけかえられ、その移動で 10 ダメージは受けない（CR-ENERGY-TRANS-NOT-ATTACHMENT）。"""
        state = board(active=mon(VENUSAUR, (RE,)), bench=(mon(RATTATA),))
        venusaur = state.players[0].active
        rainbow = venusaur.energy[0]
        target = state.players[0].bench[0]
        after = apply_kernel(state, UsePokemonPower(0, venusaur.pokemon_id, 0, energy=rainbow, source=venusaur.pokemon_id, target=target.pokemon_id))
        self.assertIn(rainbow, after.players[0].bench[0].energy)
        self.assertEqual(after.players[0].bench[0].damage, 0)
        self.assertEqual(events(after, "energy_damage"), [])
        self.assertEqual(after.energy_attachments_this_turn, 0)
        audited(self, after)

    def test_rainbow_on_kabuto_armor_is_rb4(self):
        state = board([RE], active=mon(BROCKS_GRAVELER), bench=(KABUTO,))
        assert_stops(self, state, attach(state, RE, KABUTO), NEW_CODES["RB4"])

    def test_rain_dance_with_rainbow_is_rb2(self):
        state = board([RE], active=mon(BLASTOISE))
        blastoise = state.players[0].active
        assert_stops(self, state, UsePokemonPower(0, blastoise.pokemon_id, 0, energy=card_of(state, RE), target=blastoise.pokemon_id),
                     NEW_CODES["RB2"])


class RainbowQuestionTest(unittest.TestCase):
    def test_hydro_pump_with_rainbow_is_rb1(self):
        """ハイドロポンプ（ついている「水」エネルギーの数）にレインボーエネルギーを数えるかは決まらない（RB1）。支払いには使える。"""
        state = board(active=mon(BLASTOISE, (W, W, W, RE)))
        assert_stops(self, state, UseAttack(0, 0), NEW_CODES["RB1"])

    def test_energy_retrieval_does_not_take_special_energy(self):
        """ERR-ENERGY-RETRIEVAL: トラッシュの特殊エネルギーは「基本エネルギーカード」ではない。選べるものに入らない。"""
        state = board([ENERGY_RETRIEVAL, RATTATA], discard=[RE, DCE, F])
        after = use(state, ENERGY_RETRIEVAL)
        after = answer(after, (card_of(after, RATTATA),))
        options = after.decision.options
        self.assertEqual(sorted(after.cards[u].card_id for u in options), [F])

    def test_energy_removal_can_take_special_energy(self):
        """エネルギー・リムーブの「エネルギーカード」には特殊エネルギーも入る（印刷の文面。基本エネルギーに限らない）。"""
        state = board([ENERGY_REMOVAL], opponent_active=mon(HITMONCHAN, (DCE,)))
        after = use(state, ENERGY_REMOVAL)
        while after.decision is not None:
            after = answer(after, (after.decision.options[0],))
        self.assertIn(state.players[1].active.energy[0], after.players[1].discard)
        audited(self, after)

    def test_transform_with_special_colorless_is_te2(self):
        """［へんしん］のメタモンの「どの色としても使える」が無色の特殊エネルギーにも当てはまるかで払えるかが変わるワザは止める（TE2）。"""
        state = board(active=mon(DITTO, (DCE,)), opponent_active=mon(HITMONCHAN, (F,)))
        assert_stops(self, state, UseAttack(0, 0), NEW_CODES["TE2"])


class GravelerGolemTest(unittest.TestCase):
    def test_explosion_discards_the_stadium(self):
        state = board([PEWTER_CITY_GYM], active=mon(BROCKS_GRAVELER, (F, F, F)), bench=(RATTATA,), opponent_bench=(RATTATA,))
        state = use(state, PEWTER_CITY_GYM)
        stadium = state.stadium.card
        after = apply_kernel(state, UseAttack(0, 1))
        self.assertIsNone(after.stadium)
        self.assertIn(stadium, after.players[0].discard)
        discarded = events(after, "stadium_discarded")[-1]
        self.assertEqual(discarded["reason"], "attack")
        self.assertEqual(pokemon(after, pid(after, 1, RATTATA)).damage, 10)
        audited(self, after)

    def test_explosion_without_stadium(self):
        state = board(active=mon(BROCKS_GRAVELER, (F, F, F)), bench=(RATTATA,), opponent_bench=(RATTATA,))
        after = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual(len(events(after, "stadium_discard_none")), 1)
        self.assertEqual(after.players[0].active.damage, 50)
        audited(self, after)

    def test_rock_slide_chooses_up_to_three(self):
        state = board(active=mon(BROCKS_GOLEM, (F, F, F)), opponent_bench=(RATTATA, RATTATA, RATTATA, RATTATA))
        after = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(after.decision.max_choices, 3)
        chosen = after.decision.options[:2]
        after = answer(after, chosen)
        for pid_ in chosen:
            self.assertEqual(pokemon(after, pid_).damage, 10)
        audited(self, after)


def pc_board(hand=(), opponent_discard=(POTION,), *, active=None, opponent_hand=(), opponent_bench=(RATTATA,), seed=0):
    me = {"active": active or mon(BROCKS_GRAVELER, (), damage=30), "bench": [RATTATA], "hand": [SABRINAS_PSYCHIC_CONTROL, *hand]}
    them = {"active": mon(HITMONCHAN, (F, F)), "bench": list(opponent_bench), "hand": list(opponent_hand), "discard": list(opponent_discard)}
    return build_test_state([me, them], turn_number=TURN, current_player=0, seed=seed)


def play_pc(state, coins=(H,)):
    return use(state, SABRINAS_PSYCHIC_CONTROL, coins=coins)


class PsychicControlTest(unittest.TestCase):
    def test_tails_does_nothing(self):
        state = pc_board()
        after = play_pc(state, (T,))
        self.assertIsNone(after.decision)
        self.assertIsNone(after.trainer_in_use)
        self.assertIn(card_of(state, SABRINAS_PSYCHIC_CONTROL), after.players[0].discard)
        audited(self, after)

    def test_heads_without_usable_card(self):
        """相手のトラッシュに使えるトレーナーがなければ決定を出さずに終わる（ポケモンにつけて使う・場に出して使うカードは除く）。"""
        state = pc_board(opponent_discard=(PLUSPOWER, CLEFAIRY_DOLL, PEWTER_CITY_GYM))
        after = play_pc(state)
        self.assertEqual(len(events(after, "discard_trainer_use_none")), 1)
        self.assertIsNone(after.trainer_in_use)
        audited(self, after)

    def test_use_opponents_potion(self):
        """相手のトラッシュのきずぐすりを使う。カードは同じ uid・持ち主のまま使用中の場所に移り、使い終わったら相手のトラッシュにもどる。選ぶもの・効果は使ったプレイヤー。"""
        state = pc_board()
        potion = card_of(state, POTION, zone="discard", player=1)
        after = play_pc(state)
        self.assertEqual(after.decision.kind, USE_DISCARD_TRAINER)
        self.assertEqual(after.decision.options, (potion,))
        after = answer(after, (potion,))
        self.assertEqual(after.trainer_in_use.card, potion)
        self.assertEqual(after.trainer_in_use.player, 1)
        self.assertEqual(after.trainer_in_use.using_player, 0)
        self.assertEqual(len(after.trainer_stack), 1)
        audited(self, after)
        while after.decision is not None:
            after = answer(after, (after.decision.options[0],))
        self.assertEqual(after.players[0].active.damage, 10)
        self.assertIn(potion, after.players[1].discard)
        self.assertNotIn(potion, after.players[0].discard)
        self.assertIn(card_of(state, SABRINAS_PSYCHIC_CONTROL), after.players[0].discard)
        self.assertEqual(after.trainer_stack, ())
        self.assertIsNone(after.trainer_in_use)
        inner = [e for e in after.log if e["kind"] == "play_trainer" and e.get("source_zone") == "discard"]
        self.assertEqual(len(inner), 1)
        self.assertEqual((inner[0]["player"], inner[0]["owner"]), (0, 1))
        self.assertEqual(sorted(after.cards), sorted(state.cards))  # 複製しない
        audited(self, after)

    def test_decline(self):
        state = pc_board()
        after = answer(play_pc(state), ())
        self.assertEqual(len(events(after, "discard_trainer_use_declined")), 1)
        self.assertIn(card_of(state, POTION, zone="discard", player=1), after.players[1].discard)
        audited(self, after)

    def test_invalid_answer_is_rejected(self):
        state = play_pc(pc_board(opponent_discard=(POTION, PLUSPOWER)))
        plus = card_of(state, PLUSPOWER, zone="discard", player=1)
        before = snapshot(state)
        with self.assertRaises(IllegalActionError):
            apply_kernel(state, ResolveDecision(0, state.decision.id, (plus,)))
        self.assertEqual(snapshot(state), before)

    def test_save_and_restore_mid_inner_use(self):
        """内側の使用の途中（きずぐすりの決定を待つ）を形式 18 で書き出せる。形式 17 以下は外側の使用を書き出せない（ValueError）。"""
        state = play_pc(pc_board())
        state = answer(state, (state.decision.options[0],))
        self.assertIsNotNone(state.decision)
        data = state_to_dict(state, format_version=18)
        self.assertEqual(len(data["trainer_stack"]), 1)
        for version in range(1, 18):
            with self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)
        audited(self, state)

    def test_condition_is_paid_from_users_hand(self):
        """超エネルギーリムーブの使うための条件（自分のポケモンのエネルギーカード）は、使ったプレイヤーの場で払う。満たせなければ選べるものに入らない。"""
        state = pc_board(opponent_discard=(SUPER_ENERGY_REMOVAL, POTION))
        after = play_pc(state)
        self.assertEqual([after.cards[u].card_id for u in after.decision.options], [POTION])  # 使ったプレイヤーの対戦ポケモンにエネルギーがない
        state = pc_board(opponent_discard=(SUPER_ENERGY_REMOVAL, POTION), active=mon(BROCKS_GRAVELER, (F,), damage=30))
        after = play_pc(state)
        self.assertEqual(sorted(after.cards[u].card_id for u in after.decision.options), sorted([SUPER_ENERGY_REMOVAL, POTION]))

    def test_chaos_gym_flips_for_outer_and_inner(self):
        """錯乱ジムが場にあれば、外側のサイキックコントロールと内側のトレーナーで、それぞれコインを投げる（外側のコインの結果を内側に持ち越さない）。"""
        me = {"active": mon(BROCKS_GRAVELER, (), damage=30), "bench": [RATTATA], "hand": [CHAOS_GYM, SABRINAS_PSYCHIC_CONTROL]}
        them = {"active": mon(HITMONCHAN, (F, F)), "bench": [RATTATA], "hand": [], "discard": [POTION]}
        state = use(build_test_state([me, them], turn_number=TURN, current_player=0), CHAOS_GYM)
        after = use(state, SABRINAS_PSYCHIC_CONTROL, coins=(H, H, H))  # 錯乱ジム（外側）・サイキックコントロール・錯乱ジム（内側）
        after = answer(after, (after.decision.options[0],))
        checks = events(after, "chaos_check")
        self.assertEqual(len(checks), 2)
        self.assertEqual([c["card"] for c in checks], [card_of(state, SABRINAS_PSYCHIC_CONTROL), card_of(state, POTION, zone="discard", player=1)])
        audited(self, after)

    def test_no_removal_gym_cost_is_paid_from_users_hand(self):
        """リムーブ禁止ジムの追加の条件（手札から 2 枚）は使ったプレイヤーの手札で払う。手札が足りなければエネルギー・リムーブは選べない。"""
        me = {"active": mon(BROCKS_GRAVELER, (), damage=30), "bench": [RATTATA], "hand": [NO_REMOVAL_GYM, SABRINAS_PSYCHIC_CONTROL]}
        them = {"active": mon(HITMONCHAN, (F, F)), "bench": [RATTATA], "hand": [], "discard": [ENERGY_REMOVAL, POTION]}
        state = use(build_test_state([me, them], turn_number=TURN, current_player=0), NO_REMOVAL_GYM)
        after = use(state, SABRINAS_PSYCHIC_CONTROL, coins=(H,))
        self.assertEqual([after.cards[u].card_id for u in after.decision.options], [POTION])

    def test_trainer_ban_blocks_psychic_control(self):
        """トレーナーの使用の禁止がはたらいていれば、サイキックコントロール自体を使えない（TRAINER_PREVENTED。手札から出す前）。"""
        state = pc_board(opponent_bench=(mon(DARK_VILEPLUME),))
        assert_stops(self, state, PlayTrainer(0, card_of(state, SABRINAS_PSYCHIC_CONTROL)), "TRAINER_PREVENTED", error=IllegalActionError)


class PsychicControlTurnTest(unittest.TestCase):
    """CH1 は、使うプレイヤーが番のプレイヤーでない（錯乱ジムで相手がサイキックコントロールを借りて使った）ときだけ。自分の番に使うなら、借りたことだけで CH1 にしない。"""

    def test_own_turn_is_not_ch1(self):
        state = play_pc(pc_board(opponent_discard=(ROCKET_GRUNT, POTION)))
        grunt = card_of(state, ROCKET_GRUNT, zone="discard", player=1)
        self.assertIn(grunt, state.decision.options)
        self.assertNotIn(grunt, state.decision.context_value("unresolved_choices", ()))

    def test_borrowed_psychic_control_is_ch1(self):
        me = {"active": mon(BROCKS_GRAVELER, (), damage=30), "bench": [RATTATA], "hand": [CHAOS_GYM, SABRINAS_PSYCHIC_CONTROL], "discard": [ROCKET_GRUNT]}
        them = {"active": mon(HITMONCHAN, (F, F)), "bench": [RATTATA], "hand": []}
        state = use(build_test_state([me, them], turn_number=TURN, current_player=0), CHAOS_GYM)
        state = use(state, SABRINAS_PSYCHIC_CONTROL, coins=(T, H))  # 錯乱ジムのコインは「うら」→ 相手が借りるか。サイキックコントロールのコインは「おもて」
        self.assertEqual(state.decision.player, 1)
        state = answer(state, state.decision.options)  # 相手が借りて使う
        grunt = card_of(state, ROCKET_GRUNT, zone="discard", player=0)
        d = state.decision
        self.assertEqual((d.kind, d.player), (USE_DISCARD_TRAINER, 1))
        self.assertIn(grunt, d.context_value("unresolved_choices", ()))
        assert_stops(self, state, ResolveDecision(1, d.id, (grunt,)), "UNRESOLVED_CHAOS_GYM_BORROWED_TURN")
        audited(self, state)


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.58 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.58 の 4 組を 2 seed ずつ（席を入れかえて 16 局）。監査の失敗・想定外の拒否・内部エラー・手数の上限がなく、特殊エネルギーをつけたときの効果・サイキック
        コントロールで相手のトラッシュのトレーナーを使う場面が起こる（勝敗は判断に使わない）。"""
        from tools import existing_effect_games as games

        results = games.run(range(2), pairings=games.PAIRINGS_V0_58)
        totals = {}
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"), game.get("error"))
                if game["outcome"] == "halted":
                    self.assertEqual(game["halt_code"], "UNRESOLVED_MULLIGAN_COMPENSATION")
                for key, count in game.get("v058", {}).items():
                    totals[key] = totals.get(key, 0) + count
        for key in ("attach_PMCG1-096", "attach_PMCG4-063", "attach_PMCG4-064", "attach_PMCG4-065", "energy_heal", "energy_damage"):
            with self.subTest(key=key):
                self.assertGreater(totals.get(key, 0), 0)
        self.assertTrue(any(key.startswith("psychic_control_inner_") for key in totals))
