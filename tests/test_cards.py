"""カードデータの読み込みと、対応・未対応の分類。

カードデータの由来: kyuura（https://github.com/moheronemy/kyuura）commit
ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691 の data/cards.json。照合は kyuura_engine/data/card_verification.json。
"""

import json
import subprocess
import unittest
from pathlib import Path

from kyuura_engine import EnergyType, can_pay_cost, load_card_pool
from kyuura_engine.cards import read_extract, read_verification

from tests.helpers import CHARMANDER, DIGLETT, DODUO, PONYTA, POTION, RATTATA, VENUSAUR

KYUURA_COMMIT = "ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691"
ROOT = Path(__file__).resolve().parent.parent


class CardPoolTest(unittest.TestCase):
    def test_source_is_pinned_kyuura_commit(self):
        pool = load_card_pool()
        self.assertEqual(pool.source["repository"], "https://github.com/moheronemy/kyuura")
        self.assertEqual(pool.source["commit"], KYUURA_COMMIT)
        self.assertEqual(pool.source["path"], "data/cards.json")

    def test_v0_1_pool_is_ten_basic_pokemon_and_six_basic_energy(self):
        pool = load_card_pool()
        playable = [pool.get(c) for c in sorted(pool.playable_ids)]
        self.assertEqual(len(playable), 16)
        self.assertEqual(sum(d.is_basic_pokemon for d in playable), 10)
        self.assertEqual(sum(d.is_basic_energy for d in playable), 6)
        self.assertEqual({d.provides for d in playable if d.is_basic_energy}, {
            EnergyType.GRASS, EnergyType.FIRE, EnergyType.WATER, EnergyType.LIGHTNING, EnergyType.PSYCHIC, EnergyType.FIGHTING})

    def test_every_playable_attack_has_no_effect_text(self):
        pool = load_card_pool()
        for card_id in pool.playable_ids:
            for attack in pool.get(card_id).attacks:
                self.assertTrue(attack.supported, (card_id, attack.name_ja))
                self.assertIsNone(attack.text_ja)
                self.assertIsNone(attack.text_en)
                self.assertEqual(attack.damage % 10, 0)

    def test_values_are_copied_from_kyuura(self):
        pool = load_card_pool()
        diglett = pool.get(DIGLETT)
        self.assertEqual((diglett.name_ja, diglett.hp, diglett.pokemon_type), ("ディグダ", 30, EnergyType.FIGHTING))
        self.assertEqual((diglett.weakness, diglett.resistance, diglett.resistance_value), (EnergyType.GRASS, EnergyType.LIGHTNING, 30))
        self.assertEqual(diglett.retreat_cost, 0)
        self.assertEqual([(a.name_ja, a.cost, a.damage) for a in diglett.attacks], [
            ("あなをほる", (EnergyType.FIGHTING,), 10),
            ("どろかけ", (EnergyType.FIGHTING, EnergyType.FIGHTING), 30)])
        rattata = pool.get(RATTATA)
        self.assertEqual((rattata.pokemon_type, rattata.weakness, rattata.resistance), (EnergyType.COLORLESS, EnergyType.FIGHTING, EnergyType.PSYCHIC))


class ClassificationTest(unittest.TestCase):
    """未対応のカード・ワザを「効果がないもの」として扱わない。"""

    def test_mixed_attacks_are_classified_one_by_one(self):
        charmander = load_card_pool().get(CHARMANDER)
        scratch, ember = charmander.attacks
        self.assertTrue(scratch.supported)  # ひっかく: 説明文なし
        self.assertFalse(ember.supported)  # ひのこ: 炎エネルギーをトラッシュする効果
        self.assertIn("効果", ember.unsupported_reason)
        self.assertFalse(charmander.supported)
        self.assertFalse(load_card_pool().is_playable(CHARMANDER))

    def test_damage_modifier_is_unsupported(self):
        doduo = load_card_pool().get(DODUO)
        self.assertFalse(doduo.attacks[0].supported)
        self.assertIn("×", doduo.attacks[0].unsupported_reason)

    def test_trainer_evolution_and_power_are_unsupported(self):
        pool = load_card_pool()
        self.assertIn("トレーナー", pool.get(POTION).unsupported_reasons[0])
        reasons = " ".join(pool.get(VENUSAUR).unsupported_reasons)
        self.assertIn("進化", reasons)
        self.assertIn("ポケモンパワー", reasons)


class CostTest(unittest.TestCase):
    """ワザに必要なエネルギー（p.320）。"""

    def test_colorless_can_be_paid_with_any_type(self):
        self.assertTrue(can_pay_cost([EnergyType.COLORLESS], [EnergyType.WATER]))
        self.assertTrue(can_pay_cost([EnergyType.FIRE, EnergyType.COLORLESS], [EnergyType.FIRE, EnergyType.FIRE]))

    def test_typed_cost_needs_that_type(self):
        self.assertFalse(can_pay_cost([EnergyType.FIRE, EnergyType.COLORLESS], [EnergyType.WATER, EnergyType.WATER]))
        self.assertFalse(can_pay_cost([EnergyType.FIRE, EnergyType.FIRE], [EnergyType.FIRE]))

    def test_more_energy_than_needed_is_fine(self):
        self.assertTrue(can_pay_cost([EnergyType.FIGHTING], [EnergyType.FIGHTING, EnergyType.FIGHTING, EnergyType.FIRE]))


class ProvenanceTest(unittest.TestCase):
    def test_every_pool_card_has_a_verification_record(self):
        extract = read_extract()
        verification = read_verification()
        self.assertEqual(verification["kyuura_commit"], extract["source"]["commit"])
        for card_id in extract["pool_v0_1"]:
            record = verification["cards"][card_id]
            self.assertIn(record["status"], verification["status_values"])
            self.assertIsInstance(record["page"], int)

    def test_known_mismatch_is_recorded(self):
        """ポニータ（第1弾）のワザ名は kyuura が「けりとばす」、『オフィシャルブック2000』p.75 が「けとばす」。"""
        pool = load_card_pool()
        self.assertEqual(pool.get(PONYTA).attacks[0].name_ja, "けりとばす")  # kyuura の値をそのまま使う
        record = read_verification()["cards"][PONYTA]
        self.assertEqual(record["status"], "不一致あり")
        self.assertEqual(record["mismatches"][0]["official_book_2000"], "けとばす")

    def test_fields_used_are_copied(self):
        extract = read_extract()
        top_level = {f.split(".")[0] for f in extract["fields_used_by_engine"]}
        self.assertLessEqual(top_level, set(extract["fields_copied"]))

    @unittest.skipUnless((ROOT.parent / "kyuura" / ".git").exists(), "kyuura の clone（../kyuura）がない")
    def test_extract_matches_kyuura_commit(self):
        """../kyuura があれば、同梱の写しが固定したコミットから生成したものと同じか確かめる（なくても他のテストは動く）。"""
        result = subprocess.run(
            ["python3", str(ROOT / "scripts" / "extract_kyuura_cards.py"), "--kyuura", str(ROOT.parent / "kyuura"), "--check"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
