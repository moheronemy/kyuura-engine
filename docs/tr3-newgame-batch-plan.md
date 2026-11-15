# TR3 を明示した new_game の小規模確認バッチの計画（計画だけ）

2026-11-16。計画と文書化だけです。確定計画（`plan.json`・`plan.sha256`）・キャッシュの準備・対戦の実行・テスト・ビルド・seed 探索・judge・replay はしていません。エンジン・検証用 AI・GUI・方策・規約は変えていません。

- 基点: `claude/status-ledger-v0187` の `915132a`（origin と一致。main `b1e4430` の子孫で main に入っていない）。`kyuura_engine`・`tools`・`tests`・`scripts`・`pyproject.toml` は配布の固定 `d562ec16e3f493569ed0251cbcf9062ceccdbb1a` と差 0。作業は worktree `C:\dev\kyuura-engine-lt46`・ブランチ `claude/tr3-newgame-batch-plan`。
- 識別（読み取りで測った値。実行のときに測り直す）: エンジン 0.187.0・behavior `ae974fff…`・instrumentation `13c773a8…`・`TOOL_VERSION` 11・道具 `6e0616cc…`・判定の規則 8・計画と完了の形式 7・P1 `2ed8732f…`・P3 `9499db41…`。0.187.0 の記録（[v0.187](token-sync-v0.187.md) 5 章）と同じ。
- 機械可読の下書き: [tr3-newgame-batch-plan.json](tr3-newgame-batch-plan.json)（`status: draft`。確定計画ではない）。
- 状態台帳での位置: [現在の完了・未完了一覧](project-status-ledger-v0187.md) の L-TR3 の限界（new_game での到達・完走）を確かめる単位です。TR3 の実装・GUI の追従の完了はそのままです。
- 証跡: `kyuura-engine-verification-vai/verifier/runs/tr3-newgame-batch-plan/`（事前計画・識別・デッキの検査・seed の調べ）。

**目的**: 構築盤面で確かめた実装を再証明することではありません。通常の対戦で `CS-KYUURA-PLAY-TR3@1` を選び、規約による使用不可の選択肢を避けながら局が進むかを確かめます。

## 0. 推奨案（要約）

| 項目 | 値 |
|---|---|
| 計画 | 1 つ: `vai-batch-tr3n1` |
| デッキ（両側） | 明示リスト L67-U（`vai-batch-d/decklists/decklist-L67-U.json`。sha256 `097b7db9621cc28e…`・content `72690ceea389…`・展開 `5fb91539…`。x1 と同じ） |
| 方式 | `rules-v2`・`boundary` |
| 規約集合 | `CS-KYUURA-PLAY-TR3@1`（`--conventions` で明示。照合値 `sha256:a7b800cf…`・用途 development・23 規約） |
| seed と並び | 9002 → 9003。seed ごとに rules-v2 → boundary |
| 局 | 4（g001 rules-v2・9002、g002 boundary・9002、g003 rules-v2・9003、g004 boundary・9003） |
| 単局の上限 | 既定（`runner.Limits`: 操作 2000・受理 1000・番 200・120 秒） |
| バッチの上限 | `--max-games 4`・`--budget-seconds 300`・`--evidence-max-mb 512`（次の局を始める条件の 150 秒・64 MiB は既定） |
| 記録 | `--observation`・`--prestop-inputs`（上限は既定の 256 要求・16,384 バイト・1 MiB） |
| 停止方針 | 既定（`--undetermined-evidence-missing continue` は x1 と同じ） |
| 変異 | なし。単一のプロセス・逐次。1 局ごとに止めて確かめる |

- 初期案のとおりです。別の条件は要りません（理由は 1 章）。
- 入れないもの: CURRENT との比べの対戦、規約の有効・無効を比べる対戦、出現を増やすデッキの改造、未出現のときの追加の局。

## 1. 条件の根拠

| 確かめたこと | 結果 |
|---|---|
| L67-U に 3 枚があるか | 突風 2・きずぐすり 2・ポケモンいれかえ 2（60 枚・14 種類） |
| 0.187.0 での合法性 | `batch decklist --file` → `legality.ok` 真・problems 空（`kyuura_engine.deck.deck_problems`・JP-2000.02.14・engine 0.187.0 `ae974fff…`）。content と展開の sha256 は x1 と同じ |
| 既存の時間・量（x1。0.185.0・観測と prestop あり・同じデッキと方式） | 局の時間 0.33〜9.24 秒、道具の累積時間 36.187 秒（予算 300）。ゲームの証跡 47,182,086 バイト（4 局・76 ファイル）。うち prestop 88,804 バイト・観測 26,984,953 バイト |
| x1 で 3 枚が出たか | 出た（候補全体が未裁定の選択肢の延べ 突風 81・きずぐすり 44・ポケモンいれかえ 2。[x1 の結果](prestop-first-batch-plan.md) 9.4 節） |
| TR3 の集合を計画に書けるか | `batch plan --conventions <ID@版>` は登録した集合を `resolve_for_new_game` で解決し、局ごとに `conventions.key`・`digest` を計画に書く。前例: w2 の `CS-KYUURA-PLAY-S2A@1` |

- L67-U どうし・rules-v2 と boundary は、x1 で 3 枚が出た条件で、局が短く証跡も小さい条件です。予算 300 秒・512 MiB は x1 の実測の約 8 倍・約 10 倍の余裕です（見込みで、保証ではありません）。
- TR3 は、3 条件を「未裁定（範囲の外）」から「規約による使用不可（範囲の外）」に変えるだけで、範囲の中の候補は CURRENT と同じ見込みです。局の長さが大きく変わる理由は見当たりません。ただし同じ seed でなくても、進行・出現は保証しません。
- x1 の seed（6001・9001）は使いません。今回の対象は TR3 の集合での進行で、x1 との局ごとの比べ（CURRENT との比べ）は入れないためです。

### 1.1 seed

- 保存済みの計画と記録のヘッダー（`plan.json`・`header.json` だけ）を、証跡のストア 24 か所（`kyuura-engine-verification-vai`・`kyuura-engine-verification`・GUI と旧版の検証のストア 22）から読みました。ファイル 336・読めないもの 0・使われた値 95 種類。
- 9000〜9100 で使われていたのは 9001（x1）だけで、使われた最大の値も 9001 でした。
- 規則「9002 から上へ、連続 2 値がどちらも未使用の最初の組」で **9002・9003** にしました。対戦で試して選んでいません。
- 限界: 調べたのは上の 24 か所の 2 種類のファイルだけです（GUI の固定例の seed・テストの中の seed は別の用途で、調べていません）。

## 2. 既存の手段の適合（読み取り）

| 要件 | 既存の手段 | 状況 |
|---|---|---|
| new_game から始める | `batch run`（runner が `new_game` から各局を始める） | そのまま使える |
| TR3 の明示 | `batch plan --conventions CS-KYUURA-PLAY-TR3@1` | そのまま使える。計画の各局の `conventions`、記録の `header.json`・`full_record.json` の `convention_set`（id・照合値・規約の並び）に残る |
| 観測と prestop | `--observation`・`--prestop-inputs` | そのまま使える（x1 と同じ） |
| 規約で `eligible: false` の選択肢を選ばない | 候補: 処理可能性が範囲の外なら外す（`runner` の `pick`）。選択肢: `actions.option_allowed` が `eligible` 偽を外す | そのまま使える。TR3 で手札のトレーナーがどれも使えないと、候補 `play_trainer` が `not_implemented`・理由 `no_eligible_card` になり、範囲から外れる（`processability:not_implemented` として数えられる） |
| 契約の検査で止まらない | 段の鍵は `STAGE_KEYS` で照らすが、選択肢の鍵は照らさない（`convention` は契約の外にならない）。`not_implemented` は既知の処理可能性 | 止まらない作りだが、**検証用 AI のテストに TR3 の局はない**（6 章の 1 局目の確かめで見る） |
| 1 局ごとの確かめ | x1 の外側のスクリプト `run_seq_pyc_x1.py --sessions 1`（`vai-batch-x1-run/scripts/`）と `check_game.py`（`batch.verify_complete`・`prestop.reconcile`） | そのまま使える（写して使う） |
| checked-hash pyc キャッシュ | `prepare_pyc_cache_x1.py`（`ENTRY_MODULES` に prestop をふくむ写し）・`cache_same.py` | そのまま使える。キャッシュは新しく作る（識別とコミットが x1 と違う） |
| 計画の照合 | `check_plan_x1.py` は x1 の期待値（規約集合 CURRENT・seed）を持つ | **証跡の側の写しの期待値だけ変える**（規約集合 TR3 と照合値・seed 9002・9003・batch の名前）。エンジン・道具は変えない |
| 実行後の集計 | `analyze_prestop.py`（そのまま）と、新しい読み取りだけの `analyze_tr3.py`（4 章。実行の単位で作る） | 既存のスクリプトは直さない |

**prestop の記録と規約による使用不可は別のものです。**

- prestop が記録するのは、候補全体が `unresolved_ruling` で範囲の外になった候補の inputs です。TR3 で 3 条件にあたる候補は `not_implemented`（`no_eligible_card`）になるので、prestop には入りません。TR3 の局の prestop は、ほかの未裁定の候補だけを記録します。
- 規約による使用不可は、既存の記録から次の 2 つの形で見えます。
  - **直接**: 選ばれた候補の inputs の応答（`actors/<主体>.jsonl` の試みの行の `inputs.response.stages[].options[]`）にある、`eligible` 偽で `convention` に規約 ID のある選択肢。手札のほかのトレーナーが使えるときに出ます。
  - **間接**: 候補の応答（同じ行の `candidates.response.candidates[]`）で `play_trainer` が `not_implemented`・`no_eligible_card` の局面。どのカード・どの規約かは記録にありません。本人の観測（`observe/rows.jsonl` の同じ `(episode, position)` の本人の見え方）の手札と場から、3 条件のどれが成り立つかを評価できます（[観測の対応づけ](prestop-observation-link-design.md) と同じ結び方）。これは規約の適用の直接の記録ではなく、条件の評価です。
- `no_eligible_card` は TR3 だけの理由ではありません（規約のない使えない理由でも出ます）。間接の評価で 3 条件のどれも成り立たない局面は「規約以外の理由」とします。

**最小の修正（今回は実装しない・推奨しない）**: 候補全体が規約で使用不可の局面でも規約 ID を直接記録したいなら、prestop の対象に「`play_trainer` で `not_implemented`・`no_eligible_card`」を足す変更が最小です（記録の取得だけで方策に渡さない作りは同じ）。道具の識別・`TOOL_VERSION`・計画と完了の形式が変わり、限定テストと固定の指紋の確かめが要ります。今回の目的（進行の確認）には、直接の形と間接の評価で足りるので、修正なしで実行することを推奨します。

## 3. 実行の手順（次の単位。ここでは実行しない）

1. 新しい worktree と作業ブランチ（この計画のコミットから）。`kyuura_engine`・`tools`・`tests` が `d562ec1` と差 0、無視をふくめ変更 0、識別が上の値と同じことを確かめる。実行コミット＝その worktree の HEAD（完全なハッシュ）
2. `batch decklist --file <L67-U>` で 60 枚・problems 空・content と展開の sha256
3. `python -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr3n1 --engine-commit <HEAD> --tool-commit <HEAD> --seeds 9002 9003 --modes rules-v2 boundary --decklist0 <L67-U> --decklist1 <L67-U> --conventions CS-KYUURA-PLAY-TR3@1 --max-games 4 --budget-seconds 300 --evidence-max-mb 512 --observation --prestop-inputs --undetermined-evidence-missing continue`
4. 計画の照合（`check_plan` の写し）: 4 局の並び・方式・seed・デッキの記録（`deck_problems` 空）・各局の `conventions` が `CS-KYUURA-PLAY-TR3@1` と照合値 `sha256:a7b800cf…`・`observation`・`prestop_inputs`・上限・識別。`plan.sha256` を記録
5. S-1: 新しいキャッシュ `C:\dev\kyuura-engine-pyc-cache\bae974ff-t6e0616c-cpython-314-<HEAD 7 桁>-tr3n1`（新しい空の場所）を、その worktree・同じ Python で準備。準備の時間・容量はバッチ本体と分ける
6. `run_seq_pyc_x1.py --dry-run` で `use_cache` 真・容量の確認・`batch run` を呼ばないこと
7. 1 局ずつ: キャッシュの不変（`cache_same.py`）→ `run_seq_pyc_x1.py --sessions 1` → `check_game.py`（照合の問題 0）→ 1 局目だけ追加で、記録に TR3 の `convention_set` があること・`api_contract_unknown` がないこと → 次の局。確かめが失敗したら次を呼ばない
8. 終わったあと: 集計の作り直し 1 回・ゲームの証跡のハッシュの不変・`analyze_prestop.py`・`analyze_tr3.py`（読み取りだけ。ゲームの証跡・`COMPLETE.json` に追記しない）

時間の区別: 起動（worktree・識別・デッキの確かめ・計画）、キャッシュの準備（実時間）、バッチ本体（道具の累積時間 `seconds` と外側の実時間）を別に記録します。

## 4. 実行のあとの集計（`analyze_tr3.py`。読み取りだけ）

次の 6 つを独立に数えます。どれも、0 でないことや全局 `game_over` を合格の条件にしません。

| # | 集計 | 記録の場所 | 確かめの種類 |
|---|---|---|---|
| T1 | 計画・状態・記録が TR3 を示す: 計画の各局の `conventions`、`header.json`・`full_record.json` の `convention_set`（id・照合値・23 規約）、集計の `by.conventions` | 計画・局の記録 | 直接 |
| T2 | 終わり方: `game_over`・上限（`limit_*`）・`halted_known`・`input_unavailable`・`no_progress`・停止の理由・未完了 | `result.json` の `termination`・台帳・完了マーカー | 直接 |
| T3 | 3 規約それぞれの出現: 直接（選ばれた候補の inputs の `convention` の選択肢）と、間接（`no_eligible_card` の局面の本人の観測による 3 条件の評価）を分ける | actors・observe | 直接／間接 |
| T4 | 除外した選択肢が、選択・check・submit に入っていない: 試みの `choice` の選択肢が `eligible` 偽・`convention` つきでない。check・submit の断り・拒否のコードに `NO_OPPONENT_BENCH`・`NO_BENCH`・`NO_DAMAGE_COUNTERS` がない | actors・trace | 直接 |
| T5 | 使える選択肢で進んだ: `play_trainer` の受理の数・3 枚のうち使える場面での受理（選択肢の `eligible` 真のとき）・局の受理の総数 | actors・`result.json` の `metrics.kinds` | 直接 |
| T6 | 対象外の未裁定・拒否・停止: prestop の対象（ほかの未裁定の候補）の延べと種類、`known_stop` の note・拒否のコード・停止の理由 | prestop・`result.json`・judge | 直接 |

**単位**（T3・T4）:

- 延べ（選択肢の数）・局・局面（(主体, position)）を分けます。
- 同じ局面の取り直し（同じ position の 2 回目以降の試み）は、延べに足したうえで、別に「取り直し」として数えます。
- 同じ局面の同じカードの複数の個体（手札に同じカードが 2 枚）は、選択肢の延べでは 2、カードの種類では 1 と数えます。
- 候補の範囲の外の数（`metrics.kinds.play_trainer.excluded`）は `processability:not_implemented` と `processability:unresolved_ruling` を分けて数えます。

**数えないこと・言わないこと**:

- x1 の件数と合算しません。4 局から一般的な頻度・改善の効果を推定しません。
- 規約で使えなかったカードを消費しないこと・状態が変わらないことは、送っていないので対戦では起きません。送らなかったことは T4 で直接確かめますが、「送ったときに消費しない」ことは既存の構築盤面のテスト（[v0.186](play-convention-tr3-v0.186.md)・[v0.187](token-sync-v0.187.md) 6 章のスモーク）に依ります。保存記録に値がないものを確認済みにしません。
- 間接の評価は、規約の適用の直接の記録ではありません。
- 公開用は件数と分類だけ（カード ID・seed・局の識別を出さない）。

## 5. 資源・保存・停止の方針

- 最大の局数は 4、並びは固定（g001 → g004）。未出現でも、追加の局を自動で実行しません。
- 毎局の前に、残り（512 MiB − 計画のディレクトリ）と出力先の空きが、どちらも max(128 MiB, 保存済みの最大 1 局 × 1.5) 以上であることを確かめます（`run_seq_pyc_x1.py` のまま）。足りなければ未着手を残して終えます。
- 時間は道具の累積時間で 300 秒。次の局を始めるには 150 秒の余りが要ります（既定）。予算の延長はしません。
- 記録の取得（prestop・観測）は単局とバッチの時計の中です。時間の上限の近くでは、追加の記録の負荷が進行（`limit_time`）に影響しうる点を、結果の解釈に残します。

| 起きたこと | 扱い |
|---|---|
| 上限の到達（`limit_operations`・`limit_accepted`・`limit_turns`・`limit_time`） | 局の終わり方として記録して続ける（停止方針の既定。記録の失敗とは別） |
| prestop の上限（`prestop:capped`） | 欠落を記録して続ける（note） |
| 記録の失敗（`prestop:failed`・観測の問題） | その局を保存したあとで止める |
| 照合の不一致・ファイルの欠け（`prestop:inconsistent`・`missing`・完了マーカーの照合の問題） | 止める |
| suspect・状態の不整合・replay の不一致・`api_contract_unknown`・保存の失敗 | 止める（既定） |
| 重大な例外 | 吸収しない（未完了の試行） |
| 外側の確かめ（キャッシュの不変・`check_game.py`）の失敗 | 次の局を呼ばない |
| `--acknowledge-stop`・`unlock`・予算の延長 | 自動で使わない（止まったら報告して終える） |

## 6. 受け入れ条件

**実行の妥当性**（成り立たなければ結果を使わない）:

| # | 条件 |
|---|---|
| V1 | 実行コミットの `kyuura_engine`・`tools`・`tests` が `d562ec1` と差 0、無視をふくめ変更 0、識別が 0 章の値と同じ |
| V2 | 計画の 4 局がすべて `CS-KYUURA-PLAY-TR3@1`・照合値 `sha256:a7b800cf…` で、`plan.sha256` に固定されている |
| V3 | 完了した各局の `header.json` の `convention_set` が TR3（id・照合値）で、計画と同じ |
| V4 | 完了した各局で、完了マーカーの照合（必須ファイル・ハッシュ・停止の理由の計算し直し）・判定・replay・観測・prestop の照合（x1 の R2〜R5）が成り立つ。集計で R1・R6 |
| V5 | キャッシュの中身が準備のときと同じ（各局の前後と最終集計のあと） |

**確認したいこと**（成り立たないときは、その内容を結果として記録する。合格・不合格を局の数で決めない）:

| # | 条件 |
|---|---|
| C1 | 規約で `eligible` 偽の選択肢が、選択・check・submit に入っていない（T4。延べ 0）。入っていたら不具合の候補として止めて報告する |
| C2 | 規約の理由の拒否（3 つのコード）が 0 |
| C3 | TR3 の局が、規約による使用不可を避けて進んだ（T5。受理があり、規約が原因の停止がない） |

**数えるだけ**（0 でも、どの値でも合否にしない）: T2 の終わり方、T3 の 3 規約の出現（直接・間接・未出現）、T6 の対象外の未裁定・拒否・停止、取得の状況、時間・量。

- 3 条件が出なかった規約は「未出現」と書きます。ほかの未裁定で止まった局は、その理由を書きます。

## 7. 実行の前に埋める値（下書きでは null）

- 実行コミット（完全なハッシュ）・worktree・未コミット 0・`d562ec1` との差 0・識別
- L67-U の `deck_problems`・content と展開の sha256（実行のときの値）
- `plan.sha256`・局の並び・各局の `conventions`・`prestop_inputs`・`observation`
- キャッシュの場所・準備の記録（Python の実体と版・ファイルの数・checked hash）・dry-run の `use_cache`
- 出力先の空き
- 外側のスクリプトの写しの sha256（`run_seq_pyc_x1.py`・`prepare_pyc_cache_x1.py`・`check_game.py`・`cache_same.py`・`snapshot_hashes.py`・`analyze_prestop.py`）と、`check_plan` の写しの期待値の差分

## 8. 採用の判断が要る事項と推奨値

| 事項 | 推奨 | 別の選択 |
|---|---|---|
| 条件 | L67-U どうし・rules-v2 と boundary・TR3 | 固定デッキ（3 枚がない） |
| seed | 9002・9003（規則で選んだ新しい値） | x1 の 6001・9001（CURRENT との比べになる。今回は入れない） |
| 局 | 4 | 2（seed 1 つ） |
| 規約の直接の記録の修正（2 章） | しない（直接の形と間接の評価で足りる） | prestop の対象を広げる（道具の識別が変わる） |
| 予算 | 300 秒・512 MiB | — |

## 9. 失敗・未確認

- 失敗: なし（このページの値は読み取りと、デッキの検査の CLI 1 回だけで得ました。`__pycache__` は作っていません）。
- 未確認（実行で分かること）: TR3 の局での 3 条件の出現、規約による使用不可の延べ、局の終わり方、時間と量、検証用 AI が TR3 の候補・選択肢の応答で契約の外にならないこと（作りからは止まらないが、テストはない）。
