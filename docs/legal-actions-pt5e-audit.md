# PT-5e（山札から引いて試すトレーナー）の監査（文書だけ。エンジンの版は 0.175.0 のまま）

追記（v0.176）: 利用者が 6 章の案 1 を採用し、v0.176.0 で実装した（9 章）。1〜8 章は監査のときの記録（版 0.175.0・基点 `62fff09`）のまま。

候補・inputs・check で安全に判定できる範囲と、実行時まで未確認にすべき範囲を分けるための監査です。補完の実装・テスト・ビルド・対戦の実行はしていません。確認はコード・文書・保存済みの証跡の読み取りと、静的な参照の整合の確かめだけです（モジュールの読み込み・テストの実行もしていない）。

## 0. 基点と版

| 項目 | 値 |
|---|---|
| 基点（コード） | `62fff09`（`claude/vai-u-r3a-follow`。U-R3a の実装 `81e9e99`・文書 `43debdd` と、検証用 AI の追従 `fc1aa51`・`62fff09` を含む公開コミット。`origin/main`（`88ad4d9`）には入っていない） |
| 作業ブランチ | `claude/pt-5e-audit`（専用の worktree `C:/dev/kyuura-engine-vai`。利用者の `C:/dev/kyuura-engine` は main のまま触っていない） |
| パッケージの版 | 0.175.0（変えていない） |
| 読んだコード | `kyuura_engine/legal_actions.py`・`engine.py`・`effects.py`・`faceup.py`・`zones.py`・`observation.py`・`state.py`・`heights.py`・`snapshot.py`（どれも基点のまま） |
| 参照した文書 | `legal-actions-u7-5-design.md`（PT-5e の行）・`legal-actions-u7-5c.md`（3・4 章）・`legal-actions-u7-5fg-spec.md`（4 章）・`legal-actions-r5-audit.md`・`verification-ai-inventory.md`（7 章）・`chaos-gym-borrow-t-f1.md`（基点の版） |

行番号は基点のコードのものです。

## 1. 対象の確定

### 1.1 実装・登録・カード

`legal_actions.PLAYABLE_NOT_EVALUATED`（`legal_actions.py:1472`）の 5 つの型名です。登録はカード id ごとで（`effects.py` の `trainer_entry`。別名・再録の流用はない）、5 つの型に 6 枚のカードが登録されています。この 5 つの型を継承した型はありません（`_use_condition_owner` は継承をたどるが、該当なし）。カードデータ（`kyuura_cards.json`）でこの 6 つの名前を持つカードも 6 枚だけです。

| 型（`check_playable` の行） | カード id（登録の行） | 名前 | 使うための条件の要素 |
|---|---|---|---|
| `BlainesQuiz`（`effects.py:22420`） | `PMCG6-082`（28467） | カツラのクイズ その3 | 手札のワザを持つポケモン（このカードを除く）がなければ QZ1。そのあと、おもての山札の確かめ（正解・不正解の両方の引き方） |
| `BlainesHeightQuiz`（49162） | `GD5-016`（49242） | カツラのクイズ その1 | 手札のポケモン（このカードを除く）がなければ QZ1。全部が図鑑番号・身長なしなら `UNSUPPORTED_QUIZ_HEIGHT_*`。そのあと、おもての山札の確かめ（両方の引き方） |
| `SetAsideGuessKindQuiz`（32160） | `GD5-017`（32719。`kinds="card_kind"`） | カツラのクイズ その2 | このカードを除く手札がなければ FC1（`UNRESOLVED_STATED_CARDS_SHORT`。Unsupported）。そのあと、おもての山札の確かめ |
| 同上 | `neo4-105`（32722。`kinds="personality"`） | ポケモン性格判定 | 手札に進化カードがなければ `NO_EVOLUTION_CARD_IN_HAND`（Illegal。印刷の「使うことはできない」）。そのあと、おもての山札の確かめ |
| `GuessOpponentPrizeKind`（32231） | `neo1-080`（32721） | カードめくりゲーム | うらの相手のサイドがなければ FC1。そのあと、おもての山札の確かめ（正解のときに使ったプレイヤーが 2 枚引く方だけ） |
| `SwapPleaseTrainer`（49362） | `PR1-027`（49442） | とりかえっこプリーズ | このカードを除く自分の手札が 0 枚なら `NO_OTHER_CARDS_IN_HAND`、相手の手札が 0 枚なら `OPPONENT_HAND_EMPTY`（どちらも Illegal）。そのあと、おもての山札の確かめ（オーケーでないときに 2 枚引く方） |

同じ型でも、`SetAsideGuessKindQuiz` は 2 枚で条件が違います（その2 は Unsupported の FC1、性格判定は Illegal）。以下ではカードごとに分けます。

### 1.2 PT-5e として残した理由

- U7-5 の設計の静的な走査は、状態の複製の上で試す 11 の実装を見つけました（`scan.check_playable.trials`）
- U7-5c（v0.169）は、試すのが場の処理だけの 6 つを読む値までたどって候補で呼ぶことにしました（`PLAYABLE_BOARD_TRIALS`）
- 残る 5 つは複製の上で実際の山札から引くため、読む値をたどっていませんでした
  - v0.135・v0.136 の記録（「結果は山札の枚数とおもての枚数だけで決まる」）はありましたが、U7-5c では確かめ直していません（`legal-actions-u7-5c.md` 4.2 節）
  - そのため候補では呼ばず、`unverified` にしました
- R-5 の監査で「既知の未裁定・未実装」から「監査が未完了」へ移しました（`verification-ai-inventory.md` 7 章）

### 1.3 今の扱い（基点のコード）

| 経路 | 確かめること |
|---|---|
| 候補（`_trainer_candidate`。`legal_actions.py:1493`） | `check_play_trainer(..., use_condition=False)` を呼ぶ（`_use_condition_evaluated` が偽。1504〜1505 行）<br>番・手札・トレーナーであること・使用の禁止・登録・リムーブ禁止ジムの追加の条件・MG1 は確かめる。使うための条件だけを省く<br>結果は ILLEGAL なら出さない、STOP なら実行できない区分、それ以外は `unverified`（理由 `use_condition_not_evaluated`・`preflight_not_evaluated`・`continuation_not_evaluated`） |
| inputs | 本人の手札の並びの選べるもの（`input_disclosure: "confirmed"`） |
| check（`_check`。622 行） | `_input_problem` の構造の確かめだけ（候補の値・executable）。条件は呼ばない |
| submit（`_submit`。666 行） | 構造の確かめのあと `PlayTrainer` をエンジンへ渡す<br>エンジンは `_play_trainer` → `check_play_trainer(use_condition=True)` で使うための条件を確かめる<br>拒否は送った人にだけ返り、取っ手は失効しない（`test_unverified_card_rejected_by_engine_privately`） |
| 直接のコマンド（`apply_command`） | submit と同じ `_play_trainer`（`use_condition` はいつも真） |

- `unverified` の意味: 使えるかを候補が示していない。選べるものの数・並びは条件の結果によらない
- `input_disclosure`: 入力（手札のカード）は本人に公開してよい値なので confirmed

### 1.4 未裁定と監査未完了の違い

- 条件の中には、既知の止め方があります
  - 研究上の未解決（`unresolved_ruling`）: QZ1・FC1・FU3（`UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE`）
  - エンジンの未対応（`unsupported`）: `UNSUPPORTED_QUIZ_HEIGHT_WITHOUT_DEX`・`UNSUPPORTED_QUIZ_HEIGHT_NOT_AVAILABLE`
  - 錯乱ジムの借用の CH1
- これらは「その場面では使えない・止める」というゲーム上・実装上の結論で、エンジンはいつも同じ結論を出します
- PT-5e は、合法手 API が条件を呼んでよいか（読む値が情報境界を守るか）を確かめていない、という API 側の監査の未完了です
  - 条件の中の未裁定を解くことではありません
  - 監査が終わっても、条件の中の未裁定・未対応は残ります

## 2. 読み取りと副作用の追跡

### 2.1 呼び出しの閉包（`check_playable` から）

| 入口 | 呼び出し先（この順） |
|---|---|
| `BlainesQuiz.check_playable` | `quiz_candidates`（22340。手札・`card_def`・`attacks`）→ `face_up_draw_stop` → `quiz_draw_outcome_stop`（22360） |
| `BlainesHeightQuiz.check_playable` | `quiz_height_candidates`（49110）→ `quiz_height_blocked`（49116）→ `heights.card_height`（`heights.py:169`。`definition.dex` と同梱の `species_heights.json`）→ `quiz_draw_outcome_stop` |
| `SetAsideGuessKindQuiz.check_playable` | `self.candidates`（32154。手札・`is_evolution_pokemon`）→ `quiz_draw_outcome_stop` |
| `GuessOpponentPrizeKind.check_playable` | `self.positions`（32227。相手の `prizes` と `face_up_prizes`）→ `quiz_draw_outcome_stop(outcomes=((user, 2), (user, 0)))` |
| `SwapPleaseTrainer.check_playable` | 自分・相手の `hand` → `self.face_up_draw_stop`（49372）→ `state.clone` → `_draw_up_to` → `faceup.command_problem` |
| `quiz_draw_outcome_stop`（22360） | `state.face_up_deck` が空なら None。あれば結果ごとに次をする<br>・`state.clone`（`state.py:2617`）<br>・`_draw_up_to`（`effects.py:17827`）→ `zones.draw_cards`（`zones.py:455`）→ `faceup.require_draw_through_face_up`（`faceup.py:140`）→ `face_up_below_top`（116）<br>・`faceup.command_problem`（226）→ `face_up_in_deck`（92）・`place_of`（174）・`_first_moves`（213） |

- 動的な呼び出しは、同じ型のメソッド（`self.face_up_draw_stop`・`self.candidates`・`self.positions`）だけで、名前で解決できます
- コールバック・登録の参照・状態のメソッドによる分岐はありません
- `card_height` の `load_species_heights` は同梱の固定のデータを読むだけです（`lru_cache`）
- 閉包はこの表で閉じます。未確定の呼び出し先はありません（静的な読み）

### 2.2 読む情報（主体ごとの見え方つき）

| 情報 | 読む実装 | 本人（使うプレイヤー）に見えるか | 判定の結果が依存するか |
|---|---|---|---|
| 本人の手札（カードと並び） | 6 枚すべて（候補の数・種類・図鑑番号） | 見える（`observation.py:541`） | 依存する（本人の知識） |
| 本人の山札の内容と順序 | `quiz_draw_outcome_stop`・Swap の試行で、複製の上の `deck[:count]` を引く | 枚数・おもての枚数・自分のおもての位置と id（`known_face_up`）だけ見える | 依存しない（2.3 節） |
| 相手の山札の内容と順序 | クイズ 4 枚の試行（不正解・正解の両方。相手が引く方） | 枚数・おもての枚数・いちばん上のおもてだけ見える | 依存しない（2.3 節） |
| サイドと山札の配分 | 読まない（`GuessOpponentPrizeKind` は相手のサイドの位置とおもての記録だけ） | — | — |
| 相手のサイドの内容 | `positions` が uid を `face_up_prizes` と照らす | 枚数とおもての位置・カードだけ見える（`observation.py:546〜547`） | 依存しない（空かどうかは「枚数 > おもての枚数」） |
| 相手の手札 | Swap が枚数（空か）だけを読む | 枚数は見える（`observation.py:540`） | 枚数だけ |
| 公開の場・カードの定義 | `card_def`（手札のカードの印刷の定義）・図鑑番号・同梱の身長 | 見える | 依存する（公開・本人の知識） |
| 公開済みの山札の情報（おもての山札） | `state.face_up_deck`（空か・どのカードがおもてか） | 枚数・いちばん上は全員、位置は持ち主 | 依存するのは枚数だけ（2.3 節） |
| 本人が記憶・認識している情報 | 読まない（ログ・記憶の関数を呼ばない） | — | — |
| 乱数 | 読まない（`draw_cards` は乱数を使わない。複製は `copy_rng` で写すだけ） | — | — |
| 決定・ログ・停止・状態の変更 | 複製の上で手札・山札・ログを変える（元の状態は変えない。2.4 節） | — | — |

### 2.3 秘密を読むが、判定の結果は依存しないことの根拠

`quiz_draw_outcome_stop` と `SwapPleaseTrainer.face_up_draw_stop` は、複製の上で実際の山札の上のカード（uid）を引きます。読みはありますが、返す値（None か (コード, 理由)）は次の公開の値だけで決まります。

1. `state.face_up_deck` が空か
   - 空でないのは、だれかの山札におもてのカードがあるとき
   - フラッシュのログと観測の `face_up_count` で全員に見えます
2. `draw_cards` の中の `require_draw_through_face_up` が止めるのは、`count >= 2` で、上から 2 枚目〜`count` 枚目におもてのカードがあるときです
   - `count` は `min(引く枚数, 山札の枚数)` で、山札の枚数は公開です
   - おもてのカードは、いつも山札の上から続く並びです（不変条件 `faceup.prefix_problems`。`engine.check_invariants` が `engine.py:3065` で確かめる）
   - なので、この条件は「`count >= 2` かつ その山札のおもての枚数が 2 以上」と同じです
   - 止めたときの理由の文は、プレイヤーの番号と `count` だけを書きます
3. 止めなかったときの `command_problem(state, trial)` を、引いた山札について見ます
   - 引いたおもてのカードはいちばん上（位置 0）だけで、手札へ移っても受け付けます
   - 残りの並びは変わりません。引かない側の山札は変わりません
   - なので、いつも None です（`shuffle`・見るログ・決定は試しの中に出ない）
4. 理由の文に、カードの id・名前は入りません

- 前提: 状態が `check_invariants` を満たすこと
  - スナップショットの復元は、復元のあとに `check_invariants` で確かめます（`snapshot.py:447`・969）
  - `ClientHub.from_state`（検証者・テストの構築盤面の入口）が不変条件を確かめるかは確かめていません（未確認。5.3 節）
- 既存テストの主張（今回は実行していない）
  - `tests/test_quiz_answer_rejection_v0_135.py` の `ShapeMatrixTest.test_the_check_reads_only_public_counts`: 4 つのクイズ（その1・その2・その3・性格判定）で、枚数とおもての枚数の組から止めるかが決まる
  - 同じファイルの `TwinRejectionTest.test_reason_does_not_depend_on_cards_hidden_from_the_user`: 自分の山札の深い所・相手の山札・相手の手札だけが違う双子で、使う宣言の受理・拒否と理由が同じ
  - `tests/test_card_flip_answer_rejection_v0_136.py` の `test_the_check_reads_only_public_counts`・`test_check_does_not_read_cards_hidden_from_the_user`: カードめくりゲームで同じ主張
  - とりかえっこプリーズは、深いおもての山札で止めるテスト（`test_trade_please_v0_130.py` の `test_deep_face_up_deck_stops_before_use`）だけです。秘密だけを変えた双子のテストはありません
- どの既存テストも `apply_command` の入口での主張で、候補・inputs・check の入口では確かめていません（候補は今は呼ばないため）

### 2.4 副作用

- `check_playable` の 6 つは、元の状態を変えません
  - 試行は `state.clone()` の上です。`players` の手札・山札の配列を写します
  - ログは不変のタプルを付け替えます（`state.py:2751`）。おもての山札の記録もタプルです
  - 乱数は `copy_rng` で写すだけで、引く処理は乱数を使いません
- 決定を出さず、ログ・停止を元の状態に加えません
- 例外は `IllegalActionError`・`UnsupportedError` だけです
  - `RuntimeError` は `draw_cards` の枚数の範囲外だけですが、`_draw_up_to` が `min` で丸めるので起こりません
  - `SwapPleaseTrainer.face_up_draw_stop` は `draw_cards` の FU3 を捕まえずに上げます。クイズの共通関数はコードと理由に変えて返します。どちらも、外から見えるのは同じ `UnsupportedError`（FU3）です
- 「元の状態を変えない」ことは、安全の根拠にしていません。根拠は 2.3 節の、返す値の依存です

## 3. 候補の取得からの情報境界

使う前（候補の取得）に分かる情報と、使ったあとに公開される情報を分けます。

| 候補側の値 | 使うための条件を呼んだときに変わりうるもの | 決める情報 |
|---|---|---|
| 候補の有無・件数・順序 | Illegal（`NO_OTHER_CARDS_IN_HAND`・`OPPONENT_HAND_EMPTY`・`NO_EVOLUTION_CARD_IN_HAND`）のカードを選べるものから外す。全部が外れれば `play_trainer` の候補がなくなり、候補の番号がずれる | 本人の手札、相手の手札の枚数 |
| eligible・processability | Unsupported（QZ1・FC1・FU3・`UNSUPPORTED_QUIZ_HEIGHT_*`）は eligible 偽で、`ruling_unresolved` か `not_implemented`（`_stop_processability`。811 行）<br>通れば `may_stop_later` | 本人の手札、山札の枚数・おもての枚数（公開）、相手のサイドの枚数とおもての数（公開）、同梱の身長のデータ |
| 理由・診断 | `_probe`（937 行）はコードだけを受け取り、理由の文を候補に出さない。候補の理由は `stops_*` の区分か、`preflight_not_evaluated`・`continuation_not_evaluated` | 上と同じ |
| 入力の選択肢・件数・制約 | 選べるもの = 外されなかった手札のカード（本人の手札の並び）。1 段・1 枚は変わらない | 上と同じ |
| check の結果 | 実行できない選べるものは `CANDIDATE_NOT_EXECUTABLE`（エンジンを呼ばない） | 上と同じ |
| 例外・停止の違い | 候補の作成は例外を `_probe` で区分に変えるだけ | 上と同じ |

- 本人の山札の順序・サイドとの配分を、本人が知っているとは仮定していません
  - 6 つの条件は配分を読みません。山札の順序は 2.3 節の理由で結果に効きません
- 持ち主の知識の関数（`deck_target_lower_bound` など。U7-5c の A-own）は、この 6 つでは使われていません。代わりに要るのは、2.3 節の不変条件という前提です
- 方策に完全な状態を渡すことは前提にしていません
  - ここで言う「本人の知識」は、本人の観測（`observe(state, actor)`）に出る値です（手札のカード・山札の枚数・おもての枚数・`known_face_up`・相手の手札の枚数・サイドの枚数とおもて）
  - 検証者は監査のために完全な状態を読みますが、公開 API が使ってよい情報は観測の範囲だけです
- 使ったあとに公開される情報（置いたカード・正誤・引いたカード・おもてにしたサイド・交換したカード）は、受理のあとの決定と処理で出ます。候補側へ先回りさせません

## 4. 分類

| 実装・条件 | 区分 | 根拠 |
|---|---|---|
| その3（`PMCG6-082`）: 手札のワザを持つポケモンの有無（QZ1） | A | 本人の手札と印刷の定義だけ |
| その3: おもての山札の確かめ（両方の引き方） | A | 2.3 節（公開の枚数だけ。内部の読みは結果に効かない） |
| その1（`GD5-016`）: 手札のポケモンの有無（QZ1）・全部が身長なし（`UNSUPPORTED_QUIZ_HEIGHT_*`） | A | 本人の手札・図鑑番号・同梱のデータ |
| その1: おもての山札の確かめ | A | 2.3 節 |
| その2（`GD5-017`）: このカードを除く手札の有無（FC1） | A | 本人の手札の枚数 |
| その2: おもての山札の確かめ | A | 2.3 節 |
| 性格判定（`neo4-105`）: 手札の進化カードの有無（Illegal） | A | 本人の手札と印刷の定義 |
| 性格判定: おもての山札の確かめ | A | 2.3 節 |
| カードめくりゲーム（`neo1-080`）: うらの相手のサイドの有無（FC1） | A | 相手のサイドの枚数とおもての数（公開） |
| カードめくりゲーム: おもての山札の確かめ（使ったプレイヤーだけ） | A | 2.3 節 |
| とりかえっこプリーズ（`PR1-027`）: 自分のほかの手札・相手の手札の枚数（Illegal） | A | 本人の手札、相手の手札の枚数（公開） |
| とりかえっこプリーズ: おもての山札の確かめ（オーケーでないときの 2 枚） | A | 2.3 節。秘密だけの双子の既存テストはない（7 章で足す） |
| 6 枚の受理の前の先読み（`_trainer_reaction_decline_check`・`_trainer_dead_end`・コマンドの終わりの確かめ） | D | 候補の外。答えの続き（置くカード・ワザ・答え・引くカード）を複製の上で試す。探す深さと上限、読む値をこの監査ではたどっていない |
| 6 枚の受理のあと（置くカード・答え・正誤・引くカード・おもてにしたサイド・交換） | C | 実際の手札・山札・サイドの中身で決まる。候補側では評価しない（使ったあとに公開される） |

- B（公開から決まる部分だけを分ける）に当たる条件はありませんでした。今の関数そのものが、公開の値と本人の知識だけで結果を決めています
- A の前提は 2.3 節の不変条件です。その前提を満たさない状態を候補が受け取るかは、5.3 節の未確認として残します
- A は「候補側で呼んでも情報が漏れない」ことだけを言います。受理・完走は保証しません

### 4.1 `unverified` を `may_stop_later` にするときに増える保証と要る根拠

- 増える保証
  - 「使うための条件は、送信と同じ関数（`check_play_trainer(use_condition=True)`）で、候補の時点の状態について確かめた」
  - 条件で使えないカードは選べるものに出さず、決められないカードは実行できない区分で示す
- 増えない保証
  - 受理の前の先読み（D）による拒否は、まだありえます（`preflight_not_evaluated`）
  - 受理のあとの決定・停止（C）もありえます（`continuation_not_evaluated`）
  - `supported` にはしません（ほかのトレーナーと同じ）
- 要る根拠
  1. この文書の静的な追跡
  2. 候補の入口での秘密だけの双子（7 章）
  3. U7・client_api・直接のコマンドの一致
  4. 候補・inputs・check の無副作用
  5. 拒否の配信の境界
- 区分の変更そのものを目標にはしません。6 章の案は、根拠がそろったときにだけ区分が変わる形にしています

## 5. エンジンの実行時の確かめとの関係

### 5.1 切り替えと先読み

- `check_play_trainer(state, cmd, *, use_condition=True)`（`engine.py:2001`）
  - エンジンはいつも真で呼びます（`_play_trainer`。1989 行）
  - 候補の未評価は、エンジンの確かめを省くことではありません。送れば同じ条件で拒否されます
- 受理の前の先読み（`_apply_once`（888 行）の中の 1009〜1022 行）は、使うための条件のあとに走ります
  - ［ちえくらべ］があれば、使わない続きを確かめます（`_trainer_reaction_decline_check`）
  - なければ、`changes_field` の真のトレーナーで、効果の途中の決定の答えの続きを確かめます（`_trainer_dead_end`）
  - クイズ 4 枚・カードめくりゲームは既定の真、とりかえっこプリーズは偽です
  - これは候補では今も将来も呼ばない実行時の確かめで、PT-5e の補完の対象の外です
- 本人の知識に基づく既存の確かめ（U7-5c の A-own）は、別の 6 つの型の話で、PT-5e の 6 つの型とは重なりません

### 5.2 借用・代用の経路

- 錯乱ジム（`_chaos_tails`。`engine.py:2195`）
  - 「うら」のとき、公開の部分（`borrow_public_unusable_reason`）だけで聞くかを分けます
  - 借りる人の使うための条件の Unsupported（`borrow_condition_stop`）は、選ぶと止める選択として決定の続きの情報に置きます（答える人だけに見える）
  - Illegal は「使う」と答えたときに拒否します（`require_borrow_playable`。2330 行）。T-F1（v0.168）の修正です
  - とりかえっこプリーズは借りると CH1（`borrow_problem`）
- サイキックコントロール（`effects.py:21967〜21974`）
  - 選べるものは公開の部分で作ります（F-8）
  - 条件の Unsupported は、選ぶと止める選択にします
- どちらも、借りる人の条件の判定を、借りる人自身の手札と公開の枚数で行います（2.2 節の「本人」を借りる人に読み替えても成り立つ）
- PT-5e の候補（手札から使う `play_trainer`）とは別の、決定の候補の経路です。この監査で変える必要はありません

### 5.3 実行時の情報境界について

- 不具合の疑いは見つかりませんでした
- 未確認として独立に残すもの（候補の補完とは別の課題）
  - `ClientHub.from_state` が `check_invariants`（おもての山札の並びの不変条件）を確かめるか
  - 満たさない状態（おもての印が上から続かない）を構築すると、2.3 節の前提が崩れます。試しの引き方の結果が、山札の順序で変わりうるかもしれません
  - 構築盤面だけの入口で、通常の進行（`check_invariants` を通った状態だけを返す）とスナップショットの復元（確かめる）では起こらない見込みです
  - 再現の計画（今回は実行しない）
    1. テスト専用の改変で、おもての印を 2 枚目だけに付けた状態を作る
    2. `ClientHub.from_state` が受け付けるかを見る
    3. 受け付けるなら、クイズの `PlayTrainer` の拒否の有無が山札の順序で変わるかを見る

## 6. 最初の補完案

### 案 1（推奨。1 単位）: PT-5e の 6 枚の使うための条件を、候補で呼ぶ

| 項目 | 内容 |
|---|---|
| 対象 | `PLAYABLE_NOT_EVALUATED` の 5 つの型（6 枚）を、候補の作成で `check_play_trainer(use_condition=True)` に戻す |
| 対象外 | 受理の前の先読み（D）・受理のあと（C）・借用の経路・条件の中の未裁定（QZ1・FC1・FU3）・未対応（身長）・effects.py の外で定義した条件（今までどおり呼ばない）・`supported` への変更 |
| 修正範囲 | `legal_actions.py`: `PLAYABLE_NOT_EVALUATED` を空にし、`GUARANTEE_TRAINER` の文を直す。`REASON_USE_CONDITION` は effects.py の外の条件のために残す<br>`scripts/build_legal_actions_u7_5_design.py` の PT-5e の行と生成物 `docs/legal-actions-u7-5-design.json` を作り直す<br>文書。エンジンの処理（`engine.py`・`effects.py`）は変えない |
| 公開 API の応答と保証 | 6 枚が通れば `may_stop_later`（理由から `use_condition_not_evaluated` が消える）<br>Illegal のカードは選べるものに出ない（全部なら `play_trainer` の候補がなくなる）<br>Unsupported のカードは eligible 偽（`ruling_unresolved`・`not_implemented`）で、check・submit は `CANDIDATE_NOT_EXECUTABLE` を返す（エンジンを呼ばない）<br>処理可能性の 6 区分・理由のコードの集合・入力の形は変えない |
| 既存のクライアント | 形は同じで値が変わる。GUI・検証用 AI は区分の値をすでに扱える<br>検証用 AI は、`deep` の範囲（`may_stop_later` をふくむ）にこの 6 枚が入る。判定の説明の理由の集合（`EXPLAINING_REASONS`）の見直しが要るかを、別の追従の単位で確かめる |
| 直接のコマンド | 変えない。U7 の submit も、通る入力はエンジンへ同じコマンドを渡す<br>違いは、今まで送ってエンジンが拒否していた入力を、API が送る前に断る点（意図した差）。拒否のコードは、エンジンの条件のコードから `CANDIDATE_NOT_EXECUTABLE` に変わるか、選べるものから消える |
| 情報境界の確かめ方 | 7 章の双子（候補の入口）と、2.3 節の根拠の再確認 |
| 限定のテスト・上限・完了の基準 | 7 章 |
| 版・識別 | `legal_actions.py` は振る舞いのファイル（`replay_record.INSTRUMENTATION_FILES` に入らない）なので、`behavior_digest` が変わる。版を 0.176.0 に上げる<br>0.175.0 の記録・スナップショットは、0.176.0 では再実行・復元できない（既存の設計） |
| 残る未確認 | D の先読みの読む値。5.3 節。new_game からの到達（公開の固定デッキにこの 6 枚はない。`tools/existing_effect_games.py` の開発用の対戦には出るが、U7 の候補を経由しない）。GUI・検証用 AI の追従 |

- 置き換えの案（条件を公開の枚数の式に書き直して候補だけで使う。B 型の分離）は勧めません
  - エンジンと別の実装になり、ずれる危険が増えます
  - 今の関数が公開の値だけで決まるので、分ける利点がありません
- 現状維持（`unverified` のまま。文書だけ）も選べます
  - その場合の根拠: 7 章の双子を候補の入口で確かめるまでは、静的な読みと `apply_command` の入口のテストだけで区分を上げない
  - 影響: 利用者は送るまで使えるかが分からない。情報の漏れはない
- 判断は利用者に委ねます。この監査では実装しません

## 7. 将来の限定の検証の計画（今回は実行しない）

### 7.1 双子の設計

双子を比べる前に、まず次を確かめます（前提の確かめ）。

- 比べる主体（使うプレイヤー）の観測 `observe(state, actor)` と `visible_log(state, actor)` が一致する
  - 手札・山札の枚数・`face_up_count`・`known_face_up`・相手の手札の枚数・サイドの枚数とおもて
- 相手・観戦者の観測とログも一致する
- 秘密の配分だけが違う（`fingerprint` の完全な状態は違う）

| 双子 | 違えるもの | 一致を期待するもの（候補の入口） | 実行のあとに正当に違いうるもの |
|---|---|---|---|
| T1 山札の順序 | 本人の山札のおもてより下の順序／相手の山札のいちばん上より下の順序（フラッシュあり・なしの両方） | 候補・件数・並び・eligible・処理可能性・理由・inputs・check の応答（正しい入力・不正な入力） | 引いたカード（本人の手札。本人にだけ見える） |
| T2 本人の山札とサイドの配分 | 同じ枚数のまま、山札とサイドのカードを入れかえる | 同上 | 同上 |
| T3 相手の秘密 | 相手の手札の中身（同じ枚数）・相手のうらのサイドの中身（同じおもての位置）・相手の山札の順序 | 同上 | カードめくりゲームのおもてにしたサイド、とりかえっこプリーズの交換の中身、クイズの正誤の結果 |
| T4 対照例（違ってよい） | 山札の枚数、おもての枚数（0・1・2）、相手の手札 0 枚・1 枚、うらのサイド 0 枚、手札の進化カード・ポケモンの有無 | 候補・区分が予想どおりに変わる（Illegal は消え、Unsupported は eligible 偽） | — |

- 対象は 6 枚すべてです
  - `SetAsideGuessKindQuiz` は 2 枚を別に扱います
  - とりかえっこプリーズは、既存に秘密だけの双子がないので必ず含めます

### 7.2 一致・無副作用・配信

- U7（`ActionHost`）・client_api（`ClientHub`）・直接のコマンドの一致
  - 通る入力は、3 つで受理と状態・乱数・ログが一致する
  - Illegal・Unsupported の入力は、直接のコマンドのコードと、API の扱い（選べるものにない・`CANDIDATE_NOT_EXECUTABLE`）の対応を表で確かめる
- 候補・inputs・check の無副作用: 前後で状態・乱数・ログ・決定・更新番号・全員への更新が変わらない
- 拒否の配信の境界
  - 送る前の断り・エンジンの拒否は、送った人にだけ返る
  - 相手・観戦者への更新は 0 件で、取っ手は失効しない
- 意図した差のテストの書き換え（実装の単位で行う）
  - `tests/test_legal_actions_u7_5c.py` の `test_draw_trials_are_not_called_by_queries`（呼ぶことの確かめに変える）
  - 同じファイルの `test_unverified_card_rejected_by_engine_privately`（候補から消えることの確かめに変える）
  - 同じファイルの `test_classification_matches_the_design_scan`（分類の和の確かめ）

### 7.3 範囲と上限

| 項目 | 内容 |
|---|---|
| 盤面 | 既存のテストの盤面の関数で作る構築盤面。new_game からの到達とは数えない<br>・`tests/test_quiz_answer_rejection_v0_135.py` の `board`・`play_flash`<br>・`tests/test_card_flip_answer_rejection_v0_136.py` の `board`<br>・`tests/test_legal_actions_u7_5c.py` の `board` |
| 実行 | 1 プロセス 1 モジュール。新しいモジュール 1 つ（目安 60 秒以内）と、関連の既存モジュールを再実行する<br>・`test_legal_actions_u7_5c`・`test_quiz_answer_rejection_v0_135`・`test_card_flip_answer_rejection_v0_136`<br>・`test_blaines_quiz_heights_v0_129`・`test_trade_please_v0_130`・`test_flash_faceup_deck_v0_126`<br>・U7-5 の設計の生成器の `--check`・検証用 AI のテスト<br>合計 15 分以内 |
| 対象外 | seed の探索・大量の対戦・全体テスト・GUI・E2E・lockstep・状態の監査 |
| 完了の基準 | 双子 T1〜T3 で候補の入口の応答が一致<br>T4 が予想どおり<br>3 経路の一致と、表どおりの対応<br>無副作用と配信の境界<br>意図した差のほかに既存テストの失敗がない<br>版・識別の更新 |

### 7.4 区別

| 区別 | 内容 |
|---|---|
| 既存テストの主張 | 2.3 節に挙げたもの（`apply_command` の入口）。この監査では実行していない |
| 構築盤面 | 7.1 節の計画。未実行 |
| new_game からの到達 | 計画しない（公開の固定デッキにこの 6 枚はない。seed の探索をしない）。未確認として残す |

## 8. 確かめ方の区別と結論

| 区別 | 内容 |
|---|---|
| 静的に確かめたこと | 1〜5 章の、コードの読み（呼び出しの閉包・読む値・副作用・例外・観測の公開範囲・不変条件の確かめの場所）。基点 `62fff09` |
| 既存テストの主張 | 2.3 節・7.2 節に挙げたテストの名前と内容（読んだだけ。実行していない） |
| 保存済みの証跡 | PT-5e を直接扱う保存済みの証跡はない。検証用 AI の証跡（`C:/dev/kyuura-engine-verification-vai/`）は読んでおらず、主張の根拠にしていない |

- 結論: PT-5e の 6 枚の使うための条件は、静的な読みでは、本人の手札・公開の枚数・おもての山札の不変条件だけで結果が決まります（A）。候補で呼んでも情報は漏れない見込みです
- 「安全確認済み」とするのは、静的な追跡の範囲（`check_playable` の閉包）だけです
- 次はまだ確かめていません
  - 候補の入口での双子
  - 受理の前の先読み（D）の読む値
  - `ClientHub.from_state` の不変条件（5.3 節）
  - new_game からの到達
- PT-5e を「対応済み」とはしません。補完（6 章の案 1）は、利用者の判断のあとの別の単位です
- この監査では、エンジン・検証用 AI・GUI・renderer・kyuura・カードデータ・固定デッキ・規約集合・裁定・識別方式・版を変えていません

## 9. 実装の結果（v0.176.0）

利用者の採用（2026-11-09）: 6 章の案 1。対象 6 枚の使うための条件を候補・check で評価する補完です。情報境界と無副作用の限定の検証を条件とし、エンジンのゲームの処理・裁定・GUI・AI は変えません。

| 項目 | 値 |
|---|---|
| 基点 | `1c0fc07`（`claude/pt-5e-audit`。U-R3a・AI の追従・この監査を含む公開コミット。`origin/main` には入っていない） |
| ブランチ | `claude/pt-5e-impl` |
| 実装とテスト | `9b1d098` |
| 配布用の固定コミット | `6f627007a2a7101be066ac6ba035e838a75e36e1`（版 0.176.0） |

### 9.1 変更

- `legal_actions.py`
  - 5 つの型を `PLAYABLE_NOT_EVALUATED` から新しい `PLAYABLE_FACE_UP_PREFIX_TRIALS` へ移した
  - `PLAYABLE_NOT_EVALUATED` は空で残した（テストと生成器が参照するため。最小の変更）
  - `_use_condition_evaluated(effect, state)` は、この 5 つの型について、おもての山札の並びの不変条件（`faceup.prefix_problems`）が成り立つ状態だけで真
  - 候補は、真なら実行時と同じ `check_play_trainer(use_condition=True)` を呼ぶ。公開用の判定は別に書いていない（二重の実装にしない）
  - 不変条件が成り立たない状態では、v0.175 までと同じく呼ばずに `unverified`（`use_condition_not_evaluated`）
- 結果の扱い（既存の候補の作り方のまま）

  | 条件の結果 | 候補での扱い |
  |---|---|
  | ゲーム上使えない（`NO_OTHER_CARDS_IN_HAND`・`OPPONENT_HAND_EMPTY`・`NO_EVOLUTION_CARD_IN_HAND`） | 選べるものに出さない（全部なら `play_trainer` の候補がない） |
  | 未裁定・未対応（QZ1・FC1・FU3・`UNSUPPORTED_QUIZ_HEIGHT_*`） | 実行できない区分（eligible 偽、`unresolved_ruling`・`not_implemented`、理由 `stops_before_acceptance`）。check・submit は送る前に `CANDIDATE_NOT_EXECUTABLE` |
  | 通る | `may_stop_later`（理由 `preflight_not_evaluated`・`continuation_not_evaluated`） |

  - `supported` にはしません
  - `input_disclosure`（`confirmed`）は変えていません。処理可能性とは別の軸のままです
- `may_stop_later` が表すのは「使うための条件を、送信と同じ関数で、候補の時点の状態について評価した」ことだけです
  - 受理の前の先読み（`_trainer_dead_end`・`_trainer_reaction_decline_check`）による拒否と、受理のあとの停止はありえます
  - 受理・完走は保証しません
- `GUARANTEE_TRAINER` の `preconditions` の文を、実際の確かめの範囲に合わせた（引いて試す条件を呼ぶこと、不変条件が成り立たない状態と effects.py の外の条件は呼ばないこと）
- 設計の生成器と生成物
  - `scripts/build_legal_actions_u7_5_design.py` の PT-5e を A・`candidates` にし、U7-5c の basis・open を直した
  - `scripts/build_legal_actions_api_design.py` の残件の文を直した
  - `--write` で JSON と生成区画を作り直した（`--check` problems=0）
- submit・直接のコマンドの処理の順番・診断・挙動は変えていない。`engine.py`・`effects.py`・`faceup.py`・データも変えていない（`81e9e99` からの差なし）

### 9.2 前提の確かめ

**A. おもての山札の並びの不変条件**

| 経路 | 扱い | 確かめ |
|---|---|---|
| 通常の進行 | 各コマンドの終わりに `check_invariants`（`prefix_problems` を含む）を通った状態だけを返す | `test_normal_progress_keeps_the_invariant`（フラッシュ・番の最初のドローの合法な経路） |
| スナップショット | 保存の前と復元のあとに `check_invariants` を確かめる。崩れた状態は保存できない | `test_snapshot_restore_rejects_a_broken_invariant` |
| `ClientHub.from_state`（`HostedGame`） | 確かめない。崩れた状態を受け付ける | `test_from_state_accepts_a_broken_invariant_but_the_condition_is_not_evaluated` |

- 崩れた状態で、その3 の条件の結果は相手のおもての位置で変わります（テスト専用の改変。相手の山札の 2 枚目だけ・7 枚目だけがおもてで、本人の観測は同じ）
  - 2 枚目なら FU3、7 枚目なら通ります
  - したがって候補では、その状態で条件を呼ばず、どちらも `unverified` です（応答は同じ）
- **独立した課題 PT5E-FROM-STATE-INVARIANT**（今回は直していない）
  - 崩れた状態で送ると、エンジンの経路で結果が位置によって分かれます
    - 2 枚目なら、使う前の FU3 の拒否
    - 7 枚目なら、受理のあとのコマンドの終わりで `STATE_INTEGRITY` の failed
  - 構築盤面の入口（ホスト・テスト・検証者）だけの問題で、通常の進行とスナップショットでは起こりません
  - 再現はテストにあります。入口の変更は今回の補完に混ぜていません
  - 崩れた状態では、ガードの結果（評価するか）そのものが不変条件の崩れの有無で変わります。エンジンが作らない状態についての 1 ビットで、同じ課題に含めて記録しました
  - 追記: 公開入口の監査と最小修正の計画は [pt5e-from-state-invariant-audit.md](pt5e-from-state-invariant-audit.md)（文書だけ。入口は 0.176.0 のまま）

**B. 浅い複製の共有**

- `GameState.clone` は `__dict__` の浅い写しです。写し直すのは `players`（各プレイヤーの山札・手札・サイド・トラッシュ・場の配列と場のポケモン）と乱数（`copy_rng`）だけです
- 0.176.0 の盤面（フラッシュのあと）で、元と同じものを指す可変の値（list・dict・set）は、ほかにありませんでした（証跡の `twin_results.json` の `shared_mutables_after_clone` は空）
- ログとおもての印は不変のタプルで、付け替えるだけです
- 引いて試す処理（`draw_cards`）が変えるのは、写した山札・手札の配列と、写しのログ・印だけです
- 6 枚の条件と、試しの複製で引く処理を 2 回ずつ呼びました（`test_trial_draws_leave_the_original_and_shared_values`。3 つの場面 × 6 枚）
  - 元の状態（完全な状態・乱数・ログ・おもての印・決定）と、共有する値の表現は変わりませんでした
- 加えて、候補・inputs・check の前後の無変更は、双子のすべてと対照例で確かめました

### 9.3 情報境界の限定の検証（構築盤面）

- 場面は 3 つです
  - `none`: フラッシュを使わない
  - `top_only`: フラッシュのあと番の最初のドロー 4 回ずつ。いちばん上だけがおもて
  - `both`: フラッシュの直後。上から 5 枚がおもてで、6 枚とも FU3 で実行できない
- 双子を比べる前に、次を確かめました（42 組すべてで成り立った）
  - 本人（プレイヤー 0）と観戦者の観測・公開のログが同じ
  - 完全な状態が違う
- 比べたもの
  - 本人の候補の有無・件数・順序
  - eligible・処理可能性・理由・保証
  - すべての候補の inputs
  - 選べるものごとと不正な入力（空・存在しない番号・型の違い）への check
  - 前後の状態・乱数・ログ・決定
  - 全員（0・1・観戦者・ホスト）への更新

| 比べ | 場面 | 組 | 結果 |
|---|---|---|---|
| T1 山札の順序（本人・相手。`none` は 2・3 枚目、ほかはおもてでない 8・11 枚目） | 3 | 18 | どれも同じ。状態は変わらず、更新は 0 件 |
| T2 本人の山札とサイドの配分（同じ枚数で違うカードを入れかえ） | `none`・`top_only` | 12 | 同上 |
| T3 相手の秘密（手札の中身（同じ枚数）・サイドの中身・山札の順序） | `none`・`top_only` | 12 | 同上 |
| T4 対照（公開の枚数・本人の手札） | — | 11 | 予想どおり変わった（下） |

- T4 の内訳
  - その1: 図鑑番号のないポケモンだけなら `not_implemented`、ポケモンがなければ `unresolved_ruling`
  - その2: ほかの手札がなければ `unresolved_ruling`
  - その3: ワザを持つポケモンがなければ `unresolved_ruling`
  - 性格判定（進化カードなし）・とりかえっこ（相手の手札なし・ほかの手札なし）は、選べるものに出ない
  - カードめくり: ロケット団参上! で相手のサイドがすべておもてなら `unresolved_ruling`
  - とりかえっこのおもての枚数: `none`・`top_only` は通り、`both` は止まる
- 適用外として作らなかった比べ
  - 相手のおもてのカードのうち、いちばん上より下の中身だけを変える双子。本人には見えないが、v0.135・v0.136 の既存テストの範囲で、今回は作っていない
  - 公開されている山札の上のカード・本人の手札・`known_face_up` を変えた状態は、双子と呼ばず対照に分けました
- 受理のあとの違い: T1 の双子で、その2 に正解でない答えをしたあと本人が引くカードは違いました（正当な違い。`test_results_after_acceptance_may_differ`）。候補の段階の一致とは分けています

### 9.4 直接のコマンドとの一致

| 場合 | U7・client_api | 直接のコマンド |
|---|---|---|
| 通る（6 枚。`none`） | check valid、受理。状態・乱数・ログ・決定の通し番号・本人への見え方が直接と同じ<br>次の決定: クイズ 4 枚は置くカード、カードめくりはサイドの選択、とりかえっこは相手の手札から選ぶ | 受理 |
| 受理のあとの決定（その2: 置く → 相手が答える。その1: 置く → 身長の値） | U7 の answer_decision と直接の ResolveDecision で同じ状態。決定はなくなる | 同じ |
| ゲーム上使えない（性格判定・進化カードなし、とりかえっこ・相手の手札なし） | 選べるものにない（送れない） | 拒否（`NO_EVOLUTION_CARD_IN_HAND`・`OPPONENT_HAND_EMPTY`） |
| 未裁定・未対応（その3 の QZ1・その2 の FC1・カードめくりの FU3・その1 の図鑑番号なし） | check・submit が `CANDIDATE_NOT_EXECUTABLE`（送る前に断る）。状態は変わらず、全員への更新は 0 件 | 拒否（それぞれのコード） |
| 不変条件の崩れた状態（評価しない） | `unverified` で示し、送るとエンジンが本人にだけ拒否（`NO_OTHER_CARDS_IN_HAND`。`result.role` は `actor`）。相手・観戦者への更新は 0 件で、取っ手は有効なまま | 拒否 |

- U7 が送る前に断る場合と、直接のコマンドをエンジンが拒否する場合の違いは、意図した API 上の差です（v0.175 までは、どちらもエンジンの拒否でした）
- 錯乱ジム・［ちえくらべ］・サイキックコントロールの借用経路は変えていません。既存のモジュールで回帰がないことを確かめました（9.5 節）

### 9.5 実行したテスト

1 モジュールずつ別のプロセスで、並列なしに流しました（証跡の `tests/test_runs.txt`）。

| モジュール | 件数 | 結果 |
|---|---|---|
| `tests.test_legal_actions_pt5e_v0_176`（新） | 14 | 1 回目は失敗 8、2 回目は失敗 1、3 回目で失敗 0。どれもテストの側の誤り（下） |
| `test_legal_actions_u7_5c` | 32 | 失敗 0（意図した差 3 つを直したあと） |
| `test_legal_actions_u7_5_design` | 27 | 1 回目は失敗 1（意図した差）。直してこのモジュールだけ再実行し、失敗 0 |
| `test_legal_actions_api_design`・`u7_5fg_spec`・`test_quiz_answer_rejection_v0_135`・`test_card_flip_answer_rejection_v0_136`・`test_blaines_quiz_heights_v0_129`・`test_trade_please_v0_130`・`test_chaos_gym_borrow_t_f1`・`test_slowking_mind_games_v0_132`・`test_client_api`・`test_legal_actions_u7_1`・`test_distribution`・`test_preset_decks_v0_20` | 14・9・20・25・28・34・12・31・9・42・12・15 | どれも失敗 0 |
| `test_flash_faceup_deck_v0_126` | 38 | Bash ではエラー 4（Bash から git を呼べない既知の環境の問題）。PowerShell で再実行して失敗 0 |
| `test_verification_ai_u_r3a`（AI の影響の確かめ） | 12 | 失敗 0 |
| `test_verification_ai_v2_repeat`（AI の影響の確かめ） | 15 | **失敗 4**（9.7 節。AI の追従の課題として残す） |

- 新しいモジュールの失敗と直し（期待値は変えていない）
  - 1 回目: T2 で同じカードどうしを入れかえていた（6）
  - 1 回目: 受理のあとの比べで、引く 2 枚の両方を入れかえていた（1）
  - 1 回目: 崩れた状態の送信で、フラッシュが手札に残っていて条件を満たしていた（1）
  - 2 回目: 送信の応答の診断の項目の場所を誤っていた（1）
- 意図した差（既存のテストを直した）
  - `test_legal_actions_u7_5c`: 分類の和（`PLAYABLE_FACE_UP_PREFIX_TRIALS`）、`test_draw_trials_are_called_by_queries`（呼ぶことの確かめ）、`test_unusable_draw_trial_is_not_offered`（使えないカードを出さない）
  - `test_legal_actions_u7_5_design`: 壊した仕様の 2 つ（PT-5e を E に戻してから壊す）
- 合計の時間は約 6 分です
- 流していないもの: 全体のテスト・GUI・E2E・大量の対戦・lockstep・状態の監査・seed の探索・AI の実対戦。lint（ruff）はこの環境にない

### 9.6 版・識別・配布

- 版は 0.176.0（`kyuura_engine/__init__.py`・`pyproject.toml`・`tests/test_preset_decks_v0_20.py`）。識別方式は変えていない
- `behavior_digest` は `d1bcca17…9149`（0.175.0）から `337caa88c8419c803e90a98d92fa8d36622bb7db161c057288221243b97932ea` に変わった（`legal_actions.py` は振る舞いのファイル）
  - `instrumentation_digest` は `e7d36df3…3034` のまま
- 互換: 0.175.0 の記録・スナップショットは 0.176.0 では再実行・復元できない（既存の設計）
  - 過去の証跡は元の版のまま残し、版や識別を書き換えて使っていない
  - スモークのスナップショットは 0.176.0 のソースで作った
- 配布用の固定コミット `6f627007a2a7101be066ac6ba035e838a75e36e1`
  - 配布物の中のファイルは 62（`81e9e99` と同じ一覧）。`pyproject.toml` の差は版だけで、新しい依存はない
  - `git archive` から作った wheel（sha256 `25194699bb8bf917c0fe985f9678bf2a6009f1379f794838b9348001f02fbe95`）に `scripts/check_distribution.py` をかけた: required=62・problems=0
  - リポジトリの外の新しい venv に、Git の URL から通常のインストールをした
    - `direct_url.json` の `vcs_info.commit_id` が一致し、`dir_info.editable` はない
    - `site-packages` から読み込み、実装の識別がソースと一致した。依存の宣言はない
  - スモーク（`-I`・リポジトリの外の作業ディレクトリ・スナップショットの復元と ClientHub）の結果。どれも全員への更新は 0 件で、終了コードは 0

    | 盤面 | 結果 |
    |---|---|
    | その2 | `may_stop_later`・eligible 真・check valid |
    | カードめくり（フラッシュの直後） | `unresolved_ruling`・eligible 偽・check `CANDIDATE_NOT_EXECUTABLE` |
    | 性格判定（進化カードなし） | 選べるものになし |

### 9.7 GUI・検証用 AI への影響（読んだだけ。どちらも変えていない）

新しい API の項目・値の語彙はありません（処理可能性の 6 区分・理由のコード・入力の形は同じ）。値の出方だけが変わります。

**GUI**

比べたのは `moheronemy/kyuura-engine-gui` の `feature/engine-u-r3a-facedown-powers` の `8f78ed3b227b754d6c68ba4a13dfb7516b1ee2fd` です。2026-11-09 の時点で最新の公開ブランチで、エンジン `81e9e99`（0.175.0）を固定しています。GitHub の API で読み取りだけをしました。

| 確かめたこと | 読んだ結果 | 要る追従 |
|---|---|---|
| エンジンの固定・版 | `server/requirements.txt` と契約の `engine` が `81e9e99`・0.175.0<br>`engine_source.py` が導入元のコミットと版を照らし、`server/tests/test_contract.py` が版 0.175.0 を確かめる | 固定・契約の `engine`・テストの版を `6f62700`・0.176.0 に更新 |
| 値の語彙 | 契約の `processability`・`reason_codes`（`use_condition_not_evaluated` を含む）・`executable_processability` は変わらない値<br>`validate.ts` は保証の値を文字列として見るだけ | なし |
| 選べるものが消える・実行できない区分 | 既存のトレーナー（未登録・未裁定の条件）と同じ形 | なし（表示は実際に動かして確かめる） |
| unverified → may_stop_later | 契約の文書（`docs/engine-contract.md`）は「使うための条件を前もって呼ばないトレーナーは unverified（PT-5e の 5 つ）」と書く | 文書の直し |
| 固定例 | `web/src/test/fixtures.ts` に PT-5e のカードの固定例はない | なし |

- GUI のコードの変更は要らない見込みです。依存と契約の値・文書の追従で済むと読みました（実行していない）

**検証用 AI**（同じ基点の `tools/verification_ai`）

| 確かめたこと | 読んだ結果 |
|---|---|
| deep の範囲 | `DEEP_PROCESSABILITY` は `supported`・`may_stop_later` なので、6 枚の通るカードが deep の対象に入る（v0.175 までは fallback だけ） |
| judge の期待 | 通るカードの理由は `preflight_not_evaluated`・`continuation_not_evaluated` で、どちらも `EXPLAINING_REASONS` にある。受理の前の先読みの拒否は、今までどおり説明できる拒否<br>`use_condition_not_evaluated` は崩れた状態の経路に残る |
| 方策の意味の列の指紋（`test_verification_ai_v2_repeat` の GOLDEN） | 4 つとも変わった（長さは同じ）<br>0.176.0 のまま保証の文だけを 0.175.0 の文に戻すと、4 つとも元の指紋と一致した（証跡の `ai_impact/`）<br>候補の中身に保証の文が入るためで、方策の選び方・送信の結果は変わっていない（固定デッキに 6 枚はない） |
| 固定例・来歴 | `fixtures_u_r3a.py` の説明文が「今の実装（0.175.0）」と書く。U-R3a の固定確認の証跡は 0.175.0 のまま |

- AI に要る追従（今回は着手しない）
  - GOLDEN の指紋の更新と、その来歴（保証の文の変更だけによる差）の記録
  - 判定の版を上げるかの判断（判定の規則は変わらない見込み）
  - deep で 6 枚を選ぶ場面の確かめ
  - 版の記述の更新

### 9.8 確認・補完したことと、残る未確認

- **補完したこと**: 6 枚の使うための条件を、候補・inputs・check で評価する（不変条件が成り立つ状態）
- **確かめたこと**: 9.2〜9.6 節（構築盤面のテストと、配布物・通常のインストール）
- **残る未確認**
  - 受理の前の先読み（D。`_trainer_dead_end`・`_trainer_reaction_decline_check`）の読む値
  - new_game からの到達（公開の固定デッキにこの 6 枚はない。seed の探索をしていない）
  - 独立した課題 PT5E-FROM-STATE-INVARIANT（9.2 節）
  - GUI・検証用 AI の追従と、実際の画面・AI の実対戦での確かめ
  - 相手のおもてのカードのいちばん上より下だけを変える双子（候補の入口では作っていない）
- PT-5e の全体を「完走を保証した」とは扱いません。候補側で条件を評価するようになった範囲は、不変条件が成り立つ状態の 6 枚の使うための条件だけです

### 9.9 証跡

保存先は `C:/dev/kyuura-engine-verification-vai/` です。

- `verifier/runs/pt5e-v0.176/`
  - `plan.json`: 採用と計画の記録。実行のあとに書き起こしたもので、そのことを記している
  - `invocation.json`: コマンド・終了コード・識別
  - `pending.json`: 独立した課題・保留
  - `tests/`: テストの出力と `test_runs.txt`
  - `twin_results.json` とそのスクリプト: 双子の前提と比べた結果、複製の共有の一覧、ガード
  - 配布と導入の結果、スモークの盤面
  - `ai_impact/`: GOLDEN の差の原因の確かめ
  - `gui_read/`: 読んだ GUI のファイル
- `public/runs/pt5e-v0.176/summary.json`: 非機密の集計だけ
- マニフェストは 484 ファイルです。既存の 428 ファイルが変わっていないことを確かめてから更新しました
  - `sha256.json`: `c2c9fb975200aceef00b2119c7e137584ff841ab8c3a2e701f09eead31a7f4b8`
