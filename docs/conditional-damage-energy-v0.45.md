# v0.45: 条件つきのダメージ・エネルギーの移動とトラッシュ・受けたダメージを返す効果などのポケモン 15 枚と GV1 の停止コード

v0.44 の最終コミット（`7e8a930`。版 0.44.0）から作業ブランチ `claude/v0.45-conditional-damage-energy` を作り、依頼の 15 枚のポケモンを加えました（版 0.45.0）。
同じ作業で、v0.44 で確かめた GV1 の内部エラーを直し（2 章）、v0.44 の文書のポケモン育て屋さんとサカキのペルシアンの誤りを訂正しました（3 章）。

1. 依頼の 15 枚を、どのワザも登録して対応にした（1 章。保留なし。一部のワザだけを登録してカード全体を対応と数えたものはない）。対応ポケモン 277 → 292、
   ワザの登録 479 → 507、写し 299 → 313 枚（第1弾のゴーストは v0.44 まで写しの参照カードで、写しの組 `pool_v0_45` に移した）。特殊能力・トレーナーの登録は
   変えていない（31・12）。
2. GV1（v0.44 のコードのない問い）は、エリカのピッピの「つきのちから」で起こり、公開の `apply_command` が内部エラー（RuntimeError）になっていた。停止コード
   `UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK` を付けた（裁定は未解決のまま。つきのちからの対象は狭めていない。2 章）。
3. 既存の処理の再利用（4.1 節）と、新しい共通の処理（4.2 節）: 手順 4 のコインの期限のない効果（「それ以後」）、8 段階の「決まった数より小さければ 0 にする」効果、
   こうらがえしの返す効果に倍数とはたらくときのコインを明示した値、抵抗力だけを計算しないダメージ、相手のエネルギーを相手の控えにつけかえる要素、多いエネルギーを
   トラッシュする要素、相手の山札の一番上のカードを動かすゾーンの関数など。
4. 新しい停止コードは 2 つ（5 章）: GV1（`UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK`）と AC13（`UNRESOLVED_MULTIPLE_ATTACK_CHECKS`。v0.36 の未解決の裁定。v0.44 まで
   対応カードで起こらず RuntimeError にしていたが、「スミをかける」の期限のない効果で起こる）。停止コード 53 → 55、未解決の裁定 55 → 56（GV1 は v0.44 から数えている。
   AC13 を加えた）。ほかは既存の問い・コード（W24/S37・HC3・T19b・AC6・`BENCH_FULL`）を使う。クロスカウンターを相手のワザとして使うのはエンジンの未対応
   （`UNSUPPORTED_COPIED_ATTACK`。新しいコードではない）。
5. 書き出しの形式は 11 のまま。持続する効果の種類 `zero_damage_below`・`retaliation_received_damage_scaled` と、`attack_coin_check` の `lasting`（期限のない効果だけ）を
   加えた（形式 8 から書ける。v0.44 までの効果の書き出しとログの形は変えていない。8 章）。

開始の時点で、作業ツリーに未コミットの変更はなく、作業ブランチは v0.44 の最終コミット `7e8a930` から作りました。ガイドブック（『オフィシャルブック2000』）の
キャプチャ・OCR・画像の読み直しは行っていません（第1弾のゴーストは v0.9 の過去の原典照合の記録（p.160。2026-10-13）を再利用した）。読んでいない原典を確かめたことに
する記録は作っていません。英語版の文面・現代のルールで処理を決めていません。研究の基準（kyuura `3f34908`）・カードの写しの元（`ecb2d69`）・固定した参照データは
変えていません。kyuura のデータは変更していません（参照だけ）。

## 1. カードごとの結果

| カード | id | ワザ | 実装の型（要素の並び） | 結果 |
|---|---|---|---|---|
| ゴースト（第1弾） | PMCG1-047 | さいみんじゅつ・ゆめくい | `PutToSleep`・`DamageFailUnlessOpponentStatus(ねむり)`（`FailUnlessOpponentStatus` → `Damage`）。処理に使う文面は v0.9 の照合の記録の最新の説明（p.160） | 対応 |
| カスミのタッツー | PMCG5-024 | スミをかける | `DamageThenLastingAttackCoinCheckOnHeads`（`Damage` → `OpponentAttackCheck(lasting, local_coin)`） | 対応 |
| カスミのジュゴン | PMCG5-031 | こおりのつぶて・とっしん | `DamageMultipliedAgainstType(闘, 2)`（値 `PrintedTimesIfDefenderType`）・`DamageAndSelfDamage(20)` | 対応 |
| キョウのアーボ | PMCG6-002 | とつぜんどく | `DamageThenPoisonAndConfuseOnAllHeads(2)`（`Damage` → `Coin(2)` → どく・こんらん） | 対応 |
| キョウのアーボック | PMCG6-019 | どくをためる・ポイズンパワー | `SelfStatusWithoutDamage(どく)`・`DamageIfSelfStatusThenOpponentStatus(どく, 40)`（`SelfStatusCheck` → `Damage(IfSelfStatus)` → `Status(if_result)`） | 対応 |
| キョウのベトベター | PMCG6-007 | ベトベトハンド・ヘドロなげ | `CoinSwitchOpponentThenStatus(どく)`（`ForceSwitch(local_coin)` → `Status(after_switch)`）・`DamageOnly` | 対応 |
| わるいカメックス | PMCG4-024 | ハイドロキャノン・ロケットタックル | 既存の `ExtraEnergyDamage(水, 20, 2)`・`DamageAndSelfDamageThenPreventDamageOnHeads(10)` | 対応 |
| わるいレアコイル | PMCG4-030 | ソニックブーム・じりょくせん | 既存の `DamageIgnoringWeaknessResistance`・`DamageThenMoveOpponentEnergyToBench`（`Damage` → `MoveOpponentEnergyToBench`） | 対応 |
| カツラのリザードン | PMCG6-032 | ファイヤーブレス・かえんひこう | `DiscardExcessEnergyForDamage(炎, 20)`（`DiscardOwnEnergy(excess_over_cost)` → `Damage(PlusPerDiscarded)`）・既存の `CoinChooseOpponentPokemonDamage(40)`（文面の書き方を 1 つ加えた） | 対応 |
| R団のサンダー | PMCG6-042 | プラズマ・エレクトロバーン | `DamageThenAttachEnergyFromDiscardToSelf(雷)`（`Damage` → `AttachFromDiscard(exact)`）・`DamageAndSelfDamagePerAttachedEnergyCard(雷, 10)` | 対応 |
| イワーク | PMCG1-054 | いわおとし・かたくなる | `DamageOnly`・`ZeroDamageBelowNextTurn(40)`（`SelfPersistent` の `ZeroDamageBelow`） | 対応 |
| ラッタ | PMCG1-062 | かみつく・いかりのまえば | `DamageOnly`・`HalfRemainingHpDamage`（値 `HalfRemainingHp`） | 対応 |
| R団のエビワラー | PMCG5-054 | クロスカウンター・マグナムパンチ | `ReturnReceivedDamageOnHeads(2)`（`SelfRetaliation(multiplier, on_heads)`）。処理に使う文面は kyuura の最新の説明 LD-PMCG5-054-ATK0・`DamageOnly` | 対応 |
| タケシのイシツブテ | PMCG5-047 | たすけをよぶ・スパイラルショット | `PutOwnerBasicFromDeckOntoBenchOnHeads(タケシ)`（`BenchFromDeck(owner, optional, local_coin)`）・`DamageIgnoringResistance`（`Damage(resistance=False)`） | 対応 |
| サカキのニャース | PMCG6-068 | てつだうふり・ダブルひっかき | `CoinOpponentDeckTopDiscardTrainerElseHand`（`OpponentDeckTopDiscardTrainerElseHand`）・既存の `CoinFlipDamage(2, 20)` | 対応 |

- 同じ名前の別のカード: カスミのタッツー（PMCG5-024。HP 50・スミをかける）は PMCG5-025（えんまく）と、タケシのイシツブテ（PMCG5-047。HP 40）は PMCG5-046（いしなげ）と、
  サカキのニャース（PMCG6-068。HP 40）は PMCG6-063（ねこノミ・ねこキック）と、第1弾のゴースト（PMCG1-047。とうめいを持たない）は化石の秘密のゴースト（PMCG3-030）と
  別のカードです。進化元は名前の完全一致で決め、収録の弾で制限しません（第1弾のゴーストはどちらのゴースからも、わるいレアコイルは第1弾・ロケット団のコイルから進化できる）。
- v0.45 のワザの型 18 は tests/helpers.py の `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません（解決の基盤の要素の並びで処理する）。
  engine.py・resolution/ にカード id の分岐はありません（tests/test_conditional_damage_energy_v0_45.py の `CardDataTest`）。

## 2. GV1 の停止コード

GV1（v0.44。トレーナー「サカキ」の許可だけで「その番に場に出した」「その番に進化した」の制限が外れるポケモンを、山札から重ねる効果で進化させられるか）は、
説明の「(ポケモンを進化させる時には、あなたの手札から「進化カード」を出して、そのポケモンの上にのせる)」が許可を手札から重ねる進化に限るのかが決められない未解決の
裁定です。v0.44 では、山札から重ねる効果（たきのぼりしんか・［うか］）が「サカキの」ポケモンではない自分自身を進化させるので起こらないとして、コードのない問い
（起こったらエンジンの不具合）にしていました。

- **再現**: エリカのピッピ（PMCG5-060）がバトル場、サカキのギャラドスが山札にある。手札のサカキのコイキングをこの番にベンチに出し、手札のサカキでそのポケモンに
  許可を与えてから、エリカのピッピが「つきのちから」を使う。つきのちからは自分の場のほかのポケモンも進化させるので、許可のあるサカキのコイキングにサカキのギャラドスを
  重ねられるかで選べるものが変わり、v0.44 では公開の `apply_command` が RuntimeError（内部エラー）になっていました。
- **直したこと**: 問い `evolution_permission_from_deck` に停止コード `UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK` を付けました（`resolution/questions.py`。要素
  `EvolveFromDeck`・`EvolveAttackerFromDeck` が問いを投げる。特殊能力の［うか］は `effects.PERMISSION_FROM_DECK_STOP_CODE` で同じコード）。裁定は未解決のままで、
  許可のあるポケモンを重ねられることにも、重ねられないことにもしていません。止めるのは、宣言の前（先読みが「おもて」の場合を試して見つける。コインの前）で、状態・乱数・
  ログは変わりません。`evolution.evolution_block` が返す印（`PERMISSION_ONLY_FROM_DECK`）は停止コードではなく、呼ぶ側が止めます（v0.44 のまま）。
- **狭めていないこと**: つきのちからの対象（自分の場のポケモン）・進化の制限・許可の意味は変えていません。前の番から場にいるサカキのコイキングには、許可があっても
  なくても、つきのちからの「おもて」でサカキのギャラドスを重ねられます。この番に場に出したサカキのコイキングは、許可がなければ通常の進化の制限で選べるものに
  入りません（止めない）。
- 回帰テストは tests/test_conditional_damage_energy_v0_45.py の `Gv1Test`（再現 2 つ・隣の場合 2 つ。公開の `apply_command` とすべての先読みの方法で、停止コード・
  状態・乱数・ログを確かめる）。研究の対応表は停止コードの行に移し（`not_in_kyuura`。kyuura への報告事項）、コードのない問いの一覧から外しました。
  docs/search-evolution-once-attacks-v0.44.md・evolution.py・effects.py・programs.py の GV1 の説明も合わせて直しました（v0.44 の文書は「v0.45 の訂正」として残す）。

## 3. v0.44 の文書の訂正（ポケモン育て屋さんとサカキのペルシアン）

docs/search-evolution-once-attacks-v0.44.md は、［ボスをよぶ］（サカキのペルシアン）を使う経路にポケモン育て屋さんを挙げていましたが、サカキのペルシアンは
1 進化（サカキのニャースから進化）なので、ポケモン育て屋さん（たねポケモンに 2 進化カードを直接のせる）では場に出せません。訂正した内容:

- ［ボスをよぶ］（「手札から場に出した時」）を使う機会があるのは、手札のサカキのペルシアンをサカキのニャースに重ねる通常の進化だけです。
- ポケモン育て屋さんで重ねたあとに場に出たときの特殊能力を使う機会を出す経路の例は、v0.43 のわるいカイリュー（2 進化。［てしたをよぶ］）です。
- 訂正は v0.44 の文書に「v0.45 の訂正」として書き、元の文は残しました（1 章の 4 項・経路の表・GV1 の段落・［ボスをよぶ］の段落・7 章の表・12 章）。エンジンの処理は
  変えていません（v0.44 の処理は、通常の進化とポケモン育て屋さんの両方の経路で使う機会を出し、カードの段階で正しく分かれていた）。

## 4. 再利用した処理と新しい共通の処理

### 4.1 再利用したもの

- 既存の型: `PutToSleep`・`DamageAndSelfDamage`・`DamageOnly`・`ExtraEnergyDamage`・`DamageIgnoringWeaknessResistance`（v0.39）・`CoinChooseOpponentPokemonDamage`
  （v0.44。かえんひこうの書き方 `COIN_CHOOSE_OPPONENT_POKEMON_DAMAGE_TEXTS` を 1 つ加えた）・`CoinFlipDamage`。
- 既存の要素: ワザ全体のコイン `Coin`（とつぜんどく）・`Status`（`target`・`gate`）・`ForceSwitch`（`local_coin`。v0.38）・`SelfPersistent`（`local_coin`）・
  `SelfRetaliation`（v0.13）・`OpponentAttackCheck`（v0.36）・`DiscardOwnEnergy`（v0.31）・`AttachFromDiscard`（v0.31）・`BenchFromDeck`（v0.32）。
- 既存の持続する効果: `PreventDamage`（ロケットタックル。v0.4b の「ダメージを受けない」状態）・`Retaliation`（クロスカウンター）・`AttackCoinCheck`（スミをかける）。
- 既存の問い・コード: W24/S37（`UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`。クロスカウンターでそろってきぜつしうる場合）・HC3・T19b（効果だけを決めるコイン）・AC6（こんらん）・
  使うための条件 `BENCH_FULL`（たすけをよぶ）・`UNSUPPORTED_COPIED_ATTACK`（クロスカウンターを相手のワザとして使う）。

### 4.2 新しく加えた共通の処理

- **期限のない手順 4 の効果**（スミをかける）: `AttackCoinCheck.lasting`（`active_on(turn)` は はたらく番とそれ以後の番）。期限（`expired`）では消えず、バトル場を
  はなれる・進化する・きぜつする・山札や手札にもどると消えます（p.322・p.323。`persistent.lasting`）。v0.36 の「次の相手の番」の効果（えんまく・すなかけなど）の期限は
  変えていません。重なり（期限のない効果ともう 1 つの効果）は状態に持て、そのポケモンがワザを使うときに AC13 で止めます（5 章）。
- **8 段階の「決まった数より小さければ 0 にする」効果**（かたくなる）: 持続する効果 `state.ZeroDamageBelow`（自分自身。はたらく番は次の相手の番）と、ダメージの変更効果の
  計算 `damage.ZERO_IF_BELOW`（その段階のダメージがしきい値より小さければ 0、しきい値以上ならそのまま）。`effects.attack_damage_modifiers` が 8 段階に加え、
  ログ `damage` に `damage_zero_below`（(段階, 発生源のカード, しきい値)）を残します。v0.4b の「ダメージを受けない」状態（計算の前に無効）とは別の効果です。
- **倍数とはたらくときのコインのある返す効果**（クロスカウンター）: v0.13 の `Retaliation`（受けたダメージで決まる `RETALIATION_RECEIVED`）に `multiplier`・`on_heads` を
  明示した値（種類 `retaliation_received_damage_scaled`）。固定の量・受けたダメージそのままの効果（ほのおのかべ・こうらがえし）の値・ログ・書き出しは変えていません。
  コインは効果がはたらくとき（`kernel.attack_damage_to_damage_source`。相手のワザのダメージの処理のあと・ダメージ以外の効果の前）に効果を持つポケモンの持ち主が投げ、
  「うら」ならログ `retaliation_skipped` の理由 `coin_tails`。ダメージを与えたポケモンがすでに HP 以上なら投げません（C15）。
- **抵抗力だけを計算しないダメージ**（スパイラルショット）: 要素 `Damage` の `resistance`（`calculate_attack_damage(..., resistance=False)`。ログ `ignore_resistance`）。
  弱点・ほかの段階は今までどおり計算します（v0.39 のソニックブーム（弱点・抵抗力の両方）とは別の値）。
- **相手のエネルギーを相手の控えにつけかえる要素** `MoveOpponentEnergyToBench`（じりょくせん）と決定の種類 `move_opponent_energy`、ログ `move_opponent_energy`
  （`result` は `attached`・`evaded`）。要素の種類 `ENERGY_MOVE_ELEMENT`（はがすのは相手の対戦ポケモンへの効果）を `ATTACK_ELEMENTS` に加えました。
- **多いエネルギーをトラッシュする要素**: `DiscardOwnEnergy.excess_over_cost`（ファイヤーブレス）と値 `PlusPerDiscarded`。
- **条件の要素と値**: `FailUnlessOpponentStatus`（ゆめくい）・`SelfStatusCheck`（ポイズンパワー）・`Status` の `if_result`・`after_switch`・値 `PrintedTimesIfDefenderType`・
  `IfSelfStatus`・`PerAttachedEnergyCards`・`HalfRemainingHp`。
- **山札の要素**: `BenchFromDeck` の `owner`（「(owner)のポケモン」）・`optional`（0〜1 枚）・`local_coin`、`OpponentDeckTopDiscardTrainerElseHand` とゾーンの関数
  `zones.take_deck_top`（ログ `take_deck_top`。カードを引く処理ではない）。`AttachFromDiscard.exact`（ちょうど 1 枚。プラズマ）。

## 5. 新しい停止コード・既存の問い・エンジンの未対応

| id | 問い | コード | 起こる場面 | 隣の場合（止めない） |
|---|---|---|---|---|
| GV1 | サカキの許可だけで制限が外れるポケモンを、山札から重ねる効果で進化させられるか（2 章） | `UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK`（v0.45 から） | つきのちからで、この番に場に出して許可を受けたサカキのコイキングに、山札のサカキのギャラドスを重ねられる | 前の番から場にいるサカキのコイキング（重ねる）・許可のないこの番のサカキのコイキング（選べない） |
| AC13 | 手順 4 の効果を 2 つ以上受けたポケモンがワザを使うとき、効果ごとにコインを投げるのか（その順番）、1 枚のコインで両方を決めるのか（p.309・p.322・p.323 から決められない） | `UNRESOLVED_MULTIPLE_ATTACK_CHECKS`（v0.45 から。v0.36〜v0.44 は対応カードで起こらず RuntimeError） | 期限のない「スミをかける」を受けたポケモンが、もう一度の「スミをかける」・えんまくなどを受けてワザを使う（宣言のあと・コインの前。こんらんの AC6 より先） | 効果が 1 つ（手順 4 のコイン 1 枚。こんらんなら AC6） |

- 既存の問い: クロスカウンターでエビワラーとワザを使ったポケモンがそろってきぜつしうる場合は W24/S37（`UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`。「おもて」の場合を
  数える。勝者を推測で決めない）。効果だけを決めるコイン（スミをかけるの効果のコイン・とつぜんどくの 2 枚・ベトベトハンドの入れ替えのコイン）は、相手が「ワザをうけない」なら
  HC3、「とうめい」で受けないことがありうるなら T19b（v0.34 の `void_coin_question`・v0.38 の `has_target`）。
- エンジンの未対応: クロスカウンターを相手のワザとして使う（ゆびをふる・ちょうのうりょく）のは、v0.31 の `SelfRetaliation.copy_problem` と同じ
  `UNSUPPORTED_COPIED_ATTACK`（研究の対応表の停止コードに入れない）。
- エンジンが止める `UNRESOLVED_…` は 53 → 55 件、未解決の裁定は 55 → 56 件（GV1 は v0.44 から未解決の裁定に数えていたので増えない。AC13 を加えた）。どちらも kyuura の
  未解決の一覧にない（`not_in_kyuura`。kyuura への報告事項）。

## 6. 規定と根拠（カードごと）

| カード・ワザ | 規定（処理） | 根拠 |
|---|---|---|
| ゆめくい | 相手が「ねむり」状態でないとき、ワザの失敗（p.323 の 12。ワザは使ったことになり番は終わる。ログ `attack_failed` の `reason` は `condition`）。確かめるのはワザの内容を処理するとき（こんらんのコインのあと）。どく・こんらん・マヒでは失敗する | v0.9 の照合の記録の最新の説明（p.160。kyuura の LD-PMCG1-047-ATK1 と同じ文）。印刷の文面（「ねむり」のときだけダメージをあたえる）は照合だけ |
| スミをかける | 相手に 20 → 効果のコインの「おもて」で期限のない手順 4 の効果。受けたポケモンはそれ以後ワザを使うたびにコイン（「うら」なら失敗）。バトル場をはなれる・進化で消える | kyuura の印刷の文面・v0.36 の手順 4 の規定（AC1〜AC14）・p.322・p.323 |
| こおりのつぶて | 相手の対戦ポケモンが闘ポケモンなら 1 段階で 20 × 2（弱点・抵抗力・プラスパワーなどはそのあと） | 印刷の文面・p.321（GR-2000-P321-DAMAGE-ORDER） |
| とつぜんどく | 2 枚のコインがすべて「おもて」なら、どくとこんらんの両方（1 組のコイン） | 印刷の文面 |
| どくをためる・ポイズンパワー | 自分を通常のどく（特殊などくのポケモンは通常のどくになる。v0.3a の 14）。ポイズンパワーは、ワザの内容を処理するときに自分がどく（通常・特殊のどちらでも）なら 1 段階で 40、相手をどく（相手がこのワザで HP 以上なら与えない） | 印刷の文面・p.322・p.309 |
| ベトベトハンド | コインの「おもて」で、ワザを使ったプレイヤーが相手の控えを選んで入れ替え、新しい対戦ポケモンをどく。入れ替える前の対戦ポケモンはどくにしない。控えがいなければコインを投げない | 印刷の文面・v0.31 のかどわかす・v0.38 の `has_target` |
| ロケットタックル | 相手に 40 → 自分に 10 → コインの「おもて」で次の相手の番にダメージを受けない（ダメージ以外の効果は受ける）。自分が HP 以上ならコインを投げない | 印刷の文面・v0.4b |
| じりょくせん | 相手の対戦ポケモンの基本エネルギーカード（ワザを使ったプレイヤーが選ぶ。1 枚でも決定）を、相手の控え（選ぶ）につける。控えがいない・基本エネルギーがない・相手がこのワザで HP 以上なら何もしない。つける控えが「とうめい」で受けなければ持ち主のトラッシュ | 印刷の文面・CR-TRANSPARENCY-ENERGY-BOMB（わるいマルマイン）と同じ読み方（実装上の判断。v0.31 の `MoveOwnEnergyToBench` と同じ処理） |
| ファイヤーブレス | 必要なエネルギー（炎 1）より多い炎の基本エネルギーカードをすべてトラッシュ（選ぶのはワザを使ったプレイヤー。ワザの効果。こんらんの「うら」ならトラッシュしない）し、トラッシュした枚数 × 20 を 1 段階で追加 | 印刷の文面・RUL-ENERGY-DISCARD-ATTACKS の範囲（v0.34 のブースターと同じ扱い。記録の `cards` にないことは kyuura への報告事項） |
| プラズマ | 相手に 20 → トラッシュに雷のエネルギーカードがあれば 1 枚（ちょうど。選ぶ）を自分につける（手札からつける回数に数えない）。自分が HP 以上ならつけない | 印刷の文面・v0.31 のたいでん |
| エレクトロバーン | 相手に 70 → 自分にも、ついている雷のエネルギーカードの枚数 × 10（ワザによる自分へのダメージ） | 印刷の文面・v0.2f・v0.3d |
| かたくなる | 次の相手の番、受けるワザのダメージが 8 段階で 40 より小さければ 0、40 以上ならそのまま。ダメージ以外の効果は受ける。次の相手の番の終わりに消える | 印刷の文面・p.321 の 8 段階（GR-2000-P321-DAMAGE-ORDER の 8 段階の例が「かたくなる」） |
| いかりのまえば | 相手の残りの HP の半分（ダメージカウンターの単位で切り上げ）を 1 段階の基本となるダメージにする（弱点などはそのあと） | 印刷の文面・p.321 |
| クロスカウンター | 次の相手の番、相手のワザのダメージを受けたら（このカードがきぜつしても）持ち主がコイン。「おもて」なら受けた最終ダメージの 2 倍を「クロスカウンター」のワザによるダメージとして与える（弱点・抵抗力などを計算する） | kyuura の LD-PMCG5-054-ATK0・CR-SHELL-ATTACK-ATTACKER-PLUSPOWER（受けたダメージは最終ダメージ）・CR-SHELL-ATTACK-TIMING と同じ時点（CMP-RETURN-DAMAGE-ATTACKS も参照） |
| たすけをよぶ | ベンチに空きがなければ使えない。コインの「おもて」で、山札の「タケシの」たねポケモンを 0〜1 匹ベンチに出し（手札を通さない）、どの場合も山札を切る。「うら」なら何もしない（切らない） | 印刷の文面・v0.32・v0.44 のおつかいと同じ読み方 |
| スパイラルショット | 抵抗力（4 段階）だけを計算しない | 印刷の文面 |
| てつだうふり | コインの「おもて」で、相手の山札の一番上がトレーナーなら相手のトラッシュ、それ以外なら相手の手札（カードを引くことではない。山札は切らない）。相手の山札がなければコインを投げない | 印刷の文面・v0.44 のわるいいたずらと同じ読み方 |

## 7. 対戦

検証用デッキ `G45`（草・水）・`R45`（炎・雷）・`F45`（闘・無色）・`W45`（水・超）と組 `PAIRINGS_V0_45`（`G45` 対 `R45`・`R45` 対 `F45`・`F45` 対 `W45`・`W45` 対 `G45`・
`G45` 対 `P31`）を tools/existing_effect_games.py の `--batch v0.45` に加えました。決定は `_v045_decision`（じりょくせん・たすけをよぶ・ファイヤーブレス・かえんひこう）。
AC13・W24 で拒否されたワザは場から確かめます（`V031_STOPS`）。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断していません。

`--batch v0.45 --seeds 8`（80 局。最終のコードで走らせた）: 終わり方は通常の勝敗 76・サドンデス 2・対戦準備の既知の停止（`UNRESOLVED_MULLIGAN_COMPENSATION`）2。
監査の失敗・想定外の拒否・内部エラーは 0。15 枚のどのワザも使われ、ゆめくいの失敗（68 回）とダメージ（15 回）・じりょくせんのつけかえ（14 回）・てつだうふり（12 回）・
たすけをよぶのベンチ（6 回）・クロスカウンターの「おもて」（7 回）と「うら」（5 回）・かたくなるで 0 になったダメージ（8 回）としきい値以上でそのまま受けたダメージ（7 回）・
スミをかけるで与えた効果（35 回）・ファイヤーブレスで多いエネルギーをトラッシュしてからダメージを与えた回（21 回）・プラズマでつけたエネルギー（20 回）が起こりました。原典で決められない場面で拒否されたワザ
（そのあと別の操作で続けた）は AC13 16 回・W24 12 回・JS1 24 回・HC2 7 回・HC4 7 回（AC13 は、期限のない「スミをかける」を受けたポケモンが、もう一度受けてワザを使う場面）。

## 8. 互換性

- 公開の API（`apply_command`・`new_game`・コマンド）は変えていません。書き出しの形式は 11 のまま（新しい形式はない）。
- 状態の型: 持続する効果の型 `ZeroDamageBelow` を加え、`Retaliation` に `multiplier`（既定 1）・`on_heads`（既定 False）、`AttackCoinCheck` に `lasting`（既定 False）を
  加えました。既定の値の効果は v0.44 と同じに書き出し、同じ種類です。書き出しは、`zero_damage_below`（`threshold`）・`retaliation_received_damage_scaled`
  （`attack_index`・`multiplier`・`on_heads`）・`attack_coin_check` の `lasting`（期限のない効果だけ）を加えました（形式 8 から書ける。形式 1〜7 は `ValueError`）。
- 決定の種類 `move_opponent_energy` を加えました。新しいログのイベントは `move_opponent_energy`・`take_deck_top`。既存のイベントに加えた項目: `damage` の
  `damage_zero_below`・`ignore_resistance`、`retaliation` の `multiplier`・`coin`（クロスカウンターだけ）、`retaliation_skipped` の理由 `coin_tails` と
  `received_damage`、`persistent_effect_added` の `lasting`（期限のない効果だけ）、`bench_from_deck_declined` の `owner`。
- ダメージの変更効果の計算 `damage.ZERO_IF_BELOW` と `calculate_attack_damage` の `resistance`（既定 True）、`state.RETALIATION_RECEIVED_SCALED_KIND`、
  `effects.RETALIATION_COIN_TAILS`・`ENERGY_MOVE_ELEMENT` を加えました。
- 既存の動作の変更は 2 つ（どちらも v0.44 までは内部エラー）: GV1 の場面が停止コードで拒否されるようになった（2 章）、AC13 の場面（2 つ以上の手順 4 の効果）が
  `RuntimeError` から停止コードになった。どちらも対応カードの既存の検証用デッキでは起こらず、固定した v0.44 との比較で食い違いはありません（9.2 節）。
- 研究の対応表（`research_links.json`）: 停止コードに GV1・AC13（`not_in_kyuura`）、最新の説明の区分に第1弾のゴースト（`registered` に LD-PMCG1-047-ATK1・
  `recorded_in_card_checks` に CC-PMCG1-047-P160）・R団のエビワラーのクロスカウンター（`registered` に LD-PMCG5-054-ATK0）・採用の 14 枚の説明文のあるワザ 21
  （`adopted_printed_text`）。kyuura の記録で登録していないものは LD-PMCG6-023-PWR0（キョウのベトベトンのだつりょくえき。v0.17c から延期）だけになりました。

## 9. 検証

### 9.1 テスト

- tests/test_conditional_damage_energy_v0_45.py: 登録・写し・記録（`CardDataTest`）・GV1（`Gv1Test`）・ゆめくい・スミをかけると AC13（効果が 1 つ・2 つ・えんまくとの重なり・
  AC6 との順番・HC3・T19b・期限・にげる・進化）・こおりのつぶて・とつぜんどく・ポイズンパワー・ベトベトハンド・ハイドロキャノン・ロケットタックル・ソニックブーム・
  じりょくせん（決定・効果がない場合・「とうめい」・バリアー・決定の途中の保存と再開）・ファイヤーブレス・かえんひこう・プラズマ・エレクトロバーン・かたくなる
  （しきい値・期限・8 段階）・いかりのまえば・クロスカウンター（「おもて」・「うら」・対象なし・期限・W24・まねる）・たすけをよぶ・スパイラルショット・てつだうふり・
  ダブルひっかき・不変条件（登録の値との照合・期限のない効果）・先読みの方法の一致・書き出し（形式 8 以降・v0.44 の形のまま）・正式な対戦（`GameTest`）。
- 既存のテストの期待値の更新（確かめる性質は弱めていない）: 写しと登録の数・研究の対応表の数と停止コードの一覧（GV1・AC13）・停止コードの境界の一覧・G37 の宣言の型
  （5 つ）・バリアーで止まるコインの型（とつぜんどく）・v0.17 から加えた型の一覧・第1弾のゴースト（参照カードだった性質は、その登録を除いた登録表
  `NO_BASE_HAUNTER_EFFECTS` で確かめる）・研究の基準のコミットの記録の検査（第1弾のゴーストを登録していない状態から始める）・変異 M18 の置きかえる文字列（`_retaliation_error`
  の引数に `res.state` を加えたので、同じ誤りを今のコードに入れるように直した。変異は消していない）。
- ログの監査（tests/log_audit.py）: `move_opponent_energy`（エネルギー・トラッシュの組み立て直し・「とうめい」）・`take_deck_top`（手札・トラッシュ）・クロスカウンター
  （直前の持ち主のコイン・倍数・受けたダメージ・「うら」）・期限のない手順 4 の効果（期限で消えない・ワザを使うたびのコイン）・かたくなるの 8 段階の記録・たすけをよぶの
  「タケシの」たねポケモンを確かめるようにしました。

### 9.2 比較・検査

最終のコードで行いました。

- **固定した v0.44 との比較（別のプロセス・別の木）**: `python3 tools/engine_lockstep.py tree --commit 7e8a930` で v0.44 の木を展開し、`record`（`--corpus all --seeds 10
  --stress-seeds 2 --save-every 7`。木ごとに別のプロセスで、その木の公開の API だけを使う）と `compare` で比べました。290 局・48,092 歩で食い違い 0・許した差 0
  （拒否の内訳も同じ。内部エラー 0）。
- **前の版の検証用デッキの対戦の比較**: 同じ 2 つの木で、tools/existing_effect_games.py の `--batch v0.28`〜`--batch v0.44` の組を、席の入れかえ・seed 0〜4 で
  走らせ（木ごとに `python3 -I` の別のプロセス）、1 局ごとに受け付けた操作の列・最後の状態（形式 11）の指紋・ログ・乱数の指紋・数えた出来事・監査の結果を比べました。
  630 局・84,083 歩で食い違い 0。v0.45 のカードを使わない対戦の結果は v0.44 と同じです（v0.45 の組は v0.44 の木では作れないので比べていない）。
- **GV1 の再現**: 2 章の盤面（この番にベンチに出したサカキのコイキングにサカキで許可を与え、エリカのピッピがつきのちからを使う）を、公開の `apply_command` で
  両方の木に渡しました。v0.44 の木は RuntimeError（内部エラー）、v0.45 は `UnsupportedError`（`UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK`）です。
- **v0.45 の対戦**: 7 章の `--batch v0.45 --seeds 8`（80 局。監査の失敗・想定外の拒否・内部エラー 0）。
- **検査**: `python3 scripts/check_card_sources.py`（記録 236 件。方針と合う）・`python3 scripts/check_research_links.py --kyuura ../kyuura`（研究の基準 `3f34908` の記録と
  一致）・`python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura --check`（写しは `ecb2d69` と一致）・`ruff check --select F,E9 .`（問題なし）。
- **変異試験**: `python3 tools/run_mutants.py check`（すべての変異が今のコードに入る）。置きかえる文字列を直した M18 は `witness` で、2 つの証人のテストが元のコードで通り、
  変異で失敗することを確かめました（`witness_failed`）。ほかの変異の証人・`full` は走らせていません（v0.45 で定義を変えていない）。
- **テスト**: 最終のコードで `python3 -m unittest`（リポジトリの直下。1 つのプロセス）を走らせ、3,176 件 OK（skipped 1。約 9.5 分）でした（v0.44 の 3,106 件から
  70 件増えた。v0.45 のテストのファイルは 69 件）。

### 9.3 行っていないこと

- ガイドブックの読み直し・pcg-search.com 以外の外部照合はしていません。
- 対戦 AI・勝率・デッキの釣り合いの評価はしていません。

## 10. 未解決・限界・報告事項

- GV1・AC13 は未解決の裁定のままです（停止コードで止める。根拠が見つかるまで決めない）。
- kyuura への報告事項: わるいカメックスのハイドロキャノンの文面の「がいている」（転記の誤りと思われる 1 文字の脱落。サイトは「ついている」）、わるいレアコイルの
  「特殊エネルギーカード以外」（サイトは「特殊エネルギー以外」）、タケシのイシツブテ（HP 40）の「空きが無い」（サイトは「空きがない」）、ラッタのいかりのまえばの
  ダメージの表示「?」（サイトに表示がない）。どれも処理に影響しないので、kyuura の文面・値のまま使いました（写しは直さない）。RUL-ENERGY-DISCARD-ATTACKS の
  `cards` にカツラのリザードン（ファイヤーブレス）がないこと。GV1・AC13 が kyuura の未解決の一覧にないこと。
- じりょくせんの、つける控えが「とうめい」で受けないときのトラッシュは、CR-TRANSPARENCY-ENERGY-BOMB（わるいマルマイン）と同じ読み方を当てはめた実装上の判断です
  （このカードの記録はない）。
- 特殊エネルギーのカードは写しにないので、じりょくせん（特殊エネルギーカード以外）・ファイヤーブレス（基本エネルギーカードの枚数）・エレクトロバーン（エネルギーカードの
  枚数）の特殊エネルギーの扱いは確かめていません。特殊エネルギーを加えるときに見直してください。
