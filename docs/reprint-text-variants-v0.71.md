# v0.71: 拡張パック以外の商品の再録 78 枚（効果の文面の違い）

拡張パック以外の商品（ポケモンジム・クイックスターターギフト・イントロパック・イントロパック★neo・プロモ）の再録のカード 78 枚（トレーナー 67 枚・ポケモン 11 枚）を、
kyuura データの採用で、どのトレーナーも、どのワザ・特殊能力も登録して対応にしました。目的は対応するカードを増やすことで、カードの強さ・勝率・デッキの釣り合いは評価していません。

- 基準: v0.70（`163314670996d69900578085af3fc617e3a84305`）。作業ブランチ `claude/v0.71-reprint-text-variants`（v0.70 から作った）。開始時に `main`（`1b890ee`）は v0.70 の祖先で、
  `main`・`claude/cool-ptolemy-5vtgsg` に v0.70 のあとの差分はありませんでした。未コミットの変更もありませんでした。
- カードの写しの元・研究の基準は、どちらも kyuura `7d3f4ca76c084774efb4ac6a1d3a943387e183c3` のまま。kyuura は変えていません。
- ルールの基準（2000.02.14 版）・公開の固定のデッキ・固定の参照データ・書き出しの形式（22）は変えていません。既存の `UNRESOLVED_…` の分類は変えていません。
- 公式ガイドブックのキャプチャ・OCR・読み直しはしていません。英語版の文面・現行のルール・後年の裁定で補っていません。

## 1. 数

登録から数え直した値です（tests/test_reprint_text_variants_v0_71.py の `TargetTest.test_counts_from_the_registry`）。

| | v0.70 | v0.71 |
|---|---|---|
| 写し・対応するカード | 635・635 | 713・713（kyuura の data/cards.json は 1,377 件） |
| 対応ポケモン・トレーナー・エネルギー | 492・113・30 | 503・180・30 |
| ワザ・特殊能力・トレーナー・特殊エネルギーの登録 | 825・68・113・12 | 840・74・180・12 |
| 書き出しの形式 | 22 | 22 |
| エンジンが止める `UNRESOLVED_…`・未解決の裁定 | 149・151 | 149・151（新しい問いはない） |

78 枚は、文面と処理が同じものをまとめると 45 種類です（8 章）。新しい効果の型は 2 つです（5 章・6 章）。

## 2. 78 枚と元のカード

写しの組は `pool_v0_71`（scripts/extract_kyuura_cards.py の `POOL_V0_71`。並びは依頼の並び）。78 枚とも kyuura data/engine_targets.json（7d3f4ca）の `engine_status` が
`reuse_candidate` で、`nearest_registered` が依頼の元のカードとちょうど同じです（写しの `reprint_targets` に写した。索引で、処理が同じことの証拠ではない）。v0.70 までの 635 枚と
重なりません。同じカードの組（`same_card_group`）は元のカードと同じです（`same_card_groups.json`・docs/cards/reprints.md と同じく索引で、処理が同じことの証拠にはしていない）。

**日本語のゲーム用データの差**: 78 枚とも、元のカードとの違いは効果の文面（トレーナーの文面・ワザと特殊能力の説明文）と、ポケモン図鑑の名前の空白 1 つ（GD1-022・GD5-023 の
「ポケモン図鑑HANDY505」と PMCG1-082 の「ポケモン図鑑 HANDY505」）だけでした。HP・タイプ・弱点・抵抗力・にげる・段階・進化元・ワザの名前と必要なエネルギーとダメージの目安・
特殊能力の名前と種類・トレーナーの種類は同じです（`TargetTest.test_only_effect_text_and_the_pokedex_space_differ`。scripts/check_card_sources.py の `text_free_view` で比べる）。
ナツメのスリーパー（GD6-010）のふりこののろいのダメージは、kyuura が台帳で「20」→「20×」と直した値（`FIX-GD6-010-ATK1-DAMAGE`。kyuura の前の作業の pcg-search.com の画像の判定。
2 章の終わり）で、元のカード（PMCG6-051）と同じです。

| id | 名前 | 商品 | 元のカード | 登録（型） | 処理に使う文面 | 元のカードの照合の記録の収録の一覧 |
|---|---|---|---|---|---|---|
| id | 名前 | 商品 | 元のカード | 登録（型） | 処理に使う文面 | 元のカードの照合の記録の収録の一覧 |
|---|---|---|---|---|---|---|
| GD1-006 | タケシのイシツブテ | ポケモンジム第1弾「ニビシティジム タケシ」 | PMCG5-047 | attack/0 `PutOwnerBasicFromDeckOntoBenchOnHeads`<br>attack/1 `DamageIgnoringResistance` | attack/0: この版の印刷の文面<br>attack/1: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD1-014 | エネルギー回収 | ポケモンジム第1弾「ニビシティジム タケシ」 | PMCG1-076 | trainer `DiscardFromHandThenRetrieveEnergy` | trainer: 元のカードの登録の文面（P43 p.257） | ポケモンジム第1弾タケシ |
| GD1-016 | きずぐすり | ポケモンジム第1弾「ニビシティジム タケシ」 | PMCG1-071 | trainer `RemoveDamageCounters` | trainer: 元のカードの登録の文面（P43 p.254） | ポケモンジム第1弾タケシ |
| GD1-017 | 元気のかけら | ポケモンジム第1弾「ニビシティジム タケシ」 | PMCG1-078 | trainer `BenchBasicFromOwnDiscardThenCounters`（処理が違う） | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD1-018 | タケシ | ポケモンジム第1弾「ニビシティジム タケシ」 | PMCG5-089 | trainer `HealEachDamagedPokemonTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD1-020 | なんでもなおし | ポケモンジム第1弾「ニビシティジム タケシ」 | PMCG1-080 | trainer `CureSpecialConditionsTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD1-021 | ポケモンいれかえ | ポケモンジム第1弾「ニビシティジム タケシ」 | PMCG1-073 | trainer `SwitchWithBench` | trainer: 元のカードの登録の文面（P43 p.254） | ポケモンジム第1弾タケシ |
| GD1-022 | ポケモン図鑑HANDY505 | ポケモンジム第1弾「ニビシティジム タケシ」 | PMCG1-082 | trainer `ArrangeOwnDeckTopTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD1-023 | ポケモンセンター | ポケモンジム第1弾「ニビシティジム タケシ」 | PMCG1-083 | trainer `HealEachDamagedPokemonTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD1-024 | ニビシティジム | ポケモンジム第1弾「ニビシティジム タケシ」 | PMCG5-079 | trainer `IgnoreResistanceForOwnerStadium` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD2-019 | きずぐすり | ポケモンジム第1弾「ハナダシティジム カスミ」 | PMCG1-071 | trainer `RemoveDamageCounters` | trainer: 元のカードの登録の文面（P43 p.254） | ポケモンジム第1弾カスミ |
| GD2-020 | ディフェンダー | ポケモンジム第1弾「ハナダシティジム カスミ」 | PMCG1-079 | trainer `AttachedDamageReduction` | trainer: 元のカードの登録の文面（P43 p.257） | ポケモンジム第1弾カスミ |
| GD2-021 | 突風 | ポケモンジム第1弾「ハナダシティジム カスミ」 | PMCG1-072 | trainer `SwitchOpponentWithBench` | trainer: 元のカードの登録の文面（P43 p.255） | ポケモンジム第1弾カスミ |
| GD2-022 | モンスターボール | ポケモンジム第1弾「ハナダシティジム カスミ」 | PMCG2-048 | trainer `SearchDeckTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD2-023 | ハナダシティジム | ポケモンジム第1弾「ハナダシティジム カスミ」 | PMCG5-080 | trainer `OwnerRetreatReductionStadium` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD3-014 | いいきずぐすり | ポケモンジム第2弾「クチバシティジム マチス」 | PMCG1-075 | trainer `DiscardEnergyThenHealTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD3-017 | ディフェンダー | ポケモンジム第2弾「クチバシティジム マチス」 | PMCG1-079 | trainer `AttachedDamageReduction` | trainer: 元のカードの登録の文面（P43 p.257） | ポケモンジム第2弾マチス |
| GD3-018 | 突風 | ポケモンジム第2弾「クチバシティジム マチス」 | PMCG1-072 | trainer `SwitchOpponentWithBench` | trainer: 元のカードの登録の文面（P43 p.255） | ポケモンジム第2弾マチス |
| GD3-019 | なんでもなおし | ポケモンジム第2弾「クチバシティジム マチス」 | PMCG1-080 | trainer `CureSpecialConditionsTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD3-020 | ポケモンいれかえ | ポケモンジム第2弾「クチバシティジム マチス」 | PMCG1-073 | trainer `SwitchWithBench` | trainer: 元のカードの登録の文面（P43 p.254） | ポケモンジム第2弾マチス |
| GD3-023 | モンスターボール | ポケモンジム第2弾「クチバシティジム マチス」 | PMCG2-048 | trainer `SearchDeckTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD3-024 | クチバシティジム | ポケモンジム第2弾「クチバシティジム マチス」 | PMCG5-076 | trainer `AttackCoinStadium` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD4-004 | エリカのラフレシア | ポケモンジム第2弾「タマムシシティジム エリカ」 | PMCG5-014 | attack/0 `DamageAndDrain`<br>power/0 `ConfuseDamageSourceOnHeads` | attack/0: この版の印刷の文面<br>power/0: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD4-014 | エネルギー回収 | ポケモンジム第2弾「タマムシシティジム エリカ」 | PMCG1-076 | trainer `DiscardFromHandThenRetrieveEnergy` | trainer: 元のカードの登録の文面（P43 p.257） | ポケモンジム第2弾エリカ |
| GD4-015 | エネルギー転送 | ポケモンジム第2弾「タマムシシティジム エリカ」 | PMCG3-044 | trainer `SearchDeckTrainer`（処理が違う） | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD4-019 | お上品攻撃 | ポケモンジム第2弾「タマムシシティジム エリカ」 | PMCG5-074 | trainer `ReduceAttackDamageAsWished` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD4-020 | きずぐすり | ポケモンジム第2弾「タマムシシティジム エリカ」 | PMCG1-071 | trainer `RemoveDamageCounters` | trainer: 元のカードの登録の文面（P43 p.254） | ポケモンジム第2弾エリカ |
| GD4-021 | ディフェンダー | ポケモンジム第2弾「タマムシシティジム エリカ」 | PMCG1-079 | trainer `AttachedDamageReduction` | trainer: 元のカードの登録の文面（P43 p.257） | ポケモンジム第2弾エリカ |
| GD4-022 | なんでもなおし | ポケモンジム第2弾「タマムシシティジム エリカ」 | PMCG1-080 | trainer `CureSpecialConditionsTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD4-023 | プラスパワー | ポケモンジム第2弾「タマムシシティジム エリカ」 | PMCG1-081 | trainer `AttachedAttackBonus` | trainer: 元のカードの登録の文面（P43 p.257） | ポケモンジム第2弾エリカ |
| GD4-024 | ポケモンいれかえ | ポケモンジム第2弾「タマムシシティジム エリカ」 | PMCG1-073 | trainer `SwitchWithBench` | trainer: 元のカードの登録の文面（P43 p.254） | ポケモンジム第2弾エリカ |
| GD4-025 | リサイクル | ポケモンジム第2弾「タマムシシティジム エリカ」 | PMCG3-047 | trainer `TakeFromDiscardTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD4-027 | タマムシシティジム | ポケモンジム第2弾「タマムシシティジム エリカ」 | PMCG5-078 | trainer `CureByDiscardingEnergyStadium` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD5-011 | カツラのブーバー | ポケモンジム第3弾「グレンタウンジム カツラ」 | PMCG6-031 | attack/0 `CoinBonusDamage`<br>attack/1 `MillSelfThenDamage` | attack/0: この版の印刷の文面<br>attack/1: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD5-018 | きずぐすり | ポケモンジム第3弾「グレンタウンジム カツラ」 | PMCG1-071 | trainer `RemoveDamageCounters` | trainer: 元のカードの登録の文面（P43 p.254） | ポケモンジム第3弾カツラ |
| GD5-020 | なんでもなおし | ポケモンジム第3弾「グレンタウンジム カツラ」 | PMCG1-080 | trainer `CureSpecialConditionsTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD5-022 | ポケモンいれかえ | ポケモンジム第3弾「グレンタウンジム カツラ」 | PMCG1-073 | trainer `SwitchWithBench` | trainer: 元のカードの登録の文面（P43 p.254） | ポケモンジム第3弾カツラ |
| GD5-023 | ポケモン図鑑HANDY505 | ポケモンジム第3弾「グレンタウンジム カツラ」 | PMCG1-082 | trainer `ArrangeOwnDeckTopTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD5-024 | グレンタウンジム | ポケモンジム第3弾「グレンタウンジム カツラ」 | PMCG6-085 | trainer `IgnoreWeaknessFromTypeStadium` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD6-010 | ナツメのスリーパー | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | PMCG6-051 | attack/0 `BenchBasicFromEitherDiscard`<br>attack/1 `CoinsPerDefenderCountersDamage` | attack/0: この版の印刷の文面<br>attack/1: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD6-014 | エネルギー回収 | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | PMCG1-076 | trainer `DiscardFromHandThenRetrieveEnergy` | trainer: 元のカードの登録の文面（P43 p.257） | ポケモンジム第3弾ナツメ |
| GD6-015 | きずぐすり | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | PMCG1-071 | trainer `RemoveDamageCounters` | trainer: 元のカードの登録の文面（P43 p.254） | ポケモンジム第3弾ナツメ |
| GD6-016 | ディフェンダー | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | PMCG1-079 | trainer `AttachedDamageReduction` | trainer: 元のカードの登録の文面（P43 p.257） | ポケモンジム第3弾ナツメ |
| GD6-020 | なんでもなおし | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | PMCG1-080 | trainer `CureSpecialConditionsTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD6-021 | プラスパワー | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | PMCG1-081 | trainer `AttachedAttackBonus` | trainer: 元のカードの登録の文面（P43 p.257） | ポケモンジム第3弾ナツメ |
| GD6-022 | ポケモンセンター | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | PMCG1-083 | trainer `HealEachDamagedPokemonTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD6-024 | ワープポイント | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | PMCG6-080 | trainer `SwitchBothActivesTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| GD6-025 | ヤマブキシティジム | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | PMCG6-090 | trainer `ReturnBasicEnergyStadium` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| QSG-047 | エネルギー回収 | クイックスターターギフト | PMCG1-076 | trainer `DiscardFromHandThenRetrieveEnergy` | trainer: 元のカードの登録の文面（P43 p.257） | クイックスターターギフトパック |
| QSG-048 | エネルギー転送 | クイックスターターギフト | PMCG3-044 | trainer `SearchDeckTrainer`（処理が違う） | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| QSG-049 | きずぐすり | クイックスターターギフト | PMCG1-071 | trainer `RemoveDamageCounters` | trainer: 元のカードの登録の文面（P43 p.254） | クイックスターターギフトパック |
| QSG-050 | ギャンブラー | クイックスターターギフト | PMCG3-045 | trainer `ReturnHandsToDeckTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| QSG-051 | 突風 | クイックスターターギフト | PMCG1-072 | trainer `SwitchOpponentWithBench` | trainer: 元のカードの登録の文面（P43 p.255） | クイックスターターギフトパック |
| QSG-052 | ポケモンいれかえ | クイックスターターギフト | PMCG1-073 | trainer `SwitchWithBench` | trainer: 元のカードの登録の文面（P43 p.254） | クイックスターターギフトパック |
| QSG-053 | ポケモン交換おじさん | クイックスターターギフト | PMCG1-093 | trainer `TradePokemonWithDeck` | trainer: 元のカードの登録の文面（P43 p.259） | クイックスターターギフトパック |
| IP1-007 | きずぐすり | イントロパック(フシギダネデッキ) | PMCG1-071 | trainer `RemoveDamageCounters` | trainer: 元のカードの登録の文面（P43 p.254） | イントロパック |
| IP1-019 | ポケモンいれかえ | イントロパック(フシギダネデッキ) | PMCG1-073 | trainer `SwitchWithBench` | trainer: 元のカードの登録の文面（P43 p.254） | イントロパック |
| IP1-028 | 突風 | イントロパック(フシギダネデッキ) | PMCG1-072 | trainer `SwitchOpponentWithBench` | trainer: 元のカードの登録の文面（P43 p.255） | イントロパック |
| IP2-007 | なんでもなおし | イントロパック(ゼニガメデッキ) | PMCG1-080 | trainer `CureSpecialConditionsTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| IP2-009 | ニョロモ | イントロパック(ゼニガメデッキ) | PMCG1-024 | attack/0 `ExtraEnergyDamage` | attack/0: この版の印刷の文面 | （元のカードの記録を使わない） |
| IP2-019 | エネルギー・リムーブ | イントロパック(ゼニガメデッキ) | PMCG1-070 | trainer `DiscardAttachedEnergyTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| IP2-024 | きずぐすり | イントロパック(ゼニガメデッキ) | PMCG1-071 | trainer `RemoveDamageCounters` | trainer: 元のカードの登録の文面（P43 p.254） | イントロパック |
| IPH-001 | フシギバナ | イントロパック(おまけカード) | PMCG1-011 | power/0 `EnergyTransfer` | power/0: 元のカードの登録の文面（P43 p.16・p.323） | — |
| IPH-002 | カメックス | イントロパック(おまけカード) | PMCG1-032 | attack/0 `ExtraEnergyDamage`<br>power/0 `AttachEnergyFromHand` | attack/0: 元のカードの登録の文面（P43 p.90）<br>power/0: 元のカードの登録の文面（P43 p.90） | — |
| PR1-028 | カメックス | プロモ(旧裏) | PMCG1-032 | attack/0 `ExtraEnergyDamage`<br>power/0 `AttachEnergyFromHand` | attack/0: 元のカードの登録の文面（P43 p.90）<br>power/0: 元のカードの登録の文面（P43 p.90） | — |
| PR1-029 | フシギバナ | プロモ(旧裏) | PMCG1-011 | power/0 `EnergyTransfer` | power/0: 元のカードの登録の文面（P43 p.16・p.323） | — |
| PR1-030 | リザードン | プロモ(旧裏) | PMCG1-021 | attack/0 `DiscardEnergyCardsThenDamageZeroIfLacking`（処理が違う）<br>power/0 `ConvertAttachedEnergy` | attack/0: この版の印刷の文面<br>power/0: 元のカードの登録の文面（TXT-CHARIZARD） | — |
| PR1-033 | カモネギ | プロモ(旧裏) | PMCG1-063 | attack/0 `OnceAfterEntryNoDamageOnTails` | attack/0: この版の印刷の文面 | （元のカードの記録を使わない） |
| NIP1-007 | なんでもなおし | イントロパック★neo(チコリータデッキ) | PMCG1-080 | trainer `CureSpecialConditionsTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| NIP1-015 | きずぐすり | イントロパック★neo(チコリータデッキ) | PMCG1-071 | trainer `RemoveDamageCounters` | trainer: 元のカードの登録の文面（P43 p.254） | — |
| NIP1-020 | マサキ | イントロパック★neo(チコリータデッキ) | PMCG1-074 | trainer `DrawCards` | trainer: 元のカードの登録の文面（P43 p.254） | — |
| NIP1X-006 | プラスパワー | イントロパック★neo(チコリータデッキ：拡張カード) | PMCG1-081 | trainer `AttachedAttackBonus` | trainer: 元のカードの登録の文面（P43 p.257） | — |
| NIP1X-007 | ポケモンいれかえ | イントロパック★neo(チコリータデッキ：拡張カード) | PMCG1-073 | trainer `SwitchWithBench` | trainer: 元のカードの登録の文面（P43 p.254） | — |
| NIP2-008 | なんでもなおし | イントロパック★neo(ワニノコデッキ) | PMCG1-080 | trainer `CureSpecialConditionsTrainer` | trainer: この版の印刷の文面 | （元のカードの記録を使わない） |
| NIP2-020 | きずぐすり | イントロパック★neo(ワニノコデッキ) | PMCG1-071 | trainer `RemoveDamageCounters` | trainer: 元のカードの登録の文面（P43 p.254） | — |
| NIP2-025 | マサキ | イントロパック★neo(ワニノコデッキ) | PMCG1-074 | trainer `DrawCards` | trainer: 元のカードの登録の文面（P43 p.254） | — |
| NIP2X-006 | ディフェンダー | イントロパック★neo(ワニノコデッキ：拡張カード) | PMCG1-079 | trainer `AttachedDamageReduction` | trainer: 元のカードの登録の文面（P43 p.257） | — |
| NIP2X-007 | 突風 | イントロパック★neo(ワニノコデッキ：拡張カード) | PMCG1-072 | trainer `SwitchOpponentWithBench` | trainer: 元のカードの登録の文面（P43 p.255） | — |

ナツメのスリーパー（GD6-010）の写しの修正は、kyuura の台帳（data/curation/card_corrections.json の `FIX-GD6-010-ATK1-DAMAGE`。根拠 `kyuura_existing_record`。kyuura が前の作業で
pcg-search.com のカードの画像を見て「20×」とした判定（data/curation/other_products.json の `reprint_checks`「ナツメのスリーパー」。確度: 確実））を kyuura が当てはめたものです。
写しの作り直しの道具は、kyuura が当てはめた修正の表（`KYUURA_CORRECTIONS`）にこの修正を挙げ、台帳・カードの記録・判定の記録があることを確かめます（新しい根拠 `kyuura_existing_record`。
前の写しの元にないカードだけに使え、エンジンは画像を見ていない）。修正を写しに当てはめ直してはいません（二重の修正をしない）。

## 3. 登録の作り方と記録

### 3.1 登録（`effects.REPRINT_CARDS`）

再録の表 `effects.REPRINT_CARDS`（新しい id → `Reprint`（元のカード・この版の印刷の文面・処理が違う登録・名前））と `_with_reprint_cards` が、元のカードの登録から次のように
作ります。v0.69 の `EQUIVALENT_CARDS`（処理に使う欄が全部同じカードの写し。`equivalent_to`）とは別の表です（混ぜていない）。

- 照合する文面（`text_ja`）は、この版の印刷の文面（kyuura の写しのまま。写しは書き換えていない）。
- 文面を引数に持つ型（`text`。トレーナー・スタジアムの多く）は、引数をこの版の文面にします。型の `check` が、数・種類・対象・順番をこの版の文面で確かめます（4 章）。
- 処理に使う文面（`play_text_ja`）と出典（`source`）は、
  - 元のカードが記録の最新の説明・エラッタにしたがう登録（出典が誌面のページ・kyuura の記録の id）なら、元のカードの登録と同じ（44 の対象。3.2 節）
  - 元のカードが印刷の文面にしたがう登録（出典 `kyuura data/cards.json`）なら、この版の印刷の文面（35 の対象）
  - 処理が違う登録（`behavior`。エネルギー転送の再録の版・ポケモンジム第1弾の元気のかけら・プロモのリザードンの「ほのおのうず」）は、この版の印刷の文面（6 の対象。5 章・6 章）
- 説明文のないワザ（ソーラービーム・ほのおのパンチなど）は、元のカードの登録の値（同じオブジェクト）をそのまま使います。
- 新しい id にすでに登録がある・元のカードに登録がない・元のカードがほかの表（写し・再録）の新しい id・文面の対象が元のカードの文面のある登録と違う・処理が違う対象が文面の対象に
  ない場合は `RuntimeError` です（表の誤りを黙って通さない。`RegistrationTest.test_helper_rejects_bad_tables`）。
- 同じ元のカード・同じ文面・同じ処理の登録は、同じ登録の値（不変なオブジェクト）を使います（8 章）。
- `engine.py`・`resolution/` にカード id の分岐はありません（`TargetTest.test_no_card_specific_branch_in_the_engine`）。

### 3.2 元のカードの記録の最新の説明を再録の版に当てはめる方針

**方針**: 元のカードについて、エンジンがすでに採用している処理に使う文面（過去の原典照合の記録の最新の説明・kyuura の最新の説明 LD-・エラッタ）があるとき、同じカードの組の
再録の版にも、その文面を処理に使います。根拠は、kyuura の規定 `GR-P43-P6-LATEST-DESCRIPTION`（『オフィシャルブック2000』p.6。カードの記述は「最新の説明」で、カード自体のあいまいな
表現・判断のむずかしい表現は最新の説明にしたがう。kyuura が画像で確かめた規定。研究の対応表の `applied_rule_records` に v0.71 の RP-R1 として結んだ）と、それぞれの元のカードの記録です。

- これは再録の版を独立に照合した記録ではありません。元のカードの記録（出典・確認日）は元のカードの記録のままで、再録の版を同じ日に画像で確かめた・kyuura が画像を読み直した、とは
  記録していません。
- 当てはめる範囲は、採用の記録 card_sources.json の `reprint_scope` に対象ごとに書きました: 元のカードの出典（`original_source`）・研究の対応表の元のカードの記録（`records`。
  CC-・LD-・TXT-）・元のカードの過去の原典照合の記録（`verification`）・その記録の収録の一覧（notes の「収録「…」」）にこの版の商品があるか（`listed_product`）。
  - 収録の一覧にこの版の商品がある: 29 の対象（きずぐすり・突風・ポケモンいれかえ・エネルギー回収・ディフェンダー・プラスパワー・ポケモン交換おじさんの、ポケモンジム・
    クイックスターターギフト・イントロパックの版）。
  - 収録の一覧にない: 15 の対象（イントロパック★neo（2001 年。2000 年の本より後の商品）・プロモ・イントロパックのおまけカードの版、収録の一覧が第1弾だけのマサキ、ディフェンダー・
    プラスパワー・突風・ポケモンいれかえ・きずぐすりの一覧にない商品の版）。同じカードの組と `GR-P43-P6-LATEST-DESCRIPTION` による当てはめです。
  - 商品の名前の対応（写しの jp_set → 照合の記録の書き方）は scripts/check_card_sources.py の `REPRINT_PRODUCT_NAMES`（GD1 → 「ポケモンジム第1弾タケシ」など）。
- プロモのリザードン（PR1-030）の［エナジーバーン］は、kyuura のエラッタの記録 TXT-CHARIZARD の notes が、とりかえっこプリーズのプロモ（1stp030。この版。写しの `copies` の
  ページ）の文面と、『オフィシャルブック2000』p.66 が第1弾の版ととりかえっこプリーズの版の両方を最新の説明で載せることを書いているので、その記録の範囲として当てはめました
  （`reprint_scope` の `scope_quote` に記録の notes の引用。scripts/check_research_links.py が研究の基準のコミットの記録と照らす）。印刷の「この力は消える」で、新しい止める処理・
  取り消しは作っていません（`ConvertAttachedEnergy(FIRE)`。元のカードと同じ）。
- フシギバナ（IPH-001・PR1-029）・カメックス（IPH-002・PR1-028）は、元のカードの最新の説明（LD-PMCG1-011-PWR0・LD-PMCG1-032-ATK0・LD-PMCG1-032-PWR0）。IPH-002 の［あまごい］の
  印刷の文面「この力は、自分の中で何度でも使える。」は「番」が落ちている候補として記録しました（採用の記録の `issues`。`affects_behavior: false`。写しは直さない。kyuura への報告事項）。
  処理は最新の説明にしたがいます。
- きずぐすり（9 枚）: 元のカードの照合の記録（p.254）の解説「「きずぐすり」を使おうとしている自分の場のポケモンに、ダメージカウンターが2個のっているのに1個だけとることは
  できません。2個のっていたら2個とってください。」と最新の説明にしたがい、2 個以上なら 2 個・1 個なら 1 個とりのぞきます。印刷の「最大2個、とりのぞいてよい」から、とりのぞく数を
  選ぶ決定を作っていません。ダメージのないとき（`UNRESOLVED_POTION_WITHOUT_DAMAGE`）・ダメージのないポケモン（`UNRESOLVED_POTION_UNDAMAGED_TARGET`）の既存の問いはそのままです。
- ポケモンいれかえ・突風: 再録の版の印刷の文面の「(あなたに／相手に控えがいない時、このカードは使えない)」は最新の説明にないので、`UNRESOLVED_SWITCH_WITHOUT_BENCH`・GW5
  （`UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH`）を決めていません（停止のまま。記録の範囲を `reprint_scope` の `note` に書いた）。
- エネルギー回収: 最新の説明（LD-PMCG1-076-TRAINER）にしたがいます（基本エネルギーカードだけ・使うためにトラッシュしたカードを除く・最大 2 枚）。印刷の「手札に加えてよい」は 0 枚を
  選べることを決めません（ER9・ER10 はそのまま）。

### 3.3 記録と検査

- 採用の記録（card_sources.json）: 78 件。`basis: kyuura_data`・`status: adopted`・`kyuura_commit` は写しの元（7d3f4ca）・`recorded_on` は 2026-10-19・`kyuura_records` は空（研究の
  基準のコミットに、新しい id を指す LD-・CC-・CR-・UQ-・エラッタはない）・`reprint_of`（元のカード）・`play_text`（`reprint_original_play_text` か `kyuura_printed_text`）・
  `reprint_scope`・処理が違う登録の `behavior_differs`・外部照合なし。古い記録の日付・コミットは書き換えていません。
- 研究の対応表（research_links.json）: 再録のポケモンのワザ・特殊能力のうち、元のカードの記録の文面を使う 7 つを `reprint_registrations`（元のカードの登録と記録の id。TXT-CHARIZARD は
  `scope_quote`）に、この版の印刷の文面を使う 11 を `adopted_printed_text` に挙げました。トレーナーの文面は今までどおりこの表の区分の外です。`applied_rule_records` に
  `GR-P43-P6-LATEST-DESCRIPTION` を加えました。
- scripts/check_card_sources.py の `reprint_problems`: 写しの `reprint_targets` の元のカード・元のカードの登録の根拠・同じカードの組・文面と名前のほかの処理に使う欄が同じ・名前が同じ名前
  （`deck.SAME_NAME_SPELLINGS`）・登録が元のカードの登録から決まりどおり（効果の実装・照合した文面・処理に使う文面・出典）・処理が違う登録の一覧・`play_text` の根拠・`reprint_scope` の
  出典と記録と収録の一覧・研究の対応表。登録した再録のカードには記録が要ります。違うカード・HP・必要なエネルギー・種類・記録・処理に使う文面・名前・文面は拒否します
  （`RecordTest`・`UnsupportedWithoutRegistrationTest`）。
- scripts/check_research_links.py の 4h: `reprint_registrations` の一覧・元のカードの区分・同じ文面と出典・同じカードの組・記録の id・エラッタの範囲の引用。

## 4. 書き方を受け付ける一覧（19 枚）

57 枚は、既存の型の確かめを、引数をこの版の文面にするだけで通りました。19 枚は、意味を確かめた書き方を、それぞれの型の登録の引数（数・種類・プレイヤー）と結びつけて 1 通りずつ
加えました（一律の正規化・写しの書き換えはしていない）。引数と合わない書き方は受け付けません（`UnsupportedWithoutRegistrationTest.test_added_wordings_are_tied_to_the_registered_settings`）。

| カード | 加えた書き方 | 結びつけた引数 |
|---|---|---|
| なんでもなおし（GD1-020・GD3-019・GD4-022・GD5-020・GD6-020・IP2-007・NIP1-007・NIP2-008） | 「あなたの対戦ポケモンの「どく・ねむり・マヒ・こんらん」状態を、すべて回復させる。」（`FULL_HEAL_TEXTS`） | 特殊状態の回復 |
| ポケモンセンター（GD1-023・GD6-022） | 「ダメージカウンターとエネルギーカードをすべてとりのぞく。(エネルギーカードはトラッシュする)」 | `discard_energy`・`counters=None` |
| いいきずぐすり（GD3-014） | 「エネルギーカードのついているものを1匹選ぶ。…1枚トラッシュして、…最大4個、とりのぞく。」 | `max_counters=4` |
| ギャンブラー（QSG-050） | 「あなたの手札をすべて山札にもどし」 | `who=HANDS_SELF` |
| エネルギー・リムーブ（IP2-019） | 「相手の場のポケモンを1匹選ぶ。そのポケモンについているエネルギーカードを1枚選び、トラッシュさせる。」 | `opponent_cards=1` |
| ポケモン図鑑HANDY505（GD1-022・GD5-023） | 「あなたの山札の上から最大5枚のカードを見て、好きな順番に入れ替えてから、山札の上にもどす。」 | `max_cards=5` |
| タケシのイシツブテ（GD1-006）のたすけをよぶ | 「空きがない時」（元は「空きが無い時」） | 名前の始まり「タケシの」 |
| エリカのラフレシア（GD4-004）の［ぼうぎょかふん］ | 半角のかっこ・「きぜつ」するしないにかかわらず（`DEFENSIVE_POLLEN_TEXTS`） | — |
| ナツメのスリーパー（GD6-010）のよみがえらせる | 「HPの半分(切りすて)」（`INVIGORATE_TEXTS`） | — |
| カモネギ（PR1-033）のネギでたたく | 回数の制限が先・「うら」なら「このワザのダメージは0になる」（`ONCE_AFTER_ENTRY_NO_DAMAGE_ON_TAILS_TEXTS`） | — |

- なんでもなおしの再録の版の文面は、対象を「あなたの対戦ポケモン」と書きます。処理は v0.55 のまま（FH1 の止める範囲。自分の対戦ポケモンだけが特殊状態なら回復し、ほかの場合は
  使う前に止める）で、v0.71 では変えていません。この版の文面では FH1 の範囲の問い（どのポケモンか）が狭くなるので、止める範囲はこの版にとっては必要より広い（成功を仮定しない側）
  ことを記録します（報告事項）。
- ネギでたたくの「このワザのダメージは0になる」は、コインがダメージの要素だけを決める「ダメージは与えられない」と同じ処理（ワザの失敗ではない）として受け付けました。

## 5. 処理が違うトレーナー 2 種類

### 5.1 エネルギー転送の再録の版（GD4-015・QSG-048）

印刷の文面「あなたの山札から「基本エネルギーカード」を1枚選び出し、相手プレイヤーに見せてから、手札に加えてよい。その後、その山札をよく切る。」にしたがい、v0.53 の
`SearchDeckTrainer` を `target=CardFilter("basic_energy")`・`count=1`・`optional=True`（「てよい」）・`reveal=True`（「見せてから」）・コインなし・使うための条件なしで登録しました。

- 選んだカードを見せて手札に加え（ログ `reveal_from_deck`。公開）、山札を切ります。選べるもの（山札の中身）はログに書きません。特殊エネルギー（無色2個エネルギー・
  レインボーエネルギーなど）は選べません。
- 0 枚を選ぶ・選べるカードがない: 止めずに選ばずに終わり（ログ `trainer_take_none`）、山札を切ります（v0.53 の SR1 と同じ読み方）。
- 化石の秘密の版（PMCG3-044。見せない・選ばなくてよいと書かれていない・選べるカードがなければ ST1）の登録は変えていません。処理に使う文面はこの版の印刷の文面
  （この版を採用したもの。元のカードの記録ではない）。

### 5.2 ポケモンジム第1弾の元気のかけら（GD1-017）

印刷の文面「あなたのトラッシュから、たねポケモンカードを1枚選び、あなたのベンチに出す。その後、そのポケモンに、HPの半分(切りすて)のダメージカウンターをのせる。(あなたの
トラッシュにたねポケモンカードがない時や、あなたのベンチに空きがない時、このカードは使えない)」にしたがい、新しい小さな型 `effects.BenchBasicFromOwnDiscardThenCounters`
（v0.51 の `_BenchBasicFromDiscardTrainer` の部分型。カードごとの新しい進行はない）で登録しました。

- 使うための条件: 自分のトラッシュにたねポケモンカードがない（`NO_BASIC_POKEMON_IN_DISCARD`）・自分のベンチに空きがない（`BENCH_FULL`。せまいジムの 4 匹を含む `bench_limit`）なら、
  手札から出す前に `IllegalActionError`（状態・乱数・ログは変わらない）。第1弾の版（PMCG1-078）の RV1（`UNRESOLVED_REVIVE_WITHOUT_TARGET`）は変えていません。
- 選ぶのは使ったプレイヤーで、ちょうど 1 枚（「選び、…出す」。第1弾の版の「ことができる」がない）。0 枚の答えは受け付けません。
- 順番: ベンチに出す（`zones.bench_from_discard`。カウンターはのせない）→ その後、出したあとの今有効な最大HP（`max_hp`）の半分（切りすて。`half_hp_counters`）のダメージカウンターを
  のせる（ダメージではない。ログ `trainer_place_damage_counters`。公開）。v0.51 のよみがえらせると同じ順番と HP を読む時です。第1弾の版（のせた状態でベンチに出す。出す前のカードの
  HP）の処理は変えていません。今の対応カードのたねポケモンでは、どちらの HP でものせる数は同じです（`ReviveGymTest.test_counters_follow_the_effective_max_hp_after_entering`）。
- カウンターをのせるのは 1 回だけです（出すときにはのせない）。ベンチに出すのはトラッシュからで手札からではないので、爆発ジムの反応（手札のたねポケモンをベンチに出す時）・場に出たときの
  特殊能力の「手札から出した時」の機会はありません（v0.51 の `discard_entry_power_guard`）。トレーナーの効果なので「ワザをうけない」状態・「とうめい」は関係しません。HP の半分なので
  きぜつしません（使い終えたあとのきぜつの処理はしない）。
- 決定を待つ間の保存と復元・使用中のカードの保存則・不正な答えで状態・乱数・ログが変わらないことは `ReviveGymTest` が確かめます。ログの監査（tests/log_audit.py）は、出したすぐあとに
  1 回だけ、HP の半分をのせることを組み立て直して確かめます。

## 6. プロモのリザードンの「ほのおのうず」（PR1-030）

印刷の文面「このカードについているエネルギーカードを2枚トラッシュする。(トラッシュできない時、このワザのダメージは0になる)」にしたがい、新しい小さな型
`effects.DiscardEnergyCardsThenDamageZeroIfLacking(count=2)` で登録しました。要素の並びは既存の要素だけです: `DiscardOwnEnergy(None, count=2, when_lacking=LACKING_ZERO,
timing=TIMING_EFFECT)` → `Damage(OPP, Printed(), requires="discard")`（新しい要素・決定はない）。

- トラッシュするのはカードの枚数で、どのタイプのエネルギーカードでもよい（無色2個エネルギーも 1 枚。出すエネルギーの個数で数えない）。選ぶのはワザを使ったプレイヤー（決定
  `discard_energy`。ちょうど 2 枚）。
- 説明がトラッシュできないときの処理を書いているので、トラッシュはワザの効果です（ワザを使うための条件ではない）。時点はこんらんのコインのあと、ダメージの前。こんらんの「うら」なら
  トラッシュしません。第1弾の版（PMCG1-021。「自分のエネルギーカードを2枚はがしてすてる。」）の HC1（こんらんのときの時点が決まらない）はこの版には当たらず、第1弾の版の登録
  （`DiscardEnergyBeforeDamage(None, 2, "unresolved", "condition")`）は変えていません。
- 2 枚に足りなければ 1 枚もトラッシュせず（一部だけトラッシュしない）、このワザのダメージは 0 です（ログ `discard_energy_failed` の `outcome` は `zero`）。ワザの失敗・ワザを使うための
  条件の違反ではありません。必要なエネルギー（炎 4 つ）からふつうは起こらず、相手のワザを自分のワザとして使うとき（カスミのコダックの「ちょうのうりょく」。説明が条件を書かない）に
  起こります（`FireSpinPromoTest.test_copied_with_one_card_deals_zero_without_discarding`）。ピクシーの「ゆびをふる」（条件がたりなければ使えない）では v0.31 の HC9、ピッピ（無色 3 つ）は
  2 枚以上つくので起こりません。
- v0.31 の `DiscardEnergyBeforeDamage` の確かめ（トラッシュの時点をワザの効果にできるのは「炎」エネルギーカードのワザだけ）は、この文面のために緩めていません（別の型）。
- 3 つの先読みの方法で同じ結果、不正な答えで状態が変わらないことは `FireSpinPromoTest` が確かめます。

## 7. ポケモン図鑑の名前の空白

GD1-022・GD5-023 の「ポケモン図鑑HANDY505」と PMCG1-082 の「ポケモン図鑑 HANDY505」は、空白 1 つだけが違う同じカードの名前です。名前は写しのまま持ち、デッキの「同じ名前は 4 枚まで」
（p.308）で数えるときだけ、データで書いた組（`deck.SAME_NAME_SPELLINGS`・`deck.same_name`）をまとめます。名前の空白を一律に除いていません（表にない名前はそのまま）。3 つの id を
混ぜて 4 枚は受け付け、5 枚は `TOO_MANY_COPIES: 「ポケモン図鑑 HANDY505」が 5 枚` です（`SameNameTest`）。写しにどちらの名前もあることもテストが確かめます。

GD5-007「カツラのウィンディ」・IP2-032「ウィンディ」（対応済みの「ウインディ」と表記が違う）は v0.71 の対象外で、未対応のままです。

## 8. 同じデータのカードとマチスの秘策の候補

- 78 枚は、処理に使う欄（日本語）が同じものをまとめると 45 組です。同じ組の 33 枚は、元のカード・文面・処理が同じなので、同じ登録の値（不変なオブジェクト）を使います（`_with_reprint_cards`
  のまとめ。違う文面のものはまとめない。`RegistrationTest.test_identical_reprints_share_entries`）。
- マチスの秘策の受け付けるかの確かめ（`engine._identity_candidates`）で試すカードは、今までどおり公開の情報（対応しているカードの一覧と効果の登録表）だけから作ります。処理の同じカードを
  1 枚で代表するので、試すカードは v0.70 の 527 から 572 になりました（再録の処理の違う 45 種類）。たねポケモンは 241 → 245。上限（`_IDENTITY_TRIAL_LIMIT` = 512）・2 枚以上を指定する
  コマンドの制限は変えていません。1 枚を指定するコマンドの試す回数は、割り当てる前 1 回 + たねポケモン 245 + 「たねポケモンでない」1 = 247 回です。
- 再録のポケモンの名前はどれも前からある名前なので、カツラのクイズ その3 の答えの候補（名前）は変わっていません。

## 9. v0.70 の文書の訂正（マチスの秘策の「529 回」）

v0.70 の docs/non-pack-effect-reuse-v0.70.md 6 章は、「トラッシュしたあとに、たねポケモンでないカードのほかの項目を読む処理があると、…529 回になり、上限を超えて
`UNSUPPORTED_SECRET_PLAN_IDENTITIES` になります（v0.69 は 459 回で受け付けていた）」と書いていました。これは、その経路（`engine._identity_independent` の `_OpaqueRead`）に入る
処理があればという**条件つきの見積もり**で、v0.69 と v0.70 で受け付けるかが変わることを再現したものではありません。v0.70 の文書の 6 章・8 章を、見積もりで再現していない
（未確認）ことがわかるように直しました。

v0.71 で確かめたこと:

- コード: `_OpaqueRead` は、確かめの中で「たねポケモンでない」とだけ割り当てたうらのカード（おもてにするとトラッシュする）の、`is_basic_pokemon` のほかの項目を読んだときだけ
  起こります。おもてにしたあとの処理（`zones.reveal_face_down`）はカードの id（定義ではない）と `printed_def(...).is_basic_pokemon` だけを読みます。トラッシュのカードを読む
  効果は、`is_basic_pokemon` だけを読むもの（よみがえらせる・元気のかけら・ポケモンの笛の `discard_basic_pokemon`）か、uid だけを選べるものにするもの（わるいいたずらの
  `OpponentDiscardToDeckTop`。うらのカードを効果の対象として指定しないワザ）で、同じコマンドの中でうらのカードを 1 枚指定し、そのあとトラッシュのカードのほかの項目を読む処理は
  見つかりませんでした。
- 代表の盤面と対戦: マチスの秘策のテスト（tests/test_secret_plan_v0_67.py・tests/test_final_pmcg_cards_v0_68.py）と v0.67 の検証用デッキの対戦（2 seed）を、v0.70 の木と v0.71 の木で、
  それぞれ別のプロセスで走らせ、`_OpaqueRead` を数えました。どちらの木でも、テスト（50 件。通った）の確かめ 20 回・対戦の確かめ 2 回で、`_OpaqueRead` は 0 回でした。確かめの拒否も両方の木で同じでした（テストで `UNSUPPORTED_SECRET_PLAN_IDENTITIES` 6 回・`UNSUPPORTED_SECRET_PLAN_LOST_TARGET` 2 回。どちらも 2 枚以上の指定・対象を失う既知の制限）。
- この経路に入る盤面は見つかっていないので、差は**未確認**として記録します。入る盤面が見つかったときは、両方の版で再現してから記録します（上限は上げない。先読みの作り直しはしていない）。

## 10. 検証

### 10.1 確かめたこと

- 78 枚の集合（依頼の並び）・635 枚との重なりなし・元のカードと同じカードの組・文面のほかの処理に使う欄が同じ・登録の数（`TargetTest`）。
- 登録を除くと 78 枚とも未対応にもどる（635 枚が残る）。文面・名前・枚数・数・種類・対象のデータの違いで未対応になる。HP・必要なエネルギー・トレーナーの種類・同じカードの組の違いは
  記録の検査が拒否する（`UnsupportedWithoutRegistrationTest`・`RecordTest.test_scope_check_rejects_other_game_data`）。
- 設定の表（`RegistrationTest.test_settings_table`）: 78 枚のすべての登録について、型と引数・処理に使う文面・出典を元のカードの登録と照らす。
- 焦点のテスト: きずぐすりは 2 個のっていれば 2 個（3 つの版）、いれかえ・突風・エネルギー回収・きずぐすりの既存の止める処理、エネルギー転送の見せる・選ばなくてよい・選べるカードが
  ない、元気のかけらの使うための条件・ちょうど 1 枚・順番・保存と復元・使用中のカード、リザードンのカードの種類と枚数（無色2個エネルギーは 1 枚）・こんらん・まねたときの不足・失敗との
  区別・3 つの先読みの方法・不正な答え・なんでもなおしの再録の版の FH1（tests/test_reprint_text_variants_v0_71.py。39 件）。
- 不変条件・書き出し・観測の監査（`audited`）、ログの監査（正式な対戦）。
- 正式な対戦開始（`new_game`・60 枚・サイド 6 枚）から、再録のカードと前の版のカードを混ぜたデッキ R71（炎）・G71（草・超）・W71（水・闘）の 3 組 × 2 seed × 席の入れかえ（12 局）
  （tools/existing_effect_games.py の `--batch v0.71`）: 12 局とも勝敗が決まり（`game_over` 12。1,437 手）、想定外の拒否・内部エラー・手数の上限・監査の失敗はありませんでした。原典で決められない場面で止まった操作は、既知の `UNRESOLVED_DISCARD_DECK_SHORT`（HC6）1・`UNRESOLVED_PREVENTED_COIN_DAMAGE` 1・`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`（R13）2 で、どれも場から確かめて対戦を続けました。78 枚のうち 56 枚が対戦で使われました（エネルギー転送の再録の版の見せる 6 回・ほのおのうずのトラッシュ 8 枚とダメージ 4 回・元気のかけら（GD1-017）のベンチ 3 回とカウンター・きずぐすり・突風・エネルギー回収の再録の版など）。使われなかった 22 枚（なんでもなおしの 8 枚（対戦では FH1）と、同じ組のほかの id）は単体テストで確かめました。勝敗は判断に使っていません。
- `python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura --check`・`python3 scripts/check_card_sources.py`・`python3 scripts/check_research_links.py --kyuura ../kyuura`: 問題なし。
- ruff: v0.70 と同じ 486 件（新しい指摘なし。行と列を除いて比べた）。
- 変異の定義 50 の `check`（`python3 tools/run_mutants.py check`）: 50 件すべて ok（変異が入り、証人のテストが元のコードで通る）。
- 全体のテスト（固定した写しで 1 回。`python3 -m unittest`）: 4,321 件が通った（skip 1。2,294 秒）。写しの全ファイルの指紋は作業ツリーと同じ（`6284886ce7c0`）で、そのあと変えたのはこの行だけです。

### 10.2 v0.70 との比較（別のプロセス）

固定した v0.70（`1633146`）の木と v0.71 の木を、別々のプロセスで記録して比べました。

- 標準の比較（`tools/engine_lockstep.py record`・`compare`）: 760 局・136,537 歩で食い違い 0・許した差 0（両方の木で拒否の内訳も同じ）。
- 変えた共通の処理（効果の型の確かめ・デッキの同じ名前の数え方・観測のイベントの表・ログの監査）を通る前の版のカードの組: v0.28〜v0.70 の検証用デッキの組（`--batch` の
  すべて。2 seed・席の入れかえ）を、両方の木で記録して比べました: v0.28〜v0.70 の 636 局（2 局は既知の PF1 で対戦準備が止まる）で、状態（形式 22）・ログ・乱数・観測・コマンドの列がすべて同じでした。違ったのは道具の結果の辞書に加えた v0.71 の数（`v071`。前の版のカードの組ではどれも 0）だけです。 新しいポケモンの名前がないので、カツラのクイズの位置の許容は使っていません。一括の許容もしていません。
  写しの元のコミットは同じなので、コミットの読みかえも使っていません。

### 10.3 していないこと

- 78 枚の pcg-search.com との外部照合（kyuura の日本語の文面は pcg-search.com の転記で、同じサイトでは独立した照合にならない）・カードの画像の照合はしていません。
- 大きな seed の探索はしていません。対戦で起こらない境界は単体テストで確かめました（使える場面・使えない場面は `GameTest` の数で報告）。

## 11. 限界・報告事項

- kyuura への報告事項: IPH-002 の［あまごい］の「自分の中で」（「番」が落ちている候補）。再録の版の元のカードの記録（収録の一覧）に、イントロパック★neo・プロモ・おまけカードの版が
  ないこと（同じカードの組と `GR-P43-P6-LATEST-DESCRIPTION` による当てはめで、版ごとの照合ではない）。
- なんでもなおしの再録の版は、文面が対象を「あなたの対戦ポケモン」と書くのに、FH1 の止める範囲のまま（4 章）。
- マチスの秘策の試す回数の見積もり（9 章。未確認）。
- 新しい論点・停止コードはありません（停止コード 149・未解決の裁定 151 のまま）。
