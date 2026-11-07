"""v0.165（U7-3。docs/legal-actions-u7-3.md）: 番の基本の操作（ベンチに出す・エネルギーをつける・進化させる・にげる）の候補・入力・送信の回帰テスト。

確かめの種類を分ける:

- 構築盤面（tests.helpers.build_test_state・状態の写しの項目を変える）: 各操作の正常・拒否、ベンチの上限、ベイビィ、つけた数、進化の制限、にげるの費用、反応、双子
- 補助の作り（v0.50 のテストの退化の盤面を使う）: この番に退化したポケモンの進化（DV2）
- new_game からの合法な操作の列: 準備から U7 だけで番の基本の操作に進む接続（3 つの規約集合。直接のコマンドと同じ状態）

停止コードの文字列はテストの中に書かない（区分とホストの段のコードで確かめる）。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from kyuura_engine.commands import (
    AttachEnergy,
    EndTurn,
    EvolvePokemon,
    PlayBasicToBench,
    Retreat,
)
from kyuura_engine.observation import observe
from kyuura_engine.stadiums import bench_limit
from kyuura_engine.view_record import FORBIDDEN_KEYS
from tests import helpers as H
from tests import test_mew_devolution_v0_50 as T50
from tests.log_audit import owned_card_ids, public_view
from tests.test_legal_actions_u7_1 import keys, snap, without_handles

ROOT = pathlib.Path(__file__).resolve().parent.parent
BABY = "neo1-022"  # ブビィ（ベイビィ。進化先 ブーバー = H.MAGMAR。にげる 0）
DCE = "PMCG1-096"  # 無色2個エネルギー（特殊エネルギー。1 枚で 2 個）
ENTEI = "neo3-010"
FOSSIL = "PMCG3-046"  # なにかの化石（手札ではトレーナー。場に出すのは PlayTrainer）
CHARIZARD = "PMCG1-021"  # リザードン（リザードから進化）  # エンテイ（手札から場に出したときの特殊能力［おたけび］）
SETS = (None, "CS-KYUURA-PLAY-S2A@1", "CS-KYUURA-PLAY-PO@1")
CONTRACT = {"contract": "kyuura-client-api", "format": 1}
OPPONENT = {"active": H.STARYU, "hand": [H.WATER], "deck": [H.WATER] * 5, "prizes": 2}


def board(p0, p1=None, *, turn=3, attachments=0):
    return H.build_test_state([{"deck": [H.FIRE] * 5, "prizes": 2, **p0}, dict(p1 or OPPONENT)], turn_number=turn, energy_attachments_this_turn=attachments)


def host_of(state):
    return L.ActionHost(A.HostedGame(state))


def cand(response, kind):
    return next((c for c in response["candidates"] if c["kind"] == kind), None)


def inputs_of(session, kind):
    r = session.candidates()
    c = cand(r, kind)
    return r, c, (None if c is None else session.inputs(r["game"], r["revision"], c["id"]))


def option_id(stage, **match):
    return next(o["id"] for o in stage["options"] if all(o.get(k) == v for k, v in match.items()))


def uid_of(state, player, card_id, zone="hand"):
    cards = state.players[player].hand if zone == "hand" else [q.card for q in state.players[player].in_play()]
    return next(u for u in cards if state.cards[u].card_id == card_id)


def first_pair(stages):
    for option in stages[0]["options"]:
        for pair in stages[1]["options_by_choice"][option["id"]]:
            if pair["eligible"]:
                return [option["id"], pair["option"]]
    return None


def retreat_choices(stages):
    """控えの先頭と、出すエネルギーの個数が下限に届くまでのエネルギー（選んだ順）。"""
    bench, energy = stages
    choices, units = [bench["options"][0]["id"]], 0
    for option in energy["options"]:
        if units >= energy["total_units"]["min"]:
            break
        choices.append(option["id"])
        units += option["units"]
    return choices


def via_u7(state, kind, pick):
    host = host_of(state.clone())
    session = host.session(state.current_player)
    r, c, inputs = inputs_of(session, kind)
    choices = pick(inputs["stages"])
    return host, session.submit(r["game"], r["revision"], c["id"], choices)


def via_direct(state, command):
    game = A.HostedGame(state.clone())
    return game, game.submit(command, submitter=command.player)


class Same:
    def assert_same_as_direct(self, state, kind, pick, command):
        host, result = via_u7(state, kind, pick)
        game, direct = via_direct(state, command)
        self.assertEqual(result.outcome, D.ACCEPTED, result)
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(command.player)))
        self.assertEqual(snap(host.game.state), snap(game.state))
        return host.game.state


class MappingTest(unittest.TestCase):
    """対応表（docs/legal-actions-u7-3.md 2 章）: 4 種類は 4 つのコマンドだけ。ほかの入口（トレーナー・特殊能力・ワザ）は対応しない種類のまま。"""

    def test_kinds_and_coverage(self):
        self.assertEqual(L.TURN_KINDS, ("play_basic", "attach_energy", "evolve", "retreat"))
        r = host_of(board({"active": H.CHARMANDER, "hand": []})).session(0).candidates()
        cov = r["coverage"]
        self.assertEqual(cov["completeness"], L.PARTIAL)
        self.assertEqual(cov["offered_kinds"], [L.KIND_END_TURN])  # 手札がなく控えもいない: 番の基本の操作はどれもゲーム上できない（候補なし）
        self.assertEqual(cov["scope_kinds"], list(L.MAIN_KINDS))  # 評価した種類と、対応しない種類
        self.assertEqual(cov["not_covered_kinds"], ["play_trainer",  # v0.166（U7-4）: use_attack は対応した種類（ここではエネルギーがなくワザの候補はない）
                                                    "use_power", "use_stadium",  # v0.167（U7-5a・U7-5b）: 場のポケモン 1 匹を指す 3 種類は対応した種類
                                                    "check_face_up_deck"])
        for kind in L.TURN_KINDS:
            self.assertIn(kind, cov["implemented_kinds"])

    def test_fossil_in_hand_is_not_play_basic(self):
        # 化石・人形を場に出すのはトレーナーを使う操作（PlayTrainer。U7-5）。ベンチに出す候補の選べるものにしない
        state = board({"active": H.CHARMANDER, "hand": [T50.KADABRA, FOSSIL, H.PONYTA]})
        _, _c, inputs = inputs_of(host_of(state).session(0), L.KIND_PLAY_BASIC)
        self.assertEqual([o["card_id"] for o in inputs["stages"][0]["options"]], [H.PONYTA])


class PlayBasicTest(Same, unittest.TestCase):
    def test_normal_and_same_as_direct(self):
        state = board({"active": H.CHARMANDER, "hand": [H.CHARMELEON, H.PONYTA, H.FIRE, BABY]})
        _, c, inputs = inputs_of(host_of(state).session(0), L.KIND_PLAY_BASIC)
        stage = inputs["stages"][0]
        self.assertEqual([o["card_id"] for o in stage["options"]], [H.PONYTA, BABY])  # たね・ベイビィ。手札の並び
        self.assertEqual((c["processability"], stage["bench"]), (L.SUPPORTED, {"count": 0, "limit": bench_limit(state, 0)}))
        for card_id in (H.PONYTA, BABY):
            after = self.assert_same_as_direct(state, L.KIND_PLAY_BASIC, lambda s, cid=card_id: [option_id(s[0], card_id=cid)],
                                               PlayBasicToBench(0, uid_of(state, 0, card_id)))
            self.assertEqual(after.cards[after.players[0].bench[-1].card].card_id, card_id)

    def test_bench_full_is_not_offered(self):
        state = board({"active": H.CHARMANDER, "bench": [H.GROWLITHE] * 5, "hand": [H.PONYTA]})
        r = host_of(state).session(0).candidates()
        self.assertIsNone(cand(r, L.KIND_PLAY_BASIC))
        self.assertIn(L.KIND_PLAY_BASIC, r["coverage"]["scope_kinds"])
        self.assertNotIn(L.KIND_PLAY_BASIC, r["coverage"]["offered_kinds"])

    def test_invalid_inputs(self):
        state = board({"active": H.CHARMANDER, "hand": [H.PONYTA, H.PONYTA]})
        session = host_of(state).session(0)
        r, c, _ = inputs_of(session, L.KIND_PLAY_BASIC)
        for choices in ([], ["o1", "o2"], ["o9"], [1], ["o1", "o1"], "o1", [["o1"]]):
            self.assertEqual(session.check(r["game"], r["revision"], c["id"], choices)["refusal"]["code"], L.CANDIDATE_INPUT_INVALID, choices)
        self.assertTrue(session.check(r["game"], r["revision"], c["id"], ["o2"])["valid"])

    def test_entry_power_leads_to_a_decision(self):
        state = board({"active": H.CHARMANDER, "hand": [ENTEI]})
        session = host_of(state).session(0)
        r, c, inputs = inputs_of(session, L.KIND_PLAY_BASIC)
        option = inputs["stages"][0]["options"][0]
        self.assertEqual((option["processability"], option["reasons"]), (L.MAY_STOP_LATER, [L.REASON_REACTIONS]))  # 特殊能力を持つカード
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], ["o1"]).outcome, D.ACCEPTED)
        after = session.candidates()
        self.assertEqual([x["kind"] for x in after["candidates"]], [L.KIND_ANSWER_DECISION])  # 受理のあとの決定（使うかを聞く）


class AttachTest(Same, unittest.TestCase):
    def test_normal_targets_and_same_as_direct(self):
        state = board({"active": H.CHARMANDER, "bench": [H.GROWLITHE], "hand": [H.FIRE, H.WATER, H.PONYTA]})
        _, c, inputs = inputs_of(host_of(state).session(0), L.KIND_ATTACH_ENERGY)
        energy, target = inputs["stages"]
        self.assertEqual([(o["card_id"], o["special"]) for o in energy["options"]], [(H.FIRE, False), (H.WATER, False)])
        self.assertEqual([(o["zone"], o["card_id"]) for o in target["options"]], [("active", H.CHARMANDER), ("bench", H.GROWLITHE)])
        self.assertEqual({k: [p["option"] for p in v] for k, v in target["options_by_choice"].items()}, {"o1": ["o3", "o4"], "o2": ["o3", "o4"]})
        self.assertEqual(c["processability"], L.SUPPORTED)
        bench = state.players[0].bench[0].card
        self.assert_same_as_direct(state, L.KIND_ATTACH_ENERGY, lambda s: [option_id(s[0], card_id=H.WATER), option_id(s[1], zone="bench")],
                                   AttachEnergy(0, uid_of(state, 0, H.WATER), bench))

    def test_once_per_turn(self):
        state = board({"active": H.CHARMANDER, "hand": [H.FIRE]}, attachments=1)
        r = host_of(state).session(0).candidates()
        self.assertIsNone(cand(r, L.KIND_ATTACH_ENERGY))  # その番にもうつけた（ゲーム上できない）
        self.assertIn(L.KIND_ATTACH_ENERGY, r["coverage"]["scope_kinds"])

    def test_special_energy_is_not_basic(self):
        state = board({"active": H.CHARMANDER, "hand": [DCE, H.FIRE]})
        _, c, inputs = inputs_of(host_of(state).session(0), L.KIND_ATTACH_ENERGY)
        energy = inputs["stages"][0]
        dce, fire = energy["options"]
        self.assertEqual((dce["special"], dce["processability"], fire["special"], fire["processability"]), (True, L.MAY_STOP_LATER, False, L.SUPPORTED))
        self.assertEqual(c["processability"], L.SUPPORTED)
        after = self.assert_same_as_direct(state, L.KIND_ATTACH_ENERGY, lambda s: [option_id(s[0], card_id=DCE), option_id(s[1], zone="active")],
                                           AttachEnergy(0, uid_of(state, 0, DCE), state.players[0].active.card))
        self.assertEqual(after.cards[after.players[0].active.energy[0]].card_id, DCE)

    def test_stop_before_acceptance_is_shown_not_removed(self):
        state = board({"active": H.CHARMANDER, "hand": [H.FIRE]})
        state.energy_attached_by_powers_this_turn = 1  # この番に特殊能力で手札からつけた（そのあとの通常の操作は記録で決まらない）
        session = host_of(state).session(0)
        r, c, inputs = inputs_of(session, L.KIND_ATTACH_ENERGY)
        self.assertNotIn(c["processability"], L.EXECUTABLE)
        self.assertEqual(c["reasons"], [L.REASON_STOPS])
        pair = inputs["stages"][1]["options_by_choice"]["o1"][0]
        self.assertFalse(pair["eligible"])
        before = snap(state)
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], ["o1", "o2"]).refusal.code, L.CANDIDATE_NOT_EXECUTABLE)
        _, direct = via_direct(state, AttachEnergy(0, state.players[0].hand[0], state.players[0].active.card))
        self.assertEqual(direct.outcome, D.REJECTED)  # 直接送れば、エンジンが受け付ける前に止める（U7 はホストの段で送らない）
        self.assertEqual(snap(state), before)

    def test_invalid_pairs(self):
        state = board({"active": H.CHARMANDER, "hand": [H.FIRE]})
        session = host_of(state).session(0)
        r, c, _ = inputs_of(session, L.KIND_ATTACH_ENERGY)
        for choices in (["o1"], ["o2", "o1"], ["o1", "o1"], ["o1", "o2", "o2"], ["o1", "o9"], ["o1", 2]):
            self.assertEqual(session.check(r["game"], r["revision"], c["id"], choices)["refusal"]["code"], L.CANDIDATE_INPUT_INVALID, choices)


class EvolveTest(Same, unittest.TestCase):
    def test_normal_and_name(self):
        state = board({"active": H.CHARMANDER, "bench": [H.GROWLITHE], "hand": [H.CHARMELEON, H.ARCANINE]})
        _, _c, inputs = inputs_of(host_of(state).session(0), L.KIND_EVOLVE)
        cards, targets = inputs["stages"]
        pairs = {o["card_id"]: [next(t["card_id"] for t in targets["options"] if t["id"] == p["option"]) for p in targets["options_by_choice"][o["id"]]]
                 for o in cards["options"]}
        self.assertEqual(pairs, {H.CHARMELEON: [H.CHARMANDER], H.ARCANINE: [H.GROWLITHE]})  # 名前の合う組だけ
        active = state.players[0].active.pokemon_id
        self.assert_same_as_direct(state, L.KIND_EVOLVE, lambda s: [option_id(s[0], card_id=H.CHARMELEON), option_id(s[1], pokemon=active)],
                                   EvolvePokemon(0, uid_of(state, 0, H.CHARMELEON), active))

    def test_turn_restrictions(self):
        for p0, turn in (({"active": {"card": H.CHARMANDER, "played_turn": 3}, "hand": [H.CHARMELEON]}, 3),  # その番に場に出した
                         ({"active": H.CHARMANDER, "hand": [H.CHARMELEON]}, 2),  # おたがいの最初の番
                         ({"active": {"card": H.CHARMELEON, "evolved_from": H.CHARMANDER, "evolved_turn": 3}, "hand": [CHARIZARD]}, 3)):  # その番に進化した
            r = host_of(board(p0, turn=turn)).session(0).candidates()
            self.assertIsNone(cand(r, L.KIND_EVOLVE), p0)

    def test_baby(self):
        state = board({"active": H.CHARMANDER, "bench": [BABY], "hand": [H.MAGMAR, H.CHARMELEON]})
        _, _c, inputs = inputs_of(host_of(state).session(0), L.KIND_EVOLVE)
        cards, targets = inputs["stages"]
        magmar = option_id(cards, card_id=H.MAGMAR)
        (pair,) = targets["options_by_choice"][magmar]
        self.assertEqual(next(t["card_id"] for t in targets["options"] if t["id"] == pair["option"]), BABY)  # たねポケモンのカードはベイビィにだけ
        baby = state.players[0].bench[0].pokemon_id
        self.assert_same_as_direct(state, L.KIND_EVOLVE, lambda s: [option_id(s[0], card_id=H.MAGMAR), option_id(s[1], pokemon=baby)],
                                   EvolvePokemon(0, uid_of(state, 0, H.MAGMAR), baby))

    def test_devolved_this_turn_stops(self):
        state, _pid = T50.EvolveAfterDevolutionTest("test_hand_evolution_same_turn_and_next_turn").devolved(hand=(T50.KADABRA,))
        session = host_of(state).session(0)
        r, c, inputs = inputs_of(session, L.KIND_EVOLVE)
        (pair,) = [p for p in inputs["stages"][1]["options_by_choice"][option_id(inputs["stages"][0], card_id=T50.KADABRA)]]
        self.assertFalse(pair["eligible"])
        self.assertNotIn(pair["processability"], L.EXECUTABLE)  # 未裁定（DV2）を消さずに示す
        refused = session.submit(r["game"], r["revision"], c["id"], [option_id(inputs["stages"][0], card_id=T50.KADABRA), pair["option"]])
        self.assertEqual(refused.refusal.code, L.CANDIDATE_NOT_EXECUTABLE)


class RetreatTest(Same, unittest.TestCase):
    def test_zero_cost(self):
        state = board({"active": H.GOLDEEN, "bench": [H.CHARMANDER]})
        _, _c, inputs = inputs_of(host_of(state).session(0), L.KIND_RETREAT)
        _bench, energy = inputs["stages"]
        self.assertEqual((energy["total_units"], energy["count"], energy["options"]), ({"min": 0, "max": 0}, {"min": 0, "max": 0}, []))
        self.assert_same_as_direct(state, L.KIND_RETREAT, lambda s: [s[0]["options"][0]["id"]], Retreat(0, (), state.players[0].bench[0].card))

    def test_cost_units_not_cards(self):
        state = board({"active": {"card": H.LAPRAS, "energy": [DCE, H.WATER]}, "bench": [H.CHARMANDER]})
        session = host_of(state).session(0)
        r, c, inputs = inputs_of(session, L.KIND_RETREAT)
        bench, energy = inputs["stages"]
        self.assertEqual(energy["total_units"], {"min": 2, "max": 2})
        self.assertEqual([(o["card_id"], o["units"], o["special"]) for o in energy["options"]], [(DCE, 2, True), (H.WATER, 1, False)])
        self.assertEqual(c["processability"], L.MAY_STOP_LATER)  # 特殊エネルギーがついている
        dce, water = (o["id"] for o in energy["options"])
        new = bench["options"][0]["id"]

        def check(choices):
            return session.check(r["game"], r["revision"], c["id"], choices)

        self.assertTrue(check([new, dce])["valid"])  # 1 枚で 2 個
        self.assertEqual(check([new, water])["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)  # 費用が足りない（1 個）
        self.assertEqual(check([new, dce, water])["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)  # 余計なカード（除いても足りる）
        self.assertEqual(check([new])["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)
        self.assertEqual(check([new, new])["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)
        self.assertEqual(check([dce, new])["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)  # 段の並び
        self.assertEqual(check([new, dce, dce])["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)
        self.assert_same_as_direct(state, L.KIND_RETREAT, lambda s: [s[0]["options"][0]["id"], option_id(s[1], card_id=DCE)],
                                   Retreat(0, (state.players[0].active.energy[0],), state.players[0].bench[0].card))

    def test_overpay_stops_instead_of_invalid(self):
        state = board({"active": {"card": H.CHARMANDER, "energy": [DCE]}, "bench": [H.GROWLITHE]})
        session = host_of(state).session(0)
        r, c, inputs = inputs_of(session, L.KIND_RETREAT)
        new, dce = inputs["stages"][0]["options"][0]["id"], inputs["stages"][1]["options"][0]["id"]
        self.assertEqual(session.check(r["game"], r["revision"], c["id"], [new, dce])["refusal"]["code"], L.CANDIDATE_NOT_EXECUTABLE)  # 費用不足ではなく決まらない
        self.assertEqual(session.check(r["game"], r["revision"], c["id"], [new])["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)  # 費用不足

    def test_special_conditions(self):
        for status in ("sleep", "paralysis"):
            value = True if status == "sleep" else 3
            state = board({"active": {"card": H.GOLDEEN, status: value}, "bench": [H.CHARMANDER]})
            self.assertIsNone(cand(host_of(state).session(0).candidates(), L.KIND_RETREAT), status)
        state = board({"active": {"card": H.GOLDEEN, "confusion": True}, "bench": [H.CHARMANDER]})
        _, _c, inputs = inputs_of(host_of(state).session(0), L.KIND_RETREAT)
        self.assertTrue(inputs["stages"][1]["confused"])  # 受理のあとにコイン（候補の作成では投げない）
        self.assert_same_as_direct(state, L.KIND_RETREAT, lambda s: [s[0]["options"][0]["id"]], Retreat(0, (), state.players[0].bench[0].card))

    def test_no_bench(self):
        self.assertIsNone(cand(host_of(board({"active": H.GOLDEEN})).session(0).candidates(), L.KIND_RETREAT))


class ReactionTest(unittest.TestCase):
    def test_board_with_effects_is_not_supported(self):
        quiet = board({"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "bench": [H.GROWLITHE], "hand": [H.FIRE, H.PONYTA, H.CHARMELEON]})
        loud = board({"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "bench": [H.GROWLITHE], "hand": [H.FIRE, H.PONYTA, H.CHARMELEON]},
                     {**OPPONENT, "bench": [ENTEI]})  # 相手の場に特殊能力を持つポケモン
        for state, expected in ((quiet, L.SUPPORTED), (loud, L.MAY_STOP_LATER)):
            r = host_of(state).session(0).candidates()
            for kind in L.TURN_KINDS:
                c = cand(r, kind)
                self.assertEqual(c["processability"], expected, kind)
                self.assertEqual(c["reasons"], [] if expected == L.SUPPORTED else [L.REASON_REACTIONS])


class SessionContractTest(unittest.TestCase):
    def state(self):
        return board({"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "bench": [H.GROWLITHE], "hand": [H.FIRE, H.PONYTA, H.CHARMELEON]})

    def test_queries_change_nothing(self):
        state = self.state()
        host = host_of(state)
        before = snap(host.game.state)
        session = host.session(0)
        for _ in range(2):
            r = session.candidates()
            for c in r["candidates"]:
                session.inputs(r["game"], r["revision"], c["id"])
                for choices in ([], ["o1"], ["o1", "o2"], ["o1", "o3"], ["o2", "o1"], ["o1", "o2", "o3"]):
                    session.check(r["game"], r["revision"], c["id"], choices)
        self.assertEqual(snap(host.game.state), before)

    def test_handles(self):
        host = host_of(self.state())
        session, other = host.session(0), host.session(1)
        r, c, _inputs = inputs_of(session, L.KIND_PLAY_BASIC)
        self.assertEqual(other.check(r["game"], r["revision"], c["id"], ["o1"])["refusal"]["code"], L.CANDIDATES_WRONG_ACTOR)
        self.assertEqual(session.check("other", r["revision"], c["id"], ["o1"])["refusal"]["code"], L.CANDIDATES_WRONG_GAME)
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], ["o9"]).refusal.code, L.CANDIDATE_INPUT_INVALID)
        self.assertTrue(session.check(r["game"], r["revision"], c["id"], ["o1"])["valid"])  # 拒否では失効しない
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], ["o1"]).outcome, D.ACCEPTED)
        self.assertEqual(session.check(r["game"], r["revision"], c["id"], ["o1"])["refusal"]["code"], L.CANDIDATES_STALE)  # 受理で失効

    def test_other_player_gets_nothing(self):
        r = host_of(self.state()).session(1).candidates()
        self.assertEqual((r["candidates"], r["situation"], r["empty_reason"]), ([], L.WAITING_FOR_PLAYER, L.EMPTY_NOT_ACTOR))

    def test_no_verifier_values(self):
        host = host_of(self.state())
        session = host.session(0)
        r = session.candidates()
        payload = [r] + [session.inputs(r["game"], r["revision"], c["id"]) for c in r["candidates"]]
        self.assertFalse(set(keys(payload)) & (FORBIDDEN_KEYS - {"operation_id"}))
        self.assertNotIn("seed", json.dumps(payload))


class TwinTest(unittest.TestCase):
    """本人の知識と公開の情報が同じで、相手の手札・おたがいの山札とサイドの配分だけが違う双子。候補・数・並び・制約・理由・不正な入力への答えが同じ。"""

    def twins(self):
        mine = {"active": {"card": H.LAPRAS, "energy": [DCE, H.WATER]}, "bench": [H.CHARMANDER, BABY], "hand": [H.FIRE, DCE, H.PONYTA, H.CHARMELEON, H.MAGMAR]}
        a = board({**mine, "deck": [H.FIRE, H.WATER, H.PONYTA], "prizes": [H.WATER, H.FIRE]},
                  {**OPPONENT, "hand": [H.WATER, H.CHARMELEON], "deck": [H.WATER, H.FIRE, H.SEEL], "prizes": [H.FIRE, H.WATER]})
        b = board({**mine, "deck": [H.PONYTA, H.FIRE, H.WATER], "prizes": [H.FIRE, H.WATER]},
                  {**OPPONENT, "hand": [H.SEEL, H.FIRE], "deck": [H.CHARMELEON, H.WATER, H.WATER], "prizes": [H.WATER, H.WATER]})
        for viewer in (0, None):  # 本人（プレイヤー 0）と観戦者に見えるもの。相手の手札は相手だけが知る（違ってよい）
            self.assertEqual(public_view(a, viewer), public_view(b, viewer))
        self.assertEqual(owned_card_ids(a, 0), owned_card_ids(b, 0))
        return a, b

    def responses(self, state):
        host = host_of(state)
        out = []
        for actor in (0, 1):
            session = host.session(actor)
            r = session.candidates()
            out.append(without_handles(r))
            for cid in [c["id"] for c in r["candidates"]] + ["c9"]:
                out.append(session.inputs(r["game"], r["revision"], cid))
                for choices in ([], ["o1"], ["o1", "o2"], ["o1", "o3"], ["o2", "o4"], ["o1", "o5"], ["o1", "o4", "o5"], ["o1", "o1"], ["o9"], [3]):
                    out.append(session.check(r["game"], r["revision"], cid, choices))
                out.append(dataclasses.asdict(session.submit("other", r["revision"], cid, ["o1"])))
        return out

    def test_twins_get_the_same_answers(self):
        a, b = self.twins()
        self.assertEqual(self.responses(a), self.responses(b))


class ClientApiTest(unittest.TestCase):
    def test_turn_actions_through_client_api(self):
        state = board({"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "bench": [H.GROWLITHE], "hand": [H.FIRE, H.PONYTA, H.CHARMELEON]})
        hub = ClientHub.from_state(state)
        me, spectator = hub.player(0), hub.spectator()
        r = me.handle({**CONTRACT, "type": "candidates"})["response"]
        self.assertEqual([c["kind"] for c in r["candidates"]], [L.KIND_END_TURN, *L.TURN_KINDS, L.KIND_USE_ATTACK])  # v0.166（U7-4）: ワザの候補が続く
        c = cand(r, L.KIND_ATTACH_ENERGY)
        fields = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        stages = me.handle({**CONTRACT, "type": "inputs", **fields})["response"]["stages"]
        choices = first_pair(stages)
        self.assertTrue(me.handle({**CONTRACT, "type": "check", **fields, "choices": choices})["response"]["valid"])
        bad = me.handle({**CONTRACT, "type": "submit", **fields, "choices": ["o9"]})
        self.assertEqual((bad["outcome"], bad["refusal"]["code"]), (L.REFUSED, L.CANDIDATE_INPUT_INVALID))
        self.assertEqual([hub.take_updates(a) for a in (0, 1, "spectator")], [[], [], []])  # 拒否は更新を作らない
        sent = me.handle({**CONTRACT, "type": "submit", **fields, "choices": choices})
        self.assertEqual((sent["outcome"], sent["refetch_required"]), (D.ACCEPTED, True))
        updates = {a: hub.take_updates(a) for a in (0, 1, "spectator")}
        self.assertEqual({a: [u["number"] for u in v] for a, v in updates.items()}, {0: [1], 1: [1], "spectator": [1]})
        game, _ = via_direct(state, AttachEnergy(0, state.players[0].hand[0], state.players[0].active.card))
        self.assertEqual(updates["spectator"][0]["observation"], observe(game.state, None))
        self.assertEqual(updates[1][0]["observation"], observe(game.state, 1))
        self.assertEqual(spectator.handle({**CONTRACT, "type": "candidates"})["error"]["code"], "CLIENT_REQUEST_UNKNOWN")
        self.assertEqual(hub.player(1).handle({**CONTRACT, "type": "candidates"})["response"]["candidates"], [])


def play_turn(session, done):
    """番の基本の操作を U7 の候補だけで 1 つずつ（進化 → エネルギー → ベンチ → にげる）送り、最後に番を終える。送った種類を done に加える。"""
    for kind in (L.KIND_EVOLVE, L.KIND_ATTACH_ENERGY, L.KIND_PLAY_BASIC, L.KIND_RETREAT):
        r, c, inputs = inputs_of(session, kind)
        if c is None or c["processability"] not in L.EXECUTABLE or (kind == L.KIND_RETREAT and kind in done):
            continue
        stages = inputs["stages"]
        if kind == L.KIND_PLAY_BASIC:
            choices = [next(o["id"] for o in stages[0]["options"] if o["eligible"])]
        elif kind == L.KIND_RETREAT:
            choices = retreat_choices(stages)
        else:
            choices = first_pair(stages)
        if choices is None or not session.check(r["game"], r["revision"], c["id"], choices)["valid"]:
            continue
        result = session.submit(r["game"], r["revision"], c["id"], choices)
        assert result.outcome == D.ACCEPTED, (kind, result)
        done.append(kind)
    r = session.candidates()
    if r["situation"] == L.ACTOR_TO_ACT and cand(r, L.KIND_END_TURN):
        session.submit(r["game"], r["revision"], cand(r, L.KIND_END_TURN)["id"])


CONNECT_DECK = [card for card in (H.CHARMANDER, H.CHARMELEON, H.GROWLITHE, H.ARCANINE, H.VULPIX, H.NINETALES, H.PONYTA, H.MAGMAR) for _ in range(4)] + [H.FIRE] * 28


def setup_with_u7(host):
    """準備（初期配置・補償）を U7 の候補だけで進め、ホストの入口でジャンケンの結果（プレイヤー 0 が先攻）を送る。"""
    for _ in range(40):
        moved = False
        for actor in (0, 1):
            session = host.session(actor)
            r = session.candidates()
            if not r["candidates"]:
                continue
            c = r["candidates"][0]
            stage = session.inputs(r["game"], r["revision"], c["id"])["stages"][0]
            if c["kind"] == L.KIND_PLACE_STARTING:
                choices = [o["id"] for o in stage["options"] if o["eligible"]][:2]
            else:
                choices = [stage["range"]["max"]]
            assert session.submit(r["game"], r["revision"], c["id"], choices).outcome == D.ACCEPTED
            moved = True
        if not moved:
            break
    hs = host.host_session()
    r = hs.candidates()
    assert hs.submit(r["game"], r["revision"], r["candidates"][0]["id"], [0]).outcome == D.ACCEPTED


class Recording(A.HostedGame):
    """送ったコマンドを記録する対戦（同じコマンドの列を直接送った対戦と比べるため。テストの補助）。"""

    def __init__(self, state):
        super().__init__(state)
        self.sent = []

    def submit(self, command, **kw):
        result = super().submit(command, **kw)
        if result.outcome == D.ACCEPTED:
            self.sent.append((command, kw.get("submitter")))
        return result


class ConnectionTest(unittest.TestCase):
    """new_game からの合法な操作の列（固定の seed・固定の少数の番）: U7 の候補だけで準備を終え、番の基本の操作 4 種類を送る。同じコマンドを直接送った対戦と同じ状態。"""

    def test_from_new_game_with_three_sets(self):
        for conventions in SETS:
            options = {} if conventions is None else {"conventions": conventions}
            start = A.start_game(CONNECT_DECK, CONNECT_DECK, 0, **options)
            self.assertEqual(start.outcome, D.ACCEPTED)
            recording = Recording(start.state.clone())
            host = L.ActionHost(recording)
            setup_with_u7(host)
            done = []
            for _ in range(6):
                state = host.game.state
                if state.phase is not state.phase.MAIN:
                    break
                play_turn(host.session(state.current_player), done)
            self.assertEqual(set(done), set(L.TURN_KINDS), conventions)
            direct = A.HostedGame(start.state.clone())
            for command, submitter in recording.sent:
                self.assertEqual(direct.submit(command, submitter=submitter).outcome, D.ACCEPTED, command)
            self.assertEqual(snap(direct.state), snap(host.game.state))
            self.assertTrue(any(isinstance(command, EndTurn) for command, _ in recording.sent))


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = (ROOT / "docs" / "legal-actions-u7-3.md").read_text(encoding="utf-8")
        for phrase in ("PlayBasicToBench", "AttachEnergy", "EvolvePokemon", "Retreat", "options_by_choice", "total_units", "units", "partial", "supported",
                       "may_stop_later", "unverified", "check_retreat", "kyuura-client-api"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
