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
from kyuura_engine.stadiums import bench_limit  # v0.57
from kyuura_engine.state import (
    ASLEEP,
    COUNTER_KINDS,
    Marker,
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
KANGASKHAN = "PMCG2-046"  # ガルーラ（第2弾。v0.34〜v0.67 は保留。v0.68 で利用者が示した修正を写しに当てはめて対応。こどものおつかい（無）・れんぞくパンチ（無無無無）20×）
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
# v0.46（docs/continuous-powers-v0.46.md）。常にはたらく特殊能力を持つ 8 枚と、関連する 3 枚（どれも kyuura データの採用）
MR_MIME = "PMCG2-027"  # バリヤード（ポケモンジャングル。HP 40・超・弱点 超・にげる 1。［なぞのかべ］・ヨガのポーズ（超無）10+）
ERIKAS_DRATINI = "PMCG5-063"  # エリカのミニリュウ（リーダーズスタジアム。HP 40・無色・抵抗力 超 -30・にげる 1。［ふしぎなバリアー］・しっぽでつく（無無）10+）。DRATINI（PMCG1-065）・ロケット団のミニリュウ（PMCG4-051）と別のカード
ERIKAS_IVYSAUR = "PMCG6-010"  # エリカのフシギソウ（闇からの挑戦。エリカのフシギダネから進化。HP 60・草・弱点 炎・にげる 2。［くつろぐかおり］・ダブルはっぱカッター（草草草）40×）
DARK_PRIMEAPE = "PMCG4-041"  # わるいオコリザル（ロケット団。マンキーから進化。HP 60・闘・弱点 超・にげる 1。［きょうぼう］・あばれくるう（闘闘）40）。PRIMEAPE（PMCG2-031）と別の名前
DODRIO = "PMCG2-040"  # ドードリオ（ポケモンジャングル。ドードーから進化。HP 70・無色・弱点 雷・抵抗力 闘 -30・にげる 0。［にげるサポート］・いかり（無無無）10+）
DARK_MUK = "PMCG4-007"  # わるいベトベトン（ロケット団。ベトベターから進化。HP 60・草・弱点 超・にげる 2。［ねんちゃくえき］・ヘドロパンチ（草草）20）。MUK・KOGAS_MUK と別の名前
DARK_VILEPLUME = "PMCG4-010"  # わるいラフレシア（ロケット団。わるいクサイハナから進化。HP 60・草・弱点 炎・にげる 2。［アレルギーかふん］・はなびらのうず（草草草）30×）
SNORLAX = "PMCG2-047"  # カビゴン（ポケモンジャングル。HP 90・無色・弱点 闘・抵抗力 超 -30・にげる 4。［めんえき］・のしかかり（無無無無）30）。ROCKETS_SNORLAX と別の名前
ERIKAS_VENUSAUR = "PMCG6-017"  # エリカのフシギバナ（闇からの挑戦。エリカのフシギソウから進化。HP 90・草・弱点 炎・にげる 2。せいちょう（草）・かくさんソーラービーム（草草草草）20）
ERIKAS_EXEGGCUTE = "PMCG5-012"  # エリカのタマタマ（リーダーズスタジアム。HP 50・草・弱点 炎・にげる 1。リフレクター（超）・タマゴばくだん（草無）40）
ERIKAS_EXEGGUTOR = "PMCG5-013"  # エリカのナッシー（リーダーズスタジアム。エリカのタマタマから進化。HP 70・草・弱点 炎・にげる 2。サイコエクスチェンジ（超）・ふみつけ（草無無）30+）
V0_46_POWER_POKEMON = (MR_MIME, ERIKAS_DRATINI, ERIKAS_IVYSAUR, DARK_PRIMEAPE, DODRIO, DARK_MUK, DARK_VILEPLUME, SNORLAX)  # 常にはたらく特殊能力を持つ 8 枚
V0_46_POKEMON = V0_46_POWER_POKEMON + (ERIKAS_VENUSAUR, ERIKAS_EXEGGCUTE, ERIKAS_EXEGGUTOR)  # 写しの組 pool_v0_46 の並び
# v0.47（docs/fossil-hidden-info-v0.47.md）。ポケモンとして場に出せるトレーナーカード 2 枚・化石のポケモン 5 枚・見えない情報の 4 枚・トレーナーの使用を禁止する 2 枚
# （どれも kyuura データの採用。場での HP は pcg-search.com の同じ版のページ）
MYSTERIOUS_FOSSIL = "PMCG3-046"  # なにかの化石（化石の秘密。トレーナーカード。場ではポケモン: HP 10・タイプなし・弱点なし・抵抗力なし・ワザなし）
CLEFAIRY_DOLL = "PMCG1-091"  # ピッピ人形（第1弾。トレーナーカード。場ではポケモン: HP 10・タイプなし・弱点なし・抵抗力なし・ワザなし）
OMANYTE = "PMCG3-015"  # オムナイト（化石の秘密。なにかの化石から進化。HP 40・水・弱点 草・にげる 1。［おみとおし］・みずでっぽう（水）10+）
OMASTAR = "PMCG3-021"  # オムスター（化石の秘密。オムナイトから進化する 2 進化。HP 70・水・弱点 草・にげる 1。みずでっぽう（水無）20+・とげキャノン（水水）30×）
KABUTO = "PMCG3-035"  # カブト（化石の秘密。なにかの化石から進化。HP 30・闘・弱点 草・にげる 1。［カブトアーマー］・ひっかく（無）10）
KABUTOPS = "PMCG3-040"  # カブトプス（化石の秘密。カブトから進化する 2 進化。HP 60・闘・弱点 草・にげる 1。するどいかま（闘闘）30・すいとる（闘闘闘闘）40）
AERODACTYL = "PMCG3-041"  # プテラ（化石の秘密。なにかの化石から進化。HP 60・闘・弱点 草・抵抗力 闘 -30・にげる 2。［げんしのちから］・つばさでうつ（無無無）30）
JUNGLE_MANKEY = "PMCG2-028"  # マンキー（ポケモンジャングル。HP 30・闘・弱点 超・にげる 0。［スパイ］・ひっかく（無）10）。MANKEY（PMCG4-039。ロケット団）と別のカード
ROCKET_RATTATA = "PMCG4-045"  # コラッタ（ロケット団。HP 40・無色・弱点 闘・抵抗力 超 -30・にげる 0。［わるふざけ］・でんこうせっか（無）10+）。RATTATA（PMCG1-060）と別のカード
HYPNO = "PMCG3-032"  # スリーパー（化石の秘密。スリープから進化。HP 90・超・弱点 超・にげる 2。みらいよち（超）・ナイトヘッド（超超超）30）
LT_SURGES_EEVEE = "PMCG5-062"  # マチスのイーブイ（リーダーズスタジアム。HP 40・無色・弱点 闘・抵抗力 超 -30・にげる 1。おどろかす（無）・ひっかく（無無）20）
LT_SURGES_JOLTEON = "PMCG5-042"  # マチスのサンダース（リーダーズスタジアム。マチスのイーブイから進化。HP 70・雷・弱点 闘・にげる 1。こうしゅうは（雷無）20・いかりのサンダー（雷雷雷）30+）
FOSSIL_PSYDUCK = "PMCG3-010"  # コダック（化石の秘密。HP 50・水・弱点 雷・にげる 1。ずつう（超）・みだれひっかき（水）10×）。PSYDUCK（PMCG4-019）と別のカード
V0_47_TRAINERS = (MYSTERIOUS_FOSSIL, CLEFAIRY_DOLL)
V0_47_POKEMON = (OMANYTE, OMASTAR, KABUTO, KABUTOPS, AERODACTYL, JUNGLE_MANKEY, ROCKET_RATTATA, HYPNO, LT_SURGES_EEVEE, LT_SURGES_JOLTEON, FOSSIL_PSYDUCK)
V0_47_CARDS = V0_47_TRAINERS + V0_47_POKEMON  # 写しの組 pool_v0_47 の並び
# v0.48（docs/effective-pokemon-properties-v0.48.md）。場のポケモンの今有効な最大HP・タイプ・弱点・抵抗力を変える 7 枚（どれも kyuura データの採用）
PORYGON = "PMCG1-064"  # ポリゴン（第1弾。HP 30・無色・弱点 闘・抵抗力 超 -30・にげる 1。テクスチャー1（無）・テクスチャー2（無無））
ROCKET_PORYGON = "PMCG4-050"  # ポリゴン（ロケット団。HP 40・無色・弱点 闘・抵抗力 超 -30・にげる 0。テクスチャー1（無）・サイケこうせん（無無無）20）
VENOMOTH = "PMCG2-015"  # モルフォン（ポケモンジャングル。コンパンから進化。HP 70・草・弱点 炎・抵抗力 闘 -30・にげる 0。［へんしょく］・りんぷん（草草）10）
SABRINAS_GASTLY = "PMCG6-049"  # ナツメのゴース（闇からの挑戦。HP 40・超・弱点なし・抵抗力 闘 -30・にげる 0。［ガスのからだ］・ガスでつつむ（超超）30）。GASTLY（PMCG3-029）と別のカード
SABRINAS_HAUNTER = "PMCG6-050"  # ナツメのゴースト（闇からの挑戦。ナツメのゴースから進化。HP 50・超・弱点なし・抵抗力 闘 -30・にげる 0。ナイトスピリッツ（超超）30×）
SABRINAS_GENGAR = "PMCG6-054"  # ナツメのゲンガー（闇からの挑戦。ナツメのゴーストから進化する 2 進化。HP 80・超・弱点なし・抵抗力 闘 -30・にげる 1。ダメージぞうふく（超）・やみのこえ（超超超）40）
KOGAS_DITTO = "PMCG6-072"  # キョウのメタモン（闇からの挑戦。HP 40・無色・弱点 闘・抵抗力 超 -30・にげる 1。きょだいか（無）・はたく（無）10）
V0_48_POKEMON = (PORYGON, ROCKET_PORYGON, VENOMOTH, SABRINAS_GASTLY, SABRINAS_HAUNTER, SABRINAS_GENGAR, KOGAS_DITTO)  # 写しの組 pool_v0_48 の並び
# v0.49（docs/virtual-attacks-transformation-v0.49.md）。ワザの出どころ・今の姿の共通の処理で加えた 4 枚（どれも kyuura データの採用）
SABRINAS_ALAKAZAM = "PMCG6-053"  # ナツメのフーディン（闇からの挑戦。ナツメのユンゲラーから進化する 2 進化。HP 80・超・弱点 超・にげる 3。［サイコリンク］・メガバーン（超無無無）60）
DITTO = "PMCG3-042"  # メタモン（化石の秘密。HP 50・無色・弱点 闘・抵抗力 超 -30・にげる 1。［へんしん］。ワザなし）。KOGAS_DITTO（PMCG6-072）と別のカード
BROCKS_NINETALES = "PMCG5-019"  # タケシのキュウコン（リーダーズスタジアム。タケシのロコン（PMCG5-018）から進化。HP 70・炎・弱点 水・にげる 1。「ばける」・おにび（炎炎）30）
RECALL = "PMCG5-071"  # 思い出させる（リーダーズスタジアム。トレーナー）
V0_49_POKEMON = (SABRINAS_ALAKAZAM, DITTO, BROCKS_NINETALES)
V0_49_CARDS = (SABRINAS_ALAKAZAM, DITTO, BROCKS_NINETALES, RECALL)  # 写しの組 pool_v0_49 の並び
# v0.50（docs/mew-devolution-spray-v0.50.md）。退化の共通の処理で加えた 2 枚（どれも kyuura データの採用）
MEW = "PMCG3-033"  # ミュウ（化石の秘密。HP 50・超・弱点 超・にげる 1。サイコウェーブ（超）10×・たいかビーム（超超））
DEVOLUTION_SPRAY = "PMCG1-086"  # 退化スプレー（第1弾。トレーナー）
V0_50_POKEMON = (MEW,)
V0_50_CARDS = (MEW, DEVOLUTION_SPRAY)  # 写しの組 pool_v0_50 の並び
# v0.51（docs/discard-to-bench-v0.51.md）。トラッシュのたねポケモンを持ち主のベンチに出す共通の処理で加えた 3 枚（どれも kyuura データの採用）
SABRINAS_HYPNO = "PMCG6-051"  # ナツメのスリーパー（闇からの挑戦。ナツメのスリープ（PMCG6-045）から進化する 1 進化。HP 70・超・弱点 超・にげる 2。よみがえらせる（超）・ふりこののろい（超超）20×）
REVIVE = "PMCG1-078"  # 元気のかけら（第1弾。トレーナー）。元気のかたまり（写しにない）とは別のカード
POKEMON_FLUTE = "PMCG1-084"  # ポケモンの笛（第1弾。トレーナー）
V0_51_POKEMON = (SABRINAS_HYPNO,)
V0_51_CARDS = (SABRINAS_HYPNO, REVIVE, POKEMON_FLUTE)  # 写しの組 pool_v0_51 の並び
# v0.52（docs/field-return-v0.52.md）。場のポケモンを場から手札・山札にもどす共通の処理で加えた 3 枚（どれも kyuura データの採用）
MR_FUJI = "PMCG3-048"  # フジろうじん（化石の秘密。トレーナー。pcg-search.com の一覧の番号は 047/048）
SCOOP_UP = "PMCG1-092"  # ポケモン回収（第1弾。トレーナー。pcg-search.com の一覧の番号は 087/096）
ERIKAS_DRAGONAIR = "PMCG5-066"  # エリカのハクリュー（リーダーズスタジアム。エリカのミニリュウから進化する 1 進化。HP 80・無色・弱点なし・抵抗力 超 -30・にげる 2。ふぶき（無無無）30・つれさる（無無無無））。DRAGONAIR（PMCG1-069）・DARK_DRAGONAIR（PMCG4-052）と別のカード
V0_52_POKEMON = (ERIKAS_DRAGONAIR,)
V0_52_CARDS = (MR_FUJI, SCOOP_UP, ERIKAS_DRAGONAIR)  # 写しの組 pool_v0_52 の並び
# v0.53（docs/search-retrieval-trainers-v0.53.md）。山札・トラッシュからカードを選ぶトレーナー 10 枚（pcg-search.com の一覧の番号はコメントのとおり。カード id の番号とは別の体系）
ENERGY_SEARCH = "PMCG3-044"  # エネルギー転送（化石の秘密。044/048）
POKE_BALL = "PMCG2-048"  # モンスターボール（ポケモンジャングル。048/048）
BOSS_WAY = "PMCG4-060"  # ボスのやりかた（ロケット団。058/065）
BROCK_TRAINING = "PMCG5-077"  # タケシの育て方（リーダーズスタジアム。069/096）
MISTYS_TEARS = "PMCG5-069"  # カスミのなみだ（リーダーズスタジアム。075/096）
ERIKAS_MAIDS = "PMCG5-072"  # エリカのお付き（リーダーズスタジアム。085/096）
MAINTENANCE = "PMCG1-085"  # メンテナンス（第1弾。095/096）
ITEM_FINDER = "PMCG1-087"  # ダウジングマシーン（第1弾。077/096）
RECYCLE = "PMCG3-047"  # リサイクル（化石の秘密。048/048）
NIGHTLY_GARBAGE_RUN = "PMCG4-057"  # 夜の廃品回収（ロケット団。060/065）
V0_53_CARDS = (ENERGY_SEARCH, POKE_BALL, BOSS_WAY, BROCK_TRAINING, MISTYS_TEARS, ERIKAS_MAIDS, MAINTENANCE, ITEM_FINDER, RECYCLE,
               NIGHTLY_GARBAGE_RUN)  # 写しの組 pool_v0_53 の並び
# v0.54（docs/hand-deck-trainers-v0.54.md）: 手札の入れ替え・ドロー・情報の確認のトレーナー 10 枚（kyuura データの採用。pcg-search.com の一覧の番号）
IMPOSTER_OAK = "PMCG1-089"  # にせオーキドはかせ（第1弾。082/096）
IMPOSTER_OAKS_REVENGE = "PMCG4-059"  # にせオーキドの逆襲（ロケット団。055/065）
GAMBLER = "PMCG3-045"  # ギャンブラー（化石の秘密。045/048）
SABRINAS_GAZE = "PMCG6-078"  # ナツメの眼（闇からの挑戦。076/098）
BLAINES_LAST_RESORT = "PMCG6-081"  # カツラの奥の手（闇からの挑戦。086/098）
ERIKA = "PMCG5-083"  # エリカ（リーダーズスタジアム。084/096）
SECRET_MISSION = "PMCG5-088"  # スパイ作戦（リーダーズスタジアム。080/096）
BLAINES_GAMBLE = "PMCG6-076"  # カツラのギャンブル（闇からの挑戦。087/098）
LASS = "PMCG1-095"  # ミニスカート（第1弾。094/096）
POKEDEX = "PMCG1-082"  # ポケモン図鑑 HANDY505（第1弾。089/096）
V0_54_CARDS = (IMPOSTER_OAK, IMPOSTER_OAKS_REVENGE, GAMBLER, SABRINAS_GAZE, BLAINES_LAST_RESORT, ERIKA, SECRET_MISSION, BLAINES_GAMBLE, LASS,
               POKEDEX)  # 写しの組 pool_v0_54 の並び
# v0.55（docs/instant-trainers-v0.55.md）: すぐに使い終わるトレーナー 16 枚（kyuura データの採用。pcg-search.com の一覧の番号）
MISTYS_WRATH = "PMCG5-075"  # カスミのいかり（リーダーズスタジアム。073/096）
ROCKETS_SNEAK_ATTACK = "PMCG4-061"  # ロケット団のおねーさん（ロケット団。061/065）
GOOD_MANNERS = "PMCG5-082"  # 礼儀作法（リーダーズスタジアム。088/096）
TRASH_EXCHANGE = "PMCG6-077"  # トラッシュ交換（闇からの挑戦。082/098）
ENERGY_REMOVAL = "PMCG1-070"  # エネルギー・リムーブ（第1弾。072/096）
SUPER_ENERGY_REMOVAL = "PMCG1-088"  # 超エネルギーリムーブ（第1弾。078/096）
FULL_HEAL = "PMCG1-080"  # なんでもなおし（第1弾。081/096）
POKEMON_CENTER = "PMCG1-083"  # ポケモンセンター（第1弾。090/096）
SLEEP_TRAINER = "PMCG4-054"  # ねむれ!ねむれ!（ロケット団。056/065。kyuura の種類 rockets_secret_machine）
ENERGY_FLOW = "PMCG5-067"  # エネルギーサーキュレート（リーダーズスタジアム。079/096）
ERIKAS_KINDNESS = "PMCG5-084"  # エリカの親切（リーダーズスタジアム。089/096）
BROCK_TRAINER = "PMCG5-089"  # タケシ（リーダーズスタジアム。067/096。トレーナー）
GIOVANNIS_LAST_RESORT = "PMCG6-096"  # サカキの切り札（闇からの挑戦。091/098）
SABRINA_TRAINER = "PMCG6-098"  # ナツメ（闇からの挑戦。074/098。トレーナー）
WARP_POINT = "PMCG6-080"  # ワープポイント（闇からの挑戦。078/098）
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
SUPER_POTION = "PMCG1-075"  # いいきずぐすり（v0.54 まで参照カード（実装を登録していないトレーナー）。v0.55 で対応。第1弾。070/096）
V0_55_CARDS = (MISTYS_WRATH, ROCKETS_SNEAK_ATTACK, GOOD_MANNERS, TRASH_EXCHANGE, ENERGY_REMOVAL, SUPER_ENERGY_REMOVAL, SUPER_POTION, FULL_HEAL, POKEMON_CENTER,
               SLEEP_TRAINER, ENERGY_FLOW, ERIKAS_KINDNESS, BROCK_TRAINER, GIOVANNIS_LAST_RESORT, SABRINA_TRAINER, WARP_POINT)  # 写しの組 pool_v0_55 の並び
# v0.56（docs/trainer-decisions-turn-effects-v0.56.md）: 相手の決定・相手の場へ出す・番を終える・効果でサイドを取る・期限のある効果のトレーナー 10 枚
ERIKAS_PERFUME = "PMCG5-073"  # エリカの香水（リーダーズスタジアム。085/096）
LT_SURGE_TRAINER = "PMCG5-092"  # マチス（リーダーズスタジアム。077/096。トレーナー。「マチスの」ポケモン・マチスの交渉と取りちがえない）
ROCKETS_TRAP = "PMCG5-096"  # ロケット団のワナ（リーダーズスタジアム。095/096）
ROCKET_GRUNT = "PMCG6-089"  # ロケット団員（闇からの挑戦。093/098）
LT_SURGES_TREATY = "PMCG5-081"  # マチスの交渉（リーダーズスタジアム。080/096）
MISTYS_WISH = "PMCG5-086"  # カスミのわがまま（リーダーズスタジアム。075/096）
MISTY_TRAINER = "PMCG5-085"  # カスミ（リーダーズスタジアム。071/096。トレーナー。「カスミの」ポケモン・カスミのいかり・カスミのなみだと取りちがえない）
KOGA_TRAINER = "PMCG6-094"  # キョウ（闇からの挑戦。079/098。トレーナー。「キョウの」ポケモンと取りちがえない）
INVISIBLE_WALL = "PMCG6-079"  # 見えない壁（闇からの挑戦。082/098）
ROCKETS_EXPERIMENT = "PMCG6-091"  # ロケット団の実験（闇からの挑戦。094/098）
V0_56_CARDS = (ERIKAS_PERFUME, LT_SURGE_TRAINER, ROCKETS_TRAP, ROCKET_GRUNT, LT_SURGES_TREATY, MISTYS_WISH, MISTY_TRAINER, KOGA_TRAINER, INVISIBLE_WALL,
               ROCKETS_EXPERIMENT)  # 写しの組 pool_v0_56 の並び
# v0.57: スタジアム 14 枚（docs/stadiums-v0.57.md）。どれも kyuura データの採用
PEWTER_CITY_GYM = "PMCG5-079"  # ニビシティジム（リーダーズスタジアム。071/096）
CERULEAN_CITY_GYM = "PMCG5-080"  # ハナダシティジム（リーダーズスタジアム。077/096）
RESISTANCE_GYM = "PMCG5-091"  # 抵抗力低下ジム（リーダーズスタジアム。093/096）
ROCKETS_TRAINING_GYM = "PMCG5-095"  # ロケット団の特訓ジム（リーダーズスタジアム。095/096）
CINNABAR_CITY_GYM = "PMCG6-085"  # グレンタウンジム（闇からの挑戦。089/098）
CELADON_CITY_GYM = "PMCG5-078"  # タマムシシティジム（リーダーズスタジアム。090/096）
FUCHSIA_CITY_GYM = "PMCG6-086"  # セキチクシティジム（闇からの挑戦。084/098）
SAFFRON_CITY_GYM = "PMCG6-090"  # ヤマブキシティジム（闇からの挑戦。079/098）
NARROW_GYM = "PMCG5-070"  # せまいジム（リーダーズスタジアム。091/096）
ROCKETS_MINEFIELD_GYM = "PMCG6-092"  # ロケット団の爆発ジム（闇からの挑戦。096/098）
VIRIDIAN_CITY_GYM = "PMCG6-097"  # トキワシティジム（闇からの挑戦。092/098）
VERMILION_CITY_GYM = "PMCG5-076"  # クチバシティジム（リーダーズスタジアム。083/096）
NO_REMOVAL_GYM = "PMCG5-094"  # リムーブ禁止ジム（リーダーズスタジアム。094/096）
CHAOS_GYM = "PMCG5-087"  # 錯乱ジム（リーダーズスタジアム。092/096）
V0_57_CARDS = (PEWTER_CITY_GYM, CERULEAN_CITY_GYM, RESISTANCE_GYM, ROCKETS_TRAINING_GYM, CINNABAR_CITY_GYM, CELADON_CITY_GYM, FUCHSIA_CITY_GYM,
               SAFFRON_CITY_GYM, NARROW_GYM, ROCKETS_MINEFIELD_GYM, VIRIDIAN_CITY_GYM, VERMILION_CITY_GYM, NO_REMOVAL_GYM, CHAOS_GYM)
# v0.58（docs/stadium-reuse-special-energy-v0.58.md）。スタジアムの処理を使う 3 枚と特殊エネルギー 4 枚
BROCKS_GRAVELER = "PMCG5-052"  # タケシのゴローン（リーダーズスタジアム。051/096。タケシのイシツブテから進化）
BROCKS_GOLEM = "PMCG5-053"  # タケシのゴローニャ（リーダーズスタジアム。052/096。タケシのゴローンから進化）
SABRINAS_PSYCHIC_CONTROL = "PMCG6-088"  # ナツメのサイキックコントロール（闇からの挑戦。トレーナー）
DOUBLE_COLORLESS_ENERGY = "PMCG1-096"  # 無色2個エネルギー（第1弾。096/096）
POTION_ENERGY = "PMCG4-063"  # きずぐすり配合エネルギー（ロケット団。062/065）
FULL_HEAL_ENERGY = "PMCG4-064"  # なんでもなおし配合エネルギー（ロケット団。063/065）
RAINBOW_ENERGY = "PMCG4-065"  # レインボーエネルギー（ロケット団。064/065）
V0_58_POKEMON = (BROCKS_GRAVELER, BROCKS_GOLEM)
V0_58_ENERGIES = (DOUBLE_COLORLESS_ENERGY, POTION_ENERGY, FULL_HEAL_ENERGY, RAINBOW_ENERGY)
V0_58_CARDS = (BROCKS_GRAVELER, BROCKS_GOLEM, SABRINAS_PSYCHIC_CONTROL, *V0_58_ENERGIES)
# v0.59（docs/energy-control-power-suppression-v0.59.md）。特殊能力を止める効果・エネルギーの扱いを変える 6 枚
BUZZAP_ELECTRODE = "PMCG1-040"  # マルマイン（第1弾。040/096。ビリリダマから進化。HP 80・雷・弱点 闘・にげる 1。［エネエネ］・でんげき（雷雷雷）50）。ELECTRODE（第2弾）と別のカード
BLAINE_TRAINER = "PMCG6-093"  # カツラ（闇からの挑戦。085/000。トレーナー）。「カツラの」ポケモン・カツラの奥の手・カツラのギャンブルと別のカード
BROCKS_PROTECTION = "PMCG5-090"  # タケシの保護（リーダーズスタジアム。070/096。トレーナー）
MISTYS_TENTACOOL = "PMCG5-030"  # カスミのメノクラゲ（リーダーズスタジアム。025/096。HP 50・水・弱点 雷・にげる 1。クリスタルビーム（水無）20）。TENTACOOL と別の名前
DARK_ARBOK = "PMCG4-008"  # わるいアーボック（ロケット団。002/065。アーボから進化。HP 60・草・弱点 超・にげる 2。ショックアイ（草草）・どくのきり（草草草）10）
GOOP_GAS_ATTACK = "PMCG4-056"  # まきちらせ!ベトベトガス（ロケット団。059/065。トレーナー）
V0_59_POKEMON = (BUZZAP_ELECTRODE, MISTYS_TENTACOOL, DARK_ARBOK)
V0_59_TRAINERS = (BLAINE_TRAINER, BROCKS_PROTECTION, GOOP_GAS_ATTACK)
V0_59_CARDS = (BUZZAP_ELECTRODE, BLAINE_TRAINER, BROCKS_PROTECTION, MISTYS_TENTACOOL, DARK_ARBOK, GOOP_GAS_ATTACK)
# v0.60（docs/coins-defense-rebellion-v0.60.md）。控えへのコイン・ダメージを受けない効果・攻撃するときの特殊能力・相手の効果を受けないダメージの 4 枚
FOSSIL_ZAPDOS = "PMCG3-026"  # サンダー（化石の秘密。026/048。HP 80・雷・抵抗力 闘・にげる 2。サンダーストーム（雷雷雷雷）40）。第1弾のサンダー ZAPDOS と別のカード
ROCKETS_SCYTHER = "PMCG5-016"  # R団のストライク（リーダーズスタジアム。001/096。HP 60・草・弱点 炎・抵抗力 闘・にげる 1。かげぶんしん（草）・こうそくカマ（草無無）40）
MISTYS_GYARADOS = "PMCG5-035"  # カスミのギャラドス（リーダーズスタジアム。035/096。カスミのコイキングから進化。HP 100・水・弱点 草・抵抗力 闘・にげる 3。［はんこう］・ハイドロクラッシュ（水水水水）70）
BROCKS_SANDSLASH = "PMCG5-050"  # タケシのサンドパン（リーダーズスタジアム。045/096。タケシのサンドから進化。HP 70・闘・弱点 草・抵抗力 雷・にげる 1。スピードスター（闘無）20・とげボール（闘闘）30）
V0_60_POKEMON = (FOSSIL_ZAPDOS, ROCKETS_SCYTHER, MISTYS_GYARADOS, BROCKS_SANDSLASH)
V0_60_CARDS = V0_60_POKEMON
# v0.61（docs/reactive-powers-trainer-damage-v0.61.md）。ワザ・にげる・残りHPではたらく特殊能力とトレーナーのダメージの 4 枚
DARK_GYARADOS = "PMCG4-025"  # わるいギャラドス（ロケット団。024/065。コイキングから進化。HP 70・水・弱点 草・抵抗力 闘・にげる 2。［ファイナルビーム］・れいとうビーム（水水水）30）
DARK_DUGTRIO = "PMCG4-043"  # わるいダグトリオ（ロケット団。039/065。ディグダから進化。HP 50・闘・弱点 草・抵抗力 雷・にげる 2。［おとしあな］・つきおとす（闘闘）20+）
BROCKS_PRIMEAPE = "PMCG5-051"  # タケシのオコリザル（リーダーズスタジアム。048/096。タケシのマンキーから進化。HP 70・闘・弱点 超・にげる 1。［ずらかる］・おおあばれ（闘闘闘）60）
DIGGER = "PMCG4-055"  # バトル場は穴だらけ!（ロケット団。057/065。トレーナー。kyuura の種類 rockets_secret_machine）
V0_61_POKEMON = (DARK_GYARADOS, DARK_DUGTRIO, BROCKS_PRIMEAPE)
V0_61_CARDS = (DARK_GYARADOS, DARK_DUGTRIO, BROCKS_PRIMEAPE, DIGGER)
# v0.62（docs/history-attacks-v0.62.md）。前の番のワザの履歴を読むワザ・相手を手札にもどすワザの 5 枚と、確定した修正を当てはめたベロリンガ
PIDGEOTTO = "PMCG1-066"  # ピジョン（第1弾。060/096。ポッポから進化。HP 60・無色・弱点 雷・抵抗力 闘・にげる 1。ふきとばし（無無）20・オウムがえし（無無無））
SPEAROW = "PMCG2-034"  # オニスズメ（ポケモンジャングル。035/048。HP 50・無色・弱点 雷・抵抗力 闘・にげる 0。つつく（無）10・オウムがえし（無無無））
FEAROW = "PMCG2-038"  # オニドリル（ポケモンジャングル。036/048。オニスズメから進化。HP 70・無色・弱点 雷・抵抗力 闘・にげる 0。こうそくいどう（無無無）20・ドリルくちばし（無無無無）40）
PIDGEOT = "PMCG2-043"  # ピジョット（ポケモンジャングル。034/048。ピジョンから進化。HP 80・無色・弱点 雷・抵抗力 闘・にげる 0。つばさでうつ（無無）20・ハリケーン（無無無）30）
BROCKS_DUGTRIO = "PMCG6-060"  # タケシのダグトリオ（闇からの挑戦。056/098。タケシのディグダから進化。HP 60・闘・弱点 草・抵抗力 雷・にげる 1。あながくれ（闘）・ドリルホール（闘闘無）60）
LICKITUNG = "PMCG2-041"  # ベロリンガ（ポケモンジャングル。043/048。HP 90・無色・弱点 闘・抵抗力 超・にげる 3。まきつくベロ（無）10・ちょうおんぱ（無無））
V0_62_POKEMON = (PIDGEOTTO, SPEAROW, FEAROW, PIDGEOT, BROCKS_DUGTRIO, LICKITUNG)
V0_62_CARDS = V0_62_POKEMON
# v0.63（docs/hidden-card-trainers-v0.63.md）: 公開・非公開の状態を扱うトレーナー 4 枚
HERE_COMES_TEAM_ROCKET = "PMCG4-062"  # ロケット団参上!（第4弾ロケット団。お互いのサイドをすべておもてにする）
TICKLING_MACHINE = "PMCG6-084"  # くすぐりマシーン（闇からの挑戦。ロケット団秘密メカ。「おもて」なら相手の手札を置いておく、「うら」なら番が終わる）
CHALLENGE = "PMCG4-058"  # たたきつけろ!挑戦状（第4弾ロケット団。受けないなら 2 枚引く、受けるならお互いに山札からたねポケモンをうらにしてベンチに出す）
BLAINES_QUIZ_3 = "PMCG6-082"  # カツラのクイズ その3（闇からの挑戦。手札のポケモンを置き、ワザの名前を伝え、相手が名前を答える）
V0_63_CARDS = (HERE_COMES_TEAM_ROCKET, TICKLING_MACHINE, CHALLENGE, BLAINES_QUIZ_3)
# v0.64（docs/geodude-line-unbounded-coins-v0.64.md）: 化石の秘密のイシツブテの系統 3 枚（「タケシの」系統とは別のカード）
FOSSIL_GEODUDE = "PMCG3-034"  # イシツブテ（化石の秘密。035/048。HP 50・闘・弱点 草・にげる 1。れんぞくいしなげ（闘無）10×）
FOSSIL_GRAVELER = "PMCG3-037"  # ゴローン（化石の秘密。036/048。イシツブテから進化。HP 60・闘・弱点 草・にげる 2。かたくなる（闘闘）・いわおとし（闘闘無）40）
FOSSIL_GOLEM = "PMCG3-038"  # ゴローニャ（化石の秘密。037/048。ゴローンから進化。HP 80・闘・弱点 草・にげる 4。いわころがり（闘闘闘無）60・じばく（闘闘闘闘）100）
V0_64_POKEMON = (FOSSIL_GEODUDE, FOSSIL_GRAVELER, FOSSIL_GOLEM)
V0_64_CARDS = V0_64_POKEMON
# v0.65（docs/reactive-decisions-v0.65.md）: ワザの途中の任意の決定を使う 3 枚
KOGAS_NINJA_TRICK = "PMCG6-083"  # キョウ秘伝,変わり身の術（闇からの挑戦。081/098。トレーナー。バトル場の「キョウのポケモン」につけ、相手がワザを使う時に控えと入れ替えてよい）
MISTYS_TENTACRUEL = "PMCG5-033"  # カスミのドククラゲ（リーダーズスタジアム。026/096。カスミのメノクラゲから進化。HP 70・水・弱点 雷・にげる 0。［にげこむ］・クラゲどく（水水無無）30）
BROCKS_RHYDON = "PMCG5-055"  # タケシのサイドン（リーダーズスタジアム。055/096。タケシのサイホーンから進化。HP 80・闘・弱点 草・抵抗力 雷 -30・にげる 3。［ベンチガード］・ラリアット（闘闘無無）70）
V0_65_POKEMON = (MISTYS_TENTACRUEL, BROCKS_RHYDON)
V0_65_CARDS = (KOGAS_NINJA_TRICK, MISTYS_TENTACRUEL, BROCKS_RHYDON)
# v0.66（docs/optional-trainers-v0.66.md）。のぞむなら選ぶ効果・コインのやり直し・じゃんけんのトレーナー 3 枚
CHARITY = "PMCG5-074"  # お上品攻撃（リーダーズスタジアム。087/096。トレーナー。対戦ポケモンにつけ、ワザのダメージを好きなだけ小さくしてよい。相手の番が終わったら手札にもどす）
SABRINAS_ESP = "PMCG6-087"  # ナツメのESP（闇からの挑戦。075/000。トレーナー。ナツメのポケモンにつけ、ワザの説明文のコイントスをやり直してよい。番の終わりにトラッシュ）
MISTYS_DUEL = "PMCG5-068"  # カスミの勝負（リーダーズスタジアム。074/096。トレーナー。じゃんけんの勝者が手札を山札にもどして切り、5 枚引く）
V0_66_CARDS = (CHARITY, SABRINAS_ESP, MISTYS_DUEL)
LT_SURGES_SECRET_PLAN = "PMCG5-093"  # マチスの秘策（リーダーズスタジアム。082/096。トレーナー。手札から 1 枚をうらにしてベンチに出してよい。v0.67）
V0_67_CARDS = (LT_SURGES_SECRET_PLAN,)
# v0.68（docs/final-pmcg-cards-v0.68.md）。PMCG1〜PMCG6 の残りのポケモン 3 枚
IMAKUNI_DODUO = "PMCG6-074"  # イマクニ？のドードー（闇からの挑戦。［にげまくり］・ハモる。簡略化した仕様）
V0_68_POKEMON = (KANGASKHAN, KOGAS_MUK, IMAKUNI_DODUO)
V0_68_CARDS = V0_68_POKEMON

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
              トラッシュする番は、プラスパワーなら使った番、ディフェンダーなら使った番 + 1（不変条件: 使った番は持ち主の番）。
              "markers"（v0.90）は、のっているマーカー・カウンターの [種類, ...]（色マーカーは (種類, 色)）。のせたのはカウンター（ほね・たべもの）なら持ち主、
              マーカーなら相手、のせた番は今の番の 1 つ前（いまの姿になった番より前なら、いまの姿になった番）、ワザは "test"。のせたログ marker_added も置く）
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
        for entry in spec.get("markers", ()):
            # v0.90: マーカー・カウンター（ログはあとで置く）
            kind, color = (entry, None) if isinstance(entry, str) else entry
            placer = owner if kind in COUNTER_KINDS else 1 - owner
            result.markers = (*result.markers, Marker(kind, placer, result.card, "test", max(result.current_form_turn, turn_number - 1), color))
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
    # v0.90: "markers" を書いたポケモンには、のせたログ marker_added も置く（不変条件: のっている数はログと対応する）
    for owner, p in enumerate(states):
        for pokemon in p.in_play():
            for index, marker in enumerate(pokemon.markers):
                current = state.turn_number
                state.turn_number = marker.turn
                extra = {} if marker.color is None else {"color": marker.color.value}
                count = sum(1 for m in pokemon.markers[:index + 1] if m.kind == marker.kind)
                state.add_event("marker_added", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, marker=marker.kind, **extra, count=count,
                                by_player=marker.player, source_card=marker.source_card, effect=marker.attack)
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
        if bench and len(p.bench) < bench_limit(state, player) and basics_in_hand(state, player):  # v0.57: せまいジムの上限
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
    # v0.46（docs/continuous-powers-v0.46.md）
    _effects.DamageThenSelfConfuse,  # わるいオコリザルの「あばれくるう」
    _effects.CoinsTimesDamageSelfConfuse,  # わるいラフレシアの「はなびらのうず」
    _effects.AttachEnergyFromHandOnHeads,  # エリカのフシギバナの「せいちょう」
    _effects.DamageThenExactBenchTargets,  # エリカのフシギバナの「かくさんソーラービーム」
    _effects.HalveDamageNextTurn,  # エリカのタマタマの「リフレクター」
    _effects.ShuffleHandIntoDeckThenDraw,  # エリカのナッシーの「サイコエクスチェンジ」
    # v0.47（docs/fossil-hidden-info-v0.47.md）
    _effects.ArrangeDeckTopEffect,  # スリーパーの「みらいよち」
    _effects.LookOpponentHandCardToDeck,  # マチスのイーブイの「おどろかす」
    _effects.LockOpponentTrainersNextTurn,  # コダック（化石の秘密）の「ずつう」
    _effects.DamageThenLockOpponentTrainersOnHeads,  # マチスのサンダースの「こうしゅうは」
    _effects.DamagePlusOwnCountersThenSelfDamageOnTails,  # マチスのサンダースの「ぶちかます」
    # v0.48（docs/effective-pokemon-properties-v0.48.md）
    _effects.ChangeOpponentWeakness,  # ポリゴン 2 枚の「テクスチャー1」
    _effects.ChangeOwnResistance,  # 第1弾のポリゴンの「テクスチャー2」
    _effects.DamageThenPoisonAndConfuseOnHeads,  # モルフォンの「りんぷん」
    _effects.CoinsPerNamedPokemonDamage,  # ナツメのゴーストの「ナイトスピリッツ」
    _effects.PlaceCountersOnDamagedOpponentPokemon,  # ナツメのゲンガーの「ダメージぞうふく」
    _effects.DamageThenCoinsReturnOpponentToDeck,  # ナツメのゲンガーの「やみのこえ」
    _effects.SetMaxHpOnHeads,  # キョウのメタモンの「きょだいか」
    _effects.DamageIfSelfMaxHpSet,  # キョウのメタモンの「はたく」
    # v0.50（docs/mew-devolution-spray-v0.50.md）
    _effects.DamageTimesDefenderEnergyCards,  # ミュウの「サイコウェーブ」
    _effects.DevolveChosenPokemon,  # ミュウの「たいかビーム」
    # v0.51（docs/discard-to-bench-v0.51.md）
    _effects.BenchBasicFromEitherDiscard,  # ナツメのスリーパーの「よみがえらせる」
    _effects.CoinsPerDefenderCountersDamage,  # ナツメのスリーパーの「ふりこののろい」
    # v0.52（docs/field-return-v0.52.md）
    _effects.ReturnBothActivesToDeck,  # エリカのハクリューの「つれさる」
    _effects.SelfDestructThenDiscardStadium,  # v0.58: タケシのゴローンの「ばくれつ」（v0.39 のじばく + 場のスタジアムをトラッシュする要素 DiscardStadium）
    _effects.ChooseOpponentPokemonDamageAndPowerLock,  # v0.59: わるいアーボックの「ショックアイ」（相手の場のポケモン 1 匹に 10 + 持続する効果 CannotUsePowers）
    _effects.DamagePoisonAndBenchDamage,  # v0.59: わるいアーボックの「どくのきり」
    _effects.DamageThenAttachLockOnHeads,  # v0.59: カスミのメノクラゲの「クリスタルビーム」（持続する効果 CannotAttachEnergy）
    _effects.DamageThenCoinPerOpponentBench,  # v0.60: サンダーの「サンダーストーム」（控えごとのコインと、同じコインの「うら」の数の自分へのダメージ。新しい要素 CoinPerOpponentBench）
    _effects.SelfTailsDamageGuard,  # v0.60: R団のストライクの「かげぶんしん」（持続する効果 TailsDamageGuard）
    _effects.DamageIgnoringDefenderEffects,  # v0.60: タケシのサンドパンの「スピードスター」（Damage の defender_effects）
    _effects.OpponentCoinTailsBonusDamage,  # v0.61: わるいダグトリオの「つきおとす」（相手が投げるコインの「うら」で追加。値 OpponentTailsBonus）
    _effects.DamageSelfDamageThenDiscardStadium,  # v0.61: タケシのオコリザルの「おおあばれ」（相手 → 自分 → スタジアムのトラッシュ）
    _effects.DamageIfUsedAttackLastTurn,  # v0.62: タケシのダグトリオの「ドリルホール」（前の自分の番に使ったワザの記録 A）
    _effects.RepeatReceivedAttack,  # v0.62: ピジョンの「オウムがえし」（前の相手の番に受けたワザの記録 B）
    _effects.ReflectReceivedDamageAndEffects,  # v0.62: オニスズメの「オウムがえし」（前の相手の番に受けた結果の記録 C）
    _effects.DamageThenReturnOpponentToHand,  # v0.62: ピジョットの「ハリケーン」
) + (
    # v0.64（docs/geodude-line-unbounded-coins-v0.64.md）
    _effects.CoinsUntilTailsDamage,  # 化石の秘密のイシツブテの「れんぞくいしなげ」
) + (
    # v0.68（docs/final-pmcg-cards-v0.68.md 4 章）
    _effects.SimplifiedSongDamage,  # イマクニ？のドードーの「ハモる」（簡略化した仕様。DamageOnly と同じ要素の並び）
) + (
    # v0.70（docs/non-pack-effect-reuse-v0.70.md）: ダメージのない型 2 つ（既存の要素だけの並び）
    _effects.StatusByCoinWithoutDamage,  # ニョロゾ（ES1-017・QSG-015）の「ぐるぐる」
    _effects.AttachEnergyFromDiscardToSelf,  # マチスのピカチュウ（GD3-002）の「たいでん」
) + (
    # v0.71（docs/reprint-text-variants-v0.71.md 6 章）: エネルギーカードをトラッシュする要素とダメージ（既存の要素だけの並び）
    _effects.DiscardEnergyCardsThenDamageZeroIfLacking,  # プロモのリザードン（PR1-030）の「ほのおのうず」
) + (
    # v0.72（docs/status-coins-effect-reuse-v0.72.md 3 章）: 拡張パック以外の商品のポケモン 43 枚のうち、既存の型で表せないワザ
    _effects.CoinsHeadsTimesBonusDamage,  # ルギア（PRN-042）の「エアロブラスト」（値 PrintedPlusHeadsTimes）
    _effects.DamageThenStatusSelfAndOpponent,  # エリカのクサイハナ（GD4-003）の「ゆめみのまい」・「くさいにおい」
    _effects.PoisonAndSleepWithoutDamage,  # エリカのウツドン（GD4-007）の「ねむけどく」
    _effects.DamageThenWakeOpponent,  # ナツメのルージュラ（GD6-012）の「めざめのキッス」（要素 WakeOpponent）
    _effects.DamageAndOptionalFullDrain,  # ゴルバット（ES1-009）・パラセクト（ES1-011）の「きゅうけつ」（Drain の optional）
    _effects.DamageThenMoveOneEnergyToBench,  # マチスのエレブー（GD3-010・PR1-040）の「デンキとばし」（要素 MoveOneEnergyToBench）
    _effects.RevealBasicEnergyFromDeck,  # エリカのピッピ（GD4-012）の「おつきみ」（RevealTrainerFromDeck の category）
    _effects.DamageThenForceSwitchAfterDamage,  # タケシのサイホーン（GD1-012）の「つのでなげる」（ForceSwitch の after_damage）
) + (
    # v0.75（docs/search-energy-pokemon-v0.75.md）
    _effects.DrawThenSwitchSelf,  # タケシのズバット（GD1-001）の「しらせる」（Draw → SelfSwitch の required）
    _effects.RevealNamedPokemonFromDeckAny,  # カスミのメノクラゲ（GD2-003）の「くらげのむれ」
    _effects.CoinsRecoverEnergyByHeads,  # カツラのロコン（GD5-003）の「おにびあつめ」
    _effects.AttachEnergyFromDeckToSelfExactly,  # カツラのガーディ（GD5-006）の「もえあがる」（AttachFromDeck の zero=required）
    _effects.AttachEnergyFromDeckToBench,  # ナツメのスリープ（GD6-009）の「エナジーサポート」
    _effects.CoinAttachEnergyFromDeckToSelf,  # キングラー（ES3-014）の「しおまねき」（AttachFromDeck の max_cards・local_coin・shuffle）
    _effects.DamageThenDoubleDamageNextTurn,  # キングラー（ES3-014）の「もろばバサミ」（持続する効果 DoubledDamage）
    _effects.AttachDiscardEnergyCardsToSelf,  # ミュウツー（PR1-007・PR1-008）の「エネルギーきゅうしゅう」（AttachFromDiscard の energy_type None）
) + (
    # v0.76（docs/persistent-attack-modifiers-v0.76.md）
    _effects.ReduceDamageToSelfNextOpponentTurn,  # ヒトカゲ（ES1-013）などの「なきごえ」（OpponentReducedDamage の until_turn_end）
    _effects.LockOpponentAttackOnHeads,  # コンパン（ES3-004）の「かなしばり」（OpponentAttackLock の local_coin）
    _effects.CoinNextTurnMultiplyElseLockAttack,  # ワンリキー（ES2-021・QSG-035）の「きあいいっぱつ」（Coin → SelfNextTurnAttackDamage・SelfAttackLock の gate）
    _effects.AttackLockWhileSourceActiveOnHeads,  # ヒノアラシ（PF1-004）などの「にらみつける」（OpponentAttackLockWhileSourceActive の max_hp None・local_coin）
) + (
    # v0.78（docs/darkness-metal-energy-v0.78.md）
    _effects.CoinsPerOwnPokemonDamage,  # ニューラ（neo1-056）の「ふくろだたき」（HeadsTimesNamedPokemon の names None）
    _effects.DiscardOpponentTrainersThenDamage,  # デルビル（neo2-039・NIP2X-005）の「ごうだつ」（DiscardOpponentTrainers → Damage）
    _effects.RetreatLockWithoutDamage,  # デルビル（neo4-081）の「おいつめる」（OpponentRetreatLock だけ）
    _effects.DamageThenSelfCannotAttack,  # エアームド（NIP1X-005）の「メタルスラッシュ」（持続する効果 CannotAttackNextOwnTurn）
    # v0.79（docs/shared-checks-pokemon-reuse-v0.79.md 5 章）: 既存の要素を組み合わせた 11 の型
    _effects.DamageThenParalyzeAndOpponentBenchOnHeads,  # バブルシャワー・ギガショック・ダイヤモンドダスト
    _effects.DamageThenPreventAttackDamageOnHeads,  # ピカチュウ（neo1-036）の「こうそくいどう」（PreventAttackDamage）
    _effects.DamageThenOpponentBenchOnHeads,  # モココ（neo3-027）の「エレキテール」
    _effects.CoinBonusDamageAndConfuse,  # ルージュラ（neo3-018）の「あやしいおどり」
    _effects.CoinBonusPerOwnCounter,  # ブルー（neo3-048）の「いかりのずつき」
    _effects.HealSelfWithoutDamage,  # ミニリュウ（neo4-087）の「だっぴ」
    _effects.DamageThenDiscardOneOnTails,  # カツラのヒトカゲ（GD5-001）の「ファイヤーテール」
    _effects.CoinChooseOpponentBenchDamage,  # ナツメのゴースト（GD6-007）の「かげからおそう」
    _effects.SearchTrainerRequiredOnHeads,  # ヤドキング（SI-014）の「ひらめく」
    _effects.CoinDiscardAllOpponentTrainers,  # ニューラ（PF3-003）の「だましとる」
    _effects.FailOnTailsDamageThenSelfCannotAttack,  # ハガネール（PRN-014）の「メタルクラッシュ」
) + (
    # v0.82: エネルギーをトラッシュするワザの 9 つの型（docs/energy-discard-return-v0.82.md）
    _effects.CoinDiscardEnergyCardThenDamage,
    _effects.OptionalDiscardEnergyBonusDamage,
    _effects.DamageThenDiscardAllEnergyCards,
    _effects.OptionalDiscardAllSetDamage,
    _effects.DiscardEachTypeThenDamage,
    _effects.ChooseBenchThenAttachFromDeck,
    _effects.CoinsDiscardThenBonusDamage,
    _effects.CoinDiscardOneOrAllThenDamage,
    _effects.DamageThenChosenBenchCoinDamage,
) + (
    # v0.83: ひかるポケモン・やさしいポケモンのワザの 24 の型（docs/shining-gentle-pokemon-v0.83.md）
    _effects.ChooseBenchThenDamageAndEnergyBenchDamage,
    _effects.ChooseOwnTypeThenAttachFromHand,
    _effects.CoinBonusAndBenchElseSelfDamage,
    _effects.CoinWashChosenBench,
    _effects.CoinsPerDefenderEnergyChosenStatus,
    _effects.DamageSleepThenHealBothBench,
    _effects.DiscardEnergyThenCoinConfuseElseSleep,
    _effects.DiscardEnergyThenPlusDefenderEnergyUnits,
    _effects.DiscardEnergyThenSpreadThenCoinDiscardEach,
    _effects.EachPlayerLookTopTakeBasicEnergy,
    _effects.EachPlayerMayDrawAttack,
    _effects.EachPlayerRecoverFromDiscard,
    _effects.ExcessEnergyDamageIgnoringResistance,
    _effects.FailOnTailsPlusOwnCounters,
    _effects.FailOnTailsSpreadBothThenSelfCannotAttack,
    _effects.FailUnlessEqualEnergyCardsDamage,
    _effects.HealChosenBenchByEnergy,
    _effects.HealOwnPokemonWithoutDamage,
    _effects.LookTopTakeOneThenShuffle,
    _effects.PlusDefenderSpecialEnergyCardsDamage,
    _effects.PlusIfDefenderMoreEnergyDamage,
    _effects.RevealOneNamedPokemonFromDeck,
    _effects.SelfReflectShield,
    _effects.ThreeCoinsStatusByHeads,
) + (
    # v0.84: やさしいポケモンのワザの 14 の型（docs/light-powers-evolution-v0.84.md）
    _effects.AmountIfDefenderDamagedDamage,
    _effects.BenchBabyOrBasicFromOwnDiscardAttack,
    _effects.CoinSetIfDefenderDarkDamage,
    _effects.CoinsTimesDamageThenParalyzeIfAtLeast,
    _effects.DamageByDefenderStage,
    _effects.DamageThenAttackEffectGuard,
    _effects.DamageThenBenchAttackDamageGuard,
    _effects.DamageThenBubbleJump,
    _effects.DamageThenOpponentMayDraw,
    _effects.DamageThenOptionalDiscardStadium,
    _effects.EachPlayerEvolutionSong,
    _effects.ReturnOwnBenchToDeckAttack,
    _effects.SwitchSelfThenStatusGuardAttack,
    _effects.ZeroDamageAtLeastNextTurn,
    # v0.85（docs/entry-powers-energy-lifecycle-v0.85.md）
    _effects.AttachFromDeckUpToNamedCount,
    _effects.CoinChosenSideHealAttack,
    _effects.CoinsPerOwnCountersBonusDamage,
    _effects.DamageThenMillOwnDeck,
    _effects.DamageThenStatusImmunityNextTurn,
    _effects.DiscardEnergyCardsThenDamageNoneIfLacking,
    _effects.DiscardFireThenDamageBothBenches,
    _effects.PlusDiscardTypeCardsThenReturnToDeck,
    # v0.86（docs/entry-energy-evolution-reactions-v0.86.md 7 章）
    _effects.CoinPerOpponentPokemonDamageThenHealDealt,
    _effects.DamageThenLockOpponentHandTrainersOnHeads,
    _effects.DamageThenParalyzeOrSleepByTwoCoins,
    _effects.DamageThenProtectOwnBench,
    _effects.DamageThenStopDefenderPowers,
    _effects.DiscardTypeCardsThenDamageNoneIfLacking,
    # v0.87（docs/movement-damage-reactions-v0.87.md 3 章・8 章）
    _effects.DamageThenSelfSleepThenSleepOpponentOnHeads,
    _effects.DamageThenSuppressOpponentPowersOnHeads,
    _effects.DamageThenSwitchBothActives,
    # v0.88（docs/type-energy-colors-v0.88.md 6 章）
    _effects.ChosenColorEnergySpreadDamage,
    _effects.OwnBasicColorTypeSpreadDamage,
    _effects.PlusDistinctBasicEnergyColors,
    _effects.ChangeOwnResistanceOptional,
    _effects.ChangeWeaknessAndResistanceOptional,
    # v0.89（docs/selected-target-damage-v0.89.md 5 章。選ぶ要素 ChooseTarget と選んだ個体へのダメージ・効果の要素の組み合わせ）
    _effects.ChooseOpponentPokemonDamageIgnoringEffects,
    _effects.ChooseOpponentPokemonOwnEnergyDamage,
    _effects.ChooseOpponentBenchThenCoinDamage,
    _effects.DamageThenChooseBenchCoinDamage,
    _effects.ChooseOpponentPokemonCoinsDamage,
    _effects.ChooseOpponentPokemonTargetEnergyDamage,
    _effects.ChooseOpponentPokemonDamageThenDiscardEnergyOnHeads,
    _effects.CoinChooseEitherPokemonHeal,
    _effects.ChooseOpponentPokemonCoinsPerOwnEnergyDamage,
    _effects.CoinChooseOpponentPokemonDamageApplyingWR,
    _effects.CoinActiveElseChosenBenchDamage,
    _effects.CoinChooseBenchElseSelfDamage,
    _effects.DamageThenTailsChooseOwnPokemonDamage,
    # v0.90（docs/markers-counters-v0.90.md 4〜7 章。マーカー・ダメージカウンター以外のカウンターをのせる・消費する・取りのぞく）
    _effects.MarkOpponentIfAbsent,
    _effects.MarkSelfIfAbsent,
    _effects.MarkSelfUpToLimit,
    _effects.DamageThenRemoveOwnMarkerParalyzeOnHeads,
    _effects.OptionalRemoveOwnMarkersBonusDamage,
    _effects.CoinMarkOpponent,
    _effects.CoinPaintOpponent,
    _effects.DiscardAllEnergyThenFullRecovery,
    # v0.91（docs/marker-check-field-reset-v0.91.md 4〜7 章。くろこげマーカー・ひらいしんマーカー・色マーカーののせ替え・オールクリア）
    _effects.DamageThenCoinMarkOpponentIfAbsent,
    _effects.ChooseOpponentPokemonMarkIfAbsent,
    _effects.DamageThenMarkedPokemonDamage,
    _effects.ChooseOpponentPokemonReplaceColorMarker,
    _effects.AllClear,
    # v0.92（docs/power-suppression-lasting-locks-v0.92.md 4〜9 章。期間と消える契機を明示した禁止・受けるダメージの +20・回復のあとのどく・持っている効果だけを除くだましうち・
    # おたがいの場の特殊能力の抑止・固定の値を加える「うら」が出るまでのコイン）
    _effects.CoinAttackAndRetreatLock,
    _effects.PeriodLockAttack,
    _effects.ReceivedAttackDamageBonusAttack,
    _effects.DamageDrainThenPoison,
    _effects.ChooseOpponentPokemonDamageIgnoringHeldEffects,
    _effects.DamageThenFieldPowerSuppression,
    _effects.CoinsUntilTailsBonusDamage,
    # v0.93（docs/active-leave-locks-v0.93.md 5〜7 章。バトル場をはなれられない効果・ダメージのあとの期間を明示したワザの禁止・相手を入れ替えて新しく出てきたポケモンをマヒ・
    # にげるの禁止とワザを使うときのコイン）
    _effects.DamageThenPeriodLock,
    _effects.CoinBonusDamageThenLeaveLock,
    _effects.DamageThenPoisonThenLeaveLockOnHeads,
    _effects.SwitchOpponentThenParalyzeNewOnHeads,
    _effects.DamageThenRetreatLockAndAttackCoinCheck,
    # v0.94（docs/switch-return-attacks-v0.94.md 4〜8 章。選ぶ側・必要な控え・コインを分けた相手の入れ替え・ダメージのあとの必ずの自分の入れ替え・同じコインで分かれる入れ替え・
    # ダメージの前の任意の入れ替え・相手を手札にもどすか入れ替える）
    _effects.SwitchOpponentActiveRequiringBench,
    _effects.ForceSwitchOnHeadsWithoutDamage,
    _effects.DamageThenSelfSwitch,
    _effects.DamageThenStatusOnHeadsElseSelfSwitch,
    _effects.CoinBonusDamageElseForceSwitch,
    _effects.OptionalSwitchOpponentThenDamage,
    _effects.CoinReturnOpponentToHandElseForceSwitch,
    # v0.95（docs/private-looks-deck-movement-v0.95.md 5〜10 章。相手の手札を見る・見た手札のトレーナーカードの枚数のダメージ・山札の上からちょうどの枚数を見て並べかえる・
    # コインで見た手札のトレーナーカードを山札にもどす・相手の山札の一番上を見てトラッシュ・ダメージのあと山札をトラッシュして手札に加える・ついているトレーナーを山札にもどす）
    _effects.LookOpponentHandAttack,
    _effects.DamageTimesLookedHandTrainers,
    _effects.ArrangeDeckTopExactlyEffect,
    _effects.CoinLookOpponentHandTrainerToDeck,
    _effects.OpponentDeckTopDiscardIfTrainer,
    _effects.DamageThenMillReturnTypeEnergy,
    _effects.ReturnOpponentAttachedTrainerToDeck,
    # v0.99（docs/unown-perform-help-history-v0.99.md 4 章。前の相手の番にワザによるダメージを受けていたら追加する）
    _effects.PlusIfDamagedByAttackLastOpponentTurn,
    # v0.100（docs/sketch-perish-song-history-v0.100.md。前の相手の番に相手が使ったワザを使う・ねむりで前の自分の番に受けていたら「きぜつ」させる）
    _effects.UseLastOpponentAttack,
    _effects.KnockOutIfAsleepAndReceived,
    # v0.104（docs/healing-pokemon-v0.104.md。回復の量・対象・とりのぞくかの選択と、名前のポケモンの数のダメージ・自分へのダメージとこのワザの禁止）
    _effects.CoinChooseOwnPokemonHealAll,
    _effects.OwnNamedPokemonCountDamage,
    _effects.CoinsHealSelfTimes,
    _effects.HealAllSelfThenSelfSleep,
    _effects.DamageAndSelfDamageThenLockSelf,
    _effects.OptionalHealSelf,
    _effects.HealBothActivesThenSleep,
    # v0.105（docs/recovery-evolution-coin-branches-v0.105.md。回復のあとの山札からの進化・相手のエネルギーの個数のダメージと与えたぶんの回復・3 枚のコインの分岐）
    _effects.CoinHealAllThenEvolveSelfFromDeck,
    _effects.DefenderEnergyUnitsDamageAndFullDrain,
    _effects.CoinsPerDefenderEnergyBonusAndFullDrain,
    _effects.ThreeCoinDamageOrOpponentHeal,
    # v0.106（docs/counts-coins-compositions-v0.106.md。自分のカウンターの追加と自分へのダメージ・「おもて」の数の表・カードの枚数ぶんの上限つきのコイン・相手が取ったサイドの数・
    # 同じコインの追加のダメージと自分へのダメージ）
    _effects.DamagePlusOwnCountersThenSelfDamage,
    _effects.CoinsHeadsTableBonusDamage,
    _effects.CappedCoinsPerAttachedEnergyCardsDamage,
    _effects.DamagePlusOpponentPrizesTaken,
    _effects.CoinsBonusAndSelfDamagePerHeads,
    # v0.107（docs/coin-failure-status-flight-v0.107.md。失敗のコインで決まるどく・じばく・防護と、ダメージのあとのコインで相手か自分がこんらん）
    _effects.FailOnTailsDamageThenPoison,
    _effects.FailOnTailsSelfDestruct,
    _effects.FailOnTailsDamageThenSelfBarrier,
    _effects.DamageThenConfuseOpponentOrSelf,
    # v0.108（docs/damage-modifiers-condition-bonuses-v0.108.md。使うワザのダメージを減らす効果・ダメージのあとの受けるダメージの増加・相手の特殊状態を参照する追加とどく・回復）
    _effects.DamageThenDealtDamageReduction,
    _effects.DealtDamageReductionWithoutDamage,
    _effects.DamageThenReceivedAttackDamageBonus,
    _effects.PlusIfDefenderPoisonedThenPoison,
    _effects.PlusIfDefenderStatusThenCure,
)

# v0.29 まで、ヒトカゲ（PMCG1-014）の「ひのこ」は未対応で、「登録のないワザ」の例に使っていた。v0.30 で登録したので、その性質を確かめる
# テストは、この登録だけを除いた登録表を使う（製品の登録表は変えない）
NO_EMBER_EFFECTS = DEFAULT_EFFECTS.without_attacks("test-no-ember", [AttackKey(CHARMANDER, 1)])

# v0.30 まで、リザードン（PMCG1-021）は「実装を登録していないポケモンパワー（エナジーバーン）とワザ（ほのおのうず）を持つ 2 進化」の参照カードで、
# 未対応のカードの例に使っていた（v0.7 でフーディンから引き継いだ）。v0.31 で対応にしたので、その性質を確かめるテストは、この 2 つの登録だけを除いた
# 登録表と、その登録表で分類した写しのカードの組（``no_charizard_pool``）を使う（製品の登録表は変えない）
# v0.71: プロモのリザードン（PR1-030。リザードンの再録の版。effects.REPRINT_CARDS）の登録も除く（元のカードを保留にする場面で、再録の版だけが残らないように）
NO_CHARIZARD_EFFECTS = DEFAULT_EFFECTS.without_powers("test-no-charizard", [_effects.PowerKey(CHARIZARD, 0), _effects.PowerKey("PR1-030", 0)]).without_attacks(
    "test-no-charizard", [AttackKey(CHARIZARD, 0), AttackKey("PR1-030", 0)])


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
        if not options and d.min_choices == 0:
            return ResolveDecision(d.player, d.id, ())  # v0.61: 使うと止める［ファイナルビーム］など、選ばない（使わない）だけが答えになる決定
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


def _untemper(y: int) -> int:
    """MT19937 の出力の調律（tempering）の逆。"""
    y ^= y >> 18
    y ^= (y << 15) & 0xEFC60000
    result = y
    for _ in range(5):
        result = y ^ ((result << 7) & 0x9D2C5680)
    y = result
    result = y
    for _ in range(3):
        result = y ^ (result >> 11)
    return result & 0xFFFFFFFF


def rng_with_coin_bits(*sides: CoinSide) -> random.Random:
    """次に ``getrandbits(1)`` を len(sides) 回使うと、その結果（1 = おもて）になる乱数（v0.64。テスト専用）。seed を探さず、乱数の内部の状態（MT19937 の
    624 語）を直接決める（``getrandbits(1)`` は次の 32 ビットの出力のいちばん上のビット）。624 回まで。そのあとの出力は決まった別の値（seed 0 の状態の続き）。
    「うら」が出るまで投げるコインの長い「おもて」の並びを、seed を探さずに作るため（``rng_for_coins`` は 16 枚程度までしか見つけられない）。"""
    if len(sides) > 624:
        raise ValueError("624 枚まで")
    words = list(random.Random(0).getstate()[1][:624])
    for i, side in enumerate(sides):
        top = 1 if side is CoinSide.HEADS else 0
        words[i] = _untemper((top << 31) | 0x12345)
    rng = random.Random()
    rng.setstate((3, tuple(words) + (0,), None))
    probe = random.Random()
    probe.setstate(rng.getstate())
    if [probe.getrandbits(1) for _ in sides] != [1 if side is CoinSide.HEADS else 0 for side in sides]:
        raise AssertionError("乱数の状態の組み立ての誤り")
    return rng


def with_coin_bits(state: GameState, *sides: CoinSide) -> GameState:
    """テスト専用（v0.64）: ``with_coin_results`` と同じく次のコインを ``sides`` にした状態（複製）。seed を探さない（``rng_with_coin_bits``）。"""
    new = state.clone()
    new.rng = rng_with_coin_bits(*sides)
    return new


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


def driver_retreat_cost(state, pokemon) -> int:
    """対戦の手順（テストの駆動）が「にげる」に使う、場のポケモン ``pokemon`` の印刷のにげるエネルギーの数。v0.47: なにかの化石・ピッピ人形（場での役割のある
    カード）の「にげる」は決まらない（PF2。印刷の数がない）ので、手順が「にげる」を選ばない数（ついているエネルギーより 1 多い）にする。ほかのポケモンは v0.46 までと
    同じ印刷の数（手順の結果は変わらない）。"""
    cost = state.card_def(pokemon.card).retreat_cost
    return len(pokemon.energy) + 1 if cost is None else cost


# v0.54 まで、いいきずぐすり（PMCG1-075）は「実装を登録していないトレーナー」の参照カードで、未対応のトレーナーの例に使っていた（v0.2b から）。v0.55 で対応にしたので、
# その性質を確かめるテストは、この登録だけを除いた登録表と、その登録表で分類した写しのカードの組（``no_super_potion_pool``）を使う（製品の登録表は変えない）
NO_SUPER_POTION_EFFECTS = DEFAULT_EFFECTS.without_trainers("test-no-super-potion", [SUPER_POTION])


def no_super_potion_pool():
    """いいきずぐすりの登録を除いた登録表（``NO_SUPER_POTION_EFFECTS``）で分類した、同梱の写しのカードの組（v0.55）。"""
    from kyuura_engine.cards import pool_from_extract, read_extract
    return pool_from_extract(read_extract(), NO_SUPER_POTION_EFFECTS)


# v0.69（docs/equivalent-non-pack-cards-v0.69.md 6 章）: 写しの元（カードデータのコミット）を ecb2d69 から 7d3f4ca に上げた。状態は写しの元を
# ``card_data.commit``（state_to_dict）とログ ``game_created`` の ``card_data_commit`` に持つので、v0.68 までに作った固定の参照データ（作り直さない）と比べるときは、
# この 2 か所の値だけを、確かめた移行（今の写しの元 → v0.68 までの写しの元）でもどしてから比べる。ほかの値（状態・ログ・乱数の状態の指紋・card_data のほかの項目）は
# 変えない。もどす前の値が今の写しの元でなければ AssertionError（知らない値を黙って置きかえない）
CARD_DATA_COMMIT_BEFORE_V0_69 = "ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691"
CARD_DATA_COMMIT_SINCE_V0_69 = "7d3f4ca76c084774efb4ac6a1d3a943387e183c3"
# v0.97（docs/unown-research-idfnj-v0.97.md 2 章）: 写しの元を 7d3f4ca から 73a1690 に上げた。移行は連鎖（ecb2d69 → 7d3f4ca → 73a1690。scripts/extract_kyuura_cards.py の
# KYUURA_MIGRATIONS と同じ段）で、もどすときも段を 1 つずつさかのぼる（知らない値・段を飛ばした値を黙って置きかえない）
CARD_DATA_COMMIT_SINCE_V0_97 = "73a169063463bbf7bcaa3137d70cbf9721d11534"
CARD_DATA_COMMIT = CARD_DATA_COMMIT_SINCE_V0_97  # 今の写しの元
CARD_DATA_MIGRATIONS = ((CARD_DATA_COMMIT_BEFORE_V0_69, CARD_DATA_COMMIT_SINCE_V0_69), (CARD_DATA_COMMIT_SINCE_V0_69, CARD_DATA_COMMIT_SINCE_V0_97))


def with_card_data_commit_at(data: dict, commit: str) -> dict:
    """state_to_dict の値（の写し）の、写しの元の 2 か所だけを、今の写しの元から移行の連鎖を段ごとにさかのぼって ``commit`` にもどした新しい値（``data`` は変えない。v0.97）。
    もどす前の値が今の写しの元でなければ、``commit`` が連鎖のコミットでなければ AssertionError。もどした数も確かめる。"""
    import copy

    chain = [CARD_DATA_MIGRATIONS[0][0], *(after for _, after in CARD_DATA_MIGRATIONS)]
    assert chain[-1] == CARD_DATA_COMMIT and commit in chain, commit
    result = copy.deepcopy(data)
    card_data = result.get("card_data")
    assert isinstance(card_data, dict) and card_data.get("commit") == CARD_DATA_COMMIT, card_data
    # 正式な開始（new_game）の状態はログ game_created が 1 つ、盤面を直接作った状態（build_test_state）にはない
    created = [event for event in result.get("log", []) if event.get("kind") == "game_created"]
    assert len(created) <= 1 and all(event.get("card_data_commit") == CARD_DATA_COMMIT for event in created), created
    for before, after in reversed(CARD_DATA_MIGRATIONS):
        if chain.index(after) <= chain.index(commit):
            break
        assert card_data["commit"] == after, (card_data["commit"], after)
        card_data["commit"] = before
        for event in created:
            event["card_data_commit"] = before
    assert card_data["commit"] == commit
    return result


def with_card_data_commit_before_v0_69(data: dict) -> dict:
    """state_to_dict の値（の写し）の、写しの元の 2 か所だけを v0.68 までの値にもどした新しい値（``data`` は変えない）。もどした数も確かめる。v0.97 から、今の写しの元
    （73a1690）から移行の連鎖を段ごとにさかのぼる（``with_card_data_commit_at``）。"""
    return with_card_data_commit_at(data, CARD_DATA_COMMIT_BEFORE_V0_69)


# v0.69（docs/equivalent-non-pack-cards-v0.69.md）: 拡張パック以外の商品の、登録したカードと処理に使う欄が同じカード（写しの組 pool_v0_69 のうち登録のある 84 枚。
# kyuura_engine.effects.EQUIVALENT_CARDS）。登録の一覧を数えるテストは、ここから数える（元のカードの一覧に混ぜない）
V0_69_TRAINERS = ("GD1-015", "GD1-019", "GD2-015", "GD2-016", "GD2-017", "GD2-018", "GD3-015", "GD3-016", "GD3-021", "GD3-022", "GD4-016", "GD4-017",
                  "GD4-018", "GD4-026", "GD5-014", "GD5-015", "GD6-017", "GD6-018", "GD6-019")
V0_69_POKEMON = ("GD1-002", "GD1-009", "GD1-011", "GD1-013", "GD2-004", "GD2-008", "GD2-010", "GD2-012", "GD3-001", "GD3-004", "GD3-005", "GD3-006",
                 "GD3-007", "GD4-002", "GD4-006", "GD4-008", "GD4-010", "GD4-011", "GD4-013", "GD5-002", "GD5-004", "GD5-009", "GD5-010", "GD5-012",
                 "GD6-003", "GD6-004", "GD6-013", "IP1-002", "IP1-013", "IP2-001", "IP2-002", "IP2-014", "IP2-035", "PR1-019", "PR1-031", "PR1-032",
                 "PR1-039", "PR1-047", "PR1-048", "PR1-049", "PR1-050", "PR1-061", "PR1-076", "PR1-080", "PR1-081", "PR1-082", "PR1-083", "PR1-084",
                 "PR1-085", "PR1-086", "PR1-087", "PR1-088", "PR1-089", "NIP1-010", "NIP1-012", "NIP1X-003", "NIP2-001")
V0_69_SPECIAL_ENERGIES = ("GD1-025", "GD2-024", "GD3-025", "GD4-028", "GD5-025", "GD6-026", "IP1-023", "IP2-025")
V0_69_BASIC_ENERGIES = ("IP1-004", "IP1-006", "IP1-024", "IP2-004", "IP2-005", "IP2-012", "NIP1-003", "NIP1-005", "NIP1-006", "NIP2-005", "NIP2-006", "NIP2-007")
V0_69_CARDS = V0_69_POKEMON + V0_69_TRAINERS + V0_69_SPECIAL_ENERGIES  # 登録のある 84 枚
# 新しい id の特殊能力の登録（元のカードの登録を写した 10。登録の一覧を数えるテストは、v0.68 までの一覧とこれを分けて比べる）
V0_69_POWER_CARDS = ("GD1-013", "GD2-004", "GD3-006", "GD4-008", "GD4-013", "GD5-002", "GD5-004", "GD6-004", "PR1-039", "PR1-061")

# v0.70（docs/non-pack-effect-reuse-v0.70.md）: 拡張パック以外の商品のポケモン 82 枚（写しの組 pool_v0_70。既存の効果の型の登録と、ダメージのない型 2 つ。特殊能力はない）
V0_70_POKEMON = ("GD1-004", "GD1-008", "GD2-005", "GD2-009", "GD2-013", "GD2-014", "GD3-002", "GD3-008", "GD3-013", "GD4-005", "GD5-008", "GD5-013", "GD6-006",
                 "ES1-004", "ES1-008", "ES1-012", "ES1-016", "ES1-017", "ES1-018", "ES1-024", "ES1-030", "ES1-032", "ES2-008", "ES2-009", "ES2-010", "ES2-019",
                 "ES2-022", "ES2-026", "ES2-031", "ES3-015", "ES3-033", "QSG-006", "QSG-014", "QSG-015", "QSG-016", "QSG-019", "QSG-031", "QSG-036", "QSG-042",
                 "QSG-044", "SI-001", "SI-005", "SI-006", "SI-007", "SI-009", "SI-015", "IP1-001", "IP1-016", "IP1-026", "IP1-030", "IP1-037", "IP1-039", "IP2-003",
                 "IP2-013", "IP2-016", "IP2-039", "PF1-007", "PF2-004", "NIP1-001", "NIP1-002", "NIP1-008", "NIP1-016", "NIP1-022", "NIP1-024", "NIP2-002", "NIP2-003",
                 "NIP2-004", "NIP2-016", "NIP2-018", "NIP2-024", "NIP2-026", "NIP2X-004", "PR1-011", "PR1-014", "PR1-045", "PR1-066", "PR1-069", "PRN-006", "PRN-009",
                 "PRN-013", "PRN-038", "PRN-047")
V0_70_CARDS = V0_70_POKEMON

# v0.71（docs/reprint-text-variants-v0.71.md）: 拡張パック以外の商品の再録のカード 78 枚（写しの組 pool_v0_71。effects.REPRINT_CARDS。元のカードと効果の文面だけが違う）
V0_71_POKEMON = ("GD1-006", "GD4-004", "GD5-011", "GD6-010", "IP2-009", "IPH-001", "IPH-002", "PR1-028", "PR1-029", "PR1-030", "PR1-033")
V0_71_TRAINERS = ("GD1-014", "GD1-016", "GD1-017", "GD1-018", "GD1-020", "GD1-021", "GD1-022", "GD1-023", "GD1-024", "GD2-019", "GD2-020", "GD2-021", "GD2-022",
                  "GD2-023", "GD3-014", "GD3-017", "GD3-018", "GD3-019", "GD3-020", "GD3-023", "GD3-024", "GD4-014", "GD4-015", "GD4-019", "GD4-020", "GD4-021",
                  "GD4-022", "GD4-023", "GD4-024", "GD4-025", "GD4-027", "GD5-018", "GD5-020", "GD5-022", "GD5-023", "GD5-024", "GD6-014", "GD6-015", "GD6-016",
                  "GD6-020", "GD6-021", "GD6-022", "GD6-024", "GD6-025", "QSG-047", "QSG-048", "QSG-049", "QSG-050", "QSG-051", "QSG-052", "QSG-053", "IP1-007",
                  "IP1-019", "IP1-028", "IP2-007", "IP2-019", "IP2-024", "NIP1-007", "NIP1-015", "NIP1-020", "NIP1X-006", "NIP1X-007", "NIP2-008", "NIP2-020",
                  "NIP2-025", "NIP2X-006", "NIP2X-007")
# 特殊能力の登録のある再録のカード（元のカードの登録から作った 6。登録の一覧を数えるテストは、v0.70 までの一覧とこれを分けて比べる）
V0_71_POWER_CARDS = ("GD4-004", "IPH-001", "IPH-002", "PR1-028", "PR1-029", "PR1-030")
V0_71_CARDS = ("GD1-006", "GD1-014", "GD1-016", "GD1-017", "GD1-018", "GD1-020", "GD1-021", "GD1-022", "GD1-023", "GD1-024", "GD2-019", "GD2-020", "GD2-021", "GD2-022",
               "GD2-023", "GD3-014", "GD3-017", "GD3-018", "GD3-019", "GD3-020", "GD3-023", "GD3-024", "GD4-004", "GD4-014", "GD4-015", "GD4-019", "GD4-020", "GD4-021",
               "GD4-022", "GD4-023", "GD4-024", "GD4-025", "GD4-027", "GD5-011", "GD5-018", "GD5-020", "GD5-022", "GD5-023", "GD5-024", "GD6-010", "GD6-014", "GD6-015",
               "GD6-016", "GD6-020", "GD6-021", "GD6-022", "GD6-024", "GD6-025", "QSG-047", "QSG-048", "QSG-049", "QSG-050", "QSG-051", "QSG-052", "QSG-053", "IP1-007",
               "IP1-019", "IP1-028", "IP2-007", "IP2-009", "IP2-019", "IP2-024", "IPH-001", "IPH-002", "PR1-028", "PR1-029", "PR1-030", "PR1-033", "NIP1-007",
               "NIP1-015", "NIP1-020", "NIP1X-006", "NIP1X-007", "NIP2-008", "NIP2-020", "NIP2-025", "NIP2X-006", "NIP2X-007")  # 依頼の並び（V0_71_POKEMON と V0_71_TRAINERS を合わせたもの）
# v0.72（docs/status-coins-effect-reuse-v0.72.md）: 拡張パック以外の商品のポケモン 43 枚（写しの組 pool_v0_72。kyuura データの採用）
V0_72_POKEMON = ("GD1-003", "GD1-012", "GD2-002", "GD3-010", "GD4-003", "GD4-007", "GD4-009", "GD4-012", "GD5-005", "GD6-012",
                 "ES1-006", "ES1-009", "ES1-011", "ES1-019", "ES1-020", "ES1-025", "ES1-029", "ES1-031", "ES2-023", "ES2-024", "ES2-027", "ES2-030",
                 "ES3-003", "ES3-005", "ES3-008", "ES3-013", "QSG-004", "QSG-020", "QSG-026", "QSG-037", "QSG-038", "QSG-039", "QSG-043", "QSG-054",
                 "IP1-022", "PR1-036", "PR1-037", "PR1-040", "PR1-059", "PF3-009", "NIP2-010", "NIP2X-003", "PRN-042")
V0_72_CARDS = V0_72_POKEMON

# v0.73（docs/search-recovery-trainers-v0.73.md）: 拡張パック以外の商品の、検索・回収・ドローのトレーナー 18 枚（kyuura データの採用。並びは依頼の並び）
MAX_REVIVE, MAX_REVIVE_ES2, FERVOR = "GD5-019", "ES2-034", "GD5-021"
MASTER_BALL, MASTER_BALL_ES2, MASTER_BALL_QSG, MASTER_BALL_NIP1, MASTER_BALL_NIP2 = "GD6-023", "ES2-036", "QSG-058", "NIP1-021", "NIP2-022"
FOSSIL_EXCAVATION, MOON_STONE, POKEMON_RETRIEVER = "ES1-035", "ES1-036", "ES3-035"
SUPER_SCOOP_UP, SUPER_SCOOP_UP_IP2, BILLS_TELEPORTER, BILLS_TELEPORTER_IP2 = "IP1-009", "IP2-029", "IP1-020", "IP2-021"
SUPER_ENERGY_RETRIEVAL, COMPUTER_ERROR, COMPUTER_ERROR_041 = "PR1-009", "PR1-026", "PR1-041"
V0_73_CARDS = (MAX_REVIVE, MAX_REVIVE_ES2, FERVOR, MASTER_BALL, MASTER_BALL_ES2, MASTER_BALL_QSG, MASTER_BALL_NIP1, MASTER_BALL_NIP2,
               FOSSIL_EXCAVATION, MOON_STONE, POKEMON_RETRIEVER, SUPER_SCOOP_UP, SUPER_SCOOP_UP_IP2, BILLS_TELEPORTER, BILLS_TELEPORTER_IP2,
               SUPER_ENERGY_RETRIEVAL, COMPUTER_ERROR, COMPUTER_ERROR_041)

# v0.74（docs/remaining-stadiums-v0.74.md）: 拡張パック以外の商品のスタジアム 13 枚（kyuura データの採用。並びは依頼の並び）
POKEMON_TOWER, KOGAS_NINJA_GYM, ENERGY_STADIUM, LUCKY_STADIUM_NIP2X = "ES3-036", "PR1-067", "NIP1X-009", "NIP2X-009"
LUCKY_STADIUM_PRN = ("PRN-015", "PRN-016", "PRN-017", "PRN-018", "PRN-019", "PRN-020", "PRN-021", "PRN-022")
LUCKY_STADIUM, LUCKY_STADIUM_027 = "PRN-015", "PRN-027"
V0_74_CARDS = (POKEMON_TOWER, KOGAS_NINJA_GYM, ENERGY_STADIUM, LUCKY_STADIUM_NIP2X, *LUCKY_STADIUM_PRN, LUCKY_STADIUM_027)


# v0.69（docs/equivalent-non-pack-cards-v0.69.md 7 章）: 研究の基準を kyuura 7d3f4ca に上げたので、採用の記録の kyuura_records（研究の基準のコミットでカードを指す kyuura の記録の id）に
# 加わった記録（kyuura が論点に結んだ停止コードのカード）。記録を確かめるテストは、v0.68 までの記録の値にこれを加えた値と比べる（tests/test_equivalent_non_pack_cards_v0_69.py が、
# 同梱の記録と同じことを確かめる）
V0_69_KYUURA_RECORDS_ADDED = {
    "PMCG1-013": ('UQ-POISON-OVERWRITE-ORDER',),
    "PMCG1-021": ('UQ-ENERGY-BURN-TRANSFER',),
    "PMCG1-040": ('UQ-BUZZAP-TARGET-AND-COLOR', 'UQ-SHAPESHIFT-SCOPE', 'UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY'),
    "PMCG1-044": ('UQ-DESTINY-BOND-KO',),
    "PMCG1-048": ('UQ-OPPONENT-POKEMON-COUNTERS',),
    "PMCG1-051": ('UQ-ATTACK-PRE-DAMAGE-COIN-ORDER',),
    "PMCG1-056": ('UQ-BENCH-DAMAGE-WEAKNESS-RESISTANCE',),
    "PMCG1-063": ('UQ-COPIED-ATTACK',),
    "PMCG1-064": ('UQ-CHANGE-ABSENT-WEAKNESS-RESISTANCE',),
    "PMCG1-066": ('UQ-COPIED-ATTACK',),
    "PMCG1-067": ('UQ-COIN-IN-NULLIFIED-ELEMENT',),
    "PMCG1-070": ('UQ-CARD-USE-WITHOUT-TARGET',),
    "PMCG1-075": ('UQ-TARGET-WITHOUT-EFFECT',),
    "PMCG1-078": ('UQ-CARD-USE-WITHOUT-TARGET',),
    "PMCG1-080": ('UQ-CARD-USE-WITHOUT-TARGET',),
    "PMCG1-084": ('UQ-CARD-USE-WITHOUT-TARGET',),
    "PMCG1-085": ('UQ-STATED-COUNT-SHORT',),
    "PMCG1-086": ('UQ-CARD-USE-WITHOUT-TARGET', 'UQ-DEVOLUTION-SAME-TURN', 'UQ-EVOLUTION-HP-BELOW-DAMAGE', 'UQ-SHAPESHIFT-SCOPE'),
    "PMCG1-091": ('UQ-PLAY-AS-POKEMON',),
    "PMCG1-092": ('UQ-ATTACHED-CARDS-WHEN-RETURNED', 'UQ-CARD-USE-WITHOUT-TARGET'),
    "PMCG1-096": ('UQ-RETREAT-COST-PAYMENT',),
    "PMCG2-015": ('UQ-SHIFT-COLOR-DURATION',),
    "PMCG2-029": ('UQ-REDUCED-DAMAGE-BENCH-TARGET',),
    "PMCG2-033": ('UQ-DAMAGE-TRIGGER-TIMING',),
    "PMCG2-034": ('UQ-COPIED-ATTACK',),
    "PMCG2-040": ('UQ-RETREAT-COST-PAYMENT',),
    "PMCG2-044": ('UQ-COPIED-ATTACK',),
    "PMCG3-009": ('UQ-DISCARD-ENERGY-TIMING-CONFUSION', 'UQ-STATED-COUNT-SHORT', 'UQ-UP-TO-ZERO-CHOICE'),
    "PMCG3-024": ('UQ-UP-TO-ZERO-CHOICE',),
    "PMCG3-033": ('UQ-DEVOLUTION-SAME-TURN',),
    "PMCG3-035": ('UQ-NON-ATTACK-DAMAGE-MODIFIERS',),
    "PMCG3-042": ('UQ-REACTIVE-SWITCH-DURING-ATTACK', 'UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY', 'UQ-TRANSFORM-SCOPE'),
    "PMCG3-046": ('UQ-PLAY-AS-POKEMON',),
    "PMCG3-047": ('UQ-CARD-USE-WITHOUT-TARGET',),
    "PMCG3-048": ('UQ-CARD-USE-WITHOUT-TARGET',),
    "PMCG4-019": ('UQ-EXTRA-ENERGY-COLORLESS',),
    "PMCG4-034": ('UQ-CARD-USE-WITHOUT-TARGET',),
    "PMCG4-043": ('UQ-SINKHOLE-TIMING',),
    "PMCG4-052": ('UQ-UP-TO-ZERO-CHOICE',),
    "PMCG4-053": ('UQ-UP-TO-ZERO-CHOICE',),
    "PMCG4-055": ('UQ-NON-ATTACK-DAMAGE-MODIFIERS',),
    "PMCG4-056": ('UQ-GOOP-GAS-NEW-POKEMON',),
    "PMCG4-057": ('UQ-UP-TO-ZERO-CHOICE',),
    "PMCG4-058": ('UQ-UP-TO-ZERO-CHOICE',),
    "PMCG4-065": ('UQ-NON-ATTACK-DAMAGE-MODIFIERS', 'UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY'),
    "PMCG5-010": ('UQ-UP-TO-ZERO-CHOICE',),
    "PMCG5-015": ('UQ-CARD-USE-WITHOUT-TARGET',),
    "PMCG5-019": ('UQ-SHAPESHIFT-SCOPE',),
    "PMCG5-021": ('UQ-COPIED-ATTACK',),
    "PMCG5-024": ('UQ-ATTACK-PRE-DAMAGE-COIN-ORDER',),
    "PMCG5-030": ('UQ-ATTACH-BLOCK-SCOPE',),
    "PMCG5-033": ('UQ-REACTIVE-SWITCH-DURING-ATTACK',),
    "PMCG5-041": ('UQ-UP-TO-ZERO-CHOICE',),
    "PMCG5-050": ('UQ-SPEED-STAR-SCOPE',),
    "PMCG5-051": ('UQ-SCRAM-TIMING',),
    "PMCG5-055": ('UQ-REACTIVE-SWITCH-DURING-ATTACK',),
    "PMCG5-060": ('UQ-ENTRY-POWER-DURING-ATTACK',),
    "PMCG5-071": ('UQ-RECALL-SCOPE',),
    "PMCG5-074": ('UQ-CHARITY-BELOW-ZERO',),
    "PMCG5-075": ('UQ-STATED-COUNT-SHORT',),
    "PMCG5-076": ('UQ-ATTACK-PRE-DAMAGE-COIN-ORDER',),
    "PMCG5-078": ('UQ-TARGET-WITHOUT-EFFECT',),
    "PMCG5-085": ('UQ-MISTY-SELF-DAMAGE',),
    "PMCG5-086": ('UQ-CARD-USE-WITHOUT-TARGET',),
    "PMCG5-087": ('UQ-CHAOS-GYM-BORROWED-TURN',),
    "PMCG5-092": ('UQ-CARD-USE-WITHOUT-TARGET',),
    "PMCG5-093": ('UQ-FACE-DOWN-CARD',),
    "PMCG5-096": ('UQ-UP-TO-ZERO-CHOICE',),
    "PMCG6-010": ('UQ-CALMING-AROMA-RETALIATION',),
    "PMCG6-015": ('UQ-RETURN-TO-DECK-KO-ORDER',),
    "PMCG6-021": ('UQ-ATTACK-LOCK-SOURCE-RETURNED',),
    "PMCG6-026": ('UQ-TARGET-WITHOUT-EFFECT',),
    "PMCG6-031": ('UQ-STATED-COUNT-SHORT',),
    "PMCG6-046": ('UQ-STATED-COUNT-SHORT',),
    "PMCG6-049": ('UQ-EVOLUTION-HP-BELOW-DAMAGE',),
    "PMCG6-055": ('UQ-COUNTER-TRANSFER-PROTECTED',),
    "PMCG6-060": ('UQ-COPIED-ATTACK',),
    "PMCG6-075": ('UQ-STATED-COUNT-SHORT',),
    "PMCG6-076": ('UQ-UP-TO-ZERO-CHOICE',),
    "PMCG6-082": ('UQ-CARD-USE-WITHOUT-TARGET',),
    "PMCG6-083": ('UQ-ATTACHED-CARDS-WHEN-RETURNED', 'UQ-REACTIVE-SWITCH-DURING-ATTACK', 'UQ-TRAINER-BAN-SCOPE'),
    "PMCG6-086": ('UQ-CARD-USE-WITHOUT-TARGET', 'UQ-FUCHSIA-GYM-ONCE-PER-TURN'),
    "PMCG6-087": ('UQ-ESP-REDO',),
    "PMCG6-089": ('UQ-CARD-USE-WITHOUT-TARGET',),
    "PMCG6-091": ('UQ-TRAINER-BAN-SCOPE',),
    "PMCG6-092": ('UQ-FACE-DOWN-CARD', 'UQ-NON-ATTACK-DAMAGE-MODIFIERS'),
    "PMCG6-093": ('UQ-BLAINE-SECOND-ATTACH',),
    "PMCG6-094": ('UQ-POISON-OVERWRITE-ORDER',),
    "PMCG6-095": ('UQ-CARD-USE-WITHOUT-TARGET', 'UQ-EVOLUTION-PERMISSION-FROM-DECK'),
    "PMCG6-096": ('UQ-CARD-USE-WITHOUT-TARGET', 'UQ-TARGET-WITHOUT-EFFECT'),
    "PMCG6-097": ('UQ-STATED-COUNT-SHORT',),
    "PMCG6-098": ('UQ-CARD-USE-WITHOUT-TARGET', 'UQ-TARGET-WITHOUT-EFFECT'),
}


# v0.97（docs/unown-research-idfnj-v0.97.md 3 章）: 研究の基準を kyuura 73a1690 に上げて、採用の記録の kyuura_records に加わった記録（kyuura のアンノーンの調査の裁定・論点の
# 事例が指すカード）。記録を確かめるテストは、v0.96 までの値にこれを加えた値と比べる（tests/test_unown_research_idfnj_v0_97.py が、同梱の記録と同じことを確かめる）
V0_97_KYUURA_RECORDS_ADDED = {
    "PMCG1-066": ("UQ-SPEED-STAR-SCOPE",),
    "PF1-004": ("UQ-SPEED-STAR-SCOPE",),
    "PMCG5-066": ("CR-UNOWN-DF-SOURCE-TYPE",),
    "neo1-094": ("CR-UNOWN-DF-SOURCE-TYPE",),
    "neo4-046": ("UQ-SELF-EXCLUDING-POWER-COPIES",),
    "neo2-054": ("CR-UNOWN-DECK-LIMIT-ALL-LETTERS",),
    "neo2-057": ("CR-UNOWN-DECK-LIMIT-ALL-LETTERS",),
}


def kyuura_records_since_v0_69(card_id: str, before: list | tuple = ()) -> list:
    """v0.68 までの kyuura_records（``before``）に、v0.69 で加わった記録を加えた値（並びは id の順）。v0.97 で加わった記録（``V0_97_KYUURA_RECORDS_ADDED``）も加える。"""
    return sorted([*before, *V0_69_KYUURA_RECORDS_ADDED.get(card_id, ()), *V0_97_KYUURA_RECORDS_ADDED.get(card_id, ())])


# v0.69: kyuura の未解決の一覧で論点に結ばれた停止コード（v0.68 までは not_in_kyuura。進化のあとの HP だけは out_of_scope）→ kyuura の論点
V0_69_STOP_CODE_ISSUES = {
    "UNRESOLVED_ATTACH_BLOCK_SCOPE": "UQ-ATTACH-BLOCK-SCOPE",
    "UNRESOLVED_ATTACH_FROM_DISCARD_ZERO": "UQ-UP-TO-ZERO-CHOICE",
    "UNRESOLVED_ATTACK_CHECK_CONFUSION": "UQ-ATTACK-PRE-DAMAGE-COIN-ORDER",
    "UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED": "UQ-ATTACK-LOCK-SOURCE-RETURNED",
    "UNRESOLVED_BENCH_COIN_TRANSPARENCY_ORDER": "UQ-TRANSPARENCY-COIN-ORDER",
    "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE": "UQ-BENCH-DAMAGE-WEAKNESS-RESISTANCE",
    "UNRESOLVED_BENCH_GUARD_RECOMPUTE": "UQ-REACTIVE-SWITCH-DURING-ATTACK",
    "UNRESOLVED_BENCH_GUARD_ZERO_DAMAGE_REACTION": "UQ-REACTIVE-SWITCH-DURING-ATTACK",
    "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE": "UQ-UP-TO-ZERO-CHOICE",
    "UNRESOLVED_BLAINES_QUIZ_WITHOUT_POKEMON": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_BLAINE_SECOND_ATTACH": "UQ-BLAINE-SECOND-ATTACH",
    "UNRESOLVED_BREEDER_ON_PLAY_AS_POKEMON": "UQ-PLAY-AS-POKEMON",
    "UNRESOLVED_BUZZAP_COLOR": "UQ-BUZZAP-TARGET-AND-COLOR",
    "UNRESOLVED_BUZZAP_DISGUISED": "UQ-SHAPESHIFT-SCOPE",
    "UNRESOLVED_BUZZAP_ENERGY_CARD_TYPE": "UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY",
    "UNRESOLVED_BUZZAP_OPPONENT_TARGET": "UQ-BUZZAP-TARGET-AND-COLOR",
    "UNRESOLVED_CALMING_AROMA_RETALIATION": "UQ-CALMING-AROMA-RETALIATION",
    "UNRESOLVED_CELADON_GYM_WITHOUT_CONDITION": "UQ-TARGET-WITHOUT-EFFECT",
    "UNRESOLVED_CHANGE_ABSENT_WEAKNESS_RESISTANCE": "UQ-CHANGE-ABSENT-WEAKNESS-RESISTANCE",
    "UNRESOLVED_CHAOS_GYM_BORROWED_TURN": "UQ-CHAOS-GYM-BORROWED-TURN",
    "UNRESOLVED_CHARITY_BELOW_ZERO": "UQ-CHARITY-BELOW-ZERO",
    "UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK": "UQ-COMPUTER-SEARCH-EMPTY-DECK",
    "UNRESOLVED_COPIED_ATTACK": "UQ-COPIED-ATTACK",
    "UNRESOLVED_COUNTER_TRANSFER_PROTECTED": "UQ-COUNTER-TRANSFER-PROTECTED",
    "UNRESOLVED_DAMAGE_TRIGGER_TIMING": "UQ-DAMAGE-TRIGGER-TIMING",
    "UNRESOLVED_DESTINY_BOND_KNOCKOUT": "UQ-DESTINY-BOND-KO",
    "UNRESOLVED_DEVOLUTION_INTERMEDIATE_KNOCKOUT": "UQ-EVOLUTION-HP-BELOW-DAMAGE",
    "UNRESOLVED_DEVOLUTION_SPRAY_WITHOUT_TARGET": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_DEVOLUTION_TARGET_DISGUISED": "UQ-SHAPESHIFT-SCOPE",
    "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO": "UQ-UP-TO-ZERO-CHOICE",
    "UNRESOLVED_DISCARD_DECK_SHORT": "UQ-STATED-COUNT-SHORT",
    "UNRESOLVED_DISCARD_ENERGY_TIMING": "UQ-DISCARD-ENERGY-TIMING-CONFUSION",
    "UNRESOLVED_ENERGY_BURN_TRANSFER": "UQ-ENERGY-BURN-TRANSFER",
    "UNRESOLVED_ENERGY_REMOVAL_WITHOUT_TARGET": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET": "UQ-ENERGY-RETRIEVAL-WITHOUT-TARGET",
    "UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE": "UQ-ENERGY-RETRIEVAL-ZERO-CHOICE",
    "UNRESOLVED_ENTRY_POWER_DURING_ATTACK": "UQ-ENTRY-POWER-DURING-ATTACK",
    "UNRESOLVED_ESP_HOLDER_NOT_SABRINAS": "UQ-ESP-REDO",
    "UNRESOLVED_ESP_MULTIPLE": "UQ-ESP-REDO",
    "UNRESOLVED_ESP_OPPONENT_COIN_TOSS": "UQ-ESP-REDO",
    "UNRESOLVED_EVOLUTION_HP": "UQ-EVOLUTION-HP-BELOW-DAMAGE",
    "UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK": "UQ-EVOLUTION-PERMISSION-FROM-DECK",
    "UNRESOLVED_EVOLVE_AFTER_DEVOLUTION": "UQ-DEVOLUTION-SAME-TURN",
    "UNRESOLVED_EXTRA_ENERGY_COLORLESS": "UQ-EXTRA-ENERGY-COLORLESS",
    "UNRESOLVED_FLEE_DURING_OWN_ATTACK": "UQ-REACTIVE-SWITCH-DURING-ATTACK",
    "UNRESOLVED_FUCHSIA_GYM_AFTER_REPLACEMENT": "UQ-FUCHSIA-GYM-ONCE-PER-TURN",
    "UNRESOLVED_FUCHSIA_GYM_WITHOUT_TARGET": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_FULL_HEAL_SCOPE": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_GOOP_GAS_NEW_POKEMON": "UQ-GOOP-GAS-NEW-POKEMON",
    "UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH": "UQ-GUST-WITHOUT-OPPONENT-BENCH",
    "UNRESOLVED_KOGA_POISON_ORDER": "UQ-POISON-OVERWRITE-ORDER",
    "UNRESOLVED_LAST_RESORT_UNDAMAGED_TARGET": "UQ-TARGET-WITHOUT-EFFECT",
    "UNRESOLVED_LAST_RESORT_WITHOUT_TARGET": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_LT_SURGE_WITHOUT_BASIC": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_MAX_HP_DROP": "UQ-EVOLUTION-HP-BELOW-DAMAGE",
    "UNRESOLVED_MINEFIELD_DAMAGE_RECEIVED_POWER": "UQ-NON-ATTACK-DAMAGE-MODIFIERS",
    "UNRESOLVED_MIRROR_MOVE_ATTACK_CONDITIONS": "UQ-COPIED-ATTACK",
    "UNRESOLVED_MIRROR_MOVE_LASTING_EFFECT": "UQ-COPIED-ATTACK",
    "UNRESOLVED_MIRROR_MOVE_NON_ATTACK": "UQ-COPIED-ATTACK",
    "UNRESOLVED_MIRROR_MOVE_RECEIVED_ATTACK": "UQ-COPIED-ATTACK",
    "UNRESOLVED_MISTYS_WISH_WITHOUT_HAND": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_MISTYS_WRATH_SHORT_DECK": "UQ-STATED-COUNT-SHORT",
    "UNRESOLVED_MISTY_SELF_DAMAGE": "UQ-MISTY-SELF-DAMAGE",
    "UNRESOLVED_MR_FUJI_WITHOUT_BENCH": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_MULTIPLE_ATTACK_CHECKS": "UQ-ATTACK-PRE-DAMAGE-COIN-ORDER",
    "UNRESOLVED_NIGHTLY_GARBAGE_RUN_ZERO_CHOICE": "UQ-UP-TO-ZERO-CHOICE",
    "UNRESOLVED_NINJA_TRICK_ATTACK_COIN_ORDER": "UQ-REACTIVE-SWITCH-DURING-ATTACK",
    "UNRESOLVED_NINJA_TRICK_LEAVES_WITH_POKEMON": "UQ-ATTACHED-CARDS-WHEN-RETURNED",
    "UNRESOLVED_NINJA_TRICK_UNDER_TRAINER_BAN": "UQ-TRAINER-BAN-SCOPE",
    "UNRESOLVED_OPPONENT_POKEMON_COUNTERS": "UQ-OPPONENT-POKEMON-COUNTERS",
    "UNRESOLVED_PLAY_AS_POKEMON_RETREAT": "UQ-PLAY-AS-POKEMON",
    "UNRESOLVED_PLAY_AS_POKEMON_SETUP": "UQ-PLAY-AS-POKEMON",
    "UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER": "UQ-NON-ATTACK-DAMAGE-MODIFIERS",
    "UNRESOLVED_POKEMON_FLUTE_WITHOUT_TARGET": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_POWER_DISCARD_WITHOUT_HAND": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_POWER_HEAL_WITHOUT_DAMAGE": "UQ-TARGET-WITHOUT-EFFECT",
    "UNRESOLVED_POWER_REUSE_AFTER_DEVOLUTION": "UQ-DEVOLUTION-SAME-TURN",
    "UNRESOLVED_POWER_SWITCH_WITHOUT_OPPONENT_BENCH": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_POWER_ZERO_CARDS": "UQ-UP-TO-ZERO-CHOICE",
    "UNRESOLVED_PREVENTED_EFFECT_COIN": "UQ-COIN-IN-NULLIFIED-ELEMENT",
    "UNRESOLVED_RAINBOW_AS_BASIC_ENERGY_CARD": "UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY",
    "UNRESOLVED_RAINBOW_ATTACH_AS_TYPE": "UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY",
    "UNRESOLVED_RAINBOW_DAMAGE_RECEIVED_POWER": "UQ-NON-ATTACK-DAMAGE-MODIFIERS",
    "UNRESOLVED_RAINBOW_ENERGY_TYPE": "UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY",
    "UNRESOLVED_REACTION_BY_KNOCKED_OUT_POKEMON": "UQ-REACTIVE-SWITCH-DURING-ATTACK",
    "UNRESOLVED_REACTIVE_SWITCH_TRANSFORMED_ATTACKER": "UQ-REACTIVE-SWITCH-DURING-ATTACK",
    "UNRESOLVED_RECALL_EARLIER_STAGE": "UQ-RECALL-SCOPE",
    "UNRESOLVED_RECALL_FORM": "UQ-RECALL-SCOPE",
    "UNRESOLVED_RECALL_TARGET_CHANGED": "UQ-RECALL-SCOPE",
    "UNRESOLVED_RECALL_WITHOUT_PRE_EVOLUTION_ATTACK": "UQ-RECALL-SCOPE",
    "UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET": "UQ-REDUCED-DAMAGE-BENCH-TARGET",
    "UNRESOLVED_RETREAT_COST_FLOOR": "UQ-RETREAT-COST-PAYMENT",
    "UNRESOLVED_RETREAT_OVERPAY": "UQ-RETREAT-COST-PAYMENT",
    "UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT": "UQ-RETURN-TO-DECK-KO-ORDER",
    "UNRESOLVED_REVIVE_WITHOUT_TARGET": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_ROCKETS_TRAP_ZERO_CHOICE": "UQ-UP-TO-ZERO-CHOICE",
    "UNRESOLVED_ROCKET_GRUNT_WITHOUT_BENCH": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_SABRINA_SOURCE_WITHOUT_ENERGY": "UQ-TARGET-WITHOUT-EFFECT",
    "UNRESOLVED_SABRINA_WITHOUT_TWO_POKEMON": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_SCOOP_UP_ATTACHED_TRAINER": "UQ-ATTACHED-CARDS-WHEN-RETURNED",
    "UNRESOLVED_SCOOP_UP_LAST_POKEMON": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_SCRAM_POWER_RESTORED": "UQ-SCRAM-TIMING",
    "UNRESOLVED_SCRAM_TIMING": "UQ-SCRAM-TIMING",
    "UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY": "UQ-FACE-DOWN-CARD",
    "UNRESOLVED_SECRET_PLAN_MINEFIELD": "UQ-FACE-DOWN-CARD",
    "UNRESOLVED_SHAPESHIFT_AGAIN": "UQ-SHAPESHIFT-SCOPE",
    "UNRESOLVED_SHAPESHIFT_ENTRY_POWER": "UQ-SHAPESHIFT-SCOPE",
    "UNRESOLVED_SHAPESHIFT_SUPPRESSED": "UQ-SHAPESHIFT-SCOPE",
    "UNRESOLVED_SHIFT_COLOR_DURATION": "UQ-SHIFT-COLOR-DURATION",
    "UNRESOLVED_SINKHOLE_TIMING": "UQ-SINKHOLE-TIMING",
    "UNRESOLVED_SPECIAL_POISON_OVERWRITE": "UQ-POISON-OVERWRITE-ORDER",
    "UNRESOLVED_STADIUM_ACTIVATION_UNDER_TRAINER_BAN": "UQ-TRAINER-BAN-SCOPE",
    "UNRESOLVED_STATED_CARDS_SHORT": "UQ-STATED-COUNT-SHORT",
    "UNRESOLVED_SUPER_POTION_UNDAMAGED_TARGET": "UQ-TARGET-WITHOUT-EFFECT",
    "UNRESOLVED_TRAINER_DAMAGE_REDUCTION": "UQ-NON-ATTACK-DAMAGE-MODIFIERS",
    "UNRESOLVED_TRAINER_WITHOUT_TARGET": "UQ-CARD-USE-WITHOUT-TARGET",
    "UNRESOLVED_TRANSFORM_COPIED_POWER": "UQ-TRANSFORM-SCOPE",
    "UNRESOLVED_TRANSFORM_ENERGY_COUNT": "UQ-TRANSFORM-SCOPE",
    "UNRESOLVED_TRANSFORM_MODIFIED_DEFENDER": "UQ-TRANSFORM-SCOPE",
    "UNRESOLVED_TRANSFORM_SPECIAL_ENERGY": "UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY",
    "UNRESOLVED_VERMILION_GYM_ATTACK_ORDER": "UQ-ATTACK-PRE-DAMAGE-COIN-ORDER",
    "UNRESOLVED_VIRIDIAN_GYM_ONE_COUNTER": "UQ-STATED-COUNT-SHORT",
    "UNRESOLVED_VIRTUAL_ONCE_ATTACK": "UQ-COPIED-ATTACK",
}


def assert_stop_code_counts_since(test, links, stop_codes: int, unresolved: int) -> None:
    """v0.72: 研究の対応表の停止コード・未解決の裁定の数が、ある版の数（``stop_codes``・``unresolved``）から減っていないこと。

    v0.71 までの版のテストは、そのときの総数を等号で固定していて、あとの版で停止コードを加えるたびに関係のないテストが壊れていた。総数がエンジンの側の集合と同じことは
    tests/test_research_links_v0_18e.py が等号で確かめるので、版ごとのテストはその版の数を下限として確かめる（その版で加えたコードがあることは各テストが確かめる）。"""
    counts = links["counts"]
    test.assertEqual(counts["engine_stop_codes"], len(links["stop_codes"]))
    test.assertGreaterEqual(counts["engine_stop_codes"], stop_codes)
    test.assertGreaterEqual(counts["engine_unresolved_rulings"], unresolved)


# v0.75（docs/search-energy-pokemon-v0.75.md）: 拡張パック以外の商品のポケモン 15 枚（kyuura データの採用）
BROCKS_ZUBAT_GD1 = "GD1-001"  # タケシのズバット（ポケモンジム第1弾。しらせる・つばさでうつ。PMCG5-001 とは別のカード）
MISTYS_PSYDUCK_GD2 = "GD2-001"  # カスミのコダック（ポケモンジム第1弾。ひっかく・たすけをよぶ。PMCG5-021 とは別のカード）
MISTYS_TENTACOOL_GD2 = "GD2-003"  # カスミのメノクラゲ（ふしぎなひかり・くらげのむれ。PMCG5-030 とは別のカード）
BLAINES_VULPIX_GD5 = "GD5-003"  # カツラのロコン（かみつく・おにびあつめ）
BLAINES_GROWLITHE_GD5 = "GD5-006"  # カツラのガーディ（もえあがる・のしかかり。GD5-005 とは別のカード）
SABRINAS_DROWZEE_GD6 = "GD6-009"  # ナツメのスリープ（エナジーサポート・マインドショック。PMCG6-045 とは別のカード）
PARAS_ES1 = "ES1-010"  # パラス（ひっかく・ほうしをとばす）
GROWLITHE_ES3, GROWLITHE_QSG = "ES3-010", "QSG-009"  # ガーディ（おつかい・ひのこ。同じデータ）
KINGLER_ES3 = "ES3-014"  # キングラー（クラブから進化。しおまねき・もろばバサミ。PMCG3-019 とは別のカード）
PIKACHU_QSG, PIKACHU_PR1 = "QSG-021", "PR1-020"  # ピカチュウ（じゅうでん・10まんボルト。同じデータ）
MEWTWO_PR1, MEWTWO_PR1_B = "PR1-007", "PR1-008"  # ミュウツー（エネルギーきゅうしゅう・サイコバーン。同じデータ）
SUNKERN_PRN = "PRN-032"  # ヒマナッツ（せいちょう・メガドレイン）
V0_75_POKEMON = (BROCKS_ZUBAT_GD1, MISTYS_PSYDUCK_GD2, MISTYS_TENTACOOL_GD2, BLAINES_VULPIX_GD5, BLAINES_GROWLITHE_GD5, SABRINAS_DROWZEE_GD6, PARAS_ES1,
                 GROWLITHE_ES3, GROWLITHE_QSG, KINGLER_ES3, PIKACHU_QSG, PIKACHU_PR1, MEWTWO_PR1, MEWTWO_PR1_B, SUNKERN_PRN)
V0_75_CARDS = V0_75_POKEMON


# v0.76（docs/persistent-attack-modifiers-v0.76.md）: 拡張パック以外の商品の、持続する効果・ワザの使用の制限を中心とするポケモン 24 枚（kyuura データの採用）
LT_SURGES_RATTATA_GD3 = "GD3-011"  # マチスのコラッタ（きあいだめ・かじる。PMCG5-056 とは別のカード）
NIDORAN_M_ES1, NIDORAN_M_QSG = "ES1-007", "QSG-005"  # ニドラン♂（きあいだめ・つのでとっしん。同じデータ）
SQUIRTLE_ES1, SQUIRTLE_QSG, SQUIRTLE_IP2 = "ES1-015", "QSG-013", "IP2-018"  # ゼニガメ（ウォーターパワー・はたく。同じデータ）
MARILL_PRN = "PRN-028"  # マリル（はずむ・とびのる）
CHARMANDER_ES1, CHARMANDER_QSG = "ES1-013", "QSG-007"  # ヒトカゲ（なきごえ・ほのおのしっぽ。同じデータ）
DODUO_ES1, DODUO_QSG = "ES1-028", "QSG-041"  # ドードー（なきごえ・つつく。同じデータ）
SEEL_ES2, SEEL_QSG = "ES2-006", "QSG-017"  # パウワウ（なきごえ・れいとうビーム。同じデータ）
PIKACHU_IP1 = "IP1-040"  # ピカチュウ（なきごえ・でんきショック）
CHIKORITA_PF1 = "PF1-001"  # チコリータ（なきごえ・はっぱカッター）
SLOWPOKE_PR1 = "PR1-006"  # ヤドン（ずつき・ドわすれ）
VENONAT_ES3 = "ES3-004"  # コンパン（かなしばり・サイケこうせん）
MACHOP_ES2, MACHOP_QSG = "ES2-021", "QSG-035"  # ワンリキー（きあいいっぱつ・どつく。同じデータ）
CYNDAQUIL_PF1 = "PF1-004"  # ヒノアラシ（にらみつける・スピードスター）
WOOPER_PRN = "PRN-003"  # ウパー（しっぽをふる・みずでっぽう）
TOTODILE_PRN, TOTODILE_PRN_B = "PRN-008", "PRN-011"  # ワニノコ（にらみつける・みだれひっかき。同じデータ）
GROWLITHE_IP2 = "IP2-026"  # ガーディ（とびかかる・ひのこ。ES3-010 とは別のデータ）
V0_76_POKEMON = (LT_SURGES_RATTATA_GD3, NIDORAN_M_ES1, NIDORAN_M_QSG, SQUIRTLE_ES1, SQUIRTLE_QSG, SQUIRTLE_IP2, MARILL_PRN, CHARMANDER_ES1, CHARMANDER_QSG,
                 DODUO_ES1, DODUO_QSG, SEEL_ES2, SEEL_QSG, PIKACHU_IP1, CHIKORITA_PF1, SLOWPOKE_PR1, VENONAT_ES3, MACHOP_ES2, MACHOP_QSG, CYNDAQUIL_PF1,
                 WOOPER_PRN, TOTODILE_PRN, TOTODILE_PRN_B, GROWLITHE_IP2)
V0_76_CARDS = V0_76_POKEMON

# v0.77（docs/neo-existing-effects-v0.77.md）: neo 期の拡張パック（neo1〜neo4）の、既存の効果の型で表せるカード 52 枚（kyuura データの採用。id は kyuura の小文字の id のまま）
SUNKERN_NEO1 = "neo1-006"  # ヒマナッツ（せいちょう・メガドレイン。PRN-032 と同じデータ）
SKIPLOOM_NEO1 = "neo1-012"  # ポポッコ（どくのこな・しびれごな。ハネッコから進化）
TOTODILE_NEO1 = "neo1-024"  # ワニノコ（にらみつける・みだれひっかき。PRN-008 と同じデータ）
WOOPER_NEO1 = "neo1-026"  # ウパー（ドわすれ・たたきつける）
MANTINE_NEO1 = "neo1-028"  # マンタイン（ゆらゆらおよぐ）
QUAGSIRE_NEO1 = "neo1-031"  # ヌオー（なみのり・じしん。ウパーから進化）
KINGDRA_NEO1 = "neo1-035"  # キングドラ（こうそくいどう・りゅうのたつまき。シードラから進化する 2 進化）
ELECTABUZZ_NEO1 = "neo1-039"  # エレブー（パンチ・スピードスター）
SUDOWOODO_NEO1 = "neo1-051"  # ウソッキー（じたばた・いわおとし）
SENTRET_NEO1 = "neo1-059"  # オタチ（みだれひっかき）
FURRET_NEO1 = "neo1-064"  # オオタチ（でんこうせっか・たたきつける。オタチから進化）
SUPER_SCOOP_UP_NEO1 = "neo1-083"  # スーパーポケモン回収（IP1-009 と同じデータ）
BILLS_TELEPORTER_NEO1 = "neo1-084"  # マサキの転送装置（IP1-020 と同じデータ）
HOPPIP_NEO2 = "neo2-004"  # ハネッコ（ころがりタックル。PRN-047 と同じデータ）
MAREEP_NEO2 = "neo2-020"  # メリープ（でんげき。NIP2-018 と同じデータ）
POLIWRATH_NEO2 = "neo2-037"  # ニョロボン（とづく・じごくぐるま。ニョロゾから進化する 2 進化）
ZUBAT_NEO3 = "neo3-001"  # ズバット（かみつく・どくをとばす）
PARAS_NEO3 = "neo3-002"  # パラス（ねむりのほうし・ひっかく。NIP1-022 と同じデータ）
SKIPLOOM_NEO3 = "neo3-003"  # ポポッコ（はねる・ふしぎなこな。ハネッコから進化）
SCYTHER_NEO4 = "neo4-007"  # ストライク（こうそくいどう・するどいカマ）
HERACROSS_NEO4 = "neo4-009"  # ヘラクロス（たいあたり・とつげきホーン）
TOTODILE_NEO4 = "neo4-028"  # ワニノコ（みずでっぽう）
HITMONLEE_NEO4 = "neo4-075"  # サワムラー（にだんげり・かかとおとし）
V0_77_CARDS = (
    "neo1-006", "neo1-012", "neo1-019", "neo1-024", "neo1-026", "neo1-027", "neo1-028", "neo1-031", "neo1-035", "neo1-039", "neo1-047", "neo1-051",
    "neo1-052", "neo1-059", "neo1-060", "neo1-062", "neo1-064", "neo1-066", "neo1-083", "neo1-084",
    "neo2-001", "neo2-003", "neo2-004", "neo2-013", "neo2-020", "neo2-034", "neo2-037", "neo2-047",
    "neo3-001", "neo3-002", "neo3-003", "neo3-012", "neo3-013", "neo3-037", "neo3-038",
    "neo4-001", "neo4-005", "neo4-007", "neo4-009", "neo4-015", "neo4-017", "neo4-027", "neo4-028", "neo4-029", "neo4-030", "neo4-042", "neo4-048",
    "neo4-049", "neo4-069", "neo4-072", "neo4-075", "neo4-086",
)
V0_77_TRAINERS = (SUPER_SCOOP_UP_NEO1, BILLS_TELEPORTER_NEO1)
V0_77_POKEMON = tuple(card for card in V0_77_CARDS if card not in V0_77_TRAINERS)

# v0.78（docs/darkness-metal-energy-v0.78.md）: 悪・鋼エネルギー 5 枚と、「悪」「鋼」エネルギーを使うポケモン 8 枚（写しの組 pool_v0_78）
DARKNESS_ENERGY_NEO1 = "neo1-094"  # 悪エネルギー（ポケモンチェックで 10 ダメージ）
METAL_ENERGY_NEO1 = "neo1-095"  # 鋼エネルギー（受けるワザのダメージ -10）
METAL_ENERGY_NIP1X = "NIP1X-010"  # 鋼エネルギー（受けるダメージ -10。ワザに限らない）
DARKNESS_ENERGY_NIP2X = "NIP2X-010"  # 悪エネルギー（ポケモンチェックでダメージカウンター 1 個）
DARKNESS_ENERGY_PRN = "PRN-002"  # 悪エネルギー（neo1-094 と同じ処理）
SNEASEL_NEO1 = "neo1-056"  # ニューラ（みだれひっかき・ふくろだたき）
STEELIX_NEO1 = "neo1-057"  # ハガネール（たいあたり・テールクラッシュ。イワークから進化）
SKARMORY_NEO1 = "neo1-058"  # エアームド（かぎづめ・はがねのつばさ）
HOUNDOUR_NEO2 = "neo2-039"  # デルビル（かみつく・ごうだつ）
SCIZOR_NEO2 = "neo2-045"  # ハッサム（みねうち・ダブルクロー。ストライクから進化）
HOUNDOUR_NEO4 = "neo4-081"  # デルビル（おいつめる・とびかかる）
SKARMORY_NIP1X = "NIP1X-005"  # エアームド（つつく・メタルスラッシュ）
HOUNDOUR_NIP2X = "NIP2X-005"  # デルビル（かみつく・ごうだつ。neo2-039 と同じデータ）
V0_78_ENERGIES = (DARKNESS_ENERGY_NEO1, METAL_ENERGY_NEO1, METAL_ENERGY_NIP1X, DARKNESS_ENERGY_NIP2X, DARKNESS_ENERGY_PRN)
V0_78_POKEMON = (SNEASEL_NEO1, STEELIX_NEO1, SKARMORY_NEO1, HOUNDOUR_NEO2, SCIZOR_NEO2, HOUNDOUR_NEO4, SKARMORY_NIP1X, HOUNDOUR_NIP2X)
V0_78_CARDS = V0_78_ENERGIES + V0_78_POKEMON

# v0.79（docs/shared-checks-pokemon-reuse-v0.79.md）: ポケモン 52 枚（写しの組 pool_v0_79。neo 36 枚・拡張パック以外の商品 16 枚）
SANDSHREW_ES2 = "ES2-020"  # サンド（どくばり・スピードスター）
SANDSHREW_QSG = "QSG-033"  # サンド（どくばり・スピードスター）
GASTLY_ES3 = "ES3-022"  # ゴース（こわがらせる・あんこく）
GASTLY_QSG = "QSG-028"  # ゴース（こわがらせる・あんこく）
BROCKS_MANKEY_GD1 = "GD1-005"  # タケシのマンキー（からかう・けとばす）
LT_SURGES_RATICATE_GD3 = "GD3-012"  # マチスのラッタ（いかりのまえば）
BLAINES_CHARMANDER_GD5 = "GD5-001"  # カツラのヒトカゲ（ファイヤーテール）
SABRINAS_HAUNTER_GD6 = "GD6-007"  # ナツメのゴースト（あくむ・かげからおそう）
QUILAVA_NIP1 = "NIP1-013"  # マグマラシ（たいあたり・かえんほうしゃ）
SNEASEL_PF3 = "PF3-003"  # ニューラ（だましとる・でんこうせっか）
ELECTABUZZ_PR1 = "PR1-010"  # エレブー（ひかりのかべ・でんこうせっか）
ARTICUNO_PR1 = "PR1-064"  # フリーザー（ダイヤモンドダスト）
STEELIX_PRN = "PRN-014"  # ハガネール（メタルクラッシュ・じひびき）
PRIMEAPE_SI = "SI-012"  # オコリザル（けたぐり・いかりくるう）
SLOWKING_SI = "SI-014"  # ヤドキング（ひらめく・サイコキネシス）
MARILL_SI = "SI-017"  # マリル（みずとばし・ころがりタックル）
ODDISH_NEO1 = "neo1-001"  # ナゾノクサ（かくれる・すいとる）
CHIKORITA_NEO1 = "neo1-002"  # チコリータ（たいあたり・リフレクター）
LEDYBA_NEO1 = "neo1-003"  # レディバ（ちょうおんぱ・れんぞくパンチ）
SHUCKLE_NEO1 = "neo1-007"  # ツボツボ（からにこもる・まきつく）
SUNFLORA_NEO1 = "neo1-013"  # キマワリ（はなびらのまい）
JUMPLUFF_NEO1 = "neo1-016"  # ワタッコ（ねむりごな・やどりぎのたね）
MARILL_NEO1 = "neo1-025"  # マリル（まるくなる・バブルボム）
SEADRA_NEO1 = "neo1-029"  # シードラ（あわ・だくりゅう）
AZUMARILL_NEO1 = "neo1-034"  # マリルリ（たいあたり・バブルシャワー）
PIKACHU_NEO1 = "neo1-036"  # ピカチュウ（でんこうせっか・こうそくいどう）
CHINCHOU_NEO1 = "neo1-037"  # チョンチー（ちょうおんぱ・じたばた）
AMPHAROS_NEO1 = "neo1-043"  # デンリュウ（ギガショック）
SLOWPOKE_NEO1 = "neo1-045"  # ヤドン（ねんりき・みずでっぽう）
NATU_NEO1 = "neo1-046"  # ネイティ（つつく・テレキネシス）
BEEDRILL_NEO2 = "neo2-010"  # スピアー（さんばいどく・ミサイルばり）
HOUNDOUR_NEO2_FIRE = "neo2-012"  # デルビル（スモッグ・ほのおをまとう）
CORSOLA_NEO2 = "neo2-017"  # サニーゴ（じこさいせい・とげキャノン）
NATU_NEO2 = "neo2-022"  # ネイティ（あやしいひかり）
ESPEON_NEO2 = "neo2-029"  # エーフィ（かみつく・サイコキネシス）
OMASTAR_NEO2 = "neo2-035"  # オムスター（しめあげる・とげとげMAX）
HITMONTOP_NEO2 = "neo2-038"  # カポエラー（みきり・トリプルキック）
SLUGMA_NEO3 = "neo3-008"  # マグマッグ（ほのお・マグマでかこむ）
HO_OH_NEO3 = "neo3-011"  # ホウオウ（もえあがる・せいなるほのお・ゴッドバード）
QWILFISH_NEO3 = "neo3-015"  # ハリーセン（どくばり・はりせんぼん）
REMORAID_NEO3 = "neo3-016"  # テッポウオ（ねらいうち）
SEAKING_NEO3 = "neo3-017"  # アズマオウ（つきあげる・つのでいちげき）
JYNX_NEO3 = "neo3-018"  # ルージュラ（こごえるキッス・あやしいおどり）
FLAAFFY_NEO3 = "neo3-027"  # モココ（ビリリパンチ・エレキテール）
SNUBBULL_NEO3 = "neo3-048"  # ブルー（かみつく・いかりのずつき）
VULPIX_NEO4 = "neo4-014"  # ロコン（ひのこ）
MANTINE_NEO4 = "neo4-031"  # マンタイン（おおなみ）
GLIGAR_NEO4 = "neo4-071"  # グライガー（しんけいどく）
JIGGLYPUFF_NEO4 = "neo4-085"  # プリン（ふくらむ）
DRATINI_NEO4 = "neo4-087"  # ミニリュウ（だっぴ・みだれづき）
GIRAFARIG_NEO4 = "neo4-089"  # キリンリキ（しっぽでかみつく・サイコキネシス）
CHANSEY_NEO4 = "neo4-092"  # ラッキー（おうふくびんた・タマゴなげ）
V0_79_POKEMON = (SANDSHREW_ES2, SANDSHREW_QSG, GASTLY_ES3, GASTLY_QSG, BROCKS_MANKEY_GD1, LT_SURGES_RATICATE_GD3, BLAINES_CHARMANDER_GD5, SABRINAS_HAUNTER_GD6, QUILAVA_NIP1, SNEASEL_PF3, ELECTABUZZ_PR1, ARTICUNO_PR1, STEELIX_PRN, PRIMEAPE_SI, SLOWKING_SI, MARILL_SI, ODDISH_NEO1, CHIKORITA_NEO1, LEDYBA_NEO1, SHUCKLE_NEO1, SUNFLORA_NEO1, JUMPLUFF_NEO1, MARILL_NEO1, SEADRA_NEO1, AZUMARILL_NEO1, PIKACHU_NEO1, CHINCHOU_NEO1, AMPHAROS_NEO1, SLOWPOKE_NEO1, NATU_NEO1, BEEDRILL_NEO2, HOUNDOUR_NEO2_FIRE, CORSOLA_NEO2, NATU_NEO2, ESPEON_NEO2, OMASTAR_NEO2, HITMONTOP_NEO2, SLUGMA_NEO3, HO_OH_NEO3, QWILFISH_NEO3, REMORAID_NEO3, SEAKING_NEO3, JYNX_NEO3, FLAAFFY_NEO3, SNUBBULL_NEO3, VULPIX_NEO4, MANTINE_NEO4, GLIGAR_NEO4, JIGGLYPUFF_NEO4, DRATINI_NEO4, GIRAFARIG_NEO4, CHANSEY_NEO4)
V0_79_CARDS = V0_79_POKEMON
# v0.80: トレーナー 30 枚（neo 期の拡張パック・拡張パック以外の商品。スタジアム 4 枚を含む。docs/neo-trainer-components-v0.80.md）
V0_80_CARDS = (
    "neo1-074", "neo1-087", "neo1-092", "neo2-053", "neo4-102", "neo1-078", "neo1-089", "neo1-091", "neo4-100", "neo1-082",
    "neo1-090", "neo1-093", "neo1-075", "neo1-076", "neo2-056", "GD5-017", "neo1-080", "neo4-105", "neo4-107", "neo4-111",
    "PR1-013", "PR1-074", "PRN-026", "neo1-077", "neo4-099", "neo3-054", "neo4-101", "neo4-106", "neo4-112", "ES2-033",
)
# v0.81: ポケモンのどうぐ 11 枚・ピントレンズ・常にはたらくスタジアム 3 枚（docs/pokemon-tools-stadiums-v0.81.md）
V0_81_CARDS = (
    "neo1-073", "PRN-004", "NIP1X-008", "NIP2X-008", "neo1-079", "neo1-081", "PRN-005", "neo3-055", "neo1-088", "neo4-103",
    "neo4-109", "neo4-104", "neo1-085", "neo3-057", "neo4-110",
)
# v0.82（docs/energy-discard-return-v0.82.md）: リサイクルエネルギー・エコロジムと、エネルギーカードをトラッシュするワザを持つポケモン 18 枚（写しの組 pool_v0_82 の並び）
RECYCLE_ENERGY = "neo1-096"
ECOGYM = "neo1-086"
V0_82_POKEMON = (
    "neo1-018", "PRN-007", "PRN-010", "ES3-011", "QSG-010", "ES3-012", "QSG-012", "QSG-011", "IP1-003", "PR1-062", "neo3-025", "neo1-041", "neo1-072",
    "neo4-025", "neo4-019", "PR1-071", "PF1-005", "neo3-014",
)
V0_82_CARDS = (RECYCLE_ENERGY, ECOGYM, *V0_82_POKEMON)
# v0.83（docs/shining-gentle-pokemon-v0.83.md）: ひかるポケモン 10 枚・やさしいポケモン 7 枚・ギャロップ（ES1-014）（写しの組 pool_v0_83 の並び）
SHINING_MAGIKARP, SHINING_MAGIKARP_PRN, SHINING_GYARADOS = "neo3-022", "PRN-046", "neo3-023"
SHINING_CELEBI, SHINING_RAICHU, SHINING_MEWTWO, SHINING_KABUTOPS = "neo4-013", "neo4-047", "neo4-068", "neo4-080"
SHINING_STEELIX, SHINING_NOCTOWL, SHINING_MEW = "neo4-084", "neo4-098", "PRN-044"
LIGHT_SUNFLORA, LIGHT_VENOMOTH, LIGHT_GOLDUCK, LIGHT_VAPOREON = "neo4-004", "neo4-006", "neo4-032", "neo4-034"
LIGHT_LANTURN, LIGHT_SLOWBRO, LIGHT_DRAGONAIR, RAPIDASH_ES1 = "neo4-045", "neo4-054", "neo4-093", "ES1-014"
V0_83_SHINING = (SHINING_MAGIKARP, SHINING_MAGIKARP_PRN, SHINING_GYARADOS, SHINING_CELEBI, SHINING_RAICHU, SHINING_MEWTWO, SHINING_KABUTOPS,
                 SHINING_STEELIX, SHINING_NOCTOWL, SHINING_MEW)
V0_83_POKEMON = (*V0_83_SHINING, LIGHT_SUNFLORA, LIGHT_VENOMOTH, LIGHT_GOLDUCK, LIGHT_VAPOREON, LIGHT_LANTURN, LIGHT_SLOWBRO, LIGHT_DRAGONAIR, RAPIDASH_ES1)
V0_83_CARDS = V0_83_POKEMON

# v0.84（docs/light-powers-evolution-v0.84.md）: やさしいポケモン 12 枚・ポケモン育て屋夫婦
BREEDER_COUPLE = "neo3-056"  # ポケモン育て屋夫婦（トレーナー。最大 2 匹にコイン 1 枚ずつ。「おもて」のポケモンから進化するカードを山札からさがす）
LIGHT_LEDIAN, LIGHT_NINETALES, LIGHT_ARCANINE, LIGHT_DEWGONG = "neo4-010", "neo4-018", "neo4-021", "neo4-033"
LIGHT_AZUMARILL, LIGHT_PILOSWINE, LIGHT_JOLTEON, LIGHT_MACHOKE = "neo4-040", "neo4-041", "neo4-043", "neo4-074"
LIGHT_MACHAMP, LIGHT_WIGGLYTUFF, LIGHT_DRAGONITE, LIGHT_TOGETIC = "neo4-077", "neo4-090", "neo4-094", "neo4-095"
V0_84_POKEMON = (LIGHT_LEDIAN, LIGHT_NINETALES, LIGHT_ARCANINE, LIGHT_DEWGONG, LIGHT_AZUMARILL, LIGHT_PILOSWINE, LIGHT_JOLTEON, LIGHT_MACHOKE,
                 LIGHT_MACHAMP, LIGHT_WIGGLYTUFF, LIGHT_DRAGONITE, LIGHT_TOGETIC)
V0_84_CARDS = (BREEDER_COUPLE, *V0_84_POKEMON)  # 写しの組 pool_v0_84 の並び
# 進化元（どれも前の版で対応済み。名前の完全一致で決まる）
LEDYBA_NEO1, VULPIX_NEO4, GROWLITHE_NEO4, SEEL_NEO4, MARILL_NEO1, SWINUB_NEO4 = "neo1-003", "neo4-014", "neo4-015", "neo4-027", "neo1-025", "neo4-029"
MACHOP_NEO4, JIGGLYPUFF_NEO4, TOGEPI_NEO1 = "neo4-069", "neo4-085", "neo1-066"

# v0.85（docs/entry-powers-energy-lifecycle-v0.85.md）: 進化したときの特殊能力・エネルギーを動かすポケモン 13 枚とミラクルエネルギー
BAYLEEF_NEO1, MEGANIUM_NEO1, TYPHLOSION_NEO1, FERALIGATR_NEO1, MAREEP_NEO1 = "neo1-009", "neo1-014", "neo1-021", "neo1-033", "neo1-038"
BAYLEEF_PF1, MEGANIUM_PF1, MEGANIUM_NIP1X, TYPHLOSION_PF1, CROCONAW_PF1 = "PF1-002", "PF1-003", "NIP1X-001", "PF1-006", "PF1-008"
FERALIGATR_PF1, FERALIGATR_NIP2X, CHARIZARD_PF2 = "PF1-009", "NIP2X-001", "PF2-009"
MIRACLE_ENERGY = "neo4-113"  # ミラクルエネルギー（特殊エネルギー。「ひかる」「やさしい」ポケモンにだけつけられ、つけた番の終わりにトラッシュする）
V0_85_POKEMON = (BAYLEEF_NEO1, MEGANIUM_NEO1, TYPHLOSION_NEO1, FERALIGATR_NEO1, MAREEP_NEO1, BAYLEEF_PF1, MEGANIUM_PF1, MEGANIUM_NIP1X,
                 TYPHLOSION_PF1, CROCONAW_PF1, FERALIGATR_PF1, FERALIGATR_NIP2X, CHARIZARD_PF2)
V0_85_CARDS = (*V0_85_POKEMON[:5], BAYLEEF_PF1, MEGANIUM_PF1, MEGANIUM_NIP1X, TYPHLOSION_PF1, CROCONAW_PF1, FERALIGATR_PF1, FERALIGATR_NIP2X, CHARIZARD_PF2,
               MIRACLE_ENERGY)  # 写しの組 pool_v0_85 の並び
# 進化元（どれも前の版で対応済み。名前の完全一致で決まる）
CHIKORITA_NEO1, CYNDAQUIL_NEO1, QUILAVA_PF1, TOTODILE_NEO1, CHARMELEON_BASE = "neo1-002", "neo1-018", "PF1-005", "neo1-024", "PMCG1-017"

# v0.86（docs/entry-energy-evolution-reactions-v0.86.md）: 登場・エネルギー・進化への反応 13 枚
EEVEE_NEO2, EEVEE_PF2, EEVEE_PRN = "neo2-049", "PF2-005", "PRN-024"  # イーブイ（［エナジーしんか］2 枚・［れんさしんか］）
ENTEI_NEO3, RAIKOU_NEO3, BLISSEY_NEO3, DRAGONITE_PR1, ENTEI_PF2 = "neo3-010", "neo3-029", "neo3-052", "PR1-056", "PF2-008"
DARK_CROBAT, DARK_FLAAFFY, DARK_AMPHAROS, SUICUNE_NEO3, VENUSAUR_PR1 = "neo4-012", "neo4-044", "neo4-046", "neo3-021", "PR1-058"
V0_86_POKEMON = (EEVEE_NEO2, EEVEE_PF2, EEVEE_PRN, ENTEI_NEO3, RAIKOU_NEO3, BLISSEY_NEO3, DRAGONITE_PR1, ENTEI_PF2, DARK_CROBAT, DARK_FLAAFFY, DARK_AMPHAROS,
                 SUICUNE_NEO3, VENUSAUR_PR1)
V0_86_CARDS = V0_86_POKEMON  # 写しの組 pool_v0_86 の並び

# v0.87（docs/movement-damage-reactions-v0.87.md）: 場の移動・ダメージへの反応と、ワザから守る特殊能力のポケモン 14 枚
FORRETRESS_NEO2, MAGCARGO_NEO3, DARK_MAGCARGO = "neo2-044", "neo3-009", "neo4-023"  # フォレトス［まきびし］・マグカルゴ［やけのこり］・わるいマグカルゴ［ヒートプレート］
LT_SURGES_ELECTRODE, KAKUNA_ES1, KOFFING_ES2 = "GD3-009", "ES1-005", "ES2-003"  # マチスのマルマイン［ショックボム］・コクーン［どくのたいえき］・ドガース［ぶんれつ］
MAGNEMITE_ES2, MAGNEMITE_QSG, GENGAR_PR1 = "ES2-014", "QSG-023", "PR1-053"  # コイル［マグネット］2 枚・ゲンガー［やみのちから］
ARTICUNO_ES2, ARTICUNO_QSG, DUGTRIO_PR1 = "ES2-012", "QSG-057", "PR1-046"  # フリーザー［オーロラヴェール］2 枚・ダグトリオ［もぐる］
SNORLAX_ES1, SNORLAX_QSG = "ES1-034", "QSG-046"  # カビゴン［とおせんぼ］2 枚
PINECO_NEO4, SLUGMA_NEO4 = "neo4-005", "neo4-017"  # 進化元（クヌギダマ・マグマッグ）
V0_87_POKEMON = (FORRETRESS_NEO2, MAGCARGO_NEO3, DARK_MAGCARGO, LT_SURGES_ELECTRODE, KAKUNA_ES1, KOFFING_ES2, MAGNEMITE_ES2, MAGNEMITE_QSG, GENGAR_PR1,
                 ARTICUNO_ES2, ARTICUNO_QSG, DUGTRIO_PR1, SNORLAX_ES1, SNORLAX_QSG)
V0_87_CARDS = V0_87_POKEMON

# v0.88（docs/type-energy-colors-v0.88.md）: ポケモンのタイプとエネルギーの色を変える特殊能力、色を選ぶ・数えるワザ、変えたカードをつけ替える特殊能力の 11 枚
LANTURN_NEO1, LANTURN_NEO3, PORYGON2_NEO3 = "neo1-040", "neo3-026", "neo3-051"  # ランターン［すいりょくはつでん］・ランターン［せんすい］・ポリゴン2［エナジーコンバーター］
ERIKAS_ODDISH_GD4, STARMIE_NEO3, MEW_SI = "GD4-001", "neo3-034", "SI-004"  # エリカのナゾノクサ［こうごうせい］・スターミー（コアストリーム）・ミュウ（レインボーウェーブ）
HO_OH_PF3, MAGNETON_NEO3 = "PF3-007", "neo3-045"  # ホウオウ（レインボーバーン）・レアコイル［でんじりょく］
PORYGON_ES1, PORYGON_QSG, COOL_PORYGON = "ES1-033", "QSG-045", "PR1-023"  # ポリゴン（テクスチャー2）2 枚・かっこいいポリゴン（テクスチャーマジック）
V0_88_POKEMON = (LANTURN_NEO1, LANTURN_NEO3, PORYGON2_NEO3, ERIKAS_ODDISH_GD4, STARMIE_NEO3, MEW_SI, HO_OH_PF3, MAGNETON_NEO3, PORYGON_ES1, PORYGON_QSG,
                 COOL_PORYGON)
V0_88_CARDS = V0_88_POKEMON  # 写しの組 pool_v0_88 の並び

# v0.89（docs/selected-target-damage-v0.89.md）: 対象を選ぶダメージ・選べる回復のポケモン 17 枚（同じ名前の別の版と取りちがえない）
UMBREON_NEO2, DARK_OMANYTE, BROCKS_GEODUDE_GD1 = "neo2-040", "neo4-035", "GD1-007"  # ブラッキー（だましうち）・わるいオムナイト（てっぽうみず）・タケシのイシツブテ（ロングショット）
MISTYS_SEAKING_GD2, SABRINAS_MR_MIME_GD6 = "GD2-011", "GD6-011"  # カスミのアズマオウ（だくりゅう）・ナツメのバリヤード（マジックダーツ）
RAICHU_ES2, RAICHU_QSG, MAGNETON_ES2, MAGNETON_QSG = "ES2-013", "QSG-022", "ES2-015", "QSG-024"  # ライチュウ（ろうでん）2 枚・レアコイル（マイクロウェーブ）2 枚
LICKITUNG_SI, EXEGGUTOR_SI = "SI-010", "SI-013"  # ベロリンガ（きずをなめる・のびるベロ）・ナッシー（ねらいだま）
MACHOKE_ES3, CUBONE_ES3, MEOWTH_PR1 = "ES3-028", "ES3-030", "PR1-057"  # ゴーリキー（きあいだま）・カラカラ（ほねをなげる）・ニャース（ねこパンチ）
ZAPDOS_PR1, ZAPDOS_ES2, ZAPDOS_QSG = "PR1-070", "ES2-018", "QSG-056"  # サンダー（ライトニングバーン）・サンダー（らくらい・サンダークラッシュ）2 枚
V0_89_POKEMON = (UMBREON_NEO2, DARK_OMANYTE, BROCKS_GEODUDE_GD1, MISTYS_SEAKING_GD2, SABRINAS_MR_MIME_GD6, RAICHU_ES2, RAICHU_QSG, MAGNETON_ES2, MAGNETON_QSG,
                 LICKITUNG_SI, EXEGGUTOR_SI, MACHOKE_ES3, CUBONE_ES3, MEOWTH_PR1, ZAPDOS_PR1, ZAPDOS_ES2, ZAPDOS_QSG)
V0_89_CARDS = V0_89_POKEMON  # 写しの組 pool_v0_89 の並び

# v0.90（docs/markers-counters-v0.90.md）: マーカー・ダメージカウンター以外のカウンターのポケモン 7 枚（同じ名前の別の版と取りちがえない）
GRIMER_ES2, MAROWAK_ES2, MEWTWO_ES3 = "ES2-002", "ES2-025", "ES3-026"  # ベトベター（ベトベトえき）・ガラガラ（ほねさがし・ほねこんぼう）・ミュウツー（かんぜんかいふく）
HUNGRY_SNORLAX, CUBONE_PR1, JYNX_PR1, SMEARGLE_PRN = "PR1-024", "PR1-034", "PR1-035", "PRN-029"  # くいしんぼカビゴン・カラカラ（ボーンキラー）・ルージュラ（あくまののろい）・ドーブル（ペイント）
V0_90_POKEMON = (GRIMER_ES2, MAROWAK_ES2, MEWTWO_ES3, HUNGRY_SNORLAX, CUBONE_PR1, JYNX_PR1, SMEARGLE_PRN)
V0_90_CARDS = V0_90_POKEMON  # 写しの組 pool_v0_90 の並び

# v0.91（docs/marker-check-field-reset-v0.91.md）: 残りのマーカーのポケモン 3 枚とヒノアラシ（同じ名前の別の版と取りちがえない）
QUILAVA_NEO1, ELECTABUZZ_ES2, POLYGON_PRN, CYNDAQUIL_NEO4 = "neo1-020", "ES2-017", "PRN-023", "neo4-016"  # マグマラシ（やきこがす）・エレブー（ひらいしん）・ポリゴン（オールクリア）・ヒノアラシ（えんまく）
V0_91_POKEMON = (QUILAVA_NEO1, ELECTABUZZ_ES2, POLYGON_PRN, CYNDAQUIL_NEO4)
V0_91_CARDS = V0_91_POKEMON  # 写しの組 pool_v0_91 の並び

# v0.92（docs/power-suppression-lasting-locks-v0.92.md）: 能力の消去・続く制限のポケモン 8 枚（同じ名前の別の版と取りちがえない）
SPINARAK_NEO1, ARIADOS_NEO1, ONIX_NEO1, MURKROW_NEO1 = "neo1-004", "neo1-011", "neo1-050", "neo1-055"  # イトマル（こわいかお）・アリアドス（クモのす・きゅうけつどく）・イワーク（いやなおと）・ヤミカラス（くろいまなざし）
GOLBAT_NEO3, LARVITAR_NEO4, SABRINAS_GENGAR_GD6, SCIZOR_PRN = "neo3-004", "neo4-073", "GD6-008", "PRN-025"  # ゴルバット（いやなおと・きゅうけつどく）・ヨーギラス（にらみつける）・ナツメのゲンガー（やみのはどう）・ハッサム（メタルニッパー）
V0_92_POKEMON = (SPINARAK_NEO1, ARIADOS_NEO1, ONIX_NEO1, MURKROW_NEO1, GOLBAT_NEO3, LARVITAR_NEO4, SABRINAS_GENGAR_GD6, SCIZOR_PRN)
V0_92_CARDS = V0_92_POKEMON  # 写しの組 pool_v0_92 の並び

# v0.93（docs/active-leave-locks-v0.93.md）: バトル場をはなれられない効果・続くワザの制限のポケモン 9 枚（同じ名前の別の版と取りちがえない）。キャタピーの 2 枚は同じゲーム用データ
CATERPIE_ES1, CATERPIE_QSG, TANGELA_ES2 = "ES1-002", "QSG-002", "ES2-004"  # キャタピー（からまるいと）・キャタピー（同じデータ）・モンジャラ（からみつく）
GLOOM_NEO1, CROCONAW_NEO1, DARK_ARIADOS_NEO4 = "neo1-008", "neo1-030", "neo4-011"  # クサイハナ（へんなこな・ねばるみつ）・アリゲイツ（いやなおと・くいつく）・わるいアリアドス（からめとる・どくしばり）
PILOSWINE_NEO1, DARK_CROCONAW_NEO4, OCTILLERY_NEO3 = "neo1-032", "neo4-036", "neo3-019"  # イノムー（こおりつかせる・ふぶき）・わるいアリゲイツ（かぶりつく）・オクタン（からみつく・オクタンほう）
SWINUB_NEO1 = "neo1-027"  # ウリムー（イノムーの進化元）
V0_93_POKEMON = (CATERPIE_ES1, CATERPIE_QSG, TANGELA_ES2, GLOOM_NEO1, CROCONAW_NEO1, DARK_ARIADOS_NEO4, PILOSWINE_NEO1, DARK_CROCONAW_NEO4, OCTILLERY_NEO3)
V0_93_CARDS = V0_93_POKEMON  # 写しの組 pool_v0_93 の並び

# v0.94（docs/switch-return-attacks-v0.94.md）: 入れ替え・帰還のワザのポケモン 13 枚（ワザ 21）。ピッピ・ロコンの 2 組は同じゲーム用データ
CLEFAIRY_ES1, CLEFAIRY_QSG, JIGGLYPUFF_SI, SNUBBULL_NEO1 = "ES1-026", "QSG-040", "SI-002", "neo1-061"  # ピッピ（このゆびとまれ）・同じデータ・プリン（ひとみでさそう）・ブルー（ほえる）
VENOMOTH_ES2, DONPHAN_NEO1, TOGEPI_PRN, BELLOSSOM_PRN = "ES2-001", "neo1-054", "PRN-033", "PRN-043"  # モルフォン・ドンファン（こうそくスピン）・トゲピー（はしゃぐ）・キレイハナ
TAUROS_ES3, MACHAMP_PR1, VULPIX_ES3, VULPIX_QSG, DARK_DONPHAN = "ES3-034", "PR1-052", "ES3-009", "QSG-008", "neo4-078"  # ケンタロス・カイリキー・ロコン（きつねび）・同じデータ・わるいドンファン
PHANPY_NEO4 = "neo4-072"  # ゴマゾウ（ドンファン・わるいドンファンの進化元）
V0_94_POKEMON = (CLEFAIRY_ES1, CLEFAIRY_QSG, JIGGLYPUFF_SI, SNUBBULL_NEO1, VENOMOTH_ES2, DONPHAN_NEO1, TOGEPI_PRN, BELLOSSOM_PRN, TAUROS_ES3, MACHAMP_PR1, VULPIX_ES3,
                 VULPIX_QSG, DARK_DONPHAN)
V0_94_CARDS = V0_94_POKEMON  # 写しの組 pool_v0_94 の並び

# v0.95（docs/private-looks-deck-movement-v0.95.md）: 手札・山札を見る効果とカードを動かすポケモン 11 枚（ワザ 20・特殊能力 2）。ゴーストの 2 枚は同じゲーム用データ
XATU_NEO1, NOCTOWL_NEO1, SENTRET_NEO2, SABRINAS_ABRA_GD6 = "neo1-048", "neo1-065", "neo2-046", "GD6-002"  # ネイティオ（みらいよち）・ヨルノズク（［みやぶる］）・オタチ（さぐる）・ナツメのケーシィ（とうし）
HAUNTER_ES3, HAUNTER_QSG, DARK_SCIZOR_NEO4, DARK_SLOWKING_NEO4 = "ES3-024", "QSG-029", "neo4-083", "neo4-061"  # ゴースト（ポルターガイスト）・同じデータ・わるいハッサム（おどす）・わるいヤドキング（［わるぢえ］）
DARK_QUILAVA_NEO4, RHYDON_ES3, AIPOM_NEO3 = "neo4-020", "ES3-031", "neo3-047"  # わるいマグマラシ（もやす・マグマラッシュ）・サイドン（やまくずし）・エイパム（とりさる）
NATU_NEO1, HOOTHOOT_NEO1, SLOWPOKE_NEO1, CYNDAQUIL_NEO1, RHYHORN = "neo1-046", "neo1-060", "neo1-045", "neo1-018", "PMCG2-030"  # 進化元（ネイティ・ホーホー・ヤドン・ヒノアラシ・サイホーン）
V0_95_POKEMON = (XATU_NEO1, NOCTOWL_NEO1, SENTRET_NEO2, SABRINAS_ABRA_GD6, HAUNTER_ES3, HAUNTER_QSG, DARK_SCIZOR_NEO4, DARK_SLOWKING_NEO4, DARK_QUILAVA_NEO4, RHYDON_ES3,
                 AIPOM_NEO3)
V0_95_CARDS = V0_95_POKEMON  # 写しの組 pool_v0_95 の並び

# v0.96（docs/unown-family-powers-v0.96.md）: アンノーン 7 枚（ワザ 7・特殊能力 7）と遺跡の石版 2 枚（同じゲーム用データ）。名前の書き方は「アンノーン[E]」「アンノーンL」の 2 通り
UNOWN_E, UNOWN_O, UNOWN_R = "PF2-002", "PF2-003", "PRN-035"  # アンノーン[E]（［ENGAGE］）・アンノーン[O]（［OBSERVE］）・アンノーン[R]（［REASSURE］）
UNOWN_L, UNOWN_S, UNOWN_T, UNOWN_Z = "neo4-050", "neo4-051", "neo4-052", "neo4-060"  # アンノーンL（［LAUGH］）・S（［SEARCH］）・T（［TELL］）・Z（［ZOOM］）
RUIN_WALL, RUIN_WALL_2 = "neo2-054", "neo2-057"  # 遺跡の石版（2 枚は同じゲーム用データ）
V0_96_POKEMON = (UNOWN_E, UNOWN_O, UNOWN_R, UNOWN_L, UNOWN_S, UNOWN_T, UNOWN_Z)
V0_96_TRAINERS = (RUIN_WALL, RUIN_WALL_2)
V0_96_CARDS = V0_96_POKEMON + V0_96_TRAINERS  # 写しの組 pool_v0_96 の並び


def _self_sleep_shape_only(attack):
    from kyuura_engine.effects import _check_damage_then_effect

    return _check_damage_then_effect(attack, "自分をねむり状態にする")


def self_sleep_for_other_text():
    """テスト専用（v0.87）: 説明の違うワザ（ゴーストの「あくむ」・ケーシィの「ねんりき」）を、テスト専用の登録表で「ダメージを与えた後、自分を「ねむり」状態にする」
    （``DamageAndSelfSleep``）として処理するための実装。v0.87 から ``DamageAndSelfSleep.check`` は日本語の全文を確かめるので、この 1 つの値だけ全文の比べを外し、
    形（ダメージの目安があること）の確かめは残す。型は ``DamageAndSelfSleep`` のまま（要素の並び・先読み・止める問いは製品の登録と同じ）。製品の登録表には使わない。"""
    from kyuura_engine.effects import DamageAndSelfSleep

    effect = DamageAndSelfSleep()
    object.__setattr__(effect, "check", _self_sleep_shape_only)
    return effect
