"""v0.123（docs/arcanine-name-migration-v0.123.md）: 写しの元・研究の基準の移行（kyuura 2fe0bc0 → 74b3ceb。登録済みのウィンディ 2 枚の名前の訂正）と、ウィンディ系の 3 枚（ワザ 5）。

2 章: 移行だけの段。kyuura が同じカードの画像で確かめて直した PMCG1-019「ウインディ」→「ウィンディ」・PMCG6-034「カツラのウインディ」→「カツラのウィンディ」（訂正の種類は
生成の値の誤り ``generated_value_error``）を写しの移行の段 v0.123 で受け付け、採用の記録・研究の対応表をそろえる。エンジンは画像を見ていない（kyuura の画像の照合を再利用しただけ）。

3 章〜5 章: カツラのウィンディ（GD5-007）・ウィンディ（IP2-032・PR1-016）。盤面は ``build_test_state`` と通常の操作で作った規定の確かめで、``new_game`` からの自然な対戦の結果ではない
（正式な開始からの対戦は ``AuditTest``）。
"""

from __future__ import annotations

import copy
import dataclasses
import datetime
import json
import pathlib
import pickle
import subprocess
import unittest
from typing import ClassVar

from kyuura_engine import ResolveDecision, UseAttack, deck
from kyuura_engine import effects as E
from kyuura_engine.cards import (
    EnergyType,
    load_card_pool,
    pool_from_extract,
    read_extract,
)
from kyuura_engine.coins import CoinSide
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from scripts import check_card_sources as cs
from scripts import check_research_links as rl
from tests import helpers as H
from tests.release_catalog import cards_after, cards_before
from tests.test_baby_rules_evolution_v0_114 import extract_module
from tests.test_fossil_basic_virtual_attacks_v0_120 import spec, table, trainer
from tests.test_neo_trainer_components_v0_80 import audited, new_events
from tests.test_unown_family_powers_v0_96 import snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
LINKS_PATH = ROOT / "kyuura_engine" / "data" / "research_links.json"
NOW, V0121 = "74b3ceb883dd815495d13b9987433fb14b36e44d", "2fe0bc042ce187d191843819262f8036abbb343d"
ECB, V069, V097, V0114 = ("ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3", "73a169063463bbf7bcaa3137d70cbf9721d11534",
                          "e519b99e2adcc6c2cd0998569ae5ee1101de6e89")
BASE_ENGINE = "e080c9e34989fc94ad4add1e8e579738b237fd6f"  # v0.122（この版の基点）
V0123_FINAL = "25552b8ca6292232e51e188d2be66af36ef7bf55"  # v0.123 の最後のコミット（v0.124 で研究の基準を上げたので、この版の対応表の値はここで確かめる）
ARCANINE, BLAINES_ARCANINE, KIND_ARCANINE = "PMCG1-019", "PMCG6-034", "neo4-021"
RENAMED = {ARCANINE: ("FIX-PMCG1-019-NAME-JA", "IMG-PMCG1-019", "ウインディ", "ウィンディ"),
           BLAINES_ARCANINE: ("FIX-PMCG6-034-NAME-JA", "IMG-PMCG6-034", "カツラのウインディ", "カツラのウィンディ")}
NEW_TARGETS = ("GD5-007", "IP2-032", "PR1-016")  # 4 章で登録するカード（移行の段では値が変わらない）
NEW_ISSUES = ("UQ-BILINGUAL-NAME-GLOSS", "UQ-MIND-GAMES-OPTIONAL", "UQ-MIND-GAMES-TRAINER-STEP", "UQ-FLASH-FACE-UP-DECK", "UQ-SWAP-PLEASE-OWNERSHIP")


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
    """2.1 節: 段 v0.123（2fe0bc0 → 74b3ceb）。過去の段の値・採用の記録の移行は書き換えない。"""

    def test_chain(self):
        module = extract_module()
        # v0.124: 段 v0.124（74b3ceb → b9e7cff）を加え、v0.123 の段のあとは V0_123_KYUURA_COMMIT（74b3ceb）に固定した。今の写しの元は最後の段のあと
        # （docs/super-transform-dark-pulse-v0.124.md 2 章。今の値は tests/test_super_transform_dark_pulse_v0_124.py）
        self.assertEqual((module.V0_123_KYUURA_COMMIT, module.V0_121_KYUURA_COMMIT, module.V0_114_KYUURA_COMMIT), (NOW, V0121, V0114))
        self.assertEqual(module.migration_problems(), [])
        self.assertEqual([(s["id"], s["from"], s["to"], s["document"]) for s in module.KYUURA_MIGRATIONS][:5],
                         [("v0.69", ECB, V069, "docs/equivalent-non-pack-cards-v0.69.md"), ("v0.97", V069, V097, "docs/unown-research-idfnj-v0.97.md"),
                          ("v0.114", V097, V0114, "docs/baby-rules-evolution-v0.114.md"), ("v0.121", V0114, V0121, "docs/hand-bench-attack-conditions-v0.121.md"),
                          ("v0.123", V0121, NOW, "docs/arcanine-name-migration-v0.123.md")])
        extract = read_extract()
        self.assertEqual((extract["source"]["commit"], extract["previous_source"]["commit"]), (module.KYUURA_MIGRATIONS[-1]["to"], ECB))
        self.assertEqual(extract["source_migrations"][4]["corrections"], ["FIX-PMCG1-019-NAME-JA", "FIX-PMCG6-034-NAME-JA"])
        # v0.121 の段のあとを写しの元の定数にもどすと、写しの元を上げたときに過去の段のあとまで変わる（連鎖が切れて止まる）
        steps = module.KYUURA_MIGRATIONS
        try:
            module.KYUURA_MIGRATIONS = (*steps[:3], {**steps[3], "to": module.KYUURA_COMMIT}, *steps[4:])
            self.assertTrue(any("その前の段のあと" in p for p in module.migration_problems()))
        finally:
            module.KYUURA_MIGRATIONS = steps
        # 利用者が示した PR1-069 の名前の訂正（kyuura はまだ直していない）は、今の写しの元でも同じ
        self.assertEqual([(c["card_id"], c["before"], c["after"], c["source_commit"]) for c in extract["engine_user_corrections"]],
                         [("PR1-069", "？？？", "ミュウ", module.KYUURA_COMMIT)])

    def test_adoption_migrations_are_appended(self):
        sources = cs.load_sources()
        self.assertEqual([(m["from"], m["to"], m["on"], m["document"]) for m in sources["data_migrations"]][:5],
                         [(ECB, V069, "2026-10-19", "docs/equivalent-non-pack-cards-v0.69.md"), (V069, V097, "2026-10-25", "docs/unown-research-idfnj-v0.97.md"),
                          (V097, V0114, "2026-10-28", "docs/baby-rules-evolution-v0.114.md"), (V0114, V0121, "2026-10-30", "docs/hand-bench-attack-conditions-v0.121.md"),
                          (V0121, NOW, "2026-10-31", "docs/arcanine-name-migration-v0.123.md")])
        self.assertEqual(cs.data_migrations(sources, read_extract())[1], [])
        # 採用したときのデータのコミットが 74b3ceb の記録は、この版で写しに加えたカード（pool_v0_123）だけ（移行の段では採用し直していない）
        self.assertEqual({card for card, record in sources["cards"].items() if record.get("kyuura_commit") == NOW}, set(read_extract().get("pool_v0_123", ())))

    def test_corrections_in_the_extract(self):
        corrections = {c["id"]: c for c in read_extract()["kyuura_corrections"] if c["migration"] == "v0.123"}
        self.assertEqual(sorted(corrections), sorted(fix for fix, *_ in RENAMED.values()))
        for card_id, (fix, image, before, after) in RENAMED.items():
            c = corrections[fix]
            self.assertEqual((c["card_id"], c["field"], c["before"], c["after"], c["basis"], c["kind"], c["image_check"], c["decided_on"]),
                             (card_id, "name.ja", before, after, "card_image_check", "generated_value_error", image, "2026-10-30"))
            self.assertEqual((c["kyuura_saw_image"], c["engine_saw_image"], c["applied_in_source"], c["previous_source"]), (True, False, NOW, V0121))
            self.assertFalse({"record", "commit", "kyuura_record"} & set(c))  # CC-・LD- の照合の記録ではない
        self.assertEqual(len(corrections[RENAMED[ARCANINE][0]]["evidence"]), 2)  # pcg-search.com となぞのばしょ（独立した 2 枚には数えない。kyuura の independence）
        self.assertEqual(len(corrections[RENAMED[BLAINES_ARCANINE][0]]["evidence"]), 1)

    @needs_history
    def test_extract_changes_only_the_two_names(self):
        """基点 v0.122 の写しの 1,355 枚のうち、変わったのは 2 枚の名前と、付随する notes・corrections だけ。"""
        before = {card["id"]: card for card in engine_json(BASE_ENGINE, "kyuura_engine/data/kyuura_cards.json")["cards"]}
        now = {card["id"]: card for card in read_extract()["cards"]}
        self.assertEqual(len(before), 1355)
        self.assertLessEqual(set(before), set(now))
        changed = {card for card in before if before[card] != now[card]}
        self.assertEqual(changed, set(RENAMED))
        for card_id, (fix, _, old, new) in RENAMED.items():
            self.assertEqual((before[card_id]["name"]["ja"], now[card_id]["name"]["ja"], now[card_id]["name"]["en"]), (old, new, before[card_id]["name"]["en"]))
            self.assertEqual(now[card_id]["pokemon"], before[card_id]["pokemon"])  # ワザ・HP など処理に使うほかの欄は同じ（ワザの文面も同じ）
            self.assertEqual([x["id"] for x in now[card_id]["corrections"]], [fix])
            self.assertNotIn("corrections", before[card_id])
        # やさしいウインディは今回の訂正の外（名前は変えていない。部分文字列で置きかえない）
        self.assertEqual((before[KIND_ARCANINE]["name"]["ja"], now[KIND_ARCANINE]["name"]["ja"]), ("やさしいウインディ", "やさしいウインディ"))

    @needs_kyuura
    def test_kyuura_difference_is_two_names(self):
        """2fe0bc0 → 74b3ceb の data/cards.json 全 1,377 件: 値が変わったのは登録済みの 2 枚の name・notes・corrections だけ。エンジンが使う欄は name.ja だけが違う。"""
        old, new = (kyuura_json(commit, "data/cards.json") for commit in (V0121, NOW))
        self.assertEqual({k: v for k, v in old.items() if k != "cards"}, {k: v for k, v in new.items() if k != "cards"})
        self.assertEqual([c["id"] for c in old["cards"]], [c["id"] for c in new["cards"]])
        self.assertEqual(len(new["cards"]), 1377)
        before = {c["id"]: c for c in old["cards"]}
        changed = {c["id"]: {k for k in set(c) | set(before[c["id"]]) if c.get(k) != before[c["id"]].get(k)} for c in new["cards"] if c != before[c["id"]]}
        self.assertEqual(changed, {ARCANINE: {"name", "notes", "corrections"}, BLAINES_ARCANINE: {"name", "notes", "corrections"}})
        module = extract_module()
        after = {c["id"]: c for c in new["cards"]}
        for card_id in RENAMED:
            used = [f for f in module.FIELDS_USED_BY_ENGINE if "[" not in f and module.field_or_absent(before[card_id], f) != module.field_or_absent(after[card_id], f)]
            self.assertEqual(used, ["name.ja"])
        for card_id in NEW_TARGETS:
            self.assertEqual(before[card_id], after[card_id], card_id)


class GeneratedValueKindTest(unittest.TestCase):
    """2.2 節: 生成の値の誤り（``generated_value_error``）の受け付け。根拠・欄・前後の値を確かめ、未知の種類・ほかの種類への書きかえ・画像の根拠の違いを受け付けない。"""

    def test_kind_rules_without_kyuura(self):
        module = extract_module()
        self.assertIn("generated_value_error", module.CORRECTION_KINDS)
        self.assertEqual(module.GENERATED_VALUE_FIELDS, ("name.ja",))
        good = next(c for c in module.KYUURA_CORRECTIONS if c["id"] == "FIX-PMCG1-019-NAME-JA")
        self.assertEqual(module.generated_value_problems("x", good), [])
        self.assertTrue(module.generated_value_problems("x", {**good, "basis": "user_provided"}))
        self.assertTrue(module.generated_value_problems("x", {**good, "field": "pokemon.hp"}))
        self.assertTrue(module.generated_value_problems("x", {**good, "before": None}))  # 欠けを埋める修正ではない
        self.assertTrue(module.generated_value_problems("x", {**good, "after": good["before"]}))
        self.assertEqual(module.generated_value_problems("x", {**good, "kind": "transcription_error"}), [])  # ほかの種類はこの確かめの外（台帳と照らす）

    @needs_kyuura
    def test_ledger_and_image_checks(self):
        module = extract_module()
        source = module.read_kyuura_cards(KYUURA)
        previous = json.loads(module._show(KYUURA, module.PREVIOUS_KYUURA_COMMIT, module.KYUURA_PATH).decode("utf-8"))
        pool = module.all_pool_cards() + module.REFERENCE_ONLY
        self.assertEqual(module.kyuura_correction_problems(KYUURA, source, previous, pool), [])
        self.assertEqual(module.migration_copy_problems(KYUURA, source, previous, pool), [])
        original = list(module.KYUURA_CORRECTIONS)
        index = next(i for i, c in enumerate(original) if c["id"] == "FIX-PMCG1-019-NAME-JA")

        def problems_with(**changes):
            module.KYUURA_CORRECTIONS[:] = [*original[:index], {**original[index], **changes}, *original[index + 1:]]
            try:
                return module.kyuura_correction_problems(KYUURA, source, previous, pool)
            finally:
                module.KYUURA_CORRECTIONS[:] = original

        # 種類を転記の誤りに書きかえると台帳と合わない。未知の種類は扱えない
        self.assertTrue(any("台帳の kind" in p for p in problems_with(kind="transcription_error")))
        unknown = problems_with(kind="unknown_error")
        self.assertTrue(any("台帳の kind" in p for p in unknown) and any("扱えない" in p for p in unknown))
        # 画像の根拠（URL・sha256・取得日）・画像の照合の記録が台帳と違えば受け付けない
        evidence = [dict(original[index]["evidence"][0], image_sha256="0" * 64), original[index]["evidence"][1]]
        self.assertTrue(any("evidence" in p for p in problems_with(evidence=evidence)))
        self.assertTrue(any("evidence" in p for p in problems_with(evidence=original[index]["evidence"][:1])))
        self.assertTrue(any("画像の照合の記録" in p for p in problems_with(image_check="IMG-PMCG6-034")))
        # 段の前後の値・段が合わなければ受け付けない（v0.121 の段の訂正にしない）
        self.assertTrue(any("移行の段 v0.123 の前の写しの元（2fe0bc0）の値が 'ウインデイ' ではない" in p for p in problems_with(before="ウインデイ")))
        self.assertTrue(any("移行の段 v0.121 のあと（2fe0bc0）の値が 'ウィンディ' ではない" in p for p in problems_with(migration="v0.121")))
        # 台帳の訂正を挙げていなければ、知らない修正として書き出さない
        module.KYUURA_CORRECTIONS[:] = [c for c in original if c["id"] != "FIX-PMCG1-019-NAME-JA"]
        try:
            missing = module.kyuura_correction_problems(KYUURA, source, previous, pool)
            self.assertTrue(any("FIX-PMCG1-019-NAME-JA" in p and "挙げていない" in p for p in missing))
            self.assertTrue(any("PMCG1-019" in p for p in module.migration_copy_problems(KYUURA, source, previous, pool)))  # 名前の違いを見落とさない
        finally:
            module.KYUURA_CORRECTIONS[:] = original


class AdoptionRecordTest(unittest.TestCase):
    """2.3 節: 採用の記録。名前を写しにそろえ、報告事項の解決を日付つきで追記した。当時の外部照合の値・日付・コミットは書き換えない。"""

    def test_names_issues_and_external_checks(self):
        cards = cs.load_sources()["cards"]
        for card_id, (fix, image, old, new) in RENAMED.items():
            record = cards[card_id]
            self.assertEqual((record["name_ja"], record["kyuura_commit"], record["recorded_on"]), (new, ECB, "2026-10-15"))
            [check] = record["external_checks"]
            self.assertEqual((check["kyuura_commit"], check["checked_on"], check["result"]), (ECB, "2026-10-15", "differences"))
            self.assertEqual([(d["field"], d["kyuura"], d["pcg_search"], d["affects_behavior"]) for d in check["differences"]], [("name.ja", old, new, False)])
            [issue] = record["issues"]
            self.assertIn("どちらが印刷の表記か", issue["question"])
            self.assertIn("2026-10-31（v0.123", issue["note"])
            self.assertTrue(all(text in issue["note"] for text in (fix, image, "解決した", "画像を読んでおらず", "エンジンは今回も画像を見ていない")))
            self.assertEqual(record["kyuura_records"], H.kyuura_records_since_v0_69(card_id, ["RUL-ENERGY-DISCARD-ATTACKS"] if card_id == ARCANINE else []))

    def test_check_before_the_correction_uses_the_before_value(self):
        """2026-10-15 に ecb2d69 と照らした違いの kyuura の値は、訂正の前の値（段 v0.123 の前）なので受け付ける。今の写しの元と照らしたことにすると受け付けない。"""
        sources = cs.load_sources()
        extract = read_extract()
        earlier, _ = cs.data_migrations(sources, extract)
        cards = {c["id"]: c for c in extract["cards"]}
        corrections = {(c["card_id"], c["field"]): c for c in extract["kyuura_corrections"]}
        today = datetime.date(2026, 10, 31)
        check = sources["cards"][ARCANINE]["external_checks"][0]
        found = cs.check_problems("x", check, cards[ARCANINE], extract["source"]["commit"], today, corrections, earlier)
        self.assertEqual(found, [])
        moved = dict(check, kyuura_commit=NOW)
        self.assertTrue(any("kyuura の値が写しの値と違う" in p for p in cs.check_problems("x", moved, cards[ARCANINE], extract["source"]["commit"], today, corrections, earlier)))
        other = copy.deepcopy(check)
        other["differences"][0]["kyuura"] = "ウインデイ"
        self.assertTrue(any("kyuura の値が写しの値と違う" in p for p in cs.check_problems("x", other, cards[ARCANINE], extract["source"]["commit"], today, corrections, earlier)))

    def test_records_added_by_the_research_commit(self):
        cards = cs.load_sources()["cards"]
        for card_id, added in H.V0_123_KYUURA_RECORDS_ADDED.items():
            self.assertLessEqual(set(added), set(cards[card_id]["kyuura_records"]), card_id)
        # やさしいウインディ（neo4-021）は裁定の related_cards（名前の数え方には関わらない別の名前）。名前・処理は変えていない
        self.assertEqual(cards[KIND_ARCANINE]["name_ja"], "やさしいウインディ")


class ResearchLinksTest(unittest.TestCase):
    """2.4 節: 研究の対応表。論点 74 → 79。新しい 5 論点と、既存の 2 論点に加わった事例。kyuura の 79 件を停止コード・未解決の数にそろえない。"""

    @classmethod
    def setUpClass(cls):
        cls.links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))

    def test_commits_and_counts(self):
        # v0.124: 研究の基準を b9e7cff に上げた（今の値は tests/test_super_transform_dark_pulse_v0_124.py・tests/test_catalog_contract.py）。v0.123 の値は、その版の最後のコミットの対応表で確かめる
        links = engine_json(V0123_FINAL, "kyuura_engine/data/research_links.json") if (ROOT / ".git").exists() else None
        if links is None:
            self.skipTest("このリポジトリの git の履歴がない（取り出した木）")
        self.assertEqual((links["research_commit"], links["card_data_commit"], links["research_branch"]), (NOW, NOW, "claude/v0122-names-text-trainer-procedures"))
        self.assertEqual((links["counts"]["kyuura_issues"], links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (79, 292, 293))
        self.assertEqual(links["engine_import_id"], "ENGINE-46A3E2E")
        self.assertEqual(self.links["engine_import_id"], "ENGINE-46A3E2E")

    def test_new_cases(self):
        added = [c for c in self.links["kyuura_cases_without_engine_ruling"]["cases"] if "v0.123 で研究の基準を 74b3ceb に上げて結んだ" in c.get("note", "")]
        self.assertEqual(len(added), 25)
        self.assertEqual({c["kyuura_issue"] for c in added}, {*NEW_ISSUES, "UQ-STATED-COUNT-SHORT", "UQ-CHAOS-GYM-BORROWED-TURN"})
        unregistered = {(c["kyuura_issue"], c["card_id"]) for c in added if c["engine"] == {"unregistered": True}}
        self.assertEqual({card for _, card in unregistered}, {"PR1-075", "PR1-077", "PR1-027", "ES2-035", "neo1-049"})
        self.assertEqual(len(unregistered), 10)
        required = {(c["kyuura_issue"], c["card_id"]): tuple(c["engine"]["requires_unregistered"]) for c in added if "requires_unregistered" in c["engine"]}
        self.assertEqual(len(required) + len(unregistered), 25)
        self.assertEqual(set(required.values()), {("PR1-075", "PR1-077"), ("ES2-035", "neo1-049"), ("neo1-049",), ("PR1-027",)})
        self.assertFalse([c for c in added if "stop_codes" in c["engine"] or "codeless_question" in c["engine"]])  # 新しい停止コード・問いを作っていない
        pool = load_card_pool()
        for (_, card), others in required.items():
            self.assertIn(card, pool.playable_ids, card)
            self.assertFalse(set(others) & pool.playable_ids, card)

    def test_requires_unregistered_is_checked(self):
        """``requires_unregistered``: 挙げたカードは、同じ論点の事例のカードで、登録していない。事例のカードは登録している。"""
        from kyuura_engine.effects import DEFAULT_EFFECTS

        issues = {"UQ-X": {"cases": [{"card_id": "PMCG5-087", "target": {"kind": "trainer"}}, {"card_id": "PR1-027", "target": {"kind": "trainer"}}]}}

        def problems(engine, card="PMCG5-087"):
            links = {"stop_codes": {}, "codeless_questions": {}, "kyuura_cases_without_engine_ruling": {"cases": [
                {"kyuura_issue": "UQ-X", "card_id": card, "target": "trainer", "engine": engine},
                {"kyuura_issue": "UQ-X", "card_id": "PR1-027" if card != "PR1-027" else "PMCG5-087", "target": "trainer",
                 "engine": {"unregistered": True} if card != "PR1-027" else {"requires_unregistered": ["PR1-027"]}}]}}
            return rl.unlinked_case_problems(links, issues, DEFAULT_EFFECTS)

        self.assertEqual(problems({"requires_unregistered": ["PR1-027"]}), [])
        self.assertTrue(any("登録されている" in p for p in problems({"requires_unregistered": ["PMCG1-019"]})))  # 登録したカード（同じ論点の事例でもない）
        self.assertTrue(any("事例のカードではない" in p for p in problems({"requires_unregistered": ["neo1-049"]})))
        self.assertTrue(any("重ならないリスト" in p for p in problems({"requires_unregistered": []})))
        self.assertTrue(any("重ならないリスト" in p for p in problems({"requires_unregistered": ["PMCG5-087"]})))  # 事例のカードそのもの
        self.assertTrue(any("ちょうど 1 つ" in p for p in problems({"requires_unregistered": ["PR1-027"], "unregistered": True})))

    @needs_kyuura
    def test_links_agree_with_kyuura(self):
        self.assertEqual(rl.check(KYUURA), [])


class NameTest(unittest.TestCase):
    """2.5 節: 移行のあとの名前。新しい名前を別名として足さず、2 枚の名前が置きかわる（読み替えの表・正規化は加えない）。"""

    def test_names_in_the_pool(self):
        pool = load_card_pool()
        self.assertEqual((pool.get(ARCANINE).name_ja, pool.get(BLAINES_ARCANINE).name_ja, pool.get(KIND_ARCANINE).name_ja),
                         ("ウィンディ", "カツラのウィンディ", "やさしいウインディ"))
        self.assertEqual(dict(deck.SAME_NAME_SPELLINGS), {"ポケモン図鑑HANDY505": "ポケモン図鑑 HANDY505"})
        names = {pool.get(card).name_ja for card in pool.playable_ids if pool.get(card).category == "pokemon"}
        self.assertTrue({"ウィンディ", "カツラのウィンディ", "やさしいウインディ"} <= names)
        self.assertFalse({"ウインディ", "カツラのウインディ"} & names)
        # v0.124 で「GR団のミュウツー」が加わって 510（今の値は tests/test_catalog_contract.py）。v0.123 の版の範囲の名前は 509
        self.assertEqual(len(names - {"GR団のミュウツー"}), 509)
        self.assertEqual(deck.same_name("ウィンディ"), "ウィンディ")
        self.assertNotEqual(deck.same_name("ウィンディ"), deck.same_name("カツラのウィンディ"))


# ---------------------------------------------------------------- 3 章〜5 章: 3 枚の登録

V0123 = NEW_TARGETS
BLAINES_ARCANINE_GYM, ARCANINE_INTRO, ARCANINE_PROMO = V0123
GROWLITHE, BLAINES_GROWLITHE, CLEFAIRY, CLEFABLE, ECOGYM = "PMCG1-018", "PMCG6-027", "PMCG1-067", "PMCG2-044", "neo1-086"
F, W, P_ = H.FIRE, H.WATER, H.PSYCHIC
HD, TL = CoinSide.HEADS, CoinSide.TAILS
RAGE_TEXT = "このカードについている「炎」エネルギーカードを2枚はがして捨てなければこのワザは使えない。自分にのっているダメージカウンター×10のダメージを追加する"


def run(state, command, *coins):
    return H.apply_kernel(H.with_coin_results(state, *coins) if coins else state, command)


def answer(state, choices, *coins):
    d = state.decision
    return run(state, ResolveDecision(d.player, d.id, tuple(choices)), *coins)


def promo(energy=(F, F), damage=0, **extra):
    return spec(ARCANINE_PROMO, energy, below=(GROWLITHE,), damage=damage, **extra)


def rejected(test, state, fn, code):
    before = snap(state)
    with test.assertRaises((IllegalActionError, UnsupportedError)) as raised:
        fn(state)
    test.assertEqual(raised.exception.code, code)
    test.assertEqual(snap(state), before)


class RegistrationTest(unittest.TestCase):
    """3 章: 3 枚・ワザ 5 の登録、再利用した型の数値、採用の記録、研究の対応表、登録を外したときの数。"""

    def test_cards_and_registrations(self):
        pool = load_card_pool()
        extract = read_extract()
        self.assertEqual(extract["pool_v0_123"], list(V0123))
        registry = E.DEFAULT_EFFECTS
        self.assertEqual(sorted(k for k in registry.attack_keys() if k.card_id in V0123), sorted(E.V0_123_ATTACKS))
        self.assertEqual(len(E.V0_123_ATTACKS), 5)
        self.assertFalse([k for k in registry.power_keys() if k.card_id in V0123] + [c for c in registry.trainer_ids() if c in V0123])
        for key in E.V0_123_ATTACKS:
            definition = pool.get(key.card_id)
            attack = definition.attacks[key.attack_index]
            entry = registry.attack_entry(key.card_id, key.attack_index)
            self.assertIn(key.card_id, pool.playable_ids)
            self.assertIsNone(registry.attack_problem(key.card_id, attack, definition.attacks), key)
            self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (attack.text_ja, attack.text_ja, "kyuura data/cards.json"), key)
        effect = {(k.card_id, k.attack_index): registry.attack_entry(k.card_id, k.attack_index).effect for k in E.V0_123_ATTACKS}
        self.assertEqual(effect, {
            (BLAINES_ARCANINE_GYM, 0): E.DamageAndSelfDamage(10),
            (BLAINES_ARCANINE_GYM, 1): E.DiscardEnergyBeforeDamage(EnergyType.FIRE, 3, "effect", "cannot_use"),
            (ARCANINE_INTRO, 0): E.DamageAndSelfDamage(20),
            (ARCANINE_PROMO, 0): E.CoinBonusDamage(20),
            (ARCANINE_PROMO, 1): E.DiscardEnergyBeforeDamagePlusOwnCounters(EnergyType.FIRE, 2, 10),
        })
        # 第1弾のとっしん（80・自分にも 30）と、イントロパックのとっしん（50・自分にも 20）は別の数値
        first, intro = pool.get(ARCANINE).attacks[1], pool.get(ARCANINE_INTRO).attacks[0]
        self.assertEqual([(a.name_ja, a.damage, a.text_ja) for a in (first, intro)], [("とっしん", 80, "自分にも30ダメージ。"), ("とっしん", 50, "自分にも20ダメージ。")])
        self.assertEqual(registry.attack_entry(ARCANINE, 1).effect, E.DamageAndSelfDamage(30))
        rage = pool.get(ARCANINE_PROMO).attacks[1]
        self.assertEqual((rage.damage, rage.damage_modifier, rage.text_ja), (40, "+", RAGE_TEXT))

    def test_gym_card_shares_the_blaines_arcanine_registration(self):
        """GD5-007 は PMCG6-034 と処理に使う欄が id のほかすべて同じ（SC-GD5-007）。登録は同じ値（同じオブジェクト）で、id ごとに持つ。"""
        extract = {c["id"]: c for c in read_extract()["cards"]}
        gym, dark = extract[BLAINES_ARCANINE_GYM], extract[BLAINES_ARCANINE]
        self.assertEqual((gym["name"], gym["category"], gym["pokemon"], gym["same_card_group"]), (dark["name"], dark["category"], dark["pokemon"], dark["same_card_group"]))
        self.assertEqual(dict(E.SAME_DATA_CARDS_V0_123), {BLAINES_ARCANINE_GYM: BLAINES_ARCANINE})
        for index in (0, 1):
            self.assertIs(E.DEFAULT_EFFECTS.attack_entry(BLAINES_ARCANINE_GYM, index), E.DEFAULT_EFFECTS.attack_entry(BLAINES_ARCANINE, index))
        self.assertNotIn(BLAINES_ARCANINE_GYM, E.EQUIVALENT_CARDS)  # v0.69 の写しの表（前の版の選定）には加えていない

    def test_rage_flames_check_binds_the_whole_text(self):
        """いかりのほのお: 全文と、色・枚数・カウンター 1 個あたりの数を結びつけて照らす。形だけの DamagePlusOwnCounters は通るが、トラッシュが欠けるので登録しない。"""
        attack = load_card_pool().get(ARCANINE_PROMO).attacks[1]
        self.assertEqual(E.DiscardEnergyBeforeDamagePlusOwnCounters(EnergyType.FIRE, 2, 10).check(attack), [])
        for wrong in (E.DiscardEnergyBeforeDamagePlusOwnCounters(EnergyType.FIRE, 1, 10), E.DiscardEnergyBeforeDamagePlusOwnCounters(EnergyType.FIRE, 3, 10),
                      E.DiscardEnergyBeforeDamagePlusOwnCounters(EnergyType.FIRE, 2, 20), E.DiscardEnergyBeforeDamagePlusOwnCounters(EnergyType.WATER, 2, 10)):
            self.assertNotEqual(wrong.check(attack), [], wrong)
        for text in (RAGE_TEXT + "。", RAGE_TEXT.replace("2枚", "1枚"), RAGE_TEXT.replace("×10", "×20")):
            self.assertNotEqual(E.DiscardEnergyBeforeDamagePlusOwnCounters(EnergyType.FIRE, 2, 10).check(dataclasses.replace(attack, text_ja=text)), [], text)
        self.assertEqual(E.DamagePlusOwnCounters(10).check(attack), [])  # 形の検査だけなら通る
        self.assertNotIsInstance(E.DEFAULT_EFFECTS.attack_entry(ARCANINE_PROMO, 1).effect, E.DamagePlusOwnCounters)
        self.assertIn(E.DiscardEnergyBeforeDamagePlusOwnCounters, H.ATTACK_TYPES_SINCE_V0_17)

    def test_adoption_records_and_links(self):
        cards = cs.load_sources()["cards"]
        for card in V0123:
            record = cards[card]
            self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["recorded_on"], record["kyuura_records"], record["external_checks"],
                              record["issues"], set(record["play_text"].values())),
                             ("kyuura_data", "adopted", NOW, "2026-10-31", ["CR-ARCANINE-PRINTED-NAMES"], [], [], {"kyuura_printed_text"}), card)
        self.assertEqual((cards[ARCANINE_PROMO]["name_ja"], cards[ARCANINE_INTRO]["name_ja"], cards[BLAINES_ARCANINE_GYM]["name_ja"]), ("ウィンディ", "ウィンディ", "カツラのウィンディ"))
        self.assertIn("RUL-ENERGY-DISCARD-ATTACKS の範囲の読み方", cards[BLAINES_ARCANINE_GYM]["notes"])
        links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
        printed = links["latest_descriptions"]["adopted_printed_text"]
        # v0.124 で GR団のミュウツーの 2 つ（PRN-041）をあとに加えた
        self.assertEqual(printed[-7:-2], ["GD5-007/attack/0", "GD5-007/attack/1", "IP2-032/attack/0", "PR1-016/attack/0", "PR1-016/attack/1"])

    def test_removing_the_new_registrations(self):
        """新規の登録だけを除くと 1,355 枚にもどる。名前の訂正は移行のあとのまま（2 枚は登録を除いた組でも新しい名前）。"""
        extract = read_extract()
        later = cards_after(extract, "0.123")  # v0.124 からあとの版のカード（この版の範囲の外）
        self.assertEqual(cards_after(extract, "0.122") - later, frozenset(V0123))
        self.assertTrue(set(V0123).isdisjoint(cards_before(extract, "0.123")))
        trimmed = dict(extract, cards=[c for c in extract["cards"] if c["id"] not in V0123 and c["id"] not in later], pool_v0_123=[],
                       **{key: [] for key in extract if key.startswith("pool_v0_") and set(extract[key]) & later})
        pool = pool_from_extract(trimmed, E.DEFAULT_EFFECTS)
        self.assertEqual(len(pool.playable_ids), 1355)
        self.assertEqual((pool.get(ARCANINE).name_ja, pool.get(BLAINES_ARCANINE).name_ja), ("ウィンディ", "カツラのウィンディ"))
        self.assertEqual(len(load_card_pool().playable_ids) - len(later), 1358)  # 今の総数は tests/test_catalog_contract.py


class DeckNameTest(unittest.TestCase):
    """4 章: 名前は印刷どおりの文字の比べ（CR-ARCANINE-PRINTED-NAMES）。「ウィンディ」3 枚で 4 枚まで、「カツラのウィンディ」2 枚で 4 枚まで、2 つは別の名前。"""

    @staticmethod
    def deck(*cards):
        cards = [c for c, n in cards for _ in range(n)]
        return cards + [F] * (60 - len(cards))

    def test_same_name_limits(self):
        growlithe = (GROWLITHE, 4)
        self.assertEqual(deck.deck_problems(self.deck(growlithe, (ARCANINE, 1), (ARCANINE_INTRO, 1), (ARCANINE_PROMO, 2))), [])
        self.assertEqual(deck.deck_problems(self.deck(growlithe, (ARCANINE, 2), (ARCANINE_INTRO, 2), (ARCANINE_PROMO, 1))),
                         ["TOO_MANY_COPIES: 「ウィンディ」が 5 枚（同じ名前は 4 枚まで）"])
        self.assertEqual(deck.deck_problems(self.deck(growlithe, (ARCANINE_INTRO, 4), (ARCANINE_PROMO, 1))), ["TOO_MANY_COPIES: 「ウィンディ」が 5 枚（同じ名前は 4 枚まで）"])
        self.assertEqual(deck.deck_problems(self.deck((BLAINES_GROWLITHE, 4), (BLAINES_ARCANINE_GYM, 3), (BLAINES_ARCANINE, 2))),
                         ["TOO_MANY_COPIES: 「カツラのウィンディ」が 5 枚（同じ名前は 4 枚まで）"])
        # 別の名前: 「ウィンディ」4 枚・「カツラのウィンディ」4 枚・やさしいウインディ 4 枚を同じデッキに入れられる
        self.assertEqual(deck.deck_problems(self.deck(growlithe, (BLAINES_GROWLITHE, 4), (ARCANINE, 2), (ARCANINE_PROMO, 2), (BLAINES_ARCANINE_GYM, 2),
                                                      (BLAINES_ARCANINE, 2), (KIND_ARCANINE, 4))), [])

    def test_evolves_from_printed_names(self):
        pool = load_card_pool()
        self.assertEqual({pool.get(c).evolves_from for c in (ARCANINE, ARCANINE_INTRO, ARCANINE_PROMO)}, {"ガーディ"})
        self.assertEqual({pool.get(c).evolves_from for c in (BLAINES_ARCANINE, BLAINES_ARCANINE_GYM)}, {"カツラのガーディ"})


class RageFlamesTest(unittest.TestCase):
    """5 章: いかりのほのお（炎 2 枚を捨てなければ使えない・自分のダメージカウンター × 10 を追加）。"""

    def test_discard_two_then_forty_plus_counters(self):
        for counters in (0, 3, 6):
            state = table(promo((F, F, W), damage=10 * counters), opponent=spec(H.CHANSEY))
            asked = run(state, UseAttack(0, 1))
            d = asked.decision
            pokemon = state.players[0].active
            fire = [u for u in pokemon.energy if state.cards[u].card_id == F]
            self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices, list(d.options)), ("discard_energy", 0, 2, 2, fire))
            done = answer(asked, fire)
            self.assertEqual([e["energy"] for e in new_events(state, done, "discard_energy")], fire)
            self.assertEqual([(e["amount"], e["steps"]) for e in new_events(state, done, "damage")], [(40 + 10 * counters, (("1 基本となる計算", 40 + 10 * counters),))])
            self.assertEqual([state.cards[u].card_id for u in done.players[0].active.energy], [W])
            self.assertTrue(set(fire) <= set(done.players[0].discard))
            audited(self, done)

    def test_weakness_after_the_base(self):
        state = table(promo(damage=30), opponent=spec(H.BULBASAUR))
        done = answer(run(state, UseAttack(0, 1)), state.players[0].active.energy)
        [damage] = new_events(state, done, "damage")
        self.assertEqual((dict(damage["steps"])["1 基本となる計算"], damage["weakness"], damage["amount"]), (70, True, 140))

    def test_choices_are_fire_cards_of_the_user_and_exactly_two(self):
        state = table(promo((F, F, W, F)), opponent=spec(H.CHANSEY))
        asked = run(state, UseAttack(0, 1))
        pokemon = state.players[0].active
        water = next(u for u in pokemon.energy if state.cards[u].card_id == W)
        fire = [u for u in pokemon.energy if state.cards[u].card_id == F]
        self.assertNotIn(water, asked.decision.options)
        rejected(self, asked, lambda s: answer(s, fire[:1]), "INVALID_CHOICE_COUNT")
        rejected(self, asked, lambda s: answer(s, fire), "INVALID_CHOICE_COUNT")
        before = snap(asked)
        with self.assertRaises(IllegalActionError):
            answer(asked, (fire[0], water))
        self.assertEqual(snap(asked), before)

    def test_rainbow_energy_question_is_not_bypassed(self):
        """レインボーエネルギーで「炎」2 個を払っても、炎エネルギーカードとして選ぶかは既存の RB1 で止める（カード名だけで決めない）。"""
        state = table(promo((F, H.RAINBOW_ENERGY)), opponent=spec(H.CHANSEY))
        rejected(self, state, lambda s: run(s, UseAttack(0, 1)), "UNRESOLVED_RAINBOW_ENERGY_TYPE")

    def test_confusion_tails_discards_nothing(self):
        state = table(promo(damage=20, confusion=True), opponent=spec(H.CHANSEY))
        done = run(state, UseAttack(0, 1), TL)
        self.assertEqual((done.decision, new_events(state, done, "discard_energy"), [e["amount"] for e in new_events(state, done, "damage")]), (None, [], []))
        self.assertEqual(len(new_events(state, done, "confusion_damage")), 1)

    def test_copied_by_clefable_uses_the_copier(self):
        """ゆびをふる（ピクシー）で写すときは、写したポケモン（使い手）の炎エネルギーカードとダメージカウンターで数える。炎エネルギーカードが 2 枚ない使い手は選べない（既存の判定）。"""
        opponent = promo(damage=0)
        without = run(table(spec(CLEFABLE, (P_, P_, P_), below=(CLEFAIRY,), damage=20), opponent=opponent), UseAttack(0, 0))
        self.assertEqual((without.decision.kind, list(without.decision.options)), ("select_attack", [0]))
        state = table(spec(CLEFABLE, (F, F, P_), below=(CLEFAIRY,), damage=20), opponent=opponent)
        chosen = answer(run(state, UseAttack(0, 0)), (1,))
        copier = state.players[0].active
        fire = [u for u in copier.energy if state.cards[u].card_id == F]
        self.assertEqual((chosen.decision.kind, list(chosen.decision.options)), ("discard_energy", fire))
        done = answer(chosen, fire)
        self.assertEqual([(e["pokemon_id"], e["effect"]) for e in new_events(state, done, "discard_energy")], [(copier.pokemon_id, "PR1-016#1")] * 2)
        self.assertEqual([e["amount"] for e in new_events(state, done, "damage")], [60])  # 40 + ピクシーのカウンター 2 個 × 10（ウィンディの 0 個ではない）
        self.assertEqual(len(done.players[1].active.energy), 2)  # 写されたウィンディのエネルギーは減らない
        audited(self, done)

    def test_ecogym_does_not_return_own_discards(self):
        """自分のワザでトラッシュした炎エネルギーカードは、エコロジム（相手の「ワザ・特殊能力」や「トレーナー」によるトラッシュだけをもどす）があっても手札にもどらない（v0.82 の共通の処理）。"""
        state = table(promo(damage=10), opponent=spec(H.CHANSEY), hand=(ECOGYM,))
        placed = trainer(state, ECOGYM)
        fire = list(placed.players[0].active.energy)
        done = answer(run(placed, UseAttack(0, 1)), fire)
        self.assertTrue(set(fire) <= set(done.players[0].discard))
        self.assertFalse(set(fire) & set(done.players[0].hand))
        self.assertEqual([e["amount"] for e in new_events(placed, done, "damage")], [50])

    def test_saved_and_resumed_across_the_discard(self):
        """形式 28 のまま（決定の途中の状態を形式 28 で書き出せる。新しい状態の欄はない）。トラッシュを選ぶ決定の途中の状態を、複製・deepcopy・pickle から続けても、トラッシュ・ダメージは
        1 回だけで、結果は同じ。"""
        self.assertIn(28, FORMAT_VERSIONS)  # v0.124 で形式 29 を加えた（この状態は形式 28 で表せる）
        state = table(promo((F, F, F), damage=40), opponent=spec(H.CHANSEY))
        asked = run(state, UseAttack(0, 1))
        data = state_to_dict(asked, format_version=28)
        self.assertEqual((data["decision"]["kind"], data["decision"]["min_choices"], data["decision"]["max_choices"]), ("discard_energy", 2, 2))
        choice = tuple(asked.decision.options[1:])
        done = answer(asked, choice)
        for other in (asked.clone(), copy.deepcopy(asked), pickle.loads(pickle.dumps(asked))):
            again = answer(other, choice)
            self.assertEqual(state_to_dict(again, format_version=28), state_to_dict(done, format_version=28))
            self.assertEqual(len(new_events(state, again, "discard_energy")), 2)
            self.assertEqual([e["amount"] for e in new_events(state, again, "damage")], [80])


class ReusedAttacksTest(unittest.TestCase):
    """3 章: 既存の型の 4 つのワザ（代表の場面だけ。型ごとの全組み合わせは既存のテスト）。"""

    def test_take_down_and_heat_tackle(self):
        state = table(spec(ARCANINE_INTRO, (F, F, W), below=(GROWLITHE,)), opponent=spec(H.CHANSEY))
        done = run(state, UseAttack(0, 0))
        self.assertEqual([(e["player"], e["amount"]) for e in new_events(state, done, "damage")], [(1, 50), (0, 20)])
        state = table(spec(BLAINES_ARCANINE_GYM, (F, W, W), below=(BLAINES_GROWLITHE,)), opponent=spec(H.CHANSEY))
        done = run(state, UseAttack(0, 0))
        self.assertEqual([(e["player"], e["amount"]) for e in new_events(state, done, "damage")], [(1, 40), (0, 10)])

    def test_quick_attack_and_firestorm(self):
        for side, amount in ((HD, 30), (TL, 10)):
            state = table(promo(), opponent=spec(H.CHANSEY))
            self.assertEqual([e["amount"] for e in new_events(state, run(state, UseAttack(0, 0), side), "damage")], [amount])
        state = table(spec(BLAINES_ARCANINE_GYM, (F, F, F, F), below=(BLAINES_GROWLITHE,)), opponent=spec(H.CHANSEY))
        asked = run(state, UseAttack(0, 1))
        self.assertEqual((asked.decision.min_choices, asked.decision.max_choices), (3, 3))
        done = answer(asked, asked.decision.options[:3])
        self.assertEqual((len(new_events(state, done, "discard_energy")), [e["amount"] for e in new_events(state, done, "damage")]), (3, [120]))


class CatalogTest(unittest.TestCase):
    """7 章: マチスの秘策の試すカードで、GD5-007 は PMCG6-034 と処理の同じカードとしてまとまる（v0.123 で 2 枚ぶん増える。総数の固定値は tests/test_catalog_contract.py）。"""

    def test_secret_plan_candidates_and_limits(self):
        from kyuura_engine import engine
        from kyuura_engine.resolution import preflight

        candidates = engine._identity_candidates(load_card_pool())
        self.assertEqual(len([c for c in (BLAINES_ARCANINE, BLAINES_ARCANINE_GYM) if c in candidates]), 1)
        self.assertTrue({ARCANINE_INTRO, ARCANINE_PROMO} <= set(candidates))
        self.assertEqual((engine._IDENTITY_TRIAL_LIMIT, preflight.MAX_BRANCHES), (512, 4096))


class PreflightTest(unittest.TestCase):
    """8 章: 宣言の前の先読みで試す結果の数は、トラッシュするカードの組み合わせの数（上限 4,096 は増やさない）。"""

    def test_measured_branches(self):
        from unittest import mock

        from kyuura_engine.resolution import preflight

        branches = []
        original = preflight.explore

        def counting(*args, **kwargs):
            found, tried = original(*args, **kwargs)
            branches.append(tried)
            return found, tried

        def measured(state, command):
            branches.clear()
            with mock.patch.object(preflight, "explore", counting):
                run(state, command)
            return list(branches)

        for fire, combinations in ((2, 1), (3, 3), (4, 6)):  # いかりのほのお: n 枚から 2 枚
            self.assertEqual(measured(table(promo((F,) * fire, damage=20), opponent=spec(H.CHANSEY)), UseAttack(0, 1)), [combinations])
        gym = table(spec(BLAINES_ARCANINE_GYM, (F, F, F, F), below=(BLAINES_GROWLITHE,)), opponent=spec(H.CHANSEY))
        self.assertEqual(measured(gym, UseAttack(0, 1)), [4])  # ほのおのあらし: 4 枚から 3 枚
        self.assertEqual(preflight.MAX_BRANCHES, 4096)


# ---------------------------------------------------------------- 11 章: ログの監査

class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v123_problems``・``v123_close``）は、エンジンの登録・計算を読まずに、印刷の文面とログから組み立てた場で確かめる。正式な開始からの対戦
    （tools/existing_effect_games.py の局。開発用の seed 90〜93。正式な対戦の seed 0〜3 とは別）のログを 1 か所書き換える・エンジンに一時的に不具合を入れると、監査が見つける。"""

    GAMES = ((("K123", "W123"), 90), (("W123", "K123"), 93), (("W123", "P31"), 90), (("W123", "E82"), 90))
    _played: ClassVar[dict] = {}

    @classmethod
    def game(cls, labels, seed):
        from tools import existing_effect_games as games

        if (labels, seed) not in cls._played:
            cls._played[(labels, seed)] = games.play(labels, seed, keep_state=True)
        return cls._played[(labels, seed)]

    def test_the_games_pass_the_audit(self):
        from tests.log_audit import log_problems

        used = set()
        for labels, seed in self.GAMES:
            result = self.game(labels, seed)
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual((result["outcome"], result["audit"], log_problems(result["state"])), ("game_over", {}, []))
            used |= {k for k, v in result["v123"].items() if v}
        self.assertTrue({"attack_PR1-016#1", "rage_discard_2", "rage_counters_0", "rage_counters_3", "copied_PR1-016#0", "attack_GD5-007#1", "attack_IP2-032#0",
                         "self_damage_IP2-032#0_20", "firestorm_discard_3", "quick_heads", "quick_tails"} <= used, used)

    def test_audit_finds_a_wrong_base_or_discard(self):
        from tests.log_audit import log_problems

        state = self.game(("K123", "W123"), 90)["state"].clone()
        log = [dict(e) for e in state.log]
        rage = next(i for i, e in enumerate(log) if e["kind"] == "attack" and state.cards[e["pokemon"]].card_id == ARCANINE_PROMO and e["attack_index"] == 1)
        damage = next(i for i in range(rage, len(log)) if log[i]["kind"] == "damage")
        steps = tuple(log[damage]["steps"])
        changed = list(log)
        changed[damage] = dict(log[damage], steps=((steps[0][0], steps[0][1] + 10), *steps[1:]))
        state.log = tuple(changed)
        self.assertTrue([p for p in log_problems(state) if "PR1-016#1 の基本となるダメージ" in p])
        discard = next(i for i in range(rage, len(log)) if log[i]["kind"] == "discard_energy")
        state.log = tuple(log[:discard] + log[discard + 1:])
        self.assertTrue([p for p in log_problems(state) if "PR1-016#1 でトラッシュしたカード" in p])

    def test_audit_finds_a_temporary_engine_fault(self):
        """エンジンにいかりのほのおのカウンターの数え方の不具合（1 個多く数える）を一時的に入れて同じ局を進めると、監査が基本となるダメージの違いを見つける（エンジンは戻す）。"""
        from unittest import mock

        from kyuura_engine.resolution import programs
        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        original = programs.PlusOwnCounters.value

        def wrong(self, run, flips):
            return original(self, run, flips) + (self.per if run.key.card_id == ARCANINE_PROMO else 0)

        with mock.patch.object(programs.PlusOwnCounters, "value", wrong):
            result = games.play(("K123", "W123"), 90, keep_state=True)
        self.assertTrue([p for p in log_problems(result["state"]) if "PR1-016#1 の基本となるダメージ" in p])


class DocumentTest(unittest.TestCase):
    def test_document_records_the_version(self):
        text = (ROOT / "docs" / "arcanine-name-migration-v0.123.md").read_text(encoding="utf-8")
        for needle in ("## 1. 開始点と範囲", "## 2. 写しの元・研究の基準の移行（2fe0bc0 → 74b3ceb）", "generated_value_error", "requires_unregistered", "CR-ARCANINE-PRINTED-NAMES",
                       "## 4. 名前と、同じ名前の数え方", "## 5. いかりのほのお", "DiscardEnergyBeforeDamagePlusOwnCounters", "RUL-ENERGY-DISCARD-ATTACKS", "## 6. 今回登録しないもの",
                       "UQ-BILINGUAL-NAME-GLOSS", "held_illegible_print", "0.123.0", "## 13. 検証", "lockstep", "--card-data-commit",
                       "単体のテストだけ", "4,096", "## 14. 残る制限", "外部照合・カードの画像・ガイドブックの読み直しをしていません", NOW, V0121):
            self.assertIn(needle, text)
        self.assertRegex((ROOT / "README.md").read_text(encoding="utf-8"),
                         r"\n- v0\.123（(今のエンジンの版。)?`kyuura_engine` の版は 0\.123\.0）: 名前の訂正の移行とウィンディ 3 枚")
        self.assertIn("## v0.123: 名前の訂正の移行とウィンディ 3 枚\n", (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8"))
        self.assertIn("### v0.123: 名前の訂正の移行とウィンディ 3 枚", (ROOT / "docs" / "rules-2000-02-14.md").read_text(encoding="utf-8"))
        provenance = (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8")
        for needle in ("## v0.123: ウィンディ系の 3 枚", "## v0.123: 写しの元・研究の基準を kyuura 74b3ceb に上げる移行", "2026-10-31（v0.123）の追記"):
            self.assertIn(needle, provenance)
        self.assertLess(len((ROOT / "CLAUDE.md").read_text(encoding="utf-8").splitlines()), 200)


if __name__ == "__main__":
    unittest.main()

