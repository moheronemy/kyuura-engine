"""v0.16a: 旧経路の結果の参照データ（tests/legacy_reference.py・tests/fixtures/legacy_reference_v0_15.json）そのものの確かめ。

参照データは、v0.16 で旧経路を外したあとも、v0.13 の処理の結果と比べるためのものです（docs/legacy-removal-audit-v0.16a.md 8 章）。
比べる意味がなくならないように、記録の中身（呼び出しの数・拒否と受け付けの両方・対戦の連なり）と、盤面が記録と違うときに失敗すること、
``WRONG_PHASE`` の理由の文の段階の名前の並びのほかは並べ直さないことを確かめます。
"""

import json
import unittest

from kyuura_engine import EndTurn, IllegalActionError, UnsupportedError, UseAttack

from tests import legacy_reference
from tests.helpers import FIGHTING, MACHOP, RATTATA, build_test_state


class FixtureTest(unittest.TestCase):
    def test_the_fixture_was_recorded_from_the_legacy_route(self):
        data = json.loads(legacy_reference.PATH.read_text(encoding="utf-8"))
        self.assertEqual(data["how"], legacy_reference.HOW)
        self.assertIn("a616b53aef730996e79efc97d8b17f3bdc8910e7", data["how"])  # aa551ab の kyuura_engine/ の木
        calls = data["calls"]
        kinds = {entry["outcome"][0] for entry in calls.values()}
        self.assertEqual(kinds, {"ok", "error"})
        self.assertGreater(len(calls), 1800)
        modules = {key.split(".")[1] for key in calls}
        self.assertEqual(modules, {"test_event_kernel_v0_14", "test_kernel_integration_v0_15", "test_preflight_v0_15c"})
        chains = data["chains"]
        self.assertGreater(len(chains), 30)
        self.assertGreater(sum(chain["steps"] for chain in chains.values()), 7000)
        codes = {entry["outcome"][2] for entry in calls.values() if entry["outcome"][0] == "error"}
        for code in ("UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT", "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT",
                     "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT", "UNRESOLVED_PREVENTED_COIN_DAMAGE", "UNRESOLVED_EVADED_EFFECT_COIN"):
            self.assertIn(code, codes)


class MismatchTest(unittest.TestCase):
    def test_a_different_board_is_not_compared(self):
        """記録のある呼び出しに、記録したときと違う盤面を渡すと失敗する（比べる意味がない）。"""
        recorded = next(iter(json.loads(legacy_reference.PATH.read_text(encoding="utf-8"))["calls"]))
        test_id = recorded.rsplit("#", 1)[0]

        class Fake:
            def id(self):
                return test_id

        if legacy_reference.recording():
            self.skipTest("記録するときは確かめない")
        state = build_test_state([{"active": {"card": MACHOP, "energy": [FIGHTING]}}, {"active": RATTATA}])
        store = legacy_reference._Store()
        original = legacy_reference.STORE
        legacy_reference.STORE = store
        try:
            with self.assertRaisesRegex(AssertionError, "記録したときと違う"):
                legacy_reference.expected(Fake(), state, EndTurn(0))
        finally:
            legacy_reference.STORE = original

    def test_unknown_calls_fail(self):
        class Fake:
            def id(self):
                return "tests.not_recorded.Test.test"

        if legacy_reference.recording():
            self.skipTest("記録するときは確かめない")
        state = build_test_state([{"active": {"card": MACHOP, "energy": [FIGHTING]}}, {"active": RATTATA}])
        with self.assertRaisesRegex(AssertionError, "参照データに"):
            legacy_reference.expected(Fake(), state, UseAttack(0, 0))


class WrongPhaseOrderTest(unittest.TestCase):
    def test_only_the_order_of_the_phase_names_is_normalized(self):
        a = IllegalActionError("WRONG_PHASE", "今は main。この操作は take_prize, promote_active, decision のときだけ")
        b = IllegalActionError("WRONG_PHASE", "今は main。この操作は decision, take_prize, promote_active のときだけ")
        self.assertEqual(legacy_reference.error_outcome(a), legacy_reference.error_outcome(b))
        c = IllegalActionError("WRONG_PHASE", "今は decision。この操作は decision, take_prize, promote_active のときだけ")
        self.assertNotEqual(legacy_reference.error_outcome(a), legacy_reference.error_outcome(c))

    def test_other_messages_are_kept_as_they_are(self):
        for error in (IllegalActionError("NOT_YOUR_TURN", "b, a"), UnsupportedError("UNRESOLVED_TEST", "今は main。この操作は b, a のときだけ")):
            with self.subTest(code=error.code):
                self.assertEqual(legacy_reference.error_outcome(error), ("error", type(error).__name__, error.code, error.message))


if __name__ == "__main__":
    unittest.main()
