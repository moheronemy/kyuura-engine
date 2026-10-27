"""v0.114（docs/baby-rules-evolution-v0.114.md）: 写しの元・研究の基準の移行（73a1690 → e519b99）。

2 章: 移行は連鎖（ecb2d69 → 7d3f4ca → 73a1690 → e519b99）で、v0.69・v0.97 の段の記録は書き換えない（v0.97 の段のあとは 73a1690 に固定した）。73a1690 → e519b99 の data/cards.json で
値が変わったのはベイビィ 13 枚だけで、写しの 1,250 枚の値は v0.113 と同じ。研究の基準の新しい条項・裁定・論点（UQ-NEO-TEXT-BABY-CATEGORIES）・事例を研究の対応表に結ぶ。
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import unittest
from collections import Counter

from kyuura_engine.cards import read_extract
from scripts import check_card_sources as cs
from tests import helpers as H

ROOT = pathlib.Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
DOC = ROOT / "docs" / "baby-rules-evolution-v0.114.md"
ECB, V069, V097, V0114 = ("ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3", "73a169063463bbf7bcaa3137d70cbf9721d11534",
                          "e519b99e2adcc6c2cd0998569ae5ee1101de6e89")
V0113 = "2d113b5eeea0dbd4f7466e144f7a1345494405c0"  # 確認済みの完成版（固定した v0.113）
BABIES = ("neo1-022", "neo1-042", "neo1-044", "neo1-070", "neo2-033", "neo2-050", "neo3-031", "PF2-007", "NIP1X-002", "NIP2X-002", "PRN-012", "PRN-031", "PRN-037")
RULE_FILLED = BABIES[:6]  # ルール文を kyuura が画像で埋めた neo 第1〜2弾の 6 枚
LINKS_PATH = ROOT / "kyuura_engine" / "data" / "research_links.json"


def extract_module():
    spec = importlib.util.spec_from_file_location("extract_v0114", ROOT / "scripts" / "extract_kyuura_cards.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def needs_kyuura(test):
    return unittest.skipUnless((KYUURA / ".git").exists(), "../kyuura がない")(test)


def needs_history(test):
    return unittest.skipUnless((ROOT / ".git").exists(), "このリポジトリの git の履歴がない（取り出した木）")(test)


def kyuura_json(commit: str, path: str):
    return json.loads(subprocess.check_output(["git", "-C", str(KYUURA), "show", f"{commit}:{path}"]))


class MigrationTest(unittest.TestCase):
    """2 章: 写しの元・研究の基準を e519b99 に上げる移行（カードの登録・挙動は変えない）。"""

    def test_chain_and_fixed_old_steps(self):
        module = extract_module()
        self.assertEqual((module.KYUURA_COMMIT, module.V0_97_KYUURA_COMMIT, module.V0_69_KYUURA_COMMIT, module.PREVIOUS_KYUURA_COMMIT), (V0114, V097, V069, ECB))
        self.assertEqual(module.migration_problems(), [])
        self.assertEqual([(s["id"], s["from"], s["to"], s["document"]) for s in module.KYUURA_MIGRATIONS],
                         [("v0.69", ECB, V069, "docs/equivalent-non-pack-cards-v0.69.md"), ("v0.97", V069, V097, "docs/unown-research-idfnj-v0.97.md"),
                          ("v0.114", V097, V0114, "docs/baby-rules-evolution-v0.114.md")])
        extract = read_extract()
        self.assertEqual([(s["id"], s["from"], s["to"]) for s in extract["source_migrations"]], [(s["id"], s["from"], s["to"]) for s in module.KYUURA_MIGRATIONS])
        self.assertEqual((extract["source"]["commit"], extract["previous_source"]["commit"]), (V0114, ECB))
        # v0.97 の段のあとを写しの元の定数にもどすと、写しの元を上げたときに過去の段のあとまで変わる（連鎖が切れて止まる）
        steps = module.KYUURA_MIGRATIONS
        try:
            module.KYUURA_MIGRATIONS = (steps[0], {**steps[1], "to": module.KYUURA_COMMIT}, steps[2])
            self.assertTrue(any("その前の段のあと" in p for p in module.migration_problems()))
        finally:
            module.KYUURA_MIGRATIONS = steps
        # 利用者が示した PR1-069 の名前の訂正は、今の写しの元でも同じ値（kyuura はまだ直していない）
        self.assertEqual([(c["card_id"], c["field"], c["before"], c["after"], c["source_commit"]) for c in extract["engine_user_corrections"]],
                         [("PR1-069", "name.ja", "？？？", "ミュウ", V0114)])

    def test_adoption_records_are_not_rewritten(self):
        sources = cs.load_sources()
        migrations = sources["data_migrations"]
        self.assertEqual([(m["from"], m["to"], m["on"], m["document"]) for m in migrations],
                         [(ECB, V069, "2026-10-19", "docs/equivalent-non-pack-cards-v0.69.md"), (V069, V097, "2026-10-25", "docs/unown-research-idfnj-v0.97.md"),
                          (V097, V0114, "2026-10-28", "docs/baby-rules-evolution-v0.114.md")])
        self.assertEqual(cs.data_migrations(sources, read_extract())[1], [])
        # 採用したときのデータのコミットは書き換えない（v0.113 までの 1,163 件。過去の原典照合のカードの記録 4 件はコミットなし）
        old = {card: record for card, record in sources["cards"].items() if card not in BABIES}
        self.assertEqual(Counter(r.get("kyuura_commit") for r in old.values()), {ECB: 378, V069: 700, V097: 81, None: 4})

    @needs_history
    def test_extract_cards_are_the_v0_113_cards(self):
        """写しの 1,250 枚（v0.113 の写しのカード）の値は、写しの元を上げても変わらない（固定した v0.113 の写しと比べる）。"""
        before = json.loads(subprocess.check_output(["git", "-C", str(ROOT), "show", f"{V0113}:kyuura_engine/data/kyuura_cards.json"]))
        now = {card["id"]: card for card in read_extract()["cards"]}
        self.assertEqual(len(before["cards"]), 1250)
        for card in before["cards"]:
            self.assertEqual(now[card["id"]], card, card["id"])
        self.assertEqual((before["equivalent_targets"], before["reprint_targets"]), (read_extract()["equivalent_targets"], read_extract()["reprint_targets"]))

    def test_research_links(self):
        links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
        self.assertEqual((links["research_commit"], links["card_data_commit"], links["research_branch"], links["engine_import_id"]),
                         (V0114, V0114, "claude/baby-data-engine-v0113-handover", "ENGINE-46A3E2E"))
        cases = [c for c in links["kyuura_cases_without_engine_ruling"]["cases"]
                 if c["kyuura_issue"] == "UQ-NEO-TEXT-BABY-CATEGORIES" or (c["kyuura_issue"], c["card_id"]) == ("UQ-ATTACK-PRE-DAMAGE-COIN-ORDER", "neo1-042")]
        self.assertEqual(sorted((c["kyuura_issue"], c["card_id"], c["target"]) for c in cases),
                         [("UQ-ATTACK-PRE-DAMAGE-COIN-ORDER", "neo1-042", "card"), ("UQ-NEO-TEXT-BABY-CATEGORIES", "NIP1-021", "trainer"),
                          ("UQ-NEO-TEXT-BABY-CATEGORIES", "neo1-074", "trainer"), ("UQ-NEO-TEXT-BABY-CATEGORIES", "neo2-056", "trainer"),
                          ("UQ-NEO-TEXT-BABY-CATEGORIES", "neo3-049", "attack/0"), ("UQ-NEO-TEXT-BABY-CATEGORIES", "neo3-056", "trainer"),
                          ("UQ-NEO-TEXT-BABY-CATEGORIES", "neo4-038", "attack/0")])
        sources = cs.load_sources()["cards"]
        added = {"PMCG1-086": "CR-DEVOLUTION-SPRAY-EVOLVED-BABY", "PR1-005": "CR-NEUTRAL-SHIELD-EVOLVED-BABY", "PR1-012": "CR-NEUTRAL-SHIELD-EVOLVED-BABY",
                 "neo1-074": "UQ-NEO-TEXT-BABY-CATEGORIES", "neo2-056": "UQ-NEO-TEXT-BABY-CATEGORIES", "neo3-056": "UQ-NEO-TEXT-BABY-CATEGORIES",
                 "NIP1-021": "UQ-NEO-TEXT-BABY-CATEGORIES"}
        self.assertEqual({card: (record,) for card, record in added.items()}, H.V0_114_KYUURA_RECORDS_ADDED)
        for card, record in added.items():
            self.assertIn(record, sources[card]["kyuura_records"], card)
            self.assertLess(sources[card]["recorded_on"], "2026-10-28", card)  # 記録を読み直したのではなく、id の対応を直した（記録した日は変えない）

    @needs_kyuura
    def test_kyuura_difference_is_only_the_thirteen_babies(self):
        """73a1690 → e519b99 の data/cards.json の全 1,377 件: 値が変わったのはベイビィ 13 枚だけ（6 枚のルール文・13 枚の進化先・notes・corrections・data_gaps）。"""
        old, new = (kyuura_json(commit, "data/cards.json") for commit in (V097, V0114))
        self.assertEqual({k: v for k, v in old.items() if k != "cards"}, {k: v for k, v in new.items() if k != "cards"})
        self.assertEqual([c["id"] for c in old["cards"]], [c["id"] for c in new["cards"]])
        self.assertEqual(len(new["cards"]), 1377)
        before = {c["id"]: c for c in old["cards"]}
        changed = {c["id"]: {f for f in set(c) | set(before[c["id"]]) if c.get(f) != before[c["id"]].get(f)} for c in new["cards"] if c != before[c["id"]]}
        self.assertEqual(set(changed), set(BABIES))
        for card, fields in changed.items():
            self.assertEqual(fields, {"pokemon", "notes", "corrections"} | ({"data_gaps"} if card in RULE_FILLED else set()), card)
            pokemon = {c["id"]: c for c in new["cards"]}[card]["pokemon"]
            old_pokemon = before[card]["pokemon"]
            self.assertEqual({k for k in set(pokemon) | set(old_pokemon) if pokemon.get(k) != old_pokemon.get(k)},
                             {"evolves_to"} | ({"rules_text"} if card in RULE_FILLED else set()), card)
        # 写しの元を上げても、v0.69・v0.71 の選定の記録は 73a1690 の一覧から読む（e519b99 の一覧では、選んだカードはどれも registered）
        module = extract_module()
        self.assertEqual(module.TARGET_SELECTION_COMMIT, V097)
        self.assertEqual(module.current_target_status_problems(KYUURA), [])
        targets = {c["id"]: c for c in kyuura_json(V0114, "data/engine_targets.json")["cards"]}
        self.assertEqual({targets[card]["engine_status"] for card in module.POOL_V0_69 + module.POOL_V0_71}, {"registered"})


class DocumentTest(unittest.TestCase):
    def test_migration_chapter(self):
        text = DOC.read_text(encoding="utf-8")
        for word in (V0114, V097, "KYUURA_MIGRATIONS", "V0_97_KYUURA_COMMIT", "TARGET_SELECTION_COMMIT", "current_target_status_problems", "field_added_from_print",
                     "card_image_checks.json", "existing_transcription", "UQ-NEO-TEXT-BABY-CATEGORIES", "NB0", "ENGINE-46A3E2E", "with_card_data_commit_at"):
            self.assertIn(word, text)
        provenance = (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8")
        self.assertIn("## v0.114: 写しの元・研究の基準を kyuura e519b99 に上げる移行", provenance)


if __name__ == "__main__":
    unittest.main()
