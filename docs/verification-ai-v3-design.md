# 検証用 AI の V3（boundary・negative）の仕様と限定的な実装計画（設計だけ。実装していない）

V0〜V2（とその補完）のランダム・ルール・混合の通常の進行では届いていない API の境界を調べ、正常な拒否・既知の停止と、不具合の疑いを分けて記録するための仕様と計画です。
ゲームの合法性（エンジン・U7）と AI の戦略を分けたまま、境界の経路を選ぶ方針（boundary）と、不正な入力の試験（negative）と、異常の判定（D-6）を、それぞれ別の部品にします。

- 今回は調査・設計・文書化だけです。実装・対戦の実行・テスト・ビルドはしていません。確かめは文書とコードの静的な読み取りだけです
- 採用待ちの事項（9 章）は、まだ承認・実装されたものではありません（V3-1 を実装した: [verification-ai-v3-1.md](verification-ai-v3-1.md)。V3-2 はカツラの固定の到達例に絞って実装した: [verification-ai-v3-2.md](verification-ai-v3-2.md)。V3-3 以降と、使っていない判断は採用待ちのまま）
- 既存の文書: [仕様](verification-ai-design.md)・[実装計画](verification-ai-implementation-plan.md)・[V0](verification-ai-v0.md)・[V1](verification-ai-v1.md)・[V2](verification-ai-v2.md)・
  [V2 の補完](verification-ai-v2-repeat.md)

## 0. 基点

| 項目 | 値 |
|---|---|
| 基点 | `claude/verification-ai-v2-repeat` の `4c029f4`（V2 の補完の最後。実行に使った実装は `4083189`） |
| エンジン | `kyuura_engine` は `e26df79`（0.172.0）と同じ（`git diff --quiet e26df79 HEAD -- kyuura_engine` が差なし） |
| ブランチ | `claude/verification-ai-v3-design`（worktree `C:\dev\kyuura-engine-vai`） |
| 変えないもの | エンジン本体・GUI・renderer・カードデータ・固定デッキ・規約集合・識別の方式・既存の方策と記録 |

## 1. V0〜V2 の現状

### 1.1 実際の対戦で確かめた範囲（固定デッキ `hitmonchan-dewgong` 対 `venusaur-parasect`・既定の規約集合）

| 軸 | 届いたもの |
|---|---|
| 受理した操作の種類 | `place_starting`・`mulligan_draw`・`report_janken`・`play_basic`・`attach_energy`・`evolve`・`retreat`・`play_trainer`・`use_attack`・`end_turn`・`answer_decision`（`select_pokemon`）・`take_prize`・`promote_active`・`use_power`（エナジートランスの 3 段） |
| 入力の形 | `choose_option`・`choose_value`、`depends_on_stage`・`upstream_stages`/`after`・`options_from_stage`・`distinct_across_stages`・`total_units`、任意の段を省いた・使った |
| 結果 | 受理だけ（拒否・`refused`・check の invalid・`failed` は実際の対戦で 0） |
| 終わり方 | `game_over`、開始の時点の既知の停止 `halted_known`（`UNRESOLVED_MULLIGAN_COMPENSATION`。seed 11）、`limit_accepted`（rules-v1 の繰り返し。seed 13） |
| 範囲の外・作れない | 受理の前に未裁定で止める `play_trainer`（`unresolved_ruling`）、費用の不足のにげる（`total_units_unreachable`） |
| 再現 | 完全な記録の `replay_run`（R-A）、同じ seed の方策の再実行（R-C。同じプロセス・別のプロセス） |

### 1.2 単体のテストだけで確かめた範囲

`options_by_path`（構築した盤面と合成した段）、`uniform-tuple` の上限で戻す経路、入力を返さない候補（偽物の応答）、停止の分類（偽物の応答）、`failed`（テストの中で
`apply_command` を例外にした）、`no_progress`（偽物の check・submit）、各上限、混合の境界、反復の抑制（偽物の応答と小さな対戦）。

### 1.3 届いていない範囲

`use_stadium`・`remove_disguise`・`discard_from_play`・`reveal_face_down`・`check_face_up_deck`（表示だけ）・`start_sudden_death`、`options_by_path`、処理可能性 `unverified` の候補・
選べるもの、残り R-2〜R-5、入力を返さない候補、受理のあとの停止、エンジンの拒否・ホストの段の `refused`、決定の種類 `select_pokemon`・`promote_active`・`take_prize` のほか。

### 1.4 今の除外・選び直し・異常の候補・記録

- 範囲（`deep`）: 表示だけ・入力を返さない・処理可能性が `supported`・`may_stop_later` でない・同じ状態で入力を作れなかった候補を外す（範囲が空なら `unverified` も許す）
- 選び直し: 前に試した入力・入力を作れない・check の invalid・拒否・断り・（rules-v2 の）抑えた試みで、候補の選択からやり直す。同じ状態の拒否 16・選び直し 64
- rules-v2 の反復の抑制は戦略の選好です。seed 13 の 2 局で「同じ番の同じ操作の受理の最大が 2」だったのは**観測の結果**で、保証ではありません（ランダムの側は抑えず、代わりがない
  ときは送る設計）
- 異常の候補（V0〜V2）: `supported_rejected`・`check_valid_but_submit_refused`・`state_changed_on_rejection`・`update_after_rejection`・`accepted_without_refetch`・`update_numbers`・
  `update_observation_differs_from_view`・`inputs_refused_on_fresh_handle`。どれも実際の対戦では 0
- 記録で残せるもの: 完全な記録（エンジンに渡った操作。受理・拒否・`failed`）、操作の記録（check で止めた・`refused`・作れなかった・抑えた試みを含むすべての試み）、主体ごとの
  本人向けの記録、意味の列
- 残せないもの・未実装: ホストの段の `refused`・check の invalid は完全な記録に入らない（`replay_run` で確かめられない）、R-B（記録した U7 の要求を、取っ手を取り直して送り直す
  再実行）は未実装、取っ手は保存しない（`secrets` の値。再送しても意味がない）

## 2. 3 つの実行の目的

| 目的 | 対象 | 方策・選び方 | 数えるもの |
|---|---|---|---|
| `deep`（既存） | 対戦を深く進める | V0〜V2 の方策。範囲は 1.4 節 | 到達範囲・終わり方・異常の候補。既知の残件を避けたら除外として記録（既存） |
| `boundary`（新規） | API が示す、未確認（`unverified`）・停止しうる（`may_stop_later` で理由に先読み・受理のあとの評価なし）経路 | 範囲に `unverified` を加え、処理可能性の区分ごとに均等に選ぶ（10 章の案）。API が返さない入力を推測しない。表示だけ・入力を返さない候補は送らない（範囲の外のまま）。合法性を判定しない | 送った経路ごとの結果と D-6 の判定 |
| `negative`（新規） | API の上の正常な要求から、1 つの条件だけを変えた不正な入力 | 通常の方策とは別の部品（変異）と別の乱数。通常の進行の方策の乱数を使わない | 期待した拒否・断りのコード、状態・乱数・ログ・取っ手・配信の境界が変わらないこと |

- 表示だけの FU2（`check_face_up_deck`）への送信、実行できない区分（`unresolved_ruling`・`not_implemented`・`technical_limit`）の選べるものの送信、入力を返さない候補への
  送信は、`negative` として扱います（`boundary` の通常の操作に混ぜない）
- `boundary` は、対象を選ぶ方針を変えるだけです。範囲の外の候補は外したまま記録し、`unverified` の候補を API が示した入力の形で送ります

## 3. D-6: 異常の判定の基準（推奨案。採用待ち）

### 3.1 判定の区分

| 区分 | 意味 | 不具合の件数に入れるか |
|---|---|---|
| `expected` | 期待どおりの受理・拒否・断り（negative の期待したコードを含む） | 入れない |
| `normal_rejection` | API が受理を保証しない経路のエンジンの拒否（診断がコード表にある） | 入れない |
| `known_stop` | 停止・拒否の診断が既知の分類（`unresolved_ruling`・`unsupported`・`technical_limit`）で、コード表にある | 入れない |
| `known_limitation` | API の既知の残り（R-2〜R-5・表示だけ・入力を返さない） | 入れない |
| `suspect` | 3.2 節の条件。不具合の疑い | 入れる（疑いの件数。不具合と確定ではない） |
| `undetermined` | 公開の契約・記録から判定できない（3.3 節） | 入れない。別に数える |

既知の拒否・停止は `suspect` に足しません。知らない診断・知らない契約の値を既知として扱いません（`undetermined` か `suspect`）。判定は異常の判定の部品（`judge`）だけが行い、
方策・行動生成・境界の選び方は判定を読みません。

### 3.2 判定の表

API の受理の保証は `legal_actions.py` の `GUARANTEE_*` の `acceptance` の文から、次の 2 つに分けます（判定の部品の表として持ち、版ごとに照らす）。

- **前の確かめを満たす種類**（G-ACC）: `place_starting`（`GUARANTEE_PLACEMENT`。「エンジンの受理の条件を満たす」）、`mulligan_draw`（`GUARANTEE_MULLIGAN`）、`play_basic`・
  `attach_energy`・`evolve`・`retreat`（`GUARANTEE_TURN_ACTION`。「エンジンが受け付ける前の確かめを満たす」。うらのカードをおもてにする処理・コマンドの項目の確かめはエンジンの入口）、
  `remove_disguise`・`discard_from_play`・`reveal_face_down`（`GUARANTEE_BOARD_ACTION`）。どれも eligible の選べるもの（組）で作った入力に限る
- **受理を保証しない種類**（G-NONE）: `answer_decision`・`take_prize`・`promote_active`（`GUARANTEE_ANSWER`）、`report_janken`・`start_sudden_death`、`use_attack`（先読み）、`end_turn`、
  `play_trainer`・`use_stadium`・`use_power`（エンジンの受け付ける前・終わりの確かめ）、本人のうらのカードの特殊能力
- `supported` の保証の範囲（`GUARANTEE_TURN_ACTION` の `supported_scope`）: 前の確かめを満たし、受理のあとの反応・決定・停止のもとが場にないことを公開の情報で確かめた場合だけ。
  受理のあとの全分岐の完走の保証ではない（こんらんのコインなど）。check が valid であることは受理の保証ではない

| # | 場面 | 前提の保証 | 期待 | 正常・既知 | `suspect` の条件 | `undetermined` | 根拠 |
|---|---|---|---|---|---|---|---|
| 1 | check が valid → 同じ取っ手・同じ入力の submit がホストの段で `refused` | check と submit は同じ `_lookup` と `_input_problem` を使う | 同じ判定 | — | あいだに受理がない（状態のオブジェクトが同じ）のに `refused` | あいだに受理・ホストの差し替えがあった | `legal_actions.py:609`・`:653`、V0 の `check_valid_but_submit_refused` |
| 2 | G-ACC の eligible の入力で check が valid → エンジンの拒否 | 前の確かめと同じ関数・同じ順番 | 受理 | 理由に `face_down_reveal_not_evaluated` がある（おもてにしてから確かめる）・処理可能性が `unverified` | 分類 `invalid_input` の拒否。`supported` で分類が停止の 3 つの拒否 | `may_stop_later` で分類が停止の 3 つ（コード表にあれば `known_stop`） | `GUARANTEE_TURN_ACTION` ほか、U7-3 の文書 |
| 3 | G-NONE の入力のエンジンの拒否 | 保証しない | — | 診断がコード表にあれば `normal_rejection`（停止の 3 つなら `known_stop`） | 診断がコード表にない（`DIAGNOSTIC_UNMAPPED`）・知らない分類 | — | `GUARANTEE_ATTACK`・`GUARANTEE_TRAINER` ほか |
| 4 | `unverified` の入力の拒否・受理のあとの停止 | 送るまで分からない | — | コード表にある診断なら `normal_rejection`・`known_stop` | コード表にない診断 | 本当のカードによる結果（理由 `face_down_reveal_not_evaluated`）は、結果を記録するだけ | `_unverified_paths`・U7-5g |
| 5 | 受理のあとの停止（状態が `halted`） | `may_stop_later` は評価していない | — | 停止の公開の診断の分類が既知 → `known_stop` | 分類が既知でない（`halted_unclassified`） | `supported` の受理のあとの停止（`supported_scope` が完走を保証しないので判定しない。件数とは別に記録） | V0 の終わり方の分類 |
| 6 | `unresolved_ruling`・`not_implemented`・`technical_limit` の候補・選べるものを送る（negative） | 送る前に断る | `CANDIDATE_NOT_EXECUTABLE`（形の誤りは `CANDIDATE_INPUT_INVALID`） | 期待のコード → `expected` | エンジンに渡った（完全な記録に行が増えた）・受理された | — | `_input_problem`（`legal_actions.py:866`） |
| 7 | check の invalid・ホストの段の `refused`（negative の変異） | 期待のコードは変異ごとに決まる（4.2 節） | 期待のコード | `expected` | エンジンに渡った・状態が変わった・取っ手が失効した（受理のほかで） | 期待と違うコード（`_lookup` の順番の読み違いがありうる。両方を記録） | `_lookup`（`:485`）・`REFUSAL_MESSAGES` |
| 8 | deep・boundary で、API の段から作った入力の check の invalid・`refused` | 行動生成は契約だけから作る | valid | — | 道具か API のどちらかの食い違い（`suspect`。どちらかは決めない） | — | V0 の行動生成 |
| 9 | `failed`・入口の例外・状態の不整合 | 入口は例外を投げない | 起きない | — | `failed`（分類 `state_integrity` は重い疑い）・入口からの例外・`CLIENT_GAME_UNAVAILABLE`（`failed` のあと以外） | — | `adapter.py` の説明・`client_api.handle` |
| 10 | 拒否・断りのときの状態・乱数・ログ | 拒否は状態を変えない | 状態のオブジェクトと確認値（状態の sha256・乱数の指紋・ログの長さ・決定・停止）が同じ | — | どれかが変わった | — | `adapter.HostedGame`・`replay_record.checks`・V0 の `state_changed_on_rejection` |
| 11 | 拒否・断りの情報・更新が相手・観戦者へ | 拒否では更新を作らない | どの閲覧者の outbox も空 | — | だれかに更新が出た | — | `ClientHub._on_result`・V0 の `update_after_rejection` |
| 12 | 入力を返さない候補・決定 | 情報境界が未確認 | `withheld`・`INPUT_BOUNDARY_UNCONFIRMED` | `known_limitation`（R-3・R-5）。回答者が答えられず止まれば `input_unavailable` | — | 決定の種類が `DISCLOSURE_CONFIRMED_KINDS` にあっても、決める人に見えないカードが選べるものにあれば実行時に入力を返さない（`_answer_candidate` の確かめ）ので、種類だけでは判定しない。決定の種類は公開の応答にない（検証者の記録だけで照らす） | `_answer_candidate`（`legal_actions.py:812`） |
| 13 | 知らない契約の値・診断 | — | — | — | 診断がコード表にない | 知らない段の項目・値（`api_contract_unknown`。道具の更新が要るかもしれない） | V0 の 4.4 節 |
| 14 | 受理のあと | 取っ手はすべて失効、`refetch_required` が真 | 古い取っ手は `CANDIDATES_STALE` | — | 受理のあとに古い取っ手が通る・`refetch_required` が偽 | — | `ActionHost.invalidate`・`client_api._submit` |
| 15 | 拒否・断りのあと | 取っ手は失効しない（失効は受理・差し替え・取得の上限 4 だけ） | 同じ取っ手で元の正常な入力を送れる | — | 拒否・断りのあとに元の入力が `CANDIDATES_STALE` | 同じ主体が候補を 4 回より多く取り直した（上限による失効） | `ActionHost._issue`・`_purge`、`MAX_REVISIONS_PER_ACTOR` |

## 4. negative の仕様

### 4.1 作り方と安全性

- 変異の元は、その時点の主体の入口で取った正常な要求（`check` が valid だった取っ手・候補・入力）の写し。1 つの変異で変えるのは 1 つの条件だけ。変異の記録は
  `{"base": 元の要求の意味（意味の列の形）, "mutation": {"type": 種類, "where": 段・位置, "detail": …}, "expected": 期待のコード, "observed": 応答}` で、取っ手・番号そのものは
  記録の照合の値としてだけ残す（変異の再現に使わない）
- エンジンの状態を直接変えない（ホストの入口・`GameState` に手を入れない）。未知の入力を総当たりしない（変異の種類は 4.2 節の表だけ）
- 上限: 1 つの対戦で変異を試す位置は 12 まで、1 つの位置で同じ種類の変異は 1 回まで、1 つの対戦の変異の要求は 60 まで（案。9 章）
- 変異を試す位置と種類は、方策と別の乱数（種 `kyuura-vai-v3:negative:<seed>`）で決める。通常の進行の方策の乱数を使わない
- 変異のあと、同じ取っ手で元の正常な入力を送る（通常の進行の続き。3.2 節の 15 の確かめ）。変異を試さない場合と同じ操作の列になるはずなので、意味の列（変異の行を除く）を、
  変異のない同じ条件の記録と比べる（R-C）
- 失効を作る変異（受理のあとの古い取っ手）は、元の入力の受理のあとに試す（元の入力の取っ手を失効させない順番）。取得の上限（4）による失効は、通常の進行の取っ手を失わせるので、
  通常の対戦の中では試さない（既存のテストに任せる。4.3 節）
- 状態・乱数・ログの比べ（確認値）は判定の部品だけが行う。変異の部品・方策はそれを読まない

### 4.2 変異の種類（最初の単位の候補）

| id | 変異（1 条件） | 送る要求 | 期待 | 確かめの元 |
|---|---|---|---|---|
| N-SHAPE-UNKNOWN | 選ぶものの番号を、その候補にない番号にする | check・submit | `CANDIDATE_INPUT_INVALID`・`refetch_required` 偽 | `_input_problem` |
| N-SHAPE-DUP | 同じ選ぶものを 2 回にする（数の上限の中） | check・submit | `CANDIDATE_INPUT_INVALID` | 同上 |
| N-SHAPE-COUNT | 選ぶ数を `count.max + 1`・`count.min − 1` にする（意味のある場合だけ） | check・submit | `CANDIDATE_INPUT_INVALID` | 同上 |
| N-PATH-MIX | 依存する段で、前の段の別の選び方の参照（`options_by_choice` の別の鍵・`after` の違う番号・`options_by_path` の別の鍵）の選ぶものにかえる | check・submit | `CANDIDATE_INPUT_INVALID` | `_turn_input_problem`・`_power_input_problem`・`_path_stage_problems` |
| N-NONEXEC | API が実行できない区分と示した選べるもの（`eligible` 偽・`unresolved_ruling` など）にかえる・その候補を送る | check・submit | `CANDIDATE_NOT_EXECUTABLE` | `_input_problem` |
| N-WRONG-ACTOR | 相手のプレイヤーの入口から、この取っ手で送る | check・submit | `CANDIDATES_WRONG_ACTOR`・`refetch_required` 真 | `_lookup` |
| N-STALE-AFTER-ACCEPT | 元の入力の受理のあとに、受理の前の取っ手と入力を送る | submit | `CANDIDATES_STALE`・`refetch_required` 真 | `ActionHost.invalidate` |
| N-RECOVER | 上の変異のあとに、同じ取っ手で元の入力を送る（通常の進行） | submit | 変異のない列と同じ結果 | `_issue`・`_purge` |

### 4.3 既存のテストで十分なもの（V3 の AI の実行の対象にしない）

| 条件 | 既存のテスト |
|---|---|
| 封筒・項目の誤り（`CLIENT_FIELD_UNKNOWN`・`CLIENT_FIELD_INVALID`・知らない要求） | `tests/test_client_api.py` の `test_unknown_requests_are_refused_safely` |
| 別の対戦の取っ手（`CANDIDATES_WRONG_GAME`） | U7-1〜U7-5e の各テスト |
| 取得の上限による失効（`MAX_REVISIONS_PER_ACTOR`） | `tests/test_legal_actions_u7_1.py` |
| 表示だけの FU2 の送信（構築した盤面） | `tests/test_legal_actions_u7_5f.py`（`CANDIDATE_NOT_EXECUTABLE`・形の誤り・更新なし） |
| 入力を返さない候補への送信 | `tests/test_legal_actions_u7_1.py`・`u7_5ab.py`・`u7_5g_face_down_power.py` |
| 依存する段の混ぜた入力（構築した盤面） | `tests/test_legal_actions_u7_5e.py` の `test_mixed_upstream_and_stale_downstream_are_rejected`・`u7_5g_energy2.py` の `test_mixed_and_broken_inputs_are_rejected` |

AI の実行で試す意味があるのは、通常の進行で届いた多くの位置（構築でない盤面）で、同じ変異を、状態・乱数・ログ・配信の境界の照合と、変異のあとに元の入力で続けられることの
照合と組で行うことです。

### 4.4 記録と再現

- 変異の要求はホストの段で断られ、エンジンに渡らないので、完全な記録（`ReplayCollector`）に行がありません。変異の記録は操作の記録（`trace.jsonl` の `type: "negative"` の行）と、
  判定の記録（`judge.jsonl`）に置きます
- **R-A**（完全な記録の `replay_run`）: 通常の進行の操作（受理・エンジンの拒否）を確かめる。変異は確かめない
- **R-C**（同じ seed・方策・変異の種での再実行）: 変異の位置・種類・期待・観測と通常の進行の列を、意味で比べる（取っ手・番号・`operation_id` は比べない）。変異のない同じ条件の記録
  （既存の V1 の局など）の意味の列とも比べる（変異が通常の進行に影響しないことの確かめ）
- **R-B**（記録した U7 の要求を、取っ手を取り直して意味で探して送り直す）: V3 の最初の単位では作らない（後の段。8 章）
- 取っ手などの一時的な値をそのまま再送して再現しない

## 5. boundary の仕様

- 範囲: `deep` の範囲に `unverified` の候補・選べるものを加える（表示だけ・入力を返さない・実行できない区分は外したまま）
- 選び方（`boundary-class-uniform`。案）: 範囲の中にある処理可能性の区分（`supported`・`may_stop_later`・`unverified`）から均等に 1 つ、その区分の候補から均等に 1 つ。入力は
  uniform-stage。区分の中で選ぶのは方策の乱数（方策の種の導き方は V0 と同じ形で、名前を変える）。合法性・カードによる判定はしない
- 記録: 選んだ区分・理由、送った経路の結果、D-6 の判定。`unverified_paths` の理由ごとの到達
- 届かない場合: 固定の条件で `unverified` が示されなければ、そのことを到達範囲として記録する（探索はしない）

## 6. 構成（再利用と追加）

| 部品 | 再利用 | 追加 |
|---|---|---|
| 行動生成 `actions` | そのまま（boundary の範囲は `FALLBACK_PROCESSABILITY` を常に使う） | なし |
| 方策 `policies` | 既存の方策は変えない | `BoundaryPolicy`（区分ごとの均等。boundary の選び方だけ） |
| 変異 `negative.py`（新規） | — | 正常な要求の写しから 4.2 節の変異を作る純粋な関数（JSON だけを読む。`kyuura_engine` を import しない）と、期待のコード |
| 判定 `judge.py`（新規） | V0 の異常の候補の判定を移して表にする | 3.2 節の表。入力は API の応答と、検証者の値（確認値・更新の有無・完全な記録の行の増減）。方策に渡さない |
| ランナー `runner` | 進行・上限・記録・計測・エピソード | 目的（`deep`・`boundary`・`negative`）の設定、check が valid のあと submit の前に変異を試す接点（negative の位置のときだけ）、判定の呼び出し |
| 記録 `records`・`metrics` | 意味の列・対応・マニフェスト・計測 | 変異の行・判定の集計（区分ごとに数える。`suspect` と既知を足さない） |
| 入口 `run_v3.py`（新規） | 計画を先に書く・1 局ずつ・予算 | 目的ごとの実行と比べ |

大きな汎用の試験の基盤は作りません。V0〜V2 の通常の動作（`deep`・既存の方策・既存の意味の列）は変えません（既存の意味の列の sha256 のテストを使う）。

## 7. 最初の実装の単位（推奨と優先順位）

| 順 | 単位 | 確かめる主張 | 到達方法 | 固定の条件 | 変える入力・変えない条件 | 期待 | 証跡 | 既知の制限 |
|---|---|---|---|---|---|---|---|---|
| 1 | V3-1 negative（通常の進行の中） | 通常の進行で届いた位置で、1 条件の不正な入力がホストの段で期待のコードで断られ、状態・乱数・ログ・取っ手・配信が変わらず、同じ取っ手で元の入力を続けられる | new_game から uniform-stage の通常の進行（公開の API だけ） | 固定デッキ `hitmonchan-dewgong` 対 `venusaur-parasect`・既定の規約集合・seed 12 と 13（V1 の stage-s12・s13 と同じ条件。どちらも `game_over`） | 4.2 節の N-SHAPE-*・N-PATH-MIX（`options_by_choice`・`after`。届いた位置だけ）・N-NONEXEC（未裁定の `play_trainer`。V1 で 1 局 57〜68 回の取得に示された）・N-WRONG-ACTOR・N-STALE-AFTER-ACCEPT・N-RECOVER。通常の進行の方策・seed・上限は変えない | 3.2 節の 6・7・10・11・14・15 の `expected`。意味の列（変異の行を除く）が V1 の保存した記録と一致 | 変異の行・判定の記録・確認値の比べ・R-A・R-C の比べ | `options_by_path` は届かない（このデッキの組にカツラがない）。FU2・入力を返さない候補は届かない |
| 2 | V3-2 boundary と経路の混ぜ方（試験用のデッキ） | `options_by_path` に実際の進行で届き、別の経路の選ぶものを混ぜた入力が断られる。boundary の選び方で `unverified` が示されるかを記録する | new_game から（公開の API だけ）。ただしデッキは `tests/` に定義済みの試験用のデッキ（固定デッキではない） | `tests/test_legal_actions_u7_5g_energy2.py` の `BLAINE_DECK`・`BLAINE_SEED = 1`・既定の規約集合（既存の合法な到達例） | N-PATH-MIX（`options_by_path` の別の鍵）。boundary は `boundary-class-uniform` | 3.2 節の 7。`options_by_path` の到達 | 同上 | 試験用のデッキで、固定デッキの対戦の到達とは別に数える。`unverified` は届かない見込み（届かなければそう記録） |
| 3 | V3-3 構築した盤面の境界（別の分類） | `unverified`（本人のうらのカードの特殊能力・PT-5e）・FU2 を、構築した盤面から U7 の入口で送った結果の判定 | `ClientHub.from_state`（構築した盤面）。通常の進行からの到達とは扱わない | 既存のテストの盤面（`u7_5g_face_down_power`・`u7_5c`・`u7_5f` の盤面の関数） | boundary の 1 操作と、N-NONEXEC（FU2） | 3.2 節の 4・6 | 分類 `constructed` で別に保存 | 構築した盤面は通常の進行の到達ではない |
| 後 | V3-4 小さな探索（計画だけ） | new_game から `unverified`・うらのカード・PT-5e の経路に届く固定の条件を見つける | 試験用のデッキ（マチスの秘策・カツラのクイズなど）で、seed 20 個まで・1 局 300 操作まで・合計 10 分まで（案） | 未確定 | — | — | — | 実行は承認のあと。見つけた seed は固定の条件として記録し、結果で差し替えない |
| 後 | R-B の実装 | 記録した U7 の要求を、取っ手を取り直して意味で探し、送り直す | — | — | — | — | — | V3-1〜V3-3 のあと |

最初に実装するのは V3-1 だけを推奨します（固定デッキの既存の条件だけで、新しい盤面・デッキ・探索が要らない）。V3-2・V3-3 は V3-1 のあとで、それぞれ承認を受けてから始めます。

## 8. 段階ごとの計画

### V3-1: negative（通常の進行の中）

| 項目 | 内容 |
|---|---|
| 変更の範囲 | 新規 `negative.py`・`judge.py`・`run_v3.py`、ランナーの変異の接点と目的の設定、記録の変異の行。既存の方策・行動生成は変えない |
| 単体・接続のテスト | 小さな JSON の例で各変異が 1 条件だけを変えること・期待のコード、判定の表の各行（偽物の応答）、変異の部品が `kyuura_engine` を import しない・方策の乱数を使わない、変異のある実行の意味の列（変異の行を除く）が変異のない実行と同じ（小さな上限の対戦）、確認値の比べと更新の確かめ、既存の 4 つの方策の意味の列の sha256（V2 の補完のテスト）が変わらない |
| 固定の実行 | 2 局（seed 12・13、uniform-stage、変異あり）。1 局の上限は V0〜V2 と同じ。変異の位置 12・1 局の変異の要求 60 まで。全体の予算 10 分 |
| 合格の条件 | 変異の判定がすべて `expected`（`suspect` が出ればそのまま記録する。合格・不合格は「道具が正しく記録したか」で決め、`suspect` の有無で決めない）、`replay_run` が期待どおり、意味の列（変異の行を除く）が V1 の保存した記録と一致 |
| 停止の条件 | 道具の例外・`failed` は止めて記録。上限で止まれば上限の分類 |
| 証跡 | `C:/dev/kyuura-engine-verification-vai/verifier/runs/v3-1-…/`（計画・各局の完全な記録・操作の記録・変異と判定の記録・確認値の比べ・R-A・R-C の比べ）、`public/` には判定の区分ごとの数だけ。実行ごとの `manifest`・`sha256`。過去の記録は上書きしない |
| 後へ残すもの | `options_by_path`・`unverified`・FU2・入力を返さない候補（V3-2・V3-3）、R-B |

### V3-2: boundary と経路の混ぜ方

| 項目 | 内容 |
|---|---|
| 変更の範囲 | `BoundaryPolicy`、boundary の範囲の設定、試験用のデッキを読む入口（`tests/` の定義を読むか写すかは採用待ち） |
| テスト | 区分ごとの均等の選び方（固定の種での具体的な選択）、範囲に表示だけ・入力を返さない・実行できない区分が入らないこと、既存の方策の不変 |
| 固定の実行 | 2 局（`BLAINE_DECK`・seed 1・既定の規約集合で、boundary 1 局・deep（uniform-tuple）と変異 1 局）。予算 10 分 |
| 合格の条件 | 到達と判定の記録・`replay_run`・別のプロセスでの再現 1 回 |

### V3-3: 構築した盤面の境界

| 項目 | 内容 |
|---|---|
| 変更の範囲 | 構築した盤面を `ClientHub.from_state` で包む入口（分類 `constructed`）。盤面は既存のテストの関数を使い、新しい盤面を作らない |
| テスト・実行 | 盤面ごとに boundary の 1 操作と FU2 の N-NONEXEC。盤面 3 つまで |
| 合格の条件 | 判定の記録。通常の進行の到達の数に足さない |

## 9. 採用の判断が要る事項

| id | 事項 | 案 |
|---|---|---|
| D-V3-1 | D-6 の判定の区分と表（3 章） | 推奨案のとおり。`supported` の受理のあとの停止は `undetermined`（件数とは別に記録） |
| D-V3-2 | 最初の単位 | V3-1 だけ（7 章） |
| D-V3-3 | negative の上限 | 1 局の変異の位置 12・同じ位置の同じ種類 1 回・1 局の要求 60・全体の予算 10 分 |
| D-V3-4 | negative の比べの基準 | V1 の保存した stage-s12・s13 の記録（変異のない同じ条件）と意味の列を比べる（変異のない実行をやり直さない） |
| D-V3-5 | boundary の選び方 | 区分ごとの均等（`boundary-class-uniform`）。範囲に `unverified` を加える |
| D-V3-6 | 試験用のデッキ（`tests/` の `BLAINE_DECK` など）を固定の条件に使うこと | V3-2 で使う。固定デッキの対戦とは別に数える。`tests/` から読むか、道具に写すか |
| D-V3-7 | 構築した盤面の分類 | V3-3 で別の分類（`constructed`）にする |
| D-V3-8 | 小さな探索（V3-4） | 計画だけ。実行は seed 20 個・1 局 300 操作・合計 10 分までで、別の承認 |
| D-V3-9 | R-B の実装の時期 | V3-1〜V3-3 のあと |
| D-V3-10 | V0 の異常の候補を `judge` へ移すこと | 判定の名前と区分を 3.2 節の表に合わせる。既存の記録の項目名は変えない（新しい記録にだけ判定の区分を加える） |

既存の保留（D-12 の広いデッキと規約集合、CN-1 のエンジンの側、きぜつと終局の条件の数え方、方策の追加の調整・番ごとの種類別の回数の制限・にげるの選び直しの効率）は、
今回の範囲の外のままです。

## 10. 実行の制約

将来の実行も、単一のプロセス・上限つきで、ほかのプロセスを探す・終了させる処理を持ちません。禁止中・未確認の後始末の道具は使いません。全体のテスト・GUI・E2E・lockstep・
状態の監査・大量の対戦は、この計画の範囲の外です。証跡は `C:/dev/kyuura-engine-verification-vai/` の新しい実行のディレクトリに置き（`verifier/` に完全な記録・本人向けの記録・
詳しい操作の記録、`public/` に確かめた非機密の集計だけ）、実行ごとの `manifest`・`sha256` を持ち、過去の記録を上書きしません。
