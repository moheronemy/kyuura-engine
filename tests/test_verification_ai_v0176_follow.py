"""検証用 AI の 0.176.0（PT-5e）への追従のテスト（docs/verification-ai-v0176-follow.md）。

- 比べの形式の分離: 行動の列（``records.action_sequence``・形式 action-meaning/v2）と API の契約の値の列（``records.contract_sequence``・形式 candidate-contract/v1）。
  保証の文だけを変えても行動の列は変わらず、契約の列と旧形式（meaning/v1）は変わる。主体・種類・対象・入力・意味のある順序・結果を変えると行動の列が変わる。
  評価の値（処理可能性・eligible・理由・入力の公開・段の制約）を変えると契約の列が変わる。形式の名前の違う指紋を同じ値として比べない
- 反復の抑制の鍵（``policies.action_key``）は保証の文によらない（今回は変えていない）
- PT-5e の代表の盤面（構築盤面。エンジンのテスト ``tests/test_legal_actions_pt5e_v0_176.py`` の ``table``・``staged``・``broken_marks``。new_game からの到達ではない）で、
  AI の範囲（deep の ``option_allowed``・ランナーの ``_scope``）と判定（``judge_normal``）が API の値（処理可能性・eligible・理由）だけで決まる
"""

from __future__ import annotations

import copy
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from kyuura_engine.engine import check_invariants
from tests.test_legal_actions_pt5e_v0_176 import CARD_FLIP, PERSONALITY, POTION, QUIZ2, QZ1, broken_marks, staged, table
from tools.verification_ai import actions as B
from tools.verification_ai import judge as J
from tools.verification_ai import records as R
from tools.verification_ai import runner as V
from tools.verification_ai.policies import UniformPolicy, action_key

REQ = {"contract": "kyuura-client-api", "format": 1}


def attempt(**over):
    """trace の 1 行（ランナーが書く形の小さな例）。"""
    entry = {
        "type": "attempt", "n": 1, "actor": 0, "operation_id": "v0-000001", "build": "ok",
        "candidate": {"id": "c4", "kind": "play_trainer", "processability": "may_stop_later", "eligible": True, "reasons": ["preflight_not_evaluated"],
                      "guarantees": {"preconditions": "old text", "acceptance": "a"}, "choices_format": "[カード]", "input_disclosure": "confirmed",
                      "input_stages": [{"stage": 1, "input": "choose_option"}]},
        "stages": [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "order": "significant", "note": "n",
                    "options": [{"id": "o1", "card": 7, "card_id": "GD5-017", "eligible": True, "processability": "may_stop_later", "reasons": ["x"]}]}],
        "meaning": [{"stage": 1, "option": {"card": 7, "card_id": "GD5-017", "eligible": True, "processability": "may_stop_later", "reasons": ["x"]}}],
        "check": {"response": {"valid": True}},
        "submit": {"ok": True, "outcome": "accepted", "refusal": None, "verifier": None},
    }
    for path, value in over.items():
        target = entry
        keys = path.split("__")
        for k in keys[:-1]:
            target = target[k]
        target[keys[-1]] = value
    return entry


def rows(entry):
    trace = [entry]
    return R.action_sequence(trace), R.contract_sequence(trace), R.meaning_sequence(trace)


class FormatTest(unittest.TestCase):
    def setUp(self):
        self.base = attempt()
        self.action, self.contract, self.legacy = rows(self.base)

    def test_guarantee_text_only(self):
        """0.175.0 → 0.176.0 の差の形（play_trainer の preconditions の文だけ）: 行動の列は同じ、契約の列・旧形式は違う。"""
        changed = attempt()
        changed["candidate"]["guarantees"]["preconditions"] = "new text"
        action, contract, legacy = rows(changed)
        self.assertEqual(action, self.action)
        self.assertNotEqual(contract, self.contract)
        self.assertNotEqual(legacy, self.legacy)

    def test_handles_are_not_action_meaning(self):
        changed = attempt(candidate__id="c9", operation_id="v0-000777", n=5)
        changed["stages"][0]["options"][0]["id"] = "o5"
        self.assertEqual(rows(changed)[0], self.action)

    def test_action_differences_detected(self):
        cases = {
            "actor": attempt(actor=1),
            "kind": attempt(candidate__kind="use_power"),
            "target": attempt(candidate__pokemon={"pokemon": 3, "zone": "active"}),
            "input": attempt(meaning=[{"stage": 1, "option": {"card": 8, "card_id": "GD5-017"}}]),
            "order": attempt(meaning=[{"stage": 1, "option": {"card": 7}}, {"stage": 1, "option": {"card": 8}}]),
            "value": attempt(meaning=[{"stage": 1, "value": 3}]),
            "build": attempt(build="unbuildable", meaning=None),
            "check": attempt(check={"response": {"valid": False, "refusal": {"code": "CANDIDATE_INPUT_INVALID"}}}),
            "outcome": attempt(submit={"ok": True, "outcome": "rejected", "refusal": None, "verifier": {"diagnostic_id": "X"}}),
            "refusal": attempt(submit={"ok": True, "outcome": "refused", "refusal": {"code": "CANDIDATE_STALE"}}),
        }
        reversed_order = attempt(meaning=[{"stage": 1, "option": {"card": 8}}, {"stage": 1, "option": {"card": 7}}])
        for name, entry in cases.items():
            with self.subTest(name):
                self.assertNotEqual(rows(entry)[0], self.action)
        self.assertNotEqual(rows(cases["order"])[0], rows(reversed_order)[0])  # 選んだ順を区別する

    def test_contract_differences_detected_without_action_difference(self):
        cases = {
            "processability": attempt(candidate__processability="unverified"),
            "eligible": attempt(candidate__eligible=False),
            "reasons": attempt(candidate__reasons=[]),
            "input_disclosure": attempt(candidate__input_disclosure="unconfirmed"),
            "choices_format": attempt(candidate__choices_format="x"),
            "option_processability": attempt(meaning=[{"stage": 1, "option": {"card": 7, "card_id": "GD5-017", "eligible": True, "processability": "supported",
                                                                                "reasons": ["x"]}}]),
        }
        stage_changed = attempt()
        stage_changed["stages"][0]["count"] = {"min": 0, "max": 1}
        cases["stage_constraint"] = stage_changed
        note_changed = attempt()
        note_changed["stages"][0]["note"] = "m"
        cases["stage_note"] = note_changed
        for name, entry in cases.items():
            with self.subTest(name):
                action, contract, _ = rows(entry)
                self.assertEqual(action, self.action)  # 行動の意味は同じ
                self.assertNotEqual(contract, self.contract)  # 契約の値の違いは別の照らしで見える（広い正規化で隠さない）

    def test_formats_are_named_and_not_interchangeable(self):
        trace = [self.base]
        digests = {R.sequence_digest(f(trace), fmt)["format"]: R.sequence_digest(f(trace), fmt)
                   for f, fmt in ((R.meaning_sequence, R.LEGACY_MEANING_FORMAT), (R.action_sequence, R.ACTION_FORMAT), (R.contract_sequence, R.CONTRACT_FORMAT))}
        self.assertEqual(set(digests), {"meaning/v1", "action-meaning/v2", "candidate-contract/v1"})
        self.assertEqual(len({d["sha256"] for d in digests.values()}), 3)
        self.assertNotEqual(digests["meaning/v1"], digests["action-meaning/v2"])

    def test_legacy_format_unchanged(self):
        """旧形式（保存済みの証跡の照らしに使う）は候補の id だけを除く（評価の値・保証の文を含む）まま。"""
        self.assertEqual(self.legacy[0]["candidate"], {k: v for k, v in self.base["candidate"].items() if k != "id"})
        self.assertEqual(self.legacy[0]["meaning"], self.base["meaning"])

    def test_repetition_key_ignores_guarantee_text(self):
        a, b = attempt(), attempt()
        b["candidate"]["guarantees"]["preconditions"] = "new text"
        keys = [action_key(e["actor"], e["candidate"], e["stages"], e["meaning"]) for e in (a, b)]
        self.assertEqual(keys[0], keys[1])


def hub_and_candidates(state):
    hub = ClientHub(A.HostedGame(state))
    me = hub.player(0)
    return hub, me, me.handle({**REQ, "type": "candidates"})["response"]


def trainer(me, cands, card):
    c = next((x for x in cands["candidates"] if x["kind"] == L.KIND_PLAY_TRAINER), None)
    if c is None:
        return None, None, None
    stages = me.handle({**REQ, "type": "inputs", "game": cands["game"], "revision": cands["revision"], "candidate": c["id"]})["response"]["stages"]
    option = next((o for o in stages[0]["options"] if o["card_id"] == card), None)
    return c, stages, option


class PT5eScopeTest(unittest.TestCase):
    """構築盤面（new_game からの到達ではない）。AI の範囲はカードの一覧でなく、API の処理可能性・eligible だけで決まる。"""

    def test_passing_card_is_in_deep_scope_and_check_is_not_acceptance(self):
        state = table(QUIZ2)
        hub, me, cands = hub_and_candidates(state)
        c, stages, option = trainer(me, cands, QUIZ2)
        self.assertEqual((option["processability"], option["eligible"]), (L.MAY_STOP_LATER, True))
        self.assertTrue(B.option_allowed(option, B.DEEP_PROCESSABILITY))  # deep の既存の条件で選ぶ対象に入る
        chosen, scope, _ = V.Runner(V.Config())._scope(cands, {})
        self.assertIn(c["id"], [x["id"] for x in chosen])
        handle = {"game": cands["game"], "revision": cands["revision"], "candidate": c["id"]}
        check = me.handle({**REQ, "type": "check", **handle, "choices": [option["id"]]})["response"]
        self.assertIs(check["valid"], True)
        meaning = B.meaning_of(1, stages[0], [option["id"]])
        # check の成功は受理・完走の保証ではない: 送信が拒否されても play_trainer（PRECHECK_KINDS でない）は suspect にしない
        invalid = {"ok": True, "outcome": "rejected", "verifier": {"diagnostic_id": "X", "category": D.INVALID_INPUT, "engine_code": None}}
        self.assertEqual(J.judge_normal(c, meaning, invalid)[0], J.NORMAL_REJECTION)
        category = D.default_catalog().get(QZ1).category
        stop = {"ok": True, "outcome": "rejected", "verifier": {"diagnostic_id": QZ1, "category": category, "engine_code": QZ1}}
        self.assertEqual(J.judge_normal(c, meaning, stop)[0], J.UNDETERMINED)  # 未評価の理由はあるが、代表の条件の根拠がないので known_stop にしない
        self.assertNotIn(c["kind"], J.PRECHECK_KINDS)
        sent = me.handle({**REQ, "type": "submit", **handle, "choices": [option["id"]]})
        self.assertEqual(J.judge_normal(c, meaning, {"ok": sent["ok"], "outcome": sent["outcome"]}), (J.EXPECTED, []))  # 受理（受理のあとの決定は別）

    def test_unusable_card_is_not_offered(self):
        _hub, me, cands = hub_and_candidates(table(PERSONALITY, hand=(POTION,)))
        _c, _stages, option = trainer(me, cands, PERSONALITY)
        self.assertIsNone(option)  # ゲーム上使えない: 選べるものに出ない（AI は選べない）

    def test_stopping_card_is_not_executable(self):
        state = staged(table(CARD_FLIP), "both")
        hub, me, cands = hub_and_candidates(state)
        c, stages, option = trainer(me, cands, CARD_FLIP)
        self.assertEqual((option["eligible"], option["processability"], option["reasons"]), (False, L.RULING_UNRESOLVED, [L.REASON_STOPS]))
        for allowed in (B.DEEP_PROCESSABILITY, B.FALLBACK_PROCESSABILITY):
            self.assertFalse(B.option_allowed(option, allowed))  # deep・boundary のどちらでも選ばない
        handle = {"game": cands["game"], "revision": cands["revision"], "candidate": c["id"]}
        before = copy.deepcopy(hub.take_updates(1))
        check = me.handle({**REQ, "type": "check", **handle, "choices": [option["id"]]})["response"]
        self.assertEqual((check["valid"], check["refusal"]["code"]), (False, L.CANDIDATE_NOT_EXECUTABLE))
        self.assertEqual((before, hub.take_updates(1)), ([], []))

    def test_broken_invariant_stays_unverified(self):
        state = broken_marks(table(QUIZ2), 0, 3)  # テスト専用の改変（合法な経路ではない）
        self.assertTrue(check_invariants(state))
        _hub, me, cands = hub_and_candidates(state)
        _c, _stages, option = trainer(me, cands, QUIZ2)
        self.assertEqual((option["processability"], option["eligible"]), (L.UNVERIFIED, True))
        self.assertIn(L.REASON_USE_CONDITION, option["reasons"])
        self.assertFalse(B.option_allowed(option, B.DEEP_PROCESSABILITY))  # deep では選ばない（boundary・代替だけ）
        self.assertTrue(B.option_allowed(option, B.FALLBACK_PROCESSABILITY))


if __name__ == "__main__":
    unittest.main()
