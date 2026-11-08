"""検証用 AI の V0 のテスト（docs/verification-ai-v0.md 8 章）。

- CN1Test: ``ActionHost`` と ``ReplayCollector``・``ViewHost`` の接続の問題（CN-1）の再現と、道具の側の包みでの接続・failure の伝わり方
- BuildTest: 行動生成が、段の契約（options_by_choice・upstream_stages/after・options_by_path の任意の段・options_from_stage・total_units・choose_value）から
  入力を組み立て、知らない項目で止める。実際の盤面（カツラの 2 枚目・フシギバナのエナジートランス・ラプラスのにげる）では、作った入力が check を通る
- BoundaryTest: 方策・行動生成が kyuura_engine を import しない。方策に渡る値が JSON の値だけで、その主体の入口の応答
- CheckBeforeSubmitTest・RetryTest・LimitsTest・HaltTest: check の前の送信を防ぐ・拒否の選び直しの上限・各上限と停止の分類
- RecordTest: 操作の記録とエンジンの記録の対応・replay_run の期待・意味の列の再現と違いの検出

対戦はどれも小さな上限（数十の操作）で、固定条件の V0 の実行（tools.verification_ai.run_v0）とは別です。
"""

from __future__ import annotations

import ast
import json
import pathlib
import unittest
from unittest import mock

from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine import preset_deck, replay_run
from kyuura_engine.adapter import HostStoppedError
from kyuura_engine.client_api import ClientHub
from kyuura_engine.replay_record import END_ABORTED, ReplayCollector
from kyuura_engine.view_record import ViewHost
from tests import helpers as H
from tests.test_legal_actions_u7_3 import DCE
from tests.test_legal_actions_u7_3 import board as u73_board
from tests.test_legal_actions_u7_5e import venusaur_board
from tests.test_legal_actions_u7_5g_energy2 import blaine
from tools.verification_ai import actions as B
from tools.verification_ai import records as R
from tools.verification_ai import runner as V
from tools.verification_ai.policies import UniformPolicy
from tools.verification_ai.run_v0 import expected_replay

ROOT = pathlib.Path(__file__).resolve().parents[1]
DECKS = (preset_deck("hitmonchan-dewgong").cards(), preset_deck("venusaur-parasect").cards())
REQ = {"contract": "kyuura-client-api", "format": 1}


def small(**limits):
    return V.Config(limits=V.Limits(**{"operations": 30, "seconds": 60, **limits}))


def boom(*args, **kwargs):
    raise RuntimeError("test: 処理できない結果を作る")


class CN1Test(unittest.TestCase):
    def test_view_host_and_collector_have_failure(self):
        """v0.172.0 では ReplayCollector・ViewHost が failure を持たず、ClientHub の候補の取得で AttributeError が入口の外へ出た（CN-1）。v0.173.0 で正式に直した:
        どちらも failure（失敗のない対戦では None）を持ち、ClientHub で候補を取れる（意図した差。詳しい確かめは tests/test_client_api_cn1_v0_173.py）。"""
        for name, game in (("ViewHost", ViewHost.start(*DECKS, 1)[0]), ("ReplayCollector", ReplayCollector.start(*DECKS, 1, include_git=False)[0])):
            with self.subTest(name):
                self.assertIsNone(game.failure)
                self.assertTrue(ClientHub(game).player(0).handle({**REQ, "type": "candidates"})["ok"])

    def test_wrapper_connects(self):
        game, _ = R.RecordingGame.start(*DECKS, 1)
        answer = ClientHub(game).player(0).handle({**REQ, "type": "candidates"})
        self.assertTrue(answer["ok"])
        self.assertIsNone(game.failure)

    def test_failure_propagates(self):
        """包みは failed の結果を failure として持ち、後の送信を断る。入口は CLIENT_GAME_UNAVAILABLE を返し、記録は aborted（失敗を隠さない）。"""
        game, _ = R.RecordingGame.start(*DECKS, 1)
        hub = ClientHub(game)
        me = hub.player(0)
        r = me.handle({**REQ, "type": "candidates"})["response"]
        c = r["candidates"][0]
        stage = me.handle({**REQ, "type": "inputs", "game": r["game"], "revision": r["revision"], "candidate": c["id"]})["response"]["stages"][0]
        choice = [next(o["id"] for o in stage["options"] if o["eligible"])]
        with mock.patch("kyuura_engine.adapter.apply_command", boom):
            sent = me.handle({**REQ, "type": "submit", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": choice})
        self.assertEqual(sent["outcome"], D.FAILED)
        self.assertIsNotNone(game.failure)
        self.assertEqual((game.failure.outcome, game.failure.diagnosis.category), (D.FAILED, D.INTERNAL_ERROR))
        after = me.handle({**REQ, "type": "candidates"})
        self.assertEqual((after["ok"], after["error"]["code"]), (False, "CLIENT_GAME_UNAVAILABLE"))
        with self.assertRaises(HostStoppedError):
            game.submit(None)
        self.assertEqual(game.close().data["end"]["state"], END_ABORTED)

    def test_runner_classifies_failed_and_replay_expects_recorded_failure(self):
        with mock.patch("kyuura_engine.adapter.apply_command", boom):
            result = V.run_game(small())
            self.assertEqual(result["termination"]["class"], V.FAILED)
            self.assertEqual(result["termination"]["detail"]["submit"]["verifier"]["category"], D.INTERNAL_ERROR)
            data = result["record"].data
            self.assertEqual(expected_replay(data), replay_run.RECORDED_FAILURE)
            self.assertEqual(replay_run.replay(result["record"]).status, replay_run.RECORDED_FAILURE)  # 同じ失敗の条件のもとで、同じ失敗がもう一度起きる


class FixedPolicy:
    """決まった位置を選ぶ方策（テスト用）。"""

    name, version, distribution, seed, draws = "fixed", 0, "fixed", "fixed", 0

    def __init__(self, index=0):
        self.index = index

    def choose(self, purpose, items, context):
        return min(self.index, len(items) - 1), f"fixed:{purpose}"


def opt(oid, **kw):
    return {"id": oid, "eligible": True, "processability": "supported", **kw}


class BuildTest(unittest.TestCase):
    def build(self, stages, policy=None, allowed=B.DEEP_PROCESSABILITY):
        return B.build_choices(stages, policy or FixedPolicy(), {}, allowed)

    def test_options_by_choice(self):
        stages = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1"), opt("o2")]},
                  {"stage": 2, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o3"), opt("o4")], "depends_on_stage": 1,
                   "options_by_choice": {"o1": [{"option": "o4", "eligible": True, "processability": "supported"}],
                                         "o2": [{"option": "o3", "eligible": False, "processability": "unresolved_ruling"}]}}]
        self.assertEqual(self.build(stages)[0], ["o1", "o4"])
        with self.assertRaises(B.Unbuildable):
            self.build(stages, FixedPolicy(1))  # o2 の組は実行できない区分だけ

    def test_upstream_after(self):
        stages = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1"), opt("o2")]},
                  {"stage": 2, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o3", after="o1"), opt("o4", after="o2")],
                   "depends_on_stage": 1, "upstream_stages": [1], "options_by_choice": {"o1": [{"option": "o3"}], "o2": [{"option": "o4"}]}},
                  {"stage": 3, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o5", after="o3"), opt("o6", after="o4")],
                   "depends_on_stage": 2, "upstream_stages": [1, 2], "options_by_choice": {"o3": [{"option": "o5"}], "o4": [{"option": "o6"}]}}]
        self.assertEqual(self.build(stages, FixedPolicy(1))[0], ["o2", "o4", "o6"])

    def test_options_by_path_optional(self):
        stages = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1"), opt("o2")]},
                  {"stage": 2, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o3")], "depends_on_stage": 1,
                   "options_by_choice": {"o1": [{"option": "o3"}], "o2": [{"option": "o3"}]}},
                  {"stage": 3, "input": "choose_option", "count": {"min": 0, "max": 1}, "options": [opt("o4")], "decline": True, "path_stages": [1, 2],
                   "options_by_path": {"o1/o3": [{"option": "o4", "eligible": True, "processability": "supported"}]}}]
        self.assertEqual(self.build(stages, FixedPolicy(1))[0], ["o2", "o3"])  # 鍵 o2/o3 がない: 3 段目は 0 個だけ
        self.assertEqual(self.build(stages, FixedPolicy(0))[0], ["o1", "o3"])  # 数 k の並び [0, 1] の 0 番目
        seen = {tuple(self.build(stages, UniformPolicy(f"s{i}"))[0]) for i in range(40)}
        self.assertIn(("o1", "o3", "o4"), seen)
        self.assertIn(("o1", "o3"), seen)
        self.assertNotIn(("o2", "o3", "o4"), seen)

    def test_options_from_stage_distinct_across_stages(self):
        stages = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1"), opt("o2"), opt("o3", eligible=False)]},
                  {"stage": 2, "input": "choose_option", "count": {"min": 0, "max": 5}, "options_from_stage": 1, "distinct_across_stages": True}]
        for i in range(30):
            choices, _picks, meaning = self.build(stages, UniformPolicy(f"p{i}"))
            self.assertEqual(len(set(choices)), len(choices))
            self.assertNotIn("o3", choices)
            self.assertEqual([m["stage"] for m in meaning], [1] + [2] * (len(choices) - 1))

    def test_total_units(self):
        stages = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1")]},
                  {"stage": 2, "input": "choose_option", "count": {"min": 0, "max": 3}, "total_units": {"min": 2, "max": 2},
                   "options": [opt("o2", units=2), opt("o3", units=1), opt("o4", units=1)]}]
        seen = {tuple(sorted(self.build(stages, UniformPolicy(f"u{i}"))[0][1:])) for i in range(60)}
        self.assertEqual(seen, {("o2",), ("o3", "o4")})
        stages[1]["total_units"] = {"min": 5, "max": 5}
        with self.assertRaises(B.Unbuildable) as caught:
            self.build(stages)
        self.assertEqual(caught.exception.reason, "total_units_unreachable")

    def test_choose_value(self):
        stages = [{"stage": 1, "input": "choose_value", "range": {"min": 0, "max": 2}, "count": {"min": 1, "max": 1}}]
        self.assertEqual({self.build(stages, UniformPolicy(f"v{i}"))[0][0] for i in range(40)}, {0, 1, 2})

    def test_unknown_contract_stops(self):
        base = {"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "options": [opt("o1")]}
        with self.assertRaises(B.ContractUnknown):
            self.build([{**base, "new_constraint": True}])
        with self.assertRaises(B.ContractUnknown):
            self.build([{**base, "input": "choose_rank"}])

    def real(self, state, kind, seeds=40):
        """実際の盤面: U7 の応答から作った入力が、どれも check を通る。"""
        hub = ClientHub.from_state(state)
        me = hub.player(0)
        r = me.handle({**REQ, "type": "candidates"})["response"]
        c = next(x for x in r["candidates"] if x["kind"] == kind)
        stages = me.handle({**REQ, "type": "inputs", "game": r["game"], "revision": r["revision"], "candidate": c["id"]})["response"]["stages"]
        built = []
        for i in range(seeds):
            choices, _picks, meaning = B.build_choices(stages, UniformPolicy(f"real{i}"), {}, B.FALLBACK_PROCESSABILITY)
            checked = me.handle({**REQ, "type": "check", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": choices})
            self.assertTrue(checked["response"]["valid"], (choices, checked))
            built.append((choices, meaning))
        return stages, built

    def test_real_energy2_options_by_path(self):
        stages, built = self.real(blaine(), L.KIND_ATTACH_ENERGY)
        self.assertEqual(stages[2]["path_stages"], [1, 2])
        self.assertTrue(any(len(c) == 3 for c, _ in built) and any(len(c) == 2 for c, _ in built))

    def test_real_power_three_stages(self):
        stages, built = self.real(venusaur_board(), L.KIND_USE_POWER)
        self.assertEqual([s["role"] for s in stages], ["source", "energy", "target"])
        self.assertTrue(all(len(c) == 3 for c, _ in built))

    def test_real_retreat_total_units(self):
        state = u73_board({"active": {"card": H.LAPRAS, "energy": [DCE, H.WATER]}, "bench": [H.CHARMANDER]})
        _stages, built = self.real(state, L.KIND_RETREAT)
        self.assertEqual({tuple(m["option"]["card_id"] for m in meaning[1:]) for _c, meaning in built}, {(DCE,)})


class RecordingPolicy(UniformPolicy):
    contexts: list = []

    def choose(self, purpose, items, context):
        RecordingPolicy.contexts.append((self.seed, purpose, json.loads(json.dumps(items)), context))
        return super().choose(purpose, items, context)


def json_only(value) -> bool:
    if isinstance(value, dict):
        return all(type(k) is str and json_only(v) for k, v in value.items())
    if isinstance(value, list):
        return all(json_only(v) for v in value)
    return value is None or type(value) in (str, int, float, bool)


class BoundaryTest(unittest.TestCase):
    def test_policy_and_actions_do_not_import_engine(self):
        for name in ("policies.py", "actions.py"):
            tree = ast.parse((ROOT / "tools" / "verification_ai" / name).read_text(encoding="utf-8"))
            imported = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)] + \
                       [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
            self.assertFalse([m for m in imported if "kyuura" in m or m.startswith(".")], (name, imported))

    def test_policy_receives_only_own_json(self):
        RecordingPolicy.contexts = []
        V.run_game(small(), policy_factory=RecordingPolicy)
        self.assertTrue(RecordingPolicy.contexts)
        for seed, purpose, items, context in RecordingPolicy.contexts:
            self.assertTrue(json_only(items) and json_only(context), purpose)
            actor = seed.split(":")[1]
            view = context.get("view") or {}
            if actor == "player":
                player = int(seed.split(":")[-1])
                self.assertEqual(view.get("viewer"), player)
                if purpose == "candidate":
                    self.assertEqual(context["candidates"]["actor"], player)
            else:
                self.assertEqual(view.get("viewer"), "host")  # ホストの係はホストの入口の観測（観戦者と同じ範囲）だけ
            text = json.dumps(context, ensure_ascii=False)
            for secret in ("decklists", "rng", "game_seed", "\"seed\""):
                self.assertNotIn(secret, text)


class CheckBeforeSubmitTest(unittest.TestCase):
    def test_submit_requires_matching_valid_check(self):
        class Endpoint:
            calls = 0

            def handle(self, request):
                Endpoint.calls += 1
                return {}

        handle = {"game": "g", "revision": "r", "candidate": "c1"}
        ok = {"response": {"valid": True}, "_handle": handle, "_choices": ["o1"]}
        for checked, choices in ((None, ["o1"]), ({"response": {"valid": False}, "_handle": handle, "_choices": ["o1"]}, ["o1"]), (ok, ["o2"]),
                                 ({**ok, "_handle": {**handle, "candidate": "c2"}}, ["o1"])):
            with self.assertRaises(V.SubmitWithoutCheck):
                V.submit_checked(Endpoint(), handle, choices, checked, operation_id="x")
        self.assertEqual(Endpoint.calls, 0)
        V.submit_checked(Endpoint(), handle, ["o1"], ok, operation_id="x")
        self.assertEqual(Endpoint.calls, 1)


class Faulty:
    """入口の応答を差し替える（テスト用の故障の注入。エンジンには渡さない）。"""

    def __init__(self, endpoint, change):
        self.endpoint, self.change = endpoint, change

    def handle(self, request):
        return self.change(request, self.endpoint)


def fault(kinds, make, actors=(0, 1)):
    def wrap(actor, endpoint):
        if actor not in actors:
            return endpoint
        return Faulty(endpoint, lambda req, ep: make(req, ep) if req["type"] in kinds else ep.handle(req))
    return wrap


class RetryTest(unittest.TestCase):
    def assert_no_progress(self, result, counter):
        """同じ状態の拒否の上限（16）か、試した入力の選び直しの上限（64）で止まる（入力の組が少なければ後者が先に効く）。無限に繰り返さない。"""
        detail = result["termination"]["detail"]
        self.assertEqual(result["termination"]["class"], V.NO_PROGRESS)
        limits = V.Limits()
        if detail["reason"] == "rejections_per_position":
            self.assertEqual(result["counters"][counter], limits.rejections_per_position)
        else:
            self.assertEqual((detail["reason"], detail["draws"]), ("draws_per_position", limits.draws_per_position))
            self.assertLess(result["counters"][counter], limits.rejections_per_position)
            self.assertEqual(result["counters"][counter] + result["counters"]["retry_same_input"] + result["counters"]["unbuildable"], limits.draws_per_position)

    def test_check_invalid_retry_limit_then_no_progress(self):
        result = V.run_game(small(), wrap_endpoint=fault({"check"}, lambda req, ep: {"ok": True, "response": {"valid": False, "refusal": {"code": "TEST"}}}))
        self.assert_no_progress(result, "check_invalid")
        self.assertEqual(result["counters"]["operations"], 0)  # check を通らない入力は送らない

    def test_refused_after_valid_check_is_an_anomaly_candidate(self):
        refused = {"ok": True, "outcome": "refused", "refusal": {"code": L.CANDIDATE_INPUT_INVALID}, "result": None, "refetch_required": False}
        result = V.run_game(small(), wrap_endpoint=fault({"submit"}, lambda req, ep: dict(refused)))
        self.assert_no_progress(result, "refused")
        self.assertEqual({a["kind"] for a in result["anomalies"]}, {"check_valid_but_submit_refused"})

    def test_withheld_inputs_stop_with_input_unavailable(self):
        def withheld(req, ep):
            answer = ep.handle(req)
            answer["response"] = {"candidate": req["candidate"], "kind": "x", "withheld": {"code": L.INPUT_BOUNDARY_UNCONFIRMED, "message": ""}, "stages": []}
            return answer
        result = V.run_game(small(), wrap_endpoint=fault({"inputs"}, withheld))
        self.assertEqual(result["termination"]["class"], V.INPUT_UNAVAILABLE)
        self.assertEqual(result["termination"]["detail"]["scope"]["excluded"], {"unbuildable:withheld": 1})


class LimitsTest(unittest.TestCase):
    def test_each_limit(self):
        for limits, expected, counter, value in (({"operations": 5}, V.LIMIT_OPERATIONS, "operations", 5),
                                                 ({"operations": 100, "accepted": 4}, V.LIMIT_ACCEPTED, "accepted", 4),
                                                 ({"operations": 200, "turns": 2}, V.LIMIT_TURNS, "turns", 2)):
            with self.subTest(expected):
                result = V.run_game(small(**limits))
                self.assertEqual(result["termination"]["class"], expected)
                self.assertEqual(result["counters"][counter], value)

    def test_time_limit_with_monotonic_clock(self):
        ticks = iter(range(10_000))
        result = V.run_game(small(seconds=20), clock=lambda: float(next(ticks)))
        self.assertEqual(result["termination"]["class"], V.LIMIT_TIME)


class HaltTest(unittest.TestCase):
    def halted(self, category):
        def change(req, ep):
            answer = ep.handle(req)
            answer["status"] = {**answer["status"], "status": D.HALTED, "halt": {"diagnostic_id": "X", "category": category}}
            return answer
        return V.run_game(small(), wrap_endpoint=fault({"view"}, change, actors=(V.HOST,)))["termination"]["class"]

    def test_known_and_unclassified_halts(self):
        self.assertEqual(self.halted(D.RULING_UNRESOLVED), V.HALTED_KNOWN)
        self.assertEqual(self.halted(D.UNMAPPED), V.HALTED_UNCLASSIFIED)  # 未知の停止を既知として扱わない


class RecordTest(unittest.TestCase):
    def test_record_correspondence_replay_and_meaning(self):
        a = V.run_game(small(operations=60))
        b = V.run_game(small(operations=60))
        self.assertEqual(a["termination"]["class"], V.LIMIT_OPERATIONS)
        for res in (a, b):
            self.assertEqual(R.correspondence(res["trace"], res["record"].data), [])
        data = a["record"].data
        self.assertEqual(expected_replay(data), replay_run.SUCCEEDED)
        self.assertEqual(replay_run.replay(a["record"]).status, replay_run.SUCCEEDED)
        ma, mb = R.meaning_sequence(a["trace"]), R.meaning_sequence(b["trace"])
        self.assertTrue(R.compare_meanings(ma, mb, len(ma))["equal"])
        self.assertNotIn("operation_id", json.dumps(ma))
        other = V.run_game(V.Config(policy_seed=2, limits=V.Limits(operations=60, seconds=60)))
        self.assertFalse(R.compare_meanings(ma, R.meaning_sequence(other["trace"]), len(ma))["equal"])  # 比べは違いを見つける


if __name__ == "__main__":
    unittest.main()
