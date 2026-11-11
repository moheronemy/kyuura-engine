# 検証用 AI のバッチ: 明示的なデッキリストと方式 boundary

- 状態: 実装・限定確認済み（2026-11-11。実装 `58fa44b`。計画・完了の形式 5・TOOL_VERSION 6・判定の規則 6 のまま・パッケージ 0.179.0 のまま）
- 対象: 逐次バッチ（[verification-ai-batch.md](verification-ai-batch.md)）の計画で、固定デッキのほかに明示的なデッキリストを指定できるようにし、既存の boundary の選び方
  （[verification-ai-v3-2.md](verification-ai-v3-2.md) 4 章）を方式として選べるようにする。あわせて、主体別の観測の記録（[verification-ai-observation.md](verification-ai-observation.md)）の
  失敗・欠落のときの停止と完了の扱いを確かめ、不足を補った
- 対象外（実行していない）: 新しい対戦バッチ・seed の探索・デッキの自動生成と最適化・対象デッキの採用と比較の実行・新しい方策と判定の規則・P6・U-R3a への到達を保証する固定の選び手。
  エンジン・GUI・renderer・カードデータ・固定デッキ・規約集合・裁定・識別方式・パッケージの版は変えていない

## 1. 合法性と戦略の分け方

| 責任 | 持つもの |
|---|---|
| デッキの形（入力の検証・展開の順・確認値） | `tools/verification_ai/decklist.py`（新規。`kyuura_engine` を import しない） |
| デッキの合法性（60 枚・同じ名前の枚数・カードの登録・たねの有無など） | エンジンの `kyuura_engine.deck.deck_problems` だけ。バッチは結果を記録して、不合格なら対戦を始めない |
| 候補の範囲（どの処理可能性・開示の候補を選べるか） | runner のプロファイル（deep・boundary。既存の `_scope`） |
| 候補の選び方 | 既存の方策（uniform・rules・mixed・boundary）。カード名・カード ID による戦略は足していない |

## 2. 使い方

```
python -m tools.verification_ai.batch decklist --file <明示リスト.json>
python -m tools.verification_ai.batch plan --out <証跡> --batch <名前> --engine-commit <sha> --tool-commit <sha> --seeds 1001 ... \
    --modes uniform-stage boundary --observation [--deck0 <固定デッキ> | --decklist0 <JSON>] [--deck1 <固定デッキ> | --decklist1 <JSON>]
```

- `decklist` は形・確認値・`deck_problems` を確かめて記録を表示するだけ（計画は作らない・対戦しない）。不合格・形の誤りは終了コード 2
- 側ごとに、固定デッキ（`--deck0`）か明示リスト（`--decklist0`）のどちらか 1 つ。両方を指定すると曖昧なので拒否する（計画のディレクトリも作らない）。どちらもなければ既定の固定デッキ
- `--observation` か `--no-observation` のどちらかを必ず指定する（既定を置かない）。新しい計画では `--observation` を使う方針（7 章）
- API では `make_plan(..., decklists={"0": decklist.load_file(path)})`

## 3. 明示リストの形式（`kyuura-vai-decklist/1`）

```json
{"format": "kyuura-vai-decklist/1",
 "label": "人が見分けるための名前",
 "source": {"description": "どこから来たリストか", "reference": "任意: 文書・コミットなど"},
 "cards": [["PMCG1-058", 4], ["PMCG1-029", 4], ...],
 "content_sha256": "<内容の確認値>"}
```

厳密に検証し、次のものは拒否します（`DecklistError`。計画を作らない）。

- 知らない項目・足りない項目・知らない形式の版、`source` の知らない項目・`description` の欠け
- 型の違い: `cards` が並びでない、項目が `[カード ID, 枚数]` の 2 つの並びでない、枚数が整数でない（`true`・`4.0`・`"4"`）、枚数が 1 未満
- カード ID の形（英数字と `.`・`_`・`-`、64 文字まで）。同じカード ID の重複（大文字・小文字の違いも重複として扱う。同じカードは 1 項目にまとめる）
- 空のリスト。過大な入力（ファイル 64 KiB・項目 200・枚数の合計 1,000 を超える。入力の大きさの上限で、デッキの規定ではない）
- `label`・`source` の空・長すぎ・制御文字。JSON の同じキーの重複・`NaN`・`Infinity`・UTF-8 でないバイト列
- `content_sha256` が 64 桁の小文字の 16 進でない、または `cards` から計算した値と違う（エラーに計算した値を示す）

`source` は来歴の記録です。信頼性・合法性を保証する値としては扱いません。

外部ファイルは、計画を作るときに 1 回だけ読み、内容を各局の `decks` に取り込みます。入力の記録（ファイル名・バイト数・sha256）も残しますが、再開ではファイルを読み直しません
（ファイルを変えても消しても、確定計画と照合は変わらない。テストで確認）。URL からの取得はしません。

## 4. 並び・確認値・正規化

| 値 | 定義 | 意味 |
|---|---|---|
| 展開 `expansion` | 明示リスト `entries-in-order/1`: `cards` の並びのまま、カード ID を枚数ぶん続けて並べる。固定デッキ `preset-entries-in-order/1`: `PresetDeck.cards()`（登録の項目の並び） | どちらも `kyuura_engine.deck.expand_decklist` と同じ規則。入力の並びを保持し、ID 順へ並べかえない |
| `content_sha256` | カード ID の順（コードポイント順）に並べた `[ID, 枚数]` の並びの sha256 | 内容の同一性（並びに依らない）。`label`・`source` は含めない |
| `sha256` | 展開した 60 枚の並びの sha256 | 実際の初期配列の同一性。固定デッキの既存の記録 `sha256` と同じ定義 |

- 同じ内容でも並びが違えば `sha256` が違い、同じ seed での初期の山札の切り方の結果も違いうる。並びを変えたリストは別の条件として扱う
- 固定デッキの並びは変えていない。`hitmonchan-dewgong-v2`・`venusaur-parasect-v2` の `sha256` は C1・C2 の計画の値と同じ（テストで照合）
- 固定デッキと同じ内容・同じ並びの明示リストは、`content_sha256`・`sha256` とも固定デッキと同じで、seed 12・操作 80 の局の行動の列は既存の固定値（`ACTION_GOLDEN`）と同じ（テストで確認）
- 計画の局の `config.decklists` に、両側の実行用の並びを書く（明示リストが 1 つでもある局だけ。固定デッキの側は `PresetDeck.cards()` の並び）。固定デッキだけの局は、これまでどおり `null` で、runner が固定デッキを読む
- 明示リストの側の表示用の名前は `decklist:<content_sha256 の先頭 12 桁>`（集計の比較の組・`by.decks` で使う。カードの中身を公開の集計に出さない）

## 5. 合法性の検査

- `deck_problems`（規則 `JP-2000.02.14`）を、計画を作るとき・再開の照合（`load_plan` の `check_entry`）・各局の開始の直前（`play` の中、`run_game` の前）に当てる
- 結果（`checked_by`・`rules`・エンジンの版と `behavior_digest`・`ok`・`problems`）を各局の `decks.<側>.legality` に記録する。規約集合は局の `conventions`、実装識別は計画の `identity`
- 不合格なら計画を作らない（ディレクトリも作らない）。計画のあとで結果が変わった（記録と違う・不合格になった）ら、再開を拒否し、局を始めない
- バッチは枚数制限・カードの登録・たねの有無を自分で判定しない

## 6. boundary の接続

確認した既存の関係: 方策（`Config.policy`）とプロファイル（`Config.profile`）は別の設定です。

- プロファイルは runner の候補の範囲（`_scope`）と、段の選べるものの許す処理可能性を決める。deep は `supported`・`may_stop_later`（範囲が空なら `unverified` に代える。`deep_fallback_unverified`）、
  boundary は `supported`・`may_stop_later`・`unverified`。どちらも表示だけの候補・入力の開示が未確認（withheld）の候補・実行できない区分（`unresolved_ruling`・`not_implemented`・`technical_limit`）を外す。
  `inputs` の応答が withheld なら送らない
- 方策 `boundary`（`BoundaryPolicy`）は、渡された候補の処理可能性の区分を均等に 1 つ、その区分の候補を均等に 1 つ選ぶ。入力は uniform-stage
- V3-2 で定義した組は「方策 boundary + プロファイル boundary」だけ。`MODES` に文字列を足すだけでは profile が deep のままになるので、方式 `boundary` を
  `{"policy": "boundary", "profile": "boundary"}` として足し、計画の `config` に展開する

計画に書ける方策・プロファイル・分布の組（`SUPPORTED_SETTINGS`）は次の 5 つだけです。ほかの組（rules・mixed・uniform のプロファイル boundary、方策 boundary のプロファイル deep、
boundary の uniform-tuple など）は、計画を作るとき・再開の照合で拒否し、別の方式へ読み替えません。混合の方策の boundary 化は既存の実装にないので足していません。

| 方式 | 方策 | プロファイル | 分布 |
|---|---|---|---|
| uniform-stage | uniform | deep | uniform-candidate+uniform-stage |
| uniform-tuple | uniform | deep | uniform-candidate+uniform-tuple |
| rules-v1・rules-v2 | rules | deep | uniform-candidate+uniform-stage（設定の値） |
| mixed | mixed | deep | 同上 |
| boundary | boundary | boundary | 同上 |

- deep の範囲・代替・方策の順位・乱数の消費は変えていない（runner・policies・actions は変更なし。既存の行動の指紋のテストが同じ）
- 記録: 各試みの `scope.profile`、候補の区分 `candidate_class`（候補の処理可能性）、完成した入力の区分 `input_processability`（選んだものごとの処理可能性といちばん進めにくい区分）、段の選べるものの処理可能性（`stages`）を分けて trace に残す（既存の V3-2 の記録）
- check の valid は、受理・完走の保証として扱わない（受理・拒否・停止はエンジンの結果と judge で数える）

## 7. 観測の記録の失敗・欠落のときの扱い

既存のコードとテストで確かめたこと:

- 記録の例外は runner が `recorder_failed` として記録に残し、対戦は記録なしと同じに進む。欠けは `incomplete`、矛盾は `inconsistent`。局の要約の状態が `complete` でなければ、停止方針（`on_observation_problem`。既定は `stop`。CLI で `continue` にする手段はない）で次の局へ進まずに止まる
- その局の完了マーカーは書かれるが、`stop` に理由が入る。再開は `--acknowledge-stop <game_id>` で台帳に確認を書くまで拒否する（自動で確認済みにしない）
- adapter の中の例外（記録のファイルを作れないなど）はマーカーを書かず `INCOMPLETE.json` を残し、次の実行では別の attempt で最初からやり直す（失敗した attempt を採用しない）

不足していて補ったこと（`58fa44b`）:

1. 観測を有効にした計画で、局の要約に観測の状態がないと止まらなかった → `observation:missing` で止める
2. 完了マーカーが成功と停止つきを直接は区別しなかった → `evidence`（`complete_without_stop`・`complete_with_stop`）を書く。集計の `games` に `complete_without_stop`・`complete_with_stop` を足した
   （`--acknowledge-stop` のあとも停止つきの完了として数え、成功した局と混ぜない）
3. 照合が、マーカーの `stop` と要約・`observe/summary.json` の状態の整合を見なかった → `verify_complete` で停止の理由を要約から計算し直して `stop`・`note`・`evidence` と照らし、
   `observe/summary.json` の状態とマーカーの要約の観測の状態を照らす。合わないマーカーの局は採用せず、再開を拒否する

「対戦の進行が記録なしと同じ」ことと「検証の証跡として成功した」ことは別に扱います。新しい計画では観測の記録を有効にし（`--observation`）、記録の失敗・欠落を無視して続ける初期値は置きません。
圧縮・差分化・間引き・ハッシュの確かめの省略は足していません。

## 8. 計画・保存・再開・識別と互換性

- 計画の形式 `kyuura-vai-batch-plan/5`・完了の形式 `kyuura-vai-batch-complete/5`・TOOL_VERSION 6
  - 上げた理由: 局の `decks` の記録の形（種類・展開・内容の確認値・合法性）、`config.decklists` の使い方、方式 boundary と組の照合、完了マーカーの `evidence` と照合の規則が変わったため
  - 計画には `decks`（側ごとの名前・明示リストの側・規則の説明）と `settings`（定義した組）を書く。局ごとに `config`（方策・プロファイル・分布・seed・上限・実行用の並び）・`decks`・`conventions`・`policies`
    を既定値まで展開して書き、計画の sha256 にすべて入る
- 再開の照合（`load_plan`）: 計画の sha256・形式・実装識別に加えて、各局で、デッキの記録を記録の中身から作り直して比べる（内容・並び・確認値・合法性）、実行用の並びと展開を比べる、
  方策・プロファイル・分布の組、規約集合、方策の設定を比べる。改変・不一致は拒否し、局を始めない
- `label`・`source`・入力ファイルの記録は内容の確認値に入れない来歴なので、改変は計画の sha256（計画を作ったときの値）と完了局のマーカーの `plan_sha256` で見つける
- 必須証跡: 完了マーカーに `evidence`・`stop`・`note`・`required`（観測の記録の 5 ファイルを含む）と、局の見出し `header.json` の `batch.decks`（側ごとの種類・名前・展開・確認値）
- 旧形式: 形式 4 以前の計画（30 局 vai-batch-b1・99 局 vai-batch-b2・C1・C2・観測の記録の版で作った計画）は、この版で再開・集計しない。旧計画の固定デッキの記録を新しい形へ暗黙に読み替えない。
  旧バッチは、それぞれ計画の `identity.tool`（道具の sha256）と `commits` が示す元の道具と対応付けて保持する（旧記録に継ぎ足していない）
- 実装識別: 道具の識別（tools/verification_ai の .py の sha256）は `edc20bef…83bb`（TOOL_VERSION 5。`fb22693`・`6aabd19`）から `4f97edbf…2deb`（TOOL_VERSION 6・判定の規則 6。`58fa44b`）。
  エンジン 0.179.0・`behavior_digest` `67c4c15b…7fca` は同じ

## 9. 限定確認（2026-11-11）

関連の 10 モジュールを 1 つずつ別のプロセスで実行し、すべて成功しました（163 件・失敗 0・エラー 0・スキップ 0・合計 49 秒）。全体のテストは実行していません。

| モジュール | 件数 | 主な対象 |
|---|---|---|
| decklist_boundary（新規） | 23 | 形式の正常形と不正な入力・厳密な JSON・確認値と展開の順と出典の記録・固定デッキの並びの維持・deck_problems による開始前の拒否・外部ファイルの変更後も計画が同じ・再開の改変検出・boundary の設定が runner に届く・定義していない組の拒否・boundary と deep の範囲・BoundaryPolicy の区分の選び方・観測の記録の失敗と欠落での停止・マーカーの改変の不採用・CLI |
| batch | 27 | 保存・ハッシュ・ロック・上限・再開・停止方針・集計の回帰、既存の方策の行動の指紋（`ACTION_GOLDEN`） |
| batch_judge | 11 | 判定の規則 6 の回帰 |
| observation | 16 | 観測の記録（fixture 6 ケース）と、記録つきの計画の局 |
| er9_evidence | 7 | 規則 6 と TOOL_VERSION |
| v2_repeat | 16 | 方策の行動の指紋・契約の値 |
| v3_2 | 11 | 既存の boundary の方策・プロファイル |
| p6・u_r3a・v0 | 16・12・24 | 既存の runner・判定の回帰 |

テストの中の本物のエンジンの局（対戦バッチの実績ではない）:

- 明示リスト（固定デッキと同じ内容・並び）で seed 12・操作 80 の 1 局: 行動の列が `ACTION_GOLDEN["uniform-stage-s12"]` と同じ
- 方式 boundary・観測の記録つきで seed 12・操作 40 の 1 局の一時ディレクトリのバッチ: 方策・プロファイルが boundary として見出しに入り、すべての試みの候補は実行できる区分で開示が未確認でない。
  候補の区分と完成した入力の区分を分けて記録し、観測の記録は complete
- 既存のテストの局（batch・observation の seed 12）

計画の作成の例（対戦なし）と拒否の例を証跡の `examples/` に残しました（11 章）。

## 10. 制限・未確認と次の小規模バッチへ渡す事項

- 明示リストで動かした新しい対戦バッチ・boundary のバッチの実績はない。テストの中の短い局だけ
- boundary の通常の進行で `unverified` の候補が実際に出て選ばれる場面は、今回のテストの局では確かめていない（範囲・区分の選び方は偽の候補で確認。new_game からの到達は残件のまま）
- 方式 boundary の局の judge の扱いは既存のまま（`unverified` の送信が増えると undetermined・known_stop の内訳が変わりうる）。停止方針の既定は変えていない
- 観測の記録つきの局の証跡は約 2.2 倍（[verification-ai-observation.md](verification-ai-observation.md) 8 章）。boundary の局の量は未計測
- 次の計画へ渡す事項: 使うデッキの明示リスト（出典・`content_sha256`）を計画の前に `decklist` で確かめて固定する。方式に boundary を入れるなら、比較の組（同じデッキ・規約集合・seed）で deep の方式と並べる。
  `--observation` を付ける。証跡の上限（`--evidence-max-mb`）を観測の記録の分だけ見込む。選べるものの数を伏せる決定・相手が答える決定が出る局で、記録が相手・観戦者に伏せていることを確かめる

## 11. 証跡

`C:/dev/kyuura-engine-verification-vai/verifier/runs/vai-decklist-boundary/`（デッキの内容を含む。公開しない）:

- `00_plan.md`（実装とテストの前に保存した対象・期待・上限）
- `tests/`（10 モジュールの文字の出力と JUnit・終了コードと所要時間）、`junit_run.py`
- `examples/`（明示リストの例・`decklist` の出力・一時ディレクトリに作った計画・拒否の例・確認値の比べ）、`make_examples.py`。1 回目の例の作成で、拒否の例の 1 つ（整数でない枚数）が
  例の作り方の誤りで置きかわらなかった出力を `run1_examples_bad_replace/` に残し、作り方を直して 1 回だけ作り直した（検証のコードの誤りではない）
- `identity_after_change.json`・`engine_identity.json`・`compatibility.md`・`commands.txt`
- 公開の要約: `public/runs/vai-decklist-boundary/summary.json`（件数と状態だけ）
