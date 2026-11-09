# 検証用 AI の U-R3a への追従（本人のうらのカードの 2〜3 段の特殊能力の入力）

[U-R3a](legal-actions-u-r3a-v0.175.md)（v0.175.0）で、本人のうらのカードの宣言の段が 2〜3 段の特殊能力が、構造の組の入力を返すようになりました。検証用 AI（`tools/verification_ai`）を
これに追従させました。AI の側だけの変更です。エンジン・GUI・renderer・kyuura・カードデータ・固定デッキ・規約集合・裁定・識別方式は変えていません。パッケージの版は 0.175.0 のままです。

## 0. 基点と範囲

| 項目 | 値 |
|---|---|
| 基点 | `43debddc69d8feb75f8fb6f617a517495f369951`（`claude/u-r3a-face-down-multistage-power`。U-R3a の実装 `81e9e99` と既存の AI（P6 の追従をふくむ）を含む。`origin/main` には入っていない） |
| 作業ブランチ | `claude/vai-u-r3a-follow`（専用の worktree `C:\dev\kyuura-engine-vai`。利用者の `C:\dev\kyuura-engine` は触っていない） |
| AI のコードとテストのコミット | `fc1aa511ef862405e2db242e7d07887655586259`（固定確認はこのコミットで実行） |
| 対象外 | GUI の追従、完成する入力がない R-3 の残件、R-B・新しい記録形式 |

## 1. 既存の対応範囲（読んだ結果）と変更の整理

| 確かめたこと | 既存の AI | 変更 |
|---|---|---|
| `options_by_choice`・`depends_on_stage`・`upstream_stages`・`after` | `actions._allowed_ids` が直前の段の選び方で `options_by_choice` を引き、`upstream_stages` があれば `after` が合う番号だけにする。段の項目は `STAGE_KEYS` にある | なし（再実装しない） |
| 上流ごとに分かれる後段の番号 | 上の扱いで、別の経路の番号を作らない | なし |
| uniform-stage・uniform-tuple | どちらも同じ `_allowed_ids` で作る（`build_choices`・`enumerate_inputs`） | なし |
| 候補の `pokemon`・`power` | 行動生成は段だけを読み、候補の `pokemon`・`power` を入力の作成に使わない | なし |
| `confirmed`・`unverified` | deep は `supported`・`may_stop_later` だけ（`unverified` は代わりがないときだけ）。boundary は `FALLBACK_PROCESSABILITY`（`unverified` をふくむ） | なし（deep を広げない） |
| 完成する入力がない候補 | `inputs` が `withheld` なら作らず送らない（ランナーの既存の扱い） | なし |
| 判定（形式ではなく実行結果） | うらのカードの特殊能力の拒否は、理由 `face_down_reveal_not_evaluated` で受け付ける前の確かめの保証の外になり、停止系でなければコードによらず `normal_rejection`。受理の中身（使った・トラッシュ）を分けない | 判定の規則 5（3 章）。ランナーに異常の記録と受理の中身の判定を加えた |

形式を扱えること（1〜6 行）と、実行の結果を正しく判定できること（7 行）は別です。前者は既存のままで足り、後者だけを変えました。
カード名・カード id・効果の型による分岐は、共通の行動生成・方策に加えていません。カード固有の準備と代表の選び方は `fixtures_u_r3a.py` にだけあります。

## 2. 入力生成と方策（変えていない）

- 本人向けの API が返した段・選べるもの・参照だけから入力を作る。本当のカードの条件を評価しない。`check_usable` などを呼ばず、おもてにする試行・状態の複製をしない。相手の秘密・内部の乱数を読まない
- 方策に渡すのは本人の観測・候補・段だけ（テストで確かめた。観測を渡しても渡さなくても同じ組）
- 表示だけの候補・入力非公開の候補は送らない。送信は check が valid のあとだけ（`runner.submit_checked`）
- deep の範囲は広げていない。boundary は既存どおり `unverified` を対象にする

## 3. 判定の規則 5（`JUDGE_RULES_VERSION` 4 → 5）

規則 5 を当てるのは、候補が本人のうらのカードの特殊能力（`kind` が `use_power`、`power`・`pokemon` の両方に `face_down: true`、理由に `face_down_reveal_not_evaluated`）の送信だけです（`judge.is_face_down_power`。API の契約の値だけで決める）。
P6（規則 4）・おもての特殊能力・ほかの送信の判定は変えていません。

### 3.1 拒否（check が valid のあと）

根拠は、この候補の保証（`GUARANTEE_FACE_DOWN_POWER`: 構造の組は、受け付けるかで絞らない。check は形だけ）と、選んだ入力です。コードが診断のコード表にあるだけでは正常にしません。

| 元のコード | 条件 | 判定 |
|---|---|---|
| `WRONG_ENERGY_TYPE`・`NOT_BASIC_ENERGY` | 選んだ入力に `energy` の段がある | `normal_rejection`（おもてにしたあとエンジンが決める。構造の組はタイプ・種類で絞らない） |
| `SAME_POKEMON` | `source` か `target` の段がある | `normal_rejection` |
| `WRONG_POKEMON_TYPE`・`WOULD_KNOCK_OUT` | `target` の段がある | `normal_rejection` |
| `NO_DAMAGE_COUNTERS` | `source` の段がある | `normal_rejection` |
| `POWER_ALREADY_USED` | 段を問わない | `normal_rejection` |
| 上の 7 つで、条件の段を選んでいない | — | `undetermined`（説明できない） |
| `POWER_CHOICE_MISSING`・`POWER_CHOICE_NOT_USED`・`NOT_YOUR_TURN`・`DECISION_PENDING` | — | `suspect`（宣言の項目・候補を出す条件の保証と矛盾） |
| `ENERGY_NOT_ATTACHED` | `energy` の段が前の段の `source` に依存し、それを選んだ | `suspect`（ついているカードの並びから選んだ） |
| ほかの `invalid_input` などのコード（`CARD_NOT_IN_HAND` をふくむ） | — | `undetermined` |
| 停止系の分類 | — | 規則 3 のまま（代表の条件の根拠がなければ `known_stop` にしない） |
| 分類がコード表と違う・対応漏れ・failed・ホストの断り | — | `suspect`（既存のまま） |

- おもての特殊能力では、候補の作成が組ごとにエンジンの確かめを呼ぶので、同じ `WRONG_ENERGY_TYPE` でも期待が違います。規則 5 はうらのカードの経路だけに当て、おもての経路の判定は規則 4 のままにしました（おもての経路の拒否を分けることは今回の範囲の外）
- 0・1 段のうらのカードの特殊能力も規則 5 の対象です。規則 4 では、停止系でない拒否はコードによらず `normal_rejection` でした。規則 5 では、上の表で説明できない拒否は `undetermined` になります（意図した差。過去の判定の記録は上書きしていない）

### 3.2 受理の中身

`judge_face_down_power_accepted`: 受理のあとに加わった公開のログ（観戦者に見える出来事。ランナーと固定確認は `observation.visible_log(state, None)`）で分けます。

| 出来事 | 判定 |
|---|---|
| 最初が、候補のポケモンの `secret_plan_revealed`（カード id が公開されている）で、そのあと同じポケモンの `pokemon_power` があり `secret_plan_discarded` がない | `expected`（おもてにして使った） |
| 同じく最初がおもてにする出来事で、同じポケモンの `secret_plan_discarded` があり `pokemon_power` がない | `expected`（たねでないのでトラッシュ） |
| おもてにする出来事が最初にない・別のポケモン・カード id が見えない・どちらもない・両方ある | `undetermined` |

うらの数が減ったことだけでは分けません。

### 3.3 ランナー

- うらのカードの特殊能力の check が、契約から作った入力で invalid なら、異常 `face_down_power_check_invalid_for_generated_input` を記録する（check は形だけなので契約と矛盾する。P6 と同じ考え方）
- 変異の実行（`negative` があるとき）では、受理の中身を 3.2 節で判定して記録する

## 4. 限定のテスト

`tests/test_verification_ai_u_r3a.py`（12 件）:

- 入力: 小さな JSON の 2 段・3 段で、uniform-tuple の組が参照（`options_by_choice` と `after`）の組の集合と同じ（別の経路の番号を混ぜない）。uniform-stage もその集合の中で、どの組も選ばれうる。元の応答を変えない。5 つの方策が同じ生成を使う。deep は作らない（`Unbuildable`）。組が完成しない構築盤面は入力非公開で、送れば断られる
- 情報境界: 方策に渡る文脈は観測・候補・段だけで、観測によらず同じ組
- 判定: 3 章の表（正常な拒否・条件の段がない・構造の保証・未知のコード・コード表にあるだけのコード・分類の不一致・停止系・failed・断り）、受理の中身、P6 とおもての特殊能力の判定が変わらないこと
- 固定確認の 3 ケース（5 章）を、テストの中でも流す

実行（1 モジュールずつ別のプロセス。`PYTHONIOENCODING` を外した。証跡の `tests/test_runs.txt`）:

| モジュール | 件数 | 結果 |
|---|---|---|
| `tests.test_verification_ai_u_r3a`（新） | 12 | 1 回目で失敗 0 |
| `test_verification_ai_p6`・`v3_3` | 16・9 | 失敗 0（判定の版の確認を 4 から 5 に直した。意図した差） |
| `test_verification_ai_v3_2`・`v3_1`・`v2_repeat`・`v2`・`v1`・`v0` | 11・15・15・19・19・24 | 失敗 0 |

- 方策の意味の指紋（`test_verification_ai_v2_repeat` の `GOLDEN`）は、期待の値を変えずに通りました。指紋は候補の中身・入力の意味・結果から作り、版・実装の識別を含みません。固定デッキの対戦の経路には、うらのカードの特殊能力が出ません
- 失敗・再実行はありませんでした
- 全体のテスト・GUI・E2E・対戦の探索・大きな対戦・lockstep・状態の監査は流していません

## 5. 固定確認（構築盤面の 3 ケース）

`python -m tools.verification_ai.run_u_r3a run --out C:/dev/kyuura-engine-verification-vai --engine-commit fc1aa51…`（終了コード 0。0.257 秒。要求はどれも 9）。

- 盤面: U-R3a の 3 つの代表と同じ（`fixtures_u_r3a.build` → `tests/test_legal_actions_u_r3a_v0_175.py` の `placed` → `tests/test_secret_plan_v0_67.py` の `board`・`place`）。出典から変えていない。0.175.0 で作り、開始のスナップショットから `snapshot.RestoredGame` で始めた
- 不変条件（fixture の記録）: `check_invariants` の問題なし、状態は使える、番はプレイヤー 0 の MAIN、決定なし、うらのカードに何もついていない・ダメージ 0、スナップショットの形の問題なし
- 構築盤面です。new_game から届いた証拠ではありません。完全な再現用記録は作らず、開始のスナップショットと操作の記録（trace）だけです
- 入力は、共通の行動生成（`enumerate_inputs`。uniform-tuple の列挙・boundary の範囲）が作った組から、ケースの選び手（`fixtures_u_r3a` の関数。方策ではない）が選びました。ランダムの方策が選んだものではありません。uniform-stage（`build_choices`）で作った組がその列挙に入ることも記録しました（送っていない）

| ケース | 本当のカード | 組の数 | 選んだ入力 | 結果 | 判定 |
|---|---|---|---|---|---|
| U1 | ロケット団のヒトカゲ（たね・2 段） | 4 | コラッタ → 炎エネルギー | 受理 | 通常 `expected`、受理の中身「おもてにして使った」、副作用は受理の変化 |
| U2 | ロケット団のヒトカゲ | 4 | エビワラー → 闘エネルギー | 拒否 `WRONG_ENERGY_TYPE`（`invalid_input`） | `normal_rejection`（3.1 節の条件: `energy` の段を選んだ）。副作用なし。同じ取っ手の check は valid |
| U3 | フシギバナ（2 進化・3 段） | 12 | エビワラー → 闘エネルギー → エビワラー | 受理 | 通常 `expected`、受理の中身「たねでないのでトラッシュ」 |

suspect 0・undetermined 0・期待と違うケース 0。

### 5.1 公開されたカード id と拒否の無副作用

| ケース | 相手・観戦者の観測とログ（保存した値） | 更新 | 取っ手 |
|---|---|---|---|
| U1 | 前は場のポケモン 4 がうら（カード id なし）。後は `card_id: PMCG4-012`、ログの `secret_plan_revealed` は相手・観戦者とも `PMCG4-012` | 相手・観戦者に各 1 件 | 古い取っ手の check は `CANDIDATES_STALE` |
| U2 | 前後で観測・ログが同じ（うらのまま。`PMCG4-012` は出ない） | 0 件 | 同じ取っ手で check に戻れる（valid） |
| U3 | 後は場のポケモン 4 がいない。トラッシュに `PMCG1-011`、ログの `secret_plan_revealed` は `PMCG1-011` | 各 1 件 | `CANDIDATES_STALE` |

U2 の拒否の前後で、状態の確認値（状態・乱数・ログの長さ・決定・停止・区間）・状態のオブジェクト・全員の更新の数・更新の番号・failed がどれも変わりませんでした（`judge.compare` が空）。check でも何も変わりませんでした。

## 6. 版・識別・過去の証跡

- パッケージの版は 0.175.0、`behavior_digest` は `d1bcca17071feb62d9006d3aa133a638756e05777fefe6bfdbfdc11a6e659149` のまま（`81e9e99` から `kyuura_engine/`・`pyproject.toml` の差なし。`current_identity` で確かめた）
- 判定の規則の版は 5。過去の判定の記録（規則 1〜4）は上書きしていない
- 過去の証跡は、それぞれ元の版の実装と対応付けたまま残している。今回の fixture・スナップショットは 0.175.0 で作り、旧版のスナップショットの版・識別は書き換えていない

## 7. 証跡

`C:/dev/kyuura-engine-verification-vai/` の `verifier/runs/u-r3a-ai-follow/`（実行前の計画 `plan.json`、ケースごとの `fixture.json`・`start_snapshot.json`・`trace.jsonl`・`case_result.json`、
`aggregate.json`、`invocation.json`（実行のコミット・判定の版・生成の方法・fixture の出典・コマンド・終了コード）、`run_u_r3a_stdout.txt`、`tests/` のテストの出力）と、
`public/runs/u-r3a-ai-follow/summary.json`（非機密の集計）。マニフェストは 428 ファイル。既存の 400 ファイルが変わっていないことを確かめてから更新した。

## 8. GUI の追従へ渡すこと

- うらのカードの特殊能力の 2〜3 段は、おもての特殊能力と同じ形（`options_by_choice`・`depends_on_stage`・`upstream_stages`・`after`）。前の段を変えたら後の段と check の答えを捨てる
- check は形だけ（段の数・番号・前の段との依存）。valid でも、使えること・受理は保証されない（エンジンがおもてにしてから決める）
- 結果は 3 通り: おもてにして使った受理（受理のあとに決定やコインがあることがある）、たねでないのでトラッシュした受理（特殊能力はおこらない）、おもてにしたあとの拒否（状態はもどり、本当のカードは相手・観戦者に公開されない。診断は本人だけ。取っ手は失効しない）
- 受理の中身は、公開のログの `secret_plan_revealed` のあとの `pokemon_power` か `secret_plan_discarded` かで分かる。うらの数の変化だけで分けない
- 本人の画面だけに出る候補。相手・観戦者の画面に、能力の名前・本当のカードを出さない
- 完成する入力がない候補（R-3 の残り）は入力非公開のまま。送らない
- GUI の固定するエンジンの更新・契約の表の説明の直しは、[U-R3a の文書](legal-actions-u-r3a-v0.175.md) 7.1 節のとおり（今回は GUI に着手していない）

## 9. 制限と未確認

- 構築盤面の 3 ケースだけ。new_game からの到達、ランダムの方策が実際の対戦でこの入力を選ぶこと、`SAME_POKEMON` など `WRONG_ENERGY_TYPE` 以外の正常な拒否の実際の拒否（偽の応答のテストだけ）は確かめていない
- おもての特殊能力の拒否を、候補の作成の確かめの保証で分けることは範囲の外（規則 4 のまま）
- 受理のあとの決定・コインがある型（今回の 3 ケースにはない）の、受理のあとの続きは判定していない
