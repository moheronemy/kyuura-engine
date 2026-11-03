"""v0.140（docs/prize-order-user-rule-v0.140.md）: サイドを取る順番の利用者の指定（2 章）と、知らない再開先の決定の拒否（3 章）。

**新しい規約のテスト**（利用者の指定 USER-PRIZE-ORDER-ALWAYS-CHOSEN・USER-PRIZE-ORDER-PER-PLAYER。公式の裁定ではない）:

- ``AlwaysChosenTest``: 同じきぜつの処理で両方がサイドを取るときは、おもて・うら・［おみとおし］・本人だけが知るサイドによらず、番のプレイヤーに先に取るプレイヤーの決定
  （``prize_first``）を出す。一方だけが取るなら出さない
- ``PerPlayerTest``: 先に選ばれたプレイヤーがその処理の分をすべて取ってから、もう一方が取る（交互にしない・選び直さない）。勝ち負け・サドン・デスの判定はすべて取ってから
- ``OrderAndInformationTest``: 選べるサイドの位置が同じでも、取る順番と決定の時点の情報で選択と結果が変わりうる
- ``PrizeFirstAnswerTest``: 決める人と選ぶ人の分離・観測・不正な答え・保存と復元

**不具合の修正のテスト**（両モード共通。v0.139 の追加検証の FU-D2）:

- ``UnsupportedDecisionTest``: この版が扱えない再開先（後の版の状態の写し・前の版の決定 ``prize_order``）は、観測・コマンドの前に ``UnsupportedError``（``UNSUPPORTED_DECISION``）。
  知っている再開先の壊れた状態は ``StateIntegrityError``（取り違えない）。状態・乱数・ログは変わらない
- ``OldVersionStateTest``: v0.139（789f58e）・v0.138（4ded418）の木で作った状態の写し（pickle）を、この版で読んだときの扱い（``git archive`` の読み取り用の木・別のプロセス）

再現の種類: ``legal_*`` は new_game からの合法な操作の列（seed は前の版の記録のまま固定。選び直していない）。``*_board`` は盤面を直接作った状態（``build_test_state``）と合法なコマンド。
"""

from __future__ import annotations

import dataclasses
import io
import json
import os
import pathlib
import pickle
import subprocess
import sys
import tarfile
import tempfile
import unittest

from kyuura_engine import (
    AttachEnergy,
    EndTurn,
    EngineError,
    EvolvePokemon,
    PlayTrainer,
    PromoteActive,
    ResolveDecision,
    StateIntegrityError,
    TakePrize,
    UnsupportedError,
    UseAttack,
    apply_command,
    check_invariants,
    expand_decklist,
    new_game,
    observe,
    state_to_dict,
    visible_log,
)
from kyuura_engine.commands import UsePokemonPower
from kyuura_engine.decisions import (
    DECISION_UNSUPPORTED_CODE,
    RETIRED_DECISIONS,
    USER_PRIZE_ORDER_RULES,
)
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import Phase
from kyuura_engine.zones import reveal_prize
from tests import helpers as H
from tests.test_prize_order_hc1_fix_v0_139 import (
    SELFDESTRUCT,
    legal_double_knockout,
    partial_board,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
FOSSIL, CLEFAIRY_DOLL = H.MYSTERIOUS_FOSSIL, H.CLEFAIRY_DOLL


def cid(state, uid):
    return state.cards[uid].card_id


def answer(state, choice):
    d = state.decision
    new = apply_command(state, ResolveDecision(d.player, d.id, (choice,)))
    problems = check_invariants(new)
    assert problems == [], problems
    return new


def snapshot(state):
    return state_to_dict(state, format_version=34), rng_fingerprint(state.rng), len(state.log)


def takes(state):
    return [e["player"] for e in state.log if e["kind"] == "take_prize"]


def take_all(state, pick=lambda s: 0):
    """順番の決定のあとのサイドの決定をすべて答える（``pick`` で位置を選ぶ）。取ったあとの決定（バトル場に出すなど）の手前で返す。"""
    while state.decision is not None and state.decision.kind == "take_prize":
        state = answer(state, pick(state))
    return state


def knowledge_board(*, omanyte=False, spy=None):
    """盤面を直接作った状態（P1 の番）から、合法なコマンドで P0 の番のじばくまで（v0.139 の追加検証の K1〜K5 と同じ盤面。scripts/prize_order_followup.py）。
    P0 のサイド [なにかの化石, 雷, 雷]・P1 のサイド [ピッピ人形, 水, 水]。``omanyte`` なら P1 のベンチにオムナイト（［おみとおし］）。``spy`` は P1 が［スパイ］で見る場所
    （``"own"``: 自分のサイドの位置 0・``"opponent"``: 相手のサイドの位置 0）。どのサイドもうら。"""
    bench1 = [H.RATTATA] + ([{"card": H.OMANYTE, "evolved_from": FOSSIL}] if omanyte else [])
    state = H.build_test_state([
        {"active": {"card": H.MAGNEMITE, "energy": [H.LIGHTNING, H.LIGHTNING]}, "bench": [H.MAGNEMITE], "prizes": [FOSSIL, H.LIGHTNING, H.LIGHTNING],
         "deck": [H.LIGHTNING] * 5},
        {"active": H.JUNGLE_MANKEY, "bench": bench1, "prizes": [CLEFAIRY_DOLL, H.WATER, H.WATER], "deck": [H.WATER] * 5},
    ], current_player=1, turn_number=4)
    if spy is not None:
        state = apply_command(state, UsePokemonPower(1, state.players[1].active.pokemon_id, 0))
        owner = 1 if spy == "own" else 0
        targets = state.decision.context_value("targets")
        state = answer(state, next(i for i, t in enumerate(targets) if tuple(t[:3]) == ("prize", owner, 0)))
    return apply_command(apply_command(state, EndTurn(1)), UseAttack(0, SELFDESTRUCT))


def legal_omanyte_board():
    """new_game(seed 2) からの合法な操作の列（v0.139 の追加検証の K4L。scripts/prize_order_followup.py の ``legal_omanyte_board`` と同じ列）。P1 のオムナイトの［おみとおし］で
    P0 の手札が全員に見え、5 番の P0 のじばくで両方のバトル場がきぜつする。どのサイドもうら。"""
    def card(state, player, card_id):
        return next(u for u in state.players[player].hand if cid(state, u) == card_id)

    deck0, deck1 = {"PMCG1-036": 4, "PMCG1-100": 56}, {"PMCG1-060": 4, "PMCG3-046": 4, "PMCG3-015": 4, "PMCG1-099": 48}
    state = H.finish_setup(new_game(expand_decklist(deck0), expand_decklist(deck1), 2), janken_winner=0)
    state = apply_command(apply_command(state, AttachEnergy(0, card(state, 0, "PMCG1-100"), state.players[0].active.card)), EndTurn(0))
    state = apply_command(apply_command(state, PlayTrainer(1, card(state, 1, "PMCG3-046"))), EndTurn(1))
    state = apply_command(apply_command(state, AttachEnergy(0, card(state, 0, "PMCG1-100"), state.players[0].active.card)), EndTurn(0))
    fossil = next(b for b in state.players[1].bench if cid(state, b.card) == "PMCG3-046")
    state = apply_command(apply_command(state, EvolvePokemon(1, card(state, 1, "PMCG3-015"), fossil.pokemon_id)), EndTurn(1))
    return apply_command(state, UseAttack(0, SELFDESTRUCT))


def units_board(case):
    """盤面を直接作った状態と合法なじばく（v0.139 の追加検証の 2v1・2v2・2v1-last と同じ盤面。おもてにしない）。"""
    bench0 = [H.MAGNEMITE] if case != "2v2" else [{"card": H.MAGNEMITE, "damage": 30}, H.MAGNEMITE]
    prizes1 = [H.WATER, H.RATTATA, H.LIGHTNING] if case != "2v1-last" else [H.RATTATA]
    state = H.build_test_state([
        {"active": {"card": H.MAGNEMITE, "energy": [H.LIGHTNING, H.LIGHTNING]}, "bench": bench0, "prizes": [H.LIGHTNING, H.RATTATA, H.WATER], "deck": [H.LIGHTNING] * 5},
        {"active": H.RATTATA, "bench": [{"card": H.RATTATA, "damage": 20}, H.RATTATA], "prizes": prizes1, "deck": [H.WATER] * 5},
    ])
    return apply_command(state, UseAttack(0, SELFDESTRUCT))


# ================================================================ 新しい規約（利用者の指定）


class AlwaysChosenTest(unittest.TestCase):
    """USER-PRIZE-ORDER-ALWAYS-CHOSEN: 両方が取るときは、いつも番のプレイヤーが先に取るプレイヤーを選ぶ。"""

    def assert_prize_first(self, state, remaining):
        self.assertEqual(check_invariants(state), [])
        d = state.decision
        self.assertEqual((d.kind, d.resume, d.player, d.options, state.phase), ("prize_first", "prize_first", state.current_player, (0, 1), Phase.DECISION))
        self.assertEqual(d.context_value("remaining"), remaining)
        self.assertIsNone(d.context_value("first"))
        self.assertEqual(takes(state), [])

    def test_all_face_down_legal(self):
        """合法な操作（seed 473。ロケット団参上!なし）: どのサイドもうらでも決定を出す（v0.139 までは出さずに番のプレイヤーから）。"""
        self.assert_prize_first(legal_double_knockout(rocket=False), (0, 1))

    def test_face_up_legal(self):
        self.assert_prize_first(legal_double_knockout(), (0, 1))

    def test_hand_revealed_legal(self):
        """合法な操作（seed 2）: ［おみとおし］で P0 の手札が見える（v0.139 の追加検証の FU-D1）。"""
        self.assert_prize_first(legal_omanyte_board(), (0, 1))

    def test_private_knowledge_boards(self):
        for spy in (None, "own", "opponent"):
            with self.subTest(spy=spy):
                self.assert_prize_first(knowledge_board(spy=spy), (0, 1))

    def test_partial_face_up_board(self):
        for owner in (0, 1):
            with self.subTest(owner=owner):
                self.assert_prize_first(apply_command(partial_board(reveal_owner=owner), UseAttack(0, SELFDESTRUCT)), (0, 1))

    def test_one_player_takes_no_decision(self):
        """一方だけが取るなら決定を出さない（相手のストライク HP 70 はじばくの 40 で残り、自分のコイルだけがきぜつ。P1 だけが取る）。おもてのサイドがあっても同じ。"""
        state = H.build_test_state([
            {"active": {"card": H.MAGNEMITE, "energy": [H.LIGHTNING, H.LIGHTNING]}, "bench": [H.MAGNEMITE], "prizes": 3, "deck": [H.LIGHTNING] * 5},
            {"active": H.SCYTHER, "bench": [H.RATTATA], "prizes": [H.WATER, H.RATTATA, H.LIGHTNING], "deck": [H.WATER] * 5},
        ])
        reveal_prize(state, 1, 0, trainer=0)
        state = apply_command(state, UseAttack(0, SELFDESTRUCT))
        d = state.decision
        self.assertEqual((d.kind, d.player, d.context_value("remaining"), d.context_value("first")), ("take_prize", 1, (), None))

    def test_rule_records(self):
        """利用者の指定の記録は 2 件だけ（対象を広げない）。公式の裁定ではないことを書く場所（文書）を持つ。"""
        self.assertEqual([r.id for r in USER_PRIZE_ORDER_RULES], ["USER-PRIZE-ORDER-ALWAYS-CHOSEN", "USER-PRIZE-ORDER-PER-PLAYER"])
        for rule in USER_PRIZE_ORDER_RULES:
            self.assertEqual(rule.specified_on, "2026-11-03")
            self.assertTrue(rule.statement and rule.scope and rule.document.startswith("docs/prize-order-user-rule-v0.140.md"))


class PerPlayerTest(unittest.TestCase):
    """USER-PRIZE-ORDER-PER-PLAYER: 先に選ばれたプレイヤーがその処理の分をすべて取ってから、もう一方が取る。"""

    def explore(self, start):
        """先に取るプレイヤーのどちらの答えでも、取り終えるまでの決定の並び（種類・決めるプレイヤー・先に取るプレイヤーの記録）と、取った順番。"""
        out = {}
        for first in start.decision.options:
            state, seen = answer(start, first), []
            while state.decision is not None and state.decision.kind in ("take_prize", "prize_first"):
                d = state.decision
                seen.append((d.kind, d.player, d.context_value("first")))
                self.assertIsNone(state.result)  # 取る途中では勝ち負けを決めない
                state = answer(state, 0)
            out[first] = (seen, takes(state), state)
        return out

    def test_two_against_one(self):
        start = units_board("2v1")
        self.assertEqual(start.decision.context_value("remaining"), (0, 0, 1))
        out = self.explore(start)
        self.assertEqual(out[0][0], [("take_prize", 0, 0), ("take_prize", 0, 0), ("take_prize", 1, 0)])
        self.assertEqual(out[1][0], [("take_prize", 1, 1), ("take_prize", 0, 1), ("take_prize", 0, 1)])
        self.assertEqual({k: v[1] for k, v in out.items()}, {0: [0, 0, 1], 1: [1, 0, 0]})  # 交互の 0, 1, 0 はない
        for _, _, state in out.values():
            self.assertEqual((state.decision.kind, state.decision.player), ("promote_active", 1))

    def test_two_against_two(self):
        out = self.explore(units_board("2v2"))
        self.assertEqual({k: v[1] for k, v in out.items()}, {0: [0, 0, 1, 1], 1: [1, 1, 0, 0]})
        self.assertTrue(all(kind == "take_prize" for seen, _, _ in out.values() for kind, _, _ in seen))  # 取ったあとに選び直さない

    def test_last_prize_mid_sequence_is_judged_after_all(self):
        """P1 のサイドが 1 枚（2v1-last）: P1 を先にすると P1 は途中で 0 枚になるが、P0 が取り終えるまで判定しない。どちらの順でも P1 の勝ち。"""
        out = self.explore(units_board("2v1-last"))
        self.assertEqual({k: (v[2].result.outcome, v[2].result.winner) for k, v in out.items()}, {0: ("win", 1), 1: ("win", 1)})

    def test_both_orders_reach_sudden_death(self):
        """両方が最後のサイドを同時に取る（サイド 1 枚ずつ。どのサイドもうら）: どちらの順でもサドン・デス（p.311・p.324）。"""
        start = apply_command(partial_board(reveal_owner=None, prizes=(1, 1)), UseAttack(0, SELFDESTRUCT))
        self.assertEqual((start.decision.kind, start.decision.player), ("prize_first", 0))
        out = self.explore(start)
        self.assertEqual({k: (v[2].phase, v[2].result.outcome) for k, v in out.items()}, {0: (Phase.SUDDEN_DEATH, "sudden_death"), 1: (Phase.SUDDEN_DEATH, "sudden_death")})

    def test_same_positions_give_the_same_board(self):
        """同じ位置を取れば、順番によらず場・手札・サイド・乱数は同じ（違うのはログの順番と決定の番号）。"""
        out = self.explore(units_board("2v2"))
        a, b = (state_to_dict(v[2], format_version=34) for v in out.values())
        for key in ("players", "phase", "turn_number", "current_player", "result", "rng_state_sha256"):
            self.assertEqual(a.get(key), b.get(key), key)


class OrderAndInformationTest(unittest.TestCase):
    """選べるサイドの位置（合法な候補）が同じでも、取る順番と決定の時点の情報で、選択と結果が変わりうる。今は番のプレイヤーがその順番を選べる。"""

    @staticmethod
    def pick_p1(state):
        """P1 の方策（反例のための例）: P0 の手札になにかの化石が見え、自分のサイドの位置 0 を知っていれば位置 0、そうでなければ最後の位置。"""
        view, log = observe(state, 1), visible_log(state, 1)
        hand = view["players"][0]["hand"]["cards"] or []
        knows = any(e["kind"] == "look_at_card" and e.get("owner") == 1 and e.get("position") == 0 for e in log)
        return 0 if knows and any(c["card_id"] == FOSSIL for c in hand) else state.decision.options[-1]

    def play(self, start, first):
        state = answer(start, first)
        record = {}
        while state.decision is not None and state.decision.kind == "take_prize":
            d = state.decision
            if d.player == 1:
                record["options"] = d.options
                record["seen"] = sorted(c["card_id"] for c in observe(state, 1)["players"][0]["hand"]["cards"] or [])
            state = answer(state, 0 if d.player == 0 else self.pick_p1(state))
        record["p1_took"] = cid(state, state.players[1].hand[-1])
        record["takes"] = takes(state)
        return record

    def test_choice_depends_on_order(self):
        start = knowledge_board(omanyte=True, spy="own")
        self.assertEqual(start.decision.kind, "prize_first")  # どのサイドもうらでも、番のプレイヤーが順番を選べる
        p0_first, p1_first = self.play(start, 0), self.play(start, 1)
        self.assertEqual((p0_first["takes"], p1_first["takes"]), ([0, 1], [1, 0]))
        self.assertEqual(p0_first["options"], p1_first["options"])  # 合法な候補は同じ
        self.assertIn(FOSSIL, p0_first["seen"])  # P0 が先なら、P0 の取ったうらのなにかの化石が P1 に見える（［おみとおし］）
        self.assertNotIn(FOSSIL, p1_first["seen"])
        self.assertEqual((p0_first["p1_took"], p1_first["p1_took"]), (CLEFAIRY_DOLL, H.WATER))  # 選択と結果が変わる

    def test_hand_revealed_legal_information(self):
        """合法な操作（seed 2）: P0 を先にすると、P1 の決定の時点に P0 の取ったカードが P1 と観戦者に見える（P1 を先にすると見えない）。"""
        start = legal_omanyte_board()
        counts = {}
        for first in (0, 1):
            state = answer(start, first)
            if first == 0:
                state = answer(state, 0)
            self.assertEqual((state.decision.kind, state.decision.player), ("take_prize", 1))
            counts[first] = (len(observe(state, 1)["players"][0]["hand"]["cards"]), len(observe(state, None)["players"][0]["hand"]["cards"]))
        self.assertEqual(counts[0][0] - counts[1][0], 1)
        self.assertEqual(counts[0][1] - counts[1][1], 1)


class PrizeFirstAnswerTest(unittest.TestCase):
    """決める人（番のプレイヤー）と選ぶ人（取るプレイヤー本人）の分離・観測・不正な答え・保存と復元。"""

    @classmethod
    def setUpClass(cls):
        cls.state = legal_double_knockout(rocket=False)

    def test_observation_has_no_hidden_information(self):
        state = self.state
        mine, theirs, spectator = observe(state, 0)["decision"], observe(state, 1)["decision"], observe(state, None)["decision"]
        self.assertEqual((mine["kind"], mine["player"], mine["options"], mine["meaning"]), ("prize_first", 0, [{"value": 0}, {"value": 1}], "number"))
        self.assertNotIn("options", theirs)
        self.assertNotIn("options", spectator)
        self.assertNotIn("card", json.dumps(mine))

    def test_takers_choose_their_own_prizes(self):
        for first in (0, 1):
            with self.subTest(first=first):
                state = answer(self.state, first)
                deciders = []
                while state.decision.kind == "take_prize":
                    deciders.append(state.decision.player)
                    state = answer(state, 0)
                self.assertEqual(deciders, [first, 1 - first])
                # 取ったあとの観測は今までの公開の規則のまま（うらのカードは取ったプレイヤーだけ。位置は書かない）
                seen = [e for e in visible_log(state, 1 - first) if e["kind"] == "take_prize" and e["player"] == first]
                self.assertEqual(len(seen), 1)
                self.assertNotIn("card", seen[0])
                self.assertNotIn("position", seen[0])

    def test_invalid_answers_change_nothing(self):
        state = self.state
        d = state.decision
        for command, code in ((ResolveDecision(1, d.id, (1,)), "NOT_YOUR_DECISION"), (ResolveDecision(0, d.id + 1, (0,)), "WRONG_DECISION"),
                              (ResolveDecision(0, d.id, (2,)), "INVALID_CHOICE"), (ResolveDecision(0, d.id, ()), "INVALID_CHOICE_COUNT"),
                              (ResolveDecision(0, d.id, (0, 1)), "INVALID_CHOICE_COUNT"), (TakePrize(0, 0), "WRONG_PHASE"), (EndTurn(0), "WRONG_PHASE")):
            with self.subTest(command=command):
                before = snapshot(state)
                with self.assertRaises(EngineError) as ctx:
                    apply_command(state, command)
                self.assertEqual(ctx.exception.code, code)
                self.assertEqual(snapshot(state), before)
        # 先に取るプレイヤーを選んだあと、もう一方が先に取ろうとしても受け付けない
        chosen = answer(state, 1)
        before = snapshot(chosen)
        with self.assertRaises(EngineError) as ctx:
            apply_command(chosen, ResolveDecision(0, chosen.decision.id, (0,)))
        self.assertEqual(ctx.exception.code, "NOT_YOUR_DECISION")
        self.assertEqual(snapshot(chosen), before)

    def test_save_and_restore_across_decisions(self):
        start = units_board("2v1")
        for first in (0, 1):
            with self.subTest(first=first):
                chosen = answer(start, first)
                mid = answer(chosen, 0)  # 先のプレイヤーが 1 枚取ったあと（まだ同じプレイヤーか、もう一方の番）
                for saved in (start, chosen, mid):
                    restored = pickle.loads(pickle.dumps(saved))
                    self.assertEqual(snapshot(restored), snapshot(saved))
                direct = take_all(chosen)
                via = take_all(answer(pickle.loads(pickle.dumps(start)), first))
                self.assertEqual(snapshot(direct), snapshot(via))
                self.assertEqual(rng_fingerprint(direct.rng), rng_fingerprint(start.rng))  # 順番の決定・サイドは乱数を使わない
        exported = state_to_dict(answer(start, 1), format_version=34)["decision"]  # 書き出し（形式 34 のまま）: 決定の context に先に取るプレイヤーの記録が加わる
        self.assertEqual(exported["kind"], "take_prize")
        self.assertIn('"first"', json.dumps(exported["context"]))
        self.assertEqual(state_to_dict(start, format_version=34)["decision"]["kind"], "prize_first")


# ================================================================ 不具合の修正（知らない再開先）


def with_decision(state, **changes):
    """比較用: 状態の写しの保留中の決定の項目だけを書きかえる（後の版・前の版の状態の写しを読んだ場合を作る）。"""
    fake = state.clone()
    fake.decision = dataclasses.replace(fake.decision, **changes)
    return fake


class UnsupportedDecisionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.take = legal_double_knockout(rocket=False)
        cls.take = answer(cls.take, 0)  # P0 の take_prize（先に取るプレイヤーの記録 first=0）

    def assert_unsupported(self, state, *, retired=False):
        before = snapshot(state)
        for viewer in (0, 1, None):
            with self.assertRaises(UnsupportedError) as ctx:
                observe(state, viewer)
            self.assertEqual(ctx.exception.code, DECISION_UNSUPPORTED_CODE)
        d = state.decision
        for command in (ResolveDecision(d.player, d.id, (d.options[0],)), TakePrize(d.player, 0), PromoteActive(d.player, 0), EndTurn(state.current_player)):
            with self.subTest(command=type(command).__name__):
                with self.assertRaises(UnsupportedError) as ctx:
                    apply_command(state, command)
                self.assertEqual(ctx.exception.code, DECISION_UNSUPPORTED_CODE)
                self.assertNotIn("future", str(ctx.exception))  # 状態の中の文字列をそのまま書かない
                self.assertEqual("v0.139" in str(ctx.exception), retired)
        self.assertEqual(snapshot(state), before)
        self.assertTrue(check_invariants(state))  # 診断の一覧は今までどおり問題を返す（例外にしない）

    def test_unknown_resume(self):
        self.assert_unsupported(with_decision(self.take, resume="future_resume"))

    def test_unknown_kind_and_resume(self):
        self.assert_unsupported(with_decision(self.take, kind="future_kind", resume="future_resume"))

    def test_retired_prize_order(self):
        """v0.139 の決定（種類・再開先 prize_order）。v0.139 の続きの情報の形（remaining・then・post_knockout）のまま。"""
        start = legal_double_knockout(rocket=False)
        old = with_decision(start, kind="prize_order", resume="prize_order")
        self.assertIn("prize_order", RETIRED_DECISIONS)
        self.assert_unsupported(old, retired=True)

    def test_after_save_and_restore(self):
        self.assert_unsupported(pickle.loads(pickle.dumps(with_decision(self.take, resume="future_resume"))))

    def test_known_resume_with_missing_information_is_integrity(self):
        """知っている再開先（take_prize）で、続けるのに要る情報が欠ける・合わない状態は StateIntegrityError（知らない再開先と取り違えない）。観測は作れる。"""
        start = legal_double_knockout(rocket=False)
        cases = {
            # 両方が取る並びで、先に取るプレイヤーの記録がない（v0.138・v0.139 の同時のきぜつの途中の形）
            "no_first": with_decision(start, kind="take_prize", resume="take_prize", options=tuple(range(len(start.players[0].prizes))),
                                      context=(("remaining", (1,)),)),
            # 先に取るプレイヤーの分をまとめていない
            "interleaved": with_decision(self.take, context=(("remaining", (1,)), ("first", 1))),
        }
        for name, state in cases.items():
            with self.subTest(case=name):
                state.phase = Phase.TAKE_PRIZE
                before = snapshot(state)
                observe(state, 0)
                d = state.decision
                with self.assertRaises(StateIntegrityError):
                    apply_command(state, ResolveDecision(d.player, d.id, (0,)))
                self.assertEqual(snapshot(state), before)

    def test_known_decisions_still_work(self):
        state = take_all(self.take)
        self.assertEqual(takes(state), [0, 1])
        observe(state, 0)


# ================================================================ 前の版の状態の写し（旧版の木・別のプロセス）

OLD_MAKER = r'''
import json, pickle, sys
tree = sys.argv[1]
sys.path.insert(0, tree)
import kyuura_engine
from kyuura_engine import AttachEnergy, EndTurn, PlayTrainer, ResolveDecision, UseAttack, apply_command, expand_decklist, new_game
from tests.helpers import finish_setup


def legal_double_knockout(rocket=True):
    # tests/test_prize_order_hc1_fix_v0_139.py の legal_double_knockout と同じ列（seed 473。v0.138 の木にはその file がないので、ここに写した）
    def card(state, player, card_id):
        return next(u for u in state.players[player].hand if state.cards[u].card_id == card_id)

    state = finish_setup(new_game(expand_decklist({"PMCG1-036": 4, "PMCG4-062": 4, "PMCG1-100": 52}), expand_decklist({"PMCG1-060": 4, "PMCG1-099": 56}), 473),
                         janken_winner=0)
    state = apply_command(apply_command(state, AttachEnergy(0, card(state, 0, "PMCG1-100"), state.players[0].active.card)), EndTurn(0))
    state = apply_command(state, EndTurn(1))
    state = apply_command(state, AttachEnergy(0, card(state, 0, "PMCG1-100"), state.players[0].active.card))
    if rocket:
        state = apply_command(state, PlayTrainer(0, card(state, 0, "PMCG4-062")))
    return apply_command(state, UseAttack(0, 1))


out = {"version": kyuura_engine.__version__}
plain = legal_double_knockout(rocket=False)
out["take_prize_both"] = pickle.dumps(plain).hex()  # 両方が取る並びのサイドの決定（先に取るプレイヤーの記録なし）
after = apply_command(plain, ResolveDecision(plain.decision.player, plain.decision.id, (0,)))
out["take_prize_last"] = pickle.dumps(after).hex()  # 残りが一方だけのサイドの決定
if kyuura_engine.__version__ == "0.139.0":
    out["prize_order"] = pickle.dumps(legal_double_knockout()).hex()
print(json.dumps(out))
'''


OLD_COMMITS = (("0.139.0", "789f58e2d5e60cf071f80b9d8411e329072744ba"), ("0.138.0", "4ded41817ef9a64ba07d3e0d2819d3b9cf06d318"))


class OldVersionStateTest(unittest.TestCase):
    """v0.139（789f58e）・v0.138（4ded418）の木で作った状態の写しを、この版で読む。この版で直せるのは、この版以降の扱いだけ（前の版のコードは変えない）。"""

    COMMITS = OLD_COMMITS

    @classmethod
    def setUpClass(cls):
        cls.made = {}
        with tempfile.TemporaryDirectory() as tmp:
            for version, commit in cls.COMMITS:
                data = subprocess.run(["git", "-C", str(ROOT), "archive", commit], check=True, capture_output=True).stdout
                tree = pathlib.Path(tmp) / version
                with tarfile.open(fileobj=io.BytesIO(data)) as tar:
                    tar.extractall(tree, filter="data")
                env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"} | {"PYTHONHASHSEED": "0", "PYTHONUTF8": "1"}
                proc = subprocess.run([sys.executable, "-P", "-s", "-X", "utf8", "-c", OLD_MAKER, str(tree)], capture_output=True, text=True, encoding="utf-8",
                                      env=env, check=False, cwd=tree)
                if proc.returncode != 0:
                    raise RuntimeError(proc.stderr[-2000:])
                cls.made[version] = json.loads(proc.stdout)

    def load(self, version, name):
        self.assertEqual(self.made[version]["version"], version)
        return pickle.loads(bytes.fromhex(self.made[version][name]))

    def test_v0139_prize_order_is_unsupported(self):
        state = self.load("0.139.0", "prize_order")
        self.assertEqual(state.decision.kind, "prize_order")
        UnsupportedDecisionTest.assert_unsupported(self, state, retired=True)

    def test_old_take_prize_with_both_players_is_integrity(self):
        for version, _ in self.COMMITS:
            with self.subTest(version=version):
                state = self.load(version, "take_prize_both")
                self.assertIsNone(state.decision.context_value("first"))
                before = snapshot(state)
                observe(state, 0)
                with self.assertRaises(StateIntegrityError):
                    apply_command(state, ResolveDecision(0, state.decision.id, (0,)))
                self.assertEqual(snapshot(state), before)

    def test_old_take_prize_with_one_player_continues(self):
        for version, _ in self.COMMITS:
            with self.subTest(version=version):
                state = self.load(version, "take_prize_last")
                self.assertEqual((state.decision.kind, state.decision.player, state.decision.context_value("remaining")), ("take_prize", 1, ()))
                after = answer(state, 0)
                self.assertEqual(after.decision.kind, "promote_active")


if __name__ == "__main__":
    unittest.main()
