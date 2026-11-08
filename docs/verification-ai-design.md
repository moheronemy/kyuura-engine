# エンジン検証用 AI の仕様（設計だけ。実装していない）

この文書は、合法手 API（U7）を通して対戦を自動で進め、エンジンの不具合・入力 API の不足・状態の不整合・情報境界の問題を見つけて、再現できる記録を残すための
「検証用 AI」の仕様です。段階ごとの実装計画は [verification-ai-implementation-plan.md](verification-ai-implementation-plan.md) にあります。

- この文書を作った時点（`17e31a9`）は調査・設計・文書化だけで、確認は文書とコードの静的な読み取りだけでした
- 実装の状況: V0（[verification-ai-v0.md](verification-ai-v0.md)）・V1（[verification-ai-v1.md](verification-ai-v1.md)）・V2（[verification-ai-v2.md](verification-ai-v2.md)。補完の rules-v2: [verification-ai-v2-repeat.md](verification-ai-v2-repeat.md)）を実装した。D-1〜D-12 の状態（承認済み・暫定・保留・今回扱わない）は V1 の文書の 2 章（V2 で D-7 の混合の単位を選択のエピソードに決めた。V2 の文書の 4 章）。V3 以降は未実装（V3 の boundary・negative の仕様と限定的な実装計画: [verification-ai-v3-design.md](verification-ai-v3-design.md)。D-6 の判定の基準は採用待ち）
- 検証用 AI の目的は、勝つことではありません。ランダムの行動と小さなルールの行動を組み合わせて多様な操作の列を作り、異常を分類して記録することです
- いちばん大事な原則: **ゲームの合法性（エンジン・U7）と AI の戦略を分ける**。戦略は、U7 が返した候補・入力の中で順位をつけるだけで、合法性を判定し直さない

## 0. 基点と参照した版

| 項目 | 値 |
|---|---|
| U7 のコードの検証対象 | `e26df79cc6dec913c1d15b5d8203df066334d65d`（版 0.172.0。`origin/claude/u7-5fg-impl` にある。`origin/main` にはない） |
| 実装の基点（この文書のブランチの元） | `origin/claude/u7-integration-plan` の `a84761f`（U7 の総合検証の記録の最後のコミット） |
| 基点のコードの照合 | `git diff --quiet e26df79 a84761f -- kyuura_engine` が差なし（終了コード 0）。`e26df79` から `a84761f` の差は文書・設計の生成スクリプト・2 つのテスト（`tests/test_chaos_gym_borrow_t_f1.py`・`tests/test_legal_actions_api_design.py`）だけで、パッケージ `kyuura_engine` は同じ |
| 参照した総合検証の文書 | `a84761f` の [u7-integration-verification-plan.md](u7-integration-verification-plan.md)・[u7-integration-verification-e0-g1.md](u7-integration-verification-e0-g1.md)・[u7-integration-verification-e3-g5.md](u7-integration-verification-e3-g5.md) |
| `origin/main` | `88ad4d9`（PR #38 のマージ。版 0.171.0）。U7-5f・U7-5g（0.172.0）を含まないので、検証用 AI の基点にしない |
| 作業ブランチ | `claude/verification-ai-design`（別の worktree `C:\dev\kyuura-engine-vai`。利用者の作業ツリー `C:\dev\kyuura-engine` の `main` は変えていない） |

`main` の内容は推測していません。U7-5f・U7-5g が `main` に取り込まれたら、基点を `main` に移すかを判断します（[7 章](#7-採用の判断が要る事項) の D-1）。

変えないもの: GUI・renderer・kyuura・カードデータ・固定デッキ（`kyuura_engine/decks.py`）・3 つの規約集合（既定・`CS-KYUURA-PLAY-S2A@1`・`CS-KYUURA-PLAY-PO@1`）・
エンジンのパッケージ `kyuura_engine`。

## 1. 既存の機能の調査

### 1.1 U7 の操作 API（再利用する。検証用 AI はこの経路だけで操作する）

| 部品 | 場所 | 検証用 AI での使い方 |
|---|---|---|
| `ActionHost`・`ActorSession`・`HostSession` | `kyuura_engine/legal_actions.py:391`・`:539`・`:549` | `client_api.ClientHub` の中で使われる。検証用 AI は直接呼ばない（D-3） |
| `candidates` | `legal_actions.py:559` | 本人の候補・`situation`・`empty_reason`・`coverage`（`scope_kinds`・`offered_kinds`・`not_covered_kinds`・`display_only_kinds`・`withheld_input_candidates`・`completeness`・`partial_residual`・`residual`・`unverified_paths`） |
| `inputs` | `legal_actions.py:593` | 段（`stages`）の契約。情報境界が未確認なら `withheld`（`INPUT_BOUNDARY_UNCONFIRMED`）で段を返さない |
| `check` | `legal_actions.py:609` | 候補の公開の制約だけの検査（`valid`・`refusal`）。受理の保証ではない |
| `submit` | `legal_actions.py:653` | 候補と入力から既存のコマンドを作り、包んだ対戦の `submit` に送る。結果は `accepted`・`rejected`・`failed`・`refused`（ホストの段の拒否） |
| `ClientHub`・`PlayerEndpoint`・`HostEndpoint`・`SpectatorEndpoint` | `kyuura_engine/client_api.py:94`・`:244`・`:262`・`:256` | JSON の要求と応答（`handle(dict) -> dict`。例外を投げない）。`take_updates` で閲覧者ごとの公開の更新。`verifier` の呼び出しで検証者用の `CommandResult` をホストの側だけが受け取る |
| `stage_dependency_problems` | `legal_actions.py:1622` | 依存する段の形（依存・経路の鍵・循環）の確かめ。2 段目以降のすべてが `depends_on_stage` か `path_stages` を持つ段の並びにかけ、問題があれば止める（V0 の訂正: 前の段に依存しない 2 段目（初期配置・にげる）はこの関数の対象の外。[verification-ai-v0.md](verification-ai-v0.md) 3.2 節） |

段の契約（行動生成が読む項目。`legal_actions.py` で作られる形）:

| 項目 | 意味 | 現れる種類の例 |
|---|---|---|
| `input` | `choose_option`（選ぶものの番号）か `choose_value`（値の範囲） | 全般 / `mulligan_draw`・`report_janken`・値の決定 |
| `count.min`・`count.max` | その段で選ぶ数。`min` が 0 なら省ける（`decline`） | にげるのトラッシュ・ワザといっしょに選ぶもの・カツラの 2 枚目 |
| `range.min`・`range.max` | `choose_value` の値の範囲 | 補償の枚数・ジャンケンの勝者 |
| `distinct` | 同じものを 2 回選べない | 決定・ワザ |
| `order`・`order_preserved` | 並びが結果に入るか（`significant`・`not_significant`・`not_applicable`・`unconfirmed`）。U7 は送った並びをそのまま使う | 決定・にげる・初期配置のベンチ |
| `options_from_stage`・`distinct_across_stages` | 前の段と同じ選べるものから、重ならずに選ぶ | 初期配置（バトル場 → ベンチ） |
| `depends_on_stage`・`options_by_choice` | 直前の段の番号ごとに選べるもの | エネルギー・進化・ワザ |
| `upstream_stages`・`after` | 前のすべての段の選び方ごとに別の番号（選ぶものの `after` が前の段の番号） | 特殊能力（U7-5e。0〜3 段） |
| `path_stages`・`options_by_path` | 前の複数の段の番号を `/` でつないだ鍵ごとに選べるもの | カツラの 2 枚目（U7-5g。任意の 3 段目） |
| `total_units` と選べるものの `units` | 選んだものの出すエネルギーの個数の合計の範囲（枚数ではない） | にげる |
| 選べるものの `eligible`・`processability`・`reasons` | 実行できる区分か（`EXECUTABLE` は `supported`・`may_stop_later`・`unverified`） | 全般 |

送る入力は、段の順の選ぶものの番号（または値）を並べた 1 つのリスト（`choices`）です。候補の番号 `c1…` と選ぶものの番号 `o1…` は応答ごとの値で、
同じ状態から作れば同じになりますが、取っ手（`game`・`revision`）とは組でだけ意味を持ちます。

### 1.2 処理可能性・情報の開示・coverage（混同しない軸）

| 軸 | 値 | 検証用 AI での意味 |
|---|---|---|
| `processability` | `supported` | 受け付ける前の確かめを満たし、受理のあとの反応・決定・停止のもとが場にないことを公開の情報で確かめた範囲（受理後の完走の保証ではない） |
| | `may_stop_later` | 送れる。受理のあとを評価していない（止まりうる） |
| | `unverified` | 送れる。本人の知識では受理が決まらない（送るまで分からない。`unverified_paths` に理由） |
| | `unresolved_ruling`・`not_implemented`・`technical_limit` | 送ると `CANDIDATE_NOT_EXECUTABLE`（エンジンに渡さない）。ゲーム上の禁止ではない |
| `input_disclosure` | `confirmed`・`no_input` | 入力を返す・入力がない |
| | `unconfirmed` | 入力を返さない（`withheld`。R-3・R-5） |
| `coverage.completeness` | `complete`・`partial`・`undetermined` | `scope_kinds` の種類の候補の取得の網羅だけ。受理・完走ではない |
| `coverage.residual.present` | R-2・R-3・R-4・R-5 | その応答で当てはまる残り（`public` と `actor` の scope） |

検証用 AI は、この 3 つの軸を 1 つの「合法・不正」に潰しません。記録には候補・選んだもの・送った入力ごとに、この値をそのまま残します（[4 章](#4-今の-api-の限界の扱い)）。

### 1.3 記録・再実行・診断（再利用する）

| 部品 | 場所 | 検証用 AI での使い方 |
|---|---|---|
| `adapter.start_game`・`HostedGame`・`CommandResult` | `kyuura_engine/adapter.py:216`・`:244`・`:42` | 対戦の開始と、受理したときだけ状態を進める境界。`CommandResult.verifier`（コマンド・元のコード・例外）は検証者だけ |
| `ReplayCollector` | `kyuura_engine/replay_record.py:275` | 完全な再現用記録（seed・デッキリスト・規約集合・実装の識別・受理と拒否の行・確認値）。`operation_id` を行に残す |
| `replay_run.replay` | `kyuura_engine/replay_run.py:135` | 記録のコマンドを送り直して確認値を照らす（方策を再実行しない）。`succeeded`・`diverged`・`internal_error` などの結果 |
| `view_record`（`ViewRecorder`・`view_records_from_replay`） | `kyuura_engine/view_record.py:122`・`:259` | 閲覧者ごとの記録（seed・相手のデッキ・確認値・完全な記録のコマンドを持たない） |
| `diagnostics` | `kyuura_engine/diagnostics.py` | 結果の区分（`accepted`・`rejected`・`failed`）、状態の区分、診断の分類（`invalid_input`・`unresolved_ruling`・`unsupported`・`technical_limit`・`state_integrity`・`internal_error`・`unmapped`） |
| 実装の識別 | `replay_record.implementation_identity`・`git_commit`・`runtime_identity` | 記録の見出しに使う |

静的な読み取りで見つけた接続の問題（実装の最初の段で確かめる。今回はエンジンを変えない）:

- **CN-1**: `ActionHost._state`（`legal_actions.py:460`）は包んだ対戦の `failure` を読みます。`HostedGame`（`adapter.py:258`）と `snapshot` の復元した対戦（`snapshot.py:1030`）は
  `failure` を持ちますが、`ReplayCollector` と `view_record.ViewHost` は持ちません（`grep` で `def failure` がこの 2 つにない）。`ActionHost` の説明（`legal_actions.py:11`）は
  `ViewHost` を包めると書いていますが、読み取りの上では `ClientHub(ViewHost…)`・`ClientHub(ReplayCollector…)` は候補の取得で `AttributeError` になるはずです。実行して確かめて
  いません。既存のテストは `HostedGame` の子（`tests/test_legal_actions_u7_3.py:491` の `Recording`。受理したコマンドを覚える）で U7 を通し、あとで同じコマンドを
  `ReplayCollector` に送り直して記録を作っています（`tests/test_legal_actions_u7_5e.py:447-461`）。検証用 AI は、エンジンを変えずに道具の側の小さな包み（4.6 節）で扱い、
  エンジンの側の直し（`failure` を加えるか、説明を直すか）は別の作業として提案します（D-4）

### 1.4 既存の自動の対戦・検証の道具（U7 の検証済みの範囲として扱わない）

静的な読み取りの結果、**既存の自動の対戦の道具は、どれも U7 の候補で操作を選んでいません**。完全な状態を読んでコマンドを自分で作り、`engine.apply_command`・`adapter.submit`・
`HostedGame.submit` に直接送ります。これらの結果を U7 の検証済みの範囲として扱いません（総合検証の計画も X3・X4 を U7 の検証に数えていない）。

| 道具 | 場所 | 選び方・通る API | 秘密の情報 | 再利用 |
|---|---|---|---|---|
| ランダムの駆動（不正なコマンドを混ぜる） | `tools/compat_driver.py`（`choose_command` :125・`run_scenario` :220）、`tools/stress_engine.py`（`choose_command` :304・`run_game` :775） | 重みつきランダムでコマンドを直接作り `apply_command` | 完全な状態を読む（不正な手は相手・山札のカードからも作る） | 使わない。「拒否で状態・乱数・ログが変わらない」照合（stress_engine :810）の考え方だけ参照 |
| 決まった方策の対戦 | `tests/v017_games.py`（`play_game` :220）、`tests/helpers.py`（`play_until_end` :981・`trainer_policy_command` :1707）、`tools/preset_deck_games.py`（`make_policy` :568）、`tools/existing_effect_games.py`（`make_policy` :13206）、`tests/sudden_death_games.py` | 状態から手を作り直接送る | 方策が自分の山札の中身を読むもの・停止の判定がサイドを読むものがある | 使わない（U7 を通らない。方策の考え方だけ参照） |
| lockstep・版の比べ | `tools/engine_lockstep.py`・`tools/compare_engine_versions.py`・`tools/event_kernel_compare.py` | 上の駆動の `apply_command` を差し替えて記録・比べる。`os.execve`・`subprocess`（git）を使う | 完全な状態 | 使わない（今回の範囲で実行しない） |
| 状態の監査 | `tools/snapshot_audit.py`、`tests/log_audit.py`（`log_problems` :1809・`observation_problems` :11255・`twin_command_problems` :11694）、`engine.check_invariants` | エンジンの内部 | 検証者用 | 後の段で、完全な記録に対して検証者の側でだけ使う候補（方策に渡さない） |
| U7 を通る参照クライアント | `examples/headless_client.py`（`act` :46・`play` :66） | `ClientHub` の JSON の入口だけ。いつも最初の候補（`candidates[0]`）と決まった入力 | 読まない | **再利用の出発点**（JSON の要求の作り方・入口の進め方）。説明（:7-8）は「ワザ・トレーナーを選べない」と書いているが、U7-4・U7-5c のあとは古い（直しは別の作業） |
| U7 の短い列のテスト | `tests/test_legal_actions_u7_3.py`（`setup_with_u7` :467・`Recording` :491）、`u7_4` の `play_attack_turn`、`u7_5c` の `play_with_u7`、各 U7 の `ConnectionTest` | U7 だけで固定の seed の少数の番。送ったコマンドを直接送った対戦・`ReplayCollector`・`replay_run` と比べる | 読まない（盤面の準備はテストの側） | 記録と再実行の確かめ方を再利用 |
| U7 と直接の混在 | `tests/test_legal_actions_u7_1.py`（`drive` :137・`u7_send` :107） | `trainer_policy_command`（完全な状態）で手を作り、`EndTurn` と決定の答えだけ U7、ほかは `host.game.submit` に直接 | 方策は完全な状態を読む | U7 の検証済みの範囲に数えない |
| 配布物のスモークテスト | `scripts/smoke_installed_package.py` | `ClientHub` を使うが、ピッピ人形は `game.submit(PlayTrainer(...))` で直接送る（:149-153） | 一部で状態を読む | 使わない |

リポジトリの中に `taskkill`・`psutil`・`Stop-Process`・`.kill()`・`.ps1` はありません（`subprocess` は git の呼び出し・`tools/run_mutants.py`・一部のテストだけ）。事故を起こした
`e2e_run` の系統はリポジトリの外にあります。

なお、このリポジトリの「play policy」（[play-policy-family-plan](play-policy-family-plan.md) など）は、未裁定の場面で止めずに続ける**規約集合**のことで、操作を選ぶ方策ではありません。
検証用 AI の「方策」とは別の語です。検証用 AI は規約集合を変えず、対戦を始めるときに選ぶだけです。

### 1.5 U7 の総合検証の結果と既知の残件

- 総合検証（エンジン `e26df79`・GUI `b1037bc`・renderer `af88231`）は、E0〜E5・G0〜G5 を実行し、X1〜X4（費用の大きい任意の段）は実行していません（
  [u7-integration-verification-e3-g5.md](u7-integration-verification-e3-g5.md)）。全体のテストは 303 モジュール・8,327 テスト・失敗 0・スキップ 1 でした
- 記録は「網羅の証明ではない」としています。U7 のテストは少数の固定の盤面と、固定の seed の短い `new_game` からの列で、**U7 を通して長い対戦を進めた検証はまだありません**
  （[計画](u7-integration-verification-plan.md) の 297〜302 行）。X3（`existing_effect_games`）・X4（`stress_engine`）は `legal_actions` を通らないので、U7 の検証に数えません
- 計画の X1（U7 だけで対戦を進め、各歩で直接の送信と比べる新しい道具。未実行・網羅の証明ではない）は、この検証用 AI と目的が重なります。検証用 AI は X1 の駆動の部分
  （候補から入力を作って送る）を持ちますが、「各歩で `candidates`・`inputs`・`check` の前後の状態を比べ、同じコマンドを直接にも送って比べる」lockstep の照合は持たず、
  対戦の終わりの R-A（6.7 節）で代えます。各歩の照合を加えるかは、後の段で X1 として別に判断します
- 既知の残件: R-2（自分のうらのバトル場のポケモンのワザといっしょに選ぶもの。`not_offered`。番の MAIN はいつも `partial`）、R-3（自分のうらのカードの特殊能力のうち、入力を本人の
  知識で作れないもの。`input_withheld`）、R-4（番のプレイヤーの MAIN のほかの `CheckFaceUpDeckCard`。`out_of_scope`）、R-5（情報境界を確かめていない入力。`input_withheld`）、
  PT-5e（実際の山札から引いて試す 5 つのトレーナーの使う条件。`unverified`）、UP-5t（状態の複製の上で試す 7 つの特殊能力の実装）、表示だけの FU2（`check_face_up_deck`）
- 総合検証の G4 で、GUI の e2e の後始末の道具が無関係なプロセスに強制終了を送った事故がありました（e3-g5 の 6.6 節）。その道具の系統は禁止のままです。検証用 AI は
  プロセスを探す・終了させる処理を持ちません（[8 章](#8-実行の道具の制約)）

## 2. 責任の分離

4 つの責任を分けます。クラスは最小にし、基盤（プラグインの仕組み・設定の言語・並列の実行器）は作りません。

| 責任 | 持つもの | 持たないもの |
|---|---|---|
| **A. エンジン・操作 API**（既存。変えない） | 候補と入力の条件、合法性の検査（`check`・エンジンの確かめ・`apply_command`）、実行・状態遷移・乱数・診断 | 方策・順位・探索 |
| **B. 行動生成**（新規。`actions`） | 候補の段の契約から、完成した入力（`choices`）を組み立てる。`options_by_choice`・`upstream_stages`/`after`・`options_by_path`・任意の段・`count`・`total_units`・並びを扱う。`check` と `submit` をつなぐ。知らない段の項目を見つけたら止める | カード名・カード ID・効果の型ごとの判定。エネルギーの必要数・進化の条件・対象の条件の判定 |
| **C. 戦略**（新規。`policies`） | 選択の場面（候補の選択・段の選択）に、行動生成が渡した選べるものの中で順位・確率を与える。ランダム・ルール・混合の切り替え。選んだ理由を返す | 合法性の再実装、候補の除外の判定、状態・相手の秘密・エンジンの乱数の参照 |
| **D. 検証ランナー**（新規。`runner`・`records`） | ホスト・両プレイヤー・決定の回答者の進行、上限、異常の検出と分類、記録と再現 | 方策への秘密の情報の受け渡し、プロセスの管理 |

境界の約束:

- B が選べるものとして戦略に渡すのは、U7 が返した選ぶもののうち、段の契約が今の部分の入力に許すものだけです。段の契約に書かれた制約（`count`・`distinct`・`options_by_choice` など）を
  当てはめるのは「API の契約を読む」ことで、ゲームのルールの再実装ではありません。契約にない条件（「このワザはエネルギーが足りない」など）を B・C は判定しません
- C は「選ばない」ことで候補を除けますが、それは戦略の評価です。記録には「戦略が選ばなかった」と残し、「合法でない」とは書きません
- 実行の方針（4.5 節のプロファイル）が処理可能性の区分で候補を除くのは、U7 が返した公開の区分による検証範囲の選択で、D が記録に「範囲から除いた」と残します
- C は `kyuura_engine` を import しません（テストで import を確かめる。[実装計画](verification-ai-implementation-plan.md) の V0）

### 2.1 置き場所

- 新しいコードは配布物の外の `tools/verification_ai/`（`pyproject.toml` の `packages.find` は `kyuura_engine` だけを含む）。既存の `tools/` の道具は変えません
- モジュールは 4 つまで: `actions.py`（B）・`policies.py`（C）・`runner.py`（D の進行と分類）・`records.py`（D の記録と再現）。テストは `tests/test_verification_ai_*.py`
- エンジン（A）は変えません。A の不足は「API の不足」として記録し、直しは別の作業にします

### 2.2 1 回の操作の流れ

```
ランナー(D)  : 待っている主体を status.waiting から決める（ホスト・プレイヤー 0・1）
ランナー(D)  : その主体の入口で candidates → 範囲の選択（プロファイル）→ 戦略へ選択の場面を渡す
戦略(C)      : 候補を選ぶ（理由つき）
行動生成(B)  : inputs → 段ごとに、契約が許す選べるものを作る → 戦略が段の選択をする → 完成した choices
行動生成(B)  : check（valid でなければ送らない。記録）→ submit
ランナー(D)  : 結果の分類・更新の取り出し・照合 → 記録 → 上限の確かめ → 次へ
```

## 3. ランダム・ルール・混合

3 つの方策は、同じ行動生成（B）と同じ実行の経路（D → `client_api`）を使います。違うのは選択の場面での選び方だけです。

### 3.1 ランダムの分布（名前で区別する）

「完全ランダム」という言い方はしません。実装した分布の名前で呼び、記録の `policy.distribution` に残します。

| 名前 | 何を均等にするか | 偏り | 費用 |
|---|---|---|---|
| `uniform-candidate+uniform-stage`（既定） | 候補を均等に選び、各段で、前の段の選び方のもとで契約が許す選べるものを均等に選ぶ | 完成した入力の組の数が少ない候補（`end_turn` は 1 通り）が相対的に多く選ばれる。後の段の選べるものが少ない枝が選ばれやすい。`end_turn` を 1/候補数 で選ぶので番が短くなる | 段の数に比例（列挙しない） |
| `uniform-candidate+uniform-tuple` | 候補を均等に選び、その候補の完成した入力の組（公開の制約を満たす組）を均等に選ぶ | 候補の間の偏りは上と同じ。組の数が上限（既定 4,096）を超える候補は、`uniform-stage` に落として、その事実（`tuple_fallback`）を記録する | 組の数に比例（上限つきの列挙） |
| `uniform-action`（後の段。V1 では作らない） | 全候補の完成した入力の組をまとめて均等に選ぶ | 組の多い候補（エネルギー・特殊能力）に偏り、`end_turn` がほとんど選ばれない | 全候補の列挙。上限を超えたら使えない |

段の中の選び方（`uniform-stage`）:

- `choose_value`: `range` の整数を均等に選ぶ
- `choose_option` で `count` が 1〜1: 許される選べるものを均等に選ぶ
- `count` が `min`〜`max`（2 以上・任意）: まず選ぶ数 k を `min`〜`max`（許される選べるものの数で切る）から均等に選び、次に k 個を重ならずに均等な並びで選ぶ。`decline`（k = 0）は k の値の 1 つとして
  扱う。並びが `significant`・`unconfirmed` の段では並びの違いを別の入力として扱い、`not_significant`・`not_applicable` でも U7 は並びをそのまま送るので、並びも均等に選ぶ
- `total_units` の段（にげる）: k 個の並びのうち、`units` の合計が範囲にあるものだけから選ぶ（契約に書かれた制約）。合計が範囲に入る組がなければ、入力を構築できない（3.4・6 章）
- `options_by_path` の任意の段（カツラの 2 枚目）: 鍵（前の段の組）が `options_by_path` にないなら 0 個だけ。鍵があれば `count` の通常の扱い

`uniform-tuple` の数え方は、段ごとの許される選べるものを前から順に広げる上限つきの列挙で、`total_units` などの公開の制約だけで数えます。エンジンの確かめ（にげるの `check_retreat`）は
数えるときに呼ばないので、「公開の制約を満たす組の均等」であって「受理される組の均等」ではありません。

### 3.2 候補の選択の範囲

方策に渡す候補は、実行のプロファイル（4.5 節）が決めます。プロファイルの既定（`deep`）は、`processability` が `supported`・`may_stop_later` で入力を返す候補だけです。
`unverified`・表示だけ・実行できない区分は、`boundary` のプロファイルでだけ渡します。どちらの場合も、範囲から除いた候補は種類・区分ごとの数を記録します。

### 3.3 小さなルールの方策（`rules-v1`）

対戦を深く進める（ワザ・きぜつ・サイド・終局に届く）ための小さな優先順位だけです。勝率の向上・探索・機械学習・先読みは対象外です。ルールは U7 が返した候補・選べるものの公開の項目
（`kind`・`role`・`meaning`・`card_id`・`pokemon`・ワザの `damage` の表示・観測の場の枚数）だけを読みます。

| 場面 | 優先 |
|---|---|
| 初期配置 | バトル場は eligible の最初、ベンチは eligible を上限まで（場を厚くする） |
| 補償の枚数・値の決定 | `range.max`（補償はたくさん引く）。ほかの値の決定は均等 |
| 番の MAIN（候補の順） | `play_basic` → `evolve` → `attach_energy`（つける先はバトル場を優先）→ `play_trainer` → `use_power` → `use_attack` → `end_turn`。`retreat`・`use_stadium`・場のポケモン 1 匹を指す操作は低い順位（選ぶのは混合のランダムのときだけ） |
| ワザ | ダメージの表示の数が大きいものを優先（表示が数でなければ均等）。ワザといっしょに選ぶものは 0 個 |
| バトル場に出す決定 | ついているエネルギーの枚数が多い場のポケモン（公開の観測） |
| ほかの決定 | 均等（ルールを持たない） |

同じ場面で同じ観測・候補ならいつも同じ順位にします（決まった順で同順位を切る）。各選択の理由のコード（`rule:attack_max_damage` など）を返します。

### 3.4 混合の方策

- `mixed(p_random, base_random, base_rule)`: 選択の場面ごとに、方策の乱数で確率 `p_random` ならランダム、ほかはルールで選ぶ
- 混ぜる単位は、既定を「選択の場面ごと」（候補の選択と、各段の選択が別の場面）にします。候補をランダムで選んだら段もランダムにする「操作ごと」の単位も選べるようにします（D-7）
- 選択ごとに、どちらで選んだか（`source: random | rule`）・理由のコード・方策の乱数を何回使ったかを記録します

### 3.5 乱数の分け方

| 乱数 | 種 | 使う人 |
|---|---|---|
| ゲームの乱数 | `game_seed`（`start_game` に渡す） | エンジンだけ。方策・ランナーは読まない |
| 方策の乱数 | `policy_seed` からプレイヤーごとに分けた `random.Random`（`f"{policy_seed}:{player}"` を種にする） | 戦略（C）と、ランダムの段の選択 |
| ホストの乱数 | `host_seed` の `random.Random` | ジャンケンの勝者・延長戦を始めるか（既定はいつも始める） |

方策の乱数はエンジンの乱数を消費しません。ただし、方策が違う操作を選べば、エンジンが消費する乱数（コイン・山札を切る）も変わります。これは同じ `game_seed` での比較の性質で、
「方策の変更がゲームの乱数を直接消費しない」ことと矛盾しません。取っ手は `secrets` の値で、どの乱数にも入れません。

## 4. 今の API の限界の扱い

### 4.1 4 つの段階を分ける

候補は「必ず受理される合法手の一覧」ではありません。1 つの操作の結果を、次の 4 段階で別々に記録します。

| 段階 | 失敗の記録 |
|---|---|
| (1) 入力を構築できるか（B） | `build: unbuildable`（理由: `withheld`・`no_eligible_option`・`unknown_stage_field`・`stage_shape_problem`・`total_units_unreachable`・`count_unreachable`） |
| (2) `check` を通るか | `check: invalid`（`refusal.code`） |
| (3) `submit` が受理されるか | `submit: refused`（ホストの段。`refusal.code`）・`rejected`（エンジンの拒否。診断の分類・識別）・`failed` |
| (4) 受理のあとに完走するか | 受理のあとの状態の区分（`awaiting_decision`・`halted`・`game_over`）と、停止の公開の診断。止まった操作の位置を記録 |

### 4.2 処理可能性ごとの扱い

| 区分 | `deep` | `boundary` | 受理されなかったときの分類 |
|---|---|---|---|
| `supported` | 選ぶ | 選ぶ | 拒否は **異常の候補**（受け付ける前の確かめを満たすという保証の範囲の食い違い。6 章の `guarantee_mismatch`） |
| `may_stop_later` | 選ぶ | 選ぶ | 受理の保証が「保証しない」の種類（決定・`end_turn`・ワザ・ジャンケン・延長戦）の拒否は正常な拒否。受け付ける前の確かめを満たすと書く種類（番の基本の操作・場のポケモン 1 匹を指す操作の eligible の組）の拒否は異常の候補 |
| `unverified` | 選ばない（範囲から除いたと記録） | 選ぶ | 拒否は正常な拒否（`unverified` の理由ごとに数える） |
| `unresolved_ruling`・`not_implemented`・`technical_limit` | 選ばない | 低い確率で送り、`CANDIDATE_NOT_EXECUTABLE` を期待 | 期待どおりならホストの段の正常な拒否。受理されたら異常 |

種類ごとの受理の保証の表（どの種類の拒否を異常の候補にするか）は、`legal_actions.py` の `GUARANTEE_*`（`:237-285` ほか）の `acceptance` の文から作った検証用 AI の側の表として持ち、
U7 の版が変わったら照らし直します。文を実行時に読んで判定はしません（D-6）。

### 4.3 残り・表示だけ・入力を返さない候補

| 経路 | 応答での現れ方 | 進め方 | 記録 |
|---|---|---|---|
| R-2 | 自分のうらのバトル場のポケモンの `use_attack` の 2 段目が空（`count.max` 0）。`residual.present` に R-2（`public`） | ワザだけを送れる（`unverified`。`boundary` のときだけ） | 現れた回数・位置。「ワザといっしょに選ぶものは検証の範囲の外」 |
| R-3 | うらのカードの `use_power` で `input_disclosure: unconfirmed` | 選ばない。`boundary` では `inputs` が `withheld` を返すことと、`submit` が `INPUT_BOUNDARY_UNCONFIRMED` で断ることを確かめる | `input_withheld(R-3)` |
| R-4 | 番のプレイヤーの MAIN のほかで `not_covered_kinds` に `check_face_up_deck`・`residual.present` に R-4 | 何もしない（ほかの候補で進む） | 現れた回数。「範囲の外」 |
| R-5 | 決定・特殊能力・にげるで `unconfirmed` | 選ばない。**決定の候補が R-5 なら、回答者は答えられないので対戦は進まない**（6 章の `input_unavailable`） | 決定の種類（検証者の記録だけ。完全な状態から）・位置 |
| FU2（表示だけ） | `display_only_kinds` に `check_face_up_deck`。選べるものはどれも `unresolved_ruling` | 選ばない。`boundary` では送って `CANDIDATE_NOT_EXECUTABLE` と、ほかの閲覧者への更新がないことを確かめる | 表示だけの候補の出現 |
| 入力を返さない候補（`not_implemented` で段がないなど） | `input_stages` が空・`processability` が実行できない区分 | 選ばない | 種類・理由ごとの数 |
| 候補がない | `empty_reason`（`not_actor`・`host_operation`・`game_ended`・`kinds_not_covered`・`players_to_act`） | `kinds_not_covered` で本人が操作するはずなら止める（`input_unavailable`） | 理由 |

未提供の入力を、カード定義・内部の状態・完全な記録から推測して埋めることはしません。検証者の記録に内部の値（決定の種類など）を書くのは、止まった理由を調べるためだけで、
その値で入力を作って送ることはしません。

### 4.4 知らない値

段の知らない項目、知らない `processability`・`input`・`situation`・`empty_reason`・残りの id、依存する段の並びでの `stage_dependency_problems` の問題は、推測で扱わず、その場で止めて
`api_contract_unknown` として記録します（API が変わったことを見逃さないため）。

### 4.5 実行のプロファイル

| プロファイル | 目的 | 範囲 |
|---|---|---|
| `deep` | 確認済みの経路を優先して対戦を深く進める | `supported`・`may_stop_later` の候補と eligible の選べるもの。`unverified` の候補しか進む道がない場面では止めずに `unverified` も許し、そのことを記録する（`deep_fallback_unverified`） |
| `boundary` | `unverified`・表示だけ・実行できない区分・残りの境界を調べる | すべての候補。実行できない区分・表示だけは既定 5% の確率で送り、期待した拒否を確かめる |
| `negative`（別の試験。方策を使わない） | 不正な入力でホストの段の拒否と、状態・更新が変わらないことを確かめる | 6.5 節 |

`deep` で除いた候補・選べるもの・残りは、場面ごとの数を記録し、対戦の要約に「検証の範囲から除いたもの」として出します。

### 4.6 記録しながら U7 を通す包み（CN-1 の扱い）

エンジンを変えずに、道具の側で `HostedGame` と同じ形（`state`・`submit`・`failure`）の小さな包みを作ります。包みの中で `ReplayCollector` に送り、`failure` は最後の `failed` の
`CommandResult` を返します。`ClientHub(包み, verifier=…)` で U7 を通し、完全な記録は包みの `ReplayCollector` から取ります（送り直して作るのではなく、対戦の実行と同時に作る）。
この包みは `ActionHost` の「別の経路の操作を送らない」約束を守ります（包みへの送信は `ActionHost` からだけ）。

## 5. 情報境界

### 5.1 方策に渡すもの

方策（C）と、方策のために段を組み立てる行動生成（B）に渡すのは、次の JSON の写しだけです。

- その主体の `PlayerEndpoint` の `view` の応答（本人の観測と公開の状態の区分）と、本人への公開の更新（`updates`）
- その主体の `candidates`・`inputs`・`check`・`submit` の応答
- 同じ観測のもとで本人が前に送って拒否・断られた入力の一覧（本人の送信の結果で、本人の閲覧用記録にも入る情報）

渡さないもの: `GameState`・`ClientHub`・`ActionHost`・`HostEndpoint`・相手の入口・`CommandResult`・完全な記録・`game_seed`・ゲームの乱数の状態・確認値・相手の手札・山札・サイド・
検証者用の診断。状態の複製で試すこと・先読みもしません。

### 5.2 主体を分ける

- ホストの操作（ジャンケンの結果・延長戦の開始）はランナーのホストの係（`HostEndpoint`・ホストの乱数）。プレイヤーの方策は呼ばない
- プレイヤーの操作は、その時点で待っている主体の方策だけを呼ぶ（`status.waiting` の `by` から決める。`players`（準備で両方）は 0 → 1 の決まった順で問い、候補のある方が送る。D-8）
- 相手の番の決定（相手の操作への反応など）は、決定の回答者の方策を呼ぶ。回答者の入口の `candidates` が `actor_to_act` であることと、`waiting` の主体が一致することをランナーが照らす

### 5.3 境界の確かめ（テスト）

- 方策に渡した値がすべて JSON の値（`dict`・`list`・`str`・`int`・`float`・`bool`・`None`）で、その主体の入口の応答と同じであること
- 双子: 公開の情報と本人の知識が同じで、相手の秘密（山札の並び・サイド・手札）だけが違う 2 つの状態から、同じ方策の種で同じ選択になること。U7 の既存の双子のテストと同じく、
  比べる前に、比べる主体の `observe`・`visible_log`・所有するカードの id が同じことを前提として確かめる（総合検証の双子の読み取りの点検 B の扱い）
- `policies.py` が `kyuura_engine` を import しないこと

### 5.4 記録を分ける

| 記録 | 中身 | 読む人 |
|---|---|---|
| 完全な検証者用の記録 | 見出し（実装の識別・規約集合・デッキ・seed・方策の設定）、完全な再現用記録（`ReplayCollector`）、U7 の操作の列（全主体の応答と選択と理由）、検証者用の診断、異常の前の状態の書き出し | 検証者だけ |
| 閲覧者ごとの記録 | `view_record`（プレイヤー 0・1・観戦者）と、その主体の方策の記録（本人の応答・本人の選択と理由だけ） | その閲覧者 |

閲覧者ごとの記録に、seed・方策の乱数の状態・相手の選択の理由・完全な記録の `seq` を入れません。

## 6. 異常の検出と再現

### 6.1 対戦の終わり方の分類（1 つの対戦に 1 つ）

| 分類 | 条件 |
|---|---|
| `game_over` | 状態が `game_over`（正常な終局。延長戦を含む） |
| `halted_known` | 状態が `halted` で、停止の公開の診断の分類が `unresolved_ruling`・`unsupported`・`technical_limit`（既知の未裁定・未対応による停止）。停止のコードを記録 |
| `input_unavailable` | 操作するはずの主体に、送れる入力がない（R-5 の決定・`kinds_not_covered`・すべての候補が `withheld`・入力を構築できない） |
| `failed` | `submit` の結果が `failed`、`CLIENT_GAME_UNAVAILABLE`、ランナー・入口からの例外 |
| `integrity` | 状態の不整合（`failed` で分類が `state_integrity`）か、ランナーの照合の不一致（6.3 節） |
| `api_contract_unknown` | 4.4 節の知らない値 |
| `no_progress` | 送れる入力をすべて試して拒否・断りになった（6.4 節） |
| `limit` | 上限に届いた（操作数・受理数・番の数・時間・拒否の数。どの上限かを記録） |

### 6.2 操作ごとの数（終わり方とは別に数える）

正常な受理、正常な拒否（エンジンの `rejected`。診断の識別ごと）、ホストの段の `refused`（コードごと）、`check` の `invalid`、入力を構築できなかった場面、範囲から除いた候補、
異常の候補（`guarantee_mismatch` など）。

### 6.3 ランナーの照合（異常の候補）

- `check` が `valid` なのに `submit` が `CANDIDATE_INPUT_INVALID`、または `check` が `invalid` なのに同じ入力の `submit` が受理（`boundary` で比べたときだけ）
- `supported`（と 4.2 節の表の種類の `may_stop_later` の eligible の組）の拒否（`guarantee_mismatch`）
- 依存する段の並びでの `stage_dependency_problems` の問題、`options_by_choice` などが参照する選ぶものがない
- `candidates` の `situation` と `status.waiting` の主体の食い違い、だれも操作できないのに終局・停止でない（`deadlock`）
- 拒否・断りのあとに、ほかの閲覧者へ公開の更新が出た。受理のあとの更新の `number` が連続しない。更新の観測が同じ主体の `view` と違う
- 受理のあとの `refetch_required` が真でない
- 対戦の終わりに、完全な記録の `replay_run.replay` が `succeeded`（閉じた記録）・`recorded_failure`（`failed` で止めた記録）でない

### 6.4 拒否を繰り返さない

- ランナーは、状態が変わらないあいだ（拒否・断りは状態を変えない）、本人が送って拒否・断られた入力（候補の種類と、選んだものの公開の項目の並び）を覚え、方策に「同じ観測で拒否された入力」として渡す
- 行動生成は、戦略が選んだ完成した入力がその一覧にあれば、選び直しを戦略に求める（選べるものの合法性は変えない。記録には `retry_after_rejection` と残す）
- 同じ状態での拒否・断りは既定 16 回まで、続けての断りは既定 32 回まで。超えたら `no_progress` か `limit` で止める
- 拒否はすべて記録・集計し、隠しません。方策が拒否を見て合法性を書き直すことはしません

### 6.5 不正な入力の試験（`negative`。通常の選択と別）

方策を使わず、通常の対戦の途中の決まった位置で、正しい入力から作った不正な入力（知らない番号・重なり・数の超過・段の並びの誤り・古い `revision`・別の主体の取っ手・別の対戦の
`game`・知らない項目・型の誤り）を送り、ホストの段の拒否（コード）と、状態・取っ手・ほかの閲覧者への更新が変わらないことを確かめます。不正な入力の試験の結果は通常の対戦の分類に
混ぜず、別の要約にします。

### 6.6 保存するもの

| 項目 | 中身 |
|---|---|
| エンジン | `git_commit`（実行の前に 1 回だけ取る）・`kyuura_engine.__version__`・`implementation_identity`（パッケージのファイルの sha256）・`runtime_identity` |
| 規約集合 | `set_id@version`（記録の見出しの `convention_set`） |
| デッキ | 固定デッキの `deck_id` かデッキリスト（とその sha256） |
| ゲーム | `game_seed` |
| 方策 | 名前・版（`rules-v1` など）・設定（分布・混合率・プロファイル・上限）・`policy_seed`・`host_seed` |
| 操作の列 | 操作ごとに: 永続の操作の識別（`run_id` と通し番号の `operation_id`）、主体、候補の種類と公開の項目、段、選んだもの（番号と公開の項目）、選択の理由と出所、`check`・`submit` の応答、更新の番号、状態の区分 |
| 診断 | 拒否・失敗の診断の識別・分類・元のコード（検証者用） |
| 異常 | 異常の分類、直前の位置（操作の通し番号・受理の番号・区間・番・段階）、その位置の確認値、状態の書き出し（検証者用） |
| 完全な記録 | `ReplayCollector` の記録（`operation_id` を含む）と閲覧者ごとの記録 |

取っ手（`game`・`revision`）と応答ごとの候補の番号は一時的な値で、永続の操作の識別にしません。記録に残すときは、照合用の値として、永続の識別と別の項目に置きます。

### 6.7 3 つの再現の方法を分ける

| 方法 | 何を送るか | 方策に依存するか | 確かめること |
|---|---|---|---|
| R-A 操作の列の再実行 | 完全な記録のコマンド（`replay_run.replay`） | しない | エンジンが同じ結果・確認値になる（U7 を通らない） |
| R-B U7 の経路の再実行 | 記録の操作ごとに、同じ主体の入口で `candidates` を取り直し、候補を種類と公開の項目で、選ぶものを公開の項目で探して、同じ `check`・`submit` を送る | しない | U7 の応答（取っ手を除く）と結果が記録と一致する。異常が同じ位置で起きる |
| R-C 方策の再実行 | 同じ `game_seed`・方策の版・設定・`policy_seed`・`host_seed` で最初から走らせる | する | 同じ操作の列になる（方策のコードが同じときだけ意味がある） |

再現は R-A・R-B を基本にし、R-C は方策の決定性の確かめに使います。自動の最小化（列を縮める）は後の段にします（[実装計画](verification-ai-implementation-plan.md) の V6）。

### 6.8 到達範囲の測り方

対戦の数・勝率では十分さを判断しません。次の到達範囲を、対戦ごとと集計で出します。

- 候補の種類ごと: 出た・選んだ・受理・拒否・断りの数（`IMPLEMENTED_KINDS` と比べて、届かなかった種類を出す）
- 入力の形: `input` の種類、`count` の範囲（2 以上・任意）、`decline` を選んだ・選ばなかった、`depends_on_stage`・`upstream_stages`（段の数 0〜3）・`options_by_path`・`options_from_stage`・
  `total_units`・並びの区分
- 決定の種類（`decision_kind`）ごとの回答の数（`DISCLOSURE_CONFIRMED_KINDS` と比べる。R-5 で答えられなかった種類は別に数える）
- 処理可能性・理由（`reasons`）・`unverified_paths` の理由ごとの選んだ数
- 残り（R-2〜R-5）の現れた数、表示だけの候補の数
- 状態の区分・段階・区間（延長戦に入ったか）・状況（`situation`）・`empty_reason`
- 終わり方・停止のコード・診断の識別・異常の分類

## 7. 採用の判断が要る事項

| id | 事項 | 案（推奨を先に） |
|---|---|---|
| D-1 | 実装の基点 | `a84761f`（U7 のコード `e26df79` と同じパッケージ・総合検証の記録を含む）から作る / U7-5f・U7-5g が `main` に入るのを待つ |
| D-2 | コードの置き場所 | 配布物の外の `tools/verification_ai/` / パッケージの中（配布物の検査の対象が増える） |
| D-3 | 操作の層 | `client_api`（JSON の入口。GUI と同じ契約）/ `ActorSession`（Python の値）。推奨は前者で、後者は U7 の下の層として既存のテストに任せる |
| D-4 | CN-1 | 道具の側の包み（4.6 節）で始め、エンジンの `ReplayCollector`・`ViewHost` の `failure` か `ActionHost` の説明の直しを別の作業として提案する / 先にエンジンを直す |
| D-5 | 既定のランダムの分布 | `uniform-candidate+uniform-stage` / `uniform-candidate+uniform-tuple` |
| D-6 | 拒否を異常の候補にする種類の表（4.2 節） | 道具の側の表（U7 の `GUARANTEE_*` から作り、版ごとに照らす）/ U7 の応答に機械が読める保証の区分を加える（API の変更。別の作業） |
| D-7 | 混合の単位 | 選択の場面ごと / 操作ごと |
| D-8 | 準備で両方が操作する場面の順 | 0 → 1 の決まった順 / ホストの乱数で順を決める |
| D-9 | ジャンケンの勝者 | ホストの乱数で均等 / 対戦ごとに交互 |
| D-10 | 証跡の置き場所と保存 | リポジトリの外の兄弟のフォルダ（`C:/dev/kyuura-engine-verification-vai/`。台帳が読む `C:/dev/kyuura-engine-verification/` と別）に、段ごとに sha256 つきで保存 / 一時フォルダだけ |
| D-11 | 上限の既定値 | 1 対戦の操作 2,000・受理 1,000・番 200・時間 120 秒・同じ状態の拒否 16・続けての断り 32 / 別の値 |
| D-12 | V1 以降のデッキと規約集合の組 | 固定デッキ 4 つ × 3 つの規約集合の 1 seed ずつ（12 対戦）/ もっと小さく |

## 8. 実行の道具の制約

- 単一のプロセスで、上限つきで実行します。並列の実行・子プロセスの起動・プロセスの検索・終了の処理を持ちません（`subprocess`・`taskkill`・`Stop-Process`・`psutil` を使わない）。
  実装の識別の `git_commit` は外の呼び出し側が実行の前に 1 回だけ取り、ランナーの中では `ReplayCollector.start(..., include_git=False)` を使います
- 時間の上限は、操作の合間に `time.monotonic()` を見て自分で止める協調的な上限です（ほかのプロセスを止めない）
- 禁止中の E2E・後始末の道具（`e2e_run` の系統など）は使いません。GUI は検証用 AI の対象外です
- 大量の対戦・lockstep・状態の監査・全体のテストは、この文書の範囲では実行しません。実装の段の限定のテストは [testing](testing.md) に従い、1 モジュールずつ実行します
