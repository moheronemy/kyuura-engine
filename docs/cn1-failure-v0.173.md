# v0.173: ClientHub・ActionHost が包む対戦の failure の接続（CN-1）

検証用 AI の V0 で見つけた CN-1（[verification-ai-v0.md](verification-ai-v0.md) 5.1 節・[verification-ai-v1.md](verification-ai-v1.md) 5 章）を、エンジンの側で正式に直しました。
版は 0.173.0 です。GUI・renderer・kyuura・カードデータ・固定デッキ・規約集合・裁定・識別の方式は変えていません。

## 1. 問題（v0.172.0）

- `legal_actions.ActionHost`（`client_api.ClientHub` の中）は、包んだ対戦の `state`・`submit`・`failure` を読む。`failure` は候補の取得・入力・check・submit・view のたびに
  `ActionHost._state` が読み、処理できない結果（failed）のあとは `HostStoppedError`（入口は `CLIENT_GAME_UNAVAILABLE`）にする
- `adapter.HostedGame` と `snapshot.RestoredGame` は `failure` を持つが、`replay_record.ReplayCollector` と `view_record.ViewHost` は持たなかった。そのため
  `ClientHub(ReplayCollector…)`・`ClientHub(ViewHost…)` は、最初の候補の取得で `AttributeError` が入口の外へ出た（入口の「例外を投げない」の前提が崩れる）。`ActionHost` の
  説明は `ViewHost` を包めると書いていた
- 再現: `tests/test_verification_ai_v0.py` の `CN1Test.test_view_host_and_collector_lack_failure`（修正の前のコードで実行し、`AttributeError` を確かめた。証跡の
  `cn1_before_fix_test_output.txt`）。検証用 AI は、独自の失敗の状態を持つ包み（`RecordingGame`）で避けていた

## 2. 修正

| 型 | 追加 | 意味 |
|---|---|---|
| `replay_record.ReplayCollector` | `failure` プロパティ | 包んだ `HostedGame` の `failure` をそのまま返す。失敗がなければ None、failed を受け取ったあとはその `CommandResult` |
| `view_record.ViewHost` | `failure` プロパティ | 包んだ対戦（`ReplayCollector`（`full_record` 真）か `HostedGame`（偽））の `failure` をそのまま返す |

- 失敗の状態の持ち主は、いちばん内側の `HostedGame` の 1 つだけ（包みごとに別の失敗の状態を持たない。いつも None を返して隠すことはしない。属性がないことを正常として扱う
  `getattr` の代わりではない）
- 失敗のあとの扱いは変えていない: `ActionHost` は失敗のあとの要求を断る（`CLIENT_GAME_UNAVAILABLE`）、`ReplayCollector` は記録を aborted で止め、そのあとの直接の送信は
  `CollectorStoppedError`、`HostedGame` は `HostStoppedError`。相手・観戦者への公開の更新は、処理できなかったことだけ（状態 `unavailable`・観測なし）で、検証者用の値は
  渡さない（`ClientHub._on_result` のまま）
- 戻り値の型は `HostedGame.failure` と同じ `CommandResult | None`。検証者用の値を含む結果で、ホストの中だけで使う（見る人に渡さない）
- `legal_actions.py`・`client_api.py` は変えていない（`ActionHost` の説明の「`ViewHost` を包める」は、この修正で正しくなった）

## 3. 対応する接続

`ClientHub(game)`・`ActionHost(game)` の `game` として対応するもの（`state`・`submit`・`failure` を持つ）:

| 包む対戦 | 作り方 | 完全な再現用記録 | 閲覧用記録 |
|---|---|---|---|
| `adapter.HostedGame` | `start_game` の状態・`ClientHub.start`・`ClientHub.from_state` | なし | なし |
| `replay_record.ReplayCollector` | `ReplayCollector.start`（new_game からだけ） | あり | なし |
| `view_record.ViewHost` | `ViewHost.start`（`full_record` 真・偽） | 真なら内側の `ReplayCollector` | あり |
| `snapshot.RestoredGame` | `RestoredGame(restore_snapshot(…))` | なし（`full_record` はいつも None） | 復元の時点から（`viewers`） |

- これらのほかの任意の包み・包みの入れ子は対象の外（`ActionHost` の所有権の契約: 包んだ対戦へ別の経路で操作を送らない）。検証用 AI の `RecordingGame` は `ReplayCollector` を包み、
  `failure` に収集器の値を返す（4 章）
- `ClientHub` の入口の「例外を投げない」は、上の対応する包みを使ったときの約束

## 4. 検証用 AI の側

`tools/verification_ai/records.py` の `RecordingGame` は、独自の失敗の状態（`_failure`）をやめ、`failure` に `ReplayCollector.failure` を返すようにしました。ほかの責任
（開始の決まった設定・拒否で状態が変わらないことの照合の確認値 `last_check`・記録の取り出しと閉じ方・失敗のあとの送信を `HostStoppedError` で断ること）は残しています。
方策・乱数の使い方・意味の列・check と submit の共通の経路は変えていません（`tests/test_verification_ai_v2_repeat.py` の意味の列の sha256 のテスト）。

## 5. テスト

`tests/test_client_api_cn1_v0_173.py`（4 テスト）: 対応する 5 つの包み（`HostedGame`・`ReplayCollector`・`ViewHost` の完全な記録あり・なし・`RestoredGame`）の通常の候補の取得・
check・submit と `failure` が None、テストの中で `adapter.apply_command` を例外にして failed を注入したときの `failure`（内側の `HostedGame` の値と同じオブジェクト）、失敗のあとの
プレイヤー・ホスト・観戦者の要求の断り、完全な記録の aborted と、同じ失敗の条件の再実行の recorded_failure、相手・観戦者への公開の更新と閲覧用記録に失敗の文・例外の型・
traceback が出ないこと。

意図した差: `tests/test_verification_ai_v0.py` の CN-1 の再現のテストを、修正のあとの期待（`failure` を持ち、`ClientHub` で候補を取れる）に直しました。

実行（1 モジュールずつ、別のプロセス）: `test_client_api_cn1_v0_173`（4）・`test_client_api`（9）・`test_replay_record_v0_153`（25）・`test_view_record_v0_155`（24）・
`test_replay_run_v0_154`（23）・`test_distribution`（12）・検証用 AI の 7 つ（V0 24・V1 19・V2 19・V2 の補完 15・V3-1 15・V3-2 11・V3-3 9）: 失敗 0。`test_preset_decks_v0_20`
（15）は 1 つ（`test_example_script_reaches_the_first_turn`）が、子のプロセスの出力の読み取りで `UnicodeDecodeError`（cp932）になった。この実行の環境の `PYTHONIOENCODING=utf-8`
で子は UTF-8 で書き、親はロケールの cp932 で読むため（コードの変更とは関係がない）。そのモジュールだけを `PYTHONIOENCODING` を外したプロセスで再実行して 15 テスト・失敗 0。

## 6. 版・識別・配布

| 項目 | 内容 |
|---|---|
| 版 | 0.172.0 → 0.173.0（`kyuura_engine/__init__.py`・`pyproject.toml`・`tests/test_preset_decks_v0_20.py`。既存の運用どおり、エンジンの実行時のファイルを変えたので版を上げた） |
| 識別の方式 | 変えていない（`kyuura-package-files-sha256/1`） |
| 実装の識別 | `view_record.py` は挙動の側のファイルなので `behavior_digest` が変わった（`822c10c1…f397`。0.172.0 は `07a189c9…6c18`）。`replay_record.py` は記録と診断の部品の側（`instrumentation_digest` `e7d36df3…3034`） |
| 記録・スナップショットとの互換 | 完全な再現用記録の再実行（`replay_run`）は、記録の版・`behavior_digest` が実装と違えば扱えない（`engine_version_differs`・`implementation_differs`）という既存の設計のまま。0.172.0 で作った記録（検証用 AI の V0〜V3-3 の証跡を含む）は、0.173.0 では `unsupported` になり、0.172.0 の実装（`e26df79` と同じパッケージ）で再実行する。スナップショットの復元も同じく、版・`behavior_digest` が違えば扱えない（`snapshot.py` の `implementation_differs`・`engine_version_differs`）ので、V3-3 の開始のスナップショット（0.172.0）は 0.173.0 では復元できず、0.172.0 の実装で使う。既存の証跡は元の版のまま保持し、書きかえない。状態の書き出しの形式・スナップショットの形式・確認値の方式は変えていない |
| 配布のファイル | パッケージのファイルの一覧は `e26df79` と同じ 62。新しい依存はない。`pip wheel` で作った wheel を `scripts/check_distribution.py --wheel` で照らした: `required=62 problems=0` |
| 通常のインストール | リポジトリの外の新しい仮想環境に、`git+https://github.com/moheronemy/kyuura-engine.git@ca36ba83e30b2bc8efb51180d9387578615f5a9b` を通常のインストールで入れ、接続のスモーク（`ReplayCollector`・`ViewHost` を `ClientHub` で包み、候補の取得・注入した failed のあとの `CLIENT_GAME_UNAVAILABLE`・aborted）を 1 回実行した: 成功。`direct_url.json` の `commit_id` は `ca36ba83…5a9b`、読み込みは `site-packages` から、実装の識別はソースの木と同じ |

証跡: `C:/dev/kyuura-engine-verification-vai/verifier/runs/cn1-v0.173/`（修正の前の再現の出力・テストの実行の記録・スモークのスクリプトと出力・配布の照らし・パッケージのファイルの一覧・
V3-3 の C1 の保存した証跡の確かめ）、`public/runs/cn1-v0.173/summary.json`。
