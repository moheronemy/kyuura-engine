# コインの前の検証（v0.3d）

正しく宣言した行動が「原典で決められない場合」に当たるかどうかを、コインを投げる前に確かめ終えているかを調べた記録です。v0.3c で `AttackEffect.problem`（ワザを使う前に分かる、決められない場合）を加えましたが、効果の実装の `resolve`（コインのあと）にも確認が残っていました（[architecture-v0.3c.md](architecture-v0.3c.md) 15 章のトレードオフ）。v0.3d で、対応カードのすべてのワザの実装について、コインのあとで「決められない」と分かる場合が残っていないことを確かめました。

関連: [special-conditions-audit-v0.3d.md](special-conditions-audit-v0.3d.md)（特殊状態の総合検証）、[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md)（未解決の裁定）、[architecture-v0.3d.md](architecture-v0.3d.md)（設計）。

## 1. なぜコインの前か

コインを投げてから「決められない」と分かって止める形には、次の問題があります。

1. **乱数の結果が漏れる**: `apply_command` は複製で処理するので、止まれば状態も乱数も戻ります。しかし「拒否されたかどうか」でコインの結果が分かってしまいます。たとえば「おもてなら決められない」なら、受け付けられたときは「うら」だったと分かり、プレイヤーは拒否されるかどうかを見てから行動を選べます（乱数の先読み）。
2. **合法な操作の扱いがコインで変わる**: 同じ盤面・同じコマンドが、乱数の状態によって受け付けられたり止められたりします。原典で決められないのは盤面の性質で、コインの結果ではありません。

そのため CLAUDE.md の約束は「コインを投げる効果は、投げる前に使えるかどうか・原典で決められない場合を確かめ終えておきます」です。v0.3d では、これを「**受け付けるか・どのコードで拒否するかが、コインの結果で変わらない**」という性質として、テストで確かめられる形にしました（3 章）。

`apply_command` の原子性（例外なら渡した状態も乱数も変わらない）は安全網で、コインの前の確認の代わりではありません。

## 2. エンジンが確かめる順番

### ワザ（`_use_attack`。p.309 の手順 1〜6）

```
UseAttack: 番 → ワザの位置 → ねむり・マヒ（手順 1）→ 登録（UNSUPPORTED_ATTACK）→ エネルギー（手順 2）
         → effect.problem(state, use)                    … ワザの説明の処理が決められない
         → こんらんなら _confusion_damage_problem         … こんらんの 20 とプラスパワー・ディフェンダー
         → ここまでで拒否なら、乱数もログも使っていない
         → attack（宣言。手順 3）
         → こんらんなら coin_flip(source="confusion")（手順 5）
              「うら」: _confusion_damage → _finish_attack（resolve は呼ばない）
              「おもて」: effect.resolve（手順 6。ワザの説明のコイン source="attack"）→ _finish_attack
```

### にげる（`_retreat`。p.311）

```
Retreat: 番 → 控えがいない → ねむり・マヒ
       → 失敗の記録が今の番: こんらんのまま RETREAT_ALREADY_FAILED ／ こんらんが消えた UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED
       → 入れ替える控え → エネルギー（重複・ついているか・数）
       → ここまでで拒否なら、乱数もログも使っていない
       → トラッシュ → こんらんならコイン → 入れ替え／失敗の記録
```

### ポケモンチェック（`_pokemon_check`。p.323）

```
2 どく: 両方の対戦ポケモンがどくで HP 以上になるなら、ダメージの前に HALTED（UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT）
       → ダメージ → きぜつ・サイド・交代
3 ねむり: 両方の対戦ポケモンがねむりなら、コインの前に HALTED（UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER）
       → 持ち主がコイン
4 マヒ: コインはない
```

### トレーナー

v0.3d の対応トレーナー（マサキ・きずぐすり・ポケモンいれかえ・プラスパワー・ディフェンダー）は、どれもコインを投げません。使えるかどうかの未解決は `TrainerEffect.check_playable`（`UNRESOLVED_POTION_WITHOUT_DAMAGE`・`UNRESOLVED_SWITCH_WITHOUT_BENCH`）、選択の未解決は決定の `unresolved_choices`（きずぐすりのダメージのないポケモン）で、どちらも乱数を使う前です（v0.2b）。

## 3. ワザの実装ごとの確認

v0.3d の効果の登録表（`kyuura-engine-0.3c`。ワザ 22）のワザの実装は 7 種類です。

| 実装 | 登録しているワザ | コイン | `resolve` の中で決められない場合 | `problem` |
|---|---|---|---|---|
| `DamageOnly` | 説明文のないワザ 16 | なし | なし | 既定（None） |
| `CoinFlipDamage` | ドードー「みだれづき」 | 2 枚 | なし | 既定 |
| `SelfDamageOnTails` | ピカチュウ「でんげき」 | 1 枚 | v0.3c までは、自分のタイプが自分の弱点・抵抗力のタイプなら止めた（`self_damage_problem`）。v0.3d で原典の根拠が見つかり（p.90 の解説。SUPPORTED）、止める必要がなくなった | 既定（v0.3c は `self_damage_problem`） |
| `PoisonOnHeads` | ビードル「どくばり」 | 1 枚 | なし（再びどくは `already`。特殊などくは未実装） | 既定 |
| `ParalyzeOnHeads` | キャタピー「いとをはく」 | 1 枚 | `paralysis_problem`（マヒの再付与で回復する番が変わる場合）。**相手の対戦ポケモンには起こらないことを証明した**（4 章） | 既定 |
| `PutToSleep` | パラス「キノコのほうし」 | なし | なし（再びねむりは `already`、マヒ・こんらんは置きかえ） | 既定 |
| `ConfuseOnHeads` | ロコン「あやしいひかり」 | 1 枚 | なし（再びこんらんは `already`、ねむり・マヒは置きかえ） | 既定 |

どの実装も、相手の対戦ポケモンがワザのダメージできぜつしたら、そのあとの特殊状態のコインを投げません（v0.3a〜v0.3c）。これは原典で決まった処理（p.309・p.323）で、決められない場合ではありません。

結論: v0.3d の対応カードのワザでは、コインを投げたあとで「決められない」と分かる場合はありません。どの実装も `problem` は既定（None）でよく、エンジンの `_confusion_damage_problem` だけがワザを使う前の確認です。

## 4. マヒの再付与の証明

`ParalyzeOnHeads` は、相手の対戦ポケモンだけをマヒにします。番 T（番のプレイヤー p）にワザを使うとき、相手（q）の対戦ポケモンがマヒ状態で残っているとします。マヒ状態になった番を t とすると:

1. マヒは、t より後の、持ち主（q）の最初の番の終わりに回復する（p.322・p.323。`paralysis_recovery_turn`）。番は先攻から 1 つずつ交互に進む（不変条件）。
2. 回復する番を過ぎたマヒは残らない（不変条件。v0.3b）。番 T に残っているので、回復する番 r(t) ≥ T。
3. q の番は T − 1・T + 1・…。t ≤ T − 2 なら、t より後の q の最初の番は T − 1 以下なので r(t) ≤ T − 1 < T となり、2 に反する。よって t = T − 1 か t = T。
4. t = T − 1（q の番）なら、それより後の q の最初の番は T + 1。t = T（p の番）でも、それより後の q の最初の番は T + 1。
5. 再付与の番は T なので、新しく数えた回復する番も r(T) = T + 1。どちらで数えても同じなので、`paralysis_problem` は None を返す。

したがって、このワザでは `UNRESOLVED_REPARALYSIS_RECOVERY_TURN` は起こらず、コインのあとで止まることもありません（tests/test_effect_preflight_v0_3d.py `ReparalysisProofTest.test_opponent_paralysis_never_needs_the_unresolved_ruling` が、番 2〜11 とマヒ状態になった番のすべての組で確かめる）。回復する番が変わるのは、自分の番に自分のポケモンを再びマヒにする効果だけです（`test_own_pokemon_can_need_it`。対応カードにない）。

`conditions.paralyze` の中の `paralysis_problem` の確認は残しています（将来、自分のポケモンをマヒにする効果を加えたときの安全網）。そのような効果を加えるときは、`AttackEffect.problem` で確かめてください。

## 5. コインに依存しないことのテスト

tests/test_effect_preflight_v0_3d.py `CoinIndependenceTest`:

- 7 種類の実装（それぞれ 1 つのワザ）× ワザを使うポケモンの状態 4 つ（なし・どく・こんらん・どく + こんらん）× 相手の状態 7 つ（なし・どく・ねむり・前の番のマヒ・今の番のマヒ・こんらん・どく + こんらん）× 相手がワザできぜつする／しない × プラスパワーあり／なし = 784 の盤面。
- それぞれの盤面で、コインの結果 8 通り（こんらん 1 枚 + ワザの説明 2 枚まで）すべてについて `UseAttack` を送り、結果（受け付けた／拒否のコード）が 1 つだけであることを確かめる。
- 受け付けたときは返した状態が不変条件を満たす。拒否はこんらん + プラスパワーの `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` だけ。

`PreflightOrderTest` は、エンジンが `problem` を宣言（ログ `attack`）と乱数を使う前に聞くこと、こんらんの「うら」なら `resolve` を呼ばないこと、`problem` が止めたら `resolve` を呼ばないことを、テスト専用の効果で確かめます。tests/test_confusion_attacks.py `test_unresolved_attack_is_stopped_before_the_confusion_coin` も、テスト専用の効果（`problem` が止める）で、「おもて」「うら」のどちらでも同じコードで止まり、状態と乱数が変わらないことを確かめます。

## 6. コインのあとで止まった場合

コインのあとで例外が起きた場合（今の対応カードでは起こらない。内部の誤り・将来の効果の実装の誤り）も、`apply_command` は渡した状態と乱数を変えません。tests/test_self_damage.py `ErrorAfterCoinAtomicityTest` は、コインのあとで `UnsupportedError` を出すテスト専用の効果で、これを確かめます（v0.3c まではピカチュウの未解決の場合で確かめていたが、v0.3d でその裁定が決まったので置きかえた）。

## 7. 乱数を使う場所

| 場所 | `source` | 投げるプレイヤー | 投げる前に確かめ終えていること |
|---|---|---|---|
| ワザの説明（v0.2d〜） | `attack` | ワザを使う側 | 宣言の正しさ、`problem`、こんらんの変更効果、こんらんのコイン（「おもて」のときだけ投げる） |
| こんらん（v0.3c） | `confusion` | こんらんのポケモンの持ち主 | ワザ: 同上。にげる: 宣言の正しさ・失敗の記録・エネルギー |
| ポケモンチェックの 3（v0.3b） | `pokemon_check` | ねむりのポケモンの持ち主 | 2 のどくのきぜつの処理（両方のきぜつなら止める）・両方がねむりでないこと |

コインの結果を見てから順番や処理を選ぶ処理はありません（両方のねむりは、番のプレイヤーから投げる正規化をせずに止める。[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md) 4 章）。不正な操作・原典で決められない操作は乱数を使いません（[special-conditions-audit-v0.3d.md](special-conditions-audit-v0.3d.md) 7 章・10 章）。

## 8. 新しい効果を加えるとき

- コインを投げる前に分かる「決められない場合」は `AttackEffect.problem` で返す（ワザを使う前の状態だけで決める。コインの結果で変わる条件も、ここで先に確かめる）。
- 効果の対象や数がコインで変わる場合（「おもてなら控えにも」など）は、どの結果でも決められるかを `problem` で確かめる。
- 自分のポケモンを特殊状態にする効果は、マヒの再付与（4 章の証明が成り立たない）を `problem` で確かめる。
- 確認のための汎用の枠組み（ワザの効果の DSL・検証のフレームワーク）は作らない。実装ごとに `problem` を書き、`CoinIndependenceTest` の `ATTACKS` に加える。
