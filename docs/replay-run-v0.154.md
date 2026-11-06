# v0.154: 完全な再現用記録からの再実行と確認値の照合（U4）

[仕様案](diagnostics-replay-api-design.md)の U4 を実装した版です。v0.153 の記録（`replay_record`）から対戦を作り直し、記録の行を `seq` の順に送り直して、結果と確認値を照らし、最初の不一致を返します。エンジンの処理は変えていません。`kyuura_engine` の版は 0.154.0 です。閲覧用記録（U5）・状態の復元（U6）・合法手（U7）・異なる版と規約集合の比べ（`compare_runs`）は実装していません。

## 1. 基点と承認

- 基点: `6d659d0`（v0.153 の最後。`origin/claude/replay-record-u3`。`origin/main` の `8d4beff` はその祖先）。作業ブランチ `claude/replay-run-u4`
- 利用者の承認（2026-11-06。仕様案の `adoptions` の `ADOPT-U4`）: U4 の実装と限定検証、初期状態を含む確認値の照合、拒否を含む記録の seq の順の処理、失敗・不完全な記録と正常な成功の区別、`PYTHONHASHSEED` の影響の確認、受理した結果の停止の確認、確認値から `pending_moves` などを除く根拠の確認。閲覧用記録・スナップショット・未決の判断事項（D-SNAPSHOT-BASE・D-HALT-SNAPSHOT）の承認ではない

## 2. 公開した API（`kyuura_engine.replay_run`）

`replay(record)` → `ReplayRunReport`。流れ:

1. 構造の検証（`replay_record.validate_record`）。形式の不正・矛盾なら `invalid_record`（対戦を作らない）
2. 扱えるか（`support_problems`。実装・依存データ・Python の実装と版・乱数の方式・規約集合・形式）。扱えなければ `unsupported`（対戦を作らない）
3. 記録の初期の条件から `adapter.start_game` で対戦を作る（デッキリスト 2 つ・seed・規約集合。既定のカードプールとルールの組）
4. 最初の操作の前に、開始の status と確認値（状態・乱数・ログの長さ・区間・status・決定・停止のコード）を照らす
5. 記録の行を `seq` の順に、受理・拒否・失敗のどれも `adapter.submit` で送る（記録の `submitter`・`operation_id` を渡す。方策を再実行しない）
6. 行ごとに、`outcome`・`status`・`actor` と、受理なら確認値、拒否・失敗なら診断の識別・分類・元のコードを照らし、最初の不一致で止める。拒否では状態・乱数・ログが変わらないことも照らす
7. 終わりの情報（`status`・数・最後の確認値）を、最後の状態から計算した値と照らす

乱数を各操作の前へ戻さず、記録のコインの結果を入れません（記録の乱数の確認値は照らすだけ）。理由の文は照らしません（記録が文を持たない。説明用で版で変わりうる。v0.152 の約束）。

`ReplayRunReport` の項目: `status`・`executed`（対戦を作ったか）・`start_verified`・`verified_seq`（一致した最後の行。0 は開始だけ）・`verified_accepted`・`end_verified`・`mismatch`（`Mismatch`: `location`（`start`・`operation`・`end`）・`seq`・`accepted_index`・`items`（違った項目。決めた順）・`recorded`・`replayed`）・`failure`（再実行で起きた失敗の検証者用の記録。traceback を含む）・`problems`（構造・扱えるかの問題）。`succeeded` は `status == "succeeded"` のときだけ真。

## 3. 結果の区別

| status | 意味 | 成功か |
|---|---|---|
| `succeeded` | 閉じた（`closed`）記録の最後まで、開始・各行・終わりが一致した。決定待ち・停止（HALTED）・終局のどれで閉じた記録でも、その地点までの再現の成功 | はい |
| `incomplete` | 終わりの情報（`end`）のない記録で、あった行まではすべて一致した（`verified_seq` までの部分の確かめ） | いいえ |
| `recorded_failure` | `aborted` の記録で、失敗の行の前まで一致し、その行で同じ失敗（分類・識別・元のコード）がもう一度起きた | いいえ（失敗を含む結果） |
| `unsupported` | 形式の版・実装・依存データ・Python の実装と版・乱数の方式・規約集合を扱えない。対戦を作らない | いいえ |
| `invalid_record` | 形式の不正・内容の矛盾（U3 の構造の検証）、送り直せないコマンド。対戦を作らない（送り直せないコマンドはその行で止める） | いいえ |
| `diverged` | 再実行の結果・確認値・終わりの情報が記録と違った。`mismatch` に場所と項目 | いいえ |
| `internal_error` | 記録にない内部エラー・状態の不整合が再実行で起きた（未対応・不一致に変えない）。再実行の道具の中の例外も同じ | いいえ |

- 構造の検証で読める不完全な記録（`end` がない）は、あった行まで再実行して部分的に確かめる（成功に数えない）。壊れた JSON は `replay_record.loads_record` が読まない（救わない）
- `aborted` の記録で、失敗の行の操作が今度は受理された・別の結果になった場合は `diverged`（記録の失敗が起きなかった）
- `MemoryError` と、`Exception` の子でない終了（`KeyboardInterrupt`・`SystemExit` など）は捕まえない（adapter と同じ）

U3 の構造の検証で拒否するものと、U4 の再実行で見つけるもの:

| 書きかえ | 見つける段階 |
|---|---|
| 連番の欠け・順の違い、見出しと終わりの数の不一致、初期の条件の欠け、確認値の形の誤り | U3（`invalid_record`。再実行しない） |
| 実装の識別・Python の版・規約集合の照合値・形式の版の違い | U4 の扱えるかの確かめ（`unsupported`。再実行しない） |
| seed・デッキリストの並び（同じカードの組） | U4 の開始の照合（`diverged`・`start`） |
| 受理の行の確認値（状態・乱数・ログの長さ）、コマンドの値（ワザの番号）、拒否の行の元のコード、拒否の行を受理されるコマンドに変えたもの | U4 の行の照合（`diverged`・`operation`・その `seq`） |

終わりの情報の照合（`end`）は、構造の検証が「最後の確認値・status・数が最後の行と同じ」ことを確かめたうえで、最後の状態から計算し直した値とも比べる二重の確かめです（構造の検証を通った記録で、行の照合を通って `end` だけが違うことは起こらない）。

## 4. seq と accepted_index

- 送る順は `seq`（記録の行の順）。拒否を含む記録で、受理した行だけを先に送ってから拒否を確かめることはしない（拒否の行は、記録したときと同じ状態に送る）
- `accepted_index` は受理した行の連番の照合と、不一致の場所の報告に使う
- `operation_id` は対応付けのための値で、送る順にも、決定の番号（`answers_decision`・コマンドの `decision`）にも使わない
- 拒否を記録しない記録（`rejections_recorded` が偽）でも、受理した行だけで再現が成り立つ（テスト）

## 5. 確認値の保証の範囲と除いた項目

確認値は、形式 35 の書き出しを元にした、決めた範囲の確認値です。状態がすべて同じことの証明ではありません。

保証の分け方:

- 初期の条件・実装の識別・規約集合の識別が保証するもの: 同じ入力（デッキリスト・seed・規約集合）と、同じ内容のソースと同梱データ（カードデータ・効果の登録・ルールの組）で対戦を作り直していること。カードの定義・デッキリスト・規約集合の中身はここで決まる
- 各操作の確認値が保証するもの: 状態の書き出し（形式 35。`engine_version` を除く）の sha256・乱数の指紋・ログの長さ・区間・status・決定・停止のコードが、その操作のあとで同じこと

形式 35 の書き出しから除いた・入らない項目の確かめ（v0.154 で確かめ直した）:

| 項目 | 確かめた結果 |
|---|---|
| `definitions` | `new_game` がカード id とカードプールから作り、返す状態では変えない（`engine.py` の代入は `new_game`・区間の開始で前の値を引き継ぐところと、受け付けるかを確かめる複製（`_identity_trial_state`。返す状態にはしない）だけ）。カードデータは実装の識別に入る |
| `decklists` | `new_game` で決まり、区間の開始で引き継ぐ（`sudden_death.SEGMENT_FIELD_POLICY` が keep）。記録の `initial` に入る |
| `conventions` | 書き出しの `convention_set`（ID・版・照合値・構成）に入る。記録の見出しとも照らす |
| `engine_version` | 記録の見出しにある（lockstep の `DIGEST_EXCLUDED` と同じ扱い）。実装の識別は `behavior_digest` |
| 乱数の状態そのもの | 書き出しには指紋 `rng_state_sha256` が入る。記録の `rng` は同じ指紋（`rng_fingerprint`）で、不一致の項目を状態のほかの部分と分けて報告するために別に持つ |
| `pending_moves` | 下の段落 |

`pending_moves`（ワザの途中の場の移動への反応の、まだ処理していない段）: `state.py` の注釈は「コマンドの終わり・決定を待つ間は空。不変条件 `engine._pending_moves_problems`」と書くが、**その不変条件の関数は現行のコードにない**（`check_invariants` は `pending_moves` を確かめていない）。処理のコードでは、反応の順番などの決定を出すとき、残りの段を決定の `context` の `moves` に移してから状態の `pending_moves` を空にする（`resolution/programs.py` の `settle_moves`・`_settle_move_step`・`_apply_move`・`resume_moves`、`movement.take`）。決定の `context` は形式 35 の書き出しに入る（`serialize` の決定の `context`・`resume`）ので、決定をまたぐ続きの情報は確認値の範囲に入る。そのうえで、確認値の範囲の外の値がコマンドの境界に残っていないことを機械的に確かめるため、**U4 の再実行は、開始と受理した各行のあとで `pending_moves` が空であることを確かめ、空でなければ不一致（項目 `pending_moves`）にする**（`replay_run.boundary_items`）。この版で使った記録（7 章）では、どの境界でも空だった。注釈の不変条件の関数がないことは、エンジンを変えずに記録にとどめた（直すかは別の判断）。

確認値の方式（`state-export-35-sha256/1`・`python-random-getstate-sha256/1`）は変えていない（方式の名前を変えずに中身を変えることはしない。収集側も変えていない）。

## 6. PYTHONHASHSEED と環境

- 確かめたこと（`HashSeedTest`）: 同じ小さな固定記録（ピカチュウのデッキ・seed 9・方策の 70 手と拒否を混ぜたもの。Git のコミットの値は除いて比べる）を、`PYTHONHASHSEED` を 0・1・4242 にした別々のプロセスで作ると、記録の JSON（確認値を含む）が文字列として同じだった。その記録を `PYTHONHASHSEED=77` の別のプロセスで再実行すると `succeeded`
- 差は出なかったので、確認値の並べ方（鍵の順を決めた JSON）とエンジンの挙動のどちらの問題も見つからなかった。差を隠すための並べ直しは加えていない
- 確かめた環境: Windows 11・CPython 3.14.6 だけ。異なる OS・Python の版・実装では確かめていない（未確認）。扱える範囲は v0.153 の約束（Python の実装と major・minor が同じ）のままで、それ以上に広げない

## 7. 受理した結果の停止

- 既存の盤面を調べた: v0.127 のドライアップ（構築盤面）・v0.152 のテスト（構築盤面）は、U3 の「new_game から収集する」約束に合わない（途中の構築状態を記録の初期状態にしない）
- new_game からの合法な操作の列を、事前に限った少数の試行で探した: ファイヤー（ES2-005。ドライアップ）4 枚と「炎」56 枚、対 ラッキー 4 枚と「水」56 枚。ファイヤーはエネルギーをつけてドライアップで相手のバトル場を選び、ラッキーはエネルギーをつけて番を終える決まった手順（乱数を使わない）。seed 0〜15 のうち、seed 0・5・10・13 で、ドライアップの答え（`resolve_decision`）を受理した結果として途中停止（HALTED・`interruption` あり）になった。テストは seed 0（11 行）を使う
- この記録は `succeeded`（停止のコード・status・確認値まで一致）。見つからなかった seed は、ほかの理由（準備の停止・決まった手順の答えの拒否）で、到達できないことを示すものではない
- 開始時の停止（たねポケモン 1 枚のデッキ・seed 1）も `succeeded`

## 8. 利用例（実際の出力。ハッシュの一部は省略）

記録の読み取り・対応の確かめ・再実行・成功:

```python
from kyuura_engine.replay_record import loads_record, support_problems, validate_record
from kyuura_engine.replay_run import replay

record = loads_record(text)                 # 記録の JSON（ゲームの状態の復元ではない）
validate_record(record).status              # 'structure_valid'
support_problems(record.data)               # []（この実装・環境・規約集合で扱える）
report = replay(record)
report                                      # ReplayRunReport(status='succeeded', executed=True, verified_seq=227, verified_accepted=213, end_verified=True, mismatch=None)
```

最初の不一致（seq 31 の受理の行の乱数の確認値を書きかえた例。構造の検証は通る）:

```python
validate_record(changed).status             # 'structure_valid'（U3 では見つからない）
report = replay(changed)
report      # ReplayRunReport(status='diverged', executed=True, verified_seq=30, verified_accepted=28, end_verified=False,
            #   mismatch=Mismatch(location='operation', seq=31, accepted_index=29, items=('rng',)))
report.mismatch.recorded["rng"][:8], report.mismatch.replayed["rng"][:8]   # ('00000000', '620f3ef7')  検証者用の値（repr には出さない）
```

非対応（Python の minor の版を書きかえた例。対戦を作らない）:

```python
replay(changed)       # ReplayRunReport(status='unsupported', executed=False, verified_seq=0, ...)
[(p.kind, p.code) for p in replay(changed).problems]     # [('unsupported', 'runtime_differs')]
```

不完全・aborted:

```python
replay(collector.record())   # 閉じる前の記録: ReplayRunReport(status='incomplete', executed=True, verified_seq=64, verified_accepted=60, end_verified=False, ...)
replay(aborted_record)       # 失敗の行で同じ失敗が起きれば 'recorded_failure'、起きなければ 'diverged'。どちらも成功ではない
```

## 9. 情報境界

- 記録と再実行の結果は検証者用。`view_for`・観測に記録・確認値を渡さない。`ReplayRunReport`・`Mismatch` の repr は状態・場所・項目の名前だけで、確認値・記録の値・例外の文を出さない（値は `recorded`・`replayed`・`failure` の項目で、検証者が読む）
- 再実行の失敗の traceback は `failure.traceback`（検証者用）だけ

## 10. 検証（限定）と結果

`tests/test_replay_run_v0_154.py`（盤面は 1 行目の説明）:

- 成功: サドン・デスと延長戦（拒否あり）・拒否を省いた記録・終局・受理した結果の停止・開始時の停止・決定待ちで閉じた記録・3 つの規約集合・JSON の往復のあと
- 順: 送る順が seq の順（受理・拒否の行の operation_id の並びが記録と同じ）、拒否の行と受理の行を入れかえた記録・拒否の行を受理されるコマンドに変えた記録を見つける
- 見つける段階: 構造の誤りは再実行しない、初期の条件の違いは開始で、確認値・コマンド・元のコードの違いはその行で、扱えない記録は再実行しない、境界に残った `pending_moves` を見つける
- 不完全・失敗: 閉じる前の記録・後ろを切った記録は incomplete、aborted の記録は diverged か recorded_failure、記録にない内部エラー・道具の中の例外は internal_error、終了の例外は捕まえない
- PYTHONHASHSEED（6 章）、境界（repr）、既存の API

結果は 11 章に書きます。

## 11. 検証の結果

限定検証だけを実行した（全体テスト・全 108 組・4,356 局・lockstep・ストレス実行はしていない）。終了コードは確かめの本体から。

- `tests.test_replay_run_v0_154`: 23 テスト OK（約 20 秒。`HashSeedTest` の別プロセス 4 つを含む）
- U3・U1・U2 の関係: `tests.test_replay_record_v0_153`（25）・`tests.test_diagnostics_adapter_v0_152`（37）・`tests.test_diagnostics_replay_api_design`（20）・規約集合の識別と照合値
  （`test_conventions_v0_142` の `IdentityTest`・`RecordsTest`）: OK。期待を変えたテスト 1 つ（目的は同じ）: v0.153 の `test_spec_adoptions` は、U4 の状態を planned と固定していたのを、
  v0.153 の採用の記録（`ADOPT-U3`）の中身と、実装済みの単位が採用の記録の単位と同じことを確かめる形にした
- 版のテスト（`test_preset_decks_v0_20` の `test_version`）と、変えた文書（README・実装状況・データの来歴）を読む既存のテストのメソッド 16 件: OK
- 生成物の `--check`: `build_diagnostic_catalog`・`build_diagnostics_replay_api_design`・`build_stop_policy_classification`・`build_play_policy_family_plan`・`build_convention_records`・
  `check_implementation_assumptions`・`check_normalization_revalidation` のすべてが終了コード 0（停止の方針の台帳・同梱の規約集合の記録・診断のコード表は変えていない）
- ruff 0.17.2（基点と同じ版・設定）: 新しいファイルに指摘なし。新しい抑制（`noqa`）はない
- `check_implementation_assumptions.py --sites`（基点の木と比べた差）: 版のテストの行に版の注記を足して識別が変わった 1 件（新しい 1・消えた 1。件数は同じ 1757）。実装上の仮定ではない。文面は変えていない
- 途中で直したこと: 結果の定数の名前（`UNSUPPORTED_RUN`）が停止の方針の台帳の走査に停止コードの形として数えられたので、`NOT_SUPPORTED` にした（値は `unsupported`。台帳は変えていない）。
  テストの誤り 3 つ（デッキリストの書きかえで同じカードが 5 枚になり開始が拒否された・ワザのコマンドの項目名・repr の確かめで小さな数を探した）を直した

## 12. U5 への引き継ぎと残る判断

- U5（閲覧用記録）は、完全な記録（または進行中の状態）から見る人ごとの記録を作る。完全な記録の `operations` の `command`・確認値・`header.initial` を見る人の記録に写さない。見る人ごとの値は、観測（`observe`）・ログの写し（`visible_log`・`visible_segment_logs`）・`CommandResult.view_for` から作る。双子の完全な記録から作った相手・観戦者の記録が同じことを確かめる（v0.152 の双子の比べを記録に広げる）
- U4 の `replay` で、閲覧用記録の元にした完全な記録が再現できることを、U5 の確かめの前提にできる
- 残る判断: D-SNAPSHOT-BASE・D-HALT-SNAPSHOT（保留）、閲覧用記録の版の決め方（D-VERSIONS の採用は再現用記録の部分だけ）、`pending_moves` の不変条件の関数がないことを直すか
- 未確認: 異なる OS・Python の版での確認値、長い対戦・多数の記録での再実行（全 108 組・4,356 局・lockstep は実行していない）
