"""v0.189（docs/r2-coin-preflight-design.md 5 章の案 1）: このコマンドでおもてにした使い手のワザの宣言の先読みが、ほかの結果を公開の前の状態（``ctx.original``）で試していた
不整合の修正。

0.188.0 まで、``resolution.flow._use_attack`` は、既定の先読み ``derived`` のほかの結果を ``ctx.original``（コマンドの入口の状態。使い手はまだうら）の複製で試し、使い手自身の
うらのカードの最大HPを読んで FD1（UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY）で拒否していた（``derived_full``・``legacy`` は公開のあとの状態から試す）。0.189.0 では、
使い手が ``ctx.original`` でうらだったときだけ、ほかの結果を試す複製の元（と上限を超えたときの v0.13 の止める関数の状態）を、handler の入口の状態（おもてにして変身の状態を
固定したあと・``check_use_attack`` のあと・実際の処理の前）の複製にする。

確かめること（構築盤面。``test_secret_plan_v0_67`` の ``board``・``place``・``to_active`` を再利用。new_game からの到達ではない）:

- G1a（スタジアムのコインだけが先読みを起こす: マチスのコイルのたいあたり）・G1b（ワザ自身のコイン: でんきショック。決定: マチスのエレブー PR1-040 のデンキとばし）・
  G1c（コインなしのかまいたち: 実際の面で受理・拒否が変わっていた）で、FD1 が消え、先におもてにしてから同じ宣言を送った対照（公開の後の双子）と状態・乱数・ログが同じ
- 先読みの方法 derived・derived_full・legacy が同じ結果
- G0（たいでん）は受理のまま、G2（コインつきのかまいたち）は VM1 のまま、おもての使い手は複製の元が入口の状態のまま、たねでない本当のカード（特殊能力を持つ
  マチスのレアコイルをふくむ）は先読みに入らずトラッシュ
- 公開のイベントは 1 回、コイン・乱数・効果は二重にならない、拒否の不変、直接のコマンドと API の一致
- 秘密の保護: 複製の元でも、使い手以外のうらのカード（相手・自分のベンチ）はうらのまま（FD1）。相手のうらのカードの本当のカードだけを変えても、本人の結果は同じ
- 上限を超えたときの確かめも同じ複製の元を使う（``preflight.MAX_BRANCHES`` を小さくした人工の条件。実際の盤面の通常のケースとは別の出典）
"""

from __future__ import annotations

import unittest
from unittest import mock

from kyuura_engine import zones
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import AttachEnergy, PlayTrainer, UseAttack
from kyuura_engine.engine import apply_command, apply_command_with
from kyuura_engine.errors import HiddenPropertyRead, IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe
from kyuura_engine.resolution import preflight as P
from kyuura_engine.resolution import v013_checks
from kyuura_engine.serialize import rng_fingerprint
from tests import helpers as H
from tests import test_secret_plan_v0_67 as S
from tests import test_stadiums_v0_57 as T57
from tests.test_legal_actions_u7_1 import snap
from tests.test_legal_actions_u7_4 import via_direct, via_u7

HD, TL = CoinSide.HEADS, CoinSide.TAILS
FD1, VM1 = "UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY", "UNRESOLVED_VERMILION_GYM_ATTACK_ORDER"
MAGNEMITE = H.LT_SURGES_MAGNEMITE  # PMCG5-037（でんきショック: G1b・たいあたり: G1a）
SPEAROW = H.LT_SURGES_SPEAROW  # PMCG5-057（かまいたち: G2・G1c）
ELECTABUZZ = H.LT_SURGES_ELECTABUZZ  # PMCG5-041（たいでん: G0）
ELECTABUZZ_PROMO = "PR1-040"  # マチスのエレブー（たいでん・デンキとばし: G1b の決定を出すワザ）
RATICATE = H.LT_SURGES_RATICATE  # PMCG5-059（1 進化）
MAGNETON = H.LT_SURGES_MAGNETON  # PMCG5-040（1 進化・特殊能力を持つ）
METHODS = ("derived", "derived_full", "legacy")


def board(real, *, stadium=H.VERMILION_CITY_GYM, energies=4, energy=H.LIGHTNING, opponent_face_down=None, own_bench_face_down=None):
    """プレイヤー 0 の番の main。バトル場はうらの ``real`` に ``energy`` が ``energies`` 枚、ベンチはおもてのエビワラー（と、``own_bench_face_down`` があればうらのカード）。
    相手のバトル場はおもてのエビワラー（と、``opponent_face_down`` があれば相手のベンチにうらのカード）。場のスタジアムは ``stadium``（None なら出さない）。"""
    extra = (H.LT_SURGES_SECRET_PLAN, own_bench_face_down) if own_bench_face_down else ()
    hand = (real, *([energy] * energies), *extra, *(() if stadium is None else (stadium,)))
    state = S.board(hand=hand, opponent_hand=(H.LT_SURGES_SECRET_PLAN, opponent_face_down) if opponent_face_down else ())
    state = S.place(state, real)
    state = S.to_active(state, S.face_down(state)[0])
    state = S.opponent_turn(state)
    if opponent_face_down:
        state = S.place(state, opponent_face_down, player=1)
    state = S.opponent_turn(state)
    for i in range(energies):
        if i:
            state = S.opponent_turn(S.opponent_turn(state))
        state = apply_command(state, AttachEnergy(0, S.uid_of(state, energy), state.players[0].active.card))
    if own_bench_face_down:
        state = S.place(state, own_bench_face_down)
    if stadium is not None:
        state = apply_command(state, PlayTrainer(0, S.uid_of(state, stadium)))
    assert state.is_face_down(state.players[0].active) and state.current_player == 0 and state.decision is None
    return state


def coins(state, side):
    return H.with_coin_bits(state, *[side] * 8)


def revealed(state):
    """公開の後の双子: 同じ状態で、先にバトル場のうらのカードをおもてにした（ワザのコマンドが入口でする公開と同じ ``cause``）。"""
    twin = state.clone()
    zones.reveal_face_down(twin, 0, twin.players[0].active, cause="attack")
    return twin


def result(state, command, preflight="derived"):
    try:
        after = apply_command_with(state, command, preflight=preflight)
    except (IllegalActionError, UnsupportedError) as error:
        return ("rejected", error.code, str(error))
    return ("accepted", snap(after))


def kinds(state, kind):
    return [e for e in state.log if e["kind"] == kind]


class BaseStateTest(unittest.TestCase):
    """先読みの複製の元（after_real_run に渡す状態）。"""

    def captured(self, state, command):
        seen = []
        real = P.after_real_run

        def spy(state_, original, *a, **k):
            seen.append(original)
            return real(state_, original, *a, **k)
        with mock.patch.object(P, "after_real_run", spy):
            try:
                apply_command(state, command)
            except (IllegalActionError, UnsupportedError):
                pass
        return seen

    def test_revealed_attacker_uses_the_handler_entry_state(self):
        state = coins(board(MAGNEMITE), HD)
        seen = self.captured(state, UseAttack(0, 1, stadium_coin=True))
        self.assertEqual(len(seen), 1)
        base = seen[0]
        self.assertIsNot(base, state)
        attacker = base.players[0].active
        self.assertFalse(base.is_face_down(attacker))  # おもてにしたあと
        self.assertEqual(len(kinds(base, "secret_plan_revealed")), 1)
        self.assertEqual(base.log[:len(state.log)], state.log)  # 入口のログに、公開の 1 件だけが足されている（実際の処理の結果がない）
        self.assertEqual([e["kind"] for e in base.log[len(state.log):]], ["secret_plan_revealed"])
        self.assertEqual(rng_fingerprint(base.rng), rng_fingerprint(state.rng))  # 乱数を使っていない

    def test_face_up_attacker_keeps_the_entry_state(self):
        state = T57.placed(H.VERMILION_CITY_GYM, active={"card": MAGNEMITE, "energy": [H.LIGHTNING, H.LIGHTNING]})
        seen = self.captured(coins(state, HD), UseAttack(0, 1, stadium_coin=True))
        self.assertEqual(len(seen), 1)
        self.assertEqual(snap(seen[0]), snap(coins(state, HD)))  # ctx.original（入口の状態）のまま

    def test_non_basic_never_reaches_the_preflight(self):
        for real in (RATICATE, MAGNETON):  # 特殊能力を持つ本当のカード（マチスのレアコイル）をふくむ
            with self.subTest(real=real):
                state = coins(board(real), HD)
                self.assertEqual(self.captured(state, UseAttack(0, 0, stadium_coin=True)), [])
                after = apply_command(state, UseAttack(0, 0, stadium_coin=True))
                self.assertIn(state.players[0].active.card, after.players[0].discard)
                self.assertEqual(rng_fingerprint(after.rng), rng_fingerprint(state.rng))

    def test_other_face_down_cards_stay_hidden_in_the_base(self):
        """使い手以外のうらのカード（相手のベンチ・自分のベンチ）は、複製の元でもうらのまま（項目を読むと FD1）。"""
        state = coins(board(MAGNEMITE, opponent_face_down=H.RATTATA, own_bench_face_down=H.ONIX), HD)
        seen = self.captured(state, UseAttack(0, 1, stadium_coin=True))
        self.assertEqual(len(seen), 1)
        base = seen[0]
        hidden = [q for side in base.players for q in side.in_play() if base.is_face_down(q)]
        self.assertEqual(len(hidden), 2)
        self.assertEqual({base.cards[q.card].owner for q in hidden}, {0, 1})
        for pokemon in hidden:
            with self.assertRaises(HiddenPropertyRead):
                base.card_def(pokemon.card).hp  # noqa: B018


class RepresentativeTest(unittest.TestCase):
    """代表のワザ: 先におもてにしてから同じ宣言を送った対照と同じ結果・先読みの方法の等価。"""

    def assert_like_revealed(self, state, command):
        got = result(state, command)
        twin = result(revealed(state), command)
        self.assertEqual(got, twin)
        self.assertNotIn(FD1, got)
        for method in METHODS[1:]:
            self.assertEqual(result(state, command, method), got, method)
        if got[0] == "accepted":
            after = apply_command(state, command)
            self.assertEqual(len(kinds(after, "secret_plan_revealed")), 1)
            self.assertEqual(len(kinds(after, "coin_flip")), len(kinds(apply_command(revealed(state), command), "coin_flip")))
        return got

    def test_g1a_stadium_coin_only(self):
        for side in (HD, TL):
            with self.subTest(side=side):
                got = self.assert_like_revealed(coins(board(MAGNEMITE), side), UseAttack(0, 1, stadium_coin=True))
                self.assertEqual(got[0], "accepted")

    def test_g1b_attack_coin_with_and_without_the_stadium_coin(self):
        for side in (HD, TL):
            for stadium_coin in (False, True):
                with self.subTest(side=side, stadium_coin=stadium_coin):
                    self.assert_like_revealed(coins(board(MAGNEMITE), side), UseAttack(0, 0, stadium_coin=stadium_coin))

    def test_g1b_attack_with_a_decision(self):
        for side in (HD, TL):
            with self.subTest(side=side):
                got = self.assert_like_revealed(coins(board(ELECTABUZZ_PROMO), side), UseAttack(0, 1, stadium_coin=True))
                if got[0] == "accepted":
                    self.assertIsNotNone(apply_command(coins(board(ELECTABUZZ_PROMO), side), UseAttack(0, 1, stadium_coin=True)).decision)

    def test_g1c_acceptance_no_longer_depends_on_the_real_coin(self):
        """コインなしのかまいたち: 0.188.0 は「おもて」なら受理・「うら」なら FD1（拒否から次のコインの面が分かった）。0.189.0 はどちらの面でも同じ区分。"""
        got = [self.assert_like_revealed(coins(board(SPEAROW), side), UseAttack(0, 1)) for side in (HD, TL)]
        self.assertEqual({g[0] for g in got}, {"accepted"})

    def test_g0_unchanged(self):
        for side in (HD, TL):
            with self.subTest(side=side):
                got = self.assert_like_revealed(coins(board(ELECTABUZZ), side), UseAttack(0, 0, stadium_coin=True))
                self.assertEqual(got[0], "accepted")

    def test_g2_vm1_is_kept(self):
        for side in (HD, TL):
            with self.subTest(side=side):
                state = coins(board(SPEAROW), side)
                got = self.assert_like_revealed(state, UseAttack(0, 1, stadium_coin=True))
                self.assertEqual(got[:2], ("rejected", VM1))

    def test_face_up_attacker_and_methods(self):
        state = T57.placed(H.VERMILION_CITY_GYM, active={"card": MAGNEMITE, "energy": [H.LIGHTNING, H.LIGHTNING]})
        for side in (HD, TL):
            with self.subTest(side=side):
                got = [result(coins(state, side), UseAttack(0, 1, stadium_coin=True), m) for m in METHODS]
                self.assertEqual(got[0][0], "accepted")
                self.assertEqual(got[1:], [got[0]] * 2)


class SubmitTest(unittest.TestCase):
    def test_direct_and_api_match(self):
        for side in (HD, TL):
            with self.subTest(side=side):
                state = coins(board(MAGNEMITE), side)
                host, via = via_u7(state, lambda s: ["o2", "o3"])
                game, direct = via_direct(state, UseAttack(0, 1, stadium_coin=True))
                self.assertEqual(via.outcome, "accepted", via)
                self.assertEqual((via.outcome, via.view), (direct.outcome, direct.view_for(0)))
                self.assertEqual(snap(host.game.state), snap(game.state))

    def test_rejection_leaves_everything(self):
        for state, command in ((coins(board(SPEAROW), TL), UseAttack(0, 1, stadium_coin=True)),  # VM1
                               (coins(board(MAGNEMITE, energies=0), HD), UseAttack(0, 1, stadium_coin=True))):  # 必要なエネルギーが足りない
            with self.subTest(command=command):
                before = snap(state)
                self.assertEqual(result(state, command)[0], "rejected")
                self.assertEqual(snap(state), before)


class SecretProtectionTest(unittest.TestCase):
    def test_opponent_secret_only_does_not_change_the_actors_result(self):
        """相手のベンチのうらのカードの本当のカードだけを変えた盤面: 本人のコマンドの区分・本人の観測が同じ（相手のうらのカードは公開しない）。"""
        seen = []
        for opponent in (H.RATTATA, H.ONIX, H.KADABRA):
            state = coins(board(MAGNEMITE, opponent_face_down=opponent), HD)
            got = result(state, UseAttack(0, 1, stadium_coin=True))
            view = observe(apply_command(state, UseAttack(0, 1, stadium_coin=True)), 0) if got[0] == "accepted" else got[1:]
            seen.append((got[0], view))
        self.assertEqual(seen[0][0], "accepted")
        self.assertEqual(seen[1:], [seen[0]] * 2)


class LimitPathTest(unittest.TestCase):
    """上限を超えたとき（人工: ``preflight.MAX_BRANCHES`` を小さくした。実際の盤面の通常のケースとは別の出典）。v0.13 の止める関数に渡す状態も、修正した複製の元。"""

    def test_v013_check_gets_the_revealed_base(self):
        state = coins(board(MAGNEMITE), HD)
        seen = []

        def spy(state_, use, effect, attacker, trace, *, mode="legacy"):
            seen.append((mode, state_.is_face_down(attacker), state_ is not state))
        with mock.patch.object(P, "MAX_BRANCHES", 1), mock.patch.object(v013_checks, "check", spy):
            try:
                apply_command(state, UseAttack(0, 0))  # でんきショック（ワザ自身のコイン。クチバシティジムのコインなし）
            except (IllegalActionError, UnsupportedError) as error:
                seen.append(("error", error.code))
        legacy = [s for s in seen if s[0] == "legacy_after_limit"]
        if legacy:
            self.assertEqual(legacy, [("legacy_after_limit", False, True)])
        else:  # ワザの型が v0.13 の止める関数の対象でなければ、その前に UNSUPPORTED_PREFLIGHT_LIMIT（複製の元を読まない）
            self.assertIn(("error", "UNSUPPORTED_PREFLIGHT_LIMIT"), seen)
            self.skipTest("でんきショックの型は v0.13 の止める関数の対象でない（上限の経路はこのワザで起こらない）")


if __name__ == "__main__":
    unittest.main()
