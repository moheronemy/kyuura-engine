# kyuura-engine

旧裏ポケモンカードゲーム（1996〜2001年のメディアファクトリー版）の対戦エンジンです。**「ポケットモンスターカードゲーム公式ルール 2000.02.14版」**（『ポケモンカードオフィシャルブック2000』pp.306〜326）に基づき、今の版は 0.199.0 です。

最重要の目標は、全カード対応ではなく、史料に基づいて正しく動くことです。原典で確かめられない処理は、現代のルールや推測で補わずに「未対応」「未解決」として扱います。

## 文書の入口

この README が文書の入口です。同じ役割の索引は別に作っていません。

- 現行の挙動は、下の「現行の仕様」の文書を参照先にします。
- 未対応・未裁定の事項は、下の「残件」の一覧を参照先にします。
- 版ごとの文書（`docs/<題>-v0.<版>.md`）は、その版で変えたこと・当時の根拠・検証の条件の記録です。あとの版で変わった事項は、現行の仕様の文書を優先してください。

### 現行の仕様

| 知りたいこと | 参照先 |
|---|---|
| ルールの項目ごとの扱い・誌面のページ・kyuura の記録の id・裁定の根拠 | [ルールの仕様（公式ルール 2000.02.14版）](docs/rules-2000-02-14.md) |
| 対応状況（実装済み・テスト限定・未実装・原典未確認・裁定が未解決）と版ごとの項 | [実装状況](docs/implementation-status.md) |
| 公式の記録で決まらないためエンジンが採った仕様の一覧（実装上の読み方・採用した仕様・簡略化）| [一覧](docs/implementation-assumptions.md)（台帳は同名の JSON） |
| カードデータの採用と照合の方針・データの来歴・照合の記録の再利用 | [カードデータの方針](docs/card-data-policy.md)・[データの来歴](docs/data-provenance.md)・[照合済みの記録の再利用](docs/verified-record-reuse.md) |
| 停止コードと未対応処理の分類・停止の方針 | [停止の方針の分類](docs/stop-policy-classification.md)（台帳は同名の JSON）・[利用者が決める事項](docs/stop-policy-decisions.md) |
| 厳密モード・プレイ用モードと規約集合 | [設計](docs/ruleset-mode-design.md)・[利用者が決める事項](docs/ruleset-mode-decisions.md)・今の開発用の集合 `CS-KYUURA-PLAY-TR8@1` は [v0.198](docs/play-convention-tr8-v0.198.md) |
| 外から使う入口（GUI など） | [クライアント向けのアダプタ](docs/client-api-v0.164.md)・[可視ログの配信](docs/client-api-visible-log-v0.183.md)・[合法手 API](docs/legal-actions-u7-1.md)（[仕様案](docs/legal-actions-api-design.md)）・[診断の型](docs/diagnostics-adapter-v0.152.md) |
| 再現用記録・状態スナップショット | [記録](docs/replay-record-v0.153.md)・[再実行](docs/replay-run-v0.154.md)・[スナップショット](docs/state-snapshot-v0.157.md)・[記録との接続](docs/state-snapshot-v0.158.md) |
| 実装の識別と互換性 | [設計案](docs/implementation-identity-design.md) |

**記録の区分:** 公式の記録（印刷の文面・最新の説明やエラッタ・裁定）と、エンジンの実装解釈を分けて記録しています。

- 裁定の根拠と、その項目が公式の記録で決まったのか、実装解釈なのかは、[ルールの仕様](docs/rules-2000-02-14.md) と版の文書に書いています。
- 公式の記録で決まらない場面は推測で確定せず、`UNRESOLVED_…` の停止コードで止めます（研究上の未解決とエンジンの未対応は別に扱います）。
- 例: v0.199 の［エナジーコントロール］の変更は「カード文面とカード分類に基づく実装解釈。当時の直接裁定は未確認」です（[v0.199](docs/energy-control-rainbow-v0.199.md)）。

### 対戦・検証の手順

| 作業 | 参照先 |
|---|---|
| インストール（通常・開発用） | [インストール](docs/installation.md)・下の「セットアップ」 |
| テストの実行範囲・総数の集約・過去版の対象の切り出し | [テストの実行と追加](docs/testing.md)・下の「テストの実行」 |
| 対戦を始める（API の例・固定のデッキ） | 下の「使い方」 |
| 検証用 AI の仕様 | [仕様](docs/verification-ai-design.md)・[観測の記録](docs/verification-ai-observation.md)・[範囲の外の未裁定の候補の記録（prestop）](docs/prestop-record-design.md) |
| 検証用 AI の上限つき逐次バッチ（計画・実行・照合） | [バッチ](docs/verification-ai-batch.md)・[明示的なデッキリスト](docs/verification-ai-decklist.md)・[外部の pyc キャッシュの手順](docs/verification-ai-pyc-cache-procedure.md)・[資源と実行予算](docs/verification-ai-scale-budget.md) |
| 検証用 AI の方策 | 通常のルールの方策: `rules-v1`（[V2](docs/verification-ai-v2.md)）・`rules-v2`（[V2 の補完](docs/verification-ai-v2-repeat.md)）。方式の一覧は [バッチ](docs/verification-ai-batch.md)。試験の方策は下の表 |

試験の方策は、`batch plan --modes` で明示したときだけ使います（既定にしていません）。`rules-v3`・`rules-v4` は `rules-v2` に、`rules-v5`〜`rules-v10` は 1 つ前の方策に規則を足したものです。

| 方策 | 足した規則 | 仕様と比較の文書 |
|---|---|---|
| `rules-v3` | 観測が戻った［ダメージスワップ］の周期の候補を下げる | [試験](docs/tr8-damage-swap-loop-experiment.md) |
| `rules-v4` | 確認した周期の移動だけを後回し | [試験](docs/tr8-damage-swap-transition-policy-experiment.md) |
| `rules-v5` | 同じ番の［ダメージスワップ］の受理 6 回で後回し | [試験](docs/tr8-rules-v5-damage-swap-guard-experiment.md) |
| `rules-v6` | ［エナジートランス］の往復の移動を後回し | [試験](docs/tr8-energy-trans-loop-experiment.md) |
| `rules-v7` | 支払い条件が変わらない「にげる」を後回し | [試験](docs/tr8-retreat-reselection-experiment.md) |
| `rules-v8` | ［エナジートランス］で費用に近づく移動を優先 | [試験](docs/tr8-energy-trans-progress-policy-experiment.md) |
| `rules-v9` | 同じ局面で未裁定として拒否された入力を避けて別の手へ進む | [試験](docs/tr8-rules-v9-refused-input-experiment.md) |
| `rules-v10` | ［エナジートランス］の費用評価を基本エネルギーの移動だけでも行う（レインボーなどの移動は採点の外） | [v0.200](docs/hydro-pump-rainbow-rules-v10-v0.200.md) |

### 残件（未対応・未裁定）

- **エンジンの未対応・未裁定:** [実装状況](docs/implementation-status.md) の「[未実装](docs/implementation-status.md#未実装)」「[原典未確認](docs/implementation-status.md#原典未確認)」「[裁定が未解決](docs/implementation-status.md#裁定が未解決)」が参照先です。停止コードごとの扱いは [停止の方針の分類](docs/stop-policy-classification.md) にあります。
- **エンジン・検証用 AI・GUI をまとめた一覧:** [現在の完了・未完了一覧（0.187.0 の時点）](docs/project-status-ledger-v0187.md)。0.188.0 からあとの変化は、[実装状況](docs/implementation-status.md) の末尾の「現在の完了・未完了一覧」の節と、下の「現在の状態」にあります。
- **機能凍結の前の棚卸し（v0.133 の時点）:** [棚卸し](docs/pre-freeze-gap-inventory.md)・[修正計画](docs/pre-freeze-remediation-plan.md)。

### 現在の状態（0.200.0。2026-11-28）

- **エンジン 0.200.0:** カメックスの［ハイドロポンプ］で、場で「水」を供給するレインボーエネルギーを「水」エネルギーとして数えます（[v0.200](docs/hydro-pump-rainbow-rules-v10-v0.200.md)。カード文面と既存のルールに基づく実装解釈。当時の直接裁定は未確認）。seed 9094 の通常の対戦で、0.199.0 が RB1 で拒否した宣言が受理されました（60 ダメージ）。ほかの RB1 の処理は止まるままです。
- **0.199.0 から:** ミュウツー（PR1-022）の［エナジーコントロール］で、相手の場のレインボーエネルギーを選べるものから外しました（[v0.199](docs/energy-control-rainbow-v0.199.md)）。
  - 記録の区分は「カード文面とカード分類に基づく実装解釈。当時の直接裁定は未確認」です。研究の論点（kyuura）は未解決のままです。
  - 同じ停止コード `UNRESOLVED_RAINBOW_AS_BASIC_ENERGY_CARD` を使うほかの処理には当てはめていません（止まるままです）。
- **通常の対戦での確認:** seed 9083 の 1 局で、0.198.0 が拒否した宣言が受理され、局は完走しました（[1 局の再検証](docs/energy-control-rainbow-v0199-game-verification.md)）。
  - 通常の対戦で出た枝は「うら」だけです。相手の場がレインボーエネルギーと無色2個エネルギーだけの盤面での「おもて」は、構築盤面でだけ確かめています。
- **検証用 AI:** 道具の版 21、規約集合 `CS-KYUURA-PLAY-TR8@1`。`rules-v9`・`rules-v10` は試験の方策で、明示したときだけ使います（上の表）。`rules-v10` が費用に近づく基本エネルギーの移動を選び、受理されたことを、seed 9092 の通常の対戦で確かめました（[v0.200](docs/hydro-pump-rainbow-rules-v10-v0.200.md) の 6 章）。
- **拡大デッキの監査:** `rules-v9` の本監査（0.199.0・4 条件 × 6 局・seed 9091〜9096）は 24／24 が `game_over` でした（[本監査](docs/tr8-rules-v9-expanded-deck-main-audit.md)。[先行試験](docs/tr8-rules-v9-expanded-deck-pilot.md) は 4／4）。
  - 拒否は 4 件（RB1 の［ハイドロポンプ］）で、どれも別の手が受理されました。異色の条件の費用評価は、動かせるカードにレインボーエネルギーがあるため、すべて評価できませんでした（本監査の 7 章に次の課題）。
  - `rules-v7`／`rules-v8` の費用評価を比べる旧監査の 16 計画は保全したままで、残りの 53 局は未着手です（[旧監査の計画](docs/history/tr8-rules-v8-expanded-deck-audit-plan.md)）。停止の解除・再開はしていません。

### 履歴（旧版・試験記録）

- **版の一覧:** 下の「[版の一覧](#版の一覧)」。整理の前の README の長い説明・機能ごとの使い方の例・古い一覧は、本文のまま [README の履歴](docs/history/readme-archive-v0.199.md) に移しました。
- **元の場所に残した記録:** 版の文書、v0.18〜v0.27 の検証、v0.2a〜v0.5 のアーキテクチャ、U7 の総合検証、`rules-v3`〜`rules-v9` の試験の文書などは `docs/` に置いたままです。テスト・生成器・kyuura の研究の記録・GUI の文書が、固定のパスで参照しているためです。
- **`docs/history/` に移した記録:** 検証用 AI の計画・監査・比較のうち、コード・テスト・生成器・台帳・kyuura・GUI から参照されていないものです。どれも書いた時点の版・規約集合・方策の記録で、各文書の冒頭にその条件を書いています。

| まとまり | 対象の版・規約集合・方策 | 文書 |
|---|---|---|
| 検証用 AI の初期の計画・監査 | エンジン 0.172.0〜0.185.0・`rules-v1`／`rules-v2` | [実装の計画](docs/history/verification-ai-implementation-plan.md)・[V3 の設計](docs/history/verification-ai-v3-design.md)・[V0〜V3-3 の棚卸し](docs/history/verification-ai-inventory.md)・[R-5 の監査](docs/history/legal-actions-r5-audit.md)・[小規模バッチの計画 4](docs/history/verification-ai-batch-plan4.md)・[s1 の拒否の確認](docs/history/verification-ai-batch-s1-rejection-audit.md)・[開始の照合の調査](docs/history/verification-ai-startup-check-investigation.md)・[prestop の初回バッチの計画](docs/history/prestop-first-batch-plan.md)・[範囲の外の候補の内訳](docs/history/prestop-ruling-breakdown.md) |
| TR3〜TR7 の計画・監査・比較 | エンジン 0.187.0〜0.197.0・`CS-KYUURA-PLAY-TR3@1`〜`TR7@1`・`rules-v2` | [P2-min の計画](docs/history/p2-min-batch-plan.md)・[TR3 の new_game の計画](docs/history/tr3-newgame-batch-plan.md)・[TR6 の監査](docs/history/tr6-unresolved-batch-plan.md)・[H4 の TR4／TR6 比較](docs/history/h4-tr4-tr6-comparison.md)・[T19b の TR6／TR7 比較](docs/history/t19b-tr6-tr7-comparison.md)・[TR7 の補足バッチ](docs/history/tr7-supplemental-audit.md) |
| TR8 の監査と `rules-v5`〜`rules-v8` の比較 | エンジン 0.198.0・`CS-KYUURA-PLAY-TR8@1`・`rules-v2`／`rules-v5`〜`rules-v8` | [TR8 の監査](docs/history/tr8-unresolved-batch-plan.md)・[`rules-v5` の監査](docs/history/tr8-rules-v5-audit-plan.md)・[`rules-v6` の監査](docs/history/tr8-rules-v6-scaled-audit-plan.md)・[9056 の切り分け](docs/history/tr8-rules-v7-9056-energy-trans-analysis.md)・[D4 の構築盤面](docs/history/tr8-rules-v8-d4-board-verification.md)・[未使用 seed の比較](docs/history/tr8-rules-v8-fresh-seed-comparison.md)・[拡大デッキの監査の計画](docs/history/tr8-rules-v8-expanded-deck-audit-plan.md) |

## 版の一覧

新しい順です。各版で変えたこと・当時の根拠・検証の条件は、その版の文書にあります。整理の前の README にあった長い説明は、本文のまま [README の履歴](docs/history/readme-archive-v0.199.md) の 1 章に移しました。

- v0.200（今のエンジンの版。`kyuura_engine` の版は 0.200.0）: カメックス（PMCG1-032）の［ハイドロポンプ］で、場で「水」を供給するレインボーエネルギーを「水」エネルギーとして数える（カード文面と既存のルールに基づく実装解釈。当時の直接裁定は未確認）。検証用 AI の試験の方策 `rules-v10`（道具の版 21）。 文書: [hydro-pump-rainbow-rules-v10-v0.200.md](docs/hydro-pump-rainbow-rules-v10-v0.200.md)
- v0.199（`kyuura_engine` の版は 0.199.0）: ミュウツー（PR1-022）の［エナジーコントロール］で、相手の場についているレインボーエネルギーを、ワザの文面の「特殊エネルギー以外」に当たらない特殊エネルギーカードとして選べるものから外す（カード文面とカード分類に基づく実装解釈。当時の直接裁定は未確認）。 文書: [energy-control-rainbow-v0.199.md](docs/energy-control-rainbow-v0.199.md)
- v0.198（`kyuura_engine` の版は 0.198.0）: ラッキースタジアムの別の個体の同じ番の使用のプレイ用の続行規約 `PC-LUCKY-STADIUM-REPLACEMENT@1` と開発用の部分的な集合 `CS-KYUURA-PLAY-TR8@1`（TR7@1 の 26 規約 + 1）。 文書: [play-convention-tr8-v0.198.md](docs/play-convention-tr8-v0.198.md)
- v0.197（`kyuura_engine` の版は 0.197.0）: 「とうめい」で受けないと決まったあとの特殊状態のワザのコインのプレイ用の続行規約 `PC-T19B-NULLIFIED-STATUS-COIN@1` と開発用の部分的な集合 `CS-KYUURA-PLAY-TR7@1`（TR6@1 の 25 規約 + 1）。 文書: [play-convention-tr7-v0.197.md](docs/play-convention-tr7-v0.197.md)
- v0.196（`kyuura_engine` の版は 0.196.0）: エナジーへんかんの 0 枚の答えのプレイ用の続行規約 `PC-ENERGY-CONVERSION-ZERO@1` と開発用の部分的な集合 `CS-KYUURA-PLAY-TR6@1`（TR4@1 の 24 規約 + 1）。 文書: [play-convention-tr6-v0.196.md](docs/play-convention-tr6-v0.196.md)
- v0.195（`kyuura_engine` の版は 0.195.0）: エネルギー回収の 0 枚の答えのプレイ用の続行規約 `PC-ENERGY-RETRIEVAL-ZERO@1` と開発用の部分的な集合 `CS-KYUURA-PLAY-TR4@1`（TR3@1 の 23 規約 + 1）。 文書: [play-convention-tr4-v0.195.md](docs/play-convention-tr4-v0.195.md)
- v0.194（`kyuura_engine` の版は 0.194.0）: C-TF2 の実装（0.194.0）: ワザの宣言でおもてにしたうらの使い手の姿を、公開の直後（ワザの使用の確かめ・先読み・コスト・コイン・効果の前）に既存の固定へ足した…。 文書: [r2-transform-frozen-reveal-v0.194.md](docs/r2-transform-frozen-reveal-v0.194.md)
- v0.193（`kyuura_engine` の版は 0.193.0）: C-TF1（0.193.0）: 変身で写した、ワザといっしょに宣言する特殊能力（［すいりょくはつでん］の `attack_power`・［XXXXX］・［ANGER］の `with_power`・`with_powers`）に…。 文書: [r2-transform-copied-power-v0.193.md](docs/r2-transform-copied-power-v0.193.md)
- v0.192（`kyuura_engine` の版は 0.192.0）: R-2 のアンノーンの自己持ち主の限定提示を実装した（0.192.0。うらのバトル場のアンノーンX・A 自身の［XXXXX］・［ANGER］の 2 能力だけで、R-2 全体の解消ではない）。 文書: [r2-unown-self-holder-v0.192.md](docs/r2-unown-self-holder-v0.192.md)
- v0.191（`kyuura_engine` の版は 0.191.0）: R-2 のアンノーンの［XXXXX］・［ANGER］の限定提示を実装した（0.191.0。別のおもての持ち主の 2 能力だけで、R-2 全体の解消ではない）。 文書: [r2-unown-v0.191.md](docs/r2-unown-v0.191.md)
- v0.190（`kyuura_engine` の版は 0.190.0）: R-2 の［めいれい］の限定提示を実装した（0.190.0。R-2 全体の解消ではない）。 文書: [r2-with-power-v0.190.md](docs/r2-with-power-v0.190.md)
- v0.189（`kyuura_engine` の版は 0.189.0）: おもてにしたうらの使い手（マチスの秘策）のワザの宣言の先読みが、ほかの結果を公開の前の状態で試し、使い手自身のうらのカードの項目を読んで FD1 で拒否していた不整合を直した…。 文書: [stop-ledger-sync-v0.189.md](docs/stop-ledger-sync-v0.189.md)・[r2-coin-preflight-v0.189.md](docs/r2-coin-preflight-v0.189.md)
- v0.188（`kyuura_engine` の版は 0.188.0）: R-2 の初回対応。 文書: [r2-stadium-coin-v0.188.md](docs/r2-stadium-coin-v0.188.md)
- v0.187（`kyuura_engine` の版は 0.187.0）: 停止の方針の台帳・共通規約の設計案・実行時の場面の索引（`kyuura_engine/data/convention_records.json`）を正式に同期した（台帳の蓄積の差・TR3 の採用の記録・テスト・道具だけの語の役割。台帳は `schema_version` 2）。 文書: [token-sync-v0.187.md](docs/token-sync-v0.187.md)・[project-status-ledger-v0187.md](docs/project-status-ledger-v0187.md)
- v0.186（`kyuura_engine` の版は 0.186.0）: 突風・ポケモンいれかえ・きずぐすりのプレイ用の続行規約 3 件（`PC-GUST-WITHOUT-OPPONENT-BENCH`・`PC-SWITCH-WITHOUT-BENCH`・`PC-POTION-WITHOUT-DAMAGE`）と…。 文書: [project-status-ledger-v0187.md](docs/project-status-ledger-v0187.md)・[play-convention-tr3-v0.186.md](docs/play-convention-tr3-v0.186.md)
- v0.185（`kyuura_engine` の版は 0.185.0）: 化石の発掘で山札から選んで見せたカードの `reveal_from_deck` に `card_id`（`identify=True`。トラッシュの側は変えていない）…。 文書: [fossil-slot-reveal-v0.185.md](docs/fossil-slot-reveal-v0.185.md)
- v0.184（`kyuura_engine` の版は 0.184.0）: 「相手プレイヤーに見せてから」手札に加える・山札にもどす 17 の呼ぶ箇所（トレーナー 8・特殊能力 3・ワザの要素 6）で、出来事 `reveal_from_deck`・`return_to_deck` に見せたカードの `card_id` を加えた…。 文書: [reveal-identify-v0.184.md](docs/reveal-identify-v0.184.md)
- v0.183（`kyuura_engine` の版は 0.183.0）: client_api の入口（プレイヤー・観戦者・ホスト）に読み取りの要求 `log` を加えた。 文書: [client-api-visible-log-v0.183.md](docs/client-api-visible-log-v0.183.md)
- v0.182（`kyuura_engine` の版は 0.182.0）: ポケモン交換おじさんの「相手プレイヤーに見せる」2 枚（手札から山札にもどすカード・山札から選んで手札に加えるカード）の出来事 `return_to_deck`・`reveal_from_deck` に、そのカードの `card_id` を加えた…。 文書: [trader-reveal-identification-v0.182.md](docs/trader-reveal-identification-v0.182.md)
- v0.181（`kyuura_engine` の版は 0.181.0）: E12 の修正。 文書: [keep-designated-energy-removal-v0.181.md](docs/keep-designated-energy-removal-v0.181.md)
- v0.180（`kyuura_engine` の版は 0.180.0）: S1 監査の F-1。 文書: [legal-actions-f1-face-down-attack-guarantee.md](docs/legal-actions-f1-face-down-attack-guarantee.md)
- v0.179（`kyuura_engine` の版は 0.179.0）: PT-5t-C1。 文書: [legal-actions-up5t-d-trainer-audit.md](docs/legal-actions-up5t-d-trainer-audit.md)・[verification-ai-v0179-follow.md](docs/verification-ai-v0179-follow.md)・[verification-ai-batch.md](docs/verification-ai-batch.md)
- v0.178（`kyuura_engine` の版は 0.178.0）: UP-5t-C1。 文書: [legal-actions-up5t-audit.md](docs/legal-actions-up5t-audit.md)・[verification-ai-v0178-follow.md](docs/verification-ai-v0178-follow.md)
- v0.177（`kyuura_engine` の版は 0.177.0）: PT5E-FROM-STATE-INVARIANT。 文書: [pt5e-from-state-invariant-audit.md](docs/pt5e-from-state-invariant-audit.md)
- v0.176（`kyuura_engine` の版は 0.176.0）: PT-5e。 文書: [legal-actions-pt5e-audit.md](docs/legal-actions-pt5e-audit.md)・[verification-ai-v0176-follow.md](docs/verification-ai-v0176-follow.md)
- v0.175（`kyuura_engine` の版は 0.175.0）: R-3 の U-R3a。 文書: [legal-actions-u-r3a-v0.175.md](docs/legal-actions-u-r3a-v0.175.md)
- v0.174（`kyuura_engine` の版は 0.174.0）: R-5 の P6。 文書: [legal-actions-p6-face-down-retreat.md](docs/legal-actions-p6-face-down-retreat.md)
- v0.173（`kyuura_engine` の版は 0.173.0）: CN-1 の修正。 文書: [cn1-failure-v0.173.md](docs/cn1-failure-v0.173.md)
- v0.172（`kyuura_engine` の版は 0.172.0）: 合法手 API の U7-5f・U7-5g（契約・形式の版は同じ。エンジンの動作は変えていない）。 文書: [legal-actions-u7-5fg.md](docs/legal-actions-u7-5fg.md)
- v0.171（`kyuura_engine` の版は 0.171.0）: 合法手 API の宣言する特殊能力（U7-5e）。 文書: [legal-actions-u7-5e.md](docs/legal-actions-u7-5e.md)
- v0.170（`kyuura_engine` の版は 0.170.0）: 合法手 API の場のスタジアム（U7-5d）。 文書: [legal-actions-u7-5d.md](docs/legal-actions-u7-5d.md)
- v0.169（`kyuura_engine` の版は 0.169.0）: 合法手 API の手札のトレーナー（U7-5c）。 文書: [legal-actions-u7-5c.md](docs/legal-actions-u7-5c.md)
- v0.168（`kyuura_engine` の版は 0.168.0）: 錯乱ジムの「うら」で相手がかわりに使えるかの確かめ（と、同じ確かめのナツメのサイキックコントロールの選べるもの）が、相手・観戦者に見えない手札・山札の中身を読み、決定の有無・選べるものの数・公開のログに出ていた情報漏れの修正（T-F1。両モード共通）。 文書: [chaos-gym-borrow-t-f1.md](docs/chaos-gym-borrow-t-f1.md)
- v0.167（`kyuura_engine` の版は 0.167.0）: 合法手 API の場のポケモン 1 匹を指す操作（U7-5a・U7-5b）。 文書: [legal-actions-u7-5ab.md](docs/legal-actions-u7-5ab.md)
- v0.166（`kyuura_engine` の版は 0.166.0）: 合法手 API のワザの候補と宣言の入力（U7-4）。 文書: [legal-actions-u7-4.md](docs/legal-actions-u7-4.md)
- v0.165（`kyuura_engine` の版は 0.165.0）: 合法手 API の番の基本の操作（U7-3）。 文書: [legal-actions-u7-3.md](docs/legal-actions-u7-3.md)
- v0.164（`kyuura_engine` の版は 0.164.0）: 別リポジトリの GUI 向けの最小のクライアントアダプタ `kyuura_engine.client_api`（契約 `kyuura-client-api`・形式 1）。 文書: [client-api-v0.164.md](docs/client-api-v0.164.md)
- v0.163（`kyuura_engine` の版は 0.163.0）: 合法手 API の準備の操作とホストの操作（U7-2）。 文書: [legal-actions-u7-2.md](docs/legal-actions-u7-2.md)
- v0.162（`kyuura_engine` の版は 0.162.0）: U7 の決定の入力の監査（操作の種類は増やしていない）。 文書: [legal-actions-decision-audit.md](docs/legal-actions-decision-audit.md)
- v0.161（`kyuura_engine` の版は 0.161.0）: U7-1 の補完（操作の種類は増やしていない）。 文書: [legal-actions-u7-1.md](docs/legal-actions-u7-1.md)
- v0.160（`kyuura_engine` の版は 0.160.0）: 合法手 API の最小の実装（U7-1。U7 全体の部分実装）。 文書: [legal-actions-u7-1.md](docs/legal-actions-u7-1.md)
- v0.159（`kyuura_engine` の版は 0.159.0）: U1〜U6（診断・実行アダプタ・完全な記録・再実行・閲覧用記録・状態の保存と復元・スナップショットからの接続）の総合検証。 文書: [integration-verification-v0.159.md](docs/integration-verification-v0.159.md)
- v0.158（`kyuura_engine` の版は 0.158.0）: 完全な再現用記録とスナップショットの接続（U6 の S5。これで U6 の S1〜S6 がすべて実装済み）。 文書: [state-snapshot-v0.158.md](docs/state-snapshot-v0.158.md)
- v0.157（`kyuura_engine` の版は 0.157.0）: 状態スナップショット（U6 の S1〜S4・S6）。 文書: [state-snapshot-v0.157.md](docs/state-snapshot-v0.157.md)
- v0.155（`kyuura_engine` の版は 0.155.0）: 閲覧用記録（U5）。 文書: [view-record-v0.155.md](docs/view-record-v0.155.md)
- v0.154（`kyuura_engine` の版は 0.154.0）: 完全な再現用記録からの再実行と確認値の照合（U4）。 文書: [replay-run-v0.154.md](docs/replay-run-v0.154.md)
- v0.153（`kyuura_engine` の版は 0.153.0）: 完全な再現用記録の収集・読み書き・構造の検証（U3）。 文書: [replay-record-v0.153.md](docs/replay-record-v0.153.md)
- v0.152（`kyuura_engine` の版は 0.152.0）: 診断の型と情報境界（U1）・コマンド実行結果のアダプタ（U2）。 文書: [diagnostics-adapter-v0.152.md](docs/diagnostics-adapter-v0.152.md)
- v0.151（`kyuura_engine` の版は 0.151.0）: 山札から「○」エネルギーカード・基本エネルギーカードをつける・加えるワザの、山札を見る前の研究上の停止…。 文書: [deck-search-stop-oracles-v0.151.md](docs/deck-search-stop-oracles-v0.151.md)
- v0.150（`kyuura_engine` の版は 0.150.0）: 山札をさがす効果（ベンチに出す・見せて手札に加える・山札からつける・［うか］）で、選べるカードがないと決定を出さずに進んだため、決定の有無から山札の内容が相手・観戦者に分かる情報漏れ…。 文書: [deck-search-decision-presence-v0.150.md](docs/deck-search-decision-presence-v0.150.md)
- v0.149（`kyuura_engine` の版は 0.149.0）: 任意の山札進化（たきのぼりしんか・つきのちから）で、検索の決定が出るかどうかから山札の内容が相手・観戦者に分かる情報漏れ（PSP-OPTIONAL-DECK-EVOLUTION-DECISION-PRESENCE）と…。 文書: [optional-deck-evolution-presence-v0.149.md](docs/optional-deck-evolution-presence-v0.149.md)
- v0.148（`kyuura_engine` の版は 0.148.0）: 山札から進化カードを重ねるワザ（たきのぼりしんか・つきのちから・からやぶりしんか・ひざしをあびる・ばくれつしんか・しんかのほうし・しんかのうた）の、山札を見る前の確かめ（ワザの宣言の前の先読みを含む）が、本人に見えない山札の中身を読み…。 文書: [attack-deck-evolution-preflight-v0.148.md](docs/attack-deck-evolution-preflight-v0.148.md)
- v0.147（`kyuura_engine` の版は 0.147.0）: 特殊能力の使う前の確かめが、本人に見えない山札の中身を読み、山札とサイドの配分で受理・拒否・理由が変わる情報漏れを両モード共通で直した…。 文書: [deck-content-prechecks-v0.147.md](docs/deck-content-prechecks-v0.147.md)
- v0.146（`kyuura_engine` の版は 0.146.0）: 続行規約の追加を区切り、検証の基盤と安全性を整えた。 文書: [play-set-verification-v0.146.md](docs/play-set-verification-v0.146.md)
- v0.145（`kyuura_engine` の版は 0.145.0）: ［ポイズンミスト］とどくの量の続行規約 3 件（PC-POISON-AMOUNT-ORDER@1・PC-POISON-MIST-TARGETS@1・PC-POISON-MIST-SOURCE-LEFT@1）を利用者の採用の範囲で実装し…。 文書: [poison-mist-play-po-v0.145.md](docs/poison-mist-play-po-v0.145.md)
- v0.144（`kyuura_engine` の版は 0.144.0）: ポケモンチェックのどくでかがくへんかガスの発生源がきぜつし、残りHP「10」で消えていた［ずらかる］の力がもどる盤面（SC2）が `StateIntegrityError` になっていた両モード共通の不具合を直し、ダメージの前に同じ停止コードで止める（新しい裁定ではない）。 文書: [poison-mist-play-policy-spec.md](docs/poison-mist-play-policy-spec.md)・[sc2-integrity-fix-v0.144.md](docs/sc2-integrity-fix-v0.144.md)
- v0.143（`kyuura_engine` の版は 0.143.0）: S2a の続行規約 5 件（切り直しの補償・化石と人形の初手・ポケモンチェックの両側コイン・コインで決まる枚数の不足・ポケモンチェックでのきぜつ判定）を利用者の採用で実装し、開発用の部分的な集合 `CS-KYUURA-PLAY-S2A@1` に入れた…。 文書: [play-policy-s2a-v0.143.md](docs/play-policy-s2a-v0.143.md)
- v0.142（`kyuura_engine` の版は 0.142.0）: 規約集合の識別・版の管理と、対戦への組み込みの基盤（共通規約の設計案の S1）。 文書: [ruleset-foundation-v0.142.md](docs/ruleset-foundation-v0.142.md)
- v0.141（`kyuura_engine` の版は 0.141.0）: v0.140 のサイドを取る順番の件の整理。 文書: [prize-order-v0140-cleanup-v0.141.md](docs/prize-order-v0140-cleanup-v0.141.md)
- v0.140（`kyuura_engine` の版は 0.140.0）: 利用者の指定で、同時のきぜつで両方がサイドを取るときは、いつも番のプレイヤーが先に取るプレイヤーを選び（決定 `prize_first`。おもて・うら・特殊能力の有無によらない）、選ばれたプレイヤーがまとめて取ってから、もう一方が取る…。 文書: [prize-order-user-rule-v0.140.md](docs/prize-order-user-rule-v0.140.md)
- v0.139（`kyuura_engine` の版は 0.139.0）: 正規化の再検証で両モード共通の不具合の候補とした 2 件の修正。 文書: [prize-order-hc1-fix-v0.139.md](docs/prize-order-hc1-fix-v0.139.md)
- v0.138（`kyuura_engine` の版は 0.138.0）: v0.137 で見つけた情報漏れ 2 件の修正（PSP-RUIN-WALL-BLOCKED-REASON-ORACLE・PSP-UPZ2-ENERGY-AMPLIFIER-ORACLE）。 文書: [oracle-leak-fixes-v0.138.md](docs/oracle-leak-fixes-v0.138.md)
- v0.137（`kyuura_engine` の版は 0.137.0）: 山札から選ぶトレーナーの使う前の拒否による情報漏れの修正（停止の方針の分類で見つけた PSP-ST1-DECK-ORACLE・PSP-FC1-ENERGY-ARK-ORACLE）。 文書: [deck-search-oracle-v0.137.md](docs/deck-search-oracle-v0.137.md)
- v0.136（`kyuura_engine` の版は 0.136.0）: カードめくりゲーム（neo1-080）の答えの受理・拒否による情報漏れの修正。 文書: [card-flip-answer-rejection-v0.136.md](docs/card-flip-answer-rejection-v0.136.md)
- v0.135（`kyuura_engine` の版は 0.135.0）: クイズの答えの受理・拒否による情報漏れの修正。 文書: [quiz-answer-rejection-v0.135.md](docs/quiz-answer-rejection-v0.135.md)
- v0.134（`kyuura_engine` の版は 0.134.0）: サドン・デスの延長戦の開始。 文書: [sudden-death-v0.134.md](docs/sudden-death-v0.134.md)
- v0.133（`kyuura_engine` の版は 0.133.0）: ひかるバンギラス（neo4-082）のマウンテンクラッシュ・はかいのほのお。 文書: [shining-tyranitar-v0.133.md](docs/shining-tyranitar-v0.133.md)
- v0.132（`kyuura_engine` の版は 0.132.0）: ヤドキング（neo1-049）の［ちえくらべ］・マッドインパクト。 文書: [slowking-mind-games-v0.132.md](docs/slowking-mind-games-v0.132.md)
- v0.131（`kyuura_engine` の版は 0.131.0）: ナッシー[Exeggutor]（PR1-075・PR1-077。日本語と英語を併記したプロモ）。 文書: [exeggutor-bilingual-names-v0.131.md](docs/exeggutor-bilingual-names-v0.131.md)
- v0.130（`kyuura_engine` の版は 0.130.0）: とりかえっこプリーズ（PR1-027）。 文書: [trade-please-ownership-v0.130.md](docs/trade-please-ownership-v0.130.md)
- v0.129（`kyuura_engine` の版は 0.129.0）: カツラのクイズ その1（GD5-016）。 文書: [blaines-quiz-heights-v0.129.md](docs/blaines-quiz-heights-v0.129.md)
- v0.128（`kyuura_engine` の版は 0.128.0）: kyuura の目録の分類の取り込みと、通常対戦の対象の整理。 文書: [catalog-scope-migration-v0.128.md](docs/catalog-scope-migration-v0.128.md)
- v0.127（`kyuura_engine` の版は 0.127.0）: 枚数不足の途中停止と、利用者指定の簡略ルールのプロモ 3 枚。 文書: [deferred-shortage-user-promos-v0.127.md](docs/deferred-shortage-user-promos-v0.127.md)
- v0.126（`kyuura_engine` の版は 0.126.0）: フラッシュと表向きの山札。 文書: [flash-faceup-deck-v0.126.md](docs/flash-faceup-deck-v0.126.md)
- v0.125（`kyuura_engine` の版は 0.125.0）: プクリンの最新の説明・てだすけ。 文書: [wigglytuff-helping-hand-v0.125.md](docs/wigglytuff-helping-hand-v0.125.md)
- v0.124（`kyuura_engine` の版は 0.124.0）: 変身の共通ルール・すごいへんしん・わるいはどう。 文書: [super-transform-dark-pulse-v0.124.md](docs/super-transform-dark-pulse-v0.124.md)
- v0.123（`kyuura_engine` の版は 0.123.0）: 名前の訂正の移行とウィンディ 3 枚。 文書: [arcanine-name-migration-v0.123.md](docs/arcanine-name-migration-v0.123.md)
- v0.122（`kyuura_engine` の版は 0.122.0）: アンノーンの併用・化石の進化履歴・退却時の反応の 13 枚…。 文書: [unown-fossil-retreat-reactions-v0.122.md](docs/unown-fossil-retreat-reactions-v0.122.md)
- v0.121（`kyuura_engine` の版は 0.121.0）: 写しの元・研究の基準を kyuura e519b99 から 2fe0bc0 に上げ（移行の段 v0.121。写しの 1,333 枚の値は同じ。ピカチュウ IP1-040 のなきごえの処理に使う文面を最新の説明 LD-IP1-040-ATK0 にした）…。 文書: [hand-bench-attack-conditions-v0.121.md](docs/hand-bench-attack-conditions-v0.121.md)
- v0.120（`kyuura_engine` の版は 0.120.0）: 化石の復活と仮想ワザの供給の 11 枚（トゲチック neo1-071・カブト neo2-014・オムナイト neo2-032・たまごの化石 neo2-055・ワタッコ neo3-007・キングドラ neo3-020・プテラ neo3-042・スリーパー ES3…。 文書: [fossil-basic-virtual-attacks-v0.120.md](docs/fossil-basic-virtual-attacks-v0.120.md)
- v0.119（`kyuura_engine` の版は 0.119.0）: 受けるダメージの選択・どくとねむり・場の効果のポケモン 11 枚…。 文書: [damage-reactions-poison-sleep-v0.119.md](docs/damage-reactions-poison-sleep-v0.119.md)
- v0.118（`kyuura_engine` の版は 0.118.0）: 上限なしコイン・攻撃時の能力・回復の配分のポケモン 9 枚…。 文書: [unbounded-coins-heal-allocation-v0.118.md](docs/unbounded-coins-heal-allocation-v0.118.md)
- v0.117（`kyuura_engine` の版は 0.117.0）: 場の移動・にげる時の反応・条件付きの特殊能力のポケモン 13 枚…。 文書: [retreat-return-active-powers-v0.117.md](docs/retreat-return-active-powers-v0.117.md)
- v0.116（`kyuura_engine` の版は 0.116.0）: エネルギーの付け替え・ついた時の効果・付属カードの回収と退化のポケモン 13 枚…。 文書: [energy-movement-attachment-devolution-v0.116.md](docs/energy-movement-attachment-devolution-v0.116.md)
- v0.115（`kyuura_engine` の版は 0.115.0）: 場・ベンチへのダメージ、対象ごとのコイン、ダメージの配分のポケモン 13 枚…。 文書: [spread-damage-allocation-v0.115.md](docs/spread-damage-allocation-v0.115.md)
- v0.114（`kyuura_engine` の版は 0.114.0）: ベイビィポケモン 13 枚（ブビィ neo1-022・NIP1X-002、ピチュー neo1-042・PF2-007・NIP2X-002、エレキッド neo1-044、ピィ neo1-070・PRN-012、バルキー neo2-033、ププリン neo2-05…。 文書: [baby-rules-evolution-v0.114.md](docs/baby-rules-evolution-v0.114.md)
- v0.113（`kyuura_engine` の版は 0.113.0）: 可変枚数のコインと、山札の検索・つける・場全体のトラッシュのポケモン 6 枚…。 文書: [variable-coins-search-attachments-v0.113.md](docs/variable-coins-search-attachments-v0.113.md)
- v0.112（`kyuura_engine` の版は 0.112.0）: 水エネルギーの個数によるコインとドロー・コインのマヒと自分のワザの制限のポケモン 2 枚（ドククラゲ SI-016・オムスター PR1-051）のワザ 4 を、kyuura データの採用で登録した（写しの元・研究の基準は v0.97 の kyuura 73a1690 のまま）。 文書: [energy-coins-draw-v0.112.md](docs/energy-coins-draw-v0.112.md)
- v0.111（`kyuura_engine` の版は 0.111.0）: 場のエネルギーカードの枚数でダメージ・ワザの使用条件が決まるポケモン 4 枚（ミュウツー ES1-022・QSG-032、ナツメのケーシィ GD6-001・PR1-060。同じデータの 2 組で、id ごとに登録し登録の値を共有）のワザ 8 を…。 文書: [field-energy-card-counts-v0.111.md](docs/field-energy-card-counts-v0.111.md)
- v0.110（`kyuura_engine` の版は 0.110.0）: こらえる・こうてつかと、期間つきのきぜつ回避のポケモン 2 枚（ゴマゾウ neo1-053・わるいフォレトス neo4-008）のワザ 4 を、kyuura データの採用で登録した（写しの元・研究の基準は v0.97 の kyuura 73a1690 のまま）。 文書: [endure-armor-up-v0.110.md](docs/endure-armor-up-v0.110.md)
- v0.109（`kyuura_engine` の版は 0.109.0）: 期限つきの被ダメージ時のコインとサイコパニックのポケモン 3 枚（ウパー neo2-015・エビワラー neo4-070・ユンゲラー ES3-019）のワザ 6 を、kyuura データの採用で登録した…。 文書: [timed-damage-guards-v0.109.md](docs/timed-damage-guards-v0.109.md)
- v0.108（`kyuura_engine` の版は 0.108.0）: 持続するダメージの変更・相手の特殊状態を参照するポケモン 5 枚（ヘルガー neo2-041・チョンチー neo3-024・トゲピー neo4-088・わるいプクリン neo4-091・アーボック ES3-001）のワザ 10 を…。 文書: [damage-modifiers-condition-bonuses-v0.108.md](docs/damage-modifiers-condition-bonuses-v0.108.md)
- v0.107（`kyuura_engine` の版は 0.107.0）: コインによる成否・特殊状態・防護のポケモン 9 枚…。 文書: [coin-failure-status-flight-v0.107.md](docs/coin-failure-status-flight-v0.107.md)
- v0.106（`kyuura_engine` の版は 0.106.0）: 数とコインを組み合わせるポケモン 11 枚（グランブル neo1-068・ストライク neo2-008・カブトプス neo2-018・カモネギ neo3-046・イシツブテ ES1-023・ビリリダマ ES2-016・QSG-025・ニドリーナ ES3-002…。 文書: [counts-coins-compositions-v0.106.md](docs/counts-coins-compositions-v0.106.md)
- v0.105（`kyuura_engine` の版は 0.105.0）: 回復・山札からの進化・コインの分岐のポケモン 5 枚（トランセル neo2-006・ヒマナッツ neo4-003・バタフリー neo2-009・セレビィ PF3-002・デリバード neo3-050）のワザ 8 を、kyuura データの採用で登録した…。 文書: [recovery-evolution-coin-branches-v0.105.md](docs/recovery-evolution-coin-branches-v0.105.md)
- v0.104（`kyuura_engine` の版は 0.104.0）: 回復のワザを持つポケモン 12 枚（キレイハナ neo1-015・ミルタンク neo1-069・ヒメグマ neo2-048・イノムー neo3-041・フシギダネ ES1-001・QSG-001・IP1-018・ジュゴン ES2-007・QSG-018・プリン…。 文書: [healing-pokemon-v0.104.md](docs/healing-pokemon-v0.104.md)
- v0.103（`kyuura_engine` の版は 0.103.0）: ミュウ PR1-005・PR1-012（［ニュートラルシールド］・「ねんりき」）のワザ 2・特殊能力 2 を、kyuura データの採用で登録した…。 文書: [neutral-shield-attack-origin-v0.103.md](docs/neutral-shield-attack-origin-v0.103.md)
- v0.102（`kyuura_engine` の版は 0.102.0）: トランセル ES1-003・QSG-003（［グリーンシールド］・「ふしぎなこな」）・バリヤード ES1-021・QSG-030（［ニュートラルダメージ］・「ジャグリング」）のワザ 4・特殊能力 4 を、kyuura データの採用で登録した…。 文書: [weakness-resistance-powers-v0.102.md](docs/weakness-resistance-powers-v0.102.md)
- v0.101（`kyuura_engine` の版は 0.101.0）: ソーナンス neo2-031（「カウンター」）・アンノーンK neo3-030（［KEEP］・「めざめるパワー」）のワザ 2・特殊能力 1 を、kyuura データの採用で登録した（写しの元・研究の基準は v0.97 の kyuura 73a1690 のまま）。 文書: [counter-keep-energy-protection-v0.101.md](docs/counter-keep-energy-protection-v0.101.md)
- v0.100（`kyuura_engine` の版は 0.100.0）: ドーブル neo2-052（「スケッチ」）・ムウマ neo3-035（「やみのひとみ」「ほろびのうた」）のワザ 3 を、kyuura データの採用で登録した（写しの元・研究の基準は v0.97 の kyuura 73a1690 のまま）。 文書: [sketch-perish-song-history-v0.100.md](docs/sketch-perish-song-history-v0.100.md)
- v0.99（`kyuura_engine` の版は 0.99.0）: アンノーンP neo4-058（［PERFORM］）・H neo4-063（［HELP］）・タッツー neo1-023（「ひれがえし」）のワザ 3・特殊能力 2 を、kyuura データの採用で登録した…。 文書: [unown-perform-help-history-v0.99.md](docs/unown-perform-help-history-v0.99.md)
- v0.98（`kyuura_engine` の版は 0.98.0）: アンノーンB neo3-032（［BEAR］）・Y neo3-033（［YIELD］）・V neo4-053（［VANISH］）・G neo4-062（［GIVE］）のワザ 4・特殊能力 4 を、kyuura データの採用で登録した…。 文書: [unown-bear-yield-vanish-give-v0.98.md](docs/unown-bear-yield-vanish-give-v0.98.md)
- v0.97（`kyuura_engine` の版は 0.97.0）: kyuura のアンノーンI・D・F・[N]・[J] の調査（kyuura 73a1690。研究 78d090c を取り込んだ main）を取り込み、写しの元・研究の基準を 7d3f4ca から上げる移行を連鎖…。 文書: [unown-research-idfnj-v0.97.md](docs/unown-research-idfnj-v0.97.md)
- v0.96（`kyuura_engine` の版は 0.96.0）: アンノーン 7 枚（アンノーン[E] PF2-002（［ENGAGE］）・アンノーン[O] PF2-003（［OBSERVE］）・アンノーン[R] PRN-035（［REASSURE］）・アンノーンL neo4-050（［LAUGH］）・アンノーンS neo4…。 文書: [unown-family-powers-v0.96.md](docs/unown-family-powers-v0.96.md)
- v0.95（`kyuura_engine` の版は 0.95.0）: 手札・山札を見る効果とカードを動かすポケモン 11 枚…。 文書: [private-looks-deck-movement-v0.95.md](docs/private-looks-deck-movement-v0.95.md)
- v0.94（`kyuura_engine` の版は 0.94.0）: 入れ替え・帰還のワザのポケモン 13 枚（ピッピ ES1-026・QSG-040（このゆびとまれ・ひかるゆび）、プリン SI-002（ひとみでさそう・うたう）、ブルー neo1-061（ほえる・したでなめる）、モルフォン ES2-001（たつまきおこし・レイン…。 文書: [switch-return-attacks-v0.94.md](docs/switch-return-attacks-v0.94.md)
- v0.93（`kyuura_engine` の版は 0.93.0）: 「バトル場をはなれられない」効果・続くワザの制限を持つポケモン 9 枚…。 文書: [active-leave-locks-v0.93.md](docs/active-leave-locks-v0.93.md)
- v0.92（`kyuura_engine` の版は 0.92.0）: 特殊能力を止める効果・続く「にげる」とワザの禁止・受けるダメージを増やす効果を持つポケモン 8 枚…。 文書: [power-suppression-lasting-locks-v0.92.md](docs/power-suppression-lasting-locks-v0.92.md)
- v0.91（`kyuura_engine` の版は 0.91.0）: v0.90 で残したマーカーのポケモン 3 枚（マグマラシ neo1-020（えんまく・やきこがす）、エレブー ES2-017（ひらいしん・かみなりショック）、ポリゴン PRN-023（オールクリア・ハイパーテクスチャー））と…。 文書: [marker-check-field-reset-v0.91.md](docs/marker-check-field-reset-v0.91.md)
- v0.90（`kyuura_engine` の版は 0.90.0）: 先に v0.89 の ruff の指摘（TRY004）2 件を直した（選んだ個体の記録の型の誤りと、読み方で比べる選んだ個体へのダメージの基本の型の誤りを `TypeError` に。正常な処理・公開のエラーコードは変えていない）。 文書: [markers-counters-v0.90.md](docs/markers-counters-v0.90.md)
- v0.89（`kyuura_engine` の版は 0.89.0）: 対象を選ぶダメージ・選べる回復のポケモン 17 枚…。 文書: [selected-target-damage-v0.89.md](docs/selected-target-damage-v0.89.md)
- v0.88（`kyuura_engine` の版は 0.88.0）: 先に v0.85 の 6 か所が `is_face_down` にカードの uid を渡し、場にうらのカード（マチスの秘策）があると `AttributeError` になっていたのを直した。 文書: [type-energy-colors-v0.88.md](docs/type-energy-colors-v0.88.md)
- v0.87（`kyuura_engine` の版は 0.87.0）: 場の移動・ダメージへの反応と、控えの保護・「にげる」の禁止のポケモン 14 枚…。 文書: [movement-damage-reactions-v0.87.md](docs/movement-damage-reactions-v0.87.md)
- v0.86: 登場・エネルギー・進化への反応 13 枚（イーブイ neo2-049・PF2-005・PRN-024、エンテイ neo3-010・PF2-008、ライコウ neo3-029、ハピナス neo3-052、カイリュー PR1-056、わるいクロバット neo4-0…。 文書: [entry-energy-evolution-reactions-v0.86.md](docs/entry-energy-evolution-reactions-v0.86.md)
- v0.85（`kyuura_engine` の版は 0.85.0）: 進化したときの特殊能力・エネルギーを動かす特殊能力のポケモン 13 枚…。 文書: [entry-powers-energy-lifecycle-v0.85.md](docs/entry-powers-energy-lifecycle-v0.85.md)
- v0.84（`kyuura_engine` の版は 0.84.0）: 先に v0.83 の 3 つの不具合を直した（リフレクトシールドの「おもて」の 20 を、ワザの途中の決定・状態の保存をまたいで運ぶ。かげぶんしん・「とうめい」とリフレクトシールドが同じポケモンに重なる場面を、状態を変える前に新しい問い RF1 で止める。みず…。 文書: [light-powers-evolution-v0.84.md](docs/light-powers-evolution-v0.84.md)
- v0.83（`kyuura_engine` の版は 0.83.0）: 先に v0.82 のエコロジムとリサイクルエネルギーの不要な TE2 を直した…。 文書: [shining-gentle-pokemon-v0.83.md](docs/shining-gentle-pokemon-v0.83.md)
- v0.82（`kyuura_engine` の版は 0.82.0）: 先に v0.81a のきのみの修正の漏れを直した（きのみどうしでも、回復でかがくへんかガス・［へんしん］がもどってほかのポケモンの問い合わせが変わるなら、並べ方を比べて BY1。比べるきのみが 3 つより多ければエンジンの未対応 `UNSUPPORTED_BE…。 文書: [energy-discard-return-v0.82.md](docs/energy-discard-return-v0.82.md)
- v0.81a（`kyuura_engine` の版は 0.81.1）: v0.81 の修正（新しいカードはない）。 文書: [berry-maxhp-fixes-v0.81a.md](docs/berry-maxhp-fixes-v0.81a.md)
- v0.81（`kyuura_engine` の版は 0.81.0）: v0.80 の追補として、手札・山札の中身から選ぶ決定 7 種類の選べるものの数を、決めるプレイヤーでない人の観測に見せないようにし（見えない情報の修正）、v0.80 の文書の誤り 3 点を直した。 文書: [pokemon-tools-stadiums-v0.81.md](docs/pokemon-tools-stadiums-v0.81.md)
- v0.80（`kyuura_engine` の版は 0.80.0）: v0.79 の共通処理を 2 つ直した。 文書: [neo-trainer-components-v0.80.md](docs/neo-trainer-components-v0.80.md)
- v0.79（`kyuura_engine` の版は 0.79.0）: v0.78 の共通処理を直した。 文書: [shared-checks-pokemon-reuse-v0.79.md](docs/shared-checks-pokemon-reuse-v0.79.md)
- v0.78（`kyuura_engine` の版は 0.78.0）: 悪エネルギー（neo1-094・PRN-002・NIP2X-010）・鋼エネルギー（neo1-095・NIP1X-010）の特殊エネルギー 5 枚と、「悪」「鋼」エネルギーを使うポケモン 8 枚…。 文書: [darkness-metal-energy-v0.78.md](docs/darkness-metal-energy-v0.78.md)
- v0.77（`kyuura_engine` の版は 0.77.0）: neo 期の拡張パック（neo1〜neo4。kyuura の id のまま）を実装の対象に加え、既存の効果の型で表せる 52 枚（ポケモン 50 枚・ワザ 77、トレーナーのスーパーポケモン回収 neo1-083・マサキの転送装置 neo1-084）を…。 文書: [neo-existing-effects-v0.77.md](docs/neo-existing-effects-v0.77.md)
- v0.76（`kyuura_engine` の版は 0.76.0）: 拡張パック以外の商品の、持続する効果・ワザの使用の制限を中心とするポケモン 24 枚…。 文書: [persistent-attack-modifiers-v0.76.md](docs/persistent-attack-modifiers-v0.76.md)
- v0.75（`kyuura_engine` の版は 0.75.0）: 拡張パック以外の商品のポケモン 15 枚（タケシのズバット GD1-001・カスミのコダック GD2-001・カスミのメノクラゲ GD2-003・カツラのロコン GD5-003・カツラのガーディ GD5-006・ナツメのスリープ GD6-009・パラス ES1…。 文書: [search-energy-pokemon-v0.75.md](docs/search-energy-pokemon-v0.75.md)
- v0.74（`kyuura_engine` の版は 0.74.0）: 拡張パック以外の商品のスタジアム 13 枚（ポケモンタワー ES3-036・キョウの忍者ジム PR1-067・エネルギースタジアム NIP1X-009・ラッキースタジアム NIP2X-009・PRN-015〜PRN-022・PRN-027）を…。 文書: [remaining-stadiums-v0.74.md](docs/remaining-stadiums-v0.74.md)
- v0.73（`kyuura_engine` の版は 0.73.0）: 拡張パック以外の商品の、検索・回収・ドローのトレーナー 18 枚…。 文書: [search-recovery-trainers-v0.73.md](docs/search-recovery-trainers-v0.73.md)
- v0.72（`kyuura_engine` の版は 0.72.0）: 拡張パック以外の商品のポケモン 43 枚（kyuura data/engine_targets.json の `new_effect_needed`。ワザ 77）を、kyuura データの採用で、どのワザも登録して対応にした…。 文書: [status-coins-effect-reuse-v0.72.md](docs/status-coins-effect-reuse-v0.72.md)
- v0.71（`kyuura_engine` の版は 0.71.0）: 拡張パック以外の商品（ポケモンジム・クイックスターターギフト・イントロパック・イントロパック★neo・プロモ）の再録のカード 78 枚（トレーナー 67 枚・ポケモン 11 枚）を、kyuura データの採用で、どのトレーナーも…。 文書: [reprint-text-variants-v0.71.md](docs/reprint-text-variants-v0.71.md)
- v0.70（`kyuura_engine` の版は 0.70.0）: 拡張パック以外の商品（ポケモンジム・拡張シート・クイックスターターギフト・イントロパック・プレミアムファイル・プロモーションなど）のポケモン 82 枚を、kyuura データの採用で、どのワザも登録して対応にした…。 文書: [non-pack-effect-reuse-v0.70.md](docs/non-pack-effect-reuse-v0.70.md)
- v0.69（`kyuura_engine` の版は 0.69.0）: kyuura の形式 3 のカードデータと v0.68 までの記録を取り込んだ研究の記録（kyuura `7d3f4ca`）に移り、拡張パック以外の商品（ポケモンジム・イントロパック・プロモーション・2001 年のイントロパック）のカードのうち…。 文書: [equivalent-non-pack-cards-v0.69.md](docs/equivalent-non-pack-cards-v0.69.md)
- v0.68（`kyuura_engine` の版は 0.68.0）: PMCG1〜PMCG6 の残りのポケモン 3 枚を対応にした（PMCG1〜PMCG6 の未対応は 0 枚、対応するカード 457/457）。 文書: [final-pmcg-cards-v0.68.md](docs/final-pmcg-cards-v0.68.md)
- v0.67（`kyuura_engine` の版は 0.67.0）: マチスの秘策 PMCG5-093（手札から 1 枚をうらにしてベンチに出してよい。うらのあいだは「たねポケモン」としてあつかい、ワザ・特殊能力・進化・にげる・ダメージや効果を受ける時と、自分の番に選んで（`RevealFaceDown`）おもてにする。たねポケ…。 文書: [secret-plan-preflight-v0.67.md](docs/secret-plan-preflight-v0.67.md)
- v0.66（`kyuura_engine` の版は 0.66.0）: プレイヤーが「のぞむなら」選ぶ・両方のプレイヤーが選ぶトレーナー 3 枚…。 文書: [optional-trainers-v0.66.md](docs/optional-trainers-v0.66.md)
- v0.65（`kyuura_engine` の版は 0.65.0）: ワザの最中に、ワザを受ける側のプレイヤーが「使う・使わない」を選ぶ 3 枚…。 文書: [reactive-decisions-v0.65.md](docs/reactive-decisions-v0.65.md)
- v0.64（`kyuura_engine` の版は 0.64.0）: 化石の秘密のイシツブテの系統 3 枚（イシツブテ PMCG3-034 のれんぞくいしなげ（「うら」が出るまでコインを投げ、「おもて」の数 × 10）・ゴローン PMCG3-037 のかたくなる・いわおとし・ゴローニャ PMCG3-038 のいわころがり・じばく…。 文書: [geodude-line-unbounded-coins-v0.64.md](docs/geodude-line-unbounded-coins-v0.64.md)
- v0.63: 公開・非公開の状態を扱うトレーナー 4 枚（ロケット団参上! PMCG4-062（お互いのサイドを、そのときサイドにあるカードごとにおもてにする。`GameState.face_up_prizes`）・くすぐりマシーン PMCG6-084（「おもて」なら相手の…。 文書: [hidden-card-trainers-v0.63.md](docs/hidden-card-trainers-v0.63.md)
- v0.62（`kyuura_engine` の版は 0.62.0）: 前の番のワザの履歴を読むワザ・相手を手札にもどすワザの 5 枚と、確定した修正を当てはめたベロリンガ…。 文書: [history-attacks-v0.62.md](docs/history-attacks-v0.62.md)
- v0.61（`kyuura_engine` の版は 0.61.0）: ワザ・にげる・残りHPではたらく特殊能力とトレーナーのダメージの 4 枚…。 文書: [reactive-powers-trainer-damage-v0.61.md](docs/reactive-powers-trainer-damage-v0.61.md)
- v0.60（`kyuura_engine` の版は 0.60.0）: 控えへのコイン・ダメージを受けない効果・攻撃するときの特殊能力・相手の効果を受けないダメージの 4 枚…。 文書: [coins-defense-rebellion-v0.60.md](docs/coins-defense-rebellion-v0.60.md)
- v0.59（`kyuura_engine` の版は 0.59.0）: 特殊能力を止める効果・エネルギーをつける操作を変える効果の 6 枚…。 文書: [energy-control-power-suppression-v0.59.md](docs/energy-control-power-suppression-v0.59.md)
- v0.58（`kyuura_engine` の版は 0.58.0）: スタジアムの処理を再利用するカード 3 枚（タケシのゴローン PMCG5-052 のばくれつ（場のスタジアムをトラッシュ）・タケシのゴローニャ PMCG5-053 のいわなだれ・ナツメのサイキックコントロール PMCG6-088（相手のトラッシュのトレーナーを…。 文書: [stadium-reuse-special-energy-v0.58.md](docs/stadium-reuse-special-energy-v0.58.md)
- v0.57（`kyuura_engine` の版は 0.57.0）: 未対応だったスタジアム 14 枚（ニビシティジム PMCG5-079・ハナダシティジム PMCG5-080・抵抗力低下ジム PMCG5-091・ロケット団の特訓ジム PMCG5-095・グレンタウンジム PMCG6-085・タマムシシティジム PMCG5-07…。 文書: [stadiums-v0.57.md](docs/stadiums-v0.57.md)
- v0.56（`kyuura_engine` の版は 0.56.0）: 相手の決定・番の終わり・期限のある効果のトレーナー 10 枚…。 文書: [trainer-decisions-turn-effects-v0.56.md](docs/trainer-decisions-turn-effects-v0.56.md)
- v0.55（`kyuura_engine` の版は 0.55.0）: すぐに使い終わるトレーナー 16 枚（カスミのいかり PMCG5-075・ロケット団のおねーさん PMCG4-061・礼儀作法 PMCG5-082・トラッシュ交換 PMCG6-077・エネルギー・リムーブ PMCG1-070・超エネルギーリムーブ PMCG1-…。 文書: [instant-trainers-v0.55.md](docs/instant-trainers-v0.55.md)
- v0.54（`kyuura_engine` の版は 0.54.0）: 手札の入れ替え・ドロー・情報の確認のトレーナー 10 枚…。 文書: [hand-deck-trainers-v0.54.md](docs/hand-deck-trainers-v0.54.md)
- v0.53（`kyuura_engine` の版は 0.53.0）: 山札・トラッシュからカードを選ぶトレーナー 10 枚…。 文書: [search-retrieval-trainers-v0.53.md](docs/search-retrieval-trainers-v0.53.md)
- v0.52（`kyuura_engine` の版は 0.52.0）: 場のポケモンを場から手札・山札にもどす共通の処理（どのカードも同じ uid・同じ持ち主のまま動かし、場のポケモンの番号は無効になる。持続する効果・特殊状態・ダメージカウンターはなくなる。きぜつではない）を整え、フジろうじん PMCG3-048…。 文書: [field-return-v0.52.md](docs/field-return-v0.52.md)
- v0.51（`kyuura_engine` の版は 0.51.0）: トラッシュのたねポケモンのカードを、同じ uid・同じ持ち主のまま持ち主のベンチに出す共通の処理…。 文書: [discard-to-bench-v0.51.md](docs/discard-to-bench-v0.51.md)
- v0.50（`kyuura_engine` の版は 0.50.0）: 場のポケモンの進化カードをはがす「退化」の共通の処理…。 文書: [mew-devolution-spray-v0.50.md](docs/mew-devolution-spray-v0.50.md)
- v0.49（`kyuura_engine` の版は 0.49.0）: 場のポケモンについて「実際のカード」「今の姿」「今使えるワザとその出どころ」「今持つ特殊能力とその出どころ」を区別する共通の処理…。 文書: [virtual-attacks-transformation-v0.49.md](docs/virtual-attacks-transformation-v0.49.md)
- v0.48（`kyuura_engine` の版は 0.48.0）: 場のポケモンの今有効な最大HP・タイプ（色）・弱点・抵抗力を一か所で求める処理…。 文書: [effective-pokemon-properties-v0.48.md](docs/effective-pokemon-properties-v0.48.md)
- v0.47（`kyuura_engine` の版は 0.47.0）: ポケモンとして場に出せるトレーナーカード（なにかの化石 PMCG3-046・ピッピ人形 PMCG1-091）と化石のポケモン…。 文書: [fossil-hidden-info-v0.47.md](docs/fossil-hidden-info-v0.47.md)
- v0.46（`kyuura_engine` の版は 0.46.0）: 常にはたらく特殊能力（どれも使用を宣言しない）を持つポケモン 8 枚と、関連する 3 枚を、どのワザ・どの特殊能力も登録して対応にした…。 文書: [continuous-powers-v0.46.md](docs/continuous-powers-v0.46.md)
- v0.45（`kyuura_engine` の版は 0.45.0）: 条件つきのダメージ・エネルギーの移動とトラッシュ・受けたダメージを返す効果などのポケモン 15 枚を、どのワザも登録して対応にした…。 文書: [conditional-damage-energy-v0.45.md](docs/conditional-damage-energy-v0.45.md)
- v0.44（`kyuura_engine` の版は 0.44.0）: 検索・進化・1 度だけ使えるワザのポケモン 14 枚とトレーナーのサカキを、どのワザ・どの特殊能力・トレーナーも登録して対応にした…。 文書: [search-evolution-once-attacks-v0.44.md](docs/search-evolution-once-attacks-v0.44.md)
- v0.43（`kyuura_engine` の版は 0.43.0）: 宣言して使う特殊能力 6 つと、場に出たときに使う特殊能力 3 つを持つ 9 枚を、どのワザ・どの特殊能力も登録して対応にした…。 文書: [declared-entry-powers-v0.43.md](docs/declared-entry-powers-v0.43.md)
- v0.42（`kyuura_engine` の版は 0.42.0）: 回復・カウンター操作と、特殊能力を持つ進化系統を中心とする 15 枚を、どのワザ・どの特殊能力も登録して対応にした…。 文書: [power-decisions-v0.42.md](docs/power-decisions-v0.42.md)
- v0.41（`kyuura_engine` の版は 0.41.0）: 回復・ダメージカウンターの移動・特殊状態の変化を中心とする 15 枚を対応にした…。 文書: [heal-counter-status-v0.41.md](docs/heal-counter-status-v0.41.md)
- v0.40（`kyuura_engine` の版は 0.40.0）: 場の数・条件付きの効果・入れ替え・カードの移動を中心とする 15 枚を対応にした…。 文書: [count-condition-switch-return-v0.40.md](docs/count-condition-switch-return-v0.40.md)
- v0.39（`kyuura_engine` の版は 0.39.0）: じばく・控えへのダメージ・場のポケモンの数でダメージが決まるワザを中心とする 15 枚を対応にした…。 文書: [selfdestruct-spread-count-v0.39.md](docs/selfdestruct-spread-count-v0.39.md)
- v0.38（`kyuura_engine` の版は 0.38.0）: 控えへのダメージ・入れ替え・同じコインの複数の効果・軽減・山札にもどる効果の 15 枚を対応にした…。 文書: [bench-switch-combined-v0.38.md](docs/bench-switch-combined-v0.38.md)
- v0.37（`kyuura_engine` の版は 0.37.0）: 既存の効果の再利用を中心に、依頼の 15 枚を対応にした…。 文書: [fifteen-reused-effects-v0.37.md](docs/fifteen-reused-effects-v0.37.md)
- v0.36（`kyuura_engine` の版は 0.36.0）: p.309 のワザを使う手順 4「ワザを失敗させたりワザの内容を変えてしまう効果」のコインを加えた…。 文書: [sand-attack-retreat-lock-v0.36.md](docs/sand-attack-retreat-lock-v0.36.md)
- v0.35（`kyuura_engine` の版は 0.35.0）: 結果を「おもて」の数だけで使うコイン（たまなげMAX・ウォーターパンチ・ぜんりょくとっしん・ほうでん・ちょうのうりょく・ドリルタックルなど）を、宣言の前の先読みが「おもて」の数でまとめて試すようにした…。 文書: [coin-groups-damage-order-v0.35.md](docs/coin-groups-damage-order-v0.35.md)
- v0.34（`kyuura_engine` の版は 0.34.0）: 「ワザをうけない」状態（バリアー）の相手へのコインを、コインが決めるものの意味からそろえた…。 文書: [barrier-resume-coin-bonus-v0.34.md](docs/barrier-resume-coin-bonus-v0.34.md)
- v0.33（`kyuura_engine` の版は 0.33.0）: v0.32 で未解決にした CD4（ルージュラの「ヨガのポーズ」の「相手のポケモン」）を kyuura とエンジンの既存の記録で再検討し、記録では決まらないので未解決のままにした…。 文書: [cd4-opponent-energy-coins-v0.33.md](docs/cd4-opponent-energy-coins-v0.33.md)
- v0.32（`kyuura_engine` の版は 0.32.0）: 依頼の 13 枚を対応にした。 文書: [bench-search-counter-drain-v0.32.md](docs/bench-search-counter-drain-v0.32.md)
- v0.31（`kyuura_engine` の版は 0.31.0）: v0.30 で保留した 22 枚をまとめて対応にした…。 文書: [held-cards-v0.31.md](docs/held-cards-v0.31.md)
- v0.30（`kyuura_engine` の版は 0.30.0）: 「自分の炎エネルギーカードを 1 枚トラッシュして、相手にダメージを与える」ワザを 1 つの効果の型（`DiscardEnergyThenDamage`）にまとめ、ポケモン 5 枚…。 文書: [discard-energy-attacks-v0.30.md](docs/discard-energy-attacks-v0.30.md)
- v0.29（`kyuura_engine` の版は 0.29.0）: 既存の効果の型の登録だけで対応できるポケモン 14 枚をまとめて加えた…。 文書: [card-data-policy.md](docs/card-data-policy.md)・[existing-effect-pokemon-v0.29.md](docs/existing-effect-pokemon-v0.29.md)
- v0.28（`kyuura_engine` の版は 0.28.0）: 既存の効果の型の登録だけで対応できるポケモン 10 枚をまとめて加えた…。 文書: [existing-effect-pokemon-v0.28.md](docs/existing-effect-pokemon-v0.28.md)
- v0.27（`kyuura_engine` の版は 0.27.0）: ストライク（PMCG2-017。ポケモンジャングル）を加えた。 文書: [scyther-v0.27.md](docs/scyther-v0.27.md)・[v0.27-verification.md](docs/v0.27-verification.md)
- v0.26（`kyuura_engine` の版は 0.26.0）: 固定のデッキの第2版を、第1版と別の識別子で加えた…。 文書: [preset-decks-v0.26.md](docs/preset-decks-v0.26.md)・[v0.26-verification.md](docs/v0.26-verification.md)
- v0.25（`kyuura_engine` の版は 0.25.0）: トレーナーのポケモン育て屋さん（PMCG1-094。p.259 の最新の説明「このカードは、あなたが自分の場にいるポケモンを進化させるときにだけ、使える。そのポケモンの上に「2進化カード」を直接のせ、1進化をとばして「2進化ポケモン」に進化させる。」）を…。 文書: [pokemon-breeder-v0.25.md](docs/pokemon-breeder-v0.25.md)・[v0.25-verification.md](docs/v0.25-verification.md)
- v0.24（`kyuura_engine` の版は 0.24.0）: トレーナーのポケモン交換おじさん（PMCG1-093。p.259 の最新の説明「手札から「たねポケモン」または「進化カード」を1枚選び、相手プレイヤーに見せてから、あなたの山札にもどす。それができないとき、このカードは使えない。あなたの山札から「たねポケモン」…。 文書: [pokemon-trader-v0.24.md](docs/pokemon-trader-v0.24.md)・[v0.24-verification.md](docs/v0.24-verification.md)
- v0.23（`kyuura_engine` の版は 0.23.0）: 突風とパソコン通信を同じデッキに入れた対戦を確かめた…。 文書: [energy-retrieval-v0.23.md](docs/energy-retrieval-v0.23.md)・[v0.23-verification.md](docs/v0.23-verification.md)
- v0.22（`kyuura_engine` の版は 0.22.0）: トレーナーのパソコン通信（PMCG1-090。p.260 の最新の説明「手札からカードを2枚選んでトラッシュしなければ、このカードは使えない。あなたの山札からカードを1枚選び出し、手札に加える。その後、その山札をよく切る。」）を…。 文書: [computer-search-v0.22.md](docs/computer-search-v0.22.md)・[v0.22-verification.md](docs/v0.22-verification.md)
- v0.21（`kyuura_engine` の版は 0.21.0）: トレーナーの突風（PMCG1-072。使ったプレイヤーが相手の控えポケモンを 1 匹選び、相手の対戦ポケモンと入れ替える。p.255 の最新の説明）を、既存のトレーナーの登録・使用中のカード・トレーナーの決定と、ポケモンいれかえと共通にした入れ替えの処理…。 文書: [gust-v0.21.md](docs/gust-v0.21.md)・[v0.21-verification.md](docs/v0.21-verification.md)
- v0.20（`kyuura_engine` の版は 0.20.0）: 対応済みのカードだけで組んだ固定のデッキを 2 つ加え、識別子で選んで正式な対戦開始に渡せるようにした…。 文書: [preset-decks-v0.20.md](docs/preset-decks-v0.20.md)・[v0.20-verification.md](docs/v0.20-verification.md)
- v0.19（`kyuura_engine` の版は 0.19.0）: トレーナーのオーキドはかせ（PMCG1-077。手札をすべてトラッシュし、その後、山札から 7 枚引く。p.255 の最新の説明）を、既存のトレーナーの登録・使用中のカード・ドローの処理で加えた…。 文書: [professor-oak-v0.19.md](docs/professor-oak-v0.19.md)・[v0.19-verification.md](docs/v0.19-verification.md)
- v0.18（`kyuura_engine` の版は 0.18.0）: 研究データ（kyuura）とエンジンが同じ出典・裁定を追跡できるようにした。 文書: [research-alignment-v0.18a.md](docs/research-alignment-v0.18a.md)・[unresolved-research-v0.18b.md](docs/unresolved-research-v0.18b.md)・[kernel-reuse-v0.18c.md](docs/kernel-reuse-v0.18c.md)・[mid-window-decisions-v0.18d.md](docs/mid-window-decisions-v0.18d.md)・[verification-reproducibility-v0.18e.md](docs/verification-reproducibility-v0.18e.md)・[v0.18-verification.md](docs/v0.18-verification.md)
- v0.17（`kyuura_engine` の版は 0.17.0）: 実際のカードで、解決の基盤（KERNEL）の拡張性を確かめた。 文書: [card-selection-v0.17a.md](docs/card-selection-v0.17a.md)・[card-implementation-v0.17a.md](docs/card-implementation-v0.17a.md)・[rocket-snorlax-v0.17b.md](docs/rocket-snorlax-v0.17b.md)・[kogas-muk-event-design-v0.17c.md](docs/kogas-muk-event-design-v0.17c.md)・[card-extensibility-verification-v0.17d.md](docs/card-extensibility-verification-v0.17d.md)
- v0.16（`kyuura_engine` の版は 0.16.0）: v0.13 のワザの解決の経路と経路の切り替え（`Route`・`apply_command_via`）を外し、ワザ・番の終わり・きぜつのあとの決定（サイド・交代・こんじょう・ふしちょう）を解決の基盤（`kyuura_engine/resolution`）だけで処理するようにした。 文書: [legacy-removal-audit-v0.16a.md](docs/legacy-removal-audit-v0.16a.md)・[kernel-consolidation-v0.16b.md](docs/kernel-consolidation-v0.16b.md)・[preflight-consolidation-v0.16c.md](docs/preflight-consolidation-v0.16c.md)・[legacy-test-migration-v0.16d.md](docs/legacy-test-migration-v0.16d.md)・[kernel-consolidation-verification-v0.16e.md](docs/kernel-consolidation-verification-v0.16e.md)
- v0.15（`kyuura_engine` の版は 0.15.0）: v0.14 のプロトタイプを本番の内部の部品（`kyuura_engine/resolution`）にし、ワザ・番の終わり・きぜつのあとの決定（サイド・交代・こんじょう・ふしちょう）の解決を、標準でこの基盤（経路 `KERNEL`）で処理するようにした。 文書: [integration-dependencies-v0.15a.md](docs/integration-dependencies-v0.15a.md)・[kernel-integration-v0.15b.md](docs/kernel-integration-v0.15b.md)・[preflight-optimization-v0.15c.md](docs/preflight-optimization-v0.15c.md)・[event-integration-verification-v0.15d.md](docs/event-integration-verification-v0.15d.md)
- v0.14（設計の試作。本番のエンジンは変えていない）: カード効果ごとの専用の処理を、汎用のイベント・効果の解決の仕組みに移すのが適切かを確かめた。 文書: [event-architecture-audit-v0.14.md](docs/event-architecture-audit-v0.14.md)・[event-architecture-options-v0.14.md](docs/event-architecture-options-v0.14.md)・[event-model-v0.14.md](docs/event-model-v0.14.md)・[event-prototype-verification-v0.14.md](docs/event-prototype-verification-v0.14.md)・[event-migration-plan-v0.14.md](docs/event-migration-plan-v0.14.md)
- v0.13: わるいカメール（PMCG4-021。ポケモンカード第4弾 ロケット団。ゼニガメから進化する 1 進化）のワザ「こうらがえし」…。 文書: [shell-attack-v0.13.md](docs/shell-attack-v0.13.md)・[dark-wartortle-v0.13.md](docs/dark-wartortle-v0.13.md)・[variable-retaliation-v0.13.md](docs/variable-retaliation-v0.13.md)・[architecture-v0.13.md](docs/architecture-v0.13.md)・[v0.13-verification.md](docs/v0.13-verification.md)
- v0.12: R団のファイヤー（PMCG5-020。ジム拡張第1弾 リーダーズスタジアム）のポケモンパワー「ふしちょう」…。 文書: [phoenix-v0.12.md](docs/phoenix-v0.12.md)・[rocket-moltres-v0.12.md](docs/rocket-moltres-v0.12.md)・[post-knockout-powers-v0.12.md](docs/post-knockout-powers-v0.12.md)・[temporary-attack-effects-v0.12.md](docs/temporary-attack-effects-v0.12.md)・[architecture-v0.12.md](docs/architecture-v0.12.md)・[v0.12-verification.md](docs/v0.12-verification.md)
- v0.11: サカキのカイリキー（PMCG6-061。ジム拡張第2弾 闇からの挑戦）のポケモンパワー「こんじょう」…。 文書: [guts-v0.11.md](docs/guts-v0.11.md)・[giovanni-machamp-line-v0.11.md](docs/giovanni-machamp-line-v0.11.md)・[ko-prevention-v0.11.md](docs/ko-prevention-v0.11.md)・[architecture-v0.11.md](docs/architecture-v0.11.md)・[v0.11-verification.md](docs/v0.11-verification.md)
- v0.10: カイリキー（PMCG1-057。第1弾）のポケモンパワー「はんげき」…。 文書: [counterattack-v0.10.md](docs/counterattack-v0.10.md)・[machamp-line-v0.10.md](docs/machamp-line-v0.10.md)・[post-damage-powers-v0.10.md](docs/post-damage-powers-v0.10.md)・[architecture-v0.10.md](docs/architecture-v0.10.md)・[v0.10-verification.md](docs/v0.10-verification.md)
- v0.9: ゴースト（PMCG3-030。化石の秘密）のポケモンパワー「とうめい」（ワザによってダメージや効果を受けるとき、自動的にはたらく。コインを投げて「おもて」なら、そのダメージと効果を受けない。ねむり・マヒ・こんらんのとき、この力は消える）とワザ「あくむ」…。 文書: [transparency-v0.9.md](docs/transparency-v0.9.md)・[haunter-line-v0.9.md](docs/haunter-line-v0.9.md)・[automatic-powers-v0.9.md](docs/automatic-powers-v0.9.md)・[architecture-v0.9.md](docs/architecture-v0.9.md)・[v0.9-verification.md](docs/v0.9-verification.md)
- v0.8: ベトベトン（PMCG3-007）のポケモンパワー「かがくへんかガス」…。 文書: [chemical-gas-v0.8.md](docs/chemical-gas-v0.8.md)・[grimer-line-v0.8.md](docs/grimer-line-v0.8.md)・[continuous-effects-v0.8.md](docs/continuous-effects-v0.8.md)・[architecture-v0.8.md](docs/architecture-v0.8.md)・[v0.8-verification.md](docs/v0.8-verification.md)
- v0.7: フーディン（PMCG1-049）のポケモンパワー「ダメージスワップ」（自分の番の中で何度でも、この力によってポケモンが「きぜつ」しないかぎり、自分の場のポケモンにのっているダメージカウンターを自分の場の別のポケモンにのせかえる）とワザ「あやしいひかり」…。 文書: [damage-swap-v0.7.md](docs/damage-swap-v0.7.md)・[alakazam-line-v0.7.md](docs/alakazam-line-v0.7.md)・[architecture-v0.7.md](docs/architecture-v0.7.md)・[v0.7-verification.md](docs/v0.7-verification.md)
- v0.6: カメックス（PMCG1-032）のポケモンパワー「あまごい」（自分の番の中で何度でも、手札の「水」エネルギーカードを自分の場の「水」ポケモンにつける）とワザ「ハイドロポンプ」（40+）、進化元のゼニガメ（あわ・からにこもる）・カメール（からにこもる・かみつく）を実装した。 文書: [rain-dance-v0.6.md](docs/rain-dance-v0.6.md)・[architecture-v0.6.md](docs/architecture-v0.6.md)・[v0.6-verification.md](docs/v0.6-verification.md)
- v0.5: ポケモンパワー（2000.02.14 版の用語では「特殊能力」）の基盤（`UsePokemonPower`・パワーの登録表）を、フシギバナ（PMCG1-011）の「エナジートランス」と、進化元のフシギダネ（やどりぎのタネ）・フシギソウ…。 文書: [pokemon-powers-v0.5.md](docs/pokemon-powers-v0.5.md)・[venusaur-v0.5.md](docs/venusaur-v0.5.md)・[bulbasaur-line-v0.5.md](docs/bulbasaur-line-v0.5.md)・[energy-transfer-v0.5.md](docs/energy-transfer-v0.5.md)・[architecture-v0.5.md](docs/architecture-v0.5.md)・[v0.5-verification.md](docs/v0.5-verification.md)
- v0.4e: カード・ルールを加えず、v0.4a〜v0.4d（進化・持続する効果・2 進化・強制交代・与えたダメージ・メガドレイン）の総合監査をした。 文書: [integration-audit-v0.4e.md](docs/integration-audit-v0.4e.md)・[interaction-matrix-v0.4e.md](docs/interaction-matrix-v0.4e.md)・[compatibility-v0.4e.md](docs/compatibility-v0.4e.md)・[unresolved-audit-v0.4e.md](docs/unresolved-audit-v0.4e.md)・[architecture-v0.4e.md](docs/architecture-v0.4e.md)・[v0.5-readiness.md](docs/v0.5-readiness.md)
- v0.4d: ワザの途中で相手プレイヤーの決定を待ち、答えのあとで同じワザを再開する処理と、ワザが与えたダメージの結果（`DamageResult`）を後の要素に渡す処理を、バタフリー（トランセルから進化する 2 進化）の「ふきとばし」…。 文書: [forced-switch-v0.4d.md](docs/forced-switch-v0.4d.md)・[damage-drain-v0.4d.md](docs/damage-drain-v0.4d.md)・[butterfree-v0.4d.md](docs/butterfree-v0.4d.md)・[architecture-v0.4d.md](docs/architecture-v0.4d.md)
- v0.4c: 2 進化（1 進化ポケモン → 2 進化ポケモン）を、スピアー（コクーンから進化）の「ダブルニードル」（コイン 2 枚、「おもて」の数 × 30）・「どくばり」（40、「おもて」なら相手をどく状態に）とともに実装した。 文書: [stage2-evolution-v0.4c.md](docs/stage2-evolution-v0.4c.md)・[beedrill-v0.4c.md](docs/beedrill-v0.4c.md)・[stage2-state-v0.4c.md](docs/stage2-state-v0.4c.md)・[architecture-v0.4c.md](docs/architecture-v0.4c.md)
- v0.4b: ワザによる持続する効果（番をまたいで残り、期限・ベンチに戻る・進化・きぜつで消える。特殊状態・ついているトレーナーとは別に持つ）を、トランセル（キャタピーから進化）・コクーン（ビードルから進化）の「かたまる」…。 文書: [persistent-effects-v0.4b.md](docs/persistent-effects-v0.4b.md)・[harden-v0.4b.md](docs/harden-v0.4b.md)・[persistent-damage-v0.4b.md](docs/persistent-damage-v0.4b.md)・[architecture-v0.4b.md](docs/architecture-v0.4b.md)
- v0.4a: 進化（たねポケモン → 1 進化ポケモン）を、パラセクト（パラスから進化）・ジュゴン（パウワウから進化）とともに実装した。 文書: [evolution-rules-v0.4a.md](docs/evolution-rules-v0.4a.md)・[evolution-cards-v0.4a.md](docs/evolution-cards-v0.4a.md)・[evolution-state-v0.4a.md](docs/evolution-state-v0.4a.md)・[architecture-v0.4a.md](docs/architecture-v0.4a.md)
- v0.3d: カード・ルールを加えず、特殊状態 4 種類のすべての組み合わせ（8 つの状態 × 付与・上書き・解除・操作・ポケモンチェック）を、新しい対戦からの総合テスト・負荷テスト・変異テストとともに確かめた。 文書: [special-conditions-audit-v0.3d.md](docs/special-conditions-audit-v0.3d.md)・[unresolved-rulings-v0.3d.md](docs/unresolved-rulings-v0.3d.md)・[effect-preflight-v0.3d.md](docs/effect-preflight-v0.3d.md)・[architecture-v0.3d.md](docs/architecture-v0.3d.md)・[evolution-readiness-v0.4.md](docs/evolution-readiness-v0.4.md)
- v0.3c: 「こんらん」と、こんらん状態のポケモンのワザ（宣言のあとにコインを投げ、「うら」ならワザの内容の代わりに自分に 20 ダメージ。弱点・抵抗力の影響を受ける）・にげる…。 文書: [confusion-v0.3c.md](docs/confusion-v0.3c.md)・[confusion-attacks-v0.3c.md](docs/confusion-attacks-v0.3c.md)・[retreat-confusion-v0.3c.md](docs/retreat-confusion-v0.3c.md)・[architecture-v0.3c.md](docs/architecture-v0.3c.md)
- v0.3b: 「ねむり」「マヒ」と、それによるワザ・にげるの制限、ポケモンチェックの 3（ねむりのコイン）・4（マヒの自動回復）を、キャタピーの「いとをはく」・パラスの「ひっかく」「キノコのほうし」とともに実装した。 文書: [sleep-paralysis-v0.3b.md](docs/sleep-paralysis-v0.3b.md)・[pokemon-check-v0.3b.md](docs/pokemon-check-v0.3b.md)・[cards-v0.3b.md](docs/cards-v0.3b.md)・[architecture-v0.3b.md](docs/architecture-v0.3b.md)
- v0.3a: 特殊状態の共通基盤と「どく」、番と番のあいだにエンジンが自動で行うポケモンチェック（どくのダメージ・それによるきぜつ・サイド・交代のあとで次の番）を、ビードルの「どくばり」とともに実装した。 文書: [special-conditions-v0.3a.md](docs/special-conditions-v0.3a.md)・[pokemon-check-v0.3a.md](docs/pokemon-check-v0.3a.md)・[weedle-v0.3a.md](docs/weedle-v0.3a.md)・[architecture-v0.3a.md](docs/architecture-v0.3a.md)
- v0.2f: ワザで自分に与えるダメージ（ダメージの発生源と受けるポケモンを分け、p.321 の順番で計算する）と、1 つのワザで両方のプレイヤーのポケモンがきぜつする同時のきぜつ（サイド・勝ち負け・交代の順番）を、ピカチュウの「かじる」「でんげき」とともに実装した。 文書: [self-damage-v0.2f.md](docs/self-damage-v0.2f.md)・[simultaneous-ko-v0.2f.md](docs/simultaneous-ko-v0.2f.md)・[pikachu-v0.2f.md](docs/pikachu-v0.2f.md)・[architecture-v0.2f.md](docs/architecture-v0.2f.md)
- v0.2e: ディフェンダーを実装し、自分の場のポケモンを選んでつけるトレーナー・防御側のダメージ変更（p.321 の 7 段階）・相手の番の終わりまで続く有効期限を加えた。 文書: [defender-v0.2e.md](docs/defender-v0.2e.md)・[architecture-v0.2e.md](docs/architecture-v0.2e.md)
- v0.2d: コイントス（p.319）と、コインの結果でダメージが変わるワザ（ドードーの「みだれづき」）を実装した。 文書: [coin-rules-v0.2d.md](docs/coin-rules-v0.2d.md)・[coin-attacks-v0.2d.md](docs/coin-attacks-v0.2d.md)・[architecture-v0.2d.md](docs/architecture-v0.2d.md)
- v0.2c: プラスパワーを実装し、ポケモンについて場に残るトレーナー・有効期限（番の終わり）・ダメージ計算の段階（p.321 の 5 段階）への効果の適用を加えた。 文書: [pluspower-v0.2c.md](docs/pluspower-v0.2c.md)・[architecture-v0.2c.md](docs/architecture-v0.2c.md)
- v0.2b: トレーナーカード 3 枚（マサキ・きずぐすり・ポケモンいれかえ）を、『オフィシャルブック2000』の「最新の説明」と照合して実装した。 文書: [trainers-v0.2b.md](docs/trainers-v0.2b.md)・[architecture-v0.2b.md](docs/architecture-v0.2b.md)
- v0.2a: v0.1 と同じルール・カード・対戦の結果のまま、カード効果を実装するための構造を整えた（効果の登録表、保留中の決定、場のポケモンの番号、乱数の状態の保存）。 文書: [architecture-v0.2a.md](docs/architecture-v0.2a.md)
- v0.1: 最小の対戦（対戦準備・番の進行・効果のないワザ・きぜつ・勝敗）。

### 版を変えない設計・調査・検証用 AI の作業（0.187.0 まで）

整理の前の README の順です。0.188.0 からあとの作業は、上の版の項と [実装状況](docs/implementation-status.md) の末尾の一覧にあります。

- 仕様案（v0.151 のあと。エンジンの版は 0.151.0 のまま。未承認・未実装）: 診断 API（拒否・停止・決定待ち・内部エラーの分類と、本人・相手・観戦者・検証者ごとの情報境界）と、完全な再現用記録・閲覧用記録・状態スナップショットの区別、再現のインターフェース、版と互換性の方針、実装の単位と順。 文書: [diagnostics-replay-api-design.md](docs/diagnostics-replay-api-design.md)・[diagnostics-replay-api-implementation-plan.md](docs/diagnostics-replay-api-implementation-plan.md)
- 仕様案（v0.159 のあと。エンジンの版は 0.159.0 のまま。原則だけ採用。未実装）: 実装の識別と互換性の判定の新しい方式（ゲームの挙動・記録と検証・API の形式の部品ごとの識別と、機能ごとの判定・移行の手順。現行の方式と判定は変えない。implementation-identity-design.md）と、合法手 API…。 文書: [implementation-identity-design.md](docs/implementation-identity-design.md)・[legal-actions-api-design.md](docs/legal-actions-api-design.md)・[legal-actions-api-implementation-plan.md](docs/legal-actions-api-implementation-plan.md)
- 検証用 AI の P6 への追従（v0.174 のあと。エンジンの版は 0.174.0 のまま）: 行動生成の `cost_evaluation` の確かめ・判定の規則 4・構築盤面 3 つの固定確認。 文書: [verification-ai-p6.md](docs/verification-ai-p6.md)
- R-3 の監査（v0.174 のあと。文書だけ。エンジンの版は 0.174.0 のまま）: 本人のうらのカードの 2 段以上の特殊能力の型ごとの分類と、最初の補完 U-R3a の計画（v0.175 で実装）。 文書: [legal-actions-r3-audit.md](docs/legal-actions-r3-audit.md)
- 検証用 AI の U-R3a への追従（v0.175 のあと。エンジンの版は 0.175.0 のまま）: 判定の規則 5・構築盤面 3 つの固定確認。 文書: [verification-ai-u-r3a.md](docs/verification-ai-u-r3a.md)
- 現在の完了・未完了一覧（2026-11-16。0.187.0 と GUI の追従の時点。状態の整理と文書だけ）: 完了 22・限定確認済み 11・未実装・未対応・未裁定 14・判断待ち 4・性能課題・対象外 6・main への統合 2（どれも main 未統合）: docs/project-status-ledger-v0187.md。 文書: [project-status-ledger-v0187.md](docs/project-status-ledger-v0187.md)
- 現在の完了・未完了一覧（2026-11-15。エンジン・検証用 AI・GUI。調査と文書だけ）: 完了・確認範囲に限界がある項目・残る未対応と判断事項・main への統合・次の候補を 1 つにまとめた。 文書: [project-status-ledger-v0185.md](docs/project-status-ledger-v0185.md)
- 仕様（v0.171 のあと。エンジンの版は 0.171.0 のまま。調査と仕様だけ。v0.172 で実装）: U7-5f・U7-5g の残件（CheckFaceUpDeckCard の表示・カツラの 2 枚目・自分のうらのカードのワザといっしょに選ぶもの・自分のうらのカードの特殊能力・段階と主体ごとの coverage と U7 の完了の条件）の監査と実装の仕様…。 文書: [legal-actions-u7-5fg-spec.md](docs/legal-actions-u7-5fg-spec.md)
- 計画（v0.172 のあと。エンジンの版は 0.172.0 のまま。計画だけで、総合検証は実行していない）: U7 の総合検証の計画（エンジン `e26df79`・GUI `b1037bc`・renderer `af88231` の組。目的・段階・資源の上限・証跡の保存先）。 文書: [u7-integration-verification-plan.md](docs/u7-integration-verification-plan.md)
- 設計（v0.172 のあと。エンジンの版は 0.172.0 のまま。設計と計画だけで、実装・対戦の実行はしていない）: U7 を通して対戦を進め、異常を分類して再現できる記録を残す検証用 AI の仕様と段階的な実装計画。 文書: [verification-ai-design.md](docs/verification-ai-design.md)・[verification-ai-implementation-plan.md](docs/history/verification-ai-implementation-plan.md)
- 検証用 AI の V0（エンジンの版は 0.172.0 のまま。エンジンは変えていない）: `client_api` の入口だけで固定条件の 1 対戦を進める道具 `tools/verification_ai`（行動生成・均等の方策・ランナー・記録）。 文書: [verification-ai-v0.md](docs/verification-ai-v0.md)
- 検証用 AI の V1（エンジンの版は 0.172.0 のまま。エンジンは変えていない）: ランダムの分布 `uniform-candidate+uniform-stage`（V0）と `uniform-candidate+uniform-tuple`（候補の中の完成した入力の組を上限 4,096 で列挙）の定義、選択の過程と到達範囲の計測…。 文書: [verification-ai-v1.md](docs/verification-ai-v1.md)
- 検証用 AI の V2（エンジンの版は 0.172.0 のまま。エンジンは変えていない）: 操作の種類だけで順位をつけるルールの方策 rules-v1 と、選択のエピソードごとに確率 ε でランダムを選ぶ混合の方策（同じ行動生成・check・submit・記録・計測）。 文書: [verification-ai-v2.md](docs/verification-ai-v2.md)
- 検証用 AI の V2 の補完（エンジンの版は 0.172.0 のまま。エンジンは変えていない）: 反復を抑えるルールの方策 rules-v2（同じ番に同じ意味の操作が 2 回受理されたら送る前に抑え、候補を end_turn より後ろへ下げる戦略上の選好。rules-v1 は変えていない）。 文書: [verification-ai-v2-repeat.md](docs/verification-ai-v2-repeat.md)
- 設計（エンジンの版は 0.172.0 のまま。設計と計画だけで、実装・対戦の実行はしていない）: 検証用 AI の V3（boundary・negative）の仕様と限定的な実装計画。 文書: [verification-ai-v3-design.md](docs/history/verification-ai-v3-design.md)
- 検証用 AI の V3-1（エンジンの版は 0.172.0 のまま。エンジンは変えていない）: 通常の進行の中の negative。 文書: [verification-ai-v3-1.md](docs/verification-ai-v3-1.md)
- 検証用 AI の V3-2（エンジンの版は 0.172.0 のまま。エンジンは変えていない）: カツラの固定の到達例（`BLAINE_DECK`・seed 1 を道具に写した）で、`options_by_path` の 1 枚・2 枚の正常な入力を check のあとに送り、観測と完全な記録で付与を確かめた。 文書: [verification-ai-v3-2.md](docs/verification-ai-v3-2.md)
- 検証用 AI の V3-3（エンジンの版は 0.172.0 のまま。エンジンは変えていない）: 構築盤面の代表例 4 つ（既存のテストの盤面を fixture にし、出典・sha256・整合を記録。開始のスナップショットから復元した対戦を公開の API だけで操作）で、`unverified` の受理…。 文書: [verification-ai-v3-3.md](docs/verification-ai-v3-3.md)
- 棚卸し（v0.173 のあと）: 検証用 AI の V0〜V3-3 と U7 の残件の一覧（区分・根拠・影響・次の最小の作業・優先度・裁定の要否・完了の確かめ）と、次に進める 3 件の提案。 文書: [verification-ai-inventory.md](docs/history/verification-ai-inventory.md)
- 仕様（v0.156。エンジンの版は 0.155.0 のまま。原則だけ採用。v0.157 で判断事項を採用して実装）: 状態スナップショット（U6。JSON の状態の保存・復元）。 文書: [state-snapshot-design.md](docs/state-snapshot-design.md)・[state-snapshot-implementation-plan.md](docs/state-snapshot-implementation-plan.md)

## kyuura との役割分担

| リポジトリ | 役割 |
|---|---|
| [kyuura](https://github.com/moheronemy/kyuura) | 歴史資料の**正本**。カードデータ、ルールの版と変遷、公式エラッタ、出典と確度の記録 |
| kyuura-engine（このリポジトリ） | 対戦処理の実装。kyuura の固定したコミットのデータとルールの記録を参照する |

- 参照している kyuura のコミット: `73a169063463bbf7bcaa3137d70cbf9721d11534`（カードの写しの元。v0.97 から。kyuura の main。形式 3 のカードデータ。v0.69〜v0.96 は `7d3f4ca76c084774efb4ac6a1d3a943387e183c3`、v0.68 までは `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`。[docs/unown-research-idfnj-v0.97.md](docs/unown-research-idfnj-v0.97.md) 2 章）
- 研究の基準にした kyuura のコミット: `73a169063463bbf7bcaa3137d70cbf9721d11534`（v0.97 から。写しの元と同じ。アンノーンの研究 78d090c を取り込んだ main。[docs/unown-research-idfnj-v0.97.md](docs/unown-research-idfnj-v0.97.md) 3 章）。v0.69〜v0.96 は `7d3f4ca76c084774efb4ac6a1d3a943387e183c3`（写しの元と同じ。v0.68 までの記録を kyuura が取り込んだコミット。[docs/equivalent-non-pack-cards-v0.69.md](docs/equivalent-non-pack-cards-v0.69.md) 7 章）。v0.68 までは `3f349085645f47d0649a6cacece3680caeae50bf`（ブランチ `claude/cool-ptolemy-5vtgsg`。裁定・論点・最新の説明・照合の記録。2026-10-15 に、エンジンの照合の記録を kyuura に取り込んだあとのコミットへ上げた。[docs/verified-record-reuse.md](docs/verified-record-reuse.md)）。v0.18 は `adf97107ee0d9755cd7ddedae298ecb02914128e`（ブランチ `claude/engine-findings-through-v0.17`。[docs/research-alignment-v0.18a.md](docs/research-alignment-v0.18a.md)）
- カードを実装するときは、kyuura の `data/cards.json` を信頼できる基本データとして使い、すでに記録された最新の説明・エラッタ・裁定にしたがいます。外部照合は pcg-search.com で行い（収録・カード番号で版を決める。対象の版がない・アクセスできなかったことも記録する）、ガイドブック（『オフィシャルブック2000』）の読み直しは通常の手順に入れません（2026-10-15 からの方針。[docs/card-data-policy.md](docs/card-data-policy.md)、`CLAUDE.md` の「カードデータの信頼と照合の方針」）。記録は `kyuura_engine/data/card_sources.json`（採用・外部照合）で、2026-10-14 までの原典照合の記録 `kyuura_engine/data/card_verification.json` は履歴として残しています
- 既存の照合の記録（このリポジトリと kyuura）は探して再利用し、同じ範囲を調べ直しません（`CLAUDE.md` の「照合済みの記録の再利用」）
- カードデータは、そのコミットの `data/cards.json` から必要なカードだけを抜き出した写し（`kyuura_engine/data/kyuura_cards.json`）を同梱しています。写しはカード情報の正本ではありません。由来と照合の記録は [docs/data-provenance.md](docs/data-provenance.md)。
- このリポジトリから kyuura を変更することはありません。資料の誤りや食い違いを見つけたら、kyuura 側で確かめて記録します。

## 実行環境

- Python 3.11 以降（3.11・3.12・3.13 でテスト済み）
- 標準ライブラリだけを使います。外部のパッケージは不要です。
- 自動テストはネットワークや kyuura の clone なしで動きます。

## セットアップ

```sh
git clone https://github.com/moheronemy/kyuura-engine.git
cd kyuura-engine
python3 -m pip install -e .   # 任意。開発用（編集可能）。リポジトリの直下で使うだけなら不要
```

別のリポジトリ（GUI など）から使うときは、編集可能ではなく通常のインストールで、完全なコミットハッシュに固定します（`python -m pip install "kyuura-engine @ git+https://github.com/moheronemy/kyuura-engine@<コミット>"`）。v0.164 までの配布物には `kyuura_engine.resolution` が入らず、通常のインストールでは読み込めませんでした（`e8c518f` で修正）。手順・wheel からの導入・確かめ方: [docs/installation.md](docs/installation.md)

## テストの実行

[実行範囲・総数の集約・時間の計測](docs/testing.md)に、開発中と完了時の手順をまとめています。

リポジトリの直下で:

```sh
python3 -m unittest
```

`pytest` があれば `pytest` でも実行できます。kyuura を隣に clone しておくと（`../kyuura`）、同梱のカードデータが固定したコミットと同じかを確かめるテストも動きます。

```sh
git clone https://github.com/moheronemy/kyuura.git ../kyuura
python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura --check
```

ふだんのテスト（`python3 -m unittest`）には、速い単体テスト（段階 A）と、決まった seed の対戦・ログと書き出しの監査・前の版の参照データとの比較・小さなストレス実行（段階 B）が入っています。大きな実行（段階 C）は明示的に走らせます（v0.4e。[docs/architecture-v0.4e.md](docs/architecture-v0.4e.md) 4 章）:

```sh
# 前の版（v0.11 の 8bd1e5b。v0.11 では v0.10 の 43ec8ba）と今の作業ツリーを、同じ入力で別々のプロセスで動かして比べる（約 5 分。ネットワーク不要）
python3 tools/compare_engine_versions.py --base 8bd1e5b --report report.json
# 大規模なストレス実行（でたらめな操作を混ぜ、結果を分類して数える。問題のある seed を報告する）
python3 tools/stress_engine.py --seeds 100 --steps 600 --report stress.json
# フシギバナの組だけ（エナジートランスの使用を混ぜる。v0.5）
python3 tools/stress_engine.py --scenario venusaur --scenario venusaur_status
# カメックスの組だけ（あまごいの使用を混ぜる。v0.6）
python3 tools/stress_engine.py --scenario blastoise --scenario blastoise_mixed
# フーディンの組だけ（ダメージスワップの使用を混ぜる。alakazam_mixed はフシギバナ・カメックス・フーディンを同じデッキに。v0.7）
python3 tools/stress_engine.py --scenario alakazam --scenario alakazam_mixed
# ベトベトンの組だけ（かがくへんかガスが特殊能力を消す場面。muk_mixed は両方のデッキにベトベトン。v0.8）
python3 tools/stress_engine.py --scenario muk --scenario muk_mixed
# ゴーストの組だけ（「とうめい」がはたらく場面。haunter_muk は両方のデッキにゴースト、一方にベトベトン。v0.9）
python3 tools/stress_engine.py --scenario haunter --scenario haunter_muk
# カイリキーの組だけ（「はんげき」がはたらく場面。machamp_mixed は両方のデッキにカイリキー、一方にベトベトン、もう一方にゴースト。v0.10）
python3 tools/stress_engine.py --scenario machamp --scenario machamp_mixed
# サカキのカイリキーの組だけ（「こんじょう」を使うかの決定・かがくへんかガス・G37 の場面。giovanni_mixed は両方のデッキにサカキのカイリキー、一方にベトベトン・ゴースト、もう一方にカイリキー・ロコン。v0.11）
python3 tools/stress_engine.py --scenario giovanni --scenario giovanni_mixed
# R団のファイヤーの組だけ（「ふしちょう」を使うかの決定・「ほのおのかべ」の効果と期限・W24 の場面。moltres_mixed は両方のデッキに R団のファイヤー、一方にベトベトン・ゴースト・ロコン、もう一方にカイリキー・バタフリー。v0.12）
python3 tools/stress_engine.py --scenario moltres --scenario moltres_mixed
# わるいカメールの組だけ（「こうらがえし」の効果・受けたダメージ・返すダメージ・S37 の場面。wartortle_mixed は両方のデッキにわるいカメール、一方に R団のファイヤー。v0.13）
python3 tools/stress_engine.py --scenario wartortle --scenario wartortle_mixed
# R団のカビゴンの組だけ（「わるいねぞう」・たおれこむ・Z23・C18 の場面。snorlax_mixed は一方にモンジャラ・サカキのニャース、もう一方にわるいカメール・R団のファイヤー。v0.17b）
python3 tools/stress_engine.py --scenario snorlax --scenario snorlax_mixed
# ナツメのヤドンの組だけ（ぐうたらこうげき・抵抗力で 0 になる Z23-b の場面。slowpoke_mixed は一方に R団のカビゴン・モンジャラ、もう一方にわるいカメール・R団のファイヤー。v0.18c）
python3 tools/stress_engine.py --scenario slowpoke --scenario slowpoke_mixed
# 変異試験（v0.18e から定義を版管理。tools/mutants.py）。check は定義の検査（速い）、witness は証人のテストだけ、full は全体（C 段階。1 つの変異で数分）
python3 tools/run_mutants.py check
python3 tools/run_mutants.py witness --jobs 3
python3 tools/run_mutants.py full --jobs 3 --out mutants.jsonl
# 研究の対応表（kyuura_engine/data/research_links.json）を、kyuura の研究の基準のコミットの記録と照らす（v0.18e。../kyuura が要る）
python3 scripts/check_research_links.py --kyuura ../kyuura
# カードデータの採用と外部照合の記録（kyuura_engine/data/card_sources.json）を確かめる（2026-10-15 からの方針。docs/card-data-policy.md）
python3 scripts/check_card_sources.py
# 解決の基盤の先読みの方法（derived・legacy・derived_full）どうしを、公開の apply_command を基準に同じ対戦の 1 歩ごとに比べる（交互の状態。v0.16b から
# v0.13 の経路はないので、v0.13 との比較は下の engine_lockstep.py と参照データ tests/legacy_reference.py で行う）
python3 tools/event_kernel_compare.py --stress-seeds 10 --natural-seeds 20 --mode all --mixed --timing
# 固定した前の版の木（v0.13 の 8facf3a・v0.15 の aa551ab）を展開し、この木と別々のプロセスで同じ対戦を進めて比べる（v0.15・v0.16。1 回の記録に約 10〜20 分）
python3 tools/engine_lockstep.py tree --commit 8facf3a --out /path/to/v013
python3 -I tools/engine_lockstep.py record --root /path/to/v013 --seeds 100 --stress-seeds 10 --save-every 7 --out a.jsonl.gz
python3 -I tools/engine_lockstep.py record --root . --seeds 100 --stress-seeds 10 --save-every 7 --out c.jsonl.gz
python3 tools/engine_lockstep.py compare a.jsonl.gz c.jsonl.gz   # 許す差は WRONG_PHASE の段階の名前の並びだけ（v0.16d）
```

## 使い方

ゲームの状態は `GameState`、プレイヤーの操作はコマンド（`commands.py` の dataclass）です。`apply_command` はコマンドを検査してから新しい状態を返し、渡した状態は変えません。不正な操作は `IllegalActionError`、未対応のものは `UnsupportedError` になります。返す状態は毎回、カードの保存則などの不変条件で確かめ、破れていれば `StateIntegrityError` を投げます（エンジンの不具合か、呼び出し側が状態を書き換えたことを示す）。

```python
from kyuura_engine import (
    AttachEnergy, PlaceStartingPokemon, ReportJankenResult, UseAttack,
    apply_command, expand_decklist, new_game, state_to_dict,
)

# 60 枚のデッキ（カード id は kyuura の data/cards.json の id）
deck0 = expand_decklist({"PMCG1-018": 4, "PMCG1-016": 4, "PMCG1-060": 4, "PMCG1-065": 4, "PMCG1-037": 4, "PMCG1-098": 40})
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})

state = new_game(deck0, deck1, seed=1)          # 山札を切り、7 枚配り、切り直しまで
for player in (0, 1):                            # バトル場に 1 匹、ベンチに 5 匹まで
    basics = [uid for uid in state.players[player].hand if state.card_def(uid).is_basic_pokemon]
    state = apply_command(state, PlaceStartingPokemon(player, basics[0], tuple(basics[1:6])))
state = apply_command(state, ReportJankenResult(winner=0))  # ジャンケンの勝者が先攻。番の最初の 1 枚も引く

me = state.players[0]
energy = next(uid for uid in me.hand if state.card_def(uid).is_basic_energy)
state = apply_command(state, AttachEnergy(0, energy, me.active.card))
state = apply_command(state, UseAttack(0, 0))    # ワザを使うと番が終わり、相手の番になる
print(state_to_dict(state)["phase"], state.turn_number)
```

- カード 1 枚ごとに対戦内の番号（uid）があり、コマンドは uid でカード・ポケモンを指定します。場のポケモンには、カードの uid とは別に、場に出たときに番号（`pokemon_id`）が付きます。にげる・交代では変わらず、場を離れると無効になります。
- 処理の途中でプレイヤーの選択が要るとき（きぜつさせたときのサイド、バトル場に出すポケモン、きずぐすり・ポケモンいれかえの対象）、`state.decision` に保留中の決定が入ります。決定する人は `decision.player`、選べるものは `decision.options` です。`ResolveDecision(player, decision.id, choices)` で答えます（サイドは `TakePrize`、バトル場に出すポケモンは `PromoteActive` でも答えられる）。決定を待っている間は、ほかの操作は受け付けません。
- ワザ・トレーナーを使えるのは、効果の登録表（`DEFAULT_EFFECTS`）に、カード id（ワザはカード id とワザの位置）で実装が登録されているときだけです。説明文が空なことは、使える根拠にしません。
- 原典で扱いを決められない場面（たとえば、ダメージのあるポケモンがいないときのきずぐすり）は、推測で処理せず `UnsupportedError`（コードは `UNRESOLVED_…`）になり、状態は変わりません。決定の選べるもののうち、そういうものは `decision.context_value("unresolved_choices")` に入っています。
- 乱数は `seed`（0 以上の整数）だけから作ります。同じデッキ・同じ seed・同じ操作の列なら、同じ結果になります（Python 3.11・3.12・3.13 で同じ値になることを固定値のテストで確かめています）。乱数を使うのは、山札を切るときと、コインを投げるとき（v0.2d）だけです。コインの結果をコマンドで指定する方法はありません。
- 状態は `copy.deepcopy`・`pickle` できます。状態どうしを比べるときは `==` ではなく `state_to_dict` の結果を比べてください。
- 対戦が終わったかどうかは `state.phase` で判断します（`game_over`・`sudden_death`・`halted`）。`halted` のときは `state.result` が `None` です。
- ジャンケンの結果は外から渡します（エンジンは決めません）。
- `state_to_dict` は状態を JSON にできる辞書にし、`command_to_dict` / `command_from_dict` はコマンドを辞書と相互に変換します（ほかの言語や画面から使うための境界）。`state_to_dict` の既定の形式は v0.1 と同じで、`format_version=2` で場のポケモンの番号・保留中の決定などが、`format_version=3` で使用中のトレーナーカードが、`format_version=4` でポケモンについているトレーナーカード（プラスパワーなど）が、`format_version=5` で特殊状態（v0.3a〜v0.3c）が、`format_version=6` でこんらんで「にげる」に失敗した記録（v0.3c）が、`format_version=7` で進化の重なり・場に出た番・進化した番（v0.4a）が、`format_version=8` でワザによる持続する効果（v0.4b）が加わります（いまの対戦は形式 8 を使う。古い形式は、表せないもの（カード・特殊状態・失敗の記録・進化・持続する効果）がある状態を書き出さずに `ValueError` にする）。どれも隠れた情報（山札の順番・相手の手札・サイドの中身）を含む内部の状態で、プレイヤーに見せる形ではありません。ログ（`state.log`）も内部の完全な記録で、引いたカードなどを含みます。形式 9〜13 はその後の版で加えた項目です（形式 12 は v0.47 の期限のあるトレーナーの使用の禁止、形式 13 は v0.48 の［へんしょく］の記録）。プレイヤー（または観戦者）に渡すときは、v0.47 の `observe(state, viewer)`（その人に見える盤面）と `visible_log(state, viewer)`（その人に見える項目だけのログ）を使ってください（[docs/fossil-hidden-info-v0.47.md](docs/fossil-hidden-info-v0.47.md) 5.1 節。画面・通信はありません）。
- 乱数の状態の保存・復元は `kyuura_engine.rng`（`rng_state_to_json`・`rng_from_json`）にあります。ゲーム状態全体の保存・復元は、v0.157 の状態スナップショット（`kyuura_engine.snapshot` の `save_snapshot`・`restore_snapshot`。[state-snapshot-v0.157.md](docs/state-snapshot-v0.157.md)）にあります（この段落のもとの文「ゲーム状態全体を JSON から読み込む処理はまだありません」は v0.156 までの記述）。
- 互換性（v0.140 で明記。[prize-order-user-rule-v0.140.md](docs/prize-order-user-rule-v0.140.md) 4 章）: `state_to_dict` の形式の番号は書き出しの形の版で、決定の種類などの値の語彙の版ではありません。読む側は、知らない形式に加えて知らない種類の値・項目を拒否してください。状態の写し（`pickle`）は前の版の写しを後の版で読む向きだけを考えていて、安全な外部のデータ交換の形式ではありません。この版が知らない決定の再開先・続けない前の版の決定を待つ状態は、`observe`・`apply_command` の前に `UnsupportedError`（`UNSUPPORTED_DECISION`）で拒否します。

### 固定のデッキで対戦を始める（v0.20・v0.26）

```python
from kyuura_engine import new_game, preset_deck, preset_deck_ids

print(preset_deck_ids())   # ('hitmonchan-dewgong', 'venusaur-parasect', 'hitmonchan-dewgong-v2', 'venusaur-parasect-v2')
state = new_game(preset_deck("hitmonchan-dewgong").cards(), preset_deck("venusaur-parasect").cards(), seed=1)        # 第1版
state = new_game(preset_deck("hitmonchan-dewgong-v2").cards(), preset_deck("venusaur-parasect-v2").cards(), seed=1)  # 第2版
```

```bash
python3 examples/start_preset_game.py --list
python3 examples/start_preset_game.py --deck0 hitmonchan-dewgong --deck1 venusaur-parasect --seed 1 --first 0
python3 examples/start_preset_game.py --deck0 hitmonchan-dewgong-v2 --deck1 venusaur-parasect-v2 --seed 1 --first 0
```

- `preset_deck(識別子).cards()` は `new_game` に渡せる 60 枚のカード id のリストを返します（呼ぶたびに新しいリスト）。知らない識別子は `KeyError`（例・道具では引数の誤り）です。
- 第1版（v0.20）の中身・考え方・既知の制限は [docs/preset-decks-v0.20.md](docs/preset-decks-v0.20.md)、第2版（v0.26）の中身・変更の理由・進め方・比較の結果・自動操作の限界は [docs/preset-decks-v0.26.md](docs/preset-decks-v0.26.md)。どれも試作の構成で、大会のデッキ・最適化したデッキではなく、人間どうしで勝率の釣り合いを確かめていません。

| 識別子 | ポケモン | トレーナー | エネルギー |
|---|---|---|---|
| `hitmonchan-dewgong`（第1版） | エビワラー 4・パウワウ 4・ジュゴン 3・コラッタ 3 | オーキドはかせ 4・マサキ 4・きずぐすり 4・ポケモンいれかえ 4・プラスパワー 4・ディフェンダー 4 | 闘 12・水 10 |
| `venusaur-parasect`（第1版） | フシギダネ 4・フシギソウ 4・フシギバナ 3・パラス 4・パラセクト 3 | オーキドはかせ 3・マサキ 4・きずぐすり 4・ポケモンいれかえ 4・プラスパワー 3・ディフェンダー 4 | 草 20 |
| `hitmonchan-dewgong-v2`（第2版） | エビワラー 4・パウワウ 4・ジュゴン 3・コラッタ 3 | オーキドはかせ 3・マサキ 4・ポケモンいれかえ 3・きずぐすり 2・プラスパワー 4・突風 3・パソコン通信 3・エネルギー回収 2 | 闘 12・水 10 |
| `venusaur-parasect-v2`（第2版） | フシギダネ 4・フシギソウ 2・フシギバナ 3・パラス 4・パラセクト 2・モンジャラ 2 | オーキドはかせ 3・マサキ 3・ポケモンいれかえ 3・きずぐすり 2・プラスパワー 2・突風 2・パソコン通信 3・エネルギー回収 2・ポケモン交換おじさん 2・ポケモン育て屋さん 2 | 草 19 |

- 第2版の変更の理由: 必要なたね・進化先・エネルギーを探す（パソコン通信・ポケモン交換おじさん）、デッキ B のたね不足と進化カードの余りを減らす（たね 8 → 10・フシギソウ 4 → 2・パラセクト 3 → 2）、オーキドはかせなどでトラッシュしたエネルギーを戻す（エネルギー回収）、フシギバナに通常の進化（フシギソウ経由）とポケモン育て屋さんの両方で進化できるようにする。デッキ A2 は初期案（ポケモン交換おじさん 2・闘 11・水 9）から、比べた対戦でエネルギーが足りずにワザを使えない番が第1版より増えたので、1 回だけ調整した。
- 進め方・検索先の候補・育て屋さんと通常の進化の使い分けは [docs/preset-decks-v0.26.md](docs/preset-decks-v0.26.md) 2・3 章。比較（同じ手順・同じ seed・席の入れかえ、80 局と補足の 320 局）では、デッキ B2 の引き直し・ベンチが空のまま負けた局・使わずに終わった進化カードが第1版より少なく、デッキ B2 のエネルギー不足で攻撃できなかった番は少し多かった。勝率はデッキの強さを示さない（決まった手順どうし。コラッタを交代役に使えていない・突風の選び方の偏りなど。同じ文書 9 章）。
- examples/start_preset_game.py は、対戦準備を決まったやり方で済ませて先攻の最初の番の場を表示する、**対戦の開始だけの例**です。人間が最後まで遊べる操作画面（GUI・Web・通信対戦・対戦相手の AI）はありません。最初の番から先は `apply_command` にコマンドを渡して進めます。
- 決まった手順どうしで対戦させ、終わり方（通常の勝敗・未解決の裁定による停止・手数の上限・想定外の拒否・内部エラー）と各デッキの動きを数える: `python3 tools/preset_deck_games.py --games 20 --out <結果の JSON>`。v0.26 から `--deck-a`・`--deck-b` でデッキ A・B を選べます（既定は第1版。第2版は変種なし（`--variant preset`）で使う）。
- v0.26: 第1版と第2版の 4 組を同じ seed・席の入れかえ・同じ手順で比べ、終わり方・監査・各デッキの指標（攻撃できなかった番の理由はエンジンにワザを渡して確かめる）を数える: `python3 tools/preset_deck_comparison.py --seeds 10 --out <結果の JSON>`（80 局。約 7 秒）。
- v0.21: `--variant gust` を付けると、固定のデッキのディフェンダー 3 枚を突風 3 枚に置き換えた一時的なデッキどうしで対戦させ、突風を使った回数・選んだ相手・その番のワザを数えます（固定のデッキは変わりません）。v0.22: `--variant computer` はパソコン通信 3 枚に置き換え、使った回数・トラッシュした 2 枚・山札から選んだカードとその使い道を数えます。
- v0.23: `--variant mixed` はディフェンダー 4 枚を除いて突風 2 枚・パソコン通信 2 枚を加えた一時的なデッキ、`--variant retrieval` はさらにきずぐすり 2 枚をエネルギー回収 2 枚に置き換えた一時的なデッキです（`python3 tools/preset_deck_games.py --games 20 --variant mixed`）。パソコン通信で山札から突風を選んでその番に使った回数、エネルギー回収で手に入れたエネルギーの使い道、決定ごとの持ち主・使用中のカードの確かめ（`check_…`）、トレーナーを使ってからトラッシュするまでのログの確かめ（`trainer_sequence_problems`）を数えます。
- v0.24: `--variant trader` は `retrieval` の残りのきずぐすり 2 枚をポケモン交換おじさん 2 枚に置き換えた一時的なデッキです（`python3 tools/preset_deck_games.py --games 20 --variant trader`）。ポケモン交換おじさんでもどした・手に入れたカードの段階、手に入れたカードのその後（進化・ベンチ）を数え、`retrieval` と同じ確かめ（`check_…`・`trainer_sequence_problems`）をします。
- v0.27: `--variant scyther` はデッキ A2（`hitmonchan-dewgong-v2`）のコラッタ 2 枚をストライク 2 枚に、`--variant scyther_grass` はデッキ B2（`venusaur-parasect-v2`）のモンジャラ 2 枚をストライク 2 枚に置き換えた一時的なデッキです（第2版だけに使う。もう一方のデッキはそのまま）。元の A2 対 B2・A2S 対 B2・A2 対 B2S を同じ seed・席の入れかえ・同じ手順で比べ、ストライクの動き（「つるぎのまい」・強化した「きりさく」・効果が消えた理由・にげた回数）を数える: `python3 tools/scyther_games.py --seeds 10 --out <結果の JSON>`（60 局。約 7 秒）。
- v0.28: 既存の効果の型で加えたポケモン 10 枚の検証用デッキ（`W28`・`G28`）どうしと、第2版の固定のデッキとの組を、同じ手順（v0.28 のカードがまだ使っていないワザを選ぶ手順だけを重ねたもの）で対戦させ、終わり方・監査・カードごとのワザと結果を数える: `python3 tools/existing_effect_games.py --seeds 10 --out <結果の JSON>`（3 組 × 2 席 × 10 seed = 60 局。約 7 秒）。
- v0.29: 既存の効果の型で加えたポケモン 14 枚の検証用デッキ（`GW29`・`LF29`）どうしと、第2版の固定のデッキとの組（`GW29` 対 `B2`・`LF29` 対 `A2`）を、v0.28 と同じ手順で対戦させる: `python3 tools/existing_effect_games.py --batch v0.29 --seeds 10 --out <結果の JSON>`（3 組 × 2 席 × 10 seed = 60 局。約 6 秒）。
- v0.25: `--variant breeder` は、デッキ A（エビワラー・ジュゴン）は `trader` のまま、デッキ B（フシギバナ・パラセクト）だけ `trader` のマサキ 2 枚をポケモン育て屋さん 2 枚に置き換えた一時的なデッキです（`python3 tools/preset_deck_games.py --games 20 --variant breeder`）。ポケモン育て屋さんで進化させた回数・進化したあとの特殊能力（エナジートランス）・ワザを数え、`trader` と同じ確かめ（`check_…`・`trainer_sequence_problems`）をします。

### 機能ごとの使い方の例・操作の表（履歴）

v0.2b〜v0.27 の機能ごとの使い方の例と、操作（コマンド）の表は、本文のまま [README の履歴](docs/history/readme-archive-v0.199.md) の 2 章に移しました。書いた時点の版の例で、出力・選べる操作は今の版と違うことがあります。
今の操作の一覧は `kyuura_engine/commands.py`、外から使う入口は [クライアント向けのアダプタ](docs/client-api-v0.164.md) と [合法手 API](docs/legal-actions-u7-1.md) を参照してください。

## ディレクトリ

```
kyuura_engine/
  rules.py       ルールの組（2000.02.14版の数値）と根拠の一覧
  conditions.py  特殊状態（どく・ねむり・マヒ・こんらん）を付ける・置きかえる・回復する・ベンチに戻ったら・進化したら消す。v0.3a〜v0.4a
  persistent.py  ワザによる持続する効果（「かたまる」の「ダメージを受けない」、v0.12 の「ほのおのかべ」、v0.13 の「こうらがえし」）を付ける・期限・ベンチ・進化・きぜつで消す・はたらいているか。v0.4b・v0.12・v0.13
  continuous.py  常にはたらく特殊能力（かがくへんかガス）がはたらいているか・消している特殊能力を、今の状態から求める。v0.8（v0.9 の「とうめい」・v0.10 の「はんげき」・v0.11 の「こんじょう」の評価も使う）
  cards.py       カードの定義、kyuura のデータの読み込み、対応・未対応の分類
  effects.py     効果の登録表（ワザ: カード id・ワザの位置 → 実装、トレーナー: カード id → 実装）と、トレーナー 5 枚・みだれづき・でんげき・どくばり・いとをはく・キノコのほうし・あやしいひかり・れいとうビーム・かたまるの実装（v0.4c のスピアーのワザは既存の実装の登録）、ふきとばし（ワザの途中の相手の決定）・メガドレイン（v0.4d）の実装、ワザのダメージを与える処理（相手・自分。v0.2f。「ダメージを受けない」状態なら無効。v0.4b。結果 `DamageResult` を返す。v0.4d）。決定を出すトレーナーの決定の形の宣言（`decision_problems`。v0.4e）。ポケモンパワーの登録（カード id・パワーの位置 → 実装）とエナジートランス、やどりぎのタネ・どくのこな（コインなし）の実装（v0.5）。あまごい（手札から「水」エネルギーをつける）・ハイドロポンプ（多い「水」エネルギーでダメージを追加）の実装（v0.6）。ダメージスワップ・じこさいせい（v0.7）、かがくへんかガス・どくガス・ねばりつく（v0.8）、とうめい（ワザを受けるときに自動的にはたらく。ワザの要素の処理の境界の評価 `attack_reaches`）・あくむ・エナジーへんかん（v0.9）、はんげき（ダメージを受けたときに自動的にはたらく。判定は `deal_attack_damage`、与えるのは `finish_damage_elements`）・からてチョップ・じごくぐるま（v0.10）、ハリケーンパンチほか（v0.11）、ほのおのかべ（次の相手の番にはたらく持続する効果。与えるのは `finish_damage_elements`。v0.12）・ふしちょう（きぜつしたときに使う。v0.12）、こうらがえし（返す量は受けたダメージ。v0.13）。v0.2a〜v0.13
  coins.py       コイントス（対戦の乱数で決め、1 枚ごとにログに残す）。v0.2d
  deck.py        デッキの検査
  state.py       ゲームの状態（ゾーン、場のポケモン、進化の重なり（v0.4a。v0.4c から 2 進化の 3 枚まで）・場に出た番・進化した番（v0.4a）、ワザによる持続する効果（v0.4b。v0.12 で「ほのおのかべ」の `Retaliation`。v0.13 で与えるダメージの決め方 `basis`）、特殊状態（v0.3a〜v0.3c）、にげるの失敗の記録（v0.3c）、番、ポケモンパワーで手札からつけた枚数（v0.6）、結果）
  commands.py    プレイヤーの操作
  decisions.py   保留中の決定（出す・確かめる）。v0.2a
  engine.py      対戦の進行（new_game・apply_command）、きぜつ・サイド・勝ち負け・交代（同時のきぜつは v0.2f）、ポケモンチェック（v0.3a・v0.3b）、こんらんのワザ・にげるのコイン（v0.3c）、進化（v0.4a。2 進化は v0.4c）、不変条件（v0.4e でトレーナーの決定・サイドと交代の決定・番の番号を強めた。v0.6 でパワーでつけた枚数とログの対応）、あまごいのあとの通常の操作の停止（v0.6）、こんじょうの決定（v0.11）、きぜつしたあとの「ふしちょう」の決定（サイド・勝ち負けの判定のあと、バトル場に出す前。v0.12）
  damage.py      ワザのダメージ計算（p.321 の 8 段階。2・5〜8 段階の変更効果は v0.2c）、こんらんの 20 の計算（v0.3c）
  judge.py       勝ち負けの判定（p.311 の表）
  serialize.py   状態を辞書にする（形式 1〜13。9 は v0.6、10 は v0.31、11 は v0.44、12 は v0.47、13 は v0.48）
  observation.py プレイヤー（観戦者）に渡す観測（見てよい情報だけの盤面とログ）。v0.47。v0.48 から場のポケモンの今有効な最大HP・色・弱点・抵抗力も
  zones.py       山札から引く・トレーナーをポケモンにつける・手札のエネルギーカードを場のポケモンにつける・トラッシュのカードを手札に加える処理（エンジン・トレーナー・ポケモンパワー・ワザで共通）。v0.2b・v0.2c・v0.6・v0.12
  rng.py         乱数の状態の指紋・保存・復元。v0.2a（コインも同じ乱数）
  data/kyuura_cards.json       kyuura のカードデータの写し（生成物）
  data/card_verification.json  『オフィシャルブック2000』との照合の記録
  data/research_links.json     研究（kyuura）の id との対応表（研究の基準のコミット・停止コードと論点・最新の説明・照合の記録。v0.18）
scripts/extract_kyuura_cards.py  kyuura から写しを作る
scripts/check_research_links.py  研究の対応表を kyuura の研究の基準のコミットの記録と照らす（v0.18e）
scripts/make_compat_fixture.py   v0.1 の対戦結果の参照データを作った道具（作り直さない）
tools/mutants.py                 変異試験の定義（v0.18e から版管理。証人のテストつき）
tools/run_mutants.py             変異試験の実行（check・witness・full。写しの木で走らせ、作業ツリーは変えない。v0.18e）
tools/compat_driver.py           版の比較の駆動（公開の API だけで 1 つの版を動かし、1 手ごとの記録を作る）。v0.4e
tools/compare_engine_versions.py 2 つの版の比較（git archive で取り出し、版ごとに別のプロセス。最初の食い違いを診断）。v0.4e
tools/stress_engine.py           大規模なストレス実行（ふだんのテストでは走らせない）。v0.4e。v0.5 でフシギバナの組（エナジートランスの使用を混ぜる）、v0.6 でカメックスの組（あまごいの使用を混ぜる）、v0.7 でフーディンの組、v0.8 でベトベトンの組、v0.9 でゴーストの組、v0.10 でカイリキーの組、v0.11 でサカキのカイリキーの組、v0.12 で R団のファイヤーの組、v0.13 でわるいカメールの組、v0.17 で R団のカビゴンの組、v0.18 でナツメのヤドンの組
tests/                           自動テスト（unittest）。tests/log_audit.py はログと書き出しの監査の道具（v0.4e。v0.6 で手札・あまごいの組み立て直しと形式 9。v0.8 でかがくへんかガス、v0.9 で「とうめい」の判定とエナジーへんかん、v0.10 で「はんげき」、v0.11 で「こんじょう」の決定・コイン・残り HP、v0.12 で「ふしちょう」の答え・トラッシュから手札・「ほのおのかべ」の効果と返すダメージ、v0.13 で「こうらがえし」の受けたダメージ・効果の種類。テストではない）
tests/fixtures/                  v0.1 の対戦結果の参照データ、v0.4d（4bd97bf）の記録の指紋（v0.4e。互換性のテスト用）
docs/                            ルールの仕様、実装状況、データの由来、v0.1 のレビュー、API のレビュー、v0.2a〜v0.6 のアーキテクチャ、トレーナー・コイントス・みだれづき・ディフェンダー・自分へのダメージ・同時のきぜつ・ピカチュウ・特殊状態・ポケモンチェック・ビードル・ねむり・マヒ・キャタピー・パラス・こんらん・ロコンの原典照合、特殊状態の総合検証・未解決の裁定・コインの前の検証（v0.3d）、進化の準備（v0.4）、進化のルール・カード・状態の持ち方（v0.4a）、持続する効果・かたまる・持続する効果とダメージ計算（v0.4b）、2 進化のルール・スピアー・3 枚の重なりの状態（v0.4c）、相手の強制交代・与えたダメージと回復・バタフリー（v0.4d）、総合監査・組み合わせの表・互換性・未解決の範囲・v0.5 の準備（v0.4e）、ポケモンパワーの規定・フシギバナ・フシギダネとフシギソウ・エナジートランスの処理・確かめた結果（v0.5）、あまごいの原典の照合と裁定・確かめた結果（v0.6）、ダメージスワップ・ケーシィの系統（v0.7）、かがくへんかガス・ベトベターの系統・常にはたらく効果の求め方（v0.8）、とうめいの原典の照合と裁定・ゴースの系統・自動的にはたらく特殊能力の仕組み・設計・確かめた結果（v0.9）、はんげきの原典の照合と裁定・ワンリキーの系統・ダメージを受けたあとに自動的にはたらく特殊能力の仕組み・設計・確かめた結果（v0.10）、こんじょうの原典の照合と裁定・サカキのワンリキーの系統・きぜつの判定ときぜつの処理のあいだの仕組み・設計・確かめた結果（v0.11）、ふしちょうの原典の照合と裁定・R団のファイヤーとほのおのかべ・きぜつしたあとに使う特殊能力の仕組み・番をまたいではたらくワザの効果・設計・確かめた結果（v0.12）、こうらがえしの原典の照合と裁定・わるいカメールと第4弾のゼニガメ・量が受けたダメージで決まる効果の仕組み・設計・確かめた結果（v0.13）、カードの選定・既存の要素だけのカード・R団のカビゴン・キョウのベトベトンの設計の検証・拡張性の検証（v0.17）、研究との照合・未解決の裁定の再調査・ナツメのヤドン・窓の途中の決定の設計・検証の再現性・最終の検証（v0.18）
docs/history/                    履歴に移した検証用 AI の試験記録と、整理の前の README の本文（README の「履歴」）
```
