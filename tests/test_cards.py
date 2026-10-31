"""カードデータの読み込みと、対応・未対応の分類。

カードデータの由来: kyuura（https://github.com/moheronemy/kyuura）commit
57d01f45cfb8b086d03dc0525b329cf6adeff69b の data/cards.json（v0.126 から。v0.125 は 134a664c6adf67d5604148a31b58e1a7d26d4d6d、v0.124 は b9e7cff6d2b2c6b4539ec45e61bf453879adab3a、v0.123 は 74b3ceb883dd815495d13b9987433fb14b36e44d、v0.121〜v0.122 は 2fe0bc042ce187d191843819262f8036abbb343d、v0.114〜v0.120 は e519b99e2adcc6c2cd0998569ae5ee1101de6e89、v0.97〜v0.113 は 73a169063463bbf7bcaa3137d70cbf9721d11534、v0.69〜v0.96 は
7d3f4ca76c084774efb4ac6a1d3a943387e183c3、v0.68 までは ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691）。
過去の原典照合は kyuura_engine/data/card_verification.json（ecb2d69 の写しと照らした履歴）。
"""

import subprocess
import unittest
from pathlib import Path

from kyuura_engine import EnergyType, can_pay_cost, load_card_pool
from kyuura_engine.cards import pool_from_extract, read_extract, read_verification
from kyuura_engine.effects import DEFAULT_EFFECTS, AttackKey

from tests.helpers import (
    V0_63_CARDS,
    V0_66_CARDS,
    V0_67_CARDS,
    V0_69_BASIC_ENERGIES,
    V0_69_POKEMON,
    V0_69_SPECIAL_ENERGIES,
    V0_69_TRAINERS,
    V0_71_TRAINERS,
    V0_73_CARDS,
    V0_74_CARDS,
    V0_75_POKEMON,
    V0_76_POKEMON,
    V0_77_POKEMON,
    V0_78_CARDS,
    V0_79_POKEMON,
    V0_77_TRAINERS,
    V0_80_CARDS,
    V0_81_CARDS,
    V0_96_TRAINERS,
    ECOGYM,
    BREEDER_COUPLE,
    FOSSIL_EGG,
    RECYCLE_ENERGY,
    V0_82_POKEMON,
    V0_83_POKEMON,
    V0_84_POKEMON,
    V0_85_POKEMON,
    V0_86_POKEMON,
    V0_87_POKEMON,
    V0_88_POKEMON,
    MIRACLE_ENERGY,
    V0_70_POKEMON,
    V0_71_POKEMON,
    V0_72_POKEMON,
    SABRINAS_PSYCHIC_CONTROL, V0_58_POKEMON, V0_58_ENERGIES, V0_59_POKEMON, V0_59_TRAINERS, V0_60_POKEMON, DIGGER, V0_61_POKEMON, V0_62_POKEMON, V0_64_POKEMON, V0_65_POKEMON, V0_68_POKEMON, KOGAS_NINJA_TRICK,
    V0_57_CARDS,
    IMPOSTER_OAK, IMPOSTER_OAKS_REVENGE, GAMBLER, SABRINAS_GAZE, BLAINES_LAST_RESORT, ERIKA, SECRET_MISSION, BLAINES_GAMBLE, LASS, POKEDEX,
    MISTYS_WRATH, ROCKETS_SNEAK_ATTACK, GOOD_MANNERS, TRASH_EXCHANGE, ENERGY_REMOVAL, SUPER_ENERGY_REMOVAL, FULL_HEAL, POKEMON_CENTER, SLEEP_TRAINER,
    ENERGY_FLOW, ERIKAS_KINDNESS, BROCK_TRAINER, GIOVANNIS_LAST_RESORT, SABRINA_TRAINER, WARP_POINT,
    ERIKAS_PERFUME, LT_SURGE_TRAINER, ROCKETS_TRAP, ROCKET_GRUNT, LT_SURGES_TREATY, MISTYS_WISH, MISTY_TRAINER, KOGA_TRAINER, INVISIBLE_WALL,
    ROCKETS_EXPERIMENT,
    MAINTENANCE, ITEM_FINDER, POKE_BALL, ENERGY_SEARCH, RECYCLE, NIGHTLY_GARBAGE_RUN, BOSS_WAY, MISTYS_TEARS, ERIKAS_MAIDS, BROCK_TRAINING, GIOVANNI, MR_FUJI, RECALL, SCOOP_UP, DEVOLUTION_SPRAY, REVIVE, POKEMON_FLUTE, BEEDRILL, BILL, CLEFAIRY_DOLL, MYSTERIOUS_FOSSIL, BUTTERFREE, CATERPIE, CHARMANDER, DEFENDER, DEWGONG, DIGLETT, DODUO, KAKUNA, METAPOD, PARAS, PARASECT, PIKACHU, PLUSPOWER, PONYTA,
    POTION, RATTATA, SUPER_POTION, SWITCH, no_super_potion_pool, ABRA, ALAKAZAM, BLASTOISE, BULBASAUR, CHARIZARD, IVYSAUR, KADABRA, SQUIRTLE, VENUSAUR, VULPIX,
    WARTORTLE, WEEDLE, GRIMER, MUK, GASTLY, HAUNTER, BASE_HAUNTER, MACHOP, MACHOKE, MACHAMP, GIOVANNIS_MACHAMP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHOP, ROCKETS_MOLTRES,
    ROCKET_SQUIRTLE, DARK_WARTORTLE, TANGELA, GIOVANNIS_MEOWTH, ROCKETS_SNORLAX, KOGAS_MUK, SABRINAS_SLOWPOKE, PROFESSOR_OAK, GUST,
    COMPUTER_SEARCH, ENERGY_RETRIEVAL, POKEMON_BREEDER, POKEMON_TRADER, SCYTHER, V0_28_POKEMON, V0_29_POKEMON, STARMIE, SEAKING, STARYU, GOLDEEN,
    V0_30_POKEMON, CHARMELEON, ARCANINE, GROWLITHE, V0_31_POKEMON, V0_31_TARGETS, V0_31_DEPENDENCIES, no_charizard_pool, V0_32_POKEMON, V0_33_POKEMON, V0_34_POKEMON, V0_34_POOL, KANGASKHAN, V0_35_POKEMON, V0_36_POKEMON,
    V0_37_POKEMON, V0_37_ADOPTED, FOSSIL_GRIMER, V0_38_POKEMON, V0_39_POKEMON, V0_40_POKEMON, V0_41_POKEMON, V0_42_POKEMON, V0_43_POKEMON, V0_44_POKEMON, V0_44_CARDS,
    V0_45_POKEMON, V0_46_POKEMON, V0_47_POKEMON, V0_48_POKEMON, V0_49_POKEMON, V0_50_POKEMON, V0_51_POKEMON, V0_52_POKEMON, no_base_haunter_pool,
)
from tests.release_catalog import cards_after

KYUURA_COMMIT = "57d01f45cfb8b086d03dc0525b329cf6adeff69b"  # v0.126 から（v0.125 は 134a664、v0.124 は b9e7cff、v0.123 は 74b3ceb、v0.121〜v0.122 は 2fe0bc0、v0.114〜v0.120 は e519b99、v0.97〜v0.113 は 73a1690、v0.69〜v0.96 は 7d3f4ca76c084774efb4ac6a1d3a943387e183c3）
# v0.68 までの写しの元。過去の原典照合の記録（card_verification.json。履歴）はこのコミットの写しと照らした
PREVIOUS_KYUURA_COMMIT = "ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691"
ROOT = Path(__file__).resolve().parent.parent


# v0.121（docs/hand-bench-attack-conditions-v0.121.md 9 章）: ボロのつりざお（neo3-053）・カスミのてあて（PR1-073）
V0_121_TRAINERS = ("neo3-053", "PR1-073")
V0_126_TRAINERS = ("ES2-035",)  # v0.126: フラッシュ（docs/flash-faceup-deck-v0.126.md）
V0_127_TRAINERS = ("neo4-108",)  # v0.127: 怪電波マシーン（docs/deferred-shortage-user-promos-v0.127.md）

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
        # オーキドはかせは v0.19（pool_v0_19）、突風は v0.21（pool_v0_21）、パソコン通信は v0.22（pool_v0_22）、エネルギー回収は v0.23（pool_v0_23）、ポケモン交換おじさんは v0.24（pool_v0_24）、ポケモン育て屋さんは v0.25（pool_v0_25）、
        # サカキは v0.44（pool_v0_44）、ピッピ人形・なにかの化石は v0.47（pool_v0_47。ポケモンとして場に出せるが、印刷の分類はトレーナーカード）、
        # 思い出させるは v0.49（pool_v0_49）、退化スプレーは v0.50（pool_v0_50）、元気のかけら・ポケモンの笛は v0.51（pool_v0_51）、フジろうじん・ポケモン回収は v0.52（pool_v0_52）、山札・トラッシュからカードを選ぶ 10 枚は v0.53（pool_v0_53）、手札の入れ替え・ドロー・情報の確認の 10 枚は v0.54（pool_v0_54）、すぐに使い終わる 16 枚（いいきずぐすりは v0.54 まで参照カード）は v0.55（pool_v0_55）、相手の決定・番の終わり・期限のある効果の 10 枚は v0.56（pool_v0_56）
        self.assertEqual(trainers, sorted(list(V0_57_CARDS) + list(V0_59_TRAINERS) + [KOGAS_NINJA_TRICK, ENERGY_REMOVAL, POTION, GUST, SWITCH, BILL, SUPER_POTION, ENERGY_RETRIEVAL, PROFESSOR_OAK, REVIVE, DEFENDER,
                                    FULL_HEAL, PLUSPOWER, POKEDEX, POKEMON_CENTER, POKEMON_FLUTE, MAINTENANCE, DEVOLUTION_SPRAY, ITEM_FINDER,
                                    SUPER_ENERGY_REMOVAL, IMPOSTER_OAK, COMPUTER_SEARCH, CLEFAIRY_DOLL, SCOOP_UP, POKEMON_TRADER, POKEMON_BREEDER,
                                    LASS, POKE_BALL, ENERGY_SEARCH, GAMBLER, MYSTERIOUS_FOSSIL, RECYCLE, MR_FUJI, SLEEP_TRAINER, NIGHTLY_GARBAGE_RUN,
                                    IMPOSTER_OAKS_REVENGE, BOSS_WAY, ROCKETS_SNEAK_ATTACK, ENERGY_FLOW, MISTYS_TEARS, RECALL, ERIKAS_MAIDS, ERIKAS_PERFUME,
                                    MISTYS_WRATH, BROCK_TRAINING, LT_SURGES_TREATY, GOOD_MANNERS, ERIKA, ERIKAS_KINDNESS, MISTY_TRAINER, MISTYS_WISH, SECRET_MISSION, BROCK_TRAINER, LT_SURGE_TRAINER, ROCKETS_TRAP, BLAINES_GAMBLE,
                                    TRASH_EXCHANGE, SABRINAS_GAZE, INVISIBLE_WALL, WARP_POINT, BLAINES_LAST_RESORT, ROCKET_GRUNT, ROCKETS_EXPERIMENT,
                                    KOGA_TRAINER, GIOVANNI, GIOVANNIS_LAST_RESORT, SABRINA_TRAINER, SABRINAS_PSYCHIC_CONTROL, DIGGER] + list(V0_63_CARDS) + list(V0_66_CARDS) + list(V0_67_CARDS)
                                   + list(V0_69_TRAINERS) + list(V0_71_TRAINERS) + list(V0_73_CARDS) + list(V0_74_CARDS) + list(V0_77_TRAINERS) + list(V0_80_CARDS) + list(V0_81_CARDS) + [ECOGYM, BREEDER_COUPLE] + list(V0_96_TRAINERS) + [FOSSIL_EGG] + list(V0_121_TRAINERS) + list(V0_126_TRAINERS) + list(V0_127_TRAINERS)))  # v0.84 でポケモン育て屋夫婦（pool_v0_84）。 v0.82 でエコロジム（pool_v0_82）。 v0.80 でトレーナー 30 枚（pool_v0_80）、v0.77 で neo1 のスーパーポケモン回収・マサキの転送装置、v0.74 で拡張パック以外の商品のスタジアム 13 枚（pool_v0_74）、v0.73 で拡張パック以外の商品の検索・回収・ドローのトレーナー 18 枚（pool_v0_73）、v0.71 で拡張パック以外の商品の再録のトレーナー 67 枚（pool_v0_71）、v0.69 で拡張パック以外の商品の同じトレーナー 19 枚（pool_v0_69）、v0.67 でマチスの秘策（pool_v0_67）、v0.57 でスタジアム 14 枚（pool_v0_57）、v0.58 でナツメのサイキックコントロール（pool_v0_58）、v0.59 でカツラ・タケシの保護・まきちらせ!ベトベトガス（pool_v0_59）、v0.61 でバトル場は穴だらけ!（pool_v0_61）、v0.63 で公開・非公開の状態を扱う 4 枚（pool_v0_63）
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
        # 同じ名前の第1弾のゴースト（v0.44 まで参照カード。ゆめくいが未実装）。v0.45 で対応にしたので、登録のないワザを持つカードが対応にならない
        # 性質は、その 2 つのワザの登録を除いた登録表で確かめる
        self.assertFalse(no_base_haunter_pool().is_playable(BASE_HAUNTER))
        self.assertTrue(pool.is_playable(BASE_HAUNTER))
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
        # v0.68 でキョウのベトベトンを対応にした（pool_v0_68。［だつりょくえき］の採用の仕様。docs/final-pmcg-cards-v0.68.md 3 章）
        self.assertTrue(pool.is_playable(KOGAS_MUK) and KOGAS_MUK in read_extract()["pool_v0_68"])
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
        # v0.31（v0.30 で保留した 22 枚と、その進化元として加えた 7 枚。docs/held-cards-v0.31.md）。リザードンは v0.30 まで参照カード。
        # どのカードも、進化元が写しにあり対戦で使える（2 進化は 1 進化を、1 進化はたねポケモンを持つ）
        self.assertEqual(read_extract()["pool_v0_31"], list(V0_31_TARGETS + V0_31_DEPENDENCIES))
        self.assertEqual(len(V0_31_TARGETS), 22)
        self.assertNotIn(CHARIZARD, read_extract()["reference_only"])
        names = {pool.get(c).name_ja: c for c in pool.playable_ids if pool.get(c).category == "pokemon"}
        for card_id in V0_31_POKEMON:
            definition = pool.get(card_id)
            self.assertTrue(pool.is_playable(card_id), card_id)
            if not definition.is_basic_pokemon:
                self.assertIn(definition.evolves_from, names, card_id)
        # v0.32（山札からベンチに出す・ダメージカウンターでダメージが決まる・与えたぶん回復するワザの 13 枚。docs/bench-search-counter-drain-v0.32.md）。
        # 進化先 5 枚は、進化元が同じ組にある
        self.assertEqual(read_extract()["pool_v0_32"], list(V0_32_POKEMON))
        for card_id in V0_32_POKEMON:
            definition = pool.get(card_id)
            self.assertTrue(pool.is_playable(card_id), card_id)
            if not definition.is_basic_pokemon:
                self.assertIn(definition.evolves_from, {pool.get(c).name_ja for c in V0_32_POKEMON}, card_id)
        # v0.33（相手のエネルギーカードをトラッシュする・コインで失敗する／ダメージを与えられない・控えにもダメージを与えるワザの 15 枚。
        # docs/cd4-opponent-energy-coins-v0.33.md）。進化先 6 枚は、進化元（名前が完全に一致するたねポケモン）が写しのどこかの組にある
        self.assertEqual(read_extract()["pool_v0_33"], list(V0_33_POKEMON))
        basics = {pool.get(c).name_ja for c in pool.playable_ids if pool.get(c).is_basic_pokemon}
        for card_id in V0_33_POKEMON:
            definition = pool.get(card_id)
            self.assertTrue(pool.is_playable(card_id), card_id)
            if not definition.is_basic_pokemon:
                self.assertIn(definition.evolves_from, basics, card_id)
        # v0.34（docs/barrier-resume-coin-bonus-v0.34.md）。写しの組は保留のガルーラを含む 15 枚で、ガルーラは v0.67 まで登録しないので対戦に使えなかった（v0.68 で対応）。
        # 進化先 7 枚は、進化元（名前が完全に一致するポケモン。ニドキングは 1 進化のニドリーノ）が写しのどこかの組にある
        self.assertEqual(read_extract()["pool_v0_34"], list(V0_34_POOL))
        self.assertTrue(pool.is_playable(KANGASKHAN))  # v0.68: 利用者が示した訂正を当てはめて対応にした
        names = {pool.get(c).name_ja for c in pool.playable_ids if pool.get(c).category == "pokemon"}
        for card_id in V0_34_POKEMON:
            definition = pool.get(card_id)
            self.assertTrue(pool.is_playable(card_id), card_id)
            if not definition.is_basic_pokemon:
                self.assertIn(definition.evolves_from, names, card_id)  # ニドキングの進化元のニドリーノは 1 進化
        # v0.35（docs/coin-groups-damage-order-v0.35.md）。進化先 2 枚（マチスのラッタ・カスミのニョロゾ）は、進化元が同じ組にある
        self.assertEqual(read_extract()["pool_v0_35"], list(V0_35_POKEMON))
        for card_id in V0_35_POKEMON:
            definition = pool.get(card_id)
            self.assertTrue(pool.is_playable(card_id), card_id)
            if not definition.is_basic_pokemon:
                self.assertIn(definition.evolves_from, {pool.get(c).name_ja for c in V0_35_POKEMON}, card_id)
        # v0.36（docs/sand-attack-retreat-lock-v0.36.md）。進化先 3 枚（サンドパン・わるいサンダース・マチスのオニドリル）は、進化元（名前が完全に
        # 一致するたねポケモン。サンド・イーブイ（v0.31）・マチスのオニスズメ（v0.33））が写しのどこかの組にある
        self.assertEqual(read_extract()["pool_v0_36"], list(V0_36_POKEMON))
        for card_id in V0_36_POKEMON:
            definition = pool.get(card_id)
            self.assertTrue(pool.is_playable(card_id), card_id)
            if not definition.is_basic_pokemon:
                self.assertIn(definition.evolves_from, names, card_id)
        # v0.37（docs/fifteen-reused-effects-v0.37.md）。写しの組は 15 枚で、化石の秘密のベトベターは v0.36 まで参照カード（reference_only）だった。
        # 進化先 5 枚（1 進化のライチュウ・ダグトリオ・ニョロゾ・ペルシアンと 2 進化のニョロボン）は、進化元（名前が完全に一致するポケモン）が
        # 写しのどこかの組にある
        self.assertEqual(read_extract()["pool_v0_37"], list(V0_37_POKEMON))
        self.assertEqual(read_extract()["pool_v0_38"], list(V0_38_POKEMON))  # v0.38（docs/bench-switch-combined-v0.38.md）
        self.assertEqual(read_extract()["pool_v0_39"], list(V0_39_POKEMON))  # v0.39（docs/selfdestruct-spread-count-v0.39.md）
        self.assertEqual(read_extract()["pool_v0_40"], list(V0_40_POKEMON))  # v0.40（docs/count-condition-switch-return-v0.40.md）
        self.assertEqual(read_extract()["pool_v0_41"], list(V0_41_POKEMON))  # v0.41（docs/heal-counter-status-v0.41.md）
        self.assertEqual(read_extract()["pool_v0_42"], list(V0_42_POKEMON))  # v0.42（docs/power-decisions-v0.42.md）
        self.assertEqual(read_extract()["pool_v0_43"], list(V0_43_POKEMON))  # v0.43（docs/declared-entry-powers-v0.43.md）
        self.assertEqual(read_extract()["pool_v0_44"], list(V0_44_CARDS))  # v0.44（ポケモン 14 枚とサカキ。docs/search-evolution-once-attacks-v0.44.md）
        self.assertEqual(read_extract()["pool_v0_45"], list(V0_45_POKEMON))  # v0.45（docs/conditional-damage-energy-v0.45.md）
        self.assertEqual(read_extract()["pool_v0_46"], list(V0_46_POKEMON))  # v0.46（docs/continuous-powers-v0.46.md）
        self.assertEqual(len(V0_37_ADOPTED), 14)
        self.assertNotIn(FOSSIL_GRIMER, read_extract()["reference_only"])
        names = {pool.get(c).name_ja for c in pool.playable_ids if pool.get(c).category == "pokemon"}
        for card_id in V0_37_POKEMON:
            definition = pool.get(card_id)
            self.assertTrue(pool.is_playable(card_id), card_id)
            if not definition.is_basic_pokemon:
                self.assertIn(definition.evolves_from, names, card_id)
        later = (DODUO, PIKACHU, WEEDLE, CATERPIE, PARAS, VULPIX, PARASECT, DEWGONG, METAPOD, KAKUNA, BEEDRILL, BUTTERFREE,
                 BULBASAUR, IVYSAUR, VENUSAUR, SQUIRTLE, WARTORTLE, BLASTOISE, ABRA, KADABRA, ALAKAZAM, GRIMER, MUK, GASTLY, HAUNTER,
                 MACHOKE, MACHAMP, GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHAMP, ROCKETS_MOLTRES,
                 ROCKET_SQUIRTLE, DARK_WARTORTLE, TANGELA, GIOVANNIS_MEOWTH, ROCKETS_SNORLAX, SABRINAS_SLOWPOKE, SCYTHER, *V0_28_POKEMON, *V0_29_POKEMON, *V0_30_POKEMON,
                 *V0_31_POKEMON, *V0_32_POKEMON, *V0_33_POKEMON, *V0_34_POKEMON, *V0_35_POKEMON, *V0_36_POKEMON, *V0_37_POKEMON, *V0_38_POKEMON,
                 *V0_39_POKEMON, *V0_40_POKEMON, *V0_41_POKEMON, *V0_42_POKEMON, *V0_43_POKEMON, *V0_44_POKEMON,
                 *V0_45_POKEMON, *V0_46_POKEMON, *V0_47_POKEMON, *V0_48_POKEMON, *V0_49_POKEMON, *V0_50_POKEMON, *V0_51_POKEMON, *V0_52_POKEMON,
                 *V0_58_POKEMON, *V0_58_ENERGIES, *V0_59_POKEMON, *V0_60_POKEMON, *V0_61_POKEMON, *V0_62_POKEMON, *V0_64_POKEMON, *V0_65_POKEMON, *V0_68_POKEMON,
                 *V0_69_POKEMON, *V0_69_SPECIAL_ENERGIES, *V0_69_BASIC_ENERGIES, *V0_70_POKEMON, *V0_71_POKEMON, *V0_72_POKEMON, *V0_75_POKEMON, *V0_76_POKEMON, *V0_77_POKEMON, *V0_78_CARDS, *V0_79_POKEMON, *V0_82_POKEMON, RECYCLE_ENERGY, *V0_83_POKEMON, *V0_84_POKEMON, *V0_85_POKEMON, MIRACLE_ENERGY, *V0_86_POKEMON, *V0_87_POKEMON, *V0_88_POKEMON, *cards_after(read_extract(), "0.88"))  # v0.89 から: その版より後の写しの組（tests/release_catalog.py）。 v0.88: ポケモン 11 枚。 v0.87: ポケモン 14 枚。 v0.86: ポケモン 13 枚。 v0.85: ポケモン 13 枚・ミラクルエネルギー。 v0.84: ポケモン 12 枚。 v0.83: ポケモン 18 枚。 v0.82: ポケモン 18 枚・リサイクルエネルギー。v0.79: ポケモン 52 枚。v0.78: 悪・鋼エネルギー 5 枚とポケモン 8 枚。v0.77: neo 期の拡張パックのポケモン 50 枚。v0.76: 拡張パック以外の商品のポケモン 24 枚。v0.75: 拡張パック以外の商品のポケモン 15 枚。v0.72: 拡張パック以外の商品のポケモン 43 枚。v0.71: 拡張パック以外の商品の再録のポケモン 11 枚。v0.70: 拡張パック以外の商品のポケモン 82 枚。v0.69: 拡張パック以外の商品の同じカード（ポケモン 57・特殊エネルギー 8・基本エネルギー 12）。v0.68: ガルーラ・キョウのベトベトン・イマクニ？のドードー。v0.58: タケシのゴローン・ゴローニャと特殊エネルギー 4 枚。v0.59: マルマイン・カスミのメノクラゲ・わるいアーボック。v0.60: 4 枚。v0.61: 3 枚。v0.62: 6 枚。v0.64: 3 枚
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
        # v0.2b できずぐすりを対応にしたので、実装を登録していないトレーナー（いいきずぐすり）で確かめる。v0.55 でいいきずぐすりを対応にしたので、
        # その登録だけを除いた登録表で分類した組で確かめる（製品の登録表では対応）
        self.assertIn("トレーナー", no_super_potion_pool().get(SUPER_POTION).unsupported_reasons[0])
        self.assertTrue(pool.get(SUPER_POTION).supported)
        # v0.4c で 2 進化の段階を扱えるようにしたので、2 進化のカードは段階ではなく、ポケモンパワーと登録のないワザで未対応に
        # なる（v0.4b までは理由の最初が「stage2（2 進化・ベイビィ）は未実装」だった）。v0.4e まではフシギバナ（ポケモンパワー・
        # ソーラービーム）、v0.5 ではカメックス（登録のないポケモンパワー「あまごい」・ワザ「ハイドロポンプ」）で確かめていた。
        # v0.6 ではフーディン（登録のないポケモンパワー「ダメージスワップ」・ワザ「あやしいひかり」）で確かめていた。v0.7 で
        # フーディンを対応にしたので、リザードン（登録のないポケモンパワー「エナジーバーン」・ワザ「ほのおのうず」）で確かめる。v0.31 でリザードンを
        # 対応にしたので、その 2 つの登録だけを除いた登録表で分類したカードの組で確かめる（tests/helpers.py の no_charizard_pool）
        self.assertTrue(pool.get(CHARIZARD).supported)
        reasons = " ".join(no_charizard_pool().get(CHARIZARD).unsupported_reasons)
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
        # v0.69: 照合の記録は履歴で書き換えない（ecb2d69 の写しと照らした）。写しの元は 7d3f4ca で、写しの作り直しの検査（previous_copy_problems）が、
        # ecb2d69 にあったカードの写す欄が kyuura の修正の欄と出典の記録の欄を除いて同じことを確かめる
        self.assertEqual(verification["kyuura_commit"], PREVIOUS_KYUURA_COMMIT)
        # v0.97: 修正ごとの前の写しの元は、kyuura が当てはめた移行の段の前（v0.69 の段は ecb2d69、v0.97 の段（アンノーンI・D・F のルール文）は 7d3f4ca）。
        # v0.114: ベイビィ 13 枚のルール文・進化先（kyuura が画像で埋めた。v0.114 の段）は 73a1690（docs/baby-rules-evolution-v0.114.md 4.1 節）
        # v0.121: ボロのつりざおの効果文（kyuura が画像で直した。v0.121 の段）は e519b99（docs/hand-bench-attack-conditions-v0.121.md 3 章）
        # v0.123: ウィンディ 2 枚の名前（kyuura が画像で直した生成の値の誤り。v0.123 の段）は 2fe0bc0（docs/arcanine-name-migration-v0.123.md 2 章）
        # v0.124: 写しの外のメタモン ES2-032 の文面の 1 字（kyuura が画像で直した転記の誤り。v0.124 の段）は 74b3ceb（docs/super-transform-dark-pulse-v0.124.md 2 章）
        # v0.125: 段 v0.125（b9e7cff → 134a664）に訂正はない（docs/wigglytuff-helping-hand-v0.125.md 2 章）
        # v0.126: 写しの外のとりかえっこプリーズ PR1-027 の文面の読点 1 つ（kyuura が画像で直した転記の誤り。v0.126 の段）は 134a664（docs/flash-faceup-deck-v0.126.md 2 章）
        self.assertEqual({(c["migration"], c["previous_source"]) for c in extract["kyuura_corrections"]},
                         {("v0.69", PREVIOUS_KYUURA_COMMIT), ("v0.97", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3"),
                          ("v0.114", "73a169063463bbf7bcaa3137d70cbf9721d11534"), ("v0.121", "e519b99e2adcc6c2cd0998569ae5ee1101de6e89"),
                          ("v0.123", "2fe0bc042ce187d191843819262f8036abbb343d"), ("v0.124", "74b3ceb883dd815495d13b9987433fb14b36e44d"),
                          ("v0.126", "134a664c6adf67d5604148a31b58e1a7d26d4d6d")})
        self.assertEqual(extract["source"]["commit"], KYUURA_COMMIT)
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
