# v0.3a のアーキテクチャ（特殊状態の共通基盤・どく・ポケモンチェック）

v0.3a は、場のポケモンの特殊状態と、番と番のあいだにエンジンが自動で行う処理（ポケモンチェック）を加えた版です。動く特殊状態は「どく」だけで、最初のカードはビードル（PMCG1-004）の「どくばり」です。原典の照合と裁定は [special-conditions-v0.3a.md](special-conditions-v0.3a.md)（特殊状態・どく）、[pokemon-check-v0.3a.md](pokemon-check-v0.3a.md)（ポケモンチェック）、[weedle-v0.3a.md](weedle-v0.3a.md)（カード）にあります。v0.2f の設計（[architecture-v0.2f.md](architecture-v0.2f.md)）の上に作っています。

## 1. 目的と範囲

- 特殊状態を、場のポケモン（`pokemon_id` の `PokemonInPlay`）の状態として持つ。物理的なカード（uid）としては扱わない。
- ポケモンチェックを番の進行に組み込み、番の終わり・ポケモンチェック・次の番の始まりを分ける。ポケモンチェックの中できぜつがあれば、サイド・判定・交代をすませてから次の番を始める。
- どくのダメージを、ワザのダメージと別の種類として与える（ワザのダメージの計算を通さない）。
- にげる・ポケモンいれかえで特殊状態を消す処理を 1 つにする。
- どくを使わない対戦の結果・ログ・状態を v0.2f と同じに保つ。

作らなかったもの: ねむり・マヒ・こんらん、ポケモンチェックの 1（指示されたこと）・3・4、特殊などく、特殊状態を回復するカード、進化、汎用のカード効果の記述言語・イベントの仕組み。

## 2. v0.2f からの変更

| 項目 | v0.2f | v0.3a |
|---|---|---|
| 場のポケモン | `card`・`energy`・`damage`・`pokemon_id`・`trainers` | `conditions`（`SpecialConditions`。frozen）を加えた |
| 番の終わり | `_end_turn`: トラッシュ → `turn_end` → `pokemon_check`（ログだけ）→ `_begin_turn` | `_end_turn`: トラッシュ → `turn_end` → `_pokemon_check`。次の番を始めるのは `_pokemon_check` の最後（きぜつがあれば交代のあと） |
| ポケモンチェック | ログ `pokemon_check` だけ | どくのダメージ（`poison_damage`）、きぜつ（`knock_out` に `timing: "pokemon_check"`）、サイド・判定・交代、両方がきぜつするなら止める |
| きぜつのあとの決定 | 交代のあとは番を終える | 決定の `context` に `"then": "next_turn"` があれば次の番を始める（ポケモンチェックの中のきぜつ）。なければ今までどおり |
| にげる・ポケモンいれかえ | 入れ替えるだけ | ベンチに戻ったポケモンの特殊状態を消す（`conditions.clear_special_conditions`） |
| ワザの効果 | `DamageOnly`・`CoinFlipDamage`・`SelfDamageOnTails` | `PoisonOnHeads`（相手にダメージ → コイン → 「おもて」ならどく） |
| 効果の登録表 | id `kyuura-engine-0.2f`、ワザ 17 | id `kyuura-engine-0.3a`、ワザ 18（ビードルのどくばり）。トレーナーは同じ 5 枚 |
| 新しいモジュール | — | `kyuura_engine/conditions.py`（特殊状態を付ける・消す） |
| 状態の書き出し | 形式 1〜4 | 形式 5（場のポケモンごとの `special_conditions`）。形式 1〜4 は特殊状態があれば `ValueError`。形式 1 はポケモンチェックの中の決定も `ValueError` |
| 不変条件 | — | 特殊状態（バトル場だけ・どくのダメージの値）、番の進行（番と番のあいだに番の終わりとポケモンチェックが 1 回ずつ）、決定の続き |
| ルールの参照 | — | `RULE_REFERENCES` に `special_conditions`（p.311・p.322）・`poison`（p.321〜323） |
| カードデータの写し | `pool_v0_2f` | `pool_v0_3a`（PMCG1-004）。写しを作り直した（`--check` で一致） |
| 段階（`Phase`）・コマンド・決定の種類 | — | 増やしていない |

## 3. 特殊状態のデータ構造

```python
@dataclass(frozen=True)
class Poison:
    damage: int = 10            # ポケモンチェックの「どく」で受けるダメージ（p.322・p.323）

@dataclass(frozen=True)
class SpecialConditions:
    poison: Poison | None = None  # どく（ほかの特殊状態と重複する。p.322）
    # v0.3b: ねむり・マヒ・こんらんのどれか 1 つ（たがいに重複しない。p.322）

PokemonInPlay.conditions: SpecialConditions = NO_SPECIAL_CONDITIONS
```

| 判断 | 理由 |
|---|---|
| 場のポケモン（`PokemonInPlay`）が持つ | 特殊状態はカードではなく、場のポケモンの状態（p.322）。`pokemon_id` は進化しても変わらない（v0.2a）ので、将来の進化でも同じ場所に残せる（進化したら消すのは別の処理）。カードの uid（いちばん上のカード）で持たない |
| `GameState` に別の一覧を作らない | ポケモンが場をはなれたら（きぜつ）状態もいっしょになくなる。一覧を別に持つと、二重の管理と不整合（場にいない番号の状態）が起こりうる |
| どくを別の項目にする | どくはほかの特殊状態と重複し、ねむり・マヒ・こんらんはたがいに重複しない（p.322）。「特殊状態は必ず 1 つ」という形にはしない |
| どくのダメージ量を持つ | どくのダメージを変える効果は「どく状態にかかる」（p.322）。通常のどくは 10 |
| 発生源（どくにしたポケモン）を持たない | 与えたポケモンが場をはなれても変化しても、受けた特殊状態は変わらない（p.322）。処理に使わない（ログの `special_condition.effect` には残す） |
| frozen にする | 複製（`clone`）で共有してよい。変えるときは置きかえる（`dataclasses.replace`）ので、複製したほうを変えても元は変わらない |

## 4. ポケモンチェックの状態遷移と Phase

### 検討した案

| 案 | 内容 | 判断 |
|---|---|---|
| A. `Phase.POKEMON_CHECK` を加える | ポケモンチェックの間の段階 | 採らなかった。ポケモンチェックは 1 つのコマンドの中で終わるか、決定を待つ（そのときの段階は `TAKE_PRIZE`・`PROMOTE_ACTIVE`）。コマンドの境目でこの段階になることがなく、受け付けるコマンドもない。段階を増やすと `ALLOWED`（段階ごとのコマンド）と不変条件が増えるだけ |
| B. エンジンの中の処理にし、続きを決定に書く | `_pokemon_check` がコマンドの中で処理する。決定を待つときは、決定の `context` の `"then"` に「次の番を始める」と書く | **採った** |
| C. ポケモンチェック専用の進行状態を `GameState` に持つ | 「ポケモンチェックの何番目まで処理したか」など | 採らなかった。v0.3a では、ポケモンチェックの途中で止まるのは、2 のあとのきぜつの決定だけで、そこから先は「次の番を始める」しかない。決定の続きとして持てば足りる（CLAUDE.md「段階や保留中のリストを別に増やさない」） |

B の性質:

- ポケモンチェックの中の決定を待つ間、`phase` は `TAKE_PRIZE`・`PROMOTE_ACTIVE`、`current_player`・`turn_number` は番を終えたプレイヤーの番のまま。`turn_owner` の不変条件は変わらず成り立つ。次の番はまだ始まっていない（ドロー・エネルギーの回数のリセットは `_begin_turn`）。
- 二重に行わない: ワザのあとの決定（`then` なし）は交代のあとに `_end_turn`（番の終わり → ポケモンチェック）。ポケモンチェックの中の決定（`then = "next_turn"`）は交代のあとに `_begin_turn`。どちらも 1 回だけ通る。
- 対戦が終わったら（判定・山札切れ・止める）、次の番は始まらない。
- v0.3b でポケモンチェックの 3（ねむりのコイン）・4 を加え、2 のきぜつの決定のあとに 3・4 を続ける必要が出たら、`then` の値を増やす（「ポケモンチェックの 3 から続ける」）。それでも足りなければ C を検討する。（v0.3b では、3・4 は決定を出さないので続きは 1 つで足り、`then` の値は `"next_turn"` のまま、交代のあとに 3・4 → 次の番とした。[architecture-v0.3b.md](architecture-v0.3b.md) 6 章）

```
_end_turn → turn_end → _pokemon_check → pokemon_check
   → 2: どく（両方きぜつ → _halt）→ poison_damage
   → きぜつなし: _begin_turn
   → きぜつ: knock_out(timing) → _after_knockouts(then="next_turn")
        → take_prize の決定 → 判定 → promote_active の決定 → _begin_turn
```

## 5. PendingDecision との統合

- 決定の種類・再開先は増やしていない（`take_prize`・`promote_active`。v0.2a）。
- 続きは決定の `context` の `"then"`（`engine.NEXT_TURN = "next_turn"`）。ワザのあとの決定には書かない（v0.2f と同じ形。形式 2〜4 の書き出しも同じ）。
- ポケモンチェックの中でバトル場に出すのは 1 人だけ（両方がきぜつする場合は止める）。不変条件で確かめる。
- 決定を待つ間のほかのコマンドは `WRONG_PHASE`・`NOT_YOUR_DECISION`・`WRONG_DECISION`・`INVALID_CHOICE`（状態も乱数も変えない。v0.2a から）。

## 6. ダメージの原因の区別

| | ワザによるダメージ | どくのダメージ |
|---|---|---|
| 根拠 | p.320・p.321 | p.321「8」（ワザによるダメージではない）・p.322・p.323 |
| 計算 | `effects.deal_attack_damage`（p.321 の 8 段階。弱点・抵抗力・プラスパワー・ディフェンダー） | `Poison.damage` をそのまま足す（弱点・抵抗力・プラスパワー・ディフェンダーは関係しない） |
| ログ | `damage` | `poison_damage`（`amount`・`total_damage`） |
| きぜつの時点 | ワザの要素をすべて処理してから（v0.2f） | ポケモンチェックの 2 のダメージをすべて与えてから |

どくのダメージを `deal_attack_damage` に通さないのは、計算の規定が違う（8 段階のどれも使わない）ためです。共通にしたのは、ダメージカウンター（`PokemonInPlay.damage`）と、きぜつのあとの処理（`_knock_out`・`_after_knockouts`）だけです。ダメージの種類を表す汎用の型は作っていません（イベントの種類で区別する）。

## 7. きぜつ処理

- `_knock_out(state, owner, pokemon, simultaneous=False, timing=None)`: ポケモンチェックの中のきぜつは `timing="pokemon_check"` をログに書く。トラッシュ（ついているトレーナーを含む）は同じ。特殊状態はポケモンといっしょになくなる。
- サイドを取るのは、きぜつしたポケモンの持ち主の相手（番のプレイヤーに固定しない）。
- 両方のプレイヤーのポケモンが同じポケモンチェックのどくできぜつする場合は、原典で決められない（同時か・交代の順番・サイドの順番を決める人）ので、ダメージを与える前に `_halt`（`Phase.HALTED`、`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`）。勝敗・サドン・デスとは別の終わり方。

## 8. ターン終了の順番

1. 番のプレイヤーの操作が終わる（ワザなら、きぜつ・サイド・判定・交代まで。p.309）
2. 番の終わりにトラッシュするトレーナー（プラスパワー・期限のきたディフェンダー）をトラッシュ（v0.2c・v0.2e）
3. `turn_end`
4. ポケモンチェック（`pokemon_check` → どく → きぜつ・サイド・判定・交代）
5. 次の番（`turn_start` → ドロー。山札がなければ負け）

## 9. 状態の複製と書き出し

- `PokemonInPlay.clone` は `conditions` をそのまま共有する（frozen）。`copy.deepcopy`・`pickle` もそのまま（dataclass）。ポケモンチェックの中の決定を待つ状態も、複製して同じコマンドを送れば同じ結果（テストで確かめた）。
- 形式 5 = 形式 4 + 場のポケモンごとの `special_conditions`。特殊状態がなければ `{}`。
- 形式 1〜4 は特殊状態を表せないので、特殊状態のポケモンがいれば `ValueError`（黙って落とさない。v0.2b・v0.2c と同じ方針）。形式 1 は決定の中身を持たないので、ポケモンチェックの中の決定（続きが次の番）も `ValueError`。
- ゲーム状態全体を辞書・JSON から読み込む機能はありません（v0.2a から。乱数だけは保存・復元できる）。

## 10. 不変条件

`check_invariants` に加えたもの:

| 不変条件 | 内容 |
|---|---|
| 特殊状態の型と値 | `conditions` が `SpecialConditions`。どくなら `Poison` で、ダメージは 10 の倍数の正の数 |
| ベンチに特殊状態がない | 特殊状態があるのはバトル場のポケモンだけ（p.322）。にげる・ポケモンいれかえで消し忘れたら違反 |
| 番の進行 | ログの最後の 2 つの `turn_start` の間に `turn_end` → `pokemon_check` がちょうど 1 回ずつ。今の番の始まりのあとは、番の途中なら 0 回、ポケモンチェックの中の決定なら 1 回ずつ、終わった対戦はどちらか（ポケモンチェックを二度しない・飛ばさない・次の番と混ざらない） |
| 決定の続き | `then` は `"next_turn"` だけで、`take_prize`・`promote_active` の決定にだけ付く。ポケモンチェックの中の交代は 1 人だけ |

場から消えたポケモンに特殊状態が残らないことは、データの持ち方（場のポケモンが持つ）で保証されます。番の進行の不変条件はログの最後の 2 つの番だけを見るので、対戦が長くなっても検査の手間はほとんど変わりません。

## 11. 公開 API の変更

| もの | 内容 |
|---|---|
| `Poison`・`SpecialConditions`（`kyuura_engine` から） | 特殊状態の型。`PokemonInPlay.conditions` |
| `kyuura_engine.conditions` | `poison`・`clear_special_conditions`・`NORMAL_POISON`・`POISON`・`RETREAT`・`SWITCH`（実装を加える人向け） |
| `effects.PoisonOnHeads` | どくばりの実装 |
| `engine.NEXT_TURN` | 決定の続き（`context` の `"then"`） |
| `state_to_dict(state, format_version=5)` | 特殊状態を含む形式 |
| エラーコード | `UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`（`Phase.HALTED` の `halt.code`、以後のコマンドの `UnsupportedError`） |
| ログ | `special_condition`・`special_conditions_removed`・`poison_damage`。`knock_out` の `timing` |
| 効果の登録表・版 | id `kyuura-engine-0.3a`、ワザ 18。版 `0.3.0a0` |

コマンド・段階・決定の種類は増やしていません。

## 12. 互換性

- どくのない対戦は v0.2f と同じ: v0.2f のコミット `5ce4d4e` と今の版で、既存のデッキ 7 組（v0.1〜v0.2f の統合テストのデッキ）× 40 seed（280 局、26,715 コマンド）を同じ手順で対戦させ、状態とログ（形式 4。登録表の id を除く）がすべて同じだった。
- v0.2f のテスト 449 件を v0.3a のコードで実行すると、失敗するのは下の 6 件だけ。v0.1 の参照データ・乱数とコインの固定値は変わらない。

### 変更した既存のテスト

| テスト | 変更 | 保証が弱くなっていない理由 |
|---|---|---|
| test_effects.py `test_attacks_with_text_follow_the_verified_latest_description` | 説明文のあるワザの一覧にどくばり（`PMCG1-004#0`） | 一覧をちょうど確かめる性質は同じ。どくばりも照合の記録と比べる |
| test_effects.py `RegistryImmutabilityTest.test_with_and_without_do_not_change_the_original` | 登録したワザの数 17 → 18 | 登録表が変わらないことを確かめる性質は同じ |
| test_trainers.py `test_default_registry_has_exactly_the_registered_cards` | 登録表の id `kyuura-engine-0.3a` | トレーナーの一覧と実装の一覧は同じまま |
| test_rng_and_serialize.py `test_format_2_adds_only_documented_fields` | 登録表の id | 同上 |
| test_rng_and_serialize.py `test_unknown_format_is_rejected` | 形式の一覧に 5。知らない形式の例を 5 から 0・6・"5"・None に | 知らない形式を拒否することは、例を増やして確かめる |
| test_cards.py `test_v0_1_pool_is_ten_basic_pokemon_and_six_basic_energy` | `pool_v0_3a` とビードルが使えることを確かめ、v0.1 の組の数からビードルを除く | v0.1 の組（たねポケモン 10・基本エネルギー 6）の確認は同じ |

tests/helpers.py に `WEEDLE` と、`build_test_state` のバトル場の指定に `"poison"` を加えました（既存の値・手順は変えていない）。

## 13. 将来の拡張方針

| 将来の機能 | v0.3a の土台 | 加えるもの |
|---|---|---|
| ねむり・マヒ（v0.3b） | `SpecialConditions`、`clear_special_conditions`、`_pokemon_check`、形式 5 | ねむり・マヒ・こんらんのどれか 1 つを持つ項目（重複しない。p.322）。マヒになった番の番号。ポケモンチェックの 3（ねむりのコイン）・4（マヒの回復）。`UseAttack`・`Retreat` の拒否。回復・置きかえのログ。2 のきぜつと 3・4 の前後の照合 |
| こんらん | 同上 | ワザの手順 5 のコイン・自分への 20（弱点・抵抗力の影響を受ける。p.322）、にげるのコイン・失敗の記録 |
| ポケモンチェックの 1 | `_pokemon_check` | 指示された効果の一覧と、前に番をおこなったプレイヤーが順番を選ぶ決定（p.323） |
| 特殊などく | `Poison.damage` | 付ける効果。重ねて受けたときの扱いの照合（一部は原典で決められない） |
| 進化 | `pokemon_id` | 進化したら特殊状態を消す（p.322） |
| 特殊状態を回復するトレーナー | `clear_special_conditions` | 消える理由（`reason`）を増やす |

## 14. 設計上のトレードオフ

| 判断 | 理由 | 代償 |
|---|---|---|
| `Phase.POKEMON_CHECK` を加えなかった | 観察できない段階を増やさない。決定の仕組みで足りる | ポケモンチェックの途中かどうかは、決定の `context` を見ないと分からない |
| 両方がきぜつするなら止める | 原典で決められない（3 つの点）。推測で「同時」として処理しない | どく状態のポケモンが両方にいる対戦で、まれに対戦が止まる |
| どくのダメージをすべて与えてからきぜつを処理する | ポケモンチェックの 2 は 1 つの段階。片方だけがきぜつするなら、順番で勝敗は変わらない | 対戦が終わるとき、もう一方のポケモンの最後のどくのダメージが状態に残る（どちらの順でも勝敗は同じ） |
| どくばりの相手がきぜつしたらコインを投げない | 対象がいない内容は無視する（p.309） | 投げる読み方と比べて、乱数の使い方だけが違う（結果は同じ） |
| 形式 1 でポケモンチェックの中の決定を拒否する | 続きの情報（次の番を始める）を黙って落とさない | 形式 1 しか読めないクライアントは、その瞬間の状態を受け取れない |
