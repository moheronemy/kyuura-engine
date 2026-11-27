# v0.197: 「とうめい」で受けないと決まったあとの特殊状態のワザのコインのプレイ用の続行規約（開発用の集合 CS-KYUURA-PLAY-TR7@1）

2026-11-22。利用者が採用した[設計](t19b-evaded-effect-coin-design.md)の案 B を実装しました。相手の対戦ポケモンが「とうめい」の「おもて」でワザのダメージと特殊状態を受けないと決まったら、ワザを使った側がコインを 1 回投げます。結果は効果に使わず、ワザの処理を続けます。

- **プレイ用の取り決めです。** 史実の裁定は確定していません。停止コード `UNRESOLVED_EVADED_EFFECT_COIN`（T19b）は、厳密側・既存の集合・対象の外の経路で active のままです。kyuura の論点 `UQ-COIN-IN-NULLIFIED-ELEMENT` も解決にしていません。
- **既定では有効になりません。** 省略したときの集合は `CS-KYUURA-CURRENT@1` のままです。`new_game(..., conventions="CS-KYUURA-PLAY-TR7@1")` のように明示して選んだ対戦だけで当たります。
- CURRENT@1・LEGACY@1・S2A@1・PO@1・TR3@1・TR4@1・TR6@1 の ID・版・中身・照合値は変えていません（TR6@1 は `sha256:aa53bc52…` のまま）。
- 規約 ID は `PC-T19B-NULLIFIED-STATUS-COIN@1` です。族の案 `PC-NULLIFIED-ELEMENT-COIN`（proposal のまま）のうち、T19b の特殊状態の要素の経路だけを採用しました（4 章）。登録の前に、規約 ID・集合 ID が登録表とどのブランチの履歴にもないことを確かめました。
- 範囲は、エンジンの実装と構築盤面での検証までです。GUI の追従、規約を採用したあとの通常の対戦、TR6 の監査の残り 9 局は別の単位です。**通常の対戦でこの場面に届くか・完走するかは確かめていません。**
- 証跡: `kyuura-engine-verification-vai/verifier/runs/t19b-status-coin-v0197/`（事前計画・修正の前後の構築盤面・判定・テストの前後・識別・配布の確かめ・失敗と再試行）。

## 1. 基点・コミット・識別

| 項目 | 値 |
|---|---|
| 基点 | `claude/t19b-evaded-effect-coin-design` の `a90ef86`（`a90ef86f748876a1581e71f4e469834e6c7939be`。origin と一致。版 0.196.0）。公開の全ブランチ 65 の `pyproject.toml` に 0.197 以上はなく、タグもなかった |
| 作業 | worktree `C:\dev\kyuura-engine-lt90`、ブランチ `claude/t19b-status-coin-v0197` |
| コミット | `7f04644`（実装と新しいテスト）・`70572ec`（生成物）・`bca9623`（版を 0.197.0 にする。**配布の確かめの固定コミット** `bca9623e0b7859185f8ec2c703d38c0f3b2ddc0c`）・文書のコミット |

**識別の前後**（実測。証跡の `out/identity_before_a90ef86.json`・`identity_after_fix.json`・`identity_after_version.json`・`dist/identity_installed.json`）

| 項目 | 前（0.196.0） | 修正のあと（版の前） | 後（0.197.0） |
|---|---|---|---|
| パッケージの版 | 0.196.0 | 0.196.0 | 0.197.0 |
| behavior_digest | `4a8edcf0…` | `f7313264…` | `c0199578…`（導入物も同じ） |
| instrumentation_digest | `13c773a8…` | 同じ | 同じ |
| 規則 10（H4）の basis | `b3864eca…` | `20735cb0…` | `20735cb0…` |
| 規約集合 | 7（CURRENT・LEGACY・S2A・PO・TR3・TR4・TR6） | 8（+ TR7 `sha256:4ee438ea…`） | 8 |

規則 10 の basis は `resolution/programs.py` を読むので変わりました（v0.196 と同じ理由。判定の規則・道具は変えていません）。

## 2. 前提の確かめ（実装の前。構築盤面）

修正の前のエンジンで、停止局面と同じ形の盤面を作り、厳密側の挙動を記録しました（証跡の `boards/before_CURRENT.json`・`before_TR6.json`）。盤面は、フーディン（PMCG1-049）の［あやしいひかり］30 と、「とうめい」がはたらくゴースト（PMCG3-030）です。コインは台本の乱数で決めました（1 枚目が「とうめい」、2 枚目がワザのコイン）。

| 盤面 | 台本 | CURRENT@1・TR6@1 |
|---|---|---|
| ゴーストのダメージ 30（「うら」なら HP 以上） | 4 通りすべて（「うら」・「うら」を含む） | T19b で拒否。状態・乱数・ログ・3 者の閲覧の記録は変わらない |
| ゴーストのダメージ 0 | 4 通りすべて | 同じ |
| ビードルの［どくばり］・ゴースの［したでなめる］→ ゴースト | 4 通りすべて | 同じ |
| ドガースの［くさいガス］（「うら」の効果のある型）・ミュウツー ES3-026 の［サイコブラスト］（エネルギーのトラッシュのコイン）→ ゴースト | 4 通りすべて | 同じ |
| 対照: ねむりのゴースト・かがくへんかガス・最終ダメージ 0（ロコンの［あやしいひかり］10 にディフェンダー）・ゴーストでない相手・「ダメージを受けない」相手 | 4 通りすべて | 受理（今の処理） |

- **実際の乱数が「うら」を出す台本でも拒否されました。** 宣言の前の先読みが「とうめい」の「おもて」の枝でワザのコインの問いに当たるためで、設計の見立てどおりです。
- 合法手 API でも、check は有効、submit は T19b で拒否でした（`continuable` 真・状態は変わらない・3 者の閲覧の記録は増えない）。
- 修正の前の judge（既存の runner と `batch.judge_trace`）は、拒否を `evidence_missing_stop`（`stop_condition_not_evidenced:UNRESOLVED_EVADED_EFFECT_COIN`）、判定を `undetermined` にしました（`boards/judge_before_CURRENT.json`）。TR6 の監査の保存記録（`vai-batch-tr6a-m3` の g004）と同じです。保存記録はそのまま残し、当て直していません。

## 3. 実装

| 箇所 | 変更 |
|---|---|
| `conventions.py` | 続行規約 `PC-T19B-NULLIFIED-STATUS-COIN@1`（層 continuation・user_agreed・場面 `UNRESOLVED_EVADED_EFFECT_COIN` の 1 つ。照合値 `sha256:e4082ecb…`）と集合 `CS-KYUURA-PLAY-TR7@1`（usage development・halts_at_undecided。TR6@1 の 25 規約 + 1。照合値 `sha256:4ee438ea…`）。`IMPLEMENTED_CONTINUATIONS` に加えた |
| `resolution/programs.py` | `Status._nullified_coin_path`（状態を変えない。カード ID の定数で分けない）と、`Status.run` のこの要素のコインの前の T19b の分岐。対象の経路なら `continuation_for(state, T19b)` を引き、あれば `record_application`（`player`・`target_owner`・`pokemon_id`・`element`）を書いてから、ワザを使った側がコインを 1 回投げて戻る。なければ今と同じ問いを投げる |
| `tests/log_audit.py` | `s2a_problems` に TR7 の表（規約・場面・項目）と記録の場所の確かめ（同じプレイヤーのワザの「とうめい」の「おもて」のあと・すぐあとが同じワザのコイン 1 枚・「おもて」ならその要素の受けない記録・「うら」なら特殊状態の記録なし） |
| `tests/test_play_convention_tr7_v0_197.py` | 新しいテスト 16 件（5 章） |

**対象の経路**（`_nullified_coin_path`。処理している要素とワザの値だけで決める）:

- 要素: 相手の対戦ポケモンへの特殊状態の要素（`Status`）で、この要素のコインが「おもて」で特殊状態・「うら」の効果なし。ワザ全体のコイン・前の結果・入れ替え・ダメージのあとの条件・特殊などくの条件はない。
- ワザ: 元のワザ（宣言したワザと処理しているワザが同じで、ワザを使ったポケモンの印刷のカードがそのワザのカード）で、効果の登録の型が `ConfuseOnHeads`・`PoisonOnHeads`・`ParalyzeOnHeads` のどれか（登録は 31・30・95 のワザ）。
- 条件: 対象が、このワザのダメージの要素で「とうめい」の「おもて」になり、受けないと決まっている（`reception` が偽）。HP 以上なら、今までどおりこの要素は処理しない（コインを投げない）。

候補・入力・check の契約と、保存の形式（状態の書き出しの形式・記録の形式）は変えていません。

### 3.1 受理したときの状態とログ（TR7。構築盤面の実測）

| 枝 | コイン（投げ手・順番） | 乱数の消費 | 規約の記録 | ダメージ・特殊状態 | ログの並び | 決定・番 |
|---|---|---|---|---|---|---|
| 「とうめい」の「おもて」・ワザのコイン「おもて」 | ゴースト側（主体 1）の `power` → ワザを使った側（主体 0）の `attack` | 2 | 1 | ダメージなし（30 のまま）・こんらんなし | `attack` → `coin_flip`（power）→ `evade_check`（heads）→ `attack_evaded`（damage・30）→ `convention_applied` → `coin_flip`（attack・heads）→ `attack_evaded`（confusion）→ `turn_end` | 決定なし。番が終わり、相手の番が始まる |
| 同・ワザのコイン「うら」 | 同じ | 2 | 1 | 同じ | 上と同じで、ワザのコインのあとの `attack_evaded`（confusion）がない | 同じ |
| 「とうめい」の「うら」・HP 以上 | ゴースト側の `power` だけ | 1 | なし | 30 ダメージで HP 以上 | `coin_flip` → `evade_check`（tails）→ `damage` → `knock_out` | サイドを取る決定（`take_prize`） |
| 「とうめい」の「うら」・HP 未満 | `power` → `attack` | 2 | なし | 30 ダメージ・「おもて」ならこんらん | 今の処理と同じ | 今と同じ |

- 乱数の消費は、ログのコインの数と同じでした。先読みのログと乱数の消費は、実際の対戦に残っていません。
- 規約の記録は 1 回の適用につき 1 件です（項目は `player` 0・`target_owner` 1・`pokemon_id`・`element` `confusion`。全員に見える値だけ）。
- 主体 0・1・観戦者が受け取る記録の並びは同じでした（コインの結果・規約の記録は公開）。
- ビードルの［どくばり］（`PoisonOnHeads`）とゴースの［したでなめる］（`ParalyzeOnHeads`）も、同じ並び・同じ続き（要素の並びの最後。番の終わり）でした。`element` はそれぞれ `poison`・`paralysis` です。

## 4. 規約案との対応と、採用した型

| | 内容 |
|---|---|
| 族の案 `PC-NULLIFIED-ELEMENT-COIN`（proposal のまま） | 効果がはたらかない要素のコインを投げるか。5 コード |
| 今回採用した範囲 | T19b のうち、特殊状態の要素（`Status`）のこの要素のコインの前の 1 か所だけ。D1 の「投げる」を、結果を使わない形で当てた |
| 採用した型 | `ConfuseOnHeads`（実測の型）・`PoisonOnHeads`・`ParalyzeOnHeads`。3 つとも、要素の並びが「ダメージ → この要素のコイン → 特殊状態」で同じで、無効化の条件（ダメージの要素の「とうめい」の「おもて」）と再開先（要素の並びの最後）がソースと構築盤面（S6）で同じだった |
| 保留した型・経路（T19b のまま） | `Status` のほかの型（「うら」の効果のある型。例: ドガースの［くさいガス］）、特殊状態の要素でない T19b の 14 か所（例: ミュウツーの［サイコブラスト］のエネルギーのトラッシュのコイン）、コピー・［へんしん］で持つワザ。構築盤面とソースで、同じ条件で扱える根拠を確かめていないため |
| ほかの停止コード（変えていない） | `UNRESOLVED_PREVENTED_COIN_DAMAGE`・`UNRESOLVED_PREVENTED_EFFECT_COIN`・`UNRESOLVED_DISCARD_PROTECTED_COIN`・`UNRESOLVED_KEEP_VOIDED_DISCARD_COIN` |

## 5. テストと検証（設計 7 章の S1〜S9）

`tests/test_play_convention_tr7_v0_197.py`（16 件）。エンジンの 2 ファイル（`conventions.py`・`resolution/programs.py`）を戻した状態では、TR7 を使う件が 49 件のエラー（集合を知らない）になり、厳密側の件は通りました（`out/tests_dev/tr7_before_fix.txt`）。修正のあとはすべて通りました。

| 盤面 | 結果 |
|---|---|
| S1 厳密側の拒否と巻き戻し | CURRENT@1・TR4@1・TR6@1 で、ダメージ 30・0 と 4 通りの台本すべてが T19b。状態・乱数・ログ・3 者の閲覧の記録は変わらない。API では本人に拒否の応答（`in_progress`）・閲覧の記録は増えない |
| S2 TR7「おもて」 | 3.1 節。ワザのコインは両方の結果を試した |
| S3 TR7「うら」・HP 以上 | ワザのコイン・規約の記録なし・きぜつ・サイドの決定 |
| S4 TR7「うら」・HP 未満 | 今の処理と同じ（規約の記録なし） |
| S5 無効化が起きない・一部だけ無効の対照 | ねむり・かがくへんかガス・最終ダメージ 0・ゴーストでない相手・「ダメージを受けない」相手で、TR7 と厳密側のログ・乱数・状態が同じ（修正の前の記録とも同じ） |
| S6 ほかの 2 つの型 | `PoisonOnHeads`・`ParalyzeOnHeads` は厳密側で T19b、TR7 で S2 と同じ形の受理 |
| S7 対象外の経路 | ［くさいガス］・［サイコブラスト］は TR7 でも T19b（状態は変わらない）。経路の判定にカード ID の定数がない |
| S8 既存の集合 | 既存の集合の照合値・メンバーは同じ。TR7@1 は TR6@1 の 25 規約 + 1。既定の集合は CURRENT@1 |
| S9 API と監査・判定 | 候補・入力・check は両方の集合で同じ、submit だけが違う。主体 0・1・観戦者の閲覧の記録の増え方は同じ。ログの監査は記録を受け付け、項目・場所の改変を見つける。**記録の再実行（replay）は確かめていません。** 構築盤面のスナップショットから始めた runner の記録には再現用の形式の印がなく、`replay_run.replay` は TR7・厳密側とも `invalid_record`（`format_missing`）でした。既存の道具もこの種の記録を「new_game からの完全な記録がない」として対象外にしています |

### 5.1 judge（既存の runner と judge_trace）

| 集合 | 宣言 | 判定 |
|---|---|---|
| TR7@1 | 受理（ダメージ 30・0 と 3 通りの台本） | `expected`。`undetermined` なし・`known_stop` なし。単局の runner の判定も `expected` |
| CURRENT@1 | 拒否 | 今のまま（`evidence_missing_stop`・`undetermined`。judge の根拠表に T19b の項目はない。この版で judge は変えない） |

旧 TR6 の保存記録（本実行の C3・seed 9017）は、拒否が `evidence_missing_stop`、局の終わりが `undetermined` でした。原本はそのまま残しています（作業の前後で照合値が同じ）。

### 5.2 そのほかのテスト・検査

- 実装のあと（`out/checks_impl`。2,400 秒）: 72 モジュール 2,204 件 OK、生成の検査 15 件 0、git status は前後で同じ、`--sites` の出力は基点と同じ（`ABE1CBFA…`）。
- 版のあと（`out/checks_version`）: 5 モジュール・生成の検査 15 件 0。`--sites` の数は同じ（新しい 280・欠け 6）です。候補箇所の全体の集合（1,827）の差は、版を書く行（`tests/test_preset_decks_v0_20.py` の 151 行）の ID が変わった 1 つだけでした（`out/sites_compare_version.json`）。出力の照合値が変わったのは、表示の 50 件の窓にその新しい ID が入ったためです。
- 生成物: 停止の方針の台帳（`docs/stop-policy-classification.json`）と共通規約の設計案（`docs/play-policy-family-plan.json`）を作り直しました。台帳の差は、採用の記録（`AGR-PLAY-TR7-*`・`DEC-NULLIFIED-COINS` を partly_agreed・UPDATES の 0.197.0）、T19b の箇所（規約の場面の宣言と照会）とテストの参照、行番号だけです。設計案の差は `adopted_convention` の 1 項目だけです。

## 6. 配布の確かめ（固定コミット `bca9623`）

`git archive` の展開（リポジトリの外）から wheel を作り、新しい venv に完全なハッシュで導入しました（`out/dist`）。

| 項目 | 結果 |
|---|---|
| パッケージのファイル | 62（基点と同じ）。差は `__init__.py`・`conventions.py`・`resolution/programs.py`。`pyproject.toml` は版の行だけ |
| wheel | `kyuura_engine-0.197.0-py3-none-any.whl`・sha256 `c668cce4814eee9dff5879dca1208bbc110750a315c47454231bb2bb80107d85`。`check_distribution` は required 62・problems 0 |
| 導入 | 新しい venv に `pip install --no-deps --require-hashes -r req_hashed.txt`（完全な sha256）。editable でない（`direct_url` は `archive_info`、ハッシュは wheel と同じ）。導入物は `kyuura-engine==0.197.0` と pip だけ |
| スモーク | 厳密側（CURRENT・TR6）、TR7 の「おもて」の両方のワザのコインと「うら」（きぜつ）、無効化の起きない対照（両方の集合）の 8 盤面。ソースの木と導入物で結果の照合値が一致（`9f82dd66…`・problems 0）。実装の識別も同じ |

## 7. 残る作業

- 通常の対戦（new_game）でこの場面に届くか・規約で続けた対戦が完走するかの確認（TR7 を明示した対戦。TR6 の監査の残り 9 局とは別の単位）。
  - 2026-11-22: 旧 TR6 監査で停止した C3 の seed 9017 の局を、TR6@1 と TR7@1 の各 1 局で比べました（2 局完了・`MATCHED`）。TR6 の T19b の拒否が、TR7 では受理され、番が進んで局は完走しました。通常の対戦で出た枝は「おもて」（ワザ側のコインは「うら」）と「うら」できぜつの 2 つです: [T19b の停止局の TR6／TR7 比較](history/t19b-tr6-tr7-comparison.md)
  - 2026-11-22: 旧 TR6 監査の未着手 9 条件を、TR7@1 の補足バッチ（4 計画・9 局）で実行しました（9 局完了・すべて `game_over`・拒否 0・打ち切りなし）。T19b の場面は出ていません: [TR7 の補足バッチ](history/tr7-supplemental-audit.md)
- GUI の追従（集合の明示選択・規約の記録の表示）。
- 族の案のほかの経路・ほかの停止コード、judge の根拠表の T19b（厳密側の分類）、方策の選び直し（設計の D5・D6）。

## 8. 失敗・修正・再試行・未確認

- 作業場所を Git Bash の git で作ったため、全ファイルが CRLF で書き出され、PowerShell の git では 964 ファイルが変更に見えた。差は改行だけ（`--ignore-cr-at-eol` で差なし）で、自分の変更はなかった。PowerShell の git で書き出し直し、修正の前の盤面の記録を取り直した（取り直した記録は最初の記録と一致。最初の記録は証跡の `raw/F1_crlf_checkout`）。
- 最初の実装で、規約 ID の衝突を確かめる実行時の例外を `conventions.py` に置いたところ、内部ガードの数が 619 から 620 に増えた。衝突の確かめは登録の前の作業とテストで行うことにして外し、生成物を作り直した（照合値は同じ）。
- 関連テストを回すスクリプトの初版は、モジュールの配列が `pwsh -File` で 1 つ目しか渡らず、1 モジュールだけを実行した。H4 の確かめのスクリプトの写しに置きかえた。
- 配布の確かめのスクリプトの写しを作る最初の試みは、文字列のエスケープの誤りで止まった（何も書いていない）。
- この文書と設計文書 8 章の最初の文面の 3 行が、`--sites` の候補の語に当たり、新しい候補箇所が 3 つ増えた。意味を変えずに言いかえ、候補箇所の全体の集合を基点と同じにもどした（差は版を書く行の 1 つだけ。証跡の `out/sites_compare_docs1.json`・`sites_compare_docs2.json`）。
- 未確認: 通常の対戦での到達・完走、規約で受理した対戦の記録の再実行（構築盤面の記録は再現用の形式でない）、GUI、コピー・［へんしん］の経路（対象の外にしたまま）。
