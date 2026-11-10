"""v0.179（PT-5t-C1。docs/legal-actions-up5t-d-trainer-audit.md 12 章）: トレーナーの候補の確かめが、相手のうらのカードの本当のカードを使ったら、
その結果を候補に使わない（選べるものを unverified・face_down_reveal_not_evaluated にし、拒否・停止でも外さない）。

対象の経路: ねむれ!ねむれ!（PMCG4-054。``CoinStatusOnOpponentActiveTrainer``）・トロピカルウインド（PR1-074。``CoinHealBothElseSleepBoth``）の使うための条件が、
状態の複製の上で相手のバトル場を「ねむり」にする試行で、相手のバトル場がうらのカード（マチスの秘策）なら ``zones.designate_face_down`` が本当のカードを読む（監査の 4.3 節）。
修正の前の構築盤面では外へ出る差は出なかった（読みはあった）。確認された秘密依存の判定を候補の側で採用しない補強で、漏れの再現と修正ではない。

盤面はどれも構築盤面（``tests/test_secret_plan_v0_67.py`` の ``board``・``place``・``to_active``・``face_down``。プレイヤー 0 がうらにして出したカードに、にげるで入れ替え、
番を終える。使う人はプレイヤー 1）。new_game からの到達ではない。双子は、プレイヤー 0 のうらのカードの本当のカード（たねポケモン・たねポケモンでない・メタモン）だけが違い、
プレイヤー 1 と観戦者の観測・公開のログが同じ（プレイヤー 0 の観測は本当のカードを含むので違う）。
"""

from __future__ import annotations

import unittest
from unittest import mock

from kyuura_engine import EndTurn, EvolvePokemon, PlayTrainer, apply_command
from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine import zones
from kyuura_engine.client_api import ClientHub
from kyuura_engine.engine import check_invariants
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe, visible_log
from tests import helpers as H
from tests.test_legal_actions_u7_1 import snap, without_handles
from tests.test_secret_plan_v0_67 import board, face_down, place, to_active

REQ = {"contract": "kyuura-client-api", "format": 1}
TRAINERS = {"ねむれ!ねむれ!": H.SLEEP_TRAINER, "トロピカルウインド": "PR1-074"}
REALS = {"basic": H.RATTATA, "stage1": H.KADABRA, "ditto": H.DITTO}  # たねポケモン・たねポケモンでない（おもてにするとトラッシュ）・メタモン
IMAKUNI = "PR1-013"  # イマクニ？（自分のバトル場をこんらんにする。``ConditionOwnActiveTrainer``）
GLOOM = {"card": H.DARK_GLOOM, "evolved_from": H.ROCKET_ODDISH, "evolved_turn": 4}
FACE_DOWN_REASONS = sorted([L.REASON_FACE_DOWN, L.REASON_PREFLIGHT, L.REASON_CONTINUATION])
EVALUATED_REASONS = sorted([L.REASON_PREFLIGHT, L.REASON_CONTINUATION])


def opponent_face_down(trainer, real, *, bench=(), extra_hand=(), turn_number=5):
    """プレイヤー 1 の番の MAIN。プレイヤー 1 の手札に ``trainer``、プレイヤー 0 のバトル場にうらのカード（本当のカードは ``real``）。"""
    s = board(hand=(real,), opponent_hand=(trainer, *extra_hand), opponent_bench=bench, turn_number=turn_number)
    s = place(s, real)
    s = to_active(s, face_down(s)[0])
    s = apply_command(s, EndTurn(0))
    assert s.current_player == 1 and s.decision is None and check_invariants(s) == [] and s.is_face_down(s.players[0].active)
    return s


def opponent_face_down_bench_only(trainer, real):
    s = board(hand=(real,), opponent_hand=(trainer,), turn_number=5)
    s = place(s, real)
    s = apply_command(s, EndTurn(0))
    assert s.current_player == 1 and check_invariants(s) == [] and not s.is_face_down(s.players[0].active) and face_down(s)
    return s


def opponent_face_up(trainer):
    s = board(opponent_hand=(trainer,), turn_number=5)
    s = apply_command(s, EndTurn(0))
    assert s.current_player == 1 and check_invariants(s) == []
    return s


def own_face_down(real):
    """プレイヤー 0 の番。自分のバトル場がうらのカード（本人は本当のカードを知る）、手札にイマクニ？。"""
    s = board(hand=(real, IMAKUNI), turn_number=5)
    s = place(s, real)
    s = to_active(s, face_down(s)[0])
    assert s.current_player == 0 and check_invariants(s) == [] and s.is_face_down(s.players[0].active)
    return s


def with_allergy_pollen(trainer, real):
    """使う人（1）が番の中で、ベンチのわるいクサイハナをわるいラフレシアに進化させる（［アレルギーかふん］。だれもトレーナーを使えない。読む前の公開の拒否）。"""
    s = opponent_face_down(trainer, real, bench=[GLOOM], extra_hand=(H.DARK_VILEPLUME,), turn_number=7)
    card = next(u for u in s.players[1].hand if s.cards[u].card_id == H.DARK_VILEPLUME)
    s = apply_command(s, EvolvePokemon(1, card, s.players[1].bench[0].pokemon_id))
    assert check_invariants(s) == [] and s.is_face_down(s.players[0].active)
    return s


def uid_in_hand(state, player, card_id):
    return next(u for u in state.players[player].hand if state.cards[u].card_id == card_id)


def trainer_queries(state, actor):
    """client_api の入口で、本人の候補（取っ手を除く）と、play_trainer の inputs・選べるものごとの check・不正な入力の check。他者への更新と、前後の状態・記録の並び。"""
    hub = ClientHub.from_state(state)
    me = hub.player(actor)
    before = snap(hub._host.game.state)
    r = me.handle({**REQ, "type": "candidates"})["response"]
    out = {"candidates": without_handles(r), "trainer": None}
    for c in r["candidates"]:
        if c["kind"] != L.KIND_PLAY_TRAINER:
            continue
        h = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        inputs = me.handle({**REQ, "type": "inputs", **h})["response"]
        out["trainer"] = {"candidate": without_handles(c), "inputs": without_handles(inputs),
                          "checks": [me.handle({**REQ, "type": "check", **h, "choices": [o["id"]]})["response"] for o in inputs["stages"][0]["options"]],
                          "check_bad": me.handle({**REQ, "type": "check", **h, "choices": ["o9"]})["response"]}
    others = [hub.take_updates(a) for a in (1 - actor, "spectator")]
    return out, others, snap(hub._host.game.state) == before


def option_of(out, state, player, card_id):
    uid = uid_in_hand(state, player, card_id)
    return next((o for o in out["trainer"]["inputs"]["stages"][0]["options"] if o["card"] == uid), None) if out["trainer"] else None


class TwinTest(unittest.TestCase):
    def test_twins_share_the_actor_and_spectator_knowledge(self):
        for name, trainer in TRAINERS.items():
            states = {n: opponent_face_down(trainer, real) for n, real in REALS.items()}
            first = next(iter(states.values()))
            for n, s in states.items():
                with self.subTest(trainer=name, real=n):
                    self.assertEqual((observe(s, 1), observe(s, None), visible_log(s, 1), visible_log(s, None)),
                                     (observe(first, 1), observe(first, None), visible_log(first, 1), visible_log(first, None)))
            self.assertEqual(len({str(observe(s, 0)) for s in states.values()}), len(states))  # 持ち主の観測は本当のカードを含む（知識は同じでない）
            self.assertEqual(len({str(snap(s)) for s in states.values()}), len(states))

    def test_candidates_inputs_check_do_not_depend_on_the_real_card(self):
        for name, trainer in TRAINERS.items():
            results = {}
            for n, real in REALS.items():
                s = opponent_face_down(trainer, real)
                out, others, unchanged = trainer_queries(s, 1)
                self.assertEqual(others, [[], []])  # 相手・観戦者へ本人の候補・入力・診断を出さない
                self.assertTrue(unchanged)  # 状態・乱数・ログ・決定の通し番号が同じ
                self.assertIsNone(zones.IDENTITY_CONSULTED)
                results[n] = (out, option_of(out, s, 1, trainer))
            with self.subTest(trainer=name):
                self.assertEqual(len({str(v) for v in results.values()}), 1)
                out, option = results["basic"]
                self.assertEqual((option["processability"], option["reasons"], option["eligible"]), (L.UNVERIFIED, FACE_DOWN_REASONS, True))
                c = out["trainer"]["candidate"]
                self.assertEqual((c["processability"], c["input_disclosure"]), (L.UNVERIFIED, L.DISCLOSURE_CONFIRMED))
                self.assertIn("v0.179", c["guarantees"]["preconditions"])
                self.assertEqual(len(out["trainer"]["inputs"]["stages"]), 1)  # 入力の形（1 段・手札のカード 1 枚）は今のまま
                self.assertTrue(all(ch["valid"] for ch in out["trainer"]["checks"]))  # 構造の検査だけ（受理の保証ではない）
                self.assertEqual(out["trainer"]["check_bad"]["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)

    def test_the_real_card_is_still_read_after_the_record(self):
        """候補の作成のあいだに、本当のカードを読む処理は今も呼ばれる（試行は変えていない）。読む前に相手（0）が記録され、結果を使わない。"""
        for name, trainer in TRAINERS.items():
            s = opponent_face_down(trainer, H.KADABRA)
            seen = []
            original = zones._secret_plan_keeps

            def spy(state, card, s=s, seen=seen):
                seen.append((card == s.players[0].active.card, list(zones.IDENTITY_CONSULTED or [])))
                return original(state, card)
            with mock.patch.object(zones, "_secret_plan_keeps", spy):
                L.ActionHost(A.HostedGame(s.clone())).session(1).candidates()
            with self.subTest(trainer=name):
                self.assertTrue(seen)
                self.assertTrue(all(is_target and consulted == [0] for is_target, consulted in seen))


class ControlTest(unittest.TestCase):
    def test_face_up_opponent_is_evaluated(self):
        for name, trainer in TRAINERS.items():
            s = opponent_face_up(trainer)
            out, _others, _ = trainer_queries(s, 1)
            option = option_of(out, s, 1, trainer)
            self.assertEqual((option["processability"], option["reasons"]), (L.MAY_STOP_LATER, EVALUATED_REASONS), name)

    def test_face_down_card_only_on_the_bench_is_not_read(self):
        """2 つのトレーナーの試行はバトル場だけを「ねむり」にするので、ベンチのうらのカードはおもてにしない（記録なし。今のまま評価する）。"""
        for name, trainer in TRAINERS.items():
            s = opponent_face_down_bench_only(trainer, H.KADABRA)
            out, _others, _ = trainer_queries(s, 1)
            option = option_of(out, s, 1, trainer)
            self.assertEqual((option["processability"], option["reasons"]), (L.MAY_STOP_LATER, EVALUATED_REASONS), name)

    def test_own_face_down_active_is_evaluated_with_own_knowledge(self):
        for n, real in REALS.items():
            with self.subTest(real=n):
                s = own_face_down(real)
                out, _others, _ = trainer_queries(s, 0)
                option = option_of(out, s, 0, IMAKUNI)
                self.assertIsNotNone(option)
                self.assertNotIn(L.REASON_FACE_DOWN, option.get("reasons", []))  # 本人の知識なので評価する（一律に未評価にしない）

    def test_public_refusal_before_the_read_is_kept(self):
        """読む前の公開の拒否（［アレルギーかふん］の TRAINER_PREVENTED。check_playable の前）は今のまま候補を出さない。どの双子でも同じ。"""
        for name, trainer in TRAINERS.items():
            outs = []
            for real in REALS.values():
                s = with_allergy_pollen(trainer, real)
                out, others, unchanged = trainer_queries(s, 1)
                self.assertIsNone(out["trainer"])
                self.assertTrue(unchanged)
                outs.append(out)
            self.assertEqual(len({str(o) for o in outs}), 1, name)


class RecordingTest(unittest.TestCase):
    """記録の扱い（check_play_trainer を置きかえた模擬。記録のあとの公開の拒否は、今の登録の 2 つのトレーナーでは起こらないので模擬で確かめる）。"""

    def setUp(self):
        self.state = opponent_face_up(H.SLEEP_TRAINER)
        self.uid = uid_in_hand(self.state, 1, H.SLEEP_TRAINER)

    def fake(self, *, consult=None, raised=None):
        def check(state, cmd, *, use_condition=True):
            if consult is not None:
                zones.IDENTITY_CONSULTED.append(consult)
            if raised is not None:
                raise raised
        return mock.patch.object(L, "check_play_trainer", check)

    def option(self):
        c = L._trainer_candidate(self.state, 1)
        if c is None:
            return None
        stage = c.inputs[0]
        return next((o for o in stage["options"] if o["card"] == self.uid), None)

    def test_outcomes_after_a_consultation_are_discarded(self):
        # 受け付ける・拒否（記録のあとの公開の拒否を含む: リムーブ禁止ジムの追加の条件の形）・停止（MG1 の形）のどれでも、選べるものに残して unverified
        for raised in (None, IllegalActionError("INSUFFICIENT_CARDS_IN_HAND", "x"), UnsupportedError("UNRESOLVED_MIND_GAMES_CHAOS_GYM", "y")):
            with self.subTest(raised=type(raised).__name__), self.fake(consult=0, raised=raised):
                option = self.option()
                self.assertEqual((option["processability"], option["reasons"], option["eligible"]), (L.UNVERIFIED, FACE_DOWN_REASONS, True))
                self.assertIsNone(zones.IDENTITY_CONSULTED)
        with self.fake(raised=IllegalActionError("X", "x")):
            self.assertIsNone(L._trainer_candidate(self.state, 1))  # 読んでいなければ今までどおり（ゲーム上できないものは出さない）

    def test_own_consultation_is_not_counted(self):
        with self.fake(consult=1):
            self.assertEqual(self.option()["processability"], L.MAY_STOP_LATER)

    def test_outer_record_is_kept_and_restored(self):
        outer = ["outer"]
        zones.IDENTITY_CONSULTED = outer
        try:
            with self.fake(consult=0):
                self.assertEqual(self.option()["processability"], L.UNVERIFIED)
            self.assertIs(zones.IDENTITY_CONSULTED, outer)
            self.assertEqual(outer, ["outer"])  # 外側の並びには書かない
        finally:
            zones.IDENTITY_CONSULTED = None

    def test_other_exceptions_propagate_and_the_record_is_restored(self):
        for raised in (RuntimeError("bug"), KeyError("k"), MemoryError(), KeyboardInterrupt(), SystemExit(2)):
            with self.subTest(raised=type(raised).__name__), self.fake(consult=0, raised=raised), self.assertRaises(type(raised)):
                L._trainer_candidate(self.state, 1)
            self.assertIsNone(zones.IDENTITY_CONSULTED)

    def test_power_side_still_uses_the_same_record(self):
        """UP-5t-C1 の入口（_probe_without_opponent_identity）は共通の本体を通る（振る舞いは同じ）。"""
        def check(state, cmd, **kw):
            zones.IDENTITY_CONSULTED.append(1 - cmd.player)
        with mock.patch.object(L, "check_use_pokemon_power", check):
            outcome, consulted = L._probe_without_opponent_identity(self.state, mock.Mock(player=1))
        self.assertEqual((outcome, consulted), ((None, None), True))
        self.assertIsNone(zones.IDENTITY_CONSULTED)


class ExecutionTest(unittest.TestCase):
    """U7・client_api・直接のコマンド: エンジンの受理・拒否は本当のカードによらない（_identity_independent。変えていない）。unverified の check の成功は受理の保証ではない。"""

    def test_three_routes_agree_and_do_not_depend_on_the_real_card(self):
        for name, trainer in TRAINERS.items():
            per_real = []
            for real in REALS.values():
                s = opponent_face_down(trainer, real)
                uid = uid_in_hand(s, 1, trainer)
                direct = A.HostedGame(s.clone()).submit(PlayTrainer(1, uid), submitter=1)
                host = L.ActionHost(A.HostedGame(s.clone()))
                session = host.session(1)
                r = session.candidates()
                c = next(x for x in r["candidates"] if x["kind"] == L.KIND_PLAY_TRAINER)
                option = next(o for o in session.inputs(r["game"], r["revision"], c["id"])["stages"][0]["options"] if o["card"] == uid)
                self.assertTrue(session.check(r["game"], r["revision"], c["id"], [option["id"]])["valid"])  # 構造の検査だけ
                u7 = session.submit(r["game"], r["revision"], c["id"], [option["id"]])
                hub = ClientHub.from_state(s)
                me = hub.player(1)
                rr = me.handle({**REQ, "type": "candidates"})["response"]
                cc = next(x for x in rr["candidates"] if x["kind"] == L.KIND_PLAY_TRAINER)
                h = {"game": rr["game"], "revision": rr["revision"], "candidate": cc["id"]}
                oo = next(o for o in me.handle({**REQ, "type": "inputs", **h})["response"]["stages"][0]["options"] if o["card"] == uid)
                sent = me.handle({**REQ, "type": "submit", **h, "choices": [oo["id"]]})
                with self.subTest(trainer=name, real=real):
                    self.assertEqual(u7.outcome, direct.outcome)
                    self.assertEqual(getattr(u7.view, "diagnostic_id", None), None if direct.diagnosis is None else direct.diagnosis.diagnostic_id)
                    self.assertEqual(sent["outcome"], direct.outcome)
                    if direct.outcome == D.ACCEPTED:
                        self.assertEqual(snap(host.game.state), snap(direct.state))  # 同じ受理・同じ状態（乱数を含む）
                        self.assertTrue(sent["refetch_required"])
                        self.assertTrue(hub.take_updates("spectator"))  # 受理は公開の更新になる（正当。結果は予告していない）
                    else:
                        self.assertEqual(snap(host.game.state), snap(s))  # 拒否は状態を変えない
                        self.assertEqual(hub.take_updates("spectator"), [])
                        self.assertEqual(sent["result"]["role"], "actor")  # 診断は送った本人だけ
                per_real.append(direct.outcome)
            self.assertEqual(len(set(per_real)), 1, (name, per_real))  # 受け付けるかは本当のカードによらない

    def test_rejected_submit_is_private_and_side_effect_free(self):
        """拒否の経路（相手の番に送る。公開の条件）: 状態は変わらず、診断は送った本人だけ。U7 は送信前に取っ手で断る（エンジンへは送らない）。"""
        s = opponent_face_down(H.SLEEP_TRAINER, H.KADABRA)
        uid = uid_in_hand(s, 1, H.SLEEP_TRAINER)
        direct = A.HostedGame(s.clone()).submit(PlayTrainer(0, uid), submitter=0)
        self.assertEqual(direct.outcome, D.REJECTED)
        self.assertEqual(snap(direct.state), snap(s))
        hub = ClientHub.from_state(s)
        me = hub.player(1)
        rr = me.handle({**REQ, "type": "candidates"})["response"]
        cc = next(x for x in rr["candidates"] if x["kind"] == L.KIND_PLAY_TRAINER)
        stale = me.handle({**REQ, "type": "submit", "game": rr["game"], "revision": "r-unknown", "candidate": cc["id"], "choices": ["o1"]})
        self.assertNotEqual(stale.get("outcome"), D.ACCEPTED)  # 取っ手が古い・知らないものは送信前に断る（API の上の意図した差）
        self.assertEqual(snap(hub._host.game.state), snap(s))
        self.assertEqual(hub.take_updates("spectator"), [])
        self.assertEqual(hub.take_updates(0), [])


if __name__ == "__main__":
    unittest.main()
