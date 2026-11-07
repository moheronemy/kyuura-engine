# U7-5a・U7-5b: 場のポケモン 1 匹を指す操作の候補と入力（v0.167）

合法手 API（U7）に、既存の 3 つのコマンドの候補・入力・検査・送信を加えました。

| 種類 | コマンド | 単位 |
|---|---|---|
| `remove_disguise` | `RemoveDisguise(player, pokemon)` | U7-5a |
| `discard_from_play` | `DiscardFromPlay(player, pokemon)` | U7-5a |
| `reveal_face_down` | `RevealFaceDown(player, pokemon)` | U7-5b |

仕様と実装計画は [legal-actions-u7-5-design](legal-actions-u7-5-design.md)・[legal-actions-u7-5-implementation-plan](legal-actions-u7-5-implementation-plan.md) です。採用の記録（ADOPT-U7-5AB）と仕様の訂正（CORR-1・CORR-2）は、その文書の「採用の記録と仕様の訂正」にあり、ここでは実装だけを書きます。トレーナー・特殊能力・スタジアム・`CheckFaceUpDeckCard`・3 段の入力・型ごとの入力の宣言・カツラの 2 枚目（`energy2`）は実装していません。

## 1. 基本の契約

- 新しい操作を作りません。既存のコマンドの意味・受理の条件・処理の順・停止のコード・理由の文は変えていません
- 候補の作成・`inputs`・`check` は、エンジンの受け付ける前の確かめ（下の 3 つの関数）だけを呼びます。`apply_command` を試さず、先読み・処理のあとの確かめを呼ばず、状態・乱数・ログを変えません
- 送信は既存のアダプタ（包んだ対戦の `submit`）に任せ、最終の判定は `apply_command` に残します
- モード名・カード ID による共通処理の分岐は加えていません

## 2. 3 つのコマンドと、今のエンジンの扱い

| | `RemoveDisguise` | `DiscardFromPlay` | `RevealFaceDown` |
|---|---|---|---|
| 送る主体 | 番のプレイヤー | 番のプレイヤー | 番のプレイヤー（うらのカードの持ち主） |
| 段階 | `Phase.MAIN`（決定を待つあいだは段階が違うので受け付けない） | 同じ | 同じ |
| 対象 | 自分の場（バトル場・ベンチ）の、「ばける」でのせたカードのあるポケモン | 自分の場の、いちばん上がポケモンとして出したトレーナー（なにかの化石・ピッピ人形）で、`discardable_from_play` のもの | 自分の場のうらのカード（マチスの秘策） |
| 回数・禁止 | なし（特殊能力の宣言・トレーナーの使用ではない） | なし。バトル場をはなれられない効果（`leave_lock`）があれば拒否 | なし |
| 処理 | のせたカードを持ち主のトラッシュに置き、元の姿にもどす | ついているカードもいっしょにトラッシュ（きぜつではない） | おもてにして全員に公開。「たねポケモン」でなければ、ついているカードといっしょにトラッシュ |
| 受理のあと | 処理のあとの確かめ（元の姿の最大HP。MH1・TK1）で受け付けないことがある | バトル場が空けば勝ち負け・バトル場に出す決定 | トラッシュでバトル場が空けば勝ち負け・バトル場に出す決定 |

化石・人形かどうかは、既存の登録（`play_as_pokemon_effect`・`discardable_from_play`）で決まります。カード名では判定していません。

## 3. 受け付ける前の確かめの関数化

`engine.py` の 3 つの処理の前半を、同じ順番・同じコード・同じ文のまま、次の関数に移しました。処理はその関数を呼んでから、前と同じ続きをします。

- `check_remove_disguise(state, cmd) -> PokemonInPlay`: 番・段階（`require_turn`）→ 自分の場のポケモン（`POKEMON_NOT_YOURS`・`POKEMON_NOT_IN_PLAY`）→ `NOT_DISGUISED`
- `check_discard_from_play(state, cmd) -> PokemonInPlay`: 番・段階 → 自分の場のポケモン → `NOT_DISCARDABLE` → `LEAVE_ACTIVE_PREVENTED`
- `check_reveal_face_down(state, cmd) -> PokemonInPlay`: 番・段階 → 自分の場のポケモン → `NOT_FACE_DOWN`

元のコードとの差は、`git diff` で関数の境目だけです（移した行は同じ）。読む情報も確かめました。

- 番・段階・自分の場のポケモンの番号・「ばける」でのせたカード（公開のログ `disguise` で出した）・場での役割（おもてのカード）・バトル場をはなれられない効果・うらであること（`secret_plan_placed` で公開）だけです
- うらのカードの本当のカードは読みません
- 例外として、本人のうらのカードを `DiscardFromPlay` で指すと、`NOT_DISCARDABLE` の理由の文を作るときに名前を読み、FD1（`HiddenPropertyRead`）で拒否します。これは v0.67 からの挙動で、本当のカードによりません（設計の F-2）。この挙動は変えていません

関数がコマンドの処理と同じ拒否のコードになることを、3 つの盤面の全部の場のポケモン・両方のプレイヤーで確かめました（`tests/test_legal_actions_u7_5ab.py` の `CheckFunctionTest`）。

## 4. 実行前と実行後の情報境界

- **実行前（候補・`inputs`・`check`）**
  - 選べるものは公開の値だけで作ります（`_pokemon_option`: 場のポケモンの番号・いちばん上のカードの uid・バトル場かベンチか）
  - 本人のうらのカードは `face_down: true` で示し、カード id・名前を返しません。画像のために隠れた定義を読むこともしません
  - `RevealFaceDown` の候補は、おもてにしたあとに残るか・トラッシュするかを予告しません（ADOPT-U7-5AB）。処理可能性は、うらのカードによらず `may_stop_later`（理由 `face_down_reveal_not_evaluated`）です
  - 双子の確かめ: うらのカードの本当のカード（たねポケモンのディグダ・たねでないユンゲラー）だけが違う 2 つの盤面で、本人と相手の候補・入力・件数・並び・制約・理由・不正な入力への応答が同じでした。応答の JSON に、そのカード id・名前は入りません
- **実行後**: ルールで公開される結果は、既存の観測と通知で返します（ログ `secret_plan_revealed`・`secret_plan_discarded`、観測、`client_api` の公開の更新）。実行後に結果が違うこと（ディグダは残り、ユンゲラーはトラッシュ）は、実行前の漏れではありません
- 拒否・断りは、相手・観戦者へ知らせません（公開の更新を作らない）。通常の応答に検証者用の値・生の例外の文は出しません

## 5. 処理可能性・coverage・取っ手

- **処理可能性**（理由はどれも既存の語で、GUI の契約の `reason_codes` にあります）
  - `remove_disguise`: `may_stop_later`（`continuation_not_evaluated`）。元の姿の最大HPの確かめ（MH1・TK1）は処理のあとの確かめで、候補では評価しません。解除の結果を先読みして選べるものを選り分けません
  - `discard_from_play`: U7-3 と同じ条件で `supported`（受理のあとの反応・決定・停止のもとが場にないことを公開の情報で確かめた場合）。ほかは `may_stop_later`（`reactions_not_evaluated`）
  - `reveal_face_down`: `may_stop_later`（`face_down_reveal_not_evaluated`）
  - エンジンの確かめが `UnsupportedError` なら、選べるものとして示し、実行できない区分にします（本人のうらのカードをすてる FD1 は `unresolved_ruling`・`eligible: false`）。ゲーム上の禁止（`IllegalActionError`）は出しません
- **入力の公開**: 3 種類とも `confirmed`（1 段の `choose_option`・場のポケモンの番号）。処理可能性とは別の軸です
- **coverage**: 番の候補は `partial` のままです。
  - 評価した種類に 3 種類を加え、`not_covered_kinds` は `play_trainer`・`use_power`・`use_stadium`・`check_face_up_deck` の 4 種類になりました
  - `scope_kinds` は `MAIN_KINDS` の順のままです（`_scope_kinds`）。評価した種類が `MAIN_KINDS` の途中に加わったので、並べ直さないと順が変わるためです
  - 7 種類の外に残る経路 R-1（カツラの 2 枚目 `AttachEnergy.energy2`。U7-5g）・R-2（自分のうらのバトル場のポケモンの、ワザといっしょに選ぶもの）は、応答の形を変えずに、この文書と設計の 1 章で示します
  - U7 全体を complete とはしていません
- **取っ手**: 主体の固定・状態の持ち主・有限の保持数・失効の契約は U7-1 のままです
  - 受理ですべての取っ手を失効させます
  - 断り・拒否では、他の主体の取っ手を失効させません
  - 古い取っ手・別の主体・別の対戦の取っ手は拒否します

## 6. 直接のコマンドとの一致と、意図した差

- U7 経由・`client_api` 経由・直接のコマンドで、受理・拒否・応答・状態・乱数・ログが一致しました（構築盤面の正常例・バトル場とベンチ・決定・終局・処理のあとの停止）
- 意図した差:
  - 本人のうらのカードを `DiscardFromPlay` で選ぶと、U7 は送る前に断ります（`CANDIDATE_NOT_EXECUTABLE`。`outcome: refused`）。直接のコマンドはエンジンが拒否します（FD1。`outcome: rejected`）。どちらも状態は変わりません
  - 「ばける」の解除が MH1・TK1 に当たるとき、U7 は送る前に断りません（候補は `may_stop_later`）。エンジンが処理のあとの確かめで拒否するので、直接のコマンドと同じ `rejected` です
- U7-3 の候補の失敗を直しました（設計の F-7。`legal_actions.py` だけで、エンジンは変えていません）。にげるの候補が、にげるエネルギーを求めて例外になり、v0.165〜v0.166 では候補の取得そのものが失敗していました
  - バトル場のなにかの化石・ピッピ人形（PF2）: にげるを、実行できない候補（`unresolved_ruling`・選べるものなし）にしました
  - 自分のうらのバトル場のポケモン（FD1）: にげるを `unverified` にし、入力を返さない（`INPUT_BOUNDARY_UNCONFIRMED`）ようにしました。双子で同じです
- 既存のテストの期待の変更は、U7-3・U7-4 の `not_covered_kinds` の 2 か所だけです（3 種類が対応した種類になった）

## 7. client_api と JSON の例

要求の形・契約（`kyuura-client-api`・形式 1）・`kyuura_legal_actions_format` 1 は変えていません。応答の段・選べるものの項目は既存のものだけです（`stage`・`input`・`role`・`meaning`・`count`・`options`・`order`、選べるものの `id`・`pokemon`・`card`・`zone`・`bench_index`・`face_down`・`card_id`・`eligible`・`processability`・`reasons`）。新しいのは種類の名前 3 つと段の `role`（`disguised`・`discard`・`face_down`）です。

候補（`candidates` の 1 件。`guarantees` の文は省略）:

```json
{"id": "c5", "kind": "reveal_face_down", "processability": "may_stop_later", "reasons": ["face_down_reveal_not_evaluated"],
 "guarantees": {"preconditions": "…", "acceptance": "…", "after_acceptance": "…", "supported_scope": "…"},
 "choices_format": "[場のポケモンの番号]", "input_disclosure": "confirmed", "input_stages": [{"stage": 1, "input": "choose_option"}]}
```

入力（`inputs` の `stages[0]`）。うらの対象の表示の例です（カード id・名前を出さない）:

```json
{"stage": 1, "input": "choose_option", "role": "face_down", "meaning": "pokemon", "count": {"min": 1, "max": 1}, "order": "not_applicable",
 "options": [{"id": "o1", "pokemon": 3, "card": 4, "zone": "bench", "bench_index": 0, "face_down": true, "eligible": true, "processability": "may_stop_later",
              "reasons": ["face_down_reveal_not_evaluated"]}]}
```

`remove_disguise`（タケシのキュウコン）・`discard_from_play`（なにかの化石）:

```json
{"stage": 1, "input": "choose_option", "role": "disguised", "meaning": "pokemon", "count": {"min": 1, "max": 1}, "order": "not_applicable",
 "options": [{"id": "o1", "pokemon": 1, "card": 1, "zone": "active", "card_id": "PMCG5-019", "eligible": true, "processability": "may_stop_later",
              "reasons": ["continuation_not_evaluated"]}]}
{"stage": 1, "input": "choose_option", "role": "discard", "meaning": "pokemon", "count": {"min": 1, "max": 1}, "order": "not_applicable",
 "options": [{"id": "o1", "pokemon": 1, "card": 0, "zone": "active", "card_id": "PMCG3-046", "eligible": true, "processability": "supported"}]}
```

本人のうらのカードをすてる選べるもの（実行できない）:

```json
{"id": "o1", "pokemon": 3, "card": 4, "zone": "bench", "bench_index": 0, "face_down": true, "eligible": false, "processability": "unresolved_ruling",
 "reasons": ["stops_before_acceptance"]}
```

検査・送信・受理のあとの決定:

```json
{"contract": "kyuura-client-api", "format": 1, "type": "check", "game": "…", "revision": "…", "candidate": "c3", "choices": ["o9"]}
→ {"valid": false, "refusal": {"code": "CANDIDATE_INPUT_INVALID", "message": "…"}}
{"contract": "kyuura-client-api", "format": 1, "type": "submit", "game": "…", "revision": "…", "candidate": "c3", "choices": ["o1"]}
→ {"ok": true, "outcome": "accepted", "result": {"status": "awaiting_decision", "next": [{"kind": "answer_decision", "player": 0}], …}, "refetch_required": true}
{"contract": "kyuura-client-api", "format": 1, "type": "candidates"}
→ candidates: [{"id": "c1", "kind": "promote_active", …}]   （バトル場のなにかの化石をすてて空いた。U7-1 の候補で答える）
```

拒否と断り:

- 本人のうらのカードをすてる → `{"outcome": "refused", "refusal": {"code": "CANDIDATE_NOT_EXECUTABLE", …}}`
- 「ばける」の解除が MH1 に当たる → `{"outcome": "rejected", …}`（エンジンの拒否。状態は変わらない。相手・観戦者への更新はない）

## 8. GUI への引き継ぎ（GUI リポジトリは変更していない）

- **確かめた GUI**: `kyuura-engine-gui` の `feature/engine-u7-4-attacks` の `3649946`（固定するエンジンは `9506d63`・0.166.0）を、読み取りだけで確かめました。GUI は実行していません。そのため、今の画面でそのまま動くことは保証しません
- **その GUI の契約**: `contract/kyuura-client-api-v1.json` の `turn_kinds_not_covered` に今回の 3 種類があり、`gui_operable_kinds` にありません。エンジンを 0.167.0 にすると、GUI の契約のテストが食い違います。契約の表を直すまで、3 種類は表示だけで選べないはずです（GUI の決まり）
- **GUI 側で必要な更新**:
  - 契約の表: `implemented_kinds`・`gui_operable_kinds` に 3 種類を加え、`turn_kinds_not_covered` から除きます。`stage_roles` に `remove_disguise: ["disguised"]`・`discard_from_play: ["discard"]`・`reveal_face_down: ["face_down"]` を加えます
  - 型・実行時の検証: 1 段の `choose_option`（`meaning: pokemon`）。選べるものの項目は U7-3 の場のポケモンと同じです
  - 表示名: 「ばけるをもどす」「化石・人形をすてる」「うらのカードをおもてにする」など
  - うらの対象は `face_down: true` で、画像を出さずにうらの表示にします。`eligible: false` の選べるもの（FD1）は「処理できない（ゲーム上の禁止ではない）」と表示します
- **送信と表示**: 送る前に `check` を呼び、受理のあとは `promote_active`・`answer_decision` の候補で続けます。`refused`・`rejected`・`accepted` を分けて表示してください
- **固定するコミット**: 通常のインストールとスモークテストで確かめたコミットを、この節に記録します（10 章）

## 9. 次の作業

- **T-F1（錯乱ジムの情報漏れ F-1。トレーナーの前の独立した修正）**: 錯乱ジムの「うら」で、相手がかわりに使えるかの確かめが相手の手札の中身を読み、その結果が公開のログ `chaos_not_borrowable` と、決定 `ACCEPT_REQUEST` が出るかで伝わります。両モード共通の不具合として、U7-5c の前に直します。今回は裁定・動作を変えていません
- **U7-5c（PlayTrainer）**: `_play_trainer` の手札から出す前の部分を、同じ形で `check_play_trainer` にします。状態の複製で試す 11 の実装（E）は、読む値をたどって安全と確かめるまで入力を返しません（CORR-1）

## 10. 制限・確かめた範囲

- テストの種類: 構築盤面（v0.47・v0.49・v0.67 の盤面）、補助関数（関数とコマンドの拒否のコードの一致）、new_game からの合法な操作の列（3 つの規約集合。ピッピ人形は直接のコマンドで出し、U7 ですてる。トレーナーは U7-5c）
- 確かめていない経路:
  - `leave_lock` による拒否（エンジンの既存のテストだけ。U7 の盤面では確かめていない）
  - タケシのキュウコンの「ばける」と new_game からの列
  - TK1 の代表
- 固定するコミット: 最終の報告と実装状況に記録します（`9f5da53` からの作業ブランチ `claude/u7-5ab-board-ops`）
