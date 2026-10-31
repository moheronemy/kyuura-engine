"""v0.126（docs/flash-faceup-deck-v0.126.md）: 写しの元・研究の基準の移行（kyuura 134a664 → 57d01f4。写しの外の PR1-027 の読点 1 つ）。

2 章: 移行だけの段。kyuura のちえくらべ・フラッシュ・とりかえっこプリーズの調査の記録（最新の説明 2・照合 2・裁定 5・既存の 4 論点の注記）を研究の対応表・採用の記録に結ぶ。
エンジンは原典・画像を見ていない（kyuura の記録を再利用しただけ）。この段ではカードを登録せず、処理も変えない。
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
NOW, V0125 = "57d01f45cfb8b086d03dc0525b329cf6adeff69b", "134a664c6adf67d5604148a31b58e1a7d26d4d6d"
RESEARCH_PARENT = "645f0a8d3da0cabaef8ca7db96d3f7e303448f35"  # kyuura の検査のコミット（57d01f4 の親。その親がデータ 169cdd3）
ECB, V069, V097, V0114, V0121, V0123, V0124 = (
    "ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3", "73a169063463bbf7bcaa3137d70cbf9721d11534",
    "e519b99e2adcc6c2cd0998569ae5ee1101de6e89", "2fe0bc042ce187d191843819262f8036abbb343d", "74b3ceb883dd815495d13b9987433fb14b36e44d",
    "b9e7cff6d2b2c6b4539ec45e61bf453879adab3a")
BASE_ENGINE = "19c22051d10ec2a7610e7c7641b2c6053bd5c3f1"  # この版の基点（v0.125 の最後のコミット。main 84bf94f を祖先に持つ）
FLASH, SWAP_PLEASE, SLOWKING = "ES2-035", "PR1-027", "neo1-049"
FIX = "FIX-PR1-027-TEXT-JA"
SWAP_BEFORE = ("相手プレイヤーの手札を見て、カードを1枚えらぶ。次に、相手プレイヤーにあなたの手札を見せ、カードを1枚えらばせる。そして、お互いがえらんだカードを交換してよいかどうか、"
               "相手にたずねる。オーケーなら、カードを交換して、それぞれの手札にくわえる。オーケーでないなら、交換はおこらず、あなたは山札からカードを2枚引く。"
               "(このカードは、お互いに手札が1枚以上ある時だけ使える)")
SWAP_AFTER = SWAP_BEFORE.replace("ある時だけ使える", "ある時だけ、使える")
NEW_LDS = {"ES2-035": "LD-ES2-035-TRAINER", "PR1-027": "LD-PR1-027-TRAINER"}
NEW_CCS = {"ES2-035": ["CC-ES2-035-P270"], "PR1-027": ["CC-PR1-027-P293"]}
NEW_RULINGS = {"CR-FLASH-TOP-CARD-SEEN": "CONFIRMED", "CR-SWAP-PLEASE-USE-IN-GAME": "CONFIRMED", "CR-MIND-GAMES-STADIUM-TOOL": "CONFIRMED",
               "CR-SWAP-PLEASE-REAL-TRADE-SEPARATE": "SUPPORTED", "CR-CHAOS-GYM-COIN-BEFORE-CONDITIONS": "SUPPORTED"}
UPDATED_ISSUES = ("UQ-MIND-GAMES-OPTIONAL", "UQ-MIND-GAMES-TRAINER-STEP", "UQ-FLASH-FACE-UP-DECK", "UQ-SWAP-PLEASE-OWNERSHIP")


def needs_kyuura(test):
    return unittest.skipUnless((KYUURA / ".git").exists(), "../kyuura がない")(test)


def needs_history(test):
    return unittest.skipUnless((ROOT / ".git").exists(), "このリポジトリの git の履歴がない（取り出した木）")(test)


def kyuura_json(commit: str, path: str):
    return json.loads(subprocess.check_output(["git", "-C", str(KYUURA), "show", f"{commit}:{path}"]))


def engine_json(commit: str, path: str):
    return json.loads(subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"]))


def _diff_paths(a, b, path="") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        return [p for key in sorted(set(a) | set(b)) for p in _diff_paths(a.get(key), b.get(key), f"{path}.{key}")]
    return [] if a == b else [path]


# ---------------------------------------------------------------- 2 章: 移行

class MigrationChainTest(unittest.TestCase):
    """2.1 節: 段 v0.126（134a664 → 57d01f4）。過去の段の値・採用の記録の移行は書き換えない。この段の訂正は写しの外の PR1-027 の読点 1 つ。"""

    def test_chain(self):
        module = extract_module()
        self.assertEqual((module.KYUURA_COMMIT, module.V0_125_KYUURA_COMMIT, module.V0_124_KYUURA_COMMIT), (NOW, V0125, V0124))
        self.assertEqual(module.migration_problems(), [])
        self.assertEqual([(s["id"], s["from"], s["to"]) for s in module.KYUURA_MIGRATIONS],
                         [("v0.69", ECB, V069), ("v0.97", V069, V097), ("v0.114", V097, V0114), ("v0.121", V0114, V0121), ("v0.123", V0121, V0123),
                          ("v0.124", V0123, V0124), ("v0.125", V0124, V0125), ("v0.126", V0125, NOW)])
        self.assertEqual(module.KYUURA_MIGRATIONS[-1]["document"], "docs/flash-faceup-deck-v0.126.md")
        extract = read_extract()
        self.assertEqual((extract["source"]["commit"], extract["previous_source"]["commit"]), (NOW, ECB))
        self.assertEqual(extract["source_migrations"][-1], {"id": "v0.126", "from": V0125, "to": NOW, "document": "docs/flash-faceup-deck-v0.126.md", "corrections": [FIX]})
        # v0.125 の段のあとを写しの元の定数にもどすと、写しの元を上げたときに過去の段のあとまで変わる（連鎖が切れて止まる）
        steps = module.KYUURA_MIGRATIONS
        try:
            module.KYUURA_MIGRATIONS = (*steps[:6], {**steps[6], "to": module.KYUURA_COMMIT}, steps[7])
            self.assertTrue(any("その前の段のあと" in p for p in module.migration_problems()))
        finally:
            module.KYUURA_MIGRATIONS = steps
        self.assertEqual([(c["card_id"], c["source_commit"]) for c in extract["engine_user_corrections"]], [("PR1-069", NOW)])

    def test_correction_record(self):
        """FIX-PR1-027-TEXT-JA: 写しの外のカードの転記の誤り（読点 1 つ）。画像を見たのは kyuura で、エンジンは見ていない。名前の「！」は直していない。"""
        extract = read_extract()
        fixes = [c for c in extract["kyuura_corrections"] if c["migration"] == "v0.126"]
        self.assertEqual([c["id"] for c in fixes], [FIX])
        fix = fixes[0]
        self.assertEqual((fix["card_id"], fix["field"], fix["before"], fix["after"], fix["kind"], fix["basis"], fix["image_check"]),
                         (SWAP_PLEASE, "trainer.text.ja", SWAP_BEFORE, SWAP_AFTER, "transcription_error", "card_image_check", "IMG-PR1-027"))
        self.assertEqual((fix["kyuura_saw_image"], fix["engine_saw_image"], fix["applied_in_source"], fix["previous_source"]), (True, False, NOW, V0125))
        self.assertEqual([c for c in SWAP_BEFORE if c not in SWAP_AFTER], [])
        self.assertEqual(len(SWAP_AFTER) - len(SWAP_BEFORE), 1)  # 加わったのは読点 1 つだけ（括弧・句読点を一般に正規化していない）
        self.assertNotIn(SWAP_PLEASE, {c["id"] for c in extract["cards"]})
        self.assertNotIn(SWAP_PLEASE, load_card_pool().playable_ids)

    def test_adoption_migrations_are_appended(self):
        sources = cs.load_sources()
        self.assertEqual([(m["from"], m["to"], m["on"]) for m in sources["data_migrations"]],
                         [(ECB, V069, "2026-10-19"), (V069, V097, "2026-10-25"), (V097, V0114, "2026-10-28"), (V0114, V0121, "2026-10-30"),
                          (V0121, V0123, "2026-10-31"), (V0123, V0124, "2026-10-31"), (V0124, V0125, "2026-10-31"), (V0125, NOW, "2026-10-31")])
        self.assertEqual(sources["data_migrations"][-1]["document"], "docs/flash-faceup-deck-v0.126.md")
        self.assertEqual(cs.data_migrations(sources, read_extract())[1], [])
        # 採用したときのデータのコミットが 57d01f4 の記録は、この版で写しに加えたカード（pool_v0_126）だけ（移行の段では採用し直していない）
        self.assertEqual({card for card, record in sources["cards"].items() if record.get("kyuura_commit") == NOW}, set(read_extract().get("pool_v0_126", ())))

    @needs_history
    def test_extract_is_unchanged_for_the_base_cards(self):
        """基点の写しの 1,361 枚（と参照のカード）は同じ値。変わったのは写しの元の記録・移行の段・写しの外の訂正の記録だけ。"""
        before = engine_json(BASE_ENGINE, "kyuura_engine/data/kyuura_cards.json")
        now = read_extract()
        old = {card["id"]: card for card in before["cards"]}
        new = {card["id"]: card for card in now["cards"]}
        self.assertLessEqual(set(old), set(new))
        self.assertEqual({card for card in old if old[card] != new[card]}, set())
        self.assertEqual(set(new) - set(old), set(now.get("pool_v0_126", ())))
        self.assertNotIn(FLASH, old)
        self.assertEqual(before["kyuura_corrections"], [c for c in now["kyuura_corrections"] if c["id"] != FIX])

    @needs_kyuura
    def test_kyuura_card_data_differs_only_in_the_swap_please_comma(self):
        """134a664 → 57d01f4 の data/cards.json: 全 1,377 件を欄ごとに比べ、変わったのは PR1-027 の文面・notes・corrections だけ。ES2-035（この版で登録するカード）の値は同じ。"""
        old, new = ({c["id"]: c for c in kyuura_json(commit, "data/cards.json")["cards"]} for commit in (V0125, NOW))
        self.assertEqual((len(old), set(old)), (1377, set(new)))
        changed = {card: _diff_paths(old[card], new[card]) for card in old if old[card] != new[card]}
        self.assertEqual(changed, {SWAP_PLEASE: [".corrections", ".notes", ".trainer.text.ja"]})
        self.assertEqual((old[SWAP_PLEASE]["trainer"]["text"]["ja"], new[SWAP_PLEASE]["trainer"]["text"]["ja"]), (SWAP_BEFORE, SWAP_AFTER))
        self.assertEqual((old[SWAP_PLEASE]["name"]["ja"], new[SWAP_PLEASE]["name"]["ja"]), ("とりかえっこプリーズ", "とりかえっこプリーズ"))  # 「！」は直していない
        self.assertEqual(old[FLASH], new[FLASH])
        ledger = {c["id"]: c for c in kyuura_json(NOW, "data/curation/card_corrections.json")["corrections"]}
        old_ledger = {c["id"] for c in kyuura_json(V0125, "data/curation/card_corrections.json")["corrections"]}
        self.assertEqual(set(ledger) - old_ledger, {FIX})
        self.assertEqual((ledger[FIX]["before"], ledger[FIX]["after"], ledger[FIX]["kind"]), (SWAP_BEFORE, SWAP_AFTER, "transcription_error"))


class AdoptionRecordTest(unittest.TestCase):
    """2.2 節: 採用の記録。登録済みのカードの kyuura_records に加わったのは 4 枚の新しい裁定の id だけ。採用したときのコミット・日付は書き換えない。"""

    def test_records_added_by_the_research_commit(self):
        cards = cs.load_sources()["cards"]
        self.assertEqual(HP.V0_126_KYUURA_RECORDS_ADDED, {"PMCG6-068": ("CR-FLASH-TOP-CARD-SEEN",), "PMCG5-087": ("CR-CHAOS-GYM-COIN-BEFORE-CONDITIONS",),
                                                          "neo1-085": ("CR-MIND-GAMES-STADIUM-TOOL",), "neo1-088": ("CR-MIND-GAMES-STADIUM-TOOL",)})
        for card, (added,) in HP.V0_126_KYUURA_RECORDS_ADDED.items():
            with self.subTest(card=card):
                self.assertIn(added, cards[card]["kyuura_records"])
                self.assertNotEqual(cards[card]["kyuura_commit"], NOW)  # 採用し直していない
        before = engine_json(BASE_ENGINE, "kyuura_engine/data/card_sources.json")["cards"] if (ROOT / ".git").exists() else None
        if before is not None:
            for card in HP.V0_126_KYUURA_RECORDS_ADDED:
                self.assertEqual(sorted(cards[card]["kyuura_records"]), sorted([*before[card]["kyuura_records"], *HP.V0_126_KYUURA_RECORDS_ADDED[card]]))
                self.assertEqual({k: v for k, v in cards[card].items() if k != "kyuura_records"}, {k: v for k, v in before[card].items() if k != "kyuura_records"})


class ResearchLinksTest(unittest.TestCase):
    """2.4 節: 研究の対応表。論点 90 → 90。研究の論点の数を停止コード・未解決の数にそろえない。"""

    @classmethod
    def setUpClass(cls):
        cls.links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))

    def test_commits_and_counts(self):
        links = self.links
        self.assertEqual((links["research_commit"], links["card_data_commit"], links["research_branch"]),
                         (NOW, NOW, "claude/trainer-reaction-faceup-deck-ownership-research"))
        self.assertEqual(links["counts"]["kyuura_issues"], 90)
        self.assertEqual(links["engine_import_id"], "ENGINE-46A3E2E")
        registered = FLASH in load_card_pool().playable_ids
        trainers = links["latest_descriptions"]
        self.assertEqual(trainers["trainer_records_not_registered"], {SWAP_PLEASE: NEW_LDS[SWAP_PLEASE]} if registered else NEW_LDS)
        self.assertEqual(trainers["registered_trainers"].get(FLASH), NEW_LDS[FLASH] if registered else None)
        not_in_engine = links["card_checks"]["not_in_engine"]
        for card, ids in NEW_CCS.items():
            self.assertEqual(not_in_engine.get(card), ids, card)

    def test_unregistered_trainer_descriptions_are_checked(self):
        """``trainer_records_not_registered``: 登録したトレーナーの説明と重ならず、合わせて kyuura のトレーナーの説明のすべてと同じ。登録したカードは挙げられない。"""
        if not (KYUURA / ".git").exists():
            self.skipTest("../kyuura がない")
        import copy

        broken = copy.deepcopy(self.links)
        broken["latest_descriptions"]["trainer_records_not_registered"].pop(SWAP_PLEASE)
        self.assertTrue(any("トレーナーの最新の説明（LD-…-TRAINER）の一覧が違う" in p for p in rl.check(KYUURA, links=broken)))
        broken = copy.deepcopy(self.links)
        broken["latest_descriptions"]["trainer_records_not_registered"]["PMCG1-077"] = "LD-PMCG1-077-TRAINER"
        self.assertTrue(any("両方にある" in p for p in rl.check(KYUURA, links=broken)))

    @needs_kyuura
    def test_links_agree_with_kyuura(self):
        self.assertEqual(rl.check(KYUURA), [])

    @needs_kyuura
    def test_research_records(self):
        self.assertEqual(subprocess.check_output(["git", "-C", str(KYUURA), "rev-parse", f"{NOW}^"]).decode().strip(), RESEARCH_PARENT)
        old, new = (kyuura_json(commit, "data/sidecar/rulings.json") for commit in (V0125, NOW))
        rulings = {r["id"]: r["status"] for r in new["rulings"]}
        self.assertEqual({k: v for k, v in rulings.items() if k not in {r["id"] for r in old["rulings"]}}, NEW_RULINGS)
        self.assertEqual((len(new["rulings"]), len(new["issues"]), len(new["rule_clauses"])), (350, 90, 41))
        old_issues, new_issues = ({i["id"]: i for i in data["issues"]} for data in (old, new))
        self.assertEqual(set(old_issues), set(new_issues))
        changed = {key for key in new_issues if new_issues[key] != old_issues[key]}
        self.assertEqual(changed, set(UPDATED_ISSUES))
        for key in UPDATED_ISSUES:
            # 出典・監査・注記だけが変わった（問い・事例・分類は同じ。研究の取り込みは論点の解決ではない）
            self.assertEqual({f for f in set(old_issues[key]) | set(new_issues[key]) if old_issues[key].get(f) != new_issues[key].get(f)}, {"sources", "audit", "notes"}, key)
            self.assertEqual(new_issues[key]["status"], "UNRESOLVED")
        descriptions = {r["id"] for r in kyuura_json(NOW, "data/sidecar/latest_descriptions.json")["records"]}
        old_descriptions = {r["id"] for r in kyuura_json(V0125, "data/sidecar/latest_descriptions.json")["records"]}
        self.assertEqual((len(descriptions), descriptions - old_descriptions), (54, set(NEW_LDS.values())))
        checks = {r["id"] for r in kyuura_json(NOW, "data/sidecar/card_checks.json")["records"]}
        old_checks = {r["id"] for r in kyuura_json(V0125, "data/sidecar/card_checks.json")["records"]}
        self.assertEqual((len(checks), checks - old_checks), (90, {i for ids in NEW_CCS.values() for i in ids}))

    def test_flash_cases_before_registration(self):
        """2.4 節: フラッシュの事例。ちえくらべ（neo1-049）・とりかえっこプリーズ（PR1-027）の事例は登録しないので、登録のあとも unregistered のまま。"""
        cases = {(c["kyuura_issue"], c["card_id"], c["target"]): c["engine"] for c in self.links["kyuura_cases_without_engine_ruling"]["cases"]}
        self.assertEqual(cases[("UQ-FLASH-FACE-UP-DECK", SLOWKING, "power/0")], {"unregistered": True})
        for issue in ("UQ-MIND-GAMES-OPTIONAL", "UQ-MIND-GAMES-TRAINER-STEP", "UQ-SWAP-PLEASE-OWNERSHIP"):
            for (key, card, _), engine in cases.items():
                if key == issue and card in (SLOWKING, SWAP_PLEASE):
                    self.assertEqual(engine, {"unregistered": True}, (key, card))
        self.assertFalse({SLOWKING, SWAP_PLEASE} & load_card_pool().playable_ids)


if __name__ == "__main__":
    unittest.main()
