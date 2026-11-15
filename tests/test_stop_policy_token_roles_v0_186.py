"""停止の方針の台帳: テスト・道具だけの語の役割（案 B。docs/test-only-token-design.md）。

- 分類（``build_stop_policy_classification.classify_test_only_tokens``）: スキャナの出現の種類・明示の登録（``scripts/stop_policy_token_roles.json``）・実在の停止コードの表から、
  役割（fixture・mutation_operand・historical_engine_code・non_code_identifier・unclassified）と状態（test_only・historical・unverified）を決め、矛盾・不足を問題にする
- 生成する台帳（``build()``）: schema_version 2、役割と根拠、役割ごとの数、場面の索引・設計案の場面から外れること、TR3 の記録と convention_note の修正が残ること
- 検査（``check``）: 未分類・矛盾は失敗。生成物の古さとは別の診断。旧台帳（schema 1）の読み取りは変えない

停止コードの形の文字列は ``tests/stop_policy_token_cases.json``（.py でないのでスキャナの走査の外）に置き、テストが一時の入力（メモリの上の出現の表・一時のフォルダの文書）へ展開する。
このファイルのソースには停止コードの形の文字列がない（テスト自身の言及が台帳を変えないことは ``RepositoryTest.test_this_test_adds_no_tokens`` で確かめる）。
"""

from __future__ import annotations

import copy
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_convention_records as R  # noqa: E402
import build_play_policy_family_plan as P  # noqa: E402
import build_stop_policy_classification as B  # noqa: E402
import stop_policy_scan as S  # noqa: E402

CASES = json.loads((ROOT / "tests" / "stop_policy_token_cases.json").read_text(encoding="utf-8"))
SYN = CASES["synthetic"]
TAGS = ("分類の入力の不足", "分類の矛盾", "分類の要確認", "分類の登録が古い")


def occ(**areas):
    """出現の表の 1 行（領域 → 種類 → 箇所）。"""
    return {"engine": areas.get("engine", {}), "tests": areas.get("tests", {}), "tools": areas.get("tools", {})}


class ClassifyTest(unittest.TestCase):
    """合成の出現の表と登録で、判定の順（docs/test-only-token-design.md 3 章）を確かめる。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "history.md").write_text(f"v0.1 では {SYN['historical']} で止めていた。v0.2 で外した。\n", encoding="utf-8")
        self.codes = {
            SYN["fixture"]: occ(tests={"literal": ["tests/t.py:1"]}),
            SYN["mutation"]: occ(tools={"literal": ["tools/mutants.py:3"]}),
            SYN["historical"]: occ(tests={"literal": ["tests/t.py:2"]}),
            SYN["identifier"]: occ(tools={"name": ["tools/v.py:4"]}, tests={"name": ["tests/t.py:5"]}),
            SYN["unclassified"]: occ(tests={"literal": ["tests/t.py:6"]}),
            SYN["engine_and_tests"]: occ(engine={"literal": ["kyuura_engine/e.py:1"]}, tests={"literal": ["tests/t.py:7"]}),
            SYN["moved_to_engine"]: occ(engine={"literal": ["kyuura_engine/e.py:2"]}, tests={"literal": ["tests/t.py:8"]}),
            SYN["note_only"]: occ(engine={"convention_note": ["kyuura_engine/c.py:3"]}, tests={"literal": ["tests/t.py:9"]}),
            SYN["real_but_absent"]: occ(tests={"literal": ["tests/t.py:10"]}),
        }
        self.registry = {
            SYN["fixture"]: {"role": "fixture", "basis": "テストの架空の値", "evidence": ["tests/t.py"]},
            SYN["mutation"]: {"role": "mutation_operand", "basis": "変異の値", "evidence": ["tools/mutants.py"], "paired_code": SYN["mutation_pair"]},
            SYN["historical"]: {"role": "historical_engine_code", "basis": "過去の実在のコード", "evidence": ["tests/t.py"], "removed_in": "v0.2 abc1234",
                                "documents": ["docs/history.md"]},
            SYN["moved_to_engine"]: {"role": "fixture", "basis": "架空の値だった", "evidence": ["tests/t.py"]},
        }
        self.real = {SYN["mutation_pair"], SYN["real_but_absent"]}

    def tearDown(self):
        self.tmp.cleanup()

    def classify(self, codes=None, registry=None):
        return B.classify_test_only_tokens(codes or self.codes, registry if registry is not None else self.registry, self.real, self.root)

    def test_roles_and_statuses(self):
        roles, _ = self.classify()
        expected = {SYN["fixture"]: ("fixture", "test_only"), SYN["mutation"]: ("mutation_operand", "test_only"),
                    SYN["historical"]: ("historical_engine_code", "historical"), SYN["identifier"]: ("non_code_identifier", "test_only"),
                    SYN["unclassified"]: ("unclassified", "unverified")}
        for token, (role, status) in expected.items():
            with self.subTest(token=token):
                self.assertEqual((roles[token]["role"], roles[token]["status"]), (role, status))
                self.assertTrue(roles[token]["basis"])

    def test_real_stop_codes_are_not_test_only(self):
        roles, problems = self.classify()
        self.assertNotIn(SYN["engine_and_tests"], roles)  # エンジンとテストの両方に出る実際の停止コード（テストの出現で開発用にしない）
        self.assertNotIn(SYN["moved_to_engine"], roles)  # 登録していても、止める箇所に出れば停止コードのまま
        self.assertTrue(any(p.startswith("分類の矛盾") and SYN["moved_to_engine"] in p for p in problems))

    def test_unclassified_is_kept_and_reported(self):
        roles, problems = self.classify()
        self.assertEqual(roles[SYN["unclassified"]]["status"], "unverified")
        self.assertTrue(any(p.startswith("分類の入力の不足") and SYN["unclassified"] in p for p in problems))

    def test_note_only_and_real_but_absent(self):
        roles, problems = self.classify()
        self.assertNotIn(SYN["note_only"], roles)  # convention_note は止める箇所にも開発用にも自動ではしない
        self.assertTrue(any(p.startswith("分類の要確認") and SYN["note_only"] in p for p in problems))
        self.assertEqual(roles[SYN["real_but_absent"]]["role"], "unclassified")  # 実在の停止コードの表にあるのにエンジンにない
        self.assertTrue(any(p.startswith("分類の矛盾") and SYN["real_but_absent"] in p for p in problems))

    def test_registration_conditions(self):
        broken = {
            "fixture_with_removal": {SYN["fixture"]: {**self.registry[SYN["fixture"]], "removed_in": "v9"}},
            "historical_without_documents": {SYN["historical"]: {k: v for k, v in self.registry[SYN["historical"]].items() if k != "documents"}},
            "historical_document_without_token": {SYN["historical"]: {**self.registry[SYN["historical"]], "documents": ["docs/missing.md"]}},
            "mutation_pair_not_real": {SYN["mutation"]: {**self.registry[SYN["mutation"]], "paired_code": SYN["unclassified"]}},
            "mutation_outside_mutants": {SYN["mutation"]: {**self.registry[SYN["mutation"]], "evidence": ["tests/t.py"]}},
            "evidence_without_occurrence": {SYN["fixture"]: {**self.registry[SYN["fixture"]], "evidence": ["tests/other.py"]}},
            "identifier_registered": {SYN["identifier"]: {"role": "fixture", "basis": "x", "evidence": ["tests/t.py"]}},
            "unknown_role": {SYN["fixture"]: {**self.registry[SYN["fixture"]], "role": "test_only"}},
            "no_basis": {SYN["fixture"]: {**self.registry[SYN["fixture"]], "basis": ""}},
            "stale": {SYN["stale"]: {"role": "fixture", "basis": "x", "evidence": ["tests/t.py"]}},
        }
        for name, change in broken.items():
            with self.subTest(name=name):
                registry = {**copy.deepcopy(self.registry), **change}
                _, problems = self.classify(registry=registry)
                token = next(iter(change))
                self.assertTrue(any(token in p and p.startswith(TAGS) for p in problems), problems)

    def test_valid_registry_has_only_expected_problems(self):
        _, problems = self.classify()
        flagged = {t for t in (SYN["unclassified"], SYN["moved_to_engine"], SYN["note_only"], SYN["real_but_absent"]) for p in problems if t in p}
        self.assertEqual(flagged, {SYN["unclassified"], SYN["moved_to_engine"], SYN["note_only"], SYN["real_but_absent"]})
        for token in (SYN["fixture"], SYN["mutation"], SYN["historical"], SYN["identifier"]):
            self.assertFalse([p for p in problems if token in p], token)


class RepositoryTest(unittest.TestCase):
    """今のリポジトリで作り直した台帳（書き出さない）。"""

    @classmethod
    def setUpClass(cls):
        cls.fresh = B.build()
        cls.entries = {e["id"]: e for e in cls.fresh["entries"]}
        cls.records = json.loads((ROOT / "kyuura_engine" / "data" / "convention_records.json").read_text(encoding="utf-8"))

    def test_schema_and_roles(self):
        self.assertEqual(self.fresh["schema_version"], 2)
        tokens = {i: e for i, e in self.entries.items() if e["entry_kind"] == "test_tool_only_code"}
        self.assertEqual({i: e["token_role"] for i, e in tokens.items()}, CASES["expected_roles"])
        for e in tokens.values():
            self.assertTrue(e["token_role_basis"], e["id"])
            self.assertEqual(e["status"], B.TOKEN_STATUS[e["token_role"]], e["id"])
        self.assertEqual(self.fresh["token_classification"]["problems"], [])

    def test_counts_match(self):
        counts = self.fresh["counts"]
        self.assertEqual(sum(counts["by_status"].values()), len(self.fresh["entries"]))
        self.assertEqual(sum(counts["test_tool_only_by_role"].values()), counts["test_tool_only_codes"])
        self.assertEqual(counts["by_status"]["test_only"], 11)
        self.assertNotIn("unverified", counts["test_tool_only_by_role"])

    def test_scene_index_and_plan(self):
        index = R.build(self.fresh, json.loads(R.ASSUMPTIONS.read_text(encoding="utf-8")))["scene_index"]
        ids = {s["id"] for s in index["scenes"]}
        self.assertFalse(ids & set(CASES["expected_roles"]))  # 開発用・過去のコード・識別子は場面の索引に入らない
        self.assertEqual(index["codes"], self.records["scene_index"]["codes"])  # 停止コード → 場面の対応は今と同じ
        for code in CASES["real_codes"]["tr3"] + CASES["real_codes"]["out_of_scope"]:
            self.assertIn(code, ids)
            self.assertEqual(self.entries[code]["status"], "active")
        self.assertFalse({s["id"] for s in P.scenes_from_ledger(self.fresh)} & set(CASES["expected_roles"]))

    def test_tr3_and_convention_note_kept(self):
        ids = {a["id"] for a in self.fresh["continuation_agreements"]["agreements"]}
        self.assertLessEqual({"AGR-PLAY-TR3-SET", "AGR-PLAY-TR3-GUST", "AGR-PLAY-TR3-SWITCH", "AGR-PLAY-TR3-POTION"}, ids)
        self.assertEqual(self.fresh["decision_status"]["DEC-USE-WITHOUT-EFFECT"]["status"], "partly_agreed")
        undamaged = CASES["real_codes"]["out_of_scope"][0]
        self.assertFalse([s for s in self.entries[undamaged]["implementation_sites"] if s.startswith("kyuura_engine/conventions.py")])

    def test_check_reports_classification_separately(self):
        fresh = copy.deepcopy(self.fresh)
        self.assertFalse([p for p in B.check(fresh, None) if p.startswith(TAGS)])
        token = next(i for i, e in self.entries.items() if e.get("token_role") == "fixture")
        broken = copy.deepcopy(fresh)
        entry = next(e for e in broken["entries"] if e["id"] == token)
        entry["token_role"], entry["status"] = "unclassified", "unverified"
        broken["token_classification"]["problems"] = [f"分類の入力の不足: {token}"]
        problems = B.check(broken, None)
        self.assertTrue(any(p.startswith("分類の入力の不足") and token in p for p in problems))  # 書き出したあとの --check でも自動で承認しない

    def test_old_schema_ledger_reading_unchanged(self):
        committed = json.loads(B.OUTPUT.read_text(encoding="utf-8"))
        # v0.187: 正式な台帳を schema 2 に同期した（0.186 の時点の期待「正式な台帳は旧形式のまま」から変えた）
        self.assertEqual(committed["schema_version"], 2)
        self.assertEqual(B.check(committed, None), [])
        self.assertEqual(R.build(committed, json.loads(R.ASSUMPTIONS.read_text(encoding="utf-8")))["scene_index"], self.records["scene_index"])
        # 旧形式（schema 1）の台帳には、分類の検査が何も足さない（形式の番号だけを 2 に書き換える移行はしない）
        old = copy.deepcopy(committed)
        old["schema_version"] = 1
        old.pop("token_classification", None)
        self.assertEqual(B.token_classification_problems(old), [])

    def test_this_test_adds_no_tokens(self):
        codes = S.prefixed_codes(ROOT)
        mine = [c for c, v in codes.items() for area in ("tests",) for sites in v[area].values() for s in sites
                if s.startswith("tests/test_stop_policy_token_roles_v0_186.py")]
        self.assertEqual(mine, [])  # 合成の語は .json の入力にあり、走査の対象の .py に出ない


if __name__ == "__main__":
    unittest.main()
