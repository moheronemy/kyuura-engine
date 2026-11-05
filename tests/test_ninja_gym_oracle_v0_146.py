"""v0.146（docs/play-set-verification-v0.146.md 3 章）: キョウの忍者ジム（PR1-067）の使う前の確かめの情報漏れの修正（PSP-NJ1-NINJA-GYM-ORACLE）。

v0.145 までは、``UseStadium`` の使う前の確かめ（コインの前）が実際の山札のキョウのたねポケモンを読んだので、同じ公開の情報・同じ持ち主の知識から、キョウのたねポケモンが山札と
サイドのどちらにあるかで、受理と NJ1（``UNRESOLVED_NINJA_GYM_WITHOUT_TARGET``）が分かれた。拒否は状態を変えないので、毎番くりかえせる無料の問い合わせだった。v0.146 は、
v0.137 の ST1 と同じ配分を読まない下限（``effects.deck_target_lower_bound``）で確かめる（下限が 1 より少なければ NJ1。実際には山札にある場合も含む保守的な制限）。

テスト専用の盤面（``build_test_state``）と、``new_game`` からの合法な操作の列を分けて書く。比べる検査は ``log_audit.twin_command_problems``（``owner_knowledge``。3 者の観測・
ログの写しと、持ち主が知っている所有カードの集合が同じで、見えない山札とサイドの配分だけが違う状態）。NJ1 の研究上の問い（対象がないときに使えるか）は決めない。
"""

from __future__ import annotations

import pathlib
import unittest

from kyuura_engine import (
    PlayTrainer,
    ResolveDecision,
    UseStadium,
    apply_command,
    check_invariants,
    new_game,
)
from kyuura_engine import effects as E
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import BENCH_FROM_DECK
from kyuura_engine.observation import observe
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from tests.helpers import (
    FIRE,
    GRASS,
    HITMONCHAN,
    KOGAS_KOFFING,
    KOGAS_NINJA_GYM,
    RATTATA,
    apply_kernel,
    build_test_state,
    finish_setup,
    with_coin_results,
)
from tests.log_audit import (
    command_outcome,
    owned_card_ids,
    public_view,
    twin_command_problems,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "play-set-verification-v0.146.md"
F = "PMCG1-102"
H, T = CoinSide.HEADS, CoinSide.TAILS
NJ1 = "UNRESOLVED_NINJA_GYM_WITHOUT_TARGET"
FIXED_REASON = f"{E.NINJA_GYM_WITHOUT_TARGET_REASON}。{E.DECK_TARGET_UNCONFIRMED_DETAIL}"
SETS = (None, "CS-KYUURA-PLAY-S2A@1", "CS-KYUURA-PLAY-PO@1")
# new_game からの列: 忍者ジム 4・キョウのドガース 1・ほかのたね 8・草エネルギー 47。最初の番の手札に忍者ジムがあり、キョウのドガースが山札（seed 1）・サイド（seed 17）
LEGAL_DECK = [KOGAS_NINJA_GYM] * 4 + [KOGAS_KOFFING] + [RATTATA] * 4 + [HITMONCHAN] * 4 + [GRASS] * 47
OPPONENT = [RATTATA] * 4 + [HITMONCHAN] * 4 + [GRASS] * 52


def board(koga: int, *, deck_extra=(GRASS,) * 5, prizes=(FIRE,) * 6, bench=(RATTATA,), conventions=None):
    """プレイヤー 0 の番（3 番）に忍者ジムを出した盤面。山札はキョウのドガース ``koga`` 枚と ``deck_extra``、サイドは ``prizes``（うら）。"""
    me = {"active": {"card": HITMONCHAN, "energy": [F]}, "bench": list(bench), "hand": [KOGAS_NINJA_GYM],
          "deck": [KOGAS_KOFFING] * koga + list(deck_extra), "prizes": list(prizes)}
    them = {"active": {"card": HITMONCHAN, "energy": [F, F]}, "bench": [RATTATA], "hand": []}
    state = build_test_state([me, them], turn_number=3, current_player=0, seed=0)
    if conventions is not None:
        from kyuura_engine import conventions as C

        state.conventions = C.registered_identity(C.parse_key(conventions))
    gym = next(u for u in state.players[0].hand if state.cards[u].card_id == KOGAS_NINJA_GYM)
    return apply_command(state, PlayTrainer(0, gym))


def swap_hidden(state, card_id, player=0):
    """``card_id`` のカード 1 枚と、反対の場所（山札・サイド）の別のカード 1 枚を入れかえた双子（観測・所有カード・乱数の状態は同じ。テストだけの操作）。"""
    twin = state.clone()
    p = twin.players[player]
    target = next(u for u in [*p.prizes, *p.deck] if twin.cards[u].card_id == card_id)
    zone, other_zone = (p.prizes, p.deck) if target in p.prizes else (p.deck, p.prizes)
    other = next(u for u in other_zone if twin.cards[u].card_id != card_id)
    i, j = zone.index(target), other_zone.index(other)
    zone[i], other_zone[j] = other, target
    return twin


def snapshot(state):
    return repr(state_to_dict(state, format_version=max(FORMAT_VERSIONS))), [dict(e) for e in state.log], state.rng.getstate()


def legal_first_turn(seed, conventions=None):
    state = finish_setup(new_game(LEGAL_DECK, OPPONENT, seed, conventions=conventions), janken_winner=0)
    assert state.current_player == 0
    gym = next(u for u in state.players[0].hand if state.cards[u].card_id == KOGAS_NINJA_GYM)
    return apply_command(state, PlayTrainer(0, gym))


class ConstructedBoardTest(unittest.TestCase):
    """テスト専用の盤面（``build_test_state``）。サイドはうらの炎エネルギー 6 枚（キョウのたねポケモンを入れかえるときは 1 枚がキョウのドガース）。"""

    def test_one_koga_basic_is_the_same_wherever_it_is(self):
        """キョウのドガース 1 枚（下限 max(0, 1 − 6) = 0）: 修正の前は、山札なら受理・サイドなら NJ1（docs 3.1 節）。今はどちらも同じ NJ1・同じ決まった理由の文。"""
        state = board(1)
        twin = swap_hidden(state, KOGAS_KOFFING)
        self.assertIn(next(u for u in twin.players[0].prizes if twin.cards[u].card_id == KOGAS_KOFFING), twin.players[0].prizes)
        self.assertEqual(owned_card_ids(twin, 0), owned_card_ids(state, 0))
        self.assertEqual(twin_command_problems([state, twin], [UseStadium(0)], owner_knowledge=True), [])
        for s in (state, twin):
            outcome = command_outcome(s, UseStadium(0))[0]
            self.assertEqual(outcome, ("UnsupportedError", NJ1, FIXED_REASON))

    def test_lower_bound_boundary(self):
        """下限 = 本人に見えないキョウのたねポケモン K − 山札の外の見えないカード C（6）。K = 6 は全部が山札にあっても NJ1（保守的な制限）、K = 7 は受理。どちらも双子と同じ。"""
        for koga, accepted in ((0, False), (2, False), (6, False), (7, True), (8, True)):
            with self.subTest(koga=koga):
                state = board(koga)
                self.assertEqual(E.deck_target_lower_bound(state, 0, E.CoinBenchOwnerBasicFromDeckStadium(E.KOGAS_NINJA_GYM_TEXT).target()), max(0, koga - 6))
                outcome = command_outcome(state, UseStadium(0))[0]
                self.assertEqual(outcome[0] == "accepted", accepted, outcome[:2])
                if koga:
                    self.assertEqual(twin_command_problems([state, swap_hidden(state, KOGAS_KOFFING)], [UseStadium(0)], owner_knowledge=True), [])

    def test_known_prizes_and_fewer_prizes(self):
        """山札の外の見えないカードが少なければ下限が上がる: サイド 0 枚ならキョウのたねポケモン 1 枚で受理（山札にあることは本人に分かる）。サイド 1 枚なら NJ1。
        おもてのサイド・おもての山札の扱いは共通の下限（v0.137 の ``unseen_card_pool``）のテストが確かめる。"""
        state = board(1, prizes=())
        self.assertEqual(command_outcome(state, UseStadium(0))[0], ("accepted",))
        hidden = board(1, prizes=(FIRE,))
        self.assertEqual(command_outcome(hidden, UseStadium(0))[0][:2], ("UnsupportedError", NJ1))

    def test_bench_full_is_nj1_before_the_bound(self):
        """ベンチに空きがない（公開の情報）: どの配分でも NJ1（理由の文は v0.145 までと同じ）。"""
        state = board(8, bench=(RATTATA,) * 5)
        outcome = command_outcome(state, UseStadium(0))[0]
        self.assertEqual(outcome, ("UnsupportedError", NJ1, E.NINJA_GYM_WITHOUT_TARGET_REASON))
        self.assertEqual(twin_command_problems([state, swap_hidden(state, KOGAS_KOFFING)], [UseStadium(0)], owner_knowledge=True), [])

    def test_rejection_changes_nothing_and_repeats_identically(self):
        """拒否は状態・乱数・ログを変えない（コインの前）。何度送っても同じ（くりかえしても配分によらない）。"""
        state = board(1)
        before = snapshot(state)
        outcomes = {command_outcome(state, UseStadium(0))[0] for _ in range(3)}
        self.assertEqual(outcomes, {("UnsupportedError", NJ1, FIXED_REASON)})
        self.assertEqual(snapshot(state), before)

    def test_reason_has_no_card_name_or_uid(self):
        """理由の文は決まった文（カードの名前・uid・枚数・位置を書かない）。山札のカードの名前（ドガース）を含まない。"""
        message = command_outcome(board(1), UseStadium(0))[0][2]
        self.assertEqual(message, FIXED_REASON)
        self.assertNotIn("ドガース", message)
        self.assertNotIn("uid", message)

    def test_preflight_modes_agree_with_execution(self):
        """先読み（``preflight``）の方式と実際の処理が同じ結果（受理・拒否・コード）。"""
        for koga in (1, 7):
            results = set()
            for preflight in ("derived", "derived_full", "legacy"):
                state = with_coin_results(board(koga), T)
                try:
                    after = apply_kernel(state, UseStadium(0), preflight=preflight)
                    results.add(("accepted", len(after.log)))
                except E.UnsupportedError as error:
                    results.add((error.code, error.message))
            self.assertEqual(len(results), 1, (koga, results))

    def test_accepted_use_then_search_is_private(self):
        """受理したあと（下限 1 以上）: 「おもて」の決定の選べるものは実際の山札（本人が山札をさがして見る私的な情報）。相手・観戦者の観測には選べるものを出さない。
        双子（キョウのたねポケモン 1 枚を山札↔サイド）でも、相手の公開の情報は同じ。"""
        state = with_coin_results(board(8), H)
        twin = swap_hidden(state, KOGAS_KOFFING)
        after, other = apply_command(state, UseStadium(0)), apply_command(twin, UseStadium(0))
        for s in (after, other):
            self.assertEqual((s.decision.kind, s.decision.player), (BENCH_FROM_DECK, 0))
            self.assertEqual(check_invariants(s), [])
        self.assertEqual(len(after.decision.options) - len(other.decision.options), 1)
        for viewer in (1, None):
            self.assertNotIn("options", observe(after, viewer)["decision"])
            self.assertEqual(public_view(after, viewer), public_view(other, viewer))
        chosen = apply_command(after, ResolveDecision(0, after.decision.id, (after.decision.options[0],)))
        self.assertEqual([e["kind"] for e in chosen.log[-2:]], ["stadium_bench_from_deck", "shuffle"])

    def test_common_to_every_set(self):
        """修正は両モード共通: 今の挙動の集合・S2a・PO のどれでも同じ結果（集合の続行規約は NJ1 を続けない）。"""
        for conventions in SETS:
            for koga, accepted in ((1, False), (7, True)):
                with self.subTest(conventions=conventions, koga=koga):
                    state = board(koga, conventions=conventions)
                    self.assertEqual(command_outcome(state, UseStadium(0))[0][0] == "accepted", accepted)
                    self.assertEqual(twin_command_problems([state, swap_hidden(state, KOGAS_KOFFING)], [UseStadium(0)], owner_knowledge=True), [])

    def test_goop_gas_rejection_is_unreachable_for_current_data(self):
        """写しのキョウのたねポケモンは、どれも特殊能力を持たない（GG1 のベンチに出すと止める確かめに当たらない）。``bench_entry_unconfirmed`` は呼ぶが、今の写しでは止めない。"""
        from kyuura_engine.cards import load_card_pool

        pool = load_card_pool()
        target = E.CoinBenchOwnerBasicFromDeckStadium(E.KOGAS_NINJA_GYM_TEXT).target()
        kogas = [cid for cid in sorted(pool.playable_ids) if target.matches(pool.get(cid))]
        self.assertGreaterEqual(len(kogas), 10)
        self.assertEqual([cid for cid in kogas if pool.get(cid).powers], [])


class LegalSequenceTest(unittest.TestCase):
    """``new_game`` → 対戦準備（``finish_setup``）→ 最初の番に忍者ジムを出す、合法な操作の列。双子は合法な列で着いた状態の配分だけを変えたもの。"""

    def test_seeds_from_the_reproduction(self):
        """修正の前は seed 1（キョウのドガースが山札）が受理、seed 17（サイド）が NJ1（docs 3.1 節）。今はどちらも同じ NJ1 で、双子とも違いがない。"""
        for seed, where in ((1, "deck"), (17, "prizes")):
            with self.subTest(seed=seed):
                state = legal_first_turn(seed)
                koffing = next(u for u in state.cards if state.cards[u].card_id == KOGAS_KOFFING and state.cards[u].owner == 0)
                self.assertIn(koffing, state.players[0].deck if where == "deck" else state.players[0].prizes)
                self.assertEqual(command_outcome(state, UseStadium(0))[0], ("UnsupportedError", NJ1, FIXED_REASON))
                twin = swap_hidden(state, KOGAS_KOFFING)
                self.assertEqual(owned_card_ids(twin, 0), owned_card_ids(state, 0))
                self.assertEqual(twin_command_problems([state, twin], [UseStadium(0)], owner_knowledge=True), [])

    def test_every_set_from_new_game(self):
        """3 つの集合で ``new_game`` から同じ列: どれも同じ NJ1（集合は状態に持つ）。"""
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                state = legal_first_turn(1, conventions)
                self.assertEqual(command_outcome(state, UseStadium(0))[0][:2], ("UnsupportedError", NJ1))


class DocumentTest(unittest.TestCase):
    def test_document_records_the_fix(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("PSP-NJ1-NINJA-GYM-ORACLE", "deck_target_lower_bound", NJ1, "seed 1", "seed 17"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
