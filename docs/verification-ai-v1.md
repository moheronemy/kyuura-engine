# 検証用 AI の V1（ランダムの分布と到達範囲の計測）

[仕様](verification-ai-design.md)・[実装計画](verification-ai-implementation-plan.md) の V1 を実装しました。目的は、検証用 AI のランダムの選択の分布と、到達範囲・選択の過程を
測れるようにすることです。ルールの方策・混合の方策（V2）、`boundary`・`negative`（V3）、双子（V4）は実装していません。V0 の内容は [verification-ai-v0.md](verification-ai-v0.md)。

## 1. 基点と範囲

| 項目 | 値 |
|---|---|
| 基点 | `claude/verification-ai-v0` の `2b5f556`（V0 の最後。`kyuura_engine` は `e26df79`（0.172.0）と同じ） |
| ブランチ | `claude/verification-ai-v1`（worktree `C:\dev\kyuura-engine-vai`） |
| 実行したコミット | `5d5e04e0adbc71ce2152bed6e8a2e608ed048f5c`（`behavior_digest` `07a189c9…6c18`） |
| 変えていないもの | `kyuura_engine`（エンジン本体）・GUI・renderer・カードデータ・固定デッキ・規約集合・識別の方式。V0 の段ごとの方式の選び方（乱数の使い方を含む） |

## 2. 判断の整理

| id | 事項 | 状態 | 中身 |
|---|---|---|---|
| D-1 | 実装の基点 | 承認済み（V0） | 設計と U7-5f・U7-5g を含む公開のコミットから作る。`main` への取り込みを待たない |
| D-2 | コードの置き場所 | V0 の暫定 → V1 で推奨案のまま続ける（実装の判断） | 配布物の外の `tools/verification_ai/` |
| D-3 | 操作の層 | 承認済み | `client_api` の JSON の入口 |
| D-4 | CN-1 | 道具の側は承認済み（V0）。エンジンの側は独立の課題（5 章。今回は扱わない） | `RecordingGame` が実際の failure を伝える対応を維持 |
| D-5 | ランダムの分布 | V1 で承認（利用者の指示） | 既定は `uniform-candidate+uniform-stage`（V0 と同じ）。`uniform-candidate+uniform-tuple` を加える（3 章） |
| D-6 | 拒否を異常の候補にする種類の表 | V0 の暫定を維持。種類ごとの表は保留 | V0 と同じく `supported` の拒否だけを異常の候補にする。種類ごとの受理の保証の読み方は、U7 の公開の契約の解釈に関わるので保留 |
| D-7 | 混合の単位 | 今回扱わない（V2）。V2 で選択のエピソードごとに決めた（[verification-ai-v2.md](verification-ai-v2.md) 4 章） | — |
| D-8 | 準備で両方が操作する場面の順 | V0 の暫定。再現用の既存の条件として維持 | 0 → 1 の決まった順。ゲームの合法性の判断ではない |
| D-9 | ジャンケンの勝者 | V0 の暫定。再現用の既存の条件として維持 | ホストの乱数で均等。ゲームの合法性の判断ではない |
| D-10 | 証跡の置き場所 | 承認済み（V0） | `C:/dev/kyuura-engine-verification-vai/`。V1 の実行は V0 と別のディレクトリ |
| D-11 | 上限 | 操作・受理・番・時間は承認済み（V0）。組の列挙の上限 4,096 は V1 で承認 | 同じ状態の拒否 16・選び直し 64（V0 の実装の判断）と、途中の部分の入力の上限 65,536（V1 の実装の判断）は暫定のまま使う |
| D-12 | デッキと規約集合の組 | V1 の範囲は利用者が決めた（固定デッキ・既定の規約集合）。広い組は今回扱わない | — |

V1 で決めた実装の判断（推奨案を基にしたもの。公開の契約・情報境界・合法性の責任は変えない）:

- `uniform-tuple` の並びの扱い（3.2 節）と、`order` のない 2 個以上の段は並びを数えること
- 列挙の途中の部分の入力の上限 65,536（組が少なくても、途中の並びが多すぎる段で止まらないため）
- 前に試した組をまた選んだときは、V0 と同じく選び直す（列挙から外さない）
- V1 の実行の seed は 11・12・13（V0 の seed 1 と重ねない。ゲーム・方策・ホストの seed を同じ値にする）

## 3. 分布の定義

どちらの分布も、候補の選び方は同じです: 範囲の中の候補（API の並びのまま）から、方策の乱数で均等に 1 つ。範囲の規則は V0 の `deep`（[V0 の 3.3 節](verification-ai-v0.md)）。
どちらも、全候補を通した完成した操作の全体の均等な分布ではありません。

### 3.1 `uniform-candidate+uniform-stage`（既定。V0 と同じ）

段の順に、次の手順で選びます（各手順の「均等」は方策の乱数の `randrange` 1 回）。

| 段 | 手順 |
|---|---|
| `choose_value` | 範囲 `min`〜`max` の整数から均等に 1 つ（値が 1 つでも 1 回引く） |
| `choose_option` | 1. 選ぶ数 k の並び `count.min`〜`min(count.max, 許される選べるものの数)` を作り、2 つ以上なら均等に 1 つ（1 つなら引かない）。2. 残りの選べるものから 1 つずつ k 回、重ならずに均等に選ぶ（残りが 1 つでも引く）。選んだ順がそのまま送る並び |
| 任意の段（`count.min` が 0） | 省く（k = 0）は k の並びの 1 つ。たとえば 0〜1 の段は、省く確率が 1/2 |
| 並び | `order` の区分によらず、k 個の並びは均等な順（段の区分が `not_significant` でも並べかえを区別しない分布になる。k 個の組そのものは、k のもとで均等） |
| `total_units` の段 | `units` の合計が範囲に入る組を数え上げ（上限 4,096）、その組がある k の中から均等に k、k の組の中から均等に組（2 つ以上なら）、組の中の並びを均等な順 |
| 依存する段 | `options_by_choice`・`upstream_stages`/`after`・`options_by_path`・`options_from_stage` で、前の段の選び方のもとで許される選べるものだけを並べる（[V0 の 3.2 節](verification-ai-v0.md)） |

### 3.2 `uniform-candidate+uniform-tuple`（V1）

1. 候補を均等に選ぶ（上と同じ）
2. その候補の、契約の上で作れる完成した入力の組を、段の順・API の並びの順にすべて列挙する（`actions.enumerate_inputs`）
   - 並びが `significant`・`unconfirmed` の段（と `order` のない 2 個以上の段）は、並びの違いを別の組として数える
   - 並びが `not_significant`・`not_applicable` の段は、API の並びの 1 通りだけを数える
   - `total_units`・`options_by_choice`・`upstream_stages`/`after`・`options_by_path`・`options_from_stage`・`distinct_across_stages` は、段ごとの方式と同じ規則で絞る
   - 組ごとに check・エンジンの試行をしない。列挙するのは「契約の上で作れる」組で、合法・受理される組とは扱わない。API が返さない入力を内部の状態から補わない
3. 組が 2 つ以上なら、方策がその並びから均等に 1 つを選ぶ（1 回引く）。1 つなら引かない
4. 上限: 完成した組が 4,096 を超えた（`tuple_limit`）か、途中の部分の入力が 65,536 を超えた（`node_limit`）ら、段ごとの方式（3.1 節）に戻し、試みの記録の `build_method` に
   `{"method": "stage_fallback", "reason": …}` を残す。列挙は方策の乱数を使わないので、戻したあとの乱数の使い方は段ごとの方式と同じ
5. 作れる組がなければ `Unbuildable("no_constructible_tuple")`（段ごとの方式では理由が段ごと。にげるの費用の不足は `total_units_unreachable`）

### 3.3 選び直し（どちらの分布も同じ）

同じ状態の中で、前に試した入力（候補の中身と入力の意味の組）をまた選んだとき・入力を作れなかったとき・check が invalid だったとき・送信が断られたときは、候補の選択から
もう一度やり直します（方策の乱数は続きから使う）。入力を作れなかった候補は同じ状態では範囲から外します。上限は同じ状態の拒否 16・選び直し 64（[V0 の 3.4 節](verification-ai-v0.md)）。
選び直しのぶん、実際に送った入力の分布は 3.1 節・3.2 節の 1 回の抽選の分布と同じではありません。

## 4. 計測値の意味（`tools/verification_ai/metrics.py`）

数の単位は 3 つに分けます。

| 単位 | 意味 |
|---|---|
| 取得ごと（`*_fetches`） | 候補の取得（`candidates` の応答）1 回ごと。同じ状態で選び直すと、同じ候補を何回も数える |
| 状態ごと（`*_states`） | 異なる状態（受理と受理のあいだ）の数。同じ状態で何回取得しても 1 |
| 試みごと | 方策が候補を 1 つ選んだ回数（`selected`）と、そのあとの段階 |

種類ごとの値（`metrics.kinds.<種類>`）:

| 値 | 意味 |
|---|---|
| `offered_fetches`・`offered_states` | 候補として示された（取得ごと・状態ごと） |
| `in_scope_fetches`・`in_scope_states` | 方策の範囲に入れた |
| `excluded` | 範囲の外にした理由ごとの数（取得ごと。`display_only`・`input_withheld`・`processability:<区分>`・`unbuildable:<理由>`） |
| `selection_opportunities` | この種類が範囲にあった取得の回数 |
| `expected_selections` | 取得ごとの「範囲の中のこの種類の候補の数 / 範囲の中の候補の数」の合計（均等に候補を選ぶときの選ばれる数の期待。1 つの対戦の値で、偏りの判定には使わない） |
| `selected` | 方策が候補として選んだ |
| `build_ok`・`build_failed`・`build_method` | 入力を作れた・作れなかった（理由ごと）・作り方（`tuple`・`stage_fallback:<理由>`。段ごとの方式は記録しない） |
| `already_tried` | 作った入力が、同じ状態で前に試した入力だった（送らない） |
| `check_valid`・`check_invalid` | check の結果 |
| `submitted`・`outcome` | 送った（check が valid だけ）・結果（`accepted`・`refused`・`rejected`・`failed`） |
| `after_accept` | 受理のあとの状態の区分（送信の応答の `result.status`: `in_progress`・`awaiting_decision`・`halted`・`game_over`・`sudden_death_pending`） |

関係: `selected = build_ok + Σbuild_failed`、`check_valid + check_invalid = build_ok − already_tried`、`submitted = check_valid`、`Σoutcome = submitted`
（`tests/test_verification_ai_v1.py` の `MetricsTest` が確かめる）。

軸ごとの値（`metrics.axes`）: 状況・示された候補の処理可能性と入力の開示・残り（R-2〜R-5）の出現・候補がないときの理由・範囲の中の候補の数・選んだ候補の処理可能性・
段の形（段の数・入力の種類・選ぶ数・依存の形・`total_units`）・決定の種類・終わり方・停止（分類と診断の識別）。`metrics.fetches`・`metrics.states` は対戦の全体の取得の数と状態の数。

数は 1 つの対戦の中の値です。集計（`aggregate.json`）は対戦ごとの値を並べ、独立した対戦の数（`independent_games`）を別に持ちます。再現用の実行（7.1 節）は独立した対戦に数えません。

保存した記録からの数え直し（`metrics.kind_opportunities`）は、V0 のように計測を持たない記録から、ある種類の提示・範囲・選ばれる機会を、V0 の範囲の規則で数え直します
（新しい対戦を走らせない。`unverified` への切りかえは再現しない）。

## 5. CN-1 のエンジンの側の独立の課題（今回は扱わない）

v0.173 で案 B（正式な failure の口を揃える）を実施した（[cn1-failure-v0.173.md](cn1-failure-v0.173.md)）。以下は V1 の時点の記録。

V0 で再現した CN-1（`ActionHost` が `failure` を読むが、`ReplayCollector`・`view_record.ViewHost` は持たない）は、道具の側の `RecordingGame` で接続しています。エンジンの側の
扱いは、次のどちらかを別の作業として判断します。

| 案 | 中身 | 影響 |
|---|---|---|
| A. 説明を直す | `legal_actions.py:11` の「`view_record.ViewHost` を包める」を削り、包める対戦の形（`state`・`submit`・`failure`）を説明に書く | 挙動は変わらない。記録を集めながら U7 を通すには、今のように道具の側の包みが要る |
| B. 正式な failure の口を揃える | `ReplayCollector`・`ViewHost` に、送った操作の結果が `failed` のときの結果を返す `failure` を加える（`HostedGame` と同じ意味） | `ClientHub(ReplayCollector…)`・`ClientHub(ViewHost…)` がそのまま使える。U3・U5 の公開の型への追加なので、配布物の検査・既存の記録のテストの確かめが要る |

## 6. 使い方

```
cd C:\dev\kyuura-engine-vai
python -m tools.verification_ai.run_v1 reproduce --baseline <保存済みの実行の a のディレクトリ> --out C:/dev/kyuura-engine-verification-vai --engine-commit <コミット>
python -m tools.verification_ai.run_v1 run --out C:/dev/kyuura-engine-verification-vai --engine-commit <コミット> --seeds 11 12 13 --distributions uniform-candidate+uniform-stage uniform-candidate+uniform-tuple --budget-seconds 1200
python -m tools.verification_ai.run_v0 manifest --out C:/dev/kyuura-engine-verification-vai --run <実行の名前> --command "<実行したコマンド>" --exit-code <n>
```

- `reproduce`: 保存済みの実行の見出しと同じ条件（デッキ・seed・分布・上限）で 1 局だけ走らせ（A・B の 2 局にしない）、保存済みの意味の列・終わり方・完全な記録の行と比べ、
  新しい記録の対応と `replay_run` を確かめる。終了コードは一致なら 0
- `run`: 対戦の前に計画（`plan.json`。seed・分布・局・上限・予算）を書き、決めた組を 1 局ずつ順に実行する。予算（既定 1,200 秒）を超えたら残りは実行せず `not_run` と記録する
  （対戦の数・時間・範囲を自動で増やさない）。6 局を超える組は受け付けない。終了コードは、すべての局の `replay_run` が期待どおりで記録の対応に問題がなければ 0

## 7. 実行の結果（2026-11-08）

### 7.1 別のプロセスでの V0 の再現（1 局）

| 項目 | 結果 |
|---|---|
| 基準 | 保存済みの V0 の実行 `v0-…-g1-p1-h1/a`（コミット `43d0035`） |
| 実行 | 新しい Python のプロセスで `reproduce`（コミット `5d5e04e`。12:55:47Z〜12:55:50Z。終了コード 0） |
| 終わり方 | 基準 `game_over`・再現 `game_over` |
| 意味の列 | 142 行すべて一致（時間の上限では止まっていない。完全な一致） |
| 完全な記録の行 | 主体・送り手・コマンド・結果・受理の番号の 130 行が一致（`operation_id`・確認値・時刻は比べない） |
| 記録の対応 | 問題 0 |
| `replay_run` | 期待 `succeeded`・結果 `succeeded` |

再現に使った道具のコードは V0 の実行（`43d0035`）と同じではありません（`5d5e04e` は計測と `uniform-tuple` を加えた）。段ごとの方式の選び方の処理と乱数の使い方は変えておらず、
エンジンのパッケージは同じ（`behavior_digest` が同じ）です。この一致は「V1 のコードで V0 の条件を走らせた結果が、保存済みの V0 の記録と一致した」という確かめです。

### 7.2 V1 の実行（2 方式 × seed 3 個 = 6 局）

固定デッキ `hitmonchan-dewgong` 対 `venusaur-parasect`・既定の規約集合。seed は実行の前に決めた 11・12・13（`plan.json` は対戦の前に書いた）。1 局の上限は V0 と同じ。
全体 8.0 秒（12:55:59Z〜12:56:09Z。予算 1,200 秒）。終了コード 0。

| 局 | 終わり方 | 試み | 受理 | 番 | 拒否・refused・check の invalid | 入力を作れない | 範囲の外 | `replay_run` |
|---|---|---|---|---|---|---|---|---|
| stage-s11 | `halted_known`（`UNRESOLVED_MULLIGAN_COMPENSATION`） | 0 | 0 | 0 | 0 | 0 | 0 | `succeeded` |
| stage-s12 | `game_over`（勝者 0） | 169 | 144 | 50 | 0 | `retreat` 25 | `play_trainer`（未裁定）68 | `succeeded` |
| stage-s13 | `game_over`（勝者 1） | 168 | 141 | 41 | 0 | `retreat` 27 | `play_trainer`（未裁定）57 | `succeeded` |
| tuple-s11 | `halted_known`（同上） | 0 | 0 | 0 | 0 | 0 | 0 | `succeeded` |
| tuple-s12 | `game_over`（勝者 1） | 141 | 120 | 45 | 0 | `retreat` 21 | `play_trainer`（未裁定）10 | `succeeded` |
| tuple-s13 | `game_over`（勝者 1） | 141 | 126 | 43 | 0 | `retreat` 15 | `play_trainer`（未裁定）25 | `succeeded` |

- seed 11 は、2 つの方式とも、対戦の開始（`new_game`）の時点で、エンジンが切り直しの補償の未裁定（`UNRESOLVED_MULLIGAN_COMPENSATION`。分類 `unresolved_ruling`）で止めた。方策が
  選ぶ前の既知の停止で、seed を差し替えていない。完全な記録（行 0）の `replay_run` は `succeeded`
- 記録の対応はどの局も問題 0。異常の候補はどの局も 0
- `uniform-tuple` では、上限を超えて段ごとの方式に戻った試みは 0（列挙した組の数の最大: `attach_energy` 30・`retreat` 30・`use_power` 20・`place_starting` 15）
- 6 局のうち、方策が選んだ対戦は 4 局（seed 12・13）。分布の違いの比べは 2 局ずつで、偏りを判定する数ではない

### 7.3 V0 の `use_power` が選ばれなかった理由（保存した記録の数え直し）

| 項目 | 値 |
|---|---|
| 提示 5 回の数え方 | 取得ごとに 5 回で、5 つの異なる状態（受理の番号 42・46・51・52・53）で 1 回ずつ。どれもフシギバナのエナジートランス（3 段。`may_stop_later`・`confirmed`） |
| 範囲 | 5 回とも範囲の中（除外 0） |
| 候補の数と抽選の機会 | その取得の範囲の中の候補は 5・6・6・5・5 で、選ばれる確率は 1/5・1/6・1/6・1/5・1/5（合計 0.93） |
| 入力の組み立て | 選ばれていないので、組み立ては一度もない（失敗もない） |
| 結論 | 5 回の抽選で選ばれなかっただけ（選ばれた候補は `end_turn` 3 回・`retreat` 2 回）。1 つの対戦から偏りは判断しない |

V1 の stage-s13 では `use_power` が範囲の機会 74 回のうち 26 回選ばれ、26 回受理された（3 段の入力・`upstream_stages`/`after` に実際の対戦で届いた）。tuple-s13 では 9 回受理された。

### 7.4 実際の対戦で届いた範囲と届かなかった範囲（V1 の 6 局）

- 受理した種類: V0 の 13 種類に加えて `use_power`（seed 13）。`use_stadium`・`remove_disguise`・`discard_from_play`・`reveal_face_down`・`check_face_up_deck`（表示だけ）・
  `start_sudden_death` には届いていない
- 入力の形: `upstream_stages`（特殊能力の 3 段）に届いた。`options_by_path`（カツラの 2 枚目）には届いていない（このデッキの組にカツラがない。単体のテストだけ）
- 決定の種類: `select_pokemon`・`promote_active`・`take_prize`
- 受理のあとの状態: `in_progress`・`awaiting_decision`・`game_over`。受理のあとの停止（`halted`）は起きていない
- 結果: 拒否・`refused`・check の invalid・`failed` は起きていない。停止は開始の時点の既知の停止だけ。残り（R-2〜R-5）・`input_withheld`・表示だけの候補は示されていない
- 規約集合は既定だけ。S2A・PO・ほかのデッキは実行していない

## 8. テスト

`tests/test_verification_ai_v1.py`（19 テスト）と、ランナーを変えたので `tests/test_verification_ai_v0.py`（24 テスト）。

| クラス | 確かめること |
|---|---|
| `StageProcedureTest` | 選ぶ数 → 重ならない順の選択の手順（場面と選べる数の並び）、省くのは選ぶ数 0、選べるものが 1 つでも引く、固定の seed で同じ選択 |
| `TupleTest` | 並びを数える・数えない、`order` のない段、`options_by_choice`・`upstream_stages`/`after`・`options_by_path`・`options_from_stage`・`total_units`・`choose_value` の既知の組と過不足なく一致、`tuple_limit`・`node_limit` と戻した記録、方策が組の全体から 1 回だけ選ぶ、知らない `order` で止まる、実際の盤面（カツラの 2 枚目）の組の数が段の契約から別に数えた数と同じでどの組も check を通る |
| `MetricsTest` | 取得ごと・状態ごとの区別、除外の理由、数の関係、check を経ない送信がない（両方の分布の小さな対戦）、保存した記録からの数え直しと計測の一致 |
| `ReproduceTest` | 保存した実行との単独の比べ（一致なら 0。意味の列の 1 行を変えると 1 で、最初の違いの位置を返す） |

実行（1 モジュールずつ、別のプロセス）: `tests.test_verification_ai_v1` 19 テスト・失敗 0、`tests.test_verification_ai_v0` 24 テスト・失敗 0。

## 9. 失敗・修正・再実行・未確かめ

- 失敗: なし（テスト・実行とも）
- 重複した実行: `tests.test_verification_ai_v1` を 2 回実行した（1 回目の出力の末尾が `ReproduceTest` の印字で埋まり、要約の行が見えなかったため。2 回目も 19 テスト・失敗 0）。
  件数のためだけの成功した実行の繰り返しで、本来は不要だった
- 修正: V0 の文書の「public に seed を含まない」を直した（V0 の実行の名前 `…-g1-p1-h1` と V1 の局の名前 `stage-s11` などに seed の値が現れる。どれも文書に書く固定の検証用の
  seed で、秘密として扱わない。public に入れないのは乱数の状態・デッキの並び・カード・選択の中身・取っ手）
- 未実行: なし（計画の 6 局と再現の 1 局をすべて実行した）
- 未確かめ: 7.4 節の届かなかった範囲、`uniform-tuple` の上限で戻る経路の実際の対戦（単体のテストだけ）、V0 の道具のコード（`43d0035`）そのものでの別のプロセスの再現

## 10. 限界と V2 へ進む判断の材料

- 分布の違い: 同じ seed でも 2 つの方式は別の対戦になる（seed 12・13 の受理の数・種類が違う）。2 局ずつで、分布の偏りを判定できる数ではない。`expected_selections` と `selected`
  の差も 1 局の揺れの範囲を超えると言えない
- 選び直しの無駄: にげるは費用の不足で入力を作れない場面が多い（1 局 15〜27 回）。V0 と同じく範囲から外すまでに 1 回の抽選を使う
- 範囲の外: 受理の前に未裁定で止める `play_trainer` が多い（1 局 10〜68 回の取得）
- 開始の時点の停止: 既定の規約集合では seed によって準備で止まる（seed 11）。S2A・PO の規約集合での到達は V1 では確かめていない
- 深さ: ワザの受理は 1 局 0〜9 回で、終局まで届くが、ワザ・きぜつ・サイドの経路は少ない。V2 のルールの方策（ワザを優先する小さな順位）で深さが変わるかを、同じ計測で比べられる
- 届かなかった種類・入力の形（7.4 節）は、デッキの組（D-12）か `boundary`（V3）で届かせるかの判断が要る
