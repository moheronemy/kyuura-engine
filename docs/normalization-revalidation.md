# 正規化の成立条件の再検証

[実装上の仮定の一覧](implementation-assumptions.md)で「後の版で正規化の前提が崩れた可能性がある」とした項目について、現行の処理と別の処理を比べ直しました。何が同じで何が違うか、実際の対戦に影響するかを確かめています。機能凍結の前の修正候補と、規約として判断する事項を分けるための調査です。

**今回は調査と文書化だけです。** エンジンの動作・裁定・停止の処理・規約は変えていません。ここに書く対応案は提案で、どれも採用していません。厳密モード・プレイ用モードも実装していません。

正本は台帳 [normalization-revalidation.json](normalization-revalidation.json) です。この文書の表のうち印のあるものは、`scripts/check_normalization_revalidation.py --write` が台帳から書きます。

## 1. 対象と固定した基点

| 項目 | 値 |
|---|---|
| 基点 | `2d678203db5c7fa7b9779b8746d3a873ab294351`（作業開始時の origin/main。PR #34 のマージ） |
| 元の一覧の記録 | `d620b6cfa15cb2bd975f52fb100abd7f1b401b6c`（実装上の仮定の一覧の最終コミット）。PR #34 で main に入っていて、基点と木は同じ |
| 作業ブランチ | `claude/normalization-revalidation` |
| kyuura | 読むだけ。固定研究基準 `71d1728938fb4c8fefde9b82779cdef74beb612d` で、承認の指示の文を探しました（8 章） |
| 主対象 | 元の一覧の採否判断の順序の 3 段目「前提の崩れ・食い違いのある正規化」の 20 項目 |
| 範囲を広げた項目 | 6 項目。食い違い 17 件（`premise_changed`）が指すのに 3 段目にない 5 項目と、乱数の消費を省く正規化の比較に要る 1 項目（`IA-POISON-STING-NO-COIN-ON-KO`）。理由は台帳の各項目の `scope_reason` にあります |

元の一覧の記録（項目・状態・群・集計・基点）は書き換えていません。台帳の `addenda` に、この再検証への参照だけを足しました（[implementation-assumptions.md](implementation-assumptions.md) 14 章）。

<!-- generated:counts begin（scripts/check_normalization_revalidation.py --write が台帳から書く。手で直さない） -->
| 集計 | 値 |
|---|---|
| 再検証した項目 | 26 |
| 範囲 | extended 6・primary 20 |
| 分類 | A 7・B 10・C 8・D 1 |
| 優先 | P1 8・P2 1・P3 17 |
| 推奨対応（提案。採用していない） | common_defect_candidate 2・implementation_rng_log 1・maintain_document 16・official_research 2・user_rule_decision 5 |
| 到達の確かめ方 | constructed_state 14・helper_only 5・reached_legal_ops 7 |
| 軸ごとの「違う」の項目数 | legal_actions 6・chooser 2・visible_info 6・card_movement 5・triggers_order 3・final_board_outcome 6・distribution 3・rng_consumption 3・log_save 13 |
| 再現の種類（本数） | constructed 14・helper 4・legal_ops 7・modified_impl 6 |
| 対応を付けた食い違い | 32 |
| 項目が参照するテスト（実行した・読んだだけ） | 62・2 |
| 実行したテストの指定 | 61 |
<!-- generated:counts end -->

## 2. 比較基準

各項目では、現行の処理と比べる処理を具体的に決めました。比べる処理の出所は、次の 3 つのどれかとして記録しています。

- `official_doc`: 公式資料・ルールの記述に基づくもの
- `alternative_impl`: 別の実装案
- `verification_assumption`: 検証のために置いた仮定

そのうえで、次の 9 つの軸を別々に評価しました（`same`・`differs`・`conditional`・`unknown`・`not_applicable`）。

| 軸 | 内容 |
|---|---|
| `legal_actions` | 合法な操作・選択肢 |
| `chooser` | 選択するプレイヤー |
| `visible_info` | 決定の時点で各プレイヤーに見える情報 |
| `card_movement` | カードの移動先・移動順・処理途中の状態 |
| `triggers_order` | 効果・特殊能力・きぜつなどの誘発と処理順 |
| `final_board_outcome` | 最終的な盤面・勝敗 |
| `distribution` | 結果の確率分布 |
| `rng_consumption` | 乱数の消費回数と、同じ seed の続き |
| `log_save` | ログ・観測・保存復元 |

評価の原則:

- 「同じ確率分布」と「同じ乱数列を消費する」は分けます。乱数の消費が違うだけでは、裁定上の不具合とはしません。
- 選択肢が同じでも、決定の時点で見える情報が違えば同等とはしません。移動の後の最終状態だけでは判断しません。
- 正式な処理順が分からないときは、反例が見つかっても、どちらか一方を公式の処理とはしません。
- 同等性が成り立たないことは、現行の処理が誤りであることを意味しません。

**分類:**

| 分類 | 意味 |
|---|---|
| A | 確認した範囲では同等性が成り立つ |
| B | 条件付きで成り立つ |
| C | 同等性が成り立たない |
| D | 根拠・実装・到達可能性などが不足していて未確認 |

**優先:**

| 優先 | 意味 |
|---|---|
| P0 | 正常な対戦の継続を妨げる |
| P1 | 合法な操作・非公開情報・勝敗・結果の分布に影響する |
| P2 | 特殊な組み合わせや限定条件で起こる |
| P3 | 実装方式・説明・再現性・対象外・将来の事項 |
| unknown | 影響や到達可能性を判断できない |

重大性（`severity`）・到達可能性（`reachability_level`）・確度（`confidence`）は、別の欄に記録しました。

**到達の確かめ方は区別して記録しました:**

| 記録 | 意味 |
|---|---|
| `reached_legal_ops` | `new_game` からの合法な操作列で到達した |
| `constructed_state` | 構築した盤面で確かめた（その盤面からの操作は合法な命令）。合法な操作で到達したとは書きません |
| `helper_only` | 補助関数だけで確かめた |
| `modified_impl` | 改変した比較用の処理で確かめた |

再現しなかったことを「差がない」「到達できない」とは読み替えていません。

## 3. 食い違い 17 件と主対象 20 項目の対応

前回の報告では、「前提が崩れた正規化の 20 項目」と「食い違い 17 件」を並べて書きました。この言い方は不正確でした。台帳の ID で対応させると、次のようになります。

- **17 件（`premise_changed`）は 16 項目を指します。** `IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO` には、`DISC-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO` と `DISC-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO-3` の 2 件が付いています。
- **16 項目のうち 11 項目が主対象です。** これは分類が正規化（`normalization`）の項目です。残りの 5 項目は分類が `engine_adopted` か `inference` なので、3 段目に入っていませんでした。今回は範囲を広げて扱いました。
  - `IA-THUNDERSTORM-COINS-BEFORE-DAMAGE`
  - `IA-SWIFT-EFFECTS-BY-HOLDER`
  - `IA-WARP-POINT-SG1-ONLY-WITHOUT-BENCH`
  - `IA-NAME-COUNT-EXACT-CURRENT-FORM`
  - `IA-GRUDGE-PRIZES-TAKEN-COUNT`
- **主対象 20 項目のうち残りの 9 項目は、`premise_changed` 以外の食い違いだけを持っています。**
  - `equivalence_scope`:
    - `IA-DECK-RETURN-BOTTOM-BEFORE-SHUFFLE`
    - `IA-ENERGY-CHARGE-NO-TARGET-UNUSABLE`
  - `doc_vs_code`:
    - `IA-FULL-HEAL-AGREEING-READINGS`
    - `IA-JS1-PROCEED-WHEN-READINGS-AGREE`
    - `IA-POWER-DAMAGE-WR-SKIPPED-WHEN-NO-DIFFERENCE`
    - `IA-PREFLIGHT-ENERGY-DISCARD-BY-CARD-KIND`
  - `test_gap`:
    - `IA-KO-SURVIVAL-FURTHER-DAMAGE-NOT-STOPPED`
    - `IA-LEAVE-LOCKED-OPTIONAL-SELF-SWITCH-NOT-ASKED`
  - `ledger_internal`:
    - `IA-DAMAGE-SWAP-ONE-COUNTER-PER-USE`
- **`equivalence_scope` の 5 件**のうち 4 件は主対象の項目を指し、1 件は範囲を広げた `IA-POISON-STING-NO-COIN-ON-KO` を指します。

下の表は、対象にした 32 件の食い違い（`premise_changed`・`equivalence_scope` のすべてと、主対象の項目を指すもの）の対応です。`--check` は、元の一覧のこれらの食い違いがちょうど 1 回ずつ表にあることを確かめます。あわせて、項目の対応が元の記録と同じであること、その項目の再検証があることも確かめます。

<!-- generated:mapping begin（scripts/check_normalization_revalidation.py --write が台帳から書く。手で直さない） -->
| 食い違い | 種類 | 項目 | 主対象 | 備考 |
|---|---|---|---|---|
| `DISC-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO` | premise_changed | `IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO` | ○ | 前提の崩れ（17 件の 1 つ）。再検証: IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO は C |
| `DISC-POWER-DAMAGE-WR-SKIPPED-WHEN-NO-DIFFERENCE` | doc_vs_code | `IA-POWER-DAMAGE-WR-SKIPPED-WHEN-NO-DIFFERENCE` | ○ | 文書とコードの食い違い（主対象の項目に付く）。再検証: IA-POWER-DAMAGE-WR-SKIPPED-WHEN-NO-DIFFERENCE は A |
| `DISC-POISON-STING-NO-COIN-ON-KO` | equivalence_scope | `IA-POISON-STING-NO-COIN-ON-KO` | — | 「結果が同じ」の意味が限られる。再検証: IA-POISON-STING-NO-COIN-ON-KO は B |
| `DISC-POWER-DAMAGE-WR-SKIPPED-WHEN-NO-DIFFERENCE-2` | doc_vs_code | `IA-POWER-DAMAGE-WR-SKIPPED-WHEN-NO-DIFFERENCE` | ○ | 文書とコードの食い違い（主対象の項目に付く）。再検証: IA-POWER-DAMAGE-WR-SKIPPED-WHEN-NO-DIFFERENCE は A |
| `DISC-RAIN-DANCE-ONE-CARD-PER-USE` | equivalence_scope | `IA-RAIN-DANCE-ONE-CARD-PER-USE` | ○ | 「結果が同じ」の意味が限られる。再検証: IA-RAIN-DANCE-ONE-CARD-PER-USE は C |
| `DISC-BOTH-PLAYERS-ORDER-USER-FIRST` | equivalence_scope | `IA-BOTH-PLAYERS-ORDER-USER-FIRST` | ○ | 「結果が同じ」の意味が限られる。再検証: IA-BOTH-PLAYERS-ORDER-USER-FIRST は C |
| `DISC-DECK-RETURN-BOTTOM-BEFORE-SHUFFLE` | equivalence_scope | `IA-DECK-RETURN-BOTTOM-BEFORE-SHUFFLE` | ○ | 「結果が同じ」の意味が限られる。再検証: IA-DECK-RETURN-BOTTOM-BEFORE-SHUFFLE は A |
| `DISC-POKEMON-CHECK-STEP1-2-KO-TIMING` | premise_changed | `IA-POKEMON-CHECK-STEP1-2-KO-TIMING` | ○ | 前提の崩れ（17 件の 1 つ）。再検証: IA-POKEMON-CHECK-STEP1-2-KO-TIMING は B |
| `DISC-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO-2` | wording_or_card_id | `IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO` | ○ | 言い方・カード番号の誤り（主対象の項目に付く）。再検証: IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO は C |
| `DISC-POKEMON-CHECK-STEP1-2-KO-TIMING-2` | doc_vs_code | `IA-POKEMON-CHECK-STEP1-2-KO-TIMING` | ○ | 文書とコードの食い違い（主対象の項目に付く）。再検証: IA-POKEMON-CHECK-STEP1-2-KO-TIMING は B |
| `DISC-PREFLIGHT-ENERGY-DISCARD-BY-CARD-KIND` | doc_vs_code | `IA-PREFLIGHT-ENERGY-DISCARD-BY-CARD-KIND` | ○ | 文書とコードの食い違い（主対象の項目に付く）。再検証: IA-PREFLIGHT-ENERGY-DISCARD-BY-CARD-KIND は B |
| `DISC-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO-3` | premise_changed | `IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO` | ○ | 前提の崩れ（17 件の 1 つ）。再検証: IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO は C |
| `DISC-RAIN-DANCE-ONE-CARD-PER-USE-2` | premise_changed | `IA-RAIN-DANCE-ONE-CARD-PER-USE` | ○ | 前提の崩れ（17 件の 1 つ）。再検証: IA-RAIN-DANCE-ONE-CARD-PER-USE は C |
| `DISC-TRAINER-DISCARD-AFTER-RESOLUTION` | premise_changed | `IA-TRAINER-DISCARD-AFTER-RESOLUTION` | ○ | 前提の崩れ（17 件の 1 つ）。再検証: IA-TRAINER-DISCARD-AFTER-RESOLUTION は C |
| `DISC-BOTH-PLAYERS-ORDER-USER-FIRST-2` | premise_changed | `IA-BOTH-PLAYERS-ORDER-USER-FIRST` | ○ | 前提の崩れ（17 件の 1 つ）。再検証: IA-BOTH-PLAYERS-ORDER-USER-FIRST は C |
| `DISC-DAMAGE-SWAP-ONE-COUNTER-PER-USE` | ledger_internal | `IA-DAMAGE-SWAP-ONE-COUNTER-PER-USE` | ○ | 一覧の作成中の記載の誤り（主対象の項目に付く）。再検証: IA-DAMAGE-SWAP-ONE-COUNTER-PER-USE は B |
| `DISC-ENERGY-CHARGE-NO-TARGET-UNUSABLE` | equivalence_scope | `IA-ENERGY-CHARGE-NO-TARGET-UNUSABLE` | ○ | 「結果が同じ」の意味が限られる。再検証: IA-ENERGY-CHARGE-NO-TARGET-UNUSABLE は B |
| `DISC-FULL-HEAL-AGREEING-READINGS` | doc_vs_code | `IA-FULL-HEAL-AGREEING-READINGS` | ○ | 文書とコードの食い違い（主対象の項目に付く）。再検証: IA-FULL-HEAL-AGREEING-READINGS は A |
| `DISC-HC1-NONCONFUSED-PROCEED` | premise_changed | `IA-HC1-NONCONFUSED-PROCEED` | ○ | 前提の崩れ（17 件の 1 つ）。再検証: IA-HC1-NONCONFUSED-PROCEED は C |
| `DISC-POISON-BYPASSES-DAMAGE-THRESHOLD-POWERS` | premise_changed | `IA-POISON-BYPASSES-DAMAGE-THRESHOLD-POWERS` | ○ | 前提の崩れ（17 件の 1 つ）。再検証: IA-POISON-BYPASSES-DAMAGE-THRESHOLD-POWERS は A |
| `DISC-IMMUNITY-SKIPS-STATUS-QUESTIONS` | premise_changed | `IA-IMMUNITY-SKIPS-STATUS-QUESTIONS` | ○ | 前提の崩れ（17 件の 1 つ）。再検証: IA-IMMUNITY-SKIPS-STATUS-QUESTIONS は A |
| `DISC-JS1-PROCEED-WHEN-READINGS-AGREE` | doc_vs_code | `IA-JS1-PROCEED-WHEN-READINGS-AGREE` | ○ | 文書とコードの食い違い（主対象の項目に付く）。再検証: IA-JS1-PROCEED-WHEN-READINGS-AGREE は B |
| `DISC-SINKHOLE-TIMING-AFTER-SWITCH` | premise_changed | `IA-SINKHOLE-TIMING-AFTER-SWITCH` | ○ | 前提の崩れ（17 件の 1 つ）。再検証: IA-SINKHOLE-TIMING-AFTER-SWITCH は B |
| `DISC-SWIFT-EFFECTS-BY-HOLDER` | premise_changed | `IA-SWIFT-EFFECTS-BY-HOLDER` | — | 前提の崩れ（17 件の 1 つ）。再検証: IA-SWIFT-EFFECTS-BY-HOLDER は C |
| `DISC-THUNDERSTORM-COINS-BEFORE-DAMAGE` | premise_changed | `IA-THUNDERSTORM-COINS-BEFORE-DAMAGE` | — | 前提の崩れ（17 件の 1 つ）。再検証: IA-THUNDERSTORM-COINS-BEFORE-DAMAGE は C |
| `DISC-WARP-POINT-SG1-ONLY-WITHOUT-BENCH` | premise_changed | `IA-WARP-POINT-SG1-ONLY-WITHOUT-BENCH` | — | 前提の崩れ（17 件の 1 つ）。再検証: IA-WARP-POINT-SG1-ONLY-WITHOUT-BENCH は A |
| `DISC-NAME-COUNT-EXACT-CURRENT-FORM` | premise_changed | `IA-NAME-COUNT-EXACT-CURRENT-FORM` | — | 前提の崩れ（17 件の 1 つ）。再検証: IA-NAME-COUNT-EXACT-CURRENT-FORM は B |
| `DISC-GRUDGE-PRIZES-TAKEN-COUNT` | premise_changed | `IA-GRUDGE-PRIZES-TAKEN-COUNT` | — | 前提の崩れ（17 件の 1 つ）。再検証: IA-GRUDGE-PRIZES-TAKEN-COUNT は B |
| `DISC-BERRY-BATCH-NO-INTERMEDIATE-CHECK` | premise_changed | `IA-BERRY-BATCH-NO-INTERMEDIATE-CHECK` | ○ | 前提の崩れ（17 件の 1 つ）。再検証: IA-BERRY-BATCH-NO-INTERMEDIATE-CHECK は B |
| `DISC-KO-SURVIVAL-FURTHER-DAMAGE-NOT-STOPPED` | test_gap | `IA-KO-SURVIVAL-FURTHER-DAMAGE-NOT-STOPPED` | ○ | テストの欠け（主対象の項目に付く）。再検証: IA-KO-SURVIVAL-FURTHER-DAMAGE-NOT-STOPPED は D |
| `DISC-LEAVE-LOCKED-OPTIONAL-SELF-SWITCH-NOT-ASKED` | test_gap | `IA-LEAVE-LOCKED-OPTIONAL-SELF-SWITCH-NOT-ASKED` | ○ | テストの欠け（主対象の項目に付く）。再検証: IA-LEAVE-LOCKED-OPTIONAL-SELF-SWITCH-NOT-ASKED は C |
| `DISC-RX1-NOT-ASKED-WITHOUT-LATER-DAMAGE` | premise_changed | `IA-RX1-NOT-ASKED-WITHOUT-LATER-DAMAGE` | ○ | 前提の崩れ（17 件の 1 つ）。再検証: IA-RX1-NOT-ASKED-WITHOUT-LATER-DAMAGE は A |
<!-- generated:mapping end -->

## 4. 全項目の結果

軸の欄の記号:

| 記号 | 意味 |
|---|---|
| 同 | same |
| **違** | differs |
| 条件 | conditional |
| ? | unknown |
| — | not_applicable |

推奨は提案で、採用していません。各項目の現行の処理、比べる処理、成立条件、後から加わったカード・機能、軸ごとの説明と確度、再現の手順と結果、未確認の内容は、台帳にあります。

<!-- generated:results begin（scripts/check_normalization_revalidation.py --write が台帳から書く。手で直さない） -->
| 項目 | 範囲 | 分類 | 優先 | 合法な操作 | 選択するプレイヤー | 決定の時点で各プレイヤーに見える情報 | カードの移動先 | 効果 | 最終的な盤面 | 結果の確率分布 | 乱数の消費回数と、同じ seed の続き | ログ | 到達 | 推奨（提案） |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `IA-SINKHOLE-TIMING-AFTER-SWITCH` | primary | B | P1 | **違** | **違** | 条件 | **違** | **違** | **違** | 条件 | 同 | **違** | reached_legal_ops | official_research |
| `IA-BOTH-PLAYERS-ORDER-USER-FIRST` | primary | C | P1 | 同 | 同 | **違** | 同 | — | 条件 | 条件 | **違** | **違** | constructed_state | user_rule_decision |
| `IA-HC1-NONCONFUSED-PROCEED` | primary | C | P1 | 同 | 同 | 条件 | **違** | 条件 | **違** | **違** | 同 | **違** | constructed_state | common_defect_candidate |
| `IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO` | primary | C | P1 | **違** | 同 | **違** | 同 | 同 | 条件 | 条件 | 同 | **違** | reached_legal_ops | common_defect_candidate |
| `IA-RAIN-DANCE-ONE-CARD-PER-USE` | primary | C | P1 | **違** | 同 | **違** | **違** | **違** | **違** | 同 | 同 | **違** | constructed_state | user_rule_decision |
| `IA-SWIFT-EFFECTS-BY-HOLDER` | extended | C | P1 | 同 | — | 同 | **違** | 同 | **違** | — | 同 | 条件 | constructed_state | user_rule_decision |
| `IA-THUNDERSTORM-COINS-BEFORE-DAMAGE` | extended | C | P1 | 同 | 同 | **違** | 条件 | 条件 | **違** | **違** | 同 | **違** | reached_legal_ops | user_rule_decision |
| `IA-TRAINER-DISCARD-AFTER-RESOLUTION` | primary | C | P1 | **違** | 同 | 条件 | **違** | ? | **違** | **違** | **違** | **違** | reached_legal_ops | user_rule_decision |
| `IA-LEAVE-LOCKED-OPTIONAL-SELF-SWITCH-NOT-ASKED` | primary | C | P2 | **違** | **違** | 同 | 同 | 条件 | 条件 | 条件 | 条件 | **違** | constructed_state | official_research |
| `IA-DECK-RETURN-BOTTOM-BEFORE-SHUFFLE` | primary | A | P3 | 同 | 同 | 同 | 条件 | 同 | 条件 | 同 | 同 | 条件 | reached_legal_ops | maintain_document |
| `IA-FULL-HEAL-AGREEING-READINGS` | primary | A | P3 | 同 | 条件 | 同 | 同 | 同 | 同 | 同 | 同 | 条件 | reached_legal_ops | maintain_document |
| `IA-IMMUNITY-SKIPS-STATUS-QUESTIONS` | primary | A | P3 | 同 | — | 同 | 同 | 同 | 同 | 同 | 同 | 条件 | helper_only | maintain_document |
| `IA-POISON-BYPASSES-DAMAGE-THRESHOLD-POWERS` | primary | A | P3 | — | — | 同 | 同 | 同 | 同 | 同 | 同 | 同 | constructed_state | maintain_document |
| `IA-POWER-DAMAGE-WR-SKIPPED-WHEN-NO-DIFFERENCE` | primary | A | P3 | 同 | 同 | 同 | 同 | 同 | 同 | 同 | 同 | 同 | constructed_state | maintain_document |
| `IA-RX1-NOT-ASKED-WITHOUT-LATER-DAMAGE` | primary | A | P3 | 同 | 同 | 同 | 同 | 同 | 同 | 同 | 同 | 同 | constructed_state | maintain_document |
| `IA-WARP-POINT-SG1-ONLY-WITHOUT-BENCH` | extended | A | P3 | 同 | 同 | 同 | 同 | 同 | 同 | — | — | 同 | constructed_state | maintain_document |
| `IA-BERRY-BATCH-NO-INTERMEDIATE-CHECK` | primary | B | P3 | — | — | — | 条件 | 条件 | 条件 | 同 | 同 | 条件 | helper_only | maintain_document |
| `IA-DAMAGE-SWAP-ONE-COUNTER-PER-USE` | primary | B | P3 | 同 | 同 | 同 | 同 | 同 | 同 | 同 | 同 | **違** | constructed_state | maintain_document |
| `IA-ENERGY-CHARGE-NO-TARGET-UNUSABLE` | primary | B | P3 | **違** | 同 | **違** | 同 | 同 | 同 | 同 | 同 | **違** | constructed_state | maintain_document |
| `IA-GRUDGE-PRIZES-TAKEN-COUNT` | extended | B | P3 | 同 | — | 同 | 同 | — | 条件 | 条件 | 同 | 同 | helper_only | maintain_document |
| `IA-JS1-PROCEED-WHEN-READINGS-AGREE` | primary | B | P3 | 同 | 同 | 同 | 同 | 同 | 同 | 同 | 同 | 条件 | helper_only | maintain_document |
| `IA-NAME-COUNT-EXACT-CURRENT-FORM` | extended | B | P3 | 同 | — | — | 同 | — | 条件 | 同 | 同 | 同 | helper_only | maintain_document |
| `IA-POISON-STING-NO-COIN-ON-KO` | extended | B | P3 | 条件 | 条件 | **違** | 同 | 同 | 条件 | 同 | **違** | **違** | reached_legal_ops | implementation_rng_log |
| `IA-POKEMON-CHECK-STEP1-2-KO-TIMING` | primary | B | P3 | 条件 | — | 条件 | 条件 | 条件 | 条件 | 条件 | 同 | **違** | constructed_state | maintain_document |
| `IA-PREFLIGHT-ENERGY-DISCARD-BY-CARD-KIND` | primary | B | P3 | 同 | 同 | 同 | 同 | 同 | 同 | 同 | 同 | 同 | constructed_state | maintain_document |
| `IA-KO-SURVIVAL-FURTHER-DAMAGE-NOT-STOPPED` | primary | D | P3 | ? | — | ? | ? | **違** | 条件 | ? | 条件 | **違** | constructed_state | maintain_document |
<!-- generated:results end -->

## 5. 重要な反例

「統括の再実行」と書いた反例は、調査担当の再現スクリプトを統括が実行し直し、報告どおりの差が出ることを見たものです。スクリプトは作業のスクラッチ領域にあり、リポジトリには入れていません。手順・seed・構成は台帳の `repro` にあります。

### 5.1 同時のきぜつでサイドを取る順番と、表向きのサイド（`IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO`。C・P1）

**再現:** `new_game` からの合法な操作列で到達しました（統括の再実行）。

| 項目 | 内容 |
|---|---|
| seed | 473 |
| P0 のデッキ | コイル PMCG1-036 ×4、ロケット団参上! PMCG4-062 ×4、雷 ×52 |
| P1 のデッキ | コラッタ PMCG1-060 ×4、水 ×56 |
| 操作 | P0 は 3 番目の番に、ロケット団参上! を使ってからじばくを使う。両方のバトル場がきぜつする |

**決定の時点の観測:** 現行の順は、番のプレイヤー（P0）が先に取ります。

1. P0 は、表向きのロケット団参上! を位置 3 から取ります。
2. その後に P1 の `take_prize` の決定が出ます。このとき P1 の `visible_log` には、P0 の `take_prize` が見えています（カード uid 5、`face_up=['card']`）。P0 の残りのサイドがすべて雷であることも分かっています。
3. 逆の順（比較用の改変処理）では、P0 が P1 の取った水を見てから選びます。

**同じ点:** 同じ選択の組なら、カードの動き・乱数・勝敗は同じです。

**意味:** v0.2f 5 章は、正規化の理由の一つに「後に取るプレイヤーが使える情報は増えない」を挙げています。前提は「サイドを見る・表にするカードがない」ことでした。v0.63 から、この理由と前提が成り立ちません。サイドがすべて裏の盤面に限れば同等です。

**元の文書の指定:** 同じ章は「成り立たなければ p.325 の選択（番のプレイヤーが順番を選ぶ決定）を実装します」と書いています。

**未確認:** 後の選択が先に取られたカードを見て実際に変わる盤面の例は、作っていません。この seed の P1 のサイドはすべて水で、どれを選んでも差が出ません。

### 5.2 トラッシュに置く時点とトラッシュ交換（`IA-TRAINER-DISCARD-AFTER-RESOLUTION`。C・P1）

**現行の読み方:** 使っているトレーナーは `trainer_in_use` にあり、トラッシュにありません。これは結果の同じ正規化ではなく、読み方の選択です。`TakeFromDiscardTrainer.decision_problems` は「使っているカード自身を選べる」状態を不整合として扱い、この読み方を強制しています。

**時点で結果が変わるカード（登録済み）:**
- トラッシュ交換 PMCG6-077
- リサイクル PMCG3-047（再録 GD4-025）
- ダウジングマシーン PMCG1-087
- ボロのつりざお neo3-053（コードを読んだだけ）
- ナツメのサイキックコントロール PMCG6-088 の外側のカード（コードを読んだだけ）

**再現:** seed 1 の先攻 1 番目で、トラッシュは 0 枚です。`new_game` からの合法な操作で到達しました。比べる処理は、説明の前にトラッシュに置く改変処理です（統括の再実行）。

| カード | 現行 | 比べる処理 |
|---|---|---|
| トラッシュ交換 | 0 枚と数え、このカードはトラッシュに置かれる | 1 枚と数え、このカードは山札にもどり、ビリリダマ PMCG1-037 がトラッシュに置かれる。山札の並びと乱数の状態も違う |
| リサイクル | `UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET` で使えない | 自分だけを選べる |
| ダウジングマシーン | 選べるのは PMCG6-077・PMCG3-047 | 自分（PMCG1-087）も選べる |

### 5.3 あまごいを 1 枚ずつ使う（`IA-RAIN-DANCE-ONE-CARD-PER-USE`。C・P1）

v0.6 の前提は「つけたことで何かが起こることはない」でした。次の 2 つのカードで、この前提が成り立ちません。どちらも構築盤面で確かめました（統括の再実行）。

**ユンゲラーのエナジーショック（ES3-020・QSG-027。v0.116）:**
- 受けた側のバトル場のカメックスに、あまごいで 1 枚つけるとマヒします。2 回目の使用は `POKEMON_PARALYZED` で拒否されます。
- 印刷の文面「1度に何枚でも」を、1 回の使用で複数枚つけると読むと、2 枚つけられます。この終わりの状態には、今は到達できません。

**わるいデンリュウの［かんでん］（neo4-046。v0.86）:**
- 1 枚ごとに 10 ダメージで、使用のあいだにきぜつとサイドの決定が入ります。使うプレイヤーは、その結果を見てから次の先を選びます。
- まとめて同じポケモンに 2 枚つける読み方では、`UNRESOLVED_REACTION_AFTER_KNOCKOUT` で止まります。

**未確認:** `new_game` からの操作列は組んでいません。

### 5.4 両方のプレイヤーの処理を、使ったプレイヤーから行う（`IA-BOTH-PLAYERS-ORDER-USER-FIRST`。C・P1）

HD1 は「乱数の順だけが違う」と説明しています。各プレイヤーが選ぶ処理には、この説明が当てはまりません。構築盤面と合法な命令で確かめました（統括の再実行）。

- **タイムカプセル（neo1-091）:** 相手の決定の時点で、使ったプレイヤーが山札にもどしたカードがトラッシュから消え、山札が 1 枚増えていることが相手に見えます。
- **ポケモンマーチ（neo1-076）:** 相手は、使ったプレイヤーがベンチに出したポケモンを見てから選びます。

順を入れ替えると、ポケモンマーチは切る順が変わり、同じ seed で山札の並びが変わります。乱数の消費の回数は同じです。

### 5.5 サンダーストームと［ベンチガード］（`IA-THUNDERSTORM-COINS-BEFORE-DAMAGE`。C・P1。範囲を広げた項目）

**情報の差:** コインの面と乱数の割り当ては、どちらの読み方でも同じです。ただし現行は、すべてのコインを先に投げ、公開のログ `bench_coin_results` を残してから、控えにダメージを与えます。そのため最初の［ベンチガード］の決定の時点で、決めるプレイヤーには後のコインの結果も見えています。1 匹ずつ投げる読み方では、まだ投げていません。

**合法な対戦での到達:** 固定デッキ Z60 対 R65 の `new_game` からの対戦で、観測した 13 回の決定のうち 11 回で、2 枚以上のおもてが決める前に見えていました。

**結果の差（構築盤面。統括の再実行）:** 控えは X（残り 20）・タケシのサイドン（残り 20）・Y（残り 20）で、コインは おもて・うら・おもて です。答えによって、きぜつするのは「サイドン」「Y」「X」「X と Y」のどれかになります。「Y もおもてのときだけ X を見捨てる」という方針は、現行の読み方でしかとれません。

**同じ形のワザ（コードを読んだだけ）:**
- わるいクロバット neo4-012
- バンギラス neo2-042（両方のベンチ。ワザを使う側のサイドンも、すべてのコインを見て決める）
- わるいリングマ neo4-096

1 匹ずつの比較処理は作っていません。

### 5.6 スピードスターの効果を持ち主で分ける（`IA-SWIFT-EFFECTS-BY-HOLDER`。C・P1。範囲を広げた項目）

構築盤面で確かめました（統括の再実行）。

1. 相手のチコリータ（PF1-001）が、タケシのサンドパンに「なきごえ」を使います。−10 の効果を持っているのはサンドパンで、与えたのはチコリータです。
2. サンドパンがスピードスターを使います。

| 読み方 | ダメージ |
|---|---|
| 持っているのがだれかで分ける（現行） | 10 |
| 与えたのがだれかで分ける | 20 |

SS1 はこの違いでは止まりません。SS1 自体は v0.97 のアンノーン[N] から起こります。v0.60 文書の「起こらない」という記述は古いままです。

### 5.7 HC1 を、こんらんでなければ聞かない（`IA-HC1-NONCONFUSED-PROCEED`。C・P1）

構築盤面から合法な命令で確かめました（統括の再実行）。

**場面:** こんらんでないミュウツー（PMCG1-050）が、前の番に相手のサンド（PMCG1-051）の「すなかけ」を受けています。ミュウツーがバリアーを宣言し、手順 4 のコインがうらでした。

| 読み方 | 結果 |
|---|---|
| 現行 | 止めずにワザが失敗し、エネルギーは 2 個のまま。「効果」の読み方を黙って採っている |
| トラッシュを「ワザを使うための条件」と読む | 宣言のときに 1 個トラッシュする |

こんらんなら、同じ場面で `UNRESOLVED_DISCARD_ENERGY_TIMING` で止まります。

**原因:** `DiscardOwnEnergy.on_declare` は、こんらんと、v0.114 からのベイビィのコインだけを確かめています。手順 4 のコイン（`AttackCoinCheck`・［はんこう］）は確かめていません。

**同じ形:** エネループ（v0.42）と、フーディン PR1-055 のトランスダメージ（v0.116）も同じ形です（コードを読んだだけ）。

### 5.8 どくばりで、きぜつした相手にコインを投げない（`IA-POISON-STING-NO-COIN-ON-KO`。B・P3。範囲を広げた項目）

**同じもの:** そのワザの後の盤面と、対戦の結果の分布は同じです。

**違うもの:** 乱数の消費が 1 回少なく、同じ seed の続きが変わります。

**合法な対戦での比較:** `WEEDLE_DECK` 対 `WEEDLE_DECK_B` を、方針 `poison_policy_command` で seed 0〜299 の 300 局、`new_game` から対戦させました。
- どくばりで相手がきぜつする対戦は 129 局で、そのうち 12 局で勝者が変わります（例: seed 17）。
- 全体の勝敗は、現行が P0 201・P1 99、投げる読み方が 195・105 です。12 局は 9 対 3 で、偏りとは言えません。
- 現行の操作列を投げる読み方に当てると、seed 0・1・7・17 では途中で合法でなくなります（統括の再実行で seed 0 は WRONG_PHASE）。

**合法な操作の差:** ナツメのESP があると、投げる読み方では `ESP_REDO` の決定が増えます（構築盤面）。

これは裁定上の不具合ではなく、乱数の割り当てと再現性の問題として記録します。

### 5.9 そのほかの注意点

- **［おとしあな］と［ベンチガード］（`IA-SINKHOLE-TIMING-AFTER-SWITCH`。B・P1）**
  - 進めるのは、こんらんでなく、量の比較で差がなく、使える［ベンチガード］がない場合だけです。その範囲では、時点によらず結果は同じです。
  - ［ベンチガード］がある場面は、`UNSUPPORTED_BENCH_GUARD_OUTSIDE_ATTACK` で「にげる」を受け付けません。
  - **到達の確認:** 固定デッキ G61 対 R65 の `new_game` からの対戦で、途中の状態の写しに「にげる」を当てました。81 回この停止で拒否されました（数えたのは試した回数で、対戦の数ではありません。統括は記録を読んだだけで、実行し直していません）。
  - **改変での確認:** この停止を外すと、エンジンは決定を出さずに 20 をにげたポケモンに置き、入れ替えの後の読み方を黙って当てはめました。
- **きぜつを防いだ後のダメージ（`IA-KO-SURVIVAL-FURTHER-DAMAGE-NOT-STOPPED`。D）**
  - 文書は、返す効果のダメージを「止めない例」に挙げています。現行のコードは、別の場所（`kernel._damage_source`）で KS1 で止めます。
  - 改変で確かめると、返す効果のダメージは読み方で処理が変わります。止める現行の処理のほうが、文書の例より妥当です。
  - 正規化の本体の経路に到達する盤面は作れていません。

## 6. 修正候補と規約の判断候補（提案。採用していない）

### 6.1 両モード共通の修正候補（`common_defect_candidate`）

| 項目 | 根拠 | 提案の内容 |
|---|---|---|
| `IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO` | 表向きのサイドで、後に選ぶ側が先に取られたカードを見られる（合法な対戦で確認）。元の文書 v0.2f 5 章自身が「成り立たなければ p.325 の選択を実装」と書いている | p.325 の「番のプレイヤーが順番を選ぶ」決定を出す。少なくとも、表向きのサイドがある場面では正規化を使わない |
| `IA-HC1-NONCONFUSED-PROCEED` | 手順 4 のコインがある場面で、研究の論点（HC1）の一方の読み方を黙って採っている。こんらんとベイビィのコインには止める処理を広げているのに、手順 4 のコインには広げていない（一貫しない） | 手順 4 のコインがある場面でも HC1 で止める（エネループ・トランスダメージを含む） |

### 6.2 規約として利用者の判断が必要（`user_rule_decision`）

どれも公式資料で処理順・読み方が決まりません。現行は一方を選んでいます。厳密モードでは止めるか選ばせるか、プレイ用モードでは今の読み方を続行規約にするか、を決める必要があります。

| 項目 | 判断する点 |
|---|---|
| `IA-TRAINER-DISCARD-AFTER-RESOLUTION` | 使っているトレーナーを、トラッシュを数える・選ぶ処理に含めるか（トラッシュ交換・リサイクル・ダウジングマシーン・ボロのつりざお） |
| `IA-RAIN-DANCE-ONE-CARD-PER-USE` | あまごいを 1 回 1 枚と読むか、1 回で複数枚と読むか（エナジーショック・［かんでん］で結果が変わる） |
| `IA-BOTH-PLAYERS-ORDER-USER-FIRST` | 両方が選ぶ処理で、だれが先に選ぶか。相手の選択を見てから選んでよいか（タイムカプセル・ポケモンマーチ。［ENGAGE］などは列挙だけ） |
| `IA-THUNDERSTORM-COINS-BEFORE-DAMAGE` | すべてのコインを先に投げて公開するか、1 匹ずつ投げて処理するか（［ベンチガード］の決定時点の情報） |
| `IA-SWIFT-EFFECTS-BY-HOLDER` | スピードスターが計算しない効果を、持っているのがだれかで分けるか、与えたのがだれかで分けるか |

### 6.3 公式情報の追加調査が必要（`official_research`）

| 項目 | 調べる点 |
|---|---|
| `IA-SINKHOLE-TIMING-AFTER-SWITCH` | ［おとしあな］のダメージが入れ替えの前か後か（SH1 の論点）。未対応の停止を実装しても、この時点の問いは残る。今は通常の対戦で「にげる」が使えない場面がある |
| `IA-LEAVE-LOCKED-OPTIONAL-SELF-SWITCH-NOT-ASKED` | ［にげこむ］（PMCG5-033）の「そのとき、このカードは…「ダメージ以外の効果」を受けない」が、入れ替えられないときもはたらくか。はたらくなら、聞かない現行の処理では結果が変わる（構築盤面）。はなれられない効果が相手のワザの時点にはたらく合法な経路は見つけていない（見つけていないだけで、ないとは確かめていない） |

### 6.4 実装方式・乱数の再現性・ログの問題（`implementation_rng_log`）

| 項目 | 内容 |
|---|---|
| `IA-POISON-STING-NO-COIN-ON-KO` | 分布は同じで、乱数の消費と同じ seed の続き、公開のログ、固定の参照データ（`GoldenPoisonGameTest`）が違う。ナツメのESP で決定の数も違う。モードの設計で「同じ seed の再現」を何の単位で保証するかと合わせて扱う |

### 6.5 現行を維持し、成立条件の説明を補う（`maintain_document`）

16 項目です。成立条件は 7 章にまとめました。記述が今のコードと合っていない文書があります（直していません）:

- `pokemon_check_poison` の docstring が v0.78 の記述のまま（`IA-POKEMON-CHECK-STEP1-2-KO-TIMING`）
- v0.46 文書の「どくの処理は通していない」（`IA-POISON-BYPASSES-DAMAGE-THRESHOLD-POWERS`）
- v0.60・v0.61 文書の「コードのない問い」。Z9・SS1 には停止コードがある（`IA-POWER-DAMAGE-WR-SKIPPED-WHEN-NO-DIFFERENCE`・`IA-SWIFT-EFFECTS-BY-HOLDER`）
- v0.55 文書の FH2 が、v0.72 のコードの FH2（`UNRESOLVED_FULL_HEAL_WITHOUT_CONDITION`）と別のものを指している（`IA-FULL-HEAL-AGREEING-READINGS`）
- v0.106・v0.88 文書の名前の数え方（`IA-NAME-COUNT-EXACT-CURRENT-FORM`）、サイドの取った数（`IA-GRUDGE-PRIZES-TAKEN-COUNT`）
- きぜつを防いだ後の返す効果の例（`IA-KO-SURVIVAL-FURTHER-DAMAGE-NOT-STOPPED`）

## 7. 維持できる正規化と成立条件

確認した範囲での結論です。条件は台帳の `conditions_for_equivalence` にあります。

**A: 確認した範囲では同等性が成り立つ**

| 項目 | 確認した範囲・条件 |
|---|---|
| `IA-RX1-NOT-ASKED-WITHOUT-LATER-DAMAGE` | v0.124 の姿の固定で、ワザの処理中は `ForceSwitch._form_changes` がいつも () を返す。置き換わったことを確認した（`DragOutTransformTest`） |
| `IA-DECK-RETURN-BOTTOM-BEFORE-SHUFFLE` | もどす処理の呼び出し 26 か所で、同じ効果の中で切る。違いは、同じ seed で切った後の並びだけ（v0.24 の PT7 に書かれた範囲） |
| `IA-FULL-HEAL-AGREEING-READINGS` | 自分のバトル場だけが特殊状態のとき。合法な対戦で到達した（seed 1）。ベンチの特殊状態は不変条件で除かれる |
| `IA-POISON-BYPASSES-DAMAGE-THRESHOLD-POWERS` | 今の写しで作れるどくの量（10・20・倍で 20）は、しきい値 30 より小さい。量が変わるときは KA1 で止める |
| `IA-POWER-DAMAGE-WR-SKIPPED-WHEN-NO-DIFFERENCE` | 色が当たらなければ、量は変わらない。当たる場面は 4 つの経路すべてで Z9 で止める（3 つは止めすぎの方向） |
| `IA-IMMUNITY-SKIPS-STATUS-QUESTIONS` | どの読み方でも特殊状態にならない。v0.84 きらめきタッチ・v0.85 しんぴのこなも 4 つの状態をすべて防ぐ。実行したのは TP3 だけ |
| `IA-WARP-POINT-SG1-ONLY-WITHOUT-BENCH` | 使ったプレイヤーのバトル場がベンチにもどる場合。もどらない場合（v0.93・v0.117）はコードが止める。v0.93 は構築盤面で確認した |

**B: 条件付きで成り立つ**

| 項目 | 条件 |
|---|---|
| `IA-POKEMON-CHECK-STEP1-2-KO-TIMING` | v0.79 の訂正（PK1）がコードに入っている。比べる問い合わせの範囲で差がないとき。きぜつで誘発する効果は比べていない |
| `IA-GRUDGE-PRIZES-TAKEN-COUNT` | サイドの枚数を変えるのが「取る」と「にせオーキドの発明」の置き直しだけであること。延長戦で前の区間を数えないのは v0.134 の読み方 |
| `IA-PREFLIGHT-ENERGY-DISCARD-BY-CARD-KIND` | 種類で束ねる鍵に入らない、カードごとの状態（色の変化・持ち主の変化）が、ポケモンごとの問いで先に止まること |
| `IA-ENERGY-CHARGE-NO-TARGET-UNUSABLE` | 結果（盤面・分布・乱数）に限る。宣言を受け付けるかという合法な操作の集合と、公開のログは違う |
| `IA-DAMAGE-SWAP-ONE-COUNTER-PER-USE` | ログの粒度を比べない（小さい盤面で、到達できる配り方が全探索で一致した）。調査担当は A としたが、統括が B に補正した |
| `IA-BERRY-BATCH-NO-INTERMEDIATE-CHECK` | v0.82 から、影響するきのみは並べ方を比べる。残りをまとめる処理は、`_berry_view` が問い合わせの変化を覆う場合に成り立つ。トラッシュとログの並びは違う |
| `IA-NAME-COUNT-EXACT-CURRENT-FORM` | 対象の 4 効果の名前に「メタモン」が入らない |
| `IA-SINKHOLE-TIMING-AFTER-SWITCH` | 使える［ベンチガード］がない（ある場面は未対応で止める。6.3） |
| `IA-JS1-PROCEED-WHEN-READINGS-AGREE` | 比べられない計算は比べずに、`deal_damage` の停止に任せている |

## 8. 承認記録の補完（タッチ交代・カードトレーナー認定証）

利用者が示した指示の文:

> タッチ交代とカードトレーナー認定証の3枚については非対戦カードに移管します

**現物との照合:** `kyuura_engine/data/kyuura_cards.json` の `catalog_scope.excluded_records` と、ID・名前を照合しました。指示の「タッチ交代」は 2 枚、「カードトレーナー認定証」は 1 枚で、合わせて 3 枚です。

| ID | 名前 | 目録の分類 | 使用範囲 |
|---|---|---|---|
| PR1-038 | タッチ交代！ | special_rule | kangaskhan_rule |
| PRN-048 | タッチ世代交代！ | special_rule | kangaskhan_rule |
| PR1-079 | カードトレーナー認定証 | award | standard |

**指示の文の記録:** このリポジトリ（docs・scripts・kyuura_engine）にも、kyuura の固定研究基準 `71d1728` にも、この指示の文は見つかりませんでした。元の一覧の時点では、引用が収録されていなかったことになります。指示が出た日も確かめていません。v0.128 文書は「kyuura 側の記録は 2026-10-31」と書いています。

該当する台帳の項目は `IA-DATA-CATALOG-SCOPE-EXCLUSIONS` の 1 つです。その中身を次のように分けました。

| 区分 | 内容 |
|---|---|
| **承認の引用が未収録**（`quote_missing`） | 3 枚を非対戦カードとし、通常対戦のエンジンの実装の対象から外すこと |
| **承認そのものがない**（`no_approval`） | 対象外を kyuura の目録の分類の欄（`catalog_class`・`engine_scope`・`engine_scope_reason`）で決める方式と、分類の名前 |
| 同上 | 写しの `catalog_scope.excluded_records`・`cards.ScopeExclusion` の記録の形と、ID・理由の文の設計 |
| 同上 | デッキに入れると `deck.deck_problems` が `OUT_OF_ENGINE_SCOPE` で理由をつけて拒否する、という扱い（拒否以外の扱いとの選択は、指示に書かれていない） |

この指示が承認しているのは、3 枚の移管だけです。周辺の分類方式・ID の設計・拒否の仕方・そのほかの仮定は、承認済みにしていません。

元の一覧の項目の `approval` は、元の調査時点の記録として書き換えていません。補完は台帳の `approval_supplement` と、元の一覧の追記 `ADD-CATALOG-SCOPE-APPROVAL-QUOTE` に記録しました。採否と基礎集合での扱いは、判断事項 DEC-CARD-DATA-CORRECTIONS のままです。

## 9. 未確認の事項と調査範囲の限界

- **合法な操作列で到達したのは 7 項目だけです（`IA-GRUDGE-PRIZES-TAKEN-COUNT` は、調査担当が合法な操作の到達と記録しましたが、ワザを使わずに補助関数で値を求めていたので、統括が補助関数に補正しました）。** 残りは次のとおりです。
  - 構築盤面: 14 項目
  - 補助関数だけ: 5 項目
  - 次の反例は、構築盤面だけで確かめました。`new_game` からは再現していません。
    - あまごい
    - 両方のプレイヤーの順
    - スピードスター
    - HC1
    - ［にげこむ］
- **実際に結果が変わる例を作っていないものがあります。** 表向きのサイドで、後の選択が先に取られたカードを見て実際に変わる例は、作っていません。
- **比較処理を作っていないものがあります。** サンダーストームの 1 匹ずつの比較処理は作っていません。同じ形のほかのワザ（わるいクロバット・バンギラス・わるいリングマ）は、コードを読んだだけです。
- **一部しか比べていないものがあります。**
  - トラッシュの時点: ボロのつりざお・ナツメのサイキックコントロール・GD4-025 は、コードを読んだだけです。
  - 両方のプレイヤーの順: ［ENGAGE］・ふしぎなかおり・しんかのうた・おくりものは、列挙しただけです。
  - トラッシュを読むトレーナーの列挙は、文字列の検索に頼っています。共通の関数を通る型を見落としている可能性があります。
- **到達の経路を見つけていないものがあります。**
  - `IA-KO-SURVIVAL-FURTHER-DAMAGE-NOT-STOPPED`: 正規化の本体の経路に到達する盤面を作れていないので、分類は D です。
  - ［にげこむ］: はなれられない効果が相手のワザの時点にはたらく合法な経路は、見つけていません。見つけていないだけで、ないとは確かめていません。
- **公式資料は読み直していません。** 新しい画像取得・OCR もしていません。比べる処理の多くは別の実装案か検証用の仮定で、公式の処理として比べたものではありません。
- **調査は 5 つの調査担当に分けました。** 統括が自分で行ったのは次のことです。
  - 主な反例 8 項目の再現スクリプトの再実行（各項目の `lead_check`）
  - 項目が参照するテストの実行
  - 分類の補正 1 件（`IA-DAMAGE-SWAP-ONE-COUNTER-PER-USE`）、推奨の補正 1 件（`IA-SINKHOLE-TIMING-AFTER-SWITCH`）、到達の確かめ方の補正 1 件（`IA-GRUDGE-PRIZES-TAKEN-COUNT`）

  それ以外の軸の評価は、調査担当の確認のままです。
- **再現スクリプトはリポジトリに入れていません。** 比較用の改変処理を含むため、作業のスクラッチ領域に置きました。手順・seed・構成・期待する差・結果は台帳の `repro` にあります。

## 10. 検証

| 検証 | 内容 |
|---|---|
| 再検証の台帳 | `python scripts/check_normalization_revalidation.py --check`。確かめること: ID の一意性と、元の一覧にあること。主対象 20 項目がすべてあり、範囲を広げた項目に理由があること。対象の食い違いがちょうど 1 回ずつ、元の記録と同じ項目で対応していること。9 つの軸の有無と値。分類と軸の評価が矛盾しないこと。合法な操作で到達したと書く項目が、合法な操作列の再現を持つこと。実行したと書くテストが実行の記録にあること。コードの名前とテストの名前があること。範囲を添えない「問題なし」「網羅」「到達不能」がないこと。承認の補完の 3 枚が写しと名前まで一致し、承認の範囲が 3 枚の外に及ばないこと。集計と表 |
| 元の一覧 | `python scripts/check_implementation_assumptions.py --check`（追記の ID・種類・参照先・項目）と `--sites`（候補箇所の差。再検証の文書・検査・テストは、一覧から派生した文書として走査から除いた） |
| 停止の方針の台帳 | `python scripts/build_stop_policy_classification.py --check` |
| 単体テスト | `tests/test_normalization_revalidation.py`。台帳を壊した写しで、検査が対応の漏れ・不整合を見つけることを確かめる。件数を写した期待値は持たない |
| 項目が参照するテスト | 統括が 61 の指定（クラス・メソッド・モジュール）を実行した（台帳の `tests_executed`）。読んだだけのテストは `test_refs` の `run: false` |
| 動作が変わっていないこと | `kyuura_engine/`・カードデータ・固定デッキ・参照データ・既存の固定テストに差分がないことを `git diff --stat` で確かめた |

全体の対戦テスト（`python -m unittest` 全体）は、調査と文書化だけの作業なので実行していません。

## 11. 保守

- 項目を直すときは台帳（JSON）を直し、`--write` で集計と表を書き直します。表を手で直しません。
- 推奨対応を採用・却下したら、判断事項の文書と停止の方針の台帳に記録します。この再検証の記録は、調査時点の結果として残します。
- 元の一覧に `premise_changed`・`equivalence_scope` の食い違いが増えたら、`--check` が対応の漏れとして報告します。

## 12. 追記（後の修正）

この再検証の記録（1〜11 章・台帳の項目・集計）は調査の時点のまま残します。推奨対応のうち、後の版で直したものを台帳の `addenda`（種類 `fix`）に、直したコミットとともに追記します。
直したあとの動き・検証は参照先の版の文書にあります。

<!-- generated:addenda begin（scripts/check_normalization_revalidation.py --write が台帳から書く。手で直さない） -->
| 追記 | 日 | 種類 | 項目 | 直したコミット | 参照先 | 内容 |
|---|---|---|---|---|---|---|
| `ADD-V0139-PRIZE-ORDER-HC1-FIX` | 2026-11-03 | fix | `IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO`・`IA-HC1-NONCONFUSED-PROCEED` | `4f3b88c`・`ff9ea57` | [docs/prize-order-hc1-fix-v0.139.md](../docs/prize-order-hc1-fix-v0.139.md) | 再検証で common_defect_candidate とした 2 項目を v0.139 で直した。再検証の分類・軸・推奨・集計は再検証の時点の記録のまま（直したあとの動きは参照先の版の文書）。サイド: おもてのサイドがあるときの順番の決定（p.325）。HC1: 手順 4 のコインでもコインの前に止める |
| `ADD-PRIZE-ORDER-FOLLOWUP` | 2026-11-03 | followup | `IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO` | — | [docs/prize-order-followup.json](../docs/prize-order-followup.json) | v0.139 のあとの追加の検証（調査・再現・分類だけ。動作は変えていない）。本人だけが知るうらのサイド: 位置ごとの知識だけでは今の観測で順番による差はないが、［おみとおし］で先に取るプレイヤーの手札が見えると、どのサイドもうらでも後のプレイヤーの観測が変わる（合法な操作で再現。今の条件に加える必要がある候補）。単位: 1 枚ごと（今）とプレイヤーごとで、届く並び・決定の数・決定の時点の情報が変わり、カードの動き・勝ち負けは変わらない。保存形式 34: 既存の約束の範囲内。v0.138 は prize_order の写しを読み込み、再開で RuntimeError。この項目の記載・状態・集計は元の調査時点のまま |
| `ADD-PRIZE-ORDER-UNIT-ASSUMPTION` | 2026-11-03 | assumption | `IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO` | — | [docs/prize-order-followup.json](../docs/prize-order-followup.json) | v0.139 で加えた実装上の仮定（p.325 の一般規定は公式資料、同時のきぜつのサイドへの当てはめは v0.2f の導出、単位と決める時点は v0.86 の反応の順番からの類推と実装の選択）。利用者の承認はない。比べた読みと差は docs/prize-order-followup.md 2 章 |
<!-- generated:addenda end -->
