# v0.152: 診断の型と情報境界（U1）・コマンド実行結果のアダプタ（U2）

[仕様案](diagnostics-replay-api-design.md)の U1・U2 を実装した版です。エンジンの処理（`apply_command`・`new_game`・`observe`・例外・停止・決定）は変えず、その結果を読んで、診断と見る人ごとの結果を作る新しいモジュールを加えました。`kyuura_engine` の版は 0.152.0 です。

## 1. 基点と採用

- 基点: `274c903`（仕様案の最後。`origin/claude/diagnostics-replay-api-spec`。`origin/main` の `8d4beff` はその祖先）。作業ブランチ `claude/diagnostics-u1-u2`
- 利用者の採用（2026-11-06。仕様案の JSON の `adoptions` の `ADOPT-U1-U2`）: U1・U2 の実装と、次の 6 つの方針だけ。仕様案のほかの判断事項（実装の識別・Python の環境をまたぐ再現・確認値の密度・スナップショットの形式・版の分け方・停止状態のスナップショット）は保留のまま
  1. 本人向けの説明は、原則としてコードに対応する安全な定型文（D-MESSAGE。仕様案の推奨の「生の文」ではない）
  2. 生の例外文と内部の詳細は検証者用で、通常の閲覧者へ渡さない
  3. 状態の不整合は、本人にも一般的な説明だけ（D-STATE-INTEGRITY-VIEW）
  4. 未登録のコードを推測で未裁定・未対応に分類しない。診断の対応漏れとして検出する
  5. 拒否された操作は、将来の完全記録へ任意で残せる設計にする。受理した操作の再現とは区別する（D-REJECTED。この版は記録をしない）
  6. 対戦後も情報の公開範囲を自動では広げない（D-POSTGAME）
- しないこと: 対戦記録の収集・再現、JSON の状態の読み込み、合法手の一覧、画面・通信、AI、続行規約、停止からの再開

## 2. 公開した API

新しいモジュールは 2 つです（`kyuura_engine/__init__.py` の `__all__` には加えていません。既存の名前・入口は同じ）。

| もの | 内容 |
|---|---|
| `kyuura_engine.adapter.submit(state, command, *, submitter=None, operation_id=None)` | `apply_command` を包み、`CommandResult` を返す。`state` は変えない。`submitter`（ホストが確かめた送り手）がコマンドの `player` と違えば、エンジンに渡さずに拒否（`SUBMITTER_MISMATCH`） |
| `kyuura_engine.adapter.start_game(deck0, deck1, seed, **options)` | `new_game` を包む。seed が 0 以上の整数でなければ `new_game` を呼ばずに拒否（`INVALID_SEED`）。デッキ・規約集合の拒否も同じ形 |
| `kyuura_engine.adapter.HostedGame` | 信頼されたホストが状態を持つ最小の境界。受理したときだけ状態を進め、処理できない結果のあとは操作を受け付けない（見る人は状態を持たないので、コインを見たあとに前の状態からやり直せない） |
| `CommandResult` | `outcome`・`status`・`stage`・`actor`・`operation_id`・`state`・`diagnosis`・`halt`・`continuable`・`next`・`convention_set`・`verifier`。組み合わせの矛盾は作るときに `ValueError` |
| `CommandResult.view_for(viewer)` | 見る人（0・1・None）ごとの結果。本人は `ActorDiagnostic`、相手・観戦者は `StatusNotice`、拒否は本人のほかに `None` |
| `kyuura_engine.diagnostics` | 語彙（分類・結果・状態・処理段階）、`Catalog`・`default_catalog`、`classify_error`・`classify_halt_code`、`status_of`・`next_actions`・`continuable`、閲覧用の型、`VerifierReport` |

結果（outcome）と状態（status）:

| outcome | status | state | 意味 |
|---|---|---|---|
| `accepted` | `in_progress`・`awaiting_decision`・`halted`・`game_over`・`sudden_death_pending` | 新しい状態 | 受け付けた。`halted` は受け付けた結果の停止（拒否ではない。`halt` に公開の診断） |
| `rejected` | 元の状態の status（対戦の開始の拒否は `not_started`） | 渡した状態そのもの（開始の拒否は None） | 拒否して元の状態（状態・乱数・ログ）を保った |
| `failed` | `unavailable` | None | 処理できなかった（状態の不整合・内部エラー）。元の状態で続けることを保証しない |

- `continuable` は、実際の状態（段階・規約集合・保留中の決定の再開先）から決める。分類からは推測しない。`failed` はいつも偽
- `next` は次に受け付けうる操作の種類（`place_starting_pokemon`・`draw_mulligan_cards`・`report_janken_result`・`turn_action`・`answer_decision`・`start_sudden_death`）と送るプレイヤー（決まらなければ None）。合法手の一覧ではない（どれも観測で全員に見える段階・番・決定から決まる）
- `stage` は送った操作の処理段階（`setup`・`turn_action`・`decision_answer`・`segment_start`・`state_check`・`submission`）。コマンドの種類と公開の段階から決まる。`state_check` は、状態そのものの確かめ（規約集合・再開先）による拒否
- 将来の記録との対応: `operation_id`（ホストが付ける）・`actor`・`outcome`・検証者用の記録のコマンド（`command_to_dict`）。この版は記録を作らない

## 3. コード表と分類

コード表（`kyuura_engine/data/diagnostic_catalog.json`）は `scripts/build_diagnostic_catalog.py` が作ります（手で直さない。`--check` が漏れと違いを見つける）。

- 中身: エンジンが返す元のコード 479 個 → 分類・事例・決まった文。停止の方針の台帳の停止コード 356（研究上の停止 316・実行時の停止 40。台帳の分類 C → 未裁定、B → 技術的制限 5、A → 未対応 31・互換性 3（仕様案の `compatibility_codes`）、E は理由を書いた `UNRESOLVED_RULING` だけ）と、台帳の外のコード 123（`IllegalActionError` の 120・`STATE_INTEGRITY`・`INVALID_DECK`・`INVALID_CONVENTION_SET`）。台帳の外のコードは台帳に加えていない（別の集合）
- 不正な操作のコードはエンジンのソースの `IllegalActionError(...)` から集める。f 文字列・変数・タプルの展開の呼び出し箇所（9 か所）は `DYNAMIC_SITES` に作りうるコードを書く。表にない動的な呼び出し箇所・ソースにない表の行は `--check` の問題になる。関数の中の変数を定数として読まない（大文字のモジュール・クラス直下の定数だけ）
- 事例: 場面の索引でコードの場面が 1 つなら、その場面を事例にする。2 つ以上（9 コード。`UNRESOLVED_STATED_CARDS_SHORT` など）は選ばない（`not_identified`）
- 分類の手順（`diagnostics.classify_error`）: EngineError でない例外 → `internal_error`。EngineError は、コードが表にあり、例外の型の区分（`illegal`・`unsupported`・`state_integrity`・`deck_validation`・`convention_set`）が表の `raised_as` にあるときだけその行の分類。どちらかが合わなければ `unmapped`（`DIAGNOSTIC_UNMAPPED`。元のコードは検証者用の記録だけ）。接頭辞・例外の型の名前からは推測しない
- 停止（`Phase.HALTED`）の `halt.code` も同じ表で引く（停止の文は「止めました」の文。不正な操作・状態の不整合のコードでの停止は対応漏れ）
- 決まった文: コードごとの文（33 個）か、分類・区分ごとの文。埋め込み（カード名・uid・枚数）はない
- 診断の識別（`diagnostic_id`）: 表で対応付けたコードはそのコード（一度出したコードの意味を変えない約束。仕様案 4.5 節）、アダプタが作るものは `DIAGNOSTIC_UNMAPPED`・`INTERNAL_ERROR`・`SUBMITTER_MISMATCH`・`INVALID_SEED`

状態の不整合と内部エラー:

- `StateIntegrityError` は `failed`・`state_integrity`（未対応・未裁定・内部エラーに変えない）。本人には一般的な文だけで、`problems` の文（カードの uid などを含みうる）は検証者用の記録
- EngineError でない `Exception` は `failed`・`internal_error`。元の例外・生の文・traceback は検証者用の記録（`VerifierReport.exception`・`raw_message`・`traceback`）。`MemoryError` と、`Exception` の子でない終了（`KeyboardInterrupt`・`SystemExit`・`GeneratorExit`・`CancelledError`）は捕まえない
- 捕まえる範囲はアダプタの境界の `apply_command`・`new_game` の呼び出しだけ（エンジンの中の例外の扱いは変えていない）

## 4. 見る人と検証者の情報境界

- 見る人の値は 0・1・None だけ（`True`・`2`・`"verifier"` などは `ValueError`）。検証者用の記録（`VerifierReport`）は `CommandResult.verifier` で、ホストだけが持つ。見る人の値を変えても取り出せない
- 閲覧用の型は、公開を許した項目だけを持つ: `ActorDiagnostic`（本人。結果・状態・処理段階・続けられるか・次の操作の種類・診断の識別・分類・区分・事例・決まった文・停止の公開の診断・操作の識別・規約集合）と `StatusNotice`（相手・観戦者。今の状態の公開の値だけで、だれが何を送ったか・拒否の有無を持たない）
- 閲覧用の結果に入らないもの: 生の例外文・traceback・problems・元のコード（対応漏れのとき）・コマンドの内容・未公開のカードの名前と uid・山札とサイドと置いておくカードの配分・seed・乱数の状態とその指紋・完全な状態の指紋
- 拒否は本人だけ（相手・観戦者には拒否があったことも知らせない）。`submitter` を使えば、名前を使われたプレイヤーにも知らせない
- 受け付けた結果の停止は、既存の公開の範囲（ログ `halted` のコード・観測の `interruption`）で全員に知らせる
- 内部エラーは、全員に「処理できなかった」状態（`unavailable`）だけを知らせる（中身は検証者だけ）
- 対戦が終わったあとも同じ範囲（`view_for` は段階で範囲を変えない）

返す値の秘密の確かめ: 決まった文は埋め込みがない。診断の識別・分類・事例はコードだけから決まる（事例はコード表の固定の値）。処理段階はコマンドの種類と公開の段階、`next` と `continuable` は公開の段階・番・決定と規約集合から決まる。v0.147〜v0.151 の代表の双子（5 章）で、本人・相手・観戦者の結果が同じことを確かめた。双子の比べで確かめたのは対象群だけで、ほかの拒否のコードが配分によらないことは確かめていない（7 章）。

## 5. 検証（限定）

`tests/test_diagnostics_adapter_v0_152.py`:

- 既存の API との一致: 8 つの場面（宣言の拒否・番でない操作の拒否・決定待ち・答えのあとの途中停止・延長戦の開始待ち・終局・延長戦の開始・延長戦の開始待ちでの拒否）で、受理・拒否と、返す状態・乱数・ログ・観測が `apply_command` と同じ。渡した状態が変わらない
- 結果の区別: 上の場面の outcome・status・continuable・next。停止は受理の結果で拒否の文ではない。組み合わせの矛盾は `ValueError`
- 分類: 実際の経路（研究上の停止・不正な操作・互換性の状態の確かめ・状態の不整合）と、例外を差し込む確かめ（未裁定・未対応・技術的制限・互換性・内部エラー・終了の例外・表にないコード・接頭辞の似た表にないコード・型の区分の合わないコード・表にない停止のコード）
- コード表: 作り直したものと同じで問題がない。台帳の有効な停止コードと `IllegalActionError` のコードがすべて表にある。動的な呼び出し箇所の表の行を消すと問題になる。表からコードを消すと対応漏れになる。文に埋め込みがない。2 つ以上の事例を持つコードは事例を選ばない
- 情報境界: 閲覧用の結果の項目が許した項目だけ（型の項目と辞書の鍵）、入ってはいけない名前を差し込むと見つける、拒否は本人だけ、終局のあとも広がらない、見る人の値の誤りは `ValueError`、送り手の違いはエンジンを呼ばずに拒否
- 双子: v0.151（8 つの RB2 の経路のうらのサイド・置いておくカード、はらだいこ、てじなの段階 1）、v0.150（18 の経路の山札をさがす決定まで）、v0.147（下限・ありうるカード）、v0.148（6 つの宣言）で、どの見る人の結果も同じ。双子の配分が実際に違うこと（配分を書けば違いが出ること）も確かめる
- ホストの境界・対戦の開始・文書と仕様の採用の記録

結果と、そのほかの確かめは 8 章に書きます。

## 6. 利用例（実際の出力。規約集合の照合値は省略）

```python
from kyuura_engine.adapter import HostedGame, submit

result = submit(state, EndTurn(0), submitter=0, operation_id="op-7")   # 正常な操作
result.view_for(0).to_dict()   # 本人
result.view_for(1).to_dict()   # 相手（今の状態の知らせ）
result.verifier                # 検証者用（ホストだけ）
```

正常な操作（番の終わり）:

```json
{"kyuura_diagnostic_schema": 1, "role": "actor", "viewer": 0, "outcome": "accepted", "status": "in_progress", "stage": "turn_action", "continuable": true, "next": [{"kind": "turn_action", "player": 1}], "diagnostic_id": null, "category": null, "subkind": null, "case_id": null, "case_status": null, "message": null, "halt": null, "operation_id": "op-7", "convention_set": {"id": "CS-KYUURA-CURRENT", "version": 1, "digest": "sha256:…"}}
{"kyuura_diagnostic_schema": 1, "role": "observer", "viewer": 1, "status": "in_progress", "continuable": true, "next": [{"kind": "turn_action", "player": 1}], "halt": null, "convention_set": {"id": "CS-KYUURA-CURRENT", "version": 1, "digest": "sha256:…"}}
```

拒否（番でないプレイヤー 1 の番の終わり。相手のプレイヤー 0 には `None`）:

```json
{"kyuura_diagnostic_schema": 1, "role": "actor", "viewer": 1, "outcome": "rejected", "status": "in_progress", "stage": "turn_action", "continuable": true, "next": [{"kind": "turn_action", "player": 0}], "diagnostic_id": "NOT_YOUR_TURN", "category": "invalid_input", "subkind": "command", "case_id": null, "case_status": "not_applicable", "message": "今はあなたの番ではありません。", "halt": null, "operation_id": "op-8", "convention_set": {"id": "CS-KYUURA-CURRENT", "version": 1, "digest": "sha256:…"}}
```

決定待ち（ドライアップの宣言のあと。相手には同じ status と次の操作の種類だけ）:

```json
{"kyuura_diagnostic_schema": 1, "role": "actor", "viewer": 0, "outcome": "accepted", "status": "awaiting_decision", "stage": "turn_action", "continuable": true, "next": [{"kind": "answer_decision", "player": 0}], "diagnostic_id": null, "category": null, "subkind": null, "case_id": null, "case_status": null, "message": null, "halt": null, "operation_id": "op-9", "convention_set": {"id": "CS-KYUURA-CURRENT", "version": 1, "digest": "sha256:…"}}
```

受理後の停止（ドライアップの「おもて」3 回・「水」1 枚の途中停止。観戦者にも同じ停止の診断）:

```json
{"kyuura_diagnostic_schema": 1, "role": "observer", "viewer": null, "status": "halted", "continuable": false, "next": [], "halt": {"diagnostic_id": "UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT", "category": "unresolved_ruling", "case_id": "UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT", "case_status": "identified", "message": "この場面の扱いは、基準のルールと記録からは決まらないため、エンジンは対戦を止めました。", "interrupted": true}, "convention_set": {"id": "CS-KYUURA-CURRENT", "version": 1, "digest": "sha256:…"}}
```

閲覧者向けと検証者向け（はらだいこの宣言の FC1。本人には決まった文、相手・観戦者には `None`、検証者用の記録には生の文）:

```json
{"kyuura_diagnostic_schema": 1, "role": "actor", "viewer": 0, "outcome": "rejected", "status": "in_progress", "stage": "turn_action", "continuable": true, "next": [{"kind": "turn_action", "player": 0}], "diagnostic_id": "UNRESOLVED_STATED_CARDS_SHORT", "category": "unresolved_ruling", "subkind": null, "case_id": null, "case_status": "not_identified", "message": "この場面の扱いは、基準のルールと記録からは決まらないため、エンジンはこの操作を受け付けません。", "halt": null, "operation_id": null, "convention_set": {"id": "CS-KYUURA-CURRENT", "version": 1, "digest": "sha256:…"}}
```

```text
result.verifier.engine_code    == "UNRESOLVED_STATED_CARDS_SHORT"
result.verifier.exception_type == "UnsupportedError"
result.verifier.raw_message    == "UNRESOLVED_STATED_CARDS_SHORT: 説明が決まった数（…）（FC1。山札の基本エネルギーカードが 2 枚より少ないかもしれない（…v0.151））"
```

`HostedGame` の例:

```python
game = HostedGame(state)
game.submit(EndTurn(1), submitter=1)            # 拒否: game.state は変わらない
r = game.submit(UseAttack(0, 0), submitter=0)   # 受理: game.state が進む
game.view(1)                                     # 相手の観測（observe）
```

## 7. 残る判断事項・未確認・引き継ぎ

- 保留の判断事項: D-IMPLEMENTATION-ID・D-RUNTIME・D-CHECK-DENSITY・D-SNAPSHOT-BASE・D-VERSIONS・D-HALT-SNAPSHOT（仕様案の JSON で `pending`）
- 未確認: 双子で確かめた対象群（v0.147〜v0.151）の外の拒否のコードが、秘密の配分によらないか。`next` の `turn_action` は番のプレイヤーだけを書き、番でないプレイヤーが送れる操作（あれば）を列挙しない
- 事例: 例外が事例を持たないので、2 つ以上の事例を持つ 9 コードは事例を返せない。返すにはエンジンの変更（例外に事例を持たせる）が要る（別の判断）
- 次の単位 U3（完全な再現用記録の収集と検証）への引き継ぎ: `CommandResult` の `operation_id`・`actor`・`outcome`・`verifier.command`・`verifier.engine_code` で、受理した操作と拒否した操作を分けて記録できる。拒否の記録は任意（D-REJECTED）で、再現の入力は受理した操作だけ。コード表の `schema_version` と診断の `kyuura_diagnostic_schema` は記録の見出しに書く候補

## 8. 検証の結果

限定検証だけを実行した（全体テスト・全 108 組・4,356 局・lockstep・ストレス実行はしていない）。終了コードは確かめの本体から。

- `tests.test_diagnostics_adapter_v0_152`: 37 テスト OK（双子は 3 つの集合 CS-KYUURA-CURRENT@1・CS-KYUURA-PLAY-S2A@1・CS-KYUURA-PLAY-PO@1 を含む）
- `tests.test_diagnostics_replay_api_design`: 20 テスト OK（採用の記録の確かめのため 2 つのテストの期待を変えた: 判断事項を採用の記録なしに adopted にすると見つける・技術的制限の例の項目の名前 `diagnostic_id`。目的は同じ）
- 版のテスト（`test_preset_decks_v0_20` の `test_version`）・規約集合の識別と照合値のテスト（`test_conventions_v0_142` の `IdentityTest`・`RecordsTest`）: OK（3 つの集合の ID・版・照合値は変えていない）
- 変えた文書（README・実装状況・データの来歴）を読む既存のテストのメソッド 16 件: OK
- 生成物の `--check`: `build_diagnostic_catalog`・`build_diagnostics_replay_api_design`・`build_stop_policy_classification`・`build_play_policy_family_plan`・`build_convention_records`・
  `check_implementation_assumptions`・`check_normalization_revalidation` のすべてが終了コード 0（停止の方針の台帳・同梱の規約集合の記録は変えていない）
- ruff 0.17.2（基点と同じ版・設定）: 新しい・変えたスクリプト・テスト・コードに新しい指摘なし。新しい抑制（`noqa`）はない。アダプタの境界の `except Exception` は、`MemoryError` を投げ直す判定を同じ節に置いた
  （BLE001 の対象外の形。捕まえる範囲は 3 章）。`test_preset_decks_v0_20.py` の指摘は基点と同じ
- `check_implementation_assumptions.py --sites`（基点の木と比べた差）: 増えた 2 件・消えた 1 件。この文書の 4 章の検証の文（「結果が同じ」）と、版のテストの行に版の注記を足して識別が変わった 1 件（前の行の候補が消えた）。
  どちらも実装上の仮定ではない。文面は変えていない
- 途中で直したこと: 停止の方針の台帳の走査（`scripts/stop_policy_scan.py`）は、エンジン・テストの中の停止コードの形の言葉と `RuntimeError` を数える。分類の定数の名前を `RULING_UNRESOLVED` にし
  （値は `unresolved_ruling`）、`HostedGame` の使い方の誤りは専用の例外 `HostStoppedError` にした（内部ガードではない）。テストの中に停止コードの文字列を書かない（台帳は変えていない）
- コード表の生成で、関数の中の変数（`code = "…"`）をモジュールの定数として読み、別のコードに対応付けていたのを、作る途中で見つけて直した（大文字のモジュール・クラス直下の定数だけを読む）
