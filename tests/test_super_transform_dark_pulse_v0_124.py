"""v0.124（docs/super-transform-dark-pulse-v0.124.md）: 写しの元・研究の基準の移行（kyuura 74b3ceb → b9e7cff。写しの外のメタモン ES2-032 の文面の 1 字の訂正）。

2 章: 移行だけの段。kyuura が同じカードの画像で確かめて直した ES2-032 の pokemon.powers[0].text.ja の「カ」→「力」（訂正の種類は転記の誤り ``transcription_error``）を写しの移行の段
v0.124 で受け付け、採用の記録・研究の対応表をそろえる。エンジンは画像を見ていない（kyuura の画像の照合を再利用しただけ）。この段ではカードを登録せず、処理も変えない。
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import unittest

from kyuura_engine.cards import load_card_pool, read_extract
from scripts import check_card_sources as cs
from scripts import check_research_links as rl
from tests import helpers as H
from tests.test_baby_rules_evolution_v0_114 import extract_module

ROOT = pathlib.Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
LINKS_PATH = ROOT / "kyuura_engine" / "data" / "research_links.json"
NOW, V0123 = "b9e7cff6d2b2c6b4539ec45e61bf453879adab3a", "74b3ceb883dd815495d13b9987433fb14b36e44d"
RESEARCH_LAST = "9731354f7e5c6bca08c88bbe98f9449ae96ea7a7"  # kyuura の研究の最後のコミット（b9e7cff と木が同じ）
ECB, V069, V097, V0114, V0121 = ("ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3", "73a169063463bbf7bcaa3137d70cbf9721d11534",
                                 "e519b99e2adcc6c2cd0998569ae5ee1101de6e89", "2fe0bc042ce187d191843819262f8036abbb343d")
BASE_ENGINE = "84bf94f013238472c34687533f8aec3018797cc9"  # この版の基点（main。木は v0.123 の最後 25552b8 と同じ）
DITTO, GR_MEWTWO, CLASSIC_DITTO = "ES2-032", "PRN-041", "PMCG3-042"
FIX = "FIX-ES2-032-POWER0-TEXT-JA"
NEW_ISSUES = ("UQ-TRANSFORM-ENERGY-COLOR-LIST", "UQ-SUPER-TRANSFORM-TARGETS", "UQ-SUPER-TRANSFORM-SOURCE-CHANGES", "UQ-SUPER-TRANSFORM-COPIED-POWERS",
              "UQ-SUPER-TRANSFORM-SUPPRESSED-FORM", "UQ-SUPER-TRANSFORM-ENERGY-COLORS", "UQ-TRANSFORM-REVERT-KNOCKOUT-TIMING", "UQ-TRANSFORM-BABY-AND-BASIC",
              "UQ-DARK-PULSE-TIMING")
MIGRATION_TAG = "v0.124 で研究の基準を b9e7cff に上げて結んだ"


def needs_kyuura(test):
    return unittest.skipUnless((KYUURA / ".git").exists(), "../kyuura がない")(test)


def needs_history(test):
    return unittest.skipUnless((ROOT / ".git").exists(), "このリポジトリの git の履歴がない（取り出した木）")(test)


def kyuura_json(commit: str, path: str):
    return json.loads(subprocess.check_output(["git", "-C", str(KYUURA), "show", f"{commit}:{path}"]))


def engine_json(commit: str, path: str):
    return json.loads(subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"]))


# ---------------------------------------------------------------- 2 章: 移行

class MigrationChainTest(unittest.TestCase):
    """2.1 節: 段 v0.124（74b3ceb → b9e7cff）。過去の段の値・採用の記録の移行は書き換えない。"""

    def test_chain(self):
        module = extract_module()
        self.assertEqual((module.KYUURA_COMMIT, module.V0_123_KYUURA_COMMIT, module.V0_121_KYUURA_COMMIT), (NOW, V0123, V0121))
        self.assertEqual(module.migration_problems(), [])
        self.assertEqual([(s["id"], s["from"], s["to"]) for s in module.KYUURA_MIGRATIONS],
                         [("v0.69", ECB, V069), ("v0.97", V069, V097), ("v0.114", V097, V0114), ("v0.121", V0114, V0121), ("v0.123", V0121, V0123),
                          ("v0.124", V0123, NOW)])
        self.assertEqual(module.KYUURA_MIGRATIONS[-1]["document"], "docs/super-transform-dark-pulse-v0.124.md")
        extract = read_extract()
        self.assertEqual((extract["source"]["commit"], extract["previous_source"]["commit"]), (NOW, ECB))
        self.assertEqual(extract["source_migrations"][-1]["corrections"], [FIX])
        # v0.123 の段のあとを写しの元の定数にもどすと、写しの元を上げたときに過去の段のあとまで変わる（連鎖が切れて止まる）
        steps = module.KYUURA_MIGRATIONS
        try:
            module.KYUURA_MIGRATIONS = (*steps[:4], {**steps[4], "to": module.KYUURA_COMMIT}, steps[5])
            self.assertTrue(any("その前の段のあと" in p for p in module.migration_problems()))
        finally:
            module.KYUURA_MIGRATIONS = steps

    def test_adoption_migrations_are_appended(self):
        sources = cs.load_sources()
        self.assertEqual([(m["from"], m["to"], m["on"]) for m in sources["data_migrations"]],
                         [(ECB, V069, "2026-10-19"), (V069, V097, "2026-10-25"), (V097, V0114, "2026-10-28"), (V0114, V0121, "2026-10-30"),
                          (V0121, V0123, "2026-10-31"), (V0123, NOW, "2026-10-31")])
        self.assertEqual(sources["data_migrations"][-1]["document"], "docs/super-transform-dark-pulse-v0.124.md")
        self.assertEqual(cs.data_migrations(sources, read_extract())[1], [])
        # 採用したときのデータのコミットが b9e7cff の記録は、この版で写しに加えたカード（pool_v0_124）だけ（移行の段では採用し直していない）
        self.assertEqual({card for card, record in sources["cards"].items() if record.get("kyuura_commit") == NOW}, set(read_extract().get("pool_v0_124", ())))

    def test_correction_in_the_extract(self):
        corrections = {c["id"]: c for c in read_extract()["kyuura_corrections"] if c["migration"] == "v0.124"}
        self.assertEqual(sorted(corrections), [FIX])
        c = corrections[FIX]
        self.assertEqual((c["card_id"], c["field"], c["basis"], c["kind"], c["image_check"], c["decided_on"]),
                         (DITTO, "pokemon.powers[0].text.ja", "card_image_check", "transcription_error", "IMG-ES2-032", "2026-10-31"))
        self.assertEqual((c["kyuura_saw_image"], c["engine_saw_image"], c["applied_in_source"], c["previous_source"]), (True, False, NOW, V0123))
        self.assertFalse({"record", "commit", "kyuura_record"} & set(c))  # CC-・LD- の照合の記録ではない（公式エラッタ・最新の説明とも混ぜない）
        # 前とあとの違いは「カ」→「力」の 1 字だけ（括弧・句読点を整形しない）
        before, after = c["before"], c["after"]
        self.assertEqual(len(before), len(after))
        diff = [(i, x, y) for i, (x, y) in enumerate(zip(before, after)) if x != y]
        self.assertEqual([(x, y) for _, x, y in diff], [("カ", "力")])
        self.assertIn("この「すごいへんしん」の力は使えず", after)
        self.assertIn("(ただし「進化・退化」はできず", after)  # 半角の括弧のまま

    @needs_history
    def test_extract_is_unchanged_for_the_base_cards(self):
        """基点の写しの 1,358 枚（と参照のカード）は同じ値。変わったのは写しの元の記録と、移行の段・訂正の一覧だけ。"""
        before = engine_json(BASE_ENGINE, "kyuura_engine/data/kyuura_cards.json")
        now = read_extract()
        old = {card["id"]: card for card in before["cards"]}
        new = {card["id"]: card for card in now["cards"]}
        self.assertLessEqual(set(old), set(new))
        self.assertEqual({card for card in old if old[card] != new[card]}, set())
        self.assertNotIn(DITTO, old)

    @needs_kyuura
    def test_kyuura_difference_is_one_character(self):
        """74b3ceb → b9e7cff の data/cards.json 全 1,377 件: 値が変わったのは未登録の ES2-032 の pokemon・notes・corrections だけ。pokemon の中では特殊能力の文面の 1 字だけ。"""
        old, new = (kyuura_json(commit, "data/cards.json") for commit in (V0123, NOW))
        self.assertEqual({k: v for k, v in old.items() if k != "cards"}, {k: v for k, v in new.items() if k != "cards"})
        self.assertEqual([c["id"] for c in old["cards"]], [c["id"] for c in new["cards"]])
        self.assertEqual(len(new["cards"]), 1377)
        before = {c["id"]: c for c in old["cards"]}
        changed = {c["id"]: {k for k in set(c) | set(before[c["id"]]) if c.get(k) != before[c["id"]].get(k)} for c in new["cards"] if c != before[c["id"]]}
        self.assertEqual(changed, {DITTO: {"pokemon", "notes", "corrections"}})
        after = {c["id"]: c for c in new["cards"]}
        module = extract_module()
        used = [f for f in module.FIELDS_USED_BY_ENGINE if "[" not in f and module.field_or_absent(before[DITTO], f) != module.field_or_absent(after[DITTO], f)]
        self.assertEqual(used, ["pokemon.powers"])
        self.assertEqual({k: v for k, v in before[DITTO]["pokemon"].items() if k != "powers"}, {k: v for k, v in after[DITTO]["pokemon"].items() if k != "powers"})
        self.assertEqual(before[GR_MEWTWO], after[GR_MEWTWO])  # GR団のミュウツーの値は同じ（公式大会の補足の文は play_scope を変えていない）
        self.assertEqual(after[GR_MEWTWO].get("play_scope"), "standard")


class SameStepCardCheckTest(unittest.TestCase):
    """2.2 節: 同じ段で kyuura が作った照合の記録（CC-ES2-032-P239）が、訂正のあとの値で同じ欄を照らしているときの受け付け。画像の照合を CC- の代わりにしたことにはしない。"""

    @needs_kyuura
    def test_ledger_and_image_checks(self):
        module = extract_module()
        source = module.read_kyuura_cards(KYUURA)
        previous = json.loads(module._show(KYUURA, module.PREVIOUS_KYUURA_COMMIT, module.KYUURA_PATH).decode("utf-8"))
        pool = module.all_pool_cards() + module.REFERENCE_ONLY
        self.assertEqual(module.kyuura_correction_problems(KYUURA, source, previous, pool), [])
        original = list(module.KYUURA_CORRECTIONS)
        index = next(i for i, c in enumerate(original) if c["id"] == FIX)

        def problems_with(**changes):
            module.KYUURA_CORRECTIONS[:] = [*original[:index], {**original[index], **changes}, *original[index + 1:]]
            try:
                return module.kyuura_correction_problems(KYUURA, source, previous, pool)
            finally:
                module.KYUURA_CORRECTIONS[:] = original

        # 種類を生成の値の誤りに書きかえると台帳と合わない。画像の照合の記録・画像が違えば受け付けない
        self.assertTrue(any("台帳の kind" in p for p in problems_with(kind="generated_value_error")))
        self.assertTrue(any("画像の照合の記録" in p for p in problems_with(image_check="IMG-PRN-041")))
        self.assertTrue(any("evidence" in p for p in problems_with(evidence=[dict(original[index]["evidence"][0], image_sha256="0" * 64)])))
        # 段が違えば受け付けない（v0.123 の段の訂正にしない）
        self.assertTrue(any("移行の段 v0.123" in p for p in problems_with(migration="v0.123")))
        # あとの値を前の値にすると、同じ段の照合の記録の値とも違う（照合の記録を画像の確認の代わりにしない確かめが、もう一度はたらく）
        self.assertTrue(any("CC-" in p for p in problems_with(after=original[index]["before"])))


class AdoptionRecordTest(unittest.TestCase):
    """2.3 節: 採用の記録。登録済みのカードの kyuura_records に、新しい裁定・論点の id を加えた。採用したときのコミット・日付は書き換えない。"""

    def test_records_added_by_the_research_commit(self):
        cards = cs.load_sources()["cards"]
        for card_id, added in H.V0_124_KYUURA_RECORDS_ADDED.items():
            self.assertLessEqual(set(added), set(cards[card_id]["kyuura_records"]), card_id)
            self.assertNotEqual(cards[card_id]["kyuura_commit"], NOW, card_id)
        self.assertEqual(len(H.V0_124_KYUURA_RECORDS_ADDED), 21)
        self.assertEqual(len(H.V0_124_KYUURA_RECORDS_ADDED[CLASSIC_DITTO]), 12)


class ResearchLinksTest(unittest.TestCase):
    """2.4 節: 研究の対応表。論点 79 → 88。研究の論点の数を停止コード・未解決の数にそろえない。"""

    @classmethod
    def setUpClass(cls):
        cls.links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))

    def test_commits_and_counts(self):
        links = self.links
        self.assertEqual((links["research_commit"], links["card_data_commit"], links["research_branch"]), (NOW, NOW, "main"))
        self.assertEqual(links["counts"]["kyuura_issues"], 88)
        # すごいへんしんの最新の説明は、登録するまで「登録のない kyuura の最新の説明」（v0.123 までは空）
        registered = DITTO in load_card_pool().playable_ids
        self.assertEqual(links["latest_descriptions"]["kyuura_records_not_registered"], [] if registered else ["LD-ES2-032-PWR0"])

    def test_new_cases_cover_the_new_issues(self):
        added = [c for c in self.links["kyuura_cases_without_engine_ruling"]["cases"] if MIGRATION_TAG in c.get("note", "")]
        self.assertEqual({c["kyuura_issue"] for c in added}, set(NEW_ISSUES))
        self.assertEqual(len(added), 31)

    def test_energy_registration_counts_as_card_target(self):
        from kyuura_engine.effects import DEFAULT_EFFECTS

        self.assertIn("card", rl._registered_targets(DEFAULT_EFFECTS, "PMCG1-096"))  # 無色2個エネルギー（特殊エネルギーの登録）
        self.assertIn("card", rl._registered_targets(DEFAULT_EFFECTS, "PMCG4-065"))  # レインボーエネルギー
        self.assertEqual(rl._registered_targets(DEFAULT_EFFECTS, "neo1-049"), set())  # 登録していないカード

    @needs_kyuura
    def test_links_agree_with_kyuura(self):
        self.assertEqual(rl.check(KYUURA), [])

    @needs_kyuura
    def test_research_commit_tree_is_the_research_branch(self):
        trees = [subprocess.check_output(["git", "-C", str(KYUURA), "rev-parse", f"{c}^{{tree}}"]).strip() for c in (NOW, RESEARCH_LAST)]
        self.assertEqual(trees[0], trees[1])
        rulings = kyuura_json(NOW, "data/sidecar/rulings.json")
        statuses = {}
        for ruling in rulings["rulings"]:
            statuses[ruling["status"]] = statuses.get(ruling["status"], 0) + 1
        self.assertEqual((len(rulings["rulings"]), statuses.get("CONFIRMED"), statuses.get("SUPPORTED")), (337, 237, 100))
        self.assertEqual(len(rulings["issues"]), 88)
        self.assertEqual(len(rulings["rule_clauses"]), 41)


if __name__ == "__main__":
    unittest.main()
