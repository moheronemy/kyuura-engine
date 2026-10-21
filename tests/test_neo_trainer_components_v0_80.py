"""v0.80: v0.79 の共通処理の 2 つの修正（A: ポケモンチェックの途中のきぜつのあとの交代・B: ワザが失敗しても処理する要素のコイン）と、トレーナー 30 枚
（docs/neo-trainer-components-v0.80.md）。

A（PK1）: 1 と 2 のあいだにきぜつの判定をする読み方では、バトル場が空いたプレイヤーが 2 の前にバトル場に出しうるポケモンを出してから比べる（［へんしん］の姿・最大HP が変わる）。
B: ワザが失敗しても処理する要素（メタルクラッシュの「(その場合も、…)」）は、失敗のコインが決める要素に数えない（「ダメージを受けない」相手には既存の問いで止める）。
エフェクトガード: コインの前の確かめで、ダメージの要素と効果の要素を別々に確かめる。
カードはどれも kyuura データの採用（採用したデータのコミット 7d3f4ca。処理に使う文面は kyuura の印刷の文面）。ガイドブックは読んでいない。
"""

from __future__ import annotations

import copy
import pathlib
import pickle
import unittest

from kyuura_engine import (
    EndTurn,
    EvolvePokemon,
    IllegalActionError,
    Phase,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    UseStadium,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    ACCEPT_REQUEST,
    BENCH_FROM_DECK,
    DISCARD_TO_DECK,
    QUIZ_ANSWER,
    QUIZ_CARD,
    RECOVER_POKEMON,
    SELECT_DRAW_COUNT,
    SELECT_LOOK_COUNT,
    SELECT_OPPONENT_PRIZE,
    SELECT_POKEMON,
    TAKE_LOOKED_TRAINER,
)
from kyuura_engine.effects import EffectRegistry
from kyuura_engine.observation import HIDDEN_COUNT_KINDS, observe, visible_log
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import EVOLUTION_BAN, TrainerUseLock
from tests import helpers as H
from tests.helpers import apply_kernel, build_test_state, with_coin_results
from tests.log_audit import observation_problems, serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "neo-trainer-components-v0.80.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
TURN = 7
W, F, G, L, P = H.WATER, H.FIRE, H.GRASS, H.LIGHTNING, H.PSYCHIC
MID = "UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT"
DK = H.DARKNESS_ENERGY_NEO1

SUPER_ROD, ENERGY_CHARGE, SUPER_ENERGY_RETRIEVAL_NEO, ENERGY_ARK, ENERGY_AMPLIFIER = "neo1-074", "neo1-087", "neo1-092", "neo2-053", "neo4-102"
ELM, MARY, TIME_CAPSULE, BILLS_MAIL = "neo1-078", "neo1-089", "neo1-091", "neo4-100"
POKEDEX_808, SLOT_GAME, POKEGEAR = "neo1-082", "neo1-090", "neo1-093"
REVERSE_SWITCH, MARCH, HYPER = "neo1-075", "neo1-076", "neo2-056"
QUIZ_2, CARD_FLIP, PERSONALITY, SECRET_ACTIVITY, OAKS_INVENTION = "GD5-017", "neo1-080", "neo4-105", "neo4-107", "neo4-111"
IMAKUNI, TROPICAL_WIND, DANCE_IMAKUNI, MOOMOO_MILK, POWDER = "PR1-013", "PR1-074", "PRN-026", "neo1-077", "neo4-099"
HEALING_FIELD, ENERGY_STADIUM_NEO, LUCKY_STADIUM_NEO, RADIO_TOWER = "neo3-054", "neo4-101", "neo4-106", "neo4-112"
EFFECT_GUARD = "ES2-033"

NEW_CODES = {
    "SRD1": "UNRESOLVED_SUPER_ROD_WITHOUT_TARGET",
    "UPZ1": "UNRESOLVED_TRAINER_UP_TO_ZERO_CHOICE",
    "UPZ2": "UNRESOLVED_TRAINER_UP_TO_WITHOUT_TARGET",
    "TOP1": "UNRESOLVED_DECK_TOP_SHORT",
    "TL1": "UNRESOLVED_HAND_TRAINER_LOCK_BORROW",
    "HY1": "UNRESOLVED_DEVOLUTION_SPRAY_HYPER_WITHOUT_TARGET",
    "MK1": "UNRESOLVED_MOOMOO_MILK_UNDAMAGED_TARGET",
    "BP1": "UNRESOLVED_ALL_PURPOSE_POWDER_WITHOUT_TARGET",
    "HF1": "UNRESOLVED_HEALING_FIELD_WITHOUT_DAMAGE",
}
FC1 = "UNRESOLVED_STATED_CARDS_SHORT"


def mon(card, energy=(), **extra):
    return {"card": card, "energy": list(energy), **extra}


def board(hand=(), *, active=None, bench=(H.RATTATA,), deck=None, discard=(), prizes=6, opponent_hand=(H.POTION, W), opponent_active=None, opponent_bench=(H.RATTATA,),
          opponent_deck=None, opponent_discard=(), opponent_prizes=6, current=0, turn=TURN):
    me = {"active": active or mon(H.HITMONCHAN, (F,)), "bench": list(bench), "hand": list(hand), "deck": list(deck if deck is not None else [W] * 12),
          "discard": list(discard), "prizes": prizes}
    them = {"active": opponent_active or mon(H.HITMONCHAN, (F,)), "bench": list(opponent_bench), "hand": list(opponent_hand),
            "deck": list(opponent_deck if opponent_deck is not None else [W] * 12), "discard": list(opponent_discard), "prizes": opponent_prizes}
    return build_test_state([me, them], turn_number=turn, current_player=current)


def card_of(state, card_id, zone="hand", player=0):
    return next(uid for uid in getattr(state.players[player], zone) if state.cards[uid].card_id == card_id)


def use(state, card_id, player=0, coins=(), **options):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, PlayTrainer(player, card_of(state, card_id, player=player)), **options)


def answer(state, choices, **options):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)), **options)


def answer_with_first_coin(state, choices, side):
    """山札を切ってからコインを投げる処理（エネルギー増幅装置など）で、そのコインが ``side`` になる乱数の seed を 0 から順に探して答える（テスト専用）。"""
    import random
    for seed in range(200):
        probe = state.clone()
        probe.rng = random.Random(seed)
        after = answer(probe, choices)
        flips = [e for e in after.log[len(state.log):] if e["kind"] == "coin_flip"]
        if flips and flips[0]["result"] == side.value:
            return after
    raise AssertionError("条件に合う乱数が見つからない")


def snapshot(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log], repr(state.rng.getstate())


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def PLAY_FIRST(state):
    return PlayTrainer(0, state.players[0].hand[0])


def rejects(test, state, command, code, error=UnsupportedError, **options):
    if callable(command):
        command = command(state)
    before = snapshot(state)
    with test.assertRaises(error) as caught:
        apply_kernel(state, command, **options)
    test.assertEqual(caught.exception.code, code)
    test.assertEqual(snapshot(state), before)
    return caught.exception


def new_events(before, after, *kinds):
    return [e for e in after.log[len(before.log):] if not kinds or e["kind"] in kinds]


def coins(before, after):
    return [e["result"] for e in new_events(before, after, "coin_flip")]


def without_v0_80(registry: EffectRegistry) -> EffectRegistry:
    """v0.80 で加えたトレーナーの登録（30 枚）だけを除いた登録表。"""
    return registry.without_trainers(registry.id, H.V0_80_CARDS)


# ---------------------------------------------------------------- A: ポケモンチェックの途中のきぜつと交代


def pk_board(bench, *, opponent_bench=(H.RATTATA,), ditto=None, prizes=6, opponent_prizes=6):
    me = {"active": mon(H.MACHOP, (DK,), damage=40), "bench": list(bench), "hand": [], "deck": [W] * 12, "prizes": prizes}
    them = {"active": ditto or mon(H.DITTO, damage=30, poison=10), "bench": list(opponent_bench), "hand": [], "deck": [W] * 12, "prizes": opponent_prizes}
    return build_test_state([me, them], turn_number=TURN, current_player=0)


class MidCheckReplacementTest(unittest.TestCase):
    """A: 2 の前にバトル場に出すポケモンで、［へんしん］のメタモンの姿・最大HP が変わるなら PK1。変わらない盤面は進む。"""

    def test_promoted_replacement_changes_ditto_stops_before_damage(self):
        """依頼の再現例: ワンリキー（HP 50。ダメージ 40・悪エネルギー）のベンチがポニータ（HP 40）だけ。メタモン（ワンリキーの姿で最大HP 50・ダメージ 30・どく）。v0.79 は TAKE_PRIZE
        に進み、ポニータを出す答えが MH1 で拒否されて、答えのない決定が残った。"""
        state = pk_board([H.PONYTA])
        after = apply_kernel(state, EndTurn(0))
        self.assertEqual((after.phase, after.halt.code), (Phase.HALTED, MID))
        self.assertEqual(new_events(state, after, "darkness_energy_damage", "poison_damage", "knock_out"), [])
        self.assertEqual((after.players[0].active.damage, after.players[1].active.damage), (40, 30))
        audited(self, after)

    def test_controls_proceed(self):
        """出すポケモンがワンリキー（同じ最大HP 50）なら、どちらの読み方でも同じなので v0.79 と同じに進む（メタモンがいることだけでは止めない）。"""
        cases = {
            "same_hp": pk_board([H.MACHOP]),
            "no_poison": pk_board([H.PONYTA], ditto=mon(H.DITTO, damage=0)),
            "no_ditto": pk_board([H.PONYTA], ditto=mon(H.HITMONCHAN, damage=30, poison=10)),
        }
        for name, state in cases.items():
            with self.subTest(name):
                after = apply_kernel(state, EndTurn(0))
                self.assertIs(after.phase, Phase.TAKE_PRIZE)
                while after.decision is not None:
                    d = after.decision
                    after = answer(after, d.options[:1])
                self.assertIs(after.phase, Phase.MAIN)
                audited(self, after)

    def test_any_promotion_that_changes_stops(self):
        """控えが 2 匹（ワンリキー・ポニータ）なら、ポニータを出す読み方で変わるので止める（出す答えのどれかで変わるなら、答えを決める前に止める）。"""
        after = apply_kernel(pk_board([H.MACHOP, H.PONYTA]), EndTurn(0))
        self.assertEqual((after.phase, after.halt.code), (Phase.HALTED, MID))

    def test_game_ending_reading_with_a_later_knockout_stops(self):
        """場をはなれる読み方で 2 の前に対戦が終わる（相手のサイドが 1 枚）のに、場に残る読み方では 2 のどくでほかのポケモンも HP 以上になるなら、勝ち負けが変わりうるので止める。
        2 で何も HP 以上にならないなら止めない。"""
        ends = pk_board([H.MACHOP], ditto=mon(H.HITMONCHAN, damage=60, poison=10), opponent_prizes=1)
        after = apply_kernel(ends, EndTurn(0))
        self.assertEqual((after.phase, after.halt.code), (Phase.HALTED, MID))
        calm = pk_board([H.MACHOP], ditto=mon(H.HITMONCHAN, damage=0, poison=10), opponent_prizes=1)
        after = apply_kernel(calm, EndTurn(0))
        self.assertNotEqual(after.phase, Phase.HALTED)


# ---------------------------------------------------------------- B: ワザが失敗しても処理する要素とコイン


def steelix_board(defender):
    attacker = {"card": H.STEELIX_PRN, "evolved_from": H.ONIX, "evolved_turn": TURN - 2, "played_turn": TURN - 4, "energy": [H.METAL_ENERGY_NEO1, H.FIGHTING, W]}
    return build_test_state([{"active": attacker, "bench": [H.RATTATA], "hand": [], "deck": [W] * 10},
                             {"active": defender, "bench": [H.RATTATA], "hand": [], "deck": [W] * 10}], turn_number=TURN, current_player=0)


def kakuna(**extra):
    return {"card": H.KAKUNA, "evolved_from": H.WEEDLE, "evolved_turn": TURN - 3, "played_turn": TURN - 5, **extra}


class FailureSurvivingElementTest(unittest.TestCase):
    """B: メタルクラッシュ（コインの「うら」で失敗。どちらでも次の自分の番はワザを使えない）を「ダメージを受けない」相手に使う。"""

    def test_metal_crush_against_harden_stops_in_every_mode_and_coin(self):
        state = steelix_board(kakuna(prevent_damage=TURN - 1))
        for mode in PREFLIGHT_MODES:
            for side in (HD, TL):
                with self.subTest(mode=mode, side=side):
                    rejects(self, with_coin_results(state, side), UseAttack(0, 0), "UNRESOLVED_PREVENTED_COIN_DAMAGE", preflight=mode)

    def test_houndour_comparison_still_stops(self):
        state = build_test_state([{"active": mon(H.HOUNDOUR_NEO4, (F, F)), "bench": [H.RATTATA], "hand": [], "deck": [W] * 10},
                                  {"active": kakuna(prevent_damage=TURN - 1), "bench": [H.RATTATA], "hand": [], "deck": [W] * 10}],
                                 turn_number=TURN, current_player=0)
        for side in (HD, TL):
            rejects(self, with_coin_results(state, side), UseAttack(0, 1), "UNRESOLVED_PREVENTED_COIN_DAMAGE")

    def test_normal_opponent_still_flips_and_locks_on_both_sides(self):
        state = steelix_board(mon(H.HITMONCHAN))
        for side, damage in ((HD, 50), (TL, 0)):
            with self.subTest(side=side):
                after = apply_kernel(with_coin_results(state, side), UseAttack(0, 0))
                self.assertEqual(after.players[1].active.damage, damage)
                self.assertEqual(len(new_events(state, after, "persistent_effect_added")), 1)
                audited(self, after)


# ---------------------------------------------------------------- エフェクトガードのコインの表


def guard_board(defender, *, attacker=None, attack_owner_guard=False):
    me_active = attacker or mon(H.GRIMER, (G, G))
    if attack_owner_guard:
        me_active = {**me_active, "trainers": [(EFFECT_GUARD, TURN + 1)]}
    return build_test_state([{"active": me_active, "bench": [H.RATTATA], "hand": [], "deck": [W] * 10},
                             {"active": defender, "bench": [H.RATTATA], "hand": [], "deck": [W] * 10}], turn_number=TURN, current_player=0)


GUARDED = [(EFFECT_GUARD, TURN)]  # 前の相手の番（プレイヤー 1 の番）に使い、この番の終わりにトラッシュする


class EffectGuardCoinTableTest(unittest.TestCase):
    """エフェクトガードの表: コイン 1 枚で追加のダメージとマヒを決めるねばりつく（ロケット団のベトベター。v0.8 の CoinBonusDamageAndParalyze）。
    でんじは（ダメージはいつも与え、コインはマヒだけを決める）は、エフェクトガードだけで既存の HC3 になる（コインが決める要素がどれも無効）。"""

    def attack(self, state, side, **options):
        return apply_kernel(with_coin_results(state, side), UseAttack(0, 1), **options)

    def test_guard_only_flips_and_blocks_paralysis(self):
        state = guard_board(mon(H.HITMONCHAN, trainers=GUARDED))
        for side, damage in ((HD, 30), (TL, 10)):
            with self.subTest(side=side):
                after = self.attack(state, side)
                self.assertEqual(coins(state, after), [side.value])
                self.assertEqual(after.players[1].active.damage, damage)
                self.assertEqual(after.players[1].active.conditions.names(), ())
                prevented = [e["persistent_effect"] for e in new_events(state, after, "effect_prevented")]
                self.assertEqual(prevented, ["effect_guard"] if side is HD else [])
                audited(self, after)

    def test_damage_prevention_only_flips_and_blocks_damage(self):
        state = guard_board(kakuna(prevent_damage=TURN - 1))
        after = self.attack(state, HD)
        self.assertEqual(coins(state, after), ["heads"])
        self.assertEqual(after.players[1].active.damage, 0)
        self.assertIn("paralysis", after.players[1].active.conditions.names())

    def test_both_stop_with_the_nullified_coin_question(self):
        state = guard_board(kakuna(prevent_damage=TURN - 1, trainers=GUARDED))
        for mode in PREFLIGHT_MODES:
            for side in (HD, TL):
                with self.subTest(mode=mode, side=side):
                    rejects(self, with_coin_results(state, side), UseAttack(0, 1), "UNRESOLVED_PREVENTED_EFFECT_COIN", preflight=mode)

    def test_neither_is_normal(self):
        state = guard_board(mon(H.HITMONCHAN))
        after = self.attack(state, HD)
        self.assertEqual(after.players[1].active.damage, 30)
        self.assertIn("paralysis", after.players[1].active.conditions.names())

    def test_effect_only_coin_with_guard_is_the_existing_hc3(self):
        """でんじは（コイル）のコインはマヒだけを決めるので、エフェクトガードのポケモンには既存の HC3 で止める（新しい問いにしない）。"""
        state = guard_board(mon(H.HITMONCHAN, trainers=GUARDED), attacker=mon(H.MAGNEMITE, (L,)))
        rejects(self, with_coin_results(state, HD), UseAttack(0, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")

    def test_own_attack_effects_trainers_are_not_blocked(self):
        """自分のワザの自分への効果（R団のカビゴンの「たおれこむ」）・トレーナー（ねむれ!ねむれ!）は止めない。"""
        snorlax = guard_board(mon(H.HITMONCHAN), attacker=mon(H.ROCKETS_SNORLAX, (W, W, W, W)), attack_owner_guard=True)
        after = apply_kernel(snorlax, UseAttack(0, 0))
        given = [(e["player"], e["condition"]) for e in new_events(snorlax, after, "special_condition")]
        self.assertEqual(given, [(0, "sleep")])  # 番の終わりのポケモンチェックで回復することはある
        self.assertEqual(new_events(snorlax, after, "effect_prevented"), [])
        trainer = build_test_state([{"active": mon(H.HITMONCHAN), "bench": [], "hand": [H.SLEEP_TRAINER], "deck": [W] * 10},
                                    {"active": mon(H.HITMONCHAN, trainers=GUARDED), "bench": [], "hand": [], "deck": [W] * 10}],
                                   turn_number=TURN, current_player=0)
        after = use(trainer, H.SLEEP_TRAINER, coins=(HD,))
        self.assertIn("sleep", after.players[1].active.conditions.names())

    def test_attach_and_expire(self):
        state = board([EFFECT_GUARD])
        waiting = use(state, EFFECT_GUARD)
        self.assertEqual(waiting.decision.kind, SELECT_POKEMON)
        after = answer(waiting, waiting.decision.options[:1])
        self.assertEqual(len(after.players[0].active.trainers), 1)
        mine = apply_kernel(after, EndTurn(0))
        self.assertEqual(len(mine.players[0].active.trainers), 1)  # 次の相手の番のあいだはついている
        later = apply_kernel(mine, EndTurn(1))
        self.assertEqual(later.players[0].active.trainers, [])
        audited(self, later)


# ---------------------------------------------------------------- 手札から出して使うことの禁止


class HandTrainerLockTest(unittest.TestCase):
    def test_elm_locks_hand_trainers_until_the_end_of_the_next_opponent_turn(self):
        state = board([ELM, H.POTION, H.SWITCH], deck=[H.POTION] * 12, bench=(H.RATTATA,))
        after = use(state, ELM)
        self.assertEqual(len(after.players[0].hand), 7)
        locks = [lock for lock in after.trainer_locks if lock.origin == E.HAND_TRAINER_LOCK]
        self.assertEqual([(lock.player, lock.expires_turn) for lock in locks], [(0, TURN + 1)])
        rejects(self, after, PlayTrainer(0, card_of(after, H.POTION)), "TRAINER_PREVENTED", IllegalActionError)
        their = apply_kernel(after, EndTurn(0))
        self.assertTrue(any(lock.origin == E.HAND_TRAINER_LOCK for lock in their.trainer_locks))
        mine = apply_kernel(their, EndTurn(1))
        self.assertFalse(any(lock.origin == E.HAND_TRAINER_LOCK for lock in mine.trainer_locks))
        audited(self, mine)

    def test_stadium_use_is_not_blocked(self):
        state = board([ELM, LUCKY_STADIUM_NEO], deck=[W] * 12)
        state = use(state, LUCKY_STADIUM_NEO)
        after = use(state, ELM)
        used = apply_kernel(with_coin_results(after, HD), UseStadium(0))
        self.assertEqual(len(new_events(after, used, "stadium_used")), 1)
        self.assertEqual(E.trainer_use_blockers(after, 0, from_hand=False), ())

    def test_pokegear_and_time_capsule_add_the_same_lock(self):
        gear = use(board([POKEGEAR], deck=[H.POTION, W, W, W, W, W, W, W]), POKEGEAR)
        self.assertEqual(gear.decision.kind, TAKE_LOOKED_TRAINER)
        after = answer(gear, gear.decision.options)
        self.assertTrue(any(lock.origin == E.HAND_TRAINER_LOCK for lock in after.trainer_locks))
        capsule = use(board([TIME_CAPSULE], discard=[W, H.RATTATA]), TIME_CAPSULE)
        self.assertEqual(capsule.decision.player, 0)
        after = answer(capsule, ())
        self.assertTrue(any(lock.origin == E.HAND_TRAINER_LOCK for lock in after.trainer_locks))
        audited(self, after)

    def test_borrowing_under_a_hand_lock_is_tl1(self):
        """TL1: 錯乱ジムの「うら」で、手札から出して使うことの禁止を受けているプレイヤーがかわりに使うかは決まらない（使うを選ぶと止める。使わないは答えになる）。"""
        state = board([H.CHAOS_GYM, H.POTION], active=mon(H.HITMONCHAN, (F,), damage=20), opponent_hand=[ELM], current=1, turn=TURN + 1)
        state = use(state, ELM, player=1)
        state = apply_kernel(state, EndTurn(1))
        state = use(state, H.CHAOS_GYM)
        waiting = use(state, H.POTION, coins=(TL,))
        self.assertEqual((waiting.decision.kind, waiting.decision.player), (ACCEPT_REQUEST, 1))
        rejects(self, waiting, ResolveDecision(1, waiting.decision.id, (1,)), NEW_CODES["TL1"])
        declined = answer(waiting, ())
        audited(self, declined)

    def test_rockets_experiment_lock_is_unchanged(self):
        self.assertEqual(E.SELF_TRAINER_LOCK_TURNS, 2)
        self.assertTrue(TrainerUseLock.__dataclass_fields__["origin"].default == "attack")


# ---------------------------------------------------------------- 退化スプレーHYPER


def evolved_board(hand):
    return board(hand, active={"card": H.IVYSAUR, "evolved_from": H.BULBASAUR, "evolved_turn": TURN - 2, "played_turn": TURN - 4, "energy": [G]})


class DevolutionSprayHyperTest(unittest.TestCase):
    def test_devolve_to_hand_and_ban_same_turn_evolution(self):
        state = evolved_board([HYPER])
        waiting = use(state, HYPER)
        after = answer(waiting, waiting.decision.options[:1])
        self.assertEqual(after.cards[after.players[0].active.card].card_id, H.BULBASAUR)
        ivysaur = card_of(after, H.IVYSAUR)
        self.assertEqual([r.kind for r in after.trainer_effects], [EVOLUTION_BAN])
        rejects(self, after, EvolvePokemon(0, ivysaur, after.players[0].active.pokemon_id), "EVOLUTION_PREVENTED", IllegalActionError)
        audited(self, after)
        later = apply_kernel(apply_kernel(after, EndTurn(0)), EndTurn(1))
        self.assertEqual(later.trainer_effects, ())
        evolved = apply_kernel(later, EvolvePokemon(0, card_of(later, H.IVYSAUR), later.players[0].active.pokemon_id))
        self.assertEqual(evolved.cards[evolved.players[0].active.card].card_id, H.IVYSAUR)

    def test_other_devolution_still_dv2(self):
        # 退化スプレー（v0.50）は今までどおり：はがしたカードはトラッシュに置かれ、同じ番の進化は DV2 で止める。
        state = evolved_board([H.DEVOLUTION_SPRAY, H.IVYSAUR])
        waiting = use(state, H.DEVOLUTION_SPRAY)
        waiting = answer(waiting, waiting.decision.options[:1])
        after = answer(waiting, (1,))
        self.assertIn(H.IVYSAUR, [after.cards[uid].card_id for uid in after.players[0].discard])
        self.assertEqual(after.trainer_effects, ())
        rejects(self, after, EvolvePokemon(0, card_of(after, H.IVYSAUR), after.players[0].active.pokemon_id), "UNRESOLVED_EVOLVE_AFTER_DEVOLUTION")

    def test_without_target_hy1(self):
        rejects(self, board([HYPER]), PLAY_FIRST, NEW_CODES["HY1"])


# ---------------------------------------------------------------- 30 枚の登録と文面


class RegistrationTest(unittest.TestCase):
    def test_pool_and_registrations(self):
        extract = read_extract()
        self.assertEqual(tuple(extract["pool_v0_80"]), H.V0_80_CARDS)
        pool = load_card_pool()
        for card_id in H.V0_80_CARDS:
            definition = pool.get(card_id)
            entry = E.DEFAULT_EFFECTS.trainer_entry(card_id)
            with self.subTest(card_id):
                self.assertTrue(definition.supported)
                self.assertIsNotNone(entry)
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                                 (definition.name_ja, definition.trainer_text_ja, definition.trainer_text_ja, "kyuura data/cards.json"))
                self.assertEqual(entry.effect.check(definition), [])

    def test_counts(self):
        pool = load_card_pool()
        supported = [d for d in pool.definitions.values() if d.supported]
        self.assertEqual(len(supported), 1008)  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた
        by_kind = {kind: sum(1 for d in supported if d.category == kind) for kind in ("pokemon", "trainer", "energy")}
        self.assertEqual(by_kind, {"pokemon": 713, "trainer": 259, "energy": 36})  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた
        self.assertEqual(sum(1 for d in supported if E.STADIUM_KIND in d.trainer_kinds), 41)  # v0.82 でエコロジムを加えた  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた

    def test_unsupported_counts(self):
        """kyuura data/engine_targets.json（7d3f4ca）の対象 1,377 件から今の登録を差し引くと、未対応は全対象 404・neo 202・拡張パック以外 202（v0.79 は 434・227・207）。
        ../kyuura がなければ飛ばす。"""
        import json
        import subprocess
        kyuura = ROOT.parent / "kyuura"
        if not (kyuura / ".git").exists():
            self.skipTest("../kyuura がない")
        targets = json.loads(subprocess.check_output(["git", "-C", str(kyuura), "show", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3:data/engine_targets.json"]))
        playable = load_card_pool().playable_ids
        missing = [c for c in targets["cards"] if c["id"] not in playable]
        self.assertEqual((len(targets["cards"]), len(missing), sum(1 for c in missing if c["id"].startswith("neo")),
                          sum(1 for c in missing if c["product_group"] != "expansion_pack")), (1377, 369, 182, 187))  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた

    def test_unregistered_without_the_v0_80_entries(self):
        registry = without_v0_80(E.DEFAULT_EFFECTS)
        pool = load_card_pool()
        for card_id in H.V0_80_CARDS:
            self.assertIsNone(registry.trainer_entry(card_id))
            self.assertIsNotNone(registry.trainer_problem(pool.get(card_id)))

    def test_wrong_texts_are_rejected(self):
        pool = load_card_pool()
        for card_id in H.V0_80_CARDS:
            entry = E.DEFAULT_EFFECTS.trainer_entry(card_id)
            definition = pool.get(card_id)
            other = H.V0_80_CARDS[(H.V0_80_CARDS.index(card_id) + 1) % len(H.V0_80_CARDS)]
            with self.subTest(card_id):
                self.assertNotEqual(entry.effect.check(pool.get(other)), [], f"{card_id} の登録が {other} の文面を受け付ける")
                self.assertEqual(entry.effect.check(definition), [])

    def test_document_exists(self):
        text = DOC.read_text(encoding="utf-8")
        for card_id in H.V0_80_CARDS:
            self.assertIn(card_id, text)


# ---------------------------------------------------------------- カードごと


class DiscardRecoveryTest(unittest.TestCase):
    def test_super_rod(self):
        state = board([SUPER_ROD], discard=[H.RATTATA, H.IVYSAUR, W])
        for side, card_id in ((HD, H.IVYSAUR), (TL, H.RATTATA)):
            with self.subTest(side=side):
                waiting = use(state, SUPER_ROD, coins=(side,))
                self.assertEqual(waiting.decision.kind, RECOVER_POKEMON)
                self.assertEqual([waiting.cards[o].card_id for o in waiting.decision.options], [card_id])
                rejects(self, waiting, ResolveDecision(0, waiting.decision.id, ()), "INVALID_CHOICE_COUNT", IllegalActionError)
                after = answer(waiting, waiting.decision.options)
                self.assertIn(waiting.decision.options[0], after.players[0].hand)
                self.assertEqual(coins(waiting, after), [])  # 答えのあとに投げ直さない
                audited(self, after)
        rejects(self, board([SUPER_ROD], discard=[H.RATTATA]), PLAY_FIRST, NEW_CODES["SRD1"])

    def test_energy_charge(self):
        state = board([ENERGY_CHARGE], discard=[W, H.RAINBOW_ENERGY, H.RATTATA])
        waiting = use(state, ENERGY_CHARGE, coins=(HD,))
        self.assertEqual(waiting.decision.kind, DISCARD_TO_DECK)
        self.assertEqual(len(waiting.decision.options), 2)  # 基本・特殊エネルギーカード
        rejects(self, waiting, ResolveDecision(0, waiting.decision.id, ()), NEW_CODES["UPZ1"])
        after = answer(waiting, waiting.decision.options)
        self.assertEqual([e["kind"] for e in new_events(waiting, after)][:2], ["discard_to_deck", "shuffle"])
        tails = use(state, ENERGY_CHARGE, coins=(TL,))
        self.assertIsNone(tails.decision)
        self.assertEqual(new_events(state, tails, "shuffle"), [])
        rejects(self, board([ENERGY_CHARGE], discard=[H.RATTATA]), PLAY_FIRST, NEW_CODES["UPZ2"])

    def test_super_energy_retrieval_neo(self):
        state = board([SUPER_ENERGY_RETRIEVAL_NEO, H.POTION, H.SWITCH], discard=[W, G, F])
        waiting = use(state, SUPER_ENERGY_RETRIEVAL_NEO)
        waiting = answer(waiting, waiting.decision.options[:2])
        after = answer(waiting, waiting.decision.options)
        self.assertEqual(len([u for u in after.players[0].hand if after.card_def(u).is_basic_energy]), 3)
        audited(self, after)


class DeckSearchTest(unittest.TestCase):
    def test_energy_ark_counts_heads(self):
        state = board([ENERGY_ARK], deck=[W, G, H.RATTATA, F])
        for sides, taken in (((HD, HD), 2), ((HD, TL), 1), ((TL, TL), 0)):
            with self.subTest(sides=sides):
                after = use(state, ENERGY_ARK, coins=sides)
                if taken:
                    self.assertEqual((after.decision.min_choices, after.decision.max_choices), (taken, taken))
                    after = answer(after, after.decision.options[:taken])
                self.assertEqual(len(new_events(state, after, "reveal_from_deck")), taken)
                self.assertEqual(len(new_events(state, after, "shuffle")), 1 if taken else 0)
        rejects(self, board([ENERGY_ARK], deck=[W, H.RATTATA]), PLAY_FIRST, FC1)

    def test_energy_amplifier(self):
        state = board([ENERGY_AMPLIFIER, G], deck=[W, H.RATTATA])
        waiting = use(state, ENERGY_AMPLIFIER)
        after = answer_with_first_coin(waiting, waiting.decision.options, HD)
        self.assertEqual(after.decision.max_choices, 2)  # もどした草エネルギーも選べる
        rejects(self, after, ResolveDecision(0, after.decision.id, ()), NEW_CODES["UPZ1"])
        done = answer(after, after.decision.options[:2])
        audited(self, done)
        rejects(self, board([ENERGY_AMPLIFIER, H.POTION]), PLAY_FIRST, FC1)
        rejects(self, board([ENERGY_AMPLIFIER, H.RAINBOW_ENERGY], deck=[H.RATTATA]), PLAY_FIRST, NEW_CODES["UPZ2"])


class HandDrawTest(unittest.TestCase):
    def test_mary(self):
        state = board([MARY, H.POTION], deck=[W, G, F])
        waiting = use(state, MARY)
        self.assertEqual(len(waiting.decision.options), 3)
        after = answer(waiting, waiting.decision.options[:2])
        self.assertEqual(len(after.players[0].hand), 1)
        rejects(self, board([MARY], deck=[W]), PLAY_FIRST, FC1)

    def test_bills_mail(self):
        after = use(board([BILLS_MAIL, W]), BILLS_MAIL)
        self.assertEqual(len(after.players[0].hand), 4)
        rejects(self, board([BILLS_MAIL, W, W, W, W]), PLAY_FIRST, "TOO_MANY_CARDS_IN_HAND", IllegalActionError)

    def test_time_capsule_each_player(self):
        state = board([TIME_CAPSULE], discard=[W, H.RATTATA, H.POTION], opponent_discard=[G, H.RATTATA])
        waiting = use(state, TIME_CAPSULE)
        self.assertEqual((waiting.decision.player, len(waiting.decision.options)), (0, 2))  # きずぐすりは選べない
        theirs = answer(waiting, waiting.decision.options[:1])
        self.assertEqual(theirs.decision.player, 1)
        audited(self, theirs)
        done = answer(theirs, ())
        self.assertEqual([e["player"] for e in new_events(theirs, done, "shuffle")], [0, 1])
        audited(self, done)


class DeckTopTest(unittest.TestCase):
    def test_pokedex_808(self):
        state = board([POKEDEX_808], deck=[W, G, F, L, P, W])
        waiting = use(state, POKEDEX_808)
        order = tuple(reversed(waiting.decision.options))
        after = answer(waiting, order)
        self.assertEqual(tuple(after.players[0].deck[:5]), order)
        rejects(self, board([POKEDEX_808], deck=[W] * 4), PLAY_FIRST, NEW_CODES["TOP1"])

    def test_slot_game_takes_same_named(self):
        after = use(board([SLOT_GAME], deck=[W, W, W]), SLOT_GAME)
        self.assertEqual(len(new_events(board([SLOT_GAME], deck=[W, W, W]), after, "reveal_from_deck")), 3)
        mixed = use(board([SLOT_GAME], deck=[W, G, F]), SLOT_GAME)
        self.assertEqual(new_events(board([SLOT_GAME], deck=[W, G, F]), mixed, "reveal_from_deck"), [])
        rejects(self, board([SLOT_GAME], deck=[W, W]), PLAY_FIRST, NEW_CODES["TOP1"])

    def test_pokegear_hidden_count(self):
        waiting = use(board([POKEGEAR], deck=[H.POTION, W, H.SWITCH, W, W, W, W]), POKEGEAR)
        self.assertIn(TAKE_LOOKED_TRAINER, HIDDEN_COUNT_KINDS)
        self.assertEqual(observe(waiting, 1)["decision"], {"kind": TAKE_LOOKED_TRAINER, "player": 0})
        rejects(self, board([POKEGEAR], deck=[W] * 6), PLAY_FIRST, NEW_CODES["TOP1"])


class FieldTest(unittest.TestCase):
    def test_reverse_switch_opponent_chooses_my_bench(self):
        state = board([REVERSE_SWITCH], bench=(H.RATTATA, H.MACHOP), opponent_bench=(H.RATTATA,))
        waiting = use(state, REVERSE_SWITCH)
        self.assertEqual(waiting.decision.player, 1)
        mine = answer(waiting, waiting.decision.options[1:])
        self.assertEqual(mine.cards[mine.players[0].active.card].card_id, H.MACHOP)
        self.assertEqual(mine.decision.player, 0)
        done = answer(mine, mine.decision.options)
        self.assertEqual(done.cards[done.players[1].active.card].card_id, H.RATTATA)
        audited(self, done)
        skip = use(board([REVERSE_SWITCH], bench=(), opponent_bench=()), REVERSE_SWITCH)
        self.assertEqual(len(new_events(board([REVERSE_SWITCH], bench=(), opponent_bench=()), skip, "trainer_switch_skipped")), 2)

    def test_pokemon_march(self):
        state = board([MARCH], deck=[H.RATTATA, W, W], opponent_deck=[H.MACHOP, W])
        waiting = use(state, MARCH)
        self.assertEqual((waiting.decision.kind, waiting.decision.player), (BENCH_FROM_DECK, 0))
        theirs = answer(waiting, waiting.decision.options)
        self.assertEqual(theirs.decision.player, 1)
        done = answer(theirs, ())
        self.assertEqual(len(done.players[0].bench), 2)
        self.assertEqual([e["player"] for e in new_events(theirs, done, "shuffle")], [0, 1])
        audited(self, done)
        full = board([MARCH], bench=(H.RATTATA,) * 5, deck=[H.RATTATA], opponent_deck=[W])
        after = use(full, MARCH)
        self.assertEqual([e["reason"] for e in new_events(full, after, "trainer_bench_from_deck_declined")], ["bench_full", "no_target"])
        self.assertEqual([e["player"] for e in new_events(full, after, "shuffle")], [1])


class GuessTest(unittest.TestCase):
    def test_blaines_quiz_2(self):
        state = board([QUIZ_2, H.POTION], deck=[W] * 6)
        waiting = use(state, QUIZ_2)
        self.assertEqual(waiting.decision.kind, QUIZ_CARD)
        asked = answer(waiting, waiting.decision.options)
        self.assertEqual((asked.decision.kind, asked.decision.player), (QUIZ_ANSWER, 1))
        audited(self, asked)
        right = answer(asked, (2,))  # トレーナーカード
        self.assertEqual(len(right.players[1].hand), 4)
        wrong = answer(asked, (0,))
        self.assertEqual(len(wrong.players[0].hand), 3)
        rejects(self, board([QUIZ_2]), PLAY_FIRST, FC1)

    def test_card_flip_game(self):
        state = board([CARD_FLIP], opponent_prizes=6)
        waiting = use(state, CARD_FLIP)
        self.assertEqual(waiting.decision.kind, SELECT_OPPONENT_PRIZE)
        asked = answer(waiting, (0,))
        self.assertNotIn("quiz_card", dict(asked.decision.context))
        audited(self, asked)
        done = answer(asked, (2,))  # エネルギーカード（サイドは炎エネルギー）
        self.assertIn(done.players[1].prizes[0], done.face_up_prizes)
        self.assertEqual(len(done.players[0].hand), 2)
        audited(self, done)

    def test_personality_test(self):
        rejects(self, board([PERSONALITY, W]), PLAY_FIRST, "NO_EVOLUTION_CARD_IN_HAND", IllegalActionError)
        waiting = use(board([PERSONALITY, H.IVYSAUR]), PERSONALITY)
        asked = answer(waiting, waiting.decision.options)
        done = answer(asked, (2,))
        self.assertEqual(new_events(asked, done, "quiz_kind_reveal")[0]["correct"], True)

    def test_rockets_secret_activity(self):
        waiting = use(board([SECRET_ACTIVITY], opponent_hand=(H.POTION, W)), SECRET_ACTIVITY)
        drawn = answer(waiting, waiting.decision.options[:1])
        self.assertEqual((drawn.decision.kind, drawn.decision.player, drawn.decision.options), (SELECT_DRAW_COUNT, 1, (0, 1, 2)))
        done = answer(drawn, (2,))
        self.assertEqual(len(done.players[1].hand), 3)
        rejects(self, board([SECRET_ACTIVITY], opponent_hand=()), PLAY_FIRST, FC1)

    def test_imposter_oaks_invention(self):
        state = board([OAKS_INVENTION], opponent_prizes=3)
        waiting = use(state, OAKS_INVENTION)
        self.assertEqual((waiting.decision.kind, waiting.decision.player), (ACCEPT_REQUEST, 0))
        self.assertIn("hidden", next(e for e in visible_log(waiting, 1) if e["kind"] == "look_at_prizes"))
        done = answer(waiting, (1,))
        self.assertEqual(len(done.players[1].prizes), 3)
        self.assertEqual(new_events(waiting, done, "knock_out", "take_prize"), [])
        audited(self, done)


class ConditionHealTest(unittest.TestCase):
    def test_imakuni_and_dance(self):
        after = use(board([IMAKUNI]), IMAKUNI)
        self.assertIn("confusion", after.players[0].active.conditions.names())
        self.assertIs(after.phase, Phase.MAIN)
        waiting = use(board([DANCE_IMAKUNI]), DANCE_IMAKUNI)
        after = answer(waiting, (0,))
        self.assertIn("poison", after.players[0].active.conditions.names())

    def test_tropical_wind(self):
        state = board([TROPICAL_WIND], active=mon(H.HITMONCHAN, damage=30), opponent_active=mon(H.HITMONCHAN, damage=10))
        heads = use(state, TROPICAL_WIND, coins=(HD,))
        self.assertEqual((heads.players[0].active.damage, heads.players[1].active.damage), (10, 0))
        tails = use(state, TROPICAL_WIND, coins=(TL,))
        self.assertEqual([("sleep" in p.active.conditions.names()) for p in tails.players], [True, True])

    def test_moomoo_milk_and_powder(self):
        state = board([MOOMOO_MILK], active=mon(H.HITMONCHAN, damage=50))
        waiting = use(state, MOOMOO_MILK)
        after = answer(with_coin_results(waiting, HD, HD), waiting.decision.options[:1])
        self.assertEqual(after.players[0].active.damage, 10)
        rejects(self, board([MOOMOO_MILK]), PLAY_FIRST, NEW_CODES["MK1"])
        powder = use(board([POWDER], active=mon(H.HITMONCHAN, damage=50, poison=10)), POWDER, coins=(HD,))
        self.assertEqual((powder.players[0].active.damage, powder.players[0].active.conditions.names()), (30, ()))
        rejects(self, board([POWDER]), PLAY_FIRST, NEW_CODES["BP1"])


class StadiumTest(unittest.TestCase):
    def test_healing_field(self):
        state = use(board([HEALING_FIELD], active=mon(H.HITMONCHAN, damage=30)), HEALING_FIELD)
        after = apply_kernel(with_coin_results(state, HD), UseStadium(0))
        self.assertEqual(after.players[0].active.damage, 10)
        rejects(self, after, UseStadium(0), "STADIUM_ALREADY_USED", IllegalActionError)
        rejects(self, use(board([HEALING_FIELD]), HEALING_FIELD), UseStadium(0), NEW_CODES["HF1"])

    def test_radio_tower(self):
        state = use(board([RADIO_TOWER], deck=[W, G, F]), RADIO_TOWER)
        waiting = apply_kernel(state, UseStadium(0))
        self.assertEqual((waiting.decision.kind, waiting.decision.options), (SELECT_LOOK_COUNT, (0, 1, 2)))
        after = answer(waiting, (2,))
        self.assertEqual(after.players[0].deck, state.players[0].deck)
        self.assertIn("hidden", [e for e in visible_log(after, 1) if e["kind"] == "look_at_deck_top"][-1])
        audited(self, after)

    def test_neo_energy_and_lucky_stadium(self):
        lucky = use(board([LUCKY_STADIUM_NEO]), LUCKY_STADIUM_NEO)
        after = apply_kernel(with_coin_results(lucky, HD), UseStadium(0))
        self.assertEqual(len(after.players[0].hand), 1)
        energy = use(board([ENERGY_STADIUM_NEO], discard=[W]), ENERGY_STADIUM_NEO)
        waiting = apply_kernel(with_coin_results(energy, HD), UseStadium(0))
        self.assertEqual(len(waiting.decision.options), 1)


class SaveRestoreTest(unittest.TestCase):
    def test_waiting_states_survive_copy_and_pickle(self):
        waiting = use(board([TIME_CAPSULE], discard=[W]), TIME_CAPSULE)
        for restored in (waiting.clone(), copy.deepcopy(waiting), pickle.loads(pickle.dumps(waiting))):
            self.assertEqual(snapshot(answer(restored, ())), snapshot(answer(waiting, ())))


if __name__ == "__main__":
    unittest.main()
