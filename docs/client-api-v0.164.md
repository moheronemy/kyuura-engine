# v0.164: クライアント向けの最小のアダプタ（GUI の別リポジトリ向け）

`kyuura_engine.client_api` は、別のリポジトリで作る GUI が、エンジンの内部の型（`GameState`・決定・`CommandResult`・検証者用の記録）を知らずに使える、JSON にできる要求と応答の境界です。通信の方式に依存せず、同じプロセスで `handle(dict) -> dict` を呼びます。`kyuura_engine` の版は 0.164.0 です。

実行は U7（`legal_actions`）と U2（`adapter`）に任せ、別の実行器・独自の合法性の判定は作っていません。対応する操作は U7-1・U7-2 の範囲だけです（決定への回答・番を終える・初期配置・切り直しの補償・ジャンケンの結果・延長戦の開始）。**番の候補は部分実装**です（番を終えるだけ。ほかの 12 種類は `not_covered_kinds`）。**v0.165 の追記**: U7-3 で、番の基本の操作 4 種類（`play_basic`・`attach_energy`・`evolve`・`retreat`）を同じ要求の形で扱う（契約・形式の版は同じ。応答の形の追加と GUI の追従は [legal-actions-u7-3.md](legal-actions-u7-3.md) 5〜6 章）。番の候補は部分実装のまま（ほかの 8 種類が `not_covered_kinds`）。

## 1. U7-2 の契約の確かめ（この版で直したもの）

- **ホストの操作の拒否**: v0.163 の `HostSession.submit` は、送り手の結果に全員向けの知らせ（`CommandResult.view_for(None)`）を返していた。U2 の約束で拒否の全員向けの知らせは `None` なので、エンジンが拒否したホストの操作の理由をホストが受け取れなかった（全員へ配ってよいという意味の値を送り手の応答に使っていた）。v0.164 で、ホストへの応答を `legal_actions.HostNotice`（ホストだけへの定型の診断）にした。全員へ配る更新は、このアダプタが受理のあとにだけ作る（3 章）。回帰テスト `test_host_rejection_is_answered_only_to_the_host`
- **初期配置の `supported`**: `eligible` の選べるものだけで作った入力の範囲の保証で、表示した化石・人形（`eligible` が偽）まで実行できるという意味ではない。候補の `guarantees` に `supported_scope` を加えて明示した

## 2. 責任の分担

| 層 | 担うもの |
|---|---|
| エンジン（このリポジトリ） | 対戦の状態の管理・閲覧者ごとの観測・操作の候補と入力の制約・コマンドへの変換と実行・安全な結果と定型の診断・ホストの操作の境界・クライアント向けのデータの契約（この文書） |
| ホストするアプリケーション（GUI のサーバー・同じプロセスの親など） | 入口の作成と配布・**認証**・権限の確かめ・通信の方式・**永続化**・**再送の重複の排除**・公開の更新の配信・検証者用の結果の保管 |
| GUI（別リポジトリ） | 描画・入力・画面の遷移・定型の診断と処理可能性の表示・エンジンの応答を使った操作・通信を使う場合のクライアントの処理 |

GUI は `GameState`・内部の決定・`CommandResult`・完全な再現用記録・スナップショット・検証者用の診断を扱いません（この契約の応答に入らない）。

## 3. 入口と権限

```python
from kyuura_engine.client_api import ClientHub

hub, start = ClientHub.start(deck0, deck1, seed, verifier=keep_for_verifier)   # 信頼されたホストの側
alice = hub.player(0)        # 本人 0 だけに渡す
bob = hub.player(1)          # 本人 1 だけに渡す
viewer = hub.spectator()     # 観戦者（観測と公開の更新だけ）
admin = hub.host()           # ホストの操作（信頼されたアプリケーションだけが持つ。GUI の通常の要求に混ぜない）
```

- 要求に操作主体・閲覧者を書く項目はない（`actor`・`viewer` を書けば `CLIENT_FIELD_UNKNOWN`）。主体は入口を作ったときに決まり、要求では変えられない
- プレイヤーの入口: 本人の観測・候補・入力・検査・送信と、本人への公開の更新
- 観戦者の入口: 観戦者の観測と公開の更新だけ（候補・送信の要求は `CLIENT_REQUEST_UNKNOWN`）
- ホストの入口（`HostEndpoint`）: ジャンケンの結果・延長戦の開始の候補と送信、観戦者と同じ範囲の観測
- 入口の所有と適切な配布、認証は、ホストするアプリケーションの責任（ライブラリは認証をしない）。Python の型だけでは、入口の閉包の中の参照まで隠せない（信頼できないコードと同じプロセスで動かさない）
- `verifier(actor, CommandResult)` はホスト・検証者だけが受け取る（内部エラーの詳細・検証者用の値を含む）

## 4. 要求と応答（契約の識別 `kyuura-client-api`・形式の版 1）

契約の識別と形式の版は、ゲームの版（`kyuura_engine.__version__`）・規約集合・記録の形式（`kyuura_replay_format` など）とは別の番号です。

要求（どれも JSON のオブジェクト）:

| 種類 | 入口 | 項目 |
|---|---|---|
| `view` | すべて | なし |
| `updates` | すべて | なし（その入口の閲覧者への公開の更新を取り出す） |
| `candidates` | プレイヤー・ホスト | なし |
| `inputs` | プレイヤー・ホスト | `game`・`revision`・`candidate`（文字列） |
| `check` | プレイヤー・ホスト | 上と `choices`（文字列・整数の配列。任意） |
| `submit` | プレイヤー・ホスト | 上と `choices`・`operation_id`（文字列。任意） |

誤りの扱い（例外を投げず、決まった文の `error` を返す。要求の値を文に入れない。状態・取っ手・更新を変えない）:

| 場合 | コード |
|---|---|
| オブジェクトでない | `CLIENT_REQUEST_INVALID` |
| `contract` が違う | `CLIENT_CONTRACT_UNKNOWN` |
| `format` が 1 でない（文字列・真偽を含む） | `CLIENT_FORMAT_UNSUPPORTED` |
| その入口が受け付けない種類 | `CLIENT_REQUEST_UNKNOWN` |
| 知らない項目 | `CLIENT_FIELD_UNKNOWN` |
| 項目の型・長さ（128 文字まで）・`choices` の中身（文字列・整数だけ、64 個まで）が正しくない | `CLIENT_FIELD_INVALID` |
| 処理できない結果のあと | `CLIENT_GAME_UNAVAILABLE` |

例:

```json
{"contract": "kyuura-client-api", "format": 1, "type": "candidates"}
```

```json
{"contract": "kyuura-client-api", "format": 1, "type": "candidates", "ok": true,
 "response": {"kyuura_legal_actions_format": 1, "game": "…", "actor": 0, "revision": "…", "status": "in_progress",
              "situation": "actor_to_act", "empty_reason": null,
              "coverage": {"implemented_kinds": ["take_prize", "…"], "scope_kinds": ["place_starting"], "offered_kinds": ["place_starting"],
                           "not_covered_kinds": [], "withheld_input_candidates": [], "completeness": "complete",
                           "completeness_scope": "scope_kinds（この応答に明示した種類だけ。全コマンドの合法手ではない）"},
              "candidates": [{"id": "c1", "kind": "place_starting", "processability": "supported", "input_disclosure": "confirmed",
                              "input_stages": [{"stage": 1, "input": "choose_option"}, {"stage": 2, "input": "choose_option"}], "…": "…"}]}}
```

```json
{"contract": "kyuura-client-api", "format": 1, "type": "submit", "game": "…", "revision": "…", "candidate": "c1", "choices": ["o1", "o2"], "operation_id": "gui-17"}
```

```json
{"contract": "kyuura-client-api", "format": 1, "type": "submit", "ok": true, "outcome": "accepted", "refusal": null,
 "result": {"kyuura_diagnostic_schema": 1, "role": "actor", "viewer": 0, "outcome": "accepted", "status": "in_progress", "…": "…", "operation_id": "gui-17"},
 "refetch_required": true}
```

- `submit` の `outcome` は `accepted`・`rejected`・`failed`（エンジンの結果）か `refused`（U7 のホストの段の拒否。エンジンに渡していない）。`result` はプレイヤーなら U1 の本人への診断、ホストなら `HostNotice`（どちらも定型の診断だけ。生の例外文・状態・seed・確認値を持たない）
- `refetch_required`: 候補を取り直す必要があるか（受理・古い取っ手・別の対戦・別の主体・知らない候補）
- `view` の応答: `status`（`status`・`phase`・`segment`・`continuable`・`waiting`（だれの入力・ホストの操作を待つか。`by` は 0・1・`players`・`host`）・`halt`（停止の公開の診断）・`convention_set`）と、その閲覧者の観測（`observation`。U5 と同じ `observe`）
- 処理可能性（`processability`）・入力を示して安全か（`input_disclosure`）・完全性（`completeness`）は U7 の値をそのまま渡す（`complete` は明示した種類の範囲だけ、`unverified` は受理の保証ではない、未裁定・未対応はゲーム上の禁止とは別、情報境界が未確認の入力は示さない）。表示の方法（D-U7-DISPLAY）はこの文書では採用していない（意味と機械が扱う区分を渡すだけ）

## 5. 応答と公開の更新

- 応答は要求した入口だけへ返す。拒否（エンジンの拒否・ホストの段の拒否・要求の誤り）は送り手への応答だけで、公開の更新を作らない（拒否の有無・中身・欠番・数を他の閲覧者に伝えない）
- 受理のあと、閲覧者（0・1・観戦者・ホスト）ごとに 1 つの更新を作る: `{"type": "update", "number": n, "status": …, "observation": …}`。`number` は受理でだけ進む公開の更新の番号（秘密の値のハッシュ・エンジンの乱数を使わない。拒否では進めない）
- 処理できない結果（内部エラー）: 更新は `status` が `unavailable` で `observation` が null のものだけ。詳細は `verifier` へ
- 更新は `hub.take_updates(audience)` か、入口の `updates` 要求で取り出す（同じ閲覧者の入口が複数あれば同じ箱を共有する。配信の分配はホストの責任）
- `operation_id` は今は送り手の結果に写して対応づけるだけで、更新には入らない。**重複の排除や「必ず一度だけ実行」の保証はない**（未実装の別の契約。担うのはホストするアプリケーション）
- 状態との対応は U7 の取っ手（`game`・`revision`）。受理・差し替え・復元で失効する

## 6. 再接続と履歴（契約だけ。機能は作っていない）

- 画面の復帰は、その閲覧者に許された今の観測（`view`）で行う。古い候補の取っ手は取り直す（`candidates`）
- 履歴の表示には閲覧用記録（U5。`view_record`）を使う（このアダプタの応答には入れていない）。接続より前の各時点の秘密の情報を、今の状態からさかのぼって作り直さない
- スナップショット・完全な再現用記録は GUI へ送らない（ホスト・検証者の側だけ）

## 7. 接続の確かめ（ヘッドレスの参照クライアント）

`examples/headless_client.py` は、入口の `handle` に JSON を渡して JSON を受け取るだけで対戦を進める参照クライアントです（`GameState`・実際の山札・相手の手札・完全な記録・スナップショット・検証者用の診断を読まない）。今の範囲（番の中は番を終えるだけ）では勝つための方策は作れず、番を終え続けると山札がなくなって終局します。内部の状態を読んで完走させる回避はしていません。

確かめた流れ（`tests/test_client_api.py`）: 対戦の開始 → 両方の初期配置 → 補償の選択 → ホストのジャンケンの結果 → 番の候補と番を終える → 終局の表示用の値、決定への回答（構築盤面。トレーナーを使うのは U7 の外の直接の送信）、古い取っ手の拒否と取り直し、停止の表示用の値、延長戦の開始（構築盤面）。

## 8. 導入（別リポジトリの GUI から）

- 依存の方法（推奨）: このリポジトリの固定したコミットを Python のパッケージとして入れる（`pyproject.toml` の `kyuura-engine`。依存のパッケージはない。Python 3.11 以上）。例: `pip install "kyuura-engine @ git+https://github.com/moheronemy/kyuura-engine@<commit>"`。**訂正**: v0.164 の最終コミット `d0c5cfa` までは配布物に `kyuura_engine.resolution` が入らず、この通常のインストールでは `import kyuura_engine` が失敗した。`e8c518f` 以降のコミットを固定する（[installation.md](installation.md)）。編集可能インストール（`pip install -e <path>`）はエンジンの開発用で、GUI の必須の手段ではない。パッケージの公開（PyPI など）はしていない
- 同じプロセスで使う: ホストの側で `ClientHub` を作り、入口を GUI の部品へ配る。要求・応答は JSON のオブジェクト（`dict`）
- 別のプロセス・通信で使う: 要求・応答をそのまま JSON の文字列にして通す（通信の方式・認証・再送はホストするアプリケーションが作る）
- 契約の識別と形式の版（`kyuura-client-api`・1）を GUI の側でも確かめる。形式の版が変わったら、知らない版として扱う

## 9. 制限と引き継ぎ

- 対応する操作は U7-1・U7-2 の範囲だけ（番の通常の操作 12 種類は U7-3〜U7-5）。v0.165 で U7-3 の 4 種類を加えた（ワザ・トレーナー・特殊能力など 8 種類は U7-4・U7-5）
- 認証・通信・永続化・再送の重複の排除・再接続の機能・履歴の配信は作っていない
- 公開の更新は、この hub の入口から送って受理された操作だけから作る（ホストが包んだ対戦へ直接送った操作では作らない。直接送るのは契約の外）
- 識別の方式の移行はしていない（新しいファイル `kyuura_engine/client_api.py` は識別の設計の部品 `client_api`（層 `api_format`）。現行の方式では `behavior_digest` に入る）
