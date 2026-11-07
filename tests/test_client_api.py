"""v0.164（docs/client-api-v0.164.md）: クライアント向けの最小のアダプタと、ヘッドレスの参照クライアントによる接続の確かめ。

確かめの種類を分ける:

- クライアントの側: 参照クライアント（examples/headless_client.py）の関数で、JSON の要求・応答だけを使う
- 信頼されたテストの側: hub の中の状態（``hub._host.game.state``）を読んで、状態・乱数・ログの不変や、U7 への直接の送信との一致を確かめる（クライアントの側には渡さない）
- 構築盤面（決定待ち・延長戦の開始の待ち）と、new_game からの合法な操作の列と、補助の作り（アダプタの内部エラーの差し替え）を分ける

停止コードの文字列はテストの中に書かない。
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import unittest
from unittest import mock

from kyuura_engine import adapter as A
from kyuura_engine import client_api as C
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.commands import PlayTrainer
from kyuura_engine.view_record import FORBIDDEN_KEYS
from tests import helpers as H
from tests import test_sudden_death_v0_134 as SD
from tests.test_legal_actions_u7_1 import keys, search_board, snap
from tests.test_replay_record_v0_153 import HALT_DECK

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("headless_client", ROOT / "examples" / "headless_client.py")
REF = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(REF)
MULLIGAN_DECKS = ([H.PIKACHU] + [H.FIRE] * 59, [H.PIKACHU] * 4 + [H.FIRE] * 56)  # seed 0: プレイヤー 1 に補償 7 回
SETS = (None, "CS-KYUURA-PLAY-S2A@1", "CS-KYUURA-PLAY-PO@1")
SECRET_WORDS = ("seed", "rng", "traceback", "Traceback", "state_sha256", "rng_state")


def state_of(hub):
    """信頼されたテストの側だけが読む（クライアントの側には渡さない）。"""
    return hub._host.game.state


def endpoints(hub):
    return {0: hub.player(0), 1: hub.player(1)}, hub.host(), hub.spectator()


def assert_clean(test, value, *, sender=False):
    """応答・更新に、検証者用の値・状態の確認値・生の例外文がない（閲覧用記録の入ってはいけない項目と同じ名前。送り手への応答だけは operation_id を持ってよい）。"""
    text = json.dumps(value, ensure_ascii=False)
    forbidden = FORBIDDEN_KEYS - ({"operation_id"} if sender else set())
    test.assertFalse(set(keys(value)) & forbidden, [k for k in keys(value) if k in forbidden])
    for word in SECRET_WORDS:
        test.assertNotIn(f'"{word}"', text)


class EnvelopeTest(unittest.TestCase):
    def setUp(self):
        self.hub, _ = C.ClientHub.start(*MULLIGAN_DECKS, 0)
        self.p0, self.host, self.spec = self.hub.player(0), self.hub.host(), self.hub.spectator()

    def test_unknown_requests_are_refused_safely(self):
        base = {"contract": C.CONTRACT, "format": C.FORMAT}
        cases = [("not a dict", C.REQUEST_INVALID), ({**base, "contract": "other", "type": "view"}, C.CONTRACT_UNKNOWN),
                 ({**base, "format": 2, "type": "view"}, C.FORMAT_UNSUPPORTED), ({**base, "format": "1", "type": "view"}, C.FORMAT_UNSUPPORTED),
                 ({**base, "format": True, "type": "view"}, C.FORMAT_UNSUPPORTED), ({**base, "type": "dance"}, C.REQUEST_UNKNOWN),
                 ({**base, "type": "view", "actor": 1}, C.FIELD_UNKNOWN), ({**base, "type": "candidates", "viewer": None}, C.FIELD_UNKNOWN),
                 ({**base, "type": "inputs", "game": 1, "revision": "r", "candidate": "c1"}, C.FIELD_INVALID),
                 ({**base, "type": "inputs", "revision": "r", "candidate": "c1"}, C.FIELD_INVALID),
                 ({**base, "type": "check", "game": "g", "revision": "r", "candidate": "c1", "choices": [1.5]}, C.FIELD_INVALID),
                 ({**base, "type": "check", "game": "g", "revision": "r", "candidate": "c1", "choices": "o1"}, C.FIELD_INVALID),
                 ({**base, "type": "submit", "game": "g" * 500, "revision": "r", "candidate": "c1"}, C.FIELD_INVALID),
                 ({**base, "type": "submit", "game": "g", "revision": "r", "candidate": "c1", "operation_id": 7}, C.FIELD_INVALID)]
        before = snap(state_of(self.hub))
        for request, code in cases:
            with self.subTest(request=request):
                answer = self.p0.handle(request)
                self.assertEqual((answer["ok"], answer["error"]["code"], answer["error"]["message"]), (False, code, C.ERROR_MESSAGES[code]))
                self.assertEqual(json.loads(json.dumps(answer)), answer)
        self.assertEqual(snap(state_of(self.hub)), before)
        self.assertEqual([self.hub.take_updates(a) for a in (0, 1, "spectator", "host")], [[], [], [], []])

    def test_spectator_and_host_entries_are_separate(self):
        for kind in ("candidates", "inputs", "check", "submit"):
            self.assertEqual(REF.request(self.spec, kind, game="g", revision="r", candidate="c1")["error"]["code"], C.REQUEST_UNKNOWN)
        self.assertEqual(REF.request(self.spec, "view")["viewer"], C.ROLE_SPECTATOR)
        self.assertFalse(hasattr(self.p0, "host"))
        r = REF.request(self.host, "candidates")["response"]
        self.assertEqual(r["actor"], L.HOST)
        self.assertEqual(self.p0.handle({**REF.CONTRACT, "type": "submit", "game": r["game"], "revision": r["revision"], "candidate": "c1"})["refusal"]["code"],
                         L.CANDIDATES_WRONG_ACTOR)  # ホストの取っ手をプレイヤーの入口で使えない


class FlowTest(unittest.TestCase):
    """new_game からの合法な操作の列（クライアントの側は参照クライアントの関数だけ）。"""

    def test_reference_client_reaches_the_end(self):
        hub, notice = C.ClientHub.start(*MULLIGAN_DECKS, 0)
        self.assertEqual((notice["ok"], notice["status"]), (True, D.IN_PROGRESS))
        players, host, spectator = endpoints(hub)
        report = REF.play(players, host, spectator)
        kinds = [t.get("kind") for t in report["trace"]]
        for kind in (L.KIND_PLACE_STARTING, L.KIND_MULLIGAN_DRAW, L.KIND_REPORT_JANKEN, L.KIND_END_TURN):
            self.assertIn(kind, kinds)
        self.assertEqual(report["final"]["status"], D.GAME_OVER)  # 番を終えるだけで進めると山札がなくなって終局する
        self.assertTrue(all(t.get("outcome") == D.ACCEPTED for t in report["trace"]))
        accepted = sum(1 for t in report["trace"] if t.get("outcome") == D.ACCEPTED)
        for audience in ("0", "1", "spectator"):
            updates = report["updates"][audience]
            self.assertEqual([u["number"] for u in updates], list(range(1, accepted + 1)))  # 受理ごとに 1 つ
            for u in updates:
                assert_clean(self, u)
        assert_clean(self, report["updates"])
        self.assertEqual(json.loads(json.dumps(report)), report)

    def test_same_result_as_direct_u7_and_three_sets(self):
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                options = {} if conventions is None else {"conventions": conventions}
                hub, _ = C.ClientHub.start(*MULLIGAN_DECKS, 0, **options)
                players, host, spectator = endpoints(hub)
                report = REF.play(players, host, spectator, max_steps=40)
                direct, _ = L.ActionHost.start(*MULLIGAN_DECKS, 0, **options)
                for step in report["trace"]:
                    session = direct.host_session() if step["actor"] == L.HOST else direct.session(step["actor"])
                    r = session.candidates()
                    choices = REF.choose(step["kind"], session.inputs(r["game"], r["revision"], "c1")["stages"])
                    self.assertEqual(session.submit(r["game"], r["revision"], "c1", choices).outcome, step["outcome"])
                self.assertEqual(snap(state_of(hub)), snap(direct.game.state))

    def test_halted_and_sudden_death_display(self):
        hub, _ = C.ClientHub.start(HALT_DECK, HALT_DECK, 1)
        players, host, spectator = endpoints(hub)
        view = REF.request(spectator, "view")
        self.assertEqual((view["status"]["status"], view["status"]["waiting"], view["status"]["halt"]["category"]), (D.HALTED, [], D.RULING_UNRESOLVED))
        self.assertEqual(REF.request(players[0], "candidates")["response"]["empty_reason"], L.EMPTY_GAME_ENDED)
        state = H.build_test_state([{"active": SD.PIKA, "deck": [SD.PIKA] + [H.FIRE] * 30, "prizes": 0},
                                    {"active": SD.PIKA, "deck": [SD.PIKA] + [H.FIRE] * 30, "prizes": 0}], current_player=0)
        hub = C.ClientHub.from_state(SD.constructed_sudden_death(SD.with_decklists(state)))  # 構築: サドン・デスに移った状態
        players, host, spectator = endpoints(hub)
        view = REF.request(players[0], "view")
        self.assertEqual((view["status"]["status"], view["status"]["waiting"]), (D.SUDDEN_DEATH_PENDING, [{"kind": D.NEXT_START_SUDDEN_DEATH, "by": C.ROLE_HOST}]))
        self.assertEqual(REF.request(players[0], "candidates")["response"]["empty_reason"], L.EMPTY_HOST_OPERATION)
        trace = []
        self.assertTrue(REF.act(host, trace))
        self.assertEqual(trace[0]["kind"], L.KIND_START_SUDDEN_DEATH)
        self.assertEqual(REF.request(spectator, "view")["status"]["segment"], 1)


class DecisionAndHandleTest(unittest.TestCase):
    """構築盤面（パソコン通信の決定）。"""

    def setUp(self):
        state = search_board((H.FIRE, H.FIRE, H.PONYTA))
        self.hub = C.ClientHub.from_state(state)
        self.players, self.host, self.spectator = endpoints(self.hub)
        # トレーナーを使うのは U7 の外（ホストの側の直接の送信。公開の更新は作らない）
        result = self.hub._host.game.submit(PlayTrainer(0, state.players[0].hand[0]), submitter=0)
        self.assertEqual(result.outcome, D.ACCEPTED)

    def test_answer_decision_and_stale_handle(self):
        p0, p1 = self.players[0], self.players[1]
        r = REF.request(p0, "candidates")["response"]
        self.assertEqual(r["candidates"][0]["kind"], L.KIND_ANSWER_DECISION)
        r1 = REF.request(p1, "candidates")["response"]
        self.assertEqual((r1["candidates"], r1["situation"]), ([], L.WAITING_FOR_PLAYER))
        self.assertNotIn('"options"', json.dumps(r1))
        before = snap(state_of(self.hub))
        inputs = REF.request(p0, "inputs", game=r["game"], revision=r["revision"], candidate="c1")
        check = REF.request(p0, "check", game=r["game"], revision=r["revision"], candidate="c1", choices=["o1"])
        self.assertEqual((check["response"]["valid"], check["refetch_required"]), (False, False))
        self.assertEqual(snap(state_of(self.hub)), before)  # 取得・検査で状態・乱数・ログが変わらない
        assert_clean(self, inputs)
        done = REF.request(p0, "submit", game=r["game"], revision=r["revision"], candidate="c1", choices=["o1", "o2"], operation_id="op-1")
        self.assertEqual((done["outcome"], done["refetch_required"], done["result"]["operation_id"]), (D.ACCEPTED, True, "op-1"))
        stale = REF.request(p0, "submit", game=r["game"], revision=r["revision"], candidate="c1", choices=["o1", "o2"])
        self.assertEqual((stale["outcome"], stale["refusal"]["code"], stale["refetch_required"]), (L.REFUSED, L.CANDIDATES_STALE, True))
        wrong_game = REF.request(p0, "inputs", game="other", revision=r["revision"], candidate="c1")
        self.assertEqual((wrong_game["ok"], wrong_game["refetch_required"]), (False, True))
        updates = {a: self.hub.take_updates(a) for a in (0, 1, "spectator", "host")}
        self.assertEqual({a: [u["number"] for u in v] for a, v in updates.items()}, {0: [1], 1: [1], "spectator": [1], "host": [1]})
        for u in updates.values():
            self.assertNotIn("op-1", json.dumps(u))  # operation_id は送り手への応答だけ
        r = REF.request(p0, "candidates")["response"]  # 取り直し: 山札をさがす決定
        self.assertEqual(r["candidates"][0]["kind"], L.KIND_ANSWER_DECISION)

    def test_rejections_do_not_change_other_streams(self):
        """拒否（ホストの段・エンジン）を挟んでも、相手・観戦者の更新の列は同じ。"""
        streams = []
        for noisy in (False, True):
            state = search_board((H.FIRE, H.WATER), trainer="PMCG6-076")  # 「好きなだけ」の 0 枚はエンジンが未裁定で拒否する
            hub = C.ClientHub.from_state(state)
            hub._host.game.submit(PlayTrainer(0, state.players[0].hand[0]), submitter=0)
            p0 = hub.player(0)
            r = REF.request(p0, "candidates")["response"]
            if noisy:
                self.assertEqual(REF.request(p0, "submit", game=r["game"], revision=r["revision"], candidate="c1", choices=[])["outcome"], D.REJECTED)
                self.assertEqual(REF.request(p0, "submit", game=r["game"], revision=r["revision"], candidate="c1", choices=["o9"])["outcome"], L.REFUSED)
                self.assertEqual(REF.request(hub.host(), "submit", game=r["game"], revision=r["revision"], candidate="c1")["refusal"]["code"],
                                 L.CANDIDATES_WRONG_ACTOR)
                self.assertEqual([hub.take_updates(a) for a in (1, "spectator")], [[], []])  # 拒否だけでは更新を作らない
                r = REF.request(p0, "candidates")["response"]
            self.assertEqual(REF.request(p0, "submit", game=r["game"], revision=r["revision"], candidate="c1", choices=["o1"])["outcome"], D.ACCEPTED)
            streams.append({a: hub.take_updates(a) for a in (1, "spectator")})
        self.assertEqual(streams[0], streams[1])

    def test_internal_error_details_stay_with_the_host(self):
        seen = []
        state = search_board((H.FIRE, H.FIRE, H.PONYTA))
        hub = C.ClientHub.from_state(state, verifier=lambda actor, result: seen.append(result))
        p0 = hub.player(0)
        r = REF.request(p0, "candidates")["response"]
        with mock.patch.object(A, "apply_command", side_effect=RuntimeError("テストの内部エラーの文")):
            answer = REF.request(p0, "submit", game=r["game"], revision=r["revision"], candidate="c1")
        self.assertEqual((answer["outcome"], answer["result"]["category"]), (D.FAILED, D.INTERNAL_ERROR))
        self.assertNotIn("テストの内部エラーの文", json.dumps(answer, ensure_ascii=False))
        assert_clean(self, answer, sender=True)
        self.assertIn("テストの内部エラーの文", seen[-1].verifier.raw_message)  # 詳細はホスト・検証者の側だけ
        update = hub.take_updates(1)
        self.assertEqual((update[0]["status"]["status"], update[0]["observation"]), (D.UNAVAILABLE, None))
        for endpoint in (p0, hub.spectator(), hub.host()):
            self.assertEqual(REF.request(endpoint, "view")["error"]["code"], C.GAME_UNAVAILABLE)


class DocumentTest(unittest.TestCase):
    def test_document_records_the_contract(self):
        text = (ROOT / "docs" / "client-api-v0.164.md").read_text(encoding="utf-8")
        for phrase in ("kyuura-client-api", "ClientHub", "HostEndpoint", "operation_id", "重複の排除", "部分実装", "GameState"):
            self.assertTrue(phrase in text, phrase)


if __name__ == "__main__":
    unittest.main()
