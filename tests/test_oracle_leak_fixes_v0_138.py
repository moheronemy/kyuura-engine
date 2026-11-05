"""v0.138: 遺跡の石版の拒否の理由の文・エネルギー増幅装置の UPZ2 による情報漏れの修正（PSP-RUIN-WALL-BLOCKED-REASON-ORACLE・PSP-UPZ2-ENERGY-AMPLIFIER-ORACLE。
docs/oracle-leak-fixes-v0.138.md）。

- 遺跡の石版（neo2-054・neo2-057）: v0.137 までは、ベトベトガスなどのもとで山札の候補のアンノーンがどれもベンチに出すと止めるとき、拒否の理由の文に最後に確かめた山札のカードの
  名前・uid・特殊能力の名前を書いた（受理・コードは配分によらなかった）。v0.138 は、ベンチに出しても止めないカードが山札にあることを、配分を読まない下限
  （``effects.bench_entry_unconfirmed``）で確かめ、確かめられなければ止める効果のコードと決まった文で止める
- エネルギー増幅装置（neo4-102）: v0.137 までは、使う宣言と段階 1（手札からもどすカード）の答えの UPZ2 が、実際の山札に基本エネルギーカードがあるかを読んだ。v0.138 は、
  基本エネルギーカードをもどす答えはいつも止めず、特殊エネルギーカードをもどす答えは配分を読まない下限（``deck_target_lower_bound``）が 1 以上のときだけ止めない

比べる検査（``log_audit.twin_command_problems``。``owner_knowledge``）は、3 者の観測・ログの写しと、持ち主が知っている所有カードの集合が同じで、見えない山札とサイドの配分だけが
違う状態に、同じ操作の列を送る。テスト専用の盤面（``build_test_state``）と、合法な操作の列（``new_game`` から・延長戦の区間）を分けて書く。
"""

from __future__ import annotations

import copy
import pathlib
import pickle
import random
import unittest
from collections import Counter

from kyuura_engine import (
    EndTurn,
    Phase,
    PlayTrainer,
    ResolveDecision,
    StartSuddenDeath,
    UseAttack,
    apply_command,
    check_invariants,
    new_game,
)
from kyuura_engine import effects as E
from kyuura_engine.decisions import (
    ACCEPT_REQUEST,
    BENCH_FROM_DECK,
    REACTION_POWER,
    RETURN_TO_DECK,
    SEARCH_DECK,
)
from kyuura_engine.effects import CardFilter
from kyuura_engine.observation import observe, visible_log
from tests.helpers import (
    CHAOS_GYM,
    DROWZEE,
    FIRE,
    GOOP_GAS_ATTACK,
    GRASS,
    HITMONCHAN,
    KOFFING_ES2,
    MACHOP,
    RATTATA,
    SABRINAS_GASTLY,
    SABRINAS_HAUNTER_GD6,
    H,
    T,
    build_test_state,
    finish_setup,
    with_coin_results,
)
from tests.log_audit import (
    command_outcome,
    owned_card_ids,
    serialization_problems,
    twin_command_problems,
)
from tests.test_deck_search_oracle_v0_137 import (
    ES_DECK,
    OPPONENT_DECK,
    PSYCHIC,
    SLOWKING,
    SLOWPOKE,
    card_in_hand,
    fingerprint,
    resolve,
    split_board,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "oracle-leak-fixes-v0.138.md"

ST1 = E.SEARCH_TRAINER_WITHOUT_TARGET_CODE
UPZ1, UPZ2, FC1 = E.UP_TO_ZERO_CODE, E.UP_TO_WITHOUT_TARGET_CODE, E.STATED_CARDS_SHORT_CODE
GG1, MG1, DW1 = E.GOOP_GAS_SCOPE_CODE, E.STRANGE_GAS_SCOPE_CODE, E.DARK_WAVE_SCOPE_CODE
WALLS = ("neo2-054", "neo2-057")
UNOWN_E, UNOWN_O, UNOWN_R, UNOWN_L = "PF2-002", "PF2-003", "PRN-035", "neo4-050"
AMP, DCE, RAINBOW = "neo4-102", "PMCG1-096", "PMCG4-065"
GAS_REASONS = {GG1: E.GOOP_GAS_SCOPE_REASON, MG1: E.STRANGE_GAS_SCOPE_REASON, DW1: E.DARK_WAVE_SCOPE_REASON}
UNOWN = CardFilter("basic_pokemon", name_group="アンノーン")
BASIC_ENERGY = CardFilter("basic_energy")


def answer_card(card_id):
    """決定の選べるもののうち、カードの id が ``card_id`` のいちばん前のものを答える操作（状態を受け取る関数）。"""
    return lambda s: ResolveDecision(s.decision.player, s.decision.id, (next(u for u in s.decision.options if s.cards[u].card_id == card_id),))


def play_card(card_id):
    return lambda s: PlayTrainer(s.current_player, card_in_hand(s, card_id))


def with_gas(state, gas, actor):
    """``gas`` の効果がはたらく状態（どれも合法な操作）。GG1: ``actor`` が手札のまきちらせ!ベトベトガスを使う。MG1: 相手のドガース（ES2-003）の「ふしぎなガス」（「おもて」）で
    ``actor`` の場に与え、``actor`` の番になる。DW1: 相手のナツメのゲンガー（GD6-008）の「やみのはどう」で、``actor`` の番になる。"expired": ``actor`` がベトベトガスを使い、
    番を終え、相手も番を終えて、効果が消えたあとの ``actor`` の番。"""
    if gas in (GG1, "expired"):
        state = apply_command(state, PlayTrainer(actor, card_in_hand(state, GOOP_GAS_ATTACK, actor)))
        if gas == "expired":
            state = apply_command(state, EndTurn(actor))
            state = apply_command(state, EndTurn(1 - actor))
            assert not state.trainer_effects and state.current_player == actor
        return state
    if gas in (MG1, DW1):
        attacker = 1 - actor
        state = apply_command(with_coin_results(state, H) if gas == MG1 else state, UseAttack(attacker, 0))
        assert state.current_player == actor and state.trainer_effects, state.trainer_effects
    return state


GAS_ATTACKERS = {MG1: {"card": KOFFING_ES2, "energy": [GRASS, GRASS]},
                 DW1: {"card": "GD6-008", "energy": [PSYCHIC, PSYCHIC], "evolved_from": [SABRINAS_GASTLY, SABRINAS_HAUNTER_GD6]}}


def wall_board(wall, deck_unowns, prize_unowns, gas=None, *, actor=0, prizes=None, bench=(), deck_size=8):
    """テスト専用の盤面から合法な操作で着いた ``actor`` の番（``with_gas``）。山札は詰め物（コラッタ）で上と下をはさんだ ``deck_unowns``（番の初めに引くのは詰め物）、サイドは
    ``prize_unowns`` とスリープ（``prizes`` 枚まで）。手札は遺跡の石版（GG1・"expired" ならまきちらせ!ベトベトガスも）。比べる状態は、見えないアンノーンの多重集合と枚数を同じに
    して作る。"""
    prizes = len(prize_unowns) if prizes is None else prizes
    fill = deck_size - len(deck_unowns)
    deck = [RATTATA] * (fill - fill // 2) + list(deck_unowns) + [RATTATA] * (fill // 2)
    me = {"active": HITMONCHAN, "bench": list(bench), "hand": [wall] + ([GOOP_GAS_ATTACK] if gas in (GG1, "expired") else []), "deck": deck,
          "prizes": list(prize_unowns) + [DROWZEE] * (prizes - len(prize_unowns))}
    them = {"active": GAS_ATTACKERS.get(gas, MACHOP), "deck": [RATTATA] * 10}
    first = 1 - actor if gas in (MG1, DW1) else actor
    state = build_test_state([me, them] if actor == 0 else [them, me], current_player=first, turn_number=(7 if gas in (MG1, DW1) else 3) + first)
    return with_gas(state, gas, actor)


def wall_splits(wall, hidden, prizes, gas=None, **kw):
    """見えないアンノーン ``hidden``（カードの id の並び）のうち、サイドに置く ``prizes`` 枚の選び方をすべて試した状態（並びの順は配分によらない）。"""
    seen, states = set(), []
    n = len(hidden)
    for mask in range(1 << n):
        chosen = [hidden[i] for i in range(n) if mask >> i & 1]
        if len(chosen) != min(prizes, n):
            continue
        rest = [hidden[i] for i in range(n) if not mask >> i & 1]
        key = (tuple(sorted(chosen)), tuple(sorted(rest)))
        if key in seen:
            continue
        seen.add(key)
        states.append(wall_board(wall, sorted(rest), sorted(chosen), gas, prizes=prizes, **kw))
    return states


def expected_gas_reason(code):
    return f"{GAS_REASONS[code]}。{E.BENCH_ENTRY_UNCONFIRMED_DETAIL}"


# ---------------------------------------------------------------- 1. 遺跡の石版


class RuinWallTwinTest(unittest.TestCase):
    def test_gas_rejection_does_not_depend_on_the_split(self):
        """GG1・MG1・DW1 のもとで、見えないアンノーンの山札とサイドの配分だけが違う状態に同じ使う宣言を送ると、拒否・コード・理由の文が同じ（見る人 0・1・観戦者）。理由の文は
        止める効果の決まった文で、カードの名前・uid・特殊能力の名前を書かない。修正の前は理由の文が違った（docs 2 章）。"""
        for wall in WALLS:
            for gas in (GG1, MG1, DW1):
                for hidden, prizes in (([UNOWN_E, UNOWN_R], 1), ([UNOWN_E, UNOWN_O, UNOWN_R], 2), ([UNOWN_E, UNOWN_O, UNOWN_R, UNOWN_L], 3),
                                       ([UNOWN_E, UNOWN_E, UNOWN_R], 1)):
                    with self.subTest(wall=wall, gas=gas, hidden=hidden, prizes=prizes):
                        states = wall_splits(wall, hidden, prizes, gas)
                        self.assertGreaterEqual(len(states), 2)
                        self.assertEqual(twin_command_problems(states, [play_card(wall)], owner_knowledge=True), [])
                        reasons = set()
                        for state in states:
                            outcome = command_outcome(state, play_card(wall)(state))[0]
                            self.assertEqual(outcome[:2], ("UnsupportedError", gas))
                            reasons.add(outcome[2])
                        self.assertEqual(reasons, {expected_gas_reason(gas)})
                        for state in states:
                            for uid in (*state.players[0].deck, *state.players[0].prizes):
                                self.assertNotIn(state.card_def(uid).name_ja, expected_gas_reason(gas))
                                for power in state.card_def(uid).powers:
                                    self.assertNotIn(power.name_ja, expected_gas_reason(gas))

    def test_seat_swap(self):
        for wall in WALLS:
            for gas in (GG1, MG1):
                with self.subTest(wall=wall, gas=gas):
                    states = wall_splits(wall, [UNOWN_E, UNOWN_R], 1, gas, actor=1)
                    self.assertEqual(twin_command_problems(states, [play_card(wall)], owner_knowledge=True), [])
                    self.assertEqual(command_outcome(states[0], play_card(wall)(states[0]))[0][:2], ("UnsupportedError", gas))

    def test_rejection_is_pure_and_repeatable(self):
        """拒否は状態・乱数・ログを変えず、何度送っても同じ（くりかえして配分を探れない）。"""
        for wall in WALLS:
            for state in wall_splits(wall, [UNOWN_E, UNOWN_R], 1, GG1):
                before = fingerprint(state)
                outcomes = {command_outcome(state, play_card(wall)(state))[0] for _ in range(4)}
                self.assertEqual(len(outcomes), 1)
                self.assertEqual(fingerprint(state), before)

    def test_without_active_gas_accepts_and_completes(self):
        """止める効果がない（はたらいていない・期限が切れた）なら、今までどおり使え、選ぶ → ベンチ → 切る → トラッシュまで進む（配分によらず受理）。"""
        for wall in WALLS:
            for gas in (None, "expired"):
                with self.subTest(wall=wall, gas=gas):
                    states = wall_splits(wall, [UNOWN_E, UNOWN_R], 1, gas)
                    self.assertEqual(twin_command_problems(states, [play_card(wall)], owner_knowledge=True), [])
                    for state in states:
                        self.assertIsNone(E.bench_entry_unconfirmed(state, 0, UNOWN))
                        asked = apply_command(state, play_card(wall)(state))
                        d = asked.decision
                        self.assertEqual((d.kind, d.min_choices, d.max_choices, d.options), (BENCH_FROM_DECK, 1, 1, E.deck_cards_matching(state, 0, UNOWN)))
                        self.assertEqual(d.context_value("unresolved_choices", ()), ())
                        done = resolve(asked, d.options[:1])
                        kinds = [e["kind"] for e in done.log[len(state.log):]]
                        self.assertEqual(kinds[:1] + kinds[-3:], ["play_trainer", "trainer_bench_from_deck", "shuffle", "discard_trainer"])
                        self.assertEqual(done.players[0].bench[-1].card, d.options[0])
                        self.assertEqual(check_invariants(done), [])

    def test_public_conditions_come_first(self):
        """公開の使う条件は今までどおり先: ベンチに空きがない（BENCH_FULL）→ 山札にアンノーンがあると下限で確かめられない（ST1）→ ガスの確かめ。"""
        for wall in WALLS:
            with self.subTest(wall=wall):
                full = wall_splits(wall, [UNOWN_E, UNOWN_R], 1, GG1, bench=[RATTATA] * 5)
                self.assertEqual(twin_command_problems(full, [play_card(wall)], owner_knowledge=True), [])
                self.assertEqual(command_outcome(full[0], play_card(wall)(full[0]))[0][:2], ("IllegalActionError", "BENCH_FULL"))
                short = wall_splits(wall, [UNOWN_E, UNOWN_R], 2, GG1)
                self.assertEqual(command_outcome(short[0], play_card(wall)(short[0]))[0][:2], ("UnsupportedError", ST1))

    def test_decision_after_the_search_keeps_the_actual_marks(self):
        """選んだあとの決定（山札をさがすので本人が見る）の選ぶと止める選択は、今までどおり実際の山札の候補（``bench_entry_unresolved``）。受け付ける盤面では、選べて止めない
        候補がかならずある（全部の答えが拒否される決定を残さない）。"""
        for wall in WALLS:
            for state in wall_splits(wall, [UNOWN_E, UNOWN_O], 0):
                asked = apply_command(state, play_card(wall)(state))
                d = asked.decision
                blocked = d.context_value("unresolved_choices", ())
                self.assertEqual(tuple(blocked), E.bench_entry_unresolved(state, d.options)[0])
                self.assertTrue(set(d.options) - set(blocked))

    def test_saved_and_restored_states_give_the_same_outcome(self):
        for wall in WALLS:
            for gas in (GG1, None):
                state = wall_board(wall, [UNOWN_E], [UNOWN_R], gas)
                expected = command_outcome(state, play_card(wall)(state))[0]
                for kind, restored in (("pickle", pickle.loads(pickle.dumps(state))), ("deepcopy", copy.deepcopy(state)), ("clone", state.clone())):
                    with self.subTest(wall=wall, gas=gas, kind=kind):
                        self.assertEqual(command_outcome(restored, play_card(wall)(restored))[0], expected)
                if gas is None:
                    asked = apply_command(state, play_card(wall)(state))
                    self.assertEqual(serialization_problems(asked), [])
                    again = pickle.loads(pickle.dumps(asked))
                    self.assertEqual(fingerprint(resolve(again, asked.decision.options[:1])), fingerprint(resolve(asked, asked.decision.options[:1])))


class BenchEntryHelperTest(unittest.TestCase):
    """共通処理 ``bench_entry_unconfirmed`` の、特殊能力を持つ候補・持たない候補が混ざる場合（写しのアンノーンはどれも特殊能力を持つので、遺跡の石版の登録では起こらない。条件
    ``CardFilter("basic_pokemon")`` で直接確かめる）。"""

    TARGET = CardFilter("basic_pokemon")

    def board(self, deck_cards, prize_cards, *, gas=True):
        me = {"active": HITMONCHAN, "hand": [GOOP_GAS_ATTACK] if gas else [], "deck": [FIRE] * 4 + list(deck_cards), "prizes": list(prize_cards)}
        state = build_test_state([me, {"active": MACHOP, "deck": [RATTATA] * 10}])
        return with_gas(state, GG1, 0) if gas else state

    def outcomes(self, hidden, prizes, *, gas=True):
        results = set()
        for mask in range(1 << len(hidden)):
            chosen = [hidden[i] for i in range(len(hidden)) if mask >> i & 1]
            if len(chosen) != prizes:
                continue
            rest = [hidden[i] for i in range(len(hidden)) if not mask >> i & 1]
            state = self.board(sorted(rest), sorted(chosen), gas=gas)
            problem = E.bench_entry_unconfirmed(state, 0, self.TARGET)
            actual_all_blocked = len(E.bench_entry_unresolved(state, E.deck_cards_matching(state, 0, self.TARGET))[0]) == len(E.deck_cards_matching(state, 0, self.TARGET))
            results.add((None if problem is None else (problem.code, problem.message), actual_all_blocked))
        return results

    def test_mixed_candidates(self):
        # 止めないコラッタ U 枚・止めるドガース（［ぶんれつ］）B 枚・サイド C 枚
        for hidden, prizes, accepts in (([RATTATA, KOFFING_ES2], 1, False), ([RATTATA, RATTATA, KOFFING_ES2], 1, True), ([KOFFING_ES2, KOFFING_ES2], 1, False),
                                        ([RATTATA, KOFFING_ES2, KOFFING_ES2], 1, False), ([RATTATA, RATTATA, KOFFING_ES2], 2, False)):
            with self.subTest(hidden=hidden, prizes=prizes):
                results = self.outcomes(hidden, prizes)
                verdicts = {r[0] for r in results}
                self.assertEqual(len(verdicts), 1, results)  # 配分によらない
                (verdict,) = verdicts
                self.assertEqual(verdict is None, accepts)
                if not accepts:
                    self.assertEqual(verdict, (GG1, expected_gas_reason(GG1)))

    def test_conservative_stop_when_an_unblocked_card_is_actually_in_the_deck(self):
        """保守的な制限: 止めないコラッタが実際には山札にあっても、下限が足りなければ止める（v0.137 までの確かめなら、この配分では受け付けた）。"""
        results = self.outcomes([RATTATA, KOFFING_ES2], 1)
        self.assertIn(((GG1, expected_gas_reason(GG1)), False), results)
        self.assertIn(((GG1, expected_gas_reason(GG1)), True), results)

    def test_no_blocking_effect_returns_none(self):
        self.assertEqual({r[0] for r in self.outcomes([RATTATA, KOFFING_ES2], 1, gas=False)}, {None})


class OtherBenchRoutesTest(unittest.TestCase):
    """``bench_entry_unresolved`` を使うほかの経路（v0.138 で変えていない）。選んだあとの決定（本人が山札を見る）だけで使う経路は、使う前の確かめに使っていない。"""

    def test_split_and_magnet_offer_decisions_regardless_of_the_deck(self):
        """［ぶんれつ］（resolution/kernel.py split_from_deck）・［マグネット］（CoinBenchNamedFromDeck）は、山札に候補がなくても決定を出す（0 枚を選べる）。使う前の拒否は山札を読まない。"""
        import inspect

        self.assertNotIn("bench_entry_unresolved", inspect.getsource(E.CoinBenchNamedFromDeck.check_usable))
        source = inspect.getsource(E.BenchNameGroupFromDeckTrainer.check_playable)
        self.assertNotIn("bench_entry_unresolved", source)
        self.assertNotIn("candidates", source)

    def test_increase_recorded_here_and_fixed_in_v0_147(self):
        """［INCREASE］（BenchNameGroupFromDeckOnEntry.accept_problem）は、v0.138 では実際の山札を読んだ（v0.138 で見つけた別の項目 PSP-INCREASE-ENTRY-PW3-ORACLE。この版では
        修正していない。docs 7 章の記録）。v0.147 で配分を読まない下限に直した（docs/deck-content-prechecks-v0.147.md。挙動の確かめは tests/test_deck_content_prechecks_v0_147.py。
        このテストは v0.146 まで、実際の山札を読むこと（修正していないこと）を確かめていた）。"""
        import inspect

        source = inspect.getsource(E.BenchNameGroupFromDeckOnEntry.accept_problem)
        self.assertNotIn("self.candidates(state, use.player)", source)
        self.assertIn("deck_target_lower_bound", source)
        self.assertIn("PSP-INCREASE-ENTRY-PW3-ORACLE", DOC.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 2. エネルギー増幅装置


def amp_board(hand, total, in_prizes, *, prizes=6, actor=0, **kw):
    """テスト専用の盤面: 手札にエネルギー増幅装置と ``hand``。見えない炎エネルギー ``total`` 枚のうち ``in_prizes`` 枚がサイド（v0.137 の ``split_board``）。"""
    return split_board(AMP, FIRE, total, in_prizes, prizes=prizes, actor=actor, hand_extra=tuple(hand), **kw)


def amp_splits(hand, total, prizes=6, **kw):
    return [amp_board(hand, total, j, prizes=prizes, **kw) for j in range(min(total, prizes) + 1)]


def first_coin(state, command, side):
    """切ってからコインを投げる処理で、そのコインが ``side`` になる乱数を 0 から探して ``command`` を送る（テスト専用。v0.80 のテストの answer_with_first_coin と同じ）。"""
    for seed in range(200):
        probe = state.clone()
        probe.rng = random.Random(seed)
        after = apply_command(probe, command)
        flips = [e for e in after.log[len(state.log):] if e["kind"] == "coin_flip"]
        if flips and flips[0]["result"] == side.value:
            return probe, after
    raise AssertionError("条件に合う乱数が見つからない")


AMP_HANDS = {"special": (DCE,), "two_specials": (DCE, RAINBOW), "mixed": (DCE, FIRE), "basic": (FIRE,)}
AMP_CASES = ((0, 6), (1, 6), (2, 6), (6, 6), (7, 6), (8, 6), (1, 1), (2, 1), (1, 0))


def amp_expected(hand, total, prizes):
    bound = max(0, total - prizes)
    use = FIRE in hand or bound >= 1
    return use, {card: card == FIRE or bound >= 1 for card in hand}


class AmplifierTwinTest(unittest.TestCase):
    def test_declaration_and_return_choice_do_not_depend_on_the_split(self):
        """どの手札・K・C でも、配分だけが違う状態に、使う宣言と段階 1 の答え（手札のそれぞれのエネルギーカード）を送ると、受理・拒否・コード・理由の文が同じ（見る人 0・1・観戦者）。
        宣言を受け付けるのは、手札に基本エネルギーカードがあるか下限が 1 以上のとき。特殊エネルギーカードをもどす答えを受け付けるのは、下限が 1 以上のとき。"""
        for name, hand in AMP_HANDS.items():
            for total, prizes in AMP_CASES:
                states = amp_splits(hand, total, prizes)
                use_ok, answer_ok = amp_expected(hand, total, prizes)
                with self.subTest(hand=name, total=total, prizes=prizes):
                    if len(states) >= 2:
                        self.assertEqual(twin_command_problems(states, [play_card(AMP)], owner_knowledge=True), [])
                    outcome = command_outcome(states[0], play_card(AMP)(states[0]))[0]
                    self.assertEqual(outcome[0] == "accepted", use_ok, outcome[:2])
                    if not use_ok:
                        self.assertEqual(outcome[1:3], (UPZ2, E.AMPLIFIER_UNCONFIRMED_REASON))
                        continue
                    for card in set(hand):
                        steps = [play_card(AMP), answer_card(card)]
                        if len(states) >= 2:
                            self.assertEqual(twin_command_problems(states, steps, owner_knowledge=True), [], card)
                        asked = apply_command(states[0], play_card(AMP)(states[0]))
                        out = command_outcome(asked, answer_card(card)(asked))[0]
                        self.assertEqual(out[0] == "accepted", answer_ok[card], (card, out[:2]))
                        if not answer_ok[card]:
                            self.assertEqual(out[1:3], (UPZ2, E.AMPLIFIER_UNCONFIRMED_REASON))

    def test_seat_swap(self):
        for hand, total, prizes in (((DCE,), 1, 6), ((DCE,), 7, 6), ((DCE, FIRE), 1, 6), ((DCE, FIRE), 2, 1)):
            with self.subTest(hand=hand, total=total, prizes=prizes):
                states = amp_splits(hand, total, prizes, actor=1)
                use_ok, _ = amp_expected(hand, total, prizes)
                self.assertEqual(twin_command_problems(states, [play_card(AMP)], owner_knowledge=True), [])
                if use_ok:
                    self.assertEqual(twin_command_problems(states, [play_card(AMP), answer_card(DCE)], owner_knowledge=True), [])
                outcome = command_outcome(states[0], play_card(AMP)(states[0]))[0]
                self.assertEqual(outcome[0] == "accepted", use_ok)

    def test_reason_text_is_fixed(self):
        """拒否の理由の文は決まった文（実際の山札の中身を書かない。v0.137 までの「もどしたあとの山札に基本エネルギーカードがない」を使わない）。宣言・段階 1 の答えで同じ。"""
        reasons = set()
        for total, prizes in ((0, 6), (1, 6), (6, 6), (1, 1)):
            for state in amp_splits((DCE,), total, prizes):
                reasons.add(command_outcome(state, play_card(AMP)(state))[0][2])
            for state in amp_splits((DCE, FIRE), total, prizes):
                asked = apply_command(state, play_card(AMP)(state))
                reasons.add(command_outcome(asked, answer_card(DCE)(asked))[0][2])
                self.assertEqual(asked.decision.context_value("unresolved_reason"), E.AMPLIFIER_UNCONFIRMED_REASON)
        self.assertEqual(reasons, {E.AMPLIFIER_UNCONFIRMED_REASON})
        self.assertNotIn("もどしたあとの山札に基本エネルギーカードがない", E.AMPLIFIER_UNCONFIRMED_REASON)

    def test_rejections_are_pure_and_repeatable(self):
        """使う宣言の拒否・段階 1 の答えの拒否は、状態・乱数・ログ・決定を変えず、何度送っても同じ。答えの拒否のあとも同じ決定に答えられ、基本エネルギーカードをもどせる。"""
        for state in amp_splits((DCE,), 1):
            before = fingerprint(state)
            self.assertEqual(len({command_outcome(state, play_card(AMP)(state))[0] for _ in range(4)}), 1)
            self.assertEqual(fingerprint(state), before)
        for state in amp_splits((DCE, FIRE), 1):
            asked = apply_command(state, play_card(AMP)(state))
            before = fingerprint(asked)
            self.assertEqual(len({command_outcome(asked, answer_card(DCE)(asked))[0] for _ in range(4)}), 1)
            self.assertEqual(fingerprint(asked), before)
            self.assertEqual(command_outcome(asked, answer_card(FIRE)(asked))[0], ("accepted",))

    def test_every_accepted_decision_has_an_answer(self):
        """受け付けた宣言の段階 1 には、止めない答えがかならずあり、止めない答えのあとの「おもて」の段階 2 には、選べる基本エネルギーカードがかならずある（全部の答えが拒否される
        決定を残さない）。"""
        for hand in AMP_HANDS.values():
            for total, prizes in AMP_CASES:
                for state in amp_splits(hand, total, prizes):
                    if command_outcome(state, play_card(AMP)(state))[0] != ("accepted",):
                        continue
                    asked = apply_command(state, play_card(AMP)(state))
                    d = asked.decision
                    free = [u for u in d.options if u not in d.context_value("unresolved_choices", ())]
                    with self.subTest(hand=hand, total=total, prizes=prizes):
                        self.assertTrue(free)
                        for uid in free:
                            _, after = first_coin(asked, ResolveDecision(0, d.id, (uid,)), H)
                            self.assertEqual(after.decision.kind, SEARCH_DECK)
                            self.assertTrue(after.decision.options)


class AmplifierSafePathTest(unittest.TestCase):
    def test_returned_basic_energy_can_be_searched(self):
        """基本エネルギーカードをもどす: 見えない炎エネルギーがなくても使え、「おもて」なら、もどしたカード自体を選べる → 見せて手札に加え → 切る（切るのは 2 回）。"""
        state = amp_board((FIRE,), 0, 0)
        asked = apply_command(state, play_card(AMP)(state))
        returned = card_in_hand(state, FIRE)
        self.assertEqual((asked.decision.kind, asked.decision.options, asked.decision.context_value("unresolved_choices", ())), (RETURN_TO_DECK, (returned,), ()))
        _, heads = first_coin(asked, ResolveDecision(0, asked.decision.id, (returned,)), H)
        d = heads.decision
        self.assertEqual((d.kind, d.options, d.min_choices, d.max_choices), (SEARCH_DECK, (returned,), 0, 1))
        done = resolve(heads, (returned,))
        kinds = [e["kind"] for e in done.log[len(state.log):]]
        self.assertEqual(kinds, ["play_trainer", "return_to_deck", "shuffle", "coin_flip", "reveal_from_deck", "shuffle", "discard_trainer"])
        self.assertIn(returned, done.players[0].hand)
        self.assertIn("card", [e for e in visible_log(done, 1) if e["kind"] == "reveal_from_deck"][-1])  # 相手プレイヤーに見せる
        self.assertEqual(check_invariants(done), [])

    def test_tails_shuffles_once_and_ends(self):
        state = amp_board((FIRE,), 0, 0)
        asked = apply_command(state, play_card(AMP)(state))
        _, tails = first_coin(asked, ResolveDecision(0, asked.decision.id, asked.decision.options), T)
        self.assertIsNone(tails.decision)
        kinds = [e["kind"] for e in tails.log[len(state.log):]]
        self.assertEqual(kinds, ["play_trainer", "return_to_deck", "shuffle", "coin_flip", "discard_trainer"])

    def test_special_return_with_a_bound_searches_up_to_three(self):
        """特殊エネルギーカードをもどす: 下限が 1 以上（見えない炎 8 枚・サイド 6 枚）なら、「おもて」で山札の基本エネルギーカードから 1〜3 枚（0 枚は UPZ1。状態を変えない）。"""
        state = amp_board((DCE,), 8, 3)
        asked = apply_command(state, play_card(AMP)(state))
        _, heads = first_coin(asked, answer_card(DCE)(asked), H)
        d = heads.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (SEARCH_DECK, 0, 3))
        self.assertEqual(d.options, E.deck_cards_matching(heads, 0, BASIC_ENERGY))
        before = fingerprint(heads)
        self.assertEqual(command_outcome(heads, ResolveDecision(0, d.id, ()))[0][:2], ("UnsupportedError", UPZ1))
        self.assertEqual(fingerprint(heads), before)
        done = resolve(heads, d.options[:3])
        self.assertEqual([e["kind"] for e in done.log[len(heads.log):]].count("reveal_from_deck"), 3)
        self.assertEqual(check_invariants(done), [])

    def test_existing_rejections_unchanged(self):
        """手札にエネルギーカードがない FC1（公開の手札の中身は本人が知っている）・段階 2 の 0 枚 UPZ1 は今までどおり。"""
        state = build_test_state([{"active": HITMONCHAN, "hand": [AMP, "PMCG1-071"], "deck": [FIRE] * 8}, {"active": MACHOP}])
        self.assertEqual(command_outcome(state, play_card(AMP)(state))[0][:2], ("UnsupportedError", FC1))

    def test_over_rejection_when_basic_energy_is_actually_in_the_deck(self):
        """保守的な制限: 実際には山札に基本エネルギーカードが 6 枚あっても、下限 0（サイド 6 枚）なら、特殊エネルギーカードをもどす答え（手札がそれだけなら使う宣言）を止める。"""
        state = amp_board((DCE,), 6, 0)
        self.assertEqual(len(E.deck_cards_matching(state, 0, BASIC_ENERGY)), 6)
        self.assertEqual(command_outcome(state, play_card(AMP)(state))[0][:2], ("UnsupportedError", UPZ2))
        mixed = amp_board((DCE, FIRE), 6, 0)
        asked = apply_command(mixed, play_card(AMP)(mixed))
        self.assertEqual(command_outcome(asked, answer_card(DCE)(asked))[0][:2], ("UnsupportedError", UPZ2))


class AmplifierRoutesTest(unittest.TestCase):
    def test_chaos_gym_borrower_uses_the_borrowers_bound(self):
        """錯乱ジムの「うら」で相手が借りて使うときは、借りたプレイヤーの手札と下限で確かめる。借りたプレイヤーの配分だけが違う状態で、借りる答えの受理・拒否が同じ。"""
        def board(total1, in_prizes1):
            deck1 = [RATTATA] * (10 - total1) + [DROWZEE] * in_prizes1 + [FIRE] * (total1 - in_prizes1)
            prizes1 = [FIRE] * in_prizes1 + [DROWZEE] * (6 - in_prizes1)
            state = amp_board((CHAOS_GYM, FIRE), 0, 0, opponent={"active": MACHOP, "hand": [DCE], "deck": deck1, "prizes": prizes1})
            return apply_command(state, PlayTrainer(0, card_in_hand(state, CHAOS_GYM)))

        for total1, accepts in ((1, False), (7, True)):
            with self.subTest(total1=total1):
                states = [with_coin_results(board(total1, j), T) for j in (0, 1)]
                steps = [play_card(AMP), lambda s: ResolveDecision(1, s.decision.id, (1,))]
                self.assertEqual(twin_command_problems(states, steps, owner_knowledge=True), [])
                asked = apply_command(states[0], play_card(AMP)(states[0]))
                self.assertEqual((asked.decision.kind, asked.decision.player), (ACCEPT_REQUEST, 1))
                outcome = command_outcome(asked, ResolveDecision(1, asked.decision.id, (1,)))[0]
                self.assertEqual(outcome[0] == "accepted", accepts)
                if not accepts:
                    self.assertEqual(outcome[1], UPZ2)

    def test_mind_games_offers_no_reaction_when_unusable(self):
        """相手の［ちえくらべ］: 使えない宣言には選択もコインもない（状態を変えない）。使える宣言（もどす基本エネルギーカードがある）は［ちえくらべ］の決定に進み、配分によらない。"""
        def board(hand, total, j):
            return amp_board(hand, total, j, turn_number=7,
                             opponent={"active": {"card": SLOWKING, "energy": [PSYCHIC] * 3, "evolved_from": SLOWPOKE}, "deck": [RATTATA] * 10})

        states = [board((DCE,), 1, j) for j in (0, 1)]
        self.assertEqual(twin_command_problems(states, [play_card(AMP)], owner_knowledge=True), [])
        before = fingerprint(states[0])
        self.assertEqual(command_outcome(states[0], play_card(AMP)(states[0]))[0][:2], ("UnsupportedError", UPZ2))
        self.assertEqual(fingerprint(states[0]), before)
        states = [board((DCE, FIRE), 1, j) for j in (0, 1)]
        steps = [play_card(AMP), lambda s: ResolveDecision(s.decision.player, s.decision.id, ())]
        self.assertEqual(twin_command_problems(states, steps, owner_knowledge=True), [])
        asked = apply_command(states[0], play_card(AMP)(states[0]))
        self.assertEqual(asked.decision.kind, REACTION_POWER)
        declined = resolve(asked, ())
        self.assertEqual(declined.decision.kind, RETURN_TO_DECK)
        self.assertEqual(twin_command_problems(states, steps + [answer_card(DCE)], owner_knowledge=True), [])
        self.assertEqual(command_outcome(declined, answer_card(DCE)(declined))[0][:2], ("UnsupportedError", UPZ2))

    def test_decision_across_save_and_restore(self):
        """段階 1 の決定を保存（pickle・deepcopy・clone）して、同じ答えで同じ結果（止める答え・止めない答え）。書き出し（最新の形式）の検査も通る。"""
        for total in (1, 8):
            state = amp_board((DCE, FIRE), total, 1)
            asked = apply_command(state, play_card(AMP)(state))
            self.assertEqual(serialization_problems(asked), [])
            for kind, restored in (("pickle", pickle.loads(pickle.dumps(asked))), ("deepcopy", copy.deepcopy(asked)), ("clone", asked.clone())):
                for card in (DCE, FIRE):
                    with self.subTest(total=total, kind=kind, card=card):
                        a, b = command_outcome(asked, answer_card(card)(asked)), command_outcome(restored, answer_card(card)(restored))
                        self.assertEqual(a[0], b[0])
                        if a[0] == ("accepted",):
                            self.assertEqual(fingerprint(a[1]), fingerprint(b[1]))

    def test_sudden_death_segment_uses_the_current_prizes(self):
        """延長戦の区間（サイド 1 枚）: 下限は今の区間の山札・サイドで決まり、前の区間の記録は使わない。宣言の受理は「手札の基本エネルギーカード、または下限 1 以上」と同じ。"""
        from tests.test_sudden_death_v0_134 import (
            _until_main,
            constructed_sudden_death,
            with_decklists,
        )

        cards = [AMP] * 4 + [DCE] * 4 + [FIRE] * 2 + [RATTATA] * 6
        checked = 0
        for seed in range(30):
            state = build_test_state([{"active": RATTATA, "hand": [], "deck": list(cards), "prizes": 1},
                                      {"active": RATTATA, "hand": [], "deck": list(cards), "prizes": 1}], current_player=0, seed=seed)
            fresh = next(_until_main(apply_command(constructed_sudden_death(with_decklists(state)), StartSuddenDeath())))
            player = fresh.current_player
            hand = [fresh.cards[u].card_id for u in fresh.players[player].hand]
            if AMP not in hand or not any(c in (DCE, FIRE) for c in hand):
                continue
            self.assertEqual(len(fresh.players[player].prizes), 1)
            deck, elsewhere = E.unseen_card_pool(fresh, player)
            bound = E.deck_target_lower_bound(fresh, player, BASIC_ENERGY)
            self.assertEqual(bound, max(0, sum(1 for u in (*deck, *elsewhere) if fresh.card_def(u).is_basic_energy) - len(elsewhere)))
            outcome = command_outcome(fresh, PlayTrainer(player, card_in_hand(fresh, AMP, player)))[0]
            self.assertEqual(outcome[0] == "accepted", FIRE in hand or bound >= 1, (seed, hand, bound))
            checked += 1
        self.assertGreater(checked, 0)


# ---------------------------------------------------------------- 3. 合法な操作の列


def swap_hidden(state, player, card_id, other_card_id=None):
    """この状態の、プレイヤー ``player`` の ``card_id`` のカード 1 枚と、反対の場所（山札・サイド）の別のカード（``other_card_id`` が None なら ``card_id`` でないカード）1 枚を
    入れかえた状態（観測・所有カード・乱数の状態は同じ。テストだけの操作。合法な列そのものではなく、合法な列で着いた状態の配分だけを変えたもの）。"""
    twin = state.clone()
    p = twin.players[player]
    target = next(u for u in [*p.prizes, *p.deck] if twin.cards[u].card_id == card_id)
    other_zone = p.deck if target in p.prizes else p.prizes
    zone = p.prizes if target in p.prizes else p.deck
    other = next(u for u in other_zone if (twin.cards[u].card_id == other_card_id if other_card_id else twin.cards[u].card_id != card_id))
    i, j = zone.index(target), other_zone.index(other)
    zone[i], other_zone[j] = other, target
    return twin


AMP_DECK = [AMP] * 4 + [DCE] * 4 + [FIRE] + [c for c in ES_DECK if c not in ("PMCG3-044", FIRE)][:51]


class LegalPathTest(unittest.TestCase):
    @staticmethod
    def first_turn(seed, deck=AMP_DECK):
        state = finish_setup(new_game(deck, OPPONENT_DECK, seed), janken_winner=0)
        assert state.phase is Phase.MAIN and state.current_player == 0, (seed, state.phase)
        return state

    def test_amplifier_seeds_from_the_reproduction(self):
        """new_game から（エネルギー増幅装置 4・無色2個エネルギー 4・炎エネルギー 1・たね 51）。最初の番の手札に増幅装置と無色2個エネルギーがあり炎エネルギーがない: seed 1 は炎
        エネルギーが山札、seed 25 はサイド。修正の前は seed 1 が受理・seed 25 が UPZ2（docs 2.2 節）。今はどちらも同じ拒否で、双子（山札とサイドの 2 枚の入れかえ）とも違いがない。"""
        self.assertEqual(Counter(AMP_DECK)[AMP], 4)
        self.assertEqual(len(AMP_DECK), 60)
        for seed, where in ((1, "deck"), (25, "prizes")):
            with self.subTest(seed=seed):
                state = self.first_turn(seed)
                hand = [state.cards[u].card_id for u in state.players[0].hand]
                self.assertTrue(AMP in hand and DCE in hand and FIRE not in hand)
                fire = next(u for u in state.cards if state.cards[u].card_id == FIRE and state.cards[u].owner == 0)
                self.assertIn(fire, state.players[0].deck if where == "deck" else state.players[0].prizes)
                twin = swap_hidden(state, 0, FIRE)
                self.assertEqual(owned_card_ids(twin, 0), owned_card_ids(state, 0))
                self.assertEqual(twin_command_problems([state, twin], [play_card(AMP)], owner_knowledge=True), [])
                self.assertEqual(command_outcome(state, play_card(AMP)(state))[0][:2], ("UnsupportedError", UPZ2))

    def test_amplifier_rich_deck_completes_from_the_first_turn(self):
        """基本エネルギーカード 20 枚のデッキ: 最初の番から下限が 1 以上で、特殊エネルギーカードをもどす答えも受け付け、最後まで処理できる（双子とも同じ）。"""
        deck = [AMP] * 4 + [DCE] * 4 + [FIRE] * 20 + [c for c in ES_DECK if c not in ("PMCG3-044", FIRE)][:32]
        state = next(s for s in (self.first_turn(seed, deck) for seed in range(200))
                     if {AMP, DCE} <= {s.cards[u].card_id for u in s.players[0].hand})
        self.assertGreaterEqual(E.deck_target_lower_bound(state, 0, BASIC_ENERGY), 1)
        steps = [play_card(AMP), answer_card(DCE)]
        self.assertEqual(twin_command_problems([state, swap_hidden(state, 0, FIRE)], steps, owner_knowledge=True), [])
        asked = apply_command(state, play_card(AMP)(state))
        for side in (H, T):
            _, after = first_coin(asked, answer_card(DCE)(asked), side)
            if side is H:
                after = resolve(after, after.decision.options[:3])
            self.assertIsNone(after.decision)
            self.assertEqual(check_invariants(after), [])

    def test_ruin_wall_in_a_sudden_death_segment(self):
        """延長戦の区間（構築した盤面からサドン・デスにし、StartSuddenDeath から合法な操作）: サイド 1 枚のプレイヤー 0 が、まきちらせ!ベトベトガス → 遺跡の石版。区間の seed 3 は
        サイドがアンノーン[O]。修正の前は、サイドのアンノーンと山札の別の文字のアンノーンを入れかえた双子で、理由の文が違った（docs 2.2 節）。今は同じ拒否（GG1・決まった文）。
        ガスを使わなければ石版は受け付ける（下限 2）。"""
        from tests.test_sudden_death_v0_134 import (
            _until_main,
            constructed_sudden_death,
            with_decklists,
        )

        cards0 = ["neo2-054", "neo2-054", "neo2-057", "neo2-057"] + [GOOP_GAS_ATTACK] * 4 + [UNOWN_E, UNOWN_O, UNOWN_R, UNOWN_L] + [RATTATA] * 4 + [FIRE] * 6
        cards1 = [RATTATA] * 4 + [FIRE] * 16
        state = build_test_state([{"active": RATTATA, "hand": [], "deck": list(cards0), "prizes": 1}, {"active": RATTATA, "hand": [], "deck": list(cards1), "prizes": 1}],
                                 current_player=0, seed=3)
        fresh = next(_until_main(apply_command(constructed_sudden_death(with_decklists(state)), StartSuddenDeath())))
        self.assertEqual((fresh.current_player, len(fresh.players[0].prizes)), (0, 1))
        self.assertEqual(fresh.cards[fresh.players[0].prizes[0]].card_id, UNOWN_O)
        self.assertEqual(E.deck_target_lower_bound(fresh, 0, UNOWN), 2)
        wall = next(c for c in WALLS if any(fresh.cards[u].card_id == c for u in fresh.players[0].hand))
        self.assertEqual(command_outcome(fresh, play_card(wall)(fresh))[0], ("accepted",))
        gassed = apply_command(fresh, PlayTrainer(0, card_in_hand(fresh, GOOP_GAS_ATTACK)))
        letter = next(fresh.cards[u].card_id for u in fresh.players[0].deck if fresh.cards[u].card_id in (UNOWN_E, UNOWN_R, UNOWN_L))
        twin = swap_hidden(gassed, 0, UNOWN_O, letter)
        self.assertEqual(twin_command_problems([gassed, twin], [play_card(wall)], owner_knowledge=True), [])
        self.assertEqual(command_outcome(gassed, play_card(wall)(gassed))[0][1:3], (GG1, expected_gas_reason(GG1)))


# ---------------------------------------------------------------- 4. 下限の共通処理・文書


class SharedBoundTest(unittest.TestCase):
    def test_predicate_bound_matches_the_filter_bound(self):
        """``deck_lower_bound_where`` は ``deck_target_lower_bound`` の一般化（同じ条件なら同じ値。v0.137 の 5 枚の確かめの値は変わらない）。"""
        for total, prizes in ((0, 6), (1, 6), (7, 6), (2, 1), (1, 0)):
            for state in amp_splits((DCE,), total, prizes):
                self.assertEqual(E.deck_lower_bound_where(state, 0, lambda u, s=state: BASIC_ENERGY.matches(s.card_def(u))),
                                 E.deck_target_lower_bound(state, 0, BASIC_ENERGY))

    def test_observation_does_not_expose_the_marks(self):
        """段階 1 の決定の、選ぶと止める選択・理由の文は観測に出ない（相手・観戦者には決定の種類とプレイヤーだけ。本人には選べるもの）。"""
        state = amp_board((DCE, FIRE), 1, 1)
        asked = apply_command(state, play_card(AMP)(state))
        for viewer in (0, 1, None):
            view = observe(asked, viewer)["decision"]
            self.assertNotIn("unresolved_choices", view)
            self.assertNotIn("unresolved_reason", repr(view))
            if viewer != 0:
                self.assertEqual(set(view), {"kind", "player"})


class DocumentTest(unittest.TestCase):
    def test_document_records_the_fix_and_the_open_items(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("PSP-RUIN-WALL-BLOCKED-REASON-ORACLE", "PSP-UPZ2-ENERGY-AMPLIFIER-ORACLE", "bench_entry_unconfirmed", "deck_lower_bound_where",
                       "UNRESOLVED_TRAINER_UP_TO_WITHOUT_TARGET", "UNRESOLVED_GOOP_GAS_NEW_POKEMON", "未解決のまま", "厳密モード", "PSP-INCREASE-ENTRY-PW3-ORACLE",
                       "PSP-COCOON-DV2-ORACLE"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
