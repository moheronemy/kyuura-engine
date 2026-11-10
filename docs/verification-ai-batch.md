# 検証用 AI の上限つき逐次バッチ

検証用 AI（`tools/verification_ai`）に、上限つきの逐次バッチ `tools/verification_ai/batch.py` を加えました。
ランダム・ルール・混合の方策で多様な対戦を 1 局ずつ進め、エンジンの問題を記録・再現できるようにするためのものです。

- 変えていないもの: エンジン、GUI、renderer、kyuura、カードデータ、固定デッキ、規約集合、裁定、識別方式
- パッケージの版: 0.179.0 のまま
- 既存の AI: 方策・行動生成・judge・記録はそのまま使います。runner は 1 か所だけ変えました（`MemoryError` を対戦の結果に変えない）。

ゲームの合法性はエンジンと API が決め、戦略は方策が決めるという分け方は変えていません。
バッチの値（計画・台帳・ロック）は、方策・行動生成に渡しません。

> 補完（11 章〜15 章）: そのあと、バッチの判定を単局の runner と揃え（受理の中身の判定の接続）、undetermined を理由で分類する停止方針（計画の形式 2）と、
> 証跡の量の区分を加えて、別の計画で 99 局を実行しました。0 章〜10 章は初回（`f560e87`・計画の形式 1・`vai-batch-b1`）の記録で、書きかえていません。

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
- `judge_face_down_power_accepted` は当てない。受理の前後の公開のログが要るため。当てなかった数を `not_applied` に記録する（初回の時点。補完で接続した。11 章）

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

## 11. 補完 1: バッチと単局の判定を揃える

基点は `origin/claude/vai-batch` の `b17d314`（実装 `f560e87`）です。作業ブランチは `claude/vai-batch-100`（同じ専用の worktree）で、補完のコードのコミットは `e9f7e1b` です。
事前の計画は証跡の `verifier/runs/vai-batch-100/PLAN.md` です。補完のコードの下書きと開発中のテストのあと、正式なテスト・コミット・100 局の実行の前に書きました。

### 11.1 判定の経路

| 判定 | 単局の runner（V3-1 の変異の実行の中） | バッチ（`judge_trace`） |
|---|---|---|
| 送信 | `judge_normal(candidate, meaning, submit, stages=…)` | 同じ関数・同じ引数（保存した trace の entry から） |
| 受理の中身（本人のうらのカードの特殊能力） | `judge_recorded_face_down_power(entry)` | 同じ関数（同じ entry） |
| 終わり方 | `judge_run_termination(class, detail, trace)` | 同じ関数 |

受理の中身の判定のために、runner を次のように変えました。

- 本人のうらのカードの特殊能力の送信が受理されたら、受理のあとに加わった公開のログ（観戦者に見える `visible_log`）を、trace の entry の `public_events_after_accept` に記録する。変異の実行かどうかによらない。
- この値は検証者の trace にだけあり、方策・行動生成には渡さない。
- 変異の実行の中の判定（`judge_face_down_power_accepted` の値）は、記録した同じ値に共通の入口で当てる。
- 判定の規則（`judge_face_down_power_accepted`）は変えていない。規則の版は 5 のまま。

受理の中身の判定は次のとおりです。

- 最初の公開の出来事が、候補のポケモンをおもてにしたこと（`secret_plan_revealed`）であること。
- そのあと同じポケモンの `pokemon_power` だけがあれば「おもてにして使った」、`secret_plan_discarded` だけがあれば「たねでないのでトラッシュ」。
- おもてにしていない・どちらでもない・両方がある・記録がない（`face_down_power_public_events_not_recorded`）ときは undetermined。推測しない。

件数は重ねて数えません。

- 送信の判定は、1 つの送信に 1 件（`counts`）。
- 受理の中身の判定は、別の軸（`accepted_content`）で数える。
- runner が変異の実行の中で付けた値は、バッチでは数えない（バッチは変異の実行をしない）。

終わり方の判定の変化は次のとおりです。

- runner の変異の実行の中の判定でも、halted_known では公開の停止の値を渡すようにした。初回のバッチと同じ条件になる。
- 既知の停止は、どちらも undetermined のまま。理由に停止のコードが付く（例 `halt_condition_not_evidenced:UNRESOLVED_MULLIGAN_COMPENSATION`）。
- 過去の V3 の証跡は書きかえていない。`run_v3_2.py` は自分で `judge_termination` を呼ぶ別の道具で、変えていない。

### 11.2 既存の fixture での接続の確かめ

新しい 99 局がこの経路に届くとは限らないので、既存の U-R3a の fixture（`fixtures_u_r3a`）で確かめました。実際に 99 局では届きませんでした（13 章）。

1. 盤面を作り、スナップショットから復元する。
2. 本物の runner（プロファイル boundary・操作 1 回）に通す。選び手はテストのケースの選び手で、方策ではない。
3. 保存される trace にバッチの `judge_trace` を当てる。

| fixture | 選んだ入力 | バッチの受理の中身の判定 |
|---|---|---|
| UR3A-RC | コラッタの炎エネルギー | expected・`face_down_power_revealed_and_used` |
| UR3A-VN | エビワラー → 闘エネルギー → エビワラー | expected・`face_down_power_revealed_not_basic_and_trashed` |

- 同じ fixture を変異の実行の中の判定つきで走らせると、同じ entry に同じ判定・同じ公開のログ・同じ終わり方の判定が付いた。
- 公開のログの記録を外すと undetermined（`face_down_power_public_events_not_recorded`）になり、分類 unclassified でバッチは止まる。

## 12. 補完 2: undetermined の停止方針と証跡の量

### 12.1 undetermined の分類（計画の形式 `kyuura-vai-batch-plan/2`）

undetermined は、送信・受理の中身・終わり方のどれでも、1 つずつ出どころと理由を残し、理由の先頭で分類します。
known_stop の登録（`KNOWN_STOP_EVIDENCE`）は増やしていません。

| 分類 | 理由の例 | 今回の扱い |
|---|---|---|
| `evidence_missing_stop`（根拠不足の停止） | `stop_condition_not_evidenced:<コード>`・`halt_condition_not_evidenced:<コード>`（分類とコード表は合うが、代表の条件の根拠がない） | 保存して続け、理由ごとに数える |
| `unknown_diagnostic`（未知の診断） | `stop_code_not_in_catalog:<コード>`・`halt_code_not_in_catalog:<コード>` | 保存して止める |
| `contract_unknown`（契約の未知） | `unknown_outcome:<値>`・終わり方 `api_contract_unknown` | 保存して止める |
| `no_progress` | 終わり方 `no_progress` | 保存して止める |
| `unclassified` | 上のどれでもない（`stop_not_explained_by_path`・`precheck_kind_category`・`halt_after_supported`・受理の中身の undetermined など） | 保存して止める |

ほかの判定と終わり方の扱いは次のとおりです。

| 区分 | 扱い |
|---|---|
| known_stop | 保存して続ける（`on_known_stop`） |
| suspect（送信・受理の中身・終わり方の合計） | 保存して止める |
| 終わり方 `api_contract_unknown` | 保存して止める（形式 1 では続けていた） |
| 終わり方 `halted_unclassified`・`failed`・`state_integrity`・`exception`・`inconsistency` など | 保存して止める |
| 異常の候補・replay_run の期待との不一致・記録の対応の問題 | 保存して止める |

`evidence_missing_stop` は、計画で `continue` か `stop` を選べます（`plan --undetermined-evidence-missing`）。ほかの分類は止めます。計画にない分類も止めます。
停止の確かめ（`--acknowledge-stop`）は変えていません。集計・再実行・コードから自動で確かめることはありません。

### 12.2 終わり方と判定の違い

| 終わり方（runner の分類） | judge の終わり方の判定 | 理由 |
|---|---|---|
| `game_over` | expected | — |
| `halted_known`（公開の停止の分類が未裁定・未対応・技術的な制限） | undetermined（`evidence_missing_stop`） | 終わり方は「分類が既知の停止」の意味で、正常とは言わない。judge は、停止のコードの代表の条件の根拠（DU1 だけ登録）がなければ known_stop にしない（規則 3） |
| `halted_known`（最後に受理した候補が supported） | undetermined（`unclassified`） | supported は受理のあとの完走を保証しないので、根拠のない停止を正常としない |
| `limit_*` | expected（`tool_limit`） | 道具の上限で、エンジンの問題ではない |
| `input_unavailable` | known_limitation | API が入力を示さない既知の制限 |
| `no_progress`・`api_contract_unknown` | undetermined | 理由を判定できない |
| `halted_unclassified`・`failed`・`state_integrity`・`exception`・`inconsistency` | suspect | — |

生の値は次の場所に残します。

- 停止の値: 要約の `termination_detail.halt`、`judge.json` の `termination.halt`
- 判定の理由: `judge.json` の各行と `undetermined`
- 送信の診断（`diagnostic_id`・分類・エンジンのコード・断りのコード）: `judge.json` の各行

### 12.3 証跡の量の区分

| 区分 | 対象 |
|---|---|
| `management` | `plan.json`・`plan.sha256`・`ledger.jsonl`・`LOCK`（集計の最中はロックを持つ） |
| `game_complete`（ゲームの証跡） | 照合に通った完了の attempt のディレクトリのすべてのファイル（表の各ファイル・`files.sha256.json`・`COMPLETE.json`） |
| `attempt_not_complete` | 完了マーカーのない attempt のディレクトリのファイル |
| `derived` | `aggregate.json` と public の `summary.json`（集計の時点の大きさ） |
| `other` | 上のどれでもない |

- 集計を作り直しても、`game_complete` は変わりません（13 章で確かめた）。
- 局を始める前・書き出す前の上限の確かめは、今までどおりバッチのディレクトリ全体で行います。
- 全ファイルのハッシュの照合はそのままです。圧縮・間引き・照合の省略・新しい保存の仕組みは加えていません。
- 初回の 30 局（`vai-batch-b1`）の証跡は残しています。補完のあとのコードでは道具の識別が違うので、b1 は再実行・再集計しません。

## 13. 最大 100 局の実行（`vai-batch-b2`）

### 13.1 条件

| 項目 | 値 |
|---|---|
| 実行のコミット | `e9f7e1b`（計画の保存の前にコミット） |
| デッキ・規約集合 | 固定デッキ `hitmonchan-dewgong` vs `venusaur-parasect`・`CS-KYUURA-CURRENT@1`（どちらも 1 つだけ） |
| seed | 2001〜2033（33 個。初回の 1001〜1010 と重ならない。実行の前に固定） |
| 方式 | uniform-stage・rules-v2・mixed（ルールの側 rules-v2・ε 0.25）。seed ごとに 3 方式で 99 局 |
| 単局の上限 | 既定（送信 2000・受理 1000・番 200・120 秒） |
| 全体の上限 | 局数 100・累積 900 秒（予備 150 秒）・証跡 2 GiB（予備 64 MiB）・1 局 3 attempt |
| 停止方針 | 12.1 節（`evidence_missing_stop` だけ続ける） |
| 計画の sha256 | `ef2a29ccdafc655f71240dfd7a3ccffb9484833c780315e456db58cd4545edb9` |

中断はなかったので、再開の確かめのための停止はしていません。1 つのセッションで 99 局を順に実行しました（終了コード 0、`completed`）。

### 13.2 結果

| 項目 | 値 |
|---|---|
| 局 | 計画 99・完了 99・未完了 0・未着手 0。attempt 99（未完了 0） |
| 終わり方 | `game_over` 95・`halted_known` 3・`limit_accepted` 1 |
| 送信の判定 | 15654 件がすべて expected |
| 受理の中身の判定 | 0 件（本人のうらのカードの特殊能力の受理に届かなかった） |
| 終わり方の判定 | expected 96・undetermined 3 |
| known_stop | 0 |
| undetermined | 3 件。すべて `evidence_missing_stop`（`halt_condition_not_evidenced:UNRESOLVED_MULLIGAN_COMPENSATION`。seed 2025 の 3 方式で、準備の時点の停止） |
| suspect・異常の候補・拒否・断り・failed・check の invalid | すべて 0 |
| 停止方針で止めた局 | なし |
| replay_run | 99 局すべて `succeeded`（期待どおり）、記録の対応の問題 0 |
| 時間 | 累積 279.8 秒（見込みの加算なし）。1 局の runner の時間は中央値 1.66 秒・最大 19.2 秒 |
| メモリ | 自分のプロセスの最大の作業セット 345 MB（99 局で計測。プロセスの開始からの最大） |
| 証跡 | ゲームの証跡 514.2 MB（1188 ファイル）・管理 0.25 MB・未完了 0・その他 0 |

`limit_accepted` の 1 局は rules-v2 の seed 2004 です。49 番で受理が 1000 に届きました。道具の上限で、判定は expected（`tool_limit`）です。

方式ごとの値は次のとおりです。

| 方式 | 局 | 終わり方 | 番の数 | 受理 | 方策の抑え |
|---|---|---|---|---|---|
| uniform-stage | 33 | game_over 32・halted_known 1 | 0〜70（合計 1258） | 0〜191（合計 3880） | 0 |
| rules-v2 | 33 | game_over 31・halted_known 1・limit_accepted 1 | 0〜60（合計 1029） | 0〜1000（合計 6711） | 589 |
| mixed | 33 | game_over 32・halted_known 1 | 0〜54（合計 1175） | 0〜328（合計 5063） | 40 |

### 13.3 提示・選択・送信・受理

段階ごとの数（99 局の合計）です。提示と範囲は候補の取得ごとの回数で、選択・送信・受理とは単位が違います。

| 操作 | 提示 | 範囲 | 選択 | 入力の作成 | 送信 | 受理 |
|---|---|---|---|---|---|---|
| use_power | 12600 | 12600 | 5047 | 5047 | 4420 | 4420 |
| end_turn | 17926 | 17926 | 2269 | 2269 | 2269 | 2269 |
| attach_energy | 4402 | 4402 | 2032 | 2032 | 2032 | 2032 |
| play_trainer | 9628 | 7706 | 1997 | 1997 | 1997 | 1997 |
| use_attack | 2702 | 2702 | 1192 | 1192 | 1192 | 1192 |
| answer_decision | 935 | 935 | 935 | 935 | 935 | 935 |
| play_basic | 1694 | 1694 | 801 | 801 | 801 | 801 |
| retreat | 16755 | 13014 | 4041 | 621 | 619 | 619 |
| evolve | 1266 | 1266 | 547 | 547 | 547 | 547 |
| take_prize | 243 | 243 | 243 | 243 | 243 | 243 |
| promote_active | 218 | 218 | 218 | 218 | 218 | 218 |
| place_starting | 192 | 192 | 192 | 192 | 192 | 192 |
| report_janken | 96 | 96 | 96 | 96 | 96 | 96 |
| mulligan_draw | 93 | 93 | 93 | 93 | 93 | 93 |

- 提示された 14 種類のすべてが、選択・送信・受理まで進みました。
- 方式ごとの提示・選択・送信・受理は、集計の `by.mode` にあります。
- 入力の形は `choose_option` 28503・`choose_value` 189 でした。
- 決定の種類は select_pokemon 935・take_prize 243・promote_active 218 でした。
- 段の性質は depends_on_stage・upstream_stages・options_from_stage・total_units・distinct_across_stages・count_max_over_1 に届きました。
- 任意の段は、使わない 1413・使う 592 でした。

範囲の外・入力の作成の失敗・方策の抑えは、それぞれ別の数です。

| 区分 | 数 | 中身 |
|---|---|---|
| 範囲の外 | 1922 回 | 受理の前に未裁定で止める play_trainer（`unresolved_ruling`） |
| 範囲の外 | 3741 回 | にげるで入力を作れなかった候補を、同じ状態では選び直さない（`unbuildable:total_units_unreachable`） |
| 入力の作成の失敗 | 3420 回 | にげるの費用の不足（`total_units_unreachable`） |
| 方策の抑え | 629 件 | `repeat_suppressed` 465・`candidate_demoted` 164。use_power 627・retreat 2。エンジンの拒否ではない |

届かなかったものは次のとおりです。

- 拒否・断り・入力を返さない候補・unverified の選択・deep の代替
- 本人のうらのカードの特殊能力の受理
- 表示だけの候補の提示

これらの数は、固定デッキ 1 組・規約集合 1 つでの 99 局の観測です。網羅性・強さ・正しさの証明ではありません。完走の割合も強さの指標ではありません。勝敗は集計していません。

### 13.4 集計だけの再実行

保存した結果から集計を 2 回作り直しました（対戦・replay_run はやり直していない）。

- 局・attempt・終わり方・判定・数・方式ごとの値・段階の数・到達範囲・局ごとの行・replay_run は、3 つとも同じだった。
- ゲームの証跡は 514176979 バイト・1188 ファイルで、3 つとも同じだった。
- 変わったのは次の 2 つだけ（`sessions/aggregate_only_compare.json`）:
  - 派生のファイルの量: 0 → 142284 → 142294。前の `aggregate.json` と公開の要約の大きさ。
  - 管理のファイルの量: 1 バイト。集計の最中のロックの中身。

## 14. テスト（補完）

新しいテスト `tests/test_verification_ai_batch_judge.py`（11 件）を書きました。

- 既存の fixture → 本物の runner → バッチの判定の入口。使った・トラッシュの 2 つ。単局の判定と同じ値
- 公開のログの記録がないとき・出来事が合わないときの undetermined
- halted_known の停止のコードの保持と分類、undetermined の分類の表
- 根拠不足の停止だけを続ける初期値と、止める設定。未知の分類・未知の診断・契約の未知・no_progress・suspect（受理の中身）・api_contract_unknown で止める
- known_stop で続ける
- 停止のあと、集計・再実行で確かめが勝手に外れない
- 集計を作り直してもゲームの証跡の量が変わらない（未完了の attempt を別に数える）
- 受理のあとの公開のログを記録しても、既存の方策の行動の指紋（`ACTION_GOLDEN`）が同じ

既存の `tests/test_verification_ai_batch.py`（27 件）は、偽物の要約を新しい判定の形に直しました。

- 完了局の再実行の防止・ハッシュの照合・停止の確かめのテストは、そのまま通った。
- 計画の停止方針の初期値の確かめは、新しい形に直した。

正式な実行は、1 つずつ別のプロセスで行い、JUnit の XML も保存しました（証跡の `verifier/runs/vai-batch-100/tests/run1/`）。すべて 1 回目で通りました。

| モジュール | 結果 |
|---|---|
| batch_judge | 3.2 秒 |
| batch | 7.6 秒 |
| v2_repeat | 10.7 秒（行動の指紋と契約の値の指紋が同じ） |
| v0179_follow | 2.8 秒 |
| u_r3a | 1.9 秒 |
| v3_1 | 4.0 秒 |
| v3_3 | 2.1 秒 |

開発中（証跡の外）に、次の 2 つを直しました。

- 既存のバッチのテストの偽物が、古い形の要約を返していた（5 件の失敗）。
- 新しいテストの停止の分類の値の書き誤り（`unresolved_ruling`）。

## 15. 識別・証跡・未確認・残件

### 15.1 識別

- パッケージの版 0.179.0 と `behavior_digest` `67c4c15b…7fca` は、補完の前（`vai-batch/identity_after.json`）と後（`vai-batch-100/identity_after.json`）で同じだった。
- 道具の識別は `420244af…a54b` で、計画と実行で同じだった。

### 15.2 証跡

| 保存先 | 中身 |
|---|---|
| `C:/dev/kyuura-engine-verification-vai/verifier/runs/vai-batch-100/` | 事前の計画・テストの出力と JUnit・計画とセッションの出力と終了コード・集計だけの再実行の比べ・識別・コマンド |
| `verifier/runs/vai-batch-b2/` | 計画・台帳・99 局の attempt（判定の根拠 `judge.json`・資源の記録 `COMPLETE.json` の memory を含む）・集計 |
| `public/runs/vai-batch-b2/summary.json` | 非機密の集計 |

MANIFEST_PLACEHOLDER

### 15.3 未確認

- 本人のうらのカードの特殊能力の受理の判定は、fixture でだけ確かめた。99 局では届かなかった。
- 停止方針で実際に止まる局（suspect・未知の診断など）。99 局では起きなかった。
- 根拠不足以外の undetermined は、99 局では出なかった。
- 本当の異常終了のあとの再開・本当の `MemoryError`・POSIX でのメモリの計測。

### 15.4 次に広げる前の残件

- known_stop の根拠は DU1 だけなので、準備の停止（`UNRESOLVED_MULLIGAN_COMPENSATION`）は根拠不足の undetermined のまま。登録するかは、代表の条件の根拠をテストで作ってからの判断。
- P6 の受理の中身の判定（`judge_p6_accepted`）は、runner・バッチに接続していない（`run_p6` の道具だけ）。
- 証跡は 1 局あたり平均 5.2 MB（99 局で 514 MB）。局数を増やす前に、量と再開の照合の時間の扱いを判断する。
- 拒否・停止・入力を返さない候補に届く局が少ない。デッキ・規約集合を広げるかは、別の計画で判断する。
- 勝敗・きぜつの数え方は未計測。
