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
# v0.31 で ``fired``（この枠ですでに処理した送る効果の数。2 つ目は C34・C35 の問い）を加えた。ワザの途中の決定（窓のあとの決定。窓の途中ではない）を
# またいで使う値（「とうめい」の結果・``fired``・こんじょうの写し）は、``AttackRun.suspend(carry=True)`` が決定の ``context`` の ``"frame"`` に明示的な
# データで運ぶ（4 章の案 B と同じ持ち方。``PendingDecision`` に項目を加えない）。窓の途中の決定は v0.31 でも加えていない（下の 2 つのテスト。
# docs/held-cards-v0.31.md）
FRAME_STATE_FIELDS = ("frame", "pending", "reception", "results", "coins", "origin", "applied", "evaded", "fired")
# 1 つのコマンドの解決の値のうち、きぜつの判定が使う記録（決定をまたぐと失われる）
RESOLUTION_RECORDS = ("ko_prevention_able", "knocked_by")


class DesignAssumptionTest(unittest.TestCase):
    def test_frame_state_fields_are_the_ones_the_design_covers(self):
        """続きの情報の設計（4 章の表）は、FrameState のこの 8 つの項目を写すかどうかを決めている。項目が増えたら設計を見直す（v0.31 の ``fired`` は
        見直して、決定の ``context`` で運ぶ値にした。上の ``FRAME_STATE_FIELDS`` の注）。"""
        self.assertEqual(tuple(f.name for f in dataclasses.fields(FrameState)), FRAME_STATE_FIELDS)

    def test_resolution_records_that_a_decision_would_lose(self):
        """きぜつの判定の記録（同時のきぜつ・こんじょうの写し）は Resolution の値で、状態にも決定にも保存されない（決定をまたぐと失われる）。"""
        state = build_test_state([{"active": MACHOP, "bench": [RATTATA]}, {"active": PONYTA, "bench": [RATTATA]}], turn_number=7)
        res = kernel.Resolution(state)
        for name in RESOLUTION_RECORDS:
            self.assertEqual(getattr(res, name), {}, name)
        self.assertFalse(any(hasattr(state, name) for name in RESOLUTION_RECORDS))

    def test_suspend_refuses_pending_effects(self):
        """ワザの途中の決定は、送る効果が残っていると出せない（窓の途中では止まれない。Q3）。黙って送る効果を捨てない。

        v0.34: 枠の値を運ぶ決定（``carry=True``。ダメージの要素のあとに決定を出すダメージの要素 ``ChosenBenchDamage``）だけは、まだ処理していない送る
        効果を続きの情報（``frame`` の ``pending``）に運んで出せる（窓の途中の決定ではない: 送る効果はまだ処理を始めていない。決定のあとの最後の
        ダメージの要素のあとに処理する。tests/test_barrier_resume_coin_bonus_v0_34.py）。``carry`` のない決定は今までどおり出せない。"""
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
        """ダメージの要素のあとの窓で処理する効果（DEFER）は、どれも決定を出さない（decision_kind が None）。処理（ACTIONS）は 3 つだけで、
        どれも決定を出さない（関数の中で決定の口を使わない）。v0.42 でエリカのラフレシアの「ぼうぎょかふん」（同じ窓。持ち主のコインで、ダメージを
        与えたポケモンをこんらんにする。``power_confusion_to_damage_source``）を加えた。決定を出さないので、この文書の前提（窓の途中の決定はない）は
        変わらない（docs/power-decisions-v0.42.md）。

        v0.68（docs/final-pmcg-cards-v0.68.md 3 章）: キョウのベトベトンの［だつりょくえき］（``drain_energy_from_damage_source``）を同じ窓に加えた。この処理も決定の口を
        直接使わず、「おもて」のときは ``kernel.EnergyDrainRequest`` を投げ、窓を開いた ``programs.fire_or_suspend`` が、次の要素の位置（"boundary"）を続きの情報にして
        決定を出す（v0.65 の要素のあいだの決定と同じ持ち方。案 B）。窓の途中でほかの送る効果が残ることはない（1 つの枠で 2 つ以上なら C34・C35 で止める）。

        v0.81（docs/pokemon-tools-stadiums-v0.81.md 5.2）: はんげきのツメ（ポケモンのどうぐ。``counters_to_damage_source_on_heads``）を同じ窓に加えた。持ち主のコインで、
        ダメージを与えたポケモンにダメージカウンターをのせる。決定を出さないので、この文書の前提は変わらない。効果の定義はついているトレーナーのもの（``C.COUNTER_CLAW``）。"""
        definitions = [d for _, d in C.POWER_DEFINITIONS + C.PERSISTENT_DEFINITIONS if d.timing is C.Timing.DEFER]
        # v0.84（docs/light-powers-evolution-v0.84.md）: やさしいイノムーの［ふかふかなからだ］（``power_sleep_to_damage_source``）を同じ窓に加えた。持ち主のコインで、ダメージを
        # 与えたポケモンをねむりにする（「ぼうぎょかふん」と同じ形）。決定を出さないので、この文書の前提は変わらない
        self.assertEqual(sorted(d.name for d in definitions), ["defensive_pollen", "energy_drain", "fluffy_wool", "restless_sleep", "retaliation", "strikes_back"])
        self.assertTrue(all(d.decision_kind is None for d in definitions))
        self.assertEqual(sorted(kernel.ACTIONS), ["attack_damage_to_damage_source", "counters_to_damage_source_on_heads", "drain_energy_from_damage_source",
                                                  "power_confusion_to_damage_source", "power_damage_to_damage_source", "power_sleep_to_damage_source",
                                                  # v0.83: リフレクトシールドの 20（効果の定義 REFLECT_SHIELD_RETURN。決定を出さない。docs/shining-gentle-pokemon-v0.83.md 6 章）
                                                  "reflect_damage_to_damage_source"])
        self.assertEqual(C.COUNTER_CLAW.timing, C.Timing.DEFER)
        self.assertIsNone(C.COUNTER_CLAW.decision_kind)
        for action in kernel.ACTIONS.values():
            source = inspect.getsource(action)
            self.assertNotIn("push_decision", source)
            self.assertNotIn("suspend", source)

    def test_resumes_are_unchanged(self):
        """再開先は v0.16 からの 5 つのまま（窓の途中の再開先はない）。"""
        self.assertEqual(codec.RESUMES, frozenset({"attack", "knock_out", "post_knockout", "take_prize", "promote_active"}))

    def test_kogas_muk_is_supported_with_the_v0_68_spec(self):
        """v0.18d の時点ではキョウのベトベトンは未対応だった（DEFER）。v0.68 で、この特殊能力に限った採用の仕様（自動的にはたらく・ダメージの要素のあと。
        docs/final-pmcg-cards-v0.68.md 3 章。DR1・DR6 を公式に決めたことにしない）で対応にした。効果の定義は 1 か所（``catalog.ENERGY_DRAIN``）。"""
        definition = load_card_pool().get(KOGAS_MUK)
        self.assertTrue(definition.supported)
        self.assertIsInstance(E.DEFAULT_EFFECTS.power_entry(KOGAS_MUK, 0).effect, E.DiscardAttackerEnergyOnDamage)
        names = [d.name for _, d in C.POWER_DEFINITIONS + C.PERSISTENT_DEFINITIONS]
        self.assertEqual(names.count("energy_drain"), 1)


if __name__ == "__main__":
    unittest.main()
