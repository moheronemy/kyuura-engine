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
from tests.release_catalog import cards_after
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
# v0.128: 写しの元・研究の基準を 71d1728 に上げた（docs/catalog-scope-migration-v0.128.md 2 章）。v0.126 の研究の対応表の値は、57d01f4 を基準にした最後のコミット（v0.127 の
# 最後のコミット 355589d。v0.126 の最後のコミット 6c70bfd と、この版の値は同じ）で確かめる
V0127_FINAL = "355589d432b39f8c985aafd55b8f9712ac1e9c91"
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
        # v0.128: 段 v0.128（57d01f4 → 71d1728）を加え、v0.126 の段のあとは V0_126_KYUURA_COMMIT（57d01f4）に固定した。今の写しの元は最後の段のあと
        # （docs/catalog-scope-migration-v0.128.md 2 章。今の値は tests/test_catalog_scope_migration_v0_128.py）
        self.assertEqual((module.V0_126_KYUURA_COMMIT, module.V0_125_KYUURA_COMMIT, module.V0_124_KYUURA_COMMIT), (NOW, V0125, V0124))
        self.assertEqual(module.migration_problems(), [])
        self.assertEqual([(s["id"], s["from"], s["to"]) for s in module.KYUURA_MIGRATIONS][:8],
                         [("v0.69", ECB, V069), ("v0.97", V069, V097), ("v0.114", V097, V0114), ("v0.121", V0114, V0121), ("v0.123", V0121, V0123),
                          ("v0.124", V0123, V0124), ("v0.125", V0124, V0125), ("v0.126", V0125, NOW)])
        self.assertEqual(module.KYUURA_MIGRATIONS[7]["document"], "docs/flash-faceup-deck-v0.126.md")
        extract = read_extract()
        self.assertEqual((extract["source"]["commit"], extract["previous_source"]["commit"]), (module.KYUURA_MIGRATIONS[-1]["to"], ECB))
        self.assertEqual(extract["source_migrations"][7], {"id": "v0.126", "from": V0125, "to": NOW, "document": "docs/flash-faceup-deck-v0.126.md", "corrections": [FIX]})
        # v0.125 の段のあとを写しの元の定数にもどすと、写しの元を上げたときに過去の段のあとまで変わる（連鎖が切れて止まる）
        steps = module.KYUURA_MIGRATIONS
        try:
            module.KYUURA_MIGRATIONS = (*steps[:6], {**steps[6], "to": module.KYUURA_COMMIT}, steps[7])
            self.assertTrue(any("その前の段のあと" in p for p in module.migration_problems()))
        finally:
            module.KYUURA_MIGRATIONS = steps
        self.assertEqual([(c["card_id"], c["source_commit"]) for c in extract["engine_user_corrections"]], [("PR1-069", module.KYUURA_COMMIT)])

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
        # v0.130: とりかえっこプリーズは v0.130 で写しに加えて登録した（pool_v0_130。docs/trade-please-ownership-v0.130.md）。v0.126 の版の範囲（後の版の写しの組を除く）では写しの外
        later = cards_after(extract, "0.126")
        self.assertEqual(later & {SWAP_PLEASE}, {SWAP_PLEASE})
        self.assertNotIn(SWAP_PLEASE, {c["id"] for c in extract["cards"]} - later)
        self.assertNotIn(SWAP_PLEASE, load_card_pool().playable_ids - later)

    def test_adoption_migrations_are_appended(self):
        sources = cs.load_sources()
        # v0.128: 9 段目（57d01f4 → 71d1728）が加わった（今の値は tests/test_catalog_scope_migration_v0_128.py）。v0.126 までの 8 段は書き換えない
        self.assertEqual([(m["from"], m["to"], m["on"]) for m in sources["data_migrations"]][:8],
                         [(ECB, V069, "2026-10-19"), (V069, V097, "2026-10-25"), (V097, V0114, "2026-10-28"), (V0114, V0121, "2026-10-30"),
                          (V0121, V0123, "2026-10-31"), (V0123, V0124, "2026-10-31"), (V0124, V0125, "2026-10-31"), (V0125, NOW, "2026-10-31")])
        self.assertEqual(sources["data_migrations"][7]["document"], "docs/flash-faceup-deck-v0.126.md")
        self.assertEqual(cs.data_migrations(sources, read_extract())[1], [])
        # 採用したときのデータのコミットが 57d01f4 の記録は、この版で写しに加えたカード（pool_v0_126）だけ（移行の段では採用し直していない）。v0.127 は写しの元を変えずに
        # pool_v0_127 の 6 枚を 57d01f4 で採用した（tests/test_deferred_shortage_user_promos_v0_127.py）
        # v0.129: pool_v0_129 のカツラのクイズ その1は 71d1728 で採用した（tests/test_blaines_quiz_heights_v0_129.py）ので、57d01f4 の記録には入らない
        self.assertEqual({card for card, record in sources["cards"].items() if record.get("kyuura_commit") == NOW},
                         cards_after(read_extract(), "0.125") - cards_after(read_extract(), "0.128"))

    @needs_history
    def test_extract_is_unchanged_for_the_base_cards(self):
        """基点の写しの 1,361 枚（と参照のカード）は同じ値。変わったのは写しの元の記録・移行の段・写しの外の訂正の記録だけ。"""
        before = engine_json(BASE_ENGINE, "kyuura_engine/data/kyuura_cards.json")
        now = read_extract()
        old = {card["id"]: card for card in before["cards"]}
        new = {card["id"]: card for card in now["cards"]}
        self.assertLessEqual(set(old), set(new))
        self.assertEqual({card for card in old if old[card] != new[card]}, set())
        self.assertEqual(set(new) - set(old), cards_after(now, "0.125"))  # v0.127: 後の版で写しに加えたカード（pool_v0_127）も基点にない
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
        # v0.128: 研究の基準を 71d1728 に上げた（今の値は tests/test_catalog_scope_migration_v0_128.py）。v0.126 の基準の値は、57d01f4 を基準にした最後のコミットの対応表で確かめる
        if not (ROOT / ".git").exists():
            self.skipTest("このリポジトリの git の履歴がない（取り出した木）")
        pinned = engine_json(V0127_FINAL, "kyuura_engine/data/research_links.json")
        self.assertEqual((pinned["research_commit"], pinned["card_data_commit"], pinned["research_branch"]),
                         (NOW, NOW, "claude/trainer-reaction-faceup-deck-ownership-research"))
        links = self.links
        self.assertEqual(links["counts"]["kyuura_issues"], 90)
        self.assertEqual(links["engine_import_id"], "ENGINE-46A3E2E")
        registered = FLASH in load_card_pool().playable_ids
        trainers = links["latest_descriptions"]
        # v0.130: とりかえっこプリーズを登録したので、その最新の説明は registered_trainers に移った（tests/test_trade_please_v0_130.py）
        swap_registered = SWAP_PLEASE in load_card_pool().playable_ids
        self.assertEqual(trainers["trainer_records_not_registered"], {} if swap_registered else {SWAP_PLEASE: NEW_LDS[SWAP_PLEASE]} if registered else NEW_LDS)
        self.assertEqual(trainers["registered_trainers"].get(SWAP_PLEASE), NEW_LDS[SWAP_PLEASE] if swap_registered else None)
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
        # v0.130: とりかえっこプリーズは登録した（registered_trainers）。どちらかの一覧から落とすと、kyuura のトレーナーの説明のすべてと違う
        listed = "trainer_records_not_registered" if SWAP_PLEASE in broken["latest_descriptions"]["trainer_records_not_registered"] else "registered_trainers"
        broken["latest_descriptions"][listed].pop(SWAP_PLEASE)
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
        """2.4 節: フラッシュの事例。ちえくらべ（neo1-049）の事例は登録しないので、登録のあとも unregistered のまま。v0.130: とりかえっこプリーズ（PR1-027）は v0.130 で登録し、
        所有者の事例を利用者が指定した規則で処理する（論点は解決していない。tests/test_trade_please_v0_130.py）。"""
        cases = {(c["kyuura_issue"], c["card_id"], c["target"]): c["engine"] for c in self.links["kyuura_cases_without_engine_ruling"]["cases"]}
        # v0.132 でヤドキングを登録した: 使ったプレイヤーの山札におもてのカードがあれば、使うを選ぶと FU4 で止める（docs/slowking-mind-games-v0.132.md 6 章）
        self.assertEqual(cases[("UQ-FLASH-FACE-UP-DECK", SLOWKING, "power/0")], {"stop_codes": ["UNRESOLVED_FACE_UP_DECK_PLACE_TOP"]})
        swap_registered = SWAP_PLEASE in load_card_pool().playable_ids
        for issue in ("UQ-MIND-GAMES-OPTIONAL", "UQ-MIND-GAMES-TRAINER-STEP", "UQ-SWAP-PLEASE-OWNERSHIP"):
            for (key, card, _), engine in cases.items():
                if key == issue and card == SLOWKING:
                    # v0.132 でヤドキングを登録した: 使うかの選択・時点は利用者が指定した規則、交換したカードの山札は v0.130 の所有者の規則（論点は解決していない）
                    expected = {"user_specified_rule": "PR1-027/trainer"} if issue == "UQ-SWAP-PLEASE-OWNERSHIP" else {"user_specified_rule": "neo1-049/power/0"}
                    self.assertEqual(engine, expected if SLOWKING in load_card_pool().playable_ids else {"unregistered": True}, (key, card))
                elif key == issue and card == SWAP_PLEASE:
                    self.assertEqual(engine, {"user_specified_rule": "PR1-027/trainer"} if swap_registered else {"unregistered": True}, (key, card))
        self.assertFalse({SLOWKING, SWAP_PLEASE} & (load_card_pool().playable_ids - cards_after(read_extract(), "0.126")))



# ---------------------------------------------------------------- 3 章以降: フラッシュの登録・表向きの山札（処理）

import copy as _copy
import itertools
import pickle as _pickle

from kyuura_engine import (
    CheckFaceUpDeckCard,
    EndTurn,
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    UseStadium,
    apply_command,
    observe,
    state_to_dict,
    visible_log,
)
from kyuura_engine import effects as E
from kyuura_engine import faceup as FU
from kyuura_engine.engine import check_invariants
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests.helpers import build_test_state
from tests.log_audit import (
    face_up_deck_from_log,
    observation_problems,
    serialization_problems,
)

GRASS_E, FIRE_E, WATER_E, LIGHTNING_E, PSYCHIC_E, FIGHTING_E = "PMCG1-097", "PMCG1-098", "PMCG1-099", "PMCG1-100", "PMCG1-101", "PMCG1-102"
ENERGIES = (GRASS_E, FIRE_E, WATER_E, LIGHTNING_E, PSYCHIC_E, FIGHTING_E)
BILL, OAK, COMPUTER_SEARCH, POKEDEX, RETRIEVER, RADIO_TOWER = "PMCG1-074", "PMCG1-077", "PMCG1-090", "PMCG1-082", "ES3-035", "neo4-112"
TELEPORTER = "IP1-020"
CHANSEY, RATICATE_C = "PMCG1-058", "PMCG1-062"
CODES = {"FU1": FU.FLASH_DECK_SHORT_CODE, "FU2": FU.FACE_UP_DECK_CHECK_CODE, "FU3": FU.FACE_UP_DECK_HIDDEN_TAKE_CODE,
         "FU4": FU.FACE_UP_DECK_PLACE_TOP_CODE, "FU5": FU.FACE_UP_DECK_LOOK_RETURN_CODE, "FU6": FU.FACE_UP_DECK_MOVE_CODE}


def board(hand=(FLASH,), deck0=None, deck1=None, *, discard0=(), current=0):
    deck0 = list(ENERGIES) * 2 if deck0 is None else list(deck0)
    deck1 = list(reversed(ENERGIES)) * 2 if deck1 is None else list(deck1)
    return build_test_state([{"active": CHANSEY, "hand": list(hand), "deck": deck0, "discard": list(discard0), "prizes": 6},
                             {"active": CHANSEY, "deck": deck1, "prizes": 6}], current_player=current)


def fingerprint(state):
    return (repr(state_to_dict(state, format_version=max(FORMAT_VERSIONS))), state.rng.getstate(), len(state.log), state.face_up_deck)


def card_in_hand(state, card_id, player=None):
    player = state.current_player if player is None else player
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)


def play_flash(state, first=lambda d: tuple(d.options), second=lambda d: tuple(d.options)):
    state = apply_command(state, PlayTrainer(state.current_player, card_in_hand(state, FLASH)))
    d = state.decision
    state = apply_command(state, ResolveDecision(d.player, d.id, first(d)))
    d = state.decision
    return apply_command(state, ResolveDecision(d.player, d.id, second(d)))


class RegistrationTest(unittest.TestCase):
    """3 章: フラッシュ ES2-035 の 1 枚。処理に使う文面は LD-ES2-035-TRAINER の全文。印刷の写しは別に持ち、句読点・括弧を一般に正規化して一致させない。"""

    def test_entry_and_texts(self):
        entry = E.DEFAULT_EFFECTS.trainer_entry(FLASH)
        self.assertIsInstance(entry.effect, E.FlashTrainer)
        self.assertEqual((entry.name_ja, entry.source), ("フラッシュ", "LD-ES2-035-TRAINER"))
        self.assertEqual(entry.play_text_ja, "おたがいのプレイヤーは、それぞれ、自分の山札の上から5枚のカードを見て、好きな順番にならべ替えてから、おもてを上にして山札の上にもどす。"
                                             "（先に相手プレイヤーが、ならべ替えをする）。山札を切るときには、おもてが上になっているカードをおもてが下になるように、もどしてから切る。")
        self.assertEqual(entry.text_ja, load_card_pool().get(FLASH).trainer_text_ja)
        self.assertNotEqual(entry.text_ja, entry.play_text_ja)
        if (KYUURA / ".git").exists():
            record = next(r for r in kyuura_json(NOW, "data/sidecar/latest_descriptions.json")["records"] if r["id"] == "LD-ES2-035-TRAINER")
            self.assertEqual(record["latest_description"]["text_ja"], entry.play_text_ja)
            self.assertEqual(record["printed_text"]["text_ja"], entry.text_ja)

    @needs_history
    def test_pool_and_counts(self):
        extract = read_extract()
        self.assertEqual(extract["pool_v0_126"], [FLASH])
        before = engine_json(BASE_ENGINE, "kyuura_engine/data/kyuura_cards.json")
        self.assertNotIn("pool_v0_126", before)
        playable = load_card_pool().playable_ids
        self.assertEqual(len(playable - cards_after(extract, "0.126")), 1362)  # v0.127 から後の版の写しの組を除くと、この版の 1,362 枚（今の総数は tests/test_catalog_contract.py）
        self.assertIn(FLASH, playable)
        self.assertFalse({SLOWKING, SWAP_PLEASE} & (playable - cards_after(extract, "0.126")))  # 8 章: 登録しない（v0.130: とりかえっこプリーズは後の版で登録した）

    def test_research_cases_are_bound_to_stop_codes(self):
        links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
        cases = {(c["kyuura_issue"], c["card_id"], c["target"]): c["engine"] for c in links["kyuura_cases_without_engine_ruling"]["cases"]}
        self.assertEqual(cases[("UQ-STATED-COUNT-SHORT", FLASH, "trainer")], {"stop_codes": [CODES["FU1"]]})
        self.assertEqual(cases[("UQ-FLASH-FACE-UP-DECK", FLASH, "trainer")], {"stop_codes": [CODES["FU2"], CODES["FU3"], CODES["FU6"]]})
        self.assertEqual(cases[("UQ-FLASH-FACE-UP-DECK", RETRIEVER, "trainer")], {"stop_codes": [CODES["FU4"]]})
        self.assertEqual(cases[("UQ-FLASH-FACE-UP-DECK", POKEDEX, "trainer")], {"stop_codes": [CODES["FU5"]]})
        self.assertEqual(cases[("UQ-FLASH-FACE-UP-DECK", RADIO_TOWER, "trainer")], {"stop_codes": [CODES["FU5"]]})
        self.assertEqual(cases[("UQ-FLASH-FACE-UP-DECK", SLOWKING, "power/0")], {"stop_codes": [CODES["FU4"]]})  # v0.132: ヤドキングを登録した（FU4）
        for code in CODES.values():
            self.assertEqual(links["stop_codes"][code]["engine_rulings"][0]["version"], "v0.126")
        self.assertEqual(links["latest_descriptions"]["registered_trainers"][FLASH], "LD-ES2-035-TRAINER")


class ProcedureTest(unittest.TestCase):
    """5 章: 使った側の相手が先・使った側があと。それぞれ自分の山札の 5 枚だけ。120 通りの並びを受け付け、誤った答えは状態・乱数・ログを変えない。"""

    def test_opponent_first_each_own_five(self):
        state = board()
        flash = card_in_hand(state, FLASH)
        before = (list(state.players[0].deck[:5]), list(state.players[1].deck[:5]))
        state = apply_command(state, PlayTrainer(0, flash))
        self.assertEqual(state.trainer_in_use.card, flash)
        d = state.decision
        self.assertEqual((d.player, d.options, d.min_choices, d.max_choices), (1, tuple(before[1]), 5, 5))
        state = apply_command(state, ResolveDecision(1, d.id, tuple(reversed(d.options))))
        self.assertEqual(state.players[1].deck[:5], list(reversed(before[1])))
        self.assertEqual(set(FU.face_up_in_deck(state, 1)), set(before[1]))
        self.assertEqual(FU.face_up_in_deck(state, 0), ())
        d = state.decision
        self.assertEqual((d.player, d.options), (0, tuple(before[0])))
        # 相手の並べ替えの結果のいちばん上は、使ったプレイヤーの決定の前に観測に出ている
        self.assertEqual(observe(state, 0)["players"][1]["deck"]["face_up_top"], {"card_id": state.cards[before[1][-1]].card_id})
        state = apply_command(state, ResolveDecision(0, d.id, tuple(d.options)))
        self.assertIsNone(state.decision)
        self.assertIsNone(state.trainer_in_use)
        self.assertEqual(sum(1 for e in state.log if e["kind"] == "discard_trainer"), 1)
        self.assertEqual(state.players[0].deck[:5], before[0])  # 同じ並びでも空振りにしない
        self.assertEqual(set(FU.face_up_in_deck(state, 0)), set(before[0]))
        self.assertFalse(any(e["kind"] == "shuffle" for e in state.log))  # この処理では切らない
        self.assertEqual(check_invariants(state), [])

    def test_every_permutation_is_accepted_for_each_side(self):
        """5! = 120 通りを、それぞれの側で別々に試す（両側の直積 14,400 は展開しない。相手の並べ替えは、使ったプレイヤーの選べるもの（自分の 5 枚）・決定の形を変えないので、
        相手の答えを 2 つにしぼっても、使ったプレイヤーの側の答えの集まりは同じ）。"""
        state = apply_command(board(), PlayTrainer(0, card_in_hand(board(), FLASH)))
        d = state.decision
        accepted = 0
        for order in itertools.permutations(d.options):
            after = apply_command(state, ResolveDecision(1, d.id, order))
            self.assertEqual(tuple(after.players[1].deck[:5]), order)
            accepted += 1
        self.assertEqual(accepted, 120)
        seconds = [apply_command(state, ResolveDecision(1, d.id, order)) for order in (d.options, tuple(reversed(d.options)))]
        self.assertEqual(len({(s.decision.options, s.decision.min_choices, s.decision.max_choices, s.decision.player) for s in seconds}), 1)
        mid = seconds[0]
        d2 = mid.decision
        self.assertEqual(sum(1 for order in itertools.permutations(d2.options)
                             if tuple(apply_command(mid, ResolveDecision(0, d2.id, order)).players[0].deck[:5]) == order), 120)

    def test_wrong_answers_change_nothing(self):
        state = apply_command(board(), PlayTrainer(0, card_in_hand(board(), FLASH)))
        d = state.decision
        other = state.players[1].deck[5]
        own_card = state.players[0].deck[0]
        before = fingerprint(state)
        for answer, player in ((d.options[:4], 1), (d.options + (other,), 1), (d.options[:4] + (d.options[0],), 1), (d.options[:4] + (other,), 1),
                               (d.options[:4] + (own_card,), 1), (d.options, 0)):
            with self.subTest(answer=answer, player=player):
                with self.assertRaises((IllegalActionError, UnsupportedError)):
                    apply_command(state, ResolveDecision(player, d.id, tuple(answer)))
                self.assertEqual(fingerprint(state), before)

    def test_short_decks_stop_before_use(self):
        for deck0, deck1 in ((ENERGIES[:4], None), (None, ENERGIES[:4]), (ENERGIES[:4], ENERGIES[:3]), (None, ())):
            with self.subTest(deck0=deck0, deck1=deck1):
                state = board(deck0=deck0, deck1=deck1)
                before = fingerprint(state)
                with self.assertRaises(UnsupportedError) as caught:
                    apply_command(state, PlayTrainer(0, card_in_hand(state, FLASH)))
                self.assertEqual(caught.exception.code, CODES["FU1"])
                self.assertEqual(fingerprint(state), before)
        state = play_flash(board(deck0=ENERGIES[:5], deck1=ENERGIES[:5]))  # ちょうど 5 枚は使える
        self.assertEqual(len(state.face_up_deck), 10)

    def test_reuse_replaces_marks_within_the_top_five(self):
        state = play_flash(board(hand=(FLASH, FLASH)))
        again = play_flash(state, first=lambda d: tuple(reversed(d.options)))
        self.assertEqual(len(FU.face_up_in_deck(again, 1)), 5)
        self.assertEqual(check_invariants(again), [])


class ObservationTest(unittest.TestCase):
    """4 章: 向き・知っている情報・いまの公開を分ける。"""

    def setUp(self):
        self.state = play_flash(board(), first=lambda d: tuple(reversed(d.options)))

    def test_top_public_rest_private(self):
        state = self.state
        top1 = state.cards[state.players[1].deck[0]].card_id
        for viewer in (0, 1, None):
            deck = observe(state, viewer)["players"][1]["deck"]
            self.assertEqual((deck["face_up_count"], deck["face_up_top"]), (5, {"card_id": top1}))
            self.assertEqual("known_face_up" in deck, viewer == 1)
            self.assertNotIn('"card"', json.dumps(deck))
        self.assertEqual(observation_problems(state), [])

    def test_hidden_positions_do_not_leak_through_the_log(self):
        """相手がいちばん上を同じにして下の並びを変えても、使ったプレイヤー・観戦者のログの写しと観測は同じ。"""
        views = []
        for first in (lambda d: tuple(d.options), lambda d: d.options[:1] + tuple(reversed(d.options[1:]))):
            state = play_flash(board(), first=first)
            views.append([(json.dumps(visible_log(state, viewer), default=str, ensure_ascii=False), json.dumps(observe(state, viewer)["players"][1]["deck"]))
                          for viewer in (0, None)])
        self.assertEqual(views[0], views[1])

    def test_check_request(self):
        state = self.state
        before = fingerprint(state)
        expected = {(0, 1, 2): CODES["FU2"], (1, 1, 2): "ALREADY_KNOWN", (0, 1, 0): "ALREADY_VISIBLE", (0, 1, 7): "NOT_FACE_UP", (1, 0, 3): CODES["FU2"]}
        for (player, owner, position), code in expected.items():
            with self.subTest(player=player, owner=owner, position=position):
                with self.assertRaises((IllegalActionError, UnsupportedError)) as caught:
                    apply_command(state, CheckFaceUpDeckCard(player, owner, position))
                self.assertEqual(caught.exception.code, code)
                self.assertNotIn(state.cards[state.players[owner].deck[position]].card_id, caught.exception.message)
                self.assertEqual(fingerprint(state), before)


class OperationTest(unittest.TestCase):
    """6 章: 操作ごとの確定経路と停止の境界。"""

    def test_normal_draw_reveals_next_top(self):
        state = play_flash(board())
        second = state.cards[state.players[1].deck[1]].card_id
        drawn = state.players[1].deck[0]
        state = apply_command(state, EndTurn(0))
        self.assertIn(drawn, state.players[1].hand)
        self.assertNotIn(drawn, state.face_up_deck)
        self.assertEqual(observe(state, 0)["players"][1]["deck"]["face_up_top"], {"card_id": second})
        last = [e for e in state.log if e["kind"] == "face_up_deck_top"][-1]
        self.assertEqual((last["player"], last["card_id"], last["face_up_count"]), (1, second, 4))
        self.assertEqual(observation_problems(state), [])
        self.assertEqual(face_up_deck_from_log(state), set(state.face_up_deck))

    def test_meowth_uses_the_visible_top_then_the_next_top_is_drawn(self):
        """CR-FLASH-TOP-CARD-SEEN の代表経路: サカキのニャースのてつだうふりが、見えている相手のいちばん上（トラッシュでないカード → 相手の手札）を動かし、同じコマンドで続く相手の番の
        最初の 1 枚ドローが、そのとき新しくいちばん上になったおもてのカードを引く（上から 1 枚ずつ別のログで動くので受け付ける。まとめて引く FU3 ではない）。"""
        from tests.helpers import H, with_coin_results

        state = build_test_state([{"active": {"card": "PMCG6-068", "energy": [FIGHTING_E] * 2}, "hand": [FLASH], "deck": list(ENERGIES) * 2, "prizes": 6},
                                  {"active": CHANSEY, "deck": list(reversed(ENERGIES)) * 2, "prizes": 6}])
        state = play_flash(state)
        top, second, third = state.players[1].deck[:3]
        self.assertEqual(observe(state, 0)["players"][1]["deck"]["face_up_top"]["card_id"], state.cards[top].card_id)
        after = apply_command(with_coin_results(state, H), UseAttack(0, 0))
        self.assertIn(top, after.players[1].hand)  # 基本エネルギー（トレーナーでない）は相手の手札
        self.assertIn(second, after.players[1].hand)  # 相手の番の最初のドロー
        self.assertEqual(after.players[1].deck[0], third)
        self.assertEqual(observe(after, 0)["players"][1]["deck"]["face_up_top"], {"card_id": after.cards[third].card_id})
        self.assertEqual(observation_problems(after), [])

    def test_multi_draw_stops_before_side_effects(self):
        for card_id in (BILL, OAK, TELEPORTER):
            with self.subTest(card=card_id):
                state = play_flash(board(hand=(FLASH, card_id)))
                before = fingerprint(state)
                with self.assertRaises(UnsupportedError) as caught:
                    apply_command(state, PlayTrainer(0, card_in_hand(state, card_id)))
                self.assertEqual(caught.exception.code, CODES["FU3"])
                self.assertEqual(fingerprint(state), before)

    def test_multi_draw_with_only_the_top_face_up_goes_through(self):
        state = play_flash(board(hand=(FLASH, BILL)))
        state.face_up_deck = tuple(uid for uid in state.face_up_deck if uid not in state.players[0].deck[1:])  # いちばん上だけがおもての盤面（テスト用）
        top = state.players[0].deck[0]
        after = apply_command(state, PlayTrainer(0, card_in_hand(state, BILL)))
        self.assertIn(top, after.players[0].hand)
        self.assertEqual(FU.face_up_in_deck(after, 0), ())

    def test_search_then_shuffle_clears_marks_without_extra_rng(self):
        state = play_flash(board(hand=(FLASH, COMPUTER_SEARCH, BILL, OAK)))
        state = apply_command(state, PlayTrainer(0, card_in_hand(state, COMPUTER_SEARCH)))
        d = state.decision  # 手札 2 枚をすてる
        state = apply_command(state, ResolveDecision(0, d.id, tuple(uid for uid in d.options if state.cards[uid].card_id in (BILL, OAK))))
        d = state.decision
        hidden = [uid for uid in state.players[0].deck[1:] if uid in state.face_up_deck]
        with self.assertRaises(UnsupportedError) as caught:
            apply_command(state, ResolveDecision(0, d.id, (hidden[0],)))
        self.assertEqual(caught.exception.code, CODES["FU3"])
        chosen = next(uid for uid in d.options if uid not in state.face_up_deck)
        rng = _copy.deepcopy(state.rng)
        after = apply_command(state, ResolveDecision(0, d.id, (chosen,)))
        self.assertEqual(FU.face_up_in_deck(after, 0), ())
        shuffle = [e for e in after.log if e["kind"] == "shuffle"][-1]
        self.assertEqual(shuffle["face_up_cleared"], 5)
        # 乱数: 印の有無で、切ることの乱数の使い方は変わらない（印を消してから、同じ 1 回の shuffle）
        deck = [uid for uid in state.players[0].deck if uid != chosen]
        rng.shuffle(deck)
        self.assertEqual(after.players[0].deck, deck)
        self.assertTrue(any(e["kind"] == "flash_face_up" and e["owner"] == 0 for e in after.log))  # 記憶（公開のログ）は残る
        self.assertEqual(observation_problems(after), [])
        top = state.players[0].deck[0]
        if top in d.options:
            apply_command(state, ResolveDecision(0, d.id, (top,)))  # いちばん上（見えている）を取るのは受け付ける

    def test_shuffle_without_marks_is_unchanged(self):
        state = board(hand=(COMPUTER_SEARCH, BILL, OAK))
        state = apply_command(state, PlayTrainer(0, card_in_hand(state, COMPUTER_SEARCH)))
        d = state.decision
        state = apply_command(state, ResolveDecision(0, d.id, tuple(uid for uid in d.options if state.cards[uid].card_id in (BILL, OAK))))
        d = state.decision
        after = apply_command(state, ResolveDecision(0, d.id, (d.options[0],)))
        self.assertEqual(set([e for e in after.log if e["kind"] == "shuffle"][-1]), {"kind", "turn", "player"})

    def test_place_on_top_stops_only_with_face_up(self):
        plain = board(hand=(RETRIEVER,), discard0=(RATICATE_C,))
        apply_command(plain, PlayTrainer(0, card_in_hand(plain, RETRIEVER)))  # おもてのない山札は v0.125 までと同じ
        state = play_flash(board(hand=(FLASH, RETRIEVER), discard0=(RATICATE_C,)))
        before = fingerprint(state)
        with self.assertRaises(UnsupportedError) as caught:
            apply_command(state, PlayTrainer(0, card_in_hand(state, RETRIEVER)))
        self.assertEqual(caught.exception.code, CODES["FU4"])
        self.assertEqual(fingerprint(state), before)

    def test_look_and_return_stops_but_declining_is_accepted(self):
        state = play_flash(board(hand=(FLASH, POKEDEX)))
        state = apply_command(state, PlayTrainer(0, card_in_hand(state, POKEDEX)))
        d = state.decision
        for count in d.options:
            if count == 0:
                after = apply_command(state, ResolveDecision(0, d.id, (0,)))
                self.assertEqual(FU.face_up_in_deck(after, 0), FU.face_up_in_deck(state, 0))
                continue
            with self.assertRaises(UnsupportedError) as caught:
                apply_command(state, ResolveDecision(0, d.id, (count,)))
            self.assertEqual(caught.exception.code, CODES["FU5"])

    def test_swap_prize_with_face_up_top_stops_before_declaring(self):
        """FU6: ［わるふざけ］（PMCG4-045）でサイドと山札のいちばん上を入れかえる。おもての山札なら宣言の前に止め、おもてのない山札では v0.125 までと同じに使える。"""
        from kyuura_engine import UsePokemonPower

        def side():
            return build_test_state([{"active": "PMCG4-045", "hand": [FLASH], "deck": list(ENERGIES) * 2, "prizes": 6},
                                     {"active": CHANSEY, "deck": list(ENERGIES) * 2, "prizes": 6}])

        plain = side()
        apply_command(plain, UsePokemonPower(0, plain.players[0].active.pokemon_id, 0))
        state = play_flash(side())
        before = fingerprint(state)
        with self.assertRaises(UnsupportedError) as caught:
            apply_command(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        self.assertEqual(caught.exception.code, CODES["FU6"])
        self.assertEqual(fingerprint(state), before)

    def test_radio_tower(self):
        state = play_flash(board(hand=(FLASH, RADIO_TOWER)))
        state = apply_command(state, PlayTrainer(0, card_in_hand(state, RADIO_TOWER)))
        state = apply_command(state, UseStadium(0))
        d = state.decision
        with self.assertRaises(UnsupportedError) as caught:
            apply_command(state, ResolveDecision(0, d.id, (1,)))
        self.assertEqual(caught.exception.code, CODES["FU5"])
        apply_command(state, ResolveDecision(0, d.id, (0,)))


class PersistenceTest(unittest.TestCase):
    """7 章: 保存・複製で、向き・順序・決定の段階・使用中のカードを保つ。形式 31。"""

    def test_mid_flash_copies_continue_identically(self):
        state = apply_command(board(), PlayTrainer(0, card_in_hand(board(), FLASH)))
        d = state.decision
        mid = apply_command(state, ResolveDecision(1, d.id, tuple(reversed(d.options))))
        finals = []
        for copy in (mid, mid.clone(), _copy.deepcopy(mid), _pickle.loads(_pickle.dumps(mid))):
            self.assertEqual((copy.face_up_deck, copy.decision, copy.trainer_in_use), (mid.face_up_deck, mid.decision, mid.trainer_in_use))
            d2 = copy.decision
            done = apply_command(copy, ResolveDecision(0, d2.id, tuple(reversed(d2.options))))
            finals.append(fingerprint(apply_command(done, EndTurn(0))))
        self.assertEqual(len(set(finals)), 1)

    def test_format_31(self):
        state = play_flash(board())
        self.assertGreaterEqual(max(FORMAT_VERSIONS), 31)  # v0.127 で形式 32（途中停止）を加えた
        self.assertEqual(state_to_dict(state, format_version=31)["face_up_deck"], list(state.face_up_deck))
        for version in (1, 29, 30):
            with self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)
        plain = board()
        self.assertEqual({k: v for k, v in state_to_dict(plain, format_version=31).items() if k not in ("face_up_deck", "format_version")},
                         {k: v for k, v in state_to_dict(plain, format_version=30).items() if k != "format_version"})
        self.assertEqual(serialization_problems(state), [])
        old = _pickle.loads(_pickle.dumps(plain))
        old.__dict__.pop("face_up_deck", None)  # v0.125 までの写し（項目がない）
        self.assertEqual(old.face_up_deck, ())


class AuditTest(unittest.TestCase):
    """7 章: 監査は、エンジンが出した公開範囲を正解にしない（ログから組み立てた印・観測と照らす）。"""

    @classmethod
    def setUpClass(cls):
        from tools import existing_effect_games as games

        cls.result = games.play(("M126", "F126"), 90, keep_state=True)  # 開発用の seed（正式な対戦の seed 0〜3 とは別）
        cls.done = cls.result["state"]

    def test_real_game_passes(self):
        from tests.log_audit import log_problems

        self.assertEqual(self.result["audit"], {})
        self.assertGreater(self.result["v126"]["flash_arranged"], 0)
        self.assertGreater(self.result["v126"]["drew_face_up"], 0)
        self.assertEqual(log_problems(self.done), [])

    def test_tampered_logs_are_found(self):
        from types import MappingProxyType

        from tests.log_audit import log_problems

        face_up = next(e for e in self.done.log if e["kind"] == "flash_face_up")
        top = next(e for e in self.done.log if e["kind"] == "face_up_deck_top" and e["card_id"] is not None)
        other = next(cid for cid in ENERGIES + (FLASH,) if cid != top["card_id"] and cid != face_up["top_card_id"])
        changes = {
            "公開したいちばん上": lambda e: MappingProxyType(dict(e, top_card_id=other)) if e is face_up else e,
            "uid を書いた": lambda e: MappingProxyType(dict(e, card=1)) if e is face_up else e,
            "次のいちばん上": lambda e: MappingProxyType(dict(e, card_id=other)) if e is top else e,
        }
        cleared = next((e for e in self.done.log if e["kind"] == "shuffle" and e.get("face_up_cleared")), None)
        self.assertIsNotNone(cleared)
        changes["印の消し忘れ"] = lambda e: MappingProxyType({k: v for k, v in e.items() if k != "face_up_cleared"}) if e is cleared else e
        for name, change in changes.items():
            with self.subTest(name=name):
                tampered = self.done.clone()
                tampered.log = tuple(change(e) for e in self.done.log)
                self.assertTrue(log_problems(tampered), name)

    def test_observation_leak_is_found(self):
        tampered = self.done.clone()
        extra = next(uid for p in tampered.players for uid in p.deck if uid not in tampered.face_up_deck)
        tampered.face_up_deck = tampered.face_up_deck + (extra,)
        self.assertTrue(observation_problems(tampered))


class DocumentTest(unittest.TestCase):
    """10 章: 版の文書・対応状況・裁定・データの来歴・README の v0.126。"""

    def test_documents(self):
        doc = (ROOT / "docs" / "flash-faceup-deck-v0.126.md").read_text(encoding="utf-8")
        for short, code in CODES.items():
            self.assertIn(f"| {short} | `{code}` |", doc)
        self.assertIn("UNSUPPORTED_FACE_UP_DECK_PATH", doc)
        self.assertIn(E.FLASH_LATEST_TEXT, doc)
        self.assertRegex((ROOT / "README.md").read_text(encoding="utf-8"), r"\n- v0\.126（(今のエンジンの版。)?`kyuura_engine` の版は 0\.126\.0）: フラッシュと表向きの山札")
        self.assertIn("## v0.126: フラッシュと表向きの山札\n", (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8"))
        self.assertIn("### v0.126: フラッシュと表向きの山札", (ROOT / "docs" / "rules-2000-02-14.md").read_text(encoding="utf-8"))
        self.assertIn("## v0.126: 写しの元・研究の基準を kyuura 57d01f4 に上げる移行", (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
