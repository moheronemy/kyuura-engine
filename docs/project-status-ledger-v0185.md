# 現在の完了・未完了一覧（エンジン・検証用 AI・GUI。0.185.0 の時点）

整理日: 2026-11-15。調査・文書化だけです。実装・テスト・ビルド・対戦・judge・replay・seed の探索はしていません。`kyuura_engine`・`tools.verification_ai` は import していません。

| 対象 | 参照したコミット | 内容 |
|---|---|---|
| エンジン | `b1e4430`（main。PR #40 のマージ。`ad4514a` と内容は同じ） | 0.185.0。配布の確かめの固定は `fa98012f7534fe89667730ffa3e997342bde22a6` |
| 検証用 AI | 同じ `b1e4430` の `tools/verification_ai` | `TOOL_VERSION` 10・判定の規則 8・計画と完了の形式 6 |
| GUI | `593be09`（GUI の main。PR #4 のマージ。`95645ff` と内容は同じ） | エンジンの固定は 0.185.0（`fa98012`）のまま。最後の製品の変更は `5dd80cb`。GUI は公開コミットの読み取りだけで、再確認・再実行はしていない |

- 想定した基点の `claude/fossil-slot-reveal-v0185`（`ad4514a`）と GUI の `feature/engine-0185-audit-null-contract`（`95645ff`）は、どちらも main に取り込まれ、リモートのブランチは消えています（5 章）。
- 証跡: `kyuura-engine-verification-vai/verifier/runs/status-ledger-v0185/`（事前計画・参照コミット・項目と根拠の対応・訂正一覧・候補の選定）。

**読み方**

- 各項目は 1 か所にだけ置きます。同じ項目の別名・過去の観察は、その行の「根拠」にまとめました。
- 1 章の項目は閉じます。確認範囲が限られる項目は 2 章に置き、限界を書いたうえで閉じます。2 章の「未確認」は、それだけで未完了に戻しません（全体テスト・全カードの実行・new_game からの到達を、完了の条件に足しません）。
- 確認の種類: 静的（コード・記録の読み取り）、人工（偽物の応答・写して変えた応答）、構築（構築盤面の実応答）、固定（固定例の再生）、new_game（new_game からの対戦。バッチ名と版）。
- 「GUI 文書」は GUI の `docs/engine-contract.md` の章です。GUI は今回、公開文書で確かめただけです。
- 「main 未取り込み」を未実装とは扱いません。今回の時点では、下の項目はすべて main に入っています（5 章）。

## 1. 完了として閉じる項目

| ID | 内容 | 実装 | 確認（最後の版） | 接続 | 根拠 |
|---|---|---|---|---|---|
| C-TRADER | ポケモン交換おじさんの、もどすカードと探したカードの識別（出来事の `card_id`） | 0.182.0 | 構築（0.182.0・0.183.0） | エンジン・client_api の `log`（0.183.0）・GUI（GUI 文書 25 章） | [trader-reveal-identification-v0.182.md](trader-reveal-identification-v0.182.md)・[client-api-visible-log-v0.183.md](client-api-visible-log-v0.183.md) |
| C-LOG | client_api の読み取りの要求 `log`（閲覧者ごとの受理の時点の写し・最大 256 件・`baseline_end`） | 0.183.0 | 構築・配布（`0529041`） | エンジン・client_api・GUI（25 章） | 同上 |
| C-W1AUDIT | w1 の公開の監査（61 回答） | 文書（`9eddbcf`） | 静的（保存済みの記録。0.181.0 の記録） | — | [verification-ai-w1-publication-audit.md](verification-ai-w1-publication-audit.md)・[…-remaining.md](verification-ai-w1-publication-audit-remaining.md) |
| C-ER9 | ER9（`UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE`）の条件つきの根拠 | 規則 6 | new_game（w1・0.181.0）で known_stop と、同じ決定への答え直しの受理 | 検証用 AI | [coverage-inventory 10.5 節](verification-ai-coverage-inventory-next-batch.md)・[batch-plan3 11 章](verification-ai-batch-plan3.md) |
| C-P1 | LOST_TARGET の P1（本人のうらを特殊能力で指定） | 規則 7（`TOOL_VERSION` 9） | 保存済みの s1・r1 への当て直し、new_game（u1・0.181.0）で known_stop | 検証用 AI | [lost-target-own-face-down-design.md](verification-ai-lost-target-own-face-down-design.md) 13・14 章・[pyc-cache-procedure.md](verification-ai-pyc-cache-procedure.md) 9.3 節 |
| C-P3S | LOST_TARGET の P3s（決定への回答で本人のうらを指定） | 規則 8（`TOOL_VERSION` 10） | new_game（t2 の回帰の条件・0.181.0）で known_stop と答え直しの受理（1 件） | 検証用 AI。API・GUI の契約は変わらない | [batch-plan-p3s-v0181.md](verification-ai-batch-plan-p3s-v0181.md) 10.5 節・[P3 設計](verification-ai-lost-target-p3-decision-design.md) 10 章 |
| C-KEEP | 指定でおもてにした［KEEP］とエネルギー・リムーブ（E12）の内部エラー | 0.181.0（KP1 の通常の拒否） | 構築（0.181.0）。GUI で拒否の表示と、取り直した候補での答え直しの受理（GUI 文書 23.5 節） | エンジン・GUI（23 章）・検証用 AI（E12 の期待値） | [keep-designated-energy-removal-v0.181.md](keep-designated-energy-removal-v0.181.md) |
| C-CN1 | 収集器の `failure`（CN-1） | 0.173.0 | テスト・配布のスモーク | エンジン・検証用 AI | [cn1-failure-v0.173.md](cn1-failure-v0.173.md) |
| C-RUNNER | 明示的なデッキリスト・方式 boundary・主体別の観測の記録・逐次バッチ・再開・完全保存・ハッシュ照合 | 実装済み | new_game（d1・r1・r2・s1・s2・t1・t2・u1・w1〜w3） | 検証用 AI | [decklist](verification-ai-decklist.md)・[observation](verification-ai-observation.md)・[batch](verification-ai-batch.md) |
| C-S1 | 外部の checked-hash の pyc キャッシュ（S-1） | 外側の手順 | 実バッチ（u1・w1〜w3・0.181.0）。標準の手順にできると判断（9.7 節） | 検証用 AI の実行手順 | [pyc-cache-procedure.md](verification-ai-pyc-cache-procedure.md) 9 章。キャッシュを確かめるためだけの追加のバッチは要件にしていない（未確認の長い局・別の環境は、次に実行したときに記録する） |
| C-RETREAT | 同じ番に何度もにげる | 仕様どおり（2000.02.14 版 p.311） | 静的（エンジンのテスト `test_retreat_many_times_in_one_turn`） | — | GUI 文書 21.4 節。不具合候補から外した |
| C-HOLDER | エネルギーの選べるものに付属先を示す | GUI（`2674efd`） | 単体・画面全体のテスト（人工の応答をふくむ。ブラウザでは見ていない。GUI 文書 24.5・24.6 節） | GUI だけ（API の変更なし） | GUI 文書 24 章 |
| C-GUITEXT | GUI が独自に書く、公開・受理を確約する説明文 | GUI（限定の修正） | 静的な検索と単体 | GUI だけ | GUI 文書 21・22 章 |
| C-F1 | うらのバトル場のワザの候補の保証文（F-1） | 0.180.0 | 構築 | エンジン・GUI（20 章） | [legal-actions-f1-face-down-attack-guarantee.md](legal-actions-f1-face-down-attack-guarantee.md) |
| C-FROMSTATE | 構築した状態の入口の不変条件（PT5E-FROM-STATE-INVARIANT） | 0.177.0 | 構築 | エンジン・GUI（17 章） | [pt5e-from-state-invariant-audit.md](pt5e-from-state-invariant-audit.md) 9 章 |

## 2. 実装済みだが確認範囲に限界がある項目（閉じる。限界を書く）

| ID | 内容 | 実装 | 確認したこと（版） | 確認していないこと（未確認。未完了には戻さない） | 根拠 |
|---|---|---|---|---|---|
| L-REVEAL17 | 見せる 17 の呼ぶ箇所の `card_id` | 0.184.0 | 17 か所とも構築盤面で再現し、修正後の確認。配布（`a9add68`） | 同じ処理を通るほかのカードの実行。GUI は代表 3 経路（マスターボール・おくりもの・くらげのむれ）とパソコン通信の対照だけを実応答で確かめた（GUI 文書 26 章） | [reveal-identify-v0.184.md](reveal-identify-v0.184.md) |
| L-FOSSILSLOT | 化石の発掘の山札の側の `card_id`、スロットゲームの束の `card_ids` | 0.185.0 | 構築（化石の発掘 6・スロットゲーム 6・対照 6 の 18 事例の前後比較）。配布（`fa98012`）。GUI は束の表示・本人だけの束の対照・化石の発掘を構築盤面の実応答で確かめ、ブラウザは束と対照の 2 件（GUI 文書 27 章） | new_game からの到達。GUI のブラウザでの化石の発掘 | [fossil-slot-reveal-v0.185.md](fossil-slot-reveal-v0.185.md) |
| L-NULL | 束の `cards` の `null`（うらの伏せ）と `card_ids` の契約の整合 | GUI（`5dd80cb`。文書 `95645ff`） | 契約の照合（静的）と、人工の境界の例の単体テスト | `null` のある束の実応答（GUI 文書 28.3 節） | GUI 文書 28 章 |
| L-P6 | 本人のうらのバトル場のにげる（R-5 の P6） | 0.174.0 | 構築。new_game（r2・0.179.0）で「おもてにしてにげた」を 1 回受理 | 拒否・期限の実例 | [legal-actions-p6-face-down-retreat.md](legal-actions-p6-face-down-retreat.md)・[reach-policy 16 章](verification-ai-reach-policy.md)。GUI 14 章・AI 規則 4 |
| L-UR3A | 本人のうらのカードの 2〜3 段の特殊能力（U-R3a） | 0.175.0 | 構築。new_game（r2・0.179.0）で「おもてにして使った」を 1 回受理 | 組が完成しない場面（R-3 の残り。3 章） | [legal-actions-u-r3a-v0.175.md](legal-actions-u-r3a-v0.175.md)。GUI 15 章・AI 規則 5 |
| L-PT5E | 山札から引いて試すトレーナー 6 枚の使う条件（PT-5e 案 1） | 0.176.0 | 構築（双子 42 組） | 受理の前の先読み（D）の読む値 | [legal-actions-pt5e-audit.md](legal-actions-pt5e-audit.md) 9 章。GUI 16 章・AI の追従 |
| L-UP5T | 相手のうらのカードを読む特殊能力・トレーナーの候補（UP-5t-C1・PT-5t-C1） | 0.178.0・0.179.0 | 構築（外へ出る差は修正の前も再現しなかったが、読みは確かめた） | D: 型注釈・登録・スレッドの前提は静的な監査だけ（4 章の性質の前提として保持） | [legal-actions-up5t-audit.md](legal-actions-up5t-audit.md)・[up5t-d-trainer-audit.md](legal-actions-up5t-d-trainer-audit.md)。GUI 18・19 章・AI の追従 |
| L-HIDDEN | 選択肢の数を伏せる決定の情報境界 | 実装済み | new_game（w1・0.181.0）で 4 種類（違反 0） | 残り 18 種類（今のデッキにカードがない） | [coverage-inventory 10.4 節](verification-ai-coverage-inventory-next-batch.md) |
| L-S2A | 準備の補償の続行規約 `PC-SETUP-MULLIGAN-COUNT@1`（S2A） | 実装済み | new_game（w2・0.181.0）で `convention_applied` を 3 閲覧者の公開ログで確認。既定の集合（w3）は準備で停止 | S2A のほかの続行規約・規約集合 PO | 同 10.6 節 |
| L-KINDS | 候補の種類の到達 | 実装済み | 20 種類のうち、13 バッチで受理まで届いた種類は 3.1 節のとおり（旧版をふくむ） | `remove_disguise`・`start_sudden_death` は提示なし。決定 96 種類のうち回答は 11 種類 | 同 3 章。到達は網羅の証明ではない |

## 3. 現在の不具合・未対応・API 制約

今の時点で、確かめられた**エンジンの不具合は 0 件**です。E12 は 0.181.0、交換おじさん・17 か所・化石の発掘・束の公開不足は 0.182.0〜0.185.0 で修正済みです。下は未対応・API 制約・未裁定です。

| ID | 内容 | 区分 | 根拠（最後の版） | 残る最小の作業 | 扱い |
|---|---|---|---|---|---|
| R-2 | うらのバトル場のワザといっしょに選ぶもの（`not_offered`） | API 制約（情報境界の設計の判断待ち D-U75-R2） | [inventory 1 章](verification-ai-inventory.md)（0.180.0 で保証文だけ合わせた）。new_game の r1・s1・t1・t2 で残り（residual）として出た | 示すなら本人の知識だけで何を決められるかを文書で決める | 将来課題（場面は少ない） |
| R-3 | うらのカードの 2 段以上の特殊能力の、組が完成しない場面 | API 制約 | inventory 1 章・U-R3a | なし（今の登録では生成されない経路を含む） | 保持 |
| R-4 | 番のプレイヤーの MAIN のほかの `CheckFaceUpDeckCard` | API 範囲の外（FU2 の裁定が先） | inventory 1 章 | FU2 の裁定のあとに範囲を決める | 保持 |
| R-5 | 入力を返さない候補の残り（P2 の A 群・P3〜P5 の C 群・保守の守り） | API 制約 | [R-5 の監査](legal-actions-r5-audit.md)。対戦で出ていない | なし | 保持 |
| U-PRESTOP | 受理の前に未裁定で止める候補（`play_trainer` 10,104・`discard_from_play` 634・`use_stadium` 36。13 バッチの延べ） | 未裁定による停止（範囲の外） | [coverage-inventory 3.1・3.3 節](verification-ai-coverage-inventory-next-batch.md) | カード・コードごとの内訳の集計（未実施）。→ 2026-11-15: 延べは 2 倍の誤りで、正しくは 5,052・317・18。内訳を調べた（停止コードは記録になく、カードは `use_stadium` と選択肢の一部だけ特定できた）: [受理の前の未裁定の候補の内訳](prestop-ruling-breakdown.md) | **次の候補 1**（6 章）。→ 記録の追加を設計した（未実装）: [記録の追加の設計](prestop-record-design.md)。→ 2026-11-15: 検証用 AI に実装した（TOOL_VERSION 11・計画と完了の形式 7。初回の限定バッチとカード別の内訳の更新は未実施）: [記録の追加の設計と実装](prestop-record-design.md) 11 章。→ 初回の確認バッチを設計した（未実行）: [初回の小規模確認バッチの計画](prestop-first-batch-plan.md)。→ 実行した（4 局すべて完了・R1〜R6 成立・記録用の取得は累積時間の約 0.017%・新しい 4 局だけのカード別の内訳（突風・きずぐすり・ポケモンいれかえ、discard_from_play はすべて本人のうら））: [初回確認バッチ vai-batch-x1 の結果](prestop-first-batch-plan.md) 9 章。→ 3 枚の未裁定の条件と根拠を整理した: [突風・きずぐすり・ポケモンいれかえの受理の前の未裁定の整理](prestop-three-trainers.md)。→ 主な条件の事実を本人の観測から確かめる派生記録を設計した（未実装）: [prestop と本人向けの観測の対応づけの設計](prestop-observation-link-design.md)。→ 証跡の側のスクリプトで x1 の 4 局に適用した（127 行すべて対応・3 条件はすべて成立・L1〜L7 成立。停止コードは記録なしのまま）: 同じ文書の 8 章（きずぐすりの境界条件の変更は 9 章）。→ 突風の GW5 の判断用の資料を作った（未決。推奨は現状維持と追加資料）: [突風の GW5 の判断用の資料](gust-gw5-decision.md)。→ 3 枚のプレイ用の規約の判断一覧（未採用。推奨は 3 条件とも使えない・消費しない。厳密は停止のまま）: [3 枚のトレーナーのプレイ用の規約](play-convention-three-trainers.md)。→ 2026-11-15: 利用者が採用し、0.186.0 で開発用の集合 CS-KYUURA-PLAY-TR3@1 の続行規約として実装した（既定では有効にならない。厳密側の未裁定は残る。台帳の作り直し・GUI の選択と表示は別の単位）: [v0.186](play-convention-tr3-v0.186.md)。→ 2026-11-16: 台帳の作り直し（蓄積の差・TR3 の記録・テスト・道具だけの語の案 B）を 0.187.0 で正式に同期した: [v0.187](token-sync-v0.187.md) |
| U-SETUP | 準備の停止 `UNRESOLVED_MULLIGAN_COMPENSATION`（既定の集合） | 研究上の未解決（既定の集合では止める） | w3（0.181.0）で停止の形を確認 | 続行規約の採否（4 章の判断） | 利用者の判断 |
| U-RULINGS | FU2・DU1・HC1・KP1・FC1 などの既知の未裁定の停止 | 未裁定（研究上の未解決。エンジンの未対応ではない） | inventory 3 章・各版の文書 | 裁定の記録が見つかったときに個別に扱う | 保持（全裁定の一覧は作らない） |
| U-JUDGE | known_stop の根拠のない停止（P2・P3o・ほかの効果の型・再開先、HC1・準備の停止・FU2 の代表） | 検証用 AI の判定の未対応（undetermined のまま） | inventory 5 章・P3 設計 10.9 節。P2・P3o は対戦で未出現 | 根拠の条件の設計 | 次の候補 2 |
| U-MUTATE | 変異の生成器が扱えない契約（`options_by_path` の参照・値の段・初期配置・依存する段の `path_mix`） | 検証用 AI の未対応 | inventory 2 章（V3-3） | — | 将来課題（U7 のテストがある） |
| U-RECORD | 構築盤面の正式な記録形式・R-B の再実行・fixture の依存・版をまたぐ記録 | 記録インターフェースの制限（設計どおりのものをふくむ） | inventory 6 章 | — | 保持 |
| U-METRIC | きぜつの数え方、V3-3 の C1 の公開カード ID の保存 | 計測の未対応 | inventory 7 章 | — | 保持（低） |

## 4. 未採用の仕様判断・性能課題・対象外

| ID | 内容 | 区分 | 根拠 | 扱い |
|---|---|---|---|---|
| D-CHECK | GUI で `answer_decision` を check のあとにだけ送れるようにするか（今は任意） | 未採用の設計判断 | GUI 文書 23.3・23.9・24.7 節 | 利用者の判断。KP1 は check で予告できないので、必須にしても拒否は防げない |
| D-R1 | 旧 r1（0.179.0 の記録）の P3 の行。basis の不一致を緩めない | 採用判断（互換性の案 A〜C は文書だけ） | [P3 設計 10.7 節](verification-ai-lost-target-p3-decision-design.md) | undetermined のまま旧版の記録として保持 |
| D-SETUP | 既定の規約集合で、準備の補償の続行規約を採るか | 採用判断（研究上の未解決） | inventory 3 章・coverage-inventory 10.6 節 | 利用者の判断。S2A では続行を確認済み |
| D-6 | V3 の判定の表（D-6）の全体の採用 | 採用待ち | inventory 5 章 | 保持（低） |
| P-LOG | ログの保持の量・受理の手間（ログの長さに比例）。圧縮・上限・差分の投影はしていない | 性能課題 | [client-api-visible-log-v0.183.md](client-api-visible-log-v0.183.md) 5 章（2200 件で hub 作成 0.197 秒・約 5.6 MB） | 将来課題 |
| P-SCALE | 大量の対戦の照合時間・証跡の量（観測の記録つきで約 2.2 倍） | 性能課題 | inventory 6 章・[scale-budget](verification-ai-scale-budget.md) | 大きな計画の前に判断（今は予算内） |
| P-POLICY | にげるの選び直し・番の中の合計・変異の位置・分布の偏り | 方策の改善 | inventory 8 章 | 範囲の外（利用者の指示） |
| X-UID | uid の方式全体の安全性 | 対象外（限定の監査では証明していない） | [client-api-visible-log-delivery-design.md](client-api-visible-log-delivery-design.md)・GUI 文書 27.9 節 | 対象外のまま保持 |
| X-HISTORY | GUI の全部の出来事の履歴の画面・相手の今の山札の復元 | 対象外 | GUI 文書 27.9・28.4 節 | 対象外 |

## 5. main への統合状況（2026-11-15）

| リポジトリ | main | 取り込み | 作業ブランチ |
|---|---|---|---|
| エンジン（検証用 AI をふくむ） | `b1e4430` | PR #40（`claude/fossil-slot-reveal-v0185`・`ad4514a`）まで。1〜4 章の実装・文書のコミット（`9eddbcf`・`fa98012`・`a2b29e9`・`95206ec`・`0529041`・`a9add68` など）は main の祖先 | リモートは main だけ。ローカルは停止中の lt5 のブランチ（未コミットの未追跡のテストが 1 つ）と、この整理用のブランチ |
| GUI | `593be09` | PR #4（`95645ff`）まで。`5dd80cb`・`ce31d77`・`2674efd` は main の祖先 | リモートは main だけ |

- 過去の文書の「基点は main に入っていない」は、それぞれの作業の時点の記述です。今はどれも main に入っています（過去の文書は書きかえていない）。

## 6. 次の候補（最大 3 つ）

| 順 | 候補 | 影響 | 根拠の確かさ | 既存の確認との重複 | 必要な資源 | 今の道具と情報境界 |
|---|---|---|---|---|---|---|
| 1 | U-PRESTOP: 受理の前に未裁定で止める候補の、カード・コードごとの内訳を保存済みの記録から数える | 大（延べ 1 万回を超える未送信の候補の中身が分からない。どの裁定が対戦の到達を最も狭めているかが分かる。→ 2026-11-15 の訂正: 延べは 5,052・317・18 で、1 万回を超えない。調べた結果は [受理の前の未裁定の候補の内訳](prestop-ruling-breakdown.md)） | 件数は 13 バッチの集計で確か。内訳は未集計 | 小（今まで数えていない） | 小（読み取りと集計だけ。新しい対戦なし） | 扱える（検証者の側の記録を読む。公開はカード・コードの件数だけ） |
| 2 | U-JUDGE: P2・P3o の根拠の条件の設計 | 中（undetermined を減らす） | 低〜中（どちらも対戦で未出現） | 小 | 中（設計とエンジンの根拠テスト） | 扱える |
| 3 | R-2: うらのバトル場のワザといっしょに選ぶものの情報境界の設計判断（D-U75-R2） | 小〜中（残りとして対戦に出ている唯一の R） | 中（残りの出現は記録あり） | 小 | 中（設計・API・GUI） | 設計の判断が要る |

- 利用者の判断が先の事項（D-SETUP・D-CHECK・D-R1）は、作業の候補ではなく 4 章に置きました。

**推奨する次の 1 単位: U-PRESTOP の内訳の集計（調査だけ）**

- 目的: `play_trainer`・`discard_from_play`・`use_stadium` が受理の前に未裁定で範囲の外になった理由を、カード・停止のコードごとに分ける。どの未裁定が多いかを示し、裁定の調査や規約の採否の判断材料にする。
- 範囲: 保存済みの逐次バッチの記録（候補の提示と範囲から外した理由）の読み取りと集計。まず、記録にカードとコードが残っているかを確かめる（残っていなければ、その時点で止めて報告する）。
- 成果物: 内訳の表（検証者用）、公開用の件数と分類、残件一覧への 1 行の追記。
- 実行しないこと: 新しい対戦・seed の探索・judge や replay の実行・範囲を広げる方策の実装・裁定の確定・規約の採用。

## 付録. 今も誤解を生む記述と訂正

元の文は書きかえず、下の「訂正を加えた場所」に参照を足しました。

| 記述（場所） | 今の状態 | 訂正を加えた場所 |
|---|---|---|
| 「GUI の追従は未着手」「GUI の表示は未実装」（README の v0.174〜v0.185 の各行、[inventory](verification-ai-inventory.md) 1 章の R-5・R-3、7 章の PT-5e・UP-5t、9 章） | P6・U-R3a・PT-5e・from_state・UP-5t-C1・PT-5t-C1・F-1・KEEP・log・17 か所・化石の発掘と束は GUI が追従済み（GUI 文書 14〜20・23・25〜28 章） | inventory の冒頭、README |
| 「交換おじさんは修正方式を設計（未実装）」「残り 6 分類は未調査」（inventory 4 章の「種類」の行） | 0.182.0 で修正。w1 の 61 回答の監査は完了 | inventory の冒頭 |
| 「client_api の配信・GUI の表示は未実装」（[implementation-status](implementation-status.md) の v0.182 の節） | 0.183.0 と GUI 25 章で実装 | implementation-status の末尾 |
| 「残り: GUI の束の表示と依存の更新」（[coverage-inventory](verification-ai-coverage-inventory-next-batch.md) 10.4 節の 2026-11-15 の追記） | GUI 27 章で追従した | coverage-inventory の同じ行 |
| 「P3s の new_game からの確かめはまだ」（GUI 文書 24.7 節。2026-11-14 の時点） | t2 の回帰の局で確かめた（1 章 C-P3S） | GUI のファイルは変えていない（ここに記録するだけ） |
| 「基点は main に入っていない」（各作業の文書の基点の表） | 今はすべて main に入っている（5 章） | 書きかえていない（作業の時点の記述） |
