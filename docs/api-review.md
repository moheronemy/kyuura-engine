# 公開 API のレビュー（v0.1）

将来、CLI・GUI・Web API・AI プレイヤー・ほかの言語のクライアントから使うことを想定して、v0.1 の公開 API を評価したものです。**この文書は提案だけで、ここに書いた変更はまだしていません**（このレビューで直したのは [v0.1 のレビュー](review-v0.1.md) の「修正」の項目だけ）。

## 1. 今の使い方

```python
state = new_game(deck0, deck1, seed)            # 対戦準備（切り直しまで）
state = apply_command(state, command)            # 1 手ずつ。新しい状態を返す。渡した状態は変えない
data = state_to_dict(state)                      # JSON にできる辞書（隠れた情報も含む）
command = command_from_dict({"type": "end_turn", "player": 0})
```

対戦の記録は「デッキ 2 つ・seed・コマンドの列」（とエンジンの版・kyuura のコミット）で十分です。同じものからは同じ状態になります（Python 3.11〜3.13 で確認）。状態を辞書からもどす関数（`state_from_dict`）はありません。

## 2. 公開すべきもの・内部として隠すべきもの

| もの | 今 | 分類 | 理由・提案 |
|---|---|---|---|
| `new_game` | 公開 | **公開** | 対戦の入口。`rules`・`pool` の引数は、既知のルールの組・検証したカードの組だけを受け付けるようにしたい（L10） |
| `apply_command` | 公開 | **公開** | 状態遷移の唯一の入口。返す状態は必ず不変条件で確かめる |
| コマンドの dataclass（`PlaceStartingPokemon` など） | 公開 | **公開** | 操作の表現。項目は整数（uid）と整数のタプルだけ。リストは受け付けない（`BAD_COMMAND`） |
| `command_from_dict`・`command_to_dict` | 公開 | **公開** | 他言語・Web との境界。JSON の形（`type` と各項目）を文書にして固定したい |
| `state_to_dict` | 公開 | **公開**（形を固定する） | 画面・他言語に渡す形。今は隠れた情報をすべて含むので、見る人ごとに絞る版が要る（M6） |
| `GameState` の読み取り（`phase`・`current_player`・`turn_number`・`result`・`halt`・各ゾーン） | 公開（書き換えもできる） | **読み取りだけ公開** | 今は可変の dataclass なので、呼び出し側が書き換えられる（書き換えた状態は `StateIntegrityError` になることがある）。読み取り専用の見え方を用意したい |
| `GameState.rng`・`clone()`・`add_event()` | 公開 | **内部** | 乱数を外から進めると再現性が崩れる。`clone()` は `apply_command` が使う。`add_event()` はエンジンだけが使う |
| `GameState.pending_prizes`・`pending_promotions`・`mulligan_rounds` | 公開 | **内部**（読み取りは別の形で） | 「次に誰が何を決めるか」を一般化した読み取り用の情報に置き換えたい（3.2） |
| `PlayerState`・`PokemonInPlay` | 公開（可変） | **内部**（読み取り専用の見え方を公開） | リストを直接書き換えられる |
| `CardInstance`・`DataSource`・`Halt`・`GameResult` | 公開（frozen） | **公開** | 変えられない値。`GameResult.outcome` は文字列なので Enum にしたい |
| `Phase` | 公開 | **公開** | `TERMINAL_PHASES` も公開したい（3.3） |
| `CardDefinition`・`Attack`・`EnergyType`・`can_pay_cost` | 公開 | **公開**（読み取り） | 画面の表示・AI の判断に使う |
| `load_card_pool`・`CardPool` | 公開 | **公開**（読み取り） | 結果は読み取り専用（このレビューで直した） |
| `classify_record`・`pool_from_extract`・`read_extract`・`read_verification` | モジュールから import できる | **内部** | データの読み込みと分類の道具 |
| `deck_problems`・`validate_deck`・`expand_decklist` | 公開 | **公開** | デッキの編集画面で使う。問題点は文字列ではなく（コード, カード id, 説明）の組にしたい（L9） |
| `check_invariants` | 公開 | **公開**（検査用） | テスト・不具合の調査に使う |
| 例外（`EngineError` と `code`） | 公開 | **公開** | コードの一覧を文書にして固定する（4 章） |
| `RuleSet`・`RULES_2000_02_14`・`RULE_REFERENCES` | 公開 | **公開**（読み取り） | `RULE_REFERENCES` は docs と二重管理（L8） |
| `engine._*`・`judge`・`damage` | 内部（`_` 付き・モジュール） | **内部** | `judge.decide`・`calculate_attack_damage` は純粋な関数なので、テストからは使ってよい |

## 3. 提案（今回は変更しない）

### 3.1 状態を書き換えられないようにする

`GameState`・`PlayerState`・`PokemonInPlay` は可変です。`apply_command` は複製してから処理するので、呼び出し側が古い状態を持っていても壊れませんが、呼び出し側が状態を直接書き換えることは防げません。読み取り専用の見え方（例: `state.view()` がタプルと frozen dataclass だけを返す）を公開し、可変の本体は内部にすることを提案します。

`GameState` の `==` は乱数のオブジェクトの同一性を比べるので、同じ内容でも `False` です（L7）。比べるときは `state_to_dict` を使ってください。

### 3.2 次に誰が何を決めるか

今は、段階（`phase`）と `current_player`・`pending_prizes`・`pending_promotions`・`placed_starting_pokemon`・`mulligan_draws_remaining` を組み合わせないと、次に操作するプレイヤーが分かりません。対戦準備では 2 人とも操作できます。次のような読み取り用の関数を提案します。

- `awaiting(state) -> list[(player, 決定の種類)]`: 今、操作を待っているプレイヤーと、その種類
- `legal_commands(state, player) -> list[Command]`: 今送れる合法なコマンド（AI・画面の土台）

効果の途中の選択（コイン・対象の選択）も同じ「保留中の決定」で表すと、段階を増やさずに済みます（M4）。

### 3.3 終わったかどうか

`GAME_OVER`・`SUDDEN_DEATH` は `result` を持ちますが、`HALTED` は `result` が `None` で `halt` を持ちます。`TERMINAL_PHASES` を公開するか、`is_terminal(state)` を用意することを提案します（L15）。HALTED は終端で、再開する API はありません。

### 3.4 隠れた情報とプレイヤーの権限

- `state_to_dict(state, viewer=0)` のように、見る人ごとに、相手の手札・山札の順番・サイドの中身を伏せた形を用意する。ログの `draw`・`take_prize`・`mulligan` も、見る人によって伏せる部分がある。
- コマンドには「プレイヤーの操作」と「外からの入力」（`ReportJankenResult`）があります。Web API では、コマンドの `player` と接続しているプレイヤーが同じかを確かめる層と、外からの入力を受け付ける層を分けてください。

### 3.5 場のポケモンの識別子

コマンドとログは、場のポケモンを「そのポケモンのカードの uid」で指します。進化すると一番上のカードが変わるので、場に出たときに決まる識別子（例: 最初のカードの uid を使い続ける、または別の番号）にすることを提案します（M3）。

### 3.6 デッキの問題点・ルールの組

- `DeckValidationError.problems` を `(code, card_id, message)` の組にする（L9）。
- `new_game(rules=...)` は既知のルールの組（今は 2000.02.14版だけ）を id で選ぶ形にし、値を書き換えた `RuleSet` を受け付けない（L10）。

### 3.7 性能

`apply_command` は毎回、不変条件を検査します（1 手あたり約 110µs のうち約 67µs）。AI の大量のシミュレーションでは、検査を外す選択肢（既定は検査する）を用意することを提案します。ログを tuple の連結で伸ばす処理も、局が長くなると遅くなります（L11）。

### 3.8 型

コマンドの型の検査は、型注釈が文字列であることに頼っています（L6）。JSON との変換の仕様（項目名・型）を別に定義すると、他言語のクライアントもそれに合わせられます。

## 4. 今のエラーコード

`EngineError.code` の値です（v0.1）。

| 例外 | コード |
|---|---|
| `IllegalActionError` | ALREADY_PLACED, BAD_COMMAND, BENCH_FULL, CARD_NOT_IN_HAND, DUPLICATE_CARD, ENERGY_ALREADY_ATTACHED, ENERGY_NOT_ATTACHED, GAME_OVER, INSUFFICIENT_ENERGY, INVALID_ATTACK, INVALID_DRAW_COUNT, INVALID_PLAYER, INVALID_PRIZE_INDEX, NOT_BASIC_ENERGY, NOT_BASIC_POKEMON, NOT_ON_BENCH, NOT_YOUR_DECISION, NOT_YOUR_TURN, NO_BENCH, NO_MULLIGAN_DRAW, SETUP_BENCH_LIMIT, TARGET_NOT_IN_PLAY, TARGET_NOT_YOURS, UNKNOWN_COMMAND, WRONG_PHASE, WRONG_RETREAT_COST |
| `UnsupportedError` | SUDDEN_DEATH_NOT_IMPLEMENTED, UNRESOLVED_MULLIGAN_COMPENSATION, UNSUPPORTED_ACTION, UNSUPPORTED_ATTACK |
| `DeckValidationError` | INVALID_DECK（`problems` の各行の先頭: DECK_SIZE, UNKNOWN_CARD, UNSUPPORTED_CARD, TOO_MANY_COPIES, NO_BASIC_POKEMON） |
| `StateIntegrityError` | STATE_INTEGRITY（エンジンの不具合か、呼び出し側が状態を書き換えた） |

## 5. 今のログのイベント

`state.log` の各要素は読み取り専用の辞書で、`kind` と `turn`（その時点の番数）を持ちます。

`game_created`, `shuffle`, `draw`, `mulligan`（見せた手札）, `halted`, `place_starting_pokemon`, `set_prizes`, `mulligan_draw`, `janken`, `reveal_pokemon`, `turn_start`, `deck_out`, `play_to_bench`, `attach_energy`, `retreat`, `attack`, `damage`（計算の段階を含む）, `knock_out`, `take_prize`, `promote_active`, `end_turn_without_attack`, `turn_end`, `pokemon_check`, `game_end`

ログはテストでも使っているので、事実上の API です。種類と各項目を変えるときは、この一覧と test_reproducibility.py の固定値を合わせて更新してください。
