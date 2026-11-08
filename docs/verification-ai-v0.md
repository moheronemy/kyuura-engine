# 検証用 AI の V0（固定条件の 1 対戦の縦通し）

[仕様](verification-ai-design.md) と [実装計画](verification-ai-implementation-plan.md) の V0 だけを実装しました。目的は AI の強さではなく、公開の API（`client_api`）から操作の列を
作り、エンジンの問題を記録・再現できる最小の縦通しを作ることです。V1 以降（分布の拡張・ルールの方策・混合・`boundary`・`negative`・双子・広い対象・最小化）は実装していません。

## 1. 基点と範囲

| 項目 | 値 |
|---|---|
| 基点 | `claude/verification-ai-design` の `17e31a9`（設計の最後。`e26df79` を祖先に持つ。`kyuura_engine` は `e26df79`（0.172.0）と同じ。`git diff --quiet e26df79 HEAD -- kyuura_engine` が差なし） |
| ブランチ | `claude/verification-ai-v0`（worktree `C:\dev\kyuura-engine-vai`） |
| 固定条件の実行のコミット | `43d00355e90bf05a40594d17e908e9d832abda77`（`behavior_digest` `07a189c9…6c18`。U7-5f・U7-5g の配布の確かめの値と同じ） |
| 変えていないもの | `kyuura_engine`（エンジン本体）・GUI・renderer・kyuura・カードデータ・固定デッキ・規約集合・識別の方式。既存の `tools/`・`tests/` |

### 1.1 この版で採用した判断（利用者の指示。2026-11-08）

V0 と、次の判断だけを採用しました。仕様の D-1〜D-12 を一括で採用したのではありません。

| 項目 | 採用 |
|---|---|
| 基点（D-1 の一部） | 設計と U7-5f・U7-5g を含む公開のコミットから作る（`main` への取り込みを待たない） |
| CN-1（D-4 の一部） | 小さなテストで再現を確かめ、再現したら道具の側の小さな包みで接続する。包みは実際の failure を伝える |
| 上限（D-11 の一部） | 操作 2,000・受理 1,000・番 200・時間 120 秒 |
| 証跡の保存先（D-10 の一部） | `C:/dev/kyuura-engine-verification-vai/`（`verifier/` と `public/`） |
| 方策 | 仕様の最小のランダムの方式（`uniform-candidate+uniform-stage`） |

暫定のまま（採用していない）: 準備で両方が操作する場面の順（D-8。V0 は 0 → 1 の決まった順）、ジャンケンの勝者の決め方（D-9。V0 はホストの乱数で均等）、操作の層の選択（D-3。V0 は
`client_api` を使う）、拒否を異常の候補にする種類の表（D-6。V0 は `supported` の拒否だけを異常の候補にする）、混合の単位（D-7）、デッキと規約集合の組（D-12）、コードの置き場所（D-2。V0 は
`tools/verification_ai/`）。

## 2. 構成と責任の分け方

| 責任 | モジュール | 中身 |
|---|---|---|
| A. エンジン・API（既存） | `kyuura_engine`（変えていない） | 候補・入力の条件・check・実行・診断 |
| B. 行動生成 | `tools/verification_ai/actions.py` | 段の契約から `choices` を組み立てる。知らない項目は `ContractUnknown`、作れないときは `Unbuildable`。`kyuura_engine` を import しない |
| C. 戦略 | `tools/verification_ai/policies.py` | `UniformPolicy`: 渡された並びの位置を均等に選び、理由のコードを返す。`kyuura_engine` を import しない |
| D. 検証ランナー | `tools/verification_ai/runner.py`・`records.py`・`run_v0.py` | 進行・上限・分類・照合・記録・再現 |

- 操作は `PlayerEndpoint`・`HostEndpoint` の `handle` に JSON の要求を送るだけです（`runner.request`）。ランナー・方策・行動生成は `HostedGame.submit`・`apply_command` を呼びません
- 方策に渡すのは、その主体の入口の `view`・`candidates` の応答と、段の契約（その主体の `inputs` の応答の段）だけです。ランナーが持つ完全な情報（`GameState`・`CommandResult`・
  完全な記録・seed）は渡しません。検証者用の診断は `ClientHub(verifier=…)` の呼び出しでランナーだけが受け取ります
- ホストの係（ジャンケンの勝者）は、プレイヤーの方策と別の乱数の `UniformPolicy` で、ホストの入口の観測（観戦者と同じ範囲）だけを受け取ります

### 2.1 1 回の試みの段階

1 回の試みを次の段階で分けて記録します（`trace.jsonl` の 1 行）。

1. 候補にある（`candidates`。範囲の選択の結果 `scope`）
2. 入力を作れる（`build`: `ok`・`{"withheld": …}`・`{"unbuildable": 理由, "stage": n}`・`ok_already_tried`）
3. check を通る（`check.response.valid`）
4. submit が受理される（`submit.outcome`: `accepted`・`rejected`・`failed`・`refused`）
5. 受理のあとに完走する（次の試みの状態の区分と、対戦の終わり方で見る）

## 3. 行動生成とランダムの選び方

### 3.1 分布

分布の名前は `uniform-candidate+uniform-stage` です。完成した入力の組を均等に選ぶ分布でも、全候補の操作を均等に選ぶ分布でもありません。

- 候補: 範囲の中の候補（API の並びのまま）から均等に 1 つ
- `choose_value`: 範囲の整数から均等に 1 つ（範囲の大きさの上限 10,000）
- `choose_option`: 選ぶ数 k を `count.min`〜`min(count.max, 許される選べるものの数)` から均等に選び、k 個を重ならずに順に均等に選ぶ（選んだ順が送る並び）。k が 1 通りなら乱数を使わない
- `total_units` の段: `units` の合計が範囲に入る組を、組み合わせの数え上げ（上限 4,096）で集め、k → 組 → 並びの順に均等に選ぶ。上限を超えたら `Unbuildable("combinations_limit")`

この分布では、入力の組が少ない候補（`end_turn` は 1 通り）が相対的に多く選ばれ、後の段の選べるものが少ない枝が選ばれやすくなります。

### 3.2 段の契約の扱い

- 許される選べるもの: `eligible` が偽でなく、`processability` が範囲（`deep`: `supported`・`may_stop_later`）にあるもの。`options_by_choice`・`options_by_path` の参照は、参照の
  区分と選べるものの区分の両方を見る
- `depends_on_stage`・`options_by_choice`: 前の段で選んだ 1 つの番号の参照だけ。`upstream_stages` があれば選べるものの `after` も合わせる
- `path_stages`・`options_by_path`: 前の段の番号を `/` でつないだ鍵。鍵がなければその段は 0 個だけ（`count.min` が 1 以上なら `Unbuildable`）
- `options_from_stage`・`distinct_across_stages`: 参照する段の選べるものから、前の段で選んだものを除く
- 知らない段の項目・知らない `input`: `ContractUnknown` で止める（`STAGE_KEYS` は v0.172.0 の `legal_actions.py` の段の項目）
- 段の形の確かめ `legal_actions.stage_dependency_problems` は、2 段目以降のすべてが `depends_on_stage` か `path_stages` を持つ段の並び（エネルギー・進化・ワザ・特殊能力・カツラの
  2 枚目）だけに当てます。前の段に依存しない 2 段目（初期配置の `options_from_stage`・にげるのトラッシュ）はこの関数の対象の外で、当てると「直前の段でない」と報告します
  （上限の小さな試しの実行で分かった。仕様の 1.1 節・4.4 節の「毎回かける」は誤りで、仕様を直した）

### 3.3 範囲の選択（プロファイル `deep`）

範囲の外にする候補: 表示だけ（`display_only_kinds`。FU2 の `check_face_up_deck` は送らない）・入力を返さない（`input_disclosure` が `unconfirmed`）・処理可能性が `supported`・
`may_stop_later` でない・同じ状態で入力を作れなかった。範囲の中に候補がないときだけ `unverified` も許し、`deep_fallback_unverified` を数えます。範囲の外にした候補は理由ごとに
`coverage.scope_excluded` に数えます。候補の中身でゲームの合法性を判定することはしません。

### 3.4 選び直しと上限

- 同じ状態（受理のあいだ）で、check の invalid・拒否・refused の合計が 16 になったら `no_progress`（`rejections_per_position`）
- 同じ状態での候補の選び直しが 64 回を超えたら `no_progress`（`draws_per_position`）。入力を作れなかった・前に試した入力をまた選んだ（`retry_same_input`）を含む
- 一度 check・submit で断られた入力（候補の中身と入力の意味の組）は、同じ状態では送り直しません（拒否の記録は残す。拒否を避けるためのゲームのルールの判定はしない）
- 入力を作れなかった候補は、同じ状態では選び直しから外します（同じ状態からは同じ結果になる。外したことを記録する）

## 4. 上限と終わり方

### 4.1 カウンタの意味

| カウンタ | 意味 | 上限 |
|---|---|---|
| `operations` | 送った `submit` の要求の数（受理・拒否・failed・refused のすべて。check だけで止めた試みは数えない） | 2,000 |
| `accepted` | 受理された `submit` の数 | 1,000 |
| `turns` | 始まった番の数（ホストの観測の区間の番号と番の番号の組が変わり、番の番号が 1 以上になった回数。延長戦の区間の番も数える） | 200 |
| 時間 | 実行の開始からの `time.monotonic()` の秒 | 120 秒 |

上限は、要求と要求のあいだ（ループの始め・候補の取り直しの前・submit の前）で確かめます。1 回の `handle`（エンジンの処理を含む）の途中では止められないので、時間の上限は
その 1 回の処理の時間ぶん超えることがあります。ほかのプロセスを止める・探す処理はありません。

### 4.2 対戦の終わり方（1 対戦に 1 つ）

| 分類 | 条件 |
|---|---|
| `game_over` | 状態が `game_over` |
| `halted_known` | 状態が `halted` で、停止の公開の診断の分類が `unresolved_ruling`・`unsupported`・`technical_limit` |
| `halted_unclassified` | 状態が `halted` で、分類が上の 3 つでない（既知の停止として扱わない） |
| `input_unavailable` | 操作するはずの主体に、範囲の中で送れる候補がない（R-2〜R-5・入力を返さない・作れない・`kinds_not_covered`） |
| `api_contract_unknown` | 知らない段の項目・値・状況・処理可能性・残りの id・送信の結果、段の形の問題 |
| `no_progress` | 3.4 節の上限 |
| `limit_operations`・`limit_accepted`・`limit_turns`・`limit_time` | 4.1 節の上限 |
| `failed`・`state_integrity` | `submit` の結果が `failed`（診断の分類が `state_integrity` なら後者）、処理できない結果のあとの入口の誤り |
| `exception` | ランナー・入口からの例外（入口は例外を投げない約束。ほかの分類に変えない） |
| `inconsistency` | ランナーの照合の不一致で続けられないもの（待っている主体と候補の状況の食い違い・だれも待っていない） |
| `start_rejected` | 対戦を始められなかった |

### 4.3 操作ごとの数と異常の候補

操作ごとに、受理・拒否（`rejected`）・ホストの段の `refused`（コードごと）・check の invalid・入力を作れなかった・入力を返さないを数えます。拒否は記録の対象で、拒否されたことだけで
エンジンの不具合とは扱いません。V0 が異常の候補にするのは次です（対戦は止めず、`anomalies` に記録）。

- `supported_rejected`: 処理可能性が `supported` の候補の拒否（受け付ける前の確かめを満たすという保証との食い違い）
- `check_valid_but_submit_refused`: check が valid の入力を submit が `CANDIDATE_INPUT_INVALID`・`CANDIDATE_NOT_EXECUTABLE`・`INPUT_BOUNDARY_UNCONFIRMED` で断った
- `state_changed_on_rejection`: 拒否・断りのあとに、状態のオブジェクトか確認値（`replay_record.checks`）が最後に受理したときの値と違う
- `update_after_rejection`: 拒否・断り・check の invalid のあとに、だれかに公開の更新が出た
- `accepted_without_refetch`・`update_numbers`・`update_observation_differs_from_view`: 受理のあとの `refetch_required`・更新の番号・更新の観測と `view` の食い違い
- `inputs_refused_on_fresh_handle`: 取り直したばかりの取っ手で `inputs` が断られた

## 5. 記録

### 5.1 CN-1（ActionHost と ReplayCollector・ViewHost の接続）

- 再現した: v0.172.0 で `ReplayCollector`・`ViewHost` は `failure` を持たず、`ClientHub(…)` の候補の取得で `AttributeError` が入口の外へ出ます（`client_api` の「例外を投げない」は
  包む対戦が `HostedGame` の形であることが前提）。`tests/test_verification_ai_v0.py` の `CN1Test.test_view_host_and_collector_lack_failure`
- 対応: `records.RecordingGame` が `ReplayCollector` を包み、`state`・`submit`・`failure` を持つ。送った操作の結果が `failed` ならその `CommandResult` を `failure` にし、後の送信を
  `HostStoppedError` で断る（`HostedGame` と同じ）。既存の公開の値（`CommandResult.outcome`）だけで正確に伝わるので、エンジンは変えていません
- 確かめ: 失敗を注入した送信（テストの中で `adapter.apply_command` を例外にする）で、`failure` が `failed`・`internal_error` の結果になり、入口が `CLIENT_GAME_UNAVAILABLE` を返し、記録が
  `aborted` になる。ランナーは `failed` に分類し、同じ失敗の条件の再実行は `recorded_failure`（`CN1Test`）
- エンジンへの報告事項: `legal_actions.ActionHost` の説明（`legal_actions.py:11`）は `view_record.ViewHost` を包めると書くが、`failure` がないので包めない。説明を直すか、`ViewHost`・
  `ReplayCollector` に `failure` を加えるかは別の作業で判断する

### 5.2 保存するもの

保存先は `C:/dev/kyuura-engine-verification-vai/`（リポジトリの外。Git に入れない）。

| 場所 | 中身 | 読む人 |
|---|---|---|
| `verifier/runs/<run>/a/`・`b/` | `header.json`（エンジンのコミット・版・実装の識別・実行環境・規約集合・デッキ・ゲームの seed・方策の名前・版・分布・主体ごとの種・上限・実行の引数）、`trace.jsonl`（操作の記録）、`actors/0.jsonl`・`1.jsonl`・`host.jsonl`（主体ごとに受け取った応答と選択）、`full_record.json`（完全な再現用記録）、`result.json`（終わり方・数・異常の候補・到達範囲）、`meaning.jsonl`（意味の列） | 検証者 |
| `verifier/runs/<run>/a/views/` | 閲覧者ごとの記録（`view_records_from_replay`。プレイヤー 0・1・観戦者） | 検証者（それぞれの閲覧者に渡せる形） |
| `verifier/runs/<run>/verification.json`・`invocation.json` | 再実行の結果・意味の比べ・記録の対応、実行のコマンドと終了コード | 検証者 |
| `verifier/discarded/` | 採用しなかった実行の出力（理由の `README.md`） | 検証者 |
| `public/runs/<run>/summary.json` | 終わり方・数・到達範囲・再実行の結果の集計だけ（乱数の状態・デッキの並び・カード・選択の中身・取っ手を含まないことを確かめた。V1 の訂正: 実行の名前 `…-g1-p1-h1` に固定の検証用の seed の値が現れる。seed は文書にも書く値で、秘密として扱わない。[verification-ai-v1.md](verification-ai-v1.md) 9 章） | だれでも |
| `MANIFEST.md`・`manifest.json`・`sha256.json` | 配置の説明と、すべてのファイルの sha256 | — |

完全な記録（`ReplayCollector`）にはエンジンに渡った操作（受理・拒否・failed）だけが入り、check で止めた試み・ホストの段の `refused`・入力を作れなかった試みは入りません。
`trace.jsonl` はそれらを含むすべての試みと、選択の理由・候補・段・check と submit の応答・検証者用の診断を持つ、検証用の操作の記録です。エンジンに渡った試みと完全な記録の行は、
同じ順・同じ `operation_id`・同じ結果で対応します（`records.correspondence`）。

### 5.3 再現の 2 つの方法

1. **保存したコマンドの記録の再実行**: `replay_run.replay(full_record)`。方策・U7 を通らない。期待は記録の終わりに合わせる（`closed` → `succeeded`、`aborted` → `recorded_failure`）
2. **方策の再実行**: 同じゲームの seed・方策の seed・ホストの seed・設定で最初から走らせ、意味の列を比べる

意味の列（`records.meaning_sequence`）の 1 行は 1 回の試みで、主体・候補の中身（応答ごとの番号 `id` を除く）・入力の意味（選んだ番号をその選べるものの中身に置きかえ、`id`・`after`
だけを除く）・作れたか・check の結果と断りのコード・送信の結果と断りのコード・診断の識別です。取っ手（`game`・`revision`）・`operation_id`・応答ごとの番号・時間は比べません。
ほかの項目は除きません。比べるのは 2 つの列の短い方の長さまでで、どちらも時間の上限で止まっていなければ、終わり方と長さも同じであることを求めます。

## 6. 使い方

```
cd C:\dev\kyuura-engine-vai
python -m tools.verification_ai.run_v0 run --out C:/dev/kyuura-engine-verification-vai --engine-commit <実行するコミット>
python -m tools.verification_ai.run_v0 manifest --out C:/dev/kyuura-engine-verification-vai --run <run> --command "<実行したコマンド>" --exit-code <n>
```

固定条件の既定: デッキ `hitmonchan-dewgong`（プレイヤー 0）対 `venusaur-parasect`（プレイヤー 1）、既定の規約集合（`CS-KYUURA-CURRENT@1`）、ゲームの seed 1・方策の seed 1・
ホストの seed 1、プロファイル `deep`。`run` は同じ条件で 2 回（`a`・`b`）走らせ、終了コードは、再実行が期待どおり・意味の列が一致・記録が対応・例外でないときに 0、ほかは 1 です。
コミットは引数で渡します（ランナーは git を呼ばない）。

## 7. 実行の結果（2026-11-08）

### 7.1 固定条件の実行

| 項目 | 結果 |
|---|---|
| 実行 | コミット `43d00355…`。上のコマンド。終了コード 0。所要約 5.5 秒（対戦 1 回は約 1.3 秒） |
| 終わり方 | `a`・`b` とも `game_over`（区間 0。勝者はプレイヤー 1） |
| 数（`a`） | 試み 142・送信 130・受理 130・番 46・check の invalid 0・拒否 0・refused 0・failed 0・入力を作れない 12・入力を返さない 0・`deep_fallback_unverified` 0 |
| 異常の候補 | 0 |
| `replay_run` | 期待 `succeeded`・結果 `succeeded`（130 行・受理 130 を照合。終わりも一致） |
| 閲覧者ごとの記録 | `view_records_from_replay` が `succeeded`（3 つを書いた） |
| 意味の列 | `a`・`b` の 142 行がすべて一致。終わり方と長さも同じ |
| 記録の対応 | `a`・`b` とも問題 0 |

1 回目の実行（同じコマンド）は、2 つの対戦・`replay_run`・意味の比べのあと、公開の集計を書くところで `KeyError`（規約集合の識別の項目名の誤り）で止まり、終了コード 1 でした。
その時点の結果も `game_over`・`succeeded`・142 行の一致でした。`run_v0.py` を直してコミット（`43d0035`）し、同じ条件でもう 1 回実行した結果が上の表です。1 回目の出力は
`verifier/discarded/` に置き、採用していません。

### 7.2 到達した範囲（実際の対戦）

- 受理した操作の種類（13）: `place_starting`・`mulligan_draw`・`report_janken`・`play_basic`・`attach_energy`・`evolve`・`retreat`・`play_trainer`・`use_attack`・`end_turn`・
  `answer_decision`・`take_prize`・`promote_active`
- 決定の種類: `select_pokemon` 12・`promote_active` 3・`take_prize` 3
- 入力の形: `choose_option` 132・`choose_value` 2、1 段 52・2 段 41、`depends_on_stage` 34・`options_from_stage`・`distinct_across_stages` 2・`total_units` 5・選ぶ数の上限が
  2 以上 5、任意の段を省いた 12・使った 4
- 処理可能性: 選んだ候補は `may_stop_later` 131・`supported` 11
- 範囲の外にした候補: 受理の前に未裁定で止める `play_trainer`（`unresolved_ruling`・`stops_before_acceptance`）22 回
- 入力を作れなかった: `retreat` 12 回（`total_units` が 2 で、ついているエネルギーが 1 個。U7-3 の契約どおり、費用の不足は候補から除かず入力の検査で断る。エンジンの不具合ではない）
- 示されたが選ばれなかった: `use_power` 5 回

### 7.3 実際の対戦で届かなかった範囲（V0 で未確かめ）

- 種類: `use_power`・`use_stadium`・`remove_disguise`・`discard_from_play`・`reveal_face_down`・`check_face_up_deck`（表示だけ）・`start_sudden_death`（延長戦）
- 入力の形: `upstream_stages`/`after`（特殊能力の 2〜3 段）・`options_by_path`（カツラの 2 枚目）は、実際の対戦では届かず、単体のテスト（構築した盤面の U7 の応答と合成した段）だけで
  確かめた
- 結果: 拒否（`rejected`）・ホストの段の `refused`・check の invalid・`failed`・停止（`halted`）・`unverified` への切りかえ・残り（R-2〜R-5）の出現は、実際の対戦では起きなかった。
  分類の処理は単体のテスト（故障の注入・作った応答）だけで確かめた
- 1 つのデッキの組・既定の規約集合・1 つの seed だけ。S2A・PO の規約集合、ほかのデッキは実行していない

## 8. テスト

`tests/test_verification_ai_v0.py`（24 テスト）。

| クラス | 確かめること |
|---|---|
| `CN1Test` | CN-1 の再現・包みでの接続・failure の伝わり方・ランナーの `failed` の分類と `recorded_failure` |
| `BuildTest` | `options_by_choice`・`upstream_stages`/`after`・`options_by_path` の任意の段・`options_from_stage`/`distinct_across_stages`・`total_units`・`choose_value`・知らない項目と `input`。構築した盤面（カツラの 2 枚目・フシギバナのエナジートランス・ラプラスのにげる）で、作った入力が 40 回とも check を通る |
| `BoundaryTest` | 方策・行動生成が `kyuura_engine` を import しない。方策に渡る値が JSON の値だけで、その主体の入口の応答（`viewer`・`actor` が本人） |
| `CheckBeforeSubmitTest` | valid で同じ取っ手・同じ入力の check がなければ submit を送らない |
| `RetryTest` | check の invalid・submit の refused が続くときの `no_progress`（16 回か 64 回の上限）、入力を返さないときの `input_unavailable` |
| `LimitsTest`・`HaltTest` | 操作・受理・番・時間の上限の分類、既知の停止と分類のない停止の区別 |
| `RecordTest` | 操作の記録とエンジンの記録の対応、`replay_run` の `succeeded`、意味の列の一致と、方策の seed を変えたときの違いの検出 |

テストの対戦はどれも上限の小さな対戦（数十の操作）で、7 章の固定条件の実行とは別です。

実行（1 モジュールずつ、別のプロセス）:

1. `python -m unittest tests.test_verification_ai_v0`: 24 テスト・失敗 2（`RetryTest` の 2 つ。初期配置の入力の組が少なく、同じ状態の拒否の上限 16 より先に選び直しの上限 64 で
   `no_progress` になった。止まり方は正しく、テストの期待が上限の 1 つだけを見ていた）
2. テストの期待を「どちらかの上限で止まり、その数が合う」に直し、`python -m unittest tests.test_verification_ai_v0.RetryTest` だけを再実行: 3 テスト・失敗 0

1 の実行のあとに `run_v0.py` の集計の書き出し（7.1 節）を直しました。テストが使う `run_v0.expected_replay` は変えていませんが、直したあとのモジュール全体の再実行はしていません。
全体のテスト・GUI・E2E・大量の対戦・lockstep・状態の監査・広い seed の探索はしていません。

## 9. V1 へ進む前の残件

- CN-1 のエンジンの側の扱い（`ActionHost` の説明か、`ViewHost`・`ReplayCollector` の `failure`）の判断（5.1 節）
- 実際の対戦で届かなかった種類・入力の形・結果（7.3 節）を、どの段で届かせるか（V1 のデッキと規約集合の組・V3 の `boundary`）
- 暫定のまま使っている判断（1.1 節の D-2・D-3・D-6・D-7・D-8・D-9・D-12）の採用
- `use_power` のように示されても均等の分布ではほとんど選ばれない種類があり、分布の偏り（仕様 3.1 節）が到達範囲に効く。V1 の `uniform-tuple` と到達範囲の集計で比べる
- 意味の列の比べは同じプロセスの 2 回の実行だけで確かめた。別のプロセス・別の日の再実行の一致は確かめていない
