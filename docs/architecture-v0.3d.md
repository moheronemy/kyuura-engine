# v0.3d のアーキテクチャ（特殊状態の総合検証・未解決裁定の再調査・進化の前の整理）

v0.3d は、新しいカードやルールを加えず、v0.3a〜v0.3c の特殊状態 4 種類を総合的に確かめ、原典で決められないとして止めていた裁定を調べ直し、進化（v0.4）の前に基盤を整理した版です。

- 特殊状態の総合検証: [special-conditions-audit-v0.3d.md](special-conditions-audit-v0.3d.md)
- 未解決裁定の再調査: [unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md)
- コインの前の検証: [effect-preflight-v0.3d.md](effect-preflight-v0.3d.md)
- 進化の準備（調査だけ。実装していない）: [evolution-readiness-v0.4.md](evolution-readiness-v0.4.md)

v0.3c の設計（[architecture-v0.3c.md](architecture-v0.3c.md)）の上に作っています。

## 1. 目的と範囲

- どく・ねむり・マヒ・こんらんのすべての組み合わせ（8 つの状態）で、付与・上書き・解除・操作・ポケモンチェックが原典どおりかを確かめる。
- 付与・上書き・解除の処理と不変条件をそろえる。
- 原典で決められないとして止めていた 5 件を調べ直す。決められなければ止める処理を維持する。
- 原典で決められない場合を、コインの前に確かめ終えているかを確かめる。
- 進化の実装の前に、状態の持ち方・識別子・記録の扱いを調べる（実装しない）。
- 原典に基づく意図的な修正以外で、既存の対戦の結果を変えない（9 章の比較）。

作らなかったもの: 進化・退化（コマンド `EvolvePokemon` は v0.1 から `UNSUPPORTED_ACTION` のまま）、新しいカード・ワザ・トレーナー、新しい段階・コマンド・決定の種類・ログの種類・書き出しの形式、ワザの効果の DSL・汎用の検証の枠組み。

## 2. v0.3c からの変更

| 項目 | v0.3c | v0.3d |
|---|---|---|
| 自分へのワザのダメージの弱点・抵抗力（v0.2f の未解決） | 自分のタイプが自分の弱点・抵抗力のタイプなら `UNRESOLVED_SELF_DAMAGE_WEAKNESS_RESISTANCE` で止める（`effects.self_damage_problem`） | **原典の根拠が見つかり SUPPORTED**（p.90 の解説）。弱点・抵抗力を計算する。`self_damage_problem` を外し、このコードはもう出ない（4 章） |
| `SelfDamageOnTails.problem` | `self_damage_problem` を返す | 既定（None）。v0.3d の対応カードのワザの実装は、どれも既定 |
| 特殊状態を付ける処理 | `put_to_sleep`・`paralyze`・`confuse` がそれぞれ「同じなら already、違えば replaced」を書く | 共通の `conditions._set_exclusive`・`_log_applied` にまとめた（動きは同じ。3 章） |
| 失敗の記録の不変条件 | 番・持ち主・番の終わりの前 | 加えて、今の番のログの `retreat_failed`（同じ `pokemon_id`）と対応すること（5 章） |
| `engine._turn_has_ended` | 今の番の `turn_end` があるか | `_events_since_turn_start`（今の番のログ）に置きかえ、上の 2 つの確認に使う |
| テスト用の盤面（`tests/helpers.py` の `build_test_state`） | `retreat_failed_turn` を指定できる | 指定したポケモンに、対応する `retreat_failed` のログも置く |
| 版 | `0.3.0c0` | `0.3.0d0` |
| 効果の登録表 | id `kyuura-engine-0.3c`、ワザ 22・トレーナー 5 | 変えていない（8 章） |
| カードデータの写し・コマンド・段階・決定・ログの種類・書き出しの形式 | — | 変えていない |

## 3. 特殊状態の付与（共通化）

```python
def _set_exclusive(state, owner, pokemon, value) -> bool:     # True なら同じ状態（already）
    current = pokemon.conditions.exclusive
    if type(current) is type(value):
        return True
    if current is not None:
        _remove_exclusive(state, owner, pokemon, REPLACED)       # ログ special_conditions_removed（replaced）
    pokemon.conditions = replace(pokemon.conditions, exclusive=value)   # どくは残る
    return False
```

- `put_to_sleep`・`confuse` は `_set_exclusive` → `_log_applied`（ログ `special_condition`）。`paralyze` は先に `paralysis_problem`（回復する番が変わる場合は止める。状態もログも変えない）を確かめ、マヒ状態になった番・回復する番をログに加える。`poison` は `exclusive` を変えず、どくだけを付ける（同じなら `already`）。
- ログの項目の順番・値は v0.3c と同じです（v0.3c との比較で、ログを含む状態がすべて同じだった。9 章）。
- 変異テストで、上書きでどくが消える・ほかの状態があると上書きしない・消えたログを残さない、を検出することを確かめました（[special-conditions-audit-v0.3d.md](special-conditions-audit-v0.3d.md) 11 章）。

## 4. 自分へのワザのダメージの弱点・抵抗力

v0.2f は、ワザの説明による自分へのダメージ（p.320 のダメージの (3)）に弱点・抵抗力を計算するかを原典で決められないとして、ワザを使うポケモンのタイプが自分の弱点・抵抗力のタイプなら止めていました。v0.3d で、p.90（わるいカメックスの「ハイドロキャノン」の解説）に「このワザによって、自分自身が受けるダメージは、「プラスパワー」、弱点・抵抗力などの影響を受けることです」とあるのを見つけました（[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md) 6 章）。カード 1 枚の解説から、ワザの説明による自分へのダメージ一般に広げるので、分類は SUPPORTED です（CONFIRMED にはしない）。

- `deal_attack_damage(state, use, SELF, base)` は、p.321 の 8 段階で計算し、弱点・抵抗力（3・4 段階）はワザを使うポケモンのタイプと、受けるポケモン（自分）の弱点・抵抗力で見ます。プラスパワー（5 段階）・ディフェンダー（7 段階）の扱いは v0.2f と同じです（p.257）。
- こんらんの 20（`calculate_confusion_damage`）とは混ぜていません。こんらんの 20 は「ワザによるダメージ」かが決められないので、別の計算のままです（[confusion-attacks-v0.3c.md](confusion-attacks-v0.3c.md) 5 章）。
- 対戦に使えるカード（ピカチュウ。雷・弱点 闘）では、もともと弱点・抵抗力が関係しないので、対戦の結果は変わりません。変わるのは、テストで作った「自分の弱点のタイプのポケモン」だけです。

## 5. 失敗の記録の不変条件

v0.3c の不変条件は、失敗の記録（`PokemonInPlay.retreat_failed_turn`）が「今の番・番のプレイヤーのポケモン・番の終わりの前」にあることだけを見ていました。これでは、記録を失敗していないポケモンに付ける不具合（進化や特殊状態を消す処理が、記録を書きかえる・付けかえる場合など）を見つけられません。v0.3d で、記録が「今の番のログの `retreat_failed`（同じ `pokemon_id`）」と対応することを加えました。

| 案 | 内容 | 判断 |
|---|---|---|
| A. 記録をやめて、ログから毎回求める | `retreat_failed_turn` を消し、今の番のログを探す | 採らない。v0.3c の設計（記録はポケモンといっしょに動く。[architecture-v0.3c.md](architecture-v0.3c.md) 6 章）と形式 6 の書き出しを変えることになる |
| B. 記録とログの対応を不変条件で確かめる | `_retreat_failure_problems` | **採った**。動きは変わらず、不具合を `StateIntegrityError` で見つけられる |

ログは内部の完全な記録で、`apply_command` の結果はいつもログを持つので、正しい対戦ではこの条件は必ず成り立ちます（v0.3c との比較・総合テスト・負荷テストで確かめた）。テスト用の盤面（`build_test_state`）は、記録を指定したポケモンに対応するログを置きます。

## 6. コインの前の検証

[effect-preflight-v0.3d.md](effect-preflight-v0.3d.md) にまとめました。v0.3d の対応カードのワザの実装（7 種類）では、コインのあとで「決められない」と分かる場合はありません。`ParalyzeOnHeads` の再付与の確認は相手の対戦ポケモンには働かないことを証明し、受け付けるか・拒否のコードがコインの結果で変わらないことを 784 の盤面 × コインの 8 通りで確かめました。エンジンの順番（`problem` → こんらんの変更効果 → 宣言 → コイン）は変えていません。

## 7. 状態の書き出し

形式 1〜6 は変えていません。v0.3d で状態に加えた項目はないので、形式を上げていません。形式 1〜4 で特殊状態、形式 1〜5 で失敗の記録を書き出せない場合は、v0.3c と同じく `ValueError` です（黙って落とさない。変異テストで確かめた）。ゲーム状態全体を辞書・JSON から読み込む機能は、引き続きありません。

## 8. 効果の登録表の id

登録表の id（`kyuura-engine-0.3c`）は変えていません。

- 登録しているカード・ワザ・トレーナーと、それぞれの実装（`implementation_id`）は v0.3c と同じです。
- `SelfDamageOnTails` の処理は、自分のタイプが自分の弱点・抵抗力のタイプのときだけ変わりました（止める → 計算する）。登録しているピカチュウの「でんげき」は、この場合に当たらないので、登録したワザの結果は変わりません（9 章の比較）。
- id を変えると、状態の書き出し（形式 2 以上の `effects`）と、それを確かめるテストが変わります。登録の内容が同じなので、変える理由がないと判断しました。

テスト専用の登録表（`with_attacks`）で、自分の弱点のタイプのポケモンに「でんげき」を登録した場合は、v0.3c では止まり、v0.3d では計算されます。登録表の id でこの違いは区別できないので、v0.3c と v0.3d の結果を比べるときはエンジンの版（`__version__`）も見てください。

## 9. 互換性と検査

### v0.3c（`a4c66e2`）との比較

v0.3c のコードを `git archive` で取り出し、同じ入力で次を動かしました。終わった状態（形式 6。登録表の id を除く）・ログ・乱数の状態・結果・止めた理由が、**すべて同じ**でした。

1. 既存のデッキ（特殊状態のない 7 組 × 40 seed、ビードル 40、キャタピーだけ・パラスだけ 30 ずつ、v0.3b の混ぜたデッキ 60 + 300、ビードルのミラー 400、v0.3c のこんらんのデッキ 100 + 100）: 1,340 局・121,420 コマンド。ビードル・混ぜたデッキ・こんらんのデッキの seed 0〜19 は、途中のすべての状態（ポケモンチェックの中の決定を含む）も同じ。ねむり・マヒ・こんらんで拒否された操作（コードと位置）も同じ。
2. でたらめな操作を混ぜた 32 局（v0.3b・v0.3c のでたらめな操作のテストと同じ入力。8,162 コマンドのうち 4,437 回の拒否）: 拒否のコードの列と終わった状態が同じ。
3. v0.3d の 4 種類を混ぜたデッキ（[special-conditions-audit-v0.3d.md](special-conditions-audit-v0.3d.md) 9 章）の直す手順・直さない手順 150 局ずつ（300 局・44,122 コマンド）: 途中のすべての状態が同じ。

止まった局（`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`・サドン・デスなど）も、v0.3c と同じ局・同じ状態です。v0.1 の参照データ・乱数とコインの固定値（test_reproducibility.py・test_coins.py・test_coin_games.py・test_pikachu_games.py・test_weedle_games.py・test_sleep_paralysis_games.py・test_confusion_games.py の `GOLDEN_DIGEST`・`EXPECTED_COUNTS`）は変えていません。

### v0.3c のテストを v0.3d のコードで実行した結果

v0.3c のテスト 687 件のうち、681 件が通り、5 件（下の表。subTest で数えると 9）が失敗し、1 件が skip でした（skip は、比較用のディレクトリの位置で `../kyuura` がないため）。失敗は、意図した 2 つの変更（4 章の裁定、5 章の不変条件）によるものだけです。

### 変更した既存のテスト

| テスト | 変更 | 理由・保証が弱くなっていない理由 |
|---|---|---|
| test_self_damage.py `UnresolvedSelfWeaknessTest.test_stops_before_any_damage_or_coin` | `SelfWeaknessResistanceTest` に置きかえた（自分の弱点で ×2・抵抗力で −30 して 0・プラスパワーと弱点の段階の順番・「おもて」なら自分へのダメージはない） | 裁定が決まった（4 章）。止まることの確認を、計算の結果の確認にした |
| test_self_damage.py `UnresolvedSelfWeaknessTest.test_error_after_the_coin_keeps_the_original_state` | `ErrorAfterCoinAtomicityTest` に移し、コインのあとで止まるテスト専用の効果で確かめる | ピカチュウの未解決がなくなったので、例を作り直した。コインのあとの例外で状態・乱数が変わらない性質の確認は同じ |
| test_confusion_attacks.py `test_unresolved_attack_is_stopped_before_the_confusion_coin` | テスト専用の効果（`problem` が止める）で確かめる。自分の弱点のピカチュウは `test_self_typed_pikachu_resolves_after_heads`（「おもて」→ でんげき → 自分に 10 × 2、「うら」→ こんらんの 20 × 2）に移した | コインの前に止める性質の確認は同じ（「おもて」「うら」の両方） |
| test_confusion.py `test_clone_deepcopy_pickle_keep_confusion_and_retreat_record` | 記録を直接書く代わりに `record_failure`（記録と対応するログを置く） | 5 章の不変条件。複製で記録が保たれる確認は同じ |
| test_confusion.py `InvariantTest.test_retreat_failure_record` | 同上 | 正しい記録は通り、番・持ち主・型の違う記録は違反、の確認は同じ |

加えたテスト: test_confusion.py `test_retreat_failure_record_needs_the_failure_in_the_log`、test_self_damage.py の 4 件、test_confusion_attacks.py の 1 件、新しい 4 つのモジュール（10 章）。合わせて 687 → 726 件です。

## 10. テストの構成

| モジュール | 件数 | 内容 |
|---|---|---|
| tests/test_special_conditions_matrix_v0_3d.py | 14 | 8 つの状態 × 付与・上書き・解除・ワザ・にげる・ポケモンいれかえ・ほかの操作・決定を待つ間・ポケモンチェック |
| tests/test_effect_preflight_v0_3d.py | 5 | コインに依存しないこと（784 盤面 × 8 通り）・マヒの再付与の証明・エンジンが `problem` を聞く位置 |
| tests/test_unresolved_rulings_v0_3d.py | 9 | 5 つの未解決の境界（止まる・止まらない・状態と乱数が変わらない）とこんらんの変更効果の読み方の比較 |
| tests/test_status_games_v0_3d.py | 6 | 4 種類を混ぜたデッキの新しい対戦から勝敗まで 44 局・固定値・でたらめな操作 12 局 |

Python 3.11・3.12・3.13 で 726 件が通ることを確かめました。

## 11. 将来の拡張

| 事項 | v0.3d の土台 | 加えるときに見直すこと |
|---|---|---|
| 進化（v0.4） | `clear_special_conditions`、`pokemon_id`、失敗の記録の不変条件 | [evolution-readiness-v0.4.md](evolution-readiness-v0.4.md)。進化で特殊状態を消す理由（`reason`）を加える。失敗の記録は進化したら消す（SUPPORTED）。その場合はログとの対応の不変条件も「進化のあとは記録がない」に合わせる |
| 自分のポケモンを特殊状態にする効果 | `AttackEffect.problem` | マヒの再付与の証明（[effect-preflight-v0.3d.md](effect-preflight-v0.3d.md) 4 章）が成り立たない。`problem` で確かめる |
| 特殊状態を回復するトレーナー | `_remove_exclusive`・`clear_special_conditions` | 理由を加える。こんらんを直したあとの「にげる」の再宣言は `UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED` と同じ問題 |
| 自分の弱点・抵抗力のタイプのポケモンの、自分へのダメージのワザ | `deal_attack_damage`（SUPPORTED） | 登録するカードのページの解説と照合する（p.90 と違う説明があれば CONFLICT として止める） |

## 12. 設計上のトレードオフ

| 判断 | 理由 | 代償 |
|---|---|---|
| 5 つの未解決の裁定は止めたまま | 原典で決められない（[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md)）。実装の都合で決めない | 自然な対戦でもまれに止まる（負荷テストの 400 局で 2 局。ポケモンチェックの両方のどくのきぜつ） |
| 自分へのダメージの弱点・抵抗力は、1 枚のカードの解説から一般化して SUPPORTED | p.90 の解説は、ワザの説明による自分へのダメージが「ワザによるダメージ」として計算されることの具体例。p.321 の 8 の定義とも合う | 別のカードのページに違う解説があれば見直す（今は見つかっていない） |
| 登録表の id を変えない | 登録の内容が同じ。id を変えると書き出しと多くのテストが変わる | テスト専用の登録の結果の違いは、エンジンの版で区別する |
| 不変条件でログを見る | 記録の付け間違いを見つける。状態の形を変えない | 不変条件の確認でログをさかのぼる（今の番のぶんだけ） |
