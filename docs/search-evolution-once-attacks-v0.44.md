# v0.44: 検索・進化・1 度だけ使えるワザのポケモン 14 枚とトレーナーのサカキ

v0.43（`96a0f1d`。版 0.43.0）から作業ブランチ `claude/v0.44-search-evolution-once-attacks` を作り、依頼の 15 枚（ポケモン 14 枚・トレーナー 1 枚）を加えました
（版 0.44.0）。同じ作業で、このカード群に要る共通の処理（場に出てから 1 度だけ使えるワザの記録・トレーナー「サカキ」の進化の許可・山札から重ねる進化の特殊能力・
手札を山札にもどす要素・相手のトラッシュのカードを相手の山札の上にのせる要素など）を加えました。

1. 依頼の 15 枚を、どのワザも、どの特殊能力も、トレーナーも登録して対応にした（1 章。保留なし。一部だけを登録してカード全体を対応と数えたものはない）。
   対応ポケモン 263 → 277、ワザの登録 455 → 479、特殊能力の登録 29 → 31、トレーナーの登録 11 → 12、写し 284 → 299 枚。
2. v0.43 の相手のポケモンを選ぶダメージ・場に出たときの特殊能力の入口（使う機会・PW3）・特殊能力の決定と再開、v0.24 の見せて手札に加える処理、v0.25・v0.42 の
   進化の手順（`evolution.place_evolution_card`・`evolution_block`）、v0.36 の RD9、v0.39 の GS1、v0.42 の手札にもどす処理を再利用した（3 章）。
3. 新しい共通の処理（3.2 節・4〜6 章）: 場のポケモンの記録 `attacks_used_once`（1 度だけ使えるワザ。宣言のときに記録）・`evolution_permission_turn`（サカキの
   許可。番の終わりに消える）、特殊能力で山札のカードを重ねる進化、ワザの要素 6 つ（トレーナーを見せて手札に加える・自分を山札から進化させる・自分を手札にもどす・
   手札を山札にもどす 2 つ・相手のトラッシュを山札の上にのせる）、ゾーンの関数 2 つ、先読みの答えをカード id でまとめる `card_id_answers`。
4. 新しい未解決は 3 つ（7 章）: FC1（`UNRESOLVED_STATED_CARDS_SHORT`。決まった枚数を選ばせるとき選べるカードが足りない。てじな・ラッキーたまごで共通の 1 つの問い）・
   TR1（`UNRESOLVED_TRAINER_WITHOUT_TARGET`。選ばせる対象がないときのサカキ）と、コードのない問い GV1（サカキの許可のあるポケモンを山札から重ねる効果で進化
   させる。今の対応カードでは起こらない）。停止コード 51 → 53、未解決の裁定 52 → 55（GV1 はコードのない問いで数える。Z9 と同じ）。ほかは既存の問い・コード
   （**v0.45 の訂正**: GV1 は、エリカのピッピの「つきのちから」で、その番に場に出してサカキの許可を受けたサカキのコイキングにサカキのギャラドスを重ねる場面で起こり、
   v0.44 では公開の `apply_command` が内部エラー（RuntimeError）になっていた。v0.45 で停止コード `UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK` を付けた。
   裁定は未解決のまま。[conditional-damage-energy-v0.45.md](conditional-damage-energy-v0.45.md) 2 章）
   （RD9・GS1・PW3・`UNRESOLVED_EVOLUTION_HP`）を使う。1 度だけ使えるワザを相手のワザとして使うのはエンジンの未対応（`UNSUPPORTED_COPIED_ATTACK`。新しいコードではない）。
5. 書き出しの形式 11 を加えた（10 章。形式 10 + 場のポケモンの `attacks_used_once`・`evolution_permission_turn`）。既存の動作は変えていない（固定した v0.43 と
   別のプロセスで比べて食い違い 0。10 章）。

開始の時点で、作業ツリーに未コミットの変更はなく、作業ブランチは v0.43 の最終コミット `96a0f1d` から作りました。ガイドブック（『オフィシャルブック2000』）の
キャプチャ・OCR・画像の読み直しは行っていません。読んでいない原典を確かめたことにする記録は作っていません。英語版の文面を日本語版の処理に持ち込んでいません
（サカキの「or if this is your first turn」・ペルシアンの見せる処理など）。現代のルールで補っていません。研究の基準（kyuura `3f34908`）・カードの写しの元
（`ecb2d69`）・固定した参照データは変えていません。kyuura のデータは変更していません（参照だけ）。

## 1. カードごとの結果

| カード | id | ワザ・特殊能力 | 実装の型（要素の並び） | 結果 |
|---|---|---|---|---|
| ディグダ | PMCG4-038 | じめんにもぐる・ひっかく | v0.43 の `ChooseOpponentPokemonDamage`（文面の書き方を 1 つ加えた）・`DamageOnly` | 対応 |
| ニャース | PMCG4-047 | こばんなげ | `CoinChooseOpponentPokemonDamage`（`ChosenOpponentPokemonDamage` に要素のコイン） | 対応 |
| エリカのフシギダネ | PMCG5-007 | ねむりのたね・おつかい | `SleepOpponent`・`SearchTrainerOnHeads`（`RevealTrainerFromDeck`） | 対応 |
| カスミのヒトデマン | PMCG5-027 | スターブーメラン | `DamageThenReturnSelfToHandOnHeads`（`Damage` → `ReturnAttackerToHand`）。処理に使う文面は LD-PMCG5-027-ATK0 | 対応 |
| コイキング | PMCG4-020 | はねまわる・たきのぼりしんか | `DamageOnly`・`EvolveSelfFromDeck`（`EvolveAttackerFromDeck`） | 対応 |
| キョウのコクーン | PMCG6-011 | どくどくえき・［うか］ | `SpecialPoisonOnHeadsWithoutDamage`（`Status` の特殊などく）・`CoinEvolveSelfFromDeck`（特殊能力） | 対応 |
| キョウのスピアー | PMCG6-018 | しんけいどく・ひっさつばり | `DamageThenPoisonAndParalyzeOnHeads`（1 枚のコイン）・`OnceAfterEntryNoDamageOnTails` | 対応 |
| カモネギ | PMCG1-063 | ネギでたたく・ナベでたたく | `OnceAfterEntryNoDamageOnTails`・`DamageOnly` | 対応 |
| サカキのコイキング | PMCG6-037 | りゅうのきおく・はねまくる | `OnceAfterEntryNoDamageOnTails`・既存の `CoinFlipDamage(3, 10)` | 対応 |
| サカキのギャラドス | PMCG6-040 | あらしをよぶ・りゅうのたつまき | `CoinsAllHeadsSpreadDamageExceptSelf(2, 20)`・`DamageThenSwitchOpponentIfNotKnockedOut` | 対応 |
| ナツメのバリヤード | PMCG6-046 | てじな・ビンタ | `ReturnHandThenRevealBasicEnergy(3)`（`ReturnHandThenRevealEnergy`）・`DamageOnly` | 対応 |
| カツラのマンキー | PMCG6-056 | わるいいたずら・みだれひっかき | `CoinPutOpponentDiscardOnDeckTop`（`OpponentDiscardToDeckTop`）・既存の `CoinFlipDamage(3, 10)` | 対応 |
| _____のラッキー | PMCG6-075 | ラッキーたまご・ラッキーパンチ | `CoinDrawOrReturnHandToDeck(2, 2)`（`Coin` → `Draw` /「うら」`ReturnHandToDeck`）・既存の `CoinBonusDamage(30)` | 対応 |
| サカキのペルシアン | PMCG6-071 | おそいかかる・［ボスをよぶ］ | 既存の `CoinBonusDamage(20)`・`SearchNamedTrainerOnEntry`（v0.43 の `EntryPower`） | 対応 |
| サカキ | PMCG6-095 | （トレーナー） | `EvolutionPermissionForOwnerPokemon("サカキ")` | 対応 |

- 同じ名前の別のカード（ディグダ PMCG1-052・ニャース PMCG2-036・コイキング PMCG1-031）・名前の似た別のカード（ヒトデマン・ラッキー・ペルシアン・わるいペルシアン・
  ギャラドス・カスミのコイキング・サカキのニャース）とは別の id・別のワザで、取りちがえていません（tests の `CardDataTest`）。進化元は名前の完全一致（キョウのコクーンは
  キョウのビードル、キョウのスピアーはキョウのコクーン、サカキのギャラドスはサカキのコイキング、サカキのペルシアンはサカキのニャースから。収録の弾で制限しない）。
- 特殊能力の登録を除くとキョウのコクーン・サカキのペルシアンは、トレーナーの登録を除くとサカキは、分類が未対応になります（ワザだけの登録で対応と数えない）。

## 2. カードデータと pcg-search.com との照合

- 根拠は kyuura データの採用（`kyuura_engine/data/card_sources.json`。15 件。`basis: kyuura_data`・採用したデータのコミット `ecb2d69`・記録した日 2026-10-16）と、
  pcg-search.com の同じ版のページとの照合（15 件。収録・サイトの一覧の番号で版を決めた）。
- 照合の結果は 14 件が `match`、_____のラッキー（PMCG6-075。一覧の番号 097/098）が `differences`: 名前の空欄の下線の数（kyuura は「_____のラッキー」、サイトは
  「_のラッキー」）。この名前から進化するカード・この名前を指す効果はないので処理に影響しません（`affects_behavior: false`）。kyuura のデータ・写しは直さず、
  kyuura への報告事項にしました（`issues`）。
- 処理に使う文面: スターブーメランは kyuura の最新の説明 LD-PMCG5-027-ATK0（「コインを投げて「おもて」なら、自分と自分についているすべてのカードを手札にもどす。」。
  研究の対応表の `registered`。v0.43 までは `kyuura_records_not_registered` にあった）。採用の記録の `kyuura_records` は CR-SHELL-ATTACK-STAR-BOOMERANG
  （返したダメージできぜつしたヒトデマンは手札にもどらない）と LD-PMCG5-027-ATK0。ほかの説明文のあるワザ 19 と特殊能力 2 は kyuura の印刷の文面
  （`adopted_printed_text`。306 → 327）。サカキは kyuura の印刷の文面（`play_text` の `trainer`）。
- 読んでいないガイドブックの項目（`page`・`latest_description_ja` など）は書いていません（`scripts/check_card_sources.py` が拒否する）。採用したカードを
  `card_verification.json` に加えていません。

## 3. 再利用した処理と新しい共通の処理

### 3.1 再利用したもの

- 相手の場のポケモンを選ぶダメージ: v0.43 の要素 `ChosenOpponentPokemonDamage`（決定 `SELECT_POKEMON`。弱点・抵抗力に関係なく）。こばんなげのために要素のコイン
  `local_coin` を加えた（相手に控えがいなくて対戦ポケモンしか選べないときも、コインの前に「ワザをうけない」などの無効を v0.34 の `void_coin_question` で確かめる）。
- 場に出たときの特殊能力: v0.43 の `EntryPower`・`offer_entry_power`（決定 `entry_power`・再開先 `"power"`・`return_to`）・PW3（山札にサカキがない）。
- 特殊能力の決定・再開・回数: v0.42 の `push_power_decision`・`power_uses_this_turn`（宣言のときに記録）・`resolution.after_power`。
- 進化の手順: v0.25 の `evolution.place_evolution_card`（手札からの進化・ポケモン育て屋さん・つきのちからと共通）・v0.42 の `evolution_block`（ワザによる進化でも
  通常の制限を免除しない）。v0.4a の `UNRESOLVED_EVOLUTION_HP`（進化したあとの HP がダメージ以下）。
- 見せて手札に加える・山札を切る: v0.24 の `zones.reveal_deck_to_hand`・v0.22 の `zones.search_deck_to_hand`・`zones.shuffle_deck`・v0.40 の `shuffle_in_attack`。
- 自分を手札にもどす: v0.42 の `zones.return_in_play_to_hand`（きぜつではない。持続する効果を消す理由 `return_in_play_to_hand`）。
- 原典で決められない場合: v0.36 の RD9（同じワザで HP 以上になるポケモンがいるときに場をはなれる）・v0.39 の GS1（「最大N」の 0）・v0.43 の PW3。
- 要素: `Coin`（`AtLeast`）・`Status`（`gate`・`poison_damage`・`reparalysis_check`）・`ForceSwitch(chooser="attacker")`・`BenchDamage(own=True)`・`Damage(local_gate)`・
  `Draw`。

### 3.2 新しく加えた共通の処理

| 処理 | 場所 | 使うカード |
|---|---|---|
| 1 度だけ使えるワザの記録（5 章） | `AttackEffect.once_after_entering_play`・`PokemonInPlay.attacks_used_once`・`checks.attack_request`（`ATTACK_ALREADY_USED`）・`resolution.flow._attack_body`（宣言のときに記録。ログ `once_attack_recorded`） | ネギでたたく・りゅうのきおく・ひっさつばり |
| サカキの進化の許可（6 章） | `PokemonInPlay.evolution_permission_turn`・`evolution.turn_restriction`・`EvolutionPermissionForOwnerPokemon`（ログ `evolution_permission`）・`procedures.expire_at_turn_end` | サカキ |
| 特殊能力で山札のカードを重ねる進化 | `evolution.place_evolution_card(..., power=)`（ログ `evolve` の `power`・`source_zone`）・`CoinEvolveSelfFromDeck` | ［うか］ |
| 山札からトレーナーを見せて手札に加える | 要素 `RevealTrainerFromDeck`（0〜1 枚。ログ `reveal_from_deck`・`reveal_from_deck_declined`・`reveal_from_deck_none` の `category`） | おつかい |
| 自分を山札のカードで進化させるワザ | 要素 `EvolveAttackerFromDeck`（0〜1 枚。ログ `evolve_from_deck_declined`） | たきのぼりしんか |
| 自分を手札にもどすワザ | 要素 `ReturnAttackerToHand` | スターブーメラン |
| 手札を山札にもどす | 要素 `ReturnHandToDeck`・`ReturnHandThenRevealEnergy`・`zones.return_hand_cards_to_deck`（ログ `hand_to_deck`。決定 `hand_to_deck`） | ラッキーたまご・てじな |
| 相手のトラッシュのカードを相手の山札の上にのせる | 要素 `OpponentDiscardToDeckTop`・`zones.put_discard_on_deck_top`（ログ `put_discard_on_deck_top`。決定 `discard_to_deck_top`） | わるいいたずら |
| 先読みの答えをカード id でまとめる | `programs.card_id_answers` | てじな・ラッキーたまご・わるいいたずら・おつかい |

- `card_id_answers`: 手札・山札・トラッシュのカードを選ぶ決定で、同じカード id のカードは区別できない（見えている内容と処理の結果が同じ）ので、先読みは
  カード id の組ごとに 1 つの答えだけを試します（試す数が上限（4,096）を超えないため）。カードの選び方で結果が変わりうる決定（場のポケモン）には使いません。
- engine.py・resolution/ にカード id での分岐はありません（tests の `CardDataTest.test_no_card_specific_branch_in_engine_or_kernel`）。v0.44 のワザの型 12 は
  解決の基盤の要素の並び（`programs.BUILDERS`）で処理し、`v013_checks.VERIFIED` に入れていません（tests/helpers.py の `ATTACK_TYPES_SINCE_V0_17`）。

## 4. 進化・場に出たときの特殊能力・もどり方の経路

| 経路 | 重ねるカードの場所 | 通常の進化の制限（最初の番・その番に出した・進化した） | サカキの許可 | 場に出たときの特殊能力の使う機会 | 終わったあと |
|---|---|---|---|---|---|
| 手札からの進化（`EvolvePokemon`） | 手札 | 当てはめる | その番・その場のポケモンの「その番に出した・進化した」だけを外す | 「手札から」の特殊能力にある（［ボスをよぶ］など） | 番のプレイヤーの MAIN |
| ポケモン育て屋さん | 手札 | 当てはめる（v0.25） | 同上（`skip_evolution_pairs` が `turn_restriction` を使う） | 重ねる 2 進化カードの場に出たときの特殊能力にある（わるいカイリューの［てしたをよぶ］。v0.43。もどり先はトレーナーのトラッシュ）。**v0.45 の訂正**: 1 進化の［ボスをよぶ］（サカキのペルシアン）は育て屋さんで重ねられない（育て屋さんで重ねるのは 2 進化カードだけ）ので、この経路に使う機会はない | トレーナーをトラッシュ → MAIN |
| ワザ（たきのぼりしんか・つきのちから） | 山札 | 当てはめる（`evolution_block(from_deck=True)`） | 許可だけで制限が外れる組は GV1（v0.44 では「今の対応カードでは起こらない」と書いたが、つきのちからで起こる。**v0.45 の訂正**。停止コード `UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK`） | 「手札から」はない、「場に出た時」は PW4（v0.43） | ワザのあと（番は終わる） |
| 特殊能力（［うか］） | 山札 | 当てはめる（同上） | 同上（GV1） | 重ねるカード（キョウのスピアー）に場に出たときの特殊能力はない（あれば RuntimeError。今の対応カードでは起こらない） | 特殊能力の使用後の処理 → MAIN（番は終わらない） |

- サカキの許可は、手札から重ねる進化（通常の操作・ポケモン育て屋さん）の「その番に場に出した」「その番に進化した」の 2 つの制限だけを外します（`turn_restriction`）。
  おたがいの最初の番の制限・名前・段階は変えません（日本語の文面に最初の番の記述はない。英語版の「or if this is your first turn」を持ち込まない）。
- 山札から重ねる効果（ワザ・特殊能力）で、許可だけで制限が外れる組（GV1）は決められません。山札から重ねる効果はどれも「サカキの」ポケモンではない自分自身を
  進化させるので今の対応カードでは起こらず、コードのない問い（当たったらエンジンの不具合として止める）にしました（7 章）。
  **v0.45 の訂正**: この理由は誤りでした。たきのぼりしんか・［うか］は自分自身を進化させますが、つきのちから（エリカのピッピ）は自分の場のほかのポケモンを進化させる
  ので、許可を受けたサカキのコイキングにサカキのギャラドスを重ねる場面で GV1 に当たり、v0.44 では内部エラーになっていました。v0.45 で停止コード
  `UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK` を付けました（裁定は未解決のまま。[conditional-damage-energy-v0.45.md](conditional-damage-energy-v0.45.md) 2 章）。
- ［ボスをよぶ］は「手札から場に出した時」（`from_hand_only`）なので、使う機会は手札からの進化とポケモン育て屋さんで出ます（v0.43 の入口のまま）。使うかは持ち主が
  決めます（自動的にはたらく形にしない）。使えば山札のサカキ（名前の完全一致。「サカキの切り札」などは選べない）を 1 枚手札に加え（`search_deck`。見せる指示が
  ないのでカードは非公開）、山札を切ります。
  **v0.45 の訂正**: 「ポケモン育て屋さんで出ます」は誤りでした。サカキのペルシアンは 1 進化カード（ニャースから進化）で、ポケモン育て屋さんが重ねるのは 2 進化カード
  だけなので、育て屋さんで［ボスをよぶ］の機会は出ません（v0.44 の動作は正しく、文書だけの誤り）。［ボスをよぶ］の実際の経路は、手札のサカキのペルシアンで
  ニャースを通常の手順で進化させることだけです。育て屋さんで場に出たときの特殊能力の機会が出る例は、2 進化のわるいカイリュー（［てしたをよぶ］。v0.43）です。
- スターブーメラン（手札へ）・わるいいたずら（相手の山札の上へ）・てじな・ラッキーたまご（自分の山札へ）は、どれもきぜつではありません（サイド・ログ `knock_out`・
  きぜつしたときの特殊能力はない）。空いたバトル場は、ワザのあとの勝ち負けの判定とバトル場に出す決定でうめます（控えがいなければ負け）。

## 5. 場に出てから 1 度だけ使えるワザの記録

- 記録は場のポケモンの `PokemonInPlay.attacks_used_once`（(カードの uid, ワザの位置) のタプル）です。過去のログを読み直して数えません（ログは記録で、状態の正本では
  ない）。場のポケモンの番号は場をはなれると無効で使い回さないので、場をはなれたら（きぜつ・手札・山札にもどる）記録もなくなり、もう一度場に出たら新しいポケモン
  として使えます（「このカードが場に出てから」）。ベンチにもどる・進化するだけでは同じポケモンなので記録は残ります（進化したあとのカードにそのワザがなければ関係しない）。
- 記録する時点はワザの宣言のとき（ログ `attack` のすぐあとの `once_attack_recorded`。手順 4 のコイン・こんらんのコインより前）です。p.323 の 12（v0.3d の A12。
  CONFIRMED）により、こんらんの「うら」・手順 4 のコインの「うら」・ワザのコインの「うら」でダメージを与えなくても「ワザを使った」ことになるので、記録します
  （説明の「(その場合も、ワザは使ったことになる)」とも合う）。宣言できないとき（エネルギー不足・ねむり・マヒ・使えないワザ）は記録しません。
- 2 回目の宣言は、エネルギーの確認の前に `IllegalActionError("ATTACK_ALREADY_USED")` で拒否します（状態・乱数・ログは変わらない）。
- 相手のワザとして使う（ゆびをふる・ちょうのうりょく）場合、記録をどのポケモンに付けるか（まねたポケモン・まねられたポケモン）が表せないので、エンジンの未対応
  （`unsupported_choices`・`UNSUPPORTED_COPIED_ATTACK`）にしました。原典の未解決ではありません（新しい問いにしない）。
- 不変条件 `engine._once_attack_problems`: 形・対戦準備でない・重複なし・カードが重なりにある・ワザの位置・登録が 1 度だけ使えるワザ・対応するログ
  `once_attack_recorded` がある。ログの監査は、宣言のすぐあとの記録・同じポケモンの 2 回目の宣言がないこと・状態の記録とログの記録が同じことを確かめます。

## 6. サカキの許可

- 説明（kyuura の印刷の文面）: 「あなたの場にいる「サカキのポケモン」を1匹選ぶ。あなたがのぞむなら、そのポケモンが場に出たのが今の番でも、そのポケモンを進化させて
  よい。また、進化したそのポケモンを、同じ番で、さらに進化させてもよい。(ポケモンを進化させる時には、あなたの手札から「進化カード」を出して、そのポケモンの上に
  のせる)」。カードの文面がルールに優先する（GR-2000-P307-CARD-OVER-RULE）ので、許可のあるポケモンには p.310 の制限のうち 2 つを当てはめません。
- 選ぶのは使ったプレイヤー（決定 `SELECT_POKEMON`。選べるのは自分の場の、名前が「サカキの」で始まるポケモン）。答えで、そのポケモンの `evolution_permission_turn` に
  今の番を記録し、ログ `evolution_permission`（`trainer` は使ったサカキの uid）を残します。進化させるかは持ち主が決めます（「のぞむなら」。進化させなくてもよい）。
- 許可はその番だけで、番の終わり（`procedures.expire_at_turn_end`）に消えます。許可を状態に持つのは、ログを読み直して判断しないためです（記録の寿命: 許可を与えた
  番の終わりまで。場をはなれたらポケモンごとなくなる）。
- 不変条件 `engine._evolution_permission_problems`: 今の番・持ち主が番のプレイヤー・番の終わりのあとでない・今の番のそのポケモンの `evolution_permission` がある
  （サカキのポケモンかは、登録したトレーナーの実装の `owner` で確かめる。カード id で分けない）。進化の不変条件は、許可が進化より前にあるときだけ「場に出た番と
  進化した番が同じ」「同じ番の 2 回の進化」を許します（`_evolution_permitted`。許可のない場合の確認は変えていない）。
- 自分の場にサカキのポケモンがいないときにサカキを使えるかは決められない（TR1。使う前に `UnsupportedError`）。サカキはおたがいの最初の番にも使えますが、進化は
  `FIRST_TURN_EVOLUTION` で拒否します。

## 7. 新しい未解決・既存の問い・エンジンの未対応

| id | 分類 | 内容 | 止める場所 | 止めない隣の場合 |
|---|---|---|---|---|
| FC1 | 原典の未解決（新規。`UNRESOLVED_STATED_CARDS_SHORT`。問い `stated_cards_short`） | 説明が決まった枚数を選ばせるとき（ラッキーたまごの「カードを2枚選び」・てじなの「もどしたのと同じ枚数」）、選べるカードがその枚数より少ない場合に、選べるだけ選ぶのか、その内容を処理しないのか（山札を切るか）。p.309 の「処理の対象がなくなってしまっている場合」は対象がないときの規定で、足りないときを書かない | ラッキーたまご: 手札が 2 枚より少ないとき、ワザの宣言の前（「うら」がありうる。どの先読みでも）。てじな: もどした枚数より山札の基本エネルギーカード（もどしたカードを含む）が少なく 1 枚以上のとき、段階 1 の答え（決定は待ったまま） | 手札が 2 枚以上・足りる枚数・山札の基本エネルギーカードが 0 枚（選び出す対象がないので見せずに切る。p.309） |
| TR1 | 原典の未解決（新規。`UNRESOLVED_TRAINER_WITHOUT_TARGET`） | 自分の場に説明が選ばせる「サカキのポケモン」がいないときにサカキを使えるか | 使う前（`check_playable`） | サカキのポケモンが 1 匹以上 |
| GV1 | 原典の未解決（新規。コードのない問い `evolution_permission_from_deck`。今の対応カードでは起こらない。**v0.45 の訂正**: つきのちからで起こるので停止コード `UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK` を付けた） | サカキの許可のあるポケモン（今の番に場に出した・進化した）を、山札から重ねる効果（ワザ・特殊能力）で進化させられるか。説明の「(ポケモンを進化させる時には、あなたの手札から「進化カード」を出して…)」が、許可を手札から重ねる進化に限るのかが決められない | 山札から重ねる効果の処理（`EvolveFromDeck`・`EvolveAttackerFromDeck`・［うか］）。当たったらエンジンの不具合として止める | 許可のないふつうの進化（通常の制限で選べない） |
| RD9 | 既存（v0.36） | スターブーメランで、同じワザで HP 以上になるポケモンがいるときに手札にもどる（行き先が手札でも、空いたバトル場ときぜつの処理の順番の問いは同じ） | ワザの宣言の前 | 相手がきぜつしない |
| GS1 | 既存（v0.39） | てじなの「最大3枚」で 0 枚を選べるか | 段階 1 の答え（決定は待ったまま） | 1〜3 枚 |
| PW3 | 既存（v0.43） | ［ボスをよぶ］で山札にサカキがない（選ぶカードが 0 枚） | 使う機会で使うことを選んだとき（選べるが選ぶと止める） | 使わない・山札にサカキがある |
| v0.4a | 既存（`UNRESOLVED_EVOLUTION_HP`） | たきのぼりしんか・［うか］で重ねたあとの HP がダメージ以下 | 選べるが選ぶと止める（［うか］はどれもそうならコインの前） | HP がダメージより大きい |
| — | エンジンの未対応（`UNSUPPORTED_COPIED_ATTACK`） | 1 度だけ使えるワザを相手のワザとして使う | `unsupported_choices`（選べるが選ぶと拒否） | ほかのワザ |

- FC1 はラッキーたまごとてじなで共通の 1 つの問いです（カードごとの問い・コードにしない）。v0.23 の ER9・v0.9 の H4・v0.39 の GS1・v0.43 の PW3 の答えで決めないで
  ください。
- 実装上の判断（原典で確かめた規定ではない）: 手札・山札にもどすカードの位置（山札の一番下。どちらもあとで切るので結果は変わらない。v0.24 の PT7 と同じ）、
  ラッキーたまご・てじなで山札にもどしたカードを相手に見せない（説明に見せる指示がない。ログ `hand_to_deck` の `cards` は非公開の項目）、
  てじなで見せて手札に加える順番（山札の uid の小さい順）、ワザの効果で選ぶプレイヤー（ワザを使ったプレイヤー）。
- エンジンが止める `UNRESOLVED_…` は 53 件、未解決の裁定は 55 件（停止コード 53 + コードのない未解決 Z9・GV1）。FC1・TR1 は kyuura の未解決の一覧にない
  （`not_in_kyuura`）、GV1 は kyuura に論点がない（`codeless_questions`）。kyuura への報告事項です。

## 8. 規定と根拠（カードごと）

- じめんにもぐる・こばんなげ: 相手の場のポケモン（対戦ポケモン・控え）から 1 匹、弱点・抵抗力に関係なく 10・20（v0.43 と同じ要素）。こばんなげの「うら」は何もしない
  （決定もない）。控えのポケモンにダメージを与えるので、ワザを使ったプレイヤーが選びます。
- ねむりのたね: 10 のあと相手をねむり。おつかい: 「おもて」なら山札のトレーナーカードを 0〜1 枚（「加えてよい」）。見せて手札に加え、切る。トレーナーがなければ
  見せずに切る（p.309）。「うら」なら山札を見ない・切らない。
- スターブーメラン: 20 のあと「おもて」なら自分とついているすべてのカード（重なったカード・エネルギー・トレーナー）を手札にもどす（LD-PMCG5-027-ATK0）。返すダメージ
  （こうらがえし）で HP 以上になったヒトデマンはもどらない（CR-SHELL-ATTACK-STAR-BOOMERANG。コインも投げない）。
- たきのぼりしんか: 「コイキング」から進化するカードを山札から 0〜1 枚（「つけてよい」）。通常の進化の制限を免除しない。重ねたら（選ばなくても）山札を切る。
- どくどくえき: 「おもて」なら特殊などく（20。v0.34 と同じ `Poison(20)`）。受けるダメージの違うどく状態からは TP3（既存）。しんけいどく: 20 のあと 1 枚のコインで
  どくとマヒの両方（要素ごとに投げ直さない）。マヒの再付与は v0.3b の確認のまま。
- ひっさつばり・ネギでたたく・りゅうのきおく: 場に出てから 1 回（5 章）。コインの「うら」はダメージを与えられない（`Damage(local_gate)`。ワザの失敗ではない。
  v0.33 のつのでつつくと同じ）。
- あらしをよぶ: コイン 2 枚がすべて「おもて」なら、自分以外の場のポケモン全員（相手の対戦ポケモン・お互いの控え）に、弱点・抵抗力に関係なく 20。
  りゅうのたつまき: 40 のあと、相手がきぜつしなければ、ワザを使ったプレイヤーが相手の控えを 1 匹選んで入れ替える（v0.40 の `ForceSwitch(chooser="attacker")`）。
- てじな: 段階 1（手札から 0〜3 枚。0 枚は GS1）→ もどす → 段階 2（山札の基本エネルギーカードから、もどした枚数ちょうど）→ 見せて手札に加える → 切る。
  手札がなければ決定を出さずに切る。
- わるいいたずら: 「おもて」なら相手のトラッシュから 1 枚を選び、相手の山札の一番上にのせる（切らない）。相手のトラッシュが空なら処理の対象がないのでコインも
  投げない（v0.38 の `has_target`）。
- ラッキーたまご: 「おもて」なら 2 枚引く（足りなければ引けるだけ。p.312）、「うら」なら手札から 2 枚選んで山札にもどし、切る（手札が 2 枚より少なければ FC1）。
- おそいかかる・ラッキーパンチ: 既存の `CoinBonusDamage`。

## 9. 対戦

- 検証用デッキ `K44`・`V44`・`W44` と組（`PAIRINGS_V0_44`。`W44` 対 `P31` を含む）は tools/existing_effect_games.py の `--batch v0.44` です。公開の固定のデッキ・
  既存の変種には入れていません。勝敗で採用を判断しないでください。
- `--seeds 10`（4 組 × 席の入れかえ × 10 = 80 局）: 通常の勝敗 79・停止 1（対戦準備の既知の未解決 `UNRESOLVED_MULLIGAN_COMPENSATION`）。想定外の拒否・内部エラー・
  手数の上限 0、監査（やり直し・不変条件・ログの監査・書き出しの監査・トレーナーのログの並び）の失敗 0。14 枚のどのワザも使われた。
- 原典で決められないとして拒否したあと別の操作で続けた回数: FC1 139（ほとんどがラッキーたまごの手札 1 枚以下。P31 がまねるときを含む）・RD9 31（スターブーメラン）・
  既存の HC4 16・G37 3・`UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` 1。
- サカキを使った 37 回、許可で進化させた 37 回（その番に場に出したポケモン 36・その番に進化したポケモンの 2 回目 1）。［ボスをよぶ］の使う機会 46（使う 29・使わない 7・
  PW3 で使わない 10）、［うか］56 回（山札にスピアーがないとき 5）。正式な対戦の中で、［ボスをよぶ］で手札に加えたサカキ（同じ uid）を使い、その許可で進化させる流れ
  （V44 対 W44 の seed 0・1）を tests の `GameTest` が確かめます。

## 10. 互換性

- 公開の API（コマンド・`apply_command`・`new_game`）は変えていません。状態の型に場のポケモンの項目 2 つ（`attacks_used_once`・`evolution_permission_turn`）を加えました
  （既定は空・None）。
- 書き出しの形式 11 = 形式 10 + 場のポケモンの `attacks_used_once`（[[カードの uid, ワザの位置], ...]）・`evolution_permission_turn`。形式 1〜10 は、どちらかがあると
  `ValueError`（黙って落とさない）。どちらもない状態は形式 1〜10 で今までと同じに書き出します。監査の `LATEST_FORMAT` は 11。
- 加えたもの: 決定の種類 `hand_to_deck`・`discard_to_deck_top`。ログのイベント `once_attack_recorded`・`evolution_permission`・`hand_to_deck`・`put_discard_on_deck_top`・
  `reveal_from_deck_declined`・`evolve_from_deck_declined`。既存のイベントの項目（そのときだけ）: `evolve` の `power`・`source_zone`（［うか］）、`search_deck` の `power`
  （［ボスをよぶ］）、`evolve_from_deck_none` の `power`、`reveal_from_deck_none` の `category`・`count`。解決の基盤の問い `stated_cards_short`（FC1）・
  `evolution_permission_from_deck`（GV1。コードなし）。`zones.search_deck_to_hand` に引数 `power`、`evolution.place_evolution_card` に引数 `power`、
  `evolution.evolution_block` に引数 `from_deck`。
- 拒否のコード `ATTACK_ALREADY_USED`（1 度だけ使えるワザの 2 回目）。既存の拒否のコード・順番は変えていません（`EVOLVED_THIS_TURN`・`PLAYED_THIS_TURN` は
  `turn_restriction` に移したが、同じコード・同じ文）。
- 固定した v0.43（`96a0f1d`。`tools/engine_lockstep.py tree` で展開した木）と、最終のコードで、別の木・別のプロセスで比べました。比較の差を包括的に許す設定は
  していません。結果は 11.2 節。

## 11. 検証

### 11.1 テスト

- tests/test_search_evolution_once_attacks_v0_44.py（49 件）: 登録・写し・記録（`CardDataTest`）・相手のポケモンを選ぶダメージ・山札から見せる／山札の上にのせる・
  手札を山札にもどす（FC1・GS1・0 枚・手札なし）・スターブーメラン（RD9・控えなしで負け）・山札からの進化（制限・眠りなど・ガス・GV1）・1 度だけ使えるワザ
  （記録の時点・こんらん・ベンチ・進化・まねる・形式 11）・サカキ（許可・2 回目の進化・最初の番・TR1・ポケモン育て屋さん・形式 11）・［ボスをよぶ］（使う・使わない・PW3）・
  そのほかのワザ・先読みの方法の一致・きぜつとサイド・決定の途中の保存と再開・カードの保存則・不変条件の違反・正式な対戦（`GameTest`）。
- 既存のテストの期待値の更新（確かめる性質は弱めていない）: 形式の一覧（10 → 11。形式 11 が形式 10 に 2 つの項目を加えただけであることを確かめるテストを加えた）・
  登録と写しの数・研究の対応表の数・停止コードの一覧・自分のタイプを弱点に持つポケモン（ナツメのバリヤード）・G37 の宣言の型・バリアーで止まるコインの型
  （しんけいどく）・`reveal_deck_to_hand` を使う要素（3 つ）。
- ログの監査（tests/log_audit.py）: v0.44 のイベントの組み立て直し（手札・山札・トラッシュ）と、特殊能力の宣言・コインのあとの処理、許可と進化の番、1 度だけ使える
  ワザの記録、相手のワザとして使ったワザの効果のログ（`copy_attack` の `copied`）を確かめるようにしました。

### 11.2 比較・検査

固定した v0.43（`96a0f1d`。`python3 tools/engine_lockstep.py tree --commit 96a0f1d` で展開した木。版の表示は 0.43.0）と、最終のコード（0.44.0）で、別の木・別のプロセスで
比べました。比較の差を包括的に許す設定はしていません。

| 比較 | 範囲 | 結果 |
|---|---|---|
| `tools/engine_lockstep.py record --corpus all --seeds 10 --stress-seeds 2 --save-every 7` → `compare` | 290 局・48,092 歩（v0.43 までの自然な対戦・ストレス実行の組。保存と復元 5,068 回を含む。どちらも内部エラー 0） | 食い違い 0・許した差 0 |
| 前の版の検証用デッキの対戦（作業用の道具。各木の公開の API と、その木の tools/existing_effect_games.py だけを `python3 -I` で読み込み、受け付けた操作の列・最後の状態（形式 10）の指紋・ログ・乱数・観察の数・監査の結果を比べる） | `--batch` v0.28〜v0.43 の 59 組 × 席の入れかえ × seed 0〜4 = 590 局・78,598 歩 | 違い 0 |

- v0.44 のカードは前の版の検証用デッキにないので、形式 10 で書き出せます（`attacks_used_once`・`evolution_permission_turn` は空）。v0.44 のカードの対戦は 9 章と
  tests の `GameTest` で確かめました（前の版には比べる相手がない）。
- `python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura --check`: 写しは kyuura `ecb2d69` と一致。
- `python3 scripts/check_card_sources.py`: 記録 221 件が方針と合う。
- `python3 scripts/check_research_links.py --kyuura ../kyuura`: 研究の対応表は kyuura `3f34908` の記録と一致。
- `ruff check --select F,E9 .`: 問題なし。
- `python3 tools/run_mutants.py check`: 50 の変異の定義がどれも今のコードに入る。変異の定義は変えていないので、証人（`witness`）は走らせていません。
- 全体のテスト: 最終のコードで `python3 -m unittest` を走らせ、3,106 件 OK（skipped 1。約 9.5 分）でした（v0.43 の 3,057 件から、v0.44 のテスト 49 件が増えた）。

### 11.3 行っていないこと

- 大規模な seed 探索・変異試験の全体・複数の Python の版での実行は行っていません（依頼の範囲外）。変異の定義（tools/mutants.py）は変えていません。
- ガイドブックの読み直し・新しい原典の照合（pcg-search.com の同じ版のページを除く）は行っていません。

## 12. 未解決・限界・報告事項

- kyuura への報告事項: FC1・TR1（kyuura の未解決の一覧にない）・GV1（kyuura に論点がない）、_____のラッキーの名前の空欄の下線の数、
  LD-PMCG5-027-ATK0 を処理に使う文面にしたこと（研究の対応表の `registered`）。
- 1 度だけ使えるワザを相手のワザとして使うことはエンジンの未対応です（記録をどのポケモンに付けるかを決めて実装するまで）。
- GV1 は今の対応カードでは起こりません。サカキのポケモンを山札から重ねる効果で進化させるカードを加えるときは、GV1 を原典で確かめてから扱いを決めてください。
  （**v0.45 の訂正**: つきのちからで起こる。v0.45 で停止コード `UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK` を付けた）
- サカキの許可を状態に持つのはその番だけです。番を飛ばす・続ける効果を加えるときは、許可が消える時点を見直してください。
