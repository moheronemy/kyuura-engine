# 検証用 AI の V3-3（構築盤面の代表例）と V3-2 の計測・判定の補完

[V3 の仕様と計画](verification-ai-v3-design.md) の V3-3 を、構築盤面の代表例 4 つに限って実装しました。目的は、通常の対戦では未到達だった `unverified`・表示だけの FU2・
エンジンの拒否・受理のあとの停止を、条件の分かる盤面で確かめることです。先に V3-2 の計測と判定を小さく補いました。V3-4 の探索・広いデッキと規約集合・R-B・方策の追加の調整は
対象外です。V3-2 は [verification-ai-v3-2.md](verification-ai-v3-2.md)（11 章に訂正を追記）。

1 章〜7 章は実行の前に書き、コードと同じコミットに入れました。8 章以降は実行のあとに書きます。

## 1. 基点と範囲

| 項目 | 値 |
|---|---|
| 基点 | `claude/verification-ai-v3-2` の `638657c`（V3-2。実行 `0cc21df`・集計の訂正 `c2155a4`。`kyuura_engine` は `e26df79`（0.172.0）と同じ） |
| ブランチ | `claude/verification-ai-v3-3`（worktree `C:\dev\kyuura-engine-vai`） |
| 変えていないもの | エンジン本体・GUI・renderer・カードデータ・固定デッキ・規約集合・識別の方式・CN-1 の対応・既存の方策（意味の列の sha256 のテスト） |

## 2. V3-2 の補完 A: 変異の結果の分類

| 分類 | 意味 | 例 |
|---|---|---|
| `run` | 作って送った | — |
| `not_applicable` | 前提を満たさない（その入力・状態では作れない） | 入力がない（`no_input`）、最後の段が上限・下限でない、別の経路だけの選ぶものがない |
| `unsupported_contract`（新規） | 生成器がその段の契約に対応していない（前提がないとは言えない） | 値の段（`value_stage`）、初期配置などの段の対応（`stage_layout_not_mapped`）、経路で引く段の参照を読まない（`path_stage_references_not_read`。`count_over`・`non_executable`） |
| `not_run` | 予算・位置の選び方・1 つの状態の種類の上限（`per_position_limit`。V3-3 で記録を加えた）・元の入力が受理されないで試さなかった | — |

`options_by_path` の個数の超過を作る新しい機能は加えていません（分類と記録だけ）。V3-1 の `NegativeSession` は、1 つの状態の上限で試さなかった種類を `not_run` の行として
記録します（要求は送らない。通常の進行は変わらない）。

## 3. V3-2 の補完 B: known_stop（判定の規則 3）

`judge.JUDGE_RULES_VERSION = 3`。規則 2 の「コード表にある元のコード・分類が同じ・経路の理由がエンジンの側の確かめを評価していないことを示す」に加えて、**その停止の代表の条件の
根拠**が要ります。

- 根拠は `judge.KNOWN_STOP_EVIDENCE`（元のコード → 条件の説明・出典）の登録と、場面（V3-3 のケース）の側の宣言（`evidence`）の両方。最初は代表例 DU1
  （`UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT`。ドライアップのコインの「おもて」の数が、選んだ相手のポケモンの「水」エネルギーより多い）だけを登録した
- 根拠がない停止系の拒否・受理のあとの停止は `undetermined`（`stop_condition_not_evidenced`・`halt_condition_not_evidenced`）。通常の対戦（V0〜V3-2）の停止は、場面の宣言がないので
  規則 3 では `undetermined` になる（過去の判定の記録は書きかえない。V3-1 は規則 1、V3-2 は規則 2）
- 受理のあとの停止は、受理の前の拒否と別に判定する（`judge_halt_after_accept`。公開の停止の診断の分類・コード表・根拠）
- 副作用は、受理と拒否で分けて判定する（`judge_effects`）: 拒否・断りはどれも変わらないことが期待。受理は状態の置きかえと更新の番号の前進があって当然で（受理のあとの停止・公開の更新を
  無副作用の失敗と判定しない）、それがなければ `undetermined`

## 4. V3-3 の代表例と構築盤面

### 4.1 構築盤面の扱い

- fixture は検証者の側の固定の盤面（`tools/verification_ai/fixtures_v3_3.py`）。カード固有の準備はこのモジュールに閉じ込め、共通の行動生成・方策・判定にカード名・ID・効果の型の
  分かれを加えない
- 盤面は既存のテストの関数（`tests/` のモジュール）で作る。作るときにだけ内部の状態を使い（`build_test_state`・`apply_command`・乱数の仕込み）、作ったあとの操作は公開の API の
  candidates・inputs・check・submit だけで行う。選び手は本人の入口の JSON だけを読む
- 出典（ファイル・関数・ファイルの sha256）・出典からの変更・整合の確かめ（`engine.check_invariants`・`diagnostics.state_usable`・段階・番・スナップショットの構造）を
  `fixture.json` に記録する。意図的に不整合にした盤面は使わない（おもての山札を直接置く `tests/test_legal_actions_u7_5f.py` の `built()` は使わない）
- 通常の new_game から届いた証拠とは扱わない。V3-2 の固定の対戦の到達範囲と足さない

| fixture | 出典 | 変更 |
|---|---|---|
| F1 | `tests/test_legal_actions_u7_5g_face_down_power.py` の `placed(MANKEY)`、`tests/test_secret_plan_v0_67.py` の `board`・`place`（`apply_command` でマチスの秘策を使い、マンキー（`PMCG2-028`）をうらにしてベンチに出す） | なし |
| F2 | 同じく `placed(UNOWN_B)`（アンノーンB `neo3-032`） | なし |
| F3 | `tests/test_legal_actions_u7_4.py` の `test_rejected_vs_stop_after_acceptance`、`tests/test_deferred_shortage_user_promos_v0_127.py` の `dry_board(2)`・`run(3)`、`tests/helpers.py` の `with_coin_bits` | 出典と同じく、次のコインを「おもて 3・うら 1」にした乱数（テストの乱数の仕込み） |
| F4 | `tests/test_legal_actions_u7_5f.py` の `flashed()`（`build_test_state` の盤面から `apply_command` でフラッシュを使い、答えて番を終える） | なし |

### 4.2 ケースと期待（実行の前に決めた）

| ケース | 種類 | fixture | 操作 | 期待 | 根拠 |
|---|---|---|---|---|---|
| C1 | boundary | F1 | 本人のうらのマンキーの特殊能力（入力なし）を check してから送る | 候補は `unverified`、check は valid、受理。受理のあと、相手・観戦者の観測でそのポケモンはうらでなくなる（ルールに従う公開） | `test_basic_card_reveals_then_uses_the_power_with_a_later_decision` |
| C2 | boundary | F2 | 本人のうらのアンノーンBの特殊能力（1 段。自分のバトル場のポケモン）を check してから送る | 候補は `unverified`、check は valid、エンジンが拒否。状態・乱数・ログ・決定・停止・取っ手・相手と観戦者への新しい更新が変わらず、相手・観戦者の観測でうらのまま（本当のカードは公開されない）。同じ取っ手・同じ入力の check は valid のまま | `test_rejected_after_reveal_leaves_the_state_unchanged` |
| C3 | boundary | F3 | ファイヤーのワザ（`may_stop_later`）を check してから送り、受理のあとの決定（相手のバトル場のラッキーを選ぶ）に答える | 宣言は受理・決定待ち、答えは受理・停止（DU1）。停止は判定の規則 3 で `known_stop`（場面が DU1 の根拠を宣言） | `test_rejected_vs_stop_after_acceptance`、`judge.KNOWN_STOP_EVIDENCE` |
| C4 | negative | F4 | 表示だけの候補 `check_face_up_deck`（FU2）へ、形の合う入力（最初の位置）を意図的に送る | check・submit とも `CANDIDATE_NOT_EXECUTABLE`（`refetch_required` 偽）、エンジンに渡らない、副作用なし。同じ取っ手の `end_turn` の check は valid | `GUARANTEE_FACE_UP` の acceptance・`_input_problem`、`tests/test_legal_actions_u7_5f.py` |

- 拒否・断りのケース（C2・C4）は、要求の前後の確認値（状態の sha256・乱数の指紋・ログの長さ・決定・停止）・状態のオブジェクト・閲覧者ごとの新しい更新・更新の番号を比べ、元の
  正常な要求へ戻れることを、状態を変えない check で確かめる（コマンドを 2 回送らない）
- 受理のケース（C1・C3）は、状態の変化と公開の更新を正当なものとして扱う（`judge_effects`）
- 本人のうらのカード（C1・C2）は、拒否のとき本当のカードが他者へ公開されないこと（C2）と、受理のあとはルールに従っておもてになること（C1）を分けて確かめる

## 5. 記録と再現の範囲

- 構築盤面から始めるので、完全な再現用記録（`ReplayCollector`。new_game からだけ作る）・`replay_run`（U4）・`snapshot_replay.replay_from_snapshot`（new_game からの記録の位置へ
  スナップショットをつなぐ）は対象の外。開始点を偽らない（途中から始める収集器を作らない）
- 残すもの: 開始のスナップショット（`start_snapshot.json`。`snapshot.save_snapshot`）、ケースの要求・応答・前後の比べ・判定（`trace.jsonl`・`case_result.json`）
- 復元の確かめ（事前に選んだ C3 だけ、1 回）: 同じ開始のスナップショットをもう一度復元し、新しい `ClientHub`（新しい取っ手）で同じ選び方の操作を送り、段ごとの結果（種類・入力の
  意味・結果・状態の区分）と最後の確認値を比べる。前の取っ手を使わない。U4 の new_game からの `replay_run`・R-B とは別の確かめ
- 各ケースの対戦は、スナップショットから復元した `snapshot.RestoredGame`（`failure` を持つので `ClientHub` で包める。完全な再現用記録は持たない）

## 6. 計画（実行の前に決めた）

| 項目 | 値 |
|---|---|
| ケース | C1〜C4（4.2 節）。結果を見てケースを足さない |
| 上限 | 1 ケースの要求 20・30 秒、全体 600 秒。復元の確かめは C3 の 1 回だけ |
| 入口 | `python -m tools.verification_ai.run_v3_3 run --out C:/dev/kyuura-engine-verification-vai --engine-commit <sha>`。終了コードは、どのケースも実行できて期待どおりで `suspect` がなければ 0、期待と違う・`suspect` があれば 3、実行できないケースがあれば 1 |
| fixture の誤り | エンジンの不具合と分けて、直したことと再実行を記録する（実行の前に見つけた誤り: F1 のマンキーのカード ID を `PMCG2-061` と書いていた。出典の定数 `JUNGLE_MANKEY` は `PMCG2-028`。整合の確かめで見つけて直した。fixture の記録は出典の定数との一致を確かめる） |

## 7. テスト

`tests/test_verification_ai_v3_3.py`（9 テスト）: not_applicable と生成器の未対応の区別・1 つの状態の上限で試さなかった種類の記録（`ClassificationTest`）、根拠のない停止は
`known_stop` にならない・受理のあとの停止・refused と rejected と受理の区別・受理と拒否で違う副作用の判定（`JudgeV3Test`）、fixture の整合・記録の元（`constructed_fixture`・
`new_game` 偽）・出典の sha256・スナップショットの保存と復元・復元した対戦は完全な記録を持たない（`FixtureTest`）、4 ケースの期待（メモリの中のケース。証跡のケースとは別）と、
同じスナップショットからの 2 回の復元で同じ結果（`CaseTest`）。

意図した差として、`tests/test_verification_ai_v3_1.py` の 4 行（値の段・初期配置の段の分類、根拠のない停止の判定、`halted_known` の終わり方）と `tests/test_verification_ai_v3_2.py`
の 3 行（根拠のない停止の判定・規則の版）の期待を直しました。

実行（1 モジュールずつ、別のプロセス）: `tests.test_verification_ai_v3_3`（9）・`v3_2`（11）・`v3_1`（15）・`v2_repeat`（15。既存の方策の意味の列の sha256）・`v2`（19）・`v1`（19）・
`v0`（24）: どれも失敗 0。

## 8. 実行の結果（2026-11-08）

実行: コミット `9125476`（`91254763724442ed81cd931c3fe362cc19537abd`。1〜7 章と同じコミット）。14:53:11Z〜14:53:13Z（UTC）。全体 2.1 秒。終了コード 0。計画（`plan.json`）は
ケースの前に書いた。

| ケース | 種類 | 要求 | 結果 | 判定 |
|---|---|---|---|---|
| C1 | boundary | 8 | 候補 `unverified`（理由 `face_down_reveal_not_evaluated`）・check valid・受理（決定待ち） | 通常の送信 `expected`、副作用（受理）`expected`（状態の置きかえ・確認値・更新の番号・全員への新しい更新は正当）。相手・観戦者の観測のうらのポケモンが 1 → 0（受理のあとにおもてになった） |
| C2 | boundary | 10 | 候補 `unverified`・check valid・エンジンの拒否（`NO_DAMAGE_COUNTERS`。`invalid_input`） | 通常の送信 `normal_rejection`（受理を保証しない種類）、副作用（拒否）`expected`（どれも変わらない）、相手・観戦者の観測でうらのまま・カード id は見えない（前後とも）、同じ取っ手・同じ入力の check は valid（復帰 `expected`） |
| C3 | boundary | 10 | ワザ（`may_stop_later`）の宣言は受理・決定待ち、答えは受理・停止 | どちらの送信も `expected`、副作用（受理）`expected`、停止は `known_stop`（`unresolved_ruling`・`UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT`・DU1 の根拠） |
| C4 | negative | 6 | check・submit とも `CANDIDATE_NOT_EXECUTABLE`。エンジンに渡らない | `expected`、副作用なし、同じ取っ手の `end_turn` の check は valid（復帰 `expected`） |

- `suspect` 0・`undetermined` 0・期待と違う 0
- 復元の確かめ（C3。同じ開始のスナップショットからもう一度復元し、新しい取っ手で同じ選び方の操作を送った）: 段ごとの種類・入力の意味・結果・状態の区分が同じ、最後の確認値
  （状態の sha256・乱数の指紋・ログの長さ・決定・停止）が同じ
- これらは構築盤面（4 つの fixture）での結果で、通常の new_game から届いた証拠ではない。V3-2 までの固定の対戦の到達範囲と足さない

## 9. 失敗・修正・再実行・未確かめ

- fixture の誤り: 実行の前に 1 つ（6 章。F1 のカード ID）。エンジンの不具合ではない。直したあとの fixture で、整合の確かめと 4 ケースを実行した（ケースの再実行はしていない）
- テスト: 失敗なし（7 章）
- エンジンの不具合: 見つかっていない（`suspect` 0）
- 未確かめ・対象の外: 構築盤面から始めた実行の完全な再現用記録・`replay_run`・`snapshot_replay`（new_game からでないので対象の外）、R-B、C1 の受理のあとに相手・観戦者へ見えるカード
  id の中身（うらの数が 0 になったことだけを確かめた）、HC1（受理の前のエンジンの拒否で停止系の分類）は代表例に入れていない（停止系の拒否の `known_stop` は単体のテストだけ）、
  ほかの規約集合、広いデッキ、探索

## 10. 次の段階へ残すもの

- `KNOWN_STOP_EVIDENCE` は DU1 だけ。ほかの停止（HC1・準備の停止 `UNRESOLVED_MULLIGAN_COMPENSATION` など）を `known_stop` にするには、それぞれの代表の条件の根拠の登録が要る
- 経路で引く段の参照を読む変異（`count_over`・`non_executable`）は `unsupported_contract` のまま
- new_game から `unverified` に届く固定の条件（V3-4 の探索の判断）、R-B、構築盤面の記録の形式（完全な再現用記録の外の、スナップショットから始まる記録）の判断
- V3 の設計の残り・CN-1 のエンジンの側・D-12・きぜつの数え方は変わらない
