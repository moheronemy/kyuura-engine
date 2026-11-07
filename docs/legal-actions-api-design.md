# 合法手 API（U7）の仕様案

v0.159（U1〜U6 の総合検証）のあとの仕様案です。v0.160 で U7-1（決定への回答・番を終える）だけを実装しました（[legal-actions-u7-1.md](legal-actions-u7-1.md)）。ほかの単位は仕様だけです。実装の順序と完了の基準は [legal-actions-api-implementation-plan.md](legal-actions-api-implementation-plan.md)、実装の識別との関係は [implementation-identity-design.md](implementation-identity-design.md) の 5 章（U7 の行）です。

表と構造化した仕様（[legal-actions-api-design.json](legal-actions-api-design.json)）は `scripts/build_legal_actions_api_design.py` の `SPEC` から作ります（`--write`・`--check`。表を手で二重に書かない）。`--check` は、コマンドの型（`commands.py` の dataclass）・段階（`state.Phase`）・次の操作の種類（`diagnostics.NEXT_*`）・状態の区分・決定の選べるものの意味（`observation.OPTION_MEANINGS`）のすべてに対応があるかを、コードと名前で照らします。

## 採用の記録

<!-- generated:adoption begin -->
- `ADOPT-U7-PRINCIPLES`（2026-11-07・利用者）: U7 で、操作候補（本人が知る情報から提示できる操作）・必要な入力（対象・枚数などの段階的な選択）・処理可能性（今の規約集合と実装で扱える範囲）を区別すること。候補に載ることと、そのあとの全分岐が完走することは別の保証。実際の秘密の状態にコマンドを試し、通るものだけを一覧にする設計は採らない。最終の判定は apply_command に残す
- 仕様案の状態: `proposed`・承認 `not_approved`
<!-- generated:adoption end -->

区別: 「採用済み」は利用者が採用した原則（下の表の `採用済み`）、それ以外の契約の細部・表の値・単位の分け方は**推奨案**、9 章は**利用者の判断が要る事項**です。

## 1. 原則

<!-- generated:principles begin -->
- `P-ACTOR`（採用済み）: ホストが認証した操作主体（本人）にだけ、その時点の操作候補と必要な入力を返す。プレイヤーの番号を送るだけで、他人の候補・秘密の選択肢を取れない
- `P-NOT-NEXT`（採用済み）: U2 の next（次の操作の種類の手がかり）を合法手の一覧へ読み替えない。U7 は新しい契約
- `P-FINAL`（採用済み）: 実行の最終の判定は apply_command。候補を取ったことは、あとの操作が受理される保証ではない
- `P-NO-TRIAL`（採用済み）: 実際の秘密の状態にコマンドを試し、通るものだけを一覧にしない（候補の作成は apply_command・先読みを呼ばない）
- `P-SEPARATE`（採用済み）: 候補に載ること・必要な入力・処理可能性を別の項目にする。候補に載ることは、そのあとの全分岐が完走する保証ではない
- `P-STAGED`（採用済み）: 大量の組み合わせを全展開しない。段階的な入力（ワザ → 対象、トレーナー → 枚数とカード）で表す
- `P-NO-SIDE-EFFECT`（採用済み）: 候補の取得で、ゲーム上の決定を作らない。状態・乱数・ログを変えない
- `P-TWIN`（採用済み）: 同じ本人の知識と公開の情報を持つ双子の状態では、候補の一覧・理由・入力の制約から秘密の配分を区別できない（正当に始まった山札の検索の選択肢だけは実際の山札による）
- `P-NOT-HIDDEN`（採用済み）: エンジンの未対応を、候補から黙って消してゲームの禁止に見せない（処理可能性で表す）
- `P-COMPLETENESS`（採用済み）: 上限を超えたとき、一部だけを返して完全な一覧と称さない。完全な列挙・部分的な候補・判定未確定を区別する。初版で保証できない完全性は保証しないと書く
- `P-NO-MODE-BRANCH`（採用済み）: 3 つの規約集合の違いは、状態の規約集合の登録（続行規約の参照）から受け取る。モードの名前・カードの ID の分岐を engine.py・resolution/ に加えない
- `P-NO-VERIFIER-DATA`（採用済み）: 検証者用の記録・スナップショット・確認値を、通常の API の応答に使わない
- `P-REVISION`（採用済み）: 完全な状態のハッシュ・乱数の確認値を、公開の更新番号に使わない。ホストが管理する、秘密の状態を推測できない対応を使う
<!-- generated:principles end -->

## 2. 現況（コードを読んだ判断）

| 項目 | 今の実装 | U7 での扱い |
|---|---|---|
| コマンド | `commands.py` の 20 の dataclass。辞書の形は `command_to_dict`・`command_from_dict`。カードは uid、場のポケモンは番号で指す | 候補は同じ型のコマンドを作る材料（入力の段）を返す。送るのは今の `submit` |
| 段階 | `state.Phase`（準備 3・main・決定待ち 3・終局・延長戦の開始待ち・停止） | 3 章の表 |
| U2 の `next` | `diagnostics.next_actions`: 段階・番・決定だけから決まる操作の種類と送るプレイヤー。どのカード・ワザ・対象を選べるかを持たない | 手がかりのまま。U7 の候補の種類の上位の分類（4 章の表） |
| 決定 | `PendingDecision`（id・kind・player・options・min_choices・max_choices・resume・context）。`observe(state, viewer)` の `decision` は、決める人にだけ選べるものと意味（`OPTION_MEANINGS`。9 種類）を渡し、相手・観戦者には種類と数だけ（`HIDDEN_COUNT_KINDS` は数も渡さない）。山札をさがす決定（`DECK_REVEALING_KINDS`）の選べるものは、決める人が見ているカード | 決定への回答の候補は `observe` の `decision` をそのまま使う（新しい形を作らない） |
| 対戦の道具・AI の方策 | `tests/helpers.trainer_policy_command`・`scripted_command`、`examples/start_preset_game.py`、`tools/` の対戦の道具は、内部の状態（`state.players`・手札・山札の枚数・決定の `options`・`context`）を直接読む | 公開の API に流用しない（P-NO-TRIAL・P-TWIN）。API だけを使う方策を U7-6 で作る |
| 宣言の前の確かめ・先読み | `apply_command` の中の確かめと、ワザの宣言の前の先読み（`resolution/preflight.py`。`MAX_BRANCHES` = 4096）、秘策の試し（`_IDENTITY_TRIAL_LIMIT` = 512）、決定の答えの数（`_ALTERNATIVE_ANSWER_LIMIT` = 256）、色の読み方（`COLOR_READINGS_LIMIT` = 256） | 候補の作成で呼ばない（秘密の状態に試すことになる）。上限が公開の情報だけで決まるときだけ `technical_limit` に使う |
| 本人の観測・公開のカードの定義 | `observe`（本人・相手・観戦者）。カードの定義（`state.definitions`。公開の印刷の情報） | 候補の材料は、観測と公開のカードの定義と本人の知識だけ |
| 情報漏れの対策（v0.147〜v0.151） | 秘密の山札で受理・拒否・理由が変わる処理を、持ち主の知識だけで決まる確かめに直した（`effects.searchable_deck_cards`・`deck_choice_may_only_stop`・`deck_lower_bound_where`・`deck_rainbow_possible`、決定の有無を山札の中身で変えない `required_search_choices`）。検査は `tests/log_audit.twin_command_problems`（双子の盤面） | 候補の処理可能性は、これらの持ち主の知識の関数だけで決める。双子の検査を候補の応答に広げる（7 章） |

## 3. 段階と候補

<!-- generated:phases begin -->
| 段階 | 状態の区分 | 操作主体 | 候補の種類 | 初版で complete |
|---|---|---|---|---|
| `setup_placement` | in_progress | 両方のプレイヤー（まだ置いていない人） | `place_starting` | はい |
| `setup_mulligan_draw` | in_progress | 引く枚数の残るプレイヤー | `mulligan_draw` | はい |
| `setup_first_player` | in_progress | ホスト（ジャンケンはエンジンの外の出来事） | `report_janken` | はい |
| `main` | in_progress | 番のプレイヤー | `end_turn`<br>`play_basic`<br>`attach_energy`<br>`evolve`<br>`retreat`<br>`use_attack`<br>`play_trainer`<br>`use_power`<br>`use_stadium`<br>`remove_disguise`<br>`discard_from_play`<br>`reveal_face_down`<br>`check_face_up_deck` | いいえ |
| `take_prize` | awaiting_decision | 決定のプレイヤー | `take_prize` | はい |
| `promote_active` | awaiting_decision | 決定のプレイヤー | `promote_active` | はい |
| `decision` | awaiting_decision | 決定のプレイヤー | `answer_decision` | はい |
| `sudden_death` | sudden_death_pending | ホスト（対戦の進行の操作。どちらかのプレイヤーの選択ではない） | `start_sudden_death` | はい |
| `game_over` | game_over | なし | なし | はい |
| `halted` | halted | なし（再開する API はない） | なし | はい |
<!-- generated:phases end -->

## 4. 操作の種類と必要な入力

<!-- generated:operations begin -->
| 種類 | コマンド | 操作主体 | 必要な入力の段 | 単位 |
|---|---|---|---|---|
| `place_starting` | `PlaceStartingPokemon` | player | choose_cards:active(1)<br>choose_cards:bench(0..5) | U7-2 |
| `mulligan_draw` | `DrawMulliganCards` | player | choose_count | U7-2 |
| `report_janken` | `ReportJankenResult` | host | choose_player | U7-2 |
| `play_basic` | `PlayBasicToBench` | player | なし | U7-3 |
| `attach_energy` | `AttachEnergy` | player | choose_pokemon | U7-3 |
| `retreat` | `Retreat` | player | choose_pokemon:new_active<br>choose_energies:cost | U7-3 |
| `evolve` | `EvolvePokemon` | player | choose_pokemon | U7-3 |
| `end_turn` | `EndTurn` | player | なし | U7-1 |
| `use_attack` | `UseAttack` | player | choose_attack<br>options:attack_modifiers（stadium_coin・attack_power・with_power(s)）<br>after_acceptance:decision | U7-4 |
| `take_prize` | `TakePrize` | player | choose_option:position | U7-1 |
| `promote_active` | `PromoteActive` | player | choose_option:pokemon | U7-1 |
| `answer_decision` | `ResolveDecision` | player | choose_option:decision（observe の decision をそのまま使う） | U7-1 |
| `play_trainer` | `PlayTrainer` | player | after_acceptance:decision（枚数・カードは使ったあとの決定） | U7-5 |
| `use_power` | `UsePokemonPower` | player | choose_power<br>registered:power_inputs（energy・source・target・card。カードの登録が決める） | U7-5 |
| `use_stadium` | `UseStadium` | player | registered:stadium_inputs（energy） | U7-5 |
| `remove_disguise` | `RemoveDisguise` | player | choose_pokemon | U7-5 |
| `discard_from_play` | `DiscardFromPlay` | player | choose_pokemon | U7-5 |
| `reveal_face_down` | `RevealFaceDown` | player | choose_pokemon | U7-5 |
| `check_face_up_deck` | `CheckFaceUpDeckCard` | player | choose_option:face_up_position（公開のおもての山札のカード） | U7-5 |
| `start_sudden_death` | `StartSuddenDeath` | host | なし | U7-2 |
<!-- generated:operations end -->

`next`（U2）との対応（`next` は手がかりのまま。U7 の候補の一覧ではない）:

<!-- generated:next begin -->
| next（U2） | U7 の候補の種類 |
|---|---|
| `place_starting_pokemon` | `place_starting` |
| `draw_mulligan_cards` | `mulligan_draw` |
| `report_janken_result` | `report_janken` |
| `turn_action` | `end_turn`<br>`play_basic`<br>`attach_energy`<br>`evolve`<br>`retreat`<br>`use_attack`<br>`play_trainer`<br>`use_power`<br>`use_stadium`<br>`remove_disguise`<br>`discard_from_play`<br>`reveal_face_down`<br>`check_face_up_deck` |
| `answer_decision` | `answer_decision`<br>`take_prize`<br>`promote_active` |
| `start_sudden_death` | `start_sudden_death` |
<!-- generated:next end -->

入力の種類（段階的な入力。組み合わせを全展開しない）:

<!-- generated:inputs begin -->
| 入力の種類 | 意味 | 制約 | 情報の元 |
|---|---|---|---|
| `choose_option` | 今の決定の選べるもの（observe(state, actor) の decision.options の value）から min_choices〜max_choices 個 | 個数・重複なし | 既存の決定（再利用） |
| `choose_cards` | 本人に見えるカード（observe の card。uid）から選ぶ | 個数・条件（たねポケモンなど。カードの定義と公開の状態だけで決まるもの） | 本人の知識 |
| `choose_pokemon` | 場のポケモンの番号（公開）から選ぶ | 個数・条件 | 公開 |
| `choose_energies` | ついているエネルギー（公開）から、費用を満たす組を選ぶ | 費用（数・色）の条件で表し、組を全展開しない | 公開 |
| `choose_attack` | ワザの位置（印刷・今の姿のワザ。公開） | 1 つ | 公開 |
| `choose_power` | ポケモンパワーの位置（公開） | 1 つ | 公開 |
| `choose_count` | 数（0〜上限。上限は公開の枚数から） | 範囲 | 公開 |
| `choose_player` | プレイヤー（0・1） | 1 つ | ホストの入力 |
| `options` | 操作の任意の指定（ワザの宣言のスタジアムのコイン・パワーを使う宣言など） | 真偽・指定の組 | 公開 |
| `registered` | カードの登録（effects の登録表）が宣言する入力。共通の処理はカードの ID で分岐しない | 登録が宣言する種類（上の語彙のどれか） | カードの登録 |
| `after_acceptance` | 受理したあとに、エンジンが決定として尋ねる入力（候補の取得では決定を作らない） | そのときの決定（choose_option） | 受理のあとの決定 |
| `decline` | 任意の辞退（min_choices が 0 の決定・「てよい」の効果） | 選ばないことを明示する（空の選択とは別の印にしない。既存の ResolveDecision の空の choices） | 既存の決定 |
<!-- generated:inputs end -->

段階的な入力の例:

- ワザ: 候補 `use_attack`（source はバトル場のポケモン、入力の段 `choose_attack` → `options`）。ワザの対象・コインのあとの選択は、受理のあとにエンジンが決定として尋ねる（`after_acceptance`。今の決定の仕組みを使う）
- トレーナー: 候補 `play_trainer`（source は手札のトレーナーの uid）。枚数・カードの選択は、使ったあとの決定（`after_acceptance`）。候補の取得では決定を作らない
- にげる: 候補 `retreat`（入力の段 `choose_pokemon:new_active` → `choose_energies:cost`）。費用はエネルギーの組を並べず、数・色の条件で表す
- 決定への回答: 候補 `answer_decision`（入力の段 `choose_option`。`observe` の `decision` の options・min_choices・max_choices・meaning）。`min_choices` が 0 なら任意の辞退（`decline`。空の `choices`）

## 5. 応答の形

<!-- generated:response begin -->
| 項目 | 意味 | 元 |
|---|---|---|
| `kyuura_legal_actions_format` | 応答の形式の版（1 から） | 固定 |
| `game` | ホストが発行した対戦の取っ手（不透明な文字列。seed・記録の識別ではない） | ホスト |
| `actor` | ホストが認証した操作主体（0・1・host） | ホスト |
| `revision` | 候補を作った状態との対応の取っ手（ホストが発行する不透明な値。状態のハッシュ・乱数の確認値・決定の通し番号ではない） | ホスト |
| `status` | 状態の区分（diagnostics.status_of と同じ語彙） | 公開 |
| `completeness` | complete・partial・undetermined | 契約 |
| `scope` | 含めた候補の種類（partial の理由のコードを含む） | 契約 |
| `candidates` | 候補の並び（id・kind・source・inputs・processability・reasons）。並びは公開の値の順（カードは observe の並び、種類は OPERATIONS の順） | 本人の知識と公開 |
<!-- generated:response end -->

候補の項目:

<!-- generated:candidate begin -->
| 項目 | 意味 |
|---|---|
| `id` | 応答の中だけの候補の番号（c1, c2, …。並びの順。秘密の値から作らない） |
| `kind` | 操作の種類（OPERATIONS の kind） |
| `source` | 操作に使うもの（本人に見えるカードの uid・場のポケモンの番号・ワザの位置。見えないカードの uid は入れない） |
| `inputs` | 必要な入力の段（INPUT_KINDS。段ごとに種類・制約・選べるもの）。after_acceptance の段は受理のあとの決定で尋ねる |
| `processability` | PROCESSABILITY の 1 つ |
| `reasons` | 理由のコード（決まった語彙。文は表示の側がコードから作る。実行時の例外の文・カードの位置を入れない） |
<!-- generated:candidate end -->

完全性:

<!-- generated:completeness begin -->
| 区分 | 意味 |
|---|---|
| `complete` | 契約の範囲（その段階の候補の種類）で、本人に提示できる候補をすべて含む |
| `partial` | 一部だけを含む（上限・初版の範囲の外）。理由のコードと、含めた種類を示す |
| `undetermined` | 完全かどうかを決められない（判定未確定の候補を含むなど） |
<!-- generated:completeness end -->

**初版で保証しないこと**: main（番の操作）の候補の完全性（初版は `partial` と含めた種類を返す）、候補に載った操作の受理（最終の判定は `apply_command`）、受理のあとの全分岐の完走（`may_stop_later`）、候補の応答を保存して別の実装・別の状態で使うこと。

## 6. 処理可能性

ゲーム上の合法性と、エンジンが扱えることを分けます。どの区分も候補から消しません（P-NOT-HIDDEN）。

<!-- generated:processability begin -->
| 区分 | 意味 | 表示 | 実行の候補 | 決め方 |
|---|---|---|---|---|
| `supported` | 今の規約集合と実装で、宣言の前の確かめが扱える（そのあとの分岐の完走は保証しない） | 表示 | はい | 本人の知識と公開の情報だけで決まる確かめ |
| `may_stop_later` | 受理のあと、条件しだいで研究上の停止・エンジンの未対応で止まりうる（止まるかは秘密の情報・コイン・相手の選択による） | 表示（止まりうる注意） | はい | カードの登録が宣言する停止の可能性（UNRESOLVED の場面の索引）。実際の配分を読まない |
| `unresolved_ruling` | 記録で決まらない裁定のため、今の規約集合では処理できない（研究上の未解決） | 表示（実行できない。ゲーム上の禁止ではない） | いいえ | 診断のコード表の分類（未裁定）と、状態の規約集合の続行規約の参照 |
| `not_implemented` | エンジンが未対応（研究上の未解決とは別） | 表示（実行できない。ゲーム上の禁止ではない） | いいえ | 診断のコード表の分類（未対応） |
| `technical_limit` | 先読み・読み方の組などの上限を超える（MAX_BRANCHES・COLOR_READINGS_LIMIT など） | 表示（実行できない理由として） | いいえ | 上限が公開の情報だけで決まるときだけ。秘密の配分で決まる上限は unverified |
| `unverified` | 候補の作成の時点で、本人の知識から処理可能性を決められない（判定未確定） | 表示（送れば apply_command が判定する） | はい | 上のどれにも決められないとき。拒否されても理由は双子で同じ（v0.135 以後の拒否の検査） |
<!-- generated:processability end -->

3 つの規約集合（`CS-KYUURA-CURRENT@1`・`CS-KYUURA-PLAY-S2A@1`・`CS-KYUURA-PLAY-PO@1`）の違いは、状態の規約集合の続行規約の参照（`conventions.continuation_for`・診断のコード表）から受け取ります。同じ盤面でも集合によって `unresolved_ruling` と `supported` が分かれえます。モードの名前・カードの ID の分岐は加えません（カード固有の入力はカードの登録が宣言する）。

## 7. 情報境界

<!-- generated:boundary begin -->
| 経路 | 規則 |
|---|---|
| `count` | 候補の数・選べるものの数は、本人の知識と公開の情報だけで決まる |
| `order` | 並びは公開の値の順（uid の順で山札の中身を伝えない） |
| `missing` | 候補を落とすかは本人の知識だけで決まる。決められないものは落とさず unverified にする |
| `reason` | 理由は決まった語彙のコード。双子で同じ |
| `identifier` | 候補の番号は並びの順。見えないカードの uid・秘密の値から作った識別を入れない |
| `invalid_query` | 不正な入力（知らない候補・見えないカード・範囲の外の数）を試す問い合わせも、決まったエラーで答え、秘密の情報で変わらない |
| `started_search` | 正当に始まった山札の検索（DECK_REVEALING_KINDS の決定）の選択肢だけは、実際の山札による。始まっていない検索の候補に実際の山札を使わない |
| `other_viewers` | 本人の候補を相手・観戦者に配らない（ホストの責任） |
| `verifier_data` | 検証者用の記録・スナップショット・確認値を応答に使わない |
<!-- generated:boundary end -->

本人の知識から導ける情報と、実際の秘密の状態を参照した情報の区別:

<!-- generated:knowledge begin -->
| 情報の元 | 意味 | 使ってよい |
|---|---|---|
| `public` | 全員に見える情報（観測の公開の項目） | いつも |
| `actor_knowledge` | 本人が知る情報（自分の手札・デッキリスト・所有するカードの多重集合・見たカード） | いつも |
| `started_search` | 正当に始まった検索で本人が見ているカード（決定の選べるもの） | その決定の入力だけ |
| `secret` | 本人が知らない配分（山札・サイドの並び、相手の手札） | 使わない |
<!-- generated:knowledge end -->

契約: 同じ本人の知識と公開の情報を持つ双子の状態では、候補の一覧・数・並び・理由・入力の制約・完全性から、秘密の配分を区別できない（例外は、正当に始まった山札の検索の決定の選択肢だけ）。検査は v0.135 の `twin_command_problems`（v0.137 の `owner_knowledge`）と同じ前提の双子で、応答そのものを比べます。

漏れの回帰テスト:

<!-- generated:leak-tests begin -->
| ID | 確かめること |
|---|---|
| `T-TWIN-RESPONSE` | 持ち主の知識が同じで山札・サイドの配分だけが違う双子（twin_command_problems の owner_knowledge と同じ前提）で、各操作主体の応答（候補・数・並び・理由・入力の制約・completeness）が同じ |
| `T-TWIN-REFINE` | 双子で、段階的な入力の問い合わせ（正しい入力・不正な入力）の答えが同じ |
| `T-STARTED-SEARCH` | 山札の検索が始まったあとの決定の選択肢は実際の山札による（双子で違ってよい）。始まる前の候補は同じ |
| `T-NO-SIDE-EFFECT` | 候補を何度取っても、状態・乱数・ログ・決定の通し番号が変わらない |
| `T-OTHER-ACTOR` | 相手・観戦者として問い合わせても、本人の候補・選べるもの・数が出ない |
| `T-STALE` | 古い・別の対戦・別の操作主体の取っ手を拒み、拒否の答えが秘密の情報で変わらない |
| `T-NOT-HIDDEN` | 未裁定・未対応の操作は候補から消えず、processability で表される |
| `T-NO-VERIFIER` | 応答に検証者用の値（確認値・seed・乱数・スナップショットの鍵）が入らない（閲覧用記録と同じ入ってはいけない項目の検査） |
<!-- generated:leak-tests end -->

## 8. 状態との対応とホストの責任

<!-- generated:revision begin -->
- 元: `host_token`（使わない元: `state_hash`・`rng_check`・`decision_id`・`log_length`・`record_identity`）
- 方式: ホストが対戦・操作主体ごとに不透明な取っ手（乱数の 128 ビットの値）を発行し、ホストの中で（対戦, 操作主体, 状態の内部の版）と対応づける。受理した操作（どのプレイヤーの操作でも）で、その対戦の取っ手はすべて古くなる。拒否は状態を変えないので取っ手を変えない
- 注: 取っ手を使わない直接のコマンドの送信（今の submit）は、そのまま使える。取っ手の確かめはホストの段で、エンジンに渡す前。受理するかの判定は apply_command

| 場合 | 拒否のコード | 次 |
|---|---|---|
| 古い取っ手（状態が変わった） | `CANDIDATES_STALE` | 候補を取り直す |
| 別の対戦の取っ手 | `CANDIDATES_WRONG_GAME` | その対戦の候補を取る |
| 別の操作主体の取っ手 | `CANDIDATES_WRONG_ACTOR` | 自分の候補を取る（他人の候補の中身を答えない） |
| 知らない候補・入力 | `CANDIDATE_UNKNOWN` | 候補を取り直す（理由は決まった文） |
<!-- generated:revision end -->

流れ: 本人が候補を取る（`game`・`revision` つき）→ 入力を選んでコマンドを作り、取っ手と一緒に送る → ホストが取っ手を確かめる（古い・別の対戦・別の主体なら拒否して取り直しを促す）→ `apply_command` が最終の判定 → 受理ならその対戦の取っ手はすべて古くなる。

ホストの責任:

<!-- generated:host begin -->
- 操作主体の認証（ログイン・接続）と権限の確かめ。API はホストが確かめた操作主体を受け取り、要求に書かれたプレイヤーの番号を信じない
- 応答を本人だけに渡す（相手・観戦者・記録に入れない）
- 取っ手（game・revision）の発行・対応づけ・失効
- ホストの操作（ジャンケンの結果・延長戦の開始）は、ホストの操作主体だけに候補として出す
<!-- generated:host end -->

## 9. 判断事項（利用者の判断が要る）

<!-- generated:decisions begin -->
| ID | 問い | 推奨 | 状態 | 採用・確かめの結果 |
|---|---|---|---|---|
| `D-U7-API` | 入口の形（HostedGame.legal_actions(actor) と、状態を受け取る関数 legal_actions(state, actor) を両方にするか） | ホストの入口を正とし、状態を受け取る関数はホストの中とテストだけ（取っ手を持たない） | adopted（ADOPT-U7-1） | ホストの入口（ActionHost）とクライアントの入口（ActorSession）を分ける。状態を受け取る公開の関数は作らない |
| `D-U7-TOKEN` | revision を乱数の不透明な値にするか、ホストの中の数（受理の数）を外に出すか | 不透明な値（受理の数は相手の見えない操作の数を伝えうる） | adopted（ADOPT-U7-1） | secrets の乱数の不透明な値（エンジンの乱数・状態のハッシュ・決定の番号を使わない） |
| `D-U7-REFINE` | 段階的な入力を、問い合わせ（refine）で次の段を取る形にするか、候補に全段の制約を書く形にするか | 初版は候補に段の制約を書く（ワザの対象・トレーナーの枚数は受理のあとの決定）。問い合わせは U7-4 で必要になったときに加える | adopted（ADOPT-U7-1） | 段階的に取得する（候補の一覧は段の種類だけ、選べるものと制約は inputs の問い合わせ） |
| `D-U7-DISPLAY` | 処理可能性ごとの表示・実行の扱い（PROCESSABILITY の表） | 表のとおり。どれも候補から消さない | pending |  |
| `D-U7-UNVERIFIED` | 判定未確定（unverified）の候補を実行できる候補にするか | する（送れば apply_command が判定する。拒否の理由は双子で同じ） | adopted（ADOPT-U7-1） | unverified は保証がないことを示して送信を許す |
| `D-U7-COMPLETENESS` | 初版で main の候補を complete と称する範囲 | 称さない（partial と scope）。決定・準備・延長戦の開始・終局・停止だけ complete | pending |  |
| `D-U7-HOST-OPS` | ジャンケンの結果・延長戦の開始をホストの操作主体の候補にするか | する（プレイヤーの候補には出さない） | adopted（ADOPT-U7-1） | 操作主体のある操作とホストの操作を区別する（プレイヤーには waiting_for_host を返す）。ホストの操作の入口は U7-2 |
| `D-U7-DECISION-UID` | 決定の選べるもの（observe の decision.options の value）に、決める人に見えないカードの uid が入る種類があるか | U7-1 の前に確かめる（未確認）。入るなら、U7 の応答では見えないカードを値の番号で表し、uid を入れない | checked | v0.160 の補完で種類ごとに options の式を調べ直した（docs/legal-actions-u7-1.md 2 章）。見えないカードの uid が入る種類は見つからない。情報境界を確かめた種類だけ入力を返し、確かめていない種類（unconfirmed）と、実行時に見えないカードが選べるものに来た場面は、選べるもの・数・並びを返さない（INPUT_BOUNDARY_UNCONFIRMED）。番号に置きかえるだけでは数・並びの漏れが消えないため |
<!-- generated:decisions end -->

## 10. 検証と未確認

- `python scripts/build_legal_actions_api_design.py --check`: JSON と生成区画の一致、コードの語彙（コマンドの型・段階・next・状態の区分・決定の意味）の対応、原則に反する値（main を complete と称する・候補を表示しない処理可能性・状態のハッシュを revision にする・情報境界の経路の欠け）
- テスト `tests/test_legal_actions_api_design.py`: 上の確かめを、わざと壊した値で見つけることを確かめる
- 確かめていないこと: 決定の種類のうち情報境界が unconfirmed のもの（docs/legal-actions-u7-1.md 2 章の表。U7 は入力を返さない）、候補の作成の費用、GUI の表示
