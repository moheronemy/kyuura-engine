# 状態スナップショット（v0.157・U6 の S1〜S4・S6）

[仕様](state-snapshot-design.md)の U6「JSON の状態の保存・復元」のうち、S1（型の対応表と書き出し）・S2（安全な読み取りと対応の確かめ）・S3（組み立てと整合の確かめ）・S4（保存・復元のあとの継続の一致）・S6（最小のホストへの接続）を実装した版です。`kyuura_engine` の版は 0.157.0 です（0.156.0 は使っていない。v0.156 は仕様だけの作業で、版は 0.155.0 のままだった）。

S5（完全な再現用記録の途中から再開して U4 で照らす）は実装していません（9 章）。エンジンの処理（`engine.py`・`resolution/`・観測・アダプタ・U3〜U5 の記録）は変えていません。新しいモジュール `kyuura_engine/snapshot.py` を加えただけです（実装の識別ではゲームの挙動の側のファイルに入るので、`behavior_digest` は変わる。3 章）。

## 1. 基点と範囲

- 基点: `8db7350`（v0.156 の仕様の最後。`origin/claude/state-snapshot-spec`。`origin/main` の `8d4beff` はその祖先）。作業ブランチ `claude/state-snapshot-impl`
- 最初に仕様を 2 つ訂正した（実装とは別のコミット）: 分類の数の集計（状態の dataclass の項目・項目でない値・見出しの補助情報を分けた）と、カードの uid の扱い（作り直さず値で保存する）。[仕様 4 章](state-snapshot-design.md)
- 採用した判断 6 件（`ADOPT-U6-IMPL`。[実装計画 5 章](state-snapshot-implementation-plan.md)）: DS-CONSTRUCTED・DS-HALT-TEXT・DS-CHECK・DS-DEPTH・DS-RECORD-LINK・DS-INSTRUMENTATION
- しないこと: S5、旧形式（形式 1〜35・pickle）からの自動移行、異なる規約集合での再開、停止の解除、既定でないカードプール・効果の登録表、合法手・AI・画面・通信、閲覧用記録の圧縮、実装の識別の方式の変更

## 2. 公開 API と責任

| API | 責任 | 失敗のとき |
|---|---|---|
| `save_snapshot(state, *, origin=None, label=None, include_git=False)` | 書き出し（S1）。保存の境界と登録・型の表現を確かめ、全項目を JSON の値にする。状態・乱数・ログを変えない | `SnapshotSaveError`（`code`・`kind`・`path`。部分的な結果を返さない） |
| `dumps_snapshot(snapshot)` | JSON の文字列（鍵の順は保存した順。ログのイベントの鍵の順を保つため並べかえない） | — |
| `loads_snapshot(text)` | 安全な読み取り（段 1。`replay_record.read_json_object`） | `replay_record.RecordFormatError` |
| `restore_snapshot(snapshot_or_text)` | 復元（段 1〜7）。不正な入力で例外を投げない | `RestoreReport` の `status`（restored 以外では `state` は None） |
| `RestoreReport` | 結果の検査: `status`・`problems`（種類・コード・JSON の経路）・`restored`・`message`（決まった文）・`game_status`。internal_error の `exception_type`・`traceback` は検証者用（repr に出さない） | — |
| `RestoredGame(report, *, viewers=())` | ホストへの接続（S6）。restored の結果だけから `adapter.HostedGame` で続ける。閲覧用記録は `ViewRecorder.attach` から | `SnapshotNotRestoredError` |
| `codec_fields()`・`codec_problems()`・`structure_problems(state)` | 型の対応表の内容と漏れ・保存と復元に共通の構造の確かめ（仕様の `--check` とテストが使う） | — |

例外の扱いは `adapter` と同じ: 復元の中の想定外の例外は `internal_error`（不正・非対応に変えない）。`MemoryError` と、`Exception` の子でない終了（`KeyboardInterrupt`・`SystemExit` など）は捕まえない。保存の中の想定外の例外は、そのまま呼び出し元へ伝わる（保存できない状態の `SnapshotSaveError` とは別）。`restore_snapshot` に `StateSnapshot`・文字列・バイト列でないもの（辞書など）を渡すと `TypeError`（使い方の誤り）。

既存の `new_game`・`apply_command`・`observe`・U1〜U5 の API と契約は変えていない。U3 の収集器（`ReplayCollector`）は今までどおり新しい対戦の開始からだけ作る（途中の状態を渡せるようにしていない）。

### 2.1 利用例

```python
from kyuura_engine import adapter, snapshot as SN
from kyuura_engine.commands import EndTurn, ResolveDecision

# 状態の保存と JSON の書き出し（ホストの中だけ）
snap = SN.save_snapshot(state, origin={"game_id": "g-1", "seq": 42}, label="before turn 7")
text = SN.dumps_snapshot(snap)

# JSON の読み取りと復元・結果の確かめ
report = SN.restore_snapshot(text)
if not report.restored:
    print(report.status, [(p.code, p.path) for p in report.problems])  # 入力の値は入らない

# ホストへ接続して続ける（決定待ちなら答えを送る）
game = SN.RestoredGame(report, viewers=(0, 1, None))
d = game.state.decision
result = game.submit(ResolveDecision(d.player, d.id, d.options[:d.min_choices])) if d else game.submit(EndTurn(game.state.current_player))
view = result.view_for(0)            # 本人への結果（安全な文だけ）
record = game.view_record(1)         # 閲覧用記録（origin は attached）

# 停止の状態の復元: 停止のまま。操作は拒否され、状態は変わらない
halted = SN.RestoredGame(SN.restore_snapshot(SN.dumps_snapshot(SN.save_snapshot(halted_state))))
assert halted.status == "halted" and not halted.continuable
assert halted.submit(EndTurn(0)).outcome == "rejected"

# 保存できない状態・非対応・不正な入力
try:
    SN.save_snapshot(state_with_pending_moves)
except SN.SnapshotSaveError as error:
    print(error.code, error.kind)    # pending_moves boundary
assert SN.restore_snapshot("{not json").status == "read_error"
```

## 3. 保存する内容と型（S1）

- 形式: `kyuura_snapshot_format` = 1。見出しは `engine`（U3 と同じ実装の識別）・`runtime`・`dependencies`（ルールの組・カードプール `default`・カードデータの写しの元・効果の登録表の id）・`convention_set`（`ConventionSetIdentity.record()`）・`formats`・`check`（U3 の確認値）・`state`。任意の `origin`（`game_id`・`seq`）・`label`・`git_commit` は説明用で、復元に使わない
- `state` は GameState の項目を dataclass の順に持つ。分類（[仕様 4 章](state-snapshot-design.md)）のとおり、value の項目は値、resolve の `rules`・`definitions`・`effects`・`conventions` は識別（ルールの組の id・カードの id の並び・登録表の id・規約集合の記録）、absent の `pending_moves` は入れない
- 型の対応表は `state.py` の dataclass の項目の注釈（文字列）を、決まった形の型の式に読みかえて作る（`int`・`str`・`bool`・`None`・`Any`・`Phase`・`EnergyType`・state.py の dataclass・`list[…]`・`tuple[…, ...]`・`tuple[A, B]`・`Mapping[str, Any]`（ログのイベント）・その union）。知らない形の注釈は対応表の漏れ（`codec_problems`）で、保存を拒む。型の名前は state.py の dataclass の許した一覧だけから引き、入力の型の名前・モジュールの名前からクラスを読み込まない
- リストとタプル: 注釈が `list` の項目（領域・ついているエネルギー・トレーナー・プレイヤー・ベンチ）はリストに、ほかの配列はタプルにもどす。値の型が注釈と違えば（タプルの位置のリストなど）表せないものとして保存を拒む
- 注釈が `Any` の位置（ログのイベントの値・決定の context の値・持続する効果・履歴）は、整数・文字列・真偽値・None・タプル（配列）・値の記録（`{"type", "fields"}`）・列挙（`{"enum", "value"}`）だけを表す。リスト・辞書・浮動小数・ほかの型は文字列にして保存する代わりの処理をせず、保存を拒む（`unrepresentable_value`）
- 真偽値と整数を取り違えない（`type(x) is int`）。浮動小数は受けない（乱数の `gauss_next` も None だけ）
- `cards` は CardInstance（uid・card_id・owner・origin）の配列（対応表の並びの順）。鍵は uid から作り直し、uid の重なりは不正。uid は名前・場所から付け直さない（仕様 4 章の訂正）
- ログのイベントは JSON のオブジェクトで、鍵の順を保つ（書き出しで鍵を並べかえない）
- 乱数: `random.Random.getstate()` の版・625 個の整数をそのまま保存し、復元では範囲と形を確かめて `setstate` する

カード定義・効果の登録表・ルールの組・規約集合は登録済みのものを解決する: 定義は既定のカードプール（`load_card_pool`）の `get`、効果の登録表はその `effects`、ルールの組は `replay_record.KNOWN_RULES`、規約集合は `conventions.registered_identity` と記録の一致。初版は、既定でないカードプール・登録表（テストで差し替えた登録表を含む）と、規約集合の記録がない旧状態（UNRECORDED）を扱わない。「構築盤面の保存を許す」（DS-CONSTRUCTED）は、任意のカード定義・処理を入力から登録できる意味ではない。

## 4. 保存の境界と、復元の前後の確かめ（S1〜S3）

保存の前（`save_snapshot`。どれかを満たさなければ `SnapshotSaveError`。状態を変えない・正規化しない）:

| コード | 種類 | 確かめ |
|---|---|---|
| `not_game_state`・`transient_attribute`・`missing_attribute` | boundary | GameState であり、`__dict__` が dataclass の項目と同じ（`_history_probe` などの一時的な属性がない） |
| `pending_moves` | boundary | `pending_moves` が空のタプル（`check_invariants` は確かめないので、ここで拒む） |
| `conventions` | unsupported | 規約集合の識別が記録され、登録の内容と同じ（UNRECORDED・登録と違う識別は拒む） |
| `decision_resume` | unsupported | 保留中の決定の再開先をこの版が扱える（`supported_decision_error`） |
| `rules`・`effects`・`card_pool` | unsupported | ルールの組が登録のもの、効果の登録表が既定のカードプールの登録表そのもの、写しの元と定義が既定のカードプール |
| `invariants`・`structure` | boundary | `check_invariants` と `structure_problems` が空 |
| `unrepresentable_value`・`too_deep`・`too_large` | unrepresentable | すべての項目を型の対応表で表せる、深さ・大きさが上限の中 |

`structure_problems` は `check_invariants` が見ない整合: cards の鍵と CardInstance.uid、definitions の鍵と cards の card_id の集まり、プレイヤーが 2 人、決定の id が採番の状態より小さい、場のポケモンの番号が重ならず採番の状態より小さい、過去の区間の番号が並びの位置と同じ。

復元（`restore_snapshot`）の 7 つの段と結果は[仕様 7 章](state-snapshot-design.md)の表のとおり。どの段で止まっても状態を返さない（部分的な状態を作っても、通常の対戦に渡さない）。

- 段 2 の malformed（見出しの形・知らない項目・欠けた項目）と、知らない形式の版の unsupported
- 段 3 の unsupported: `behavior_digest`・`instrumentation_digest`（DS-INSTRUMENTATION）・エンジンの版・Python の実装と major・minor・乱数の方式・確認値などの形式・ルールの組・カードプール・カードデータ・効果の登録表・規約集合（登録と記録の一致）
- 段 4: 状態の項目の過不足（malformed）、状態の識別と見出しの依存の食い違い（inconsistent）、知らない card_id（unsupported）
- 段 5 の malformed: 型（bool と int・浮動小数）・列挙の値・型の印（知らない名前・その位置で許さない型）・項目の過不足・dataclass の値の確かめ・uid の重なり・乱数の形
- 段 6: 知らない再開先（unsupported）、`structure_problems`・`check_invariants`（カードの保存則・uid の参照先・所有者・場の形・decklists と cards）・規約集合（inconsistent）、そのあと確認値と、もう一度保存した JSON の一致（inconsistent）

確認値（DS-CHECK）は復元の結果を照らすためのもので、署名・認証・改ざんの防止ではない。作り直せるので、壊した状態から確認値を作り直した入力も、構造・不変条件の確かめで inconsistent になる（テスト `test_rebuilt_check_does_not_hide_a_broken_state`）。

誤りの文: `RestoreReport.message` は結果の種類ごとの決まった文、`problems` はコードと JSON の経路（項目の名前と位置）だけで、入力の値・seed・カードを入れない。`SnapshotSaveError` の文もコードと経路だけ。

## 5. 状態別の保存・復元・継続

| 状態 | 保存・復元 | 復元のあと（保存しない状態と同じ） | 確かめた盤面 |
|---|---|---|---|
| 通常の対戦中・準備中 | できる | 同じ操作を同じ結果で受理・拒否 | F1・F2 |
| 準備中・ワザ・トレーナーの決定待ち（context に処理の続き） | できる | 答えの処理の続きが同じ | F2 |
| 受理した結果の途中停止・HALTED | できる（停止の文も保存。DS-HALT-TEXT） | どの操作も拒否。停止を解除しない・規約集合を差し替えない | F4 |
| 終局 | できる | どの操作も拒否 | F5 |
| サドン・デスの開始待ち・延長戦の途中・複数の区間 | できる | 保存した乱数の続きで延長戦の準備を切る。区間の記録・初期の所有者・uid を保つ | F6 |
| pending_moves・一時的な属性・不変条件・構造の外 | 拒む | — | 保存の境界のテスト |
| UNRECORDED・知らない再開先・既定でない登録 | 拒む | — | 同上 |

停止の診断用の文は閲覧者へそのまま出さない（`public_halt` の安全な文だけ。テストで、復元した停止の状態の `view_for`・観測・閲覧用記録に文が出ないことを確かめた）。

## 6. 継続一致の確かめ（S4）と、F1〜F9 の対応

テスト `tests/test_state_snapshot_v0_157.py` は、保存しない状態と、保存して復元した状態へ同じ操作の列を送り、各境界で次を比べる: 保存した全項目（スナップショットの `state`）・U3 の確認値・乱数の状態・今と過去の区間のログ・本人と相手と観戦者の観測・操作の結果（outcome・status・stage・診断・停止の公開の診断・次の操作・規約・3 者への `view_for`・検証者用のコードと文）。

| ID | 場面 | 盤面（合法な列・構築盤面） | テスト |
|---|---|---|---|
| F1 | 通常の操作 | ピカチュウの方策 seed 9（new_game から。準備・40・80 番目の受理のあとで保存し、続けて比べる） | `LegalSequenceTest.test_f1_f3_f7_normal_play_in_three_sets` |
| F2 | 準備中・対戦中の決定待ち（context に処理の続き） | 準備の各段階（たねの少ないデッキ。seed は 40 個まで）・ドライアップの対象の決定（new_game から）・挑戦状の受けるかの決定（構築盤面。使用中のトレーナー・置いておくカード・context あり） | `DecisionTest` |
| F3 | 拒否の操作 | F1 の列に、番でないプレイヤーの番の終わり・違う id の答えを混ぜる。復元のあとも同じ診断で拒否され、状態が変わらない | F1 と同じ・`HaltTest` |
| F4 | 途中停止・HALTED | ドライアップ seed 0（受理した結果の途中停止。new_game から）・たねポケモン 1 枚のデッキ seed 1（準備の停止）。どの操作も拒否・停止の文を閲覧者に出さない | `HaltTest` |
| F5 | 終局 | ピカチュウ seed 0（new_game から） | `LegalSequenceTest.test_f5_game_over_rejects_everything` |
| F6 | サドン・デスの開始・複数の区間 | ピカチュウ seed 9（開始待ちで保存 → StartSuddenDeath、延長戦の途中で保存） | `LegalSequenceTest.test_f6_sudden_death_and_segments` |
| F7 | 規約が当てはまる操作 | 3 つの集合で F1。S2a の切り直しの補償（new_game から。ログ convention_applied）・S2a の両方ねむり（構築盤面）・PO の［ポイズンミスト］とどく（構築盤面） | `test_f1_…`・`ConstructedBoardTest.test_f7_*` |
| F8 | 持続する効果・マーカー・うらのカード・所有者の交換・同名のカード | マチスの秘策（うらのカード）・とりかえっこプリーズ（同名のコラッタどうしの交換。origin）・かたまる・マーカー（構築盤面）、同名のカードの uid（new_game から） | `ConstructedBoardTest.test_f8_*`・`test_same_name_cards_keep_their_uids` |
| F9 | 不正・非対応・不整合の入力 | 読めない JSON・NaN・重なった鍵・大きすぎる・深すぎる、知らない項目・欠けた項目・bool と int・浮動小数・列挙の値・型の印・uid の重なり・乱数の形、形式の版・実装・部品の識別・Python の版・乱数の方式・ルールの組・カードプール・カードデータ・登録表・規約集合・知らないカード・知らない再開先、確認値の違い・乱数の違い・依存と状態の食い違い、確認値を作り直した壊れた状態、内部エラーの区別 | `InvalidInputTest`・`SaveBoundaryTest` |

構築盤面（`tests.helpers.build_test_state`）と new_game からの合法な操作の列を分けて書いた（テストの説明）。構築盤面は保存・復元できることだけを確かめ、new_game から合法に到達できることは保証しない（DS-CONSTRUCTED）。

## 7. ホストへの接続と完全な記録の境界（S6）

- `RestoredGame` は restored の `RestoreReport` だけから作る（ほかの結果・状態のない結果は `SnapshotNotRestoredError`）。中は `adapter.HostedGame` で、受理・拒否・処理できない結果の扱いは U2 と同じ
- `status`・`continuable` は状態の値から決める（停止・終局を活動中とみなさない）。規約集合を差し替える API・停止を解除する API はない
- `full_record` はいつも None。保存の前からの完全な再現用記録を持っているようには扱わない。U3 の `ReplayCollector` は新しい対戦の開始からだけ作る（途中の状態から作る入口を加えていない）。完全な記録との接続は S5
- 閲覧用記録は、復元した時点から `ViewRecorder.attach` で始める（`origin` は attached）。始まりの項目の過去のログは復元した時点の投影で、保存の前の各イベントの時点の知識を復元したとは保証しない（[仕様 2 章](state-snapshot-design.md)）
- 見る人には `view`・`view_record`・`CommandResult.view_for` の結果だけを渡す。`state`・スナップショットはホストの中だけ（テストで、閲覧用記録に乱数・確認値・形式の名前・実装の識別が出ないことを確かめた）

## 8. 検証と未確認

限定の検証だけを実行した（全体のテスト・全 108 組・4,356 局・lockstep の全体・広いストレス実行はしていない。重い処理は並行させていない。終了コードは確かめの本体から）。

| 検証 | 結果 |
|---|---|
| `tests.test_state_snapshot_v0_157`（新しいテスト。F1〜F9・保存の境界・情報境界・ホストへの接続・対応表） | 36 件 OK |
| `tests.test_state_snapshot_design`・`tests.test_diagnostics_replay_api_design`（仕様・分類・対応表の照合） | 33 件 OK |
| U1〜U5 の直接関係するテスト（`test_diagnostics_adapter_v0_152`・`test_replay_record_v0_153`・`test_replay_run_v0_154`・`test_view_record_v0_155`）と版のテスト（`test_preset_decks_v0_20`） | 37＋72＋15 件 OK |
| 生成物の `--check` 8 本（スナップショットの仕様・診断の仕様・診断のコード表・停止の方針の台帳・同梱の規約集合の記録・実装上の仮定・正規化の再確認・共通規約の設計案） | すべて終了コード 0 |
| ruff 0.17.2（新しい・変えたモジュール・テスト・スクリプト・道具） | 指摘なし。新しい抑制なし。停止の台帳の語（`UNSUPPORTED_…`・`UNRESOLVED_…`）と `RuntimeError` の送出を加えていない |
| `check_implementation_assumptions.py --sites`（基点 `8db7350` の木と比べた差） | 4 件増・1 件減（下の分類） |

`--sites` の差の分類（文面は変えていない）: 増えた 3 件は、保存の境界の説明の「保存のために状態を変えない・正規化しない」という方針の文（`docs/state-snapshot-design.md`・`scripts/build_state_snapshot_design.py`・この文書）で、実装上の仮定ではない。残りの 1 件増・1 件減は、版のテストの経緯の注釈の行（`tests/test_preset_decks_v0_20.py` の 151 行。v0.132 の利用者指定の経緯を含む既存の行）に 0.157.0 を書き足して識別が変わったもの。

限定の監査（テストの結果は変えずに、new_game・apply_command が返す前の位置（`engine._require_integrity`）で保存と復元を試す。コマンドの処理の途中の位置も含む）:

v0.158 の訂正: この節は v0.157 で「`python -m tools.snapshot_audit` で 434 件のテスト・訂正のあと 24,694 の状態」と書いていたが、残っている証拠（作業用の出力ファイルと作業の記録）で確かめると、次のとおりだった。監査は再実行していない（件数を合わせるための再実行はしない）。

- 実行したコード: 作業用の監査の道具（作業用ディレクトリの `audit.py`。コミットしていない）と、その時点のコミット前の `snapshot.py`。コミットした `tools/snapshot_audit.py` は同じ数え方で書き直したもので、それ自体は実行していない
- 最後の結果として確かめられるもの（実行 D）: とりかえっこプリーズ v0.130（2 つ）・サドン・デス v0.134・スタジアム v0.57・エネルギーの役割と力の停止 v0.59・見えないカードのトレーナー v0.63・途中停止 v0.127・ミュウの退化 v0.50・ばける v0.49 の 9 つのテストのモジュール（317 件のテスト）で、型の対応表の訂正のあとに、18,461 の状態を保存して restored で復元した。保存を拒んだのは、テストが差し替えた効果の登録表の 29 の状態（`effects`。対応の外）だけ。深さは最大 13（上限 64）
- 24,694・33・434 件は、実行 D と、訂正の前の実行 A（マチスの秘策 v0.67・マーカー v0.90・かたまる v0.4b の 117 件のテスト。6,233 の状態が restored・`effects` の拒否 4・深さは最大 12）を足した数で、1 回の実行の結果ではない。実行 A の 3 つのモジュールは訂正のあとに走らせていない（実行 A に表せない値はなかったが、訂正のあとの結果としては未確認）

| 実行 | コードの時点 | 対象 | テスト | restored | 保存の拒否 | 深さ |
|---|---|---|---|---|---|---|
| A | 訂正の前 | v0.67・v0.90・v0.4b | 117 | 6,233 | effects 4 | 12 |
| B | 訂正の前 | 上の 9 つ | 317 | 18,447 | effects 29・unrepresentable_value 14（`power_uses_this_turn`） | 13 |
| C | 訂正のあと | v0.49・v0.50 | 114 | 9,077 | なし | 12 |
| D | 訂正のあと | 上の 9 つ（C の 2 つを含む） | 317 | 18,461 | effects 29 | 13 |

- 実行 B で、`power_uses_this_turn` の 14 の状態を表せなかった（のせたカードの特殊能力の記録は 3 つの値。v0.49 の `effects.power_use_record`。注釈は 2 つのまま）。正当な値なので、型の対応表の訂正（`HINT_OVERRIDES`。2 つか 3 つの整数だけ）で扱い、テストを加えた。検査は緩めていない
- 途中の報告の「18,461・拒否 29」は実行 D の結果。最終の報告の「24,694・拒否 33」は A と D の合計（訂正の前と後の実行を足した数）
- 各実行のときの `snapshot.py` の内容は別に残していない（実行 D のあとコミット 80504fc までに変わったかは未確認）

未確認:

- 監査の対象のほかのテストの盤面・カード（全体のテストは実行していない）。ほかの場面で表せない値が出れば、保存は `unrepresentable_value` で拒む（文字列にして保存することはない）
- 長い対戦・すべての決定の種類での深さ（監査とテストの範囲では 13）
- OS・Python の版をまたぐ復元（この環境だけ。保証は U3 の範囲: 実装と major・minor が同じ）
- 構築盤面が new_game から合法に到達できるか（保証しない）
- 大きさの上限に近い実際の状態（テストは上限を小さくした読み取りの拒否だけ）

## 9. 次の作業（S5 など）への引き継ぎ

- S5: 完全な再現用記録の k 行目のあとの状態のスナップショット（`origin` に `game_id`・`seq`）から、残りの行を U4 と同じ語彙で照らす。対応付けは任意の補助情報（DS-RECORD-LINK）なので、記録とスナップショットの一致（`check` と記録の行の確認値）を S5 で確かめる。U3 の収集器を途中から作る入口は、別の判断として扱う
- 既定でないカードプール・登録表・旧状態（UNRECORDED）を扱うなら、識別の方式と登録の解決の方法を別に決める（今は unsupported）
- Python の版・OS をまたぐ保証は、U3 の範囲（実装と major・minor が同じ）のまま。別の環境での確かめはしていない
