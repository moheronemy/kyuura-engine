# オーキドはかせ（v0.19）: 照合済みの記録の再利用と実装

v0.19 で、トレーナーのオーキドはかせ（PMCG1-077。ポケモンカード第1弾）を対応にしました。`CLAUDE.md` の「照合済みの記録の再利用」（[verified-record-reuse.md](verified-record-reuse.md)）の手順を当てはめ、既存の記録で決まる規定は読み直さず、記録のなかったカードのページ（p.255）だけを原典で確かめました。

- 基準のルール: 「ポケットモンスターカードゲーム公式ルール 2000.02.14版」（『ポケモンカードオフィシャルブック2000』pp.306〜326 [P43]）
- カードの処理: 同じ本のカードのページの「最新の説明」（p.6「この本の使いかた」。[trainers-v0.2b.md](trainers-v0.2b.md) の前提と同じ）
- カードデータ: kyuura `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`（写しの元。変えていない）。研究の基準: kyuura `3f349085645f47d0649a6cacece3680caeae50bf`
- 分類（CONFIRMED・SUPPORTED・UNRESOLVED・CONFLICT）の意味は [trainers-v0.2b.md](trainers-v0.2b.md) 1 章と同じ

## 1. 既存の記録を探した結果（手順の 1〜5）

| 探した記録 | 結果 | 使い方 |
|---|---|---|
| kyuura `data/cards.json`（`ecb2d69`・`3f34908` で同じ） | PMCG1-077 オーキドはかせ。文面「自分の手札を全部すてて、新たに7枚のカードを自分の山札から引いて手札にする。」（なぞのばしょの転記。第1弾の印刷）。種類（`kinds`）なし | 登録の照合（`TrainerEntry.text_ja`）。処理の根拠にはしない |
| kyuura のサイドカー（LD-・CC-・CR-・UQ-） | このカードの記録はない | — |
| kyuura `data/rule_history.json` の P43 のページの記録 | p.255 の記録はない（近くのページは p.254・p.257） | — |
| kyuura `rule_history.json` の `card_lists.supporter`（`MIX-SUPPORTER-ERRATA`） | 2002年の公式大会で「サポーター適用カード」とされた 15 種に PMCG1-077 がある | **使わない**。2000.02.14 版のあとの規定（CLAUDE.md「後年の裁定も混ぜません」） |
| `kyuura_engine/data/card_verification.json` | このカードの記録はない | — |
| docs/trainers-v0.2b.md 2 章（トレーナー共通）・3 章（マサキ） | p.310 のトレーナーの使いかた（手順 1〜4・何枚でも・使いすて・使うための条件・使っている最中はほかのことをしない）、p.312 の効果で引くとき（山札の一番上から・足りなければ引けるだけ・0 枚でも負けではない・最後の 1 枚を引いても負けではない）、番の最初のドローとの違い（p.309・p.311・p.312）、引いたカードを見せなくてよい（p.312）。どれも 2026-10-12 に画像で照合した記録 | **再利用**（対象: 効果で引くトレーナー・使いすてのトレーナー。ルールの版は同じ） |
| `zones.return_discard_to_hand`（v0.12）の説明と、その根拠の記録 | トラッシュにはカードの順番がない（p.312） | **再利用** |
| docs/architecture-v0.2b.md 9 章 | 非公開の情報（引いたカード）と公開の情報（トラッシュ）のログの項目の方針 | **再利用**（実装上の方針） |

既存の記録で足りなかったもの（原典に戻る前に書いたこと）:

1. このカードの「最新の説明」の文面（印刷の文面と違うか。「すてる」がトラッシュか。トラッシュと引く順番が書かれているか）。
2. このカードに「使うための条件」（p.310）があるか。
3. 手札がこのカードだけのとき・手札にもう 1 枚あるときの扱いについて、カードのページ（解説）に記述があるか。
4. 図版の文面が kyuura の写しと同じか（写しの照合）。

一般の規定（トレーナーの使いかた・効果で引く・山札切れ）は、既存の記録で決まるので読み直していません。

## 2. 原典で確かめたこと（p.255 だけ。2026-10-15）

Internet Archive のスキャン [J38]（PDF 372 ページ、`PDF n = p.(n-2)`）の PDF 257 ページ（p.255）だけを画像にしました（ページ全体は 110dpi で位置を確かめ、見出し・図版・最新の説明・解説は 400dpi）。OCR の文字はページの位置を探すのに使っただけです。p.255 には突風・エネルギー・リムーブ・オーキドはかせがあり、照合したのはいちばん下のオーキドはかせです。

| 項目 | 内容 |
|---|---|
| 見出し・収録 | 「オーキドはかせ」、収録「ポケモンカード第1弾」だけ |
| 図版の文面 | 「自分の手札を全部すてて、新たに 7枚のカードを自分の山札から引 いて手札にする。」（kyuura の写しと同じ。図版が第1弾のどの刷かは確かめていない） |
| 最新の説明 | 「あなたの手札をすべてトラッシュする。その後、山札からカードを7枚引いて、手札にする。」 |
| 解説（処理に関わる記述） | 「もちろん手札が「オーキドはかせ」1枚になったときが最高の場合ですが……。」「手札を全部トラッシュして7枚とるのですから、7枚以上にはなりません。」「手札をトラッシュするために「オーキドはかせ」を使うという方法もあります。」「多く入れすぎると使いすぎて、山札切れになったり、必要なカードがすべてトラッシュに置かれたりしますからね。」 |
| 照合の記録 | `card_verification.json` の PMCG1-077（`status` は「不一致あり」: 最新の説明が kyuura の文面（印刷）と違う。誤りではなく版の違い。トランセルのかたまる（PMCG1-003）と同じ扱い） |

## 3. 規定（O1〜O13）

「再利用」は既存の記録で決まり、今回読み直していないもの。「p.255」は今回読んだもの。

| id | 事項 | 分類 | 根拠 | 実装 | テスト |
|---|---|---|---|---|---|
| O1 | 使っているこのカードは手札にない（トラッシュする手札に含まない） | CONFIRMED | 再利用: p.310 の手順 1「手札から出して」（trainers-v0.2b.md 2 章）。p.255 の解説「7枚以上にはなりません」「手札が「オーキドはかせ」1枚になったときが最高」とも合う | `engine._play_trainer` が手札から出して `trainer_in_use` に置いてから `resolve` を呼ぶ（既存） | `test_the_card_itself_is_not_part_of_the_discarded_hand` |
| O2 | 使い終わったらこのカードをトラッシュする | CONFIRMED（使いすて）・SUPPORTED（時点は効果のあと） | 再利用: p.310「使ったトレーナーカードは、トラッシュします」（trainers-v0.2b.md 2 章）。トラッシュにカードの順番はない（p.312）ので、時点で結果は変わらない | `engine._finish_trainer`（既存。`discard_trainer`） | 同上 |
| O3 | 手札をすべてトラッシュする（印刷の「すてて」） | CONFIRMED | p.255 の最新の説明「すべてトラッシュする」 | `zones.discard_hand`（ログ `discard_hand`） | `test_discards_the_rest_of_the_hand_then_draws_seven` |
| O4 | トラッシュしてから引く | CONFIRMED | p.255 の最新の説明「その後」。再利用: p.310 の手順 4（書いてある順にしたがう） | `DiscardHandAndDraw.resolve` | 同上（ログの順番） |
| O5 | 手札がこのカードだけでも使える（トラッシュは 0 枚） | CONFIRMED | p.255 の最新の説明に使うための条件がない。再利用: p.310（使うための条件を満たせないときだけ使えない）。p.255 の解説「手札が「オーキドはかせ」1枚になったときが最高の場合」 | `check_playable` で拒否しない（既定） | `test_hand_of_only_this_card` |
| O6 | 山札が 7 枚未満なら引けるだけ引く | CONFIRMED | 再利用: p.312「カードが足りないときは、引けるだけのカードを引いてください」（trainers-v0.2b.md 3 章） | `min(7, 山札の枚数)` を `zones.draw_cards` | `test_deck_smaller_than_seven_draws_what_it_can`・`test_deck_of_exactly_seven` |
| O7 | 山札が 0 枚でも使え、0 枚引く。負けではない | CONFIRMED | 再利用: p.312「山札にカードがなかったり…負けにはなりません」。O5 と同じく使うための条件はない | 同上 | `test_empty_deck_discards_the_hand_and_draws_nothing`・`test_empty_deck_and_no_other_cards` |
| O8 | 山札切れの負けは、番の最初に引けないときだけ | CONFIRMED | 再利用: p.309・p.311・p.312（trainers-v0.2b.md 3 章） | 既存の番の最初のドロー | `test_deck_out_happens_only_at_the_start_of_the_turn`・`NaturalGamesTest.test_deck_out_ends_games_only_at_the_start_of_a_turn` |
| O9 | 使っても番は続く（手札からつける回数などは変えない） | CONFIRMED | 再利用: p.310（トレーナーは自分の番に使い、すませたら番の続き） | `_finish_trainer` が `Phase.MAIN` にもどす（既存） | `test_turn_continues_and_can_be_used_again_in_the_same_turn` |
| O10 | 同じ番に何枚でも使える（引いたオーキドはかせも使える） | CONFIRMED | 再利用: p.310「1回の自分の番で何枚でも」 | 回数を数えない（既存） | 同上 |
| O11 | 手札にあるもう 1 枚のオーキドはかせはトラッシュする手札に含まれる | CONFIRMED（O1・O3 から） | 手札にあるので「手札をすべて」に含まれる | `zones.discard_hand` | `test_the_card_itself_is_not_part_of_the_discarded_hand` |
| O12 | 引いたカードは相手に見せなくてよい。トラッシュしたカードは公開 | CONFIRMED（引いたカード）・実装上の方針（ログの項目） | 再利用: p.312（引いたカード）、architecture-v0.2b.md 9 章（隠す情報は決まった項目だけ） | `draw` の `cards` だけが隠れた情報。`discard_hand` の項目は `player`・`cards`（全員に見える） | `test_log_fields` |
| O13 | 手札・トラッシュの並び（引いたカードは山札の上から順に手札の後ろ、トラッシュは手札の並び → このカード） | 実装上の仮定 | 再利用: 手札の並びにルール上の意味はない（trainers-v0.2b.md 3 章）・トラッシュに順番はない（p.312） | `zones.discard_hand`・`zones.draw_cards` | `test_discards_the_rest_of_the_hand_then_draws_seven` |

未解決（UNRESOLVED）の規定はありません。止める処理（`UNRESOLVED_…`）も加えていません（停止コードは 18 件、未解決の裁定は 24 件のまま）。

扱わないこと:

- 2002年の「サポーター適用カード」の規定（kyuura `MIX-SUPPORTER-ERRATA`）。2000.02.14 版のあとの規定なので、1 番に 1 枚などの制限は入れていません。
- 手札・トラッシュを参照する未実装のカード（解説の例「マチスのピカチュウ」の「たいでん」など）との組み合わせ。そのカードを加えるときに、このカードでトラッシュしたカードの扱いを確かめます。
- 見る人ごとのログ（公開のログ）は v0.2b から未実装のままです（architecture-v0.2b.md 9 章）。

## 4. 実装

| 変更 | 内容 |
|---|---|
| `kyuura_engine/zones.py` | `discard_hand(state, player)`: 手札をすべて、同じ uid のまま手札の並びの順にトラッシュに置き、ログ `discard_hand`（`player`・`cards`）を残す。ゾーンの間でカードを動かす共通の関数（`draw_cards`・`return_discard_to_hand` と同じ場所） |
| `kyuura_engine/effects.py` | `DiscardHandAndDraw(count)`（`TrainerEffect`。`implementation_id` は `discard_hand_and_draw`）: `discard_hand` → `draw_cards(min(count, 山札の枚数))`。乱数を使わず、決定を出さない。登録 `"PMCG1-077": TrainerEntry(DiscardHandAndDraw(count=7), …, "P43 p.255")` |
| `kyuura_engine/cards.py`・`scripts/extract_kyuura_cards.py` | 写しの組 `pool_v0_19`（PMCG1-077）。写しは `python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura` で作り直した（元のコミット `ecb2d69` は同じ。`--check` で一致） |
| `kyuura_engine/data/card_verification.json` | PMCG1-077 の照合の記録（p.255・2026-10-15） |
| `kyuura_engine/data/research_links.json`・`scripts/check_research_links.py` | `card_checks.engine_verified_without_kyuura_record` に PMCG1-077（kyuura に記録がない。報告事項）。kyuura に記録ができたら一覧を直すよう、検査を加えた |
| `tests/log_audit.py` | ログの `discard_hand` を手札・トラッシュの組み立て直しに加え、トラッシュしたカードが組み立てた手札と同じことを確かめる |

変えていないもの: `engine.py`・`kyuura_engine/resolution/`（カード id での分岐を加えていない。`RegistrationTest.test_no_card_specific_branch_in_the_engine`）、公開の API（コマンド・関数の呼び方）、状態の型、書き出しの形式（形式 9 のまま。`trainer_in_use` は形式 3 から）、効果の登録表の id（`kyuura-engine-0.13`。v0.17・v0.18 と同じく変えていない）、固定した参照データ。ログには新しいイベント `discard_hand` を加えました（既存のイベントの形は変えていない）。

## 5. kyuura への報告事項

kyuura は変更していません（このリポジトリの作業で kyuura にコミットしない）。次は kyuura 側で記録する事項です。

| 事項 | 内容 |
|---|---|
| 照合の記録（CC-）がない | PMCG1-077 の照合（p.255・2026-10-15・400dpi）は `card_verification.json` にある。kyuura の取り込み（`import_provenance`）の形式で取り込める（[verified-record-reuse.md](verified-record-reuse.md) 3 章と同じ手順） |
| 最新の説明の記録がない | 最新の説明「あなたの手札をすべてトラッシュする。その後、山札からカードを7枚引いて、手札にする。」は印刷の文面と違う。kyuura のサイドカーにはトレーナーの最新の説明の形式がない（[verified-record-reuse.md](verified-record-reuse.md) 5 章の「トレーナーの最新の説明」と同じ不足） |
| P43 のページの記録がない | `rule_history.json` の P43 に p.255 の記録がない |

## 6. コードとテストの対応

| 規定・判断 | コード | テスト |
|---|---|---|
| 登録・照合の記録・写しの組 | `effects.DEFAULT_EFFECTS`・`card_verification.json`・`pool_v0_19` | tests/test_professor_oak_v0_19.py `RegistrationTest`、tests/test_trainers.py（登録の一覧・最新の説明の照合）、tests/test_cards.py（写しの組） |
| O1〜O13 | `effects.DiscardHandAndDraw`・`zones.discard_hand`・既存の `engine._play_trainer`・`_finish_trainer` | tests/test_professor_oak_v0_19.py `ProfessorOakTest`（盤面を直接作る） |
| 拒否で状態が変わらない（相手の番・別のトレーナーの決定を待つ間） | 既存の共通の確認 | `test_rejections_change_nothing` |
| 正式な対戦開始から勝敗まで | — | `NaturalGamesTest`（41 局）・`MixedDeckGamesTest`（16 局） |
| ログの監査 | `tests/log_audit.py` の `discard_hand` | `NaturalGamesTest.test_invariants_logs_and_serialization`・`MixedDeckGamesTest` |
| 研究の対応表 | `research_links.json`・`scripts/check_research_links.py` | tests/test_research_links_v0_18e.py |
