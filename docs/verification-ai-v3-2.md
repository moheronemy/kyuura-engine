# 検証用 AI の V3-2（カツラの固定の到達例: options_by_path と BoundaryPolicy）

[V3 の仕様と計画](verification-ai-v3-design.md) の V3-2 を、既存のカツラの固定の到達例に絞って実装しました。`options_by_path` の正常な入力と不正な入力を確かめ、boundary の
対象へ届いたかを分けて記録します。構築した盤面・seed の探索・広いデッキと規約集合・R-B・V3-3 以降は対象外です。V3-1 は [verification-ai-v3-1.md](verification-ai-v3-1.md)。

1 章〜7 章は対戦の実行の前に書き、コードと同じコミットに入れました。8 章以降は実行のあとに書きます。指示の最後の文は「必要な場面の確認後は計」で途切れていたので、
「必要な場面を確かめたら、計画した止まり方で止める」と読み、局 1・2 はつける操作の受理のあと、局 3 は 40 操作で止める計画にしました。

## 1. 基点と範囲

| 項目 | 値 |
|---|---|
| 基点 | `claude/verification-ai-v3-1` の `bc25064`（V3-1。実行は `8091ed6`。`kyuura_engine` は `e26df79`（0.172.0）と同じ） |
| ブランチ | `claude/verification-ai-v3-2`（worktree `C:\dev\kyuura-engine-vai`） |
| 変えていないもの | エンジン本体・GUI・renderer・カードデータ・既存の固定デッキ・規約集合・識別の方式・既存の方策（意味の列の sha256 のテスト）・V3-1 の変異の種類 |

## 2. 固定の到達例

| 項目 | 値 |
|---|---|
| 出典 | `tests/test_legal_actions_u7_5g_energy2.py` の `BLAINE_DECK`（224 行）・`BLAINE_SEED = 1`（225 行）と `ConnectionTest.test_two_cards_from_new_game`（`e26df79` と同じファイル） |
| 内容 | カツラのガーディ（`PMCG6-027`）4・カツラ（`PMCG6-093`）4・炎エネルギー（`PMCG1-098`）52 の 60 枚を両方のプレイヤーに。sha256 は `tools/verification_ai/run_v3_2.py` の `DECK_SOURCE`（実行の記録にも書く） |
| 保持 | 道具の固定の例として `run_v3_2.py` に写した（実行時に `tests/` を読まない。テストは写しと出典が同じことを確かめる）。既存の固定デッキ（`kyuura_engine/decks.py`）ではない |
| 列 | new_game（既定の規約集合・seed 1）→ 準備（両方のプレイヤーが、バトル場に eligible の最初・ベンチに次の 1 枚、補償は最大）→ ジャンケン（勝者 0）→ プレイヤー 0 がカツラを使う → エネルギーをつける（1 段目: 最初の炎、2 段目: 最初のカツラのガーディ、3 段目: 2 枚つけるときは最初の炎） |
| 進め方 | 固定の到達の列の選び手（`FixedReachPolicy`。記録の名前 `fixed-reach`）が、API の応答の候補の種類と、選べるものの公開の項目（`card_id`・段の `role`）で選ぶ。入力は行動生成が段の契約から作り、check・submit を通す。カード名からコマンドを作らない。乱数を使わない。想定した候補・選べるものがなければ推測で続けず止める（例外 `ScriptMiss`） |
| 1 枚と 2 枚 | 別々の対戦で同じ列を最初から走らせる（状態を巻き戻さない・内部の状態を変えない） |

## 3. options_by_path の確かめと変異

- 実際の応答（つける操作の段）から、`path_stages` の並び・鍵を作る上流の選ぶもの・鍵ごとの参照（`eligible`・処理可能性・カード）・鍵ごとに使えない 3 段目の選ぶもの・3 段目を
  省いたときの入力の長さを記録する（`options_by_path.json`）
- 正常な入力: 2 枚目なし（3 段目を省く。入力は 2 つ）と 2 枚目あり（入力は 3 つ）。どちらも check のあとに 1 回だけ submit し、受理のあとの本人の観測（つけた場のポケモンの炎エネルギーの
  枚数の増え方）と、完全な記録のコマンド（`attach_energy` の `energy2` の有無）で実際につけたものを確かめる（`attachment.json`）。GUI の確かめではなく、AI の道具を通した確かめ
- 変異（V3-1 の種類に加えた 2 つ。V3-1 の種類は変えない。`negative.V3_2_TYPES` の順に、つける操作の前に 1 回ずつ。前提を満たさなければ not_applicable）:
  - `path_mix_path`: `options_by_path` の段で、上流の選び方（鍵）を保ち、その鍵の参照にない選ぶもの（ほかの鍵の参照にあり、この段にある番号）にかえる。対象の外: この鍵の参照にも
    ある（両方の経路で許される）、上流で選んだものと同じカード（`card`）を指す（同じカードを 2 回選ぶことにもなり条件が重なる）、どの鍵でも実行できる区分でない、後の段がこの段に依存する
  - `duplicate_replace`: 同じ段（同じ役割）で 2 つ以上選んでいるとき、1 つを、その段の別の選んだものと同じ番号にする（個数は変えない）。役割の違う段の番号どうし（1 段目と 3 段目の
    炎など）を同じにすることは、単一の条件の重複の試験にしない
  - ほか: `unknown_option`・`count_over`・`count_under`・`path_mix`（`options_by_choice`）・`non_executable`・`wrong_actor`・`stale_after_accept`（V3-1 と同じ）
- 予想（実行の前の静的な読み取り）: カツラの例では 3 段目の参照は「1 段目と別の炎のカード」で、ほかの鍵の参照にだけある選ぶものは 1 段目と同じカードになる。そのため
  `path_mix_path` は条件が重なって not_applicable になる見込み。`duplicate_replace` は 2 つ以上選ぶ段がないので not_applicable の見込み。どちらも探索・条件の緩和で届かせない
- 副作用の確かめ・復帰の check・通常の送信 1 回・古い取っ手は V3-1 と同じ（[V3-1 の 2 章・3 章](verification-ai-v3-1.md)）

## 4. BoundaryPolicy

- 範囲（ランナーのプロファイル `boundary`）: `deep` の範囲に `unverified` の候補を加える。表示だけ・入力を返さない・実行できない区分は外したまま（通常の送信の対象にしない）。
  入力の組み立ても `unverified` の選べるものを許す。`deep` の動作と乱数の使い方は変えない
- 選び方（`BoundaryPolicy`。分布 `boundary-class-uniform+uniform-stage`）: 渡された候補の**候補の処理可能性**の区分を列挙し、区分を均等に 1 つ、その区分の候補を均等に 1 つ（区分・候補が
  1 つなら乱数を使わない）。入力は uniform-stage。合法性を判定しない
- 候補と完成した入力の区分の違い: 候補の処理可能性は、選べるもの・組の中でいちばん進めやすい区分。完成した入力の区分（`actions.input_processability`）は、選んだものごとの区分
  （依存する段は `options_by_choice` の参照、経路で引く段は `options_by_path` の参照、ほかは選べるもの）の中でいちばん進めにくい区分。試みの記録に `candidate_class` と
  `input_processability` を分けて書き、候補の区分だけで完成した入力も同じ区分だったとは数えない
- 固定の到達の列で目的の場面へ進めたもの（局 1・2。理由のコード `fixed-reach:…`）と、BoundaryPolicy が自分で選んだもの（局 3。`boundary:class:…`）を記録の上で分ける

## 5. 判定の規則の版 2（`judge.JUDGE_RULES_VERSION = 2`）

V3-1 の判定（規則 1。`8091ed6`）を読み直し、停止系の拒否を `known_stop` にする条件を絞りました。V3-1 の保存した判定の記録は書きかえません。

- 区分（`may_stop_later`・`unverified`）だけで `known_stop` にしない。停止系の分類（`unresolved_ruling`・`unsupported`・`technical_limit`）の拒否を `known_stop` にするのは、
  (1) エンジンの元のコードが診断のコード表にあり、表の分類が診断の分類と同じ、(2) その経路の候補か選んだものの理由が、エンジンの側の確かめを候補の作成では評価していないことを示す
  （`preflight_not_evaluated`・`continuation_not_evaluated`・`reactions_not_evaluated`・`use_condition_not_evaluated`・`face_down_reveal_not_evaluated`・
  `segment_setup_not_evaluated`・`turn_start_not_evaluated`・`checkup_not_evaluated`）ときだけ。(1) がなければ `undetermined`（`stop_code_not_in_catalog`）、(2) がなければ
  `undetermined`（`stop_not_explained_by_path`）
- コード表の分類と診断の分類が違えば `suspect`。コード表にない診断（`unmapped`）は `suspect`（規則 1 と同じ）
- 前の確かめを満たす種類で、`supported` の停止系の拒否は `suspect`、`invalid_input` は `suspect`（規則 1 と同じ）
- エンジンの `rejected` とホストの段の `refused` を分ける（check が valid のあとの `refused` は `suspect`）。`failed`・例外・副作用・保証との食い違いは別に記録する（規則 1 と同じ）
- 終わり方 `script_complete`（計画した止まり方）は `expected`

## 6. 計画（実行の前に決めた）

| 局 | 目的 | 固定の条件 | 変異の位置 | 止まり方 |
|---|---|---|---|---|
| 1 `one-card` | 固定の列で、エネルギーを 1 枚つける（3 段目を省く） | 2 章のデッキ・seed 1・既定の規約集合 | プレイヤー 0 のつける操作（1 回目）の送信の前。`V3_2_TYPES` の順に 1 回ずつ | つける操作の受理と古い取っ手の試験のあと `script_complete` |
| 2 `two-card` | 同じ列で、エネルギーを 2 枚つける | 同上 | 同上 | 同上 |
| 3 `boundary` | BoundaryPolicy の短い確かめ（方策が選ぶ） | 同上（`policy=boundary`・`profile=boundary`） | なし | 40 操作（`limit_operations`） |

上限: 1 局の上限は V0〜V3-1 と同じ（局 3 は操作 40）。変異の要求は 1 局 60 まで。全体の予算 600 秒。結果を見て seed・局・変異を変えません。届かなければ未到達として残します。

入口: `python -m tools.verification_ai.run_v3_2 run --out C:/dev/kyuura-engine-verification-vai --engine-commit <sha>`。終了コードは V3-1 と同じ（0・3・1）。

## 7. テスト

`tests/test_verification_ai_v3_2.py`（10 テスト）: 写したデッキが出典と同じ（`DeckTest`）、`options_by_path` の単一の条件の別の経路・カツラの形の重なりで not_applicable・両方の経路で
許されるもの・省いた入力、個数を保った重複と役割の違う段の見送り（`PathMutationTest`）、候補の区分と完成した入力の区分の違い（`InputProcessabilityTest`）、区分 → 候補の選び方と
乱数の回数・boundary の範囲に表示だけ・入力を返さない・実行できない区分が入らないこと・deep は変わらない（`BoundaryPolicyTest`）、規則 2 の `known_stop`・`undetermined`・
`suspect`（`JudgeRulesTest`）、固定の列の 1 枚と 2 枚（メモリの中の対戦。証跡の局とは別）・通常の送信 1 回・復帰・変異の判定・副作用で止まる（`FixedReachTest`）。

規則 2 にしたので、`tests/test_verification_ai_v3_1.py` の `JudgeTest` の 1 行（停止系の拒否を、元のコードと経路の理由なしで `known_stop` と期待していた）を規則 2 の期待に直した
（意図した差）。

テストの実行（1 モジュールずつ、別のプロセス）: `tests.test_verification_ai_v3_2`（10 テスト）は 2 つ失敗（`FixedReachTest` の 1 枚・2 枚。完全な記録のコマンドの `type` を `AttachEnergy` と
書いて探していたが、記録の値は `attach_energy` だった。道具の誤り）。`run_v3_2.py` を直して `FixedReachTest` だけ（2 テスト）を再実行: 失敗 0。ランナー・判定・変異・方策を変えたので
`tests.test_verification_ai_v3_1`（15）・`v2_repeat`（15。既存の方策の意味の列の sha256）・`v2`（19）・`v1`（19）・`v0`（24）: 失敗 0。実行のあとに加えた `SummarizeTest`（1 テスト）
だけを実行: 失敗 0（8.2 節）。

## 8. 実行の結果（2026-11-08）

### 8.1 実行と、集計の書き出しの失敗

| 手順 | 内容 | 終了コード |
|---|---|---|
| 1 | `run_v3_2 run`（コミット `0cc21df`。1〜7 章と同じコミット）。14:34:05Z〜14:34:07Z（UTC）。計画（`plan.json`）を書いてから 3 局を 1 局ずつ実行し、局ごとの記録（完全な記録・操作の記録・本人向けの記録・変異・`options_by_path.json`・`attachment.json`・`verification.json`）を書いた。そのあと集計（`aggregate.json`）の書き出しで `TypeError`（BoundaryPolicy の局の、入力のない候補の完成した入力の区分が None で、キーの並べかえで止まった） | 1 |
| 2 | 道具を直してコミット（`c2155a4`）。`run_v3_2 summarize` で、保存した局のファイルだけから集計と公開の集計を書いた（対戦を走らせていない。局の数は 3 のまま） | 0 |

### 8.2 3 局の結果

| 局 | 選び手 | 終わり方（判定） | 受理 | `replay_run` | 記録の対応 | 通常の送信の判定 |
|---|---|---|---|---|---|---|
| `one-card` | 固定の到達の列（`fixed-reach` 6） | `script_complete`（`expected`） | 6 | 期待 `succeeded`・結果 `succeeded` | 問題 0 | `expected` 6 |
| `two-card` | 固定の到達の列（`fixed-reach` 6） | `script_complete`（`expected`） | 6 | 期待 `succeeded`・結果 `succeeded` | 問題 0 | `expected` 6 |
| `boundary` | BoundaryPolicy（`boundary` 40）・ホストの係（均等 1） | `limit_operations`（`expected`。道具の上限） | 40 | 期待 `succeeded`・結果 `succeeded` | 問題 0 | （記録しない。negative のない局） |

### 8.3 options_by_path（実際の応答。`two-card/options_by_path.json`）

- 3 段目: `path_stages` は `[1, 2]`、`count` は 0〜1、`decline` 真。3 段目の選べるものは手札の炎 7 枚（`o9`〜`o15`。どれも `eligible` 真・`may_stop_later`）
- 鍵は 7 つ（`o1/o8`〜`o7/o8`）。上流は 1 段目の炎のどれか（`o1`〜`o7`）と、2 段目のカツラのガーディ（`o8`。場で選べるのはこの 1 匹だけ）
- 鍵ごとの参照は 6 つで、どれも `eligible` 真・`may_stop_later`。鍵ごとに使えない 3 段目の選ぶものは、1 段目で選んだ炎と同じカード 1 つだけ（例: 鍵 `o1/o8` では `o9`）
- 3 段目を省いた入力は 2 つ（`one-card` の入力 `[o1, o8]`）、2 枚目ありは 3 つ（`two-card` の入力 `[o1, o8, o10]`）
- 受理のあとの確かめ（`attachment.json`）: `one-card` はつけた場のポケモンの炎が 0 → 1、完全な記録のコマンドに `energy2` なし。`two-card` は 0 → 2、コマンドに `energy2` あり

### 8.4 変異（つける操作の前）

| 局 | 実行した変異（check / submit） | 判定 | 復帰の check |
|---|---|---|---|
| `one-card` | `unknown_option`・`wrong_actor`・`stale_after_accept`（3 / 3） | すべて `expected` | 1（`expected`） |
| `two-card` | `unknown_option`・`wrong_actor`・`stale_after_accept`（3 / 3） | すべて `expected` | 1（`expected`） |

- `suspect` 0・`undetermined` 0。変異の前後の確認値・状態のオブジェクト・新しい更新・更新の番号は変わらず、通常の送信は 1 回だけ
- not_applicable:
  - `path_mix_path`（両方の局）: 前提を満たす例がない。3 段目のほかの鍵にだけある選ぶものは、1 段目で選んだ炎と同じカードだけで、同じカードを 2 回選ぶ条件と重なる（3 章の予想どおり）。
    **options_by_path の単一の条件の別の経路の混ぜ方は、この固定の条件では未到達**
  - `duplicate_replace`（両方）: 2 つ以上選ぶ段がない（役割の違う段の炎を同じにすることは試験にしない）。**未到達**
  - `count_over`: `one-card` は 3 段目が上限でない。`two-card` は理由が `no_extra_option` だが、実際の応答には同じ鍵の参照にほかの炎（`o11`〜`o15`）がある。V3-1 の `count_over` の関数
    （`_allowed_now`）は経路で引く段の参照を読まないので、前提がないのではなく**道具が対応していない**（V3-1 の種類を変えない方針のため直していない）
  - `count_under`: 最後の段が下限でない。`path_mix`（`options_by_choice`）: 2 段目の参照がどの 1 段目でも同じ。`non_executable`: 実行できない区分の選べるものがない

### 8.5 BoundaryPolicy

- 実装と単体の確かめ: 区分 → 候補の選び方、乱数の回数、boundary の範囲（表示だけ・入力を返さない・実行できない区分を入れない）、deep が変わらないこと（7 章）
- 実際の対戦（`boundary` の局。40 操作）: 示された候補の区分は `supported`（取得ごと 60）・`may_stop_later`（47）だけで、**`unverified` は示されなかった（boundary の対象に未到達）**。
  BoundaryPolicy が選んだ候補の区分は `supported` 18・`may_stop_later` 22、作った完成した入力の区分は `supported` 17・`may_stop_later` 2・入力なし 21
- 受理した種類: `place_starting` 2・`mulligan_draw` 1・`report_janken` 1・`play_basic` 1・`play_trainer` 2・`attach_energy` 7・`retreat` 7・`end_turn` 19
- 固定の到達の列で場面へ進めたもの（局 1・2）と、BoundaryPolicy が選んだもの（局 3）は、試みの記録の理由のコード（`fixed-reach:…`・`boundary:class:…`）で分かれている。正常な
  2 枚目の実行（局 2）を、未確認の経路の確かめとは数えない

### 8.6 判定の規則 2

実際の対戦では拒否・停止がなく、停止系の拒否の判定（`known_stop`・`undetermined`）は単体のテストだけで確かめました（7 章の `JudgeRulesTest`）。

## 9. 失敗・修正・再実行・未確かめ

- 失敗と修正: テストの 2 つ（記録のコマンドの `type` の誤り。7 章のあと）、実行の集計の書き出し（8.1 節）。どちらも道具の誤り。エンジンの不具合は見つかっていない（`suspect` 0）
- 再実行: 失敗したテストのクラスだけ・加えたテストだけ。対戦の再実行はしていない（3 局は 1 回ずつ。集計は保存したファイルから作った）
- 未実行: なし
- 未確かめ: `options_by_path` の単一の条件の別の経路と個数を保った重複（前提を満たす例がない）、経路で引く段の `count_over`（道具の未対応）、`unverified` の経路（boundary の対象に
  未到達）、停止系の拒否の判定の実際の対戦、ほかの規約集合（S2A・PO）での同じ列（既存の U7 のテストは 3 つの規約集合で 2 枚をつけている）、別のプロセスでの再現

## 10. V3-3 以降へ進むための残件

- `options_by_path` の別の経路を単一の条件で試すには、鍵ごとの参照の差が「同じカード」でない固定の条件（場にカツラのポケモンとそうでないポケモンがいて、2 段目で経路が分かれる例など）が
  要る。今の固定の条件では届かない（探索はしていない）
- 経路で引く段の参照を読む `count_over` は、V3-1 の種類を変えるか、新しい種類として加えるかの判断が要る
- `unverified` に届く固定の条件がない（構築した盤面の V3-3、探索の V3-4 の判断）
- V3 の設計の残りの判断（D-V3-*）・R-B・CN-1 のエンジンの側・D-12・きぜつの数え方は変わらない

## 11. 訂正と補完（V3-3 で追記。2026-11-08）

過去の証跡は直さず、この文書の誤りと記録の不足を訂正します。対戦の再実行はしていません。

- テストの件数（7 章のあとの実行の記録の補完。この会話の実行の出力から。件数のための再実行はしていない）:
  1. `tests.test_verification_ai_v3_2` の最初の実行: `Ran 10 tests`・`FAILED (failures=2)`。失敗は `FixedReachTest.test_one_and_two_cards` の 1 つのテストの 2 つの subTest（1 枚・2 枚）で、
     「2 つ失敗」と書いたのは 2 つのテストではなく 2 つの subTest の失敗の数
  2. `tests.test_verification_ai_v3_2.FixedReachTest` だけ: `Ran 2 tests`・`OK`
  3. 実行のあとに `SummarizeTest` を加え、`tests.test_verification_ai_v3_2.SummarizeTest` だけ: `Ran 1 test`・`OK`
  4. **V3-2 のコード（`c2155a4`）で、`tests.test_verification_ai_v3_2` の全体（11 テスト）を 1 回で通した実行はない**。V3-3 で変異・判定を変えたあとのコードでの全体の実行は
     [verification-ai-v3-3.md](verification-ai-v3-3.md) 7 章（V3-2 のコードの結果ではない）
- 分類の訂正: 8.4 節の `two-card` の `count_over` の `no_extra_option` は、前提の不足ではなく、生成器（`_allowed_now`）が経路で引く段の参照を読まないことによる見送りでした
  （`unsupported_contract`）。同じく、経路で引く段の `non_executable` の `no_non_executable_option` も、生成器が経路で引く段の参照を読まないので `unsupported_contract` にあたります。
  保存した V3-2 の記録（`negatives.jsonl`）の値は書きかえていません（V3-3 の 2 章の分類で読む）
- 判定の規則: V3-2 の局の判定は規則 2 です。規則 3（V3-3）では、根拠のない停止系の拒否・停止は `known_stop` にしません。V3-2 の局には停止系の拒否・停止がなかったので、判定の結果は変わりません
