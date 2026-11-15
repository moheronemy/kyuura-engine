# うらのバトル場のワザの候補の保証の文（S1 監査の F-1 の修正。v0.180.0）

2026-11-13。[vai-batch-s1 の拒否の監査](verification-ai-batch-s1-rejection-audit.md) 3.3 節の F-1 を直しました。U7-5 の設計の F-1（錯乱ジム。[chaos-gym-borrow-t-f1.md](chaos-gym-borrow-t-f1.md)）とは別のものです。

- 直したのは、候補の保証の文（`guarantees`）と実装の対応だけです。ゲームの処理・拒否の判定・裁定は変えていません。
- 候補・選べるものの有無・順序・参照・入力の形、処理可能性と理由、inputs・check・submit の判定、エンジンの状態遷移・乱数の消費は変わりません。
- 方策・入力生成・judge の規則（6 のまま）・カードデータ・固定デッキ・規約集合・GUI・renderer も変えていません。
- 旧監査の「不具合らしいものは見つからなかった」は、ゲームの処理と拒否の判定に不整合が見つからなかった、という範囲の結論です。保証の文の不一致（F-1）は、その監査で別に記録し、修正していませんでした。

## 1. 基点と範囲

| 項目 | 値 |
|---|---|
| 基点 | `claude/vai-batch-s1-reject-audit` の `10a54f8045461afb5b38b28f9c1876cd4d4a40fe`（S1 監査の文書。origin と一致。`origin/main` `7b3d53c` の祖先ではなく、main への取り込みは仮定しない）。`kyuura_engine`・`pyproject.toml` は 0.179.0 の配布のコミット `4b6e3fe` と同じ |
| 作業ブランチ | `claude/f1-face-down-attack-guarantee`（専用の worktree）。利用者の作業ツリーは触っていない |
| コミット | 実装とテスト `238255004abdc053bb25a7f3031350d3d2c6c6e6`、版 0.180.0 `27ba35d7d325aabe4a8804c57e095e00fc3b81c6`（配布の確かめの固定コミット）、この文書 |
| 事前計画 | 証跡の `PLAN.md`（変更・テストの前に保存） |
| 対象外 | LOST_TARGET の根拠の登録・judge の規則 7、ほかの保証の文の整理、GUI の追従、資源の最適化、新しい対戦バッチ |

## 2. 問題と実装の事実

0.179.0 では、`_attack_candidate` が `GUARANTEE_ATTACK` を、バトル場がうらのときの分岐 `_face_down_attack_candidate` にもそのまま渡していました。

`GUARANTEE_ATTACK` の preconditions は「エンジンが宣言を受け付ける前の確かめ（`resolution.flow.check_use_attack`）を候補の作成と入力の検査に使う」です。うらの分岐の実際の処理は次のとおりで、この文は成り立ちません。

| 段 | うらの分岐が実際にすること |
|---|---|
| 候補の作成 | 選べるワザは、本人が知る本当のカード（観測の `real`。本人の応答にだけ出す）の印刷のワザの並び。`check_use_attack`・宣言の前の先読みは呼ばない。選べるものは `unverified`・`face_down_reveal_not_evaluated`。宣言といっしょに選ぶものは示さない（段 2 は 0 個）。印刷のワザがなければ、入力のない `not_implemented` の候補（`no_printed_attack`） |
| 入力の検査（check） | `_attack_input_problem` が形（番号・段の並び・重なり・組）だけを確かめる。`verify=_not_checked` は常に通す（エンジンの確かめを呼ばない） |
| 送信（submit） | `apply_command` が入口から判定する。項目・段階の確かめのあと `_reveal_for_action`（番・決定待ちでないことを確かめておもてにする）、そのあと本当のカードに応じて処理し、受け付けなければコマンドごと拒否する（複製を捨て、元の状態のまま） |

## 3. 修正

`legal_actions.py` に `GUARANTEE_FACE_DOWN_ATTACK` を新しく作り、`_attack_candidate` でバトル場がうらのとき（`state.is_face_down(active)`。うらであることは公開）だけ、これを渡すようにしました。差分は 15 行の追加と 2 行の削除です。

- `GUARANTEE_ATTACK`（おもてのワザ、使えないワザの候補の `_UNUSABLE_GUARANTEES`）は変えていません。
- 本当のカードの違いでは分けません。うらの分岐の 2 つの戻り値（ワザがある・ない）は同じ値を使います。
- 項目の名前は既存の 4 つ（`preconditions`・`acceptance`・`after_acceptance`・`supported_scope`）のままです。語彙（処理可能性・理由）は増えていません。

新しい文の要点は次のとおりです。

| 項目 | 内容 |
|---|---|
| preconditions | 番のプレイヤーの main で、本人のバトル場がうらであること。ワザは本人が知る本当のカードの印刷のワザ。`check_use_attack`（必要なエネルギー・特殊状態・ワザを使えない効果などを含む）と先読みは、候補の作成でも入力の検査でも呼ばない。check は形（ワザの番号が 1 つで、ほかを選ばない）だけ |
| acceptance | 保証しない。check が valid でも、エンジンの確かめを通したことを意味しない。送信のあとの判定は、エンジンがコマンドの入口から行い（`_reveal_for_action` を含む）、受け付けなければコマンドごと拒否する |
| after_acceptance | 評価していない。受理のあとに何が起こるか（ワザを使ったか、その続きの決定・停止を含む）を予告しない |
| supported_scope | `unverified`（エンジンの確かめを呼んでいない）。受理・必要なエネルギー・ワザの実行の完了の保証ではなく、公開の許可でもない |

おもてにしたあとの結果（残るか・トラッシュか・ワザの効果）は、文では予告しません。テストで「トラッシュ」「たねポケモン」の語がないことを確かめています。

`check_use_attack` を新たに呼ぶ、秘密を読む試行を加える、候補を減らす、エネルギーを計算する、といった動作の変更はしていません。

## 4. 対象以外の応答・動作が変わらないことの確かめ

修正の前（`10a54f8` を展開したソース）と後（作業ツリー）で、同じ証跡のスクリプト `contract_dump.py` を別のプロセスで実行し、応答を書きかえずに保存して、項目ごとに比べました（`contract_compare.py` → `contract_diff.json`）。

盤面は P6 のテストの `face_down_active` です（構築盤面。new_game からの到達ではありません）。本当のカードだけが違う 4 つ（たねのコラッタ・たねのイワーク・1 進化のユンゲラー・炎エネルギー）と、おもてのエビワラーの対照を使いました。

| 確かめたこと | 結果 |
|---|---|
| 差のある場所 | 32 か所。すべて、うらの 4 例の use_attack の候補の `guarantees` の 4 項目（U7 の候補と client_api の候補の両方） |
| おもての対照 | 差なし |
| inputs・check（形の合う入力・合わない入力 8 通り） | 差なし |
| 送信の結果 | 前後で同じ。コラッタ・イワークのいわおとし・ユンゲラーの 2 つのワザは受理、イワークのかたくなるは拒否（`INSUFFICIENT_ENERGY`・`invalid_input`、状態は変わらない）。どれも U7 と直接のコマンドで結果・本人への結果・状態が同じ |
| 問い合わせによる状態の変化 | 前後とも、候補・inputs・check で状態・乱数・ログが変わらない |
| 相手の候補・相手と観戦者の観測・公開ログ | 前後で同じ（要約の値） |
| `GUARANTEE_ATTACK` | 前後で同じ値 |

保証の文だけを差しかえた応答を、テストの期待値に使ってはいません。テストの期待値は定数で書きました。

## 5. テスト

新しいモジュール `tests/test_legal_actions_f1_v0_180.py`（8 件）で確かめました。

- うらの候補に新しい保証が付く。4 つの本当のカードで同じ値で、client_api の候補も同じ
- おもてのワザの候補の保証は 0.179.0 の値のまま（sha256 で固定）
- 保証の文以外の値（区分・理由・入力の公開・段・選べるもの・check）は 0.179.0 の値
- 受理・拒否は 0.179.0 と同じ（U7 と直接のコマンドで結果・状態が同じ。拒否は状態を変えず、相手・観戦者へ知らせない）
- 元の文（`GUARANTEE_ATTACK`）は、文の確かめに通らない

元の文に戻すと失敗することは、別のプロセスの中だけで `GUARANTEE_FACE_DOWN_ATTACK` を元の値にしてモジュールを実行し、確かめました（`revert_check.json`。8 件のうち 2 件が失敗し、エラーは 0）。ソースのファイルは書きかえていません。

モジュールは 1 つずつ別のプロセスで実行し、出力・終了コード・JUnit を証跡に保存しました。

| 実行 | モジュール | 結果 |
|---|---|---|
| run1-new | 新しいモジュール | 失敗 2（テストの側の誤り。ワザのない場合の inputs は `stages: []` を返すこと、文の部分一致の書き方）。直した |
| run2-new | 新しいモジュール | 8 件成功 |
| run3-related | `test_legal_actions_u7_4`・`p6_face_down_retreat_v0_174`・`u7_1`・`u_r3a_v0_175`・`u7_5g_face_down_power`・`pt5t_c1_v0_179`・`test_secret_plan_v0_67`・`test_verification_ai_v2_repeat`・`v0179_follow`・`test_verification_ai_p6` | 10 モジュール・177 件が成功 |
| run4-version（版のあと） | `test_preset_decks_v0_20`・`test_distribution`・新しいモジュール・`test_verification_ai_v2_repeat` | 成功 |

全体のテスト、GUI、E2E、新しいバッチ、seed の探索はしていません。

## 6. 検証用 AI の指紋

- `test_verification_ai_v2_repeat` は、修正のあと・版のあとのどちらでも成功しました。4 つの固定の対戦の行動の指紋（`ACTION_GOLDEN`）と契約の値の指紋（`CONTRACT_GOLDEN_0179`）は変わっていません。固定値は更新していません。
- 契約の値の列は `guarantees` を含みます。そのため、固定の対戦にうらのバトル場のワザの候補が出ていれば、値は変わるはずです。変わらなかったので、4 つの対戦にはこの候補が出ていないと読めます（行を数えて確かめたわけではありません）。
- 新しい保証の文は fixture（4 節・5 節）で確かめました。固定の対戦の指紋が変わらなかったことと、fixture で確かめたことは、別のことです。
- AI のコードは変えていません。`guarantees` は反復の鍵（`policies.EVAL_FIELDS`）から除かれ、方策・入力生成は読みません。judge の `PRECHECK_KINDS` に use_attack はなく、判定の入力にもなりません。

## 7. 版・識別・配布

| 項目 | 変更の前（`10a54f8` = `4b6e3fe` のパッケージ） | 変更の後（`27ba35d`） |
|---|---|---|
| パッケージの版 | 0.179.0 | 0.180.0 |
| `behavior_digest` | `67c4c15bafcf00b81f7abe7ef2396742181d27744b2af7efd1657f4c90767fca` | `08038e06f7fd0f6d8f4ba26727f92e1d83245b8940b984987a66fe9452ff6c77` |
| `instrumentation_digest` | `d34367481dd69bd72c715e1977feb93b3c19596a01f3b53a104eca2e7e06146d` | 同じ |
| 識別の方式 | `kyuura-package-files-sha256/1`（58・4 ファイル） | 同じ |
| 道具の識別（`tools.verification_ai.batch` 版 8 の `tool_digest`） | `dbca28bd06ba4602a1f3c334f8b0154067149cf35a460777cb7e4e6865afceba`（26 ファイル） | 同じ |
| 判定の規則の版 | 6 | 6 |

配布は既存の手順（0.179.0 と同じ）で確かめました。

- 配布対象: `git ls-tree` の `kyuura_engine` は 62 = 62 ファイル。`pyproject.toml` の差は版の 1 行だけで、依存は増えていない
- `git archive 27ba35d` → `pip wheel --no-deps` → `scripts/check_distribution.py --wheel`: required=62・problems=0（wheel の sha256 `3239528efecd77bbe95a33ccf05fae7ffe4fb47fb0536d0a7f211df01dc29717`）
- リポジトリの外の新しい venv に、`git+https://github.com/moheronemy/kyuura-engine.git@27ba35d7d325aabe4a8804c57e095e00fc3b81c6` から通常のインストール。`direct_url` のコミットは `27ba35d…`（editable でない）、読み込みは site-packages、依存（requires）はなし、パッケージのファイルは 62
- 導入物の実装の識別は、ソースの識別と一致
- スモーク: この版のソースで作ったスナップショット 4 つ（うらのイワーク・ユンゲラー・炎エネルギー、おもての対照）を、導入物で復元して確かめた（送信はしない）。うらの 3 つは新しい保証の値（ワザのある 2 つは check が valid）、おもては 0.179.0 の `GUARANTEE_ATTACK` の値で、相手・観戦者への更新はない

既存の記録・スナップショット・バッチの計画は、元の実装（0.179.0 以前）と結び付けたまま残しています。新しい識別に書きかえたり、旧い計画を移して再開したりはしていません。0.179.0 の記録・スナップショットは 0.180.0 では再実行・復元できません（既存の設計）。旧版のスナップショットの復元や旧記録の再実行も、スモークではしていません。

## 8. GUI・AI への追従

- GUI の追従はしていません。必要になりそうなのは、固定するエンジンのコミット（`27ba35d`）、契約の engine の値、版のテスト、固定例の compatibility（うらのバトル場のワザの候補の保証の文）の更新です（GUI では確かめていない見込み）。
- 検証用 AI は、指紋の固定値を含めて更新が要りませんでした（6 節）。バッチの計画は実装の識別の違いで再開しないので、0.180.0 で実行するときは新しい計画を作ります。

## 9. 未確認・残件

- new_game からの対戦で、うらのバトル場のワザの候補の新しい文を見た記録はありません（構築盤面と導入スモークだけ）。
- LOST_TARGET の根拠の登録・judge の規則 7（[S1 監査](verification-ai-batch-s1-rejection-audit.md) 4 章と、証跡の `judge_proposal_lost_target.md`）は別の単位です。
- うらのバトル場のワザの拒否のための judge の専用の規則（今は一般の規則で正常な拒否と判定）も、別の単位です。
- ほかの保証の文の整理はしていません。

## 10. 証跡

- 保存先: `kyuura-engine-verification-vai/verifier/runs/f1-face-down-attack-guarantee/`
  - 事前計画（`PLAN.md`）
  - 識別（`identity.py`・`identity_before.json`・`identity_after.json`・`source_identity.json`）
  - 修正の前後の契約の差（`contract_dump.py`・`contract_compare.py`・`contract_before.json`・`contract_after.json`・`contract_diff.json`）
  - 元の文に戻す確かめ（`revert_check.py`・`revert_check.json`）
  - テストの出力・JUnit（`run_tests.py`・`junit_unittest.py`・`tests/run1-new`〜`run4-version`）
  - 配布（`package_files_*.txt`・`pyproject_diff.txt`・`pip_wheel_output.txt`・`check_distribution_output.txt`・`install_pip_output.txt`・`venv_pip_list.txt`・`make_smoke_snapshots.py`・スナップショット・`install_smoke_script.py`・`install_smoke_output.json`）
  - コマンドと終了コード・失敗と再実行（`commands.txt`）
- 公開用: `public/runs/f1-face-down-attack-guarantee/summary.json`（確認済みの件数と状態だけ）
