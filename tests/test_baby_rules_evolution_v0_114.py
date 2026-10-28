"""v0.114（docs/baby-rules-evolution-v0.114.md）: 写しの元・研究の基準の移行（73a1690 → e519b99）と、ナツメのESPのやり直しのあとの入れ替えの結果。

2 章: 移行は連鎖（ecb2d69 → 7d3f4ca → 73a1690 → e519b99）で、v0.69・v0.97 の段の記録は書き換えない（v0.97 の段のあとは 73a1690 に固定した）。73a1690 → e519b99 の data/cards.json で
値が変わったのはベイビィ 13 枚だけで、写しの 1,250 枚の値は v0.113 と同じ。研究の基準の新しい条項・裁定・論点（UQ-NEO-TEXT-BABY-CATEGORIES）・事例を研究の対応表に結ぶ。
"""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import pickle
import subprocess
import unittest
from collections import Counter
from unittest import mock

from kyuura_engine import PlayTrainer, ResolveDecision
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.conditions import PARALYSIS, POISON
from kyuura_engine.decisions import ESP_REDO, FORCED_SWITCH
from kyuura_engine.engine import check_invariants
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.resolution import programs as P
from kyuura_engine.state import MARKER_COLOR
from scripts import check_card_sources as cs
from tests import helpers as H
from tests import test_variable_coins_search_attachments_v0_113 as V113
from tests.helpers import apply_kernel
from tests.test_neo_trainer_components_v0_80 import audited, new_events
from tests.test_unown_family_powers_v0_96 import snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
DOC = ROOT / "docs" / "baby-rules-evolution-v0.114.md"
ECB, V069, V097, V0114 = ("ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3", "73a169063463bbf7bcaa3137d70cbf9721d11534",
                          "e519b99e2adcc6c2cd0998569ae5ee1101de6e89")
V0113 = "2d113b5eeea0dbd4f7466e144f7a1345494405c0"  # 確認済みの完成版（固定した v0.113）
BABIES = ("neo1-022", "neo1-042", "neo1-044", "neo1-070", "neo2-033", "neo2-050", "neo3-031", "PF2-007", "NIP1X-002", "NIP2X-002", "PRN-012", "PRN-031", "PRN-037")
RULE_FILLED = BABIES[:6]  # ルール文を kyuura が画像で埋めた neo 第1〜2弾の 6 枚
HD, TL = CoinSide.HEADS, CoinSide.TAILS
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


class EspSwitchContinuationTest(unittest.TestCase):
    """3 章: ナツメのESPのやり直しのあとに、前の要素の入れ替えの結果（``ForceSwitch`` の、入れ替えて出た控えの番号）を続きの情報 ``switched_results`` で運ぶ（エンジンの不具合の限定した
    修正。公式の裁定・kyuura の論点の解決ではない）。通常の登録・操作（手札のナツメのESPを ``PlayTrainer`` でナツメのフーディンにつけ、超の色マーカーをのせたわるいアリアドス（neo4-011）の
    「からめとる」を［サイコリンク］で使う。ESPの関数・解決の部品を差しかえない）。"""

    ARIADOS = "neo4-011"

    def board(self):
        provider = {"card": self.ARIADOS, "energy": [], "markers": [(MARKER_COLOR, EnergyType.PSYCHIC)], "evolved_from": ["neo1-004"]}
        state = V113.board(V113.mon(V113.ALAKAZAM, (H.GRASS, H.WATER)), bench=(provider,), opponent=V113.mon(H.HITMONCHAN), opponent_bench=(H.RATTATA, H.MACHOP),
                           hand=(V113.ESP_CARD,))
        played = apply_kernel(state, PlayTrainer(0, V113.uid(state, V113.ESP_CARD)))
        return V113.answer(played, (played.players[0].active.pokemon_id,))

    def switched(self):
        """「からめとる」を宣言した、入れ替える控えの決定の状態と、入れ替える控え（1 匹目）の番号。"""
        state = self.board()
        switch = V113.attack(state, 0, card=V113.provider_card(state, self.ARIADOS))
        self.assertEqual(switch.decision.kind, FORCED_SWITCH)
        return switch, switch.decision.options[0]

    def test_redo_and_keep_with_both_faces(self):
        """やり直さない「おもて」・「うら」、やり直して「うら」→「おもて」・「おもて」→「うら」。採った最後の面が「おもて」のときだけ、新しく出てきたポケモン（入れ替えた控え）がマヒ。
        入れ替え・マヒは 1 回だけ（入れ替え・コインを処理し直さない）。コインは最初の 1 枚と、やり直したときの 1 枚。"""
        switch, bench = self.switched()
        for redo, first, again, paralyzed in (((), HD, None, True), ((), TL, None, False), ((1,), TL, HD, True), ((1,), HD, TL, False)):
            with self.subTest(redo=redo, first=first, again=again):
                esp = V113.answer(switch, (bench,), first)
                self.assertEqual(esp.decision.kind, ESP_REDO)
                self.assertEqual(dict(esp.decision.context)["switched_results"], (("switch", bench),))
                audited(self, esp)
                done = V113.same_answers(self, esp, redo, *(() if again is None else (again,)))
                self.assertEqual((done.players[1].active.pokemon_id, done.players[1].active.conditions.paralyzed), (bench, paralyzed))
                events = new_events(switch, done)
                self.assertEqual([e["kind"] for e in events].count("forced_switch"), 1)
                self.assertEqual(len([e for e in events if e["kind"] == "special_condition" and e.get("condition") == PARALYSIS]), int(paralyzed))
                self.assertEqual(len([e for e in events if e["kind"] == "coin_flip" and e.get("source") == "attack"]), 1 + len(redo))

    def test_saved_across_the_switch_decision_and_invalid_answers(self):
        """入れ替え先の決定・ESPの決定をまたいで clone・deepcopy・pickle しても同じ続きになる。ESPの決定への不正な答え（決めるプレイヤーの違い・選べない値・重複）は、状態・乱数・ログ・
        決定を変えない。運んだ値を除いた v0.113 までの続きの形では、マヒを黙って省く（この修正が直したもの）。"""
        switch, bench = self.switched()
        expected = V113.answer(switch, (bench,), HD)
        for other in (switch.clone(), copy.deepcopy(switch), pickle.loads(pickle.dumps(switch))):
            self.assertEqual(snap(V113.answer(other, (bench,), HD)), snap(expected))
        before = snap(expected)
        for player, choices in ((1, ()), (0, (2,)), (0, (1, 1))):
            with self.assertRaises(IllegalActionError):
                apply_kernel(expected, ResolveDecision(player, expected.decision.id, choices))
        self.assertEqual(snap(expected), before)
        self.assertTrue(V113.answer(expected, ()).players[1].active.conditions.paralyzed)
        old_form = copy.deepcopy(expected)  # 決定は複製のあいだで共有されることがあるので、deepcopy した状態の決定だけを書きかえる
        object.__setattr__(old_form.decision, "context", tuple(item for item in old_form.decision.context if item[0] != "switched_results"))
        self.assertFalse(V113.answer(old_form, ()).players[1].active.conditions.paralyzed)

    def test_invariant_and_uncarried_results(self):
        """不変条件: 運んだ入れ替えの結果が、この番に入れ替えて出た相手の場のポケモンでなければ違反。続きの情報で運べない種類の結果を、ESPのやり直しのあとの要素が読む並び（今の写しには
        ない。登録の型の並びを一時的に置きかえて作る）は、黙って省かずに宣言の前に ``UNSUPPORTED_ESP_CONTINUATION`` で拒否する（状態を変えない）。"""
        switch, bench = self.switched()
        esp = V113.answer(switch, (bench,), HD)
        broken = copy.deepcopy(esp)
        other = esp.players[1].bench[0].pokemon_id
        object.__setattr__(broken.decision, "context", tuple(("switched_results", (("switch", other),)) if key == "switched_results" else (key, value)
                                                             for key, value in broken.decision.context))
        self.assertTrue(any("入れ替えの結果" in p for p in check_invariants(broken)))
        state = self.board()
        before = snap(state)
        # 前の要素の結果（真偽の値。続きの情報で運ばない種類）を、コインを投げる要素が名前で読む並び
        uncarried = {E.SwitchOpponentThenParalyzeNewOnHeads: lambda e: (P.OpponentStatusCheck("checked", (POISON,)),
                                                                         P.Status(PARALYSIS, local_coin=HD, after_switch="checked"))}
        with mock.patch.dict(P.BUILDERS, uncarried), self.assertRaises(UnsupportedError) as caught:
            V113.attack(state, 0, card=V113.provider_card(state, self.ARIADOS))
        self.assertEqual(caught.exception.code, "UNSUPPORTED_ESP_CONTINUATION")
        self.assertEqual(snap(state), before)


class DocumentTest(unittest.TestCase):
    def test_migration_chapter(self):
        text = DOC.read_text(encoding="utf-8")
        for word in (V0114, V097, "KYUURA_MIGRATIONS", "V0_97_KYUURA_COMMIT", "TARGET_SELECTION_COMMIT", "current_target_status_problems", "field_added_from_print",
                     "card_image_checks.json", "existing_transcription", "UQ-NEO-TEXT-BABY-CATEGORIES", "NB0", "ENGINE-46A3E2E", "with_card_data_commit_at"):
            self.assertIn(word, text)
        provenance = (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8")
        self.assertIn("## v0.114: 写しの元・研究の基準を kyuura e519b99 に上げる移行", provenance)

    def test_esp_chapter(self):
        text = DOC.read_text(encoding="utf-8")
        for word in ("ENG-V0113-ESP-REDO-SWITCH-RESULT", "switched_results", "UNSUPPORTED_ESP_CONTINUATION", "_esp_carry_check", "EspSwitchContinuationTest", "からめとる",
                     "サカキのニャース（PMCG6-063）"):
            self.assertIn(word, text)
        v0113 = (ROOT / "docs" / "variable-coins-search-attachments-v0.113.md").read_text(encoding="utf-8")
        self.assertNotIn("カスミのニャース（PMCG6-063）", v0113)
        self.assertIn("6,315 件のうち失敗 2", v0113)  # v0.113 の全体のテストの記録はそのまま


if __name__ == "__main__":
    unittest.main()
