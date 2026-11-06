# v0.155: 閲覧用記録（U5）と、U4 の説明の整合

[仕様案](diagnostics-replay-api-design.md)の U5 を実装した版です。本人・相手・観戦者の 1 人が、その時点で知ることのできた情報だけを持つ対戦の記録（閲覧用記録）を作ります。完全な再現用記録（v0.153）とは別の用途・形式（`kyuura_view_format`）です。エンジンの処理は変えていません（`state.py` の注釈の訂正だけ。1 章）。`kyuura_engine` の版は 0.155.0 です。

閲覧用記録から対戦を再実行すること・状態を復元することは保証しません。閲覧用記録を閉じても、そこから対戦を再開する機能はありません。

## 1. 基点と U4 の説明の整合

- 基点: `a8ad207`（v0.154 の最後。`origin/claude/replay-run-u4`。`origin/main` の `8d4beff` はその祖先）。作業ブランチ `claude/view-record-u5`
- U4 の報告の説明を、実際の差分（`git diff 6d659d0 a8ad207 -- kyuura_engine`）と照らした（コミット `006a58c`。U5 とは別にした）:
  - 「書き出しの決定に `resume`・`context` が入る」は、**既にあることを確かめただけ**（`serialize.py` は v0.154 で変えていない。v0.2a の `ab8fc6f` から）。[v0.154 の文書](replay-run-v0.154.md)に追記した
  - 「確認値の方式は変えていない」「エンジン側の差分は版の番号と新しいモジュールだけ」はそのとおり。確認値の方式・既存の記録の確認値の意味は変わらない
  - `state.py` の `pending_moves` の注釈が存在しない不変条件の関数（`engine._pending_moves_problems`）を指していたのを、事実に合わせて直した。エンジンに不変条件は加えていない。U4 の境界の確かめ（`replay_run.boundary_items`）は変えずに残す
- 実装の識別（`kyuura-package-files-sha256/1`）: 方式の決め方（記録・診断の部品は `adapter.py`・`diagnostics.py`・`replay_record.py`・`data/diagnostic_catalog.json` の 4 つ、ほかの `.py`・`data/*.json` はゲームの挙動の側）は変えていない。そのため `replay_run.py`（v0.154）と `view_record.py`（v0.155）はゲームの挙動の側に入る（変えると記録が非対応になる、安全側）。分け方を変えるなら方式の名前を変える（同じ名前のまま中身を変えない）
- 利用者の採用（2026-11-06。仕様案の `adoptions` の `ADOPT-U5`）: U5 の実装と、別の形式の版・各時点の観測から作る・遡って入れない・拒否は本人だけ・seq を出さない・秘密の値を写さない・再実行と復元を保証しない・対戦後も広げない、の方針だけ。スナップショットの形式・停止状態からの再開・D-SNAPSHOT-BASE・D-HALT-SNAPSHOT は保留のまま

## 2. 公開した API（`kyuura_engine.view_record`）

| もの | 内容 |
|---|---|
| `ViewHost.start(deck0, deck1, seed, *, viewers=(0, 1, None), conventions=None, full_record=True, record_rejections=True, game_id=None)` | 対戦を始め、閲覧者ごとの収集を始める（閲覧者は作るときに固定）。`full_record` なら完全な再現用記録も `ReplayCollector` で集める。対戦の実行は U2・U3（`HostedGame`・`ReplayCollector`）に任せる |
| `host.submit(command, *, submitter=None, operation_id=None)` | 操作を送り、`CommandResult` を返す（閲覧用記録には、結果から作った項目を加える） |
| `host.view_record(viewer)`・`host.close()` | 閉じる前の閲覧用記録、閉じた (完全な記録か None, 閲覧者 → 閲覧用記録)。完全な記録は検証者用 |
| `ViewRecorder.attach(viewer, state)` | 対戦の途中（構築した状態を含む）から記録を始める（`origin` は `attached`）。`add(result)` に `CommandResult` を順に渡す |
| `view_records_from_replay(record, viewers)` | 完全な再現用記録から、U4 の検証つきの再実行で作る。(再実行の結果, 閲覧用記録か None)。`succeeded` でなければ None |
| `dumps_view_record`・`loads_view_record`・`validate_view_record` | JSON の書き出し・読み取り（U3 と同じ安全な読み取り）・構造の検証 |

閲覧者の値は 0・1・None（観戦者）だけ（`observe` と同じ）。`"verifier"` などは `ValueError`。検証者の情報（完全な記録・`CommandResult.verifier`）は閲覧用記録から取り出せない。`ViewRecorder`・`ViewHost` のコンストラクタを直接呼ぶと `TypeError`。

## 3. 記録の形式（`kyuura_view_format` 1）

```
{ "kyuura_view_format": 1,
  "header": { "viewer", "role"（player・spectator）, "origin"（new_game・attached）, "engine_version", "convention_set"（id・version・digest）,
              "diagnostic_schema", "own_decklist"（プレイヤーだけ。自分のデッキのカードの組。並びではない） },
  "entries": [ { "n", "kind", "segment", "events"?, "observation"?, "notice" } ],
  "end": { "state": "closed" | "aborted", "entries", "status" } | null }
```

項目の種類:

| kind | いつ | 中身 |
|---|---|---|
| `start` | 収集を始めたとき（最初の 1 つ） | その時点の観測、過去の区間と今の区間の閲覧用ログ、状態の知らせ |
| `update` | 操作が受理されたあと | 新しい閲覧用ログのイベント（区間の番号・ログの位置）、その時点の観測、`view_for` の結果（本人は結果、相手・観戦者は状態の知らせ） |
| `own_rejection` | 本人が送った操作が拒否されたとき（本人の記録だけ） | 本人向けの診断（定型文・識別・分類。コマンドの内容は入れない） |
| `unavailable` | 処理できない結果（内部エラー・状態の不整合）のとき | 一般的な「処理できない」の知らせだけ（本人は定型文の診断）。記録は `aborted` で止まる |

区別して表すもの: 通常の進行（`status` が `in_progress`）、本人への決定の要求（観測の `decision` に選べるもの、`next` が本人の `answer_decision`）、ほかのプレイヤーが決定中（観測の決定の種類・決めるプレイヤー・選ぶ数だけ。`observe` が許す範囲）、受理した結果の停止（`status` が `halted`、`halt` に公開の診断）、終局（`game_over`）、サドン・デスの開始待ち（`sudden_death_pending`）と新しい区間（`segment`）、記録の終わり（`end.state` が `closed`）と中断（`aborted`）。対戦の終局と記録を閉じることは別（`end.status` と `end.state`）。

ログ: 各 `update` は、前の項目のあと新しくログに加わったイベントだけを、その時点の `visible_log` の写しで持つ（毎回全部を持たない）。イベントは区間ごとのログの位置（`log_index`）で並び、重なり・欠けがない。延長戦を始めたとき（区間が変わったとき）は、前の区間のまだ記録していないイベントを、区間が終わったときの見える範囲（`visible_segment_logs`。うらのまま山札にもどった相手のカードの uid を見せない）で持ち、続けて新しい区間のイベントを位置 0 から持つ。

大きさ: 項目ごとに観測をまるごと持つので、ピカチュウのデッキの 1 対戦（約 220 項目）で 1 つの記録が約 2.8 MB（圧縮はしていない）。

## 4. 実行時の収集と、完全な記録からの変換

- 実行時の収集（`ViewHost`）: 信頼されたホストが、操作を送るたびに `CommandResult` から閲覧者ごとの項目を作る。各項目は、その時点の `observe(state, viewer)`・`visible_log(state, viewer)`・`result.view_for(viewer)` を JSON の値として写して固定する
- 完全な記録からの変換（`view_records_from_replay`）: U4 の `replay` に `observer` を渡し、照合に通った開始と各行の `CommandResult` を、その時点で閲覧者ごとの収集器に渡す（最後の状態だけから作らない）。再実行が `succeeded` のときだけ閲覧用記録を返す（`diverged`・`internal_error`・`incomplete`・`recorded_failure` では None）。実行時に集めたものと、同じ完全な記録から変換したものは同じになる（テスト）
- `replay_run.replay` の変更: 任意の `observer` の引数を加えただけ（照合・結果は同じ）

## 5. 閲覧者ごとの情報境界

- 各項目の中身は、既存の `observe`・閲覧用ログ・`view_for` の境界そのもの（新しい見える範囲を作らない）。決定の候補・選ぶ数・`context` などは、`observe` が許さない相手・観戦者の記録には入らない
- 入れないもの（構造の検証が項目の名前で見つける）: `seed`・乱数の状態とその確認値・完全な状態の確認値（`check`・`state_digest`）・デッキリストの並びと相手のデッキリスト（`decklists`）・完全な記録のコマンド（`command`）・生の例外文・traceback・`problems`・検証者用の診断（`engine_code`・`verifier`）・`resume`・`context`・停止の診断用の文・完全な記録の `seq`・`accepted_index`・`operation_id`。ログのイベントの `hidden` の中の名前（隠した項目の名前）は値を持たないので例外として扱う
- `operation_id` は `view_for` の本人の結果から除く（ホストの識別は完全な記録と対応付けられる）
- 実時刻・所要時間は入れない。通信のタイミング（応答の時間）による推測への対策は、この記録の範囲の外（保証しない）
- 自分のデッキリストは、カードの組として並べ直したものだけ（並びは uid の付け方を決めるので入れない）
- 公開してよい識別（規約集合の ID・版・照合値、エンジンの版、診断の形式）は入れる（`observe` と同じ）
- 対戦が終わっても範囲を広げない（記録を閉じるときに何も加えない）

## 6. 拒否・連番・過去の知識

- 拒否は、送った本人の記録にだけ `own_rejection` として入る。相手・観戦者の記録には、行・通知・空の行・連番の欠け・件数の違いのどれも残らない（拒否は状態とログを変えないので、`update` も加えない）
- `n` は、その閲覧者の記録に出した項目だけで 1 から連続する。完全な記録の `seq`・操作の総数・`accepted_index` とは対応しない
- 記録した項目は、その時点の値で固定する（JSON の値の写し）。あとで手札・山札・うらのカードが公開されても、過去の項目へ遡って埋めない。`visible_log` は、うらのカードがおもてになると前のイベントの uid も見せる（v0.67）が、閲覧用記録は記録した時点の写しを持つ。元の状態・ログがあとで変わっても、記録した項目は変わらない（`data` は写しを返す）

## 7. 構造の検証（`validate_view_record`）

結果は U3 と同じ `RecordReport`（`status`: `malformed`・`inconsistent`・`incomplete`・`unsupported`・`structure_valid`。`replay_verified` はいつも偽）。

- 読み取り（`loads_view_record`。U3 の `read_json_object` を使う）: 不正な JSON・重なった鍵・`NaN`・大きすぎる入力（64 MiB）・深すぎる入れ子（64）・最上位が辞書でないもの。誤りの文に入力の値を入れない
- `malformed`: 形式の版がない、知らない最上位の項目、見出し・項目・終わりの項目の過不足、知らない種類、入ってはいけない項目の名前、値の型
- `inconsistent`: 連番の欠け・順、`start` が最初でない、閲覧者と知らせ・観測の閲覧者の不一致、本人でない記録の `own_rejection`、区間の飛び、ログの位置の重なり・欠け、`unavailable` のあとの項目、終わりの数・status・閉じ方の不一致
- `incomplete`: 終わりがない。`unsupported`: 知らない形式の版

保証しないこと: 記録が本当に安全な投影（`observe`・閲覧用ログ・`view_for`）から作られたこと、対戦が正しかったこと、手で作った記録の内容（構造の検証は認証ではない）。閲覧用記録から完全な記録を作れないことは、入れない項目で担保する（構造の検証はその名前を見つける）。

## 8. 利用例（実際の出力。照合値・デッキの一部は省略）

閲覧者を固定して収集を始め、操作と答えを送り、拒否を含めて閉じる:

```python
from kyuura_engine.view_record import ViewHost, dumps_view_record, loads_view_record, validate_view_record

host, started = ViewHost.start(deck0, deck1, 9, viewers=(0, 1, None))   # 閲覧者はここで固定
host.submit(command, submitter=player)                                  # 操作・決定への答え（受理なら各閲覧者に update）
host.submit(EndTurn(0), submitter=0)                                    # 番でない操作: rejected（NOT_YOUR_TURN）
full, views = host.close()                                              # full は完全な記録（検証者用）。views は閲覧者ごと
```

各閲覧者の記録の項目の種類（4 つの受理と 1 つの拒否のあと）:

```
0    ViewRecord(format=1, viewer=0, entries=6, end='closed')     ['start', 'update', 'update', 'update', 'update', 'own_rejection']
1    ViewRecord(format=1, viewer=1, entries=5, end='closed')     ['start', 'update', 'update', 'update', 'update']
None ViewRecord(format=1, viewer=None, entries=5, end='closed')  ['start', 'update', 'update', 'update', 'update']
```

本人（プレイヤー 0）の記録の拒否の項目（相手・観戦者の記録にはない）:

```json
{"n": 6, "kind": "own_rejection", "segment": 0, "notice": {"kyuura_diagnostic_schema": 1, "role": "actor", "viewer": 0, "outcome": "rejected", "status": "in_progress", "stage": "turn_action", "continuable": true, "next": [{"kind": "turn_action", "player": 1}], "diagnostic_id": "NOT_YOUR_TURN", "category": "invalid_input", "subkind": "command", "case_id": null, "case_status": "not_applicable", "message": "今はあなたの番ではありません。", "halt": null, "convention_set": {"id": "CS-KYUURA-CURRENT", "version": 1, "digest": "sha256:…"}}}
```

`next` は次に受け付けうる操作の種類だけで、合法手の一覧ではありません（v0.152）。

相手（プレイヤー 1）の記録の `update` のログ（その時点の閲覧用ログの新しいイベント）:

```json
{"n": 3, "kind": "update", "segment": 0, "events": [{"segment": 0, "log_index": 6, "event": {"kind": "place_starting_pokemon", "turn": 0, "player": 1, "active": 75, "bench": [73, 66, 74, 71]}}, {"segment": 0, "log_index": 7, "event": {"kind": "set_prizes", "turn": 0, "player": 0, "count": 6}}, {"segment": 0, "log_index": 8, "event": {"kind": "set_prizes", "turn": 0, "player": 1, "count": 6}}]}
```

JSON の書き出し・読み取り・構造の検証:

```python
text = dumps_view_record(views[1])          # 閲覧者 1 に渡してよい
back = loads_view_record(text)              # RecordFormatError なら読めない
validate_view_record(back)                  # RecordReport(status='structure_valid', problems=(), complete=True, end_state='closed', replay_verified=False)
```

完全な記録と閲覧用記録の違い:

| | 完全な再現用記録（`kyuura_replay_format`） | 閲覧用記録（`kyuura_view_format`） |
|---|---|---|
| 渡す相手 | 検証者（ホスト） | その閲覧者 |
| 初期の条件 | デッキリスト（並び）・seed・規約集合 | 自分のデッキのカードの組・規約集合の識別 |
| 操作 | すべてのコマンド（拒否も任意で）・`seq`・`accepted_index`・`operation_id` | コマンドを持たない。閲覧用ログと観測と知らせだけ。拒否は本人の記録だけ |
| 確認値 | 状態・乱数の指紋 | なし |
| 再実行・復元 | U4 で再実行して照らせる | 保証しない |

## 9. 検証（限定）

`tests/test_view_record_v0_155.py`（盤面は 1 行目の説明）:

- 収集と往復: 本人・相手・観戦者ごとの収集・JSON の往復・構造の検証、連番、自分のデッキのカードの組
- 拒否: プレイヤー 0 だけが拒否を試した対戦で、相手・観戦者の記録が拒否のない対戦の記録と連番・件数を含めて同じ。本人の記録の拒否の項目を除くと、拒否のない対戦の本人の記録と同じ。拒否の項目は定型文の安全な診断
- 入れない項目がない、完全な記録からの変換が実行時の収集と同じ、検証に通らない（不一致・不完全）記録からは作らない、閲覧者の値の誤り・固定
- 過去の知識: 途中で取った記録の項目が最後の記録でも同じ、手札にあったカードがあとで場・トラッシュに出ても過去の項目は枚数だけ、元の状態を書きかえても・`data` の写しを書きかえても記録は変わらない、途中から始めた記録のログの位置の続き
- 双子（構築盤面）: v0.151 の RB2・はらだいこの宣言で 3 者の記録が同じ。v0.150 の山札をさがす決定まで相手・観戦者の記録が同じで、決定は `observe` が許す範囲（選べるものなし）。本人の記録の決定だけに選べるもの（正当に山札を見る本人は比べない）
- 状態: 受理した結果の停止（ドライアップ seed 0。完全な記録は U4 で再現できる）、終局、決定待ちで閉じる、サドン・デスと 2 つの区間（ログの位置が区間ごとに連続）、内部エラーで aborted（生の文・例外の名前が入らない）、3 つの規約集合
- 壊した記録・読み取りの誤り、U1〜U4 の約束（完全な記録は再現できる・別の形式）

結果は 10 章に書きます。

未確認: マチスの秘策のうらのカードを含む対戦の閲覧用記録（uid の隠し方の過去の固定は、実行時の写しで担保しているが、その盤面での確かめはしていない）、異なる OS・Python の版、長い対戦・多数の記録。

## 10. 検証の結果

限定検証だけを実行した（全体テスト・全 108 組・4,356 局・lockstep・ストレス実行はしていない）。終了コードは確かめの本体から。

- `tests.test_view_record_v0_155`: 22 テスト OK（約 30 秒）
- U1〜U4 の関係: `tests.test_replay_run_v0_154`（23）・`tests.test_replay_record_v0_153`（25）・`tests.test_diagnostics_adapter_v0_152`（37）・`tests.test_diagnostics_replay_api_design`（20）・
  規約集合の識別と照合値（`test_conventions_v0_142` の `IdentityTest`・`RecordsTest`）: OK。期待を変えたテスト 1 つ（目的は同じ）: v0.154 の `test_spec` は U5 の状態を planned と固定していたのを、
  v0.154 の承認の記録（`ADOPT-U4`）の中身と、実装済みの単位が採用の記録の単位と同じことを確かめる形にした
- 版のテスト（`test_preset_decks_v0_20` の `test_version`）と、変えた文書（README・実装状況・データの来歴）を読む既存のテストのメソッド 16 件: OK
- 生成物の `--check` 7 本（診断のコード表・仕様案・停止の方針の台帳・共通規約の設計案・同梱の規約集合の記録・実装上の仮定・正規化の再確認）: すべて終了コード 0
- ruff 0.17.2（基点と同じ版・設定）: 新しい・変えたファイルに新しい指摘なし（`state.py` の UP035 は注釈だけを変えた既存の行の指摘で基点と同じ）。新しい抑制（`noqa`）はない
- `check_implementation_assumptions.py --sites`（基点の木と比べた差）: 増えた 2・消えた 1。この文書の 4 章の API の変更の説明（「結果は同じ」）と、版のテストの行の識別の付け替え。どちらも実装上の仮定ではない。文面は変えていない
- 途中で直したこと（テストの誤り）: 入ってはいけない語の文字列の検索が、診断の区分の値（`"subkind":"command"`）に当たったので、項目名（`"command":`）を探す形にした。あとで公開されたカードの確かめで、ピカチュウのデッキでは手札のカードがトラッシュでなく場に出るので、場・トラッシュに出たカードで確かめる形にした

## 11. 次の段階への引き継ぎ

- JSON の保存・復元（U6）: 閲覧用記録は状態の復元に使わない（観測は状態のすべてではない）。スナップショットは完全な状態から作る別の形式で、D-SNAPSHOT-BASE（形式 35 から状態を作り直せるかの監査）・D-HALT-SNAPSHOT は保留のまま
- 合法手・GUI（U7）: 閲覧用記録の観測と知らせは、そのまま画面に渡せる。合法手の一覧は、閲覧者の知る情報だけで作る（v0.152 の `next` は種類だけ）
- 大きさ: 観測をまるごと持つ形で約 2.8 MB/対戦。差分にするかは、画面・通信の要件が決まってから（形式の版を上げる）

## 追記（v0.156: 過去のログの情報境界の確かめ）

[state-snapshot-design.md](state-snapshot-design.md) の作業で、次の経路が起きないかを確かめました（エンジン・閲覧用記録の実装は変えていない）。

1. うらのカード（マチスの秘策）に関わるイベントを閲覧用記録に加える（相手の閲覧用ログでは、そのカードの uid を伏せる。`observation._mask_face_down`）
2. あとで持ち主がおもてにする（`RevealFaceDown`）。このとき `visible_log` は、**過去のイベントの uid も見せる**（構築盤面で確かめた: うらのポケモンにつけたエネルギーの `attach_energy` の `target` が、おもてにする前は `None`、あとは uid）
3. 新しい項目で過去のログを取り直すと、過去のイベントの詳細が現れる

結果: 閲覧用記録ではこの経路は起きない。

- 収集器は、前に記録した位置（`_cursor`）より後ろのログだけを、その時点の `visible_log` から写す。過去の位置の内容を取り直したり更新したりしない。同じ位置を 2 回出さない
- 延長戦を始めて区間が変わるときも、前の区間の、まだ記録していない位置だけを写す（区間が終わったときの見える範囲）
- 完全な記録からの変換（`view_records_from_replay`）も同じ収集器（`ViewRecorder.add`）を使うので、同じ境界になる（変換の経路をマチスの秘策を含む合法な対戦の記録で確かめてはいない。コードが同じことによる）
- 確かめたテスト: `tests/test_view_record_v0_155.py` の `PastLogBoundaryTest`（構築盤面から合法な操作。秘策を使う → うらのポケモンにエネルギーをつける → おもてにする。相手・観戦者の記録の過去の位置は伏せたまま、位置は重ならず欠けない、おもてにしたイベント自体はその時点で見える、持ち主は記録した時点から見える）

途中から始めた記録（`attach`）の保証の範囲: 始まりの項目の過去のログは、**記録を始めた時点の投影**で固定する。イベントが起きた時点の投影を作り直すことはしない（その時点の知識は状態に残っていないので、推測で作らない）。たとえば、始めた時点でおもてになっているカードなら、始める前のうらのあいだのイベントでも uid が見える（始めた時点では正当に見える）。始めた位置は `header.origin` が `attached` で表す。対戦の開始から集めた記録（`origin` が `new_game`）だけが、各イベントが起きた時点の投影を持つ。
