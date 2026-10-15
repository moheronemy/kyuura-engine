# 突風（v0.21）: 照合済みの記録の再利用と実装

v0.21 で、トレーナーの突風（PMCG1-072。ポケモンカード第1弾）を対応にしました。`CLAUDE.md` の「照合済みの記録の再利用」（[verified-record-reuse.md](verified-record-reuse.md)）の手順を当てはめ、入れ替えの規定など既存の記録で決まるものは読み直していません。記録のなかったこのカードのページ（p.255 の突風）だけを原典で確かめました。

- 基準のルール: 「ポケットモンスターカードゲーム公式ルール 2000.02.14版」（『ポケモンカードオフィシャルブック2000』pp.306〜326 [P43]）
- カードの処理: 同じ本のカードのページの「最新の説明」（p.6「この本の使いかた」。[trainers-v0.2b.md](trainers-v0.2b.md) の前提と同じ）
- カードデータ: kyuura `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`（写しの元。変えていない）。研究の基準: kyuura `3f349085645f47d0649a6cacece3680caeae50bf`（変えていない）
- 分類（CONFIRMED・SUPPORTED・UNRESOLVED・CONFLICT）の意味は [trainers-v0.2b.md](trainers-v0.2b.md) 1 章と同じ

## 1. 既存の記録を探した結果（手順の 1〜5）

| 探した記録 | 結果 | 使い方 |
|---|---|---|
| kyuura `data/cards.json`（`ecb2d69`・`3f34908` で同じ） | PMCG1-072 突風。文面「相手の場の対戦ポケモンと控えポケモンを入れ替える。どの控えポケモンを出させるかは、自分が自由に選ぶことができる。相手に控えがいない場合は使えない。」（なぞのばしょの転記。第1弾の印刷）。種類（`kinds`）なし | 登録の照合（`TrainerEntry.text_ja`）だけに使う。処理の根拠にはしない |
| kyuura のサイドカー（LD-・CC-・CR-・UQ-） | このカードの記録はない。控えがいないときの論点（UQ-）もない | — |
| kyuura `data/rule_history.json` の P43 のページの記録 | p.255 の記録はない | — |
| kyuura `docs/cards/reprints.md`（`data/curation/other_products.json` の `reprint_text` から生成） | 再録の文面の変更（「相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える」に）を「書き方だけ」（`wording`）と分類。控えがいないときの一文がなくなったことの根拠は書かれていない | **裁定の根拠にしない**（裁定・照合の記録ではなく、根拠のない分類）。報告事項（7 章） |
| `kyuura_engine/data/card_verification.json` | このカードの記録はない | — |
| docs/trainers-v0.2b.md 2 章（トレーナー共通）・5 章（ポケモンいれかえ） | p.310 のトレーナーの使いかた（手順 1〜4・使いすて・使うための条件・使っている最中はほかのことをしない）、入れ替えの規定（にげるではない・にげるエネルギーを払わない・ついているカードとカウンターはいっしょに移動・特殊状態と持続する効果は消える・ねむり・マヒでも入れ替える・「バトル場をはなれられない」状態。p.311・p.322・p.325）、控えがいないときのポケモンいれかえ（UNRESOLVED）。2026-10-12 に画像で照合した記録 | **再利用**（対象: トレーナーの効果による「ポケモンの入れ替え」。ルールの版は同じ） |
| docs/forced-switch-v0.4d.md（F1〜F16） | ワザの効果による相手の入れ替え（ふきとばし）: 相手が選ぶ（F3。p.19 の最新の説明「入れ替わるポケモンは、相手が選ぶ」）、F8〜F12（特殊状態・持続する効果・カードと番号・ねむり・マヒ・にげるではない）、F13（「にげる」の失敗の記録は番のプレイヤーのポケモンにだけ付く） | F8〜F13 の入れ替えの規定は**再利用**。選ぶプレイヤー（F3）と処理（`FORCED_SWITCH`）は**使わない**（突風は選ぶプレイヤーが違う） |
| docs/transparency-v0.9.md の T29 | トレーナーによるダメージや効果は受ける（「とうめい」ははたらかない。p.159。CONFIRMED） | **再利用** |
| docs/chemical-gas-v0.8.md の G8 | かがくへんかガスはトレーナーの効果に影響しない（CONFIRMED） | **再利用** |
| docs/conditions（v0.3a〜v0.3c）・docs/persistent-damage-v0.4b.md・v0.12・v0.13 | ベンチにもどったら特殊状態・持続する効果（かたまる・ほのおのかべ・こうらがえし）が消える（p.322）。消すのは `clear_special_conditions`・`remove_persistent_effects`（理由 `switch` はトレーナーの効果による入れ替え） | **再利用**（処理・ログの理由） |

既存の記録で足りなかったもの（原典に戻る前に書いたこと）。どれも突風のカードのページ（p.255）にしかない:

1. G1: このカードの「最新の説明」の文面（だれが選ぶか。相手に控えがいないときに使えるかが書かれているか）。
2. G2: 図版の文面が kyuura の写しと同じか（写しの照合）。
3. G3: 解説に、処理に関わる記述（選ぶプレイヤー・控えがいないとき）があるか。
4. G4: 見出し・収録商品。

一般のルール（p.306〜326）・ほかのカードのページは読み直していません。

## 2. 原典で確かめたこと（p.255 の突風だけ。2026-10-15）

Internet Archive のスキャン [J38]（PDF 372 ページ、`PDF n = p.(n-2)`）の PDF 257 ページ（p.255）を、v0.19 で 400dpi にした画像から、見出し・収録・最新の説明、図版、解説の 3 か所を切り出して目で読みました（OCR の文字は使っていません）。p.255 には突風・エネルギー・リムーブ・オーキドはかせがあり、照合したのはいちばん上の突風です。

| 項目 | 内容 |
|---|---|
| 見出し・収録 | 「突風」、収録「ポケモンカード第1弾」「ポケモンジム第1弾カスミ」「ポケモンジム第2弾マチス」「クイックスターターギフトパック」「イントロパック」 |
| 図版の文面 | 「相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える。」（最新の説明と同じ。kyuura の写しと違う）。図版の右下に番号㉘とマークがあり、第1弾の版ではない可能性が高い（kyuura の docs/cards/products/intro-packs.md のイントロパック（フシギダネデッキ）028/040 と番号は合うが、版は確かめていない） |
| 最新の説明 | 「相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える。」 |
| 解説（処理に関わる記述） | 「相手のベンチからポケモンを選んでバトル場に呼んできます。呼んでくるポケモンは、自分の対戦ポケモンが倒せそうなポケモンがよいでしょう。」「相手のベンチのポケモンにエネルギーカードがついてなくて、逃げることができないような大きなポケモンがいたらバトル場に呼んで、時間をかせぎます。」。相手に控えがいないときの記述はない |
| 照合の記録 | `card_verification.json` の PMCG1-072（`status` は「不一致あり」: 図版・最新の説明が kyuura の文面（第1弾の印刷の転記）と違う） |

## 3. 規定（GW1〜GW18）

「再利用」は既存の記録で決まり、今回読み直していないもの。「p.255」は今回読んだもの。テストはどれも tests/test_gust_v0_21.py。

| id | 事項 | 分類 | 根拠 | 実装 | テスト |
|---|---|---|---|---|---|
| GW1 | 処理は最新の説明にしたがう（印刷の文面と違う） | CONFLICT（違いは「どの控えポケモンを出させるかは、自分が自由に選ぶ」の書き方と、控えがいないときの一文。GW5） | p.255 の最新の説明・図版。kyuura の写しは第1弾の印刷。p.6 | `TrainerEntry.play_text_ja` に最新の説明、`text_ja` に写しの文面 | `RegistrationTest.test_entry_follows_the_verified_latest_description` |
| GW2 | 相手の控えポケモンを選ぶのは、突風を使ったプレイヤー | CONFIRMED | p.255 の最新の説明「相手の控えポケモンを1匹選び」（主語は使うプレイヤー。ふきとばしの最新の説明の「入れ替わるポケモンは、相手が選ぶ」（p.19）のような書き方はない）。p.255 の解説「相手のベンチからポケモンを選んでバトル場に呼んできます。呼んでくるポケモンは、自分の対戦ポケモンが倒せそうな…」。ポケモンいれかえの「1匹選び」も使うプレイヤーが選ぶ（再利用: trainers-v0.2b.md 5 章） | 決定（`SELECT_POKEMON`）の `player` は使ったプレイヤー。番のプレイヤー・番の番号は変えない。ふきとばしの処理（`FORCED_SWITCH`。相手が決定する）は使わない | `ChoiceTest.test_decision_belongs_to_the_user`・`test_opponent_cannot_answer`・`RegistrationTest.test_no_card_specific_branch_and_no_forced_switch` |
| GW3 | 選べるのは相手のベンチのポケモン（控えポケモン）だけ。自分の場のポケモン・相手の対戦ポケモン・場にいないものは選べない。1 匹を選ぶ | CONFIRMED | p.255 の最新の説明「相手の控えポケモンを1匹選び」 | 選べるもの = 相手のベンチの場のポケモンの番号（`pokemon_id`。ベンチの並び）。1〜1 個 | `ChoiceTest.test_invalid_choices_keep_the_decision_waiting`・`test_choosing_a_specific_one_among_many` |
| GW4 | 相手の控えが 1 匹でも決定を出す | 実装上の判断（ポケモンいれかえと同じ） | 再利用: trainers-v0.2b.md 5 章（「入れ替える対象はプレイヤーが選ぶ」。1 匹でも決定を出す） | 決定の選べるものが 1 つ | `UsableTest.test_one_opponent_bench_pokemon_is_enough_and_own_bench_does_not_matter` |
| GW5 | 相手に控えポケモンがいないとき | **UNRESOLVED** | p.255 の最新の説明・図版・解説に書かれていない。再利用: p.310（トレーナーの使いかた）・p.311（「控えがいなければ宣言できない」は「にげる」の規定）。ポケモンいれかえの同じ場合も UNRESOLVED（v0.2b）。第1弾の印刷の文面の「相手に控えがいない場合は使えない」は最新の説明にないので使わない（印刷の文面で補わない。p.6）。一文がなくなったことを「使える（効果なし）」と読むこともできない。同じ本のふきとばしの最新の説明は控えがいないときを括弧で書く（p.19）が、書いていないカードの扱いは決まらない | `check_playable` が `UnsupportedError("UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH")`。カードを手札から出す前に止め、状態・乱数・ログは変わらない | `UsableTest.test_opponent_without_bench_is_unresolved` |
| GW6 | 自分の場（自分のベンチの有無）は関係しない | CONFIRMED | p.255 の最新の説明は相手の場だけを指す。使うための条件はない（再利用: p.310） | 自分の場を見ない | `UsableTest.test_one_opponent_bench_pokemon_is_enough_and_own_bench_does_not_matter`・`test_opponent_without_bench_is_unresolved`（自分のベンチの有無で同じ） |
| GW7 | 「にげる」ではない。にげるエネルギーを払わず、使ったプレイヤーの「にげる」にも関わらない | CONFIRMED | 再利用: p.310〜311（にげるの手順）・p.325「「にげる」も、この「ポケモンの入れ替え」にふくまれます」（trainers-v0.2b.md 5 章・F12） | `_switch_active_with_bench`（にげるの処理を使わない） | `SwitchedPokemonTest.test_no_retreat_cost_and_retreat_is_unaffected` |
| GW8 | ついているカード（エネルギー・ディフェンダー。有効期限も）・ダメージカウンター・進化の重なりはポケモンといっしょに移る。場のポケモンの番号は変わらない | CONFIRMED（カード・カウンター）・SUPPORTED（p.311 のにげるの手順の文を入れ替えに当てる）・実装上の仮定（番号） | 再利用: p.311「ポケモンを移動させるときは、そのポケモンについているすべてのカード…いっしょに移動」（trainers-v0.2b.md 5 章・F10） | 場のポケモン（`PokemonInPlay`）ごと入れ替える。もとの対戦ポケモンは、選んだポケモンがいたベンチの位置に入る | `SwitchedPokemonTest.test_conditions_persistent_effects_and_attached_cards`・`test_attached_defender_still_expires_at_its_turn`・`ChoiceTest.test_choosing_a_specific_one_among_many` |
| GW9 | ベンチにもどった相手のポケモンの特殊状態（どく・ねむり・マヒ・こんらん）は消える | CONFIRMED | 再利用: p.311・p.322（F8。trainers-v0.2b.md 5 章） | `clear_special_conditions(..., SWITCH)`（ログ `special_conditions_removed`、`player` は相手、理由 `switch`） | `SwitchedPokemonTest.test_conditions_persistent_effects_and_attached_cards` |
| GW10 | ベンチにもどった相手のポケモンのワザによる持続する効果（かたまる・ほのおのかべ・こうらがえし）は消える | CONFIRMED | 再利用: p.322（F9・v0.4b・v0.12・v0.13） | `remove_persistent_effects(..., SWITCH)`（ログ `persistent_effect_removed`、理由 `switch`） | 同上 |
| GW11 | ねむり・マヒ状態の相手の対戦ポケモンでも入れ替える | CONFIRMED | 再利用: p.325（F11。trainers-v0.2b.md 5 章） | 状態を見ない | 同上（ねむり・マヒの場合） |
| GW12 | 「にげる」の失敗の記録 | 起こらない（実装上の仮定。不変条件で成り立つ） | 再利用: F13（記録は番のプレイヤーのポケモンにだけ付き、番の終わりに消える。v0.3c。p.311）。突風を使う番に相手のポケモンには記録がない | 消さない・付けない | `SwitchedPokemonTest.test_no_retreat_cost_and_retreat_is_unaffected` |
| GW13 | 相手の「とうめい」ははたらかない（トレーナーの効果は受ける） | CONFIRMED | 再利用: p.159（T29） | `attack_reaches` を呼ばない。乱数を使わない | `SwitchedPokemonTest.test_transparency_is_not_evaluated` |
| GW14 | かがくへんかガスは突風に影響しない | CONFIRMED | 再利用: G8（p.48・p.309・p.310） | 確かめない | （既存の `OtherActionsTest` の規定。突風で別に確かめていない） |
| GW15 | 使っても番は続く。そのあとワザ・にげるなどができ、ワザは入れ替えで出た相手の対戦ポケモンに当たる | CONFIRMED | 再利用: p.310（トレーナーは自分の番に使い、すませたら番の続き） | `engine._finish_trainer` が `Phase.MAIN` にもどす（既存） | `TurnAndConservationTest.test_same_turn_continues_and_the_attack_hits_the_new_active`・`NaturalGamesTest` |
| GW16 | 「バトル場をはなれられない」状態のポケモン | 該当なし（その状態を持つカードがない） | 再利用: p.325「21」「22」（trainers-v0.2b.md 5 章の将来の処理） | なし。その状態を加えるときに、突風の扱い（使えるか・何も起きないか）を原典で確かめる | — |
| GW17 | 使っているカードの場所: 決定を待つ間は使用中（手札にもトラッシュにもない）、すませたらトラッシュ。宣言の拒否ではカードは手札のまま、不正な選択の拒否では決定を待ったまま使用中 | CONFIRMED（p.310 の手順 1〜4。再利用）・実装（決定の仕組み。v0.2a・v0.2b） | 再利用: p.310 | `trainer_in_use`・`push_trainer_decision`・`check_choices`（既存） | `ChoiceTest`・`UsableTest.test_rejected_declarations_do_not_change_state`・`TurnAndConservationTest.test_card_conservation_and_the_caller_state` |
| GW18 | ログ `switch` の `player` は入れ替わる場の持ち主（突風では相手）。選んだのは直前の `play_trainer` の `player` | 実装上の判断（ログの意味の明記） | — | 項目は加えていない（ポケモンいれかえのログと同じ形） | `TurnAndConservationTest.test_switch_trainer_on_own_side_is_unchanged`・`NaturalGamesTest` |

## 4. 実装

- `effects.SwitchOpponentWithBench`（`implementation_id` `switch_opponent_with_bench`）を `TrainerEntry` で PMCG1-072 に登録しました（`DEFAULT_EFFECTS` の id は `kyuura-engine-0.13` のまま。v0.17〜v0.20 と同じく変えていない）。
  - `check_playable`: 相手のベンチが空なら `UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH`（GW5）。
  - `resolve`: `push_trainer_decision(kind=SELECT_POKEMON, player=使ったプレイヤー, options=相手のベンチの pokemon_id)`（GW2・GW3）。
  - `resume`: `_switch_active_with_bench(state, 相手, 選んだ pokemon_id)`。
  - `decision_problems`: 決定するのは使ったプレイヤー・種類・1 匹・選べるものが相手のベンチ（不変条件が決定を待つたびに確かめる）。v0.4e の `_select_own_pokemon_problems` に、理由の文に書く持ち主（`whose`）を加えて使っています（確かめる中身は同じ）。
- 入れ替えの処理は、v0.20 までの `SwitchWithBench.resume` の本体を、そのまま関数 `effects._switch_active_with_bench(state, owner, pokemon_id)` にしました。ポケモンいれかえ（`owner` は使ったプレイヤー）と突風（`owner` は相手）が同じ関数を呼びます。突風だけの入れ替えの処理はありません。ポケモンいれかえの動き・ログは変わりません（固定した v0.20 との比較。[v0.21-verification.md](v0.21-verification.md) 4 章）。
- ふきとばしの処理（`resolution/programs.py` の `FORCED_SWITCH`・ログ `forced_switch`・「とうめい」の判定）は使いません。ふきとばしは相手が選ぶワザの効果で、ログの監査はログ `forced_switch` を「とうめい」の判定の対象（ワザの効果）として確かめるので、突風の入れ替えに使うと規定（T29）にも反します。
- `engine.py`・`kyuura_engine/resolution/` は変えていません（カード id での分岐もない。`RegistrationTest.test_no_card_specific_branch_and_no_forced_switch`）。決定の仕組み・使用中のカード・不変条件も既存のものです。
- 書き出しは形式 9 のまま（状態の項目を加えていない）。決定を待つ間の状態は、使用中のトレーナーがあるので形式 3 以上で書き出せます（形式 1・2 は `ValueError`。v0.2b から同じ）。

### ログ

新しいイベントの種類・項目はありません。突風を使うと `play_trainer`（`player` は使ったプレイヤー）→ `switch` → （あれば）`special_conditions_removed`・`persistent_effect_removed` → `discard_trainer` の順です。`switch`・`special_conditions_removed`・`persistent_effect_removed` の `player` は入れ替わる場の持ち主（相手）です。ポケモンいれかえでは使ったプレイヤーと持ち主が同じだったので、v0.21 で `switch` の `player` の意味を「入れ替わる場の持ち主」と明記しました（値はポケモンいれかえでは変わらない）。ログを読む側は、突風で選んだプレイヤーを直前の `play_trainer` の `player` で知ります。決定の答えはログに残りません（v0.2a から同じ）。

## 5. 未解決と変えていないもの

- 新しい未解決: GW5（`UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH`）。エンジンが止める `UNRESOLVED_…` は 19 件、未解決の裁定は 25 件になりました（v0.20 までの 18 件・24 件は変えていない）。kyuura に論点がないので、研究の対応表（`research_links.json`）では `kyuura_disposition` を `not_in_kyuura` にしています（報告事項。kyuura に記録ができたら `scripts/check_research_links.py` が知らせる）。
- ポケモンいれかえの `UNRESOLVED_SWITCH_WITHOUT_BENCH`（v0.2b）は、突風とは別のカードの別の問いとして、そのままです（解消していない）。ふきとばしの「控えがいなければ入れ替えない」（F4。ワザの説明の規定）も変えていません。
- 既存のカードの裁定・確度の分類、固定した参照データ（tests/fixtures/）、研究の基準・写しの元のコミット、v0.20 の固定のデッキ（`kyuura_engine.decks`）は変えていません。

## 6. 組み合わせの対戦（tools/preset_deck_games.py の `--variant gust`）

v0.20 の 2 つの固定のデッキのディフェンダー 4 枚のうち 3 枚を突風 3 枚に置き換えた一時的な 60 枚どうしで、正式な対戦開始から対戦させました（`deck_cards`。公開の固定のデッキは変えていません）。手順に加えたのは突風の使い方だけです（1 番に 1 回だけ考え、相手の控えポケモンのうち残りの HP がいちばん少ないものが相手の対戦ポケモンより少なければ使い、決定ではそのポケモンを選ぶ。相手に控えがいなければ使わない）。強い AI ではなく、勝率でカードの強さを判断していません。結果の数は [v0.21-verification.md](v0.21-verification.md) 5 章です。

## 7. kyuura への報告事項（kyuura にはコミット・プッシュしない）

1. 突風（PMCG1-072）の照合の記録（CC-）・最新の説明・p.255 のページの記録がない（`research_links.json` の `card_checks.engine_verified_without_kyuura_record` に挙げた。オーキドはかせと同じ）。
2. 相手に控えがいないときに突風を使えるか（GW5）の論点（UQ-）がない（`stop_codes` の `not_in_kyuura`）。
3. `docs/cards/reprints.md`（`data/curation/other_products.json` の `reprint_text`）が、突風の文面の変更を「書き方だけ」と分類しているが、なくなった一文「相手に控えがいない場合は使えない」の扱い（意味が変わらないとする根拠）が書かれていない。エンジンはこの分類を裁定の根拠にしていない。誤りとは決めていない。
4. p.255 の図版の文面は第1弾の印刷の転記と違う（図版は第1弾の版ではない可能性が高い。番号㉘）。写しの文面の誤りではなく、版の違いと考えている（確かめていない）。

## 8. 次にカードを加えるときの注意

- 入れ替えるトレーナー・効果を加えるときは、選ぶプレイヤー（使ったプレイヤーか相手か）を最新の説明で確かめ、見た目が似ていることだけで突風・ポケモンいれかえ・ふきとばしの処理を流用しないでください。入れ替えそのもの（場のポケモンごと動かす・特殊状態と持続する効果を消す・ログ `switch`）は `_switch_active_with_bench` を使います（トレーナーの効果の入れ替え。ワザの効果の入れ替えは `FORCED_SWITCH`）。
- 「バトル場をはなれられない」状態（p.325）を加えるときは、突風・ポケモンいれかえ・ふきとばしの扱いを原典で確かめてください（GW16）。
- 相手の控えポケモンを選ぶ決定は、決定のプレイヤーが番のプレイヤーで、選べるものが相手の場のポケモンです。決定の形の確かめ（`decision_problems`）は `_select_own_pokemon_problems(..., whose="相手")` で書けます。
