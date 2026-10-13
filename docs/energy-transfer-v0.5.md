# エナジートランスの処理（v0.5）

フシギバナのポケモンパワー「エナジートランス」の、コマンド・確かめる順番・状態の変化・ログ・ほかの処理との関係です。根拠の照合は [venusaur-v0.5.md](venusaur-v0.5.md)（カード）・[pokemon-powers-v0.5.md](pokemon-powers-v0.5.md)（一般の規定）。

最新の説明（p.16・p.323）: 「この力は、自分の番の中で何度でも使える。自分の場にいるポケモンについている「草」エネルギーを、自分の場にいる別のポケモンにつけかえる。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は使えない。」

## 1. コマンドの形（B4）

```python
UsePokemonPower(player, pokemon, power=0, energy=None, source=None, target=None)
```

| 項目 | 意味 |
|---|---|
| `player` | 使うプレイヤー（番のプレイヤー） |
| `pokemon` | 特殊能力を使う自分の場のポケモンの番号（`pokemon_id`）。バトル場でもベンチでもよい |
| `power` | 特殊能力の位置（カードに印刷された順、0 から）。フシギバナは 0 |
| `energy` | つけかえるエネルギーカードの uid |
| `source` | そのエネルギーがついている自分の場のポケモンの番号（移動元） |
| `target` | つけかえる先の、自分の場の別のポケモンの番号（移動先） |

決めた理由（案 A「コマンドに明示する」と案 B「決定（`PendingDecision`）で選ばせる」の比較）:

- 選ぶものは 3 つ（エネルギー・移動元・移動先）で、どれも宣言の時点で場に見えている。選ぶ順番で選べるものが変わらない（移動元はエネルギーで決まり、移動先は移動元以外の自分のポケモン）。決定にすると、2〜3 段階の決定（エネルギー → 移動先）と、その途中の状態（宣言したが処理していない）が要り、書き出しの形式 1〜8 で表せない状態（形式 9）が生まれる。
- p.311 の「特殊能力の使用を宣言したら、…すべてすませてから」は、1 つのコマンドで処理を終えれば自然に満たされる。
- 案 A にしたので、決定（`Phase.DECISION`）・再開先・書き出しの形式を加えていない（形式は 1〜8 のまま。形式 9 はない）。
- 場のポケモンは場のポケモンの番号で指す（v0.4a の `EvolvePokemon.target` と同じ。ベンチも指せ、進化しても変わらない）。エネルギーはカードの uid（v0.1 から、カードは uid）。
- v0.4e までの 2 つの項目（`player`・`pokemon`）だけの形（`command_from_dict` の辞書）も読める（ほかの項目は既定の値）。v0.1 の参照データの 36 回のコマンドも読め、ルールによる拒否になる（tests/test_compat_v0_1.py）。
- 決定を出すパワー（選ぶものが処理の途中で決まるもの）を加えるときは、案 B の形（`PowerEffect.resume`・`decision_problems`・再開先）を加える（[architecture-v0.5.md](architecture-v0.5.md) 9 章）。

## 2. 確かめる順番（状態を変える前にすべて）

拒否したら、状態・乱数・ログは変わらない（`apply_command` は複製した状態で処理する。v0.1 から）。

| 順 | 確かめること | コード | 場所 |
|---|---|---|---|
| 1 | コマンドの項目の型（整数、選ばせるものは整数か None。bool・文字列は不可） | `BAD_COMMAND` | `commands.check_command_fields` |
| 2 | 対戦が終わっていない・止まっていない | `GAME_OVER`・止めた理由のコード | `apply_command` |
| 3 | 段階が `Phase.MAIN`（決定を待つ間・対戦準備・サイド・バトル場に出す段階は不可） | `WRONG_PHASE` | `engine._require_turn` |
| 4 | プレイヤーの番号・番のプレイヤー | `INVALID_PLAYER`・`NOT_YOUR_TURN` | 同上 |
| 5 | 使うポケモンが自分の場にいる | `POKEMON_NOT_YOURS`（相手の場）・`POKEMON_NOT_IN_PLAY` | `engine._use_pokemon_power` |
| 6 | いちばん上のカードに、その位置の特殊能力がある | `NO_POKEMON_POWER` | 同上 |
| 7 | 特殊能力の実装が登録されていて、データと合う | `UNSUPPORTED_POKEMON_POWER`（`UnsupportedError`） | 同上 |
| 8 | このカードがねむり・マヒ・こんらんでない | `POKEMON_ASLEEP`・`POKEMON_PARALYZED`・`POKEMON_CONFUSED` | `EnergyTransfer.check_usable` |
| 9 | 選ばせるもの（`energy`・`source`・`target`）がそろっている | `POWER_CHOICE_MISSING` | 同上 |
| 10 | 移動元・移動先が場にいて、自分の場のポケモン | `SOURCE_NOT_IN_PLAY`・`SOURCE_NOT_YOURS`・`TARGET_NOT_IN_PLAY`・`TARGET_NOT_YOURS` | 同上 |
| 11 | 移動先が移動元と別のポケモン | `SAME_POKEMON` | 同上 |
| 12 | エネルギーが移動元についている | `ENERGY_NOT_ATTACHED` | 同上 |
| 13 | 「草」の基本エネルギーカード | `WRONG_ENERGY_TYPE` | 同上 |

ワザ・にげるの制限（`engine._require_not_asleep_or_paralyzed`・こんらんのコイン）は流用していない（8 はカードの説明による別の確認）。こんらんでもコインは投げない（説明が「使えない」と書く）。

## 3. 1 回の使用で 1 枚（実装上の仮定）

説明は、1 回の使用で何枚つけかえるかを書いていない（印刷の文面は「好きなだけ移動させることができる」、最新の説明は「何度でも使える。…つけかえる」）。エンジンは 1 回の使用（1 つのコマンド）で 1 枚をつけかえる。

- 何度でも使えるので、何枚まとめて移しても、1 枚ずつ移した結果（どのエネルギーがどのポケモンについているか）と同じ。ほかの処理がはさまらない（p.311: 宣言したらすべてすませてから）ので、1 枚ずつ移すあいだに起こることはない。
- 乱数を使わないので、移す回数・順番で結果は変わらない。
- 「1 回 1 枚」を原典の規定として扱っていない（docs と `UsePokemonPower` の説明に、実装上の仮定と書いた）。

## 4. 状態の変化

- 移動元の `PokemonInPlay.energy` から、選んだ uid を取りのぞき、移動先の `energy` の最後に加える。カードは同じ uid のまま（複製しない・なくさない・トラッシュしない・持ち主は変わらない）。カードの保存則（`check_invariants`）はそのまま成り立つ。
- `energy_attachments_this_turn`（手札からつけた回数）は変えない（SUPPORTED。[venusaur-v0.5.md](venusaur-v0.5.md) V10）。つけかえのあとも手札から 1 枚つけられ、手札からつけたあとも何度でもつけかえられる。
- 乱数は使わない（コインがない）。
- 番は終わらない（`Phase.MAIN` のまま。`_finish_attack` を呼ばない）。使った回数を状態に持たない（数えない）。
- 段階・決定・書き出しの形式を加えていない。状態の項目も加えていない（形式 1〜8 のまま。フシギバナは 2 進化なので、場にいれば形式 7 以上で書き出す。v0.4c と同じ）。

## 5. ログ

```text
pokemon_power  player, pokemon（使うポケモンのいちばん上のカードの uid）, pokemon_id, power（名前）, power_index, turn
move_energy    player, pokemon, pokemon_id（使ったポケモン）, power（PowerKey の文字列 "PMCG1-011@power0"）,
               energy（uid）, from_pokemon_id, to_pokemon_id, turn
```

- `pokemon_power` は p.311 の手順 1（宣言）、`move_energy` は手順 3（処理）。1 回の使用で、`pokemon_power` のすぐあとに `move_energy` が 1 つ。
- 手札からつけたログ `attach_energy` とは別のイベント（混同しない）。
- ログは記録で、状態の正本ではない。tests/log_audit.py の組み立て直し（場のポケモンのエネルギー）に `move_energy` を加え、次も確かめる: 直前に同じ番・同じプレイヤー・同じポケモンの宣言があること、宣言したポケモンが番のプレイヤーの場のポケモンであること、移動元・移動先・エネルギーが同じプレイヤーのものであること、移動元にそのエネルギーがついていること、ワザのあと（番の終わりまで）に特殊能力の使用がないこと。監査が壊れたログ・状態を見つけることを tests/test_bulbasaur_games_v0_5.py `LogAuditMoveEnergyTest` で確かめた（移動のログを消す・移動先を変える・相手のポケモンにする・uid を変える・2 回にする・宣言を消す・状態だけ動かす・ログだけ残す）。

## 6. ほかの処理との関係

| 処理 | 関係 | テスト |
|---|---|---|
| ワザ（p.320） | 必要なエネルギーは、ワザを使うときについているエネルギーで決まる。つけかえで払えるようになり、払えなくなる | `CostRecomputationTest.test_attack_cost`・変異 11 |
| にげる（p.311） | にげるエネルギーは、そのときバトル場のポケモンについているエネルギーから選ぶ。つけかえたエネルギーで払え、移したエネルギーは選べない | `test_retreat_cost`・変異 12 |
| 手札からエネルギーをつける（p.310） | 別の処理（回数を使わない） | `test_attaching_from_hand_is_a_separate_action` |
| 進化（p.310） | つけかえたエネルギーは進化してもついたまま。進化したその番に、フシギバナの特殊能力を使える。進化前のカードの特殊能力は使えない | `EvolutionInterplayTest`・`test_pre_evolution_power_cannot_be_used` |
| にげる・ポケモンいれかえ | 入れ替わってもエネルギーはついたまま。ベンチに移ったフシギバナも使える | `test_switch_and_retreat_keep_the_energy` |
| 強制交代（v0.4d のふきとばし） | エネルギーは変わらない。ベンチに移ったフシギバナは次の自分の番に使える | `test_forced_switch_keeps_the_energy` |
| きぜつ（p.313・p.323） | つけかえたエネルギーは、ついているポケモンといっしょにトラッシュ | `test_moved_energy_is_discarded_with_the_knocked_out_pokemon`・自然な対戦 13 回・変異 13 |
| 特殊状態 | 使うフシギバナのねむり・マヒ・こんらんだけが制限。移動元・移動先の特殊状態は関係しない。どくだけなら使える | `SpecialConditionTest` |
| 持続する効果・ついているトレーナー | 関係しない（エネルギーだけを動かす） | — |
