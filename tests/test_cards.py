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
    WARTORTLE, WEEDLE, GRIMER, MUK, GASTLY, HAUNTER, BASE_HAUNTER, MACHOP, MACHOKE, MACHAMP, GIOVANNIS_MACHAMP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHOP, ROCKETS_MOLTRES,
    ROCKET_SQUIRTLE, DARK_WARTORTLE, TANGELA, GIOVANNIS_MEOWTH, ROCKETS_SNORLAX, KOGAS_MUK, SABRINAS_SLOWPOKE, PROFESSOR_OAK, GUST,
    COMPUTER_SEARCH, ENERGY_RETRIEVAL, POKEMON_BREEDER, POKEMON_TRADER, SCYTHER, V0_28_POKEMON, V0_29_POKEMON, STARMIE, SEAKING, STARYU, GOLDEEN,
    V0_30_POKEMON, CHARMELEON, ARCANINE, GROWLITHE,
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
        # オーキドはかせは v0.19（pool_v0_19）、突風は v0.21（pool_v0_21）、パソコン通信は v0.22（pool_v0_22）、エネルギー回収は v0.23（pool_v0_23）、ポケモン交換おじさんは v0.24（pool_v0_24）、ポケモン育て屋さんは v0.25（pool_v0_25）
        self.assertEqual(trainers, [POTION, GUST, SWITCH, BILL, ENERGY_RETRIEVAL, PROFESSOR_OAK, DEFENDER, PLUSPOWER, COMPUTER_SEARCH,
                                    POKEMON_TRADER, POKEMON_BREEDER])
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
        self.assertEqual(read_extract()["pool_v0_8"], [GRIMER, MUK])  # v0.8（常にはたらくポケモンパワーのかがくへんかガス）
        self.assertTrue(all(pool.is_playable(c) for c in (GRIMER, MUK)))
        self.assertEqual(read_extract()["pool_v0_9"], [GASTLY, HAUNTER])  # v0.9（ワザを受けるときに自動的にはたらくポケモンパワーのとうめい）
        self.assertTrue(all(pool.is_playable(c) for c in (GASTLY, HAUNTER)))
        self.assertFalse(pool.is_playable(BASE_HAUNTER))  # 同じ名前の第1弾のゴースト（参照カード。ゆめくいが未実装）
        self.assertEqual(read_extract()["pool_v0_10"], [MACHOKE, MACHAMP])  # v0.10（ダメージを受けたときに自動的にはたらくポケモンパワーのはんげき）
        self.assertTrue(all(pool.is_playable(c) for c in (MACHOP, MACHOKE, MACHAMP)))  # ワンリキーは v0.1 から
        # v0.11（相手のワザによるダメージできぜつするときに使えるポケモンパワーのこんじょう）。サカキのカイリキーは v0.10 では参照カード
        self.assertEqual(read_extract()["pool_v0_11"], [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHAMP])
        self.assertTrue(all(pool.is_playable(c) for c in (GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHAMP)))
        # v0.12（きぜつしたときに使えるポケモンパワーのふしちょう・次の相手の番にはたらく効果のワザのほのおのかべ）
        self.assertEqual(read_extract()["pool_v0_12"], [ROCKETS_MOLTRES])
        self.assertTrue(pool.is_playable(ROCKETS_MOLTRES) and pool.get(ROCKETS_MOLTRES).is_basic_pokemon)
        # v0.13（次の相手の番に受けたダメージと同じダメージを返す効果のワザのこうらがえし）。第4弾のゼニガメは第1弾のゼニガメと同じ名前
        self.assertEqual(read_extract()["pool_v0_13"], [ROCKET_SQUIRTLE, DARK_WARTORTLE])
        self.assertTrue(pool.is_playable(ROCKET_SQUIRTLE) and pool.get(ROCKET_SQUIRTLE).is_basic_pokemon)
        self.assertTrue(pool.is_playable(DARK_WARTORTLE) and pool.get(DARK_WARTORTLE).is_stage1_pokemon)
        # v0.17a（既存のワザの要素だけで実装したカード。docs/card-implementation-v0.17a.md）
        self.assertEqual(read_extract()["pool_v0_17a"], [TANGELA, GIOVANNIS_MEOWTH])
        self.assertTrue(all(pool.is_playable(c) and pool.get(c).is_basic_pokemon for c in (TANGELA, GIOVANNIS_MEOWTH)))
        # v0.17b（ねむり状態でだけはたらくポケモンパワーのわるいねぞう・自分をねむりにするワザのたおれこむ）。キョウのベトベトン（v0.17c）は参照カード
        self.assertEqual(read_extract()["pool_v0_17b"], [ROCKETS_SNORLAX])
        self.assertTrue(pool.is_playable(ROCKETS_SNORLAX) and pool.get(ROCKETS_SNORLAX).is_basic_pokemon)
        self.assertFalse(pool.is_playable(KOGAS_MUK) or pool.get(KOGAS_MUK).supported)
        # v0.18c（たおれこむと同じ実装の型で加えたナツメのヤドン。docs/kernel-reuse-v0.18c.md）
        self.assertEqual(read_extract()["pool_v0_18c"], [SABRINAS_SLOWPOKE])
        self.assertTrue(pool.is_playable(SABRINAS_SLOWPOKE) and pool.get(SABRINAS_SLOWPOKE).is_basic_pokemon)
        # v0.19（既存のトレーナーの登録・ドローの処理で加えたオーキドはかせ。docs/professor-oak-v0.19.md）
        self.assertEqual(read_extract()["pool_v0_19"], [PROFESSOR_OAK])
        self.assertTrue(pool.is_playable(PROFESSOR_OAK) and pool.get(PROFESSOR_OAK).category == "trainer")
        # v0.21（既存のトレーナーの登録・決定・ポケモンいれかえと同じ入れ替えの処理で加えた突風。docs/gust-v0.21.md）
        self.assertEqual(read_extract()["pool_v0_21"], [GUST])
        self.assertTrue(pool.is_playable(GUST) and pool.get(GUST).category == "trainer")
        # v0.22（既存のトレーナーの登録・2 段階のトレーナーの決定・ゾーンの共通の関数で加えたパソコン通信。docs/computer-search-v0.22.md）
        self.assertEqual(read_extract()["pool_v0_22"], [COMPUTER_SEARCH])
        self.assertTrue(pool.is_playable(COMPUTER_SEARCH) and pool.get(COMPUTER_SEARCH).category == "trainer")
        # v0.23（既存のトレーナーの登録・2 段階のトレーナーの決定・手札のトラッシュとトラッシュから手札に加える共通の関数で加えたエネルギー回収。
        # docs/energy-retrieval-v0.23.md）
        self.assertEqual(read_extract()["pool_v0_23"], [ENERGY_RETRIEVAL])
        self.assertTrue(pool.is_playable(ENERGY_RETRIEVAL) and pool.get(ENERGY_RETRIEVAL).category == "trainer")
        # v0.24（既存のトレーナーの登録・2 段階のトレーナーの決定・手札から山札にもどす・山札から選び出して見せる共通の関数で加えたポケモン交換
        # おじさん。docs/pokemon-trader-v0.24.md）
        self.assertEqual(read_extract()["pool_v0_24"], [POKEMON_TRADER])
        self.assertTrue(pool.is_playable(POKEMON_TRADER) and pool.get(POKEMON_TRADER).category == "trainer")
        # v0.25（既存のトレーナーの登録・2 段階のトレーナーの決定・進化の手順の共通の関数で加えたポケモン育て屋さん。docs/pokemon-breeder-v0.25.md）
        self.assertEqual(read_extract()["pool_v0_25"], [POKEMON_BREEDER])
        self.assertTrue(pool.is_playable(POKEMON_BREEDER) and pool.get(POKEMON_BREEDER).category == "trainer")
        # v0.27（次の自分の番のワザのダメージを変える持続する効果「つるぎのまい」のストライク。docs/scyther-v0.27.md）
        self.assertEqual(read_extract()["pool_v0_27"], [SCYTHER])
        self.assertTrue(pool.is_playable(SCYTHER) and pool.get(SCYTHER).is_basic_pokemon)
        # v0.28（既存の効果の型の登録だけで加えたポケモン 10 枚。docs/existing-effect-pokemon-v0.28.md）。1 進化はスターミー（ヒトデマンから）・
        # アズマオウ（トサキントから）、ほかはたねポケモン
        self.assertEqual(read_extract()["pool_v0_28"], list(V0_28_POKEMON))
        for card_id in V0_28_POKEMON:
            definition = pool.get(card_id)
            self.assertTrue(pool.is_playable(card_id), card_id)
            self.assertEqual(definition.is_basic_pokemon, card_id not in (STARMIE, SEAKING), card_id)
        self.assertEqual((pool.get(STARMIE).evolves_from, pool.get(SEAKING).evolves_from), (pool.get(STARYU).name_ja, pool.get(GOLDEEN).name_ja))
        # v0.29（既存の効果の型の登録だけで加えたポケモン 14 枚。kyuura データの採用。docs/existing-effect-pokemon-v0.29.md）。どれもたねポケモン
        self.assertEqual(read_extract()["pool_v0_29"], list(V0_29_POKEMON))
        self.assertTrue(all(pool.is_playable(c) and pool.get(c).is_basic_pokemon for c in V0_29_POKEMON))
        # v0.30（エネルギーをトラッシュしてダメージを与えるワザの共通の型。docs/discard-energy-attacks-v0.30.md）。ヒトカゲは v0.29 まで参照カード。
        # 1 進化はリザード（ヒトカゲから）・ウインディ（ガーディから）
        self.assertEqual(read_extract()["pool_v0_30"], list(V0_30_POKEMON))
        self.assertNotIn(CHARMANDER, read_extract()["reference_only"])
        for card_id in V0_30_POKEMON:
            self.assertTrue(pool.is_playable(card_id), card_id)
            self.assertEqual(pool.get(card_id).is_basic_pokemon, card_id not in (CHARMELEON, ARCANINE), card_id)
        self.assertEqual((pool.get(CHARMELEON).evolves_from, pool.get(ARCANINE).evolves_from), (pool.get(CHARMANDER).name_ja, pool.get(GROWLITHE).name_ja))
        later = (DODUO, PIKACHU, WEEDLE, CATERPIE, PARAS, VULPIX, PARASECT, DEWGONG, METAPOD, KAKUNA, BEEDRILL, BUTTERFREE,
                 BULBASAUR, IVYSAUR, VENUSAUR, SQUIRTLE, WARTORTLE, BLASTOISE, ABRA, KADABRA, ALAKAZAM, GRIMER, MUK, GASTLY, HAUNTER,
                 MACHOKE, MACHAMP, GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHAMP, ROCKETS_MOLTRES,
                 ROCKET_SQUIRTLE, DARK_WARTORTLE, TANGELA, GIOVANNIS_MEOWTH, ROCKETS_SNORLAX, SABRINAS_SLOWPOKE, SCYTHER, *V0_28_POKEMON, *V0_29_POKEMON, *V0_30_POKEMON)
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
        """v0.30 からヒトカゲの「ひのこ」は登録したので、その登録を除いた登録表で確かめる（v0.29 までは既定の登録表で未対応だった）。"""
        from kyuura_engine.cards import pool_from_extract
        from kyuura_engine.effects import DEFAULT_EFFECTS, AttackKey

        pool = pool_from_extract(read_extract(), DEFAULT_EFFECTS.without_attacks("test-no-ember", [AttackKey(CHARMANDER, 1)]))
        charmander = pool.get(CHARMANDER)
        scratch, ember = charmander.attacks
        self.assertTrue(scratch.supported)  # ひっかく: 説明文なし
        self.assertFalse(ember.supported)  # ひのこ: 炎エネルギーをトラッシュする効果
        self.assertIn("効果", ember.unsupported_reason)
        self.assertFalse(charmander.supported)
        self.assertFalse(pool.is_playable(CHARMANDER))
        self.assertTrue(load_card_pool().is_playable(CHARMANDER))  # 既定の登録表（v0.30 から）では使える

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
