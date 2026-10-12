# 公開 API のレビュー（v0.1・v0.2a）

将来、CLI・GUI・Web API・AI プレイヤー・ほかの言語のクライアントから使うことを想定して、公開 API を評価したものです。v0.1 のレビューで書いた提案のうち、v0.2a で実装したものと、まだ提案のままのものを分けて書いています。構造の説明は [v0.2a のアーキテクチャ](architecture-v0.2a.md) にあります。

## 1. 今の使い方

```python
state = new_game(deck0, deck1, seed)                 # 対戦準備（切り直しまで）
state = apply_command(state, command)                 # 1 手ずつ。新しい状態を返す。渡した状態は変えない
if state.decision is not None:                        # 決定を待っている（v0.2a）
    d = state.decision                                # 誰が（d.player）、何を（d.kind）、どれから（d.options）選ぶか
    state = apply_command(state, ResolveDecision(d.player, d.id, (d.options[0],)))
data = state_to_dict(state)                           # JSON にできる辞書（形式 1。隠れた情報も含む）
data2 = state_to_dict(state, format_version=2)        # 形式 2（場のポケモンの番号・決定などを加えた）
command = command_from_dict({"type": "end_turn", "player": 0})
```

対戦の記録は「デッキ 2 つ・seed・コマンドの列」（とエンジンの版・kyuura のコミット・効果の登録表の id）で十分です。同じものからは同じ状態になります（Python 3.11〜3.13 で確認）。状態を辞書からもどす関数（`state_from_dict`）はありません（[アーキテクチャ 6 章](architecture-v0.2a.md#6-乱数)）。

## 2. v0.2a で加えた公開 API

| もの | 内容 |
|---|---|
| `ResolveDecision(player, decision, choices)` | 保留中の決定に答えるコマンド。どの種類の決定にも使える。JSON の `type` は `resolve_decision` |
| `PendingDecision` | 保留中の決定（`GameState.decision`）。`id`・`kind`・`player`・`options`・`min_choices`・`max_choices`・`resume`・`context` |
| `GameState.decision`・`next_decision_id` | 今の決定（なければ `None`）と、次に付ける決定の番号 |
| `PokemonInPlay.pokemon_id`・`GameState.next_pokemon_id`・`GameState.find_pokemon(pokemon_id)` | 場のポケモンの番号。カードの uid とは別 |
| `Phase.DECISION` | v0.1 からある 2 つ以外の決定を待つ段階 |
| `TERMINAL_PHASES` | 終わった段階（GAME_OVER・SUDDEN_DEATH・HALTED）。v0.1 のレビューの提案（3.3）を実装 |
| `EffectRegistry`・`DEFAULT_EFFECTS`・`AttackKey` | 効果の登録表。`CardPool.effects`・`GameState.effects` |
| `state_to_dict(state, format_version=2)` | 形式 2。既定は形式 1（v0.1 と同じ） |
| `kyuura_engine.rng`（`rng_fingerprint`・`rng_state_to_json`・`rng_from_json`・`copy_rng`） | 乱数の状態の指紋と、保存・復元 |
| エラーコード | `WRONG_DECISION`・`INVALID_CHOICE`・`INVALID_CHOICE_COUNT`・`DUPLICATE_CHOICE`（4 章） |

## 3. 公開すべきもの・内部として隠すべきもの

| もの | 今 | 分類 | 理由・提案 |
|---|---|---|---|
| `new_game` | 公開 | **公開** | 対戦の入口。`rules`・`pool` の引数は、既知のルールの組・検証したカードの組だけを受け付けるようにしたい（L10） |
| `apply_command` | 公開 | **公開** | 状態遷移の唯一の入口。返す状態は必ず不変条件で確かめる |
| コマンドの dataclass（`PlaceStartingPokemon` など、`ResolveDecision`） | 公開 | **公開** | 操作の表現。項目は整数（uid・番号）と整数のタプルだけ。リストは受け付けない（`BAD_COMMAND`） |
| `command_from_dict`・`command_to_dict` | 公開 | **公開** | 他言語・Web との境界。JSON の形（`type` と各項目）を文書にして固定したい |
| `state_to_dict` | 公開 | **公開**（形式ごとに固定する） | 形式 1 は v0.1 と同じに固定。形式 2 は v0.2a で加えた。どちらも内部の完全な状態で、見る人ごとに絞る形が要る（M6、[アーキテクチャ 8 章](architecture-v0.2a.md#8-非公開の情報方針未実装)） |
| `GameState` の読み取り（`phase`・`current_player`・`turn_number`・`result`・`halt`・`decision`・各ゾーン） | 公開（書き換えもできる） | **読み取りだけ公開** | 可変の dataclass なので、呼び出し側が書き換えられる（書き換えた状態は `StateIntegrityError` になることがある）。読み取り専用の見え方を用意したい |
| `GameState(...)` を直接作る | できる（v0.2a から `effects` が必要） | **内部** | 正式な入口は `new_game`。テストの `build_test_state` だけが直接作る |
| `GameState.rng`・`clone()`・`add_event()` | 公開 | **内部** | 乱数を外から進めると再現性が崩れる。`clone()` は `apply_command` が使う。`add_event()` はエンジンだけが使う |
| `GameState.pending_prizes`・`pending_promotions` | 読み取り専用の値（v0.2a。決定から作る） | **互換のためだけに残す** | 新しいコードは `decision` を見る |
| `GameState.mulligan_rounds` | 公開 | **読み取りだけ公開** | 切り直しの経過（HALTED の理由の説明に使う） |
| `PendingDecision` | 公開（frozen） | **公開** | 画面・AI が「何を選ぶか」を知るための情報。`resume`・`context` はエンジンの続きの情報なので、クライアントは読まなくてよい |
| `PlayerState`・`PokemonInPlay` | 公開（可変） | **内部**（読み取り専用の見え方を公開） | リストを直接書き換えられる |
| `CardInstance`・`DataSource`・`Halt`・`GameResult` | 公開（frozen） | **公開** | 変えられない値。`GameResult.outcome` は文字列なので Enum にしたい |
| `Phase`・`TERMINAL_PHASES` | 公開 | **公開** | 決定を待つ段階は `decisions.DECISION_PHASES` |
| `CardDefinition`・`Attack`・`EnergyType`・`can_pay_cost` | 公開 | **公開**（読み取り） | 画面の表示・AI の判断に使う。`supported` は、そのプールの登録表での分類 |
| `load_card_pool`・`CardPool` | 公開 | **公開**（読み取り） | 結果は読み取り専用。`CardPool.effects` は分類に使った登録表 |
| `EffectRegistry`・`DEFAULT_EFFECTS`・`AttackKey` | 公開 | **公開**（読み取り。登録は実装を加える人向け） | どのワザが使えるかの根拠。`with_attacks`・`without_attacks` は新しい登録表を作る（元は変えない） |
| `AttackEffect`・`DamageOnly`・`AttackEntry`・`AttackUse` | `kyuura_engine.effects` | **公開（実装を加える人向け）** | カードの効果を実装するときの型 |
| `decisions.push_decision`・`push_attack_decision`・`check_choices` | `kyuura_engine.decisions` | **内部（エンジンと効果の実装向け）** | クライアントは使わない。決定に答えるのは `ResolveDecision` |
| `classify_record`・`pool_from_extract`・`read_extract`・`read_verification` | モジュールから import できる | **内部** | データの読み込みと分類の道具 |
| `deck_problems`・`validate_deck`・`expand_decklist` | 公開 | **公開** | デッキの編集画面で使う。問題点は文字列ではなく（コード, カード id, 説明）の組にしたい（L9） |
| `check_invariants` | 公開 | **公開**（検査用） | テスト・不具合の調査に使う |
| 例外（`EngineError` と `code`） | 公開 | **公開** | コードの一覧を固定する（4 章） |
| `RuleSet`・`RULES_2000_02_14`・`RULE_REFERENCES` | 公開 | **公開**（読み取り） | `RULE_REFERENCES` は docs と二重管理（L8） |
| `kyuura_engine.rng` | モジュール | **公開**（保存・比較用） | 乱数を進める関数は持たない |
| `engine._*`・`judge`・`damage` | 内部（`_` 付き・モジュール） | **内部** | `judge.decide`・`calculate_attack_damage` は純粋な関数なので、テストからは使ってよい |

## 4. 互換性と移行（v0.1 → v0.2a）

- 対戦の結果（v0.1 の 15 の場面の再生）・固定値・形式 1 の状態の辞書・ログ・v0.1 のコマンドは変わりません（[アーキテクチャ 9 章](architecture-v0.2a.md#9-互換性)）。
- 互換でない変更と移行の方法は、[アーキテクチャ 9 章の表](architecture-v0.2a.md#api-の変更互換でないもの) にまとめました。主なもの:
  - `GameState` を直接作るには `effects` が必要
  - `pending_prizes`・`pending_promotions` は読み取り専用
  - カードの分類は登録表で決まる（未対応の理由の文言が変わった）
  - `Phase.DECISION` が加わった
- 新しいクライアントへの推奨:
  - 決定は `state.decision` を見て `ResolveDecision` で答える。
  - 場のポケモンは `pokemon_id` で追う。
  - 状態の辞書は形式 2 を使う。
  - `TakePrize`・`PromoteActive`（カードの uid）は、v0.1 との互換のために残しています。

## 5. 提案（まだ実装していない）

### 5.1 状態を書き換えられないようにする

`GameState`・`PlayerState`・`PokemonInPlay` は可変です。`apply_command` は複製してから処理するので、呼び出し側が古い状態を持っていても壊れませんが、呼び出し側が状態を直接書き換えることは防げません。読み取り専用の見え方（例: `state.view()` がタプルと frozen dataclass だけを返す）を公開し、可変の本体は内部にすることを提案します。

`GameState` の `==` は乱数のオブジェクトの同一性を比べるので、同じ内容でも `False` です（L7）。比べるときは `state_to_dict` を使ってください。

### 5.2 次に誰が何を決めるか

v0.2a で、ワザの途中・きぜつのあとの決定は `state.decision` に一本化しました。まだ一本化していないのは、対戦準備（`PlaceStartingPokemon`・`DrawMulliganCards`・`ReportJankenResult`）と、番の途中の操作（`MAIN`）です。対戦準備は 2 人が同時に操作できるため、1 つの決定では表せません。次のような読み取り用の関数を提案します。

- `awaiting(state) -> list[(player, 操作の種類)]`: 今、操作を待っているプレイヤーと、その種類（決定・対戦準備・番の操作）
- `legal_commands(state, player) -> list[Command]`: 今送れる合法なコマンド（AI・画面の土台）。決定は `options` から作れる

### 5.3 隠れた情報とプレイヤーの権限

- 見る人ごとの形（`view(state, viewer)`。viewer はプレイヤー 0・1・観戦者）を加える。ログの `draw`・`take_prize` なども、見る人によって伏せる部分がある（[アーキテクチャ 8 章](architecture-v0.2a.md#8-非公開の情報方針未実装)）。
- コマンドには「プレイヤーの操作」と「外からの入力」（`ReportJankenResult`）があります。Web API では、次の 2 つを分けてください。
  - コマンドの `player`（`ResolveDecision` なら決定の `player`）と、接続しているプレイヤーが同じかを確かめる層
  - 外からの入力を受け付ける層

### 5.4 場のポケモンの識別子の移行

v0.1 からあるコマンドは、場のポケモンをカードの uid で指します。v0.2a で場のポケモンの番号（`pokemon_id`）を加え、`ResolveDecision` の選べるものは番号になりました。進化を実装するときの移行の手順は [アーキテクチャ 5 章](architecture-v0.2a.md#コマンドの移行の方針) にあります。

### 5.5 デッキの問題点・ルールの組

- `DeckValidationError.problems` を `(code, card_id, message)` の組にする（L9）。
- `new_game(rules=...)` は既知のルールの組（今は 2000.02.14版だけ）を id で選ぶ形にし、値を書き換えた `RuleSet` を受け付けない（L10）。

### 5.6 性能

`apply_command` は毎回、不変条件を検査します（1 手あたり約 110µs のうち約 67µs。v0.1 のレビューの測定）。AI の大量のシミュレーションでは、検査を外す選択肢（既定は検査する）を用意することを提案します。ログを tuple の連結で伸ばす処理も、局が長くなると遅くなります（L11）。

### 5.7 型

コマンドの型の検査は、型注釈が文字列であることに頼っています（L6）。JSON との変換の仕様（項目名・型）を別に定義すると、他言語のクライアントもそれに合わせられます。

## 6. エラーコード

`EngineError.code` の値です。

| 例外 | コード |
|---|---|
| `IllegalActionError` | ALREADY_PLACED, BAD_COMMAND, BENCH_FULL, CARD_NOT_IN_HAND, DUPLICATE_CARD, DUPLICATE_CHOICE（v0.2a）, ENERGY_ALREADY_ATTACHED, ENERGY_NOT_ATTACHED, GAME_OVER, INSUFFICIENT_ENERGY, INVALID_ATTACK, INVALID_CHOICE（v0.2a）, INVALID_CHOICE_COUNT（v0.2a）, INVALID_DRAW_COUNT, INVALID_PLAYER, INVALID_PRIZE_INDEX, NOT_BASIC_ENERGY, NOT_BASIC_POKEMON, NOT_ON_BENCH, NOT_YOUR_DECISION, NOT_YOUR_TURN, NO_BENCH, NO_MULLIGAN_DRAW, SETUP_BENCH_LIMIT, TARGET_NOT_IN_PLAY, TARGET_NOT_YOURS, UNKNOWN_COMMAND, WRONG_DECISION（v0.2a）, WRONG_PHASE, WRONG_RETREAT_COST |
| `UnsupportedError` | SUDDEN_DEATH_NOT_IMPLEMENTED, UNRESOLVED_MULLIGAN_COMPENSATION, UNSUPPORTED_ACTION, UNSUPPORTED_ATTACK |
| `DeckValidationError` | INVALID_DECK（`problems` の各行の先頭: DECK_SIZE, UNKNOWN_CARD, UNSUPPORTED_CARD, TOO_MANY_COPIES, NO_BASIC_POKEMON） |
| `StateIntegrityError` | STATE_INTEGRITY（エンジンの不具合か、呼び出し側が状態を書き換えた） |

## 7. ログのイベント

`state.log` の各要素は読み取り専用の辞書で、`kind` と `turn`（その時点の番数）を持ちます。v0.2a で、製品の処理が出すイベントは変わっていません（決定そのものはログに残さない）。

`game_created`, `shuffle`, `draw`, `mulligan`（見せた手札）, `halted`, `place_starting_pokemon`, `set_prizes`, `mulligan_draw`, `janken`, `reveal_pokemon`, `turn_start`, `deck_out`, `play_to_bench`, `attach_energy`, `retreat`, `attack`, `damage`（計算の段階を含む）, `knock_out`, `take_prize`, `promote_active`, `end_turn_without_attack`, `turn_end`, `pokemon_check`, `game_end`

ログはテストでも使っているので、事実上の API です。種類と各項目を変えるときは、この一覧、test_reproducibility.py の固定値、v0.1 の参照データ（tests/fixtures）との関係を合わせて見直してください。場のポケモンを指す項目は、今はカードの uid です（進化を実装するときに `pokemon_id` を加える予定）。
