# 0.198.0・TR8 の新しい seed で完走と残る未裁定を測るバッチの計画（計画だけ）

2026-11-23。計画と文書化だけです。次のことはしていません（次の単位）:

- 確定計画（`plan.json`・`plan.sha256`）の生成、キャッシュの準備、dry-run、対戦、judge、replay
- エンジン・検証用 AI・GUI・方策・規約・judge・版の変更

**基点と実行候補:**

- **文書の基点:** `claude/rs1-tr7-tr8-comparison` の `34c3ed1f86940f538db17c571b9c528351bfbfe4`（origin と一致）。
- **実行の候補:** 0.198.0 の配布の固定 `a3583786cf93ee67ce95b94a5b94505f5fcef1b0`（commit。`34c3ed1` の祖先）。
  - `a358378..34c3ed1` の差は README と docs だけで、実行コードの差は 0 です（RS1 の比較の作業で照合済み。[rs1-tr7-tr8-comparison](rs1-tr7-tr8-comparison.md) 1 章）。
- **作業の場所:** worktree `C:\dev\kyuura-engine-lt98`、ブランチ `claude/tr8-unresolved-batch-plan`。識別とデッキの検査は、別の worktree `C:\dev\kyuura-engine-lt98r` を `a358378` に切り離して行いました（測定の前後とも、無視をふくめ変更 0・`__pycache__` 0）。

**重複の確かめ（新しい計画を作る前）:**

| 調べた場所 | 結果 |
|---|---|
| 公開のブランチの名前 | TR8 の監査・新しい seed の計画にあたるものはない（TR3・TR6 の計画、TR7 の補足、RS1 の 3 本だけ） |
| 基点の `docs/` のファイル名 | TR8 を名前にふくむのは v0.198 の規約文書だけ。`tr8-unresolved-batch-plan` はない |
| 証跡の実行フォルダ・公開の要約 | TR8 の新しい seed・4 条件の監査（計画・進行・完了）はない。TR8 の名前があるのは RS1 の 1 組の比較（`vai-batch-rs1c-tr8`・旧 seed 9017・C4 の 1 局）と、TR8 の実装の作業記録だけ |

→ 同じ監査は、計画済み・進行中・完了済みのどれでもありません。新しい計画を作りました。

**識別**（実行候補 `a358378` を切り離して読み取りで測った値。実行のときに測り直す）:

| 項目 | 値 |
|---|---|
| エンジン | 0.198.0・behavior `c9912dd8…`（58 ファイル・方式 `kyuura-package-files-sha256/1`）・instrumentation `61f09812…`（4 ファイル） |
| 道具 | `tools.verification_ai.batch`・`TOOL_VERSION` 13・digest `be95aa1e…`（27 ファイル） |
| 判定の規則 | 10 |
| 形式 | 計画 `kyuura-vai-batch-plan/7`・完了 `kyuura-vai-batch-complete/7` |
| basis | P1 `e27dfe1d…`・P3 `69d05615…`・P2 `e1ab9ac0…`・R（0 枚の回収）`2e912bee…` |
| 規約集合 | `CS-KYUURA-PLAY-TR8@1`・固定値 `sha256:27dfe27a…`（計算し直した値と一致・検証の問題 0）・27 規約 |
| TR8 の中身 | `CS-KYUURA-PLAY-TR7@1`（26 規約・`sha256:4ee438ea…`・固定値 = 計算値）の並びのまま、`PC-LUCKY-STADIUM-REPLACEMENT@1`（RS1）を最後に 1 つ足したもの。TR7 にあって TR8 にない規約は 0 |
| 既定の集合 | `CS-KYUURA-CURRENT@1`（12 規約。TR8 は明示したときだけ） |

- 上の値は、RS1 の比較の実行（`vai-rs1-compare-run/out/identity_run.json`）と、エンジンのファイルの場所のほかは全項目で同じでした。照合した項目はエンジンの版・識別・集合・既定の集合・規約の照合値・続行の実装の一覧・道具・道具の版・判定の規則・basis です。
- **機械可読の下書き:** [tr8-unresolved-batch-plan.json](tr8-unresolved-batch-plan.json)（`status: draft`。確定計画ではない）。
- **証跡:** `kyuura-engine-verification-vai/verifier/runs/vai-tr8-batch-plan-run/`。事前計画、識別、集合と形式、デッキの検査、seed の調べ、過去の局の時間と量の見積もりを置いています。

**目的:** TR8 を明示して選び、ルールベース AI の通常の対戦（`new_game` から）で、着手した局のうち何局が `game_over` まで進むか、どの未裁定が続行や手の選択を妨げるかを測ります。

- RS1 は、以前は止まっていた候補が通常の対戦で提示・選択・受理されるところまでを、1 組（旧 seed 9017・C4）で確かめました（[rs1-tr7-tr8-comparison](rs1-tr7-tr8-comparison.md)）。今回は未使用の seed で、同じ 4 つのデッキの条件を調べます。
- 頻度や完走率を一般に推定することはしません。旧 TR3・TR6・TR7 の監査の値は参考で、版・seed・対象の局が違うので、完走率の差を TR8 の効果としては扱いません。

## 0. 推奨案（要約）

| 項目 | 値 |
|---|---|
| 方式 | `rules-v2` だけ（方策 `rules`・`rules_version` 2・`repeat_threshold` 2・プロファイル `deep`・分布 `uniform-candidate+uniform-stage`） |
| 規約集合 | `CS-KYUURA-PLAY-TR8@1`（`--conventions` で明示） |
| 記録 | `--observation`・`--prestop-inputs`（上限は既定の 256 要求・16,384 バイト・1 MiB） |
| 停止方針 | 既定（`--undetermined-evidence-missing continue`。TR3・TR6 の監査、TR7 の補足、RS1 の比較と同じ） |
| 変異 | なし。単一のプロセス・逐次。1 局ごとに止めて確かめる |
| 対戦の条件 | 4 つ（2 章）。C1 L67-U どうし・C2 固定デッキ v2 の組・C3 P42 対 L67-U・C4 LUCKY_DECK 対 CONNECT_DECK（旧監査と同じ） |
| seed | 先行 9020、本実行 9021〜9026（3 章） |
| 局 | 先行 4（条件ごとに 1）＋本実行 24（条件ごとに 6）＝ 28 |
| 計画 | 8 つ。先行 `vai-batch-tr8a-p1`〜`-p4`（各 1 局）、本実行 `vai-batch-tr8a-m1`〜`-m4`（各 6 局）。番号は条件 C1〜C4 に対応 |
| 単局の上限 | 既定（`runner.Limits`: 操作 2000・受理 1000・番 200・120 秒） |
| 実行のコミット | `a3583786cf93ee67ce95b94a5b94505f5fcef1b0`（完全なハッシュを `--engine-commit`・`--tool-commit` に渡す。worktree を切り離して使う） |
| 予算 | 4 章（先行の各計画 300 秒・512 MiB、本実行の各計画 900 秒・1,024 MiB、全体 道具 3,600 秒・実時間 7,200 秒・証跡 2,048 MiB） |

入れないもの:

- boundary・reach・mixed などほかの方式
- デッキの向きの入れ替え・改造、方策の変更
- 先行の結果を見た seed・デッキ・条件の差し替え、局の追加、予算の延長
- TR7・TR6・CURRENT との比べの対戦（同じ seed で集合だけを変える比べは別の単位）

## 1. 基点と実行の条件の確認

| 確かめたこと | 結果 |
|---|---|
| `34c3ed1` の位置 | `origin/claude/rs1-tr7-tr8-comparison` と一致（`ls-remote` と `rev-parse`） |
| `a358378` の位置 | 完全なハッシュ `a3583786cf93ee67ce95b94a5b94505f5fcef1b0` が commit として存在し、`34c3ed1` の祖先（`merge-base --is-ancestor` 真） |
| コードの差 | `a358378..34c3ed1` は README と docs だけ（RS1 の比較の作業の記録）。この単位は docs だけを足す |
| 作業ツリー | `lt98r`（切り離し）は測定・デッキの検査のあとも変更 0（無視をふくむ）・`__pycache__` 0 |
| RS1 の比較の記録 | 識別・時間と量の幅の資料として使った。識別は上の表と同じ |

## 2. 対戦の条件

旧監査（TR3 の本実行・TR6 の監査・TR7 の補足）と同じ 4 条件です。席の向き・ファイルも同じにします。

| 条件 | 主体 0 | 主体 1 | 指定 | 合法性（0.198.0・`a358378`） |
|---|---|---|---|---|
| C1 | 明示リスト L67-U | 明示リスト L67-U | `--decklist0/1 verifier/runs/vai-batch-d/decklists/decklist-L67-U.json` | exit 0・`legality.ok` 真・problems 空 |
| C2 | 固定デッキ `hitmonchan-dewgong-v2` | 固定デッキ `venusaur-parasect-v2` | `--deck0`・`--deck1` | `deck_problems` 空 |
| C3 | 明示リスト P42 | 明示リスト L67-U | `--decklist0 verifier/runs/p2-min-batch-plan/decklists/decklist-P42.json --decklist1 <L67-U>` | exit 0・ok・空 |
| C4 | 明示リスト LUCKY_DECK | 明示リスト CONNECT_DECK | `--decklist0/1 verifier/runs/vai-batch-d/decklists/decklist-*.json` | exit 0・ok・空 |

- **カードの版の照合:** `batch decklist --file`（`a358378`）の 4 つの明示リストの出力は、TR6 の監査の計画（0.196.0）の出力と、エンジンの版と behavior の 2 行のほかは同じでした。`content_sha256`・展開の `sha256`・カード ID の一覧・合法性、固定デッキ 4 つのカード ID の一覧と `deck_problems` も同じです（証跡の `out/deck_profile.json`）。
- **確認値:** L67-U `5fb91539…`・P42 `243c137f…`・LUCKY_DECK `857abd7d…`・CONNECT_DECK `6ae10e56…`（展開の sha256）。どれも 60 枚です。
- **ER9・H4・T19b・RS1 にかかわるカード**（デッキの構成。出るかどうかは対戦で決まる）:

| 条件 | ER9 のエネルギー回収（PMCG1-076） | H4 のエナジーへんかんを持つゴース（PMCG3-029） | T19b の「とうめい」を持つゴースト（PMCG3-030） | RS1 のラッキースタジアム（「自分の番ごとに1回」の 10 版） | TR3 の 3 枚（突風・いれかえ・きずぐすり） |
|---|---|---|---|---|---|
| C1 | なし | なし | なし | なし | 各 2 |
| C2 | 各デッキ 2 | なし | なし | なし | 2〜3 |
| C3 | なし | P42 に 4 | P42 に 3 | なし | 各 2 |
| C4 | なし | なし | なし | LUCKY_DECK に PRN-015 が 4 | なし |

- 「とうめい」の登録（`AttackImmunityOnHeads`）があるカードは PMCG3-030 だけです。T19b の場面は、C3 で主体 0 のゴーストが場に出て、相手が特殊状態のコインのワザを使うときに限られます。
- RS1 の範囲の外の版（PRN-027）と、範囲の外のスタジアム（エネルギースタジアムなど）は、4 条件のどのデッキにもありません。RS1 の `#other` の事例は、デッキの構成からは出ない見込みです。
- 変身の力を登録したカード（PMCG3-042）は、4 条件のどのデッキにもありません。
- 範囲の外の経路が出なくても、測定の欠けにはしません（5.4 節）。
- **引き継ぐ設定:** `rules-v2`／`deep`・既定の単局上限・観測と prestop あり・変異なし・逐次実行。

## 3. seed・局数・並び

- **調べ:** 証跡のストア 30 か所の `plan.json`・`header.json` 458 ファイルを読みました。対象は `kyuura-engine-verification`・`-vai`、GUI と旧版の検証のストアで、読めないものは 0 です（証跡の `out/seed_scan.json`）。
  - 使われた値は 113 種類でした。
  - 9000〜9200 で使われていたのは 9001〜9019 で、最大値は 9019 です。9013〜9019 は TR6 の監査（未着手の局をふくむ計画）・TR7 の補足・RS1 の比較で使われています。
- **規則:** 9020 から上へ、連続 7 値がすべて未使用の最初の組を選びます。先頭の 1 値を先行、残りの 6 値を本実行に使います。
  - → **先行 9020、本実行 9021〜9026**
- 実行のときに同じ規則で調べ直します。値が変わっていたら（ほかの作業で使われていたら）、実行を止めて計画を直します。その場で別の値に替えることはしません。対戦の結果による seed の差し替えもしません。

**並び（固定）:**

| 段 | 局 | 順 |
|---|---|---|
| 先行 | 4 | p1（C1・9020）→ p2（C2・9020）→ p3（C3・9020）→ p4（C4・9020） |
| 本実行 | 24 | seed の昇順に、seed の中で条件を回す: 9021 で m1→m2→m3→m4、9022 で m1→…→m4、…、9026 で m1→…→m4 |

- 1 回の呼び出しで 1 局（`--sessions 1`）にし、計画をまたいで上の順に呼びます。
- 予算が足りなくなったとき、未着手は並びの後ろの局（後の seed の全条件）に寄ります。
- 8 つの計画は、先行の 1 局目を始める前にまとめて作り、`plan.sha256` を記録して固定します。先行が不合格なら、本実行の計画は未着手のまま残します。

## 4. 時間・容量の見積もりと予算

### 4.1 保存済みの記録から作った見積もり

`out/budget_estimate.json` を使いました。完了マーカー 30 局と、計画の台帳・作業記録の外側の台帳の読み取りです。

| 記録 | 局 | 終わり方 | 1 局の時間（attempt）の中央値・最大 | 1 局の量の最大 | 道具の累積 | 外側の実時間（game_end の和） | 計画のディレクトリ |
|---|---|---|---|---|---|---|---|
| TR6 の監査の先行（0.196.0・TR6） | 4 | game_over 4 | C1 2.07・C2 2.58・C3 2.96・C4 4.75 秒 | 17.0 MB（C4） | 22.523 秒 | 84.160 秒（文書の値） | 44,788,269 バイト |
| TR6 の監査の本実行（同上） | 15 | game_over 14・no_progress 1 | C1 1.34・3.49／C2 1.46・35.88／C3 4.72・9.22／C4 4.27・4.95 秒 | 102.6 MB（C2・受理 993） | 127.708 秒 | 351.032 秒 | 255,215,431 バイト |
| TR7 の補足（0.197.0・TR7） | 9 | game_over 9 | C1 1.38・2.07／C2 4.75・9.14／C3 1.55・1.96／C4 1.68・4.68 秒 | 32.1 MB（C2） | 44.451 秒 | 184.729 秒 | 81,264,877 バイト |
| RS1 の比較（0.198.0・TR7／TR8・C4） | 2 | game_over 2 | 4.61・4.65 秒 | 16.3 MB | 14.846 秒 | 44.375 秒 | 32,172,332 バイト |

- **見込み（参考）:** 4 つの記録ごとの 1 局あたりの平均のうち最大の値（道具 8.514 秒・外側 23.402 秒・証跡 17,014,362 バイト。どれも TR6 の本実行）× 28 局は、道具 238.4 秒・外側 655.3 秒・証跡 476,402,138 バイト（454.3 MiB）です。1.5 倍にすると道具 357.6 秒・外側 982.9 秒・証跡 681.5 MiB で、全体の上限（道具 3,600 秒・実時間 7,200 秒・証跡 2,048 MiB）の 10%・14%・33% にあたります。
- **版・seed の違い:** 0.198.0・TR8 では、RS1 の受理のあとに局の進み方が TR7 と分かれます（RS1 の比較で、番 35 から先の展開が変わった）。seed も新しいので、局の長さは見込みと違いえます。
- **上側:** 1 局は単局の上限の 120 秒で終わりえます。28 × 122 秒 ＝ 3,416 秒が道具の全体の上限に入ります。量の上側は、受理 1000 の局で約 100〜200 MB です（TR6 の監査の最大 1 局は受理 993 で 102.6 MB）。
- **起動と照合の費用**（RS1 の比較・TR7 の補足の実測）:
  - キャッシュの準備はバッチの外で、185 ファイル・約 13.9 MB・約 27 秒
  - 1 局の外側の実時間（呼び出しと照合）は 22.1〜30.6 秒（TR6 の本実行の最大は 68.6 秒）
  - 集計の作り直しは 1 計画 約 2 秒

### 4.2 予算（確定値）

| 項目 | 値 |
|---|---|
| 計画ごとの CLI | 先行: `--max-games 1 --budget-seconds 300 --evidence-max-mb 512`。本実行: `--max-games 6 --budget-seconds 900 --evidence-max-mb 1024` |
| 計画の中の既定 | 次の局を始める時間の余り 150 秒（`game_reserve_seconds`）・証跡の余り 64 MiB（`evidence_reserve_bytes`）・1 局の試行 3 回まで |
| 全体の道具の累積時間 | 3,600 秒（8 つの計画の台帳の `accounted_seconds_total` の和） |
| 全体の実時間 | 7,200 秒（1 局の呼び出しと毎局の照合の外側の時間。起動・計画の生成・キャッシュの準備・最後の集計・文書は別に記録） |
| 全体の証跡 | 2,048 MiB（8 つの計画のディレクトリの合計） |
| 各局の開始条件（すべて） | その計画の道具の残り 150 秒以上・全体の道具の残り 150 秒以上・全体の実時間の残り 600 秒以上 |
| 各局の開始条件の容量（すべて） | その計画の証跡の残り 384 MiB 以上・全体の証跡の残り 384 MiB 以上・出力先のドライブの空き 4,096 MiB 以上 |

- 証跡の残りの下限は max(384 MiB, 保存済みの最大 1 局 × 1.5) とします。保存済みの最大 1 局（102.6 MB）× 1.5 は 146.8 MiB なので、384 MiB を使います。先行の局でこれを超える 1 局が出たら、その × 1.5 を下限にします（下げることはしない）。
- 本実行の各計画（1,024 MiB）は、計画の証跡が 640 MiB を超えたあとは次の局を始めません（残り 384 MiB の条件）。
- **予算が足りないとき:** 次の局を始めず、未着手の局を残して終えます。延長・局の追加・`--acknowledge-stop`・unlock はしません。終わり方は、計画の打ち切りとして記録します（`stopped_budget_time`・`stopped_budget_evidence`・全体の上限での打ち切り。5.1 節）。
- 作業時（2026-11-23）の出力先のドライブ（C:）の空きは約 246 GB でした。実行の日の値は実行のときに測ります（下書きでは `null`）。

### 4.3 先行の実測で見積もりを更新する手順

1. 先行の 4 局のあと、各条件の先行 1 局の道具の時間・外側の実時間・量を記録する（台帳と完了マーカー）。
2. 本実行の見通しを作る:
   - 本体: 条件ごとに「先行 1 局 × 6」を足す。
   - 上側: その 1.5 倍と、4.1 節の過去の 1 局の最大 × 24 も並べる。
3. 見通しを全体の残り（道具・実時間・証跡）と並べて記録する。見通しが残りを超えても進む。毎局の前の残予算の確かめで、足りなくなったら未着手を残して終える。予算は変えない。
4. 先行の最大 1 局 × 1.5 が 384 MiB を超えたら、4.2 節の証跡の下限をその値にする。
5. 更新した見通しは、文書の結果の節と証跡に書く。本実行の局数・seed・並びは変えない。

## 5. 記録と集計の設計

項目ごとに別々に数えます。0 であることや多いことを、どの項目でも合否の条件にしません。数えるのは、完了した局の試行で照合に通ったものです。未完了の試行と未着手の局は「未実行」として別に数えます。**主集計は本実行の局だけで、先行の 4 局は別の欄に分けます。**

### 5.1 局の終了と完走率

| 分類 | 数え方 | 証拠の出所 |
|---|---|---|
| `game_over` | 局の終わり方 | `result.json` の `termination.class`・完了マーカーの `summary.termination`・`summary.judge.termination` |
| 未裁定による終了 | `halted_known` で `detail.halt.category` が `unresolved_ruling`。`diagnostic_id` を実測のコードとして数える | `result.json`・`trace.jsonl` |
| `no_progress` | 同じ状態の引き直しの上限。コードを持たないので、直前の拒否のコード（あれば実測）と最後の局面の候補の処理可能性を併記する | 同上・試みの行 |
| 単局の上限 | `limit_operations`・`limit_accepted`・`limit_turns`・`limit_time` を別に | 同上（`termination.detail`） |
| ほかの続けられない終わり方 | `halted_known` のほかの分類（`unsupported` など）・`input_unavailable` | 同上 |
| 異常 | 完了マーカーの `stop`（`prestop:*`・観測の問題・`inconsistency`・`suspect`・`api_contract_unknown`・`state_integrity`・`exception` ほか）と、外側の照合の問題 | 完了マーカー・台帳・外側の照合の出力 |
| 計画の打ち切り | 停止方針の発動・実行や照合の異常・予算の不足で、次の局を呼ばなかったこと。局の終わり方とは別に、未着手の局の数として数える | 計画の台帳の `session_end` の `status`・外側の台帳 |

- **件数は 5 つを別に数えます:** 予定（28。本実行 24）・着手（呼び出した局）・完了（完了マーカーのある局）・未完了（`INCOMPLETE.json` で終わった試行の局）・未着手（呼ばなかった局）。
- **完走率** ＝ `game_over` の局の数 ÷ 着手した局の数。必ず件数を併記します（例: 「22／24」）。分母に未着手を入れません。未完了の局は分母に入り、`game_over` には入りません。
  - 主集計は本実行、先行は別の欄です。条件ごと（C1〜C4）と全体を出します。
  - 旧 TR3・TR6・TR7 の監査の値は参考の列だけに置きます（5.6 節）。
- 停止方針で止まる分類（`on_undetermined` の `no_progress`・`contract_unknown`・`unknown_diagnostic` など）が出た場合は、その局を記録したうえで計画が止まり、7 章の打ち切りになります（TR6 の本実行の C3・9017 と同じ扱い）。

### 5.2 拒否と除外の 5 区分

| # | 区分 | 数え方 | 証拠の出所 |
|---|---|---|---|
| R1 | **送信した拒否** | `submit.outcome` が `rejected`。`verifier.engine_code`（`result.diagnostic_id`）・`category`・`continuable` ごと | `actors/<主体>.jsonl` の試みの行（`trace.jsonl` の `submit` と照合） |
| R2 | **答え直して続いた拒否** | R1 のあと、同じ（主体, position）の後の試みで、送信して受理された拒否の数。受理されずに局が終わった拒否は別に数える | 試みの行の並び・`result.json` |
| R3 | **道具が送信を抑止した試み** | R1 のあと、同じ（主体, position）の試みで送信がない行（`submit` なし）の数と、counters の `retry_same_input`。拒否とかかわらない `policy_suppressed` は別の欄 | 試みの行・`counters` |
| R4 | **候補全体の除外** | 候補の応答で `processability` が `unresolved_ruling`（理由 `stops_before_acceptance`）の候補。種類（kind）・カードごと | 試みの行の `candidates.response.candidates[]`（選んだ候補は `trace.jsonl` の `candidate_class` でも照合）。カードの特定は `prestop/inputs.jsonl` と本人の観測 |
| R5 | **取得済み入力の中の選択肢の除外** | 取得した inputs の選択肢で `processability` が `unresolved_ruling` のもの | 試みの行の `inputs.response.stages[].options[]`（prestop の inputs は別に数える） |

- check・送信の断り（`refusal.code`。規約 ID の有無も）と、判定の区分（known_stop・expected・undetermined）は R1 の横に別の列として並べます。
- **単位と分母:**
  - R1〜R3: 送信の数（`counters.operations`）と check の数。コードごとに延べ・局面・局。
  - R4: 候補の応答のある試みの行の数。延べ・取り直しを除いた延べ（同じ（主体, position）の 2 回目以降を除く）・局面・局。
  - R5: 取得した inputs の数と、その中の選択肢の数。方策が選んだ候補の inputs だけが分母に入るので、「取得済み入力の中で」と書きます。
- 答え直して続いた拒否は、局の終了に数えません。拒否が `no_progress` につながった局は 5.1 節の `no_progress` にも入るので、二重に数えたことを表に書きます。
- **コードの 3 区分:**
  - **実測:** 同じ局面の拒否・停止の結果に出たコード（R1・未裁定による終了）。
  - **静的照合:** カードと種類と、そのときの本人の観測から、停止の分類表（[stop-policy-classification.json](stop-policy-classification.json)）とエンジンのソースで照らしたコード。R4・R5 は、候補と選択肢の記録に停止のコードがないので、カードを特定できても実測にはしません。
  - **不明:** どちらでも決まらないもの。
- **未記録と確認済みの 0 件を分けます:**
  - 未取得: inputs を取得していない候補の選択肢。
  - 記録上限による省略: prestop の `capped`・`skipped_fetch_cap`・`skipped_bytes_cap`・`unsaved_bytes_cap`。
  - 読み取り失敗: `unsaved_failure`・`failure`・`withheld`・`refused`・`contract_unknown`・`oversize`、分析スクリプトの読めない行。
  - これらは「未記録」として数え、確認できた 0 件（「未出現」）とは別の列にします。未完了の試行・未着手の局は「未実行」です。

### 5.3 規約で使えた手（ER9・H4・T19b・RS1）

| 規約 | 規約の適用記録がある受理 | 残った拒否 | 経路の見分け |
|---|---|---|---|
| ER9 `PC-ENERGY-RETRIEVAL-ZERO@1` | `convention_applied`（規約 ID）の数と、その送信の判定（expected） | `UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE` の拒否。経路（錯乱ジムの「おもて」・「うら」・サイキックコントロール・［ちえくらべ］・不明）ごと | 状態のログ（`chaos_check` など。[play-convention-tr4-v0.195](play-convention-tr4-v0.195.md) 2 章） |
| H4 `PC-ENERGY-CONVERSION-ZERO@1` | 同上。経路（元のワザ・ゆびをふる）ごと | `UNRESOLVED_RECOVER_ZERO_ENERGY` の拒否。経路（メタモンの［へんしん］・ほかのコピー・不明）ごと | 宣言したワザ・ワザを使ったポケモンのカード（[play-convention-tr6-v0.196](play-convention-tr6-v0.196.md) 2 章） |
| T19b `PC-T19B-NULLIFIED-STATUS-COIN@1` | 同上。出来事の並び（`evade_check` heads → `attack_evaded` → `convention_applied` → ワザの `coin_flip`）を併記 | `UNRESOLVED_EVADED_EFFECT_COIN` の拒否。経路（範囲の外のワザ・コピー・不明）ごと | 宣言したワザ・相手の「とうめい」の `evade_check`（[play-convention-tr7-v0.197](play-convention-tr7-v0.197.md) 3 章） |
| RS1 `PC-LUCKY-STADIUM-REPLACEMENT@1` | 同上。`scene` `#lucky-once-stated-replacement`・`used_cards` を併記 | RS1 の候補全体の除外（R4 の `use_stadium` で、`UNRESOLVED_STADIUM_REUSE_AFTER_REPLACEMENT` の `#other` の静的照合）と、送信の拒否 | 公開ログの `stadium_used`・`stadium_placed`（`replaces`）と観測の `stadium_uses_this_turn` |

- **RS1 の 3 段階**（記録で確かめられる範囲。分母は RS1 の局面）:
  - **局面:** 本人の観測で、この番の `stadium_uses_this_turn` に自分が使った同じ名前の別の個体があり、場のスタジアムが「自分の番ごとに1回」のラッキースタジアムで、自分がまだその個体を使っていない（主体, position）。公開ログの入れかえ（`stadium_placed` の `replaces`）で裏づけます。
  - **提示:** その局面の候補に、場の個体の `use_stadium` があり、`processability` が `unresolved_ruling` でない（RS1 の比較では `may_stop_later`・`continuation_not_evaluated`）。延べ・取り直しを除いた延べ・局面で数えます。
  - **選択:** その局面の試みで方策が `use_stadium` を選んだ（`trace.jsonl` の選んだ候補）。組み立てられなかった試み（`unbuildable`）は別に数えます。
  - **受理:** 選んだ `use_stadium` の `check` が valid、`submit` が accepted、judge が `expected` で、同じ受理の公開ログに `convention_applied`（RS1・`#lucky-once-stated-replacement`）がある。コインの結果（「おもて」で `draw`）も併記します。
  - 3 段階は別々に数え、提示があって選ばれなかった局面・選ばれて受理されなかった局面を残します。
- **受理と残った拒否は別の欄です。** 規約が当たった受理の数から、ほかの局での解消を推定しません。対象の場面が出なかった（未出現）ことから「解消した」とは言いません。
- 経路を状態のログから決められないときは「不明」とし、記録にある値だけを書きます。
- **ほかの規約:** `convention_applied` の規約 ID ごとの数（`PC-SETUP-MULLIGAN-COUNT` など）、取得した inputs の選択肢で `eligible` 偽かつ `convention` に規約 ID があるもの（TR3 の 3 規約など）、規約 ID のある断りを、別の表に並べます。規約 ID が分からない使用不可（`play_trainer`・`no_eligible_card`）は「規約 ID 不明」の列にします。
- **規約の数の照合:** `convention_applied` の数を、観戦者・主体 0・主体 1 の公開ログで比べ、同じであることを確かめます。

### 5.4 入力の提示の制約（参考の欄）

`not_implemented` の理由ごと（`no_printed_attack`・`no_eligible_card` をふくむ）、`unverified` の理由ごと、`coverage.residual`、`withheld_input_candidates`、入力を作れない（`unbuildable`）の数を、候補の応答と `result.json` の `counters`・`metrics` から並べます。未裁定ではないので、表 A・表 B には入れません。

### 5.5 集計の項目と証拠の対応表

| 項目 | prestop | actors | 観測 | trace | 保存済みの判定 | ほか |
|---|---|---|---|---|---|---|
| 5.1 局の終了・完走率 | — | 最後の局面の候補（`no_progress`・`input_unavailable` の併記） | — | 停止の結果の照合 | `judge.json` の `termination` | `result.json`・完了マーカー・台帳 |
| R1〜R3 拒否・答え直し・抑止 | — | 送信・check の結果とコード、同じ局面の後の試み（送信あり／なし） | — | `submit`・`check` の照合 | `rows`・`known_stop`・`undetermined` | `counters` |
| R4 候補全体 | 候補の inputs（カードの特定。コードなし） | 候補の応答の `processability` | 局面の結び付け（手札・場・スタジアムの使用） | `candidate_class` | — | 分類表（静的照合） |
| R5 選択肢 | prestop の inputs の選択肢（別に数える） | 選んだ候補の inputs の選択肢 | 選択肢のポケモンのダメージ・トラッシュの中身 | `input_processability` | — | — |
| 5.3 規約の受理 | — | 送信の結果（`accepted`・規約集合） | `convention_applied`・出来事の並び | 選んだ候補 | 送信の行の判定 | 経路の見分け（状態のログ） |
| 5.3 残った拒否 | — | 拒否のコード・答え直し | 拒否の前後で見る人の観測が同じこと | `submit` | known_stop／`evidence_missing_stop` | 経路の見分け |
| 5.3 RS1 の 3 段階 | `use_stadium` の inputs（段なし） | 候補の `processability`・選んだ候補・送信の結果 | `stadium_uses_this_turn`・`stadium_placed`・`convention_applied`・`coin_flip` | 選んだ候補 | 送信の行の判定 | — |

- 分析は、保存済みのファイルだけを読む新しいスクリプトで行います（次の単位で作る `analyze_tr8a.py`）。
  - 標準ライブラリだけを使い、エンジンを import せず、ゲームの証跡に書きません。
  - 元にするのは、TR6 の監査の `analyze_tr6a.py`、TR7 の補足の `scenes_tr7s.py`、RS1 の比較の `analyze_rs1c.py`（観測の出来事の番号は受理の番号 + 1。RS1 の比較の F3）です。
- 先行の前に、保存済みの局で読み取りを確かめます（出力は証跡の外）。
  - RS1 の比較の TR8 の 1 局: 受理 190・`convention_applied` 1（RS1）・RS1 の局面 1（提示・選択・受理が各 1）が、保存済みの分析と同じになること。
  - TR6 の監査の本実行の C3・9017 の局（拒否 1・`retry_same_input` 63・`no_progress`）: R1〜R3 の数が保存済みの値と同じになること。
  - TR7 の補足の 9 局: R4・R5 の延べ・局面・局が保存済みの値と同じになること。
  - 集合の照合は TR8 の局だけで真になります（ほかは数の照合だけに使う）。
- 0.198.0 の記録で項目の名前が同じであることは、先行の 1 局目で確かめます（7 章の P-6）。

### 5.6 過去の監査の結果（参考）

| 記録 | 版・集合 | 局 | 完走（`game_over`／着手） | 終わり方のほか | 計画の打ち切り |
|---|---|---|---|---|---|
| TR3 の監査（[tr3-unresolved-batch-plan](tr3-unresolved-batch-plan.md)） | 0.194.0・TR3@1 | 先行 4・本実行 24 | 先行 4／4・本実行 24／24 | なし | なし |
| TR6 の監査（[tr6-unresolved-batch-plan](tr6-unresolved-batch-plan.md)） | 0.196.0・TR6@1 | 先行 4・本実行 15（予定 24） | 先行 4／4・本実行 14／15 | `no_progress` 1（C3。直前の拒否 `UNRESOLVED_EVADED_EFFECT_COIN`） | 停止方針（未着手 9） |
| TR7 の補足（[tr7-supplemental-audit](tr7-supplemental-audit.md)） | 0.197.0・TR7@1 | 9（旧 TR6 の未着手の条件） | 9／9 | なし | なし |

- 表には、過去の監査で出た条件が今回も出たか（出た・出なかった）だけを並べます。「出なかった」から解消は推定しません。
- 過去の監査と合算しません。版・seed・対象の局が違うので、完走率の差を TR8 の効果としては扱いません。TR8 の効果は、同じ seed で集合だけを変えた比べ（RS1 の比較）で確かめた範囲だけです。

## 6. 実行の手順（次の単位。ここでは実行しない）

1. **作業の場所:** 新しい worktree と作業ブランチを、この計画のコミットから作る。
   - 実行用の worktree を `a358378` に切り離し、無視をふくめ変更 0 で、識別が序の表と同じことを確かめる。
   - 計画・キャッシュ・dry-run・対戦は切り離した `a358378` で行い、文書はブランチで書く。
2. **事前の照合:** seed の調べ直し（3 章の規則）・4 つの明示リストの検査と固定デッキの `deck_problems`・TR8 の照合値（固定値と計算値）・TR8 − TR7 が RS1 の 1 規約だけ。
3. **計画の作成と固定:** 8 つの計画を作る（CLI は下）。計画を照合し、`plan.sha256` を 8 つ、1 局目の前に記録する。
   - 照合には TR7 の補足の `check_plans_tr7s.py` の写しを使う。期待値だけを、計画名・局・seed・デッキ・規約集合・上限・実行コミットに変える。
4. **キャッシュ:** 新しい空の場所 `C:\dev\kyuura-engine-pyc-cache\c9912dd8-tbe95aa1-cpython-314-a358378-tr8a` に、同じ Python で checked-hash の pyc を準備する。準備の時間・容量はバッチ本体と分ける。
5. **外側のスクリプト:** RS1 の比較・TR6 の監査の写しを使う。逐次の実行・キャッシュの準備と照合・局の照合（`check_game.py`）・全体の予算・1 局の手順・ハッシュ・prestop の分析が対象。
   - 変えるのは、計画名と 28 局の並び、全体の予算（3,600 秒・7,200 秒・2,048 MiB）、5 章の分析（`analyze_tr8a.py`）、先行の関門だけ。
   - 差分を証跡に残す。
6. **dry-run:** 8 計画とも `use_cache` 真・容量の確認・`batch run` を呼ばないこと・計画のディレクトリが `plan.json`・`plan.sha256` だけであることを確かめる。
7. **先行の 4 局:** 1 局ずつ次の順に進める。失敗したら次を呼ばない。
   - 状態の確かめ → 残予算と空き容量 → キャッシュの照合 → `--sessions 1` → `check_game.py` → 分析 → 関門（7 章）→ キャッシュの照合
8. **本実行へ進むか:** 7 章の条件を確かめて記録してから進む。4.3 節の見通しも記録する。
9. **本実行:** 3 章の並びで 1 局ずつ（7 と同じ確かめ）。4.2 節の開始条件が満たせなければ、未着手を残して終える。
10. **終わったあと:**
    - 計画ごとの集計の作り直しを 1 回、ゲームの証跡のハッシュの不変を確かめる
    - `final_consistency.py`（局ごとの和と集計の一致）・`analyze_prestop.py`・`analyze_tr8a.py`（読み取りだけ）
    - 8 章の報告

**計画の CLI:**

- `<L67-U>` などは 2 章のファイル（`C:\dev\kyuura-engine-verification-vai\verifier\runs\…` の完全なパス）、`<HEAD>` は `a3583786cf93ee67ce95b94a5b94505f5fcef1b0` です。
- 共通の部分 `<共通>` は `--engine-commit <HEAD> --tool-commit <HEAD> --modes rules-v2 --conventions CS-KYUURA-PLAY-TR8@1 --observation --prestop-inputs --undetermined-evidence-missing continue` です。

```
python -X utf8 -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr8a-p1 --seeds 9020 --decklist0 <L67-U> --decklist1 <L67-U> --max-games 1 --budget-seconds 300 --evidence-max-mb 512 <共通>
python -X utf8 -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr8a-p2 --seeds 9020 --deck0 hitmonchan-dewgong-v2 --deck1 venusaur-parasect-v2 --max-games 1 --budget-seconds 300 --evidence-max-mb 512 <共通>
python -X utf8 -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr8a-p3 --seeds 9020 --decklist0 <P42> --decklist1 <L67-U> --max-games 1 --budget-seconds 300 --evidence-max-mb 512 <共通>
python -X utf8 -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr8a-p4 --seeds 9020 --decklist0 <LUCKY_DECK> --decklist1 <CONNECT_DECK> --max-games 1 --budget-seconds 300 --evidence-max-mb 512 <共通>
python -X utf8 -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr8a-m1 --seeds 9021 9022 9023 9024 9025 9026 --decklist0 <L67-U> --decklist1 <L67-U> --max-games 6 --budget-seconds 900 --evidence-max-mb 1024 <共通>
（m2〜m4 は p2〜p4 と同じデッキの指定で、seed・上限は m1 と同じ）
```

## 7. 先行の 4 局の確かめと、本実行へ進む条件

**先行の各局で確かめること（関門）:**

| # | 条件 |
|---|---|
| P-1 | 確定計画と識別: 実行コミットが `a358378` で、無視をふくめ変更 0。識別（エンジン・behavior・instrumentation・道具・判定の規則・形式・basis）が序の表と同じ。`plan.json` の sha256 が先行の前に記録した `plan.sha256` と同じ。計画の照合の問題 0 |
| P-2 | TR8 の一致: 計画の各局の `conventions`、`header.json`・`full_record.json` の `convention_set`、観測と送信の結果の規約集合が `CS-KYUURA-PLAY-TR8@1`・`sha256:27dfe27a…` |
| P-3 | 完了記録とハッシュ: `batch.verify_complete`（必須ファイル・ハッシュ・停止の理由の計算し直し）の問題 0。試行 1 つ・完了マーカーあり |
| P-4 | 観測・prestop・judge・replay: 観測 `complete`・問題 0。prestop の R2〜R5 の成立と対応の問題 0。判定の termination の分類が記録と同じ。既存の最終状態の replay の照合が期待どおり。anomalies なし |
| P-5 | 契約の外の記録 0: trace・actors の値に `contract_unknown`・`api_contract_unknown` 0。規約で `eligible` 偽の選択肢の選択・check・送信 0 |
| P-6 | 5 章の項目が 0.198.0 の記録で読める（`analyze_tr8a.py` が例外なく終わり、読めない形の行が 0。値が 0 なのはよい） |
| P-7 | 集計の一致: 計画の集計のカウンタ・prestop の数が局の値と同じ。`analyze_tr8a.py` の合計（試みの行・受理・拒否・`convention_applied`）が局ごとの和と完了マーカーと同じ。`convention_applied` の数が 3 つの見る人の公開ログで同じ |
| P-8 | キャッシュの不変: 中身が準備のときと同じ（各局の前後） |

**本実行へ進む条件（すべて）:**

1. 先行の 4 局で P-1〜P-8 がすべて成り立つ（計画と識別、完了記録とハッシュ、観測・prestop、judge と既存の最終状態の replay の検査、契約の外の記録 0、集計の一致、キャッシュの不変）。
2. 4.2 節の開始条件で、本実行の最初の局（m1 の 9021）を始められる。

- **進む条件に入れないもの:** 完走率・特定の停止・特定の規約の出現。先行の局が上限や未裁定で終わっても、記録と照合が成り立てば進みます。RS1・ER9・H4・T19b の規約が先行で 1 回も当たらなくても進みます。
- **進まないとき:** 1 が成り立たなければ本実行を始めず、先行の結果と原因を報告して終えます。道具・スクリプトの直しは別の単位にし、同じ計画での再実行・seed やデッキの替えはしません。

**打ち切り（先行・本実行の途中をふくむ）:**

各局で P-3〜P-5・P-7・P-8 のどれかが成り立たないとき、外側の確かめが失敗したとき、停止方針で止まったとき、開始条件の予算・容量が足りないときは、次を呼びません。未着手（呼んでいない局）と未完了（試行が `INCOMPLETE.json` で終わった局）を分けて記録し、報告します。

| 起きたこと | 扱い |
|---|---|
| 単局の上限の到達 | 局の終わり方として記録して続ける |
| `halted_known`・`input_unavailable` の終わり方 | 記録して続ける（停止方針の `continue_terminations`） |
| `no_progress` の終わり方 | 局を記録する。judge の termination が undetermined になれば、停止方針（`on_undetermined.no_progress` は stop）で計画が止まり、打ち切り |
| judge の undetermined の分類で止まるもの（`contract_unknown`・`unknown_diagnostic` など） | 停止方針のとおり止める（打ち切り） |
| prestop の上限（`capped`） | 未記録として数えて続ける |
| known_stop の拒否・`evidence_missing_stop`（答え直して続いたもの） | 記録して続ける |
| 記録の失敗・照合の不一致・ファイルの欠け・suspect・状態の不整合・replay の不一致・`api_contract_unknown`・保存の失敗・キャッシュの不一致 | 止める（異常。打ち切り） |
| 重大な例外 | 吸収しない（未完了の試行として記録して止める） |
| 残予算・空き容量の不足 | 未着手を残して終える（打ち切りとして記録） |
| `--acknowledge-stop`・unlock・予算の延長・局の追加・再試行 | 自動で使わない（別の判断） |

## 8. 実行後の報告の様式と、次の候補の選び方

**件数の表:** 予定・着手・完了・未完了・未着手を、段（先行・本実行）と条件（C1〜C4）ごとに並べます。完走率は「`game_over` の局数／着手した局数（割合）」の形で、本実行を主、先行を別の欄にします。

**表 A: 対戦が終わった条件**（5.1 節）

| 列 | 内容 |
|---|---|
| 条件 | 終わり方の分類（`game_over` 以外）と、コード（実測）・カード（観測・prestop のおもて）・候補の種類 |
| 件数 | 終わった局の数（条件 C1〜C4 ごとと計） |
| 影響した局 | 局の数・対戦の条件の数 |
| 条件を特定できた証拠 | 実測／静的照合／不明 |
| 対処に必要な判断 | 裁定の調べ（研究上の未解決）／エンジンの未対応の実装／プレイ用規約の採否／方策・道具・判定の規則の扱い |

**表 B: 複数局で実行できる手を減らした条件**（R4・R5 と 5.3 節の残った拒否。2 局以上に出たもの）

| 列 | 内容 |
|---|---|
| 条件 | 区分（R1〜R5）・候補の種類・カード（特定できたとき）・コード（実測／静的照合／不明） |
| 件数 | 延べ・取り直しを除いた延べ・局面（分母を併記） |
| 影響した局 | 局の数・対戦の条件の数 |
| 条件を特定できた証拠 | 表 A と同じ区分 |
| 対処に必要な判断 | 表 A と同じ区分 |
| 見込みの区分 | 続行や受理できる手が増える見込み／表示・診断だけが変わる見込み（下） |

- 並べ方: 表 A は終わった局の数の順、表 B は影響した局の数 → 局面の数の順。
- 先行の 4 局は別の列に示し、本実行の分母（着手した局）と混ぜません。
- ER9・H4・T19b・RS1 の欄（5.3 節）は、表 A・表 B とは別の表に、受理と残った拒否を分けて示します。RS1 は 3 段階を並べます。

**次に調査する候補（最大 3 件）の選び方:**

1. 表 A・表 B の上位から、条件（カードと場面）を特定できたものだけを選ぶ。
2. 研究上の未解決（`UNRESOLVED_…`。裁定の記録で決まらない）だけを候補にする。エンジンの未対応・記録の異常・入力 API の制約・方策や道具の扱いは別の一覧に回す。
3. 表 A に出たものを先に、次に表 B の影響した局の数の順。同じ順位なら影響した対戦の条件の数の順。
4. 各候補に**見込みの区分**を付け、2 つを分けて並べる:
   - **続行や受理できる手が増える見込み:** 規約か実装で、今は対戦が止まる・除外される・拒否される候補・選択肢・回答を受理できるようになるもの。除外の階層と、受理したあとの進み方が記録から言えるもの。
   - **表示・診断だけが変わる見込み:** 受理できる手は変わらず、理由の表示・コードの記録・候補の説明が変わるだけのもの。例: 方策がすでに外している選択肢を規約の使用不可として示す、コード不明の除外にコードを付ける。
5. 各候補に、規約の文の案ではなく、判断に要ることを書く（場面・使えない／続行の選択肢・カードの消費・既存の規約との重なり）。

**原因の特定に足りない証拠:** 原因が特定できないもの（コード不明・経路不明）は候補に採りません。候補に採る前に必要な証拠を書きます。

| 不足 | 今の記録で取れる証拠 | 足りない証拠の例 |
|---|---|---|
| 候補全体の除外・選択肢の除外のコード | 候補・選択肢の `processability`・理由、prestop の inputs のカード、本人の観測（手札・場・トラッシュ・スタジアムの使用）、分類表とソースの静的照合 | 候補の記録に停止のコードを足すエンジンの API の変更（別の単位）。それまでは静的照合のまま数える |
| prestop の段がなくカードが分からない | 候補の主体の手札・場の観測からの結び付け（観測で評価したと書く） | 段のない候補のカードを記録する道具の変更（`TOOL_VERSION` が変わる別の単位） |
| 静的照合だけで盤面を確かめていない | そのときの本人の観測（ダメージの有無・トラッシュの基本エネルギーの有無・山札の枚数） | 内部状態の直接の読み取り（公開ログと観測で決まらない値） |
| 経路が不明（ER9・H4・T19b の残った拒否） | 状態のログの、その使用の出来事（`chaos_check`・`trainer_reaction_answered`・宣言したワザ・`evade_check`） | 出来事のない経路の区別（コピーのワザの元のカードなど）は、記録にないので不明のまま |
| 方策がその手を選ぶか・受理したあとの進み方 | 方策の選択（`trace.jsonl`）と、同じ局面の後の試み | 同じ seed で集合だけを変える比べ（RS1 の比較と同じ形。別の単位） |
| `no_progress` の原因 | 直前の拒否のコード・同じ局面の試みの数・`retry_same_input` | 方策の選び直しの規則の評価（道具・方策の変更の別の単位） |

**言わないこと:**

- TR8 だけの結果から、TR7・TR6・TR3・CURRENT に対する完走率の改善を推定しません。
- 28 局から一般の頻度を推定しません。過去の監査・比較の件数と合算しません。
- 公開用の要約は件数と状態だけにします（カード ID・seed・局の識別・停止のコードを出さない）。

## 9. 実行の前に確定する値（下書きでは null）

- 実行コミット（`a358378` の完全なハッシュ）・worktree・未コミット 0・識別の測り直し
- seed の調べ直しの結果（9020〜9026 が未使用のまま）
- デッキの合法性・確認値（明示リストの content・展開・ファイルの sha256、固定デッキの展開）
- 8 つの計画の `plan.sha256`・局の並び・各局の `conventions`・`observation`・`prestop_inputs`・上限
- キャッシュの場所・準備の記録（Python の実体と版・ファイルの数・checked hash）・dry-run の `use_cache`
- 当日の出力先のドライブの空き（4,096 MiB 以上）
- 外側のスクリプトの写しの sha256 と、原本との差分
- `analyze_tr8a.py` の sha256 と、保存済みの局での読み取りの確かめの結果
- 先行の実測と、4.3 節の更新した見通し

## 10. 採用の判断が要る事項と推奨値

| 事項 | 推奨 | 別の選択 |
|---|---|---|
| 条件 | C1〜C4（旧監査と同じ） | — |
| 局 | 先行 4・本実行 24 | — |
| seed | 先行 9020・本実行 9021〜9026（規則で選んだ新しい値） | — |
| 予算 | 4.2 節 | — |
| 実行コミット | `a358378` を切り離して使う（RS1 の比較と同じ） | この計画のコミット（コードは差 0。識別は同じ） |
| 停止方針 | 既定（`no_progress` の undetermined で止める） | 続ける方針は計画の CLI を変える別の判断 |
| 規約 ID・停止のコードの記録を広げる修正 | しない（今の記録で「規約 ID 不明」「コード不明」として分けて数える） | 道具・エンジンの API が変わる別の単位 |

## 11. 失敗・未確認

- **失敗:** 読み取りのスクリプトの写しを 3 回直しました。どれも証跡の `commands.txt` に記録しています。対戦・計画の生成はしていません。
  - F1: 証跡のハッシュの写しの確かめが、名前の数を誤って数えて止まった（何も書いていない）。
  - F2: seed の調べの写しで、引き継いだ説明の行の値まで置きかえた。その行をもとにもどした（規則と処理の値は 9020）。
  - F3: デッキの調べの写しの「とうめい」の検索が改行をまたげず、持ち主を見つけなかった。直して取り直した（最初の出力は上書き）。
- **未確認（実行で分かること）:**
  - 0.198.0・TR8 での 4 条件の時間と量、記録の項目の名前が同じこと
  - 各条件の終わり方と完走率、未裁定の出現
  - ER9・H4・T19b・RS1 の規約が当たる回数と、範囲の外の経路の出現
  - RS1 の局面が新しい seed の C4 で出るか、方策がその手を選ぶか
  - 上限による終わり方
