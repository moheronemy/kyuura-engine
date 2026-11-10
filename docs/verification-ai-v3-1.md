# 検証用 AI の V3-1（通常の進行の中の negative）

[V3 の仕様と計画](verification-ai-v3-design.md) の最初の単位 V3-1 だけを実装しました。目的は、不正な要求が正しく断られ、状態・乱数・ログ・他者への配信・そのあとの正常な進行に
影響しないことを確かめることです。boundary・構築した盤面・新しいデッキ・seed の探索・R-B・V3-2 以降は実装していません。

1 章〜6 章は対戦の実行の前に書き、コードと同じコミットに入れました。7 章以降は実行のあとに書きます。

## 1. 基点と採用の範囲

| 項目 | 値 |
|---|---|
| 基点 | `claude/verification-ai-v3-design` の `1ffe36c`（V3 の設計。V2 の補完 `4c029f4` を含む。`kyuura_engine` は `e26df79`（0.172.0）と同じ） |
| ブランチ | `claude/verification-ai-v3-1`（worktree `C:\dev\kyuura-engine-vai`） |
| 変えていないもの | エンジン本体・GUI・renderer・カードデータ・固定デッキ・規約集合・識別の方式・既存の方策・CN-1 の対応 |

この版で採用した範囲（利用者の指示）: V3-1 と、その範囲に要る判定・記録。V3 の設計の判断事項（D-V3-1〜10）を一括で採用したのではありません。V3-1 の判定（2 章）は、設計の D-6 の表の
うち、V3-1 で使う行を補足したものです。

## 2. 判定の基準（V3-1 の範囲）

### 2.1 区分

`expected`・`normal_rejection`・`known_stop`・`known_limitation`・`suspect`・`undetermined` を分けます（V3 の設計の 3.1 節）。変異の前提を満たさないものは `not_applicable` として
別に記録し、判定の区分に入れません。`suspect` は不具合の疑いの件数で、確定ではありません。既知の区分と足しません。コード表にない診断・期待と違う応答は証跡に残し、既知として
扱いません。`suspect` が出ても証跡を残せれば道具の確かめとしては成り立ちますが、原因が分かるまで「問題なし」とは書きません。

### 2.2 check が valid のあとの拒否（通常の進行。`judge.judge_normal`）

- 同じ主体・同じ取っ手・同じ入力で、あいだに状態の変化（受理・ホストの差し替え）がない（ランナーは check と submit のあいだに別の要求を送らない。negative の要求は送るが、副作用が
  あれば止まる）。この条件で、ホストの段の `refused` は `suspect`（`check_valid_but_host_refused`）。エンジンの `rejected` とは分ける
- エンジンの `rejected` は、API の保証で読む（一律に `suspect` にしない。check が valid であることを受理の保証としない）:
  - 前の確かめを満たす種類（`place_starting`・`mulligan_draw`・`play_basic`・`attach_energy`・`evolve`・`retreat`・`remove_disguise`・`discard_from_play`・`reveal_face_down`）で、
    選んだものがどれも eligible、処理可能性が `unverified` でなく、理由におもてにする前の確かめ（`face_down_reveal_not_evaluated`）がない: 分類 `invalid_input` なら `suspect`、
    停止の 3 つの分類なら `supported` は `suspect`・ほかは `known_stop`、ほかの分類は `undetermined`
  - 受理を保証しない種類・`unverified`: 停止の 3 つの分類なら `known_stop`、ほかの分類は `normal_rejection`
  - どちらでも、診断がない・コード表にない（`unmapped`）なら `suspect`。`failed` は `suspect`
- 終わり方（`judge.judge_termination`）: `game_over` は `expected`、`halted_known` は `known_stop`（直前の受理が `supported` なら `undetermined`）、上限は `expected`（道具の上限）、
  `input_unavailable` は `known_limitation`、`api_contract_unknown`・`no_progress` は `undetermined`、ほか（`halted_unclassified`・`failed`・例外・不整合・副作用）は `suspect`

### 2.3 取っ手（`legal_actions.ActionHost` の契約。静的に読んだもの）

- 失効の要因は次の 4 つ: (1) 受理（`ActionHost.invalidate`。すべての取っ手）、(2) ホストの差し替え・復元（`replace_game`。すべて）、(3) 状態のオブジェクトの置きかえ（`_purge`。
  受理のほかで状態が置きかわったとき）、(4) 主体ごとの保持の上限（`MAX_REVISIONS_PER_ACTOR` = 4。同じ主体が候補を取り直すと、古い順に失効）
- 新しい候補の取得だけで、すべての古い取っ手がすぐに失効するのではない（4 つより古いものから失効する）。拒否・ホストの段の断りでは失効しない
- negative は候補を取得しない（`candidates` を送らない）。通常の進行の取っ手を (4) で失効させない。取っ手を使う変異（別主体・古い取っ手）は、その 1 つの条件だけが不正であることが
  分かる要求で試す: 別主体は、本人の今の取っ手と正しい入力を相手のプレイヤーの入口から送る（コードの判定の順は `_lookup`: 別の対戦 → 取っ手がない → 別主体 → 状態の置きかえ →
  知らない候補）。古い取っ手は、元の入力の受理（(1)）のあとに、受理の前の取っ手と入力を送る
- 期待: 別主体は `CANDIDATES_WRONG_ACTOR`、古い取っ手は `CANDIDATES_STALE`。どちらも `refetch_required` が真（`client_api._REFETCH`）。入力の変異は `CANDIDATE_INPUT_INVALID`・
  `CANDIDATE_NOT_EXECUTABLE` で `refetch_required` が偽

### 2.4 配信

- 「更新が空」ではなく、変異の要求によって**新しい更新が増えていない**ことを確かめる。閲覧者ごとの未取得の更新の数（`ClientHub._outbox` の長さ）と更新の番号（`ClientHub._seq`）を、
  要求の前後で比べる。既にある未取得の更新は数えない（増えた分だけ）
- 数えるときに更新を取り出さない（`take_updates` を呼ばない。配る順・取り出しの位置を変えない）。`ClientHub` に取り出さずに数える公開の口がないので、検証者の側（`judge`）だけが内部の
  値を読む。方策・変異の部品には渡さない

### 2.5 副作用（`judge.snapshot`・`judge.compare`。検証者の側だけ）

変異の要求の前後で、状態のオブジェクトの置きかえ、確認値（`replay_record.checks`: 状態の sha256・乱数の指紋・ログの長さ・区間・状態の区分・決定・停止）、閲覧者ごとの新しい更新、
更新の番号、処理できない結果の有無を比べます。状態のオブジェクトが同じことだけで変化なしとはしません（確認値も比べる）。どれかが変われば `suspect` にし、その対戦の通常の進行を
止めます（終わり方 `negative_side_effect`。前後の値は変異の記録にある）。同じ不正な要求を繰り返しません。

## 3. 変異（`tools/verification_ai/negative.py`）

正常な要求（check が valid だった取っ手・候補・入力）の写しから、1 つの条件だけを変えます。変える前と後の入力・変えた段と位置・変異の種類を記録します。前提を満たさなければ
`not_applicable`（理由つき）にして、無理に作りません。入力の変異は、変える前と後が 1 か所だけ違うこと（置きかえ 1・加えた 1・除いた 1）を確かめ、違えば試しません。

| 種類 | 変えること | 前提（なければ not_applicable） |
|---|---|---|
| `unknown_option` | 入力の 1 つを、その候補のどの段にもない番号にする | 入力が選ぶものの番号（値の段・入力なし・初期配置でない） |
| `duplicate` | ある段で選んだものを、その段の中でもう 1 つ加える（選ぶ数の上限の中） | 上限に余りのある段 |
| `count_over` | 最後の段に、その段の選べるもの（今の経路で実行できる区分）をもう 1 つ加える | 最後の段が上限ちょうどで、加えられるものがある |
| `count_under` | 最後の段の最後の 1 つを除く | 最後の段が下限ちょうどで 1 以上 |
| `path_mix` | 依存する段（`options_by_choice`）の選ぶものを、前の段の別の選び方の参照にだけあるもの（この候補にある番号）にかえる | そういうものがあり、後の段がその段に依存しない（依存すると後の段の参照も合わなくなり、条件が重なる） |
| `non_executable` | ある段の選ぶものを、同じ経路の参照の中で API が実行できない区分と示したもの（`eligible` 偽・`unresolved_ruling` など）にかえる | そういうものがあり、後の段がその段に依存しない |
| `wrong_actor` | 本人の今の取っ手と正しい入力を、相手のプレイヤーの入口から送る | プレイヤーの状態 |
| `stale_after_accept` | 元の入力の受理のあとに、受理の前の取っ手と入力を送る | 元の入力が受理される（されなければ `not_run`） |

- 送る要求: 入力の変異と `wrong_actor` は check を送り、check が valid でなく副作用がなければ submit も送る（check が valid なら submit を送らない: 不正な入力を受理させない）。
  `stale_after_accept` も check のあとに、古いと断られたときだけ submit を送る（元の入力を正常に送り直さない）。check と submit はそれぞれ数える
- 変異の位置・種類・変異の中の選び方は、方策・ゲームと別の乱数（`random.Random("kyuura-vai-v3:negative:<seed>")`）。方策の乱数を使わず、候補を取得しないので、通常の進行の方策の
  選択の順は変わらない
- 変異のあと（入力の変異か `wrong_actor` を 1 つ以上送った状態）、同じ取っ手で元の正常な入力を check して（状態を変えない）、valid で副作用がないことを確かめる（復帰の確かめ。
  別に数える）。そのあとの通常の submit は 1 回だけ（ランナーの既存の送信）

## 4. 記録と再現

- 通常の進行: 既存の完全な記録（`ReplayCollector`）と `replay_run`（R-A）。期待は記録の終わりに合わせる（閉じた記録は `succeeded`、`failed` で止めた記録は `recorded_failure`）
- negative: ホストの段で断られた要求はエンジンに渡らないので、完全な記録に行がありません。要求・応答・前後の比べ・判定を、操作の記録（`trace.jsonl` の `type: "negative"`・
  `"negative_recovery"` の行）と `negatives.jsonl` に置きます
- 比べ: negative の行を除いた通常の進行の意味の列を、V1 の保存した記録（`stage-s12`・`stage-s13`）と比べ、完全な記録の行（主体・送り手・コマンド・結果・受理の番号）と終わり方も比べる
  （R-C の形の比べ。変異のない記録を基準にする）
- 取っ手・一時的な番号をそのまま再送する再現は作らない。R-B（記録した U7 の要求を、取っ手を取り直して意味で探して送り直す）は未実装のまま

## 5. 実行の計画（実行の前に決めた）

| 項目 | 値 |
|---|---|
| 条件 | `hitmonchan-dewgong` 対 `venusaur-parasect`・既定の規約集合・uniform-stage・seed 12 と 13（ゲーム・方策・ホスト）。比べる基準は V1 の `stage-s12`・`stage-s13` |
| 局 | 2 局まで |
| 変異の位置 | `negative.plan_positions(seed, 12, 2, 140)`: 受理の番号 2〜139 から変異の乱数で 12 個。その状態の最初の check が valid の試みで、プレイヤーの状態だけ（ホストの状態は試さない） |
| 種類の選び方 | 変異の乱数で 8 種類を並べ、試した回数の少ない種類から。前提を満たさない種類は `not_applicable` で次へ。1 つの状態で 2 種類まで、各種類 1 回まで |
| 上限 | 通常の進行は V0〜V2 と同じ。変異の要求は 1 局 60 まで（check と submit を別に数える。足りなければ `not_run`）。復帰の check は別に数える。全体の予算 600 秒 |
| 入口 | `python -m tools.verification_ai.run_v3 run --out C:/dev/kyuura-engine-verification-vai --engine-commit <sha> --baseline <V1 の局のディレクトリ> --seeds 12 13` |

結果を見て seed・位置・局を変えません。届かなかった変異は未到達として残します。終了コードは、記録の確かめ（`replay_run`・記録の対応）に問題がなく `suspect` がなければ 0、
`suspect` があれば 3、記録の確かめに問題があれば 1。

## 6. テスト

`tests/test_verification_ai_v3_1.py`（15 テスト）: 変異が 1 条件だけ・前提がなければ not_applicable・変異の部品が `kyuura_engine` を import しない（`MutationTest`）、refused と rejected・
API の保証による判定・期待と違うコード・エンジンに渡った・副作用・正当な失効を疑わない・復帰の判定（`JudgeTest`）、既にある更新と新しい更新の区別・状態の置きかえ・同じオブジェクトで
確認値が変わったときの検出（`SnapshotTest`）、変異の乱数が方策とゲームに影響しない（変異のない実行と同じ意味の列・完全な記録の行・方策の乱数の回数）・復帰の check と通常の送信が
1 回だけ・古い取っ手の試験は受理のあと・副作用の疑いで止めて証跡を残す（`SessionTest`）。既存の方策の意味の列の sha256 は `tests/test_verification_ai_v2_repeat.py` の `UnchangedTest`。

テストの実行（1 モジュールずつ、別のプロセス）: `tests.test_verification_ai_v3_1`（15 テスト）は 1 つが失敗（`test_duplicate_and_count`。`count_over` の例が、最後の段の選べるもの
3 つをすべて選んでいて加えるものがなく、`not_applicable` が正しい動作だった。テストの例の誤り）。例を直して `MutationTest` だけ（7 テスト）を再実行: 失敗 0。ランナーを変えたので
`tests.test_verification_ai_v2_repeat`（15。既存の方策の意味の列の sha256 を含む）・`v2`（19）・`v1`（19）・`v0`（24）: 失敗 0。

## 7. 使い方

```
cd C:\dev\kyuura-engine-vai
python -m tools.verification_ai.run_v3 run --out C:/dev/kyuura-engine-verification-vai --engine-commit <コミット> --baseline C:/dev/kyuura-engine-verification-vai/verifier/runs/v1-hitmonchan-dewgong-vs-venusaur-parasect-default --seeds 12 13
python -m tools.verification_ai.run_v0 manifest --out C:/dev/kyuura-engine-verification-vai --run <実行の名前> --command "<実行したコマンド>" --exit-code <n>
```

`run` は実行のディレクトリがすでにあれば止まります（既存の証跡を上書きしない）。3 局以上は受け付けません。`Runner(config, negative=NegativeSession(seed, positions))` でも使えます。

## 8. 実行の結果（2026-11-08）

実行: コミット `8091ed6`（`8091ed603b3491bde97d6196f66e35086f4925a7`。1〜6 章と同じコミット）。14:21:15Z〜14:21:22Z（UTC）。全体 4.9 秒（予算 600 秒）。終了コード 0。
計画（`plan.json`）は対戦の前に書いた。

### 8.1 通常の進行と V1 との比べ

| 局 | 終わり方 | 受理 | 番 | 意味の列（V1 と） | 完全な記録の行（V1 と） | 終わり方（V1 と） | `replay_run` | 記録の対応 | 通常の送信の判定 | 終わり方の判定 |
|---|---|---|---|---|---|---|---|---|---|---|
| seed 12 | `game_over` | 144 | 50 | 169 行すべて一致 | 一致 | 一致 | 期待 `succeeded`・結果 `succeeded` | 問題 0 | `expected` 144 | `expected` |
| seed 13 | `game_over` | 141 | 41 | 168 行すべて一致 | 一致 | 一致 | 期待 `succeeded`・結果 `succeeded` | 問題 0 | `expected` 141 | `expected` |

変異と復帰の確かめを入れても、通常の進行（方策の選択・エンジンに渡った操作・終わり方）は、変異のない V1 の記録と同じでした。異常の候補（V0〜V2 の名前）は 0。

### 8.2 変異の結果

| 局 | 試した状態 | 変異の要求（check / submit） | 復帰の check | 判定 |
|---|---|---|---|---|
| seed 12 | 計画の 12 状態すべて（16・17・22・32・44・49・75・80・94・97・120・123） | 24 / 24 | 12（すべて `expected`） | `unknown_option` 4・`count_over` 3・`count_under` 4・`non_executable` 1・`wrong_actor` 6・`stale_after_accept` 6、すべて `expected` |
| seed 13 | 計画の 12 状態すべて（14・25・36・49・51・60・66・83・85・91・94・126） | 24 / 24 | 12（すべて `expected`） | `unknown_option` 5・`count_over` 3・`count_under` 4・`path_mix` 2・`wrong_actor` 5・`stale_after_accept` 5、すべて `expected` |

- `suspect` 0・`undetermined` 0。どの変異の要求の前後でも、状態の確認値（状態の sha256・乱数の指紋・ログの長さ・区間・状態の区分・決定・停止）・状態のオブジェクト・閲覧者ごとの
  新しい更新・更新の番号は変わらなかった。期待したコードと `refetch_required` で断られ、どの要求もエンジンに渡らなかった
- 変異のあとの元の入力の check（24 回）はすべて valid（拒否・断りで取っ手が失効しない）。古い取っ手（11 回）はどれも受理のあとに `CANDIDATES_STALE` で断られた
- 変異を送った記録（2 局で 48 行。古い取っ手を含む）の元の候補の種類: `end_turn` 14・`play_basic` 10・`play_trainer` 6・`use_power` 6・`attach_energy` 4・`evolve` 2・`use_attack` 2・`answer_decision` 2・`retreat` 2
- この結果は、この 2 局の 24 状態で試した変異についての観測です。ほかの状態・入力の形・種類について断られることを示すものではありません

### 8.3 not_applicable・未到達

| 種類 | 試せなかった理由（2 局の合計） |
|---|---|
| `duplicate` | **未到達**（2 局とも 0 回）。上限に余りのある段がない 14・入力がない（`end_turn`）7 |
| `non_executable` | seed 13 で未到達。同じ経路に実行できない区分の選べるものがない 13・入力がない 7 |
| `path_mix` | seed 12 で未到達。別の経路だけの選ぶものがない 12・入力がない 7 |
| `count_over` | 加えられるものがない 6・入力がない 7 |
| `count_under` | 最後の段が下限でない 2・入力がない 6 |
| `unknown_option` | 入力がない 7 |

`not_run`（要求の予算・元の入力が受理されなかった）は 0。変異の要求は 1 局 48（上限 60）。

## 9. 失敗・修正・再実行・未確かめ

- 失敗: テストの例の誤り 1（6 章）。実行は失敗なし
- 再実行: 失敗したテストのクラスだけの 1 回。対戦の再実行はしていない（2 局は 1 回ずつ）
- 未実行: なし
- 未確かめ: `duplicate`（未到達）、`options_by_path`・`upstream_stages`/`after` の段の `path_mix`（この 2 局で届いたのは `options_by_choice` の 2 段の操作だけ。特殊能力の段は後の段が依存
  するので対象の外）、初期配置・値の段の入力の変異（対象の外）、ホストの状態の変異、取得の上限（4）による失効（既存のテストに任せた）、エンジンの拒否・停止がある状態での変異、
  ほかの seed・デッキ・規約集合、別のプロセスでの再現
- エンジンの不具合: 見つかっていない（`suspect` 0）

## 10. V3-2 以降へ進むための残件

- `duplicate` が固定デッキの 2 局で届かない（入力の段の上限がほとんど 1）。届かせるなら、選ぶ数の上限が 2 以上の段（にげるのトラッシュ・決定の複数の選択など）のある状態を変異の位置に
  選ぶ方法か、別の固定の条件が要る（seed・位置を結果を見て変えないので、V3-1 では未到達のまま）
- `path_mix` の対象を、後の段が依存する段（特殊能力の 2・3 段）や `options_by_path` に広げるには、1 条件にする変え方（最後の段だけを変えるなど）の設計が要る
- 変異の位置の選び方（受理の番号から均等）では、`end_turn` だけの状態に当たることが多い（入力の変異が試せない）
- V3 の設計の残り（D-V3-1〜10 のうち V3-1 で使っていない判断、V3-2 の boundary と試験用のデッキ、V3-3 の構築した盤面、V3-4 の探索、R-B）、CN-1 のエンジンの側、D-12、きぜつの数え方
