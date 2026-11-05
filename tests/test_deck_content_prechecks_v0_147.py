"""v0.147（docs/deck-content-prechecks-v0.147.md）: 特殊能力の使う前の確かめが、本人に見えない山札の中身を読んでいた情報漏れの修正（両モード共通）。

v0.146 までは、次の 8 つの実装の使う前の確かめ（使う宣言・使う機会の答え。コインの前・山札を見る前）が実際の山札を読んだので、同じ公開の情報・同じ持ち主の知識から、対象のカードが
山札とサイドのどちらにあるかで、受理・拒否・コードが分かれた。拒否は状態を変えないので、くりかえせる無料の問い合わせだった。

- 山札に対象があることを読む（PW3）: しんかのひかり（``SearchEvolutionCardToHand``）・てしたをよぶ（``BenchBasicsFromDeckOnEntry``）・［ボスをよぶ］（``SearchNamedTrainerOnEntry``）・
  ［INCREASE］（``BenchNameGroupFromDeckOnEntry``。PSP-INCREASE-ENTRY-PW3-ORACLE）・［FIND］・［JOIN］（``SearchDeckWithBenchLettersToHand``）・［YIELD］・［GIVE］
  （``CoinAttachEnergyFromDeckToOwnPokemon``）→ 配分を読まない下限（``effects.deck_lower_bound_where``・``deck_target_lower_bound``）が 1 より少なければ同じコードで止める
- 山札にあると止めるカードを読む: ［うか］の DV2・GV1（``CoinEvolveSelfFromDeck``。PSP-COCOON-DV2-ORACLE）・ファイヤーブーストのレインボーエネルギー（``CoinAttachFromDeckOnEntry``）
  → 山札にあるかもしれないカード（``effects.possible_deck_cards``。持ち主が知っている集合）にあれば止める
- 止めるカードと止めないカードがある: ［うか］の HP・［YIELD］のレインボーエネルギー・［INCREASE］の GG1 → 止めないカードが山札にあることを下限で確かめられなければ止める

盤面はテスト専用の盤面（``build_test_state``）だけ。比べる検査は ``log_audit.twin_command_problems``（``owner_knowledge``。3 者の観測・ログの写しと、持ち主が知っている所有カードの
集合が同じで、見えない山札とサイドの配分だけが違う状態）。``new_game`` からの合法な操作の列での再現はしていない（docs 2 章）。研究上の問い（PW3・DV2・RB2 など）は決めない。
"""

from __future__ import annotations

import pathlib
import pickle
import unittest

from kyuura_engine import (
    EvolvePokemon,
    PlayBasicToBench,
    PlayTrainer,
    ResolveDecision,
    UsePokemonPower,
    apply_command,
    check_invariants,
)
from kyuura_engine import conventions as C
from kyuura_engine import effects as E
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    ATTACH_FROM_DECK,
    BENCH_FROM_DECK,
    ENTRY_POWER,
    SEARCH_DECK,
)
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from tests import helpers as H
from tests.helpers import build_test_state, with_coin_results
from tests.log_audit import command_outcome, owned_card_ids, twin_command_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "deck-content-prechecks-v0.147.md"
W, F, P = H.WATER, H.FIRE, H.PSYCHIC
UI, UF, UN, UD, UJ, UO, UY = "neo2-023", "neo2-026", "PF2-001", "neo2-025", "PRN-034", H.UNOWN_O, "neo3-033"
QUILAVA_PF1 = "PF1-005"
PW3, DV2, RB2, GG1 = ("UNRESOLVED_POWER_ZERO_CARDS", "UNRESOLVED_EVOLVE_AFTER_DEVOLUTION", "UNRESOLVED_RAINBOW_ATTACH_AS_TYPE",
                      "UNRESOLVED_GOOP_GAS_NEW_POKEMON")
SETS = (None, "CS-KYUURA-PLAY-S2A@1", "CS-KYUURA-PLAY-PO@1")
HIDDEN = (W,) * 6  # うらのサイド 6 枚（対象を含まない）


def mon(card, energy=(), **kw):
    return {"card": card, "energy": list(energy), **kw}


def state_of(me, *, conventions=None):
    them = {"active": mon(H.RATTATA), "bench": [H.RATTATA], "deck": [W] * 10, "prizes": [W] * 6}
    state = build_test_state([me, them], turn_number=7, current_player=0)
    if conventions is not None:
        state.conventions = C.registered_identity(C.parse_key(conventions))
    return state


def swap_hidden(state, card_id, player=0):
    """``card_id`` のカード 1 枚（山札）と、うらのサイドの別のカード 1 枚を入れかえた双子（観測・所有カード・乱数は同じ。テストだけの操作）。"""
    twin = state.clone()
    p = twin.players[player]
    target = next(u for u in p.deck if twin.cards[u].card_id == card_id)
    other = next(u for u in p.prizes if twin.cards[u].card_id != card_id)
    i, j = p.deck.index(target), p.prizes.index(other)
    p.deck[i], p.prizes[j] = other, target
    return twin


def hand_uid(s, cid, player=0):
    return next(u for u in s.players[player].hand if s.cards[u].card_id == cid)


def pid(s, cid, player=0):
    return next(p.pokemon_id for p in s.players[player].in_play() if s.cards[p.card].card_id == cid)


def use_answer(s):
    return ResolveDecision(s.decision.player, s.decision.id, tuple(s.decision.options))


def decline_answer(s):
    return ResolveDecision(s.decision.player, s.decision.id, ())


def declare(s):
    return UsePokemonPower(0, s.players[0].active.pokemon_id, 0)


def snapshot(state):
    return repr(state_to_dict(state, format_version=max(FORMAT_VERSIONS))), [dict(e) for e in state.log], state.rng.getstate()


# 盤面: (名前, 対象のカード, 盤面を作る関数（山札の対象の枚数 n・サイド・集合）, 前の段のコマンド, 確かめるコマンド, 止めるときのコード)
def evolutionary_light(n, prizes=HIDDEN, conventions=None):
    return state_of({"active": mon(H.DARK_DRAGONAIR, played_turn=1, evolved_from=H.ROCKET_DRATINI, evolved_turn=3),
                     "deck": [H.DARK_DRAGONITE] * n + [W] * 5, "prizes": list(prizes)}, conventions=conventions)


def summon_minions(n, prizes=HIDDEN, conventions=None, bench=(H.RATTATA,)):
    return state_of({"active": mon(H.DARK_DRAGONAIR, played_turn=1, evolved_from=H.ROCKET_DRATINI, evolved_turn=3), "bench": list(bench),
                     "hand": [H.DARK_DRAGONITE], "deck": [H.RATTATA] * n + [W] * 5, "prizes": list(prizes)}, conventions=conventions)


def call_for_boss(n, prizes=HIDDEN, conventions=None):
    return state_of({"active": mon(H.GIOVANNIS_MEOWTH, played_turn=1), "hand": [H.GIOVANNIS_PERSIAN], "deck": [H.GIOVANNI] * n + [W] * 5,
                     "prizes": list(prizes)}, conventions=conventions)


def increase(n, prizes=HIDDEN, conventions=None, hand=()):
    return state_of({"active": mon(H.HITMONCHAN), "hand": [UI, *hand], "deck": [H.UNOWN_E] * n + [W] * 5, "prizes": list(prizes)}, conventions=conventions)


def find(n, prizes=HIDDEN, conventions=None, bench=None):
    bench = bench if bench is not None else [mon(UF), mon(UI), mon(UN), mon(UD)]
    return state_of({"active": mon(H.RATTATA), "bench": bench, "deck": [H.POTION] * n + [W] * 5, "prizes": list(prizes)}, conventions=conventions)


def join(n, prizes=HIDDEN, conventions=None):
    return state_of({"active": mon(H.RATTATA), "bench": [mon(UJ), mon(UO), mon(UI), mon(UN)], "deck": [H.HITMONCHAN] * n + [W] * 5,
                     "prizes": list(prizes)}, conventions=conventions)


def yield_(n, prizes=HIDDEN, conventions=None, extra=()):
    return state_of({"active": mon(UY), "deck": [P] * n + list(extra) + [W] * 5, "prizes": list(prizes)}, conventions=conventions)


def cocoon(n, prizes=HIDDEN, conventions=None):
    """キョウのスピアーを退化スプレーで 1 枚はがした（合法な操作）、今の番に退化したキョウのコクーン。山札のキョウのスピアー ``n`` 枚。"""
    s = state_of({"active": mon(H.KOGAS_BEEDRILL, evolved_from=[H.KOGAS_WEEDLE, H.KOGAS_KAKUNA]), "hand": [H.DEVOLUTION_SPRAY],
                  "deck": [H.KOGAS_BEEDRILL] * n + [W] * 5, "prizes": list(prizes)}, conventions=conventions)
    s = apply_command(s, PlayTrainer(0, hand_uid(s, H.DEVOLUTION_SPRAY)))
    s = apply_command(s, ResolveDecision(0, s.decision.id, (s.players[0].active.pokemon_id,)))
    return apply_command(s, ResolveDecision(0, s.decision.id, (1,)))


def fire_boost(n, prizes=(F,) * 6, conventions=None):
    return state_of({"active": mon(QUILAVA_PF1, played_turn=1, evolved_from=H.CYNDAQUIL_PF1, evolved_turn=3), "hand": [H.TYPHLOSION_PF1],
                     "deck": [H.RAINBOW_ENERGY] * n + [F] * 5, "prizes": list(prizes)}, conventions=conventions)


def evolve_into(card):
    return lambda s: EvolvePokemon(0, hand_uid(s, card), s.players[0].active.pokemon_id)


def bench_i(s):
    return PlayBasicToBench(0, hand_uid(s, UI))


def declare_at(card):
    return lambda s: UsePokemonPower(0, pid(s, card), 0)


# (名前, 対象, 盤面, 前の段, 確かめる段, コード)。対象のカード 1 枚が山札（双子はサイド）
LOWER_BOUND = (
    ("しんかのひかり", H.DARK_DRAGONITE, evolutionary_light, (), declare, PW3),
    ("てしたをよぶ", H.RATTATA, summon_minions, (evolve_into(H.DARK_DRAGONITE),), use_answer, PW3),
    ("ボスをよぶ", H.GIOVANNI, call_for_boss, (evolve_into(H.GIOVANNIS_PERSIAN),), use_answer, PW3),
    ("INCREASE", H.UNOWN_E, increase, (bench_i,), use_answer, PW3),
    ("FIND", H.POTION, find, (), declare_at(UF), PW3),
    ("JOIN", H.HITMONCHAN, join, (), declare_at(UJ), PW3),
    ("YIELD", P, yield_, (), declare, PW3),
)
POSSIBLE = (
    ("うか DV2", H.KOGAS_BEEDRILL, cocoon, (), declare, DV2),
    ("ファイヤーブースト", H.RAINBOW_ENERGY, fire_boost, (evolve_into(H.TYPHLOSION_PF1),), use_answer, RB2),
)


def before(case, state):
    for step in case[3]:
        state = apply_command(state, step(state))
    return state


class TwinTest(unittest.TestCase):
    """修正の前に漏れを確かめた盤面（docs 2 章の表）: 対象 1 枚が山札の状態と、サイドの 1 枚と入れかえた双子に同じコマンドを送る。今はどの集合でも受理・拒否・コード・理由の文が同じ。"""

    def test_every_case_is_the_same_wherever_the_card_is(self):
        for case in (*LOWER_BOUND, *POSSIBLE):
            name, card, build, steps, check, code = case
            for conventions in SETS:
                with self.subTest(name=name, conventions=conventions):
                    state = build(1, conventions=conventions)
                    twin = swap_hidden(state, card)
                    self.assertEqual(owned_card_ids(twin, 0), owned_card_ids(state, 0))
                    commands = [*steps, check]
                    self.assertEqual(twin_command_problems([state, twin], commands, owner_knowledge=True), [])
                    outcomes = {command_outcome(s, check(s))[0] for s in (before(case, state), before(case, twin))}
                    self.assertEqual(len(outcomes), 1, outcomes)
                    (outcome,) = outcomes
                    self.assertEqual(outcome[:2], ("UnsupportedError", code))  # 1 枚では、どちらも止める（保守的な制限）

    def test_reasons_carry_no_card_identity(self):
        """理由の文は決まった文（カードの uid・山札の位置を書かない）。v0.146 までの RB2 は uid の並びを書いた。"""
        for case in (*LOWER_BOUND, *POSSIBLE):
            name, card, build, _steps, check, code = case
            with self.subTest(name=name):
                state = before(case, build(1))
                reason = command_outcome(state, check(state))[0][2]
                uids = [u for u in state.players[0].deck if state.cards[u].card_id == card]
                self.assertNotIn(f"[{uids[0]}]", reason)
                self.assertNotIn(f"{uids[0]},", reason)
                if code == PW3:
                    self.assertIn(E.DECK_TARGET_UNCONFIRMED_DETAIL, reason)


class LowerBoundTest(unittest.TestCase):
    """下限 = 本人に見えない対象の枚数 K − 山札の外の見えないカード C。サイド 1 枚（C = 1）なら K = 1 は止め、K = 2 は受理（双子も同じ）。サイド 0 枚なら K = 1 で受理。"""

    def test_boundary_with_one_hidden_prize(self):
        for case in LOWER_BOUND:
            name, card, build, steps, check, code = case
            for n, accepted in ((0, False), (1, False), (2, True)):
                with self.subTest(name=name, n=n):
                    state = before(case, build(n, prizes=(W,)))
                    outcome = command_outcome(state, check(state))[0]
                    self.assertEqual(outcome[0] == "accepted", accepted, outcome[:2])
                    if not accepted:
                        self.assertEqual(outcome[1], code)
                    if n:
                        raw = build(n, prizes=(W,))
                        self.assertEqual(twin_command_problems([raw, swap_hidden(raw, card)], [*steps, check], owner_knowledge=True), [])

    def test_no_hidden_prizes_accepts_one_card(self):
        for case in LOWER_BOUND:
            name, _card, build, _steps, check, _code = case
            with self.subTest(name=name):
                state = before(case, build(1, prizes=()))
                self.assertEqual(command_outcome(state, check(state))[0], ("accepted",))

    def test_six_hidden_prizes_need_seven(self):
        """サイドがうら 6 枚の間は、見えない対象が 7 枚以上ないと使えない（実際には山札に 6 枚あっても止める保守的な制限）。"""
        _name, _card, build, _steps, check, _code = LOWER_BOUND[0]
        for n, accepted in ((6, False), (7, True)):
            with self.subTest(n=n):
                state = build(n)
                self.assertEqual(command_outcome(state, check(state))[0][0] == "accepted", accepted)


class AcceptedPathTest(unittest.TestCase):
    """受理したら、そのあとの決定（山札を見たあと）に選べるカードが必ずある（先読みと実際の実行が一致する）。拒否は状態・乱数・ログを変えず、くりかえしても同じ。"""

    def test_accepted_declarations_reach_a_decision_with_a_choice(self):
        expected = {"しんかのひかり": SEARCH_DECK, "てしたをよぶ": BENCH_FROM_DECK, "ボスをよぶ": SEARCH_DECK, "INCREASE": BENCH_FROM_DECK, "FIND": SEARCH_DECK,
                    "JOIN": SEARCH_DECK}
        for case in LOWER_BOUND:
            name, card, build, _steps, check, _code = case
            with self.subTest(name=name):
                state = before(case, build(2, prizes=(W,)))
                if name == "YIELD":
                    state = with_coin_results(state, CoinSide.HEADS)
                done = apply_command(state, check(state))
                self.assertEqual(check_invariants(done), [])
                self.assertEqual(done.decision.kind, expected.get(name, ATTACH_FROM_DECK))
                self.assertTrue(any(done.cards[o].card_id == card for o in done.decision.options))

    def test_rejection_changes_nothing_and_repeats(self):
        for case in (*LOWER_BOUND, *POSSIBLE):
            name, _card, build, _steps, check, _code = case
            with self.subTest(name=name):
                state = before(case, build(1))
                first = snapshot(state)
                outcomes = {command_outcome(state, check(state))[0] for _ in range(3)}
                self.assertEqual(len(outcomes), 1)
                self.assertEqual(snapshot(state), first)

    def test_declining_an_entry_power_is_still_accepted(self):
        """使う機会の決定で「使わない」は、どの配分でも受理する（使うかは持ち主が決める。v0.43）。"""
        for case in (*LOWER_BOUND, *POSSIBLE):
            name, card, build, steps, check, _code = case
            if check is not use_answer:
                continue
            with self.subTest(name=name):
                state = build(1)
                self.assertEqual(twin_command_problems([state, swap_hidden(state, card)], [*steps, decline_answer], owner_knowledge=True), [])
                offered = before(case, state)
                self.assertEqual(offered.decision.kind, ENTRY_POWER)
                self.assertEqual(command_outcome(offered, decline_answer(offered))[0], ("accepted",))

    def test_save_and_restore_keep_the_result(self):
        for case in (*LOWER_BOUND, *POSSIBLE):
            name, _card, build, _steps, check, _code = case
            with self.subTest(name=name):
                state = before(case, build(1))
                restored = pickle.loads(pickle.dumps(state))
                self.assertEqual(command_outcome(restored, check(restored))[0], command_outcome(state, check(state))[0])


class PossiblePresenceTest(unittest.TestCase):
    """山札にあると止めるカード（［うか］の DV2・ファイヤーブーストのレインボーエネルギー）は、山札にあるかもしれないカード（持ち主が知っている集合）で決める。"""

    def test_card_only_in_the_prizes_still_stops(self):
        for case in POSSIBLE:
            name, card, build, _steps, check, code = case
            with self.subTest(name=name):
                twin = before(case, swap_hidden(build(1), card))
                self.assertEqual(command_outcome(twin, check(twin))[0][:2], ("UnsupportedError", code))

    def test_no_such_card_unseen_is_accepted(self):
        for case in POSSIBLE:
            name, _card, build, _steps, check, _code = case
            with self.subTest(name=name):
                state = before(case, build(0))
                self.assertEqual(command_outcome(state, check(state))[0], ("accepted",))

    def test_possible_deck_cards_is_owner_knowledge(self):
        state = cocoon(1)
        twin = swap_hidden(state, H.KOGAS_BEEDRILL)
        self.assertEqual(E.possible_deck_cards(state, 0), E.possible_deck_cards(twin, 0))
        self.assertEqual(sorted(E.possible_deck_cards(state, 0)), sorted([*state.players[0].deck, *state.players[0].prizes]))


class MixedStopTest(unittest.TestCase):
    """止めるカードと止めないカードがある経路: 止めないカードが山札にあることを下限で確かめられなければ止める。"""

    def test_yield_rainbow_only_possible_is_rb2_in_both_twins(self):
        state = yield_(0, extra=(H.RAINBOW_ENERGY,))
        twin = swap_hidden(state, H.RAINBOW_ENERGY)
        self.assertEqual(twin_command_problems([state, twin], [declare], owner_knowledge=True), [])
        self.assertEqual(command_outcome(state, declare(state))[0], ("UnsupportedError", RB2, E.rainbow_possible_in_deck_error(P_TYPE).message))

    def test_yield_with_a_confirmed_psychic_energy_offers_the_rainbow_as_a_stop_choice(self):
        state = with_coin_results(yield_(2, prizes=(W,), extra=(H.RAINBOW_ENERGY,)), CoinSide.HEADS)
        done = apply_command(state, declare(state))
        rainbow = next(o for o in done.decision.options if done.cards[o].card_id == H.RAINBOW_ENERGY)
        self.assertEqual(done.decision.context_value("unresolved_choices"), (rainbow,))  # 山札を見たあとの決定（本人が見る）は実際の山札で決める

    def test_increase_under_goop_gas_stops_with_the_fixed_reason(self):
        """まきちらせ!ベトベトガスのもとでベンチに出したアンノーンI（ガスのあとに出すと GG1 で出せないので、出したあとにガスを使う）。山札のアンノーンを持ち主が確かめられても、
        ベンチに出しても止めないカードを確かめられないので GG1（理由の文は決まった文。v0.146 までは山札のカードの名前・uid を書いた）。"""
        state = increase(2, prizes=(), hand=(H.GOOP_GAS_ATTACK,))
        offered = apply_command(state, bench_i(state))
        declined = apply_command(offered, decline_answer(offered))
        gas = apply_command(declined, PlayTrainer(0, hand_uid(declined, H.GOOP_GAS_ATTACK)))
        use = E.PowerUse(0, gas.players[0].bench[0].pokemon_id, E.PowerKey(UI, 0))
        problem = E.BenchNameGroupFromDeckOnEntry().accept_problem(gas, use)
        self.assertEqual(problem.code, GG1)
        self.assertIn(E.BENCH_ENTRY_UNCONFIRMED_DETAIL, problem.message)
        for uid in gas.players[0].deck:
            self.assertNotIn(f"カード {uid}", problem.message)


class KeptStopsTest(unittest.TestCase):
    """公開の情報で決まる止め方・使えない条件は変えていない。"""

    def test_public_conditions_are_unchanged(self):
        full = summon_minions(3, prizes=(), bench=(H.RATTATA,) * 5)
        offered = apply_command(full, evolve_into(H.DARK_DRAGONITE)(full))
        outcome = command_outcome(offered, use_answer(offered))[0]
        self.assertEqual(outcome[:2], ("UnsupportedError", PW3))
        self.assertIn("ベンチに空きがない", outcome[2])
        missing = find(3, prizes=(), bench=[mon(UF), mon(UI), mon(UN)])
        self.assertEqual(command_outcome(missing, declare_at(UF)(missing))[0][:2], ("IllegalActionError", "REQUIRED_BENCH_POKEMON_MISSING"))


class RemainingAttackLeakTest(unittest.TestCase):
    """直していない漏れの記録（PSP-ATTACK-DECK-EVOLUTION-PREFLIGHT-ORACLE。docs 4 章）: 山札から進化カードを重ねるワザの宣言の前の先読みは、実際の山札の組で DV2 を確かめる
    （resolution/programs.py。この版では変えていない）。直したら、このテストを修正の確かめに替える。"""

    def test_waterfall_evolution_declaration_still_depends_on_the_deck(self):
        from kyuura_engine import UseAttack

        s = state_of({"active": mon(H.GYARADOS, (W, W, W), evolved_from=[H.ROCKET_MAGIKARP]), "hand": [H.DEVOLUTION_SPRAY], "deck": [H.GYARADOS] + [W] * 5,
                      "prizes": list(HIDDEN)})
        s = apply_command(s, PlayTrainer(0, hand_uid(s, H.DEVOLUTION_SPRAY)))
        s = apply_command(s, ResolveDecision(0, s.decision.id, (s.players[0].active.pokemon_id,)))
        s = apply_command(s, ResolveDecision(0, s.decision.id, (1,)))
        self.assertEqual(s.cards[s.players[0].active.card].card_id, H.ROCKET_MAGIKARP)
        twin = swap_hidden(s, H.GYARADOS)
        outcomes = [command_outcome(x, UseAttack(0, 1))[0][:2] for x in (s, twin)]
        self.assertEqual(outcomes, [("UnsupportedError", DV2), ("accepted",)])
        self.assertTrue(twin_command_problems([s, twin], [UseAttack(0, 1)], owner_knowledge=True))


P_TYPE = E.EnergyType.PSYCHIC


class DocumentTest(unittest.TestCase):
    def test_document_records_the_fix(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("PSP-INCREASE-ENTRY-PW3-ORACLE", "PSP-COCOON-DV2-ORACLE", "PSP-DECK-CONTENT-PRECHECKS", "deck_lower_bound_where", "possible_deck_cards",
                       "PSP-ATTACK-DECK-EVOLUTION-PREFLIGHT-ORACLE"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
