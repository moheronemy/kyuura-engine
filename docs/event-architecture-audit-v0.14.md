# 現行アーキテクチャの分析（v0.14 Phase A）

v0.14 は、カード効果ごとの専用の処理を、汎用的なイベント・効果の解決の仕組みに移すのが適切かを確かめる版です。この文書は、その前提として、v0.13（`8facf3a`。ブランチ `claude/v0.13-shell-attack`）のコードを読んで確かめた処理の流れと、技術的な負債をまとめたものです。

- 行番号はすべて `8facf3a` のものです（v0.14 では `kyuura_engine/` を変えていない）。
- 「確認した事実」はコードを読んで・実行して確かめたこと、「評価」はそこからの判断です。区別して書きます。
- 版ごとの変更の数は、`git` の差分から、docstring とコメントを除いた AST が変わった関数・メソッドを数えました（スクリプトは [event-prototype-verification-v0.14.md](event-prototype-verification-v0.14.md) 7 章）。docstring だけの変更は数えていません。

関連する文書: [event-architecture-options-v0.14.md](event-architecture-options-v0.14.md)（設計案の比較）・[event-model-v0.14.md](event-model-v0.14.md)（イベントモデル）・[event-prototype-verification-v0.14.md](event-prototype-verification-v0.14.md)（検証）・[event-migration-plan-v0.14.md](event-migration-plan-v0.14.md)（移行計画）。

## 1. コマンドの処理（A1）

### 1.1 `apply_command` の流れ（確認した事実）

| 順番 | 処理 | 場所 |
|---|---|---|
| 1 | 未対応のコマンドの型（`UNSUPPORTED_COMMANDS`）・知らない型を拒否 | engine.py:253-257 |
| 2 | コマンドの項目の型（`check_command_fields`） | engine.py:258 |
| 3 | 終わった対戦（`GAME_OVER`・`SUDDEN_DEATH`・`HALTED`）を拒否 | engine.py:259-264 |
| 4 | 状態を複製（`GameState.clone`） | engine.py:265、state.py:499 |
| 5 | コマンドの型ごとの処理（`_HANDLERS`。14 種類） | engine.py:266、1606-1621 |
| 6 | 返す状態の不変条件（`check_invariants`）。破れていれば `StateIntegrityError` | engine.py:267、1627 |

### 1.2 複製と原子性（確認した事実）

- `GameState.clone`（state.py:499）は、変わる部分（プレイヤーのゾーンのリスト・場のポケモン・乱数）を複製し、変わらない部分（カードの定義・uid とカードの対応・ログの各要素（`MappingProxyType`）・効果の登録表）を共有する。ログはタプルで、`add_event` が新しいタプルを作る（state.py:559）。
- 処理の途中で例外が起きても、渡した状態は変わらない（複製の上で処理する）。そのため、効果の実装は「状態を変える前に確かめる」ことと「処理の途中で `UnsupportedError` を投げてもよい」ことの両方が成り立つ（例: `ParalyzeOnHeads.resolve` はダメージのあとで `paralysis_problem` を投げる。effects.py:1502-1504）。
- 拒否で乱数が進まないことは、乱数の状態も複製するので構造的に保証される。ただし「受け付けるか」がコインの結果で変わらないこと（コインの前に止める）は、各効果の実装が個別に守っている（4.5 節）。

### 1.3 合法性の確認（確認した事実）

- コマンドごとの `_require_phase`・`_require_turn`・`_require_in_hand`（engine.py:278-300）と、ワザ・にげるの `_require_not_asleep_or_paralyzed`（engine.py:976）。
- 効果ごとの確認: ワザは `AttackEffect.problem`（宣言の前。effects.py:193）、トレーナーは `TrainerEffect.check_playable`、パワーは `PowerEffect.check_usable`（effects.py:2905）。
- 登録の確認: `EffectRegistry.attack_effect`・`trainer_effect`・`power_effect`（effects.py:3500・3537・3572）は、登録がない・データ（名前・文面）と合わないなら None を返し、エンジンが `UNSUPPORTED_…` にする。

### 1.4 効果の登録・検索・実行（確認した事実）

- 識別子は `AttackKey`（カード id, ワザの位置）・トレーナーのカード id・`PowerKey`（カード id, パワーの位置）。登録表 `EffectRegistry`（effects.py:3450）は変えられない値で、`GameState.effects` で対戦ごとに持つ。
- 実行: ワザは `AttackEffect.resolve`／`resume`、トレーナーは `TrainerEffect.resolve`／`resume`、宣言するパワーは `PowerEffect.resolve`。自動的にはたらく・常にはたらくパワーは `resolve` を持たず、エンジンの決まった場所が実装の型（`isinstance`）で探して使う（4.1 節）。

### 1.5 ワザ・トレーナー・ポケモンパワーの違い（確認した事実）

| | ワザ | トレーナー | 宣言するパワー |
|---|---|---|---|
| 入口 | `_use_attack`（engine.py:832） | `_play_trainer`（engine.py:1389） | `_use_pokemon_power`（engine.py:1454） |
| 宣言の前の確認 | 番・ワザの位置・ねむり・マヒ・登録・エネルギー・`effect.problem`・こんらんのダメージの変更効果・C18・G37・W24（engine.py:867-891） | 番・手札・登録・`check_playable` | 番・場のポケモン・登録・`POWER_NOT_DECLARABLE`・`POWER_SUPPRESSED`・`check_usable` |
| 乱数 | こんらんのコイン・ワザのコイン・「とうめい」のコイン | 山札を切る（マサキは引くだけ） | なし（v0.5〜v0.13 のパワー） |
| 決定 | ワザの途中（`resume="attack"`）・きぜつの前（`knock_out`）・きぜつのあと（`take_prize`・`post_knockout`・`promote_active`） | トレーナーの途中（`resume="trainer"`） | 出さない（出したら `RuntimeError`。engine.py:1520-1521） |
| 後処理 | `_finish_attack`（きぜつ → サイド → 勝ち負け → ふしちょう → 交代 → 番の終わり） | `_finish_trainer`（トラッシュして `MAIN` にもどる） | なし（番は続く） |

## 2. イベントに相当する処理（A2）

v0.13 には「イベント」という仕組みはありません。下の表は、汎用のイベントに相当する出来事が、今どの関数で起こるかです。「乱数」は乱数を使うか、「ログ」は残る公開のログのイベントです。

| 出来事 | 処理する関数 | 入力 | 出力・状態の変化 | 乱数 | ログ |
|---|---|---|---|---|---|
| ワザの宣言 | `_use_attack`（engine.py:893） | `UseAttack` | なし（宣言の記録だけ） | なし | `attack` |
| コイントス | `coins.flip_coins`（coins.py） | 投げるプレイヤー・枚数・理由（`source`）・効果 | 結果（`CoinFlips`） | 1 枚 1 回 `getrandbits(1)` | `coin_flip`（1 枚ごと） |
| ダメージ計算の開始 | `effects.deal_attack_damage`（effects.py:510） | `AttackUse`・受けるポケモンの種類（相手のバトル場・自分）・基本となるダメージ | — | — | — |
| ダメージの防止 | 同じ関数の最初（effects.py:570-582。`persistent.damage_prevention`） | 受けるポケモンの持続する効果 | 要素は無効（計算しない） | なし | `damage_prevented` |
| ダメージの修正 | `attack_damage_modifiers`（effects.py:2472）＋ `damage.calculate_attack_damage`（p.321 の 8 段階） | ついているトレーナー（プラスパワー 5 段階・ディフェンダー 7 段階）・弱点・抵抗力 | 最終ダメージ | なし | （`damage` の `steps`・`modifiers`） |
| ダメージを受ける前の評価（「とうめい」） | `effects.attack_reaches`（effects.py:693。effects.py:586 から） | 最終ダメージ > 0、受けるポケモンの「とうめい」 | 受けない（`DamageResult.evaded`） | 1 匹 1 回のコイン | `evade_check`・`attack_evaded` |
| ダメージの適用 | 同じ関数（effects.py:605） | 最終ダメージ | `receiver.damage += final` | なし | `damage` |
| ダメージを受けたときの記録 | 同じ関数（effects.py:591-604・629-637） | 受けたときの特殊状態・ガス・持続する効果 | `AttackUse.counterattacks`・`ko_prevention_able`・`retaliations` に加える | なし | なし |
| ダメージの処理の完了 | `effects.finish_damage_elements`（effects.py:847） | `AttackUse` の記録 | 「はんげき」（effects.py:890）・「ほのおのかべ」「こうらがえし」（effects.py:1047）を与える | 「とうめい」のコイン（返すダメージを受けるゴースト） | `counterattack`・`retaliation`・`damage`（`retaliation`）など |
| 特殊状態の付与 | `conditions.poison`・`put_to_sleep`・`paralyze`・`confuse`（conditions.py:70-153）。直前に `attack_reaches` | 受けるポケモン | `PokemonInPlay.conditions` | なし（ワザのコインは別） | `special_condition` |
| きぜつの候補の判定 | `_ko_prevention_offer`（engine.py:1014）・`_knock_out_after_attack`（engine.py:1099）・`_pokemon_check`（engine.py:517） | 場のポケモンのダメージと HP | 候補（状態に持たない） | なし | なし |
| きぜつの防止 | `_resume_knock_out`（engine.py:1058）→ `PreventKnockOutOnHeads.prevent`（effects.py:3339） | 決定 `KO_PREVENTION` の答え | ダメージを HP − 10 | コイン 1 枚 | `ko_prevention_declined`・`_declared`・`ko_prevented`・`_failed` |
| きぜつの処理 | `_knock_out`（engine.py:1159） | きぜつするポケモン | トラッシュ・持続する効果の消去 | なし | `knock_out`・`persistent_effect_removed` |
| きぜつのあとの効果の候補 | `_post_knockout_candidates`（engine.py:1113。トラッシュの前に求める） | きぜつするポケモン | 候補（決定の `context` で運ぶ） | なし | なし |
| サイドの取得 | `_after_knockouts`（engine.py:1193）→ `_next_prize_or_judge`（1245）→ 決定 `TAKE_PRIZE` → `_resume_take_prize`（1348） | きぜつの数 | 手札 | なし | `take_prize` |
| 勝ち負けの判定 | `_next_prize_or_judge`（engine.py:1258。`judge.decide`） | サイド・バトル場 | 結果 | なし | `game_end` |
| きぜつのあとの効果（「ふしちょう」） | `_offer_post_knockout`（engine.py:1282）→ `_resume_post_knockout`（1305） | 候補 | トラッシュ → 手札 | なし | `post_knockout_power_*`・`return_to_hand` |
| バトル場への補充 | `_promotions_after_judge`（engine.py:1271）→ 決定 `PROMOTE_ACTIVE` → `_resume_promote_active`（1360） | ベンチ | バトル場 | なし | `promote_active` |
| 番の終了 | `_end_turn`（engine.py:406） | — | ついているトレーナーのトラッシュ・持続する効果の失効・にげるの失敗の記録の消去 | なし | `discard_attached_trainer`・`persistent_effect_removed`・`turn_end` |
| 持続する効果の失効 | `persistent.remove_expired_persistent_effects`（persistent.py:90。engine.py:425 から） | `active_turn` が今の番 | 効果を消す | なし | `persistent_effect_removed`（`expired`） |
| ポケモンチェック | `_pokemon_check`（engine.py:454）・`_pokemon_check_sleep_and_paralysis`（534） | 特殊状態 | どくのダメージ・きぜつ・ねむり・マヒの回復・次の番 | ねむりのコイン | `pokemon_check`・`poison_damage`・`sleep_check` など |

評価: 出来事の境界はすでに関数としてはっきり分かれていて、ログもそれぞれの境界で出ている。ないのは「その境界ではたらく効果を、登録された効果の一覧から探す」共通の仕組みで、効果の種類ごとに境界のコードの中で直接探している（4.1 節）。

## 3. カード効果ごとの専用の処理（A3）

| 効果 | 発動の判定 | 条件の評価 | 実行 | 順番の管理 | 中断・再開 | 宣言の前に止める確認 | 不変条件の例外 |
|---|---|---|---|---|---|---|---|
| ゴースト「とうめい」（v0.9） | `deal_attack_damage`（effects.py:586）と、効果を与える 9 種類のワザの実装が `attack_reaches` を直接呼ぶ | `evasion_power`（effects.py:664。`isinstance(effect, AttackImmunityOnHeads)`・`is_working`・`suppressors_of`） | `attack_reaches`（コイン・記録・ログ） | 1 つのワザで 1 匹 1 回（`AttackUse.reception`） | 決定の前に決める（`reception` は決定をまたがない） | `evaded_effect_coin_problem`（T19b。3 つの実装の `problem`） | なし |
| カイリキー「はんげき」（v0.10） | `deal_attack_damage`（effects.py:592-596・629-633） | `counterattack_power`（effects.py:806） | `_apply_counterattack`（effects.py:890） | `finish_damage_elements`（effects.py:847）を、11 か所（ワザの実装 10・`_apply_retaliation` 1）とエンジン 2 か所で呼ぶ | 決定の前に与える（`push_attack_decision` が確かめる。decisions.py:141-145） | `counterattack_double_knockout_problem`（C18。effects.py:951）＋ 10 の `damage_profile` | `_counter_knocked_out_attacker_awaiting`（engine.py:2080） |
| サカキのカイリキー「こんじょう」（v0.11） | ダメージを受けたときに `ko_prevention_able` を記録（effects.py:599-601）。きぜつの判定で `_ko_prevention_offer`（engine.py:1014） | `ko_prevention_power`（effects.py:1201）・`is_able`・`ko_prevention_suppressors` | `_resume_knock_out`（engine.py:1058）→ `prevent` | `_ko_prevention_offer` が 2 匹以上なら `RuntimeError`（engine.py:1051-1054） | 決定 `KO_PREVENTION`（`resume="knock_out"`） | `ko_prevention_attack_effect_problem`（G37。effects.py:1236）＋ 9 の `opponent_effect_elements` | `_ko_prevention_awaiting`（engine.py:2107）・`_ko_prevention_decision_problems`（2134） |
| R団のファイヤー「ふしちょう」（v0.12） | `_post_knockout_candidates`（engine.py:1113）を `_knock_out_after_attack`・`_pokemon_check` の 2 か所から | `post_knockout_power`（effects.py:3417）・`is_able`・`suppressors_of` | `_resume_post_knockout`（engine.py:1305）→ `recover` | 候補が 2 つ以上なら `RuntimeError`（engine.py:1151-1155）。勝ち負けの判定のあとに正規化 | 候補を `TAKE_PRIZE` の決定の `context`（`"post_knockout"`）で運び、`POST_KNOCKOUT_POWER`（`resume="post_knockout"`） | （W24・ポケモンチェックの両方のきぜつが先に止める） | `_post_knockout_candidate_problems`・`_post_knockout_decision_problems`（engine.py:2202-2284） |
| R団のファイヤー「ほのおのかべ」（v0.12） | `deal_attack_damage`（effects.py:603-604・634-637） | `persistent.retaliation`（persistent.py:115） | `_apply_retaliation`（effects.py:1047） | `finish_damage_elements` | なし（決定の前に与える） | `retaliation_double_knockout_problem`（W24。effects.py:1136） | `_counter_knocked_out_attacker_awaiting`（「ほのおのかべ」の分。engine.py:2101-2103） |
| わるいカメール「こうらがえし」（v0.13） | 同上（受けたダメージを `PendingRetaliation.received` に記録） | 同上（`Retaliation.basis`） | 同上（`base_damage`） | 同上 | 同上 | 同上（S37 = W24） | 同上・`_retaliation_problems`（engine.py:2010） |
| ベトベトン「かがくへんかガス」（v0.8） | 発動しない（常にはたらく。状態から求める） | `continuous.suppressors_of`（continuous.py:51） | — | — | — | — | — |

### 3.1 共通にできる処理と、ルールの意味を守るために専用が必要な部分（評価）

| 共通にできる（同じことを効果ごとに書いている） | ルールの意味を守るために専用が必要 |
|---|---|
| 効果の持ち主を探す（いちばん上のカードのパワーを `isinstance` で探す。5 か所: effects.py:664・806・1201・3417、continuous.py:29） | 「とうめい」のコインは 1 つのワザで 1 匹 1 回（T4）。「はんげき」は乱数なし。「こんじょう」はコイン・残り HP 10（効果の中身） |
| 特殊状態でのはたらき（`is_working`・`is_able` の本体はどれも「ねむり・マヒ・こんらんでない」。effects.py:3198・3236・3280・3323・3392） | 「はたらく」（自動）と「使える」（任意・決定）の区別（p.311・p.323） |
| かがくへんかガスでの抑止（`suppressors_of` を 5 か所から聞く） | かがくへんかガスどうしは消し合わない（名前で除く） |
| 「相手のワザによるダメージを受けたとき」の判定（`deal_attack_damage` の中で 3 つの効果が同じ条件 `receiver_player != use.player and calc.final > 0` を書く。effects.py:592・603） | 「はんげき」の 10 は特殊能力のダメージ（`deal_attack_damage` を通さない）、「ほのおのかべ」「こうらがえし」はワザによるダメージ（通す）。返すダメージの量（固定・受けたダメージ） |
| ダメージの処理の終わりで与える（`finish_damage_elements`） | 時点は p.89（ダメージの処理のあと、ダメージ以外の効果の前） |
| 2 つ以上はたらいたら止める（3 か所: effects.py:879-883、engine.py:1051-1054・1151-1155） | 順番が原典で決まらない（C34/C35・G40・P32）ので、仕組みが順番を決めてはいけない |
| 両方がきぜつしうるなら宣言の前に止める（C18・W24 が同じ形の判定を別々に書く。effects.py:951・1136） | どの組み合わせが「同時のきぜつ」か決められないか（p.324）は、ダメージの分類（ワザ・特殊能力・前の番の効果）で決まる |

## 4. 技術的負債（A4）

### 4.1 効果の種類に応じた分岐（確認した事実）

- 自動的にはたらく・常にはたらく・決められたときに使うパワーは、エンジンが実装の型で探す: `isinstance(effect, AttackImmunityOnHeads)`（effects.py:677）、`CounterattackDamage`（820）、`PreventKnockOutOnHeads`（1208）、`ReturnToHandOnKnockOut`（3424、engine.py:2240）、`SuppressOtherPowers`（continuous.py:35）。持続する効果は `isinstance(effect, PreventDamage)`・`Retaliation`（persistent.py:110・126、engine.py:2004、serialize.py:120・128）。
- 種類が 1 つ増えるたびに、探す関数・`is_working`／`is_able`・公開の問い合わせ（`working_evasion_power`・`working_counterattack_power`・`available_ko_prevention_power`）を 1 組ずつ加えてきた。

### 4.2 複数の箇所に分かれた発動条件（確認した事実）

- 「相手のワザのダメージ（最終ダメージ > 0）を受けた」という同じ条件が、`deal_attack_damage` の中で「はんげき」（effects.py:592）・「こんじょう」の記録（599）・「ほのおのかべ」「こうらがえし」（603）に別々に書かれている。
- 「とうめい」の評価（`attack_reaches`）は、ダメージ（`deal_attack_damage`）と、効果を与える 9 種類のワザの実装（effects.py:1372・1414・1448・1509・1572・1604・1635・1688・1930）が別々に呼ぶ。呼び忘れは静かに見落とす（検出はテストだけ）。
- 「ダメージの処理の完了」（`finish_damage_elements`）は、ダメージ以外の効果を持つワザの実装 10 種類と `_apply_retaliation`、エンジン 2 か所（engine.py:904・1381）の、合わせて 13 か所で呼ぶ。呼び忘れは `_require_damage_elements_finished`（effects.py:836）・`push_attack_decision`（decisions.py:141-145）が `RuntimeError` で止める（動的な確認。構造では防げない）。

### 4.3 同じ概念の重複した実装（確認した事実）

- 「効果の対象（相手の対戦ポケモン）がこのワザのダメージできぜつした」の判定が 2 通りある: 今のダメージで比べる（`target.damage >= hp`。effects.py:1366・1499・1682）と、ダメージの要素の結果で見る（`result.knocked_out`。1410・1444・1572・1923）。`finish_damage_elements` のあとで相手のダメージが変わるのは、「ほのおのかべ」のダメージを受けたワザを使ったポケモンの「はんげき」が相手（効果を持つポケモン）にダメージを与えるときだけ。今の対応カードでは、「はんげき」を持つカイリキーのワザ（ちきゅうなげ）に効果がないので起こらない（評価: 今は同じ答えだが、同じ規定（p.309「処理の対象がなくなってしまっている場合」）の 2 通りの実装）。
- 「2 つ以上はたらいたら止める」・「両方がきぜつしうるなら止める」の判定は、効果の組み合わせごとに別の関数（3.1 節）。
- 「ねむり・マヒ・こんらんでない」の判定が 5 つのクラスで同じ本体（3.1 節）。

### 4.4 特定のカードの追加で変更が必要になった共通の関数（確認した事実）

版ごとに、コード（docstring を除く）が変わった関数・メソッドの数と、そのうち共通の処理（特定のカードのものではない関数）:

| 版 | 加えた効果 | 変わった関数・メソッド（加えたものを除く） | うち共通の処理 |
|---|---|---|---|
| v0.8 | かがくへんかガス | 6 | `_use_pokemon_power`・`PowerEffect` |
| v0.9 | とうめい | 16 | `deal_attack_damage`・`AttackUse`・`DamageResult`・ほかのカードのワザの `resolve` 7 つ |
| v0.10 | はんげき | 22 | `deal_attack_damage`・`attack_reaches`・`AttackUse`・`push_attack_decision`・`_use_attack`・`_resume_attack`・`check_invariants`・ほかのカードのワザの `resolve` 10 |
| v0.11 | こんじょう | 26 | `deal_attack_damage`・`AttackUse`・`AttackEffect`・`DamageProfile`・`counterattack_double_knockout_problem`・`_use_attack`・`_finish_attack`・`_resume_attack`・`_decision_problems`・`_RESUMERS`・`check_invariants`・`state_to_dict`・ほかのカードのワザのクラス 9（`opponent_effect_elements`） |
| v0.12 | ふしちょう・ほのおのかべ | 29 | `deal_attack_damage`・`finish_damage_elements`・`_require_damage_elements_finished`・`AttackUse`・`push_attack_decision`・`_use_attack`・`_knock_out_after_attack`・`_after_knockouts`・`_next_prize_or_judge`・`_resume_take_prize`・`_pokemon_check`・`_ko_prevention_offer`・`_RESUMERS`・`_decision_problems`・`_persistent_effect_problems`・`check_invariants`・`add_persistent_effect`・`remove_persistent_effects`・`PokemonInPlay`・`state_to_dict` |
| v0.13 | こうらがえし | 11 | `deal_attack_damage`・`_apply_retaliation`・`PendingRetaliation`・`retaliation_double_knockout_problem`・`_retaliation_problems`・`Retaliation` |

- `deal_attack_damage` は v0.9 から v0.13 まで 5 つの版すべてで変わった。`AttackUse` は v0.9〜v0.12 の 4 つの版で、ワザ 1 回の中だけの記録の項目が 1 つずつ増えた（`reception`・`counterattacks`・`ko_prevention_able`・`retaliations`）。
- 自動的にはたらく効果を 1 種類加えるたびに、その効果と関係のないカードのワザの実装を書きかえた（v0.9 で 7、v0.10 で 10、v0.11 で 9 のクラス）。
- `_use_attack` の宣言の前の確認は、v0.10・v0.11・v0.12 で 1 つずつ増えた（C18・G37・W24。engine.py:885-889）。

評価: 「効果を 1 種類加えると、ダメージの適用・ワザの実装・宣言の前の確認・不変条件の 4 か所が同時に変わる」形が、v0.9 から 5 つの版で続いている。v0.13 は v0.12 の仕組み（`Retaliation`）の延長だったので小さく済んだ。

### 4.5 宣言の前に止める確認（原典で決められない場合）の構造（確認した事実）

- 止める確認は 5 つの関数（`effect.problem`・`_confusion_damage_problem`・C18・G37・W24）で、順番は `_use_attack` が固定する（engine.py:881-891）。
- C18・G37・W24 は、ワザの実装が宣言する補助の情報（`damage_profile`（10 の上書き）・`opponent_effect_elements`（9 の宣言）・`DamageProfile.outcomes`）に頼る。宣言を忘れると、止めるべき場合を見落とす（`damage_profile` は「×」「+」「−」のあるワザで上書きしないと `NotImplementedError` になるが、自分へのダメージ・効果の要素の宣言忘れは静かに見落とす。tests/test_guts_v0_11.py が実装の `attack_reaches` の呼び出しと照らして検出する）。
- 評価: 止める確認は「ワザの処理を、コインのすべての結果で、状態を変えずに先読みする」ことを、組み合わせごとに手で書いたものになっている。組み合わせが増えると、確認の関数と補助の情報が掛け算で増える。

### 4.6 `PendingDecision` による中断・再開の限界（確認した事実）

- 決定は一度に 1 つ（`GameState.decision`）。再開先は名前（6 種類。engine.py:1527-1534）で、続きの情報は `context`（名前と値の組。型の決まりはなく、種類ごとの不変条件が形を確かめる）。
- ワザ 1 回の中だけの記録（`AttackUse` の 4 項目）は、決定をまたぐと失われる（`_resume_attack` が新しい `AttackUse` を作る。engine.py:1378）。そのため:
  - 「はんげき」「ほのおのかべ」は決定の前に与え終える必要がある（`push_attack_decision` が `RuntimeError`）。
  - 「こんじょう」の記録が要る場面で決定をまたいでいたら `RuntimeError`（engine.py:1045-1047）。
  - 「とうめい」の結果を決定のあとで使うワザは、結果を `context` に持つ必要がある（docs/automatic-powers-v0.9.md 3 章）。
- きぜつのあとの流れ（サイド → 勝ち負け → ふしちょう → 交代 → 番の終わり／ポケモンチェックの続き）は、再開先の関数が次の関数を呼ぶ連鎖で、続きの情報（`"remaining"`・`"then"`・`"post_knockout"`）を決定の `context` で受け渡す（engine.py:1245-1366）。新しい段階を加えるには、この連鎖のどこに入れるかを決め、`context` の項目と不変条件を加える（v0.12 の「ふしちょう」は 4 つの関数と 2 つの不変条件を変えた）。
- 評価: 保存・復元の形式を変えずに済んでいる（形式 9 のまま）という大きな長所がある。一方で、続きの情報がコールスタックと `context` に分かれていて、決定をまたいで残る情報と失われる情報を、効果ごとに考える必要がある。

### 4.7 不変条件の例外（確認した事実）

- 「場のポケモンのダメージは HP 未満」の例外が 2 つ（`_counter_knocked_out_attacker_awaiting`・`_ko_prevention_awaiting`）あり、どちらも今の番のログを読んで確かめる（engine.py:2080-2131）。v0.12 で「ほのおのかべ」のぶんを広げた。
- 評価: 例外はどれも「ワザの要素を処理し終えたが、きぜつの処理の前に決定を待つ」という同じ状況を、効果ごとに許している。

### 4.8 新しい効果を加えるときの変更の範囲（評価）

v0.9〜v0.13 の実際の変更から、ダメージ・きぜつに関わる自動的・任意の効果を 1 種類加えるときに変わってきた場所:

1. 効果の実装（`PowerEffect` のクラス）と登録。
2. 境界の関数（`deal_attack_damage`・`finish_damage_elements`・`_finish_attack` など）に、その効果を探して使うコード。
3. `AttackUse` に、ワザ 1 回の中の記録の項目。
4. 関係のないワザの実装（効果の前の呼び出し・宣言）。
5. 宣言の前に止める確認の関数と、`_use_attack` の呼び出し。
6. 決定の種類・再開先・`context`・不変条件と例外。
7. ログの監査（tests/log_audit.py）の組み立て直し。
8. ストレス実行の観察（tools/stress_engine.py の `_observe_…`）。

このうち 1・7・8 は、どの設計でも要る（効果の中身と検証）。2〜6 が、汎用の仕組みで減らせるかを確かめる対象です。

## 5. 重大度（評価）

| 問題 | 重大度 | 理由 |
|---|---|---|
| `deal_attack_damage` に効果ごとの判定が集まる（4.2・4.4） | 高 | 5 つの版で続けて変わった。ここを誤ると、すべてのワザのダメージに影響する |
| 宣言の前に止める確認が組み合わせごとの手書き（4.5） | 高 | 未解決の裁定を守る仕組みが、補助の情報の宣言忘れで静かに外れうる |
| ダメージの処理の完了を各ワザの実装が呼ぶ（4.2） | 中 | 呼び忘れは `RuntimeError` で見つかる（静かには壊れない）が、効果のあるワザを加えるたびに要る |
| 「とうめい」の評価を各ワザの実装が呼ぶ（4.2） | 中 | 呼び忘れは静かに見落とす（テストで検出） |
| 効果の型での分岐・重複（4.1・4.3） | 低〜中 | 動きは正しいが、種類が増えるたびに同じ形の関数が増える |
| 同じ規定の 2 通りの実装（4.3。きぜつした対象） | 低 | 今の対応カードでは同じ答え。将来のカードで食い違いうる |
| 決定をまたいで失われる記録（4.6） | 中 | 今は `RuntimeError` で守っているが、決定のあとに記録を使う効果を加えるときに設計が要る |
| 不変条件の例外がログを読む（4.7） | 低 | 確認の仕組みで、ルールの判断ではない |

## 6. まとめ

- 確認した事実: 出来事の境界は関数として分かれていて、ログ・乱数・保存の形式は安定している。効果を探して使うコードが境界の中に直接書かれていて、効果の種類を加えるたびに、境界の関数・関係のないワザの実装・宣言の前の確認・不変条件が同時に変わってきた。
- 評価: 変わりやすいのは「どの効果がいつはたらき、どの順番で処理されるか」（発動の判定・順番・止める確認）で、「効果の中身」（コイン・ダメージの量・特殊状態）ではない。v0.14 のプロトタイプは、この「発動の判定・順番・止める確認」を共通の仕組みが管理できるかを確かめる。
