"""状態スナップショット（U6）の仕様案の確かめ（docs/state-snapshot-design.md 9 章）。

仕様案の JSON・文書の生成区画が同じ元から作ったものであることと、分類表とコードの型・項目の照合・原則に反する分類を、わざと壊した値で見つけることを確かめる。件数を期待値に写さない。
"""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("build_state_snapshot_design", ROOT / "scripts" / "build_state_snapshot_design.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)


def written() -> dict:
    return json.loads(B.OUTPUT.read_text(encoding="utf-8"))


class GeneratedTest(unittest.TestCase):
    def test_written_files_match_the_source(self):
        self.assertEqual(B.check(written(), B.DESIGN.read_text(encoding="utf-8"), B.PLAN.read_text(encoding="utf-8")), [])

    def test_edited_table_is_detected(self):
        design = B.DESIGN.read_text(encoding="utf-8").replace("| `pending_moves` | absent |", "| `pending_moves` | value |", 1)
        problems = B.check(written(), design, B.PLAN.read_text(encoding="utf-8"))
        self.assertTrue(any("生成区画" in p for p in problems), problems)


class CoverageTest(unittest.TestCase):
    """分類表とコードの型・項目を名前で照らす（項目が加わった・消えた・型が加わったら見つける）。"""

    def test_current_code_is_covered(self):
        self.assertEqual(B.coverage_problems(written()), [])

    def test_added_field_is_detected(self):
        code = B.code_fields()
        code["GameState"] = code["GameState"] + ["future_field_for_test"]
        code["PoisonMist"] = code["PoisonMist"] + ["future_flag_for_test"]
        problems = B.coverage_problems(written(), code)
        self.assertIn("GameState.future_field_for_test に分類がない（コードに加わった項目）", problems)
        self.assertIn("PoisonMist.future_flag_for_test に分類がない（コードに加わった項目）", problems)

    def test_removed_field_and_new_type_are_detected(self):
        code = B.code_fields()
        code["PendingDecision"] = [f for f in code["PendingDecision"] if f != "context"]
        code["FutureEffectForTest"] = ["source_card"]
        problems = B.coverage_problems(written(), code)
        self.assertIn("PendingDecision.context の分類があるが、コードにない", problems)
        self.assertIn("型 FutureEffectForTest に分類がない（コードに加わった型）", problems)

    def test_counts_keep_fields_attributes_and_metadata_apart(self):
        # 状態の項目・項目でない属性・見出しの補助情報を 1 つの数に足さない。項目の数はコードの項目の名前の数と同じ
        counts = B.category_counts(written())
        code = B.code_fields()
        self.assertEqual(sum(c["fields"] for c in counts.values()), sum(len(fields) for fields in code.values()))
        self.assertEqual(sum(c["non_field"] for c in counts.values()), len(written()["non_field_attributes"]))
        self.assertEqual(sum(c["metadata"] for c in counts.values()), len(written()["snapshot_metadata"]))
        self.assertEqual(counts["descriptive"]["fields"], 0)

    def test_same_field_count_but_renamed_is_detected(self):
        # 件数が同じでも、名前が変われば見つける
        code = B.code_fields()
        code["Halt"] = ["code", "message", "references", "interruption_renamed"]
        problems = B.coverage_problems(written(), code)
        self.assertTrue(any("interruption_renamed" in p for p in problems))
        self.assertTrue(any("Halt.interruption の分類があるが" in p for p in problems))


class BrokenSpecTest(unittest.TestCase):
    def broken(self, edit) -> list[str]:
        spec = copy.deepcopy(written())
        edit(spec)
        return B.spec_problems(spec)

    def test_principles_are_enforced(self):
        cases = [
            (lambda s: s["explicit_types"]["GameState"]["rng"].update(category="derive"), "乱数"),
            (lambda s: s["explicit_types"]["GameState"]["pending_moves"].update(category="value"), "pending_moves"),
            (lambda s: s["explicit_types"]["GameState"]["definitions"].update(category="value"), "definitions"),
            (lambda s: s["explicit_types"]["PendingDecision"]["context"].update(category="absent"), "決定待ち"),
            (lambda s: s["explicit_types"]["CardInstance"]["uid"].update(category="derive"), "uid"),
            (lambda s: s["format"].update(key="format_version"), "形式の版の名前"),
            (lambda s: next(x for x in s["states"] if "HALTED" in x["state"]).update(save=False), "停止"),
            (lambda s: s.update(approval="approved"), "承認"),
            (lambda s: s["decisions"][0].update(status="maybe"), "pending・adopted でない"),
            (lambda s: s["decisions"][0].pop("adopted"), "採用の記録"),
            (lambda s: s["units"][4].update(status="implemented"), "実装した単位"),
        ]
        for edit, word in cases:
            with self.subTest(word):
                self.assertTrue(any(word in p for p in self.broken(edit)), word)

    def test_vocabulary_and_plan(self):
        cases = [
            (lambda s: s["explicit_types"]["GameState"]["seed"].update(category="maybe"), "語彙"),
            (lambda s: s["explicit_types"]["GameState"]["seed"].update(basis=""), "根拠"),
            (lambda s: s["restore_steps"][2].update(failure="guessed"), "guessed"),
            (lambda s: s["units"][0].update(depends=["S6"]), "あとの単位"),
            (lambda s: s["verification"].__setitem__(6, {"id": "F7", "case": "x", "fixture": "CS-KYUURA-CURRENT@1"}), "CS-KYUURA-PLAY-PO@1"),
        ]
        for edit, word in cases:
            with self.subTest(word):
                self.assertTrue(any(word in p for p in self.broken(edit)), word)


class CodecCoverageTest(unittest.TestCase):
    """分類表と、実装の型の対応表（kyuura_engine.snapshot）を名前で照らす。"""

    def test_codec_matches(self):
        self.assertEqual(B.codec_problems(written()), [])

    def test_codec_difference_is_detected(self):
        from kyuura_engine import snapshot

        codec = copy.deepcopy(snapshot.codec_fields())
        codec["GameState"]["pending_moves"] = "value"
        codec["PoisonMist"]["future_flag_for_test"] = "value"
        del codec["Asleep"]
        problems = B.codec_problems(written(), codec)
        for name in ("GameState", "PoisonMist", "Asleep"):
            self.assertTrue(any(name in p for p in problems), name)


class DocumentTest(unittest.TestCase):
    def test_cross_references(self):
        design = (ROOT / "docs" / "diagnostics-replay-api-design.md").read_text(encoding="utf-8")
        plan = (ROOT / "docs" / "diagnostics-replay-api-implementation-plan.md").read_text(encoding="utf-8")
        self.assertIn("state-snapshot-design.md", design)
        self.assertIn("state-snapshot-implementation-plan.md", plan)
        spec = json.loads((ROOT / "docs" / "diagnostics-replay-api-design.json").read_text(encoding="utf-8"))
        status = {d["id"]: d["status"] for d in spec["decisions"]}
        self.assertEqual((status["D-SNAPSHOT-BASE"], status["D-HALT-SNAPSHOT"]), ("adopted", "adopted"))
        self.assertEqual({u["id"]: u["status"] for u in spec["units"]}["U6"], "planned")  # S5 が未実装なので、U6 全体は planned のまま
        snapshot_spec = written()
        self.assertEqual({u["id"]: u["status"] for u in snapshot_spec["units"]},
                         {"S1": "implemented", "S2": "implemented", "S3": "implemented", "S4": "implemented", "S5": "planned", "S6": "implemented"})
        self.assertEqual({d["id"]: d["status"] for d in snapshot_spec["decisions"]}, dict.fromkeys(snapshot_spec["implementation_adoption"]["decisions"], "adopted"))


if __name__ == "__main__":
    unittest.main()
