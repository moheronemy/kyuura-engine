# 検証用 AI の P6 への追従（本人のうらのバトル場のポケモンのにげるの入力）

検証用 AI（`tools/verification_ai`）を、エンジン 0.174.0 の P6（[legal-actions-p6-face-down-retreat.md](legal-actions-p6-face-down-retreat.md)）に追従させました。AI の側だけの変更で、
エンジン本体・GUI・renderer・kyuura・カードデータ・固定デッキ・規約集合・裁定・識別の方式・パッケージの版（0.174.0）は変えていません。合法性（エンジン・API）と戦略（方策）の
分離は変えていません。GUI の追従は別の作業に残しています。

| 項目 | 値 |
|---|---|
| 基点 | `claude/p6-face-down-retreat` の `ac64d39`（P6 と既存の AI を含む公開のコミット） |
| 配布を確かめたコミット | `f7bf450580bf0d02573b4d032271be6b8e12d699`（0.174.0） |
| 実行したコミット | `5f0ecf662f23b714b3fc4e6686e1bb5481dd7af3`（AI のコード。`kyuura_engine`・`pyproject.toml` は `ac64d39` と同じ） |
| 実装の識別 | `behavior_digest` `cf279dc9…e129`・`instrumentation_digest` `e7d36df3…3034`（AI の変更の前後で同じ。AI のファイルはパッケージの識別に入らない） |
| 判定の規則の版 | 4（3 から上げた。4 章） |

## 1. P6 の契約の読み取り

P6 の文書・`legal_actions._retreat_candidate`・`_input_problem`・エンジンの `Retreat` の処理・既存のテストを読んで、AI の側の扱いを決めた。

- 段 2（にげるのトラッシュ）の `cost_evaluation` = `{"status": "not_evaluated", "reason": "face_down_reveal_not_evaluated", "omitted": ["total_units", "units"]}` のとき、
  `total_units` と選べるものごとの `units` はない
- AI は、返された控えとエネルギーカードを、`count`（0〜枚数）・重なりなしの制約だけで選び、選んだ順をそのまま送る（`order` `significant`）
- 費用・個数・足りるかを計算しない。`total_units` がないことを費用 0 と読まない
- check が valid なのは形の確かめで、にげられる保証ではない
- おもてのにげる（`total_units` と `units` がある段）は今までどおり、個数の合計で組を絞る

### 1.1 宣言の確かめとおもてにする処理の順（エンジンのコードを読んだ。変えていない）

`engine.apply_command` に `Retreat` を送ったとき:

1. `apply_command` の入口: コマンドの項目、終局・延長戦・停止の段階、保留中の決定の再開先（`_require_supported_decision`）を確かめ、状態を複製する
2. `_reveal_for_action`（`Retreat` はバトル場のポケモンが対象）: バトル場のポケモンがうらなら、`_require_turn`（番・段階）と決定待ちでないことを確かめてから、**おもてにする**
   （`reveal_face_down`）
   - 本当のカードが「たねポケモン」でない: ついているカードといっしょにトラッシュし、空いたバトル場の処理のあと、コマンドを受け付けたことにする（`_retreat` は呼ばれない。
     ねむり・マヒ・にげられない効果・とおせんぼ・費用は確かめない）
   - 「たねポケモン」: 次へ
3. `_retreat` → `check_retreat_declaration`: 控えがいる・ねむり・マヒでない・場での役割のあるカードでない（PF2）・バトル場をはなれられない効果・にげられない効果・とおせんぼ・
   この番のこんらんの失敗
4. `check_retreat`: 入れ替える控えがベンチにいる・にげるエネルギー（`retreat_cost`）・重なり・ついているカード・選んだカードの出す個数（`WRONG_RETREAT_COST` など）
5. 3・4 のどれかが拒否すれば、コマンドごと拒否する（複製を捨てる。おもてにしたことも残らない）

にげるは、この版では「1 番に何度でも」（`_retreat` の説明）。番・段階は 2 で、おもてにする前に確かめる。宣言の確かめ（3）と費用（4）は、おもてにしたあとに確かめる。
たねポケモンでないカードでは、宣言の確かめは一度も行わない。

## 2. 入力の生成の変更（`actions.py`）

- `STAGE_KEYS` に `cost_evaluation` を加えた
- `check_cost_contract`（`build_choices`・`enumerate_inputs` のどちらも、組み立ての前にすべての段に当てる）:
  - `cost_evaluation` がある段: 形が `status`・`reason`・`omitted` の 3 つちょうど、`status` は `not_evaluated`、`reason` は知っている理由（`face_down_reveal_not_evaluated`）、
    `omitted` は `["total_units", "units"]` の並びのリスト、`choose_option` の段で、`total_units` もどの選べるものの `units` もない。どれかが違えば `ContractUnknown`
  - `cost_evaluation` のない段で、選べるものに `units` があるのに `total_units` がない: `ContractUnknown`
  - にげる（候補の種類 `retreat`）のトラッシュの段（role `discard`）で、`total_units` も `cost_evaluation` もない: `ContractUnknown`（費用 0 と読まない）。候補の種類は、
    ランナーが方策の文脈に渡す候補（`context["candidate"]["kind"]`。API の契約の値）から読む。種類の分からない呼び出し（文脈が空）では、この 1 つだけは確かめられない
- `cost_evaluation` の段は、`total_units` のない段と同じ選び方になる: uniform-stage は「選ぶ数 → 重なりのない並び」、uniform-tuple は 0〜枚数のすべての並び
  （`order` `significant` なので並びの違いを別の組として数える）。列挙の上限（`TUPLE_LIMIT`・`NODE_LIMIT`）と、超えたときの段ごとの方式への代替は変えていない
- 本人の観測の `real`・カードの定義・内部の状態で費用を補わない。候補の `card_id` などからカードごとの合法性を判定しない（`actions.py` は `kyuura_engine` を import しない）
- 方策（random・rules-v1・rules-v2・mixed・boundary）は、入力の組み立てに同じ行動生成を使う（方策が選ぶのは候補と、行動生成が渡す並びの位置だけ）。P6 専用の戦略・カードごとの
  分岐は加えていない
- ランナー: P6 の段（`cost_evaluation` あり）の入力の check が invalid なら、異常 `p6_check_invalid_for_generated_input` を記録する（P6 の check は形だけなので、契約から作った入力が
  通らないのは契約との矛盾）。ほかの種類の check の invalid の扱いは変えていない

## 3. deep と boundary

- deep の範囲（`supported`・`may_stop_later`）は広げていない。P6 の候補は `unverified` なので、deep では、ほかに候補がないときの代替（`deep_fallback_unverified`）だけで選ばれる
- boundary は、もともと `unverified` を範囲に入れる。P6 で入力が公開された（`input_disclosure` が `confirmed`）ので、boundary の範囲に入る（v0.173 までは入力を返さないので
  `input_withheld` で外れていた）

## 4. 判定（`judge.py`。規則の版 4）

規則 4 は、にげるの候補で段に `cost_evaluation` がある送信（`judge.is_p6`。API の契約の値だけで決める）にだけ当てる。`cost_evaluation` のない送信は規則 3 のまま。過去の判定
結果（規則 1〜3 の証跡）は書きかえていない。

| 場面 | 判定 | 根拠 |
|---|---|---|
| 形の誤りで check が invalid（AI が契約から作った入力で） | ランナーが異常として記録（送らない） | P6 の check は形だけ |
| check が valid のあと、ホストの段の断り（`refused`） | suspect | 規則 1 から同じ |
| check が valid のあとのエンジンの拒否で、元のコードが `P6_ENGINE_DECIDES`（`WRONG_RETREAT_COST`・`POKEMON_ASLEEP`・`POKEMON_PARALYZED`・`RETREAT_PREVENTED`・`LEAVE_ACTIVE_PREVENTED`・`RETREAT_ALREADY_FAILED`）で、診断の分類がコード表と同じ | normal_rejection（理由に `p6_engine_decides_after_reveal` と条件） | おもてにしたあとに、本当のカード・おもてにしたあとの状態で決まる拒否（1.1 節の 3・4）。API は費用・宣言の確かめを評価しないと契約で示す |
| エンジンの拒否で、元のコードが `P6_API_GUARANTEED`（`DUPLICATE_CARD`・`ENERGY_NOT_ATTACHED`・`NOT_ON_BENCH`・`NO_BENCH`・`NOT_YOUR_TURN`・`DECISION_PENDING`） | suspect | 入力の形・候補を出す条件で API が満たすはずのもの |
| ほかのコードの拒否（停止系でない） | undetermined | 説明できない（unverified だから正常、とはしない） |
| 停止系の拒否 | 規則 3（代表の条件の根拠がなければ undetermined） | known_stop の根拠の登録（`KNOWN_STOP_EVIDENCE`）は、正常な入力の拒否の分類とは別 |
| 診断の分類がない・コード表と違う・failed | suspect | 規則 1 から同じ |
| 受理で、新しいログが `secret_plan_revealed` で始まり `retreat` がある | expected（`p6_revealed_and_retreated`） | `judge_p6_accepted` |
| 受理で、`secret_plan_revealed` で始まり `secret_plan_discarded` がある | expected（`p6_revealed_not_basic_and_trashed`） | 同上（既存の処理でトラッシュ） |
| 受理で、ほかの出来事の並び | undetermined | 受理だけで正常としない |

副作用は、既存の `judge_effects` で受理と拒否を分ける。拒否: 状態・乱数・ログ・決定・停止・区間の確認値と、他者への新しい更新・更新の番号が変わらない。受理: 状態の置きかえと
更新の番号の前進があって当然（公開・状態の変化は正当）。拒否のあとは、同じ取っ手で同じ入力の check に戻れることを `judge_recovery` で確かめる。

`P6_ENGINE_DECIDES` は、元のコードと「その送信の条件」（なぜこの経路で正常か）の表で、カード・場面ごとの登録ではない。今回の実行で起きたのは `WRONG_RETREAT_COST` だけ（5 章）。
ほかの 5 つのコードは、テストの偽物の応答でだけ確かめた。

## 5. 固定確認（構築盤面。new_game からの到達ではない）

`python -m tools.verification_ai.run_p6 run --out C:/dev/kyuura-engine-verification-vai --engine-commit <sha>`（単一のプロセス。1 ケース 20 要求・30 秒、全体 300 秒）。

- 盤面は `fixtures_p6`（P6 のエンジンのテストの `face_down_active` を、0.174.0 の実装から作る。旧版のスナップショットは使わない）。カード固有の準備とケースの選び方は fixture に閉じる
- 開始のスナップショットを保存し、それを復元した対戦を `ClientHub` で包み、公開の API だけで操作する。完全な再現用記録は作らない（new_game からでない）
- にげるの入力は、共通の行動生成 `enumerate_inputs`（uniform-tuple の列挙。boundary の範囲）が作った組から、ケースの選び手（`fixtures_p6.zero_energy`・`one_energy`。方策ではない）が
  選ぶ。**ランダムの方策がこの入力を選んだのではない**。受理のあとの決定（バトル場に出す）は、`build_choices`（uniform-stage・均等の方策。種 `kyuura-vai-p6:promote`）で作った
- 送信はいつも check が valid のあと（`runner.submit_checked`）

| ケース | 本当のカード | 生成した組 | 選んだ入力 | 結果 | 判定 | 要求 |
|---|---|---|---|---|---|---|
| R1 | コラッタ（たね・にげる 0） | `[o1]`・`[o1, o2]` | `[o1]` | 受理（おもてにしてにげた）。古い取っ手は `CANDIDATES_STALE` | normal expected・effects expected・accepted `p6_revealed_and_retreated` | 9 |
| R2 | イワーク（たね・にげる 3） | 同じ | `[o1, o2]` | 拒否 `WRONG_RETREAT_COST`（`invalid_input`）。変化なし（`changed` が空）。うらのまま。同じ取っ手の check は valid | normal_rejection（`p6_engine_decides_after_reveal`）・effects expected・recovery expected | 9 |
| R3 | ユンゲラー（1 進化） | 同じ | `[o1]` | 受理（おもてにしてトラッシュ）。続けて `promote_active` に答えて受理 | normal expected・effects expected・accepted `p6_revealed_not_basic_and_trashed`・follow の normal・effects expected | 13 |

suspect 0・undetermined 0・期待と違うもの 0。全体 0.224 秒。

- 情報境界: 3 つの盤面で、本人の段（`stages`）と、共通の行動生成が作った組が同じだった（`generated_identical_across_cases`・`stages_identical_across_cases`）
- 相手・観戦者の観測のうらの数は、R2 の拒否の前後で同じ（1 → 1。うらのまま。カード ID のあるうらのポケモンは 0）。受理した R1・R3 では 1 → 0（おもてにしたことの公開。
  受理の正当な変化）

## 6. テスト

1 モジュールずつ別のプロセスで実行した（証跡の `tests/test_runs.txt`）。

| モジュール | テスト | 結果 |
|---|---|---|
| `test_verification_ai_p6`（新） | 16 | 1 回目は 3 つがエラー（テストの誤り: uniform-tuple の分布の名前、混合の方策でエピソードを始めずに選んだ）。テストだけ直して再実行し、失敗 0 |
| `test_verification_ai_v0`・`v1`・`v2`・`v2_repeat`・`v3_1`・`v3_2` | 24・19・19・15・15・11 | 失敗 0 |
| `test_verification_ai_v3_3` | 9 | 1 回目は 1 つ失敗（判定の版の確かめ 4 != 3。意図した差）。確かめを 4 に直して再実行し、失敗 0 |

新しいテストの中身:

- 入力の契約: 0 枚・1 枚・2 枚の選択と、選んだ順の両方（uniform-stage）、uniform-tuple の既知の小さな集合（エネルギー 2 枚で 5 組・0 枚で 1 組）と上限を超えたときの代替、
  `units` を求めない（3 枚で 16 組。個数で絞らない）、知らない・矛盾する `cost_evaluation`（`status`・`reason`・`omitted` の不足と並び・余計な項目・dict でない・`total_units` や
  `units` が残る・値の段）と、`total_units` も `cost_evaluation` もないにげるのトラッシュの段・`total_units` のない `units` で止まる（両方の方式）、おもてのにげるは個数で絞る
  （従来どおり）、deep の範囲では作らない、5 つの方策が同じ行動生成を使う、check のない送信がない
- 情報境界: 本当のカードだけが違う 3 つの盤面で、本人の候補・段が同じで、列挙の結果と、同じ種の uniform-stage の選び方が同じ。本人の観測（`real` つき）を文脈に渡しても結果が
  変わらない（本人の観測に `real` があることと、生成がそれを使わないことを分けて確かめた）。方策に渡す文脈は本人の観測・候補・段だけ
- 判定: 規則 4 の拒否の分け方（正常・suspect・undetermined・分類の不一致・分類なし・failed・断り・受理）、`cost_evaluation` のない送信は規則 3 のまま、受理の中身の分け方
- 実行の結果: 3 つの盤面の `run_p6.run_case`（受理と古い取っ手・拒否の無副作用と取っ手・トラッシュと受理のあとの決定）

既存の方策の指紋（`test_verification_ai_v2_repeat` の意味の列の sha256）は、0.174.0 でも値を変えずに通った。指紋は、候補の中身・入力の意味・送信の結果の列から作り、パッケージの版・
実装の識別を含まない（`records.meaning_sequence`）。固定デッキの対戦の経路にうらのバトル場のにげるが現れないので、P6 の変更は指紋の入力に入らない。値は一括で更新していない。

実行していないもの: 全体のテスト・GUI・E2E・seed の探索・大きな対戦・lockstep・状態の監査・R-B。

## 7. 版・過去の証跡

- パッケージの版は 0.174.0 のまま（AI だけの変更）。`behavior_digest` は変わっていない（`cf279dc9…e129`。実行の前に確かめた）
- 0.172.0（V0〜V3-3）・0.173.0（CN-1）の記録・スナップショットは、0.174.0 ではそのまま再実行・復元できない（既存の設計）。過去の証跡は元の版の実装と対応づけて保持し、書きかえて
  いない（マニフェストの更新の前に、既存の 335 ファイルの sha256 が変わっていないことを確かめた）
- 今回の fixture・スナップショットは 0.174.0 の実装から作った。旧版のスナップショットの版・識別を書きかえて使っていない

## 8. 証跡

- `C:/dev/kyuura-engine-verification-vai/verifier/runs/p6-ai-follow/`: 実行の計画（`plan.json`。実行の前に書いた）・ケースごとの fixture の記録（本当のカードを含む）・
  開始のスナップショット・操作の記録（`trace.jsonl`）・ケースの結果・集計・実行の記録（`invocation.json`: 実行のコミット・生成の方式・判定の版・fixture の出典・コマンド・終了コード）・
  テストの出力（`tests/`）
- `public/runs/p6-ai-follow/summary.json`: 非機密の集計（ケースの結果と判定だけ。本当のカード・盤面の中身を含まない）
- マニフェスト: 363 ファイル

## 9. GUI の追従へ渡す注意

- `cost_evaluation` は、形（3 つの項目ちょうど・値）を確かめてから受け付け、知らない値・矛盾（`total_units`・`units` が残る）で止める（AI と同じ扱い）
- `cost_evaluation` も `total_units` もないにげるのトラッシュの段は、費用 0 と読まずに止める
- 費用・個数を表示・計算しない（本人の観測の `real` から求めない）。0〜枚数のどの選び方も、check は形だけで valid になる
- 送る前の check の門に、この段（または `retreat`）を入れる（GUI の今の門は `total_units` のある段だけ。P6 の文書 5.1 節）
- エンジンの拒否（`WRONG_RETREAT_COST` など）は本人だけに返り、状態は変わらず、取っ手も失効しない。同じ候補で選び直せる
- 受理は 2 通り: おもてにしてにげる、または本当のカードがたねポケモンでなければトラッシュされ、バトル場に出す決定（`promote_active`）が続く
- 宣言の確かめ（ねむり・マヒなど）は、おもてにしたあとにだけ行う（1.1 節）。うらのあいだに GUI が推測して止めない

## 10. 未確認

- `P6_ENGINE_DECIDES` のうち、`WRONG_RETREAT_COST` 以外の 5 つのコードは、実際の拒否で起きていない（テストの偽物の応答だけ）
- new_game からの到達（公開の固定デッキにマチスの秘策がない）。構築盤面の結果を、通常の対戦での到達の証拠としない
- ランダムの方策が、実際の対戦で P6 の入力を選んだこと（今回の固定確認はケースの選び手が選んだ）
- 種類の分からない呼び出し（文脈に候補がない）での、「にげるのトラッシュの段で total_units も cost_evaluation もない」の確かめ（ランナーの経路はいつも候補を渡す）
