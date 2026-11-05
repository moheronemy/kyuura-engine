"""v0.146（docs/play-set-verification-v0.146.md 2 章）: 1 歩ごとの比較の道具（tools/engine_lockstep.py）の記録に規約集合を持たせ、集合の違う記録を同じ条件の対戦として比べない。

- 記録の形式 2: 見出し（記録の形式・指紋の書き出しの形式・規約集合の識別）と、歩ごとの集合の指紋 ``k``。記録の途中で、状態の集合が木の登録と見出しに合うかを確かめる
- 指紋の形式: 今の挙動の集合は形式 9（前の版の木と比べる）、ほかの集合は形式 35（規約集合の項目を含む。エンジンの版だけを除く）と、集合間の比較だけが使う指紋 ``x``
- ``compare``: 同じ集合だけを通常に比べる（集合・指紋の形式の違い・記録の改変は比べる前に拒否。終了コード 2）。意図した集合間の比較は ``--cross-set``（終了コード 3）。
  見出しのない形式 1 の記録は、条件を満たすときだけ（``--legacy-as``）比べる

道具の関数を同じプロセスで呼ぶ（記録は小さな対戦の組: 自然な対戦のモジュール 1 つと、ストレスの組 1 つ）。
"""

from __future__ import annotations

import argparse
import contextlib
import gzip
import io
import json
import pathlib
import sys
import tempfile
import unittest

from kyuura_engine import StartSuddenDeath, apply_command
from kyuura_engine import conventions as C

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import engine_lockstep as lockstep

DOC = ROOT / "docs" / "play-set-verification-v0.146.md"
CURRENT, S2A, PO = "CS-KYUURA-CURRENT@1", "CS-KYUURA-PLAY-S2A@1", "CS-KYUURA-PLAY-PO@1"
TMP = None


def record_args(out, conventions=None, *, save_every=0, digest_format=None, corpus="all"):
    return argparse.Namespace(root=str(ROOT), route=None, preflight=None, corpus=corpus, modules="test_coin_games", scenarios="basics", seeds=1,
                              stress_seeds=1, start=0, steps=120, illegal_rate=0.05, save_every=save_every, timing=False, card_data_commit="",
                              conventions=conventions, digest_format=digest_format, out=str(out))


def make(name, conventions=None, **kw):
    path = pathlib.Path(TMP.name) / f"{name}.jsonl.gz"
    if not path.exists():
        with contextlib.redirect_stdout(io.StringIO()):
            rc = lockstep.record(record_args(path, conventions, **kw))
        assert rc == 0, (name, rc)
    return path


def read_lines(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def write_lines(path, lines):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return path


def compare(a, b, *, cross_set=False, legacy_as=None):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        rc = lockstep.compare(argparse.Namespace(a=str(a), b=str(b), cross_set=cross_set, legacy_as=legacy_as))
    return rc, buffer.getvalue()


def rewritten(source, name, change_header=None, change_line=None):
    """記録を書きかえた写し（``change_header`` は見出しの集合を変え、歩の ``k`` を合わせて作り直す＝形の正しい別の集合の記録。``change_line`` は行ごとの改変）。"""
    lines = read_lines(source)
    if change_header is not None:
        header = lines[0]["header"]
        change_header(header["conventions"])
        k = lockstep.conventions_digest(header["conventions"])
        named = f"{header['conventions']['id']}@{header['conventions']['version']}"
        for line in lines[1:]:
            if "k" in line:
                line["k"] = k
            if "summary" in line:
                line["conventions"] = named
    if change_line is not None:
        lines = change_line(lines)
    return write_lines(pathlib.Path(TMP.name) / f"{name}.jsonl.gz", lines)


def as_format_1(source, name, version):
    """見出し・``k`` を除き、終わりの集計の版を ``version`` にした形式 1 の記録（v0.145 までの道具の記録の形）。"""
    lines = []
    for line in read_lines(source)[1:]:
        line.pop("k", None)
        if "summary" in line:
            line.pop("conventions", None)
            line.pop("record_format", None)
            line["version"] = version
        lines.append(line)
    return write_lines(pathlib.Path(TMP.name) / f"{name}.jsonl.gz", lines)


def setUpModule():
    global TMP
    TMP = tempfile.TemporaryDirectory()


def tearDownModule():
    TMP.cleanup()


class RecordFormatTest(unittest.TestCase):
    def test_header_and_step_digests(self):
        """見出しに記録の形式 2・指紋の形式・集合の識別（ID・版・照合値・構成）。歩には集合の指紋 k。今の挙動の集合は形式 9、PO は形式 35（指紋 x を加え、エンジンの版を除く）。"""
        for name, conventions, digest_format in (("current", None, 9), ("po", PO, 35)):
            with self.subTest(name):
                lines = read_lines(make(name, conventions))
                header = lines[0]["header"]
                identity = C.registered_identity(C.parse_key(conventions or CURRENT))
                self.assertEqual((header["record_format"], header["digest_format"], header["conventions"]), (2, digest_format, identity.record()))
                self.assertEqual(header["digest_excludes"], ["engine_version"] if digest_format == 35 else [])
                steps = [line for line in lines[1:] if "h" in line]
                self.assertTrue(steps)
                self.assertEqual({line["k"] for line in steps}, {lockstep.conventions_digest(identity.record())})
                self.assertEqual(all("x" in line for line in steps), digest_format == 35)
                summary = lines[-1]
                self.assertEqual((summary["errors"], summary["record_format"], summary["conventions"]), (0, 2, f"{identity.set_id}@{identity.version}"))
                self.assertGreater(summary["summary"]["conventions_checked"], len(steps) - 1)

    def test_unknown_set_and_unrepresentable_digest_stop_before_recording(self):
        """知らない集合・形式 9 で書き出せない集合は、記録を始める前に止める（推測で既定の集合にしない）。"""
        out = pathlib.Path(TMP.name) / "never.jsonl.gz"
        with self.assertRaises(SystemExit) as caught:
            lockstep.record(record_args(out, "CS-KYUURA-UNKNOWN@1"))
        self.assertIn("確かめられない", str(caught.exception))
        with self.assertRaises(SystemExit) as caught:
            lockstep.record(record_args(out, PO, digest_format=9))
        self.assertIn("書き出せない", str(caught.exception))
        self.assertFalse(out.exists())

    def test_legacy_default_digest_is_the_pinned_one(self):
        """形式 1 の記録の対応付けに使う既定の集合の照合値は、v0.142 から固定の照合値と同じ。"""
        key = lockstep.LEGACY_DEFAULT_SET[:2]
        self.assertEqual(lockstep.LEGACY_DEFAULT_SET[2], C.PINNED_SET_DIGESTS[key])
        self.assertEqual(lockstep.LEGACY_DEFAULT_SET[2], C.registered_identity(key).digest)


class SameSetCompareTest(unittest.TestCase):
    def test_same_set_compares_as_before(self):
        for name, conventions in (("current", None), ("s2a", S2A), ("po", PO)):
            with self.subTest(name):
                path = make(name, conventions)
                rc, text = compare(path, path)
                self.assertEqual(rc, 0, text)
                self.assertIn("食い違い 0", text)

    def test_save_and_restore_keep_the_set(self):
        """保存・復元を挟む記録（``--save-every``）: 復元した状態の集合も確かめ、挟まない記録と同じ指紋。"""
        plain, saved = make("po", PO), make("po_saved", PO, save_every=3)
        summary = read_lines(saved)[-1]
        self.assertGreater(summary["summary"]["restored"], 0)
        self.assertEqual(summary["errors"], 0)
        rc, text = compare(plain, saved)
        self.assertEqual(rc, 0, text)

    def test_a_step_divergence_is_still_a_divergence(self):
        source = make("po", PO)

        def change(lines):
            for line in lines:
                if "h" in line and line.get("i") == 3:
                    line["h"] = "0" * 32
                    line["x"] = "0" * 32
                    break
            return lines

        rc, text = compare(source, rewritten(source, "po_diverged", change_line=change))
        self.assertEqual(rc, 1, text)
        self.assertIn("DIVERGENCE", text)


class MismatchTest(unittest.TestCase):
    def test_id_version_digest_members_each_refused(self):
        """形の正しい別の集合の記録（見出しと k が合う）: ID・版・照合値・構成のどれが違っても、歩を比べる前に拒否する（終了コード 2）。"""
        source = make("po", PO)
        changes = {
            "集合の ID": lambda c: c.update(id="CS-KYUURA-PLAY-OTHER"),
            "集合の版": lambda c: c.update(version=2),
            "集合の照合値": lambda c: c.update(digest="sha256:" + "0" * 64),
            "構成の規約": lambda c: c.update(members=c["members"][:-1]),
        }
        for label, change in changes.items():
            with self.subTest(label):
                rc, text = compare(source, rewritten(source, f"po_{len(label)}_{label[-2:]}", change_header=change))
                self.assertEqual(rc, 2, text)
                self.assertIn("REFUSED", text)
                self.assertIn(label, text)
                self.assertNotIn("食い違い", text)

    def test_different_registered_sets_are_refused(self):
        for a, b in (("s2a", "po"), ("current", "po"), ("current", "s2a")):
            with self.subTest(pair=(a, b)):
                rc, text = compare(make(a, {"current": None, "s2a": S2A, "po": PO}[a]), make(b, {"current": None, "s2a": S2A, "po": PO}[b]))
                self.assertEqual(rc, 2, text)
                self.assertIn("規約集合が違う", text)

    def test_tampered_records_are_refused(self):
        """記録の改変: 歩の k を変えた・見出しだけを変えた（k と合わない）・見出しが途中にある・知らない記録の形式・除いた項目の改変・形式 35 の記録の x がない。"""
        source = make("po", PO)

        def k_changed(lines):
            next(line for line in lines if "k" in line)["k"] = "f" * 16
            return lines

        def header_only(lines):
            lines[0]["header"]["conventions"]["id"] = "CS-KYUURA-PLAY-S2A"
            return lines

        def header_moved(lines):
            return [lines[1], lines[0], *lines[2:]]

        def unknown_format(lines):
            lines[0]["header"]["record_format"] = 3
            return lines

        def excludes_changed(lines):
            lines[0]["header"]["digest_excludes"] = []
            return lines

        def x_missing(lines):
            next(line for line in lines if "x" in line).pop("x")
            return lines

        for change in (k_changed, header_only, header_moved, unknown_format, excludes_changed, x_missing):
            with self.subTest(change.__name__):
                rc, text = compare(source, rewritten(source, f"tampered_{change.__name__}", change_line=change))
                self.assertEqual(rc, 2, text)
                self.assertIn("REFUSED 記録の形式", text)


class CrossSetTest(unittest.TestCase):
    def test_cross_set_needs_the_flag_and_is_not_a_success(self):
        """意図した集合間の比較: ``--cross-set`` を付けたときだけ。両方とも形式 35 の指紋の記録。終わっても終了コード 3（互換性の判定ではない）。"""
        strict35, po = make("current35", None, digest_format=35), make("po", PO)
        rc, text = compare(strict35, po)
        self.assertEqual(rc, 2)
        rc, text = compare(strict35, po, cross_set=True)
        self.assertEqual(rc, 3, text)
        self.assertIn("互換性の判定ではない", text)
        rc, text = compare(make("current", None), po, cross_set=True)
        self.assertEqual(rc, 2)
        self.assertIn("形式 35 の指紋", text)
        rc, text = compare(po, po, cross_set=True)
        self.assertEqual(rc, 2)
        self.assertIn("集合は同じ", text)

    def test_cross_set_finds_the_first_difference_by_x(self):
        """集合間の比較は x・コマンド・受理と拒否で比べる（h・k は集合で違うので除く）。x の差は差として数える。"""
        source = make("po", PO)

        def change(lines):
            next(line for line in lines if "x" in line and line.get("i") == 2)["x"] = "1" * 32
            return lines

        other = rewritten(source, "po_x_changed", change_line=change)
        strict35 = make("current35", None, digest_format=35)
        rc, text = compare(strict35, other, cross_set=True)
        self.assertEqual(rc, 3)
        self.assertIn("DIVERGENCE", text)


class LegacyRecordTest(unittest.TestCase):
    def test_format_1_records(self):
        """形式 1（見出しのない v0.145 までの記録）: 形式 1 どうしは今までどおり。0.142 以後の木の形式 1 は ``--legacy-as CS-KYUURA-CURRENT@1`` を付け、形式 2 の側がその集合（固定の照合値）の
        ときだけ比べる。集合を持たない木（0.142 より前）の形式 1 は、集合の記録がある形式 2 とは比べない。"""
        current = make("current", None)
        old = as_format_1(current, "legacy_0145", "0.145.0")
        rc, text = compare(old, old)
        self.assertEqual(rc, 0, text)
        rc, text = compare(old, current)
        self.assertEqual(rc, 2)
        self.assertIn("--legacy-as", text)
        rc, text = compare(old, current, legacy_as=CURRENT)
        self.assertEqual(rc, 0, text)
        rc, text = compare(old, current, legacy_as=PO)
        self.assertEqual(rc, 2)
        po35 = make("po", PO)
        rc, text = compare(old, po35, legacy_as=CURRENT)
        self.assertEqual(rc, 2)
        pre = as_format_1(current, "legacy_0141", "0.141.0")
        rc, text = compare(pre, current)
        self.assertEqual(rc, 2)
        self.assertIn("集合を持たない木", text)
        unknown = as_format_1(current, "legacy_unknown", "?")
        self.assertEqual(compare(unknown, current, legacy_as=CURRENT)[0], 2)

    def test_format_1_with_k_is_refused(self):
        current = make("current", None)
        rc, text = compare(rewritten(current, "headerless", change_line=lambda lines: lines[1:]), current, legacy_as=CURRENT)
        self.assertEqual(rc, 2)
        self.assertIn("見出しが失われた", text)


class RecorderCheckTest(unittest.TestCase):
    """記録の途中の確かめ（``Recorder.check_conventions``）: 状態の集合が見出しと違えば記録の誤り。延長戦は集合を引き継ぐ。"""

    def recorder(self, key):
        import kyuura_engine as engine

        return lockstep.Recorder(engine, engine.apply_command, io.StringIO(), conventions_module=C,
                                 conventions=C.registered_identity(C.parse_key(key)).record())

    def test_state_with_another_set_is_an_error(self):
        from tests.helpers import build_test_state

        state = build_test_state([{"active": "PMCG1-060", "deck": ["PMCG1-097"] * 10}, {"active": "PMCG1-060", "deck": ["PMCG1-097"] * 10}])
        self.recorder(CURRENT).check_conventions(state)
        with self.assertRaises(lockstep.ConventionRecordError):
            self.recorder(PO).check_conventions(state)

    def test_sudden_death_inherits_the_set(self):
        from tests import test_sudden_death_v0_134 as SD
        from tests.helpers import build_test_state

        state = build_test_state([{"active": SD.PIKA, "deck": [SD.PIKA] + [SD.FIRE] * 30, "prizes": 0},
                                  {"active": SD.PIKA, "deck": [SD.PIKA] + [SD.FIRE] * 30, "prizes": 0}])
        base = SD.constructed_sudden_death(SD.with_decklists(state))
        base.conventions = C.registered_identity(C.parse_key(PO))
        started = apply_command(base, StartSuddenDeath())
        self.recorder(PO).check_conventions(started)
        changed = started.clone()
        changed.conventions = C.registered_identity(C.parse_key(S2A))
        with self.assertRaises(lockstep.ConventionRecordError):
            self.recorder(PO).check_conventions(changed)


class DocumentTest(unittest.TestCase):
    def test_document_records_the_contract(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("記録の形式 2", "--cross-set", "--legacy-as", "--digest-format", "engine_version"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
