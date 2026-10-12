# アーキテクチャ（v0.4b）: ワザによる持続する効果と「かたまる」

v0.4b は、ワザによって番をまたいで残る効果（「持続する効果」。p.322・p.323）を、場のポケモンが持つ値として保持し、規定の時点・行動で消す仕組みを加えた版です。対応カードはトランセル（キャタピーから進化）・コクーン（ビードルから進化）で、どちらも「かたまる」（コインが「おもて」なら、次の相手の番、ダメージを受けない。ダメージ以外の効果は受ける）を持ちます。原典照合は [persistent-effects-v0.4b.md](persistent-effects-v0.4b.md)（規定）・[harden-v0.4b.md](harden-v0.4b.md)（カード）・[persistent-damage-v0.4b.md](persistent-damage-v0.4b.md)（ダメージ計算）にあります。

## 1. 方針

- 3 つを 1 つの仕組みにまとめない: ワザによる持続する効果（`persistent_effects`）・ついているトレーナーカード（`trainers`。物理的なカード）・特殊状態（`conditions`）は、別の項目・別の関数・別のログで扱う。
- 汎用の効果の言語・イベントの仕組みは作らない。v0.4b で要る効果は 1 種類（`PreventDamage`）で、型の一覧（`PERSISTENT_EFFECT_TYPES`）に加えていく形にした。
- ダメージの防止は、`DamageModifier` に大きな負の数を入れて 0 に見せる形にしない。p.321 のとおり「ダメージを受けない」状態ならダメージの要素を無効にする（計算しない）。
- 原典で決められない場合（コインでダメージの量を決める要素が無効になるときのコイン）は、コインの前に止める。
- 持続する効果を使わない対戦は、v0.4a と同じ結果・ログ・乱数にする。

## 2. v0.4a からの変更

| 項目 | v0.4a | v0.4b |
|---|---|---|
| `PokemonInPlay` | 特殊状態・ついているトレーナー・進化の重なり | `persistent_effects`（ワザによる持続する効果のタプル）を加えた |
| 持続する効果の値 | — | `state.PreventDamage(source_card, source_player, created_turn, active_turn)`（frozen）・`PERSISTENT_EFFECT_TYPES` |
| 持続する効果の処理 | — | 新しいモジュール `persistent.py`（付ける・消す・期限切れ・「ダメージを受けない」状態か） |
| ワザの実装 | 7 種類 | `PreventDamageOnHeads`（かたまる）を加えた。`CoinFlipDamage.problem`（「ダメージを受けない」相手なら `UNRESOLVED_PREVENTED_COIN_DAMAGE`） |
| ワザのダメージ | `deal_attack_damage` が計算して与える | 受けるポケモンが「ダメージを受けない」状態なら、計算せずにログ `damage_prevented` だけを残す |
| 番の終わり | ついているトレーナーをトラッシュ・にげるの失敗の記録を消す | はたらく番が終わった持続する効果を消す（`remove_expired_persistent_effects`）を加えた |
| にげる・ポケモンいれかえ | 特殊状態を消す | 持続する効果も消す（別の処理・別のログ） |
| 進化 | 特殊状態・にげるの失敗の記録を消す | 持続する効果も消す（別の処理・別のログ）。ついているトレーナーは受け継ぐ（変えていない） |
| きぜつ | 重なったカードもトラッシュ | 持続する効果の消滅をログに残す（カードではないのでトラッシュには何も置かない） |
| ログ | — | `persistent_effect_added`・`persistent_effect_removed`・`damage_prevented` |
| エラーコード | — | `UNRESOLVED_PREVENTED_COIN_DAMAGE`（`UnsupportedError`） |
| 不変条件 | — | 持続する効果の型・発生源・番・期限・置き場所・重複・ログとの対応（`_persistent_effect_problems`） |
| 状態の書き出し | 形式 1〜7 | 形式 8（場のポケモンごとの `persistent_effects`）。形式 1〜7 は効果があると `ValueError` |
| 効果の登録表 | id `kyuura-engine-0.4a`、ワザ 26 | id `kyuura-engine-0.4b`、ワザ 30（トランセル 2・コクーン 2） |
| カードデータの写し | `pool_v0_4a` まで | `pool_v0_4b`（PMCG1-003・PMCG1-009）。作り直して `--check` で一致 |
| 照合の記録 | 説明文のあるワザは 1 枚に 1 つ | 説明文のあるワザが 2 つあるカードは、`latest_description_ja`・`card_image_text_ja` をワザの位置ごとの辞書にした |
| 版 | `0.4.0a0` | `0.4.0b0` |

コマンドの種類・段階（`Phase`）・決定の種類は増やしていない。`DamageModifier`・ダメージ計算の 8 段階・プラスパワー・ディフェンダーの計算は変えていない。

## 3. PokemonInPlay

```
PokemonInPlay(
    card=トランセルの uid, evolution_stack=(キャタピーの uid,), pokemon_id=12,
    energy=[...], damage=..., trainers=[AttachedTrainer(...)],      # カード
    conditions=SpecialConditions(...),                               # 特殊状態
    retreat_failed_turn=None,                                        # にげるの失敗の記録
    persistent_effects=(PreventDamage(source_card=トランセルの uid, source_player=0, created_turn=5, active_turn=6),),
)
```

- `persistent_effects` は frozen の値のタプル。置きかえるときは新しいタプルを作る（`clone` で共有してよい）。
- 効果を受けているポケモンは、効果を持っている `PokemonInPlay`（ログでは `pokemon_id`）。発生源は `source_card`・`source_player`（受けたポケモンとは別に持つ。相手に与える効果（「すなかけ」など）を加える余地）。

## 4. 持続する効果のデータ構造

| 項目 | 意味 | 指示書 4.1 の概念 |
|---|---|---|
| 持っている `PokemonInPlay` | 効果を受けているポケモン | 効果を受けている Pokémon ID |
| 型（`PreventDamage`。`kind = "prevent_damage"`） | 効果の種類 | 効果の種類 |
| `source_card`・`source_player` | 効果を与えたワザを使ったカード・プレイヤー | 発生源 |
| `created_turn` | 効果を与えた番 | 効果が発生した番 |
| `active_turn` | 効果がはたらく番（次の相手の番）。この番の終わりに消える | 効果が働く期間・終了する条件（期限） |
| （型が決める） | ベンチ・進化・きぜつで消える | 終了する条件（行動） |

期限は「はたらく番」1 つで表した（v0.4b の効果は、はたらく番と消える番が同じ）。はたらく期間と消える時点が違う効果（「すなかけ」のように期限がない効果など）を加えるときは、型ごとに項目を加える。

## 5. AttackEffect

- `PreventDamageOnHeads`: コイン 1 枚。「おもて」なら `PreventDamage(attacker.card, player, turn, turn + 1)` を自分に付ける。ダメージの要素はない（`check` でダメージの目安のあるワザを拒否）。こんらんのコインはエンジンが先に投げる（v0.3c）。
- `CoinFlipDamage.problem`（v0.4b で加えた）: 相手の対戦ポケモンが「ダメージを受けない」状態なら `UNRESOLVED_PREVENTED_COIN_DAMAGE`。エンジンはワザの宣言・こんらんのコインの前にこれを聞く（v0.3c からの順番）。
- ほかの実装（`PoisonOnHeads`・`ParalyzeOnHeads`・`ConfuseOnHeads`・`SelfDamageOnTails`・`PutToSleep`・`DamageOnly`）は変えていない。ダメージの要素の無効は `deal_attack_damage` の中で扱うので、それぞれの実装は効果の要素をいつもどおり処理する。

## 6. DamageModifier を使わない理由

`DamageModifier` は、ダメージ計算の段階で数を加える効果（プラスパワー・ディフェンダー）のための形。「かたまる」は段階で数を変える効果ではなく、「ダメージを受けない」状態で、p.321 はその状態のポケモンへのダメージの要素を無効にすると書く（[persistent-damage-v0.4b.md](persistent-damage-v0.4b.md) 3 章）。そこで、`deal_attack_damage` の最初で状態を確かめ、計算そのものをしない形にした。ログも `damage`（計算した結果）ではなく `damage_prevented` にした。

## 7. 効果の適用・解除とターン進行

```
5 番（持ち主の番）: かたまる → コイン「おもて」→ persistent_effect_added（active_turn 6）→ ワザのあと（きぜつ・サイド）
                    → 番の終わり（ついているトレーナー → 期限が 5 番の持続する効果（なし）→ turn_end）
ポケモンチェック: どくのダメージは受ける（効果ははたらかない。p.323）。どくできぜつしたら効果も消える（knock_out）
6 番（相手の番）: 効果がはたらく。相手のワザのこのポケモンへのダメージの要素は無効（damage_prevented）、効果の要素は有効
                    → 番の終わり（ついているトレーナー（ディフェンダーなど）→ persistent_effect_removed（expired）→ turn_end）
ポケモンチェック: 効果はもうない
7 番（持ち主の番）: 効果はない
```

- 6 番に勝敗が決まったら、番の終わりは来ない。効果は終わった状態に残る（不変条件は終わった状態でも成り立つ）。
- 番は先攻から 1 つずつ交互に進むこと（不変条件）を前提に、「次の相手の番」を番の番号 + 1 で表す（v0.2e のディフェンダーと同じ）。

## 8. 進化・ベンチ・きぜつ

| 契機 | 処理（順番） | ついているトレーナー |
|---|---|---|
| 進化（`_evolve_pokemon`） | `evolve` → 特殊状態（`clear_special_conditions`）→ 持続する効果（`remove_persistent_effects(EVOLVE)`）→ にげるの失敗の記録 | 受け継ぐ（変えない） |
| にげる（成功）（`_retreat`） | `retreat` → 特殊状態 → 持続する効果（`RETREAT`） | いっしょに移る |
| にげる（こんらんで失敗） | 入れ替えないので、どちらも消さない | 変えない |
| ポケモンいれかえ（`SwitchWithBench.resume`） | `switch` → 特殊状態 → 持続する効果（`SWITCH`） | いっしょに移る |
| きぜつ（`_knock_out`） | `knock_out`（カードをトラッシュ）→ 持続する効果（`KNOCK_OUT`。ログだけ） | いっしょにトラッシュ |

場のポケモンの番号（`pokemon_id`）は進化しても変えない（v0.4a の実装上の仮定）が、番号が同じだからといって効果を残さない（p.310 の「別のポケモン」の帰結の 1 つとして消す）。

## 9. 乱数

持続する効果を付ける・消す・ダメージの要素を無効にすることは、乱数を使わない。乱数を使うのは「かたまる」の説明のコイン（`flip_coins`。`source: "attack"`）だけ。こんらん状態でこんらんのコインが「うら」なら「かたまる」のコインは投げない。原典で決められない場合（`UNRESOLVED_PREVENTED_COIN_DAMAGE`）はコインの前に止めるので、拒否された操作は乱数を進めない（`apply_command` は複製した状態で処理する）。

## 10. ログ

| イベント | 項目 | いつ |
|---|---|---|
| `persistent_effect_added` | `player`・`pokemon`・`pokemon_id`・`persistent_effect`（種類）・`source_card`・`source_player`・`active_turn`・`effect`（ワザの `AttackKey`）。`turn` が効果を与えた番 | 「かたまる」の「おもて」 |
| `persistent_effect_removed` | `player`・`pokemon`・`pokemon_id`・`persistent_effect`・`source_card`・`created_turn`・`active_turn`・`reason`（`expired`・`retreat`・`switch`・`evolve`・`knock_out`） | 期限切れ・ベンチ・進化・きぜつ |
| `damage_prevented` | `player`・`pokemon`・`pokemon_id`・`target`・`effect`（ワザ）・`persistent_effect`・`source_card` | 「ダメージを受けない」状態のポケモンへのダメージの要素 |

既存のイベント（`attack`・`damage`・`coin_flip`・`evolve`・`knock_out`・`special_conditions_removed`・`discard_attached_trainer`）の項目と意味は変えていない。持続する効果がなければ、新しいイベントは出ない。`damage_prevented` に防いだ量を書かないのは、p.321 のとおり計算しないから（量が定義されない）。

## 11. 形式 8

形式 7 に、場のポケモンごとの `persistent_effects` を加えた。

```
"persistent_effects": [{"effect": "prevent_damage", "source_card": 31, "source_card_id": "PMCG1-003",
                        "source_player": 0, "created_turn": 5, "active_turn": 6}]
```

- 形式 1〜7 は、持続する効果を受けているポケモンがいると `ValueError`（黙って落とさない）。効果は次の相手の番の終わりに消えるので、その間だけ。
- 効果のない状態は、形式 1〜7 で v0.4a と同じに書き出す。形式 8 は形式 7 に空の `persistent_effects` を加えたもの（テスト `test_without_effects_older_formats_are_unchanged`）。
- 特殊状態・ついているトレーナー・にげるの失敗の記録・進化の重なり・保留中の決定・乱数の指紋は、形式 7 までと同じ項目。
- 状態全体を JSON から読み込む処理は、今回もない。

## 12. 不変条件

`_persistent_effect_problems`（`check_invariants` から、場のポケモンごと）:

- 型: `PERSISTENT_EFFECT_TYPES` の値のタプル。番の項目は整数（bool は不可）
- 置き場所: バトル場のポケモンだけ（ベンチに戻ったら消える）。対戦準備の段階にはない
- 発生源: `PreventDamage` は自分自身に与える効果なので、発生源はこのポケモンのいまのカード・持ち主
- 番: 効果を与えた番は持ち主の番で、いまの姿になった番以後・今の番まで。はたらく番は次の番。期限が過ぎていない（今の番がはたらく番より後、またははたらく番の `turn_end` のあとなら違反）
- 重複: 同じ種類の効果は 1 つまで
- ログとの対応: 同じポケモン・種類・番の `persistent_effect_added` があり、そのあとに `persistent_effect_removed`・`evolve`・`retreat`・`switch`（このポケモンがベンチに戻った）がない

持続する効果はカードではないので、カードの保存則（カードの数・uid の一意性）には数えない。テストで効果を置くときは `build_test_state` の `"prevent_damage"`（効果を与えた番。対応するログも置く）を使う。

## 13. 既存互換性

v0.4a（`99c85d0`）と比べた（scratchpad の比較スクリプト。リポジトリには入れていない）。登録表の id（`effects`）は除いて比べた。

| 比べたもの | 局数・コマンド数 | 結果 |
|---|---|---|
| v0.3d までの既存のデッキ（進化なし。トレーナー・みだれづき・ピカチュウ・どく・ねむり・マヒ・こんらん・自分へのダメージ・プラスパワー・ディフェンダー・止まる局を含む） | 1,340 局（121,420 コマンド。途中の状態も一部すべて比べた） | 終わった状態・ログ・乱数・拒否がすべて同じ |
| でたらめな操作 | 32 局（8,162 コマンド、拒否 4,437） | 同じ |
| 特殊状態 4 種類を混ぜたデッキ | 300 局（44,122 コマンド） | 同じ |
| 進化を使う対戦（パラス → パラセクト・パウワウ → ジュゴン。tests/test_evolution_games_v0_4a.py の 40 局。10 局は途中の状態もすべて） | 40 局（5,964 コマンド） | 終わった状態・途中の状態・ログ・乱数・拒否・保留中の決定（形式 7）がすべて同じ |
| 進化を混ぜたでたらめな操作 | 12 局（4,317 コマンド、拒否 3,171） | 同じ |

v0.1 の参照データ（tests/fixtures/v0_1_reference.json）は変えていない（tests/test_compat_v0_1.py は変更なしで通る）。コマンド・エラーコード（既存のもの）・段階・既存のログの意味・止まる局（HALTED）は変わらない。

v0.4a のテスト 776 件を v0.4b のエンジンで動かすと、7 件が失敗する（どれも登録の内容を固定した値）。v0.4b で次のように直した。

| テスト | 変更 | 理由 |
|---|---|---|
| test_cards.py `test_v0_1_pool_is_ten_basic_pokemon_and_six_basic_energy` | `pool_v0_4b`（トランセル・コクーン）を確かめ、v0.1 の組の数から除く | 対応カードを加えた |
| test_effects.py `test_attacks_with_text_follow_the_verified_latest_description` | 説明文のあるワザに 4 つを加え、照合の記録の辞書（ワザの位置ごと）を読めるようにした | 同じ |
| test_effects.py `test_with_and_without_do_not_change_the_original` | ワザの数 26 → 30 | 同じ |
| test_evolution_games_v0_4a.py `GoldenEvolutionGameTest.test_seed` | 登録表の id を `kyuura-engine-0.4b` に（固定値の digest は同じ） | 登録表の id |
| test_rng_and_serialize.py `test_format_2_adds_only_documented_fields` | 登録表の id | 同じ |
| test_rng_and_serialize.py `test_unknown_format_is_rejected` | 形式 1〜8、知らない形式に 9 | 形式 8 を加えた |
| test_trainers.py `test_default_registry_has_exactly_the_registered_cards` | 登録表の id | 登録表の id |

失敗ではないが、CLAUDE.md の約束（ワザの実装を加えたら `ATTACKS` にも加える）にしたがい、test_effect_preflight_v0_3d.py の `CoinIndependenceTest` に「かたまる」（1 進化なので進化したものとして置き、盤面の番を 2 つずらした）と、「ダメージを受けない」状態の相手の盤面 2 つを加えた（ドードーは `UNRESOLVED_PREVENTED_COIN_DAMAGE`、ほかは今までどおり）。tests/helpers.py に `METAPOD`・`KAKUNA` と、`build_test_state` の `"prevent_damage"` を加えた。

加えたテスト: tests/test_harden_v0_4b.py（42 件）・tests/test_harden_games_v0_4b.py（7 件）。合わせて 776 → 825 件。Python 3.11・3.12・3.13 で通る。

## 14. 将来の 2 進化（v0.4c）への準備

| 事項 | v0.4b の土台 | 2 進化で見直すこと |
|---|---|---|
| 2 進化の規定 | v0.4a の E1〜E20（p.309・p.310・p.316・p.319・p.324） | 1 進化 → 2 進化の重ね方（「○○から進化」が 1 進化の名前）。3 枚の重なり（p.319） |
| 同じ番の再進化の禁止 | `EVOLVED_THIS_TURN`（v0.4a。テスト専用のカードで確かめた） | 実際のカード（キャタピー → トランセル → バタフリーを同じ番にしない） |
| 進化での持続する効果・特殊状態の解除 | v0.4b（`remove_persistent_effects(EVOLVE)`・`clear_special_conditions(EVOLVE)`） | トランセル・コクーンが「かたまる」の効果を受けたまま進化することは、自然な対戦では起こらない（効果は相手の番だけ）。盤面を直接作るテストは v0.4b にある |
| Pokémon ID・HP・ダメージ・エネルギー・ついているトレーナー | v0.4a のまま（番号は変えない、受け継ぐ） | 2 進化の HP がダメージ以下になる場合は `UNRESOLVED_EVOLUTION_HP` のまま（スピアーはコクーンと同じ HP 80、バタフリーはトランセルと同じ HP 70。p.21 の解説も「スピアーに進化してもHPは変わりません」） |
| きぜつ・サイド | 重なったカードをすべてトラッシュ、サイドは 1 枚 | 3 枚の重なり |
| 書き出し | 形式 7・8 の `evolution_stack`（下から順のリスト） | 長さ 2 の重なりはそのまま書ける。不変条件の「1 枚まで」を変える |

バタフリー・スピアー（kyuura `ecb2d694`）:

| カード | kyuura | 本のページ | ワザ | 今の `AttackEffect` で処理できるか |
|---|---|---|---|---|
| スピアー（PMCG1-012。コクーンから進化。LV.32・HP 80・草・弱点 炎・抵抗力 闘 −30・にげる 0） | stage2、ポケモンパワーなし | p.21（ページ画像で見出しと図版を確かめた。照合は v0.4c で 300dpi で行う） | ダブルニードル（無無無）30×「コインを2枚投げて「おもて」の出た数×30のダメージ。」、どくばり（草草草）40「コインを投げて「おもて」なら、相手を「どく」状態にする。」 | ダブルニードルは `CoinFlipDamage(coins=2, damage_per_heads=30)`、どくばりは `PoisonOnHeads` で処理できる見込み（最新の説明を照合してから）。ダブルニードルを「ダメージを受けない」ポケモンに使うと `UNRESOLVED_PREVENTED_COIN_DAMAGE` |
| バタフリー（PMCG2-007。トランセルから進化。LV.28・HP 70・草・弱点 炎・抵抗力 闘 −30・にげる 0） | stage2、ポケモンパワーなし | p.19（同じ） | ふきとばし（無無）20「相手を控えポケモンと入れ替える。入れ替わるポケモンは、相手が選ぶ。（相手に控えがいないとき、入れ替えはおこらない）」、メガドレイン（草草草草）40「相手にダメージを与えたら、その半分（切り上げ）のダメージカウンターを、自分からとりのぞく。」 | **できない**。ふきとばし（相手の入れ替え・相手が選ぶ決定・入れ替わった相手の特殊状態と持続する効果の解除）、メガドレイン（与えたダメージによる回復。「ダメージを受けない」相手なら与えていないので回復しないと読めるが、照合が要る） |

推奨: v0.4c は、ビードル → コクーン → スピアーの 2 進化だけを、スピアーのページ（p.21）を 300dpi で照合してから実装する。バタフリーは、ふきとばし・メガドレインの原典照合と実装（相手の入れ替え・与えたダメージによる回復）が要るので、別の段階にする。

（v0.4c 注: この推奨どおり、v0.4c でスピアーを p.21 と照合し、ダブルニードルを `CoinFlipDamage(coins=2, damage_per_heads=30)`、どくばりを `PoisonOnHeads` として登録した。最新の説明は、ダブルニードルが書き方だけ違い（内容は同じ）、どくばりはビードルと同じ。バタフリーは実装していない。[architecture-v0.4c.md](architecture-v0.4c.md) 14 章に v0.4d の準備）

## 15. 設計上のトレードオフ

- 期限を「はたらく番」1 つで表したので、型を加えるたびに期限の表し方を見直す必要がある（汎用の期限の仕組みは作らなかった）。
- 不変条件のログとの対応は、効果ごとにログをさかのぼって探す。効果は 1〜2 番の間しか残らないので、さかのぼる長さは短い。
- 「ダメージを受けない」状態でダメージを計算しないので、防いだ量はログにない。量が要る効果（「ダメージを与えたら」など）を加えるときは、原典で量の扱いを確かめる。
- 効果を与えた番に効果を受けたポケモンが動く場面（ベンチに戻る・進化する）は自然な対戦では起こらないので、盤面を直接作るテストだけで確かめている。
