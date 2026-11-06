"""v0.159（docs/integration-verification-v0.159.md）: U1〜U6 の総合検証で直した契約の回帰テスト。

- save_snapshot の誤りの優先: 状態を保存できない（境界・表せない値・深さ・大きさ）なら origin・label の形によらず SnapshotSaveError。保存できるときだけ origin・label の形を
  確かめる（ValueError）。補助の情報を加えた書き出しが大きさの上限を超えれば too_large
- 閲覧用記録の構造の検証が、完全な状態の接続用確認値（v0.158）とスナップショットの形式の鍵を、入ってはいけない項目として拒む
- 実装の識別が違う記録（過去の実装で作った記録を表す）は、拡張の有無・前半の再実行によらず unsupported
停止コードの文字列はテストの中に書かない。
"""

from __future__ import annotations

import copy
import pathlib
import unittest
from types import MappingProxyType
from unittest import mock

from kyuura_engine import replay_record as R
from kyuura_engine import replay_run as RR
from kyuura_engine import snapshot as SN
from kyuura_engine import snapshot_replay as SR
from kyuura_engine import view_record as V
from tests.test_replay_record_v0_153 import DECKS
from tests.test_state_snapshot_v0_157 import advance, pikachu_policy, simple_state

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "integration-verification-v0.159.md"
BAD_ORIGINS = ({"game_id": 1}, {"seq": -1}, {"other": "x"})
BAD_LABELS = (7, "x" * (SN.MAX_LABEL + 1))


def setUpModule():
    global BASE
    BASE = advance(simple_state(), pikachu_policy(9, probe=False), 30)


def with_log_value(value):
    state = BASE.clone()
    state.log = BASE.log + (MappingProxyType({"kind": "note", "turn": BASE.turn_number, "value": value}),)
    return state


def unsavable_states():
    moves = BASE.clone()
    moves.pending_moves = ("left_play",)
    nested = ()
    for _ in range(SN.MAX_DEPTH):
        nested = (nested,)
    return ((moves, "pending_moves"), (with_log_value(0.5), "unrepresentable_value"), (with_log_value(nested), "too_deep"))


class SaveErrorOrderTest(unittest.TestCase):
    def test_state_errors_come_before_origin_and_label(self):
        for state, code in unsavable_states():
            for kwargs in [{"origin": o} for o in BAD_ORIGINS] + [{"label": lb} for lb in BAD_LABELS]:
                with self.subTest(code=code, kwargs=kwargs), self.assertRaises(SN.SnapshotSaveError) as caught:
                    SN.save_snapshot(state, **kwargs)
                self.assertEqual(caught.exception.code, code)

    def test_origin_and_label_are_checked_when_the_state_can_be_saved(self):
        for kwargs in [{"origin": o} for o in BAD_ORIGINS] + [{"label": lb} for lb in BAD_LABELS]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                SN.save_snapshot(BASE, **kwargs)

    def test_size_limit(self):
        plain = SN.dumps_snapshot(SN.save_snapshot(BASE)).encode("utf-8")
        labelled = SN.save_snapshot(BASE, origin={"game_id": "g", "seq": 3}, label="before")
        self.assertEqual(list(labelled.data)[-2:], ["origin", "label"])  # 補助の情報は state のあと（v0.157 と同じ並び）
        self.assertEqual({k: v for k, v in labelled.data.items() if k not in ("origin", "label")}, SN.save_snapshot(BASE).data)
        with mock.patch.object(SN, "MAX_RECORD_BYTES", len(plain) - 1):  # 状態だけで上限を超える: origin の形によらず too_large
            for kwargs in ({}, {"origin": {"game_id": 1}}, {"label": 7}):
                with self.subTest(kwargs=kwargs), self.assertRaises(SN.SnapshotSaveError) as caught:
                    SN.save_snapshot(BASE, **kwargs)
                self.assertEqual(caught.exception.code, "too_large")
        with mock.patch.object(SN, "MAX_RECORD_BYTES", len(plain) + 5):  # 状態だけなら収まり、補助の情報を加えると超える
            SN.save_snapshot(BASE)
            with self.assertRaises(SN.SnapshotSaveError) as caught:
                SN.save_snapshot(BASE, label="a label longer than five bytes")
            self.assertEqual(caught.exception.code, "too_large")
            with self.assertRaises(ValueError):  # 形の誤りは、加えた大きさを確かめる前
                SN.save_snapshot(BASE, label=7)


class ViewRecordBoundaryTest(unittest.TestCase):
    def test_verifier_keys_are_forbidden(self):
        host, _ = V.ViewHost.start(*DECKS, 3, viewers=(1,), full_record=False)
        record = host.close()[1][1]
        self.assertEqual(V.validate_view_record(record).status, V.STRUCTURE_VALID)
        for key in (R.EXTENSION_CONNECTION_CHECK, SN.FORMAT_KEY):
            data = copy.deepcopy(record.data)
            data["entries"][0]["observation"][key] = "0" * 64
            report = V.validate_view_record(data)
            with self.subTest(key=key):
                self.assertEqual(report.status, V.MALFORMED)
                self.assertIn(("forbidden_field", f"$.entries[0].observation.{key}"), [(p.code, p.path) for p in report.problems])


class OtherImplementationTest(unittest.TestCase):
    def test_record_of_another_implementation_is_unsupported(self):
        for checks in (False, True):
            collector, _ = R.ReplayCollector.start(*DECKS, 0, include_git=False, connection_checks=checks)
            snap = SN.save_snapshot(collector.state)
            data = collector.close().data
            data["header"]["engine"]["behavior_digest"] = "0" * 64
            data["header"]["engine"]["version"] = "0.157.0"
            codes = {p.code for p in RR.replay(data).problems}
            self.assertEqual(RR.replay(data).status, RR.NOT_SUPPORTED)
            self.assertLessEqual({"implementation_differs", "engine_version_differs"}, codes)
            for prefix in (True, False):
                with self.subTest(checks=checks, prefix=prefix):
                    report = SR.replay_from_snapshot(data, snap, SR.RecordPosition.initial(), replay_prefix=prefix)
                    self.assertEqual((report.status, report.scope, report.replay_verified), (SR.NOT_SUPPORTED, None, False))


class DocumentTest(unittest.TestCase):
    def test_document_records_the_contracts_and_results(self):
        text = DOC.read_text(encoding="utf-8")
        for phrase in ("tools/snapshot_audit.py", "24,694", "from_connection", "whole_record", "SnapshotSaveError", "合法手の一覧ではない",
                       "behavior_digest", "274c903", "760"):
            self.assertTrue(phrase in text, phrase)
