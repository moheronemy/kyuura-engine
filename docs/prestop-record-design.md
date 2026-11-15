# 範囲の外にした未裁定の候補のカードを、検証者用の記録に残す機能の設計

→ 2026-11-15 に実装した（TOOL_VERSION 11・計画と完了の形式 7。11 章）。以下 0〜10 章は設計の時点の記述です。

2026-11-15。調査・設計・文書化だけです。実装・テスト・ビルド・対戦・judge・replay・追加の計測はしていません。`kyuura_engine`・`tools.verification_ai` は import していません（コードを文字として読んだだけ）。

- 基点: `claude/prestop-ruling-breakdown` の `7f51ce4`（origin と一致。main `b1e4430` の子孫で main には入っていない。コードは main と同じ）。作業は worktree `C:\dev\kyuura-engine-lt30`・ブランチ `claude/prestop-record-design`。
- 前提の調査: [受理の前の未裁定の候補の内訳](prestop-ruling-breakdown.md)（13 バッチの延べ `play_trainer` 5,052・`discard_from_play` 317・`use_stadium` 18。停止コードは記録にない）。
- 機械可読の下書き: [prestop-record-design.json](prestop-record-design.json)（`status: draft`）。
- 証跡: `kyuura-engine-verification-vai/verifier/runs/prestop-record-design/`。

## 0. 結論（推奨案）

- **エンジンは変えません。** 公開 API の `inputs` を、本人の入口から、同じ候補の取得の取っ手で 1 回呼びます。返る選択肢（`card`・`card_id`・`processability`・`reasons` など）だけを、検証者用の新しいファイルに残します。
- 呼ぶ場所は runner の `_episode_loop` です。`_scope` と `metrics.fetch` のあと、方策の `choose` の前に置きます。対象は、範囲の外の理由が `processability:unresolved_ruling` の候補だけです。
- 同じ (主体, `position`, 種類, 候補の中身) の 2 回目以降は取得しません。保存済みの記録では、同じ局面で候補の中身が変わった例は 0 で、取り直しは最大 6 回でした。
- 計画で明示的に有効にしたときだけ動きます（既定は無効）。計画の形式 7・完了の形式 7・`TOOL_VERSION` 11 にします。エンジンの版・`behavior_digest`・P1/P3 の basis は変わりません。
- 非干渉は、コード上の根拠で「状態・乱数・ログ・決定・更新・取っ手の発行・方策の入力を変えない」と言えます。ただし例外が 1 つあります。**実時間が増えるので、単局の時間の上限（`seconds`）やバッチの予算の近くでは、終わり方が変わりえます。** 受け入れ条件でこれを分けて確かめます（6 章）。
- 停止コードは取れないままです。静的なコードの候補を、実行時の停止コードに読み替えません。

## 1. 今の経路（読んだコード）

| 段 | 場所 | 内容 |
|---|---|---|
| 候補の取得 | `runner._episode_loop`（`request(endpoint, "candidates")`） | 本人の入口。`legal_actions._candidates` が候補を作る。このとき選択肢ごとに受理の前の確かめ（`check_play_trainer` などの `_probe`・`_probe_recording_identity`。状態の複製の上の試行をふくむ）を済ませ、選択肢と処理可能性を `_Candidate.inputs` に持つ。`host._issue` が取っ手（`revision`）を発行し、主体ごとに最大 4 つ保持する（`MAX_REVISIONS_PER_ACTOR`） |
| 範囲 | `runner._scope` | `display_only`・`input_withheld`・`processability:<区分>`・`unbuildable:<理由>` の順に外す。外した候補の `id → 理由`（`reasons`）を返す |
| 計数 | `metrics.fetch(position, cands, in_scope, reasons)` | 取得 1 回ごとに、種類ごとの提示・範囲の外の理由を数える（前回の延べの元） |
| 選択 | `policy.choose("candidate", in_scope, context)` | 方策の乱数を使う。範囲の中だけを見る |
| 本人の記録 | `actor_logs[actor].append({"type": "attempt", ..., "candidates": response, ...})` | 選んだ取得だけを書く。範囲の中が空で止まった取得は書かない |
| 入力 | `request(endpoint, "inputs", **handle)` | 選んだ候補だけ。範囲の外の候補の入力は取らない |
| 入力の生成・check・submit | `B.build_choices`・`request(..., "check")`・`submit_checked` | 方策の乱数を使う。submit だけが状態を変えうる |

## 2. 追加の `inputs` の要求の副作用（コード上の根拠と未確認）

`client_api._Endpoint._inputs` → `ClientHub._state()` → `legal_actions._inputs(host, actor, game, revision, candidate)` → `ActionHost._lookup`。

| 確かめた点 | 結果 | 根拠 | 未確認・条件 |
|---|---|---|---|
| 状態・乱数・ログ・決定 | 変えない | `_inputs` は `_lookup` のあと、作り置きの `found.inputs` を `_copy`（JSON の写し）で返すだけ。コマンドを作らない・`submit` を呼ばない | — |
| 先読み・複製の上の試行 | しない | 確かめは `_candidates` で済んでいる（`_trainer_candidate`・`_board_candidates`・`_stadium_candidate`） | — |
| 本当のカードの読み取り | 新たには読まない | 同上。返す値は候補を作ったときに本人向けに作った値（`_card_option`: 本人の手札の `card`・`card_id`。`_pokemon_option`: 本人のうらは `face_down` だけで `card_id` なし） | — |
| 更新の箱 | 消費・追加しない | 更新を足すのは `ClientHub._on_result`（受理・結果のあと）、取り出すのは `take_updates` だけ | — |
| ログの写し（0.183.0 の `log`） | 変えない | `_record_log` は結果のあとだけ | — |
| 取っ手の発行・保持数 | 発行しない | 発行は `_candidates` の `host._issue` だけ。`_inputs` は発行しない | **取っ手が古いときだけ** `_lookup` が `_purge()` で保持中の古い取っ手を捨てる。推奨案は取得の直後に呼ぶので、状態は同じオブジェクトで、捨てる取っ手はない見込み（受け入れ条件で確かめる） |
| キャッシュ・登録表 | 書かない | `_lookup` は `self._issued.get`・`item.candidates.get` を読むだけ | — |
| 処理できない結果のあと | 誤りの応答 | `ActionHost._state` が `HostStoppedError` → `client_api` は `CLIENT_GAME_UNAVAILABLE` | submit の前には起こらない見込み |
| 取っ手が合わない | `refusal`（`CANDIDATES_STALE` など）。`ok` 偽・`refetch_required` 真 | `_lookup` | 直後に呼ぶので起こらない見込み。起きたら記録の失敗として残す（6 章） |
| 入力の境界が未確認 | `withheld`（`INPUT_BOUNDARY_UNCONFIRMED`）・`stages: []` | `_inputs` | 範囲の外の理由が `input_withheld` の候補は対象にしない。未裁定の候補で起きたら `withheld` と記録する |
| 表示だけ・入力なし | 表示だけの候補は理由が `display_only` で対象外。入力のない候補（`input_stages` が空）は `stages: []` が返る | `_scope`・`_stadium_candidate`（選ばせない効果） | 入力のない候補は要求しない（記録は「入力なし」） |
| そのほかの例外 | エンジンの不具合なら `endpoint.handle` から例外が出る | `handle` が捕まえるのは `HostStoppedError` だけ | 6 章の扱い |
| 時間・メモリ | 増える | 要求 1 回は、辞書の参照と JSON の写し 2 回（`_copy` と runner の `request`） | 実測していない。単局の `seconds` の上限・バッチの予算に入る（6 章） |

**結論**: 状態・乱数・ログ・決定・更新・取っ手の発行を変えないことは、コード上の根拠で言えます。取っ手の保持（古い取っ手を捨てる経路）と時間は、条件つきです。どちらも受け入れ条件で確かめます。「読み取りだから無副作用」とは扱いません。

**再利用の検討**: 範囲の外の候補は選ばれないので、通常の経路でその候補の `inputs` を取ることはありません。候補の応答そのもの（保存済み）には選択肢がありません（`input_stages` の段の番号と種類だけ）。そのため、候補全体が未裁定のときの再利用元はありません。選ばれた候補の中の未裁定の選択肢は、今の actors の記録（`inputs.response`）にあるので、それを再利用し、新しい仕組みは作りません。内部の完全な状態・秘密のカード表から補う案は採りません。

## 3. 取得の時点と方策への非干渉

**時点**: `_episode_loop` の中で、`in_scope, scope, reasons = self._scope(...)` と `self.metrics.fetch(...)` のすぐあと、`if not in_scope: raise _Stop(INPUT_UNAVAILABLE ...)` の前。範囲の中が空で止まる取得も記録できます。

**対象**: その取得の候補のうち、`reasons[c["id"]] == "processability:unresolved_ruling"` で、`input_stages` が空でないもの。種類で絞りません（今の記録では 3 種類だけ。全種類を数えた結果）。

**要求**: その取得の応答の `game`・`revision` と候補の `id` で、本人の入口へ `request(endpoint, "inputs", ...)`。記録用の要求は runner の新しい関数 1 か所だけから呼び、通常の要求と区別して記録します。

| 条件 | 推奨案での扱い |
|---|---|
| 方策の範囲・順位・選択・入力の生成 | 変えない（記録は `_scope` の結果を読むだけ。`in_scope`・`reasons`・`unbuildable`・`tried` を書きかえない） |
| 追加の応答を方策へ渡さない | 渡さない（`context`・`own_view`・`policy` のどの属性にも入れない。`actor_logs`・`trace` にも入れない） |
| 方策・混合・ホストの乱数 | 使わない（記録の処理は乱数を持たない。`inputs` はエンジンの乱数を使わない） |
| check・submit | 呼ばない |
| candidates の余分な取得 | しない（同じ取得の取っ手を使う） |
| 通常の記録との区別 | 別のファイル `prestop/inputs.jsonl`。`metrics`・`coverage`・`counters`・`anomalies` も変えない |
| 重複 | 同じ記録の鍵（4 章）の 2 回目以降は要求しない（数だけ数える） |
| 失敗のあと | 対戦は続ける。記録の側だけを止めるか続けるかは 6 章 |

**結果が変わりうる条件**（非干渉を保証できない点）:

1. **時間の上限**: 追加の要求の時間は、単局の単調時計（`Limits.seconds`。既定 120 秒）とバッチの累積（`budget_seconds`・`game_reserve_seconds`）に入ります。上限の近くで終わる局は、有効・無効で終わり方（`limit_time`）や、次の局を始めるかが変わりえます。
2. **取っ手の保持**: 直後に呼ぶ前提が崩れると（同じ取得のあいだに状態が置きかわる）、`_purge` で取っ手が捨てられえます。今の runner では、取得から方策の選択まで submit はないので、起こらない見込みです。
3. **例外**: 記録用の要求でエンジンの例外が出たとき、捕まえれば対戦は続き、捕まえなければ無効のときと違う終わり方になります（6 章で扱いを決める）。

ほかの経路（観測の記録 `recorder`・変異 `negative`）とは、次のように組み合わせます。観測の記録とは組み合わせてよいことにします（観測の記録は API を呼ばない）。変異（V3-1）とは、最初の版では組み合わせません（`ValueError`。観測の記録と同じ扱い）。

## 4. 記録の形式・重複・上限

**ファイル**（局の試行のディレクトリ。有効にした計画だけ必須）:

- `prestop/inputs.jsonl`: 1 行 = 記録の鍵ごとの最初の 1 回（形式 `kyuura-vai-prestop-inputs/1`）
- `prestop/summary.json`: 局の集計と状態（形式 同じ）

**記録の鍵**: (主体, `position`, 候補の種類, 候補の中身の要約)。候補の中身の要約は、`id` を除いた候補の応答（`runner.candidate_key` と同じ正規化）の sha256 です。取っ手（`revision`）と候補の番号（`id`）は鍵に入れません。

- 同じ位置でも、候補の中身（処理可能性・理由・保証の文・`stadium` など）が違えば別の鍵になります。保存済みの記録では 0 件でしたが、契約の上では起こりうるので、鍵に入れます。
- 取っ手だけが違う取り直しは同じ鍵で、要求しません（`repeats` に数えるだけ）。

**1 行の項目**（最小）:

| 項目 | 内容 |
|---|---|
| `format`・`seq` | 形式と、局の中の通し番号 |
| `actor`・`position`・`episode`・`fetch` | 主体・受理の数（runner の `position`）・エピソードの番号・この局の取得の通し番号（記録の側で数える） |
| `candidate` | `id`・`kind`・`processability`・`reasons`・`input_disclosure`・`input_stages`、`stadium`（あれば）、`content_sha256`（記録の鍵の要約）。保証の文は sha256 だけ |
| `source` | `record_fetch`（記録用の取得）。今の版では通常の取得の再利用は起こらない（範囲の外の候補は選ばれない）ので、値は 1 つ |
| `status` | `ok`・`withheld`・`refused`・`contract_unknown`・`no_stages`・`error` |
| `refusal`・`withheld` | 返ったコードだけ（文は 200 字まで） |
| `stages` | 段ごとに `stage`・`input`・`role`・`meaning`・`count`、選択肢ごとに `id`・`card`（uid）・`card_id`（あれば）・`face_down`（あれば）・`pokemon`・`zone`・`processability`・`eligible`・`reasons`。ほかの項目は写さない |
| `bytes`・`seconds` | 応答の JSON のバイト数・要求の時間（単調時計） |

- `card_id` がない選択肢（本人のうらのカード）は `face_down` だけを残し、観測や `real` から補いません。

**上限**（保存済みの 272 局の記録から。実測ではない）:

| 上限 | 推奨値 | 根拠 |
|---|---|---|
| 局ごとの記録用の要求の数 `max_fetches_per_game` | 256 | 記録の鍵の数は 1 局で中央値 8・p95 51・p99 102・最大 214 |
| 1 回の応答の量 `max_response_bytes` | 16,384 | 選ばれた `play_trainer` の `inputs` 応答は中央値 669・最大 2,736 バイト |
| 局ごとの保存の量 `max_bytes_per_game` | 1,048,576 | 256 × 4 KiB。272 局の鍵の合計 4,188 × 最大 2.7 KB でも約 11 MB（局あたりは小さい） |

- 上限に達したら、その局のそれより後の記録用の要求をやめます（対戦は続ける）。それ以降の未裁定の候補は数え続け、`skipped_cap` として集計します（0 件として扱わない）。要約の状態は `capped` です。
- 応答が `max_response_bytes` を超えたら、選択肢を写さず `status: error`・理由 `response_too_large` とし、その鍵は取得済み（内容なし）にします。

**要約**（`prestop/summary.json`）: `enabled`・`status`（`complete`・`capped`・`failed`）・上限・`offered`（範囲の外の未裁定の候補の延べ。種類ごと）・`record_keys`・`fetched`・`ok`・`withheld`・`refused`・`contract_unknown`・`no_stages`・`error`・`skipped_cap`・`repeats`・`bytes`・`seconds`・`failure`。

## 5. 集計（将来）と照合

| 区分 | 出し方 |
|---|---|
| 提示の延べ | `summary.offered`（取得 1 回の中の候補 1 つ = 1。今の `metrics` の `excluded["processability:unresolved_ruling"]` と同じ定義） |
| 記録用の取得を試みた局面 | 鍵の数のうち、要求した数（`fetched`） |
| 取得できた局面 | `ok` |
| 候補全体と選択肢の未裁定 | 候補全体は `prestop/inputs.jsonl`。選択肢の一部だけは、今の actors の `inputs.response`（再利用。別の表） |
| カード別の出現 | `ok` の行の選択肢の `card_id`（ない場合は `face_down`・`card_id なし`として別に数える） |
| 未取得 | `withheld`・`refused`・`contract_unknown`・`error`・`skipped_cap`・無効の計画・旧記録を分ける。どれも 0 件とは数えない |
| 同じ候補の繰り返し | `repeats` |
| 停止コード | 不明のまま（記録に出ない）。静的なコードの候補は別の表で「静的」と書き、実行時のコードとしない |

**照合**（前回の 2 倍の誤りを踏まえる）:

1. 局ごとに、`summary.offered` の種類ごとの値が、同じ局の `result.json` の `metrics.kinds.<種類>.excluded["processability:unresolved_ruling"]` と一致する。
2. 局ごとに、`offered = Σ(鍵ごとの 1 + repeats) + skipped_cap の延べ + 無効のとき 0`。`record_keys = fetched + skipped_cap の鍵`。
3. バッチの集計は局ごとの要約を 1 回ずつ足す（種類の集合を 1 回だけたどる）。集計の結果が局ごとの合計と一致することを確かめる。

## 6. 時間・失敗・秘密

**時間**: 記録用の要求は、単局の単調時計とバッチの累積時間の中で行い、予算の外にしません。要約に `seconds`（記録用の要求の合計）を残し、累積時間のうちの割合を報告できるようにします。単局の上限・予算・待ちの条件は変えません。

| 失敗 | 扱い |
|---|---|
| 記録用の `inputs` だけが `refusal`（stale など） | その鍵を `refused`（コード）と記録し、対戦は続ける。通常の `anomalies` には入れない（要約の数だけ） |
| `withheld` | `withheld`（コード）と記録し、続ける |
| 契約不明・形式の不正（`stages` が並びでない・選択肢が辞書でないなど） | `contract_unknown`（どこが合わないか）と記録し、続ける。通常の進行の `API_CONTRACT_UNKNOWN` の停止にはしない（記録の側の判定なので） |
| 通常の例外（記録の処理・要求で `Exception`） | 記録の失敗（`failure`。場所・型・文 300 字まで）とし、その局のそれより後の記録をやめる。対戦は続ける。要約の状態は `failed` |
| `MemoryError` | 通す（runner の `_rec` と同じ。局は未完了） |
| `KeyboardInterrupt`・`SystemExit` | 捕まえない（`Exception` でない）。今の未完了の試行の扱い（`INCOMPLETE.json`・再開）に従う |
| 保存の失敗 | 今の局のファイルの保存と同じ扱い（必須ファイルが揃わなければ完了にしない） |
| バッチの停止方針 | 有効にした計画で要約の状態が `failed`・必須ファイルの欠けのときは、観測の記録の欠けと同じく、その局のあとでバッチを止める。`capped` は止めない（集計で範囲を示す） |

- 記録の失敗は、方策の拒否・ゲームの停止・エンジンの拒否とは別の区分です。

**秘密**: 記録するのは、本人の入口が本人に返した値だけです（本人の手札のカード、本人の場のポケモン、本人のうらのカードは `face_down` だけ）。保存先は検証者用の局のディレクトリ（`verifier/`）で、actors の記録と同じ扱いです。ClientHub の更新の箱・ログの写し・GUI へは何も渡しません（記録は runner の中だけで、hub の配信の経路を通らない）。公開用の要約には件数と分類だけを出し、カード ID・uid・seed・局の識別を出しません。

## 7. 受け入れ条件と将来のテスト（今回は実行しない）

**fixture・人工の応答・短い既存の固定テストで確かめる**:

| # | 内容 |
|---|---|
| A1 | 有効と無効で、行動の列の指紋（`sequences.json` の action・contract）・trace の各試みの選択・入力・check・submit・終わり方・`counters`・`metrics` が同じ（時間の上限にかからない短い局。既存の固定の短い局と v2_repeat の指紋） |
| A2 | 方策・混合・ホスト・変異の乱数の消費が同じ（乱数の状態を局の終わりで比べる。偽物の方策で `choose` の呼び出しの列を比べる） |
| A3 | 記録用の要求の前後で、取っ手の保持数（`ActionHost.issued_count`）・更新の箱の長さ・ログの写しの位置・状態のオブジェクトが同じ |
| A4 | 候補・主体・位置の対応（構築盤面: 手札のトレーナーがすべて未裁定の場面で、記録の選択肢の `card_id` が本人の手札のそのカードと同じ） |
| A5 | 重複の抑制（同じ局面の取り直しで要求は 1 回、`repeats` が増える）と、上限（偽物の小さい上限で `skipped_cap`・`capped`） |
| A6 | `withheld`・`refused`（偽物の入口が stale を返す）・`contract_unknown`・通常の例外・`MemoryError`・`KeyboardInterrupt` の扱い |
| A7 | 保存・必須ファイル（有効のときだけ）・`files.sha256.json`・COMPLETE の照合・再開（有効の計画で途中から再開しても、完了局のファイルが同じ） |
| A8 | 公開の要約・公開の出力に、カード ID・uid・seed・局の識別が入らない |
| A9 | 無効（既定）の計画では、ファイル・要約・識別以外の出力が今と同じ |
| A10 | 本人のうらのカードの選択肢は `face_down` だけで、`card_id` を補わない |

**新しいバッチで確かめる**（初回の限定バッチ。別の単位で計画する）:

- 照合 1〜3（局ごとの延べが `result.json` と一致・集計が局の合計と一致）
- `refused`・`contract_unknown`・`error` が 0 か、0 でないなら件数と理由
- 記録用の要求の時間の合計と、累積時間に対する割合。上限に達した局の有無
- カード別の出現の表（`play_trainer`・`discard_from_play`・`use_stadium`）

## 8. 変更箇所・版・互換性

| 箇所 | 変更 |
|---|---|
| `tools/verification_ai/runner.py` | `Runner.__init__` に `prestop` の引数（記録器。None なら今と同じ）。`_episode_loop` の 1 か所で記録用の関数を呼ぶ。`run_game` にも同じ引数 |
| 新しいファイル `tools/verification_ai/prestop.py` | 記録器（鍵・上限・形式・要約・失敗）。`observe.ObservationRecorder` と同じ約束（`failure`・`files()`・`summary()`） |
| `tools/verification_ai/batch.py` | 計画の項目 `prestop_inputs: {"enabled", "version", "limits"}`（ない・偽なら無効）。`required_files` に有効のときだけ 2 つ。完了のマーカーと局の要約に記録の状態。停止方針に `failed` を足す。集計に局ごとの合計 |
| 計画・完了の形式 | 7 に上げる（形式 6 の計画は今と同じく再開しない。移行しない） |
| `TOOL_VERSION` | 11。道具の識別（`tool_digest`）は .py の変更で変わる |
| エンジン | 変えない。版・`behavior_digest`・P1/P3 の basis・instrumentation は同じ |
| 判定の規則 | 変えない（8 のまま）。judge は新しいファイルを読まない |

- 旧計画・旧記録: 形式 6 以前の計画は、今と同じく再開しません。旧記録をあとから取得した inputs で埋めたり、過去の候補を取得済みとしたりしません。旧記録の集計は、前回の調査のとおり「カード不明」のままです。
- 停止コードの取得（検証者用の診断の追加）は、エンジンの変更が要るので別の単位です。

**段階**:

1. 実装と関連テスト（A1〜A10。runner・prestop・batch の単体と、既存の短い固定テスト・v2_repeat の指紋）
2. 初回の限定バッチ（既存の固定デッキ・方式で数局。計画・予算・seed はその単位で決める）
3. 内訳の調査の更新（新しいバッチの記録だけで、カード別の表を作る。旧記録は変えない）

## 9. 採用の判断が要る事項と推奨値

| 事項 | 推奨 | 別の選択 |
|---|---|---|
| 機能の採否 | 採る（エンジンを変えずに、最大の不明点を減らせる） | 採らない（不明のまま） |
| 対象 | 範囲の外の理由が `processability:unresolved_ruling` の候補（種類で絞らない） | 3 種類だけ |
| 既定 | 無効。計画で明示的に有効 | — |
| 上限 | 256 要求・16 KiB・1 MiB（局ごと） | より小さく（例 128） |
| 記録の失敗 | 局は続け、`failed` ならその局のあとでバッチを止める | 止めない（集計で示すだけ） |
| 変異（V3-1）との組み合わせ | しない | する（記録の行との対応を別に設計） |
| 版 | 計画・完了の形式 7・`TOOL_VERSION` 11 | — |

## 10. 失敗・修正・再実行・未確認

- この単位の作業の記録は証跡の `commands.txt` にあります。
- 未確認（実装・実測の単位で確かめる）:
  - 記録用の要求の時間・メモリ（実測していない）
  - 取っ手を捨てる経路（`_purge`）に実際に入らないこと
  - 範囲の中が空で止まる取得に、未裁定の候補が出る頻度（保存済みの記録には、その取得の候補の応答が残っていない）
  - `use_stadium` の入力のない候補（選ばせない効果）の頻度

## 11. 実装の結果（2026-11-15。TOOL_VERSION 11・計画と完了の形式 7）

基点は `1850b4c`（この設計のコミット）、作業はブランチ `claude/prestop-record-impl`・worktree `C:\dev\kyuura-engine-lt31` です。設計の推奨案をそのまま採りました。エンジン・方策・判定の規則・データは変えていません。

### 11.1 変えたもの

| 箇所 | 内容 |
|---|---|
| `tools/verification_ai/prestop.py`（新しい） | 記録器 `PrestopRecorder`、計画の設定 `plan_setting`・`setting_problems`、照合 `reconcile`・`excluded_by_kind` |
| `runner.py` | 引数 `prestop`（変異 `negative` との併用は `ValueError`）。`_episode_loop` の `_scope`・`metrics.fetch` の直後に `_prestop_fetch`（範囲が空の停止と方策の選択の前）。記録用の要求は `request(endpoint, "inputs", game=…, revision=…, candidate=…)` の 1 か所だけ |
| `batch.py` | 計画の項目 `prestop_inputs`（無効も明示。plan.sha256 に入る）、`load_plan` での設定の照合、`required_files`（有効なら `prestop/inputs.jsonl`・`prestop/summary.json`）、局の要約 `prestop`・`prestop_problems`、停止方針 `on_prestop_problem`、`verify_complete` の照合、集計 `prestop` と量 `game_complete_prestop`、CLI の `--prestop-inputs`・`--no-prestop-inputs`（どちらかが必須） |
| 版 | 計画 `kyuura-vai-batch-plan/7`・完了 `kyuura-vai-batch-complete/7`・`TOOL_VERSION` 11。判定の規則 8 は同じ |

- 通常の経路の再利用: 範囲の外の候補は方策に選ばれないので、通常の経路でその候補の inputs は取られません（構造上、再利用元はない）。選ばれた候補の一部の選択肢だけが未裁定の場合は、既存の actors の `inputs` の記録をそのまま使います（新しい記録をしない）。

### 11.2 件数の定義と照合式（`prestop/summary.json`。局ごと）

- `offered`（対象の候補の提示の延べ）・`offered_by_kind`・`keys`（一意な鍵）・`repeats`（同じ鍵の 2 回目以降）
- 鍵ごとに 1 つ: `no_stages`・`attempted`（`ok`・`withheld`・`refused`・`contract_unknown`・`error`・`oversize` のどれか 1 つ）・`skipped_fetch_cap`・`skipped_bytes_cap`・`skipped_after_failure`
- 保存: `rows`・`rows_bytes`（`prestop/inputs.jsonl` の実際の UTF-8 のバイト数。改行をふくむ）・`unsaved_bytes_cap`・`unsaved_failure`
- `seconds`（記録用の要求の合計。局の単調時計・バッチの累積時間の内側）・`fetches`（候補の取得の回数）・`capped`・`status`（`complete`・`capped`・`failed`）・`failure`・`counts_complete`

照合式（`prestop.reconcile`。完了の照合・テストで同じ関数）:

1. `offered == keys + repeats`、`offered == Σ offered_by_kind`
2. `keys == no_stages + attempted + skipped_fetch_cap + skipped_bytes_cap + skipped_after_failure`
3. `attempted == ok + withheld + refused + contract_unknown + error + oversize`
4. `rows == attempted − unsaved_bytes_cap − unsaved_failure`、`rows_bytes ==` ファイルの長さ・行の数 `== rows`・`rows_bytes ≤ max_rows_bytes`、`attempted ≤ max_fetches_per_game`
5. `status` は `failure` と `capped` から決まる値と同じ
6. 局: `offered_by_kind[k] == result.json の metrics.kinds[k].excluded["processability:unresolved_ruling"]`（記録の数え上げが途中で失敗した `counts_complete: false` の局は除き、その局は `failed` で止まる）
7. バッチ: 局ごとの要約を 1 回ずつ足す（同じ単位の数どうしだけ。種類の集合を 1 回だけたどる）

上限（局ごと。計画の `prestop_inputs.limits`。既定値より大きくできない）: 要求 256 回・応答 1 回 16,384 バイト（JSON の UTF-8）・`prestop/inputs.jsonl` 1,048,576 バイト。設計の `max_bytes_per_game` は、対象が inputs.jsonl だけであることを名前で示すため `max_rows_bytes` にした（値は同じ）。

- 要求の前に、本文のない行すら入らないと分かれば要求しない（`skipped_bytes_cap`）
- 応答が 16 KiB を超えたら本文を保存せず、量と理由（`oversize`・`response_too_large`）だけを残す
- 行が 1 MiB を超えるなら書かず（`unsaved_bytes_cap`）、それ以降は要求しない。別のファイルへ逃がさない
- `summary.json` は固定の件数・状態・時間・失敗だけ（1 MiB の対象外。候補別の一覧は入れない）。2 つのファイルとも、既存のバッチの証跡の量（局のファイルの合計）に入る

### 11.3 失敗・停止・再開

- withheld・refused（stale・`CLIENT_GAME_UNAVAILABLE` をふくむ）・形式の不正: 記録して続ける。candidates を取り直さない。通常の anomalies・停止・judge には入れない
- 通常の例外: 記録の失敗。その局の記録をやめ、対戦は既存の経路で続ける。要約の状態は `failed`。完了のマーカーに `prestop:failed:…` の停止の理由が付き（`complete_with_stop`）、その局を保存したあとでバッチを止める（`stopped_policy`）。停止の承認は自動で解除しない
- `MemoryError` は通す。`KeyboardInterrupt`・`SystemExit` は捕まえない（既存の未完了の試行の扱い）
- 上限の到達（`capped`）は止めずに、完了のマーカーの note に `prestop:capped:…` を残す
- 有効な計画では、2 つのファイルを必須ファイル・ハッシュの表・完了のマーカーに入れる。完了の照合で、`summary.json` とマーカーの要約の一致、照合式の計算し直し、ファイルの欠け・破損を確かめ、合わない局を完了として採らない
- 形式 6 以前の計画は再開しない（移行・上書きしない）。旧記録へ後から inputs を足したり、取得済みと扱ったりしない

### 11.4 非干渉と時間

- 本物の runner の固定の短い局（固定デッキ・方式 uniform-stage・seed 12・80 操作。既存の `v2_repeat` の固定値と同じ局）で、有効と無効を比べ、次が同じことを確かめた: 行動の列と契約の列の指紋、各試みの入力と選んだ理由、方策の乱数の消費、状態と乱数の確認値（`checks`）、終わり方・counters・anomalies・metrics・coverage、actors の記録（取っ手の値だけを置き換えて比べた）、通常の要求の種類・順・候補
- 同じ局で、記録用の要求の前後で、取っ手の保持の数・更新の箱の長さ・状態のオブジェクト・ログの長さ・`ActionHost._purge` の呼び出しの数が同じで、応答はすべて `ok`・`refetch_required: false`（古い取っ手の経路に入らない）
- 実時間: 記録用の要求の時間は局の単調時計（`Limits.seconds`）とバッチの累積時間の内側で、要約の `seconds` に残る。比べた局は時間の上限（60 秒）に十分な余裕があった。**上限の近くで終わる局では、実時間の増加で終わり方が変わりうる**ので、「有効・無効で終わり方まで常に同じ」とは保証しない

### 11.5 識別（変更の前後。`identity.py`）

| 項目 | 前（`1850b4c`） | 後 |
|---|---|---|
| エンジンの版・behavior_digest・instrumentation_digest | 0.185.0・`a3b65dbe…`・`d3436748…` | 同じ |
| P1・P3 の basis | `06ec1daf…`・`6a8287f9…` | 同じ |
| 判定の規則 | 8 | 8 |
| TOOL_VERSION・道具の識別 | 10・`7b56ed5a…`（26 ファイル） | 11・`6e0616cc…`（27 ファイル） |
| 計画・完了の形式 | 6・6 | 7・7 |

### 11.6 テスト（1 モジュールずつ別のプロセス。UTF-8 の出力・終了コード・JUnit は証跡の `scripts/tests/`）

| 実行 | モジュール | 件数 | 結果 |
|---|---|---|---|
| 新しいテストの 1 回目（`attempt1_new`） | `test_verification_ai_prestop` | 22 | 失敗 1（テストの誤り: actors の記録を比べるとき、実行ごとに乱数で発行される取っ手の値 `game`・`revision` を置き換えていなかった。製品のコードは変えていない） |
| 新しいテスト（直したあと） | 同じ | 22 | 成功 |
| 関係する既存のテスト（batch・判定・明示リスト・ER9・P1・P3・観測・P6 の受理・reach・reach 版 2・v2_repeat の指紋） | 11 | 220 | 成功 |
| runner を使う既存のテスト（P6・U-R3a・V0〜V3-3・0.176〜0.179 の追従） | 11 | 156 | 成功 |

- 既存のテストで期待を直したのは版の値だけです（`TOOL_VERSION` 10 → 11、形式 6 → 7。旧の期待は注記に残した。er9・P1・P3・reach・reach 版 2）。計画の CLI のテスト（明示リスト）は、`--no-prestop-inputs` を足しました（記録の有無の明示が必須になったため）。
- `v2_repeat` の行動の指紋の固定値は変えていません。有効にした本物のバッチの局でも、同じ固定値と一致しました。
- 新しいテストの内容: 対象の選定（候補全体だけ・段なし・選択肢の一部だけの候補を対象にしない）、重複（取っ手だけが違う取り直し・中身が違う・主体が違う）、上限（256 回、16,384 と 16,385 バイト（マルチバイトの文字で作った応答）、1 MiB の境界の行の実バイト数と改行、本文つきの行が入らないときに書かずに止める）、失敗（stale・`CLIENT_GAME_UNAVAILABLE`・withheld・形式の不正・通常の例外・`MemoryError`・`KeyboardInterrupt`・`SystemExit`）、照合式の不一致の検出、計画の設定の拒否、変異との併用の拒否、本物の runner の非干渉（11.4 節）、本物のバッチ（保存・必須ファイル・ハッシュ・完了の照合・破損と欠けの検出・集計・公開の出力にカード ID が出ない・無効の計画は今と同じ・記録の失敗でその局のあとに止まり承認なしに再開しない・再開で完了局の記録が変わらない・旧形式と不正な設定の計画を再開しない）、方策・行動生成・判定・指標が記録を読まないこと
- 構築盤面と短いテストは、新しいバッチの実績に数えていません
- 実行していないもの: 全体テスト・GUI・E2E・新しい対戦のバッチ・seed の探索・旧記録への judge・replay の当て直し

### 11.7 初回の限定バッチに残る確認

- → 2026-11-15: 初回の小規模確認バッチを設計した（未実行）: [初回の小規模確認バッチの計画](prestop-first-batch-plan.md)

- 照合式 6・7 を、新しいバッチの局で確かめる（前回の 2 倍の誤りを繰り返さない）
- `refused`・`contract_unknown`・`error`・`oversize`・上限の到達が 0 か、0 でないなら件数と理由
- 記録用の要求の時間の合計と、累積時間に対する割合。時間の上限の近くで終わった局の有無
- カード別の出現の表（内訳の調査の更新は別の単位。旧記録は変えない）
- 未確認のまま: 範囲の中が空で止まる取得での未裁定の候補の頻度、入力のない `use_stadium` の候補の頻度、長い局・reach の方式での時間とメモリ
