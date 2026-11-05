"""v0.141（docs/prize-order-v0140-cleanup-v0.141.md）: v0.140 のサイドを取る順番の件の、互換性の例外・期待値の更新・旧状態の拒否の整理。サイドを取る順番の規約
（USER-PRIZE-ORDER-ALWAYS-CHOSEN・USER-PRIZE-ORDER-PER-PLAYER）は変えていない（その規約のテストは tests/test_prize_order_user_rule_v0_140.py）。

- ``RuleChangedChainTest``: 旧経路の記録と全体では比べない対戦（``tests/legacy_reference.RULE_CHANGED_CHAINS``）の確かめ（2 章）。従来の順で答えたやり直しが記録と同じ・違いはじめる歩より
  前が同じ・prize_first の歩と答えが登録と同じ、を求め、無関係な差（わざと加えた違い・登録の値の違い）を許さない
- ``StateClassificationTest``: 保留中の決定の 5 つの分類（正常・前の版の決定・知らない再開先・続けるのに必要な情報の不足・矛盾）の例外・文と、拒否で状態・乱数・ログが変わらないこと（4 章）
- ``OldStateOriginTest``: v0.138・v0.139 の木で正しく作った、両方がサイドを取る途中の状態が、この版で作った状態から先に取るプレイヤーの記録を除いたものと区別できない（作った版を
  推測しない理由。4 章）

accepted の数の分け方（3 章）は、5 つの対戦のテストの ``test_counts``（``prize_first_answered``）が確かめる。
"""

from __future__ import annotations

import dataclasses
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import event_kernel_compare as compare
import stress_engine as stress

from kyuura_engine import (
    EndTurn,
    EngineError,
    PromoteActive,
    ResolveDecision,
    StateIntegrityError,
    TakePrize,
    UnsupportedError,
    apply_command,
    observe,
    state_to_dict,
)
from kyuura_engine.decisions import DECISION_UNSUPPORTED_CODE
from kyuura_engine.state import Phase
from tests import legacy_reference as L
from tests.test_prize_order_user_rule_v0_140 import (
    OLD_COMMITS,
    OldVersionStateTest,
    answer,
    legal_double_knockout,
    snapshot,
    take_all,
    takes,
    with_decision,
)

LABEL, RULE = next(iter(L.RULE_CHANGED_CHAINS.items()))


class _Recorder:
    """``compare.stress_game`` に比べる関数のかわりに渡す: 処理して ``legacy_reference.Chain`` に足すだけ（記録と比べない）。"""

    def __init__(self, chain, apply):
        self.chain, self.apply = chain, apply
        self.counts = Counter()

    def begin(self, game):
        pass

    def end(self):
        pass

    def __call__(self, state, command):
        try:
            new = self.apply(state, command)
        except EngineError as error:
            self.chain.add(state, command, L.error_outcome(error))
            raise
        self.chain.add(state, command, ("ok", L.digest(new)))
        return new


def play_chain(apply=apply_command):
    _kind, name, seed, steps, illegal_rate = RULE.game
    chain = L.Chain(LABEL)
    compare.stress_game(_Recorder(chain, apply), next(s for s in stress.ALL_SCENARIOS if s.name == name), seed, steps=steps, illegal_rate=illegal_rate)
    return chain


def value_of(chain):
    return {"steps": chain.steps, "digest": chain._hash.hexdigest()[:32]}


def noisy_at(n):
    """``n`` 回目に受け付けた処理の結果だけに、公開のログを 1 つ加える（わざと加える、規約の変更と関係のない違い）。"""
    calls = [0]

    def apply(state, command):
        new = apply_command(state, command)
        calls[0] += 1
        if calls[0] == n:
            new = new.clone()
            new.add_event("note", text="unrelated")
        return new

    return apply


class RuleChangedChainTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entry = json.loads(L.PATH.read_text(encoding="utf-8"))["chains"][LABEL]
        cls.chain = play_chain()
        cls.replay = L.previous_order_replay(RULE)

    def check(self, *, chain=None, rule=RULE, entry=None, replay=None):
        chain = chain or self.chain
        L.check_rule_changed_chain(chain, rule, entry or self.entry, value_of(chain), replay or self.replay)

    def test_registered_chain_passes(self):
        self.assertEqual(RULE.convention, "CONV:USER-PRIZE-ORDER-ALWAYS-CHOSEN")
        self.check()

    def test_previous_order_replay_reproduces_the_record(self):
        """prize_first に番のプレイヤーで答えて（方策の乱数を使わずに）進め、決定の番号・first だけをもどすと、記録（306 歩）と同じ。"""
        self.assertEqual(self.replay.value(), self.entry)
        self.assertEqual(self.replay.answered, 1)

    def test_first_difference_is_the_added_decision(self):
        """違いはじめる歩 259（両方がきぜつするワザ）は、入力が同じで結果だけが違う（prize_first を待つ）。次の歩 260 が方策の答え（番のプレイヤー 1 が相手 0 を選んだ。従来と
        違う取る順番）。"""
        n = RULE.first_difference
        self.assertEqual(self.chain.rows[:n], self.replay.rows[:n])
        self.assertEqual(self.chain.rows[n][0], self.replay.rows[n][0])
        self.assertNotEqual(self.chain.rows[n][1], self.replay.rows[n][1])
        self.assertEqual(self.chain.prize_first, [(n + 1, {"type": "resolve_decision", "player": 1, "decision": 12, "choices": [0]})])
        self.assertNotEqual(value_of(self.chain), self.entry)

    def test_unrelated_difference_is_rejected(self):
        """わざと加えた違いを許さない。違いはじめる歩より前（実際の対戦で）・後（やり直しで。後の歩はやり直しが記録と比べる）・両方。"""
        before = play_chain(noisy_at(100))
        with self.assertRaisesRegex(AssertionError, "より前の歩"):
            self.check(chain=before)
        with self.assertRaisesRegex(AssertionError, "説明できない差"):
            self.check(replay=L.previous_order_replay(RULE, apply=noisy_at(200)))
        with self.assertRaisesRegex(AssertionError, "説明できない差"):
            self.check(chain=play_chain(noisy_at(210)), replay=L.previous_order_replay(RULE, apply=noisy_at(210)))

    def test_wrong_registration_is_rejected(self):
        other_answer = ((260, {"type": "resolve_decision", "player": 1, "decision": 12, "choices": [1]}),)
        with self.assertRaisesRegex(AssertionError, "登録"):
            self.check(rule=dataclasses.replace(RULE, prize_first=other_answer))
        with self.assertRaisesRegex(AssertionError, "登録"):
            self.check(rule=dataclasses.replace(RULE, prize_first=()))
        with self.assertRaisesRegex(AssertionError, "違わない"):
            self.check(rule=dataclasses.replace(RULE, first_difference=258))
        with self.assertRaisesRegex(AssertionError, "より前の歩 259"):
            self.check(rule=dataclasses.replace(RULE, first_difference=261))
        with self.assertRaisesRegex(AssertionError, "記録と同じ"):
            self.check(entry=value_of(self.chain))

    def test_previous_order_form_is_narrow(self):
        """記録の形へのもどしは、決定の番号と、番のプレイヤーの first だけ。ほかの値の first は失敗、ほかの項目は変えない。"""
        start = legal_double_knockout(rocket=False)
        state = answer(start, start.current_player)
        data = state_to_dict(state, format_version=9)
        back = L._previous_order_form(data, 1, state.current_player)
        self.assertNotIn("first", back["decision"]["context"])
        self.assertEqual(back["next_decision_id"], data["next_decision_id"] - 1)
        self.assertEqual({k: v for k, v in back.items() if k not in ("decision", "next_decision_id")},
                         {k: v for k, v in data.items() if k not in ("decision", "next_decision_id")})
        with self.assertRaisesRegex(AssertionError, "番のプレイヤー"):
            L._previous_order_form(data, 1, 1 - state.current_player)

    def test_unlisted_chain_with_prize_first_is_rejected(self):
        other = next(label for label in json.loads(L.PATH.read_text(encoding="utf-8"))["chains"] if label != LABEL)
        chain = L.Chain(other)
        chain.prize_first.append((0, {"type": "resolve_decision"}))
        with self.assertRaisesRegex(AssertionError, "RULE_CHANGED_CHAINS にない"):
            chain.finish()


INSUFFICIENT = "続けるのに必要な情報が不足"


class StateClassificationTest(unittest.TestCase):
    """保留中の決定の分類（docs/prize-order-v0140-cleanup-v0.141.md 4 章）。"""

    @classmethod
    def setUpClass(cls):
        cls.start = legal_double_knockout(rocket=False)  # prize_first を待つ（番のプレイヤー 0）
        cls.take = answer(cls.start, 0)  # P0 の take_prize（first=0）

    def cases(self):
        n = len(self.start.players[0].prizes)
        no_first = with_decision(self.start, kind="take_prize", resume="take_prize", options=tuple(range(n)), context=(("remaining", (1,)),))
        no_first.phase = Phase.TAKE_PRIZE
        return {
            "retired": (with_decision(self.start, kind="prize_order", resume="prize_order"), UnsupportedError, "前の版の決定"),
            "unknown_resume": (with_decision(self.take, resume="future_resume"), UnsupportedError, "この版が知らない再開先"),
            "insufficient": (no_first, StateIntegrityError, INSUFFICIENT),
            "interleaved": (with_decision(self.take, context=(("remaining", (1,)), ("first", 1))), StateIntegrityError, "まとめていない"),
            "bad_first": (with_decision(self.take, context=(("remaining", (1,)), ("first", 7))), StateIntegrityError, "正しくない"),
        }

    def test_rejections(self):
        for name, (state, error, text) in self.cases().items():
            with self.subTest(case=name):
                before = snapshot(state)
                d = state.decision
                for command in (ResolveDecision(d.player, d.id, (d.options[0],)), TakePrize(d.player, 0), PromoteActive(d.player, 0)):
                    with self.assertRaises(error) as ctx:
                        apply_command(state, command)
                    message = str(ctx.exception)
                    self.assertIn(text, message)
                    for word in ("壊れ", "後の版", "future"):  # 作った版・壊れたと決めつけない。状態の中の文字列を書かない
                        self.assertNotIn(word, message)
                    self.assertEqual("v0.139" in message, name == "retired")  # 版を書くのは、前の版の名前と分かる決定だけ
                    if error is StateIntegrityError:
                        self.assertEqual(INSUFFICIENT in message, name == "insufficient")  # 不足と矛盾を書き分ける
                if error is UnsupportedError:
                    with self.assertRaises(UnsupportedError) as ctx:
                        observe(state, 0)
                    self.assertEqual(ctx.exception.code, DECISION_UNSUPPORTED_CODE)
                    with self.assertRaises(UnsupportedError):
                        apply_command(state, EndTurn(state.current_player))
                else:
                    observe(state, 0)  # 知っている再開先なので観測は作れる
                self.assertEqual(snapshot(state), before)

    def test_normal_states_continue(self):
        for first in (0, 1):
            with self.subTest(first=first):
                state = take_all(answer(self.start, first))
                self.assertEqual(takes(state), [first, 1 - first])
                observe(state, 0)


class OldStateOriginTest(unittest.TestCase):
    """v0.138・v0.139 の木で正しく作った、両方が取る途中のサイドの決定には、作った版の記録がない。この版で作った同じ場面の状態から、先に取るプレイヤーの記録（first）を除き、
    決定の番号をもどすと、書き出しの値が同じになる（状態から作った版を区別できない）。"""

    COMMITS = OLD_COMMITS
    setUpClass = classmethod(OldVersionStateTest.setUpClass.__func__)
    load = OldVersionStateTest.load

    def test_old_state_is_indistinguishable(self):
        start = legal_double_knockout(rocket=False)
        now = state_to_dict(answer(start, start.current_player), format_version=34)
        now = L._previous_order_form(now, 1, start.current_player)
        for version, _ in self.COMMITS:
            with self.subTest(version=version):
                old = self.load(version, "take_prize_both")
                data = state_to_dict(old, format_version=34)
                self.assertEqual([k for k in data if "version" in k], ["format_version"])  # エンジンの版の項目はない（effects の id は v0.13 からの固定の名前）
                self.assertEqual(data["effects"], now["effects"])
                self.assertEqual({k for k in data if data[k] != now.get(k)}, set())
                with self.assertRaises(StateIntegrityError) as ctx:
                    apply_command(old, ResolveDecision(0, old.decision.id, (0,)))
                self.assertIn(INSUFFICIENT, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
