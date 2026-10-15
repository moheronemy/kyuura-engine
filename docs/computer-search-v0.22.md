# パソコン通信（v0.22）: 照合済みの記録の再利用と実装

v0.22 で、トレーナーのパソコン通信（PMCG1-090。ポケモンカード第1弾）を対応にしました。`CLAUDE.md` の「照合済みの記録の再利用」（[verified-record-reuse.md](verified-record-reuse.md)）の手順を当てはめ、トレーナーの使いかたなど既存の記録で決まるものは読み直していません。記録のなかったこのカードのページ（p.260）と、既存の記録で範囲の足りなかった p.310 の例・p.312 の山札の項だけを原典で確かめました。

- 基準のルール: 「ポケットモンスターカードゲーム公式ルール 2000.02.14版」（『ポケモンカードオフィシャルブック2000』pp.306〜326 [P43]）
- カードの処理: 同じ本のカードのページの「最新の説明」（p.6「この本の使いかた」。[trainers-v0.2b.md](trainers-v0.2b.md) の前提と同じ）
- カードデータ: kyuura `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`（写しの元。変えていない）。研究の基準: kyuura `3f349085645f47d0649a6cacece3680caeae50bf`（変えていない）
- 分類（CONFIRMED・SUPPORTED・UNRESOLVED・CONFLICT）の意味は [trainers-v0.2b.md](trainers-v0.2b.md) 1 章と同じ

## 1. 既存の記録を探した結果（手順の 1〜5）

| 探した記録 | 結果 | 使い方 |
|---|---|---|
| kyuura `data/cards.json`（`ecb2d69`・`3f34908` で同じ） | PMCG1-090 パソコン通信。文面「手札から2枚カードをすてることによって、山札から好きなカードを1枚選んで手札にすることができる。そのあとで山札をよくきってもとに戻す。」（なぞのばしょの転記。第1弾の印刷）。種類（`kinds`）なし | 登録の照合（`TrainerEntry.text_ja`）だけに使う。処理の根拠にはしない |
| kyuura のサイドカー（LD-・CC-・CR-・UQ-） | このカードの記録はない。山札が 0 枚のときの論点もない | — |
| kyuura `data/rule_history.json`・`rule_differences.json` | このカードの記録は大会のカードの使用制限（1999〜2000 年）だけ。p.260 のページの記録・p.312 の「山札の内容を見て」「山札を切ったり」の記録はない | 使用制限は対戦のルールに関わらないので使わない |
| `kyuura_engine/data/card_verification.json` | このカードの記録はない | — |
| docs/trainers-v0.2b.md 2 章（トレーナー共通） | p.310 のトレーナーの使いかた（手順 1 手札から出して相手に見えるようにする → 2 名前を伝える → 3 使うための条件にしたがう → 4 残りの説明。使うための条件を満たせなければ使えない「例は「パソコン通信」」・何枚でも・使いすて・トラッシュの時点・使っている最中はほかのことをしない）。2026-10-12 に画像で照合した記録 | **再利用**。ただし p.310 の例の文面は記録されていない（不足 G5） |
| docs/trainers-v0.2b.md 3 章・docs/rules-2000-02-14.md | p.312「カードを引く」は山札の一番上を手札に加える・引いたカードは見せなくてよい・効果で引くときは引けるだけ引く・負けは番の最初に引けないときだけ（p.309・p.312） | **再利用**（「カードを引く」との違いを決めるため） |
| docs/professor-oak-v0.19.md・`zones.discard_hand` | 手札をすべてトラッシュする処理（ログ `discard_hand`）。トラッシュに順番はない（p.312） | 「手札の一部を選んでトラッシュ」との違いを確かめた（4 章）。トラッシュに順番がないことは**再利用** |
| docs/architecture-v0.2b.md 9 章 | 非公開の情報は、イベントの種類ごとの決まった項目にだけ入れる（`draw` の `cards` など） | **再利用**（実装上の方針） |
| docs/rules-2000-02-14.md の「実装上の仮定」 | 「デッキを切る」は seed から作った乱数での並べ替え 1 回で表す（v0.1） | **再利用**（山札を切る処理） |
| docs/preset-decks-v0.20.md 6 章 | 次の作業の候補。「p.310 が「使うための条件」の例に挙げているカード」 | — |

既存の記録で足りなかったもの（原典に戻る前に書いたこと）:

1. G1: このカードの「最新の説明」の文面（トラッシュするのは何枚で、使うための条件か。山札から選ぶのはどの種類のカードで、何枚か。選ぶことを省略できるか。相手に見せるか。山札を切るか。順番）。
2. G2: 図版の文面が kyuura の写しと同じか（写しの照合）。
3. G3: 解説に、処理に関わる記述（手札の枚数・山札が 0 枚のとき）があるか。
4. G4: 見出し・収録商品。
5. G5: p.310 の「使うための条件」の例（パソコン通信）の文面。v0.2b の記録は「例は「パソコン通信」」とだけ書き、文面を記録していない。
6. G6: p.312 の「山札」の項のうち、山札の中を見ること・山札を切ることの規定。v0.2b の記録は「カードを引く」ことの規定だけを記録している。

ページは推測せず、本の索引（p.354「シリーズ別カードさくいん」。第1弾のトレーナーカード「パソコン通信 …… 260」）で探しました。同じ索引の突風 255・ポケモンいれかえ 254・マサキ 254 は、既存の照合の記録のページと同じです。一般のルールの通読・ほかのカードのページの読み直しはしていません。

## 2. 原典で確かめたこと（2026-10-15）

Internet Archive のスキャン [J38]（PDF 372 ページ、`PDF n = p.(n-2)`）を画像にし（ページ全体は 110dpi で位置を確かめ、読む部分は 400dpi で切り出した）、目で読みました。OCR の文字はページと索引の位置を探すのに使っただけです。

### p.260（PDF 262）のパソコン通信（いちばん上。同じページのダウジングマシーン・ポケモン回収は照合していない）

| 項目 | 内容 |
|---|---|
| 見出し・収録 | 「パソコン通信」、収録「ポケモンカード第1弾」だけ |
| 図版の文面 | 「手札から2枚カードをすてることによって、山札から好きなカードを1枚選んで手札にすることができる。そのあとで山札をよくきってもとに戻す。」（kyuura の写しと同じ） |
| 最新の説明 | 「手札からカードを2枚選んでトラッシュしなければ、このカードは使えない。あなたの山札からカードを1枚選び出し、手札に加える。その後、その山札をよく切る。」 |
| 解説（処理に関わる記述） | 「「パソコン通信」は、何でも好きなカードを1枚、自分の山札から持ってくることができるからです。そのかわりに手札からカードを2枚トラッシュしなければいけませんが、これはなかなか選ぶのがたいへんです。」「必要なカードをとにかく山札から持ってきて、対戦の準備をととのえます。」「しかし使いどころがなかったら、使わないという判断も大切です。」。手札の枚数・山札が 0 枚のときの記述はない |
| 参考（照合していない隣のカード） | 同じページのダウジングマシーンの最新の説明は「…トラッシュから「トレーナーカード」を1枚選び出し、相手プレイヤーに見せてから、手札に加える。」で、見せる指示がある（パソコン通信にはない）。この比較のために読んだだけで、ダウジングマシーンの照合の記録は作っていない |

### p.310（PDF 312）の「トレーナーカードを使う」の例（G5）

> たとえば「パソコン通信」には、手札からカードを2枚トラッシュしなければならないという条件が記述されています。2枚トラッシュできないときには、「パソコン通信」を使うことはできません。
> 「パソコン通信」の説明：手札からカードを2枚選んでトラッシュしなければ、このカードは使えない。あなたの山札からカードを1枚選び出し、手札に加える。その後、その山札をよく切る。：最新の説明

### p.312（PDF 314）の「山札」「手札」「トラッシュ」の項（G6）

- 「特に指示されないかぎり、自分や相手の山札の内容を見てはいけません。」「特に指示されないかぎり、自分や相手の山札を切ったり、カードの順番を変えたりしてはいけません。」
- 「「カードを引く」と指定されたときには、山札の一番上のカードを取って、手札に加えます。」「特に指示されないかぎり、引いたカードを相手プレイヤーに見せる必要はありません。」（既存の記録と同じ）
- 「特に指示されないかぎり、手札として持っているカードを直接トラッシュしてはいけません。」
- 「カードをトラッシュするときには、かならず表を上にして置きます。」（どちらのプレイヤーもトラッシュの内容を見られる。トラッシュに順番はない、は既存の記録と同じ）
- 山札から選び出す（探す）ことの一般の規定・山札が 0 枚のときに選び出す効果の扱いは書かれていない

## 3. 規定（CS1〜CS21）

「再利用」は既存の記録で決まり、今回読み直していないもの。「p.260」「p.310 の例」「p.312 の山札」は今回読んだもの。テストはどれも tests/test_computer_search_v0_22.py。

| id | 事項 | 分類 | 根拠 | 実装 | テスト |
|---|---|---|---|---|---|
| CS1 | 処理は最新の説明にしたがう（印刷の文面と違う） | CONFLICT（書き方の違い。「すてることによって…できる」→「選んでトラッシュしなければ、このカードは使えない」（使うための条件）、「選んで手札にすることができる」→「選び出し、手札に加える」、「よくきってもとに戻す」→「その後、その山札をよく切る」） | p.260 の最新の説明・図版、p.310 の例。p.6 | `TrainerEntry.play_text_ja` に最新の説明、`text_ja` に写しの文面 | `RegistrationTest.test_entry_follows_the_verified_latest_description` |
| CS2 | 使うための条件は、手札からカードを 2 枚選んでトラッシュすること。2 枚トラッシュできなければ使えない | CONFIRMED | p.260 の最新の説明「手札からカードを2枚選んでトラッシュしなければ、このカードは使えない。」。p.310 の例「2枚トラッシュできないときには、「パソコン通信」を使うことはできません。」 | `check_playable` が `IllegalActionError("INSUFFICIENT_CARDS_IN_HAND")`（手札から出す前。カードは手札に残る） | `UsableTest.test_hand_of_one_or_two_cards_cannot_use_it` |
| CS3 | 使っているこのカードは、トラッシュする手札に含まれない | CONFIRMED | 再利用: p.310 の手順（1 手札から出して相手に見えるようにする → 3 使うための条件にしたがう。trainers-v0.2b.md 2 章）。条件を確かめる時点で、このカードは手札にない | `check_playable` はこのカードを除いて数える。決定の選べるものは手札から出したあとの手札（`trainer_in_use` のこのカードは選べない） | `UsableTest.test_hand_of_three_cards_can_use_it`・`DiscardStageTest.test_invalid_choices_keep_the_decision` |
| CS4 | 使う前の手札が合計 1 枚（このカードだけ）・2 枚なら使えない。3 枚以上なら使える | CONFIRMED（CS2・CS3 から） | 同上 | 同上 | `UsableTest` |
| CS5 | ほかの使うための条件はない（自分の場・相手の場・手札の種類は条件にならない） | CONFIRMED | p.260 の最新の説明が挙げる条件は手札のトラッシュだけ。p.310 の例も同じ。再利用: p.310（使うための条件はカードに書かれたもの） | ほかを確かめない | `UsableTest.test_hand_of_three_cards_can_use_it` |
| CS6 | 山札が 0 枚のときに使えるか | **UNRESOLVED** | 使うための条件は手札のトラッシュだけ（p.260・p.310 の例）で、山札が 0 枚のときは書かれていない。条件を満たせても、残りの説明（山札から 1 枚選び出す）は行えない。p.312 の「カードが足りないときは、引けるだけのカードを引いてください」「負けにはなりません」は「カードを引く」ときの規定で、選び出すときの規定ではない。p.310 は「使うための条件を満たすことができないとき」は使えないとだけ書き、残りの説明を行えないときを書かない。使える（手札 2 枚をトラッシュするだけ）とも、使えないとも決められない | `check_playable` が使うための条件の確認のあとで `UnsupportedError("UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK")`（手札から出す前。状態・乱数・ログは変わらない） | `UsableTest.test_empty_deck_is_unresolved_and_checked_after_the_condition` |
| CS7 | トラッシュする 2 枚を選ぶのは使ったプレイヤー | CONFIRMED | p.260 の最新の説明「手札からカードを2枚選んで」（使うプレイヤーへの指示）。解説「これはなかなか選ぶのがたいへんです」 | 決定 `DISCARD_FROM_HAND` の `player` は使ったプレイヤー | `DiscardStageTest.test_decision_shape_and_card_in_use`・`test_invalid_choices_keep_the_decision`（相手の答えは `NOT_YOUR_DECISION`） |
| CS8 | ちょうど 2 枚。同じ名前の別のカード 2 枚を選べる。同じカードを 2 回は選べない | CONFIRMED | p.260「カードを2枚」（カードは 1 枚ずつの物。名前の制限は書かれていない） | 選ぶ数 2〜2。重複は `DUPLICATE_CHOICE`、数の違いは `INVALID_CHOICE_COUNT` | `test_two_cards_with_the_same_name_can_be_discarded`・`test_invalid_choices_keep_the_decision` |
| CS9 | 選べるのは自分の手札のカードだけ（使用中のこのカード・場・山札・トラッシュ・相手のカードは選べない） | CONFIRMED | p.260「手札から」。p.312「特に指示されないかぎり、手札として持っているカードを直接トラッシュしてはいけません」（指示があるのは手札） | 選べるもの = 手札のカードの uid（手札の並び）。ほかは `INVALID_CHOICE` | `test_invalid_choices_keep_the_decision`・`test_discarded_cards_cannot_be_chosen_as_trash` |
| CS10 | トラッシュしたカードは公開。トラッシュに順番はない | CONFIRMED | p.312「カードをトラッシュするときには、かならず表を上にして置きます。」。再利用: トラッシュに順番はない（p.312） | 選んだカードを手札の並びの順にトラッシュする（実装上の判断。答えの並びによらず同じ状態）。ログ `discard_from_hand` の `cards` は公開 | `test_answer_order_does_not_matter`・`test_two_cards_with_the_same_name_can_be_discarded` |
| CS11 | 山札から選ぶのは使ったプレイヤーで、どの種類のカードでもよい（ポケモン・トレーナー・エネルギー）。1 枚 | CONFIRMED | p.260 の最新の説明「あなたの山札からカードを1枚選び出し」。解説「何でも好きなカードを1枚、自分の山札から持ってくることができる」 | 決定 `SEARCH_DECK`（`player` は使ったプレイヤー。選べるものは山札のすべてのカード。1〜1 枚） | `SearchStageTest.test_decision_shape`・`test_any_card_and_any_position_can_be_chosen` |
| CS12 | 選ぶことは省略できない（山札が 1 枚以上なら 1 枚選ぶ） | CONFIRMED | p.260 の最新の説明は「選び出し、手札に加える。」（印刷の文面の「できる」がない） | 選ぶ数の下限 1（0 枚は `INVALID_CHOICE_COUNT`） | `test_invalid_choices_keep_the_discards_and_the_decision` |
| CS13 | 使ったプレイヤーは山札の中を見て選ぶ。相手は見ない | CONFIRMED | p.312「特に指示されないかぎり、自分や相手の山札の内容を見てはいけません。」に対し、このカードは山札から選び出す指示 | 山札のカードは決定の選べるもの（内部の状態）にだけ持ち、ログに書かない。選べるものの並びは uid の小さい順（山札の並びを決定に写さない。実装上の判断） | `test_decision_shape`・`test_hidden_information_stays_out_of_the_log` |
| CS14 | 選んだカードを相手に見せる必要はない | SUPPORTED | 最新の説明に見せる指示がない。p.312「特に指示されないかぎり、引いたカードを相手プレイヤーに見せる必要はありません。」（「引いた」カードの規定）。同じページのダウジングマシーンの最新の説明は「相手プレイヤーに見せてから」と書く（見せるときは指示がある） | ログ `search_deck` の `card` は選んだプレイヤーだけが見る項目（非公開の情報。architecture-v0.2b.md 9 章の方針） | `test_hidden_information_stays_out_of_the_log` |
| CS15 | 山札が 1 枚: そのカードを選ぶ。山札は 0 枚になる | CONFIRMED（CS11・CS12 から） | 同上 | 1 枚でも決定を出す（実装上の判断。ポケモンいれかえ・突風と同じ） | `test_deck_of_one` |
| CS16 | 順番: 手札をトラッシュ（使うための条件）→ 山札から選び出して手札に加える → その山札を切る | CONFIRMED | 再利用: p.310 の手順 3（使うための条件）→ 4（残りの説明）。p.260「…手札に加える。その後、その山札をよく切る。」 | 段階 1 の答えでトラッシュ → 段階 2 の決定 → 段階 2 の答えで手札に加える → 切る。ログ `play_trainer` → `discard_from_hand` → `search_deck` → `shuffle` → `discard_trainer` | `test_two_cards_with_the_same_name_can_be_discarded`・`test_any_card_and_any_position_can_be_chosen`・`test_hidden_information_stays_out_of_the_log` |
| CS17 | その（自分の）山札を切る | CONFIRMED | p.260「その山札をよく切る」。p.312「特に指示されないかぎり…山札を切ったり…してはいけません」（指示がある） | `zones.shuffle_deck`（v0.1 の「デッキを切る」と同じ。乱数 `state.rng` の並べかえ 1 回。実装上の仮定の再利用）。0・1 枚なら乱数を使わない | `test_any_card_and_any_position_can_be_chosen`・`test_deck_of_one`・`test_same_seed_and_commands_give_the_same_result` |
| CS18 | 使い終わったらこのカードをトラッシュする（効果のあと） | CONFIRMED（使いすて）・SUPPORTED（時点） | 再利用: p.310（trainers-v0.2b.md 2 章） | `engine._finish_trainer`（既存。`discard_trainer` は `shuffle` のあと） | `AfterResolutionTest.test_turn_continues_and_the_searched_card_can_be_used` |
| CS19 | 使っても番は続く。同じ番に別のパソコン通信を使える（1 枚目のトラッシュに、もう 1 枚を選ぶこともできる） | CONFIRMED | 再利用: p.310（1 回の番で何枚でも。すませたら番の続き） | 回数を数えない（既存） | `test_turn_continues_and_the_searched_card_can_be_used`・`test_another_computer_search_in_the_same_turn` |
| CS20 | 手札に加えるのは「カードを引く」ではない。山札が 0 枚になっても負けではなく、負けるのは次の自分の番の最初に引けないとき | CONFIRMED | p.312「「カードを引く」と指定されたときには、山札の一番上のカードを取って…」（選び出すのは引くことではない）。再利用: 負けは番の最初に引けないときだけ（p.309・p.312） | `zones.search_deck_to_hand`（`draw_cards` を使わない）。番の最初のドローは既存 | `test_empty_deck_after_search_loses_only_at_the_next_draw`・`test_deck_of_one` |
| CS21 | 段階 2 の答えが不正でも、すんだ段階 1（トラッシュ）は取り消さない。決定を待ったまま、カードは使用中 | 実装上の判断（p.310「そのトレーナーカードによって起こることをすべてすませてからでないと、他のことはできません」と矛盾しない） | — | 決定の確認（`check_choices`）が状態を変える前に拒否する（v0.2a からの決定の仕組み） | `test_invalid_choices_keep_the_discards_and_the_decision` |

## 4. 実装

- `effects.DiscardFromHandThenSearchDeck(discard=2, search=1)`（`implementation_id` `discard_from_hand_then_search_deck`）を `TrainerEntry` で PMCG1-090 に登録しました（`DEFAULT_EFFECTS` の id は `kyuura-engine-0.13` のまま）。
  - `check_playable`: このカードを除く手札が 2 枚未満なら `INSUFFICIENT_CARDS_IN_HAND`（CS2〜CS4）、そのあと山札が 0 枚なら `UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK`（CS6）。どちらも手札から出す前で、状態・乱数・ログは変わらない。拒否のコードの順番は「`IllegalActionError` のあとに `UNRESOLVED_…`」（docs/architecture-v0.7.md 12 章の約束）。
  - `resolve`: 段階 1 の決定 `DISCARD_FROM_HAND`（選べるものは手札。2〜2 枚）。
  - `resume`: 段階 1 の答えなら `zones.discard_from_hand` でトラッシュし、段階 2 の決定 `SEARCH_DECK`（選べるものは山札の uid の小さい順。1〜1 枚）を出す。段階 2 の答えなら `zones.search_deck_to_hand` で手札に加え、`zones.shuffle_deck` で切る。決定がなくなったら、エンジンがこのカードをトラッシュする（既存の `_resume_trainer` → `_finish_trainer`）。
  - `decision_problems`: 決定するのは使ったプレイヤー・種類・選ぶ数・選べるもの（段階 1 は手札、段階 2 は山札）・使っているこのカードを選べないこと・段階 2 は段階 1 のトラッシュのあと。不変条件が決定を待つたびに確かめる。
- 複数段階の選択は、既存のトレーナーの決定の再開（`resume` が次の決定を出す。v0.2b の約束）で表しました。別の決定の列・汎用の効果の書き方は作っていません。`engine.py`・`kyuura_engine/resolution/` にカード id・実装での分岐はありません（`RegistrationTest.test_no_card_specific_branch_in_the_engine`）。
- 決定の種類を 2 つ加えました（`decisions.DISCARD_FROM_HAND = "discard_from_hand"`・`SEARCH_DECK = "search_deck"`。段階は既存の `Phase.DECISION`、再開先は既存の `"trainer"`）。

### 共通の部品の変更（4 章の比較で、既存の処理が変わらないことを確かめた）

| 変更 | 理由 | 既存の処理との差 |
|---|---|---|
| `zones.shuffle_deck(state, player)` を加え、`engine._shuffle_deck` はそれを呼ぶだけにした | 効果で山札を切る処理（effects.py）から使うため（effects.py は engine.py を読み込まない） | 本体は v0.21 の `engine._shuffle_deck` と同じ（`state.rng.shuffle` 1 回・ログ `shuffle`）。対戦の準備・切り直しの乱数の使い方は同じ |
| `zones.discard_from_hand(state, player, cards)` を加え、`zones.discard_hand` とカードを動かす部分（`_hand_to_discard`）を共通にした | 手札の一部を選んでトラッシュする処理と、オーキドはかせの手札をすべてトラッシュする処理で、同じゾーンの操作を重ねて書かないため | `discard_hand` の動き（手札の並びの順にトラッシュの最後へ・持ち主の確認・ログ `discard_hand`）は同じ。ログのイベントは別（監査は `discard_hand` を「手札のすべて」と確かめる） |
| `zones.search_deck_to_hand(state, player, card)` を加えた | 山札の指定したカードを手札に加える処理（「カードを引く」の `draw_cards` とは別） | 新しい処理 |

オーキドはかせの `discard_hand` を、選んだ 2 枚に使う形（手札を一時的に分けるなど）にはしていません。手札を「すべて」トラッシュする規定と、「選んで」トラッシュする規定は別のもので、ログの監査の確かめ方も違うためです。

### ログ（新しいイベント 2 つ・既存のイベント 1 つを効果でも使う）

| イベント | 項目 | 見せてよい相手 | 意味 |
|---|---|---|---|
| `discard_from_hand`（新規） | `player`・`cards` | 全員（トラッシュは表を上にして置く。p.312） | 使うための条件で、手札から選んだカードをトラッシュした（手札の並びの順） |
| `search_deck`（新規） | `player` | 全員 | 山札からカードを 1 枚選び出して手札に加えた |
| `search_deck`（新規） | `card` | 選んだプレイヤーだけ（CS14） | 選んだカード |
| `shuffle`（v0.1 から） | `player` | 全員 | 山札を切った。v0.22 から、対戦の準備・切り直しのほかに、カードの効果でも出る |

山札の中身（段階 2 の決定の選べるもの）は内部の状態（`GameState.decision`）にだけあり、ログには書きません（`test_hidden_information_stays_out_of_the_log`）。今のログ・`state_to_dict` は内部の完全な記録で、見る人ごとに伏せたログ・表示の API は未実装です（architecture-v0.2b.md 9 章。v0.22 でも作っていない）。ログの監査（tests/log_audit.py）は、`discard_from_hand`（手札 → トラッシュ）と `search_deck`（山札 → 手札。持ち主・手札やトラッシュにないこと）を組み立て直しに加えました。

### 拒否のコード

- `INSUFFICIENT_CARDS_IN_HAND`（新規。`IllegalActionError`）: 使うための条件（このカードを除く手札 2 枚）を満たせない。
- `UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK`（新規。`UnsupportedError`）: CS6。
- 決定の答えの拒否は既存のコード（`INVALID_CHOICE`・`INVALID_CHOICE_COUNT`・`DUPLICATE_CHOICE`・`NOT_YOUR_DECISION`・`WRONG_DECISION`・`WRONG_PHASE`）。

書き出しは形式 9 のまま（状態の項目を加えていない）。決定を待つ間は使用中のトレーナーがあるので形式 3 以上で書き出せます（v0.2b から同じ）。公開の API（`kyuura_engine` の公開の名前・コマンド）は変えていません。

## 5. 未解決と変えていないもの

- 新しい未解決: CS6（`UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK`）。エンジンが止める `UNRESOLVED_…` は 20 件、未解決の裁定は 26 件になりました（v0.21 までの 19 件・25 件は変えていない）。既存の「効果の対象がないときに使えるか」の問い（きずぐすり `UNRESOLVED_POTION_WITHOUT_DAMAGE`・ポケモンいれかえ `UNRESOLVED_SWITCH_WITHOUT_BENCH`・突風 `UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH`）と同じ形ですが、カードと条件が違う別の問いです（パソコン通信は使うための条件が明記され、その条件は満たせる。足りないのは残りの説明の対象）。どれも解消していません。kyuura に論点がないので、研究の対応表では `kyuura_disposition` を `not_in_kyuura` にしています。
- 既存のカードの裁定・確度の分類、固定した参照データ（tests/fixtures/）、研究の基準・写しの元のコミット、v0.20 の固定のデッキ、v0.21 の突風の変種は変えていません。

## 6. 組み合わせの対戦（tools/preset_deck_games.py の `--variant computer`）

v0.20 の 2 つの固定のデッキのディフェンダー 4 枚のうち 3 枚をパソコン通信 3 枚に置き換えた一時的な 60 枚どうしで、正式な対戦開始から対戦させました（`deck_cards`。公開の固定のデッキ・突風の変種は変えていない）。手順に加えたのはパソコン通信の使い方だけです（1 番に 1 回だけ考え、このカードを除く手札が 2 枚以上・山札が 1 枚以上で、山札に今の番に使えるカード（進化できる進化カード → ベンチが 2 匹未満ならたねポケモン → まだつけていない番の、足りないタイプの基本エネルギー）があれば使う。トラッシュする 2 枚は決まった順で選ぶ）。強い AI ではなく、勝率でカードの強さを判断していません。山札が 0 枚の番は使いません（CS6）。結果の数は [v0.22-verification.md](v0.22-verification.md) 5 章です。

## 7. kyuura への報告事項（kyuura にはコミット・プッシュしない）

1. パソコン通信（PMCG1-090）の照合の記録（CC-）・最新の説明・p.260 のページの記録がない（`research_links.json` の `card_checks.engine_verified_without_kyuura_record` に挙げた）。
2. 山札が 0 枚のときにパソコン通信を使えるか（CS6）の論点（UQ-）がない（`stop_codes` の `not_in_kyuura`）。
3. p.310 の「使うための条件」の例（パソコン通信）と、p.312 の山札の規定（「特に指示されないかぎり、自分や相手の山札の内容を見てはいけません」「…山札を切ったり、カードの順番を変えたりしてはいけません」）の記録が、kyuura の rule_history.json・rule_differences.json にない。
4. kyuura の写し（第1弾の印刷の文面）と p.260 の図版の文面は同じ（誤りはない）。最新の説明と区別した記録がない。

## 8. 次にカードを加えるときの注意

- 手札の一部を選んでトラッシュするトレーナー（ダウジングマシーン・エネルギー回収など「手札からカードを…トラッシュしなければ」）は、`zones.discard_from_hand` とログ `discard_from_hand` を使い、使うための条件を `check_playable` で確かめてください。手札をすべてトラッシュする `discard_hand` と混ぜないでください。
- 山札から選び出すトレーナー・ワザは `zones.search_deck_to_hand`（ログ `search_deck` の `card` は非公開の項目）と、指示があれば `zones.shuffle_deck` を使ってください。「カードを引く」（`draw_cards`）と混ぜないでください。選び出せるものの種類に制限があるカード（「たねポケモン」「エネルギーカード」など）は、その種類が山札にないときの扱いを原典で確かめてください（CS6・CS12 と同じ問いが起こる）。
- 選んだカードを相手に見せる指示のあるカード（ダウジングマシーンなど）は、見せたカードを公開の項目にするログの形を決めてください（今の `search_deck` は非公開）。
