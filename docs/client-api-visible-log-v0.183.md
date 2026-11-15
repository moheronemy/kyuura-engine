# v0.183: client_api の可視ログの配信（読み取りの要求 `log`）

2026-11-14。[設計](client-api-visible-log-delivery-design.md)の案 B と推奨値（8 章の J1〜J7）を、エンジンの側で実装しました。

- 変更は `kyuura_engine/client_api.py` だけです（と版）。
- GUI の接続層・安全検査・表示（J8 と設計 9 章）は別の単位で、変えていません。
- 新しい裁定・ゲームの処理の変更はありません。
- 証跡: `kyuura-engine-verification-vai/verifier/runs/client-api-visible-log-v0183/`（事前計画 `PLAN.md`、作業の記録 `commands.txt`、スクリプト `scripts/`、出力 `out/`・`scripts/tests/`・`smoke/`）。

## 1. 基点と識別

| 項目 | 値 |
|---|---|
| 基点 | `claude/trader-log-delivery-design` の `dc26e64`（origin と一致・変更 0。`origin/main` は祖先、基点は main に入っていない。`95206ec..dc26e64` は文書だけ。版 0.182.0・`TOOL_VERSION` 10・判定の規則 8・形式 6） |
| 作業 | 新しい worktree `C:\dev\kyuura-engine-lt21`、ブランチ `claude/client-api-visible-log-v0183` |
| コミット | `8e425dc`（実装と回帰テスト）、`0529041`（版を 0.183.0 にする。配布の確かめの固定コミット `05290415377738143c5ec2fa7f5cf092e9e0e5ae`） |

**識別の前後**（`scripts/identity.py` → `out/identity_before.json`・`identity_after.json`。実測）

| 項目 | 前（0.182.0） | 後（0.183.0） |
|---|---|---|
| behavior_digest | `aa90734a…` | `fc76af65…`（変わる。`client_api.py` は behavior のファイル） |
| instrumentation_digest | `d3436748…` | 同じ |
| P1 の basis | `a83547d8…` | 同じ（対象のファイルに `client_api.py` がない） |
| P3 の basis | `0a8f7530…` | 同じ |
| `TOOL_VERSION`・道具の識別 | 10・`7b56ed5a…` | 同じ |
| 判定の規則・計画と完了の形式 | 8・6 | 同じ |

- judge・runner・batch・方策は変えていません。
- 検証用 AI の計画の識別は版と behavior をふくむので、0.183.0 では新しい計画で実行します（旧計画の移行・再開・識別の書き換えはしない）。

## 2. 要求 `log` の仕様

**入口**: プレイヤー（本人の写し）・観戦者（観戦者の写し）・ホスト（観戦者の写し）。

**要求**: `{"contract": "kyuura-client-api", "format": 1, "type": "log"}`。任意で `"from": {"segment": 整数, "index": 整数}` を付けます。

**位置の意味**: `(segment, index)` は「その区間のログの番号 `index` の出来事の前」です。`index` は 0 からその区間の長さまでの値をとります。

| 項目 | 定義 |
|---|---|
| 初期の取得 | `from` を省くと `(0, 0)` から読む |
| 正規化 | `index` がその区間の長さと等しく、後ろに区間があるときは `(segment + 1, 0)` と同じ位置 |
| `entries` | `from` から古い順に最大 `MAX_LOG_ENTRIES`（256）。各項目は `{"segment", "log_index", "event"}`（閲覧用記録の出来事と同じ形） |
| `next` | 最後に返した出来事の次の位置（正規化した値）。`entries` が空なら `from`（正規化した値） |
| `end` | 応答の時点の末尾（今の区間と、そのログの長さ）。処理できない結果のあとは、最後の受理の位置 |
| `complete` | `next == end` |
| `baseline_end` | hub を作ったときの末尾。位置が `baseline_end` より前の出来事は作った時点の投影、`baseline_end` 以降は受理の時点の写し。hub を作ったあとは変わらない |
| 誤り | 区間がない・`index` がその区間の長さより大きい: `CLIENT_LOG_POSITION_UNKNOWN`（「ログの位置がこの対戦の範囲にない」）。`from` が辞書でない・名前がちょうど `segment`・`index` でない・整数でない（真偽・小数・文字列）・負・2**31 以上: `CLIENT_FIELD_INVALID`。知らない項目: `CLIENT_FIELD_UNKNOWN`。どれも状態・写し・更新の箱を変えない |

例（ポケモン交換おじさんで手札のカードを山札にもどした直後に、前に受け取った位置から読む）:

```json
{"contract": "kyuura-client-api", "format": 1, "type": "log", "from": {"segment": 0, "index": 300}}
```

```json
{"contract": "kyuura-client-api", "format": 1, "type": "log", "ok": true,
 "entries": [{"segment": 0, "log_index": 300, "event": {"kind": "play_trainer", "…": "…"}},
             {"segment": 0, "log_index": 301, "event": {"kind": "return_to_deck", "turn": 5, "player": 0, "card": 2, "card_id": "…"}}],
 "next": {"segment": 0, "index": 302}, "end": {"segment": 0, "index": 302}, "complete": true,
 "baseline_end": {"segment": 0, "index": 300}}
```

- 末尾の位置を送ると、`entries` は空で、`next == end`・`complete` は真です。
- 空のログ（構築盤面）では、`(0, 0)` が末尾です。
- 同じ位置から読み直すと、すでに返した位置の出来事は同じ値です。`end`・`complete`・1 回の件数は応答の時点で変わります（その間の受理で増える）。応答の全体が永久に同じとは限りません。
- 取得の途中で受理があっても、持っている `next` から読めば欠けも重なりもありません。
- 区間の変化（サドン・デスの延長戦）: 区間の終わりの位置と次の区間の `(n, 0)` は同じ応答になり、`entries` は区間をまたいで続きます。
- 保持の上限はありません（古い位置の誤りもない）。
- 別の対戦の位置は、その対戦の範囲にあるとは限りません（範囲外なら `CLIENT_LOG_POSITION_UNKNOWN`）。受け取る側は、対戦・閲覧者ごとに位置を分けて持ちます。
- 位置の値（各区間の長さ）は、閲覧者によらず同じです（`visible_event` は出来事を除かない）。中身は閲覧者ごとの写しです。
- `log` は状態を読みません。処理できない結果（`failed`）のあとも、それまでに固定した写しを返します（`view` などは `CLIENT_GAME_UNAVAILABLE`）。
- 既存の要求・応答（`view`・`updates`・`candidates`・`inputs`・`check`・`submit`）・公開の更新・`number`・形式の版 1 は同じです。`log` を使わない旧クライアントは今までどおり動きます。

## 3. 固定の時点と主体別の可視性

- hub は、作るとき（`ClientHub.start`・`from_state`）に、閲覧者 0・1・観戦者ごとに今の状態の可視ログを写します。
  - 写しの出どころは `visible_segment_logs`（終わった区間）と `visible_log`（今の区間）です。
  - これが baseline で、作った時点の投影です。元の出来事の時点の公開は保証しません。
  - 例: マチスの秘策のうらのカードが作る前におもてになっていれば、その前の出来事でも uid が見えます。
- 受理のたびに、増えた出来事だけを、その時点の `visible_log` から写して足します。区間が変わったら、前の区間の残りを `visible_segment_logs` から写します。
  - 写しは JSON の値の写しで、前に足した写しは変えません。
  - 後でおもてになった・うらになったカードでも、前の写しは受理の時点の値のままです（`ViewRecorder` と同じ。テストで一致を確かめた）。
- 拒否では写しを足しません（拒否はログを変えない）。本人の拒否の診断は `submit` の応答だけにあり、`log` にも他人にも出ません。
- 処理できない結果では足しません。
- 返す値は、その入口の閲覧者の写しだけです。完全な記録・内部の状態・カードの対応表・`verifier` は返しません。
- 応答は写しの JSON の写しなので、呼び出し側が応答を変えても、hub の写しは変わりません。
- ポケモン交換おじさん: `return_to_deck`・`reveal_from_deck` の `card_id`（v0.182）は、出来事を書いた受理の時点で、使用者・相手・観戦者・ホストの `log` から取れます。それより前の位置にはありません。
- パソコン通信: `search_deck` は、相手・観戦者・ホストには `hidden: {"card": null}` のままです（使用者には `card`）。
- 旧形式: `card_id` のない出来事（0.181.0 以前の記録・ほかの 18 の呼ぶ箇所・引数なしの生成）は、そのまま返し、後の状態から補いません。
- `log` の読み取りは、状態・乱数・ログ・決定・更新の箱・取っ手を変えません。読むために `candidates`・`inputs`・`check` を呼ぶ必要もありません。

## 4. テスト

**新しいテスト** `tests/test_client_api_visible_log_v0_183.py`（19）

- 盤面は既存の構築盤面と補助関数です。
  - `test_pokemon_trader_v0_24.board`・`test_computer_search_v0_22.board`
  - マチスの秘策の `test_secret_plan_v0_67.board`、［KEEP］の `test_keep_designated_energy_removal_v0_181.opponent_face_down`、`test_sudden_death_v0_134.constructed_sudden_death`
  - 人工の出来事の列（構築盤面のログに公開の `shuffle` を足す）
- どれも new_game からの対戦の実績には数えません。

| 種類 | 確かめること |
|---|---|
| 公開の範囲 | 交換おじさんのもどすカード・探したカードを、4 つの入口がその受理の時点で `card_id` とともに読める。使った直後・山札から選ぶ前には出ない。ホストは観戦者と同じ。位置からの差分 |
| 非公開 | パソコン通信の `search_deck` は相手・観戦者・ホストに伏せたまま。使用者には `card` |
| 拒否 | ［KEEP］のエネルギー・リムーブの拒否で、どの入口の `log` も同じ。診断は送信の結果だけ。更新 0 |
| 固定 | マチスの秘策のうらのポケモンにつけたエネルギーの `target`: おもてにしたあとも、相手・観戦者の写しは伏せたまま（今の `visible_log` は見せる）。持ち主には見える。前に読んだ位置の値が同じ |
| 一致 | 同じ時点に始めた `ViewRecorder` の出来事と、3 閲覧者で位置・値が一致 |
| baseline | 同じ状態から後で作った hub では、作る前の位置が作った時点の投影（上の `target` が見える）。`baseline_end` の値 |
| 取得 | 256・257・600 件のページ（256 / 256+1 / 256+256+88）、`(0, 0)` からの初期の取得、同じ位置の再取得、取得の途中の追記（`end` が進む・既存の位置は同じ）、末尾の空の応答、空のログ |
| 誤り | 不正な型・名前・負数・真偽・小数・2**31 以上（`CLIENT_FIELD_INVALID`）、ない区間・末尾より先（`CLIENT_LOG_POSITION_UNKNOWN`）、知らない項目。どれも状態・更新を変えない |
| 区間 | サドン・デスの延長戦の開始で、区間をまたぐ位置・区間の境界の正規化・`view` の区間との一致 |
| 分離 | 別の対戦の位置は範囲外になりうる。閲覧者ごとに位置は同じで、引いたカードは本人の写しだけ |
| 不変 | 返した応答を変えても、次の応答は同じ |
| failed | 処理できない結果のあとも、それまでの写しを読める（`view` は `CLIENT_GAME_UNAVAILABLE`） |
| 非干渉 | `log` を何度も挟んでも、状態・乱数・ログ・決定の通し番号、候補・入力・check・submit・view の応答（取っ手を除く）、更新の箱の中身が同じ。`view`・`updates` の応答の形、観戦者の `candidates` の拒否、形式の版 1 |

**修正前のソース**（`dc26e64` の展開に新しいテストを写した）では、19 とも失敗しました（`out/new_test_on_prefix_dc26e64.txt`）。修正後は 19 とも成功しました。

**関連のテスト**（モジュールごとに別のプロセス。PowerShell・`MSYS=noglob`・UTF-8・`PYTHONDONTWRITEBYTECODE=1`。JUnit と終了コードは `scripts/tests/`）

- `related_impl`: 41 モジュール・697 テスト。すべて成功しました。
  - `client_api` を import するテスト 33 に、閲覧用記録・snapshot・交換おじさん・パソコン通信・盤面の出どころ（マチスの秘策・サドン・デス）・検証用 AI の v2_repeat を加えた範囲です。
  - 検証用 AI の行動・契約の指紋（v2_repeat の固定値）は変えずに成功しました（差なし）。
- `version_bump`: preset_decks_v0_20・distribution・新しいテストの 3 モジュール・46 テスト。すべて成功しました。
- 全体のテストは実行していません。
- 静的な確かめ: `add_event` の種類はすべて見える範囲の表にあります（設計の単位の `event_keys_scan.json` で文字列の 372 種類。この単位で、動的な 3 か所の 4 種類も表にあることを確かめた）。hub を作るとき・受理のたびに `visible_event` を呼ぶようになったので、表にない種類があると `ValueError` になります（`ViewRecorder` と同じ前提）。

## 5. 保持の量と測定（限定。`scripts/measure_log.py` → `out/measure_log.json`）

方法と前提:
- 新しい対戦はしていません。構築盤面のログに、人工の出来事（公開の `shuffle` と、本人だけの `cards` をもつ `draw` を交互）を、hub を作る前に足しました。
- 300 件と 2200 件（保存済みの記録の最大 2191 に近い）で測りました。
- JSON の量は `json.dumps` の UTF-8 のバイト数で、Python のオブジェクトの実メモリではありません。
- tracemalloc は Python の割り当ての差です。ワーキングセットはプロセス全体の参考値です。時間は、この端末の 1 回の値です。

| 項目 | 300 件 | 2200 件 |
|---|---|---|
| 保持した出来事（閲覧者ごと） | 300 | 2200 |
| 保持の JSON の量（本人 / 相手・観戦者） | 約 24 KB / 約 26 KB | 約 180 KB / 約 190 KB |
| hub を作る時間 | 0.031 秒 | 0.197 秒 |
| hub を作る tracemalloc の増分（3 閲覧者の写しと hub） | 約 0.75 MB | 約 5.6 MB |
| ワーキングセットの増分（参考） | 約 0.85 MB | 約 8.6 MB |
| 1 閲覧者の全体の読み取り | 2 ページ・約 26 KB・0.007 秒 | 9 ページ・約 192 KB・0.048 秒 |
| 50 回の全体の読み取り | 0.33 秒 | 2.42 秒 |
| 大きいログのあとの受理 1 回（番を終える） | 0.010 秒 | 0.037 秒 |

- 反復の取得で保持の量は増えませんでした（保持した出来事の数は同じ）。
- tracemalloc の current は、50 回で 約 4〜12 KB、100 回で 約 8〜18 KB 増えました。
  - 補助の診断（`scripts/diag_repeat_alloc.py` → `out/diag_repeat_alloc.txt`）では、増分はどれも入口の振り分けの行で割り当てられたものでした。50 回ごとに 400 → 180 → 77 → 12 → 9 → 8 個と減っていき、6 回目は 約 360 バイトでした。
  - 保持の写しではありません。インタープリタの内部のキャッシュなどの見込みですが、原因は確かめていません。
- 受理 1 回の手間は、ログの長さに比例して増えます（`visible_log` をログの全体について作るため）。今回は最適化（圧縮・保持の上限・差分だけの投影・並列化）はしていません。

## 6. 配布の確かめ（固定コミット `0529041`）

1. `git ls-tree` の `kyuura_engine` の数: 62（`95206ec` と同じ）。`pyproject.toml` の差は版の 1 行だけで、依存は増えていません。
2. `git archive 0529041` の展開から wheel を作りました。
   - `pip wheel --no-deps`: exit 0。`kyuura_engine-0.183.0-py3-none-any.whl`、sha256 `2871e2cb…`
   - `scripts/check_distribution.py --wheel`: exit 0（required=62・problems=0）
3. スモーク用のスナップショット: 同じ展開から、この版で新しく作りました。
   - 交換おじさんの盤面に人工の公開の出来事を足してログを 300 にしたもの
   - パソコン通信の盤面
   - 旧版のスナップショットは使っていません。
4. scratchpad の新しい venv に `pip install git+https://github.com/moheronemy/kyuura-engine.git@05290415…` で導入しました（exit 0。入ったのは kyuura-engine 0.183.0 と pip だけ）。
5. スモーク（`scripts/log_smoke_v0183.py`。tests を使わない）の結果:
   - 導入物: site-packages から読み込み、direct_url は vcs の commit `0529041…` で editable ではない、`requires` なし・62 ファイル・識別はソースと一致
   - 交換おじさん: 4 つの入口とも 256 + 49 の 2 ページで、2 つの出来事が正しい `card_id` とともに baseline のあとの位置にある
   - パソコン通信: 相手・観戦者・ホストには伏せたまま。使用者には `card`
   - 位置は連続していた。ソースの木での実行と導入物での実行で、結果（`result_sha256` `634b32bd…`）が同じ

## 7. 旧記録との関係

- 状態・snapshot の構造は変えていません。hub の写しは状態に入りません。
- 復元した状態から作った hub の、作る前の履歴の限界は `baseline_end` で表します。
- 旧記録・閲覧用記録・snapshot・検証用 AI の計画は、それを作った版の実装に結び付いたままです。移行・再開・識別の書き換えはしていません。
- 0.182.0 以前の記録の出来事に `card_id` がなければ、識別の情報はありません。

## 8. GUI への引き継ぎ（別の単位。今回は変えていない）

- 最新の公開の GUI の基点を確かめ直してから実装します。設計の時点は `origin/feature/gui-energy-holder-label` の `2674efd` でした。
- エンジンの依存を `0529041` 以降の固定コミットにします。
- 画面の側に必要なこと:
  - `log` の取得と位置の管理（対戦・閲覧者ごとに `next` を持つ）
  - 位置による重なりの排除
  - 遅い応答の破棄（世代の番号）
  - `CLIENT_LOG_POSITION_UNKNOWN` のときの始め直し
- 接続層の安全検査（`safety.py`）の例外:
  - 閲覧用記録の検査と同じ、検証した `hidden` の構造だけに限ります。対象は可視ログの出来事の `hidden` の辞書で、値が null か真偽でない整数だけです。
  - その中の名前（`game_created` の `seed` など）だけを許します。任意の場所の `seed` などの禁じた名前は、今までどおり許しません。
- 交換おじさんの表示:
  - `card_id` があるときだけカードの表（catalog）で名前を引きます。
  - 表にないときは「カード定義にないカード（ID）」、`card_id` がなければ「見せたカード（識別の情報なし）」とします。
  - 観測・ほかの出来事・uid から補いません。
  - 送信の門・check・候補に結び付けず、相手の手札・山札の推測にも使いません。

## 9. 未確認・失敗・修正・再実行

- 未確認:
  - new_game からの対戦での `log`（構築盤面と人工の列だけ）
  - 1 回の受理で 2 つ以上の区間が始まる場合（手順はあるが、盤面がない）
  - GUI の追従
  - ほかの 18 の呼ぶ箇所と w1 の残り 57 件の監査
  - uid の方式全体の安全性
  - 反復の取得の小さい割り当ての原因
  - 全体のテスト
- 失敗・修正・再実行:
  - 新しいテストの初版:
    - `ActionResult` に `diagnosis` がない誤り（`view.diagnostic_id` に直した）
    - 文書の有無を確かめるテストが実装のコミットで文書より先になる（そのテストを外し、文書の確かめは既存の文書のテストと README の参照にまかせた）
    - 取得の途中の追記のテストで、hub の中の状態にじかに出来事を足していた（新しい盤面から作るように直した）
    - 意味のない `run` の上書きを外した
    - どれも実装を変えていない
  - 資源の測定の 1 回目は、ワーキングセットが取れなかった（`GetCurrentProcess` の戻りの型を決めず、疑似ハンドルが切り詰められた）。型を決めた 2 回目で取れた。1 回目の出力とスクリプトは `out/attempt1_*` に残した
  - 実装のパッチを Bash のヒアドキュメントで当てようとして、シェルの構文の誤りで止まった（何も書かれていない）。scratchpad のスクリプトで当てた
