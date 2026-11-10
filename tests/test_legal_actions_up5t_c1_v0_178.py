"""v0.178（UP-5t-C1。docs/legal-actions-up5t-audit.md 11 章）: 特殊能力の使うための条件の候補の側の確かめが、相手のうらのカードの本当のカードを使ったら、
その結果を候補に使わない（unverified・face_down_reveal_not_evaluated）。

対象: ``CoinConditionOnEitherActive`` の［くさいかふん］（わるいクサイハナ PMCG4-006）・［えんかくさいみん］（スリープ PMCG4-033）。状態の複製の上でおたがいの
対戦ポケモンを特殊状態にして試し、相手の対戦ポケモンがうらのカード（マチスの秘策）なら ``zones.designate_face_down`` が本当のカードを読む（監査の 3.1 節）。

盤面はどれも構築盤面（``tests/test_secret_plan_v0_67.py`` の ``board``・``place``・``to_active``・``face_down`` と ``build_test_state``。プレイヤー 0 がうらにして出したカードに、
にげるで入れ替え、番を終える）。new_game からの到達ではない。双子は、プレイヤー 0 のうらのカードの本当のカード（たねポケモン・たねポケモンでないカード・メタモン）だけが違い、
プレイヤー 1（使う人）と観戦者の観測・公開のログが同じ（プレイヤー 0 の観測は本当のカードを含むので違う）。
"""

from __future__ import annotations

import unittest
from unittest import mock

from kyuura_engine import EndTurn, UsePokemonPower, apply_command
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
POWERS = {"くさいかふん": {"card": "PMCG4-006", "evolved_from": "PMCG4-003"}, "えんかくさいみん": {"card": "PMCG4-033"}}
REALS = {"basic": H.RATTATA, "stage1": H.KADABRA, "ditto": H.DITTO}  # たねポケモン・たねポケモンでない（おもてにするとトラッシュ）・メタモン（［へんしん］）


def opponent_face_down(power, real, **user):
    """プレイヤー 1 の番の MAIN。プレイヤー 1 のバトル場に特殊能力のポケモン、プレイヤー 0 のバトル場にうらのカード（本当のカードは ``real``）。"""
    s = board(hand=(real,), opponent={**POWERS[power], **user}, turn_number=5)
    s = place(s, real)
    s = to_active(s, face_down(s)[0])
    s = apply_command(s, EndTurn(0))
    assert s.current_player == 1 and s.decision is None and check_invariants(s) == [] and s.is_face_down(s.players[0].active)
    return s


def opponent_face_up(power):
    s = board(opponent=POWERS[power], turn_number=5)
    s = apply_command(s, EndTurn(0))
    assert s.current_player == 1 and check_invariants(s) == []
    return s


def own_face_down(power, real):
    """プレイヤー 0 の番。自分のバトル場がうらのカード（本人は本当のカードを知る）、自分のベンチに特殊能力のポケモン。"""
    s = board(hand=(real,), bench=[POWERS[power]], turn_number=5)
    s = place(s, real)
    s = to_active(s, face_down(s)[0])
    assert s.current_player == 0 and check_invariants(s) == [] and s.is_face_down(s.players[0].active)
    return s


def power_queries(state, actor):
    """client_api の入口で、本人の候補（取っ手を除く）・特殊能力の候補ごとの inputs と check（[]・不正な入力）。他者への更新と、前後の状態・記録の並び。"""
    hub = ClientHub.from_state(state)
    me = hub.player(actor)
    before = snap(hub._host.game.state)
    r = me.handle({**REQ, "type": "candidates"})["response"]
    uses = []
    for c in r["candidates"]:
        if c["kind"] != L.KIND_USE_POWER:
            continue
        h = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        uses.append({"candidate": without_handles(c), "inputs": without_handles(me.handle({**REQ, "type": "inputs", **h})["response"]),
                     "check": me.handle({**REQ, "type": "check", **h, "choices": []})["response"],
                     "check_bad": me.handle({**REQ, "type": "check", **h, "choices": ["o1"]})["response"]})
    others = [hub.take_updates(a) for a in (1 - actor, "spectator")]
    return {"candidates": without_handles(r), "uses": uses}, others, snap(hub._host.game.state) == before


def power_of(uses, name):
    return [u for u in uses if u["candidate"]["power"]["name_ja"] == name]


class TwinTest(unittest.TestCase):
    def test_twins_share_the_actor_and_spectator_knowledge(self):
        for power in POWERS:
            states = {n: opponent_face_down(power, real) for n, real in REALS.items()}
            first = next(iter(states.values()))
            for n, s in states.items():
                with self.subTest(power=power, real=n):
                    self.assertEqual((observe(s, 1), observe(s, None), visible_log(s, 1), visible_log(s, None)),
                                     (observe(first, 1), observe(first, None), visible_log(first, 1), visible_log(first, None)))
            self.assertEqual(len({str(observe(s, 0)) for s in states.values()}), len(states))  # 持ち主の観測は本当のカードを含む（知識は同じでない）
            self.assertEqual(len({str(snap(s)) for s in states.values()}), len(states))

    def test_candidates_inputs_check_do_not_depend_on_the_real_card(self):
        for power in POWERS:
            results = {}
            for n, real in REALS.items():
                s = opponent_face_down(power, real)
                out, others, unchanged = power_queries(s, 1)
                self.assertEqual(others, [[], []])  # 相手・観戦者へ本人の候補・診断を出さない
                self.assertTrue(unchanged)
                self.assertIsNone(zones.IDENTITY_CONSULTED)
                results[n] = out
            with self.subTest(power=power):
                self.assertEqual(len({str(v) for v in results.values()}), 1)
                [use] = power_of(results["basic"]["uses"], power)
                c = use["candidate"]
                self.assertEqual((c["processability"], c["reasons"], c["input_disclosure"], c["input_stages"]),
                                 (L.UNVERIFIED, [L.REASON_FACE_DOWN], L.DISCLOSURE_NONE, []))
                self.assertEqual(use["inputs"]["stages"], [])
                self.assertEqual((use["check"]["valid"], use["check_bad"]["valid"], use["check_bad"]["refusal"]["code"]), (True, False, L.CANDIDATE_INPUT_INVALID))

    def test_the_real_card_is_read_before_the_fix_point(self):
        """候補の作成のあいだに、相手のうらのカードの本当のカードを読む処理は今も呼ばれる（試行は変えていない）。読んだことが記録され、結果を使わない。"""
        s = opponent_face_down("くさいかふん", H.KADABRA)
        seen = []
        original = zones._secret_plan_keeps

        def spy(state, card):
            seen.append((card == s.players[0].active.card, list(zones.IDENTITY_CONSULTED or [])))
            return original(state, card)
        with mock.patch.object(zones, "_secret_plan_keeps", spy):
            L.ActionHost(A.HostedGame(s.clone())).session(1).candidates()
        self.assertTrue(seen)
        self.assertTrue(all(is_target and consulted == [0] for is_target, consulted in seen))  # 読む前に相手（0）が記録されている


class ControlTest(unittest.TestCase):
    def test_face_up_opponent_is_evaluated(self):
        for power in POWERS:
            out, _others, _ = power_queries(opponent_face_up(power), 1)
            [use] = power_of(out["uses"], power)
            self.assertEqual((use["candidate"]["processability"], use["candidate"]["reasons"]), (L.MAY_STOP_LATER, [L.REASON_CONTINUATION]))

    def test_own_face_down_active_is_evaluated_with_own_knowledge(self):
        for power in POWERS:
            for n, real in REALS.items():
                with self.subTest(power=power, real=n):
                    out, _others, _ = power_queries(own_face_down(power, real), 0)
                    uses = power_of(out["uses"], power)
                    self.assertTrue(all(L.REASON_FACE_DOWN not in u["candidate"]["reasons"] for u in uses))  # 本人の知識なので評価する（一律に未評価にしない）

    def test_publicly_unusable_power_is_not_offered_in_any_twin(self):
        for power in POWERS:
            outs = []
            for real in REALS.values():
                out, _others, _ = power_queries(opponent_face_down(power, real, confusion=True), 1)  # こんらんのポケモンは使えない（公開の条件。試行の前に断る。ねむりは相手の番の終わりのポケモンチェックで治りうるので使わない）
                outs.append(out)
                self.assertEqual(power_of(out["uses"], power), [])
            self.assertEqual(len({str(o) for o in outs}), 1)


class RecordingTest(unittest.TestCase):
    def setUp(self):
        self.state = opponent_face_up("くさいかふん")
        self.cmd = UsePokemonPower(1, self.state.players[1].active.pokemon_id, 0)

    def fake(self, *, consult, raised=None):
        def check(state, cmd, **kw):
            if consult:
                zones.IDENTITY_CONSULTED.append(0)
            if raised is not None:
                raise raised
        return mock.patch.object(L, "check_use_pokemon_power", check)

    def test_outcomes_after_a_consultation_are_discarded(self):
        for raised in (None, IllegalActionError("X", "x"), UnsupportedError("Y", "y")):
            with self.subTest(raised=type(raised).__name__), self.fake(consult=True, raised=raised):
                self.assertEqual(L._power_verdict(self.state, self.cmd, False), (L.UNVERIFIED, [L.REASON_FACE_DOWN]))
                self.assertIsNone(zones.IDENTITY_CONSULTED)
        with self.fake(consult=False, raised=IllegalActionError("X", "x")):
            self.assertIsNone(L._power_verdict(self.state, self.cmd, False))  # 読んでいなければ今までどおり（候補にしない）

    def test_own_consultation_is_not_counted(self):
        def check(state, cmd, **kw):
            zones.IDENTITY_CONSULTED.append(cmd.player)
        with mock.patch.object(L, "check_use_pokemon_power", check):
            self.assertEqual(L._power_verdict(self.state, self.cmd, False), (L.MAY_STOP_LATER, [L.REASON_CONTINUATION]))

    def test_outer_record_is_kept_and_restored(self):
        outer = ["outer"]
        zones.IDENTITY_CONSULTED = outer
        try:
            with self.fake(consult=True):
                self.assertEqual(L._power_verdict(self.state, self.cmd, False)[0], L.UNVERIFIED)
            self.assertIs(zones.IDENTITY_CONSULTED, outer)
            self.assertEqual(outer, ["outer"])  # 外側の並びには書かない
        finally:
            zones.IDENTITY_CONSULTED = None

    def test_other_exceptions_propagate_and_the_record_is_restored(self):
        for raised in (RuntimeError("bug"), KeyError("k"), MemoryError(), KeyboardInterrupt(), SystemExit(2)):
            with self.subTest(raised=type(raised).__name__), self.fake(consult=True, raised=raised), self.assertRaises(type(raised)):
                L._power_verdict(self.state, self.cmd, False)
            self.assertIsNone(zones.IDENTITY_CONSULTED)


class ExecutionTest(unittest.TestCase):
    """U7・client_api・直接のコマンド: エンジンの受理・拒否は本当のカードによらない（_identity_independent。変えていない）。unverified の check の成功は受理の保証ではない。"""

    def outcome(self, result):
        return (result.outcome, None if result.diagnosis is None else result.diagnosis.diagnostic_id)

    def test_three_routes_agree_and_do_not_depend_on_the_real_card(self):
        for power in POWERS:
            per_real = []
            for real in REALS.values():
                s = opponent_face_down(power, real)
                pid = s.players[1].active.pokemon_id
                direct = A.HostedGame(s.clone()).submit(UsePokemonPower(1, pid, 0), submitter=1)
                host = L.ActionHost(A.HostedGame(s.clone()))
                session = host.session(1)
                r = session.candidates()
                c = next(x for x in r["candidates"] if x["kind"] == L.KIND_USE_POWER and x["power"]["name_ja"] == power)
                self.assertTrue(session.check(r["game"], r["revision"], c["id"], [])["valid"])  # 構造の検査だけ
                u7 = session.submit(r["game"], r["revision"], c["id"], [])
                hub = ClientHub.from_state(s)
                me = hub.player(1)
                rr = me.handle({**REQ, "type": "candidates"})["response"]
                cc = next(x for x in rr["candidates"] if x["kind"] == L.KIND_USE_POWER and x["power"]["name_ja"] == power)
                sent = me.handle({**REQ, "type": "submit", "game": rr["game"], "revision": rr["revision"], "candidate": cc["id"], "choices": []})
                with self.subTest(power=power, real=real):
                    self.assertEqual(u7.outcome, direct.outcome)
                    self.assertEqual(getattr(u7.view, "diagnostic_id", None), None if direct.diagnosis is None else direct.diagnosis.diagnostic_id)
                    self.assertEqual(sent["outcome"], direct.outcome)
                    if direct.outcome == D.ACCEPTED:
                        self.assertEqual(snap(host.game.state), snap(direct.state))  # 同じ受理・同じ状態（乱数を含む）
                        self.assertTrue(sent["refetch_required"])
                        self.assertTrue(hub.take_updates("spectator"))  # 受理は公開の更新になる（正当）
                    else:
                        self.assertEqual(snap(host.game.state), snap(s))  # 拒否は状態を変えない
                        self.assertEqual(hub.take_updates("spectator"), [])
                        self.assertEqual(sent["result"]["role"], "actor")  # 診断は送った本人だけ
                per_real.append(direct.outcome)
            self.assertEqual(len(set(per_real)), 1, per_real)  # 受け付けるかは本当のカードによらない


if __name__ == "__main__":
    unittest.main()
