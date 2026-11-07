"""v0.158（docs/state-snapshot-v0.158.md）: 完全な再現用記録とスナップショットの接続（U6-S5）。

盤面の種類:
- new_game からの合法な操作の列を U3 の収集器で記録し、各行の直後の状態を保存したもの（ピカチュウのデッキの方策。seed 9 はサドン・デスから延長戦・拒否を混ぜたもの・
  省いたもの、seed 0 は終局。ファイヤー対ラッキーの seed 0 はドライアップの答えを受理した結果の途中停止、たねポケモン 1 枚のデッキの seed 1 は準備で停止。3 つの規約集合）
- 構築盤面（tests.helpers.build_test_state）は保存できても、new_game から始まる記録にはつながらないことだけを確かめる
- 記録・スナップショットを書きかえる確かめ・例外を差し込む確かめ
停止コードの文字列はテストの中に書かない。
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import unittest
from types import MappingProxyType
from unittest import mock

from kyuura_engine import EndTurn, ResolveDecision, StartSuddenDeath
from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import replay_record as R
from kyuura_engine import replay_run as RR
from kyuura_engine import snapshot as SN
from kyuura_engine import snapshot_replay as SR
from kyuura_engine.commands import command_from_dict
from kyuura_engine.state import Phase
from tests import helpers as H
from tests.test_replay_record_v0_153 import DECKS, HALT_DECK
from tests.test_replay_run_v0_154 import DRY_DECKS, dry_command

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "state-snapshot-v0.158.md"
SETS = (None, "CS-KYUURA-PLAY-S2A@1", "CS-KYUURA-PLAY-PO@1")


class InjectedError(Exception):
    """テストが差し込む想定外の例外。"""


@dataclasses.dataclass
class Collected:
    record: R.ReplayRecord
    snaps: dict  # seq → その行の直後（0 は開始の直後）の状態のスナップショット
    final: object  # 収集を終えたときの状態（保存しないで続けた状態）


def submitter(command):
    player = getattr(command, "player", None)
    return player if player in (0, 1) else None


def collect(seed, *, decks=DECKS, conventions=None, record_rejections=True, probe=True, connection_checks=False, max_steps=6000, max_segments=2,
            close=True, game_id=None):
    """収集器でピカチュウの方策の操作を送り、各行の直後の状態を保存する（origin に game_id・seq）。``probe`` なら、ときどき拒否される操作を送る。"""
    game_id = game_id or f"pikachu-{seed}"
    collector, start = R.ReplayCollector.start(*decks, seed, conventions=conventions, game_id=game_id, record_rejections=record_rejections,
                                               include_git=False, connection_checks=connection_checks)
    assert start.outcome == D.ACCEPTED
    snaps = {0: SN.save_snapshot(collector.state, origin={"game_id": game_id, "seq": 0})}

    def send(command, sub=None):
        result = collector.submit(command, submitter=sub)
        seq = len(collector.record().data["operations"])
        if seq not in snaps:
            snaps[seq] = SN.save_snapshot(collector.state, origin={"game_id": game_id, "seq": seq})
        return result

    segments = 1
    for step in range(max_steps):
        state = collector.state
        if state.phase in (Phase.GAME_OVER, Phase.HALTED) or (state.phase == Phase.SUDDEN_DEATH and segments >= max_segments):
            break
        if state.phase == Phase.SUDDEN_DEATH:
            send(StartSuddenDeath())
            segments += 1
            continue
        if probe and step % 17 == 5 and state.phase == Phase.MAIN:
            send(EndTurn(1 - state.current_player), 1 - state.current_player)
        if probe and step % 13 == 3 and state.decision is not None:
            d = state.decision
            send(ResolveDecision(d.player, d.id + 7, d.options[:d.min_choices]), d.player)
        command = H.trainer_policy_command(state, janken_winner=seed % 2)
        assert send(command, submitter(command)).outcome == D.ACCEPTED
    return Collected(collector.close() if close else collector.record(), snaps, collector.state)


def dry_halt():
    """ドライアップの答えを受理した結果として途中停止し、そのあと拒否される操作を 2 つ送る。"""
    collector, _ = R.ReplayCollector.start(*DRY_DECKS, 0, game_id="dry", include_git=False, connection_checks=True)
    snaps = {0: SN.save_snapshot(collector.state)}
    for _ in range(100):
        if collector.state.phase is Phase.HALTED:
            break
        assert collector.submit(dry_command(collector.state)).outcome == D.ACCEPTED
        snaps[len(collector.record().data["operations"])] = SN.save_snapshot(collector.state)
    for player in (0, 1):
        assert collector.submit(EndTurn(player), submitter=player).outcome == D.REJECTED
        snaps[len(collector.record().data["operations"])] = SN.save_snapshot(collector.state)
    return Collected(collector.close(), snaps, collector.state)


def halted_start():
    collector, _ = R.ReplayCollector.start(HALT_DECK, HALT_DECK, 1, include_git=False)
    snaps = {0: SN.save_snapshot(collector.state)}
    collector.submit(EndTurn(0), submitter=0)
    snaps[1] = SN.save_snapshot(collector.state)
    return Collected(collector.close(), snaps, collector.state)


def setUpModule():
    global SD, SD_PLAIN, OVER, HALT, HALT_START
    SD = collect(9, connection_checks=True)
    SD_PLAIN = collect(9, record_rejections=False)
    OVER = collect(0)
    HALT = dry_halt()
    HALT_START = halted_start()


def ops(c):
    return c.record.data["operations"]


def first_seq(c, test):
    return next(o["seq"] for o in ops(c) if test(o))


def at(seq):
    return SR.RecordPosition.initial() if seq == 0 else SR.RecordPosition.after(seq)


def edited(record, edit):
    data = copy.deepcopy(record.data if isinstance(record, R.ReplayRecord) else record)
    edit(data)
    return data


def rebuilt(snapshot, change):
    """スナップショットを復元した状態を ``change`` で変え、保存し直す（自己確認値 check は変えた状態から作り直される）。"""
    report = SN.restore_snapshot(snapshot)
    assert report.restored
    return SN.save_snapshot(change(report.state))


class ConnectTest(unittest.TestCase):
    def assertWhole(self, c, seq, **kw):
        report = SR.replay_from_snapshot(c.record, c.snaps[seq], at(seq), **kw)
        self.assertEqual((report.status, report.scope, report.replay_verified), (SR.SUCCEEDED, SR.SCOPE_WHOLE_RECORD, True), report)
        self.assertEqual((report.verified_from, report.verified_seq, report.start_verified, report.end_verified), (0, len(ops(c)), True, True))
        self.assertIn(SR.BASIS_PREFIX, report.connection_basis)
        self.assertIsNone(report.mismatch)
        return report

    def test_initial_snapshot_replays_every_operation(self):
        self.assertWhole(SD, 0)
        self.assertWhole(OVER, 0)

    def test_after_an_accepted_operation(self):
        seq = first_seq(SD, lambda o: o["outcome"] == D.ACCEPTED and o["seq"] > 40)
        self.assertWhole(SD, seq)
        report = SR.replay_from_snapshot(SD.record, SN.dumps_snapshot(SD.snaps[seq]), at(seq), replay_prefix=False)  # JSON の文字列からも
        self.assertEqual((report.status, report.scope, report.replay_verified, report.suffix_verified), (SR.SUCCEEDED, SR.SCOPE_FROM_CONNECTION, False, True))
        self.assertEqual((report.connection_basis, report.prefix_replayed, report.verified_from, report.start_verified), ((SR.BASIS_CONNECTION_CHECK,), False, seq, False))

    def test_after_a_rejected_operation(self):
        seq = first_seq(SD, lambda o: o["outcome"] == D.REJECTED and o["seq"] > 20)
        accepted_before = max(o["seq"] for o in ops(SD)[:seq] if o["outcome"] == D.ACCEPTED)
        # 拒否は状態を変えないので、直前の受理の行の直後と同じ状態。位置は別（残りは seq+1 から）
        self.assertEqual(SD.snaps[seq].data["state"], SD.snaps[accepted_before].data["state"])
        self.assertWhole(SD, seq)
        self.assertWhole(SD, accepted_before)
        # origin の seq は位置と照らす（同じ状態でも、拒否の行の直後として保存したものを直前の受理の位置にはつながない）
        report = SR.replay_from_snapshot(SD.record, SD.snaps[seq], at(accepted_before))
        self.assertEqual((report.status, report.mismatch.items), (SR.CONNECTION_MISMATCH, ("origin.seq",)))
        plain = rebuilt(SD.snaps[seq], lambda s: s)  # origin のないスナップショットは、どちらの位置にもつながる
        for position in (seq, accepted_before):
            self.assertEqual(SR.replay_from_snapshot(SD.record, plain, at(position)).status, SR.SUCCEEDED)

    def test_awaiting_decision_then_answer(self):
        seq = first_seq(SD, lambda o: o["outcome"] == D.ACCEPTED and o["status"] == D.AWAITING_DECISION)
        answer = next(o for o in ops(SD)[seq:] if o["outcome"] == D.ACCEPTED)
        self.assertIn(answer["command"]["type"], R.ANSWER_COMMANDS)  # 残りの最初の受理の行が、その決定への答え
        self.assertWhole(SD, seq)
        self.assertEqual(SR.replay_from_snapshot(SD.record, SD.snaps[seq], at(seq), replay_prefix=False).status, SR.SUCCEEDED)

    def test_halt_after_an_accepted_answer(self):
        halted = first_seq(HALT, lambda o: o["outcome"] == D.ACCEPTED and o["status"] == D.HALTED)
        self.assertEqual(ops(HALT)[-1]["outcome"], D.REJECTED)  # 停止のあとの操作は拒否のまま
        for seq in (halted, len(ops(HALT))):
            self.assertWhole(HALT, seq)
            report = SR.replay_from_snapshot(HALT.record, HALT.snaps[seq], at(seq), replay_prefix=False)
            self.assertEqual(report.status, SR.SUCCEEDED)
        restored = SN.restore_snapshot(HALT.snaps[halted]).state
        self.assertEqual((restored.phase, D.status_of(restored)), (Phase.HALTED, D.HALTED))

    def test_halted_from_the_start(self):
        self.assertEqual(HALT_START.record.data["header"]["start"]["status"], D.HALTED)
        self.assertWhole(HALT_START, 0)
        self.assertWhole(HALT_START, 1)
        # 拡張のない記録で前半を再実行しなければ、検証済みとして続けない
        report = SR.replay_from_snapshot(HALT_START.record, HALT_START.snaps[0], at(0), replay_prefix=False)
        self.assertEqual((report.status, report.scope, [p.code for p in report.problems]), (SR.NOT_SUPPORTED, None, ["connection_check_absent"]))

    def test_game_over_closed_record(self):
        self.assertEqual(OVER.record.data["end"]["status"], D.GAME_OVER)
        self.assertWhole(OVER, len(ops(OVER)))
        self.assertWhole(OVER, len(ops(OVER)) // 2)

    def test_sudden_death_and_segments(self):
        pending = first_seq(SD, lambda o: o["outcome"] == D.ACCEPTED and o["status"] == D.SUDDEN_DEATH_PENDING)
        started = first_seq(SD, lambda o: o["command"]["type"] == "start_sudden_death")
        self.assertEqual(started, pending + 1)
        later = first_seq(SD, lambda o: o["outcome"] == D.ACCEPTED and o["seq"] > (started + len(ops(SD))) // 2)  # 延長戦の区間の途中
        for seq in (pending, started, later):
            with self.subTest(seq=seq):
                self.assertWhole(SD, seq)
                self.assertEqual(SR.replay_from_snapshot(SD.record, SD.snaps[seq], at(seq), replay_prefix=False).status, SR.SUCCEEDED)
        self.assertEqual(SN.restore_snapshot(SD.snaps[later]).state.segment_index, 1)
        self.assertEqual(len(SN.restore_snapshot(SD.snaps[later]).state.segments), 1)
        # 区間 0 の状態を区間 1 の位置へつなぐと、区間の番号ごと違う
        report = SR.replay_from_snapshot(SD.record, rebuilt(SD.snaps[pending], lambda s: s), at(later))
        self.assertEqual(report.status, SR.CONNECTION_MISMATCH)
        self.assertIn("check.segment", report.mismatch.items)

    def test_records_with_and_without_rejections(self):
        self.assertFalse(any(o["outcome"] == D.REJECTED for o in ops(SD_PLAIN)))
        self.assertTrue(any(o["outcome"] == D.REJECTED for o in ops(SD)))
        n = len(ops(SD_PLAIN))
        for seq in (0, n // 3, n):
            self.assertWhole(SD_PLAIN, seq)
        # 同じ対戦でも、拒否を記録したかで seq が違う別の記録（記録の識別も違う）
        self.assertNotEqual(SR.record_identity(SD.record), SR.record_identity(SD_PLAIN.record))

    def test_three_convention_sets(self):
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                c = collect(5, conventions=conventions, connection_checks=True, max_steps=120)
                seq = len(ops(c)) // 2
                self.assertWhole(c, seq)
                self.assertEqual(SR.replay_from_snapshot(c.record, c.snaps[seq], at(seq), replay_prefix=False).status, SR.SUCCEEDED)
                other = next(s for s in SETS if s != conventions)
                d = collect(5, conventions=other, max_steps=10, probe=False)  # 別の規約集合の同じ対戦の状態はつながない
                report = SR.replay_from_snapshot(c.record, d.snaps[0], at(0))
                self.assertEqual(report.status, SR.CONNECTION_MISMATCH)
                self.assertIn("convention_set", report.mismatch.items)

    def test_three_ways_agree(self):
        # 保存しないで続けた状態・復元して記録の残りを送った状態・最初から U4 で再実行した状態が同じ
        seq = len(ops(SD)) // 2
        restored = SN.RestoredGame(SN.restore_snapshot(SD.snaps[seq]))
        for op in ops(SD)[seq:]:
            restored.submit(command_from_dict(dict(op["command"])), submitter=op["submitter"], operation_id=op["operation_id"])
        replayed = []
        self.assertEqual(RR.replay(SD.record, observer=replayed.append).status, RR.SUCCEEDED)
        final_u4 = next(r.state for r in reversed(replayed) if r.outcome == D.ACCEPTED)
        items = [SN.state_items(s) for s in (SD.final, restored.state, final_u4)]
        self.assertEqual(items[0], items[1])
        self.assertEqual(items[0], items[2])
        self.assertEqual(len({SN.connection_check(s) for s in (SD.final, restored.state, final_u4)}), 1)
        self.assertEqual(SR.replay_from_snapshot(SD.record, SD.snaps[seq], at(seq)).status, SR.SUCCEEDED)


class MisconnectionTest(unittest.TestCase):
    def test_other_record(self):
        report = SR.replay_from_snapshot(SD.record, OVER.snaps[0], at(0))  # 別の seed の対戦
        self.assertEqual(report.status, SR.CONNECTION_MISMATCH)
        self.assertIn("initial.seed", report.mismatch.items)
        self.assertIn("origin.game_id", report.mismatch.items)
        self.assertFalse(report.prefix_replayed)  # 安い確かめで止め、前半を再実行しない
        identity = SR.record_identity(OVER.record)
        report = SR.replay_from_snapshot(SD.record, SD.snaps[0], SR.RecordPosition.initial(record=identity))
        self.assertEqual((report.status, [p.code for p in report.problems]), (SR.CONNECTION_MISMATCH, ["record_differs"]))
        ok = SR.replay_from_snapshot(SD.record, SD.snaps[0], SR.RecordPosition.initial(record=SR.record_identity(SD.record)))
        self.assertEqual(ok.status, SR.SUCCEEDED)

    def test_other_seq(self):
        seq = first_seq(SD, lambda o: o["outcome"] == D.ACCEPTED and o["seq"] > 30)
        nxt = first_seq(SD, lambda o: o["outcome"] == D.ACCEPTED and o["seq"] > seq)
        report = SR.replay_from_snapshot(SD.record, rebuilt(SD.snaps[seq], lambda s: s), at(nxt))
        self.assertEqual(report.status, SR.CONNECTION_MISMATCH)
        self.assertEqual(report.phase, SR.PHASE_CONNECTION)
        self.assertIn("check.state", report.mismatch.items)
        self.assertEqual((report.scope, report.verified_seq), (None, None))

    def test_rebuilt_self_check_is_not_enough(self):
        # スナップショットの状態を変えて保存し直す（check も作り直され、復元は通る）。記録のその位置の状態とは違うので拒否する
        seq = first_seq(SD, lambda o: o["outcome"] == D.ACCEPTED and o["seq"] > 30)

        def swap_deck(state):
            player = state.players[0]
            deck = list(player.deck)
            i = next(i for i in range(1, len(deck)) if state.cards[deck[i]].card_id != state.cards[deck[0]].card_id)
            deck[0], deck[i] = deck[i], deck[0]
            players = list(state.players)
            players[0] = dataclasses.replace(player, deck=tuple(deck) if isinstance(player.deck, tuple) else deck)
            return dataclasses.replace(state, players=players)
        changed = rebuilt(SD.snaps[seq], swap_deck)
        self.assertTrue(SN.restore_snapshot(changed).restored)
        for prefix in (True, False):
            report = SR.replay_from_snapshot(SD.record, changed, at(seq), replay_prefix=prefix)
            self.assertEqual((report.status, report.mismatch.items), (SR.CONNECTION_MISMATCH, ("check.state",)))

    def test_items_outside_the_existing_checks(self):
        # 既存の確認値（形式 35 の sha256・乱数の指紋）が見ない保存項目を変える: 位置の確認値は記録と同じのまま、接続の確かめが見つける
        def reorder_event(state):
            log = list(state.log)
            i = next(i for i, e in enumerate(log) if len(e) > 2)
            log[i] = MappingProxyType(dict(reversed(list(log[i].items()))))
            return dataclasses.replace(state, log=tuple(log) if isinstance(state.log, tuple) else log)

        def decklist_order(state):
            deck = list(state.decklists[0])
            i = next(i for i in range(1, len(deck)) if deck[i] != deck[0])
            deck[0], deck[i] = deck[i], deck[0]
            return dataclasses.replace(state, decklists=(tuple(deck), state.decklists[1]))

        for c, prefix, label in ((SD_PLAIN, True, "旧記録・前半の再実行"), (SD, False, "拡張・接続用確認値")):
            seq = first_seq(c, lambda o: o["outcome"] == D.ACCEPTED and o["seq"] > 30)
            row_check = ops(c)[seq - 1]["check"]
            for name, change, expected in (("log の鍵の順", reorder_event, ("state.log",) if prefix else ("connection_check",)),
                                           ("decklists の順", decklist_order, ("initial.decklists",))):
                with self.subTest(label, item=name):
                    changed = rebuilt(c.snaps[seq], change)
                    self.assertTrue(SN.restore_snapshot(changed).restored)
                    self.assertEqual(changed.data["check"], row_check)  # 既存の確認値では見分けられない
                    report = SR.replay_from_snapshot(c.record, changed, at(seq), replay_prefix=prefix)
                    self.assertEqual((report.status, report.mismatch.items), (SR.CONNECTION_MISMATCH, expected))
                    self.assertEqual(report.prefix_replayed, prefix and expected == ("state.log",))

    def test_constructed_board_is_not_connected(self):
        # 構築盤面は保存できる（DS-CONSTRUCTED）が、new_game から始まる記録の位置にはつながらない
        state = H.build_test_state([{"active": H.PIKACHU}, {"active": H.PIKACHU}])
        snapshot = SN.save_snapshot(state)
        report = SR.replay_from_snapshot(SD.record, snapshot, at(0))
        self.assertIn(report.status, (SR.CONNECTION_MISMATCH, SR.NOT_SUPPORTED))
        self.assertFalse(report.succeeded)

    def test_position_inside_the_record(self):
        n = len(ops(SD))
        report = SR.replay_from_snapshot(SD.record, SD.snaps[n], at(n + 1))
        self.assertEqual((report.status, [p.code for p in report.problems]), (SR.INVALID_POSITION, ["seq_out_of_range"]))
        for bad in (lambda: SR.RecordPosition("middle", 3), lambda: SR.RecordPosition.after(0), lambda: SR.RecordPosition("initial", 2),
                    lambda: SR.RecordPosition.after(True), lambda: SR.RecordPosition.initial(record="x")):
            with self.assertRaises(ValueError):
                bad()
        with self.assertRaises(TypeError):
            SR.replay_from_snapshot(SD.record, SD.snaps[0], 0)  # accepted_index・seq の数だけでは位置にしない
        with self.assertRaises(TypeError):
            SR.replay_from_snapshot(SD.record, {"state": {}}, at(0))
        with self.assertRaises(TypeError):
            SR.replay_from_snapshot("record", SD.snaps[0], at(0))


class MismatchTest(unittest.TestCase):
    def test_initial_conditions_implementation_runtime_conventions(self):
        cases = (
            ("seed", lambda d: d["header"]["initial"].update(seed=d["header"]["initial"]["seed"] + 1), SR.CONNECTION_MISMATCH),
            ("implementation", lambda d: d["header"]["engine"].update(behavior_digest="0" * 64), SR.NOT_SUPPORTED),
            ("runtime", lambda d: d["header"]["runtime"].update(python_version=[2, 7, 0]), SR.NOT_SUPPORTED),
            ("conventions", lambda d: d["header"]["convention_set"].update(digest="x"), SR.NOT_SUPPORTED),
        )
        for name, edit, status in cases:
            with self.subTest(name):
                self.assertEqual(SR.replay_from_snapshot(edited(OVER.record, edit), OVER.snaps[5], at(5)).status, status)
        snap = OVER.snaps[5].data
        snap["engine"]["behavior_digest"] = "0" * 64
        report = SR.replay_from_snapshot(OVER.record, json.dumps(snap), at(5))
        self.assertEqual((report.status, report.restore.status), (SR.NOT_SUPPORTED, SN.NOT_SUPPORTED))

    def test_remaining_rows_checks_and_end(self):
        seq = first_seq(SD, lambda o: o["outcome"] == D.ACCEPTED and o["seq"] > 30)
        later = first_seq(SD, lambda o: o["outcome"] == D.ACCEPTED and o["seq"] > seq + 10)

        def change_command(d):
            op = d["operations"][later - 1]
            op["operation_id"] = "changed"
        report = SR.replay_from_snapshot(edited(SD.record, change_command), SD.snaps[seq], at(seq))
        self.assertEqual(report.status, SR.SUCCEEDED)  # operation_id は照らす値ではない（U4 と同じ）

        def change_check(d):
            d["operations"][later - 1]["check"]["rng"] = "0" * 64
        report = SR.replay_from_snapshot(edited(SD.record, change_check), SD.snaps[seq], at(seq))
        self.assertEqual((report.status, report.phase, report.mismatch.seq, report.mismatch.items), (SR.DIVERGED, SR.PHASE_SUFFIX, later, ("rng",)))
        self.assertEqual((report.scope, report.verified_seq), (SR.SCOPE_WHOLE_RECORD, later - 1))

        def change_connection(d):
            d["operations"][later - 1]["connection_check"] = "0" * 64
        report = SR.replay_from_snapshot(edited(SD.record, change_connection), SD.snaps[seq], at(seq))
        self.assertEqual((report.status, report.mismatch.items), (SR.DIVERGED, ("connection_check",)))
        self.assertEqual(RR.replay(edited(SD.record, change_connection)).mismatch.items, ("connection_check",))  # U4 も照らす

        def change_end(d):
            d["end"]["final_check"]["state"] = "0" * 64
        report = SR.replay_from_snapshot(edited(SD.record, change_end), SD.snaps[seq], at(seq))
        self.assertEqual(report.status, SR.INVALID_RECORD)  # 終わりの情報の改変は構造の検証で見つかる

        prefix_row = next(o["seq"] for o in reversed(ops(SD)[:seq - 1]) if o["outcome"] == D.ACCEPTED)

        def change_prefix_row(d):
            d["operations"][prefix_row - 1]["check"]["rng"] = "0" * 64
        broken = edited(SD.record, change_prefix_row)
        report = SR.replay_from_snapshot(broken, SD.snaps[seq], at(seq))
        self.assertEqual((report.status, report.phase, report.mismatch.seq, report.replay_verified), (SR.DIVERGED, SR.PHASE_PREFIX, prefix_row, False))
        # 前半を再実行しなければ、接続位置のあとだけが一致した結果（記録の全体の検証ではない）
        report = SR.replay_from_snapshot(broken, SD.snaps[seq], at(seq), replay_prefix=False)
        self.assertEqual((report.status, report.scope, report.replay_verified, report.verified_from), (SR.SUCCEEDED, SR.SCOPE_FROM_CONNECTION, False, seq))

    def test_extension_structure(self):
        undeclared = edited(SD_PLAIN.record, lambda d: d["operations"][0].update(connection_check="0" * 64))
        self.assertIn("connection_check_undeclared", [p.code for p in R.validate_record(undeclared).problems])
        unknown = edited(SD.record, lambda d: d["header"]["extensions"].update(future="x/1"))
        self.assertEqual(R.validate_record(unknown).status, R.UNSUPPORTED)
        cut = edited(unknown, lambda d: d.update(end=None))
        self.assertEqual(RR.replay(cut).status, RR.NOT_SUPPORTED)  # 途中で切れた記録でも、知らない拡張は扱わない
        missing = edited(SD.record, lambda d: d["operations"][0].pop("connection_check", None) if d["operations"][0]["outcome"] == D.ACCEPTED
                         else d["header"]["start"].pop("connection_check"))
        self.assertEqual(R.validate_record(missing).status, R.MALFORMED)
        self.assertEqual(RR.replay(SD.record).status, RR.SUCCEEDED)  # 拡張のある記録も U4 で全体を照らせる
        # None の位置（接続用確認値を作れなかった位置）は、前半を再実行しなければ確かめられない
        seq = first_seq(SD, lambda o: o["outcome"] == D.ACCEPTED and o["seq"] > 30)
        unavailable = edited(SD.record, lambda d: d["operations"][seq - 1].update(connection_check=None))
        report = SR.replay_from_snapshot(unavailable, SD.snaps[seq], at(seq), replay_prefix=False)
        self.assertEqual((report.status, [p.code for p in report.problems]), (SR.NOT_SUPPORTED, ["connection_check_unavailable"]))
        self.assertEqual(SR.replay_from_snapshot(unavailable, SD.snaps[seq], at(seq)).status, SR.SUCCEEDED)


class IncompleteFailureTest(unittest.TestCase):
    def test_incomplete_record(self):
        c = collect(9, max_steps=80, close=False)
        self.assertIsNone(c.record.data["end"])
        seq = len(ops(c)) // 2
        report = SR.replay_from_snapshot(c.record, c.snaps[seq], at(seq))
        self.assertEqual((report.status, report.scope, report.succeeded, report.replay_verified, report.end_verified),
                         (SR.INCOMPLETE, SR.SCOPE_WHOLE_RECORD, False, False, False))
        self.assertEqual(report.verified_seq, len(ops(c)))

    def aborted(self):
        collector, _ = R.ReplayCollector.start(*DECKS, 9, include_git=False, connection_checks=True)
        snaps = {0: SN.save_snapshot(collector.state)}
        for i in range(8):
            collector.submit(H.trainer_policy_command(collector.state, janken_winner=1))
            snaps[i + 1] = SN.save_snapshot(collector.state)

        def boom(state, command):
            raise InjectedError("secret 5150")
        with mock.patch.object(A, "apply_command", boom):
            collector.submit(H.trainer_policy_command(collector.state, janken_winner=1))
        return collector.close(), snaps

    def test_aborted_record(self):
        record, snaps = self.aborted()
        self.assertEqual(record.data["end"]["state"], R.END_ABORTED)
        report = SR.replay_from_snapshot(record, snaps[8], at(9))  # 失敗の行の直後からは続けない
        self.assertEqual((report.status, [p.code for p in report.problems]), (SR.INVALID_POSITION, ["after_failure"]))
        calls = {"n": 0}
        real = A.apply_command

        def fail_ninth(state, command):
            calls["n"] += 1
            if calls["n"] == 9:
                raise InjectedError("again")
            return real(state, command)
        with mock.patch.object(A, "apply_command", fail_ninth):
            report = SR.replay_from_snapshot(record, snaps[4], at(4))  # 前半 4 回 + 後半 4 回のあとの 9 回目で同じ失敗
        self.assertEqual((report.status, report.succeeded, report.replay_verified, report.verified_seq), (SR.RECORDED_FAILURE, False, False, 9))
        self.assertEqual(SR.replay_from_snapshot(record, snaps[4], at(4)).status, SR.DIVERGED)  # 失敗が起きなければ記録と違う

    def test_internal_errors(self):
        seq = len(ops(OVER)) // 2
        with mock.patch.object(SR, "checks", side_effect=ValueError("secret 6060")):
            report = SR.replay_from_snapshot(OVER.record, OVER.snaps[seq], at(seq))
        self.assertEqual((report.status, report.failure.exception_type), (SR.INTERNAL_ERROR, "ValueError"))
        self.assertNotIn("6060", repr(report))
        calls = {"n": 0}
        real = A.apply_command

        def fail_later(state, command):
            calls["n"] += 1
            if calls["n"] == seq + 3:
                raise InjectedError("secret 7070")
            return real(state, command)
        with mock.patch.object(A, "apply_command", fail_later):
            report = SR.replay_from_snapshot(OVER.record, OVER.snaps[seq], at(seq))
        self.assertEqual((report.status, report.phase), (SR.INTERNAL_ERROR, SR.PHASE_SUFFIX))
        with mock.patch.object(SN, "check_invariants", side_effect=InjectedError("x")):
            report = SR.replay_from_snapshot(OVER.record, OVER.snaps[seq], at(seq))
        self.assertEqual((report.status, report.restore.status), (SR.INTERNAL_ERROR, SN.INTERNAL_ERROR))
        for error in (KeyboardInterrupt(), SystemExit(1), MemoryError()):
            with self.subTest(type(error).__name__), mock.patch.object(SR, "checks", side_effect=error), self.assertRaises(type(error)):
                SR.replay_from_snapshot(OVER.record, OVER.snaps[seq], at(seq))

    def test_broken_snapshot_is_not_a_mismatch(self):
        seq = len(ops(OVER)) // 2
        data = OVER.snaps[seq].data
        data["check"]["log_length"] += 1  # 状態と自己確認値が合わない: 不一致ではなく、不正なスナップショット
        report = SR.replay_from_snapshot(OVER.record, json.dumps(data), at(seq))
        self.assertEqual((report.status, report.restore.status), (SR.INVALID_SNAPSHOT, SN.INCONSISTENT))
        report = SR.replay_from_snapshot(OVER.record, b"{", at(seq))
        self.assertEqual((report.status, report.restore.status), (SR.INVALID_SNAPSHOT, SN.READ_ERROR))


class BoundaryTest(unittest.TestCase):
    def test_repr_and_problems_have_no_secret(self):
        seq = len(ops(SD)) // 2
        report = SR.replay_from_snapshot(SD.record, SD.snaps[seq], at(seq))
        text = repr(report) + str(report)
        for secret in (SD.snaps[seq].data["check"]["state"], SD.snaps[seq].data["check"]["rng"], ops(SD)[seq - 1].get("connection_check")):
            self.assertNotIn(secret, text)
        bad = SR.replay_from_snapshot(SD.record, OVER.snaps[0], at(0))
        text = repr(bad) + " ".join(map(str, bad.problems + bad.mismatch.items))
        for secret in (H.PIKACHU, OVER.snaps[0].data["check"]["state"], ops(SD)[0].get("connection_check") or "-"):  # カード・確認値を出さない（項目の名前だけ）
            self.assertNotIn(secret, text)

    def test_views_do_not_carry_record_values(self):
        seq = len(ops(SD)) // 2
        restored = SN.RestoredGame(SN.restore_snapshot(SD.snaps[seq]), viewers=(0, 1, None))
        self.assertIsNone(restored.full_record)
        text = json.dumps([restored.view(v) for v in (0, 1, None)], ensure_ascii=False, default=str)
        for word in ("connection_check", "kyuura_snapshot_format", "kyuura_replay_format", SD.snaps[seq].data["check"]["rng"]):
            self.assertNotIn(word, text)

    def test_collector_contract_is_unchanged(self):
        plain = R.ReplayCollector.start(*DECKS, 9, include_git=False)[0]
        self.assertNotIn("extensions", plain.record().data["header"])
        self.assertNotIn("connection_check", plain.record().data["header"]["start"])
        with self.assertRaises(TypeError):
            R.ReplayCollector(object(), None, {}, True)  # 途中の状態から収集を始める入口はない


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("replay_from_snapshot", "RecordPosition", "record_identity", "kyuura-snapshot-state-sha256/1", "kyuura-replay-header-sha256/1",
                       "connection_mismatch", "invalid_position", "invalid_snapshot", "whole_record", "from_connection", "replay_verified",
                       "connection_checks", "extensions"):
            self.assertIn(needle, text)
        for result in SR.RESULTS:
            self.assertIn(f"`{result}`", text)
