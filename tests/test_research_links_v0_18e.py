"""v0.18e: 研究の対応表（kyuura_engine/data/research_links.json）と、エンジンの停止コード・問い・登録・照合の記録が合うこと。
docs/research-alignment-v0.18a.md・docs/verification-reproducibility-v0.18e.md。

kyuura（研究の正本）の記録そのものは写さず、id の対応だけを持つ。ここでは kyuura がなくても確かめられること（エンジンの側の集合と対応表が
同じ）を確かめ、../kyuura があれば ``scripts/check_research_links.py`` で kyuura の研究の基準のコミットの記録とも照らす。

停止コード・登録を加えたのに対応表に書かないと失敗する（エンジンから研究の id を引けなくなるのを防ぐ）。kyuura の記録 id: engine_unresolved_index・
UQ-…・CR-…・LD-…・CC-…（v0.18 は kyuura adf9710。2026-10-15 の照合の記録の取り込みのあとは kyuura 3f34908。docs/verified-record-reuse.md）。
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import unittest

from kyuura_engine import effects as E
from kyuura_engine.cards import read_extract, read_verification
from kyuura_engine.resolution import questions

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINKS = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
KYUURA = ROOT.parent / "kyuura"


def engine_stop_codes() -> set[str]:
    """エンジンの中の ``UNRESOLVED_…``（既定の UNRESOLVED_RULING を除く。tests/test_unresolved_boundaries_v0_4e.py の数え方と同じ）。"""
    codes = set()
    for path in (ROOT / "kyuura_engine").rglob("*.py"):
        codes |= set(re.findall(r"\bUNRESOLVED_[A-Z_]+[A-Z]\b", path.read_text(encoding="utf-8")))
    return codes - {"UNRESOLVED_RULING"}


def registered_targets() -> set[str]:
    registry = E.DEFAULT_EFFECTS
    found = {f"{k.card_id}/attack/{k.attack_index}" for k in registry.attack_keys()
             if registry.attack_entry(k.card_id, k.attack_index).play_text_ja is not None}
    found |= {f"{k.card_id}/power/{k.power_index}" for k in registry.power_keys()
              if getattr(registry.power_entry(k.card_id, k.power_index), "play_text_ja", None) is not None}
    return found


def all_engine_rulings():
    for entry in LINKS["stop_codes"].values():
        yield from entry["engine_rulings"]
    for entry in LINKS["codeless_questions"].values():
        yield from entry["engine_rulings"]
    for section in ("unresolved_without_code", "deferred_card_questions", "implementation_assumptions_with_issue"):
        for entry in LINKS[section]:
            yield from entry["engine_rulings"]


class ResearchLinksTest(unittest.TestCase):
    def test_commits(self):
        """研究の基準（kyuura 3f34908。2026-10-15 に adf9710 から上げた。docs/verified-record-reuse.md）とカードの写しの元（ecb2d69）を
        分けて持つ。写しの元は同梱の写しのコミットと同じ。"""
        self.assertRegex(LINKS["research_commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(LINKS["research_commit"], "3f349085645f47d0649a6cacece3680caeae50bf")
        self.assertEqual(LINKS["engine_import_id"], "ENGINE-46A3E2E")
        self.assertEqual(LINKS["card_data_commit"], read_extract()["source"]["commit"])
        self.assertNotEqual(LINKS["research_commit"], LINKS["card_data_commit"])

    def test_every_stop_code_is_linked(self):
        """エンジンの停止コードの集合と、対応表の停止コードの集合が同じ（v0.30 までの 22 件 + v0.31 の 15 件 + v0.32 の 1 件 + v0.34 の 2 件 + v0.36 の 2 件 + v0.37 の 1 件 + v0.38 の 1 件 + v0.39 の 1 件 + v0.40 の 1 件 + v0.41 の 1 件 + v0.42 の 2 件 + v0.43 の 2 件 = 51 件）。論点のないものは kyuura の
        処理が out_of_scope。kyuura にまだ記録がない停止コードは not_in_kyuura（v0.21 の突風の UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH・v0.22 の
        パソコン通信の UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK・v0.23 のエネルギー回収の 2 件・v0.31 の HC1〜HC10 の 10 件・v0.32 の CD4・v0.34 の TP3・NK5・v0.36 の AC6・RD9・v0.37 の JS1・v0.38 の GK1・v0.39 の GS1・v0.40 の SG1・v0.41 の CX1・v0.42 の PW1・PW2・v0.43 の PW3・PW4。kyuura への報告事項）。
        v0.31 で、v0.30 まで起こらなかった（コードのない）5 件（T27・C34/C35・G40・P19・P32）が複数のポケモンにダメージを与えるワザで起こるように
        なったので停止コードにした。kyuura の論点（UQ-）はそのまま（kyuura の未解決の一覧ではコードのない行なので、``kyuura_index_engine_key`` で
        行を指す。scripts/check_research_links.py）。"""
        self.assertEqual(set(LINKS["stop_codes"]), engine_stop_codes())
        self.assertEqual(len(LINKS["stop_codes"]), LINKS["counts"]["engine_stop_codes"])
        not_in_kyuura = set()
        for code, entry in LINKS["stop_codes"].items():
            with self.subTest(code=code):
                if entry["kyuura_disposition"] == "not_in_kyuura":
                    self.assertIsNone(entry["kyuura_issue"])
                    not_in_kyuura.add(code)
                else:
                    self.assertEqual(entry["kyuura_disposition"], "issue" if entry["kyuura_issue"] else "out_of_scope")
        self.assertEqual(not_in_kyuura, {"UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH", "UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK",
                                         "UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET", "UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE",
                                         # v0.31（docs/held-cards-v0.31.md の HC1〜HC10）
                                         "UNRESOLVED_DISCARD_ENERGY_TIMING", "UNRESOLVED_DESTINY_BOND_KNOCKOUT", "UNRESOLVED_PREVENTED_EFFECT_COIN",
                                         "UNRESOLVED_EXTRA_ENERGY_COLORLESS", "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO", "UNRESOLVED_DISCARD_DECK_SHORT",
                                         "UNRESOLVED_ATTACH_FROM_DISCARD_ZERO", "UNRESOLVED_POWER_HEAL_WITHOUT_DAMAGE", "UNRESOLVED_COPIED_ATTACK",
                                         "UNRESOLVED_ENERGY_BURN_TRANSFER",
                                         # v0.32（docs/bench-search-counter-drain-v0.32.md の CD4）
                                         "UNRESOLVED_OPPONENT_POKEMON_COUNTERS",
                                         # v0.34（docs/barrier-resume-coin-bonus-v0.34.md の TP3（v0.3a の 15）・NK5）
                                         "UNRESOLVED_SPECIAL_POISON_OVERWRITE", "UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET",
                                         # v0.36（docs/sand-attack-retreat-lock-v0.36.md の AC6・RD9）
                                         "UNRESOLVED_ATTACK_CHECK_CONFUSION", "UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT",
                                         # v0.37（docs/fifteen-reused-effects-v0.37.md の JS1）
                                         "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE",
                                         # v0.38（docs/bench-switch-combined-v0.38.md の GK1）
                                         "UNRESOLVED_DAMAGE_TRIGGER_TIMING",
                                         # v0.39（docs/selfdestruct-spread-count-v0.39.md の GS1）
                                         "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE",
                                         # v0.40（docs/count-condition-switch-return-v0.40.md の SG1）
                                         "UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED",
                                         # v0.41（docs/heal-counter-status-v0.41.md の CX1）
                                         "UNRESOLVED_COUNTER_TRANSFER_PROTECTED",
                                         # v0.42（docs/power-decisions-v0.42.md の PW1・PW2）
                                         "UNRESOLVED_POWER_SWITCH_WITHOUT_OPPONENT_BENCH", "UNRESOLVED_POWER_DISCARD_WITHOUT_HAND",
                                         # v0.43（docs/declared-entry-powers-v0.43.md の PW3・PW4）
                                         "UNRESOLVED_POWER_ZERO_CARDS", "UNRESOLVED_ENTRY_POWER_DURING_ATTACK"})
        moved = {code: entry["kyuura_index_engine_key"] for code, entry in LINKS["stop_codes"].items() if "kyuura_index_engine_key" in entry}
        self.assertEqual(moved, {"UNRESOLVED_TRANSPARENCY_COIN_ORDER": "T27", "UNRESOLVED_MULTIPLE_DAMAGE_TRIGGERS": "C34/C35",
                                 "UNRESOLVED_KO_PREVENTION_ORDER": "G40", "UNRESOLVED_PHOENIX_GAS_SOURCE_KNOCKOUT": "P19",
                                 "UNRESOLVED_POST_KNOCKOUT_POWERS_ORDER": "P32"})
        self.assertEqual(LINKS["unresolved_without_code"], [])

    def test_codeless_questions_exist(self):
        """コードのない問い（Z9・Z22）は、問いの表（questions.QUESTIONS）にコードなしである。"""
        for name in LINKS["codeless_questions"]:
            with self.subTest(name=name):
                self.assertIn(name, questions.QUESTIONS)
                self.assertIsNone(questions.QUESTIONS[name].code)

    def test_every_question_is_linked_to_its_rulings(self):
        """問いの表のどの問いも、対応表に裁定 id（か版）ごと載っている。コードのある問いは停止コードの行、コードのない問いはコードのない問いか
        起こらない未解決の行。問いを加えたら対応表も直す。

        v0.31 の ``UNSUPPORTED_…`` のコードの問い（``copied_attack_unsupported``。エンジンが表せないワザをまねるとき）は裁定の未解決ではなく
        エンジンの対応の範囲なので、停止コードの行には載せない（docs/held-cards-v0.31.md）。"""
        def ids(rulings):
            return {r["ruling_id"] or r["version"] for r in rulings} | {r["version"] for r in rulings}

        codeless_rows = [ids(e["engine_rulings"]) for e in LINKS["unresolved_without_code"]]
        for key, question in questions.QUESTIONS.items():
            with self.subTest(question=key):
                if question.code is not None and question.code.startswith("UNSUPPORTED_"):
                    self.assertNotIn(question.code, LINKS["stop_codes"])
                elif question.code is not None:
                    self.assertTrue(set(question.rulings) <= ids(LINKS["stop_codes"][question.code]["engine_rulings"]))
                elif key in LINKS["codeless_questions"]:
                    self.assertTrue(set(question.rulings) <= ids(LINKS["codeless_questions"][key]["engine_rulings"]))
                else:
                    self.assertTrue(any(set(question.rulings) <= row for row in codeless_rows), question.rulings)

    def test_counts(self):
        """未解決の裁定 43 件 = 停止コード 42 + コードのない未解決（Z9）。v0.32 で CD4 の 1 件、v0.34 で TP3・NK5 の 2 件、v0.36 で AC6・RD9 の 2 件を加えた。v0.30 までは 28 件 = 停止コード 22 + コードのない未解決（起こらない 5・Z9）
        で、v0.31 で起こらない 5 件を停止コードにし（数は同じ）、HC1〜HC10 の 10 件を加えた。kyuura の論点は 19 件で、別の数え方（v0.21 の
        GW5・v0.22 の CS6・v0.23 の ER9・ER10・v0.31 の HC1〜HC10・v0.32 の CD4・v0.34 の TP3・NK5・v0.36 の AC6・RD9 は kyuura に論点がない）。"""
        counted = len(LINKS["stop_codes"]) + len(LINKS["unresolved_without_code"]) + sum(
            v["counted_as_engine_unresolved"] for v in LINKS["codeless_questions"].values())
        self.assertEqual(counted, LINKS["counts"]["engine_unresolved_rulings"])
        issues = {v["kyuura_issue"] for v in LINKS["stop_codes"].values() if v["kyuura_issue"]}
        issues |= {v["kyuura_issue"] for v in LINKS["codeless_questions"].values() if v["kyuura_issue"]}
        for section in ("unresolved_without_code", "deferred_card_questions", "implementation_assumptions_with_issue"):
            issues |= {v["kyuura_issue"] for v in LINKS[section]}
        self.assertEqual(len(issues), LINKS["counts"]["kyuura_issues"])
        self.assertTrue(all(i.startswith("UQ-") for i in issues))

    def test_engine_ruling_ids_appear_in_their_documents(self):
        """対応表に書いたエンジンの裁定 id は、書いた文書にある（文書の表の行か本文）。"""
        for ruling in all_engine_rulings():
            with self.subTest(ruling=ruling):
                text = (ROOT / ruling["document"]).read_text(encoding="utf-8")
                if ruling["ruling_id"] is not None:
                    self.assertRegex(text, rf"(?<![A-Za-z0-9]){re.escape(ruling['ruling_id'])}(?![0-9])")

    def test_latest_descriptions_cover_every_registration(self):
        """最新の説明を登録したワザ・特殊能力は、どれも 6 つの区分（kyuura の LD-、文面が印刷と同じで kyuura の CC- に書かれたもの、CC- はあるが
        ワザの文面を照合していないもの、kyuura に記録なし、kyuura データの採用で処理に使う文面を kyuura の印刷の文面にしたもの（2026-10-15
        からの方針。docs/card-data-policy.md。採用の記録 card_sources.json との対応は scripts/check_card_sources.py が確かめる）、処理に使う
        文面を kyuura のエラッタ（RUL- など）にしたもの（v0.30 の errata_text）、処理に使う文面を kyuura の card_differences の最新の説明に
        したもの（v0.31 の difference_text。ピッピの「ゆびをふる」））のちょうど 1 つに挙げる（登録を加えたら対応表も直す）。
        文面の一致は scripts/check_research_links.py が kyuura で確かめる。"""
        section = LINKS["latest_descriptions"]
        groups = {name: set(section[name]) for name in
                  ("registered", "recorded_in_card_checks", "card_checks_without_text", "registered_without_kyuura_record",
                   "adopted_printed_text", "errata_text", "difference_text")}
        names = list(groups)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                with self.subTest(a=a, b=b):
                    self.assertFalse(groups[a] & groups[b])
        self.assertEqual(set().union(*groups.values()), registered_targets())
        # v0.18c のナツメのヤドンは、2026-10-15 にエンジンの照合の記録を kyuura に取り込んだ（CC-PMCG6-044-P155。kyuura は画像を読み直していない）。
        self.assertEqual(section["recorded_in_card_checks"]["PMCG6-044/attack/0"], "CC-PMCG6-044-P155")
        # ドードーのみだれづきは、図版の版が決まらないので kyuura の照合の記録で文面を照合していない（docs/verified-record-reuse.md 4 章）。
        self.assertEqual(set(section["card_checks_without_text"]), {"PMCG1-061/attack/0"})
        for target, ld_id in section["registered"].items():
            card, kind, index = target.split("/")
            self.assertEqual(ld_id, f"LD-{card}-{'ATK' if kind == 'attack' else 'PWR'}{index}")
        for target, cc_id in {**section["recorded_in_card_checks"], **section["card_checks_without_text"]}.items():
            card = target.split("/")[0]
            self.assertTrue(cc_id.startswith(f"CC-{card}-P"), cc_id)
            self.assertIn(cc_id, LINKS["card_checks"]["engine_verified"][card])
        # v0.30: 炎エネルギーをトラッシュするワザは kyuura の RUL-ENERGY-DISCARD-ATTACKS の文面にしたがう。記録の cards はウインディだけなので、
        # ほかのワザは適用の範囲（errata_scope。記録の notes の引用・同じ印刷の文面）で結ぶ。照らすのは scripts/check_research_links.py
        # v0.31: リザードンの「エナジーバーン」は TXT-CHARIZARD（記録の cards にリザードンがある。適用の範囲ではない）
        self.assertEqual(set(section["errata_text"].values()), {"RUL-ENERGY-DISCARD-ATTACKS", "TXT-CHARIZARD"})
        self.assertEqual(section["errata_text"]["PMCG1-021/power/0"], "TXT-CHARIZARD")
        scoped = {target for scope in section["errata_scope"] for target in scope["targets"]}
        self.assertEqual(scoped, set(section["errata_text"]) - {"PMCG1-019/attack/0", "PMCG1-021/power/0"})
        # v0.31: ピッピの「ゆびをふる」は kyuura の card_differences の最新の説明（p.223 の解説の記録。LD- はない。kyuura への報告事項）
        # v0.42: カイリューの［かけつける］は kyuura の card_differences の最新の説明（p.249 の記録。特殊状態の記述がない。LD- はない）
        self.assertEqual(section["difference_text"], {"PMCG1-067/attack/1": "kyuura data/curation/card_differences.json#PMCG1-067",
                                                      "PMCG3-043/power/0": "kyuura data/curation/card_differences.json#PMCG3-043"})
        for scope in section["errata_scope"]:
            self.assertEqual(section["errata_text"][scope["targets"][0]], scope["record"])

    def test_card_checks_cover_every_verified_card(self):
        """エンジンの照合の記録のあるカードは、kyuura の CC- の id か「kyuura に記録なし」のどちらかに挙げる。"""
        section = LINKS["card_checks"]
        cards = set(read_verification()["cards"])
        self.assertFalse(set(section["engine_verified"]) & set(section["engine_verified_without_kyuura_record"]))
        self.assertEqual(set(section["engine_verified"]) | set(section["engine_verified_without_kyuura_record"]), cards)
        self.assertFalse(set(section["not_in_engine"]) & cards)
        for card, ids in {**section["engine_verified"], **section["not_in_engine"]}.items():
            for cc_id in ids:
                self.assertTrue(cc_id.startswith(f"CC-{card}-"), cc_id)

    def test_classification_differences_do_not_change_behaviour(self):
        """分類の違い（17 件）は、どれも処理を変えない（docs/research-alignment-v0.18a.md 4・5 章）。"""
        self.assertEqual(len(LINKS["classification_differences"]), 17)
        for diff in LINKS["classification_differences"]:
            self.assertIn(diff["kyuura_status"], ("CONFIRMED", "SUPPORTED"))
            self.assertFalse(diff["behaviour_changed"])
            self.assertTrue(diff["kyuura_ruling"].startswith("CR-"))

    def test_z23_subcases(self):
        """Z23 の場合（docs/unresolved-research-v0.18b.md 3 章）を 4 つに分けて持つ。"""
        self.assertEqual([s["id"] for s in LINKS["subcases"]["Z23"]], ["Z23-a", "Z23-b", "Z23-c", "Z23-d"])

    @unittest.skipUnless((KYUURA / ".git").exists(), "../kyuura がない")
    def test_matches_the_research_commit(self):
        """../kyuura があれば、対応表を kyuura の研究の基準のコミットの記録と照らす（論点の分類・未解決の一覧・裁定の分類・最新の説明の文面・
        照合の記録・カードデータの違い）。"""
        result = subprocess.run(["python3", str(ROOT / "scripts" / "check_research_links.py"), "--kyuura", str(KYUURA)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
