# 検証用 AI の上限つき逐次バッチ

検証用 AI（`tools/verification_ai`）に、上限つきの逐次バッチ `tools/verification_ai/batch.py` を加えました。
ランダム・ルール・混合の方策で多様な対戦を 1 局ずつ進め、エンジンの問題を記録・再現できるようにするためのものです。

- 変えていないもの: エンジン、GUI、renderer、kyuura、カードデータ、固定デッキ、規約集合、裁定、識別方式
- パッケージの版: 0.179.0 のまま
- 既存の AI: 方策・行動生成・judge・記録はそのまま使います。runner は 1 か所だけ変えました（`MemoryError` を対戦の結果に変えない）。

ゲームの合法性はエンジンと API が決め、戦略は方策が決めるという分け方は変えていません。
バッチの値（計画・台帳・ロック）は、方策・行動生成に渡しません。

## 0. 基点と範囲

| 項目 | 値 |
|---|---|
| 基点 | `origin/main` の `7b3d53c`（PR #39 の取り込み）。木は `claude/vai-0179-follow` の `bbe3f6c` と同じで、0.179.0 と既存の AI を含む |
| 配布を確かめたコミット | `4b6e3fea9212c50622dcfea7142dcc76fd14b09d`（0.179.0）。今のエンジンの `behavior_digest` `67c4c15b…7fca` と同じ |
| 作業ブランチ | `claude/vai-batch`（専用の worktree `C:\dev\kyuura-engine-up5td`）。利用者の `C:\dev\kyuura-engine` は触っていない |
| コードのコミット | `f560e87`。初回の実行は、このコミットの作業ツリーで、計画を保存してから行った |
| 実行の前の計画 | 証跡の `verifier/runs/vai-batch/PLAN.md` |
| 対象外 | 並列・分散・常駐・GUI・汎用のジョブ管理、snapshot の途中からの継続、R-B、全体のテスト、E2E、デッキ・規約集合の追加、seed の探索、lockstep、状態の監査 |

## 1. 構成

新しく持つ責任は次の 5 つだけです。

| 責任 | 実装 |
|---|---|
| 1. 計画を読む | `make_plan`・`load_plan` |
| 2. 1 局ずつ順に実行する | `run_batch`。同じプロセスで、既存の部品を直接呼ぶ |
| 3. 各局を確定保存する | `_run_attempt` |
| 4. 完了局を照合して再開する | `scan`・`verify_complete` |
| 5. 結果と到達範囲を集計する | `aggregate`。保存済みの局だけから作る |

1 局の実行（`EngineAdapter.play`）で使う既存の部品は次のとおりです。

| 部品 | 役割 |
|---|---|
| `runner.run_game` | 方策・行動生成・上限・終わり方の分類。V0〜V3 と同じ |
| `run_v1.check_record` | 完全な記録の `replay_run` と、操作の記録との対応 |
| `run_v1.game_header` | 見出し |
| `records.action_sequence`・`contract_sequence` | 指紋 |

judge（規則の版 5）は、保存する trace に、局が終わったあとで当てます（`judge_trace`）。

- 送信ごとに `judge_normal` を当てる。V3-1 の変異の実行の中で runner が当てるのと同じ引数
- 終わり方に `judge_termination` を当てる。halted_known では、公開の停止の値を渡す
- `judge_face_down_power_accepted` は当てない。受理の前後の公開のログが要るため。当てなかった数を `not_applied` に記録する

方策の順位・反復の抑制・乱数の消費は変えていません。
計画の経路（規約集合を `ID@版` で明示し、既定値を展開した設定）でも、`v2_repeat` の `ACTION_GOLDEN` の 2 件が同じことをテストで確かめました。

使い方は次のとおりです（作業ツリーの根で実行）。

```
python -m tools.verification_ai.batch plan --out <証跡> --batch <名前> --engine-commit <sha> --tool-commit <sha> --seeds 1001 ... --modes uniform-stage rules-v2 mixed
python -m tools.verification_ai.batch run --out <証跡> --batch <名前> [--stop-after-games N] [--acknowledge-stop <game_id> ...]
python -m tools.verification_ai.batch aggregate --out <証跡> --batch <名前>
python -m tools.verification_ai.batch unlock --out <証跡> --batch <名前> --session <ロックのセッション ID>
```

`run` の終了コードは次のとおりです。

| コード | 意味 |
|---|---|
| 0 | 完了、`--stop-after-games` での停止、時間・証跡の上限での停止 |
| 1 | 停止方針・エラーでの停止 |
| 2 | 照合の不一致・ロックで始めなかった |

## 2. 計画の形式（`plan.json`、形式 `kyuura-vai-batch-plan/1`）

`plan` は実行の前に計画を書き、計画のファイルの sha256 を `plan.sha256` に書きます。
既存のディレクトリがあれば、計画を作りません（上書きしない）。

### 2.1 局ごとの項目（`games[]`）

| 項目 | 中身 |
|---|---|
| `game_id` | 一意。`g001-uniform-stage-s1001` の形 |
| `comparison_group` | 同じ条件の比較の組（デッキ・規約集合・seed）。組の中の局も、それぞれ別の `game_id` を持つ |
| `config` | runner の `Config` の全項目を既定値も展開したもの |
| `decks` | 固定デッキの名前・枚数・カードの並びの sha256 |
| `conventions` | 規約集合の `ID@版` と照合値 |
| `policies` | 主体ごとの方策（下の 2.2 節） |

`config` には次のものが入ります。

- デッキ
- 規約集合（`CS-KYUURA-CURRENT@1` のように、既定も明示する）
- ゲーム・方策・ホストの seed
- プロファイル（`deep`）
- 分布・方策・ε・ルールの版・反復の閾値
- 単局の上限 `limits`

`policies` は、`make_policies` で作った値を記録します（乱数は引かない）。

- 名前・版・分布
- seed の文字列（混合の判定の seed を含む）
- ε・ルールの版・閾値・`demote_after`

### 2.2 方式

| 方式 | 方策 |
|---|---|
| `uniform-stage` | 候補も段ごとの入力も均等 |
| `rules-v2` | 閾値 2 の反復の抑制つきのルール |
| `mixed` | ルールの側は rules-v2。ε 0.25、閾値 2 |

`uniform-tuple`・`rules-v1` も使えます。初回は使っていません。
ホストの係は、どの方式でも均等です（既存のとおり）。

### 2.3 バッチ全体の項目

| 項目 | 中身 |
|---|---|
| `format` | 計画の形式の版 |
| `identity` | 道具とエンジンの実装の識別（下の表） |
| `commits` | エンジン・道具のコミット（呼び出し側が渡した値） |
| `limits` | 局数・全体の時間・予備の秒・証跡の量と予備・1 局の attempt の数 |
| `stop_policy` | 3 章 |
| `rules` | 差し替えない・延長しないなどの約束 |

`identity` には次のものが入ります。

| 対象 | 値 |
|---|---|
| 道具 | `tools/verification_ai/*.py` の sha256 の要約 |
| エンジン | 版、`behavior_digest` と `instrumentation_digest`、実行環境（Python の版・乱数の形式） |

### 2.4 実行のときの照合

`run` は始める前に次のことを照らし、1 つでも違えば何も実行しません（`BatchRefused`）。

- 計画の sha256
- 形式
- 実装識別（道具・エンジン・実行環境）
- 各局の設定と、今のデッキの確認値・規約集合の照合値・方策の値

seed・デッキを結果を見て差し替える経路はありません。

## 3. 保存・再開・ロック

### 3.1 保存の配置

```
verifier/runs/<バッチ>/
  plan.json  plan.sha256  ledger.jsonl  aggregate.json  （実行中だけ LOCK）
  games/<game_id>/attempt-001/
    header.json  trace.jsonl  actors/{0,1,host}.jsonl  full_record.json  result.json
    verification.json  judge.json  sequences.json
    files.sha256.json  COMPLETE.json        （未完了なら INCOMPLETE.json がありうる）
public/runs/<バッチ>/summary.json
```

### 3.2 1 つの attempt の確定の順

1. 各ファイルを、同じディレクトリの一時ファイル（`.<名前>.tmp-…`）に書く。flush・fsync のあと、`os.replace` で置きかえる（同じファイルシステム）。
2. すべてを読み直して、書いた値の sha256 と照らす。
3. ハッシュの表 `files.sha256.json` を書く。
4. 最後に `COMPLETE.json` を書く。中身は、計画の sha256・局の設定の sha256・実装識別・表の sha256・必須ファイル・要約・停止方針の判定。

書き込みの途中で止まった場合の扱いは次のとおりです。

- 一時ファイルが残り、目的のファイルは前のまま（またはないまま）になる。
- `COMPLETE.json` がない attempt は未完了。
- Windows ではディレクトリの fsync ができないので、置きかえの永続化は OS に任せる。完了の判断は、ファイルがあることではなく、`COMPLETE.json` とハッシュの照合で行う。

### 3.3 再開

`COMPLETE.json` がある attempt は、次のすべてを照らします。

- 計画・局の設定・識別が一致する
- 表の sha256 が一致する
- 必須ファイルがそろっている
- 表とディスクのファイルの集合が同じ
- 各ファイルのハッシュが一致する

照合の結果ごとの扱いは次のとおりです。

| 状態 | 扱い |
|---|---|
| 照合に通った完了局 | 再実行しない |
| 照合に失敗した完了局（破損・不一致・別設定） | 採用も再実行もせず、バッチを始めない |
| 計画にない局のディレクトリ | 同上 |
| 完了が 2 つある局 | 同上 |
| 未完了の attempt | 消さずに残す。次の番号の attempt として最初から実行する |

中断した attempt・再試行・完了局は合算しません。集計では、局の数と attempt の数（完了・未完了・不正）を分けます。

### 3.4 ロックと台帳

ロックの扱いは次のとおりです。

- バッチのディレクトリに `LOCK` を `O_CREAT|O_EXCL` で作る。中身はセッション ID・PID・ホスト名・開始時刻。
- 同時に 2 つ目を起動すると `LockHeld` で始めない。`aggregate` も同じロックを使う。
- 自分のセッションのロックは、正常な終わり・例外・`KeyboardInterrupt` のどれでも `finally` で外す。
- PID は記録するだけで、生死を調べて自動で解除しない。

ロックが残ったときの手順は次のとおりです。

1. そのセッションのプロセスが動いていないことを、利用者が確かめる。他のプロセスを探す処理は、この道具にはない。
2. `unlock --session <LOCK の session>` で外す。セッション ID が合うときだけ外れ、台帳に `lock_removed` を書く。

台帳 `ledger.jsonl` は追記だけで、1 行に 1 つの出来事を書き、書くたびに flush・fsync します。

- 出来事: セッションの始まり・終わり、attempt の始まり・終わり、停止方針での停止、確かめ、ロックの除去
- 途中で切れた最後の行は、読むときに除いて数える。次に書く行は改行してから書く。

## 4. 上限・停止方針・資源

### 4.1 上限

| 上限 | 値 | 確かめる時点 |
|---|---|---|
| 単局 | runner.`Limits()` の既定（V0〜V3 と同じ: 送信 2000・受理 1000・番 200・120 秒・同じ状態の拒否 16・選び直し 64） | runner が要求と要求のあいだで |
| 局数 | 30 | 計画を作るとき・読むとき |
| 全体の時間 | 累積 600 秒（単調時計）。次の局は、残りが予備の 150 秒以上のときだけ始める | 各局の前 |
| 証跡の量 | バッチのディレクトリで 800 MiB。次の局は、残りが 64 MiB 以上のときだけ始める | 各局の前と、書き出しの前 |
| attempt | 1 局 3 回まで（未完了も数える） | 各局の前 |

全体の時間は、セッションごとの単調時計の経過を台帳に書き、合計します。再開しても戻しません。

- 終わり（`session_end`）のないセッション（異常終了・強制終了）は、最後の記録のあとの時間がわからないので、予備の 150 秒を足す（`estimated_sessions` に数える）。
- 1 回のエンジンの呼び出しは途中で止められない。runner の時間の上限も要求と要求のあいだで確かめるので、1 局が上限をその分だけ超えることがある。
- 予備の秒は、replay_run・書き出しの時間も見込んだ値。
- 強制終了・タイムアウトでのプロセスの終了はしない。

書き出しの前に、その局の量を足すと上限を超えるときは、次のようにします。

- ファイルを書かずに `INCOMPLETE.json`（状態 `evidence_limit`）だけを書く。
- バッチを止める。

### 4.2 停止方針（計画の `stop_policy`。実行の前に保存した初期値）

| 区分 | 扱い |
|---|---|
| 終わり方 `game_over`・`halted_known`・`input_unavailable`・`no_progress`・`api_contract_unknown`・`limit_*` | 保存して次へ |
| 終わり方 `halted_unclassified`・`failed`・`state_integrity`・`exception`・`inconsistency`・`start_rejected`・`negative_side_effect`・知らない値 | 保存して止める |
| judge の `suspect`（送信・終わり方） | 保存して止める |
| judge の `undetermined` | 別に数えて続ける（`note`） |
| runner の異常の候補（`anomalies`） | 保存して止める |
| `replay_run` が期待と違う・記録の対応の問題 | 保存して止める |
| adapter の例外・証跡の書き込みの失敗・証跡の上限 | 未完了の attempt を残して止める |
| `KeyboardInterrupt`・`SystemExit`・`MemoryError` | 対戦の結果に変えない。未完了の attempt と台帳（書ければ）を残して投げ直す。次の局を始めない |

ユーザーの依頼の分類と、既存の分類の対応は次のとおりです。

| 依頼の分類 | 既存の分類 |
|---|---|
| limit | `limit_operations`・`limit_accepted`・`limit_turns`・`limit_time` |
| integrity | `state_integrity` |
| suspect・undetermined | judge の判定の数 |

runner の中の例外は `exception` の終わり方になり、`judge_termination` でも suspect になります。
runner の `MemoryError` は、今回から `exception` にせず投げ直します。

停止方針で止めた局は、確定保存したうえで止めます。
その局を確かめたことを `--acknowledge-stop <game_id>` で台帳に書くまで、`run` は再開しません。

### 4.3 資源

- 1 局の結果は `play` の中だけで持ちます。書いたバイト列は書いたあとに捨て、戻り値は小さな要約だけにします。全局の trace・完全な記録をメモリにためません（weakref のテストで確かめた）。
- メモリは、自分のプロセスの使用量だけを局のあとに記録します（Windows は `K32GetProcessMemoryInfo`、POSIX は `getrusage`）。取れなければ `not_measured` です。値はプロセスの開始からの最大で、局ごとの値ではありません。
- 新しい依存は加えていません。

## 5. 初回の小規模実行（`vai-batch-b1`）

### 5.1 条件

| 項目 | 値 |
|---|---|
| デッキ | 固定デッキ `hitmonchan-dewgong` vs `venusaur-parasect`（1 組） |
| 規約集合 | `CS-KYUURA-CURRENT@1`（既定を明示） |
| seed | 1001〜1010（事前に固定。ゲーム・方策・ホストに同じ値） |
| 方式 | `uniform-stage`・`rules-v2`・`mixed`（ε 0.25） |
| 局数 | 30（seed ごとに 3 方式） |
| 計画の sha256 | `49364ff957ac9a683a3546254aab115c5bc1b07a76d74f68a7fa57c483e3255e` |
| 上限 | 4.1 節の初期値。延長していない |

再開の確かめは、強制終了を使わずに次の手順で行いました。予定の局数は増やしていません。

| セッション | 実行 | 結果 |
|---|---|---|
| 1 | `--stop-after-games 7` で正常に止めた | 7 局（17.8 秒） |
| 2 | 同じ計画で再開 | 完了の 7 局を照合して飛ばし、残りの 23 局を実行（55.2 秒） |

- セッション 1 の 63 ファイルは、セッション 2 のあとも sha256 と更新時刻が同じだった。
- どの局も attempt は 1 つ。

### 5.2 結果

| 項目 | 値 |
|---|---|
| 局 | 計画 30・完了 30・未完了 0・未着手 0。attempt 30（未完了 0） |
| 終わり方 | `game_over` 30（halted・input_unavailable・no_progress・上限・failed はなかった） |
| 判定 | 送信 4126 件がすべて `expected`、終わり方 30 件がすべて `expected`（suspect 0・undetermined 0） |
| 異常の候補 | 0 |
| 拒否・断り・failed・check の invalid | 0・0・0・0 |
| replay_run | 30 局すべて `succeeded`（期待どおり）、記録の対応の問題 0。元の対戦の数には足さない |
| 停止方針で止めた局 | なし |
| 時間 | 累積 73.07 秒（見込みの加算なし）。1 局の runner の時間は中央値 1.36 秒・最大 6.37 秒 |
| メモリ | プロセスの最大の作業セット 170 MB（30 局で計測） |
| 証跡 | 局のファイル 129.3 MB（バッチのディレクトリ 129.5 MB） |

方式ごとの値は次のとおりです。

| 方式 | 局 | 番の数 | 受理 | runner の秒の合計 |
|---|---|---|---|---|
| uniform-stage | 10 | 11〜58（合計 397） | 30〜173（合計 1253） | 14.3 |
| rules-v2 | 10 | 5〜53（合計 291） | 23〜393（合計 1530） | 17.7 |
| mixed | 10 | 7〜52（合計 293） | 26〜370（合計 1343） | 17.8 |

### 5.3 到達範囲

段階ごとの数は、集計の `funnel` に別の数として記録しました。

- 提示（offered）
- 範囲（in_scope）
- 選択（selected）
- 入力の作成（build_ok）
- check
- 送信（submitted）
- 結果（outcome）

各項目の到達は次のとおりです。

- **操作の種類**: 提示された 14 種類のすべてを、選び、受理まで進めた。answer_decision・attach_energy・end_turn・evolve・mulligan_draw・place_starting・play_basic・play_trainer・promote_active・report_janken・retreat・take_prize・use_attack・use_power
- **入力の形**: `choose_option` 7090・`choose_value` 48
- **段の性質**: depends_on_stage・upstream_stages・options_from_stage・total_units・distinct_across_stages・count_max_over_1
- **任意の段**: 使わない 407・使う 170
- **決定の種類**: select_pokemon 256・take_prize 81・promote_active 66
- **待ちの種類**: turn_action・answer_decision・place_starting_pokemon・draw_mulligan_cards・report_janken_result
- **範囲の外**:
  - 受理の前に未裁定で止める play_trainer（`unresolved_ruling`）が 423 回の取得
  - にげるの費用の不足（`total_units_unreachable`）で入力を作れなかった。760 回の試み。V2 と同じ既知の傾向
- **方策の抑え**: 110 件（`repeat_suppressed` 81・`candidate_demoted` 29）。エンジンの拒否ではない。use_power で選んだ 1110 回のうち、送ったのは 1000 回
- **到達しなかったもの**: 停止・拒否・入力を返さない候補・unverified の選択・deep の代替・表示だけの候補の提示

これらの数は、この計画の 30 局の観測です。網羅性・強さ・正しさの証明ではありません。勝敗は集計していません。

## 6. 記録・再現と重複の防止

各局の完全な記録を `replay_run` で確かめました。

- 期待する結果は記録の終わりに合わせる（閉じた記録は `succeeded`、failed で止めた記録は `recorded_failure`）。すべてを succeeded に合わせない。
- 30 局はどれも閉じた記録で、すべて期待どおりだった。
- 再現の確かめは元の実行とは別に `verification.json` に記録し、局の数に足さない。

再開の照合は 3.3 節のとおりです。正常に保存した局は再実行していません（5.1 節）。R-B（U7 の要求の送り直し）は作っていません。

集計は `aggregate` で、保存済みの完了局と台帳から作り直せます。

- 対戦・replay_run をやり直さない。
- 集計だけを実行し直すと、バッチのディレクトリの量（`aggregate.json` 自身を含む）のほかは同じ値になった。
- 公開の集計（`public/`）には、seed を含む `game_id`・局ごとの行・デッキの並び・選択の中身を入れていない。

## 7. テスト

`tests/test_verification_ai_batch.py`（27 件）を書きました。

### 7.1 偽物の adapter と一時ディレクトリ（23 件）

OS のプロセスの終了や本当のメモリの枯渇は使わず、例外は偽物から投げます。次のことを確かめました。

- 計画の展開・ハッシュ・一意性、上書き・局数・重複の拒否
- 計画・識別・設定の変更の拒否
- 完了局の再開時の飛ばし
- 破損・余分なファイル・別設定の完了マーカー・計画にない局の検出
- 完了マーカーの前の書き込みの失敗・一時ファイルだけが残った attempt の保持と再試行
- `KeyboardInterrupt`・`SystemExit`・`MemoryError`・adapter の例外
- 二重起動・aggregate の同時実行・残ったロックと unlock
- 累積の時間（再開で戻さない）・終わりのないセッションの見込み・途中で切れた台帳の行
- 局のあいだと書き出しの前の証跡の量
- attempt の数
- 停止方針（suspect・確かめ・undetermined・各分類）
- 集計だけの再実行と公開の集計
- 局のあとに結果を持たないこと（weakref）
- メモリの計測

### 7.2 本物の部品（4 件）

- 計画の経路で `ACTION_GOLDEN`（uniform-stage-s12・rules-v1-s13）が同じ
- mixed の方策の記録
- runner が `MemoryError` を結果に変えない
- 上限 40 の操作の 1 局のバッチで、`replay_run` が期待どおり

### 7.3 実行

関連モジュールだけを 1 つずつ別のプロセスで実行し、すべて 1 回目で通りました。修正・再実行はありません。

| モジュール | 結果 |
|---|---|
| batch | 7.5 秒 |
| v2_repeat | 10.7 秒 |
| v0179_follow | 2.8 秒 |
| v0 | 4.0 秒 |

コミットの前の開発中に、このテストが台帳の誤りを見つけました。途中で切れた行のあとに続けて書くと、次の行も壊れていました。直してからコミットしました。

## 8. 実装識別

- 版 0.179.0、`behavior_digest` `67c4c15bafcf00b81f7abe7ef2396742181d27744b2af7efd1657f4c90767fca` は、変更の前と後で同じだった（`identity_before.json`・`identity_after.json`）。
- 道具の識別（`tools/verification_ai/*.py` 21 ファイル）は `3d9a1a84…b5e4`。計画と実行で同じだった。

## 9. 証跡

| 保存先 | 中身 |
|---|---|
| `C:/dev/kyuura-engine-verification-vai/verifier/runs/vai-batch/` | 計画（PLAN.md）、テストの出力、セッションの出力、再開の前後のファイルの照合、集計だけの再実行の比べ、実装識別、コマンド |
| `verifier/runs/vai-batch-b1/` | バッチの計画・台帳・30 局の attempt・集計 |
| `public/runs/vai-batch-b1/summary.json` | 非機密の集計 |

マニフェストは、既存の 714 件を照らしたあと（不一致 0）、1100 ファイルで書き直しました（386 件を追加、消したもの・変わったものはなし）。

- `sha256.json`: `00c08b75fd47396692b6e5641097d6a4a7ca03c2090df9ea8804e9c529626bfc`

## 10. 未確認と、大量の対戦へ広げる前の残件

### 10.1 未確認

- 本当の異常終了（プロセスの強制終了・電源断）のあとの再開。テストは例外と、ファイルを置いた状態で代えた。
- 本当の `MemoryError`。
- 停止・拒否・suspect のある局での実際の停止方針。初回の 30 局では起きなかった。
- POSIX でのメモリの計測。
- 証跡の量が大きいときの、再開の照合（全ファイルのハッシュ）の時間。

### 10.2 残件

- known_stop の根拠の登録が DU1 だけなので、停止のある局は undetermined になる（既存の残件）。続ける方針のままでよいかの判断。
- 局数を増やすと、再開のたびの全ファイルのハッシュの照合が重くなる。局ごとの表の照合を、変更時刻で省くかの判断。
- 証跡の量は 1 局あたり約 1.3〜6.9 MB。大量の対戦では、圧縮か、trace・本人向けの記録の間引きの判断が要る。
- デッキ・規約集合を広げるときは、計画を別に作る（今の計画に足さない）。
- `judge_face_down_power_accepted` は、バッチでは当てていない。受理の前後の公開のログが要る。
- 勝敗・きぜつの数え方は未計測（既存の残件）。
