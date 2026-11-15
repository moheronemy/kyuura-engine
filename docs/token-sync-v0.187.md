# v0.187: 停止の方針の台帳・設計案・実行時の場面の索引の正式な同期（案 B）

2026-11-16。`kyuura_engine` の版は 0.187.0。

正式な生成物に次の 3 つを反映しました。

- 停止の方針の台帳の蓄積の差（[差の調査](stop-ledger-drift-audit.md)の A・B・C・D と、F の修正）
- TR3 の採用の記録
- テスト・道具だけの語の分類（[案 B](test-only-token-design.md) 9 章）

ゲームの処理・裁定・規約の内容・診断のカタログは変えていません。

- **基点:** `claude/test-only-token-impl` の `c2c50e8`（生成の道具・分類の入力は `d83f8f3`。origin と一致。main `b1e4430` の子孫で main に入っていない。版 0.186.0）
- **作業:** worktree `C:\dev\kyuura-engine-lt44`、ブランチ `claude/token-sync-v0187`
- **コミット:**
  - `31ce43d`: 生成物の同期と、1 テストの期待
  - `d562ec1`: 版と台帳の UPDATES。**配布の確かめの固定コミット** `d562ec16e3f493569ed0251cbcf9062ceccdbb1a`
  - この文書のコミット
- 公開のリモートのどの参照にも 0.187.0 以降の版はなく、版は 1 回だけ上げました。
- **証跡:** `kyuura-engine-verification-vai/verifier/runs/token-sync-v0187/`

## 1. 同期の前の確かめ（基点、読み取りだけ）

- 台帳の `--check` は「生成物が古い」の 1 件だけで exit 1 でした。分類の問題は 0 件です。ほかの生成の検査は exit 0 でした。
- 正式な台帳は `schema_version` 1 で、作り直す台帳は 2 です。
- 12 件の役割と根拠は、設計の対応表と隔離した生成のどちらとも一致しました。未分類・矛盾はありませんでした。
- 生成の入力（生成の道具・分類の入力・研究の対応表・棚卸し・実装上の仮定の台帳）の sha256 は、隔離した生成の記録と同じでした。
- リポジトリの外の道具の証拠（`C:/dev/kyuura-engine-verification` の `*.json` 61 件）の並びの sha256 も同じでした。
- メモリの上で作り直した台帳は、隔離した生成の台帳とバイトまで同じでした。

## 2. 同期した生成物

生成の手順と依存の順は、隔離した生成と同じです。

1. 台帳 `--write`（台帳と `ruleset-mode-design.md` の生成区画）
2. 設計案 `--write`（JSON と `play-policy-family-plan.md` の生成区画）
3. 場面の索引 `--write`

台帳を読むほかの生成物（診断のカタログ・診断と再現の API の設計・S2a と毒の霧の仕様案・実装上の仮定の台帳）は `--check` で確かめ、作り直す必要はありませんでした。

| 生成物 | 基点 | 同期のあと | 隔離した生成と |
|---|---|---|---|
| `docs/stop-policy-classification.json` | `e02455ee…`（schema 1・429 項目） | `748e49e1…`（schema 2・433 項目） | バイトまで同じ |
| `docs/ruleset-mode-design.md` の生成区画 | `2e60c63d…` | 変わらない | 同じ |
| `docs/play-policy-family-plan.json` | `6bf484e4…`（場面の行 399） | `e1d85069…`（391） | バイトまで同じ |
| `docs/play-policy-family-plan.md` の生成区画 | `c872135b…` | `bb526d64…` | 展開先の文書とバイトまで同じ |
| `kyuura_engine/data/convention_records.json` | `6d81dcfc…`（場面 398） | `d10d1721…`（390） | バイトまで同じ |
| `kyuura_engine/data/diagnostic_catalog.json` | `6c265dd7…` | 変わらない（`--check` exit 0） | — |

- `play-policy-family-plan.md` の差は、件数の表の 2 行（場面 399 → 391、区分 E 19 → 11）と、内訳の表の「E テスト・道具だけのコード 8」の 1 行の削除だけです。
- 2 回目の `--write` で、追跡ファイルに差は出ませんでした。
- **版のコミット（`d562ec1`）の差:** 台帳の生成の道具の `UPDATES` に 0.187.0 の項目を足し、台帳を作り直しました。
  - 台帳の差は `updates` の 1 項目だけです。比べた結果は `out/ledger_diff_isolated_to_versioned.json` で、1 件・`/updates`・changed でした。
  - 0.137〜0.186 と同じく、台帳を変えた版の記録です。避けられない差なので、正規化や除外で消していません。
  - 設計案・場面の索引・設計の文書・診断のカタログは、このコミットで変わりません。

### 2.1 台帳の差の説明

- **基点 → 同期:**
  - 層 1（生）の差は 1,708 件、行番号を除いた層 2 は 150 件です（`out/ledger_diff_base_to_synced.json`）。
  - 基点の台帳は、前の単位の調査の時点の正式な台帳と同じです（`e02455ee…`）。
- **前の単位の生成 → 同期:**
  - 前の単位の生成は、生成の道具の修正のあとのもの（`ledger-generator-tr3-fix` の `fixed1`）です。
  - 差は 42 件で、すべて意味のある差です（`out/ledger_diff_fixed1_to_synced.json`）。
  - 内訳は、12 件の `status`・`token_role`・`token_role_basis` と、`counts`・`schema_version`・`token_classification` だけです。
- 基点から前の単位の生成までの差は、前の単位で全件を対応づけました（A 1,558・B 2・C 73・D 38 と、F の修正 3、TR3 の記録の追加）。この 2 段で、今回の差を説明できます。
- **項目の数の変化（429 → 433）:** 前の単位で、テスト・道具だけの新規 4 件が台帳に入るようになったためです。4 件はどちらも場面の索引には入りません。

## 3. 分類・場面の索引・停止コードの対応・TR3

- **台帳:**
  - `by_status` は active 399・test_only 11・historical 3・fixed 20 で、合計 433 は項目の数と一致しました。
  - 役割ごとの数は fixture 9・mutation_operand 1・historical_engine_code 1・non_code_identifier 1 で、合計 12 は `test_tool_only_codes` と一致しました。
  - 12 件の役割は、設計の対応表と一致しました。分類の問題は 0 件です。
- **場面の索引:**
  - 場面は 398 → 390 です。消えたのは既存のテスト・道具だけの 8 件で、新規 4 件は入りません。
  - 停止コード → 場面の対応（`scene_index.codes`）と `current_behavior` は、基点と同じです。上位で変わったのは `scene_index.scenes` だけです。
- **設計案:** 場面の行は 399 → 391 で、対象の語の行は残りません。上位の差は `counts`・`scenes`・`sources`（台帳の項目の数）です。
- **前の試算との比較:** 試算（場面 390・active 399 と状態ごとの数）と同じ値でした。件数は生成の結果を照らしたもので、合わせるための固定値ではありません。
- **TR3:**
  - 採用の記録 `AGR-PLAY-TR3-*` 4 項目と `DEC-USE-WITHOUT-EFFECT`（partly_agreed）が、正式な台帳に入りました。基点の台帳にはありませんでした。
  - 厳密側の 3 つの停止コードは active のままで、場面の索引にあります。停止コード → 場面の対応も同じです。
- **規約と集合:**
  - 固定の照合値は、集合 4（旧状態用を除く）・規約 23 ですべて一致しました。
  - TR3 の集合の確かめも問題 0 件です。
  - `kyuura_engine/conventions.py` は変えていません。

## 4. 生成の検査とテスト

すべて、実際の Git 履歴のある worktree で実行しました。対象と理由は、実行の前に `out/related_tests_plan.md` へ記録しました。

### 4.1 生成の検査（`--check`、1 つずつ別のプロセス）

| 道具 | 基点 | 同期のあと | 版のあと |
|---|---|---|---|
| `scripts/build_stop_policy_classification.py`（分類の検査を含む） | 1（生成物が古い） | 0 | 0 |
| `scripts/build_play_policy_family_plan.py` | 0 | 0 | 0 |
| `scripts/build_convention_records.py` | 0 | 0 | 0 |
| `scripts/build_diagnostic_catalog.py` | 0 | 0 | 0 |
| `scripts/build_diagnostics_replay_api_design.py` | 0 | 0 | 0 |
| `scripts/build_play_policy_s2a_spec.py` | 0 | 0 | 0 |
| `scripts/build_poison_mist_play_policy_spec.py` | 0 | 0 | 0 |
| `scripts/build_implementation_identity_design.py` | 0 | 0 | 0 |
| `scripts/build_legal_actions_api_design.py` | 0 | 0 | 0 |
| `scripts/build_legal_actions_u7_5_design.py` | 0 | 0 | 0 |
| `scripts/build_state_snapshot_design.py` | 0 | 0 | 0 |
| `scripts/check_implementation_assumptions.py` | 0 | 0 | 0 |
| `scripts/check_normalization_revalidation.py` | 0 | 0 | 0 |

- コマンドは `python -X utf8 -B <道具> --check` です（cwd は worktree）。上の 13 の道具の `--check` は、同期のあとと版のあとに、すべて exit 0 でした。
- 一覧の外の道具:
  - `scripts/legal_actions_decision_sites.py` は main のないデータの一覧で、検査の道具ではありません。
  - `scripts/prize_order_followup.py` は v0.140 より前の木で動かす道具で、今の木では exit 1 になります（基点でも同じ。今回の変更とは関係ありません）。
  - `scripts/extract_*.py` はカードデータの抽出で、kyuura を読むため実行していません（今回の入力ではありません）。

### 4.2 テスト（1 モジュールずつ別のプロセス）

- **同期のあと（25 モジュール）:**
  - 1 回目は 24 成功・1 失敗でした。失敗は `tests.test_stop_policy_token_roles_v0_186` の、「正式な台帳は schema 1 のまま」という 0.186 の時点の期待です（計画に書いた、同期で変わる期待）。
  - 期待を schema 2 に変え、旧形式の台帳に分類の検査が何も足さないことの確かめは残しました。
  - 2 回目は、編集が反映される前の実行で、同じ失敗でした。3 回目は 13 テストすべて成功です。
  - 対象: 停止の方針の 3 モジュール、設計案・2 つの仕様案、診断のカタログの 2 モジュール、規約の基盤、TR3、3 つの規約集合、U1〜U6 の統合、実装の識別の設計、再現用記録・再実行・snapshot の 3 モジュール、検証用 AI のバッチ・P1・P3・固定の指紋、公開の入口、研究の対応表。
- **版のあと（14 モジュール）:** すべて成功しました。
  - 版の期待、配布の形、版を読むサイドの順番のテスト
  - 識別の設計、再現用記録・snapshot の 2 モジュール
  - 検証用 AI のバッチと固定の指紋
  - 規約の基盤、TR3、停止の方針の 3 モジュール
- **文書のあと:** 4.3 節を参照。
- 全体のテスト・新しい対戦・seed 探索・judge・replay はしていません。

### 4.3 文書のあと

（文書のコミットのあとに記入）

## 5. 版と識別

| 項目 | 基点 `c2c50e8`（0.186.0） | 同期のあと `31ce43d` | 版のあと `d562ec1`（0.187.0） |
|---|---|---|---|
| エンジンの版 | 0.186.0 | 0.186.0 | 0.187.0 |
| behavior_digest（58 ファイル） | `3871f75a…` | `ee554790…` | `ae974fff…` |
| instrumentation_digest（4 ファイル） | `13c773a8…` | 同じ | 同じ |
| P1 の basis | `2ed8732f…` | 同じ | 同じ |
| P3 の basis | `9499db41…` | 同じ | 同じ |
| 検証用 AI の TOOL_VERSION と道具の識別 | 11・`6e0616cc…` | 同じ | 同じ |
| 判定の規則・計画・完了の形式 | 8・`kyuura-vai-batch-plan/7`・`kyuura-vai-batch-complete/7` | 同じ | 同じ |

- パッケージの 62 ファイルのうち、基点から変わったのは次の 2 ファイルだけです。
  - `kyuura_engine/data/convention_records.json`（同期）: ゲームのデータとして behavior_digest に入ります。同期のあとの値 `ee554790…` は、隔離した試算と同じです。
  - `kyuura_engine/__init__.py`（版の文字列）
- 最終の値と試算の違いは、版の文字列（`__init__.py`）だけで説明できます。
- 識別の対象の一覧（behavior 58・instrumentation 4・P1/P3 の basis のファイル）は変えていません。
- 旧記録・snapshot・計画は、それぞれを作った版と識別に対応付けたままです。再判定も、識別の書き換えもしていません。0.186.0 以前の記録を読む・拒否するテスト（再現用記録・snapshot・検証用 AI）は成功しました。

## 6. 配布の確かめ

固定コミット `d562ec16e3f493569ed0251cbcf9062ceccdbb1a` で次を行いました。

1. `git archive` をリポジトリの外に展開しました。パッケージのファイルは 62 で、基点と同じ数です。
2. `pip wheel --no-deps` で `kyuura_engine-0.187.0-py3-none-any.whl`（sha256 `57cccb46…`）を作りました。
3. `scripts/check_distribution.py --wheel` は exit 0 でした（required=62・problems=0）。
4. リポジトリの外の新しい venv に、`pip install git+https://github.com/moheronemy/kyuura-engine.git@d562ec16e3f493569ed0251cbcf9062ceccdbb1a` で導入しました（非 editable、exit 0）。
   - 導入されたのは kyuura-engine 0.187.0 と pip だけで、依存はありません。
   - `direct_url` は Git URL と完全なハッシュです（commit_id・requested_revision とも固定コミット）。
   - 読み込み元は site-packages です。

**スモーク:**

- 盤面は、固定コミットの展開でこの版の snapshot として作りました。突風・ポケモンいれかえ・きずぐすりの 3 種類について、厳密側・TR3・TR3 で対象ありの 3 通りで 9 盤面です。旧版の snapshot は使っていません。
- ソースと導入物で同じスモークを実行し、どちらも問題 0 件、結果の sha256 が同じ（`24437819…`）でした。識別もソースと同じです。
- 確かめた内容:
  - 厳密側: 3 つの未裁定の停止が残ります。
  - TR3: 対象がない 3 条件は、規約つきの使用不可になります。
  - TR3 で対象あり: 受理され、正常な対照は変わりません。
  - 実行時の場面の索引: 場面 390、テスト・道具だけの語は 0 件、厳密側の 3 コードは索引にあります。
  - 規約・集合の固定の照合値は一致しました。
- 9 盤面の結果は、v0.186 のスモークの結果とすべて同じでした。

## 7. 残る未確認と別の単位

- **GUI:** 依存（0.187.0）の更新と表示の追従は別の単位で、今回は変えていません。
  - 場面の索引からテスト・道具だけの 8 件が消えたことが、GUI の表示の対象に関係するかは確かめていません。
- **到達の確認:**
  - 場面の索引・停止コードの対応は、静的な生成と構築盤面のスモークで確かめました。new_game から実際に到達したことは確かめていません。
  - テストが場面の ID を参照していることは、実際の到達の実績ではありません。
- **生成の道具の都合:** 台帳の生成の道具は、リポジトリの外の道具の証拠（`C:/dev/kyuura-engine-verification`）を読みます。その中身が変わると、台帳の `--check` が「生成物が古い」になりえます（今回は並びの sha256 が隔離した生成と同じでした）。
- **今の木で動かない既存の道具:** `scripts/prize_order_followup.py` は、今の木では exit 1 になります（既存の動き。今回は扱っていません）。
- 全体のテストは実行していません。
