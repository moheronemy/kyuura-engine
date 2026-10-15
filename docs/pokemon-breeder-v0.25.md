# ポケモン育て屋さん（v0.25）: 照合済みの記録の再利用と実装

v0.25 で、トレーナーのポケモン育て屋さん（PMCG1-094。ポケモンカード第1弾）を対応にしました。この 1 枚だけで、公開の固定のデッキ・ほかのカードの効果は変えていません。`CLAUDE.md` の「照合済みの記録の再利用」（[verified-record-reuse.md](verified-record-reuse.md)）の手順にしたがい、進化の規定（p.309・p.310・p.313・p.316・p.319・p.322〜p.324）・トレーナーの使いかた（p.310）は既存の記録を再利用し、読み直していません。既存の記録で足りなかったカードのページ（p.259 のポケモン育て屋さん）だけを原典で確かめました。

- 基準のルール: 「ポケットモンスターカードゲーム公式ルール 2000.02.14版」（『ポケモンカードオフィシャルブック2000』pp.306〜326 [P43]）
- カードの処理: 同じ本のカードのページの「最新の説明」（p.6「この本の使いかた」。[trainers-v0.2b.md](trainers-v0.2b.md) の前提と同じ）。印刷の文面・英語版（「You can only play this card when you would be allowed to evolve that Pokémon anyway」）・現代のルールでは補っていません
- カードデータ: kyuura `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`（写しの元。変えていない）。研究の基準: kyuura `3f349085645f47d0649a6cacece3680caeae50bf`（変えていない）
- 分類（CONFIRMED・SUPPORTED・UNRESOLVED・CONFLICT）の意味は [trainers-v0.2b.md](trainers-v0.2b.md) 1 章と同じ

## 1. 既存の記録を探した結果（手順の 1〜5）

| 探した記録 | 結果 | 使い方 |
|---|---|---|
| kyuura `data/cards.json`（`ecb2d69`・`3f34908` で同じ） | PMCG1-094 ポケモン育て屋さん。文面「ポケモンを進化させるときに使う。2進化カードをいきなりつけることができる。」（なぞのばしょの転記。第1弾の印刷）。`jp_en_differences` に 2002 年のサポーター適用カード | 登録の照合（`TrainerEntry.text_ja`）だけに使う。処理の根拠にはしない |
| kyuura `data/rule_history.json` の `MIX-SUPPORTER-ERRATA` | 2002 年の「サポーター適用カード」にポケモン育て屋さんが入る | **使わない**（2000.02.14 版のあとの規定。v0.19・v0.24 と同じ扱い） |
| kyuura `rule_history.json` の P43 の p.259 のページの記録・公式のエラッタ | このカードの記録はない | — |
| kyuura のサイドカー（LD-・CC-・CR-・UQ-） | このカードの記録はない。p.88 の第4弾のゼニガメの照合の記録（`CC-PMCG4-018-P43`。エンジンの記録の取り込み）の解説に、「ゼニガメ」から「ポケモン育て屋さん」で「わるいカメックス」に進化する例 | **再利用**（系統の例。BR6。もとはエンジンの v0.13 の記録で、エンジンとは別に原典を確かめた証拠としては数えない） |
| `kyuura_engine/data/card_verification.json` | このカードの記録はない。v0.24 の PMCG1-093（ポケモン交換おじさん）の記録に、このカードの解説のうちポケモン交換おじさんを使う 1 段落の文面がある | 1 段落は処理の順番の確かめ（交換おじさんで山札から 2 進化カードを持ってきて、育て屋さんで 2 進化させる）にだけ使った範囲で、**このカードの照合の記録としては扱わない**（見出し・図版・最新の説明・ほかの解説は照合していない） |
| docs/evolution-rules-v0.4a.md・docs/stage2-evolution-v0.4c.md・docs/stage2-state-v0.4c.md | 進化の規定（E1〜E20・R1・H1、S1〜S22）: 名前で重ねる・書かれていない組み合わせで重ねない（p.309・p.324）、その番に場に出したポケモン・おたがいの最初の番・その番に進化したポケモンは進化できない（p.310）、特殊状態・持続する効果は消え、ダメージ・エネルギー・つけて使うトレーナーは受け継ぐ（p.310・p.322・p.323）、進化ポケモンは 2 枚または 3 枚（p.319）、きぜつしたら重なったカードをすべてトラッシュ（p.313）、たねポケモンに 2 進化カードを直接重ねられない（S2）、HP がダメージ以下になる進化は UNRESOLVED（H1） | **再利用**（育て屋さんによる進化に当てはめた。3 章） |
| docs/trainers-v0.2b.md 2 章 | p.310 のトレーナーの使いかた（使うための条件・何枚でも・使いすて・トラッシュの時点） | **再利用** |
| docs/chemical-gas-v0.8.md | トレーナーはかがくへんかガスで止まらない（G8）。特殊能力がはたらいているかは問い合わせのたびに求める | **再利用**（進化したあとのフシギバナのエナジートランス） |

既存の記録で足りなかったもの（原典に戻る前に書いたこと）:

1. G1: 処理の根拠になる最新の説明（kyuura に LD- がなく、エンジンにも記録がない）。特に、使うための条件の有無、重ねる相手（たねポケモンか）、1 進化カードが要るか。
2. G2: 見出し・収録商品・図版の文面（写しとの照合）。
3. G3: 解説のうち処理に関わる記述（進化の制限（最初の番）との関係・1 進化カードの扱い・系統の例）。v0.24 で読んだ 1 段落のほかの段落。

ページは v0.24 で本の索引（p.354「シリーズ別カードさくいん」。第1弾のトレーナーカード「ポケモン育て屋さん …… 259」）から確かめた p.259 です。一般のルール（pp.306〜326）・同じページのメンテナンス・ポケモン交換おじさんは読み直していません。

## 2. 原典で確かめたこと（2026-10-15）

Internet Archive のスキャン [J38]（PDF 372 ページ、`PDF n = p.(n-2)`）の p.259（PDF 261）を、v0.24 で作った 400dpi の画像から切り出して目で読みました（いちばん下のポケモン育て屋さんの部分だけ）。

| 項目 | 内容 |
|---|---|
| 見出し・収録 | 「ポケモン育て屋さん」、収録「ポケモンカード第1弾」 |
| 図版の文面 | 「ポケモンを進化させるときに使う。2進化カードをいきなりつけることができる。」（kyuura の写しと同じ。第1弾の印刷） |
| 最新の説明 | 「このカードは、あなたが自分の場にいるポケモンを進化させるときにだけ、使える。そのポケモンの上に「2進化カード」を直接のせ、1進化をとばして「2進化ポケモン」に進化させる。」 |
| 解説（1 段落目） | 「「ポケモン育て屋さん」を使えば、対戦開始2回めの自分の番で「ゼニガメ」が「カメックス」に、「ヒトカゲ」が「リザードン」へと一気に進化することができます。2種類の2進化ポケモンを育てようとしている大型デッキを使う場合などは、1進化ポケモンカードをかなり減らして「ポケモン育て屋さん」を多めに入れると進化が完成しやすくなります。ただし、急いで2進化ポケモンにしても、ワザも使えない、逃げられないということになることもあるのでエネルギーの数には注意してください。」 |
| 解説（2 段落目。v0.24 で読んだ段落） | 「「ポケモン交換おじさん」と組み合わせて使うと、さらにすばやく2進化させることができます。場にたねポケモンが出ていて、手札にポケモンのカードがあれば、そのポケモンのカードを「ポケモン交換おじさん」で山札にもどし、2進化ポケモンカードを山札から持ってきて「ポケモン育て屋さん」で2進化ポケモンにします。とにかく2進化ポケモンにはやく進化したいというデッキにおすすめの方法です。」 |

最新の説明と図版の違い（`card_verification.json` の `mismatches`）: 図版は「進化させるときに使う」「2進化カードをいきなりつけることができる」で、最新の説明は「進化させるときにだけ、使える」（使うための条件）、「そのポケモンの上に「2進化カード」を直接のせ、1進化をとばして「2進化ポケモン」に進化させる」（重ねる相手・1 進化を飛ばすこと）と書きます。処理は最新の説明にしたがいます（BR1）。

## 3. 規定（BR1〜BR22）

「再利用」は既存の記録で決まり、今回読み直していないもの。「p.259」は今回読んだもの。テストはどれも tests/test_pokemon_breeder_v0_25.py。

| id | 事項 | 分類 | 根拠 | 実装 | テスト |
|---|---|---|---|---|---|
| BR1 | 処理は最新の説明にしたがう（印刷の文面・図版と違う） | CONFLICT（書き方） | p.259 の最新の説明・図版。p.6 | `TrainerEntry.play_text_ja` に最新の説明、`text_ja` に写しの文面 | `RegistrationTest.test_entry_follows_the_verified_latest_description` |
| BR2 | 使えるのは、自分の場のポケモンを進化させるときだけ。進化させられる組（BR3〜BR10）がなければ使えない | CONFIRMED | p.259「このカードは、あなたが自分の場にいるポケモンを進化させるときにだけ、使える。」。再利用: p.310（使うための条件はカードに書かれたもの。手札から出す前に確かめる） | `check_playable` が `IllegalActionError("NO_EVOLUTION_TARGET")`（手札から出す前。カードは手札に残る） | `UsableTest.test_no_pair_cannot_use_it`・`test_other_lineages_are_not_pairs` |
| BR3 | 進化させるのは自分の場（バトル場・ベンチ）のポケモン | CONFIRMED | p.259「自分の場にいるポケモン」。再利用: p.309・p.313（場はバトル場とベンチ。S8） | 自分の場のポケモン（場の並び） | `UsableTest.test_usable_on_the_active_and_on_the_bench`・`EvolutionResultTest.test_bench_target` |
| BR4 | 進化させるのはたねポケモン（重なりのない、たねポケモンのカード）。1 進化ポケモン・2 進化ポケモンは対象にならない | SUPPORTED | p.259「1進化をとばして「2進化ポケモン」に進化させる」（とばす 1 進化はたねポケモンからの 1 回目の進化）・解説の例（ゼニガメ・ヒトカゲ）と 2 段落目「場にたねポケモンが出ていて」。再利用: p.316（1 進化はたねポケモンから 1 回目、2 進化は 2 回目） | `skip_evolution_pairs` がたねポケモンだけを見る | `test_no_pair_cannot_use_it`（1 進化ポケモンに 2 進化） |
| BR5 | 重ねるのは手札の 2 進化カード。1 進化カード・ほかのカードは重ねられない | 2 進化カード: CONFIRMED。手札から: SUPPORTED | p.259「そのポケモンの上に「2進化カード」を直接のせ」。手札からは、最新の説明が場所を書かず、再利用: p.309「手札に…進化カードがあり」・p.310 の手順 1「手札から出して」、p.259 の 2 段落目「2進化ポケモンカードを山札から持ってきて「ポケモン育て屋さん」で」（山札から手札に持ってきてから使う） | 選べるもの = 手札の 2 進化カード（手札の並び） | `DecisionTest.test_card_decision_shape_and_invalid_cards`・`test_no_pair_cannot_use_it`（1 進化カードだけ） |
| BR6 | 系統: 2 進化カードの「○○○○から進化」の名前の 1 進化カードが「△△から進化」とする名前が、そのたねポケモンの名前と同じ（名前の完全一致） | SUPPORTED | p.259「1進化をとばして」（とばす 1 進化は、そのたねポケモンから進化し、2 進化カードがその 1 進化から進化するもの）。再利用: p.309・p.324（進化は名前で決まり、書かれていない組み合わせで重ねない。E1・E19・S1・S2）。例: p.259 の解説（ゼニガメ → カメックス、ヒトカゲ → リザードン）、p.88 の第4弾のゼニガメの解説（ゼニガメ → わるいカメックス。CC-PMCG4-018-P43） | 4 章 | `LineageTest`・`UsableTest.test_other_lineages_are_not_pairs` |
| BR7 | 2 進化カードの「○○○○から進化」の 1 進化カードのデータが写しにない・同じ名前の 1 進化カードで進化元が食い違うときは、系統を確かめられないので進化させない | 実装上の判断（データの範囲。ルールの裁定ではない） | — | その組だけなら `UnsupportedError("UNSUPPORTED_EVOLUTION_LINEAGE")`。ほかに組があれば選べるものに入れない | `UsableTest.test_unknown_lineage_is_unsupported`・`LineageTest.test_missing_or_conflicting_stage1_data_is_not_guessed` |
| BR8 | 1 進化カードを手札・山札などに用意する必要はなく、使わない（作らない・動かさない） | CONFIRMED | p.259 の最新の説明に 1 進化カードの指示がない（「直接のせ」）。解説「1進化ポケモンカードをかなり減らして「ポケモン育て屋さん」を多めに入れると進化が完成しやすくなります」 | 2 進化カードだけを重ねる | `EvolutionResultTest.test_stack_is_basic_and_stage2_and_everything_else_is_inherited`（手札のフシギソウは手札のまま。カードの種類と数が変わらない） |
| BR9 | 育て屋さんによるものも「進化」で、p.310 の進化の制限が当てはまる: おたがいの最初の番には使えない・その番に場に出したたねポケモンは進化させられない | SUPPORTED | p.259「進化させるときにだけ」「進化させる」・解説「対戦開始2回めの自分の番で…一気に進化することができます」。再利用: p.310（E4・E5） | `check_playable` の `FIRST_TURN_EVOLUTION`（おたがいの最初の番）・`current_form_turn`（その番に場に出したたねポケモンを除く） | `UsableTest.test_first_turn_of_each_player`・`test_no_pair_cannot_use_it`・`test_played_this_turn_by_command` |
| BR10 | その番に進化したポケモンは対象にならない（たねポケモンではない） | SUPPORTED（BR4 から。再利用: p.310 の E7） | 同上 | 重なりのあるポケモンを除く | `test_no_pair_cannot_use_it`（1 進化ポケモン） |
| BR11 | 特殊状態のたねポケモンも進化させられ、進化したら特殊状態・持続する効果・こんらんで「にげる」に失敗した記録は消える | SUPPORTED（進化の規定の当てはめ） | 再利用: p.322（E14）・p.323（E15）・R1 | 通常の進化と同じ `evolution.place_evolution_card` | `EvolutionResultTest.test_special_conditions_and_retreat_failure_are_cleared`・`test_persistent_effects_are_removed` |
| BR12 | 受け継ぐもの: ダメージカウンター・エネルギー・つけて使うトレーナー（効果と有効期限）。場に出た番・場のポケモンの番号は変えない | SUPPORTED（p.310 の E8・E9・E8' の当てはめ）・実装上の仮定（場のポケモンの番号） | 再利用: p.310 | `place_evolution_card`（`PokemonInPlay` ごと変えない） | `test_stack_is_basic_and_stage2_and_everything_else_is_inherited` |
| BR13 | 重なりはたねポケモン + 2 進化カードの 2 枚 | CONFIRMED | p.259「直接のせ」。再利用: p.319「1枚のたねポケモンカードと、1または2枚の進化カードの合計2枚または3枚」 | `evolution_stack` は `(たねポケモン,)`、いちばん上が 2 進化カード | `test_stack_is_basic_and_stage2_and_everything_else_is_inherited`・`InvariantTest` |
| BR14 | いちばん上の 2 進化カードの内容がそのポケモンを表す（HP・タイプ・弱点・抵抗力・にげる・ワザ・特殊能力） | SUPPORTED（p.310 の E3'・E6 の当てはめ） | 再利用: p.310 | 既存（どの処理もいちばん上のカード）。特殊能力がはたらいているかは問い合わせのたびに求める（v0.8） | `AfterEvolutionTest.test_energy_trans_and_solar_beam`・`test_new_power_follows_chemical_gas` |
| BR15 | きぜつしたら、重なった 2 枚とついているカードをトラッシュする。サイドは 1 枚 | SUPPORTED（p.313 の E17・E17' の当てはめ） | 再利用: p.313・p.323 | 既存の `knock_out`（`PokemonInPlay.cards()`） | `AfterEvolutionTest.test_knock_out_trashes_both_cards`・自然な対戦（6 章） |
| BR16 | 選ぶのは使ったプレイヤー。順番は、進化させるポケモン → 重ねる 2 進化カード | 選ぶ人: CONFIRMED。順番: 実装上の判断（結果は変わらない） | p.259「あなたが自分の場にいるポケモンを進化させる」。順番は再利用: p.310 の進化の手順 1（ポケモンを示してから、進化させるカードを見せる） | 決定 `SELECT_POKEMON` → `SELECT_EVOLUTION_CARD`（どちらも `player` は使ったプレイヤー） | `DecisionTest` |
| BR17 | 進化したあとの HP が、のっているダメージ以下になる組 | **UNRESOLVED**（v0.4a の H1。変えていない。同じ問い・同じコード） | 再利用: p.310・p.323 | その組だけなら使う前に `UnsupportedError("UNRESOLVED_EVOLUTION_HP")`。ほかに組があれば選べるが、選ぶと同じコード（`unresolved_choices`。決定は待ったまま） | `UsableTest.test_hp_at_or_below_the_damage_is_unresolved`（写しのカードでは起こらないので、テスト専用の写し） |
| BR18 | 使い終わったらこのカードをトラッシュする（進化のあと）。番は続く。同じ番に何枚でも使える | CONFIRMED（使いすて・何枚でも）・SUPPORTED（時点） | 再利用: p.310（trainers-v0.2b.md 2 章） | 既存の `engine._finish_trainer` | `test_stack_is_basic_and_stage2_and_everything_else_is_inherited`・`AfterEvolutionTest.test_second_breeder_in_the_same_turn` |
| BR19 | 育て屋さんで進化させたポケモンは、その番にもう一度は進化させられない | SUPPORTED（p.310 の E7 の当てはめ。2 進化の上の段階もない） | 再利用: p.310 | 既存（`evolved_turn`・名前の確認） | `AfterEvolutionTest.test_normal_evolution_still_cannot_skip_and_no_second_evolution` |
| BR20 | 通常の進化（`EvolvePokemon`）では、たねポケモンに 2 進化カードを直接重ねられない | CONFIRMED（v0.4c の S2。変えていない） | 再利用: p.309・p.324 | 既存の `EVOLUTION_NAME_MISMATCH` | `test_normal_evolution_still_cannot_skip_and_no_second_evolution` |
| BR21 | 対象・カードが 1 つでも決定を出す | 実装上の判断（パソコン通信・突風などと同じ） | — | 決定 `SELECT_POKEMON`・`SELECT_EVOLUTION_CARD`（1〜1） | `test_usable_on_the_active_and_on_the_bench` |
| BR22 | 段階 2 の答えが不正でも、段階 1 は取り消さない（段階 1 は選ぶだけで状態を変えない）。決定を待ったまま、カードは使用中 | 実装上の判断 | — | 決定の確認（`check_choices`）が状態を変える前に拒否する | `DecisionTest.test_card_decision_shape_and_invalid_cards` |

通常の進化の制限は免除していません（BR9・BR10・BR19・BR17）。反対に、通常の進化の名前・段階の確認（`EVOLUTION_NAME_MISMATCH`・`EVOLUTION_STAGE_MISMATCH`）は「1 進化を飛ばす」こと自体を拒否するので、育て屋さんの効果には当てはめず、4 章の系統の確認に置きかえています（それ以外の確認は通常の進化と同じ）。

## 4. 進化系統の照合方法

2 進化カードのデータにあるのは「○○○○から進化」（1 進化の名前）だけで、たねポケモンの名前はありません。そこで、同じ写しの 1 進化カードのデータを使います。

1. 写しの読み込み（`cards.pool_from_extract`）で、2 進化カードの定義に `stage1_evolves_from` を加える: 写しの 1 進化カード（段階が stage1 のポケモンのカード。対戦に使えるかは問わない）のうち、名前（日本語の名前の完全一致）が 2 進化カードの「○○○○から進化」と同じものの「△△から進化」の名前（重複を除き並べたもの）。
2. 育て屋さんの効果（`evolution.skipped_stage1_basic`）は、それが 1 つに決まればその名前を、たねポケモンの名前（完全一致）と比べる。0 個（写しに 1 進化カードがない）・2 個以上（同じ名前の 1 進化カードで進化元が食い違う）なら確かめられない（BR7）。
3. 名前の一部（「カイリキー」「ワンリキー」）・形容詞（「サカキの」「わるい」）・種族では比べない。名前が同じ別のカード（第1弾と第4弾のゼニガメなど）は、名前が同じなので同じ系統として扱う（p.309・p.324 の規定は名前で決まる。p.88 の解説の例）。

| 2 進化カード | 「○○○○から進化」 | 写しの 1 進化カードの進化元 | 重ねられるたねポケモン |
|---|---|---|---|
| フシギバナ（PMCG1-011） | フシギソウ | フシギダネ | フシギダネ |
| カメックス（PMCG1-032） | カメール | ゼニガメ | ゼニガメ（第1弾・第4弾のどちらも） |
| フーディン（PMCG1-049） | ユンゲラー | ケーシィ | ケーシィ |
| カイリキー（PMCG1-057） | ゴーリキー | ワンリキー | ワンリキー（サカキのワンリキーは不可） |
| サカキのカイリキー（PMCG6-061） | サカキのゴーリキー | サカキのワンリキー | サカキのワンリキー（ワンリキーは不可） |
| スピアー（PMCG1-012） | コクーン | ビードル | ビードル |
| バタフリー（PMCG2-007） | トランセル | キャタピー | キャタピー |
| リザードン（PMCG1-021。参照カード） | リザード | （写しにない） | 確かめられない（カードも未対応） |

対戦に使える 2 進化カード 7 種類は、どれも 1 進化カードが写しにあります。必要なデータが足りない組み合わせ（リザードンなど）を推測で対応にはしていません。ほかのカード効果は新しく実装していません。

## 5. 実装

- `effects.EvolveBasicToStage2`（`implementation_id` `evolve_basic_to_stage2`。`skips_stage1_evolution = True`）を `TrainerEntry` で PMCG1-094 に登録しました（`DEFAULT_EFFECTS` の id は `kyuura-engine-0.13` のまま）。
  - `check_playable`: おたがいの最初の番は `FIRST_TURN_EVOLUTION`。進化させられる組（`effects.skip_evolution_pairs`）があれば使える。なければ、原典で決められない組（HP）だけなら `UNRESOLVED_EVOLUTION_HP`、エンジンが確かめられない組（未対応の 2 進化カード・系統を確かめられない 2 進化カード）だけなら `UNSUPPORTED_EVOLUTION`・`UNSUPPORTED_EVOLUTION_LINEAGE`、ほかは `NO_EVOLUTION_TARGET`。どれも手札から出す前。
  - `resolve`: 段階 1 の決定 `SELECT_POKEMON`（選べるものは進化させられる自分の場のたねポケモン。場の並び。HP の組だけのポケモンは `unresolved_choices`）。
  - `resume`: 段階 1 の答えなら段階 2 の決定 `SELECT_EVOLUTION_CARD`（選べるものはそのポケモンに重ねられる手札の 2 進化カード。手札の並び。`context` の `"target"`）。段階 2 の答えなら `evolution.place_evolution_card(..., trainer=このカード)` で進化させる。
  - `decision_problems`: 決定するのは使ったプレイヤー・種類・選ぶ数・選べるもの（そのときの場と手札から求め直す）・`unresolved_choices`・段階 2 の `"target"`。不変条件が決定を待つたびに確かめる。
- `kyuura_engine/evolution.py`（新規）: `place_evolution_card`（v0.24 までの `engine._evolve_pokemon` の、確認のあとの状態を変える手順 1〜5 をそのまま関数にした。通常の進化と育て屋さんで共通）と `skipped_stage1_basic`（4 章）。`engine.py` を読み込まない（`effects.py` からも使う）。
- `engine._evolve_pokemon` は確認（順番・コード）を変えず、手順を `place_evolution_card` に委ねる（動き・ログは同じ。固定した v0.24 との比較で食い違い 0。[v0.25-verification.md](v0.25-verification.md) 3 章）。
- `cards.CardDefinition.stage1_evolves_from`（新しい項目。2 進化カードだけ。既定 `()`）と `cards._with_stage1_lineage`（写しの読み込みで求める）。
- `effects.TrainerEffect.skips_stage1_evolution`（新しい印。既定 False）。不変条件が、たねポケモン + 2 進化の重なりの進化のログのトレーナーを、カード id ではなくこの印で確かめる。
- 決定の種類 `decisions.SELECT_EVOLUTION_CARD = "select_evolution_card"` を加えました（段階は `Phase.DECISION`、再開先は `"trainer"`）。段階 1 は既存の `SELECT_POKEMON`。別の決定の列・汎用の効果の書き方は作っていません。
- `engine.py`・`resolution/` にカード id・実装の名前での分岐はありません（`RegistrationTest.test_no_card_specific_branch_in_the_engine`）。

### ログ

| イベント | 項目 | 見せてよい相手 | 意味 |
|---|---|---|---|
| `evolve`（v0.4a から） | `player`・`pokemon_id`・`from_card`・`from_card_id`・`to_card`・`to_card_id` | 全員 | 進化した（p.310 の手順 1 で相手に見せる） |
| `evolve` の `trainer_card`（v0.25 で加えた項目） | 使っているトレーナーのカードの uid | 全員 | 1 進化を飛ばして重ねた進化だけにある（通常の進化のログには書かない。v0.24 と同じ形） |

新しいイベントの種類はありません。進化で消える特殊状態・持続する効果・にげるの失敗の記録のログ（`special_conditions_removed`・`persistent_effect_removed`・`retreat_failure_cleared`。`reason` は `evolve`）は通常の進化と同じです。ログの監査（tests/log_audit.py）は、通常の進化（`trainer_card` なし）の名前と、`trainer_card` のある進化（使っている最中の、1 進化を飛ばして進化させるトレーナーの効果で、たねポケモンに系統の合う 2 進化カードを重ねた）を確かめます。

### 拒否のコード

- `NO_EVOLUTION_TARGET`（新規。`IllegalActionError`）: 進化させられる組がない（BR2）。
- `UNSUPPORTED_EVOLUTION_LINEAGE`（新規。`UnsupportedError`）: 系統を写しで確かめられない組だけ（BR7。原典の問いではないので `UNRESOLVED_…` ではない）。
- 既存のコード: `FIRST_TURN_EVOLUTION`（BR9）・`UNRESOLVED_EVOLUTION_HP`（BR17）・`UNSUPPORTED_EVOLUTION`（未対応の 2 進化カード。デッキには入らない）、決定の答えの `INVALID_CHOICE`・`INVALID_CHOICE_COUNT`・`DUPLICATE_CHOICE`・`NOT_YOUR_DECISION`・`WRONG_DECISION`・`WRONG_PHASE`。

### 公開の API・書き出し

- 公開の API（`kyuura_engine` の公開の名前・コマンド・`apply_command` の呼び方）は変えていません。`EvolvePokemon` の確認も同じです。
- 書き出しは形式 9 のまま（状態の項目を加えていない。重なりは既存の `evolution_stack`。形式 7 から書き出せる）。`CardDefinition.stage1_evolves_from` はカードの定義（写しから求める）で、状態にも書き出しにも入りません。

## 6. 進化の重なりの扱い（不変条件・書き出し・監査・きぜつ）

v0.4c の前提（[architecture-v0.4c.md](architecture-v0.4c.md) 14 章・[stage2-state-v0.4c.md](stage2-state-v0.4c.md) 5 章: いちばん下がたねポケモン・`EVOLUTION_STAGES` の順・重なりの上の側とログ `evolve` の対応）を見直し、次のようにしました。

| 前提 | v0.24 まで | v0.25 |
|---|---|---|
| いちばん下 | たねポケモン | 同じ |
| 段階の順 | 重なりの位置で決まる（下から たね → 1 進化 → 2 進化） | 下から段階が増えていく（`EVOLUTION_STAGES` の順）。隣り合う 2 枚は、1 段階の差なら「○○○○から進化」が下の名前（今までと同じ）、たねポケモンと 2 進化（2 段階の差）なら 4 章の系統が合い、**その移り変わりの進化のログに `trainer_card`（1 進化を飛ばして進化させるトレーナー）がある**こと。ほかは違反 |
| 枚数 | 3 枚まで | 同じ（たね + 2 進化は 2 枚） |
| 1 進化した番の必要条件 | 2 進化ポケモンなら、1 進化できる持ち主の番があること | 3 枚の重なりだけに当てはめる（たね + 2 進化には 1 進化した番がない） |
| ログとの対応 | 移り変わりごとに `evolve` が 1 つ（`new_game` からの対戦ではすべて） | 同じ。加えて、`trainer_card` は 1 進化を飛ばした移り変わりだけにあり、持ち主のカードで、登録した実装が `skips_stage1_evolution` |

- テストの盤面（`build_test_state` の `"evolved_from"`）でたね + 2 進化の重なりを作ると、ログがないので不変条件の違反です（`InvariantTest.test_hand_built_skip_stack_without_the_log_is_rejected`。v0.4c の「たねに 2 進化」の違反のテストもそのまま通る）。育て屋さんで進化させた盤面は、テストでも実際に育て屋さんを使って作ります。不変条件を弱めていません。
- 通常の進化（`EvolvePokemon`）は、名前・段階の確認で 1 進化を飛ばせません（BR20）。仮に飛ばしても、ログに `trainer_card` がないので不変条件が見つけます。
- 書き出し: 形式 9 のまま（重なりは既存の項目）。書き出しの監査（`serialization_problems`）が通ります。
- きぜつ・場をはなれるとき: 既存の `knock_out` が `PokemonInPlay.cards()`（重なったカードすべて）とついているカードをトラッシュします（2 枚でも 3 枚でも同じ）。自然な対戦で、育て屋さんで進化したフシギバナが 14 回きぜつし、どれも 2 枚がトラッシュにありました（[v0.25-verification.md](v0.25-verification.md) 4 章）。

## 7. 未解決と変えていないもの

- 新しい未解決はありません。HP がダメージ以下になる組（BR17）は v0.4a の H1 と同じ問いなので、同じコード（`UNRESOLVED_EVOLUTION_HP`）を使い、新しい裁定・コードにしていません。エンジンが止める `UNRESOLVED_…` は 22 件、未解決の裁定は 28 件のままです。
- 既存のカードの裁定・確度の分類、固定した参照データ（tests/fixtures/）、研究の基準・写しの元のコミット、v0.20 の固定のデッキ、既存の対戦の変種（`preset`・`gust`・`computer`・`mixed`・`retrieval`・`trader`）は変えていません（変種の結果が v0.24 と同じことを確かめた）。

## 8. 組み合わせの対戦（tools/preset_deck_games.py）

| 変種 | 置き換え | 使い方 |
|---|---|---|
| `--variant breeder` | デッキ A（エビワラー・ジュゴン）は v0.24 の `trader` のまま（2 進化ポケモンがいないので育て屋さんを入れない）。デッキ B（フシギバナ・パラセクト）は `trader` のマサキ 2 枚をポケモン育て屋さん 2 枚に置き換える（`DECK_SUBSTITUTIONS`）。どちらも 60 枚 | `python3 tools/preset_deck_games.py --games 20 --variant breeder`（席を入れかえて 20 局ずつ。合計 40 局） |

手順に加えたもの（決まった手順で、強い AI ではない。勝率でカードの強さを判断しない）:

- ポケモン育て屋さん: その番のほかの操作が終わったとき（突風・エネルギー回収の手順のあと、ポケモン交換おじさん・パソコン通信・オーキドはかせの手順の前）、1 番に 1 回だけ考え、進化させられる組があれば使う。進化させるのはバトル場のポケモン → ついているエネルギーが多いもの → 場の並び、重ねるのは選べるもののうち手札の並びの先。おたがいの最初の番は使わない。
- そのあとの操作（元の手順）で、フシギバナのエナジートランス・ワザを使う。
- `mixed`・`retrieval`・`trader` と同じく、決定ごとの持ち主・使用中のカード（`check_…`）と、トレーナーを使ってからトラッシュするまでのログ（`trainer_sequence_problems`。育て屋さんでは `evolve` と、進化で消えるもののログだけ）を確かめ、使った回数・進化させたポケモン・進化したあとの特殊能力・ワザを数える（`breeder_uses`）。

結果の数は [v0.25-verification.md](v0.25-verification.md) です。

## 9. kyuura への報告事項（kyuura にはコミット・プッシュしない）

1. ポケモン育て屋さん（PMCG1-094）の照合の記録（CC-）・最新の説明（LD-）・P43 の p.259 のページの記録がない（`research_links.json` の `card_checks.engine_verified_without_kyuura_record` に挙げた）。p.259 の図版は第1弾の印刷（kyuura の写し）と同じ文面で、最新の説明は使うための条件（「進化させるときにだけ、使える」）と重ねる相手（「そのポケモンの上に…直接のせ、1進化をとばして」）を書く（写しの誤りではない）。
2. p.259 の解説の「対戦開始2回めの自分の番で」（最初の番の進化の制限が当てはまること）・「1進化ポケモンカードをかなり減らして」（1 進化カードが要らないこと）の記録がない。
3. kyuura の `rule_history.json` に、1 進化を飛ばす進化（たねポケモン + 2 進化の 2 枚の進化ポケモン）と、系統（2 進化カードの進化元の 1 進化の進化元）の決め方の記録がない。p.88 の解説の例（第4弾のゼニガメ → わるいカメックス）は CC-PMCG4-018-P43 にある。
4. kyuura の論点（UQ-）にする新しい未解決はない（HP の問いは既存の H1）。

## 10. 次にカードを加えるときの注意

- 退化（1 進化を飛ばした進化ポケモンを退化させたら、たねポケモンにもどるか、1 進化ポケモンになるか）・ベイビィ・ほかの 1 進化を飛ばす効果を加えるときは、6 章の重なりの前提（隣り合う 2 枚の確かめ方・`trainer_card`・`skips_stage1_evolution`）と、`evolution.skipped_stage1_basic` の系統の決め方を見直し、原典と照合してください。
- 写しに入れる 2 進化カードは、「○○○○から進化」の 1 進化カードも写しにあることを確かめてください（ないと育て屋さんで系統を確かめられない。BR7）。1 進化カードを対戦に使わないなら参照カードとして入れられます。
- 進化の手順（`place_evolution_card`）を変えると、通常の進化と育て屋さんの両方が変わります。固定した前の版と別のプロセスで比べてください（`tools/engine_lockstep.py`）。
