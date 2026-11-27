# ER9 の規約採用の前後を比べるバッチの計画（TR3@1 と TR4@1。0.195.0）

- **日付:** 2026-11-21。**基点:** `claude/er9-zero-choice-v0195` の `5aa8659`。作業ブランチ `claude/er9-tr4-compare-plan`。
- **2026-11-21 の追記:** この計画で実行した（6 章）。12 局すべて完了し、MATCHED 3・NO_TARGET 3。
- **状態:** 計画と機械可読の下書きだけです（[er9-tr4-compare-batch-plan.json](er9-tr4-compare-batch-plan.json)）。確定計画の生成・キャッシュの準備・対戦の実行は次の単位です。
- **問い:** エンジン 0.195.0 で、`new_game` から始めた対戦のエネルギー回収の 0 枚の答えが、**TR3@1 では ER9 で拒否され、TR4@1 では受理されて対戦が続くか**。
- **関連:** [ER9 の設計](er9-energy-retrieval-zero-design.md)・[v0.195 の実装](play-convention-tr4-v0.195.md)・[TR3 の未裁定の監査のバッチ](tr3-unresolved-batch-plan.md)（C2 の保存結果）。
- **証跡:** `kyuura-engine-verification-vai/verifier/runs/er9-tr4-compare-plan/`。

## 1. 基点と実行するコード

| 項目 | 値 |
|---|---|
| 基点 | `5aa8659bf08b55c86abd79fd74a88a44d818bba6`（origin と一致。この値を含む公開ブランチは `claude/er9-zero-choice-v0195` だけ） |
| 配布の固定（実行するコード） | `fafbb83a4cb6979b7801c10a493d05ae3b43e763`（0.195.0）。`fafbb83..5aa8659` の差は文書 5 ファイルだけで、`kyuura_engine`・`tools`・`tests`・`scripts`・`pyproject.toml` の差は 0 |
| C2 の実行（参考） | `891e1fb`（0.194.0）。`891e1fb..fafbb83` の実行するコードの差は `kyuura_engine/__init__.py`・`conventions.py`・`effects.py`・`pyproject.toml` だけ。道具（`tools`）の差は 0 |

**実測した識別**（`5aa8659` の作業ツリーのソース。証跡の `out/identity_5aa8659.json`・`out/sets_and_formats.json`）

| 項目 | 値 |
|---|---|
| エンジン | 0.195.0・behavior `5cbd40af…`・instrumentation `13c773a8…` |
| 道具 | `TOOL_VERSION` 13・`be95aa1e…`（27 ファイル）。C2 と同じ |
| 判定の規則・形式 | 規則 10・`RECORDED_STOP_CONDITIONS` は ER9 だけ。計画 `kyuura-vai-batch-plan/7`・完了 `kyuura-vai-batch-complete/7` |
| basis | P1 `e1d389e7…`・P3 `89d12d2e…`・P2 `d652db24…`・規則 10 `6d41f57f…`（0.194.0 の C2 とは違う） |
| TR3@1 | 23 規約・`sha256:a7b800cf…`（固定値 = 計算値・構成の問題 0） |
| TR4@1 | 24 規約・`sha256:15af975a…`（固定値 = 計算値・構成の問題 0）。**TR3@1 の 23 規約の並びのあとに `PC-ENERGY-RETRIEVAL-ZERO@1` を 1 件加えたもの**（差は 1 件だけ。TR3 にあって TR4 にない規約は 0） |

## 2. 比較の条件

- 両側とも同じ固定コミットの 0.195.0。違いは計画の規約集合（`--conventions`）だけです。
- C2 と同じ: 固定デッキ v2 の組（プレイヤー 0 が `hitmonchan-dewgong-v2`、プレイヤー 1 が `venusaur-parasect-v2`。内容と並びの sha256 も C2 と同じことを確定の時に照らす）、方式 `rules-v2`（rules・版 2・反復の閾値 2）・プロファイル `deep`・分布 `uniform-candidate+uniform-stage`、単局の上限（操作 2,000・受理 1,000・番 200・120 秒・同じ局面の拒否 16・選び直し 64）、観測と prestop の記録を有効、変異なし、逐次。
- ゲーム・方策・ホストの seed は同じ値（C2 と同じ）。
- **seed: C2 で使った 9007〜9012 の 6 値を意図して再使用します。** 0.194.0 で ER9 が出た 3 値（9007・9008・9011）を含む全 6 値を固定し、ER9 が出なくても条件・局数を変えません。0.194.0 の結果は条件の選定と予算の見積もりにだけ使い、規約の効果は 0.195.0 どうしで比べます。

### 2.1 2 つの計画と実行の順

| 計画 | 規約集合 | 局 | 上限 |
|---|---|---|---|
| `vai-batch-er9c-tr3` | `CS-KYUURA-PLAY-TR3@1` | 6（g001〜g006 = seed 9007〜9012） | 900 秒・1,024 MiB・最大 6 局 |
| `vai-batch-er9c-tr4` | `CS-KYUURA-PLAY-TR4@1` | 6（同じ） | 同じ |

計画を作るコマンドは下書きの `plans.*.plan_command` です（C2 の引数のうち、規約集合・計画名・コミットだけが違う）。局の ID（`g001-rules-v2-s9007` など）と `run_id` は両側で同じなので、`operation_id` も同じ形になります。

**実行の順（12 局。seed ごとに TR3 → TR4）**

| 呼び出し | 組 | seed | 側 | 0.194.0 の C2 での ER9（参考） |
|---|---|---|---|---|
| 1・2 | 1 | 9007 | TR3 → TR4 | 試み 94 |
| 3・4 | 2 | 9008 | TR3 → TR4 | 試み 153 |
| 5・6 | 3 | 9009 | TR3 → TR4 | なし |
| 7・8 | 4 | 9010 | TR3 → TR4 | なし |
| 9・10 | 5 | 9011 | TR3 → TR4 | 試み 38 |
| 11・12 | 6 | 9012 | TR3 → TR4 | なし |

TR4 の局のあとに、その組の比較（`pair_compare`）をします。

## 3. 何を比べるか

### 3.1 操作の対応づけと最初の分岐

- 主: 2 局の `trace.jsonl` の試みの行を、道具の既存の `records.action_sequence`（`action-meaning/v2`。取っ手・番号・評価の値を除く）で先頭から比べ、最初に違う行（`records.compare_meanings`）を**最初の分岐**とします。
- 同じ行で、`records.contract_sequence`（API の契約の値）、`full_record.json` の operations（seq・operation_id・command・outcome・status・diagnostic）、`observe/rows.jsonl`（結果・更新の数・観測の照合値）、`judge.json` の rows を並べます。
- 参考: 0.195.0 の TR3 の局の action・contract の指紋を、C2 の `sequences.json` と比べます（エンジンの識別が違うので合格条件ではない）。

**いつも違う項目（比べる前に除く。事前に列挙）:** 計画名・`plan.json`・`plan.sha256`・台帳・LOCK・session、局の規約集合（鍵・照合値）と `comparison_group`、完全な記録と観測の header の集合の識別、時刻・経過秒・メモリ、ファイルの sha256・`files.sha256.json`・`COMPLETE.json` の値。ランダムな取っ手（game・revision・候補と選ぶものの番号）は `action_sequence` がもとから除きます。

**最初の分岐の前に同じはずの項目:** 主体・候補の種類と中身（評価の値を除く）・入力・check・結果・断り・診断、`operation_id`。

**生の差として保存するもの:** 最初の分岐の行の両側（action と contract）と前後 3 行、full_record の operations の最初の不一致の行、両側の action の行の列（records.canonical の JSON で 1 行ずつ。jsonl）。

### 3.2 同じ状況の 0 枚の答え（対応した 0 枚の答え）

最初の分岐の行で、両側の試みが次をすべて満たすときに「対応した」とします。

1. 主体が同じ
2. 候補が `answer_decision`、段が 1 つで `decision_kind` が `retrieve_energy`、数が最小 0・最大 1 以上
3. 選べるもの（カードの uid と ID）が同じ
4. 入力が空（meaning・choices が空）で、check が有効
5. 経路: 送信前の本人の観測で、使用中のカードがエネルギー回収（PMCG1-076 か再録の版）、この使用の `play_trainer` に `via`・`source_zone` がなく、そのあとの出来事が `discard_from_hand` だけ（`chaos_check`・`chaos_answered`・`trainer_reaction_answered`・`stadium_card` がない）
6. 費用: その `discard_from_hand` のカードが同じ
7. 決定: 決定の番号と、決定の情報の `discarded` が同じ

規約の対象は手札から通常に使ったエネルギー回収です。5 を満たさない ER9（錯乱ジム・サイキックコントロール・［ちえくらべ］を聞いた使用）は、両側とも ER9 のはずなので、**対象外の経路として別に数えます**（対応した 0 枚に入れない）。

### 3.3 期待と、それを確かめる記録

| 側 | 期待 |
|---|---|
| TR3 | submit が rejected・`UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE`（`unresolved_ruling`）・status `awaiting_decision`・次は同じ主体の `answer_decision`（決定待ちのまま）。どの見る人も更新 0。そのあと同じ決定に答え直す。judge は `known_stop`（規則 6 の根拠 ER9） |
| TR4 | submit が accepted・status `in_progress`・次が番の操作（決定が閉じる）。全員の公開ログに `convention_applied`（`PC-ENERGY-RETRIEVAL-ZERO`・版 1・`player`・`available`）と `discard_trainer` が 1 つずつで、`retrieve_energy` はない。本人の観測で、手札が同じ・費用のカードがトラッシュのまま・エネルギー回収が持ち主のトラッシュへ・選べたエネルギーがトラッシュのまま。番のプレイヤー・番の番号が同じで段階は main。judge は `expected` |

**比較の項目と証拠の対応**

| 項目 | 記録 |
|---|---|
| 0 枚の送信と結果 | `trace.jsonl` の試み（candidate・stages・meaning・choices・check・submit・verifier）、`full_record.json` の operations |
| 拒否で状態・観測が変わらない（TR3） | `observe/rows.jsonl`（updates・見る人ごとの前後の照合値とログの長さ）、full_record の check |
| 経路・費用・選べるもの | `observe/view-<主体>.json` の送信前の本人の観測（使用中のカード・ログの `play_trainer`・`discard_from_hand`・決定の選べるもの）、trace の stages |
| 受理のあとのカードの移動（TR4） | `observe/view-<主体>.json` の送信の前と後（手札・トラッシュ）、既存の replay の照合（最終の状態） |
| 公開ログの出来事（TR4） | `observe/view-0.json`・`view-1.json`・`view-spectator.json` の受理の後のログ、`observe/rows.jsonl` の updates |
| 決定が閉じ同じ番へ（TR4） | submit の result（status・next）、受理の後の観測（決定なし・番・番のプレイヤー・段階） |
| judge | `judge.json` の rows（TR3 `known_stop`・TR4 `expected`）、`batch.judge_trace` の当て直し（記録を書かない） |
| その後の進行 | `result.json`（終わり方・counters）、`COMPLETE.json` の要約、終わりの観測（勝敗） |

### 3.4 組の分類

| 分類 | 意味 |
|---|---|
| MATCHED | 最初の分岐が、対応した 0 枚の答えの行 |
| DIVERGED_BEFORE | 対応した 0 枚の答えより前に分岐した（生の差で原因を調べる。規約の直接効果に数えない） |
| NO_TARGET | 両側とも最後まで分岐せず、対応した 0 枚の答えがない（同じ対戦） |
| OTHER_DIVERGENCE | 分岐したが、分岐の行が対象の 0 枚の答えではない（対象外の経路の ER9 を含む） |
| INCOMPLETE | 片側が未着手・未完了（照合に通らない attempt を含む） |

- 分岐のあとの操作・勝敗・完走は、各局の結果として記録します。規約の直接の効果は、対応づけた 0 枚の答えだけで評価します。分岐のあとの ER9 は対応づけず、局ごとの件数として数えます。
- **主な報告の指標:** 対応した 0 枚の答えの数、ER9 の拒否（TR3・TR4、対象の経路・対象外の経路）、TR3 の答え直しの受理、TR4 の規約による受理、受理のあとの進行（局ごとの終わり方・番・受理の数・勝敗・時間）、組の分類の件数。

## 4. 予算と関門

### 4.1 C2 の実測（0.194.0。見積もりだけ）

| seed | 終わり方 | 番 | 受理 | ER9 | 完了の大きさ | 外側の秒（実行＋照合） |
|---|---|---|---|---|---|---|
| 9007 | game_over | 40 | 253 | 1 | 19.3 MB | 33.5 |
| 9008 | game_over | 45 | 194 | 1 | 16.5 MB | 32.6 |
| 9009 | game_over | 6 | 23 | 0 | 1.2 MB | 22.8 |
| 9010 | game_over | 28 | 100 | 0 | 6.6 MB | 25.4 |
| 9011 | game_over | 9 | 50 | 1 | 2.9 MB | 23.7 |
| 9012 | game_over | 8 | 32 | 0 | 1.6 MB | 23.8 |

計画全体: 道具の時間 36.05 秒（6 局）、計画のディレクトリ 48,079,827 バイト。TR4 の局は 0 枚の受理のあと進行が変わるので、この値は上限ではありません。

### 4.2 確定値

| 項目 | 値 |
|---|---|
| 計画ごと | 道具の時間 900 秒・証跡 1,024 MiB（予約 64 MiB）・最大 6 局・局の予約 150 秒 |
| 全体（2 計画） | 道具の時間 1,800 秒・外側の実時間 3,600 秒・証跡 1,024 MiB |
| 次の局を始める条件（すべて） | 計画の残り時間 ≥ 150 秒・全体の道具の残り ≥ 150 秒・全体の外側の残り ≥ 600 秒・計画の残りの証跡 ≥ 必要量・全体の残りの証跡 ≥ 必要量・ドライブの空き ≥ 4,096 MiB |
| 必要量 | max(384 MiB, 2 計画で保存済みの最大の完了 1 局 × 1.5)。開始の時点は 384 MiB（C2 の最大 19.3 MB × 1.5 より大きい） |
| 見積もり | 道具 約 72 秒・外側 約 560 秒（照合と組の比較を含む）・証跡 約 100 MiB |

### 4.3 開始の前の関門

1. 2 計画を固定の CLI 引数で作り、どちらの局も始める前に、両方の `plan.sha256` の全値を記録する（確定計画の固定）。
2. 計画の照合: 版 0.195.0、engine/tool の commit が `fafbb83…`、behavior `5cbd40af…`・道具 `be95aa1e…`・形式 plan/7、集合の鍵と照合値（TR3 `a7b800cf…`・TR4 `15af975a…`）、seed 6 値、デッキの内容と並びの sha256 が C2 と同じ、局の config が規約集合のほかは C2 と同じ、2 計画の局の config が規約集合のほかは同じ。
3. 0.195.0 用の checked-hash pyc キャッシュ（`C:\dev\kyuura-engine-pyc-cache\b5cbd40a-tbe95aa1-cpython-314-fafbb83-er9c`）を作り、全ハッシュを記録して照らす。
4. dry-run（2 計画）で、キャッシュを使うことと容量を確かめる。全体の予算の最初の確かめをする。
5. seed の使用の走査で、9007〜9012 が C2 の 4 計画で使われていることを記録する（意図した再使用）。

### 4.4 1 局ごとの手順

既存の CLI で 1 局ずつ実行します（C2 の外側の手順 `one_game_main.ps1` と同じ並び）。

1. 開始の前の確かめ: 計画の sha256 が固定値・この局が未着手・前の局が完了して照合済み
2. 全体の予算（4.2 の条件。足りなければ残りを未着手で正常に終える）
3. キャッシュの照合（前）
4. `run_seq --sessions 1`（`batch run --stop-after-games 1`）
5. 終わり方の区別: `session_limit`、または `completed` でこの局をちょうど 1 局、完了・停止なしで走らせたときだけ照合へ
6. `check_game`: 完了マーカー・必須ファイル・ハッシュ・停止の理由の計算し直し・prestop の要約と照合式・終わり方・判定・既存の replay の照合・観測・prestop の件数
7. ER9 の送信の列挙と経路
8. TR4 の局のあとだけ、組の比較（3 章。分類・期待の確かめ・生の差の保存）
9. キャッシュの照合（後）、外側の台帳に開始・終わり・秒

12 局のあと: 各計画の aggregate を 1 回（同じキャッシュ）、最後の整合の確かめ、キャッシュの最後の照合、prestop の分析、6 組の集計。

### 4.5 停止の条件

- **残りを未着手にして終える:** 計画・キャッシュ・識別の照合の不一致、batch run の異常な終わり（停止の方針の stop・未完了・failed・exception など）、照合・分析・組の比較の道具の失敗・記録の欠け・ハッシュの不一致・観測や prestop の問題・replay の照合の失敗、判定の `suspect`・止める `undetermined`、予算・空き容量の不足。
- **別の判断でしかしないこと:** 自動の再試行（2 回目の attempt）、停止の解除（`--acknowledge-stop`・unlock）、局・seed の追加や差し替え、予算の延長。
- **合格条件にしないこと:** ER9 が出ること、0 枚の答えが対応すること、完走の割合が上がること。

## 5. 比べられる範囲と、足りない証拠

- 比べられる: 対応した 0 枚の答えの、TR3 の拒否と TR4 の受理（結果・観測・公開ログ・カードの移動・判定）、組ごとの最初の分岐の位置、各局の終わり方と進行。
- 足りない証拠:
  - エンジンの内部状態の照合値は送信ごとには記録されません（受理は full_record の check、拒否の直後は観測の照合値で代えます）。
  - replay の照合は最終の状態だけです（途中の操作ごとの状態は観測で代えます）。
  - 本人以外の秘密の値は、本人の観測でしか確かめられません。
  - 0.194.0 の C2 と 0.195.0 の TR3 の一致は参考です（エンジンの識別が違う）。
  - 0 枚の答えは方策の無作為な枚数の選択で出るので、0.195.0 で対応する答えが出るかは実行するまで分かりません（出なくても条件は変えない）。

## 6. 実行の結果（2026-11-21）

- **実行:** 作業ブランチ `claude/vai-batch-er9c`（作業ツリー `C:\dev\kyuura-engine-lt81`）。実行のあいだは固定 `fafbb83…` に切り離して、確定計画・キャッシュ・12 局を走らせた。
  証跡は `kyuura-engine-verification-vai/verifier/runs/vai-batch-er9c-run/`（作業記録）と、2 つの計画のフォルダ `vai-batch-er9c-tr3`・`vai-batch-er9c-tr4`。
- **確定計画:** 既存 CLI で 2 計画を作り、初局の前に全文と `plan.sha256` を保存した（TR3 `40509931…`・TR4 `3429a092…`）。
  C2 の計画と、規約集合（と比較の組の名前・デッキの適否を判定したエンジンの識別）のほかは同じで、2 計画どうしも各局が規約集合のほかは同じ（照合の問題 0）。
- **識別:** 0.195.0・behavior `5cbd40af…`・instrumentation `13c773a8…`・道具 `be95aa1e…`（版 13）・判定の規則 10・計画と完了の形式 7・basis（P1 `e1d389e7…`・P3 `89d12d2e…`・
  P2 `d652db24…`・規則 10 `6d41f57f…`）。計画の時点の実測と同じ。TR3@1 23 規約・TR4@1 24 規約、固定値 = 計算値、差は `PC-ENERGY-RETRIEVAL-ZERO@1` の 1 件。
- **キャッシュ:** `b5cbd40a-tbe95aa1-cpython-314-fafbb83-er9c`（185 pyc）。dry-run 2 回でキャッシュの利用と未着手を確かめ、12 局の前後と最後で全ハッシュが同じだった。

### 6.1 局と組

予定 12・着手 12・完了 12・未完了 0・未着手 0（打ち切りなし）。12 局とも `game_over`、照合（完了の記録・ハッシュ・完全記録との対応・観測・prestop・判定・最終状態の replay・キャッシュ）がすべて成立した。

| 組 | seed | 分類 | 分岐の試み | TR3 の 0 枚の答え | TR4 の 0 枚の答え | 期待の照合 | TR3 の局 | TR4 の局 |
|---|---|---|---|---|---|---|---|---|
| 1 | 9007 | MATCHED | 94 | ER9 で拒否 → 2 枚で答え直して受理 | 受理（規約） | すべて真 | game_over・40 番・受理 253 | game_over・34 番・受理 228 |
| 2 | 9008 | MATCHED | 153 | ER9 で拒否 → 2 枚で答え直して受理 | 受理（規約） | すべて真 | game_over・45 番・受理 194 | game_over・49 番・受理 360 |
| 3 | 9009 | NO_TARGET | — | — | — | — | game_over・6 番・受理 23 | game_over・6 番・受理 23 |
| 4 | 9010 | NO_TARGET | — | — | — | — | game_over・28 番・受理 100 | game_over・28 番・受理 100 |
| 5 | 9011 | MATCHED | 38 | ER9 で拒否 → 2 枚で答え直して受理 | 受理（規約） | すべて真 | game_over・9 番・受理 50 | game_over・9 番・受理 50 |
| 6 | 9012 | NO_TARGET | — | — | — | — | game_over・8 番・受理 32 | game_over・8 番・受理 32 |

- **5 分類:** MATCHED 3・DIVERGED_BEFORE 0・NO_TARGET 3・OTHER_DIVERGENCE 0・INCOMPLETE 0。
- **ER9 から受理への変化を直接確かめた組: 3 組**（MATCHED の 3 組すべて）。3 組とも、最初の分岐は対応した 0 枚の答えの行（同じ試みの番号・同じ `operation_id`）で、
  その前の action・contract の列と完全記録の操作は同じだった。7 条件（主体・決定・選べるもの・空の答えと check・通常の手札使用・費用・決定の情報）はすべて一致した。
- **TR3:** 3 件とも ER9（`unresolved_ruling`）で拒否、status `awaiting_decision`・次は同じ主体の答え、どの見る人も観測の照合値とログの長さが同じで更新 0、judge は `known_stop`（規則 6 の根拠 ER9）。
  3 件とも同じ決定に 2 枚で答え直して受理された。
- **TR4:** 3 件とも受理、status `in_progress`・決定なし・使用中のカードなし・同じ番の番のプレイヤーで段階 main。全員の公開ログに `convention_applied`（`PC-ENERGY-RETRIEVAL-ZERO`・版 1・
  場面とコード ER9・使用者・選べた枚数）と `discard_trainer` が 1 つずつで、`retrieve_energy` はない。本人の観測で手札は同じ、費用のカードと選べたエネルギーはトラッシュのまま、
  エネルギー回収は持ち主のトラッシュへ（トラッシュに加わったのはこのカードだけ）。judge は `expected`。
- **件数:** ER9 の拒否は TR3 3（対象の経路）・TR4 0。対象外の経路（錯乱ジム・サイキックコントロール・［ちえくらべ］）の 0 枚の答えは両側とも 0。
  TR3 の答え直しの受理 3。TR4 の規約による受理 4（対応した 3 と、分岐のあとの 1。組 2 の TR4 の局の後半）。TR3 の局にこの規約の記録はない。
  ほかの規約の記録は、組 6 の両側の切り直しの規約（`PC-SETUP-MULLIGAN-COUNT`）1 つずつ。
- **NO_TARGET の 3 組:** 0 枚の答えが出ず、両側の操作の列・完全記録が最後まで同じ（同じ対戦）だった。
- **参考:** 0.195.0 の TR3 の 6 局の action・contract の指紋は、C2（0.194.0）の 6 局とすべて同じだった（エンジンの識別は違う）。分岐のあとの展開と勝敗は参考の結果で、
  組 1・組 2 は TR4 の番・受理の数が TR3 と違った（勝者は同じ）。組 5（seed 9011）は 0 枚の受理のあとも番・受理の数が同じだった。
- **判定の当て直し:** 12 局とも、`batch.judge_trace` の当て直しが保存した judge の行・終わり方と同じ（記録は書いていない）。計画の集計は TR3 `expected` 652・`known_stop` 3、TR4 `expected` 793。
  undetermined・suspect は 0。replay は 12 局とも `succeeded`（期待どおり）。

### 6.2 時間・容量

| 項目 | TR3 | TR4 | 全体（上限） |
|---|---|---|---|
| 道具の時間（計画の台帳） | 27.235 秒 | 32.174 秒 | 59.409 秒（1,800） |
| 局の時間の和 | 13.258 秒 | 17.48 秒 | — |
| 外側の実時間（実行＋照合＋比較） | 113.352 秒 | 190.544 秒 | 303.896 秒（3,600） |
| 完了した局の証跡 | 48.0 MB | 63.3 MB | 計画のフォルダの和 111.4 MB（1,024 MiB） |

毎局の前の予算の確かめは 12 回とも条件を満たした（最大の完了 1 局 33.7 MB × 1.5 は 384 MiB より小さく、必要量は 384 MiB のまま）。

### 6.3 確かめられた範囲と、足りない証拠

- 受理・拒否の結果、観測（見る人ごとの照合値・ログの長さ・更新）、公開ログの出来事、本人の手札とトラッシュ、判定は記録で確かめた。
- エンジンの内部状態の照合値は送信ごとには記録がない。拒否で状態が変わらないことは観測（全員の照合値とログの長さ・更新 0）と完全記録の確認値で、受理のあとの状態は本人の観測で確かめた。
  replay の照合は最終の状態だけ。
- 本人以外の秘密の値（相手の手札など）は確かめていない。
- 選んだ 6 つの seed から、一般の ER9 の発生率や完走の割合の改善は推定しない。
- 失敗・修正・再実行は作業記録（`commands.txt`）に残した（製品のコード・計画・記録は変えていない）。
