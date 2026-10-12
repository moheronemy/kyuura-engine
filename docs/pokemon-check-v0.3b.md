# ポケモンチェック（v0.3b）: ねむり・マヒと、どくのきぜつとの順番

v0.3b でポケモンチェックに加えた 3（ねむり）・4（マヒ）と、v0.3a の 2（どく）のきぜつとの順番について、原典で確かめたこと、決められなかったこと、実装、テストを対応づけた記録です。v0.3a のポケモンチェック（いつ行うか・どくのダメージ・どくのきぜつ・両方がどくできぜつする場合）は [pokemon-check-v0.3a.md](pokemon-check-v0.3a.md)、ねむり・マヒの規定は [sleep-paralysis-v0.3b.md](sleep-paralysis-v0.3b.md)、設計は [architecture-v0.3b.md](architecture-v0.3b.md) にあります。

- 基準のルール: 「ポケットモンスターカードゲーム公式ルール 2000.02.14版」（『ポケモンカードオフィシャルブック2000』pp.306〜326 [P43]、kyuura `NEO-2000-OFFICIAL-RULES`・`knockout_timing`）
- 照合の方法: スキャン [J38] のページ画像を目で読んだ（2026-10-12）。読んだページは p.309、p.311、p.313、p.322、p.323、p.324、p.325

## 1. 原典の記述（画像で読んだ）

| ページ | 記述 |
|---|---|
| p.323「ポケモンチェック」 | 「ポケモンチェックはどちらのプレイヤーの番でもありません。」「ポケモンチェックでは、おたがいのプレイヤーのすべてのポケモンがその対象になります。」 |
| p.323「ポケモンチェックでおこなうことの順番」 | 「1.「ポケモンチェックで○○する」と指示されたことをおこなう」（「ここでおこなうことが複数あった場合には、このポケモンチェックの前に番をおこなったプレイヤーが、その順番を決めます。」）「2.「どく」のダメージを与える ◆どく状態になっているポケモンに、それぞれ10ダメージを与えます。」「3.「ねむり」からさめるかどうかをチェックする ◆ねむり状態になっているポケモンの側のプレイヤーは、コインを投げます。「おもて」が出たら、そのプレイヤーのポケモンは、ねむり状態から回復します。」「4.「マヒ」がなおるかどうかをチェックする ◆マヒ状態になっているポケモンのうち、回復できるポケモンは、マヒ状態から回復します。◆ポケモンのマヒ状態は、マヒ状態になった番の「次の自分（そのポケモンの持ち主）の番」の終わりのポケモンチェックで自動的に回復します。」 |
| p.322 | 「ねむり状態のポケモンの側のプレイヤーは、ポケモンチェックのたびにコインを投げます。」 |
| p.323「16」 | 「ポケモンがもっているHP以上のダメージを受けると、ポケモンは「きぜつ」してトラッシュに置かれます。」「「きぜつ」したのが対戦ポケモンだったら、ベンチから新しい対戦ポケモンを出さなくてはなりません。かわりの対戦ポケモンが出せないときは、…負けとなり、対戦は終了します。」 |
| p.311・p.313 | 「「きぜつ」などで、あなたの対戦ポケモンがいなくなったら、ベンチから、代わりの対戦ポケモンをすぐに出さなければなりません。」（p.311）、「ベンチからすぐに代わりのポケモンを出さなくてはいけません。」（p.313） |
| p.322 | 「特殊状態になるポケモンは、バトル場にいるポケモン（対戦ポケモン）だけです。ベンチにいるポケモンは、特殊状態にはなりません。」 |
| p.325「23」 | 「同じタイミングで複数のことがらが起こったときは、特に指示されていないかぎり、それらを処理する順番を、そのとき番をおこなっているプレイヤーが決めます。」 |

## 2. 裁定の分類

| # | 事項 | 分類 | 根拠 | 実装 |
|---|---|---|---|---|
| C1 | 順番: 1 指示されたこと → 2 どく → 3 ねむり → 4 マヒ | CONFIRMED | p.323 | 2 → 3 → 4（1 は対応カードにない） |
| C2 | 3: ねむり状態のポケモンの持ち主がコインを 1 枚投げ、「おもて」なら回復 | CONFIRMED | p.322・p.323 | `flip_coins(state, owner, 1, source="pokemon_check", effect="sleep", card=…, pokemon_id=…)` → `sleep_check` →（「おもて」なら）`special_conditions_removed`（`sleep_coin`） |
| C3 | 3: どちらのプレイヤーの番のあとでも投げる | CONFIRMED | p.322「ポケモンチェックのたびに」 | すべてのポケモンチェック |
| C4 | 4: マヒ状態になった番の次の持ち主の番の終わりのポケモンチェックで自動的に回復。コインはない | CONFIRMED | p.322・p.323 | `paralysis_recovery_turn(state, owner, turn) == state.turn_number`（いま終わった番）なら消す（`paralysis_end`） |
| C5 | どく + ねむりのポケモン: どくのダメージ（2）のあとにねむりのコイン（3） | CONFIRMED | p.323 の順番 | 2 → 3 |
| C6 | 2 のどくできぜつしたポケモンについて、3 のコインを投げない | SUPPORTED | HP 以上のダメージを受けたポケモンはきぜつしてトラッシュに置かれる（p.323「16」）。3 の対象は「ねむり状態になっているポケモン」で、トラッシュのカードは場のポケモンではない。特殊状態はバトル場のポケモンだけ（p.322） | 2 のきぜつを処理してから 3 に進む（C7）。きぜつしたポケモンは場にいないので投げない（乱数も使わない） |
| C7 | 2 のきぜつのあと、サイド・判定・交代を 3 より先に行う | SUPPORTED | きぜつしたらトラッシュに置かれ（p.323）、代わりの対戦ポケモンを「すぐに」出す（p.311・p.313）。ポケモンチェックの手順にきぜつの段階はない（p.323） | 2 → きぜつ → サイド → 判定 → 交代（決定を待つ）→ 3 → 4 → 次の番 |
| C8 | 交代して出てきたポケモンは、同じポケモンチェックの 3・4 の対象か | SUPPORTED（結果は同じ） | ベンチにいたポケモンには特殊状態がない（p.322）ので、3・4 ですることがない | 対象にしても何もしない |
| C9 | 2 のきぜつで勝敗が決まったら、3・4 はしない | SUPPORTED | 「対戦は終了します」（p.311・p.323） | `GAME_OVER`・`SUDDEN_DEATH` で止まり、コインを投げない。もう一方のポケモンのねむり・マヒは状態に残る |
| C10 | 両方の対戦ポケモンがねむり状態のとき、どちらが先にコインを投げるか | **UNRESOLVED** | 4 章 | コインを投げる前に `Phase.HALTED`（`UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`） |
| C11 | 両方のポケモンが 2 のどくできぜつする場合 | **UNRESOLVED**（v0.3a のまま） | [pokemon-check-v0.3a.md](pokemon-check-v0.3a.md) 3 章 | ダメージ・コインの前に止める（`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`）。v0.3b で変えていない |
| C12 | マヒの回復（4）は、ねむりのコイン（3）より後 | CONFIRMED | p.323 | 3 → 4。ただし同じポケモンがねむりとマヒになることはない（重複しない。p.322）ので、結果には関係しない（ログの順だけ） |
| C13 | 3・4 ではダメージを与えないので、きぜつは起こらない。プレイヤーの選択もない | SUPPORTED | p.322・p.323 | 3・4 は決定を出さない |

### C7 の判断（「どく → きぜつ → 交代 → ねむり → マヒ」を機械的に決めていない理由）

p.323 のポケモンチェックの手順にはきぜつの段階がありません（kyuura `knockout_timing`: 第1〜2版はポケモンチェックできぜつを判定していた。2000.02.14版の手順にはない）。きぜつについての規定は「HP以上のダメージを受けると、ポケモンは「きぜつ」してトラッシュに置かれます」（p.323）で、ダメージを受けた時点のことです。対戦ポケモンがいなくなったら「すぐに」代わりを出す（p.311・p.313）とも書かれています。そのため、2 でダメージを受けてきぜつしたポケモンは、3 の時点で場にいません。

| 読み方 | きぜつしたポケモンのねむりのコイン | 交代と 3 のコインの前後 |
|---|---|---|
| きぜつの処理を 3 より先（採った） | 投げない | 交代が先。交代するプレイヤーは、相手のねむりのコインの結果を見ずに選ぶ |
| きぜつの処理をポケモンチェックの最後 | 投げる（結果は使われない） | 3 のコインが先 |

後者は、2000.02.14版がポケモンチェックからはずしたきぜつの判定（第2版の書き方）を、ポケモンチェックの最後に置くことになり、原典の記述（ダメージを受けたらきぜつしてトラッシュに置かれる・すぐに出す）と合いません。乱数の使い方（投げるかどうか）と、交代するプレイヤーが見る情報が変わるので、「どちらでも同じ」ではありません。前者は原典の規定から導けるので SUPPORTED とし、前者で実装しました。

勝敗が 2 で決まらず、交代のあとで 3・4 に進むことは、ポケモンチェックの手順（p.323）が 2 で終わるとは書かれていないことによります（3・4 は「ポケモンチェックでおこなうこと」）。

## 3. 処理の順番（状態遷移）

```
_end_turn: 期限のきたトレーナーをトラッシュ → turn_end
  ▼
_pokemon_check: pokemon_check
  ├ 2. どく: 両方がきぜつする → HALTED（UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT。ダメージ・コインの前）
  │          それ以外 → それぞれ poison_damage
  ├ きぜつがない ────────────────────────────────┐
  └ きぜつがある → knock_out（timing: pokemon_check）│
        → _after_knockouts(then=NEXT_TURN)        │
        ├ TAKE_PRIZE の決定（相手側）  ┐ context の "then" = "next_turn"
        ├ 判定 → 決まれば GAME_OVER（3・4・次の番はない）
        └ PROMOTE_ACTIVE の決定（持ち主）┘          │
              ▼                                   ▼
_pokemon_check_sleep_and_paralysis（v0.3b）
  ├ 3. ねむり: 両方の対戦ポケモンがねむり → HALTED（UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER。コインの前）
  │            それ以外 → 持ち主が coin_flip（source: pokemon_check）→ sleep_check →「おもて」なら special_conditions_removed（sleep_coin）
  ├ 4. マヒ: 回復する番の終わりなら special_conditions_removed（paralysis_end）。コインはない
  └ _begin_turn（次の番: turn_start → draw）
```

- `_pokemon_check_sleep_and_paralysis` を呼ぶのは 2 か所だけ: 2 できぜつがないとき（`_pokemon_check` の中）と、2 のきぜつの決定がすべて終わったとき（`_next_promotion_or_end` で `then == NEXT_TURN`）。どちらも 1 回のポケモンチェックに 1 回だけで、最後に `_begin_turn` を呼ぶ（`_begin_turn` をほかの場所から呼ばない）。
- 決定の続き（`context` の `"then"`）の値は v0.3a と同じ `"next_turn"`（「ポケモンチェックの中で、次の番はまだ始まっていない」）。v0.3b では、交代のあとで次の番を始める前に 3・4 を行う。値を変えなかったのは、書き出しの形（形式 2〜5 の `decision.context.then`）とクライアントへの意味（ポケモンチェックの中）を v0.3a と同じに保つため。3・4 は決定を出さないので、`"then"` の決定は 2 のきぜつのあとにしかなく、再開したときに 3・4 をしたかどうかで迷うことはない。
- Phase は増やしていない（v0.3a と同じ）。3・4 は 1 つのコマンドの中で終わる。

## 4. 両方の対戦ポケモンがねむり状態のとき（UNRESOLVED）

p.323 の 3 は「ねむり状態になっているポケモンの側のプレイヤーは、コインを投げます」とだけ書き、両方のプレイヤーが投げるときの順番を書いていません。

- p.323 の 1 の「このポケモンチェックの前に番をおこなったプレイヤーが、その順番を決めます」は、1（指示されたこと）についての記述で、3 には書かれていない。
- p.325 の「そのとき番をおこなっているプレイヤーが決めます」は、ポケモンチェックが「どちらのプレイヤーの番でもありません」（p.323）なので当てはめられない（v0.3a の両方がどくできぜつする場合と同じ問題）。
- エンジンは乱数を順に使う（コイン 1 枚に `getrandbits(1)` 1 回）ので、投げる順番によって、どちらのポケモンがどの結果になるかが変わる。たとえば次の 2 回が「おもて・うら」なら、プレイヤー 0 が先ならプレイヤー 0 が回復し、プレイヤー 1 が先ならプレイヤー 1 が回復する。順番を決める人がいるなら、それはプレイヤーの選択（決定）になるが、その人も決まらない。

そのため、3 の時点で両方の対戦ポケモンがねむり状態なら、**コインを投げる前に**対戦を止めます（`Phase.HALTED`、`UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`。ログ `… pokemon_check →（poison_damage）→ halted`）。2 のどくのダメージは与えたあとです（2 で両方がきぜつする場合は v0.3a のとおり 2 の前に止める）。番のプレイヤーから投げるような正規化はしていません。

v0.3b の対応カードでは起こりません。ねむりにするのはキノコのほうし（相手の対戦ポケモンだけ）で、ワザを使うポケモンはその時点でねむり状態ではない（ねむりのポケモンはワザを使えない）ので、ねむりにされたポケモンの持ち主の側では、ねむりのポケモンが入れ替わらないかぎり、相手をねむりにするワザを使えません。入れ替わったら（ポケモンいれかえ）前のポケモンのねむりは消えます。そのため、ポケモンチェックの時点でねむり状態の対戦ポケモンは多くても 1 匹です（自然な対戦 15 局・負荷テスト 400 局で 0 回）。自分のポケモンをねむりにする効果や、ポケモンチェックの 1 でねむりにする効果を加えたら起こりうるので、止める処理を残しています。両方がねむりでも、片方が 2 のどくできぜつすれば 3 の時点では 1 匹なので止めません（C6・C7）。

## 5. 乱数の使い方の順番

1. ワザのコイン（ワザの説明の順。v0.2d）
2. ワザのあとのきぜつ・サイド・交代（乱数を使わない）
3. 番の終わり → ポケモンチェック: 2 のどく（乱数を使わない）→ 2 のきぜつ・サイド・交代（乱数を使わない）→ 3 のねむりのコイン（1 枚）→ 4 のマヒ（乱数を使わない）
4. 次の番のドロー（乱数を使わない）

ねむりがなければ、ポケモンチェックで乱数は使いません（v0.3a と同じ）。マヒの回復も使いません。不正な操作・決定は状態も乱数も変えません（`apply_command` は複製してから処理する。決定に答える前にコインを投げることはない）。止めるときは、コインを投げる前です。

## 6. ログ

| イベント | 項目 | 意味 |
|---|---|---|
| `coin_flip` | `player`（持ち主）・`source: "pokemon_check"`・`effect: "sleep"`・`card`（ねむりのポケモンのカード）・`pokemon_id`・`number`・`count`・`result` | ねむりのコイン。ワザのコイン（`source: "attack"`、`effect` は `"PMCG1-002#0"` など）と区別する |
| `sleep_check` | `player`・`pokemon`・`pokemon_id`・`result`・`recovered` | 3 の結果（回復したか）。すぐ前の `coin_flip` に対応する |
| `special_conditions_removed` | `conditions: ("sleep",)`・`reason: "sleep_coin"` | 3 で回復した |
| `special_conditions_removed` | `conditions: ("paralysis",)`・`reason: "paralysis_end"` | 4 で回復した |
| `halted` | `code: "UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER"` | 4 章 |

この先のコインの結果や乱数の内部状態は、ログにも、プレイヤー向けの情報にも出しません（状態の書き出しは乱数の指紋だけ）。

## 7. PendingDecision との関係

- 新しい決定の種類・再開先はない。ポケモンチェックの中で決定を待つのは、v0.3a と同じく 2 のきぜつのあとのサイド（`take_prize`）と交代（`promote_active`）だけ。
- 決定を待つ間の段階は `TAKE_PRIZE`・`PROMOTE_ACTIVE`、`turn_number`・`current_player` は番を終えたプレイヤーの番のまま。ねむり・マヒの状態もそのまま（まだ 3・4 をしていない）。マヒの不変条件（回復する番が今の番より前ではない）は、回復する番が今の番でも満たす。
- 決定を待つ間のほかのコマンドは拒否し、状態も乱数も変えない（3 のコインを先に投げない）。
- 複製・deepcopy・pickle した状態に同じ決定を送れば、同じコインの結果になる。

## 8. コードとテストの対応

| 規定・判断 | コード | テスト（test_pokemon_check_v0_3b.py） |
|---|---|---|
| C1 順番、特殊状態なし・どくだけ | `engine._pokemon_check`・`_pokemon_check_sleep_and_paralysis` | `CheckStepsTest.test_no_conditions_no_coin`・`test_poison_only`・`test_order_poison_then_sleep_then_paralysis` |
| C2・C3 ねむりのコイン | `_pokemon_check_sleep_and_paralysis` | `test_sleep_coin_is_flipped_by_the_owner_after_either_players_turn`・`test_heads_recovers` |
| C4 マヒの回復 | `conditions.paralysis_recovery_turn` | `test_paralysis_only_recovers_on_its_turn_without_a_coin` |
| 二重に行わない | `_end_turn`・`_next_promotion_or_end`・`_progress_problems` | `test_the_check_is_done_once`、test_pokemon_check.py `ProgressInvariantTest` |
| C6・C7・C8 きぜつ → 交代 → 3・4 | `_pokemon_check`・`_next_promotion_or_end` | `PoisonKnockOutAndStepsTest`、`BothAsleepTest.test_one_knocked_out_by_poison_then_the_other_flips` |
| C9 勝敗が決まったら 3・4 はしない | `_next_prize_or_judge` | `test_game_over_in_step_2_skips_the_rest`・`test_paralysis_left_when_the_game_ends_in_step_2` |
| C10 両方がねむり | `_pokemon_check_sleep_and_paralysis`・`_halt` | `BothAsleepTest.test_halts_before_any_coin`・`test_poison_damage_is_given_before_the_halt` |
| C11 両方がどくできぜつ（v0.3a のまま） | `_pokemon_check` | `test_double_poison_knock_out_still_halts_before_the_damage_and_coins`、test_pokemon_check.py `DoubleKnockOutTest` |
| 決定を待つ間の拒否・複製・書き出し | `apply_command`・`serialize` | `test_rejections_during_the_check_do_not_flip_coins`・`test_copies_during_the_check_give_the_same_coin`・`test_formats_during_the_check` |
| 5 章 乱数の順番 | `coins.flip_coins` | `AttackThenCheckTest` |
| 正式な対戦開始から | — | test_sleep_paralysis_games.py `test_each_check_flips_at_most_one_sleep_coin_after_the_poison`・`test_paralysis_recovers_at_the_end_of_the_owners_next_turn`・`test_only_coins_use_randomness_after_setup` |
