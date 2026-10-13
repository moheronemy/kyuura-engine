"""カードデータの読み込みと、対応・未対応の分類。

カードデータの由来: kyuura（https://github.com/moheronemy/kyuura）commit
ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691 の data/cards.json。照合は kyuura_engine/data/card_verification.json。
"""

import subprocess
import unittest
from pathlib import Path

from kyuura_engine import EnergyType, can_pay_cost, load_card_pool
from kyuura_engine.cards import pool_from_extract, read_extract, read_verification
from kyuura_engine.effects import DEFAULT_EFFECTS, AttackKey

from tests.helpers import (
    BEEDRILL, BILL, BUTTERFREE, CATERPIE, CHARMANDER, DEFENDER, DEWGONG, DIGLETT, DODUO, KAKUNA, METAPOD, PARAS, PARASECT, PIKACHU, PLUSPOWER, PONYTA,
    POTION, RATTATA, SUPER_POTION, SWITCH, ABRA, ALAKAZAM, BLASTOISE, BULBASAUR, CHARIZARD, IVYSAUR, KADABRA, SQUIRTLE, VENUSAUR, VULPIX,
    WARTORTLE, WEEDLE,
)

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
        # v0.2b でトレーナー 3 枚（pool_v0_2b）、v0.2c でプラスパワー（pool_v0_2c）、v0.2d でドードー（pool_v0_2d）、
        # v0.2e でディフェンダー（pool_v0_2e）、v0.2f でピカチュウ（pool_v0_2f）、v0.3a でビードル（pool_v0_3a）、
        # v0.3b でキャタピー・パラス（pool_v0_3b）、v0.3c でロコン（pool_v0_3c）、v0.4a で 1 進化のパラセクト・ジュゴン
        # （pool_v0_4a）、v0.4b で 1 進化のトランセル・コクーン（pool_v0_4b）、v0.4c で 2 進化のスピアー（pool_v0_4c）、
        # v0.4d で 2 進化のバタフリー（pool_v0_4d）、v0.5 でフシギダネ・フシギソウ・フシギバナ（pool_v0_5）、v0.6 でゼニガメ・
        # カメール・カメックス（pool_v0_6）、v0.7 でケーシィ・ユンゲラー・フーディン（pool_v0_7）を加えた。v0.1 の組
        # （トレーナーと v0.2d 以降のポケモン以外）は変わらない
        trainers = sorted(c for c in pool.playable_ids if pool.get(c).category == "trainer")
        self.assertEqual(trainers, [POTION, SWITCH, BILL, DEFENDER, PLUSPOWER])
        self.assertEqual(read_extract()["pool_v0_2e"], [DEFENDER])
        self.assertEqual(read_extract()["pool_v0_2f"], [PIKACHU])
        self.assertTrue(pool.is_playable(PIKACHU))
        self.assertEqual(read_extract()["pool_v0_3a"], [WEEDLE])  # v0.3a でビードル
        self.assertTrue(pool.is_playable(WEEDLE))
        self.assertEqual(read_extract()["pool_v0_3b"], [CATERPIE, PARAS])  # v0.3b でキャタピー・パラス
        self.assertTrue(pool.is_playable(CATERPIE) and pool.is_playable(PARAS))
        self.assertEqual(read_extract()["pool_v0_3c"], [VULPIX])  # v0.3c でロコン
        self.assertTrue(pool.is_playable(VULPIX))
        self.assertEqual(read_extract()["pool_v0_2d"], [DODUO])
        self.assertTrue(pool.is_playable(DODUO))
        self.assertEqual(read_extract()["pool_v0_4a"], [PARASECT, DEWGONG])  # v0.4a で 1 進化
        self.assertTrue(pool.is_playable(PARASECT) and pool.is_playable(DEWGONG))
        self.assertEqual(read_extract()["pool_v0_4b"], [METAPOD, KAKUNA])  # v0.4b で 1 進化（かたまる）
        self.assertTrue(pool.is_playable(METAPOD) and pool.is_playable(KAKUNA))
        self.assertEqual(read_extract()["pool_v0_4c"], [BEEDRILL])  # v0.4c で 2 進化
        self.assertTrue(pool.is_playable(BEEDRILL) and pool.get(BEEDRILL).is_stage2_pokemon)
        self.assertEqual(read_extract()["pool_v0_4d"], [BUTTERFREE])  # v0.4d で 2 進化（ふきとばし・メガドレイン）
        self.assertTrue(pool.is_playable(BUTTERFREE) and pool.get(BUTTERFREE).is_stage2_pokemon)
        self.assertEqual(read_extract()["pool_v0_5"], [BULBASAUR, IVYSAUR, VENUSAUR])  # v0.5（ポケモンパワーのエナジートランス）
        self.assertTrue(all(pool.is_playable(c) for c in (BULBASAUR, IVYSAUR, VENUSAUR)))
        self.assertEqual(read_extract()["pool_v0_6"], [SQUIRTLE, WARTORTLE, BLASTOISE])  # v0.6（ポケモンパワーのあまごい）
        self.assertTrue(all(pool.is_playable(c) for c in (SQUIRTLE, WARTORTLE, BLASTOISE)))
        self.assertEqual(read_extract()["pool_v0_7"], [ABRA, KADABRA, ALAKAZAM])  # v0.7（ポケモンパワーのダメージスワップ）
        self.assertTrue(all(pool.is_playable(c) for c in (ABRA, KADABRA, ALAKAZAM)))
        later = (DODUO, PIKACHU, WEEDLE, CATERPIE, PARAS, VULPIX, PARASECT, DEWGONG, METAPOD, KAKUNA, BEEDRILL, BUTTERFREE,
                 BULBASAUR, IVYSAUR, VENUSAUR, SQUIRTLE, WARTORTLE, BLASTOISE, ABRA, KADABRA, ALAKAZAM)
        playable = [pool.get(c) for c in sorted(pool.playable_ids) if c not in trainers and c not in later]
        self.assertEqual(len(playable), 16)
        self.assertEqual(sum(d.is_basic_pokemon for d in playable), 10)
        self.assertEqual(sum(d.is_basic_energy for d in playable), 6)
        self.assertEqual({d.provides for d in playable if d.is_basic_energy}, {
            EnergyType.GRASS, EnergyType.FIRE, EnergyType.WATER, EnergyType.LIGHTNING, EnergyType.PSYCHIC, EnergyType.FIGHTING})

    def test_every_playable_attack_has_no_effect_text(self):
        """v0.1 の組のワザは、どれも説明文がない（v0.2d のドードーは説明文のあるワザ。tests/test_coin_attacks.py）。"""
        pool = load_card_pool()
        for card_id in set(pool.playable_ids) & set(read_extract()["pool_v0_1"]):
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
        """「×」のダメージのワザも、実装が登録されていなければ未対応。

        v0.2d でドードーの「みだれづき」を登録したので、その登録を除いた登録表で確かめる（v0.2c までは
        既定の登録表で未対応だった）。
        """
        from kyuura_engine.cards import pool_from_extract
        from kyuura_engine.effects import DEFAULT_EFFECTS, AttackKey

        effects = DEFAULT_EFFECTS.without_attacks("test-no-doduo", [AttackKey(DODUO, 0)])
        pool = pool_from_extract(read_extract(), effects)
        doduo = pool.get(DODUO)
        self.assertFalse(doduo.attacks[0].supported)
        self.assertIn("×", doduo.attacks[0].unsupported_reason)
        self.assertFalse(pool.is_playable(DODUO))

    def test_trainer_evolution_and_power_are_unsupported(self):
        pool = load_card_pool()
        # v0.2b できずぐすりを対応にしたので、実装を登録していないトレーナー（いいきずぐすり）で確かめる
        self.assertIn("トレーナー", pool.get(SUPER_POTION).unsupported_reasons[0])
        # v0.4c で 2 進化の段階を扱えるようにしたので、2 進化のカードは段階ではなく、ポケモンパワーと登録のないワザで未対応に
        # なる（v0.4b までは理由の最初が「stage2（2 進化・ベイビィ）は未実装」だった）。v0.4e まではフシギバナ（ポケモンパワー・
        # ソーラービーム）、v0.5 ではカメックス（登録のないポケモンパワー「あまごい」・ワザ「ハイドロポンプ」）で確かめていた。
        # v0.6 ではフーディン（登録のないポケモンパワー「ダメージスワップ」・ワザ「あやしいひかり」）で確かめていた。v0.7 で
        # フーディンを対応にしたので、リザードン（登録のないポケモンパワー「エナジーバーン」・ワザ「ほのおのうず」）で確かめる
        reasons = " ".join(pool.get(CHARIZARD).unsupported_reasons)
        self.assertTrue(pool.get(CHARIZARD).is_stage2_pokemon)
        self.assertNotIn("進化", reasons)
        self.assertIn("ポケモンパワー「エナジーバーン」", reasons)
        self.assertIn("ほのおのうず", reasons)
        # 名前が同じワザでも、カードごとの登録がなければ未対応（v0.6 までフーディンの「あやしいひかり」（ロコンの PMCG1-015 と同じ
        # 名前）で確かめていたこと。v0.7 でフーディンの位置に別の登録を加えたので、登録を除いた登録表で確かめる）
        without = pool_from_extract(read_extract(), DEFAULT_EFFECTS.without_attacks("test-no-alakazam-attack", [AttackKey(ALAKAZAM, 0)]))
        self.assertFalse(without.get(ALAKAZAM).supported)
        self.assertIn("あやしいひかり", " ".join(without.get(ALAKAZAM).unsupported_reasons))
        self.assertTrue(without.get(VULPIX).supported)


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
