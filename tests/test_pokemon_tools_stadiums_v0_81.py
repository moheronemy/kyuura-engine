"""v0.81: v0.80 の追補（2.1: エネルギー増幅装置の段階 1 の選べるものの数の見えない情報・2.2: v0.80 の文書の訂正）と、ポケモンのどうぐ 11 枚・ピントレンズ・
常にはたらくスタジアム 3 枚（docs/pokemon-tools-stadiums-v0.81.md）。

カードはどれも kyuura データの採用（採用したデータのコミット 7d3f4ca。処理に使う文面は kyuura の印刷の文面）。ガイドブックは読んでいない。順番の根拠は
GR-2000-P323-POKEMON-CHECK（ポケモンチェックの順番: 指示されたこと → どく → ねむり → マヒ。どちらの番でもない）・GR-2000-P321-DAMAGE-ORDER（スタジアムは 6 段階）・
GR-2000-P320-COUNTER-MOVE（ダメージカウンターをのせるのはダメージではない）・GR-2000-P320-RECOVERY（とりのぞく）。
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
    Retreat,
    UseAttack,
    check_invariants,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import EXP_ALL_ENERGY, RETURN_TO_DECK, SELECT_POKEMON
from kyuura_engine.observation import (
    HIDDEN_COUNT_KINDS,
    OPTION_MEANINGS,
    PUBLIC_EVENTS,
    observe,
)
from tests import helpers as H
from tests.helpers import apply_kernel, build_test_state, with_coin_results
from tests.test_neo_trainer_components_v0_80 import (
    ENERGY_AMPLIFIER,
    answer,
    audited,
    board,
    card_of,
    mon,
    new_events,
    rejects,
    snapshot,
    use,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "pokemon-tools-stadiums-v0.81.md"
DOC80 = ROOT / "docs" / "neo-trainer-components-v0.80.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
TURN = 7
W, F, G, L, P = H.WATER, H.FIRE, H.GRASS, H.LIGHTNING, H.PSYCHIC
FT = H.FIGHTING

BERRY, BERRY_PRN, BERRY_NIP1, BERRY_NIP2 = "neo1-073", "PRN-004", "NIP1X-008", "NIP2X-008"
GOLD_BERRY, MIRACLE_BERRY, MIRACLE_BERRY_PRN, BALLOON_BERRY = "neo1-079", "neo1-081", "PRN-005", "neo3-055"
FOCUS_BAND, COUNTER_CLAW, EXP_ALL, PINPOINT_LENS = "neo1-088", "neo4-103", "neo4-109", "neo4-104"
BELLSPROUT_TOWER, ROCKETS_HIDEOUT, BUMPY_GYM = "neo1-085", "neo3-057", "neo4-110"
TOOLS = (BERRY, BERRY_PRN, BERRY_NIP1, BERRY_NIP2, GOLD_BERRY, MIRACLE_BERRY, MIRACLE_BERRY_PRN, BALLOON_BERRY, FOCUS_BAND, COUNTER_CLAW, EXP_ALL)
STADIUMS = (BELLSPROUT_TOWER, ROCKETS_HIDEOUT, BUMPY_GYM)
CARDS = TOOLS + (PINPOINT_LENS,) + STADIUMS

NEW_CODES = {
    "BY1": "UNRESOLVED_POKEMON_CHECK_BERRY_ORDER",
    "BB1": "UNRESOLVED_BALLOON_BERRY_FAILED_RETREAT",
    "FB1": "UNRESOLVED_FOCUS_BAND_TIMING",
}
TR1 = "UNRESOLVED_TRAINER_WITHOUT_TARGET"
CP2 = "UNRESOLVED_RETREAT_COST_FLOOR"
G40 = "UNRESOLVED_KO_PREVENTION_ORDER"
C18 = "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT"
CONFUSION_MODIFIERS = "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS"


def tool(card, turn=None):
    return (card, turn)


def attach(state, card_id, pokemon_id, player=0):
    """手札の ``card_id`` を使い、場のポケモン ``pokemon_id`` につける（決定に答える）。"""
    waiting = use(state, card_id, player=player)
    if waiting.decision is None:
        return waiting
    return answer(waiting, (pokemon_id,))


def pid(state, player, where="active", index=0):
    side = state.players[player]
    return side.active.pokemon_id if where == "active" else side.bench[index].pokemon_id


def attack(state, index, *sides, player=0):
    if sides:
        state = with_coin_results(state, *sides)
    return apply_kernel(state, UseAttack(player, index))


class HiddenCountTest(unittest.TestCase):
    """2.1: 手札から種類でしぼったカードを選ぶ決定の、選べるものの数・選ぶ数は、決めるプレイヤーでない人に見せない。"""

    def _amplifier(self, hand, deck):
        return use(board([ENERGY_AMPLIFIER, *hand], deck=deck), ENERGY_AMPLIFIER)

    def test_amplifier_stage_one_hides_the_count(self):
        a = self._amplifier([W, H.RATTATA], [W, G, G])
        b = self._amplifier([W, G], [W, G, H.RATTATA])
        self.assertEqual((a.decision.kind, len(a.decision.options), len(b.decision.options)), (RETURN_TO_DECK, 1, 2))
        for viewer in (1, None):
            with self.subTest(viewer=viewer):
                self.assertEqual(observe(a, viewer)["decision"], observe(b, viewer)["decision"])
                self.assertEqual(observe(a, viewer)["decision"], {"kind": RETURN_TO_DECK, "player": 0})

    def test_pokemon_trader_hides_the_count(self):
        a = use(board([H.POKEMON_TRADER, H.RATTATA, W], deck=[H.MACHOP]), H.POKEMON_TRADER)
        b = use(board([H.POKEMON_TRADER, H.RATTATA, H.MACHOP], deck=[W]), H.POKEMON_TRADER)
        self.assertEqual((len(a.decision.options), len(b.decision.options)), (1, 2))
        for viewer in (1, None):
            self.assertEqual(observe(a, viewer)["decision"], observe(b, viewer)["decision"])

    def test_decider_still_sees_the_count_and_cards(self):
        a = self._amplifier([W, H.RATTATA], [W, G, G])
        view = observe(a, 0)["decision"]
        self.assertEqual(view["option_count"], 1)
        self.assertEqual([option["card_id"] for option in view["options"]], [W])
        self.assertEqual(observation_errors(a), [])

    def test_hand_filtered_kinds_are_hidden(self):
        for kind in ("return_to_deck", "select_evolution_card", "attach_from_hand", "hand_to_active", "discard_from_hand", "opponent_hand_to_deck",
                     "opponent_hand_to_bench"):
            self.assertIn(kind, HIDDEN_COUNT_KINDS)

    def test_stage_two_invalid_answer_and_save_restore(self):
        a = self._amplifier([W, H.RATTATA], [W, G, G])
        rejects(self, a, ResolveDecision(0, a.decision.id, (999,)), "INVALID_CHOICE", error=IllegalActionError)
        for restored in (a.clone(), copy.deepcopy(a), pickle.loads(pickle.dumps(a))):
            for viewer in (0, 1, None):
                self.assertEqual(observe(restored, viewer), observe(a, viewer))
        second = answer(a, a.decision.options)
        if second.decision is not None:
            self.assertIn(second.decision.kind, HIDDEN_COUNT_KINDS)
            self.assertEqual(observe(second, 1)["decision"], {"kind": second.decision.kind, "player": 0})


def observation_errors(state):
    from tests.log_audit import observation_problems

    return observation_problems(state)


class DocCorrectionTest(unittest.TestCase):
    """2.2: v0.80 の文書の訂正（エネルギーアークのコインは 2 枚・デルビルの比べは「とびかかる」・SRD1 はどちらかの種類のカードがないとき）。"""

    def test_v080_document_is_corrected(self):
        text = DOC80.read_text(encoding="utf-8")
        self.assertIn("コイン 2 枚の「おもて」の数", text)
        self.assertNotIn("コイン 3 枚", text)
        self.assertIn("「とびかかる」", text)
        self.assertIn("どちらかの種類のカードがなければ SRD1", text)
        self.assertIn("進化カードかたねポケモンのどちらかがない", text)


class RegistrationTest(unittest.TestCase):
    def test_all_fifteen_are_supported(self):
        pool = load_card_pool()
        for card in CARDS:
            with self.subTest(card=card):
                self.assertIn(card, pool.playable_ids)
                entry = E.DEFAULT_EFFECTS.trainer_entry(card)
                self.assertEqual(entry.effect.check(pool.definitions[card]), [])
                self.assertEqual(entry.text_ja, pool.definitions[card].trainer_text_ja)
        for card in TOOLS:
            self.assertEqual(pool.definitions[card].trainer_kinds, ("pokemon_tool",))
            self.assertIsInstance(E.DEFAULT_EFFECTS.trainer_entry(card).effect, E.PokemonToolEffect)
        self.assertNotIsInstance(E.DEFAULT_EFFECTS.trainer_entry(PINPOINT_LENS).effect, E.PokemonToolEffect)
        self.assertEqual(pool.definitions[PINPOINT_LENS].trainer_kinds, ())

    def test_cards_match_the_helpers_list(self):
        self.assertEqual(CARDS, H.V0_81_CARDS)

    def test_unregistered_without_the_v0_81_entries(self):
        registry = E.DEFAULT_EFFECTS.without_trainers(E.DEFAULT_EFFECTS.id, H.V0_81_CARDS)
        pool = load_card_pool()
        for card_id in H.V0_81_CARDS:
            self.assertIsNone(registry.trainer_entry(card_id))
            self.assertIsNotNone(registry.trainer_problem(pool.get(card_id)))

    def test_wrong_texts_are_rejected(self):
        pool = load_card_pool()
        for card_id in H.V0_81_CARDS:
            entry = E.DEFAULT_EFFECTS.trainer_entry(card_id)
            others = [other for other in H.V0_81_CARDS if pool.get(other).trainer_text_ja != pool.get(card_id).trainer_text_ja]
            with self.subTest(card_id):
                self.assertEqual(entry.effect.check(pool.get(card_id)), [])
                for other in others:
                    self.assertNotEqual(entry.effect.check(pool.get(other)), [], f"{card_id} の登録が {other} の文面を受け付ける")

    def test_tool_header_variants_are_explicit(self):
        pool = load_card_pool()
        self.assertTrue(pool.definitions[BERRY].trainer_text_ja.startswith(E.TOOL_HEADER_IN_PLAY))
        self.assertTrue(pool.definitions[BERRY_NIP1].trainer_text_ja.startswith(E.TOOL_HEADER_FIELD))
        # 書き方を取りちがえた登録は受け付けない（文の正規化をしない）
        wrong = E.CounterBerry(E.TOOL_HEADER_FIELD, "\n", 2)
        self.assertTrue(wrong.check(pool.definitions[BERRY]))
        self.assertTrue(E.CounterBerry(E.TOOL_HEADER_IN_PLAY, "", 2).check(pool.definitions[BERRY]))
        self.assertTrue(E.CounterBerry(E.TOOL_HEADER_IN_PLAY, "\n", 3).check(pool.definitions[BERRY]))
        self.assertTrue(E.CounterBerry("あなたのポケモンにつけて使う。", "\n", 2).check(pool.definitions[BERRY]))

    def test_no_card_id_branches_in_engine(self):
        for path in ("kyuura_engine/engine.py", *sorted(str(p.relative_to(ROOT)) for p in (ROOT / "kyuura_engine" / "resolution").glob("*.py"))):
            text = (ROOT / path).read_text(encoding="utf-8")
            for card in CARDS:
                self.assertNotIn(f'"{card}"', text, path)

    def test_observation_tables(self):
        self.assertEqual(OPTION_MEANINGS[EXP_ALL_ENERGY], "card")
        for event in ("tool_heal", "focus_band", "counter_claw", "tool_damage_counters", "exp_all_declined", "tool_move_energy"):
            self.assertIn(event, PUBLIC_EVENTS)


class ToolCommonTest(unittest.TestCase):
    def test_attach_one_tool_per_pokemon_and_coexist(self):
        state = board([BERRY, GOLD_BERRY, H.PLUSPOWER], bench=(H.RATTATA,))
        active, bench = pid(state, 0), pid(state, 0, "bench")
        waiting = use(state, BERRY)
        self.assertEqual((waiting.decision.kind, waiting.decision.options), (SELECT_POKEMON, (active, bench)))
        once = answer(waiting, (active,))
        self.assertEqual(len(E.attached_tools(once, once.players[0].active)), 1)
        self.assertIsNone(once.players[0].active.trainers[0].discard_at_end_of_turn)
        second = use(once, GOLD_BERRY)
        self.assertEqual(second.decision.options, (bench,))  # どうぐのついているポケモンにはつけられない
        both = answer(second, (bench,))
        plus = apply_kernel(both, PlayTrainer(0, card_of(both, H.PLUSPOWER)))  # どうぐでないついているトレーナーはいっしょにつく
        self.assertEqual(len(plus.players[0].active.trainers), 2)
        audited(self, plus)

    def test_no_target_is_tr1(self):
        state = build_test_state([
            {"active": mon(H.HITMONCHAN, (FT,), trainers=[tool(BERRY)]), "hand": [GOLD_BERRY], "deck": [W] * 10, "prizes": 6},
            {"active": mon(H.HITMONCHAN, (FT,)), "deck": [W] * 10, "prizes": 6},
        ], turn_number=TURN)
        rejects(self, state, PlayTrainer(0, card_of(state, GOLD_BERRY)), TR1)

    def test_two_tools_break_the_invariant(self):
        state = build_test_state([
            {"active": mon(H.HITMONCHAN, (FT,), trainers=[tool(BERRY), tool(GOLD_BERRY)]), "deck": [W] * 10, "prizes": 6},
            {"active": mon(H.HITMONCHAN, (FT,)), "deck": [W] * 10, "prizes": 6},
        ], turn_number=TURN)
        self.assertTrue(any("ポケモンのどうぐが 2 枚" in p for p in check_invariants(state)))

    def test_tool_stays_through_turn_end_and_evolution(self):
        state = board([BALLOON_BERRY, H.MACHOKE], active=mon(H.MACHOP, (FT,), played_turn=1))
        state = attach(state, BALLOON_BERRY, pid(state, 0))
        evolved = apply_kernel(state, EvolvePokemon(0, card_of(state, H.MACHOKE), pid(state, 0)))
        self.assertEqual(len(E.attached_tools(evolved, evolved.players[0].active)), 1)
        ended = apply_kernel(evolved, EndTurn(0))
        self.assertEqual(len(E.attached_tools(ended, ended.players[0].active)), 1)
        audited(self, ended)


def check_board(mine, theirs=None, *, turn=TURN):
    """番のプレイヤー 0 が番を終えるとポケモンチェックになる盤面。"""
    return build_test_state([
        {"active": mine, "bench": [H.RATTATA], "deck": [W] * 10, "prizes": 6},
        {"active": theirs or mon(H.HITMONCHAN, (FT,)), "bench": [H.RATTATA], "deck": [W] * 10, "prizes": 6},
    ], turn_number=turn)


class BerryTest(unittest.TestCase):
    def test_berry_heals_two_and_is_discarded(self):
        state = check_board(mon(H.HITMONCHAN, (FT,), damage=30, trainers=[tool(BERRY)]))
        after = apply_kernel(state, EndTurn(0))
        holder = next(p for p in after.players[0].in_play() if p.pokemon_id == pid(state, 0))
        self.assertEqual(holder.damage, 10)
        self.assertEqual(E.attached_tools(after, holder), ())
        self.assertEqual([e["counters"] for e in new_events(state, after, "tool_heal")], [2])
        self.assertEqual([e["reason"] for e in new_events(state, after, "discard_attached_trainer")], ["used"])
        audited(self, after)

    def test_berry_needs_enough_counters(self):
        for card, damage, kept in ((BERRY, 10, True), (GOLD_BERRY, 30, True), (GOLD_BERRY, 40, False), (BERRY_NIP2, 20, False)):
            with self.subTest(card=card, damage=damage):
                state = check_board(mon(H.HITMONCHAN, (FT,), damage=damage, trainers=[tool(card)]))
                after = apply_kernel(state, EndTurn(0))
                holder = next(p for p in after.players[0].in_play() if p.pokemon_id == pid(state, 0))
                self.assertEqual(bool(E.attached_tools(after, holder)), kept)

    def test_miracle_berry_cures_before_poison(self):
        state = check_board(mon(H.HITMONCHAN, (FT,), damage=10, poison=10, trainers=[tool(MIRACLE_BERRY)]))
        after = apply_kernel(state, EndTurn(0))
        holder = next(p for p in after.players[0].in_play() if p.pokemon_id == pid(state, 0))
        self.assertEqual((holder.damage, holder.conditions.names()), (10, ()))
        self.assertEqual(new_events(state, after, "poison_damage"), [])
        cured = new_events(state, after, "special_conditions_removed")
        self.assertEqual([(e["reason"], e["tool_card"]) for e in cured], [("cured", state.players[0].active.trainers[0].card)])
        audited(self, after)

    def test_miracle_berry_without_condition_stays(self):
        state = check_board(mon(H.HITMONCHAN, (FT,), trainers=[tool(MIRACLE_BERRY_PRN)]))
        after = apply_kernel(state, EndTurn(0))
        holder = next(p for p in after.players[0].in_play() if p.pokemon_id == pid(state, 0))
        self.assertEqual(len(E.attached_tools(after, holder)), 1)

    def test_darkness_energy_and_berry_order_stops_only_when_it_matters(self):
        dk = H.DARKNESS_ENERGY_NEO1
        stops = check_board(mon(H.HITMONCHAN, (FT, dk), damage=10, trainers=[tool(BERRY)]))
        after = apply_kernel(stops, EndTurn(0))
        self.assertEqual((after.phase, after.halt.code), (Phase.HALTED, NEW_CODES["BY1"]))
        same = check_board(mon(H.HITMONCHAN, (FT, dk), damage=30, trainers=[tool(BERRY)]))
        done = apply_kernel(same, EndTurn(0))
        holder = next(p for p in done.players[0].in_play() if p.pokemon_id == pid(same, 0))
        self.assertEqual(holder.damage, 20)
        audited(self, done)


class BalloonAndBumpyTest(unittest.TestCase):
    def _board(self, active, *, stadium=None, confused=False):
        spec = mon(H.HITMONCHAN, (FT, FT), trainers=[tool(BALLOON_BERRY)], **({"confusion": True} if confused else {}))
        state = build_test_state([
            {"active": active or spec, "bench": [H.RATTATA], "hand": [stadium] if stadium else [], "deck": [W] * 10, "prizes": 6},
            {"active": mon(H.HITMONCHAN, (FT,)), "bench": [H.RATTATA], "deck": [W] * 10, "prizes": 6},
        ], turn_number=TURN)
        if stadium:
            state = use(state, stadium)
        return state

    def test_balloon_zero_cost_and_discarded_on_retreat(self):
        state = self._board(None)
        bench = state.players[0].bench[0].card
        energy = state.players[0].active.energy
        self.assertEqual((E.retreat_cost(state, 0).minimum, E.retreat_cost(state, 0).maximum), (0, 0))
        rejects(self, state, Retreat(0, (energy[0],), bench), "WRONG_RETREAT_COST", error=IllegalActionError)
        after = apply_kernel(state, Retreat(0, (), bench))
        moved = after.players[0].bench[0]
        self.assertEqual(E.attached_tools(after, moved), ())
        self.assertEqual([e["reason"] for e in new_events(state, after, "discard_attached_trainer")], ["retreat"])
        self.assertEqual(new_events(state, after, "retreat")[0]["retreat_cost_zeroed"], (state.players[0].active.trainers[0].card,))
        audited(self, after)

    def test_switch_keeps_the_balloon(self):
        state = build_test_state([
            {"active": mon(H.HITMONCHAN, (FT,), trainers=[tool(BALLOON_BERRY)]), "bench": [H.RATTATA], "hand": [H.SWITCH], "deck": [W] * 10, "prizes": 6},
            {"active": mon(H.HITMONCHAN, (FT,)), "deck": [W] * 10, "prizes": 6},
        ], turn_number=TURN)
        after = answer(use(state, H.SWITCH), (pid(state, 0, "bench"),))
        self.assertEqual(len(E.attached_tools(after, after.players[0].bench[0])), 1)

    def test_confused_retreat_with_balloon_is_bb1(self):
        state = self._board(None, confused=True)
        rejects(self, state, Retreat(0, (), state.players[0].bench[0].card), NEW_CODES["BB1"])

    def test_bumpy_gym_adds_one_to_basic_only(self):
        state = build_test_state([
            {"active": mon(H.HITMONCHAN, (FT, FT, FT)), "bench": [H.RATTATA], "hand": [BUMPY_GYM], "deck": [W] * 10, "prizes": 6},
            {"active": mon(H.MACHOKE, (FT,), evolved_from=H.MACHOP), "deck": [W] * 10, "prizes": 6},
        ], turn_number=TURN)
        state = use(state, BUMPY_GYM)
        self.assertEqual(E.retreat_cost(state, 0).maximum, 3)  # たね: 2 + 1
        self.assertEqual(E.retreat_cost(state, 1).maximum, 3)  # 1 進化: 3 のまま

    def test_balloon_and_bumpy_gym_order_is_cp2(self):
        state = self._board(None, stadium=BUMPY_GYM)
        bench = state.players[0].bench[0].card
        cost = E.retreat_cost(state, 0)
        self.assertTrue(cost.floor_ambiguous(0) and cost.floor_ambiguous(1))
        rejects(self, state, Retreat(0, (), bench), CP2)
        rejects(self, state, Retreat(0, (state.players[0].active.energy[0],), bench), CP2)


class DamageStadiumAndLensTest(unittest.TestCase):
    def _attack_board(self, attacker, defender, *, hand=(), my_bench=(H.RATTATA,), their_bench=(H.RATTATA,)):
        return build_test_state([
            {"active": attacker, "bench": list(my_bench), "hand": list(hand), "deck": [W] * 10, "prizes": 6},
            {"active": defender, "bench": list(their_bench), "deck": [W] * 10, "prizes": 6},
        ], turn_number=TURN)

    def test_tower_reduces_colorless_attacks_at_step_six(self):
        state = self._attack_board(mon(H.DRAGONITE, (W,) * 4, evolved_from=[H.DRATINI, H.DRAGONAIR]), mon(H.HITMONCHAN, (FT,)), hand=[BELLSPROUT_TOWER])
        state = use(state, BELLSPROUT_TOWER)
        after = attack(state, 0)
        damage = new_events(state, after, "damage")[0]
        self.assertEqual(damage["amount"], 10)
        self.assertIn((6, state.stadium.card, -30), damage["modifiers"])
        audited(self, after)

    def test_tower_ignores_non_colorless(self):
        state = self._attack_board(mon(H.HITMONCHAN, (FT,)), mon(H.RATTATA), hand=[BELLSPROUT_TOWER])
        state = use(state, BELLSPROUT_TOWER)
        after = attack(state, 0)
        self.assertEqual(new_events(state, after, "damage")[0]["amount"], 40)

    def test_tower_and_confusion_stops(self):
        state = self._attack_board(mon(H.RATTATA, (W,), confusion=True), mon(H.HITMONCHAN, (FT,)), hand=[BELLSPROUT_TOWER])
        state = use(state, BELLSPROUT_TOWER)
        rejects(self, state, UseAttack(0, 0), CONFUSION_MODIFIERS)

    def test_pinpoint_lens_ignores_resistance_and_expires(self):
        state = self._attack_board(mon(H.HITMONCHAN, (FT,)), mon(H.DODUO), hand=[PINPOINT_LENS])
        without = attack(state, 0)
        self.assertEqual(new_events(state, without, "damage")[0]["amount"], 0)
        lensed = attach(state, PINPOINT_LENS, pid(state, 0))
        after = attack(lensed, 0)
        damage = new_events(lensed, after, "damage")[0]
        self.assertEqual((damage["amount"], damage["ignore_resistance"], damage["resistance_ignored_by"]), (20, True, lensed.players[0].active.trainers[0].card))
        self.assertEqual(after.players[0].active.trainers, [])  # 使った番の終わりにトラッシュ
        audited(self, after)

    def test_hideout_raises_max_hp_of_dark_pokemon(self):
        state = self._attack_board(mon(H.DARK_ARBOK, (G,), evolved_from=H.ROCKET_EKANS), mon(H.DARK_ARBOK, (G,), evolved_from=H.ROCKET_EKANS), hand=[ROCKETS_HIDEOUT])
        before = E.max_hp(state, state.players[1].active)
        after = use(state, ROCKETS_HIDEOUT)
        self.assertEqual((before, E.max_hp(after, after.players[0].active), E.max_hp(after, after.players[1].active)), (60, 80, 80))
        self.assertEqual(E.max_hp(after, after.players[0].bench[0]), 30)
        self.assertEqual(observe(after, None)["players"][1]["active"]["hp"], 80)


class FocusBandTest(unittest.TestCase):
    def _board(self, attacker=None, defender=None, *, their_bench=(H.RATTATA,)):
        return build_test_state([
            {"active": attacker or mon(H.HITMONCHAN, (FT, FT, FT)), "bench": [H.RATTATA], "deck": [W] * 10, "prizes": 6},
            {"active": defender or mon(H.RATTATA, trainers=[tool(FOCUS_BAND)]), "bench": list(their_bench), "deck": [W] * 10, "prizes": 6},
        ], turn_number=TURN)

    def test_heads_leaves_ten_and_discards(self):
        state = self._board()
        after = attack(state, 1, HD)
        rattata = after.players[1].active
        self.assertEqual((rattata.damage, after.phase), (20, Phase.MAIN))
        self.assertEqual(E.attached_tools(after, rattata), ())
        self.assertEqual([e["survived"] for e in new_events(state, after, "focus_band")], [True])
        audited(self, after)

    def test_tails_knocks_out(self):
        state = self._board()
        after = attack(state, 1, TL)
        self.assertEqual([e["survived"] for e in new_events(state, after, "focus_band")], [False])
        self.assertEqual(len(new_events(state, after, "knock_out")), 1)

    def test_effect_after_damage_is_fb1(self):
        state = self._board(attacker=mon(H.ELECTABUZZ, (L,)), defender=mon(H.ABRA, damage=20, trainers=[tool(FOCUS_BAND)]))
        rejects(self, state, UseAttack(0, 0), NEW_CODES["FB1"])

    def test_band_with_exp_all_is_g40(self):
        # 同じきぜつの判定の窓で、きあいのハチマキと学習装置がはたらく（どちらを先に処理するかで結果が変わる。既存の G40）
        state = self._board(defender=mon(H.RATTATA, (W,), trainers=[tool(FOCUS_BAND)]), their_bench=(mon(H.MACHOP, trainers=[tool(EXP_ALL)]),))
        rejects(self, state, UseAttack(0, 1), G40)


class CounterClawTest(unittest.TestCase):
    def _board(self, attacker=None, *, my_bench=(H.RATTATA,), claw_damage=0):
        return build_test_state([
            {"active": attacker or mon(H.HITMONCHAN, (FT,)), "bench": list(my_bench), "deck": [W] * 10, "prizes": 6},
            {"active": mon(H.HITMONCHAN, (FT,), damage=claw_damage, trainers=[tool(COUNTER_CLAW)]), "bench": [H.RATTATA], "deck": [W] * 10, "prizes": 6},
        ], turn_number=TURN)

    def test_heads_places_two_counters_and_discards(self):
        state = self._board()
        after = attack(state, 0, HD)
        self.assertEqual(after.players[0].active.damage, 20)
        self.assertEqual(new_events(state, after, "damage")[0]["amount"], 20)
        counters = new_events(state, after, "tool_damage_counters")
        self.assertEqual([(e["counters"], e["target_pokemon_id"]) for e in counters], [(2, pid(state, 0))])
        self.assertEqual(E.attached_tools(after, after.players[1].active), ())
        audited(self, after)

    def test_tails_keeps_the_claw(self):
        state = self._board()
        after = attack(state, 0, TL)
        self.assertEqual(after.players[0].active.damage, 0)
        self.assertEqual(len(E.attached_tools(after, after.players[1].active)), 1)

    def test_not_on_own_turn_and_not_on_bench(self):
        state = build_test_state([
            {"active": mon(H.HITMONCHAN, (FT,)), "bench": [mon(H.RATTATA, trainers=[tool(COUNTER_CLAW)])], "deck": [W] * 10, "prizes": 6},
            {"active": mon(H.HITMONCHAN, (FT,)), "bench": [H.RATTATA], "deck": [W] * 10, "prizes": 6},
        ], turn_number=TURN)
        after = attack(state, 0)
        self.assertEqual(new_events(state, after, "counter_claw"), [])

    def test_double_knockout_that_decides_the_game_is_c18(self):
        state = self._board(mon(H.HITMONCHAN, (FT, FT, FT), damage=60), my_bench=(), claw_damage=50)
        rejects(self, state, UseAttack(0, 1), C18)


class ExpAllTest(unittest.TestCase):
    def _board(self):
        return build_test_state([
            {"active": mon(H.HITMONCHAN, (FT, FT, FT)), "bench": [H.RATTATA], "deck": [W] * 10, "prizes": 6},
            {"active": mon(H.RATTATA, (W, F)), "bench": [mon(H.MACHOP, trainers=[tool(EXP_ALL)])], "deck": [W] * 10, "prizes": 6},
        ], turn_number=TURN)

    def test_move_one_basic_energy_then_discard(self):
        state = self._board()
        waiting = attack(state, 1)
        decision = waiting.decision
        self.assertEqual((decision.kind, decision.player, decision.min_choices, decision.max_choices), (EXP_ALL_ENERGY, 1, 0, 1))
        self.assertEqual(len(decision.options), 2)
        chosen = decision.options[0]
        after = apply_kernel(waiting, ResolveDecision(1, decision.id, (chosen,)))
        machop = next(p for p in after.players[1].in_play() if p.card == state.players[1].bench[0].card)
        self.assertIn(chosen, machop.energy)
        self.assertEqual(E.attached_tools(after, machop), ())
        audited(self, after)

    def test_decline_keeps_the_tool(self):
        state = self._board()
        waiting = attack(state, 1)
        after = apply_kernel(waiting, ResolveDecision(1, waiting.decision.id, ()))
        machop = next(p for p in after.players[1].in_play() if p.card == state.players[1].bench[0].card)
        self.assertEqual(len(E.attached_tools(after, machop)), 1)
        self.assertEqual(len(new_events(waiting, after, "exp_all_declined")), 1)

    def test_save_restore(self):
        waiting = attack(self._board(), 1)
        for restored in (waiting.clone(), copy.deepcopy(waiting), pickle.loads(pickle.dumps(waiting))):
            self.assertEqual(snapshot(apply_kernel(restored, ResolveDecision(1, restored.decision.id, ()))),
                             snapshot(apply_kernel(waiting, ResolveDecision(1, waiting.decision.id, ()))))


if __name__ == "__main__":
    unittest.main()
