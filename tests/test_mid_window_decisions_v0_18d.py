"""v0.18d: 窓の途中の決定（ダメージの要素のあとの窓で決定を出す効果）の設計の前提を固定するテスト。docs/mid-window-decisions-v0.18d.md。

結論は DEFER（キョウのベトベトンの「だつりょくえき」は DR1・DR6 が原典で決まらないので延期。基盤も広げていない）。ここでは、設計（続きの情報に
写す値・止まれない所・まだ決定を出す効果がないこと）がコードとずれたら気づけるように、前提をテストにする。設計の前提が変わったら、このテストと
docs/mid-window-decisions-v0.18d.md 3 章・4 章を合わせて直す（テストの期待だけを変えない）。

根拠: docs/kogas-muk-event-design-v0.17c.md 3 章（Q1〜Q10）・docs/unresolved-research-v0.18b.md 4〜6 章。kyuura の記録 id:
UQ-ENERGY-DRAIN-DECLARATION・UQ-ENERGY-DRAIN-TIMING（NEO-2000-OFFICIAL-RULES）。
"""

from __future__ import annotations

import dataclasses
import inspect
import unittest

from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.resolution import catalog as C
from kyuura_engine.resolution import codec, kernel, programs
from kyuura_engine.resolution.events import FrameKind, FrameState
from tests.helpers import KOGAS_MUK, MACHOP, PONYTA, RATTATA, build_test_state

# 3 章の表: 決定をまたぐと失われ、続きの情報（案 B）に写す必要がある枠ごとの値
FRAME_STATE_FIELDS = ("frame", "pending", "reception", "results", "coins", "origin", "applied", "evaded")
# 1 つのコマンドの解決の値のうち、きぜつの判定が使う記録（決定をまたぐと失われる）
RESOLUTION_RECORDS = ("ko_prevention_able", "knocked_by")


class DesignAssumptionTest(unittest.TestCase):
    def test_frame_state_fields_are_the_ones_the_design_covers(self):
        """続きの情報の設計（4 章の表）は、FrameState のこの 8 つの項目を写すかどうかを決めている。項目が増えたら設計を見直す。"""
        self.assertEqual(tuple(f.name for f in dataclasses.fields(FrameState)), FRAME_STATE_FIELDS)

    def test_resolution_records_that_a_decision_would_lose(self):
        """きぜつの判定の記録（同時のきぜつ・こんじょうの写し）は Resolution の値で、状態にも決定にも保存されない（決定をまたぐと失われる）。"""
        state = build_test_state([{"active": MACHOP, "bench": [RATTATA]}, {"active": PONYTA, "bench": [RATTATA]}], turn_number=7)
        res = kernel.Resolution(state)
        for name in RESOLUTION_RECORDS:
            self.assertEqual(getattr(res, name), {}, name)
        self.assertFalse(any(hasattr(state, name) for name in RESOLUTION_RECORDS))

    def test_suspend_refuses_pending_effects(self):
        """ワザの途中の決定は、送る効果が残っていると出せない（窓の途中では止まれない。Q3）。黙って送る効果を捨てない。"""
        state = build_test_state([{"active": MACHOP, "bench": [RATTATA]}, {"active": PONYTA, "bench": [RATTATA]}], turn_number=7)
        attacker = state.players[0].active
        res = kernel.Resolution(state)
        fs = res.open_frame(FrameKind.ATTACK, parent=None, player=0, source_pid=attacker.pokemon_id,
                            attack_key=E.AttackKey(MACHOP, 0))
        run = programs.AttackRun(res, fs, (), state.card_def(attacker.card).attacks[0])
        fs.pending.append(object())  # 送る効果の代わり（中身は見ない）
        with self.assertRaisesRegex(RuntimeError, "送る効果が残っている"):
            run.suspend(kind="test", player=0, options=(1,))
        self.assertIsNone(state.decision)

    def test_after_damage_window_has_no_decision(self):
        """ダメージの要素のあとの窓で処理する効果（DEFER）は、どれも決定を出さない（decision_kind が None）。処理（ACTIONS）は 2 つだけで、
        どちらも決定を出さない（関数の中で決定の口を使わない）。"""
        definitions = [d for _, d in C.POWER_DEFINITIONS + C.PERSISTENT_DEFINITIONS if d.timing is C.Timing.DEFER]
        self.assertEqual(sorted(d.name for d in definitions), ["restless_sleep", "retaliation", "strikes_back"])
        self.assertTrue(all(d.decision_kind is None for d in definitions))
        self.assertEqual(sorted(kernel.ACTIONS), ["attack_damage_to_damage_source", "power_damage_to_damage_source"])
        for action in kernel.ACTIONS.values():
            source = inspect.getsource(action)
            self.assertNotIn("push_decision", source)
            self.assertNotIn("suspend", source)

    def test_resumes_are_unchanged(self):
        """再開先は v0.16 からの 5 つのまま（窓の途中の再開先はない）。"""
        self.assertEqual(codec.RESUMES, frozenset({"attack", "knock_out", "post_knockout", "take_prize", "promote_active"}))

    def test_kogas_muk_is_still_deferred(self):
        """キョウのベトベトンは未対応のまま（効果のないものとして扱わない）。登録表にも効果の定義にもない。"""
        definition = load_card_pool().get(KOGAS_MUK)
        self.assertFalse(definition.supported)
        self.assertTrue(any("だつりょくえき" in reason for reason in definition.unsupported_reasons))
        self.assertIsNone(E.DEFAULT_EFFECTS.power_entry(KOGAS_MUK, 0))
        names = {d.name for _, d in C.POWER_DEFINITIONS + C.PERSISTENT_DEFINITIONS}
        self.assertNotIn("energy_drain", names)


if __name__ == "__main__":
    unittest.main()
