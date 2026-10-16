# v0.41: 回復・ダメージカウンターの移動・特殊状態の変化を中心とする 15 枚

v0.40（`cbc5515`。版 0.40.0）から作業ブランチ `claude/v0.41-heal-counter-status` を作り、依頼の 15 枚を加えました（版 0.41.0）。

1. 依頼の 15 枚（クサイハナ PMCG2-009・ウツボット PMCG2-016・シードラ PMCG3-020・わるいペルシアン PMCG4-048・カツラのファイヤー PMCG6-035・ヤドン PMCG4-032・
   エリカのナゾノクサ PMCG5-002・エリカのナゾノクサ PMCG5-003・エリカのクサイハナ PMCG5-009・ナツメのコダック PMCG6-036・ナツメのゴルダック PMCG6-038・
   ナツメのモルフォン PMCG6-022・ナツメのヤドラン PMCG6-048・エリカのプリン PMCG5-058・R団のミュウツー PMCG6-055）を、どのワザも登録して対応にした（1 章。
   保留なし。特殊能力を持つカードはない）。対応ポケモン 224 → 239、ワザの登録 396 → 425（特殊能力 12 のまま）、写し 245 → 260 枚。
2. 回復（ダメージカウンターをとりのぞく）を 1 つの要素 `HealCounters` にまとめた（自分だけ・自分の場の全員・お互いの場の全員、決まった数・コインの「おもて」の数、
   ワザ全体のコイン・要素のコイン。3 章）。ダメージカウンターを相手にのせる要素 `ShiftCountersToOpponent`・取り替える要素 `SwapCounters` は、ダメージの処理を通さない
   ダメージカウンターの移動として加えた（取り替える前の双方の数で処理する）。特殊状態を選ぶ要素 `ChosenStatus`（決定 `select_special_condition`）・山札から
   エネルギーをつける要素 `AttachFromDeck`（決定 `attach_from_deck`）を加えた。
3. ダメージシフト・チェンジダメージで、相手の対戦ポケモンがその効果を受けない（「ワザをうけない」状態・「とうめい」）とき、自分の側を処理するかは記録から
   決まらないので、宣言の前に止める（新しい未解決 CX1。`UNRESOLVED_COUNTER_TRANSFER_PROTECTED`。5 章）。停止コード 46 → 47、未解決の裁定 47 → 48。ほかは既存の
   問い・既存のコード（ひのとりの RD9・Z23、へんなこな・ミラクルかふん・ようかいえき・ゆうわく・げんかくおんぱの HC3・T19b、シードラのみずでっぽうの HC4、
   まねるワザの HC9、2 匹の「とうめい」の T27、v0.3b のマヒの再付与）で、新しい問いを加えていない（6 章）。
4. 既存の不具合を 1 つ直した: ダメージの要素のあとのワザ全体のコイン（v0.37 のニャースの「ねこにこばん」）を、「はんげき」などの「ダメージを受けたとき」の効果を
   持つ相手に使うと、v0.40 までは内部エラー（`RuntimeError`）になっていた。「ダメージを受けたとき」の効果をコインの前に処理するようにした（3.5 節）。

開始の時点で、作業ツリーに未コミットの変更はなく、`claude/v0.40-count-condition-switch-return` は `cbc5515`（版 0.40.0）のままでした（リモートに v0.41 の
ブランチはない）。ガイドブック（『オフィシャルブック2000』）のキャプチャ・OCR・画像の読み直しは行っていません。読んでいない原典を確かめたことにする記録は
作っていません。足りない裁定を現代のルールから推測して決めていません。今回の作業に関係しない未解決と、保留中のガルーラ（PMCG2-046）・ベロリンガは再調査して
いません。研究の基準（kyuura `3f34908`）・写しの元（`ecb2d69`）・固定した参照データ・公開の固定のデッキは変えていません。`engine.py`・`resolution/` にカード id での
分岐を加えていません（tests/test_heal_counter_status_v0_41.py の `test_no_card_specific_branch_in_the_engine`）。

## 1. カードごとの結果

15 枚とも対応にしました。どのワザも登録し、ワザの一部だけの登録はありません。15 枚とも kyuura データの採用（`card_sources.json` の `basis: kyuura_data`）で、
処理に使う文面は kyuura の印刷の文面です（研究の基準のコミットに、15 枚を指す kyuura の最新の説明・エラッタ・裁定・論点・照合の記録はない。`kyuura_records` は
15 件とも空。カツラのファイヤーは、R団のファイヤー（PMCG5-020）の照合の記録 CC-PMCG5-020-P82 の `not_confused_with` に名前が出るだけで、このカードの記録では
ない）。説明文のある 26 のワザを研究の対応表の `adopted_printed_text` に加えました。説明文のない 3 つのワザ（ずつき・ひっかく・サイコバーン）は `DamageOnly` です。

| カード | id | 版（pcg-search.com の一覧の番号） | ワザ | 実装 | 結果 |
|---|---|---|---|---|---|
| クサイハナ | PMCG2-009 | ポケモンジャングル 006/048 | どくのこな（草）・くさいにおい（草草）20 | `PoisonWithoutDamage`・`DamageThenConfuseBoth` | 対応（ナゾノクサ PMCG2-002 から進化。エリカのクサイハナとは別の名前） |
| ウツボット | PMCG2-016 | ポケモンジャングル 014/048 | さそうかおり（草）・ようかいえき（草草）20 | `SwitchOpponentActive`（v0.31 のかどわかすと同じ型）・`DamageThenRetreatLockOnHeads` | 対応（ウツドン PMCG2-011 から進化する 2 進化。エリカのウツドンからは進化できない） |
| シードラ | PMCG3-020 | 化石の秘密 019/048 | みずでっぽう（水無）20+・こうそくいどう（水無無）20 | `ExtraEnergyDamageMixed(水, 10, 2)`（v0.31）・`DamageThenSelfBarrierOnHeads`（v0.34） | 対応（タッツー PMCG3-014 から進化。カスミのシードラ・カスミのタッツーとは別の名前。2 章） |
| わるいペルシアン | PMCG4-048 | ロケット団 048/065 | ゆうわく（無）・どくのつめ（無無）10 | `SwitchOpponentActiveOnHeads`・`PoisonOnHeads` | 対応（ニャース PMCG2-036 から進化。ペルシアン・サカキのニャースとは別の名前） |
| カツラのファイヤー | PMCG6-035 | 闇からの挑戦 035/098 | ひのとり（炎炎炎炎炎）90 | `DamageThenReturnSelfToDeckOnTails` | 対応（ワザは 1 つ。ファイヤー PMCG3-009・R団のファイヤーとは別の名前） |
| ヤドン | PMCG4-032 | ロケット団 034/065 | ひなたぼっこ（無）・ずつき（超）10 | `AttachEnergyFromDeckToSelf(超)`・`DamageOnly` | 対応（化石の秘密のヤドン PMCG3-027・ナツメのヤドンとは別のカード） |
| エリカのナゾノクサ | PMCG5-002 | リーダーズスタジアム 006/096 | ちょっとすいとる（草）10・たまにすいとる（草無）20 | `DamageThenHealSelf(1)`・`DamageThenHealSelf(1, on_heads=True)` | 対応（HP 50。同じ名前の PMCG5-003 とは別のカード） |
| エリカのナゾノクサ | PMCG5-003 | リーダーズスタジアム 005/096 | へんなこな（草）10 | `DamageThenStatusByCoin(こんらん, ねむり)` | 対応（HP 40。ワザは 1 つ） |
| エリカのクサイハナ | PMCG5-009 | リーダーズスタジアム 007/096 | ヒーリングかふん（草）・ミラクルかふん（草草草）30 | `CoinHealSelf(4)`・`DamageThenChosenStatusOnHeads` | 対応（どちらのエリカのナゾノクサからも進化。クサイハナとは別の名前） |
| ナツメのコダック | PMCG6-036 | 闇からの挑戦 037/098 | ひっかく（無）10・こまったねんりき（超）20 | `DamageOnly`・`CoinDamageAndConfuseElseSelfConfuse` | 対応（コダック PMCG4-019・カスミのコダックとは別の名前） |
| ナツメのゴルダック | PMCG6-038 | 闇からの挑戦 038/098 | ダメージシフト（超超）・ウォーターシュート（水無無）20+ | `MoveOwnCountersToOpponent`・`CoinBonusDamage(20)` | 対応（ナツメのコダックから進化） |
| ナツメのモルフォン | PMCG6-022 | 闇からの挑戦 004/098 | かいふくりんぷん（草）・げんかくおんぱ（超）10 | `CoinsHealOwnPokemon(3)`・`DamageThenConfuseOnAnyHeads(2)` | 対応（ナツメのコンパン PMCG6-006 から進化） |
| ナツメのヤドラン | PMCG6-048 | 闇からの挑戦 048/098 | いねむり（超）・きあいずつき（超無無）40 | `CoinHealSelf(3, then_sleep=True)`・`DamageThenLockSelf` | 対応（ナツメのヤドン PMCG6-044 から進化。化石の秘密のヤドン・ロケット団のヤドンからは進化できない） |
| エリカのプリン | PMCG5-058 | リーダーズスタジアム 064/096 | みんなでかいふく（無）・やさしいパンチ（無無）40- | `HealAllPokemonBothSides(1)`・`DamageMinusIfDefenderDamaged(30)` | 対応（プリン PMCG2-035 とは別の名前） |
| R団のミュウツー | PMCG6-055 | 闇からの挑戦 043/098 | チェンジダメージ（超）・さいみんはどう（超超）20・サイコバーン（超超超無）60 | `SwapCountersOnHeads`・`DamageThenSleepOnHeads`・`DamageOnly` | 対応（ミュウツー PMCG1-050 とは別の名前） |

## 2. カードデータと pcg-search.com との照合

- 写しは既存の手順（`python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura`）で作り直しました（組 `pool_v0_41`。参照するコミット `ecb2d69` は変えていない）。
  ほかのカードの記録は変わっていません。15 枚とも kyuura の日本語の文面の出典（`ja_text_source`）は pcg-search.com ではありません（nazonobasho.com・ポケモン
  wiki）ので、pcg-search.com との照合は独立した照合です。
- pcg-search.com の同じ版のページと照合しました（2026-10-16。照合した欄は名前・段階・HP・タイプ・弱点・抵抗力・にげる・ワザの名前・エネルギー・ダメージ・
  説明文。カードの画像は読んでいない）。版はカード名だけでなく、収録とサイトの一覧の番号・HP・ワザで決めました。同じ名前のエリカのナゾノクサ 2 枚は、HP とワザで
  サイトの版を決めました（005/096 は HP 40・へんなこな、006/096 は HP 50・ちょっとすいとる。一覧の番号が kyuura の id の番号と逆になる）。ヤドン 034/065・
  ナツメのモルフォン 004/098・R団のミュウツー 043/098 など、サイトの一覧の番号が kyuura の id の番号と違うカードがあります。14 件は `match`、1 件は `differences`
  （処理に影響しない。`affects_behavior: false`）です。
  - シードラのみずでっぽう: サイトのかっこは半角「(ダメージ追加は2つぶんまで)」、kyuura は全角（記号の違い）。
- 採用の記録（`card_sources.json`）は 15 件 `adopted`（`kyuura_commit` は `ecb2d69`、記録した日は 2026-10-16、説明文のあるワザの `play_text` は
  `kyuura_printed_text`）。過去の原典照合の記録（`card_verification.json`）には加えていません。ガイドブックの項目は書いていません。

## 3. 共通の処理

### 3.1 新しく加えた型

どれも解決の基盤の要素の並び（`programs.BUILDERS`）で処理し、v0.13 の約束（`resolve`・`resume`）は上書きしていません。`v013_checks.VERIFIED` には入れず、
tests/helpers.py の `ATTACK_TYPES_SINCE_V0_17` に加えました（18 の型）。型の `check` は、登録したワザの印刷の文面と同じ書き方だけを受け付けます（`TextTest`）。

| 型 | 要素の並び | 使うワザ |
|---|---|---|
| `DamageThenHealSelf(counters, on_heads)` | `Damage(相手)` → `HealCounters(counters, 自分, 要素のコイン おもて（on_heads のとき）)` | ちょっとすいとる・たまにすいとる |
| `CoinHealSelf(counters, then_sleep)` | `Coin` → `HealCounters(counters, 自分, おもて)`（→ `Status(ねむり, 自分, おもて)`） | ヒーリングかふん・いねむり |
| `CoinsHealOwnPokemon(coins)` | `Coin(coins 枚)` → `HealCounters(「おもて」の数, 自分の場の全員)` | かいふくりんぷん |
| `HealAllPokemonBothSides(counters)` | `HealCounters(counters, お互いの場の全員)` | みんなでかいふく |
| `MoveOwnCountersToOpponent` | `ShiftCountersToOpponent()` | ダメージシフト |
| `SwapCountersOnHeads` | `Coin` → `SwapCounters(おもて)` | チェンジダメージ |
| `DamageThenConfuseBoth` | `Damage(相手)` → `Status(こんらん, 相手)` → `Status(こんらん, 自分)` | くさいにおい |
| `DamageThenStatusByCoin(heads, tails)` | `Damage(相手)` → `Status(heads, 要素のコイン おもて, otherwise=tails)` | へんなこな |
| `DamageThenChosenStatusOnHeads` | `Damage(相手)` → `ChosenStatus(要素のコイン おもて)` | ミラクルかふん |
| `CoinDamageAndConfuseElseSelfConfuse` | `Coin` → `Damage(相手, おもて)` → `Status(こんらん, 相手, おもて)` → `Status(こんらん, 自分, うら)` | こまったねんりき |
| `DamageThenConfuseOnAnyHeads(coins)` | `Damage(相手)` → `Coin(coins 枚)` → `Status(こんらん, 相手, 「おもて」が 1 枚以上)` | げんかくおんぱ |
| `DamageThenSleepOnHeads` | `Damage(相手)` → `Status(ねむり, 要素のコイン おもて)` | さいみんはどう |
| `DamageThenRetreatLockOnHeads` | `Damage(相手)` → `OpponentRetreatLock(要素のコイン おもて)` | ようかいえき |
| `SwitchOpponentActiveOnHeads` | `ForceSwitch(ワザを使ったプレイヤーが選ぶ, 要素のコイン おもて, required)`（相手に控えがいることは実装の `usage_problem`） | ゆうわく |
| `DamageThenReturnSelfToDeckOnTails` | `Damage(相手)` → `ReturnSelfToDeck(うら, ダメージを与えた後)` | ひのとり |
| `AttachEnergyFromDeckToSelf(energy_type)` | `AttachFromDeck(energy_type)` | ひなたぼっこ |
| `DamageThenLockSelf` | `Damage(相手)` → `SelfAttackLock(コインなし)` | きあいずつき |
| `DamageMinusIfDefenderDamaged(reduction)` | `Damage(相手, PrintedMinusIfDefenderDamaged(reduction))` | やさしいパンチ |

既存の型の登録: どくのこなは `PoisonWithoutDamage`（v0.8）、さそうかおりは `SwitchOpponentActive`（v0.31 のかどわかす）、シードラのみずでっぽうは
`ExtraEnergyDamageMixed`（v0.31）、こうそくいどうは `DamageThenSelfBarrierOnHeads`（v0.34 のギャロップ）、どくのつめは `PoisonOnHeads`、ウォーターシュートは
`CoinBonusDamage(20)`、説明文のない 3 つは `DamageOnly`。

既存の型が受け付ける書き方（v0.37 の約束。意味が同じと記録・印刷の文面で確かめた書き方だけ）に、次の 3 つを加えました。

- `SwitchOpponentActive`: さそうかおりの「相手の控えポケモンを選び、相手の対戦ポケモンと入れ替える。」（かどわかすの「選んで」と同じ処理）。v0.40 までは形だけを
  確かめていたので、v0.41 から 2 つの書き方だけを受け付けます（`SWITCH_OPPONENT_ACTIVE_TEXTS`）。
- `DamageThenSelfBarrierOnHeads`: シードラのこうそくいどうの「…ワザによるダメージや効果を受けない。」（v0.37 のしんだふりと同じ書き方。「ワザをうけない」状態）。
- `ExtraEnergyDamageMixed`: シードラのみずでっぽうの「…多いエネルギー1つにつき10ダメージを追加する。（ダメージ追加は2つぶんまで）」。

### 3.2 要素・値に加えた項目と新しい要素

- 新しい要素 `HealCounters`（回復）: `scope` は `HEAL_SELF`（ワザを使ったポケモン）・`HEAL_OWN_ALL`（自分の場の全員。バトル場 → ベンチ）・`HEAL_BOTH_ALL`
  （ワザを使ったプレイヤーの場 → 相手の場）。とりのぞく数は `counters`（決まった数）か `heads_of`（ワザ全体のコインの「おもて」の数。どのポケモンにも同じ数）で、
  それぞれのっている数まで。0 個のポケモンからはとりのぞかず、効果を受けない（「とうめい」も評価しない）。とりのぞくポケモンごとに、効果を受ける前に「ワザをうけない」
  状態・「とうめい」を評価する（`reaches`。要素の種類 `heal`）。ログはとりのぞいたポケモンごとに `attack_heal`（v0.31 のぼーっとすると同じ形。相手のポケモンなら
  `attacker` を加える）。
- 新しい要素 `ShiftCountersToOpponent`（ダメージシフト）・`SwapCounters`（チェンジダメージ）: ダメージの処理（`kernel.deal_damage`）を通さず、ダメージカウンターの数を
  変える（要素の種類 `damage_counters`。ログ `place_damage_counters`・`swap_damage_counters`）。そのあと HP 以上になったポケモンは、きぜつの原因の枠を記録し
  （`kernel.track_ko`。同時のきぜつの判定）、きぜつの判定で「こんじょう」を使えない（`ko_prevention_able` を偽にする）。
- 新しい要素 `ChosenStatus`（ミラクルかふん）と決定 `decisions.SELECT_SPECIAL_CONDITION`（選べるものは `effects.CHOSEN_CONDITIONS` = ねむり・マヒ・こんらん・どく の
  番号 0〜3。1 つ）。決定をまたいで枠の値（「とうめい」の結果など）を運ぶ（`carry`）。マヒの再付与で回復する番が変わる場合は、マヒを選べるが選ぶと止める
  （`unresolved_choices`）。先読みは、止める答えを除くすべての答えを試す。
- 新しい要素 `AttachFromDeck`（ひなたぼっこ）と決定 `decisions.ATTACH_FROM_DECK`（選べるものは山札の「超」の基本エネルギーカード。uid の小さい順。0〜1 枚）・
  `zones.attach_from_deck`（山札 → ワザを使ったポケモン）。ログ `attach_energy_from_deck`（つけたカードは公開）・`attach_energy_from_deck_none`（`reason` は
  `declined`・`no_candidates`）。どの場合も、そのあと山札を切る（v0.40 の `shuffle_in_attack`。先読みでは切らない）。つけたあと `effects.after_energy_attached` を呼ぶ
  （v0.31 の「ほのおでかいふく」などのエネルギーカードをつけたときの効果）。
- 新しい値 `PrintedMinusIfDefenderDamaged(reduction)`（やさしいパンチ。p.321 の 1 段階）。
- `AttackRun.coin_is` の面に `AtLeast(count)`（ワザ全体のコインの「おもて」の数が `count` 以上。げんかくおんぱ）を加えた。「おもて」の数だけを使うので、先読みは
  「おもて」の数でまとめて試せる（v0.35）。
- `Status.has_target` を加えた: 対象（相手の対戦ポケモン・自分）がこのワザの中で HP 以上なら、処理の対象がない（ダメージの要素のあとのワザ全体のコインが、決める
  要素のどれにも対象がなければ投げない。v0.38 の `Coin`。げんかくおんぱ）。対象がこんじょうを使えるなら G37 で止める。v0.40 までの型でこの値を使うのは、コインが
  ダメージの要素より前にあるワザだけで、そこでは対象はまだ HP 以上にならないので、動作は変わらない。
- `SelfAttackLock.local_coin` に `None`（コインを投げずにいつも与える。きあいずつき）、`OpponentRetreatLock.local_coin`（ようかいえき。既定 `None` は v0.36 と同じ）を
  加えた。

### 3.3 ログ・決定・状態

- 決定の種類 `select_special_condition`・`attach_from_deck` を加えました（段階・再開先・コマンドは同じ。再開先 `"attack"`）。書き出しの形式は 10 のままです。
- 新しいログのイベントは `place_damage_counters`・`swap_damage_counters`・`attach_energy_from_deck`・`attach_energy_from_deck_none`。回復は既存の `attack_heal` を
  ポケモンごとに出します（v0.31 は 1 回のワザに 1 回だけ）。
- 状態の型・持続する効果の型は加えていません（ようかいえきは v0.36 の `CannotRetreat`、きあいずつきは v0.35 の `CannotUseOwnAttack`、こうそくいどうは v0.31 の
  `AttackBarrier`）。
- ログの監査（tests/log_audit.py）: `attack_heal` を、登録の実装でとりのぞいてよいポケモン（自分だけ・自分の場・お互いの場）・前のダメージ・数で確かめ、1 回の
  ワザで同じポケモンから 2 回とりのぞかないことを確かめる（ポケモンごと）。`place_damage_counters`（同じワザでとりのぞいた数と同じ・相手の対戦ポケモン）・
  `swap_damage_counters`（取り替える前の双方の数）・`attach_energy_from_deck`（ワザを使ったプレイヤーの山札の、登録のタイプの基本エネルギーカード。すぐあとに
  山札を切る）を組み立て直し、回復・のせる・取り替える効果を、相手のポケモンが受ける効果として「とうめい」の判定と照らす。ダメージの要素のあとのコインが
  ダメージ以外の効果だけを決めるワザ（`EFFECT_COIN_AFTER_DAMAGE`）に、v0.41 の 6 つの型とねこにこばんを加えた（「はんげき」はそのコインより先）。

### 3.4 再利用したもの

- v0.36 の `ReturnSelfToDeck`・RD9（ひのとり）、v0.36 の `CannotRetreat`（ようかいえき）、v0.35 の `CannotUseOwnAttack`（きあいずつき）、v0.34 の `AttackBarrier`・
  `void_coin_question`・`carry`（こうそくいどう・決定をまたぐ値）、v0.31 のかどわかす（さそうかおり・ゆうわく）・`ExtraEnergyDamageMixed`（HC4）・HC3・HC9、
  v0.38 の `ForceSwitch.local_coin`・`Coin.has_target`、v0.40 の `shuffle_in_attack`、v0.35 の「おもて」の数でまとめる先読み、v0.17b の Z23、v0.9 の「とうめい」・
  T4・T8・T27・T19b、v0.11 の G37、v0.3b のマヒの再付与の問い、v0.3c のこんらん、v0.31 の `after_energy_attached`。
- 今回のカード群に必要な処理で、残したエンジンの制限は、まねるワザのきあいずつき（7 章）だけです。

### 3.5 既存の不具合の修正（ダメージのあとのワザ全体のコインと「ダメージを受けたとき」の効果）

v0.37 のニャース（PMCG2-036）の「ねこにこばん」（ダメージ → コイン → 引く）を、カイリキーの「はんげき」などの「ダメージを受けたとき」の効果を持つポケモンに
使うと、v0.40 までは `programs.run_elements` が「ワザ全体のコイン・確認は、ダメージの要素より前に置く」の `RuntimeError`（内部エラー）で止まっていました。
「ダメージを受けたとき」の効果は、そのワザのダメージの処理のあと・ダメージ以外の効果（効果を決めるワザのコインを含む）の前に処理する（CR-COUNTERATTACK-TIMING・
CR-FIRE-WALL-TIMING・CR-SHELL-ATTACK-TIMING。エンジンの v0.10・v0.12・v0.13）ので、ダメージの要素のあとのワザ全体のコインのうち、あとにダメージの要素がない
もの（ダメージ以外の効果だけを決めるコイン）の前に、その効果を処理するようにしました。あとにダメージの要素があるコインは今までどおりエンジンの不具合として
止めます（今の対応カードにはない）。v0.41 のげんかくおんぱも同じ並びです。

- 影響の範囲: ねこにこばん・げんかくおんぱを、「ダメージを受けたとき」の効果がはたらいている相手に使う場合だけ（v0.40 までは内部エラーで、受け付けた結果は
  なかった）。ほかの場合の動作は変わりません（10.2 節の比較）。
- テスト: tests/test_heal_counter_status_v0_41.py の `CoinAfterDamageTest`（ログの `counterattack` が `coin_flip` より前・効果・引く枚数・「はんげき」で HP 以上に
  なっても相手への効果のコインは投げる）。

## 4. 規定と根拠

どれも既存の記録の再利用と印刷の文面で決めました（ガイドブックは読んでいない）。記録で決まらない場面は 5 章の CX1 と、6 章の既存の問いだけです。「実装上の判断」は、
印刷の文面の読み方としてエンジンが決めたもので、原典で確かめた規定ではありません。

| id | 規定 | 根拠 | テスト |
|---|---|---|---|
| HL1 | 回復はダメージカウンターをとりのぞくこと。とりのぞくのはのっている数まで（10 ずつ）。0 個のポケモンからはとりのぞかない（効果を受けない） | GR-2000-P320-RECOVERY（「すべてのダメージカウンターをとりのぞいたら、それ以上の回復はできない」） | `HealTest.test_little_drain_removes_one_after_the_damage`・`test_healing_pollen_removes_up_to_four` |
| HL2 | 説明に「ダメージを与えたら」のない回復（ちょっとすいとる・たまにすいとる・いねむりなど）は、相手にダメージを与えなくても（「ダメージを受けない」状態・「ワザをうけない」状態・最終ダメージ 0）回復する。やどりぎのタネ（`Drain`）の条件を付けない | 印刷の文面（説明に書かれた条件だけ）。GR-2000-P321-PREVENTED-ELEMENTS（「ダメージを受けない」状態はダメージの要素だけを無効にする） | `test_little_drain_does_not_need_to_deal_damage`・`test_occasional_drain_only_on_heads_and_flips_against_a_barrier` |
| HL3 | 自分を回復するワザで、自分がこのワザの中で HP 以上（相手の「はんげき」など）なら、処理の対象がないのでとりのぞかない（コインも投げない。ログ `effect_skipped`）。そのあと、きぜつする | GR-2000-P309-ATTACK-PROCEDURE（処理の対象がなくなった内容は無視する）。v0.31 の `HealSelfOnHeads` と同じ | `test_no_heal_when_the_attacker_is_knocked_out_by_counterattack` |
| HL4 | いねむり: 「おもて」なら 3 つとりのぞき、そのあと自分をねむりにする。カウンターがのっていなくても（回復の処理の対象がない）、ねむりの内容は処理する。もとのどくは残る | GR-2000-P309-ATTACK-PROCEDURE（対象がなくなった内容だけを無視して、次の内容を処理する）。p.322（どくはほかの特殊状態と重なる） | `test_doze_heals_three_then_sleeps` |
| HL5 | かいふくりんぷん: コイン 3 枚を 1 度だけ投げ、「おもて」の数ぶんを自分と控えの全員から、それぞれとりのぞく（ポケモンごとに投げ直さない。のっている数まで）。相手のポケモンはとりのぞかない | 印刷の文面（「コインを3枚投げ、「おもて」の数ぶんのダメージカウンターを…それぞれ」） | `test_healing_scales_same_heads_for_every_own_pokemon` |
| HL6 | みんなでかいふく: お互いの場のポケモン全員から 1 つずつ。相手のポケモンの回復も効果の要素で、相手の対戦ポケモンが「ワザをうけない」状態なら、そのポケモンだけとりのぞかない。「ダメージを受けない」状態は関係しない | 印刷の文面（「お互いの場にいるポケモン全員から、それぞれ」）。v0.31 の効果の要素の無効。GR-2000-P321-PREVENTED-ELEMENTS | `test_heal_everyone_removes_one_from_both_sides`・`test_heal_everyone_and_protection` |
| HL7 | 回復の効果を受けるポケモンの「とうめい」は、とりのぞくカウンターがあるときだけ、持ち主がコインを投げて判定する（自分のワザでもはたらく）。とりのぞくポケモンのうち 2 匹以上が「とうめい」を持つなら T27 で宣言の前に止める | v0.9 の T8（自分のワザの効果にもはたらく）・T21（効果を受けないなら判定しない）・T27・T33 | `test_transparency_of_an_own_pokemon_is_evaluated_only_when_healing`・`test_heal_everyone_and_protection` |
| MV1 | ダメージシフト: 自分と自分の控え全員のうち、カウンターがのっているポケモンから 1 つずつ（ワザを使ったポケモン → ベンチの順）とりのぞき、とりのぞいた数のカウンターを相手の対戦ポケモンにのせる（1 回）。移すカウンターがなければ何もしない | 印刷の文面（「それぞれ」ではなく「ダメージカウンターを1つずつとりのぞき、とりのぞいたダメージカウンターをすべて、相手にのせる」） | `CounterShiftTest.test_removes_one_from_each_and_places_the_total`・`test_nothing_to_move` |
| MV2 | のせるのはダメージカウンターの移動で、ワザのダメージではない: 弱点・抵抗力・プラスパワー・ディフェンダーを計算せず、「ダメージを受けない」状態でものせる。相手の「はんげき」などの「ダメージを受けたとき」の効果ははたらかない | GR-2000-P320-COUNTER-MOVE（ダメージカウンターの移動は「ダメージを受けた」ことにならない。エンジンの v0.7 の S19） | `test_not_damage_so_no_damage_calculation_or_trigger` |
| MV3 | のせたカウンターで HP 以上になった相手は、ワザのあとにきぜつする（サイドはワザを使ったプレイヤー）。相手のワザのダメージで HP 以上になったのではないので、「こんじょう」は使えない | p.309・p.324（きぜつはワザのあと）。v0.11 の G3〜G7 | `test_knock_out_after_the_attack_without_guts` |
| MV4 | 自分の控えのゴーストからとりのぞく前に、その「とうめい」を判定する。受けなければ、そのポケモンからはとりのぞかず、のせる数にも数えない | v0.9 の T8。印刷の文面（「とりのぞいたダメージカウンターをすべて」） | `test_own_transparency_is_evaluated_before_removing` |
| XC1 | チェンジダメージ: 「おもて」なら、ワザを使ったポケモンと相手の対戦ポケモンのカウンターを、取り替える前の双方の数で取り替える（片方を変えてから、変えたあとの数をもう片方に渡さない）。数が同じなら何もしない | 印刷の文面（「…すべてと、…すべてを、取り替える」） | `SwapTest.test_swaps_the_values_before_the_swap`・`test_equal_counters_change_nothing` |
| XC2 | どちらも「ダメージを受けた」ことにならない（計算しない・「ダメージを受けない」状態・ディフェンダーは関係しない・「はんげき」ははたらかない）。取り替えたあと HP 以上のポケモンは、ワザのあとにきぜつする。両方がそろって HP 以上になることはない（自分の HP ≤ 相手の取り替える前の数 < 相手の HP ≤ 自分の取り替える前の数 < 自分の HP は成り立たない） | GR-2000-P320-COUNTER-MOVE。p.309・p.324 | `test_knock_out_of_either_side`・`test_not_blocked_by_damage_prevention` |
| SS1 | くさいにおい: 相手をこんらん → 自分をこんらん。相手がこのワザのダメージで HP 以上なら相手の効果だけを飛ばし、自分はこんらんになる。相手が「ワザをうけない」状態でも自分の効果は処理する | 印刷の文面（「その後、自分も」）。GR-2000-P309-ATTACK-PROCEDURE | `StatusTest.test_foul_odor_confuses_both` |
| SS2 | へんなこな: 1 枚のコインで、「おもて」ならこんらん・「うら」ならねむり（投げ直さない）。相手への効果だけを決めるコインなので、「ワザをうけない」相手には HC3、「とうめい」で受けないと決まった相手には T19b | 印刷の文面。v0.34 のくさいガス（`Status.otherwise`）・`void_coin_question` | `test_strange_powder_one_coin_decides_which` |
| SS3 | ミラクルかふん: 「おもて」なら、ワザを使ったプレイヤーが「ねむり・マヒ・こんらん・どく」から 1 つを選び、相手をその状態にする（実装上の判断: 「選び」の主語はワザを使ったプレイヤー。かどわかすなどの説明の「選び」と同じ）。選んだ状態の重なり・置きかえは p.322 のとおり | 印刷の文面。p.322 | `test_miracle_pollen_each_choice`・`test_miracle_pollen_tails_has_no_choice` |
| SS4 | ミラクルかふんの決定: 番号の外・0 個・2 個・ほかのプレイヤーの答えは状態を変えずに拒否し、決定は待ったまま。決定を待つ状態を保存して再開しても同じ。マヒの再付与で回復する番が変わる場合は、マヒを選べるが選ぶと止める（v0.3b の問い） | v0.2a の決定の約束。v0.3b（`UNRESOLVED_REPARALYSIS_RECOVERY_TURN`） | `test_miracle_pollen_invalid_answers_and_save_restore`・`test_miracle_pollen_reparalysis_choice_is_held` |
| SS5 | こまったねんりき: 1 枚のコインで、「おもて」なら相手に 20 とこんらん、「うら」なら相手にダメージを与えず（ダメージの要素がない）、自分をこんらん。自分への効果も決めるコインなので、相手が「ワザをうけない」状態でも投げる | 印刷の文面。v0.34 の `void_coin_question` | `test_troubled_telekinesis`・`test_troubled_telekinesis_against_transparency` |
| SS6 | げんかくおんぱ: ダメージのあと、コイン 2 枚の 1 枚でも「おもて」なら相手をこんらん（2 枚とも投げる）。相手の「はんげき」はコインより先（3.5 節）。相手がこのワザで HP 以上なら投げない | 印刷の文面。CR-COUNTERATTACK-TIMING。GR-2000-P309-ATTACK-PROCEDURE | `test_illusion_wave_any_heads_of_two`・`test_illusion_wave_flips_no_coin_without_a_target`・`CoinAfterDamageTest` |
| SS7 | ようかいえき: 「おもて」なら、相手の対戦ポケモンは次の相手の番に「にげる」ことができない（v0.36 の `CannotRetreat`。拒否のコード `RETREAT_PREVENTED`）。相手がこのワザで HP 以上なら投げない。「ワザをうけない」相手には HC3、「とうめい」で受けないと決まった相手には T19b | 印刷の文面。v0.36 の RL1〜RL5 | `RetreatLockOnHeadsTest` |
| LU1 | さそうかおり: ワザを使ったプレイヤーが相手の控えを選び、入れ替える（コインなし）。相手に控えがいなければ何もしない（使うための条件ではない） | 印刷の文面。v0.31 のかどわかす | `LureTest.test_sweet_scent_attacker_chooses` |
| LU2 | ゆうわく: 「(相手に控えがいない時、このワザは使えない)」はワザを使うための条件（コインの前に `NO_OPPONENT_BENCH`）。「おもて」なら、ワザを使ったプレイヤーが選んで入れ替える | 印刷の文面。v0.38 ののびるキック・v0.40 のひきずりだす | `test_lure_requires_bench_and_heads` |
| PH1 | ひのとり: 「うら」なら、ダメージを与えた後、自分とついているすべてのカードを山札にもどし、山札を切る（v0.36 のくもがくれガスの面を「うら」にしたもの）。きぜつではない（サイドはない）。空いたバトル場は既存の決定で出す。控えがいなければ負け | 印刷の文面。v0.36 の RD1〜RD8 | `PhoenixFlameTest.test_tails_returns_everything_and_promotes`・`test_no_bench_loses_after_returning` |
| SN1 | ひなたぼっこ: 山札の「超」の基本エネルギーカードを 1 枚選び、ワザを使ったポケモンにつけてよい（0〜1 枚）。山札から直接つける（手札を通さない）。手札からつける通常の操作（p.310 の 1 番に 1 枚）・特殊能力でつけた枚数には数えない | 印刷の文面（「自分の山札から…選び出し、このカードにつけてよい」） | `SunbathTest.test_choose_one` |
| SN2 | つけた・つけない・選べるものがない、のどれでも、そのあと山札を切る（実装上の判断: 「その後、その山札をよく切る」は、山札を見た場合のすべて）。選べなかった山札の中身はログに書かない | 印刷の文面 | `test_decline_and_no_candidates_still_shuffle`・`test_invalid_answers` |
| FH1 | きあいずつき: 40 のあと、次の自分の番にこのカードは「きあいずつき」を使えない（v0.35 の `CannotUseOwnAttack`。コインなし。拒否のコード `ATTACK_LOCKED`。ほかのワザは使える） | 印刷の文面。v0.35 のあわあわ | `HeadbuttLockTest.test_locked_on_the_next_own_turn_only` |
| GP1 | やさしいパンチ: 相手の対戦ポケモンにダメージカウンターがのっていれば、基本となるダメージは 40 − 30（p.321 の 1 段階。数に比例しない）。控えのカウンターは見ない | 印刷の文面。p.320 の「相手」（v0.40 のつのでえぐるの HD1 と同じ見方） | `PulledPunchTest` |
| SE1 | シードラ: みずでっぽうは v0.31 の `ExtraEnergyDamageMixed`（必要なエネルギーに無色。無色を払える「水」が多いときは HC4）。こうそくいどうは「ワザをうけない」状態（v0.34 のギャロップと同じ `AttackBarrier`） | v0.31 の HC4。v0.34。v0.37（書き方） | `SeadraTest` |

## 5. CX1: ダメージシフト・チェンジダメージで、相手がその効果を受けない場合

| 項目 | 内容 |
|---|---|
| 問い | ナツメのゴルダックの「ダメージシフト」（自分の側からとりのぞいて相手にのせる）・R団のミュウツーの「チェンジダメージ」（自分と相手のカウンターを取り替える）で、相手の対戦ポケモンがその効果を受けない（「ワザをうけない」状態・「とうめい」）とき、自分の側（自分と控えからとりのぞく・自分のカウンターの数を変える）を処理するか |
| 記録で確かめたこと | kyuura の研究の基準のコミット（`3f34908`）に、ダメージシフト・チェンジダメージ・2 枚のカードを指す記録はない。GR-2000-P320-COUNTER-MOVE はダメージカウンターの移動が「ダメージを受けた」ことにならないことを書くが、移動の片方の側が効果を受けない場合を書かない。GR-2000-P309-ATTACK-PROCEDURE は処理の対象がなくなった内容を無視することを書くが、1 つの内容（とりのぞいてのせる・取り替える）の一部の対象だけが効果を受けない場合を書かない。エンジンの記録のダメージスワップ（v0.7）は自分の場の中の移動で、相手が受けない場合がない |
| 決まらない理由 | 2 通りの読み方がある。(a) 1 つの効果なので、相手が受けなければ全体を処理しない（自分の側も変わらない）。(b) 自分の側への処理は自分のポケモンへの効果なので処理し、相手への部分だけが無効（ダメージシフトはとりのぞいたカウンターが消える、チェンジダメージは自分だけが相手の数になる）。どちらを選んでも、自分のポケモンのダメージ（ときにはきぜつ）が変わる。現代のルールからも推測しない |
| 処理 | 宣言の前に止める（`UnsupportedError`。`UNRESOLVED_COUNTER_TRANSFER_PROTECTED`。問い `counter_transfer_protected`）。「ワザをうけない」状態は、とりのぞく・取り替える前に確かめる。「とうめい」はのせる・取り替える効果を受けるときのコインで決まるので、先読みが（コインのすべての結果を試して）受けない結果を見つけ、宣言の前に止める（実際のコインが「うら」でも止める。v0.9 の T19b と同じ扱い）。状態・乱数・ログは変わらない |
| 影響の範囲 | 移す・取り替えるカウンターがない（自分の場のどのポケモンにもない・数が同じ）なら、効果を受けるポケモンがないので止めない。相手が「ダメージを受けない」状態（かたまる）・ディフェンダーは関係しない（ダメージではない。MV2・XC2）。チェンジダメージの「うら」は何もしない（先読みが「おもて」を試すので、「ワザをうけない」状態の相手には宣言の前に止まる） |
| 研究の対応表 | `stop_codes` の `UNRESOLVED_COUNTER_TRANSFER_PROTECTED`（`kyuura_disposition: not_in_kyuura`。kyuura の未解決の一覧にない。kyuura への報告事項） |
| テスト | `CounterShiftTest.test_cx1_when_the_opponent_does_not_receive_the_counters`・`SwapTest.test_cx1_when_the_opponent_does_not_receive_the_swap`・`test_equal_counters_change_nothing`・tests/test_unresolved_boundaries_v0_4e.py |

## 6. 既存の問いとの関係（RD9・Z23・HC3・T19b・HC4・HC9・T27・G37・v0.3b・v0.4b）

- **RD9**（v0.36。山札にもどす処理と同じワザで HP 以上になるポケモン）: ひのとりが当たります。90 で相手の対戦ポケモンが HP 以上になりうる場合（コインの両方の結果を
  先読みが試す）は、宣言の前に止めます。対応カードのほとんどの相手が 90 で HP 以上になるので、対戦ではひのとりの多くが RD9 で止まります（8 章）。
- **Z23**（v0.17b。「ダメージを与えた後」の効果で、そのダメージの要素がダメージを与えなかった）: ひのとりが当たります（相手が「ダメージを受けない」状態・
  「ワザをうけない」状態・最終ダメージ 0）。v0.18c のナツメのヤドンの「ぐうたらこうげき」の Z23-b（抵抗力 超）も、今回の対戦のデッキで起こります。
- **HC3・T19b**（相手への効果だけを決めるコイン）: へんなこな・ミラクルかふん・ようかいえき・ゆうわく・げんかくおんぱ・さいみんはどう・どくのつめで、v0.34 の
  `void_coin_question` と v0.38 の要素のコインの確かめのまま当てはまります。たまにすいとる・ヒーリングかふん・いねむり・こまったねんりき・チェンジダメージは、
  自分への効果を決めるコインなので投げます（チェンジダメージは CX1 で止まる）。
- **HC4**（v0.31。必要なエネルギーに無色がまざる「みずでっぽう」）: シードラのみずでっぽうが当たります。
- **HC9**（v0.31。まねるワザで、使うための条件が決められない）: カスミのコダックがゆうわくを、相手に控えがいないときにまねる場合（7 章）。
- **T27**（v0.9。1 つのワザで 2 匹の「とうめい」）: みんなでかいふく・かいふくりんぷん・ダメージシフトで、とりのぞくカウンターがある「とうめい」のポケモンが 2 匹
  以上の場合。
- **G37**（v0.11。こんじょうを使えるポケモンが、同じワザの効果を受ける）: 相手に効果を与える v0.41 の型は `opponent_effect_elements` を宣言しています（回復・
  のせる・取り替える効果も、相手のポケモンへの効果として宣言した）。
- **v0.3b のマヒの再付与**: ミラクルかふんでマヒを選ぶ場合（SS4）。自然な対戦では起こりません。
- **v0.4b**（「ダメージを受けない」相手に、ダメージの量だけを決めるコイン）: ウォーターシュート（`CoinBonusDamage`）で、該当する場面だけ当てはまります。

## 7. まねるワザ

ピクシー・ピッピ（「ゆびをふる」）・カスミのコダック（「ちょうのうりょく」）が、15 枚の 29 のワザをまねる場合を確かめました（`CopyTest`）。

- 29 のワザ × 3 匹のどれも、内部のエラーにならず処理するか、`UNRESOLVED_`・`UNSUPPORTED_` のコードで拒否します。まねたワザの処理のあとも不変条件が通ります。
- まねたワザの「自分」は、まねたポケモンです（ちょっとすいとるの回復・ひなたぼっこでつける先・くさいにおいのこんらん・ダメージシフトでとりのぞく自分の場）。
- ゆうわく（相手に控えがいなければ使えない）を、条件のたりないときにまねる場合は、v0.31 からの約束どおり、ピクシー・ピッピは選べず、カスミのコダックは選べるが
  選ぶと HC9（`UNRESOLVED_COPIED_ATTACK`）です。
- **エンジンの未対応（原典の問いではない）**: きあいずつきは、番をまたぐ効果（`CannotUseOwnAttack`）を、効果を持つポケモンのカードのワザの位置で記録するので、
  相手のワザとして使った効果を表せません。v0.35 からの `UNSUPPORTED_COPIED_ATTACK` で、選べるが選ぶと止めます（`test_headbutt_lock_is_an_engine_limitation`。
  内部エラーにはしない）。

## 8. 対戦

正式な開始（`new_game`・60 枚・サイド 6 枚）からの小規模な対戦で、15 枚の登場・進化・29 のワザと、そのあとの対戦の継続を確かめました
（tests/test_heal_counter_status_v0_41_games.py。`python3 tools/existing_effect_games.py --batch v0.41`）。seed を探し回っていません（最初の 6 つの seed）。
勝率・カードの強さ・デッキの釣り合いは評価していません。

- 検証用デッキ（tools/existing_effect_games.py。公開の固定のデッキ・前の版の検証用デッキには入れていない。同じ名前のカードは合わせて 4 枚まで）:
  - `G41`（草）: ナゾノクサ（第2弾）4・クサイハナ 3・マダツボミ 4・ウツドン 3・ウツボット 2・エリカのナゾノクサ（PMCG5-002・PMCG5-003）2 枚ずつ・
    エリカのクサイハナ 3、トレーナー 12、草エネルギー 25
  - `P41`（超・水）: ナツメのコダック 4・ナツメのゴルダック 3・ナツメのヤドン 4・ナツメのヤドラン 3・ロケット団のヤドン 4・R団のミュウツー 3、トレーナー 12、
    超エネルギー 21・水エネルギー 6
  - `C41`（無色・水）: ニャース 4・わるいペルシアン 3・タッツー 4・シードラ 3・エリカのプリン 4・ラッキー 4、トレーナー 12、水エネルギー 26
  - `R41`（炎・草・超）: カツラのファイヤー 4・ナツメのコンパン 4・ナツメのモルフォン 3、トレーナー 12、炎エネルギー 25・草エネルギー 6・超エネルギー 6
  - トレーナー 12 はどのデッキも、マサキ・ポケモンいれかえ・きずぐすり・プラスパワー・ディフェンダー・突風を 2 枚ずつ。
- 組（`PAIRINGS_V0_41`）: `G41` 対 `P41`・`P41` 対 `C41`・`C41` 対 `R41`・`R41` 対 `G41`・`G41` 対 `P31`（v0.31 のデッキ。ピッピ・ピクシー・カスミのコダックが
  v0.41 のワザをまねる）・`R41` 対 `F37`（v0.37 のデッキ。タケシのイワーク（HP 100）は、カツラのファイヤーの 90 で HP 以上にならない）。席を入れかえて seed 0〜5
  （72 局）。
- 手順: v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順と、使っていないワザのためにエネルギーをためる手順（v0.38 と同じ）を重ね、
  ミラクルかふんの選び方（決定のたびに ねむり・マヒ・こんらん・どく を順に）・ひなたぼっこの選び方（つける・つける・つけない を順に）を加えた（対戦相手の AI では
  ない）。原典で決められない場合・使うための条件・きあいずつきの拒否は、場から確かめてから別の操作を続ける（`V031_STOPS`。v0.41 で CX1 の確かめを加え、Z23 の
  確かめを「ダメージを与えた後」の効果のあるワザすべてに広げ、RD9 の確かめにひのとり・ゆうわくの `NO_OPPONENT_BENCH` を加えた）。

| 終わり方 | 局数 |
|---|---|
| 通常の勝敗（`game_over`） | 70 |
| サドンデス（`sudden_death`） | 0 |
| 既知の裁定による停止（`halted`。対戦準備の `UNRESOLVED_MULLIGAN_COMPENSATION`） | 2 |
| 手数の上限・想定外の拒否・内部エラー・監査の失敗 | 0 |

- 原典で決められない場合でワザの宣言を拒否されたあと、別の操作で続けた回数: RD9 197 回（ひのとり。相手が 90 で HP 以上になりうる）・HC4 25 回（シードラの
  みずでっぽう）・Z23 15 回（ナツメのヤドンのぐうたらこうげきが抵抗力 超 の相手に。ひのとりを含む）・v0.3d の `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` 11 回・
  v0.4b の `UNRESOLVED_PREVENTED_COIN_DAMAGE` 2 回（どれも場から確かめた）。使うための条件などで拒否されたあと続けた回数: きあいずつきの `ATTACK_LOCKED` 26 回・
  ゆうわくの `NO_OPPONENT_BENCH` 3 回ほか。CX1 はこの 72 局では起こりません（作業の途中の別のデッキの構成では 2 回起こった。境界は単体テスト）。
- 15 枚がどれも場に出て（進化先 8 枚は通常の進化の操作で）、29 のワザがどれも使われました。回復（自分・自分の場の全員・お互いの場の全員。みんなでかいふくで相手の
  ポケモンの回復 167 回）、ダメージシフトでのせる（31 回。のせた数はとりのぞいた数と同じ）、チェンジダメージで取り替える（11 回。取り替える前の双方の数）、
  ミラクルかふんの 4 つの状態、くさいにおい・こまったねんりきの自分のこんらん、いねむりの自分のねむり、へんなこなのこんらんとねむり、ようかいえきの「にげる」こと
  ができない効果（55 回）とそれによる「にげる」の拒否、さそうかおり・ゆうわくの入れ替え、ひのとり（4 回。「うら」で山札にもどす 2 回）、ひなたぼっこで山札から
  つける（54 回）・つけない（20 回）・つけるものがない、きあいずつきの効果とそれによる拒否、やさしいパンチの 10・40、さいみんはどうのねむり、こうそくいどうの
  「ワザをうけない」状態が起こりました。どの局も、受け付けた操作の列を `new_game` からやり直したログが同じで、不変条件・ログの監査・書き出しの監査が通りました。

## 9. 互換性

- 公開の API・書き出しの形式（10）・状態の型・持続する効果の型は変えていません。
- 決定の種類 `select_special_condition`・`attach_from_deck` を加えました（v0.40 までの書き出しを読む側は、知らない種類として拒否すること）。
- ログ: 新しいイベント `place_damage_counters`・`swap_damage_counters`・`attach_energy_from_deck`・`attach_energy_from_deck_none`。`attack_heal` は、v0.41 のワザでは
  1 回のワザに何回も出る（ポケモンごと。相手のポケモンなら `attacker`）。v0.40 までのワザのログの形は同じです。
- 既存の動作の変更:
  1. ダメージの要素のあとのワザ全体のコイン（ねこにこばん）を「ダメージを受けたとき」の効果がはたらいている相手に使うと、v0.40 までは内部エラー、v0.41 からは
     効果を処理してからコインを投げる（3.5 節）。
  2. `SwitchOpponentActive`（かどわかす・さそうかおり）の `check` が、登録した 2 つの書き方だけを受け付ける（v0.40 までは形だけ）。登録しているワザは変わらない
     （`TextTest.test_existing_registrations_still_pass`）。
  ほかの既存の型・要素に加えた項目は、どれも既定の値で今までの動作のままです（`SelfAttackLock.local_coin`・`OpponentRetreatLock.local_coin`・`Status.has_target`・
  `AttackRun.coin_is` の `AtLeast`・`SELF_BARRIER_ON_HEADS_TEXTS`・`extra_energy_damage_texts`）。
- ログの監査（テストの道具）は 3.3 節のとおり広げました。v0.40 までのワザでの確かめは同じです。
- 前の版のテストのうち、全体の数・一覧を確かめるテストの期待を、v0.41 の数に直しました（10.4 節）。
- 固定した v0.40 との比較の結果は 10.2 節。

## 10. 検証

### 10.1 テスト

- 単体テスト（tests/test_heal_counter_status_v0_41.py。75 件）: カードの登録と記録・説明の文面・進化（同じ名前・似た名前の取りちがえを含む）・回復（0・1・複数・
  上限・同じコインの複数のポケモン・ダメージを与えない場合・「はんげき」で HP 以上・「とうめい」・T27）・ダメージシフト（ダメージではないこと・きぜつとサイド・
  こんじょう・CX1）・チェンジダメージ（取り替える前の数・きぜつ・CX1）・特殊状態（くさいにおい・へんなこな・ミラクルかふんの決定・不正な答え・保存と再開・マヒの
  再付与・こまったねんりき・げんかくおんぱ・さいみんはどう）・ダメージのあとのコインと「はんげき」（3.5 節）・ようかいえき・さそうかおりとゆうわく・ひのとり・
  ひなたぼっこ・きあいずつき・やさしいパンチ・シードラ・まねるワザ・不変条件と書き出しと保存と拒否の原子性・先読みの 3 つの方法の一致・文書。
- 正式な開始からの対戦（tests/test_heal_counter_status_v0_41_games.py。5 件・72 局）: 8 章。

### 10.2 固定した v0.40 との比較

最終のコードで、固定した v0.40（`cbc5515`。`tools/engine_lockstep.py tree` で展開した木）と、別のプロセスで比べました。比較の差を包括的に許す設定はしていません。

| 比較 | 範囲 | 結果 |
|---|---|---|
| `tools/engine_lockstep.py record --corpus all --seeds 10 --stress-seeds 2 --save-every 7` → `compare` | 290 局・48,092 歩（v0.40 までの自然な対戦・ストレス実行の組。保存と復元 5,068 回を含む） | 食い違い 0・許した差 0 |
| 前の版の検証用デッキの対戦（作業用の道具。各木の公開の API と、その木の tools/existing_effect_games.py だけを読み込み、受け付けた操作の列・最後の状態（形式 10）の指紋・ログ・乱数・拒否の数を比べる） | `--batch` v0.28〜v0.40 の 44 組 × 席の入れかえ × seed 0〜4 = 440 局・53,144 歩 | 違い 0 |
| 3.5 節の修正（ねこにこばんを「はんげき」を持つカイリキーに使う。コイン「おもて」） | 同じ盤面を両方の木で 1 回 | v0.40 は `RuntimeError`（内部エラー）、v0.41 は `counterattack` → `coin_flip` → `draw`（意図した変更） |

3.5 節の修正・`SwitchOpponentActive` の書き方の確かめは、v0.40 までのカードの対戦では違いを生みません（上の比較で違いがないことを確かめた）。

### 10.3 検査

| 検査 | 結果 |
|---|---|
| `python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura --check` | kyuura `ecb2d69` と一致 |
| `python3 scripts/check_card_sources.py` | 記録 182 件。方針と合っている |
| `python3 scripts/check_research_links.py --kyuura ../kyuura` | 研究の基準 `3f34908` の記録と一致 |
| `ruff check --select F,E9 kyuura_engine tests tools scripts` | All checks passed |
| `python3 tools/run_mutants.py check`（変異の定義が今のコードに入るか） | どの変異も ok |

### 10.4 全体のテスト

最終のコードで `python3 -m unittest` を走らせ、2,921 件 OK（skipped 1）でした。その前の 1 回目（v0.41 の文書を書く前・前の版のテストの数を直す前）は、全体の数・一覧を
確かめる前の版のテスト 5 件と、文書・宣言の確かめの 2 件で失敗しました。直したのは、全体の数（停止コード・採用の記録の説明文のあるワザ）と一覧（相手の対戦
ポケモンに効果を与える型・T19b で止まるワザ（わるいペルシアンのどくのつめ）・バリアーで止まるコインの型（げんかくおんぱ）・こんらんの 20 が 40 になるポケモン
（ロケット団のヤドン・ナツメのヤドラン・R団のミュウツー。どれも超・弱点 超）・エンジンの `UNRESOLVED_…` のコードの一覧）の期待です（tests/test_card_sources.py・
test_guts_v0_11.py・test_transparency_v0_9.py・test_unresolved_boundaries_v0_4e.py・test_unresolved_rulings_v0_3d.py・test_barrier_resume_coin_bonus_v0_34.py。
数を確かめる tests/test_cards.py・test_cd4_opponent_energy_coins_v0_33.py・test_effects.py・test_research_links_v0_18e.py も直した）。どれも v0.41 のカードが加わった
ことによる期待の変更で、エンジンの処理は変えていません。test_guts_v0_11.py の宣言の確かめは、要素が登録の値で決まる型（`DamageThenStatusByCoin` の
`opponent_effect_elements` は property）を、登録した実装の宣言で数えるようにしました。

### 10.5 行っていないこと

- 変異試験の実行（`witness`・`full`）・性能の測定・複数の Python での実行は、依頼のとおり行っていません。
- ガイドブックの読み直し・pcg-search.com 以外の外部照合は行っていません。

## 11. 未解決・限界・報告事項

- 新しい未解決の裁定は CX1 の 1 件（5 章）。エンジンが止める `UNRESOLVED_…` は 47 件、未解決の裁定は 48 件。
- 既存の問い（RD9・Z23・HC3・T19b・HC4・HC9・T27・G37・v0.3b・v0.4b）は、該当する場面だけに当てはめ、分類を変えていません（6 章）。
- 実装上の判断（印刷の文面の読み方としてエンジンが決めたもの。原典で確かめた規定ではない）: ミラクルかふんで選ぶのはワザを使ったプレイヤー（SS3）、ひなたぼっこで
  つけない・選べるものがない場合も山札を切る（SN2）、回復するポケモンの順番（ログの並びだけ。とりのぞく数は変わらない）。
- エンジンの未対応として残ったもの: まねるワザのきあいずつき（`UNSUPPORTED_COPIED_ATTACK`。7 章）。
- kyuura への報告事項（kyuura のデータ・記録は変えていない。[data-provenance.md](data-provenance.md) の v0.41 の章）:
  1. CX1 が kyuura の未解決の一覧にない（研究の対応表の `stop_codes` で `not_in_kyuura`）。
  2. シードラ（PMCG3-020）のみずでっぽうのかっこ: kyuura は全角、pcg-search.com は半角（処理には影響しない）。
  3. 研究の基準のコミットに、15 枚のどれかを指す kyuura の最新の説明・エラッタ・裁定・論点・照合の記録はない。
