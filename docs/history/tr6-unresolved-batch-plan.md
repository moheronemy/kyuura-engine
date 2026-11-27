# 0.196.0・TR6 の新しい seed で残る未裁定を測るバッチの計画（計画だけ）

> **履歴の記録（`docs/history/` に移した。2026-11-28）:** エンジン 0.196.0・`CS-KYUURA-PLAY-TR6@1`・`rules-v2` の監査の計画と結果。書いた時点の版・規約集合・方策の記録で、現行の仕様・既定の方策ではありません。今の状態は [README](../../README.md) の「現在の状態」、仕様は [ルールの仕様](../rules-2000-02-14.md) と [実装状況](../implementation-status.md) を参照してください。

**追記（2026-11-22）:** 8 計画を固定し、先行の 4 局（seed 9013）を実行しました。P-1〜P-8 は 4 局とも成立し、本実行へ進めると判定しました。本実行の 24 局は未着手です（12 章）。下の 0〜11 章は計画のときの本文のままです。

**追記（2026-11-22・本実行）:** 本実行は 15 局を着手・完了しました（game_over 14・no_progress 1）。C3・seed 9017 の局で停止方針によりバッチが止まり、残りの 9 局は未着手です。次に調べる候補は T19b・きずぐすりの対象・ER10 の 3 件です（13 章）。

2026-11-22。計画と文書化だけです。次のことはしていません（次の単位）:

- 確定計画（`plan.json`・`plan.sha256`）の生成、キャッシュの準備、対戦、seed 探索の対戦、judge、replay
- エンジン・検証用 AI・GUI・方策・規約・judge・版の変更

**基点と実行候補:**

- **文書の基点:** `claude/h4-tr4-tr6-compare` の `0887b1e27c5a020da8f3ecff6583d5854ebe330c`（origin と一致。main `b1e4430` には入っていない）。
- **実行の候補:** 0.196.0 の配布の固定 `7f7712acebd022ac5c9a7d5a346b89d3a2ab9690`。
  - `0887b1e` の祖先で、ふくむ公開のブランチは `origin/claude/h4-zero-v0196`・`origin/claude/h4-tr4-tr6-compare` の 2 つです。
  - `kyuura_engine`・`tools`・`tests`・`scripts`・`pyproject.toml` は `0887b1e` と差 0 です。`7f7712a..0887b1e` の 4 コミットは docs だけです。
- **作業の場所:** worktree `C:\dev\kyuura-engine-lt86`、ブランチ `claude/tr6-unresolved-batch-plan`。

**重複の確かめ（新しい計画を作る前）:**

| 調べた場所 | 結果 |
|---|---|
| 公開のブランチの名前 | TR6 の監査・新しい seed の計画にあたるものはない |
| 全公開ブランチの `docs/` のファイル名 | TR6 を名前にふくむのは H4 の比較（`h4-tr4-tr6-comparison`）と v0.196 の規約文書だけ |
| 証跡の実行フォルダ | TR6 の監査にあたるものはない |
| 保存済みの計画で `CS-KYUURA-PLAY-TR6` を持つもの | `vai-batch-h4c-tr6` だけ。これは H4 の比較で、C3 の 2 局・旧 seed 9006・9009 を使っており、新しい seed・4 条件の監査ではない |

→ 同じ監査は、計画済み・進行中・完了済みのどれでもありません。新しい計画を作りました。

**識別**（実行候補 `7f7712a` を切り離して読み取りで測った値。実行のときに測り直す）:

| 項目 | 値 |
|---|---|
| エンジン | 0.196.0・behavior `4a8edcf0…`（58 ファイル・方式 `kyuura-package-files-sha256/1`）・instrumentation `13c773a8…`（4 ファイル） |
| 道具 | `tools.verification_ai.batch`・`TOOL_VERSION` 13・digest `be95aa1e…` |
| 判定の規則 | 10 |
| 形式 | 計画 `kyuura-vai-batch-plan/7`・完了 `kyuura-vai-batch-complete/7` |
| basis | P1 `e1d389e7…`・P3 `89d12d2e…`・P2 `d652db24…`・R（0 枚の回収）`b3864eca…` |
| 規約集合 | `CS-KYUURA-PLAY-TR6@1`・固定値 `sha256:aa53bc52…`（計算し直した値と一致）・development・`halts_at_undecided`・25 規約 |
| TR6 の中身 | `CS-KYUURA-PLAY-TR4@1`（24 規約・`sha256:15af975a…`）の並びのまま、`PC-ENERGY-CONVERSION-ZERO@1` を最後に 1 つ足したもの。足した規約の照合値も固定値と同じ。検証の問題 0 |

- 上の値は、H4 の比較の実行（`vai-batch-h4c-run/out/identity_run.json`）と全項目で同じでした。照合した項目はエンジンの版・識別・道具・判定の規則・basis・集合・規約の照合値・続行の実装の一覧・既定の集合です。
- 測ったあと、作業ツリーは変更 0（無視をふくむ）、`__pycache__` 0 のままでした。
- **0.196.0・TR6 で 4 条件を回した保存済みのバッチはありません。** 時間と量は 0.194.0 の TR3 の監査（`vai-batch-tr3u1-*`）の記録から見積もり、ER9・H4 の比較の実測（0.195.0・0.196.0）で幅を確かめました（4 章）。先行の 4 局で測り直します。
- **機械可読の下書き:** [tr6-unresolved-batch-plan.json](tr6-unresolved-batch-plan.json)（`status: draft`。確定計画ではない）。
- **証跡:** `kyuura-engine-verification-vai/verifier/runs/tr6-unresolved-batch-plan/`。事前計画、識別、集合と形式、デッキの検査、seed の調べ、過去の局の時間と量、見積もりを置いています。

**目的:** TR6 を明示して選び、ルールベース AI の対戦から「次にどの未裁定を扱えば、対戦を続けられる場面や実際に選べる手が増えるか」を調べます。ER9（エネルギー回収の 0 枚）と H4（エナジーへんかんの 0 枚）の限定規約は、実装と比較が済んでいます。今回は別の seed で、残っている問題を探します。頻度や完走率を一般に推定することはしません。過去の TR3 の監査との件数の比べも、TR6 の効果としては扱いません。

## 0. 推奨案（要約）

| 項目 | 値 |
|---|---|
| 方式 | `rules-v2` だけ（方策 `rules`・`rules_version` 2・`repeat_threshold` 2・プロファイル `deep`・分布 `uniform-candidate+uniform-stage`） |
| 規約集合 | `CS-KYUURA-PLAY-TR6@1`（`--conventions` で明示） |
| 記録 | `--observation`・`--prestop-inputs`（上限は既定の 256 要求・16,384 バイト・1 MiB） |
| 停止方針 | 既定（`--undetermined-evidence-missing continue`。TR3 の監査と同じ） |
| 変異 | なし。単一のプロセス・逐次。1 局ごとに止めて確かめる |
| 対戦の条件 | 4 つ（2 章）。C1 L67-U どうし・C2 固定デッキ v2 の組・C3 P42 対 L67-U・C4 LUCKY_DECK 対 CONNECT_DECK（TR3 の本実行と同じ） |
| seed | 先行 9013、本実行 9014〜9019（3 章） |
| 局 | 先行 4（条件ごとに 1）＋本実行 最大 24（条件ごとに 6）＝最大 28 |
| 計画 | 8 つ。先行 `vai-batch-tr6a-p1`〜`-p4`（各 1 局）、本実行 `vai-batch-tr6a-m1`〜`-m4`（各 6 局）。番号は条件 C1〜C4 に対応 |
| 単局の上限 | 既定（`runner.Limits`: 操作 2000・受理 1000・番 200・120 秒） |
| 実行のコミット | `7f7712a`（完全なハッシュを `--engine-commit`・`--tool-commit` に渡す。worktree を切り離して使う） |
| 予算 | 4 章（TR3 の監査の上限をそのまま引き継ぐ） |

入れないもの:

- boundary・reach・mixed などほかの方式
- デッキの向きの入れ替え・改造、方策の変更
- 先行の結果を見た seed・デッキ・条件の差し替え、局の追加、予算の延長
- TR4・TR3・CURRENT との比べの対戦（同じ seed で集合だけを変える比べは別の単位）

## 1. 基点と実行の条件の確認

| 確かめたこと | 結果 |
|---|---|
| `0887b1e` の位置 | `origin/claude/h4-tr4-tr6-compare` と一致。main（`b1e4430`）の祖先ではない |
| `7f7712a` の位置 | `0887b1e` の祖先（`merge-base --is-ancestor` 真）。ふくむ公開のブランチは `h4-zero-v0196`・`h4-tr4-tr6-compare` |
| コードの差 | `git diff --stat 7f7712a 0887b1e -- kyuura_engine tools tests scripts pyproject.toml` は空 |
| `7f7712a..0887b1e` | 4 コミット（v0.196 の文書・設計の言い回しの直し・最後の確かめの記録・H4 の比較）。どれも docs だけ |
| 作業ツリー | 切り離しと測定のあとも変更 0（無視をふくむ）・`__pycache__` 0。測定のあとブランチにもどした |
| ER9・H4 の比較の記録 | 識別・予算の確かめの資料として使った。H4 の比較（`vai-batch-h4c-*`）の識別は上の表と同じ。ER9 の比較は 0.195.0 の記録で、時間と量の幅だけに使った |

## 2. 対戦の条件

TR3 の本実行（[tr3-unresolved-batch-plan](../tr3-unresolved-batch-plan.md) 2 章）と同じ 4 条件です。席の向き・ファイルも同じにします。

| 条件 | 主体 0 | 主体 1 | 指定 | 合法性（0.196.0） |
|---|---|---|---|---|
| C1 | 明示リスト L67-U | 明示リスト L67-U | `--decklist0/1 verifier/runs/vai-batch-d/decklists/decklist-L67-U.json` | exit 0・`legality.ok` 真・problems 空 |
| C2 | 固定デッキ `hitmonchan-dewgong-v2` | 固定デッキ `venusaur-parasect-v2` | `--deck0`・`--deck1` | `deck_problems` 空 |
| C3 | 明示リスト P42 | 明示リスト L67-U | `--decklist0 verifier/runs/p2-min-batch-plan/decklists/decklist-P42.json --decklist1 <L67-U>` | exit 0・ok・空 |
| C4 | 明示リスト LUCKY_DECK | 明示リスト CONNECT_DECK | `--decklist0/1 verifier/runs/vai-batch-d/decklists/decklist-*.json` | exit 0・ok・空 |

- **カードの版の照合:** 次の値が、TR3 の実行（`vai-batch-tr3u1-run/out/deck_profile.json`）とすべて同じでした（証跡の `out/deck_profile.json`）。
  - `batch decklist --file`（`7f7712a`）の 4 つの明示リストの `content_sha256`・展開の `sha256`・カード ID の一覧
  - 固定デッキ 4 つのカード ID の一覧と `deck_problems`
- **確認値:** L67-U `5fb91539…`・P42 `243c137f…`・LUCKY_DECK `857abd7d…`・CONNECT_DECK `6ae10e56…`（展開の sha256）。どれも 60 枚です。
- **ER9・H4・TR3 にかかわるカード**（デッキの構成。出るかどうかは対戦で決まる）:

| 条件 | ER9 のエネルギー回収（PMCG1-076） | H4 のエナジーへんかんを持つゴース（PMCG3-029） | TR3 の 3 枚（突風・ポケモンいれかえ・きずぐすり） |
|---|---|---|---|
| C1 | なし | なし | 各 2 |
| C2 | 各デッキ 2 | なし | 2〜3 |
| C3 | なし | P42 に 4 | 各 2 |
| C4 | なし | なし | なし |

- H4 の［ゆびをふる］の経路と、ER9 の範囲の外の経路は、デッキの構成からは出る見込みが小さいです。ER9 の範囲の外は錯乱ジム・サイキックコントロール・［ちえくらべ］です。出なくても測定の欠けにはしません（5.4 節）。
- 変身の力を登録したカード（PMCG3-042）は、4 条件のどのデッキにもありません。
- **引き継ぐ設定:** `rules-v2`／`deep`・既定の単局上限・観測と prestop あり・変異なし・逐次実行。

## 3. seed・局数・並び

- **調べ:** 証跡のストア 30 か所の `plan.json`・`header.json` 402 ファイルを読みました。対象は `kyuura-engine-verification`・`-vai`、GUI と旧版の検証のストアで、読めないものは 0 です（証跡の `out/seed_scan.json`）。
  - 使われた値は 106 種類でした。
  - 9000〜9200 で使われていたのは 9001〜9012 で、最大値は 9012 です。
  - 9006〜9012 は TR3 の監査で使われ、ER9・H4 の比較もその中の値を使っています。
- **規則:** 9013 から上へ、連続 7 値がすべて未使用の最初の組を選びます。先頭の 1 値を先行、残りの 6 値を本実行に使います。
  - → **先行 9013、本実行 9014〜9019**
- 実行のときに同じ規則で調べ直します。値が変わっていたら（ほかの作業で使われていたら）、実行を止めて計画を直します。その場で別の値に替えることはしません。観測の結果による seed の差し替えもしません。

**並び（固定）:**

| 段 | 局 | 順 |
|---|---|---|
| 先行 | 4 | p1（C1・9013）→ p2（C2・9013）→ p3（C3・9013）→ p4（C4・9013） |
| 本実行 | 最大 24 | seed の昇順に、seed の中で条件を回す: 9014 で m1→m2→m3→m4、9015 で m1→…→m4、…、9019 で m1→…→m4 |

- 1 回の呼び出しで 1 局（`--sessions 1`）にし、計画をまたいで上の順に呼びます。
- 予算が足りなくなったとき、未着手は並びの後ろの局（後の seed の全条件）に寄ります。
- 8 つの計画は、先行の 1 局目を始める前にまとめて作り、`plan.sha256` を記録して固定します。先行が不合格なら、本実行の計画は未着手のまま残します。

## 4. 時間・容量の見積もりと予算

### 4.1 保存済みの記録から作った見積もり

`out/budget_estimate.json` を使いました（`past_games_scan.json` の完了マーカー 326 局の読み取りと、計画・外側の台帳）。

| 記録 | 局 | 1 局の時間（attempt）の中央値・最大 | 1 局の量の最大 | 道具の累積 | 外側の実時間 | 計画のディレクトリ |
|---|---|---|---|---|---|---|
| TR3 の監査の先行（0.194.0・TR3） | 4 | C1 0.80・C2 0.44・C3 9.79・C4 9.99 秒 | 17.0 MB | 27.830 秒 | 113.170 秒 | 34,702,697 バイト |
| TR3 の監査の本実行（同上） | 24 | C1 3.76・19.94／C2 2.00・10.77／C3 11.95・30.94／C4 10.18・11.16 秒 | 44.2 MB（C3） | 238.012 秒 | 746.925 秒 | 326,794,588 バイト |
| ER9 の比較（0.195.0・C2） | 12 | 1.61・11.99 秒 | 33.7 MB | 59.409 秒 | 303.896 秒 | 111,434,202 バイト |
| H4 の比較（0.196.0・C3・TR4／TR6） | 4 | 6.80・13.09 秒 | 29.8 MB | 35.683 秒 | 119.773 秒 | 69,710,307 バイト |

- 終わり方は 4 つの記録のどの局も `game_over` でした。
- TR3 の本実行の外側の台帳は 25 行あります。手順の直しで 1 局の照合をやり直した分（[TR3 の計画](../tr3-unresolved-batch-plan.md) 13.7 節）をふくむので、局の数より 1 多くなっています。
- **見込み（参考）:** TR3 の監査の 28 局の実測は、道具 265.8 秒・外側 860.1 秒・証跡 361.5 MB でした。1.5 倍にすると道具 約 399 秒・証跡 約 542 MB で、全体の上限（道具 3,600 秒・証跡 2,048 MiB）の 11%・25% にあたります。
- **版・seed の違い:** 0.196.0・TR6 では、0 枚の答えの受理のあとに局の進み方が TR3 と分かれます。seed も新しいので、局の長さは見込みと違いえます。
  - ER9・H4 の比較では、規約を当てた側の局が 1 局で受理 360（33.7 MB）まで伸びた例がありました。
- **上側:** 1 局は単局の上限の 120 秒で終わりえます。28 × 122 秒 ＝ 3,416 秒が道具の全体の上限に入ります。量の上側の見込みは、観測ありで受理 1000 の局の約 100〜200 MB です。
- **起動と照合の費用**（H4 の比較の実測）:
  - キャッシュの準備はバッチの外で、185 ファイル・13.9 MB
  - 1 局の外側の実時間（呼び出しと照合）は 23.5〜36.1 秒
  - 集計の作り直しは 1 計画 約 2 秒

### 4.2 予算（確定値。TR3 の監査の上限を引き継ぐ）

| 項目 | 値 |
|---|---|
| 計画ごとの CLI | 先行: `--max-games 1 --budget-seconds 300 --evidence-max-mb 512`。本実行: `--max-games 6 --budget-seconds 900 --evidence-max-mb 1024` |
| 計画の中の既定 | 次の局を始める時間の余り 150 秒（`game_reserve_seconds`）・証跡の余り 64 MiB（`evidence_reserve_bytes`）・1 局の試行 3 回まで |
| 全体の道具の累積時間 | 3,600 秒（8 つの計画の台帳の `accounted_seconds_total` の和） |
| 全体の外側の実時間 | 7,200 秒（1 局の呼び出しと毎局の照合。起動・計画の生成・キャッシュの準備・最後の集計・文書は別に記録） |
| 全体の証跡 | 2,048 MiB（8 つの計画のディレクトリの合計） |
| 次の局を始める残予算（すべて） | その計画の道具の残り 150 秒以上・全体の道具の残り 150 秒以上・全体の外側の残り 600 秒以上 |
| 毎局の前に必要な空き容量（すべて） | その計画の証跡の残り 384 MiB 以上・全体の証跡の残り 384 MiB 以上・出力先のドライブの空き 4,096 MiB 以上 |

- 証跡の残りの下限は max(384 MiB, 保存済みの最大 1 局 × 1.5) とします。TR3 の監査の最大 1 局（44.2 MB）× 1.5 は 66 MB なので、384 MiB を使います。先行の局でこれを超える 1 局が出たら、その × 1.5 を下限にします。
- **予算が足りないとき:** 次の局を始めず、未着手の局を残して終えます。延長・局の追加・`--acknowledge-stop`・unlock はしません。終わり方は、バッチの停止として記録します（`stopped_budget_time`・`stopped_budget_evidence`・全体の上限での打ち切り。5.1 節）。
- 作業時（2026-11-22）の出力先のドライブ（C:）の空きは約 247.8 GB でした。実行の日の値は実行のときに測ります（下書きでは `null`）。

### 4.3 先行の実測で見積もりを更新する手順

1. 先行の 4 局のあと、各条件の先行 1 局の道具の時間・外側の実時間・量を記録する（台帳と完了マーカー）。
2. 本実行の見通しを作る:
   - 本体: 条件ごとに「先行 1 局 × 6」を足す。
   - 上側: その 1.5 倍と、TR3 の監査で本実行の実測が先行からの見通しを上回った比（道具 1.43 倍・量 1.58 倍）を当てた値も並べる。
3. 見通しを全体の残り（道具・外側・証跡）と並べて記録する。見通しが残りを超えても進む。毎局の前の残予算の確かめで、足りなくなったら未着手を残して終える。予算は変えない。
4. 先行の最大 1 局 × 1.5 が 384 MiB を超えたら、4.2 節の証跡の下限をその値にする（下げることはしない）。
5. 更新した見通しは、文書の結果の節と証跡に書く。本実行の局数・seed・並びは変えない。

## 5. 記録と集計の設計

4 つの項目を別々に数えます。0 であることや多いことを、どの項目でも合否の条件にしません。数えるのは、完了した局の試行で照合に通ったものです。未完了の試行と未着手の局は「未実行」として別に数えます。主集計は本実行の局だけで、先行の 4 局は別の列に分けます。

### 5.1 局の終了

| 分類 | 数え方 | 証拠の出所 |
|---|---|---|
| `game_over` | 局の終わり方 | `result.json` の `termination.class`・完了マーカーの `summary.judge.termination` |
| 設定の上限 | `limit_operations`・`limit_accepted`・`limit_turns`・`limit_time` を別に | 同上（`termination.detail`） |
| 対戦を終わらせた未裁定 | `halted_known` で `detail.halt.category` が `unresolved_ruling`。`diagnostic_id` を実測のコードとして数える | `result.json`・`trace.jsonl` |
| 続けられない未対応・制限 | `halted_known` のほかの分類（`unsupported` など）と、`input_unavailable`・`no_progress`。後の 2 つはコードを持たないので「不明」とし、最後の局面の候補の処理可能性を併記する | 同上 |
| 異常 | 完了マーカーの `stop`（`prestop:*`・観測の問題・`inconsistency`・`suspect`・`api_contract_unknown`・`state_integrity`・`exception` ほか）と、外側の照合の問題 | 完了マーカー・台帳・外側の照合の出力 |
| その他 | 上のどれでもない終わり方 | 同上 |

- **分母:** 始めた局。完了した局と、未完了の試行の局を合わせたものです。条件ごとと全体で出します。
- **バッチの停止は局の終わり方と混ぜずに、別に記録します:**
  - 計画ごとの台帳の `session_end` の `status`（`completed`・`stopped_budget_time`・`stopped_budget_evidence`・停止方針による停止）
  - 外側の呼び出しの終わり方
  - 全体の上限による打ち切り
  - 未着手の局の数と、未完了の試行の数（別の欄）
- 停止方針で止まる分類（`on_undetermined` の `no_progress`・`contract_unknown`・`unknown_diagnostic` など）が出た場合は、その局を記録したうえでバッチが止まります。

### 5.2 途中の拒否

| 欄 | 数え方 | 証拠の出所 |
|---|---|---|
| 送信の拒否 | `submit.outcome` が `rejected`。`verifier.engine_code`（`result.diagnostic_id`）・`category`・`continuable` ごと | `actors/<主体>.jsonl` の試みの行（`trace.jsonl` の `submit` と照合） |
| check・送信の断り | `check.response.refusal.code`・`submit.refusal.code` ごと（規約 ID の有無も） | 同上 |
| 判定の区分 | known_stop・expected・undetermined の分類ごと | `judge.json` の `rows`・`known_stop`・`undetermined` |
| **答え直して続いた拒否** | 拒否のあと、同じ（主体, position）の後の試みで、送信して受理された拒否の数 | 試みの行の並び |
| 受理されずに局が終わった拒否 | 拒否のあと、同じ局面で受理がないまま局が終わった数 | 同上・`result.json` |
| **道具が送信を抑止した試み** | 拒否のあと、同じ（主体, position）の試みで送信がない行（`submit` なし）の数。方策が選び直し、道具が送らなかったもの | 試みの行（H4 の比較の `not_submitted` と同じ定義） |

- **分母:** 送信の数（`counters.operations`）と check の数。コードごとに延べ・局面・局を並べます。
- 答え直して続いた拒否は、局の終了に数えません。5.1 節には局の最後の終わり方だけが入ります。
- 拒否が `no_progress`（同じ状態の拒否の上限）につながった局は、5.1 節の `no_progress` にも入ります。二重に数えたことを表に書きます。

### 5.3 候補・選択肢の除外

| 階層 | 数え方 | 証拠の出所 |
|---|---|---|
| 候補全体の除外 | 候補の応答で `processability` が `unresolved_ruling` の候補（理由 `stops_before_acceptance`）。種類（kind）ごと | 試みの行の `candidates.response.candidates[]`（選んだ候補は `trace.jsonl` の `candidate_class` でも照合） |
| 候補の中のカードの特定 | 上の候補の prestop の inputs の選択肢の `card_id`（おもて）・`face_down`（うら） | `prestop/inputs.jsonl`・`prestop/summary.json` |
| 取得済み入力の中の選択肢の除外 | 取得した inputs の選択肢で `processability` が `unresolved_ruling` のもの | 試みの行の `inputs.response.stages[].options[]`（prestop の inputs は別に数える） |

**単位と分母:**

| 単位 | 定義 | 分母 |
|---|---|---|
| 延べ | 候補の応答（または取得した inputs）に現れた回数 | 候補全体: 候補の応答のある試みの行の数とその候補の延べ。選択肢: 取得した inputs の数とその選択肢の延べ |
| 取り直しを除いた延べ | 同じ局面（主体, position）の 2 回目以降の試みの分を除いた延べ | 同上（取り直しを除いた行） |
| 局面 | 除外が出た（主体, position）の数 | 試みの行の局面の数 |
| 局 | 除外が 1 回以上出た局の数 | 始めた局（条件ごと・全体） |

- 選択肢の階層の分母は、取得した inputs だけです。方策が選んだ候補の inputs と、prestop の inputs が該当します。取得していない候補の選択肢は分からないので、「取得済み入力の中で」と書きます。
- **コードの 3 区分:**
  - **実測:** 同じ局面の拒否・停止の結果に出たコード。
  - **静的照合:** カードと種類から、停止の分類表（[stop-policy-classification.json](../stop-policy-classification.json)）とエンジンのソースで照らしたコード。
  - **不明:** どちらでも決まらないもの。
  - 候補と選択肢の記録には停止のコードがありません（TR3 の監査の記録の調べ）。そのため、prestop でカードを特定できても、実測のコードにはしません。
- **未記録と 0 件を分けます:**
  - 未取得: inputs を取得していない候補の選択肢。
  - 記録上限による省略: prestop の `capped`・`skipped_fetch_cap`・`skipped_bytes_cap`・`unsaved_bytes_cap`。
  - 読み取り失敗: `unsaved_failure`・`failure`・`withheld`・`refused`・`contract_unknown`・`oversize`、分析スクリプトの読めない行。
  - これらは「未記録」として数え、確認できた 0 件（「未出現」）と別の列にします。未完了の試行・未着手の局は「未実行」です。

### 5.4 規約による受理／使用不可

| 欄 | 区分 | 証拠の出所 |
|---|---|---|
| **ER9 の規約が当たった受理** | `convention_applied`（`convention` `PC-ENERGY-RETRIEVAL-ZERO`）の数と、その送信の判定（expected） | 公開ログの出来事（観測）・送信の結果・`judge.json` |
| **ER9 の残った拒否** | `UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE` の拒否。経路（錯乱ジムの「おもて」・「うら」・サイキックコントロール・［ちえくらべ］・不明）ごと | 5.2 節の拒否と、そのときの状態のログ（`chaos_check` など。[play-convention-tr4-v0.195](../play-convention-tr4-v0.195.md) 2 章の見分け方） |
| **H4 の規約が当たった受理** | `convention_applied`（`PC-ENERGY-CONVERSION-ZERO`）の数と判定。経路（元のワザ・ゆびをふる）ごと | 公開ログ・送信の結果・判定。経路は宣言したワザ・ワザを使ったポケモンのカード（[play-convention-tr6-v0.196](../play-convention-tr6-v0.196.md) 2 章） |
| **H4 の残った拒否** | `UNRESOLVED_RECOVER_ZERO_ENERGY` の拒否。経路（メタモンの［へんしん］・ほかのコピー・不明）ごと | 5.2 節の拒否と同じ局面の記録 |
| ほかの規約の出現 | `convention_applied` の規約 ID ごと（`PC-SETUP-MULLIGAN-COUNT` など） | 公開ログ |
| 規約 ID を直接確かめた使用不可 | 取得した inputs の選択肢で、`eligible` 偽かつ `convention` に規約 ID があるもの。規約 ID ごと（TR3 の 3 規約など） | 試みの行の `inputs.response.stages[].options[]` |
| 規約 ID のある断り | check・送信の断りに規約 ID があるもの | 試みの行の `check`・`submit` |
| 規約 ID が分からない使用不可 | 候補 `play_trainer` が `not_implemented`・理由 `no_eligible_card`（inputs を取得していない） | 候補の応答 |
| 入力の提示の制約 | `not_implemented` の理由ごと（`no_printed_attack` をふくむ）、`unverified` の理由ごと、`coverage.residual`、`withheld_input_candidates`、入力を作れない（`unbuildable`） | 候補の応答・`result.json` の `counters`・`metrics` |

- **受理と残った拒否は別の欄です。** 規約が当たった受理の数から、ほかの局での解消を推定しません。
  - ER9・H4 の対象の場面が出なかった（未出現）ことから、「解消した」とは言いません。
  - 範囲の外の経路が出なかったことも、測定の欠けにはしません（デッキの構成。2 章）。
- 経路を状態のログから決められないときは「不明」とし、記録にある値だけを書きます。
- 候補全体が除外されて inputs を取得していない場合は、規約 ID を直接確かめた件数に入れません。`no_eligible_card` は規約のない理由でも出るので、「規約 ID 不明」の別の列にします。

### 5.5 集計の項目と証拠の対応表

| 項目 | prestop | actors | 観測 | trace | 保存済みの判定 | ほか |
|---|---|---|---|---|---|---|
| 5.1 局の終了 | — | 最後の局面の候補（`input_unavailable` の併記） | — | 停止の結果の照合 | `judge.json` の `termination` | `result.json`・完了マーカー・台帳 |
| 5.2 拒否・答え直し・抑止 | — | 送信・check の結果とコード、同じ局面の後の試み（送信あり／なし） | — | `submit`・`check` の照合 | `rows`・`known_stop`・`undetermined` | `counters` |
| 5.3 候補全体 | 候補の inputs（カードの特定。コードなし） | 候補の応答の `processability` | 局面の結び付け | `candidate_class` | — | 分類表（静的照合） |
| 5.3 選択肢 | prestop の inputs の選択肢（別に数える） | 選んだ候補の inputs の選択肢 | — | `input_processability` | — | — |
| 5.4 ER9・H4 の受理 | — | 送信の結果（`accepted`・規約集合） | `convention_applied`・出来事の並び | — | 送信の行の判定 | 経路の見分け（状態のログ） |
| 5.4 ER9・H4 の残った拒否 | — | 拒否のコード・答え直し | 拒否の前後で見る人の観測が同じこと | `submit` | known_stop | 経路の見分け |
| 5.4 規約 ID・提示の制約 | — | 選択肢の `convention`・断り・候補の理由 | — | `scope`・`build` | — | `counters.unbuildable`・`metrics.kinds` |

- 分析は、保存済みのファイルだけを読む新しいスクリプトで行います（次の単位で作る `analyze_tr6a.py`）。
  - 標準ライブラリだけを使い、エンジンを import せず、ゲームの証跡に書きません。
  - 元にするのは、TR3 の監査の `analyze_unresolved.py` と、H4 の比較の `analyze_h4c_game.py` の答え直しと抑止の数え方です。
- 先行の前に、保存済みの局で読み取りを確かめます（出力は証跡の外）。
  - H4 の比較の TR6 の 2 局と、ER9 の比較の TR4 の 1 局を使います。
  - 受理の数・拒否の数・`convention_applied` の数が、保存済みの集計と同じになることを確かめます。
- 0.196.0 の記録で項目の名前が同じであることは、先行の 1 局目で確かめます（7 章の P-6）。

### 5.6 過去の TR3 の監査の集計（参考）

[tr3-unresolved-batch-plan](../tr3-unresolved-batch-plan.md) 13 章（0.194.0・TR3@1・seed 9007〜9012 の 24 局）の値は、表に「参考」として並べるだけです。

| 項目 | TR3 の本実行 24 局（参考） |
|---|---|
| 終わり方 | `game_over` 24 |
| 拒否 | ER9 3（C2）・H4 1（C3）。どれも答え直して受理 |
| 候補全体の除外 | `discard_from_play`（静的: `UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY`）9 局・エネルギー回収（静的: `UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET`）3 局・`use_stadium`（不明）4 局 |
| 選択肢の除外 | きずぐすりのあとの `select_pokemon`（静的: `UNRESOLVED_POTION_UNDAMAGED_TARGET`）8 局ほか |

- seed・版・規約集合が違うので、件数の差を TR6 の効果とは扱いません。TR6 の効果は、同じ seed で集合だけを変えた比べ（ER9・H4 の比較）で確かめた範囲だけです。
- 今回の表には、TR3 の監査で出た条件が今回も出たか（出た・出なかった）だけを並べます。「出なかった」から解消は推定しません。

## 6. 実行の手順（次の単位。ここでは実行しない）

1. **作業の場所:** 新しい worktree と作業ブランチを、この計画のコミットから作る。
   - `7f7712a` に切り離したとき、無視をふくめ変更 0 で、識別が序の表と同じことを確かめる。
   - 計画・キャッシュ・dry-run・対戦は切り離した `7f7712a` で行い、文書はブランチにもどして書く。
2. **事前の照合:** seed の調べ直し（3 章の規則）・4 つの明示リストの検査と固定デッキの `deck_problems`・TR6 の照合値（固定値と計算値）。
3. **計画の作成と固定:** 8 つの計画を作る（CLI は下）。計画を照合し、`plan.sha256` を 8 つ、1 局目の前に記録する。
   - 照合には `check_plans_h4c.py` の写しを使う。期待値だけを、計画名・局・seed・デッキ・規約集合・上限・実行コミットに変える。
4. **キャッシュ:** 新しい空の場所 `C:\dev\kyuura-engine-pyc-cache\b4a8edcf-tbe95aa1-cpython-314-7f7712a-tr6a` に、同じ Python で準備する。準備の時間・容量はバッチ本体と分ける。
5. **外側のスクリプト:** H4 の比較の写しを使う。逐次の実行・キャッシュの準備と照合・局の照合・全体の予算・1 局の手順・ハッシュ・prestop の分析が対象。
   - 変えるのは、計画名と 28 局の並び、5 章の分析（`analyze_tr6a.py`）、先行の関門だけ。
   - 差分を証跡に残す。
6. **dry-run:** 8 計画とも `use_cache` 真・容量の確認・`batch run` を呼ばないことを確かめる。
7. **先行の 4 局:** 1 局ずつ次の順に進める。失敗したら次を呼ばない。
   - 残予算 → キャッシュの照合 → `--sessions 1` → `check_game.py` → 関門（7 章）→ キャッシュの照合
8. **本実行へ進むか:** 7 章の条件を確かめて記録してから進む。4.3 節の見通しも記録する。
9. **本実行:** 3 章の並びで 1 局ずつ（7 と同じ確かめ）。4.2 節の残予算が足りなければ、未着手を残して終える。
10. **終わったあと:**
    - 計画ごとの集計の作り直しを 1 回、ゲームの証跡のハッシュの不変を確かめる
    - `final_consistency.py`（局ごとの和と集計の一致）・`analyze_prestop.py`・`analyze_tr6a.py`（読み取りだけ）
    - 8 章の報告

**計画の CLI:**

- `<L67-U>` などは 2 章のファイル、`<HEAD>` は `7f7712acebd022ac5c9a7d5a346b89d3a2ab9690` です。
- 共通の部分 `<共通>` は `--engine-commit <HEAD> --tool-commit <HEAD> --modes rules-v2 --conventions CS-KYUURA-PLAY-TR6@1 --observation --prestop-inputs --undetermined-evidence-missing continue` です。

```
python -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr6a-p1 --seeds 9013 --decklist0 <L67-U> --decklist1 <L67-U> --max-games 1 --budget-seconds 300 --evidence-max-mb 512 <共通>
python -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr6a-p2 --seeds 9013 --deck0 hitmonchan-dewgong-v2 --deck1 venusaur-parasect-v2 --max-games 1 --budget-seconds 300 --evidence-max-mb 512 <共通>
python -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr6a-p3 --seeds 9013 --decklist0 <P42> --decklist1 <L67-U> --max-games 1 --budget-seconds 300 --evidence-max-mb 512 <共通>
python -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr6a-p4 --seeds 9013 --decklist0 <LUCKY_DECK> --decklist1 <CONNECT_DECK> --max-games 1 --budget-seconds 300 --evidence-max-mb 512 <共通>
python -B -m tools.verification_ai.batch plan --out C:\dev\kyuura-engine-verification-vai --batch vai-batch-tr6a-m1 --seeds 9014 9015 9016 9017 9018 9019 --decklist0 <L67-U> --decklist1 <L67-U> --max-games 6 --budget-seconds 900 --evidence-max-mb 1024 <共通>
（m2〜m4 は p2〜p4 と同じデッキの指定で、seed・上限は m1 と同じ）
```

## 7. 先行の 4 局の確かめと、本実行へ進む条件

**先行の各局で確かめること（関門）:**

| # | 条件 |
|---|---|
| P-1 | 確定計画と識別: 実行コミットが `7f7712a` で、無視をふくめ変更 0。識別（エンジン・behavior・instrumentation・道具・判定の規則・形式・basis）が序の表と同じ。`plan.json` の sha256 が先行の前に記録した `plan.sha256` と同じ。計画の照合の問題 0 |
| P-2 | TR6 の一致: 計画の各局の `conventions`、`header.json`・`full_record.json` の `convention_set`、観測と送信の結果の規約集合が `CS-KYUURA-PLAY-TR6@1`・`sha256:aa53bc52…` |
| P-3 | 完了記録とハッシュ: `batch.verify_complete`（必須ファイル・ハッシュ・停止の理由の計算し直し）の問題 0 |
| P-4 | 観測・prestop・judge・replay: 観測 `complete`・問題 0。prestop の R2〜R5 の成立と対応の問題 0。判定の termination の分類が記録と同じ。既存の最終状態の replay の照合が期待どおり。異常 0 |
| P-5 | 契約の外（`contract_unknown`）の記録 0。規約で `eligible` 偽の選択肢の選択・check・送信 0 |
| P-6 | 5 章の項目が 0.196.0 の記録で読める（`analyze_tr6a.py` が例外なく終わり、読めない形の行が 0。値が 0 なのはよい） |
| P-7 | 集計の一致: 計画の集計のカウンタ・prestop の数が局の値と同じ。`analyze_tr6a.py` の合計（試みの行・受理・拒否・`convention_applied`）が局ごとの和と完了マーカーと同じ |
| P-8 | キャッシュの不変: 中身が準備のときと同じ（各局の前後） |

**本実行へ進む条件（すべて）:**

1. 先行の 4 局で P-1〜P-8 がすべて成り立つ（記録と照合に問題がない）。
2. 4.2 節の残予算と空き容量で、次の局（m1 の 9014）を始められる。

- **進む条件に入れないもの:** 特定の停止・特定の規約の出現・完走率。先行の局が上限や未裁定で終わっても、記録と照合が成り立てば進みます。ER9・H4 の規約が先行で 1 回も当たらなくても進みます。
- **進まないとき:** 1 が成り立たなければ本実行を始めず、先行の結果と原因を報告して終えます。道具・スクリプトの直しは別の単位にし、同じ計画での再実行・seed やデッキの替えはしません。

**打ち切り（本実行の途中をふくむ）:**

各局で P-3〜P-5・P-7・P-8 のどれかが成り立たないとき、外側の確かめが失敗したとき、停止方針で止まったときは、次を呼びません。未着手（呼んでいない局）と未完了（試行が `INCOMPLETE.json` で終わった局）を分けて記録し、報告します。

| 起きたこと | 扱い |
|---|---|
| 上限の到達（局の上限） | 局の終わり方として記録して続ける |
| `halted_known`・`input_unavailable`・`no_progress` の終わり方 | 記録して続ける（停止方針の `continue_terminations`）。judge の undetermined の分類で止まるものは停止方針のとおり止める |
| prestop の上限（`capped`） | 未記録として数えて続ける |
| known_stop の拒否（答え直して続いたもの） | 記録して続ける |
| 記録の失敗・照合の不一致・ファイルの欠け・suspect・状態の不整合・replay の不一致・`api_contract_unknown`・保存の失敗・キャッシュの不一致 | 止める（異常） |
| 重大な例外 | 吸収しない（未完了の試行として記録して止める） |
| 残予算・空き容量の不足 | 未着手を残して終える（正常な終わりとして記録） |
| `--acknowledge-stop`・unlock・予算の延長・局の追加・再試行 | 自動で使わない（別の判断） |

## 8. 実行後の報告の様式と、次の候補の選び方

**表 A: 対戦を終わらせた条件**（5.1 節）

| 列 | 内容 |
|---|---|
| 条件 | 終わり方の分類と、コード（実測）・カード（prestop のおもて）・候補の種類 |
| 件数 | 終わった局の数（条件 C1〜C4 ごとと計） |
| 影響した局 | 局の数・対戦の条件の数 |
| 条件を特定できた証拠 | 実測／静的照合／不明 |
| 対処に必要な判断 | 裁定の調べ（研究上の未解決）／エンジンの未対応の実装／プレイ用規約の採否／入力 API の判断 |

**表 B: 複数局で実行できる手を減らした条件**（5.3 節・5.4 節。2 局以上に出たもの）

| 列 | 内容 |
|---|---|
| 条件 | 除外の階層（候補全体／取得済み入力の選択肢）・候補の種類・カード（特定できたとき）・コード（実測／静的照合／不明） |
| 件数 | 延べ・取り直しを除いた延べ・局面（分母を併記） |
| 影響した局 | 局の数・対戦の条件の数 |
| 条件を特定できた証拠 | 表 A と同じ区分 |
| 対処に必要な判断 | 表 A と同じ区分 |
| 見込みの区分 | 受理できる回答や手が増える見込み／表示・診断だけが変わる見込み（下） |

- 並べ方: 表 A は終わった局の数の順、表 B は影響した局の数 → 局面の数の順。
- 先行の 4 局は別の列に示し、本実行の分母（始めた局）と混ぜません。
- ER9・H4 の欄（5.4 節）は、表 A・表 B とは別の表に、受理と残った拒否を分けて示します。

**次に調査する候補（最大 3 件）の選び方:**

1. 表 A・表 B の上位から、条件（カードと場面）を特定できたものだけを選ぶ。
2. 研究上の未解決（`UNRESOLVED_…`。裁定の記録で決まらない）だけを候補にする。エンジンの未対応・記録の異常・入力 API の制約は別の一覧に回す。
3. 表 A に出たものを先に、次に表 B の影響した局の数の順。同じ順位なら影響した対戦の条件の数の順。
4. 各候補に**見込みの区分**を付ける:
   - **受理できる回答や手が増える見込み:** 規約か実装で、今は除外・拒否される候補・選択肢・回答を受理できるようになるもの。除外の階層と、受理したあとの進み方が記録から言えるもの。
   - **表示・診断だけが変わる見込み:** 受理できる手は変わらず、理由の表示・コードの記録・候補の説明が変わるだけのもの。例: コード不明の除外にコードを付ける、同じ場面の別の停止に名前を付ける。
5. 各候補に、規約の文の案ではなく、判断に要ることを書く（場面・使えない／続行の選択肢・カードの消費・既存の規約との重なり）。

**原因が特定できないもの**（コード不明・経路不明）は候補に採りません。候補に採る前に必要な証拠を書きます:

| 不足 | 必要な証拠の例 |
|---|---|
| 候補全体の除外でコードが不明（TR3 の監査の `use_stadium` など） | 候補の記録に停止のコードを足すエンジンの API の変更（別の単位）、またはそのときの場の状態（トレーナーの使用の禁止・同じ名前のスタジアム）の記録と静的照合 |
| prestop の段がなくカードが分からない | 候補の主体の手札・場の観測からの結び付け（観測で評価したと書く）、または段のない候補のカードを記録する道具の変更（`TOOL_VERSION` が変わる別の単位） |
| 静的照合だけで盤面を確かめていない | そのときの状態（ダメージの有無・トラッシュの基本エネルギーの有無など）を観測で照らした記録 |
| 経路が不明（ER9・H4 の残った拒否） | 状態のログの、その使用の出来事（`chaos_check`・`trainer_reaction_answered`・宣言したワザ）の記録 |

**言わないこと:**

- TR6 だけの結果から、TR3・CURRENT に対する完走率の改善を推定しません。
- 28 局から一般の頻度を推定しません。TR3 の監査・ER9・H4 の比較の件数と合算しません。
- 公開用の要約は件数と分類・状態だけにします（カード ID・seed・局の識別を出さない）。

## 9. 実行の前に確定する値（下書きでは null）

- 実行コミット（`7f7712a` の完全なハッシュ）・worktree・未コミット 0・識別の測り直し
- seed の調べ直しの結果（9013〜9019 が未使用のまま）
- デッキの合法性・確認値（明示リストの content・展開・ファイルの sha256、固定デッキの展開）
- 8 つの計画の `plan.sha256`・局の並び・各局の `conventions`・`observation`・`prestop_inputs`・上限
- キャッシュの場所・準備の記録（Python の実体と版・ファイルの数・checked hash）・dry-run の `use_cache`
- 当日の出力先のドライブの空き（4,096 MiB 以上）
- 外側のスクリプトの写しの sha256 と、原本との差分
- `analyze_tr6a.py` の sha256 と、保存済みの局での読み取りの確かめの結果
- 先行の実測と、4.3 節の更新した見通し

## 10. 採用の判断が要る事項と推奨値

| 事項 | 推奨 | 別の選択 |
|---|---|---|
| 条件 | C1〜C4（TR3 の本実行と同じ） | — |
| 局 | 先行 4・本実行 24 | 本実行 12（条件ごとに 3） |
| seed | 先行 9013・本実行 9014〜9019（規則で選んだ新しい値） | — |
| 予算 | 4.2 節（TR3 の監査の上限） | — |
| 実行コミット | `7f7712a` を切り離して使う（H4 の比較と同じ） | この計画のコミット（コードは差 0。識別は同じ） |
| 規約 ID・停止のコードの記録を広げる修正 | しない（今の記録で「規約 ID 不明」「コード不明」として分けて数える） | 道具・エンジンの API が変わる別の単位 |

## 11. 失敗・未確認

- **失敗:** 証跡の `commands.txt` に記録しました（読み取りのスクリプトの直し）。対戦・計画の生成はしていません。
- **未確認（実行で分かること）:**
  - 0.196.0・TR6 での時間と量、記録の項目の名前が同じこと
  - 各条件の終わり方と未裁定の出現
  - ER9・H4 の規約が当たる回数と範囲の外の経路の出現
  - 上限による終わり方

## 12. 8 計画の固定と先行の 4 局（2026-11-22）

8 計画の固定と、先行の 4 局の実行・照合・進行判定を行いました。本実行の 24 局は未着手で、起動は次の単位です。製品のコード・規約・judge・GUI・版は変えていません。

- **作業の場所:** worktree `C:\dev\kyuura-engine-lt87`、ブランチ `claude/tr6a-pilot`（この計画のコミット `d25feba` から）。計画・キャッシュ・dry-run・対戦は `7f7712a` に切り離して行い、文書はブランチにもどして書きました。
- **証跡:** `kyuura-engine-verification-vai/verifier/runs/vai-batch-tr6a-run/`（確定計画の写し・開始判定・局ごとの検査・集計・失敗の記録）と、計画ごとの `vai-batch-tr6a-p1`〜`-p4`・`-m1`〜`-m4`。

### 12.1 開始前の確かめ

| 確かめたこと | 結果 |
|---|---|
| 重複 | `vai-batch-tr6a-*` の計画・実行記録・公開ブランチは、全証跡ストアに 0。新しく作った |
| 実行コミット | `7f7712acebd022ac5c9a7d5a346b89d3a2ab9690` に切り離し、無視をふくめ変更 0・`__pycache__` 0。`d25feba` の祖先で、`kyuura_engine`・`tools`・`tests`・`scripts`・`pyproject.toml` の差 0（差は docs と README だけ） |
| 識別 | 版・behavior・instrumentation・道具・判定の規則・計画と完了の形式・basis が、計画の JSON の `expected_identity` と全項目で同じ（証跡の `out/identity_check.json`） |
| TR6@1 | 固定値 = 計算し直した値（`sha256:aa53bc52…`）・25 規約・development・`halts_at_undecided`・検証の問題 0。TR4@1 の 24 規約の並びのまま `PC-ENERGY-CONVERSION-ZERO@1` を最後に足した集合 |
| デッキ | 4 つの明示リストの `batch decklist --file` は exit 0・`legality.ok` 真・problems 空。確認値と固定デッキの構成は計画のとき（`tr6-unresolved-batch-plan/out/deck_profile.json`）と同じ |
| seed | 30 ストア・402 ファイルの調べ直し（読めない 0）で、使用済みは 9001〜9012 のまま。9013〜9019 は未使用 |

### 12.2 8 計画の固定

既存の CLI（6 章の命令）で 8 計画を作り、先行の 1 局目の前に `plan.json`・`plan.sha256` の写しとハッシュを保存しました（証跡の `out/plans/`・`out/plan_sha256_all.txt`）。

| 計画 | 条件 | seed | 局 | 計画の上限 | `plan.sha256` |
|---|---|---|---|---|---|
| `vai-batch-tr6a-p1` | C1 | 9013 | 1 | 300 秒・512 MiB | `a8bb54649eca…` |
| `vai-batch-tr6a-p2` | C2 | 9013 | 1 | 300 秒・512 MiB | `095c24b136df…` |
| `vai-batch-tr6a-p3` | C3 | 9013 | 1 | 300 秒・512 MiB | `7ee6b36aaea7…` |
| `vai-batch-tr6a-p4` | C4 | 9013 | 1 | 300 秒・512 MiB | `b9a5c5569a55…` |
| `vai-batch-tr6a-m1` | C1 | 9014〜9019 | 6 | 900 秒・1,024 MiB | `365d1f36498c…` |
| `vai-batch-tr6a-m2` | C2 | 9014〜9019 | 6 | 900 秒・1,024 MiB | `7cb9f7304acf…` |
| `vai-batch-tr6a-m3` | C3 | 9014〜9019 | 6 | 900 秒・1,024 MiB | `2b87a3d1780a…` |
| `vai-batch-tr6a-m4` | C4 | 9014〜9019 | 6 | 900 秒・1,024 MiB | `0aa890178604…` |

- **計画の照合（問題 0）:** 形式 `kyuura-vai-batch-plan/7`・実行コミット・識別、局の並びと 3 つの seed、`rules-v2`（`rules`・`deep`・`uniform-candidate+uniform-stage`・`rules_version` 2・`repeat_threshold` 2）、`CS-KYUURA-PLAY-TR6@1` と照合値、既定の単局上限（操作 2000・受理 1000・番 200・120 秒）、席ごとのデッキの種類・合法性・確認値、観測あり、prestop あり（256 要求・16,384 バイト・1 MiB）、計画の上限と既定の余り、停止方針（`evidence_missing` continue ほか）。
- **TR3 の監査の計画との照らし（問題 0）:** 同じ条件の `vai-batch-tr3u1-*` と比べ、違うのは規約集合・seed（方策の seed の文字列をふくむ）・局 ID・run_id・判定したエンジンの版と識別だけでした。デッキ・席・方式・上限・観測・prestop・停止方針は同じで、変異はありません。

### 12.3 キャッシュ・dry-run・集計の手順

- **キャッシュ:** `C:\dev\kyuura-engine-pyc-cache\b4a8edcf-tbe95aa1-cpython-314-7f7712a-tr6a`（新しい空の場所）に、バッチと同じ Python で準備しました。185 ファイル・13,879,602 バイト・すべて checked hash・準備 26.8 秒（予算の外）。基準のハッシュは証跡の `raw/cache_hashes_prepared.json` です。
- **dry-run（8 計画）:** どれも `use_cache` 真・照合 7 項目が真・容量の確認 ok で、`batch run` を呼んでいません。計画のディレクトリは `plan.json`・`plan.sha256` だけのままでした。
- **集計の手順:** `analyze_tr6a.py`（TR3 の監査の `analyze_unresolved.py` に、拒否のあとの答え直しと抑止の分け方・ER9 と H4 の受理と残った拒否・P-5・P-7 の照合を足したもの）を、先行の前に保存済みの局で確かめました。
  - H4 の比較の TR6 の 2 局: 受理 346・拒否 0・試み 398・`convention_applied` 3 が、保存済みの集計と同じ。
  - ER9 の比較の TR4 の 1 局（9008）: 受理・拒否と、規約が当たった受理 2・`convention_applied` 2 が、保存済みの分析と同じ。
  - 拒否の分け方の追加の確かめとして、H4 の比較の TR4 の 2 局: 拒否 5・答え直して受理 5・送信なし 12 が保存済みの値と同じ。
  - TR4 の局は header が TR4 なので、集合の照合は偽になります（数の照合だけに使った）。出力は証跡の外に置き、照合の結果を `out/analyze_check.json` に残しました。

### 12.4 先行の 4 局

1 局ずつ C1 → C2 → C3 → C4 の順に、残予算 → キャッシュの照合 → `--sessions 1` → `check_game.py` → 分析（ER9・H4 の局の分析の写しと `analyze_tr6a.py`）→ 関門 → キャッシュの照合、と進めました。4 局とも着手・完了し、未完了・未着手は 0 です。

| 条件 | 終わり方 | 番 | 受理 | 拒否 | 試み | 局の時間 | 局の量 | 道具の累積 | 外側の実時間 |
|---|---|---|---|---|---|---|---|---|---|
| C1 | `game_over` | 32 | 121 | 0 | 141 | 2.067 秒 | 7.50 MiB | 4.524 秒 | 19.793 秒 |
| C2 | `game_over` | 37 | 137 | 0 | 168 | 2.581 秒 | 9.59 MiB | 4.983 秒 | 20.166 秒 |
| C3 | `game_over` | 52 | 137 | 0 | 150 | 2.964 秒 | 9.28 MiB | 5.439 秒 | 20.855 秒 |
| C4 | `game_over` | 63 | 202 | 0 | 263 | 4.745 秒 | 16.19 MiB | 7.577 秒 | 23.346 秒 |
| 計 | `game_over` 4 | — | 597 | 0 | 722 | 12.357 秒 | 42.56 MiB | 22.523 秒 | 84.160 秒 |

- 先行の 4 計画のディレクトリの合計は 44,788,269 バイトです（集計の作り直しの前）。
- 4 局のあと、計画ごとに集計を 1 回作り直しました（同じキャッシュ・各 約 2 秒）。ゲームの証跡のハッシュは前後で同じでした。差は派生のバイトと、一時的なロックの管理のバイト（p1 で 1 バイト）だけです。

### 12.5 関門 P-1〜P-8（4 局とも成立）

| # | 証跡との対応 | 結果 |
|---|---|---|
| P-1 | 実行コミット `7f7712a`・変更 0、`out/identity_check.json`、`out/check_plans.json`・`out/plan_vs_tr3u1.json` の問題 0、各局の前の `plan.sha256` = 固定値（`checks/pre_game_callN.json`） | 成立 |
| P-2 | 完全な記録の header が `CS-KYUURA-PLAY-TR6`・版 1・`sha256:aa53bc52…`。観測と送信の結果の集合が TR6 だけ（ER9・H4 の局の分析の `sets`）。計画の各局の `conventions` | 成立 |
| P-3 | `batch.verify_complete` の問題 0・試行 1 つ・完了マーカーあり（`checks/check_after_callN.json`） | 成立 |
| P-4 | 観測 `complete`・R2〜R5・prestop `complete`・R6 の一致と照合の問題 0（`out/final/*_prestop.json`）・判定の termination の分類が記録と同じ（`game_over`）・undetermined 0・既存の最終状態の replay の照合が期待どおり・anomalies なし・対応の問題 0・停止の理由なし | 成立 |
| P-5 | trace・actors の値に `contract_unknown`・`api_contract_unknown` 0。規約つき・`eligible` 偽の選択肢の選択・check・送信 0 | 成立 |
| P-6 | `analyze_tr6a.py` が局ごとと 4 局まとめで例外なく終わり、読めない行 0 | 成立 |
| P-7 | 集計の作り直しで counters・prestop の数が局の和と同じ（`out/final/*_final_consistency.json`）。分析の試み・受理・拒否が counters と同じ。`convention_applied` の数が 3 つの見る人の公開ログと ER9・H4 の分析で同じ | 成立 |
| P-8 | キャッシュが準備のときと同じ（dry-run のあと・各局の前後・最後。`raw/cache_*.json`） | 成立 |

判定の記録は証跡の `out/pilot_gates.json` です。

### 12.6 先行の集計（4 項目。本実行の主集計とは混ぜない）

**項目 1 局の終了:** `game_over` 4。設定の上限・対戦を終わらせた未裁定・続けられない未対応・異常は 0 でした。バッチの停止もありません（4 計画とも `completed`）。

**項目 2 途中の拒否:**

- 送信の拒否 0、check・送信の断り 0。
- 答え直して続いた拒否・受理されずに局が終わった拒否・拒否のあとに道具が送信を抑止した試みは、どれも 0 です（拒否 0 による、確認済みの 0）。
- counters の `policy_suppressed` は 7（C1）でした。拒否とかかわらない方策の抑止の延べなので、別の欄にします。`check_invalid`・`refused`・`withheld`・`retry_same_input`・`failed` は 0 でした。

**項目 3 候補・選択肢の除外:**

| 階層 | 種類・カード | 延べ／取り直しを除く／局面 | 局（条件） | コード |
|---|---|---|---|---|
| 候補全体 | `discard_from_play`（prestop の選択肢 4 つはすべてうら） | 7／4／4 | 2（C1・C3） | 静的照合: `UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY` |
| 候補全体 | `use_stadium`（prestop の段なし） | 2／1／1 | 1（C4） | 不明 |
| 取得した inputs の選択肢 | `play_trainer` のエネルギー回収（PMCG1-076） | 2／2／2 | 1（C2） | 静的照合: `UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET` |
| 取得した inputs の選択肢 | きずぐすり（PMCG1-071）のあとの `select_pokemon` | 16／16／5 | 3（C1〜C3） | 静的照合: `UNRESOLVED_POTION_UNDAMAGED_TARGET` |

- **実測のコードは 0 です。** 拒否・停止がなく、候補と選択肢の記録には停止のコードがないためです。
- **未記録と 0 件の区別:** prestop は 4 局とも `complete` で、上限・失敗による未記録は 0 でした。`use_stadium` は prestop の段がない候補なので、カード・コードとも記録の範囲の外です（未記録の欠けではない）。選択肢の階層の分母は、取得した inputs だけです。
- **静的照合の根拠**（`7f7712a` の行）:
  - うらのポケモンを場からすてる: `engine.py:2686`（FD1・`HiddenPropertyRead`）、`errors.py:51・54`。
  - エネルギー回収: `effects.py:6683・6694`。ほかの停止の経路はポケモンタワー（PT1・`effects.py:21650`）だけで、C2 のデッキにはありません。
  - きずぐすり: `effects.py:7156〜7157`（ダメージ 0 の自分のポケモンが対象の選択肢）。
  - そのときの盤面（ダメージやトラッシュの基本エネルギーの有無）は、まだ照らしていません（8 章の不足の表）。

**項目 4 規約による受理／使用不可:**

- `convention_applied` は 0 でした（ER9・H4 をふくむ）。
- ER9・H4 の 0 枚の答えは出ませんでした。規約が当たった受理 0・残った拒否 0 です。未出現なので、解消したとは言いません。
- 規約 ID を直接確かめた使用不可:
  - `PC-POTION-WITHOUT-DAMAGE@1` 7（局 2）
  - `PC-SWITCH-WITHOUT-BENCH@1` 1（局 1）
- 規約 ID が分からない使用不可（`play_trainer`・`no_eligible_card`）: 延べ 17・取り直しを除く 10・局面 10・局 3。
- 入力の提示の制約: `unverified`（`evolve`・`face_down_reveal_not_evaluated`）1、`unbuildable` 118、`coverage.residual` 0。

### 12.7 見通しの更新（4.3 節の手順）

| 見通し | 道具の累積 | 外側の実時間 | 証跡 |
|---|---|---|---|
| 本体（条件ごとに先行 1 局 × 6） | 135.1 秒 | 505.0 秒 | 268,729,614 バイト（256.3 MiB） |
| 上側（本体 × 1.5） | 202.7 秒 | 757.4 秒 | 403,094,421 バイト（384.4 MiB） |
| 上側（TR3 の監査の比: 道具 1.43・量 1.58） | 193.2 秒 | — | 424,592,790 バイト（404.9 MiB） |
| 先行のあとの全体の残り | 3,577.5 秒 | 7,115.8 秒 | 2,102,515,256 バイト（2,005.1 MiB） |

- どの見通しも全体の残りに収まります。毎局の前の残予算の確かめは、本実行でもそのまま行います。
- 証跡の残りの下限は 384 MiB のままです（先行の最大 1 局 16.19 MiB × 1.5 は 384 MiB 未満）。
- 出力先のドライブの空きは 259,443,326,976 バイト（約 247,424 MiB）でした。
- 本実行の局数・seed・並び・予算は変えていません。

### 12.8 本実行へ進めるかの判定

**本実行へ進めます。**

1. 先行の 4 局で P-1〜P-8 がすべて成り立ちました（12.5 節）。
2. m1 の 9014 を始める残予算と空き容量の確かめ（`out/budget_after_pilot_m1.json`）が ok でした。
   - 計画の残り 900 秒、全体の道具の残り 3,577.5 秒、全体の外側の残り 7,115.8 秒。
   - 計画の証跡の残り 1,024 MiB、全体の証跡の残り 2,005.1 MiB、ドライブの空き約 247,424 MiB。

- 完走率・特定の停止・ER9・H4 の出現は、条件に入れていません。
- **本実行の 4 計画（24 局）は未着手です。** ディレクトリは `plan.json`・`plan.sha256` だけで、`plan.sha256` は固定した値のままです（最後に確かめた）。起動は次の単位です。

### 12.9 失敗の記録

- **F1:** 作業前のマニフェストの照合で、最初に 27 ストアを選びました。前の単位と同じ 25 ストアで取り直しました（読み取りだけ。最初の出力は `raw/F1_*`）。
- **F2:** TR3 の監査の計画との照らしの初版が、方策の seed の文字列を除いていませんでした。8 計画とも `games` の差として出たため、除いて取り直しました（最初の出力は `raw/F2_*`）。
- **F3:** 関門のまとめの初版が、prestop の分析の R6 の形（`r6.equal`・問題の一覧）を読み違え、P-4 が 4 局とも偽になりました。分析そのものは R6 真・照合の問題 0 で、ゲームの証跡は変わっていません。読み方を直して取り直しました（最初の出力は `raw/F3_*`）。
- **F4:** `analyze_tr6a.py` の最初の作成は、シェルの引用の誤りで何も書かずに終わりました。ファイルとして書き直しました。
- 対戦の再試行・seed の替え・局の追加・上限の延長・`--acknowledge-stop`・unlock はしていません。

## 13. 本実行（2026-11-22）

文書の基点は `claude/tr6a-pilot` の `ac95483`、作業ブランチは `claude/tr6a-main`（worktree `C:\dev\kyuura-engine-lt88`）です。証跡は `verifier/runs/vai-batch-tr6a-main-run/` にあります。製品のコード・規約・judge・GUI・版は変えていません。

- **結果:** 15 局を着手し、15 局とも完了しました。そのうち 14 局が `game_over`、1 局（C3・seed 9017）が `no_progress` です。
- **打ち切り:** その C3 の局で、判定の termination が undetermined になり、停止方針でバッチが止まりました（`stopped_policy`）。7 章の打ち切りの規則で残りの 9 局は呼んでいません。
- **しなかったこと:** 再試行・`--acknowledge-stop`・unlock・seed の替え・局の追加・予算の延長。

### 13.1 開始前の確かめ

- **重複:** `vai-batch-tr6a-m1`〜`-m4` はどれも `plan.json`・`plan.sha256` だけで、未着手でした。`*tr6a-main*` のディレクトリとブランチもありませんでした。
- **実行の場所:** 実行は先行と同じ `C:\dev\kyuura-engine-lt87` を `7f7712a` に切り離して行いました。キャッシュの準備の記録が、この worktree の場所と結びついているためです（`worktree_same`）。
  - 切り離したとき、無視をふくめ変更 0、`__pycache__` 0 でした。
  - `7f7712a..ac95483` の差は docs と README だけで、コードの差は 0 です。
- **識別:** `measure_identity` と集合・形式の実測が、先行の記録（`vai-batch-tr6a-run/out/identity_7f7712a.json`・`sets_and_formats.json`）と同じでした。
  - 計画の `expected_identity` との照合（`identity_check_tr6a.py`）も全項目 ok です。対象は版・behavior・instrumentation・道具・判定の規則・計画と完了の形式・basis です。
  - TR6@1 は固定値 = 計算値で、25 規約、TR4@1 の 24 規約に `PC-ENERGY-CONVERSION-ZERO@1` を足した集合でした。
- **先行の記録:** 先行の関門は 4 局とも P-1〜P-8 が真、文書の `pilot_execution` と判定は「進める」で同じでした（`out/precheck.json`）。先行の証跡は、25 ストアのマニフェストの照合で不一致 0 です。
- **計画のハッシュ:** 本実行の 4 計画の `plan.json` の sha256 は、`plan.sha256`・先行の固定値・文書の値のどれとも同じでした（m1 `365d1f36…`・m2 `7cb9f730…`・m3 `2b87a3d1…`・m4 `0aa89017…`）。
- **キャッシュ:** 185 ファイルで、準備のときと同じでした。
- **dry-run:** 4 計画の dry-run は、どれも `use_cache` 真で、7 つの確かめが真、容量も ok でした。`batch run` は呼ばれず、計画のディレクトリは変わっていません。
- **外側のスクリプト:** 先行の写しです（`one_game_tr6m.ps1`・`run_all_tr6m.ps1`）。
  - 変えたのは、呼び出し N（1〜24）と、seed の昇順・seed の中の m1→m4 の並びの対応だけです。全体の外側の台帳も、先行と本実行の 2 つにしました。
  - 差分は `raw/*.diff` にあります。

### 13.2 実行と打ち切り

| 呼び出し | seed | C1 | C2 | C3 | C4 |
|---|---|---|---|---|---|
| 1〜4 | 9014 | game_over（6 番・受理 18） | game_over（33・95） | game_over（37・154） | game_over（63・205） |
| 5〜8 | 9015 | game_over（31・102） | game_over（29・86） | game_over（67・215） | game_over（68・199） |
| 9〜12 | 9016 | game_over（25・85） | game_over（6・28） | game_over（74・360） | game_over（51・164） |
| 13〜15 | 9017 | game_over（47・168） | game_over（65・993） | **no_progress**（44・156。拒否 1） | 未着手 |
| 16〜24 | 9018・9019 | 未着手 | 未着手 | 未着手 | 未着手 |

- **件数:**
  - 予定 24、着手 15、完了 15、未完了 0（`INCOMPLETE.json` 0）、未着手 9。
  - 計画ごとの完了: m1 4/6・m2 4/6・m3 4/6・m4 3/6。
- **毎局の確かめ:**
  - **前:** 状態の確かめ（`checks/pre_game_call*.json`）・残予算（`checks/budget_before_call*.json`）・キャッシュの 3 つを、15 回とも通りました。
  - **後:** 呼び出し 1〜14 は関門が go でした（`checks/gate_call*.json`）。
  - **呼び出し 15:** `batch run` が `stopped_policy` で終わったので、外側のスクリプトはそこで止めました（終了コード 12）。
    - 局の照合と分析は、同じ命令を読み取りだけで流しました（`scripts/post_stop_call15.ps1`）。
    - 照合: verify の問題 0、R2〜R5 真、観測 complete、replay は期待どおり、prestop complete、対応の問題 0・anomalies なし、キャッシュは不変。
    - 関門で偽になったのは、停止の理由があることと judge の undetermined の 2 つだけです。
- **停止の中身:**
  - 局の終わり方は `no_progress`（同じ局面の引き直し 64 回。`draws_per_position`）です。
  - 判定の termination は `undetermined`、完了マーカーの停止の理由は `undetermined:no_progress:1` でした。
  - 計画の停止方針（`undetermined` の `no_progress` で止める）どおりに、m3 のバッチが止まりました。LOCK はありません。
  - 4.2 節・7 章のとおり、`--acknowledge-stop` は使っていません。並びの後ろの 9 局（9017 の C4、9018・9019 の全条件）は呼んでいません。
- **最後の照合（`scripts/final_main.ps1`）:** 4 計画とも、次が成り立ちました。
  - 集計の作り直しの前後で、ゲームの証跡のハッシュが同じ。
  - `final_consistency` で、カウンタと prestop の数が局の和と同じ。
  - LOCK なし。`analyze_prestop` は完了しました。
  - 集計の作り直しの前後で `evidence.bytes.derived` などの派生の量だけが変わるのは、先行と同じです。
- **分析:** 15 局をまとめた `analyze_tr6a.py`（`out/analyze_tr6a_main.json`）は、P-5・P-6・P-7 と規約集合がすべて真でした。

### 13.3 予算の実績

| 項目 | 本実行（15 局） | 先行をふくむ全体 | 全体の上限 | 残り |
|---|---|---|---|---|
| 道具の累積時間 | 127.708 秒（m1 15.2・m2 56.3・m3 35.4・m4 20.9） | 150.231 秒 | 3,600 秒 | 3,449.8 秒 |
| 外側の実時間（毎局の game_end の和） | 351.032 秒（外側の通しは 358 秒） | 435.192 秒 | 7,200 秒 | 6,764.8 秒 |
| 証跡（計画のディレクトリ。最後の集計のあと） | 255,215,431 バイト（243.4 MiB） | 300,003,700 バイト（286.1 MiB） | 2,048 MiB | 1,761.9 MiB |

- **打ち切りの理由:** 予算ではありません。最後の確かめでも、次の局を始める条件はすべて満たしていました（`out/budget_after_main.json`）。
- **最大の 1 局:** C2・9017 の 102.6 MB（受理 993・試行 35.9 秒）です。× 1.5 でも 384 MiB 未満なので、証跡の下限は 384 MiB のままでした。
- **ドライブの空き:** 約 246,705 MiB でした。
- **先行からの見通しとの比較:** 本体（24 局）の見通しは、道具 135.1 秒・外側 505.0 秒・証跡 256.3 MiB でした。15 局の実績は、道具 127.7 秒・外側 351.0 秒・証跡 243.4 MiB です。

### 13.4 4 項目の集計（本実行 15 局が主。先行 4 局は参考）

**1. 局の終了**

| 分類 | 本実行 | 条件 | 先行（参考） |
|---|---|---|---|
| `game_over` | 14 | C1 4・C2 4・C3 3・C4 3 | 4 |
| 対戦を終わらせた未裁定（`halted_known` の `unresolved_ruling`） | 0 | — | 0 |
| 設定の上限 | 0 | — | 0 |
| `no_progress` | 1 | C3 | 0 |
| 異常（記録・照合の問題） | 0 | — | 0 |

- **`no_progress` の 1 局:** 終わり方そのものはコードを持ちません。ただし、最後の局面で実測の拒否 `UNRESOLVED_EVADED_EFFECT_COIN` があり、そのあと受理がないまま終わりました（2 と表 A）。
- **バッチの停止:** m3 の `stopped_policy` です。ほかの 3 計画は、呼び出しごとの `stopped_requested`（`--stop-after-games 1`）でした。未着手は 9 局、未完了の試行は 0 です。

**2. 途中の拒否**

| コード | 拒否 | 答え直して受理 | 受理されずに局が終わった | 道具が送信を抑止した試み | 局面・局 |
|---|---|---|---|---|---|
| `UNRESOLVED_EVADED_EFFECT_COIN`（`unresolved_ruling`・`continuable` 真） | 1 | 0 | 1 | 63（`retry_same_input` 63） | 1 局面・1 局（C3） |

- **分母:** 送信の数 3,029 です（受理 3,028 + 拒否 1）。試みの行は 3,994 です。
- **断り:** check・送信とも 0 です。
- **カウンタ:** `policy_suppressed` 176 は、拒否とかかわらない方策の抑止の延べで、別の欄です。
- **ER9・H4:** 拒否は 0 でした（4 を参照）。

**3. 候補・選択肢の除外**

| 階層 | 種類・カード | コード（区分） | 延べ | 取り直しを除いた延べ | 局面 | 局（条件） |
|---|---|---|---|---|---|---|
| 候補全体 | `play_trainer`（prestop の選択肢のカードはすべてエネルギー回収 PMCG1-076） | `UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET`（静的照合） | 26 | 17 | 17 | 3（C2） |
| 候補全体 | `use_stadium`（prestop の段なし） | 不明 | 6 | 3 | 3 | 2（C4） |
| 候補全体 | `discard_from_play`（prestop の選択肢はすべてうら） | `UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY`（静的照合） | 4 | 4 | 4 | 1（C3） |
| 取得済み入力の選択肢 | きずぐすり（PMCG1-071）のあとの `select_pokemon` | `UNRESOLVED_POTION_UNDAMAGED_TARGET`（静的照合） | — | — | 18 | 10（C1・C2・C3） |
| 取得済み入力の選択肢 | `play_trainer` の選択肢のエネルギー回収（PMCG1-076） | `UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET`（静的照合） | — | — | 8 | 4（C2） |

- **選択肢の階層の数:**
  - 局面・局は、出所の照合（`out/sources_main.json`）の値です。
  - 取得済み入力の延べは、`answer_decision` の延べ 53（18 行・10 局）と `play_trainer` の延べ 10（8 行・4 局）です。
  - 分母は、局ごとの取得した inputs の数です（`analyze_tr6a_main.json` の `denominators`）。
- **実測のコード:** 0 です。候補・選択肢の記録には停止のコードがありません。
- **静的照合:** 先行と同じ `7f7712a` のソースの行による対応で（12.6 節）、当時の盤面は照らしていません。
  - 候補全体の `play_trainer` には、prestop の inputs の選択肢がすべてエネルギー回収のとき、選択肢の階層と同じ対応を当てました。prestop のカードは `play_trainer|PMCG1-076` 24 です。
- **未記録:** prestop は 15 局とも complete で、上限・失敗による未記録は 0 です。
- **`use_stadium`:** prestop の段がない候補なので、カード・コードとも記録の範囲の外です。原因不明のままにします。

**4. 規約による受理／使用不可**

| 欄 | 本実行 | 先行（参考） |
|---|---|---|
| ER9 の規約が当たった受理（`PC-ENERGY-RETRIEVAL-ZERO@1`） | 2（1 局・C2。経路はどちらも手札からの通常の使用。判定 expected 2） | 0 |
| ER9 の残った拒否 | 0 | 0 |
| H4 の規約が当たった受理（`PC-ENERGY-CONVERSION-ZERO@1`） | 9（3 局・C3。経路はどれも元のワザ。判定 expected 9） | 0 |
| H4 の残った拒否 | 0 | 0 |
| ほかの規約の `convention_applied` | 0 | 0 |
| 規約 ID を直接確かめた使用不可（取得した inputs の `eligible` 偽） | `PC-POTION-WITHOUT-DAMAGE@1` 15（14 局面・7 局）、`PC-GUST-WITHOUT-OPPONENT-BENCH@1` 3（3 局面・1 局） | きずぐすり 7・いれかえ 1 |
| 規約 ID が分からない使用不可（`play_trainer` の `no_eligible_card`） | 96（78 局面・9 局） | 17 |
| 入力の提示の制約 | `unverified`（`use_power` の `face_down_reveal_not_evaluated`）1、`unbuildable` 726、`coverage.residual` の出現 0 | — |

- **使用の経路:** 状態のログで裏づけた範囲です。
  - ER9 は、錯乱ジム・反応の出来事がない手札からの使用でした。
  - H4 は、宣言したワザがエナジーへんかんでした（`analyze_er9c_game.py`・`analyze_h4c_game.py` の写し）。
- **言わないこと:** 範囲の外の経路は出ませんでしたが、測定の欠けにはしません。受理の数から、ほかの局での解消を推定しません。

### 13.5 表 A: 対戦を終わらせた条件

| 条件 | 件数 | 影響した局 | 条件を特定できた証拠 | 対処に必要な判断 |
|---|---|---|---|---|
| `no_progress`（直前の拒否は `UNRESOLVED_EVADED_EFFECT_COIN`） | 1（C3） | 1 局・1 条件 | **実測**（拒否のコード）。カードは本人の観測で確認 | 裁定の調べ（研究上の未解決 T19b）／プレイ用規約の採否。続けられなかったことについては、方策の選び直しの扱い（別の一覧） |

- **場面（C3・seed 9017・主体 1・局面 156）:**
  - 主体 1 のバトル場はフーディン（PMCG1-049）で、ワザ［あやしいひかり］（コインで相手をこんらん）を宣言しました。
  - 相手のバトル場はゴースト（PMCG3-030。特殊能力「とうめい」）です。ゴース（PMCG3-029）から進化していました。
  - 宣言が `UNRESOLVED_EVADED_EFFECT_COIN` で拒否されました（`continuable` 真。状態は変わらない）。
  - エンジンの理由（`effects.py:903`）: 「とうめい」が「おもて」でダメージと効果を受けないと決まったあと、効果を決めるワザのコインを投げるかは、原典（p.159・p.160・p.309・p.321）から決められない。投げるかで乱数の続きが変わる。
- **そのあと:**
  - 同じ局面で、`end_turn`・`retreat`・`play_trainer` の候補も示されていました。
  - それでも方策はワザの候補を選び続け、道具は同じ入力の送信を 63 回抑止しました（`retry_same_input`）。
  - 引き直しの上限で `no_progress` になりました。
- **判定:**
  - 拒否は `evidence_missing_stop`（`stop_condition_not_evidenced:UNRESOLVED_EVADED_EFFECT_COIN`）でした。judge の known_stop の根拠表にこのコードの項目がないためです。
  - 計画の `--undetermined-evidence-missing continue` で続き、終わり方の `undetermined` で止まりました。

### 13.6 表 B: 複数局で実行できる手を減らした条件（2 局以上）

| 条件 | 件数（延べ・取り直しを除く・局面） | 影響した局 | 証拠 | 対処に必要な判断 | 見込みの区分 |
|---|---|---|---|---|---|
| 選択肢: きずぐすりのあとの `select_pokemon` のダメージ 0 の対象 | 局面 18 | 10 局・C1〜C3 | 静的照合（`UNRESOLVED_POTION_UNDAMAGED_TARGET`） | プレイ用規約の採否（既存の設計 [play-convention-potion-target](../play-convention-potion-target.md)） | 表示・診断だけ（既存の設計の評価: 方策は未裁定の対象をすでに外し、有効な対象が残る） |
| 選択肢: `play_trainer` のエネルギー回収 | 局面 8 | 4 局・C2 | 静的照合（`UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET`） | 裁定の調べ（ER10）／プレイ用規約の採否（既存の設計 [er10](../er10-energy-retrieval-without-target-design.md)） | 規約の案しだい（下の候補 3） |
| 候補全体: `play_trainer`（選択肢はエネルギー回収だけ） | 26・17・17 | 3 局・C2 | 静的照合（同上） | 同上 | 受理できる手が増える見込み（候補そのものが使えるようになる案のとき） |
| 候補全体: `use_stadium` | 6・3・3 | 2 局・C4 | 不明 | 不明（次の調査候補にしない） | — |

- **並び:** 影響した局の数、次に局面の数の順です。
- **1 局だけのもの:** `discard_from_play`（うら。C3 の 1 局）は 1 局だけなので、この表に入れていません。13.4 節の 3 にあります。

### 13.7 次に調べる候補（3 件）

8 章の選び方で選びました。手順は、表 A を先にし、次に表 B を影響した局の数の順に並べることです。候補にしたのは、研究上の未解決で、カードと場面を特定できたものだけです。

| # | 候補 | 根拠 | 見込みの区分 | 判断に要ること | 不足する証拠 |
|---|---|---|---|---|---|
| 1 | **T19b `UNRESOLVED_EVADED_EFFECT_COIN`**（「とうめい」で受けないと決まったあとの、効果を決めるワザのコイン） | 表 A。実測の拒否 1。その局面で受理がないまま局が終わった。カード・場面は本人の観測で確認 | **受理できる回答や手が増える見込み**: 今は宣言の前に拒否されるワザが、規約のもとで受理される | 投げる／投げない（乱数の列が変わる）。既存の規約の系統の案 `PC-NULLIFIED-ELEMENT-COIN`（判断事項 DEC-NULLIFIED-COINS・状態 proposal。[play-policy-family-plan](../play-policy-family-plan.md)）と、同じ系統の 4 コード（`UNRESOLVED_PREVENTED_COIN_DAMAGE` など）との範囲の重なり。厳密モードは今のまま | 出現は 1 局だけ。受理したあとの進み方は記録にない。「とうめい」がはたらいていたこと（かがくへんかガス等で消されていないこと）は、エンジンの拒否の理由と観測から読んだだけで、別の照らしはしていない |
| 2 | **`UNRESOLVED_POTION_UNDAMAGED_TARGET`**（きずぐすりの対象にダメージ 0 の自分のポケモン） | 表 B の 1 位（10 局・18 局面・3 条件） | **表示・診断だけ**: 既存の設計（TR3 の 13 局面）では、方策はすでに未裁定の対象を外し、有効な対象が残っていた | 既存の設計の推奨案（`PC-POTION-UNDAMAGED-TARGET@1`（案）で `eligible` 偽として示す）の採否 | 今回の 18 局面の当時の盤面（ダメージ 0 であること・有効な対象が残っていたこと）は照らしていない。静的照合だけ |
| 3 | **ER10 `UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET`**（トラッシュに基本エネルギーがないときのエネルギー回収） | 表 B（候補全体 3 局・17 局面、選択肢 4 局・8 局面。C2 だけ） | 案しだい: 使えるようにする案（ER10 の設計の C）なら**受理できる手が増える見込み**、規約による使用不可で示す案（B）なら**表示・診断だけ** | 既存の設計 [er10](../er10-energy-retrieval-without-target-design.md) は現状維持（A）を推奨。今回は候補全体の除外が 17 局面あり、手札のトレーナーの候補がエネルギー回収だけのときに候補そのものが使えなかった。ER9 の 0 枚の扱い（今回 2 回受理）とそろえるか | 今回の局面の当時のトラッシュの基本エネルギーの有無は、観測で照らしていない。静的照合だけ |

**候補にしなかったもの（別の一覧）:**

| 項目 | 区分 | 理由・必要な証拠 |
|---|---|---|
| `use_stadium` の候補全体の除外（C4・2 局・3 局面） | コード不明 | prestop の段がなく、カード・コードとも記録にない。候補の記録に停止のコードを足す API の変更（別の単位）か、そのときの場の状態の記録と静的照合が要る |
| 拒否のあと方策が同じ種類の候補を選び続けた（13.5 節） | 道具・方策の扱い | `continuable` の拒否のあと、別の種類の候補（`end_turn` など）に移らず `no_progress` になった。方策の選び直しの規則は道具の変更（`TOOL_VERSION`）の別の単位 |
| judge の known_stop の根拠表に `UNRESOLVED_EVADED_EFFECT_COIN` がない | 判定の規則 | 拒否が `evidence_missing_stop` になった。判定の規則の変更は対象外（別の単位） |
| `discard_from_play` のうらのカード（`UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY`。1 局） | 1 局だけ | 表 B の条件（2 局以上）に入らない。既存の FD1 の設計がある |
| `no_eligible_card`（規約 ID 不明。96 延べ・9 局） | 規約 ID 不明 | 規約のない理由でも出るので、原因を分けられない |

- **過去の TR3 の監査との関係:** 版と seed が違うので、件数の差から TR6 の効果や完走率の改善は推定しません。
  - TR3 の監査でも出た除外は、今回も出ました: `discard_from_play`・エネルギー回収・`use_stadium`・きずぐすり。
  - TR3 の監査になかったものは 2 つです: `UNRESOLVED_EVADED_EFFECT_COIN` の拒否と、`no_progress` の終わり方。
  - TR3 の監査であった ER9・H4 の拒否は、今回は出ず、規約が当たった受理（2・9）が出ました。

### 13.8 失敗の記録

どれも、ゲームの証跡と登録済みの証跡は変えていません。

- **F1:** 外側のスクリプトの写しを作る最初の試みは、シェルの heredoc の中の `\v` などのエスケープでパスの文字列が合わず、置きかえの確かめで止まりました。何も書いていません。ファイルのスクリプト（`derive_drivers_tr6m.py`）で作り直しました。
- **F2:** `derive_drivers_tr6m.py` の初版は、`run_all` の置きかえの対象が 2 回あって確かめで止まりました。そのとき、先に書いた `one_game_tr6m.ps1` は消してから、直した版で作り直しました。
- **F3:** 本実行のまとめ（`main_summary_tr6m.py`）の初版には、2 つの誤りがありました。最初の出力は `raw/F3_main_summary_first.json` です。
  - 出所の照合の拒否の場面（`rejected|…`）を、選択肢の除外に入れていた。
  - 候補全体の `play_trainer` に静的照合の対応を当てていなかった。
- 呼び出し 15 の停止は失敗ではなく、計画の打ち切りの規則によるものです（13.2 節）。
