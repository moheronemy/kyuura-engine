# U1〜U6 の総合検証（v0.159）

診断（U1）・実行アダプタ（U2）・完全な再現用記録（U3）・再実行と照合（U4）・閲覧用記録（U5）・状態の保存と復元とスナップショットからの接続（U6。S1〜S6）がそろったので、機能の追加を止め、契約の整合と実装の全体を確かめた版です。`kyuura_engine` の版は 0.159.0 です。新しい機能は加えていません。合法手の一覧（U7）の仕様は作っていません（11 章）。エンジンの処理（`engine.py`・`resolution/`・観測）は変えていません。

## 1. 基点・範囲・作業の保護

- 基点: `aff77f9`（v0.158 の最後。`origin/claude/state-snapshot-s5`。`origin/main` の `8d4beff` はその祖先）。作業ブランチ `claude/u1-u6-integration`
- 作業の木: 別の作業ツリー `C:\dev\kyuura-engine-v149`（利用者の作業ツリー `C:\dev\kyuura-engine` の未コミットの変更 17 件・`.claude/`・改行コードだけの差分には触れていない。開始時と終了時に 18 項目のまま）
- kyuura（`C:\dev\kyuura`）は `b9e7cff`・変更なしのまま（読んだだけ）
- 環境: Windows 11・Python 3.14.6（CPython）・`PYTHONUTF8=1`。PATH の先頭の git は msys2 の `c:\devkitPro\msys2\usr\bin\git.exe`（2.55.0）。v0.151 の引数の展開（`^{tree}` の波括弧）を避けるため、git を呼ぶテスト・道具の実行では `MSYS=noglob` を設定した
- 重い処理（監査・測定・全体のテスト・lockstep）は 1 つずつ順に実行し、並行させていない。実行中は作業の木を変えていない（前後の指紋。9 章）

順序: 1 契約の照合（2 章）→ 2 監査（3 章）→ 3 測定（4 章）→ 4 修正と回帰テスト・コードの固定（5 章）→ 5 全体のテスト（6 章）→ 6 既存のエンジンとの比べ（7 章）→ 7 文書化と、文書を読むテストの再実行。

## 2. 公開 API と契約の照合

実装（`kyuura_engine/diagnostics.py`・`adapter.py`・`replay_record.py`・`replay_run.py`・`view_record.py`・`snapshot.py`・`snapshot_replay.py`）と各版の文書を読み比べた（コードを読んだ判断。実測は 3〜7 章）。

| 単位 | 入口と既定値 | 結果の分類 | 例外と結果の境界 | 情報境界 |
|---|---|---|---|---|
| U1 | `classify_error`・`classify_halt_code`・`next_actions`・`continuable`・`check_viewer` | 分類 8 つ（表にないコード・型の違いは `unmapped`。`EngineError` でない例外は `internal_error`） | 見る人の値が 0・1・None でなければ `ValueError` | 本人は `ActorDiagnostic`、相手・観戦者は `StatusNotice`（公開の項目だけ）。検証者の値は `VerifierReport` だけ |
| U2 | `submit(state, command, *, submitter=None, operation_id=None)`・`start_game`・`HostedGame` | `accepted`・`rejected`（元の状態を保つ）・`failed`（状態の不整合・内部エラー。状態を返さない） | `EngineError` は拒否（`StateIntegrityError` は failed）、ほかの `Exception` は failed・internal_error。`MemoryError`・`KeyboardInterrupt`・`SystemExit` は捕まえない。failed のあとの `HostedGame` は `HostStoppedError` | 拒否は本人だけに知らせる（相手・観戦者には None） |
| U3 | `ReplayCollector.start(..., record_rejections=True, include_git=True, connection_checks=False)`・`validate_record(record, *, check_support=True)`・`loads_record` | 構造の検証は malformed・inconsistent・incomplete・unsupported・structure_valid（`replay_verified` はいつも偽） | 読めない JSON は `RecordFormatError`、閉じた・止まった収集器は `CollectorStoppedError` | 記録は検証者用（見る人に渡さない） |
| U4 | `replay(record, *, observer=None)` | succeeded・incomplete・recorded_failure・unsupported・invalid_record・diverged・internal_error（`succeeded` だけが成功） | 想定外の例外は internal_error（不一致・未対応に変えない） | 結果・`Mismatch` の値は検証者用（repr に値を出さない） |
| U5 | `ViewHost.start(..., viewers=(0, 1, None), full_record=True)`・`ViewRecorder.attach`・`view_records_from_replay`・`validate_view_record` | 構造の検証は U3 と同じ形（`replay_verified` は偽） | 前の状態と合わない結果は `ValueError`（ホストの誤り） | その時点で知りえた値だけ。拒否は本人の記録だけ。完全な記録の値・確認値は入れない |
| U6 S1〜S4・S6 | `save_snapshot(state, *, origin=None, label=None, include_git=False)`・`restore_snapshot`・`RestoredGame` | 復元は restored・read_error・malformed・unsupported・inconsistent・internal_error | 保存できない状態は `SnapshotSaveError`、`origin`・`label` の形の誤りは `ValueError`、`restore_snapshot` の型の誤りは `TypeError`。復元の想定外の例外は internal_error | スナップショットは検証者用。`RestoredGame` の閲覧用記録は attached から |
| U6 S5 | `replay_from_snapshot(record, snapshot, position, *, replay_prefix=True)`・`RecordPosition`・`record_identity` | U4 の 7 つに invalid_snapshot・invalid_position・connection_mismatch | 型の誤りは `TypeError`、位置の形の誤りは `ValueError`。想定外の例外は internal_error | 検証者用。repr に seed・カード・確認値を出さない |

継続可能性（`continuable`）は、進行中・決定待ち・延長戦の開始待ちで、かつこの版がその状態の規約集合・再開先を処理できるときだけ真（停止・終局・failed は偽）。これはどの単位でも同じ定義（`diagnostics.continuable`）を使っている。

### 2.1 明示を求められた 4 点

**A. 拡張のない記録。** 既定（`connection_checks=False`）の収集の出力の形が v0.157 と同じことと、過去の実装で作った記録を今の実装で扱えることは別です。扱えるかは記録の見出しの実装の識別（`behavior_digest`。パッケージの `.py` と `data/*.json` の内容から、記録と診断の部品 4 つを除いたものの sha256）と版で決まり、違えば U4・S5 とも `unsupported`（`implementation_differs`・`engine_version_differs`）です。拡張の有無・前半の再実行（`replay_prefix`）によりません。したがって v0.157 の実装で作った記録は v0.158・v0.159 では扱えません（v0.158 の文書 5 章の「v0.157 までの記録を含む」は誤りで、訂正した）。前半の再実行で扱える「旧記録」は、今の実装で作った拡張のない記録だけです（テスト `OtherImplementationTest`）。

あわせて、実装の識別の分け方の食い違いを記録しました（**変えていない。利用者の判断が要る**）: v0.153 の文書は `behavior_digest` を「ゲームの挙動の識別（記録と診断の部品を除いたもの）」としていますが、部品の一覧（`replay_record.INSTRUMENTATION_FILES`）は v0.153 の 4 つ（`adapter.py`・`diagnostics.py`・`replay_record.py`・`data/diagnostic_catalog.json`）のままで、あとで加えた検証者用のモジュール（`replay_run.py`・`view_record.py`・`snapshot.py`・`snapshot_replay.py`）は `behavior_digest` の側に入ります。そのため、これらを直すと（この版の修正を含む）、ゲームの処理が同じでもそれまでの記録・スナップショットは `unsupported` になります。安全側の振る舞い（互換を推測しない）なので不具合とはせず、分け方を変えるには、識別の方式の意味が変わるので新しい方式の名前と利用者の判断が要ります。v0.153 の文書に注を加えました。

**B. 接続確認値による検証。** `replay_prefix=False` の接続は、記録の接続用確認値（任意の拡張）と復元した状態の値の一致から、接続位置のあとの行と終わりの情報だけを照らします。前半の操作の列が正しいことは保証しません（前半の行は構造の検証だけ。終わりの情報の受理の数も、前半の分は記録の値を使う）。結果は `scope` が `from_connection`、`replay_verified` は偽、`suffix_verified` だけが真で、`whole_record` の成功として扱いません（S5 のテスト `MismatchTest` は、前半だけを書きかえた記録が `from_connection` では通り、`whole_record` では見つかることを確かめている。4 章の測定でも 3 つの位置すべてで `from_connection`・`replay_verified` 偽）。

**C. `save_snapshot` の誤りの優先（実装を直した）。** v0.158 の実装は、型の対応表・保存の境界・表せない値（`state_items`）を `origin`・`label` の形より先に確かめていたが、深さ（`too_deep`）と大きさ（`too_large`）の上限は `origin`・`label` を加えたあとに確かめていたので、状態が深すぎるうえに `origin` の形も違うと `ValueError` になっていた（v0.157 の実装は、表せない値も `origin`・`label` のあとに確かめていた）。v0.159 で次のとおりに統一し、実装・docstring・v0.157 の文書の表・テストをそろえた:

1. 状態そのものを保存できない（型の対応表・保存の境界・表せない値・状態だけの書き出しの深さと大きさ）→ `origin`・`label` の形によらず `SnapshotSaveError`
2. 状態を保存できるときだけ、`origin`・`label` の形を確かめる → `ValueError`
3. 補助の情報（`origin`・`label`・`git_commit`）を加えた書き出しが大きさの上限を超える → `SnapshotSaveError`（`too_large`）

成功したときの書き出し（鍵の並び・値）は前と同じ（補助の情報は `state` のあと）。テスト `SaveErrorOrderTest`（直す前のコードでは 4 件がエラーになることを確かめた）。

**D. `next`。** `next` は次に受け付けうる操作の種類（`place_starting_pokemon`・`draw_mulligan_cards`・`report_janken_result`・`turn_action`・`answer_decision`・`start_sudden_death`）と送るプレイヤーで、合法手の一覧ではない（`diagnostics.next_actions` は段階・番・決定だけから決まり、どのカード・ワザ・対象を選べるかを持たない）。v0.152 の文書・仕様の表（`next` の行）と一致していて、変えていない。

### 2.2 見つけた食い違いの分類

| 事象 | 分類 | 対応 |
|---|---|---|
| v0.158 の文書の「旧記録（v0.157 までの記録を含む）」 | 文書の誤り | 訂正した（v0.158 の文書 2・5 章） |
| `save_snapshot` の深さ・大きさの上限が `origin`・`label` の形のあと | 実装の不具合（優先が一貫しない） | 直した（C） |
| 閲覧用記録の構造の検証が、v0.158 で加えた完全な状態の接続用確認値（`connection_check`）とスナップショットの形式の鍵（`kyuura_snapshot_format`）を拒まない | 実装の不足（U5 の境界「完全な状態の確認値は入れない」を検証が見ない。閲覧用記録の作り方は値を入れていない） | 入ってはいけない項目の名前に加えた（`ViewRecordBoundaryTest`。直す前のコードでは失敗） |
| 検証者用のモジュールが `behavior_digest` の側に入る | 仕様と実装の食い違い（安全側） | 変えていない。文書に注（A） |
| `save_snapshot` の docstring の「どちらも確かめない」（実際は形を確かめる） | 文書の誤り | 直した（形だけを確かめ、内容は確かめない） |

承認済みの情報境界・規約・互換性（記録の形式・確認値の方式・実装の識別の方式）は変えていません。

## 3. コミット済みの保存・復元の監査

コミットした `tools/snapshot_audit.py` そのものを実行した（作業用の別のスクリプトで代えていない）。

- 道具: `tools/snapshot_audit.py`（最後に変えたコミット `80504fc`。sha256 `45b9cfc51a16ce6a7b93b4e0385ca1525f30b95bd5d815de25d833ae0b44ef9d`）
- 対象（実行の前に固定）: v0.157 の監査の実行 A と D の和集合。名前は v0.158 の作業の記録（実行したコマンドの行）から確かめた。推測した名前はない
  - 実行 A: `tests.test_secret_plan_v0_67`・`tests.test_markers_counters_v0_90`・`tests.test_harden_v0_4b`
  - 実行 D: `tests.test_trade_please_v0_130`・`tests.test_ownership_exchange_v0_130`・`tests.test_sudden_death_v0_134`・`tests.test_stadiums_v0_57`・`tests.test_energy_control_power_suppression_v0_59`・`tests.test_hidden_card_trainers_v0_63`・`tests.test_deferred_shortage_user_promos_v0_127`・`tests.test_mew_devolution_v0_50`・`tests.test_virtual_attacks_transformation_v0_49`
  - 重なりはない（12 モジュール）
- コマンド: `python -m tools.snapshot_audit <上の 12 モジュール>`（リポジトリの根・`PYTHONUTF8=1`）
- 木: `aff77f9`（作業の木の変更なし。前後の指紋は同じ: 追跡ファイル 696・`cba696f5…02abe`）

| 実行 | コード | 対象 | テスト | 保存・復元を試した状態 | restored | 保存の拒否 | 予期しない失敗・内部エラー | 深さ | 時間 | 終了コード |
|---|---|---|---|---|---|---|---|---|---|---|
| v0.159 | `aff77f9`（コミット済みの道具・v0.158 の `snapshot.py`） | 12 モジュール | 434（失敗 0・エラー 0） | 24,727（保存 24,694＋拒否 33） | 24,694 | `effects` 33（`$.state.effects`） | 0（restored でない復元 0・表せない値 0・構造 0・境界の外 0） | 13 | 514 秒（壁時計 516 秒） | 0 |

- 拒否の 33 件はすべて、テストが差し替えた効果の登録表（既定のカードプールの登録表でない）を使う状態で、仕様どおりの対応の外（`SAVE_NOT_SUPPORTED`）。道具は effects の拒否で終了コードを 1 にしない
- v0.157 の文書 8 章の表（実行 A〜D）とは別の行です。この 1 回の実行は、v0.157 の最終の報告の数（24,694・33・434 件）と同じになったが、v0.157 の数は訂正の前の実行 A と後の実行 D の合計で、コードの時点が違う。v0.159 の行は 1 つのコード（`aff77f9`）で 12 モジュールを 1 回で走らせた結果で、実行 A の 3 モジュールが型の対応表の訂正のあとのコードでも表せない値なしに通ることを、はじめて確かめた
- 5 章の修正（`save_snapshot` の誤りの優先）のあとには監査を走らせていない。修正は保存できない状態・形の誤りのときの例外の順だけで、保存に成功する経路の書き出し（監査が数える restored）は同じ（`SaveErrorOrderTest.test_size_limit` が同じ書き出しを確かめる）。全体のテスト（6 章）は修正のあとの木
- 実行のあと、作業の木・同梱のデータ・テストの固定データ・文書の JSON の指紋は前と同じ（参照データを変えていない）

## 4. 固定した長い記録の測定

性能の基礎の測定です。速度の目標・合否の閾値は設けていません。圧縮・キャッシュ・記録の形式の最適化はしていません。

対戦（実行の前に固定。seed を探していない。どちらも既存の U3〜U6 のテストの対戦）:

| 名前 | デッキ・seed | 既存のテスト | 選んだ理由 |
|---|---|---|---|
| L | ピカチュウのデッキ（`tests.test_replay_record_v0_153.DECKS`）seed 0 | `test_snapshot_replay_v0_158` の OVER | ピカチュウの対戦で、1 区間のまま終局まで進む |
| S | 同じデッキ seed 9 | 同じテストの SD・v0.157 のテスト | サドン・デスから延長戦（2 区間目）へ進んで終局 |

操作はテストの `collect` と同じ方策（`trainer_policy_command`）と同じ拒否の混ぜ方。接続位置は実行の前に規則で固定した: mid（行の数の半分以後の最初の決定待ちの受理の行）・sd_pending（延長戦の開始待ちになった受理の行。S だけ）・sd_start（`start_sudden_death` の受理の行。区間の境界。S だけ）。

| 対戦 | 行 | 受理 | 拒否 | 区間 | 終わり |
|---|---|---|---|---|---|
| L | 111 | 105 | 6 | 1 | game_over |
| S | 227 | 213 | 14 | 2（2 区間目は seq 208 から） | game_over |

収集（`ReplayCollector.submit` の時間の合計。方策の時間を除く）と容量:

| 対戦 | 拡張なし: 時間・記録 | 拡張あり（`connection_checks=True`）: 時間・記録 | 閲覧用記録（本人 0・本人 1・観戦者） |
|---|---|---|---|
| L | 0.33 秒・53,376 バイト | 0.46 秒・62,559 バイト（+17%） | 1,163,992・1,159,478・1,139,978 バイト |
| S | 0.99 秒・103,005 バイト | 1.38 秒・121,476 バイト（+18%） | 2,905,978・2,909,715・2,852,235 バイト |

- 拡張の有無で記録の行（接続用確認値を除く）・最終の状態は同じ。どちらも構造の検証は structure_valid
- 閲覧用記録は完全な記録の約 20〜28 倍。各項目がその時点の観測の全体（場・手札の枚数・公開のカードなど。1 項目あたり約 10〜13 KB）を写して固定する作り方（U5 の契約「あとで公開された情報を過去の項目へ遡って入れない」）のためで、不具合ではない。差分で持つなどの最適化は範囲の外（記録の形式の変更になる）

スナップショット（位置ごと）:

| 対戦・位置 | seq・状態 | 保存 | 復元 | 大きさ | 深さ | 復元した状態と元の状態 |
|---|---|---|---|---|---|---|
| L mid | 56・決定待ち | 5.1 ms | 5.5 ms | 40,200 バイト | 11 | 同じ |
| S mid | 113・決定待ち | 6.7 ms | 7.6 ms | 60,812 バイト | 11 | 同じ |
| S sd_pending | 207・延長戦の開始待ち | 8.3 ms | 10.0 ms | 84,624 バイト | 11 | 同じ |
| S sd_start | 208・進行中（区間 1） | 7.7 ms | 9.1 ms | 80,408 バイト | 10 | 同じ |

再現（秒。1 回の測定）:

| 対戦・位置 | U4 全体（拡張なし・あり） | S5 前半の再実行つき（拡張なし・あり） | S5 接続用確認値だけ（拡張あり） | S5 前半なし・拡張なし |
|---|---|---|---|---|
| L mid | 0.37・0.50 | 0.39・0.51（whole_record） | 0.29（from_connection・verified_from 56） | unsupported（`connection_check_absent`） |
| S mid | 1.10・1.49 | 1.13・1.50（whole_record） | 0.85（from_connection・113） | unsupported |
| S sd_pending | 同上 | 1.11・1.50 | 0.17（from_connection・207） | unsupported |
| S sd_start | 同上 | 1.08・1.48 | 0.15（from_connection・208） | unsupported |

- すべての実行で、期待した結果（U4 は succeeded、S5 の前半つきは succeeded・whole_record・`replay_verified` 真、接続用確認値だけは succeeded・from_connection・`replay_verified` 偽、前半も拡張もない接続は unsupported）。測定の道具の想定外の結果は 0（終了コード 0）
- 一致の確かめ（保存する全項目・U3 の確認値・乱数の状態・今と過去の区間のログ・3 者の観測）: U4 の再実行の最終の状態、各位置の復元した状態、復元した状態から残りの行を送った最終の状態が、保存しないで続けた状態とすべて同じ

費用の内訳（cProfile の呼び出しの回数。S の全体）:

- U4 の時間の約半分は確認値（`checks` → `state_check`。形式 35 の書き出しの sha256）。回数は 243 = 開始 1＋受理 213＋拒否 14×2＋終わり 1。拒否の行は「状態が変わらないこと」を確かめるため前後で 2 回求める（意図した重なり。拒否の少ない記録では小さい）
- 拡張ありの U4・収集は、受理の行ごとに接続用確認値（`state_items` の符号化と sha256）を 1 回加えるので約 35〜40% 増える（214 回。0.84 秒）
- S5 の前半つきの時間は U4 の全体とほぼ同じ（前半の再実行＋後半の再実行が記録の全行）。接続の確かめの重なり（`_state_differences` が全項目を比べたあと念のため接続用確認値を両方の状態で求める。`state_items` 4 回・0.014 秒）は小さく、直していない
- 接続用確認値だけの接続は、接続位置のあとの行の数に比例する（sd_start で 0.15 秒）。極端な増大・不要な全体の繰り返しは見つからなかった

## 5. 修正と回帰テスト・コードの固定

| 修正 | ファイル | 回帰テスト |
|---|---|---|
| `save_snapshot` の誤りの優先の統一（2.1 節 C）と docstring | `kyuura_engine/snapshot.py` | `tests/test_integration_u1_u6_v0_159.py` の `SaveErrorOrderTest`（3 件） |
| 閲覧用記録の入ってはいけない項目に `connection_check`・`kyuura_snapshot_format` | `kyuura_engine/view_record.py` | `ViewRecordBoundaryTest` |
| 過去の実装の記録は U4・S5 とも unsupported（文書の訂正の確かめ） | 文書だけ | `OtherImplementationTest` |
| 文書の訂正 | `docs/state-snapshot-v0.158.md`・`docs/state-snapshot-v0.157.md`（API の表）・`docs/replay-record-v0.153.md`（識別の分け方の注） | `DocumentTest` |

- 回帰テストは、直す前の `snapshot.py`・`view_record.py` に差し替えると 6 件が失敗・エラーになることを確かめた（もとにもどした）
- 内部エラーを未対応に変えていない。不変条件を弱めていない。広い正規化で不一致を隠していない。固定デッキ・過去の参照データ・続行規約・規約集合の内容を変えていない。記録の形式・確認値の方式・実装の識別の方式の名前と意味を変えていない
- 版を 0.159.0 にした（`__init__.py`・`pyproject.toml`・版のテスト・README・実装状況）

## 6. 全体のテスト

（実行のあとに書く）

## 7. 既存のエンジンとの比べ（lockstep）

比べの基点は U1 の実装の前の仕様のコミット `274c903`（版 0.151.0）。`274c903` から `aff77f9` までに、既存のエンジンのファイルで変わったのは `kyuura_engine/__init__.py`（版の文字列）と `state.py`（注釈の 1 行）だけで、ほかは U1〜U6 の新しいモジュール・コード表・道具（コードを読んだ判断）。

対象は既存の lockstep の固定した 760 局（`tools/engine_lockstep.py record` の既定: `--corpus all --seeds 20 --stress-seeds 10`。自然な対戦のモジュール 23 × seed 20 と、ストレスの組 30 × seed 10。対象・席・seed・方策は変えない）。新しい API・記録の形式の互換性の試験とは別の、既存のエンジンの挙動の確かめです。

（結果は実行のあとに書く）

## 8. その他の検査

（実行のあとに書く）

## 9. 証拠

（実行のあとに書く）

## 10. 結果の区分

（実行のあとに書く）

## 11. 残る事項と次の作業

（実行のあとに書く）
