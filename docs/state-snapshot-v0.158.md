# 完全な再現用記録とスナップショットの接続（v0.158・U6 の S5）

[仕様](state-snapshot-design.md)の U6「JSON の状態の保存・復元」のうち、残っていた S5（完全な再現用記録の決まった位置にスナップショットをつなぎ、残りの行を U4 で照らす）を実装した版です。`kyuura_engine` の版は 0.158.0 です。これで U6 の単位 S1〜S6 がすべて実装済みになりました（U6 全体の状態は implemented。v0.157 の時点の正しい状態は partial で、v0.158 の最初のコミットで記録を直した）。

保存・復元（U6）と記録・再現（U3・U4）をつなぐ検証者用の機能です。U3 の収集器を途中から始める入口・新しい記録の行の継ぎ足し・閲覧用記録の開始前の知識の復元・異なる規約集合での再開は実装していません（9 章）。エンジンの処理（`engine.py`・`resolution/`・観測・アダプタ）は変えていません。

## 1. 基点と範囲

- 基点: `d832635`（v0.157 の最後。`origin/claude/state-snapshot-impl`。`origin/main` の `8d4beff` はその祖先）。作業ブランチ `claude/state-snapshot-s5`
- 最初に記録を 2 つ整理した（S5 とは別のコミット）
  - U6 の実装の状態: v0.157 の仕様は U6 全体を planned と書き、実装した単位を診断の仕様の採用の記録に書いていなかった。単位の状態に partial を加え、U6 の部分の単位（S1〜S6）の状態と全体の状態を分けて記録した（`ADOPT-U6-IMPL` の単位は `U6/S1`〜`U6/S4`・`U6/S6`）。この版の S5 の実装で、U6 は implemented になった
  - v0.157 の限定の監査: 途中の報告の 18,461 の状態・拒否 29 と、最終の報告の 24,694 の状態・拒否 33 を、残っている証拠（作業用の出力と作業の記録）で確かめ、[v0.157 の文書 8 章](state-snapshot-v0.157.md)を訂正した。24,694・33 は、型の対応表の訂正の前の実行（117 件のテスト）と後の実行（317 件）の合計で、1 回の実行の結果ではなかった。最後の結果として確かめられるのは、訂正のあとの実行の 18,461・拒否 29（effects だけ）・深さ 13。監査は再実行していない
- 採用した契約（`ADOPT-U6-S5`。利用者の指示）: 接続位置は初期の状態か特定の操作の行の直後。実装・環境・依存データ・規約集合と、接続位置の状態・乱数を確かめてから続ける。残りの行は拒否の行も含めて元の seq の順。「接続位置のあとの一致」と「記録の全体の一致」を分ける。確認値の一致を出所の認証・過去に実際に作られたことの証明としない。`ReplayCollector` は新しい対戦からの収集だけ。既存の確認値に不足があれば新しい方式を別の名前で明示し、同じ方式の名前の意味を変えない

## 2. 公開 API と利用例

`kyuura_engine/snapshot_replay.py`（新しいモジュール）:

| API | 責任 | 失敗のとき |
|---|---|---|
| `RecordPosition.initial(*, record=None)`・`RecordPosition.after(seq, *, record=None)` | 接続位置（3 章）。`record` は任意の記録の識別 | 形の誤りは `ValueError` |
| `record_identity(record)` | 記録の識別（方式 `kyuura-replay-header-sha256/1`。見出しの JSON の sha256） | — |
| `replay_from_snapshot(record, snapshot, position, *, replay_prefix=True)` | 接続の確かめと、残りの行の再実行・照合（U4 と同じ処理） | 不正・非対応・不一致では例外を投げず `ResumeReport`。型の誤りは `TypeError` |
| `ResumeReport` | 結果（6 章）: `status`・`scope`・`replay_verified`・`suffix_verified`・`connection_basis`・`verified_from`・`verified_seq`・`mismatch`・`phase`・`restore` | — |

`kyuura_engine/snapshot.py` に加えたもの: `state_items(state)`（保存する全項目の JSON の値。`save_snapshot` の `state` と同じ）・`connection_check(state)`（接続用確認値。5 章）。`kyuura_engine/replay_record.py` に加えたもの: `ReplayCollector.start(..., connection_checks=False)`（任意の拡張。5 章）・`CONNECTION_CHECK_METHOD`・`connection_declared`・`connection_value`。`kyuura_engine/replay_run.py` は U4 の処理を `run_start`・`run_rows`・`run_end` に分け（`replay` の結果は同じ）、S5 の前半・後半の再実行が同じ処理を使う。

```python
from kyuura_engine import replay_record as R, snapshot as SN, snapshot_replay as SR

# 完全な記録とスナップショットの読み取り（どちらも安全な JSON の読み取り。pickle を使わない）
record = R.loads_record(record_text)
snap = SN.loads_snapshot(snapshot_text)          # 復元と照合は replay_from_snapshot の中で行う（文字列のままでも渡せる）

# 接続位置: 初期化の直後（seq 0）か、seq の行の直後（拒否の行の直後も別の位置）。記録の識別で別の記録への誤接続を見つける
position = SR.RecordPosition.after(42, record=SR.record_identity(record))

# 接続の確かめと残りの再実行（既定は前半も再実行して全体を照らす）
report = SR.replay_from_snapshot(record, snap, position)
if report.replay_verified:                       # 記録の全体（開始・すべての行・終わりの情報）が一致
    ...
elif report.suffix_verified:                     # 接続位置のあとだけが一致（scope == "from_connection"）
    ...
else:
    print(report.status, report.phase, report.mismatch)   # 例: connection_mismatch connection Mismatch(..., items=('check.state',))
    print([(p.code, p.path) for p in report.problems])    # 入力の値は入らない

# 接続用確認値のある記録（任意の拡張）では、前半を再実行せずに接続を確かめられる（範囲は接続位置のあとだけ）
collector, _ = R.ReplayCollector.start(deck0, deck1, seed, connection_checks=True)
...
quick = SR.replay_from_snapshot(collector.close(), snap, position, replay_prefix=False)
assert quick.scope == "from_connection" and not quick.replay_verified

# 旧記録（拡張のない記録）: 前半を再実行して確かめる。再実行しないなら検証済みとして続けない
old = SR.replay_from_snapshot(old_record, snap, position, replay_prefix=False)
assert old.status == "unsupported"               # problems のコードは connection_check_absent
```

## 3. 接続位置と記録の識別

- 位置は種類と seq で決める: `initial`（seq 0。初期化が終わった直後・最初の操作の前）と `after_operation`（seq の行の処理が終わった直後。1 以上）。`accepted_index` だけでは位置を決めない（拒否の行を記録したかで受理の番号と seq の対応が変わる）。`replay_from_snapshot` に整数を渡すと `TypeError`
- 拒否の行の直後は、状態は直前の受理の行の直後と同じだが、記録の中の別の位置として扱う（残りの行は seq+1 から）。スナップショットの状態だけでは 2 つを見分けられないので、位置は呼び出し側が決め、スナップショットの `origin.seq` があれば位置と照らす
- 記録の中にない seq（行の数より大きい）は `invalid_position`（`seq_out_of_range`）。失敗の行の直後は `invalid_position`（`after_failure`。失敗のあとの状態からは続けない）。内部エラーで使えなくなった状態は、記録の構造（失敗の行のあとに行がない・aborted）から接続位置にならない
- 記録の識別（`record_identity`）: 見出し（初期の条件・実装と環境の識別・規約集合・拒否を記録したか・拡張・開始の確認値など）の JSON を、鍵の順と区切りを決めて sha256 にした値。同じ対戦でも拒否を記録したかで別の記録になる（seq が違う）。位置の `record` と記録の識別が違えば `connection_mismatch`（`record_differs`）。スナップショットの `origin.game_id` があれば記録の `game_id` と照らす
- 識別・確認値は内容を見分けるための値で、署名・出所の認証・過去に実際に作られたことの証明ではない。改ざんした記録とスナップショットを両方そろえて作り直すことは防げない

## 4. 接続の確かめ

確かめる順（どこかで合わなければ、それより後へ進まない。残りの行を送らない）:

| 順 | 確かめ | 合わないとき |
|---|---|---|
| 1 | 記録の構造（U3 の `validate_record`。形・順序・前後の矛盾・拡張の形） | `invalid_record`（形・矛盾）・`unsupported`（知らない形式の版・拡張） |
| 2 | 記録がこの実装・環境・依存データ・規約集合で扱えるか（U3 の `support_problems`） | `unsupported` |
| 3 | 接続位置（記録の識別・seq の範囲・失敗の行の直後でない） | `connection_mismatch`（`record_differs`）・`invalid_position` |
| 4 | スナップショットの復元（U6 の段 1〜7: 形式・対応（実装・記録の部品・環境・依存・規約集合）・登録データの解決・整合・自己確認値・往復） | `invalid_snapshot`（read_error・malformed・inconsistent）・`unsupported`・`internal_error` |
| 5 | 記録とスナップショットの識別・初期の条件・依存・規約集合と、その位置の確認値（状態・乱数・ログの長さ・区間・状態の知らせ・決定・停止） | `connection_mismatch`（違った項目の名前） |
| 6 | 保存する全項目の一致: 記録の接続用確認値（拡張があり、その位置の値があるとき）と、前半の再実行（`replay_prefix=True` のとき）。どちらもなければ検証済みとして続けない | `connection_mismatch`・`diverged`（前半が記録と違う。`phase` は prefix）・`unsupported`（`connection_check_absent`・`connection_check_unavailable`） |
| 7 | 残りの行を元の seq の順に送り、終わりの情報を照らす（U4 の `run_rows`・`run_end`） | U4 と同じ（`diverged`・`recorded_failure`・`incomplete`・`invalid_record`・`internal_error`。`phase` は suffix） |

5 の「その位置の確認値」は、initial なら見出しの開始の確認値、受理の行の直後ならその行の確認値、拒否の行の直後なら、それ以前の最後の受理の行（なければ開始）の確認値です。スナップショットの自己確認値（`check`）は復元の段 6 で状態と一致を確かめたもので、記録のその位置と一致することは 5 で記録の値と比べて確かめます（自己確認値が正しいだけでは接続の証明にしない）。

### 4.1 既存の確認値だけでは足りない項目

完全な記録の確認値（`state-export-35-sha256/1` と `python-random-getstate-sha256/1`。`replay_record.checks`）は、状態の書き出しの形式 35 から作った範囲の値です。スナップショットが保存する項目のうち、次のものはこの確認値に入らないか、区別が落ちます。

| 項目 | 形式 35 の確認値 | 接続でどう保証するか |
|---|---|---|
| `decklists` | 入らない | 記録の見出しの `initial.decklists` と直接比べる（5）。並びも比べる。接続用確認値・前半の再実行でも比べる |
| `definitions`（カードの定義） | 入らない（カードの id は `cards` の記録に入る） | スナップショットは id の並びだけを保存し、既定のカードプールから解決する。カードプールの写しの元（`card_data`）と効果の登録表の id は記録とスナップショットの両方の対応の確かめ（2・4）と依存の比べ（5）で同じ。`definitions` の id の集まりと `cards` の card_id の集まりが同じことは復元の構造の確かめ（`structure_problems`）が見る |
| `pending_moves` | 入らない | 保存しない。保存の境界で空を求め、復元では空。U4 の各行でも空を確かめる（`boundary_items`） |
| 登録データ（`rules`・`effects`・`conventions`） | ルールの組の id・効果の登録表の id・規約集合の記録は入る | 識別から登録済みのものを解決する（入力からクラス・コードを読み込まない）。記録の見出しの規約集合・依存とスナップショットの見出しを直接比べる（5）。規約集合の差し替えはできない |
| 乱数 | 指紋（`getstate()` の repr の sha256）は入る | スナップショットは状態そのものを保存し、復元で指紋を確かめる。指紋は記録の位置の値と比べる（5） |
| `CardInstance.origin` | 入らない（カードの記録は card_id・owner だけ） | 前半の再実行・接続用確認値で比べる |
| 型と順序 | 形式 35 はタプルとリストを区別せず（`_plain`）、鍵を並べかえる（`sort_keys`）。値の記録の型の印・列挙も文字列や辞書になる | スナップショットは型の対応表の形（タプルとリスト・型の印・列挙）とログのイベントの鍵の順を保つ。前半の再実行・接続用確認値はこの形のまま比べる |
| 停止の文・ログの全体・過去の区間 | 入る（形式 35 の halt・log・segments） | 同じ値をスナップショットも持つ。比べる形は上の型と順序のとおり |

テスト（`MisconnectionTest.test_items_outside_the_existing_checks`）は、ログのイベントの鍵の順と `decklists` の並びを変えて保存し直したスナップショットで、位置の確認値が記録の値と同じのまま（既存の確認値では見分けられない）、接続の確かめが不一致として見つけることを確かめる。`CardInstance.origin` だけを変えた状態は、不変条件（所有の記録と照らす確かめ）が保存を拒むので、このテストでは使っていない。

構築盤面（`tests.helpers.build_test_state`）は保存の境界と整合の確かめを満たせば保存できるが（DS-CONSTRUCTED）、それは new_game から始まる記録の位置につながることではない（初期の条件・確認値が合わない）。

## 5. 接続用確認値と互換性

既存の確認値は 4.1 の項目を見ないので、新しい方式を別の名前で加えた。既存の方式（`state-export-35-sha256/1`・`python-random-getstate-sha256/1`）の名前と意味は変えていない。

- 方式 `kyuura-snapshot-state-sha256/1`（`replay_record.CONNECTION_CHECK_METHOD`・`snapshot.connection_check`）: `{"method": 方式, "card_pool": "default", "state": state_items(状態)}` を、鍵を並べかえずに（項目は保存の順・ログのイベントの鍵は保存した順）区切りを決めた JSON（UTF-8）にした sha256
- 対象: スナップショットが保存する意味のある全項目（`state` の全項目。登録データ・依存の識別 `rules`・`definitions`・`effects`・`conventions`・`card_data` を含む）とカードプールの識別
- 除くもの: スナップショットの `check`（状態から求める値。自分を含む確認値にしない）・実装と環境の識別（照合値でなく対応の確かめで扱う）・`origin`・`label`・`git_commit`（補助の情報）・`pending_moves`（保存の境界で空）
- 保存できない状態（保存の境界の外・型の対応表で表せない値）では値を作らない（`SnapshotSaveError`。記録では None）

記録への任意の拡張（形式の版は `kyuura_replay_format` = 1 のまま）:

- `ReplayCollector.start(..., connection_checks=True)` のときだけ、見出しに `"extensions": {"connection_check": "kyuura-snapshot-state-sha256/1"}` を書き、`header.start` と受理した行ごとに `connection_check`（64 桁の 16 進、または作れなかった位置の None）を残す。既定は偽で、v0.157 までと同じ記録
- 構造の検証: 知らない拡張の名前・方式は `unsupported`（`extension_unknown`・`extension_method_unknown`）。拡張を明示したのに値がない・形が違えば `malformed`（`connection_check_missing`・`connection_check_bad`）。明示していないのに値があれば `inconsistent`（`connection_check_undeclared`）。受理でない行に値があれば `inconsistent`（`check_on_non_accepted`）
- U4（`replay_run.replay`）は、拡張のある記録では開始と受理した行ごとに接続用確認値も照らす（違えば項目 `connection_check`）。拡張のない記録の結果は v0.157 と同じ。知らない拡張の記録は、途中で切れていても `unsupported`
- 旧記録（拡張のない記録。v0.157 までの記録を含む）は黙って読みかえない（値があるものとして補わない）。初期の条件から接続位置まで再実行して得た状態と、スナップショットの全項目を比べる方法で扱う（既定）。前半を再実行しないなら `unsupported`（`connection_check_absent`）。拡張のある記録でも、その位置の値が None なら同じ（`connection_check_unavailable`）
- 古い実装（v0.157 以前）は見出しの `extensions` と行の `connection_check` を知らないが、実装の識別が違うので、v0.158 の記録は古い実装では `unsupported` になる（拡張の値を読み飛ばして照合したことにはならない）
- 前半を省いた接続は速いが、照らす範囲は接続位置のあとだけ（`from_connection`）。前半の行は今回照らしていない

## 6. 結果の契約

| `status` | 意味 |
|---|---|
| `succeeded` | 照らした範囲の最後まで（残りの行と終わりの情報が）一致した。全体か接続位置のあとだけかは `scope` |
| `incomplete` | 終わりの情報がない記録で、最後の行まで一致した（成功に数えない） |
| `recorded_failure` | aborted の記録で、失敗の行まで一致し、同じ失敗がもう一度起きた（成功に数えない） |
| `unsupported` | 記録・スナップショット・拡張をこの実装・環境・依存データ・規約集合で扱えない。接続を確かめる根拠がない（`connection_check_absent`・`connection_check_unavailable`） |
| `invalid_record` | 記録の形式の不正・内容の矛盾（終わりの情報の改変もここ）。送り直せないコマンド |
| `invalid_snapshot` | スナップショットを読めない・形式が正しくない・状態が整合しない（`restore` に復元の結果） |
| `invalid_position` | 接続位置が記録の中にない・失敗の行の直後 |
| `connection_mismatch` | スナップショットが記録のその位置の状態と一致しない（別の記録・別の位置・別の区間・違う状態。`mismatch.items` に違った項目の名前） |
| `diverged` | 前半（`phase` は prefix）または残りの行・終わりの情報（suffix）の再実行の結果・確認値が記録と違った |
| `internal_error` | 記録にない内部エラー・処理の中の想定外の例外（不一致・未対応に変えない） |

- `scope`: `whole_record`（前半も今回再実行して照らした）・`from_connection`（接続位置のあとだけ）。接続を確かめる前に止まれば None
- `replay_verified` は `succeeded` かつ `whole_record` のときだけ真。前半を照らしていない結果では、記録の全体の検証として扱わない（`suffix_verified` だけが真）
- `connection_basis`: 接続の根拠（`prefix_replay`・`connection_check`）。`verified_from`: 照らした行の範囲の始まり（全体なら 0。接続位置のあとだけならその seq）。`verified_seq`・`verified_accepted`: 一致した最後の行の seq と受理の数
- `mismatch`: 最初の不一致（U4 と同じ `Mismatch`。接続の不一致は `location` が connection）。`phase`: 不一致・失敗の起きた部分（prefix・connection・suffix）
- 再実行は U4 と同じ: 方策を再実行しない、乱数を各操作の前へ戻さない、コインの結果を入れない、`accepted_index` は受理の行の照合に使う（途中から照らすときの数の食い違いも見つける）、拒否の行では結果と状態が変わらないことを確かめる、最初の不一致で止める、終わりの情報も照らす
- 停止・決定待ち・終局の意味は復元した状態のまま（停止の状態をつないでも、停止の解除・規約集合の差し替えの API はない）
- 例外の扱いは adapter・U4 と同じ: 想定外の例外は `internal_error`（`failure` に traceback。repr に出さない）。`MemoryError`・`KeyboardInterrupt`・`SystemExit` は捕まえない

## 7. 情報境界

- 記録・スナップショット・接続用確認値・照合の詳細（`Mismatch` の値・`failure`・`restore`）は、信頼されたホスト・検証者用。`view_for`・観測・閲覧用記録には入らない（入口を加えていない）
- `ResumeReport`・`Mismatch`・`RecordPosition` の repr は、seed・カード・確認値・乱数を出さない（状態・項目の名前・seq だけ）。問題の説明はコードと JSON の経路だけで、入力の値を入れない
- JSON の読み取りは U3 の安全な読み取り（大きさ・深さ・重なった鍵・NaN を拒む）。pickle・`__setstate__` を使わない

## 8. 検証

限定の検証（全体のテスト・108 のまとまり・4,356 局・lockstep の全体・広い監査・負荷・v0.157 の状態の監査の再実行はしていない）。

| 実行 | 結果 |
|---|---|
| 新しいテスト `tests/test_snapshot_replay_v0_158.py` | 28 件 OK |
| 新しいテストと、直接関係するテスト（`test_state_snapshot_v0_157`・`test_replay_record_v0_153`・`test_replay_run_v0_154`・`test_view_record_v0_155`・`test_diagnostics_adapter_v0_152`・`test_state_snapshot_design`・`test_diagnostics_replay_api_design`・版のテスト `test_preset_decks_v0_20`）を 1 つのプロセスで順に | 222 件 OK（終了コード 0） |
| 生成物の `--check` 8 本（スナップショットの仕様・診断の仕様・診断のコード表・停止の方針の台帳・同梱の規約集合の記録・実装上の仮定・正規化の再確認・共通規約の設計案） | すべて終了コード 0 |
| ruff（変えた・加えたモジュール・テスト・スクリプト） | 指摘なし。新しい抑制なし。停止の台帳の語と `RuntimeError` の送出を加えていない（テストが差し込む例外は専用の `InjectedError`） |
| `check_implementation_assumptions.py --sites`（終了コード 0。基点 `d832635` の木と走査の結果を比べた差） | 2 件増・1 件減（下の分類） |

`--sites` の差の分類（文面は変えていない）: 増えた 1 件は、この文書の 2 章の「`replay` の結果は同じ」（U4 の処理を分けても再実行の結果が変わらないことの説明）で、実装上の仮定ではない。残りの 1 件増・1 件減は、版のテストの経緯の注釈の行（`tests/test_preset_decks_v0_20.py` の 151 行。v0.132 の利用者指定の経緯を含む既存の行）に 0.158.0 を書き足して識別が変わったもの。

テストの盤面（new_game からの合法な操作の列と構築盤面を分ける）と確かめたこと:

| 場面 | テスト |
|---|---|
| 初期の状態のスナップショットから全操作を再実行 | `ConnectTest.test_initial_snapshot_replays_every_operation` |
| 受理の行の直後・拒否の行の直後（同じ状態で別の位置。origin.seq の照合） | `test_after_an_accepted_operation`・`test_after_a_rejected_operation` |
| 決定待ちから答えて続ける | `test_awaiting_decision_then_answer` |
| 受理の結果の途中停止・HALTED（開始から停止） | `test_halt_after_an_accepted_answer`・`test_halted_from_the_start` |
| 終局で閉じた記録 | `test_game_over_closed_record` |
| サドン・デスの開始の前後・延長戦の区間の途中・別の区間への誤接続 | `test_sudden_death_and_segments` |
| 拒否を省いた記録と含む記録 | `test_records_with_and_without_rejections` |
| 3 つの規約集合（別の集合の状態はつながない） | `test_three_convention_sets` |
| 保存しないで続けた状態・復元して残りを送った状態・最初から U4 で再実行した状態が同じ | `test_three_ways_agree` |
| 別の記録・別の seq・記録の識別・自己確認値を作り直した違う状態・既存の確認値の対象外の項目・構築盤面 | `MisconnectionTest` |
| 初期の条件・実装・環境・規約集合の不一致、残りの行・確認値・接続用確認値・終わりの情報の改変、前半の改変（全体の検証では見つかり、接続位置のあとだけでは見つからない）、拡張の構造 | `MismatchTest` |
| 不完全な記録・aborted（失敗の行の直後は位置にしない・同じ失敗の再現）・内部エラー（後半・復元の中）・壊れたスナップショット | `IncompleteFailureTest` |
| repr・問題・観測に値が出ない、収集器の契約 | `BoundaryTest` |

未確認:

- 長い対戦・多くの区間での前半の再実行の時間（テストの記録は数百行まで。前半の再実行は行の数に比例する）
- 接続用確認値の拡張を付けた収集の費用（受理の行ごとに保存する全項目の sha256 を取る。既定は付けない）
- OS・Python の版をまたぐ接続（この環境だけ。保証は U3 の範囲: 実装と major・minor が同じ）
- 構築盤面が new_game から合法に到達できるか（保証しない。接続できないことだけを確かめた）

## 9. しないこと・次の作業への引き継ぎ

- しないこと: `ReplayCollector` の途中からの開始、新しい対戦の記録の継ぎ足し（接続したあとの操作を同じ記録へ足す）、閲覧用記録の開始前の各イベントの時点の知識の復元、異なる規約集合での再開、停止の解除、既定でないカードプール・効果の登録表、旧形式（形式 1〜35）からの自動移行
- 総合検証へ: 全体のテスト・lockstep・広い監査は今回走らせていない。U6 全体（S1〜S6）を含む総合検証では、v0.157 の監査の対象外のテストの盤面での保存・復元と、長い記録での接続（前半の再実行の時間）を確かめる
- 合法手 API（U7）の仕様の作成へ: 合法手の一覧は見る人の知る情報だけで作る境界で、この版の検証者用の値（記録・スナップショット・接続用確認値）を使わない。復元した状態から合法手を作る場合も、閲覧者に渡すのは観測の範囲だけ
