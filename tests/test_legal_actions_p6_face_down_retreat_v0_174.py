"""v0.174（R-5 の P6。docs/legal-actions-p6-face-down-retreat.md）: 本人のうらのバトル場のポケモンのにげるの入力。

確かめること（構築盤面。new_game からの到達ではない）:

- 入力契約: 入力の公開は confirmed、処理可能性は unverified のまま、段 1 は控え・段 2 はついているカード（0〜枚数）、total_units・units を省き cost_evaluation で示す
- 情報境界: 本当のカードだけが違う双子（たね・無色・にげる 0 のコラッタ、たね・闘・にげる 3 のイワーク、1 進化・超・にげる 3 のユンゲラー）で、本人の候補・inputs・check の
  応答が同じ。相手・観戦者の応答・観測・ログ・更新に本当のカードが出ない（本人の観測には real があるので、本人の全知識は同じではない）
- check は形だけ（存在しない番号・重なり・段の並び・数）。候補・inputs・check で状態・乱数・ログが変わらない
- U7・client_api・直接のコマンドで、受理（コラッタ）・拒否（イワークのエネルギー不足）・トラッシュして受理（ユンゲラー）の結果・状態・乱数・ログ・診断が同じ
- おもてのにげるの契約は変わらない
"""

from __future__ import annotations

import json
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from kyuura_engine.commands import AttachEnergy, Retreat
from kyuura_engine.observation import observe, visible_log
from tests import helpers as H
from tests import test_secret_plan_v0_67 as S
from tests.test_legal_actions_u7_1 import keys, snap, without_handles

REQ = {"contract": "kyuura-client-api", "format": 1}
TWINS = (H.RATTATA, H.ONIX, H.KADABRA)  # たね・無色・にげる 0 / たね・闘・にげる 3 / 1 進化・超・にげる 3
COST = {"status": L.COST_NOT_EVALUATED, "reason": L.REASON_FACE_DOWN, "omitted": ["total_units", "units"]}


def face_down_active(real):
    """プレイヤー 0 の番。バトル場はうらの ``real``（マチスの秘策）で闘エネルギー 1 枚、ベンチはエネルギーのないエビワラー。にげるはこの番にまだしていない。"""
    state = S.place(S.board(hand=(real, H.FIGHTING)), real)
    state = S.to_active(state, S.face_down(state)[0])
    state = S.opponent_turn(S.opponent_turn(state))
    active = state.players[0].active
    energy = next(u for u in state.players[0].hand if state.cards[u].card_id == H.FIGHTING)
    state = S.apply_command(state, AttachEnergy(0, energy, active.card))
    assert state.is_face_down(state.players[0].active) and len(state.players[0].active.energy) == 1 and len(state.players[0].bench) == 1
    return state


def retreat_of(session):
    r = session.candidates()
    c = next(c for c in r["candidates"] if c["kind"] == L.KIND_RETREAT)
    return r, c, session.inputs(r["game"], r["revision"], c["id"])


class ContractTest(unittest.TestCase):
    def test_candidate_and_stages(self):
        state = face_down_active(H.RATTATA)
        before = snap(state)
        host = L.ActionHost(A.HostedGame(state))
        r, c, inputs = retreat_of(host.session(0))
        self.assertEqual((c["input_disclosure"], c["processability"], c["reasons"]), (L.DISCLOSURE_CONFIRMED, L.UNVERIFIED, [L.REASON_FACE_DOWN]))
        self.assertEqual(c["guarantees"], L.GUARANTEE_FACE_DOWN_RETREAT)
        self.assertEqual([s["stage"] for s in c["input_stages"]], [1, 2])
        self.assertNotIn("withheld", inputs)
        first, second = inputs["stages"]
        self.assertEqual((first["role"], first["count"], [o["id"] for o in first["options"]]), ("new_active", {"min": 1, "max": 1}, ["o1"]))
        bench = state.players[0].bench[0]
        self.assertEqual(first["options"][0], {"id": "o1", "pokemon": bench.pokemon_id, "card": bench.card, "zone": "bench", "bench_index": 0,
                                               "card_id": H.HITMONCHAN, "eligible": True, "processability": L.UNVERIFIED, "reasons": [L.REASON_FACE_DOWN]})
        energy = state.players[0].active.energy[0]
        self.assertEqual((second["role"], second["count"], second["order"], second["distinct"]), ("discard", {"min": 0, "max": 1}, L.ORDER_SIGNIFICANT, True))
        self.assertEqual(second["cost_evaluation"], COST)
        self.assertEqual(second["options"], [{"id": "o2", "card": energy, "card_id": H.FIGHTING, "special": False, "eligible": True,
                                              "processability": L.UNVERIFIED, "reasons": [L.REASON_FACE_DOWN]}])
        present = set(keys([r, inputs]))  # 項目の名前として（omitted・note の文の中の名前は数えない）
        self.assertFalse({"total_units", "units"} & present)
        cov = r["coverage"]
        self.assertNotIn(c["id"], cov["withheld_input_candidates"])
        self.assertNotIn({"id": "R-5", "scope": L.RESIDUAL_ACTOR, "candidate": c["id"]}, cov["residual"]["present"])
        self.assertIn(c["id"], next(p["candidates"] for p in cov["unverified_paths"] if p["reason"] == L.REASON_FACE_DOWN))
        self.assertEqual(snap(host._game.state), before)  # 候補・inputs で状態・乱数・ログが変わらない

    def test_face_up_retreat_is_unchanged(self):
        state = S.board(bench=(H.RATTATA,))  # おもてのエビワラー（闘エネルギー 2 枚・にげる 2）
        _r, c, inputs = retreat_of(L.ActionHost(A.HostedGame(state)).session(0))
        second = inputs["stages"][1]
        self.assertEqual(c["guarantees"], L.GUARANTEE_TURN_ACTION)
        self.assertNotIn("cost_evaluation", second)
        self.assertEqual(second["total_units"], {"min": 2, "max": 2})
        self.assertEqual([sorted(o) for o in second["options"]], [sorted(["id", "card", "card_id", "special", "units", "processability"])] * 2)
        self.assertEqual([o["units"] for o in second["options"]], [1, 1])


class CheckTest(unittest.TestCase):
    def test_shape_only(self):
        state = face_down_active(H.ONIX)
        host = L.ActionHost(A.HostedGame(state))
        session = host.session(0)
        r, c, _inputs = retreat_of(session)
        before = snap(host._game.state)
        cases = {
            (): L.CANDIDATE_INPUT_INVALID,  # 控えがない
            ("o9",): L.CANDIDATE_INPUT_INVALID,  # 存在しない控え
            ("o1", "o9"): L.CANDIDATE_INPUT_INVALID,  # 存在しないエネルギー
            ("o2",): L.CANDIDATE_INPUT_INVALID,  # 段の並びが違う（エネルギーが先）
            ("o2", "o1"): L.CANDIDATE_INPUT_INVALID,
            ("o1", "o1"): L.CANDIDATE_INPUT_INVALID,  # 控えを 2 回
            ("o1", "o2", "o2"): L.CANDIDATE_INPUT_INVALID,  # 重なり（枚数を超える）
            (1,): L.CANDIDATE_INPUT_INVALID,  # 番号の型
            ("o1",): None,  # エネルギー 0 枚（形は合う。足りるかはエンジン）
            ("o1", "o2"): None,  # イワークのにげる 3 には足りないが、check は費用を見ない
        }
        for choices, code in cases.items():
            with self.subTest(choices=choices):
                answer = session.check(r["game"], r["revision"], c["id"], list(choices))
                self.assertEqual((answer["valid"], None if answer["refusal"] is None else answer["refusal"]["code"]), (code is None, code))
        self.assertEqual(snap(host._game.state), before)  # check で状態・乱数・ログが変わらない


class TwinTest(unittest.TestCase):
    """本当のカードだけが違う双子（公開の情報と、本人の手札・場の公開の値は同じ。本人の観測の real は違う）。"""

    def responses(self, real):
        state = face_down_active(real)
        host = L.ActionHost(A.HostedGame(state))
        session = host.session(0)
        r, c, inputs = retreat_of(session)
        checks = [session.check(r["game"], r["revision"], c["id"], list(ch)) for ch in ((), ("o1",), ("o1", "o2"), ("o2",), ("o1", "o2", "o2"), ("o9",))]
        hub = ClientHub(A.HostedGame(state.clone()))
        envelope = hub.player(0).handle({**REQ, "type": "candidates"})
        others = {
            "opponent_candidates": without_handles(host.session(1).candidates()),
            "host_candidates": without_handles(host.host_session().candidates()),
            "observations": [observe(state, viewer) for viewer in (1, None)],
            "logs": [visible_log(state, viewer) for viewer in (1, None)],
            "client_views": [hub.player(1).handle({**REQ, "type": "view"}), hub.spectator().handle({**REQ, "type": "view"})],
        }
        own = {"candidates": without_handles(r), "inputs": inputs, "checks": checks,
               "client_candidates": {k: v for k, v in envelope["response"].items() if k not in ("game", "revision")}}
        return state, own, others

    def test_twins_are_the_same(self):
        results = [self.responses(real) for real in TWINS]
        states = [s for s, _own, _others in results]
        self.assertEqual(len({s.cards[s.players[0].active.card].card_id for s in states}), 3)  # 本当のカードは違う
        self.assertNotEqual(observe(states[0], 0), observe(states[1], 0))  # 本人の観測は real が違う（本人の全知識は同じでない）
        for _state, own, others in results[1:]:
            self.assertEqual(own, results[0][1])  # 件数・並び・制約・理由・check の答えが本当のカード（費用・タイプ・段階）によらない
            self.assertEqual(others, results[0][2])
        for state, own, others in results:
            real = state.cards[state.players[0].active.card].card_id
            self.assertNotIn(real, json.dumps(own, ensure_ascii=False))  # 本人の候補・入力にも本当のカード ID を書かない
            self.assertNotIn(real, json.dumps(others, ensure_ascii=False, default=str))


class SameAsDirectTest(unittest.TestCase):
    """U7（ActorSession）・client_api（ClientHub）・直接のコマンド（HostedGame.submit）で同じ結果。"""

    def run_three(self, real, choices, command_of):
        state = face_down_active(real)
        bench, energy = state.players[0].bench[0].card, state.players[0].active.energy[0]
        command = command_of(bench, energy)
        direct_game = A.HostedGame(state.clone())
        direct = direct_game.submit(command, submitter=0)
        host = L.ActionHost(A.HostedGame(state.clone()))
        session = host.session(0)
        r, c, _ = retreat_of(session)
        via_u7 = session.submit(r["game"], r["revision"], c["id"], list(choices))
        hub = ClientHub(A.HostedGame(state.clone()))
        me = hub.player(0)
        cr = me.handle({**REQ, "type": "candidates"})["response"]
        cid = next(x["id"] for x in cr["candidates"] if x["kind"] == L.KIND_RETREAT)
        handle = {"game": cr["game"], "revision": cr["revision"], "candidate": cid}
        via_client = me.handle({**REQ, "type": "submit", **handle, "choices": list(choices)})
        self.assertEqual((via_u7.outcome, via_u7.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual((via_client["outcome"], via_client["result"]), (direct.outcome, direct.view_for(0).to_dict()))
        self.assertEqual(snap(host._game.state), snap(direct_game.state))
        self.assertEqual(snap(hub._state()), snap(direct_game.state))
        stale = session.check(r["game"], r["revision"], c["id"], list(choices))
        return state, direct, direct_game.state, hub, me, handle, stale

    def test_basic_is_revealed_and_retreats(self):
        state, direct, after, hub, _me, _handle, stale = self.run_three(H.RATTATA, ("o1",), lambda bench, energy: Retreat(0, (), bench))
        self.assertEqual(direct.outcome, D.ACCEPTED)
        self.assertEqual(stale["refusal"]["code"], L.CANDIDATES_STALE)  # 受理で取っ手は失効する
        self.assertEqual(after.players[0].active.card, state.players[0].bench[0].card)  # エビワラーがバトル場へ
        revealed = next(q for q in after.players[0].bench if q.card == state.players[0].active.card)
        self.assertFalse(after.is_face_down(revealed))
        self.assertEqual(len(revealed.energy), 1)  # にげる 0: トラッシュしない
        self.assertEqual([e["kind"] for e in after.log if e["kind"] == "secret_plan_revealed"], ["secret_plan_revealed"])
        self.assertEqual((after.decision, after.current_player), (None, 0))  # 到達: 同じ番の MAIN にもどる
        self.assertTrue(hub.take_updates(1))  # 受理は公開の更新になる（おもてにしたカードは全員に公開。既存の処理）

    def test_basic_without_enough_energy_is_rejected_and_restored(self):
        state, direct, after, hub, me, handle, stale = self.run_three(H.ONIX, ("o1", "o2"), lambda bench, energy: Retreat(0, (energy,), bench))
        self.assertEqual(direct.outcome, D.REJECTED)
        self.assertEqual(snap(after), snap(state))  # 状態・乱数・ログ・決定の通し番号がもどる（おもてにしたことも残らない）
        self.assertTrue(after.is_face_down(after.players[0].active))
        view = direct.view_for(0)
        self.assertEqual((view.outcome, view.diagnostic_id is not None), (D.REJECTED, True))  # 診断は送った本人への見え方にある（U7・client_api と同じことは run_three で比べた）
        self.assertTrue(stale["valid"])  # 拒否では取っ手は失効しない
        for audience in (1, "spectator"):
            self.assertEqual(hub.take_updates(audience), [])  # 拒否は公開の更新にしない
        self.assertEqual(me.handle({**REQ, "type": "check", **handle, "choices": ["o1", "o2"]})["response"]["valid"], True)
        for viewer in (1, None):
            self.assertNotIn(H.ONIX, json.dumps(observe(after, viewer), ensure_ascii=False))

    def test_not_basic_is_revealed_and_trashed(self):
        state, direct, after, hub, _me, _handle, stale = self.run_three(H.KADABRA, ("o1",), lambda bench, energy: Retreat(0, (), bench))
        self.assertEqual(direct.outcome, D.ACCEPTED)
        self.assertEqual(stale["refusal"]["code"], L.CANDIDATES_STALE)
        self.assertIsNone(after.players[0].active)  # ついているカードといっしょにトラッシュ（にげるはおこらない）
        self.assertIn(state.players[0].active.card, after.players[0].discard)
        self.assertIn(state.players[0].active.energy[0], after.players[0].discard)
        self.assertEqual([e["kind"] for e in after.log[len(state.log):]][:2], ["secret_plan_revealed", "secret_plan_discarded"])
        self.assertEqual((after.decision.kind, after.decision.player), ("promote_active", 0))  # 到達: バトル場に出す決定まで（答えていない）
        self.assertTrue(hub.take_updates("spectator"))


if __name__ == "__main__":
    unittest.main()
