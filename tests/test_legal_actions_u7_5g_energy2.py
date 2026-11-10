"""U7-5g（docs/legal-actions-u7-5fg.md 3 章）: カツラの 2 枚目（AttachEnergy.energy2）の、attach_energy の任意の 3 段目（options_by_path）の回帰テスト。

確かめの種類を分ける:

- 合法な操作の列（tests.test_instant_trainers_v0_55 の盤面から apply_command でカツラを使う）: 1 枚・2 枚・任意の省略、組ごとの 3 段目、不正な経路の混在、同じカード、
  違う付け先、許可なし、回数（BL1・2 枚のあと）、特殊エネルギー（レインボー・無色 2 個）、直接のコマンドとの一致、取っ手、client_api
- new_game からの合法な操作の列（固定の seed。3 つの規約集合）: 準備を U7 で終え、カツラを使い、2 枚を U7 でつける。直接の列と同じ状態
- 補助関数の確かめ: 段の形の確かめ（stage_dependency_problems）が、壊した options_by_path・path_stages を見つける

停止コードの文字列はテストの中に書かない。
"""

from __future__ import annotations

import copy
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from kyuura_engine.commands import AttachEnergy
from kyuura_engine.engine import apply_command
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from tests import helpers as H
from tests.test_instant_trainers_v0_55 import board, use
from tests.test_legal_actions_u7_1 import snap, without_handles
from tests.test_legal_actions_u7_3 import (
    SETS,
    Recording,
    cand,
    host_of,
    inputs_of,
    setup_with_u7,
    via_direct,
)

CONTRACT = {"contract": "kyuura-client-api", "format": 1}


def blaine(hand=(H.FIRE, H.FIRE, H.FIRE, H.WATER), *, used=True, bench=(H.GROWLITHE,)):
    """バトル場にカツラのガーディ、ベンチにガーディ（「カツラのポケモン」でない）。手札にカツラと ``hand``。``used`` ならカツラを使った（この番だけ 2 枚にする）。"""
    state = board((H.BLAINE_TRAINER, *hand), active={"card": H.BLAINES_GROWLITHE, "energy": []}, bench=bench)
    return use(state, H.BLAINE_TRAINER) if used else state


def hand_uids(state, card_id):
    return [u for u in state.players[0].hand if state.cards[u].card_id == card_id]


def attach(state):
    host = host_of(state)
    session = host.session(0)
    r, c, inputs = inputs_of(session, L.KIND_ATTACH_ENERGY)
    return host, session, r, c, inputs["stages"]


def ids(stages, energy, target, energy2=None):
    """カードの uid・場のポケモンの uid から選ぶものの番号（3 段目は 1・2 段目の組の options_by_path から）。"""
    first = next(o["id"] for o in stages[0]["options"] if o["card"] == energy)
    second = next(p["option"] for p in stages[1]["options_by_choice"][first] if next(o for o in stages[1]["options"] if o["id"] == p["option"])["card"] == target)
    if energy2 is None:
        return [first, second]
    third = next(p["option"] for p in stages[2]["options_by_path"][f"{first}/{second}"] if next(o for o in stages[2]["options"] if o["id"] == p["option"])["card"] == energy2)
    return [first, second, third]


class ShapeTest(unittest.TestCase):
    def test_without_blaine_the_candidate_keeps_the_two_stage_shape(self):
        _h, _s, _r, c, stages = attach(blaine(used=False))
        self.assertEqual([s["stage"] for s in stages], [1, 2])
        self.assertEqual(c["choices_format"], "[エネルギーカードの番号, つける場のポケモンの番号]")

    def test_third_stage_by_path(self):
        state = blaine()
        fire, water = hand_uids(state, H.FIRE), hand_uids(state, H.WATER)[0]
        active, bench = state.players[0].active.card, state.players[0].bench[0].card
        _h, _s, _r, c, stages = attach(state)
        self.assertEqual([s["stage"] for s in stages], [1, 2, 3])
        third = stages[2]
        self.assertEqual((third["role"], third["meaning"], third["count"], third["decline"], third["path_stages"]),
                         ("energy2", "card", {"min": 0, "max": 1}, True, [1, 2]))
        self.assertNotIn("options_by_choice", third)
        self.assertNotIn("depends_on_stage", third)
        self.assertEqual(L.stage_dependency_problems(stages), [])
        by_card = {o["id"]: o["card"] for o in stages[0]["options"]}
        target_of = {o["id"]: o["card"] for o in stages[1]["options"]}
        third_card = {o["id"]: o["card"] for o in third["options"]}
        paths = {(by_card[k.split("/")[0]], target_of[k.split("/")[1]]): sorted(third_card[ref["option"]] for ref in refs) for k, refs in third["options_by_path"].items()}
        # 「炎」エネルギーカード → カツラのポケモン の組だけに、ほかの「炎」エネルギーカードが続く（水・ベンチのガーディ・同じカードは続かない）
        self.assertEqual(paths, {(f, active): sorted(x for x in fire if x != f) for f in fire})
        self.assertNotIn(water, third_card.values())
        self.assertFalse(any(k[1] == bench for k in paths))
        self.assertEqual(c["choices_format"], "[エネルギーカードの番号, つける場のポケモンの番号(, 2 枚目のエネルギーカードの番号)]（2 枚目は任意）")

    def test_special_energy(self):
        state = blaine(hand=(H.FIRE, H.RAINBOW_ENERGY, H.DOUBLE_COLORLESS_ENERGY))
        fire, rainbow = hand_uids(state, H.FIRE)[0], hand_uids(state, H.RAINBOW_ENERGY)[0]
        _h, session, r, c, stages = attach(state)
        choices = ids(stages, fire, state.players[0].active.card, rainbow)  # レインボー: 「炎」エネルギーカードとして選べるかが決まらない（RB2）
        ref = next(p for p in stages[2]["options_by_path"]["/".join(choices[:2])] if p["option"] == choices[2])
        self.assertEqual((ref["eligible"], ref["processability"], ref["reasons"]), (False, L.RULING_UNRESOLVED, [L.REASON_STOPS]))
        self.assertEqual(session.check(r["game"], r["revision"], c["id"], choices)["refusal"]["code"], L.CANDIDATE_NOT_EXECUTABLE)
        with self.assertRaises(UnsupportedError):
            apply_command(state, AttachEnergy(0, fire, state.players[0].active.card, energy2=rainbow))
        dce = hand_uids(state, H.DOUBLE_COLORLESS_ENERGY)[0]
        self.assertNotIn(dce, [o["card"] for o in stages[2]["options"]])  # 無色 2 個: 「炎」エネルギーカードでない（ゲーム上できない）
        with self.assertRaises(IllegalActionError):
            apply_command(state, AttachEnergy(0, fire, state.players[0].active.card, energy2=dce))


class SubmitTest(unittest.TestCase):
    def assert_same(self, state, choices_of, command):
        host, session, r, c, stages = attach(state.clone())
        result = session.submit(r["game"], r["revision"], c["id"], choices_of(stages))
        game, direct = via_direct(state, command)
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual(snap(host.game.state), snap(game.state))
        return host

    def test_one_and_two_cards_match_direct(self):
        state = blaine()
        fire = hand_uids(state, H.FIRE)
        active = state.players[0].active.card
        one = self.assert_same(state, lambda st: ids(st, fire[0], active), AttachEnergy(0, fire[0], active))  # 3 段目を省く: 1 枚（今までの形）
        self.assertEqual(one.game.state.energy_attachments_this_turn, 1)
        two = self.assert_same(state, lambda st: ids(st, fire[0], active, fire[1]), AttachEnergy(0, fire[0], active, energy2=fire[1]))
        self.assertEqual((two.game.state.players[0].active.energy, two.game.state.energy_attachments_this_turn), ([fire[0], fire[1]], 2))
        self.assertEqual(two.game.state.log[-1]["energy2"], fire[1])
        self.assertIsNone(cand(two.session(0).candidates(), L.KIND_ATTACH_ENERGY))  # 2 枚のあと: この番はもうつけられない（ゲーム上できない）

    def test_non_blaine_target_is_one_card_only(self):
        state = blaine()
        fire = hand_uids(state, H.FIRE)
        bench = state.players[0].bench[0].card
        self.assert_same(state, lambda st: ids(st, fire[0], bench), AttachEnergy(0, fire[0], bench))
        with self.assertRaises(IllegalActionError):
            apply_command(state, AttachEnergy(0, fire[0], bench, energy2=fire[1]))

    def test_second_operation_is_bl1(self):
        state = blaine()
        fire = hand_uids(state, H.FIRE)
        active = state.players[0].active.card
        once = apply_command(state, AttachEnergy(0, fire[0], active))
        _h, session, r, c, stages = attach(once)
        self.assertEqual(c["processability"], L.RULING_UNRESOLVED)  # 2 回目の操作は BL1（未裁定）。1 枚・2 枚とも送れない
        for choices in (ids(stages, fire[1], active), ids(stages, fire[1], active, fire[2])):
            self.assertEqual(session.check(r["game"], r["revision"], c["id"], choices)["refusal"]["code"], L.CANDIDATE_NOT_EXECUTABLE)

    def test_mixed_and_broken_inputs_are_rejected(self):
        state = blaine()
        before = snap(state)
        fire = hand_uids(state, H.FIRE)
        active, bench = state.players[0].active.card, state.players[0].bench[0].card
        host, session, r, c, stages = attach(state)
        good = ids(stages, fire[0], active, fire[1])
        other = ids(stages, fire[1], active, fire[2])
        third_of = {o["card"]: o["id"] for o in stages[2]["options"]}
        bad = [
            [good[0], ids(stages, fire[0], bench)[1], good[2]],  # ベンチのガーディ（options_by_path に鍵がない）
            [good[0], good[1], third_of[fire[0]]],  # 同じカードの 2 回の指定（その組の options_by_path にない）
            [other[0], other[1], third_of[fire[1]]],  # 別の組の 3 段目（1 段目を変えた古い 3 段目）
            [good[0], good[2], good[1]], [good[2], good[1]], [*good, good[2]], [good[0]], [],
            [good[0], good[1], "o99"], [good[0], good[1], 1],
        ]
        for choices in bad:
            with self.subTest(choices=choices):
                self.assertEqual(session.check(r["game"], r["revision"], c["id"], choices)["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)
                self.assertEqual(session.submit(r["game"], r["revision"], c["id"], choices).refusal.code, L.CANDIDATE_INPUT_INVALID)
        self.assertEqual(snap(host.game.state), before)
        self.assertTrue(session.check(r["game"], r["revision"], c["id"], good)["valid"])  # 拒否のあとも取っ手は有効
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], good).outcome, D.ACCEPTED)
        self.assertEqual(session.check(r["game"], r["revision"], c["id"], good)["refusal"]["code"], L.CANDIDATES_STALE)  # 受理で失効

    def test_queries_change_nothing(self):
        state = blaine()
        before = snap(state)
        _h, session, r, c, stages = attach(state)
        for choices in ([], stages[0]["options"][0]["id"]):
            session.check(r["game"], r["revision"], c["id"], choices)
        self.assertEqual(snap(state), before)

    def test_client_api(self):
        state = blaine()
        fire = hand_uids(state, H.FIRE)
        hub = ClientHub.from_state(state)
        me = hub.player(0)
        r = me.handle({**CONTRACT, "type": "candidates"})["response"]
        c = cand(r, L.KIND_ATTACH_ENERGY)
        handle = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        stages = me.handle({**CONTRACT, "type": "inputs", **handle})["response"]["stages"]
        sent = me.handle({**CONTRACT, "type": "submit", **handle, "choices": ids(stages, fire[0], state.players[0].active.card, fire[1])})
        self.assertEqual((sent["outcome"], sent["refetch_required"]), (D.ACCEPTED, True))
        self.assertEqual(len(hub.take_updates("spectator")), 1)


class StageCheckTest(unittest.TestCase):
    def test_broken_path_stages_are_found(self):
        _h, _s, _r, _c, stages = attach(blaine())
        key = next(iter(stages[2]["options_by_path"]))

        def broken(mutate):
            copied = copy.deepcopy(stages)
            mutate(copied)
            return L.stage_dependency_problems(copied)

        cases = {
            "unknown key": lambda s: s[2]["options_by_path"].__setitem__("o98/o99", [{"option": s[2]["options"][0]["id"]}]),
            "wrong arity": lambda s: s[2]["options_by_path"].__setitem__(key.split("/")[0], []),
            "missing ref": lambda s: s[2]["options_by_path"][key].append({"option": "o99"}),
            "duplicate ref": lambda s: s[2]["options_by_path"][key].append(dict(s[2]["options_by_path"][key][0])),
            "self reference": lambda s: s[2].__setitem__("path_stages", [1, 3]),
            "reversed": lambda s: s[2].__setitem__("path_stages", [2, 1]),
            "mixed with options_by_choice": lambda s: s[2].__setitem__("options_by_choice", {}),
            "mixed with depends_on_stage": lambda s: s[2].__setitem__("depends_on_stage", 2),
            "without path_stages": lambda s: s[2].pop("path_stages"),
            "pair not in stage 2": lambda s: s[1]["options_by_choice"].__setitem__(key.split("/")[0], []),
        }
        for name, mutate in cases.items():
            with self.subTest(name):
                self.assertTrue(broken(mutate), name)


BLAINE_DECK = [H.BLAINES_GROWLITHE] * 4 + [H.BLAINE_TRAINER] * 4 + [H.FIRE] * 52
BLAINE_SEED = 1  # 事前に固定した seed: 準備を U7 で終えた先攻（0）の場にカツラのガーディがいて、手札にカツラと炎エネルギー 2 枚以上がある


class ConnectionTest(unittest.TestCase):
    def test_two_cards_from_new_game(self):
        self.assertEqual(len(BLAINE_DECK), 60)
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                options = {} if conventions is None else {"conventions": conventions}
                start = A.start_game(BLAINE_DECK, BLAINE_DECK, BLAINE_SEED, **options)
                recording = Recording(start.state.clone())
                host = L.ActionHost(recording)
                setup_with_u7(host)
                session = host.session(0)
                r, c, inputs = inputs_of(session, L.KIND_PLAY_TRAINER)
                blaine_card = next(o["id"] for o in inputs["stages"][0]["options"] if o["card_id"] == H.BLAINE_TRAINER)
                self.assertEqual(session.submit(r["game"], r["revision"], c["id"], [blaine_card]).outcome, D.ACCEPTED)
                state = host.game.state
                fire = hand_uids(state, H.FIRE)
                target = next(q.card for q in state.players[0].in_play() if state.cards[q.card].card_id == H.BLAINES_GROWLITHE)
                r, c, inputs = inputs_of(session, L.KIND_ATTACH_ENERGY)
                self.assertEqual(session.submit(r["game"], r["revision"], c["id"], ids(inputs["stages"], fire[0], target, fire[1])).outcome, D.ACCEPTED)
                self.assertEqual(host.game.state.energy_attachments_this_turn, 2)
                direct = A.HostedGame(start.state.clone())
                for command, submitter in recording.sent:
                    self.assertEqual(direct.submit(command, submitter=submitter).outcome, D.ACCEPTED, command)
                self.assertEqual(snap(direct.state), snap(host.game.state))
                self.assertTrue(any(isinstance(cmd, AttachEnergy) and cmd.energy2 is not None for cmd, _ in recording.sent))
                self.assertEqual(without_handles(host.session(1).candidates())["situation"], L.WAITING_FOR_PLAYER)


if __name__ == "__main__":
    unittest.main()
