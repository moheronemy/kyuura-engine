# v0.153: 完全な再現用記録の収集・読み書き・構造の検証（U3）

[仕様案](diagnostics-replay-api-design.md)の U3 を実装した版です。v0.152 のアダプタ（`adapter.start_game`・`HostedGame`）の上に、対戦の開始から操作の送信までを一体で記録する収集器と、記録の JSON の読み書き・構造の検証を加えました。エンジンの処理（受理の条件・状態・乱数・ログ・観測）は変えていません。`kyuura_engine` の版は 0.153.0 です。

**U3 の検証の成功（`structure_valid`）は、記録をエンジンで再実行して確認値と一致したことを意味しません。** 再実行して照らすのは U4（未実装）です。記録の JSON の読み取りは記録の形式の読み取りで、ゲームの状態の JSON からの復元（未実装）とは別の機能です。

## 1. 基点と採用

- 基点: `7a0ee0f`（v0.152 の最後。`origin/claude/diagnostics-u1-u2`。`origin/main` の `8d4beff` はその祖先）。作業ブランチ `claude/replay-record-u3`
- 利用者の採用（2026-11-06。仕様案の JSON の `adoptions` の `ADOPT-U3`）: U3 の実装と、次の 4 つの方針だけ。スナップショットの形式（D-SNAPSHOT-BASE）と停止状態のスナップショット（D-HALT-SNAPSHOT）は保留のまま
  1. 実装の識別: エンジンの版に加え、挙動に関係するソースと同梱データの内容のハッシュ。Git のコミットは補助の情報（D-IMPLEMENTATION-ID）
  2. 実行環境: 再現の保証を、対応する Python の実装・版に限る。OS・パス・改行など意味に影響しない違いまで無条件に非対応にしない（D-RUNTIME。仕様案の推奨の「拒否しない」ではない）
  3. 確認値の密度: 受理した操作ごとに、状態と乱数の確認値（D-CHECK-DENSITY）
  4. 形式の版: 再現用記録の形式の版を独立して設け、診断の形式・状態の形式・規約集合の版は参照する。ほかの保留中の形式に一括で当てはめない（D-VERSIONS は記録の形式の部分だけ）
- 既に採用済みの方針（v0.152 まで）: 受理した操作が再現の入力、拒否した操作は任意で記録する確認の対象、コイン・乱数などの観測は確認値、方策を再実行しない、完全な記録を見る人に渡さない、対戦後も公開の範囲を広げない
- しないこと: 再実行と照合（U4）、閲覧用記録（U5）、状態の JSON からの復元、停止からの再開、合法手の一覧・AI・画面・通信、続行規約

## 2. 公開した API（`kyuura_engine.replay_record`）

| もの | 内容 |
|---|---|
| `ReplayCollector.start(deck0, deck1, seed, *, conventions=None, game_id=None, record_rejections=True, operation_id=None, include_git=True)` | `adapter.start_game` で対戦を始め、(収集器, 開始の `CommandResult`) を返す。開始が拒否・処理できなければ収集器は None。既定のカードプールとルールの組だけ（ほかは記録から作り直せないので受け付けない） |
| `collector.submit(command, *, submitter=None, operation_id=None)` | `HostedGame` で操作を送り、結果から記録の 1 行を作って、`CommandResult` を返す。操作と結果を別々に渡す入口はない |
| `collector.close()` | 記録を閉じて `ReplayRecord` を返す（終局でなくても閉じられる。閉じた記録から再開する機能はない） |
| `collector.record()` | 閉じる前の記録（`end` がない。検証すると `incomplete`） |
| `collector.view(viewer)`・`collector.state` | 見る人の観測（`observe`）と、ホストの中だけで使う今の状態 |
| `dumps_record(record)`・`loads_record(text)` | 記録の JSON の書き出し（鍵の順を決めた 1 行）と読み取り（JSON の値だけ。pickle などに変えない） |
| `validate_record(record, *, check_support=True)` | 構造の検証。`RecordReport`（`status`・`problems`・`complete`・`end_state`・`replay_verified`（いつも偽）） |
| `support_problems(data)` | この実装・環境・規約集合で扱えるかだけを調べる |
| `implementation_identity(root=None)`・`runtime_identity()`・`state_check(state)`・`checks(state)` | 識別と確認値の計算 |

収集器の約束:

- `ReplayCollector` は `start` でだけ作る（コンストラクタを直接呼ぶと `TypeError`）。途中の状態から収集を始める入口はない
- 拒否した操作は `record_rejections` が真のときだけ記録する。省いても、受理した操作の順は `accepted_index` で決まる
- 処理できない結果（failed: 内部エラー・状態の不整合）を記録したら収集を止める（`end.state` が `aborted`）。そのあとの操作・閉じたあとの操作は `CollectorStoppedError`。未確認の状態から黙って続けない
- 記録の連番（`seq`）と `operation_id`（ホストが付ける）は別のもの。`operation_id` は任意で、記録の中で重ならないこと

## 3. 記録の形式（`kyuura_replay_format` 1）

```
{ "kyuura_replay_format": 1,
  "header": { "game_id", "engine", "runtime", "dependencies", "convention_set", "formats", "initial", "rejections_recorded", "start" },
  "operations": [ { "seq", "operation_id", "actor", "submitter", "segment", "command", "answers_decision"?, "outcome", "status",
                    "accepted_index"?（受理だけ）, "check"?（受理だけ）, "diagnostic"?（拒否・失敗だけ） } ],
  "end": { "state": "closed" | "aborted", "operations", "accepted", "status", "final_check", "segments" } | null }
```

入力・確認値・補助の情報の区別:

| 種類 | 項目 | 使い方 |
|---|---|---|
| 再現の入力 | `header.initial`（デッキリスト 2 つ・seed・ルールの組・規約集合・カードプール）、受理した操作の `command`（`accepted_index` の順） | U4 が `new_game` とコマンドの列で状態を作り直す。先攻はジャンケンの結果の操作（`report_janken_result`）として操作の列に入る。切り直しは seed の乱数で決まる |
| 扱えるかの条件 | `header.engine`（版・`behavior_digest`）・`runtime`・`dependencies`・`convention_set`・`formats` | 合わなければ unsupported（5 章） |
| 確認値 | `header.start.check`、受理した操作の `check`、操作の `outcome`・`status`・`diagnostic`、`end` | 照らすための値。再現の入力にしない。乱数の確認値を、再現のときに各操作の前へ戻す使い方をしない（誤った実行でも一致させてしまう） |
| 補助の情報 | `game_id`・`operation_id`・`actor`・`submitter`・`segment`・`answers_decision`・`engine.git_commit`・`instrumentation_digest` | 対応付け・調査のため |

`initial` の `seed` だけでは足りません。`new_game` の入力は、デッキリスト 2 つ・seed・ルールの組（`rules`）・カードプール（カードデータと効果の登録表）・規約集合で、記録はすべてを持ちます（カードプールとルールの組は既定のものだけ。`dependencies` にカードデータの写しの元と効果の登録表の id を書く）。

確認値（受理した操作ごと。方式は `header.formats.check_methods`）:

- `state`（`state-export-35-sha256/1`）: `state_to_dict(state, format_version=35)` から `engine_version` を除き、鍵の順・区切りを決めた JSON（UTF-8）の sha256。形式 35 の書き出しが状態から落とすのは、乱数の状態そのもの（指紋 `rng_state_sha256` は入る）・カードの定義（カード id とカードデータから決まる。カードデータは実装の識別に入る）・デッキリスト（見出しの `initial`）・`pending_moves`（コマンドの境界ではいつも空。不変条件）・規約集合のオブジェクト（`convention_set` の記録として入る）。`engine_version` は見出しにあるので除く（lockstep の `DIGEST_EXCLUDED` と同じ扱い）
- `rng`（`python-random-getstate-sha256/1`）: `rng.rng_fingerprint`（`random.Random.getstate()` の repr の sha256）
- `log_length`・`segment`・`status`・`decision`（id・種類・決めるプレイヤー）・`halt`（停止のコード）
- 方式を変えたら方式の名前を変える（違う方式の値を同じ値として比べない）。lockstep の記録の指紋（形式 9 か 35 の sha256 の先頭 32 文字）とは別の値で、lockstep の記録をこの形式として読まない

対戦の終局と記録を閉じることは別です。`end.status` は対戦の今の状態（`game_over`・`halted`・`awaiting_decision` など）で、`end.state` は記録の閉じ方（`closed`・`aborted`）です。サドン・デスの区間は、操作の `segment`（操作の前の区間）、受理した `start_sudden_death` の `check.segment`（1 つ進む）、`end.segments`（区間の番号と始まった `seq`）で表します。

## 4. 実装・データ・環境の識別

- 範囲: パッケージ `kyuura_engine` の中の `*.py`（`__pycache__` を除く）と `data/*.json`。エンジンの処理・効果の登録・ルールの組・解決の基盤（`resolution/`）・カードデータ（`kyuura_cards.json`）・規約集合の記録（`convention_records.json`）など、実行時に読むものはすべてこの中にある（`load_card_pool` は同梱の写しを読む。kyuura の木は実行時に読まない）。挙動に関わらないかもしれない同梱データ（`research_links.json` など）も、外して見落とすより入れる側に倒した（変わると識別が変わり、U4 は unsupported を返す）
- 分け方: `behavior_digest` はゲームの挙動の識別（上の範囲から記録と診断の部品を除いたもの）。`instrumentation_digest` は記録と診断の部品（`adapter.py`・`diagnostics.py`・`replay_record.py`・`data/diagnostic_catalog.json`）。診断の表を直してもゲームの挙動の識別は変わらない。扱えるかの判定は `behavior_digest` で行い、`instrumentation_digest` は調査の補助
- そろえ方（`kyuura-package-files-sha256/1`）: ファイルはパッケージの中の相対パス（`/` 区切り）の辞書順。中身は UTF-8 として読み、先頭の BOM を除き、改行（CRLF・CR）を LF にそろえてから sha256。全体は「パス・中身の sha256」の並びの sha256。チェックアウトの場所・改行・Git の有無によらない。コメントだけの変更も別の識別になる（内容のハッシュなので、意味の違いを判定しない）
- 規約集合の照合値（`ConventionSetIdentity.digest`）とは役割が違う（そちらは規約の意味の内容の識別）。既存の指紋（lockstep の追跡ファイルの sha256、形式 35 の書き出し）は流用していない
- Git のコミット（`engine.git_commit`）は補助の情報で、識別にも扱えるかの判定にも使わない（`include_git=False` なら書かない）
- 実行環境（`runtime`）: Python の実装（`platform.python_implementation()`）と版（major・minor・micro）、乱数の方式（`rng.RNG_FORMAT` と `getstate` の版）。扱えるのは、実装・major・minor・乱数の方式が同じとき。micro の違い・OS・パスは記録せず、非対応にしない
- ハッシュは内容を見分けるための値で、署名・改ざんの防止・作った人の証明ではない

## 5. 読み取りと構造の検証

`loads_record` は JSON を読むだけです: 64 MiB を超える入力、深さ 64 を超える入れ子、重なった鍵、`NaN`・`Infinity`、最上位が辞書でないもの、UTF-8 でないもの、JSON として読めないものは `RecordFormatError`（`code` と場所だけを持ち、入力の値を文に入れない）。リポジトリにほかの入力の大きさの決まりはないので、記録の読み取りだけの最小の上限です。

`validate_record` の結果（重い順の 1 つ。`problems` はすべて）:

| status | 意味 | 例 |
|---|---|---|
| `malformed` | 形式として不正 | 必須の項目の欠け（初期の条件の不足を含む）、知らない結果の種類、確認値の欠け・形の誤り、知らない最上位の項目、形式の版がない |
| `inconsistent` | 内容・順序の矛盾 | 連番の欠け・重なり・順の違い、`accepted_index` の順、`operation_id` の重なり、拒否を記録しない記録の拒否の行、拒否として記録した内部エラー・状態の不整合、拒否・失敗の行の確認値、終局・停止のあとの受理、延長戦の開始待ちでの開始でない受理、開始でない区間の変化、決定待ちのあとの答えでない受理・違う決定への答え、見出しと終わりの不一致（数・状態・最後の確認値・区間）、`initial` と `convention_set`・`dependencies` の不一致、失敗のあとの操作 |
| `incomplete` | 途中で切れている | `end` がない（閉じる前の記録・書き込みの途中で切れた記録） |
| `unsupported` | 読めるが、この実装・環境・規約集合では扱えない | 知らない形式の版、`behavior_digest`・エンジンの版の違い、Python の実装・major・minor・乱数の方式の違い、状態の書き出しの形式・確認値の方式・診断の形式の違い、知らないルールの組、カードデータ・効果の登録表の違い、登録と合わない規約集合 |
| `structure_valid` | 構造の検証に通った | 再実行で一致したことではない（`replay_verified` は偽） |

保証すること: 記録の形・連番・前後の状態の流れ（決定待ち・終局・停止・延長戦の開始待ち・区間）・見出しと終わりの一致・この実装で扱えるか。保証しないこと: 記録のコマンドを送ったら本当にその結果・確認値になるか（U4）、確認値が正しく計算されたか、記録がホストの収集器で作られたこと（記録の辞書は手で作れる。途中から作った記録や確認値を書きかえた記録も、形と流れが合えば `structure_valid` になりうる。見分けるのは U4 の再実行）。

## 6. 情報境界

- 完全な記録は検証者用（seed・デッキリスト・すべての操作・確認値・診断の元のコードを含む）。`view_for` の結果・観測とは別のもので、記録を見る人に渡さない。読み取った記録を、そのまま画面の応答にしない
- `ReplayRecord` の repr・文は形式の版・操作の数・閉じ方だけ（seed・デッキリスト・確認値を出さない。ログに出しても中身が漏れないように）。読み取りの誤りの文も入力の値を含まない
- 記録は拒否・失敗の診断を、識別・分類・元のコードだけで持つ（例外の生の文・traceback は入れない）
- ハッシュ（確認値・識別）だけなら公開してよいとは考えない（候補の少ない秘密は、候補を当てはめて確認値と比べれば確かめられる。仕様案 5.2 節）
- 収集器の `view` は `observe` そのもの。`CommandResult.view_for` の結果は v0.152 と同じ（記録の項目を持たない）

## 7. 検証（限定）

`tests/test_replay_record_v0_153.py`（盤面: new_game からの合法な操作の列。ピカチュウのデッキの方策（seed 9 はサドン・デスから延長戦、seed 0 は終局）、たねポケモン 1 枚のデッキ（seed 1 は準備で停止）。記録をわざと壊す確かめ、例外を差し込む確かめ）:

- 往復と検証: 閉じた記録の JSON の往復（同じ文字列にもどる）、閉じる前の記録は incomplete
- 内容: 初期の条件・規約集合・開始の確認値（`new_game` の状態と同じ）、連番と受理の順、決定待ち・延長戦の開始待ち・答え、延長戦の区間の境界、拒否の記録の有無（省いても受理の列と確認値は同じ）、不正な答えで状態・乱数・ログが変わらない、終局・閉じたあとの操作、準備で停止した記録を閉じる、開始の拒否、途中の状態から収集器を作れない、収集器を通しても `apply_command` と同じ状態・確認値
- 失敗: 内部エラーで収集器が止まり、記録は aborted（生の文を記録しない）
- 壊した記録: malformed・inconsistent・incomplete・unsupported のそれぞれ（5 章の表の例）。micro の版の違いは扱える。読み取りの誤りに入力の値が入らない
- 識別: 場所・改行（CRLF・BOM）・Git の有無で同じ、カードデータ・エンジンのソースの変更で変わる、診断の部品の変更はゲームの挙動の識別を変えない、規約集合の照合値と別の値
- 境界: repr に秘密の値がない、見る人の結果に記録の項目がない
- 既存の 3 つの集合: 記録の識別は登録の値のまま、構造の検証に通る

`next` について: 開始の結果の `next`（例: `place_starting_pokemon`）は、次に受け付けうる操作の種類だけで、合法手の一覧ではありません（v0.152）。

## 8. 利用例（実際の出力。ハッシュの一部は省略）

収集を始め、操作を送り、拒否を含めて記録を閉じる:

```python
from kyuura_engine.replay_record import ReplayCollector, dumps_record, loads_record, validate_record

collector, started = ReplayCollector.start(deck0, deck1, 9, game_id="g-9", operation_id="start")
started.next            # (NextAction('place_starting_pokemon', None),) 次の操作の種類。合法手の一覧ではない
collector.submit(PlaceStartingPokemon(0, 19, (14, 1)), submitter=0, operation_id="op-1")   # accepted
collector.submit(EndTurn(1), submitter=1, operation_id="op-2")                             # rejected（WRONG_PHASE）。拒否も記録する
record = collector.close()
```

記録の操作の行（受理と拒否）と終わり:

```json
{"operation_id": "op-1", "actor": 0, "submitter": 0, "segment": 0, "command": {"type": "place_starting_pokemon", "player": 0, "active": 19, "bench": [14, 1]}, "outcome": "accepted", "status": "in_progress", "accepted_index": 1, "check": {"state": "99003567…be367", "rng": "fd2e41d2…35312", "log_length": 6, "segment": 0, "status": "in_progress", "decision": null, "halt": null}, "seq": 1}
{"operation_id": "op-2", "actor": 1, "submitter": 1, "segment": 0, "command": {"type": "end_turn", "player": 1}, "outcome": "rejected", "status": "in_progress", "diagnostic": {"diagnostic_id": "WRONG_PHASE", "category": "invalid_input", "engine_code": "WRONG_PHASE"}, "seq": 2}
{"state": "closed", "operations": 2, "accepted": 1, "status": "in_progress", "final_check": {"state": "99003567…be367", "rng": "fd2e41d2…35312", "log_length": 6, "segment": 0, "status": "in_progress", "decision": null, "halt": null}, "segments": [{"index": 0, "start_seq": 0}]}
```

書き出し・読み取り・構造の検証と扱える範囲:

```python
text = dumps_record(record)              # 検証者の保管場所へ（見る人に渡さない）
back = loads_record(text)                # RecordFormatError なら読めない
report = validate_record(back)
report.status, report.complete, report.end_state, report.replay_verified
# ('structure_valid', True, 'closed', False)  ← 再実行で一致したことではない
repr(back)                               # ReplayRecord(format=1, operations=2, end='closed')
```

Python の minor の版が違う記録（`runtime.python_version` の 2 つ目を書きかえた例）:

```python
validate_record(changed).status          # 'unsupported'
[(p.kind, p.code, p.path) for p in validate_record(changed).problems]
# [('unsupported', 'runtime_differs', '$.header.runtime')]
```

## 9. U4 への引き継ぎと残る判断

**v0.154 の訂正**: 下の 1 つ目の項目と 3 章の表の「受理した操作の `command`（`accepted_index` の順）」は、再現の入力が受理した行のコマンドであることの説明で、送る順は`seq` の順（拒否・失敗の行を含む記録の行の順）です。U4（[replay-run-v0.154.md](replay-run-v0.154.md)）は、受理した行だけを先に送ってから拒否を確かめることはせず、記録の行を `seq` の順に送ります。`accepted_index` は受理の連番の照合に使います。下の記述は v0.153 の時点の記録として残します。

- U4 の入力: `header.initial` で `new_game` を作り、`outcome` が `accepted` の操作を `accepted_index` の順に `adapter.submit`（または `apply_command`）で送る。各操作のあとに `checks` を計算し、記録の `check` と比べて、最初に違った操作（`seq`・`accepted_index`）と項目（`state`・`rng`・`log_length`・`segment`・`status`・`decision`・`halt`）を返す。拒否の行を含む記録なら、同じ状態に送って、同じ診断の識別・元のコードの拒否になり状態が変わらないことを確かめる。失敗の行は、同じ失敗になるかを確かめる（成功に数えない）
- 扱えるかは U4 の最初に `support_problems` で確かめる（unsupported なら再実行しない）。乱数を各操作の前へ戻さない
- 未確認: 異なる OS で同じ確認値になるか（改行・パスは識別から除いたが、実行の結果は確かめていない）、文字列のハッシュの乱数化（`PYTHONHASHSEED`）が確認値に影響しないか（形式 35 の書き出しは鍵の順を決めて比べるが、集合の並びに依る値がないことは確かめていない）
- 残る判断: D-SNAPSHOT-BASE・D-HALT-SNAPSHOT（保留）。閲覧用記録（U5）の版の決め方は、D-VERSIONS の採用の範囲に入れていない

## 10. 検証の結果

限定検証だけを実行した（全体テスト・全 108 組・4,356 局・lockstep・ストレス実行はしていない）。終了コードは確かめの本体から。

- `tests.test_replay_record_v0_153`: 25 テスト OK
- U1・U2 の関係: `tests.test_diagnostics_adapter_v0_152`（37）・`tests.test_diagnostics_replay_api_design`（20）・規約集合の識別と照合値（`test_conventions_v0_142` の `IdentityTest`・`RecordsTest`）: OK。
  期待を変えたテスト 2 つ（目的は同じ）: v0.152 の `test_spec_records_only_the_adopted_policies` は、採用した判断事項の全体ではなく v0.152 の採用の記録（`ADOPT-U1-U2`）の中身を確かめる形にした
  （v0.153 の採用で全体が増えた）。仕様のテストの `test_coin_as_replay_input` は、記録の項目からコインの結果の行がなくなった（コインは状態の確認値に入る）ので、壊した行を自分で加えて確かめる形にした
- 版のテスト（`test_preset_decks_v0_20` の `test_version`）と、変えた文書（README・実装状況・データの来歴）を読む既存のテストのメソッド 16 件: OK
- 生成物の `--check`: `build_diagnostic_catalog`・`build_diagnostics_replay_api_design`・`build_stop_policy_classification`・`build_play_policy_family_plan`・`build_convention_records`・
  `check_implementation_assumptions`・`check_normalization_revalidation` のすべてが終了コード 0（停止の方針の台帳・同梱の規約集合の記録・診断のコード表は変えていない）
- ruff 0.17.2（基点と同じ版・設定）: 新しいファイルに指摘なし。新しい抑制（`noqa`）はない（テストの lambda の代入は関数にした）。`test_preset_decks_v0_20.py` の指摘は基点と同じ 6 件
- `check_implementation_assumptions.py --sites`（基点の木と比べた差）: 版のテストの行に版の注記を足して識別が変わった 1 件（新しい 1・消えた 1。件数は同じ）。実装上の仮定ではない。文面は変えていない
- 収集器を通しても、`apply_command` で同じ操作の列を送った状態・確認値と同じ（テスト）。3 つの集合の識別は登録の値のまま
