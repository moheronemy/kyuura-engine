# v0.32: 山札からベンチに出すワザ・ダメージカウンターでダメージが決まるワザ・与えたぶん回復するワザ（13 枚）

v0.32 では、依頼の 13 枚だけを対象に、必要な共通の処理を加えて対応にしました（ほかの候補には広げていない）。

- 山札から名前の決まったたねポケモンをベンチに出すワザ（なかまをよぶ・ふえる）と、その進化先
- ダメージカウンターの数でダメージが決まるワザ（じたばた・ヨガのポーズ）と、その進化先
- 与えたぶん回復するワザ（きゅうけつ）

カードデータは kyuura の `data/cards.json`（写しの元 `ecb2d69`）を基本データとして採用し、pcg-search.com の同じ版のページと照合しました
（2026-10-15 からの方針。[card-data-policy.md](card-data-policy.md)）。公式ガイドブックのキャプチャ・OCR・画像の読み直しはしていません。足りない
裁定を現代のルールから推測して決めた箇所はなく、原典（記録）で決められない場面は、その場面だけを止めます（4 章）。

## 1. 結果

| 項目 | v0.31 | v0.32 |
|---|---|---|
| 加えたカード | — | 13 枚（どれも対応） |
| 対応ポケモン（対戦に使えるポケモンのカード） | 106 | 119 |
| ワザの登録 | 176 | 202（+26） |
| 特殊能力の登録 | 12 | 12 |
| カードの写し（`kyuura_cards.json`） | 127 枚 | 140 枚（写しの組 `pool_v0_32`） |
| エンジンが止める `UNRESOLVED_…`（停止コード） | 37 | 38（CD4） |
| 未解決の裁定 | 38 | 39 |
| 書き出しの形式 | 10 | 10（変えていない） |

保留・分離したカードはありません。

## 2. カードごとの結果

処理に使う文面（説明文のあるワザ）は、どれも kyuura の印刷の文面です（kyuura に最新の説明・エラッタ・裁定の記録はない。研究の基準
`3f34908` で確かめた。研究の対応表の `adopted_printed_text`）。説明文のないワザは `DamageOnly`。

| id | カード | 段階 | ワザと実装の型 | pcg-search.com（同じ版） |
|---|---|---|---|---|
| PMCG2-001 | ニドラン♀（第2弾） | たね | みだれひっかき `CoinFlipDamage(3, 10)`・なかまをよぶ `PutBasicFromDeckOntoBench(("ニドラン♂", "ニドラン♀"))` | 第2弾「ポケモンジャングル」002/048。一致 |
| PMCG2-002 | ナゾノクサ（第2弾） | たね | しびれごな `ParalyzeOnHeads`・ふえる `PutBasicFromDeckOntoBench(("ナゾノクサ",))` | 005/048。一致 |
| PMCG2-005 | マダツボミ（第2弾） | たね | つるのムチ `DamageOnly`・なかまをよぶ `PutBasicFromDeckOntoBench(("マダツボミ",))` | 012/048。一致 |
| PMCG3-013 | クラブ（化石の秘密） | たね | なかまをよぶ `PutBasicFromDeckOntoBench(("クラブ",))`・はさむ `DamageOnly` | 第3弾「化石の秘密」016/048。一致 |
| PMCG2-008 | ニドリーナ（第2弾） | ニドラン♀から進化 | ちょうおんぱ `ConfuseOnHeadsWithoutDamage`・にどげり `CoinFlipDamage(2, 30)` | 003/048。一致 |
| PMCG2-011 | ウツドン（第2弾） | マダツボミから進化 | どくのこな `PoisonOnHeads`・はっぱカッター `DamageOnly` | 013/048。一致 |
| PMCG1-031 | コイキング（第1弾） | たね | たいあたり `DamageOnly`・じたばた `DamageTimesOwnCounters(10)` | 第1弾 033/096。一致 |
| PMCG1-034 | ギャラドス（第1弾） | コイキングから進化 | りゅうのいかり `DamageOnly`・バブルこうせん `ParalyzeOnHeads` | 034/096。一致 |
| PMCG3-019 | キングラー（化石の秘密） | クラブから進化 | じたばた `DamageTimesOwnCounters(10)`・クラブハンマー `DamageOnly` | 017/048。一致 |
| PMCG1-048 | ルージュラ（第1弾） | たね | おうふくびんた `CoinFlipDamage(2, 10)`・ヨガのポーズ `DamagePlusDefenderCounters(10)` | 049/096。一致 |
| PMCG2-004 | コンパン（第2弾） | たね | しびれごな `ParalyzeOnHeads`・きゅうけつ `DamageAndFullDrain` | 010/048。違い 1（「与えたぶんの」と「与えた分の」。表記だけで処理は同じ） |
| PMCG3-002 | ズバット（化石の秘密） | たね | ちょうおんぱ `ConfuseOnHeadsWithoutDamage`・きゅうけつ `DamageAndFullDrain` | 003/048。一致 |
| PMCG3-005 | ゴルバット（化石の秘密） | ズバットから進化 | つばさでうつ `DamageOnly`・きゅうけつ `DamageAndFullDrain` | 004/048。一致 |

- 照合した欄は、名前・段階・HP・タイプ・弱点・抵抗力・にげる・ワザの名前・必要なエネルギー・ダメージの表示・説明文（2026-10-16。
  `kyuura_engine/data/card_sources.json` の `external_checks`）。kyuura の日本語の文面の出典はどれも pcg-search.com ではない（`ja_text_source` は
  別のサイト）ので、独立した照合として数えます。カードの画像は読んでいません。
- 同じ名前の別のカード: 第2弾のナゾノクサ（PMCG2-002）と第4弾のナゾノクサ（PMCG4-003）、化石の秘密のズバット（PMCG3-002）と第4弾のズバット
  （PMCG4-002）は、名前が同じでワザが違う別のカードです。登録はカード id で引くので混ざりません。ふえるは説明が名前「ナゾノクサ」で指すので、
  第4弾のナゾノクサも選べます。ゴルバットの進化元の名前は「ズバット」なので、第4弾のズバットからも通常の進化で進化でき、名前の違うタケシの
  ズバット（PMCG5-001）からは進化できません。ニドラン♂（PMCG1-005）と第4弾のコイキング（PMCG4-020）は写していません（範囲外。今の対戦では
  なかまをよぶで選べるのはニドラン♀だけ）。

## 3. 共通の処理

`engine.py`・`resolution/` にカード id の分岐は加えていません。新しい効果の型は解決の基盤の要素の並び（`resolution/programs.py` の `BUILDERS`）で
処理し、v0.13 の約束（`resolve`・`resume`）では書いていません。どれも `v013_checks.VERIFIED` には入れていません（tests/helpers.py の
`ATTACK_TYPES_SINCE_V0_17` に加えた）。

| 区分 | 処理 | 内容 |
|---|---|---|
| 新規 | 効果の型 `effects.PutBasicFromDeckOntoBench(names)` | 登録の確かめ（`check`: 説明の「自分の山札から「…」を1匹さがしてベンチに」の名前・「その山札をよくきる」・「自分のベンチに空きがなければ…使えない」）、ワザを使うための条件（`usage_problem`: ベンチに空きがなければ `BENCH_FULL`）、決定の形（`decision_problems`） |
| 新規 | 要素 `programs.BenchFromDeck(names)` | 山札の、名前の合うたねポケモンを選ばせて（決定 `BENCH_FROM_DECK`）ベンチに出し、山札を切る。選べるものがなければ出さずに切る。相手のワザとして使うときの条件（`copy_problem`） |
| 新規 | `zones.bench_from_deck` | 山札のカードを、手札を通さずにベンチの最後に出す（場のポケモンの番号・場に出た番は `enter_play`） |
| 新規（移動） | `zones.enter_play` | v0.31 までの `engine._enter_play` の本体をそのまま関数にした（`engine._enter_play` はこれを呼ぶ）。手札から出す処理と共通 |
| 新規 | 決定の種類 `decisions.BENCH_FROM_DECK` | 選ぶのはワザを使ったプレイヤー。選べるものは山札の、名前の合うたねポケモンの uid（小さい順）。1〜1 |
| 新規 | ログ `bench_from_deck`（`card`・`to_pokemon_id`）・`bench_from_deck_none` | 出したカードは場に出るので公開。選べたほかの山札のカードは書かない。どちらのすぐあとにも既存の `shuffle` |
| 新規 | 基本となるダメージ `programs.OwnCountersTimes(per)` | 自分のダメージカウンターの数 × `per`（コインなし） |
| 新規 | 基本となるダメージ `programs.PlusDefenderCounters(per)` | 目安 + 相手の対戦ポケモンのカウンター × `per`。相手の控えにカウンターがあれば問い `opponent_pokemon_counters`（CD4） |
| 新規 | 効果の型 `DamageTimesOwnCounters`・`DamagePlusDefenderCounters`・`DamageAndFullDrain` | 登録の確かめだけ（処理は要素） |
| 変更 | 要素 `programs.Drain` に `full`（既定は偽） | 偽なら v0.31 までと同じ（`counters` が None なら半分の切り上げ、数なら決まった数）。真なら与えたダメージ ÷ 10 個。どれも、のっている数まで |
| 新規 | 問い `questions.QUESTIONS["opponent_pokemon_counters"]` | `UNRESOLVED_OPPONENT_POKEMON_COUNTERS`（CD4。優先度 10） |
| 再利用 | `Damage` 要素・p.321 の計算（`kernel.deal_damage`）・`Drain` のきぜつしたワザを使ったポケモンの扱い（C16）・`zones.shuffle_deck`・ワザを使うための条件（v0.31 の `usage_problem`）・相手のワザとして使うときの条件（v0.31 の `copy_problem` と HC9）・ワザの途中の決定（v0.4d）・既存の効果の型 6 つ（`CoinFlipDamage`・`ParalyzeOnHeads`・`PoisonOnHeads`・`ConfuseOnHeadsWithoutDamage`・`DamageOnly`） | |

先読み: `BenchFromDeck` は先読み（状態の複製の上で試す。乱数はコインだけ）では山札を切りません。切った並びを使う処理が先読みの範囲（宣言から
きぜつの判定まで）にないことを、この要素がワザの最後の要素であることで確かめます（ほかの位置に置くと `RuntimeError`）。実際の処理は既存の
`zones.shuffle_deck`（乱数 `state.rng` の並べかえ 1 回。0・1 枚なら乱数を使わない）で、先読みの方法によらず乱数の使い方は同じです。

## 4. 規定と根拠

分類は既存の記録の再利用です（CONFIRMED・SUPPORTED は、その元の記録の分類）。読んでいない原典を確かめたことにはしていません。

### 4.1 山札からベンチに出す（DB）

| id | 規定 | 分類 | 根拠 | テスト（tests/test_bench_search_counter_drain_v0_32.py） |
|---|---|---|---|---|
| DB1 | 選べるのは山札の、説明の「」の名前と同じ名前のたねポケモン。同じ名前の別のカードも選べ、名前の違うカード・進化カードは選べない | CONFIRMED（文面） | kyuura の印刷の文面（名前で指す）。kyuura のデータで、その名前のカードはどれもたねポケモン（ベンチに出せるのはたねポケモンだけという既存の規定とも合う） | `BenchFromDeckTest.test_candidates_are_basic_pokemon_with_a_named_name` |
| DB2 | 自分のベンチに空きがなければ、このワザは使えない（ワザを使うための条件。必要なエネルギーの確認のあと・こんらんのコインの前。`BENCH_FULL`） | CONFIRMED（文面） | 印刷の文面「自分のベンチに空きがなければ（、このワザは）使えない」。条件の時点は v0.31 の「ぼーっとする」と同じ（`checks.attack_request` の `usage_problem`） | `test_bench_space_boundary` |
| DB3 | 選ぶのはワザを使ったプレイヤーで、1 匹（省略できない） | SUPPORTED | 文面「自分の山札から「…」を1匹さがしてベンチに出す」（「できる」「最大」がない。v0.22 の CS12 と同じ読み方） | `test_invalid_choices_keep_the_decision` |
| DB4 | 山札に選べるものがない（山札 0 枚を含む）: ワザは使える（使えないのはベンチに空きがないときだけ）。ベンチに出すものはなく、そのあと山札を切る | SUPPORTED | p.309「処理の対象がなくなってしまっている場合、その内容は無視して、次の内容の処理をおこなってください」（kyuura の GR-2000-P309-ATTACK-PROCEDURE）。v0.9 の H5・v0.31 のゴミあさりと同じ読み方 | `test_no_target_in_the_deck` |
| DB5 | 出したカードは手札を通らずにベンチに出る。場に出た番は今の番で、手札から出したときと同じ進化の制限（その番には進化できず、次の自分の番には進化できる） | CONFIRMED（文面）・既存の規定 | 文面「山札から…ベンチに出す」。p.310 の進化の制限（v0.4a の `played_turn`） | `test_put_directly_onto_the_bench_and_shuffle`・`test_the_benched_pokemon_follows_the_normal_evolution_rule` |
| DB6 | 出したカードは公開（場）。選べたほかの山札のカードは公開しない | 実装上の判断（既存の方針） | p.312 の山札の規定と v0.22 の CS13 の扱い（山札の中身はログに書かない） | `test_hidden_deck_contents_stay_out_of_the_log` |
| DB7 | 山札を切るのは、ベンチに出したあと（出さなかったときも）。乱数は既存の `zones.shuffle_deck` | CONFIRMED（文面）・実装上の仮定の再利用 | 文面「その後、その山札をよくきる」。v0.22 の CS17 | `test_put_directly_onto_the_bench_and_shuffle`・`test_no_target_in_the_deck` |
| DB8 | こんらん状態: コインが「うら」なら探さない・切らない（こんらんの 20） | 既存の規定 | p.309 の手順 5（v0.3c） | `test_confusion` |
| DB9 | 相手のワザとして使う（ゆびをふる・ちょうのうりょく）: ベンチに空きがあれば、使ったポケモンの持ち主の山札から出す。空きがなければ、説明にしたがうピッピ・条件がたりなければ使えないとするピクシーでは選べず、条件を書かないカスミのコダックでは決められない | 既存の規定（v0.31） | v0.31 の `copy_problem` の扱い（「ぼーっとする」と同じ）と HC9 | `test_copied_search_attack` |

### 4.2 ダメージカウンターでダメージが決まる（CD）

| id | 規定 | 分類 | 根拠 | テスト |
|---|---|---|---|---|
| CD1 | じたばた: 自分のダメージカウンターの数 × 10 が基本となるダメージ（p.321 の 1 段階）。0 個なら 0 で、2 段階までで 0 以下なので計算を終える（ダメージを与えない。プラスパワーも計算しない）。弱点・抵抗力・プラスパワー・ディフェンダーはそのあと | SUPPORTED | kyuura の CR（サカキのワンリキーの「いかりのスーパーパンチ」の「おもて」: 自分のカウンターの数 × 20 が基本となるダメージ、0 個なら 0 でダメージを与えない）と p.321 の計算（エンジンの共通の処理）。じたばたはコインがないだけ | `CounterDamageTest.test_flail_counts_own_counters`・`test_flail_with_pluspower_and_zero_counters` |
| CD2 | 数えるのはダメージの要素を処理する時点の、そのポケモンにのっているカウンター（進化前からのっているものを含む） | SUPPORTED | kyuura の CR（からてチョップ: 数えるダメージカウンターは進化前からのっているものを含む） | `test_flail_counts_own_counters`（キングラー） |
| CD3 | ヨガのポーズ: 目安 20 + 相手の対戦ポケモンのカウンター × 10 が基本となるダメージ。弱点などはそのあと。自分のカウンター・自分のベンチのカウンターは数えない | CONFIRMED（文面。相手の控えにカウンターがないとき） | 印刷の文面「相手のポケモンにのっているダメージカウンター×10のダメージを追加する」とダメージの目安「20+」（p.320 の「+」） | `test_meditate_counts_the_defending_pokemon` |
| CD4 | 「相手のポケモン」が相手の対戦ポケモンか、相手の場のポケモンすべてかは決められない。相手の控えポケモンにカウンターがのっていて、読み方で基本となるダメージが変わるときは、宣言の前（こんらんのコインの前）に `UNRESOLVED_OPPONENT_POKEMON_COUNTERS` で止める | UNRESOLVED | 文面にどちらとも書かれていない（旧裏の第1弾でこの言い方はこのワザだけ。kyuura に裁定・論点・最新の説明の記録はない）。英語版の文面は使わない | `test_meditate_stops_when_the_reading_matters` |
| CD5 | どちらもコインがないので、「ダメージを受けない」状態の相手でもコインの問い（v0.4b）にならず、ダメージの要素が無効になるだけ | 既存の規定 | p.321（v0.4b） | `test_counter_damage_is_not_a_coin_effect` |

### 4.3 与えたぶん回復する（LL）

| id | 規定 | 分類 | 根拠 | テスト |
|---|---|---|---|---|
| LL1 | とりのぞく数は与えたダメージ ÷ 10 個。与えたダメージは最終ダメージ（弱点・抵抗力・プラスパワー・ディフェンダーのあと）で、相手の残りの HP で小さくしない | SUPPORTED | 印刷の文面「相手にダメージを与えたら、与えたぶんのダメージカウンターを自分からとりのぞく」。「与えたダメージ」は v0.4d の D の規定（p.319・p.321。メガドレインと同じ） | `FullDrainTest.test_heal_amount_follows_the_final_damage` |
| LL2 | のっている数より多くはとりのぞかない。のっていなければ 0 個（ログは残す） | 既存の規定 | p.320（v0.4d） | 同上（cap・no counters） |
| LL3 | 相手がきぜつしても回復する | SUPPORTED（既存） | kyuura の CR-LEECH-SEED-AFTER-KO・メガドレイン（v0.4d） | 同上（knock out） |
| LL4 | ダメージを与えなかった（最終ダメージ 0・「ダメージを受けない」状態・「とうめい」）ら回復しない | CONFIRMED・SUPPORTED（既存） | p.319（最終ダメージ 0）・v0.4b・kyuura の CR-TRANSPARENCY-DRAIN | `test_no_heal_without_damage` |
| LL5 | Z23（「ダメージを与えた後、…」）の問いにはならない（「ダメージを与えたら」は効果の条件で、メガドレイン・やどりぎのタネと同じ） | 既存の規定 | v0.17b の Z23 の範囲（`Status` の `after_damage` だけ） | `test_no_heal_without_damage`（止めない） |
| LL6 | ワザを使ったポケモンが相手の「はんげき」などで HP 以上になったら回復しない（`drain_heal_skipped`） | 既存の規定 | v0.10 の C16・kyuura の CR-SHELL-ATTACK-KO-ATTACKER-OWN-EFFECTS | `test_attacker_knocked_out_by_counterattack` |
| LL7 | メガドレインは半分（切り上げ）のまま | 既存の規定 | v0.4d | `test_mega_drain_keeps_the_half`・`CardDataTest.test_programs` |

## 5. 止める場面と残る未解決

- 新しい未解決: CD4（`UNRESOLVED_OPPONENT_POKEMON_COUNTERS`）。相手の控えにカウンターがないときは処理します。kyuura に論点がないので、研究の
  対応表では `kyuura_disposition` を `not_in_kyuura` にしています（kyuura への報告事項）。
- 既存の問いと同じもの（カードごとに登録していない）: 相手のワザとして使うときにベンチに空きがない（カスミのコダック）は HC9
  （`UNRESOLVED_COPIED_ATTACK`）。きゅうけつ・じたばた・ヨガのポーズで、ほかの既存の問い（こんらんの 20 の変更効果・同時のきぜつなど）に当たる場面は、
  既存の判定がそのまま止めます。
- 対戦（6 章）で起こった停止: 対戦準備の `UNRESOLVED_MULLIGAN_COMPENSATION`（2 局。v0.20 からの既知の未解決。デッキは変えていない）。
- 範囲外: ニドラン♂・第4弾のコイキングなど、写していないカード。
- エンジンが止める `UNRESOLVED_…` は 38 件、未解決の裁定は 39 件です。

## 6. 正式な開始からの対戦

検証用デッキ 2 つ（tools/existing_effect_games.py の `G32`: 草、`W32`: 水・超）を、互いと第2版の固定のデッキに当てる 3 組（`--batch v0.32`。
`G32` 対 `W32`・`G32` 対 `A2`・`W32` 対 `B2`）で、席を入れかえて seed 0〜5 の 36 局を進めました（tests/test_bench_search_counter_drain_v0_32_games.py。
seed を探し回っていない）。手順は v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順を重ねたもので、山札からベンチに出す
ワザの決定は元の手順のまま（1 つ目の選べるもの）です。勝率・カードの強さ・デッキの釣り合いは評価していません。

- 終わり方: 通常の勝敗 34 局・停止 2 局（`UNRESOLVED_MULLIGAN_COMPENSATION`）。手数の上限・想定外の拒否・内部エラーは 0。
- 監査: どの局も、受け付けた操作の列を `new_game` からやり直したログが同じで、不変条件・ログの監査・書き出しの監査・トレーナーのログの並びが通る。
- 止まったワザ: CD4 が 8 回（場から相手の控えにカウンターがあることを確かめてから別の操作を続けた）、既存のこんらんの 20 の変更効果が 1 回。
  ベンチに空きがなくて使えないワザ（`BENCH_FULL`）は 36 局では起こらなかった（単体テストで確かめた）。

| id | カード | 場に出た（局） | ワザ 1（回・局） | ワザ 2（回・局） | ほか |
|---|---|---|---|---|---|
| PMCG2-001 | ニドラン♀ | 56（22 局） | みだれひっかき 27・8 | なかまをよぶ 6・4 | 山札からベンチに出た 6 |
| PMCG2-002 | ナゾノクサ | 48（21 局） | しびれごな 136・14 | ふえる 25・11 | ふえる: 出した 15（うち第4弾のナゾノクサ 6）・選べるものなし 10 |
| PMCG2-005 | マダツボミ | 42（19 局） | つるのムチ 30・10 | なかまをよぶ 6・5 | 山札からベンチに出た 6 |
| PMCG3-013 | クラブ | 64（21 局） | なかまをよぶ 39・14 | はさむ 37・12 | 出した 21・選べるものなし 17 |
| PMCG2-008 | ニドリーナ | 進化 35（21 局） | ちょうおんぱ 41・13 | にどげり 37・10 | |
| PMCG2-011 | ウツドン | 進化 25（17 局） | どくのこな 42・13 | はっぱカッター 41・11 | |
| PMCG1-031 | コイキング | 52（21 局） | たいあたり 24・14 | じたばた 17・9 | じたばたの基本となるダメージ 0・10・20 |
| PMCG1-034 | ギャラドス | 進化 34（21 局） | りゅうのいかり 22・10 | バブルこうせん 12・5 | |
| PMCG3-019 | キングラー | 進化 36（19 局） | じたばた 38・11 | クラブハンマー 23・7 | じたばたの基本となるダメージ 0〜50 |
| PMCG1-048 | ルージュラ | 52（20 局） | おうふくびんた 59・16 | ヨガのポーズ 32・7 | ヨガのポーズの基本となるダメージ 20〜60 |
| PMCG2-004 | コンパン | 29（19 局） | しびれごな 15・9 | きゅうけつ 5・3 | 回復のログ 4 |
| PMCG3-002 | ズバット | 39（23 局） | ちょうおんぱ 18・6 | きゅうけつ 23・8 | 回復のログ 23 |
| PMCG3-005 | ゴルバット | 進化 23（16 局） | つばさでうつ 9・4 | きゅうけつ 5・4 | 回復のログ 5 |

## 7. 互換性と既存のカードへの影響

- 公開の API（`apply_command`・コマンド・`state_to_dict` の呼び方）は変えていません。拒否のコードは既存の `BENCH_FULL` を使います。
- 書き出しは形式 10 のままです。山札から出したポケモンの場に出た番（`played_turn`）は形式 7 から書き出し、形式 1〜6 はログの `bench_from_deck` の番で
  分かります（serialize.py の説明に加えた）。ワザの途中の決定（`resume="attack"`）は今までどおり形式 2 以上。
- ログ: `bench_from_deck`・`bench_from_deck_none` を加えました。ほかのログの形は変えていません。ログの監査（tests/log_audit.py）に、山札から出したカード
  の組み立て直し・すぐあとの `shuffle`・ワザ 1 回に 1 回まで・`drain_heal` のとりのぞく数（登録の実装との照合）を加えました。
- 既存のカード: `engine._enter_play` の本体を `zones.enter_play` に移したこと、`Drain` に `full` を加えたことのほかに、既存の処理は変えていません。
  固定した v0.31 と 1 歩ごとに比べて食い違いがないことを確かめました（8 章）。
- 研究の基準（`3f34908`）・カードの写しの元（`ecb2d69`）・固定した参照データ・公開の固定のデッキは変えていません。効果の登録表の id は
  `kyuura-engine-0.13` のままです。

## 8. 検証

| 検証 | 結果 |
|---|---|
| 新しい単体テスト（tests/test_bench_search_counter_drain_v0_32.py。30 件） | 成功。カードごとの登録の確かめ（26 のワザの型と値・名前・文面・採用の記録・研究の対応表・進化の名前の完全一致・同じ名前の別のカード・登録の確かめの拒否）、共通の仕組みの境界（選べるもの・決定の形・不正な答え・ベンチ 4 匹と 5 匹・山札 0 枚と対象なし・山札を切る乱数・こんらん・公開する情報・相手のワザとして使う・書き出し・カウンター 0 個と複数・弱点・プラスパワー・CD4 の止まる場合と隣・回復の量と上限・0 ダメージ・相手のきぜつ・はんげき・メガドレインの半分）、26 のワザ × 相手 5 × 自分のダメージ 2 × こんらん 2 × コイン 3 の先読みの方法ごとの一致（1,560 通り） |
| 正式な開始からの対戦（tests/test_bench_search_counter_drain_v0_32_games.py。36 局） | 成功（6 章） |
| 既存のテストの期待の更新 | 登録の数・一覧（tests/test_effects.py・test_cards.py・test_card_sources.py）、停止コードの一覧（test_unresolved_boundaries_v0_4e.py・test_research_links_v0_18e.py）、T19b の対象のワザ名（test_transparency_v0_9.py。既存の型の登録だけ）、自分のタイプが弱点のポケモン（test_unresolved_rulings_v0_3d.py。ルージュラ）。どれも確かめる性質は同じ |
| 固定した v0.31（`3a21551`。`tools/engine_lockstep.py tree`）と 1 歩ごとの比較（公開の API だけ。v0.32 のカードは使わない対戦） | `--corpus all --seeds 10 --stress-seeds 2 --save-every 7`（場にポケモンを出す処理をどの対戦も通る）で 290 対戦・48,092 歩、`--modules test_butterfree_games_v0_4d,test_bulbasaur_games_v0_5,test_machamp_games_v0_10 --scenarios butterfree,venusaur,venusaur_status,machamp,blastoise_mixed,alakazam_mixed --seeds 20 --stress-seeds 10 --save-every 7`（メガドレイン・やどりぎのタネの `Drain`）で 120 対戦・26,662 歩。どちらも食い違い 0・許した差 0・内部の誤り 0（作業の途中のコードと最終のコードの 2 回） |
| `python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura --check` | 「kyuura ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691 と一致しています」 |
| `python3 scripts/check_card_sources.py` | 「カードデータの採用と外部照合の記録は方針と合っています（記録 61 件）」 |
| `python3 scripts/check_research_links.py --kyuura ../kyuura` | 「研究の対応表は kyuura 3f349085645f47d0649a6cacece3680caeae50bf の記録と一致しています」 |
| `ruff check --select F,E9 .` | 問題なし（既定の規則すべてでは v0.31 と同じ 398 件。加えたファイルに新しい指摘はない） |
| `python3 tools/run_mutants.py check`（変異の定義が今のコードに入るか） | 50 件すべて ok |
| 全体のテスト（`python3 -m unittest`、最終のコード） | 9 章 |

走らせていないもの: 変異試験の全体（`run_mutants.py full`）・性能の測定・複数の Python の版での実行（どれも、具体的な理由がないので依頼のとおり走らせていない）。

## 9. 最終のコードでの全体のテスト

`python3 -m unittest`（リポジトリの直下。Python 3.13）: 2,348 件、成功 2,347・失敗 0・スキップ 1（v0.31 の 2,314 件 + 34 件。スキップは v0.31 までと
同じ 1 件）。実行時間は約 7 分 49 秒。
