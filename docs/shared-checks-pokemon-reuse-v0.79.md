# v0.79: v0.78 の共通処理の修正と、ポケモン 52 枚・ワザ 94

作業ブランチ `claude/v0.79-shared-checks-pokemon-reuse`（v0.78 の `513ef66` から作った）。写しの元・研究の基準は kyuura `7d3f4ca76c084774efb4ac6a1d3a943387e183c3` のまま、
ルールの基準は 2000.02.14 版のまま。カードデータは kyuura の `data/cards.json`（日本語の欄）を採用した。公式ガイドブックのキャプチャ・OCR・読み直しはしていない。52 枚の
pcg-search.com のページ・カードの画像も照合していない（外部照合なし。kyuura の日本語の文面の多くは pcg-search.com・nazonobasho.com・ポケモンWiki の転記で、同じ所を開き直す
ことは独立した照合にならない）。英語の欄・現代のルール・後年の裁定で日本語の不足を補っていない。

## 1. 対象と数

| | v0.78 | v0.79 |
|---|---|---|
| 写し・対応するカード | 891・891 | 943・943 |
| 対応ポケモン・トレーナー・エネルギー | 643・213・35 | 695・213・35 |
| ワザ・特殊能力・トレーナー・特殊エネルギーの登録 | 1,088・74・213・17 | 1,182・74・213・17 |
| 未対応（全対象・neo・拡張パック以外） | 486・263・223 | 434・227・207 |
| 停止コード・未解決の裁定 | 165・167 | 166・168 |

- 写しの組 `pool_v0_79`（52 枚。neo 36 枚・拡張パック以外の商品 16 枚）を加え、写しの作り直しの道具で作った（手で直していない）。v0.78 までの 891 枚の写しの値・組は変わらない
  （`--check` が通る）。未対応の数は kyuura data/engine_targets.json（7d3f4ca）の対象 1,377 件から今の登録を差し引いて数えた（`engine_status` は v0.68 の時点の索引なので使わない）。
- 保留したカードはない。GD5-007・IP2-032（表記の違うウィンディ）は今までどおり対象外、NIP1X-004 は除いた。リサイクルエネルギー・ミラクルエネルギー・ベイビィ・ひかるポケモン・
  「にげる」を変える効果・アンノーンは対象にしていない（新しい特殊能力・特殊エネルギーもない）。
- 52 枚（カード id・名前・ワザ・型）:

| id | 名前 | ワザと型 |
|---|---|---|
| ES2-020 / QSG-033 | サンド（同じデータ） | どくばり `PoisonOnHeads`・スピードスター `DamageIgnoringDefenderEffects`（「抵抗カ」の書き方） |
| ES3-022 / QSG-028 | ゴース（同じデータ） | こわがらせる `LockOpponentTrainersNextTurn`・あんこく `ConfuseOnHeads` |
| GD1-005 | タケシのマンキー | からかう `SwitchOpponentActive`・けとばす `DamageOnly` |
| GD3-012 | マチスのラッタ | いかりのまえば `HalfRemainingHpDamage`（切り上げ。ダメージの目安なし） |
| GD5-001 | カツラのヒトカゲ | ファイヤーテール `DamageThenDiscardOneOnTails`（新） |
| GD6-007 | ナツメのゴースト | あくむ `SleepOpponent`・かげからおそう `CoinChooseOpponentBenchDamage`（新） |
| NIP1-013 | マグマラシ | たいあたり `DamageOnly`・かえんほうしゃ `DiscardEnergyThenDamage(炎)` |
| PF3-003 | ニューラ | だましとる `CoinDiscardAllOpponentTrainers`（新）・でんこうせっか `CoinBonusDamage(20)` |
| PR1-010 | エレブー | ひかりのかべ `HalveDamageNextTurn`・でんこうせっか `CoinBonusDamage(20)` |
| PR1-064 | フリーザー | ダイヤモンドダスト `DamageThenParalyzeAndOpponentBenchOnHeads(10)`（新） |
| PRN-014 | ハガネール | メタルクラッシュ `FailOnTailsDamageThenSelfCannotAttack`（新）・じひびき `DamageThenRetreatLock` |
| SI-012 | オコリザル | けたぐり `DamageOnly`・いかりくるう `DamagePlusOwnCountersThenSelfConfuseOnTails(10)` |
| SI-014 | ヤドキング | ひらめく `SearchTrainerRequiredOnHeads`（新）・サイコキネシス `DamagePlusDefenderEnergy(10)` |
| SI-017 | マリル | みずとばし `ChooseOpponentPokemonDamage(10)`・ころがりタックル `DamageOnly` |
| neo1-001 | ナゾノクサ | かくれる `SelfBarrierOnHeads`・すいとる `DamageAndDrain` |
| neo1-002 | チコリータ | たいあたり `DamageOnly`・リフレクター `HalveDamageNextTurn` |
| neo1-003 | レディバ | ちょうおんぱ `ConfuseOnHeadsWithoutDamage`・れんぞくパンチ `CoinFlipDamage(4, 10)` |
| neo1-007 | ツボツボ | からにこもる `PreventDamageOnHeads`・まきつく `ParalyzeOnHeads` |
| neo1-013 | キマワリ | はなびらのまい `CoinFlipDamageThenSelfConfuse(3, 30)` |
| neo1-016 | ワタッコ | ねむりごな `SleepOpponent`・やどりぎのたね `DamageAndRemoveCounters(1)` |
| neo1-025 | マリル | まるくなる `PreventDamageOnHeads`・バブルボム `DamageThenParalyzeOrSelfDamage(10)` |
| neo1-029 | シードラ | あわ `ParalyzeOnHeads`・だくりゅう `DamageThenCoinBenchDamage(10)` |
| neo1-034 | マリルリ | たいあたり `DamageOnly`・バブルシャワー `DamageThenParalyzeAndOpponentBenchOnHeads(10)`（新） |
| neo1-036 | ピカチュウ | でんこうせっか `CoinBonusDamage(10)`・こうそくいどう `DamageThenPreventAttackDamageOnHeads`（新） |
| neo1-037 | チョンチー | ちょうおんぱ `ConfuseOnHeadsWithoutDamage`・じたばた `DamageTimesOwnCounters(10)` |
| neo1-043 | デンリュウ | ギガショック `DamageThenParalyzeAndOpponentBenchOnHeads(10)`（新） |
| neo1-045 | ヤドン | ねんりき `ParalyzeOnHeads`・みずでっぽう `ExtraEnergyDamage(水, 10, 2)` |
| neo1-046 | ネイティ | つつく `DamageOnly`・テレキネシス `ChooseOpponentPokemonDamage(20)` |
| neo2-010 | スピアー | さんばいどく `DamageThenSpecialPoisonOnHeads(30)`・ミサイルばり `CoinFlipDamage(4, 20)` |
| neo2-012 | デルビル | スモッグ `PoisonOnHeads`・ほのおをまとう `DamageThenAttachEnergyFromDiscardToSelf(炎)` |
| neo2-017 | サニーゴ | じこさいせい `DiscardEnergyAndRemoveAllCounters(水)`・とげキャノン `CoinFlipDamage(2, 30)` |
| neo2-022 | ネイティ | あやしいひかり `ConfuseOnHeads` |
| neo2-029 | エーフィ | かみつく `DamageOnly`・サイコキネシス `DamagePlusDefenderEnergy(10)` |
| neo2-035 | オムスター | しめあげる `CoinBonusDamageAndParalyze(20)`・とげとげMAX `CoinsPerAttachedTypeBonusDamage(水, 20)` |
| neo2-038 | カポエラー | みきり `SelfBarrierOnHeads`・トリプルキック `CoinFlipDamage(3, 30)` |
| neo3-008 | マグマッグ | ほのお `DamageOnly`・マグマでかこむ `DamageThenRetreatLock` |
| neo3-011 | ホウオウ | もえあがる `AttachEnergyFromDeckToSelfExactly(炎)`・せいなるほのお `CoinChooseOpponentPokemonDamage(40)`・ゴッドバード `FailOnTailsDamage(1)` |
| neo3-015 | ハリーセン | どくばり `PoisonOnHeads`・はりせんぼん `CoinsUntilTailsDamage(20)` |
| neo3-016 | テッポウオ | ねらいうち `CoinChooseOpponentPokemonDamage(20)` |
| neo3-017 | アズマオウ | つきあげる `CoinBonusDamage(10)`・つのでいちげき `CoinsAllHeadsBonusDamage(2, 40)` |
| neo3-018 | ルージュラ | こごえるキッス `PutToSleep`・あやしいおどり `CoinBonusDamageAndConfuse(20)`（新） |
| neo3-027 | モココ | ビリリパンチ `DamageOnly`・エレキテール `DamageThenOpponentBenchOnHeads(10)`（新） |
| neo3-048 | ブルー | かみつく `DamageOnly`・いかりのずつき `CoinBonusPerOwnCounter(10)`（新） |
| neo4-014 | ロコン | ひのこ `DiscardEnergyThenDamage(炎)` |
| neo4-031 | マンタイン | おおなみ `DamageThenSelfCannotAttack` |
| neo4-071 | グライガー | しんけいどく `DamageThenPoisonAndParalyzeOnHeads` |
| neo4-085 | プリン | ふくらむ `DamageThenReduceDamageNextTurn(10)` |
| neo4-087 | ミニリュウ | だっぴ `HealSelfWithoutDamage(1)`（新）・みだれづき `CoinFlipDamage(2, 10)` |
| neo4-089 | キリンリキ | しっぽでかみつく `CoinBonusDamage(20)`・サイコキネシス `DamagePlusDefenderEnergy(10)` |
| neo4-092 | ラッキー | おうふくびんた `CoinFlipDamage(2, 20)`・タマゴなげ `FailOnTailsDamage(2)` |

- 処理に使う文面は、どのワザも kyuura の印刷の文面（採用の記録の `play_text` は `kyuura_printed_text`。研究の対応表の `adopted_printed_text` に説明文のあるワザ 83）。
- ES2-020 と QSG-033（サンド）・ES3-022 と QSG-028（ゴース）は同じデータで、id ごとに登録したうえで同じ登録の値にまとめた（`effects.SAME_DATA_CARDS_V0_79`）。記録は id ごと。
  ほかのカードは名前・同じカードの組で自動ではまとめていない。
- 進化は名前の完全一致と段階で決まり、商品をまたぐ（マリルリ ← マリル、デンリュウ ← モココ ← メリープ、ハガネール ← イワーク、ヤドキング ← ヤドン、ナツメのゴースト ← ナツメのゴース など）。

## 2. A: ポケモンチェックの途中のきぜつ（PK1。新規）

v0.78 は、ポケモンチェックの 1（悪エネルギー）と 2（どく）のあいだのきぜつの判定の時点を決めず、両方のプレイヤーのポケモンがきぜつする場合だけを止めていた。片方のプレイヤーだけの
きぜつは、どの時点でも結果が変わらないとしていたが、変わる場合があった。

- 再現（v0.78 は `TAKE_PRIZE` に進む）: 番 7・番のプレイヤー 0。プレイヤー 0 のバトル場にベトベトン（PMCG3-007。HP 70・ダメージ 60・neo1-094 の悪エネルギー）、プレイヤー 1 の
  バトル場にどく 10 のカブト（PMCG3-035）。プレイヤー 0 が `EndTurn`。悪エネルギーでベトベトンが HP 以上になる。2 のあとにきぜつを判定するなら、2 の時点でかがくへんかガスが
  はたらき、カブトアーマーは消えているのでどく 10 をそのまま受ける。1 と 2 のあいだに判定するなら、ベトベトンが場をはなれてガスが消え、カブトアーマーを当てはめるか（KA1）の
  問いになる。
- 新しい問い PK1（`UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT`。kyuura の未解決の一覧にない `not_in_kyuura`）: 1 で HP 以上になったポケモンがいるとき、そのポケモンが 1 と 2 のあいだに
  場をはなれる読み方と、2 のあとまで場に残る読み方で、ほかのポケモンの 2 の「どく」と 2 のあとのきぜつの判定の問い合わせが変わるなら、ダメージを与える前に対戦を止める。範囲は
  ポケモンチェックの 1 と 2 のあいだのきぜつの判定の時点だけ（ワザ・特殊能力のあとのきぜつ、ポケモンチェックの 2 と 3 のあいだには広げていない）。裁定は決めていない。
- 判定は一般の比べ（`procedures.mid_check_knockout_divergence`。カード id で分けない）: 状態の複製に 1 の結果をのせ、HP 以上のポケモンを場から除いた複製と除かない複製で、場に残る
  ポケモンごとに「どくのダメージ（KA1 で止めるか・鋼エネルギーを当てはめた量）・2 のあとに今有効な最大HP以上になるか・2 のあとに［ずらかる］の残りHP「10」になるか・2 のあとに
  HP 以上になるポケモンの特殊能力が消えているか」（`_mid_check_view`）を比べる。答えを求めると止まる（VS1 など）なら、その停止コードを答えとして比べる。
- 変わらない盤面（どく状態のポケモンがいない・受ける量が変わらない・ガスの発生源でない・鋼エネルギーでどちらの読み方でも 0）は v0.78 と同じに進む。悪エネルギーのない
  ポケモンチェックは何も変えていない（この確かめは悪エネルギーの効果があるときだけ）。
- 既存の停止との順番: 1 の DE1・VS1・［ベンチガード］、2 の KA1（今の読み方で止まるなら、その停止のまま）のあと、SC1・両方のきぜつの前に確かめる。［へんしん］のメタモンが写している
  ポケモンが 1 で HP 以上になる盤面（メタモンの最大HPが変わり、2 のあとにきぜつするかが変わる）は、v0.78 はコマンドのあとの MH1（`UNRESOLVED_MAX_HP_DROP`。`EndTurn` の拒否）で
  止めていたが、v0.79 はポケモンチェックの中で PK1 で止める（どちらも決められない場面の停止）。

## 3. B: ワザでないダメージの止める確かめを最終の量で比べる

v0.78 の DE1（悪エネルギーのダメージ）・KA1（どく）は、受けるダメージを変える常にはたらく特殊能力（カブトアーマー・なぞのかべ）を当てはめると量が変わるかを、鋼エネルギー
（NIP1X-010。説明のとおり当てはめる -10）を数えずに比べていたので、どの読み方でも最終の量が 0 になる盤面でも止めていた。

- 共通の比べ `effects.non_attack_change_matters`（量の関数の並び）: どの効果も当てはめない量（鋼エネルギーは当てはめる）と、効果の組を当てはめる量を、鋼エネルギーの前・あとの
  すべての順番で比べ、違う量になる効果を返す。DE1・KA1・RB4（レインボーエネルギーの 10）・EX1（爆発ジムの 20）・TD1（トレーナーのダメージ。持続する効果も）が同じ関数を使う。
  同じ原因（鋼エネルギーを数えない比べ）なので、5 つとも直した。MT1（特殊能力のダメージ。当てはめるのは決まっていて、順番だけが問い）は v0.78 から最終の量で比べている。
- 止めない: カブト + neo1-094 + NIP1X-010（10 → 半分 0 → -10 でも、-10 → 0 → 半分でも 0）・どく 10 のカブト + NIP1X-010・レインボーエネルギー（10）・バトル場は穴だらけ!（10）を
  NIP1X-010 のカブトに。
- 止める（隣の場面）: neo1-095 の鋼エネルギー（ワザによるダメージだけ）+ neo1-094 のカブト（DE1）・鋼エネルギーのないカブト・特殊などく 20 + NIP1X-010（半分にすると 0、しなければ 10。KA1）。
- 悪エネルギー（NIP2X-010）のダメージカウンターはダメージではないので、変えない・比べない（今までどおり）。
- EX1 は、手札から出したばかりのたねポケモンにエネルギーがないので対戦では起こらない（関数を直接呼んで確かめた）。

## 4. C: v0.78 の検証の報告の訂正

v0.78 の文書（docs/darkness-metal-energy-v0.78.md 10 章）は「ワザでないダメージを 0 までへらす場面（`darkness_damage_reduced`）は起こらなかった」と書いていた。これは誤り。

- `darkness_damage_reduced` は、悪エネルギーの 10 ダメージを鋼エネルギーで減らした回数だけを数える値で、0 回だった（悪エネルギー自身の10の軽減は未発生）。
- `metal_nonattack`（ワザでないダメージを NIP1X-010 で減らした回数）は 42 回で、利用者が同じ 60 局を独立に走らせ直して、どれも最終のダメージが 0 であることを確かめた（例:
  `C77` 対 `M78`・seed 0・37 番の `poison_damage`。`amount_before` 10・`amount` 0・`energy_reduction` あり）。v0.78 の作業の実行は 42 回を数えたが、0 になったかを確かめていなかった。
- v0.78 の文書は「悪エネルギー自身の10の軽減は未発生。どく等を含む非ワザダメージの0化は42回確認」と直した（だれが走らせたかを書き分けた）。60 局は走らせ直していない。
- 集計に `nonattack_zeroed`（ワザでないダメージを減らして最終が 0 になった回数。悪エネルギーのダメージも含む）を加えた（`tools/existing_effect_games.py` の `v078_uses`）。
  `darkness_damage_reduced` の意味は変えていない。

## 5. 新しい組み合わせ（11 の型・13 のワザ）

どれも既存の要素の組み合わせ（`resolution/programs.py` の `BUILDERS`）で、カード id の分岐はない。`ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていない
（上限を超えたら `UNSUPPORTED_PREFLIGHT_LIMIT`。先読みの方法 legacy はすべての結果を試す方法になる）。説明の文面は、登録の値（ダメージ・コインの面・特殊状態・対象・枚数）と
結びつけた全文だけを受け付ける。

| 型 | ワザ | 要素の並び | 意味 |
|---|---|---|---|
| D `DamageThenParalyzeAndOpponentBenchOnHeads` | バブルシャワー（30）・ギガショック（40）・ダイヤモンドダスト（20） | `ReparalysisGuard` → `Coin` → `Damage` → `BenchDamage(gate)` → `Status(マヒ, gate)` | 1 枚のコインで、マヒと相手の控え全員に弱点・抵抗力なしの 10 |
| E `DamageThenPreventAttackDamageOnHeads` | ピカチュウ（neo1-036）のこうそくいどう | `Damage` → `SelfPersistent(prevent_attack_damage, local_coin)` | 「おもて」なら次の相手の番、ワザによるダメージだけを受けない |
| F `DamageThenOpponentBenchOnHeads` | エレキテール | `Coin` → `Damage` → `BenchDamage(gate)` | 「おもて」なら相手の控え全員に 10 だけ |
| G `CoinBonusDamageAndConfuse` | あやしいおどり | `Coin` → `Damage(目安 + 20)` → `Status(こんらん, gate)` | 「おもて」なら 40 とこんらん、「うら」なら 20 |
| H `CoinBonusPerOwnCounter` | いかりのずつき | `Damage(HeadsPlusOwnCounters)` | 「おもて」なら 10 + 自分のカウンター × 10、「うら」なら 10 |
| I `HealSelfWithoutDamage` | だっぴ | `HealCounters(1)` | ダメージなし。自分のカウンターを 1 個 |
| J `DamageThenDiscardOneOnTails` | ファイヤーテール | `Damage` → `DiscardOwnEnergy(炎, 1, local_coin=うら, when_lacking=skip)` | 20 のあと「うら」なら炎エネルギーカードを 1 枚選んでトラッシュ |
| K `CoinChooseOpponentBenchDamage` | かげからおそう | `ChosenBenchDamage(30)` | 「おもて」なら相手の控え 1 匹に弱点・抵抗力なしの 30。対戦ポケモンにはダメージなし |
| L `SearchTrainerRequiredOnHeads` | ひらめく | `RevealTrainerFromDeck(required=True)` | 「おもて」なら山札のトレーナーカード 1 枚を必ず見せて手札に加え、切る |
| M `CoinDiscardAllOpponentTrainers` | だましとる | `DiscardOpponentTrainers(all_pokemon=True, local_coin=おもて)` | 「おもて」なら相手の場のポケモン全員のトレーナーカードをすべてトラッシュ |
| N `FailOnTailsDamageThenSelfCannotAttack` | メタルクラッシュ | `FailOnTails` → `Damage` → `SelfCannotAttack(even_if_failed=True)` | 「うら」なら失敗。どちらでも次の自分の番はワザを使えない |

- D: マヒとダメージの順番は、ダメージの要素をまとめてのせてから効果（p.89 の「ダメージを受けたとき」の効果の時点。v0.39 の `DamagePoisonAndBenchDamage` と同じ）。相手の対戦ポケモンが
  このワザで HP 以上・「ダメージを受けない」状態でも、控えへのダメージは残る（効果の要素ではマヒを与える。「ダメージを受けない」状態でもマヒは受ける）。相手の対戦ポケモンが
  「ワザをうけない」状態で控えがいなければ、コインが決める要素がどれも無効なので HC3（v0.34 の `void_coin_question`）。控えへのダメージは、とうめい・見えない壁・［ベンチガード］・
  ［だつりょくえき］の既存の処理のまま。
- E: 持続する効果 `state.PreventAttackDamage`（`PreventDamage` の部分型。種類 `prevent_attack_damage`。下の 7 章）。でんこうせっかの追加は 10（英語の欄の 20 を使わない）。
- G: v0.78 までの `CoinBonusDamageAndParalyze` は形だけを確かめていて、あやしいおどりの文面も通っていた。v0.79 から、追加の量とマヒを書いた文面（「追加して、」「追加し、」の 2 通り）
  だけを受け付ける（ロケット団のベトベター・サカキのゴーリキー・オムスター（neo2-035）は今までどおり通る）。
- J: v0.78 までの `DamageThenDiscardAllOnTails` は形だけを確かめていて、ファイヤーテールの文面も通っていた。v0.79 から「すべて」とエネルギーの種類を書いた文面だけを受け付ける。
  ファイヤーテールは 1 枚しかなくても決定を出す（K2）。選べるカードがない（ピッピの「ゆびをふる」で使ったなど）なら、トラッシュせず、コインも投げない（与えた 20 は残る。
  `LACKING_SKIP`。p.309）。
- K: 相手に控えがいなければ、コインを投げず何もしない（説明は使うための条件を書かない。v0.38 の「のびるつる」と同じ読み方）。
- L: 「てよい」がないので、選べるカードがあればちょうど 1 枚（0 枚の答えは `INVALID_CHOICE_COUNT`）。選べるカードがない・山札が 0 枚なら、加えずに山札を切る（v0.75 の「もえあがる」と
  同じ読み方。p.309。新しい停止にしない）。「うら」なら山札を見ない・切らない。選べるものとその数は、使ったプレイヤーだけに見える（`SEARCH_DECK` は `HIDDEN_COUNT_KINDS`）。
- M: ポケモンごとに「ワザをうけない」状態・「とうめい」を評価する（2 匹以上の「とうめい」は T27）。カードは持ち主のトラッシュ。自分のカード・エネルギー・進化カード・スタジアム・
  プレイヤーに与えた効果は変えない。トレーナーカードのついている相手のポケモンがいなければコインを投げない。
- N: v0.31 からワザが失敗すると残りの要素を処理しなかった（`run.failed`）。v0.79 で、失敗したあとも処理する要素の印 `Element.after_failure`（既定は偽）を加え、`SelfCannotAttack` の
  `even_if_failed` だけが真にする。効果はコインの結果（ナツメのESPでやり直せばやり直した結果。この要素はコインを投げないので、ESPの再開で 2 度与えない）を採ったあとの 1 回。
  v0.78 の `CannotAttackNextOwnTurn`（はたらく番は与えた番 + 2。期限・ベンチ・進化・きぜつで消える）で、相手のワザとして使ったワザも含めてすべてのワザを止め、「にげる」・トレーナー・
  特殊能力は止めない。ピッピの「ゆびをふる」でメタルクラッシュを使うと、ピッピに与える。v0.78 のエアームド（メタルスラッシュ）・新しいマンタイン（おおなみ）は変えていない。
  ナツメのESPはナツメのポケモンにだけつくので、ハガネールのメタルクラッシュでは起こらない（対戦で確かめていない）。

## 6. 既存の型が受け付ける書き方を加えたもの

意味が同じと確かめた書き方を、登録の値と結びつけて 1 通りずつ加えた（一般の正規化・部分一致はしていない）。

| 型 | 加えた書き方（違い） | カード |
|---|---|---|
| `DamageIgnoringDefenderEffects` | 「抵抗カ」（カタカナの「カ」。写しのまま） | ES2-020・QSG-033 |
| `LockOpponentTrainersNextTurn` | 「次の相手の番が終わるまで」「「トレーナーカード」」 | ES3-022・QSG-028 |
| `SwitchOpponentActive` | 「1匹選び、」 | GD1-005 |
| `HalfRemainingHpDamage`（切り上げ） | 「相手の残りHPの半分(切り上げ)のダメージを与える。」とダメージの目安なし（null）の組 | GD3-012 |
| `HalveDamageNextTurn` | 「次の相手の番で、…うけるダメージは半分(切り捨て)…」・「(ダメージ以外の効果は受ける)」 | PR1-010・neo1-002 |
| `DamageThenRetreatLock` | 「次の相手の番、このワザを受けた相手は…」 | PRN-014・neo3-008 |
| `DamagePlusOwnCountersThenSelfConfuseOnTails` | 「の数×」「自分を「こんらん」状態にする」 | SI-012 |
| `ChooseOpponentPokemonDamage` | 弱点・抵抗力を括弧に入れない | SI-017・neo1-046 |
| `CoinFlipDamageThenSelfConfuse` | 「投げ、」「自分を「こんらん」状態にする」 | neo1-013 |
| `DamageThenCoinBenchDamage` | 「投げて、」の読点 | neo1-029 |
| `DamageThenAttachEnergyFromDiscardToSelf` | 「1枚を選び出し、」 | neo2-012 |
| `CoinsPerAttachedTypeBonusDamage` | 「自分についている」 | neo2-035 |
| `SelfBarrierOnHeads` | 「相手のワザによるダメージや効果」 | neo2-038 |
| `AttachEnergyFromDeckToSelfExactly` | 「エネルギーカードを1枚選び出し」 | neo3-011 |
| `CoinChooseOpponentPokemonDamage` | 「そのポケモンに、」 | neo3-011・neo3-016 |
| `CoinsUntilTailsDamage` | 「投げつづけ、」 | neo3-015 |
| `DamageThenPoisonAndParalyzeOnHeads` | 「「どく」と「マヒ」状態にする」（「両方の」なし） | neo4-071 |
| `DamageThenReduceDamageNextTurn`（コインなし） | 「…受けるダメージは「-10」される（ダメージ以外の効果はそのまま）。」（v0.62 のあながくれと同じ言い回し） | neo4-085 |
| `FailOnTailsDamage`（2 枚） | 「投げて、1枚でも」 | neo4-092 |

境界: neo3-011・neo3-016 は相手の場全体（バトル場・ベンチ）から選ぶ（控えだけの型ではない）。neo1-046・SI-017 は弱点・抵抗力だけを計算しない（サンドのスピードスターは相手の
効果も受けない）。GD3-012 は切り上げ（写しに「?」を足していない）。neo4-085 は 10 ダメージのあるワザ（ダメージのない `ReduceDamageNextTurn` ではない）。neo3-015 は `CoinsUntilTailsDamage`
（コインの枚数を打ち切らない）。数の値は文面の値と照らした（`CoinFlipDamage` の枚数・ダメージなど。違う値は受け付けない）。

## 7. 状態の形と互換性

- 持続する効果の種類 `prevent_attack_damage`（`state.PreventAttackDamage`）を加えた。v0.4b の「ダメージを受けない」（`PreventDamage`。かたまる）は v0.61 からトレーナーのダメージ
  （バトル場は穴だらけ!）も防ぐ（p.235 の解説の記録）が、こうそくいどうの説明は「ワザによるダメージ」と書くので、トレーナーのダメージは防がない（`attack_only`。`effects.trainer_damage`）。
  ワザのダメージの要素を計算の前に無効にすること・ダメージ以外の効果は受けること・消える契機は同じ（部分型）。書き出しの形式は 22 のまま（持続する効果の種類は形式 8 から書ける）。
- 公開の API・コマンド・決定の種類・ログのイベントの種類は変えていない（ログ `discard_energy_failed` の `outcome` に `skip` を加えた）。
- 意図した変化: (1) PK1 で止まる盤面（v0.78 は進む・MH1 で拒否）、(2) B で止めなくなった盤面（最終の量が同じ）、(3) `CoinBonusDamageAndParalyze`・`DamageThenDiscardAllOnTails` の
  文面の確かめ（今の登録はどれも通る。違う文面の新しい登録を拒否する）。v0.78 までの登録・写しの組の結果は変わらない（10 章の比較）。
- カツラのクイズの名前の候補に、新しい名前 12（カポエラー・キマワリ・サニーゴ・チョンチー・ツボツボ・デンリュウ・ブルー・ホウオウ・マグマラシ・マリルリ・ヤドキング・ワタッコ）が
  加わり、候補の並びの位置が変わる。マチスの秘策の試すカードは公開の登録の一覧から作り、上限（512）は変えていない。

## 8. 未解決と技術的な制限

- 新しい未解決の裁定は PK1 だけ（停止コード 166・未解決の裁定 168）。B は既存の問い（DE1・KA1・RB4・EX1・TD1）の範囲を狭めただけで、どれも解決していない。
- エンジンの未対応は加えていない。
- 対戦で確かめていないもの（単体テストで確かめた）は 10 章。

## 9. kyuura への報告事項

- サンド（ES2-020・QSG-033）のスピードスターの説明の「抵抗カ」（カタカナの「カ」。「抵抗力」の転記の誤りと思われる）。写しは直していない。
- ヤドン（neo1-045）・ネイティ（neo1-046）の `ja_text_source` の URL の番号が入れかわっている（neo01-046-yadon・neo01-045-naty。名前とワザは合う。処理に使う欄ではない）。
- マチスのラッタ（GD3-012）のいかりのまえばのダメージの目安が null（第1弾のラッタは「?」）。
- engine_targets.json の `engine_status` は v0.68 の時点の索引で、v0.79 の登録を写すと 52 枚が `registered` になる。

## 10. 検証

どれも最終のコードで行った（テストと文書を直したあとの作業ツリーを写した木で、走らせているあいだは写しを変えていない）。

- 登録を除いた確かめ: v0.79 の登録だけを除いた登録表では、52 枚とも未対応にもどり（891 枚）、ほかのカードの対応は変わらない（tests/test_shared_checks_pokemon_reuse_v0_79.py `RegistrationTest`）。
- A・B の回帰: PK1 で止まる盤面（ベトベトン・カブトの組・特殊状態・鋼エネルギー・メタモンの［へんしん］）と、止める必要のない隣の盤面（悪エネルギーのない場・結果が変わらない場）、
  B の最終の量（DE1・KA1・RB4・EX1・TD1）を単体テストで確かめた。A・B の回帰のテストは v0.78 の木では失敗し、v0.79 では通る。
- 組み合わせの型 11 のテスト・決定・3 つの先読みの方法（`derived`・`derived_full`・`legacy`）の確かめ（同じファイル）。
- `--batch v0.79 --seeds 3`（4 組・24 局）: 24 局とも通常の勝敗で終わり、停止 0・監査の失敗 0。原典で決められない場面で拒否されたワザは `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` 28 回・
  `UNRESOLVED_PREVENTED_COIN_DAMAGE` 1 回、拒否されたにげるは `UNRESOLVED_RETREAT_OVERPAY` 9 回（どれも既存の問い。拒否のあと対戦を続けた）。組み合わせの型 11 はどれも対戦で使われた。
  ワザ 94 のうち 73 を対戦で使い、21（NIP1-013#0・#1、PR1-064#0、neo1-001#1、neo1-007#0・#1、neo1-043#0、neo2-010#1、neo2-012#0・#1、neo2-017#0・#1、neo2-029#0・#1、neo2-035#0・#1、
  neo3-008#1、neo3-011#2、neo3-016#0、neo4-071#0、neo4-089#1）は対戦では使われなかった（単体テストの登録・型の確かめだけ）。勝敗は判断に使わない。
- 固定した v0.78（コミット `513ef66`）と別の木・別のプロセスで比べた（`tools/engine_lockstep.py record --corpus all --seeds 20 --stress-seeds 10`）: 760 対戦・136,537 歩で食い違い 0
  （許した差 0）。
- 前の版の組（`--batch v0.31`・`v0.44`・`v0.47`・`v0.57`・`v0.58`・`v0.61`・`v0.63`・`v0.78`。seed 2）を v0.78 の木と比べた: 結果は同じ（v0.79 の空の集計の欄と、`--batch v0.78` の
  `v078_uses` の新しい欄 `nonattack_zeroed` を除く）。v0.63 のカツラのクイズの結果（正解・不正解の数など）も同じ。
- 検査: `scripts/extract_kyuura_cards.py --check`（写しは 7d3f4ca と一致）・`scripts/check_card_sources.py`（記録 856 件）・`scripts/check_research_links.py --kyuura ../kyuura`
  （研究の基準と一致）・ruff（v0.78 の木と同じ指摘。`effects.py` の型の読み込みの 1 行の内容が変わっただけ）・`tools/run_mutants.py check`（定義 50 がすべて今のコードに入る。
  変異試験そのもの（`witness`・`full`）は走らせていない）。
- テスト一式（`python3 -m unittest`）: 4,650 件・成功（skip 2）。../kyuura・git に依る登録の数のテストは作業ツリーで走らせて成功（77 件・skip なし）。
