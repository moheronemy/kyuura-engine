"""診断 API と対戦記録・再現インターフェースの仕様案の確かめ（docs/diagnostics-replay-api-design.md 11 章）。

仕様案の JSON・文書の生成区画が同じ元から作ったものであることと、わざと壊した仕様で ``--check`` の確かめが問題を見つけることを確かめる。件数を期待値に写さない。
"""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "build_diagnostics_replay_api_design.py"
_spec = importlib.util.spec_from_file_location("build_diagnostics_replay_api_design", SCRIPT)
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)


def written() -> dict:
    return json.loads(B.OUTPUT.read_text(encoding="utf-8"))


def problems_of(spec: dict) -> list[str]:
    return B.spec_problems(spec)


class GeneratedTest(unittest.TestCase):
    def test_written_files_match_the_source(self):
        problems = B.check(written(), B.DESIGN.read_text(encoding="utf-8"), B.PLAN.read_text(encoding="utf-8"))
        self.assertEqual(problems, [])

    def test_edited_table_is_detected(self):
        design = B.DESIGN.read_text(encoding="utf-8").replace("| `internal_error` |", "| `internal_errors` |", 1)
        problems = B.check(written(), design, B.PLAN.read_text(encoding="utf-8"))
        self.assertTrue(any("生成区画" in p for p in problems), problems)

    def test_missing_block_is_detected(self):
        plan = B.PLAN.read_text(encoding="utf-8").replace("<!-- generated:units begin -->", "", 1)
        problems = B.check(written(), B.DESIGN.read_text(encoding="utf-8"), plan)
        self.assertTrue(any("units" in p for p in problems), problems)


class BrokenSpecTest(unittest.TestCase):
    """壊した仕様で、それぞれの確かめが問題を見つける。"""

    def broken(self, edit) -> list[str]:
        spec = copy.deepcopy(written())
        edit(spec)
        return problems_of(spec)

    def test_internal_error_mapped_to_unsupported(self):
        def edit(spec):
            spec["classification_rules"][0]["category"] = "unsupported"
        self.assertTrue(any("内部エラー" in p for p in self.broken(edit)))

    def test_internal_error_listed_as_rejection(self):
        def edit(spec):
            rejected = next(o for o in spec["outcomes"] if o["id"] == "rejected")
            rejected["categories"].append("internal_error")
        self.assertTrue(any("internal_error" in p for p in self.broken(edit)))

    def test_secret_visible_to_spectator(self):
        def edit(spec):
            next(v for v in spec["visibility"] if v["item"] == "seed")["spectator"] = "yes"
        self.assertTrue(any("seed" in p for p in self.broken(edit)))

    def test_rejection_sent_to_opponent(self):
        def edit(spec):
            spec["examples"][1]["views"]["opponent"] = {"outcome": "rejected"}
        self.assertTrue(any("相手・観戦者" in p for p in self.broken(edit)))

    def test_verifier_field_in_view(self):
        def edit(spec):
            spec["examples"][0]["views"]["spectator"]["state_digest"] = "x"
        self.assertTrue(any("検証者だけの項目" in p for p in self.broken(edit)))

    def test_unknown_code_and_case(self):
        # 停止コードの接頭辞を持たない値にする（停止の方針の台帳の走査が、テストの中のコードとして数えないように）
        def edit(spec):
            spec["examples"][2]["payload"]["code"] = "NOT_A_REAL_CODE_FOR_TEST"
            spec["examples"][2]["payload"]["case_id"] = "NOT_A_REAL_CODE_FOR_TEST#no-such-case"
        problems = self.broken(edit)
        self.assertTrue(any("NOT_A_REAL_CODE_FOR_TEST がエンジン" in p for p in problems), problems)
        self.assertTrue(any("no-such-case" in p for p in problems), problems)

    def test_broken_reference(self):
        def edit(spec):
            spec["existing"][0]["refs"].append("kyuura_engine/engine.py::no_such_function_for_test")
        self.assertTrue(any("no_such_function_for_test" in p for p in self.broken(edit)))

    def test_coin_as_replay_input(self):
        # v0.153: 記録の項目にコインの結果の行はない（コインは状態の確認値に入る）。コインの結果を入力の項目として加えると見つける
        def edit(spec):
            spec["records"][0]["fields"].append({"name": "operations[].coins", "required": False, "role": "input", "meaning": "x"})
        self.assertTrue(any("コイン" in p for p in self.broken(edit)))

    def test_secret_field_in_view_record(self):
        def edit(spec):
            spec["records"][1]["fields"].append({"name": "header.seed", "required": False, "role": "reference", "meaning": "x"})
        self.assertTrue(any("閲覧用記録" in p for p in self.broken(edit)))

    def test_cross_version_compare_cannot_succeed(self):
        def edit(spec):
            next(f for f in spec["replay_functions"] if f["id"] == "compare_runs")["results"].append("succeeded")
        self.assertTrue(any("compare_runs" in p for p in self.broken(edit)))

    def test_unit_cycle_and_unknown_dependency(self):
        def edit(spec):
            spec["units"][0]["depends"] = ["U7"]
            spec["units"][1]["depends"].append("U99")
        problems = self.broken(edit)
        self.assertTrue(any("循環" in p for p in problems), problems)
        self.assertTrue(any("U99" in p for p in problems), problems)

    def test_approval_cannot_be_recorded(self):
        # v0.152: 採用は adoptions の記録に範囲を限って書く。記録のない判断事項を adopted にする・単位を実装済みにする・仕様案全体を承認済みにすると見つける
        def edit(spec):
            spec["approval"] = "approved"
            # v0.156: 判断事項はすべて採用の記録つきになったので、記録のない判断事項をテストで加えて adopted にする
            spec["decisions"].append({"id": "D-TEST-ONLY", "question": "x", "options": ["x"], "recommendation": "x", "status": "adopted", "adopted": "x"})
            next(u for u in spec["units"] if u["status"] == "planned")["status"] = "implemented"
        problems = self.broken(edit)
        self.assertTrue(any("承認" in p for p in problems), problems)
        self.assertTrue(any("採用の記録（adoptions）にない" in p for p in problems), problems)
        self.assertTrue(any("採用の記録の単位と合わない" in p for p in problems), problems)

    def test_partial_unit_follows_its_parts(self):
        # v0.158: 部分の単位（parts）を持つ単位の全体の状態は部分から決まる（一部だけなら partial）。部分の状態は採用の記録（"U6/S1" の形）と合わせる
        def planned_whole(spec):
            next(u for u in spec["units"] if u["id"] == "U6")["status"] = "planned"
        self.assertTrue(any("全体の状態" in p for p in self.broken(planned_whole)))

        def unrecorded_part(spec):
            next(p for u in spec["units"] if u["id"] == "U6" for p in u["parts"] if p["status"] == "planned")["status"] = "implemented"
        problems = self.broken(unrecorded_part)
        self.assertTrue(any("部分" in p and "採用の記録の単位と合わない" in p for p in problems), problems)

        def unknown_part(spec):
            spec["adoptions"][-1]["units"].append("U6/S9")
        self.assertTrue(any("U6/S9" in p for p in self.broken(unknown_part)))

    def test_adopted_decision_without_record(self):
        def edit(spec):
            spec["adoptions"][0]["decisions"].remove("D-MESSAGE")
        self.assertTrue(any("D-MESSAGE" in p for p in self.broken(edit)))

    def test_new_version_key_cannot_reuse_existing_name(self):
        def edit(spec):
            spec["records"][2]["version_key"] = "format_version"
        self.assertTrue(any("format_version" in p for p in self.broken(edit)))

    def test_unknown_decision_reference(self):
        def edit(spec):
            spec["units"][0]["done"].append("D-NOT-DEFINED に従う")
        self.assertTrue(any("D-NOT-DEFINED" in p for p in self.broken(edit)))


class LedgerAgreementTest(unittest.TestCase):
    """分類の表のコードが、停止の方針の台帳で同じ意味のまま（台帳を書き換えたら気づく）。"""

    def test_compatibility_codes_are_runtime_codes(self):
        ledger = json.loads(B.LEDGER.read_text(encoding="utf-8"))
        entries = {e["id"]: e for e in ledger["entries"]}
        for code in written()["compatibility_codes"]:
            self.assertEqual(entries[code]["entry_kind"], "runtime_stop_code", code)
            self.assertEqual(entries[code]["status"], "active", code)

    def test_technical_limit_codes_in_the_ledger_are_category_b(self):
        ledger = json.loads(B.LEDGER.read_text(encoding="utf-8"))
        b_codes = {e["id"] for e in ledger["entries"] if e["entry_kind"] == "runtime_stop_code" and e.get("classification") == "B"}
        example_limits = {e["payload"]["diagnostic_id"] for e in written()["examples"] if e["payload"].get("category") == "technical_limit"}
        self.assertTrue(example_limits)
        self.assertLessEqual(example_limits, b_codes)


if __name__ == "__main__":
    unittest.main()
