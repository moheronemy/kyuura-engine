# v0.174: 本人のうらのバトル場のポケモンのにげるの入力（R-5 の P6）

[R-5 の監査](legal-actions-r5-audit.md) 5 章の提案 P6 を、エンジンの側の 1 単位として実装しました。公開の情報から安全に作れる入力を API に加える作業で、ゲームの合法性・裁定・
エンジンのコマンドの処理は変えていません。

## 1. 採用の記録

- 採用: 利用者の指示（2026-11-09「R-5監査で提案されたP6（本人のうらのバトル場のポケモンのにげる入力）の補完を採用します。」）
- 範囲: `legal_actions._retreat_candidate` の、本人のバトル場のポケモンがうら（マチスの秘策）の分岐だけ。GUI・renderer・kyuura・カードデータ・固定デッキ・規約集合・裁定・識別の方式・
  検証用 AI の道具は変えていない
- 位置づけ: **進行不能を解消する修正ではない**。P6 は v0.173.0 でも進行を止めない（同じ番のほかの操作・番を終えるは示される）。うらのままにげる操作（ルール上できる。エンジンは
  おもてにしてから確かめる）を、API から選べるようにするだけ
- 監査の結論の限定: 監査の「決定待ちで止まるのは C 群だけ」は、監査で確かめた登録・経路の範囲での結論。P2（見えないカードが選べるものにある実行時の確かめ）の通常の到達は未確認で、
  届く経路がないとは断定していない。今回は P2 を再監査していない

## 2. 入力契約（実装の前に決めた）

### 2.1 候補

| 項目 | おもてのにげる（変えない） | うらのバトル場のにげる（v0.173.0） | うらのバトル場のにげる（v0.174.0） |
|---|---|---|---|
| `input_disclosure` | `confirmed` | `unconfirmed`（入力を返さない。R-5） | `confirmed` |
| `processability`・`reasons` | 確かめの結果 | `unverified`・`["face_down_reveal_not_evaluated"]` | 同じ（変えない） |
| `guarantees` | `GUARANTEE_TURN_ACTION` | `GUARANTEE_TURN_ACTION`（入力の検査で `check_retreat` を呼ぶ、と書いてあり、うらでは当たらなかった） | `GUARANTEE_FACE_DOWN_RETREAT`（同じ 4 つの項目。確かめを呼ばないことを書く） |
| `choices_format` | `[入れ替える控えの番号, トラッシュするエネルギーの番号, ...]` | 同じ | 同じ |

本人だけが知る本当のカード（カード ID・名前・にげるエネルギー・タイプ）は、候補・理由・保証・入力のどこにも書かない。相手・観戦者の応答にはにげるの候補そのものがない（番のプレイヤーだけ）。

### 2.2 入力の段

| 段 | おもてのにげる | うらのバトル場のにげる（v0.174.0） |
|---|---|---|
| 1（`role` `new_active`・`meaning` `pokemon`） | 本人のベンチのポケモン（公開。うらの控えは `face_down`）。`count` 1〜1。各選べるものに `eligible`・`processability`・`reasons` | 同じ形。各選べるものは `eligible` 真・`processability` `unverified`・`reasons` `["face_down_reveal_not_evaluated"]` |
| 2（`role` `discard`・`meaning` `card`） | ついているカード。`count` 0〜枚数。`distinct`・`order` `significant`・`order_preserved`。`total_units`（にげるエネルギーの範囲）と、選べるものごとの `units` | ついているカード（公開）。`count` 0〜枚数。`distinct`・`order` `significant`・`order_preserved`。**`total_units`・`units` を省き**、かわりに `cost_evaluation` を置く。各選べるものに `card`・`card_id`・`special`・`eligible` 真・`processability` `unverified`・`reasons` |

新しい項目 `cost_evaluation`（段 2 だけ。オブジェクト）:

```json
{"status": "not_evaluated", "reason": "face_down_reveal_not_evaluated", "omitted": ["total_units", "units"]}
```

- `status` は今は `not_evaluated` だけ。`reason` は候補の理由と同じ語彙（`REASON_FACE_DOWN`）。`omitted` は、この段で省いた項目の名前（段の `total_units` と、選べるものの `units`）
- **省略できる条件**: `total_units`・`units` を省くのは、`cost_evaluation` があり、`status` が `not_evaluated` の段だけ。`cost_evaluation` のない段（おもてのにげる）は今までどおり
  `total_units` とすべての `units` がある。`cost_evaluation` も `total_units` もないにげるの段は、契約の外（クライアントは不明な応答として止める）
- **クライアントが計算してはいけない値**: にげるエネルギー（費用）・カードごとのエネルギーの個数・選んだカードで足りるか。0 と見なさない。うらのポケモンの本当のカード（本人の観測の
  `real`）から求めない（費用・個数は、場の効果・持ち主のタイプによる読み方・特殊エネルギーで変わり、エンジンがおもてにしてから決める）
- **入力の並びと意味**: `choices` は `[段 1 の番号, 段 2 の番号, ...]`。1 つめが入れ替える控え、残りがトラッシュするカードで、送った並びがトラッシュの並び（`order` `significant`。U7 は
  並びを変えない）。段 2 は 0 枚も選べる
- **`eligible`・`processability` の意味**: `eligible` 真は「入力として選べる（形の上で受け付ける）」だけ。`processability` `unverified` は「候補の作成・入力の検査で受理を確かめていない。
  送ればエンジンがおもてにしてから決める」。どちらも、にげられる・受理されるという保証ではない

### 2.3 check と submit

- `check`: 公開の情報と入力契約から確かめられる構造だけを検査する。選べるものの番号があること、1 つめが段 1・残りが段 2、段 2 の重なりがないこと（したがって数は 0〜枚数）。控えと
  エネルギーは候補が持つ番号（候補を作ったときの控えのいちばん上のカード・ついているカード）だけを引く。エンジンの確かめ（`check_retreat`）・状態の複製の上でおもてにして試すことは
  しない。形が合えば `valid` 真。**`valid` 真は、にげられる・受理されるという保証ではない**
- `submit`: 既存の `Retreat(actor, トラッシュするカード（選んだ順）, 控え)` をそのまま送る。エンジンは番・決定待ちでないことを確かめたあと、このポケモンをおもてにし（`_reveal_for_action`）、
  本当のカードが「たねポケモン」ならふつうに確かめる（受け付けなければコマンドごと拒否。状態・乱数・ログはもどり、おもてにしたことも公開しない。拒否は送った本人だけ）。「たねポケモン」
  でなければ、ついているカードといっしょにトラッシュして受理する（全員に公開）。受理で取っ手はすべて失効する（今までどおり）。FD1 などの停止は変えていない

### 2.4 形式の版

`kyuura_legal_actions_format`・クライアント API の `format` は 1 のまま。既存の運用（U7-5g の 3 段目 `energy2`・`options_by_path`・coverage の residual は、既存の項目の意味を変えない
追加として形式 1 のまま加えた）に合わせる。既存の項目（`total_units`・`units`）の意味は変えず、うらのバトル場のにげるの段で省き、省いたことを新しい項目で示す。ただし、項目の追加だけを
根拠に古いクライアントが正しく動くとはしない（5 章）。

## 3. 入力の JSON の例

構築盤面（テストの `face_down_active`。プレイヤー 0 のバトル場はうらのポケモンで闘エネルギー 1 枚、ベンチはエビワラー）の、本人の `inputs` の応答（説明の文は略）:

```json
{"candidate": "c2", "kind": "retreat", "stages": [
  {"stage": 1, "input": "choose_option", "role": "new_active", "meaning": "pokemon", "count": {"min": 1, "max": 1},
   "options": [{"id": "o1", "pokemon": 1, "card": 0, "zone": "bench", "bench_index": 0, "card_id": "PMCG1-058",
                "eligible": true, "processability": "unverified", "reasons": ["face_down_reveal_not_evaluated"]}],
   "order": "not_applicable"},
  {"stage": 2, "input": "choose_option", "role": "discard", "meaning": "card", "count": {"min": 0, "max": 1},
   "options": [{"id": "o2", "card": 5, "card_id": "PMCG1-102", "special": false,
                "eligible": true, "processability": "unverified", "reasons": ["face_down_reveal_not_evaluated"]}],
   "distinct": true, "order": "significant", "order_preserved": true,
   "cost_evaluation": {"status": "not_evaluated", "reason": "face_down_reveal_not_evaluated", "omitted": ["total_units", "units"]},
   "note": "…"}]}
```

`choices` の例: `["o1"]`（エネルギーをトラッシュしない）・`["o1", "o2"]`。どちらも check は `valid` 真で、受理はエンジンが決める（4.1 節の拒否の例）。

## 4. 限定の検証（構築盤面。new_game からの到達ではない）

`tests/test_legal_actions_p6_face_down_retreat_v0_174.py`（7 テスト）。盤面は既存の `tests/test_secret_plan_v0_67.py` の関数で作る（マチスの秘策でうらにして出し、にげるでバトル場へ、
2 番あとに闘エネルギーを 1 枚つける）。

### 4.1 直接のコマンドとの一致

同じ状態の複製で、U7（`ActorSession.submit`）・client_api（`ClientHub` のプレイヤーの入口）・直接のコマンド（`HostedGame.submit(Retreat(...))`）を比べた。結果の区分・本人への見え方
（診断を含む）が同じで、状態・乱数・ログ・決定の通し番号（`snap`）が同じ。

| 場面 | 本当のカード | 入力 | 結果 | 到達した範囲 |
|---|---|---|---|---|
| たねポケモンでにげる | コラッタ（たね・無色・にげる 0） | `["o1"]` | 受理。おもてにしてにげた（ログ `secret_plan_revealed`・`retreat`）。取っ手は失効（`CANDIDATES_STALE`）。公開の更新あり | 同じ番の MAIN にもどる（決定なし） |
| エネルギーが足りない | イワーク（たね・闘・にげる 3） | `["o1", "o2"]` | 拒否（`WRONG_RETREAT_COST`・`invalid_input`。本人への見え方だけ）。状態・乱数・ログはもどり、うらのまま。取っ手は失効しない。相手・観戦者への公開の更新なし。相手・観戦者の観測にカード ID は出ない | — |
| たねポケモンでない | ユンゲラー（1 進化） | `["o1"]` | 受理。おもてにして、ついているカードといっしょにトラッシュ（ログ `secret_plan_revealed`・`secret_plan_discarded`。にげるはおこらない） | 本人のバトル場に出す決定（`promote_active`）まで。答えていない |

拒否の診断のコードと到達の範囲は、証跡の `reached_outcomes.json` に記録した（直接のコマンドで同じ盤面）。終局へは進んでいない。

### 4.2 情報境界（双子）

- 双子: 本当のカードだけが違う 3 つの盤面（コラッタ・イワーク・ユンゲラー。段階・タイプ・にげるエネルギーが違う）。公開の情報（場・トラッシュ・枚数・ログ）と、本人の手札・場の公開の
  値は同じ。**本人の観測には本当のカード（`real`）があるので、本人の全知識は同じではない**（テストで本人の観測が違うことも確かめた）。比べたのは、この入力契約が使う部分だけ
- 本人の候補（取っ手を除く）・`inputs`・6 つの入力への `check`・client_api の候補が、3 つで同じ（件数・並び・制約・理由・`check` の答えが、費用・タイプ・段階によらない）
- 相手の候補・ホストの候補・相手と観戦者の観測・見えるログ・client_api の相手と観戦者の `view` が、3 つで同じ。本人の候補・入力にも、相手・観戦者の応答にも、本当のカード ID が出ない

### 4.3 形の検査と無副作用

- `CANDIDATE_INPUT_INVALID`: 空・存在しない控え（`o9`）・存在しないエネルギー・エネルギーが先・控えを 2 回・重なり（枚数を超える）・番号の型の誤り
- `valid` 真: エネルギー 0 枚・費用に足りないエネルギー（check は費用を見ない）
- 候補・`inputs`・`check` の前後で、状態・乱数・ログ・決定の通し番号が同じ
- おもてのにげるの契約は変わらない（`total_units`・すべての選べるものの `units` があり、`cost_evaluation` はない。保証は `GUARANTEE_TURN_ACTION`）

### 4.4 実行したテストと結果

1 モジュールずつ別のプロセスで実行した（証跡の `test_runs.txt`）。

| モジュール | テスト | 結果 |
|---|---|---|
| `test_legal_actions_p6_face_down_retreat_v0_174`（新） | 7 | 1 回目は 2 つ失敗（テストの誤り: 項目の名前と、説明の文・`omitted` の中の名前を区別していなかった。本人への見え方の属性の名前の誤り）。テストだけ直して再実行し、失敗 0 |
| `test_legal_actions_u7_5ab` | 27 | 失敗 0（v0.173 の期待「入力を返さない」を直した。意図した差） |
| `test_legal_actions_u7_5g_residual`・`test_legal_actions_u7_3`・`test_legal_actions_u7_1`・`test_client_api` | 9・29・42・9 | 失敗 0 |
| `test_legal_actions_api_design`・`test_legal_actions_decision_audit`・`test_legal_actions_u7_5_design` | 14・15・27 | 失敗 0 |
| `test_preset_decks_v0_20`（版）・`test_distribution` | 15・12 | 失敗 0（前者は v0.173 と同じく、環境の `PYTHONIOENCODING` を外したプロセスで実行） |

実行していないもの: 全体のテスト・GUI・E2E・大きな対戦・lockstep・状態の監査・seed の探索・new_game からの到達・検証用 AI の実行。

## 5. GUI・検証用 AI への影響（読み取りだけ。今回は変えていない）

### 5.1 GUI

比べる相手は、GUI のリポジトリ（`moheronemy/kyuura-engine-gui`）の最新の公開の作業ブランチ `feature/u7-verification-e0-g1` の `78c02a61cd4951e177f2f3791e05ef4807cb3215`。
2026-11-09 に GitHub の API で読み取りだけをした（GUI のリポジトリには fetch も書き込みもしていない）。このコミットは、`main` の `088822c` と `feature/engine-u7-5fg` の `b1037bc` を含み、それより新しい。

| 確かめたこと | `78c02a6` の今の扱い（コードを読んだ） | v0.174.0 の応答で起こること |
|---|---|---|
| 段の項目 | `web/src/api/validate.ts` の `stage` が、契約の表の `stage_keys`（`cost_evaluation` がない）にない項目を「知らない入力の項目」として不正にする | うらのバトル場のにげるの `inputs` は不明な応答として止まる（安全な側の失敗。送らない） |
| `total_units`・`units` が必須か | `total_units` がある段だけ、すべての選べるものに `units` を求める。`total_units` のない段は個数を数えない（`DecisionPanel` は `units` を表示しない） | `stage_keys` だけを直すと、個数の欄が出ない。費用を 0 とは表示しない（`total_units` がないと数える部分を飛ばす） |
| 送る前の check | `checkGate.ts` は、`check_before_submit_kinds`（`retreat` を含まない）か、`total_units` のある段のときだけ check を求める | `stage_keys` だけを直すと、この入力は check なしで送れる形になる（エンジンが決めるので情報は漏れないが、GUI の方針の門を通らない） |
| 選べるものの項目 | 選べるものの検査は共通（`eligible`・`reasons`・`special`・`face_down` を許す）。うらの控えにカード ID があれば不正 | 段 2 の選べるものに `eligible`・`reasons` が加わる（許される） |
| 入力非公開の表示 | `input_disclosure` が `unconfirmed` なら「入力非公開」を表示 | この候補は `confirmed` になる |

GUI に必要な追従（今回は着手しない）:
- `stage_keys` に `cost_evaluation` を加え、形（`status`・`reason`・`omitted`）を確かめる
- `cost_evaluation` のある段は「費用・個数は評価していない」と表示し、個数を計算しない（本人の観測の `real` から求めない）
- 送る前の check の門に、この段（または `retreat` 全体）を加える
- `cost_evaluation` も `total_units` もないにげるの段は、不明な応答として止める

### 5.2 検証用 AI（同じ基点の `tools/verification_ai`）

追記: このあと検証用 AI を追従させた（[verification-ai-p6.md](verification-ai-p6.md)）。下は追従の前の、v0.174.0 の時点の読み取り。

- `actions.py` の `STAGE_KEYS` に `cost_evaluation` がないので、`ContractUnknown`（推測で扱わない）で止まる（安全な側の失敗）
- 追従するときの注意:
  - `total_units` のない段は、今の選び方（0〜枚数の並び）になる
  - `deep` の範囲は `unverified` を許さないので、この候補はふだん選ばない（ほかに進む道がないときだけ）
  - check は今も、いつも送る前に呼ぶ
  - `unverified` の候補へのエンジンの拒否（`WRONG_RETREAT_COST` など）を、判定（`judge`）で異常の候補と既知の扱いのどちらにするかを決める必要がある
- 項目の追加だけを根拠に、古いクライアントが正しく動くとはしない。`stage_keys` で止める GUI・`ContractUnknown` で止める AI は安全な側に止まる。一方、知らない項目を無視するクライアントは、
  `total_units` のない段を「制約なし」と読みうる（エンジンが決めるので情報は漏れないが、送る前の判断を誤る）

## 6. 版・識別・配布

| 項目 | 内容 |
|---|---|
| 版 | 0.173.0 → 0.174.0（`kyuura_engine/__init__.py`・`pyproject.toml`・`tests/test_preset_decks_v0_20.py`。既存の運用どおり、エンジンの実行時のファイルを変えたので上げた） |
| 識別の方式 | 変えていない（`kyuura-package-files-sha256/1`） |
| 実装の識別 | `legal_actions.py` は挙動の側のファイルなので、`behavior_digest` が `cf279dc9…e129` に変わった（0.173.0 は `822c10c1…f397`）。`instrumentation_digest` は `e7d36df3…3034` のまま |
| 記録・スナップショット | 0.173.0 で作った完全な再現用記録・スナップショットは、版・`behavior_digest` が違うので、0.174.0 では再実行・復元できない（既存の設計。`implementation_differs`・`engine_version_differs`）。CN-1（0.173.0）・V0〜V3-3（0.172.0）の証跡は元の版のまま保持し、使うときはその版の実装を使う。状態の書き出し・スナップショットの形式・確認値の方式は変えていない |
| 配布のファイル | パッケージのファイルの一覧は `ca36ba8` と同じ 62。新しい依存はない（`pyproject.toml` の差は版だけ）。固定コミットの `git archive` から作った wheel を `scripts/check_distribution.py --wheel` で照らした: `required=62 problems=0`（wheel の sha256 `d6550b45…b378`） |
| 固定コミット | `f7bf450580bf0d02573b4d032271be6b8e12d699`（版を 0.174.0 にする） |
| 通常のインストール | 下の手順で 1 回実行し、成功した |

通常のインストールのスモーク:
- リポジトリの外の新しい仮想環境に、`git+https://github.com/moheronemy/kyuura-engine.git@f7bf450580bf0d02573b4d032271be6b8e12d699` を通常のインストール（editable でない）で入れ、リポジトリの外の作業ディレクトリから実行した
- 導入: `direct_url.json` の `commit_id` は `f7bf450…`（`vcs_info`）、読み込みは `site-packages`、実装の識別はソースの木と同じ
- 盤面: ソースで作った構築盤面のスナップショットを復元した（同じ識別でなければ復元できない）
- 確かめた内容（送信はしていない）:
  - `ClientHub` でのにげるの候補は `confirmed`・`unverified`
  - `inputs` には `cost_evaluation` があり、`total_units`・`units` はない
  - 形の check: 控えだけ・控えとエネルギーは valid、エネルギーが先・重なり・存在しない番号は invalid
  - 相手・観戦者の応答に、本当のカード ID がない

証跡:
- `C:/dev/kyuura-engine-verification-vai/verifier/runs/p6-v0.174/`: 実行計画・コマンドと終了コード・テストの出力・到達の記録・配布の照らし・パッケージのファイルの一覧・スモークのスクリプトとスナップショットと出力（スナップショットは本当のカードを含むので verifier だけ）
- `public/runs/p6-v0.174/summary.json`: 非機密の集計

## 7. 残るもの

- R-5 の全体は解消していない。残るのは次のとおり。R-3・R-2・R-4 も残る
  - P2（A 群。見えないカードが選べるものにある実行時の確かめ。通常の到達は未確認）
  - P3〜P5（C 群。この版が続けられない状態）
  - P1・P7・P8（今の登録では生成されない保守の守り）
- うらのバトル場のにげるは `unverified` のまま（受理は送るまで分からない）。宣言の確かめ（その番にもうにげた・ねむり・マヒ・にげられない効果）も、うらの分岐では v0.173 と同じく
  候補の作成で評価していない。エンジンがこれらを、おもてにする前と後のどちらで確かめるかは、今回は確かめていない（コマンドの処理は変えていない）
- new_game からの到達は確かめていない（公開の固定デッキにマチスの秘策がない）。構築盤面の確かめを、通常の対戦での到達の証拠としない
- GUI の追従（5 章）は未着手。検証用 AI は追従した（[verification-ai-p6.md](verification-ai-p6.md)）
