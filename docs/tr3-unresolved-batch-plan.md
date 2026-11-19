# 0.194.0・TR3 で対戦を妨げる未裁定を測るバッチの計画（計画だけ）

2026-11-19。計画と文書化だけです。確定計画（`plan.json`・`plan.sha256`）の生成・キャッシュの準備・対戦・seed 探索の対戦・judge・replay はしていません。エンジン・検証用 AI・GUI・方策・規約は変えていません。

- **基点:** `claude/r2-transform-fd-offer-design` の `e0afbdc`（origin と一致。main `b1e4430` に入っていない。`e0afbdc` を含む公開のブランチはこの 1 つだけ）。
  - `kyuura_engine`・`tools`・`tests`・`scripts`・`pyproject.toml` は配布の固定 `f747dc971126145d1e61c4e6b14d8229c6a37e13`（0.194.0 の版のコミット）と差 0 です。`f747dc9` から `e0afbdc` までの 3 コミットは docs と README だけです。
  - 作業は worktree `C:\dev\kyuura-engine-lt74`・ブランチ `claude/tr3-unresolved-batch-plan`。
- **識別**（読み取りで測った値。実行のときに測り直す）:

| 項目 | 値 |
|---|---|
| エンジン | 0.194.0・behavior `b636dd94…`（58 ファイルの方式 `kyuura-package-files-sha256/1`）・instrumentation `13c773a8…` |
| 道具 | `tools.verification_ai.batch`・`TOOL_VERSION` 13・digest `be95aa1e…`（27 ファイル） |
| 判定の規則 | 10 |
| 形式 | 計画 `kyuura-vai-batch-plan/7`・完了 `kyuura-vai-batch-complete/7` |
| basis | P1 `341af16e…`・P3 `e7ad631c…`・P2 `cc467268…`・R `aecf097e…` |
| 規約集合 | `CS-KYUURA-PLAY-TR3@1`・`sha256:a7b800cf…`・development・`halts_at_undecided`・23 規約（TR3 の 3 規約をふくむ。vai-batch-tr3n1 と同じ照合値） |

- **0.194.0・`TOOL_VERSION` 13 で走らせた保存済みのバッチはありません。** 道具は `9a64f8e`（規則 10）から変わっていませんが、エンジンの behavior は 0.187.0 の `ae974fff…` から変わっています。時間と量の見積もりは過去の版の記録から作り、先行の 4 局で測り直します。
- **機械可読の下書き:** [tr3-unresolved-batch-plan.json](tr3-unresolved-batch-plan.json)（`status: draft`。確定計画ではない）。
- **証跡:** `kyuura-engine-verification-vai/verifier/runs/tr3-unresolved-batch-plan/`（事前計画・識別・デッキの検査と比べ・seed の調べ・過去の局の時間と量・記録の項目の調べ）。

**目的:** ルールベース AI のまとまった局数で、(1) 対戦が終わる原因と、(2) 対戦中に選べる手が減る原因を測ります。結果は、次に採用を検討するプレイ用規約の優先順位に使います。頻度・完走率の一般的な推定や、CURRENT との比べはしません。

**T1 の扱い:** うらの化石のメタモンのワザの候補（T1）は設計済みです（[T1 の再設計](r2-transform-face-down-offer-design.md)。未実装）。このバッチでは今の提示の制約（`no_printed_attack` など）を、そのまま測ります。

## 0. 推奨案（要約）

| 項目 | 値 |
|---|---|
| 方式 | `rules-v2` だけ（方策 `rules`・`rules_version` 2・`repeat_threshold` 2・プロファイル `deep`・分布 `uniform-candidate+uniform-stage`。1.2 節） |
| 規約集合 | `CS-KYUURA-PLAY-TR3@1`（`--conventions` で明示） |
| 記録 | `--observation`・`--prestop-inputs`（上限は既定の 256 要求・16,384 バイト・1 MiB） |
| 停止方針 | 既定（`--undetermined-evidence-missing continue`。x1・tr3n1 と同じ） |
| 変異 | なし。単一のプロセス・逐次。1 局ごとに止めて確かめる |
| 対戦の条件 | 4 つ（2 章）。C1 L67-U どうし（比べの基準）・C2 固定デッキ v2 の組・C3 P42 対 L67-U・C4 LUCKY_DECK 対 CONNECT_DECK |
| seed | 先行 9006、本実行 9007〜9012（3 章） |
| 局 | 先行 4（条件ごとに 1）＋本実行 最大 24（条件ごとに 6）＝最大 28 |
| 計画 | 8 つ。先行 `vai-batch-tr3u1-p1`〜`-p4`（各 1 局）、本実行 `vai-batch-tr3u1-m1`〜`-m4`（各 6 局）。番号は条件 C1〜C4 に対応 |
| 単局の上限 | 既定（`runner.Limits`: 操作 2000・受理 1000・番 200・120 秒） |
| 予算 | 4 章（確定値） |

入れないもの:

- boundary・reach・mixed などほかの方式
- デッキの向きの入れ替え、デッキの改造、方策の変更
- 先行の結果を見た seed・デッキ・条件の差し替え、局の追加、予算の延長
- CURRENT・規約を変えた集合との比べの対戦

## 1. 基点と実行の条件の確認

### 1.1 公開の履歴と実行のコード

| 確かめたこと | 結果 |
|---|---|
| `e0afbdc` の位置 | `origin/claude/r2-transform-fd-offer-design` と一致。`git branch -r --contains e0afbdc` はこのブランチだけ。main（`b1e4430`）の祖先ではない |
| 配布の固定との差 | `git diff --stat f747dc9 e0afbdc -- kyuura_engine tools tests scripts pyproject.toml` は空。`f747dc9..e0afbdc` の 3 コミットの変更は docs と README だけ |
| `f747dc9` | 「版を 0.194.0 にする（C-TF2…）」。`origin/claude/r2-transform-c-tf2-impl`・`u7-4-ac-doc-correction`・`r2-transform-fd-offer-design` にふくまれる |
| 道具の変化 | `git diff --stat 9a64f8e e0afbdc -- tools` は空（`TOOL_VERSION` 13 のまま） |
| 作業ツリー | lt74 は変更 0（無視をふくむ）。識別の測定のあとも `__pycache__` 0 |

### 1.2 方式と探索の範囲（現行の CLI と過去の TR3 のバッチ）

- `batch plan --help`（`e0afbdc`）の `--modes` は `boundary`・`mixed`・`reach-p6`・`reach-u-r3a`・`reach2-p6`・`reach2-u-r3a`・`rules-v1`・`rules-v2`・`uniform-stage`・`uniform-tuple` です。
- `MODES["rules-v2"]` は `{"policy": "rules", "rules_version": 2, "repeat_threshold": 2}` で、組 `("rules", "deep", "uniform-candidate+uniform-stage")` だけが計画で受け付けられます（`SUPPORTED_SETTINGS`）。
- vai-batch-tr3n1 の g001（rules-v2）の計画の `config` は、`policy` rules・`profile` deep・`distribution` uniform-candidate+uniform-stage・`rules_version` 2・`repeat_threshold` 2・seed 3 つが同じ値・`limits` が既定でした。今回も同じ指定です。
- 1 つの計画はデッキの組を 1 つだけ持ちます（`make_plan` の `deck0`・`deck1`・`decklists`）。条件ごとに別の計画にします。
- 並びは計画の中で「seed ごとに方式を並べる」です。方式が 1 つなので、計画の中の局は seed の順です。

## 2. 対戦の条件

選び方（先に決めた規則。対戦の結果では選んでいない）:

1. 比べの基準として L67-U どうしを入れる（必須）。
2. ほかは、登録済みの固定デッキと保存済みの明示リストから選ぶ。0.194.0 の `deck_problems` で合法なことを確かめる。
3. カードの種類の重なり（Jaccard）が L67-U と小さく、条件どうしでも組の中身が違うこと。
4. 過去の rules-v2 か、観測と prestop ありの局の時間と量の記録があること（見積もりのため）。
5. 片方の変形だけのデッキ（L67-URC は L67-U と 0.875）と、v1 の固定デッキ（v2 と重なる）は入れない。

| 条件 | 主体 0 | 主体 1 | 指定 | L67-U との重なり | 過去の記録 |
|---|---|---|---|---|---|
| C1 | 明示リスト L67-U | 明示リスト L67-U | `--decklist0/1 vai-batch-d/decklists/decklist-L67-U.json` | — | rules-v2・観測と prestop・0.185/0.187 で 4 局 |
| C2 | 固定デッキ `hitmonchan-dewgong-v2` | 固定デッキ `venusaur-parasect-v2` | `--deck0`・`--deck1` | 0.333・0.192 | rules-v2・観測・0.181 で 3 局 |
| C3 | 明示リスト P42 | 明示リスト L67-U | `--decklist0 p2-min-batch-plan/decklists/decklist-P42.json --decklist1 <L67-U>` | 0.35 | boundary・観測と prestop・0.187 で 2 局（rules-v2 はない） |
| C4 | 明示リスト LUCKY_DECK | 明示リスト CONNECT_DECK | `--decklist0/1 vai-batch-d/decklists/decklist-*.json` | 0.0・0.0 | rules-v2・観測・0.179 で 3 局 |

- **合法性（0.194.0）:** `batch decklist --file` は 5 つの明示リスト（L67-U・P42・LUCKY_DECK・CONNECT_DECK・L67-URC）がどれも exit 0・`legality.ok` 真・problems 空でした。固定デッキ 4 つも `deck_problems` が空でした（証跡の `out/deck_profile.json`）。
- **TR3 の 3 枚:** C1・C3 は突風・ポケモンいれかえ・きずぐすりが各 2、C2 は各 2〜3 です。C4 にはありません（規約の使用不可が出ない対照）。
- **T1 のカード:** 変身の力を登録したカードは PMCG3-042 だけで、4 条件のどのデッキにもありません。T1 の `no_printed_attack` は、ほかのうらのバトル場のカードで出たときだけ数えます（出ないことを測定の欠けにしない。5.4 節）。
- **向き:** 表の主体 0・1 のまま（C3 は p2n1 と同じ向き）。入れ替えた組は入れません。

## 3. seed・局数・並び

- **調べ:** 証跡のストア 30 か所（`kyuura-engine-verification`・`-vai`・GUI と旧版の検証のストア）の `plan.json`・`header.json` 344 ファイル（読めないもの 0）。使われた値 99 種類。9000〜9200 で使われていたのは 9001〜9005 だけでした。
- **規則:** 「9002 から上へ、連続 7 値がすべて未使用の最初の組。先頭の 1 値を先行、残りの 6 値を本実行に使う」→ **先行 9006、本実行 9007〜9012**。
- 実行のときに同じ規則で調べ直し、値が変わったら（ほかの作業で使われていたら）実行を止めて計画を直します（その場で別の値に替えない）。

**並び（固定）:**

| 段 | 局 | 順 |
|---|---|---|
| 先行 | 4 | p1（C1・9006）→ p2（C2・9006）→ p3（C3・9006）→ p4（C4・9006） |
| 本実行 | 24 | seed ごとに条件を回す: 9007 で m1→m2→m3→m4、9008 で m1→…→m4、…、9012 で m1→…→m4 |

- 本実行は 1 回の呼び出しで 1 局（`--sessions 1`）にして、計画をまたいで上の順に呼びます。予算が足りなくなったときの未着手は、並びの後ろの局（後の seed の全条件）に寄ります。
- 本実行の 4 つの計画は、先行の局を始める前に 8 つの計画をまとめて作り、`plan.sha256` を記録して固定します。先行が不合格なら、本実行の計画は未着手のまま残します。

## 4. 時間・容量の見積もりと予算（確定値）

### 4.1 保存済みの記録から作った見積もり

`out/past_games_scan.json`（完了マーカー 282 局の読み取り）から:

| 条件・記録 | 局 | 1 局の時間（attempt） | 1 局の量の最大 |
|---|---|---|---|
| C1 rules-v2・観測と prestop（0.185・0.187） | 4 | 0.62〜9.09 秒（中央値 5.41） | 14.6 MB |
| C2 rules-v2・観測（0.181） | 3 | 0.62〜6.39 秒 | 16.7 MB |
| C3 boundary・観測と prestop（0.187） | 2 | 11.49〜12.04 秒 | 17.9 MB |
| C4 rules-v2・観測（0.179） | 3 | 4.44〜6.68 秒 | 17.5 MB |
| rules-v2 の過去の最大（観測なし。L67-URC・0.179） | 15 | 最大 32.98 秒 | 44.6 MB |
| 観測ありの最大（reach・上限 limit_accepted をふくむ） | — | 最大 50.03 秒 | 95.1 MB |

- **見込み:** 28 局 × 1 局 1〜12 秒 ＝ 道具の累積時間で約 100〜400 秒。量は 28 × 15 MB 前後 ＝ 約 0.3〜0.5 GB。
- **幅:** 1 局は単局の上限の 120 秒で終わりえます。量の上限の見込みは、観測ありの受理 1000 の局で約 100〜200 MB です。見積もりの幅が大きいので、先行の後の進行の条件（7 章）と、毎局の前の残予算の確かめで扱います。
- **起動と照合の費用**（vai-batch-tr3n1 の実測）: キャッシュの準備 52.6 秒（185 ファイル・13.8 MB。バッチの外）、1 局の呼び出しの外側の実時間 約 9.6 秒（38.25 秒 / 4）、集計の作り直し 2.0 秒。照合（`check_game.py`・関門・キャッシュの照合）は 1 局 60 秒以内とみて、外側の実時間の上限に入れます。
- メモリは tr3n1 で最大のワーキングセット 205.8 MB でした（上限は設けず、記録します）。

### 4.2 予算（確定値）

| 項目 | 値 |
|---|---|
| 計画ごとの CLI | 先行: `--max-games 1 --budget-seconds 300 --evidence-max-mb 512`。本実行: `--max-games 6 --budget-seconds 900 --evidence-max-mb 1024` |
| 計画の中の既定 | 次の局を始める時間の余り 150 秒（`game_reserve_seconds`）・証跡の余り 64 MiB（`evidence_reserve_bytes`）・1 局の試行 3 回まで |
| 全体の道具の累積時間 | 3,600 秒（8 つの計画の台帳の `accounted_seconds_total` の和） |
| 全体の外側の実時間 | 7,200 秒（1 局の呼び出しと毎局の照合。起動・計画の生成・キャッシュの準備・最後の集計・文書は別に記録） |
| 全体の証跡 | 2,048 MiB（8 つの計画のディレクトリの合計） |
| 次の局を始める残予算（すべて） | その計画の残り時間 150 秒以上（道具が確かめる）・全体の道具の残り 150 秒以上・全体の実時間の残り 600 秒以上 |
| 毎局の前に必要な空き容量（すべて） | その計画の残りの証跡 384 MiB 以上・全体の残りの証跡 384 MiB 以上・出力先のドライブの空き 4,096 MiB 以上 |

- 384 MiB は、量の上限の見込み（約 200 MB）の約 2 倍です。x1 の外側のスクリプトの規則（max(128 MiB, 保存済みの最大 1 局 × 1.5)）の下限を 384 MiB にした値で、保存済みの最大 1 局 × 1.5 のほうが大きければそちらを使います。
- 全体の上限は、局が上限の 120 秒で終わり続けても 28 局を始められる時間（28 × 122 秒 ≒ 3,416 秒）です。量は上限の見込みで続くと全体の 2,048 MiB で止まります（その場合は未着手を残す）。
- **予算が足りないとき:** 次の局を始めず、未着手の局を残して終えます。延長・局の追加・`--acknowledge-stop`・unlock はしません。終わり方（`stopped_budget_time`・`stopped_budget_evidence`・全体の上限での打ち切り）を、バッチの停止として記録します（5.1 節）。
- 作業時（2026-11-19）の出力先のドライブ（C:）の空きは約 245 GB です。

## 5. 記録と集計の設計

4 つの項目を別々に数えます。どの項目も、0 であることや多いことを合否の条件にしません。数えるのは完了した局の試行（照合に通ったもの）で、未完了の試行は別に数えます。

### 5.1 対戦の終了

| 分類 | 数え方 | 証拠の出所 |
|---|---|---|
| `game_over` | 局の終わり方 | `result.json` の `termination.class`・完了マーカーの `summary.judge.termination` |
| 設定の上限 | `limit_operations`・`limit_accepted`・`limit_turns`・`limit_time` を別に | 同上（`termination.detail`） |
| 処理を続けられない未裁定 | `halted_known` で `detail.halt.category` が `unresolved_ruling` のもの。`diagnostic_id` を直接のコードとして数える | `result.json`・`trace.jsonl` |
| 処理を続けられない未対応・制限 | `halted_known` のほかの分類（`unsupported` など）と、`input_unavailable`・`no_progress` | 同上。`input_unavailable`・`no_progress` はコードを持たないので、最後の局面の候補の処理可能性を併記し、コードは「不明」 |
| 記録・照合の異常 | 完了マーカーの `stop`（`prestop:*`・観測の問題・`inconsistency`・`suspect`・`api_contract_unknown`・`state_integrity`・`exception` ほか）と、`check_game.py` の問題 | 完了マーカー・台帳・外側の照合の出力 |
| その他 | 上のどれでもない終わり方 | 同上 |

- **分母:** 始めた局（完了した局＋未完了の試行の局）。条件ごとと全体。
- **バッチの停止は別に記録します:** 計画ごとの台帳の `session_end` の `status`（`completed`・`stopped_budget_time`・`stopped_budget_evidence`・停止方針による停止）、外側の呼び出しの終わり方、全体の上限による打ち切り、未着手の局の数。
- 停止方針で止まる分類（`on_undetermined` の `no_progress`・`contract_unknown`・`unknown_diagnostic` など）が出たら、その局を記録したうえでバッチが止まります。これはバッチの停止で、ほかの局の終わり方とは混ぜません。

### 5.2 対戦中の拒否

| 数えるもの | 数え方 | 証拠の出所 |
|---|---|---|
| 送信の拒否 | `submit.outcome` が `rejected`。`result.diagnostic_id`・`case_id`・`category`・`continuable` ごと | `actors/<主体>.jsonl` の試みの行（`trace.jsonl` の `submit` と照合） |
| check と送信の断り | `check.response.refusal.code`・`submit.refusal.code` ごと（規約 ID の有無も） | 同上 |
| 判定の区分 | known_stop・expected・undetermined の分類ごと | `judge.json` の `rows`・`known_stop`・`undetermined` |
| 回答し直し | 拒否・断りのあと、同じ（主体, position）の後の試みが受理された数／受理されずに局が終わった数 | 試みの行の並び |

- **分母:** 送信した数（`counters.operations`）と check の数。コードごとに延べ・局・局面を併記します。
- 拒否のあと同じ局面で受理されて続いた例は、対戦の終了に数えません（5.1 節には局の最後の終わり方だけが入る）。
- 拒否が `no_progress`（同じ状態の拒否の上限）につながった局は、5.1 節の `no_progress` にも入ります（二重に数えたことを表に明記する）。

### 5.3 未裁定による手の減少

| 階層 | 数え方 | 証拠の出所 |
|---|---|---|
| 候補全体の除外 | 候補の応答で `processability` が `unresolved_ruling` の候補（今の記録では理由 `stops_before_acceptance`）。種類（kind）ごと | 試みの行の `candidates.response.candidates[]`（選んだ候補は `trace.jsonl` の `candidate_class` でも照合） |
| 候補の中のカードの特定 | 上の候補の inputs（prestop）の選択肢の `card_id`（おもてのとき）・`face_down`（うらのとき） | `prestop/inputs.jsonl`・`prestop/summary.json` |
| 入力の中の一部の選択肢の除外 | 取得した inputs の選択肢で `processability` が `unresolved_ruling` のもの | 試みの行の `inputs.response.stages[].options[]` |

- **単位:** 延べの提示（候補の応答に現れた回数）・試みの行・局面（主体, position）・局を並べます。同じ局面の 2 回目以降の試み（取り直し）の延べを別に示し、取り直しを除いた延べも示します。
- **選択肢の階層の分母:** 取得した inputs だけです（方策が選んだ候補の inputs と prestop の inputs）。取得していない候補の選択肢は分かりません。選択肢の階層の数は「取得した inputs の中で」と書きます。
- **コード:** 候補と選択肢の記録には停止のコードがありません（`out/field_survey_tr3n1.json`: tr3n1 の 4 局で、actors・prestop に `UNRESOLVED_…` の文字列は 0。拒否と停止の結果にだけある）。
  - **prestop でカードを特定できることと、実際の停止のコードを記録できることは別です。** prestop の行からはカード（おもての `card_id`）と候補の種類が分かりますが、そのカードでエンジンがどのコードで止まるかは記録されません。
  - そこで、候補・入力にコードがなければ「コード不明」とします。カードと種類から停止の分類表（[stop-policy-classification.json](stop-policy-classification.json)）やエンジンのソースでコードを照らした場合は「静的な照合」とし、拒否・停止の結果に出た「実測のコード」と別の列にします。
- **欠けと未出現:** prestop の `capped`・`skipped_fetch_cap`・`skipped_bytes_cap`・`unsaved_bytes_cap`・`unsaved_failure`・`failure`・`withheld`・`refused`・`contract_unknown`・`oversize` は「未記録」として数え、0 件の「未出現」と分けます。未完了の試行・未着手の局も「未実行」として分けます。

### 5.4 プレイ用規約・入力 API の制約

| 数えるもの | 区分 | 証拠の出所 |
|---|---|---|
| 規約 ID を直接確かめた使用不可 | 取得した inputs の選択肢で `eligible` 偽かつ `convention` に規約 ID があるもの。規約 ID ごと | 試みの行の `inputs.response.stages[].options[]` |
| 規約 ID のある断り | check・送信の断りに規約 ID があるもの | 試みの行の `check`・`submit` |
| 規約 ID が分からない使用不可 | 候補 `play_trainer` が `not_implemented`・理由 `no_eligible_card`（inputs を取得していない） | 候補の応答 |
| 入力の提示の制約 | `not_implemented` の理由ごと（T1 の `no_printed_attack` をふくむ）、`unverified` の理由ごと（`face_down_reveal_not_evaluated` など）、`coverage.residual` の分類（R-2〜R-5）の出現、`withheld_input_candidates`、入力を作れない（`unbuildable`） | 候補の応答・`result.json` の `counters`・`metrics` |

- **候補全体が除外されて入力を取得していない場合は、規約 ID を直接確かめた件数に入れません。** `no_eligible_card` は規約のない理由でも出るので、「規約 ID 不明」の別の列にします。本人の観測で条件を評価する場合（tr3n1 の C の方法）は「評価」と書き、直接の確認と分けます。
- **判別できる範囲:** 規約 ID は取得した inputs の選択肢と断りだけで分かります。`no_printed_attack` は候補の理由として直接分かりますが、選んだデッキに PMCG3-042 がないので、T1 が設計で対象にした場面（うらの化石のメタモン）は出ない見込みです。ほかのカードで出た場合も、そのまま理由ごとに数えます。
- C4 は TR3 の 3 枚を持たないので、規約による使用不可が 0 でも測定の欠けではありません。

### 5.5 集計の項目と証拠の対応表

| 項目 | prestop | actors | 観測 | trace | 保存済みの判定 | ほか |
|---|---|---|---|---|---|---|
| 5.1 終了 | — | 最後の局面の候補（`input_unavailable` の併記） | — | 停止の結果の照合 | `judge.json` の `termination` | `result.json`・完了マーカー・台帳 |
| 5.2 拒否 | — | 送信・check の結果とコード、回答し直し | — | `submit`・`check` の照合 | `judge.json` の `rows`・`known_stop`・`undetermined` | `counters` |
| 5.3 候補全体 | 候補の inputs（カードの特定。コードなし） | 候補の応答の `processability` | 局面の結び付け（同じ position） | `candidate_class`（選んだ候補） | — | 分類表（静的な照合） |
| 5.3 選択肢 | prestop の inputs の選択肢（別に数える） | 選んだ候補の inputs の選択肢 | — | `input_processability` | — | — |
| 5.4 規約 ID | — | 選択肢の `convention`・断り | — | — | — | — |
| 5.4 規約 ID 不明 | — | `no_eligible_card` の候補 | 条件の評価（評価と書く） | — | — | — |
| 5.4 提示の制約 | — | 候補の理由・`coverage.residual`・`withheld_input_candidates` | — | `scope`・`build` | — | `counters.unbuildable`・`metrics.kinds` |

- 項目の名前と値の形は、tr3n1 の保存済みの 4 局（0.187.0・`TOOL_VERSION` 11・形式 7）で確かめました（`out/field_survey_tr3n1.json`）。0.194.0・`TOOL_VERSION` 13 の記録で同じ名前であることは、先行の 1 局目で確かめます（7 章の P-6）。
- 分析は保存済みのファイルだけを読む新しいスクリプト（実行の単位で作る `analyze_unresolved.py`。標準ライブラリだけ・エンジンを import しない・ゲームの証跡に書かない）で行います。先行の前に、tr3n1 の保存済みの 1 局で読み取りの確かめをします（出力は証跡の外）。

## 6. 実行の手順（次の単位。ここでは実行しない）

1. 新しい worktree と作業ブランチ（この計画のコミットから）。コードが `f747dc9` と差 0、無視をふくめ変更 0、識別が 0 章の値と同じことを確かめる。実行コミット＝その worktree の HEAD（完全なハッシュ）
2. seed の調べ直し（3 章の規則）・5 つのデッキの検査（`batch decklist --file`・固定デッキの `deck_problems`）・規約集合の照合値
3. 8 つの計画を作る（CLI は下）。計画の照合（x1 の `check_plan` の写しの期待値だけを、計画名・局・seed・デッキ・規約集合・上限・実行コミットに変える）。`plan.sha256` を 8 つ記録する
4. キャッシュ（S-1）: 新しい空の場所 `C:\dev\kyuura-engine-pyc-cache\bb636dd9-tbe95aa1-cpython-314-<HEAD 7 桁>-tr3u1` を、その worktree・同じ Python で準備する。準備の時間・容量はバッチ本体と分ける
5. 外側のスクリプト: x1・tr3n1 の 6 つ（逐次・キャッシュの準備・局の照合・キャッシュの照合・ハッシュ・prestop の分析）を写す。変えるのは、容量の下限（`FLOOR` 128 → 384 MiB）と、全体の予算と並びを持つ小さな呼び出し役（計画をまたぐ並び・全体の時間と証跡の残り・ドライブの空き）だけ。差分を証跡に残す
6. dry-run で `use_cache` 真・容量の確認・`batch run` を呼ばないこと（8 つの計画とも）
7. 先行の 4 局: 1 局ずつ、キャッシュの照合 → `--sessions 1` → `check_game.py` → 関門（7 章）→ キャッシュの照合。失敗したら次を呼ばない
8. 7 章の進行の条件を確かめ、記録してから本実行へ進む
9. 本実行: 3 章の並びで 1 局ずつ（7 と同じ確かめ）。4.2 節の残予算が足りなければ、未着手を残して終える
10. 終わったあと: 計画ごとの集計の作り直し 1 回・ゲームの証跡のハッシュの不変・`final_consistency.py`（局ごとの和と集計の一致）・`analyze_prestop.py`・`analyze_unresolved.py`（読み取りだけ）・8 章の報告

**計画の CLI**（`<L67-U>` などは 2 章のファイル、`<HEAD>` は実行コミット。共通の部分 `<共通>` = `--engine-commit <HEAD> --tool-commit <HEAD> --modes rules-v2 --conventions CS-KYUURA-PLAY-TR3@1 --observation --prestop-inputs --undetermined-evidence-missing continue`）:

```
python -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr3u1-p1 --seeds 9006 --decklist0 <L67-U> --decklist1 <L67-U> --max-games 1 --budget-seconds 300 --evidence-max-mb 512 <共通>
python -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr3u1-p2 --seeds 9006 --deck0 hitmonchan-dewgong-v2 --deck1 venusaur-parasect-v2 --max-games 1 --budget-seconds 300 --evidence-max-mb 512 <共通>
python -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr3u1-p3 --seeds 9006 --decklist0 <P42> --decklist1 <L67-U> --max-games 1 --budget-seconds 300 --evidence-max-mb 512 <共通>
python -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr3u1-p4 --seeds 9006 --decklist0 <LUCKY_DECK> --decklist1 <CONNECT_DECK> --max-games 1 --budget-seconds 300 --evidence-max-mb 512 <共通>
python -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr3u1-m1 --seeds 9007 9008 9009 9010 9011 9012 --decklist0 <L67-U> --decklist1 <L67-U> --max-games 6 --budget-seconds 900 --evidence-max-mb 1024 <共通>
（m2〜m4 は p2〜p4 と同じデッキの指定で、seed・上限は m1 と同じ）
```

## 7. 先行の 4 局の確かめと、本実行へ進む条件

**先行の各局で確かめること（関門）:**

| # | 条件 |
|---|---|
| P-1 | 実行コミットのコードが `f747dc9` と差 0、無視をふくめ変更 0、識別（エンジン・道具・規則・形式・basis）が 0 章の値と同じ |
| P-2 | TR3 の一致: 計画の各局の `conventions`、`header.json`・`full_record.json` の `convention_set`、観測と送信の結果の規約集合が `CS-KYUURA-PLAY-TR3@1`・`sha256:a7b800cf…` |
| P-3 | 保存・ハッシュ・完了の照合: `batch.verify_complete`（必須ファイル・ハッシュ・停止の理由の計算し直し）の問題 0 |
| P-4 | 観測 `complete`・問題 0、prestop の R2〜R5 の成立・対応の問題 0、判定の termination の分類が記録と同じ、既存の replay の照合が期待どおり、異常 0 |
| P-5 | 契約の外（`contract_unknown`）の記録 0、規約で `eligible` 偽の選択肢の選択・check・送信 0 |
| P-6 | 5 章の項目が 0.194.0 の記録で読める（`analyze_unresolved.py` が例外なく終わり、読めない形の行が 0。値が 0 なのはよい） |
| P-7 | 局ごとの値と集計の一致: 計画の集計のカウンタ・prestop の数が局の値と同じ。`analyze_unresolved.py` の合計が局ごとの和と同じ |
| P-8 | キャッシュの中身が準備のときと同じ（各局の前後） |

**本実行へ進む条件（すべて）:**

1. 先行の 4 局で P-1〜P-8 がすべて成り立つ（記録と照合に問題がない）
2. 4.2 節の残予算で次の局（m1 の 1 局目）を始められる

- 完走率や、特定の未裁定の出現は、進む条件に入れません。先行の局が上限や未裁定で終わっても、記録と照合が成り立てば進みます。
- **見積もりの幅への扱い:** 先行の 4 局の時間と量から、本実行の見込み（条件ごとの先行の 1 局 × 6 の和）を記録します。見込みが 4.2 節の全体の残りを超えても進みます（毎局の前の残予算の確かめで、足りなくなったら未着手を残して終える）。予算は延ばしません。
- **進まないとき:** 1 が成り立たなければ本実行を始めず、先行の結果と原因を報告して終えます。道具・スクリプトの直しは別の単位にし、同じ計画での再実行・seed やデッキの替えはしません。

**本実行の途中で止めるとき:** 各局で P-3〜P-5・P-7・P-8 のどれかが成り立たないとき、外側の確かめが失敗したとき、停止方針で止まったとき。止めたら次を呼ばず、未着手を残して報告します。

| 起きたこと | 扱い |
|---|---|
| 上限の到達（局の上限） | 局の終わり方として記録して続ける |
| `halted_known`・`input_unavailable`・`no_progress` の終わり方 | 記録して続ける（停止方針の `continue_terminations`）。judge の undetermined の分類で止まるものは停止方針のとおり止める |
| prestop の上限（`capped`） | 未記録として数えて続ける |
| 記録の失敗・照合の不一致・ファイルの欠け・suspect・状態の不整合・replay の不一致・`api_contract_unknown`・保存の失敗 | 止める |
| 重大な例外 | 吸収しない（未完了の試行） |
| 残予算の不足 | 未着手を残して終える（正常な終わりとして記録） |
| `--acknowledge-stop`・unlock・予算の延長・局の追加・再実行 | 自動で使わない |

## 8. 実行後の報告の様式とプレイ用規約の候補の選び方

**表 A: 対戦を終わらせた条件**（5.1 節。上位の項目）

| 列 | 内容 |
|---|---|
| 条件 | 終わり方の分類と、コード（実測）・カード（prestop のおもて）・候補の種類 |
| 件数 | 終わった局の数（条件 C1〜C4 ごとと計） |
| 影響した局 | 局の数・対戦の条件の数 |
| 条件を特定できた証拠 | 実測のコード／静的な照合／コード不明 のどれか |
| 対処に必要な判断 | 裁定の調べ（研究上の未解決）／エンジンの未対応の実装／プレイ用規約の採否／入力 API の判断 |

**表 B: 複数局で繰り返し選べる手を減らした条件**（5.3 節・5.4 節。2 局以上に出たもの）

| 列 | 内容 |
|---|---|
| 条件 | 除外の階層（候補全体／選択肢）・候補の種類・カード（特定できたとき）・コード（実測／静的／不明） |
| 件数 | 延べの提示・取り直しを除いた延べ・局面 |
| 影響した局 | 局の数・対戦の条件の数 |
| 条件を特定できた証拠 | 表 A と同じ区分 |
| 対処に必要な判断 | 表 A と同じ区分 |

- 並べ方: 表 A は終わった局の数、表 B は影響した局の数、次に局面の数の順。
- 先行の 4 局は別の列に示し、本実行の分母（始めた局）と混ぜません。

**プレイ用規約の候補（最大 3 件）:**

1. 表 A・表 B の上位から、条件（カードと場面）を特定できたものだけを選ぶ（コード不明のものは、特定に必要な追加の記録を書いて候補から外す）
2. 研究上の未解決（`UNRESOLVED_…`。裁定の記録で決まらない）だけを候補にする。エンジンの未対応（`UNSUPPORTED_…` ほか）・記録の異常・入力 API の制約（T1 など）は別の一覧に回す
3. 表 A に出たものを先に、次に表 B の影響した局の数の順。同じ順位なら影響した対戦の条件の数
4. 各候補に、規約にする文の案ではなく、判断に要ること（場面・使えない／続行の選択肢・カードの消費・既存の規約との重なり）を書く

**言わないこと:**

- TR3 だけの結果から、CURRENT に対する完走率の改善を推定しません。規約を採用したあとの比べは、同じデッキ・seed・方策を使う別の単位にします。
- 28 局から一般的な頻度を推定しません。tr3n1・x1・p2n1 の件数と合算しません。
- 公開用は件数と分類だけです（カード ID・seed・局の識別を出さない）。

## 9. 実行の前に確定する値（下書きでは null）

- 実行コミット（完全なハッシュ）・worktree・未コミット 0・`f747dc9` との差 0・識別の測り直し
- seed の調べ直しの結果（9006〜9012 が未使用のまま）
- 5 つのデッキの合法性・確認値（明示リストの content・展開・ファイルの sha256、固定デッキの展開の sha256）
- 8 つの計画の `plan.sha256`・局の並び・各局の `conventions`・`observation`・`prestop_inputs`・上限
- キャッシュの場所・準備の記録（Python の実体と版・ファイルの数・checked hash）・dry-run の `use_cache`
- 出力先のドライブの空き（4,096 MiB 以上）
- 外側のスクリプトの写しの sha256 と、原本との差分（容量の下限・呼び出し役・`check_plan` の期待値）
- `analyze_unresolved.py` の sha256 と、tr3n1 の保存済みの 1 局での読み取りの確かめの結果

## 10. 採用の判断が要る事項と推奨値

| 事項 | 推奨 | 別の選択 |
|---|---|---|
| 条件 | C1〜C4（2 章） | C3 を P42 どうしにする・L67-URC を入れる（L67-U と重なる） |
| 局 | 先行 4・本実行 24 | 本実行 12（条件ごとに 3） |
| seed | 先行 9006・本実行 9007〜9012（規則で選んだ新しい値） | — |
| 予算 | 4.2 節 | 全体の証跡を 1,024 MiB にする（上限の見込みが続くと早く止まる） |
| 規約 ID の直接の記録を広げる修正（prestop の対象に `no_eligible_card` を足すなど） | しない（今の記録で「規約 ID 不明」として分けて数える） | 道具の識別・`TOOL_VERSION` が変わる別の単位 |
| 停止のコードを候補の記録に足す修正 | しない（コード不明・静的な照合として分ける） | エンジンの API の変更（別の単位） |

## 11. 失敗・未確認

- 失敗: 証跡の `commands.txt` に記録しました（読み取りのスクリプトの直し）。対戦・計画の生成はしていません。
- 未確認（実行で分かること）: 0.194.0・`TOOL_VERSION` 13 での時間と量、記録の項目の名前が同じこと、各条件の終わり方と未裁定の出現、上限による終わり方、C2〜C4 の rules-v2 での prestop の量。
