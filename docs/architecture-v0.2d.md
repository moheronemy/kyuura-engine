# v0.2d のアーキテクチャ（コイントスと、コインを投げるワザ）

v0.2d は、コイントスの処理と、コインの結果でダメージが変わるワザ（ドードーの「みだれづき」）を加えた版です。原典の照合と裁定は [coin-rules-v0.2d.md](coin-rules-v0.2d.md)（コイントスの規定）と [coin-attacks-v0.2d.md](coin-attacks-v0.2d.md)（みだれづき）にあります。

## 1. 目的と範囲

- 公式ルール（p.319）にもとづくコイントスを、対戦の乱数（`GameState.rng`）だけで決める。
- 乱数の再現性（同じ seed・操作列なら同じコイン）と、保存・復元（複製・`deepcopy`・`pickle`・乱数の JSON）を保つ。
- コインの結果をイベントログに残す。
- コインの結果でダメージが変わるワザを、v0.2c のダメージ計算（p.321 の段階）・プラスパワーとつなぐ。
- 既存の対戦結果・固定値・互換性・不変条件を変えない。

作らなかったもの: 汎用のカード効果の記述言語、コインの結果で分かれる効果の一般の仕組み（「おもてなら〜、うらなら〜」）、特殊状態・自分へのダメージ・山札の移動・トレーナーのコイン、ゲーム状態全体の JSON からの読み込み。

## 2. 変更の概要

| 項目 | v0.2c | v0.2d |
|---|---|---|
| 乱数を使う処理 | 山札を切る（対戦準備） | 山札を切る、コインを投げる（`coins.flip_coins`。1 枚 1 回 `getrandbits(1)`） |
| 新しいモジュール | — | `kyuura_engine/coins.py`（`CoinSide`・`CoinFlips`・`flip_coins`） |
| ワザの実装 | `DamageOnly` | `CoinFlipDamage`（コインを投げ、「おもて」の数 × n）。相手の対戦ポケモンにダメージを与える処理は `effects.damage_opponent_active` に分け、両方が使う |
| 効果の登録表 | id `kyuura-engine-0.2c`、ワザ 14 | id `kyuura-engine-0.2d`、ワザ 15（PMCG1-061#0 みだれづき） |
| `AttackEntry` | `effect`・`name_ja` | `text_ja`・`play_text_ja`・`source` を加えた（説明文のあるワザの照合用。省略時は None） |
| 登録の照合 | ワザ名 | ワザ名と説明文（`AttackEntry.text_ja` とデータの説明文が違えば使えない） |
| ダメージ計算 | 2 段階で終えたときも、渡した変更効果をすべて `modifiers` に入れていた（そうなる場面はなかった） | 2 段階で終えたら、計算に使った 2 段階の効果だけ。ログ `damage` に `stopped_after_step_2`（あるときだけ） |
| ログ | — | `coin_flip`（1 枚ごと） |
| カードデータの写し | ドードーは参照カード | `pool_v0_2d`（PMCG1-061）。対戦に使える |
| 状態の形・書き出しの形式 | 形式 1〜4 | 変えていない（コインの結果は状態に残らず、ログだけ） |
| 公開 API | — | `CoinSide` を加えた。版 `0.2.0d0` |

## 3. 乱数

- 乱数は対戦ごとの `GameState.rng`（`random.Random(seed)`）1 本だけです。モジュールの `random`（グローバルな乱数）は使わず、参照もしません（テストで、グローバルな乱数の seed を変えても結果が同じで、状態も変わらないことを確かめている）。
- 使う順番: 対戦準備で山札を切る（`shuffle`）→ 対戦中、コインを投げるたびに `getrandbits(1)`。
- `getrandbits(1)` は、メルセンヌ・ツイスタの 32 ビットの出力 1 個の最上位ビットです。Python 3.11・3.12・3.13 で同じ値になることを、固定値のテスト（test_coins.py `GoldenCoinTest`、test_coin_games.py `GoldenCoinGameTest`）で確かめました。`random()` などの浮動小数点を通す方法より、使う回数（1 枚 1 回）がはっきりします。
- コインを投げる効果のない対戦では、v0.2c までと同じく、対戦準備のあとで乱数を使いません（既存の固定値・互換性のテストは変わらない）。

### 検討した案

| 案 | 判断 |
|---|---|
| A. 対戦の乱数で決める（`getrandbits(1)`）（採用） | 再現できる。保存・復元は既存の乱数の仕組みでできる。プレイヤーは結果を選べない |
| B. ジャンケンと同じく、結果を外からコマンドで受け取る | プレイヤー（呼び出し側）が結果を選べてしまう。指示（「通常のコマンドで結果を選べない」）に合わない |
| C. コインの係（オブジェクト）を状態に持たせ、差し替えられるようにする | テストのために本番の API に口を作ることになる。`clone` で係ごと複製する必要がある。A で足りる |
| D. `random() < 0.5` | 結果の分布は同じだが、浮動小数点を通すので、使う回数と値の対応が A よりわかりにくい |

### テストでの制御

テストは、状態の `rng` を、決めた結果になる乱数に差し替えます（tests/helpers.py `rng_for_coins`・`with_coin_results`。seed を 0 から順に探すので毎回同じ）。エンジンのコマンド・公開 API に、コインの結果を指定する方法はありません（test_coins.py `test_rng_for_coins_is_test_only`）。正式な対戦開始のテスト（test_coin_games.py）は差し替えをせず、seed から決まるコインで進めます。

## 4. コインの API（`kyuura_engine/coins.py`）

```python
flip_coins(state, player, count, *, source, effect, card, pokemon_id=None) -> CoinFlips
```

- `count` 枚を 1 枚ずつ投げ、`CoinFlips(results)`（投げた順の `CoinSide` の組。`heads`・`tails` は数）を返します。
- `count` が 1 以上の整数でない・`player` が 0 か 1 でないときは、乱数を使う前に `ValueError`（効果の実装の誤り。プレイヤーの操作の誤りではない）。
- 効果の実装（`AttackEffect.resolve` など）の中から呼びます。エンジンの外から呼ぶものではありません（公開 API には `CoinSide` だけを出した）。

将来の効果（特殊状態・自分へのダメージ・トレーナーのコイン）も、この関数でコインを投げ、結果の使い方は各効果の実装に書きます。「おもてなら〜」の共通の記述の仕組みは作っていません（効果ごとに原典を照合して実装する）。

## 5. ログ

1 枚ごとに `coin_flip` を残します。

| 項目 | 内容 |
|---|---|
| `player` | コインを投げるプレイヤー（効果を使っている側。ワザならワザを使うポケモン側。[coin-rules-v0.2d.md](coin-rules-v0.2d.md) 2 章の 4） |
| `source` | 理由の種類（`"attack"`: ワザの説明） |
| `effect` | 効果の識別子（ワザなら `AttackKey` の文字列 `"PMCG1-061#0"`） |
| `card` | 効果を持つカードの uid（ワザならワザを使うポケモンのカード） |
| `pokemon_id` | 効果を持つ場のポケモンの番号（カードの uid とは別の番号。場のポケモンでなければ None） |
| `number` | 何枚目か（1 から） |
| `count` | この効果で投げる枚数 |
| `result` | `"heads"`（おもて）・`"tails"`（うら） |

1 枚ごとにしたのは、何枚目にどちらが出たかを残すため（将来の「うらが出るまで投げる」などでも同じ形で残せる）。合計（「おもて」の数）はログから数えられ、ダメージの記録（`damage` の `steps` の 1 段階）にも出ます。コインの結果は両方のプレイヤーが見るもので、隠す情報はありません（ログは今も内部の完全な記録。[architecture-v0.2b.md 9 章](architecture-v0.2b.md)）。

## 6. ワザの処理と原子性

```
apply_command(state, UseAttack)
  ├─ 段階・対戦の終わり（GAME_OVER・SUDDEN_DEATH・HALTED）の確認
  ├─ state.clone()（乱数も複製）
  └─ _use_attack
       ├─ 番・プレイヤー・ワザの位置・登録（UNSUPPORTED_ATTACK）・必要なエネルギー
       ├─ ログ attack（p.309 の手順 3: 宣言）
       ├─ effect.resolve（手順 6）: CoinFlipDamage → flip_coins → damage_opponent_active
       └─ _finish_attack（きぜつ → サイドの決定 … → 番の終わり）
  └─ check_invariants（破れていれば StateIntegrityError）
```

- ワザを使えるかの確認は、すべてコインの前に済みます。拒否する操作では、そもそもコインまで進みません。
- `apply_command` は複製した状態で処理するので、コインを投げたあとで止まっても（原典で決められない場合の `UnsupportedError`、エンジンの不具合の `StateIntegrityError`・`ValueError`）、渡した状態とその乱数は変わりません（test_coin_attacks.py `ErrorAfterFlippingTest`）。この性質があるので、「コインの前に使えるかを確かめる」ための新しい段階（`AttackEffect` の確認用の関数）は加えていません。投げる前に原典で決められない場合を見つける必要のある効果を加えるときに、`TrainerEffect.check_playable` と同じ形で加えます。
- 不正なコマンド・未対応・原典未解決・エンジンの不具合・正常なワザの結果の区別は [coin-rules-v0.2d.md](coin-rules-v0.2d.md) 4 章。
- 不変条件: コインはゾーン・段階・保留中の決定を加えないので、`check_invariants` に加えた条件はありません。カードの保存則などは、コインのワザのあとも毎回確かめます（`apply_command`。test_coin_games.py は各手で `check_invariants` を呼ぶ）。

## 7. ダメージ計算との統合

- ワザの実装が 1 段階の「基本となるダメージ」を計算して渡します（`damage_opponent_active(state, use, base)`）。`DamageOnly` は目安の数字、`CoinFlipDamage` は「おもて」の数 × n。
- 2・5〜8 段階の変更効果（プラスパワーなど）は v0.2c と同じく `attack_damage_modifiers` が集めます。コインのワザのための特別な処理はありません。
- 「おもて」0 枚なら 1 段階が 0 で、2 段階のあとで計算を終えます（p.321）。このとき `DamageCalculation.modifiers` は、計算に使った 2 段階の効果だけになりました（v0.2c では渡したすべて。v0.2c までのワザはダメージが正なので、この場面は起こらなかった）。ログ `damage` に `modifiers` は出ず、`stopped_after_step_2: true` が出ます。
- 抵抗力などで最後に 0 以下になった場合（2 段階で終えたのではない）は、今までどおり `amount` 0 で、段階の記録にマイナスが残ります。2 つは記録で区別できます。

## 8. 保留中の決定とコイン

- みだれづきはプレイヤーの決定を出しません。コイン・ダメージ・きぜつの判定は 1 つのコマンドの中で終わり、そのあとサイドを取る・バトル場に出す決定（v0.2a）を出すことがあります。決定に答えるとき、乱数は使いません。
- 決定を待つ間（`TAKE_PRIZE`・`PROMOTE_ACTIVE`・`DECISION`）は `UseAttack` を受け付けないので（`WRONG_PHASE`）、決定の途中でコインを投げることはありません。
- 決定が選ばれたあとでコインを投げる効果（`resume` の中で `flip_coins`）を加えても、`ResolveDecision` も複製した状態で処理するので、原子性は同じです。

## 9. 状態の書き出し・保存と復元

| 何を | どうする | 状況 |
|---|---|---|
| コインの結果 | ログ `coin_flip`。ログは形式 1〜4 のどれにも入る | 新しい形式は加えていない（形式 5 は不要） |
| この先のコイン | 乱数の状態の指紋 `rng_state_sha256`（`state_to_dict`） | 比べるためのもので、乱数はもどせない |
| 乱数の保存・復元 | `rng.rng_state_to_json`・`rng_from_json`（v0.2a） | 実装済み。コインを投げる前・後のどちらで保存しても、続きのコインは同じ（test_coins.py `CoinRngTest`、test_coin_games.py） |
| ゲーム状態の複製 | `GameState.clone`・`copy.deepcopy`・`pickle` | 乱数ごと複製する（実装済み） |
| ゲーム状態全体の JSON からの読み込み | — | **未実装**。`state_to_dict` は書き出し専用（乱数は指紋だけ）。読み込みを作るときは、乱数の状態（`rng_state_to_json`）・効果の登録表の id・カードの定義の出典を合わせて保存する必要がある |

## 10. 互換性

- 既存のテスト 282 件: すべて成功（変更したテストは下の表）。新しいテストを加えて 348 件。
- v0.1 の参照データ（tests/fixtures/v0_1_reference.json。変えていない）の再生: 同じ結果。エラーコードが変わるのは v0.2b からの `play_trainer` の 38 件だけで、v0.2d で新しく変わったものはない（参照データのデッキにドードーはない）。
- 乱数の固定値（test_reproducibility.py）: 変わらない。
- 既存のログ: コインを投げるワザを使わない対戦では、新しいイベント・項目は出ない。`damage` の `stopped_after_step_2` は 2 段階で計算を終えたときだけ出る（v0.2c までのワザでは起こらない）。
- v0.2b・v0.2c の未解決の場面（`UNRESOLVED_POTION_*`・`UNRESOLVED_SWITCH_WITHOUT_BENCH`・切り直しの `HALTED`）、p.325 の同じタイミングの順番（番のプレイヤーが先。実装上の仮定）、プラスパワーの裁定は変えていない。

### 変更した既存のテスト

| テスト | 変更 | 理由 |
|---|---|---|
| test_cards.py `test_v0_1_pool_is_ten_basic_pokemon_and_six_basic_energy` | 対戦に使えるカードに `pool_v0_2d`（ドードー）があることを加え、v0.1 の組の数え方からドードーを除いた | ドードーが対戦に使えるようになった。v0.1 の組（たねポケモン 10・基本エネルギー 6）は変わらない |
| test_cards.py `test_every_playable_attack_has_no_effect_text` | v0.1 の組のワザで確かめる | ドードーは説明文のあるワザ（test_coin_attacks.py で確かめる） |
| test_cards.py `test_damage_modifier_is_unsupported` | ドードーの登録を除いた登録表で、「×」のワザが未対応になることを確かめる | 既定の登録表ではドードーを登録した。確かめる性質（登録のない「×」のワザは使えない）は同じ |
| test_effects.py `test_every_v0_1_attack_is_registered_explicitly_as_damage_only` | v0.1 の組のカードで確かめる | 同上 |
| test_effects.py `test_attack_with_text_is_supported_when_an_implementation_is_registered`・`test_attack_with_text_cannot_be_registered_as_damage_only` | テスト専用の登録に、照合した説明文（`text_ja`）を書いた | 説明文の照合を加えたので、説明文のあるワザの登録には説明文が要る。確かめる性質は同じ |
| test_effects.py `test_with_and_without_do_not_change_the_original` | 登録の数 14 → 15 | みだれづきを加えた |
| test_trainers.py `test_default_registry_has_exactly_the_registered_cards`、test_rng_and_serialize.py `test_format_2_adds_only_documented_fields` | 登録表の id `kyuura-engine-0.2d` | ワザの登録を加えた（トレーナーの登録は同じ） |
| test_rng_and_serialize.py `test_engine_does_not_use_randomness_after_setup` | docstring だけ（「コインは未実装」→ コインのないデッキでは使わない） | テストの内容は同じ |

## 11. 将来の拡張方針

| 将来の機能 | v0.2d の土台 | 足りないもの | kyuura の文面にあるカードの例（照合前） |
|---|---|---|---|
| コインによる自分へのダメージ（「うらなら、自分にも 10 ダメージ」） | `flip_coins`、`damage_opponent_active` | 自分へのダメージの処理（p.320 のダメージ (3)。弱点・抵抗力を計算するか、プラスパワーを加えるか（p.257 の解説は加える）を原典で照合）。自分がきぜつしたときのサイド（相手が取る）と、同時のきぜつ（p.324・p.325） | 「コインを投げて「うら」なら、自分にも10ダメージ。」「…「うら」なら、自分にも30ダメージ。」の文面のワザ |
| コインによる特殊状態（「おもてなら、マヒ」） | `flip_coins` | 特殊状態の状態・ポケモンチェック（p.323）・ねむり・マヒ・こんらん・どくの処理（ねむりの回復のコインなど、コインはこの関数で投げる）。ワザの要素の順番（ダメージ → 効果。p.309・p.320） | シードラ「あわ」（p.320 の例）、「コインを投げて「おもて」なら、相手を「マヒ」状態にする。」の文面のワザ |
| 連続コイントス（「うらが出るまで投げる」） | 1 枚ごとのログ（`number`）、`flip_coins` | 終わりが決まっていない回数の投げ方（1 枚ずつ `flip_coins(…, 1)` を呼ぶ形で表せる。`count` の記録の意味を決める） | — |
| コインを使うトレーナー | `flip_coins` の `source`・`effect`・`card`（トレーナーのカード id・uid） | `TrainerEffect.resolve` の中で投げる。原典の照合 | — |
| ディフェンダー | v0.2c の `AttachedTrainer`・7 段階 | 対象を選ぶ決定・有効期限（次の相手の番の終わり）の照合 | — |
| 特殊状態 | — | 状態の保存場所（`PokemonInPlay` か持続する効果の一覧）、ポケモンチェック、にげる・ワザの制限（p.309・p.311） | — |
| 進化・退化 | 場のポケモンの番号（進化で変わらない） | `EvolvePokemon`（いまは未対応の操作）、最初の番・出した番の制限（p.310）、ついているカードの引き継ぎ（p.324） | ドードー → ドードリオ（ジャングル） |

## 12. 設計上のトレードオフ

| 判断 | 理由 | 代償 |
|---|---|---|
| コインを対戦の乱数で決め、外から指定させない | 再現できる。プレイヤーが選べない | 実物のコインで遊んだ結果を記録・再生するには、別の入力の仕組みが要る |
| 1 枚 1 回の `getrandbits(1)` | 使う回数がはっきりし、固定値で確かめやすい | 乱数の使い方を変えると、コインのある対戦の固定値が変わる |
| コインの結果を状態に残さず、ログだけに残す | 状態の形・書き出しの形式を変えない | 「さっきのコインの結果」を参照する効果を加えるときは、状態に残す必要がある |
| 1 枚ごとのログ | 何枚目かがわかり、将来の連続コイントスも同じ形 | ログが長くなる |
| コインの前の確認用の段階を加えなかった | 複製してから処理するので、途中で止まっても乱数は進まない | 投げる前に原典で決められない場合を見つける効果では、確認の段階を加える必要がある |
| 説明文の照合を `AttackEntry` に加えた（`text_ja`） | トレーナーと同じく、データが変わったら気づける | 説明文のあるワザを登録するには、照合した説明文を書く必要がある |
