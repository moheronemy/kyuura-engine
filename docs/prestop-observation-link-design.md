# prestop の記録と本人向けの観測の対応づけ: 3 枚の未裁定の主な条件の事実を確かめる派生記録の設計

2026-11-15。設計・文書化だけです。実装・テスト・対戦・judge・replay・裁定の決定はしていません。`kyuura_engine`・`tools.verification_ai` は import していません（コード・文書・保存済みの JSON を文字として読み、少量の例を読み取り専用のスクリプトで確かめただけ）。→ 同じ日の追記: 4 章の派生の記録を作る読み取り専用のスクリプトを証跡の側に実装し、x1 の 4 局に当てた（L1〜L7 成立）。結果は 8 章です。0〜7 章は設計の時点の記述のままです。

- 基点: `claude/prestop-three-trainers` の `a9806d2`（origin と一致。main `b1e4430` の子孫で main に入っていない。取り込み・削除・更新はない。コードは x1 の実行コミット `6ac3d3d` と差 0）。作業は worktree `C:\dev\kyuura-engine-lt35`・ブランチ `claude/prestop-observation-link`。
- 前提: [3 枚の未裁定の整理](prestop-three-trainers.md)・[記録の設計と実装](prestop-record-design.md) 11 章・[x1 の結果](prestop-first-batch-plan.md) 9 章。
- 証跡: `kyuura-engine-verification-vai/verifier/runs/prestop-observation-link/`（事前計画・`scripts/feasibility.py`・`out/feasibility.json`）。

## 0. 結論

- prestop の各行は、**(局の試行, `episode`)** で、actors の記録の `type: "position"` の行（その行動の始めに本人が受け取った観測 `view`）に一意に結べます。x1 の 95 行すべてで、対応先は 1 つ・主体と `position` も一致しました（対応先なし・複数・矛盾は 0）。
- 3 枚の主な条件（受理の前の確かめの定義）は、どれもその観測の値だけで「成立・不成立・判定不能」に分けられます。x1 の少量の例（カードごとに 2 行・計 6）は、どれも「成立」でした。全件の評価はしていません。
- 主な条件が成立しても、それが実際の停止の原因だったとは言えません（AL2・SG1・MH1・MH2・TK1・MG1 なども止めうる）。停止コードは引き続き「記録なし・不明」です。
- 派生の記録は、**完了済みの局のディレクトリに書きません**（`files.sha256.json`・完了マーカーの照合が「表とディスクのファイルが違う」で壊れるため）。別の検証単位の下に保存します。

## 1. 対応づけの識別子と根拠

| 記録 | 持つ値 | 定義（コード） |
|---|---|---|
| prestop の行（`prestop/inputs.jsonl`） | `actor`・`position`・`episode`・`fetch`・`seq`・`candidate.content_sha256` | `runner._prestop_fetch` が `self._episode["episode"]` と `self.position` を渡す。`fetch` は記録器の中の取得の通し番号（ほかの記録にはない） |
| 本人の観測（`actors/<主体>.jsonl` の `type: "position"`） | `position`・`episode`（辞書。`episode`・`actor`・`position` など）・`view`（本人の入口の `view` の応答） | `runner._act` が、主体の行動の始めに 1 回 `view` を取り、`episode_count` を 1 増やして書く |
| エピソード（`trace.jsonl` の `type: "episode"`） | `episode`・`actor`・`position` | 同上。`episode_count` は局の中で通し（主体をまたいで一意） |

- エピソードの中では受理がありません（受理でエピソードが終わり、`position` が 1 進む）。拒否・check の不正では状態が変わらないので、同じエピソードの中のすべての取得は、エピソードの始めの観測と同じ状態です（`runner` の注記「拒否では状態が変わらないので同じエピソードのまま」）。
- 記録の順が近いことは使いません。`fetch` は actors の記録にないので、対応には使いません。

**対応を一意に決める条件**: prestop の行の (局の試行, `actor`, `episode`) で、`actors/<actor>.jsonl` の `type: "position"` かつ `episode.episode == episode` の行がちょうど 1 つあり、その行の `position == row.position` かつ `episode.actor == row.actor`。

| 状態 | 定義 | x1 |
|---|---|---|
| `linked` | 上の条件をすべて満たす | 95 |
| `no_position` | 該当の行がない | 0 |
| `multiple_positions` | 2 つ以上ある | 0 |
| `conflict` | 1 つあるが `position` か主体が合わない | 0 |
| `no_options` | 対応はあるが、prestop の行に選択肢がない（`status` が ok でない） | 0 |

- 同じ状態を複数回記録した場合: 同じエピソードの取り直しは、prestop では同じ鍵の 2 回目以降として行にならない（`repeats`）。対応先の観測は 1 つなので、重複の扱いは要りません。
- 観測を持たない行（actors の `type: "attempt"`、拒否の記録）は、対応先に使いません。
- 対応できない場合は、推測で埋めず、上の状態と理由を書いて、条件は「判定不能」にします。

## 2. 集計の単位

x1 の 53・25・2 は、カードごとの局面の数です。合計の 80 は「カードと局面の組」の数で、重なりのない局面の数とは定義が違います。

| 単位 | 定義 | x1 |
|---|---|---|
| 選択肢の延べ | 対象のカードの未裁定の選択肢（行 × 選択肢） | 突風 81・きずぐすり 44・ポケモンいれかえ 2 |
| カードと局面の組 | (カード, 局の試行, 主体, position) | 53・25・2（計 80） |
| カードをまたいで重なりを除いた局面 | (局の試行, 主体, position) | 80（x1 では 2 枚以上が同じ局面に出た例が 0。重なりがあれば組の合計より小さくなる） |
| 同じ局面の行 | 同じ局面の prestop の行の数（候補の中身が違えば別の行） | 最大 2 |
| 同じ局面の取り直し | 同じ局面・同じ候補の内容の取得の延べ − 1 | prestop の要約の `repeats` は種類・カードごとでないので、派生の記録では actors の `attempt` の候補の応答から数える（4 章） |

## 3. 3 つの主な条件と、観測から確かめられること

条件は既存の受理の前の確かめ（`effects.py` の `check_playable`）の定義のままです。カードの文面から別の条件を作りません。

| カード | 受理の前の確かめの定義 | 観測の項目（本人の `view.observation`） | 成立 | 不成立 | 判定不能 |
|---|---|---|---|---|---|
| きずぐすり | `not any(p.damage > 0 for p in 本人の in_play())`（in_play はバトル場とベンチ） | `players[actor].active.damage` と `players[actor].bench[*].damage` | バトル場があり、バトル場とベンチのすべてに `damage` があり、どれも 0 | どれか 1 つでも `damage` が正 | バトル場がない・`damage` のない項目がある・形が違う |
| ポケモンいれかえ | `not 本人の bench` | `players[actor].bench` の長さ | 並びで長さ 0 | 並びで長さ 1 以上 | 並びでない |
| 突風 | `not 相手の bench` | `players[1-actor].bench` の長さ | 並びで長さ 0 | 並びで長さ 1 以上 | 並びでない |

- 観測が範囲を覆っているか: 本人の場のポケモンは、バトル場とベンチの全部が観測に出て、それぞれ `damage` を持ちます。本人のうらのカード（マチスの秘策）も `face_down` で出て、`damage` を持ちます（うらのあいだは 0。エンジンの状態の値と同じ）。相手の場のベンチは、番 1 以降は全員分が並びで出ます（番 0 の対戦準備では `{"face_down": true}` だけの項目ですが、並びの数は残る。トレーナーは番 1 以降なので当たらない）。
- 「ダメージのあるカードが見えない」ことだけで成立とはしません。成立は、バトル場とベンチの**すべての項目に `damage` の値がある**ことを確かめたときだけです。
- 使うのは、その時点までに本人へ届いた観測の値だけです。完全な記録・`real`・後の状態・既知のデッキ・他者の非公開の記録から補いません（`real` は本人のうらの本当のカードで、条件には使わない）。
- **原因の特定はしない**: 主な条件が成立していても、同じ候補の作成で AL2・SG1・MH1・MH2・TK1・MG1 なども止めうるので、実際の停止の原因とは言えません。逆に、主な条件が不成立なら、ほかの条件で止まったことを示しますが、どれかは決めません。今回はそれらの条件の判定には広げません。
- 停止コードは「記録なし・不明」のままです。静的なコードの候補を、実行時のコードに置き換えません。

## 4. 派生の記録の仕様（検証者用）

**置き場所**: 元のバッチ（`verifier/runs/<batch>/`）の外。`verifier/runs/<分析の単位>/derived/<batch>/` に置きます。元の局のディレクトリ・計画・台帳・完了マーカー・集計は変えません。

**ファイル**

| ファイル | 中身 |
|---|---|
| `link.jsonl` | 1 行 = (局の試行, prestop の行の `seq`, 選択肢の `id`) の 1 つ（対象の 3 枚の未裁定の選択肢だけ） |
| `summary.json` | `link.jsonl` だけから計算した件数（下） |
| `inputs.json` | 入力のファイルごとの相対パスと sha256（prestop の行・actors・trace・result・完了マーカー） |

**`link.jsonl` の 1 行**（形式 `kyuura-vai-prestop-link/1`。キーは辞書の順・区切りなしの JSON・LF）:

| 項目 | 内容 |
|---|---|
| `format` | `kyuura-vai-prestop-link/1` |
| `attempt` | 局の試行のディレクトリ（`games/<局>/attempt-<n>`。検証者用。公開用には出さない） |
| `row` | `{"seq", "line_sha256"}`（prestop の行の通し番号と、その行のバイトの sha256） |
| `option` | `{"id", "condition_key"}`（選択肢の `id` と、条件の鍵 `potion_without_damage`・`switch_without_bench`・`gust_without_opponent_bench`。カード ID は複製しない。行の参照から引ける） |
| `state` | `{"actor", "position", "episode"}` |
| `link` | `{"status", "actors_file", "line", "line_sha256"}`（状態は 1 章の 5 つ。対応先の actors の行番号とその行の sha256。対応しないときは行番号と sha256 を `null`、理由を `reason` に） |
| `facts` | きずぐすり: `{"own_field_items", "damage_present", "damage_positive"}`、ポケモンいれかえ: `{"own_bench_count"}`、突風: `{"opponent_bench_count"}`。どれも件数だけ（カード・名前・`real` を写さない） |
| `refs` | 参照した観測の項目のパス（例 `view.observation.players[1].bench`） |
| `condition` | `{"result": "holds"・"not_holds"・"undetermined", "reason"}` |
| `stop_code` | 常に `"not_recorded"` |
| `cause` | 常に `"not_determined"`（条件の成立を停止の原因に読み替えない） |

**同じ局面の取り直し**: `summary.json` の `retakes` は、actors の `type: "attempt"` の候補の応答の中で、同じ (主体, position) に同じ `content_sha256` の候補が出た回数 − 1 を、局面とカードの組ごとに数えます。その合計と prestop の要約の `repeats` の照合は種類ごとにはできないので、「局の `repeats` 以下」だけを確かめ、合わなければ `retakes_unverified` とします（範囲が空で止まった取得は actors に書かれないため）。

**`summary.json`**（`link.jsonl` だけから。種類の集合を 1 回だけたどる）:

- `options_by_condition`・`card_state_pairs`（条件ごと）・`distinct_states`（条件をまたいで重なりを除く）・`states_with_two_or_more_conditions`
- `link_status`（5 つの状態ごと）・`condition_result`（条件ごとに holds・not_holds・undetermined）・`undetermined_reasons`
- `retakes`（条件ごとの合計）・`retakes_unverified`
- `stop_code`: `"not_recorded"` の 1 つだけ

**順と重複**: 行は (局の試行, `row.seq`, `option.id`) の順。同じ組は 1 行だけ（2 回目があれば作成を止める）。

**失敗の扱い**: 入力のどれかが読めない・JSON が壊れている・prestop の要約の照合（`prestop.reconcile`）が空でない・完了マーカーの照合が通らない、のどれかがあれば、何も書かずに止めます（一時ファイルに書いて最後に入れ替える）。形の知らない観測は止めずに `undetermined`（理由つき）にします。

## 5. 受け入れ条件（次の実装の単位）

| # | 条件 |
|---|---|
| L1 | 同じ入力（`inputs.json` の sha256 が同じ）から、同じ `link.jsonl`・`summary.json`（バイトまで同じ）になる |
| L2 | `no_position`・`multiple_positions`・`conflict`・`no_options` と `undetermined` を、`linked`・`holds`・`not_holds` に混ぜない（件数を別に出す） |
| L3 | `options_by_condition` が、x1 の既存の集計（突風 81・きずぐすり 44・ポケモンいれかえ 2）と同じ。`card_state_pairs` が 53・25・2、`distinct_states` は組の合計以下で、差が `states_with_two_or_more_conditions` から説明できる |
| L4 | すべての行の `stop_code` が `not_recorded`・`cause` が `not_determined`。文書・要約に「停止の原因」「裁定」と読める語を書かない |
| L5 | 実行の前後で、元のバッチのすべてのファイルの sha256・`batch.verify_complete` の結果・完了マーカー・集計が同じ（派生の記録は元のバッチの外） |
| L6 | 公開用の要約は件数と分類だけで、seed・局の識別・uid・カード ID・非公開の選択肢・`real` の値をふくまない（禁止語の確かめを通ってから書く） |
| L7 | 条件の評価は対応した本人の観測の値だけで行い、`real`・完全な記録・後の状態を読まない（読み込むファイルの一覧を `inputs.json` に固定し、`full_record.json` をふくめない） |

**テストの設計**（今回は追加・実行しない）: 人工の小さな記録で、(1) 対応 1 つ・なし・複数・`position` の不一致・主体の不一致、(2) きずぐすりで `damage` が全部 0・1 つ正・`damage` の欠け・バトル場なし・本人のうら（`face_down` で `damage` 0）、(3) ベンチが空・1 匹・並びでない、(4) 同じ局面に 2 枚の条件が出る（重なりを除いた数が組の合計より小さい）、(5) 同じ入力で 2 回作って同じバイト、(6) 入力が壊れているときに何も書かない、(7) 公開の要約に禁止語がない。実際の x1 の 4 局では L1〜L7。

## 6. 確かめた例（x1。少量）

- 対応: 95 行すべて `linked`。エピソードは 4 局で 687・重複 0。
- 単位: 選択肢 81・44・2、組 53・25・2、重なりを除いた局面 80（重なり 0）、同じ局面の行は最大 2。
- 条件の例（カードごとに最初の 2 行）: 突風 2・ポケモンいれかえ 2・きずぐすり 2 が、どれも `holds`（相手・本人のベンチが空、本人の場の `damage` がすべて 0）。原因の特定ではありません。

## 7. 失敗・未確認・次の単位

- 失敗: なし（確かめのスクリプトは 1 回で exit 0）。
- 未確認: 全件の条件の評価（今回はしていない）、`retakes` の数え方の実際の値、`not_holds` が出た場合の扱いの例（例に出ていない）、x1 以外のバッチ（旧記録は prestop がない）。
- 次の最小の単位: 4 章の派生の記録を作る読み取り専用のスクリプト（検証者の側。エンジン・検証用 AI は変えない）を、x1 の 4 局に当てて L1〜L7 を確かめる。

## 8. x1 の 4 局への適用の結果（2026-11-15）

読み取り専用のスクリプトを実装し、x1 の完了済みの 4 局に当てました。エンジン・検証用 AI・GUI・API・版・形式・方策は変えていません。対戦・seed の探索・judge・replay はしていません。

- 基点: `claude/prestop-observation-link` の `ba70c25`（origin と一致。main `b1e4430` の子孫で main に入っていない。コードは x1 の実行コミット `6ac3d3d` と差 0）。作業は worktree `C:\dev\kyuura-engine-lt36`・ブランチ `claude/prestop-link-apply`（文書だけ）。
- 証跡: `kyuura-engine-verification-vai/verifier/runs/prestop-link-apply/`（事前計画・`scripts/prestop_link.py`・`scripts/tests/test_prestop_link.py`・`scripts/acceptance.py`・`derived/vai-batch-x1/`・`derived_repeat/vai-batch-x1/`・`out/`・`commands.txt`）。公開用は `public/runs/prestop-link-apply/summary.json`（件数と分類だけ）。

### 8.1 実装（4 章の仕様からの違いをふくむ）

- 標準ライブラリだけです。`kyuura_engine`・`tools.verification_ai` は import しません。入力は引数で明示した局の試行だけで、各試行で読むのは `COMPLETE.json`・`files.sha256.json`・`prestop/inputs.jsonl`・`prestop/summary.json`・`actors/0.jsonl`・`actors/1.jsonl` の 6 つだけです。読み込みは 1 つの読み手を通り、`full_record` の名前のファイルは読む前に拒否します。
- **入力の照合**: 4 章は「`prestop.reconcile` が空でない」なら止める、としていました。import しないので計算し直さず、完了のときに記録された `summary.prestop_problems` が空であることと、ファイルが変わっていないこと（`files.sha256.json` の sha256 が完了マーカーの `files_table_sha256` と同じで、読んだ 4 つのファイルの sha256 が表と同じ）で確かめます。どれかが合わない、JSON が壊れている、のどれかなら、何も書かずに終了コード 2 で止めます。
- **読む範囲**: 4 章の `inputs.json` の例には trace・result もありました。対応づけと条件の評価に要らないので読みません。`inputs.json` には、実際に読んだファイルの相対パスと sha256 だけを書きます。
- **対応**: 1 章の条件に、観測の `view.viewer` が主体と同じことを加えました（違えば `conflict`）。
- **条件の評価**: 3 章の定義のままです。`damage` は 0 以上の整数だけを値として読みます（真偽値・文字列・負の数は不正値）。きずぐすりは、正の `damage` が 1 つでも見えれば不成立、そうでなく欠けや不正値があれば判定不能、バトル場がなければ判定不能、ベンチが並びでなければ判定不能です。`players` の並びの `player` が 0・1 の順でなければ、3 つとも判定不能です。
- **行**: `option` が null の行は、prestop の行の `status` が ok でないときに 1 行だけ書きます（`no_options`。どのカードかは記録にない）。`row` には `seq`・`line_sha256` に加えて、元の行番号 `line` も書きます。`attempt` は `games/<局>/attempt-<n>` です。
- **取り直し**: 行ごとに、`actors/<主体>.jsonl` の `type: "attempt"` のうち、同じ `position` で候補の応答に同じ `content_sha256` の候補が出た回数を数えます。その回数 − 1 を取り直しとし、0 回なら不明（null）とします。局の中で、全部の行の合計が `prestop/summary.json` の `repeats` 以下で、かつ不明が 0 なら `within_repeats`、そうでなければ `unverified` です。`repeats` をカードに配分しません。`summary.json` の `retakes` は条件ごとに行の単位で足し、選択肢の数は掛けません。
- **出力**: `link.jsonl`・`summary.json`・`inputs.json` を一時のディレクトリに書きます。読み直して同じバイトかを確かめてから、名前を変えて確定します。出力先がすでにあれば、終了コード 3 で拒否します。失敗のときは一時のディレクトリを消し、何も残しません。`summary.json` は、書く `link.jsonl` のバイトを読み直して計算します。時刻・絶対パス・乱数・カード ID は書きません。

### 8.2 人工の入力の限定テスト

`scripts/tests/test_prestop_link.py`（unittest・30 件）はすべて通りました（`out/unittest.txt`）。調べた場合は次のとおりです。

- 3 条件それぞれの成立・不成立・判定不能
- `damage` の欠け・文字列・真偽値・負の数、バトル場なし、ベンチが並びでない、`players` の形・並び順の違い
- 本人のうら（`face_down` で `damage` 0・正、`damage` なし）
- 対応なし・他の主体の記録を使わないこと・複数・`position`・主体・`viewer` の不一致・選択肢なし
- 1 行に 2 つの選択肢、同じ局面に 2 つの条件（組 3・局面 2・重なり 1）、取り直し（2 回目・不明・`repeats` を超える）
- 壊れた JSON（1 局目・2 局目）・ハッシュの不一致・表の不一致・`prestop_problems` が空でない・試行の重複
- いずれも出力を残さないこと、既存の出力先の拒否（中身を変えない）
- 2 回の生成のバイト一致、LF・絶対パス・カード ID の不在、`summary.json` が `link.jsonl` だけから計算されること、`full_record` の拒否

### 8.3 x1 の結果

| 項目 | 生成した値 | 既存の値（照合先） |
|---|---|---|
| 行 | 127（4 局） | — |
| 選択肢の延べ | 突風 81・きずぐすり 44・ポケモンいれかえ 2 | 81・44・2（x1 の集計・実現可能性の確かめ） |
| カードと局面の組 | 53・25・2（計 80） | 53・25・2（計 80） |
| 重なりを除いた局面 | 80（2 つ以上の条件が出た局面 0） | 80（0） |
| 対応の状態 | `linked` 127・ほかの 4 つ 0 | 95 行すべて対応（実現可能性の確かめ） |
| 取り直し | 突風 5・きずぐすり 6・ポケモンいれかえ 0（不明 0・`unverified` 0） | 局ごとの `repeats` 5・1・0・8（計 14）以下 |

件数は生成の側に固定値を入れずに求め、既存の 2 つの集計と同じでした。差はありません。取り直しは、対象の 3 枚の行（80 行）の合計が局ごとに 4・1・0・6（計 11）で、どの局でも `repeats` 以下でした。残りの 3 は、対象の外の行（`discard_from_play` など）の取り直しと考えられますが、内訳は数えていません。対象の行のうち、取得が 2 回の行が 15、1 回の行が 112 でした（選択肢の行の単位）。

| 条件 | 成立 | 不成立 | 判定不能 |
|---|---|---|---|
| 突風（相手のベンチが空） | 81 | 0 | 0 |
| きずぐすり（本人の場の `damage` がすべて 0） | 44 | 0 | 0 |
| ポケモンいれかえ（本人のベンチが空） | 2 | 0 | 0 |

- きずぐすりの 44 は、本人の場が 6 匹の行が 41、5 匹の行が 3 で、どれも `damage` の値がそろって 0 でした。
- 3 つの主な条件は、x1 ではすべての選択肢で成り立っていました。ほかの条件（AL2 など）も成り立っていたかは調べていません。どの条件で止まったかは決めていません。停止コードは `not_recorded`、`cause` は `not_determined` です。

### 8.4 受け入れ条件

| # | 結果 | 根拠（`out/acceptance.json`） |
|---|---|---|
| L1 | 成立 | 別の出力先（`derived/`・`derived_repeat/`）へ 2 回作った 3 ファイルがバイトまで同じ（`link.jsonl` `486ae1af…`・`summary.json` `965a85bc…`・`inputs.json` `141d6bf0…`） |
| L2 | 成立 | 状態ごとの件数を別に出す。`linked` 以外の行で結果が判定不能でないものは 0。状態の合計 = 行の数、結果の合計 = 選択肢の数 |
| L3 | 成立 | 8.3 の表。組の合計 − 局面 = 0 = 重なりの局面の数 |
| L4 | 成立 | すべての行が `not_recorded`・`not_determined`。要約と理由の文字列に該当の語はない |
| L5 | 成立 | 元のバッチの `games/` の 76 ファイルの sha256 が前と同じ（変更・追加・削除 0）。`plan.json`・`ledger.jsonl`・`aggregate.json` も同じ。4 局の完了マーカーの表の sha256 と表の 17 ファイルが一致し、`prestop_problems` は空、`stop` は空。派生の記録はバッチの外 |
| L6 | 成立 | 公開の要約は禁止語の確かめを通ってから書いた（seed・局の識別・uid・カード ID・カード名・試行・`real`・絶対パスなし） |
| L7 | 成立 | `inputs.json` は 4 局 × 6 ファイル = 24 で、上の一覧と同じ。`full_record` をふくまない。`refs` はすべて `view.observation.` の項目 |

- L5 の完了の照合は、`batch.verify_complete` を import しない形で、ファイルの不変の部分（表と各ファイルのハッシュ）だけを確かめました。ハッシュを取るため、`full_record.json` もバイトとしては読んでいます（内容は使わない）。対応づけのスクリプトは読みません。

### 8.5 失敗・修正・未確認

- 失敗 1: 最初の実行（終了コード 2・出力なし）は、完了マーカーと表そのものを表と照合していたためです（2 つは表にない）。照合を、表にある 4 つに直しました。止め方は仕様どおりでした。
- 失敗 2: テストの補助が、1 つのテストの中で同じ出力先を使い回していました（7 件のエラー）。テストの側を直しました。スクリプトは変えていません。
- 修正: 設計と照らして、`attempt` の書き方（根からのパス → `games/<局>/attempt-<n>`）と `retakes_unverified` の欠けを直しました。直す前の版で作った出力は `superseded/derived-script-v1/` に残しています（使っていない）。名前が重なる試行は、拒否するようにしました。
- 設計と保存形式の矛盾: ありません（違いは 8.1 のとおりで、どれも記録した）。
- 未確認: 対象の外の行の取り直しの内訳（残りの 3）、`not_holds`・判定不能が実際の記録に出た場合（x1 では 0）、x1 以外のバッチ（旧記録には prestop がない）、ほかの条件の判定。
