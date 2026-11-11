# 検証用 AI の主体別の観測・更新・公開ログの記録（observe）

- 状態: 実装・限定確認済み（2026-11-11。実装 `fb22693`。TOOL_VERSION 5・判定の規則 6 のまま・パッケージ 0.179.0 のまま）
- 対象: `tools/verification_ai/observe.py`・`runner.py`（記録の入口だけ）・`batch.py`（計画・完了・証跡量）・`fixtures_observe.py`（限定確認の fixture）
- しないこと: 新しい対戦バッチ・デッキリスト・boundary の追加・旧バッチ（30 局・99 局・C1・C2）への継ぎ足し。エンジン・方策・行動生成・判定の規則の変更

## 1. 目的と既存の記録との関係

C1・C2 の結果の確認（[verification-ai-batch-plan3.md](verification-ai-batch-plan3.md) 11 章）で、保存した証跡は「行動する主体の要求と応答」だけで、相手・観戦者への更新・
公開のログ・相手が行動しないあいだの観測は残っていないことが分かった。この記録は、その不足を、これから実行する計画に限って補う。

| 記録 | 中身 | だれのための値か | この単位での扱い |
|---|---|---|---|
| `trace.jsonl` | 試み（attempt）ごとの候補・入力・check・送信・判定の材料（全主体） | 検証者 | 変えない |
| `actors/<主体>.jsonl` | **その主体が行動するとき**の要求（view・candidates・inputs・check・submit）と応答 | その主体の視点の写し（全配信の証跡ではない） | 変えない（意味を広げない） |
| `full_record.json` | 完全な再現用記録（seed・コマンド・確認値） | ホスト・検証者（完全な情報） | 変えない。この形式に混ぜない |
| `observe/view-0.json`・`view-1.json`・`view-spectator.json` | **新規**。主体ごとの閲覧用記録（エンジンの `view_record`。形式 `kyuura_view_format` 1）: 開始と受理ごとの観測・新しいログ・本人の拒否の診断 | その主体が知ってよい値だけ（operation_id などを入れない形式） | 新規 |
| `observe/rows.jsonl` | **新規**。対応表（形式 `kyuura-vai-observation/1`）: ローカルの通し番号ごとの送信・主体別の前後の観測の sha256・ログの位置・閲覧用記録の項目の番号・更新の写し | 検証者 | 新規 |
| `observe/summary.json` | **新規**。行の数・欠け・矛盾・閲覧用記録の構造の検証 | 検証者 | 新規 |

主体は プレイヤー 0・プレイヤー 1・観戦者 の 3 つ。ホストの宛先（`host`）の更新は観戦者と同じ範囲の観測なので、対応表には `host` の宛先として別に残すが、
ホストの完全な情報は `full_record.json` だけが持つ（この形式に入れない）。

## 2. 使い方

- バッチ: 計画を作るときに `--observation`（`make_plan(..., observation=True)`）。計画の `observation.enabled` が真なら、各局で記録を作り、`observe/` の 5 ファイルが必須ファイルになる
  （`batch.required_files`）。偽なら従来と同じ（`observe/` を作らない）
- 単局: `Runner(config, recorder=observe.ObservationRecorder())`。局の終わりに `recorder.files()`（保存するバイト列）・`recorder.summary()`
- 記録を有効にした計画で、記録が `complete` でない局は、停止方針 `on_observation_problem`（既定 stop）で止める
- （TOOL_VERSION 6 から）`plan` では `--observation` か `--no-observation` の明示が必須。要約に観測の状態がない局も止め、完了マーカーの `evidence` で停止つきの完了を区別する（[verification-ai-decklist.md](verification-ai-decklist.md) 7 章）

## 3. 記録の形式

### 3.1 対応表 `observe/rows.jsonl`（1 行 1 つ）

| 項目 | 意味 |
|---|---|
| `seq` | ローカルの通し番号（0 は開始。送信・check の invalid・終わりのたびに 1 増える）。受理番号では拒否を見分けられないので、これを主の番号にする |
| `kind` | `start`・`submit`・`check_invalid`・`end`（と異常の `orphan_drain`） |
| `attempt`・`position` | `trace.jsonl` の試みの番号・状態の番号（check などの無変更の要求は、この試みの番号で trace・actors と対応する） |
| `operation_id`・`actor`・`outcome`・`refusal` | 送信の識別・操作主体・結果（accepted・rejected・refused・failed）・断りのコード |
| `accepted_index` | 受理番号（ClientHub の更新の `number` と同じ）。非受理は `null` |
| `engine_results` | その送信でホストの側が受け取ったエンジンの結果（refused はエンジンに届かないので空） |
| `viewers.<0・1・spectator>` | `before`・`after`: 送信の前後の観測（`observation.observe`）の sha256 とログの位置（区間・ログの長さ）。`view_entry`・`view_kind`: その送信で閲覧用記録に入った項目の番号と種類（入らなければ null）。`new_log_events`: その項目の新しいログの数 |
| `updates.<0・1・spectator・host>` | その送信のあと runner が通常の経路で取り出した更新の写し（`drained`）。観測の中身は、送信のあとの観測と同じなら sha256 だけ（違えば中身も残す）。取り出されなかったら `not_drained` |
| `problems` | 行の期待との矛盾・欠け（4 章） |

開始の行（`seq` 0）は、主体ごとの開始の観測の sha256・ログの位置・閲覧用記録の項目 1、更新の位置（次の番号 1。ClientHub は作った直後で、受理の前に更新はない）を持つ。
終わりの行は、終わり方・最後の観測の sha256・ログの位置・対応付けられなかったエンジンの結果の数を持つ。

### 3.2 主体別の閲覧用記録 `observe/view-<主体>.json`

エンジンの `view_record.ViewRecorder`（[view-record-v0.155.md](view-record-v0.155.md)）をそのまま使う。各項目は、その時点の `observe`・`visible_log`・`visible_segment_logs`・
`CommandResult.view_for` から作った JSON の写しで、作った時点で凍結される。

- 受理: 3 主体すべてに `update`（新しいログ・観測・知らせ）
- 拒否: 送った本人の記録だけに `own_rejection`（診断）。相手・観戦者の記録には項目も連番の欠けも残らない
- 処理できない結果: 全員に `unavailable`（記録は aborted）
- 開始は `ViewRecorder.attach`（origin は `attached`）。ClientHub を作った直後の状態から始めるため。開始の項目には、その区間のログの先頭からの写しが入る

## 4. 欠落・矛盾の扱い

- 欠け（`incomplete`）: runner が取り出さなかった更新（`not_drained`。failed で runner が止まったときなど）、受理・拒否・failed なのにエンジンの結果が届かなかった送信。**空の更新・空の観測として書かない**
- 矛盾（`inconsistent`）: 前の行の送信のあとの観測と次の行の送信の前の観測の違い、受理でないのに観測・ログの位置が変わった、受理の更新の番号が受理番号でない、受理でないのに更新が出た、
  更新の観測が送信のあとの観測と違う、閲覧用記録の項目の数・種類・観測・ログの範囲が対応表と合わない、閲覧用記録の構造の検証（`validate_view_record`）が structure_valid でない
- 記録の失敗（`recorder_failed`）: 記録の処理の例外。runner は以後の記録を呼ばず、対戦はそのまま続ける。閉じられなかった閲覧用記録は `missing` と書く（空の記録にしない）
- `summary.json` の `status` は `complete`・`incomplete`・`inconsistent`・`recorder_failed`。完了マーカーの要約にも入る

## 5. カーソル・保持上限・過去のログ

- **更新のカーソル**: `ClientHub.take_updates(宛先)` は、その宛先の未配の更新をすべて取り出して空にする（読み位置を進める）。記録側はこれを**呼ばない**。runner は送信・check の invalid の
  たびに 4 つの宛先から取り出す（既存の動作。受理なら番号の確かめ、それ以外なら出ないことの確かめ）。記録は runner が取り出した結果の写しを受け取るだけなので、通常側の更新を奪わない
  （テスト `test_recorder_never_takes_updates_and_sees_what_the_runner_took`: 記録の有効・無効で取り出しの回数・順・中身が同じ）
- **保持上限**: ClientHub v1 の未配の更新には上限がない（宛先ごとのリスト）。取りこぼしは「runner が取り出さなかった」ことでだけ起こり、`not_drained` として残る。更新の番号の欠けは
  `update_numbers` の矛盾になる
- **ログの位置**: 件数の差だけでなく、行ごとに前後の（区間・ログの長さ）を持ち、閲覧用記録の各項目のログの（区間・位置）が前の位置から後の位置まで連続することを照らす
- **過去のログ**: 閲覧用記録の項目は作った時点の見える範囲の写しで、あとで公開された情報を遡って入れない。区間が変わるときの前の区間の残りは、区間の終わりの見える範囲
  （`visible_segment_logs`。うらのまま山札にもどったカードの uid を見せない）。記録はファイルに書くまで項目を作り直さない（局の終わりに凍結した項目を書くだけ）

## 6. 通常の進行への非干渉

- 方策・行動生成・判定・指標は記録を参照しない（`self.recorder` は runner の `_rec` からだけ呼ぶ。テストで静的に確かめる）
- 観測は公式の投影関数（`observe`）と閲覧用記録だけで作る。記録のために candidates・inputs・check を余分に送らない（取っ手を変えない）。記録の入口は状態を読むだけ
- 記録の有効・無効で、行動の列・方策の乱数の消費（draws）・最後の状態と乱数の確認値（`replay_record.checks`）・終わり方・counters・anomalies が同じ（fixture の 6 ケース）。
  既存の行動の指紋の設定（uniform-stage・seed 12・操作 80）を記録つきの計画で実行しても、行動の列の sha256 は `ACTION_GOLDEN` と同じ
- 局のファイルで違うのは `observe/` の 5 つと、時刻・所要時間、取っ手（`game`・`revision`。`legal_actions` が `secrets` で毎回作る値。エンジンの乱数ではない）だけ（証跡 `onoff_files_diff.json`）

## 7. バッチへの接続と旧記録

- 計画の形式 `kyuura-vai-batch-plan/4`（`observation` の設定が必須）・完了の形式 `kyuura-vai-batch-complete/4`・TOOL_VERSION 5。道具の識別（tools/verification_ai の .py の sha256）は
  `60a16e49…1850`（TOOL_VERSION 4）から `edc20bef…83bb` に変わった。エンジンの版 0.179.0・`behavior_digest` `67c4c15b…7fca`（C1・C2 の計画と同じ）は変わらない
- 有効な計画では `observe/` の 5 ファイルが必須ファイル・ハッシュの表・完了マーカーの `required` に入る。照合は、マーカーの `required` から外されていても計画の必須ファイルとして照らす
- 証跡量の内訳 `evidence.game_complete_observation`（完了局のうち `observe/` の大きさ。区分の合計には重ねない）と、集計の `observation`（状態ごとの局数・行の数・問題のコード）を足した
- **旧バッチ**: 30 局・99 局・C1・C2 の計画は形式 3 以前で、道具の識別も違うので、新しい版では再開しない（`load_plan` が拒否する）。旧記録に、今のコードで作った観測を継ぎ足さない。
  旧記録の不足（更新・ログ・観戦者の観測がない）はそのまま残る

## 8. 証跡量への影響

既存のテストの設定（uniform-stage・seed 12・操作 80・受理 80）の 1 局で、局のファイルは 2.12 MB から 4.72 MB（2.23 倍）。`observe/` は 2.61 MB（受理 1 回あたり約 33 KB。
閲覧用記録 3 つが各 0.77〜0.79 MB、対応表 0.26 MB）。観測を受理ごとに 3 主体ぶん丸ごと持つため。C1・C2 の規模（54 局・約 290 MiB）なら、およそ 2 倍強になる見込み（未計測）。
大きな計画の前に、観測の差分化・圧縮・間引きを判断する（残件）。

## 9. 限定確認（2026-11-11）

既存のテストの盤面から作る fixture（`fixtures_observe.py`。通常の new_game から届いた証拠とは扱わない）を、本物の runner（開始だけ fixture の状態。`FixtureRunner`）で動かした。
ケースの選び手は方策ではなく、ケースの条件に合う場面だけを公開の値で選ぶ（ほかは均等）。

| ケース | fixture の出典 | 確かめたこと | 結果 |
|---|---|---|---|
| search | パソコン通信のテストの `board()` | 回答者だけに山札のカードが選べるものとして届く。相手・観戦者の閲覧用記録（観測・ログ・知らせ）に、山札のカード・選んだカードの uid が出ない（検索のログは `hidden`） | 成り立つ |
| opponent | U7-1 のテスト（キョウのベトベトン・コインおもて・ワザのあと） | 決定に答えるのはプレイヤー 1 だけ。プレイヤー 0 は waiting_for_player で、入力の要求は拒否。受理の更新は 4 宛先に番号 1 | 成り立つ |
| trader | ポケモン交換おじさんのテストの `board()` | もどしたカード・選んだカードが、その送信の新しいログで 3 主体すべてに出る | 成り立つ |
| er9 | エネルギー回収のテストの `board()` | 0 枚の拒否は本人の記録だけに診断（`UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE`）。相手・観戦者に項目・更新・ログなし。前後の観測が同じ。受理番号は 1・2・null・3 で、拒否はローカルの番号で見分ける | 成り立つ |
| p6・ur3a | `fixtures_p6`（P6A）・`fixtures_u_r3a`（UR3A-RC）。boundary のプロファイル | 観戦者の閲覧用記録のその送信のログが、trace の `public_events_after_accept` と同じで、受理の中身の判定（`judge_recorded_accepted_content`）が同じ expected | 成り立つ |

そのほか: 行と trace の operation_id・主体・結果の一致、受理番号の連続、取り出されなかった更新の `not_drained`（incomplete）、記録の例外（recorder_failed。対戦は記録なしと同じ）、
対応表と閲覧用記録の不一致の検出、記録つきの本物のバッチ 1 局（既存のテストの設定）の保存・照合・1 バイトの書きかえの検出・`required` から外したときの検出、停止方針、旧形式の計画の拒否。

テスト: `tests/test_verification_ai_observation.py`（16 件）と、関係する 7 モジュール（batch 27・batch_judge 11・er9_evidence 7・v2_repeat 16・p6 16・u_r3a 12・v0 24）を
1 つずつ別のプロセスで実行し、すべて成功（129 件）。全体テストは実行していない。

## 10. 未確認と残件

- 未確認: 区間が変わる（延長戦）・処理できない結果（failed）・ホストの操作（ジャンケン）の行は、テストの fixture で通していない（形式と照合の処理だけ）。記録つきの新しいバッチは実行していない
- candidates・inputs・check の応答の前後比較は代表のテストだけ（全要求の通信記録の基盤ではない）。check などは対応表の `attempt` で trace・actors と対応付ける
- 証跡量（8 章）。大きな計画の前に差分化・圧縮・間引きを判断する
- 閲覧用記録の凍結・区間の扱いはエンジンの `view_record` の保証（エンジンのテスト `tests/test_view_record_v0_155.py`）に頼る。この単位ではエンジンのテストを実行していない（エンジンは変えていない）
- デッキリスト・boundary の方式へ進む前に: 記録を有効にした計画で、選べるものの数を伏せる決定（`HIDDEN_COUNT_KINDS`）と相手が答える決定が、相手・観戦者の記録に出ないことを確かめる
  （この単位の fixture は search と opponent の 2 例だけ）

## 11. 証跡

`C:/dev/kyuura-engine-verification-vai/verifier/runs/vai-observe-record/`（事前計画 `00_plan.md`・記録例 `examples/<ケース>/`・テストの出力と JUnit `tests/`・識別・証跡量・
コマンド `commands.txt`）。公開用の集計は `public/runs/vai-observe-record/summary.json`（件数・状態だけ）。主体別の観測は本人の手札・検索の選べるものを含むので、ファイル全体を公開できるとは扱わない。
