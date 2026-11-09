"""v0.175（R-3 の U-R3a。docs/legal-actions-u-r3a-v0.175.md）: 本人のうらのカードの、宣言の段が 2〜3 段の特殊能力の構造の入力。

盤面はどれも構築盤面からの合法な列（tests.test_secret_plan_v0_67 の ``board``（build_test_state）から apply_command でマチスの秘策を使い、本当のカードをうらにして
ベンチに出す）。new_game からの到達ではない。確かめること:

- 入力契約: 入力の公開は confirmed、処理可能性は unverified のまま。段は宣言の場所の並び（自分の場 → 選んだポケモンについているカード（→ 自分の場））。
  ついているカードのないポケモンは組が完成しないので 1 段目に出さない。受け付けるか（タイプ・同じポケモン）で組を絞らない
- check は形だけ（段の数・並び・番号・別の経路の番号・型）。候補・inputs・check で状態・乱数・ログ・更新が変わらない
- 情報境界: 相手の秘密（手札の中身。枚数は同じ）だけが違う双子で本人の応答が同じ。本人の本当のカードを変えた盤面で、相手・観戦者の応答が同じ（本人の全知識が同じ双子ではない。
  確かめるのは、他者への応答が本人の本当のカードによらないこと）。選べるものが本人の観測だけから作った参照と同じ
- U7・client_api・直接のコマンドで、受理（ロケット団のヒトカゲ）・おもてにしたあとの拒否（WRONG_ENERGY_TYPE）・トラッシュして受理（フシギバナ。3 段）が同じ
- 選べるもののない場面は入力を返さない（R-3 のまま）
"""

from __future__ import annotations

import json
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from kyuura_engine.commands import UsePokemonPower
from kyuura_engine.observation import observe, visible_log
from tests import helpers as H
from tests import test_secret_plan_v0_67 as S
from tests.test_legal_actions_u7_1 import snap, without_handles

REQ = {"contract": "kyuura-client-api", "format": 1}
RC = H.ROCKET_CHARMANDER  # たね。［ほのおをもらう］（TakeEnergyToSelf: source → energy の 2 段）
VENUSAUR = H.VENUSAUR  # 2 進化。［エナジートランス］（EnergyTransfer: source → energy → target の 3 段）。うらから使うと、おもてにしてトラッシュ
RATTATA_FW = {"card": H.RATTATA, "energy": [H.FIRE, H.WATER]}


def placed(real, *, active=None, opponent_hand=()):
    """プレイヤー 0 の番の MAIN。バトル場は闘エネルギー 2 枚のエビワラー、ベンチは炎・水エネルギーのコラッタと、マチスの秘策でうらにして出した ``real``。"""
    state = S.place(S.board(hand=(real,), bench=(RATTATA_FW,), active=active, opponent_hand=opponent_hand), real)
    fd = S.face_down(state)[0]
    assert fd.energy == [] and fd.damage == 0 and state.decision is None and state.current_player == 0  # 不変条件（うらのあいだは何もついていない・決定待ちでない）
    return state


def power_of(response):
    found = [c for c in response["candidates"] if c["kind"] == L.KIND_USE_POWER and c["power"].get("face_down")]
    assert len(found) == 1, found
    return found[0]


def open_inputs(session):
    r = session.candidates()
    c = power_of(r)
    return r, c, session.inputs(r["game"], r["revision"], c["id"])


def field_ids(state):
    p = state.players[0]
    return {"hitmonchan": p.active, "rattata": p.bench[0], "face_down": S.face_down(state)[0]}


class ContractTest(unittest.TestCase):
    def test_two_stage_structure(self):
        state = placed(RC)
        f = field_ids(state)
        before = snap(state)
        host = L.ActionHost(A.HostedGame(state))
        r, c, inputs = open_inputs(host.session(0))
        self.assertEqual((c["input_disclosure"], c["processability"], c["reasons"]), (L.DISCLOSURE_CONFIRMED, L.UNVERIFIED, [L.REASON_FACE_DOWN]))
        self.assertEqual((c["power"]["card_id"], c["power"]["face_down"], c["guarantees"]), (RC, True, L.GUARANTEE_FACE_DOWN_POWER))
        self.assertNotIn("withheld", inputs)
        first, second = inputs["stages"]
        self.assertEqual((first["role"], first["meaning"], first["count"]), ("source", "pokemon", {"min": 1, "max": 1}))
        # 1 段目: ついているカードのあるポケモンだけ（うらのヒトカゲは何もついていないので組が完成しない）。自分自身・炎でないカードの組も絞らない
        self.assertEqual([(o["id"], o["pokemon"]) for o in first["options"]], [("o1", f["hitmonchan"].pokemon_id), ("o2", f["rattata"].pokemon_id)])
        self.assertEqual((second["role"], second["meaning"], second["depends_on_stage"], second["upstream_stages"]), ("energy", "card", 1, [1]))
        self.assertEqual(second["options_by_choice"], {"o1": [{"option": "o3", "eligible": True, "processability": L.UNVERIFIED, "reasons": [L.REASON_FACE_DOWN]},
                                                              {"option": "o4", "eligible": True, "processability": L.UNVERIFIED, "reasons": [L.REASON_FACE_DOWN]}],
                                                       "o2": [{"option": "o5", "eligible": True, "processability": L.UNVERIFIED, "reasons": [L.REASON_FACE_DOWN]},
                                                              {"option": "o6", "eligible": True, "processability": L.UNVERIFIED, "reasons": [L.REASON_FACE_DOWN]}]})
        self.assertEqual([(o["id"], o["after"], o["card"]) for o in second["options"]],
                         [("o3", "o1", f["hitmonchan"].energy[0]), ("o4", "o1", f["hitmonchan"].energy[1]),
                          ("o5", "o2", f["rattata"].energy[0]), ("o6", "o2", f["rattata"].energy[1])])
        self.assertEqual({(o["processability"], tuple(o["reasons"])) for s in inputs["stages"] for o in s["options"]}, {(L.UNVERIFIED, (L.REASON_FACE_DOWN,))})
        self.assertEqual(L.stage_dependency_problems(inputs["stages"]), [])
        cov = r["coverage"]
        self.assertNotIn(c["id"], cov["withheld_input_candidates"])
        self.assertNotIn("R-3", [i["id"] for i in cov["residual"]["present"]])
        self.assertIn(c["id"], next(p["candidates"] for p in cov["unverified_paths"] if p["reason"] == L.REASON_FACE_DOWN))
        self.assertEqual(snap(host._game.state), before)

    def test_three_stage_structure(self):
        state = placed(VENUSAUR)
        host = L.ActionHost(A.HostedGame(state))
        _r, c, inputs = open_inputs(host.session(0))
        self.assertEqual((c["input_disclosure"], c["processability"]), (L.DISCLOSURE_CONFIRMED, L.UNVERIFIED))  # たねでないことを予告しない（D-U75-REVEAL-OUTCOME）
        self.assertEqual([s["role"] for s in inputs["stages"]], ["source", "energy", "target"])
        third = inputs["stages"][2]
        self.assertEqual((third["depends_on_stage"], third["upstream_stages"]), (2, [1, 2]))
        self.assertEqual(len(third["options"]), 4 * 3)  # (source, energy) の 4 組 × 自分の場の 3 匹（番号は前の段の選び方ごとに別）
        self.assertEqual(L.stage_dependency_problems(inputs["stages"]), [])

    def test_reference_from_the_owner_observation(self):
        """選べるものは、本人の観測（公開の場・ついているカード）だけから作った参照と同じ（real からは印刷の特殊能力と宣言だけを読む）。"""
        state = placed(RC)
        obs = observe(state, 0)["players"][0]
        field = [obs["active"], *obs["bench"]]
        expected_first = [q["pokemon_id"] for q in field if q["energy"]]
        expected_second = {q["pokemon_id"]: [e["card"] for e in q["energy"]] for q in field if q["energy"]}
        _r, _c, inputs = open_inputs(L.ActionHost(A.HostedGame(state)).session(0))
        first, second = inputs["stages"]
        self.assertEqual([o["pokemon"] for o in first["options"]], expected_first)
        by_id = {o["id"]: o for o in second["options"]}
        self.assertEqual({o["pokemon"]: [by_id[ref["option"]]["card"] for ref in second["options_by_choice"][o["id"]]] for o in first["options"]}, expected_second)

    def test_no_complete_tuple_stays_withheld(self):
        """自分の場のどのポケモンにもついているカードがない: 組が完成しないので入力を返さない（R-3 のまま。項目を省いた送信にしない）。"""
        state = S.place(S.board(hand=(RC,), active={"card": H.HITMONCHAN, "energy": []}), RC)
        host = L.ActionHost(A.HostedGame(state))
        r = host.session(0).candidates()
        c = power_of(r)
        self.assertEqual((c["input_disclosure"], c["processability"]), (L.DISCLOSURE_UNCONFIRMED, L.NOT_IMPLEMENTED))
        self.assertIn({"id": "R-3", "scope": L.RESIDUAL_ACTOR, "candidate": c["id"]}, r["coverage"]["residual"]["present"])


class CheckTest(unittest.TestCase):
    def test_shape_only(self):
        state = placed(RC)
        hub = ClientHub(A.HostedGame(state))
        me = hub.player(0)
        r = me.handle({**REQ, "type": "candidates"})["response"]
        c = power_of(r)
        handle = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        me.handle({**REQ, "type": "inputs", **handle})
        before = snap(hub._state())
        cases = {
            (): L.CANDIDATE_INPUT_INVALID,  # 数
            ("o1",): L.CANDIDATE_INPUT_INVALID,  # 2 段目がない
            ("o1", "o5"): L.CANDIDATE_INPUT_INVALID,  # 別の経路（コラッタ）の 2 段目の番号（after が合わない）
            ("o2", "o3"): L.CANDIDATE_INPUT_INVALID,
            ("o3", "o1"): L.CANDIDATE_INPUT_INVALID,  # 段の並び
            ("o1", "o1"): L.CANDIDATE_INPUT_INVALID,  # 1 段目の番号を 2 段目に（重なり）
            ("o1", "o3", "o3"): L.CANDIDATE_INPUT_INVALID,  # 数・重なり
            ("o9", "o3"): L.CANDIDATE_INPUT_INVALID,  # 存在しない番号
            ("o1", "o99"): L.CANDIDATE_INPUT_INVALID,
            (1, "o3"): L.CANDIDATE_INPUT_INVALID,  # 番号の型
            ("o1", "o3"): None,  # 形は合う（闘エネルギーなので、おもてにしたあとエンジンが拒否する。check は受理を保証しない）
            ("o2", "o5"): None,
            ("o2", "o6"): None,
        }
        for choices, code in cases.items():
            with self.subTest(choices=choices):
                answer = me.handle({**REQ, "type": "check", **handle, "choices": list(choices)})["response"]
                self.assertEqual((answer["valid"], None if answer["refusal"] is None else answer["refusal"]["code"]), (code is None, code))
        self.assertEqual(snap(hub._state()), before)
        for audience in (1, "spectator", "host"):
            self.assertEqual(hub.take_updates(audience), [])  # 候補・inputs・check は更新を作らない


class InformationTest(unittest.TestCase):
    def own_responses(self, state):
        host = L.ActionHost(A.HostedGame(state))
        session = host.session(0)
        r, c, inputs = open_inputs(session)
        checks = [session.check(r["game"], r["revision"], c["id"], list(ch)) for ch in ((), ("o1", "o3"), ("o1", "o5"), ("o2", "o5"), ("o9",))]
        return {"candidates": without_handles(r), "inputs": inputs, "checks": checks}

    def others(self, state):
        host = L.ActionHost(A.HostedGame(state))
        hub = ClientHub(A.HostedGame(state.clone()))
        return {"opponent_candidates": without_handles(host.session(1).candidates()), "host_candidates": without_handles(host.host_session().candidates()),
                "observations": [observe(state, viewer) for viewer in (1, None)], "logs": [visible_log(state, viewer) for viewer in (1, None)],
                "client_views": [hub.player(1).handle({**REQ, "type": "view"}), hub.spectator().handle({**REQ, "type": "view"})]}

    def test_opponent_secret_twins(self):
        """本人の知識（本人の観測。real をふくむ）は同じで、相手の手札の中身（枚数は同じ）だけが違う双子: 本人の候補・inputs・check が同じ。"""
        a, b = placed(RC, opponent_hand=(H.RATTATA,)), placed(RC, opponent_hand=(H.ONIX,))
        self.assertEqual(observe(a, 0), observe(b, 0))
        self.assertNotEqual(sorted(a.cards[u].card_id for u in a.players[1].hand), sorted(b.cards[u].card_id for u in b.players[1].hand))
        self.assertEqual(self.own_responses(a), self.own_responses(b))

    def test_others_do_not_depend_on_the_owner_real_card(self):
        """本人の本当のカードだけを変えた盤面（ヒトカゲ・コラッタ・フシギバナ）。本人の観測は real が違うので、本人の全知識が同じ双子ではない。確かめるのは、相手・観戦者・ホストへの
        応答が本人の本当のカードによらないこと。"""
        results = [self.others(placed(real)) for real in (RC, H.RATTATA, VENUSAUR)]
        for other in results[1:]:
            self.assertEqual(other, results[0])
        text = json.dumps(results[0], ensure_ascii=False, default=str)
        self.assertNotIn(RC, text)
        self.assertNotIn("ほのおをもらう", text)


class SameAsDirectTest(unittest.TestCase):
    """U7（ActorSession）・client_api（ClientHub）・直接のコマンド（HostedGame.submit）で同じ結果。"""

    def run_three(self, real, choices, command_of):
        state = placed(real)
        command = command_of(field_ids(state))
        direct_game = A.HostedGame(state.clone())
        direct = direct_game.submit(command, submitter=0)
        host = L.ActionHost(A.HostedGame(state.clone()))
        session = host.session(0)
        r, c, _ = open_inputs(session)
        self.assertTrue(session.check(r["game"], r["revision"], c["id"], list(choices))["valid"])
        via_u7 = session.submit(r["game"], r["revision"], c["id"], list(choices))
        hub = ClientHub(A.HostedGame(state.clone()))
        me = hub.player(0)
        cr = me.handle({**REQ, "type": "candidates"})["response"]
        handle = {"game": cr["game"], "revision": cr["revision"], "candidate": power_of(cr)["id"]}
        via_client = me.handle({**REQ, "type": "submit", **handle, "choices": list(choices)})
        self.assertEqual((via_u7.outcome, via_u7.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual((via_client["outcome"], via_client["result"]), (direct.outcome, direct.view_for(0).to_dict()))
        self.assertEqual(snap(host._game.state), snap(direct_game.state))
        self.assertEqual(snap(hub._state()), snap(direct_game.state))
        stale = session.check(r["game"], r["revision"], c["id"], list(choices))
        return state, direct, direct_game.state, hub, me, handle, stale

    def test_basic_is_revealed_and_uses_the_power(self):
        state, direct, after, hub, _me, _handle, stale = self.run_three(
            RC, ("o2", "o5"), lambda f: UsePokemonPower(0, f["face_down"].pokemon_id, 0, source=f["rattata"].pokemon_id, energy=f["rattata"].energy[0]))
        f = field_ids(state)
        self.assertEqual(direct.outcome, D.ACCEPTED)
        self.assertEqual(stale["refusal"]["code"], L.CANDIDATES_STALE)
        new = [e["kind"] for e in after.log[len(state.log):]]
        self.assertEqual(new[0], "secret_plan_revealed")
        self.assertIn("move_energy", new)
        self.assertNotIn("secret_plan_discarded", new)
        user = next(q for q in after.players[0].bench if q.pokemon_id == f["face_down"].pokemon_id)
        self.assertFalse(after.is_face_down(user))
        self.assertEqual(user.energy, [f["rattata"].energy[0]])  # 炎エネルギーがヒトカゲへ
        self.assertEqual((after.decision, after.current_player), (None, 0))  # 到達: 同じ番の MAIN にもどる（受理のあとの決定はない）
        for viewer in (1, None):  # 受理のあとの公開は既存の処理（おもてにしたカード id が相手・観戦者に見える）
            seen = next(q for q in observe(after, viewer)["players"][0]["bench"] if q["pokemon_id"] == user.pokemon_id)
            self.assertEqual((seen.get("face_down"), seen["card_id"]), (None, RC))
            revealed = [e for e in visible_log(after, viewer) if e["kind"] == "secret_plan_revealed"]
            self.assertEqual([e["card_id"] for e in revealed], [RC])
        self.assertTrue(hub.take_updates(1))

    def test_basic_rejected_after_reveal_is_restored(self):
        state, direct, after, hub, me, handle, stale = self.run_three(
            RC, ("o1", "o3"), lambda f: UsePokemonPower(0, f["face_down"].pokemon_id, 0, source=f["hitmonchan"].pokemon_id, energy=f["hitmonchan"].energy[0]))
        self.assertEqual(direct.outcome, D.REJECTED)
        self.assertEqual((direct.diagnosis.category, direct.verifier.engine_code), (D.INVALID_INPUT, "WRONG_ENERGY_TYPE"))  # 実行前に決めた代表の拒否（闘エネルギーは炎でない）
        self.assertEqual(snap(after), snap(state))  # 状態・乱数・ログ・決定の通し番号がもどる
        self.assertTrue(after.is_face_down(S.face_down(after)[0]))
        self.assertTrue(stale["valid"])  # 拒否では取っ手は失効しない
        for audience in (1, "spectator"):
            self.assertEqual(hub.take_updates(audience), [])
        for viewer in (1, None):
            self.assertNotIn(RC, json.dumps([observe(after, viewer), visible_log(after, viewer)], ensure_ascii=False))
        self.assertTrue(me.handle({**REQ, "type": "check", **handle, "choices": ["o2", "o5"]})["response"]["valid"])

    def test_not_basic_is_revealed_and_trashed(self):
        state, direct, after, hub, _me, _handle, stale = self.run_three(
            VENUSAUR, ("o1", "o3", "o7"),
            lambda f: UsePokemonPower(0, f["face_down"].pokemon_id, 0, source=f["hitmonchan"].pokemon_id, energy=f["hitmonchan"].energy[0],
                                      target=f["hitmonchan"].pokemon_id))
        f = field_ids(state)
        self.assertEqual(direct.outcome, D.ACCEPTED)
        self.assertEqual(stale["refusal"]["code"], L.CANDIDATES_STALE)
        new = [e["kind"] for e in after.log[len(state.log):]]
        self.assertEqual(new[:2], ["secret_plan_revealed", "secret_plan_discarded"])
        self.assertNotIn("move_energy", new)  # 特殊能力はおこらない（入力は読まない）
        self.assertIn(f["face_down"].card, after.players[0].discard)
        self.assertEqual(after.players[0].active.energy, f["hitmonchan"].energy)
        self.assertEqual((after.decision, after.current_player), (None, 0))  # ベンチのカード: 交代の決定はない
        for viewer in (1, None):
            revealed = [e for e in visible_log(after, viewer) if e["kind"] == "secret_plan_revealed"]
            self.assertEqual([e["card_id"] for e in revealed], [VENUSAUR])
            self.assertIn(VENUSAUR, [c["card_id"] for c in observe(after, viewer)["players"][0]["discard"]])
        self.assertTrue(hub.take_updates("spectator"))


if __name__ == "__main__":
    unittest.main()
