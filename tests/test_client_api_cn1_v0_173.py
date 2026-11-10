"""v0.173（CN-1）: ``client_api.ClientHub``・``legal_actions.ActionHost`` が包む対戦の ``failure`` の接続の回帰テスト（docs/cn1-failure-v0.173.md）。

確かめること:

- 対応する包み（``adapter.HostedGame``・``replay_record.ReplayCollector``・``view_record.ViewHost``（完全な記録あり・なし）・``snapshot.RestoredGame``）で、通常の
  候補の取得・check・submit ができ、失敗のない対戦では ``failure`` が None
- エンジンの failed を注入すると、包みの ``failure`` が実際の失敗の結果（内側の ``HostedGame`` の値と同じオブジェクト）になる
- 失敗のあとの操作は入口で断られる（``CLIENT_GAME_UNAVAILABLE``）。完全な記録の終わりは aborted、同じ失敗の条件の再実行は recorded_failure
- 相手・観戦者への公開の更新・閲覧用記録には、内部の失敗の情報（例外の型・文・traceback・元のコード）が出ない
"""

from __future__ import annotations

import json
import unittest
from unittest import mock

from kyuura_engine import diagnostics as D
from kyuura_engine import preset_deck, replay_run
from kyuura_engine import snapshot as SN
from kyuura_engine.adapter import HostedGame, start_game
from kyuura_engine.client_api import ClientHub
from kyuura_engine.replay_record import END_ABORTED, ReplayCollector
from kyuura_engine.view_record import ViewHost, dumps_view_record

DECKS = (preset_deck("hitmonchan-dewgong").cards(), preset_deck("venusaur-parasect").cards())
REQ = {"contract": "kyuura-client-api", "format": 1}
SECRET = "test-cn1-secret-failure-text"


def boom(*args, **kwargs):
    raise RuntimeError(SECRET)


def wrappers():
    start = start_game(*DECKS, 1)
    restored = SN.RestoredGame(SN.restore_snapshot(SN.dumps_snapshot(SN.save_snapshot(start.state))))
    return {
        "HostedGame": HostedGame(start.state.clone()),
        "ReplayCollector": ReplayCollector.start(*DECKS, 1, include_git=False)[0],
        "ViewHost(full_record)": ViewHost.start(*DECKS, 1)[0],
        "ViewHost(no_full_record)": ViewHost.start(*DECKS, 1, full_record=False)[0],
        "RestoredGame": restored,
    }


def place(me):
    """プレイヤー 0 の初期配置を、候補・入力・check・submit で送る。"""
    r = me.handle({**REQ, "type": "candidates"})["response"]
    c = r["candidates"][0]
    handle = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
    stage = me.handle({**REQ, "type": "inputs", **handle})["response"]["stages"][0]
    choice = [next(o["id"] for o in stage["options"] if o["eligible"])]
    checked = me.handle({**REQ, "type": "check", **handle, "choices": choice})
    return checked, me.handle({**REQ, "type": "submit", **handle, "choices": choice})


class SupportedWrappersTest(unittest.TestCase):
    def test_normal_candidates_check_submit(self):
        for name, game in wrappers().items():
            with self.subTest(name):
                self.assertIsNone(game.failure)
                checked, sent = place(ClientHub(game).player(0))
                self.assertTrue(checked["response"]["valid"])
                self.assertEqual(sent["outcome"], D.ACCEPTED)
                self.assertIsNone(game.failure)


class FailurePropagationTest(unittest.TestCase):
    def fail_through_hub(self, game):
        hub = ClientHub(game)
        with mock.patch("kyuura_engine.adapter.apply_command", boom):
            _checked, sent = place(hub.player(0))
        return hub, sent

    def test_failure_is_the_real_result_and_later_requests_are_refused(self):
        for name, game in wrappers().items():
            with self.subTest(name):
                hub, sent = self.fail_through_hub(game)
                self.assertEqual(sent["outcome"], D.FAILED)
                failure = game.failure
                self.assertIsNotNone(failure)
                self.assertEqual((failure.outcome, failure.diagnosis.category), (D.FAILED, D.INTERNAL_ERROR))
                inner = game
                while not isinstance(inner, HostedGame):  # 包みは内側の HostedGame の値をそのまま返す（別の失敗の状態を持たない）
                    inner = inner._game
                self.assertIs(failure, inner.failure)
                checks = [(hub.player(0), ("view", "candidates")), (hub.player(1), ("view", "candidates")), (hub.host(), ("view", "candidates")),
                          (hub.spectator(), ("view",))]  # 観戦者の入口は candidates を受け付けない（要求の種類の誤りになる）
                for endpoint, kinds in checks:
                    for kind in kinds:
                        answer = endpoint.handle({**REQ, "type": kind})
                        self.assertEqual((answer["ok"], answer["error"]["code"]), (False, "CLIENT_GAME_UNAVAILABLE"))

    def test_records_abort_and_replay_is_recorded_failure(self):
        collector = ReplayCollector.start(*DECKS, 1, include_git=False)[0]
        self.fail_through_hub(collector)
        record = collector.close()
        self.assertEqual(record.data["end"]["state"], END_ABORTED)
        with mock.patch("kyuura_engine.adapter.apply_command", boom):  # 同じ失敗の条件のもとで再実行する
            self.assertEqual(replay_run.replay(record).status, replay_run.RECORDED_FAILURE)
        view_host = ViewHost.start(*DECKS, 1)[0]
        self.fail_through_hub(view_host)
        full, _views = view_host.close()
        self.assertEqual(full.data["end"]["state"], END_ABORTED)

    def test_no_internal_failure_details_to_other_viewers(self):
        view_host = ViewHost.start(*DECKS, 1)[0]
        hub, _sent = self.fail_through_hub(view_host)
        for audience in (1, "spectator"):
            updates = hub.take_updates(audience)
            self.assertEqual(updates[-1]["status"], {"status": D.UNAVAILABLE, "continuable": False, "waiting": []})
            self.assertIsNone(updates[-1]["observation"])
            text = json.dumps(updates, ensure_ascii=False)
            for leak in (SECRET, "RuntimeError", "Traceback", "INTERNAL_ERROR"):
                self.assertNotIn(leak, text)
        _full, views = view_host.close()
        for viewer in (1, None):
            text = dumps_view_record(views[viewer])
            for leak in (SECRET, "RuntimeError", "Traceback"):
                self.assertNotIn(leak, text)


if __name__ == "__main__":
    unittest.main()
