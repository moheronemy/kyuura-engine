"""v0.125（docs/wigglytuff-helping-hand-v0.125.md）: 写しの元・研究の基準の移行（kyuura b9e7cff → 134a664。データの値は全欄が同じ）。

2 章: 移行だけの段。kyuura のプクリンの最新の説明・コインで決まる枚数の不足の調査の記録（最新の説明 4・照合 3・裁定 8・論点 2 と、既存の論点の事例）を研究の対応表・採用の記録に
結ぶ。エンジンは原典・画像を見ていない（kyuura の記録を再利用しただけ）。この段ではカードを登録せず、処理も変えない。
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import unittest

from kyuura_engine.cards import load_card_pool, read_extract
from scripts import check_card_sources as cs
from scripts import check_research_links as rl
from tests import helpers as HP
from tests.test_baby_rules_evolution_v0_114 import extract_module

ROOT = pathlib.Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
LINKS_PATH = ROOT / "kyuura_engine" / "data" / "research_links.json"
NOW, V0124 = "134a664c6adf67d5604148a31b58e1a7d26d4d6d", "b9e7cff6d2b2c6b4539ec45e61bf453879adab3a"
RESEARCH_PARENT = "6681d5c9e48eec8c4fc3a35be4caff94634067da"  # kyuura の不足の研究のコミット（134a664 の親）
ECB, V069, V097, V0114, V0121, V0123 = ("ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3",
                                        "73a169063463bbf7bcaa3137d70cbf9721d11534", "e519b99e2adcc6c2cd0998569ae5ee1101de6e89",
                                        "2fe0bc042ce187d191843819262f8036abbb343d", "74b3ceb883dd815495d13b9987433fb14b36e44d")
BASE_ENGINE = "e165fe0fb3de0e73129135f8cbaa34e2aae0eb64"  # この版の基点（v0.124 の最後のコミット。main 84bf94f を祖先に持つ）
WIGGLYTUFF = "ES1-027"
NEW_LDS = ("LD-ES1-027-ATK0", "LD-ES1-027-PWR0", "LD-ES2-005-ATK0", "LD-QSG-055-ATK0")
NEW_CCS = {"ES1-027": ["CC-ES1-027-P226"], "ES2-005": ["CC-ES2-005-P82"], "QSG-055": ["CC-QSG-055-P82"]}
NEW_ISSUES = ("UQ-HELPING-HAND-CHOICE", "UQ-DESTRUCTIVE-FIRE-FAILURE")
NEW_RULINGS = {"CR-DESTRUCTIVE-FIRE-TEXT": "CONFIRMED", "CR-DRY-UP-PROCEDURE": "CONFIRMED", "CR-HELPING-HAND-USE": "CONFIRMED", "CR-INFLATE-LATEST": "CONFIRMED",
               "CR-MOUNTAIN-CRUSH-PROCEDURE": "CONFIRMED", "CR-THOUGHT-WAVE-MACHINE-PROCEDURE": "CONFIRMED", "CR-INFLATE-DAMAGE-STEP": "SUPPORTED",
               "CR-UNTIL-TAILS-NOT-CAPPED": "SUPPORTED"}
# 研究の基準を上げて加わった、エンジンの裁定 id のない事例（論点・カード・対象）。kyuura の同じ対象の事例（はかいのほのおの 5 つ・［てだすけ］の 2 つ）は 1 つの組
NEW_CASES = {
    ("UQ-CARD-USE-WITHOUT-TARGET", "ES1-027", "power/0"), ("UQ-CARD-USE-WITHOUT-TARGET", "neo4-108", "trainer"),
    ("UQ-DESTRUCTIVE-FIRE-FAILURE", "neo4-082", "attack/1"), ("UQ-HELPING-HAND-CHOICE", "ES1-027", "power/0"),
    ("UQ-NON-ATTACK-DAMAGE-MODIFIERS", "ES1-027", "attack/0"), ("UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY", "neo4-082", "attack/1"),
    ("UQ-STATED-COUNT-SHORT", "neo4-082", "attack/0"), ("UQ-STATED-COUNT-SHORT", "neo4-082", "attack/1"), ("UQ-STATED-COUNT-SHORT", "neo4-108", "trainer"),
    ("UQ-STATED-COUNT-SHORT", "ES2-005", "attack/0"), ("UQ-STATED-COUNT-SHORT", "QSG-055", "attack/0"),
}
MIGRATION_TAG = "v0.125 で研究の基準を 134a664 に上げて結んだ"
OUT_OF_SCOPE = ("neo4-082", "neo4-108", "ES2-005", "QSG-055")  # 7 章: 登録しない


def needs_kyuura(test):
    return unittest.skipUnless((KYUURA / ".git").exists(), "../kyuura がない")(test)


def needs_history(test):
    return unittest.skipUnless((ROOT / ".git").exists(), "このリポジトリの git の履歴がない（取り出した木）")(test)


def kyuura_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(KYUURA), "show", f"{commit}:{path}"])


def kyuura_json(commit: str, path: str):
    return json.loads(kyuura_bytes(commit, path))


def engine_json(commit: str, path: str):
    return json.loads(subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"]))


# ---------------------------------------------------------------- 2 章: 移行

class MigrationChainTest(unittest.TestCase):
    """2.1 節: 段 v0.125（b9e7cff → 134a664）。過去の段の値・採用の記録の移行は書き換えない。この段に訂正はない。"""

    def test_chain(self):
        module = extract_module()
        self.assertEqual((module.KYUURA_COMMIT, module.V0_124_KYUURA_COMMIT, module.V0_123_KYUURA_COMMIT), (NOW, V0124, V0123))
        self.assertEqual(module.migration_problems(), [])
        self.assertEqual([(s["id"], s["from"], s["to"]) for s in module.KYUURA_MIGRATIONS],
                         [("v0.69", ECB, V069), ("v0.97", V069, V097), ("v0.114", V097, V0114), ("v0.121", V0114, V0121), ("v0.123", V0121, V0123),
                          ("v0.124", V0123, V0124), ("v0.125", V0124, NOW)])
        self.assertEqual(module.KYUURA_MIGRATIONS[-1]["document"], "docs/wigglytuff-helping-hand-v0.125.md")
        extract = read_extract()
        self.assertEqual((extract["source"]["commit"], extract["previous_source"]["commit"]), (NOW, ECB))
        self.assertEqual(extract["source_migrations"][-1], {"id": "v0.125", "from": V0124, "to": NOW, "document": "docs/wigglytuff-helping-hand-v0.125.md", "corrections": []})
        self.assertFalse([c for c in extract["kyuura_corrections"] if c["migration"] == "v0.125"])
        # v0.124 の段のあとを写しの元の定数にもどすと、写しの元を上げたときに過去の段のあとまで変わる（連鎖が切れて止まる）
        steps = module.KYUURA_MIGRATIONS
        try:
            module.KYUURA_MIGRATIONS = (*steps[:5], {**steps[5], "to": module.KYUURA_COMMIT}, steps[6])
            self.assertTrue(any("その前の段のあと" in p for p in module.migration_problems()))
        finally:
            module.KYUURA_MIGRATIONS = steps
        self.assertEqual([(c["card_id"], c["source_commit"]) for c in extract["engine_user_corrections"]], [("PR1-069", NOW)])

    def test_adoption_migrations_are_appended(self):
        sources = cs.load_sources()
        self.assertEqual([(m["from"], m["to"], m["on"]) for m in sources["data_migrations"]],
                         [(ECB, V069, "2026-10-19"), (V069, V097, "2026-10-25"), (V097, V0114, "2026-10-28"), (V0114, V0121, "2026-10-30"),
                          (V0121, V0123, "2026-10-31"), (V0123, V0124, "2026-10-31"), (V0124, NOW, "2026-10-31")])
        self.assertEqual(sources["data_migrations"][-1]["document"], "docs/wigglytuff-helping-hand-v0.125.md")
        self.assertEqual(cs.data_migrations(sources, read_extract())[1], [])
        # 採用したときのデータのコミットが 134a664 の記録は、この版で写しに加えたカード（pool_v0_125）だけ（移行の段では採用し直していない）
        self.assertEqual({card for card, record in sources["cards"].items() if record.get("kyuura_commit") == NOW}, set(read_extract().get("pool_v0_125", ())))

    @needs_history
    def test_extract_is_unchanged_for_the_base_cards(self):
        """基点の写しの 1,360 枚（と参照のカード）は同じ値。変わったのは写しの元の記録と、移行の段だけ。"""
        before = engine_json(BASE_ENGINE, "kyuura_engine/data/kyuura_cards.json")
        now = read_extract()
        old = {card["id"]: card for card in before["cards"]}
        new = {card["id"]: card for card in now["cards"]}
        self.assertLessEqual(set(old), set(new))
        self.assertEqual({card for card in old if old[card] != new[card]}, set())
        self.assertEqual(set(new) - set(old), set(now.get("pool_v0_125", ())))
        self.assertNotIn(WIGGLYTUFF, old)
        self.assertEqual(before["kyuura_corrections"], now["kyuura_corrections"])

    @needs_kyuura
    def test_kyuura_card_data_is_identical(self):
        """b9e7cff → 134a664 の data/cards.json: バイト列が同じ（1,377 件の全欄が同じ）。台帳は ES1-027 の候補の later_notes だけが加わり、訂正の数・候補の状態は同じ。"""
        self.assertEqual(kyuura_bytes(V0124, "data/cards.json"), kyuura_bytes(NOW, "data/cards.json"))
        self.assertEqual(len(kyuura_json(NOW, "data/cards.json")["cards"]), 1377)
        old, new = (kyuura_json(commit, "data/curation/card_corrections.json") for commit in (V0124, NOW))
        self.assertEqual(old["corrections"], new["corrections"])
        old_candidates = {(c["card_id"], c["field"]): c for c in old["candidates"]}
        new_candidates = {(c["card_id"], c["field"]): c for c in new["candidates"]}
        self.assertEqual(set(old_candidates), set(new_candidates))
        changed = {key for key in new_candidates if new_candidates[key] != old_candidates[key]}
        self.assertEqual(changed, {(WIGGLYTUFF, "pokemon.attacks[0].text.ja")})
        candidate = new_candidates[(WIGGLYTUFF, "pokemon.attacks[0].text.ja")]
        self.assertEqual(candidate["status"], "held_illegible_print")  # 最新の説明を読んでも、印刷の 1 字が読めたことにはしない
        self.assertEqual({k: v for k, v in candidate.items() if k != "later_notes"}, old_candidates[(WIGGLYTUFF, "pokemon.attacks[0].text.ja")])


class AdoptionRecordTest(unittest.TestCase):
    """2.3 節: 採用の記録。登録済みのカードの kyuura_records に加わったのは、ゴローン（ES2-023）の CR-UNTIL-TAILS-NOT-CAPPED だけ。採用したときのコミット・日付は書き換えない。"""

    def test_records_added_by_the_research_commit(self):
        cards = cs.load_sources()["cards"]
        self.assertEqual(HP.V0_125_KYUURA_RECORDS_ADDED, {"ES2-023": ("CR-UNTIL-TAILS-NOT-CAPPED",)})
        record = cards["ES2-023"]
        self.assertEqual((record["kyuura_records"], record["kyuura_commit"], record["recorded_on"]),
                         (["CR-UNTIL-TAILS-NOT-CAPPED"], V069, "2026-10-19"))

    def test_registered_until_tails_coins_are_not_capped(self):
        """CR-UNTIL-TAILS-NOT-CAPPED（SUPPORTED）: 登録済みのれんぞくいわなげ（ES2-023）は v0.64 の型のまま「うら」が出るまで投げる（コインの数・ダメージに上限を置かない）。"""
        from kyuura_engine.effects import DEFAULT_EFFECTS, CoinsUntilTailsDamage

        entry = DEFAULT_EFFECTS.attack_entry("ES2-023", 0)
        self.assertIsInstance(entry.effect, CoinsUntilTailsDamage)
        self.assertNotIn("max", {f for f in vars(entry.effect)})


class ResearchLinksTest(unittest.TestCase):
    """2.4 節: 研究の対応表。論点 88 → 90。研究の論点の数を停止コード・未解決の数にそろえない。"""

    @classmethod
    def setUpClass(cls):
        cls.links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))

    def test_commits_and_counts(self):
        links = self.links
        self.assertEqual((links["research_commit"], links["card_data_commit"], links["research_branch"]), (NOW, NOW, "claude/eloquent-lamport-5xyv5r"))
        self.assertEqual(links["counts"]["kyuura_issues"], 90)
        self.assertEqual(links["engine_import_id"], "ENGINE-46A3E2E")
        registered = WIGGLYTUFF in load_card_pool().playable_ids
        expected = ["LD-ES2-005-ATK0", "LD-QSG-055-ATK0"] if registered else sorted(NEW_LDS)
        self.assertEqual(links["latest_descriptions"]["kyuura_records_not_registered"], expected)
        not_in_engine = links["card_checks"]["not_in_engine"]
        for card, ids in NEW_CCS.items():
            self.assertEqual(not_in_engine.get(card), ids, card)

    def test_new_cases(self):
        added = [c for c in self.links["kyuura_cases_without_engine_ruling"]["cases"] if MIGRATION_TAG in c.get("note", "")]
        self.assertEqual({(c["kyuura_issue"], c["card_id"], c["target"]) for c in added}, NEW_CASES)
        self.assertEqual(len(added), 11)
        # 登録しないカード（7 章）の事例は、登録のあとも unregistered のまま
        for case in added:
            if case["card_id"] in OUT_OF_SCOPE:
                self.assertEqual(case["engine"], {"unregistered": True}, case)
        self.assertFalse(set(OUT_OF_SCOPE) & load_card_pool().playable_ids)

    @needs_kyuura
    def test_links_agree_with_kyuura(self):
        self.assertEqual(rl.check(KYUURA), [])

    @needs_kyuura
    def test_research_records(self):
        self.assertEqual(subprocess.check_output(["git", "-C", str(KYUURA), "rev-parse", f"{NOW}^"]).decode().strip(), RESEARCH_PARENT)
        old, new = (kyuura_json(commit, "data/sidecar/rulings.json") for commit in (V0124, NOW))
        rulings = {r["id"]: r["status"] for r in new["rulings"]}
        self.assertEqual({k: v for k, v in rulings.items() if k not in {r["id"] for r in old["rulings"]}}, NEW_RULINGS)
        self.assertEqual((len(new["rulings"]), len(new["issues"]), len(new["rule_clauses"])), (345, 90, 41))
        self.assertEqual(sorted({i["id"] for i in new["issues"]} - {i["id"] for i in old["issues"]}), sorted(NEW_ISSUES))
        self.assertTrue(all(i["status"] == "UNRESOLVED" for i in new["issues"] if i["id"] in NEW_ISSUES))  # 研究の取り込みは論点の解決ではない
        descriptions = {r["id"] for r in kyuura_json(NOW, "data/sidecar/latest_descriptions.json")["records"]}
        old_descriptions = {r["id"] for r in kyuura_json(V0124, "data/sidecar/latest_descriptions.json")["records"]}
        self.assertEqual((len(descriptions), sorted(descriptions - old_descriptions)), (52, sorted(NEW_LDS)))
        checks = {r["id"] for r in kyuura_json(NOW, "data/sidecar/card_checks.json")["records"]}
        old_checks = {r["id"] for r in kyuura_json(V0124, "data/sidecar/card_checks.json")["records"]}
        self.assertEqual((len(checks), sorted(checks - old_checks)), (88, sorted(i for ids in NEW_CCS.values() for i in ids)))


if __name__ == "__main__":
    unittest.main()
