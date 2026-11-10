# U7 の総合検証の先行の実行（E0・E1・E2・G0・G1）

[u7-integration-verification-plan.md](u7-integration-verification-plan.md) の E0・E1・E2・G0・G1 を、2026-11-08 に先に実行した記録です。E3 以降・G2 以降・X1〜X4 は始めていません。G1 は途中で、実行の環境がメモリ不足で止めました（4 章）。止まったあとの自動の再実行はしていません。

## 1. 対象と場所

| 区分 | 値 |
|---|---|
| コードの検証対象（エンジン） | `e26df79cc6dec913c1d15b5d8203df066334d65d`（0.172.0）。実行の木 `C:\dev\kyuura-engine-u7verify`（detached・変更なし） |
| コードの検証対象（GUI） | `b1037bc6651a4a7104a0f1203e73667fac961d33`。実行の木 `C:\dev\kyuura-engine-gui-wt-u75fg`（変更なし） |
| コードの検証対象（renderer） | `af882310059c7f33bc371d31b859b09f5428f6d1`（GUI の lockfile の `resolved`。renderer のリポジトリは読むだけ） |
| 参照した文書の版 | エンジン `05a6749`（文書だけ）、計画 `03e742c`（`claude/u7-integration-plan`） |
| U7 の前の基点（E2 の `--sites` の比べだけ） | `a2c51a1`（`C:\dev\kyuura-engine-u7base`。detached） |
| 環境 | Windows 11 Home 10.0.26300・Python 3.14.6・git 2.49.0（PowerShell から。`MSYS=noglob`）・Node.js 24.18.0・npm 11.16.0・Edge 157.0.4341.42・Playwright 1.65.0。メモリ 15,661 MB（E0 の開始時の空き約 5,086 MB） |
| GUI の依存の導入元（G0） | `server/.venv` の kyuura-engine は Git の URL からの通常のインストール（`direct_url.json` の `vcs_info.commit_id` が `e26df79…`・編集可能でない・`kyuura_engine` は作業場所の `.venv\Lib\site-packages` の下）。fastapi 0.162.0・uvicorn 0.54.0・pytest 9.2.0。renderer は `git+ssh://…/kyuura-card-renderer.git#af88231…`（package 0.1.0） |

コードの固定先は変えていません。この作業で直したのは文書・文書の生成器とそのテスト（6 章）で、`kyuura_engine/` と GUI のコードは変えていないので、E1・G1 の結果は当初の固定のコミットでの結果です（修正の前と後の区別は要らない）。

## 2. E0（固定と準備）

- 3 つのリポジトリで `git fetch` のあと、対象のコミットがあることと、含むブランチを確かめた: エンジン `e26df79` は `origin/claude/u7-5fg-impl`・`origin/claude/u7-integration-plan`（`origin/main` `88ad4d9` は含まない）、GUI `b1037bc` は `origin/feature/engine-u7-5fg`（`origin/main` `088822c` は含まない）、renderer `af88231` は `origin/main`（先頭 `7f9d9b6`）
- 作業の木の指紋（追跡ファイルと sha256）: エンジンの実行の木 750 ファイル・`1c61f6b5…2f6b`・変更なし、GUI の実行の木 115 ファイル・`810a610e…7f34`・変更なし。利用者のエンジンの checkout（main `0c00b56`）は変更なし、利用者の GUI の checkout の未コミットの変更は 13 件のまま（触れていない）
- kyuura `b9e7cff`・変更なし。GUI のポート（8765・8766・5173・5174・4173）の待ち受けなし。python・node・msedge・シェルのプロセスの一覧を記録した（止めていない）

## 3. E1（U7 と直接関係する 30 モジュール）

計画の 30 モジュールと、実際のファイルが同じことを確かめた（差なし）。1 モジュールずつ別のプロセス（`python -u -m unittest -v tests.<モジュール>`。`PYTHONUTF8=1`・`MSYS=noglob`・`PYTHONPATH` なし）、期限はモジュールごとに 1800 秒。

- 結果: 30 モジュール・659 件・失敗 0・エラー 0・skip 0・終了コードが 0 でないモジュール 0・期限切れ 0。2026-11-08 15:05:01〜15:15:19（約 10 分）
- 長いもの: `test_legal_actions_api_design` 227 秒・`test_legal_actions_decision_audit` 118 秒・`test_secret_plan_v0_67` 66 秒・`test_snapshot_replay_v0_158` 47 秒・`test_view_record_v0_155` 33 秒。ほかは 20 秒以下

| モジュール | 件数 | モジュール | 件数 | モジュール | 件数 |
|---|---:|---|---:|---|---:|
| test_legal_actions_u7_1 | 42 | test_legal_actions_u7_5g_face_down_power | 10 | test_energy_control_power_suppression_v0_59 | 27 |
| test_legal_actions_u7_2 | 17 | test_client_api | 9 | test_secret_plan_v0_67 | 24 |
| test_legal_actions_u7_3 | 29 | test_legal_actions_decision_audit | 15 | test_stadium_reuse_special_energy_v0_58 | 41 |
| test_legal_actions_u7_4 | 27 | test_legal_actions_api_design | 13 | test_instant_trainers_v0_55 | 51 |
| test_legal_actions_u7_5ab | 27 | test_legal_actions_u7_5_design | 27 | test_replay_record_v0_153 | 25 |
| test_legal_actions_u7_5c | 32 | test_legal_actions_u7_5fg_spec | 9 | test_replay_run_v0_154 | 23 |
| test_legal_actions_u7_5d | 25 | test_chaos_gym_borrow_t_f1 | 12 | test_view_record_v0_155 | 24 |
| test_legal_actions_u7_5e | 24 | test_distribution | 12 | test_state_snapshot_v0_157 | 37 |
| test_legal_actions_u7_5f | 8 | test_preset_decks_v0_20 | 15 | test_snapshot_replay_v0_158 | 28 |
| test_legal_actions_u7_5g_residual | 9 | test_legal_actions_u7_5g_energy2 | 11 | test_integration_u1_u6_v0_159 | 6 |

この件数は E1 の 1 回の実行の数です。前回の限定の検証（20 モジュール・388 件など）とは別の行で、足し合わせません。文書を読むテストは、実行の木 `e26df79` の文書（`05a6749` の 2 つの文書の差の前）を読んでいます。

計画の「あわせて読む確認」（双子のテストが公開の観測が同じことを先に確かめているかの表）は、この実行では作っていません（未実行。E3 の前に行う）。

## 4. E2（生成物・台帳の検査）

実行の木 `e26df79` の根で、1 つずつ（期限 1800 秒）。

| 検査 | 結果 | 終了コード |
|---|---|---|
| `build_legal_actions_api_design.py --check`・`build_legal_actions_u7_5_design.py --check`・`build_implementation_identity_design.py --check`・`build_convention_records.py --check`・`build_diagnostic_catalog.py --check`・`build_diagnostics_replay_api_design.py --check`・`build_state_snapshot_design.py --check`・`build_play_policy_family_plan.py --check`・`build_stop_policy_classification.py --check`・`check_implementation_assumptions.py --check`・`check_normalization_revalidation.py --check` | problems=0（集計を出す 2 つも問題なし） | すべて 0 |
| `check_card_sources.py` | 方針と一致（記録 1287 件） | 0 |
| `check_research_links.py` | kyuura `71d17289…` の記録と一致 | 0 |
| `check_implementation_assumptions.py --sites`（報告だけ） | new_sites 229・missing_sites 5（台帳に記録した時点の走査との差） | 0 |

`--sites` の差は、同じ道具を U7 の前の `a2c51a1` で実行した結果（new_sites 224・missing_sites 5）と比べて分類した。e26df79 だけの候補箇所は 2 つ（`docs/legal-actions-u7-1.md` 247 行の双子の比べの記述、`scripts/build_implementation_identity_design.py` 204 行の識別の設計案の sha256 の作り方）、a2c51a1 だけは 2 つ（`tests/test_preset_decks_v0_20.py` 151 行の版の注釈の行。版の文字列で ID が変わる。もう 1 つは e26df79 では台帳に記録済みの行）。新しい種類の前提は見つからなかった（読んだ判断。分類の表は証跡の `E2/sites_classification.md`）。数を合わせるための文の書き換えはしていない。

計画の E2 の一覧にない生成器（`build_play_policy_s2a_spec.py`・`build_poison_mist_play_policy_spec.py`）は実行していない（計画の対象の外。U7 で変わっていない）。

## 5. G0・G1（GUI）

GUI の側の記録は GUI のリポジトリの `docs/engine-contract.md` 13.9 節にもあります。

- G0: 作業場所 `b1037bc`・変更なし。導入元は 1 章の表のとおり。ポートの待ち受けなし
- G1 の対象（実際のコードで確かめた。計画と同じ 4 ファイル・14 件）: `turn-basics.spec.ts` 2・`u75e.spec.ts` 3・`u75.spec.ts` 6・`attacks.spec.ts` 3

| 実行 | ファイル | 結果 | 数え方 |
|---|---|---|---|
| run1（15:20） | 4 つを 1 つの絞り込みとして渡した（道具の引数の分け方の誤り） | テストは 0 件（No tests found）・終了コード 1 | 数えない（呼び出しの誤り。道具を直した） |
| run2 | `turn-basics.spec.ts` | 2 件成功（JUnit: failures 0・errors 0・skipped 0）・終了コード 0 | 数える |
| run2 | `u75e.spec.ts` | 3 件成功・終了コード 0 | 数える |
| run2 | `u75.spec.ts` | 中断（15:21:49 に始め、6 件のうち 5 件が標準出力で ✓ のところで、実行の環境がメモリ不足で裏の実行を止めた。JUnit・終了コードなし） | 数えない（中断） |
| run2 | `attacks.spec.ts` | 始めていない | 未実行 |

- 止まったあと: 8766・5174 の待ち受けなし、接続層・Playwright・道具のプロセスなし（止めたものはない）。空きメモリは約 4,976 MB。指示どおり、重い実行（e2e）を自動では再開していない
- 今回の接続層であることの確かめ: 接続層（8766）の待ち受けのコマンド行は相対の `..\server\.venv\Scripts\python.exe` で作業場所の場所を含まないので、祖先のプロセスをたどり、今回起動した npx の子孫であることで確かめた。venv の場所は G0 の `engine_source` の `module`（作業場所の `.venv` の下）。2 秒ごとの観測なので、短い実行の待ち受けは観測にないことがある
- G1 の数え方: 完了した 5 件（2 ファイル）だけ。14 件のうち、u75 の 6 件と attacks の 3 件は今回の結果がない

## 6. 文書の訂正（計画の 1.4 節の 4 件と、X1 の記述）

| 件 | 確かめた事実 | 訂正した場所 |
|---|---|---|
| 1 | `helpers.attachToActive` の呼び出しは `attacks.spec.ts` 33・68・92・97・136 行、`u75.spec.ts` 61 行、`u75e.spec.ts` 30・62 行 | GUI `docs/engine-contract.md` 13.8 の「今回」の説明（記録の数は変えず、説明に attacks を加えて訂正の注を付けた） |
| 2 | `halt` は `scenarios.py` 117 行で `ClientHub.start(decks…, seed)` を呼ぶ（操作の列の再生ではない）。決定待ち・サドン・デスは pikachu_seed9 の列の再生 | GUI `README.md`（テストの節） |
| 3 | U7-5 の設計の JSON の単位（U7-5a〜U7-5g・T-F1）はすべて implemented で、採用の記録の実装した単位と同じ | エンジン `docs/legal-actions-api-implementation-plan.md` の冒頭と単位の表。表は生成器 `scripts/build_legal_actions_api_design.py` から作るので、U7-5 の状態を implemented にし、その根拠を U7-5 の設計の JSON と照らす確かめ（`u7_5_reference_problems`）と、残件（R-2〜R-5・PT-5e・UP-5t・MAIN の partial）を `u7_5_reference` に加えた。回帰テスト `test_u7_5_status_follows_the_u7_5_design_record`。`docs/legal-actions-api-design.json` を `--write` で作り直した |
| 4 | `web/playwright.config.ts` の reporter は `[["list"]]` だけ。JUnit は前回も今回もコマンド行の `--reporter=list,junit` と `PLAYWRIGHT_JUNIT_OUTPUT_NAME` で出した | GUI `docs/engine-contract.md` 13.8（補足）・`README.md`（テストの節に JUnit の出し方） |
| X1 | 計画の 6.2 節の「U7 の網羅を示すには X1 が要ります」は誤り | 計画の 6.2 節: X1 は範囲を広げる追加の手段の 1 つで、作っても U7 全体の網羅の証明ではなく、今回の先行の検証にも必須ではない |

古い実行の記録（GUI の 13.8 の「前回」「今回」の表の数）は書き換えていません。

### 6.1 訂正のあとの確かめ（計画のブランチの木）

訂正は計画のブランチ（`C:\dev\kyuura-engine-u7plan`）の文書・生成器・テストだけです。[testing](testing.md) の文書だけの変更の扱いに従い、変えたファイルを読むテストのクラス・モジュールと生成器の確かめを、1 つずつ実行しました（E1 とは別の行）。結果は 6.2 節。

### 6.2 訂正のあとの確かめの結果

- 木: `C:\dev\kyuura-engine-u7plan`（`03e742c` に、1〜6 章の訂正の未コミットの変更 5 ファイル: `docs/legal-actions-api-design.json`・`docs/legal-actions-api-implementation-plan.md`・`docs/u7-integration-verification-plan.md`・`scripts/build_legal_actions_api_design.py`・`tests/test_legal_actions_api_design.py`。このあと同じ内容をコミットした）
- 対象（変えたファイルと `03e742c` で参照を加えた README・`docs/implementation-status.md`・`docs/legal-actions-u7-5fg.md` を読むもの。静的に探した）: 23（モジュール 7・クラス 16）。各対象の前に空きメモリを確かめ（3,000 MB より少なければ止める。最小 4,935 MB で止まらなかった）
- 結果: 23 対象・110 件・失敗 0・エラー 0・skip 0・終了コード 0。2026-11-08 15:23:22〜15:30:31。生成器 `build_legal_actions_api_design.py --check`・`build_legal_actions_u7_5_design.py --check`・`check_implementation_assumptions.py --check` は problems=0、`--sites` は E2 と同じ集合（new_sites 229・missing_sites 5。この訂正で候補箇所は増えていない）
- `test_legal_actions_api_design` は E1（e26df79 の木・13 件）とこの確かめ（計画のブランチ・新しいテストを加えて 14 件）で 2 回実行したが、木が違う別の行で、足し合わせない

## 7. 証跡

- 恒久の保存先: `C:/dev/kyuura-engine-verification-u7/`（リポジトリの外。Git に入れていない）
  - `verifier/runs/2026-11-08-e0-e1-e2-g0-g1/`: 今回の実行（E0・E1・E2・G0・G1・DOC・tools）。JUnit・標準出力・標準エラー・summary.jsonl・指紋・プロセスの一覧・画面のフォルダ。未確認のものを含むので verifier の側
  - `verifier/preserved/`: 既存の一時の証跡の写し（5 組・243 ファイル。写す前後の sha256 が一致。原本は残した。`index.json` に元の場所・時点・対象・写し先）。過去の記録で、今回の結果ではない
  - `public/runs/2026-11-08-e0-e1-e2-g0-g1/`: 中身を読んで秘密を含まないと確かめた集計だけ（`summary.md`）
  - `MANIFEST.md`・`manifest.json`・`sha256.json`（全ファイルの sha256）

## 8. 残ることと、次へ進む判断の材料

- 未実行: G1 の `u75.spec.ts`（6 件）・`attacks.spec.ts`（3 件）、E3 以降（全体のテスト・監査・配布）、G2 以降、X1〜X4
- メモリ: e2e の実行中に、端末全体の空きが少なくなった（E0 の時点の空きは 15,661 MB のうち約 5,086 MB）。G1 の残りと、E3（v0.159 は 283 モジュール・4,778 秒）は、ほかのアプリを閉じて空きを増やしてから、利用者の指示で始めるのがよい。e2e は 1 ファイルずつのままにする
- 双子のテストの読む確認（計画 E1）は未実行

## 9. 再開（2026-11-08 16:20〜16:26。双子の読み取りの点検と G1 の残り 9 件）

前の実行（1〜8 章）とは別の実行です。E1・E2 と、G1 の完了した 5 件（turn-basics 2・u75e 3）は再実行していません。中断した u75 の途中の 5 件は数えていません。証跡は `verifier/runs/2026-11-08-g1-resume-twins/`。

### 9.1 始める前の確かめ

- エンジン: 利用者の checkout main `0c00b56`・変更なし、計画のブランチ `d7a7c44`、実行の木 `e26df79`・変更なし。GUI: 利用者の checkout の未コミットの変更 13 件（触れていない）、記録のブランチ `1daabb9`、実行の木 `b1037bc`・変更なし。renderer `af88231` は `origin/main` の祖先
- 待ち受け（8765・8766・5173・5174・4173）なし、接続層・Playwright・道具のプロセスなし
- メモリ: 空き 4,444 MB、コミットの上限 30,509 MB のうち空き 5,736 MB（約 81% がコミット済み）。前回の停止の原因を空きメモリだけに決めない（コミットの空きも小さい）

### 9.2 双子の読み取りの点検（計画 E1 の残り）

`e26df79` の tests を読んだ（サブエージェントの読みと、一部をこの作業で直接確かめた。一覧は証跡の `TWIN/twin_review.md`）。網羅の証明ではありません。

- A（前提の一致を明示的に検査）13・B（共通の構築と差分から分かるが検査なし）3・C（本人の知識や公開の情報も違う。情報境界の双子ではない）4・D（確定できない）0
- 前提の検査の道具: `tests/log_audit.py` の `public_view`（observe と visible_log）と `owned_card_ids`（デッキリストの知識）。本人の observe は本人の手札・本人のうらの本当のカードを含むので、本人の `public_view` と `owned_card_ids` の一致で公開の情報と本人の知識の一致を確かめられる
- B の 3 つ（`test_chaos_gym_borrow_t_f1.py` の TwinTest。使ったあとの観測だけを比べ、使う前の状態の前提を検査していなかった）に、前提の検査（使う前の状態の observe・visible_log・所有するカードの id）を加えた。そのモジュールだけを計画のブランチの木で実行: 12 件・失敗 0・エラー 0・skip 0
- C: `test_legal_actions_u7_5ab.py` の RevealFaceDownTest（本人のうらのカードの本当のカードが違う。本人の知識で結果を予告しないことの確かめ）、`test_legal_actions_u7_5d.py` の seed 1 と 17 の別の対戦（テストの説明自身が双子でないと書く）、`test_legal_actions_u7_5g_residual.py` の本人の残りの公開の部分の比べ。u7_3・u7_4 の TwinTest の、プレイヤー 1 の応答の比べ（1 の手札・デッキリストも違う）も情報境界の双子には数えない
- 不足（漏れ・不具合ではない）: 前提を行動の前だけで確かめるもの（u7_1・decision_audit）、本人の visible_log を比べないもの（u7_5f・u7_5d）、前提と結果を 1 つの比べに入れたもの（u7_5c・u7_5d・u7_5e）。広く直すのは範囲の外として保留した。この点検で実際の情報の漏れ・不具合は見つけていない

### 9.3 G1 の残り 9 件

1 件ずつ別の Playwright のプロセス。絞り込みはファイルと行（`npx playwright test e2e/<ファイル>:<行> --reporter=list,junit`）で、JUnit の件数が 1 でテスト名が対象の完全な名前と同じことで、意図した 1 件だけが選ばれたことを確かめた。最初の 1 件のあと、結果・資源・残りのプロセスを確かめてから残りの 8 件を続けた。各件の前に空き 1,500 MB・コミットの空き 2,000 MB を下回れば始めない条件をつけた（下回らなかった）。

| # | 対象 | 結果 | テストの時間 | プロセスの時間 |
|---|---|---|---:|---:|
| 1 | u75.spec.ts:39 ラッキースタジアム | 成功（1/0/0/0）・終了コード 0 | 3.6 秒 | 16.3 秒 |
| 2 | u75.spec.ts:59 ヤマブキシティジム | 成功・0 | 3.6 | 13.0 |
| 3 | u75.spec.ts:73 マチスの秘策 | 成功・0 | 4.1 | 14.1 |
| 4 | u75.spec.ts:104 ピッピ人形 | 成功・0 | 3.5 | 11.8 |
| 5 | u75.spec.ts:115 錯乱ジム | 成功・0 | 4.9 | 15.3 |
| 6 | u75.spec.ts:141 「ばける」の解除（再生した固定例） | 成功・0 | 2.2 | 9.9 |
| 7 | attacks.spec.ts:26 プリセットのデッキ | 成功・0 | 4.9 | 13.6 |
| 8 | attacks.spec.ts:89 ファイヤーのデッキ | 成功・0 | 5.4 | 14.5 |
| 9 | attacks.spec.ts:133 狭い画面 | 成功・0 | 3.2 | 11.0 |

テストの時間は JUnit の testcase（設定の期限 120 秒の対象）、プロセスの時間は接続層・Vite の起動と終了を含む全体（道具の期限 600 秒）で、別に記録した。タイムアウト・中断・失敗はない。

- G1 の到達: 対象 14 件のうち、前の実行の完了 5 件（turn-basics 2・u75e 3）と今回の 9 件で、14 件すべてに成功の結果がある（実行は 2 回に分かれ、合わせて 1 回の実行ではない）
- 資源: 今回起動したプロセスの木（npx から下。node 6・msedge 9・cmd 5・python 2 など 21）の私用のメモリの最大は 695〜1,501 MB。端末の空きの最小 3,293 MB、コミットの空きの最小 4,218 MB。Claude Code・OS からの停止の知らせはなかった（前景で 1 件ずつ実行した）
- 観測の不足: 1 件目は道具の誤り（子孫のプロセスを探す鍵の型の違い）で子孫と使用量を記録できず、直して 2 件目から記録した（1 件目は成功しているので再実行していない）。待ち受けの観測（2 秒ごと）は 9 件とも記録がなかった（原因は確かめていない）。今回の接続層であることは、始める前に待ち受けがないこと・設定の `reuseExistingServer: false`（使用中のポートなら Playwright が失敗する）・接続層（python）と Vite（node）が今回起動した npx の子孫として記録されたこと・終わったあと待ち受けがないことで確かめた。待ち受けの pid とコマンド行の照合はできていない
- 後始末: 各件のあと、今回の子孫と記録したプロセスで生きているもの 0、待ち受け 0。止めたプロセスはない。他のアプリ・他のセッションのプロセスは閉じていない

### 9.4 残ること

- E3 以降・G2 以降・X1〜X4 は未実行
- 端末のコミットの空きは 4〜6 GB（上限の約 80% がコミット済み）で、e2e 1 件の木で約 1.5 GB を使う。E3（全体のテスト）は 1 モジュールずつでも長い（v0.159 で 4,778 秒）ので、始める前に、ほかのアプリを閉じてコミットの空きを増やせるかを利用者に確かめるのがよい
- 待ち受けの pid の観測の道具は、次の GUI の段の前に直す（直さないなら、今回と同じ間接の確かめになることを記録する）

## 10. その後

- E3 以降・G2 以降の必須の段は、[u7-integration-verification-e3-g5.md](u7-integration-verification-e3-g5.md) で実行した。待ち受けの観測（5 章・9.3 節）は、その文書の 6.5 節で訂正した（netstat・Get-NetTCPConnection の待ち受けの表示はこの環境で決め手にならない）
