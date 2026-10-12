# v0.2b のアーキテクチャ（トレーナーカード）

v0.2b は、v0.2a の土台（効果の登録表・保留中の決定・場のポケモンの番号）を使って、トレーナーカード 3 枚（マサキ・きずぐすり・ポケモンいれかえ）を実装した版です。原典の照合と、カードごとの裁定は [trainers-v0.2b.md](trainers-v0.2b.md) にあります。

> **その後の変更（v0.2c）**: ポケモンについて場に残るトレーナー（プラスパワー）のために、`PokemonInPlay.trainers`・番の終わりのトラッシュ・ダメージ計算の段階への効果の適用・状態の辞書の形式 4 を加えました（[v0.2c のアーキテクチャ](architecture-v0.2c.md)）。この文書は v0.2b の時点の記録です。

## 1. 目的と範囲

- トレーナーカードを使う処理（`PlayTrainer`）を、公式ルール p.310 の手順どおりに加える。
- v0.2a の効果の登録表・保留中の決定・場のポケモンの番号が、実際のカード効果で働くことを確かめる。
- 将来のトレーナーにも使える形にする。ただし、カード効果の汎用の記述言語（DSL）や、入れ子の実行環境は作らない。
- 原典で決められない場合は、推測で処理せず `UnsupportedError` で止める。確定している通常の場合は実装する。

対応したのは 3 枚だけです。ほかのトレーナー（プラスパワーなどのつけて使うもの、スタジアムを含む）は未対応のままです。

## 2. 変更の概要

| 項目 | v0.2a | v0.2b |
|---|---|---|
| 効果の登録表 | ワザだけ（`AttackKey` → `AttackEntry`） | トレーナーの欄を加えた（カード id → `TrainerEntry`）。登録表の id は `kyuura-engine-0.2b` |
| `PlayTrainer` | 未対応（`UNSUPPORTED_ACTION`） | 処理する（`engine._play_trainer`） |
| 決定 | サイド・交代（製品）、テスト専用のワザの決定 | トレーナーの対象の選択（`kind="select_pokemon"`、再開先 `"trainer"`）。原典で扱いを決められない選択（`unresolved_choices`） |
| 状態 | — | `GameState.trainer_in_use`（使っている最中のトレーナーカード） |
| 状態の辞書 | 形式 1・2 | 形式 3（`trainer_in_use` を加えた）。形式 1・2 は使用中のトレーナーがあると書き出さない（`ValueError`） |
| カードの分類 | トレーナーはすべて未対応 | 登録表に実装があり、名前・文面が登録したときと同じトレーナーだけ対応 |
| カードデータの写し | v0.1 のカード + 参照カード | トレーナー 3 枚（`pool_v0_2b`）と、参照カードのいいきずぐすり（PMCG1-075。実装を登録していないトレーナー）を加えた。参照カードだったきずぐすりは対戦用に移した |
| ルールの組 | — | `RuleSet.damage_per_counter = 10`（p.319） |

新しいファイル: `kyuura_engine/zones.py`（山札から引く処理。エンジンの番の最初のドローとマサキで共通）。

## 3. トレーナーの登録表

`effects.EffectRegistry` にトレーナーの欄を加えました（ワザの欄と同じ考え方）。

```python
TrainerEntry(
    effect,        # 実装（TrainerEffect）
    name_ja,       # 登録したときに照合した kyuura の写しの名前
    text_ja,       # 同じく、写しの文面（第1弾の印刷の転記。処理の根拠ではない）
    play_text_ja,  # 実装がしたがう文面（『オフィシャルブック2000』の最新の説明）
    source,        # play_text_ja の出典（"P43 p.254"）
)
```

- 識別子はカード id です。名前でも説明文の有無でもありません。同じ名前の別のカード（ジムシリーズの再録など）は、別に登録しないかぎり未対応です。
- `trainer_problem(definition)` は、登録がない・名前が違う・文面が違う・実装が扱えない種類（`trainer.kinds` がある）のときに理由を返します。文面の照合は、参照する kyuura のコミットを上げてデータが変わったときに気づくためです。
- 登録表は変えられません。`with_trainers`・`without_trainers`（と、ワザの `with_attacks`・`without_attacks`）は新しい登録表を返し、もう一方の欄をそのまま引き継ぎます。
- 登録表は対戦ごとに `GameState.effects` に入ります。テスト用の実装は、テスト用の登録表（`DEFAULT_EFFECTS.with_trainers(...)` で作り、`pool_from_extract`・`build_test_state` に渡す）にだけ入り、`DEFAULT_EFFECTS` には入りません（tests/test_trainers.py `test_registry_is_per_game_and_test_effects_stay_out_of_the_default`）。

### 実装の基底（`TrainerEffect`）

| メソッド | 役割 | 状態を変えるか |
|---|---|---|
| `check(definition)` | カードのデータがこの実装で扱える形か（登録の誤りを見つける） | — |
| `check_playable(state, use)` | 使えるか。「使うための条件」（p.310）を満たせないなら `IllegalActionError`、原典で決められないなら `UnsupportedError` | 変えない |
| `resolve(state, use)` | カードの説明にしたがう。決定が要るときは `push_trainer_decision` で決定を出して戻る | 変える |
| `resume(state, use, decision, choices)` | 決定のあとの続き。さらに決定を出してもよい | 変える |

手札から出す・相手に見せる（ログ）・トラッシュする・番にもどる、はエンジンが行います。実装はカードの説明の部分だけを持ちます。

v0.2b の実装: `DrawCards(count=2)`（マサキ）、`RemoveDamageCounters(counters=2)`（きずぐすり）、`SwitchWithBench()`（ポケモンいれかえ）。数値はカードごとの引数で、ほかのカード（「山札から○枚引く」など）にも使えます。ただし、使い回すときは、そのカードの最新の説明を確かめてから登録します。

## 4. `PlayTrainer` の処理の流れ

```
MAIN ──PlayTrainer(player, card)──▶ 検査（状態を変えない）
          1. 番のプレイヤーか・MAIN か（WRONG_PHASE / INVALID_PLAYER / NOT_YOUR_TURN）
          2. 手札にあるか（CARD_NOT_IN_HAND）
          3. トレーナーか（NOT_TRAINER）
          4. 登録表に実装があるか（UNSUPPORTED_TRAINER）
          5. check_playable（使うための条件 / UNRESOLVED_…）
      ──▶ 手札 → trainer_in_use、ログ play_trainer（名前を伝える。p.310 の手順 1・2）
      ──▶ resolve（手順 3・4）
            ├─ 決定なし ──▶ _finish_trainer: trainer_in_use → トラッシュ、ログ discard_trainer、MAIN
            └─ 決定あり ──▶ DECISION（decision.resume = "trainer"）
                              ──ResolveDecision──▶ 検査（NOT_YOUR_DECISION / WRONG_DECISION /
                                                   INVALID_CHOICE_COUNT / DUPLICATE_CHOICE / INVALID_CHOICE /
                                                   UNRESOLVED_…（unresolved_choices））
                              ──▶ resume
                                    ├─ さらに決定 ──▶ DECISION
                                    └─ 決定なし ──▶ _finish_trainer ──▶ MAIN
```

- 検査はすべて状態を変える前に行います。どこで拒否しても、`apply_command` は複製した状態で処理しているので、渡した状態は変わりません。
- 決定を待っている間（`Phase.DECISION`）は `ResolveDecision` だけを受け付けます。別のトレーナー・ワザ・エネルギー・にげる・番の終わりは `WRONG_PHASE` です（p.310「その…起こることをすべてすませてからでないと、他のことはできません」）。
- v0.2b のトレーナーは、きぜつ・勝敗を起こしません。使い終わったら必ず `MAIN` にもどります。きぜつを起こすトレーナーを加えるときは、`_finish_trainer` のあとにきぜつの判定を加えます（11 章）。

## 5. 保留中の決定との統合

- `decisions.push_trainer_decision(state, use, kind=..., player=..., options=..., unresolved_choices=...)` で決定を出します。再開先は `"trainer"`、続きの情報は `context` の `"use"`（プレイヤー、カードの uid、カード id）です。
- 対象のポケモンは場のポケモンの番号（`pokemon_id`）で選びます（`kind="select_pokemon"`）。きずぐすりは自分の場のポケモン、ポケモンいれかえは自分のベンチのポケモンです。相手のポケモン・存在しない番号は選べるものに入らないので `INVALID_CHOICE` です。
- 決定の番号（`decision.id`）は対戦の中で使い回しません。前のトレーナーの決定の番号で答えると `WRONG_DECISION`、答えたあとにもう一度送ると（決定がないので）`WRONG_PHASE` です。
- 選べるもののうち、原典で扱いを決められないもの（きずぐすりのダメージのないポケモン）は、`context` の `"unresolved_choices"` に入れます。それを選ぶと、状態を変えずに `UnsupportedError`（`"unresolved_code"`・`"unresolved_reason"`）になり、決定は残ります。原典で決められないことを、選べないこと（`INVALID_CHOICE`、ルールで不正）として扱わないためです。不変条件は、扱いを決められる選択が少なくとも 1 つ残っていることを確かめます（答えられない決定を作らない）。
- 複数段階の選択は、v0.2a と同じく、`resume` が次の決定を出す形で書けます。v0.2b の 3 枚は 1 段階です。

## 6. トラッシュの処理

- トレーナーカードは、手札から出した時点で手札を離れ、説明にしたがい終わったらトラッシュします（p.310「使ったトレーナーカードは、トラッシュします」）。決定を待っている間は `GameState.trainer_in_use` にあります。
- トラッシュするのは持ち主のトラッシュです（`TrainerInUse.player`。番のプレイヤー = 持ち主）。
- 使うための条件・原典で決められない場合で拒否したときは、カードは手札に残ります（手札から出す前に検査する）。
- 3 枚とも「使いすて」以外の記述はありません。場に残るトレーナー（つけて使うもの、スタジアム）は、それを加えるときに別の置き場所を作ります。

## 7. 状態の保存則と不変条件

`apply_command` は返す状態を毎回 `check_invariants` で確かめます。v0.2b で次を加えました。

- 使用中のトレーナーカードは、持ち主のゾーンの 1 つとして数える（カードの保存則。手札・トラッシュと二重にない、消えていない）。
- 使用中のカードはトレーナーカードで、持ち主は番のプレイヤー。
- 使用中のトレーナーがあるのは、そのトレーナーの決定（`resume == "trainer"`）を待っている間だけ。逆に、トレーナーの決定を待っているなら使用中のトレーナーがある。決定の `"use"` は使用中のカードと同じで、そのカードの実装が登録表にある。
- 終わった段階（GAME_OVER・SUDDEN_DEATH・HALTED）には、使用中のトレーナーも決定もない。
- `unresolved_choices` は選べるものの中にあり、残りで決定に答えられる。

これで、カードの消失・二重の移動（手札とトラッシュ・使用中の両方にある）・効果の二重の実行（同じ決定に 2 回答える）は、コマンドの検査と不変条件の両方で防ぎます（tests/test_trainers.py `test_broken_trainer_state_is_detected`、test_trainer_games.py のでたらめなコマンドの検査）。

## 8. 状態の書き出し（形式 3）

| 形式 | 内容 | 使用中のトレーナーがあるとき |
|---|---|---|
| 1（既定） | v0.1 と同じ形 | `ValueError`（使用中のカードを表せない。黙ってカードを落とさない） |
| 2 | v0.2a の項目を加えた形 | `ValueError` |
| 3 | 2 に `trainer_in_use`（`player`・`card`・`card_id`、なければ `null`）を加えた形 | 書き出せる |

トレーナーを使う対戦では形式 3 を使ってください。使用中のトレーナーがない状態では、形式 1・2 も今までどおり書き出せます（v0.1 の固定値・参照データは形式 1 のまま）。

## 9. 非公開の情報とログ

今のログ（`GameState.log`）と `state_to_dict` は、**エンジンの内部の完全な記録**です。プレイヤーや観戦者にそのまま見せると、隠れた情報が漏れます。**公開のログ（見る人ごとに伏せたログ）は未実装です。今のログを対戦の通信にそのまま使うことは安全ではありません。**

v0.2b のトレーナーで加わった・使うイベントの扱い:

| イベント | 項目 | 見せてよい相手 |
|---|---|---|
| `play_trainer` | `player`・`card`・`trainer`（名前） | 全員（手札から出して相手に見せる。p.310） |
| `draw`（マサキ・番の最初） | `player`、引いた枚数（`len(cards)`） | 全員 |
| `draw` | `cards`（引いたカード） | 引いたプレイヤーだけ（p.312「引いたカードを相手プレイヤーに見せる必要はありません」） |
| `remove_damage_counters`・`switch`・`discard_trainer` | すべて | 全員（場・トラッシュの公開の情報） |

ほかに隠す必要がある項目（v0.1 から）: `take_prize` の `card`（取ったサイドは相手に見せなくてよい。p.312）、`place_starting_pokemon` の `active`・`bench`（裏にして出し、表にするまで）。

設計の方針: 隠す情報は、イベントの種類ごとの決まった項目（上の表）にだけ入れ、イベントの別の項目に重ねて書かない（たとえば `draw` は枚数を別の項目に書かず、`cards` の長さで表す）。こうしておくと、見る人ごとのログは、種類ごとの項目を伏せるだけで作れます。その変換（`view(state, viewer)` など）は未実装です（[architecture-v0.2a.md 8 章](architecture-v0.2a.md)）。

## 10. 互換性

- **v0.1 の対戦結果**: v0.1（6068785）で記録した 15 場面の参照データ（tests/fixtures/v0_1_reference.json）は変えていません。再生すると、受け付けた 951 のコマンドと最後の状態（ログを含む）は完全に同じです。違うのは、v0.1 で `UNSUPPORTED_ACTION` だった `play_trainer` 38 件のエラーコードだけです（参照データのデッキにはトレーナーがないので、今もすべて拒否されます）。内訳は `WRONG_PHASE` 15・`INVALID_PLAYER` 14・`NOT_YOUR_TURN` 6・`CARD_NOT_IN_HAND` 3 です。互換性テストは、この 38 件だけ「ルールによる拒否（`IllegalActionError`）であること」を確かめ、ほかは今までどおりコードの一致を確かめます。
- **固定値**: 乱数の固定値（配りと 1 局の状態の SHA-256）は変わっていません。
- **ログ**: 既存のイベントの形は変えていません。トレーナーのイベント（`play_trainer`・`remove_damage_counters`・`switch`・`discard_trainer`）を加えました。マサキの `draw` は番の最初のドローと同じ形です。
- **コマンド**: 既存のコマンドの動作は変わりません。`PlayTrainer` は未対応から対応に変わりました（`UNSUPPORTED_COMMANDS` から外した）。
- **API の変更**: [api-review.md](api-review.md) の v0.2b の章。

### 変更した既存のテスト

どれも「トレーナーは未対応」「PlayTrainer は未対応」を前提にしていたものです。確かめる性質（登録のないトレーナーは使えない、など）は、実装を登録していないトレーナー（いいきずぐすり）で同じように確かめています。

| テスト | 変更 |
|---|---|
| test_turns.py `UnsupportedActionsTest.test_unsupported_commands` | 未対応の一覧から `PlayTrainer` を外し、手札にないカードは `CARD_NOT_IN_HAND` になることを確かめる |
| test_cards.py `test_v0_1_pool_is_ten_basic_pokemon_and_six_basic_energy` | 対戦用の組に加わったトレーナー 3 枚を確かめ、それ以外が v0.1 と同じ 16 枚であることを確かめる |
| test_cards.py `test_trainer_evolution_and_power_are_unsupported` | きずぐすり → いいきずぐすり |
| test_deck.py `test_unsupported_cards_are_rejected` | きずぐすり → いいきずぐすり |
| test_state_integrity.py `ALLOWED`・`PhaseCommandMatrixTest` | `MAIN` で `PlayTrainer` を受け付ける。ほかの段階の `PlayTrainer` は `WRONG_PHASE`（終わった段階はそれぞれのコード） |
| test_rng_and_serialize.py `test_format_2_adds_only_documented_fields`・`test_unknown_format_is_rejected` | 登録表の id（`kyuura-engine-0.2b`）、形式の一覧（1・2・3） |
| test_compat_v0_1.py | 上の `play_trainer` 38 件の扱い（参照データは変えていない） |

## 11. 将来の拡張方針

| 将来の機能 | v0.2b の土台 | 加えるもの |
|---|---|---|
| ほかのトレーナー（引く・回復・入れ替えなど） | `TrainerEntry`・`TrainerEffect`・`push_trainer_decision` | カードの最新の説明を照合し、実装を登録する。使うための条件は `check_playable` で `IllegalActionError` |
| 使うための条件があるトレーナー（パソコン通信など） | `check_playable` | 条件の検査と、条件の支払い（手札をトラッシュするなど）の選択の決定 |
| つけて使うトレーナー（プラスパワー・ディフェンダー）、スタジアム | `trainer.kinds` を扱えない実装は登録を拒む（`check`） | 場のポケモンにつくトレーナーの置き場所、番の終わりのトラッシュ、ダメージ計算の段階（p.321） |
| きぜつを起こすトレーナー | `_finish_trainer` | 使い終わったあとのきぜつの判定とサイド・交代（ワザのあとの処理を共通にする） |
| コイン（コインを投げるトレーナー・ワザ） | `GameState.rng`、乱数の保存・復元 | コインを投げる関数と、結果のログ |
| 特殊状態 | ポケモンいれかえは「ポケモンの入れ替え」 | ベンチに戻ったら特殊状態・持続する効果が消える（p.311）。にげるができない状態でも入れ替えは行う（p.325） |
| 進化 | 場のポケモンの番号（進化しても変わらない） | カードの重なり。きずぐすりの対象は場のポケモンの番号なので変わらない |
| 同じタイミングの順番（p.325） | 保留中の決定 | 番のプレイヤーが順番を選ぶ決定（[trainers-v0.2b.md 6 章](trainers-v0.2b.md)） |
| 入れ子の処理（トレーナーの途中で別の決定が割り込むなど） | 決定は一度に 1 つ、続きは `context` | 必要になったら、続きを積む形を検討する |
| 見る人ごとの状態・ログ | 隠す情報はイベントの決まった項目にだけ入る（9 章） | `view(state, viewer)` |

## 12. 設計上のトレードオフ

| 判断 | 理由 | 代償 |
|---|---|---|
| 登録表を 1 つのクラスのまま、トレーナーの欄を加えた | 対戦ごとの登録表（`GameState.effects`）が 1 つで済む。ワザと同じ考え方 | 欄が増えるたびに `with_*`・`without_*` が増える |
| 実装を `effects.py` に置いた（別のモジュールにしなかった） | 登録表（`DEFAULT_EFFECTS`）と実装の循環 import を避ける | `effects.py` が長くなった。カードが増えたら、実装をカードの種類ごとのモジュールに分け、登録表を組み立てるモジュールを別にする |
| 使用中のトレーナーを `GameState` の 1 つの欄にした | 1 枚を使っている最中に別のトレーナーは使えない（p.310）ので、一度に 1 枚。保存則を確かめやすい | 場に残るトレーナーには別の置き場所が要る |
| 原典で決められない選択を、選べるものに入れて `UnsupportedError` にした | 「ルールで不正」と「原典で決められない」を区別する | 選べるものをそのまま使うクライアントは、`unresolved_choices` も見る必要がある |
| 形式 1・2 は使用中のトレーナーがあると書き出さない | カードが消えたように見える辞書を作らない | 形式 1 を使っていたコードは、トレーナーのある対戦では形式 3 に変える必要がある |
| 未解決の場合を `UnsupportedError` にし、`Phase.HALTED` にしない | 未解決なのはそのトレーナーを使うことだけで、対戦は続けられる（使わなければよい） | 未解決の場面で、プレイヤーはそのカードを使えない |
