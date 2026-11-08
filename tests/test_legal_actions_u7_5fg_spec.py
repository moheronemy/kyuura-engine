"""U7-5f・U7-5g の残件の監査と仕様（docs/legal-actions-u7-5fg-spec.md。調査と仕様だけ。実装はない）の確かめ。

- 3 段の入力の互換性（0.2 節）: 小さな既知の入力（エナジートランスの構築盤面）で、旧クライアントの 3 つの作りを試す（補助関数の確かめ）
- GUI の契約の表（kyuura-engine-gui 9c36a8f の contract/kyuura-client-api-v1.json の stage_keys。読み取りだけで写した値）が、新しい段の項目を知らない項目として見つける（安全な側の失敗）
- 仕様が書く今のコードの状態（残る経路がまだ候補にないこと・コマンドの項目・CheckFaceUpDeckCard の止め方）と、文書・生成した仕様の記述
"""

from __future__ import annotations

import dataclasses
import itertools
import json
import pathlib
import unittest

from kyuura_engine import faceup
from kyuura_engine import legal_actions as L
from kyuura_engine.commands import AttachEnergy, CheckFaceUpDeckCard
from kyuura_engine.engine import apply_command
from kyuura_engine.errors import IllegalActionError
from tests import helpers as H
from tests.test_legal_actions_u7_3 import cand, host_of
from tests.test_legal_actions_u7_5e import venusaur_board

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "legal-actions-u7-5fg-spec.md"
# kyuura-engine-gui 9c36a8f（feature/engine-u7-5-trainers-stadium。エンジン 0885d66 を固定）の契約の表の stage_keys（2026-11-08 に gh api で読み取りだけで写した）
GUI_9C36A8F_STAGE_KEYS = ["stage", "input", "role", "decision_kind", "meaning", "name", "count", "options", "options_from_stage", "distinct", "distinct_across_stages", "order",
                          "order_preserved", "decline", "note", "range", "remaining", "depends_on_stage", "options_by_choice", "total_units", "bench", "confused"]


def energy_trans():
    host = host_of(venusaur_board())
    session = host.session(0)
    r = session.candidates()
    c = cand(r, L.KIND_USE_POWER)
    return session, r, c, session.inputs(r["game"], r["revision"], c["id"])["stages"]


class ThreeStageCompatibilityTest(unittest.TestCase):
    """旧クライアントの作りごとの結果（docs 0.2 節の表）。"""

    def setUp(self):
        self.session, self.r, self.c, self.stages = energy_trans()

    def valid(self, path):
        return self.session.check(self.r["game"], self.r["revision"], self.c["id"], list(path))["valid"]

    def walk(self, key_of):
        paths = [[o["id"]] for o in self.stages[0]["options"] if o["eligible"]]
        for stage in self.stages[1:]:
            paths = [p + [ref["option"]] for p in paths for ref in stage["options_by_choice"].get(key_of(p, stage), []) if ref["eligible"]]
        return paths

    def test_generic_client_reaches_exactly_the_valid_paths(self):
        generic = self.walk(lambda path, stage: path[stage["depends_on_stage"] - 1])  # depends_on_stage が指す段の選ぶもので引く
        everything = [list(t) for t in itertools.product(*[[o["id"] for o in s["options"]] for s in self.stages])]
        valid = [p for p in everything if self.valid(p)]
        self.assertEqual(len(generic), 6)
        self.assertTrue(all(self.valid(p) for p in generic))
        self.assertEqual(sorted(map(tuple, generic)), sorted(map(tuple, valid)))

    def test_stage_one_keyed_client_fails_closed(self):
        self.assertEqual(self.walk(lambda path, stage: path[0]), [])  # U7-3 の 2 段を前提に、いつも 1 段目で引く: 組ができない（誤った組を作らない）

    def test_client_ignoring_options_by_choice_is_protected_by_the_server(self):
        everything = [list(t) for t in itertools.product(*[[o["id"] for o in s["options"]] for s in self.stages])]
        self.assertEqual(len(everything), 36)
        rejected = [p for p in everything if not self.valid(p)]
        self.assertEqual(len(rejected), 30)
        refusal = self.session.check(self.r["game"], self.r["revision"], self.c["id"], rejected[0])["refusal"]["code"]
        self.assertEqual(refusal, L.CANDIDATE_INPUT_INVALID)  # 安全はサーバの入力の検査による（クライアントの互換ではない）

    def test_gui_contract_table_stops_on_unknown_keys(self):
        unknown = sorted({key for stage in self.stages for key in stage} - set(GUI_9C36A8F_STAGE_KEYS))
        self.assertEqual(unknown, ["upstream_stages"])  # 知らない段の項目として止まる（安全な側の失敗）
        self.assertTrue(any("after" in option for stage in self.stages for option in stage["options"]))

    def test_shared_stage_two_ids_cannot_key_a_third_stage(self):
        """否定テスト: U7-3 の attach_energy のように 2 段目の番号が 1 段目によらず同じ形で、3 段目を 2 段目の番号だけで引こうとすると、段の形の確かめは通るが、2 段目の番号が
        上流（1 段目）の選び方を識別しないので、3 段目の続きを 1・2 段目の組ごとに分けられない（R-1 の 3 段目に新しい引き方が要る理由。D-U75-ENERGY2-SCHEMA）。"""
        stages = [{"stage": 1, "options": [{"id": "o1"}, {"id": "o2"}]},
                  {"stage": 2, "options": [{"id": "o3"}], "depends_on_stage": 1, "options_by_choice": {"o1": [{"option": "o3"}], "o2": [{"option": "o3"}]}},
                  {"stage": 3, "options": [{"id": "o4", "after": "o3"}], "depends_on_stage": 2, "upstream_stages": [1, 2], "options_by_choice": {"o3": [{"option": "o4"}]}}]
        self.assertEqual(L.stage_dependency_problems(stages), [])  # 形は通る: 2 段目の o3 は 1 段目の o1・o2 のどちらのあとかを識別しない
        self.assertEqual(len(stages[1]["options_by_choice"]), 2)  # o3 が 2 つの上流で共有される（3 段目の続きを上流の組ごとに分けられない）


class CurrentCodeTest(unittest.TestCase):
    """仕様が書く今のコードの状態（実装していないことの確かめ）。"""

    def test_command_fields(self):
        self.assertEqual([f.name for f in dataclasses.fields(CheckFaceUpDeckCard)], ["player", "owner", "position"])
        self.assertEqual([(f.name, f.default) for f in dataclasses.fields(AttachEnergy)][-1], ("energy2", None))

    def test_check_face_up_deck_is_never_accepted_and_ignores_the_turn(self):
        state = H.build_test_state([{"active": H.CHARMANDER, "deck": [H.FIRE] * 5}, {"active": H.CHARMANDER, "deck": [H.FIRE] * 5}], turn_number=3)
        for player in (0, 1):  # 番のプレイヤー（0）でも、番でないプレイヤー（1）でも同じ（番を確かめない）
            for owner, position in ((0, 1), (1, 1), (1, 0), (1, 99), (2, 1)):
                with self.assertRaises(IllegalActionError):
                    apply_command(state, CheckFaceUpDeckCard(player, owner, position))
        self.assertEqual(faceup.prefix_problems(state), [])  # おもてのカードは上から続く並び（不変条件）

    def test_residual_paths_are_not_offered_yet(self):
        r = host_of(venusaur_board()).session(0).candidates()
        self.assertEqual(r["coverage"]["not_covered_kinds"], [])  # v0.172: U7-5f は実装した（表示だけの種類。display_only_kinds）
        self.assertEqual(r["coverage"]["completeness"], L.PARTIAL)
        self.assertNotIn("residual", r["coverage"])  # 5.3 節の residual は未実装（推奨だけ）


class DocumentTest(unittest.TestCase):
    def test_document_and_spec(self):
        text = DOC.read_text(encoding="utf-8")
        for phrase in ("9c36a8fe033f32b589cd57721725fdcc13c318f3", "0885d664913bc8e57279ed9e44ac51cc97d5a6bf", "3649946", "CheckFaceUpDeckCard", "face_up_count", "FU2",
                       "energy2", "options_by_path", "R-1", "R-2", "residual", "unverified_paths", "PT-5e", "採用済み", "推奨", "判断待ち", "D-U75-FACE-UP-ACTORS",
                       "D-U75-ENERGY2-SCHEMA", "D-U75-FACE-DOWN-POWER", "D-U75-R2", "D-U7-COMPLETENESS"):
            self.assertIn(phrase, text)
        spec = json.loads((ROOT / "docs" / "legal-actions-u7-5-design.json").read_text(encoding="utf-8"))
        self.assertEqual((spec["gui_ref"]["commit"], spec["gui_ref"]["pinned_engine"]), ("9c36a8fe033f32b589cd57721725fdcc13c318f3", "0885d664913bc8e57279ed9e44ac51cc97d5a6bf"))
        needed = {d["id"] for d in spec["adoption_needed"]}
        self.assertLessEqual({"D-U75-FACE-UP-ACTORS", "D-U75-ENERGY2-SCHEMA", "D-U75-FACE-DOWN-POWER", "D-U75-R2"}, needed)
        self.assertEqual(next(u for u in spec["units"] if u["id"] == "U7-5f").get("status"), "implemented")  # v0.172: 採用のあとの作業（docs/legal-actions-u7-5fg.md）で実装した
        self.assertIn("CORR-3", {c["id"] for c in spec["adoption_record"]["corrections"]})


if __name__ == "__main__":
    unittest.main()
