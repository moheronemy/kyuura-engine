# アーキテクチャ（v0.4d）: ワザの途中の相手の決定と、与えたダメージの受け渡し

v0.4d は、バタフリー（PMCG2-007。トランセルから進化する 2 進化ポケモン）の 2 つのワザを扱うために、(A) ワザの途中で相手プレイヤーの決定を待ち、そのあとで同じワザの処理を再開すること、(B) ワザが与えたダメージを正確に把握し、その量に応じた後の要素を処理すること、を加えた版です。原典照合は [butterfree-v0.4d.md](butterfree-v0.4d.md)（カード）・[forced-switch-v0.4d.md](forced-switch-v0.4d.md)（ふきとばし）・[damage-drain-v0.4d.md](damage-drain-v0.4d.md)（メガドレイン）にあります。

## 1. 方針

- v0.2a からあるワザの途中の決定（`push_attack_decision`・`resume="attack"`・`_resume_attack`）を、そのまま相手プレイヤーの決定にも使う。新しいコマンド・段階（`Phase`）・状態の項目・書き出しの形式は加えない。
- ダメージの結果は、`deal_attack_damage` が返す小さな値（`DamageResult`）で後の要素に渡す。ログを読み直さない。巨大な効果の DSL・新しいイベントの仕組みは作らない。
- 番の終わり・きぜつの判定・サイド・交代・ポケモンチェックは、既存の共通の処理（`_finish_attack`・`_after_knockouts`・`_end_turn`）だけで行う。ワザの実装に重ねて書かない。
- 原典で決められない場合は止める方針（`UNRESOLVED_…`）のまま。v0.4d の 2 つのワザには、原典の記述から決まらない盤面はなかった（新しい `UNRESOLVED_…` はない）。
- バタフリーを使わない対戦は、v0.4c と同じ結果・ログ・乱数にする（14 章）。

## 2. v0.4c からの変更

| 項目 | v0.4c | v0.4d |
|---|---|---|
| `AttackEffect` | `check`・`problem`・`resolve`・`resume` | `decision_problems`（このワザが出した決定を待つ状態の、効果ごとの不変条件。既定は「決定するのはワザを使ったプレイヤー」）を加えた |
| ワザの実装 | 8 種類 | 10 種類: `DamageAndForceSwitch`（ふきとばし）・`DamageAndDrain`（メガドレイン）を加えた |
| `deal_attack_damage`・`damage_opponent_active` | 戻り値なし | `DamageResult` を返す（ログ・ダメージの値・計算・乱数は同じ） |
| 決定の種類 | `take_prize`・`promote_active`・`select_pokemon` | `forced_switch`（`decisions.FORCED_SWITCH`。ワザを使われた側が決定する。段階は `Phase.DECISION`） |
| 特殊状態・持続する効果が消える理由 | `retreat`・`switch`・… | `forced_switch`（`conditions.FORCED_SWITCH`・`persistent.REMOVAL_REASONS`）を加えた |
| ログ | — | `forced_switch`・`forced_switch_skipped`・`drain_heal` を加えた。既存のイベントの形は変えていない |
| 不変条件 | ワザの決定は続きの情報と登録だけ | ワザの決定の共通の確認（番のプレイヤー・バトル場のポケモン・カード id・今の番のワザのログ）と、効果ごとの `decision_problems`。持続する効果のログとの対応に `forced_switch` を加えた |
| 状態の書き出し | 形式 1〜8 | 同じ（形式 9 は加えていない）。形式 1 は、ワザの途中の決定があると `ValueError`（黙って落とさない） |
| 効果の登録表 | id `kyuura-engine-0.4c`、ワザ 32 | id `kyuura-engine-0.4d`、ワザ 34（バタフリー 2） |
| カードデータの写し | `pool_v0_4c` まで | `pool_v0_4d`（PMCG2-007）。作り直して `--check` で一致。`cards.POOL_KEYS` に加えた |
| 照合の記録 | — | PMCG2-007（p.19。ワザの位置ごとの辞書） |
| 版 | `0.4.0c0` | `0.4.0d0` |

コマンドの種類・段階（`Phase`）・状態（`GameState`・`PokemonInPlay`・`PendingDecision`）の項目・エラーコードは増やしていません。

## 3. AttackEffect と resolve・resume

```
AttackEffect
  check(attack)                          登録の誤りを見つける（データの形）
  problem(state, use)                    原典で決められない場合（ワザの宣言・こんらんのコインの前。v0.3c）
  resolve(state, use)                    ワザの説明の処理（p.309 の手順 6）。決定が要れば push_attack_decision して戻る
  resume(state, use, decision, choices)  決定のあとの続きだけ（宣言・エネルギー・コイン・それまでの要素を繰り返さない）
  decision_problems(state, use, decision)  v0.4d: 決定を待つ状態の効果ごとの不変条件
```

エンジンの流れ（v0.2a から変えていない）:

- `_use_attack`: 確認（番・ワザの位置・ねむり・マヒ・登録・エネルギー）→ `problem`・こんらんのダメージの確認 → ログ `attack` → こんらんのコイン（「うら」なら `_confusion_damage` → `_finish_attack`）→ `effect.resolve` → 決定がなければ `_finish_attack`。
- `_resolve_decision`: 段階・プレイヤー・決定するプレイヤー（`NOT_YOUR_DECISION`）・決定の番号（`WRONG_DECISION`）・選択（`check_choices`）を確かめてから `_resolve`（決定を閉じる）→ `_resume_attack` → `effect.resume` → 決定がなければ `_finish_attack`。

決定を出した `resolve` のあとで `_finish_attack` を呼ばないこと、再開は決定を閉じてから 1 回だけであることは、v0.2a の仕組みそのものです。v0.4d で、この仕組みを製品のカードで初めて使いました（v0.4c まではテスト専用の 2 段階の効果だけ）。

## 4. ふきとばし（DamageAndForceSwitch）・強制交代

規定は [forced-switch-v0.4d.md](forced-switch-v0.4d.md)。

- `resolve`: 相手の対戦ポケモンに目安の数字（20）のダメージ → `DamageResult.knocked_out` なら `forced_switch_skipped`（`knocked_out`）で終わり → 相手に控えがいなければ `forced_switch_skipped`（`no_bench`）で終わり → `push_attack_decision(kind=FORCED_SWITCH, player=相手, options=相手のベンチの番号, context=(("target", 相手の対戦ポケモンの番号),))`。
- `resume`: `target` が相手のバトル場にいることを確かめ（いなければエンジンの不具合として `RuntimeError`）、場のポケモンごと入れ替え、ログ `forced_switch`、`clear_special_conditions(FORCED_SWITCH)`、`remove_persistent_effects(FORCED_SWITCH)`。
- 強制交代は「にげる」（`_retreat`）を通さない。にげるエネルギー・こんらんのコイン・にげるの失敗の記録は関係しない。トレーナーの「ポケモンいれかえ」（`SwitchWithBench`）とも別の処理（選ぶプレイヤー・ログが違う）。入れ替えの 1 行と、特殊状態・持続する効果を消す既存の関数の呼び出しは同じ形。

`DamageAndForceSwitch.decision_problems` は、決定の種類・決定するのが相手・1 匹だけ選ぶ・`target` が相手の対戦ポケモン・選べるものが相手のベンチのポケモンの番号と同じことを確かめます。

## 5. PendingDecision・相手プレイヤーの決定・Phase

| 項目 | 値 |
|---|---|
| `PendingDecision` | 項目は v0.2a のまま（`id`・`kind`・`player`・`options`・`min_choices`・`max_choices`・`resume`・`context`） |
| 決定するプレイヤー | `decision.player` = 相手。番のプレイヤー（`state.current_player`）はワザを使ったプレイヤーのまま。番の番号も変えない |
| 段階 | `Phase.DECISION`（`phase_for("forced_switch")`）。新しい段階は加えていない |
| 選べるもの | 相手のベンチのポケモンの番号（`pokemon_id`）。カードの uid ではない |
| 続きの情報 | `("use", (player, pokemon_id, card_id, attack_index))`（v0.2a の形）と `("target", 相手の対戦ポケモンの番号)` |
| 答え | `ResolveDecision(相手, 決定の番号, (番号,))`。誤りは `NOT_YOUR_DECISION`・`INVALID_PLAYER`・`WRONG_DECISION`・`INVALID_CHOICE`・`INVALID_CHOICE_COUNT`・`WRONG_PHASE`（[forced-switch-v0.4d.md](forced-switch-v0.4d.md) 5 章） |
| 待つ間のほかの操作 | どちらのプレイヤーも `WRONG_PHASE`（`_require_turn` は `Phase.MAIN` だけ） |
| 控えが 1 匹 | 決定を出す（実装上の仮定。`PROMOTE_ACTIVE` と同じ形） |
| 隠れた情報 | 決定に入るのは相手のベンチのポケモンの番号だけ（場の公開の情報）。手札・山札は入れない |

ワザの途中の決定（`resume="attack"`）を受けて番を進める処理は、決定がワザを使ったプレイヤーのものでも相手のものでも同じです（`_resume_attack` → `_finish_attack`）。

## 6. メガドレイン（DamageAndDrain）

規定は [damage-drain-v0.4d.md](damage-drain-v0.4d.md)。

- `resolve`: 相手の対戦ポケモンに目安の数字（40）のダメージ → `DamageResult.dealt <= 0` なら終わり（与えなかった・防いだ）→ `drain = (dealt // 10 + 1) // 2` → `min(drain, バタフリーのダメージ // 10)` 個をとりのぞく → ログ `drain_heal`。
- 回復するのはワザを使ったポケモン（`AttackUse.pokemon_id` で引く）。回復は既存の「きずぐすり」（トレーナー。`RemoveDamageCounters`。決定を出して選んだポケモンから 2 個）とは別の実装で、ログも別（`remove_damage_counters` の形は変えていない）。
- 決定は出さない。乱数を使わない。

## 7. ダメージ結果の受け渡し（DamageResult）

[damage-drain-v0.4d.md](damage-drain-v0.4d.md) 3 章。`deal_attack_damage` の戻り値で、受けたポケモン（種類・持ち主・番号）・防いだか・最終ダメージ（防いだら None）・きぜつするかを渡します。`dealt`（与えたダメージ）は最終ダメージで、防いだとき・0 のときは 0。

- ふきとばしは `knocked_out` だけを使う（量は使わない。最終ダメージ 0 でも入れ替える）。
- メガドレインは `dealt` だけを使う（防いだときも 0 も、与えなかったので回復しない）。
- 既存のワザの実装（`PoisonOnHeads` など）は戻り値を使わず、相手のダメージと HP を直接比べるまま（変えていない）。

## 8. きぜつ・勝敗

- きぜつの判定は v0.2f のまま、ワザの要素をすべて処理したあと（`_finish_attack`。決定のあとなら再開の最後）に、場のすべてのポケモンについてまとめて行う。サイド → 勝ち負けの判定 → 交代（`PROMOTE_ACTIVE`）→ 番の終わり → ポケモンチェック。
- ふきとばしの 20 ダメージで相手がきぜつするなら、入れ替えの内容を処理しない（対象がいない。SUPPORTED。[forced-switch-v0.4d.md](forced-switch-v0.4d.md) 4 章）。これはふきとばしの実装の中の判断で、きぜつの処理（トラッシュ・サイド・交代）の時点は変えていない。
- メガドレインの回復は、きぜつの判定の前（ワザの要素）。相手がきぜつしても回復する。
- バタフリーのきぜつ: 3 枚（キャタピー・トランセル・バタフリー）とついているカードをトラッシュし、サイドは 1 枚（v0.4c のまま）。

## 9. 乱数

ふきとばし・メガドレイン・相手の決定・入れ替え・回復は乱数を使いません。拒否されたコマンド・答えは乱数を進めません（`apply_command` は複製した状態で処理する）。こんらん状態のバタフリーのワザは、こんらんのコイン 1 枚だけ。総合テストで、対戦準備のあとの乱数がコインだけであることを確かめました。

## 10. ログ・書き出し（シリアライズ）

- 加えたログのイベント: `forced_switch`・`forced_switch_skipped`・`drain_heal`（項目は [forced-switch-v0.4d.md](forced-switch-v0.4d.md) 6 章・[damage-drain-v0.4d.md](damage-drain-v0.4d.md) 5 章）。特殊状態・持続する効果が消えたログの `reason` に `forced_switch`。どれも隠れた情報を含まない。
- 決定を出したこと・答えたことは、v0.2a と同じくログに残さない（選んだ結果が `forced_switch` に残る）。
- 書き出しは形式 8 のまま。決定を待つ状態は、形式 2 以上の `decision`（`id`・`kind`・`player`・`options`・`min_choices`・`max_choices`・`resume`・`context`（`use`・`target`））と `phase`・`current_player`・`turn_number` で完全に表せる（新しい状態の情報はない）。形式 1（v0.1 の形）は、ワザの途中の決定の項目を持たないので、ワザの途中の決定（`resume="attack"`）があれば `ValueError` にした（v0.4c までは段階 `decision` だけが残り、決定の中身が黙って落ちていた。製品のカードでは起こらなかった）。進化したバタフリーがいれば、形式 1〜6 はもともと `ValueError`（v0.4a）。
- `GameState` 全体の JSON からの読み込みは対象外のまま。

## 11. 不変条件

`engine._decision_problems` の「ワザの決定」の確認を `_attack_decision_problems` に分け、強めました。

| 確認 | 内容 |
|---|---|
| 続きの情報 | `use` が 4 つの値で、ワザを使ったポケモンが場にいて、ワザが登録表にある（v0.2a） |
| 番のプレイヤー | `use` のプレイヤーが番のプレイヤーで、ワザを使ったポケモンがそのバトル場にいて、いちばん上のカードが `use` のカード id（v0.4d） |
| ワザのログ | 今の番に、そのプレイヤーのログ `attack` がちょうど 1 回あり、ポケモン・ワザの位置が合う（v0.4d） |
| 効果ごと | `AttackEffect.decision_problems`。既定は「決定するのはワザを使ったプレイヤー」（テスト専用の 2 段階の効果もこれを満たす）。ふきとばしは 4 章（v0.4d） |

ほかに、持続する効果のログとの対応（`_persistent_effect_log_problems`）で、`forced_switch` の `old_active_pokemon_id` のあとに残っている効果を違反にしました。ベンチのポケモンの特殊状態・持続する効果、場のポケモンの番号の重複、カードの保存則、番の進行（番の終わり・ポケモンチェックが 1 回ずつ）は v0.4c までの確認がそのまま働きます。

## 12. テスト（新規・変更・変異・負荷）

| ファイル | 件数 | 内容 |
|---|---|---|
| tests/test_forced_switch_v0_4d.py（新規） | 31 | ふきとばしの流れ・控え 0/1/複数・誤った答え・待つ間の操作・二重の再開・致死ダメージ・勝ち・受け継ぐもの・特殊状態・持続する効果・最終 0・にげるの失敗の記録・ログ・こんらん・複製・書き出し・不変条件 |
| tests/test_damage_drain_v0_4d.py（新規） | 19 | `DamageResult`・メガドレイン（基本・弱点・抵抗力・プラスパワー・ディフェンダー・0・防止・回復 0/10/20/30 以上・上限・残りの HP を超える・きぜつ・勝ち・バタフリーだけ・1 回だけ）・こんらん |
| tests/test_butterfree_v0_4d.py（新規） | 9 | カードの値・登録・照合・両方のワザの登録・2 進化・受け継ぐもの・3 枚のきぜつ・複製 |
| tests/test_butterfree_games_v0_4d.py（新規） | 7 | 正式な対戦開始からの 40 局（回数の固定値・サイド・再現・乱数・番ごとの 1 回）、固定値の 1 局、でたらめな操作と答えの 16 局 |

加えたテスト: 66 件。合わせて 892 → 958 件。Python 3.11・3.12・3.13 で通る。

既存のテストの変更（v0.4c のテストを v0.4d のエンジンで動かすと 10 件が失敗する。どれも登録の内容・写しの組を固定した値か、形式 1 で書き出していた 1 件）:

| テスト | 変更 | 理由 |
|---|---|---|
| test_cards.py `test_v0_1_pool_is_ten_basic_pokemon_and_six_basic_energy` | `pool_v0_4d`（バタフリー）を確かめ、v0.1 の組の数から除く | 対応カードを加えた |
| test_effects.py `test_attacks_with_text_follow_the_verified_latest_description` | 説明文のあるワザにバタフリーの 2 つを加えた | 同上 |
| test_effects.py `test_with_and_without_do_not_change_the_original` | ワザの数 32 → 34 | 同上 |
| test_stage2_v0_4c.py `test_stage2_is_not_supported_as_a_whole` | 「バタフリーは写しにない」を「`pool_v0_4d` にある」に | 同上 |
| test_trainers.py `test_default_registry_has_exactly_the_registered_cards` | 登録表の id | 登録表の id |
| test_rng_and_serialize.py `test_format_2_adds_only_documented_fields` | 登録表の id | 同上 |
| test_evolution_games_v0_4a.py `GoldenEvolutionGameTest.test_seed` | 登録表の id（digest は同じ） | 同上 |
| test_harden_games_v0_4b.py `GoldenHardenGameTest.test_seed` | 登録表の id（digest は同じ） | 同上 |
| test_stage2_games_v0_4c.py `GoldenStage2GameTest.test_seed` | 登録表の id（digest は同じ） | 同上 |
| test_state_integrity.py `PhaseCommandMatrixTest.test_every_command_in_every_phase` | 状態の比較を形式 1 → 形式 8 に | 形式 1 は、ワザの途中の決定（この試験の `Phase.DECISION` の状態。テスト専用の 2 段階の効果）を表せないので `ValueError` にした（10 章） |

失敗ではないが、CLAUDE.md の約束（ワザの実装を加えたら `ATTACKS` にも加える）にしたがい、test_effect_preflight_v0_3d.py の `CoinIndependenceTest` にバタフリーの 2 つのワザを加えた（どちらも、プラスパワーのついたこんらん状態でなければ、いつも受け付ける）。tests/helpers.py に `BUTTERFREE` を加えた。乱数・対戦結果の固定値（digest）は変えていない。

変異テスト（scratchpad。誤りを 1 つずつ入れて、新しい 4 つのファイルと test_effect_preflight_v0_3d.py を動かした）: 23 個（指示書 20 章の 20 個と追加 3 個）すべてをテストが見つけた。構文・名前の誤りで落ちたものはない。

| # | 入れた誤り | 見つけたテスト |
|---|---|---|
| 1 | ふきとばしでワザを使ったプレイヤーが控えを選ぶ（不変条件の確認も外す） | test_forced_switch・test_butterfree・test_butterfree_games |
| 2 | 相手のベンチ以外（相手のバトル場・自分のベンチ）を選べる（不変条件の確認も外す） | 同上 |
| 3 | 20 ダメージが二重に入る | test_forced_switch・test_butterfree_games |
| 4 | 相手の決定の前に、ワザのあとの処理（番の終わり）に進む | test_forced_switch・test_butterfree・test_butterfree_games・test_effect_preflight |
| 5 | 決定のあとにワザを最初から実行し直す | test_forced_switch・test_butterfree_games |
| 6 | 強制交代でダメージが消える | 同上 |
| 7 | 強制交代で特殊状態が残る | 同上（不変条件） |
| 8 | 強制交代で持続する効果が残る | 同上 |
| 9 | 強制交代でエネルギーが消える | 同上 |
| 10 | 強制交代で場のポケモンの番号が変わる | 同上 |
| 11 | メガドレインが基本ダメージ 40 だけを見る | test_damage_drain・test_butterfree_games |
| 12 | 与えたダメージが弱点・抵抗力を無視する | test_damage_drain |
| 13 | 与えたダメージがディフェンダーを無視する | test_damage_drain・test_butterfree_games |
| 14 | 回復の切り上げを誤る（切り捨て） | 同上 |
| 15 | 回復がのっているダメージを超える | test_damage_drain・test_butterfree_games・test_effect_preflight |
| 16 | ダメージを防がれても回復する | test_damage_drain |
| 17 | こんらんでワザが失敗しても回復する | 同上 |
| 18 | バタフリーのワザのあと、相手のきぜつの処理を省く | test_forced_switch・test_damage_drain・test_butterfree_games |
| 19 | バタフリーのきぜつで進化元のカードが残る | test_butterfree・test_butterfree_games |
| 20 | 決定への答え（不正なものも）で、渡した状態の乱数が進む | test_forced_switch・test_butterfree・test_butterfree_games |
| 21 | 20 ダメージできぜつする相手も入れ替える | test_forced_switch・test_butterfree_games・test_effect_preflight |
| 22 | 控えのいない相手にも決定を出す | test_forced_switch・test_butterfree_games |
| 23 | 強制交代で持続する効果が残り、ログとの対応の不変条件も `forced_switch` を見ない | test_forced_switch・test_butterfree_games |

負荷テスト（scratchpad。リポジトリには入れていない）:

| 試験 | 規模 | 結果 |
|---|---|---|
| 自然な対戦（バタフリーのデッキ。seed 2000〜2399） | 400 局（100 局は 1 手ごとに追加の確認をしながら再現） | 内部の不具合 0。止まったのは `UNRESOLVED_MULLIGAN_COMPENSATION` 11 局だけ（v0.1 からの未解決）。原典で決められないとして拒否したワザ: `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` 11・`UNRESOLVED_PREVENTED_COIN_DAMAGE` 2（どちらも既存）。バタフリーへの進化 868・ふきとばし 1,602（入れ替え 1,068・控えなし 137・きぜつ 388・特殊状態を消した 50・持続する効果を消した 100）・メガドレイン 475（回復 320・0 個 152）・バタフリーのきぜつ 225（どれも 3 枚） |
| でたらめな操作と答え（seed 0〜199） | 200 局 | 内部の不具合 0。相手の決定を待つ間の拒否 1,238（`NOT_YOUR_DECISION`・`WRONG_DECISION`・`INVALID_CHOICE`・`INVALID_CHOICE_COUNT`・`WRONG_PHASE` など）、受け付けた答え 259（どれも相手の、今の決定の番号の、選べるもの 1 つ）。拒否は状態・乱数・ログを変えない |

確かめたこと（1 手ごと）: 決定の持ち主（相手）・選べるもの（相手のベンチ）・対象（相手のバトル場）、番ごとのワザ・番の終わり・ポケモンチェック・入れ替え・回復が 1 回まで、ワザ 1 回につき相手へのダメージの要素は 1 つまで、ベンチの特殊状態・持続する効果がない、場のポケモンの番号が重ならない、場をはなれたポケモンのカードがトラッシュにある、カードの保存則（不変条件）、乱数がコインだけ、サイドの数、再現。

## 13. 自然な対戦（正式な対戦開始からの試験）

tests/test_butterfree_games_v0_4d.py。キャタピー・トランセル・バタフリーを両方のデッキに入れ、ビードル → コクーン → スピアー・ロコン・パラス → パラセクト・ピカチュウ・ガーディ・プラスパワー・ディフェンダー・ポケモンいれかえ・マサキ・きずぐすりと混ぜた 60 枚のデッキで、`new_game` から勝敗まで 40 局（seed 0〜19・300〜319）。手順は v0.4c の手順に、バタフリーのワザの選び方（相手の対戦ポケモンが特殊状態・持続する効果を受けている・控えがいない・偶数番目の番ならふきとばし、そうでなく自分にダメージがあればメガドレイン）、相手の答え方（番の番号で決まる位置の控え）、相手の対戦ポケモンが特殊状態・持続する効果を受けていればベンチのバタフリーににげる手順を加えたもの（対戦相手の AI ではない）。

| 出来事 | 回数 |
|---|---|
| トランセル → バタフリー | 72 |
| ふきとばし | 133（こんらんで失敗 2） |
| 相手が選んだ（= 入れ替えた） | 82（控え 1 匹 25・2 匹 17・3 匹 17・4 匹 4・5 匹 19） |
| 控えがいないので入れ替えない | 11 |
| 20 ダメージできぜつしたので入れ替えない | 38 |
| 入れ替えで特殊状態を消した | 4 |
| 入れ替えで持続する効果を消した | 6 |
| ダメージを防がれたまま入れ替えた（「かたまる」の相手） | 6 |
| メガドレイン | 39 |
| 回復した（1 個以上） | 32（合計 62 個） |
| ダメージを与えたが、のっているカウンターがなく 0 個 | 7 |
| バタフリーのきぜつ（3 枚をトラッシュ） | 20（ワザのあと 18・ポケモンチェックのどく 2） |
| 勝敗が決まった | 37（止まった 3 局は対戦準備の切り直しの補償） |

「かたまる」の相手へのメガドレイン・最終ダメージ 0 のメガドレインは、自然な対戦では起こらなかったので、盤面を直接作ったテスト（tests/test_damage_drain_v0_4d.py）で確かめました。自然な対戦と、盤面を直接作ったテストは、テストのファイルを分けています。固定値の 1 局は cure seed 0（125 コマンド、39 番で勝敗。ふきとばし 2・メガドレイン 2・バタフリーのきぜつ 1）で、Python 3.11・3.12・3.13 で同じ digest です。

## 14. 既存互換性

v0.4c（`7ed8ef5`）と比べた（scratchpad の比較スクリプト。リポジトリには入れていない）。登録表の id（`effects`）は除いて比べた。どの比較も、バタフリーを使わない対戦で、出力（終わった状態・途中の状態・ログ・乱数・拒否のコード・保留中の決定・HALTED の理由）が完全に同じだった。

| 比べたもの | 局数・コマンド数 | 結果 |
|---|---|---|
| v0.3d までの既存のデッキ（たねポケモンだけ・トレーナー・みだれづき・ピカチュウ・どく・ねむり・マヒ・こんらん・自分へのダメージ・プラスパワー・ディフェンダー。止まる局（`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`・切り直しの補償）9 局・サドン・デス 1 局を含む） | 1,340 局（121,420 コマンド。途中の状態も一部すべて）とでたらめな操作 32 局（8,162 コマンド） | 同じ |
| 特殊状態 4 種類を混ぜたデッキ | 300 局（44,122 コマンド） | 同じ |
| 1 進化（パラス → パラセクト・パウワウ → ジュゴン）と、でたらめな進化 12 局 | 52 局（でたらめな操作 4,317） | 同じ |
| 「かたまる」と 1 進化（キャタピー → トランセル・ビードル → コクーン）。すべての途中の状態と保留中の決定を形式 8 で | 56 局（5,880 コマンド + でたらめな操作 5,445） | 同じ |
| 2 進化（ビードル → コクーン → スピアー。tests/test_stage2_games_v0_4c.py の 40 局。すべての途中の状態と保留中の決定（種類・持ち主・番号・選べるもの・続きの情報））と、でたらめな操作 16 局 | 56 局（4,369 コマンド + でたらめな操作 5,639） | 同じ |
| 既存のワザの途中の決定（テスト専用の 2 段階の効果。正式な対戦開始から 60 局。決定ごとに、誤った答え（決定するプレイヤーでない・違う番号）の拒否のコードも） | 60 局 | 同じ |

v0.1 の参照データ（tests/fixtures/v0_1_reference.json）は変えていない（tests/test_compat_v0_1.py は変更なしで通る）。既存のコマンド・エラーコード・段階・ログのイベントの形・止まる局（HALTED）・乱数の固定値（tests/test_reproducibility.py）は変わらない。既存の対戦の固定値（digest）は、登録表の id を除けば同じ（12 章）。

## 15. 将来への拡張

- 相手が決定するほかのワザ: `AttackEffect.decision_problems` を上書きして決定の形を宣言し、`push_attack_decision` の `player` に相手を渡す。決定の種類を加えるときは `phase_for` が `Phase.DECISION` を返すこと、`_attack_decision_problems` の共通の確認を満たすことを確かめる。
- ワザを使ったプレイヤーと相手が続けて決定するワザ（複数段階）: v0.2a の複数段階の決定（`resume` が次の決定を出す）で表せる。`decision_problems` は段階ごとの形を `context` で見分ける。
- 「ダメージを与えたら」起こるほかの効果: `DamageResult.dealt` を使い、防いだとき・0 のときの扱いをカードごとに照合する（メガドレインは最新の説明と p.319 で決まった）。量に関係なく起こる効果（どく・マヒなど）と同じ扱いにしない。
- 控えポケモンへのダメージ（p.320 の (2)・(4)）を加えるときは、`DamageResult` の `target` に種類を足す前に、受けるポケモンの選び方と計算（p.257 など）を原典で確かめる（v0.2f の約束のまま）。
- ワザの途中で対象のポケモンがいなくなる処理（v0.4d のふきとばしの致死ダメージ）は、ワザの実装の中で `DamageResult.knocked_out` を見て判断している。ダメージのあとに相手の対戦ポケモンへの効果があるワザを加えるときは、同じように p.309・p.89 の規定を当てはめ、きぜつの処理（トラッシュ・サイド・交代）は `_finish_attack` に任せる。
- 退化・ベイビィ・ポケモンパワーは対象外のまま（[architecture-v0.4c.md](architecture-v0.4c.md) 14 章）。

## 16. 設計上のトレードオフ

- 致死ダメージのときに入れ替えないことを、きぜつの処理の時点（`_finish_attack`）を変えずにワザの実装の中で表した。ワザの途中で本当にトラッシュする形にすると、v0.2f のきぜつの処理（同時のきぜつ・サイドの順番）を作り直すことになり、結果も変わらない（[forced-switch-v0.4d.md](forced-switch-v0.4d.md) 4 章）。
- 控えが 1 匹のときも決定を出す。答える手間が 1 回増えるが、「相手が選ぶ」の形と `PROMOTE_ACTIVE` の約束がそろう。
- 形式 1 で、ワザの途中の決定を `ValueError` にした。v0.4c までは段階 `decision` だけが書き出されていた（テスト専用の効果でだけ起こった）。黙って落とさないための変更で、ほかの状態の形式 1 の書き出しは変わらない。
- `forced_switch` を `switch` と別のイベントにした。ログを読む側は、入れ替えの種類を 3 つ（`retreat`・`switch`・`forced_switch`）見分ける必要がある。
