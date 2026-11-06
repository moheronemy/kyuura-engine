"""v0.154（docs/replay-run-v0.154.md）: 完全な再現用記録の再実行と確認値の照合（U4）。

盤面の種類（docs 7 章）:
- new_game からの合法な操作の列を U3 の収集器で記録したもの: ピカチュウのデッキの方策（seed 9 はサドン・デスから延長戦、seed 0 は終局。拒否を混ぜたもの・省いたもの）、
  たねポケモン 1 枚のデッキ（seed 1 は準備で停止）、ファイヤー（ES2-005）対ラッキー（seed 0 はドライアップの答えを受理した結果として途中停止。seed は 0〜15 に限って探した）、
  3 つの規約集合
- 記録を書きかえる確かめ（U3 の構造の検証で拒否するものと、構造は通り U4 の再実行で不一致になるものを分ける）
- 例外を差し込む確かめ（記録された失敗・再実行の内部エラー）
停止コードの文字列はテストの中に書かない。
"""

from __future__ import annotations

import copy
import json
import os
import pathlib
import subprocess
import sys
import unittest
from unittest import mock

from kyuura_engine import (
    AttachEnergy,
    EndTurn,
    ResolveDecision,
    UseAttack,
    apply_command,
)
from kyuura_engine import adapter as A
from kyuura_engine import conventions as C
from kyuura_engine import diagnostics as D
from kyuura_engine import replay_record as R
from kyuura_engine import replay_run as RR
from kyuura_engine.state import Phase
from tests import helpers as H
from tests.test_replay_record_v0_153 import DECKS, HALT_DECK, drive

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "replay-run-v0.154.md"
U3_DOC = ROOT / "docs" / "replay-record-v0.153.md"
SPEC = ROOT / "docs" / "diagnostics-replay-api-design.json"
SETS = (None, "CS-KYUURA-PLAY-S2A@1", "CS-KYUURA-PLAY-PO@1")
DRY_MOLTRES = "ES2-005"  # ファイヤー（ドライアップ）
DRY_DECKS = ([DRY_MOLTRES] * 4 + [H.FIRE] * 56, [H.CHANSEY] * 4 + [H.WATER] * 56)


def dry_command(state):
    """ファイヤーはエネルギーをつけてドライアップ（相手のバトル場を選ぶ）、ラッキーはエネルギーをつけて番を終える（決まった手順。乱数を使わない）。"""
    if state.phase in (Phase.SETUP_PLACEMENT, Phase.SETUP_MULLIGAN_DRAW, Phase.SETUP_FIRST_PLAYER):
        return H.trainer_policy_command(state, janken_winner=0)
    d = state.decision
    if d is not None:
        if d.player == 0 and state.players[1].active is not None and state.players[1].active.pokemon_id in d.options:
            return ResolveDecision(0, d.id, (state.players[1].active.pokemon_id,))
        return H.trainer_policy_command(state, janken_winner=0)
    player = state.current_player
    p = state.players[player]
    energy = H.FIRE if player == 0 else H.WATER
    if state.energy_attachments_this_turn == 0 and p.active is not None:
        cards = [u for u in p.hand if state.cards[u].card_id == energy]
        if cards:
            return AttachEnergy(player, cards[0], p.active.card)
    if player == 0 and p.active is not None and len(p.active.energy) >= 2 and state.turn_number > 1:
        return UseAttack(0, 0)
    return EndTurn(player)


def dry_up_halt():
    collector, _ = R.ReplayCollector.start(*DRY_DECKS, 0, include_git=False)
    for _ in range(100):
        if collector.state.phase is Phase.HALTED:
            break
        result = collector.submit(dry_command(collector.state))
        assert result.outcome == D.ACCEPTED
    return collector


def until_decision(seed=9):
    collector, _ = R.ReplayCollector.start(*DECKS, seed, include_git=False)
    while collector.state.decision is None:
        collector.submit(H.trainer_policy_command(collector.state, janken_winner=seed % 2))
    return collector


def halted_start():
    collector, _ = R.ReplayCollector.start(HALT_DECK, HALT_DECK, 1, include_git=False)
    collector.submit(EndTurn(0), submitter=0)
    return collector


def setUpModule():
    global SD, SD_PLAIN, OVER, HALT_OP, HALT_START, DECISION
    SD = drive(9, probe=True).close()
    SD_PLAIN = drive(9, record_rejections=False, probe=True).close()
    OVER = drive(0).close()
    HALT_OP = dry_up_halt().close()
    HALT_START = halted_start().close()
    DECISION = until_decision().close()


def edited(record, edit):
    data = copy.deepcopy(record.data)
    edit(data)
    return data


def first(data, outcome, *, after=0, kind=None):
    return next(o for o in data["operations"] if o["outcome"] == outcome and o["seq"] > after and (kind is None or o["command"]["type"] == kind))


class SuccessTest(unittest.TestCase):
    def assertSucceeded(self, record):
        report = RR.replay(record)
        self.assertEqual(report.status, RR.SUCCEEDED, report)
        ops = record.data["operations"]
        self.assertEqual((report.executed, report.start_verified, report.end_verified, report.mismatch), (True, True, True, None))
        self.assertEqual((report.verified_seq, report.verified_accepted), (len(ops), sum(o["outcome"] == D.ACCEPTED for o in ops)))
        return report

    def test_collected_records_replay(self):
        for name, record in (("サドン・デスと延長戦・拒否あり", SD), ("拒否を省いた", SD_PLAIN), ("終局", OVER), ("受理後の途中停止", HALT_OP),
                             ("開始時の停止", HALT_START), ("決定待ちで閉じた", DECISION)):
            with self.subTest(name):
                self.assertSucceeded(record)

    def test_fixture_kinds(self):
        self.assertEqual(SD.data["end"]["segments"][1]["index"], 1)
        self.assertEqual(OVER.data["end"]["status"], D.GAME_OVER)
        last = HALT_OP.data["operations"][-1]
        self.assertEqual((last["outcome"], last["check"]["status"], last["command"]["type"]), (D.ACCEPTED, D.HALTED, "resolve_decision"))
        self.assertIsNotNone(last["check"]["halt"])
        self.assertEqual(HALT_START.data["header"]["start"]["check"]["status"], D.HALTED)
        self.assertEqual(DECISION.data["end"]["status"], D.AWAITING_DECISION)
        self.assertTrue(any(o["outcome"] == D.REJECTED for o in SD.data["operations"]))
        self.assertTrue(any("answers_decision" in o for o in SD.data["operations"]))

    def test_three_convention_sets(self):
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                collector, _ = R.ReplayCollector.start(*DECKS, 5, conventions=conventions, include_git=False)
                for _ in range(40):
                    if collector.state.phase in (Phase.GAME_OVER, Phase.HALTED, Phase.SUDDEN_DEATH):
                        break
                    collector.submit(H.trainer_policy_command(collector.state, janken_winner=1))
                record = collector.close()
                key = C.parse_key(conventions) if conventions else C.DEFAULT_SET
                self.assertEqual(record.data["header"]["convention_set"], C.registered_identity(key).record())
                self.assertSucceeded(record)

    def test_json_round_trip_then_replay(self):
        self.assertSucceeded(R.loads_record(R.dumps_record(SD)))


class OrderTest(unittest.TestCase):
    """記録の行を seq の順に送る（受理だけを先に送らない）。拒否を省いた記録も同じ受理の列で再現する。"""

    def test_seq_order(self):
        sent = []
        real = RR.submit

        def spy(state, command, **kw):
            sent.append(kw.get("operation_id"))
            return real(state, command, **kw)
        with mock.patch.object(RR, "submit", spy):
            self.assertEqual(RR.replay(SD).status, RR.SUCCEEDED)
        self.assertEqual(sent, [o["operation_id"] for o in SD.data["operations"]])

    def test_moved_rejection_is_detected(self):
        # 決定に違う id で答えた拒否の行を、そのあとの受理の行と入れかえる（seq と accepted_index は付け直す）: 構造は通るが、拒否の行で状態の status が違う
        def edit(d):
            ops = d["operations"]
            i = next(k for k, o in enumerate(ops) if o["outcome"] == D.REJECTED and str(o["operation_id"]).startswith("wrong-"))
            j = i + 1
            while ops[j]["outcome"] != D.ACCEPTED:
                j += 1
            ops[i], ops[j] = ops[j], ops[i]
            for k, o in enumerate(ops, 1):
                o["seq"] = k
            ops[i]["status"], ops[j]["status"] = ops[i]["check"]["status"], ops[i]["status"]
        data = edited(SD, edit)
        report = RR.replay(data)
        self.assertIn(report.status, (RR.DIVERGED, RR.INVALID_RECORD), report)
        self.assertFalse(report.succeeded)

    def test_rejection_turned_into_acceptable_command(self):
        # 拒否の行のコマンドを、受理されるコマンド（番のプレイヤーの番の終わり）に変える: 構造は通り、再実行で outcome が違う
        def edit(d):
            op = first(d, D.REJECTED, kind="end_turn")
            op["command"]["player"] = 1 - op["command"]["player"]
            op["submitter"] = op["command"]["player"]
        data = edited(SD, edit)
        self.assertEqual(R.validate_record(data).status, R.STRUCTURE_VALID)
        report = RR.replay(data)
        self.assertEqual((report.status, report.mismatch.location, report.mismatch.items[0]), (RR.DIVERGED, RR.LOCATION_OPERATION, "outcome"))
        self.assertEqual(report.verified_seq, first(data, D.REJECTED, kind="end_turn")["seq"] - 1)


def swap_first_and_last_card(d):
    """デッキリストの最初と最後のカードを入れかえる（同じカードの組のまま。カードの uid の付け方が変わる）。"""
    deck = d["header"]["initial"]["decklists"][0]
    deck[0], deck[-1] = deck[-1], deck[0]


class DetectionTest(unittest.TestCase):
    """書きかえた記録: U3 の構造の検証で拒否するもの（再実行しない）と、構造は通り U4 の再実行で不一致になるもの。"""

    def run_edit(self, record, edit):
        data = edited(record, edit)
        return R.validate_record(data), RR.replay(data)

    def test_structure_errors_are_not_executed(self):
        with mock.patch.object(RR, "start_game", side_effect=AssertionError("対戦を作った")):
            for edit in (lambda d: d["operations"].pop(3), lambda d: d["header"]["initial"].pop("seed"), lambda d: d["end"].update(accepted=0)):
                structure, report = self.run_edit(SD, edit)
                self.assertIn(structure.status, (R.MALFORMED, R.INCONSISTENT))
                self.assertEqual((report.status, report.executed), (RR.INVALID_RECORD, False))

    def test_initial_conditions_diverge_at_start(self):
        for edit in (lambda d: d["header"]["initial"].update(seed=10),
                     swap_first_and_last_card):
            structure, report = self.run_edit(SD, edit)
            self.assertEqual(structure.status, R.STRUCTURE_VALID)
            self.assertEqual((report.status, report.mismatch.location, report.start_verified), (RR.DIVERGED, RR.LOCATION_START, False))
            self.assertIn("state", report.mismatch.items)

    def test_check_values_diverge_at_the_operation(self):
        target = first(SD.data, D.ACCEPTED, after=30)
        for item, value in (("rng", "0" * 64), ("state", "1" * 64), ("log_length", target["check"]["log_length"] + 1)):
            with self.subTest(item):
                structure, report = self.run_edit(SD, lambda d, i=item, v=value: next(o for o in d["operations"] if o["seq"] == target["seq"])["check"].update({i: v}))
                self.assertEqual(structure.status, R.STRUCTURE_VALID)
                self.assertEqual((report.status, report.mismatch.location, report.mismatch.seq, report.mismatch.accepted_index, report.mismatch.items),
                                 (RR.DIVERGED, RR.LOCATION_OPERATION, target["seq"], target["accepted_index"], (item,)))
                self.assertEqual((report.verified_seq, report.verified_accepted), (target["seq"] - 1, target["accepted_index"] - 1))

    def test_changed_command_and_diagnostic(self):
        attack = first(SD.data, D.ACCEPTED, kind="use_attack")
        structure, report = self.run_edit(SD, lambda d: next(o for o in d["operations"] if o["seq"] == attack["seq"])["command"].update(
            attack_index=1 - attack["command"]["attack_index"]))
        self.assertEqual(structure.status, R.STRUCTURE_VALID)
        self.assertEqual((report.status, report.mismatch.seq), (RR.DIVERGED, attack["seq"]))
        rejected = first(SD.data, D.REJECTED)
        structure, report = self.run_edit(SD, lambda d: next(o for o in d["operations"] if o["seq"] == rejected["seq"])["diagnostic"].update(engine_code="NOT_A_REAL_CODE_FOR_TEST"))
        self.assertEqual(structure.status, R.STRUCTURE_VALID)
        self.assertEqual((report.status, report.mismatch.items), (RR.DIVERGED, ("engine_code",)))

    def test_unsupported_is_not_executed(self):
        with mock.patch.object(RR, "start_game", side_effect=AssertionError("対戦を作った")):
            for edit in (lambda d: d["header"]["engine"].update(behavior_digest="0" * 64), lambda d: d["header"]["runtime"]["python_version"].__setitem__(1, 0),
                         lambda d: d["header"]["convention_set"].update(digest="sha256:" + "0" * 64), lambda d: d.update(kyuura_replay_format=2)):
                _, report = self.run_edit(SD, edit)
                self.assertEqual((report.status, report.executed), (RR.NOT_SUPPORTED, False))

    def test_pending_moves_outside_the_check_are_reported(self):
        real = RR.submit

        def leaky(state, command, **kw):
            result = real(state, command, **kw)
            if result.outcome == D.ACCEPTED and kw.get("operation_id") == "op-40":
                result.state.pending_moves = (("same", "moved", (), ()),)
            return result
        with mock.patch.object(RR, "submit", leaky):
            report = RR.replay(SD)
        self.assertEqual((report.status, report.mismatch.items), (RR.DIVERGED, ("pending_moves",)))


class IncompleteAndFailureTest(unittest.TestCase):
    def test_incomplete_records_are_not_success(self):
        collector = drive(9, probe=True, max_steps=60)
        report = RR.replay(collector.record())
        self.assertEqual((report.status, report.succeeded, report.end_verified), (RR.INCOMPLETE, False, False))
        self.assertEqual(report.verified_seq, len(collector.record().data["operations"]))
        cut = edited(SD, lambda d: (d["operations"].__delitem__(slice(50, None)), d.update(end=None)))
        report = RR.replay(cut)
        self.assertEqual((report.status, report.verified_seq), (RR.INCOMPLETE, 50))

    def aborted(self):
        collector, _ = R.ReplayCollector.start(*DECKS, 9, include_git=False)
        for _ in range(8):
            collector.submit(H.trainer_policy_command(collector.state, janken_winner=1))

        def boom(state, command):
            raise RuntimeError("secret 5150")
        with mock.patch.object(A, "apply_command", boom):
            collector.submit(H.trainer_policy_command(collector.state, janken_winner=1))
        return collector.close(), boom

    def test_aborted_records_are_not_success(self):
        record, _ = self.aborted()
        report = RR.replay(record)  # 失敗が起きない（同じ操作が受理される）: 記録と違う
        self.assertEqual((report.status, report.mismatch.items), (RR.DIVERGED, ("outcome",)))
        calls = {"n": 0}
        real = A.apply_command

        def fail_ninth(state, command):
            calls["n"] += 1
            if calls["n"] == 9:
                raise RuntimeError("again")
            return real(state, command)
        with mock.patch.object(A, "apply_command", fail_ninth):
            report = RR.replay(record)  # 同じ行で同じ失敗がもう一度起きた: 失敗を含む結果（成功ではない）
        self.assertEqual((report.status, report.succeeded, report.verified_seq), (RR.RECORDED_FAILURE, False, 9))
        self.assertIn("RuntimeError", report.failure.traceback)

    def test_unexpected_internal_error(self):
        calls = {"n": 0}
        real = A.apply_command

        def fail_later(state, command):
            calls["n"] += 1
            if calls["n"] == 20:
                raise RuntimeError("secret 6060")
            return real(state, command)
        with mock.patch.object(A, "apply_command", fail_later):
            report = RR.replay(SD)
        self.assertEqual(report.status, RR.INTERNAL_ERROR)
        self.assertIn("6060", report.failure.raw_message)
        self.assertNotIn("6060", repr(report))

    def test_errors_inside_the_runner_are_internal_errors(self):
        with mock.patch.object(RR, "checks", side_effect=ValueError("boom")):
            report = RR.replay(SD)
        self.assertEqual((report.status, report.failure.exception_type), (RR.INTERNAL_ERROR, "ValueError"))
        for error in (KeyboardInterrupt(), SystemExit(1), MemoryError()):
            with self.subTest(type(error).__name__), mock.patch.object(RR, "checks", side_effect=error), self.assertRaises(type(error)):
                RR.replay(SD)


class HashSeedTest(unittest.TestCase):
    """同じ小さな固定記録を、PYTHONHASHSEED の違う別プロセスで作り、再実行する。"""

    SCRIPT = ("import sys; sys.path.insert(0, {root!r});"
              "from tests.test_replay_record_v0_153 import drive;"
              "from kyuura_engine import replay_record as R, replay_run as RR;"
              "rec = drive(9, probe=True, max_steps=70).close();"
              "text = R.dumps_record(rec).replace(rec.data['header']['engine'].get('git_commit') or '', '');"
              "print(RR.replay(R.loads_record(sys.stdin.read())).status if {replay} else text, end='')")

    def run_with(self, seed, *, replay=False, stdin=""):
        env = dict(os.environ, PYTHONHASHSEED=str(seed), PYTHONUTF8="1")
        done = subprocess.run([sys.executable, "-c", self.SCRIPT.format(root=str(ROOT), replay=replay)], input=stdin, capture_output=True, text=True,
                              encoding="utf-8", env=env, timeout=600, check=False)
        self.assertEqual(done.returncode, 0, done.stderr[-2000:])
        return done.stdout

    def test_records_and_replay_do_not_depend_on_hash_seed(self):
        texts = {seed: self.run_with(seed) for seed in (0, 1, 4242)}
        self.assertEqual(len(set(texts.values())), 1)
        record = R.loads_record(texts[0])
        self.assertEqual(R.validate_record(record).status, R.STRUCTURE_VALID)
        self.assertEqual(self.run_with(77, replay=True, stdin=texts[0]), RR.SUCCEEDED)


class BoundaryTest(unittest.TestCase):
    def test_reports_do_not_print_secrets(self):
        data = edited(SD, lambda d: first(d, D.ACCEPTED, after=30)["check"].update(rng="0" * 64))
        report = RR.replay(data)
        text = repr(report)
        self.assertNotIn("0" * 64, text)  # 確認値（記録の値・再実行の値）を repr に出さない
        self.assertNotIn(first(SD.data, D.ACCEPTED, after=30)["check"]["rng"], text)
        self.assertNotIn("decklists", text)
        self.assertNotIn(SD.data["header"]["initial"]["decklists"][0][0], text)

    def test_engine_api_unchanged(self):
        state = apply_command(R.ReplayCollector.start(*DECKS, 3, include_git=False)[0].state, H.trainer_policy_command(
            R.ReplayCollector.start(*DECKS, 3, include_git=False)[0].state, janken_winner=1))
        self.assertEqual(type(state).__name__, "GameState")
        import kyuura_engine
        self.assertNotIn("replay", kyuura_engine.__all__)


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("replay(", "succeeded", "recorded_failure", "incomplete", "diverged", "pending_moves", "PYTHONHASHSEED", "seq"):
            self.assertIn(needle, text)

    def test_u3_document_correction(self):
        text = U3_DOC.read_text(encoding="utf-8")
        self.assertIn("v0.154 の訂正", text)

    def test_spec(self):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        units = {u["id"]: u["status"] for u in spec["units"]}
        self.assertEqual((units["U4"], units["U5"], units["U6"], units["U7"]), ("implemented", "planned", "planned", "planned"))
        status = {d["id"]: d["status"] for d in spec["decisions"]}
        self.assertEqual((status["D-SNAPSHOT-BASE"], status["D-HALT-SNAPSHOT"]), ("pending", "pending"))
        self.assertIn("recorded_failure", {r["id"] for r in spec["replay_results"]})


if __name__ == "__main__":
    unittest.main()
