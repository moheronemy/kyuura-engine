"""効果の登録表（v0.2a、M5）。

ワザを使えるのは、効果の登録表に（カード id, ワザの位置）で実装が登録されているときだけ。
説明文が空であることは実装がある証拠にならない。説明文があっても、実装が登録されていれば使える。
"""

import copy
import pickle
import unittest

from kyuura_engine import (
    DeckValidationError, UnsupportedError, UseAttack, apply_command, deck_problems, expand_decklist, load_card_pool,
    new_game, state_to_dict,
)
from kyuura_engine.cards import pool_from_extract, read_extract
from kyuura_engine.effects import DAMAGE_ONLY, DEFAULT_EFFECTS, EQUIVALENT_CARDS, REPRINT_CARDS, AttackEffect, AttackEntry, AttackKey, PowerKey

from tests.helpers import (
    CHARMANDER, DIGLETT, FIGHTING, FIRE, FIRE_DECK, GROWLITHE, MACHOP, NO_EMBER_EFFECTS, PONYTA, VENUSAUR, WATER_FIGHTING_DECK,
    active, build_test_state,
)


# v0.31 で加えた説明文のあるワザ（45）。docs/held-cards-v0.31.md
V0_31_WITH_TEXT = [
    AttackKey("PMCG1-021", 0), AttackKey("PMCG1-022", 0), AttackKey("PMCG1-022", 1), AttackKey("PMCG1-042", 0), AttackKey("PMCG1-042", 1),
    AttackKey("PMCG1-044", 0), AttackKey("PMCG1-044", 1), AttackKey("PMCG1-050", 0), AttackKey("PMCG1-050", 1), AttackKey("PMCG1-067", 0),
    AttackKey("PMCG1-067", 1), AttackKey("PMCG2-037", 0), AttackKey("PMCG2-037", 1), AttackKey("PMCG2-044", 0), AttackKey("PMCG2-044", 1),
    AttackKey("PMCG3-009", 0), AttackKey("PMCG3-009", 1), AttackKey("PMCG3-027", 0), AttackKey("PMCG3-027", 1), AttackKey("PMCG4-014", 1),
    AttackKey("PMCG4-015", 1), AttackKey("PMCG4-016", 0), AttackKey("PMCG4-016", 1), AttackKey("PMCG4-017", 1), AttackKey("PMCG4-019", 0),
    AttackKey("PMCG4-019", 1), AttackKey("PMCG4-022", 0), AttackKey("PMCG4-028", 1), AttackKey("PMCG5-021", 0), AttackKey("PMCG5-032", 0),
    AttackKey("PMCG5-032", 1), AttackKey("PMCG5-036", 0), AttackKey("PMCG5-041", 0), AttackKey("PMCG5-041", 1), AttackKey("PMCG6-025", 0),
    AttackKey("PMCG6-026", 0), AttackKey("PMCG6-027", 0), AttackKey("PMCG6-029", 1), AttackKey("PMCG6-031", 0), AttackKey("PMCG6-031", 1),
    AttackKey("PMCG6-033", 0), AttackKey("PMCG6-034", 0), AttackKey("PMCG6-034", 1), AttackKey("PMCG6-041", 0), AttackKey("PMCG6-041", 1),
]
# v0.32 で加えた説明文のあるワザ（19）。docs/bench-search-counter-drain-v0.32.md
V0_32_WITH_TEXT = [
    AttackKey("PMCG1-031", 1), AttackKey("PMCG1-034", 1), AttackKey("PMCG1-048", 0), AttackKey("PMCG1-048", 1), AttackKey("PMCG2-001", 0),
    AttackKey("PMCG2-001", 1), AttackKey("PMCG2-002", 0), AttackKey("PMCG2-002", 1), AttackKey("PMCG2-004", 0), AttackKey("PMCG2-004", 1),
    AttackKey("PMCG2-005", 1), AttackKey("PMCG2-008", 0), AttackKey("PMCG2-008", 1), AttackKey("PMCG2-011", 0), AttackKey("PMCG3-002", 0),
    AttackKey("PMCG3-002", 1), AttackKey("PMCG3-005", 1), AttackKey("PMCG3-013", 0), AttackKey("PMCG3-019", 0),
]
# v0.33 で加えた説明文のあるワザ（25）。docs/cd4-opponent-energy-coins-v0.33.md
V0_33_WITH_TEXT = [
    AttackKey("PMCG1-005", 0), AttackKey("PMCG1-010", 0), AttackKey("PMCG1-069", 0), AttackKey("PMCG1-069", 1), AttackKey("PMCG3-016", 0),
    AttackKey("PMCG3-016", 1), AttackKey("PMCG3-018", 0), AttackKey("PMCG3-018", 1), AttackKey("PMCG4-023", 1), AttackKey("PMCG4-046", 1),
    AttackKey("PMCG5-039", 0), AttackKey("PMCG5-039", 1), AttackKey("PMCG5-044", 0), AttackKey("PMCG5-044", 1), AttackKey("PMCG5-049", 0),
    AttackKey("PMCG5-057", 0), AttackKey("PMCG5-057", 1), AttackKey("PMCG6-003", 0), AttackKey("PMCG6-003", 1), AttackKey("PMCG6-006", 0),
    AttackKey("PMCG6-006", 1), AttackKey("PMCG6-058", 0), AttackKey("PMCG6-058", 1), AttackKey("PMCG6-064", 0), AttackKey("PMCG6-064", 1),
]
# v0.34 で加えた説明文のあるワザ（26。タケシのロコンの「ほのお」は説明文なし）。docs/barrier-resume-coin-bonus-v0.34.md
V0_34_WITH_TEXT = [AttackKey(card, index) for card in ("PMCG2-019", "PMCG2-020", "PMCG2-023", "PMCG2-026", "PMCG1-041", "PMCG2-042", "PMCG6-024",
                                                       "PMCG6-069", "PMCG1-013", "PMCG2-012", "PMCG2-029", "PMCG2-032") for index in (0, 1)] + [
    AttackKey("PMCG5-018", 1), AttackKey("PMCG1-006", 0)]
# v0.35 で加えた説明文のあるワザ（10。5 枚の 2 つずつ。どれも説明文あり）。docs/coin-groups-damage-order-v0.35.md
V0_35_WITH_TEXT = [AttackKey(card, index) for card in ("PMCG5-056", "PMCG5-059", "PMCG5-022", "PMCG5-029", "PMCG6-065") for index in (0, 1)]
# v0.36 で加えた説明文のあるワザ（16。サンドパンの「きりさく」・カスミのタッツーの「たいあたり」・キョウのポッポの「つつく」は説明文なし）。
# docs/sand-attack-retreat-lock-v0.36.md
V0_36_WITH_TEXT = [AttackKey(card, index) for card in ("PMCG3-008", "PMCG4-029", "PMCG5-023", "PMCG5-064", "PMCG6-015") for index in (0, 1)] + [
    AttackKey("PMCG1-051", 0), AttackKey("PMCG3-036", 1), AttackKey("PMCG3-014", 0), AttackKey("PMCG5-025", 1), AttackKey("PMCG6-062", 1),
    AttackKey("PMCG5-005", 0)]
# v0.37 で加えた説明文のあるワザ（21。つのでつく・たいあたり・ずつき・きりさく・いわおとし・はねる・ひっかくは説明文なし）。
# docs/fifteen-reused-effects-v0.37.md
V0_37_WITH_TEXT = [AttackKey(card, index) for card in ("PMCG3-003", "PMCG1-038", "PMCG1-028", "PMCG1-033", "PMCG3-001", "PMCG6-009")
                   for index in (0, 1)] + [
    AttackKey("PMCG2-030", 0), AttackKey("PMCG4-049", 1), AttackKey("PMCG5-043", 0), AttackKey("PMCG6-045", 0), AttackKey("PMCG1-056", 1),
    AttackKey("PMCG5-048", 0), AttackKey("PMCG2-036", 0), AttackKey("PMCG5-028", 0), AttackKey("PMCG2-039", 1)]
# v0.38: 控えへのダメージ・入れ替え・同じコインの複数の効果・軽減・山札にもどる効果の 15 枚（docs/bench-switch-combined-v0.38.md）の説明文のあるワザ 21
V0_38_WITH_TEXT = [AttackKey(card, index) for card in ("PMCG3-023", "PMCG5-017", "PMCG3-004", "PMCG6-070", "PMCG6-012", "PMCG4-031") for index in (0, 1)] + [
    AttackKey("PMCG3-039", 0), AttackKey("PMCG5-006", 1), AttackKey("PMCG5-008", 1), AttackKey("PMCG2-033", 1), AttackKey("PMCG6-028", 0),
    AttackKey("PMCG6-030", 1), AttackKey("PMCG6-001", 1), AttackKey("PMCG6-066", 1), AttackKey("PMCG6-067", 0)]
# v0.39: じばく・控えへのダメージ・場のポケモンの数でダメージが決まるワザの 15 枚（docs/selfdestruct-spread-count-v0.39.md）の説明文のあるワザ 21
V0_39_WITH_TEXT = [AttackKey(card, index) for card in ("PMCG1-036", "PMCG1-039", "PMCG3-006", "PMCG3-025", "PMCG6-016") for index in (0, 1)] + [
    AttackKey("PMCG2-024", 0), AttackKey("PMCG3-024", 0), AttackKey("PMCG2-025", 1), AttackKey("PMCG6-008", 0), AttackKey("PMCG6-039", 0),
    AttackKey("PMCG4-026", 1), AttackKey("PMCG2-045", 0), AttackKey("PMCG2-045", 1), AttackKey("PMCG2-013", 0), AttackKey("PMCG1-059", 0),
    AttackKey("PMCG5-004", 1)]
# v0.40: 場の数・条件付きの効果・入れ替え・カードの移動の 15 枚（docs/count-condition-switch-return-v0.40.md）の説明文のあるワザ 22
V0_40_WITH_TEXT = [AttackKey(card, index) for card in ("PMCG4-011", "PMCG6-004", "PMCG6-021", "PMCG4-042", "PMCG5-045", "PMCG4-039", "PMCG2-031")
                   for index in (0, 1)] + [
    AttackKey("PMCG6-005", 0), AttackKey("PMCG6-014", 1), AttackKey("PMCG4-037", 1), AttackKey("PMCG6-013", 0), AttackKey("PMCG6-020", 1),
    AttackKey("PMCG4-044", 1), AttackKey("PMCG5-011", 1), AttackKey("PMCG5-034", 1)]
# v0.41: 回復・カウンターの移動・特殊状態の変化を中心とする 15 枚（docs/heal-counter-status-v0.41.md）の説明文のあるワザ 26
V0_41_WITH_TEXT = [AttackKey(card, index) for card in ("PMCG2-009", "PMCG2-016", "PMCG3-020", "PMCG4-048", "PMCG5-002", "PMCG5-009", "PMCG6-038",
                                                       "PMCG6-022", "PMCG6-048", "PMCG5-058", "PMCG6-055") for index in (0, 1)] + [
    AttackKey("PMCG6-035", 0), AttackKey("PMCG4-032", 0), AttackKey("PMCG5-003", 0), AttackKey("PMCG6-036", 1)]
# v0.42: 回復・カウンター操作と、特殊能力を持つ進化系統を中心とする 15 枚（docs/power-decisions-v0.42.md）の説明文のあるワザ 16
V0_42_WITH_TEXT = [AttackKey(card, index) for card in ("PMCG6-052", "PMCG4-035", "PMCG3-017") for index in (0, 1)] + [
    AttackKey(card, 0) for card in ("PMCG2-014", "PMCG3-028", "PMCG3-031", "PMCG5-014", "PMCG6-043", "PMCG6-047", "PMCG3-043", "PMCG4-034",
                                    "PMCG5-060", "PMCG5-065")]
# v0.43: 宣言して使う特殊能力・場に出たときに使う特殊能力を持つ 9 枚（docs/declared-entry-powers-v0.43.md）の説明文のあるワザ 8（ロケット団のヒトカゲの
# 「ほのおのしっぽ」は説明文なし）
V0_43_WITH_TEXT = [AttackKey(card, 0) for card in ("PMCG4-006", "PMCG4-033", "PMCG5-010", "PMCG5-040", "PMCG4-052", "PMCG4-009", "PMCG4-036",
                                                   "PMCG4-053")]
# v0.44: 検索・進化・1 度だけ使えるワザの 14 枚（docs/search-evolution-once-attacks-v0.44.md）の説明文のあるワザ 20（ディグダの「ひっかく」・コイキングの
# 「はねまわる」・カモネギの「ナベでたたく」・ナツメのバリヤードの「ビンタ」は説明文なし）
V0_44_WITH_TEXT = [AttackKey(card, index) for card, index in (
    ("PMCG4-038", 0), ("PMCG4-047", 0), ("PMCG5-007", 0), ("PMCG5-007", 1), ("PMCG5-027", 0), ("PMCG4-020", 1), ("PMCG6-011", 0), ("PMCG6-018", 0),
    ("PMCG6-018", 1), ("PMCG1-063", 0), ("PMCG6-037", 0), ("PMCG6-037", 1), ("PMCG6-040", 0), ("PMCG6-040", 1), ("PMCG6-046", 0), ("PMCG6-056", 0),
    ("PMCG6-056", 1), ("PMCG6-075", 0), ("PMCG6-075", 1), ("PMCG6-071", 0))]
# v0.45（docs/conditional-damage-energy-v0.45.md）: 15 枚の説明文のあるワザ 24。第1弾のゴーストの 2 つは v0.9 の過去の原典照合の記録の最新の説明（p.160）、
# R団のエビワラーの「クロスカウンター」は kyuura の最新の説明（LD-PMCG5-054-ATK0）、ほかは採用の記録の play_text（kyuura の印刷の文面）と合う
# （キョウのベトベターの「ヘドロなげ」・イワークの「いわおとし」・ラッタの「かみつく」・R団のエビワラーの「マグナムパンチ」は説明文なし）
V0_45_WITH_TEXT = [AttackKey(card, index) for card, index in (
    ("PMCG1-047", 0), ("PMCG1-047", 1), ("PMCG5-024", 0), ("PMCG5-031", 0), ("PMCG5-031", 1), ("PMCG6-002", 0), ("PMCG6-019", 0), ("PMCG6-019", 1),
    ("PMCG6-007", 0), ("PMCG4-024", 0), ("PMCG4-024", 1), ("PMCG4-030", 0), ("PMCG4-030", 1), ("PMCG6-032", 0), ("PMCG6-032", 1), ("PMCG6-042", 0),
    ("PMCG6-042", 1), ("PMCG1-054", 1), ("PMCG1-062", 1), ("PMCG5-054", 0), ("PMCG5-047", 0), ("PMCG5-047", 1), ("PMCG6-068", 0), ("PMCG6-068", 1))]
# v0.46: 常にはたらく特殊能力を持つ 8 枚と関連する 3 枚の説明文のあるワザ（どれも。kyuura データの採用。処理に使う文面は kyuura の印刷の文面。
# docs/continuous-powers-v0.46.md）
V0_46_WITH_TEXT = [AttackKey(card, index) for card, index in (
    ("PMCG2-027", 0), ("PMCG5-063", 0), ("PMCG6-010", 0), ("PMCG4-041", 0), ("PMCG2-040", 0), ("PMCG4-007", 0), ("PMCG4-010", 0), ("PMCG2-047", 0),
    ("PMCG6-017", 0), ("PMCG6-017", 1), ("PMCG5-012", 0), ("PMCG5-012", 1), ("PMCG5-013", 0), ("PMCG5-013", 1))]
# v0.47（docs/fossil-hidden-info-v0.47.md）: ポケモン 11 枚の説明文のあるワザ 12（ひっかく・するどいかま・つばさでうつは説明文なし。処理に使う文面は kyuura の印刷の文面）
V0_47_WITH_TEXT = [AttackKey(card, index) for card, index in (
    ("PMCG3-015", 0), ("PMCG3-021", 0), ("PMCG3-021", 1), ("PMCG3-040", 1), ("PMCG4-045", 0), ("PMCG3-032", 0), ("PMCG3-032", 1),
    ("PMCG5-062", 0), ("PMCG5-042", 0), ("PMCG5-042", 1), ("PMCG3-010", 0), ("PMCG3-010", 1))]
# v0.48（docs/effective-pokemon-properties-v0.48.md）。説明文のあるワザ 10（ナツメのゴースの「ガスでつつむ」は説明文なし）。処理に使う文面は kyuura の印刷の文面
V0_48_WITH_TEXT = [AttackKey(card, index) for card, index in (
    ("PMCG1-064", 0), ("PMCG1-064", 1), ("PMCG4-050", 0), ("PMCG4-050", 1), ("PMCG2-015", 0), ("PMCG6-050", 0), ("PMCG6-054", 0), ("PMCG6-054", 1),
    ("PMCG6-072", 0), ("PMCG6-072", 1))]
# v0.49（docs/virtual-attacks-transformation-v0.49.md）。説明文のあるワザはナツメのフーディンの「メガバーン」1 つ（タケシのキュウコンの「おにび」は説明文なし。
# メタモンはワザなし）。処理に使う文面は kyuura の印刷の文面
V0_49_WITH_TEXT = [AttackKey("PMCG6-053", 0)]
# v0.50（docs/mew-devolution-spray-v0.50.md）。ミュウの「サイコウェーブ」・「たいかビーム」。処理に使う文面は kyuura の印刷の文面
V0_50_WITH_TEXT = [AttackKey("PMCG3-033", 0), AttackKey("PMCG3-033", 1)]
# v0.51（docs/discard-to-bench-v0.51.md）。ナツメのスリーパーの「よみがえらせる」・「ふりこののろい」。処理に使う文面は kyuura の印刷の文面
V0_51_WITH_TEXT = [AttackKey("PMCG6-051", 0), AttackKey("PMCG6-051", 1)]
V0_52_WITH_TEXT = [AttackKey("PMCG5-066", 0), AttackKey("PMCG5-066", 1)]  # v0.52: エリカのハクリューのふぶき・つれさる
V0_58_WITH_TEXT = [AttackKey("PMCG5-052", 1), AttackKey("PMCG5-053", 0)]  # v0.58: タケシのゴローンのばくれつ・タケシのゴローニャのいわなだれ
# v0.59: マルマイン（第1弾）のでんげき・カスミのメノクラゲのクリスタルビーム・わるいアーボックのショックアイ・どくのきり（kyuura の印刷の文面）
V0_59_WITH_TEXT = [AttackKey("PMCG1-040", 0), AttackKey("PMCG5-030", 0), AttackKey("PMCG4-008", 0), AttackKey("PMCG4-008", 1)]
# v0.60: サンダー（化石の秘密）のサンダーストーム・R団のストライクのかげぶんしん・タケシのサンドパンのスピードスター・とげボール（kyuura の印刷の文面）
V0_60_WITH_TEXT = [AttackKey("PMCG3-026", 0), AttackKey("PMCG5-016", 0), AttackKey("PMCG5-050", 0), AttackKey("PMCG5-050", 1)]
# v0.61（docs/reactive-powers-trainer-damage-v0.61.md）: わるいギャラドスの「れいとうビーム」・わるいダグトリオの「つきおとす」・タケシのオコリザルの「おおあばれ」
V0_61_WITH_TEXT = [AttackKey("PMCG4-025", 0), AttackKey("PMCG4-043", 0), AttackKey("PMCG5-051", 0)]
# v0.62（docs/history-attacks-v0.62.md）: ピジョンのふきとばし・オウムがえし・オニスズメのオウムがえし・オニドリルのこうそくいどう・ピジョットのハリケーン・
# タケシのダグトリオのあながくれ・ドリルホール・ベロリンガのまきつくベロ・ちょうおんぱ（説明文のないワザはつつく・ドリルくちばし・つばさでうつ）
V0_62_WITH_TEXT = [AttackKey("PMCG1-066", 0), AttackKey("PMCG1-066", 1), AttackKey("PMCG2-034", 1), AttackKey("PMCG2-038", 0), AttackKey("PMCG2-043", 1),
                   AttackKey("PMCG6-060", 0), AttackKey("PMCG6-060", 1), AttackKey("PMCG2-041", 0), AttackKey("PMCG2-041", 1)]
# v0.64: れんぞくいしなげ・かたくなる・じばく（kyuura の印刷の文面。docs/geodude-line-unbounded-coins-v0.64.md）
V0_64_WITH_TEXT = [AttackKey("PMCG3-034", 0), AttackKey("PMCG3-037", 0), AttackKey("PMCG3-038", 1)]
# v0.65: クラゲどく・ラリアット（kyuura の印刷の文面。docs/reactive-decisions-v0.65.md）
V0_65_WITH_TEXT = [AttackKey("PMCG5-033", 0), AttackKey("PMCG5-055", 0)]
# v0.68: ガルーラのこどものおつかい（利用者が示した訂正の文面）・れんぞくパンチ、イマクニ？のドードーのハモる（簡略化した仕様。キョウのベトベトンのヘドロのうずは説明文なし）
V0_68_WITH_TEXT = [AttackKey("PMCG2-046", 0), AttackKey("PMCG2-046", 1), AttackKey("PMCG6-074", 0)]
# v0.70: 拡張パック以外の商品のポケモン 82 枚の、説明文のあるワザ 85（写しの説明文で数える。処理に使う文面は kyuura の印刷の文面）
V0_70_WITH_TEXT = [AttackKey(c["id"], i) for c in read_extract()["cards"] if c["id"] in read_extract()["pool_v0_70"]
                   for i, a in enumerate(c["pokemon"]["attacks"]) if a["text"]["ja"] is not None]
# v0.72: 拡張パック以外の商品のポケモン 43 枚の、説明文のあるワザ 67（写しの説明文で数える。処理に使う文面は kyuura の印刷の文面）
V0_72_WITH_TEXT = [AttackKey(c["id"], i) for c in read_extract()["cards"] if c["id"] in read_extract()["pool_v0_72"]
                   for i, a in enumerate(c["pokemon"]["attacks"]) if a["text"]["ja"] is not None]
# v0.75（docs/search-energy-pokemon-v0.75.md）: 拡張パック以外の商品のポケモン 15 枚の説明文のあるワザ（24。処理に使う文面は kyuura の印刷の文面）
V0_75_WITH_TEXT = [AttackKey(c["id"], i) for c in read_extract()["cards"] if c["id"] in read_extract()["pool_v0_75"]
                   for i, a in enumerate(c["pokemon"]["attacks"]) if a["text"]["ja"] is not None]
# v0.76（docs/persistent-attack-modifiers-v0.76.md）: 拡張パック以外の商品のポケモン 24 枚の説明文のあるワザ（処理に使う文面は kyuura の印刷の文面）
V0_76_WITH_TEXT = [AttackKey(c["id"], i) for c in read_extract()["cards"] if c["id"] in read_extract()["pool_v0_76"]
                   for i, a in enumerate(c["pokemon"]["attacks"]) if a["text"]["ja"] is not None]
# v0.77（docs/neo-existing-effects-v0.77.md）: neo 期の拡張パックのポケモン 50 枚の説明文のあるワザ（50。処理に使う文面は kyuura の印刷の文面）
V0_77_WITH_TEXT = [AttackKey(c["id"], i) for c in read_extract()["cards"] if c["id"] in read_extract()["pool_v0_77"] and c["category"] == "pokemon"
                   for i, a in enumerate(c["pokemon"]["attacks"]) if a["text"]["ja"] is not None]
# v0.78: 「悪」「鋼」エネルギーを使うポケモン 8 枚の説明文のあるワザ 12（kyuura の印刷の文面）
V0_78_WITH_TEXT = [AttackKey(c["id"], i) for c in read_extract()["cards"] if c["id"] in read_extract()["pool_v0_78"] and c["category"] == "pokemon"
                   for i, a in enumerate(c["pokemon"]["attacks"]) if a["text"]["ja"] is not None]
# v0.79: ポケモン 52 枚の説明文のあるワザ 83（kyuura の印刷の文面）
V0_79_WITH_TEXT = [AttackKey(c["id"], i) for c in read_extract()["cards"] if c["id"] in read_extract()["pool_v0_79"] and c["category"] == "pokemon"
                   for i, a in enumerate(c["pokemon"]["attacks"]) if a["text"]["ja"] is not None]
# v0.82: ポケモン 18 枚の説明文のあるワザ 27（kyuura の印刷の文面。docs/energy-discard-return-v0.82.md）
V0_82_WITH_TEXT = [AttackKey(c["id"], i) for c in read_extract()["cards"] if c["id"] in read_extract()["pool_v0_82"] and c["category"] == "pokemon"
                   for i, a in enumerate(c["pokemon"]["attacks"]) if a["text"]["ja"] is not None]
# v0.83: ポケモン 18 枚の説明文のあるワザ 32（kyuura の印刷の文面。docs/shining-gentle-pokemon-v0.83.md）
V0_83_WITH_TEXT = [AttackKey(c["id"], i) for c in read_extract()["cards"] if c["id"] in read_extract()["pool_v0_83"] and c["category"] == "pokemon"
                   for i, a in enumerate(c["pokemon"]["attacks"]) if a["text"]["ja"] is not None]



class RecordingEffect(AttackEffect):
    """テスト専用の実装: ダメージを与えず、呼ばれたことをログに残すだけ（製品のコードには登録しない）。"""

    implementation_id = "test_recording"

    def resolve(self, state, use):
        state.add_event("test_effect", player=use.player, pokemon_id=use.pokemon_id, key=str(use.key))


RECORDING = RecordingEffect()


def extract_with_other_diglett():
    """ディグダの記録を、別のカード id の別のカードとして加えた写し（同じ名前のワザを持つ別のカード）。"""
    extract = copy.deepcopy(read_extract())
    other = copy.deepcopy(next(c for c in extract["cards"] if c["id"] == DIGLETT))
    other["id"] = "TEST-OTHER-DIGLETT"
    extract["cards"].append(other)
    extract["pool_v0_1"].append(other["id"])
    return extract


class DefaultRegistryTest(unittest.TestCase):
    def test_every_v0_1_attack_is_registered_explicitly_as_damage_only(self):
        # v0.2d でコインを投げるワザのドードー（pool_v0_2d）が対戦に使えるようになったので、v0.1 の組で確かめる
        # （ドードーは tests/test_coin_attacks.py）
        pool = load_card_pool()
        for card_id in sorted(set(pool.playable_ids) & set(read_extract()["pool_v0_1"])):
            for attack in pool.get(card_id).attacks:
                entry = DEFAULT_EFFECTS.attack_entry(card_id, attack.index)
                self.assertIsNotNone(entry, (card_id, attack.index))
                self.assertIs(entry.effect, DAMAGE_ONLY)
                self.assertEqual(entry.name_ja, attack.name_ja)
                self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card_id, attack))

    def test_every_registered_key_matches_the_card_data(self):
        """登録表のどの登録も、写しのカードのワザを指していて、データと合う（位置のずれがない）。"""
        pool = load_card_pool()
        for key in DEFAULT_EFFECTS.attack_keys():
            attack = pool.get(key.card_id).attacks[key.attack_index]
            self.assertIsNone(DEFAULT_EFFECTS.attack_problem(key.card_id, attack), key)

    def test_every_registration_is_backed_by_a_verification_record(self):
        """登録したワザのカードは、登録の根拠の記録をちょうど 1 つ持つ: 『オフィシャルブック2000』と照合した記録（card_verification.json。
        2026-10-14 までに登録したカード。履歴）か、kyuura データの採用の記録（card_sources.json の adopted。2026-10-15 からの方針。
        docs/card-data-policy.md。採用の記録の中身は scripts/check_card_sources.py と tests/test_card_sources.py が確かめる）。"""
        from kyuura_engine.cards import read_verification
        from scripts import check_card_sources as card_sources

        verification = read_verification()
        sources = card_sources.load_sources()
        for key in DEFAULT_EFFECTS.attack_keys():
            basis = card_sources.registration_basis(key.card_id, verification, sources)
            self.assertIn(basis, (card_sources.GUIDEBOOK_RECORD, card_sources.KYUURA_DATA), key)
            if basis == card_sources.GUIDEBOOK_RECORD:
                self.assertIn(verification["cards"][key.card_id]["status"], ("一致", "不一致あり"), key)

    def test_attacks_with_text_follow_the_verified_latest_description(self):
        """説明文のあるワザの登録（v0.2d から）は、照合した説明文・最新の説明・出典を持ち、照合の記録と合う。

        説明文のないワザ（DamageOnly）の登録は、どれも None のまま。kyuura データの採用の記録（2026-10-15 からの方針）で登録したワザは、
        採用の記録の play_text（根拠が kyuura の印刷の文面か kyuura の記録の id）と合うことを scripts/check_card_sources.py が確かめる
        （ガイドブックのページを求めない）。
        """
        from kyuura_engine.cards import read_verification
        from scripts import check_card_sources as card_sources

        records = read_verification()["cards"]
        sources = card_sources.load_sources()["cards"]
        pool = load_card_pool()
        with_text = []
        for key in DEFAULT_EFFECTS.attack_keys():
            entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
            attack = pool.get(key.card_id).attacks[key.attack_index]
            self.assertEqual(entry.text_ja, attack.text_ja, key)
            if attack.text_ja is None:
                self.assertEqual((entry.play_text_ja, entry.source), (None, None), key)
                continue
            with_text.append(key)
            if key.card_id not in records:
                self.assertIn(f"attack/{key.attack_index}", sources[key.card_id]["play_text"], key)
                continue
            record = records[key.card_id]
            latest = record.get("latest_description_ja")
            if isinstance(latest, dict):  # 説明文のあるワザが 2 つあるカード（v0.4b）は、ワザの位置ごと
                latest = latest.get(str(key.attack_index))
            if latest is None:
                # v0.30: 過去の原典照合の記録はあるが、その記録に処理に使う文面のないワザ（照合したあとで登録したヒトカゲの「ひのこ」）は、
                # card_sources.json の basis: guidebook_record の play_text に根拠を書く（照合の記録は書き換えない）
                self.assertEqual(sources[key.card_id]["basis"], "guidebook_record", key)
                self.assertIn(f"attack/{key.attack_index}", sources[key.card_id]["play_text"], key)
                continue
            self.assertEqual(entry.play_text_ja, latest, key)
            self.assertEqual(entry.source, f"P43 p.{record['page']}", key)
            self.assertEqual(record["pdf_page"], record["page"] + 2)
        # ピカチュウの「でんげき」（p.125。v0.2f）、ドードーの「みだれづき」（p.231。v0.2d）
        # ビードルの「どくばり」（p.19。v0.3a）、キャタピーの「いとをはく」（p.17）・パラスの「キノコのほうし」（p.38。v0.3b）、
        # ロコンの「あやしいひかり」（p.67。v0.3c）、ジュゴンの「れいとうビーム」（p.102）・パラセクトの「キノコのほうし」（p.39。v0.4a）、
        # トランセルの「かたまる」・「しびれごな」（p.18）・コクーンの「かたまる」・「どくのこな」（p.21。v0.4b）、
        # スピアーの「ダブルニードル」・「どくばり」（p.21。v0.4c）、バタフリーの「ふきとばし」・「メガドレイン」（p.19。v0.4d）、
        # フシギダネの「やどりぎのタネ」（p.13）・フシギソウの「どくのこな」（p.14。v0.5）、
        # ゼニガメの「あわ」・「からにこもる」（p.87）・カメールの「からにこもる」（p.88）・カメックスの「ハイドロポンプ」（p.90。v0.6）、
        # ケーシィの「ねんりき」（p.149）・ユンゲラーの「じこさいせい」（p.151）・フーディンの「あやしいひかり」（p.153。v0.7）、
        # ベトベトンの「ヘドロこうげき」（p.48）・ロケット団のベトベターの「どくガス」「ねばりつく」（p.45。v0.8）、
        # 化石の秘密のゴースの「したでなめる」「エナジーへんかん」（p.158）・ゴーストの「あくむ」（p.160。v0.9）、
        # ゴーリキーの「からてチョップ」「じごくぐるま」（p.190。v0.10。カイリキーの「ちきゅうなげ」は説明文なし）、
        # サカキのワンリキーの「いかりのスーパーパンチ」（p.189）・サカキのゴーリキーの「いちかばちか」「じごくがため」（p.191）・
        # サカキのカイリキーの「ハリケーンパンチ」（p.193。v0.11。サカキのワンリキーの「チョップ」は説明文なし）、
        # R団のファイヤーの「ほのおのかべ」（p.82。v0.12）、わるいカメールの「おうふくびんた」「こうらがえし」（p.89。v0.13。第4弾の
        # ゼニガメの「こうらアタック」は説明文なし）、モンジャラの「しめつける」「どくのこな」（p.55）・サカキのニャースの「ねこノミ」
        # （p.229。v0.17a。「ねこキック」は説明文なし）、R団のカビゴンの「たおれこむ」（p.245。v0.17b）、ナツメのヤドンの「ぐうたらこうげき」
        # （p.155。v0.18c）、ストライクの「つるぎのまい」（p.56。v0.27。「きりさく」は説明文なし）、v0.28 の既存の効果の型の登録だけで加えた
        # スターミーの「じこさいせい」「スターフリーズ」（p.112）・スリープの「あやしいひかり」（p.164）・ラッキーの「まるまる」「すてみタックル」
        # （p.235）・タマタマの「さいみんじゅつ」「やどりぎのタネ」（p.49）・カイロスの「まんりきばさみ」（p.58）・プリンの「こもりうた」（p.225）・
        # シェルダーの「ちょうおんぱ」「からをとじる」（p.103）・ラプラスの「みずでっぽう」「あやしいひかり」（p.116）（トサキント・アズマオウの
        # ワザ・スリープとプリンの「はたく」・カイロスの「ハサミギロチン」は説明文なし）、v0.29 の kyuura データの採用で加えたニョロモの「みずでっぽう」・
        # アーボの「どくばり」・ナゾノクサの「ねむりごな」「どくのこな」・ドガースの「どくガス」・ミニリュウの「まきつく」・タケシのズバットの
        # 「どくのきば」・カスミのトサキントの「みだれづき」「ちょうおんぱ」・マチスのコイルの「でんきショック」・マチスのビリリダマの「スピンボール」
        # 「ダブルスピン」・タケシのイシツブテの「いしなげ」・タケシのベロリンガの「たたきつける」（ガイドブックの照合の記録はなく、採用の記録の
        # play_text と合う。scripts/check_card_sources.py）、v0.30 のエネルギーをトラッシュしてダメージを与えるワザ（ヒトカゲの「ひのこ」・リザード／
        # ウインディ／ブーバーの「かえんほうしゃ」は kyuura の RUL-ENERGY-DISCARD-ATTACKS の最新の説明、第4弾のポニータの「ひのこ」は印刷の文面）と
        # ウインディの「とっしん」（印刷の文面）。v0.31 で v0.30 の保留の 22 枚と進化元・依存のカードを加えた（V0_31_WITH_TEXT。
        # どれも採用の記録の play_text（kyuura の印刷の文面・エラッタ・card_differences の最新の説明）と合う。
        # scripts/check_card_sources.py。docs/held-cards-v0.31.md）
        expected = ([AttackKey("PMCG1-001", 0), AttackKey("PMCG1-002", 0), AttackKey("PMCG1-003", 0), AttackKey("PMCG1-003", 1),
                                     AttackKey("PMCG1-004", 0), AttackKey("PMCG1-007", 0), AttackKey("PMCG1-007", 1), AttackKey("PMCG1-008", 1), AttackKey("PMCG1-009", 0), AttackKey("PMCG1-009", 1),
                                     AttackKey("PMCG1-012", 0), AttackKey("PMCG1-012", 1), AttackKey("PMCG1-014", 1), AttackKey("PMCG1-015", 0),
                                     AttackKey("PMCG1-017", 1), AttackKey("PMCG1-019", 0), AttackKey("PMCG1-019", 1), AttackKey("PMCG1-020", 1),
                                     AttackKey("PMCG1-023", 0), AttackKey("PMCG1-023", 1), AttackKey("PMCG1-024", 0), AttackKey("PMCG1-026", 0), AttackKey("PMCG1-026", 1), AttackKey("PMCG1-027", 0),
                                     AttackKey("PMCG1-030", 1), AttackKey("PMCG1-032", 0), AttackKey("PMCG1-035", 1),
                                     AttackKey("PMCG1-043", 0), AttackKey("PMCG1-045", 1), AttackKey("PMCG1-046", 0), AttackKey("PMCG1-049", 0),
                                     AttackKey("PMCG1-055", 0), AttackKey("PMCG1-055", 1), AttackKey("PMCG1-061", 0), AttackKey("PMCG1-068", 0), AttackKey("PMCG1-068", 1),
                                     AttackKey("PMCG2-003", 1), AttackKey("PMCG2-006", 0), AttackKey("PMCG2-006", 1), AttackKey("PMCG2-007", 0), AttackKey("PMCG2-007", 1),
                                     AttackKey("PMCG2-010", 0), AttackKey("PMCG2-017", 0), AttackKey("PMCG2-018", 0), AttackKey("PMCG2-035", 0),
                                     AttackKey("PMCG3-007", 0), AttackKey("PMCG3-012", 0), AttackKey("PMCG3-012", 1), AttackKey("PMCG3-022", 0), AttackKey("PMCG3-022", 1),
                                     AttackKey("PMCG3-029", 0),
                                     AttackKey("PMCG3-029", 1), AttackKey("PMCG3-030", 0), AttackKey("PMCG4-001", 1), AttackKey("PMCG4-003", 0),
                                     AttackKey("PMCG4-003", 1), AttackKey("PMCG4-004", 0),
                                     AttackKey("PMCG4-004", 1), AttackKey("PMCG4-005", 1), AttackKey("PMCG4-013", 0), AttackKey("PMCG4-021", 0),
                                     AttackKey("PMCG4-021", 1),
                                     AttackKey("PMCG4-051", 0), AttackKey("PMCG5-001", 1),
                                     AttackKey("PMCG5-020", 0), AttackKey("PMCG5-026", 0), AttackKey("PMCG5-026", 1), AttackKey("PMCG5-037", 0),
                                     AttackKey("PMCG5-038", 0), AttackKey("PMCG5-038", 1), AttackKey("PMCG5-046", 0), AttackKey("PMCG5-061", 1),
                                     AttackKey("PMCG6-044", 0), AttackKey("PMCG6-057", 1),
                                     AttackKey("PMCG6-059", 0), AttackKey("PMCG6-059", 1), AttackKey("PMCG6-061", 0), AttackKey("PMCG6-063", 0),
                                     AttackKey("PMCG6-073", 0)] + V0_31_WITH_TEXT + V0_32_WITH_TEXT + V0_33_WITH_TEXT + V0_34_WITH_TEXT
                                    + V0_35_WITH_TEXT + V0_36_WITH_TEXT + V0_37_WITH_TEXT + V0_38_WITH_TEXT
                                    + V0_39_WITH_TEXT + V0_40_WITH_TEXT + V0_41_WITH_TEXT + V0_42_WITH_TEXT + V0_43_WITH_TEXT
                                + V0_44_WITH_TEXT + V0_45_WITH_TEXT + V0_46_WITH_TEXT + V0_47_WITH_TEXT + V0_48_WITH_TEXT
                                + V0_49_WITH_TEXT + V0_50_WITH_TEXT + V0_51_WITH_TEXT + V0_52_WITH_TEXT + V0_58_WITH_TEXT + V0_59_WITH_TEXT + V0_60_WITH_TEXT + V0_61_WITH_TEXT + V0_62_WITH_TEXT + V0_64_WITH_TEXT + V0_65_WITH_TEXT + V0_68_WITH_TEXT + V0_70_WITH_TEXT + V0_72_WITH_TEXT + V0_75_WITH_TEXT + V0_76_WITH_TEXT + V0_77_WITH_TEXT + V0_78_WITH_TEXT + V0_79_WITH_TEXT + V0_82_WITH_TEXT + V0_83_WITH_TEXT)
        # v0.69: 拡張パック以外の商品の同じカード（effects.EQUIVALENT_CARDS）の新しい id には、元のカードと同じ登録（説明文のあるワザも同じ）がある
        expected = expected + [AttackKey(new, key.attack_index) for new, original in EQUIVALENT_CARDS.items() for key in expected if key.card_id == original]
        # v0.71: 拡張パック以外の商品の再録のカード（effects.REPRINT_CARDS）の新しい id にも、元のカードの説明文のあるワザの登録がある（照合する文面はこの版の印刷の文面）
        expected = expected + [AttackKey(new, key.attack_index) for new, reprint in REPRINT_CARDS.items() for key in expected if key.card_id == reprint.original]
        self.assertEqual(with_text, sorted(expected))

    def test_pool_and_game_use_the_same_registry(self):
        state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, 1)
        self.assertIs(load_card_pool().effects, DEFAULT_EFFECTS)
        self.assertIs(state.effects, DEFAULT_EFFECTS)
        for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            self.assertEqual(copied.effects.attack_keys(), DEFAULT_EFFECTS.attack_keys())


# v0.30 からヒトカゲの「ひのこ」は登録した（DiscardEnergyThenDamage）。登録のないワザのテストは、その登録を除いた登録表
# （tests/helpers.py の NO_EMBER_EFFECTS）で、効果のないワザ（ひっかく）と登録のない効果のあるワザ（ひのこ）を持つカードを作って確かめる
# （v0.29 までは既定の登録表でそうなっていた）
NO_EMBER = NO_EMBER_EFFECTS


class UnregisteredTest(unittest.TestCase):
    def test_attack_with_text_is_not_registered(self):
        charmander = pool_from_extract(read_extract(), NO_EMBER).get(CHARMANDER)
        ember = charmander.attacks[1]
        self.assertIn("登録されていない", NO_EMBER.attack_problem(CHARMANDER, ember))
        self.assertFalse(charmander.supported)
        self.assertTrue(charmander.attacks[0].supported)  # ひっかくは登録してある（ワザ単位で分類する）

    def test_attack_without_text_is_refused_if_not_registered(self):
        """説明文がなくても、登録がなければ使えない（説明文が空なことは実装がある証拠にならない）。"""
        effects = DEFAULT_EFFECTS.without_attacks("test-no-machop", [AttackKey(MACHOP, 0)])
        pool = pool_from_extract(read_extract(), effects)
        machop = pool.get(MACHOP)
        self.assertIsNone(machop.attacks[0].text_ja)
        self.assertFalse(machop.attacks[0].supported)
        self.assertFalse(pool.is_playable(MACHOP))
        deck = expand_decklist({MACHOP: 4, FIGHTING: 56})
        self.assertTrue(any(p.startswith("UNSUPPORTED_CARD") for p in deck_problems(deck, pool)))
        with self.assertRaises(DeckValidationError):
            new_game(deck, FIRE_DECK, 0, pool=pool)
        # 対戦の中でも、その対戦の登録表に登録がなければ使えない
        state = build_test_state([{"active": {"card": MACHOP, "energy": [FIGHTING]}}, {"active": GROWLITHE}], effects=effects)
        before = state_to_dict(state)
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_ATTACK")
        self.assertEqual(state_to_dict(state), before)

    def test_unsupported_card_in_deck_is_rejected(self):
        deck = expand_decklist({CHARMANDER: 1, PONYTA: 4, FIRE: 55})
        self.assertTrue(any("ひのこ" in p and "登録されていない" in p for p in deck_problems(deck, pool_from_extract(read_extract(), NO_EMBER))))
        self.assertEqual(deck_problems(deck), [])  # 既定の登録表（v0.30 から）では使える


class RegisteredWithTextTest(unittest.TestCase):
    def test_attack_with_text_is_supported_when_an_implementation_is_registered(self):
        """説明文があっても、実装が登録されていれば使える。処理は登録した実装が行う（説明文から推測しない）。"""
        # v0.2d から、説明文のあるワザの登録には、照合した説明文（kyuura の写しの値）を書く
        ember_text = load_card_pool().get(CHARMANDER).attacks[1].text_ja
        effects = DEFAULT_EFFECTS.with_attacks(
            "test-ember", {AttackKey(CHARMANDER, 1): AttackEntry(RECORDING, "ひのこ", text_ja=ember_text)})
        pool = pool_from_extract(read_extract(), effects)
        self.assertTrue(pool.get(CHARMANDER).attacks[1].supported)
        self.assertTrue(pool.get(CHARMANDER).supported)
        state = build_test_state([{"active": {"card": CHARMANDER, "energy": [FIRE, FIRE]}}, {"active": GROWLITHE}], effects=effects)
        state = apply_command(state, UseAttack(0, 1))
        self.assertEqual([e["kind"] for e in state.log[-6:-4]], ["attack", "test_effect"])
        self.assertEqual(state.log[-5]["key"], "PMCG1-014#1")
        self.assertEqual(active(state, 1).damage, 0)  # 登録した実装はダメージを与えない（説明文の「30」は使わない）

    def test_attack_with_text_cannot_be_registered_as_damage_only(self):
        """効果のあるワザを、効果のないワザ（DamageOnly）として登録しても使えない（登録の誤りを見つける）。"""
        ember = load_card_pool().get(CHARMANDER).attacks[1]
        effects = DEFAULT_EFFECTS.with_attacks(
            "test-bad", {AttackKey(CHARMANDER, 1): AttackEntry(DAMAGE_ONLY, "ひのこ", text_ja=ember.text_ja)})
        self.assertIn("説明文のあるワザを、効果のないワザとして登録している", effects.attack_problem(CHARMANDER, ember))
        self.assertIsNone(effects.attack_effect(CHARMANDER, ember))

    def test_registered_name_must_match_the_data(self):
        """登録したワザ名がデータと違えば使えない（データの並びが変わったときに気づく）。"""
        effects = DEFAULT_EFFECTS.with_attacks("test-name", {AttackKey(PONYTA, 0): AttackEntry(DAMAGE_ONLY, "けとばす")})
        attack = load_card_pool().get(PONYTA).attacks[0]
        self.assertIn("ワザ名", effects.attack_problem(PONYTA, attack))


class SameNameDifferentCardTest(unittest.TestCase):
    """同じ名前のワザでも、カードが違えば別の登録（ワザ名は識別子ではない）。"""

    def test_registration_is_by_card_and_position(self):
        extract = extract_with_other_diglett()
        pool = pool_from_extract(extract)
        other = pool.get("TEST-OTHER-DIGLETT")
        self.assertEqual([a.name_ja for a in other.attacks], [a.name_ja for a in pool.get(DIGLETT).attacks])
        self.assertTrue(pool.get(DIGLETT).supported)
        self.assertFalse(other.supported)  # 同じ名前のワザだが、このカードには登録がない

        effects = DEFAULT_EFFECTS.with_attacks("test-other", {
            AttackKey("TEST-OTHER-DIGLETT", 0): AttackEntry(RECORDING, "あなをほる"),
            AttackKey("TEST-OTHER-DIGLETT", 1): AttackEntry(DAMAGE_ONLY, "どろかけ"),
        })
        pool = pool_from_extract(extract, effects)
        original = pool.get(DIGLETT).attacks[0]
        copy_attack = pool.get("TEST-OTHER-DIGLETT").attacks[0]
        self.assertIs(effects.attack_effect(DIGLETT, original), DAMAGE_ONLY)
        self.assertIs(effects.attack_effect("TEST-OTHER-DIGLETT", copy_attack), RECORDING)


class RegistryImmutabilityTest(unittest.TestCase):
    def test_with_and_without_do_not_change_the_original(self):
        keys = DEFAULT_EFFECTS.attack_keys()
        DEFAULT_EFFECTS.with_attacks("x", {AttackKey("PMCG1-021", 0): AttackEntry(RECORDING, "ほのおのうず")})
        DEFAULT_EFFECTS.without_attacks("y", keys)
        self.assertEqual(DEFAULT_EFFECTS.attack_keys(), keys)
        # v0.1 の 13 + ヒトカゲの「ひっかく」（v0.2a）+ ドードーの「みだれづき」（v0.2d）+ ピカチュウの 2 つ（v0.2f）
        # + ビードルの「どくばり」（v0.3a）+ キャタピーの「いとをはく」・パラスの「ひっかく」「キノコのほうし」（v0.3b）
        # + ロコンの「あやしいひかり」（v0.3c）+ パラセクトの 2 つ・ジュゴンの 2 つ（v0.4a）+ トランセルの 2 つ・コクーンの 2 つ（v0.4b）
        # + スピアーの 2 つ（v0.4c）+ バタフリーの 2 つ（v0.4d）+ フシギダネの 1 つ・フシギソウの 2 つ・フシギバナの 1 つ（v0.5）
        # + ゼニガメの 2 つ・カメールの 2 つ・カメックスの 1 つ（v0.6）+ ケーシィの 1 つ・ユンゲラーの 2 つ・フーディンの 1 つ（v0.7）
        # + ロケット団のベトベターの 2 つ・ベトベトンの 1 つ（v0.8）+ 化石の秘密のゴースの 2 つ・ゴーストの 1 つ（v0.9）
        # + ゴーリキーの 2 つ・カイリキーの 1 つ（v0.10）+ サカキのワンリキーの 2 つ・サカキのゴーリキーの 2 つ・サカキのカイリキーの 1 つ（v0.11）
        # + R団のファイヤーの 1 つ（v0.12）+ 第4弾のゼニガメの 1 つ・わるいカメールの 2 つ（v0.13）
        # + モンジャラの 2 つ・サカキのニャースの 2 つ（v0.17a）+ R団のカビゴンの 1 つ（v0.17b）+ ナツメのヤドンの 1 つ（v0.18c）
        # + ストライクの 2 つ（v0.27）
        # + ラプラス・スターミー・アズマオウ・カイロス・タマタマ・プリン・ラッキー・スリープ・シェルダーの 2 つずつ・トサキントの 1 つ（v0.28）
        # + アーボ・ズバット・ナゾノクサ・ドガース・ワンリキー・タケシのズバット・カスミのトサキント・マチスのコイル・マチスのビリリダマ・
        #   タケシのベロリンガの 2 つずつ・ニョロモ・ビリリダマ・ミニリュウ・タケシのイシツブテの 1 つずつ（v0.29。kyuura データの採用）
        # + ヒトカゲの「ひのこ」・リザード・ウインディ・ブーバーの 2 つずつ・第4弾のポニータの 1 つ（v0.30。エネルギーをトラッシュしてダメージを
        #   与えるワザの共通の型）
        # + v0.30 の保留の 22 枚と進化元・依存のカード 7 枚、合わせて 29 枚のワザ 52（v0.31。docs/held-cards-v0.31.md）
        # + 山札からベンチに出す・ダメージカウンターでダメージが決まる・与えたぶん回復するワザの 13 枚のワザ 26（v0.32。docs/bench-search-counter-drain-v0.32.md）
        # + 相手のエネルギーカードをトラッシュする・コインで失敗する／ダメージを与えられない・控えにもダメージを与えるワザの 15 枚のワザ 28
        #   （v0.33。docs/cd4-opponent-energy-coins-v0.33.md）
        # + バリアーに対するコインの見直し・ダメージのあとの決定をまたぐ処理と合わせた 14 枚のワザ 27（v0.34。docs/barrier-resume-coin-bonus-v0.34.md）
        # + 可変枚数のコインの先読み・ダメージの計算の順番の決定と合わせた 5 枚のワザ 10（v0.35。docs/coin-groups-damage-order-v0.35.md）
        # + 手順 4 のコイン・「にげる」ことができない効果・自分を山札にもどす効果と合わせた 11 枚のワザ 19（v0.36。docs/sand-attack-retreat-lock-v0.36.md）
        # + 既存の効果の再利用・文面の違いの受け付け・新しい要素の組み合わせの 15 枚のワザ 28（v0.37。docs/fifteen-reused-effects-v0.37.md）
        # + 控えへのダメージ・入れ替え・同じコインの複数の効果・軽減・山札にもどる効果の 15 枚のワザ 29（v0.38。docs/bench-switch-combined-v0.38.md）
        # + じばく・控えへのダメージ・場のポケモンの数でダメージが決まるワザの 15 枚のワザ 25（v0.39。docs/selfdestruct-spread-count-v0.39.md）
        # + 場の数・条件付きの効果・入れ替え・カードの移動の 15 枚のワザ 28（v0.40。docs/count-condition-switch-return-v0.40.md）
        # + 回復・カウンターの移動・特殊状態の変化を中心とする 15 枚のワザ 29（v0.41。docs/heal-counter-status-v0.41.md）
        # + 回復・カウンター操作と、特殊能力を持つ進化系統を中心とする 15 枚のワザ 21（v0.42。docs/power-decisions-v0.42.md）
        # + 宣言して使う特殊能力・場に出たときに使う特殊能力を持つ 9 枚のワザ 9（v0.43。docs/declared-entry-powers-v0.43.md）
        # + 検索・進化・1 度だけ使えるワザの 14 枚のワザ 24（v0.44。docs/search-evolution-once-attacks-v0.44.md）
        # + 条件つきのダメージ・エネルギーの移動とトラッシュ・受けたダメージを返す効果などの 15 枚のワザ 28（v0.45。カスミのタッツー（HP 50）・
        #   キョウのアーボはワザ 1 つ。docs/conditional-damage-energy-v0.45.md）
        # + 常にはたらく特殊能力を持つ 8 枚（ワザ 1 つずつ）と関連する 3 枚（ワザ 2 つずつ）のワザ 14（v0.46。docs/continuous-powers-v0.46.md）
        # + なにかの化石・ピッピ人形と化石のポケモン・見えない情報を扱う 4 枚・トレーナーの使用を禁止する 2 枚のうち、ポケモン 11 枚のワザ 17（v0.47。
        #   オムナイト・カブト・プテラ・マンキー・コラッタはワザ 1 つ。docs/fossil-hidden-info-v0.47.md）
        # + 場のポケモンの今有効な最大HP・タイプ・弱点・抵抗力を変える 7 枚のワザ 11（v0.48。モルフォン・ナツメのゴース・ナツメのゴーストはワザ 1 つ。
        #   docs/effective-pokemon-properties-v0.48.md）
        # + ナツメのフーディンの「メガバーン」・タケシのキュウコンの「おにび」（v0.49。メタモンはワザなし。docs/virtual-attacks-transformation-v0.49.md）
        # + ミュウの「サイコウェーブ」・「たいかビーム」（v0.50。docs/mew-devolution-spray-v0.50.md）
        # + ナツメのスリーパーの「よみがえらせる」・「ふりこののろい」（v0.51。docs/discard-to-bench-v0.51.md）
        # + エリカのハクリューの「ふぶき」・「つれさる」（v0.52。docs/field-return-v0.52.md）
        # + タケシのゴローンの「たいあたり」・「ばくれつ」・タケシのゴローニャの「いわなだれ」・「ランドクラッシュ」（v0.58。docs/stadium-reuse-special-energy-v0.58.md）
        # + マルマイン（第1弾）の「でんげき」・カスミのメノクラゲの「クリスタルビーム」・わるいアーボックの「ショックアイ」・「どくのきり」（v0.59。
        #   docs/energy-control-power-suppression-v0.59.md）
        # + サンダー（化石の秘密）の「サンダーストーム」・R団のストライクの「かげぶんしん」「こうそくカマ」・カスミのギャラドスの「ハイドロクラッシュ」・タケシのサンドパンの
        #   「スピードスター」「とげボール」（v0.60。docs/coins-defense-rebellion-v0.60.md）
        # + わるいギャラドスの「れいとうビーム」・わるいダグトリオの「つきおとす」・タケシのオコリザルの「おおあばれ」（v0.61。docs/reactive-powers-trainer-damage-v0.61.md）
        # + 化石の秘密のイシツブテの「れんぞくいしなげ」・ゴローンの「かたくなる」「いわおとし」・ゴローニャの「いわころがり」「じばく」（v0.64。
        #   docs/geodude-line-unbounded-coins-v0.64.md）
        # + カスミのドククラゲの「クラゲどく」・タケシのサイドンの「ラリアット」（v0.65。docs/reactive-decisions-v0.65.md）
        # + ガルーラの「こどものおつかい」「れんぞくパンチ」・キョウのベトベトンの「ヘドロのうず」・イマクニ？のドードーの「ハモる」（v0.68。docs/final-pmcg-cards-v0.68.md）
        self.assertEqual(len(keys), 1248)  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.72: 拡張パック以外の商品のポケモン 43 枚のワザ 77 を加えた。v0.71: 拡張パック以外の商品の再録 11 枚のワザ 15 を加えた（元のカードの登録から作った）。v0.70: 拡張パック以外の商品のポケモン 82 枚のワザ 136 を加えた。v0.69: 拡張パック以外の商品の同じカード 84 枚のワザ 92 を加えた（元のカードの登録を写した）  # v0.83 でポケモン 18 枚（ワザ 33）を加えた
        # ポケモンパワー（v0.5）の登録も同じく変わらない（with_powers・without_powers は新しい登録表を返す）
        powers = DEFAULT_EFFECTS.power_keys()
        DEFAULT_EFFECTS.without_powers("z", powers)
        DEFAULT_EFFECTS.with_powers("w", {PowerKey(CHARMANDER, 0): DEFAULT_EFFECTS.power_entry(VENUSAUR, 0)})
        self.assertEqual(DEFAULT_EFFECTS.power_keys(), powers)
        # フシギバナの「エナジートランス」（v0.5）・カメックスの「あまごい」（v0.6）・フーディンの「ダメージスワップ」（v0.7）
        # v0.8 でベトベトンの「かがくへんかガス」（PMCG3-007）、v0.9 でゴーストの「とうめい」（PMCG3-030）、v0.10 でカイリキーの「はんげき」
        # （PMCG1-057）、v0.11 でサカキのカイリキーの「こんじょう」（PMCG6-061）、v0.12 で R団のファイヤーの「ふしちょう」（PMCG5-020）、v0.17b で
        # R団のカビゴンの「わるいねぞう」（PMCG6-073）を加えた。v0.31 でリザードンの「エナジーバーン」（PMCG1-021）・カツラのロコンの
        # 「しぜんになおる」（PMCG6-026）・カツラのキュウコンの「ほのおでかいふく」（PMCG6-033）を加えた（docs/held-cards-v0.31.md）。v0.42 で
        # ラフレシア・メノクラゲ・ヤドラン・ゲンガー・カイリュー・わるいユンゲラー・エリカのラフレシア・エリカのウツボットの 8 つを加えた
        # （docs/power-decisions-v0.42.md）。v0.43 でわるいクサイハナ・わるいゴルバット・ロケット団のヒトカゲ・ロケット団のスリープ・わるいヤドラン・
        # わるいハクリュー・わるいカイリュー・エリカのマダツボミ（PMCG5-010）・マチスのレアコイルの 9 つを加えた（docs/declared-entry-powers-v0.43.md）。
        # v0.44 でキョウのコクーンの［うか］（PMCG6-011）・サカキのペルシアンの［ボスをよぶ］（PMCG6-071）を加えた（docs/search-evolution-once-attacks-v0.44.md）。
        # v0.46 で常にはたらく特殊能力 8 つ（PMCG2-027・PMCG2-040・PMCG2-047・PMCG4-007・PMCG4-010・PMCG4-041・PMCG5-063・PMCG6-010）を加えた
        # （docs/continuous-powers-v0.46.md）。v0.47 でマンキーの［スパイ］（PMCG2-028）・オムナイトの［おみとおし］（PMCG3-015）・カブトの［カブトアーマー］
        # （PMCG3-035）・プテラの［げんしのちから］（PMCG3-041）・ロケット団のコラッタの［わるふざけ］（PMCG4-045）を加えた（docs/fossil-hidden-info-v0.47.md）。
        # v0.48 でモルフォンの［へんしょく］（PMCG2-015）・ナツメのゴースの［ガスのからだ］（PMCG6-049）を加えた（docs/effective-pokemon-properties-v0.48.md）。
        # v0.49 でメタモンの［へんしん］（PMCG3-042）・タケシのキュウコンの「ばける」（PMCG5-019）・ナツメのフーディンの［サイコリンク］（PMCG6-053）を加えた
        # （docs/virtual-attacks-transformation-v0.49.md）
        # v0.59 でマルマイン（第1弾。PMCG1-040）の［エネエネ］を加えた（docs/energy-control-power-suppression-v0.59.md）。
        ORIGINAL_POWERS = (PowerKey(VENUSAUR, 0), PowerKey("PMCG1-021", 0), PowerKey("PMCG1-032", 0), PowerKey("PMCG1-040", 0), PowerKey("PMCG1-049", 0),
                                  PowerKey("PMCG1-057", 0), PowerKey("PMCG2-014", 0), PowerKey("PMCG2-015", 0), PowerKey("PMCG2-027", 0), PowerKey("PMCG2-028", 0),
                                  PowerKey("PMCG2-040", 0), PowerKey("PMCG2-047", 0), PowerKey("PMCG3-007", 0), PowerKey("PMCG3-011", 0),
                                  PowerKey("PMCG3-015", 0), PowerKey("PMCG3-028", 0), PowerKey("PMCG3-030", 0), PowerKey("PMCG3-031", 0),
                                  PowerKey("PMCG3-035", 0), PowerKey("PMCG3-041", 0), PowerKey("PMCG3-042", 0), PowerKey("PMCG3-043", 0),
                                  PowerKey("PMCG4-006", 0), PowerKey("PMCG4-007", 0), PowerKey("PMCG4-009", 0), PowerKey("PMCG4-010", 0),
                                  PowerKey("PMCG4-012", 0), PowerKey("PMCG4-025", 0), PowerKey("PMCG4-033", 0),  # v0.61: わるいギャラドスの［ファイナルビーム］
                                  PowerKey("PMCG4-034", 0), PowerKey("PMCG4-036", 0), PowerKey("PMCG4-041", 0),
                                  PowerKey("PMCG4-043", 0),  # v0.61: わるいダグトリオの［おとしあな］
                                  PowerKey("PMCG4-045", 0),
                                  PowerKey("PMCG4-052", 0),
                                  PowerKey("PMCG4-053", 0),
                                  PowerKey("PMCG5-010", 0), PowerKey("PMCG5-014", 0), PowerKey("PMCG5-015", 0), PowerKey("PMCG5-019", 0), PowerKey("PMCG5-020", 0),
                                  PowerKey("PMCG5-033", 0),  # v0.65: カスミのドククラゲの［にげこむ］
                                  PowerKey("PMCG5-035", 0),  # v0.60: カスミのギャラドスの［はんこう］
                                  PowerKey("PMCG5-040", 0),
                                  PowerKey("PMCG5-051", 0),  # v0.61: タケシのオコリザルの［ずらかる］
                                  PowerKey("PMCG5-055", 0),  # v0.65: タケシのサイドンの［ベンチガード］
                                  PowerKey("PMCG5-063", 0), PowerKey("PMCG6-010", 0), PowerKey("PMCG6-011", 0),
                                  PowerKey("PMCG6-023", 0),  # v0.68: キョウのベトベトンの［だつりょくえき］
                                  PowerKey("PMCG6-026", 0), PowerKey("PMCG6-033", 0), PowerKey("PMCG6-049", 0), PowerKey("PMCG6-053", 0),
                                  PowerKey("PMCG6-061", 0), PowerKey("PMCG6-071", 0), PowerKey("PMCG6-073", 0),
                                  PowerKey("PMCG6-074", 0))  # v0.68: イマクニ？のドードーの［にげまくり］
        # v0.69: 拡張パック以外の商品の同じカードの新しい id 10 枚の特殊能力（元のカードの登録を写した）
        self.assertEqual(tuple(k for k in powers if k.card_id.startswith("PMCG")), ORIGINAL_POWERS)
        # v0.71: 拡張パック以外の商品の再録のカードの特殊能力 6（元のカードの登録から作った）
        self.assertEqual(tuple(k for k in powers if not k.card_id.startswith("PMCG")),
                         tuple(sorted((PowerKey("GD1-013", 0), PowerKey("GD2-004", 0), PowerKey("GD3-006", 0), PowerKey("GD4-008", 0), PowerKey("GD4-013", 0),
                                       PowerKey("GD5-002", 0), PowerKey("GD5-004", 0), PowerKey("GD6-004", 0), PowerKey("PR1-039", 0), PowerKey("PR1-061", 0),
                                       *(PowerKey(card, 0) for card in ("GD4-004", "IPH-001", "IPH-002", "PR1-028", "PR1-029", "PR1-030"))))))


if __name__ == "__main__":
    unittest.main()
