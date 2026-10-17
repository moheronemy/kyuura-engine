"""テスト用の道具。

- ``build_test_state``: 正式な対戦開始（``new_game``）を通さずに、盤面を直接作る。
  ルールの 1 か所だけを確かめたいテストで使う。デッキの枚数などの対戦準備の規定は
  通らないので、対戦準備・デッキのテストには使わない。
- ``scripted_command``: 統合テストで 1 試合を最後まで進めるための、決まった手順の操作。
  対戦相手の AI ではない（強さや戦略は考えていない）。
- ``with_coin_results``（v0.2d）: テストの中だけで、次に投げるコインの結果を決める（状態の乱数を、
  その結果になる乱数に差し替える）。エンジンの API にはコインの結果を指定する方法はない。
"""

from __future__ import annotations

import random
from typing import Iterable

from kyuura_engine import (
    AttachEnergy,
    DrawMulliganCards,
    EndTurn,
    GameState,
    Phase,
    PlaceStartingPokemon,
    PlayBasicToBench,
    PromoteActive,
    ReportJankenResult,
    TakePrize,
    UseAttack,
    apply_command,
    can_pay_cost,
    expand_decklist,
    load_card_pool,
    new_game,
)
from kyuura_engine.rules import RULES_2000_02_14
from kyuura_engine.state import (
    ASLEEP,
    AttachedTrainer,
    CONFUSED,
    NextTurnAttackDamage,
    PreventDamage,
    Retaliation,
    RETALIATION_RECEIVED,
    CardInstance,
    DataSource,
    Paralyzed,
    PlayerState,
    Poison,
    PokemonInPlay,
    SpecialConditions,
    freeze_mapping,
)

# カード id（kyuura data/cards.json の id）
PONYTA = "PMCG1-016"
GROWLITHE = "PMCG1-018"
STARYU = "PMCG1-025"
SEEL = "PMCG1-029"
VOLTORB = "PMCG1-037"
DIGLETT = "PMCG1-052"
MACHOP = "PMCG1-053"
HITMONCHAN = "PMCG1-058"
RATTATA = "PMCG1-060"
DRATINI = "PMCG1-065"
GRASS = "PMCG1-097"
FIRE = "PMCG1-098"
WATER = "PMCG1-099"
LIGHTNING = "PMCG1-100"
PSYCHIC = "PMCG1-101"
FIGHTING = "PMCG1-102"
CHARMANDER = "PMCG1-014"  # ヒトカゲ（v0.29 までは「ひのこ」が未対応の参照カード。v0.30 で対戦用。ひっかく（無）10・ひのこ（炎無）30）
DODUO = "PMCG1-061"  # ドードー（v0.2d で対応。みだれづき: コイン 2 枚の「おもて」の数×10）
PIKACHU = "PMCG1-035"  # ピカチュウ（v0.2f で対応。かじる 10、でんげき 30・「うら」なら自分にも 10）
WEEDLE = "PMCG1-004"  # ビードル（v0.3a で対応。どくばり 10・「おもて」なら相手をどく状態に）
CATERPIE = "PMCG1-002"  # キャタピー（v0.3b で対応。いとをはく 10・「おもて」なら相手をマヒ状態に）
PARAS = "PMCG2-003"  # パラス（v0.3b で対応。ひっかく 20、キノコのほうし（ダメージなし）で相手をねむり状態に）
VULPIX = "PMCG1-015"  # ロコン（v0.3c で対応。あやしいひかり 10・「おもて」なら相手をこんらん状態に。炎・弱点 水・にげる 1）
SCYTHER = "PMCG2-017"  # ストライク（v0.27。たね・HP 70・草・弱点 炎・抵抗力 闘 -30・にげる 0。つるぎのまい（草）・きりさく（無無無）30。p.56）
# v0.28: 既存の効果の型の登録だけで加えたポケモン（docs/existing-effect-pokemon-v0.28.md）
LAPRAS = "PMCG3-022"  # ラプラス（化石の秘密。たね・HP 80・水・弱点 雷・にげる 2。みずでっぽう（水）10+・あやしいひかり（水水）10。p.116）
STARMIE = "PMCG1-026"  # スターミー（ヒトデマンから進化。HP 60・水・弱点 雷・にげる 1。じこさいせい（水水）・スターフリーズ（水無無）20。p.112）
GOLDEEN = "PMCG2-021"  # トサキント（たね・HP 40・水・弱点 雷・にげる 0。つのでつく（水）10。p.108）
SEAKING = "PMCG2-022"  # アズマオウ（トサキントから進化。HP 70・水・弱点 雷・にげる 1。つのでつく（水）10・たきのぼり（水無）30。p.109）
PINSIR = "PMCG2-018"  # カイロス（たね・HP 60・草・弱点 炎・にげる 1。まんりきばさみ（草草）20・ハサミギロチン（草草無無）50。p.58）
EXEGGCUTE = "PMCG2-006"  # タマタマ（たね・HP 50・草・弱点 炎・にげる 1。さいみんじゅつ（超）・やどりぎのタネ（草草）20。p.49）
JIGGLYPUFF = "PMCG2-035"  # プリン（たね・HP 60・無色・弱点 闘・抵抗力 超 -30・にげる 1。こもりうた（無）・はたく（無無）20。p.225）
CHANSEY = "PMCG1-068"  # ラッキー（たね・HP 120・無色・弱点 闘・抵抗力 超 -30・にげる 1。まるまる（無無）・すてみタックル（無無無無）80。p.235）
DROWZEE = "PMCG1-045"  # スリープ（たね・HP 50・超・弱点 超・にげる 1。はたく（無）10・あやしいひかり（超超）10。p.164）
SHELLDER = "PMCG3-012"  # シェルダー（化石の秘密。たね・HP 30・水・弱点 雷・にげる 1。ちょうおんぱ（水）・からをとじる（水）。p.103）
V0_28_POKEMON = (LAPRAS, STARMIE, GOLDEEN, SEAKING, PINSIR, EXEGGCUTE, JIGGLYPUFF, CHANSEY, DROWZEE, SHELLDER)
# v0.29: 既存の効果の型の登録だけで加えたポケモン（kyuura データの採用。docs/existing-effect-pokemon-v0.29.md）。どれもたねポケモン。同じ名前の
# 第1弾のカード（VOLTORB・MACHOP・DRATINI など）とは別の id
POLIWAG = "PMCG1-024"  # ニョロモ（第1弾。HP 40・水・弱点 草・にげる 1。みずでっぽう（水）10+）
ROCKET_EKANS = "PMCG4-001"  # アーボ（ロケット団。HP 50・草・弱点 超・にげる 1。かみつく（無）10・どくばり（草草）20）
ROCKET_ZUBAT = "PMCG4-002"  # ズバット（ロケット団。HP 40・草・弱点 超・抵抗力 闘 -30・にげる 0。ぶつかる（無）10・かみつく（草無）20）
ROCKET_ODDISH = "PMCG4-003"  # ナゾノクサ（ロケット団。HP 50・草・弱点 炎・にげる 1。ねむりごな（草）・どくのこな（草）。ダメージの目安なし）
ROCKET_KOFFING = "PMCG4-005"  # ドガース（ロケット団。HP 40・草・弱点 超・にげる 1。たいあたり（無）10・どくガス（草無）20）
ROCKET_VOLTORB = "PMCG4-027"  # ビリリダマ（ロケット団。HP 40・雷・弱点 闘・にげる 1。スピードボール（雷）20）
ROCKET_MACHOP = "PMCG4-040"  # ワンリキー（ロケット団。HP 50・闘・弱点 超・にげる 1。パンチ（無無）20・キック（闘無無）30）
ROCKET_DRATINI = "PMCG4-051"  # ミニリュウ（ロケット団。HP 40・無色・弱点なし・抵抗力 超 -30・にげる 1。まきつく（無無）10）
BROCKS_ZUBAT = "PMCG5-001"  # タケシのズバット（HP 40・草・弱点 超・抵抗力 闘 -30・にげる 0。つばさでうつ（無）10・どくのきば（草無）20）
MISTYS_GOLDEEN = "PMCG5-026"  # カスミのトサキント（HP 40・水・弱点 雷・にげる 1。みだれづき（無）10×・ちょうおんぱ（水）。ダメージの目安なし）
LT_SURGES_MAGNEMITE = "PMCG5-037"  # マチスのコイル（HP 40・雷・弱点 闘・にげる 1。でんきショック（雷）10・たいあたり（無無）20）
LT_SURGES_VOLTORB = "PMCG5-038"  # マチスのビリリダマ（HP 40・雷・弱点 闘・にげる 1。スピンボール（雷）20×・ダブルスピン（雷無）20×）
BROCKS_GEODUDE = "PMCG5-046"  # タケシのイシツブテ（HP 50・闘・弱点 草・にげる 1。いしなげ（闘）10×）
BROCKS_LICKITUNG = "PMCG5-061"  # タケシのベロリンガ（HP 80・無色・弱点 闘・抵抗力 超 -30・にげる 3。ベロではたく（無無）20・たたきつける（無無無）30×）
V0_29_POKEMON = (POLIWAG, ROCKET_EKANS, ROCKET_ZUBAT, ROCKET_ODDISH, ROCKET_KOFFING, ROCKET_VOLTORB, ROCKET_MACHOP, ROCKET_DRATINI,
                 BROCKS_ZUBAT, MISTYS_GOLDEEN, LT_SURGES_MAGNEMITE, LT_SURGES_VOLTORB, BROCKS_GEODUDE, BROCKS_LICKITUNG)
# v0.30: 自分の「炎」エネルギーカードを 1 枚トラッシュしてダメージを与えるワザの共通の型（DiscardEnergyThenDamage）で加えたポケモン
# （docs/discard-energy-attacks-v0.30.md）。ヒトカゲ（CHARMANDER）も v0.30 から対戦用。第4弾のポニータは第1弾のポニータ（PONYTA）と同じ名前の別のカード
CHARMELEON = "PMCG1-017"  # リザード（第1弾。ヒトカゲから進化。HP 80・炎・弱点 水・にげる 1。きりさく（無無無）30・かえんほうしゃ（炎炎無）50）
ARCANINE = "PMCG1-019"  # ウインディ（第1弾。ガーディから進化。HP 100・炎・弱点 水・にげる 3。かえんほうしゃ（炎炎無）50・とっしん（炎炎無無）80）
MAGMAR = "PMCG1-020"  # ブーバー（第1弾。たね。HP 50・炎・弱点 水・にげる 2。ほのおパンチ（炎炎）30・かえんほうしゃ（炎炎無）50）
ROCKET_PONYTA = "PMCG4-013"  # ポニータ（第4弾ロケット団。たね。HP 50・炎・弱点 水・にげる 1。ひのこ（炎無）30）
V0_30_POKEMON = ("PMCG1-014", CHARMELEON, ARCANINE, MAGMAR, ROCKET_PONYTA)
# v0.31: v0.30 で保留した 22 枚（docs/held-cards-v0.31.md）と、その進化元として加えた 7 枚。写しの組 pool_v0_31 の並び（対象 22 枚 → 進化元 7 枚）
NINETALES = "PMCG1-022"  # キュウコン（第1弾。ロコンから進化。かどわかす・だいもんじ）
ZAPDOS = "PMCG1-042"  # サンダー（第1弾。かみなり・10まんボルト）
BASE_GASTLY = "PMCG1-044"  # ゴース（第1弾。さいみんガス・みちづれ。化石の秘密のゴース GASTLY とは別のカード）
MEWTWO = "PMCG1-050"  # ミュウツー（第1弾。サイコキネシス・バリアー）
CLEFABLE = "PMCG2-044"  # ピクシー（ジャングル。ピッピから進化。ゆびをふる・ちいさくなる）
MOLTRES = "PMCG3-009"  # ファイヤー（化石の秘密。やまやき・ゴッドバード）
SLOWPOKE = "PMCG3-027"  # ヤドン（化石の秘密。ぼーっとする・ゴミあさり）
DARK_RAPIDASH = "PMCG4-014"  # わるいギャロップ（ロケット団。ポニータ（第4弾）から進化。うしろげり・ひばしら）
DARK_CHARMELEON = "PMCG4-015"  # わるいリザード（ロケット団。ヒトカゲから進化。しっぽでたたく・ファイヤーボール）
DARK_FLAREON = "PMCG4-016"  # わるいブースター（ロケット団。イーブイから進化。いかり・ひあそび）
DARK_CHARIZARD = "PMCG4-017"  # わるいリザードン（ロケット団。わるいリザードから進化。つめではじく・れんぞくファイヤーボール）
DARK_GOLDUCK = "PMCG4-022"  # わるいゴルダック（ロケット団。コダックから進化。だい3のめ・ちょうねんりき）
DARK_ELECTRODE = "PMCG4-028"  # わるいマルマイン（ロケット団。ビリリダマ（第4弾）から進化。ころがりタックル・エナジーボム）
MISTYS_GOLDUCK = "PMCG5-032"  # カスミのゴルダック（カスミのコダックから進化。エクストラビーム・スーパーデストロイ）
LT_SURGES_ELECTABUZZ = "PMCG5-041"  # マチスのエレブー（たいでん・ほうでん）
BLAINES_CHARMANDER = "PMCG6-025"  # カツラのヒトカゲ（メラメラ・きりさく）
BLAINES_CHARMELEON = "PMCG6-029"  # カツラのリザード（カツラのヒトカゲから進化。ほのおのつめ・やきはらう）
BLAINES_MAGMAR = "PMCG6-031"  # カツラのブーバー（ひをふく・マグマふんしゅつ）
BLAINES_NINETALES = "PMCG6-033"  # カツラのキュウコン（カツラのロコンから進化。ほのおでかいふく・しゃくねつ）
BLAINES_ARCANINE = "PMCG6-034"  # カツラのウインディ（カツラのガーディから進化。ヒートタックル・ほのおのあらし）
LT_SURGES_RAICHU = "PMCG6-041"  # マチスのライチュウ（マチスのピカチュウから進化。バリバリ・でんきタックル）
CLEFAIRY = "PMCG1-067"  # ピッピ（第1弾。進化元。うたう・ゆびをふる）
EEVEE = "PMCG2-037"  # イーブイ（ジャングル。進化元。しっぽをふる・でんこうせっか）
PSYDUCK = "PMCG4-019"  # コダック（ロケット団。進化元。めまい・みずでっぽう）
MISTYS_PSYDUCK = "PMCG5-021"  # カスミのコダック（進化元。ちょうのうりょく）
BLAINES_VULPIX = "PMCG6-026"  # カツラのロコン（進化元。しぜんになおる・しっぽでまどわす）
BLAINES_GROWLITHE = "PMCG6-027"  # カツラのガーディ（進化元。もえひろがる）
LT_SURGES_PIKACHU = "PMCG5-036"  # マチスのピカチュウ（進化元。でんこうせっか）
V0_31_TARGETS = (NINETALES, "PMCG1-021", ZAPDOS, BASE_GASTLY, MEWTWO, CLEFABLE, MOLTRES, SLOWPOKE, DARK_RAPIDASH, DARK_CHARMELEON,
                 DARK_FLAREON, DARK_CHARIZARD, DARK_GOLDUCK, DARK_ELECTRODE, MISTYS_GOLDUCK, LT_SURGES_ELECTABUZZ, BLAINES_CHARMANDER,
                 BLAINES_CHARMELEON, BLAINES_MAGMAR, BLAINES_NINETALES, BLAINES_ARCANINE, LT_SURGES_RAICHU)
V0_31_DEPENDENCIES = (CLEFAIRY, EEVEE, PSYDUCK, MISTYS_PSYDUCK, BLAINES_VULPIX, BLAINES_GROWLITHE, LT_SURGES_PIKACHU)
V0_31_POKEMON = V0_31_TARGETS + V0_31_DEPENDENCIES
# v0.32（山札からベンチに出す・ダメージカウンターでダメージが決まる・与えたぶん回復するワザのポケモンと進化先。docs/bench-search-counter-drain-v0.32.md）
NIDORAN_F = "PMCG2-001"  # ニドラン♀（第2弾。HP 60・草・弱点 超・にげる 1。みだれひっかき（草）10×・なかまをよぶ（草草））
JUNGLE_ODDISH = "PMCG2-002"  # ナゾノクサ（第2弾。HP 50・草・弱点 炎・にげる 1。しびれごな（草）10・ふえる（草草））。ROCKET_ODDISH と同じ名前の別のカード
BELLSPROUT = "PMCG2-005"  # マダツボミ（第2弾。HP 40・草・弱点 炎・にげる 1。つるのムチ（草）10・なかまをよぶ（草））
KRABBY = "PMCG3-013"  # クラブ（化石の秘密。HP 50・水・弱点 雷・にげる 2。なかまをよぶ（水）・はさむ（水無）20）
NIDORINA = "PMCG2-008"  # ニドリーナ（第2弾。ニドラン♀から進化。HP 70。ちょうおんぱ（草）・にどげり（草無無）30×）
WEEPINBELL = "PMCG2-011"  # ウツドン（第2弾。マダツボミから進化。HP 70。どくのこな（草）10・はっぱカッター（草草）30）
MAGIKARP = "PMCG1-031"  # コイキング（第1弾。HP 30・水・弱点 雷・にげる 1。たいあたり（無）10・じたばた（水）10×）
GYARADOS = "PMCG1-034"  # ギャラドス（第1弾。コイキングから進化。HP 100・水・弱点 草・抵抗力 闘 -30。りゅうのいかり（水水水）50・バブルこうせん（水水水水）40）
KINGLER = "PMCG3-019"  # キングラー（化石の秘密。クラブから進化。HP 60・水・弱点 雷。じたばた（水）10×・クラブハンマー（水水無）40）
JYNX = "PMCG1-048"  # ルージュラ（第1弾。HP 70・超・弱点 超・にげる 2。おうふくびんた（超）10×・ヨガのポーズ（超超無）20+）
VENONAT = "PMCG2-004"  # コンパン（第2弾。HP 40・草・弱点 炎・にげる 1。しびれごな（草）10・きゅうけつ（草無）10）
FOSSIL_ZUBAT = "PMCG3-002"  # ズバット（化石の秘密。HP 40・草・弱点 超・抵抗力 闘 -30・にげる 0。ちょうおんぱ（無無）・きゅうけつ（草無）10）
GOLBAT = "PMCG3-005"  # ゴルバット（化石の秘密。ズバットから進化。HP 60・草・弱点 超・抵抗力 闘 -30・にげる 0。つばさでうつ（無無無）30・きゅうけつ（草草無）20）
V0_32_POKEMON = (NIDORAN_F, JUNGLE_ODDISH, BELLSPROUT, KRABBY, NIDORINA, WEEPINBELL, MAGIKARP, GYARADOS, KINGLER, JYNX, VENONAT, FOSSIL_ZUBAT, GOLBAT)
# v0.33（相手のエネルギーカードをトラッシュする・コインで失敗する／ダメージを与えられない・控えにもダメージを与えるワザのポケモンと進化先。
# docs/cd4-opponent-energy-coins-v0.33.md）
DRAGONAIR = "PMCG1-069"  # ハクリュー（第1弾。ミニリュウから進化。HP 80・無色・抵抗力 超 -30・にげる 2。たたきつける（無無無）30×・はかいこうせん（無無無無）20）
FOSSIL_GOLDUCK = "PMCG3-016"  # ゴルダック（化石の秘密。コダックから進化。HP 70・水・弱点 雷・にげる 1。ねんりき（超）10・はかいこうせん（水水無）20）
DARK_VAPOREON = "PMCG4-023"  # わるいシャワーズ（ロケット団。イーブイから進化。HP 60・水・弱点 雷・にげる 1。かみつく（無無無）30・うずしお（水水無）20）
LT_SURGES_MAGNEMITE_30 = "PMCG5-039"  # マチスのコイル（HP 30・雷・弱点 闘・にげる 0。はかいでんぱ（雷）10・こんらんでんぱ（雷雷）20）。LT_SURGES_MAGNEMITE と同じ名前の別のカード
SABRINAS_VENONAT = "PMCG6-006"  # ナツメのコンパン（HP 40・草・弱点 炎・にげる 1。どくのしょっかく（草）・はかいビーム（超無）20）
NIDORAN_M = "PMCG1-005"  # ニドラン♂（第1弾。HP 40・草・弱点 超・にげる 1。つのでつつく（草）30）
NIDORINO = "PMCG1-010"  # ニドリーノ（第1弾。ニドラン♂から進化。HP 60・草・弱点 超・にげる 1。にどげり（草無無）30×・つのドリル（草草無無）50）
CLOYSTER = "PMCG3-018"  # パルシェン（化石の秘密。シェルダーから進化。HP 50・水・弱点 雷・にげる 2。からではさむ（水水）30・とげキャノン（水水）30×）
DARK_RATICATE = "PMCG4-046"  # わるいラッタ（ロケット団。コラッタから進化。HP 50・無色・弱点 闘・抵抗力 超 -30・にげる 1。かじる（無無）20・ひっさつまえば（無無無）50）
BROCKS_DIGLETT = "PMCG5-044"  # タケシのディグダ（HP 40・闘・弱点 草・抵抗力 雷 -30・にげる 1。ふいをつく（闘）20・ミニじしん（闘無）40）
BROCKS_RHYHORN = "PMCG5-049"  # タケシのサイホーン（HP 70・闘・弱点 草・抵抗力 雷 -30・にげる 3。ドリルタックル（闘無）70）
LT_SURGES_SPEAROW = "PMCG5-057"  # マチスのオニスズメ（HP 50・無色・弱点 雷・抵抗力 闘 -30・にげる 0。ふきとばし（無）10・かまいたち（無無）40）
GIOVANNIS_NIDORAN_F = "PMCG6-003"  # サカキのニドラン♀（HP 50・草・弱点 超・にげる 1。つき（草）20・すてみタックル（無無）30）
BLAINES_RHYHORN = "PMCG6-058"  # カツラのサイホーン（HP 60・闘・弱点 草・抵抗力 雷 -30・にげる 2。ホーンアタック（闘）30・かけぬける（無無無）20）
BLAINES_DODUO = "PMCG6-064"  # カツラのドードー（HP 50・無色・弱点 雷・抵抗力 闘 -30・にげる 0。けりつける（無）20・しかえし（無無）10×）
V0_33_POKEMON = (DRAGONAIR, FOSSIL_GOLDUCK, DARK_VAPOREON, LT_SURGES_MAGNEMITE_30, SABRINAS_VENONAT, NIDORAN_M, NIDORINO, CLOYSTER, DARK_RATICATE,
                 BROCKS_DIGLETT, BROCKS_RHYHORN, LT_SURGES_SPEAROW, GIOVANNIS_NIDORAN_F, BLAINES_RHYHORN, BLAINES_DODUO)
# v0.34（バリアーに対するコインの見直し・ダメージのあとの決定をまたぐ処理と合わせて加えた 14 枚と保留の 1 枚。docs/barrier-resume-coin-bonus-v0.34.md）
RAPIDASH = "PMCG2-019"  # ギャロップ（第2弾。ポニータから進化。HP 70・炎・弱点 水・にげる 0。ふみつけ（無無）20+・こうそくいどう（炎炎無）30）
FLAREON = "PMCG2-020"  # ブースター（第2弾。イーブイから進化。HP 70・炎・弱点 水・にげる 1。でんこうせっか（無無）10+・かえんほうしゃ（炎炎無無）60）
VAPOREON = "PMCG2-023"  # シャワーズ（第2弾。イーブイから進化。HP 80・水・弱点 雷・にげる 1。でんこうせっか（無無）10+・みずでっぽう（水水無）30+）
JOLTEON = "PMCG2-026"  # サンダース（第2弾。イーブイから進化。HP 70・雷・弱点 闘・にげる 1。でんこうせっか（無無）10+・ミサイルばり（雷雷無）20×）
ELECTABUZZ = "PMCG1-041"  # エレブー（第1弾。HP 70・雷・弱点 闘・にげる 2。でんきショック（雷）10・かみなりパンチ（雷無）30+）
TAUROS = "PMCG2-042"  # ケンタロス（第2弾。HP 60・無色・弱点 闘・抵抗力 超 -30・にげる 2。ふみつけ（無無）20+・いかりくるう（無無無）20+）
BROCKS_VULPIX = "PMCG5-018"  # タケシのロコン（HP 40・炎・弱点 水・にげる 1。ほのお（炎）20・でんこうせっか（無無）10+）。VULPIX・BLAINES_VULPIX とは別の名前
GIOVANNIS_PINSIR = "PMCG6-024"  # サカキのカイロス（HP 70・草・弱点 炎・にげる 2。きあいばさみ（草無）10+・うしろなげ（草無無）40）。PINSIR とは別のカード
BLAINES_KANGASKHAN = "PMCG6-069"  # カツラのガルーラ（HP 80・無色・弱点 闘・抵抗力 超 -30・にげる 3。こどもパンチ（無）10・おやこパンチ（無無無）30+）
KOFFING = "PMCG1-006"  # ドガース（第1弾。HP 50・草・弱点 超・にげる 1。くさいガス（草草）10）。ROCKET_KOFFING とは別のカード
NIDOKING = "PMCG1-013"  # ニドキング（第1弾。ニドリーノから進化。HP 90・草・弱点 超・にげる 3。あばれる（草無無）30+・どくどく（草草草）20）
EXEGGUTOR = "PMCG2-012"  # ナッシー（第2弾。タマタマから進化。HP 80・草・弱点 炎・にげる 3。テレポート（超）・たまなげMAX（無）20×）
KANGASKHAN = "PMCG2-046"  # ガルーラ（第2弾。保留。登録しない。こどものおつかい（無）・れんぞくパンチ（無無無無）20×）
CUBONE = "PMCG2-029"  # カラカラ（第2弾。HP 40・闘・弱点 草・抵抗力 雷 -30・にげる 1。なきつく（無）・いかり（闘闘）10+）
MAROWAK = "PMCG2-032"  # ガラガラ（第2弾。カラカラから進化。HP 60・闘・弱点 草・抵抗力 雷 -30・にげる 1。ほねブーメラン（闘闘）30×・たすけをよぶ（闘闘無））
V0_34_POKEMON = (RAPIDASH, FLAREON, VAPOREON, JOLTEON, ELECTABUZZ, TAUROS, BROCKS_VULPIX, GIOVANNIS_PINSIR, BLAINES_KANGASKHAN, KOFFING, NIDOKING,
                 EXEGGUTOR, CUBONE, MAROWAK)  # 対応にした 14 枚（ガルーラは保留）
V0_34_POOL = (RAPIDASH, FLAREON, VAPOREON, JOLTEON, ELECTABUZZ, TAUROS, BROCKS_VULPIX, GIOVANNIS_PINSIR, BLAINES_KANGASKHAN, KOFFING, NIDOKING,
              EXEGGUTOR, KANGASKHAN, CUBONE, MAROWAK)  # 写しの組 pool_v0_34（保留のガルーラを含む 15 枚）
# v0.35（docs/coin-groups-damage-order-v0.35.md）: kyuura データの採用で加えた 5 枚
LT_SURGES_RATTATA = "PMCG5-056"  # マチスのコラッタ（リーダーズスタジアム。HP 30・無色・弱点 闘・抵抗力 超 -30・にげる 0。きあいだめ（無）・でんこうせっか（無無）10+）
LT_SURGES_RATICATE = "PMCG5-059"  # マチスのラッタ（マチスのコラッタから進化。HP 60・無色・弱点 闘・抵抗力 超 -30・にげる 1。きあいだめ（無）・すてみタックル（無無）40）
MISTYS_POLIWAG = "PMCG5-022"  # カスミのニョロモ（リーダーズスタジアム。HP 50・水・弱点 草・にげる 1。あわあわ（水）20・ドわすれ（水水））
MISTYS_POLIWHIRL = "PMCG5-029"  # カスミのニョロゾ（カスミのニョロモから進化。HP 70・水・弱点 草・にげる 2。はかいのうず（水無）20・ウォーターパンチ（無無無）30+）
BLAINES_TAUROS = "PMCG6-065"  # カツラのケンタロス（闇からの挑戦。HP 70・無色・弱点 闘・抵抗力 超 -30・にげる 2。3ぼんのしっぽ（無）10×・ぜんりょくとっしん（無無無）20×）
V0_35_POKEMON = (LT_SURGES_RATTATA, LT_SURGES_RATICATE, MISTYS_POLIWAG, MISTYS_POLIWHIRL, BLAINES_TAUROS)  # 対応にした 5 枚（写しの組 pool_v0_35 と同じ）
# v0.36（docs/sand-attack-retreat-lock-v0.36.md）: kyuura データの採用で加えた 11 枚
SANDSHREW = "PMCG1-051"  # サンド（第1弾。HP 40・闘・弱点 草・抵抗力 雷 -30・にげる 1。すなかけ（闘）10。効果は1回できえる）
SANDSLASH = "PMCG3-036"  # サンドパン（化石の秘密。サンドから進化。HP 70・闘・弱点 草・抵抗力 雷 -30・にげる 1。きりさく（無無）20・みだれひっかき（闘闘）20×）
FOSSIL_MAGMAR = "PMCG3-008"  # ブーバー（化石の秘密。HP 70・炎・弱点 水・にげる 1。えんまく（炎）10・スモッグ（炎炎）20）。MAGMAR（第1弾）とは別のカード
HORSEA = "PMCG3-014"  # タッツー（化石の秘密。HP 40・水・弱点 雷・にげる 0。えんまく（水）10）
MISTYS_HORSEA = "PMCG5-025"  # カスミのタッツー（リーダーズスタジアム。HP 40・水・弱点 雷・にげる 0。たいあたり（水）10・えんまく（水水）20）
KOGAS_PIDGEY = "PMCG6-062"  # キョウのポッポ（闇からの挑戦。HP 50・無色・弱点 雷・抵抗力 闘 -30・にげる 1。つつく（無）10・すなかけ（無無無）20）
DARK_JOLTEON = "PMCG4-029"  # わるいサンダース（ロケット団。イーブイから進化。HP 50・雷・弱点 闘・にげる 1。サンダーフラッシュ（雷）20・サンダーアタック（雷雷無）30）
MISTYS_SEEL = "PMCG5-023"  # カスミのパウワウ（リーダーズスタジアム。HP 50・水・弱点 雷・にげる 1。アイスバーン（水）10・しんきろう（水無）10）
LT_SURGES_FEAROW = "PMCG5-064"  # マチスのオニドリル（マチスのオニスズメから進化。HP 70・無色・弱点 雷・抵抗力 闘 -30・にげる 0。マシンガンドリル（無無）10×・わしづかみ（無無無）30）
KOGAS_KOFFING = "PMCG6-015"  # キョウのドガース（闇からの挑戦。HP 50・草・弱点 超・にげる 1。えんまく（草）10・くもがくれガス（草無）30）。KOFFING とは別のカード
ERIKAS_BELLSPROUT = "PMCG5-005"  # エリカのマダツボミ（リーダーズスタジアム。HP 50・草・弱点 炎・にげる 1。へなへなタックル（無）20）。BELLSPROUT とは別のカード
V0_36_POKEMON = (SANDSHREW, SANDSLASH, FOSSIL_MAGMAR, HORSEA, MISTYS_HORSEA, KOGAS_PIDGEY, DARK_JOLTEON, MISTYS_SEEL, LT_SURGES_FEAROW, KOGAS_KOFFING,
                 ERIKAS_BELLSPROUT)  # 対応にした 11 枚（写しの組 pool_v0_36 と同じ）
# v0.37（docs/fifteen-reused-effects-v0.37.md）: 15 枚（化石の秘密のベトベターは v0.8 の過去の原典照合の記録で、ほかの 14 枚は kyuura データの採用）
RHYHORN = "PMCG2-030"  # サイホーン（第2弾。HP 70・闘・弱点 草・抵抗力 雷 -30・にげる 3。にらみつける（無）・つのでつく（闘無無）30）。BROCKS_RHYHORN などとは別のカード
ROCKET_EEVEE = "PMCG4-049"  # イーブイ（ロケット団。HP 40・無色・弱点 闘・抵抗力 超 -30・にげる 1。たいあたり（無）10・すなかけ（無無）10）。EEVEE（第2弾）とは別のカード
BROCKS_SANDSHREW = "PMCG5-043"  # タケシのサンド（リーダーズスタジアム。HP 50・闘・弱点 草・抵抗力 雷 -30・にげる 1。すなじごく（闘闘）20）。SANDSHREW とは別のカード
SABRINAS_DROWZEE = "PMCG6-045"  # ナツメのスリープ（闇からの挑戦。HP 50・超・弱点 超・にげる 1。あんじをかける（超）・ずつき（無無）20）。DROWZEE とは別のカード
RAICHU = "PMCG1-038"  # ライチュウ（第1弾。ピカチュウから進化。HP 80・雷・弱点 闘・にげる 1。こうそくいどう（雷無無）20・かみなり（雷雷雷無）60）
DUGTRIO = "PMCG1-056"  # ダグトリオ（第1弾。ディグダから進化。HP 70・闘・弱点 草・抵抗力 雷 -30・にげる 2。きりさく（闘闘無）40・じしん（闘闘闘闘）70）
POLIWHIRL = "PMCG1-028"  # ニョロゾ（第1弾。ニョロモから進化。HP 60・水・弱点 草・にげる 1。ドわすれ（水水）・おうふくびんた（水水無）30×）
POLIWRATH = "PMCG1-033"  # ニョロボン（第1弾。ニョロゾから進化する 2 進化。HP 90・水・弱点 草・にげる 3。みずでっぽう（水水無）30+・うずしお（水水無無）40）
FOSSIL_EKANS = "PMCG3-001"  # アーボ（化石の秘密。HP 40・草・弱点 超・にげる 1。どくえき（草）・まきつく（草無）20）。ROCKET_EKANS とは別のカード
BROCKS_ONIX = "PMCG5-048"  # タケシのイワーク（リーダーズスタジアム。HP 100・闘・弱点 草・にげる 3。うなりごえ（無）・いわおとし（闘闘無）30）
MEOWTH = "PMCG2-036"  # ニャース（第2弾。HP 50・無色・弱点 闘・抵抗力 超 -30・にげる 1。ねこにこばん（無無）10）。GIOVANNIS_MEOWTH とは別のカード
KOGAS_TANGELA = "PMCG6-009"  # キョウのモンジャラ（闇からの挑戦。HP 50・草・弱点 炎・にげる 2。ねむりごな（草）10・つるでさがす（草無））。TANGELA とは別のカード
MISTYS_MAGIKARP = "PMCG5-028"  # カスミのコイキング（リーダーズスタジアム。HP 30・水・弱点 雷・にげる 1。しんだふり（無）・はねる（無）10）。MAGIKARP とは別のカード
PERSIAN = "PMCG2-039"  # ペルシアン（第2弾。ニャースから進化。HP 70・無色・弱点 闘・抵抗力 超 -30・にげる 0。ひっかく（無無）20・かみつく（無無無）30）
V0_37_ADOPTED = (RHYHORN, ROCKET_EEVEE, BROCKS_SANDSHREW, SABRINAS_DROWZEE, RAICHU, DUGTRIO, POLIWHIRL, POLIWRATH, FOSSIL_EKANS, BROCKS_ONIX, MEOWTH,
                 KOGAS_TANGELA, MISTYS_MAGIKARP, PERSIAN)  # kyuura データの採用の記録で加えた 14 枚
PARASECT = "PMCG2-010"  # パラセクト（v0.4a で対応。パラスから進化する 1 進化。HP 60・草・弱点 炎・にげる 1。キノコのほうし・きりさく 30）
DEWGONG = "PMCG1-030"  # ジュゴン（v0.4a で対応。パウワウから進化する 1 進化。HP 80・水・弱点 雷・にげる 3。オーロラビーム 50・れいとうビーム 30）
METAPOD = "PMCG1-003"  # トランセル（v0.4b。キャタピーから進化。かたまる・しびれごな）
KAKUNA = "PMCG1-009"  # コクーン（v0.4b。ビードルから進化。かたまる・どくのこな）
BEEDRILL = "PMCG1-012"  # スピアー（v0.4c。コクーンから進化する 2 進化。HP 80・草・弱点 炎・抵抗力 闘 -30・にげる 0。ダブルニードル・どくばり 40）
BUTTERFREE = "PMCG2-007"  # バタフリー（v0.4d。トランセルから進化する 2 進化。HP 70・草・弱点 炎・抵抗力 闘 -30・にげる 0。ふきとばし 20・メガドレイン 40）
VENUSAUR = "PMCG1-011"  # フシギバナ（v0.5。フシギソウから進化する 2 進化。HP 100・草・弱点 炎・にげる 2。ポケモンパワー エナジートランス・ソーラービーム 60）
IVYSAUR = "PMCG1-008"  # フシギソウ（v0.5。フシギダネから進化する 1 進化。HP 60・草・弱点 炎・にげる 1。つるのムチ 30・どくのこな 20）
BULBASAUR = "PMCG1-001"  # フシギダネ（v0.5。HP 40・草・弱点 炎・にげる 1。やどりぎのタネ 20）
# カメックス（v0.6。カメールから進化する 2 進化。HP 100・水・弱点 雷・にげる 3。ポケモンパワー あまごい・ハイドロポンプ 40+）。
# v0.5 では「実装を登録していないポケモンパワーを持つので未対応」の参照カードだった（v0.6 で対応にしたので、その役はフーディンへ）
BLASTOISE = "PMCG1-032"
WARTORTLE = "PMCG1-027"  # カメール（v0.6。ゼニガメから進化する 1 進化。HP 70・水・弱点 雷・にげる 1。からにこもる・かみつく 40）
SQUIRTLE = "PMCG1-023"  # ゼニガメ（v0.6。HP 40・水・弱点 雷・にげる 1。あわ 10・からにこもる）
# フーディン（v0.7。ユンゲラーから進化する 2 進化。HP 80・超・弱点 超・にげる 3。ポケモンパワー ダメージスワップ・あやしいひかり 30）。
# v0.6 では「実装を登録していないポケモンパワーを持つので未対応」の参照カードだった（v0.7 で対応にしたので、その役はリザードンへ）
ALAKAZAM = "PMCG1-049"
KADABRA = "PMCG1-046"  # ユンゲラー（v0.7。ケーシィから進化する 1 進化。HP 60・超・弱点 超・にげる 3。じこさいせい・ちょうねんりき 50）
ABRA = "PMCG1-043"  # ケーシィ（v0.7。HP 30・超・弱点 超・にげる 0。ねんりき 10）
GRIMER = "PMCG4-004"  # ロケット団のベトベター（v0.8。HP 40・草・弱点 超・にげる 1。どくガス・ねばりつく 10+）
MUK = "PMCG3-007"  # ベトベトン（v0.8。ベトベターから進化する 1 進化。HP 70・草・弱点 超・にげる 2。かがくへんかガス・ヘドロこうげき 30）
# 化石の秘密のベトベター（v0.8〜v0.36 は参照カード（「ちいさくなる」が未実装でデッキに入らない）。v0.37 で対応にした。HP 50・草・弱点 超・にげる 1。
# ベトベト（無）10・ちいさくなる（草））
FOSSIL_GRIMER = "PMCG3-003"
V0_37_POKEMON = V0_37_ADOPTED[:1] + (FOSSIL_GRIMER,) + V0_37_ADOPTED[1:]  # 対応にした 15 枚（写しの組 pool_v0_37 の 14 枚と化石の秘密のベトベター）
# v0.38（docs/bench-switch-combined-v0.38.md）。控えへのダメージ・入れ替え・同じコインの複数の効果・軽減・山札にもどる効果の 15 枚（kyuura データの採用）。
# 同じ名前の別のカード（タケシのロコン PMCG5-018・キョウのポッポ PMCG6-062・第1弾のケーシィ PMCG1-043）と取りちがえない
ARTICUNO = "PMCG3-023"  # フリーザー（化石の秘密。HP 70・水・弱点なし・抵抗力 闘 -30・にげる 2。フリーズドライ（水水水）30・ふぶき（水水水水）50）
HITMONLEE = "PMCG3-039"  # サワムラー（化石の秘密。HP 60・闘・弱点 超・にげる 1。のびるキック（闘闘）・とびひざげり（闘闘闘）50）
ERIKAS_TANGELA = "PMCG5-006"  # エリカのモンジャラ（リーダーズスタジアム。HP 60・草・弱点 炎・にげる 2。つるでうつ（草）10・のびるつる（草草無））。TANGELA・KOGAS_TANGELA とは別の名前
BROCKS_VULPIX_50 = "PMCG5-017"  # タケシのロコン（リーダーズスタジアム。HP 50・炎・弱点 水・にげる 1。みつめる（無）・ほのおのわ（炎炎）20）。BROCKS_VULPIX（PMCG5-018）とは別のカード
BROCKS_GOLBAT = "PMCG5-008"  # タケシのゴルバット（タケシのズバットから進化。HP 70・草・弱点 超・抵抗力 闘 -30・にげる 1。スピードひこう（無）20・かいてんひこう（無無無））
ARBOK = "PMCG3-004"  # アーボック（化石の秘密。アーボから進化。HP 60・草・弱点 超・にげる 2。いかくこうげき（草）10・どくのきば（草草無）20）
RHYDON = "PMCG2-033"  # サイドン（第2弾。サイホーンから進化。HP 100・闘・弱点 草・抵抗力 雷 -30・にげる 3。つのでつく（闘無無）30・げきとつ（闘闘闘闘）50）
BLAINES_PONYTA = "PMCG6-028"  # カツラのポニータ（闇からの挑戦。HP 50・炎・弱点 水・にげる 1。けりにげ（無無）20）。PONYTA とは別の名前
BLAINES_RAPIDASH = "PMCG6-030"  # カツラのギャロップ（カツラのポニータから進化。HP 70・炎・弱点 水・にげる 0。ほのおのたてがみ（炎）20・ふみあらす（炎無無）30+）
KOGAS_PIDGEOTTO = "PMCG6-070"  # キョウのピジョン（キョウのポッポから進化。HP 60・無色・弱点 雷・抵抗力 闘 -30・にげる 0。クイックターン（無無無）30×・こうそくひこう（無無無無）10+）
KOGAS_WEEDLE = "PMCG6-001"  # キョウのビードル（闇からの挑戦。HP 40・草・弱点 炎・にげる 1。チクチクさす（無）10・きけんなはり（草無）10）。WEEDLE とは別の名前
GIOVANNIS_NIDORINA = "PMCG6-012"  # サカキのニドリーナ（サカキのニドラン♀から進化。HP 80・草・弱点 超・にげる 2。どくばりタックル（草無）30・のしかかり（草無無）20）
SABRINAS_PORYGON = "PMCG6-066"  # ナツメのポリゴン（闇からの挑戦。HP 40・無色・弱点 闘・抵抗力 超 -30・にげる 1。とがる（無）10・バリアアタック（無無）20）
ROCKET_ABRA = "PMCG4-031"  # ケーシィ（ロケット団。HP 40・超・弱点 超・にげる 1。いなくなる（超）・ねんりき（超）10）。ABRA（PMCG1-043）とは別のカード
KOGAS_PIDGEY_40 = "PMCG6-067"  # キョウのポッポ（闇からの挑戦。HP 40・無色・弱点 雷・抵抗力 闘 -30・にげる 1。でんれい（無）・つばさでうつ（無無）20）。KOGAS_PIDGEY（PMCG6-062）とは別のカード
V0_38_POKEMON = (ARTICUNO, HITMONLEE, ERIKAS_TANGELA, BROCKS_VULPIX_50, BROCKS_GOLBAT, ARBOK, RHYDON, BLAINES_PONYTA, BLAINES_RAPIDASH, KOGAS_PIDGEOTTO,
                 KOGAS_WEEDLE, GIOVANNIS_NIDORINA, SABRINAS_PORYGON, ROCKET_ABRA, KOGAS_PIDGEY_40)  # 写しの組 pool_v0_38 の並び
# v0.39（docs/selfdestruct-spread-count-v0.39.md）。同じ名前の別のカード（MAGNEMITE と ROCKET_MAGNEMITE、MAGNETON と FOSSIL_MAGNETON、JUNGLE_PIKACHU と
# PIKACHU、FOSSIL_RAICHU と RAICHU、KOGAS_KOFFING_40 と KOGAS_KOFFING）と取りちがえない
MAGNEMITE = "PMCG1-036"  # コイル（第1弾。HP 40・雷・弱点 闘・にげる 1。でんじは（雷）10・じばく（雷無）40）
MAGNETON = "PMCG1-039"  # レアコイル（第1弾。コイルから進化。HP 60・雷・弱点 闘・にげる 1。でんじは（雷雷無）30・じばく（雷雷無無）80）
FOSSIL_WEEZING = "PMCG3-006"  # マタドガス（化石の秘密。ドガースから進化。HP 60・草・弱点 超・にげる 1。スモッグ（草草）20・じばく（草草無）60）
FOSSIL_MAGNETON = "PMCG3-025"  # レアコイル（化石の秘密。コイルから進化。HP 80・雷・弱点 闘・にげる 2。ソニックブーム（雷無）20・じばく（雷雷雷雷）100）
JUNGLE_PIKACHU = "PMCG2-024"  # ピカチュウ（第2弾。HP 50・雷・弱点 闘・にげる 1。スパーク（雷雷）20）。PIKACHU（PMCG1-035）とは別のカード
FOSSIL_RAICHU = "PMCG3-024"  # ライチュウ（化石の秘密。ピカチュウから進化。HP 90・雷・弱点 闘・にげる 1。ギガスパーク（雷雷雷雷）30）。RAICHU（PMCG1-038）とは別のカード
ELECTRODE = "PMCG2-025"  # マルマイン（第2弾。ビリリダマから進化。HP 90・雷・弱点 闘・にげる 1。たいあたり（無無）20・ビリビリ（雷雷雷）20）
KOGAS_KOFFING_40 = "PMCG6-008"  # キョウのドガース（闇からの挑戦。HP 40・草・弱点 超・にげる 1。おならガス（草）10）。KOGAS_KOFFING（PMCG6-015）とは別のカード
MISTYS_POLIWRATH = "PMCG6-039"  # カスミのニョロボン（闇からの挑戦。カスミのニョロゾから進化する 2 進化。HP 90・水・弱点 草・にげる 3。ウォーターリング（水水無無）30）
ROCKET_MAGNEMITE = "PMCG4-026"  # コイル（ロケット団。HP 40・雷・弱点 闘・にげる 1。たいあたり（無無）20・ちょくれつじりょく（雷無）10+）。MAGNEMITE とは同じ名前の別のカード
WIGGLYTUFF = "PMCG2-045"  # プクリン（第2弾。プリンから進化。HP 80・無色・弱点 闘・抵抗力 超 -30・にげる 2。こもりうた（無）・ともだちのわ（無無無）10+）
NIDOQUEEN = "PMCG2-013"  # ニドクイン（第2弾。ニドリーナから進化する 2 進化。HP 90・草・弱点 超・にげる 3。ラブラブアタック（草無）20+・メガトンパンチ（草草無無）50）
KOGAS_WEEZING = "PMCG6-016"  # キョウのマタドガス（闇からの挑戦。キョウのドガースから進化。HP 70・草・弱点 超・にげる 2。とつぜんばくはつ（草草）10+・どくどくガス（草草無）20）
PIDGEY = "PMCG1-059"  # ポッポ（第1弾。HP 40・無色・弱点 雷・抵抗力 闘 -30・にげる 1。かぜおこし（無無）10）
ERIKAS_PARAS = "PMCG5-004"  # エリカのパラス（リーダーズスタジアム。HP 50・草・弱点 炎・にげる 1。はさむ（無）10・きけんなほうし（草草））。PARAS とは別の名前のカード
V0_39_POKEMON = (MAGNEMITE, MAGNETON, FOSSIL_WEEZING, FOSSIL_MAGNETON, JUNGLE_PIKACHU, FOSSIL_RAICHU, ELECTRODE, KOGAS_KOFFING_40, MISTYS_POLIWRATH,
                 ROCKET_MAGNEMITE, WIGGLYTUFF, NIDOQUEEN, KOGAS_WEEZING, PIDGEY, ERIKAS_PARAS)  # 写しの組 pool_v0_39 の並び
# v0.40（docs/count-condition-switch-return-v0.40.md）。場の数・条件付きの効果・入れ替え・カードの移動の 15 枚
KOGAS_ZUBAT = "PMCG6-005"  # キョウのズバット（闇からの挑戦。HP 40・草・弱点 超・抵抗力 闘 -30・にげる 0。むれでおそう（草無）10×）。ZUBAT・BROCKS_ZUBAT とは別の名前
KOGAS_GOLBAT = "PMCG6-014"  # キョウのゴルバット（キョウのズバットから進化。HP 60・草・弱点 超・抵抗力 闘 -30・にげる 0。かみつく（無無）20・ひどいおんぱ（草草草）30）
DARK_WEEZING = "PMCG4-011"  # わるいマタドガス（ロケット団。ドガースから進化。HP 60・草・弱点 超・にげる 1。みんなでばくはつ（草無）20×・しびれガス（草草草）20）
DARK_HYPNO = "PMCG4-037"  # わるいスリーパー（ロケット団。スリープから進化。HP 60・超・弱点 超・にげる 2。サイコパンチ（超）20・ベンチをあやつる（超超無）20×）
GIOVANNIS_NIDORAN_M = "PMCG6-004"  # サカキのニドラン♂（闇からの挑戦。HP 40・草・弱点 超・にげる 1。にどげり（無）10×・いかりのいちげき（草）30）。NIDORAN_M とは別の名前
GIOVANNIS_NIDORINO = "PMCG6-013"  # サカキのニドリーノ（サカキのニドラン♂から進化。HP 70・草・弱点 超・にげる 2。つのでえぐる（草無無）20+）
GIOVANNIS_NIDOKING = "PMCG6-021"  # サカキのニドキング（サカキのニドリーノから進化する 2 進化。HP 120・草・弱点 超・にげる 3。すごむ（草）・ローリングアタック（草草草無）40+）
GIOVANNIS_NIDOQUEEN = "PMCG6-020"  # サカキのニドクイン（サカキのニドリーナから進化する 2 進化。HP 100・草・弱点 超・にげる 3。メガトンキック（草草無）40・ラブラリアット（草草無無）50+）
DARK_MACHOKE = "PMCG4-042"  # わるいゴーリキー（ロケット団。ワンリキーから進化。HP 60・闘・弱点 超・にげる 2。ひきずりだす（闘闘無）20・なぐりとばす（闘闘無）30）
DARK_MACHAMP = "PMCG4-044"  # わるいカイリキー（わるいゴーリキーから進化する 2 進化。HP 70・闘・弱点 超・にげる 3。メガトンパンチ（闘闘）30・つまみだす（闘闘闘無））
ERIKAS_WEEPINBELL = "PMCG5-011"  # エリカのウツドン（エリカのマダツボミから進化。HP 60・草・弱点 炎・にげる 1。よだれ（草）10・さそってとかす（草草）20）。WEEPINBELL とは別の名前
MISTYS_SEADRA = "PMCG5-034"  # カスミのシードラ（カスミのタッツーから進化。HP 70・水・弱点 雷・にげる 1。しっぽのムチ（水）20・きぜつばり（水水水）30+）
BROCKS_MANKEY = "PMCG5-045"  # タケシのマンキー（リーダーズスタジアム。HP 40・闘・弱点 超・にげる 0。ひまつぶし（無）・からてチョップ（闘無）40-）。MANKEY とは別の名前
MANKEY = "PMCG4-039"  # マンキー（ロケット団。HP 40・闘・弱点 超・にげる 0。いたずら（無）・おこる（闘無）20+）
PRIMEAPE = "PMCG2-031"  # オコリザル（第2弾。マンキーから進化。HP 70・闘・弱点 超・にげる 1。みだれひっかき（闘闘）20×・あばれまわる（闘闘無）50）
V0_40_POKEMON = (KOGAS_ZUBAT, KOGAS_GOLBAT, DARK_WEEZING, DARK_HYPNO, GIOVANNIS_NIDORAN_M, GIOVANNIS_NIDORINO, GIOVANNIS_NIDOKING, GIOVANNIS_NIDOQUEEN,
                 DARK_MACHOKE, DARK_MACHAMP, ERIKAS_WEEPINBELL, MISTYS_SEADRA, BROCKS_MANKEY, MANKEY, PRIMEAPE)  # 写しの組 pool_v0_40 の並び
# v0.41（docs/heal-counter-status-v0.41.md）。回復・カウンターの移動・特殊状態の変化を中心とする 15 枚
GLOOM = "PMCG2-009"  # クサイハナ（第2弾。ナゾノクサから進化。HP 60・草・弱点 炎・にげる 1。どくのこな（草）・くさいにおい（草草）20）
VICTREEBEL = "PMCG2-016"  # ウツボット（第2弾。ウツドンから進化する 2 進化。HP 80・草・弱点 炎・にげる 2。さそうかおり（草）・ようかいえき（草草）20）
SEADRA = "PMCG3-020"  # シードラ（第3弾。タッツーから進化。HP 60・水・弱点 雷・にげる 1。みずでっぽう（水無）20+・こうそくいどう（水無無）20）。MISTYS_SEADRA とは別の名前
DARK_PERSIAN = "PMCG4-048"  # わるいペルシアン（ロケット団。ニャースから進化。HP 60・無色・弱点 闘・抵抗力 超 -30・にげる 0。ゆうわく（無）・どくのつめ（無無）10）
BLAINES_MOLTRES = "PMCG6-035"  # カツラのファイヤー（闇からの挑戦。HP 90・炎・弱点なし・抵抗力 闘 -30・にげる 3。ひのとり（炎炎炎炎炎）90）。MOLTRES・ROCKETS_MOLTRES とは別の名前
ROCKET_SLOWPOKE = "PMCG4-032"  # ヤドン（ロケット団。HP 50・超・弱点 超・にげる 1。ひなたぼっこ（無）・ずつき（超）10）。SLOWPOKE（化石の秘密）とは同じ名前の別のカード
ERIKAS_ODDISH = "PMCG5-002"  # エリカのナゾノクサ（リーダーズスタジアム。HP 50・草・弱点 炎・にげる 1。ちょっとすいとる（草）10・たまにすいとる（草無）20）
ERIKAS_ODDISH_40 = "PMCG5-003"  # エリカのナゾノクサ（リーダーズスタジアム。HP 40・草・弱点 炎・にげる 1。へんなこな（草）10）。ERIKAS_ODDISH とは同じ名前の別のカード
ERIKAS_GLOOM = "PMCG5-009"  # エリカのクサイハナ（エリカのナゾノクサから進化。HP 60・草・弱点 炎・にげる 1。ヒーリングかふん（草）・ミラクルかふん（草草草）30）
SABRINAS_PSYDUCK = "PMCG6-036"  # ナツメのコダック（闇からの挑戦。HP 50・水・弱点 雷・にげる 1。ひっかく（無）10・こまったねんりき（超）20）。PSYDUCK・MISTYS_PSYDUCK とは別の名前
SABRINAS_GOLDUCK = "PMCG6-038"  # ナツメのゴルダック（ナツメのコダックから進化。HP 70・水・弱点 雷・にげる 2。ダメージシフト（超超）・ウォーターシュート（水無無）20+）
SABRINAS_VENOMOTH = "PMCG6-022"  # ナツメのモルフォン（ナツメのコンパンから進化。HP 60・草・弱点 炎・抵抗力 闘 -30・にげる 0。かいふくりんぷん（草）・げんかくおんぱ（超）10）
SABRINAS_SLOWBRO = "PMCG6-048"  # ナツメのヤドラン（ナツメのヤドンから進化。HP 70・超・弱点 超・にげる 2。いねむり（超）・きあいずつき（超無無）40）
ERIKAS_JIGGLYPUFF = "PMCG5-058"  # エリカのプリン（リーダーズスタジアム。HP 50・無色・弱点 闘・抵抗力 超 -30・にげる 1。みんなでかいふく（無）・やさしいパンチ（無無）40-）
ROCKETS_MEWTWO = "PMCG6-055"  # R団のミュウツー（闇からの挑戦。HP 70・超・弱点 超・にげる 2。チェンジダメージ（超）・さいみんはどう（超超）20・サイコバーン（超超超無）60）
V0_41_POKEMON = (GLOOM, VICTREEBEL, SEADRA, DARK_PERSIAN, BLAINES_MOLTRES, ROCKET_SLOWPOKE, ERIKAS_ODDISH, ERIKAS_ODDISH_40, ERIKAS_GLOOM, SABRINAS_PSYDUCK,
                 SABRINAS_GOLDUCK, SABRINAS_VENOMOTH, SABRINAS_SLOWBRO, ERIKAS_JIGGLYPUFF, ROCKETS_MEWTWO)  # 写しの組 pool_v0_41 の並び
# v0.42（docs/power-decisions-v0.42.md）: 回復・カウンター操作と、特殊能力を持つ進化系統を中心とする 15 枚（kyuura データの採用）
SABRINAS_JYNX = "PMCG6-052"  # ナツメのルージュラ（闇からの挑戦。HP 60・超・弱点 超・にげる 1。よいおこない（超）・だきつく（超無）20）。JYNX（第1弾）とは別の名前
VILEPLUME = "PMCG2-014"  # ラフレシア（第2弾。クサイハナから進化。HP 80・草・弱点 炎・にげる 2。［ヒーリング］・はなびらのまい（草草草）40×）
SLOWBRO = "PMCG3-028"  # ヤドラン（化石の秘密。ヤドンから進化。HP 60・超・弱点 超・にげる 1。［へんなこうどう］・ねんりき（超超）20）。SABRINAS_SLOWBRO とは別の名前
GENGAR = "PMCG3-031"  # ゲンガー（化石の秘密。ゴーストから進化。HP 80・超・抵抗力 闘 -30・にげる 1。［のろい］・ナイトヘッド（超超超）30）
ERIKAS_VILEPLUME = "PMCG5-014"  # エリカのラフレシア（リーダーズスタジアム。エリカのクサイハナから進化。HP 80・草・弱点 炎・にげる 2。［ぼうぎょかふん］・メガドレイン（草草草）30）
SABRINAS_ABRA = "PMCG6-043"  # ナツメのケーシィ（闇からの挑戦。HP 40・超・弱点 超・にげる 0。エネループ（超）20）。ABRA・ROCKET_ABRA とは別の名前
SABRINAS_KADABRA = "PMCG6-047"  # ナツメのユンゲラー（ナツメのケーシィから進化。HP 70・超・弱点 超・にげる 1。ライフダウン（超）・サイコショット（超無無）30）
DRAGONITE = "PMCG3-043"  # カイリュー（化石の秘密。ハクリューから進化。HP 100・無色・抵抗力 闘 -30・にげる 1。［かけつける］・たたきつける（無無無無）40×）
ERIKAS_VICTREEBEL = "PMCG5-015"  # エリカのウツボット（エリカのウツドンから進化。HP 80・草・弱点 炎・にげる 2。［かおりのわな］・はっぱカッター（草草草）50）。VICTREEBEL とは別の名前
DARK_KADABRA = "PMCG4-034"  # わるいユンゲラー（ロケット団。ケーシィから進化。HP 50・超・弱点 超・にげる 2。［ぶっしつこうかん］・マインドショック（超超）30）
DARK_ALAKAZAM = "PMCG4-035"  # わるいフーディン（わるいユンゲラーから進化。HP 60・超・弱点 超・にげる 3。テレポートブラスト（超超無）30・マインドショック（超超超）40）
TENTACOOL = "PMCG3-011"  # メノクラゲ（化石の秘密。HP 30・水・弱点 雷・にげる 0。［おくびょう］・ようかいえき（水）10）
TENTACRUEL = "PMCG3-017"  # ドククラゲ（メノクラゲから進化。HP 60・水・弱点 雷・にげる 0。ちょうおんぱ（水）・クラゲばり（水水）10）
ERIKAS_CLEFAIRY = "PMCG5-060"  # エリカのピッピ（リーダーズスタジアム。HP 50・無色・弱点 闘・抵抗力 超 -30・にげる 1。つきのちから（無）・ムーンキック（無無）20）。CLEFAIRY とは別の名前
ERIKAS_CLEFABLE = "PMCG5-065"  # エリカのピクシー（エリカのピッピから進化。HP 70・無色・弱点 闘・抵抗力 超 -30・にげる 2。ようせいのきせき（無）・ムーンインパクト（無無無）30）
V0_42_POKEMON = (SABRINAS_JYNX, VILEPLUME, SLOWBRO, GENGAR, ERIKAS_VILEPLUME, SABRINAS_ABRA, SABRINAS_KADABRA, DRAGONITE, ERIKAS_VICTREEBEL, DARK_KADABRA,
                 DARK_ALAKAZAM, TENTACOOL, TENTACRUEL, ERIKAS_CLEFAIRY, ERIKAS_CLEFABLE)  # 写しの組 pool_v0_42 の並び
# v0.43（docs/declared-entry-powers-v0.43.md）: 宣言して使う特殊能力（6 枚）と、場に出たときに使う特殊能力（3 枚）を持つ 9 枚（kyuura データの採用）
DARK_GLOOM = "PMCG4-006"  # わるいクサイハナ（ロケット団。ナゾノクサから進化。HP 50・草・弱点 炎・にげる 2。［くさいかふん］・どくのこな（草草）10）。GLOOM・ERIKAS_GLOOM とは別の名前
ROCKET_DROWZEE = "PMCG4-033"  # スリープ（ロケット団。HP 50・超・弱点 超・にげる 1。［えんかくさいみん］・あくむ（超無）10）。DROWZEE（第1弾）と同じ名前の別のカード
ROCKET_CHARMANDER = "PMCG4-012"  # ヒトカゲ（ロケット団。HP 40・炎・弱点 水・にげる 1。［ほのおをもらう］・ほのおのしっぽ（炎）20）。CHARMANDER（第1弾）と同じ名前の別のカード
ERIKAS_BELLSPROUT_40 = "PMCG5-010"  # エリカのマダツボミ（リーダーズスタジアム。HP 40・草・弱点 炎・にげる 1。［ようぶんきゅうしゅう］・のびるつる（草））。ERIKAS_BELLSPROUT と同じ名前の別のカード
LT_SURGES_MAGNETON = "PMCG5-040"  # マチスのレアコイル（マチスのコイルから進化。HP 70・雷・弱点 闘・にげる 2。［エナジーチャージ］・メガショック（雷雷雷無）50）
DARK_DRAGONAIR = "PMCG4-052"  # わるいハクリュー（ロケット団。ミニリュウから進化。HP 60・無色・抵抗力 超 -30・にげる 2。［しんかのひかり］・しっぽでつく（無無無）20+）
DARK_GOLBAT = "PMCG4-009"  # わるいゴルバット（ロケット団。ズバットから進化。HP 50・草・弱点 超・抵抗力 闘 -30・にげる 0。［こっそりかみつく］・ふらふらとぶ（草草））
DARK_SLOWBRO = "PMCG4-036"  # わるいヤドラン（ロケット団。ヤドンから進化。HP 60・超・弱点 超・にげる 2。［つりあげる］・きまぐれこうげき（超超）40）
DARK_DRAGONITE = "PMCG4-053"  # わるいカイリュー（ロケット団。わるいハクリューから進化。HP 70・無色・抵抗力 闘 -30・にげる 2。［てしたをよぶ］・きょだいなしっぽ（無無無無）70）
V0_43_POKEMON = (DARK_GLOOM, ROCKET_DROWZEE, ROCKET_CHARMANDER, ERIKAS_BELLSPROUT_40, LT_SURGES_MAGNETON, DARK_DRAGONAIR, DARK_GOLBAT, DARK_SLOWBRO,
                 DARK_DRAGONITE)  # 写しの組 pool_v0_43 の並び
# v0.44（docs/search-evolution-once-attacks-v0.44.md）: 場のポケモンを選ぶ・山札をさがす・山札から進化する・場に出てから 1 回だけ使えるワザ・カードの移動のポケモン
# 14 枚とトレーナー 1 枚（kyuura データの採用）
ROCKET_DIGLETT = "PMCG4-038"  # ディグダ（ロケット団。HP 40・闘・弱点 草・抵抗力 雷 -30・にげる 0。じめんにもぐる（闘）・ひっかく（闘無）20）。DIGLETT（第1弾）と同じ名前の別のカード
ROCKET_MEOWTH = "PMCG4-047"  # ニャース（ロケット団。HP 40・無色・弱点 闘・抵抗力 超 -30・にげる 1。こばんなげ（無無））。MEOWTH（第2弾）・GIOVANNIS_MEOWTH と別のカード
ERIKAS_BULBASAUR = "PMCG5-007"  # エリカのフシギダネ（リーダーズスタジアム。HP 50・草・弱点 炎・にげる 1。ねむりのたね（草）10・おつかい（草草））
MISTYS_STARYU = "PMCG5-027"  # カスミのヒトデマン（リーダーズスタジアム。HP 40・水・弱点 雷・にげる 1。スターブーメラン（水）20）。STARYU（第1弾）とは別の名前
ROCKET_MAGIKARP = "PMCG4-020"  # コイキング（ロケット団。HP 30・水・弱点 雷・にげる 1。はねまわる（無）10・たきのぼりしんか（水水水））。MAGIKARP（第1弾）と同じ名前の別のカード
KOGAS_KAKUNA = "PMCG6-011"  # キョウのコクーン（闇からの挑戦。キョウのビードルから進化。HP 60・草・弱点 炎・にげる 2。［うか］・どくどくえき（草））
KOGAS_BEEDRILL = "PMCG6-018"  # キョウのスピアー（闇からの挑戦。キョウのコクーンから進化。HP 80・草・弱点 炎・抵抗力 闘 -30・にげる 0。しんけいどく（草草）20・ひっさつばり（無無無）70）
FARFETCHD = "PMCG1-063"  # カモネギ（第1弾。HP 50・無色・弱点 雷・抵抗力 闘 -30・にげる 1。ネギでたたく（無）30・ナベでたたく（無無無）30）
GIOVANNIS_MAGIKARP = "PMCG6-037"  # サカキのコイキング（闇からの挑戦。HP 30・水・弱点 雷・にげる 1。りゅうのきおく（水）40・はねまくる（水無）10×）
GIOVANNIS_GYARADOS = "PMCG6-040"  # サカキのギャラドス（闇からの挑戦。サカキのコイキングから進化。HP 90・水・弱点 草・抵抗力 闘 -30・にげる 3。あらしをよぶ（水）・りゅうのたつまき（水水無無）40）
SABRINAS_MR_MIME = "PMCG6-046"  # ナツメのバリヤード（闇からの挑戦。HP 50・超・弱点 超・にげる 1。てじな（無）・ビンタ（超無）20）
BLAINES_MANKEY = "PMCG6-056"  # カツラのマンキー（闇からの挑戦。HP 40・闘・弱点 超・にげる 0。わるいいたずら（無）・みだれひっかき（闘）10×）。MANKEY・BROCKS_MANKEY とは別の名前
BLANK_CHANSEY = "PMCG6-075"  # _____のラッキー（闇からの挑戦。HP 90・無色・弱点 闘・抵抗力 超 -30・にげる 1。ラッキーたまご（無）・ラッキーパンチ（無無無）10+）。名前は kyuura の名前のまま
GIOVANNIS_PERSIAN = "PMCG6-071"  # サカキのペルシアン（闇からの挑戦。サカキのニャースから進化。HP 60・無色・弱点 闘・抵抗力 超 -30・にげる 0。［ボスをよぶ］・おそいかかる（無無無）20+）
GIOVANNI = "PMCG6-095"  # サカキ（闇からの挑戦。トレーナー。選んだ「サカキのポケモン」は、今の番、場に出た番・進化した番でも進化させてよい）
V0_44_POKEMON = (ROCKET_DIGLETT, ROCKET_MEOWTH, ERIKAS_BULBASAUR, MISTYS_STARYU, ROCKET_MAGIKARP, KOGAS_KAKUNA, KOGAS_BEEDRILL, FARFETCHD, GIOVANNIS_MAGIKARP,
                 GIOVANNIS_GYARADOS, SABRINAS_MR_MIME, BLAINES_MANKEY, BLANK_CHANSEY, GIOVANNIS_PERSIAN)  # 写しの組 pool_v0_44 のポケモン（並び）
V0_44_CARDS = V0_44_POKEMON + (GIOVANNI,)  # 写しの組 pool_v0_44 の並び（トレーナーは最後）
# v0.45（docs/conditional-damage-energy-v0.45.md）: 条件つきのダメージ・エネルギーの移動とトラッシュ・受けたダメージを返す効果などのポケモン 15 枚
# （第1弾のゴーストは v0.9 の過去の原典照合の記録、ほかは kyuura データの採用）
MISTYS_HORSEA_50 = "PMCG5-024"  # カスミのタッツー（リーダーズスタジアム。HP 50・水・弱点 雷・にげる 0。スミをかける（水水）20）。MISTYS_HORSEA（PMCG5-025）と同じ名前の別のカード
MISTYS_DEWGONG = "PMCG5-031"  # カスミのジュゴン（リーダーズスタジアム。カスミのパウワウから進化。HP 80・水・弱点 雷・にげる 2。こおりのつぶて（水水）20・とっしん（水無無無）60）
KOGAS_EKANS = "PMCG6-002"  # キョウのアーボ（闇からの挑戦。HP 50・草・弱点 超・にげる 1。とつぜんどく（草）10）
KOGAS_ARBOK = "PMCG6-019"  # キョウのアーボック（闇からの挑戦。キョウのアーボから進化。HP 90・草・弱点 超・にげる 2。どくをためる（草）・ポイズンパワー（草草）20）
KOGAS_GRIMER = "PMCG6-007"  # キョウのベトベター（闇からの挑戦。HP 50・草・弱点 超・にげる 1。ベトベトハンド（草）・ヘドロなげ（草無）20）
DARK_BLASTOISE = "PMCG4-024"  # わるいカメックス（ロケット団。わるいカメールから進化。HP 70・水・弱点 雷・にげる 2。ハイドロキャノン（水水）30+・ロケットタックル（水無無）40）
DARK_MAGNETON = "PMCG4-030"  # わるいレアコイル（ロケット団。コイルから進化。HP 60・雷・弱点 闘・にげる 2。ソニックブーム（無無）20・じりょくせん（雷雷）30）
BLAINES_CHARIZARD = "PMCG6-032"  # カツラのリザードン（闇からの挑戦。カツラのリザードから進化。HP 100・炎・弱点 水・抵抗力 闘 -30・にげる 3。ファイヤーブレス（炎）20+・かえんひこう（炎炎））
ROCKETS_ZAPDOS = "PMCG6-042"  # R団のサンダー（闇からの挑戦。HP 70・雷・抵抗力 闘 -30・にげる 2。プラズマ（雷）20・エレクトロバーン（雷雷雷無）70）。ZAPDOS（第1弾）と別の名前
ONIX = "PMCG1-054"  # イワーク（第1弾。HP 90・闘・弱点 草・にげる 3。いわおとし（闘）10・かたくなる（闘闘））
RATICATE = "PMCG1-062"  # ラッタ（第1弾。コラッタから進化。HP 60・無色・弱点 闘・抵抗力 超 -30・にげる 1。かみつく（無）20・いかりのまえば（無無無）?）
ROCKETS_HITMONCHAN = "PMCG5-054"  # R団のエビワラー（リーダーズスタジアム。HP 60・闘・弱点 超・にげる 1。クロスカウンター（闘）・マグナムパンチ（闘闘無）50）。HITMONCHAN と別の名前
BROCKS_GEODUDE_40 = "PMCG5-047"  # タケシのイシツブテ（リーダーズスタジアム。HP 40・闘・弱点 草・にげる 1。たすけをよぶ（闘）・スパイラルショット（闘無）20）。BROCKS_GEODUDE（PMCG5-046）と別のカード
GIOVANNIS_MEOWTH_40 = "PMCG6-068"  # サカキのニャース（闇からの挑戦。HP 40・無色・弱点 闘・抵抗力 超 -30・にげる 1。てつだうふり（無）・ダブルひっかき（無無）20×）。GIOVANNIS_MEOWTH（PMCG6-063）と別のカード
GASTLY = "PMCG3-029"  # 化石の秘密のゴース（v0.9。HP 50・超・弱点なし・抵抗力 闘 −30・にげる 0。したでなめる 10・エナジーへんかん）
HAUNTER = "PMCG3-030"  # 化石の秘密のゴースト（v0.9。ゴースから進化する 1 進化。HP 50・超・弱点なし・抵抗力 闘 −30・にげる 0。とうめい・あくむ 10）
BASE_HAUNTER = "PMCG1-047"  # 第1弾のゴースト（v0.9 の参照カード。同じ名前の別のカード。とうめいを持たない。HP 60・超・抵抗力 闘 -30・にげる 1。さいみんじゅつ（超）・ゆめくい（超超）50。v0.44 まで「ゆめくい」が未実装でデッキに入らず、v0.45 で対応にした）
V0_45_POKEMON = (BASE_HAUNTER, MISTYS_HORSEA_50, MISTYS_DEWGONG, KOGAS_EKANS, KOGAS_ARBOK, KOGAS_GRIMER, DARK_BLASTOISE, DARK_MAGNETON, BLAINES_CHARIZARD,
                 ROCKETS_ZAPDOS, ONIX, RATICATE, ROCKETS_HITMONCHAN, BROCKS_GEODUDE_40, GIOVANNIS_MEOWTH_40)  # 写しの組 pool_v0_45 の並び
V0_45_ADOPTED = V0_45_POKEMON[1:]  # kyuura データの採用で加えた 14 枚（第1弾のゴーストは v0.9 の過去の原典照合の記録）
MACHOKE = "PMCG1-055"  # ゴーリキー（v0.10。ワンリキーから進化する 1 進化。HP 80・闘・弱点 超・にげる 3。からてチョップ 50−・じごくぐるま 60）
MACHAMP = "PMCG1-057"  # カイリキー（v0.10。ゴーリキーから進化する 2 進化。HP 100・闘・弱点 超・にげる 3。はんげき・ちきゅうなげ 60）
# サカキのカイリキー（v0.10 では参照カード。v0.11 で対応。サカキのゴーリキーから進化する 2 進化。HP 100・闘・弱点 超・にげる 3。ポケモンパワー
# こんじょう・ハリケーンパンチ 30×。はんげきを持たない）
GIOVANNIS_MACHAMP = "PMCG6-061"
GIOVANNIS_MACHOKE = "PMCG6-059"  # サカキのゴーリキー（v0.11。サカキのワンリキーから進化する 1 進化。HP 80・闘・弱点 超・にげる 2。いちかばちか 60・じごくがため 20+）
GIOVANNIS_MACHOP = "PMCG6-057"  # サカキのワンリキー（v0.11。HP 50・闘・弱点 超・にげる 1。チョップ 10・いかりのスーパーパンチ 20×）
# R団のファイヤー（v0.12。ジム拡張第1弾。たね。HP 60・炎・弱点なし・抵抗力 闘 −30・にげる 2。ポケモンパワー ふしちょう（このカードが「きぜつ」
# したとき、使える。トラッシュから手札に加える）・ほのおのかべ（炎炎炎）40（次の相手の番、相手のワザによるダメージを受けたとき、相手に 10））
ROCKETS_MOLTRES = "PMCG5-020"
# 第4弾（ロケット団）のゼニガメ（v0.13。たね。HP 50・水・弱点 雷・にげる 1。こうらアタック（無無）20。第1弾のゼニガメ（SQUIRTLE）と同じ名前の
# 別のカード。どちらからでもわるいカメールに進化できる）
ROCKET_SQUIRTLE = "PMCG4-018"
# わるいカメール（v0.13。ゼニガメから進化する 1 進化。HP 60・水・弱点 雷・抵抗力なし・にげる 1。おうふくびんた（水）10×・こうらがえし（水無）
# ダメージなし（次の相手の番、相手のワザによってダメージを受けたとき、そのポケモンにも同じダメージを与える））
DARK_WARTORTLE = "PMCG4-021"
# モンジャラ（v0.17a。第1弾。たね。HP 50・草・弱点 炎・にげる 2。しめつける（草無）20（コインで「おもて」ならマヒ）・どくのこな（草草草）20（どく）。
# 既存の実装（ParalyzeOnHeads・PoisonOpponent）だけで登録）
TANGELA = "PMCG1-007"
# サカキのニャース（v0.17a。ジム拡張第2弾。たね。HP 50・無色・弱点 闘・抵抗力 超 −30・にげる 2。ねこノミ（無）ダメージなし（コインで「おもて」なら
# こんらん）・ねこキック（無無無）30。ねこノミは既存の要素 Status の新しい並び（ConfuseOnHeadsWithoutDamage））
GIOVANNIS_MEOWTH = "PMCG6-063"
# R団のカビゴン（v0.17b。ジム拡張第2弾。たね。HP 90・無色・弱点 闘・抵抗力 超 −30・にげる 4。ポケモンパワー わるいねぞう（ねむり状態で相手のワザに
# よるダメージを受けたとき、ダメージを与えたポケモンに 20。特殊能力のダメージ）・たおれこむ（無無無）20（ダメージを与えた後、自分をねむり））
ROCKETS_SNORLAX = "PMCG6-073"
# キョウのベトベトン（v0.17c。参照カード。ポケモンパワー だつりょくえき（未実装）。分類で拒否する）
KOGAS_MUK = "PMCG6-023"
# ナツメのヤドン（v0.18c。ジム拡張第2弾。たね。HP 50・超・弱点 超・抵抗力なし・にげる 1。ぐうたらこうげき（超無）30（ダメージを与えた後、自分を
# ねむり）。たおれこむと同じ DamageAndSelfSleep で、新しい要素・型はない）
SABRINAS_SLOWPOKE = "PMCG6-044"
# リザードン（参照カード。リザードから進化する 2 進化。実装を登録していないポケモンパワー「エナジーバーン」とワザ「ほのおのうず」を
# 持つ。v0.4e まではフシギバナ、v0.5 ではカメックス、v0.6 ではフーディンが「ポケモンパワーを持つので未対応」の参照カードだった。
# v0.7 でフーディンを対応にしたので、その役を引き継ぐ）
CHARIZARD = "PMCG1-021"
# トレーナー（v0.2b で対応）
POTION = "PMCG1-071"  # きずぐすり
GUST = "PMCG1-072"  # 突風（v0.21 で対応。使ったプレイヤーが相手の控えポケモンを 1 匹選び、相手の対戦ポケモンと入れ替える。p.255）
SWITCH = "PMCG1-073"  # ポケモンいれかえ
BILL = "PMCG1-074"  # マサキ
PROFESSOR_OAK = "PMCG1-077"  # オーキドはかせ（v0.19 で対応。手札をすべてトラッシュし、その後 7 枚引く。p.255）
PLUSPOWER = "PMCG1-081"  # プラスパワー（v0.2c で対応）
COMPUTER_SEARCH = "PMCG1-090"  # パソコン通信（v0.22 で対応。手札から 2 枚選んでトラッシュし、山札から 1 枚選び出して手札に加え、山札を切る。p.260）
ENERGY_RETRIEVAL = "PMCG1-076"  # エネルギー回収（v0.23 で対応。手札から 1 枚選んでトラッシュし、トラッシュの基本エネルギーカードを最大 2 枚手札に加える。p.257）
POKEMON_BREEDER = "PMCG1-094"  # ポケモン育て屋さん（v0.25 で対応。自分の場のたねポケモンに手札の 2 進化カードを直接重ね、1 進化を飛ばして進化させる。p.259）
POKEMON_TRADER = "PMCG1-093"  # ポケモン交換おじさん（v0.24 で対応。手札のたねポケモン・進化カードを見せて山札にもどし、山札のたねポケモン・進化カードを見せて手札に加え、山札を切る。p.259）
DEFENDER = "PMCG1-079"  # ディフェンダー（v0.2e で対応）
SUPER_POTION = "PMCG1-075"  # いいきずぐすり（参照カード。実装を登録していないトレーナー）

# 60 枚の合法なデッキ（たねポケモン 20 枚 + 基本エネルギー 40 枚）
FIRE_DECK = expand_decklist({GROWLITHE: 4, PONYTA: 4, RATTATA: 4, DRATINI: 4, VOLTORB: 4, FIRE: 40})
WATER_FIGHTING_DECK = expand_decklist({STARYU: 4, SEEL: 4, DIGLETT: 4, MACHOP: 4, HITMONCHAN: 4, WATER: 20, FIGHTING: 20})
# たねポケモン 40 枚（10 種 × 4）+ エネルギー 20 枚。手札がたねポケモンだけになる seed を探すのに使う
MANY_BASICS = expand_decklist({p: 4 for p in (PONYTA, GROWLITHE, STARYU, SEEL, VOLTORB, DIGLETT, MACHOP, HITMONCHAN, RATTATA, DRATINI)} | {FIRE: 20})
# たねポケモンが少ない 60 枚のデッキ（切り直しが起こりやすい）
ONE_BASIC = expand_decklist({MACHOP: 1, FIGHTING: 59})
FEW_BASICS = expand_decklist({SEEL: 4, WATER: 56})


def find_seed(deck0, deck1, predicate, start: int = 0, limit: int = 5000) -> int:
    """predicate(new_game(...)) が真になる最初の seed（決まった順に探すので毎回同じ seed になる）。"""
    for seed in range(start, start + limit):
        if predicate(new_game(deck0, deck1, seed)):
            return seed
    raise AssertionError("条件に合う seed が見つからない")


def uids(state: GameState, player: int, zone: str, card_id: str | None = None) -> list[int]:
    p = state.players[player]
    items = getattr(p, zone)
    return [u for u in items if card_id is None or state.cards[u].card_id == card_id]


def basics_in_hand(state: GameState, player: int) -> list[int]:
    return [u for u in state.players[player].hand if state.card_def(u).is_basic_pokemon]


def energy_in_hand(state: GameState, player: int) -> list[int]:
    return [u for u in state.players[player].hand if state.card_def(u).is_basic_energy]


def place_all(state: GameState, player: int, max_bench: int = 5) -> GameState:
    basics = basics_in_hand(state, player)
    return apply_command(state, PlaceStartingPokemon(player, basics[0], tuple(basics[1 : 1 + max_bench])))


def finish_setup(state: GameState, janken_winner: int = 0, draw_count: int = 2) -> GameState:
    """対戦準備を最後まで進める（両方がたねポケモンを全部出す → 引く権利があれば引く → ジャンケン）。"""
    for player in (0, 1):
        if not state.players[player].placed_starting_pokemon:
            state = place_all(state, player)
    while state.phase is Phase.SETUP_MULLIGAN_DRAW:
        player = 0 if state.players[0].mulligan_draws_remaining else 1
        state = apply_command(state, DrawMulliganCards(player, min(draw_count, len(state.players[player].deck))))
    return apply_command(state, ReportJankenResult(janken_winner))


# ---------------------------------------------------------------- 盤面を直接作る（テスト専用）


def build_test_state(
    players: list[dict],
    *,
    current_player: int = 0,
    turn_number: int = 3,
    seed: int = 0,
    energy_attachments_this_turn: int = 0,
    effects=None,
    pool=None,
) -> GameState:
    """テスト専用: 正式な対戦開始を通さずに MAIN の盤面を作る。

    players[i] のキー（どれも省略できる。active は必須）:
      active: カード id、または {"card": id, "damage": n, "energy": [id, ...], "poison": ダメージ, "sleep": True,
              "paralysis": マヒ状態になった番, "confusion": True, "retreat_failed_turn": 番,
              "evolved_from": 下のたねポケモンのカード id, "evolved_turn": 進化した番, "played_turn": 場に出た番,
              "prevent_damage": 効果を与えた番, "retaliation": 効果を与えた番, "retaliation_received": 効果を与えた番}
              （"poison" はバトル場のポケモンのどく状態。v0.3a。"sleep"・"paralysis" はねむり・マヒ状態。v0.3b。
              "confusion" はこんらん状態、"retreat_failed_turn" はこんらん状態で「にげる」に失敗した番。v0.3c。
              特殊状態をベンチに書くと不変条件で拒否される。"sleep"・"paralysis"・"confusion" は重複しないので
              2 つ以上は書けない。"evolved_from" は進化しているポケモン（v0.4a。"card" が 1 進化ポケモン）。v0.4c から、
              2 進化ポケモンは "evolved_from" に下のカードのリスト [たねポケモン, 1 進化ポケモン]（下から順）を書く。
              "evolved_turn" はいまの姿に進化した番で、省略すると、3 番以降の持ち主の番（2 進化ならその 2 つ目以降）の
              うち、今の番より前の最後の番（なければ今の番）。1 進化した番は書かない（状態に持たないので、不変条件は
              その前に 1 進化できる番があることだけを確かめる。進化のログは置かない）。"played_turn" の既定は 0（対戦準備で出した）。
              "prevent_damage" は、その番に「かたまる」などで受けた持続する効果 ``PreventDamage``（v0.4b。はたらく番は次の番）。
              効果を与えたログ ``persistent_effect_added`` も、その番の記録として置く（不変条件: 効果はログと対応する）。
              "retaliation" は、その番に「ほのおのかべ」で受けた持続する効果 ``Retaliation``（v0.12。ワザの位置 0・与えるダメージ 10。
              カードは R団のファイヤー。ログも "prevent_damage" と同じく置く）。
              "retaliation_received" は、その番に「こうらがえし」で受けた持続する効果 ``Retaliation``（v0.13。ワザの位置 1・決め方
              ``RETALIATION_RECEIVED``（受けたダメージと同じダメージを返す）・量 None。カードはわるいカメール。ログも同じく置く）。
              "next_turn_attack_damage" は、(効果を与えた番, 効果を与えたワザの位置, ダメージが変わるワザの位置, 変えたあとのダメージ)
              の持続する効果 ``NextTurnAttackDamage``（v0.27。「つるぎのまい」。はたらく番は与えた番 + 2。カードはストライク。ログも同じく
              置き、ログの ``effect`` は効果を与えたワザ）。
              "trainers" は、ついているトレーナー（v0.4e）の [(カード id, トラッシュする番), ...]。使ったプレイヤーは持ち主。
              トラッシュする番は、プラスパワーなら使った番、ディフェンダーなら使った番 + 1（不変条件: 使った番は持ち主の番））
      bench:  active と同じ形のリスト
      hand / deck / discard: カード id のリスト（deck は先頭が一番上）
      prizes: カード id のリスト、または枚数（枚数なら炎エネルギーで埋める）
    pool: カードの定義を引くカードの組（省略時は同梱の写し。テスト専用のカードを使うとき）
    """
    pool = pool or load_card_pool()
    cards: dict[int, CardInstance] = {}

    def new_uid(card_id: str, owner: int) -> int:
        uid = len(cards)
        cards[uid] = CardInstance(uid, card_id, owner)
        return uid

    next_pokemon_id = [1]

    def pokemon(spec, owner: int) -> PokemonInPlay:
        if isinstance(spec, str):
            spec = {"card": spec}
        below = spec.get("evolved_from", ())
        below = (below,) if isinstance(below, str) else tuple(below)  # 2 進化（v0.4c）は [たね, 1 進化]（下から順）
        stack = tuple(new_uid(card_id, owner) for card_id in below)
        result = PokemonInPlay(new_uid(spec["card"], owner), pokemon_id=next_pokemon_id[0])
        next_pokemon_id[0] += 1
        result.played_turn = spec.get("played_turn", 0)
        if stack:
            result.evolution_stack = stack
            evolved_turn = spec.get("evolved_turn")
            if evolved_turn is None:
                # 先攻はプレイヤー 0（奇数の番）。おたがいの最初の番（1・2 番）には進化できない。今の番より前の持ち主の番の
                # うち最後の番（なければ今の番）。2 進化（v0.4c）は、その前に 1 進化した持ち主の番がいる（同じ番に二度は
                # 進化できない。p.310）ので、その 2 つ目から（場に出た番は見ない。v0.4a と同じ）
                owned = [t for t in range(3, turn_number + 1) if t % 2 == (1 if owner == 0 else 0)]
                owned = owned[len(stack) - 1:]
                if not owned:
                    raise ValueError("進化した番を決められない（turn_number を大きくするか evolved_turn を書く）")
                earlier = [t for t in owned if t < turn_number]
                evolved_turn = earlier[-1] if earlier else owned[-1]
            result.evolved_turn = evolved_turn
        result.energy = [new_uid(e, owner) for e in spec.get("energy", [])]
        result.trainers = [AttachedTrainer(new_uid(card_id, owner), owner, discard_at) for card_id, discard_at in spec.get("trainers", [])]
        result.damage = spec.get("damage", 0)
        exclusive = None
        if spec.get("sleep"):
            exclusive = ASLEEP
        if "paralysis" in spec:
            if exclusive is not None:
                raise ValueError("ねむりとマヒは重複しない（p.322）")
            exclusive = Paralyzed(turn=spec["paralysis"])
        if spec.get("confusion"):
            if exclusive is not None:
                raise ValueError("ねむり・マヒ・こんらんは重複しない（p.322）")
            exclusive = CONFUSED
        result.retreat_failed_turn = spec.get("retreat_failed_turn")
        if "prevent_damage" in spec:
            created = spec["prevent_damage"]
            result.persistent_effects = (PreventDamage(result.card, owner, created, created + 1),)
        if "retaliation" in spec:
            created = spec["retaliation"]
            result.persistent_effects = (*result.persistent_effects, Retaliation(result.card, owner, created, created + 1, 0, 10))
        if "retaliation_received" in spec:
            created = spec["retaliation_received"]
            result.persistent_effects = (
                *result.persistent_effects, Retaliation(result.card, owner, created, created + 1, 1, None, RETALIATION_RECEIVED)
            )
        if "next_turn_attack_damage" in spec:
            # v0.27: (効果を与えた番, 効果を与えたワザの位置, ダメージが変わるワザの位置, 変えたあとのダメージ)。はたらく番は与えた番 + 2
            created, attack_index, target_index, amount = spec["next_turn_attack_damage"]
            result.persistent_effects = (
                *result.persistent_effects,
                NextTurnAttackDamage(result.card, owner, created, created + 2, attack_index, target_index, amount),
            )
        poison = Poison(spec["poison"]) if "poison" in spec else None
        if poison is not None or exclusive is not None:
            result.conditions = SpecialConditions(poison=poison, exclusive=exclusive)
        return result

    states = []
    for owner, spec in enumerate(players):
        prizes = spec.get("prizes", 6)
        if isinstance(prizes, int):
            prizes = [FIRE] * prizes
        p = PlayerState(deck=[])
        p.active = pokemon(spec["active"], owner) if spec.get("active") else None
        p.bench = [pokemon(b, owner) for b in spec.get("bench", [])]
        p.hand = [new_uid(c, owner) for c in spec.get("hand", [])]
        p.deck = [new_uid(c, owner) for c in spec.get("deck", [FIRE] * 10)]
        p.prizes = [new_uid(c, owner) for c in prizes]
        p.discard = [new_uid(c, owner) for c in spec.get("discard", [])]
        p.placed_starting_pokemon = True
        states.append(p)

    used = {c.card_id for c in cards.values()}
    state = GameState(
        rules=RULES_2000_02_14,
        card_data=DataSource(pool.source["repository"], pool.source["commit"], pool.source["path"]),
        seed=seed,
        rng=random.Random(seed),
        cards=freeze_mapping(cards),
        definitions=freeze_mapping({c: pool.get(c) for c in used}),
        decklists=((), ()),
        players=states,
        phase=Phase.MAIN,
        turn_number=turn_number,
        current_player=current_player,
        first_player=0,
        energy_attachments_this_turn=energy_attachments_this_turn,
        next_pokemon_id=next_pokemon_id[0],
        effects=effects or pool.effects,
    )
    # "retreat_failed_turn" を書いたポケモンには、その番の「にげる」の失敗のログも置く（v0.3d の不変条件: 記録はログの
    # retreat_failed と対応する）。テスト専用の盤面なので、トラッシュしたエネルギーは空にしておく
    for owner, p in enumerate(states):
        for pokemon in p.in_play():
            if pokemon.retreat_failed_turn is not None:
                state.add_event("retreat_failed", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, discarded=())
    # "prevent_damage" を書いたポケモンには、効果を与えた番のログも置く（v0.4b の不変条件: 持続する効果はログと対応する）
    for owner, p in enumerate(states):
        for pokemon in p.in_play():
            for effect in pokemon.persistent_effects:
                current = state.turn_number
                state.turn_number = effect.created_turn  # ログの turn は効果を与えた番
                # v0.27: 「つるぎのまい」の効果は、ログの監査が効果を与えたワザ（AttackKey の文字列）から登録を引くので、ワザを書く
                attack = f"{state.cards[effect.source_card].card_id}#{effect.attack_index}" if isinstance(effect, NextTurnAttackDamage) else "test"
                state.add_event(
                    "persistent_effect_added", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id,
                    persistent_effect=effect.kind, source_card=effect.source_card, source_player=effect.source_player,
                    active_turn=effect.active_turn, effect=attack,
                )
                state.turn_number = current
    return state


def active(state: GameState, player: int) -> PokemonInPlay:
    return state.players[player].active


# ---------------------------------------------------------------- 1 試合を進める決まった手順


def best_affordable_attack(state: GameState, player: int) -> int | None:
    """使えるワザのうち、ダメージの目安の数字がいちばん大きいもの（同じなら後のワザ）。

    ダメージの目安の数字がないワザ（パラスの「キノコのほうし」。v0.3b）は 0 として比べる（それまでの対応カードには
    ないので、既存の対戦の手順は変わらない）。"""
    pokemon = state.players[player].active
    definition = state.card_def(pokemon.card)
    provided = state.energy_types(pokemon)
    best = None
    for attack in definition.attacks:
        if attack.supported and can_pay_cost(attack.cost, provided):
            if best is None or (attack.damage or 0) >= (definition.attacks[best].damage or 0):
                best = attack.index
    return best


def scripted_command(state: GameState, *, attack: bool = True, bench: bool = True, janken_winner: int = 0):
    """今の状態で次に送る操作を 1 つ返す（統合テスト用の決まった手順）。

    - 対戦準備: 手札のたねポケモンをすべて出す。引く権利があれば 2 枚引く。ジャンケンは janken_winner の勝ち。
    - 自分の番: たねポケモンをベンチに出す → エネルギーをバトル場のポケモンにつける → 使える一番強いワザを使う。
      ワザが使えなければ番を終える。
    - サイドは一番目を取る。バトル場には、ベンチの一番目のポケモンを出す。
    """
    phase = state.phase
    if phase is Phase.SETUP_PLACEMENT:
        player = 0 if not state.players[0].placed_starting_pokemon else 1
        basics = basics_in_hand(state, player)
        return PlaceStartingPokemon(player, basics[0], tuple(basics[1:6]) if bench else ())
    if phase is Phase.SETUP_MULLIGAN_DRAW:
        player = 0 if state.players[0].mulligan_draws_remaining else 1
        return DrawMulliganCards(player, min(2, len(state.players[player].deck)))
    if phase is Phase.SETUP_FIRST_PLAYER:
        return ReportJankenResult(janken_winner)
    if phase is Phase.TAKE_PRIZE:
        player = next(p for p, n in state.pending_prizes.items() if n > 0)
        return TakePrize(player, 0)
    if phase is Phase.PROMOTE_ACTIVE:
        player = state.pending_promotions[0]
        return PromoteActive(player, state.players[player].bench[0].card)
    if phase is Phase.MAIN:
        player = state.current_player
        p = state.players[player]
        if bench and len(p.bench) < 5 and basics_in_hand(state, player):
            return PlayBasicToBench(player, basics_in_hand(state, player)[0])
        if state.energy_attachments_this_turn == 0 and energy_in_hand(state, player):
            return AttachEnergy(player, energy_in_hand(state, player)[0], p.active.card)
        if attack:
            index = best_affordable_attack(state, player)
            if index is not None:
                return UseAttack(player, index)
        return EndTurn(player)
    raise AssertionError(f"操作を決められない局面 {phase}")


def play_until_end(state: GameState, *, max_steps: int = 5000, check=None, **policy) -> tuple[GameState, list]:
    """終わる（GAME_OVER / SUDDEN_DEATH / HALTED）まで scripted_command を送る。送った操作の列も返す。"""
    commands = []
    for _ in range(max_steps):
        if state.phase in (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED):
            return state, commands
        command = scripted_command(state, **policy)
        commands.append(command)
        state = apply_command(state, command)
        if check is not None:
            check(state)
    raise AssertionError("決まった手数で終わらなかった")


def replay(state: GameState, commands: Iterable) -> GameState:
    for command in commands:
        state = apply_command(state, command)
    return state


# ---------------------------------------------------------------- テスト専用のワザの効果（製品の登録表には入れない）

from kyuura_engine.decisions import push_attack_decision  # noqa: E402
from kyuura_engine.effects import DEFAULT_EFFECTS, AttackEffect, AttackEntry, AttackKey  # noqa: E402
from kyuura_engine import effects as _effects  # noqa: E402

# v0.17 から製品の登録表に加えたワザの実装の型（v0.13 の 24 種類のあと）。解決の基盤の要素の並び（programs.BUILDERS）で処理し、v0.13 の
# 約束（resolve・resume）を持たない。v0.13 の止める関数で確かめる型（v013_checks.VERIFIED）には入れない（v0.16c。自動では加えない）
ATTACK_TYPES_SINCE_V0_17 = (
    _effects.ConfuseOnHeadsWithoutDamage,  # v0.17a: サカキのニャースの「ねこノミ」（既存の要素 Status の新しい並び）
    _effects.DamageAndSelfSleep,  # v0.17b: R団のカビゴンの「たおれこむ」（Damage と、対象を自分にした Status）
    _effects.SetNextTurnAttackDamage,  # v0.27: ストライクの「つるぎのまい」（次の自分の番のワザのダメージを変える持続する効果。新しい要素）
    _effects.DiscardEnergyThenDamage,  # v0.30: ヒトカゲの「ひのこ」など（エネルギーをトラッシュする要素 DiscardOwnEnergy と Damage）
) + (
    # v0.31: v0.30 の保留の 22 枚と進化元・依存のカード（docs/held-cards-v0.31.md 3 章の仕組みの表）
    _effects.AttachDiscardEnergyToSelf,  # マチスのエレブーの「たいでん」
    _effects.CannotAttackOnHeads,  # イーブイの「しっぽをふる」
    _effects.CoinBonusDamage,  # イーブイの「でんこうせっか」・マチスのピカチュウの「でんこうせっか」・カツラのブーバーの「ひをふく」
    _effects.CoinBonusDamageThenDiscardAll,  # マチスのライチュウの「バリバリ」
    _effects.CoinBonusDiscardThenDamage,  # わるいブースターの「ひあそび」
    _effects.CoinDiscardOpponentEnergyEach,  # カスミのゴルダックの「スーパーデストロイ」
    _effects.CoinsDiscardThenSpreadDamage,  # カツラのリザードの「やきはらう」
    _effects.CoinsPerEnergyDamageThenDiscard,  # わるいリザードンの「れんぞくファイヤーボール」
    _effects.CopyOpponentAttackEffect,  # ピッピの「ゆびをふる」・ピクシーの「ゆびをふる」
    _effects.DamageAndBenchTypeDamage,  # カツラのガーディの「もえひろがる」
    _effects.DamagePlusDefenderEnergy,  # ミュウツーの「サイコキネシス」
    _effects.DamagePlusOwnCounters,  # わるいブースターの「いかり」
    _effects.DamageThenDiscardAllOnTails,  # カスミのゴルダックの「エクストラビーム」・カツラのキュウコンの「しゃくねつ」
    _effects.DamageThenDiscardEachEnergy,  # カツラのヒトカゲの「メラメラ」
    _effects.DamageThenMoveEnergyToBench,  # わるいマルマインの「エナジーボム」
    _effects.DamageThenOptionalBenchDamage,  # わるいギャロップの「ひばしら」
    _effects.DamageThenParalyzeOrSelfDamage,  # マチスのライチュウの「でんきタックル」
    _effects.DiscardAllThenCoinDamage,  # マチスのエレブーの「ほうでん」
    _effects.DiscardEnergyBeforeDamage,  # リザードンの「ほのおのうず」・サンダーの「10まんボルト」・カツラのウインディの「ほのおのあらし」
    _effects.DiscardEnergyThenDraw,  # わるいゴルダックの「だい3のめ」
    _effects.DiscardEnergyThenRecoverTrainer,  # ヤドンの「ゴミあさり」
    _effects.DiscardEnergyThenSelfEffect,  # ゴースの「みちづれ」・ミュウツーの「バリアー」
    _effects.DiscardFireThenMillOpponent,  # ファイヤーの「やまやき」
    _effects.DrawCardsAttack,  # コダックの「めまい」
    _effects.ExtraEnergyDamageMixed,  # コダックの「みずでっぽう」
    _effects.FailOnTailsDamage,  # ファイヤーの「ゴッドバード」
    _effects.FailOnTailsDiscardThenDamage,  # わるいリザードの「ファイヤーボール」
    _effects.HealSelfOnHeadsIfDamaged,  # ヤドンの「ぼーっとする」
    _effects.MillSelfThenDamage,  # カツラのブーバーの「マグマふんしゅつ」
    _effects.ReduceDamageNextTurn,  # ピクシーの「ちいさくなる」
    _effects.SleepOnHeadsWithoutDamage,  # ゴースの「さいみんガス」・ピッピの「うたう」
    _effects.SwitchOpponentActive,  # キュウコンの「かどわかす」
    _effects.ThreeCoinPsychicPower,  # カスミのコダックの「ちょうのうりょく」
) + (
    # v0.32（docs/bench-search-counter-drain-v0.32.md 3 章）
    _effects.PutBasicFromDeckOntoBench,  # ニドラン♀・マダツボミ・クラブの「なかまをよぶ」・ナゾノクサの「ふえる」
    _effects.DamageTimesOwnCounters,  # コイキング・キングラーの「じたばた」
    _effects.DamagePlusDefenderCounters,  # ルージュラの「ヨガのポーズ」
    _effects.DamageAndFullDrain,  # コンパン・ズバット（化石の秘密）・ゴルバットの「きゅうけつ」
) + (
    # v0.33（docs/cd4-opponent-energy-coins-v0.33.md 3 章）
    _effects.DamageThenDiscardOpponentEnergy,  # ハクリュー・ゴルダックの「はかいこうせん」・わるいシャワーズの「うずしお」・マチスのコイルの「はかいでんぱ」・ナツメのコンパンの「はかいビーム」
    _effects.NoDamageOnTails,  # ニドラン♂の「つのでつつく」
    _effects.DamageAndParalyzeOnHeadsElseFail,  # パルシェンの「からではさむ」
    _effects.DamageAndOwnBenchDamage,  # タケシのディグダの「ミニじしん」
    _effects.DamageThenCoinBenchDamage,  # カツラのサイホーンの「かけぬける」
) + (
    # v0.34（docs/barrier-resume-coin-bonus-v0.34.md 4 章）
    _effects.CoinBonusOrSelfDamage,  # エレブーの「かみなりパンチ」・ニドキングの「あばれる」
    _effects.DamageThenSelfBarrierOnHeads,  # ギャロップの「こうそくいどう」
    _effects.DamagePlusOwnCountersThenSelfConfuseOnTails,  # ケンタロスの「いかりくるう」
    _effects.DamageThenCoinOwnBenchDamage,  # サカキのカイロスの「うしろなげ」
    _effects.DamageThenPoisonOrConfuse,  # ドガースの「くさいガス」
    _effects.DamageAndSpecialPoison,  # ニドキングの「どくどく」
    _effects.SwitchSelfWithBench,  # ナッシーの「テレポート」
    _effects.CoinsPerAttachedEnergyDamage,  # ナッシーの「たまなげMAX」
    _effects.ReduceDamageToSelf,  # カラカラの「なきつく」
    _effects.PutTypeBasicFromDeckOntoBench,  # ガラガラの「たすけをよぶ」
) + (
    # v0.35（docs/coin-groups-damage-order-v0.35.md 4 章）
    _effects.MultiplyNextTurnAttackDamage,  # マチスのコラッタ・ラッタの「きあいだめ」
    _effects.DamageThenLockSelfOnTails,  # カスミのニョロモの「あわあわ」
    _effects.LockOpponentAttack,  # カスミのニョロモの「ドわすれ」
    _effects.CoinsPerAttachedTypeBonusDamage,  # カスミのニョロゾの「ウォーターパンチ」
    _effects.CoinsHeadsDamageTailsSelfDamage,  # カツラのケンタロスの「ぜんりょくとっしん」
) + (
    # v0.36（docs/sand-attack-retreat-lock-v0.36.md 5 章）
    _effects.DamageThenAttackCoinCheck,  # すなかけ・えんまく・サンダーフラッシュ・しんきろう
    _effects.DamageThenRetreatLock,  # アイスバーン・わしづかみ
    _effects.DamageThenReturnSelfToDeckOnHeads,  # キョウのドガースの「くもがくれガス」
) + (
    # v0.37（docs/fifteen-reused-effects-v0.37.md 3 章）
    _effects.PoisonOnHeadsWithoutDamage,  # アーボの「どくえき」
    _effects.ParalyzeOnHeadsWithoutDamage,  # タケシのイワークの「うなりごえ」
    _effects.DamageThenDrawOnHeads,  # ニャースの「ねこにこばん」
    _effects.DrawOnHeads,  # キョウのモンジャラの「つるでさがす」
    _effects.SelfBarrierOnHeads,  # カスミのコイキングの「しんだふり」
    _effects.DamageThenReduceDamageToSelf,  # ペルシアンの「かみつく」
) + (
    # v0.38（docs/bench-switch-combined-v0.38.md 3 章）
    _effects.ChooseOpponentBenchDamage,  # サワムラーの「のびるキック」・エリカのモンジャラの「のびるつる」
    _effects.DamageThenChosenBenchDamage,  # タケシのロコンの「ほのおのわ」
    _effects.SpreadDamage,  # タケシのゴルバットの「かいてんひこう」
    _effects.DamageThenCoinBenchDamageEitherSide,  # フリーザーの「ふぶき」
    _effects.CoinBonusDamageAndBenchDamage,  # カツラのギャロップの「ふみあらす」
    _effects.DamageThenForceSwitchOnHeads,  # アーボックの「いかくこうげき」
    _effects.DamageThenForceSwitchThenSelfDamage,  # サイドンの「げきとつ」
    _effects.DamageThenSelfSwitchOnHeads,  # カツラのポニータの「けりにげ」
    _effects.CoinBonusDamageAndSelfBarrier,  # キョウのピジョンの「こうそくひこう」
    _effects.DamageThenPoisonOrParalyze,  # キョウのビードルの「きけんなはり」
    _effects.DamageAndSelfDamageThenPoisonOnHeads,  # サカキのニドリーナの「どくばりタックル」
    _effects.DamageThenReduceDamageNextTurn,  # ナツメのポリゴンの「バリアアタック」
    _effects.DiscardAttachedAndReturnSelfToDeck,  # ケーシィの「いなくなる」
    _effects.ReturnSelfToDeckThenSearchPokemon,  # キョウのポッポの「でんれい」
) + (
    # v0.39（docs/selfdestruct-spread-count-v0.39.md 3 章）
    _effects.SelfDestruct,  # コイル・レアコイル（第1弾）・マタドガス・レアコイル（化石の秘密）の「じばく」
    _effects.DamageIgnoringWeaknessResistance,  # レアコイル（化石の秘密）の「ソニックブーム」
    _effects.DamageThenChosenBenchTargets,  # ライチュウ（化石の秘密）の「ギガスパーク」
    _effects.DamageThenSameTypeBenchDamage,  # マルマインの「ビリビリ」
    _effects.DamageThenCoinBenchDamageBothSides,  # キョウのドガース（PMCG6-008）の「おならガス」
    _effects.DamageThenOtherTypeBenchDamageBothSides,  # カスミのニョロボンの「ウォーターリング」
    _effects.DamagePlusPokemonCount,  # コイル（ロケット団）の「ちょくれつじりょく」・プクリンの「ともだちのわ」・ニドクインの「ラブラブアタック」
    _effects.CoinBonusDamageAndSelfDamage,  # キョウのマタドガスの「とつぜんばくはつ」
    _effects.DamageThenSpecialPoisonOnHeads,  # キョウのマタドガスの「どくどくガス」
    _effects.CoinPoisonAndBenchDamage,  # エリカのパラスの「きけんなほうし」
) + (
    # v0.40（docs/count-condition-switch-return-v0.40.md 3 章）
    _effects.GroupAttackFromDeck,  # キョウのズバットの「むれでおそう」
    _effects.NamedPokemonExplosion,  # わるいマタドガスの「みんなでばくはつ」
    _effects.OpponentFlipsTailsDamage,  # わるいスリーパーの「ベンチをあやつる」
    _effects.DamageRequiringOwnCounters,  # サカキのニドラン♂の「いかりのいちげき」
    _effects.DamagePlusIfDefenderDamaged,  # サカキのニドリーノの「つのでえぐる」
    _effects.AttackLockWhileSourceActive,  # サカキのニドキングの「すごむ」
    _effects.FailOnTailsAmountIfBenchNamed,  # サカキのニドクインの「ラブラリアット」
    _effects.SwitchOpponentThenDamage,  # わるいゴーリキーの「ひきずりだす」・エリカのウツドンの「さそってとかす」
    _effects.ReturnOpponentActiveToDeck,  # わるいカイリキーの「つまみだす」
    _effects.CoinsAllHeadsBonusDamage,  # カスミのシードラの「きぜつばり」
    _effects.ShuffleDeckAttack,  # タケシのマンキーの「ひまつぶし」・マンキーの「いたずら」
    _effects.DamageThenSelfConfuseOnTails,  # オコリザルの「あばれまわる」
) + (
    # v0.41（docs/heal-counter-status-v0.41.md 3 章）
    _effects.DamageThenHealSelf,  # エリカのナゾノクサの「ちょっとすいとる」・「たまにすいとる」
    _effects.CoinHealSelf,  # エリカのクサイハナの「ヒーリングかふん」・ナツメのヤドランの「いねむり」
    _effects.CoinsHealOwnPokemon,  # ナツメのモルフォンの「かいふくりんぷん」
    _effects.HealAllPokemonBothSides,  # エリカのプリンの「みんなでかいふく」
    _effects.MoveOwnCountersToOpponent,  # ナツメのゴルダックの「ダメージシフト」
    _effects.SwapCountersOnHeads,  # R団のミュウツーの「チェンジダメージ」
    _effects.DamageThenConfuseBoth,  # クサイハナの「くさいにおい」
    _effects.DamageThenStatusByCoin,  # エリカのナゾノクサ（HP 40）の「へんなこな」
    _effects.DamageThenChosenStatusOnHeads,  # エリカのクサイハナの「ミラクルかふん」
    _effects.CoinDamageAndConfuseElseSelfConfuse,  # ナツメのコダックの「こまったねんりき」
    _effects.DamageThenConfuseOnAnyHeads,  # ナツメのモルフォンの「げんかくおんぱ」
    _effects.DamageThenSleepOnHeads,  # R団のミュウツーの「さいみんはどう」
    _effects.DamageThenRetreatLockOnHeads,  # ウツボットの「ようかいえき」
    _effects.SwitchOpponentActiveOnHeads,  # わるいペルシアンの「ゆうわく」
    _effects.DamageThenReturnSelfToDeckOnTails,  # カツラのファイヤーの「ひのとり」
    _effects.AttachEnergyFromDeckToSelf,  # ヤドン（ロケット団）の「ひなたぼっこ」
    _effects.DamageThenLockSelf,  # ナツメのヤドランの「きあいずつき」
    _effects.DamageMinusIfDefenderDamaged,  # エリカのプリンの「やさしいパンチ」
) + (
    # v0.42（docs/power-decisions-v0.42.md）
    _effects.HealChosenOpponentThenDraw,  # ナツメのルージュラの「よいおこない」
    _effects.CoinFlipDamageThenSelfConfuse,  # ラフレシアの「はなびらのまい」
    _effects.ReturnEnergyThenDamage,  # ナツメのケーシィの「エネループ」
    _effects.PlaceCountersToRemainingHpOnHeads,  # ナツメのユンゲラーの「ライフダウン」
    _effects.DamageThenOptionalSelfSwitch,  # わるいフーディンの「テレポートブラスト」
    _effects.EvolveFromDeckOnHeads,  # エリカのピッピの「つきのちから」
    _effects.ReturnOwnPokemonToHandOnHeads,  # エリカのピクシーの「ようせいのきせき」
) + (
    # v0.43（docs/declared-entry-powers-v0.43.md）
    _effects.ChooseOpponentPokemonDamage,  # わるいゴルバットの「ふらふらとぶ」
) + (
    # v0.44（docs/search-evolution-once-attacks-v0.44.md）
    _effects.CoinChooseOpponentPokemonDamage,  # ロケット団のニャースの「こばんなげ」
    _effects.SearchTrainerOnHeads,  # エリカのフシギダネの「おつかい」
    _effects.DamageThenReturnSelfToHandOnHeads,  # カスミのヒトデマンの「スターブーメラン」
    _effects.EvolveSelfFromDeck,  # ロケット団のコイキングの「たきのぼりしんか」
    _effects.OnceAfterEntryNoDamageOnTails,  # ひっさつばり・ネギでたたく・りゅうのきおく
    _effects.CoinsAllHeadsSpreadDamageExceptSelf,  # サカキのギャラドスの「あらしをよぶ」
    _effects.DamageThenSwitchOpponentIfNotKnockedOut,  # サカキのギャラドスの「りゅうのたつまき」
    _effects.DamageThenPoisonAndParalyzeOnHeads,  # キョウのスピアーの「しんけいどく」
    _effects.SpecialPoisonOnHeadsWithoutDamage,  # キョウのコクーンの「どくどくえき」
    _effects.ReturnHandThenRevealBasicEnergy,  # ナツメのバリヤードの「てじな」
    _effects.CoinPutOpponentDiscardOnDeckTop,  # カツラのマンキーの「わるいいたずら」
    _effects.CoinDrawOrReturnHandToDeck,  # _____のラッキーの「ラッキーたまご」
) + (
    # v0.45（docs/conditional-damage-energy-v0.45.md）
    _effects.DamageFailUnlessOpponentStatus,  # 第1弾のゴーストの「ゆめくい」
    _effects.DamageThenLastingAttackCoinCheckOnHeads,  # カスミのタッツー（HP 50）の「スミをかける」
    _effects.DamageMultipliedAgainstType,  # カスミのジュゴンの「こおりのつぶて」
    _effects.DamageThenPoisonAndConfuseOnAllHeads,  # キョウのアーボの「とつぜんどく」
    _effects.SelfStatusWithoutDamage,  # キョウのアーボックの「どくをためる」
    _effects.DamageIfSelfStatusThenOpponentStatus,  # キョウのアーボックの「ポイズンパワー」
    _effects.CoinSwitchOpponentThenStatus,  # キョウのベトベターの「ベトベトハンド」
    _effects.DamageAndSelfDamageThenPreventDamageOnHeads,  # わるいカメックスの「ロケットタックル」
    _effects.DamageThenMoveOpponentEnergyToBench,  # わるいレアコイルの「じりょくせん」
    _effects.DiscardExcessEnergyForDamage,  # カツラのリザードンの「ファイヤーブレス」
    _effects.DamageThenAttachEnergyFromDiscardToSelf,  # R団のサンダーの「プラズマ」
    _effects.DamageAndSelfDamagePerAttachedEnergyCard,  # R団のサンダーの「エレクトロバーン」
    _effects.ZeroDamageBelowNextTurn,  # イワークの「かたくなる」
    _effects.HalfRemainingHpDamage,  # ラッタの「いかりのまえば」
    _effects.ReturnReceivedDamageOnHeads,  # R団のエビワラーの「クロスカウンター」
    _effects.PutOwnerBasicFromDeckOntoBenchOnHeads,  # タケシのイシツブテ（HP 40）の「たすけをよぶ」
    _effects.DamageIgnoringResistance,  # タケシのイシツブテ（HP 40）の「スパイラルショット」
    _effects.CoinOpponentDeckTopDiscardTrainerElseHand,  # サカキのニャース（HP 40）の「てつだうふり」
)

# v0.29 まで、ヒトカゲ（PMCG1-014）の「ひのこ」は未対応で、「登録のないワザ」の例に使っていた。v0.30 で登録したので、その性質を確かめる
# テストは、この登録だけを除いた登録表を使う（製品の登録表は変えない）
NO_EMBER_EFFECTS = DEFAULT_EFFECTS.without_attacks("test-no-ember", [AttackKey(CHARMANDER, 1)])

# v0.30 まで、リザードン（PMCG1-021）は「実装を登録していないポケモンパワー（エナジーバーン）とワザ（ほのおのうず）を持つ 2 進化」の参照カードで、
# 未対応のカードの例に使っていた（v0.7 でフーディンから引き継いだ）。v0.31 で対応にしたので、その性質を確かめるテストは、この 2 つの登録だけを除いた
# 登録表と、その登録表で分類した写しのカードの組（``no_charizard_pool``）を使う（製品の登録表は変えない）
NO_CHARIZARD_EFFECTS = DEFAULT_EFFECTS.without_powers("test-no-charizard", [_effects.PowerKey(CHARIZARD, 0)]).without_attacks(
    "test-no-charizard", [AttackKey(CHARIZARD, 0)])


def no_charizard_pool():
    """リザードンの登録を除いた登録表（``NO_CHARIZARD_EFFECTS``）で分類した、同梱の写しのカードの組（v0.31）。"""
    from kyuura_engine.cards import pool_from_extract, read_extract
    return pool_from_extract(read_extract(), NO_CHARIZARD_EFFECTS)


# v0.36 まで、化石の秘密のベトベター（PMCG3-003）は「ちいさくなる」が未実装の参照カードだった（v0.8）。v0.37 で対応にしたので、その性質を
# 確かめるテストは、この 2 つのワザの登録だけを除いた登録表と、その登録表で分類した写しのカードの組（``no_fossil_grimer_pool``）を使う
NO_FOSSIL_GRIMER_EFFECTS = DEFAULT_EFFECTS.without_attacks("test-no-fossil-grimer", [AttackKey(FOSSIL_GRIMER, 0), AttackKey(FOSSIL_GRIMER, 1)])


def no_fossil_grimer_pool():
    """化石の秘密のベトベターの登録を除いた登録表（``NO_FOSSIL_GRIMER_EFFECTS``）で分類した、同梱の写しのカードの組（v0.37）。"""
    from kyuura_engine.cards import pool_from_extract, read_extract
    return pool_from_extract(read_extract(), NO_FOSSIL_GRIMER_EFFECTS)


# v0.44 まで、第1弾のゴースト（PMCG1-047）は「ゆめくい」が未実装の参照カードだった（v0.9）。v0.45 で対応にしたので、その性質を確かめるテストは、
# この 2 つのワザの登録だけを除いた登録表と、その登録表で分類した写しのカードの組（``no_base_haunter_pool``）を使う（製品の登録表は変えない）
NO_BASE_HAUNTER_EFFECTS = DEFAULT_EFFECTS.without_attacks("test-no-base-haunter", [AttackKey(BASE_HAUNTER, 0), AttackKey(BASE_HAUNTER, 1)])


def no_base_haunter_pool():
    """第1弾のゴーストの登録を除いた登録表（``NO_BASE_HAUNTER_EFFECTS``）で分類した、同梱の写しのカードの組（v0.45）。"""
    from kyuura_engine.cards import pool_from_extract, read_extract
    return pool_from_extract(read_extract(), NO_BASE_HAUNTER_EFFECTS)


class TwoStepTestEffect(AttackEffect):
    """テスト専用: 2 段階の決定を出すワザの効果（保留中の決定の仕組みを確かめるため）。

    1. ワザを使ったプレイヤーが、相手の場のポケモンを 1〜2 匹選ぶ（場のポケモンの番号）
    2. 同じプレイヤーが、与えるダメージ 10 か 20 を選ぶ
    選んだポケモンに、選んだダメージをそのまま与える（弱点・抵抗力は計算しない。実在のワザではない）。
    """

    implementation_id = "test_two_step"

    def resolve(self, state, use):
        targets = [pokemon.pokemon_id for pokemon in state.players[1 - use.player].in_play()]
        push_attack_decision(state, use, kind="test_choose_targets", player=use.player, options=targets,
                             min_choices=1, max_choices=2, context=(("step", 1),))

    def resume(self, state, use, decision, choices):
        if decision.context_value("step") == 1:
            push_attack_decision(state, use, kind="test_choose_amount", player=use.player, options=(10, 20),
                                 context=(("step", 2), ("targets", tuple(choices))))
            return
        amount = choices[0]
        for pokemon_id in decision.context_value("targets"):
            _, pokemon = state.find_pokemon(pokemon_id)
            pokemon.damage += amount
        state.add_event("test_two_step", targets=decision.context_value("targets"), amount=amount)


def two_step_effects():
    """ワンリキー（PMCG1-053）の「けたぐり」を、テスト専用の 2 段階の効果に置き換えた登録表。"""
    return DEFAULT_EFFECTS.with_attacks("test-two-step", {AttackKey(MACHOP, 0): AttackEntry(TwoStepTestEffect(), "けたぐり")})


# ---------------------------------------------------------------- トレーナーを使う決まった手順（v0.2b）

from kyuura_engine import PlayTrainer, ResolveDecision  # noqa: E402


def trainer_command(state: GameState):
    """番のプレイヤーが、決まった手順でトレーナーを使うなら、そのコマンド。使わないなら None。

    - マサキ: 手札にあれば使う（山札が 0 枚でも使える。p.312）
    - きずぐすり: 自分の場にダメージカウンターののったポケモンがいれば使う
    - ポケモンいれかえ: 控えがいて、バトル場のポケモンにダメージがあり、それよりダメージの少ない控えがいれば使う
    """
    player = state.current_player
    p = state.players[player]

    def in_hand(card_id):
        return next((u for u in p.hand if state.cards[u].card_id == card_id), None)

    bill, potion, switch = in_hand(BILL), in_hand(POTION), in_hand(SWITCH)
    if bill is not None:
        return PlayTrainer(player, bill)
    if potion is not None and any(pokemon.damage for pokemon in p.in_play()):
        return PlayTrainer(player, potion)
    if switch is not None and p.bench and p.active.damage and min(b.damage for b in p.bench) < p.active.damage:
        return PlayTrainer(player, switch)
    return None


def trainer_policy_command(state: GameState, *, janken_winner: int = 0):
    """``scripted_command`` に、トレーナーを使う手順と、トレーナーの決定への答えを加えたもの（統合テスト用）。

    プラスパワー（v0.2c）は、ワザを使う直前に、手札にあるだけつける。ディフェンダー（v0.2e）は、ワザを使う・番を
    終える直前に、手札にあるだけ自分の対戦ポケモンにつける（相手の番にワザを受けるのはバトル場のポケモン）。

    決定には、扱いを決められるもののうち、きずぐすりならダメージのいちばん多いポケモン、
    それ以外は最初のものを選ぶ。
    """
    if state.phase is Phase.DECISION:
        d = state.decision
        unresolved = d.context_value("unresolved_choices", ())
        options = [o for o in d.options if o not in unresolved]
        if d.context_value("use", (None, None, None))[2] == POTION:
            options.sort(key=lambda pid: -state.find_pokemon(pid)[1].damage)
        return ResolveDecision(d.player, d.id, (options[0],))
    if state.phase is Phase.MAIN:
        command = trainer_command(state)
        if command is not None:
            return command
        scripted = scripted_command(state, janken_winner=janken_winner)
        if isinstance(scripted, (UseAttack, EndTurn)):
            # 番を終える前に、手札のディフェンダーをすべてつける（v0.2e。決定では最初の選べるもの = 対戦ポケモンを選ぶ。
            # ディフェンダーのないデッキでは何もしない）
            p = state.players[state.current_player]
            defender = next((u for u in p.hand if state.cards[u].card_id == DEFENDER), None)
            if defender is not None:
                return PlayTrainer(state.current_player, defender)
        if isinstance(scripted, UseAttack):
            # ワザを使う直前に、手札のプラスパワーをすべてつける（v0.2c。プラスパワーのないデッキでは何もしない）
            p = state.players[state.current_player]
            pluspower = next((u for u in p.hand if state.cards[u].card_id == PLUSPOWER), None)
            if pluspower is not None:
                return PlayTrainer(state.current_player, pluspower)
        return scripted
    return scripted_command(state, janken_winner=janken_winner)


# ---------------------------------------------------------------- コイン（v0.2d。テスト専用の乱数の制御）

from kyuura_engine.coins import CoinSide  # noqa: E402

H, T = CoinSide.HEADS, CoinSide.TAILS


def rng_for_coins(*sides: CoinSide, start: int = 0) -> random.Random:
    """次に ``getrandbits(1)`` を len(sides) 回使うと、その結果（1 = おもて）になる乱数（テスト専用）。

    seed を 0 から順に探すので、毎回同じ乱数になる。エンジンのコインは 1 枚につき ``getrandbits(1)`` を 1 回
    使う（kyuura_engine/coins.py）。
    """
    wanted = [1 if side is CoinSide.HEADS else 0 for side in sides]
    for seed in range(start, start + 100000):
        probe = random.Random(seed)
        if [probe.getrandbits(1) for _ in wanted] == wanted:
            return random.Random(seed)
    raise AssertionError("条件に合う乱数が見つからない")


def with_coin_results(state: GameState, *sides: CoinSide) -> GameState:
    """テスト専用: 次に投げるコインの結果を ``sides`` にした状態（複製。渡した状態は変えない）。"""
    new = state.clone()
    new.rng = rng_for_coins(*sides)
    return new


# ---------------------------------------------------------------- 解決の設定の指定（v0.15b。v0.16b から経路はない）

from kyuura_engine.engine import apply_command_with  # noqa: E402


def apply_kernel(state: GameState, command, **options):
    """解決の設定（``options`` は ``preflight``・``catalog``）を指定して処理する（``engine.apply_command_with``）。v0.15b では経路 ``KERNEL`` を
    選ぶ入口だった。v0.16b で v0.13 の経路（``apply_legacy``）を外したので、経路はなく、解決の基盤だけが処理する。"""
    return apply_command_with(state, command, **options)


def coin_events(state: GameState, since: int = 0) -> list[dict]:
    return [dict(e) for e in state.log[since:] if e["kind"] == "coin_flip"]


def coin_results(state: GameState, since: int = 0) -> list[str]:
    return [e["result"] for e in coin_events(state, since)]


# ディフェンダー（v0.2e）を入れた 60 枚のデッキ（プラスパワー・ドードー・ほかのトレーナーと組み合わせる）
DEFENDER_DECK = expand_decklist({
    DODUO: 4, GROWLITHE: 4, RATTATA: 4, DRATINI: 4, VOLTORB: 4, BILL: 4, POTION: 2, SWITCH: 2, PLUSPOWER: 4, DEFENDER: 4,
    FIRE: 24,
})
DEFENDER_DECK_B = expand_decklist({
    STARYU: 4, SEEL: 4, DIGLETT: 4, MACHOP: 4, HITMONCHAN: 4, BILL: 2, PLUSPOWER: 2, DEFENDER: 4, WATER: 16, FIGHTING: 16,
})

# ピカチュウ（v0.2f）を入れた 60 枚のデッキ（両方にピカチュウ。プラスパワー・ディフェンダー・ドードーと組み合わせる）
PIKACHU_DECK = expand_decklist({
    PIKACHU: 4, RATTATA: 4, VOLTORB: 4, DRATINI: 4, DODUO: 4, PLUSPOWER: 4, DEFENDER: 4, BILL: 2, LIGHTNING: 30,
})
PIKACHU_DECK_B = expand_decklist({
    PIKACHU: 4, DIGLETT: 4, MACHOP: 4, HITMONCHAN: 4, RATTATA: 4, PLUSPOWER: 2, DEFENDER: 2, LIGHTNING: 18, FIGHTING: 18,
})

# ドードー（v0.2d）を入れた 60 枚のデッキ（たねポケモン 20 枚 + トレーナー + 基本エネルギー）
DODUO_DECK = expand_decklist({DODUO: 4, GROWLITHE: 4, PONYTA: 4, RATTATA: 4, VOLTORB: 4, FIRE: 40})
DODUO_TRAINER_DECK = expand_decklist({
    DODUO: 4, GROWLITHE: 4, RATTATA: 4, DRATINI: 4, VOLTORB: 4, BILL: 4, POTION: 2, SWITCH: 2, PLUSPOWER: 4, FIRE: 28,
})
