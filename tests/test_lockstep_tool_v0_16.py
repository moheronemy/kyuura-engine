"""v0.16a: 別の木と 1 歩ごとに比べる道具（tools/engine_lockstep.py）の、許す差の判定。

固定した v0.13（8facf3a）・v0.15（aa551ab）と v0.16 を、別々の木・別々のプロセスで比べるとき（docs/legacy-removal-audit-v0.16a.md 8 章）、
許す差は、決定への答えの ``WRONG_PHASE`` の理由の文の段階の名前の並び（v0.13 からの ``frozenset`` の並び。v0.16d で決まった並びにする）
だけです。ほかの理由の文の違い・コード・状態の指紋の違いは、許さない（食い違いとして報告する）ことを確かめます。
"""

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import engine_lockstep as lockstep  # noqa: E402


def rejected(message: str, *, code: str = "WRONG_PHASE", kind: str = "IllegalActionError", step: int = 4, command: str = "c0ffee") -> dict:
    record = {"g": "natural:test:0", "i": step, "c": command, "o": [kind, code, hashlib.sha1(message.encode()).hexdigest()[:12]]}
    if code == "WRONG_PHASE":
        record["m"] = message
    return record


A = "今は main。この操作は take_prize, promote_active, decision のときだけ"
B = "今は main。この操作は decision, take_prize, promote_active のときだけ"


class WrongPhaseOrderTest(unittest.TestCase):
    def test_only_the_order_of_the_phase_names_is_allowed(self):
        self.assertTrue(lockstep.wrong_phase_order_only(rejected(A), rejected(B)))

    def test_other_differences_are_divergences(self):
        cases = {
            "今の段階が違う": rejected("今は decision。この操作は take_prize, promote_active, decision のときだけ"),
            "段階の名前の集まりが違う": rejected("今は main。この操作は take_prize, decision のときだけ"),
            "文の形が違う": rejected("今は main。この操作は take_prize, promote_active, decision のときに限る"),
            "歩が違う": rejected(B, step=5),
            "コマンドが違う": rejected(B, command="beef"),
            "例外の種類が違う": rejected(B, kind="UnsupportedError"),
        }
        for label, other in cases.items():
            with self.subTest(label):
                self.assertFalse(lockstep.wrong_phase_order_only(rejected(A), other))

    def test_other_codes_are_never_allowed(self):
        a = rejected("理由 1", code="NOT_YOUR_TURN")
        b = rejected("理由 2", code="NOT_YOUR_TURN")
        self.assertFalse(lockstep.wrong_phase_order_only(a, b))

    def test_records_without_the_message_are_never_allowed(self):
        """v0.15 までの記録（理由の文そのもの ``m`` がない）は、指紋だけでは並びの違いと確かめられないので許さない。"""
        a, b = rejected(A), rejected(B)
        del a["m"], b["m"]
        self.assertFalse(lockstep.wrong_phase_order_only(a, b))

    def test_a_message_that_does_not_match_its_digest_is_never_allowed(self):
        a, b = rejected(A), rejected(B)
        b["m"] = A.replace("main", "main ")  # 指紋と文が食い違う記録
        self.assertFalse(lockstep.wrong_phase_order_only(a, b))

    def test_accepted_steps_with_different_states_are_never_allowed(self):
        a = {"g": "natural:test:0", "i": 3, "c": "c0ffee", "o": "ok", "h": "1" * 32}
        b = dict(a, h="2" * 32)
        self.assertFalse(lockstep.wrong_phase_order_only(a, b))


if __name__ == "__main__":
    unittest.main()
