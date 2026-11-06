"""v0.153（docs/replay-record-v0.153.md）: 完全な再現用記録の収集・読み書き・構造の検証（U3）。

盤面の種類（docs 7 章）:
- new_game からの合法な操作の列: ピカチュウのデッキ（tests/test_pikachu_games.py の方策。seed 9 はサドン・デスになり延長戦へ、seed 0 は終局）、たねポケモン 1 枚のデッキ（seed 1 は準備で停止）
- 記録をわざと壊す確かめ（JSON の辞書を書きかえる）
- 例外を差し込む確かめ（``adapter.apply_command`` を置きかえる）: 内部エラーと収集器の停止
エンジンで再実行して確認値と照らすこと（U4）はしない。停止コードの文字列はテストの中に書かない（停止の方針の台帳の走査が数えないように）。
"""

from __future__ import annotations

import copy
import json
import pathlib
import shutil
import tempfile
import unittest
from unittest import mock

from kyuura_engine import (
    EndTurn,
    ResolveDecision,
    StartSuddenDeath,
    apply_command,
    new_game,
    observe,
    state_to_dict,
)
from kyuura_engine import adapter as A
from kyuura_engine import conventions as C
from kyuura_engine import diagnostics as D
from kyuura_engine import replay_record as R
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import Phase
from tests import helpers as H
from tests.test_pikachu_games import play_game

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "replay-record-v0.153.md"
SPEC = ROOT / "docs" / "diagnostics-replay-api-design.json"
SETS = (None, "CS-KYUURA-PLAY-S2A@1", "CS-KYUURA-PLAY-PO@1")
DECKS = (H.PIKACHU_DECK, H.PIKACHU_DECK_B)
HALT_DECK = [H.PIKACHU] + [H.LIGHTNING] * 59  # たねポケモン 1 枚: seed 1 で準備の切り直しの補償が決まらず停止する


def snapshot(state):
    return repr(state_to_dict(state, format_version=max(FORMAT_VERSIONS))), state.rng.getstate(), tuple(dict(e) for e in state.log)


def drive(seed, *, record_rejections=True, probe=False, max_steps=6000, max_segments=2):
    """収集器で、ピカチュウの方策の操作を送る（サドン・デスなら延長戦を始める）。``probe`` なら、ときどき番でないプレイヤーの番の終わりと、決定に違う id の答えを送る（拒否）。"""
    collector, start = R.ReplayCollector.start(*DECKS, seed, game_id=f"pikachu-{seed}", record_rejections=record_rejections, operation_id="start")
    assert start.outcome == D.ACCEPTED
    segments = 1
    for step in range(max_steps):
        state = collector.state
        if state.phase in (Phase.GAME_OVER, Phase.HALTED) or (state.phase == Phase.SUDDEN_DEATH and segments >= max_segments):
            break
        if state.phase == Phase.SUDDEN_DEATH:
            collector.submit(StartSuddenDeath(), operation_id=f"op-{step}")
            segments += 1
            continue
        if probe and step % 17 == 5 and state.phase == Phase.MAIN:
            collector.submit(EndTurn(1 - state.current_player), submitter=1 - state.current_player, operation_id=f"bad-{step}")
        if probe and step % 13 == 3 and state.decision is not None:
            d = state.decision
            collector.submit(ResolveDecision(d.player, d.id + 7, d.options[:d.min_choices]), submitter=d.player, operation_id=f"wrong-{step}")
        command = H.trainer_policy_command(state, janken_winner=seed % 2)
        player = getattr(command, "player", None)
        result = collector.submit(command, submitter=player if player in (0, 1) else None, operation_id=f"op-{step}")
        assert result.outcome == D.ACCEPTED, (step, result.diagnosis)
    return collector


def setUpModule():
    global SD, SD_PLAIN, OVER
    SD = drive(9, probe=True)
    SD_PLAIN = drive(9, record_rejections=False, probe=True)
    OVER = drive(0)


def data_of(collector):
    return collector.close().data if not collector.stopped else collector.record().data


def report(data, **kw):
    return R.validate_record(data, **kw)


def ops(d):
    return d["operations"]


def rejected(d):
    return next(o for o in d["operations"] if o["outcome"] == D.REJECTED)


def without_seq(op):
    return {k: v for k, v in op.items() if k != "seq"}


def codes(rep, kind=None):
    return {p.code for p in rep.problems if kind is None or p.kind == kind}


class RoundTripTest(unittest.TestCase):
    def test_closed_record_round_trip_and_validation(self):
        record = SD.close()
        text = R.dumps_record(record)
        back = R.loads_record(text)
        self.assertEqual(back.data, record.data)
        self.assertEqual(R.dumps_record(back), text)
        rep = R.validate_record(back)
        self.assertEqual((rep.status, rep.complete, rep.end_state, rep.replay_verified, rep.problems), (R.STRUCTURE_VALID, True, R.END_CLOSED, False, ()))

    def test_in_progress_record_is_incomplete(self):
        collector, _ = R.ReplayCollector.start(*DECKS, 3, include_git=False)
        rep = R.validate_record(collector.record())
        self.assertEqual((rep.status, rep.complete), (R.INCOMPLETE, False))
        self.assertTrue(R.validate_record(collector.close()).complete)


class ContentTest(unittest.TestCase):
    def test_header_initial_conditions(self):
        header = SD.record().data["header"]
        self.assertEqual(header["initial"]["decklists"], [list(DECKS[0]), list(DECKS[1])])
        self.assertEqual((header["initial"]["seed"], header["initial"]["rules"], header["initial"]["card_pool"]), (9, new_game(*DECKS, 9).rules.id, "default"))
        self.assertEqual(header["convention_set"], C.registered_identity(C.DEFAULT_SET).record())
        self.assertEqual(header["formats"]["check_methods"], R.CHECK_METHODS)
        self.assertEqual(header["start"]["check"], R.checks(new_game(*DECKS, 9)))  # 開始の確認値は new_game の状態と同じ（記録は乱数・状態を変えない）
        self.assertTrue(header["rejections_recorded"])

    def test_operations_and_segments(self):
        data = SD.record().data
        ops = data["operations"]
        accepted = [op for op in ops if op["outcome"] == D.ACCEPTED]
        self.assertEqual([op["seq"] for op in ops], list(range(1, len(ops) + 1)))
        self.assertEqual([op["accepted_index"] for op in accepted], list(range(1, len(accepted) + 1)))
        self.assertTrue(any(op["outcome"] == D.REJECTED for op in ops))
        statuses = {op["check"]["status"] for op in accepted}
        self.assertTrue({D.AWAITING_DECISION, D.SUDDEN_DEATH_PENDING, D.IN_PROGRESS} <= statuses, statuses)
        answers = [op for op in accepted if "answers_decision" in op]
        self.assertTrue(answers)
        start_ops = [op for op in accepted if op["command"]["type"] == "start_sudden_death"]
        self.assertEqual(len(start_ops), 1)
        self.assertEqual((start_ops[0]["segment"], start_ops[0]["check"]["segment"]), (0, 1))
        end = SD.close().data["end"]
        self.assertEqual(end["segments"], [{"index": 0, "start_seq": 0}, {"index": 1, "start_seq": start_ops[0]["seq"]}])
        for op in ops:
            self.assertEqual(op["segment"], 0 if op["seq"] <= start_ops[0]["seq"] else 1)

    def test_rejections_optional_and_not_inputs(self):
        with_rejections = [op for op in SD.record().data["operations"] if op["outcome"] == D.ACCEPTED]
        plain = SD_PLAIN.record().data
        self.assertFalse(plain["header"]["rejections_recorded"])
        self.assertTrue(all(op["outcome"] == D.ACCEPTED for op in plain["operations"]))
        self.assertEqual([without_seq(op) for op in plain["operations"]], [without_seq(op) for op in with_rejections])  # 拒否を省いても受理した操作の順と確認値は同じ
        self.assertEqual(R.validate_record(SD_PLAIN.close()).status, R.STRUCTURE_VALID)

    def test_rejections_do_not_change_state(self):
        collector, _ = R.ReplayCollector.start(*DECKS, 9, include_git=False)
        state = collector.state
        while state.decision is None:
            collector.submit(H.trainer_policy_command(state, janken_winner=1))
            state = collector.state
        before = snapshot(state)
        d = state.decision
        result = collector.submit(ResolveDecision(d.player, d.id + 1, ()), submitter=d.player, operation_id="wrong")
        self.assertEqual(result.outcome, D.REJECTED)
        self.assertIs(collector.state, state)
        self.assertEqual(snapshot(collector.state), before)
        op = collector.record().data["operations"][-1]
        self.assertEqual((op["outcome"], op["diagnostic"]["category"], op["status"]), (D.REJECTED, D.INVALID_INPUT, D.AWAITING_DECISION))
        self.assertNotIn("check", op)

    def test_game_over_and_close(self):
        record = OVER.close()
        self.assertEqual(record.data["end"]["status"], D.GAME_OVER)
        self.assertEqual(R.validate_record(record).status, R.STRUCTURE_VALID)
        with self.assertRaises(R.CollectorStoppedError):
            OVER.submit(EndTurn(0))

    def test_halted_start_can_be_closed(self):
        collector, result = R.ReplayCollector.start(HALT_DECK, HALT_DECK, 1, include_git=False)
        self.assertEqual((result.outcome, result.status), (D.ACCEPTED, D.HALTED))
        rejected = collector.submit(EndTurn(0), submitter=0)
        self.assertEqual(rejected.outcome, D.REJECTED)
        record = collector.close()
        self.assertEqual((record.data["end"]["status"], record.data["header"]["start"]["check"]["halt"] is not None), (D.HALTED, True))
        self.assertEqual(R.validate_record(record).status, R.STRUCTURE_VALID)  # 閉じた記録（停止から再開する機能ではない）

    def test_rejected_start_makes_no_collector(self):
        collector, result = R.ReplayCollector.start(*DECKS, -1)
        self.assertIsNone(collector)
        self.assertEqual(result.diagnosis.diagnostic_id, D.INVALID_SEED_ID)

    def test_no_collection_from_a_midway_state(self):
        with self.assertRaises(TypeError):
            R.ReplayCollector(object(), A.HostedGame(new_game(*DECKS, 3)), {}, True)

    def test_same_behavior_as_apply_command(self):
        state, commands = play_game(9)
        collector, _ = R.ReplayCollector.start(*DECKS, 9, include_git=False)
        for command in commands:
            collector.submit(command)
        self.assertEqual(snapshot(collector.state), snapshot(state))
        x = new_game(*DECKS, 9)
        for command in commands[:40]:
            x = apply_command(x, command)
        self.assertEqual(collector.record().data["operations"][39]["check"]["state"], R.state_check(x))


class FailureTest(unittest.TestCase):
    def test_internal_error_stops_the_collector(self):
        collector, _ = R.ReplayCollector.start(*DECKS, 3, include_git=False)
        collector.submit(H.trainer_policy_command(collector.state, janken_winner=1))

        def boom(state, command):
            raise RuntimeError("secret 4242")
        with mock.patch.object(A, "apply_command", boom):
            result = collector.submit(H.trainer_policy_command(collector.state, janken_winner=1))
        self.assertEqual((result.outcome, result.diagnosis.category), (D.FAILED, D.INTERNAL_ERROR))
        self.assertTrue(collector.stopped)
        with self.assertRaises(R.CollectorStoppedError):
            collector.submit(EndTurn(0))
        record = collector.close()
        data = record.data
        self.assertEqual((data["end"]["state"], data["operations"][-1]["outcome"]), (R.END_ABORTED, D.FAILED))
        self.assertNotIn("4242", R.dumps_record(record))  # 生の文は記録しない（診断の識別だけ）
        rep = R.validate_record(record)
        self.assertEqual((rep.status, rep.end_state), (R.STRUCTURE_VALID, R.END_ABORTED))


class BrokenRecordTest(unittest.TestCase):
    """記録をわざと壊すと、種類ごとに見つける。"""

    def broken(self, edit):
        data = copy.deepcopy(SD.close().data)
        edit(data)
        return R.validate_record(data)

    def assertKind(self, edit, kind, code):
        rep = self.broken(edit)
        self.assertEqual(rep.status, kind, rep.problems)
        self.assertIn(code, codes(rep), rep.problems)

    def test_malformed(self):
        self.assertKind(lambda d: d["header"]["initial"].pop("seed"), R.MALFORMED, "initial_incomplete")
        self.assertKind(lambda d: d["header"]["initial"].update(decklists=[d["header"]["initial"]["decklists"][0]]), R.MALFORMED, "initial_incomplete")
        self.assertKind(lambda d: d["header"].pop("runtime"), R.MALFORMED, "missing_or_bad")
        self.assertKind(lambda d: ops(d)[3].update(outcome="maybe"), R.MALFORMED, "outcome_unknown")
        self.assertKind(lambda d: next(o for o in ops(d) if "check" in o)["check"].update(state="xyz"), R.MALFORMED, "check_bad")
        self.assertKind(lambda d: next(o for o in ops(d) if "check" in o).pop("check"), R.MALFORMED, "check_missing")
        self.assertKind(lambda d: d.pop(R.FORMAT_KEY), R.MALFORMED, "format_missing")
        self.assertKind(lambda d: d.update(extra=1), R.MALFORMED, "unknown_field")

    def test_inconsistent(self):
        self.assertKind(lambda d: ops(d).insert(5, copy.deepcopy(ops(d)[5])), R.INCONSISTENT, "seq_out_of_order")
        self.assertKind(lambda d: ops(d).__setitem__(slice(4, 6), [ops(d)[5], ops(d)[4]]), R.INCONSISTENT, "seq_out_of_order")
        self.assertKind(lambda d: ops(d).pop(10), R.INCONSISTENT, "seq_out_of_order")
        self.assertKind(lambda d: [o.update(operation_id="same") for o in ops(d)[:2]], R.INCONSISTENT, "operation_id_duplicate")
        self.assertKind(lambda d: d["end"].update(operations=1), R.INCONSISTENT, "end_operation_count")
        self.assertKind(lambda d: d["end"]["final_check"].update(log_length=0), R.INCONSISTENT, "end_final_check")
        self.assertKind(lambda d: d["end"].update(segments=[{"index": 0, "start_seq": 0}]), R.INCONSISTENT, "end_segments")
        self.assertKind(lambda d: d["header"]["initial"].update(conventions="CS-KYUURA-PLAY-PO@1"), R.INCONSISTENT, "conventions_mismatch")
        self.assertKind(lambda d: d["header"].update(rejections_recorded=False), R.INCONSISTENT, "rejection_not_announced")
        self.assertKind(lambda d: rejected(d)["diagnostic"].update(category=D.INTERNAL_ERROR), R.INCONSISTENT, "failure_recorded_as_rejection")
        self.assertKind(lambda d: rejected(d).update(check=d["end"]["final_check"]), R.INCONSISTENT, "check_on_non_accepted")

        def answer_wrong(d):
            op = next(o for o in ops(d) if "answers_decision" in o and o["command"]["type"] == "resolve_decision")
            op["command"]["decision"] += 100
        self.assertKind(answer_wrong, R.INCONSISTENT, "wrong_decision_answered")

        def jump_segment(d):
            op = next(o for o in ops(d) if o["outcome"] == D.ACCEPTED and o["seq"] > 20)
            op["check"]["segment"] = 1
        self.assertKind(jump_segment, R.INCONSISTENT, "segment_changed_without_start")

        def after_game_over(d):
            last = next(o for o in reversed(ops(d)) if o["outcome"] == D.ACCEPTED)
            extra = copy.deepcopy(last)
            extra.update(seq=len(ops(d)) + 1, accepted_index=last["accepted_index"] + 1, operation_id="extra")
            last["check"].update(status=D.GAME_OVER, decision=None, halt=None)
            last["status"] = D.GAME_OVER
            ops(d).append(extra)
        self.assertKind(after_game_over, R.INCONSISTENT, "accepted_after_terminal")

    def test_truncated(self):
        self.assertKind(lambda d: d.update(end=None), R.INCOMPLETE, "end_missing")

        def cut(d):  # 途中で切れた（後ろの操作と終わりがない）
            del d["operations"][len(d["operations"]) // 2:]
            d["end"] = None
        self.assertKind(cut, R.INCOMPLETE, "end_missing")

    def test_unsupported(self):
        self.assertKind(lambda d: d.update(kyuura_replay_format=2), R.UNSUPPORTED, "format_unknown")
        self.assertKind(lambda d: d["header"]["engine"].update(behavior_digest="0" * 64), R.UNSUPPORTED, "implementation_differs")
        self.assertKind(lambda d: d["header"]["runtime"]["python_version"].__setitem__(1, 0), R.UNSUPPORTED, "runtime_differs")
        self.assertKind(lambda d: d["header"]["runtime"]["rng"].update(format="other"), R.UNSUPPORTED, "rng_scheme_differs")
        self.assertKind(lambda d: d["header"]["convention_set"].update(digest="sha256:" + "0" * 64), R.UNSUPPORTED, "convention_set_unsupported")
        self.assertKind(lambda d: d["header"]["formats"]["check_methods"].update(state="other/1"), R.UNSUPPORTED, "check_method_unknown")
        # 版の 3 つ目（micro）だけの違いは扱える（OS・パスは記録しない）
        rep = self.broken(lambda d: d["header"]["runtime"]["python_version"].__setitem__(2, 999))
        self.assertEqual(rep.status, R.STRUCTURE_VALID)

    def test_reading_errors_carry_no_input(self):
        good = R.dumps_record(SD.close())
        secret = "SECRET-SEED-77881"
        cases = {
            "not_json": good[:-30] + secret,
            "duplicate_key": '{"a": 1, "a": "' + secret + '"}',
            "non_finite_number": '{"a": NaN, "b": "' + secret + '"}',
            "not_object": '["' + secret + '"]',
            "too_deep": '{"a":' * 100 + '"' + secret + '"' + "}" * 100,
        }
        for code, text in cases.items():
            with self.subTest(code), self.assertRaises(R.RecordFormatError) as ctx:
                R.loads_record(text)
            self.assertEqual(ctx.exception.code, code)
            self.assertNotIn(secret, str(ctx.exception))
        with mock.patch.object(R, "MAX_RECORD_BYTES", 10), self.assertRaises(R.RecordFormatError) as ctx:
            R.loads_record(good)
        self.assertEqual(ctx.exception.code, "too_large")


class IdentityTest(unittest.TestCase):
    """実装の識別: 場所・改行・Git の有無によらず、ゲームの処理に関わる内容の変化を見分ける。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = pathlib.Path(cls.tmp.name)
        cls.a = base / "a" / "kyuura_engine"
        cls.b = base / "deep" / "other place" / "kyuura_engine"
        for target in (cls.a, cls.b):
            shutil.copytree(R.PACKAGE_ROOT, target, ignore=shutil.ignore_patterns("__pycache__"))
        for path in cls.b.rglob("*.py"):  # 改行を CRLF に、先頭に BOM
            path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes().replace(b"\n", b"\r\n"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_same_content_same_identity(self):
        current = R.current_identity()
        for root in (self.a, self.b):
            identity = R.implementation_identity(root)
            self.assertEqual(identity, current)
        self.assertIsNone(R.git_commit(self.a))  # Git の木ではない（識別には使わない）

    def test_meaningful_changes_are_seen(self):
        root = pathlib.Path(self.tmp.name) / "changed" / "kyuura_engine"
        shutil.copytree(self.a, root)
        before = R.implementation_identity(root)
        cards = root / "data" / "kyuura_cards.json"
        cards.write_bytes(cards.read_bytes().replace(b'"hp": 40', b'"hp": 50', 1))
        after = R.implementation_identity(root)
        self.assertNotEqual(after["behavior_digest"], before["behavior_digest"])
        diag = root / "diagnostics.py"
        diag.write_bytes(diag.read_bytes() + b"\n# changed\n")
        again = R.implementation_identity(root)
        self.assertEqual(again["behavior_digest"], after["behavior_digest"])  # 診断の部品はゲームの処理の識別に入れない
        self.assertNotEqual(again["instrumentation_digest"], after["instrumentation_digest"])
        effects = root / "effects.py"
        effects.write_bytes(effects.read_bytes() + b"\n# changed\n")
        self.assertNotEqual(R.implementation_identity(root)["behavior_digest"], again["behavior_digest"])

    def test_identity_is_not_the_convention_digest(self):
        identity = R.current_identity()
        self.assertNotIn(identity["behavior_digest"], {C.registered_identity(k).digest.removeprefix("sha256:") for k in C.SETS})


class BoundaryTest(unittest.TestCase):
    """完全な記録は検証者用: 見る人の結果・repr・読み取りの誤りに出さない。"""

    def test_repr_has_no_secret(self):
        record = SD.close()
        text = repr(record)
        self.assertNotIn("decklists", text)
        self.assertNotIn(DECKS[0][0], text)
        self.assertNotIn(str(record.data["header"]["start"]["check"]["state"]), text)

    def test_views_are_unchanged_and_have_no_record_fields(self):
        collector, _ = R.ReplayCollector.start(*DECKS, 9, include_git=False)
        result = collector.submit(H.trainer_policy_command(collector.state, janken_winner=1), submitter=0)
        for viewer in (0, 1, None):
            view = result.view_for(viewer)
            if view is None:
                continue
            payload = json.dumps(view.to_dict(), ensure_ascii=False)
            for word in ("seed", "decklists", "behavior_digest", "check", "rng", "operations", R.FORMAT_KEY):
                self.assertNotIn(word, payload)
        self.assertEqual(collector.view(1), observe(collector.state, 1))
        self.assertFalse(hasattr(collector, "view_for"))


class ConventionSetsTest(unittest.TestCase):
    """既存の 3 つの集合: 記録の識別は登録の値のまま、構造の検証に通る。"""

    def test_three_sets(self):
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                collector, _ = R.ReplayCollector.start(*DECKS, 5, conventions=conventions, include_git=False)
                for _ in range(30):
                    state = collector.state
                    if state.phase in (Phase.GAME_OVER, Phase.HALTED, Phase.SUDDEN_DEATH):
                        break
                    collector.submit(H.trainer_policy_command(state, janken_winner=1))
                record = collector.close()
                key = C.parse_key(conventions) if conventions else C.DEFAULT_SET
                self.assertEqual(record.data["header"]["convention_set"], C.registered_identity(key).record())
                self.assertEqual(R.validate_record(record).status, R.STRUCTURE_VALID)


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("ReplayCollector", "validate_record", "loads_record", "replay_verified", "behavior_digest", "U4", "合法手"):
            self.assertIn(needle, text)

    def test_spec_adoptions(self):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        adopted = {d["id"] for d in spec["decisions"] if d["status"] == "adopted" and d["adoption"] != "ADOPT-U6-PRINCIPLES"}
        self.assertEqual(adopted, {"D-MESSAGE", "D-REJECTED", "D-POSTGAME", "D-STATE-INTEGRITY-VIEW", "D-IMPLEMENTATION-ID", "D-RUNTIME", "D-CHECK-DENSITY",
                                   "D-VERSIONS"})
        # v0.156: D-SNAPSHOT-BASE・D-HALT-SNAPSHOT は、後の原則の採用（ADOPT-U6-PRINCIPLES）だけで決まった（この版の採用では決めていない）
        later = next(a for a in spec["adoptions"] if a["id"] == "ADOPT-U6-PRINCIPLES")
        decided = {d["id"]: d for d in spec["decisions"]}
        for key in ("D-SNAPSHOT-BASE", "D-HALT-SNAPSHOT"):
            self.assertEqual((decided[key]["status"], decided[key]["adoption"]), ("adopted", "ADOPT-U6-PRINCIPLES"))
            self.assertIn(key, later["decisions"])
        # v0.154: 後の承認（ADOPT-U4）で U4 も実装済みになった。v0.153 の採用の記録（ADOPT-U3）が持つのは U3 と 4 つの判断事項だけ
        u3 = next(a for a in spec["adoptions"] if a["id"] == "ADOPT-U3")
        self.assertEqual((u3["units"], set(u3["decisions"])), (["U3"], {"D-IMPLEMENTATION-ID", "D-RUNTIME", "D-CHECK-DENSITY", "D-VERSIONS"}))
        units = {u["id"]: u["status"] for u in spec["units"]}
        self.assertEqual(units["U3"], "implemented")
        # v0.158: 採用の記録の単位には、部分の単位（"U6/S1" の形。U6 は partial）もある。全体を実装した単位だけを比べる
        self.assertEqual({u for u, st in units.items() if st == "implemented"}, {u for a in spec["adoptions"] for u in a["units"] if "/" not in u})


if __name__ == "__main__":
    unittest.main()
