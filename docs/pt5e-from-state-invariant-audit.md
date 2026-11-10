# PT5E-FROM-STATE-INVARIANT の監査と最小修正の計画（構築した状態の公開入口の整合性）

[PT-5e の補完](legal-actions-pt5e-audit.md)（v0.176.0。9.2 節）で、`ClientHub.from_state` が不変条件の崩れた状態を受け付けることが分かりました。
この文書は、その入口と関連する公開入口の契約・実装の監査と、最小修正の計画です。追記（v0.177）: 利用者が案 B を採用し、v0.177.0 で実装しました（9 章）。1〜8 章は監査のときの記録のままです。**調査・設計・文書化だけで、入口の修正・テスト・ビルド・対戦・モジュールの読み込みはしていません。**
エンジン・AI・GUI・renderer・データ・固定デッキ・規約集合・裁定・識別方式・版（0.176.0）は変えていません。

## 0. 基点と範囲

| 項目 | 値 |
|---|---|
| 基点 | `7533fbb2679c97fc47e7326efa3f7d77d4e089af`（`claude/vai-0176-follow`。PT-5e の実装 `9b1d098`・版 0.176.0 の `6f62700`・文書 `fba415a` と、検証用 AI の追従 `41c819d`・`7533fbb` を含む） |
| main への取り込み | なし（`origin/main` は `88ad4d9`。`fba415a` は `origin/main` の祖先でない。`7533fbb` を含むリモートのブランチは `origin/claude/vai-0176-follow` だけ） |
| 作業ブランチ | `claude/pt5e-from-state-audit`（専用の worktree `C:\dev\kyuura-engine-vai`。利用者の `C:\dev\kyuura-engine` は main のまま、変更なし） |
| GUI（読み取りだけ） | `feature/engine-pt5e-trainers` の `dbb6456eb87fa7fd864185a612ee573e512c98b1`（0.176.0・`6f62700` を固定） |
| 方法 | コード・文書・保存済みの証跡の読み取りと、静的な照らし合わせ。根拠の種類を「コード」「既存テストの主張」「保存済みの実行の証跡」で書き分ける |

## 1. 既存の問題と証跡

### 1.1 何が起きたか

| 項目 | 内容 | 根拠の種類 |
|---|---|---|
| 崩した不変条件 | おもての山札の印の並び（`faceup.prefix_problems`。`check_invariants` の一部）。印は山札のそれぞれで上から続く並びでなければならない。テスト専用の改変 `broken_marks(state, owner, position)` が、相手（プレイヤー 1）の山札の `position` 枚目（0 から）の 1 枚だけに印を付けた（いちばん上はうら） | コード（`tests/test_legal_actions_pt5e_v0_176.py` の `broken_marks`、`faceup.py` の `prefix_problems`） |
| 公開の情報 | 本人の手札・枚数・観測。おもての山札の印は、正しい状態では「上から n 枚」として観測に出る。崩れた 2 つの状態（2 枚目だけ・7 枚目だけ）で本人の観測は同じ | 既存テストの主張（`observe(far, 0) == observe(near, 0)`） |
| 秘密 | 相手の山札の中でどの位置に印があるか（崩れた状態では観測に出ない位置）。正しい状態では起こらない値 | コードと既存テストの主張 |
| 要求と応答の差（候補） | 候補・inputs・check の答えは 2 つの状態で同じ（`unverified`・`use_condition_not_evaluated`）。PT-5e の候補の側のガード（`_use_condition_evaluated` が `prefix_problems` があれば評価しない）による | 既存テストの主張（`queries(far)[0] == queries(near)[0]`）、保存済みの証跡（`pt5e-v0.176/twin_results.json` の `prefix_guard`: `responses_equal: true`） |
| 要求と応答の差（送信） | カツラのクイズ その3 を `HostedGame.submit` で送ると、2 枚目なら使う前の拒否 `REJECTED`・`FU3`、7 枚目なら受理のあとのコマンドの終わりの確かめで `FAILED`・`STATE_INTEGRITY`（対戦が止まる） | 既存テストの主張（`outcomes == [(FAILED, "STATE_INTEGRITY"), (REJECTED, FU3)]`）。保存済みの証跡は、このテストを含むモジュールが 3 回目で失敗 0（`pt5e-v0.176/tests/run3_pt5e.txt`） |
| もう 1 つの差 | 候補の側のガードの結果（評価するか）そのものが、不変条件の崩れの有無で変わる。エンジンが作らない状態についての 1 ビット | 文書（監査の 9.2 節）と `pending.json` |
| 候補の側で防いだ範囲 | 候補・inputs・check が、崩れた状態で引いて試す条件を呼ばないこと（応答が秘密の位置によらない） | 既存テスト |
| 送信・直接のコマンドに残る挙動 | `apply_command` は入力の状態を確かめず、返す状態だけを `_require_integrity` で確かめる（コード: `engine._apply`・`_require_integrity`）。そのため、崩れた状態からの送信は、処理の途中で出る拒否か、処理を終えたあとの `StateIntegrityError` かに、秘密の位置で分かれる。同じ形で、使えないカードの拒否（`NO_OTHER_CARDS_IN_HAND`）は本人だけに返る（`test_broken_invariant_keeps_the_engine_rejection_private`） | コードと既存テスト |
| new_game からの到達 | **ない**。通常の進行は各コマンドの終わりで `check_invariants` を通った状態だけを返し（`engine._require_integrity`）、スナップショットは保存の前と復元のあとに確かめる。崩れた状態は、テスト専用の改変（状態の直接の書きかえ）でしか作っていない。通常の合法な対戦で再現した問題ではない | コードと既存テスト（`test_normal_progress_keeps_the_invariant`・`test_snapshot_restore_rejects_a_broken_invariant`） |

### 1.2 問題の性質

- 不整合な状態を受け付ける入口があり、その状態ではエンジンの拒否・失敗の分かれ方が、観測に出ない値で変わる（情報境界の前提が崩れる）
- エンジンの処理の誤りではない（エンジンは崩れた状態を作らない）。入口の契約（何を受け付けるか）の問題
- 修正しても、通常の対戦の結果は変わらない（通常の状態は今も不変条件を満たす）

## 2. 公開入口の一覧と責任（コードから）

| 入口 | 受け付ける値と契約（docstring） | 複製か参照か | 今の確かめ | 時期 | 不整合のとき | halted・終局・決定待ち・準備中 | 呼び出し元（エンジンの外） | 信頼の境界 |
|---|---|---|---|---|---|---|---|---|
| `engine.new_game` | デッキ・seed・規約集合 | 新しい状態を作る | `check_invariants`＋サドン・デスの開始の確かめ | 返す前 | `StateIntegrityError`（エンジンの不具合） | 作るのは準備中だけ | 全般 | 公開。入力はデッキ・seed（状態でない） |
| `adapter.start_game`・`ClientHub.start`・`ActionHost.start`・`ReplayCollector.start`・`ViewHost.start` | 同上を `CommandResult` で | 同上 | `new_game` の確かめ | 返す前 | `FAILED` の結果（分類 `state_integrity`） | 同上 | GUI の `local_match`、AI のランナー | 公開。外から状態を受け取らない |
| `engine.apply_command`（`apply_command_with`・`_traced` は内部・試験用） | 状態とコマンド。「渡した状態が壊れている → `StateIntegrityError`」 | 渡した状態を変えず、新しい状態を返す | 入力の状態: `require_state_conventions` だけ。返す状態: `check_invariants` | 処理の前（規約）と返す前（不変条件） | 処理の途中の拒否か、返す前の `StateIntegrityError`（**入力の不整合を処理の前に見ない**） | 終局・停止への操作は拒否。決定待ちは答えだけ | 全般（GUI の固定例の再生も） | 低層の公開 API。入力の状態の整合は呼び出し側の責任（docstring の「壊れている」は結果としての検出） |
| `adapter.submit(state, …)` | 状態とコマンドを `CommandResult` に | 同上 | `apply_command` と同じ。`StateIntegrityError` は `FAILED` | 同上 | `FAILED`（`STATE_INTEGRITY`）か拒否 | 同上 | `HostedGame` | 低層 |
| `adapter.HostedGame(state)` | 「信頼されたホストが状態を持つ最小の境界」 | **参照を持つ**（複製しない） | なし | — | 送信のときに上と同じ | 状態のまま | `ActionHost`・`ClientHub` の各入口、`RestoredGame`、`ReplayCollector`、`ViewHost`、テスト（`ClientHub(A.HostedGame(state))` の形が 5 ファイル: エンジン 2・検証用 AI のテスト 3） | 信頼された内部。外からの状態の整合は保証しない |
| `legal_actions.ActionHost(game)` | 「信頼されたホストの入口」。包んだ対戦の別名・直接の変更は保証の外 | game の参照 | なし | — | 同上 | 同上 | `ClientHub.__init__`、テスト | 信頼された内部 |
| `legal_actions.ActionHost.from_state(state)` | 「状態の複製を `HostedGame` で包む」 | **複製**（`state.clone()`） | **なし** | — | 送信のときに上と同じ | 状態のまま | エンジンのテスト 3 ファイル（`decision_audit`・`u7_1`・`u7_2`） | ホスト。外から状態を受け取る入口 |
| `client_api.ClientHub(game)` | 「信頼されたホストの側の対戦」 | game の参照 | なし | — | 同上 | 同上 | 検証用 AI のランナー（`run_v3_3` などが `RestoredGame` を包む。復元で確かめ済み）、テスト | 信頼された内部 |
| `client_api.ClientHub.from_state(state)` | 「状態の複製から（ホスト・テストの側。復元した状態から始めるとき）」 | **複製**（`HostedGame(state.clone())`） | **なし** | — | 同上（PT-5e の問題） | 状態のまま | GUI の固定例（`scenarios.py`。公開の `new_game`・`apply_command` で再生した状態）と GUI のテスト専用盤面（`p6_boards`・`r3a_boards`・`pt5e_boards`。作るたびに `check_invariants` が空を確かめる）、テスト 14 ファイル（エンジン 12・検証用 AI の `test_verification_ai_v0`・`_v1` の 2。どれも構築盤面） | ホスト。**プレイヤーの入口（取っ手）を配る前の、外から状態を受け取る入口** |
| `snapshot.save_snapshot` | 状態を保存 | 読むだけ | 境界の確かめ（型・余分な属性・`pending_moves`・規約集合・決定の再開先・ルール・効果の登録・カードプール）＋`check_invariants`＋`structure_problems` | 保存の前 | `SnapshotSaveError`（場所の名前だけ。値を入れない） | 保存できる（決定の再開先が未対応なら拒否） | AI の run_p6・run_u_r3a・run_v3_3 | 公開。検査が最も厳しい |
| `snapshot.restore_snapshot`・`RestoredGame(report)` | JSON・`StateSnapshot` → 状態。`RestoredGame` は restored の結果だけ | 新しい状態を組み立てる。`RestoredGame` は `HostedGame(report.state)` | 形式・対応・解決・組み立て・`supported_decision_error`・`structure_problems`・`check_invariants`・規約集合・確認値・往復 | 復元のとき | 結果の種類（`inconsistent` など）と問題の場所。例外は内部エラーの結果（`MemoryError` は投げ直す） | 停止・終局も作れる（状態のまま） | AI の fixture（V3-3・P6・U-R3a） | 公開。外部の入力（ファイル）の境界 |
| `view_record.ViewRecorder.attach(viewer, state)` | 途中（構築した状態を含む）から閲覧用記録を始める | 参照を読む | なし | — | — | 状態のまま | `RestoredGame`（確かめ済み）・テスト | 信頼された内部（記録） |
| `observation.observe`・`visible_log` など | 状態の観測 | 読むだけ | なし | — | 入力による（例外もありうる） | — | 全般 | 低層（読むだけ） |

まとめ:

- 外から作った `GameState` を受け取って**プレイヤーの入口を配れる**のは、`ClientHub.from_state`・`ActionHost.from_state`（とその下の `HostedGame(state)`・`ClientHub(game)`・`ActionHost(game)` の直接の組み立て）
- そのうち、確かめるのは**スナップショットの復元の経路だけ**。`from_state` の 2 つは複製はするが確かめない
- `HostedGame`・`ActionHost(game)`・`ClientHub(game)` は docstring で「信頼されたホストの内部」の境界。`from_state` の 2 つは「ホスト・テストの側」と書かれ、受け付ける状態の整合の条件は書かれていない（契約の空白）

## 3. 不変条件の確かめ（`engine.check_invariants`）の範囲

### 3.1 保証すること（コードから）

- カードの保存則: すべてのカードが持ち主のゾーンの 1 か所にだけある（山札・手札・サイド・トラッシュ・場・進化の下・ばける・ついているエネルギー・ついているトレーナー・スタジアム・使用中のトレーナー・外側のトレーナー・置いておくカード）。未知の番号・重複・持ち主の違い・どこにもないカード
- カードの表の形（`uid` と鍵・持ち主・出所）、`new_game` で作った状態ならデッキリストとの一致（`decklists` が空なら見ない）、所有者の変更（`_ownership_problems`）、区間（`_segment_problems`）
- 場の形: ポケモンのカード・ダメージ（10 の倍数・HP 未満。決定待ちの例外つき）・ベンチの上限・サイドの枚数・特殊状態・進化の重なりと番（ログがあれば照らす）・持続する効果・マーカー・うらのカード・場のポケモンの番号
- 段階と決定: `Phase` の型、番の進行、終局・停止の条件（決定・使用中のトレーナー・結果・止めた理由・途中停止の記録）、決定の形（`_decision_problems`）、トレーナーの使用中の形
- 履歴: 番の終わりとポケモンチェックの回数、パワーでつけた回数、トレーナーの禁止、履歴（`_history_problems`）
- おもての山札の印（`faceup.prefix_problems`）・おもてのサイド・置いておくカード・スタジアム・リコール

### 3.2 保証しないこと

- **合法な操作の列から到達できること**（不変条件を満たすことは到達可能と同じではない。`build_test_state` の盤面は進化のログを置かないなど、到達を前提にしない）
- 乱数の状態と履歴の整合（乱数はどの値でも受け付ける）
- 効果の登録・カードデータ・ルールの組が既定のものであること（`snapshot._boundary_problem` が見る。`check_invariants` は見ない）
- 規約集合の整合（`require_state_conventions`。コマンドごとに見る）・決定の再開先の対応（`supported_decision_error`）
- 状態の構造（`snapshot.structure_problems`: `cards` の型・定義の組・…）、`pending_moves` が空であること（snapshot と `replay_run` が見る）
- 外から状態を直接書きかえていないこと（`ActionHost` の docstring のとおり検出しない）

### 3.3 確かめ自体の性質

| 観点 | 読み取りの結果 |
|---|---|
| 副作用 | 状態を読むだけ（問題の文のリストを返す）。乱数・ログ・状態を変える呼び出しは見当たらない |
| 例外 | 値の型・参照が壊れていると例外になりうる（例: `state.card_def(uid)` は定義のないカードで引けない、`state.players` の形が違えば属性の読み取りで失敗）。一部は型を確かめて文にする（`Phase`・進化の重なり・番号）が、すべてではない |
| 秘密を含みうる診断 | 問題の文に、カードの番号・ゾーン（山札・手札・サイド）・持ち主の名前が入る（例: 「カード 12 が プレイヤー 1 の hand と deck の 2 か所にある」）。**プレイヤーに渡してはいけない**。今は `StateIntegrityError.problems`・`str(error)` に入り、`adapter._report` で検証者用の記録（`VerifierReport.problems`）だけに入る。プレイヤーには分類の固定の文（「対戦の状態に問題が見つかったため、対戦を続けられません。」）だけが返る |
| コスト | 各コマンドの終わりに毎回呼んでいる確かめと同じ（1 回分）。退化のログがあればログを最初から読む |
| 安全に受け付けられる入力 | `GameState` の型で、`check_invariants` が例外なしに空を返すもの。型の違う値・確かめの中の例外は「確かめられない」として拒否する（受け付けない）のが安全 |

## 4. 拒否の方針の候補と推奨

### 4.1 比べた案

| 案 | 内容 | 長所 | 短所 |
|---|---|---|---|
| A | `ClientHub.from_state` だけで確かめる | 変更が最も小さい | `ActionHost.from_state` に同じ空白が残る。2 つの入口で契約が違う |
| **B（推奨）** | 2 つの `from_state` が使う**共通の下位の関数を 1 つ**作り、そこで複製してから確かめる（`ClientHub.from_state` と `ActionHost.from_state` の両方がそれを呼ぶ） | 外から状態を受け取って入口を配る 2 つの経路を 1 か所で閉じる。重複しない。複製した写し（ホストが持つもの）を確かめるので、呼び出し側の別名による確かめのあとの変更の影響を受けない | `from_state` で崩れた状態を作っていたテスト 2 件の書き方が変わる（5 章） |
| C | `HostedGame.__init__` で確かめる | 低層まですべて閉じる | `RestoredGame`・`ReplayCollector`・`start_game` の経路（確かめ済み）で二重になる。信頼された内部・検証者用の構築（崩れた状態の候補の振る舞いを確かめるテスト・AI の接続のテスト）の道がなくなり、その代わりに無検査の選択肢が要る |
| D | 契約を文書にするだけ | コードを変えない | 問題（入口が崩れた状態を受け付け、秘密の位置で結果が分かれる）が残る |

推奨は **B**。公開クライアントの境界（プレイヤーの入口・取っ手を配る前に、ホストが外から状態を受け取る `from_state`）と、信頼された内部・検証者の境界（`HostedGame(state)`・`ActionHost(game)`・`ClientHub(game)` の直接の組み立て。docstring で「信頼されたホストの内部」）を分けます。

- **無検査の選択肢は公開 API に加えない**。崩れた状態をあえて作る検証（PT-5e の候補の側のガードのテストなど）は、既存の低層の組み立て（`ClientHub(A.HostedGame(state))`）を使う。これは新しい抜け道ではなく、既存の信頼された内部の入口で、その契約（呼び出し側が整合を保証する）を docstring に明記する
- 低層の公開 API（`apply_command`・`adapter.submit`・`observe`）は、契約の明記だけにする（入力の状態の整合は呼び出し側の責任。返す状態は今までどおり確かめる）
- 規約集合・決定の再開先は入口で見ない（今もコマンドごとに処理の前に拒否し、その拒否は状態の公開の値で決まる）。入口に加えるかは採用の判断（7 章）
- スナップショットの境界の確かめ（効果の登録・カードプール・構造）は入口に流用しない（テスト用の効果の登録・テスト専用のカードの組の盤面を拒否してしまう。`check_invariants` より強い前提）

### 4.2 拒否の形式（推奨）

| 観点 | 推奨 |
|---|---|
| どこで | `from_state` の中、`HostedGame` を作る前（ホスト・セッション・取っ手を作る前）。状態を変えない（確かめは複製に対して、読むだけ） |
| 何で | Python の例外（`from_state` は JSON の要求ではなくホストの API なので、クライアントの要求・応答のスキーマ・エラーのコード表は変えない）。新しい例外の型を 1 つ（仮の名前 `UnusableStateError`。`ValueError` の下位。ホストの使い方の誤りの扱い）。属性 `code`（`"STATE_INTEGRITY"`＝不変条件の問題、`"STATE_CHECK_ERROR"`＝確かめの中の例外、型の違いは `TypeError`）と `problems`（問題の文。ホスト・検証者だけ） |
| 文 | `str(error)` は固定の文だけ（問題の文・カードの番号を入れない）。ホストがそのまま画面・ログの公開の部分に出しても秘密を出さない。詳しい問題は `problems` 属性だけ |
| 呼び出し側の見分け | 型と `code` で見分けられる。`StateIntegrityError`（処理の結果の不整合。`FAILED` の結果になる）とは別の型にして、「入口で受け付けなかった」と「処理の途中で壊れた」を混ぜない |
| 例外の扱い | 確かめの中の `Exception` は `STATE_CHECK_ERROR` で拒否する（元の例外は `__cause__` に残す）。`MemoryError` は投げ直す（`adapter`・`restore_snapshot` と同じ）。`KeyboardInterrupt`・`SystemExit` は `BaseException` なので捕まえない（`except Exception` だけを使う） |
| プレイヤーへの露出 | 入口を作る前に拒否するので、プレイヤーの応答・公開の更新・取っ手は存在しない |
| 実行のときの確かめ | 残す（コマンドの終わりの `check_invariants`、スナップショットの確かめ）。入口の確かめは前提を作るだけで、その後の低層の操作・直接の書きかえは防がない |

### 4.3 PT-5e の候補の側のガード

**残す**（推奨）。理由: `from_state` を閉じても、信頼された内部の組み立て（`HostedGame(state)`）・`ActionHost.game` の直接の変更・低層の API からは崩れた状態がありうる。ガードはそのとき候補が秘密によって変わらないようにする多重の防御で、コストは `prefix_problems` 1 回。入口の修正のあとは「`from_state` では届かない」ことを文書に書き加える。

## 5. 互換性と利用箇所への影響（読み取り）

| 利用箇所 | 今の使い方 | 推奨の修正での見込み | 根拠 |
|---|---|---|---|
| PT-5e のテスト `test_from_state_accepts_a_broken_invariant_but_the_condition_is_not_evaluated` | `ClientHub.from_state(far/near)` が受け付けることを確かめる | **意図した変化**: 拒否を確かめる形に変える（崩れた状態の候補・送信の比べは、低層の組み立てで残す） | コード |
| PT-5e のテスト `test_broken_invariant_keeps_the_engine_rejection_private` | 崩れた状態を `ClientHub.from_state` で包む | 拒否される。崩れた状態の振る舞いの確かめなので、信頼された内部の組み立て（`ClientHub(A.HostedGame(state))`）に移す（主張は変えない） | コード |
| ほかのテスト（`ClientHub.from_state` を使う 13 ファイル＋`ActionHost.from_state` の 3 ファイル。検証用 AI の `test_verification_ai_v0`・`_v1` の実際の盤面の確かめを含む） | 多くは `build_test_state` の構築盤面 | **静的には決められない**。`build_test_state` は最後に `check_invariants` を呼ばない。ただし、多くのテストは同じ盤面から受理された操作を確かめており（受理は返す状態の不変条件を通る）、入力が整合している間接の根拠になる。候補だけを見るテストの盤面は未確認 | コード（`tests/helpers.py`） |
| 検証用 AI（`tools/verification_ai`） | 実行のコードは `from_state` を使わない。fixture は `snapshot.save`→`restore`→`RestoredGame`→`ClientHub(game)`（復元で確かめ済み）。接続のテスト（`_p6`・`_u_r3a`・`_v0176_follow`）は `ClientHub(A.HostedGame(state))`（崩れた状態の `unverified` の確かめを含む）。テストの `_v0`・`_v1` だけが構築盤面を `ClientHub.from_state` で包む | 実行のコード・fixture・接続のテストは影響なし。`_v0`・`_v1` は上の行と同じく盤面しだい（未確認） | コード（`tools/verification_ai/fixtures_*.py`・`run_*.py`・`tests/test_verification_ai_*.py`） |
| GUI（`dbb6456`） | 固定例（`scenarios.py`）は公開の `new_game`・`apply_command` で再生した状態を `ClientHub.from_state` で包む。テスト専用盤面（`p6_boards`・`r3a_boards`・`pt5e_boards`）は作るたびに `check_invariants` が空を確かめてから `from_state` | 影響なしの見込み（どちらも不変条件を満たす状態だけを渡す）。停止の固定例（`halt_seed1`）も `apply_command` が返した状態なので満たす。GUI が例外を画面に出す経路があれば、新しい例外の扱いを接続層で決める | GUI の `server/kyuura_gui_server/scenarios.py:126`・`server/tests/*_boards.py`・`docs/engine-contract.md:40` |
| 文書の例 | `legal-actions-u7-1.md`（`ActionHost.from_state` の表）・`verification-ai-v3-design.md`（構築盤面を `from_state` で包む案）・GUI の `engine-contract.md` | 受け付ける条件（不変条件を満たす状態）と拒否の例外を書き加える | 文書 |
| 保存・復元・記録 | 変えない（スナップショットは今も確かめる。`ReplayCollector`・`ViewHost` は `start` だけ） | 影響なし | コード |
| 有効な終端・決定待ち・準備中 | `check_invariants` は終局・停止（途中停止を含む）・決定待ち・準備の段階の条件を持つ | 正しく作られた状態は通る見込み。代表で確かめる（6 章） | コード |

既存の fixture が拒否された場合の扱い: その fixture の問題の文を読み、(a) fixture が不整合（盤面の作り方の誤り）なら fixture を直す理由を個別に記録する、(b) 確かめの前提が厳しすぎる（正しい盤面を拒否する）ならエンジンの確かめの誤りとして別に調べる。確かめを弱めて通す・fixture を一括で書きかえることはしない。

## 6. 限定の検証の計画（今回は実行しない）

新しいモジュール 1 つ（仮: `tests/test_from_state_integrity_v0_177.py`。16 件まで・60 秒まで）:

| # | 確かめ | 盤面（作り方の計画） |
|---|---|---|
| 1 | 正常な new_game の状態（準備中）を `ClientHub.from_state`・`ActionHost.from_state` が受け付け、候補が `ClientHub.start` と同じ | `new_game` |
| 2 | 決定待ち・終局・停止（途中停止を含む）・サドン・デスの有効な状態を受け付ける | 既存のテストの経路（公開のコマンドで進めた状態）。新しい対戦・seed の探索はしない |
| 3 | おもての山札が連続しない状態を両方の `from_state` が拒否する（`code` が `STATE_INTEGRITY`） | PT-5e の `broken_marks` |
| 4 | 重複・所属の違い・未知の番号の代表をそれぞれ拒否する | `build_test_state` の盤面を複製して 1 か所だけ変える |
| 5 | 型の違う値（`GameState` でない）は `TypeError`、確かめの中の例外は `STATE_CHECK_ERROR` で拒否（`__cause__` に元の例外）。`MemoryError` は投げ直し、`KeyboardInterrupt` は捕まえない | 偽の状態・`check_invariants` を差し替えた小さな例 |
| 6 | 拒否で渡した状態が変わらない（指紋の前後）・ハブ・ホスト・取っ手を作らない（例外のあとに返り値がない） | 3 の盤面 |
| 7 | 秘密だけが違う 2 つの崩れた状態（2 枚目・7 枚目）で、例外の型・`code`・`str` が同じ（`problems` 以外に差がない） | 3 の盤面 2 つ |
| 8 | `str(error)` に問題の文・カードの番号が入らない | 3・4 |
| 9 | スナップショットとの整合: `save`→`restore` した状態を `from_state` が受け付ける。スナップショットが保存を拒否する崩れた状態は `from_state` も拒否する | PT-5e の `staged` |
| 10 | 規約集合・登録: テスト用の効果の登録・テスト専用のカードの組の盤面（`build_test_state(effects=…, pool=…)`）を、不変条件を満たせば受け付ける（スナップショットの境界より緩い） | 既存のテストの盤面 |
| 11 | 信頼された内部の組み立て（`ClientHub(A.HostedGame(state))`）は今のまま（崩れた状態の候補は `unverified`。PT-5e のガードが残る） | 3 の盤面 |

既存のモジュールの回帰（1 つずつ別のプロセス。合計 30 モジュール・20 分まで）:

- `from_state` を使うテスト 17 ファイル（`ClientHub.from_state` の 14・`ActionHost.from_state` の 3。2 章の表の呼び出し元。PT-5e のテストは 5 章の 2 件を意図して変える）
- `test_client_api`・`test_client_api_cn1_v0_173`・`test_state_snapshot_v0_157`・`test_snapshot_replay_v0_158`・`test_view_record_v0_155`・`test_replay_record_v0_153`
- 検証用 AI の `test_verification_ai_v3_3`・`_p6`・`_u_r3a`・`_v0176_follow`（`from_state` を使わない経路の回帰）
- 識別・配布: `test_distribution`・`test_preset_decks_v0_20`（版を上げる場合）

対象外: 全体のテスト・大量の対戦・seed の探索・GUI・E2E・lockstep・状態の監査。GUI の確かめは GUI の追従の別の作業。

## 7. 採用の判断が必要なこと

1. 推奨の案 B（2 つの `from_state` の共通の下位の関数で確かめる）を採るか
2. 例外の型: 新しい型（推奨。`ValueError` の下位、固定の文、`code`・`problems`）か、既存の `StateIntegrityError` を投げるか（後者は `str` に問題の文が入り、処理の途中の不整合と区別しにくい）
3. 入口で規約集合（`require_state_conventions`）・決定の再開先（`supported_decision_error`）も見るか（推奨: 今回は見ない。コマンドごとの既存の拒否のまま）
4. 版: `client_api.py`・`legal_actions.py` は振る舞いのファイルなので `behavior_digest` が変わる（`adapter.py` に共通の関数を置くなら `instrumentation_digest` も変わる）。版を 0.177.0 に上げ、0.176.0 の記録・スナップショットは新しい版で再実行・復元できない（既存の設計）ことを受け入れるか
5. 既存のエンジンのテストの盤面が拒否されたときの扱い（5 章の (a)・(b) の個別の判断）の進め方
6. GUI の追従（固定の更新・`engine-contract.md` の `from_state` の行の条件の追記）を別の作業にするか

## 8. 残る制限

- 入口で確かめても、合法な対戦から到達できることは保証しない（不変条件は到達可能性より弱い）
- 信頼された内部の組み立て・`ActionHost.game` の直接の変更・低層の API からは、崩れた状態がありうる（契約で呼び出し側の責任にする。PT-5e のガードと、コマンドの終わりの確かめで補う）
- `check_invariants` が見ない整合（乱数・効果の登録・構造・`pending_moves`）は入口でも見ない
- 既存のテストの盤面が受け付けられるかは、実装のときの回帰で初めて分かる（静的には決められない）

## 9. 実装の結果（v0.177.0。利用者が案 B を採用）

1〜8 章は監査のときの記録（版 0.176.0・基点 `7533fbb`）のままです。利用者が 4 章の案 B と、7 章の 1〜3（新しい例外の型・入口で規約集合と決定の再開先は見ない）を採用し、v0.177.0 で実装しました。

### 9.1 共通の確かめと拒否の時期

- 共通の関数 `adapter.checked_state_copy(state)` を 1 つ加え、`ClientHub.from_state`・`ActionHost.from_state` の両方がそれだけを呼ぶ（確かめを重ねて書いていない）
  1. 型: `type(state) is GameState`（子のクラスは受け付けない）。違えば `TypeError`（使い方の誤り。複製しない）
  2. 複製（`state.clone()`）
  3. 複製を既存の `engine.check_invariants` で確かめる
  4. 問題があれば `UnusableStateError`。通った複製だけで `HostedGame` を作り、そのあとで `ActionHost`・`ClientHub`・セッション・取っ手を作る
- 置き場所は `adapter.py`（`HostedGame` のとなり）。`adapter` はもともと `engine` を import しているので、新しい依存・循環はない。`legal_actions`・`client_api` は `adapter` から import する
- 確かめるのは複製（ホストが持つもの）なので、確かめたあとに呼び出し側が渡した状態を変えても、ホストの対戦には影響しない
- 信頼された内部の組み立て（`HostedGame(state)`・`ActionHost(game)`・`ClientHub(game)`）は確かめない（変えていない）。期待する前提（`new_game`・`apply_command` が返した状態、`restore_snapshot` が復元した状態、`checked_state_copy` を通した状態）を docstring に書いた。崩れた状態をここへ直接渡すのは、低層の振る舞いを確かめる検証者・テストだけ（通常の使い方ではない）
- 無検査で通す公開の選択肢は加えていない。PT-5e の候補の側のガード・`apply_command` の実行のあとの確かめ・スナップショットの確かめは残した

### 9.2 例外の型・code・文・詳しい問題

| 場合 | 結果 |
|---|---|
| 型の違い（`GameState` でない・子のクラス） | `TypeError`（固定の文） |
| 複製の失敗（`clone` の `Exception`） | `UnusableStateError`・`code` `STATE_CHECK_ERROR`・`stage` `clone`・`problems` 空・元の例外は `__cause__` |
| `check_invariants` が問題を返した | `UnusableStateError`・`code` `STATE_INTEGRITY`・`stage` `check`・`problems` は問題の文のタプル |
| `check_invariants` の中の `Exception` | `UnusableStateError`・`code` `STATE_CHECK_ERROR`・`stage` `check`・`problems` 空・元の例外は `__cause__` |
| `MemoryError` | 投げ直す（変えない） |
| `KeyboardInterrupt`・`SystemExit` など（`Exception` の子でないもの） | 捕まえない（`except Exception` だけ） |

- `UnusableStateError` は `ValueError` の子で、`EngineError`・`StateIntegrityError`（処理の結果の不整合。`failed` の結果）とは別の型。公開の位置は `kyuura_engine.adapter.UnusableStateError`（`client_api`・`legal_actions` からも同じものを参照できる）
- `str()` は `code` ごとの固定の文だけ（問題の文・カードの番号などの値を入れない）。`problems` はホスト・検証者だけが読む（カードの番号・ゾーンが入り、秘密を含みうる）
- 入口を作る前に投げるので、プレイヤー向けの JSON の応答・公開の更新は存在しない。JSON の要求・応答のスキーマとエラーのコード表は変えていない
- 範囲: Python のオブジェクトを受け取るホスト向けの入口で、信頼できないデータの読み込み（デシリアライズ）ではない。任意の壊れたオブジェクト・悪意のある値に対して安全であるとは保証しない（外部の入力は `snapshot.restore_snapshot`）。不変条件を満たすことは、合法な対戦から到達できることではない。入口のあとにホストが状態を直接変えることは防がない

### 9.3 有効な状態と不整合な状態の結果

| 状態（作り方） | `ClientHub.from_state`・`ActionHost.from_state` |
|---|---|
| 準備中（`start_game` の new_game の状態） | 受け付ける。候補は `ClientHub.start` と同じ（取っ手を除く） |
| 番の途中（構築盤面）・決定待ち（パソコン通信のあと）・終局（ピカチュウの対戦 seed 0）・停止（準備の停止 seed 1・途中停止）・サドン・デス（構築）・テスト用の効果の登録の盤面 | 受け付ける。ホストは複製を持ち、渡した状態は変わらない。状態の知らせ（`status_of`）はそのまま |
| おもての山札の印が続かない・同じカードが 2 か所・持ち主でないゾーン・未知の番号 | 拒否（`STATE_INTEGRITY`。`problems` は `check_invariants` の結果と同じ）。渡した状態は変わらない |
| 秘密の位置だけが違う崩れた状態 2 つ（相手の山札の 2 枚目・7 枚目） | 2 つの入口・2 つの状態で、例外の型・`code`・`stage`・文が同じ |
| スナップショット | 保存・復元した状態は受け付ける。スナップショットが保存を断る崩れた状態は、入口も断る |
| 信頼された内部の組み立て `ClientHub(A.HostedGame(...))`（検証者専用） | 今のまま受け付ける。崩れた状態の候補は PT-5e のガードで `unverified` |

確かめるのは不変条件だけです。効果の登録・規約集合の正しさは確かめません（テスト用の効果の登録の盤面も、不変条件を満たせば受け付ける）。

### 9.4 テストの盤面の変更と根拠

- 既存の盤面で、新しい確かめに拒否されたものは**なかった**（`from_state` を使う 17 モジュールを含む回帰がすべて 1 回目で失敗 0）
- 意図した変更は PT-5e のテストの 2 件だけ（契約の変更）:
  - `test_from_state_accepts_a_broken_invariant_but_the_condition_is_not_evaluated` → `test_from_state_rejects_a_broken_invariant_and_the_condition_is_not_evaluated_internally`: 2 つの入口の拒否（同じ型・code・文）を確かめる形にした。崩れた状態の候補と送信の結果の比べは、信頼された内部の組み立て（`queries(..., internal=True)`）で残した（主張は同じ）
  - `test_broken_invariant_keeps_the_engine_rejection_private`: 包み方だけを `ClientHub(A.HostedGame(state.clone()))` に変えた（検証者専用。通常の使い方ではない）。主張は同じ

### 9.5 テスト

| 種類 | 結果 |
|---|---|
| 新しいモジュール `tests/test_from_state_integrity_v0_177.py` | 12 件 OK |
| PT-5e のモジュール（2 件を変えた） | 14 件 OK |
| 回帰（1 つずつ別のプロセス）: `from_state` を使う 16（PT-5e を除く。エンジン 14・AI のテスト 2）、`client_api_cn1`・`state_snapshot_v0_157`・`snapshot_replay_v0_158`・`view_record_v0_155`・`replay_record_v0_153`、AI の `v3_3`・`p6`・`u_r3a`・`v0176_follow`、版のあとの `preset_decks_v0_20`・`distribution` | すべて OK |
| 合計 | 29 モジュール、失敗 0、修正・再実行なし。版のコミットの前の 27 モジュールで約 4.5 分 |

全体のテスト・GUI・E2E・AI の実対戦・大量の対戦・seed の探索・lockstep・状態の監査はしていない。

### 9.6 版・識別・配布

- 版 0.177.0。識別方式は同じ（`kyuura-package-files-sha256/1`）。`client_api.py`・`legal_actions.py`（振る舞いのファイル）を変えたので `behavior_digest` が `337caa88…32ea` から `68ee4ab4949862c43f1eb403d7c2311f43aaa6b902f482c4dc318be5b5c84727` に、`adapter.py`（計測のファイル）を変えたので `instrumentation_digest` が `e7d36df3…3034` から `d34367481dd69bd72c715e1977feb93b3c19596a01f3b53a104eca2e7e06146d` に変わった
- 0.176.0 の完全な記録・スナップショットは、0.177.0 では再実行・復元できない（実装の識別が違う。既存の設計）。過去の証跡は旧い実装と対応づけたまま残す。旧いスナップショットの識別を書きかえて使わない
- 新しい実行時のファイルはない（配布するファイルは 62 で同じ。`pyproject.toml` の差は版だけで、新しい依存はない）。wheel の照らしは required=62・problems=0
- 配布用の固定コミット `01317a649e65461dfeffabfa0b4893840ae6d9ee` を、リポジトリの外の新しい venv に Git の URL から通常のインストールをして、スモークを 1 回した（終了コード 0）: `direct_url` のコミットが一致、editable でなく site-packages から読み込み、版と実装の識別がソースと一致、依存なし、パッケージのファイルは 62（`__pycache__` を除く）。new_game の状態を 2 つの入口が受け付け、テスト専用に変えた状態（重複・秘密の位置だけが違う印 2 つ）を 2 つの入口が同じ型・code・固定の文で拒否、型の違いは `TypeError`、渡した状態は変わらない

### 9.7 公開入口の契約と、残る低層の API の前提

| 入口 | v0.177 の契約 |
|---|---|
| `ClientHub.from_state`・`ActionHost.from_state` | 外から作った状態をプレイヤーの入口へつなぐ公開の入口。型・複製・不変条件を確かめ、通らなければ hub・セッション・取っ手を作らずに拒否 |
| `HostedGame(state)`・`ActionHost(game)`・`ClientHub(game)`・`ViewRecorder.attach` | 信頼された内部の組み立て（確かめない）。前提: `new_game`・`apply_command`・`restore_snapshot`・`checked_state_copy` を通った状態。崩れた状態を渡すのは検証者・テストだけ |
| `apply_command`・`adapter.submit`・`observe` | 低層。入力の状態の整合は呼び出し側の責任。返す状態は今までどおりコマンドの終わりに確かめる |
| `restore_snapshot`・`RestoredGame` | 外部の入力（ファイル）の境界。今までどおり（最も厳しい確かめ） |

### 9.8 GUI・検証用 AI への影響

- GUI（`dbb6456`。読み取りだけ）: 固定例・テスト専用盤面はどちらも不変条件を満たす状態だけを `ClientHub.from_state` に渡すので、拒否されない見込み（実際の GUI では確かめていない）。追従（固定のコミットを `01317a6` 以降に・契約の engine の値・版のテスト・`engine-contract.md` の `from_state` の行に受け付ける条件と `UnusableStateError` を書く・接続層が例外を画面に出すなら固定の文だけにする）は別の作業
- 検証用 AI: 実行のコードは `from_state` を使わない。テスト（`v0`・`v1`・`v3_3`・`p6`・`u_r3a`・`v0176_follow`）は失敗 0。AI のコードは変えていない。保存済みの証跡の版（0.176.0 以前）は変えていない

### 9.9 証跡と残る制限

- 証跡: `C:/dev/kyuura-engine-verification-vai/verifier/runs/pt5e-from-state-fix/`（採用の記録・実行の前の計画・例外の契約・コマンドと終了コード・テストの盤面の変更の理由・テストの出力・配布と導入の結果）と `public/runs/pt5e-from-state-fix/summary.json`。既存の 509 ファイルが変わっていないことを確かめてから、マニフェストを 556 ファイルに更新した（`sha256.json` の sha256 は `1341313a68b25342fee581082f68407639358b69498c4c5ef30f13727a8ae0ad`）
- 残る制限: 8 章のとおり（不変条件は到達可能性より弱い・信頼された内部の組み立てと低層の API からは崩れた状態がありうる・`check_invariants` が見ない整合は入口でも見ない）。加えて、入口のあとにホストが状態を直接変えることは防がない。規約集合・決定の再開先は入口で見ない（コマンドごとの既存の拒否のまま）。任意の壊れたオブジェクト・悪意のある値への安全は保証しない
