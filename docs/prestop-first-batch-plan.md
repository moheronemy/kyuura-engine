# 未裁定の候補の inputs の記録: 初回の小規模確認バッチの計画（設計だけ）

2026-11-15。調査・設計・文書化だけです。実装・テスト・対戦・seed の探索・judge・replay・確定計画やキャッシュの作成・外側のスクリプトの変更と実行はしていません。`kyuura_engine`・`tools.verification_ai` は import していません。

- 基点: `claude/prestop-record-impl` の `5188f68`（実装 `fa992b3`。origin と一致・変更 0。main `b1e4430` の子孫で main に入っていない。新しい公開の変更はない）。作業は worktree `C:\dev\kyuura-engine-lt32`・ブランチ `claude/prestop-first-batch-design`。
- 仕様: [記録の追加の設計と実装](prestop-record-design.md) 11 章（エンジン 0.185.0・`TOOL_VERSION` 11・判定の規則 8・計画と完了の形式 7）。
- 機械可読の下書き: [prestop-first-batch-plan.json](prestop-first-batch-plan.json)（`status: draft`。確定計画ではない）。
- 証跡: `kyuura-engine-verification-vai/verifier/runs/prestop-first-batch-design/`（事前計画・選定の集計 `out/select_conditions.json`・外側の手順の確かめ）。

## 0. 推奨案（要約）

| 項目 | 値 |
|---|---|
| 計画 | 1 つ: `vai-batch-x1` |
| デッキ（両側） | 明示リスト L67-U（ファイル `vai-batch-d/decklists/decklist-L67-U.json`。sha256 `097b7db9621cc28e…`・content_sha256 `72690ceea389…`。t1・u1 と同じ） |
| 方式 | `rules-v2`・`boundary` |
| 規約集合 | 既定（`CS-KYUURA-CURRENT@1`） |
| seed と並び | 6001（回帰の条件）→ 9001（新しい）。seed ごとに rules-v2 → boundary |
| 局 | 4（g001 rules-v2・6001、g002 boundary・6001、g003 rules-v2・9001、g004 boundary・9001） |
| 単局の上限 | 既定（`runner.Limits`: 操作 2000・受理 1000・番 200・120 秒） |
| バッチの上限 | `--max-games 4`・`--budget-seconds 300`・`--evidence-max-mb 512`（次の局を始める条件の 150 秒・64 MiB は既定） |
| 記録 | `--observation`・`--prestop-inputs`（上限は既定の 256 要求・16,384 バイト・1 MiB） |
| 停止方針 | 既定（`--undetermined-evidence-missing continue` は t1・u1 と同じ） |
| 変異 | なし。単一のプロセス・逐次 |

- 6 局を埋めることを目標にしていません。照合に必要な最小として、回帰の条件の 2 局（2 種類の未裁定が出た記録がある）と、新しい seed の 2 局（出現を保証しない対照）にしました。
- 有効・無効を比べる対戦は入れません。非干渉は既存の固定テスト（11.4 節）で確かめた範囲として、この計画の結果とは分けます。

## 1. 対象条件の根拠と出現の限界

保存済みの 16 バッチ・272 局を、条件（デッキの組・方式・規約集合）ごとに数えました（`select_conditions.py`。候補全体が `unresolved_ruling` の候補の延べと、(主体, position) の局面）。

| 条件 | 局 | play_trainer が出た局（局面） | discard_from_play が出た局（局面） | 最長の局 | 最大の量 |
|---|---|---|---|---|---|
| L67-U どうし・rules-v2（d1・t1・u1） | 8 | 4（63） | 6（15） | 4.5 秒 | 13.1 MB |
| L67-U どうし・boundary（d1・t1・u1） | 8 | 7（99） | 5（16） | 7.3 秒 | 19.9 MB |
| L67-URC どうし・rules-v2・boundary（s1。観測なし）、reach 系の方式（r1・r2・s2・t2） | 計 58 | 出る | 出る | 最長 41.9 秒（reach 系） | 最大 90.7 MB（reach 系） |
| 固定デッキ（hitmonchan-dewgong 系・v2）・各方式 | 計 192 | 多い | 0 | 19.2 秒 | 45.0 MB |
| LUCKY_DECK 対 CONNECT_DECK（d2） | 6 | 0 | 0 | — | — |

- L67-U どうしの rules-v2・boundary は、観測ありの 0.181.0（t1・u1）をふくむ既存の条件で、play_trainer と discard_from_play の両方が出ました。局が短く、証跡も小さい条件です。固定デッキの条件では discard_from_play が出ません。L67-URC は観測なしの記録だけか、reach 系の長い局です。
- **回帰の条件**: seed 6001 は t1 の結果を見て選びました。t1 では rules-v2 の局で play_trainer 局面 24・discard_from_play 4、boundary の局で 25・1 でした。ただし t1 は 0.181.0 の記録で、今は 0.185.0（`effects.py` の識別の変更）です。同じ seed でも同じ進行・同じ出現になるとは限りません。
- **新しい seed**: 9001 は、保存済みのすべての `plan.json`・`header.json`（329 ファイル）にない値です（9001〜9100 は未使用、最大の既存値は 8003）。対戦で選んでいません。
- use_stadium（段なしの対照）は入れません。出た条件は LUCKY_DECK の d2 だけで（0.179.0・5 局・10 局面）、別の計画になり、予備の 150 秒が増えます。段なしの扱いは単体テストで確かめた範囲とします。
- 3 種類の出現を必須にしません。出なかった種類は「未出現」と記録します。
- 停止コードは記録用の inputs からも分からないので、コード別の集計は目的にしません。保存済みの記録のカード不明を、この計画の結果で埋めません。

## 2. 実行の手順と現行の道具の適合

| 項目 | 状況 | 実行のときに要ること |
|---|---|---|
| 計画・完了の形式 7・`TOOL_VERSION` 11 | 道具が自分で書く・照らす | なし |
| `--prestop-inputs`／`--no-prestop-inputs` | 計画の CLI で必須（どちらか） | `--prestop-inputs` を付ける |
| `--observation`／`--no-observation` | 必須（今までどおり） | `--observation` |
| `run --stop-after-games 1` | 変わらない | なし |
| 必須ファイル・集計の項目 | 有効な計画では `prestop/` の 2 つが必須。集計に `prestop`・`game_complete_prestop` | なし |
| 外側の逐次の実行（`vai-batch-w-run/scripts/run_seq_pyc_u.py`） | 既存の CLI を 1 局ずつ呼ぶだけ。計画の中身を読まず、`limits.evidence_max_bytes`・`max_games` だけを読む。量は計画のディレクトリの全ファイル（prestop をふくむ）。続ける条件は「1 局が complete で停止の理由なし」（`capped` は note なので続く。`failed` は停止の理由なので止まる） | **そのまま使える**。git の実体のパス（`c:/devkitPro/msys2/usr/bin/git.exe`）はこの環境の値で、存在を確かめた |
| キャッシュの準備（`prepare_pyc_cache.py`） | `tools/verification_ai/*.py` を glob で集めるので、新しい `prestop.py` もコンパイルされる。準備の記録（Python・worktree・コミット・未コミット・キャッシュの場所）の照合は同じ | **最小の修正を推奨**: 読み込みの確かめの入口 `ENTRY_MODULES` に `tools.verification_ai.prestop` を足す（batch は prestop を関数の中で遅れて読み込むので、今の一覧では事前の確かめで読み込まれない。足さなくても実行はできる） |
| 事後の集計（`analyze_batch.py` など） | 項目を読むだけで、prestop の 2 ファイルは「観測以外」の量に入る | 照合とカード別の内訳は、新しい読み取りだけのスクリプト `analyze_prestop.py` で行う（4・6 章。既存のスクリプトは直さない） |
| 時間・容量・停止方針 | 追加の取得の時間は単局とバッチの時計の中。停止方針に `on_prestop_problem` | なし |

**実行の手順**（次の単位。ここでは実行しない）:

1. 新しい worktree と作業ブランチ（この計画のコミットから）。`tools/`・`kyuura_engine/` が `fa992b3` と差 0 で、識別（エンジン 0.185.0・behavior `a3b65dbe…`・道具 11・`6e0616cc…`・規則 8・P1 `06ec1daf…`・P3 `6a8287f9…`）が同じことを確かめる。実行コミット＝その worktree の HEAD
2. `batch decklist --file <L67-U のファイル>` で 60 枚・problems 空・content と展開の sha256 を確かめる
3. `batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-x1 --engine-commit <HEAD> --tool-commit <HEAD> --seeds 6001 9001 --modes rules-v2 boundary --decklist0 <L67-U> --decklist1 <L67-U> --max-games 4 --budget-seconds 300 --evidence-max-mb 512 --observation --prestop-inputs --undetermined-evidence-missing continue`
4. 計画の照合: `plan.json` の `prestop_inputs`（`enabled` 真・形式・版 1・上限 3 つ）と `observation`、局の並び・デッキの記録（`deck_problems` 空）・識別が下書きと同じこと、`plan.sha256` を記録
5. S-1: 新しいキャッシュ `C:\dev\kyuura-engine-pyc-cache\ba3b65db-t6e0616c-cpython-314-<HEAD 7 桁>-x1`（新しい空の場所）を、その worktree・同じ Python（前回は 3.14.6）で準備。準備の時間・容量はバッチ本体と分ける
6. `run_seq_pyc_u.py --dry-run` で `use_cache` 真・容量の確認・`batch run` を呼ばないことを確かめる
7. キャッシュの sha256 を確かめて `run_seq_pyc_u.py`（`-B`・`PYTHONPYCACHEPREFIX`。`run --stop-after-games 1` を 1 局ずつ）
8. 終わったあと: 完全な照合（集計の作り直し 1 回）・キャッシュの不変・`analyze_batch.py`・`analyze_prestop.py`

## 3. 資源・保存・停止の手順

- 毎局の前の必要量: max(128 MiB, この計画で保存済みの最大 1 局の証跡（完了した attempt のディレクトリ。prestop の 2 ファイルをふくむ）× 1.5)。残り（512 MiB − 計画のディレクトリ）と出力先の空きが、どちらも必要量以上のときだけ次を呼ぶ（`run_seq_pyc_u.py` のまま）
- 見込み（保証ではない）: t1・u1 の局は最長 7.35 秒・最大 19.9 MB（観測あり）。prestop の記録は 1 局で数十 KB の見込み（局ごとの鍵は保存済みの記録で中央値 8・最大 214、応答は最大 2,736 バイト）。4 局で 100 MB・60 秒を大きく下回る見込み
- 時間: 追加の取得の時間は単局の `Limits.seconds` とバッチの累積時間の中です。予算・待ちの条件は変えません。過去の実測から終わり方や完了局数を保証しません。要約の `seconds` の合計と、累積時間に占める割合を確かめます
- 時間・量・空きが足りなければ、未着手を残して終わる（自動で延長しない）

| 起きたこと | 扱い |
|---|---|
| 記録の通常の例外（`prestop:failed`） | その局を保存したあとで止める（`stopped_policy`） |
| 上限の到達（`prestop:capped`） | 欠落を記録して続ける（note） |
| 照合式の不一致・要約やファイルの欠け（`prestop:inconsistent`・`missing`） | 止める |
| 重大な例外（`MemoryError`・`KeyboardInterrupt`・`SystemExit`） | 吸収しない。未完了の試行（`INCOMPLETE.json`） |
| suspect・状態の不整合・replay の不一致・保存の失敗など | 今までどおり止める |
| `--acknowledge-stop`・`unlock` | 自動で使わない（止まったら報告して終える） |

- 記録の失敗（prestop の状態）と、ゲーム上の拒否・停止（終わり方・判定）は別に集計します。

## 4. 実行のときの受け入れ条件（局ごと・計画ごと）

**記録と照合**

| # | 条件 |
|---|---|
| R1 | `plan.json` の `prestop_inputs` が有効・上限 3 つで、`plan.sha256` に固定されている |
| R2 | 各局の `prestop/inputs.jsonl`・`prestop/summary.json` が、完了マーカーの `required`・`files.sha256.json`・ディスクにある |
| R3 | 対象の提示の延べ（`offered_by_kind`）が、同じ局の `result.json` の `metrics.kinds.<種類>.excluded["processability:unresolved_ruling"]` と同じ |
| R4 | 照合式（keys・repeats・要求・段なし・省略・未保存・状態）が成り立つ（`prestop_problems` が空、計算し直しても空） |
| R5 | `rows_bytes` が `inputs.jsonl` の実際の長さと同じで、行の数が `rows` と同じ |
| R6 | 集計の `prestop.counts` が、局ごとの要約を 1 回ずつ足した値と同じ（集計の作り直しの前後で同じ） |

**取得の状況**（数えるだけ。0 でないことを合格の条件にしない）: `ok`・`withheld`・`refused`・`contract_unknown`・`error`・`oversize`、各上限による省略（`skipped_fetch_cap`・`skipped_bytes_cap`）と失敗のあとの省略、範囲が空で止まった取得（trace の終わり方 `input_unavailable` と prestop の `fetches` の対応）。取得できなかった対象は 0 件や正常として扱わない。

**非干渉と秘密**

- 方策へ記録用の応答を渡さない構造は既存のテスト（`IsolationTest`）の範囲。今回のコードがそれと同じであること（実行コミットの差 0）を確かめる
- 記録の中身が配られない: prestop の記録は runner の中だけにあり、hub の更新の箱・ログの写し・GUI の経路を通らない（実装の構造。11.1 節）。実行では、公開の集計 `public/runs/vai-batch-x1/summary.json` に、prestop の行の選択肢の `card_id` の値が文字として出ないことを確かめる（相手・観戦者の閲覧用記録との比べは、同じカードが別の公開の出来事で正当に出うるので、合否の条件にしない）
- 本人のうらの選択肢は `face_down` として数え、`card_id` を補わない
- 通常の要求と記録用の要求を区別する（prestop の `attempted` と、trace の試みの数は別の数）
- 取っ手・状態・更新の異常は、既存の検査（判定・replay・観測の記録の照合・anomalies）で見る。記録用の要求が `refused`（stale）になった局があれば、異常として報告する

- 自然に出なかった失敗・上限は「未出現」とし、単体テストで確かめた範囲（11.6 節）と分けます。境界の条件を対戦で起こすために局を増やしません。

## 5. 実行のあとの、新しい記録だけからのカード別の内訳

`analyze_prestop.py`（次の単位で作る。読み取りだけ）で、この計画の完了局だけから作ります。

| 表 | 中身 |
|---|---|
| 種類別 | 候補の種類ごとの提示の延べ・一意な鍵・`ok`・未取得（理由ごと）・段なし |
| 選択肢のカード別 | `ok` の行の選択肢のうち `processability` が `unresolved_ruling` のものの `card_id` ごとの件数（延べ・局・局面） |
| 識別できないもの | `face_down`（本人のうら）・`card_id` のない参照だけの選択肢・段なしの候補・未取得の鍵 |
| 区分 | 候補全体の未裁定（prestop の行）と、選ばれた候補の中の一部の選択肢の未裁定（actors の `inputs` の記録）を別の表に |
| 単位 | 延べ・局・局面（(主体, position)）を分ける |

- 完全な記録・`real`・手札の観測から、不明なカードを補いません。
- カード ID と公開の定義（効果の型）を静的に対応づける場合も、実行時の停止コードを特定したとは扱いません。
- 旧 13 バッチの訂正済みの件数（[内訳の調査](prestop-ruling-breakdown.md)）と、この計画の結果は別の表にします。新しい数で過去の内訳が分かったとは書きません。
- 公開用は件数と分類だけ（カード ID・seed・局の識別を出さない）。

## 6. 採用の判断が要る事項と推奨値

| 事項 | 推奨 | 別の選択 |
|---|---|---|
| 条件 | L67-U どうし・rules-v2 と boundary・既定の規約集合 | 固定デッキ（discard_from_play が出ない） |
| seed | 6001（回帰）と 9001（新しい） | 6001 だけ（2 局。新しい seed の対照なし）・9001 と 9002（回帰なし） |
| 局 | 4 | 2・6 |
| use_stadium の対照 | 入れない（単体テストの範囲） | LUCKY_DECK の別の計画（+1〜2 局・予備 150 秒） |
| 予算 | 300 秒・512 MiB | — |
| キャッシュの準備の `ENTRY_MODULES` | prestop を足す（最小の修正） | 足さない |

## 7. 実行の前に残る確認（未実施。下書きでは null）

- 実行コミット・worktree・未コミット 0、`tools/`・`kyuura_engine/` が `fa992b3` と差 0、識別
- L67-U の `deck_problems`（0.185.0 での合法性）・content と展開の sha256
- 計画の `plan.sha256`・局の並び・`prestop_inputs`・`observation`
- キャッシュの準備の記録（Python の実体と版・ファイルの数・checked hash）・dry-run の `use_cache`
- 出力先の空き

## 8. 失敗・修正・未確認

- 選定の集計のスクリプトは、局の seed を `seed` の項目から読もうとして空（null）になりました（計画の局は `config.game_seed` と `game_id` に持つ）。スクリプトは直さず、出力の局の識別（`game_id`）と t1 の計画の `config.game_seed` から seed を読みました。条件ごとの数・seed の使用の確かめ（`plan.json`・`header.json` の `game_seed`・`seeds` を集める）には影響しません。
- 未確認: 0.185.0 で seed 6001 が同じ進行になるか、9001 で未裁定の候補が出るか、prestop の記録の実際の量と時間、範囲が空で止まる取得での未裁定の候補。
