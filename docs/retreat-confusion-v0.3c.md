# こんらん状態のポケモンの「にげる」（v0.3c）: コイン・エネルギー・再宣言の制限

こんらん状態のポケモンが「にげる」を宣言したときの規定について、原典で確かめたこと、決められなかったこと、実装、テストを対応づけた記録です。原典の記述の全文とこんらん状態そのものの分類は [confusion-v0.3c.md](confusion-v0.3c.md)、ワザのときは [confusion-attacks-v0.3c.md](confusion-attacks-v0.3c.md)、設計は [architecture-v0.3c.md](architecture-v0.3c.md) にあります。

## 1. 原典の記述（要点）

pp.310〜311「バトル場にいる対戦ポケモンをにがす」（300dpi の画像で読んだ）:

1. 「対戦ポケモンが「にげる」ことを宣言します。」
2. 「…「にげるときにトラッシュするエネルギーの数」ぶんのエネルギーを、そのポケモンについているエネルギーカードの中から選んで、トラッシュします。トラッシュできないときは、「にげる」を宣言することはできません。」
3. 「「にげる」をおこなうポケモンがこんらん状態なら、それによって「にげる」が失敗するかどうかを以下のようにチェックします。」●「「にげる」を宣言したポケモン側のプレイヤーは、コインを1枚投げます。「うら」なら、「にげる」は失敗です。」●「「にげる」が失敗したからといって、トラッシュしたエネルギーカードを取り戻すことはできません。」
4. 「自分の控えポケモンを1匹選び、対戦ポケモンと入れ替えます。…」●「「にげる」が失敗したとき、この入れ替えをおこなってはいけません。」

続けて p.311: 「自分のベンチに控えポケモンがいないときには、「にげる」を宣言することはできません。」「バトル場にいるポケモンがねむり状態またはマヒ状態のとき、そのポケモンは「にげる」を宣言することができません。」「「にげる」の宣言は、1回の自分の番の中で、何度でもすることができます。」●「1匹のポケモンが何回「にげる」を宣言してもかまいません。」「**一度「にげる」に失敗したこんらん状態のポケモンは、今の自分の番では、もう「にげる」を宣言することができません。**」●「**次の自分の番になれば、再び「にげる」を宣言することができます。**」「ベンチに戻ったら、そのポケモンの「どく」「ねむり」「マヒ」「こんらん」状態や、「持続する効果」は、すべて消えてなくなります。」

p.325「21 ポケモンの入れ替え」: 「「にげる」も、この「ポケモンの入れ替え」にふくまれます。」「「にげる」がおこなえない状態のポケモンでも、「そのポケモンを入れ替える」と指示されたときは、入れ替えをおこないます。」

## 2. 処理の順番（`engine._retreat`）

| 順 | 処理 | 根拠 | 拒否・失敗のとき |
|---|---|---|---|
| 0 | 番の確認 | — | `NOT_YOUR_TURN` など |
| 1 | 控えがいない | p.311 | `NO_BENCH`（宣言できない） |
| 2 | ねむり・マヒ | p.311・p.322 | `POKEMON_ASLEEP`・`POKEMON_PARALYZED`（こんらんとは重複しない） |
| 3 | この番に、このポケモンがこんらんで「にげる」に失敗している | p.311 | こんらん状態のままなら `RETREAT_ALREADY_FAILED`（`IllegalActionError`）。こんらんが消えていれば `UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED`（`UnsupportedError`。R14） |
| 4 | 入れ替える控え・トラッシュするエネルギーの確認（にげるエネルギーの数ぶん、そのポケモンについているエネルギー） | p.310 手順 2・4 | `NOT_ON_BENCH`・`DUPLICATE_CARD`・`ENERGY_NOT_ATTACHED`・`WRONG_RETREAT_COST`（トラッシュできないので宣言できない） |
| 5 | エネルギーをトラッシュする | p.310 手順 2 | — |
| 6 | こんらん状態なら、宣言したプレイヤーがコインを 1 枚（`coin_flip` の `source: "confusion"`、`effect: "retreat"`）→ `confusion_check`（`action: "retreat"`） | p.311 手順 3 | — |
| 7a | 「おもて」（またはこんらんでない）: 控えと入れ替える（ついているカード・ダメージもいっしょに）。ベンチに戻ったポケモンの特殊状態（こんらん・どく）は消える | p.311 手順 4 | — |
| 7b | 「うら」: 失敗。入れ替えない。トラッシュしたエネルギーは戻らない。こんらん・どく・ダメージ・ついているカードはそのまま。このポケモンの記録 `retreat_failed_turn` = 今の番。ログ `retreat_failed`（`discarded` にトラッシュしたエネルギー）。**番は終わらない** | p.311 手順 3・4、再宣言の規定 | — |
| 8 | 番の終わりに、すべての場のポケモンの記録を消す | p.311「今の自分の番では」「次の自分の番になれば」 | — |

1〜4 で拒否した操作は、エネルギーもコインも使いません（`apply_command` は複製した状態で処理する。テストで状態・乱数が変わらないことを確かめた）。7b の失敗は、宣言が正しく成り立ったあとのルールによる結果で、エネルギーのトラッシュ・コイン・記録は状態に残ります。

入れ替える控えは、手順 4 で選ぶものですが、コマンド（`Retreat(player, discard, new_active)`）で先に指定します。コインの結果で選べる控えは変わらず、「うら」なら使わないだけなので、結果は同じです（v0.1 からのコマンドの形を変えていない）。

## 3. 裁定の分類（にげる）

| # | 事項 | 分類 | 根拠 | 実装 |
|---|---|---|---|---|
| R1 | こんらん状態のポケモンも「にげる」を宣言できる | CONFIRMED | p.311 が宣言できないとするのは、控えがいない・ねむり・マヒだけ。手順 3 は宣言のあとのチェック | 拒否しない |
| R2 | エネルギーをトラッシュしてからコインを投げる | CONFIRMED | 手順 2 → 3 | 5 → 6 |
| R3 | 投げるのは、宣言したポケモン側のプレイヤー | CONFIRMED | 手順 3 | `flip_coins(state, cmd.player, 1, source="confusion", effect="retreat", …)` |
| R4 | 「うら」なら失敗。トラッシュしたエネルギーは取り戻せない | CONFIRMED | 手順 3 | エネルギーはトラッシュに残る |
| R5 | 失敗したら入れ替えない | CONFIRMED | 手順 4 の● | 控えはそのまま。こんらん・どくもそのまま（ベンチに戻っていない） |
| R6 | 失敗しても番は終わらない | SUPPORTED | 番が自動的に終わるのはワザを使ったとき（p.309）。p.311 の「今の自分の番では、もう…宣言することができません」は、失敗のあとも番が続くことを前提にしている | 段階は `MAIN` のまま。エネルギーをつける・トレーナー・ワザ（こんらんのコインをもう一度投げる）・番を終えるができる |
| R7 | 一度失敗したこんらん状態のポケモンは、今の自分の番では、もう宣言できない | CONFIRMED | p.311 | `RETREAT_ALREADY_FAILED`（コイン・エネルギーの前） |
| R8 | 次の自分の番には、再び宣言できる | CONFIRMED | p.311 | 番の終わりに記録を消す（`_end_turn`）。こんらんは自然に回復しないので、次の番もコインを投げる |
| R9 | 制限はポケモンごと（プレイヤーごとではない）。ほかのポケモンは「にげる」を宣言できる | CONFIRMED | p.311 の主語は「一度「にげる」に失敗したこんらん状態のポケモンは」。「1匹のポケモンが何回…宣言してもかまいません」 | 記録は場のポケモン（`pokemon_id`）が持つ。プレイヤー単位の「この番はもうにげられない」にしない |
| R10 | にげるエネルギーが 0 のポケモンでも、こんらんならコインを投げる | SUPPORTED | 手順 2 は 0 個をトラッシュし、手順 3 に例外がない | ディグダ・コラッタ（にげる 0）でもコイン。「うら」なら失敗（`discarded` は空） |
| R11 | 「おもて」なら入れ替え、ベンチに戻ったポケモンのこんらん（とどく）は消える | CONFIRMED | 手順 4・p.311 | `clear_special_conditions`（`reason: "retreat"`） |
| R12 | 宣言できない「にげる」（控えがいない・エネルギーが足りない・ねむり・マヒ）では、エネルギーもコインも使わない | CONFIRMED | 手順 2「トラッシュできないときは、「にげる」を宣言することはできません」、p.311 | 2 章の 1〜4 で拒否 |
| R13 | 失敗のあとでも、ポケモンいれかえでは入れ替えられる（コインはない） | CONFIRMED | p.325 | `SwitchWithBench` を制限しない。ベンチに戻ったポケモンのこんらんは消える |
| R14 | 失敗したあとにベンチに戻り（こんらんが消え）、同じ番にバトル場に戻ったポケモンが「にげる」を宣言できるか | **UNRESOLVED** | p.311 の主語「一度「にげる」に失敗したこんらん状態のポケモン」に、こんらんでなくなったポケモンが含まれるかは書かれていない（「失敗したポケモン」と読めば宣言できず、「今こんらん状態のポケモン」と読めば宣言できる） | `UnsupportedError`（`UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED`）。エネルギー・コインの前に止める。起こる手順の例: 失敗 → ポケモンいれかえで控えに → 新しい対戦ポケモンが「にげる」かポケモンいれかえで戻す |
| R15 | 失敗の記録は番の終わりまで、ベンチに戻っても残る | SUPPORTED | R7 の「今の自分の番では」。ベンチに戻ってもそのポケモンは同じポケモン（`pokemon_id`）。消えるのは特殊状態と持続する効果で、失敗の規定は特殊状態ではない | ベンチのポケモンも記録を持てる（R14 の判定に使う） |
| R16 | 入れ替える控えをコマンドで先に指定する | 設計 | 手順 4 の選択はコインの結果で変わらない | `Retreat.new_active` を手順 4 まで使わない |

## 4. 状態の持ち方

`PokemonInPlay.retreat_failed_turn: int | None`。こんらん状態で「にげる」に失敗した番の番号を、場のポケモンごとに持ちます。

- 失敗したら `state.turn_number` を入れる。番の終わり（`_end_turn`）で、場のすべてのポケモンについて None に戻す（`turn_end` のログの前）
- 確かめるのは「`retreat_failed_turn == state.turn_number`」。番の番号と比べるので、消し忘れがあっても次の番の宣言を誤って拒否しない（不変条件でも消し忘れを見つける）
- 場を離れたら（きぜつ）場のポケモンごと消える。進化（未実装）では同じ `pokemon_id` のまま残る（進化を加えるときに見直す。[architecture-v0.3c.md](architecture-v0.3c.md) 14 章）
- 不変条件: None か、今の番の番号（整数）。持ち主は番のプレイヤー。対戦準備の段階・番の終わりのあと（ポケモンチェックの途中の決定）には残らない
- 書き出し: 形式 6 の場のポケモンごとの `retreat_failed_turn`。形式 1〜5 は表せないので、記録があれば `ValueError`（黙って落とさない）

## 5. ポケモンいれかえとの関係

| 手順 | 結果 |
|---|---|
| こんらん状態のポケモンにポケモンいれかえ | コインなしで入れ替え、こんらんは消える（R13・C14） |
| 「にげる」に失敗 → ポケモンいれかえ | 入れ替えられる。失敗したポケモンはベンチで記録を持ったまま（こんらんは消える） |
| 失敗 → ポケモンいれかえ → 新しい対戦ポケモンが「にげる」 | 新しい対戦ポケモンは失敗していないので宣言できる（R9）。こんらんでなければコインもない |
| 失敗 → ポケモンいれかえ → 失敗したポケモンをバトル場に戻す → そのポケモンが「にげる」 | **UNRESOLVED**（R14）。止める |
| 失敗 → 番を終える → 相手の番 → 自分の番 | 記録は消えている。こんらんのままなら、コインを投げて「にげる」ができる（R8） |

## 6. ログ

```
# こんらん状態の対戦ポケモンが「にげる」（エネルギーはこの前にトラッシュ済み）
coin_flip        {player, source: "confusion", effect: "retreat", card, pokemon_id, number: 1, count: 1, result}
confusion_check  {player, pokemon, pokemon_id, action: "retreat", result, succeeded}
# 「おもて」
retreat          {player, discarded, old_active, new_active}             ← v0.1 と同じ形
special_conditions_removed {conditions: ("confusion",) か ("poison", "confusion"), reason: "retreat"}
# 「うら」
retreat_failed   {player, pokemon, pokemon_id, discarded}
```

こんらんでない「にげる」のログは v0.1 と同じです（`retreat` だけ。コインはない）。再宣言の拒否はコマンドの拒否なので、ログに残りません。

## 7. 実装とテストの対応

| 事項 | コード | テスト |
|---|---|---|
| R1〜R5・R11 コインと結果 | `engine._retreat`・`_confusion_check` | test_confusion_retreat.py `ConfusedRetreatTest.test_heads_retreats`・`test_tails_fails_and_keeps_the_trashed_energy_in_the_discard` |
| R10 にげるエネルギー 0・1・2 | `engine._retreat` | `test_retreat_costs_zero_one_and_two` |
| R12 宣言できない「にげる」 | `engine._retreat` | `test_illegal_retreats_are_rejected_before_any_energy_or_coin`、`test_not_confused_retreat_flips_no_coin` |
| R6 番は続く | — | `AfterFailureTest.test_the_rest_of_the_turn_goes_on` |
| R7 再宣言の拒否 | `retreat_failed_turn`・`RETREAT_ALREADY_FAILED` | `test_cannot_declare_again_this_turn` |
| R8 次の番 | `_end_turn` | `test_record_is_cleared_at_the_end_of_turn_and_retreat_is_allowed_next_turn` |
| R9 ポケモンごと | `PokemonInPlay.retreat_failed_turn` | `test_failure_is_per_pokemon_not_per_player` |
| R13 ポケモンいれかえ | `SwitchWithBench`（変更なし） | `test_switch_after_failure_is_allowed`、test_confusion.py `LeavingTheBattleFieldTest` |
| R14 未解決 | `UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED` | `test_failed_pokemon_back_in_the_battle_field_is_unresolved` |
| ダメージを変えるカードは「にげる」を止めない | — | `test_pluspower_does_not_stop_retreat` |
| 記録の書き出し・不変条件 | `serialize`・`engine._retreat_failure_problems` | `test_serialization_of_the_record`、test_confusion.py `InvariantTest` |
| 正式な対戦開始から | — | test_confusion_games.py `test_failed_pokemon_never_retreats_in_the_same_turn` |
