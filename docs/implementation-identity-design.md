# 実装の識別と互換性の判定の新しい方式（設計案）

v0.159（U1〜U6 の総合検証）のあとの設計案です。**設計と移行の計画だけ**で、現行の識別（`replay_record.implementation_identity`）・対応の判定（`support_problems`・`snapshot._check_support`）・記録の形式は変えていません。エンジンの版は 0.159.0 のままです。

表と構造化した仕様（[implementation-identity-design.json](implementation-identity-design.json)）は `scripts/build_implementation_identity_design.py` の `SPEC` から作ります（`--write` で書き直し、`--check` で確かめる。表を手で二重に書かない）。表の書き出しは状態スナップショットの仕様案の生成器の関数をそのまま使っています。生成区画の外の本文は手で書きます。

## 採用の記録

<!-- generated:adoption begin -->
- `ADOPT-IDENTITY-PRINCIPLES`（2026-11-07・利用者）: 実装の識別を、ゲームの挙動・記録と検証の機能・API の形式の 3 つの責任に分けることを、新しい識別の方式として設計すること（既存の方式の意味を変えない。分けたことだけを理由に過去の記録を互換として扱わない）。新しい方式の細部・移行・判定の変更は採用していない
- 設計案の状態: `proposed`・承認 `not_approved`
<!-- generated:adoption end -->

採用したのは原則（3 つの責任に分けることを新しい方式として設計する・既存の方式の意味を変えない・分けたことだけを理由に過去の記録を互換にしない）だけです。この文書の方式の細部・機能ごとの判定・移行の段・判断事項は**推奨案**で、採用していません。

## 1. 現行の方式と制限

<!-- generated:current begin -->
- 方式: `kyuura-package-files-sha256/1`
- 定義: パッケージの .py（__pycache__ を除く）と data/*.json を、改行を LF・BOM を除いた中身の sha256 で連ねた sha256。INSTRUMENTATION_FILES の 4 つが instrumentation_digest、残りがすべて behavior_digest
- INSTRUMENTATION_FILES: `adapter.py`・`diagnostics.py`・`replay_record.py`・`data/diagnostic_catalog.json`
- 制限:
  - あとで加えた記録・検証のモジュール（replay_run.py・view_record.py・snapshot.py・snapshot_replay.py）は INSTRUMENTATION_FILES にないので behavior_digest に入る。これらを直すと、ゲームの処理が同じでも、それまでの記録・スナップショットは unsupported になる（v0.159 の総合検証 2.1 節 A）
  - __init__.py（__version__）が behavior_digest に入るので、版を上げるだけで behavior_digest が変わる
  - U4・S5（replay_record.support_problems）は behavior_digest と版だけを比べ、instrumentation_digest を比べない。スナップショット（snapshot._check_support）は instrumentation_digest も比べる（DS-INSTRUMENTATION）。今は版の一致の条件がこの差を覆っている
  - 部品ごとの識別がないので、ある機能が使わない部品の違いでも、その機能を拒む
<!-- generated:current end -->

（コードを読んだ判断。v0.159 の総合検証の 2.1 節 A と同じ。）

## 2. 責任の層と部品

実装の識別を 3 つの責任（層）に分け、各層の中を、機能ごとに一致を求める単位（部品）に分けます。識別のハッシュは部品ごとに求めます。

<!-- generated:layers begin -->
| 層 | 責任 |
|---|---|
| `game_behavior` | ゲームの挙動（状態の遷移・効果・規則・カードデータ・エンジンが読む観測と書き出し） |
| `record_verification` | 記録・検証の機能（診断・収集・再実行・閲覧用記録・スナップショット） |
| `api_format` | API の形式（パッケージの公開の入口と、各データ形式・方式の識別子） |
<!-- generated:layers end -->

<!-- generated:components begin -->
| 部品 | 層 | ファイルの数 | 役割 | 注 |
|---|---|---|---|---|
| `game_behavior` | game_behavior | 51 | 対戦の状態の遷移・受理と拒否・乱数の使い方・ログ・観測（engine.py・effects.py が observation.py を読み込み、observation.py が serialize.py を読み込むので、観測と状態の書き出しもここに入る）・カードデータ・固定デッキ・規約集合の登録の記録 | data/card_sources.json・data/research_links.json は実行時にエンジンが読まない来歴のデータ（スクリプト・テストだけが読む）。分けるかは D-PROVENANCE。初版は保守的にゲームの挙動に入れる |
| `diagnostics` | record_verification | 2 | 診断の型・コード表による分類・情報境界・状態の区分（status_of・next_actions） | 記録の各行の分類（status・diagnostic）を決める |
| `adapter` | record_verification | 1 | コマンドの実行結果（accepted・rejected・failed）と本人・相手・観戦者の知らせ | 記録の各行の outcome を決める |
| `replay_record` | record_verification | 1 | 完全な再現用記録の収集・形式・構造の検証・確認値（state_check・checks・接続用確認値の呼び出し）・現行の識別の計算 | 記録を書く側と読む側の両方 |
| `replay_run` | record_verification | 1 | 完全な記録の再実行と照合（U4） | 読む側だけ（記録の値を作らない） |
| `view_record` | record_verification | 1 | 閲覧用記録の作成・構造の検証（U5） | 閲覧用記録を書く側と読む側 |
| `snapshot` | record_verification | 1 | 状態スナップショットの保存・復元の符号化（コーデック）・接続用確認値（U6） | 符号化の対応表は SNAPSHOT_FORMAT の中身で、名前のついた方式を持たない（初版は部品の識別の一致で守る） |
| `snapshot_replay` | record_verification | 1 | 完全な記録とスナップショットの接続（U6-S5） | 読む側だけ |
| `public_facade` | api_format | 1 | パッケージの公開の名前（import と __all__）と、エンジンの版の文字列（__version__） | 処理を持たない（--check が import・代入・説明の文だけであることを確かめる）。版の文字列はここにあるので、今は版を上げるたびに behavior_digest が変わる（4 章） |
| `legal_actions` | api_format | 1 | 合法手 API（U7。docs/legal-actions-api-design.md）の操作候補・必要な入力の作成と、候補からの送信（U7-1 は決定への回答と番を終える。docs/legal-actions-u7-1.md） | v0.160 で加えた。U2 の HostedGame・CommandResult と observe を使う（別の実行器を持たない）。現行の方式では behavior_digest に入る |
<!-- generated:components end -->

### 2.1 ファイルの分類

パッケージの識別に入るすべてのファイル（`replay_record.package_files()`。`.py` と `data/*.json`）を、ちょうど 1 つの部品に分けます。`--check` は、この表とパッケージのファイルを名前で照らし、加わった・消えた・2 つの部品にあるファイルを見つけます（新しいファイルは、分類を書くまで `--check` が失敗する）。

<!-- generated:files begin -->
| ファイル | 部品 | 層 |
|---|---|---|
| `__init__.py` | public_facade | api_format |
| `adapter.py` | adapter | record_verification |
| `cards.py` | game_behavior | game_behavior |
| `checks.py` | game_behavior | game_behavior |
| `coins.py` | game_behavior | game_behavior |
| `commands.py` | game_behavior | game_behavior |
| `conditions.py` | game_behavior | game_behavior |
| `continuous.py` | game_behavior | game_behavior |
| `conventions.py` | game_behavior | game_behavior |
| `damage.py` | game_behavior | game_behavior |
| `data/card_sources.json` | game_behavior | game_behavior |
| `data/card_verification.json` | game_behavior | game_behavior |
| `data/convention_records.json` | game_behavior | game_behavior |
| `data/diagnostic_catalog.json` | diagnostics | record_verification |
| `data/kyuura_cards.json` | game_behavior | game_behavior |
| `data/research_links.json` | game_behavior | game_behavior |
| `data/species_heights.json` | game_behavior | game_behavior |
| `decisions.py` | game_behavior | game_behavior |
| `deck.py` | game_behavior | game_behavior |
| `decks.py` | game_behavior | game_behavior |
| `diagnostics.py` | diagnostics | record_verification |
| `effects.py` | game_behavior | game_behavior |
| `engine.py` | game_behavior | game_behavior |
| `errors.py` | game_behavior | game_behavior |
| `evolution.py` | game_behavior | game_behavior |
| `faceup.py` | game_behavior | game_behavior |
| `heights.py` | game_behavior | game_behavior |
| `history.py` | game_behavior | game_behavior |
| `interruption.py` | game_behavior | game_behavior |
| `judge.py` | game_behavior | game_behavior |
| `legal_actions.py` | legal_actions | api_format |
| `markers.py` | game_behavior | game_behavior |
| `movement.py` | game_behavior | game_behavior |
| `observation.py` | game_behavior | game_behavior |
| `persistent.py` | game_behavior | game_behavior |
| `procedures.py` | game_behavior | game_behavior |
| `reactions.py` | game_behavior | game_behavior |
| `replay_record.py` | replay_record | record_verification |
| `replay_run.py` | replay_run | record_verification |
| `resolution/__init__.py` | game_behavior | game_behavior |
| `resolution/catalog.py` | game_behavior | game_behavior |
| `resolution/codec.py` | game_behavior | game_behavior |
| `resolution/contract.py` | game_behavior | game_behavior |
| `resolution/events.py` | game_behavior | game_behavior |
| `resolution/flow.py` | game_behavior | game_behavior |
| `resolution/kernel.py` | game_behavior | game_behavior |
| `resolution/preflight.py` | game_behavior | game_behavior |
| `resolution/programs.py` | game_behavior | game_behavior |
| `resolution/questions.py` | game_behavior | game_behavior |
| `resolution/unbounded.py` | game_behavior | game_behavior |
| `resolution/v013_checks.py` | game_behavior | game_behavior |
| `rng.py` | game_behavior | game_behavior |
| `rules.py` | game_behavior | game_behavior |
| `serialize.py` | game_behavior | game_behavior |
| `snapshot.py` | snapshot | record_verification |
| `snapshot_replay.py` | snapshot_replay | record_verification |
| `stadiums.py` | game_behavior | game_behavior |
| `state.py` | game_behavior | game_behavior |
| `sudden_death.py` | game_behavior | game_behavior |
| `view_record.py` | view_record | record_verification |
| `zones.py` | game_behavior | game_behavior |
<!-- generated:files end -->

分け方の根拠（コードを読んだ判断）:

- `observation.py`・`serialize.py` は、公開の形（観測・状態の書き出し・コマンドの辞書）を持ちますが、`engine.py`・`effects.py` が `observation.py` を読み込み、`observation.py` が `serialize.py` を読み込むので、ゲームの挙動に入れます。API の形式の層は、ファイルの中身ではなく、形式・方式の識別子（3 章）で表します
- `commands.py` もゲームの挙動です（エンジンが受け付けるコマンドの定義。辞書の形 `command_to_dict` も同じファイル）
- `data/card_sources.json`・`data/research_links.json` は、実行時にエンジンが読みません（スクリプトとテストだけ）。初版は保守的にゲームの挙動に入れます（D-PROVENANCE）
- `__init__.py` は公開の名前と版の文字列だけで、処理を持ちません（`--check` が確かめる）

### 2.2 依存の向き

ゲームの挙動のファイルは、ほかの層のファイルを読み込みません（読み込むなら、その処理は挙動に影響しうるので、そのファイルはゲームの挙動に入れる）。`--check` が AST の import で確かめます。今の例外は 1 つです:

<!-- generated:dependency begin -->
| ファイル | 読み込む | 理由 | 解消 |
|---|---|---|---|
| `serialize.py` | `__init__.py` | state_to_dict が engine_version（__version__）を書き出す（確認値からは除く）。版の文字列を読むだけ | M2（版の文字列を版だけのファイルへ移す） |
<!-- generated:dependency end -->

## 3. 識別子と使う場所

<!-- generated:identifiers begin -->
| 識別子 | 種類 | コード | 値 | 意味 | 使う場所 |
|---|---|---|---|---|---|
| `engine_version` | release | `kyuura_engine.__version__` |  | エンジンの版（リリースの名前） | replay_record.support_problems（engine_version_differs）<br>snapshot._check_support（同）<br>view_record の見出し（engine_version。読む側は比べない）<br>serialize.state_to_dict の engine_version（確認値から除く） |
| `identity_method` | identity | `kyuura_engine.replay_record.IDENTITY_METHOD` | `kyuura-package-files-sha256/1` | 現行の実装の識別の方式 | replay_record.support_problems<br>snapshot._check_support |
| `behavior_digest` | identity |  |  | 現行の方式のゲームの挙動の側の識別（4 つの部品以外のすべて） | replay_record.support_problems（implementation_differs）<br>snapshot._check_support（同） |
| `instrumentation_digest` | identity |  |  | 現行の方式の記録と診断の部品 4 つの識別 | snapshot._check_support（instrumentation_differs）。U4・S5 は比べない |
| `replay_format` | format | `kyuura_engine.replay_record.REPLAY_FORMAT` | `1` | 完全な再現用記録の形式（kyuura_replay_format） | replay_record._structure（SUPPORTED_REPLAY_FORMATS） |
| `view_format` | format | `kyuura_engine.view_record.VIEW_FORMAT` | `1` | 閲覧用記録の形式（kyuura_view_format） | view_record.validate_view_record |
| `snapshot_format` | format | `kyuura_engine.snapshot.SNAPSHOT_FORMAT` | `1` | 状態スナップショットの形式（kyuura_snapshot_format） | snapshot の復元の段 2 |
| `state_export_format` | format | `kyuura_engine.replay_record.STATE_EXPORT_FORMAT` | `35` | 確認値に使う状態の書き出しの形式 | replay_record.support_problems（state_export_format_unsupported）<br>snapshot._formats |
| `state_check_method` | method | `kyuura_engine.replay_record.STATE_CHECK_METHOD` | `state-export-35-sha256/1` | 状態の確認値の方式 | replay_record.support_problems（check_method_unknown）<br>snapshot._formats |
| `rng_check_method` | method | `kyuura_engine.replay_record.RNG_CHECK_METHOD` | `python-random-getstate-sha256/1` | 乱数の確認値の方式 | 同上 |
| `connection_check_method` | method | `kyuura_engine.replay_record.CONNECTION_CHECK_METHOD` | `kyuura-snapshot-state-sha256/1` | 接続用確認値の方式（任意の拡張） | replay_record._check_extensions<br>snapshot_replay（from_connection） |
| `record_identity_method` | method | `kyuura_engine.snapshot_replay.RECORD_IDENTITY_METHOD` | `kyuura-replay-header-sha256/1` | 記録の見分け（見出しの sha256。認証ではない） | snapshot_replay.RecordPosition.record |
| `diagnostic_schema` | format | `kyuura_engine.diagnostics.DIAGNOSTIC_SCHEMA` | `1` | 診断の形式 | replay_record.support_problems（diagnostic_schema_unsupported）<br>snapshot._formats<br>view_record の見出し |
| `rng_format` | format | `kyuura_engine.rng.RNG_FORMAT` | `python-random-mt19937-v3` | 乱数の方式 | replay_record.runtime_identity（rng_scheme_differs）<br>snapshot._formats |
| `runtime` | environment |  |  | Python の実装と版（major・minor）と乱数の方式 | replay_record.support_problems（runtime_differs）<br>snapshot._check_support（同） |
| `dependencies` | dependency |  |  | ルールの組・カードデータ（リポジトリ・コミット・パス）・効果の登録表 | replay_record.support_problems（rules_unknown・card_data_differs・effects_differs）<br>snapshot._check_support（同と card_pool_not_default） |
| `convention_set` | convention |  |  | 規約集合の ID・版・照合値（固定した照合値と登録の内容） | replay_record.support_problems（convention_set_unsupported）<br>snapshot._check_support（同）<br>conventions.require_state_conventions |
| `git_commit` | auxiliary |  |  | Git の HEAD（補助の情報。識別に使わない） | 記録・スナップショットの見出し（任意） |
<!-- generated:identifiers end -->

`--check` は、値を書いた識別子がコードの値と同じことを確かめます（コードの値が変われば、この表を作り直す）。

## 4. エンジンの版による判定

現行の判定は、エンジンの版が違えば U4・S5・スナップショットを一律に `unsupported` にします（`engine_version_differs`）。

<!-- generated:version begin -->
| 場合 | 版の規則 | 結果 |
|---|---|---|
| 今（現行の方式） | 版が違えば U4・S5・スナップショットは unsupported | 版は毎回上がり、__init__.py の版の文字列が behavior_digest にも入るので、どのリリースのあとも前の記録は unsupported。版の一致の条件は behavior_digest の一致と重なり、独立の情報を足していない |
| 部品を分けても、版の不一致で拒む | 部品の識別が同じでも、版が違えば unsupported | 改善しない。閲覧用記録だけを直したリリースでも版が上がるので、U4 の記録はやはり unsupported になる。分けた識別は、版が同じ開発中の木どうしでしか効かない |
| 推奨: 版を補助の情報にする | 互換は機能ごとの部品の識別・形式と方式の識別子・依存・環境・規約集合で決め、版は表示と記録の補助 | 記録・検証の部品だけを直したリリースのあとも、ゲームの挙動の部品とその機能が使う部品が同じなら U4 の記録を扱える。版の文字列は __init__.py から外し、どの識別にも入れない（移行の M2） |
<!-- generated:version end -->

したがって、識別を分けても版の不一致だけで拒むなら、改善はありません。新しい方式では、版を互換の条件から外して補助の情報にし（D-VERSION-AUX）、版の文字列をどの識別にも入らないファイルへ移します（移行の M2）。互換を認める根拠は、版の大小や「ゲームの処理を変えていない」という申告ではなく、部品のファイルの中身の識別と、方式の既知の答え（固定した入力に対する出力のテスト）です。

## 5. 機能ごとの判定（推奨案）

部品のそれぞれを、機能ごとに「一致が要る」「読む側（今の実装。一致を求めない）」「使わない」のどれかに分けます。分けていない部品があれば `--check` が失敗します（不明は拒否）。

<!-- generated:features begin -->
| 機能 | 一致が要る部品 | 読む側（一致を求めない） | 使わない部品 | 形式・方式・環境の対応 | 補助の情報 | 注 |
|---|---|---|---|---|---|---|
| U4 の全体の再現（replay） | `game_behavior`<br>`diagnostics`<br>`adapter`<br>`replay_record` | `replay_run` | `view_record`<br>`snapshot`<br>`snapshot_replay`<br>`public_facade`<br>`legal_actions` | `replay_format`<br>`state_export_format`<br>`state_check_method`<br>`rng_check_method`<br>`diagnostic_schema`<br>`rng_format`<br>`runtime`<br>`dependencies`<br>`convention_set` | engine_version<br>git_commit<br>game_id<br>operation_id | 記録の各行の値（受理・拒否・コード・status・確認値）を作った部品は一致を求める。replay_record は書く側を兼ねるので、初版は一致を求める（緩めるかは D-WRITER） |
| スナップショットの復元（restore_snapshot） | `game_behavior`<br>`diagnostics`<br>`snapshot` | なし | `adapter`<br>`replay_record`<br>`replay_run`<br>`view_record`<br>`snapshot_replay`<br>`public_facade`<br>`legal_actions` | `snapshot_format`<br>`state_export_format`<br>`state_check_method`<br>`rng_check_method`<br>`diagnostic_schema`<br>`rng_format`<br>`runtime`<br>`dependencies`<br>`convention_set` | engine_version<br>git_commit<br>origin<br>label | 符号化の対応表に名前のついた方式がないので、snapshot の部品の一致で守る（D-CODEC）。確認値の status は診断が決めるので diagnostics も一致を求める |
| S5 の接続の再現（replay_from_snapshot） | `game_behavior`<br>`diagnostics`<br>`adapter`<br>`replay_record`<br>`snapshot` | `replay_run`<br>`snapshot_replay` | `view_record`<br>`public_facade`<br>`legal_actions` | `replay_format`<br>`snapshot_format`<br>`state_export_format`<br>`state_check_method`<br>`rng_check_method`<br>`connection_check_method`<br>`record_identity_method`<br>`diagnostic_schema`<br>`rng_format`<br>`runtime`<br>`dependencies`<br>`convention_set` | engine_version<br>git_commit<br>origin<br>label | 記録の条件（U4）とスナップショットの条件の和。記録とスナップショットの部品の識別も互いに同じこと。from_connection は whole_record とは別の保証のまま |
| 完全な記録からの閲覧用記録の作成（view_records_from_replay） | `game_behavior`<br>`diagnostics`<br>`adapter`<br>`replay_record` | `replay_run`<br>`view_record` | `snapshot`<br>`snapshot_replay`<br>`public_facade`<br>`legal_actions` | `replay_format`<br>`state_export_format`<br>`state_check_method`<br>`rng_check_method`<br>`diagnostic_schema`<br>`rng_format`<br>`runtime`<br>`dependencies`<br>`convention_set` | engine_version<br>git_commit | U4 が succeeded のときだけ作る。作った閲覧用記録は今の view_record の形式で、見出しに作った側の部品の識別を書く（観測は game_behavior に入るので、観測の違いは U4 の条件で拒む） |
| 閲覧用記録の読み取り（validate_view_record・表示） | なし | `view_record` | `game_behavior`<br>`diagnostics`<br>`adapter`<br>`replay_record`<br>`replay_run`<br>`snapshot`<br>`snapshot_replay`<br>`public_facade`<br>`legal_actions` | `view_format`<br>`diagnostic_schema` | engine_version<br>convention_set | 表示用の記録で、再現の確かめではない（replay_verified はいつも偽）。形式の版と構造で読む。実装の識別の一致は求めない（今と同じ）。作った側の部品の識別は表示の補助 |
| 将来の合法手 API（操作候補・必要な入力） | `game_behavior`<br>`diagnostics`<br>`adapter`<br>`legal_actions` | なし | `replay_record`<br>`replay_run`<br>`view_record`<br>`snapshot`<br>`snapshot_replay`<br>`public_facade` | `convention_set` | engine_version | 処理可能性の区分に診断のコード表を使い、送信は U2 のアダプタ（HostedGame・CommandResult）を通す。候補はホストの中で、その時点の状態と動いている実装から作り、保存して別の実装で使わない（docs/legal-actions-api-design.md の状態との対応）。候補の応答の形式の版は U7 で新しく設ける（legal_actions_format）。保存した候補を別の実装で読むことは対応しない |
<!-- generated:features end -->

- **一致が要る**: 記録・スナップショットの値（受理・拒否・コード・status・確認値・符号化した状態）を作った部品。記録の見出しの部品の識別と、今の実装の識別が同じこと
- **形式・方式の対応**: 形式の版・方式の名前を、読む側が知っていること（知らなければ unsupported）。方式の名前の意味は既知の答えのテストで固定する
- **補助の情報**: 表示・記録の見分けにだけ使い、互換の判定に使わない値

## 6. 原則

<!-- generated:principles begin -->
- `P-OLD-KEPT`: 現行の方式（kyuura-package-files-sha256/1）とその判定はそのまま残す。方式の名前の意味を変えない
- `P-NO-REINTERPRET`: 新しい方式から現行の方式へ、現行の方式から新しい方式へ、自動で読み替えない。現行の方式の記録は現行の判定だけで扱う
- `P-NO-SPLIT-COMPAT`: 分けたことだけを理由に、過去の記録を互換として扱わない（現行の方式の記録は部品の識別を持たないので、新しい判定に入れない）
- `P-METHODS`: ゲームの挙動が同じでも、確認値の方式・復元の符号化・診断の分類・記録の形式の違いを無視しない（機能ごとに一致を求める部品・識別子を表にする）
- `P-UNKNOWN-REJECT`: 分類のない部品・知らない方式・知らない形式の版・知らない部品の識別は、安全側に拒否する（unsupported）
- `P-NOT-AUTH`: 識別のハッシュは、偶然の違いを見つける値で、署名・出所の認証ではない（記録を書いた人が値を書きかえられる）
- `P-NOT-DECLARATION`: 互換を認める根拠を、版の番号の大小や「ゲームの処理を変えていない」という申告にしない。ファイルの中身の識別と、固定した入力に対する方式の出力（既知の答え）で決める
<!-- generated:principles end -->

## 7. 新しい方式

<!-- generated:new-method begin -->
- 名前: `kyuura-component-identity/1`（proposed）
- 定義: 部品（COMPONENTS）ごとに、その部品のファイルを現行と同じ正規化（改行を LF・BOM を除く）で連ねた sha256。部品の一覧と部品ごとのファイルの一覧はこの設計の分類で決め、分類のないファイルがあれば識別を作らない（収集・保存を拒む）
- 記録に書く項目: identity.method・identity.components（部品 → {digest, files}）・identity.classification_digest（部品とファイルの対応の sha256）・version（補助）
- 守り:
  - 分類の漏れ: パッケージのファイルの一覧と分類を名前で照らす（この設計の --check と同じ）。新しいファイルを加えたら、分類を書くまで --check が失敗する
  - 依存の向き: ゲームの挙動の部品のファイルは、ほかの層の部品を読み込まない（AST の import で確かめる）。読み込めば、その部品はゲームの挙動に入る
  - 公開の入口: public_facade のファイルは import・代入・説明の文だけ（処理を持たない）
  - 方式の既知の答え: 確認値・接続用確認値・記録の見分けの方式ごとに、固定した状態・見出しに対する値をテストに固定する。出力が変われば方式の名前を変える（同じ名前で意味を変えない）
  - 符号化の既知の答え: スナップショットの符号化に、固定した状態の保存の JSON をテストに固定する（D-CODEC で方式の名前をつけるまで、snapshot の部品の一致も求める）
<!-- generated:new-method end -->

## 8. 移行の手順

<!-- generated:migration begin -->
| 段 | ID | 内容 | 現行の判定を変えるか | 状態 |
|---|---|---|---|---|
| 1 | M0 | この設計（文書と --check）。現行の識別・判定・形式は変えない | いいえ | this_change |
| 2 | M1 | 方式の既知の答えのテスト（確認値・接続用確認値・記録の見分け・スナップショットの符号化）を加える。識別・判定は変えない | いいえ | planned |
| 3 | M2 | 版の文字列を __init__.py から別のファイル（版だけを持つ。public_facade の外の release の扱い）へ移す。現行の方式の定義（全ファイル − 4 つ）は変えないので、現行の behavior_digest の値はこのリリースで変わる（いつもと同じ） | いいえ | planned |
| 4 | M3 | 新しい方式の識別の計算（部品ごとの digest）を加える。書く側は使わない（計算とその --check だけ） | いいえ | planned |
| 5 | M4 | 新しい形式の版（kyuura_replay_format 2・kyuura_snapshot_format 2）で、見出しに新しい方式の識別を書く。形式 1 の書き出し・読み取り・判定は残す | いいえ | planned |
| 6 | M5 | 形式 2 の読み取りの判定を FEATURES の表どおりに実装する（機能ごとに一致を求める部品・形式・方式。版は補助）。形式 1 は現行の判定のまま | いいえ | planned |
| 7 | M6 | 回帰テスト: 形式 1 の記録の扱いが変わらない／形式 2 で view_record だけを変えた木でも U4 の記録を扱える／game_behavior の 1 ファイルを変えると unsupported／分類のないファイルで識別を作らない／方式の既知の答えが変われば失敗する | いいえ | planned |
| 8 | M7 | 書き出しの既定を形式 2 にするか（D-DEFAULT）。形式 1 の書き出しを残す期間 | いいえ | planned |
<!-- generated:migration end -->

- 現行の方式（形式 1 の記録・スナップショット）の判定は、どの段でも変えません。形式 1 の記録を新しい方式で読み替えません（部品の識別がないので、分けた判定に入れられない）
- 新しい方式の記録を、現行の方式の判定で読みません（形式の版で分ける）
- 合法手 API（U7）は、保存した候補を扱わないので、M3 以後を待ちません（[legal-actions-api-implementation-plan.md](legal-actions-api-implementation-plan.md)）。v0.160（U7-1）で `kyuura_engine/legal_actions.py` を部品 `legal_actions` に分類しました（新しい方式は実装していない。現行の方式では `behavior_digest` に入るので、v0.159 までの記録・スナップショットは v0.160 では unsupported。いつもの版の更新と同じ）

## 9. 判断事項（利用者の判断が要る）

<!-- generated:decisions begin -->
| ID | 問い | 推奨 | 状態 |
|---|---|---|---|
| `D-PROVENANCE` | 実行時にエンジンが読まない来歴のデータ（card_sources.json・research_links.json）をゲームの挙動から外すか | 初版は外さない（保守的）。外すなら、実行時に読まないことを確かめるテスト（読み込みの経路の検査）を先に作る | pending |
| `D-WRITER` | U4 で replay_record（書く側と読む側を兼ねる）の一致を求め続けるか | 初版は求める。書く側と読む側を分けるか、形式 2 の書き出しの既知の答えのテストができたら緩める | pending |
| `D-CODEC` | スナップショットの符号化に名前のついた方式をつけるか | つける（kyuura-snapshot-codec/1 など）。それまでは snapshot の部品の一致を求める | pending |
| `D-VERSION-AUX` | 新しい方式で、エンジンの版を互換の条件から外し、補助の情報にするか | 外す（4 章。外さなければ分けても改善しない） | pending |
| `D-FORMAT-BUMP` | 新しい識別を書くのに、形式の版を上げるか（形式 1 の任意の拡張にしないか） | 上げる（判定の規則が変わるので、形式 1 の読む側が新しい記録を形式 1 の規則で読まないように） | pending |
| `D-DEFAULT` | 書き出しの既定を形式 2 にする時期と、形式 1 を書ける期間 | M6 の回帰テストのあと。形式 1 の読み取りはやめない | pending |
| `D-RUNTIME-PATCH` | Python の版の比べを major・minor のままにするか | 今のまま（ADOPT-U3 の D-RUNTIME）。変えない | pending |
<!-- generated:decisions end -->

## 10. 検証と未確認

- `python scripts/build_implementation_identity_design.py --check`: JSON と生成区画の一致・ファイルの分類の漏れ・依存の向き・公開の入口・識別子の値・機能ごとの判定がすべての部品を扱うこと・原則・移行の段
- テスト `tests/test_implementation_identity_design.py`: 上の確かめを、わざと壊した値（加えたファイル・ほかの層を読み込むゲームのファイル・扱わない部品・版を条件にした機能・値の違う識別子）で見つけることを確かめる
- 確かめていないこと: 新しい方式の実装（計算・記録・判定）・方式の既知の答え・来歴のデータを実行時に読まないことの検査（D-PROVENANCE）。どれも実装の作業（移行の M1〜M6）
