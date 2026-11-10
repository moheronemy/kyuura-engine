# 検証用 AI の 0.176.0（PT-5e）への追従と、行動の列と API の契約の値の比べの分離

[PT-5e](legal-actions-pt5e-audit.md)（v0.176.0）で、山札から引いて試すトレーナー 6 枚の使うための条件を候補の作成で呼ぶようになりました。検証用 AI（`tools/verification_ai`）を
これに追従させました。AI の側だけの変更です。エンジン・GUI・renderer・kyuura・カードデータ・固定デッキ・規約集合・裁定・識別方式は変えていません。パッケージの版は 0.176.0 のままです。

## 0. 基点と範囲

| 項目 | 値 |
|---|---|
| 基点 | `fba415af2bc450050ef89a1cf80a303396d7cd32`（`claude/pt-5e-impl`。PT-5e の実装 `9b1d098`・版 0.176.0 の `6f62700`・文書と、既存の AI（U-R3a の追従をふくむ）を含む。`origin/main` には入っていない） |
| 作業ブランチ | `claude/vai-0176-follow`（専用の worktree `C:\dev\kyuura-engine-vai`。利用者の `C:\dev\kyuura-engine` は触っていない） |
| AI のコードとテストのコミット | `41c819d1ad6a2433a5360323fad0ef908642ebcf`（テストはこのコミットと同じ作業ツリーで実行） |
| 実行の前の計画 | 証跡の `verifier/runs/vai-0176-follow/plan.json`（コードを変える前・テストの前に書いた）。PT-5e の実行の計画（`pt5e-v0.176/plan.json`）は実行のあとに書いたもので、そのことはその記録に残したまま。今回の計画とは混ぜない |
| 対象外 | GUI の追従、`ClientHub.from_state` の入口の不変条件（PT5E-FROM-STATE-INVARIANT）、受理の前の先読み（D）、ほかの残件 |

## 1. 指紋のテストの 4 件の失敗の原因

`tests/test_verification_ai_v2_repeat.py` の `UnchangedTest` は、上限 80 の操作の小さな対戦 4 つ（uniform-stage-s12・uniform-tuple-s12・rules-v1-s13・mixed-v1-s13）の
`records.meaning_sequence` の sha256 を固定値（`1aad030` で取った値）と照らしていました。0.176.0 で 4 件とも失敗しました（行の数は同じ）。

| 確かめたこと | 結果 |
|---|---|
| 指紋に入れていた項目 | 1 行 = 1 回の試み。主体・候補の中身（応答ごとの `id` だけを除く。処理可能性・理由・eligible・**保証の文**・choices_format・入力の段の要約・入力の公開をふくむ）・入力の意味（選べるものの中身。評価の値をふくむ）・作れたか・check・送信の結果・断り・拒否・診断のコード |
| 0.175.0 と 0.176.0 の差（6 つの小さな対戦を両方のコードで実行し、行ごと・葉ごとに比べた） | 違う葉は 6 つの対戦のすべてで `candidate.guarantees.preconditions` だけ。違う行はどれも `play_trainer` の候補（10・12・7・16 行と、rules-v2-s13 の 11 行・mixed-v2-s13 の 16 行）。行動・入力・check・結果・診断に差はない |
| 保証の文が入力の選択・方策の乱数の消費に影響するか | しない。方策（`policies`）と行動生成（`actions`）は保証の文を読まない。反復の抑制の鍵（`policies.action_key`）は評価の値（`EVAL_FIELDS`。`guarantees` をふくむ）を除く。両方の版で鍵の列・抑えた回数が同じ。ランナーの「同じ状態で試した」の照らし（`runner.candidate_key`）は候補の中身を使うが、1 つの対戦の中で同じ版の文どうしを比べるだけで、版の間の動作は変えない |
| 原因の調べの証拠 | PT-5e の作業で、保証の文を 0.175.0 の文に置きかえると 4 件とも旧い指紋に一致することを確かめた（`pt5e-v0.176/ai_impact/`）。この確かめは原因の証拠として残し、応答を旧い文に書きかえてテストを通す修正にはしていない |
| 行動の列の意味と API の説明の文の混在 | あった。旧い形式は行動と契約の値を 1 つの行に混ぜていたので、契約の文の変更だけで「方策の列が変わった」ように見えた |

## 2. 行動の列と API の契約の値の比べの分離（形式の版）

比べの目的を 2 つに分け、別の形式・別の指紋にしました（`tools/verification_ai/records.py`）。

| 形式（`format`） | 関数 | 目的 | 含めるもの | 除くもの |
|---|---|---|---|---|
| `meaning/v1`（旧。変えていない） | `meaning_sequence` | 保存済みの証跡（V0〜V3・P6・U-R3a の `meaning.jsonl` など）との照らし | 上の 1 章のとおり（行動と契約の値が混ざる） | 取っ手・`operation_id`・時間 |
| `action-meaning/v2`（新） | `action_sequence` | 行動・入力・結果の再現の比べ | 主体・候補の種類と対象（候補の中身から `EVAL_FIELDS` を除いたもの）・選んだ入力（段の番号と、選べるものの中身から同じ値を除いたもの、または `value`。**選んだ順のまま**。並びに意味のない段も並べかえないので、方策の選び方の差も見える）・作れたか・check の結果と断りのコード・送信の結果・断り・拒否・診断のコード | 取っ手（`id`・`after`・`game`・`revision`・`operation_id`）と評価・説明の値（`processability`・`reasons`・`eligible`・`guarantees`・`choices_format`・`input_stages`・`input_disclosure`）。除いた値は次の形式で比べる |
| `candidate-contract/v1`（新） | `contract_sequence` | API の契約の値の比べ（行動の列と同じ行に対応） | 候補の評価・説明の値（`EVAL_FIELDS` から取っ手 `id`・`after` を除いたもの）・inputs の段の契約（応答のまま。制約・注記・選べるものとその評価の値）・選んだ選べるものの評価の値 | 正規化しない（保証の文の変更もここで差になる） |

- 指紋は `records.sequence_digest(rows, format)` で、形式の名前・行の数・sha256 の組にする。形式の違う指紋を同じ値として比べない
- `EVAL_FIELDS` は反復の抑制の鍵と同じ集合を使う（定義は `policies` の 1 か所）。行動の列の対象・入力の表現は、反復の抑制の鍵と同じ除き方で、違うのは並びに意味のない段を並べかえないことだけ（再現の比べは鍵より厳しい）
- 反復の抑制の鍵・抑制の動作は変えていない
- 方策・入力生成・ゲームの乱数の消費は変えていない（新しい関数は記録を読むだけ）

### 2.1 移行の根拠

| 根拠 | 内容 |
|---|---|
| 版の間の計測（証跡 `migration_compare.json`） | 1c0fc07（0.175.0。AI のコードは fba415a と同じ）に新しい記録の関数だけを重ねた木と、今の木で、6 つの小さな対戦（既存の GOLDEN の 4 つと rules-v2-s13・mixed-v2-s13。上限 80 の操作）を実行した。`action-meaning/v2` の指紋は 6 つとも両方の版で同じ。`candidate-contract/v1` は 6 つとも違い、違う葉は `play_trainer` の `guarantees.preconditions` だけ。0.175.0 の木の `meaning/v1` は 4 つとも既存の GOLDEN と一致した（旧い指紋の来歴の確かめ） |
| 小さなテスト（`tests/test_verification_ai_v0176_follow.py` の `FormatTest`） | 保証の文だけを変えた行: 行動の列は同じ、契約の列と旧形式は違う。取っ手だけを変えた行: 行動の列は同じ。主体・種類・対象・入力・意味のある順序（選んだ順）・`value`・作れたか・check・送信の結果・断りを変えた行: 行動の列が違う。処理可能性・eligible・理由・入力の公開・choices_format・選んだものの処理可能性・段の制約・段の注記を変えた行: 行動の列は同じで、契約の列が違う。3 つの形式の名前と指紋が別。旧形式の中身は変えていない。反復の抑制の鍵は保証の文によらない |
| 固定値（`tests/test_verification_ai_v2_repeat.py`） | `LEGACY_MEANING_V1_AT_0175`（旧い指紋。来歴として残し、今のコードとは比べない）、`ACTION_GOLDEN`（0.175.0 と 0.176.0 で同じ値）、`CONTRACT_GOLDEN_0176`（0.176.0 の契約の値。エンジンの契約が変われば変わる。変わったら差を調べ、来歴つきで更新する）。同じテストで、check を経ない送信がないことも確かめる |

保証の文の差（0.175.0 → 0.176.0。`play_trainer` の `guarantees.preconditions`）: 「…使うための条件のうち、おもての部分の上で実際の山札から引いて試すもの（`PLAYABLE_NOT_EVALUATED`）は呼ばない（unverified）」が、
「…v0.176: おもての部分の上で山札から引いて試す使うための条件（`PLAYABLE_FACE_UP_PREFIX_TRIALS`）を呼ぶ。結果は本人の手札・公開の枚数と、おもての山札の並びの不変条件で決まる。
この不変条件が成り立たない状態では呼ばない（unverified）。effects.py の外で定義した条件も呼ばない（unverified）」になった。全文は証跡の `migration_compare.json` の `guarantee_text_changes`。

## 3. PT-5e による選ぶ範囲の変化と判定

AI の範囲はカードの一覧で決めず、API の処理可能性・eligible・入力の公開だけで決まります（`actions.option_allowed`・ランナーの `_scope`。変えていない）。

| 代表（構築盤面。new_game からの到達ではない） | API の値 | deep | boundary・代替 | 根拠 |
|---|---|---|---|---|
| 通る（カツラのクイズ その2） | `may_stop_later`・eligible・理由 `preflight_not_evaluated`・`continuation_not_evaluated` | 選ぶ | 選ぶ | 保存済みの証跡（`pt5e-v0.176/install_smoke_output.json`。6f62700 の Git の URL からのインストール）と、接続のテスト（候補が `_scope` に入る・check が valid・送信が受理） |
| ゲーム上使えない（ポケモン性格判定。進化カードなし） | 選べるものに出ない | 出ない | 出ない | 同上 |
| 未裁定・未対応（カードめくりゲーム。FU3） | `unresolved_ruling`・eligible でない・`stops_before_acceptance` | 選ばない | 選ばない | 同上（check は `CANDIDATE_NOT_EXECUTABLE`、更新 0 件） |
| 不変条件の崩れた状態（テスト専用の改変） | `unverified`・eligible・`use_condition_not_evaluated` | 選ばない | 選ぶ | 保存済みの証跡（`pt5e-v0.176/twin_results.json` の `prefix_guard`）と接続のテスト |

- 保存済みの応答に AI の範囲の関数を当てた結果は証跡の `pt5e_saved_scope.json`。接続のテスト（`PT5eScopeTest`）は既存のエンジンのテストの盤面（`table`・`staged`・`broken_marks`）を使い、新しい固定の対戦は加えていない
- 判定（`judge.py`）は変えていない。`play_trainer` は `PRECHECK_KINDS`（受け付ける前の確かめを API が保証する種類）に入っていないので、check の成功を受理・完走の保証として扱わない: check のあとの入力の拒否は `normal_rejection`、停止系の拒否は、未評価の理由（`preflight_not_evaluated` などは `EXPLAINING_REASONS` にある）があっても、代表の条件の根拠（`KNOWN_STOP_EVIDENCE`）がなければ `undetermined`（`known_stop` にしない）。受理は `expected`。受理のあとの停止は `judge_halt_after_accept` の既存の扱い
- 今回の 4 つの小さな対戦には対象の 6 枚が出ない（契約の列の差は保証の文だけ）。通常の対戦で 6 枚が選ばれる場面は確かめていない

## 4. 版の説明

`fixtures_u_r3a.py`・`fixtures_p6.py` の「今の実装（0.175.0／0.174.0）から作る」を、実際の依存（実行するときのエンジンの実装から作る。過去の実行のときの版は実行の記録に残る）に直しました。
過去の実行の記録の版は書きかえていません。

## 5. 限定の検証の結果

- 実行: 関連する AI のモジュールを 1 つずつ別のプロセスで（PowerShell、MSYS=noglob、PYTHONIOENCODING を外す）。コマンド・出力・終了コードは証跡の `tests/`
- 結果: 6 章の表
- 対象外: V0〜V3 の実対戦の再実行、全体のテスト、GUI、E2E、大量の対戦、seed の探索、lockstep、状態の監査

## 6. テスト

AI のコードとテストのコミット `41c819d1ad6a2433a5360323fad0ef908642ebcf` と同じ作業ツリーで実行しました（1 回目で、すべて失敗 0。修正・再実行なし）。

| モジュール | 件数 | 結果 | 秒 |
|---|---|---|---|
| `tests.test_verification_ai_v0176_follow`（新） | 11 | OK | 2 |
| `tests.test_verification_ai_v2_repeat` | 16 | OK | 11 |
| `tests.test_verification_ai_v0` | 24 | OK | 4 |
| `tests.test_verification_ai_v1` | 19 | OK | 4 |
| `tests.test_verification_ai_v2` | 19 | OK | 5 |
| `tests.test_verification_ai_v3_1` | 15 | OK | 4 |
| `tests.test_verification_ai_v3_2` | 11 | OK | 3 |
| `tests.test_verification_ai_v3_3` | 9 | OK | 2 |
| `tests.test_verification_ai_p6` | 16 | OK | 2 |
| `tests.test_verification_ai_u_r3a` | 12 | OK | 2 |

- 変更の前（fba415a）の `v2_repeat` は 15 件のうち 4 件が失敗（`pt5e-v0.176/tests/`）。変更のあとは 16 件（旧い指紋を来歴として残すテストを 1 件加えた）で失敗 0
- rules-v1・rules-v2・mixed・ランダム（uniform-stage・uniform-tuple）の選び方が変わっていないこと: `ACTION_GOLDEN` の 4 つ（0.175.0 と同じ値）と、移行の計測の rules-v2-s13・mixed-v2-s13（両方の版で行動の列・反復の抑制の鍵の列・抑えた回数が同じ）。rules-v2 の抑制の動作は `v2_repeat` の既存のテスト
- P6・U-R3a の判定: `test_verification_ai_p6`・`test_verification_ai_u_r3a` が失敗 0（判定のコードは変えていない）
- 移行の計測の 12 の小さな対戦（6 つ × 2 つの版）は 24 秒、終了コード 0

## 7. 版・識別・過去の証跡

- パッケージの版 0.176.0、`behavior_digest` `337caa88c8419c803e90a98d92fa8d36622bb7db161c057288221243b97932ea`、`instrumentation_digest` `e7d36df3…3034`、識別方式 `kyuura-package-files-sha256/1` は、AI の変更の前後で同じ（AI のコードは識別の対象のファイルではない）
- 0.175.0 以前の記録・スナップショットは元の実装と対応づけたまま残す。識別を書きかえて新しい版で使わない。保存済みの `meaning.jsonl` は `meaning/v1` の形式のまま

## 8. GUI の追従へ渡すこと

- AI の変更は GUI の契約に影響しない（エンジンの API・版・識別は変えていない）。GUI の追従は PT-5e の文書（監査の 9 章）の事項のまま: 固定するエンジンのコミット（6f62700 以降）・契約の engine の値・版を確かめるテスト・`engine-contract.md` の更新
- 保証の文（`play_trainer` の `guarantees.preconditions`）が変わった。GUI が保証の文をそのまま表示・照合しているなら、その差を見込む
- 6 枚の選べるものの処理可能性が `may_stop_later`・選べるものなし・実行できない区分・`unverified`（崩れた状態だけ）に分かれる。値の語彙は増えていない

## 9. 証跡

`C:/dev/kyuura-engine-verification-vai/` の `verifier/runs/vai-0176-follow/`（検証者だけ）と `public/runs/vai-0176-follow/summary.json`（非機密の集計だけ）。

| ファイル | 中身 |
|---|---|
| `plan.json` | 実行の前の計画 |
| `migration_games.py`・`migration_compare.py`・`migration_compare.json`・`migration_games_0175.json`・`migration_games_0176.json`・`migration_commands.txt` | 版の間の計測（6 つの小さな対戦の 3 つの形式の列）と、形式ごとの比べ・保証の文の差・コマンドと終了コード |
| `pt5e_saved_scope.py`・`pt5e_saved_scope.json` | 保存済みの PT-5e の応答に AI の範囲の関数を当てた結果 |
| `tests/` | テストの実行のスクリプト・モジュールごとの出力・終了コード |
| `identity_after.json`・`code_diff_stat.txt`・`code_diff.patch` | 変更のあとの実装の識別と、コードの差 |

マニフェスト（`manifest.json`・`sha256.json`・`MANIFEST.md`）は、既存の 484 ファイルが変わっていないことを確かめてから、509 ファイルに更新しました
（`sha256.json` の sha256 は `94044b668adee1bb4932eac08b7b737d406d49a7eb2ac74a11790daf4b84fcbc`）。

## 10. 制限と未確認

- 通常の new_game からの対戦で 6 枚が選ばれ、受理・停止する場面は確かめていない（構築盤面と保存済みの応答だけ）
- 受理の前の先読み（D）で拒否される場面の判定は、合成の診断で確かめただけ
- `ClientHub.from_state` の入口の不変条件（PT5E-FROM-STATE-INVARIANT）は別の課題のまま
- 保存済みの V0〜V3 の証跡の再現（`run_v1.reproduce` など）は `meaning/v1` で比べるが、0.176.0 では実装の識別が違うので、旧い証跡を新しい版で再実行しない（既存の設計）
