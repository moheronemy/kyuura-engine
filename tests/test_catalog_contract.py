"""Current catalog totals belong here; release tests check their own cards."""

import json
import subprocess
import unittest
from collections import Counter
from pathlib import Path

from kyuura_engine.cards import load_card_pool, read_extract
from kyuura_engine.effects import DEFAULT_EFFECTS
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests.log_audit import LATEST_FORMAT
from tests.release_catalog import cards_after, cards_before

ROOT = Path(__file__).resolve().parent.parent


class CatalogContractTest(unittest.TestCase):
    def test_current_catalog_totals(self):
        pool = load_card_pool()
        extract = read_extract()
        self.assertEqual(len(extract["cards"]), 1191)
        self.assertEqual(len(pool.playable_ids), 1191)
        self.assertEqual(pool.playable_ids, frozenset(
            card.id for card in pool.definitions.values() if card.supported))
        self.assertEqual(
            Counter(pool.get(card).category for card in pool.playable_ids),
            {"pokemon": 892, "trainer": 262, "energy": 37},
        )
        registry = DEFAULT_EFFECTS
        self.assertEqual(
            (len(registry.attack_keys()), len(registry.power_keys()),
             len(registry.trainer_ids()), len(registry.energy_ids())),
            (1477, 146, 262, 19),
        )
        self.assertEqual(
            sum(registry.trainer_entry(card).effect.is_stadium
                for card in registry.trainer_ids()),
            41,
        )

    def test_current_quiz_names_and_secret_plan_trials(self):
        # カツラのクイズの名前の候補（対応しているポケモンの名前）と、マチスの秘策の試すカード（処理の同じカードを 1 枚で代表）・そのうちのたねポケモン
        from kyuura_engine import engine

        pool = load_card_pool()
        names = {pool.get(card).name_ja for card in pool.playable_ids if pool.get(card).category == "pokemon"}
        self.assertEqual(len(names), 459)
        candidates = engine._identity_candidates(pool)
        basics = [card for card in candidates if pool.get(card).category == "pokemon" and pool.get(card).stage == "basic"]
        self.assertEqual((len(candidates), len(basics)), (984, 462))
        self.assertEqual(engine._IDENTITY_TRIAL_LIMIT, 512)

    def test_current_research_totals(self):
        data = ROOT / "kyuura_engine" / "data"
        links = json.loads((data / "research_links.json").read_text())
        self.assertEqual(
            (links["counts"]["engine_stop_codes"],
             links["counts"]["engine_unresolved_rulings"]),
            (234, 235),
        )
        self.assertEqual(len(links["latest_descriptions"]["adopted_printed_text"]), 1132)

    def test_current_format_and_audit_agree(self):
        # Keep the audit's independently maintained schema check. Deriving its
        # version from the serializer would hide missing audit field coverage.
        self.assertEqual(LATEST_FORMAT, 26)
        self.assertEqual(FORMAT_VERSIONS, tuple(range(1, LATEST_FORMAT + 1)))

    def test_target_universe_and_current_unsupported_totals(self):
        extract = read_extract()
        kyuura = ROOT.parent / "kyuura"
        if not (kyuura / ".git").exists():
            self.skipTest("../kyuura is required for the pinned target catalog")
        raw = subprocess.check_output([
            "git", "-C", str(kyuura), "show",
            f"{extract['source']['commit']}:data/engine_targets.json",
        ])
        targets = json.loads(raw)["cards"]
        ids = {card["id"] for card in targets}
        neo = {card["id"] for card in targets if card["id"].startswith("neo")}
        non_pack = {card["id"] for card in targets
                    if card["product_group"] != "expansion_pack"}
        pmcg = {card for card in ids if card.startswith("PMCG")}
        self.assertEqual(len(ids), len(targets))
        self.assertEqual((len(ids), len(pmcg), len(non_pack), len(neo)),
                         (1377, 457, 597, 323))
        self.assertEqual(
            Counter(card["jp_set"] for card in targets if card["id"] in neo),
            {"neo1": 96, "neo2": 57, "neo3": 57, "neo4": 113},
        )
        playable = load_card_pool().playable_ids
        self.assertLessEqual(playable, ids)
        self.assertLessEqual(pmcg, playable)
        self.assertEqual((len(ids - playable), len(neo - playable),
                          len(non_pack - playable)), (186, 86, 100))


class ReleaseCohortTest(unittest.TestCase):
    def test_future_releases_do_not_change_an_older_slice(self):
        extract = {"pool_v0_71": ["old"], "pool_v0_72": ["next"], "cards": []}
        self.assertEqual(cards_after(extract, "0.71"), {"next"})
        extract.update({"pool_v0_89": ["future"], "pool_v1_1": ["later"]})
        self.assertEqual(cards_after(extract, "0.71"), {"next", "future", "later"})
        self.assertEqual(cards_before(extract, "0.72"), {"old"})

    def test_numeric_order_suffixes_and_duplicate_ids(self):
        extract = {"pool_v0_9": ["a"], "pool_v0_10": ["a", "b"],
                   "pool_v0_10a": ["c"], "pool_v0_11": ["d"]}
        self.assertEqual(cards_before(extract, "0.10a"), {"a", "b"})
        self.assertEqual(cards_after(extract, "0.10"), {"c", "d"})
        self.assertEqual(cards_after(extract, "pool_v0_10a"), {"d"})

    def test_malformed_release_fails_instead_of_ignoring_a_pool(self):
        with self.assertRaises(ValueError):
            cards_after({}, "latest")
        with self.assertRaises(ValueError):
            cards_after({"pool_vbad": ["a"]}, "0.88")


if __name__ == "__main__":
    unittest.main()
