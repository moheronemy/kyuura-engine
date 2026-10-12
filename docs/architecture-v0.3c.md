# v0.3c のアーキテクチャ（こんらん: ワザ・にげるのコインと失敗）

v0.3c は、v0.3b の特殊状態の基盤に「こんらん」を加え、こんらん状態のポケモンのワザ（コイン・自分への 20 ダメージ・自分のきぜつ）と「にげる」（コイン・エネルギー・同じ番の再宣言の制限）を実装した版です。対応カードはロコン（PMCG1-015）の「あやしいひかり」です。原典の照合と裁定は [confusion-v0.3c.md](confusion-v0.3c.md)（こんらん状態）、[confusion-attacks-v0.3c.md](confusion-attacks-v0.3c.md)（ワザ・ロコン）、[retreat-confusion-v0.3c.md](retreat-confusion-v0.3c.md)（にげる）にあります。v0.3b の設計（[architecture-v0.3b.md](architecture-v0.3b.md)）の上に作っています。

## 1. 目的と範囲

- こんらん状態を、ねむり・マヒと重複しない特殊状態として、場のポケモンの状態に持つ（p.322）。
- 「不正なコマンド」（宣言できない。拒否し、状態も乱数も変えない）と、「正しく宣言した行動がルールで失敗する」（コイン・エネルギー・番の終わりが状態に残る）を分ける。
- ワザ: 宣言のあと（p.309 の手順 5）にこんらんのコインを投げ、「うら」ならワザの内容の代わりに自分に 20（弱点・抵抗力の影響を受ける）。ワザは使ったことになり、番が終わる。
- にげる: エネルギーをトラッシュしてからコインを投げ、「うら」なら失敗（エネルギーは戻らない）。失敗したポケモンは、その番はもう宣言できない（ポケモンごと）。
- 原典で決められない場合（こんらんの 20 とプラスパワー・ディフェンダー、こんらんが消えたあとの再宣言）は、コイン・エネルギーの前に止める。
- こんらんを使わない対戦の結果・ログ・乱数・拒否を v0.3b と同じに保つ。

作らなかったもの: 進化、特殊状態を回復するトレーナー、ワザを失敗させる効果（p.309 の手順 4）、持続する効果、控えポケモンへのダメージ、新しい段階（`Phase`）・コマンド・決定の種類、ゲーム状態全体の読み込み。

## 2. v0.3b からの変更

| 項目 | v0.3b | v0.3c |
|---|---|---|
| 特殊状態 | `exclusive` は `Asleep`・`Paralyzed(turn)`・None | `Confused` を加えた（持つ情報はない。共有値 `CONFUSED`）。`SpecialConditions.confused` |
| 場のポケモン | — | `PokemonInPlay.retreat_failed_turn: int | None`（こんらんで「にげる」に失敗した番） |
| 付ける・消す | `put_to_sleep`・`paralyze` | `conditions.confuse`（二重にならない・ねむり／マヒを置きかえる・どくは残す）。`put_to_sleep`・`paralyze` はこんらんも置きかえる |
| ワザ | 確認 → `attack` → 効果 | 確認 → 決められない場合の確認（`AttackEffect.problem`・`_confusion_damage_problem`）→ `attack` → こんらんならコイン（`_confusion_check`）→「おもて」効果／「うら」`_confusion_damage` → `_finish_attack` |
| にげる | 確認 → トラッシュ → 入れ替え | 確認（失敗の記録を含む）→ トラッシュ → こんらんならコイン →「おもて」入れ替え／「うら」失敗の記録（番は続く） |
| 番の終わり | ついているトレーナーのトラッシュ → `turn_end` | その間に、場のすべてのポケモンの失敗の記録を消す |
| ダメージ | `calculate_attack_damage`（8 段階） | `calculate_confusion_damage`（20 → 弱点 → 抵抗力 → 0 で止める）を加えた |
| ワザの効果 | `AttackEffect.check`・`resolve`・`resume` | `AttackEffect.problem`（既定は None。`SelfDamageOnTails` は `self_damage_problem`）、`ConfuseOnHeads`（あやしいひかり） |
| エラーコード | — | `RETREAT_ALREADY_FAILED`（`IllegalActionError`）、`UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS`・`UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED`（`UnsupportedError`） |
| ログ | `coin_flip` の `source` は `attack`・`pokemon_check` | `source: "confusion"` を加えた。`confusion_check`・`confusion_damage`・`retreat_failed` を加えた |
| 効果の登録表 | id `kyuura-engine-0.3b`、ワザ 21 | id `kyuura-engine-0.3c`、ワザ 22（あやしいひかり）。トレーナーは同じ 5 枚 |
| 状態の書き出し | 形式 1〜5 | 形式 5 に `confusion: {}`。形式 6（場のポケモンごとの `retreat_failed_turn`）を加えた |
| 不変条件 | `exclusive` は `Asleep`・`Paralyzed` | `Confused` も許す。失敗の記録（今の番・番のプレイヤー・番の終わりの前） |
| ルールの参照 | — | `rules.RULE_REFERENCES` に `confusion`・`confusion_attack`・`confusion_retreat` |
| カードデータの写し | `pool_v0_3b` | `pool_v0_3c`（PMCG1-015）。作り直して `--check` で一致 |
| 版 | `0.3.0b0` | `0.3.0c0` |

## 3. 特殊状態のデータ構造

```python
@dataclass(frozen=True)
class Confused:               # こんらん（持つ情報はない）。name = "confusion"
    pass

@dataclass(frozen=True)
class SpecialConditions:
    poison: Poison | None = None
    exclusive: Asleep | Paralyzed | Confused | None = None   # ねむり・マヒ・こんらんのどれか 1 つ
    confused: bool                                          # 性質（v0.3c）

@dataclass
class PokemonInPlay:
    ...
    conditions: SpecialConditions = NO_SPECIAL_CONDITIONS
    retreat_failed_turn: int | None = None                  # v0.3c
```

| 判断 | 理由 |
|---|---|
| こんらんを `exclusive` に入れる | 「「ねむり」「マヒ」「こんらん」状態が重複することはありません」（p.322）。v0.3b で用意した項目。「特殊状態は 1 つだけ」の形にはしない（どくは別） |
| こんらんは情報を持たない | 自然に回復しない（p.322）。期限・回数・発生源は要らない |
| 失敗の記録を特殊状態に入れない | 失敗の規定は特殊状態ではない（ベンチに戻っても「今の自分の番」の間は残る。R15）。こんらんが消えても記録は残り、R14（未解決）を判定できる |

## 4. 状態の付与・上書き・解除

| 処理 | 関数 | ログ |
|---|---|---|
| こんらんにする | `confuse(state, owner, pokemon, effect=…)`: もうこんらんなら変えない（`already`）。ねむり・マヒなら消して（`replaced`）こんらん。どくは残す | `special_condition`（`condition: "confusion"`） |
| ねむり・マヒにする | v0.3b と同じ。こんらんなら消す（`replaced`） | v0.3b と同じ |
| ベンチに戻る | `clear_special_conditions`（にげるの「おもて」・ポケモンいれかえ） | `special_conditions_removed`（`retreat`・`switch`） |
| ポケモンチェック | こんらんは何もしない（p.323） | — |
| きぜつ | 場のポケモンといっしょになくなる | `knock_out` |

## 5. ワザの手順とこんらん

```
UseAttack: 番 → ワザの位置 → ねむり・マヒ → 登録 → エネルギー
         → 決められない場合（effect.problem、こんらんなら _confusion_damage_problem）→ UnsupportedError（コインの前）
         → attack（宣言）
         → こんらんなら coin_flip(source="confusion") → confusion_check
              「うら」: _confusion_damage（confusion_damage）→ _finish_attack
              「おもて」: effect.resolve（ワザの説明。コイン source="attack"）→ _finish_attack
```

| 案 | 内容 | 判断 |
|---|---|---|
| A. こんらんの「うら」を `IllegalActionError` にする | 拒否して状態を戻す | 採らない。宣言は正しく、コイン・20 ダメージ・番の終わりはルールの結果（指示の「正しく宣言した行動が失敗する」） |
| B. こんらんを効果の実装（`AttackEffect`）の中で処理する | 各効果がこんらんを見る | 採らない。p.309 の手順 5 はワザの説明（手順 6）とは別の段階で、すべてのワザに共通。エンジンの `_use_attack` に置き、効果の実装は変えない |
| C. 決められない場合を、効果の `resolve` の中だけで確かめる | v0.3b まで | 足りない。こんらんのコインのあとで止まると「投げてから決める」形になる。`AttackEffect.problem`（ワザを使う前に分かることだけで決める）を加え、コインの前に聞く。状態によって決まる確認（`ParalyzeOnHeads` の再付与）は `resolve` に残る（`apply_command` が複製で処理するので、止まっても渡した状態・乱数は変わらない） |
| D. 新しい段階・決定を加える | こんらんの判定を待つ | 採らない。プレイヤーの選択がない（コインは乱数）。1 つのコマンドの中で終わる |

乱数の順番: こんらんのコイン → ワザの説明のコイン（「おもて」のとき）→ ポケモンチェックのねむりのコイン。「うら」なら、こんらんのコイン 1 枚だけ。

## 6. にげるの手順と失敗の記録

```
Retreat: 番 → 控えがいない → ねむり・マヒ
       → 失敗の記録が今の番（こんらんのまま → RETREAT_ALREADY_FAILED ／ こんらんが消えた → UNRESOLVED_…）
       → 入れ替える控え → エネルギー（数・重複・ついているか）
       → トラッシュ
       → こんらんなら coin_flip(source="confusion", effect="retreat") → confusion_check
            「うら」: retreat_failed_turn = 今の番、retreat_failed（番は続く）
            「おもて」: 入れ替え（retreat）→ clear_special_conditions(RETREAT)
_end_turn: ついているトレーナーのトラッシュ → 場のすべてのポケモンの retreat_failed_turn = None → turn_end → ポケモンチェック
```

| 案 | 内容 | 判断 |
|---|---|---|
| A. プレイヤー単位のフラグ（「この番はもうにげられない」） | `PlayerState` に 1 つ | 採らない（指示で禁止。p.311 の主語はポケモン。ほかのポケモンは宣言できる） |
| B. `GameState` に失敗したポケモンの番号の一覧 | 番ごとの集合 | 採らない。保留中のリストを別に増やさない（CLAUDE.md）。ポケモンが場を離れたときに一覧から消す処理が要る |
| C. 場のポケモンに失敗した番を持たせる | `PokemonInPlay.retreat_failed_turn` | **採った**。ポケモンといっしょに動き、きぜつで消える。番の番号と比べるので、記録の意味（どの番の失敗か）が明確。番の終わりに消す |
| D. こんらん状態（`Confused`）に記録を持たせる | `Confused(failed_turn)` | 採らない。こんらんが消えても記録が要る（R14 の判定）。こんらんの値を共有できなくなる |

## 7. コイントス

| `coin_flip` の `source` | `effect` | 投げるプレイヤー | 続くログ |
|---|---|---|---|
| `attack`（v0.2d） | ワザの `AttackKey` | ワザを使う側 | ワザの効果（`damage`・`special_condition` など） |
| `pokemon_check`（v0.3b） | `sleep` | ねむりのポケモンの持ち主 | `sleep_check` |
| `confusion`（v0.3c） | ワザの `AttackKey`、または `retreat` | こんらん状態のポケモンの持ち主（ワザを使う・にげるを宣言した側） | `confusion_check`（`action`: `attack`／`retreat`、`result`、`succeeded`） |

すべて `coins.flip_coins` だけで投げます（1 枚 1 回 `getrandbits(1)`）。コインの結果をコマンドで指定する口は作っていません（テストは `with_coin_results`）。こんらんのない対戦では `source: "confusion"` のコインはなく、乱数の使い方は v0.3b と同じです（13 章の比較）。

## 8. ダメージ計算

こんらんの 20 は `calculate_confusion_damage` で計算し、`deal_attack_damage`（ワザによるダメージ）を通しません。

- 弱点・抵抗力（p.322）は、自分のタイプと自分の弱点・抵抗力で見る（p.321 の 3・4 の定義）。0 以下は 0。
- こんらんのダメージが「ワザによるダメージ」かが決められない（[confusion-attacks-v0.3c.md](confusion-attacks-v0.3c.md) A11）ので、プラスパワー・ディフェンダーの段階を持たない。ついていればコインの前に止めるので、この計算には来ない。
- v0.2f の自分へのダメージ（ワザの説明の (3)）の規定とは混ぜない（[confusion-attacks-v0.3c.md](confusion-attacks-v0.3c.md) 5 章）。
- ログは `confusion_damage`（`damage` と分ける）。v0.1 からの `damage` のログの形・意味（ワザによるダメージ）は変えない。

## 9. きぜつ処理

こんらんの 20 のあとは、ワザのあとと同じ `_finish_attack` です（ワザの要素をすべて処理したあとで、場のポケモンをまとめて判定する。CLAUDE.md）。こんらんでは自分のポケモンだけがダメージを受けるので、同時のきぜつは起こりません。サイドは相手側が取り（p.323）、持ち主が新しい対戦ポケモンを出し、出せなければ負け（p.311 の表）。番は、交代のあと（決定の `then` なし）で終わります（v0.2f の自分のきぜつと同じ流れ）。

## 10. PendingDecision

新しい決定の種類・再開先・`context` の項目はありません。こんらんのコイン・失敗はプレイヤーの選択ではありません。こんらんの「うら」で自分がきぜつしたあとの `TAKE_PRIZE`（相手）・`PROMOTE_ACTIVE`（自分）は、v0.2f と同じ決定です。

## 11. シリアライズ

| 形式 | こんらん | 失敗の記録 |
|---|---|---|
| 1〜4 | 表せない（特殊状態のポケモンがいれば `ValueError`） | 表せない（`ValueError`） |
| 5 | `special_conditions` に `"confusion": {}`（v0.3b の `sleep`・`paralysis` と同じく、形式の番号は変えずに項目を加えた） | 表せない（記録のあるポケモンがいれば `ValueError`） |
| 6 | 5 と同じ | 場のポケモンごとの `retreat_failed_turn`（None か番の番号） |

- 形式 5 の項目を加えた理由は v0.3b と同じです（既存の項目の意味は変わらず、こんらんのない状態の書き出しは同じ。13 章の比較で確かめた）。知らない項目のある形式 5 は、読む側が拒否してください。書き出せない特殊状態の値があれば `ValueError` にします（黙って落とさない）。
- 形式 6 は、失敗の記録という新しい項目を場のポケモンすべてに加えるので、番号を上げました。記録のない状態では、形式 5 に `retreat_failed_turn: None` を加えたものと同じです（テストで確かめた）。
- 記録は番の終わりに消えるので、ポケモンチェックの途中の決定・次の番の状態は形式 5 でも書き出せます。
- `clone`・`copy.deepcopy`・`pickle`・乱数の JSON 保存と復元で、こんらんと記録が保たれることをテストで確かめました。**ゲーム状態全体を辞書・JSON から読み込む機能は、引き続きありません**（v0.2a から。乱数だけは保存・復元できる）。

## 12. 不変条件

| 不変条件 | 内容 |
|---|---|
| 特殊状態の型 | `exclusive` は `Asleep`・`Paralyzed`・`Confused`・None のどれか（文字列や知らない型は違反） |
| ベンチに特殊状態がない | v0.3a と同じ（こんらんも含む） |
| 失敗の記録 | None か整数。今の番の番号と同じ。持ち主が番のプレイヤー。対戦準備の段階にはない。今の番の `turn_end` のあとにはない |
| 番の進行・決定の続き・マヒの期限 | v0.3b と同じ |

## 13. 互換性と検査

- **v0.3b（`0516c05`）との比較**: v0.3b のコードを `git archive` で取り出し、同じ入力で次の 1,140 局（104,295 コマンド）と、でたらめな操作を混ぜた 16 局を動かした。終わった状態（形式 5。登録表の id を除く）・ログ・乱数の状態・結果・止めた理由がすべて同じだった。
  1. 特殊状態を使わない既存のデッキ 7 組 × 40 seed（280 局）
  2. ビードル（どく）のデッキ × 40 seed
  3. キャタピーだけ・パラスだけのデッキ × 30 seed ずつ
  4. v0.3b の混ぜたデッキ（どく・ねむり・マヒ）: 直す手順 60 局、直さない手順 300 局（`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT` で止まる局を含む）
  5. どくを直さないビードルのミラー × 400 seed（止まる局を含む）
  6. 2・4 の 20 局ずつは、途中のすべての状態（ポケモンチェックの中の決定を含む）も同じ。ねむり・マヒで拒否された操作（コードと位置）も同じ
  7. でたらめな操作を混ぜた 16 局（v0.3b の `RandomCommandsWithStatusDecksTest` と同じ入力。4,142 コマンドのうち 2,485 回の拒否を含む）: 拒否のコードの列と終わった状態が同じ
  - 止まった局は 9 局（ビードルのミラー 5 局・混ぜたデッキの直さない手順 4 局。すべて `UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`）で、v0.3b と同じ局・同じ状態。サドン・デスは 1 局（ピカチュウのデッキ）で同じ
- v0.3b のテスト 613 件を v0.3c のコードで実行すると、失敗するのは下の 6 件だけ（どれも登録表の id・登録の一覧・形式の一覧を確かめるもの）。1 件の skip は、比較用のディレクトリの位置で `../kyuura` がないため（リポジトリの直下では実行される）。v0.1 の参照データ・乱数とコインの固定値（test_reproducibility.py・test_coins.py・test_coin_games.py・test_pikachu_games.py・test_weedle_games.py・test_sleep_paralysis_games.py の `GOLDEN_DIGEST`・`EXPECTED_COUNTS`）は変えていない。
- コマンド・段階・決定の種類は増やしていない。こんらんのない対戦では、新しいエラーコード・ログ・コインは出ない。

### 変更した既存のテスト

| テスト | 変更 | 保証が弱くなっていない理由 |
|---|---|---|
| test_effects.py `test_attacks_with_text_follow_the_verified_latest_description` | 説明文のあるワザの一覧に、あやしいひかり（`PMCG1-015#0`） | 一覧をちょうど確かめる性質は同じ。加えたワザも照合の記録と比べる |
| test_effects.py `RegistryImmutabilityTest.test_with_and_without_do_not_change_the_original` | 登録したワザの数 21 → 22 | 登録表が変わらないことを確かめる性質は同じ |
| test_trainers.py `test_default_registry_has_exactly_the_registered_cards` | 登録表の id `kyuura-engine-0.3c` | トレーナーの一覧と実装の一覧は同じまま |
| test_rng_and_serialize.py `test_format_2_adds_only_documented_fields` | 登録表の id | 同上 |
| test_rng_and_serialize.py `test_unknown_format_is_rejected` | 形式の一覧に 6、知らない形式の例を 6 → 7 | 知らない形式（0・7・文字列・None）を拒否する性質は同じ |
| test_cards.py `test_v0_1_pool_is_ten_basic_pokemon_and_six_basic_energy` | `pool_v0_3c` とロコンが使えることを確かめ、v0.1 の組の数からロコンを除く | v0.1 の組（たねポケモン 10・基本エネルギー 6）の確認は同じ |

tests/helpers.py に `VULPIX` と、`build_test_state` のバトル場の指定に `"confusion"`・`"retreat_failed_turn"` を加えました（既存の盤面は変わらない）。

### 負荷テスト・変異テスト

- 負荷テスト（作業用）: 自然な対戦 400 局と、でたらめな操作を混ぜた 200 局。結果は [confusion-v0.3c.md](confusion-v0.3c.md) 8 章。
- 変異テスト（作業用。実装を 1 か所ずつ壊し、test_confusion*.py が失敗するかを見る）: 30 種類すべてを検出した。こんらんのコインを投げない・「うら」で成功・相手が投げる・「うら」でもワザの内容を処理する・「うら」で番が終わらない・20 を 10 にする・20 を相手に与える・弱点／抵抗力を計算しない・0 で止めない・プラスパワー／ディフェンダーの未解決を通す・ワザの未解決をコインの前に確かめない・宣言のログがない・にげるのコインを投げない・エネルギーをトラッシュしない・失敗したらエネルギーを戻す・失敗を記録しない・再宣言を拒否しない・番の終わりに記録を消さない・こんらんが消えたあとも拒否する（未解決を決めてしまう）・ねむり／マヒならこんらんにならない・こんらんにするとどくが消える・「うら」でこんらんにする・きぜつした相手にもコインを投げる・形式 5 でこんらんを落とす・古い形式で記録を落とす・複製で記録を落とす・記録の不変条件を確かめない・知らない型の特殊状態を通す。

## 14. 将来の拡張

| 事項 | v0.3c の土台 | 加えるときに見直すこと |
|---|---|---|
| 進化 | `clear_special_conditions`、`pokemon_id` は進化しても同じ | 進化で特殊状態が消える（p.322）。失敗の記録（`retreat_failed_turn`）は進化で残すか（進化しても同じポケモンか）を原典で照合する |
| 特殊状態を回復するトレーナー | `_remove_exclusive`・`clear_special_conditions` | 消す理由（`reason`）を加える。こんらんを直したあとの「にげる」の再宣言は R14 と同じ問題になる |
| ワザを失敗させる効果（p.309 の手順 4） | `_use_attack` の手順 5 の前 | 手順 4 と 5 の順番。こんらんのコインより前に失敗するなら、こんらんのコインを投げない |
| ワザの説明にコストがあるワザ | `AttackEffect.problem` | こんらんの「うら」でコストを払うか（[confusion-attacks-v0.3c.md](confusion-attacks-v0.3c.md) A14） |
| 「ワザによるダメージを受けない」効果 | `_confusion_damage_problem` | こんらんの 20 がワザによるダメージかに関わる（A11 と同じ未解決） |
| 番を飛ばす・続ける効果 | 記録は番の番号で比べる | 「今の自分の番」「次の自分の番」の表し方 |
| プレイヤーごとの見え方 | ログの `confusion_check`・`retreat_failed` は公開情報 | 隠す情報はない（コインの結果は両方のプレイヤーに見える。p.319） |

## 15. 設計上のトレードオフ

| 判断 | 理由 | 代償 |
|---|---|---|
| ダメージを変えるカードがついたこんらんのポケモンのワザは、コインの前に止める | こんらんの 20 とプラスパワー・ディフェンダーの関係が決められない。「おもて」なら問題がない場合も、投げる前には分からない | プラスパワー・ディフェンダーをつけたこんらんのポケモンはワザを使えない（自然な対戦の 36 局で 2 回）。プレイヤーはつける前に判断する必要がある |
| こんらんが消えたあとの再宣言は止める | p.311 の主語の読み方が 2 つある | 失敗 → ポケモンいれかえ → 戻す、の手順の番で、そのポケモンは「にげる」を使えない（次の番には使える） |
| こんらんの 20 を別の計算にする | 「ワザによるダメージ」か決められない。v0.2f の自分へのダメージと混ぜない | ダメージ計算が 2 つになる（共通の部分は弱点・抵抗力の定義だけ） |
| `AttackEffect.problem` は、ワザを使う前に分かることだけ | こんらんのコインの前に確かめられる形にする | 状態によって決まる確認（ダメージのあとで分かるもの）は `resolve` に残る。止まっても `apply_command` の原子性で状態は戻るが、「コインの前に止める」約束は形の上では守られない場合がある（v0.3c の対応カードでは起こらない） |
| 入れ替える控えをコマンドで先に指定する | v0.1 からのコマンドの形を変えない | 「うら」のとき、指定した控えは使われない（結果は同じ） |
| 形式 5 にこんらんを加え、記録だけ形式 6 にした | 既存の項目の意味を変えない加え方は v0.3b と同じ。記録は新しい種類の項目 | 形式 5 を読むクライアントは、知らない項目を拒否する必要がある |
