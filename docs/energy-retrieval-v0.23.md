# エネルギー回収（v0.23）: 照合済みの記録の再利用と実装

v0.23 で、トレーナーのエネルギー回収（PMCG1-076。ポケモンカード第1弾）を対応にしました。あわせて、突風とパソコン通信を同じデッキに入れた対戦を確かめました（6 章）。`CLAUDE.md` の「照合済みの記録の再利用」（[verified-record-reuse.md](verified-record-reuse.md)）の手順にしたがい、トレーナーの使いかたなど既存の記録で決まることは読み直していません。既存の記録で足りなかったカードのページ（p.257 のエネルギー回収の部分）だけを原典で確かめました。

- 基準のルール: 「ポケットモンスターカードゲーム公式ルール 2000.02.14版」（『ポケモンカードオフィシャルブック2000』pp.306〜326 [P43]）
- カードの処理: 同じ本のカードのページの「最新の説明」（p.6「この本の使いかた」。[trainers-v0.2b.md](trainers-v0.2b.md) の前提と同じ）
- カードデータ: kyuura `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`（写しの元。変えていない）。研究の基準: kyuura `3f349085645f47d0649a6cacece3680caeae50bf`（変えていない）
- 分類（CONFIRMED・SUPPORTED・UNRESOLVED・CONFLICT）の意味は [trainers-v0.2b.md](trainers-v0.2b.md) 1 章と同じ

## 1. 既存の記録を探した結果（手順の 1〜5）

| 探した記録 | 結果 | 使い方 |
|---|---|---|
| kyuura `data/cards.json`（`ecb2d69`・`3f34908` で同じ） | PMCG1-076 エネルギー回収。文面「手札から1枚のカードをすてることによって、トラッシュから2枚の好きなエネルギーカードをひろって、手札に加えることができる。」（なぞのばしょの転記。第1弾の印刷）。`jp_en_differences` にエラッタ（基本エネルギーだけを拾える）の説明 | 登録の照合（`TrainerEntry.text_ja`）だけに使う。処理の根拠にはしない |
| kyuura `data/rule_history.json` の `ERR-ENERGY-RETRIEVAL`（公式のエラッタ） | 会報 Vol.5（1998-06-10）で「基本エネルギーカード」に解釈が変わったこと。notes の 8 番目に、kyuura が p.257 のスキャン（根拠 J38）で読んだ最新の説明「手札からカードを1枚選んでトラッシュしなければ、このカードは使えない。あなたのトラッシュから「基本エネルギーカード」を最大2枚選び出し、手札に加える。ただし、このカードを使うためにトラッシュしたカードを選ぶことはできない。」と、解説の 1 文「「エネルギー回収」では、「無色2個エネルギー」や「なんでもなおし配合エネルギー」などの特殊エネルギーカードは手札に加えることはできません。」 | **再利用**（最新の説明の文面と、特殊エネルギーを選べないこと。kyuura が原典を読んだ記録で、エンジンの記録の取り込みではない）。会報 Vol.5 の「「最大2枚」なので 1 枚だけでも手札に加えられる」は 1998 年の資料で基準の資料ではないので、根拠にしない（ER8 の参考にとどめる） |
| kyuura `rule_history.json` の P43 の p.257 のページの記録 | 「エネルギー回収（第1弾ほか。「基本エネルギーカード」を最大2枚。特殊エネルギーは手札に加えられない）」。照合の記録の取り込みはプラスパワー・ディフェンダーだけ | 再利用（同上） |
| kyuura のサイドカー（LD-・CC-・CR-・UQ-） | このカードの記録はない。`UQ-ENERGY-CONVERSION-ZERO`（ゴースのエナジーへんかんで 0 枚を選べるか）はあるが、`cases` はエナジーへんかんだけで、「「最大○枚」と書くほかのカードは、kyuura では調べていない」 | ER9 の重複の確認（別のカードの別の論点として扱う。5 章） |
| `kyuura_engine/data/card_verification.json` | このカードの記録はない | — |
| docs/trainers-v0.2b.md 2 章（トレーナー共通） | p.310 のトレーナーの使いかた（手順 1 手札から出す → 2 名前を伝える → 3 使うための条件にしたがう → 4 残りの説明。使うための条件を満たせなければ使えない・何枚でも・使いすて・トラッシュの時点） | **再利用** |
| docs/computer-search-v0.22.md（パソコン通信） | 手札から選んでトラッシュする処理（`zones.discard_from_hand`・ログ `discard_from_hand`・決定 `DISCARD_FROM_HAND`）、使用中のカードを数えないこと（CS3）、p.312 のトラッシュは表を上にして置く（公開）、山札が 0 枚のとき（CS6。トレーナーでは p.309 の「処理の対象がない内容は無視」を当てはめていない） | **再利用**（処理の部品と、p.310・p.312 の規定。枚数はこのカードの最新の説明で別に決める） |
| docs/haunter-line-v0.9.md（ゴースのエナジーへんかん） | 「エネルギーカード」を最大 2 枚（H3）、0 枚を選べるか（H4。UNRESOLVED）、トラッシュにないとき（H5。ワザなので p.309 で SUPPORTED） | 似ているが別のカード（ワザ・「エネルギーカード」・トラッシュしたカードを除く規定がない）。枚数・対象は流用せず、このカードの最新の説明で決めた。H4 は同じ言い回しの問いとして 5 章で扱いを比べた |
| docs/architecture-v0.2b.md 9 章 | 非公開の情報は、イベントの種類ごとの決まった項目にだけ入れる | **再利用**（実装上の方針） |

既存の記録で足りなかったもの（原典に戻る前に書いたこと）:

1. G1: p.257 の図版の文面（写しとの照合。kyuura の記録は最新の説明と解説の 1 文だけで、図版を照合していない）。
2. G2: 見出し・収録商品。
3. G3: 解説のうち、処理に関わるほかの記述（手札の枚数・トラッシュに基本エネルギーカードがないとき・0 枚を選べるか）。kyuura の記録は解説の特殊エネルギーの 1 文だけ。

最新の説明の文面は kyuura の記録を再利用できる範囲でしたが、照合の記録（`card_verification.json`）には同じ画像で読んだ文を書きました（2 章。kyuura の記録と同じ）。ページは推測せず、本の索引（p.354「シリーズ別カードさくいん」。第1弾のトレーナーカード「エネルギー回収 …… 257」）で探しました。一般のルールの通読・同じページのプラスパワー・ディフェンダーの読み直しはしていません。

## 2. 原典で確かめたこと（2026-10-15）

Internet Archive のスキャン [J38]（PDF 372 ページ、`PDF n = p.(n-2)`）を画像にし（ページ全体は 110dpi で位置を確かめ、読む部分は 400dpi で切り出した）、目で読みました。

### p.257（PDF 259）のエネルギー回収（いちばん下。同じページのプラスパワー・ディフェンダーは読み直していない）

| 項目 | 内容 |
|---|---|
| 見出し・収録 | 「エネルギー回収」、収録「ポケモンカード第1弾」「ポケモンジム第1弾タケシ」「ポケモンジム第2弾エリカ」「ポケモンジム第3弾ナツメ」「クイックスターターギフトパック」 |
| 図版の文面 | 「手札からカードを1枚選んでトラッシュしなければ、このカードは使えない。あなたのトラッシュから基本エネルギーカードを最大2枚選び、手札に加えてよい。(ただし、このカードを使うためにトラッシュしたカードを選ぶことはできない)」。第1弾の印刷（kyuura の写し）ではない版（どの商品の版かは決めていない） |
| 最新の説明 | 「手札からカードを1枚選んでトラッシュしなければ、このカードは使えない。あなたのトラッシュから「基本エネルギーカード」を最大2枚選び出し、手札に加える。ただし、このカードを使うためにトラッシュしたカードを選ぶことはできない。」（kyuura の ERR-ENERGY-RETRIEVAL の記録と同じ） |
| 解説（処理に関わる記述） | 「「エネルギー回収」を使うとき、「手札のカードを1枚トラッシュしないといけない、さてどのカードをトラッシュしようか？」けっこう悩むところです。」「注意する点としては、「エネルギー回収」を使うときにトラッシュしたエネルギーカードは回収できないことです。それ以外にも、「エネルギー回収」では、「無色2個エネルギー」や「なんでもなおし配合エネルギー」などの特殊エネルギーカードは手札に加えることはできません。」。ほかは使いどころ（エネルギーをトラッシュするワザを持つ炎・雷のデッキ、多色のデッキ）。トラッシュに基本エネルギーカードがないとき・0 枚を選べるかの記述はない |

図版は「手札に加えてよい」（任意に読める）と書きますが、最新の説明は「選び出し、手札に加える」で、処理の根拠は最新の説明です（図版の言い回しで 0 枚の扱いを決めない。ER9）。

## 3. 規定（ER1〜ER17）

「再利用」は既存の記録で決まり、今回読み直していないもの。「p.257」は今回読んだもの（最新の説明は kyuura の記録と同じ）。テストはどれも tests/test_energy_retrieval_v0_23.py。

| id | 事項 | 分類 | 根拠 | 実装 | テスト |
|---|---|---|---|---|---|
| ER1 | 処理は最新の説明にしたがう（印刷の文面・図版と違う） | CONFLICT（エラッタ。第1弾の印刷は「好きなエネルギーカード」「すてることによって…できる」。図版は別の版の文面） | p.257 の最新の説明・図版。p.6。kyuura の ERR-ENERGY-RETRIEVAL | `TrainerEntry.play_text_ja` に最新の説明、`text_ja` に写しの文面 | `RegistrationTest.test_entry_follows_the_verified_latest_description` |
| ER2 | 使うための条件は、手札からカードを 1 枚選んでトラッシュすること。使っているこのカードは含まない。手札が合計 1 枚（このカードだけ）なら使えず、2 枚以上なら使える | CONFIRMED | p.257「手札からカードを1枚選んでトラッシュしなければ、このカードは使えない。」。再利用: p.310 の手順（手札から出してから使うための条件。CS3 と同じ規定） | `check_playable` が `IllegalActionError("INSUFFICIENT_CARDS_IN_HAND")`（手札から出す前。カードは手札に残る） | `UsableTest.test_hand_of_this_card_only_cannot_use_it` |
| ER3 | トラッシュするカードの種類に制限はない（ポケモン・トレーナー・エネルギー。もう 1 枚のエネルギー回収も） | CONFIRMED | p.257「カードを1枚」。解説「どのカードをトラッシュしようか？」 | 選べるもの = 手札のすべてのカード | `test_any_kind_of_card_can_be_discarded`・`AfterResolutionTest.test_second_energy_retrieval_in_the_same_turn` |
| ER4 | トラッシュするカード・手札に加えるカードを選ぶのは使ったプレイヤー | CONFIRMED | p.257「手札から…選んで」「あなたのトラッシュから…選び出し」 | 決定 `DISCARD_FROM_HAND`・`RETRIEVE_ENERGY` の `player` は使ったプレイヤー | `DiscardStageTest`・`RetrieveStageTest`（相手の答えは `NOT_YOUR_DECISION`） |
| ER5 | 順番: 手札をトラッシュ（使うための条件）→ トラッシュの基本エネルギーカードを選んで手札に加える | CONFIRMED | p.257 の文の順番。再利用: p.310 の手順 3 → 4 | 段階 1 の答えでトラッシュ → 段階 2 の決定 → 段階 2 の答えで手札に加える。ログ `play_trainer` → `discard_from_hand` → `retrieve_energy` → `discard_trainer` | `RetrieveStageTest.test_retrieve_one_or_two_basic_energy_cards` |
| ER6 | 手に入れられるのは自分のトラッシュの基本エネルギーカードだけ（特殊エネルギーカード・トレーナー・ポケモン・相手のトラッシュのカードは選べない） | CONFIRMED | p.257「あなたのトラッシュから「基本エネルギーカード」を」・解説「特殊エネルギーカードは手札に加えることはできません」 | 選べるもの = 自分のトラッシュのうち `is_basic_energy` のカード。今の写しに特殊エネルギーのカードはない（規定は実装したが、特殊エネルギーで確かめるテストはない） | `test_decision_shape_excludes_the_discarded_card`・`test_invalid_choices_keep_the_discard_and_the_decision`・`UsableTest.test_no_basic_energy_in_the_discard_is_unresolved`（相手のトラッシュ） |
| ER7 | このカードを使うためにトラッシュしたカードは選べない（基本エネルギーカードでも） | CONFIRMED | p.257「ただし、このカードを使うためにトラッシュしたカードを選ぶことはできない。」・解説「「エネルギー回収」を使うときにトラッシュしたエネルギーカードは回収できない」 | 段階 2 の選べるものから段階 1 でトラッシュしたカード（決定の `context` の `"discarded"`）を除く。不変条件がログの `discard_from_hand` と照らす | `test_decision_shape_excludes_the_discarded_card`・`test_invalid_choices_keep_the_discard_and_the_decision` |
| ER8 | 最大 2 枚。選べるものが 1 枚なら 1 枚まで。2 枚以上あっても 1 枚だけを選べる | CONFIRMED | p.257「最大2枚」 | 決定の選ぶ数の上限 = min(2, 選べるものの数) | `test_retrieve_one_or_two_basic_energy_cards`・`test_only_one_target` |
| ER9 | 選べるものがあるのに 0 枚を選べるか | **UNRESOLVED** | p.257 の最新の説明は「最大2枚選び出し、手札に加える」で、0 枚を含むかを書かない。解説にもない。図版の「手札に加えてよい」は最新の説明ではない。ゴースのエナジーへんかんの H4 と同じ言い回しの問いだが、別のカード（トレーナー。使うための条件はすでに満たした）で、kyuura の `UQ-ENERGY-CONVERSION-ZERO` の対象でもない | 決定は 0 枚も受け付ける形（`min_choices` 0）にし、0 枚の答えで状態を変える前に `UnsupportedError("UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE")`。決定は待ったまま（1 枚以上を選び直せる）。段階 1 のトラッシュは取り消さない | `test_zero_cards_is_unresolved_and_keeps_the_decision` |
| ER10 | 使う前の自分のトラッシュに基本エネルギーカードがないときに使えるか（手札をトラッシュするだけで使えるか） | **UNRESOLVED** | 使うための条件は手札のトラッシュだけで満たせる（p.257）が、残りの説明の対象がないときは書かれていない。トラッシュする手札が基本エネルギーカードでも、ER7 で選べないので対象は生じない。p.309 の「処理の対象がなくなってしまっている場合、その内容は無視」はワザの処理の規定（エナジーへんかんの H5）で、トレーナーには当てはめていない（パソコン通信の CS6・きずぐすり・ポケモンいれかえ・突風と同じ扱い） | `check_playable` が使うための条件の確認のあとで `UnsupportedError("UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET")`（手札から出す前。状態・乱数・ログは変わらない） | `UsableTest.test_no_basic_energy_in_the_discard_is_unresolved`・`AfterResolutionTest.test_second_energy_retrieval_in_the_same_turn` |
| ER11 | 選べるものの数を決める時点 | CONFIRMED（ER7 から） | トラッシュしたカードは選べないので、段階 2 の選べるもの = 使う前のトラッシュの基本エネルギーカード（ほかに変わるものはない）。使う前に数えても、トラッシュのあとに数えても同じ | `check_playable` は使う前のトラッシュで ER10 を確かめ、段階 2 はトラッシュのあとのトラッシュからトラッシュしたカードを除いて選べるものを作る（0 枚なら確認の漏れとして `RuntimeError`） | `UsableTest.test_no_basic_energy_in_the_discard_is_unresolved`（トラッシュする手札が炎エネルギーでも止まる） |
| ER12 | 同じ名前の別のカード 2 枚・タイプの違う 2 枚を選べる。同じカードを 2 回は選べない | CONFIRMED | p.257「基本エネルギーカードを最大2枚」（名前・タイプの制限は書かれていない。カードは 1 枚ずつの物） | 重複は `DUPLICATE_CHOICE`、数の違いは `INVALID_CHOICE_COUNT` | `test_retrieve_one_or_two_basic_energy_cards`・`test_invalid_choices_keep_the_discard_and_the_decision` |
| ER13 | 手に入れたカードは公開の情報（トラッシュから手札に移ったカードは、だれにも分かる） | SUPPORTED | 最新の説明に「見せる」の指示はないが、p.312「カードをトラッシュするときには、かならず表を上にして置きます。」（トラッシュは公開）。再利用: トラッシュに順番はない（p.312） | ログ `retrieve_energy` の `cards` は公開（トラッシュの並びの順。答えの並びによらない）。決定の選べるものもトラッシュの公開のカード | `test_retrieve_one_or_two_basic_energy_cards` |
| ER14 | 使い終わったらこのカードをトラッシュする。使っても番は続く。同じ番に何枚でも使える | CONFIRMED（使いすて・何枚でも）・SUPPORTED（時点） | 再利用: p.310（trainers-v0.2b.md 2 章） | `engine._finish_trainer`（既存。`discard_trainer` は `retrieve_energy` のあと） | `AfterResolutionTest` |
| ER15 | 対象が 1 枚でも決定を出す（段階 1・段階 2 とも） | 実装上の判断（パソコン通信・ポケモンいれかえ・突風と同じ） | — | 決定 `DISCARD_FROM_HAND`（1〜1 枚）・`RETRIEVE_ENERGY`（0〜min(2, 数) 枚） | `UsableTest.test_hand_of_this_card_only_cannot_use_it`・`test_only_one_target` |
| ER16 | 段階 2 の答えが不正でも、すんだ段階 1（トラッシュ）は取り消さない。決定を待ったまま、カードは使用中 | 実装上の判断（パソコン通信の CS21 と同じ） | — | 決定の確認が状態を変える前に拒否する（ER9 の止める処理も状態を変える前） | `test_invalid_choices_keep_the_discard_and_the_decision`・`test_zero_cards_is_unresolved_and_keeps_the_decision` |
| ER17 | 手に入れた基本エネルギーカードは手札のカードで、その番にまだエネルギーをつけていなければ、1 枚つけられる | CONFIRMED | 再利用: p.310（手札からエネルギーカードを 1 番に 1 枚） | 既存の `AttachEnergy` | `test_turn_continues_and_the_retrieved_energy_can_be_attached`・`RetrievalGamesTest` |

「回収できるカードの規定」（ER6。基本エネルギーカードだけ）と「今使えるカードの範囲」（写しの基本エネルギー 6 種類。特殊エネルギーのカードは写しになく、対戦に入らない）は別です。特殊エネルギーのカードを加えるときは、選べるものに入らないことをそのカードで確かめてください。

## 4. 実装

- `effects.DiscardFromHandThenRetrieveEnergy(discard=1, retrieve=2)`（`implementation_id` `discard_from_hand_then_retrieve_energy`）を `TrainerEntry` で PMCG1-076 に登録しました（`DEFAULT_EFFECTS` の id は `kyuura-engine-0.13` のまま）。
  - `check_playable`: このカードを除く手札が 1 枚未満なら `INSUFFICIENT_CARDS_IN_HAND`（ER2）、そのあと自分のトラッシュに基本エネルギーカードがなければ `UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET`（ER10）。どちらも手札から出す前。
  - `resolve`: 段階 1 の決定 `DISCARD_FROM_HAND`（選べるものは手札。1〜1 枚）。パソコン通信と同じ決定の種類。
  - `resume`: 段階 1 の答えなら `zones.discard_from_hand` でトラッシュし（パソコン通信と同じ関数。ログ `discard_from_hand`）、段階 2 の決定 `RETRIEVE_ENERGY`（選べるものはトラッシュの基本エネルギーカードからトラッシュしたカードを除いたもの。`context` の `"discarded"`。0〜min(2, 数) 枚）を出す。段階 2 の答えが 0 枚なら `UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE`（ER9）。1 枚以上なら `zones.return_discard_to_hand`（エナジーへんかん・ふしちょうと同じ関数）で手札に加え、ログ `retrieve_energy`。決定がなくなったら、エンジンがこのカードをトラッシュする（既存の `_resume_trainer` → `_finish_trainer`）。
  - `decision_problems`: 決定するのは使ったプレイヤー・種類・選ぶ数・選べるもの・使っているこのカードを選べないこと・段階 2 の `"discarded"` がログの最後の `play_trainer` のあとの `discard_from_hand` と同じこと。不変条件が決定を待つたびに確かめる。
- 決定の種類を 1 つ加えました（`decisions.RETRIEVE_ENERGY = "retrieve_energy"`。段階は既存の `Phase.DECISION`、再開先は既存の `"trainer"`）。ゴースのエナジーへんかんの `RECOVER_ENERGY`（ワザの決定。「エネルギーカード」。除くカードがない）とは意味が違うので、流用していません。
- `engine.py`・`kyuura_engine/resolution/`・`zones.py` は変えていません（共通の部品は既存のものをそのまま使った）。`engine.py`・`resolution/` にカード id・実装での分岐はありません（`RegistrationTest.test_no_card_specific_branch_in_the_engine`）。

### ログ（新しいイベント 1 つ）

| イベント | 項目 | 見せてよい相手 | 意味 |
|---|---|---|---|
| `discard_from_hand`（v0.22 から） | `player`・`cards` | 全員 | 使うための条件で、手札から選んだカードをトラッシュした（エネルギー回収では 1 枚） |
| `retrieve_energy`（新規） | `player`・`cards` | 全員（トラッシュは公開の情報。ER13） | 自分のトラッシュの基本エネルギーカードを手札に加えた（トラッシュの並びの順。1〜2 枚） |

ログの監査（tests/log_audit.py）は `retrieve_energy` を手札・トラッシュの組み立て直しに加え、自分のトラッシュの基本エネルギーカードであること・1〜2 枚・重複がないこと・そのトレーナーを使うためにトラッシュしたカード（`discard_from_hand` から `discard_trainer` まで）でないことを確かめます。エナジーへんかんの `recover_energy`（ワザの中だけ）・ふしちょうの `return_to_hand` とは別のイベントです（監査の確かめ方が違う）。

### 拒否のコード

- `INSUFFICIENT_CARDS_IN_HAND`（v0.22 から。`IllegalActionError`）: 使うための条件（このカードを除く手札 1 枚）を満たせない。
- `UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET`（新規。`UnsupportedError`）: ER10。
- `UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE`（新規。`UnsupportedError`）: ER9。
- 決定の答えの拒否は既存のコード（`INVALID_CHOICE`・`INVALID_CHOICE_COUNT`・`DUPLICATE_CHOICE`・`NOT_YOUR_DECISION`・`WRONG_DECISION`・`WRONG_PHASE`）。

書き出しは形式 9 のまま（状態の項目を加えていない。段階 2 の `"discarded"` は既存の決定の `context` に入る）。公開の API（`kyuura_engine` の公開の名前・コマンド）は変えていません（決定の種類の名前 `decisions.RETRIEVE_ENERGY` を加えただけ）。

## 5. 未解決と変えていないもの

- 新しい未解決: ER9（`UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE`）・ER10（`UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET`）。エンジンが止める `UNRESOLVED_…` は 22 件、未解決の裁定は 28 件になりました（v0.22 までの 20 件・26 件は変えていない）。
- 既存の未解決との重複: ER9 はエナジーへんかんの H4（`UNRESOLVED_RECOVER_ZERO_ENERGY`。kyuura の `UQ-ENERGY-CONVERSION-ZERO`）と同じ「最大2枚」の言い回しの問いですが、別のカード（トレーナー）・別の文（「基本エネルギーカード」・トラッシュしたカードを除く）で、kyuura の論点もエナジーへんかんだけを対象にしているので、別の裁定・別のコードにしました（どちらかの答えが見つかっても、もう一方を同じに扱わない）。ER10 は、トレーナーで残りの説明の対象がないときの問い（パソコン通信の CS6・突風の GW5・ポケモンいれかえ・きずぐすり）と同じ形ですが、カードと条件が違う別の問いです。どれも解消していません。kyuura に論点がないので、研究の対応表では `kyuura_disposition` を `not_in_kyuura` にしています。
- 既存のカードの裁定・確度の分類、固定した参照データ（tests/fixtures/）、研究の基準・写しの元のコミット、v0.20 の固定のデッキ、既存の対戦の変種（`preset`・`gust`・`computer`）は変えていません。

## 6. 組み合わせの対戦（tools/preset_deck_games.py）

正式な対戦開始（`new_game`・60 枚・サイド 6 枚）から、v0.20 の 2 つの固定のデッキをもとにした一時的な 60 枚どうしで対戦させます（公開の固定のデッキは変えない。`deck_cards`・`SUBSTITUTIONS`）。

| 変種 | 置き換え | 使い方 |
|---|---|---|
| `--variant mixed`（第1段階） | ディフェンダー 4 枚を除き、突風 2 枚・パソコン通信 2 枚を加える（ほかは同じ） | `python3 tools/preset_deck_games.py --games 20 --variant mixed`（席を入れかえて 20 局ずつ） |
| `--variant retrieval`（第2段階） | `mixed` からさらに、きずぐすり 2 枚を除き、エネルギー回収 2 枚を加える | `python3 tools/preset_deck_games.py --games 20 --variant retrieval` |

手順に加えたもの（決まった手順で、強い AI ではない。勝率でカードの強さを判断しない）:

- パソコン通信: 山札に突風があり、手札になく、突風の手順が今の番に使う場面（相手の控えのうち残りの HP がいちばん少ないものが、相手の対戦ポケモンより少ない）なら、突風を選ぶ（v0.22 の選び方の前に考える。突風のないデッキでは何もしないので、`computer` の結果は v0.22 と同じ）。その番のあとの操作で、手に入れた突風を使う。
- エネルギー回収: その番のほかの操作が終わったとき、1 番に 1 回だけ考え、このカードを除く手札が 1 枚以上・自分のトラッシュに基本エネルギーカードがあり、その番にまだエネルギーをつけていなくて手札に基本エネルギーカードがないときに使う。トラッシュする 1 枚はパソコン通信と同じ決まった順、手に入れるのはバトル場・育てる系統のベンチのポケモンのワザに足りないタイプを先に、選べるだけ（0 枚は選ばない。ER9）。トラッシュに基本エネルギーカードがなければ使わない（ER10）。
- `mixed`・`retrieval` では、決定のたびに、決定するプレイヤー・番のプレイヤー・使用中のカードがその決定のトレーナーの使用と同じか、MAIN にもどったら使用中のカードが残っていないかを数え（`check_…`）、突風・パソコン通信・エネルギー回収を使ってからトラッシュするまでのログに、ほかのトレーナーの使用・その実装が出さないイベント・持ち主の違うイベントがないかを確かめます（`trainer_sequence_problems`）。

結果の数は [v0.23-verification.md](v0.23-verification.md) です。

## 7. kyuura への報告事項（kyuura にはコミット・プッシュしない）

1. エネルギー回収（PMCG1-076）の照合の記録（CC-）・最新の説明（LD-）がない（最新の説明は rule_history.json の ERR-ENERGY-RETRIEVAL の notes にある。`research_links.json` の `card_checks.engine_verified_without_kyuura_record` に挙げた）。p.257 の図版は第1弾の印刷ではない版の文面（「…基本エネルギーカードを最大2枚選び、手札に加えてよい。(ただし…)」）で、kyuura の写し（第1弾の印刷）とは違う（版の違いで、写しの誤りではない）。
2. ER9（選べるものがあるのに 0 枚を選べるか）・ER10（トラッシュに基本エネルギーカードがないときに使えるか）の論点がない（`stop_codes` の `not_in_kyuura`）。`UQ-ENERGY-CONVERSION-ZERO` は「「最大○枚」と書くほかのカードは、kyuura では調べていない」としており、エネルギー回収はそのようなカードの 1 つ。
3. P43 の p.257 のページの記録の要約に、「このカードを使うためにトラッシュしたカードは選べない」（最新の説明の「ただし…」・解説「「エネルギー回収」を使うときにトラッシュしたエネルギーカードは回収できない」）がない（ERR-ENERGY-RETRIEVAL の notes の最新の説明にはある）。

## 8. 次にカードを加えるときの注意

- トラッシュから手札に加えるトレーナー（ダウジングマシーン・超エネルギー回収など）は、`zones.return_discard_to_hand` と、そのカードのログのイベント（公開・非公開の項目）を使ってください。エネルギー回収の `retrieve_energy` は「基本エネルギーカード」・トラッシュしたカードを除く規定の監査をしているので、ほかのカードに流用しないでください。ダウジングマシーンは「相手プレイヤーに見せてから」の指示があります（p.260）。
- 「最大○枚」と書くほかのカードは、0 枚を選べるかを ER9・H4 と同じに決めないでください（カードごとに原典で確かめ、決まらなければ止める）。
- 特殊エネルギーのカードを加えるときは、エネルギー回収の選べるものに入らないこと（ER6）をそのカードのテストで確かめてください。
