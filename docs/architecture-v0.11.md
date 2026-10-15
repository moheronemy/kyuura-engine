# 設計の変更（v0.11）

v0.11 は、サカキのカイリキー（PMCG6-061。ジム拡張第2弾 闇からの挑戦）のポケモンパワー「こんじょう」（相手のワザによるダメージで「きぜつ」するとき、使える。コインを投げて「おもて」なら「きぜつ」せず残り HP が 10。ダメージを受けるとき、すでにねむり・マヒ・こんらんなら使えない）と、ワザ「ハリケーンパンチ」、進化元のサカキのワンリキー（PMCG6-057。チョップ・いかりのスーパーパンチ）・サカキのゴーリキー（PMCG6-059。いちかばちか・じごくがため）を加えた版です。

目標は、**きぜつの判定から実際のきぜつの処理までのあいだに、原典にもとづく特殊能力の使用・選択・コイン・状態の変更を安全に挟める仕組み**を、既存の構造を使って作ることです。

関連する文書:

- 原典の照合と裁定: [guts-v0.11.md](guts-v0.11.md)（G1〜G42・A4〜A6）と [giovanni-machamp-line-v0.11.md](giovanni-machamp-line-v0.11.md)（L1〜L14）
- きぜつの判定ときぜつの処理のあいだの仕組み: [ko-prevention-v0.11.md](ko-prevention-v0.11.md)
- 確かめた結果: [v0.11-verification.md](v0.11-verification.md)

新しく加えたのは次のものだけです。

- 使用を宣言する特殊能力の実装 `PreventKnockOutOnHeads`（`declared = True`。決められたときにしか使えない）
- ワザ 1 回の中だけの記録 `AttackUse.ko_prevention_able`（ダメージを受けたときに使える状態だったか）
- きぜつの処理の前の境界 `engine._ko_prevention_offer` と、決定の種類 `KO_PREVENTION`・再開先 `"knock_out"`（`_resume_knock_out`）
- 公開の問い合わせ `available_ko_prevention_power`
- 2 つのワザの実装（`CoinHeadsDamagePerOwnCounter`・`SelfDamageInsteadOnTails`）、ワザの宣言 `AttackEffect.opponent_effect_elements`、ダメージの候補の組 `DamageProfile.outcomes`・`pairs()`
- 4 つのログのイベント（`ko_prevention_declined`・`ko_prevention_declared`・`ko_prevented`・`ko_prevention_failed`）
- 1 つの `UNRESOLVED_…` のコード（`UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT`）
- 不変条件の 1 つの例外（この決定を待つ間の、HP 以上のダメージのポケモン）

状態の項目・書き出しの形式（9 のまま）・コマンドの種類・段階は加えていません。決定の種類を 1 つ加えました（既存の `Phase.DECISION`・`ResolveDecision` で答える）。

## 1. v0.10 の処理の順番（B1）

v0.10 の `engine._use_attack` を読んで確かめた順番:

| 順番 | 処理 | 場所 | 原典 |
|---|---|---|---|
| 1 | 宣言の前の確認（番・段階・ねむり・マヒ・エネルギー・`effect.problem`・こんらんのダメージの変更効果・C18） | `_use_attack` | p.309 |
| 2 | 宣言（ログ `attack`）→ こんらんのコイン（こんらんのとき） | `_use_attack`・`_confusion_check` | p.309 手順 5 |
| 3 | ワザのダメージの適用（「とうめい」の評価 → p.321 の計算 → 「はんげき」の判定 → ダメージをのせる） | `effects.deal_attack_damage` | p.160・p.321・p.192 |
| 4 | 「はんげき」の 10 を与える（ダメージの要素がすべて終わったところ） | `effects.finish_damage_elements` | p.89・p.192 |
| 5 | ダメージ以外の効果（ワザのコイン・特殊状態・入れ替えの決定・回復） | ワザの実装 | p.89・p.309 |
| 6 | きぜつの判定（場のすべてのポケモンで HP 以上） | `_finish_attack` | p.309・p.323・p.324 |
| 7 | きぜつの処理（トラッシュ。同時なら `simultaneous`） | `_finish_attack` → `_after_knockouts` | p.313・p.323 |
| 8 | サイド（きぜつしたポケモンの相手側。同時のきぜつは番のプレイヤーから正規化） | `_after_knockouts`（決定 `TAKE_PRIZE`） | p.323・p.325 |
| 9 | バトル場に出す（番でないプレイヤーが先） | `_after_knockouts`（決定 `PROMOTE_ACTIVE`） | p.323・p.324 |
| 10 | 勝ち負け（p.311 の表） | `_after_knockouts` | p.311 |
| 11 | 番の終わり → ポケモンチェック | `_end_turn`・`_pokemon_check` | p.310・p.323 |

v0.10 の `_finish_attack` は 6 と 7 を同じ関数で続けて行っていました（6 の判定と 7 の処理のあいだに、外から何かを挟む口がない）。「こんじょう」はきぜつ「する」とき（6 のあと、7 の前）に使うので、ここに境界を加えます。

## 2. 設計案の比較（B2）

| 観点 | 案 A: きぜつの処理の直前に専用の処理 | 案 B: きぜつの候補を評価する共通の境界 | 案 C: ダメージの適用のときに評価 | 案 D: 独立した決定の段階 |
|---|---|---|---|---|
| 形 | `_finish_attack` の中で、こんじょうの条件を直接書いてコインを投げる | `_finish_attack` を「判定」と「処理」に分け、あいだに 1 か所の境界（`_ko_prevention_offer`）を置く。選択は既存の決定 | `deal_attack_damage` の中で、HP 以上になったら評価する | 新しい `Phase`（きぜつの防止）と専用のコマンド・保留中のリスト |
| 原典との整合 | 時点は合う | 時点は合う（ワザの要素をすべて処理したあと・きぜつの処理の前。G2） | **合わない**: ワザの途中（p.309「ワザを使っている最中に、…特殊能力の使用を宣言してはいけません」）。HP 以上になったあとの要素（でんげきのコイン・自分へのダメージ・「はんげき」）が残る | 時点は合う |
| 任意の使用 | コインを投げる前に選ばせる口がない（強制にするか、別に作る） | 既存の決定（0〜1 個）で表せる | ワザの途中の決定になり、ダメージの要素の途中で止まる（再開の位置が増える） | 表せる |
| 原子性 | コマンド 1 回で完結するなら問題ない | 決定を出して止まる・答えで続ける（v0.2a から。`apply_command` は複製の上で処理） | ワザの途中で止まるので、ダメージの要素の続きを保存する必要がある | 新しい段階の不変条件・遷移を全部書く必要がある |
| 既存のワザの処理 | 変えない | 変えない（`_finish_attack` の本体を `_knock_out_after_attack` に移しただけ） | すべてのダメージの要素の後ろに分岐が入る | 段階の遷移を加える |
| 「はんげき」との整合 | 「はんげき」の後になる | 「はんげき」（ワザの処理の中）の後になる。C18 の止める処理は宣言の前のまま | 「はんげき」の前になってしまう（ダメージの要素ごと） | 後になる |
| 乱数 | 選択がないとき不要なコインを投げてしまう | 答えたあと、使うときだけ 1 回 | 同左 | 同左 |
| ログの監査 | 監査できる | 宣言・コイン・結果を分けて監査できる | 途中の位置が多く監査が難しい | 監査できる |
| 保存・復元 | 形式 9 のまま | 形式 9 のまま（既存の `decision` で表せる。3 章） | ワザの続きを保存する形式が要る | 新しい段階・項目の形式（形式 10）が要る |
| API の互換 | 変えない | 決定の種類が 1 つ増えるだけ（`ResolveDecision` で答える） | 決定の種類・再開の位置が増える | コマンド・段階が増える |
| 複雑さ | 小さいが、任意の使用を表せない | 小さい（境界 1 か所・決定 1 種類・再開先 1 つ） | 大きい | 大きい |
| 採否 | 不採用（**任意の使用を省略する案は採らない**） | **採用**（A と B の合わせた形: 境界は 1 か所で、条件はこんじょうに必要なものだけ） | 不採用 | 不採用（指示のとおり、段階・保留中のリストを増やさない） |

採用した形は、きぜつの処理の直前の 1 か所に「こんじょうを使えるポケモンがいるか」を聞く境界を置き（案 A の小ささ）、選択は既存の決定の仕組み（案 B）で表すものです。汎用のイベントの仕組み（購読・発行・優先度）は作っていません。きぜつを防ぐ効果が 2 つ以上になる場合の順番は原典で決まっていない（G16・G40）ので、仕組みが順番を決めないように、2 つ以上なら止めます。

## 3. プレイヤーの選択（B3）

| 案 | 検討 | 採否 |
|---|---|---|
| 1. ワザの途中で決定を出す | 決定の時点は「ワザの要素をすべて処理したあと」（ワザの途中ではない）。v0.4d の「ふきとばし」（相手が決定する）と同じ `push_decision`（`player=相手`）を、ワザのあと・きぜつの処理の前に出す | **採用**（ワザの途中ではなく、ワザのあとの決定） |
| 2. ワザの前のコマンドで選ぶ | ワザを使うのは相手プレイヤー。こんじょうの持ち主は、相手がワザを宣言する前に「使うか」を答えることになる。そのときは、ダメージの量・コインの結果・HP 以上になるか（使えるとき）が分からない。p.311 の宣言の時点（決められたとき）とも合わない | 不採用 |
| 3. 既存の選択処理を広げる | 既存の決定（`PendingDecision`・`ResolveDecision`・`_RESUMERS`）をそのまま使い、種類（`KO_PREVENTION`）と再開先（`"knock_out"`）を 1 つずつ加える | **採用**（1 の実装の方法） |

- 決定を出すのはコインの前で、まだ乱数を使っていません。決定の中身（選べるもの・`context`）にコインの結果はありません（G12・G13。`test_coin_is_not_known_before_answering`）。持ち主が知っているのは、ワザのダメージと効果・ワザのコイン・「はんげき」・HP 以上になったことだけです（どれも公開の情報）。
- 「選ばない」（0 個）が使わない答えです（`min_choices` 0・`max_choices` 1）。エンジンは使うかを選びません。
- 決定を待つ間は `Phase.DECISION` で、`ResolveDecision` 以外は受け付けません（v0.2a から）。
- 攻撃の途中の決定を保存できないから強制にする、ということはしていません（形式 9 の `decision` で表せる。4 章）。

## 4. 保存形式（B4）

**形式 9 のまま（形式 10 を加えない）**。

| 項目 | 扱い |
|---|---|
| 新しい状態 | なし。待っている決定は既存の `GameState.decision`（`PendingDecision`）で表す |
| 決定の種類 | `kind` = `"ko_prevention"`、`resume` = `"knock_out"`（文字列の値。形式 2 以上の `decision` の項目で書き出せる） |
| ワザの処理の再開位置 | 決定はワザの要素をすべて処理したあとに出すので、ワザの続きはない。答えのあとは `_resume_knock_out` → `_knock_out_after_attack`（きぜつの処理）だけ。`context` の `"attack"`（ワザを使ったプレイヤー・ポケモン・カード id・ワザの位置）は不変条件とログの監査のため |
| ダメージを受けたときの特殊状態の記録 | 決定を出す前に、使える状態だったポケモンだけを選べるものにする。記録（`AttackUse.ko_prevention_able`）は決定のあとに要らない（ワザ 1 回の中だけの値。状態に持たない） |
| 乱数 | 決定を出すまでに乱数を使わない。答えで使うときに 1 回。乱数の状態は既存の `GameState.rng`（形式 9 の書き出しは乱数の指紋だけ。pickle・`clone` は乱数の状態ごと写す） |
| ログ | 既存の `GameState.log`。決定そのものはログに残さない（v0.2a から）。答えは `ko_prevention_declined`・`ko_prevention_declared` |
| 不変条件 | `_ko_prevention_decision_problems`・`_ko_prevention_awaiting`（[ko-prevention-v0.11.md](ko-prevention-v0.11.md) 4 章） |
| 古い形式との互換 | 形式 2〜9 は決定の項目で書き出せる。形式 1 は決定の項目がないので `ValueError`（v0.4d のワザの途中の決定と同じ。黙って落とさない） |
| 保存・復元の再現性 | pickle・`copy.deepcopy`・`clone` で写した状態から、同じ答えで同じ結果になる（`DecisionTest.test_save_and_resume`・`test_replay_and_save_restore_at_the_decision`・[v0.11-verification.md](v0.11-verification.md) 2.3） |

書き出しの監査の `LATEST_FORMAT` は 9 のまま。`required_format` は再開先 `"knock_out"` の決定を形式 2 以上にしました（tests/log_audit.py）。

## 5. HP とダメージカウンター（B5）

- 「おもて」の処理は `pokemon.damage = HP − remaining_hp`（`remaining_hp` は登録の 10）です。HP 100 なら 90（ダメージカウンター 9 個）。「ダメージを 10 にする」処理ではありません。
- HP はいちばん上のカード（進化した姿）の値（v0.4a）。HP を変える効果（退化・HP を増やすカード）は対応カードにありません。退化を加えるときは、こんじょうのあとの HP の扱いを原典で確かめます。
- 登録の確認（`PreventKnockOutOnHeads.check`）はパワーの文面だけを見て、カードの HP を見ません。HP が `remaining_hp` 以下のカードに登録する場合は扱いません（登録はサカキのカイリキー（HP 100）だけ。ほかのカードに登録するときに確かめる）。
- ダメージを 0 にする・カウンターを取りのぞく処理（きずぐすり・`remove_damage_counters`）とは別のログ（`ko_prevented`。`damage_before`・`total_damage`・`remaining_hp`）にしました（G21）。

## 6. 原子性（B6）

| 保証 | 確かめ方 |
|---|---|
| 無効なワザは状態を変えない | G37 の止める処理（`UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT`）はワザの宣言の前（こんらんのコインの前）。拒否で状態・乱数・ログが変わらない（`G37Test`・`KoPreventionAttackEffectTest`） |
| 不必要なコインを投げない | 決定を出すまで乱数を使わない。使わないと答えたら投げない（`test_decline_is_knocked_out_without_a_coin`。変異 26・28・29） |
| コインは正しい回数 | 使うと答えたら 1 回（`UseTest`。変異 5・6。ログの監査の 13） |
| 使わない選択を正確に処理 | `ko_prevention_declined` → ふつうにきぜつ（`DecisionTest`） |
| 未確定の決定がある間に別の操作をしない | `Phase.DECISION`。`EndTurn`・`UseAttack`・`UsePokemonPower` などは拒否（`test_other_operations_are_rejected_while_waiting`） |
| 正常な処理を途中で再開できる | 答えの `ResolveDecision` で `_resume_knock_out` から続ける |
| 保存・復元のあとも結果が同じ | pickle・`deepcopy`・`clone`（`test_save_and_resume`・`test_replay_and_save_restore_at_the_decision`・保存と復元の確かめ。変異 25） |
| 例外で中途半端な状態を確定しない | `apply_command` は複製の上で処理する（v0.2a）。`RuntimeError`（G40 など）は渡した状態を変えない |
| 決定の答えの不正 | 選べないもの・多すぎる選択・決定するプレイヤーでない・番号の違いは `IllegalActionError`（既存の `check_choices`）で、状態・乱数・ログを変えない |

## 7. 既存の未解決 C18（B7）

- こんじょうの発動条件は「相手のワザによるダメージ」です。「はんげき」の 10 は特殊能力によるダメージ（v0.10 の C13。SUPPORTED）なので当たりません（G5）。ワザを使ったサカキのカイリキーが「はんげき」で HP 以上になっても使えず、ふつうにきぜつします（`test_strikes_back_damage_does_not_offer`）。
- C18（カイリキーがワザで、ワザを使ったポケモンが「はんげき」だけできぜつする場合）は、こんじょうで解決したことにしていません。止める処理（`UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT`）はワザの宣言の前のままです（G39）。
- 変えたのは、C18 の判定に使うダメージの候補の組み合わせだけです。v0.10 は「相手へのダメージの候補」と「自分へのダメージの候補」のすべての組で確かめていました。サカキのゴーリキーの「いちかばちか」は「おもて」（相手に 60・自分に 0）と「うら」（相手に 0・自分に 100）が同時に起こらないので、すべての組で確かめると起こらない組（相手のきぜつと自分への 100）で止めてしまいます。v0.11 から、同じコインの結果でいっしょに起こる組（`DamageProfile.pairs()`。`outcomes` を書いた実装はその組、書いていない実装はすべての組）で確かめます。v0.10 までのワザは `outcomes` を書いていないので、すべての組で、答えは v0.10 と同じです（tests/test_counterattack_v0_10.py の C18 のテストはそのまま通る。変異 35 が見つける）。
- 「きぜつを防ぐ能力」を、どく（G7）・こんらん（G4）・自分のワザ（G4）・「はんげき」（G5）・ダメージカウンターの移動（G6）には当てはめていません。決定を出すのは `_finish_attack`（ワザのあと）の経路だけで、ポケモンチェックのきぜつ（`_pokemon_check` → `_after_knockouts`）は通りません。

## 8. ログ（B8）

| イベント | 項目 | 意味 |
|---|---|---|
| `ko_prevention_declined` | `player`（持ち主）・`pokemon`（カードの uid）・`pokemon_id`・`power`（`PowerKey` の文字列。例 `PMCG6-061@power0`）・`total_damage` | 使わないと答えた |
| `ko_prevention_declared` | 同上と `hp` | 使うと答えた（p.311 の手順 1 の宣言） |
| `coin_flip` | `source` `power`・`effect`（`PowerKey`）・`player`（持ち主）・`pokemon_id`・`result` | 宣言のすぐあとのコイン（既存のイベント） |
| `ko_prevented` | `player`・`pokemon`・`pokemon_id`・`power`・`result`・`damage_before`・`total_damage`（HP − 10）・`remaining_hp`（10） | 「おもて」。きぜつしなかった |
| `ko_prevention_failed` | `player`・`pokemon`・`pokemon_id`・`power`・`result`・`total_damage` | 「うら」。そのあとの `knock_out` でふつうにきぜつ |

指示の候補との対応:

| 候補 | 採否 | 理由 |
|---|---|---|
| `ko_prevention_check` | 使っていない | この版の `*_check`（`sleep_check`・`confusion_check`・`evade_check`）は自動のコインの結果の名前。こんじょうは宣言と結果を分けて残す（`ko_prevention_declared` → `coin_flip` → 結果）ので、宣言の有無（`declined`・`declared`）と結果のイベントにした |
| `ko_prevented` | 採用 | 「おもて」 |
| `ko_prevention_failed` | 採用 | 「うら」 |

記録の候補との対応: 能力の識別（`power`）・使うポケモン（`pokemon`・`pokemon_id`）・プレイヤー（`player`）・使用の選択（`declined`／`declared`）・きぜつの原因（同じワザの直前の `damage`。ワザの宣言 `attack` から後。重複させない）・コイン（`coin_flip`・`result`）・成功・失敗（イベントの種類）・前後のダメージ（`damage_before`・`total_damage`）・きぜつしたか（そのあとの `knock_out` の有無）。

## 9. 実装（C1〜C5）

- **C1 特殊能力**: `PreventKnockOutOnHeads(remaining_hp)`（`PowerEffect`）。`declared = True`（使用を宣言する。G1）で、自動的にはたらく・常にはたらく特殊能力（`declared = False`）と同じ真偽値で区別します（種類の項目を増やしていない）。`check`（ポケモンパワー・説明文）・`is_able`（ねむり・マヒ・こんらんでない。どくは見ない）・`check_usable`（`UsePokemonPower` で使おうとしたら `POWER_NOT_USABLE_NOW`。G41）・`resolve`（`UsePokemonPower` の経路では呼ばれない。呼ばれたら `RuntimeError`）・`prevent`（コイン 1 枚と結果）。登録は `PowerKey("PMCG6-061", 0)`（印刷の文面・最新の説明・出典 P43 p.193）。
- **C2 きぜつの防止**: `_finish_attack` → `_ko_prevention_offer` → 決定 → `_resume_knock_out` → `_knock_out_after_attack`（[ko-prevention-v0.11.md](ko-prevention-v0.11.md) 1〜3 章）。「おもて」のポケモンは HP 未満なので、きぜつ・サイド・交代・勝ち負けに入りません。
- **C3 乱数**: `flip_coins(state, owner, 1, source="power", effect=PowerKey, pokemon_id=…)` だけ。同じ seed・状態・コマンドの列から同じ結果（`test_answering_is_deterministic`・`GoldenGiovanniGameTest` の固定値 `GOLDEN_DIGEST`）。決定を出す・使わないと答える・拒否のときは乱数を使いません。
- **C4 かがくへんかガス**: `ko_prevention_suppressors` は `continuous.suppressors_of` をそのまま呼びます（判定を複製しない）。決定を出す時点（きぜつの判定）のガスで決めます。`UsePokemonPower` では v0.8 の順番どおり `POWER_SUPPRESSED` が `POWER_NOT_USABLE_NOW` より先です。
- **C5 進化系とワザ**: [giovanni-machamp-line-v0.11.md](giovanni-machamp-line-v0.11.md)。チョップ（`DamageOnly`）・いかりのスーパーパンチ（`CoinHeadsDamagePerOwnCounter(20)`）・いちかばちか（`SelfDamageInsteadOnTails(100)`）・じごくがため（`CoinBonusDamageAndParalyze(bonus=20)`）・ハリケーンパンチ（`CoinFlipDamage(coins=4, damage_per_heads=30)`。乱数 4 回・ログ `coin_flip` 4 つ）。
- 写し: `pool_v0_11`（scripts/extract_kyuura_cards.py の `POOL_V0_11`。サカキのワンリキー・サカキのゴーリキー・サカキのカイリキー。サカキのカイリキーは v0.10 の参照カードから移した）。照合の記録は card_verification.json。登録表の id は `kyuura-engine-0.11`、ワザ 61 件・パワー 7 件。

### 9.1 G37 の止める処理

こんじょうを使えるポケモンが、ダメージで HP 以上になり、同じワザでそのポケモンに効果（特殊状態・入れ替え）を与える場合は、原典で決められない（G37。UNRESOLVED）ので、ワザの宣言の前に止めます（`ko_prevention_attack_effect_problem`）。

- ワザの実装は、ダメージのあとに相手に与える効果の種類を `AttackEffect.opponent_effect_elements` で宣言します（`PoisonOnHeads`・`PoisonOpponent`・`PoisonWithoutDamage`・`SleepOpponent`・`PutToSleep`・`ParalyzeOnHeads`・`CoinBonusDamageAndParalyze`・`ConfuseOnHeads`・`DamageAndForceSwitch`）。宣言と実装の `attack_reaches` の呼び出しが合うことを、tests/test_guts_v0_11.py がソースを読んで確かめます（9 種類）。
- HP 以上になりうるかは、ダメージの候補（`damage_profile`。コインのどの結果も）と状態を変えない計算（`preview_attack_damage`）で求めます。コインの結果で受け付けるかが変わりません（`CoinIndependenceTest`）。
- 確かめる順番: ワザの共通の確認 → `effect.problem` → こんらんのダメージの変更効果 → C18 → **G37**（どれも宣言の前・こんらんのコインの前）。

## 10. エラーコード

| コード | 種類 | いつ |
|---|---|---|
| `POWER_NOT_USABLE_NOW` | `IllegalActionError`（新しい理由） | 「こんじょう」の使用を `UsePokemonPower` で宣言しようとした（決められたときではない。G41）。共通の確認・`POWER_NOT_DECLARABLE`・`POWER_SUPPRESSED` のあと |
| `UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT` | `UnsupportedError`（新しい） | G37 になりうるワザの宣言（こんらんのコインの前） |
| 既存の `INVALID_CHOICE`・`INVALID_CHOICE_COUNT`・`DUPLICATE_CHOICE` など | `IllegalActionError` | 決定の答えの不正（既存の `check_choices`。`test_invalid_answers`） |

拒否の順番の約束（v0.7・v0.8 の API の約束）は変えていません。エンジンが止める `UNRESOLVED_…` は 16 件（v0.10 の 15 件 + 1 件）、未解決の裁定は 19 件（v0.10 の 17 件 + G37・G40）。

## 11. 不変条件

- 場の形: HP 以上のダメージのポケモンが場に残るのは、v0.10 の例外（`_counter_knocked_out_attacker_awaiting`）と、v0.11 の `_ko_prevention_awaiting`（この決定を待つ間の、決定の対象のポケモンと、同じワザで HP 以上になったワザを使ったポケモン）だけ。
- 決定の形: `_ko_prevention_decision_problems`（[ko-prevention-v0.11.md](ko-prevention-v0.11.md) 4 章）。種類と再開先の組・選ぶ数・決定するプレイヤー・ワザ・特殊能力・HP 以上・特殊状態・ガス・ログ（そのワザのダメージがあり、こんじょう・きぜつのログがまだない）。
- 決定の種類と再開先の組を `_decision_problems` が確かめます（`KO_PREVENTION` なら `"knock_out"`、その逆も）。

## 12. ログの監査（tests/log_audit.py）

ワザごとに、ログから組み立て直したその時点の場（いちばん上のカード・ねむり・マヒ・こんらん・はたらいているかがくへんかガス・ダメージ）で、次のことを確かめます。

- 相手のワザのダメージ（0 より大きい）を受けた、こんじょうを持つポケモンについて、受けたときに使える状態だったか（ねむり・マヒ・こんらん）を記録する。
- そのワザのあと HP 以上で、使える状態で、ガスに消されていないなら、きぜつ（`knock_out`）の前に `ko_prevention_declined` か `ko_prevention_declared` が 1 つある（ないままきぜつしていたら誤り）。
- `ko_prevention_declared` のすぐあとに、持ち主の、その特殊能力のコイン（`coin_flip`。`source` `power`）があり、そのすぐあとに結果（`ko_prevented`／`ko_prevention_failed`）があって、コインの結果と合う。`ko_prevention_declined` のあとにコインはない。
- 1 つのワザで、答えは 1 回まで（二重の処理がない）、結果の数は宣言の数と同じ。
- 宣言・答えは、ワザのあと（そのワザの中）・持ち主・登録がこんじょう・相手のワザのダメージを受けた・HP 以上・きぜつの前・使える状態・ガスに消されていない、のすべてを満たす。
- 「おもて」の `total_damage` が HP − 10（`remaining_hp` 10）で、そのポケモンはそのワザのあときぜつしない（サイドも取られない）。「うら」・使わないなら、そのワザのあときぜつする。
- ダメージの組み立て直しに `ko_prevented` を含める（ダメージをその値にする）。

指示の 14 種類の誤りを、自然な対戦のログを書きかえて見つけることを確かめました（tests/test_giovanni_games_v0_11.py の `LogAuditGutsTest`。[v0.11-verification.md](v0.11-verification.md) 2.4）。

ログだけでは確かめられないこと:

- 決定の中身（選べるもの・`context`）はログに残らない（v0.2a からの約束）。答えと選べるものの対応は、エンジンの不変条件（`_ko_prevention_decision_problems`・`check_choices`）と単体テストで確かめる。監査は、答えのイベントのポケモン・特殊能力が、その時点で使えたポケモン・特殊能力と合うかを確かめる（14 の誤り）。
- 乱数の消費の回数は、ログの `coin_flip` の数で確かめる（13 の誤り）。ログに残らない乱数の消費（エンジンの不具合）は、乱数の指紋の固定値（`GOLDEN_DIGEST`・tests/test_reproducibility.py）と前の版との比較で見つける。
- 判定の時点の特殊状態・ガスは、ログから組み立て直した値。ログにない状態の変化（盤面を直接作ったテスト）では確かめられない。
- 原典で決められないとして止めた場合（G37）は、拒否なのでログに残らない。止めたことは単体テストとストレス実行で確かめる。

## 13. 変えたもの

| ファイル | 変更 |
|---|---|
| kyuura_engine/effects.py | `PreventKnockOutOnHeads`・`AttackUse.ko_prevention_able`・`deal_attack_damage` の記録・`ko_prevention_power`・`ko_prevention_suppressors`・`available_ko_prevention_power`（公開）・`ko_prevention_attack_effect_problem`・`AttackEffect.opponent_effect_elements`（9 種類の実装に宣言）・`DamageProfile.outcomes`・`pairs()`（C18 の判定に使う）・`prevented_coin_damage_problem`（`CoinFlipDamage.problem` を関数に分けた。止める条件は同じ）・2 つのワザの実装・登録（id `kyuura-engine-0.11`） |
| kyuura_engine/engine.py | `_finish_attack` を判定と処理に分けた（`_ko_prevention_offer`・`_knock_out_after_attack`）、再開先 `"knock_out"`（`_resume_knock_out`）、G37 の確認、`_finish_attack` に `use` を渡す（3 か所）、不変条件（`_ko_prevention_awaiting`・`_ko_prevention_decision_problems`） |
| kyuura_engine/decisions.py | 決定の種類 `KO_PREVENTION` |
| kyuura_engine/serialize.py | 形式 1 で再開先 `"knock_out"` の決定は `ValueError` |
| kyuura_engine/__init__.py・pyproject.toml | `available_ko_prevention_power` を公開、版 0.11.0 |
| kyuura_engine/cards.py | 写しのプール `pool_v0_11` |
| scripts/extract_kyuura_cards.py・kyuura_engine/data/kyuura_cards.json | `POOL_V0_11`。サカキのカイリキーを参照カードから移した。写しを作り直した（`--check` が kyuura `ecb2d694` と一致） |
| kyuura_engine/data/card_verification.json | PMCG6-057・PMCG6-059 の照合の記録を加え、PMCG6-061 を書き直した（パワー・ワザ） |
| tests/log_audit.py | 12 章 |
| tools/stress_engine.py | サカキのカイリキーの組（`giovanni`・`giovanni_mixed`）。`POWER_USERS` の最後にサカキのカイリキー（宣言の試み → `POWER_NOT_USABLE_NOW`）。こんじょうの観測（ワザの前の場からエンジンと同じ公開の問い合わせで求めて、ログと比べる） |

## 14. 変えなかったもの

- 書き出しの形式（9）・状態の項目・コマンド・段階。
- きぜつの処理（`_after_knockouts`）・サイドの正規化・バトル場に出す順番・p.311 の表（v0.2f）。`_finish_attack` の本体は `_knock_out_after_attack` に移しただけで、中身は同じ。
- v0.5〜v0.10 の特殊能力（エナジートランス・あまごい・ダメージスワップ・かがくへんかガス・とうめい・はんげき）と、その拒否のコード・ログ。
- 既存の未解決の裁定 17 件（コードのある 15 件・コードのない T27・C34/C35）。C18（判定の組の求め方だけを変え、v0.10 のワザでは同じ答え）・R13・T19b・H4・K3 の扱い・拒否のコードの順番の保証しない範囲。
- 比較の駆動（tools/compat_driver.py）・参照データ（tests/fixtures/compat_base_4bd97bf.json・tests/fixtures/v0_1_reference.json）。
- kyuura（変更していない）。

## 15. 変えた既存のテストと理由

| テスト | 変更 | 理由 |
|---|---|---|
| test_*_games（stage2・blastoise・alakazam・harden・evolution・bulbasaur・butterfree・muk・haunter・machamp）・test_rng_and_serialize・test_trainers・test_chemical_gas_v0_8・test_rain_dance_v0_6・test_damage_swap_v0_7 | 登録表の id を `kyuura-engine-0.11` に | 書き出しの `effects` の id が変わった（ルールの動き・乱数・ログ・固定値の指紋は同じ） |
| test_pokemon_powers_v0_5 | パワーの一覧に「こんじょう」、件数 7 | 登録を加えた |
| test_effects | 説明文のあるワザの一覧に 4 件、件数 61、パワーの一覧 | 同上 |
| test_cards | `pool_v0_11`、使えるカード | 写しのプールを加え、サカキのカイリキーを参照カードから使えるカードにした |
| test_counterattack_v0_10 | サカキのカイリキーを「使えないカード」の例から外し、「はんげき」以外のパワーを持つ使えるカードの例にした。`CoinIndependenceTest` の独立のモデルが、コイン 4 枚（ハリケーンパンチ）と自分のカウンターの数（いかりのスーパーパンチ）を実装の値から読むようにした | v0.10 はサカキのカイリキーを参照カードとして使っていた。モデルは「×」のワザのコインを 2 枚までと仮定していた |
| test_effect_preflight_v0_3d | `ATTACKS` に 5 件、`EVOLVED_FROM`・コインのダメージの一覧 | ワザの実装を加えたら `ATTACKS` に加える（CLAUDE.md） |
| test_unresolved_boundaries_v0_4e | `ALL_CODES` に新しいコード、`KoPreventionAttackEffectTest` | 止める場合を加えた |
| tests/helpers.py | サカキのワンリキー・サカキのゴーリキーのカード id | テストで使う |

## 16. 次の版への提案（実装していない）

- きぜつを防ぐ効果が 2 つ以上になる場合（2 匹のこんじょう・きあいのハチマキ（ネオ。2000.02.14 版の範囲の外）・ベンチにダメージを与えるワザ）: 順番を原典で確かめ、確かめるまではワザの宣言の前に止める（新しい `UNRESOLVED_…`）。今の `RuntimeError` を置きかえる。
- G37 の裁定: 当時の公式の Q&A で、こんじょうで生き残ったポケモンがそのワザの効果を受けるかを確かめられれば、止める処理を決まった処理に置きかえる。
- 「きぜつしたとき」に使う特殊能力（R団のファイヤーの［ふしちょう］。p.82）: きぜつの処理（トラッシュ）のあとの別の境界になる。サイドを取る・バトル場に出す決定との順番を原典で確かめる。
- ポケモンチェックのきぜつ・特殊能力のダメージによるきぜつに当てはまる効果: その経路（`_pokemon_check`・`_apply_counterattack`）にも境界が要る。
- C18 の裁定（v0.10 のまま）。
