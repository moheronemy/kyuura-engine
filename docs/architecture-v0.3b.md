# v0.3b のアーキテクチャ（ねむり・マヒとポケモンチェックの拡張）

v0.3b は、v0.3a の特殊状態の共通基盤に「ねむり」「マヒ」を加え、ポケモンチェックの 3（ねむりのコイン）・4（マヒの回復）と、ワザ・にげるの制限を実装した版です。対応カードはキャタピー（PMCG1-002）の「いとをはく」とパラス（PMCG2-003）の「ひっかく」「キノコのほうし」です。原典の照合と裁定は [sleep-paralysis-v0.3b.md](sleep-paralysis-v0.3b.md)（ねむり・マヒ）、[pokemon-check-v0.3b.md](pokemon-check-v0.3b.md)（ポケモンチェック）、[cards-v0.3b.md](cards-v0.3b.md)（カード）にあります。v0.3a の設計（[architecture-v0.3a.md](architecture-v0.3a.md)）の上に作っています。

## 1. 目的と範囲

- 複数の番にまたがって続き、ワザ・にげるを制限し、ポケモンチェックの中で回復する特殊状態を、場のポケモンの状態として持つ。
- ねむり・マヒはたがいに重複せず、どくとは重複する（p.322）ことを、データの形で表す。
- マヒの回復する番を、番の数を足すのではなく「マヒ状態になった番の次の持ち主の番」（p.323）で決める。
- ポケモンチェックの 2（どく）のきぜつ・サイド・交代のあとに 3・4 を行い、次の番を始める。二重に行わない。
- 原典で決められない場合（両方の対戦ポケモンがねむり、マヒの再付与で回復する番が変わる）は、乱数を使う前に止める・拒否する。
- 特殊状態を使わない対戦・どくだけの対戦の結果・ログ・乱数を v0.3a と同じに保つ。

作らなかったもの: こんらん、ポケモンチェックの 1、進化、特殊状態を回復するトレーナー、特殊などく、汎用の効果の記述言語・イベントの仕組み、新しい段階（`Phase`）・コマンド・決定の種類。

## 2. v0.3a からの変更

| 項目 | v0.3a | v0.3b |
|---|---|---|
| 特殊状態 | `SpecialConditions(poison)` | `SpecialConditions(poison, exclusive)`。`exclusive` は `Asleep`・`Paralyzed(turn)`・None（こんらんを加えるときもここ） |
| 付ける・消す | `conditions.poison`・`clear_special_conditions` | `put_to_sleep`・`paralyze`（置きかえ・二重にならない・再付与の未解決）、`recover_from_sleep`・`recover_from_paralysis`、`paralysis_recovery_turn`・`paralysis_problem` |
| ワザ | 番・ワザの位置・登録・エネルギー | ワザの位置のあとに、ねむり・マヒなら `POKEMON_ASLEEP`・`POKEMON_PARALYZED`（p.309 の手順 1 はエネルギーの確認より前） |
| にげる | 控え・入れ替える控え・エネルギー | 控えのあとに、ねむり・マヒなら同じコードで拒否（p.311） |
| ポケモンチェック | 2（どく）→ きぜつ → 次の番 | 2 → きぜつ・サイド・判定・交代 → 3（ねむりのコイン）→ 4（マヒの回復）→ 次の番（`_pokemon_check_sleep_and_paralysis`） |
| 決定の続き（`then`） | `"next_turn"`: 交代のあと次の番を始める | 値は同じ `"next_turn"`。交代のあと 3・4 をしてから次の番を始める |
| 止める | `UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT` | 加えて `UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`（両方の対戦ポケモンがねむり。コインの前） |
| 拒否（未解決） | — | `UNRESOLVED_REPARALYSIS_RECOVERY_TURN`（`UnsupportedError`。対応カードでは起こらない） |
| ワザの効果 | `PoisonOnHeads` ほか | `ParalyzeOnHeads`（いとをはく）・`PutToSleep`（キノコのほうし。ダメージの要素がない） |
| 効果の登録表 | id `kyuura-engine-0.3a`、ワザ 18 | id `kyuura-engine-0.3b`、ワザ 21（いとをはく、ひっかく、キノコのほうし）。トレーナーは同じ 5 枚 |
| 状態の書き出し | 形式 5（`special_conditions` に `poison`） | 形式 5 に `sleep: {}`・`paralysis: {"turn": n}` を加えた（形式の番号は同じ。6 章） |
| ログ | `special_condition`・`special_conditions_removed`・`poison_damage` | `sleep_check` を加えた。`coin_flip` の `source: "pokemon_check"`。`special_condition` のマヒに `paralyzed_turn`・`recovery_turn`。消えた理由に `sleep_coin`・`paralysis_end`・`replaced` |
| ログの番 | イベントの項目が `turn` を上書きできた | `add_event` が `turn` の項目を拒否する（ログの `turn` はいつも今の番） |
| `turn_owner` | `engine.turn_owner` | `state.turn_owner` に移した（`engine.turn_owner` も同じもの）。マヒの回復する番の計算に使う |
| 不変条件 | 特殊状態の型・ベンチ・番の進行・決定の続き | `exclusive` の型、マヒ状態になった番（1〜今の番）、期限の過ぎたマヒが残らない |
| カードデータの写し | `pool_v0_3a` | `pool_v0_3b`（PMCG1-002・PMCG2-003）。作り直して `--check` で一致 |
| 版 | `0.3.0a0` | `0.3.0b0` |

## 3. 特殊状態のデータ構造

```python
@dataclass(frozen=True)
class Asleep:                 # ねむり（持つ情報はない）。name = "sleep"
    pass

@dataclass(frozen=True)
class Paralyzed:              # マヒ。name = "paralysis"
    turn: int                 # マヒ状態になった番（GameState.turn_number）

@dataclass(frozen=True)
class SpecialConditions:
    poison: Poison | None = None                    # どく（ほかと重複する）
    exclusive: Asleep | Paralyzed | None = None     # ねむり・マヒ（・将来のこんらん）のどれか 1 つ
    def names(self) -> tuple[str, ...]: ...         # p.322 の順: ("poison", "sleep") など
    asleep: bool; paralyzed: bool                   # 性質
```

| 判断 | 理由 |
|---|---|
| ねむり・マヒを 1 つの項目（`exclusive`）にする | 「「ねむり」「マヒ」「こんらん」状態が重複することはありません」（p.322）を型で表す。両方を持つ状態は作れない |
| どくは別の項目のまま | どくは重複する（p.322）。ねむり・マヒが置きかわっても、回復しても、どくは残る |
| マヒは「マヒ状態になった番」を持つ | 回復するのは「マヒ状態になった番の「次の自分（持ち主）の番」の終わり」（p.323）。持ち主は場のポケモンの持ち主（場所）で決まり、番の持ち主は `turn_owner` で決まるので、番の番号だけを持てば、回復する番は計算できる。「回復する番」そのものを持たないのは、規定の書き方（なった番から数える）に合わせるため。番の数 + 1 にはしない（持ち主の番にマヒ状態になったら 2 つ後） |
| ねむりは情報を持たない | 回復はポケモンチェックのたびのコインだけ（p.322）。期限・回数はない |
| 発生源を持たない | 与えたポケモンが場をはなれても変わらない（p.322） |
| frozen・`dataclasses.replace` で置きかえる | 複製（`clone`）で共有してよい（v0.3a と同じ）。`ASLEEP` は 1 つを共有する |

## 4. 状態の付与・上書き・解除

| 処理 | 関数 | ログ |
|---|---|---|
| ねむりにする | `put_to_sleep(state, owner, pokemon, effect=…)`: もうねむりなら変えない（`already`）。マヒなら消して（`replaced`）ねむり。どくは残す | `special_condition`（`condition: "sleep"`） |
| マヒにする | `paralyze(…)`: `paralysis_problem` で未解決を確かめる。もうマヒなら変えない（`already`）。ねむりなら消して（`replaced`）マヒ（`turn` は今の番）。どくは残す | `special_condition`（`condition: "paralysis"`・`paralyzed_turn`・`recovery_turn`） |
| ねむりから回復 | `recover_from_sleep`（ポケモンチェックの 3 の「おもて」） | `special_conditions_removed`（`("sleep",)`・`sleep_coin`） |
| マヒから回復 | `recover_from_paralysis`（ポケモンチェックの 4） | `special_conditions_removed`（`("paralysis",)`・`paralysis_end`） |
| ベンチに戻る | `clear_special_conditions`（にげる・ポケモンいれかえ。v0.3a） | `special_conditions_removed`（すべて。`retreat`・`switch`） |
| きぜつ | 場のポケモンといっしょになくなる（v0.3a） | `knock_out` |
| 進化 | 未実装（加えるときは `clear_special_conditions` に理由を加える） | — |

付ける処理は、バトル場のポケモンでなければ `RuntimeError`（エンジンの不具合）です。ベンチのポケモンは特殊状態にならない（p.322）ので、プレイヤーの操作の誤りではありません。

## 5. ワザとにげるの制限

```
UseAttack:  番 → ワザの位置（INVALID_ATTACK）→ ねむり・マヒ（POKEMON_ASLEEP・POKEMON_PARALYZED）
            → 登録（UNSUPPORTED_ATTACK）→ エネルギー（INSUFFICIENT_ENERGY）→ attack → 効果（コイン）
Retreat:    番 → 控えがいない（NO_BENCH）→ ねむり・マヒ → 入れ替える控え → エネルギー → トラッシュ → 入れ替え
PlayTrainer（ポケモンいれかえ）: 制限しない（p.325）。ベンチに戻ったら特殊状態を消す
```

確認はすべて処理の前（コイン・ダメージ・エネルギーのトラッシュ・番の終わりの前）です。`apply_command` は複製した状態で処理するので、拒否は渡した状態も乱数も変えません。エネルギーをつける・ベンチに出す・トレーナーを使う・番を終えるは制限しません（p.322「特殊状態になっていても、そのポケモンにエネルギーカードをつけたり…することはできます」）。

## 6. ポケモンチェックの処理と Phase

| 案 | 内容 | 判断 |
|---|---|---|
| A. `Phase.POKEMON_CHECK` を加える | ポケモンチェックの段階 | 採らなかった（v0.3a と同じ理由。3・4 はプレイヤーの選択がなく、1 つのコマンドの中で終わる） |
| B. 決定の続きに「ポケモンチェックの 3 から」を書く | `then` の値を増やす | 採らなかった。3・4 は決定を出さないので、決定を待つのはいつも 2 のきぜつのあと。続きは 1 つ（3 → 4 → 次の番）で足りる |
| C. `then = "next_turn"` のまま、交代のあとの処理を「3・4 → 次の番」にする | `_next_promotion_or_end` が `_pokemon_check_sleep_and_paralysis` を呼ぶ | **採った**。値の意味（ポケモンチェックの中。次の番はまだ始まっていない）と書き出しの形が v0.3a と同じ |
| D. ポケモンチェックの進行状態を `GameState` に持つ | 「何番まで処理したか」 | 採らなかった（段階や保留中のリストを別に増やさない。CLAUDE.md） |

```
_end_turn → turn_end → _pokemon_check → pokemon_check
   → 2: どく（両方きぜつ → _halt）→ poison_damage
   → きぜつなし: _pokemon_check_sleep_and_paralysis
   → きぜつ: knock_out(timing) → _after_knockouts(then="next_turn")
        → take_prize の決定 → 判定（決まれば GAME_OVER）→ promote_active の決定
        → _pokemon_check_sleep_and_paralysis
_pokemon_check_sleep_and_paralysis
   → 3: 両方ねむり → _halt（コインの前）／ 持ち主が coin_flip → sleep_check →（おもて）回復
   → 4: 回復する番ならマヒを消す
   → _begin_turn（turn_start → draw）
```

- `_begin_turn` を呼ぶのは `_pokemon_check_sleep_and_paralysis` の最後だけ（と、対戦の開始）。ポケモンチェックの 3・4 は 1 回のポケモンチェックに 1 回だけ通る。
- ワザのあとの決定（`then` なし）は、交代のあとで `_end_turn`（番の終わり → ポケモンチェック）。v0.3a と同じ。
- 番の進行の不変条件（番と番のあいだに `turn_end` → `pokemon_check` が 1 回ずつ）は v0.3a のまま。

## 7. コイントス

- ねむりのコインは v0.2d の `flip_coins` を使う（`source: "pokemon_check"`、`effect: "sleep"`、`player` は持ち主、`card`・`pokemon_id` はねむりのポケモン）。1 枚につき `getrandbits(1)` 1 回。プレイヤーが結果を選ぶ口はない（テストは `with_coin_results`）。
- 結果は `sleep_check`（`result`・`recovered`）に残す。ワザのコイン（`source: "attack"`）と区別できる。
- 乱数を使う順番: ワザのコイン → ポケモンチェックの 3 のコイン。ねむりがなければポケモンチェックで乱数を使わない。マヒの回復・どく・きぜつ・サイド・交代は乱数を使わない（[pokemon-check-v0.3b.md](pokemon-check-v0.3b.md) 5 章）。
- 両方がねむりなら、コインの前に止める（乱数を使わない）。マヒの再付与の未解決も、コインの前に確かめる。

## 8. きぜつ処理

- 2 のどくのきぜつは v0.3a と同じ（`_knock_out(…, timing="pokemon_check")` → `_after_knockouts(then=NEXT_TURN)`）。きぜつしたポケモンのねむり・マヒはいっしょになくなり、3 のコインを投げない。
- 交代して出てきたポケモンはベンチにいたので特殊状態がなく、3・4 ですることがない。
- 勝敗が決まったら（`GAME_OVER`・`SUDDEN_DEATH`）、3・4 と次の番はない。残ったポケモンのねむり・マヒは状態に残る（不変条件は終わった対戦でも成り立つ）。
- 両方がどくできぜつする場合は v0.3a のまま止める（ダメージ・コインの前）。

## 9. PendingDecision

新しい決定の種類・再開先・`context` の項目はありません。ポケモンチェックの中で決定を待つ間（`TAKE_PRIZE`・`PROMOTE_ACTIVE`、`then = "next_turn"`）は、ねむり・マヒはそのまま（3・4 はまだ）で、マヒの回復する番が今の番でも不変条件を満たします。決定を待つ間のほかのコマンド・不正な決定は拒否し、コインを先に投げません。

## 10. シリアライズ

| 形式 | 特殊状態 |
|---|---|
| 1〜4 | 表せない。特殊状態（どく・ねむり・マヒ）のポケモンがいれば `ValueError`（黙って落とさない） |
| 5 | 場のポケモンごとの `special_conditions`: `{}`、`{"poison": {"damage": 10}}`、`{"sleep": {}}`、`{"paralysis": {"turn": 3}}`、`{"poison": …, "sleep": {}}` など |

形式 5 に項目を加えましたが、形式の番号は 6 にしていません。v0.3a の形式 5 の項目（`poison`）の意味は変わらず、どくだけの状態・特殊状態のない状態の書き出しは v0.3a と同じです（720 局の比較で確かめた。12 章）。v0.3a の形式 5 を読むクライアントは、知らない項目（`sleep`・`paralysis`）があれば拒否してください（黙って無視すると、ワザ・にげるの制限を表示できない）。マヒの回復する番は書き出さず、`turn` と `first_player` から求めます（`conditions.paralysis_recovery_turn`。ログの `special_condition` には `recovery_turn` がある）。

複製: `PokemonInPlay.clone` は `conditions` を共有する（frozen）。`copy.deepcopy`・`pickle`・乱数の JSON 保存と復元（`rng_state_to_json`・`rng_from_json`）のどれでも、同じコマンドで同じ結果（ねむりのコインも同じ）になることをテストで確かめました。**ゲーム状態全体を辞書・JSON から読み込む機能は、引き続きありません**（v0.2a から。乱数だけは保存・復元できる）。

## 11. 不変条件

| 不変条件 | 内容 |
|---|---|
| 特殊状態の型と値 | `conditions` が `SpecialConditions`。どくは `Poison`（10 の倍数の正の数）。`exclusive` は `Asleep`・`Paralyzed`・None のどれか |
| マヒ状態になった番 | 1 以上、今の番以下の整数 |
| 期限の過ぎたマヒが残らない | `paralysis_recovery_turn(…) >= turn_number`（回復する番の終わりのポケモンチェックで消えていない、を見つける。ポケモンチェックの中の決定・終わった対戦でも成り立つ） |
| ベンチに特殊状態がない | v0.3a と同じ（ねむり・マヒも含む） |
| 番の進行・決定の続き | v0.3a と同じ |

ねむり・マヒが同時にないことは、データの形（`exclusive` は 1 つ）で保証されます。場から消えたポケモンに特殊状態が残らないことも、データの持ち方（場のポケモンが持つ）で保証されます。

## 12. 互換性

- **v0.3a（`1577bff`）との比較**: 同じ入力で次の 720 局（57,901 コマンド）を対戦させ、終わった状態・ログ・乱数の状態（形式 4 または 5。登録表の id を除く）がすべて同じだった。
  1. 特殊状態を使わない既存のデッキ 7 組 × 40 seed（280 局）
  2. どくだけを使うビードルのデッキ × 40 seed（どくのきぜつ・ポケモンチェックの中の勝敗を含む）。このうち 20 局は、途中のすべての状態（ポケモンチェックの中の決定を含む）も同じ
  3. どくを直さないビードルのミラー × 400 seed（seed 27 など 5 局が `UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT` で止まる。止まる局・止まった状態も同じ）
- v0.3a のテスト 522 件を v0.3b のコードで実行すると、失敗するのは下の 5 件だけ（どれも登録表の id・登録の一覧を確かめるもの）。v0.1 の参照データ・乱数とコインの固定値（test_reproducibility.py・test_coins.py・test_coin_games.py・test_pikachu_games.py・test_weedle_games.py）は変えていない。
- コマンド・段階・決定の種類は増やしていない。エラーコードは 3 つ増えた（`POKEMON_ASLEEP`・`POKEMON_PARALYZED`・`UNRESOLVED_REPARALYSIS_RECOVERY_TURN`）。止めるコードが 1 つ増えた（`UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`）。どれも、ねむり・マヒのない対戦では出ない。

### 変更した既存のテスト

| テスト | 変更 | 保証が弱くなっていない理由 |
|---|---|---|
| test_effects.py `test_attacks_with_text_follow_the_verified_latest_description` | 説明文のあるワザの一覧に、いとをはく（`PMCG1-002#0`）・キノコのほうし（`PMCG2-003#1`） | 一覧をちょうど確かめる性質は同じ。加えたワザも照合の記録と比べる |
| test_effects.py `RegistryImmutabilityTest.test_with_and_without_do_not_change_the_original` | 登録したワザの数 18 → 21 | 登録表が変わらないことを確かめる性質は同じ |
| test_trainers.py `test_default_registry_has_exactly_the_registered_cards` | 登録表の id `kyuura-engine-0.3b` | トレーナーの一覧と実装の一覧は同じまま |
| test_rng_and_serialize.py `test_format_2_adds_only_documented_fields` | 登録表の id | 同上 |
| test_cards.py `test_v0_1_pool_is_ten_basic_pokemon_and_six_basic_energy` | `pool_v0_3b` とキャタピー・パラスが使えることを確かめ、v0.1 の組の数からこの 2 枚を除く | v0.1 の組（たねポケモン 10・基本エネルギー 6）の確認は同じ |

tests/helpers.py に `CATERPIE`・`PARAS` と、`build_test_state` のバトル場の指定に `"sleep"`・`"paralysis"` を加えました。`best_affordable_attack` は、ダメージの目安の数字がないワザを 0 として比べるようにしました（それまでの対応カードにはないので、既存の対戦の手順は変わらない。上の比較で確かめた）。

## 13. 将来の拡張（こんらん）

v0.3c で実装しました（[architecture-v0.3c.md](architecture-v0.3c.md)）。下の表は v0.3b の時点の見通しです。実装では、こんらんの 20 をワザによるダメージの計算とは別にし（プラスパワー・ディフェンダーを計算するかは原典で決められないので、ついていれば止める）、にげるの失敗の記録は場のポケモンごとに持ちました。

| 事項 | v0.3b の土台 | 加えるもの |
|---|---|---|
| こんらんの保持 | `SpecialConditions.exclusive` | `Confused`（情報を持たない）。ねむり・マヒと置きかわる（p.322）。どくと重複する |
| ワザのときのコイン | ワザの手順の確認（p.309 の手順 1〜3）・`flip_coins` | 手順 5: 持ち主がコイン 1 枚、「うら」ならワザの内容に関わらず自分に 20（p.309・p.322） |
| 自分への 20 の弱点・抵抗力 | `deal_attack_damage` の `SELF`（v0.2f。弱点・抵抗力が関係すると止める） | こんらんのダメージは「「弱点・抵抗力」の影響を受けます」（p.322）と書かれているので、こんらん専用の計算（ワザによるダメージか、プラスパワー・ディフェンダーの扱い）を原典で照合する |
| にげるときのコイン | `_retreat` | p.311 の 3: コイン 1 枚、「うら」なら失敗（エネルギーはもどらない）。一度失敗したら、その番はもう宣言できない（番ごとの記録が要る） |
| 回復 | `clear_special_conditions` | 自然に回復しない（p.322）。ベンチに戻る・進化で消える |
| ポケモンチェック | 3・4 | こんらんはポケモンチェックですることがない（p.323 の手順にない） |

## 14. 設計上のトレードオフ

| 判断 | 理由 | 代償 |
|---|---|---|
| 両方がねむりなら止める | コインの順番が原典で決まらず、順番で乱数の割り当てが変わる。番のプレイヤーから投げる正規化をしない | 自分をねむりにする効果などを加えると、止まる対戦がありうる（v0.3b の対応カードでは起こらない） |
| 2 のきぜつの処理を 3 より先 | 原典の「きぜつしてトラッシュに置かれる」「すぐに出す」から導ける | きぜつの処理をポケモンチェックの最後に置く読み方と比べて、乱数の使い方と交代するプレイヤーの見る情報が違う（[pokemon-check-v0.3b.md](pokemon-check-v0.3b.md) 2 章で根拠を書いた） |
| マヒの再付与で回復する番が変わるなら拒否 | 原典で決められない | 自分をマヒにする効果を加えると、その効果が使えない場面がありうる |
| `then` の値を変えない | 書き出しの形とクライアントへの意味を保つ | 値の名前（`next_turn`）だけでは、交代のあとに 3・4 があることが分からない（コードと文書で説明している） |
| マヒの回復する番を書き出さない | 状態は規定の形（なった番）だけを持つ | クライアントは `first_player` から計算するか、ログの `recovery_turn` を見る必要がある |
