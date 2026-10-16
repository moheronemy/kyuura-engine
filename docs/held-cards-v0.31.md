# v0.31: v0.30 で保留した 22 枚の一括実装

v0.30（`43fed61`）の docs/discard-energy-attacks-v0.30.md 4 章で保留した 22 枚を、必要な共通の仕組みをまとめて加えて対応にしました。進化元として
7 枚を加えています。カードデータは 2026-10-15 からの方針（docs/card-data-policy.md）のとおり、kyuura の data/cards.json（写しの元 `ecb2d69`）を
採用し、外部照合は pcg-search.com だけで行いました。公式ガイドブックは読んでいません（キャプチャ・OCR・画像の読み直しはしていない）。

- 作業ブランチ: `claude/v0.31-held-cards`（`claude/v0.30-discard-energy-attacks` の `43fed61` から。`origin/main` の整備（`f50a9ab`。PR #5）は
  `43fed61` にすでに含まれていて、ほかに取り込む後続の整備はなかった）。版は 0.31.0。
- 写しの元（`KYUURA_COMMIT` = `ecb2d69`）と研究の基準（`3f34908`）は変えていません。固定した参照データ（tests/fixtures の参照データ）は作り直していません。
- 公開の固定のデッキ（`kyuura_engine.decks`）は変えていません。

## 1. 結果

| 区分 | 枚数 | 状態 |
|---|---|---|
| 対象（v0.30 で保留した 22 枚） | 22 | 22 枚とも対応（カード全体。すべてのワザ・特殊能力に登録があり、対戦に使える） |
| 依存のために加えたカード（進化元） | 7 | 7 枚とも対応 |
| 残ったカード | 0 | — |

- 対戦に使えるポケモンは 106 枚（v0.30 は 77 枚。写しの組 `pool_v0_31`。写しのカードは 99 → 127 枚（リザードンは v0.30 までも参照カードとして写しにあった）、対戦に使えるカードはトレーナー・エネルギーを合わせて 123 枚）。
- ワザの登録 124 → 176（+52）、特殊能力の登録 9 → 12（+3）。
- 「カード全体を対応」は、そのカードのすべてのワザと特殊能力が登録され（`pool.is_playable`）、進化のカードは系統の進化元も対戦に使えること
  （tests/test_held_cards_v0_31.py の `CardDataTest`）。
- 原典（記録）で決められない場面は、その場面だけを止めます（5 章）。止める場面があっても、カードは対戦に使えます（止める場面では別の操作をする）。

## 2. カードごとの整理と実装

「既存」は v0.30 までの効果の型の登録だけ、「新」は v0.31 で加えた効果の型（3 章の仕組みの組み合わせ）。「止める場面」は 5 章。

### 2.1 対象の 22 枚

| id | カード | 段階（進化元） | ワザ・特殊能力（効果の型） | 止める場面 |
|---|---|---|---|---|
| PMCG1-022 | キュウコン | 1 進化（ロコン PMCG1-015。v0.3c から対応） | かどわかす（`SwitchOpponentActive`・新）・だいもんじ（`DiscardEnergyThenDamage`・既存。RUL-ENERGY-DISCARD-ATTACKS の範囲） | — |
| PMCG1-021 | リザードン | 2 進化（リザード PMCG1-017。v0.30） | ほのおのうず（`DiscardEnergyBeforeDamage`・新）・［エナジーバーン］（`ConvertAttachedEnergy`・新。TXT-CHARIZARD） | HC1・HC10 |
| PMCG1-042 | サンダー | たね | かみなり（`SelfDamageOnTails`・既存）・10まんボルト（`DiscardEnergyBeforeDamage`・新） | HC1 |
| PMCG1-044 | ゴース（第1弾） | たね | さいみんガス（`SleepOnHeadsWithoutDamage`・新）・みちづれ（`DiscardEnergyThenSelfEffect`・新） | HC1・HC2・HC3 |
| PMCG1-050 | ミュウツー | たね | サイコキネシス（`DamagePlusDefenderEnergy`・新）・バリアー（`DiscardEnergyThenSelfEffect`・新） | HC1・HC3 |
| PMCG2-044 | ピクシー | 1 進化（ピッピ。v0.31） | ゆびをふる（`CopyOpponentAttackEffect("cannot_use")`・新）・ちいさくなる（`ReduceDamageNextTurn`・新） | HC9 |
| PMCG3-009 | ファイヤー（化石の秘密） | たね | やまやき（`DiscardFireThenMillOpponent`・新）・ゴッドバード（`FailOnTailsDamage`・新） | HC1・HC5・HC6 |
| PMCG3-027 | ヤドン（化石の秘密） | たね | ぼーっとする（`HealSelfOnHeadsIfDamaged`・新）・ゴミあさり（`DiscardEnergyThenRecoverTrainer`・新） | HC1 |
| PMCG4-014 | わるいギャロップ | 1 進化（第4弾のポニータ PMCG4-013。v0.30） | うしろげり（`DamageOnly`・既存）・ひばしら（`DamageThenOptionalBenchDamage`・新） | — |
| PMCG4-015 | わるいリザード | 1 進化（ヒトカゲ PMCG1-014） | しっぽでたたく（`DamageOnly`）・ファイヤーボール（`FailOnTailsDiscardThenDamage`・新） | — |
| PMCG4-016 | わるいブースター | 1 進化（イーブイ。v0.31） | いかり（`DamagePlusOwnCounters`・新）・ひあそび（`CoinBonusDiscardThenDamage`・新） | — |
| PMCG4-017 | わるいリザードン | 2 進化（わるいリザード） | つめではじく（`DamageOnly`）・れんぞくファイヤーボール（`CoinsPerEnergyDamageThenDiscard`・新） | 8 章（先読みの上限） |
| PMCG4-022 | わるいゴルダック | 1 進化（第4弾のコダック。v0.31） | だい3のめ（`DiscardEnergyThenDraw`・新）・ちょうねんりき（`DamageOnly`） | — |
| PMCG4-028 | わるいマルマイン | 1 進化（第4弾のビリリダマ PMCG4-027。v0.29） | ころがりタックル（`DamageOnly`）・エナジーボム（`DamageThenMoveEnergyToBench`・新。CR-TRANSPARENCY-ENERGY-BOMB） | 8 章（先読みの上限） |
| PMCG5-032 | カスミのゴルダック | 1 進化（カスミのコダック。v0.31） | エクストラビーム（`DamageThenDiscardAllOnTails(None)`・新）・スーパーデストロイ（`CoinDiscardOpponentEnergyEach`・新） | HC3・T27 |
| PMCG5-041 | マチスのエレブー | たね | たいでん（`AttachDiscardEnergyToSelf`・新）・ほうでん（`DiscardAllThenCoinDamage`・新） | HC7 |
| PMCG6-025 | カツラのヒトカゲ | たね | メラメラ（`DamageThenDiscardEachEnergy`・新）・きりさく（`DamageOnly`） | — |
| PMCG6-029 | カツラのリザード | 1 進化（カツラのヒトカゲ） | ほのおのつめ（`DamageOnly`）・やきはらう（`CoinsDiscardThenSpreadDamage`・新） | T27・C34/C35・G40・P19・P32 |
| PMCG6-031 | カツラのブーバー | たね | ひをふく（`CoinBonusDamage`・新）・マグマふんしゅつ（`MillSelfThenDamage`・新） | HC6 |
| PMCG6-033 | カツラのキュウコン | 1 進化（カツラのロコン。v0.31） | しゃくねつ（`DamageThenDiscardAllOnTails(炎)`・新）・［ほのおでかいふく］（`HealOnEnergyAttach`・新） | — |
| PMCG6-034 | カツラのウインディ | 1 進化（カツラのガーディ。v0.31） | ヒートタックル（`DamageAndSelfDamage(10)`・既存）・ほのおのあらし（`DiscardEnergyBeforeDamage`・新。RUL-ENERGY-DISCARD-ATTACKS の範囲の時点） | — |
| PMCG6-041 | マチスのライチュウ | 1 進化（マチスのピカチュウ。v0.31） | バリバリ（`CoinBonusDamageThenDiscardAll`・新）・でんきタックル（`DamageThenParalyzeOrSelfDamage`・新） | — |

### 2.2 依存のために加えたカード（7 枚）

| id | カード | 必要とした対象 | ワザ・特殊能力 |
|---|---|---|---|
| PMCG1-067 | ピッピ（第1弾） | ピクシー | うたう（`SleepOnHeadsWithoutDamage`）・ゆびをふる（`CopyOpponentAttackEffect("follow_text")`。処理に使う文面は kyuura の card_differences の記録） |
| PMCG2-037 | イーブイ | わるいブースター | しっぽをふる（`CannotAttackOnHeads`）・でんこうせっか（`CoinBonusDamage(20)`） |
| PMCG4-019 | コダック（ロケット団） | わるいゴルダック | めまい（`DrawCardsAttack(1)`）・みずでっぽう（`ExtraEnergyDamageMixed`。HC4） |
| PMCG5-021 | カスミのコダック | カスミのゴルダック | ちょうのうりょく（`ThreeCoinPsychicPower`。HC9） |
| PMCG6-026 | カツラのロコン | カツラのキュウコン | しっぽでまどわす（`ConfuseOnHeads`・既存）・［しぜんになおる］（`RemoveOwnCounterOncePerTurn`。HC8） |
| PMCG6-027 | カツラのガーディ | カツラのウインディ | もえひろがる（`DamageAndBenchTypeDamage`） |
| PMCG5-036 | マチスのピカチュウ | マチスのライチュウ | でんこうせっか（`CoinBonusDamage(20)`） |

ほかの進化元（ロコン・ヒトカゲ・リザード・第4弾のポニータ・第4弾のビリリダマ・カツラのヒトカゲ）は v0.30 までに対応しているか、対象の 22 枚に含まれます。
進化元のカードも、すべてのワザ・特殊能力を対応にしました（ワザを 1 つ登録しただけで対応と数えていない）。

## 3. 新設・拡張した共通の仕組み

カードごとの分岐は `engine.py`・`resolution/` に加えていません。新しいワザは、解決の基盤の要素の並び（`resolution/programs.py` の `BUILDERS`）で、
既存の要素（`Damage`・`Status`・`ForceSwitch`・`DiscardOwnEnergy` など）の拡張と新しい要素の組み合わせとして加えました。v0.13 の約束（`resolve`）では
書いていません。v0.30 の `DiscardEnergyThenDamage`（炎 1 枚を選んでトラッシュ → ダメージ）の意味は広げていません（第4弾のポニータのひのこの
「トラッシュできない時、このワザのダメージは0になる」を `when_lacking="zero"` で区別しただけ）。

### 3.1 依頼で区別した点

| 区別 | 実装 |
|---|---|
| 指定枚数をトラッシュ／すべてトラッシュ | `DiscardOwnEnergy.count`（数・None ならすべて（決定なし））・`heads_of`（コインの「おもて」の数）・`any_number`（好きなだけ。0 枚は HC5） |
| カードの枚数／エネルギーの個数 | トラッシュ・コインの数はエネルギーカードの枚数で数える（`attached_basic_energy`）。ワザに必要なエネルギー・多いエネルギー（みずでっぽう）は供給するエネルギー（`state.energy_types`。エナジーバーンで「炎」になったカードを含む） |
| ワザの使用条件／ワザの効果 | `DiscardOwnEnergy.timing`: `effect`（説明がワザの効果・RUL-ENERGY-DISCARD-ATTACKS の範囲。こんらんのコインのあと）／`unresolved`（「はがしてすてる」。こんらんのときだけ HC1）。使用条件の「ダメージカウンターがのってない時には、このワザは使えない」は `usage_problem`（宣言のときに拒否） |
| コイン判定の前／後 | ワザ全体のコイン（`Coin`。ダメージ・トラッシュ・効果の分かれ道）と要素の中のコイン（`local_coin`。その要素だけ）を分ける。れんぞくファイヤーボールはコイン → ダメージ → トラッシュ、ほうでんはトラッシュ → コイン → ダメージ |
| 攻撃側／防御側が選ぶ | `ForceSwitch.chooser`（`"attacker"`: かどわかす／既定: ふきとばしの相手）。相手のエネルギーのトラッシュ・相手のワザの選択もワザを使ったプレイヤー |
| ダメージを防がれた場合にも行う処理 | トラッシュの要素はダメージの要素と別（防がれても、こんらんで「うら」でなければトラッシュする）。`requires`（トラッシュできなかったら、そのあとの要素を処理しない）と、ダメージを与えたかで決まる `after_damage`（v0.17b）を混ぜない |
| 特殊能力とワザ | エナジーバーン・しぜんになおるは宣言する特殊能力（`UsePokemonPower`。ワザの解決の基盤を通らない）、ほのおでかいふくはエネルギーカードをつけたときに自動的にはたらく特殊能力（`after_energy_attached`）。ワザの効果の持続する効果とは別 |

### 3.2 仕組みの一覧

| 仕組み | 置き場所 | 使うワザ・特殊能力 |
|---|---|---|
| トラッシュの要素の拡張（数・すべて・コインの数・好きなだけ・ワザ全体のコイン・要素のコイン・トラッシュできないとき（`LACKING_*`）・時点（`TIMING_*`）） | `programs.DiscardOwnEnergy` | ほのおのうず・10まんボルト・みちづれ・バリアー・やまやき・ゴミあさり・ひばしら以外のトラッシュのワザ |
| ワザの失敗（p.323 の 12。ワザは使ったことになり番は終わる。ログ `attack_failed`） | `programs.FailOnTails`・`AttackRun.fail` | ゴッドバード・ファイヤーボール・やきはらう（トラッシュできないとき） |
| ダメージの量（コインで追加・相手のエネルギーの数・自分のカウンター・トラッシュした数のコイン・山札からトラッシュした炎の数・無色をふくむ多いエネルギー） | `programs.HeadsBonus` ほか | でんこうせっか・ひをふく・サイコキネシス・いかり・ほうでん・マグマふんしゅつ・みずでっぽう |
| 控えポケモンへのダメージ（全員・タイプで限る・選ぶ。「弱点・抵抗力に関係なく」。プラスパワーは変えない） | `programs.BenchDamage`・`OptionalDiscardBenchDamage`・`kernel.deal_damage(OPPONENT_BENCH)` | やきはらう・もえひろがる・ひばしら |
| 相手のエネルギーカードのトラッシュ（ワザを使ったプレイヤーがポケモンごとに選ぶ。「とうめい」・「ワザをうけない」を評価） | `programs.DiscardOpponentEnergy` | メラメラ・スーパーデストロイ |
| カードの移動（トラッシュのトレーナーを手札に・トラッシュのエネルギーを自分に・エネルギーを控えに・山札からトラッシュ・山札から引く） | `programs.RecoverTrainer`・`AttachFromDiscard`・`MoveOwnEnergyToBench`・`MillOwnDeck`・`MillOpponentDeck`・`Draw`、`zones.attach_from_discard`・`discard_from_deck` | ゴミあさり・たいでん・エナジーボム・マグマふんしゅつ・やまやき・だい3のめ・めまい・ちょうのうりょく |
| 持続する効果（次の相手の番）: みちづれ `DestinyBond`・バリアー `AttackBarrier`（ダメージと効果の要素を無効）・ちいさくなる `DamageReduction`（p.321 の 8 段階）・しっぽをふる `CannotAttack`（相手に与える効果。`on_opponent`） | `state`・`persistent`・`programs.SelfPersistent`・`OpponentCannotAttack`・`checks.attack_request`・`flow._destiny_bond` | みちづれ・バリアー・ちいさくなる・しっぽをふる |
| 相手のワザを自分のワザとして使う（選んだワザの要素の並びを同じ枠で処理。弱点・抵抗力はワザを使ったポケモンのタイプ。必要なエネルギーはいらない。条件の扱い `clause`） | `programs.CopyOpponentAttack`・`Element.copy_problem`・`AttackRun.redirect` | ゆびをふる（ピクシー・ピッピ）・ちょうのうりょく |
| 特殊能力: エネルギーのタイプを変える（何度でも。番の終わりにもどる）・自分の番ごとに 1 回（回数を状態に持つ）・エネルギーをつけたとき | `effects.ConvertAttachedEnergy`・`RemoveOwnCounterOncePerTurn`・`HealOnEnergyAttach`・`after_energy_attached`、`GameState.energy_burn`・`power_uses_this_turn` | エナジーバーン・しぜんになおる・ほのおでかいふく |
| ワザの途中の決定の新しい種類 | `decisions.SELECT_ATTACK`・`DISCARD_OPPONENT_ENERGY`・`ATTACH_TO_BENCH`・`RECOVER_TRAINER`・`ATTACH_FROM_DISCARD` | 上のワザ |
| 決定をまたぐ値（ワザ全体のコイン・使っているワザ・「とうめい」の結果・処理した送る効果の数・こんじょうの写し）を決定の `context` で運ぶ | `AttackRun.suspend(carry=...)`・`restore` | 2 つ以上の決定を出すワザ |

決定をまたぐ値は、v0.18d の案 B と同じく既存の `decision.context` に明示的なデータで持ちます（`PendingDecision` に項目を加えていない。書き出しの
形式 9 の決定の形は同じ）。窓の途中の決定（ダメージの要素のあとの窓で決定を出す効果）は加えていません（だつりょくえきは DEFER のまま）。

## 4. 採用した資料と外部照合

- カードデータ: kyuura `data/cards.json`（`ecb2d69`）。`python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura` で写しに 29 枚を加えた（写しの組 `pool_v0_31`）。
- 処理に使う文面: 印刷の文面（kyuura の写し）。ただし次の 3 つは記録の文面（研究の対応表 `latest_descriptions`）。
  - キュウコンの「だいもんじ」: kyuura の RUL-ENERGY-DISCARD-ATTACKS（rule_history.json の errata。確実）の最新の説明。記録の `cards` はウインディだけなので、
    記録の「炎エネルギーカードをトラッシュするタイプのワザ（「かえんほうしゃ」など）は、すべて同じ処理になります。」の範囲として当てはめた（`errata_scope`）。
    印刷の文面はかえんほうしゃと同じ。
  - リザードンの「エナジーバーン」: kyuura の TXT-CHARIZARD（確実。記録の `cards` にリザードンがある）。印刷の文面（「こんらん」のときだけ使えない）は照合だけに使う。
  - ピッピの「ゆびをふる」: kyuura の data/curation/card_differences.json の PMCG1-067 の記録（確度: 確実）が引く最新の説明と、同じ記録の解説「基本的にワザに
    必要なエネルギー以外はワザの説明にしたがいます」（`FOLLOW_TEXT`）。kyuura に LD- の記録はない（研究の対応表の `difference_text`。検査は
    `scripts/check_research_links.py` の 4e・`scripts/check_card_sources.py`）。
- 裁定: わるいマルマインの「エナジーボム」で控えのゴースト（とうめい）の「おもて」ならエネルギーはトラッシュ（kyuura の CR-TRANSPARENCY-ENERGY-BOMB。エンジンの T36）。
  ほのおのあらしのトラッシュの時点は RUL-ENERGY-DISCARD-ATTACKS の範囲（炎エネルギーカードをトラッシュして大きなダメージを与えるワザ）として、ワザの効果。
- 一般の規定は既存の記録の再利用（p.309 のワザの手順と「処理の対象がない内容」、p.321 のダメージの計算の段階、p.322・p.323 の持続する効果とワザの失敗、
  p.257 のプラスパワー（控えポケモンへのダメージはそのまま）・ディフェンダー、p.312 の効果で引く規定）。この版のために誌面を読み直していません。
- 採用の記録: `kyuura_engine/data/card_sources.json` に 29 件（`basis: kyuura_data`・`adopted`。`kyuura_records` はキュウコン・リザードン・わるいマルマインだけ）。
  `card_verification.json`（過去の原典照合）には加えていません。
- pcg-search.com との照合（29 件。2026-10-15。対象の版はサイトの一覧の番号で決めた）: `match` 21 件、`differences` 8 件（キュウコン・サンダー・ピクシー・
  ファイヤー・ヤドン・コダック・カツラのブーバー・カツラのウインディ）。違いはどれも書き方・表記の違いで、処理に影響しません（`affects_behavior: false`）。
  照合できなかったカードはありません。

### 4.1 kyuura への報告事項（kyuura は変更していない）

1. RUL-ENERGY-DISCARD-ATTACKS の `cards` にキュウコン（PMCG1-022）の「だいもんじ」がない（v0.30 のヒトカゲ・リザード・ブーバーと同じ。範囲として当てはめた）。
2. ピッピ（PMCG1-067）の「ゆびをふる」の最新の説明は card_differences にだけあり、LD- の記録がない。
3. pcg-search.com とのワザ名・カード名の表記の違い: ファイヤー（化石の秘密）の「ゴッドバード」（サイトは「ゴットバード」）、カツラのウインディ（サイトの見出しは
   「カツラのウィンディ」）。ほかの違い（サイトの誤記と見られるもの）は採用の記録の `external_checks` にある。
4. HC1〜HC10 は kyuura に論点がない（研究の対応表の `not_in_kyuura`）。T27・C34/C35・G40・P19・P32 は kyuura の未解決の一覧でコードのない行（エンジンが停止コードを
   付けたので `kyuura_index_engine_key` で照らす）。

## 5. 原典（記録）で決められない場面

止めるのは状態を変える前です（宣言の前は `UnsupportedError` で、状態・ログ・乱数は変わらない。答えのときは決定を待ったまま）。宣言の前に止めるものは、
コインの結果によらない（先読みがすべての結果を試す）。成功を仮定するテストはありません（tests/test_held_cards_v0_31_stops.py）。

| id | 停止コード | 場面 | 影響する範囲 |
|---|---|---|---|
| HC1 | `UNRESOLVED_DISCARD_ENERGY_TIMING` | 「はがしてすてる」（トラッシュがワザを使うための条件か効果か、RUL-ENERGY-DISCARD-ATTACKS の未解決の問い（炎以外・大きなダメージでないもの）のとおり決められない）ワザを、こんらん状態で使う（「うら」でトラッシュするかが変わる） | ほのおのうず・10まんボルト・みちづれ・バリアー・やまやき・ゴミあさりを、こんらん状態で使うときだけ。こんらんでなければ、どちらの読み方でも結果は同じ |
| HC2 | `UNRESOLVED_DESTINY_BOND_KNOCKOUT` | みちづれで相手の対戦ポケモンも「きぜつ」するとき、同時のきぜつ（p.324）かが決められず、勝ち負けが決まる（サイドを取りきる・場にポケモンがいなくなる）場合 | その場面だけ（相手のワザの宣言の前）。勝ち負けが決まらなければ両方がサイドを取る。こんじょうの候補もある場合はコードのない問い（今の対応カードでは起こらない） |
| HC3 | `UNRESOLVED_PREVENTED_EFFECT_COIN` | 「ワザをうけない」状態（バリアー）のポケモンへの効果だけを決めるコインを投げるか | バリアーのミュウツーに、うたう・さいみんガス・しっぽをふる・スーパーデストロイ（全員が受けない）を使うとき |
| HC4 | `UNRESOLVED_EXTRA_ENERGY_COLORLESS` | 無色をふくむワザの「ワザに必要なエネルギーよりも多く水エネルギーがついている時」の多いエネルギーの数（無色を水で払うかで変わる） | 第4弾のコダックのみずでっぽうで、読み方で数が変わるとき（多い水がなければ 20 で進む） |
| HC5 | `UNRESOLVED_DISCARD_ANY_NUMBER_ZERO` | 「好きなだけはがしてすてる」で 0 枚を選べるか | やまやきの答えが 0 枚のとき（1 枚以上なら進む） |
| HC6 | `UNRESOLVED_DISCARD_DECK_SHORT` | 山札の上から決まった枚数をトラッシュする効果で、山札が足りない | マグマふんしゅつ（自分の山札 5 枚未満）、やまやき（相手の山札 0 枚・選んだ枚数より少ない） |
| HC7 | `UNRESOLVED_ATTACH_FROM_DISCARD_ZERO` | 「最大2枚を取り出して」で、トラッシュに雷があるときに 0 枚を選べるか | たいでんの答えが 0 枚のとき |
| HC8 | `UNRESOLVED_POWER_HEAL_WITHOUT_DAMAGE` | ダメージカウンターがのっていないときに、しぜんになおるを使えるか（番ごとに 1 回を使ったことになるか） | その使用だけ |
| HC9 | `UNRESOLVED_COPIED_ATTACK` | 相手のワザを自分のワザとして使うとき、使うワザの条件の扱いが決められない（例: ピクシーと、トラッシュが「ほかに必要な条件」にあたるか決められないワザ。カスミのコダックと「はがしてすてる」ワザ） | そのワザを選んだとき（選べるが止まる）。選べるワザがすべてそうなら宣言の前 |
| HC10 | `UNRESOLVED_ENERGY_BURN_TRANSFER` | エナジーバーンで「炎」になった草エネルギーカードを、エナジートランス（「草」エネルギーをつけかえる）でつけかえられるか | その使用だけ |
| T27 | `UNRESOLVED_TRANSPARENCY_COIN_ORDER` | 1 つのワザで 2 匹以上の「とうめい」のポケモンがダメージ・効果を受ける（コインの順番） | やきはらう・スーパーデストロイなどで相手の場に 2 匹以上の化石の秘密のゴーストがいるとき |
| C34/C35 | `UNRESOLVED_MULTIPLE_DAMAGE_TRIGGERS` | 1 つのワザで「ダメージを受けたとき」の効果が 2 つ以上はたらく | やきはらうで相手の場に 2 匹以上のカイリキー（はんげき）などがいるとき |
| G40 | `UNRESOLVED_KO_PREVENTION_ORDER` | きぜつするときに使える特殊能力（こんじょう）の候補が 2 つ以上 | やきはらうで 2 匹以上のサカキのカイリキーが同時に HP 以上になるとき |
| P32 | `UNRESOLVED_POST_KNOCKOUT_POWERS_ORDER` | きぜつしたときに使える特殊能力（ふしちょう）の候補が 2 つ以上 | やきはらうで 2 匹以上の R団のファイヤーがきぜつするとき |
| P19 | `UNRESOLVED_PHOENIX_GAS_SOURCE_KNOCKOUT` | かがくへんかガスの発生源が、ふしちょうのポケモンといっしょにきぜつする | やきはらうでベトベトンと R団のファイヤーがいっしょにきぜつするとき |

T27・C34/C35・G40・P19・P32 は v0.30 まで「今の対応カードでは起こらない」コードのない問いで、起こったら `RuntimeError` にしていました。控えポケモン・
複数のポケモンにダメージ・効果を与えるワザで起こるようになったので、問いの表（`questions.QUESTIONS`）にコードを付けました（裁定の分類・kyuura の論点は変えていない）。
エンジンが止める `UNRESOLVED_…` は 22 → 37 件、未解決の裁定は 28 → 38 件（研究の対応表の `counts`）。

ルールの問いではないエンジンの未対応として、`UNSUPPORTED_COPIED_ATTACK`（番をまたぐ効果をワザを使ったポケモンに与えるワザ（ほのおのかべ・こうらがえし・
つるぎのまい）は、相手のワザとして使えない。効果の型・不変条件が「効果を与えたカードのワザ」を前提にしているため）を加えました。研究の対応表の停止コードには入れていません。

## 6. 状態・公開 API・ログ・書き出しの変更と互換性

| 変更 | 内容 | 互換性 |
|---|---|---|
| 書き出しの形式 10 | 形式 9 に `power_uses_this_turn`（[場のポケモンの番号, 特殊能力の位置]）と `energy_burn`（[場のポケモンの番号, エネルギーカードの uid]）を加えた | 形式 1〜9 は、どちらも空なら今までどおり書き出せる。空でなければ `ValueError`（黙って落とさない）。ログの監査の `LATEST_FORMAT` は 10 |
| `GameState` | `power_uses_this_turn`・`energy_burn`（どちらもタプル。番の最初・番の終わりに空）、`energy_types`・`energy_type_of`（エナジーバーンを数えたエネルギーのタイプ） | 不変条件 `engine._turn_power_problems` が今の番のログと照らす |
| 持続する効果の型 | `DestinyBond`・`AttackBarrier`・`DamageReduction`・`CannotAttack` を加え、既存の型に `on_opponent`（クラスの値）を加えた | 既存の効果の書き出し・ログは同じ。形式 1〜7 は今までどおり持続する効果があると `ValueError` |
| 決定の種類 | `select_attack`・`discard_opponent_energy`・`attach_to_bench`・`recover_trainer`・`attach_from_discard` | 段階・再開先（`attack`）・コマンドは増やしていない |
| ログのイベント | `attack_failed`・`discard_energy_failed`・`discard_attached_energy`・`attack_heal`・`recover_trainer`・`attach_energy_from_discard`・`attack_attach_energy`・`discard_from_deck`・`copy_attack`・`effect_prevented`・`effect_skipped`・`destiny_bond`・`energy_burn`・`power_heal`。`discard_energy` に `reason`（`no_bench`・`evaded`）、`damage` に `ignore_weakness_resistance`・`target`（控え）を加えた | 既存のイベントの形は同じ。ログの監査（tests/log_audit.py）がどれも組み立て直す |
| 公開 API | 変えていない（`apply_command`・コマンドの型・`state_to_dict` の呼び方） | — |
| 研究の対応表 | 停止コード 15 件、`latest_descriptions` の `adopted_printed_text` +45・`errata_text` +2・`difference_text`（新しい区分）、コードのない問い `destiny_bond_with_ko_prevention` | `scripts/check_research_links.py`・`scripts/check_card_sources.py` を新しい区分に合わせた |

## 7. 既存カードへの影響

- リザードン（PMCG1-021）は v0.7 から「実装を登録していないポケモンパワーとワザを持つ 2 進化」の参照カードでした。対応にしたので、その性質を確かめるテストは、
  リザードンの登録だけを除いた登録表（tests/helpers.py の `NO_CHARIZARD_EFFECTS`・`no_charizard_pool`）を使います（製品の登録表は変えない）。
- 第4弾のポニータのひのこは、v0.30 でトラッシュできない場合を「起こらない」としていましたが、相手のワザとして使われると起こるので、印刷の文面のとおりダメージを
  0 にします（`DiscardEnergyThenDamage.when_lacking="zero"`。RUL の記録の文面のワザは今までどおり「なくなる」）。
- じこさいせい（v0.7）のトラッシュの要素は v0.30 と同じ（`DiscardOwnEnergy` の既定の値）。
- 既存のテストの期待を変えたもの（古い前提になった理由）: 登録の数と一覧（ワザ 176・特殊能力 12・説明文のあるワザ・宣言しない特殊能力・相手に効果を与える型）、
  停止コードの一覧、こんらんの 20 が 40 になるポケモン（ミュウツー・化石の秘密のヤドンも弱点 超）、T19b で止まるワザ（しっぽでまどわす）、`FrameState` の項目
  （`fired`）、コードのない問いだった 5 件が停止コードになったこと（v0.9〜v0.13 のテストで `RuntimeError` を期待していたもの）、書き出しの最新の形式（10）。
  どれも、確かめる性質（登録表と実装の対応・止める場面・形式の互換）は変えていません。
- 変異試験の定義のうち 2 つ（M17・R12）は、変えた関数の名前（`knocked(res)`・`gone`）に合わせ、同じ誤りを今のコードに入れるように直しました。

## 8. 残った制限

- 先読みの上限（`preflight.MAX_BRANCHES` 4,096）: 決定の答えの組み合わせ・コインが多いワザは、ついているエネルギーが多いと試す結果の数が上限を超え、
  `UNSUPPORTED_PREFLIGHT_LIMIT` で拒否します（v0.17 からの型は v0.13 の止める関数で確かめないので、今までの方針どおり）。れんぞくファイヤーボールは炎 8 枚以上、
  エナジーボムはエネルギー 13 枚以上（控え 2 匹）・8 枚以上（控え 3 匹）・6 枚以上（控え 5 匹）、ほうでん・やまやきは 13 枚以上。対戦の道具はこの場面を
  場から確かめて別の操作を続けます（`V031_STOPS`）。
- 相手のワザとして使えないワザ（`UNSUPPORTED_COPIED_ATTACK`。5 章）。
- ほのおでかいふくは、解決の基盤の窓（ワザ・きぜつ・番の終わり）の外（エネルギーカードをつけたとき）ではたらくので、効果の定義の対応表（`resolution/catalog.py`）に
  入れていません（`after_energy_attached` だけで評価する）。
- 窓の途中の決定は加えていません（v0.18d の DEFER のまま）。

## 9. 検証

### 9.1 テスト

| テスト | 確かめたこと |
|---|---|
| tests/test_held_cards_v0_31.py | 22 枚が v0.30 の文書 4 章と同じ、29 枚の対応・登録と写し・採用の記録と外部照合・進化の系統と通常の進化、すべてのワザ（52）を 1 回以上（先読みの 3 つの方法で結果・乱数が同じ） |
| tests/test_held_cards_v0_31_mechanisms.py | 新しい決定の持ち主・選べるもの・数・不正な答えと原子性、選んだ順によらないトラッシュ、コインとトラッシュの順番、カードの総数、持続する効果（はたらく番・期限・突風・いれかえ）、プラスパワー・ディフェンダー・弱点抵抗力・8 段階、こんらんとトラッシュの時点、特殊能力 3 つ、相手のワザの選び方・弱点・決定、形式 10、52 のワザ × 相手 4 × こんらん 2 × コイン 3 の先読みの方法の一致（1,248 盤面） |
| tests/test_held_cards_v0_31_stops.py | 停止コード 15 と `UNSUPPORTED_COPIED_ATTACK` の止まる場合と隣の止まらない場合（コインの結果・先読みの方法によらない。状態・ログ・乱数が変わらない） |
| tests/test_held_cards_v0_31_games.py | 正式な開始からの 48 局（9.2） |

### 9.2 正式な開始からの対戦

検証用デッキ `R31`・`K31`・`E31`・`P31`（tools/existing_effect_games.py）を 4 組（`R31-K31`・`E31-P31`・`R31-P31`・`K31-E31`）に分け、席を入れかえて seed 0〜5
（48 局。最初の 6 つの seed）。`python3 tools/existing_effect_games.py --batch v0.31 --seeds 6`。

- 48 局とも通常の勝敗で終わり、やり直し・不変条件・ログの監査・書き出しの監査・決定の持ち主の確かめが通った（監査の失敗 0）。
- 止まったワザは、原典で決められない場面（HC4 11 回・HC9 5 回・HC6 1 回・HC2 1 回）と、v0.30 までのこんらんの 20 の変更効果 2 回だけで、どれも場から止まるのが
  正しいことを確かめてから続けた。
- 手順は v0.26 から変えていない手順に、v0.31 のワザの決定への答え・特殊能力の使用・「エネルギーをためるために番を終える」（使えるワザをどれも 2 回以上使い、
  まだ使っていないワザが必要なエネルギーの不足で使えないとき）を重ねたもの。v0.31 のカードのいない v0.28〜v0.30 の組の結果は変わらない。勝敗・カードの強さ・
  デッキの釣り合いは評価していません。

### 9.3 カード・ワザ・特殊能力ごとの確認

「対戦で使用」は 9.2 の 48 局の回数と局数（こんらんの「うら」で 20 になった宣言も数える）。「未確認」はありません。

| id | カード | ワザ・特殊能力 | 単体テストで確認 | 対戦で使用（48 局の回数・局数） |
|---|---|---|---|---|
| PMCG1-022 | キュウコン | かどわかす | 確認（AttackTest.test_ninetales） | 使用（14 回・7 局） |
| PMCG1-022 | キュウコン | だいもんじ | 確認（AttackTest.test_ninetales） | 使用（8 回・4 局） |
| PMCG1-021 | リザードン | ほのおのうず | 確認（AttackTest.test_charizard_fire_spin） | 使用（2 回・2 局） |
| PMCG1-021 | リザードン | ［エナジーバーン］ | 確認（PowerTest.test_energy_burn・test_hc10） | 使用（16 回・4 局） |
| PMCG1-042 | サンダー | かみなり | 確認（AttackTest.test_zapdos） | 使用（2 回・1 局） |
| PMCG1-042 | サンダー | 10まんボルト | 確認（AttackTest.test_zapdos） | 使用（2 回・1 局） |
| PMCG1-044 | ゴース | さいみんガス | 確認（AttackTest.test_base_gastly） | 使用（49 回・12 局） |
| PMCG1-044 | ゴース | みちづれ | 確認（AttackTest.test_base_gastly） | 使用（45 回・9 局） |
| PMCG1-050 | ミュウツー | サイコキネシス | 確認（AttackTest.test_mewtwo） | 使用（14 回・6 局） |
| PMCG1-050 | ミュウツー | バリアー | 確認（AttackTest.test_mewtwo） | 使用（5 回・3 局） |
| PMCG2-044 | ピクシー | ゆびをふる | 確認（AttackTest.test_clefable_and_clefairy_metronome） | 使用（61 回・13 局） |
| PMCG2-044 | ピクシー | ちいさくなる | 確認（AttackTest.test_clefable_and_clefairy_metronome） | 使用（52 回・11 局） |
| PMCG3-009 | ファイヤー | やまやき | 確認（AttackTest.test_moltres） | 使用（36 回・16 局） |
| PMCG3-009 | ファイヤー | ゴッドバード | 確認（AttackTest.test_moltres） | 使用（10 回・2 局） |
| PMCG3-027 | ヤドン | ぼーっとする | 確認（AttackTest.test_slowpoke） | 使用（20 回・12 局） |
| PMCG3-027 | ヤドン | ゴミあさり | 確認（AttackTest.test_slowpoke） | 使用（24 回・13 局） |
| PMCG4-014 | わるいギャロップ | うしろげり | 確認（AttackTest.test_dark_rapidash） | 使用（15 回・6 局） |
| PMCG4-014 | わるいギャロップ | ひばしら | 確認（AttackTest.test_dark_rapidash） | 使用（17 回・6 局） |
| PMCG4-015 | わるいリザード | しっぽでたたく | 確認（AttackTest.test_dark_charmeleon） | 使用（8 回・2 局） |
| PMCG4-015 | わるいリザード | ファイヤーボール | 確認（AttackTest.test_dark_charmeleon） | 使用（10 回・2 局） |
| PMCG4-016 | わるいブースター | いかり | 確認（AttackTest.test_dark_flareon） | 使用（15 回・8 局） |
| PMCG4-016 | わるいブースター | ひあそび | 確認（AttackTest.test_dark_flareon） | 使用（11 回・5 局） |
| PMCG4-017 | わるいリザードン | つめではじく | 確認（AttackTest.test_dark_charizard） | 使用（24 回・6 局） |
| PMCG4-017 | わるいリザードン | れんぞくファイヤーボール | 確認（AttackTest.test_dark_charizard） | 使用（7 回・3 局） |
| PMCG4-022 | わるいゴルダック | だい3のめ | 確認（AttackTest.test_dark_golduck） | 使用（19 回・8 局） |
| PMCG4-022 | わるいゴルダック | ちょうねんりき | 確認（AttackTest.test_dark_golduck） | 使用（17 回・5 局） |
| PMCG4-028 | わるいマルマイン | ころがりタックル | 確認（AttackTest.test_dark_electrode） | 使用（25 回・8 局） |
| PMCG4-028 | わるいマルマイン | エナジーボム | 確認（AttackTest.test_dark_electrode） | 使用（5 回・4 局） |
| PMCG5-032 | カスミのゴルダック | エクストラビーム | 確認（AttackTest.test_mistys_golduck） | 使用（41 回・11 局） |
| PMCG5-032 | カスミのゴルダック | スーパーデストロイ | 確認（AttackTest.test_mistys_golduck） | 使用（33 回・9 局） |
| PMCG5-041 | マチスのエレブー | たいでん | 確認（AttackTest.test_lt_surges_electabuzz） | 使用（18 回・9 局） |
| PMCG5-041 | マチスのエレブー | ほうでん | 確認（AttackTest.test_lt_surges_electabuzz） | 使用（25 回・10 局） |
| PMCG6-025 | カツラのヒトカゲ | メラメラ | 確認（AttackTest.test_blaines_charmander） | 使用（12 回・5 局） |
| PMCG6-025 | カツラのヒトカゲ | きりさく | 確認（AttackTest.test_blaines_charmander） | 使用（8 回・1 局） |
| PMCG6-029 | カツラのリザード | ほのおのつめ | 確認（AttackTest.test_blaines_charmeleon） | 使用（30 回・9 局） |
| PMCG6-029 | カツラのリザード | やきはらう | 確認（AttackTest.test_blaines_charmeleon） | 使用（20 回・7 局） |
| PMCG6-031 | カツラのブーバー | ひをふく | 確認（AttackTest.test_blaines_magmar） | 使用（43 回・16 局） |
| PMCG6-031 | カツラのブーバー | マグマふんしゅつ | 確認（AttackTest.test_blaines_magmar） | 使用（37 回・12 局） |
| PMCG6-033 | カツラのキュウコン | しゃくねつ | 確認（AttackTest.test_blaines_ninetales_attack） | 使用（28 回・10 局） |
| PMCG6-033 | カツラのキュウコン | ［ほのおでかいふく］ | 確認（PowerTest.test_fire_recovery_on_attach） | 使用（17 回・7 局） |
| PMCG6-034 | カツラのウインディ | ヒートタックル | 確認（AttackTest.test_blaines_arcanine） | 使用（21 回・11 局） |
| PMCG6-034 | カツラのウインディ | ほのおのあらし | 確認（AttackTest.test_blaines_arcanine） | 使用（10 回・5 局） |
| PMCG6-041 | マチスのライチュウ | バリバリ | 確認（AttackTest.test_lt_surges_raichu） | 使用（5 回・4 局） |
| PMCG6-041 | マチスのライチュウ | でんきタックル | 確認（AttackTest.test_lt_surges_raichu） | 使用（4 回・2 局） |
| PMCG1-067 | ピッピ | うたう | 確認（AttackTest.test_clefable_and_clefairy_metronome） | 使用（13 回・7 局） |
| PMCG1-067 | ピッピ | ゆびをふる | 確認（AttackTest.test_clefable_and_clefairy_metronome） | 使用（4 回・3 局） |
| PMCG2-037 | イーブイ | しっぽをふる | 確認（AttackTest.test_eevee_tail_wag） | 使用（28 回・11 局） |
| PMCG2-037 | イーブイ | でんこうせっか | 確認（AttackTest.test_lt_surges_pikachu_and_eevee_quick_attack） | 使用（17 回・5 局） |
| PMCG4-019 | コダック | めまい | 確認（AttackTest.test_psyduck） | 使用（14 回・7 局） |
| PMCG4-019 | コダック | みずでっぽう | 確認（AttackTest.test_psyduck） | 使用（10 回・8 局） |
| PMCG5-021 | カスミのコダック | ちょうのうりょく | 確認（AttackTest.test_mistys_psyduck） | 使用（42 回・9 局） |
| PMCG6-026 | カツラのロコン | しっぽでまどわす | 確認（AttackTest.test_blaines_vulpix_and_growlithe） | 使用（36 回・5 局） |
| PMCG6-026 | カツラのロコン | ［しぜんになおる］ | 確認（PowerTest.test_natural_cure_once_per_turn・test_hc8） | 使用（15 回・7 局） |
| PMCG6-027 | カツラのガーディ | もえひろがる | 確認（AttackTest.test_blaines_vulpix_and_growlithe） | 使用（14 回・7 局） |
| PMCG5-036 | マチスのピカチュウ | でんこうせっか | 確認（AttackTest.test_lt_surges_pikachu_and_eevee_quick_attack） | 使用（7 回・3 局） |

### 9.4 固定した v0.30 との比較と、既存の検査

共通の処理（解決の基盤の要素・持続する効果・きぜつの判定・決定をまたぐ値・ダメージの計算の 8 段階・エネルギーをつけたあとの処理）を変えたので、固定した v0.30 の木
（`43fed61`。`tools/engine_lockstep.py tree`）と、別のプロセスで 1 歩ごとに比べました（`record`・`compare`。公開の API だけ。v0.31 のカードは使わない対戦）。

| 比較 | 結果 |
|---|---|
| v0.30 と同じ大きさ（`--corpus all --seeds 10 --stress-seeds 2 --save-every 7`） | 290 対戦・48,092 歩で、食い違い 0・許した差 0・内部の誤り 0（作業の途中のコードと最終のコードの 2 回） |
| 変えた共通の処理を多く通る組（`--modules test_alakazam_games_v0_7,test_butterfree_games_v0_4d,test_moltres_games_v0_12,test_dark_wartortle_games_v0_13,test_harden_games_v0_4b,test_haunter_games_v0_9,test_machamp_games_v0_10 --scenarios alakazam,alakazam_mixed,butterfree,moltres_mixed,wartortle_mixed,harden,haunter_muk,machamp_mixed,giovanni_mixed --seeds 20 --stress-seeds 10 --save-every 7`。じこさいせいのトラッシュの要素・ふきとばしの入れ替え・ほのおのかべ・こうらがえし・かたまる・とうめい・はんげき・こんじょう） | 230 対戦・42,880 歩で、食い違い 0・許した差 0・内部の誤り 0 |

| 確かめたこと（最終のコード） | 結果 |
|---|---|
| `python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura --check` | 「kyuura ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691 と一致しています」 |
| `python3 scripts/check_card_sources.py` | 「カードデータの採用と外部照合の記録は方針と合っています（記録 48 件）」 |
| `python3 scripts/check_research_links.py --kyuura ../kyuura` | 「研究の対応表は kyuura 3f349085645f47d0649a6cacece3680caeae50bf の記録と一致しています」 |
| `ruff check --select F,E9 .` | 指摘なし |
| `python3 tools/run_mutants.py check` | 50 の変異の定義がどれも今のコードに入る（ok 50。M17・R12 は変えた関数の名前に合わせて直した） |
| `python3 tools/existing_effect_games.py --batch v0.31 --seeds 6` | 48 局、通常の勝敗 48・監査の失敗 0（9.2） |
| `python3 -m unittest`（すべて） | Python 3.13.16 で 2,314 件、成功、スキップ 1 件（tests.test_cross_version_compatibility の `FullComparisonTest.test_no_differences`。`KYUURA_COMPAT_BASE` を設定したときだけ走る C 段階の比較）、失敗 0。8 分 1 秒 |

### 9.5 実行していない検証

変異試験の全体（`tools/run_mutants.py full`）・性能の測定・複数の Python での反復は走らせていません（依頼の範囲で具体的な必要がなかった）。変異の定義が今の
コードに入ることは `python3 tools/run_mutants.py check` で確かめました。
