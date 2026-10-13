# 公開 API のレビュー（v0.1〜v0.4d）

将来、CLI・GUI・Web API・AI プレイヤー・ほかの言語のクライアントから使うことを想定して、公開 API を評価したものです。v0.1 のレビューで書いた提案のうち、v0.2a で実装したものと、まだ提案のままのものを分けて書いています。構造の説明は [v0.2a](architecture-v0.2a.md)・[v0.2b](architecture-v0.2b.md)・[v0.2c](architecture-v0.2c.md)・[v0.2d](architecture-v0.2d.md)・[v0.2e](architecture-v0.2e.md)・[v0.2f](architecture-v0.2f.md)・[v0.3a](architecture-v0.3a.md)・[v0.3b](architecture-v0.3b.md) のアーキテクチャにあります。

## 1. 今の使い方

```python
state = new_game(deck0, deck1, seed)                 # 対戦準備（切り直しまで）
state = apply_command(state, command)                 # 1 手ずつ。新しい状態を返す。渡した状態は変えない
if state.decision is not None:                        # 決定を待っている（v0.2a）
    d = state.decision                                # 誰が（d.player）、何を（d.kind）、どれから（d.options）選ぶか
    state = apply_command(state, ResolveDecision(d.player, d.id, (d.options[0],)))
data = state_to_dict(state)                           # JSON にできる辞書（形式 1。隠れた情報も含む）
data2 = state_to_dict(state, format_version=2)        # 形式 2（場のポケモンの番号・決定などを加えた）
data3 = state_to_dict(state, format_version=3)        # 形式 3（使用中のトレーナーを加えた。v0.2b）
data4 = state_to_dict(state, format_version=4)        # 形式 4（ついているトレーナーを加えた。v0.2c。トレーナーのある対戦ではこれ）
command = command_from_dict({"type": "end_turn", "player": 0})
```

対戦の記録は「デッキ 2 つ・seed・コマンドの列」（とエンジンの版・kyuura のコミット・効果の登録表の id）で十分です。同じものからは同じ状態になります（Python 3.11〜3.13 で確認）。コインの結果（v0.2d）も seed から決まるので、記録に加える必要はありません（コマンドで結果を指定する方法もない）。状態を辞書からもどす関数（`state_from_dict`）はありません（[アーキテクチャ 6 章](architecture-v0.2a.md#6-乱数)）。

## 2. v0.2a〜v0.4e で加えた公開 API

### v0.2a

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

### v0.2b

| もの | 内容 |
|---|---|
| `PlayTrainer(player, card)` | トレーナーカードを使う（v0.1 からあったコマンドを、未対応から対応にした）。JSON の `type` は `play_trainer` |
| 決定の種類 `"select_pokemon"` | 効果の対象の場のポケモンを選ぶ（きずぐすり・ポケモンいれかえ）。`options` は場のポケモンの番号 |
| `PendingDecision.context` の `"unresolved_choices"`・`"unresolved_code"`・`"unresolved_reason"` | 選べるもののうち、原典で扱いを決められないもの。選ぶと `UnsupportedError`（決定は残る） |
| `GameState.trainer_in_use`・`TrainerInUse` | 使っている最中のトレーナーカード（決定を待っている間だけ） |
| `state_to_dict(state, format_version=3)` | 形式 3（`trainer_in_use`）。形式 1・2 は使用中のトレーナーがあると `ValueError` |
| `EffectRegistry.trainer_ids`・`trainer_entry`・`trainer_problem`・`trainer_effect`・`with_trainers`・`without_trainers` | トレーナーの登録表 |
| `TrainerEntry`・`TrainerEffect`・`TrainerUse`・`DrawCards`・`RemoveDamageCounters`・`SwitchWithBench` | トレーナーの実装を加える人向け（`kyuura_engine.effects`） |
| `decisions.push_trainer_decision`・`decisions.SELECT_POKEMON` | 効果の実装向け（クライアントは使わない） |
| `CardDefinition.trainer_text_ja`・`trainer_text_en`・`trainer_kinds` | トレーナーのデータ（照合用） |
| `RuleSet.damage_per_counter` | ダメージカウンター 1 個のダメージ（10。p.319） |
| `kyuura_engine.zones.draw_cards` | 山札から引く（内部。エンジンと効果の実装で共通） |
| エラーコード | `NOT_TRAINER`、`UNSUPPORTED_TRAINER`、`UNRESOLVED_POTION_WITHOUT_DAMAGE`、`UNRESOLVED_POTION_UNDAMAGED_TARGET`、`UNRESOLVED_SWITCH_WITHOUT_BENCH`（6 章） |

### v0.2c

| もの | 内容 |
|---|---|
| `AttachedTrainer`・`PokemonInPlay.trainers` | ポケモンについているトレーナーカード（カードの uid・使ったプレイヤー・`discard_at_end_of_turn`） |
| `state_to_dict(state, format_version=4)` | 形式 4（場のポケモンごとの `trainers`）。形式 1〜3 は、ついているトレーナーがあると `ValueError` |
| `damage.DamageModifier`・`calculate_attack_damage(..., modifiers=())`・`DAMAGE_STEP_CHOOSER` | ダメージ計算の 2・5〜8 段階の加算の変更効果（既存の呼び方はそのまま使える） |
| `TrainerEffect.stays_in_play`・`TrainerEffect.damage_modifiers`・`AttachedAttackBonus`・`effects.attack_damage_modifiers` | 場に残るトレーナーの実装を加える人向け |
| `zones.attach_trainer` | 使用中のトレーナーを場のポケモンにつける（効果の実装向け。内部） |
| ログ | `attach_trainer`・`discard_attached_trainer`、`damage` の `modifiers`・`knock_out` の `discarded_trainers`（あるときだけ） |

コマンドは増やしていません（プラスパワーも `PlayTrainer` で使う）。

### v0.2d

| もの | 内容 |
|---|---|
| `CoinSide`（`kyuura_engine` から import できる） | コインの結果（`HEADS`＝`"heads"` おもて、`TAILS`＝`"tails"` うら）。ログ `coin_flip` の `result` の値 |
| `coins.flip_coins`・`coins.CoinFlips` | 効果の実装向け（内部。クライアントは使わない）。コインを投げ、ログを残す |
| `effects.CoinFlipDamage`・`effects.damage_opponent_active` | コインを投げるワザの実装・相手の対戦ポケモンにダメージを与える処理（実装を加える人向け） |
| `AttackEntry.text_ja`・`play_text_ja`・`source` | 説明文のあるワザの登録の照合と出典（省略時は None） |
| ログ | `coin_flip`（1 枚ごと）、`damage` の `stopped_after_step_2`（2 段階のあとで計算を終えたときだけ） |
| `RULE_REFERENCES` | `coin_toss`・`attack_text`・`attack_failure` |

コマンド・段階・状態の項目・書き出しの形式は増やしていません。コインの結果を指定するコマンド・引数はありません（[architecture-v0.2d.md 3 章](architecture-v0.2d.md)）。

### v0.2e

| もの | 内容 |
|---|---|
| ディフェンダー（PMCG1-079） | `PlayTrainer` で使い、`select_pokemon` の決定（自分の場のポケモンの番号）に `ResolveDecision` で答える |
| `effects.AttachedDamageReduction` | ディフェンダーの実装（7 段階の −amount、`discard_turn_offset = 1`）。実装を加える人向け |
| `TrainerEffect.discard_turn_offset`・`TrainerEffect.attachment_discard_turn(state)` | 場に残るトレーナーの有効期限（使った番からいくつ後の番の終わりにトラッシュするか）。場に残る実装はこれを宣言する（不変条件が確かめる） |
| `engine.turn_owner(state, turn_number)` | その番号の番のプレイヤー（奇数番は先攻） |

コマンド・段階・決定の種類・ログの種類・状態の項目・書き出しの形式は増やしていません。

### v0.2f

| もの | 内容 |
|---|---|
| ピカチュウ（PMCG1-035）の「かじる」（`UseAttack(…, 0)`）・「でんげき」（`UseAttack(…, 1)`） | でんげきは相手に 30 → コイン 1 枚 → 「うら」なら自分に 10。きぜつ・サイド・交代は v0.2a の決定（`take_prize`・`promote_active`）で、同時のきぜつでは 2 つずつ順に出る |
| `effects.OPPONENT_ACTIVE`・`effects.SELF`・`effects.DAMAGE_TARGETS` | ワザのダメージを受けるポケモンの種類（p.320 のダメージの (1)・(3)）。実装を加える人向け |
| `effects.deal_attack_damage(state, use, target, base)` | ワザのダメージを 1 つ与える（受けるポケモンを決め、p.321 の順番で計算し、ログを残す）。ダメージを与えるワザの実装はこれを使う |
| `effects.damage_receiver(state, use, target)`・`effects.self_damage_problem(state, use)` | 受けるポケモン、自分へのダメージを原典で決められる形で計算できるか（できなければ `UnsupportedError`）。`self_damage_problem` は v0.3d で外した |
| `effects.SelfDamageOnTails(self_damage)` | でんげきの実装 |

コマンド・段階・決定の種類・ログの種類・状態の項目・書き出しの形式は増やしていません。ログの `damage`（自分へのダメージ）と `knock_out`（同時のきぜつ）に項目を加えました（7 章）。

### v0.3a

| もの | 内容 |
|---|---|
| ビードル（PMCG1-004）の「どくばり」（`UseAttack(…, 0)`） | 相手に 10 → コイン 1 枚 → 「おもて」なら相手をどく状態に |
| `Poison`・`SpecialConditions`（`kyuura_engine` から） | 場のポケモンの特殊状態（`PokemonInPlay.conditions`。frozen） |
| `kyuura_engine.conditions` | `poison`・`clear_special_conditions`（特殊状態を付ける・消す。実装を加える人向け） |
| `effects.PoisonOnHeads` | どくばりの実装 |
| ポケモンチェック | 番の終わりのあと、エンジンが自動で行う（どくのダメージ・きぜつ・サイド・交代）。ポケモンチェックの中のきぜつでは、サイド・交代の決定（`take_prize`・`promote_active`）が出て、`context` の `then` が `"next_turn"`（`engine.NEXT_TURN`） |
| `state_to_dict(state, format_version=5)` | 場のポケモンごとの `special_conditions` を加えた形 |

コマンド・段階・決定の種類は増やしていません。

### v0.3b

| もの | 内容 |
|---|---|
| キャタピー（PMCG1-002）の「いとをはく」（`UseAttack(…, 0)`） | 相手に 10 → コイン 1 枚 → 「おもて」なら相手をマヒ状態に |
| パラス（PMCG2-003）の「ひっかく」「キノコのほうし」（`UseAttack(…, 0)`・`UseAttack(…, 1)`） | ひっかく 20。キノコのほうしはダメージを与えず、相手をねむり状態に |
| `Asleep`・`Paralyzed`（`kyuura_engine` から） | `SpecialConditions.exclusive` の値（ねむり・マヒ。たがいに重複しない）。`Paralyzed.turn` はマヒ状態になった番 |
| `SpecialConditions.asleep`・`paralyzed`・`names()` | 状態を調べる性質 |
| `kyuura_engine.conditions` | `put_to_sleep`・`paralyze`・`recover_from_sleep`・`recover_from_paralysis`・`paralysis_recovery_turn`・`paralysis_problem`、理由の定数 `SLEEP_COIN`・`PARALYSIS_END`・`REPLACED`（実装を加える人向け） |
| `effects.ParalyzeOnHeads`・`PutToSleep` | いとをはく・キノコのほうしの実装 |
| ワザ・にげるの拒否 | `IllegalActionError` の `POKEMON_ASLEEP`・`POKEMON_PARALYZED`（状態も乱数も変えない） |
| ポケモンチェック | 2（どく）→ きぜつ・サイド・交代 → 3（ねむりのコイン。持ち主が投げる）→ 4（マヒの回復）→ 次の番。ポケモンチェックの中の決定の `then` は v0.3a と同じ `"next_turn"` |
| `state.turn_owner` | 番の番号から番のプレイヤー（`engine.turn_owner` と同じもの） |
| `state_to_dict(state, format_version=5)` | `special_conditions` に `sleep: {}`・`paralysis: {"turn": n}` が加わった |

コマンド・段階・決定の種類は増やしていません。

### v0.3c

| もの | 内容 |
|---|---|
| ロコン（PMCG1-015）の「あやしいひかり」（`UseAttack(…, 0)`） | 相手に 10 → コイン 1 枚 → 「おもて」なら相手をこんらん状態に |
| `Confused`（`kyuura_engine` から） | `SpecialConditions.exclusive` の値（こんらん。ねむり・マヒと重複しない。持つ情報はない） |
| `SpecialConditions.confused` | 状態を調べる性質 |
| `PokemonInPlay.retreat_failed_turn` | こんらん状態で「にげる」に失敗した番（なければ None）。番の終わりに None に戻る。そのポケモンはその番の間「にげる」を宣言できない |
| `kyuura_engine.conditions` | `confuse`、`CONFUSION`・`CONFUSION_DAMAGE`（実装を加える人向け） |
| `damage.calculate_confusion_damage` | こんらんの 20 の計算（弱点・抵抗力だけ） |
| `effects.ConfuseOnHeads`、`AttackEffect.problem` | あやしいひかりの実装。ワザを使う前に分かる、原典で決められない場合を返す口（既定は None。エンジンがこんらんのコインの前に聞く） |
| こんらん状態のポケモンの `UseAttack` | 宣言のあとでコイン（`source: "confusion"`）。「うら」なら自分に 20（`confusion_damage`）で番が終わる。拒否ではない（`apply_command` は新しい状態を返す） |
| こんらん状態のポケモンの `Retreat` | エネルギーをトラッシュしてからコイン。「うら」なら `retreat_failed`（番は続く）。拒否ではない |
| 再宣言の拒否 | `IllegalActionError` の `RETREAT_ALREADY_FAILED`（状態も乱数も変えない） |
| 原典で決められない場合 | `UnsupportedError` の `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS`（ダメージを変えるカードがついたこんらんのポケモンのワザ）・`UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED`（失敗のあとこんらんが消えて戻ったポケモンの「にげる」） |
| `state_to_dict(state, format_version=5)` | `special_conditions` に `confusion: {}` が加わった |
| `state_to_dict(state, format_version=6)` | 5 に、場のポケモンごとの `retreat_failed_turn` を加えた形 |

コマンド・段階・決定の種類は増やしていません。

### v0.3d

公開するものは増やしていません（コマンド・段階・決定の種類・ログの種類・状態の項目・書き出しの形式・エラーコードは同じ）。変わったのは次のものです。

| もの | 内容 |
|---|---|
| `effects.self_damage_problem` | 外した（v0.2f の未解決が p.90 の解説で決まった。[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md) 6 章） |
| `effects.deal_attack_damage(state, use, SELF, base)` | 自分へのダメージにも弱点・抵抗力を計算する（ワザを使うポケモンのタイプと自分の弱点・抵抗力）。`UNRESOLVED_SELF_DAMAGE_WEAKNESS_RESISTANCE` はもう出ない |
| `SelfDamageOnTails.problem` | 既定（None）。v0.3d の対応カードのワザの実装は、どれも `problem` が None（[effect-preflight-v0.3d.md](effect-preflight-v0.3d.md)） |
| `check_invariants` | にげるの失敗の記録が、今の番のログの `retreat_failed`（同じ `pokemon_id`）と対応しないと違反（v0.3d） |
| `kyuura_engine.__version__` | `0.3.0d0`。効果の登録表の id は `kyuura-engine-0.3c` のまま（登録の内容が同じ。[architecture-v0.3d.md](architecture-v0.3d.md) 8 章） |

### v0.4a

| もの | 内容 |
|---|---|
| `EvolvePokemon(player, card, target)` | 手札の 1 進化カード（`card`）を、自分の場のポケモン（`target`＝場のポケモンの番号 `pokemon_id`。カードの uid ではない）に重ねて進化させる。決定は出さず、乱数を使わず、番は続く。v0.3d まで `UNSUPPORTED_ACTION` だった |
| パラセクト（PMCG2-010）・ジュゴン（PMCG1-030） | 1 進化（`pool_v0_4a`）。パラセクトは キノコのほうし（0）・きりさく（1）、ジュゴンは オーロラビーム（0）・れいとうビーム（1） |
| `PokemonInPlay.evolution_stack`・`played_turn`・`evolved_turn`・`current_form_turn`・`cards()` | 下のカード（下から順のタプル）・場に出た番・進化した番。`card` はいちばん上のカード |
| `CardDefinition.evolves_from`・`is_stage1_pokemon` | 「○○から進化」の名前・1 進化のカードか |
| `kyuura_engine.conditions.EVOLVE` | 特殊状態が進化で消えた理由（ログの `reason`） |
| `state_to_dict(state, format_version=7)` | 6 に、場のポケモンごとの `evolution_stack`・`played_turn`・`evolved_turn` を加えた形 |
| `RULE_REFERENCES` | `evolution`・`evolved_pokemon` |
| `kyuura_engine.__version__` | `0.4.0a0`。効果の登録表の id は `kyuura-engine-0.4a` |

段階・決定の種類は増やしていません。

### v0.4b

| もの | 内容 |
|---|---|
| トランセル（PMCG1-003）・コクーン（PMCG1-009） | 1 進化（`pool_v0_4b`）。トランセルは かたまる（0）・しびれごな（1）、コクーンは かたまる（0）・どくのこな（1） |
| `PreventDamage`（`kyuura_engine` から import できる）・`state.PERSISTENT_EFFECT_TYPES` | ワザによる持続する効果の値（frozen。`source_card`・`source_player`・`created_turn`・`active_turn`、`kind = "prevent_damage"`） |
| `PokemonInPlay.persistent_effects` | 場のポケモンが受けている持続する効果のタプル（既定は `()`） |
| `kyuura_engine.persistent` | `add_persistent_effect`・`remove_persistent_effects`・`remove_expired_persistent_effects`・`damage_prevention`（効果の実装を加える人向け。内部）。消える理由 `EXPIRED`・`KNOCK_OUT`（と `conditions` の `RETREAT`・`SWITCH`・`EVOLVE`） |
| `effects.PreventDamageOnHeads` | 「かたまる」の実装（効果の実装を加える人向け） |
| `state_to_dict(state, format_version=8)` | 7 に、場のポケモンごとの `persistent_effects` を加えた形 |
| `kyuura_engine.__version__` | `0.4.0b0`。効果の登録表の id は `kyuura-engine-0.4b` |

コマンド・段階・決定の種類は増やしていません。

### v0.4c

| もの | 内容 |
|---|---|
| `EvolvePokemon(player, card, target)` | 同じコマンドで、手札の 2 進化カードを自分の場の 1 進化ポケモンに重ねる（1 進化 → 2 進化）。今の番に 1 進化したポケモンは `EVOLVED_THIS_TURN` |
| スピアー（PMCG1-012） | 2 進化（`pool_v0_4c`。コクーンから進化）。ダブルニードル（0）・どくばり（1） |
| `CardDefinition.is_stage2_pokemon`・`is_evolution_pokemon` | 2 進化のカードか・エンジンが進化の手順で扱う進化カード（1 進化・2 進化）か |
| `kyuura_engine.cards.EVOLUTION_STAGES` | 進化の重なりの下から順の段階 `("basic", "stage1", "stage2")` |
| `PokemonInPlay.evolution_stack` | 0〜2 枚（2 進化なら たねポケモン・1 進化ポケモンの順）。項目は v0.4a と同じ |
| `kyuura_engine.__version__` | `0.4.0c0`。効果の登録表の id は `kyuura-engine-0.4c` |

コマンド・段階・決定の種類・状態の項目・書き出しの形式（形式 8 のまま）・ログのイベントは増やしていません。エラーコード `EVOLUTION_STAGE_MISMATCH` を加えました（6 章）。

### v0.4d

| もの | 内容 |
|---|---|
| バタフリー（PMCG2-007） | 2 進化（`pool_v0_4d`。トランセルから進化）。ふきとばし（0）・メガドレイン（1） |
| 決定の種類 `forced_switch`（`decisions.FORCED_SWITCH`） | ワザ（ふきとばし）の途中で、ワザを使われた側のプレイヤーが、入れ替わる控えを選ぶ。`decision.player` は相手で、`state.current_player` はワザを使ったプレイヤーのまま。段階は `Phase.DECISION`。答えは `ResolveDecision(相手, decision.id, (pokemon_id,))` |
| `effects.DamageResult` | `deal_attack_damage`・`damage_opponent_active` の戻り値（`target`・`player`・`pokemon_id`・`prevented`・`amount`（防いだら None）・`knocked_out`、`dealt`）。効果の実装を加える人向け |
| `AttackEffect.decision_problems(state, use, decision)` | ワザが出した決定を待つ状態の、効果ごとの不変条件。既定は「決定するのはワザを使ったプレイヤー」。相手が決定する効果は上書きする（効果の実装を加える人向け） |
| `effects.DamageAndForceSwitch`・`DamageAndDrain` | ふきとばし・メガドレインの実装（効果の実装を加える人向け）。`effects.TARGET_KNOCKED_OUT`・`NO_BENCH`（ログ `forced_switch_skipped` の理由） |
| `conditions.FORCED_SWITCH`・`persistent.REMOVAL_REASONS` | 特殊状態・持続する効果が消える理由に `forced_switch` |
| `kyuura_engine.__version__` | `0.4.0d0`。効果の登録表の id は `kyuura-engine-0.4d` |

コマンド・段階・状態の項目・エラーコード・書き出しの形式（形式 8 のまま）は増やしていません。`state_to_dict(state)`（形式 1）は、ワザの途中の決定があると `ValueError` になりました（4 章）。ログのイベント `forced_switch`・`forced_switch_skipped`・`drain_heal` を加えました（7 章）。

### v0.4e

| もの | 内容 |
|---|---|
| `TrainerEffect.decision_problems(state, use, decision)` | トレーナーが出した決定を待つ状態の、効果ごとの不変条件（v0.4d のワザの `AttackEffect.decision_problems` と同じ考え方）。既定は「決定するのはトレーナーを使ったプレイヤー」。決定を出す実装（きずぐすり・ポケモンいれかえ・ディフェンダー）は種類・選ぶ数・選べるもの・原典で決められない選択を宣言する（効果の実装を加える人向け） |
| `check_invariants` | トレーナーの決定の形、サイド・交代の決定の再開先と選ぶ数、サイドを取る「だれが何枚」、両方が出すときの順番、番の番号と番の始まりのログを確かめるようになった（[architecture-v0.4e.md](architecture-v0.4e.md)）。`new_game`・`apply_command` が返す状態では、v0.4d と同じく問題はない |
| tools/compare_engine_versions.py・tools/compat_driver.py・tools/stress_engine.py | 前の版との比較・ストレス実行の道具（パッケージの API ではない。リポジトリの直下で実行する） |
| `kyuura_engine.__version__` | `0.4.0e0`。効果の登録表の id は `kyuura-engine-0.4d` のまま（登録の中身を変えていない） |

コマンド・段階・状態の項目・エラーコード・ログのイベント・書き出しの形式（形式 8 のまま）は増やしていません。

### v0.5

| もの | 内容 |
|---|---|
| `UsePokemonPower(player, pokemon, power=0, energy=None, source=None, target=None)` | v0.1 からあったコマンドを受け付けるようにした。`pokemon` は特殊能力を使う自分の場のポケモンの番号（`pokemon_id`）、`power` は特殊能力の位置、`energy`・`source`・`target` は特殊能力の説明が選ばせるもの（エナジートランスは、移すエネルギーの uid・移動元と移動先の場のポケモンの番号）。番のプレイヤーの `Phase.MAIN` だけで受け付ける。使っても番は終わらない（[energy-transfer-v0.5.md](energy-transfer-v0.5.md)） |
| `PowerKey`・`PowerEntry`（`kyuura_engine` から公開）、`effects.PowerUse`・`PowerEffect`・`EnergyTransfer` | ポケモンパワーの登録（効果の実装を加える人向け）。`EffectRegistry.power_keys`・`power_entry`・`power_problem`・`power_effect`・`with_powers`・`without_powers` |
| `cards.Power`・`CardDefinition.powers` | カードのポケモンパワー（名前・種類・印刷の文面・使えるか・理由） |
| `effects.PoisonOpponent`・`DamageAndRemoveCounters` | どくのこな（コインなし）・やどりぎのタネの実装（効果の実装を加える人向け） |
| フシギダネ（PMCG1-001）・フシギソウ（PMCG1-008）・フシギバナ（PMCG1-011） | 対戦用のカード（`pool_v0_5`）。参照カードはフシギバナからカメックス（PMCG1-032）に替えた |
| `commands.UNSUPPORTED_COMMANDS` | 空のタプル（未対応の操作のコマンドの種類はなくなった） |
| `kyuura_engine.__version__` | `0.5.0`。効果の登録表の id は `kyuura-engine-0.5` |

段階・状態の項目・書き出しの形式（形式 8 のまま）は増やしていません。エラーコード（6 章）とログのイベント `pokemon_power`・`move_energy`（7 章）を加えました。

### v0.6

| もの | 内容 |
|---|---|
| `UsePokemonPower`（項目・型は v0.5 と同じ） | カメックスの「あまごい」は、`energy` に自分の手札の「水」エネルギーカードの uid、`target` につける先の自分の場の「水」ポケモンの番号を指定する（`source` は None。指定したら `POWER_CHOICE_NOT_USED`）。1 回の使用で 1 枚。項目の意味はパワーごとに違う（エナジートランスの `energy` はついているカード）ので、クライアントはパワーごとに選ばせるものを決める（[architecture-v0.6.md](architecture-v0.6.md) 1 章） |
| `GameState.energy_attached_by_powers_this_turn` | 加えた（整数。既定 0）。この番にポケモンパワーの効果で手札からつけた枚数。番の最初に 0。手札からつける通常の操作の回数 `energy_attachments_this_turn` とは別 |
| `state_to_dict(state, format_version=9)` | 加えた。形式 8 に上の段の `energy_attached_by_powers_this_turn` を加えたもの。形式 1〜8 は、その数が 0 でなければ `ValueError`（0 なら v0.5 と同じ） |
| `effects.AttachEnergyFromHand`・`ExtraEnergyDamage` | あまごい・ハイドロポンプの実装（効果の実装を加える人向け） |
| `zones.attach_energy_from_hand(state, player, energy, pokemon)` | 手札のエネルギーカードを場のポケモンにつける共通の処理（エンジンの内部。確かめることは呼ぶ側が先に済ませる） |
| ゼニガメ（PMCG1-023）・カメール（PMCG1-027）・カメックス（PMCG1-032） | 対戦用のカード（`pool_v0_6`）。参照カードはカメックスからフーディン（PMCG1-049）に替えた |
| `kyuura_engine.__version__` | `0.6.0`。効果の登録表の id は `kyuura-engine-0.6` |

段階・コマンドの種類・決定の種類は増やしていません。エラーコード `WRONG_POKEMON_TYPE`・`POWER_CHOICE_NOT_USED`・`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`（6 章）とログのイベント `power_attach_energy`（7 章）を加えました。

### v0.7

| もの | 内容 |
|---|---|
| `UsePokemonPower`（項目・型は v0.5 と同じ） | フーディンの「ダメージスワップ」は、`source` に移動元、`target` に移動先の自分の場のポケモンの番号を指定する（`energy` は None。指定したら `POWER_CHOICE_NOT_USED`）。1 回の使用で 1 個（10）。使うフーディン自身も移動元・移動先にできる（[architecture-v0.7.md](architecture-v0.7.md) 1 章） |
| `effects.MoveDamageCounter`・`effects.would_be_knocked_out(state, pokemon, damage)` | ダメージスワップの実装と、きぜつの判定の式（ダメージが HP と同じか大きい。いちばん上のカードの HP）を 1 か所にした関数（効果の実装を加える人向け） |
| `effects.DiscardEnergyAndRemoveAllCounters` | ユンゲラーの「じこさいせい」の実装 |
| `decisions.DISCARD_ENERGY`（`"discard_energy"`） | 決定の種類を加えた。じこさいせいで、ワザを使ったプレイヤーが、ワザを使ったポケモンについている「超」エネルギーカード（選べるものはカードの uid）を 1 枚選ぶ。答えは `ResolveDecision`。段階は `Phase.DECISION`（v0.4d のワザの途中の決定と同じ） |
| ケーシィ（PMCG1-043）・ユンゲラー（PMCG1-046）・フーディン（PMCG1-049） | 対戦用のカード（`pool_v0_7`）。参照カードはフーディンからリザードン（PMCG1-021）に替えた |
| `kyuura_engine.__version__` | `0.7.0`。効果の登録表の id は `kyuura-engine-0.7` |

段階・コマンドの種類・状態の項目・書き出しの形式は増やしていません（形式 9 のまま）。エラーコード `NO_DAMAGE_COUNTERS`・`WOULD_KNOCK_OUT`（ダメージスワップ。`SAME_POKEMON`・`SOURCE_NOT_…`・`TARGET_NOT_…`・`POWER_CHOICE_…` は v0.5・v0.6 からあるもの）と、ログのイベント `move_damage_counter`・`discard_energy`・`remove_all_damage_counters` を加えました。拒否のコードの順番で約束しているのは、(1) 型 → 対戦の終わり → 段階・番 → 共通の確認 → パワーごとの確認、(2) パワーの使えない特殊状態は選ばせるものより先、(3) `UNRESOLVED_…` はほかの確認がすべて通ったあと、だけです。それ以外の、2 つ以上の理由で正しくないコマンドにどのコードを返すかは約束していません（[architecture-v0.7.md](architecture-v0.7.md) 12 章）。

### v0.8

| もの | 内容 |
|---|---|
| `kyuura_engine.power_suppressors(state, pokemon_id, power_index=0)` | 場のポケモンの特殊能力を、今消している場のポケモン（はたらいているかがくへんかガスを持つベトベトン）の番号のタプル。空なら消されていない（ほかの条件で使えないことはある）。場にいないポケモン・ない特殊能力なら `ValueError`。状態を変えない。コマンドを送らずに、使えない理由を示すため（[continuous-effects-v0.8.md](continuous-effects-v0.8.md) 2 章） |
| `kyuura_engine.working_power_suppressors(state)` | はたらいているかがくへんかガスを持つ場のポケモンの番号のタプル（プレイヤー 0 → 1、それぞれバトル場 → ベンチの順）。状態を変えない |
| `continuous.suppressors_of(state, power)` | 特殊能力 `power`（カードのデータの `Power`）を消している場のポケモンの番号（エンジンの内部・効果の実装を加える人向け） |
| `effects.PowerEffect.declared` | クラス変数。宣言して使う特殊能力なら True（v0.5〜v0.7 の実装）。常にはたらく特殊能力（`SuppressOtherPowers`）は False |
| `effects.SuppressOtherPowers`・`PoisonWithoutDamage`・`CoinBonusDamageAndParalyze` | かがくへんかガス・どくガス・ねばりつくの実装（効果の実装を加える人向け） |
| ロケット団のベトベター（PMCG4-004）・ベトベトン（PMCG3-007） | 対戦用のカード（`pool_v0_8`）。化石の秘密のベトベター（PMCG3-003）は参照カード（デッキに入らない） |
| `kyuura_engine.__version__` | `0.8.0`。効果の登録表の id は `kyuura-engine-0.8` |

段階・コマンドの種類・決定の種類・状態の項目・書き出しの形式（9 のまま）・ログのイベントの種類は増やしていません。エラーコード `POWER_NOT_DECLARABLE`（常にはたらいていて宣言しない特殊能力の使用。かがくへんかガス）・`POWER_SUPPRESSED`（はたらいているかがくへんかガスに消されている特殊能力の使用）を加えました。どちらも `IllegalActionError` で、宣言のログより前に拒否する（状態・乱数・ログは変わらない）。拒否のコードの順番の約束に、(1) の「共通の確認」と「パワーごとの確認」のあいだに `POWER_NOT_DECLARABLE` → `POWER_SUPPRESSED` を加えました（[architecture-v0.8.md](architecture-v0.8.md) 13 章）。

## 3. 公開すべきもの・内部として隠すべきもの

| もの | 今 | 分類 | 理由・提案 |
|---|---|---|---|
| `new_game` | 公開 | **公開** | 対戦の入口。`rules`・`pool` の引数は、既知のルールの組・検証したカードの組だけを受け付けるようにしたい（L10） |
| `apply_command` | 公開 | **公開** | 状態遷移の唯一の入口。返す状態は必ず不変条件で確かめる |
| コマンドの dataclass（`PlaceStartingPokemon` など、`ResolveDecision`） | 公開 | **公開** | 操作の表現。項目は整数（uid・番号）と整数のタプルだけ。リストは受け付けない（`BAD_COMMAND`） |
| `command_from_dict`・`command_to_dict` | 公開 | **公開** | 他言語・Web との境界。JSON の形（`type` と各項目）を文書にして固定したい |
| `state_to_dict` | 公開 | **公開**（形式ごとに固定する） | 形式 1 は v0.1 と同じに固定。形式 2 は v0.2a、形式 3 は v0.2b で加えた。どれも内部の完全な状態で、見る人ごとに絞る形が要る（M6、[アーキテクチャ 8 章](architecture-v0.2a.md#8-非公開の情報方針未実装)） |
| `GameState` の読み取り（`phase`・`current_player`・`turn_number`・`result`・`halt`・`decision`・各ゾーン） | 公開（書き換えもできる） | **読み取りだけ公開** | 可変の dataclass なので、呼び出し側が書き換えられる（書き換えた状態は `StateIntegrityError` になることがある）。読み取り専用の見え方を用意したい |
| `GameState(...)` を直接作る | できる（v0.2a から `effects` が必要） | **内部** | 正式な入口は `new_game`。テストの `build_test_state` だけが直接作る |
| `GameState.rng`・`clone()`・`add_event()` | 公開 | **内部** | 乱数を外から進めたり差し替えたりすると、再現性が崩れ、この先のコインの結果も変わる（v0.2d。テストは結果を決めるために差し替えるが、通常の使い方ではない）。`clone()` は `apply_command` が使う。`add_event()` はエンジンだけが使う |
| `GameState.pending_prizes`・`pending_promotions` | 読み取り専用の値（v0.2a。決定から作る） | **互換のためだけに残す** | 新しいコードは `decision` を見る |
| `GameState.mulligan_rounds` | 公開 | **読み取りだけ公開** | 切り直しの経過（HALTED の理由の説明に使う） |
| `PendingDecision` | 公開（frozen） | **公開** | 画面・AI が「何を選ぶか」を知るための情報。`resume`・`context` はエンジンの続きの情報なので、クライアントは読まなくてよい |
| `PlayerState`・`PokemonInPlay` | 公開（可変） | **内部**（読み取り専用の見え方を公開） | リストを直接書き換えられる |
| `CardInstance`・`DataSource`・`Halt`・`GameResult` | 公開（frozen） | **公開** | 変えられない値。`GameResult.outcome` は文字列なので Enum にしたい |
| `Phase`・`TERMINAL_PHASES` | 公開 | **公開** | 決定を待つ段階は `decisions.DECISION_PHASES` |
| `CardDefinition`・`Attack`・`EnergyType`・`can_pay_cost` | 公開 | **公開**（読み取り） | 画面の表示・AI の判断に使う。`supported` は、そのプールの登録表での分類 |
| `load_card_pool`・`CardPool` | 公開 | **公開**（読み取り） | 結果は読み取り専用。`CardPool.effects` は分類に使った登録表 |
| `EffectRegistry`・`DEFAULT_EFFECTS`・`AttackKey`・`TrainerEntry` | 公開 | **公開**（読み取り。登録は実装を加える人向け） | どのワザ・トレーナーが使えるかの根拠。`with_*`・`without_*` は新しい登録表を作る（元は変えない） |
| `AttackEffect`・`DamageOnly`・`AttackEntry`・`AttackUse`・`TrainerEffect`・`TrainerUse` と各実装 | `kyuura_engine.effects` | **公開（実装を加える人向け）** | カードの効果を実装するときの型 |
| `decisions.push_decision`・`push_attack_decision`・`push_trainer_decision`・`check_choices` | `kyuura_engine.decisions` | **内部（エンジンと効果の実装向け）** | クライアントは使わない。決定に答えるのは `ResolveDecision` |
| `GameState.trainer_in_use` | 公開（frozen の値） | **読み取りだけ公開** | 決定を待っている間、使用中のトレーナーを表示するのに使う |
| `zones.draw_cards` | モジュール | **内部** | 山札から引く処理（エンジンと効果の実装で共通） |
| `classify_record`・`pool_from_extract`・`read_extract`・`read_verification` | モジュールから import できる | **内部** | データの読み込みと分類の道具 |
| `deck_problems`・`validate_deck`・`expand_decklist` | 公開 | **公開** | デッキの編集画面で使う。問題点は文字列ではなく（コード, カード id, 説明）の組にしたい（L9） |
| `check_invariants` | 公開 | **公開**（検査用） | テスト・不具合の調査に使う |
| `power_suppressors`・`working_power_suppressors`（v0.8） | 公開 | **公開**（読み取り） | 状態を変えない問い合わせ。画面が、特殊能力を使えない理由（かがくへんかガス）を示すのに使う。`continuous.suppressors_of` はエンジンの内部 |
| 例外（`EngineError` と `code`） | 公開 | **公開** | コードの一覧を固定する（4 章） |
| `RuleSet`・`RULES_2000_02_14`・`RULE_REFERENCES` | 公開 | **公開**（読み取り） | `RULE_REFERENCES` は docs と二重管理（L8） |
| `kyuura_engine.rng` | モジュール | **公開**（保存・比較用） | 乱数を進める関数は持たない |
| `engine._*`・`judge`・`damage` | 内部（`_` 付き・モジュール） | **内部** | `judge.decide`・`calculate_attack_damage` は純粋な関数なので、テストからは使ってよい |

## 4. 互換性と移行

### v0.1 → v0.2a

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

### v0.1・v0.2a → v0.2b

- 対戦の結果（v0.1 の参照データの最後の状態・ログ）・固定値・既存のコマンドの動作は変わりません。違いは、v0.1 で `UNSUPPORTED_ACTION` だった `PlayTrainer` が処理されるようになったことです（参照データの 38 件は、今もルールによって拒否される。[v0.2b のアーキテクチャ 10 章](architecture-v0.2b.md#10-互換性)）。
- 互換でない変更:
  - `PlayTrainer` は `UNSUPPORTED_ACTION` にならない（`UNSUPPORTED_COMMANDS` から外した）
  - 効果の登録表の id が `kyuura-engine-0.2b` になった（形式 2・3 の `effects`）
  - 写しの対戦用のカードの組に、トレーナー 3 枚が加わった（`CardPool.playable_ids`）。参照カードのきずぐすり（PMCG1-071）は対戦用に移り、いいきずぐすり（PMCG1-075）が参照カードに加わった
  - 形式 1・2 は、使用中のトレーナーがある状態を書き出さない（`ValueError`）
  - `RuleSet` に `damage_per_counter` が加わった（`RuleSet(...)` を直接作るコードは引数が要る）
  - `EffectRegistry(...)` の第 3 引数（`trainers`、省略可）が加わった
- 新しいクライアントへの推奨: 状態の辞書は形式 3 を使う。決定の `options` から選ぶときは `context` の `unresolved_choices` を除く。

### v0.2b → v0.2c

- 対戦の結果（v0.1 の参照データ）・固定値・既存のコマンドとログは変わりません。ついているトレーナーがない対戦では、新しいイベント・項目は出ません。
- 互換でない変更:
  - 効果の登録表の id が `kyuura-engine-0.2c` になり、トレーナーの登録にプラスパワーが加わった
  - 写しの対戦用のカードの組に、プラスパワー（`pool_v0_2c`）が加わった
  - 形式 1〜3 は、ついているトレーナーがある状態を書き出さない（`ValueError`）
  - `PokemonInPlay` に `trainers`、`DamageCalculation` に `modifiers` が加わった（どちらも既定値あり）
- 新しいクライアントへの推奨: 状態の辞書は形式 4 を使う。

### v0.2c → v0.2d

- 対戦の結果（v0.1 の参照データ）・固定値・既存のコマンドとログは変わりません。コインを投げるワザを使わない対戦では、乱数の使い方も、新しいイベント・項目もありません。
- 互換でない変更:
  - 効果の登録表の id が `kyuura-engine-0.2d` になり、ワザの登録にドードーの「みだれづき」（PMCG1-061#0）が加わった
  - 写しの対戦用のカードの組に、ドードー（`pool_v0_2d`）が加わった（参照カードから移った）
  - 説明文のあるワザの登録は、`AttackEntry.text_ja` にデータと同じ説明文を書かないと使えない（データが変わったことに気づくため。トレーナーの `TrainerEntry.text_ja` と同じ）
  - `DamageCalculation.modifiers` は、2 段階のあとで計算を終えたときは、計算に使った 2 段階の効果だけになった（v0.2c までの対応カードでは起こらない）
- 新しいクライアントへの推奨: コインの結果はログの `coin_flip` から表示する。対戦を保存して再開するときは、乱数の状態を `rng.rng_state_to_json` で保存する（ゲーム状態全体の読み込みは未実装）。

### v0.2d → v0.2e

- 対戦の結果（v0.1 の参照データ）・乱数とコインの固定値・既存のコマンドとログは変わりません。ディフェンダーを使わない対戦では、新しいイベント・項目は出ません。
- 互換でない変更:
  - 効果の登録表の id が `kyuura-engine-0.2e` になり、トレーナーの登録にディフェンダーが加わった（形式 2 以上の `effects` の値が変わる。test_coin_games.py の固定値は、この id を除いてハッシュを取るようにした）
  - 写しの対戦用のカードの組に、ディフェンダー（`pool_v0_2e`）が加わった
  - 不変条件が増えた: 番のプレイヤーがその番号の番の持ち主であること、ついているトレーナーの有効期限が「今の番 + `discard_turn_offset`」より先でないこと、使った番が使ったプレイヤーの番であること。場に残るトレーナーの実装を自分で加える場合は、`discard_turn_offset` を宣言する
- 新しいクライアントへの推奨: 状態の辞書は形式 4 を使う（ディフェンダーは相手の番もついている）。

### v0.2e → v0.2f

- 対戦の結果・ログ・状態（形式 4。登録表の id を除く）は、ピカチュウを使わない対戦では変わりません。v0.2e のコミット `2c3db11` と、既存のデッキ 6 組 × 40 seed（240 局、23,332 コマンド）を同じ方針で対戦させて比べ、すべて同じでした。v0.1 の参照データ・乱数とコインの固定値（test_reproducibility.py・test_coins.py・test_coin_games.py）も変わりません。
- v0.2e のテスト 401 件を v0.2f のコードで実行すると、失敗するのは登録表の id・登録したワザ・カードの組を確かめる 5 件だけ（[architecture-v0.2f.md 11 章](architecture-v0.2f.md) の表）。
- 互換でない変更:
  - 効果の登録表の id が `kyuura-engine-0.2f` になり、ワザの登録にピカチュウの 2 つ（PMCG1-035#0・#1）が加わった
  - 写しの対戦用のカードの組に、ピカチュウ（`pool_v0_2f`）が加わった
  - エラーコード `UNRESOLVED_SELF_DAMAGE_WEAKNESS_RESISTANCE` が加わった（対応カードでは起こらない）
  - 自分のワザで自分のポケモンがきぜつするようになった（相手がサイドを取る）。同時のきぜつでは、サイドの決定が両方のプレイヤーに、バトル場の決定が両方のプレイヤーに出る。クライアントは、決定のプレイヤーが番のプレイヤーと限らないことを前提にする（v0.1 の `PromoteActive` でも相手が答える場面はあった）
  - 対戦の中でサドン・デス（`Phase.SUDDEN_DEATH`）になることがある（v0.2e までの対応カードでは起こらなかった）
- `effects.damage_opponent_active` は残した（中身は `deal_attack_damage(…, OPPONENT_ACTIVE, …)`。ログの形は同じ）。
- 新しいクライアントへの推奨: ダメージの表示はログの `damage` の `player`・`pokemon`（`target` が `self` なら自分へのダメージ）を使う。同時のきぜつは `knock_out.simultaneous` で分かる。

### v0.2f → v0.3a

- どくのない対戦の結果・ログ・状態（形式 4。登録表の id を除く）は変わりません。v0.2f のコミット `5ce4d4e` と、既存のデッキ 7 組 × 40 seed（280 局、26,715 コマンド）を同じ手順で対戦させて比べ、すべて同じでした。どく状態のポケモンがいなければ、ポケモンチェックのログは今までどおり `pokemon_check` だけです。v0.1 の参照データ・乱数とコインの固定値も変わりません。
- v0.2f のテスト 449 件を v0.3a のコードで実行すると、失敗するのは登録表の id・登録したワザ・カードの組・知らない形式の例（5 が形式になった）を確かめる 6 件だけ（[architecture-v0.3a.md 12 章](architecture-v0.3a.md)）。
- 互換でない変更:
  - 効果の登録表の id が `kyuura-engine-0.3a` になり、ワザの登録にビードルのどくばり（PMCG1-004#0）が加わった。写しの対戦用のカードの組に `pool_v0_3a`
  - 書き出しの形式 5 が加わった（`FORMAT_VERSIONS` は 1〜5）。形式 1〜4 は特殊状態のポケモンがいると `ValueError`。形式 1 はポケモンチェックの中の決定も `ValueError`
  - `_end_turn` のあとに次の番がすぐ始まるとは限らない（ポケモンチェックの中のきぜつの決定を待つ）。そのあいだの `current_player` は番を終えたプレイヤー
  - エラーコード `UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`（`Phase.HALTED`）が加わった。正式な対戦で起こる（どくを直さないミラーでまれに）
  - `PokemonInPlay` の項目に `conditions` が加わった（位置引数の最後。既定は特殊状態なし）
  - 不変条件が増えた（特殊状態・番の進行・決定の続き）。ログを書きかえた状態や、ベンチのポケモンに特殊状態を付けた状態は `StateIntegrityError`
- 新しいクライアントへの推奨: 状態の辞書は形式 5 を使う。どくのダメージはログの `poison_damage` で、ワザの `damage` とは別に表示する。決定の `context` の `then` が `"next_turn"` なら、ポケモンチェックの中（次の番はまだ始まっていない）。

### v0.3a → v0.3b

- ねむり・マヒを使わない対戦の結果・ログ・乱数の状態は変わりません。v0.3a のコミット `1577bff` と、特殊状態を使わない既存のデッキ 7 組 × 40 seed、ビードルのデッキ × 40 seed、どくを直さないビードルのミラー × 400 seed（`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT` で止まる 5 局を含む）の 720 局（57,901 コマンド）を同じ手順で対戦させて比べ、終わった状態（形式 4・5。登録表の id を除く）がすべて同じでした。ビードルの 20 局は途中のすべての状態（ポケモンチェックの中の決定を含む）も同じでした。
- v0.3a のテスト 522 件を v0.3b のコードで実行すると、失敗するのは登録表の id・登録したワザ・カードの組を確かめる 5 件だけ（[architecture-v0.3b.md 12 章](architecture-v0.3b.md)）。
- 互換でない変更:
  - 効果の登録表の id が `kyuura-engine-0.3b` になり、ワザの登録にキャタピーのいとをはく（PMCG1-002#0）、パラスのひっかく（PMCG2-003#0）・キノコのほうし（PMCG2-003#1）が加わった。写しの対戦用のカードの組に `pool_v0_3b`
  - 形式 5 の `special_conditions` に `sleep`・`paralysis` の項目が加わった（どくだけの状態は v0.3a と同じ形）。v0.3a の形式 5 だけを知るクライアントは、知らない項目があれば拒否すること
  - `SpecialConditions` の項目に `exclusive` が加わった（キーワード引数。既定は None）
  - エラーコード `POKEMON_ASLEEP`・`POKEMON_PARALYZED`（`IllegalActionError`）、`UNRESOLVED_REPARALYSIS_RECOVERY_TURN`（`UnsupportedError`）、止めるコード `UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`（`Phase.HALTED`）が加わった。後の 2 つは対応カードでは起こらない
  - ポケモンチェックの中の決定（`then = "next_turn"`）のあと、次の番の前に 3・4 を行う（ねむりのコインを投げることがある）
  - `GameState.add_event` に `turn` の項目を渡すと `ValueError`（ログの番を上書きさせない）
  - 不変条件が増えた（`exclusive` の型、マヒの番、期限の過ぎたマヒ）
- 新しいクライアントへの推奨: ワザ・にげるのボタンは `special_conditions` の `sleep`・`paralysis` を見て無効にする（送っても拒否される）。ねむりのコインはログの `coin_flip`（`source: "pokemon_check"`）と `sleep_check` で表示する。マヒの回復する番は `special_condition` の `recovery_turn`（または `paralysis.turn` と `first_player`）で表示する。

### v0.3b → v0.3c

- こんらんを使わない対戦の結果・ログ・乱数の状態・拒否は変わりません。v0.3b のコミット `0516c05` と、特殊状態を使わない既存のデッキ 7 組・ビードル・キャタピー・パラス・v0.3b の混ぜたデッキ（直す／直さない）・どくを直さないビードルのミラーの 1,140 局（104,295 コマンド。`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT` で止まる 9 局を含む）と、でたらめな操作を混ぜた 16 局を同じ手順で動かして比べ、終わった状態（形式 5。登録表の id を除く）・ログ・乱数・拒否のコードの列がすべて同じでした。60 局は途中のすべての状態（ポケモンチェックの中の決定を含む）も同じでした（[architecture-v0.3c.md 13 章](architecture-v0.3c.md)）。
- v0.3b のテスト 613 件を v0.3c のコードで実行すると、失敗するのは登録表の id・登録したワザ・カードの組・形式の一覧を確かめる 6 件だけ。
- 互換でない変更:
  - 効果の登録表の id が `kyuura-engine-0.3c` になり、ワザの登録にロコンのあやしいひかり（PMCG1-015#0）が加わった。写しの対戦用のカードの組に `pool_v0_3c`
  - 形式 5 の `special_conditions` に `confusion` の項目が加わった。v0.3b の形式 5 だけを知るクライアントは、知らない項目があれば拒否すること
  - 形式 6 が加わった（`FORMAT_VERSIONS` は 1〜6）。「にげる」に失敗した記録のある状態は形式 1〜5 で書き出せない（`ValueError`）
  - `SpecialConditions.exclusive` の値に `Confused` が加わった。`PokemonInPlay` に `retreat_failed_turn`（キーワード引数。既定は None）が加わった
  - こんらん状態のポケモンの `UseAttack`・`Retreat` は、宣言が正しければ必ず受け付け、コインの結果で処理が変わる（「うら」でも例外にならない）
  - エラーコード `RETREAT_ALREADY_FAILED`（`IllegalActionError`）、`UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS`・`UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED`（`UnsupportedError`）が加わった
  - ログに `confusion_check`・`confusion_damage`・`retreat_failed` と、`coin_flip` の `source: "confusion"` が加わった
  - 不変条件が増えた（`Confused` の型、失敗の記録の番・持ち主・番の終わり）
  - `AttackEffect` に `problem` が加わった（既定は None。`SelfDamageOnTails` は v0.2f の未解決を、ワザを使う前に返す）
- 新しいクライアントへの推奨: こんらん状態のポケモンのワザ・にげるのボタンは無効にしない（コインを投げる）。`retreat_failed_turn` が今の番のポケモンの「にげる」は無効にする（送っても拒否される）。こんらんのコインはログの `coin_flip`（`source: "confusion"`）と `confusion_check`（`action`・`succeeded`）、自分への 20 は `confusion_damage` で表示する。

### v0.3c → v0.3d

- 対戦の結果・ログ・乱数の状態・拒否は変わりません。v0.3c のコミット `a4c66e2` と、既存のデッキの 1,340 局（121,420 コマンド）・でたらめな操作を混ぜた 32 局（8,162 コマンド、4,437 回の拒否）・v0.3d の 4 種類を混ぜたデッキの 300 局（44,122 コマンド）を同じ手順で動かして比べ、終わった状態（形式 6。登録表の id を除く）・ログ・乱数・拒否のコードの列がすべて同じでした（[architecture-v0.3d.md 9 章](architecture-v0.3d.md)）。
- v0.3c のテスト 687 件を v0.3d のコードで実行すると、失敗するのは 5 件だけ（自分へのダメージの弱点・抵抗力の停止を確かめる 3 件、失敗の記録を直接書いて不変条件を確かめる 2 件）。
- 互換でない変更:
  - 自分のタイプが自分の弱点・抵抗力のタイプのポケモンの、ワザによる自分へのダメージは、`UnsupportedError`（`UNRESOLVED_SELF_DAMAGE_WEAKNESS_RESISTANCE`）ではなく、弱点・抵抗力を計算して処理する（対応カードでは起こらない。テスト専用の登録で起こる）
  - `effects.self_damage_problem` を外した
  - 不変条件が増えた（失敗の記録とログの対応）。状態を直接作るテストは、記録に対応するログ `retreat_failed` も置くこと（tests/helpers.py の `build_test_state` は自動で置く）
- 新しいクライアントへの推奨: 変更なし。

### v0.3d → v0.4a

- 進化カードを使わない対戦の結果・ログ・乱数の状態・拒否は変わりません。v0.3d のコミット `3654be2` と、既存のデッキの 1,340 局（121,420 コマンド）・でたらめな操作を混ぜた 32 局（8,162 コマンド、4,437 回の拒否）・v0.3d の 4 種類を混ぜたデッキの 300 局（44,122 コマンド）を同じ手順で動かして比べ、終わった状態（形式 6。登録表の id を除く）・途中の状態・ログ・乱数・拒否のコードの列がすべて同じでした（[architecture-v0.4a.md 9 章](architecture-v0.4a.md)）。
- v0.3d のテスト 726 件を v0.4a のコードで実行すると、失敗するのは 11 件だけ（進化が未対応であること・登録表・形式の一覧を確かめるもの）。
- 互換でない変更:
  - `EvolvePokemon` を受け付ける（`UNSUPPORTED_COMMANDS` は `UsePokemonPower` だけ）。進化カードのない対戦では、進化のコマンドはルールによる拒否（`CARD_NOT_IN_HAND`・`NOT_EVOLUTION_CARD`・`WRONG_PHASE` など）になる。v0.1 の参照データの 43 回の進化のコマンドの拒否のコードが変わる（状態は同じ）
  - 効果の登録表の id が `kyuura-engine-0.4a` になり、ワザの登録にパラセクト・ジュゴンの 4 つが加わった。写しの対戦用のカードの組に `pool_v0_4a`
  - 形式 7 が加わった（`FORMAT_VERSIONS` は 1〜7）。進化したポケモンのいる状態は形式 1〜6 で書き出せない（`ValueError`）
  - `PokemonInPlay` に `evolution_stack`・`played_turn`・`evolved_turn`（キーワード引数。既定は `()`・0・None）。たねポケモン以外のポケモンのカードが進化していない場のポケモンになっていると、不変条件の違反
  - エラーコードとログのイベントが加わった（6・7 章）
- 新しいクライアントへの推奨: 状態の辞書は形式 7 を使う（v0.4b からは形式 8）。進化のボタンは、手札の 1 進化カードと、名前の合う場のポケモンのうち、`played_turn`・`evolved_turn`（`current_form_turn`）が今の番より前のものだけを有効にする（1・2 番は無効）。場のポケモンを指すときは `pokemon_id` を使う（進化するといちばん上のカードの uid が変わる）。

### v0.4a → v0.4b

- 持続する効果（「かたまる」）を使わない対戦の結果・ログ・乱数の状態・拒否・保留中の決定は変わりません。v0.4a のコミット `99c85d0` と、既存のデッキの 1,340 局（121,420 コマンド）・でたらめな操作を混ぜた 32 局（8,162 コマンド）・4 種類を混ぜたデッキの 300 局（44,122 コマンド）・進化を使う 40 局（5,964 コマンド。途中の状態も一部すべて）・進化を混ぜたでたらめな操作の 12 局（4,317 コマンド）を同じ手順で動かして比べ、終わった状態（形式 6・7。登録表の id を除く）・途中の状態・ログ・乱数・拒否のコードの列がすべて同じでした（[architecture-v0.4b.md 13 章](architecture-v0.4b.md)）。
- v0.4a のテスト 776 件を v0.4b のコードで実行すると、失敗するのは 7 件だけ（登録表の id・ワザの数・説明文のあるワザの一覧・形式の一覧・カードの組を固定したもの）。
- 互換でない変更:
  - 効果の登録表の id が `kyuura-engine-0.4b` になり、ワザの登録にトランセル・コクーンの 4 つが加わった。写しの対戦用のカードの組に `pool_v0_4b`
  - 形式 8 が加わった（`FORMAT_VERSIONS` は 1〜8）。持続する効果を受けているポケモンのいる状態は形式 1〜7 で書き出せない（`ValueError`）
  - `PokemonInPlay` に `persistent_effects`（キーワード引数。既定は `()`）
  - 照合の記録（`card_verification.json`）の、説明文のあるワザが 2 つあるカードの `card_image_text_ja`・`latest_description_ja` は、ワザの位置ごとの辞書
  - エラーコード（`UNRESOLVED_PREVENTED_COIN_DAMAGE`）とログのイベント（`persistent_effect_added`・`persistent_effect_removed`・`damage_prevented`）が加わった（6・7 章）
- 新しいクライアントへの推奨: 状態の辞書は形式 8 を使う。「ダメージを受けない」状態は、場のポケモンの `persistent_effects` のうち `active_turn` が今の番のもの。ドードーの「みだれづき」を「ダメージを受けない」ポケモンに使うと `UnsupportedError`（原典で決められない）になるので、ボタンを無効にするか、拒否を表示する。

### v0.4b → v0.4c

- 2 進化のカード（スピアー）を使わない対戦の結果・ログ・乱数の状態・拒否・保留中の決定は変わりません。v0.4b のコミット `d21369a` と、既存のデッキの 1,340 局（121,420 コマンド）・でたらめな操作の 32 局・4 種類を混ぜたデッキの 300 局（44,122 コマンド）・1 進化を使う 40 局（5,964 コマンド）と、でたらめな進化の 12 局・「かたまる」を使う 40 局（5,880 コマンド。途中の状態と保留中の決定をすべて形式 8 で）と、でたらめな操作の 16 局を同じ手順で動かして比べ、出力がすべて同じでした（[architecture-v0.4c.md 13 章](architecture-v0.4c.md)）。
- v0.4b のテスト 825 件を v0.4c のコードで実行すると、失敗するのは 9 件だけ（登録表の id・ワザの数・説明文のあるワザの一覧・カードの組・フシギバナの未対応の理由を固定したもの）。
- 互換でない変更:
  - 効果の登録表の id が `kyuura-engine-0.4c` になり、ワザの登録にスピアーの 2 つが加わった。写しの対戦用のカードの組に `pool_v0_4c`
  - 2 進化のカードの未対応の理由から「2 進化」がなくなった（フシギバナはポケモンパワーと登録のないワザで未対応のまま）
  - `PokemonInPlay.evolution_stack` が 2 枚になることがある（形式 7・8 の `evolution_stack` のリストが 2 つになる。項目は同じ）
  - エラーコード `EVOLUTION_STAGE_MISMATCH`（実在のカードの組では起こらない）
- 新しいクライアントへの推奨: 進化のボタンは、手札の進化カード（1 進化・2 進化）と、名前の合う場のポケモン（2 進化なら 1 進化ポケモン）のうち、`current_form_turn` が今の番より前のものだけを有効にする。同じ番に 1 進化させたポケモンは、その番には 2 進化できない。スピアーの「ダブルニードル」を「ダメージを受けない」ポケモンに使うと、みだれづきと同じく `UnsupportedError`。

### v0.4c → v0.4d

- バタフリーを使わない対戦の結果・ログ・乱数の状態・拒否・保留中の決定は変わりません。v0.4c のコミット `7ed8ef5` と、既存のデッキの 1,340 局（121,420 コマンド）・でたらめな操作の 32 局・4 種類を混ぜたデッキの 300 局（44,122 コマンド）・1 進化を使う 40 局とでたらめな進化の 12 局・「かたまる」を使う 40 局（5,880 コマンド）とでたらめな操作の 16 局・2 進化を使う 40 局（4,369 コマンド。途中の状態と保留中の決定をすべて形式 8 で）とでたらめな操作の 16 局・テスト専用のワザの途中の決定を使う 60 局を同じ手順で動かして比べ、出力がすべて同じでした（[architecture-v0.4d.md 14 章](architecture-v0.4d.md)）。
- v0.4c のテスト 892 件を v0.4d のコードで実行すると、失敗するのは 10 件だけ（登録表の id・ワザの数・説明文のあるワザの一覧・カードの組を固定したもの 9 件と、形式 1 でワザの途中の決定を書き出していた 1 件）。
- 互換でない変更:
  - 効果の登録表の id が `kyuura-engine-0.4d` になり、ワザの登録にバタフリーの 2 つが加わった。写しの対戦用のカードの組に `pool_v0_4d`
  - `state_to_dict(state, format_version=1)` は、ワザの途中の決定（`decision.resume == "attack"`）があると `ValueError`（v0.4c までは段階 `decision` だけが書き出され、決定の中身が落ちていた。製品のカードでは起こらなかった）。形式 2 以上を使う
  - `deal_attack_damage`・`damage_opponent_active` が `None` ではなく `DamageResult` を返す
  - 決定を待つ状態で、`decision.player` が番のプレイヤーと違うことがある（`forced_switch`）。「決定するのは番のプレイヤー」と決めつけていたクライアントは直す必要がある
- 新しいクライアントへの推奨: 決定の表示・答えは、いつも `state.decision.player` を見て、そのプレイヤーに求める（番のプレイヤーではない）。`forced_switch` の選べるもの（`options`）は相手のベンチのポケモンの番号。決定を待つ間は、どちらのプレイヤーにも通常の操作のボタンを出さない。

### v0.4d → v0.4e

- 受け付ける操作・拒否のコード・状態・ログ・乱数の状態・保留中の決定・形式 1〜8 の書き出しは、v0.4d（`4bd97bf`）と同じです。リポジトリの道具（tools/compare_engine_versions.py）で、8 組 50 局・11,377 手を版ごとに別のプロセスで動かして比べ、食い違いは 0 でした（[compatibility-v0.4e.md](compatibility-v0.4e.md)）。
- v0.4d のテスト 958 件は、v0.4e のコードで変更なしにすべて通ります。
- 互換でない変更: `check_invariants` が、v0.4d では見つけなかった壊れた状態（呼び出し側が書き換えたトレーナーの決定・サイドと交代の決定・番の番号）を問題として返す。そのような状態を `apply_command` に渡していたクライアントは、壊れた状態を作らないように直す必要がある（正しい状態は変わらず受け付ける）。

### v0.4e → v0.5

- フシギダネ・フシギソウ・フシギバナを使わない対戦の、受け付ける操作・拒否のコード・状態・ログ・乱数の状態・保留中の決定・形式 1〜8 の書き出しは、v0.4e（`c1e13ec`）と同じです。tools/compare_engine_versions.py で、8 組 50 局・11,377 手を版ごとに別のプロセスで動かして比べ、食い違いは 0 でした（比べないのは効果の登録表の id だけ。[v0.5-verification.md](v0.5-verification.md)）。
- v0.4e のテスト 1,032 件を v0.5 のコードで実行すると、失敗・エラーが 32 件（subTest を含む。テストの数では 21 件）でした（登録表の id・ワザの数・カードの組・照合の記録を固定したもの、フシギバナを未対応の例にしたもの、`UsePokemonPower` を `UNSUPPORTED_ACTION` とするもの）。どれも意図を変えずに直しました（[architecture-v0.5.md](architecture-v0.5.md) 8 章）。
- 互換でない変更:
  - `UsePokemonPower` が `UnsupportedError("UNSUPPORTED_ACTION")` ではなく、ルールによる拒否（`WRONG_PHASE`・`NOT_YOUR_TURN`・`POKEMON_NOT_IN_PLAY`・`NO_POKEMON_POWER` など）か、登録のないパワーなら `UNSUPPORTED_POKEMON_POWER` になる。`pokemon` は場のポケモンの番号として読む（v0.1 の 2 つの項目の辞書も読めるが、カードの uid のつもりの値は場のポケモンの番号として扱われる）。v0.1 の参照データの 36 回のコマンドの拒否のコードが変わる（状態は同じ。tests/test_compat_v0_1.py）
  - `command_to_dict(UsePokemonPower(...))` は 6 つの項目を書き出す（v0.4e までは 2 つ）
  - 効果の登録表の id が `kyuura-engine-0.5` になり、ワザの登録が 4 つ、パワーの登録が 1 つ加わった。`EffectRegistry(...)` の 4 番目の引数（`powers`）、`describe()` の `"powers"`
  - フシギバナ（PMCG1-011）は参照カードではなくなった（対戦で使える）。参照カードはカメックス（PMCG1-032）
- 新しいクライアントへの推奨: 特殊能力のボタンは、自分の番の `Phase.MAIN` で、自分の場のポケモンのうち `state.card_def(pokemon.card).powers` があり `supported` のものに出す。エナジートランスは、移すエネルギー（自分の場のポケモンについている「草」の基本エネルギー）と移動先（移動元以外の自分の場のポケモン）を選ばせて、1 枚ごとに 1 つのコマンドを送る。

### v0.5 → v0.6

- ゼニガメ・カメール・カメックスを使わない対戦の、受け付ける操作・拒否のコード・状態・ログ・乱数の状態・保留中の決定・形式 1〜8 の書き出しは、v0.5（`0fbc3ab`）と同じです。tools/compare_engine_versions.py で、8 組 50 局・11,377 手を版ごとに別のプロセスで動かして比べ、食い違いは 0 でした（比べないのは効果の登録表の id だけ。[v0.6-verification.md](v0.6-verification.md)）。
- v0.5 のテスト 1,093 件を v0.6 のコードで実行すると、失敗・エラーが 25 件でした（登録表の id・ワザとパワーの数・カードの組を固定したもの、カメックスを未対応の例にしたもの、形式の一覧を 8 までと固定したもの、未解決のコードの一覧）。どれも意図を変えずに直しました（[architecture-v0.6.md](architecture-v0.6.md) 11 章）。
- 互換でない変更:
  - あまごいでつけた枚数が 0 でない状態（あまごいを使った番のあいだ）は、形式 1〜8 で書き出せない（`ValueError`）。形式 9 を使う
  - あまごいでつけたあと、その番にまだ通常の操作をしていないときの `AttachEnergy` は `UnsupportedError`（`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`）。v0.5 にはこの状態がない
  - 効果の登録表の id が `kyuura-engine-0.6` になり、ワザの登録が 5 つ、パワーの登録が 1 つ加わった
  - カメックス（PMCG1-032）は参照カードではなくなった（対戦で使える）。参照カードはフーディン（PMCG1-049）
  - エナジートランスの特殊状態の拒否のメッセージの文（コードは同じ）
- 新しいクライアントへの推奨: あまごいは、手札の「水」の基本エネルギーと、自分の場の「水」ポケモン（`state.card_def(pokemon.card).pokemon_type`）を選ばせて、1 枚ごとに 1 つのコマンドを送る。あまごいを使った番に、まだ通常の操作でつけていなければ、通常の操作のボタンは出さない（原典で決められないので、エンジンは止める）。

### v0.6 → v0.7

- ケーシィ・ユンゲラー・フーディンを使わない対戦の、受け付ける操作・拒否のコード・状態・ログ・乱数の状態・保留中の決定・形式 1〜8 の書き出しは、v0.6（`787fff9`）と同じです。tools/compare_engine_versions.py で、8 組 50 局・11,377 手を版ごとに別のプロセスで動かして比べ、食い違いは 0 でした（比べないのは効果の登録表の id だけ。[v0.7-verification.md](v0.7-verification.md)）。
- v0.6 のテスト 1,152 件を v0.7 のコードで実行した結果と、意図を変えずに直したテストは [architecture-v0.7.md](architecture-v0.7.md) 11 章・[v0.7-verification.md](v0.7-verification.md) 2 章。
- 互換でない変更:
  - 効果の登録表の id が `kyuura-engine-0.7` になり、ワザの登録が 4 つ、パワーの登録が 1 つ加わった
  - フーディン（PMCG1-049）は参照カードではなくなった（対戦で使える）。参照カードはリザードン（PMCG1-021）
  - 決定の種類 `discard_energy` が加わった（クライアントは、知らない種類の決定も `options` から `min_choices`〜`max_choices` 個を選んで答えられる）
- 新しいクライアントへの推奨: ダメージスワップは、ダメージカウンターがのった自分の場のポケモンと、移動先の自分の場の別のポケモン（のせたあとのダメージが HP より小さいもの。`effects.would_be_knocked_out`）を選ばせ、1 個ごとに 1 つのコマンドを送る。

### v0.7 → v0.8

- ベトベター・ベトベトンを使わない対戦の、受け付ける操作・拒否のコード・状態・ログ・乱数の状態・保留中の決定・形式 1〜8 の書き出しは、v0.7（`22cbe24`）と同じです。tools/compare_engine_versions.py で、8 組 50 局・11,377 手を版ごとに別のプロセスで動かして比べ、食い違いは 0 でした（比べないのは効果の登録表の id だけ。[v0.8-verification.md](v0.8-verification.md)）。
- v0.7 のテストを v0.8 のコードで実行した結果と、意図を変えずに直したテストは [architecture-v0.8.md](architecture-v0.8.md) 12 章・[v0.8-verification.md](v0.8-verification.md) 4.3。
- 互換でない変更:
  - 効果の登録表の id が `kyuura-engine-0.8` になり、ワザの登録が 3 つ、パワーの登録が 1 つ加わった
  - ベトベトンが場にいて、ねむり・マヒ・こんらんでないあいだは、エナジートランス・あまごい・ダメージスワップの `UsePokemonPower` が `POWER_SUPPRESSED`（v0.7 にはベトベトンがいないので、v0.7 で受け付けた操作が拒否に変わることはない）
- 新しいクライアントへの推奨: 特殊能力のボタンを出す前に `power_suppressors(state, pokemon_id, power_index)` を聞き、空でなければ「かがくへんかガス（場のポケモン ○○）で使えない」と示す。かがくへんかガスのボタンは出さない（宣言しない）。

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

v0.1 からあるコマンドは、場のポケモンをカードの uid で指します。v0.2a で場のポケモンの番号（`pokemon_id`）を加え、`ResolveDecision` の選べるものは番号になりました。進化を実装するときの移行の手順は [アーキテクチャ 5 章](architecture-v0.2a.md#コマンドの移行の方針) にあります。v0.4a で、進化しても `pokemon_id` を変えず、`EvolvePokemon.target` を `pokemon_id` にしました（v0.3d の調査の推奨。[evolution-state-v0.4a.md](evolution-state-v0.4a.md) 2 章）。v0.1 からのコマンドの uid は、いちばん上のカードの uid だけで指します（重なりの下のカードでは指せない）。

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
| `IllegalActionError` | ALREADY_PLACED, BAD_COMMAND, BENCH_FULL, CARD_NOT_IN_HAND, DUPLICATE_CARD, DUPLICATE_CHOICE（v0.2a）, ENERGY_ALREADY_ATTACHED, ENERGY_NOT_ATTACHED, GAME_OVER, INSUFFICIENT_ENERGY, INVALID_ATTACK, INVALID_CHOICE（v0.2a）, INVALID_CHOICE_COUNT（v0.2a）, INVALID_DRAW_COUNT, INVALID_PLAYER, INVALID_PRIZE_INDEX, NOT_BASIC_ENERGY, NOT_BASIC_POKEMON, NOT_ON_BENCH, NOT_TRAINER（v0.2b）, NOT_YOUR_DECISION, NOT_YOUR_TURN, NO_BENCH, NO_MULLIGAN_DRAW, POKEMON_ASLEEP（v0.3b）, POKEMON_PARALYZED（v0.3b）, RETREAT_ALREADY_FAILED（v0.3c）, NOT_EVOLUTION_CARD・FIRST_TURN_EVOLUTION・EVOLUTION_NAME_MISMATCH・PLAYED_THIS_TURN・EVOLVED_THIS_TURN（v0.4a）, EVOLUTION_STAGE_MISMATCH（v0.4c）, SETUP_BENCH_LIMIT, TARGET_NOT_IN_PLAY, TARGET_NOT_YOURS, UNKNOWN_COMMAND, WRONG_DECISION（v0.2a）, WRONG_PHASE, WRONG_RETREAT_COST, NO_POKEMON_POWER（v0.5）, POKEMON_NOT_IN_PLAY（v0.5）, POKEMON_NOT_YOURS（v0.5）, POKEMON_CONFUSED（v0.5。エナジートランス）, POWER_CHOICE_MISSING（v0.5）, SOURCE_NOT_IN_PLAY（v0.5）, SOURCE_NOT_YOURS（v0.5）, SAME_POKEMON（v0.5）, WRONG_ENERGY_TYPE（v0.5）, WRONG_POKEMON_TYPE（v0.6。あまごいのつける先が「水」ポケモンでない）, POWER_CHOICE_NOT_USED（v0.6。パワーが使わない項目を指定した）, NO_DAMAGE_COUNTERS（v0.7。ダメージスワップの移動元にダメージカウンターがない）, WOULD_KNOCK_OUT（v0.7。ダメージスワップの移動先に 1 個のせるときぜつする）。POWER_NOT_DECLARABLE（v0.8。常にはたらいていて宣言しない特殊能力（かがくへんかガス）の使用）, POWER_SUPPRESSED（v0.8。はたらいているかがくへんかガスに消されている特殊能力の使用）。POKEMON_ASLEEP・POKEMON_PARALYZED・TARGET_NOT_IN_PLAY・TARGET_NOT_YOURS・ENERGY_NOT_ATTACHED は v0.5 のエナジートランスでも使う。v0.6 のあまごいは POKEMON_ASLEEP・POKEMON_PARALYZED・POKEMON_CONFUSED・POWER_CHOICE_MISSING・CARD_NOT_IN_HAND・NOT_BASIC_ENERGY・WRONG_ENERGY_TYPE・TARGET_NOT_IN_PLAY・TARGET_NOT_YOURS も使う。v0.7 のダメージスワップは POKEMON_ASLEEP・POKEMON_PARALYZED・POKEMON_CONFUSED・POWER_CHOICE_MISSING・POWER_CHOICE_NOT_USED・SOURCE_NOT_IN_PLAY・SOURCE_NOT_YOURS・TARGET_NOT_IN_PLAY・TARGET_NOT_YOURS・SAME_POKEMON も使う |
| `UnsupportedError` | SUDDEN_DEATH_NOT_IMPLEMENTED, UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS（v0.3c）, UNRESOLVED_MULLIGAN_COMPENSATION, UNRESOLVED_POTION_UNDAMAGED_TARGET（v0.2b）, UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT（v0.3a。HALTED）, UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER（v0.3b。HALTED）, UNRESOLVED_POTION_WITHOUT_DAMAGE（v0.2b）, UNRESOLVED_REPARALYSIS_RECOVERY_TURN（v0.3b）, UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED（v0.3c）, UNRESOLVED_SELF_DAMAGE_WEAKNESS_RESISTANCE（v0.2f〜v0.3c。v0.3d から出ない）, UNRESOLVED_SWITCH_WITHOUT_BENCH（v0.2b）, UNRESOLVED_EVOLUTION_HP（v0.4a）, UNRESOLVED_PREVENTED_COIN_DAMAGE（v0.4b）, UNSUPPORTED_ACTION, UNSUPPORTED_ATTACK, UNSUPPORTED_EVOLUTION（v0.4a）, UNSUPPORTED_TRAINER（v0.2b）, UNSUPPORTED_POKEMON_POWER（v0.5。登録のないポケモンパワー）, UNRESOLVED_ATTACH_AFTER_POWER_ATTACH（v0.6。あまごいでつけたあとの通常の操作）。UNSUPPORTED_ACTION は v0.5 から出ない（`UNSUPPORTED_COMMANDS` が空） |
| `DeckValidationError` | INVALID_DECK（`problems` の各行の先頭: DECK_SIZE, UNKNOWN_CARD, UNSUPPORTED_CARD, TOO_MANY_COPIES, NO_BASIC_POKEMON） |
| `StateIntegrityError` | STATE_INTEGRITY（エンジンの不具合か、呼び出し側が状態を書き換えた） |

## 7. ログのイベント

`state.log` の各要素は読み取り専用の辞書で、`kind` と `turn`（その時点の番数）を持ちます。v0.2a で、製品の処理が出すイベントは変わっていません（決定そのものはログに残さない）。v0.2b でトレーナーのイベントを加えました（既存のイベントの形は変えていない）。ログは内部の完全な記録で、隠れた情報（`draw` の `cards` など）を含みます。見る人ごとのログはありません（[v0.2b のアーキテクチャ 9 章](architecture-v0.2b.md#9-非公開の情報とログ)）。

`game_created`, `shuffle`, `draw`, `mulligan`（見せた手札）, `halted`, `place_starting_pokemon`, `set_prizes`, `mulligan_draw`, `janken`, `reveal_pokemon`, `turn_start`, `deck_out`, `play_to_bench`, `attach_energy`, `retreat`, `attack`, `damage`（計算の段階を含む）, `knock_out`, `take_prize`, `promote_active`, `end_turn_without_attack`, `turn_end`, `pokemon_check`, `game_end`

v0.2c: `attach_trainer`（`player`・`card`・`pokemon`・`pokemon_id`・`discard_at_end_of_turn`）, `discard_attached_trainer`（同じ項目と `reason`＝`end_of_turn`）。v0.2e のディフェンダーも同じイベントを使う（`discard_at_end_of_turn` は使った番 + 1。`damage` の `modifiers` に `(7, カードの uid, -20)`）。`damage` に `modifiers`（`(段階, カードの uid, 加えた数)`。変更効果があるときだけ）、`knock_out` に `discarded_trainers`（ついていたトレーナーがあるときだけ）

v0.2d: `coin_flip`（`player`・`source`＝`attack`・`effect`＝`AttackKey` の文字列・`card`＝カードの uid・`pokemon_id`・`number`＝何枚目（1 から）・`count`＝投げる枚数・`result`＝`heads`/`tails`）。`damage` に `stopped_after_step_2`（2 段階のあとで計算を終えたときだけ。「おもて」0 枚のみだれづきなど）

v0.2f: `damage` に、相手の対戦ポケモン以外へのダメージのときだけ `target`（`self`）・`pokemon_id`（受けたポケモン）・`effect`（ワザの識別子。例 `PMCG1-035#1`）。`player` は受けたポケモンの持ち主（自分へのダメージならワザを使ったプレイヤー）。`knock_out` に、1 つのワザで 2 匹以上きぜつしたときだけ `simultaneous`（`true`）

v0.3a: `special_condition`（`player`＝特殊状態になったポケモンの持ち主・`pokemon`・`pokemon_id`・`condition`＝`poison`・`damage`・`effect`＝効果の識別子、もうその状態なら `already`）, `special_conditions_removed`（`player`・`pokemon`・`pokemon_id`・`conditions`・`reason`＝`retreat`/`switch`）, `poison_damage`（ポケモンチェックの「どく」。`player`・`pokemon`・`pokemon_id`・`amount`・`total_damage`。ワザの `damage` とは別）。`knock_out` に、ポケモンチェックの中のきぜつなら `timing`（`pokemon_check`）。`halted` はポケモンチェックで止めたときも出る（`code` だけ）。どく状態のポケモンがいなければ、`pokemon_check` のあとに新しいイベントは出ない

v0.3b: `special_condition` の `condition` に `sleep`・`paralysis`（マヒなら `paralyzed_turn`＝マヒ状態になった番・`recovery_turn`＝回復する番）。`special_conditions_removed` の `reason` に `sleep_coin`（ねむりのコインの「おもて」）・`paralysis_end`（マヒの回復）・`replaced`（ねむり・マヒが置きかわった）。`coin_flip` の `source` に `pokemon_check`（`effect`＝`sleep`、`player`＝ねむりのポケモンの持ち主、`card`・`pokemon_id`＝ねむりのポケモン）。`sleep_check`（`player`・`pokemon`・`pokemon_id`・`result`・`recovered`）。ねむり・マヒのポケモンがいなければ、v0.3a と同じログ

v0.3c: `special_condition` の `condition` に `confusion`。`special_conditions_removed` の `conditions` に `confusion`（`reason` は `retreat`・`switch`・`replaced`）。`coin_flip` の `source` に `confusion`（`effect`＝ワザの `AttackKey` の文字列か `retreat`、`player`＝こんらん状態のポケモンの持ち主、`card`・`pokemon_id`＝そのポケモン）。`confusion_check`（`player`・`pokemon`・`pokemon_id`・`action`＝`attack`/`retreat`・`result`・`succeeded`）。`confusion_damage`（ワザがこんらんしたときの自分への 20。`player`・`pokemon`・`pokemon_id`・`effect`・`amount`・`steps`・`weakness`・`resistance`・`total_damage`。ワザによるダメージの `damage` とは別）。`retreat_failed`（`player`・`pokemon`・`pokemon_id`・`discarded`）。こんらんのポケモンがいなければ、v0.3b と同じログ

v0.4a: `evolve`（`player`・`pokemon_id`・`from_card`＝進化前のいちばん上のカードの uid・`from_card_id`・`to_card`＝進化カードの uid・`to_card_id`。番はログの `turn`）。`special_conditions_removed` の `reason` に `evolve`。`retreat_failure_cleared`（`player`・`pokemon`・`pokemon_id`・`reason`＝`evolve`。こんらんで「にげる」に失敗した記録が進化で消えた）。`knock_out` に、進化したポケモンのきぜつなら `evolution_stack`（下のカードの uid。`pokemon` はいちばん上のカード）。進化しない対戦では、v0.3d と同じログ

v0.4b: `persistent_effect_added`（`player`・`pokemon`・`pokemon_id`・`persistent_effect`＝種類（`prevent_damage`）・`source_card`・`source_player`・`active_turn`＝はたらく番・`effect`＝ワザの `AttackKey`。効果を与えた番はログの `turn`）。`persistent_effect_removed`（`player`・`pokemon`・`pokemon_id`・`persistent_effect`・`source_card`・`created_turn`・`active_turn`・`reason`＝`expired`・`retreat`・`switch`・`evolve`・`knock_out`）。`damage_prevented`（`player`・`pokemon`・`pokemon_id`・`target`・`effect`＝ワザ・`persistent_effect`・`source_card`。「ダメージを受けない」状態のポケモンへのダメージの要素が無効になった。計算しないので量はない）。持続する効果を使わない対戦では、v0.4a と同じログ

v0.4d: `forced_switch`（`player`＝入れ替えられたプレイヤー・`attacker`＝ワザを使ったプレイヤー・`attacker_pokemon_id`・`effect`＝ワザの `AttackKey`・`old_active`・`new_active`・`old_active_pokemon_id`・`new_active_pokemon_id`）、`forced_switch_skipped`（`player`・`attacker`・`attacker_pokemon_id`・`effect`・`pokemon`・`pokemon_id`・`reason`＝`knocked_out`/`no_bench`）、`drain_heal`（`player`・`pokemon`・`pokemon_id`・`effect`・`dealt`＝回復の計算のもとにした与えたダメージ・`drain_counters`＝半分の切り上げ・`counters`＝とりのぞいた数・`amount`・`damage_before`・`total_damage`）。`special_conditions_removed`・`persistent_effect_removed` の `reason` に `forced_switch`。既存のイベント（`switch`・`remove_damage_counters`・`damage`・`damage_prevented` など）の形は変えていない。

v0.4c: 新しいイベント・項目はない。2 進化の `evolve` は、`from_card` が 1 進化ポケモン（コクーン）、`to_card` が 2 進化カード（スピアー）。2 進化ポケモンの `knock_out` の `evolution_stack` は下の 2 枚（たねポケモン・1 進化ポケモンの順）

v0.5: `pokemon_power`（`player`・`pokemon`＝使うポケモンのいちばん上のカードの uid・`pokemon_id`・`power`＝特殊能力の名前・`power_index`。p.311 の宣言）、`move_energy`（`player`・`pokemon`・`pokemon_id`＝特殊能力を使ったポケモン・`power`＝`PowerKey` の文字列（`PMCG1-011@power0`）・`energy`＝移したエネルギーの uid・`from_pokemon_id`・`to_pokemon_id`）。1 回の使用で `pokemon_power` のすぐあとに `move_energy` が 1 つ。手札からつけた `attach_energy` とは別のイベント。やどりぎのタネは v0.4d のメガドレインと同じ `drain_heal`（`drain_counters` は 1）、どくのこなは `special_condition`（`effect`＝`PMCG1-008#1`）。

v0.6: `power_attach_energy`（`player`・`pokemon`・`pokemon_id`＝特殊能力を使ったポケモン・`power`＝`PowerKey` の文字列（`PMCG1-032@power0`）・`energy`＝手札からつけたエネルギーの uid・`to_pokemon_id`）。1 回の使用で `pokemon_power` のすぐあとに 1 つ。手札からつける通常の操作の `attach_energy`・エナジートランスの `move_energy` とは別のイベント。ゼニガメの「あわ」は `special_condition`（`effect`＝`PMCG1-023#0`）、「からにこもる」は v0.4b の `persistent_effect_added`。ハイドロポンプは `damage` だけ（追加のダメージは基本となるダメージに入る）。

v0.7: `move_damage_counter`（`player`・`pokemon`・`pokemon_id`＝特殊能力を使ったポケモン・`power`＝`PowerKey` の文字列（`PMCG1-049@power0`）・`count`＝1・`from_pokemon_id`・`to_pokemon_id`・`from_total_damage`・`to_total_damage`＝移したあとのダメージ）。1 回の使用で `pokemon_power` のすぐあとに 1 つ。`discard_energy`（`player`・`pokemon`・`pokemon_id`・`effect`＝ワザの `AttackKey`・`energy`＝トラッシュしたエネルギーカードの uid）と `remove_all_damage_counters`（`player`・`pokemon`・`pokemon_id`・`effect`・`counters`・`amount`・`damage_before`・`total_damage`）はユンゲラーの「じこさいせい」（決定に答えたあと、この順番で 1 つずつ）。`damage`・`remove_damage_counters`・`drain_heal`・`move_energy` の形は変えていない。

v0.8: 新しいイベント・項目はない。かがくへんかガスがはたらき始めた・消えたことはログに残さない（状態から求める。原因の `evolve`・`knock_out`・`special_condition`・`special_conditions_removed` などは今までどおり）。消されて使えなかった特殊能力の使用は拒否で、`pokemon_power` も残らない。どくガスは `special_condition` だけ（`damage` なし・コインなし）、ねばりつくは `coin_flip` → `damage`（「おもて」なら 20 を加えた基本となるダメージ）→ `special_condition`（`paralysis`）、ヘドロこうげきは `damage` → `coin_flip` → `special_condition`（`poison`）。

v0.2b: `play_trainer`（`player`・`card`・`trainer`＝名前）, `remove_damage_counters`（`pokemon`・`pokemon_id`・`counters`＝とりのぞいた個数・`total_damage`）, `switch`（`old_active`・`new_active`・それぞれの `pokemon_id`）, `discard_trainer`（`player`・`card`）。マサキの引いたカードは `draw`（番の最初のドローと同じ形）

ログはテストでも使っているので、事実上の API です。種類と各項目を変えるときは、この一覧、test_reproducibility.py の固定値、v0.1 の参照データ（tests/fixtures）との関係を合わせて見直してください。場のポケモンを指す項目は、v0.1 からのイベントはいちばん上のカードの uid です（進化するとそのポケモンのいちばん上の uid は変わる）。v0.2c 以降のイベントと進化のイベントは `pokemon_id` も持ちます。
