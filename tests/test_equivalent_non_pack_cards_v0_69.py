"""v0.69（docs/equivalent-non-pack-cards-v0.69.md）: kyuura の形式 3 のカードデータ（7d3f4ca）への移行と、拡張パック以外の商品の、登録したカードと処理に使う欄が
同じ 96 枚（kyuura data/engine_targets.json の engine_status ``mechanically_equivalent``。写しの組 pool_v0_69）の登録。

- 96 枚は、元のカードの登録を新しい id ごとに同じ登録で写す（effects.EQUIVALENT_CARDS・_with_equivalent_cards。基本エネルギー 12 枚は登録がなく、
  EQUIVALENT_BASIC_ENERGY に対応だけを書く）。同じ名前のカードを自動で対応させない。登録の照合（名前・文面・実装の check）は新しい id のデータでも行う
- 新しい id の動きは、元のカードの仕組みのテスト（v0.31〜v0.66 のテストのクラス）を、カードの定数だけを新しい id に置きかえてもう一度走らせて確かめる
  （``substituted``。テストの中身・期待は変えない）。正式な対戦開始からの対戦（tools/existing_effect_games.py の --batch v0.69）で起こったことは、
  ``GameTest`` が別に確かめる
- 写しの元を上げたので、状態の写しの元（card_data.commit・ログ game_created の card_data_commit）が変わる。固定の参照データとは、この 2 か所だけを
  確かめた移行でもどして比べる（tests/helpers.py の with_card_data_commit_before_v0_69）
"""

from __future__ import annotations

import dataclasses
import importlib
import json
import pickle
import unittest
from pathlib import Path

from kyuura_engine import apply_command, new_game
from kyuura_engine import effects as E
from kyuura_engine import engine as engine_module
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.commands import AttachEnergy, EvolvePokemon, PlayTrainer, Retreat
from kyuura_engine.deck import deck_problems
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.serialize import state_to_dict
from scripts import check_card_sources as cs
from tests.helpers import build_test_state
from tests.log_audit import serialization_problems

ROOT = Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
DOC = ROOT / "docs" / "equivalent-non-pack-cards-v0.69.md"
EXTRACT = read_extract()
CARDS = {c["id"]: c for c in EXTRACT["cards"]}
TARGETS = {c["id"]: c for c in EXTRACT["equivalent_targets"]["cards"]}
POOL_V0_69 = tuple(EXTRACT["pool_v0_69"])
TABLE = {**E.EQUIVALENT_CARDS, **E.EQUIVALENT_BASIC_ENERGY}
RELEASED_2001 = ("NIP1-003", "NIP1-005", "NIP1-006", "NIP1-010", "NIP1-012", "NIP1X-003", "NIP2-001", "NIP2-005", "NIP2-006", "NIP2-007")
DCE_REPRINTS = ("GD1-025", "GD2-024", "GD3-025", "GD4-028", "GD5-025", "GD6-026", "IP1-023", "IP2-025")
DCE = "PMCG1-096"


def _registrations(registry, card_id):
    return cs._registrations(registry, card_id)


class TableTest(unittest.TestCase):
    """表と写しの組（96 枚）。"""

    def test_pool_is_every_mechanically_equivalent_target(self):
        self.assertEqual(len(POOL_V0_69), 96)
        self.assertEqual(set(TABLE), set(POOL_V0_69))
        self.assertFalse(set(E.EQUIVALENT_CARDS) & set(E.EQUIVALENT_BASIC_ENERGY))
        self.assertEqual(EXTRACT["equivalent_targets"]["commit"], EXTRACT["source"]["commit"])
        self.assertEqual([c["id"] for c in EXTRACT["equivalent_targets"]["cards"]], list(POOL_V0_69))
        for card_id in POOL_V0_69:
            with self.subTest(card=card_id):
                self.assertEqual(TARGETS[card_id]["equivalent_to"], [TABLE[card_id]])
        # 種類でしぼっていない（無色2個エネルギー 8 枚は kyuura の category が data_missing）
        self.assertEqual({card_id for card_id in POOL_V0_69 if TARGETS[card_id]["category"] == "data_missing"}, set(DCE_REPRINTS))

    def test_basic_energy_table_is_only_basic_energy(self):
        for new, original in E.EQUIVALENT_BASIC_ENERGY.items():
            self.assertEqual(CARDS[new]["energy"], {**CARDS[original]["energy"]}, new)
            self.assertEqual(CARDS[new]["energy"]["kind"], "basic")
        self.assertEqual(len(E.EQUIVALENT_BASIC_ENERGY), 12)
        self.assertEqual(len(E.EQUIVALENT_CARDS), 84)

    def test_counts(self):
        pool = load_card_pool()
        registry = E.DEFAULT_EFFECTS
        categories = [pool.get(c).category for c in pool.playable_ids]
        # v0.73 で拡張パック以外の商品のトレーナー 18 枚を加えた（774・(546, 198, 30)・トレーナー 198）。v0.74 でスタジアム 13 枚を加えた（787・(546, 211, 30)・トレーナー 211）。
        # v0.70 で拡張パック以外の商品のポケモン 82 枚（ワザ 136）を加えた（v0.69 は 553・(410, 113, 30)・ワザ 689）。v0.71 で拡張パック以外の商品の再録 78 枚（ポケモン 11・トレーナー 67。ワザ 15・特殊能力 6・トレーナー 67）を加えた。
        # v0.72 で拡張パック以外の商品のポケモン 43 枚（ワザ 77）を加えた。
        self.assertEqual(len(pool.playable_ids), 1080)  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚（ワザ 14・特殊能力 12）を加えた  # v0.85 でポケモン 13 枚（ワザ 17・特殊能力 9）・ミラクルエネルギーを加えた  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚を含む）を加えた  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.83 でポケモン 18 枚（ワザ 33）を加えた  # v0.84 でポケモン 12 枚（ワザ 19・特殊能力 5）・ポケモン育て屋夫婦を加えた
        self.assertEqual((categories.count("pokemon"), categories.count("trainer"), categories.count("energy")), (783, 260, 37))  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚（ワザ 14・特殊能力 12）を加えた  # v0.85 でポケモン 13 枚（ワザ 17・特殊能力 9）・ミラクルエネルギーを加えた  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚を含む）を加えた  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.83 でポケモン 18 枚（ワザ 33）を加えた  # v0.84 でポケモン 12 枚（ワザ 19・特殊能力 5）・ポケモン育て屋夫婦を加えた
        self.assertEqual((len(registry.attack_keys()), len(registry.power_keys()), len(registry.trainer_ids()), len(registry.energy_ids())),
                         (1312, 114, 260, 19))  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚（ワザ 14・特殊能力 12）を加えた  # v0.85 でポケモン 13 枚（ワザ 17・特殊能力 9）・ミラクルエネルギーを加えた  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚を含む）を加えた  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.83 でポケモン 18 枚（ワザ 33）を加えた  # v0.84 でポケモン 12 枚（ワザ 19・特殊能力 5）・ポケモン育て屋夫婦を加えた
        self.assertEqual(registry.id, "kyuura-engine-0.13")
        self.assertEqual(set(POOL_V0_69) - pool.playable_ids, set())

    def test_no_automatic_mapping_by_name(self):
        """登録を写したのは表のカードだけ。写しの、同じ名前で登録のないカード（表にないもの）は未対応のまま。"""
        registered = cs.registered_cards(E.DEFAULT_EFFECTS)
        pool = load_card_pool()
        names = {pool.get(c).name_ja for c in registered}
        for card_id, definition in pool.definitions.items():
            if definition.name_ja in names and card_id not in registered and not definition.is_basic_energy:
                self.assertNotIn(card_id, TABLE, card_id)
        for new in E.EQUIVALENT_CARDS:
            self.assertIn(new, registered)

    def test_no_card_id_branches(self):
        for path in [ROOT / "kyuura_engine" / "engine.py", *(ROOT / "kyuura_engine" / "resolution").glob("*.py")]:
            text = path.read_text(encoding="utf-8")
            for card_id in POOL_V0_69:
                self.assertNotIn(f'"{card_id}"', text, path.name)


class ParityTest(unittest.TestCase):
    """96 枚すべて: 処理に使う欄・同じカードの組・登録が元のカードと同じ。"""

    def test_every_card_matches_its_original(self):
        pool = load_card_pool()
        registry = E.DEFAULT_EFFECTS
        for new, original in TABLE.items():
            with self.subTest(card=new, original=original):
                self.assertEqual(cs.engine_view(CARDS[new]), cs.engine_view(CARDS[original]))
                self.assertIsNotNone(CARDS[new]["same_card_group"])
                self.assertEqual(CARDS[new]["same_card_group"], CARDS[original]["same_card_group"])
                self.assertTrue(pool.get(new).supported, pool.get(new).unsupported_reasons)
                mine, theirs = _registrations(registry, new), _registrations(registry, original)
                self.assertEqual(set(mine), set(theirs))
                for target in mine:
                    self.assertIs(mine[target], theirs[target])
                ours = dataclasses.replace(pool.get(new), id=original, name_en=None, energy_text_en=None, trainer_text_en=None,
                                           attacks=tuple(dataclasses.replace(a, name_en=None, text_en=None) for a in pool.get(new).attacks),
                                           powers=tuple(dataclasses.replace(w, name_en=None, text_en=None) for w in pool.get(new).powers))
                plain = pool.get(original)
                plain = dataclasses.replace(plain, name_en=None, energy_text_en=None, trainer_text_en=None,
                                            attacks=tuple(dataclasses.replace(a, name_en=None, text_en=None) for a in plain.attacks),
                                            powers=tuple(dataclasses.replace(w, name_en=None, text_en=None) for w in plain.powers))
                self.assertEqual(ours, plain)

    def test_fields_compared(self):
        """比べる欄: 段階・進化元・タイプ・HP・弱点・抵抗力・にげる・ワザ（名前・エネルギー・ダメージ・説明）・特殊能力（種類・名前・説明）・トレーナーの種類と説明・
        エネルギーの種類・出すもの・説明。"""
        view = cs.engine_view(CARDS["GD6-004"])
        self.assertEqual(set(view["pokemon"]), {"stage", "evolves_from", "hp", "types", "weaknesses", "resistances", "retreat_cost", "rules_text", "powers",
                                                "attacks"})
        self.assertEqual(set(cs.engine_view(CARDS["GD2-015"])["trainer"]), {"kinds", "text"})
        self.assertEqual(set(cs.engine_view(CARDS["GD1-025"])["energy"]), {"kind", "provides", "text"})

    def test_helper_rejects_wrong_tables(self):
        registry = E.DEFAULT_EFFECTS
        base = registry.without_attacks("t", [k for k in registry.attack_keys() if k.card_id in E.EQUIVALENT_CARDS]) \
            .without_powers("t", [k for k in registry.power_keys() if k.card_id in E.EQUIVALENT_CARDS]) \
            .without_trainers("t", [c for c in registry.trainer_ids() if c in E.EQUIVALENT_CARDS]) \
            .without_energies("t", [c for c in registry.energy_ids() if c in E.EQUIVALENT_CARDS])
        rebuilt = E._with_equivalent_cards(base, E.EQUIVALENT_CARDS)
        self.assertEqual(len(rebuilt.attack_keys()), 1312)  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚（ワザ 14・特殊能力 12）を加えた  # v0.85 でポケモン 13 枚（ワザ 17・特殊能力 9）・ミラクルエネルギーを加えた  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.72 で 77、v0.71 で 15、v0.70 で 136 を加えた（v0.69 は 689）  # v0.83 でポケモン 18 枚（ワザ 33）を加えた  # v0.84 でポケモン 12 枚（ワザ 19・特殊能力 5）・ポケモン育て屋夫婦を加えた
        with self.assertRaises(RuntimeError):
            E._with_equivalent_cards(base, {"GD1-002": "GD1-011"})  # 元のカードに登録がない
        with self.assertRaises(RuntimeError):
            E._with_equivalent_cards(registry, {"GD1-002": "PMCG5-018"})  # すでに登録がある
        with self.assertRaises(RuntimeError):
            E._with_equivalent_cards(base, {"GD1-002": "PMCG5-018", "PMCG5-018": "PMCG5-017"})  # 写しの写し
        missing = base.without_attacks("t", [k for k in base.attack_keys() if k.card_id == "PMCG5-018"])
        with self.assertRaises(RuntimeError):
            E._with_equivalent_cards(missing, {"GD1-002": "PMCG5-018"})

    def test_data_mismatch_makes_the_card_unsupported(self):
        """新しい id のデータの説明文・名前が登録と違えば、そのカードは未対応（元のカードの登録を流用しても照合は新しい id のデータで行う）。"""
        extract = json.loads(json.dumps(EXTRACT))
        card = next(c for c in extract["cards"] if c["id"] == "GD2-012")
        card["pokemon"]["attacks"][0]["text"]["ja"] = "ちがう説明文"
        trainer = next(c for c in extract["cards"] if c["id"] == "GD2-015")
        trainer["name"]["ja"] = "ちがう名前"
        pool = pool_from_extract(extract)
        self.assertFalse(pool.get("GD2-012").supported)
        self.assertFalse(pool.get("GD2-015").supported)
        self.assertTrue(pool.get("PR1-031").supported)


class RecordTest(unittest.TestCase):
    """採用の記録（card_sources.json）・研究の対応表・2001 年の発売のカード。"""

    def setUp(self):
        self.sources = cs.load_sources()
        self.links = cs.load_links()

    def test_records(self):
        self.assertEqual(cs.problems(), [])
        for new, original in E.EQUIVALENT_CARDS.items():
            record = self.sources["cards"][new]
            with self.subTest(card=new):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["equivalent_to"]),
                                 (cs.KYUURA_DATA, cs.ADOPTED, EXTRACT["source"]["commit"], original))
                self.assertEqual(record["external_checks"], [])  # 外部照合はしていない（元のカードの照合を再利用する）
                self.assertEqual(set(record["play_text"].values()) - {cs.EQUIVALENT}, set())
                self.assertFalse(set(record) & cs.GUIDEBOOK_KEYS)
        for new in E.EQUIVALENT_BASIC_ENERGY:
            self.assertNotIn(new, self.sources["cards"])  # 基本エネルギーは登録がないので採用の記録もない

    def test_old_records_keep_their_commit_and_dates(self):
        """v0.68 までの採用の記録の採用したときのデータのコミット・記録した日は書き換えない（data_migrations で移行を書く）。"""
        (migration,) = self.sources["data_migrations"]
        self.assertEqual((migration["from"], migration["to"]), (EXTRACT["previous_source"]["commit"], EXTRACT["source"]["commit"]))
        # v0.70 の採用の記録（写しの元 7d3f4ca で採用した。拡張パック以外の商品のポケモン 82 枚）は、移行の前の記録ではない
        v070 = set(read_extract()["pool_v0_70"]) | set(read_extract()["pool_v0_71"]) | set(read_extract()["pool_v0_72"]) | set(read_extract()["pool_v0_73"]) | set(read_extract()["pool_v0_74"]) | set(read_extract()["pool_v0_75"]) | set(read_extract()["pool_v0_76"]) | set(read_extract()["pool_v0_77"]) | set(read_extract()["pool_v0_78"]) | set(read_extract()["pool_v0_79"]) | set(read_extract()["pool_v0_80"]) | set(read_extract()["pool_v0_81"]) | set(read_extract()["pool_v0_82"]) | set(read_extract()["pool_v0_83"]) | set(read_extract()["pool_v0_84"]) | set(read_extract()["pool_v0_85"]) | set(read_extract()["pool_v0_86"]) | set(read_extract()["pool_v0_87"])  # v0.76 の 24 枚も除く。 v0.75 の 15 枚も除く。 v0.71 の再録 78 枚・v0.72 の 43 枚・v0.73 の 18 枚も写しの元 7d3f4ca で採用した
        old = [r for c, r in self.sources["cards"].items() if r.get("basis") == cs.KYUURA_DATA and c not in E.EQUIVALENT_CARDS and c not in v070]
        self.assertTrue(old)
        self.assertEqual({r["kyuura_commit"] for r in old}, {migration["from"]})
        self.assertTrue(all(r["recorded_on"] <= "2026-10-19" for r in old))

    def test_equivalent_record_rejections(self):
        """記録の誤り（元のカード・外部照合・処理に使う文面の根拠）を検査が見つける。"""
        def run(mutate):
            sources = json.loads(json.dumps(self.sources))
            mutate(sources["cards"])
            return cs.problems(sources)
        self.assertTrue(any("EQUIVALENT_CARDS" in p for p in run(lambda c: c["GD1-002"].update(equivalent_to="PMCG5-017"))))
        self.assertTrue(any("外部照合" in p for p in run(lambda c: c["GD1-002"].update(external_checks=[{"site": "pcg-search.com"}]))))
        self.assertTrue(any("play_text" in p for p in run(lambda c: c["GD1-002"]["play_text"].update({"attack/0": cs.PRINTED_TEXT}))))
        self.assertTrue(any("登録の根拠" in p or "card_verification" in p or "ちょうど一方" in p
                            for p in run(lambda c: c.pop("GD1-002"))))

    def test_research_links(self):
        section = self.links["latest_descriptions"]["equivalent_registrations"]
        self.assertEqual(section["GD2-012/attack/0"], "PMCG5-027/attack/0")  # スターブーメラン（元のカードの最新の説明 LD-PMCG5-027-ATK0 にしたがう）
        self.assertEqual(self.links["research_commit"], EXTRACT["source"]["commit"])
        self.assertEqual(self.links["card_data_commit"], EXTRACT["source"]["commit"])
        self.assertEqual(self.links["card_data_differences"], [])

    @unittest.skipUnless((KYUURA / ".git").exists(), "../kyuura がない")
    def test_research_links_check(self):
        from scripts import check_research_links as research

        self.assertEqual(research.check(KYUURA), [])
        links = json.loads(json.dumps(self.links))
        links["latest_descriptions"]["equivalent_registrations"]["GD2-012/attack/0"] = "PMCG5-026/attack/0"
        self.assertTrue(any("GD2-012/attack/0" in p for p in research.check(KYUURA, links=links)))
        links = json.loads(json.dumps(self.links))
        del links["latest_descriptions"]["equivalent_registrations"]["GD2-012/attack/0"]
        self.assertTrue(research.check(KYUURA, links=links))

    def test_released_after_rule_base(self):
        """2001 年のイントロパック（neo）の 10 枚は、2000.02.14 版のルールのあとの発売。発売日は変えず、kyuura の記録のまま持つ。"""
        late = {c for c, t in TARGETS.items() if t["released_after_rule_base"]}
        self.assertEqual(late, set(RELEASED_2001))
        for card_id in RELEASED_2001:
            self.assertEqual(TARGETS[card_id]["release_date"], "2001-04-06")
            definition = load_card_pool().get(card_id)
            self.assertNotEqual(definition.stage, "baby")
            if card_id in self.sources["cards"]:
                self.assertIn("2000.02.14 版のルールのあと", self.sources["cards"][card_id]["notes"])
        for card_id in set(POOL_V0_69) - late:
            self.assertFalse(TARGETS[card_id]["released_after_rule_base"])


def _deck(*cards):
    deck = [c for card, n in cards for c in [card] * n]
    return deck


class DeckTest(unittest.TestCase):
    """同じ名前の 4 枚の制限は id をまたいで数える。基本エネルギーは制限なし。"""

    def test_same_name_across_ids(self):
        pool = load_card_pool()
        deck = _deck(("PMCG5-018", 3), ("GD1-002", 2), ("PMCG1-097", 55))
        self.assertTrue(any("TOO_MANY_COPIES" in p and "タケシのロコン" in p for p in deck_problems(deck, pool)))
        deck = _deck(("PMCG5-018", 2), ("GD1-002", 2), ("PMCG1-097", 56))
        self.assertEqual(deck_problems(deck, pool), [])

    def test_dce_across_ids(self):
        pool = load_card_pool()
        deck = _deck(("PMCG1-018", 4), (DCE, 2), ("GD1-025", 2), ("IP1-023", 1), ("PMCG1-098", 51))
        self.assertTrue(any("TOO_MANY_COPIES" in p and "無色2個エネルギー" in p for p in deck_problems(deck, pool)))

    def test_basic_energy_has_no_limit(self):
        pool = load_card_pool()
        deck = _deck(("IP2-001", 2), ("NIP1-012", 2), ("PMCG1-098", 20), ("IP2-004", 20), ("NIP1-005", 16))
        self.assertEqual(deck_problems(deck, pool), [])
        state = new_game(deck, deck, 3)
        self.assertEqual(state.card_data.commit, EXTRACT["source"]["commit"])


class MixedEvolutionTest(unittest.TestCase):
    """進化は名前と段階で決まる（版によらない）。元のカードと新しい id を混ぜて進化させる。"""

    def test_mixed_line(self):
        state = build_test_state([{"active": {"card": "PMCG6-043", "played_turn": 1}, "hand": ["GD6-003", "PMCG6-053"]}, {"active": "PMCG1-018"}],
                                 turn_number=5)
        a = state.players[0].active
        state = apply_command(state, EvolvePokemon(0, state.players[0].hand[0], a.pokemon_id))
        self.assertEqual(state.cards[state.players[0].active.card].card_id, "GD6-003")
        from kyuura_engine import EndTurn

        state = apply_command(apply_command(state, EndTurn(0)), EndTurn(1))
        state = apply_command(state, EvolvePokemon(0, state.players[0].hand[0], a.pokemon_id))
        top = state.players[0].active
        self.assertEqual([state.cards[u].card_id for u in (*top.evolution_stack, top.card)], ["PMCG6-043", "GD6-003", "PMCG6-053"])
        evolves = [e for e in state.log if e["kind"] == "evolve"]
        self.assertEqual([(e["from_card_id"], e["to_card_id"]) for e in evolves], [("PMCG6-043", "GD6-003"), ("GD6-003", "PMCG6-053")])

    def test_name_mismatch_still_rejected(self):
        state = build_test_state([{"active": {"card": "PMCG1-018", "played_turn": 1}, "hand": ["GD6-003"]}, {"active": "PMCG1-018"}], turn_number=5)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].active.pokemon_id))
        self.assertEqual(ctx.exception.code, "EVOLUTION_NAME_MISMATCH")


class DoubleColorlessTest(unittest.TestCase):
    """無色2個エネルギーの新しい id: 1 枚で無色 2 個（カードの枚数と個数を分ける）・ワザとにげるの支払い・基本エネルギーカードではない。"""

    def test_units_and_payment(self):
        for card_id in DCE_REPRINTS:
            with self.subTest(card=card_id):
                state = build_test_state([{"active": {"card": "PMCG1-018"}, "hand": [card_id]}, {"active": "PMCG1-018"}])
                p = state.players[0]
                state = apply_command(state, AttachEnergy(0, p.hand[0], p.active.card))
                active = state.players[0].active
                self.assertEqual(len(active.energy), 1)
                self.assertEqual(E.energy_unit_count(state, active.energy, active), 2)
                self.assertFalse(state.card_def(active.energy[0]).is_basic_energy)
                self.assertEqual(E.energy_units(state, active, active.energy[0]), (frozenset({E.EnergyType.COLORLESS}),) * 2)

    def test_retreat_with_reprint(self):
        """にげる 3 のタケシのサイドン（GD1-013）が、無色2個エネルギーの新しい id 1 枚と基本エネルギー 1 枚でにげる（個数 3）。にげる 1 のナツメのユンゲラーが
        無色2個エネルギーの新しい id 1 枚でにげる選び方は、個数がにげるエネルギーより多いので RT1（v0.58 と同じ）。"""
        state = build_test_state([{"active": {"card": "GD1-013", "evolved_from": "PMCG5-049", "energy": ["GD1-025", "IP2-012"]}, "bench": ["PMCG5-049"]},
                                  {"active": "PMCG1-018"}])
        p = state.players[0]
        self.assertEqual(E.retreat_cost(state, 0).maximum, 3)
        new = apply_command(state, Retreat(0, tuple(p.active.energy), p.bench[0].card))
        self.assertEqual(new.cards[new.players[0].bench[-1].card].card_id, "GD1-013")
        state = build_test_state([{"active": {"card": "GD6-003", "evolved_from": "PMCG6-043", "energy": ["IP1-023"]}, "bench": ["PMCG6-043"]},
                                  {"active": "PMCG1-018"}])
        p = state.players[0]
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, Retreat(0, tuple(p.active.energy), p.bench[0].card))
        self.assertEqual(ctx.exception.code, "UNRESOLVED_RETREAT_OVERPAY")

    def test_not_basic_energy_for_retrieval(self):
        """エネルギー回収（基本エネルギーカードだけ）の対象にならない（トラッシュに無色2個エネルギーの新しい id しかなければ ER10）。"""
        state = build_test_state([{"active": "PMCG1-018", "hand": ["PMCG1-076", "PMCG1-098"], "discard": ["GD2-024", "IP2-025"]}, {"active": "PMCG1-018"}])
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        self.assertEqual(ctx.exception.code, "UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET")


class SecretPlanPoolTest(unittest.TestCase):
    """マチスの秘策の受け付けるかの確かめ: 対応しているカードの一覧が増えても、試すカードは処理の同じカードを 1 枚で代表する（v0.68 と同じ 457 枚。試す回数を
    増やさない。公開の情報だけで決まる）。2 枚以上を指定するコマンドの制限は変えていない。v0.70 で拡張パック以外の商品のポケモン 82 枚（処理の違うカード 70 種類）が
    加わり、試すカードは 527 枚（v0.69 の 457 枚 + 70。tests/test_non_pack_effect_reuse_v0_70.py）。v0.69 の新しい id を試すカードに加えないことは変えていない"""

    def test_candidates_unchanged(self):
        pool = load_card_pool()
        candidates = engine_module._identity_candidates(pool)
        v070 = set(read_extract()["pool_v0_70"]) | set(read_extract()["pool_v0_71"]) | set(read_extract()["pool_v0_72"]) | set(read_extract()["pool_v0_73"]) | set(read_extract()["pool_v0_74"]) | set(read_extract()["pool_v0_75"]) | set(read_extract()["pool_v0_76"]) | set(read_extract()["pool_v0_77"]) | set(read_extract()["pool_v0_78"]) | set(read_extract()["pool_v0_79"]) | set(read_extract()["pool_v0_80"]) | set(read_extract()["pool_v0_81"]) | set(read_extract()["pool_v0_82"]) | set(read_extract()["pool_v0_83"]) | set(read_extract()["pool_v0_84"]) | set(read_extract()["pool_v0_85"]) | set(read_extract()["pool_v0_86"]) | set(read_extract()["pool_v0_87"])  # v0.76 の 24 枚も除く。 v0.75 の 15 枚も除く。 v0.71: 再録のカード（処理の違う 45 種類）・v0.72 の 43 枚・v0.73 の 18 枚も除いて比べる
        self.assertEqual(len(set(candidates) - v070), 457)
        self.assertFalse(set(candidates) & set(POOL_V0_69) - {c for c in POOL_V0_69 if c not in TABLE})
        self.assertEqual(set(candidates) - v070, set(pool.playable_ids) - set(POOL_V0_69) - v070)
        keys = {engine_module._behavior_key(pool, c) for c in candidates}
        for new in POOL_V0_69:
            self.assertIn(engine_module._behavior_key(pool, new), keys, new)
        self.assertEqual(engine_module._IDENTITY_TRIAL_LIMIT, 512)

    def test_quiz_names_have_no_duplicates(self):
        state = build_test_state([{"active": "PMCG1-018"}, {"active": "PMCG1-018"}])
        names = E.quiz_answer_names(state)
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names.count("タケシのロコン"), 1)


def substituted(module_name: str, class_name: str, names: dict[str, str], *, tables_in: tuple[str, ...] = ()):
    """``module_name`` のテストのクラスを、モジュールのカードの定数（``names``: 定数の名前 → 新しい id）だけを置きかえて走らせるクラス。テストの中身・期待は変えない。
    ``tables_in`` は、盤面を作る関数（``mon`` など）を借りているモジュール（その表にも新しい id の鍵を加える）。"""
    module = importlib.import_module(module_name)
    base = getattr(module, class_name)
    table_modules = (module, *(importlib.import_module(name) for name in tables_in))

    class Substituted(base):
        @classmethod
        def setUpClass(cls):
            cls._saved = {name: getattr(module, name) for name in names}
            for name, value in names.items():
                if TABLE.get(value) != cls._saved[name]:
                    raise AssertionError(f"{value} は {name}（{cls._saved[name]}）の新しい id ではない")
                setattr(module, name, value)
            # モジュールの表（進化の下のカードの表 BELOW など。元の id を鍵にする辞書）にも、新しい id の鍵を同じ値で加える（表の値は変えない）
            originals = {cls._saved[name]: value for name, value in names.items()}
            cls._tables = []
            for owner in table_modules:
                for name, table in list(vars(owner).items()):
                    if isinstance(table, dict) and not name.startswith("_") and any(key in table for key in originals):
                        cls._tables.append((owner, name, table))
                        setattr(owner, name, {**table, **{new: table[old] for old, new in originals.items() if old in table}})
            super().setUpClass()

        @classmethod
        def tearDownClass(cls):
            try:
                super().tearDownClass()
            finally:
                for name, value in cls._saved.items():
                    setattr(module, name, value)
                for owner, name, table in cls._tables:
                    setattr(owner, name, table)

        def test_substitution_is_active(self):
            for name, value in names.items():
                self.assertEqual(getattr(module, name), value)
                self.assertNotEqual(self._saved[name], value)

    Substituted.__name__ = Substituted.__qualname__ = f"{class_name}With{'_'.join(v.replace('-', '') for v in names.values())}"
    Substituted.__module__ = __name__
    return Substituted


FleeReprintTest = substituted("tests.test_reactive_decisions_v0_65", "FleeTest", {"MISTYS_TENTACRUEL": "GD2-004"})
BenchGuardReprintTest = substituted("tests.test_reactive_decisions_v0_65", "BenchGuardTest", {"BROCKS_RHYDON": "GD1-013"})
EnergyChargeReprintTest = substituted("tests.test_declared_entry_powers_v0_43", "EnergyChargeTest", {"LT_SURGES_MAGNETON": "GD3-006"})
SweetTrapReprintTest = substituted("tests.test_power_decisions_v0_42", "SweetTrapTest", {"ERIKAS_VICTREEBEL": "GD4-008"})
NaturalCureReprintTest = substituted("tests.test_held_cards_v0_31_mechanisms", "PowerTest",
                                     {"BLAINES_VULPIX": "GD5-002", "BLAINES_NINETALES": "GD5-004"}, tables_in=("tests.test_held_cards_v0_31",))
StrangeBarrierReprintTest = substituted("tests.test_continuous_powers_v0_46", "StrangeBarrierTest", {"ERIKAS_DRATINI": "GD4-013"})
StrangeBarrierPromoTest = substituted("tests.test_continuous_powers_v0_46", "StrangeBarrierTest", {"ERIKAS_DRATINI": "PR1-039"})
PsylinkReprintTest = substituted("tests.test_virtual_attacks_transformation_v0_49", "PsylinkTest", {"SABRINAS_ALAKAZAM": "GD6-004"})
PeekReprintTest = substituted("tests.test_fossil_hidden_info_v0_47", "PeekAndSwapTest", {"JUNGLE_MANKEY": "PR1-061"})
EspReprintTest = substituted("tests.test_optional_trainers_v0_66", "EspTest", {"SABRINAS_ESP": "GD6-018"})
DuelReprintTest = substituted("tests.test_optional_trainers_v0_66", "MistysDuelTest", {"MISTYS_DUEL": "GD2-017"})
PerfumeReprintTest = substituted("tests.test_trainer_decisions_turn_effects_v0_56", "ErikasPerfumeTest", {"ERIKAS_PERFUME": "GD4-018"})
LtSurgeReprintTest = substituted("tests.test_trainer_decisions_turn_effects_v0_56", "LtSurgeTest", {"LT_SURGE_TRAINER": "GD3-021"})
TreatyReprintTest = substituted("tests.test_trainer_decisions_turn_effects_v0_56", "LtSurgesTreatyTest", {"LT_SURGES_TREATY": "GD3-022"})
DceUnitsReprintTest = substituted("tests.test_stadium_reuse_special_energy_v0_58", "EnergyUnitsTest", {"DOUBLE_COLORLESS_ENERGY": "GD1-025"})
DceRetreatReprintTest = substituted("tests.test_stadium_reuse_special_energy_v0_58", "RetreatTest", {"DOUBLE_COLORLESS_ENERGY": "IP2-025"})


class SaveRestoreTest(unittest.TestCase):
    """新しい id は状態・ログ・書き出しにそのまま残る（元の id に置きかえない）。保存と復元。"""

    def test_ids_survive_save_and_restore(self):
        state = build_test_state([{"active": {"card": "GD2-004", "evolved_from": "PR1-048", "energy": ["IP2-005"]}, "hand": ["GD2-017"]},
                                  {"active": "GD1-013"}])
        data = state_to_dict(state, format_version=22)
        copied = pickle.loads(pickle.dumps(state))
        self.assertEqual(state_to_dict(copied, format_version=22), data)
        ids = {c.card_id for c in state.cards.values()}
        self.assertTrue({"GD2-004", "PR1-048", "IP2-005", "GD2-017", "GD1-013"} <= ids)
        self.assertEqual(serialization_problems(state), [])


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game）からの対戦: 新しい id と元のカードを混ぜたデッキ（tools/existing_effect_games.py の M69・S69）、決まった seed・席の入れかえ。"""

    @classmethod
    def setUpClass(cls):
        from tools import existing_effect_games as games

        cls.games = games
        cls.results = games.run(range(2), pairings=games.PAIRINGS_V0_69)

    def test_games_finish_without_audit_failures(self):
        for name, run in self.results.items():
            for game in run["games"]:
                with self.subTest(run=name, seed=game["seed"], decks=game["decks"]):
                    self.assertIn(game["outcome"], ("game_over", "sudden_death", "halted"), game.get("error"))
                    self.assertEqual(game["audit"], {})

    def test_new_ids_are_played(self):
        from collections import Counter

        uses = Counter()
        for run in self.results.values():
            for game in run["games"]:
                uses.update(game["v069"])
        self.assertTrue(any(k.startswith("attack_") for k in uses))
        self.assertTrue(any(k.startswith("evolve_") for k in uses))
        self.assertGreater(uses["in_deck"], 0)

    def test_decks_mix_new_and_original_ids(self):
        for label in ("M69", "S69"):
            deck = self.games.deck_cards(label)
            self.assertTrue(set(deck) & set(POOL_V0_69))
            self.assertTrue(set(deck) - set(POOL_V0_69))
            self.assertEqual(deck_problems(deck), [])


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = DOC.read_text(encoding="utf-8")
        for word in ("7d3f4ca", "mechanically_equivalent", "EQUIVALENT_CARDS", "FIX-PMCG2-046-ATK0-TEXT", "data_migrations", "pool_v0_69", "2001-04-06"):
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()
