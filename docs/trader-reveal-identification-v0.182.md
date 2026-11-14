# v0.182: ポケモン交換おじさんの「相手に見せるカード」の識別（案 A の実装）

2026-11-14。[設計](trader-reveal-identification-design.md) 6 章の案 A を実装しました。エンジンの出来事と閲覧用記録の修正だけです。client_api のログの配信・GUI の表示・新しい対戦のバッチはしていません。新しい裁定は入れていません。

- 仕様: [pokemon-trader-v0.24.md](pokemon-trader-v0.24.md) の PT6（もどすカードを相手に見せる）・PT13（探したカードを相手に見せる）。p.259 の最新の説明。
- 発端: [w1 の公開の識別の確認](verification-ai-w1-publication-audit.md) 4 章（相手・観戦者が、もどしたカードを識別できない）。
- 証跡: `kyuura-engine-verification-vai/verifier/runs/trader-reveal-identification-v0182/`（事前計画 `PLAN.md`、作業の記録 `commands.txt`、スクリプト `scripts/`、出力 `out/`・`scripts/tests/`・`smoke/`）。

**状態の区別**

| 範囲 | 状態 |
|---|---|
| エンジンの出来事（`return_to_deck`・`reveal_from_deck`）と閲覧用記録 | 修正済み（この版） |
| client_api（形式 1）の公開の更新でのログの配信 | 未実装（設計の 7 章の段階 2。形式 1 の更新は status と observation だけ） |
| GUI の表示 | 未実装（段階 3。段階 2 のあと） |
| ほかの 18 の呼ぶ箇所（3 章） | 未確認（変えていない。出来事の形は今までどおり） |
| w1 の残り 6 分類・57 件 | 未調査（監査の文書 3 章） |

## 1. 基点と識別

| 項目 | 値 |
|---|---|
| 基点 | `claude/trader-reveal-identification-design` の `eea56c0`（origin と一致・変更 0。`origin/main` は祖先で、基点は main に入っていない。版は 0.181.0） |
| 作業 | 新しい worktree `C:\dev\kyuura-engine-lt18`、ブランチ `claude/trader-reveal-identification-v0182` |
| コミット | `c894afb`（実装と回帰テスト）、`95206ec`（版を 0.182.0 にする。配布の確かめの固定コミット） |
| 保護 | 利用者の main・lt5（追跡していないテストのファイルをふくむ）・既存の worktree は触っていない |

**識別の前後**（`scripts/identity.py` → `out/identity_before.json`・`identity_after.json`）

| 項目 | 前（0.181.0） | 後（0.182.0） |
|---|---|---|
| behavior_digest | `5e0cb4ac…` | `aa90734a…`（変わる） |
| instrumentation_digest | `d3436748…` | 同じ |
| P1 の basis | `d1729754…` | `a83547d8…`（変わる。`effects.py`・`zones.py` をふくむ） |
| P3 の basis | `bb6d1730…` | `0a8f7530…`（変わる。同上） |
| `TOOL_VERSION`・道具の識別 | 10・`7b56ed5a…` | 同じ |
| 判定の規則・計画と完了の形式 | 8・6 | 同じ |

- 検証用 AI の basis が変わるので、0.181.0 の計画・記録は 0.182.0 ではそのまま当て直せません（既存の設計）。次のバッチは新しい計画で実行します。

## 2. 変更

1. `zones.return_hand_to_deck`・`zones.reveal_deck_to_hand` に、キーワードだけの引数 `identify: bool = False` を足しました。
   - 真のときだけ、出来事に `card_id`（その時点の `state.cards[card].card_id`）を書きます。
   - `card`（uid）・ほかの項目・出来事の順は変えていません。
2. `effects.TradePokemonWithDeck` の 2 つの呼ぶ箇所（もどす・手札に加える）だけが `identify=True` を渡します。
   - `engine.py`・`resolution/` にカード ID による分岐を加えていません（既存の `test_no_card_specific_branch_in_the_engine` が成功）。
3. 変えていないもの:
   - 配信（`PUBLIC_EVENTS`・`PRIVATE_FIELDS`・`_mask_face_down`）
   - 観測・閲覧用記録の形式
   - 状態・snapshot の形式
   - 乱数の消費・決定・候補・入力・受理の判定
4. 古い出来事: `card_id` のない `return_to_deck`・`reveal_from_deck`（0.181.0 以前の記録と、ほかの効果の出来事）は、そのまま読み込めます。補う処理はありません（設計の 6 章の 4）。

## 3. 呼ぶ箇所の数の訂正

設計の 6 章では「ほかの 8 の呼ぶ箇所」と書きましたが、実際は 18 でした。設計の時点で `effects.py` の一部だけを数えていました。

| ファイル | 呼ぶ箇所 | うち `identify=True` |
|---|---|---|
| `kyuura_engine/effects.py` | 14 | 2（`TradePokemonWithDeck`） |
| `kyuura_engine/resolution/programs.py` | 6 | 0 |

- 設計で数えていなかったのは次の 10 です。
  - `effects.py` の 4: `LookTopTakeTrainerThenShuffleLock`・`EachPlayerSearchToolOnEntry`・`BreederCoupleSearch`・`SearchDeckWithBenchLettersToHand`
  - `programs.py` の 6: ワザの要素
- どれも既定（`identify` なし）のままで、出来事の形は変わりません（4 章の比較のテスト）。
- 案 A の選択・推奨は変わりません。新しいテストの `test_only_trader_passes_identify` が、パッケージ全体でこの数と `identify=True` の位置を固定しています。

## 4. テスト

**新しいテスト** `tests/test_trader_reveal_identification_v0_182.py`（15）。盤面は既存の `tests/test_pokemon_trader_v0_24.board`・`tests/test_computer_search_v0_22.board`（構築盤面）で、`ClientHub.from_state` の正規の入口（候補 → 入力 → 送信）と `ViewRecorder.attach` を使います。

| 種類 | 確かめること |
|---|---|
| 正 | `return_to_deck`・`reveal_from_deck` に、そのカードの `card_id`。出来事の種類と順は同じ |
| 正 | 使用者・相手・観戦者の 3 閲覧者が、見せた時点（受理の更新と閲覧用記録）で識別できる |
| 負 | 使う前・もどすカードを選ぶ前・山札から選ぶ前には、uid・`card_id` を出さない |
| 負 | 手札・山札のほかのカードを、相手・観戦者に出さない |
| 正・負 | 同じカード ID の別の 1 枚（もどすカードと同じカードが山札にある）を取り違えない。選ぶ前に山札の 1 枚を出さない |
| 一致・不変 | 閲覧用記録の出来事が `visible_log` と同じ。後の受理（番を終える）のあとで、前の項目が変わらない |
| 対照 | パソコン通信の `search_deck` は相手・観戦者に `hidden` のままで、`card_id` を出さない。トラッシュの公開は今までどおり |
| 既定 | `identify` はキーワードだけで、既定は偽。引数なしで呼ぶと今までの形 |
| 範囲 | パッケージで `identify=True` を渡すのは交換おじさんの 2 か所だけ（3 章） |
| 旧形式 | `card_id` のない出来事をふくむ閲覧用記録も読み込め、検査の結果が同じ |

- 修正前のソース（`eea56c0` の展開に新しいテストを写した）: 15 のうち 7 が失敗しました（`card_id` がない 5、`identify` がない 2）。残りの 8（負・対照・旧形式）は成功しました（`out/new_test_on_prefix_eea56c0.txt`）。
- 修正後: 15 とも成功しました。

**既存のテストの期待の更新**（`tests/test_pokemon_trader_v0_24.py`。判定の中身は変えていない）

- `test_returned_card_goes_to_the_deck_and_is_shown`・`test_shown_cards_and_hidden_deck` の出来事の期待に `card_id` を加えました。
- v0.24〜v0.181 の期待（`card_id` なし）は docstring に残しました。
- 版の期待: `tests/test_preset_decks_v0_20.py`（0.182.0 と来歴）。

**関連のテスト**（モジュールごとに別のプロセス。JUnit と終了コードは `scripts/tests/`）

- `related_impl`: 22 モジュール・597 テスト。21 が成功しました。
  - `test_flash_faceup_deck_v0_126` だけが 4 errors でした。原因は worktree の中で過去のコミットを読む `git show` が、Bash からの実行で失敗したことです（既知の環境の問題。今回の変更とは関係しない）。
  - PowerShell（`MSYS=noglob`）からこのモジュールだけを再実行し、38 とも成功しました（`related_impl_git_powershell`）。
- `version_bump`: preset_decks_v0_20・distribution・新しいテストの 3 モジュール・42 テスト。すべて成功しました。
- 関連の範囲:
  - 交換おじさん・パソコン通信
  - 出来事をふくむトレーナーのテスト
  - 観測・閲覧用記録・完全な記録・snapshot
  - 検証用 AI の観測と v2_repeat（指紋の固定値は変えずに成功）
  - 配布
- 全体のテストは実行していません。

## 5. 前後の比較（`scripts/dump_run.py`・`compare_runs.py`）

修正前（lt17 = `eea56c0`）と修正後（lt18）の同じ構築盤面を別のプロセスで実行しました。各段について、次の値を比べました。

- 候補・入力・検査・受理
- 状態のゾーン・ログ
- 3 閲覧者の `visible_log`・観測・公開の更新
- 乱数の指紋・閲覧用記録

盤面は、交換おじさん（番を終えるまで）・同じカード ID の 1 枚がある盤面・パソコン通信の 3 つです。

- 取っ手（`game`・`revision`）は `secrets` の乱数なので、同じ版の 2 回でも違います（`legal_actions.py` の冒頭）。比べる前に置きかえました（40 か所）。
- 意図した差（2 つの出来事の `card_id`）を取り除いた残りの差は、3 つの盤面とも 0 でした。
  - 加わった `card_id` は、どれもその uid のカードの値でした（誤り 0。uid と `card_id` の組は盤面ごとに 2）。
  - 乱数の指紋・受理・不変条件の問題 0 は前後で同じでした。
  - 公開の更新・観測には差がありません（形式 1 はログを配らないので、`card_id` は更新に出ない。段階 2 の前提）。
- パソコン通信の対照は、閲覧用記録の指紋まで前後で同じでした。
- 修正後のソースを 2 回実行した結果は、閲覧用記録の指紋まで同じでした（`out/compare_after_repeat.json`）。

## 6. 配布の確かめ（固定コミット `95206ec`）

1. `git ls-tree` の `kyuura_engine` の数: 62（`a2b29e9` と同じ）。
2. `git archive 95206ec` の展開から wheel を作りました。
   - `pip wheel --no-deps`: exit 0。`kyuura_engine-0.182.0-py3-none-any.whl`、sha256 `6207dfb1…`
   - `scripts/check_distribution.py --wheel`: exit 0（required=62・problems=0）
3. スモーク用のスナップショット: 同じ展開から、この版で新しく作りました（交換おじさん 2・パソコン通信 1。古い版のスナップショットは使わない）。
4. scratchpad の新しい venv に `pip install git+https://github.com/moheronemy/kyuura-engine.git@95206ec…` で導入しました（exit 0。入ったのは kyuura-engine 0.182.0 と pip だけ）。
5. スモーク（リポジトリの外の作業フォルダ）の結果:
   - 導入先は site-packages。direct_url は vcs の commit `95206ec…` で、editable ではない
   - `requires` なし・62 ファイル・識別はソースと一致
   - 交換おじさん: 2 つの盤面とも、3 閲覧者の閲覧用記録の 2 つの出来事に正しい `card_id`
   - パソコン通信: 相手・観戦者には `hidden` のままで `card_id` なし。使用者には選んだカード
   - 受理・検査は 9 段ともに成功し、不変条件の問題は 0
   - 1 回目は exit 1 でした。スクリプトの誤りで、閲覧用記録（JSON の写し）と `visible_log`（タプル）を型ごと比べていました（パソコン通信のトラッシュの `cards`）。JSON の形にして比べるよう直した 2 回目は exit 0 でした。1 回目の出力とスクリプトは `out/install_smoke_attempt1_*` に残しています。

## 7. 引き継ぎ

- **client_api のログの配信（段階 2）**: 公開の更新にその受理の `visible_log` の写しを足すかどうかと、情報の約束・形式の版は別の設計の単位です。この版の `card_id` は、その単位があって初めて GUI に届きます。
- **GUI の追従（段階 3）**: 設計の時点で読んだ GUI は `C:\dev\kyuura-engine-gui` の main `434d1fa` です。GUI のログの配信・表示の設計では、434d1fa ではなく、報告されている `2674efd` 以降の実際に公開された基点を確かめてから始めます。
- **ほかの 18 の呼ぶ箇所**: 文面と公開の範囲を別の単位で確かめてから判断します（無条件に広げない）。
- **w1 の残り 57 件**: 監査の文書 3 章の方法で、別の単位で確かめます。

## 8. 未確認・失敗・修正

- 未確認:
  - new_game からの到達（構築盤面だけ）
  - GUI・client_api の配信
  - 全体のテスト
  - 保存済みのバッチへの judge・replay の当て直し
  - 18 の呼ぶ箇所の文面
  - w1 の残り 57 件
- 失敗・修正・再実行:
  - 新しいテストの初版は呼ぶ箇所を `effects.py` の 10 と仮定していたので、実際の 14（と `programs.py` の 6）で失敗しました。パッケージ全体を数えるテストに直しました（3 章）。
  - テストのファイルの編集で、シェルのエスケープによる誤り（改行・`\b`）が 2 回起き、Edit とスクリプトで直しました（実行前に構文の誤りで止まった）。
  - 比較のスクリプトは 3 回直しました（いずれも比較の側の誤り。実装は同じ）。
    - ログの出来事が repr の文字列になっていた
    - 取っ手を置きかえていなかった
    - 前の側の置きかえの結果を使っていなかった
  - スモークのスクリプトは 1 回直しました（6 章）。
  - `test_preset_decks_v0_20` が `-B` なしの子プロセスを起動するので、lt18 に追跡の対象外の `__pycache__`（34 ファイル）ができました。コミット・配布の確かめ（展開と wheel）には入っていません。それ以降の実行では `PYTHONDONTWRITEBYTECODE=1` を設定しました。
