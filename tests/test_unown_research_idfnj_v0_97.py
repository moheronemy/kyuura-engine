"""v0.97（docs/unown-research-idfnj-v0.97.md 2 章・3 章）: 写しの元・研究の基準を kyuura 73a1690（研究 78d090c を取り込んだ main）に上げる移行。

移行は連鎖（ecb2d69 → 7d3f4ca → 73a1690）で、v0.69 の段の記録は書き換えない。kyuura がカードの画像で埋めたアンノーンI・D・F のルール文（台帳 FIX-neo2-023/025/026-RULES-TEXT-JA。
根拠 card_image_check）は、台帳の画像の記録（URL・sha256・取得日・カードの識別・確かめた範囲）と照らす。画像を読んだのは kyuura で、エンジンは画像・公式の書籍を見ていない。
kyuura の論点の事例のうちエンジンの裁定 id のないもの（kyuura_cases_without_engine_ruling）と、論点はあるが kyuura の未解決の一覧に行がない停止コード（issue_not_in_index）を確かめる。
"""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest
from collections import Counter

from kyuura_engine.cards import read_extract
from scripts import check_card_sources as cs
from tests import helpers as H

ROOT = pathlib.Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
DOC = ROOT / "docs" / "unown-research-idfnj-v0.97.md"
ECB, V069, NOW = "ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3", "73a169063463bbf7bcaa3137d70cbf9721d11534"
UNOWN_RULES = {"neo2-023": "FIX-neo2-023-RULES-TEXT-JA", "neo2-025": "FIX-neo2-025-RULES-TEXT-JA", "neo2-026": "FIX-neo2-026-RULES-TEXT-JA"}
RULE_TEXT = "「アンノーン」はデッキに4枚までしか入れることができません。"
OLD_CORRECTIONS = ("FIX-PMCG2-041-ATK0-NAME", "FIX-PMCG2-041-LEVEL", "FIX-PMCG2-046-ATK0-TEXT", "FIX-GD6-010-ATK1-DAMAGE", "FIX-SI-010-ATK1-NAME")


def extract_module():
    spec = importlib.util.spec_from_file_location("extract_v097", ROOT / "scripts" / "extract_kyuura_cards.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def research_module():
    from scripts import check_research_links as research

    return research


def needs_kyuura(test):
    return unittest.skipUnless((KYUURA / ".git").exists(), "../kyuura がない")(test)


class MigrationChainTest(unittest.TestCase):
    """移行の連鎖（写しの source_migrations・採用の記録の data_migrations）。過去の段の値は書き換えない。"""

    def test_pinned_commits_and_chain(self):
        module = extract_module()
        extract = read_extract()
        self.assertEqual((module.KYUURA_COMMIT, module.V0_69_KYUURA_COMMIT, module.PREVIOUS_KYUURA_COMMIT), (NOW, V069, ECB))
        self.assertEqual(module.migration_problems(), [])
        self.assertEqual([(s["id"], s["from"], s["to"]) for s in extract["source_migrations"]], [("v0.69", ECB, V069), ("v0.97", V069, NOW)])
        self.assertEqual([s["corrections"] for s in extract["source_migrations"]], [list(OLD_CORRECTIONS), list(UNOWN_RULES.values())])
        self.assertEqual((extract["source"]["commit"], extract["previous_source"]["commit"]), (NOW, ECB))
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        self.assertEqual((links["research_commit"], links["card_data_commit"], links["counts"]["kyuura_issues"]), (NOW, NOW, 72))

    def test_old_steps_and_records_are_not_rewritten(self):
        sources = cs.load_sources()
        first, second = sources["data_migrations"]
        self.assertEqual((first["from"], first["to"], first["on"], first["document"]), (ECB, V069, "2026-10-19", "docs/equivalent-non-pack-cards-v0.69.md"))
        self.assertEqual((second["from"], second["to"], second["on"], second["document"]), (V069, NOW, "2026-10-25", "docs/unown-research-idfnj-v0.97.md"))
        # v0.96 までの採用の記録の採用したときのデータのコミットは、v0.68 までの 378 件が ecb2d69、v0.69〜v0.96 の 700 件が 7d3f4ca（過去の原典照合のカードの記録 4 件はコミットなし）
        old = {card: r for card, r in sources["cards"].items() if card not in set(read_extract().get("pool_v0_97", ()))}
        self.assertEqual(Counter(r.get("kyuura_commit") for r in old.values()), {ECB: 378, V069: 700, None: 4})
        self.assertTrue(all(r["recorded_on"] <= "2026-10-24" for r in old.values() if "recorded_on" in r))
        # 外部照合の照らしたコミット・確認日も書き換えていない（移行の前のコミットか、今の写しのコミット。v0.97 の移行のあとの照合はない）
        checked = Counter(check["kyuura_commit"] for r in old.values() for check in r.get("external_checks", ()))
        self.assertLessEqual(set(checked), {ECB, V069})

    def test_data_migrations_rejects_a_broken_chain(self):
        extract = read_extract()
        sources = cs.load_sources()
        _, problems = cs.data_migrations(sources, extract)
        self.assertEqual(problems, [])

        def broken(change):
            changed = copy.deepcopy(sources)
            change(changed["data_migrations"])
            return cs.data_migrations(changed, extract)[1]

        self.assertTrue(any("つながっていない" in p for p in broken(lambda m: m[1].update({"from": ECB}))))  # 段を飛ばす
        self.assertTrue(any("source_migrations" in p for p in broken(lambda m: m[0].update({"to": NOW}))))  # 過去の段のあとだけを今の値にする
        self.assertTrue(any("段の数" in p for p in broken(lambda m: m.pop())))  # 2 段目がない
        self.assertTrue(any("前の段の日より前" in p for p in broken(lambda m: m[1].update({"on": "2026-10-18"}))))
        self.assertTrue(any("previous_source" in p for p in broken(lambda m: m.reverse())))
        chain, _ = cs.data_migrations(sources, extract)
        self.assertEqual((chain.position(ECB), chain.position(V069), chain.position(NOW)), (0, 1, 2))
        # 外部照合の照らしたコミットが修正の段の前なら、修正の前の値でもよい（v0.69 の段の修正は ecb2d69 の照合だけ。v0.97 の段の修正は 7d3f4ca の照合も前）
        self.assertTrue(cs._before_correction(chain, ECB, {"previous_source": ECB}))
        self.assertFalse(cs._before_correction(chain, V069, {"previous_source": ECB}))
        self.assertTrue(cs._before_correction(chain, V069, {"previous_source": V069}))
        self.assertFalse(cs._before_correction(chain, NOW, {"previous_source": V069}))

    def test_card_data_commit_helper_walks_back_one_step_at_a_time(self):
        data = {"card_data": {"commit": NOW}, "log": [{"kind": "game_created", "card_data_commit": NOW}]}
        self.assertEqual(H.with_card_data_commit_at(data, V069)["card_data"]["commit"], V069)
        back = H.with_card_data_commit_before_v0_69(data)
        self.assertEqual((back["card_data"]["commit"], back["log"][0]["card_data_commit"]), (ECB, ECB))
        self.assertEqual(data["card_data"]["commit"], NOW)  # 渡した値は変えない
        with self.assertRaises(AssertionError):
            H.with_card_data_commit_before_v0_69({"card_data": {"commit": V069}, "log": []})  # 今の写しの元でない値は置きかえない
        with self.assertRaises(AssertionError):
            H.with_card_data_commit_at(data, "0" * 40)


class UnownRulesCorrectionTest(unittest.TestCase):
    """kyuura がカードの画像で埋めたアンノーンI・D・F のルール文（根拠 card_image_check・種類 transcription_omission）。"""

    def test_recorded_corrections(self):
        extract = read_extract()
        found = {c["card_id"]: c for c in extract["kyuura_corrections"] if c["id"] in UNOWN_RULES.values()}
        self.assertEqual(set(found), set(UNOWN_RULES))
        for card, c in found.items():
            with self.subTest(card=card):
                self.assertEqual((c["id"], c["field"], c["before"], c["after"], c["basis"], c["kind"], c["migration"]),
                                 (UNOWN_RULES[card], "pokemon.rules_text.ja", None, RULE_TEXT, "card_image_check", "transcription_omission", "v0.97"))
                self.assertEqual((c["kyuura_saw_image"], c["engine_saw_image"], c["applied_in_source"], c["previous_source"]), (True, False, NOW, V069))
                self.assertEqual(len(c["evidence"]), 2)  # pcg-search.com・なぞのばしょの画像（独立した 2 枚の実物の照合とは数えない）
                self.assertTrue(all(e["image_url"].startswith("https://") and len(e["image_sha256"]) == 64 and e["accessed_on"] == "2026-10-24" for e in c["evidence"]))
                for key in ("record", "commit", "kyuura_record"):
                    self.assertNotIn(key, c)  # kyuura の照合の記録（CC-）・最新の説明（LD-）・修正のコミットを書かない
        old = {c["id"]: c for c in extract["kyuura_corrections"] if c["id"] in OLD_CORRECTIONS}
        self.assertEqual({(c["migration"], c["applied_in_source"], c["previous_source"]) for c in old.values()}, {("v0.69", V069, ECB)})

    @needs_kyuura
    def test_checks_pass_and_reject_wrong_records(self):
        module = extract_module()
        source = module.read_kyuura_cards(KYUURA)
        previous = json.loads(module._show(KYUURA, module.PREVIOUS_KYUURA_COMMIT, module.KYUURA_PATH).decode("utf-8"))
        pool = module.all_pool_cards() + module.REFERENCE_ONLY
        self.assertEqual(module.kyuura_correction_problems(KYUURA, source, previous, pool), [])
        self.assertEqual(module.migration_copy_problems(KYUURA, source, previous, pool), [])
        current = {card["id"]: card for card in source["cards"]}
        for card in UNOWN_RULES:
            self.assertEqual(current[card]["pokemon"]["rules_text"]["ja"], RULE_TEXT)  # 写しの元の値（生成する写しはこの値をそのまま写す）
            self.assertNotIn("pokemon.rules_text.ja", current[card]["data_gaps"])
        original = list(module.KYUURA_CORRECTIONS)
        index = next(i for i, c in enumerate(original) if c["id"] == UNOWN_RULES["neo2-023"])
        target = original[index]
        evidence = [dict(e) for e in target["evidence"]]
        cases = [
            ("前の写しの元", dict(target, before="ちがう文面")),
            ("当てはまっていない", dict(target, after="「アンノーン」はデッキに3枚までしか入れることができません。")),
            ("台帳の kind", dict(target, kind="transcription_error")),
            ("台帳の basis", dict(target, basis="kyuura_source_check", record="CC-neo2-023-P1", commit="0" * 40)),
            ("kyuura が画像を見た", dict(target, kyuura_saw_image=False)),
            ("kyuura が画像を見た", dict(target, engine_saw_image=True)),
            ("照合の記録（CC-）", dict(target, record="CC-neo2-023-P1")),
            ("画像（URL・sha256・取得日）と違う", dict(target, evidence=[dict(evidence[0], image_sha256="0" * 64), evidence[1]])),
            ("画像（URL・sha256・取得日）と違う", dict(target, evidence=evidence[:1])),
            ("台帳の決めた日", dict(target, decided_on="2026-10-23")),
            ("段 v0.69 のあと", dict(target, migration="v0.69")),
            ("KYUURA_MIGRATIONS にない", dict(target, migration="v0.98")),
        ]
        try:
            for expected, bad in cases:
                with self.subTest(expected=expected, bad={k: bad[k] for k in bad if bad.get(k) != target.get(k)}):
                    module.KYUURA_CORRECTIONS[:] = [*original[:index], bad, *original[index + 1:]]
                    self.assertTrue(any(expected in p for p in module.kyuura_correction_problems(KYUURA, source, previous, pool)),
                                    module.kyuura_correction_problems(KYUURA, source, previous, pool))
            # 台帳の修正を挙げていなければ、写しの組のカードの知らない修正として書き出さない（5 枚を写しの組に入れたとき）
            module.KYUURA_CORRECTIONS[:] = [c for c in original if c["id"] != UNOWN_RULES["neo2-023"]]
            self.assertTrue(any("挙げていない" in p for p in module.kyuura_correction_problems(KYUURA, source, previous, [*pool, "neo2-023"])))
            # 欠けの修正を当てはめずに段ごとに比べると、ルール文と欠けている欄の一覧の違いとして見つかる（修正のほかの欄の変化を見落とさない）
            module.KYUURA_CORRECTIONS[:] = [c for c in original if c["migration"] != "v0.97"]
            found = module.migration_copy_problems(KYUURA, source, previous, ["neo2-023"])
            self.assertTrue(any("neo2-023 の pokemon" in p for p in found) and any("neo2-023 の data_gaps" in p for p in found), found)
        finally:
            module.KYUURA_CORRECTIONS[:] = original
        self.assertEqual(module.migration_copy_problems(KYUURA, source, previous, ["neo2-023", "neo2-025", "neo2-026"]), [])
        # 移行の連鎖の段の値を、今の値に書き換えると止まる（過去の段のあとだけを 73a1690 にする）
        steps = module.KYUURA_MIGRATIONS
        try:
            module.KYUURA_MIGRATIONS = ({**steps[0], "to": NOW}, steps[1])
            self.assertTrue(module.migration_problems())
        finally:
            module.KYUURA_MIGRATIONS = steps


class ResearchCasesTest(unittest.TestCase):
    """kyuura の論点の事例のうちエンジンの裁定 id のないもの（kyuura_cases_without_engine_ruling）と、issue_not_in_index の停止コード。"""

    def setUp(self):
        self.links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))

    def test_cases_and_unindexed_codes(self):
        cases = self.links["kyuura_cases_without_engine_ruling"]["cases"]
        self.assertEqual(len(cases), 13)
        self.assertEqual(Counter(c["kyuura_issue"] for c in cases), {"UQ-EFFECT-AFTER-NO-DAMAGE": 1, "UQ-CARD-USE-WITHOUT-TARGET": 3, "UQ-NON-ATTACK-DAMAGE-MODIFIERS": 1,
                                                                   "UQ-SPEED-STAR-SCOPE": 3, "UQ-SELF-EXCLUDING-POWER-COPIES": 5})
        cv1 = self.links["stop_codes"]["UNRESOLVED_CONDUCTIVITY_MULTIPLE_SOURCES"]
        self.assertEqual((cv1["kyuura_issue"], cv1["kyuura_disposition"]), ("UQ-SELF-EXCLUDING-POWER-COPIES", "issue_not_in_index"))
        case = next(c for c in cases if c["card_id"] == "neo4-046")
        self.assertEqual(case["engine"], {"stop_codes": ["UNRESOLVED_CONDUCTIVITY_MULTIPLE_SOURCES"]})

    @needs_kyuura
    def test_check_passes_and_rejects_wrong_links(self):
        research = research_module()
        self.assertEqual(research.check(KYUURA), [])
        rulings = research.git_show(KYUURA, self.links["research_commit"], "data/sidecar/rulings.json")
        issues = {x["id"]: x for x in rulings["issues"]}
        from kyuura_engine.effects import DEFAULT_EFFECTS

        def problems(change):
            links = copy.deepcopy(self.links)
            change(links)
            return research.unlinked_case_problems(links, issues, DEFAULT_EFFECTS)

        def cases(links):
            return links["kyuura_cases_without_engine_ruling"]["cases"]

        self.assertEqual(problems(lambda links: None), [])
        self.assertTrue(any("kyuura だけ" in p for p in problems(lambda links: cases(links).pop())))  # 事例の見落とし
        self.assertTrue(any("対応表だけ" in p for p in problems(lambda links: cases(links).append(dict(cases(links)[0], card_id="PMCG1-001")))))
        # 登録しているカードを登録していないとしない。登録していないカードの対象を停止コードで止めるとしない
        self.assertTrue(any("登録されている" in p for p in problems(lambda links: next(c for c in cases(links) if c["card_id"] == "neo4-046").update(
            engine={"unregistered": True}))))
        # 停止コードの論点が事例の論点と違えば、engine_issue_differs を書く（CV1 を not_in_kyuura にもどすと、論点のないコードに結んだ事例になる）
        self.assertTrue(any("engine_issue_differs" in p for p in problems(lambda links: links["stop_codes"]["UNRESOLVED_CONDUCTIVITY_MULTIPLE_SOURCES"].update(
            kyuura_issue=None, kyuura_disposition="not_in_kyuura"))))
        # issue_not_in_index の停止コードは、kyuura の未解決の一覧にない・論点がある・事例に結ばれていることを確かめる（集合の比べを緩めない）
        links = copy.deepcopy(self.links)
        next(c for c in cases(links) if c["card_id"] == "neo4-046")["engine"] = {"unregistered": True}
        self.assertTrue(any("結んだ kyuura の事例" in p for p in research.check(KYUURA, links=links)))
        links = copy.deepcopy(self.links)
        links["stop_codes"]["UNRESOLVED_POWER_ZERO_CARDS"]["kyuura_disposition"] = "issue_not_in_index"
        self.assertTrue(any("kyuura の未解決の一覧にある" in p for p in research.check(KYUURA, links=links)))


class DocumentTest(unittest.TestCase):
    def test_migration_chapters(self):
        text = DOC.read_text(encoding="utf-8")
        for word in ("73a169063463bbf7bcaa3137d70cbf9721d11534", "78d090c329aca58c4b5fbaefa2a1e5c089433b58", "KYUURA_MIGRATIONS", "source_migrations", "card_image_check",
                     "transcription_omission", "issue_not_in_index", "kyuura_cases_without_engine_ruling", "UQ-SELF-EXCLUDING-POWER-COPIES", "with_card_data_commit_at"):
            self.assertIn(word, text)
        provenance = (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8")
        self.assertIn("## v0.97: 写しの元・研究の基準を kyuura 73a1690 に上げる移行", provenance)


if __name__ == "__main__":
    unittest.main()
