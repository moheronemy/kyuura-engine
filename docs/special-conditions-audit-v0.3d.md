# 特殊状態 4 種類の総合検証（v0.3d）

v0.3a〜v0.3c で 1 つずつ加えた「どく」「ねむり」「マヒ」「こんらん」を、組み合わせ・操作・ポケモンチェック・新しい対戦からの総合テスト・負荷テスト・変異テストで、まとめて確かめた記録です。新しいカードやルールは加えていません。原典で決められない裁定の再調査は [unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md)、コインの前の検証は [effect-preflight-v0.3d.md](effect-preflight-v0.3d.md)、設計の変更は [architecture-v0.3d.md](architecture-v0.3d.md) にあります。

## 0. 照合の条件

| 項目 | 内容 |
|---|---|
| 基準のルール | 「ポケットモンスターカードゲーム公式ルール 2000.02.14版」（『ポケモンカードオフィシャルブック2000』pp.306〜326 [P43]、kyuura `NEO-2000-OFFICIAL-RULES`） |
| 読み直したページ | p.309（ワザを使う手順 1〜6・進化）、pp.310〜311（進化・にげる）、p.321（8 ワザによるダメージと効果）、p.322（10 特殊状態・11 持続する効果）、p.323（11 の続き・12 ワザの失敗・13 マーカーとカウンター・15 ポケモンチェック）、p.325（21 ポケモンの入れ替え）。カードのページの解説は p.90・p.207・p.238・p.295（[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md)） |
| 照合の方法 | Internet Archive のスキャン [J38] の PDF をページ画像にして目で読んだ（2026-10-12）。OCR の文字はページを探すのに使っただけ |
| kyuura の記録 | 参照コミット `ecb2d694` の `sleep`・`paralysis`・`confusion_attack`・`confusion_retreat`・`status_on_evolve`・`knockout_timing` |
| 分類 | CONFIRMED（原文に書かれている）・CONFIRMED（解説）（カードのページなどの解説に書かれている）・SUPPORTED（原文から導ける、または原文の例から一般化した）・UNRESOLVED（原文で決められない）・CONFLICT（資料が食い違う） |

v0.3d で分類を変えたのは、v0.2f の「自分へのワザのダメージの弱点・抵抗力」（UNRESOLVED → SUPPORTED。[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md) 6 章）だけです。特殊状態の規定の分類は v0.3a〜v0.3c のままで、SUPPORTED の事項を CONFIRMED に上げたものはありません。

## 1. 8 つの状態

どく（`SpecialConditions.poison`）はほかの特殊状態と重複し、ねむり・マヒ・こんらん（`SpecialConditions.exclusive`）はたがいに重複しない（p.322「特殊状態の重複」）ので、バトル場のポケモンがとりうる特殊状態は次の 8 つです。

| 状態 | `SpecialConditions` | 書き出し（形式 5・6 の `special_conditions`） |
|---|---|---|
| なし | `NO_SPECIAL_CONDITIONS` | `{}` |
| どく | `poison=Poison(10)` | `{"poison": {"damage": 10}}` |
| ねむり | `exclusive=ASLEEP` | `{"sleep": {}}` |
| どく + ねむり | `poison=Poison(10), exclusive=ASLEEP` | `{"poison": …, "sleep": {}}` |
| マヒ | `exclusive=Paralyzed(turn)` | `{"paralysis": {"turn": n}}` |
| どく + マヒ | `poison=Poison(10), exclusive=Paralyzed(turn)` | `{"poison": …, "paralysis": …}` |
| こんらん | `exclusive=CONFUSED` | `{"confusion": {}}` |
| どく + こんらん | `poison=Poison(10), exclusive=CONFUSED` | `{"poison": …, "confusion": {}}` |

8 つとも、不変条件を満たし、形式 5・6 で書き出せ、`clone`・`copy.deepcopy`・`pickle` で保たれ、形式 1〜4 では `ValueError`（黙って落とさない）になることを確かめました（tests/test_special_conditions_matrix_v0_3d.py `EightStatesTest`）。ベンチのポケモンが 8 つのどれか（なし以外）を持てば不変条件の違反です（同 `test_bench_pokemon_never_hold_them`）。

## 2. 付与・上書き・解除の規定

v0.3a〜v0.3c の照合（[special-conditions-v0.3a.md](special-conditions-v0.3a.md)・[sleep-paralysis-v0.3b.md](sleep-paralysis-v0.3b.md)・[confusion-v0.3c.md](confusion-v0.3c.md)・[retreat-confusion-v0.3c.md](retreat-confusion-v0.3c.md)）を 1 つの表にまとめました。番号は各文書のものです（同じ番号が文書ごとに別の事項を指すので、文書名をつけています）。

| 事項 | 分類 | 根拠 | 実装 | テスト |
|---|---|---|---|---|
| 特殊状態になるのはバトル場のポケモンだけ（v0.3a #2） | CONFIRMED | p.322 | 付ける処理はバトル場のポケモンだけ。ベンチにあれば不変条件の違反 | `EightStatesTest.test_bench_pokemon_never_hold_them` |
| どくは重複しない（二重のどくにならない。v0.3a #11） | CONFIRMED | p.322 | 状態は変えず、ログに `already` | `OverwriteMatrixTest.test_poison_joins_every_exclusive_state` |
| どくはほかの特殊状態と重複する（v0.3a #12・sleep-paralysis O5・confusion C7） | CONFIRMED | p.322 | `poison` と `exclusive` を別の項目に持つ | 同上・`EightStatesTest` |
| ねむり・マヒ・こんらんは重複しない（sleep-paralysis O1・confusion C8） | CONFIRMED | p.322 | 1 つの項目 `exclusive` | `OverwriteMatrixTest.test_every_transition` |
| 同じ状態を再び受けても二重にならない（sleep-paralysis S9・P9、confusion C4） | CONFIRMED | p.322 | 状態は変えず、ログに `already` | 同上（`previous == new`） |
| マヒ → ねむり: マヒが消えてねむり（sleep-paralysis O2） | CONFIRMED | p.322 の例 | 前の状態を消して（`replaced`）から付ける | 同上 |
| ねむり → マヒ、ねむり／マヒ ⇄ こんらん（sleep-paralysis O3、confusion C9・C10） | SUPPORTED | p.322 の例（O2）の一般化 | 同上 | 同上 |
| 置きかわっても、どくは残る（sleep-paralysis O6、confusion C11） | SUPPORTED | p.322（どくはほかと重複する。置きかわるのは 3 つのあいだだけ） | `exclusive` だけを置きかえる | 同上（`poisoned=True`） |
| マヒの再付与で回復する番が変わる場合（sleep-paralysis P10） | **UNRESOLVED** | p.322・p.323 に書かれていない | `UNRESOLVED_REPARALYSIS_RECOVERY_TURN`（状態を変えない） | `OverwriteMatrixTest.test_reparalysis_with_another_recovery_turn`、[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md) 5 章 |
| ベンチに戻ったら（にげる・ポケモンいれかえ）すべて消える。復活しない（v0.3a #3・#4・#18） | CONFIRMED | p.311・p.322・p.325 | `clear_special_conditions`（`retreat`・`switch`） | `RetreatMatrixTest`・`OtherActionsMatrixTest.test_switch_in_every_state` |
| ねむりはポケモンチェックの 3 のコインの「おもて」で回復（sleep-paralysis S6） | CONFIRMED | p.322・p.323 | `sleep_coin` | `PokemonCheckMatrixTest.test_check_in_every_state` |
| マヒは、マヒ状態になった番より後の持ち主の最初の番の終わりに回復（sleep-paralysis P5〜P8） | CONFIRMED（P5・P8）・SUPPORTED（P6・P7） | p.322・p.323 | `paralysis_end`（`paralysis_recovery_turn`） | 同上・`test_opponent_paralysis_received_this_turn_does_not_recover_yet` |
| どく・こんらんは自然に回復しない（v0.3a #10・confusion） | CONFIRMED | p.322 | ポケモンチェックで消さない | 同上 |
| きぜつしたら、場のポケモンといっしょになくなる | CONFIRMED | p.323（きぜつ・トラッシュ） | 場のポケモンごとトラッシュ | `PokemonCheckMatrixTest.test_poison_knock_out_in_every_exclusive_state` |
| 進化したら消える（v0.3a #6・sleep-paralysis S12・P13・confusion C6） | CONFIRMED | p.310 手順 3・p.322 | 進化は未実装（[evolution-readiness-v0.4.md](evolution-readiness-v0.4.md)） | — |
| 「にげる」の失敗の記録は特殊状態ではなく、ベンチに戻っても番の終わりまで残る（retreat-confusion R15） | SUPPORTED | p.311 | `PokemonInPlay.retreat_failed_turn`。`clear_special_conditions` は記録を変えない | 変異テスト「特殊状態を消すとにげる失敗の記録も消える」を検出（11 章） |

## 3. 付与・上書きの実装の統一（v0.3d）

v0.3c までは `put_to_sleep`・`paralyze`・`confuse` がそれぞれ「同じ状態なら `already`、別の状態なら `replaced` で消してから付ける」を書いていました。v0.3d で、この共通の部分を `conditions._set_exclusive`（同じ型なら何もしない・違えば前の状態を消してから置きかえる。どくは `dataclasses.replace` で残す）と `conditions._log_applied`（ログ `special_condition`。`already` のときだけ項目を加える）にまとめました。

- 4 つの付ける関数の外から見た動き（状態・ログの順番と項目・例外）は変わっていません（v0.3c との比較。[architecture-v0.3d.md](architecture-v0.3d.md) 9 章）。
- マヒは、`paralysis_problem`（回復する番が変わる場合は止める）を先に確かめ、そのあとで `_set_exclusive` を呼びます（止めるときに状態もログも変わらない）。
- 「特殊状態は 1 つだけ」という形にはしていません（CLAUDE.md）。どくを消す処理は `clear_special_conditions` だけです。

付ける・消す処理と、その理由（ログ `special_conditions_removed` の `reason`）は次のとおりです。

| 理由 | 消すもの | 呼ぶところ |
|---|---|---|
| `replaced` | ねむり・マヒ・こんらんのうち前の 1 つ（どくは残す） | `_set_exclusive` |
| `retreat` | すべて | にげるの成功（こんらんならコインの「おもて」） |
| `switch` | すべて | ポケモンいれかえ |
| `sleep_coin` | ねむり | ポケモンチェックの 3 |
| `paralysis_end` | マヒ | ポケモンチェックの 4 |

## 4. 操作 × 8 つの状態

tests/test_special_conditions_matrix_v0_3d.py の `AttackMatrixTest`・`RetreatMatrixTest`・`OtherActionsMatrixTest`・`PendingDecisionMatrixTest` で、8 つの状態それぞれについて確かめました（コインは「おもて」「うら」の両方）。

| 操作 | なし・どく | ねむり・どく + ねむり | マヒ・どく + マヒ | こんらん・どく + こんらん | 根拠 |
|---|---|---|---|---|---|
| ワザ | 使える（こんらんのコインはない） | `POKEMON_ASLEEP`（エネルギーの確認より前。状態・乱数は変わらない） | `POKEMON_PARALYZED`（同） | 宣言のあとこんらんのコイン。「おもて」ならワザ、「うら」なら自分に 20 でワザの内容はない。どちらも番は終わる | p.309 手順 1・5、p.322 |
| にげる | コインなしで入れ替え、特殊状態はすべて消える | `POKEMON_ASLEEP` | `POKEMON_PARALYZED` | エネルギーをトラッシュしてからコイン。「おもて」なら入れ替えてすべて消える、「うら」なら入れ替えず、失敗の記録。番は続く | p.311、p.322 |
| ポケモンいれかえ | コインなしで入れ替え、すべて消える（`switch`） | 同（ねむりでも入れ替える） | 同 | 同（こんらんのコインはない） | p.325 |
| トレーナー・エネルギー・ベンチに出す | できる（乱数を使わない） | できる | できる | できる | p.322（特殊状態でもエネルギーをつけられる） |
| 番を終える | ポケモンチェックへ | 同 | 同 | 同 | p.323 |
| 決定を待つ間（ポケモンチェックの中のサイドの決定） | 番のプレイヤーの操作はすべて拒否。状態も乱数も変わらない（ねむり・こんらんのコインを先に投げない） | 同 | 同 | 同 | v0.2a の決定の約束 |

ねむり・マヒの拒否は、ワザではエネルギーの確認の前、にげるでは入れ替える控え・エネルギーの確認の前です（p.309 の手順 1・p.311。v0.3b の `test_asleep_check_comes_before_the_energy_check`）。こんらんのワザ・にげるの宣言が正しくない場合（エネルギー不足・にげるエネルギーの数の誤り）は、コインの前にそのコードで拒否します（test_confusion_attacks.py・test_confusion_retreat.py）。

## 5. こんらん

v0.3c で確かめた事項（[confusion-v0.3c.md](confusion-v0.3c.md)・[confusion-attacks-v0.3c.md](confusion-attacks-v0.3c.md)・[retreat-confusion-v0.3c.md](retreat-confusion-v0.3c.md)）に、v0.3d では次を加えました。

- 8 つの状態のうちこんらんの 2 つ（どくあり・なし）で、ワザ・にげるのコインの数と出どころ（`source`）が、「おもて」なら `["confusion", "attack"]`（ワザの説明のコインがあるワザ）、「うら」なら `["confusion"]` だけであること（`AttackMatrixTest`）。
- 「うら」のワザで、自分の状態（こんらん・どく）が変わらないこと。ワザの効果（相手をこんらんにする）がないこと。
- にげるの失敗の記録が、今の番のログの `retreat_failed`（同じ場のポケモンの番号）と対応すること（v0.3d で不変条件に加えた。8 章）。
- こんらんの 20 とプラスパワー・ディフェンダー、失敗のあとこんらんが消えたポケモンの再宣言は、UNRESOLVED のまま止める（[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md) 1・2 章）。

## 6. ポケモンチェック × 8 つの状態

`PokemonCheckMatrixTest`（番を終えたあとのポケモンチェック。p.323）:

| 状態 | 2 どく | 3 ねむり | 4 マヒ | こんらん |
|---|---|---|---|---|
| なし | — | — | — | — |
| どく | 10 | — | — | — |
| ねむり（+ どく） | （10） | 持ち主がコイン 1 枚（`source: "pokemon_check"`）。「おもて」で回復 | — | — |
| マヒ（+ どく） | （10） | — | 前の番（相手の番）にマヒ状態になったものは、今の番の終わりに回復（`paralysis_end`） | — |
| こんらん（+ どく） | （10） | — | — | 何もしない（自然に回復しない） |

- 番と番のあいだに `turn_end` と `pokemon_check` が 1 回ずつ。ねむりがなければ乱数を使わない。
- 相手の番にマヒ状態になったポケモンは、その番の終わりには回復せず、持ち主の次の番の終わりに回復する（`test_opponent_paralysis_received_this_turn_does_not_recover_yet`）。
- どくできぜつしたポケモンの特殊状態はいっしょになくなり、ねむりのコインは投げない。ベンチから出たポケモンは特殊状態なし（`test_poison_knock_out_in_every_exclusive_state`）。
- 両方の対戦ポケモンのどくのきぜつ・両方のねむりは止める（[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md) 3・4 章。境界のテストは tests/test_unresolved_rulings_v0_3d.py）。

## 7. 不正な操作と乱数

- 不正な操作（`IllegalActionError`）と原典で決められない操作（`UnsupportedError`）は、渡した状態も乱数も変えません（`apply_command` は複製して処理する）。8 つの状態と操作の組み合わせ（4 章）、決定を待つ間の操作、総合テストのでたらめな操作（9 章）、負荷テスト（10 章）のすべての拒否で確かめました。
- 原典で決められない場合は、コインの前に分かるものはコインの前に止めます。ワザの効果の実装ごとに、受け付けるか・拒否のコードがコインの結果で変わらないことを確かめました（[effect-preflight-v0.3d.md](effect-preflight-v0.3d.md)）。
- コインを投げたあとで内部の例外が起きても、渡した状態・乱数は変わりません（tests/test_self_damage.py `ErrorAfterCoinAtomicityTest`、test_sleep_paralysis.py `test_internal_error_after_the_coin_leaves_the_input_unchanged`）。

## 8. 不変条件

特殊状態に関わる不変条件（`check_invariants`）は次のとおりです。v0.3d で加えたのは最後の 1 つです。

| 不変条件 | 版 |
|---|---|
| `conditions` は `SpecialConditions`。`poison` は `Poison` か None、`exclusive` は `Asleep`・`Paralyzed`・`Confused`・None（知らない型は違反） | v0.3a〜v0.3c |
| ベンチのポケモンに特殊状態がない | v0.3a |
| マヒ状態になった番は、1 以上・今の番以下の整数。回復する番を過ぎたマヒが残っていない | v0.3b |
| 番の進行（番と番のあいだに `turn_end` → `pokemon_check` が 1 回ずつ） | v0.3a |
| 「にげる」の失敗の記録は、今の番・番のプレイヤーのポケモン・番の終わりの前にだけある | v0.3c |
| **失敗の記録は、今の番のログの `retreat_failed`（同じ `pokemon_id`）と対応する** | v0.3d |

最後の不変条件は、失敗していないポケモンに記録が付く不具合（記録を付け間違える、特殊状態を消す処理や将来の進化が記録を書きかえる）を見つけるためのものです。v0.3c までは記録の番・持ち主だけを見ていたので、記録をほかのポケモンに付けても見つけられませんでした（変異テストで確かめた。11 章）。`tests/helpers.py` の `build_test_state` は、`retreat_failed_turn` を指定したポケモンに、対応するログを置くようにしました。

## 9. 新しい対戦からの総合テスト

tests/test_status_games_v0_3d.py。60 枚のデッキ・サイド 6 枚の正式な開始（`new_game`）から勝敗まで。手順は test_confusion_games.py の `confusion_policy_command`（対戦相手の AI ではない）。

| デッキ | 内容 |
|---|---|
| A | ビードル 3・パラス 3・キャタピー 3・ロコン 3・ピカチュウ 4・ポケモンいれかえ 2・プラスパワー 2・ディフェンダー 2・マサキ 2・きずぐすり 2・草 18・炎 8・雷 8 |
| B | ビードル 3・パラス 3・キャタピー 3・ロコン 3・ドードー 4・ポケモンいれかえ 2・マサキ 2・ディフェンダー 2・草 22・炎 16 |

特殊状態を直す手順（seed 0〜19。にげる・ポケモンいれかえで直す）20 局と、直さない手順（seed 300〜323）24 局、合わせて 44 局で数えた回数（`EXPECTED_COUNTS`。手順・デッキ・乱数の使い方が変わると変わる）:

| 項目 | 回数 | 項目 | 回数 |
|---|---|---|---|
| どくにした（うち `already`） | 123（1） | ねむりにした | 271 |
| マヒにした | 142 | こんらんにした（うち `already`） | 68（4） |
| どく + ねむり（局ごとの組） | 5 | どく + マヒ | 4 |
| どく + こんらん | 1 | ねむりでワザ・にげるを拒否 | 131・153 |
| マヒでワザ・にげるを拒否 | 108・135 | こんらんのワザ「おもて」・「うら」 | 17・23 |
| こんらんのにげる「おもて」・「うら」 | 20・26 | `RETREAT_ALREADY_FAILED` | 23 |
| `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` | 2 | ねむりの回復・継続 | 229・225 |
| マヒの回復（`paralysis_end`） | 132 | にげるで消えた（どく・こんらん） | 51・20 |
| ポケモンいれかえで消えた（どく・ねむり・マヒ・こんらん・どく + マヒ） | 5・8・6・8・1 | 自分へのダメージ（でんげき） | 14 |
| ワザのあとのきぜつ | 269 | ポケモンチェックのきぜつ | 52 |
| 勝敗が決まった局 | 44 | 止まった局（HALTED） | 0 |

- ねむり・マヒ・こんらんのあいだの置きかえ（`replaced`）は、この 44 局では起こりませんでした。単体テスト（2 章）と負荷テスト（10 章）で確かめています。
- どの局も、対戦準備のあとの乱数はコインだけに使われ、コインの結果は乱数の列と一致し、番と番のあいだのポケモンチェックは 1 回、回復する番を過ぎたマヒは残りません。2 局は、同じコマンドを送り直して同じ状態になることを確かめました。
- 固定値の局（seed 2。230 コマンド・87 番で勝敗。ねむり 24・どく 3・こんらん 4・マヒ 1 回、どく + ねむりが重なる）の状態の SHA-256 は、Python 3.11・3.12・3.13 で同じです。
- でたらめな操作を混ぜた 12 局（`RandomCommandsWithAllConditionsTest`）では、すべての拒否で状態と乱数が変わりません。

## 10. 負荷テスト

作業用のスクリプト（リポジトリには入れない）で、9 章の 2 つのデッキを使って動かしました。

**自然な対戦 400 局**（seed 2000〜2399、直す手順と直さない手順を交互）:

| 結果 | 局数 |
|---|---|
| 勝敗が決まった（`GAME_OVER`） | 398 |
| 止まった: `UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT` | 2 |

| 項目 | 回数 | 項目 | 回数 |
|---|---|---|---|
| どく・ねむり・マヒ・こんらんにした | 1,247・2,290・1,489・634 | うち `already`（どく・こんらん） | 19・86 |
| 置きかえ（こんらん・ねむりが消えた） | 7・4 | どく + ねむり・マヒ・こんらん | 50・2・17 |
| ねむりでワザ・にげるを拒否 | 1,141・1,276 | マヒでワザ・にげるを拒否 | 1,161・1,433 |
| こんらんのワザ「おもて」・「うら」 | 187・215 | こんらんのにげる「おもて」・「うら」 | 214・263 |
| `RETREAT_ALREADY_FAILED` | 227 | `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` | 26 |
| ねむりの回復・継続 | 1,957・1,887 | マヒの回復（`paralysis_end`） | 1,371 |
| 自分へのダメージ | 167 | ワザのあと・ポケモンチェックのきぜつ | 2,544・555 |

すべての局で、対戦準備のあとの乱数はコインだけに使われ、コインの結果が乱数の列と一致しました。

**でたらめな操作を混ぜた 200 局**（seed 7000〜7199、1 局 500 操作まで。正しい手順 55%・でたらめな「にげる」15%・でたらめなコマンド 30%）:

| 結果 | 局数 |
|---|---|
| 500 操作で終わらない | 99 |
| 勝敗が決まった | 98 |
| 止まった: `UNRESOLVED_MULLIGAN_COMPENSATION`（v0.1 から） | 2 |
| 止まった: `UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT` | 1 |
| 内部の例外 | 0 |

- 拒否は 44,926 回（`IllegalActionError` のうち多いもの: `POKEMON_PARALYZED` 12,908・`NOT_YOUR_TURN` 7,959・`POKEMON_ASLEEP` 7,807・`INVALID_PLAYER` 3,876・`NOT_TRAINER` 2,871・`WRONG_PHASE` 2,866・`WRONG_RETREAT_COST` 1,669・`RETREAT_ALREADY_FAILED` 1,146。`UnsupportedError`: `UNRESOLVED_POTION_WITHOUT_DAMAGE` 15・`UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` 12・`UNRESOLVED_SWITCH_WITHOUT_BENCH` 6）。**すべての拒否で、渡した状態と乱数が変わりませんでした。** 受け付けた操作でも渡した状態は変わらず、返した状態は不変条件を満たしました。
- `UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED` と `UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER` は、自然な対戦・でたらめな操作のどちらでも起こりませんでした。前者は、失敗した番にポケモンいれかえなどで 2 回入れ替える必要があり（v0.3c の負荷テストでは 7 回）、後者は、ねむりのポケモンはワザを使えないので、対応カードでは両方の対戦ポケモンが同時にねむりになりません（[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md) 4 章）。どちらも、起こる盤面をテストで直接作って確かめています。

## 11. 変異テスト

作業用のスクリプト（リポジトリには入れない）で、実装を 1 か所ずつ壊し、v0.3d のテストと特殊状態のテスト（test_special_conditions_matrix_v0_3d・test_effect_preflight_v0_3d・test_unresolved_rulings_v0_3d・test_status_games_v0_3d・test_confusion・test_confusion_retreat・test_self_damage・test_pokemon_check・test_rng_and_serialize・test_turns）が失敗するかを見ました。構文の誤り・名前の誤り（`SyntaxError`・`IndentationError`・`NameError`）で失敗した変異は、検出に数えない決まりにしました（該当はなかった）。

| # | 変異 | 結果 |
|---|---|---|
| 1 | ねむり・マヒ・こんらんの上書きで、どくも消える | 検出（17 件が失敗） |
| 2 | ほかの排他的な状態があると上書きしない | 検出 |
| 3 | 上書きで、前の状態が消えたログを残さない | 検出 |
| 4 | こんらんのコインを 2 枚投げる | 検出 |
| 5 | 不正なコマンドで状態・乱数が変わる（複製しない） | 検出 |
| 6 | 特殊状態を消すと、にげる失敗の記録も消える | 検出 |
| 7 | マヒが 1 つ早い番に回復する | 検出 |
| 8 | ポケモンチェックを二重に記録する | 検出 |
| 9 | どくによるきぜつを無視する | 検出 |
| 10 | ワザの `problem` をコインの前に聞かない | 検出 |
| 11 | こんらんの変更効果の未解決をコインの前に確かめない | 検出 |
| 12 | 形式 1〜5 で、にげる失敗の記録を黙って落とす | 検出 |
| 13 | 形式 1〜4 で、特殊状態を黙って落とす | 検出 |
| 14 | にげる失敗の記録とログの対応を確かめない（v0.3d の不変条件） | 検出 |
| 15 | 自分へのダメージに弱点・抵抗力を計算しない（v0.2f の旧扱い） | 検出 |
| 16 | にげる失敗のあとの再宣言を拒否しない | 検出 |
| 17 | 両方がどくできぜつしても止めない | 検出 |
| 18 | 両方がねむりでも止めない | 検出（止まらずに `halt` がないことで失敗） |
| 19 | マヒの再付与の未解決を通す | 検出 |

19 種類すべてを検出しました。v0.3c の変異テスト（30 種類）は [architecture-v0.3c.md](architecture-v0.3c.md) 13 章にあります。

## 12. 見つかったこと

| 事項 | 分類 | 対応 |
|---|---|---|
| 特殊状態の付与・上書き・解除・操作・ポケモンチェックに、原典と違う動きは見つからなかった | — | 実装の動きは変えていない（付ける処理の共通化だけ。3 章） |
| 失敗の記録の不変条件が、記録の付け間違いを見つけられなかった | 検査の不足 | ログとの対応を不変条件に加えた（8 章） |
| v0.2f の自分へのワザのダメージの弱点・抵抗力 | UNRESOLVED → **SUPPORTED** | p.90 の解説で決まった。止める処理を外し、弱点・抵抗力を計算する（[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md) 6 章）。対応カード（ピカチュウ）の結果は変わらない |
| こんらん・ポケモンチェックの 5 つの未解決 | UNRESOLVED のまま | 止める処理を維持（[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md) 1〜5 章） |
| ねむり・マヒ・こんらんのあいだの置きかえは、自然な対戦ではまれ | 観察 | 単体テスト・負荷テストで確かめた |
