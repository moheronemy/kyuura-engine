# 停止の方針の台帳の 0.189.0 への同期

2026-11-17。生成物だけの同期です。エンジン・生成の道具・入力・パッケージ内データ・版は変えていません。前回の正式な同期は [token-sync-v0.187.md](token-sync-v0.187.md)（0.187.0）です。

## 1. 基点

| 項目 | 値 |
|---|---|
| 基点 | `claude/r2-coin-preflight-fix` = `dd9bee9`（0.189.0。origin と一致。main 未統合）。配布固定 `021510c` |
| 作業 | worktree `kyuura-engine-lt60`、ブランチ `claude/stop-ledger-sync-v0189` |
| GUI の参照 | `feature/engine-0189-r2-coin` = `ae30f6c`（読むだけ） |

基点では、`build_stop_policy_classification.py --check` だけが「生成物が古い」で失敗していました。ほかの生成の検査 8 つは成功していました。

## 2. 隔離した生成と差の分類

- 生成器の入力は、リポジトリのコードと `docs/pre-freeze-gap-inventory.json`・`kyuura_engine/data/research_links.json` です。外部の道具の証拠 `C:/dev/kyuura-engine-verification` は読むだけで、作業の前後で同じハッシュでした（775 ファイル）。
- 隔離先は、履歴を持つ別の worktree（基点と同じコミット）です。既存の順（台帳 → 設計案 → 場面の索引 → 診断のカタログ）に `--write` を流しました。
- 変わったのは `docs/stop-policy-classification.json` だけでした。設計案・`docs/ruleset-mode-design.md` の生成区画・場面の索引（`kyuura_engine/data/convention_records.json`）・診断のカタログは同じです。

差は 38 の路で、10 項目（どれも `active`）に分かれます。

| 分類 | 路 | 内容 |
|---|---|---|
| 行の位置だけ | 5 | `resolution/flow.py` の 179 → 185 と 186 → 192（`UNSUPPORTED_PREFLIGHT_LIMIT`・`UNSUPPORTED_LEGACY_PREFLIGHT` の実装の場所）。0.189.0 の `_use_attack` の変更（8 行の追加・2 行の変更）で、それより後ろの行が 6 行ずれたため |
| 公開済みテストの参照の追加 | 29 | テストのファイルの一覧と数（`files_total`・`mention_lines`・`assert_like_lines`）。足されたのは規則 10（`test_verification_ai_recover_zero_r10`・`test_recover_zero_energy_premise_v0_187`）・P2（`test_verification_ai_lost_target_p2`・`test_lost_target_p2_min_v0_187`）・R-2（`test_legal_actions_r2_stadium_coin_v0_188`）・先読み修正（`test_preflight_face_down_attacker_v0_189`）の単位のテスト。削除はない |
| 表示の上限 | 4 | `reachability.evidence`（生成器が並べたテストのファイルの先頭 5 件）の入れ替わり。新しいテストが並びの前に入り、5 件目より後ろへ押し出されたものがある（一覧から消えたテストは、`tests.files` には残る） |
| 件数・順序だけ | 0 | — |
| 新しいトークン・分類の矛盾・未分類 | 0 | — |
| 停止条件・裁定・規約・実行時データの意味 | 0 | — |

- 変わらなかったもの:
  - 各項目の `id`・`entry_kind`・`status`・方針の状態・`reachability.status`・`current_stop` のコード
  - 台帳の上位の項目（`counts`・`updates` など）
  - 案 B の開発用トークンの分類と `convention_note`（26 の路）
- テストのファイルへの言及は、文字列の出現の数です。実際の停止の場所・到達の実績ではありません（到達の区分 `reachability.status` は変わっていない）。

## 3. 同期の条件と正式な同期

**同期の条件（すべて満たした）:**
- 未分類・矛盾は 0 件です。
- すべての差に根拠があります（各単位のテスト・0.189.0 の行の追加・生成器の表示の上限）。
- 裁定・規約・停止条件の新しい判断は要りません。
- 生成器の修正は要りません。
- パッケージ内データは変わりません。
- 識別も変わりません（4 章）。

**正式な同期:**
- worktree `lt60` で同じ順に `--write` しました。正式の台帳は隔離した生成とバイトまで同じでした（sha256 `2EC706ED…`）。
- 2 回目の `--write` で差は出ませんでした。
- 台帳の UPDATES（採用の記録）は足していません。ゲームや規約の新しい採用ではないためです。
- **生成の検査:** 9 つすべて成功しました（台帳・設計案・場面の索引・診断のカタログ・規約の仕様案 2・診断と再現の API の設計・実装の識別の設計・決定の場所）。
- **関連テスト:** 1 モジュールずつ別プロセスで 7 つ流し、すべて成功しました（`test_stop_policy_classification`・`test_stop_policy_generator_tr3_v0_186`・`test_stop_policy_token_roles_v0_186`・`test_play_policy_family_plan`・`test_conventions_v0_142`・`test_diagnostics_adapter_v0_152`・`test_distribution`）。

## 4. 識別

作業の前後で次が同じでした。版上げ・wheel の作成・再導入はしていません。
- パッケージの全 62 ファイルのハッシュ
- エンジン 0.189.0
- behavior `c7ba8323…`・instrumentation `13c773a8…`
- P1・P2・P3 と規則 10 の専用 basis
- TOOL_VERSION 13・道具の識別・判定の規則 10・形式 7
- 規約集合 5 つの識別と既定の集合

## 5. 状態

- 停止の方針の台帳は 0.189.0 のコードと同期しました。
- GUI は `feature/engine-0189-r2-coin`（`ae30f6c`）で 0.189.0 に追従済みとして扱います。この単位では確かめていません。GUI の main には未統合です。
- R-2 のほかの追加選択は未対応のままです。

証跡は `kyuura-engine-verification-vai/verifier/runs/stop-ledger-sync-v0189/` です。
