"""停止の方針の台帳の生成の道具: 規約の本文（除外の注記など）の停止コードの言及を止める箇所として数えない修正と、TR3 の採用の記録の入力（docs/stop-ledger-drift-audit.md 8 章）。

- 走査（``scripts/stop_policy_scan.py``）: エンジンの ``Convention(...)`` の呼び出しの中で ``scenes=`` の外にある停止コードの文字列は、種類 ``convention_note``（文字列の言及）にし、
  ``literal`` に数えない。``scenes=`` の中（規約の対象の場面の宣言）と、呼び出しの外の文字列は今までどおり ``literal``。コード名・ファイル名で分けない
- 生成の入力（``scripts/build_stop_policy_classification.py``）: TR3 の採用の記録（AGR-PLAY-TR3-*・DEC-USE-WITHOUT-EFFECT の状態・UPDATES の 0.186.0）。採用の日付・規約・場面は
  エンジンの登録（``kyuura_engine.conventions``）と照らす。厳密側の停止と対象外の未裁定は active のまま

台帳そのもの（docs/stop-policy-classification.json）は書き出さない（作り直した台帳の値は、作る関数 ``build()`` の戻り値で確かめる）。
"""

from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_stop_policy_classification as B  # noqa: E402
import stop_policy_scan as S  # noqa: E402
from kyuura_engine import conventions as C  # noqa: E402

UNDAMAGED = "UNRESOLVED_POTION_UNDAMAGED_TARGET"
TR3_CODES = ("UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH", "UNRESOLVED_SWITCH_WITHOUT_BENCH", "UNRESOLVED_POTION_WITHOUT_DAMAGE")

FAKE_CONVENTIONS = '''\
X = Convention("PC-FAKE", 1, "continuation", "user_agreed", "UNRESOLVED_FAKE_B は対象外の説明",
               content={"unchanged": ["UNRESOLVED_FAKE_B（受理のあとの未裁定。この規約の対象外）"], "also": "UNRESOLVED_FAKE_A を続ける"},
               scenes=("UNRESOLVED_FAKE_A",
                       "UNRESOLVED_FAKE_C"))
CODE = "UNRESOLVED_FAKE_D"
'''
FAKE_EFFECTS = '''\
def check(state):
    raise UnsupportedError("UNRESOLVED_FAKE_B", "本当の止める箇所")
'''


def sites(codes, code, kind="literal"):
    return sorted(codes.get(code, {}).get("engine", {}).get(kind, []))


class ScanTest(unittest.TestCase):
    """合成の木（一時フォルダ）で、規約の本文の言及と本当の止める箇所を分ける。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        for d in (S.ENGINE_DIR, *S.TEST_DIRS, *S.TOOL_DIRS):
            (root / d).mkdir(parents=True, exist_ok=True)
        (root / S.ENGINE_DIR / "conv.py").write_text(FAKE_CONVENTIONS, encoding="utf-8")
        (root / S.ENGINE_DIR / "eff.py").write_text(FAKE_EFFECTS, encoding="utf-8")
        (root / "tests" / "t.py").write_text('Convention("PC-T", 1, "c", "u", "s", content={"n": "UNRESOLVED_FAKE_B"})\n', encoding="utf-8")
        self.codes = S.prefixed_codes(root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_note_is_not_a_stop_site(self):
        self.assertEqual(sites(self.codes, "UNRESOLVED_FAKE_B"), ["kyuura_engine/eff.py:2"])  # 本当の止める箇所だけ
        self.assertEqual(sites(self.codes, "UNRESOLVED_FAKE_B", "convention_note"), ["kyuura_engine/conv.py:1", "kyuura_engine/conv.py:2"])

    def test_scenes_and_other_literals_are_kept(self):
        self.assertEqual(sites(self.codes, "UNRESOLVED_FAKE_A"), ["kyuura_engine/conv.py:3"])  # 規約の対象の場面の宣言
        self.assertEqual(sites(self.codes, "UNRESOLVED_FAKE_A", "convention_note"), ["kyuura_engine/conv.py:2"])  # 本文の言及は別に記録
        self.assertEqual(sites(self.codes, "UNRESOLVED_FAKE_C"), ["kyuura_engine/conv.py:4"])  # 複数の場面の一部が対象外の言及と混ざらない
        self.assertEqual(sites(self.codes, "UNRESOLVED_FAKE_D"), ["kyuura_engine/conv.py:5"])  # 呼び出しの外の定数はそのまま

    def test_tests_and_tools_are_unchanged(self):
        self.assertEqual(sorted(self.codes["UNRESOLVED_FAKE_B"]["tests"].get("literal", [])), ["tests/t.py:1"])  # エンジンの外は今までどおり


class RepositoryScanTest(unittest.TestCase):
    """今のエンジンのコードで、TR3 の除外の注記を数えず、規約の対象のコードと厳密側の止める箇所を保つ。"""

    @classmethod
    def setUpClass(cls):
        cls.codes = S.prefixed_codes(ROOT)

    def test_undamaged_target_note_not_counted(self):
        literal = sites(self.codes, UNDAMAGED)
        self.assertTrue(literal)
        self.assertFalse([s for s in literal if s.startswith("kyuura_engine/conventions.py")])
        self.assertTrue([s for s in literal if s.startswith("kyuura_engine/effects.py")])  # 本当の止める箇所は残る
        self.assertTrue([s for s in sites(self.codes, UNDAMAGED, "convention_note") if s.startswith("kyuura_engine/conventions.py")])

    def test_tr3_codes_keep_scene_and_stop_sites(self):
        for code in TR3_CODES:
            with self.subTest(code=code):
                literal = sites(self.codes, code)
                self.assertTrue([s for s in literal if s.startswith("kyuura_engine/conventions.py")])  # 場面の宣言（規約の対象）
                self.assertTrue([s for s in literal if s.startswith("kyuura_engine/effects.py")])  # 厳密側の止める箇所

    def test_earlier_scene_declarations_kept(self):
        self.assertTrue([s for s in sites(self.codes, "UNRESOLVED_POISON_CHANGE_ORDER") if s.startswith("kyuura_engine/conventions.py")])


class AdoptionRecordTest(unittest.TestCase):
    """TR3 の採用の記録（生成の入力）と、作り直した台帳の値。"""

    @classmethod
    def setUpClass(cls):
        cls.ledger = B.build()
        cls.entries = {e["id"]: e for e in cls.ledger["entries"]}

    def test_agreements_match_registration(self):
        agreements = {a["id"]: a for a in B.CONTINUATION_AGREEMENTS}
        expected = {"AGR-PLAY-TR3-SET": C.TR3_SET_ID, "AGR-PLAY-TR3-GUST": C.GUST_WITHOUT_OPPONENT_BENCH_ID, "AGR-PLAY-TR3-SWITCH": C.SWITCH_WITHOUT_BENCH_ID,
                    "AGR-PLAY-TR3-POTION": C.POTION_WITHOUT_DAMAGE_ID}
        for aid, name in expected.items():
            with self.subTest(aid=aid):
                a = agreements[aid]
                self.assertIn(f"{name}@1", a["statement"])
                self.assertEqual((a["source"]["by"], a["source"]["on"]), ("user", "2026-11-15"))
                self.assertIn("2026-11-15", C.CONVENTIONS[(name, 1)].content["adoption"] if name != C.TR3_SET_ID else C.TR3_ADOPTION)
                self.assertIn("公式", a["source"]["not_recorded_as"])
        for key, aid in zip(C.TR3_MEMBERS, ("AGR-PLAY-TR3-GUST", "AGR-PLAY-TR3-SWITCH", "AGR-PLAY-TR3-POTION")):
            (scene,) = C.CONVENTIONS[key].scenes
            self.assertTrue(agreements[aid]["reading"].startswith(scene))  # 採用の範囲の場面（登録と同じ）
        self.assertNotIn(UNDAMAGED, agreements["AGR-PLAY-TR3-POTION"]["reading"].split("。")[0])  # 対象外を範囲に入れない

    def test_generated_ledger_reflects_tr3(self):
        ids = {a["id"] for a in self.ledger["continuation_agreements"]["agreements"]}
        self.assertLessEqual({"AGR-PLAY-TR3-SET", "AGR-PLAY-TR3-GUST", "AGR-PLAY-TR3-SWITCH", "AGR-PLAY-TR3-POTION"}, ids)
        status = self.ledger["decision_status"]["DEC-USE-WITHOUT-EFFECT"]
        self.assertEqual((status["status"], status["agreements"]), ("partly_agreed", ["AGR-PLAY-TR3-GUST", "AGR-PLAY-TR3-SWITCH", "AGR-PLAY-TR3-POTION"]))
        self.assertIn("0.186.0", [u["version"] for u in self.ledger["updates"]])
        self.assertEqual(B.agreement_problems(self.ledger), [])

    def test_strict_and_out_of_scope_stay_active(self):
        for code in (*TR3_CODES, UNDAMAGED, "UNRESOLVED_LEAVE_LOCK_NO_EFFECT", "UNRESOLVED_MIND_GAMES_CHAOS_GYM_ORDER"):
            with self.subTest(code=code):
                self.assertEqual(self.entries[code]["status"], "active")
        self.assertFalse([s for s in self.entries[UNDAMAGED]["implementation_sites"] if s.startswith("kyuura_engine/conventions.py")])
        self.assertFalse([s for site in self.entries[UNDAMAGED]["current_stop"] for s in site["sites"] if s.startswith("kyuura_engine/conventions.py")])
        for code in TR3_CODES:
            self.assertTrue([s for s in self.entries[code]["implementation_sites"] if s.startswith("kyuura_engine/effects.py")], code)


if __name__ == "__main__":
    unittest.main()
