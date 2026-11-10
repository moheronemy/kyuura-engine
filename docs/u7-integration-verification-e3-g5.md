# U7 の総合検証の実行（E3・E4・E5・G2・G3・G4・G5）

[u7-integration-verification-plan.md](u7-integration-verification-plan.md) の必須の段の残り（E3〜E5・G2〜G5）を、2026-11-08 に実行した記録です。前の段（E0〜E2・G0・G1）は [u7-integration-verification-e0-g1.md](u7-integration-verification-e0-g1.md) にあります。X1〜X4（費用の大きい追加）は実行していません。網羅の証明ではありません。

## 1. 対象と場所

| 区分 | 値 |
|---|---|
| コードの検証対象 | エンジン `e26df79cc6dec913c1d15b5d8203df066334d65d`（0.172.0）・GUI `b1037bc6651a4a7104a0f1203e73667fac961d33`・renderer `af882310059c7f33bc371d31b859b09f5428f6d1`。固定は変えていない |
| 実行の木 | エンジン `C:\dev\kyuura-engine-u7verify`（detached・変更なし）。GUI `C:\dev\kyuura-engine-gui-wt-u75fg`（変更なし）と、G4 のクリーンな場所 `C:\dev\kyuura-engine-verification-u7\clean\gui-b1037bc` |
| 文書の版 | 計画と記録のブランチ `claude/u7-integration-plan`（この文書を加える前は `1244cfc`） |
| 環境 | E0 の記録と同じ道具の版。開始のときの空きメモリ約 8.0 GB・コミットの空き約 16.7 GB（上限約 26.4 GB） |

この作業で `kyuura_engine/`・tests・GUI のコード・renderer は変えていません。結果はすべて当初の固定のコミットでの結果です（修正の前と後の区別は要らない）。

## 2. 実行の決まり

- 重い処理は並列にしない。1 モジュール・1 ファイル・1 コマンドずつ別のプロセスで、前のものが終わってから次を始めた
- 各モジュール・コマンドの前に、空きメモリ 1,500 MB・コミットの空き 3,000 MB 以上を確かめた（下回れば始めずに止める）。下回ったことはない
- 開始・終了・コマンド・終了コード・件数・標準出力・標準エラー・JUnit を証跡に残した（7 章）
- 成功した検証は再実行していない。下の 3.2 の再実行は、起動の環境の誤りで失敗・skip したものだけ

## 3. E3（全体のテスト）

### 3.1 1 回目（Git Bash から起動）

- 16:49:18〜18:17:54。303 モジュールを 1 つずつ `python -u -m unittest -v tests.<名前>`（期限 3,600 秒）。期限切れ 0・停止 0
- 303 モジュール・8,316 件。終了コード 1 が 11 モジュール（失敗 2・エラー 19）、skip 2
- 最も長いのは `test_card_sources` の 640 秒。空きメモリの最小 7,422 MB・コミットの空きの最小 16,369 MB

### 3.2 失敗の分類と再実行

- 11 モジュールの失敗・エラーはすべて、テストの中の `git -C <木> show|archive|merge-base …` の終了コード 128（`not a git repository`）でした。実行の木の `.git` は MSYS の形の道（`gitdir: /c/dev/…`）を指し、Git Bash から継いだ環境の git はそれを解けません。PowerShell から同じ呼び出しは成功します。テストの失敗ではなく、起動の環境の誤りと分類しました
- 同じ原因の skip 1 件（`test_neo_existing_effects_v0_77` の「v0.76 のコミットがない」。`git show` が失敗したときに skip する）
- 再実行: 上の 12 モジュールを PowerShell から、同じ木・同じ道具で（18:19:15〜18:23:42）。12 モジュール・303 件・失敗 0・エラー 0・skip 0
- テスト・期待値・エンジンは変えていません

### 3.3 まとめ

モジュールごとに、再実行したものは再実行の結果、ほかは 1 回目の結果で数えます（足し重ねない）。

| モジュール | 件 | 失敗 | エラー | skip |
|---:|---:|---:|---:|---:|
| 303 | 8,327 | 0 | 0 | 1 |

- skip 1: `test_cross_version_compatibility`（`KYUURA_COMPAT_BASE=4bd97bf` を設定したときだけの大きな比べ。[testing](testing.md) の任意の比べで、設定していない）
- 木の指紋は前と後で同じ（HEAD `e26df79`・750 ファイル・変更なし）

## 4. E4（状態スナップショットの限定の監査）

`python -m tools.snapshot_audit tests.<名前>` を 10 モジュールに 1 つずつ（PowerShell から。18:24:25〜18:25:01。期限 1,800 秒）。

| モジュール | 件 | restored | 保存の拒否 | 最大の深さ |
|---|---:|---:|---|---:|
| `test_legal_actions_u7_3` | 29 | 160 | — | 11 |
| `test_legal_actions_u7_4` | 27 | 104 | — | 11 |
| `test_legal_actions_u7_5ab` | 27 | 129 | — | 11 |
| `test_legal_actions_u7_5c` | 32 | 202 | effects 1 | 11 |
| `test_legal_actions_u7_5d` | 25 | 199 | — | 12 |
| `test_legal_actions_u7_5e` | 24 | 142 | — | 11 |
| `test_legal_actions_u7_5g_energy2` | 11 | 57 | — | 11 |
| `test_legal_actions_u7_5g_face_down_power` | 10 | 28 | — | 11 |
| `test_client_api` | 9 | 336 | — | 11 |
| `test_chaos_gym_borrow_t_f1` | 12 | 134 | — | 11 |

- 10 モジュールとも終了コード 0。206 件・失敗 0・エラー 0。restored でない復元 0・表せない値 0・構造の問題 0
- effects の 1 件（`$.state.effects`）は、テストで差し替えた効果の登録表の保存の拒否で、計画どおり数えるだけ
- 範囲は選んだ 10 モジュールの `_require_integrity` の位置の状態だけです

## 5. E5（配布と通常のインストール）

18:25:50〜18:27:41。PowerShell から。

- `git archive e26df79…` を展開した木で、別の仮想環境の `python -m build`。wheel `kyuura_engine-0.172.0-py3-none-any.whl`（sha256 `1b2ca854…3ba5`）・sdist `kyuura_engine-0.172.0.tar.gz`（`036982be…26a0`）
  - 展開の 1 回目は、PATH の先にあった devkitPro の tar が `C:` を遠隔の名前と読んで失敗し（展開先は空。そのビルドも中身なしで失敗）、Windows の `tar.exe` で展開し直しました。道具の呼び出しの誤りで、配布物の問題ではありません
- `scripts/check_distribution.py --wheel … --sdist …`: `required=62 problems=0`
- クリーンな仮想環境に `pip install --no-cache-dir "kyuura-engine @ git+https://github.com/moheronemy/kyuura-engine@e26df79cc6dec913c1d15b5d8203df066334d65d"`（`-e`・PYTHONPATH なし）。`pip freeze` はその 1 行だけ
- スモーク: `scripts/smoke_installed_package.py` をリポジトリの外に写し、そこを作業ディレクトリにして `<venv>\Scripts\python -I`。終了コード 0・problems なし・版 0.172.0・読み込んだ場所は venv の site-packages
- 識別: インストールしたものとソースの木の `implementation_identity` はすべての項目で同じ
  - `behavior_digest` `07a189c9bd196c489a9a59b247ff23681d78d7cd1edc666516f966ed1e3a6c18`（58 ファイル）。[legal-actions-u7-5fg.md](legal-actions-u7-5fg.md) 6.2 節の記録と同じ
  - `instrumentation_digest` `e1f397cd…43bb`（4 ファイル）
  - 規約集合 CS-KYUURA-CURRENT@1 `9a9b95c6…3cee`・CS-KYUURA-PLAY-S2A@1 `b317a3f0…10c4`・CS-KYUURA-PLAY-PO@1 `06d51219…3528`。スモークの中で固定の値と同じ

## 6. G2〜G5（GUI）

### 6.1 G2（GUI の作業場所）

| 対象 | 実行 | 結果 |
|---|---|---|
| 型の検査・ビルド | `npx tsc --noEmit -p tsconfig.json`・`npm run build` | どちらも終了コード 0 |
| vitest | 18 ファイルを 1 つずつ | 227 件・失敗 0・skip 0 |
| pytest（接続層） | 10 ファイルを 1 つずつ | 113 件・失敗 0・skip 0 |
| e2e | local-flow・card-images・u75fg を 1 ファイルずつ | 5・4・4 の 13 件・失敗 0 |

### 6.2 G3（preview）

- G2 のビルドを `KYUURA_E2E_PREVIEW=1`（`npx vite preview`）で配り、card-images・u75fg の 8 件・失敗 0

### 6.3 G4（クリーンな場所）

- `feature/engine-u7-5fg` を新しく clone して `b1037bc` に detach。新しい npm のキャッシュ・pip のキャッシュなし・空の PYTHONPATH・ssh なしで `npm run setup`（終了コード 0。変更なし）
- 接続層の仮想環境の kyuura-engine は Git の URL からの通常のインストール（`commit_id e26df79…`・0.172.0・編集可能でない・場所はクリーンな場所の `.venv` の下）
- 型の検査・ビルド 0、vitest 227 件・pytest 113 件・失敗 0、e2e 7 ファイル 27 件（local-flow 5・card-images 4・turn-basics 2・attacks 3・u75 6・u75e 3・u75fg 4）・失敗 0、preview 8 件・失敗 0

### 6.4 G5（renderer の固定）

- GUI の作業場所とクリーンな場所の両方で、package.json の依存は `github:moheronemy/kyuura-card-renderer#af88231…`、lockfile の `resolved` は `git+ssh://…/kyuura-card-renderer.git#af88231…`・version 0.1.0
- 入れた renderer の package.json・README.md は renderer のリポジトリの `af88231` の木と同じ sha256。`dist-lib/` の 75 ファイルは固定コミットの木になく（入れるときに作るもの）、2 つの場所で 75 ファイルの sha256 がすべて同じ
- renderer のリポジトリは読むだけで、変えていません

#### 6.4.1 G5 の確かめ直し（2026-11-08。読むだけ）

ファイルの読み取りと git の読み取り（`ls-tree`・`show`・`rev-parse`・`status`）だけで、前の記録と別の道具（`verifier/runs/2026-11-08-g5-recheck/tools/g5_recheck.py`）を使って確かめ直しました。インストール・サーバーの起動・テストの再実行はしていません。

| 項目 | 作業場所 `kyuura-engine-gui-wt-u75fg` | クリーンな場所 `clean/gui-b1037bc` |
|---|---|---|
| HEAD・変更 | `b1037bc…`・なし | `b1037bc…`・なし |
| `web/package.json`・`web/package-lock.json` | `b1037bc` の木と同じ sha256 | 同じ（2 つの場所で同じバイト） |
| lockfile・`node_modules/.package-lock.json` | `resolved` は `git+ssh://…/kyuura-card-renderer.git#af88231…`・0.1.0 | 同じ |
| 入れた renderer | 77 ファイル（package.json・README.md・`dist-lib/` 75・8,498,695 バイト） | 同じ。道の一覧と sha256 の違い 0 |
| フォント `@fontsource/noto-sans-jp` | 5.3.1（lockfile も 5.3.1）・2,319 ファイル | 同じ。sha256 の違い 0 |

- 生成物がコミットにないこと: renderer の `af88231` の木（109 ファイル）に `dist-lib/` のファイルはなく、`.gitignore` に `dist-lib` があります。GUI の `b1037bc` の木にも `node_modules`・`dist-lib` はありません。入れた renderer の package.json・README.md の 2 ファイルは、木の同じ道のファイルと同じ sha256 です
- 入れるときに作られること: renderer の package.json の `prepare` は `npm run build:lib`、`files` は `dist-lib` だけです。クリーンな場所の 75 ファイルの更新時刻は 18:39:27 で、G4 の準備（checkout 18:38:12・`npm run setup` の終了 18:39:28）のあいだでした。`prepare` が動いたことを直接示すログは残っておらず、時刻と package.json からの読みです
- 75 ファイルの内訳: 画像 51（png 50・jpg 1）は renderer の木の素材と同じバイトの写しで、残り 24 はビルドで作る `.js` 12・`.d.ts` 12 です。24 には CRLF・絶対パスらしい文字列・`sourceMappingURL` がありません。2 つの場所は生成の時刻が約 6 時間ちがいますが、改行・絶対パス・生成した環境による差は見つかりませんでした
- 前の記録（`G5/renderer_clean.json`・`renderer_wt_u75fg.json`）の 75 ファイルの道と sha256 は、確かめ直しと全部同じでした
- 気づいたこと（直していない）: G4 の準備は `GIT_SSH_COMMAND=fail` で成功したので、npm は GitHub の依存を ssh 以外の方法で取ったと読めますが、方法のログはありません。また、準備の出力に「skipping integrity check for git dependency」があり、Git の依存では lockfile の `integrity` は確かめられず、固定はコミットの id によります

### 6.5 接続層のプロセスの確かめ

- e2e は 1 ファイルずつ別の Playwright のプロセス。JUnit の件数がファイルの件数と同じことで、意図したテストが選ばれたことを確かめた
- 接続層（`server\.venv\Scripts\python.exe -m kyuura_gui_server --port 8766 --test-fixed-seed 21`）と Vite（`npx vite` か `npx vite preview`）は、各実行で起動した npx の子孫として記録した。仮想環境は実行した場所の `server\.venv` で、エンジンは上の Git の URL のインストール
- 待ち受けの観測の訂正: この環境の `Get-NetTCPConnection` は待ち受けを示さず、netstat の `LISTENING` は生きている待ち受けでも pid 0 と出ます。また、止めたプロセスの残りが接続を拒否する `LISTENING` として残ることも、生きている待ち受けが netstat に出ないこともありました。このため、前の段（e0-g1 の 5 章・9 章）の「待ち受けなし」は弱い根拠でした（プロセスの確かめは別で有効）。G2 の 2 ファイル目からは、8765・8766・5173・5174・4173 に直接 TCP でつなげるかで使用中を決めました。始める前と終わったあと、どのポートにもつながりませんでした
- 直す前の道具が、残りの `LISTENING` を使用中と読んで G2 の 2 ファイルを始めなかった記録があります（テストは実行していない。数えない）

### 6.6 事故（G4 の e2e の後始末）

- e2e の道具は、終わったあと「今回の子孫と記録したプロセスで、まだ生きているもの」を `taskkill /T /F` で止めていました。子孫は ParentProcessId をたどって集めていましたが、この値は親が終わっても残り、pid は再利用されます。G4 の `u75.spec.ts` と `u75e.spec.ts` の実行で、終わった古い親と同じ pid のプロセスを経て、今回の実行でない常駐のアプリ・デスクトップの部品・サービスを子孫と誤って数え、181 件を止めようとしました（`taskkill /T /F` の呼び出し 181 回）。要求した 181 件のうち今回の実行の過程は 0 件です。失敗の行は 392（Access is denied 389・critical system process 3）。成功の行は道具が標準出力を捨てたので残っていません。18:5x の確かめで 53 件がいなかった（PowerToys・シェルの部品・WebView2・svchost の一部など）が、止められたのか自分で終わったのかは区別できません（2026-11-08 に訂正: 以前は「53 件が止まりました」と書いていた。調べ直しは証跡の `verifier/incident-2026-11-08-process-kill/REPORT.md`）。取り込みの境目は、Playwright のテストの CLI の node.exe（pid 1008）を ParentProcessId に持つものとして記録された wininit.exe・csrss.exe でした
- 利用者の指示（他のアプリや他のセッションのプロセスを閉じない）に反します。テストの結果（JUnit）とは別で、上の件数は変わりませんが、その 2 件の資源の記録（最大の使用量・残り）は誤って数えたものを含むので使いません
- 原因の調べ直しと、道具の最小限の修正・模擬の検証（実際のプロセスを操作しない）は `verifier/incident-2026-11-08-process-kill/` と `verifier/tools/2026-11-08-safe-cleanup/`（リポジトリの外）。禁止の道具は禁止のまま
- 見つけたあと止める処理は実行していません。止まったプロセスを起動し直してはいません。道具は、子の作成時刻が親と実行の始まりより後の鎖だけをたどり、`taskkill` と強制の終了をなくして、後始末では自分で起動して握っている根への通常の終了の要求 1 回と、残りの記録だけにする形に直しました。直したあとの道具はレビュー前で、実際の実行はしていません（禁止の名前の 2 つは、ガードが名前を含む操作を拒否するので構文の確かめもしていない）。模擬のプロセスの一覧での試験は 20 件・12 件で、今回の実行でないプロセスへの要求 0 です

### 6.7 終わったあと

- GUI の作業場所とクリーンな場所の指紋は `b1037bc`・115 ファイルで E0 の記録と同じ・変更なし。エンジンの実行の木も変更なし
- 利用者の GUI の作業場所の未コミットの 13 件は E0 の記録と同じ（触れていない）
- 今回の python・node・Playwright のプロセスは残っていない

## 7. 証跡

- 保存先: `C:/dev/kyuura-engine-verification-u7/verifier/runs/2026-11-08-e3-g5/`（リポジトリの外。Git に入れていない）
  - `E3/`（1 回目の `summary.jsonl`・各モジュールの `.out`・`.err`・`RESULT.md`・指紋）、`E3/rerun_pwsh/`（再実行）
  - `E4/`・`E5/`（配布物・sha256・pip freeze・スモークの JSON・`RESULT.md`）
  - `G2/`・`G3/`・`G4/`・`G5/`・`AFTER/`・`G_RESULT.md`（JUnit・標準出力・標準エラー・events.jsonl・resources.jsonl）
  - `NOTES/listener_detection.md`・`NOTES/INCIDENT_g4_process_kill.md`
  - `tools/`（実行の道具。事故のときの形は `e2e_run_as_used_in_g2_g4.ps1`）
- G5 の確かめ直し: `C:/dev/kyuura-engine-verification-u7/verifier/runs/2026-11-08-g5-recheck/`（`RESULT.md`・`out/g5_recheck.json`・道具）
- 事故の調査: `verifier/incident-2026-11-08-process-kill/`（`REPORT.md`・記録の写し・分析・MANIFEST）。直した道具: `verifier/tools/2026-11-08-safe-cleanup/`
- 集計: `public/runs/2026-11-08-e3-g5/summary.md`（中身を読んで秘密を含まないと確かめた数だけ）
- 一覧: `MANIFEST.md`・`manifest.json`・`sha256.json`

## 8. 残ること

- X1〜X4 は実行していない（計画の任意の段）
- [README](../README.md) と [implementation-status](implementation-status.md) の U7 の総合検証の行は「計画だけ」のまま（この作業では変えていない）
- 双子の点検の不足（e0-g1 の 9.2 節）の広い直しは保留のまま
