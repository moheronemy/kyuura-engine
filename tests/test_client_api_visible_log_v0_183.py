"""v0.183（docs/client-api-visible-log-v0.183.md。設計は docs/client-api-visible-log-delivery-design.md の案 B）: client_api の読み取りの要求 ``log``。

``ClientHub`` が閲覧者（0・1・観戦者）ごとの可視ログの写しを受理の時点で固定して持ち、位置 ``(segment, log_index)`` から最大 256 件ずつ返す。

確かめの種類を分ける:

- クライアントの側: 入口の ``handle`` に JSON の要求を渡し、JSON の応答だけを読む（``log`` の取得に ``candidates``・``inputs``・``check`` を使わない）
- 信頼されたテストの側: 操作は hub の中の ``ActionHost`` のセッション（候補 → 入力 → 送信）で送り、状態（``hub._host.game.state``）を読んで、状態・乱数・ログの不変や、
  ``ViewRecorder`` との一致を確かめる
- 盤面は既存の構築盤面（ポケモン交換おじさん・パソコン通信・マチスの秘策・［KEEP］のエネルギー・リムーブ・サドン・デス）と、人工の出来事の列（ページの境界）。
  どれも new_game からの対戦の実績には数えない
"""

from __future__ import annotations

import copy
import json
import unittest
from unittest import mock

from kyuura_engine import adapter as A
from kyuura_engine import client_api as C
from kyuura_engine import diagnostics as D
from kyuura_engine import zones
from kyuura_engine.observation import visible_log
from kyuura_engine.view_record import ViewRecorder
from tests import helpers as H
from tests import test_computer_search_v0_22 as CS
from tests import test_keep_designated_energy_removal_v0_181 as K
from tests import test_pokemon_trader_v0_24 as PT
from tests import test_sudden_death_v0_134 as SD
from tests.test_client_api import REF, assert_clean, state_of
from tests.test_legal_actions_u7_1 import snap

TRADER, COMPUTER_SEARCH = "PMCG1-093", "PMCG1-090"
ENVELOPE = {"contract": C.CONTRACT, "format": C.FORMAT}


def log_request(endpoint, start=None, **extra):
    request = {**ENVELOPE, "type": "log", **({} if start is None else {"from": start}), **extra}
    return endpoint.handle(request)


def read_all(endpoint, start=None):
    """``complete`` まで ``next`` で続ける。(出来事の並び, 応答の並び)。"""
    pages = []
    while True:
        answer = log_request(endpoint, start)
        assert answer["ok"], answer
        pages.append(answer)
        if answer["complete"]:
            return [e for p in pages for e in p["entries"]], pages
        start = answer["next"]


def readers(hub):
    return {"0": hub.player(0), "1": hub.player(1), "spectator": hub.spectator(), "host": hub.host()}


def act(hub, actor, kind, stages):
    """``actor`` のセッションで、種類 ``kind`` の最初の候補に、段ごとに card が ``stages[i]`` にふくまれる選べるものを選んで送る（信頼されたテストの側）。"""
    session = hub._host.session(actor)
    c = session.candidates()
    cand = next(x for x in c["candidates"] if x["kind"] == kind)
    inputs = session.inputs(c["game"], c["revision"], cand["id"]) or {}
    choices = []
    for stage, wanted in zip(inputs.get("stages") or [], stages):
        choices += [o["id"] for o in stage["options"] if o.get("card") in set(wanted)]
    return session.submit(c["game"], c["revision"], cand["id"], tuple(choices))


def trader_hub(**kw):
    state = PT.board(**kw)
    hub = C.ClientHub.from_state(state)
    st = state_of(hub)
    return hub, PT.by_id(st, 0, "hand", TRADER)[0], PT.by_id(st, 0, "hand", H.DEWGONG)[0], PT.by_id(st, 0, "deck", H.IVYSAUR)[0]


def trader_events(entries):
    return [(e["event"]["kind"], e["event"]["card"], e["event"].get("card_id")) for e in entries if e["event"]["kind"] in ("return_to_deck", "reveal_from_deck")]


def with_public_events(count, state=None):
    """人工の出来事の列: 構築盤面のログに、公開の出来事（``shuffle``）を ``count`` 個足した状態（hub を作る前。baseline の投影になる）。"""
    state = state or PT.board()
    for _ in range(count - len(state.log)):
        state.add_event("shuffle", player=0)
    assert len(state.log) == count
    return state


class TraderIdentificationTest(unittest.TestCase):
    def test_each_viewer_reads_both_shown_cards_when_they_are_shown(self):
        hub, trader, give, take = trader_hub()
        ends = []
        self.assertEqual(act(hub, 0, "play_trainer", [[trader]]).outcome, D.ACCEPTED)
        for name, endpoint in readers(hub).items():
            entries, _ = read_all(endpoint)
            self.assertEqual(trader_events(entries), [], name)  # 使った直後（もどすカードを選ぶ前）には出さない
        ends.append(log_request(hub.spectator())["end"])
        self.assertEqual(act(hub, 0, "answer_decision", [[give]]).outcome, D.ACCEPTED)
        for name, endpoint in readers(hub).items():
            entries, _ = read_all(endpoint)
            self.assertEqual(trader_events(entries), [("return_to_deck", give, H.DEWGONG)], name)  # 山札から選ぶ前には、探すカードを出さない
        self.assertEqual(act(hub, 0, "answer_decision", [[take]]).outcome, D.ACCEPTED)
        for name, endpoint in readers(hub).items():
            entries, _ = read_all(endpoint)
            self.assertEqual(trader_events(entries), [("return_to_deck", give, H.DEWGONG), ("reveal_from_deck", take, H.IVYSAUR)], name)
            positions = [(e["segment"], e["log_index"]) for e in entries]
            self.assertEqual(positions, [(0, i) for i in range(len(state_of(hub).log))], name)
            assert_clean(self, entries)
        self.assertEqual(read_all(hub.host())[0], read_all(hub.spectator())[0])  # ホストの入口は観戦者の写し

    def test_only_the_new_events_after_a_position(self):
        hub, trader, give, take = trader_hub()
        before = log_request(hub.player(1))["next"]
        act(hub, 0, "play_trainer", [[trader]])
        act(hub, 0, "answer_decision", [[give]])
        act(hub, 0, "answer_decision", [[take]])
        tail, _ = read_all(hub.player(1), before)
        self.assertEqual([e["log_index"] for e in tail], list(range(before["index"], len(state_of(hub).log))))
        self.assertEqual([e["event"]["kind"] for e in tail], ["play_trainer", "return_to_deck", "reveal_from_deck", "shuffle", "discard_trainer"])

    def test_computer_search_result_stays_hidden(self):
        state = CS.board()
        hub = C.ClientHub.from_state(state)
        st = state_of(hub)
        cs, pick = CS.by_id(st, 0, "hand", COMPUTER_SEARCH)[0], CS.by_id(st, 0, "deck", H.BILL)[0]
        discards = [CS.by_id(st, 0, "hand", H.FIRE)[0], CS.by_id(st, 0, "hand", H.PONYTA)[0]]
        act(hub, 0, "play_trainer", [[cs]])
        act(hub, 0, "answer_decision", [discards])
        act(hub, 0, "answer_decision", [[pick]])
        for name in ("1", "spectator", "host"):
            entries, _ = read_all(readers(hub)[name])
            search = [e["event"] for e in entries if e["event"]["kind"] == "search_deck"]
            self.assertEqual(search, [{"kind": "search_deck", "turn": CS.TURN, "player": 0, "hidden": {"card": None}}], name)
            self.assertNotIn(f'"card": {pick}', json.dumps(entries), name)
        own = [e["event"] for e in read_all(hub.player(0))[0] if e["event"]["kind"] == "search_deck"]
        self.assertEqual(own[0]["card"], pick)

    def test_old_event_without_card_id_is_returned_as_is(self):
        """card_id のない旧形式の出来事（引数なしの生成の関数。hub を作る前）はそのまま返し、後の状態から補わない。"""
        state = PT.board()
        card = PT.by_id(state, 0, "hand", H.DEWGONG)[0]
        zones.return_hand_to_deck(state, 0, card)
        hub = C.ClientHub.from_state(state)
        for endpoint in readers(hub).values():
            (event,) = [e["event"] for e in read_all(endpoint)[0] if e["event"]["kind"] == "return_to_deck"]
            self.assertEqual(event, {"kind": "return_to_deck", "turn": PT.TURN, "player": 0, "card": card})


class RejectionTest(unittest.TestCase):
    def test_rejection_is_only_in_the_senders_response(self):
        state, _fd, (energy,) = K.opponent_face_down(K.UNOWN_K)
        hub = C.ClientHub.from_state(K.play(state, K.ENERGY_REMOVAL))
        before = {name: log_request(e) for name, e in readers(hub).items()}
        result = act(hub, 0, "answer_decision", [[energy]])
        self.assertEqual(result.outcome, D.REJECTED)
        for name, endpoint in readers(hub).items():
            self.assertEqual(log_request(endpoint), before[name], name)  # 拒否ではログが増えない（どの閲覧者の写しも同じ）
            self.assertNotIn(result.view.diagnostic_id, json.dumps(read_all(endpoint)[0], ensure_ascii=False), name)
        self.assertIsNotNone(result.view.diagnostic_id)  # 本人の診断は送信の結果だけにある
        self.assertEqual([hub.take_updates(a) for a in (0, 1, "spectator", "host")], [[], [], [], []])


class FixedPastTest(unittest.TestCase):
    """マチスの秘策（v0.67）: うらのポケモンにつけたエネルギーの target は、相手の写しで伏せる。あとでおもてにすると、今の visible_log は過去の出来事の uid も見せるが、
    hub の写しは受理の時点の値のまま（後の公開・状態の変化で変わらない）。"""

    def run_secret_plan(self):
        from tests.test_secret_plan_v0_67 import DIGLETT, LT_SURGES_SECRET_PLAN, board, uid_of

        state = board(hand=(DIGLETT, H.FIGHTING))
        hub = C.ClientHub.from_state(state)
        attached = {v: ViewRecorder.attach(v, state_of(hub)) for v in C.LOG_VIEWERS}  # 同じ時点に始めた閲覧用記録（比べる用）
        hub._verifier = lambda actor, result: [r.add(result) for r in attached.values()]
        st = state_of(hub)
        diglett, fighting = uid_of(st, DIGLETT), uid_of(st, H.FIGHTING)
        self.assertEqual(act(hub, 0, "play_trainer", [[uid_of(st, LT_SURGES_SECRET_PLAN)]]).outcome, D.ACCEPTED)
        self.assertEqual(act(hub, 0, "answer_decision", [[diglett]]).outcome, D.ACCEPTED)
        self.assertEqual(act(hub, 0, "attach_energy", [[fighting], [diglett]]).outcome, D.ACCEPTED)
        st = state_of(hub)
        index = next(i for i, e in enumerate(st.log) if e["kind"] == "attach_energy" and e["target"] == diglett)
        seen = {name: copy.deepcopy(read_all(e)[0]) for name, e in readers(hub).items()}
        self.assertEqual(act(hub, 0, "reveal_face_down", [[diglett]]).outcome, D.ACCEPTED)
        return hub, attached, diglett, index, seen

    def test_entries_do_not_change_after_the_card_is_revealed(self):
        hub, attached, hidden, index, seen = self.run_secret_plan()
        st = state_of(hub)
        self.assertIn(hidden, [v for v in visible_log(st, 1)[index].values() if type(v) is int])  # 今の投影は過去の uid を見せる
        for name in ("1", "spectator", "host"):
            entries, _ = read_all(readers(hub)[name])
            self.assertEqual(entries[:len(seen[name])], seen[name], name)  # 前に読んだ位置の値は同じ
            self.assertIsNone(entries[index]["event"]["target"], name)  # 受理の時点は伏せたまま
        self.assertEqual(read_all(hub.player(0))[0][index]["event"]["target"], hidden)  # 持ち主は受理の時点から見える

    def test_entries_equal_view_records_started_at_the_same_time(self):
        hub, attached, _hidden, _index, _seen = self.run_secret_plan()
        for viewer, name in ((0, "0"), (1, "1"), (None, "spectator")):
            record = [x for e in attached[viewer].record().data["entries"] for x in e.get("events") or []]
            self.assertEqual(read_all(readers(hub)[name])[0], record, name)

    def test_baseline_is_the_projection_when_the_hub_is_made(self):
        hub, _attached, hidden, index, _seen = self.run_secret_plan()
        st = state_of(hub)
        late = C.ClientHub.from_state(st)  # 同じ状態から作った別の hub: 作る前のログは、作った時点の投影
        answer = log_request(late.player(1))
        self.assertEqual(answer["baseline_end"], {"segment": 0, "index": len(st.log)})
        self.assertEqual(answer["entries"][index]["event"], visible_log(st, 1)[index])
        self.assertEqual(answer["entries"][index]["event"]["target"], hidden)  # 元の受理の時点（伏せていた）とは違う。baseline より前は元の時点の公開を保証しない
        self.assertIsNone(read_all(hub.player(1))[0][index]["event"]["target"])
        self.assertLess(log_request(hub.player(1))["baseline_end"]["index"], index + 1)  # 先の hub では、この位置は baseline のあと（受理の時点の写し）


class CursorTest(unittest.TestCase):
    def test_pages_of_256(self):
        for count, sizes in ((256, [256]), (257, [256, 1]), (600, [256, 256, 88])):
            with self.subTest(count=count):
                hub = C.ClientHub.from_state(with_public_events(count))
                entries, pages = read_all(hub.spectator())
                self.assertEqual([len(p["entries"]) for p in pages], sizes)
                self.assertEqual([p["complete"] for p in pages], [False] * (len(sizes) - 1) + [True])
                self.assertEqual([e["log_index"] for e in entries], list(range(count)))
                self.assertEqual(pages[0]["next"], {"segment": 0, "index": min(256, count)})
                for p in pages:
                    self.assertEqual((p["end"], p["baseline_end"]), ({"segment": 0, "index": count}, {"segment": 0, "index": count}))

    def test_first_read_starts_at_zero_and_repeated_reads_return_the_same_entries(self):
        hub = C.ClientHub.from_state(with_public_events(300))
        first = log_request(hub.player(0))
        self.assertEqual(first, log_request(hub.player(0), {"segment": 0, "index": 0}))
        self.assertEqual(first["entries"][0]["log_index"], 0)
        again = [log_request(hub.player(0), {"segment": 0, "index": 10}) for _ in range(3)]
        self.assertEqual(again[0], again[1])
        self.assertEqual(again[0]["entries"][0], first["entries"][10])

    def test_appended_while_reading(self):
        hub = C.ClientHub.from_state(with_public_events(300, PT.board()))
        first = log_request(hub.player(1))
        self.assertFalse(first["complete"])
        self.assertEqual(act(hub, 0, "play_trainer", [[PT.by_id(state_of(hub), 0, "hand", TRADER)[0]]]).outcome, D.ACCEPTED)
        later = log_request(hub.player(1), first["next"])
        self.assertEqual(later["end"], {"segment": 0, "index": len(state_of(hub).log)})
        self.assertGreater(later["end"]["index"], first["end"]["index"])  # end は応答の時点の末尾
        self.assertEqual([e["log_index"] for e in later["entries"]], list(range(256, len(state_of(hub).log))))
        self.assertTrue(later["complete"])
        re_read = log_request(hub.player(1))
        self.assertEqual(re_read["entries"], first["entries"])  # 同じ位置の既存の出来事は同じ。end・complete は応答の時点で変わる
        self.assertNotEqual(re_read["end"], first["end"])

    def test_end_and_empty_log(self):
        state = PT.board()
        hub = C.ClientHub.from_state(state)
        n = len(state_of(hub).log)
        at_end = log_request(hub.spectator(), {"segment": 0, "index": n})
        self.assertEqual((at_end["entries"], at_end["next"], at_end["end"], at_end["complete"]),
                         ([], {"segment": 0, "index": n}, {"segment": 0, "index": n}, True))
        empty = H.build_test_state([{"active": SD.PIKA, "deck": [H.FIRE] * 5}, {"active": SD.PIKA, "deck": [H.FIRE] * 5}])
        if empty.log:
            self.skipTest("構築盤面のログが空でない")
        answer = log_request(C.ClientHub.from_state(empty).player(0))
        self.assertEqual((answer["entries"], answer["next"], answer["end"], answer["complete"], answer["baseline_end"]),
                         ([], {"segment": 0, "index": 0}, {"segment": 0, "index": 0}, True, {"segment": 0, "index": 0}))

    def test_invalid_and_unknown_positions(self):
        hub = C.ClientHub.from_state(with_public_events(20))
        state = state_of(hub)
        before = (snap(state), [hub.take_updates(a) for a in (0, 1, "spectator", "host")])
        invalid = [[0, 0], "0:0", 0, {"segment": 0}, {"index": 0}, {"segment": 0, "index": 0, "x": 1}, {"segment": -1, "index": 0},
                   {"segment": 0, "index": -1}, {"segment": True, "index": 0}, {"segment": 0, "index": False}, {"segment": 0, "index": 1.0},
                   {"segment": 0, "index": 2**31}, {"segment": "0", "index": 0}, None]
        for endpoint in readers(hub).values():
            for value in invalid:
                answer = endpoint.handle({**ENVELOPE, "type": "log", "from": value})
                self.assertEqual((answer["ok"], answer["error"]["code"]), (False, C.FIELD_INVALID), value)
            for value in ({"segment": 1, "index": 0}, {"segment": 0, "index": 21}, {"segment": 7, "index": 3}):
                answer = log_request(endpoint, value)
                self.assertEqual((answer["ok"], answer["error"]["code"], answer["type"]), (False, C.LOG_POSITION_UNKNOWN, "log"), value)
            self.assertEqual(endpoint.handle({**ENVELOPE, "type": "log", "after": 0})["error"]["code"], C.FIELD_UNKNOWN)
        self.assertEqual((snap(state), [hub.take_updates(a) for a in (0, 1, "spectator", "host")]), before)

    def test_segment_change(self):
        state = H.build_test_state([{"active": SD.PIKA, "deck": [SD.PIKA] + [H.FIRE] * 30, "prizes": 0},
                                    {"active": SD.PIKA, "deck": [SD.PIKA] + [H.FIRE] * 30, "prizes": 0}], current_player=0)
        hub = C.ClientHub.from_state(SD.constructed_sudden_death(SD.with_decklists(state)))
        first = state_of(hub).segment_index
        old_len = len(state_of(hub).log)
        mid = log_request(hub.spectator(), {"segment": first, "index": old_len})
        trace = []
        self.assertTrue(REF.act(hub.host(), trace))  # 延長戦を始める（ホストの操作）
        st = state_of(hub)
        self.assertEqual(st.segment_index, first + 1)
        for name, endpoint in readers(hub).items():
            entries, _ = read_all(endpoint)
            positions = [(e["segment"], e["log_index"]) for e in entries]
            finished = [s for s in (st.segments or ()) if s.index == first]
            self.assertEqual(positions[:len(finished[0].log)], [(first, i) for i in range(len(finished[0].log))], name)
            self.assertEqual(positions[len(finished[0].log):], [(first + 1, i) for i in range(len(st.log))], name)
            boundary = log_request(endpoint, {"segment": first, "index": len(finished[0].log)})  # 区間の終わりは次の区間の始まりと同じ位置
            self.assertEqual(boundary, log_request(endpoint, {"segment": first + 1, "index": 0}), name)
            self.assertEqual(boundary["end"]["segment"], REF.request(endpoint, "view")["status"]["segment"], name)
        self.assertEqual(mid["complete"], True)

    def test_separation_between_games_and_viewers(self):
        hub_a = C.ClientHub.from_state(with_public_events(30))
        hub_b = C.ClientHub.from_state(with_public_events(10))
        far = log_request(hub_a.player(0))["next"]
        self.assertEqual(log_request(hub_b.player(0), far)["error"]["code"], C.LOG_POSITION_UNKNOWN)  # 別の対戦の位置は、範囲にあるとは限らない
        state = PT.board()
        hub = C.ClientHub.from_state(state)
        act(hub, 0, "end_turn", [])  # 番を終えると相手が引く（引いたカードは本人の写しだけ）
        logs = {name: read_all(e)[0] for name, e in readers(hub).items()}
        self.assertEqual({name: [(e["segment"], e["log_index"]) for e in v] for name, v in logs.items()}, {name: [(e["segment"], e["log_index"]) for e in logs["0"]] for name in logs})
        draws = {name: [e["event"] for e in v if e["event"]["kind"] == "draw"] for name, v in logs.items()}
        self.assertIn("cards", draws["1"][-1])
        self.assertNotIn("cards", draws["0"][-1])
        self.assertNotIn("cards", draws["spectator"][-1])

    def test_returned_values_can_be_changed_without_changing_the_kept_log(self):
        hub, trader, give, _take = trader_hub()
        act(hub, 0, "play_trainer", [[trader]])
        act(hub, 0, "answer_decision", [[give]])
        answer = log_request(hub.player(1))
        kept = copy.deepcopy(answer)
        for e in answer["entries"]:
            e["event"]["kind"] = "changed"
            e["event"].pop("card_id", None)
        answer["entries"].clear()
        answer["next"]["index"] = 0
        self.assertEqual(log_request(hub.player(1)), kept)


class FailedTest(unittest.TestCase):
    def test_kept_log_is_readable_after_a_failed_result(self):
        hub, trader, _give, _take = trader_hub()
        act(hub, 0, "play_trainer", [[trader]])
        before = {name: read_all(e)[0] for name, e in readers(hub).items()}
        p0 = hub.player(0)
        r = REF.request(p0, "candidates")["response"]
        with mock.patch.object(A, "apply_command", side_effect=RuntimeError("テストの内部エラーの文")):
            answer = REF.request(p0, "submit", game=r["game"], revision=r["revision"], candidate=r["candidates"][0]["id"], choices=["o1"])
        self.assertEqual(answer["outcome"], D.FAILED)
        for name, endpoint in readers(hub).items():
            self.assertEqual(REF.request(endpoint, "view")["error"]["code"], C.GAME_UNAVAILABLE)
            entries, pages = read_all(endpoint)
            self.assertEqual(entries, before[name], name)
            self.assertNotIn("テストの内部エラーの文", json.dumps(pages, ensure_ascii=False))


class NonInterferenceTest(unittest.TestCase):
    def drive(self, noisy):
        hub, trader, give, take = trader_hub()
        responses = []

        def read_everything():
            if noisy:
                for endpoint in readers(hub).values():
                    read_all(endpoint)
                    log_request(endpoint, {"segment": 0, "index": 0})

        p0 = hub.player(0)
        for kind, uids in (("play_trainer", [trader]), ("answer_decision", [give]), ("answer_decision", [take])):
            read_everything()
            c = REF.request(p0, "candidates")["response"]
            cand = next(x for x in c["candidates"] if x["kind"] == kind)
            inputs = REF.request(p0, "inputs", game=c["game"], revision=c["revision"], candidate=cand["id"])
            choices = [o["id"] for o in inputs["response"]["stages"][0]["options"] if o.get("card") in uids]
            check = REF.request(p0, "check", game=c["game"], revision=c["revision"], candidate=cand["id"], choices=choices)
            read_everything()
            submit = REF.request(p0, "submit", game=c["game"], revision=c["revision"], candidate=cand["id"], choices=choices)
            read_everything()
            responses.append({"candidates": c, "inputs": inputs, "check": check, "submit": submit,
                              "views": {name: REF.request(e, "view") for name, e in readers(hub).items()}})
        updates = {a: hub.take_updates(a) for a in (0, 1, "spectator", "host")}
        return snap(state_of(hub)), responses, updates

    def test_log_requests_do_not_change_anything_else(self):
        quiet, noisy = self.drive(False), self.drive(True)
        self.assertEqual(quiet[0], noisy[0])  # 状態・乱数・ログ・決定の通し番号

        def without_handles(value):
            if isinstance(value, dict):
                return {k: ("<handle>" if k in ("game", "revision") and isinstance(v, str) else without_handles(v)) for k, v in value.items()}
            if isinstance(value, list):
                return [without_handles(v) for v in value]
            return value

        self.assertEqual(without_handles(quiet[1]), without_handles(noisy[1]))  # 候補・入力・check・submit・view の応答（取っ手は secrets の乱数）
        self.assertEqual(quiet[2], noisy[2])  # 更新の箱を log が取り出さない
        self.assertEqual([len(v) for v in noisy[2].values()], [3, 3, 3, 3])

    def test_existing_responses_keep_their_shape(self):
        hub, _trader, _give, _take = trader_hub()
        self.assertEqual(set(REF.request(hub.player(0), "view")), {"contract", "format", "type", "ok", "viewer", "status", "observation"})
        self.assertEqual(set(REF.request(hub.spectator(), "updates")), {"contract", "format", "type", "ok", "updates"})
        self.assertEqual(REF.request(hub.spectator(), "candidates")["error"]["code"], C.REQUEST_UNKNOWN)
        self.assertEqual(C.FORMAT, 1)
        self.assertEqual(set(log_request(hub.spectator())), {"contract", "format", "type", "ok", "entries", "next", "end", "complete", "baseline_end"})


if __name__ == "__main__":
    unittest.main()
