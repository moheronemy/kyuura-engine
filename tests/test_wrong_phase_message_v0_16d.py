"""v0.16d: 決定への答えを拒否する理由の文（``WRONG_PHASE``）の段階の並びを決まった順番にする（docs/legacy-test-migration-v0.16d.md 5 章）。

v0.13〜v0.15 は、決定を待つ段階（``decisions.DECISION_PHASES``。``frozenset``）の並びで理由の文を書いていたので、文字列のハッシュの乱数化
（``PYTHONHASHSEED``）によってプロセスごとに文が変わっていた（docs/kernel-integration-v0.15b.md 7 章）。ルールの変更ではなく、診断の文の
決定性の改善: 例外の種類（``IllegalActionError``）・コード（``WRONG_PHASE``）・受け付ける段階・状態・ログ・乱数は変えない。並びは段階の
定義の順（``decisions.DECISION_PHASE_ORDER``）。固定した v0.13・v0.15 との比較では、この文の段階の並びの差だけを区別して数える
（tools/engine_lockstep.py の ``wrong_phase_order_only``。tests/legacy_reference.py は並びを正規化して比べる）。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from kyuura_engine import IllegalActionError, ResolveDecision, apply_command, state_to_dict
from kyuura_engine.decisions import DECISION_PHASE_ORDER, DECISION_PHASES
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import Phase

from tests.helpers import RATTATA, build_test_state

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = "今は main。この操作は take_prize, promote_active, decision のときだけ"

PROBE = """
import json
from kyuura_engine import IllegalActionError, ResolveDecision, apply_command
from kyuura_engine.decisions import DECISION_PHASES
from tests.helpers import RATTATA, build_test_state
state = build_test_state([{"active": RATTATA}, {"active": RATTATA}])
try:
    apply_command(state, ResolveDecision(0, 0, ()))
except IllegalActionError as error:
    print(json.dumps({"set_order": [p.value for p in DECISION_PHASES], "type": type(error).__name__, "code": error.code,
                      "message": error.message}, ensure_ascii=False))
"""


def probe(seed: str) -> dict:
    """``PYTHONHASHSEED`` を ``seed`` にした別のプロセスで、決定への答えを拒否させる（``-I`` は ``PYTHONHASHSEED`` も無視するので使わない）。"""
    env = {**os.environ, "PYTHONHASHSEED": seed}
    out = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


class WrongPhaseMessageTest(unittest.TestCase):
    def board(self):
        return build_test_state([{"active": RATTATA}, {"active": RATTATA}])

    def test_message_uses_the_phase_definition_order(self):
        """番のプレイヤーの操作の段階（``main``）で決定に答えると、``WRONG_PHASE`` の理由の文は段階の定義の順で書く。拒否で状態・ログ・
        乱数を変えない。"""
        state = self.board()
        before = (state_to_dict(state, format_version=9), rng_fingerprint(state.rng))
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, ResolveDecision(0, 0, ()))
        self.assertEqual((ctx.exception.code, ctx.exception.message), ("WRONG_PHASE", EXPECTED))
        self.assertEqual((state_to_dict(state, format_version=9), rng_fingerprint(state.rng)), before)

    def test_accepted_phases_are_unchanged(self):
        """受け付ける段階は v0.13〜v0.15 と同じ 3 つ（並びの組は集合と同じ）。"""
        self.assertEqual(DECISION_PHASES, frozenset({Phase.TAKE_PRIZE, Phase.PROMOTE_ACTIVE, Phase.DECISION}))
        self.assertEqual(frozenset(DECISION_PHASE_ORDER), DECISION_PHASES)
        self.assertEqual(len(DECISION_PHASE_ORDER), len(DECISION_PHASES))

    def test_same_message_under_every_hash_seed(self):
        """``PYTHONHASHSEED`` を変えても理由の文は同じ（集合の並びが変わる seed をふくむ）。例外の種類・コードも同じ。"""
        results = {seed: probe(seed) for seed in ("0", "1", "2", "3", "4242", "random")}
        self.assertGreater(len({tuple(r["set_order"]) for r in results.values()}), 1)  # 集合の並びは seed で変わる（確かめる意味がある）
        for seed, result in results.items():
            with self.subTest(seed=seed):
                self.assertEqual((result["type"], result["code"], result["message"]), ("IllegalActionError", "WRONG_PHASE", EXPECTED))


if __name__ == "__main__":
    unittest.main()
