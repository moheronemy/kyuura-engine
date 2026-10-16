# CLAUDE.md

このリポジトリで作業するときの約束です。

## 役割

- **kyuura**（https://github.com/moheronemy/kyuura）が歴史資料の正本です。カードデータ、ルールの版、公式エラッタ、出典と確度はそこにあります。
- **kyuura-engine**（このリポジトリ）は対戦処理の実装です。資料の正本ではありません。
- kyuura のデータを勝手に変更しないでください（このリポジトリの作業で kyuura にコミット・プッシュしない）。資料の誤りや食い違いを見つけたら、報告事項として記録し（docs/data-provenance.md、docs/rules-2000-02-14.md の「kyuura の記録との違い」）、kyuura 側の作業として扱います。

## ブランチと取り込み（`main`。2026-10-15 から）

- **`main` が統合ブランチです**（既定のブランチにする）。2026-10-15 に、v0.26 までを取り込んだコミット `7c788c0`（PR #2 のマージ。中身は v0.26 の最終コミット `fcf8987` と同じ）から作りました。
- 作業（版・カード・道具・文書の直し）は、`main` から作った作業ブランチで行います。終わったら作業ブランチから `main` へプルリクを出し、マージします。次の作業のブランチは、マージしたあとの `main` から作ります。
- プルリクの取り込み先（base）は、作るたびに `main` であることを確かめてください。前の版のブランチを取り込み先にしないでください（2026-10-15 の PR #2 は、取り込み先が既定のブランチだった `claude/v0.19-professor-oak` になり、v0.19 の名前のブランチに v0.20〜v0.26 が入った）。
- `main` に直接コミット・プッシュしないでください。`main` を含め、プッシュ済みのブランチの履歴を書き換えない（強制プッシュ・リベース・巻き戻しをしない）でください。プルリクの作成・マージは、利用者が頼んだときだけ行います。
- 版ごとのブランチ（`claude/v0.6-rain-dance`〜`claude/v0.26-preset-decks-v2`）は記録として残し、消したり書き換えたりしません。名前と中身の合わないブランチもそのままにします。
  - `claude/v0.19-professor-oak` は PR #2 で v0.26 までを含む。
  - `claude/cool-ptolemy-5vtgsg` は PR #1 で v0.10 を取り込み、2026-10-15 に `main` を取り込んだ。
- 固定した前の版と比べるとき（`tools/engine_lockstep.py` など）は、ブランチの名前ではなくコミット（`8facf3a`・`aa551ab`・`548dd65` など）で指します。kyuura の研究の基準・カードの写しの元も、下のとおりコミットで固定しています（kyuura のブランチの運用とは別）。

## 研究資料の参照コミットを固定する

- 参照する kyuura のコミットは `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691` です（scripts/extract_kyuura_cards.py の `KYUURA_COMMIT`）。
- 研究の基準（裁定・論点・最新の説明・照合の記録を照らすコミット）は `3f349085645f47d0649a6cacece3680caeae50bf` です（ブランチ `claude/cool-ptolemy-5vtgsg`。kyuura の既定のブランチにも、v0.25 までの記録の取り込み（kyuura の PR #1）で含まれた。`kyuura_engine/data/research_links.json` の `research_commit`）。v0.18a〜v0.18 は `adf97107ee0d9755cd7ddedae298ecb02914128e`（ブランチ `claude/engine-findings-through-v0.17`。docs/research-alignment-v0.18a.md）で、2026-10-15 に、エンジンの照合の記録を kyuura に取り込んだあとのコミットへ、差分を確かめてから上げました（docs/verified-record-reuse.md）。写しのコミットと分けているのは、状態がカードデータの元のコミットを持ち、上げると固定した参照データが変わるからです。エンジンが使う項目が同じことは `scripts/check_research_links.py`（v0.18e）が確かめます。
- カードデータの写し `kyuura_engine/data/kyuura_cards.json` は手で編集せず、`python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura` で作り直します。
- 参照するコミットを上げるときは、写しを作り直し、変わった項目に対応するテストと docs を見直します。

## カードデータの信頼と照合の方針（2026-10-15〜）

カードの実装を速めるための方針です。docs/card-data-policy.md（手順・記録の形式・検査）と kyuura の docs/engine-readiness.md 12 章に同じ方針を書きました。この節と食い違う古い指示（下の「照合済みの記録の再利用」の原典に戻る手順・各版の文書の「画像で読み直した」など）より、この節が優先します。

1. **kyuura の `data/cards.json`・`cards.csv` を、カードを実装するための信頼できる基本データとして扱います。** カードごとの原典照合の記録（kyuura の CC-）がないことだけを理由に、実装を止めたり原典を開いたりしないでください。JSON と CSV が一致することは、独立した原典照合とは数えません（同じデータの別の形式）。
2. **カード情報の外部照合には pcg-search.com を使います。** カード名だけでなく、収録・カード番号（サイトの一覧の番号 `list_number`）で対象の版を決めます。既存の照合結果は再利用し、同じカードを毎回調べ直さないでください。kyuura の日本語の文面が pcg-search.com の転記のカード（写しの `ja_text_source`。今はプリン PMCG2-035）は、日本語の欄を同じサイトと照らしても独立した照合になりません。
3. **公式ガイドブック（『オフィシャルブック2000』。通称 Silver Bible）のキャプチャ・OCR・画像の読み直しは、通常のカード実装の手順に入れません。** 情報の不足や矛盾があっても、自動的にガイドブックの調査に進まないでください（読み直すのは利用者が明示的に依頼したときだけ）。
4. **すでに記録されている最新の説明・エラッタ・裁定は、引き続き使います。** 印刷の文面と、処理に適用する説明（`play_text_ja`）を区別します。pcg-search.com のカードの画像だけを根拠に、既存の裁定や最新の説明を取り消さないでください。
5. **pcg-search.com に対象の版がない、またはアクセスできない場合は、その事実を記録します。** 外部照合ができなかったことだけでは、kyuura のデータによる実装を妨げません。挙動に影響する具体的な矛盾があるカードは、論点を記録してそのカードだけを保留にし、ほかの作業を続けます。

- 記録は 3 種類を分けます: kyuura データの採用（`kyuura_engine/data/card_sources.json` の `basis: kyuura_data`。採用したデータのコミット = `KYUURA_COMMIT`・カード id・記録した日・処理に使う文面の根拠 `play_text`・研究の基準のコミットでそのカードを指す kyuura の記録の id `kyuura_records`・論点・`adopted`／`on_hold`）、pcg-search.com との照合（同じファイルの `external_checks`。URL・確認日・対象の版（収録・一覧の番号）・照らしたコミット・結果（`match`・`differences`・`edition_not_listed`・`inaccessible`）・照合した欄・違い）、過去の原典照合（`card_verification.json`。2026-10-14 までの記録。履歴として残し、書き換えない）。
- 処理に使う文面は、kyuura の最新の説明（LD-）があればそれ（登録の `source` は LD- の id）、エラッタ（ERR-・TXT-・RUL-）があればそれ（`source` はその id）、どちらもなければ kyuura の印刷の文面（`play_text_ja` は写しの文面と同じ、`source` は `kyuura data/cards.json`、研究の対応表の `adopted_printed_text`）。裁定（CR-）にはしたがい、論点（UQ-）に当たる場合は今までどおり止めます。
- 読んでいない原典を確かめたことにする記録を作らないでください。採用の記録・外部照合に、ガイドブックの項目（`page`・`pdf_page`・`latest_description_ja`・`card_image_text_ja` など）を書かないでください（`scripts/check_card_sources.py` が拒否する）。採用したカードを `card_verification.json` に加えないでください。
- 各版の節の「原典で確かめる」「原典と照合する」（新しい処理・相互作用を加えるとき）は、既存の記録（kyuura の裁定・規定・最新の説明・エラッタの記録、このリポジトリの裁定の表と過去の原典照合）で確かめることと読みます。記録で決まらなければ、ガイドブックを読みに行かず、今までどおり `UNRESOLVED_…` で止めるか、そのカードを保留にします。
- 登録したカードは、過去の原典照合の記録か採用の記録（`adopted`）のちょうど一方を持ちます。保留（`on_hold`）のカードは登録しません。外部照合で見つけた違いで、kyuura のデータ・写しを直さないでください（kyuura への報告事項）。
- 検査: `python3 scripts/check_card_sources.py`（記録の形・登録との対応・外部照合の形）、`python3 scripts/check_research_links.py --kyuura ../kyuura`（研究の基準のコミットの kyuura の記録の見落とし・LD- の無視・データの誤り）、tests/test_card_sources.py。実装の整合性の検査（登録の名前・文面が写しと同じ、効果の型の `check` など）は今までどおりです。

## 照合済みの記録の再利用（2026-10-15）

既存の照合の記録を、同じ範囲で何度も調べ直さないための手順です。kyuura の docs/engine-readiness.md 10 章と同じ手順です（このリポジトリでの記録の場所・2026-10-15 の取り込みの結果は docs/verified-record-reuse.md）。2026-10-15 からのカードデータの方針（上の節）で、手順の 4・5（原典に戻る）はカードの実装の手順から外しました。

1. **原典を開く前に、既存の記録を探します。** このリポジトリの `kyuura_engine/data/card_verification.json`（カードごとの照合の記録）・関連する裁定の文書（docs の各版の裁定の表・docs/rules-2000-02-14.md）・docs/data-provenance.md と、kyuura のサイドカー（`data/sidecar/` の最新の説明 LD-・照合 CC-・裁定 CR-・論点 UQ-。id は `research_links.json` で引ける）・ページごとの記録（kyuura `data/rule_history.json` の P43 の `refs`）。
2. **対象とルールの版が一致し、必要な項目の照合の結果と出典が確かめられれば、再利用します。** 一致を見るのは、カード id・ワザ（特殊能力）の位置と名前・採用するルールの版（2000.02.14 版。最新の説明は『オフィシャルブック2000』）。出典は、資料・ページ・確認日・確認の方法・照合した項目です。
3. **新しいセッションになった、確認日が古い、実装する人が変わった、だけを理由に原典を読み直さないでください。**
4. **既存の記録で判断できない部分があっても、ガイドブックの調査に自動で進みません。** カードデータは kyuura のデータを使い（上の節）、記録のあとで変わったデータ（写しの文面と記録の文面の違い。tests/test_effects.py・tests/test_trainers.py・scripts/check_research_links.py が見つける）・記録どうしの矛盾・記録が扱っていない新しい相互作用のうち、挙動に影響する具体的な矛盾は、論点を記録してそのカードだけを保留にします。原典の規定で決められない処理は、今までどおり `UNRESOLVED_…` で止めます。
5. **利用者がガイドブックの調査を明示的に依頼したときは、** 読み直す前に、既存の記録で何が足りないかを具体的に書きます（記録の場所と id・足りない欄や問い・記録では決まらない理由）。読み直したら、読んだ範囲だけを記録します（2026-10-14 までの `card_verification.json` の形。確認日・方法・ページ・照合した項目）。

- 再利用は、記録された確認の範囲（照合した項目・`scope`・最新の説明・画像の確認）に限ります。照合していない欄を「同じ」と読みかえないでください。
- テストが通ったことだけを、原典と照合した証拠にしないでください。
- 再利用で SUPPORTED・UNRESOLVED などの分類を変えないでください（分類を変えるのは、新しく読んだ資料の根拠があるときだけ。根拠の書き方は下の「ルールの扱い」の `UNRESOLVED_…` の分類を変えるときの約束）。
- kyuura の記録は、kyuura が原典を読んだもの（`by: kyuura`）と、このリポジトリの記録を取り込んだもの（`import_provenance`。kyuura は画像を読み直していない）を区別します。取り込んだ記録を、エンジンの記録とは別に原典を確かめた証拠として数えないでください（もとはこのリポジトリの記録）。
- 印刷の文面（kyuura の `data/cards.json`・写し）・最新の説明（`play_text_ja`・LD-）・裁定（エンジンの裁定の表・CR-）・実装上の仮定を混ぜないでください。
- 各版の文書の「画像で読み直した」「p.N と照合した」は、その版の作業の記録（履歴）です。今のカードの実装の手順ではありません。

## ルールの扱い

- 基準のルールは「ポケットモンスターカードゲーム公式ルール 2000.02.14版」（『ポケモンカードオフィシャルブック2000』pp.306〜326、kyuura の `NEO-2000-OFFICIAL-RULES`）です。
- **現代のルールで補完しないでください。** 当時の第4版の冊子や後年の裁定も混ぜません。
- 原典で確かめた規定と、実装の都合で決めたこと（実装上の仮定）を区別して書きます（docs/rules-2000-02-14.md の 5章・6章）。
- 原文で決められない処理は、推測で「公式ルール」として実装しません。`UnsupportedError` や `Phase.HALTED` で明示的に止め、docs/implementation-status.md の「裁定が未解決」に書きます。
- 未実装のカード効果を、効果がないものとして処理しないでください。対応していないカード・ワザ・操作は、分類（cards.py）・デッキの検査（deck.py）・`UnsupportedError` で明示的に拒否します。
- ワザを使えるのは、効果の登録表（kyuura_engine/effects.py の `DEFAULT_EFFECTS`）に（カード id, ワザの位置）で実装が登録されているときだけです（v0.2a）。説明文が空なことを実装がある証拠にしないでください。登録するカードは、登録の根拠の記録をちょうど 1 つ持ちます: 2026-10-14 までに登録したカードは『オフィシャルブック2000』と照合した記録（`kyuura_engine/data/card_verification.json`。履歴）、2026-10-15 からは kyuura データの採用の記録（`kyuura_engine/data/card_sources.json`。上の「カードデータの信頼と照合の方針」）。tests/test_effects.py・scripts/check_card_sources.py が確かめます。
- トレーナーも同じです（v0.2b）。カード id で `TrainerEntry` を登録し、kyuura の写しの名前・文面（照合用）と、実装がしたがう文面（`play_text_ja`）・出典を書きます。実装がしたがう文面は、過去の原典照合で登録したトレーナーは『オフィシャルブック2000』の「最新の説明」（照合の記録の `latest_description_ja`）、採用の記録で登録するトレーナーは kyuura の最新の説明・エラッタか、それがなければ kyuura の印刷の文面です（tests/test_trainers.py・scripts/check_card_sources.py が確かめる）。英語版の文面や現代のカードの文面で日本語版の処理を決めないでください。
- 説明文のあるワザ（v0.2d から）は、`AttackEntry` に kyuura の写しの説明文（`text_ja`。照合用）と、実装がしたがう文面（`play_text_ja`）・出典（`source`）を書きます。過去の原典照合で登録したワザは照合の記録の `latest_description_ja` と、採用の記録で登録するワザは採用の記録の `play_text` の根拠（kyuura の印刷の文面・LD-・エラッタ）と合わせます（tests/test_effects.py `test_attacks_with_text_follow_the_verified_latest_description`・scripts/check_card_sources.py が確かめる）。登録した説明文とデータの説明文が違えば、そのワザは使えません。
- カード効果の中で原典で決められない場合は、成功を仮定せず `UnsupportedError`（コードは `UNRESOLVED_…`）で止めます。使えるかどうかなら `TrainerEffect.check_playable`、決定の選択なら `push_trainer_decision` の `unresolved_choices` を使います。テストは「止まること・状態が変わらないこと」を確かめ、仮定に基づく成功のテストは書きません。決めた根拠と未解決の事項は docs/trainers-v0.2b.md のように、原典の記述・分類（CONFIRMED・SUPPORTED・UNRESOLVED・CONFLICT）・コード・テストを対応づけて書きます。

## 状態の作り（v0.2a）

- プレイヤーの選択を待つ処理は、`kyuura_engine/decisions.py` の `push_decision` で保留中の決定（`GameState.decision`）を作り、engine.py の再開先（`_RESUMERS`。v0.16b から `engine._answer_decision` が、再開先が `resolution.RESUMES` なら解決の基盤、`trainer` なら `_resume_trainer` に振り分ける）で続けます。段階や保留中のリストを別に増やさないでください。決定は一度に 1 つです。
- 場のポケモンは `pokemon_id`（場に出たときに付ける番号。進化しても同じ、場を離れたら無効、使い回さない）で指します。カードの uid はカードの番号で、場のポケモンの番号ではありません。v0.1 のコマンド（`PromoteActive` など）はカードの uid のまま受け付けます。v0.4a の `EvolvePokemon.target` は場のポケモンの番号です。
- 状態の書き出しは `state_to_dict(state)` が v0.1 の形（`format_version` 1）、`state_to_dict(state, format_version=2)` が v0.2a の項目を加えた形です。既定の形を変えると固定値と互換性のテストが変わります。
- tests/fixtures/v0_1_reference.json は v0.1 の結果の参照データです。互換性を確かめるためのものなので、scripts/make_compat_fixture.py で作り直さないでください（作り直すと v0.1 との比較ではなくなります）。v0.1 で未対応だった操作を対応にしたら、参照データは変えずに tests/test_compat_v0_1.py の `NOW_SUPPORTED` に加え、エラーコードが変わる件数と内訳を docs に書きます（v0.2b の `play_trainer`）。
- トレーナーを使っている最中（決定を待つ間）のカードは `GameState.trainer_in_use` にあります（カードの保存則の対象）。この状態は形式 1・2 では書き出せないので、トレーナーのある対戦のテストは形式 3 以上で比べます。
- ポケモンについて場に残るトレーナー（v0.2c。プラスパワーなど）は `PokemonInPlay.trainers`（`AttachedTrainer`）にあります。使用中（`trainer_in_use`）とは別の領域です。実装は `TrainerEffect.stays_in_play = True` にし、有効期限の長さを `discard_turn_offset`（使った番からいくつ後の番の終わりにトラッシュするか。プラスパワー 0、ディフェンダー 1 = 次の相手の番。v0.2e）で宣言して、`zones.attach_trainer(..., discard_at_end_of_turn=effect.attachment_discard_turn(state))` でつけます。有効期限（`discard_at_end_of_turn`）の番の終わりにエンジンがトラッシュし、きぜつしたらポケモンといっしょにトラッシュします。勝敗が決まった番は番の終わりが来ないので、何もしません。形式 1〜3 は、ついているトレーナーを書き出せない（`ValueError`）ので、形式 4 で比べます。番は先攻から 1 つずつ交互に進むこと（番のプレイヤー = `engine.turn_owner(state, turn_number)`）を不変条件で確かめているので、「次の相手の番」は番の番号 + 1 で表します。番を飛ばす・続ける効果を加えるときは、この前提と有効期限の表し方を見直してください。
- ダメージを変えるカードの効果は、`damage.DamageModifier`（段階と加える数）で p.321 の段階に渡します。最終ダメージに直接足さないでください。加算でない効果を加えるときは、同じ段階の順番を決めるプレイヤー（`DAMAGE_STEP_CHOOSER`）に決定で選ばせます。
- コイン（v0.2d）は `kyuura_engine/coins.py` の `flip_coins` だけで投げます（1 枚 1 回 `GameState.rng.getrandbits(1)`、1 なら「おもて」。1 枚ごとにログ `coin_flip`）。コインの結果をコマンドや引数で指定する口を作らないでください。テストで結果を決めるときは、tests/helpers.py の `with_coin_results`（状態の乱数を差し替える）を使います。コインを投げる効果は、投げる前に使えるかどうか・原典で決められない場合を確かめ終えておきます。コインの使い方（回数・順番）を変えると、tests/test_coins.py・tests/test_coin_games.py の固定値が変わります。
- ワザのダメージ（v0.2f）は `effects.deal_attack_damage(state, use, target, base)` で与えます（v0.4d から結果 `DamageResult` を返す）。発生源はいつもワザを使うポケモンで、受けるポケモンは `target`（`OPPONENT_ACTIVE`・`SELF`。p.320 のダメージの (1)・(3)）で決めます。ポケモンの `damage` に最終ダメージを直接足さないでください。控えポケモンへのダメージ（(2)・(4)）を加えるときは、種類を足す前に、受けるポケモンの選び方と計算（弱点・抵抗力・プラスパワーなどの扱い。p.257）を原典で確かめます。自分へのダメージの弱点・抵抗力は、ワザを使うポケモンのタイプと自分の弱点・抵抗力で計算します（v0.3d。p.90 の解説。SUPPORTED。v0.2f〜v0.3c の `self_damage_problem` は外した）。こんらんの 20（`calculate_confusion_damage`）とは別の計算のままにしてください（docs/unresolved-rulings-v0.3d.md 6 章）。
- きぜつは、ワザの要素をすべて処理したあとで `engine._finish_attack` がまとめて判定します（p.309・p.324）。ワザの効果の中でポケモンをトラッシュしないでください。サイドはきぜつしたポケモンの相手側のプレイヤーが取り（p.323）、勝ち負けはすべてのサイドを取ってから p.311 の表で判定します。同時のきぜつで両方がサイドを取る順番は、番のプレイヤーが選ぶ（p.325）ところを、結果が変わらないので番のプレイヤーからに正規化しています。サイドに関わるカードを加えるときはこの前提を見直してください（docs/simultaneous-ko-v0.2f.md 5 章）。バトル場に出す順番（番でないプレイヤーが先。pp.323〜324）はルールで決まった順番で、選択ではありません。
- 特殊状態（v0.3a〜v0.3c）は場のポケモンの `PokemonInPlay.conditions`（`SpecialConditions`。frozen なので `dataclasses.replace` で置きかえる）に持ちます。カードの uid や `GameState` の別の一覧で持たないでください。付けるのは `conditions.poison`・`put_to_sleep`・`paralyze`・`confuse`（v0.3c）、消すのは `conditions.clear_special_conditions`（にげる・ポケモンいれかえでベンチに戻ったとき。p.311・p.322。進化したとき（`EVOLVE`。v0.4a。p.310・p.322））・`recover_from_sleep`・`recover_from_paralysis`（ポケモンチェック）。特殊状態になるのはバトル場のポケモンだけで、ベンチのポケモンに特殊状態があれば不変条件の違反です。どくはほかの特殊状態と重複し（`SpecialConditions.poison`）、ねむり・マヒ・こんらんはたがいに重複しない（p.322）ので 1 つの項目（`SpecialConditions.exclusive`。`Asleep`・`Paralyzed`・`Confused`）に持ちます。「特殊状態は 1 つだけ」という形にしないでください。ねむり・マヒ・こんらんが置きかわる・回復するときに、どくを消さないでください。形式 1〜4 は特殊状態を書き出せない（`ValueError`）ので、形式 5 以上で比べます。
- ポケモンチェック（v0.3a）は、番の終わり（`_end_turn`）のあとに `engine._pokemon_check` が 1 回だけ行い、最後（v0.3b からは 3・4 の `_pokemon_check_sleep_and_paralysis` の最後）に次の番を始めます（`_begin_turn` をほかの場所から呼ばない）。段階（`Phase`）は増やしていません。ポケモンチェックの中のきぜつは、ワザのあとと同じ `_after_knockouts` で処理し、決定の `context` の `"then"`（`engine.NEXT_TURN`）で「交代のあとはポケモンチェックの残り（3・4）をして次の番を始める」ことを表します（ワザのあとの決定には書かない）。どくのダメージはワザによるダメージではない（p.321）ので、`deal_attack_damage` を通さず、ログも `poison_damage` です。両方のプレイヤーのポケモンがポケモンチェックのどくできぜつする場合は原典で決められないので、ダメージを与える前に `Phase.HALTED`（`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`）で止めます。番の進行（番と番のあいだに `turn_end` → `pokemon_check` が 1 回ずつ）は不変条件（`_progress_problems`）で確かめています。
- ポケモンチェックの 3（ねむり）・4（マヒ）（v0.3b）は `engine._pokemon_check_sleep_and_paralysis` が行い、最後に `_begin_turn` を呼びます。呼ぶのは、2 できぜつがないときと、2 のきぜつの決定（`then` が `engine.NEXT_TURN`）が終わったときの 2 か所だけです。2 のきぜつ・サイド・判定・交代は 3 より先です（HP 以上のダメージできぜつしてトラッシュ・すぐに出す。p.311・p.313・p.323。きぜつしたポケモンのねむりのコインは投げない）。`then` の値は v0.3a と同じ `"next_turn"`（書き出しの形を変えないため）で、交代のあとは 3・4 → 次の番です。3・4 で決定を出す効果（ポケモンチェックの 1 など）を加えるときは、続きの持ち方を見直してください（docs/pokemon-check-v0.3b.md 3 章・docs/architecture-v0.3b.md 6 章）。
- ねむりのコインは持ち主が `flip_coins(state, owner, 1, source="pokemon_check", effect="sleep", …)` で投げ、結果を `sleep_check` に残します。両方の対戦ポケモンがねむりなら、投げる順番が原典で決まらず乱数の割り当てが変わるので、コインの前に `Phase.HALTED`（`UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`）で止めます。番のプレイヤーから投げるような正規化をしないでください。
- マヒ（v0.3b）は、マヒ状態になった番（`Paralyzed.turn`）を持ち、回復する番は `conditions.paralysis_recovery_turn`（`turn` より後の、持ち主の最初の番。`state.turn_owner`）で求めます。`turn + 1` で決めないでください（持ち主の番にマヒ状態になったら 2 つ後）。期限の過ぎたマヒが残らないことは不変条件で確かめています。マヒの再付与で回復する番が変わる場合は原典で決められないので、コインの前に `conditions.paralysis_problem` で確かめ、`UnsupportedError`（`UNRESOLVED_REPARALYSIS_RECOVERY_TURN`）にします。
- ねむり・マヒのポケモンのワザ・にげるは、処理の前に `IllegalActionError`（`POKEMON_ASLEEP`・`POKEMON_PARALYZED`）で拒否します（p.309 の手順 1 はエネルギーの確認より前。p.311）。ポケモンいれかえは制限しません（p.325）。ワザ・にげるを制限する状態を加えるときは `engine._require_not_asleep_or_paralyzed` と同じ場所で確かめます。
- こんらん（v0.3c）は、ワザ・にげるの宣言を拒否しません（p.309・p.311 の宣言できない状態はねむり・マヒだけ）。宣言が正しく成り立ったあとで、持ち主が `engine._confusion_check`（`flip_coins` の `source="confusion"`、ログ `confusion_check`）でコインを投げます。ワザ（p.309 の手順 5）は「うら」なら効果の `resolve` を呼ばずに `engine._confusion_damage`（`damage.calculate_confusion_damage`。20、弱点・抵抗力だけ。ログ `confusion_damage`）→ `_finish_attack`。にげる（p.311 の手順 3）はエネルギーをトラッシュしてから投げ、「うら」なら入れ替えずに `retreat_failed`（番は続く）。どちらも不正なコマンド（`IllegalActionError`）にしないでください（コイン・エネルギー・20 ダメージ・番の終わりは状態に残る）。こんらんの 20 を `deal_attack_damage`（ワザによるダメージ）に通したり、v0.2f の自分へのダメージの規定と混ぜたりしないでください（docs/confusion-attacks-v0.3c.md 5 章）。
- ワザの効果の実装で、ワザを使う前に分かる「原典で決められない場合」は `AttackEffect.problem` で返します（v0.3c。エンジンがこんらんのコインの前に聞く。v0.3d の対応カードの実装はどれも既定の None）。受け付けるか・拒否のコードがコインの結果で変わらないことを tests/test_effect_preflight_v0_3d.py の `CoinIndependenceTest` で確かめているので、ワザの実装を加えたら `ATTACKS` にも加えます（docs/effect-preflight-v0.3d.md）。こんらんの 20 にプラスパワー・ディフェンダーを計算するかは決められないので、ワザを使うこんらん状態のポケモンにダメージを変えるカードがついていれば、コインの前に `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` で止めます（`engine._confusion_damage_problem`）。
- こんらんで「にげる」に失敗した記録（v0.3c）は、場のポケモンの `PokemonInPlay.retreat_failed_turn`（失敗した番の番号）に持ち、`_end_turn` で消します。プレイヤー単位の「この番はもうにげられない」フラグや、`GameState` の別の一覧にしないでください（p.311 の制限はポケモンごと）。こんらんのまま再宣言したら `RETREAT_ALREADY_FAILED`、失敗のあとこんらんが消えて同じ番にバトル場に戻ったポケモンの宣言は原典で決められないので `UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED`（どちらもエネルギー・コインの前）。形式 1〜5 はこの記録を書き出せない（`ValueError`）ので、形式 6 で比べます。記録は、今の番のログの `retreat_failed`（同じ `pokemon_id`）と対応することを不変条件で確かめています（v0.3d）。テストで記録を置くときは、`build_test_state` の `"retreat_failed_turn"` か、対応するログといっしょに置いてください。進化したら記録を消します（v0.4a。ログ `retreat_failure_cleared`。SUPPORTED。docs/evolution-rules-v0.4a.md の R1）。特殊状態を消す処理（`clear_special_conditions`）には含めず、進化の処理の中で別に消します。特殊状態を回復するトレーナーを加えるときは、この記録の扱いを見直してください。
- ダメージの目安の数字がないワザ（パラスの「キノコのほうし」）は、ダメージの要素がないワザとして実装します（`PutToSleep`。ダメージの計算も `damage` のログもない）。`DamageOnly` に 0 を渡す登録にしないでください（docs/sleep-paralysis-v0.3b.md 4 章）。
- ログのイベントに `turn` の項目を渡さないでください（`add_event` が `ValueError`。ログの `turn` はいつも今の番。マヒの番は `paralyzed_turn`）。
- ログは内部の完全な記録です（引いたカードなどの隠れた情報を含む）。イベントを加えるときは、隠す情報を決まった項目にだけ入れます（docs/architecture-v0.2b.md 9 章）。
- 進化（v0.4a）は、たねポケモン → 1 進化ポケモン、v0.4c から 1 進化ポケモン → 2 進化ポケモンも、同じ `EvolvePokemon(player, card, target)`（`engine._evolve_pokemon`）で扱います。退化・ベイビィ・進化に関わるカードの効果は未実装で、ベイビィのカードは分類（cards.py）で拒否します。2 進化のカードは段階では拒否せず、1 進化と同じカードごとの条件（進化元の名前・ワザの登録・ポケモンパワーの登録）で分類します（2 進化の段階だからといって一括で対応にしない）。v0.4c〜v0.4e は「ポケモンパワーなし」が条件で、フシギバナは未対応でした。v0.5 でポケモンパワーの登録表を加え、フシギバナのパワー（エナジートランス）とワザ（ソーラービーム）を登録したので、フシギバナは対応になりました（下の「ポケモンパワー（v0.5）」。v0.6 でカメックス、v0.7 でフーディンも対応にした。未対応のパワーを持つ 2 進化の例はリザードン PMCG1-021）。確かめる順番とコードは docs/evolution-rules-v0.4a.md 3 章と docs/stage2-evolution-v0.4c.md 3 章のとおりで、どれも状態を変える前に拒否します。名前は合うが段階が合わない組み合わせ（テスト専用のカードだけで起こる）は `EVOLUTION_STAGE_MISMATCH`（v0.4c）。
- 進化しているポケモンは、いちばん上のカードを `PokemonInPlay.card`、下に重なったカードを `PokemonInPlay.evolution_stack`（下から順。進化していなければ `()`）に持ちます。場のポケモンの番号（`pokemon_id`）は進化しても変えません（実装上の仮定）。p.310 の「別のポケモン」は、いちばん上のカード・`evolved_turn`（いまの姿に進化した番）・特殊状態と失敗の記録と持続する効果（v0.4b）を消すことで表します。進化の条件の「その番の最初から場に出ていた」は `played_turn`（場に出た番。対戦準備は 0。`_enter_play` だけで決める。にげる・交代では変えない）と `evolved_turn` で確かめます（`current_form_turn`）。HP・タイプ・弱点・抵抗力・にげる・ワザは、どの処理もいちばん上のカードの定義を使い、下のカードの定義を見ないでください。
- 進化ではダメージ・エネルギー・ついているトレーナー（`PokemonInPlay.trainers`。効果と有効期限も）を変えません（p.310。ついているトレーナーの効果が続くのは SUPPORTED。docs/evolution-rules-v0.4a.md の E8'）。進化で消える「持続する効果」（p.322・p.323）を持つワザを加えるときは、進化の処理で消します（ついているカードの効果とは分ける）。
- 進化したポケモンがきぜつしたら、`PokemonInPlay.cards()`（重なったカードすべて）をトラッシュします（p.313）。サイドは 1 匹につき 1 枚のままです。
- 進化したあとの HP が、のっているダメージ以下になる場合は原典で決められないので、状態を変える前に `UnsupportedError`（`UNRESOLVED_EVOLUTION_HP`）で止めます。進化の手順の中できぜつを判定しないでください。
- 重なりの形（3 枚まで、下から順の段階 たね → 1 進化 → 2 進化（`cards.EVOLUTION_STAGES`）、すべての隣り合う 2 枚で上のカードの「○○から進化」が下のカードの名前、進化した番の範囲、2 進化の前に 1 進化できる持ち主の番があること、進化した番の特殊状態はログ `evolve` のあとに付いたもの）は `engine._evolution_problems` の不変条件で確かめています。1 進化した番は状態に持たず（`evolved_turn` は最新の進化の番）、そのポケモンの番号のログ `evolve` が重なりの上の側の移り変わりと順番どおりに対応し、番が増えていき、最後の番が `evolved_turn` であることを `_evolution_log_problems` で確かめます（v0.4c。`new_game` からの対戦ではすべての移り変わりにログが要る）。1 進化した番を状態に加えなかった理由（進化の条件に要らない・形式 9 を避ける・ログで確かめられる）は docs/stage2-state-v0.4c.md 5 章。テストで進化したポケモンを置くときは、`build_test_state` の `"evolved_from"`（1 進化は下のたねポケモンのカード id、2 進化は下のカード id のリスト [たね, 1 進化]。v0.4c）・`"evolved_turn"`・`"played_turn"` を使ってください（作った重なりのログは置かないので、不変条件はあるログだけを確かめる）。
- 形式 1〜6 は進化しているポケモンを書き出せない（`ValueError`）ので、進化のある対戦は形式 7 で比べます。進化していない状態は形式 1〜6 で今までと同じに書き出します（`played_turn` はログから分かるので古い形式には入れない）。
- 2 進化（v0.4c）は、v0.4a の前提（docs/architecture-v0.4a.md 10 章・docs/architecture-v0.4b.md 14 章・docs/evolution-state-v0.4a.md）を見直して、重なりの長さを 1 から 2 までに広げました（いちばん下がたねポケモン・`EVOLVED_THIS_TURN` は変えていない。同じ番の 1 進化 → 2 進化もこれで拒否する）。2 進化ポケモンがきぜつしたら 3 枚すべてとついているカードをトラッシュし、サイドは 1 枚です。退化・ベイビィ・1 進化を飛ばす進化を加えるときは、先に docs/architecture-v0.4c.md 14 章・docs/stage2-state-v0.4c.md 5 章の前提（重なりの上の側とログ `evolve` の対応、いちばん下がたねポケモン、`EVOLUTION_STAGES`）を見直し、原典と照合します（v0.25 でポケモン育て屋さんの 1 進化を飛ばす進化を加えたときに見直した。下の「ポケモン育て屋さん（v0.25）」・docs/pokemon-breeder-v0.25.md 6 章）。
- ワザによる持続する効果（v0.4b。p.322・p.323）は、場のポケモンの `PokemonInPlay.persistent_effects`（frozen の値のタプル。v0.4b は `state.PreventDamage`、v0.12 で `state.Retaliation`（「ほのおのかべ」。v0.13 で与えるダメージの決め方 `basis` を加え、「こうらがえし」も同じ型）を加えた。型の一覧は `state.PERSISTENT_EFFECT_TYPES`）に持ちます。特殊状態（`conditions`）・ついているトレーナー（`trainers`。物理的なカード）と 1 つの仕組みにまとめないでください。`AttachedTrainer` を流用したり、効果のためにカードの uid を作ったりしないでください。付ける・消す・調べるのは `kyuura_engine/persistent.py`（`add_persistent_effect`・`remove_persistent_effects`・`remove_expired_persistent_effects`・`damage_prevention`・v0.12 の `retaliation`）だけで、消したらログ `persistent_effect_removed`（`reason`: `expired`・`retreat`・`switch`・`evolve`・`knock_out`）を残します。
- 持続する効果が消える契機は、期限（「かたまる」は次の相手の番の終わり。`_end_turn` で、ついているトレーナーのトラッシュのあと・ポケモンチェックの前。p.236・p.18 のワザ解説。SUPPORTED）・ベンチに戻る（にげるの成功・ポケモンいれかえ。p.311・p.322）・進化（p.310・p.323）・きぜつ（p.322）です。進化・ベンチに戻るときは、特殊状態の解除・持続する効果の解除・にげるの失敗の記録の解除を別々の関数で行い、ついているトレーナーは消さないでください（進化では受け継ぐ。v0.4a の E8'）。こんらんで「にげる」に失敗したらベンチに戻っていないので消しません。一度消えた効果は復活しません。「次の相手の番」は効果を与えた番 + 1 で表しています（番は交互に進む前提。v0.2e と同じ）。
- 「ダメージを受けない」状態（「かたまる」の効果。最新の説明「次の相手の番、このカードはダメージを受けない。（ダメージ以外の効果は受ける）」。印刷の文面「…ダメージが0になる。」にはしたがわない）のポケモンにダメージを与えるワザの要素は無効です（p.321）。`effects.deal_attack_damage` の最初で `damage_prevention` を見て、計算せずにログ `damage_prevented` だけを残します（防いだ量は書かない）。`DamageModifier` に大きな負の数を入れる・ディフェンダーと同じ 7 段階にする形にしないでください。ほかのポケモンへのダメージ・ダメージ以外の効果の要素は有効なので、ワザの実装は効果のコイン・特殊状態をいつもどおり処理します（「ダメージが 0 になった」ことを、ワザの失敗・効果の要素の省略にしないでください）。ポケモンチェックのどくのダメージは効果を見ません（p.323。どちらの番でもない）。
- コインでダメージの量を決める要素だけのワザ（`CoinFlipDamage`。みだれづき・v0.4c のスピアーのダブルニードル）を「ダメージを受けない」相手に使うときにコインを投げるかは原典で決められないので、`CoinFlipDamage.problem` がこんらんのコインの前に `UNRESOLVED_PREVENTED_COIN_DAMAGE` を返します。「ダメージを与えたら」起こる効果（メガドレインなど）を加えるときは、発生条件に実際にダメージを与えたかが含まれるかをカードごとに照合し、特殊状態の追加効果と同じ扱いにしないでください（docs/persistent-damage-v0.4b.md 5 章）。
- 持続する効果の不変条件（`engine._persistent_effect_problems`）は、型・発生源（`PreventDamage`・`Retaliation` は自分自身）・番（与えた番は持ち主の番、はたらく番は次の番、期限が過ぎていない）・置き場所（バトル場だけ）・重複・ログとの対応（`persistent_effect_added` があり、そのあとに消したはずのイベントがない）を確かめます。テストで効果を置くときは `build_test_state` の `"prevent_damage"`・v0.12 の `"retaliation"`・v0.13 の `"retaliation_received"`（効果を与えた番）を使ってください。効果を与えた番にそのポケモンがベンチに戻る・進化する盤面は自然な対戦では起こらないので、そのテストは「盤面を直接作った」と書き、自然な対戦の結果として数えないでください。形式 1〜7 は持続する効果を書き出せない（`ValueError`）ので、形式 8 で比べます。相手に与える持続する効果（すなかけ・からまるいと）・カウンターをのせるタイプ・期限のない効果を加えるときは、型・期限の表し方・消える契機・不変条件（発生源が自分自身であること）を見直してください。
- ワザの途中で相手プレイヤーが決定する処理（v0.4d。バタフリーの「ふきとばし」）は、v0.2a の `push_attack_decision` に `player=相手` を渡して出し、`_resume_attack` → `_finish_attack` で続けます。番のプレイヤー（`current_player`）・番の番号は変えません。段階は既存の `Phase.DECISION` で、新しい段階・コマンド・保留中のリストを加えないでください。選べるものは場のポケモンの番号（`pokemon_id`）です。ワザの実装は、自分が出す決定の形（種類・決定するプレイヤー・選べるもの・`context`）を `AttackEffect.decision_problems` で宣言します（既定は「決定するのはワザを使ったプレイヤー」。相手が決定する効果は上書きする）。不変条件（`engine._attack_decision_problems`）は、続きの情報・番のプレイヤー・ワザを使ったポケモン・今の番のワザのログ `attack` を共通に確かめてから、それを呼びます。`resume` は決定のあとの要素だけを処理し、宣言・エネルギーの確認・コイン・それまでのダメージを繰り返さないでください（docs/architecture-v0.4d.md 3〜5 章）。
- ワザの効果による相手の強制交代（v0.4d）は「にげる」（`_retreat`）を通さず、にげるエネルギー・こんらんのコイン・にげるの失敗の記録に関わりません。場のポケモンごと入れ替え、ベンチにもどったポケモンの特殊状態と持続する効果は、既存の `clear_special_conditions`・`remove_persistent_effects` に理由 `FORCED_SWITCH`（`forced_switch`）を渡して別々に消します。ついているトレーナー（有効期限も）・ダメージ・エネルギー・重なり・番号は変えません。ログは `forced_switch`（入れ替えなかったら `forced_switch_skipped`）で、トレーナーの `switch` の形は変えないでください。相手に控えがいなければ入れ替えない（ワザの説明の規定）ことと、トレーナーの `UNRESOLVED_SWITCH_WITHOUT_BENCH` は別の規定です（docs/forced-switch-v0.4d.md）。
- ワザのダメージの要素の結果（v0.4d）は、`deal_attack_damage` の戻り値 `DamageResult`（受けたポケモン・`prevented`・`amount`（防いだら None）・`knocked_out`、`dealt`）で後の要素に渡します。ログを読み直して直前のダメージを推定しないでください。計算した結果の 0（`amount` 0）とダメージを防いだこと（`prevented`。計算しない）を区別し、「ダメージを与えたら」起こる効果がどちらを同じに扱うかはカードごとに照合します（メガドレインはどちらも回復しない。docs/damage-drain-v0.4d.md）。「与えたダメージ」は最終ダメージで、相手の残りの HP で上限を付けません（p.319）。
- ワザのダメージで相手の対戦ポケモンが HP 以上のダメージを受けたら、その後の相手の対戦ポケモンへの効果の要素は、ワザの実装が `DamageResult.knocked_out`（または HP との比較。v0.3a からの実装）で見て処理しません（p.309・p.89・p.213。v0.4d のふきとばしは SUPPORTED）。きぜつの処理（トラッシュ・サイド・交代）の時点は `_finish_attack` のままにしてください（ワザの途中でトラッシュしない）。
- 与えたダメージによる回復（v0.4d。メガドレイン）は、ワザを使ったポケモン（`AttackUse.pokemon_id`）から、のっている数までとりのぞき、ログ `drain_heal` に計算のもとにした与えたダメージを残します。「きずぐすり」のログ `remove_damage_counters` の形は変えないでください。
- 状態の書き出しの形式 1 は、ワザの途中の決定（`resume="attack"`）があると `ValueError` です（v0.4d。形式 1 に決定の項目がないため。黙って落とさない）。ワザの途中の決定のある状態は形式 2 以上（進化したポケモンがいれば形式 7 以上）で比べます。
- 原典で決められないとして止めている裁定（`UNRESOLVED_…`）の分類を変えるときは、根拠の誌面と読み方の比較を docs/unresolved-rulings-v0.3d.md のように書きます。SUPPORTED を根拠なく CONFIRMED にしないでください。
- トレーナーの効果の途中の決定（v0.4e）は、ワザ（v0.4d の `AttackEffect.decision_problems`）と同じく、トレーナーの実装が `TrainerEffect.decision_problems` で決定の形（決定するプレイヤー・種類・選ぶ数・選べるもの・原典で決められない選択）を宣言します。決定を出すトレーナーを加えたら上書きしてください（既定は「決定するのはトレーナーを使ったプレイヤー」だけを確かめる）。決定を待つ間は場が変わらないので、選べるものは決定を出したときと同じ並びです。
- サイドを取る決定の並びは、不変条件（`engine._prize_queue_problems`。v0.4e）が、ログのきぜつ（`knock_out`）から決まる「だれが何枚取るか」と比べます。同時のきぜつで両方が取る順番は確かめません（p.325 で番のプレイヤーが選べる。エンジンは正規化しているが、ほかの順番もルール上は正しい）。両方がバトル場に出す順番（番でないプレイヤーが先。pp.323〜324）は確かめます。サイド・きぜつに関わるカードを加えるときは、この確認を見直してください。
- 状態の番の番号と番のプレイヤーは、最後のログ `turn_start` と同じであることを不変条件で確かめています（v0.4e）。テストで番を進めるときは `EndTurn` などのコマンドを使い、`turn_number` を直接書きかえないでください（壊した状態のテストを除く）。

## 総合監査・互換性・負荷の道具（v0.4e）

- テストの段階: A（速い単体テスト）と B（決まった seed の対戦・ログと書き出しの監査・前の版の参照データとの比較・小さなストレス実行）は `python3 -m unittest` に入っています。C（前の版との大きな比較・大規模なストレス実行）は、ふだんのテストで走らせないでください（`python3 tools/compare_engine_versions.py --base <コミット>`・`python3 tools/stress_engine.py`）。
- ログの監査（tests/log_audit.py の `log_problems`）は、ログだけから場のポケモンのダメージ・エネルギー・トラッシュ・サイドを組み立て直して状態と比べます。ダメージ・エネルギー・トラッシュを変えるログのイベントを加えたら、組み立て直しにも加えてください。ログは記録で、状態の正本ではありません（エンジンはログから状態を決めない）。
- 書き出しの監査（`serialization_problems`）は、形式 1〜10（v0.6 から 9、v0.31 から 10）が表せる状態だけを書き出し、最新の形式（`LATEST_FORMAT` = 10）から後の項目を除いたものと同じになることを確かめます。状態の項目を加えたら `required_format`・`POKEMON_FIELDS_SINCE`・`TOP_FIELDS_SINCE` を更新してください。形式 11 を加えるときは、監査の `LATEST_FORMAT` と docs/architecture-v0.6.md 4 章を見直します。
- 前の版との比較の駆動（tools/compat_driver.py）は、エンジンの公開の API だけを使い、版ごとに別のプロセス（`python3 -I`）で、指定した木の `kyuura_engine` だけを読み込みます。比べないのは効果の登録表の id（`effects`）だけです。ルールの動きに関わる状態・ログを比較から除かないでください。
- tests/fixtures/compat_base_4bd97bf.json は、基準の版（v0.4d の `4bd97bf`）で駆動が作った記録の指紋です。今の版から作り直さないでください（作り直すと前の版との比較ではなくなる）。駆動を変えたら、ファイルの `how` の引数で基準の版から作り直します。
- テストの盤面にポケモンについているトレーナーを置くときは、`build_test_state` の `"trainers"`（[(カード id, トラッシュする番), ...]）を使います。

## 変更するとき

- 規定を加えたり直したりしたら、対応する自動テストを加えます。テストの docstring かコメントに、根拠（誌面のページ、または kyuura の記録 id・採用したデータ）を書きます。kyuura データの採用で加えたカードに、読んでいない誌面のページを書かないでください。
- カードを登録したら、`python3 scripts/check_card_sources.py` と（../kyuura があれば）`python3 scripts/check_research_links.py --kyuura ../kyuura` を走らせます。
- 対戦のテストは、正式な開始（`new_game`、60 枚のデッキ、サイド 6 枚）を使います。盤面を直接作る `tests/helpers.py` の `build_test_state` は、1 か所の規定を確かめるテストだけに使い、対戦準備やデッキのテストには使いません。
- 乱数は `GameState.rng`（seed から作る）だけを使います。
- `apply_command` は渡された状態を変えません（clone してから処理する）。この性質を壊さないでください。
- `new_game`・`apply_command` は、返す状態を `check_invariants` で確かめます（破れていれば `StateIntegrityError`）。ゾーン・段階・保留中の決定を加えたら、その不変条件も `check_invariants` に加えます。段階やコマンドの種類を加えたら、tests/test_state_integrity.py の `ALLOWED`・`sample_commands` も更新します。
- 乱数・カードの番号の付け方・状態の形を変えると、tests/test_reproducibility.py の固定値が変わります。意図した変更のときだけ値を更新し、理由をコミットに書きます。
- docs（README.md、docs/implementation-status.md など）を実態に合わせます。対応していないものを対応済みと書かないでください。
- テスト: `python3 -m unittest`（リポジトリの直下。標準ライブラリだけ）。

## ポケモンパワー（v0.5）

- 2000.02.14 版の公式ルールの用語は「特殊能力」です（p.311・p.323）。一般の規定は docs/pokemon-powers-v0.5.md で誌面と照合しました。kyuura の rule_history.json・rule_differences.json のポケモンパワーの記録は第4版の冊子（ed4）のもので、2000.02.14 版の規定として使わないでください。英語版の文面・後年の英語版の規定（`EN-2002-STATUS-POWERS`）・現代の「特性」のルールで日本語版の処理を決めないでください。
- ポケモンパワーはワザ（`AttackEffect`）の一種として扱わないでください。`effects.PowerKey`（カード id, パワーの位置）で `PowerEntry`（実装 `PowerEffect`・照合した kyuura の写しの名前と印刷の文面・実装がしたがう最新の説明 `play_text_ja`・出典）を登録します。登録がない・データ（名前・文面・種類）と合わないパワーを持つカードは使えません（cards.py が分類し、使用は `UNSUPPORTED_POKEMON_POWER`）。パワーを持つカードを一括で対応にしないでください。照合の記録は `card_verification.json` の `power_card_image_text_ja`・`power_latest_description_ja`（パワーの位置ごと。tests/test_pokemon_powers_v0_5.py が確かめる。過去の原典照合で登録したパワー。2026-10-15 からの採用の記録で登録するパワーは、採用の記録の `play_text` で確かめる）。
- 使用は `UsePokemonPower(player, pokemon, power, energy, source, target)` です。`pokemon`・`source`・`target` は場のポケモンの番号（`pokemon_id`）、`energy` はカードの uid。v0.4e までの 2 つの項目（`player`・`pokemon`）の辞書も読めるようにしてあります（壊さないでください）。番のプレイヤーの `Phase.MAIN` だけで受け付けます（決定を待つ間・ワザのあとは不可）。使っても番は終わりません（`_finish_attack` を呼ばない）。
- どの特殊能力があるかは、いちばん上のカードの定義で決めます（進化前のカードの特殊能力は使えない。p.310）。
- 使う前の共通の確認は `engine._use_pokemon_power`、パワーごとの確認（使えない特殊状態・説明が選ばせるもの）は `PowerEffect.check_usable` で、どちらも状態を変える前に済ませます（拒否で状態・乱数・ログが変わらない）。原典で決められない場合は、成功を仮定せず `UnsupportedError`（`UNRESOLVED_…`）で止めます。特殊状態の制限はパワーの説明ごとです。ワザ・にげるの制限（`engine._require_not_asleep_or_paralyzed`・こんらんのコイン）を流用しないでください。
- 「何度でも使える」パワーの回数は数えません。回数の制限のあるパワー（「自分の番ごとに1回」など）を加えるときは、回数を状態に持ちます（ログから数えない。書き出しの新しい形式と不変条件が要る。v0.6 の `energy_attached_by_powers_this_turn` と同じ形。v0.31 のしぜんになおるは `power_uses_this_turn`（形式 10）で、同じ形のパワーは `PowerEffect.once_per_turn = True` にすればこの記録を使える。次の新しい形式は 11）。v0.5 のパワーは決定を出しません。決定を出すパワーを加えるときは、ワザ（v0.4d）・トレーナー（v0.4e）と同じく `resume`・`decision_problems` と再開先を加えます。自動的にはたらく・常にはたらくパワーは宣言しないので、`UsePokemonPower` の形では扱いません（どちらも `PowerEffect.declared = False`。常にはたらくパワーは下の「かがくへんかガス（v0.8）」、自動的にはたらくパワーは下の「とうめい（v0.9）」「はんげき（v0.10）」。docs/architecture-v0.5.md 9 章）。決められたときにしか使えない（宣言する）パワーは `declared = True` のまま `check_usable` で拒否し、決められたときにエンジンが決定で使うかを聞きます（下の「こんじょう（v0.11）」）。
- エナジートランス（`EnergyTransfer`）は、同じ uid のエネルギーカードを移動元の `energy` から移動先の `energy` へ移すだけです（複製・トラッシュ・持ち主の変更をしない）。`energy_attachments_this_turn`（手札からつけた回数）は変えず（SUPPORTED。docs/venusaur-v0.5.md V10）、乱数を使いません。ログは宣言 `pokemon_power` のすぐあとに `move_energy` で、手札からつけた `attach_energy` と混同しないでください。1 回の使用で 1 枚は実装上の仮定です（ルールとして扱わない。docs/energy-transfer-v0.5.md 3 章）。特殊エネルギーを加えるときは、移せるエネルギーの判定（今は「草」の基本エネルギー）を見直してください。
- ワザ・にげるに必要なエネルギーは、そのときついているエネルギーで決めます（つけかえの前の値を覚えておかない）。
- やどりぎのタネ（`DamageAndRemoveCounters`）は `DamageResult.dealt` で「ダメージを与えたら」を判定し、メガドレインと同じ `effects._remove_attacker_counters`（ログ `drain_heal`）でとりのぞきます。フシギソウのどくのこな（`PoisonOpponent`）はコインを投げません。コインを投げる `PoisonOnHeads` を流用しないでください。
- ストレス実行（tools/stress_engine.py）は、フシギバナの組（`POWER_SCENARIOS`）でエナジートランスの使用を混ぜます。比較の駆動（tools/compat_driver.py）は変えていません（参照データ compat_base_4bd97bf.json と結びついているため）。駆動にパワーの操作を加えるときは、参照データを基準の版から作り直します。
- 未対応のポケモンパワーを持つカードの例はリザードン（PMCG1-021。写しの参照カード。v0.5 ではカメックス、v0.6 ではフーディンだったが、それぞれ v0.6・v0.7 で対応にした）を使います。登録を除いた登録表（`DEFAULT_EFFECTS.without_powers(...)`）でも作れます。

## あまごいと手札からつける処理（v0.6）

- カメックス（PMCG1-032）の「あまごい」は `effects.AttachEnergyFromHand`（`PowerKey("PMCG1-032", 0)`）です。`UsePokemonPower` の `energy` は手札のカードの uid、`target` はつける先の場のポケモンの番号で、`source` は使いません（指定したら `POWER_CHOICE_NOT_USED`）。エナジートランス（`EnergyTransfer`。場のエネルギーのつけかえ、ログ `move_energy`）と取りちがえないでください。項目の意味はパワーごとに違うので、パワーの実装の `check_usable` が確かめます。裁定は docs/rain-dance-v0.6.md（R1〜R15）、設計は docs/architecture-v0.6.md。
- 手札のエネルギーカードを場のポケモンにつけるのは `zones.attach_energy_from_hand` だけです（通常の操作 `engine._attach_energy` とあまごいで共通）。カードを動かすだけで、つけてよいかの確認・回数・ログは呼ぶ側が、動かす前にすべて済ませます。ほかのゾーンから場へ動かすパワー・トレーナーを加えるときも、同じように 1 か所の関数にしてください。
- 手札からつける通常の操作（p.310。1 番に 1 枚）の回数 `energy_attachments_this_turn` と、ポケモンパワーで手札からつけた枚数 `energy_attached_by_powers_this_turn`（番の最初に 0。不変条件で今の番のログ `power_attach_energy` の数と同じ）は別に持ちます。1 つにまとめないでください（まとめると R13 を決めることになる）。あまごいは通常の操作の回数を見ません（R12。SUPPORTED）。
- あまごいでつけたあと、その番にまだ通常の操作をしていないときの通常の操作は、原典で決められない（R13。p.310 の「1枚だけ」にあまごいでつけたカードを数えるかが書かれていない）ので、`engine._attach_energy` が、ほかの確認がすべて通ったあと、カードを動かす前に `UnsupportedError`（`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`）で止めます。英語版の文面（「This doesn't use up your 1 Energy card attachment」）で決めないでください。テストは「止まること・状態が変わらないこと」だけを確かめます。原典で決まったら、止める処理を決まった処理に置きかえ、分類を変える根拠を docs に書きます。
- 書き出しの形式 9 は形式 8 に `energy_attached_by_powers_this_turn` を加えたものです。形式 1〜8 は、その数が 0 でなければ `ValueError`。あまごいを使う対戦は形式 9 で比べます（ストレス実行の拒否の前後の比較も形式 9）。比較の駆動（tools/compat_driver.py）は形式 8 のままで変えていません（参照データ compat_base_4bd97bf.json と結びついているため）。
- ログの監査（tests/log_audit.py）は v0.6 から手札も組み立て直します（引いた・取ったサイド → 場に出した・進化・つけた・使った・切り直し）。手札を変えるログのイベントを加えたら、組み立て直しにも加えてください。宣言（`pokemon_power`）のすぐあとには、その処理のイベント（`move_energy`・`power_attach_energy`・v0.7 の `move_damage_counter`）が 1 つあることも確かめています（決定を出すパワーを加えるときは見直す）。
- ハイドロポンプ（`ExtraEnergyDamage`）は、ついている「水」エネルギーから必要な数を引いた数（上限 2）× 10 を基本となるダメージ（p.321 の 1 段階）に加えます。必要なエネルギーがすべて同じタイプのワザだけを登録できます（無色が混ざるワザを加えるときは、どのエネルギーで払ったかの扱いを原典で確かめる）。
- ゼニガメ・カメールの「からにこもる」は、トランセル・コクーンの「かたまる」と同じ `PreventDamageOnHeads` で、印刷の文面（「…受けるダメージが0になる。」）ではなく最新の説明にしたがいます。

## ダメージスワップとケーシィの系統（v0.7）

- フーディン（PMCG1-049）の「ダメージスワップ」は `effects.MoveDamageCounter`（`PowerKey("PMCG1-049", 0)`）です。`UsePokemonPower` の `source`・`target` は移動元・移動先の場のポケモンの番号（どちらも自分の場。バトル場・ベンチ・フーディン自身のどれでもよい）で、`energy` は使いません（指定したら `POWER_CHOICE_NOT_USED`）。エナジートランス（エネルギーのつけかえ）・あまごい（手札からつける）と取りちがえないでください。裁定は docs/damage-swap-v0.7.md（S1〜S25・A4）、設計は docs/architecture-v0.7.md、確かめた結果は docs/v0.7-verification.md。
- 1 回の使用で 1 個を移すのは実装上の仮定です（ルールとして扱わない。S3）。何度でも使えるので、どの移し方も途中できぜつしない 1 個ずつの移動に分けられる（S18。docs/damage-swap-v0.7.md 4 章の証明）。1 回に何個も移す形（`count` などの項目・移動の一覧）にするときは、途中の状態のきぜつの扱いを原典で確かめてから変えてください。「何度でも」なので使った回数を状態に持たず、数えません。
- きぜつさせる移動は、状態を変える前に `effects.would_be_knocked_out(state, target, target.damage + 10)` で確かめて `WOULD_KNOCK_OUT` で拒否します（p.153「この力によってポケモンが「きぜつ」しないかぎり」。CONFIRMED）。移してからきぜつの処理（`_after_knockouts`）にまかせる形にしないでください（サイド・交代が起こってしまう）。HP はいちばん上のカードの値です。不変条件（場のポケモンのダメージは HP 未満）が二重に確かめます。
- 確かめる順番（docs/architecture-v0.7.md 3 章）: 使うフーディンのねむり・マヒ・こんらん（選ばせるものより先）→ 選ばせるものの有無・`energy` の指定 → 移動元・移動先が自分の場のポケモン → 別のポケモン（`SAME_POKEMON`）→ 移動元にカウンター（`NO_DAMAGE_COUNTERS`）→ きぜつ（`WOULD_KNOCK_OUT`）。どくのフーディンは使えます（S8。SUPPORTED）。移動元・移動先の特殊状態は見ません（S9）。
- 拒否のコードの順番のうち API の約束として保証するのは、型 → 対戦の終わり → 段階・番 → 共通の確認 → パワーごとの確認、パワーの使えない特殊状態は選ばせるものより先、`UNRESOLVED_…` はほかの確認がすべて通ったあと、だけです（docs/architecture-v0.7.md 12 章）。それ以外の `IllegalActionError` の理由どうしの順番（v0.6 の変異 19・v0.7 の変異 25）をテストで固定しないでください。
- 移したカウンターは「ダメージを受けた」ことになりません（p.320。S19）。`damage` を 10 ずつ動かすだけで、`deal_attack_damage` を通さず（弱点・抵抗力・プラスパワー・ディフェンダー・「ダメージを受けない」状態を計算しない）、ログ `damage` を出しません。ログは宣言 `pokemon_power` のすぐあとに `move_damage_counter`（`count` 1・`from_pokemon_id`・`to_pokemon_id`・移したあとのダメージ）です。`remove_damage_counters`（きずぐすり）・`drain_heal`・`move_energy` と混同しないでください。「ダメージを受けたとき」にはたらく効果を加えるときは、移動で起こさないことを確かめてください。
- ダメージスワップは、あまごいの R13 の判定（`energy_attached_by_powers_this_turn`）に数えません（S20）。R13（`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`）は v0.7 で変えていません。
- 書き出しは形式 9 のままです（v0.7 で状態の項目・形式を加えていない。監査の `LATEST_FORMAT` も 9）。
- ログの監査（tests/log_audit.py）は `move_damage_counter`（持ち主・場にいるか・別のポケモン・移動元のカウンター・移したあとのダメージ・移動先が HP 未満・ワザのあとでない・登録がダメージカウンターを移すパワー）と、じこさいせいの `discard_energy`・`remove_all_damage_counters` を組み立て直します。ダメージを動かすパワー・ワザを加えたら、組み立て直しにも加えてください。
- ユンゲラー（PMCG1-046）の「じこさいせい」は `effects.DiscardEnergyAndRemoveAllCounters`（`energy_type` は超）です。ワザの途中の決定（v0.4d の仕組み）で、ワザを使ったプレイヤーが、ワザを使ったポケモンについている「超」の基本エネルギーカード（ついている順）から 1 枚選びます（決定 `decisions.DISCARD_ENERGY`。1 枚しかなくても決定を出す。実装上の仮定。K2）。`resume` はトラッシュ（ログ `discard_energy`）→ すべてとりのぞく（ログ `remove_all_damage_counters`）だけを処理します。ダメージカウンターがなくても使えます（K4。きずぐすりの `UNRESOLVED_POTION_WITHOUT_DAMAGE` とは別）。「トラッシュできないとき、このワザの効果はなくなる」（K3）は今の対応カードでは起こらないので `RuntimeError` にしています。特殊エネルギーを加えるときは、この場合の処理とテストを加えてください。裁定は docs/alakazam-line-v0.7.md（K1〜K10）。
- ケーシィ・ユンゲラー・フーディンは自分の弱点が超なので、こんらんで自分に与える 20 は 40 になります（p.322。K10）。こんらんの 20 を固定値で期待するテストは、`damage.calculate_confusion_damage` の値（弱点・抵抗力だけ）で期待してください。
- ストレス実行（tools/stress_engine.py）は、フーディンの組（`alakazam`・`alakazam_mixed`）でダメージスワップの使用を混ぜます。`POWER_USERS` の並びの最後にフーディンを加えたので、フーディンのいない組の操作（乱数の使い方）は v0.6 と同じです。並びを変えると、ほかの組の操作が変わります。比較の駆動（tools/compat_driver.py）は変えていません。

## かがくへんかガスと常にはたらく特殊能力（v0.8）

- ベトベトン（PMCG3-007）の「かがくへんかガス」は `effects.SuppressOtherPowers`（`PowerKey("PMCG3-007", 0)`。`exempt_name` は「かがくへんかガス」）です。常にはたらいていて使用を宣言しない（p.311・p.323）ので `PowerEffect.declared = False` で、`UsePokemonPower` は `POWER_NOT_DECLARABLE`（`check_usable`・`resolve` を呼ばない）。裁定は docs/chemical-gas-v0.8.md（G1〜G33・A4）、効果の求め方は docs/continuous-effects-v0.8.md、設計は docs/architecture-v0.8.md、確かめた結果は docs/v0.8-verification.md。
- はたらいているかは状態に持たず、kyuura_engine/continuous.py（`suppressors_of`・`working_power_suppressors`・`power_suppressors`）が、場のポケモン・いちばん上のカード・特殊状態・効果の登録表から、問い合わせのたびに求めます。「はたらいている」の印・一覧を `GameState`・`PokemonInPlay` に加えたり、ログを読んで決めたりしないでください（進化・きぜつ・回復・ベンチに戻る・保存と復元で古くなる。変異 10・21・22）。かがくへんかガスのログのイベントもありません（原因の `evolve`・`knock_out`・`special_condition`・`special_conditions_removed` は今までどおり）。
- 消すのは、両方のプレイヤーの場の「かがくへんかガス」以外のすべての特殊能力です（持ち主を見ない。G4）。ねむり・マヒ・こんらんのベトベトンの力は消えていて、どくは関係しません（G9〜G12）。かがくへんかガスどうしは名前で除くので消し合いません。`check` が「かがくへんかガス」という名前のパワーにだけ登録を許すので、判定は循環しません。
- `engine._use_pokemon_power` の確かめる順番は、共通の確認（使うポケモン・特殊能力の有無・登録）→ `POWER_NOT_DECLARABLE` → `POWER_SUPPRESSED`（`suppressors_of`）→ パワーごとの `check_usable` です（API の約束。docs/architecture-v0.8.md 2 章・13 章。変異 24）。パワーの実装の `check_usable` に、かがくへんかガスの確認を重ねて書かないでください。
- ワザ・トレーナー・手札からつける通常の操作・進化・にげるは止めません（G8・G28）。消える前にすませた特殊能力の結果は戻しません（G27）。R13（`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`）は変えていません（G29。`energy_attached_by_powers_this_turn` を変えない）。
- 自動的にはたらく・かがくへんかガスのほかの常にはたらく特殊能力を加えるときは、その効果を使う前に `continuous.suppressors_of` を聞いてください（G7。「その力も消える」。v0.9 の「とうめい」は `effects.evasion_power` が聞いている）。期限のある「特殊能力を消す」効果（まきちらせ！ベトベトガス p.265・ドガースのふしぎなガス p.52）は期限を状態に持つ必要があるので、`suppressors_of` の発生源・書き出しの形式 10・不変条件を見直します（docs/continuous-effects-v0.8.md 6 章）。
- ログの監査（tests/log_audit.py）は v0.8 から、ねむり・マヒ・こんらんを組み立て直し（`special_condition`・`special_conditions_removed`・`knock_out`）、特殊能力の宣言のたびに、その時点の場ではたらいているかがくへんかガスを求めて、消されている特殊能力の使用・宣言しない特殊能力の宣言がないことを確かめます（最後の状態だけで過去の使用を決めない）。ねむり・マヒ・こんらんを変えるログのイベントを加えたら、組み立て直しにも加えてください。
- ロケット団のベトベター（PMCG4-004）の「どくガス」は `PoisonWithoutDamage`（ダメージの目安なし・コインなし。ダメージの目安のあるワザの `PoisonOpponent` を流用しない）、「ねばりつく」は `CoinBonusDamageAndParalyze(bonus=20)`（コイン → 基本となるダメージ（「おもて」なら + 20）→ きぜつしていなければマヒ。「ダメージを受けない」相手にもコインを投げる）、ベトベトンの「ヘドロこうげき」は `PoisonOnHeads` です。裁定は docs/grimer-line-v0.8.md（M1〜M9）。化石の秘密のベトベター（PMCG3-003）は参照カード（「ちいさくなる」が未実装）。
- 書き出しは形式 9 のままです（v0.8 で状態の項目・形式を加えていない。監査の `LATEST_FORMAT` も 9）。
- ストレス実行（tools/stress_engine.py）は、ベトベトンの組（`muk`・`muk_mixed`）でかがくへんかガスの場面を混ぜます。`POWER_USERS` の並びの最後にベトベトンを加えたので、ベトベトンのいない組の操作（乱数の使い方）は v0.7 と同じです。比較の駆動（tools/compat_driver.py）は変えていません。

## とうめいと自動的にはたらく特殊能力（v0.9）

- ゴースト（PMCG3-030。化石の秘密）の「とうめい」は `effects.AttackImmunityOnHeads`（`PowerKey("PMCG3-030", 0)`）です。決められたとき（ワザによってダメージや効果を受けるとき）に自動的にはたらき、使用を宣言しない（p.323）ので `declared = False` で、`UsePokemonPower` は `POWER_NOT_DECLARABLE`。裁定は docs/transparency-v0.9.md（T1〜T42・A4）、仕組みは docs/automatic-powers-v0.9.md、設計は docs/architecture-v0.9.md、確かめた結果は docs/v0.9-verification.md。第1弾のゴースト（PMCG1-047）は同じ名前の別のカード（参照カード）で、取りちがえないでください。
- 評価は、ワザの要素がポケモンにダメージや効果を与える直前に `effects.attack_reaches(state, use, owner, pokemon, element, amount=...)` を呼ぶことだけで行います。ダメージは `deal_attack_damage` が、p.321 の計算で最終ダメージが 0 より大きいときに呼びます（0 なら「ダメージを受けなかった」ので呼ばない。T21）。効果（特殊状態・入れ替え）を与えるワザの実装は、効果の前に呼びます。ポケモンに効果を与えるワザの実装を加えるときは、必ず呼んでください（要素の種類が `ATTACK_ELEMENTS` になければ加える）。汎用のイベントの仕組み（購読・発行）にしないでください。
- コイン・ログ（`evade_check`・`attack_evaded`）・記録は `attack_reaches` だけが行います。コインはゴースト側のプレイヤー（T33）が `flip_coins`（`source="power"`、`effect` は `PowerKey`）で、1 つのワザにつき 1 匹 1 回（T4。SUPPORTED）。結果は `AttackUse.reception`（ワザ 1 回の中だけの値。状態に持たない。比較・表示に含めない）に記録し、同じワザのあとの要素で使います。はたらいていなければ、記録・コイン・ログはありません。「とうめい」の結果を状態・ログから読み直さないでください。
- はたらいているか（`effects.evasion_power`）は、いちばん上のカード・特殊状態（ねむり・マヒ・こんらんで消える。どくは関係しない）・v0.8 の `continuous.suppressors_of`（かがくへんかガス）から、問い合わせのたびに求めます。抑止の判定を複製しないでください。場所（ベンチ）・ワザを使ったプレイヤーは見ません（T7・T8）。公開の問い合わせは `working_evasion_power(state, pokemon_id)`。
- ワザは失敗にしません（T17・T18。エネルギーはついたまま・番は終わる・ワザを使う側への要素は処理する）。受けなかったら `deal_attack_damage` は `DamageResult.evaded`（`amount` は None）を返し、「ダメージを与えたら」の効果では `dealt` が 0 です。受けなかったダメージで、きぜつしたことにしないでください（`knocked_out` は今のダメージで求める）。
- 原典で決められない「おもて」のあとのワザのコイン（T19b）は、`PoisonOnHeads`・`ParalyzeOnHeads`・`ConfuseOnHeads` の `problem`（`evaded_effect_coin_problem`。最終ダメージは状態を変えない `preview_attack_damage`）が、ワザの宣言の前に `UNRESOLVED_EVADED_EFFECT_COIN` で止めます。「ダメージ → ワザのコイン → 効果」のワザを加えるときは、同じ `problem` を持たせ、ワザのコインの前に `_require_not_evaded` を置いてください。
- 決定をまたぐ（`resume`）と `AttackUse` は新しくなり、記録は引き継がれません。v0.9 の対応カードは、受けるかを決めてから決定を出します（ふきとばし）。決定のあとで受けるかを決めるワザを加えるときは、結果を決定の `context` に持ってください（書き出しの形式を変えずに済む。docs/automatic-powers-v0.9.md 3 章）。
- 1 つのワザで複数の「とうめい」のポケモンが受ける場合のコインの順番（T27）は原典で決められません。ベンチ・複数のポケモンにダメージや効果を与えるワザを加えるときは、コインの前に止める処理を加えてください（実装の順番を裁定にしない）。自分への効果（かたまる・じこさいせい・回復）を「とうめい」を持つポケモンのワザとして加えるときは、評価を加えます（docs/automatic-powers-v0.9.md 2.1）。
- 「とうめい」のほかに自動的にはたらく特殊能力を加えるときは、はたらく時点を原典で確かめてその処理の中で評価し、`continuous.suppressors_of` を聞いてください（v0.10 のカイリキー［はんげき］は下の「はんげき（v0.10）」）。乱数を使うなら docs/automatic-powers-v0.9.md 4 章の保証を守ります。
- ゴースの「エナジーへんかん」は `RecoverEnergyAndSelfDamage(max_cards=2, self_damage=10)` です。ワザの途中の決定（`decisions.RECOVER_ENERGY`。`min_choices` 0・`max_choices` は min(2, トラッシュのエネルギーカードの枚数)）で選び、0 枚を選ぶと `UNRESOLVED_RECOVER_ZERO_ENERGY`（H4。決定は待ったまま）。トラッシュにエネルギーカードがなければ決定を出さずに自分へのダメージだけ（H5）。手札に加える → 自分にダメージの順（ログ `recover_energy` → `damage`）。ゴーストの「あくむ」は `SleepOpponent`（ダメージのあとコインなしでねむり。ダメージのない `PutToSleep` と区別する）、ゴースの「したでなめる」は `ParalyzeOnHeads`。裁定は docs/haunter-line-v0.9.md（H1〜H13）。
- ログの監査（tests/log_audit.py）は v0.9 から、ワザごとに「とうめい」の判定とその直前のコイン・判定のあとの処理・受けないと決まったポケモンへのダメージと効果・はたらいている「とうめい」の判定のないダメージと効果を確かめ、`recover_energy`（トラッシュ → 手札）を組み立て直します。ダメージ・効果を与えるワザや自動的にはたらく特殊能力を加えたら、監査にも加えてください。ログだけで確かめられない制約は docs/architecture-v0.9.md 8.1。
- 書き出しは形式 9 のままです（v0.9 で状態の項目・形式を加えていない。監査の `LATEST_FORMAT` も 9）。エンジンが止める `UNRESOLVED_…` は 14 件（v0.8 までの 12 件は変えていない。R13 を含む）。
- ストレス実行（tools/stress_engine.py）は、ゴーストの組（`haunter`・`haunter_muk`）で「とうめい」の場面を混ぜます。`POWER_USERS` の並びの最後にゴーストを加えたので、ゴーストのいない組の操作（乱数の使い方）は v0.8 と同じです。比較の駆動（tools/compat_driver.py）は変えていません。

## はんげきとダメージを受けたあとに自動的にはたらく特殊能力（v0.10）

- カイリキー（PMCG1-057。第1弾）の「はんげき」は `effects.CounterattackDamage(amount=10)`（`PowerKey("PMCG1-057", 0)`）です。相手のワザによってダメージを受けたときに自動的にはたらき、使用を宣言しない（p.323）ので `declared = False` で、`UsePokemonPower` は `POWER_NOT_DECLARABLE`。裁定は docs/counterattack-v0.10.md（C1〜C43・A4）、仕組みは docs/post-damage-powers-v0.10.md、設計は docs/architecture-v0.10.md、確かめた結果は docs/v0.10-verification.md。進化元のゴーリキー（PMCG1-055）のワザは docs/machamp-line-v0.10.md（M1〜M12）。サカキのカイリキー（PMCG6-061）は名前に「カイリキー」を含む別のカード（v0.10 では参照カード。v0.11 で［こんじょう］を対応にした）で、取りちがえないでください。
- 判定は、相手のワザのダメージの要素（`effects.deal_attack_damage`。最終ダメージが 0 より大きく、受けるポケモンの持ち主がワザを使ったプレイヤーでない）で、ダメージをのせる直前の状態（「ダメージを受けるとき、すでに」）から `counterattack_power` で求め、`AttackUse.counterattacks`（ワザ 1 回の中だけの記録。状態に持たない。比較・表示に含めない）に加えるだけです。「ダメージが増えた」ことから判定しないでください（こんらんの 20・どく・ダメージスワップ・「はんげき」自身のダメージは、ワザのダメージの要素を通らないので判定しない。C4〜C7・C14）。
- 10 を与えるのは `effects.finish_damage_elements` だけです。そのワザのダメージの処理（自分へのダメージを含む）がすべて終わったところ、ダメージ以外の効果（ワザのコイン・特殊状態・入れ替えの決定・回復）の前（p.89 の「こうらがえし」の解説。SUPPORTED）。ダメージ以外の効果のあるワザの実装は、最後のダメージの要素のあと・効果の前に `finish_damage_elements(state, use)` を呼んでください。エンジンも `resolve`・`resume` のあとに呼びます（ダメージの要素だけのワザ）。呼ばずに効果（`attack_reaches` のダメージ以外の要素）・決定（`push_attack_decision`）・回復（`_remove_attacker_counters`）に進むと `RuntimeError` です（`_require_damage_elements_finished`。順番を黙って変えない）。ダメージを与えるワザ・効果のあるワザを加えたら、どちらに当たるかを確かめてください。
- 「はんげき」の 10 は特殊能力によるダメージで、ワザによるダメージではありません（p.321「8」・p.138・p.245。SUPPORTED）。`deal_attack_damage` を通さず（`_apply_counterattack`）、弱点・抵抗力・プラスパワー・ディフェンダー・「とうめい」を計算・判定しません。ダメージカウンターの移動（`move_damage_counter`）にもしないでください。連鎖は発生源の分類で起こらないので、回数の上限で止めないでください。
- カイリキーがそのダメージで HP 以上になっても与えます（「（それによってこのカードが「きぜつ」しても、）」。CONFIRMED）。きぜつ・サイド・交代・勝ち負けは今までどおりワザのあとの `engine._finish_attack` で、変えていません。ワザを使ったポケモンが同じワザの自分へのダメージですでに HP 以上なら与えず `counterattack_skipped`（C15）、「はんげき」で HP 以上になったら、そのあとの自分の回復は処理せず `drain_heal_skipped`（C16）、相手への効果（ふきとばし）は処理します。ふきとばしの決定を待つ間だけ、「はんげき」で HP 以上になったワザを使ったポケモンが場に残ることを不変条件が許します（`engine._counter_knocked_out_attacker_awaiting`。決定の `context` と今の番のログで確かめる狭い例外。広げないでください）。
- カイリキーがワザのダメージで、ワザを使ったポケモンが「はんげき」のダメージで、そろってきぜつする（「はんげき」がなければきぜつしない）場合は、同時のきぜつか（p.324）が原典で決められない（C18。UNRESOLVED）ので、ワザの宣言の前（こんらんのコインの前）に `UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT` で止めます（`effects.counterattack_double_knockout_problem`）。止めるかは、ワザのダメージの候補（`AttackEffect.damage_profile`。コインのすべての結果）と状態を変えない計算（`preview_attack_damage`）で求めるので、コインの結果で受け付けるかが変わりません。ダメージの数がコイン・状態で変わるワザ・自分にダメージを与えるワザを加えたら `damage_profile` を上書きしてください（ダメージの目安に「×」「+」「−」（`damage_modifier`）のあるワザは、上書きしないと `NotImplementedError`。自分へのダメージは既定で「なし」なので、上書きしないと C18 を見落とす）。勝者を推測で決めないでください。`_apply_counterattack` でこの場合に来たら `RuntimeError`。
- 1 つのワザで 2 つ以上の「はんげき」がはたらく場合（C34・C35。複数のポケモンにダメージを与えるワザ）の順番は原典で決められません。今の対応カードでは起こらず、`finish_damage_elements` が 2 つ以上なら `RuntimeError` です。そのようなワザを加えるときは、宣言の前に止める処理（新しい `UNRESOLVED_…`）を加えてください。
- はたらいているか（`counterattack_power`・公開の `working_counterattack_power(state, pokemon_id)`）は、いちばん上のカード・ねむり・マヒ・こんらん（どくは関係しない）・v0.8 の `continuous.suppressors_of` から、問い合わせのたびに求めます。場所（ベンチ）は見ません。「とうめい」（`evasion_power`）とは別の型で探します（はたらく時点が違うので、1 つの関数にまとめないでください）。
- ほかの「ダメージを受けたとき」にはたらく特殊能力（［ショックボム］・［わるいねぞう］・［どくのたいえき］）・ワザ（「こうらがえし」は返すダメージがワザによるダメージ。p.89・p.321）を加えるときは、docs/post-damage-powers-v0.10.md 7 章を確かめてください。
- ゴーリキーの「からてチョップ」は `DamageReducedByOwnCounters(10)`（50 − 自分のダメージカウンターの数 × 10 が p.321 の 1 段階。0 以下なら 2 段階で計算を終える）、「じごくぐるま」は `DamageAndSelfDamage(20)`（相手に 60 → 自分に 20。コインなし。`SelfDamageOnTails` を流用しない）、カイリキーの「ちきゅうなげ」は説明文なし（効果のないワザ）です。からてチョップは印刷の文面ではなく最新の説明にしたがいます。
- ログは `counterattack`・`counterattack_skipped`・`drain_heal_skipped`。ログの監査（tests/log_audit.py）は v0.10 から、ワザごとに、その時点の場で相手のワザのダメージを、はたらいている「はんげき」を持つポケモンが受けたかを求め、そのワザの中に「はんげき」が 1 回あること・ダメージ以外の効果・きぜつより先にあること・「はんげき」のあとにダメージの要素がないこと・相手・量・ダメージ・きぜつの印・回復・ほかのきぜつを確かめ、ダメージを組み立て直します。ダメージを受けたときにはたらく特殊能力を加えたら、監査にも加えてください。ログだけで確かめられない制約は docs/architecture-v0.10.md 12.1。
- 書き出しは形式 9 のままです（v0.10 で状態の項目・形式を加えていない。監査の `LATEST_FORMAT` も 9）。エンジンが止める `UNRESOLVED_…` は 15 件（v0.9 までの 14 件は変えていない。R13・T19b・H4 を含む。コードのない T27・C34/C35 は起こらない）。
- ストレス実行（tools/stress_engine.py）は、カイリキーの組（`machamp`・`machamp_mixed`）で「はんげき」の場面を混ぜます。`POWER_USERS` の並びの最後にカイリキーを加えたので、カイリキーのいない組の操作（乱数の使い方）は v0.9 と同じです（18 組 × 40 seed の数が v0.9 の木と同じことを確かめた）。比較の駆動（tools/compat_driver.py）は変えていません。

## こんじょうときぜつの判定ときぜつの処理のあいだ（v0.11）

- サカキのカイリキー（PMCG6-061。ジム拡張第2弾）の「こんじょう」は `effects.PreventKnockOutOnHeads(remaining_hp=10)`（`PowerKey("PMCG6-061", 0)`）です。最新の説明・印刷の文面とも「使える」「使えない」なので、使用を宣言する特殊能力（`declared = True`）で、使うかは持ち主が決めます（p.311。p.100 の［にげこむ］の解説。G1・G10・A4。SUPPORTED）。自動的にはたらく形（`declared = False`）にしないでください。「ワザの途中の決定を保存できないから」などの理由で強制にしないでください。決められたとき（相手のワザによるダメージで「きぜつ」するとき）にしか使えないので、`UsePokemonPower` は `check_usable` が `POWER_NOT_USABLE_NOW`（共通の確認・`POWER_SUPPRESSED` のあと）。裁定は docs/guts-v0.11.md（G1〜G42・A4〜A6）、仕組みは docs/ko-prevention-v0.11.md、設計は docs/architecture-v0.11.md、確かめた結果は docs/v0.11-verification.md。第1弾のカイリキー（PMCG1-057。［はんげき］）は別のカードです。
- 使う時点は、ワザの要素（ダメージ・ワザのコイン・自分へのダメージ・「はんげき」・ダメージ以外の効果）をすべて処理したあと、きぜつの処理（トラッシュ・サイド・交代・勝ち負け）の前です（p.309「ワザを使っている最中に、…特殊能力の使用を宣言してはいけません」。G2）。`engine._finish_attack` が `_ko_prevention_offer` を聞き、使えるポケモンがいれば決定（`decisions.KO_PREVENTION`。`player` は持ち主（番でないプレイヤー）、`options` はそのポケモンの番号 1 つ、`min_choices` 0・`max_choices` 1、`resume` `"knock_out"`、`context` の `"attack"`・`"power"`）を出して止まり、`_resume_knock_out` → `_knock_out_after_attack`（v0.10 までの `_finish_attack` の本体）で続けます。いなければすぐに `_knock_out_after_attack`。段階・コマンド・保留中のリスト・汎用のイベントの仕組みを加えないでください。番のプレイヤー・番の番号は変えません。
- 決定を出す時点では乱数を使いません（コインの結果を事前に見せない。G12・G13）。選ばない（0 個）なら使わない（ログ `ko_prevention_declined`。コインなし）。選んだら宣言（`ko_prevention_declared`）→ 持ち主のコイン 1 枚（`flip_coins` の `source="power"`、`effect` は `PowerKey`）→「おもて」ならダメージを HP − 10（`ko_prevented`）、「うら」なら何もしない（`ko_prevention_failed`）。ダメージを 0 にしたり、カウンターをとりのぞく処理（`remove_damage_counters`）にしたりしないでください。答えのあとは、同じきぜつの判定で 2 度決めさせません（G14）。
- 使えるのは、相手のワザのダメージ（`deal_attack_damage` を通り、最終ダメージが 0 より大きく、受けるポケモンの持ち主がワザを使ったプレイヤーでない）で HP 以上になったポケモンだけです。どく（ポケモンチェック）・こんらんの 20・自分のワザ・「はんげき」の 10（特殊能力のダメージ）・ダメージスワップでは使えません（G3〜G7）。「きぜつを防ぐ能力だから」と、ほかのきぜつの経路（`_pokemon_check`・`_apply_counterattack`）に当てはめないでください。
- ダメージを受けるときのねむり・マヒ・こんらん（「すでに」）は、`deal_attack_damage` がダメージをのせる前に `AttackUse.ko_prevention_able`（ワザ 1 回の中だけの記録。状態に持たない）に記録します。どくは関係しません。かがくへんかガスは決定を出す時点で `continuous.suppressors_of`（`ko_prevention_suppressors`）を聞きます（判定を複製しない）。場所（ベンチ）は見ません。公開の問い合わせは `available_ko_prevention_power(state, pokemon_id)`。
- 「おもて」のポケモンは HP 未満なので、きぜつ・サイド・交代・勝ち負けに入りません。決定を待つ間だけ、HP 以上のポケモン（決定の対象と、同じワザで HP 以上になったワザを使ったポケモン）が場に残ることを不変条件が許します（`engine._ko_prevention_awaiting`。決定の形・ログは `_ko_prevention_decision_problems`。広げないでください）。
- 原典で決められない G37（使えるポケモンがワザのダメージで HP 以上になり、同じワザでそのポケモンに効果（特殊状態・入れ替え）を与える場合、「おもて」で残ったポケモンがその効果を受けるか）は、ワザの宣言の前（C18 の確認のあと、こんらんのコインの前）に `UnsupportedError`（`UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT`。`effects.ko_prevention_attack_effect_problem`）で止めます。ダメージのあとに相手に効果を与えるワザの実装は、効果の種類を `AttackEffect.opponent_effect_elements` で宣言してください（tests/test_guts_v0_11.py が実装の `attack_reaches` の呼び出しと照らす）。宣言を忘れると G37 を見落とします。
- 同じきぜつの判定でこんじょう（などきぜつするときに使える特殊能力）を使えるポケモンが 2 匹以上になる場合（G40・G16）は、今の対応カードでは起こらず `RuntimeError` です。ベンチ・複数のポケモンにダメージを与えるワザ、きあいのハチマキ（ネオ。範囲外）などのきぜつを防ぐ効果、「きぜつしたとき」の特殊能力（v0.12 の［ふしちょう］のほか）を加えるときは、順番を原典で確かめ、確かめるまでは宣言の前に止める処理（新しい `UNRESOLVED_…`）を加えてください。
- v0.10 の C18 は、こんじょうで解決したことにしていません（G39）。C18 の判定は、v0.11 から同じコインの結果でいっしょに起こるダメージの組（`DamageProfile.pairs()`。`outcomes` を書いた実装はその組）で確かめます（サカキのゴーリキーの「いちかばちか」は「おもて」と「うら」が同時に起こらない）。v0.10 までのワザは `outcomes` を書いていないので答えは同じです。コインで相手と自分へのダメージが入れかわるワザを加えたら `outcomes` を書いてください。
- サカキのワンリキーの「いかりのスーパーパンチ」は `CoinHeadsDamagePerOwnCounter(20)`（コインが「おもて」なら自分のカウンターの数 × 20。「ダメージを受けない」相手は `UNRESOLVED_PREVENTED_COIN_DAMAGE`。`prevented_coin_damage_problem` は `CoinFlipDamage.problem` から分けた関数）、サカキのゴーリキーの「いちかばちか」は `SelfDamageInsteadOnTails(100)`（コインが先。「うら」なら相手へのダメージの要素はなく自分に 100。`SelfDamageOnTails`（でんげき）を流用しない）、「じごくがため」は `CoinBonusDamageAndParalyze(bonus=20)`、サカキのカイリキーの「ハリケーンパンチ」は `CoinFlipDamage(coins=4, damage_per_heads=30)` です。裁定は docs/giovanni-machamp-line-v0.11.md（L1〜L14）。
- 書き出しは形式 9 のままです（決定は既存の `decision` の項目で表す）。形式 1 は再開先 `"knock_out"` の決定があると `ValueError`。監査の `LATEST_FORMAT` も 9。エンジンが止める `UNRESOLVED_…` は 16 件（v0.10 までの 15 件は変えていない。R13・T19b・H4・C18 を含む。コードのない T27・C34/C35・G40 は起こらない）。
- ログの監査（tests/log_audit.py）は v0.11 から、ワザごとに、相手のワザのダメージを受けたときの特殊状態・ガス・HP 以上かを組み立て直し、使えるのに答えのないきぜつ・答えの重複・宣言とコインと結果の順番と一致・残り HP 10・「おもて」のきぜつ・「うら」と使わないときの生存・使えないのに答えたことを確かめ、`ko_prevented` をダメージの組み立て直しに含めます。きぜつの判定で使う効果を加えたら、監査にも加えてください。決定の中身はログにないので、答えとの対応はエンジンの不変条件で確かめます（docs/architecture-v0.11.md 12 章）。
- ストレス実行（tools/stress_engine.py）は、サカキのカイリキーの組（`giovanni`・`giovanni_mixed`）で「こんじょう」の場面を混ぜます。`POWER_USERS` の並びの最後にサカキのカイリキーを加えたので、サカキのカイリキーのいない組の操作（乱数の使い方）は v0.10 と同じです（20 組 × 40 seed の数が v0.10 の木と同じことを確かめた）。比較の駆動（tools/compat_driver.py）は変えていません。

## ふしちょう・ほのおのかべと、きぜつしたあと・番をまたぐワザの効果（v0.12）

- R団のファイヤー（PMCG5-020。ジム拡張第1弾。依頼の候補の id PMCG5-017 は別のカード）の「ふしちょう」は `effects.ReturnToHandOnKnockOut`（`PowerKey("PMCG5-020", 0)`）、「ほのおのかべ」は `effects.DamageAndRetaliation(10)`（`AttackKey("PMCG5-020", 0)`）です。どちらも p.82 の最新の説明にしたがい、印刷の文面（kyuura の写し）は照合にだけ使います。裁定は docs/phoenix-v0.12.md（P1〜P35）・docs/rocket-moltres-v0.12.md（カードの照合・W1〜W30）、仕組みは docs/post-knockout-powers-v0.12.md・docs/temporary-attack-effects-v0.12.md、設計は docs/architecture-v0.12.md、確かめた結果は docs/v0.12-verification.md。
- 「ふしちょう」は使用を宣言する任意の特殊能力（`declared = True`。p.311・p.82。SUPPORTED）です。自動的にはたらく形にしないでください。v0.11 の「こんじょう」の処理（`_ko_prevention_offer`・`KO_PREVENTION`・`knock_out`）を流用しないでください（条件は「きぜつ」したとき、時点はトラッシュのあと。docs/post-knockout-powers-v0.12.md 1 章）。場にいるときの `UsePokemonPower` は `check_usable` が `POWER_NOT_USABLE_NOW`。
- 使えるか（いちばん上のカード・きぜつするときのねむり・マヒ・こんらん・かがくへんかガス）は、きぜつの処理（`_knock_out`。トラッシュ）の前に `engine._post_knockout_candidates` で求めます（ワザのあと `_knock_out_after_attack` とポケモンチェック `_pokemon_check` の 2 か所）。トラッシュのあとの場の状態やログから、過去の特殊状態・抑止を判断しないでください。ガスは `continuous.suppressors_of` を聞きます（判定を複製しない）。きぜつの原因を問いません（どくでも、自分の番の「はんげき」でも使える）。
- 候補（(持ち主, カードの uid, カード id, パワーの位置)）は、サイドを取る決定の `context` の `"post_knockout"` で運び（候補がなければ決定の形は v0.11 と同じ）、`_next_prize_or_judge` が、勝ち負けの判定で対戦が続くなら、バトル場に出す前に決定 `decisions.POST_KNOCKOUT_POWER`（持ち主・選べるものはトラッシュのそのカード・0〜1 個・再開先 `"post_knockout"`・`context` の `"power"` と、ポケモンチェックの中なら `"then"`）を出します（`_offer_post_knockout` → `_resume_post_knockout` → `_promotions_after_judge`）。対戦が終わるなら決めさせません。段階・コマンド・汎用のイベントの仕組みを加えないでください。
- 「ふしちょう」とサイド・勝ち負け・バトル場に出すの順番は原典で決まらない（P27・P28・P30）が、どの順番でも結果が変わらないので、「サイド → 勝ち負けの判定 →（続くなら）ふしちょう → バトル場に出す」に正規化しています（ルールの裁定ではない。docs/post-knockout-powers-v0.12.md 3 章）。勝ち負けより「ふしちょう」が先だと決めないでください。サイド・手札・勝ち負け・手札からバトル場に出すことに関わるカードを加えるときは、この正規化が成り立つかを見直してください。
- トラッシュのカードを手札に加えるのは `zones.return_discard_to_hand` だけです（v0.9 のエナジーへんかんも使う）。使ったら、そのカード（同じ uid）だけを手札に加え（ついていたエネルギー・トレーナーはトラッシュに残る）、ログは宣言 `post_knockout_power_declared` のすぐあとに `return_to_hand`（`revealed`）。手札にもどしても、きぜつしたことに変わりはなく、相手はサイドを取ります（p.82）。
- ガスの発生源がいっしょにきぜつする（P19）・候補が 2 つ以上（P32）は、今の対応カードでは起こらず `RuntimeError` です（W24・`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT` が先に止める）。ベンチ・複数のポケモンにダメージを与えるワザ、ほかの「きぜつしたとき」の特殊能力を加えるときは、原典で確かめるまで宣言の前に止める処理を加えてください。
- 「ほのおのかべ」の効果は持続する効果 `state.Retaliation`（発生源・番・`attack_index`・`amount`。自分自身に与え、`active_turn` = 与えた番 + 1）で、`PokemonInPlay.persistent_effects` に持ちます（v0.4b と同じ置き場所・消える契機・ログ）。ワザ 1 回の中の値・ログから求め直す形にしないでください。はたらくのは `persistent.retaliation`（`active_turn` が今の番）のときだけで、次の相手の番の終わりに消えます（`_end_turn`。p.89 の「こうらがえし」の解説。SUPPORTED）。ベンチにもどる（ふきとばし）・きぜつで消え、復活しません。特殊状態・かがくへんかガスでは止まりません。
- 判定は `deal_attack_damage` が、相手のワザのダメージ（最終ダメージ > 0、受けるポケモンの持ち主がワザを使ったプレイヤーでない）でダメージをのせる直前に `AttackUse.retaliations` に加えるだけで、与えるのは `finish_damage_elements`（v0.10 の「はんげき」と同じ時点。p.89）の `_apply_retaliation` です。「ほのおのかべ」の 10 は R団のファイヤーのワザによるダメージ（p.82「弱点・抵抗力の影響を受けます」・p.89。SUPPORTED）なので、`retaliation_use`（ワザを使ったのは効果を持つポケモン、ワザは効果を与えたワザ）で `deal_attack_damage` を通し、弱点・抵抗力・ディフェンダー・「とうめい」を計算し、受けたカイリキーの「はんげき」をはたらかせます。v0.10 の `_apply_counterattack`（特殊能力のダメージ）を流用しないでください。ダメージが増えたことから判定しないでください。
- R団のファイヤーがそのダメージできぜつしても与えます。ワザを使ったポケモンがすでに HP 以上なら与えず `retaliation_skipped`。「ほのおのかべ」できぜつしたワザを使ったポケモンの回復は処理せず（`drain_heal_skipped`）、相手への効果（ふきとばし）は処理します（v0.10 の `_counter_knocked_out_attacker_awaiting` の例外を「ほのおのかべ」のダメージにも当てはめた）。ワザを使ったあと相手の「はんげき」で HP 以上になったら効果を与えず `persistent_effect_skipped`。
- 「ほのおのかべ」のダメージで、番のプレイヤーのワザを使ったポケモン（サカキのカイリキー）が HP 以上になったら「こんじょう」を使えます（`_ko_prevention_offer` は v0.12 から番のプレイヤーも見る。記録 `ko_prevention_able` は `_apply_retaliation` がきっかけのワザと共有する）。対応カードでは W24 が先に止めるので起こりません（テスト専用の効果で確かめた）。
- R団のファイヤーがワザのダメージで、ワザを使ったポケモンが「ほのおのかべ」のダメージで、そろってきぜつしうる場合（W24。v0.10 の C18 と同じ問い）は原典で決められないので、ワザの宣言の前（G37 の確認のあと、こんらんのコインの前）に `UnsupportedError`（`UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`。`effects.retaliation_double_knockout_problem`）で止めます。同じコインの結果でいっしょに起こるダメージの組（`DamageProfile.pairs()`）と `preview_attack_damage` で求め、「ほのおのかべ」で「はんげき」がはたらく 10 も数えます。勝者を推測で決めないでください。「こんじょう」で解決したことにしないでください。
- 1 つのワザで「はんげき」と「ほのおのかべ」が合わせて 2 つ以上はたらく場合（C34・C35 と同じ問い）は `RuntimeError` のままです。ワザの途中の決定（`push_attack_decision`）の前に、与えていない「ほのおのかべ」が残っていても `RuntimeError` です。
- 書き出しは形式 9 のままです（`persistent_effects` の種類 `retaliation` に `attack_index`・`amount` を加えた。決定は既存の `decision`）。形式 1 は再開先 `"post_knockout"` の決定・`"post_knockout"` を持つサイドを取る決定があると `ValueError`。監査の `LATEST_FORMAT` も 9。エンジンが止める `UNRESOLVED_…` は 17 件（v0.11 までの 16 件は変えていない）。未解決の裁定は 22 件（コードのない T27・C34/C35・G40・P19・P32 を含む）。
- 不変条件は、「ふしちょう」の決定・候補（`_post_knockout_decision_problems`・`_post_knockout_candidate_problems`。カードが持ち主のトラッシュにあり、ログの直前のきぜつのカード・登録・ガス）と、`Retaliation`（`_retaliation_problems`。登録されたワザと量）を確かめます。テストで効果を置くときは `build_test_state` の `"retaliation"`（効果を与えた番。今の番 − 1）を使ってください。
- ログの監査（tests/log_audit.py）は v0.12 から、きぜつごとに「ふしちょう」を使えるか（特殊状態・ガスを組み立て直す）と答え・時点・`return_to_hand` を、「ほのおのかべ」の効果（追加・期限・消去）と返すダメージ（量・弱点・抵抗力・相手。別の窓 `ret` で数える）を確かめ、`return_to_hand` を手札・トラッシュの組み立て直しに含めます。きぜつしたあとに使う効果・番をまたぐ効果を加えたら、監査にも加えてください。
- ストレス実行（tools/stress_engine.py）は、R団のファイヤーの組（`moltres`・`moltres_mixed`）で「ふしちょう」の決定と「ほのおのかべ」の場面を混ぜます。`POWER_USERS` の並びの最後に R団のファイヤーを加えたので、R団のファイヤーのいない組の操作（乱数の使い方）は v0.11 と同じです（22 組 × 40 seed の数が v0.11 の結果と同じことを確かめた）。比較の駆動（tools/compat_driver.py）は変えていません。

## こうらがえしと量が受けたダメージで決まる「相手の番ではたらく効果」（v0.13）

- わるいカメール（PMCG4-021。第4弾ロケット団）の「こうらがえし」は `effects.ReturnReceivedDamage`（`AttackKey("PMCG4-021", 1)`）、「おうふくびんた」は既存の `CoinFlipDamage(coins=2, damage_per_heads=10)`、進化元の第4弾のゼニガメ（PMCG4-018）の「こうらアタック」は `DAMAGE_ONLY` です。p.89 の最新の説明にしたがい、印刷の文面（kyuura の写し）は照合にだけ使います。裁定は docs/shell-attack-v0.13.md（S1〜S49）、カードの照合は docs/dark-wartortle-v0.13.md、仕組みは docs/variable-retaliation-v0.13.md、設計は docs/architecture-v0.13.md、確かめた結果は docs/v0.13-verification.md。わるいカメックスは PMCG4-024（範囲外。PMCG4-008 はわるいアーボック）。
- こうらがえしの効果は v0.12 の `state.Retaliation` に、与えるダメージの決め方 `basis`（`RETALIATION_FIXED`（ほのおのかべの 10）・`RETALIATION_RECEIVED`（受けたダメージ））を明示した値です（量 `amount` は `fixed` のときだけ。`__post_init__` が組を確かめる）。固定と可変を別のクラス・ワザごとの個別の処理にしないでください。量の決め方を特別な値（0 や負の数）に隠さないでください。種類 `kind` は決め方から求める property（`fixed` は v0.12 と同じ `"retaliation"`、`received_damage` は `"retaliation_received_damage"`）で、クラスから `Retaliation.kind` を読まないでください。ほのおのかべの値・ログ・書き出しは v0.12 と同じです。
- 返す量は、効果を持つポケモンが受けたダメージ（相手のワザのダメージの要素の最終ダメージ。p.321 の 1〜7 段階のあと。HP で上限をつけない）です。元のワザの基本となるダメージ（ダメージの目安の数字）にしないでください（p.89「2倍のまま相手にダメージが返ります」「100ダメージを受けたらそのまま100」）。受けたダメージは `deal_attack_damage` がダメージをのせる直前に `PendingRetaliation.received`（ワザ 1 回の中の値）に記録します。「直前に受けたダメージ」を状態の項目にしたり、ログを読み直して求めたりしないでください。基本となるダメージは `Retaliation.base_damage(received)` で求めます。
- 返すダメージは「こうらがえし」のワザによるダメージ（p.321「8」の例そのもの。CONFIRMED）で、v0.12 と同じ `_apply_retaliation`（`retaliation_use` で `deal_attack_damage`）を通します（弱点・抵抗力・ディフェンダー・「とうめい」・受けたカイリキーの「はんげき」）。返す時点は `finish_damage_elements`（相手のワザのダメージの処理のあと・ダメージ以外の効果の前。p.89 の「ふきとばし」「スターブーメラン」の例）のままです。ダメージ以外の効果は返しません。
- ワザを使ったポケモンが返すダメージで HP 以上になったら、そのポケモン自身への効果は各ワザの実装が処理しません（p.89 のスターブーメランの例。一般化は SUPPORTED。`_skip_heal_of_knocked_out_attacker`・`DamageAndRetaliation`）。エンジンで一律に効果を省く形にしないでください。カスミのヒトデマン（スターブーメラン）は未実装で、tests/test_shell_attack_v0_13.py のテスト専用の模擬のワザ（`StarBoomerang`。カードを動かさず時点を記録する）で順番を確かめています。
- わるいカメールとワザを使ったポケモンがそろってきぜつしうる場合（S37）は v0.12 の W24 と同じ問いなので、同じ `UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`（`effects.retaliation_double_knockout_problem`）で止めます。新しい裁定 ID・コードを加えないでください。返す量はダメージの組（`DamageProfile.pairs()`）ごとに、わるいカメールが受ける最終ダメージから求めます（コインの結果で受け付けるかが変わらない）。返す量が大きいので止まる場面が多く、ハリケーンパンチは必ず止まります（番のプレイヤーの「こんじょう」（S46）は対応カードでは起こらない）。勝者を推測で決めないでください。
- 返すダメージで別の効果がはたらくこと（連鎖）は番の進み方から起こらない（返すダメージを受けるのは番のプレイヤーのポケモンで、その効果は持ち主の相手の番だけにはたらく。S45）ので、起こったら `_apply_retaliation` が RuntimeError で止めます。回数の上限（再帰の深さ）で止める形にしないでください。1 つのワザで効果を持つポケモンが 2 回以上ダメージを受ける場合（S7）は C34/C35 と同じ問いで、RuntimeError のままです。
- 不変条件（`engine._retaliation_problems`）は、登録された実装の `retaliation_terms()` と効果の `(basis, amount)` を照らします。返す効果のワザを加えたら `retaliation_terms` を書いてください。テストで効果を置くときは `build_test_state` の `"retaliation_received"`（効果を与えた番。ワザの位置 1）を使います。
- 書き出しは形式 9 のままです（`persistent_effects` の種類 `retaliation_received_damage` は `attack_index` だけ。量は書かない）。監査の `LATEST_FORMAT` も 9。エンジンが止める `UNRESOLVED_…` は 17 件、未解決の裁定は 22 件のまま（v0.13 で加えていない）。
- ログは新しいイベントを加えず、`retaliation` に `basis`・`received_damage` を加えました（こうらがえしのときだけ）。ログの監査（tests/log_audit.py）は v0.13 から、受けたダメージがきっかけのダメージのログの最終ダメージと同じこと・基本となるダメージ・効果の種類が登録と合うこと・状態の効果の種類がログで与えた種類と同じことを確かめます。量の決め方の違う返す効果（クロスカウンターなど）を加えたら、`basis`・監査・`retaliation_terms` を合わせて加えてください。
- ストレス実行（tools/stress_engine.py）は、わるいカメールの組（`wartortle`・`wartortle_mixed`）を最後に加えました。わるいカメールはポケモンパワーを持たないので `POWER_USERS` は変えていません（ほかの組の操作は v0.12 と同じ。24 組の数が v0.12 の結果と同じことを確かめた）。`_observe_moltres` は「ほのおのかべ」のログだけを、`_observe_shell` は「こうらがえし」のログを確かめます。比較の駆動（tools/compat_driver.py）は変えていません。

## 汎用のイベント・効果の解決の試作（v0.14）

- （v0.15b で、プロトタイプは本番の内部の部品 `kyuura_engine/resolution/` になった。下の「解決の基盤の本番への統合（v0.15）」。この節は v0.14 の時点の約束で、v0.15 の節が優先する。）
- `experiments/event_kernel/` は本番ではありませんでした（設計の試作。docs/event-model-v0.14.md。v0.15b で本番の部品になり、v0.16d で v0.14 の名前の互換の層ごと外した）。本番（`kyuura_engine/`）の規則（「汎用のイベントの仕組み（購読・発行）にしない」など）は v0.14 では変えていません。
- プロトタイプは v0.13 の状態の型・書き出しの形式 9・ログ・決定の形をそのまま使い、ワザ・番の終わりと、再開先 `attack`・`knock_out`・`post_knockout`・`take_prize`・`promote_active` の決定だけを処理します（ほかのコマンドは `kyuura_engine.apply_command` に渡す。`flow.owned`）。本番の非公開の関数を 14 直接呼んでいる（docs/event-prototype-verification-v0.14.md 1 章）ので、それらの意味を変えたら比較のテストで確かめてください。
- tests/test_event_kernel_v0_14.py・tests/test_event_kernel_games_v0_14.py は、同じ入力で本番とプロトタイプの結果（形式 9 の全体・乱数の指紋・拒否の例外とコード）が同じことを確かめます。本番のワザ・ダメージ・きぜつ・番の終わりの動きを変えたら（カードを加えたときも）失敗することがあります。そのときは、プロトタイプの対応表（`programs.BUILDERS`・`catalog` の定義と対応表）を合わせるか、比べない範囲を docs に書いてください。比較のテストの期待を本番に合わせて弱めないでください。
- 窓の順番・枠の表（`events.SPAWNS`）・問いの表（`questions.QUESTIONS`）は、原典の処理の順番と裁定を表します。表にない連鎖・問いは `RuntimeError` で止めます。回数の上限・購読の順番・優先度の数値で処理の順番を決める形にしないでください（問いの `priority` は v0.13 の確認の順番を写したもので、2 つ以上の問いに当たったときにどのコードで止めるかだけを決める）。
- 先読みの `derived` は、状態の複製の上で、コインと決定の選び方のすべての結果を試し、乱数を使いません（複製の乱数を `Oracle` に差しかえ、コイン以外の乱数を使ったら止める）。比べるための `legacy` は v0.13 の止める関数をそのまま呼びます。
- C 段階の比較は `python3 tools/event_kernel_compare.py`（ふだんのテストで走らせない）。変異試験と保守性の測定（E4）の方法・結果は docs/event-prototype-verification-v0.14.md、移行の判断（PARTIAL）・段階・中止の条件は docs/event-migration-plan-v0.14.md。

## 解決の基盤の本番への統合（v0.15）

- 確認（`checks.py`）と状態を変える共通の手続き（`procedures.py`）は、v0.13 の経路と解決の基盤の両方が使います（v0.15a。docs/integration-dependencies-v0.15a.md）。どちらも `engine.py` を読み込まないでください。共通の部品を変えると両方の経路が同じように変わるので、同じ木の中の比較では見つかりません。固定した前の版の木と別のプロセスで比べてください（`tools/engine_lockstep.py`。C 段階。ふだんのテストで走らせない）。
- 解決の基盤は `kyuura_engine/resolution/` です（v0.15b。docs/kernel-integration-v0.15b.md）。`engine.py` を読み込まないでください（依存の向きは engine → resolution → checks・procedures。tests/test_kernel_integration_v0_15.py の `DependencyTest` が確かめる）。v0.14 の名前の互換の層（`experiments/event_kernel/__init__.py`）は v0.16d で外しました（テスト・道具は `kyuura_engine.resolution` と `engine` の内部の入口を直接使う）。互換のための別名（`sys.modules` への登録）・コードの複製を戻さないでください（`DependencyTest.test_no_copy_of_the_kernel_remains`）。
- （v0.16b で経路（`engine.Route`・`DEFAULT_ROUTE`・`apply_command_via`・`resolution.handles`）と v0.13 の経路を外した。下の「旧経路の撤去と解決の基盤の一本化（v0.16）」。）公開の `apply_command(state, command)` の呼び方を変えないでください。解決の設定（先読みの方法・効果の定義の対応表）を選ぶときは内部の入口 `engine.apply_command_with(..., preflight=..., catalog=...)`（tests/helpers.py の `apply_kernel`）か `apply_command_traced` を使い、グローバルな可変フラグ・処理の途中で書きかえる値で切り替えないでください。
- 解決の基盤が処理するのは、ワザ・番の終わり（`resolution.COMMANDS`）と、再開先が `attack`・`knock_out`・`post_knockout`・`take_prize`・`promote_active`（`resolution.RESUMES`）の決定への答えです。トレーナーの決定（`trainer`）への答えは engine.py（`_answer_decision` → `_resume_trainer`）です。`ResolveDecision` をすべて解決の基盤に送らないでください。製品の登録表にワザの実装を加えたら、`BUILDERS` に要素の並びを加えてください（tests/test_kernel_integration_v0_15.py が製品の登録表のすべてを確かめる。製品のワザに v0.13 の約束のアダプタを使わない）。
- 原典で決められない場合に止める理由の文は、`effects` の共通の関数（`prevented_coin_damage_error`・`evaded_effect_coin_error`・`counterattack_double_knockout_error`・`retaliation_double_knockout_error`・`ko_prevention_attack_effect_error`）で作ります（解決の基盤と v0.13 の止める関数が同じ関数を使う）。解決の基盤は文に書く値を枠の値（`FrameState` の `origin`・`applied`・`evaded`）から読み、解決の記録（`Trace`）からは読みません（比較のテスト・参照データ・道具は理由の文も比べる）。
- 処理の途中の故障を注入して確かめるテストは、解決の基盤の内部（`codec.push_decision`・`programs.APPLY_CONDITION`・`kernel.ACTIONS`・`GameState.add_event` など）を差しかえます（tests/test_kernel_integration_v0_15.py の `KernelAtomicityTest`・`KernelGuardTest`。v0.16b で v0.13 の経路を差しかえるテストもこの形に移した）。
- 宣言の前の先読み（v0.15c。docs/preflight-optimization-v0.15c.md）の方法は `derived`（標準。実際の処理を先に行い、記録したコインの並び以外の結果だけを状態の複製の上で試す）・`derived_full`（v0.14 の方法。比べる基準）・`legacy`（v0.13 の止める関数）です。試さないのは、先読みの範囲（`Resolution.horizon` まで）でコインを投げず・決定を出さず・コイン以外の乱数を使わず・例外もないときだけです。条件を緩めないでください。範囲の終わり（`_finish_attack` の `res.horizon()`）は、複製の上の処理が `DryRunComplete` で止まる所と同じにしてください。
- 複製の上で決定に答えるときは、決定に合うすべての答え（`programs.all_answers`。選ぶ数・選ぶもの・順番）を試します。代表を選んで同じものとみなさないでください（v0.14 のエナジーへんかんは代表だけで、見落としうる）。エナジーへんかんの 0 枚（H4）は決定の答えのときに止めるものなので試しません。
- 試す結果の数は `preflight.MAX_BRANCHES`（4,096）までです（`derived` の `siblings` も実際の処理の結果を 1 つと数える。v0.16c で直した）。超えたら途中までの結果を使わず、`v013_checks.VERIFIED`（v0.13 の 24 種類。v0.16c で `preflight.LEGACY_VERIFIED` から移した）なら v0.13 の止める関数で確かめ、ほかは `UNSUPPORTED_PREFLIGHT_LIMIT` で拒否します。ワザの実装を加えても `VERIFIED` に自動では加えないでください。
- 実際の処理の乱数の前に置く記録（`preflight.RecordingRandom`）は、範囲の終わりと `finally` で外します。返す状態の乱数は元の `random.Random` です（tests/test_preflight_v0_15c.py が確かめる）。
- 解決の基盤の独立した不変条件（v0.15d。tests/test_kernel_invariants_v0_15.py の 1〜12。docs/event-integration-verification-v0.15d.md 4 章）は、解決の記録と v0.13 の公開の問い合わせで、対戦の 1 歩ごとに確かめます。窓・枠の種類・送る効果・決定の再開先を加えたら、不変条件（窓の順番・枠の表・二重の処理・決定を待つ状態）も見直してください。解決の記録（`Trace`）を結果の判断に使わないでください（不変条件 12 が、記録をとらない処理と結果・拒否を比べる）。
- 解決の基盤・先読み・振り分けを変えたら、最終のコードで、固定した前の版（v0.13 の `8facf3a`・v0.15 の `aa551ab`）と別のプロセスで比べます（`tools/engine_lockstep.py`。v0.16b から同じ木の中の v0.13 の経路はない）。前の段階の比較の結果を、変えたあとのコードの確かめとして使わないでください。

## 旧経路の撤去と解決の基盤の一本化（v0.16）

- 撤去の前の監査（v0.16a）は docs/legacy-removal-audit-v0.16a.md です。参照の分類（A〜F）・テスト専用のワザ 21 種類・採用した方式（v0.13 の約束で書いたワザの実装を KERNEL の枠の中で処理する明示的なアダプタ）を書いています。
- 固定した前の版と比べるときは、`python3 tools/engine_lockstep.py tree --commit <コミット> --out <空の場所>` で木を展開し、`record`（別のプロセスで、その木の公開の API だけを使う）と `compare` で比べます。許す差は、決定への答えの `WRONG_PHASE` の理由の文の段階の名前の並びだけです（`compare` が文そのものを確かめて数える）。ほかの理由の文の違いを無視する変更をしないでください。
- tests/fixtures/legacy_reference_v0_15.json は、旧経路（v0.13 の処理）の結果の参照データです（v0.16a。tests/legacy_reference.py）。旧経路を外したあとも、盤面を直接作る比較のテストは、KERNEL の結果をこの記録と比べます。今の版から作り直さないでください（旧経路がない木では作れない。作り直すと v0.13 との比較ではなくなる）。盤面の指紋が記録と違うと失敗するので、記録した呼び出しのテストの盤面・呼び出しの順番を変えるときは、変えた理由と、同じ性質を確かめる別のテストを docs に書きます。
- v0.16b で v0.13 の経路を外しました（docs/kernel-consolidation-v0.16b.md）。ワザ・番の終わり・きぜつのあとの決定を処理するのは解決の基盤（`kyuura_engine/resolution`）だけです。v0.10〜v0.13 の節に出てくる `engine._finish_attack`・`_ko_prevention_offer`・`_post_knockout_candidates`・`_after_knockouts`・`_end_turn`・`_pokemon_check`・`effects._apply_counterattack`・`_apply_retaliation`・`AttackUse.counterattacks` などは、docs/kernel-consolidation-v0.16b.md 5 章の表の新しい場所（`resolution.flow`・`resolution.kernel`）で読みかえてください（規定・順番・ログは同じ）。旧経路の関数を戻さないでください（tests/test_kernel_integration_v0_15.py の `EntryTest` が確かめる）。
- 製品のワザは要素の並び（`programs.BUILDERS`）で加えます。v0.13 の約束（`AttackEffect.resolve`・`resume`）で書いた実装（テスト・外の登録表）は、解決の基盤の枠の中のアダプタ（`resolution/contract.py`）で処理します。補助関数（`deal_attack_damage`・`damage_opponent_active`・`attack_reaches`・`finish_damage_elements`・`decisions.push_attack_decision`・`_require_not_evaded`）は解決の基盤の部品（`kernel.deal_damage`・`reaches`・`fire_pending`・`AttackRun.suspend`）に委ねる入口で、枠の外（`AttackUse.runtime` がない）で呼ぶと `RuntimeError` です。単体テストは `resolution.open_attack` で枠を開きます。補助関数に処理を書き戻したり、解決の基盤を通らずにダメージをのせる口を作ったりしないでください。
- アダプタで処理する実装の宣言の前の確認は、実装の宣言（`problem` と v0.13 の止める関数。`v013_checks.check`。解決の記録の方法は `contract`）だけで、先読みの方法によりません（`resolve` を複製の上で呼ばない）。要素の並びも v0.13 の約束の `resolve` もない実装は、状態を変える前に `UNSUPPORTED_ATTACK` で拒否します（`contract.program_for`。黙って効果のないワザにしない）。標準の実装の部分型の既定の `resolve`・`resume` は、最も近い対応表の型の要素の並びを枠の中で処理します。
- v0.13 の止める関数（`effect.problem` → こんらんのダメージ → C18 → G37 → W24/S37 を同じ順番で呼ぶ判定）は、限定的な互換の部品 `kyuura_engine/resolution/v013_checks.py`（`check`・`VERIFIED`・`MODES`）だけが使います（v0.16c。docs/preflight-consolidation-v0.16c.md）。使い道はアダプタの実装（方法 `contract`）・試す結果の数が上限を超えたときの `VERIFIED` の型（`legacy_after_limit`）・比べるための先読みの方法 `legacy` の 3 つだけで、`flow._use_attack` から呼びます。先読み（`preflight`）・解決の基盤の処理・アダプタから読み込まないでください（tests/test_preflight_consolidation_v0_16c.py の `DependencyTest`）。上限を超えたときの扱い（フォールバック）を、止める関数を外すためだけに変えないでください（外す条件は docs 6 章）。
- 先読みの上限の前後（1・2・16・4,096・4,097 以上・8,192 通り）は tests/test_preflight_consolidation_v0_16c.py の `BranchLimitBoundaryTest` が確かめます。上限を超えたら、途中までの結果で当たった問い・当たらなかったことを答えに使わないでください。製品のワザで試す結果の数のいちばん多い場合（こんらんのエナジーへんかんで 1 + 57² = 3,250）が上限に届かないことは `ProductBoundTest` が確かめます。決定の選択肢が増えるワザ・コインの多いワザを加えたら、docs 3 章の上界を見直してください。
- 決定への答えを拒否する理由の文（`WRONG_PHASE`）の段階の並びは `decisions.DECISION_PHASE_ORDER`（段階の定義の順）です（v0.16d。v0.15 までは `frozenset` の並びで、プロセスごとに変わっていた）。理由の文に集合の並びを書かないでください。固定した v0.13・v0.15 との比較では、この並びの差だけを `wrong_phase_order_only` として数えます（docs/legacy-test-migration-v0.16d.md 5 章）。
- 移したテストの対応表・重複する処理の調査・互換の層を外した理由は docs/legacy-test-migration-v0.16d.md です。v0.13 の約束の補助関数・実装の `resolve` を直接呼ぶテストは、`resolution.open_attack` で枠を開いてください（枠の外の `RuntimeError` で、確かめたい理由と違う所で通ってしまう。v0.16d で 1 件直した）。故障を注入するテストは、注入した誤りそのものが出たことを確かめてください。
- 最終監査（v0.16e。版 0.16.0）は docs/kernel-consolidation-verification-v0.16e.md です。固定した v0.13（`8facf3a`）・v0.15（`aa551ab`）と、別の木・別のプロセスで 2,560 対戦・350,533 歩を比べて食い違い 0（許した差は `WRONG_PHASE` の段階の並び 202 件）。解決の基盤・先読み・振り分け・アダプタ・`v013_checks` を変えたら、同じ比較（`tools/engine_lockstep.py`。2 章の手順）と変異試験（5 章の 34 の変異）をやり直してください。

## 実カードによる解決の基盤の拡張性の実証（v0.17）

- 新しいカードの効果は、解決の基盤の効果の定義（`resolution/catalog.py`）とワザの要素（`resolution/programs.py` の `BUILDERS`）で加えます。v0.13 の約束（`AttackEffect.resolve`・`resume`）で書かないでください（v0.17 の型はどれも上書きしていない。tests/test_existing_elements_v0_17a.py・tests/test_rocket_snorlax_v0_17b.py が確かめる）。v0.17 から加えた実装の型は `v013_checks.VERIFIED` に入れず、tests/helpers.py の `ATTACK_TYPES_SINCE_V0_17` に加えます（一覧を数えるテストはそこから数える）。
- 既存の要素だけで加えたカード（v0.17a）: モンジャラ（PMCG1-007。しめつける `ParalyzeOnHeads`・どくのこな `PoisonOpponent`）、サカキのニャース（PMCG6-063。ねこノミ `ConfuseOnHeadsWithoutDamage` = 要素 `Status(CONFUSION, local_coin=HEADS)` だけ、ねこキック `DamageOnly`）。新しい裁定はない（docs/card-implementation-v0.17a.md）。
- R団のカビゴン（PMCG6-073）の「わるいねぞう」は `effects.CounterattackDamageWhileAsleep(amount=20)`（`PowerKey("PMCG6-073", 0)`）で、はんげきと同じ窓・同じ処理（`kernel.power_damage_to_damage_source`）です。効果の定義 `catalog.RESTLESS_SLEEP` は `requires=frozenset({"sleep"})`（その特殊状態のときだけはたらく）で、`disabled_by` は空です。通常の特殊状態の抑止（`BLOCKING_CONDITIONS`）を当てはめないでください。特殊状態の条件は `catalog.blocked_by_status`（`disabled_by` と `requires`）だけで判定し、カードごとの分岐にしないでください。v0.13 の問い合わせ（`PowerEffect.is_working`。ログの監査が使う）は `works_with` で同じ条件を表します。裁定は docs/rocket-snorlax-v0.17b.md（Z1〜Z30）。
- 「わるいねぞう」の 20 は特殊能力によるダメージです（p.245。CONFIRMED）。弱点・抵抗力を計算するかは原典で決まらない（Z9）ので、`ignores_weakness_resistance = False` の特殊能力のダメージで、受けるポケモンの弱点・抵抗力が与えるポケモンのタイプなら、コードのない問い `power_damage_weakness_resistance` で止めます（R団のカビゴンは無色で、今のカードでは起こらない）。はんげきは `ignores_weakness_resistance = True`（「弱点・抵抗力」に関係なく）。そろってのきぜつ（Z13）は C18 と同じ問い・同じコード `UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT` で、理由の文は特殊能力の名前とページ（`effects.power_name_and_page`。はんげきは v0.16 までと同じ文）です。新しいコードにしないでください。
- 「たおれこむ」は `effects.DamageAndSelfSleep`（`AttackKey("PMCG6-073", 0)`。要素の並び `Damage(OPP)` → `Status(SLEEP, target=SELF, after_damage="damage")`）です。要素 `Status` の `target`（`OPP`・`SELF`）と `after_damage`（「ダメージを与えた後」の効果の、もとのダメージの要素の名前）は汎用の項目で、カードごとの要素を加えないでください。自分への効果も `reaches` で「とうめい」を評価し、対象が HP 以上なら飛ばします（自分がこんじょうを使える場合は G37 と同じ問いでコードのない `ko_prevention_self_effect`。今のカードでは起こらない）。
- 「ダメージを与えた後、…」の効果で、そのダメージの要素がダメージを与えなかった（`DamageResult.dealt` が 0。ディフェンダーで 0・「ダメージを受けない」状態・「とうめい」）ときに効果を与えるかは原典で決まらない（Z23）ので、宣言の前に `UNRESOLVED_EFFECT_AFTER_NO_DAMAGE`（問い `effect_after_no_damage`。優先度 10）で止めます。「ダメージを与えた後」の効果を加えるときは `after_damage` を書いてください。成功を仮定するテストを書かないでください。
- キョウのベトベトン（PMCG6-023）の「だつりょくえき」は実装を延期しました（v0.17c。DEFER。docs/kogas-muk-event-design-v0.17c.md）。宣言する特殊能力か（DR1）・処理する時点（DR6）が原典で決まらず、今の KERNEL はダメージの要素のあとの窓の中で決定を出して続けられません（`AttackRun.suspend` は送る効果が残っていれば RuntimeError。決定をまたいで `FrameState`・`Resolution` の値は残らない）。カードは分類で拒否したままにしてください（効果のないものとして扱わない）。実装するときは、同じ文書 6 章の手順（自動なら続きの情報を既存の `decision.context` に明示的なデータで持つ案 B、宣言するならきぜつの判定の窓の任意の効果の拡張）にしたがいます。`PendingDecision` に項目を加える形（案 A）は形式 9 を保てないので採らないでください。
- 比べる方法 `legacy`（v0.13 の止める関数の先読み）は、`v013_checks.VERIFIED` の型だけにそれを使い、ほかの型（v0.17 から加えた型）はすべての結果を試す方法で確かめます（v0.17d。`flow._use_attack`）。v0.13 の止める関数は v0.17 の問い（Z23 など）を知らず、使うとコインの結果で受け付けるかが変わります（docs/card-extensibility-verification-v0.17d.md 6 章。tests/test_rocket_snorlax_v0_17b.py `test_no_damage_stops_in_every_preflight_mode`）。新しい型を `legacy` のためだけに `VERIFIED` に加えないでください。
- エンジンが止める `UNRESOLVED_…` は 18 件（v0.16 までの 17 件は変えていない）、未解決の裁定は 24 件（Z9・Z23 を加えた。Z13 は C18、Z18 は C34/C35 と同じ問い）。だつりょくえきの DR1・DR6・DR8・DR13・DR18 は、カードが未対応なのでエンジンの止める処理はなく、延期の理由として記録しています。
- 書き出しは形式 9 のまま、ログのイベントの種類・状態の型・`engine.py` は変えていません。ストレス実行の組 `snorlax`・`snorlax_mixed` は `ALL_SCENARIOS` の最後、`POWER_USERS` の最後に R団のカビゴンを加えたので、R団のカビゴンのいない組の操作は v0.16 と同じです。固定した v0.16（`15770c6`）との比較は、`tools/engine_lockstep.py record` の `--scenarios` に v0.16 の 26 組を渡して新しいカードの組を除きます（docs/card-extensibility-verification-v0.17d.md 3 章）。新しいカードの対戦のテストは tests/v017_games.py の `play_game(decks, seed, ...)`（v0.13 の対戦の手順をデッキを引数にして使う）。

## 研究データとの同期と検証の再現性（v0.18）

- 研究の基準は kyuura `3f349085645f47d0649a6cacece3680caeae50bf`（v0.18 は `adf97107ee0d9755cd7ddedae298ecb02914128e`。2026-10-15 に上げた。上の「研究資料の参照コミットを固定する」）。エンジンの停止コード・問い・未解決の裁定・登録した最新の説明・照合の記録と、kyuura の id（論点 UQ-・裁定 CR-・最新の説明 LD-・照合 CC-）の対応は `kyuura_engine/data/research_links.json` に持ちます。kyuura の記録（文面・分類・根拠）を写さないでください（id の対応だけ。正本は kyuura）。docs/research-alignment-v0.18a.md。
- 停止コード・問い（`questions.QUESTIONS`）・最新の説明のある登録（`play_text_ja`）・照合の記録を加えたら、対応表も直します（tests/test_research_links_v0_18e.py が、エンジンの側の集合と対応表を照らす）。最新の説明のある登録は、kyuura の LD-（`registered`）・印刷の文面と同じで kyuura の CC- に書かれたもの（`recorded_in_card_checks`）・CC- はあるがワザの文面を照合していないもの（`card_checks_without_text`）・kyuura に記録なし（`registered_without_kyuura_record`）・kyuura データの採用で処理に使う文面を kyuura の印刷の文面にしたもの（`adopted_printed_text`。2026-10-15 からの方針。エンジンが原典と照合した記録ではない）・処理に使う文面を kyuura のエラッタ（ERR-・TXT-・RUL-）にしたもの（`errata_text`。v0.30）・処理に使う文面を kyuura の data/curation/card_differences.json の記録（確度: 確実）の最新の説明にしたもの（`difference_text`。v0.31。ピッピの「ゆびをふる」。LD- がない）のちょうど 1 つに挙げます（2026-10-15 から）。エラッタの記録の `cards` にないカードに、記録の範囲（「…はすべて同じ処理」など）として当てはめるときは、`errata_scope` に記録の文の引用・記録が挙げるカードの同じ印刷の文面・対象を書きます（v0.30。検査が研究の基準のコミットの記録と照らす。印刷の文面が違うカードに当てはめない）。kyuura に記録がなければ `registered_without_kyuura_record`・`engine_verified_without_kyuura_record` に挙げ、kyuura への報告事項にします（2026-10-15 の取り込みで空になり、v0.19 で `engine_verified_without_kyuura_record` にオーキドはかせ（PMCG1-077）、v0.21 で突風（PMCG1-072）、v0.22 でパソコン通信（PMCG1-090）、v0.23 でエネルギー回収（PMCG1-076）、v0.24 でポケモン交換おじさん（PMCG1-093）、v0.25 でポケモン育て屋さん（PMCG1-094）、v0.27 でストライク（PMCG2-017。`registered_without_kyuura_record` にも「つるぎのまい」の PMCG2-017/attack/0）、v0.28 で既存の効果の型で加えたポケモン 10 枚（`registered_without_kyuura_record` に説明文のあるワザ 13）を加えた。kyuura に記録ができたら、検査が一覧を直すよう知らせる）。v0.29 の採用の記録で加えたポケモン 14 枚の説明文のあるワザ 14 は `adopted_printed_text` に挙げています（kyuura への報告事項ではない。v0.30 でとっしん・第4弾のポニータのひのこを加えて 16。v0.31〜v0.33 の採用で加えたワザ・特殊能力も同じ区分）。kyuura の未解決の一覧（`engine_unresolved_index`）にまだない停止コードは、`stop_codes` の `kyuura_disposition` を `not_in_kyuura` にします（v0.21 の `UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH`・v0.22 の `UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK`・v0.23 の `UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET`・`UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE`・v0.31 の HC1〜HC10 の 10 件・v0.32 の CD4（`UNRESOLVED_OPPONENT_POKEMON_COUNTERS`）。kyuura に記録ができたら検査が知らせる）。kyuura の未解決の一覧でコードのない行に、エンジンが停止コードを付けたもの（v0.31 の T27・C34/C35・G40・P19・P32）は、`kyuura_index_engine_key` でその行を指します。`../kyuura` があれば `python3 scripts/check_research_links.py --kyuura ../kyuura` が、論点の分類（UNRESOLVED のままか）・エンジンの未解決の一覧・分類の違い・最新の説明の文面・照合の記録・カードデータの違いを、研究の基準のコミットの記録と照らします。kyuura で論点が UNRESOLVED でなくなったら、このスクリプトが失敗します。そのときは、根拠を docs に書いてから止める処理を見直します（エンジンの判断で先に決めない）。
- カードの写しの元（`KYUURA_COMMIT` = `ecb2d69`）と研究の基準（`3f34908`。v0.18 は `adf9710`）は別に持ちます。状態はカードデータの元のコミット（`state.card_data.commit`・ログ `game_created`）を持ち、写しのコミットを上げると固定した参照データがすべて変わるからです。エンジンが使う項目が 2 つのコミットで同じことは、上のスクリプトが確かめます（違いは対応表の `card_data_differences` だけ）。
- 分類（CONFIRMED・SUPPORTED）は kyuura の記録を正本にします。エンジンの過去の版の裁定の表は当時の記録として書き換えません（v0.18a の分類の違い 17 件。どれも処理は同じ）。コインの有無・順番だけが変わる論点（kyuura の rng_only）を、実装の約束として決めることは v0.18 では採っていません（docs/research-alignment-v0.18a.md 7 章）。
- Z23 は、ダメージを与えなかった場合を Z23-a（要素が無効）・Z23-b（計算の結果が 0。ディフェンダー・抵抗力）・Z23-c（「とうめい」）・Z23-d（対象がいない。今のワザでは起こらない）に分けて記録しています（docs/unresolved-research-v0.18b.md 3 章）。どれか 1 つの答えが見つかっても、ほかの場合を同じに扱わないでください（理由の文が場合を書く。tests/test_unresolved_research_v0_18b.py）。「ダメージを与えた後」の効果のダメージの要素は、並びの最初でコインで飛ばされない形にしています（Z23-d が起こらない。崩すワザを加えるときは Z23-d を原典で確かめる）。
- ナツメのヤドン（PMCG6-044。v0.18c）の「ぐうたらこうげき」は、たおれこむと同じ実装の型 `DamageAndSelfSleep` の登録だけです（カードごとの分岐・新しい要素はない）。超のワザなので、抵抗力 超 の相手で Z23-b が起こります（止める）。docs/kernel-reuse-v0.18c.md。
- 窓の途中の決定（ダメージの要素のあとの窓で決定を出す効果）は、v0.18d でも DEFER です（docs/mid-window-decisions-v0.18d.md）。p.100［にげこむ］のとおり、宣言する特殊能力でもワザの最中（ダメージのあと・効果の前）に使う例があるので、だつりょくえきは DR1 がどちらでも案 B（`decision.context` の明示的な続きの情報）が要る可能性があります。実装するときは同じ文書の 6 章の 6 つの性質を受け入れの条件にし、9 章の手順にしたがいます。tests/test_mid_window_decisions_v0_18d.py は設計の前提（`FrameState` の項目・送る効果が残ると止まれない・決定を出す送る効果がない）を固定しています。テストの期待だけを変えないでください。
- 変異試験の定義は `tools/mutants.py`（版管理）、実行は `tools/run_mutants.py`（`check`・`witness`・`full`。写しの木で走らせ、作業ツリーは変えない）です。変異ごとに証人のテスト（元のコードで通り、変異で失敗するテスト）を持ち、構文として正しくない変異は見つけた数に入れません。コードを変えて変異が入らなくなったら（tests/test_mutation_definitions_v0_18e.py が失敗する）、同じ誤りを今のコードに入れるように直します（変異を消して数を減らさない）。走らせていない変異試験を、通ったと書かないでください（docs/verification-reproducibility-v0.18e.md）。

## オーキドはかせと手札をトラッシュするトレーナー（v0.19）

- オーキドはかせ（PMCG1-077）は `effects.DiscardHandAndDraw(count=7)`（`TrainerEntry`。p.255 の最新の説明「あなたの手札をすべてトラッシュする。その後、山札からカードを7枚引いて、手札にする。」）です。既存のトレーナーの登録・使用中のカード（`trainer_in_use`）・ドロー（`zones.draw_cards`）の処理だけで扱い、`engine.py`・`resolution/` にカード id での分岐を加えていません（tests/test_professor_oak_v0_19.py が確かめる）。規定と根拠（O1〜O13。再利用した記録と p.255 で読んだことの区別）は docs/professor-oak-v0.19.md、検証は docs/v0.19-verification.md。
- 手札をすべてトラッシュに置くのは `zones.discard_hand` だけです（ログ `discard_hand`。`cards` はトラッシュに置いたカードで公開の情報）。使っているトレーナーは p.310 の手順 1 で手札から出ている（`trainer_in_use`）ので含めません。手札を捨てる・山札にもどすトレーナー（にせオーキドはかせ・にせオーキドの逆襲など）を加えるときも、ゾーンの間の移動は 1 か所の関数にし、ログの監査（tests/log_audit.py。`discard_hand` は手札の組み立て直しと同じであることを確かめる）にも加えてください。
- 効果で引くときの規定（山札が足りなければ引けるだけ・0 枚でも負けではない・負けは番の最初に引けないときだけ。p.309・p.312）は v0.2b のマサキと同じで、オーキドはかせのために読み直していません（照合済みの記録の再利用）。トラッシュに順番はない（p.312）ので、手札とこのカードをトラッシュする順番で結果は変わりません。
- 2002年の「サポーター適用カード」（kyuura `MIX-SUPPORTER-ERRATA`）は 2000.02.14 版のあとの規定なので使いません（1 番に 1 枚などの制限を入れない）。
- 写しの組は `pool_v0_19`、効果の登録表の id は `kyuura-engine-0.13` のまま（v0.17・v0.18 と同じく変えていない）、書き出しは形式 9 のままです。正式な対戦開始からの統合テストは、オーキドはかせを手札にあればいつも使う決まった手順（`oak_command`）で、境界（手札がこのカードだけ・山札 7 枚未満・山札 0 枚）を自然な対戦で起こします（山札 0 枚は seed 0〜399 で seed 71 の 1 局だけなので、その seed を加えている）。

## 最初の対戦用デッキ（v0.20）

- 利用者が選ぶ固定のデッキは `kyuura_engine/decks.py` の `PRESET_DECKS` の 1 か所だけで持ちます（`PresetDeck`。識別子・名前・（カード id, 枚数）の並び）。`cards()`・`counts()` は呼ぶたびに新しい値を返し、登録は書きかえられません。テストの盤面・統合テストのためのデッキ（tests/ のもの）をここに登録しないでください。docs/preset-decks-v0.20.md。
- 固定のデッキは対応済みのカードだけで組みます。未対応のカードを入れて、効果がないものとして扱わないでください（tests/test_preset_decks_v0_20.py が、すべてのカード・ワザ・特殊能力の登録・進化の関係・照合の記録を確かめる）。最初の試作の構成で、勝率の釣り合いを確かめた構成ではありません。そう書かないでください。
- 対戦で既知の未解決の裁定（たとえば対戦準備の `UNRESOLVED_MULLIGAN_COMPENSATION`）に当たっても、避けるためにデッキ・ルールを黙って変えないでください。終わり方の分類（通常の勝敗・サドンデス・停止・`UNRESOLVED_…` で拒否されたあと続けた回数・手数の上限・想定外の拒否・内部エラー）から落とさずに数えます（tools/preset_deck_games.py）。
- tools/preset_deck_games.py は、既存の統合テストの決まった手順（tests/v017_games.py の `play_game` と v0.13 の手順）を再利用し、エネルギーのつけ先とオーキドはかせの使い方だけを加えた駆動です。対戦相手の AI ではありません。勝率でデッキの強さ・釣り合いを判断しないでください。
- examples/start_preset_game.py は対戦の開始だけの例です。人間が最後まで遊べる操作画面と書かないでください。
- v0.26 で第2版（`hitmonchan-dewgong-v2`・`venusaur-parasect-v2`）を別の識別子で加えました（下の「固定のデッキの第2版（v0.26）」）。第1版の識別子と中身は変えないでください。

## 突風と相手の場の入れ替え（v0.21）

- 突風（PMCG1-072）は `effects.SwitchOpponentWithBench`（`TrainerEntry`。p.255 の最新の説明「相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える。」）です。選ぶのは突風を使ったプレイヤーで（GW2）、決定（`SELECT_POKEMON`）の `player` は使ったプレイヤー、選べるものは相手のベンチの場のポケモンの番号です。バタフリーの「ふきとばし」（相手が選ぶ。v0.4d の F3）の処理（`FORCED_SWITCH`・ログ `forced_switch`・「とうめい」の判定）を使わないでください。見た目が似ていることだけで処理を流用しないでください。規定と根拠（GW1〜GW18。再利用した記録と p.255 で読んだことの区別）は docs/gust-v0.21.md、検証は docs/v0.21-verification.md。
- 入れ替えそのものは、ポケモンいれかえと共通の `effects._switch_active_with_bench(state, owner, pokemon_id)`（v0.20 までの `SwitchWithBench.resume` の本体をそのまま関数にした）だけで行います（場のポケモンごと入れ替え・特殊状態と持続する効果を理由 `switch` で消す・ログ `switch`）。突風だけの入れ替えの処理を作らないでください。ログ `switch`・`special_conditions_removed`・`persistent_effect_removed` の `player` は入れ替わる場の持ち主（突風では相手）で、使ったプレイヤーは直前の `play_trainer` の `player` です（項目は加えていない）。トレーナーの効果なので「とうめい」は評価しません（T29。p.159）。
- 相手に控えがいないときに突風を使えるかは原典で決められない（GW5。最新の説明・解説になく、第1弾の印刷の文面の「相手に控えがいない場合は使えない」は最新の説明にない）ので、`check_playable` が `UnsupportedError`（`UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH`）で止めます。印刷の文面・kyuura の再録の分類（docs/cards/reprints.md の「書き方だけ」）で補わないでください。ポケモンいれかえの `UNRESOLVED_SWITCH_WITHOUT_BENCH` とは別の問いです（解消していない）。エンジンが止める `UNRESOLVED_…` は 19 件、未解決の裁定は 25 件です。
- 「バトル場をはなれられない」状態（p.325）を加えるときは、突風・ポケモンいれかえ・ふきとばしの扱いを原典で確かめてください（GW16）。
- 組み合わせの対戦は tools/preset_deck_games.py の `--variant gust`（固定のデッキのディフェンダー 3 枚を突風 3 枚に置き換えた一時的なデッキ。`deck_cards`）です。公開の固定のデッキ（`kyuura_engine.decks`）に突風を入れないでください。既定の `--variant preset` の結果は v0.20 と同じです（突風の手順は何もしない）。
- 写しの組は `pool_v0_21`、効果の登録表の id は `kyuura-engine-0.13` のまま、書き出しは形式 9 のままです。`engine.py`・`resolution/` は変えていません。

## パソコン通信と手札・山札を選ぶトレーナー（v0.22）

- パソコン通信（PMCG1-090）は `effects.DiscardFromHandThenSearchDeck(discard=2, search=1)`（`TrainerEntry`。p.260 の最新の説明「手札からカードを2枚選んでトラッシュしなければ、このカードは使えない。あなたの山札からカードを1枚選び出し、手札に加える。その後、その山札をよく切る。」。p.310 の例にも同じ文）です。規定と根拠（CS1〜CS21。再利用した記録と p.260・p.310 の例・p.312 の山札の項で読んだことの区別）は docs/computer-search-v0.22.md、検証は docs/v0.22-verification.md。
- 使うための条件（このカードを除く手札 2 枚。p.310）は `check_playable` が手札から出す前に確かめ、満たせなければ `IllegalActionError("INSUFFICIENT_CARDS_IN_HAND")` です。使用中のこのカード（`trainer_in_use`）を数えたり、選べるものに入れたりしないでください。山札が 0 枚のとき（CS6）は原典で決められないので、条件の確認のあとで `UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK` で止めます。p.312 の「引けるだけ引く」（「カードを引く」ときの規定）で補わないでください。
- 2 段階の選択は、既存のトレーナーの決定の再開（`resume` が次の決定を出す）で表します（決定の種類 `decisions.DISCARD_FROM_HAND`・`SEARCH_DECK`。段階は `Phase.DECISION`、再開先は `"trainer"`）。別の決定の列・汎用の効果の書き方を作らないでください。段階 2 の不正な答えで、すんだ段階 1 のトラッシュを取り消さないでください。
- 手札の一部を選んでトラッシュするのは `zones.discard_from_hand`（ログ `discard_from_hand`。手札の並びの順。公開）、手札をすべてトラッシュするのは `zones.discard_hand`（ログ `discard_hand`）で、カードを動かす部分（`_hand_to_discard`）を共通にしています。2 つのログのイベントを混ぜないでください（監査の確かめ方が違う）。山札から選び出して手札に加えるのは `zones.search_deck_to_hand`（ログ `search_deck` の `card` は選んだプレイヤーだけが見る非公開の項目）で、「カードを引く」`draw_cards` と混ぜないでください。山札を切るのは `zones.shuffle_deck`（v0.21 までの `engine._shuffle_deck` の本体。対戦の準備・切り直しと共通。乱数 `state.rng` の並べかえ 1 回）だけです。新しい乱数を作らないでください。
- 山札の中身（段階 2 の決定の選べるもの。uid の小さい順）は内部の状態にだけ持ち、ログに書かないでください。選んだカードを相手に見せる必要がない（CS14）は SUPPORTED です。見せる指示のあるカード（ダウジングマシーンなど）を加えるときは、ログの公開の項目を決めてください。
- 組み合わせの対戦は tools/preset_deck_games.py の `--variant computer`（固定のデッキのディフェンダー 3 枚をパソコン通信 3 枚に置き換えた一時的なデッキ）です。公開の固定のデッキに入れないでください。`--variant preset`・`--variant gust` の結果は v0.21 と同じです。
- 写しの組は `pool_v0_22`、効果の登録表の id は `kyuura-engine-0.13` のまま、書き出しは形式 9 のままです。エンジンが止める `UNRESOLVED_…` は 20 件、未解決の裁定は 26 件です。

## 突風とパソコン通信の併用・エネルギー回収（v0.23）

- 突風とパソコン通信を同じデッキに入れた対戦は tools/preset_deck_games.py の `--variant mixed`（固定のデッキのディフェンダー 4 枚を除き、突風 2 枚・パソコン通信 2 枚を加えた一時的なデッキ）です。パソコン通信の手順は、山札に突風があり手札になく、突風の手順が今の番に使う場面なら突風を選びます（突風のないデッキでは何もしないので、`--variant computer` の結果は v0.22 と同じ）。`mixed`・`retrieval` では、決定ごとの持ち主・使用中のカード（`check_…`）とトレーナーを使ってからトラッシュするまでのログ（`trainer_sequence_problems`）を確かめます。公開の固定のデッキに入れないでください。
- エネルギー回収（PMCG1-076）は `effects.DiscardFromHandThenRetrieveEnergy(discard=1, retrieve=2)`（`TrainerEntry`。p.257 の最新の説明「手札からカードを1枚選んでトラッシュしなければ、このカードは使えない。あなたのトラッシュから「基本エネルギーカード」を最大2枚選び出し、手札に加える。ただし、このカードを使うためにトラッシュしたカードを選ぶことはできない。」）です。規定と根拠（ER1〜ER17）は docs/energy-retrieval-v0.23.md、検証は docs/v0.23-verification.md。最新の説明の文面は kyuura の ERR-ENERGY-RETRIEVAL（rule_history.json）の記録を再利用し、p.257 は図版・見出し・収録・解説だけを読みました。
- 段階 1 はパソコン通信と同じ決定 `DISCARD_FROM_HAND`・`zones.discard_from_hand`（手札から 1 枚）、段階 2 は決定 `decisions.RETRIEVE_ENERGY`（自分のトラッシュの基本エネルギーカードから、段階 1 でトラッシュしたカード（決定の `context` の `"discarded"`）を除いたもの。0〜min(2, 数) 枚）と `zones.return_discard_to_hand`（ログ `retrieve_energy`。公開）です。ゴースのエナジーへんかんの `RECOVER_ENERGY`（ワザ・「エネルギーカード」・除くカードがない）・ログ `recover_energy` を流用しないでください。似ているだけで、枚数・対象・使うための条件を同じと判断しないでください。
- 使う前の自分のトラッシュに基本エネルギーカードがないとき（ER10）は `UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET`（`check_playable`。使うための条件の確認のあと）、選べるものがあるのに 0 枚を選んだとき（ER9）は `UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE`（決定は待ったまま）で止めます。トラッシュする手札が基本エネルギーカードでも選べない（ER7）ので、トラッシュによって対象は生じません（対象の数は使う前に数えても同じ）。ER9 はエナジーへんかんの H4 と同じ言い回しの別のカードの問いで、どちらかの答えでもう一方を決めないでください。エンジンが止める `UNRESOLVED_…` は 22 件、未解決の裁定は 28 件です。
- 回収できるのは基本エネルギーカードだけ（ER6。特殊エネルギーは選べない）ですが、今の写しに特殊エネルギーのカードはありません。特殊エネルギーのカードを加えるときは、選べるものに入らないことをそのカードで確かめてください。
- 組み合わせの対戦は `--variant retrieval`（`mixed` からさらにきずぐすり 2 枚をエネルギー回収 2 枚に置き換えた一時的なデッキ）です。写しの組は `pool_v0_23`、効果の登録表の id は `kyuura-engine-0.13` のまま、書き出しは形式 9 のままです。`engine.py`・`resolution/`・`zones.py` は変えていません。

## ポケモン交換おじさんと手札・山札を入れかえるトレーナー（v0.24）

- ポケモン交換おじさん（PMCG1-093）は `effects.TradePokemonWithDeck`（`TrainerEntry`。p.259 の最新の説明「手札から「たねポケモン」または「進化カード」を1枚選び、相手プレイヤーに見せてから、あなたの山札にもどす。それができないとき、このカードは使えない。あなたの山札から「たねポケモン」または「進化カード」を1枚選び出し、相手プレイヤーに見せてから、手札に加える。その後、その山札をよく切る。」）です。規定と根拠（PT1〜PT19。再利用した記録と p.259 で読んだことの区別）は docs/pokemon-trader-v0.24.md、検証は docs/v0.24-verification.md。印刷の文面（「交換することができる」）・英語版・現代の同じ名前のカードで補わないでください。
- 使うための条件は、このカードを除く手札のたねポケモン・進化カード（`is_basic_pokemon`・`is_evolution_pokemon`。既存のカードの定義）を山札にもどすことだけで、満たせなければ `IllegalActionError("NO_POKEMON_CARD_IN_HAND")`（`check_playable`。手札から出す前）。山札の中身（見えない情報）を使うための条件にしないでください（PT3）。もどしたカードは山札に入るので、段階 2 の選べるものに含め、山札にほかのポケモンのカードがなければそれを選び直します（p.259 の解説。PT10・PT11）。「対象がない」（使えない）・「探しても見つからない」（起こらない）・「選ぶのを省略する」（できない）を混ぜないでください。
- 段階 1 は決定 `decisions.RETURN_TO_DECK`（手札のたねポケモン・進化カードから 1 枚）→ `zones.return_hand_to_deck`（山札の一番下。ログ `return_to_deck` は公開）、段階 2 は既存の決定 `SEARCH_DECK`（山札のたねポケモン・進化カード。uid の小さい順。`context` の `"returned"`）→ `zones.reveal_deck_to_hand`（ログ `reveal_from_deck` は公開）→ `zones.shuffle_deck` です。手札をトラッシュする効果ではないので、パソコン通信・エネルギー回収の `discard_from_hand` を使わないでください。もどしてから選び出す順番（p.259 の最新の説明・ポケモン育て屋さんの解説）を、実装しやすさで入れかえないでください。もどす位置（一番下）は実装上の仮定（PT7。そのあと必ず切るので結果は変わらない）で、切らないカードに流用しないでください。
- 見せるカード（もどしたカード・手に入れたカード）だけをログの公開の項目に書き、山札の中身（段階 2 の選べるもの）はログに書きません。パソコン通信の `search_deck`（`card` は非公開。CS14）を、見せる指示のあるカードに流用しないでください（`search_deck_to_hand`・`reveal_deck_to_hand` はカードを動かす部分 `_deck_to_hand` だけを共通にしている）。
- 手に入れたカードは、ふつうの規定でベンチに出し・進化します（PT17）。交換で手に入れたことを理由に、その番に場に出たポケモン・最初の番の進化の制限を免除しないでください。2002 年の「サポーター適用カード」（kyuura `MIX-SUPPORTER-ERRATA`）は使いません。
- 組み合わせの対戦は tools/preset_deck_games.py の `--variant trader`（`retrieval` の残りのきずぐすり 2 枚をポケモン交換おじさん 2 枚に置き換えた一時的なデッキ）です。公開の固定のデッキに入れないでください。既存の変種の結果は v0.23 と同じです。
- 写しの組は `pool_v0_24`、効果の登録表の id は `kyuura-engine-0.13` のまま、書き出しは形式 9 のままです。`engine.py`・`resolution/` は変えていません。新しい未解決はなく、エンジンが止める `UNRESOLVED_…` は 22 件、未解決の裁定は 28 件のままです。

## ポケモン育て屋さんと 1 進化を飛ばす進化（v0.25）

- ポケモン育て屋さん（PMCG1-094）は `effects.EvolveBasicToStage2`（`TrainerEntry`。p.259 の最新の説明「このカードは、あなたが自分の場にいるポケモンを進化させるときにだけ、使える。そのポケモンの上に「2進化カード」を直接のせ、1進化をとばして「2進化ポケモン」に進化させる。」）です。規定と根拠（BR1〜BR22。再利用した記録と p.259 で読んだことの区別）は docs/pokemon-breeder-v0.25.md、検証は docs/v0.25-verification.md。v0.24 で読んだ解説の 1 段落を、このカードの照合の記録として扱わないでください（v0.25 で p.259 のこのカードの部分を読んだ）。印刷の文面・英語版（「when you would be allowed to evolve that Pokémon anyway」）・現代のルールで補わないでください。
- 育て屋さんによるものも「進化」です。p.310 の進化の制限（おたがいの最初の番・その番に場に出したたねポケモン）を免除しないでください。反対に、通常の進化の名前・段階の確認（`EVOLUTION_NAME_MISMATCH`・`EVOLUTION_STAGE_MISMATCH`）は 1 進化を飛ばすこと自体を拒否するので、育て屋さんには当てはめず、系統の確認に置きかえています。通常の `EvolvePokemon` で 1 進化を飛ばせるようにしないでください（v0.4c の S2）。
- 系統は、2 進化カードの「○○○○から進化」の名前の 1 進化カード（同じ写しのカードのデータ）の進化元の名前（`CardDefinition.stage1_evolves_from`。`cards.pool_from_extract` が求める）と、たねポケモンの名前の完全一致で確かめます（`evolution.skipped_stage1_basic`）。名前の一部・形容詞（「サカキの」「わるい」）で比べないでください。写しに 1 進化カードがない・進化元が食い違う 2 進化カードは確かめられないので、推測で対応にせず `UNSUPPORTED_EVOLUTION_LINEAGE`（または選べるものに入れない）にします。写しに 2 進化カードを加えるときは、その 1 進化カードも写しにあることを確かめてください。`state.definitions` はデッキのカードだけなので、1 進化カードを状態から引かないでください。
- 進化の手順（p.310 の手順 1〜5。特殊状態・持続する効果・にげるの失敗の記録を消し、ダメージ・エネルギー・ついているトレーナー・場のポケモンの番号・場に出た番を受け継ぐ）は `kyuura_engine/evolution.py` の `place_evolution_card` だけで行います（通常の `EvolvePokemon` と育て屋さんで共通。`engine.py` を読み込まない）。育て屋さんのときだけ、ログ `evolve` に `trainer_card`（使っているトレーナーのカードの uid）を書きます（通常の進化のログは v0.24 と同じ形）。進化の手順を変えると両方が変わるので、固定した前の版と別のプロセスで比べてください。
- 進化の重なりの不変条件（`engine._evolution_problems`）は、下から段階が増えていくこと（`EVOLUTION_STAGES` の順）を確かめ、隣り合う 2 枚が 1 段階の差なら「○○○○から進化」が下の名前、たねポケモンと 2 進化なら系統が合い、その移り変わりの進化のログに `trainer_card` があることを要ります。`trainer_card` は 1 進化を飛ばした移り変わりだけにあり、持ち主のカードで、登録した実装が `TrainerEffect.skips_stage1_evolution`（カード id で分けない）であることを `_skip_evolution_log_problems` で確かめます。テストの盤面（`build_test_state` の `"evolved_from"`）でたね + 2 進化の重なりを作るとログがないので違反です。育て屋さんで進化した盤面は、テストでも実際に育て屋さんを使って作ってください。不変条件を弱めないでください。
- 決定は、使ったプレイヤーが進化させるたねポケモン（既存の `SELECT_POKEMON`）→ 重ねる手札の 2 進化カード（`decisions.SELECT_EVOLUTION_CARD`。`context` の `"target"`）の順（p.310 の進化の手順 1 の順。実装上の判断）。進化したあとの HP がダメージ以下になる組は v0.4a の H1 と同じ問いなので、同じ `UNRESOLVED_EVOLUTION_HP`（使う前・`unresolved_choices`）で止めます。新しいコードにしないでください。
- 組み合わせの対戦は tools/preset_deck_games.py の `--variant breeder`（デッキ A は `trader` のまま、デッキ B だけ `trader` のマサキ 2 枚をポケモン育て屋さん 2 枚に置き換えた一時的なデッキ。`DECK_SUBSTITUTIONS`）です。公開の固定のデッキに入れないでください。既存の変種の結果は v0.24 と同じです。
- 写しの組は `pool_v0_25`、効果の登録表の id は `kyuura-engine-0.13` のまま、書き出しは形式 9 のままです。`resolution/` は変えていません。新しい未解決はなく、エンジンが止める `UNRESOLVED_…` は 22 件、未解決の裁定は 28 件のままです。

## 固定のデッキの第2版（v0.26）

- 第2版は `kyuura_engine/decks.py` の `PRESET_DECKS` に、第1版と並べて別の識別子（`hitmonchan-dewgong-v2`・`venusaur-parasect-v2`）で持ちます（v0.20 の `PresetDeck` の仕組みのまま。新しいデッキ管理の仕組みを作らない）。第1版（`hitmonchan-dewgong`・`venusaur-parasect`）の識別子と中身は変えないでください（tests/test_preset_decks_v0_26.py が v0.20 の文書の表と比べる）。構成・変更の理由・進め方・比較の結果・自動操作の限界は docs/preset-decks-v0.26.md、検証は docs/v0.26-verification.md。
- 開始の例（examples/start_preset_game.py）・対戦の道具（tools/preset_deck_games.py の `--deck-a`・`--deck-b`）の既定は第1版のままです。黙って第2版に切りかえないでください。知らない識別子は引数の誤りで、1 局も始めずに拒否します（0 局の成功として扱わない）。既存の変種（`gust`〜`breeder`）は第1版のカードを置き換える一時的なデッキなので、第2版には使えません（`ValueError`）。
- 第1版と第2版を比べるときは、tools/preset_deck_comparison.py（4 組・同じ seed・席の入れかえ・同じ手順）を使います。手順（`make_policy`）は 4 組とも同じ関数で、v0.26 では変えていません（既存の 7 つの変種の結果は v0.25 と同じ）。比較のために手順を変えたら、同じ手順で第1版も測り直し、前の手順の数値を混ぜないでください。`play(..., observe=True)` は数えるだけで、選ぶ操作を変えません（テストが確かめる）。
- 「攻撃できなかった番」は、手順が攻撃しなかったことから推測せず、やり直した状態でエンジンに `UseAttack` を渡して確かめます（拒否のコードが理由）。確かめるのはその時点のバトル場のポケモンだけです。集計には分母（局数・自分の番）を付け、1 局に何回も起こる出来事を局数と混ぜないでください。
- 第2版は試作の構成です。大会のデッキ・最適化したデッキ・人間どうしで釣り合いを確かめたデッキと書かないでください。勝率は判断に使わず、勝率を良く見せるための調整・未解決の裁定を避けるためだけの構成の変更をしないでください。初期案からの調整は 1 回（デッキ A2 のポケモン交換おじさん 2 → 闘・水 1 枚ずつ。根拠は docs/preset-decks-v0.26.md 4 章）で、デッキ B2 は初期案のままです。
- 研究の基準（`3f34908`）とカードの写しの元（`ecb2d69`）は変えていません。kyuura に v0.25 までの記録を還元したコミット（`codex/engine-findings-through-v0.25` の `0a82aed`）への切りかえは、研究の対応表と検査を更新する別の作業です。

## ストライクと次の自分の番にワザのダメージを変える効果（v0.27）

- ストライク（PMCG2-017）の「つるぎのまい」は `effects.SetNextTurnAttackDamage(target_attack_index=1, target_attack_name="きりさく", damage=60)`（`AttackKey("PMCG2-017", 0)`。要素 `programs.SelfNextTurnAttackDamage`）、「きりさく」は `DamageOnly` です。p.56・p.321 の最新の説明「次の自分の番、このカードが使う「きりさく」のダメージは「60」になる。」と p.57 のワザ解説にしたがいます。印刷の文面（kyuura の写し。「2倍」）・英語版の文面で処理を決めないでください。規定と根拠（SC1〜SC22。再利用した記録と p.56・p.57・p.321 で読んだことの区別）は docs/scyther-v0.27.md、検証は docs/v0.27-verification.md。
- 効果は持続する効果 `state.NextTurnAttackDamage`（`PokemonInPlay.persistent_effects`。v0.4b と同じ置き場所・消える契機・ログ）で、はたらく番は与えた番 + 2（型の `turns_until_active`。`PreventDamage`・`Retaliation` は 1）です。はたらく番の終わりに消えます（p.57「効果の持続：次の自分の番の最後」）。ワザ 1 回の中の値・ログから求め直す形・プレイヤー単位の印にしないでください。効果がはたらくかは `persistent.next_turn_attack_damage(state, pokemon, attack_index)` で、効果を与えたカード（いちばん上）とワザの位置で探します（ワザの名前で探さない。ほかのストライク・パラセクトの同じ名前の「きりさく」を変えない）。
- 対象のワザは登録のデータ（位置と名前）で表し、`AttackEffect.card_problems`（v0.27）が同じカードのほかのワザと照合します（位置・名前・説明のないダメージの目安だけのワザ）。合わなければカードは未対応です。`EffectRegistry.attack_problem`・`attack_effect` の `attacks`（そのカードのワザの一覧）は、分類（cards.py）と使うときの確認（checks.py）が渡します。ほかのワザを指す実装を加えたら `card_problems` を書いてください。
- 「「60」になる」は p.321 の 2 段階で、ダメージをその数にする効果（`damage.DamageModifier` の `operation=SET`。既定は `ADD`）です。最終ダメージに直接足したり、最終ダメージを 2 倍にしたり、8 段階で置きかえたりしないでください。弱点・抵抗力・プラスパワー・ディフェンダーはそのあとの段階で計算します。同じ段階に加算でない効果とほかの効果が重なったら、計算の順番を選ぶ決定（p.321。2 段階はワザを使うプレイヤー）がないので `calculate_attack_damage` が `RuntimeError` で止めます（今の対応カードでは起こらない）。2 段階のほかの効果を加えるときは、先に順番を選ぶ決定を加えてください。
- 変更効果を集めるのは `effects.attack_damage_modifiers(state, attacker, defender, attack=…)` だけです。解決の基盤の `kernel.deal_damage`（`frame.attack_key`）と宣言の前の `preview_attack_damage`（`use.key`。C18・W24 などの確かめ）が同じ関数を使います。片方だけに効果を足さないでください。ダメージの候補（`damage_profile`）は印刷の 30（1 段階）のままです（候補に効果を重ねて数えない）。`attack` を渡さない呼び出し（こんらんの 20 の確かめ `procedures.confusion_damage_problem`）は v0.26 と同じで、こんらんの 20 に「つるぎのまい」は関係しません（p.309 の手順 5。SC17）。
- ワザのダメージのログ `damage` は、効果がはたらいたときだけ `steps` に `("2 つるぎのまい", 60)`、項目 `damage_set`（`((2, 効果を与えたカード, 60),)`）が入ります。加える数の `modifiers` に混ぜないでください（効果のないダメージのログは v0.26 と同じ）。ログの監査（tests/log_audit.py）は、持続する効果のはたらく番を種類ごとに確かめ（「つるぎのまい」は + 2）、ワザのダメージごとに 2 段階の記録の有無と値を、ログから組み立てた効果と登録の位置で確かめます。
- 不変条件（`engine._persistent_effect_problems`）は、はたらく番を `created_turn + turns_until_active` で確かめます。同じ種類の効果は、`turns_until_active` が 1 の型は 1 つまで、どの型も同じはたらく番は 1 つまでです（「つるぎのまい」ははたらく番にもう一度使うと、その番の終わりまで、はたらく番の違う 2 つがある。SC7）。効果を消したログとの対応は、同じ効果（与えた番・はたらく番）のログだけを数えます。登録の値は `_next_turn_attack_damage_problems`（実装の `next_turn_terms()`）で照らします。テストで効果を置くときは `build_test_state` の `"next_turn_attack_damage"`（(与えた番, 効果を与えたワザの位置, 変わるワザの位置, ダメージ)）を使ってください（ログの `effect` は効果を与えたワザ）。
- 書き出しは形式 9 のままです（`persistent_effects` の種類 `next_turn_attack_damage` に `attack_index`・`target_attack_index`・`amount` を加えた。v0.12・v0.13 の種類と同じ扱い）。形式 1〜7 は効果があると `ValueError`。監査の `LATEST_FORMAT` も 9。新しい未解決はなく、エンジンが止める `UNRESOLVED_…` は 22 件、未解決の裁定は 28 件のままです。
- 「次の自分の番」は与えた番 + 2 で表しています（番は交互に進む前提。v0.2e と同じ）。番を飛ばす・続ける効果を加えるときは、この表し方も見直してください。進化先・ほかの「次の自分の番」の効果（「きあいだめ」「ウォーターパワー」）は加えていません。加えるときは、効果の対象・変え方・期限をカードごとに照合し、`NextTurnAttackDamage`（1 つのワザのダメージをその数にする）に当てはまるかを確かめてください。
- 写しの組は `pool_v0_27`、効果の登録表の id は `kyuura-engine-0.13` のまま。公開の固定のデッキは変えていません。対戦の道具の変種 `scyther`（第2版のデッキ A2 のコラッタ 2 枚 → ストライク 2 枚）・`scyther_grass`（第2版のデッキ B2 のモンジャラ 2 枚 → ストライク 2 枚）は第2版だけに使う一時的なデッキ（`tools/preset_deck_games.py` の `V2_SUBSTITUTIONS`）で、第1版の変種（`gust`〜`breeder`）は今までどおり第2版に使えません。tools/scyther_games.py が元の A2 対 B2・A2S 対 B2・A2 対 B2S を同じ seed・席の入れかえ・同じ手順（v0.26 から変えていない）で比べます。勝率で採用を判断しないでください。手順は交代役として「にげる」を使わず、「つるぎのまい」の効果に合わせてエネルギーのつけ先を選びません（docs/scyther-v0.27.md 7 章）。

## 既存の効果の型で加えたポケモン 10 枚（v0.28）

- ラプラス（PMCG3-022）・スターミー（PMCG1-026。ヒトデマンから進化）・トサキント（PMCG2-021）・アズマオウ（PMCG2-022。トサキントから進化）・カイロス（PMCG2-018）・
  タマタマ（PMCG2-006）・プリン（PMCG2-035）・ラッキー（PMCG1-068）・スリープ（PMCG1-045）・シェルダー（PMCG3-012）を、既存の型の登録（`DEFAULT_EFFECTS`）だけで加えました
  （ワザ 19。`ExtraEnergyDamage(水, 10, 2)`・`DiscardEnergyAndRemoveAllCounters(水)`・`DamageAndSelfDamage(80)`・`DamageAndRemoveCounters(1)`・`ParalyzeOnHeads`・
  `ConfuseOnHeads`・`ConfuseOnHeadsWithoutDamage`・`PutToSleep`・`PreventDamageOnHeads`・`DamageOnly`）。一覧・根拠・検証の範囲・報告事項は docs/existing-effect-pokemon-v0.28.md。
  `engine.py`・`resolution/`・型の意味と `check`・ログ・書き出しの形式は変えていません。分離したカードはなく、新しい未解決もありません。
- どのカードも、カードのページ（p.49・p.58・p.103・p.108・p.109・p.112・p.116・p.164・p.225・p.235）の最新の説明と照合し、同じ文面の既存の登録・一般の規定の記録は
  再利用しました（照合済みの記録の再利用）。印刷の文面（kyuura の写し）は登録の照合だけに使います。ラッキーのまるまる・シェルダーのからをとじるは「かたまる」と同じ最新の説明
  （「ダメージを受けない」）で、印刷の文面の「0になる」にしたがいません。
- タマタマの 2 つめのワザ名は、誌面ではひらがなの「やどりぎのたね」、写しは「やどりぎのタネ」です。登録の照合は写しの名前で行い、食い違いとして記録しています
  （PMCG1-008「つるのムチ」と同じ扱い）。写しを手で直さないでください（kyuura 側の報告事項）。
- ラッキーの解説（p.235）「トレーナーカードによるダメージも受けません」: 今の対応カードにダメージを与えるトレーナーはありません。加えるときは、「ダメージを受けない」状態を
  そのダメージにも当てはめるかを、この解説で確かめてください。
- 検証用デッキ `W28`・`G28` と、v0.28 のカードがまだ使っていないワザを選ぶ手順（v0.26 から変えていない手順に重ねたもの）は tools/existing_effect_games.py にあります。
  公開の固定のデッキ・既存の変種には入れていません。60 局の結果・確認表（カード・ワザごとに単体テストと統合のどちらで確かめたか）は docs の 5 章です。勝敗で採用を判断しないでください。
- 写しの組は `pool_v0_28`（写しは 81 枚）、効果の登録表の id は `kyuura-engine-0.13` のまま（ワザの登録 92）。テストの定数は tests/helpers.py の `LAPRAS` など・`V0_28_POKEMON`。

## 既存の効果の型で加えたポケモン 14 枚（v0.29）

- ニョロモ（PMCG1-024）・ロケット団のアーボ（PMCG4-001）・ズバット（PMCG4-002）・ナゾノクサ（PMCG4-003）・ドガース（PMCG4-005）・ビリリダマ（PMCG4-027）・
  ワンリキー（PMCG4-040）・ミニリュウ（PMCG4-051）・タケシのズバット（PMCG5-001）・カスミのトサキント（PMCG5-026）・マチスのコイル（PMCG5-037）・
  マチスのビリリダマ（PMCG5-038）・タケシのイシツブテ（PMCG5-046）・タケシのベロリンガ（PMCG5-061）を、既存の型の登録（`DEFAULT_EFFECTS`）だけで加えました
  （ワザ 24。`ExtraEnergyDamage(水, 10, 2)`・`PoisonOnHeads`・`PutToSleep`・`PoisonWithoutDamage`・`ParalyzeOnHeads`・`CoinFlipDamage`・
  `ConfuseOnHeadsWithoutDamage`・`DamageOnly`）。2026-10-15 からのカードデータの方針で加えた最初のカードです。一覧・判断・照合・検証の範囲は
  docs/existing-effect-pokemon-v0.29.md。`engine.py`・`resolution/`・型の意味と `check`・ログ・書き出しの形式は変えていません。保留・分離したカードはなく、新しい未解決もありません。
- 根拠は kyuura データの採用の記録（`card_sources.json`。14 件・`kyuura_records` は空）と pcg-search.com の同じ版のページとの照合（14 件とも `match`）です。
  ガイドブックは読んでいません。説明文のあるワザの処理に使う文面は kyuura の印刷の文面（`source` は `kyuura data/cards.json`）です。誌面のページをテスト・記録に書かないでください。
- 同じ名前の別のカード: マチスのコイル・タケシのイシツブテはリーダーズスタジアムに 2 種類ずつあり、写しの HP・ワザと同じ版（サイトの一覧の 038/096・050/096）と照合しました。
  ロケット団のワンリキー・ビリリダマ・ミニリュウは第1弾の同じ名前のカード（PMCG1-053・PMCG1-037・PMCG1-065）と別の id・別のワザです。
- ニョロモのみずでっぽうは、カメックスのハイドロポンプと同じ印刷の文面で、kyuura の LD-PMCG1-032-ATK0（`ambiguous_in_print`）と再録の分類（「書き方だけ」）にしたがって
  `ExtraEnergyDamage` で登録しました（採用の記録の `notes`。LD-PMCG1-032-ATK0 はカメックスの記録なので `kyuura_records` に入れていない）。新しい裁定ではありません。
- 検証用デッキ `GW29`・`LF29` と組（`PAIRINGS_V0_29`）は tools/existing_effect_games.py の `--batch v0.29` です（v0.28 の組の結果は変わらない）。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。
- 写しの組は `pool_v0_29`（写しは 95 枚）、効果の登録表の id は `kyuura-engine-0.13` のまま（ワザの登録 116）。テストの定数は tests/helpers.py の `POLIWAG` など・`V0_29_POKEMON`。

## エネルギーをトラッシュしてダメージを与えるワザ（v0.30）

- ヒトカゲ（PMCG1-014）の「ひのこ」・リザード（PMCG1-017）／ウインディ（PMCG1-019）／ブーバー（PMCG1-020）の「かえんほうしゃ」・第4弾ロケット団のポニータ（PMCG4-013。第1弾のポニータ PMCG1-016 とは別のカード）の「ひのこ」は、
  共通の型 `effects.DiscardEnergyThenDamage(EnergyType.FIRE)`（要素の並び `programs.DiscardOwnEnergy` → `Damage(OPP, Printed())`）です。ほかのワザは既存の型（ひっかく・きりさく・ほのおパンチ `DamageOnly`、
  とっしん `DamageAndSelfDamage(30)`）。仕様・カードごとの整理・保留したカード・記録・検証は docs/discard-energy-attacks-v0.30.md。
- 処理は kyuura の `RUL-ENERGY-DISCARD-ATTACKS`（確実）にしたがいます: トラッシュはワザを使うための条件ではなく「ワザの効果」で、宣言 → 持続する効果 → こんらんの確認 → ワザの内容（ここでトラッシュ）。
  第1弾の 4 つのワザの処理に使う文面は記録の最新の説明（「自分についている「炎」エネルギーカードを1枚トラッシュする。トラッシュできないとき、このワザのダメージはなくなる。」。出典は記録の id）、
  印刷の文面（「…はがしてすてる。」）は照合だけに使います。トラッシュが使用条件か効果かを、現代のルール・似た別のカードから推測しないでください。宣言のときにトラッシュしないでください。
- トラッシュするのは、ワザを使うポケモン自身についている「炎」の基本エネルギーカード 1 枚だけです（p.309。余分に捨てない）。選ぶのはワザを使ったプレイヤーで、v0.7 のじこさいせいと同じ決定
  `discard_energy`（ついている順・1 枚でも決定を出す。K2）です。選択・トラッシュの仕組みを別に作らないでください（`DiscardOwnEnergy` と `effects.attached_basic_energy`・
  `discard_attached_energy_decision_problems` を共通に使う。じこさいせいは `DiscardOwnEnergy` → `HealAllCounters`）。
- トラッシュはダメージの要素より先です。相手がダメージを受けなくても（「ダメージを受けない」状態・「とうめい」・最終ダメージ 0）トラッシュはすんでいます（「ダメージを与えた後」の効果ではなく、Z23 にかかわらない）。
  こんらんの「うら」ならトラッシュしません。トラッシュできない場合は今の対応カードでは起こらないので `RuntimeError`（K3 と同じ。第4弾のポニータの「0になる」と最新の説明の「なくなる」の違いもこの場合だけ）。
  特殊エネルギー・ほかのワザを使うワザを加えるときは、この場合の処理とテストを加えてください。
- 型の `check` は、トラッシュするタイプが「炎」でない登録を拒否します（記録の未解決の問い「炎エネルギー以外のエネルギーをトラッシュするワザにも同じ説明が当てはまるか」）。似た文面の超・雷・水のワザ
  （ミュウツーのバリアー・ゴースのみちづれなど）にこの型を流用しないでください。「…トラッシュしなければ、このワザは使えない」（カツラのウインディ・化石の秘密のヤドン）・コインでトラッシュするワザ
  （わるいリザードなど）・すべて／複数枚トラッシュするワザも、この型の意味の外です（docs 4 章）。
- 記録の `cards` はウインディだけです。ヒトカゲ・リザード・ブーバーのワザ（同じ印刷の文面）には、記録の「炎エネルギーカードをトラッシュするタイプのワザ（「かえんほうしゃ」など）は、すべて同じ処理になります。」の範囲として当てはめました（`research_links.json` の `latest_descriptions.errata_scope`・`errata_text`）。
  記録の `cards` にこれらがないことは kyuura への報告事項です（kyuura を直さない）。
- ヒトカゲは v0.2a の過去の原典照合の記録（`card_verification.json`）のあるカードで、その記録に「ひのこ」の文面はありません。v0.30 から、`card_sources.json` の `guidebook_record` に、照合の記録に
  処理に使う文面のない登録の根拠（`play_text`・`kyuura_records`）を書けます（`scripts/check_card_sources.py`。照合の記録に文面のある登録は書けない。ガイドブックの項目は今までどおり書けない）。
  照合の記録（履歴）は書き換えないでください。
- v0.29 まで「ひのこ」が未登録であることを「登録のないワザ」の例に使っていたテストは、その登録だけを除いた登録表（tests/helpers.py の `NO_EMBER_EFFECTS`）を使います。
- ログの監査（tests/log_audit.py）は、ワザごとのエネルギーのトラッシュ（`discard_energy`）の数・順番・種類を、登録した実装で確かめます（じこさいせいはとりのぞく処理と同じ数、`DiscardEnergyThenDamage` は
  こんらんの「うら」・最後の決定待ちを除いて 1 回でダメージの要素より前、ほかのワザは 0 回）。エネルギーをトラッシュするワザを加えたら、監査にも加えてください。
- 検証用デッキ `F30` と組（`PAIRINGS_V0_30`）は tools/existing_effect_games.py の `--batch v0.30` です（v0.28・v0.29 の組の結果は変わらない）。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。
- 写しの組は `pool_v0_30`（写しは 99 枚）、効果の登録表の id は `kyuura-engine-0.13` のまま（ワザの登録 124）。書き出しは形式 9 のまま、ログのイベント・決定の種類は増やしていません。新しい未解決はありません
  （停止コード 22 件・未解決の裁定 28 件）。テストの定数は tests/helpers.py の `CHARMELEON` など・`V0_30_POKEMON`。

## v0.30 で保留した 22 枚の一括実装（v0.31）

- v0.30 の docs/discard-energy-attacks-v0.30.md 4 章の 22 枚と、進化元 7 枚（ピッピ PMCG1-067・イーブイ PMCG2-037・第4弾のコダック PMCG4-019・カスミのコダック PMCG5-021・
  カツラのロコン PMCG6-026・カツラのガーディ PMCG6-027・マチスのピカチュウ PMCG5-036）を、kyuura データの採用で加えました（対応ポケモン 77 → 106。写しの組 `pool_v0_31`。
  ワザの登録 176・特殊能力 12）。カードごとの整理・仕組み・資料・止める場面・互換性・検証は docs/held-cards-v0.31.md。ガイドブックは読んでいません。テストの定数は
  tests/helpers.py の `V0_31_TARGETS`・`V0_31_DEPENDENCIES`・`V0_31_POKEMON`。
- 新しいワザは、解決の基盤の要素の並び（`programs.BUILDERS`）で加えました（v0.13 の約束で書かない）。v0.31 の効果の型は tests/helpers.py の `ATTACK_TYPES_SINCE_V0_17` に
  加えています。`engine.py`・`resolution/` にカード id の分岐はありません。
- エネルギーカードのトラッシュは `programs.DiscardOwnEnergy` 1 つで表します（数 `count`（None ならすべて。決定なし）・コインの「おもて」の数 `heads_of`・好きなだけ
  `any_number`・ワザ全体のコイン `gate`・要素のコイン `local_coin`・トラッシュできないとき `when_lacking`（`LACKING_*`）・時点 `timing`（`TIMING_EFFECT`・
  `TIMING_UNRESOLVED`））。v0.30 の `DiscardEnergyThenDamage`（炎 1 枚 → ダメージ）の意味を、すべて・複数枚・コインのトラッシュ・炎以外に広げないでください（別の型）。
  時点が決められない「はがしてすてる」のワザは、こんらん状態で使うときだけ HC1（`UNRESOLVED_DISCARD_ENERGY_TIMING`）で止めます。炎エネルギーカードをトラッシュして
  大きなダメージを与えるワザ（ほのおのあらし）は RUL-ENERGY-DISCARD-ATTACKS の範囲としてワザの効果です。範囲を推測で広げないでください。
- 持続する効果に `DestinyBond`（みちづれ）・`AttackBarrier`（バリアー。ダメージと効果の要素を無効）・`DamageReduction`（ちいさくなる。p.321 の 8 段階）・`CannotAttack`
  （しっぽをふる。相手に与える効果。`on_opponent = True`。`source_card` は効果を与えたワザを使ったポケモンのカード）を加えました（はたらく番は次の相手の番。消える契機は
  v0.4b と同じ）。相手に与える効果を加えるときは、不変条件（`engine._persistent_effect_problems` の発生源と番）を見直してください。
- 相手のワザを自分のワザとして使う効果（`programs.CopyOpponentAttack`）は、選んだワザの要素の並びを同じ枠でワザを使ったポケモンのワザとして処理します（必要な
  エネルギーはいらない。弱点・抵抗力はワザを使ったポケモンのタイプ）。使うワザの条件がたりないときに選べるかは、要素の `copy_problem` と説明の条件 `clause`
  （`CANNOT_USE`（ピクシー）・`FOLLOW_TEXT`（ピッピ。kyuura の card_differences の記録の解説）・None（カスミのコダック））で決めます。決められなければ選べるが選ぶと
  止める（HC9）。番をまたぐ効果をワザを使ったポケモンに与える要素（`SelfRetaliation`・`SelfNextTurnAttackDamage`）は `UNSUPPORTED_COPIED_ATTACK`（エンジンの未対応。
  研究の対応表の停止コードに入れない）。要素を加えたら `copy_problem` を確かめてください（既定は None = 使える）。
- 特殊能力: エナジーバーン（`ConvertAttachedEnergy`。TXT-CHARIZARD。使った時点でついているカードを、この番「炎」として数える。`GameState.energy_burn`。ワザに
  必要なエネルギーの確認は `state.energy_types`）・しぜんになおる（`RemoveOwnCounterOncePerTurn`。自分の番ごとに 1 回。回数は `GameState.power_uses_this_turn`。
  ログから数えない）・ほのおでかいふく（`HealOnEnergyAttach`。エネルギーカードをつける処理のあとに `effects.after_energy_attached`。解決の基盤の窓の外なので効果の
  定義の対応表に入れていない）。手札・トラッシュ・ワザからエネルギーカードをつける処理を加えるときは、`after_energy_attached` を呼んでください。
- 書き出しの形式 10 = 形式 9 + `power_uses_this_turn`・`energy_burn`（形式 1〜9 は空なら今までどおり、空でなければ `ValueError`）。不変条件
  `engine._turn_power_problems` が今の番のログと照らします。
- ワザの途中の決定の種類 `select_attack`・`discard_opponent_energy`・`attach_to_bench`・`recover_trainer`・`attach_from_discard` を加えました（段階・再開先・コマンドは同じ）。
  2 つ以上の決定を出すワザが決定をまたいで使う値（ワザ全体のコイン・使っているワザ・「とうめい」の結果・処理した送る効果の数 `FrameState.fired`・こんじょうの写し）は、
  `AttackRun.suspend(carry=True)` が決定の `context` に明示的なデータで運びます（v0.18d の案 B の持ち方。`PendingDecision` に項目を加えない）。窓の途中の決定は加えていません。
- ワザの途中の決定を待つ間だけ、同じワザのダメージの要素で HP 以上になったポケモンが場に残ることを不変条件が許します（`engine._attack_damage_awaiting`。今の番の
  ログの最後のワザの宣言のあとのダメージで確かめる狭い例外。広げないでください）。
- 控えポケモン・複数のポケモンにダメージ・効果を与えるワザで、v0.30 まで起こらなかった問い（T27・C34/C35・G40・P19・P32）が起こるようになったので、停止コード
  （`UNRESOLVED_TRANSPARENCY_COIN_ORDER`・`UNRESOLVED_MULTIPLE_DAMAGE_TRIGGERS`・`UNRESOLVED_KO_PREVENTION_ORDER`・`UNRESOLVED_PHOENIX_GAS_SOURCE_KNOCKOUT`・
  `UNRESOLVED_POST_KNOCKOUT_POWERS_ORDER`）を付けて宣言の前に止めます（分類は変えていない）。新しい未解決は HC1〜HC10（docs/held-cards-v0.31.md 5 章）。エンジンが止める
  `UNRESOLVED_…` は 37 件、未解決の裁定は 38 件です。
- 先読みの上限（4,096 通り）: v0.31 の型は `v013_checks.VERIFIED` に入れていないので、上限を超えたら `UNSUPPORTED_PREFLIGHT_LIMIT` です（れんぞくファイヤーボールは炎 8 枚
  以上など。docs 8 章）。上限を超える場面を避けるために `VERIFIED` に加えないでください。
- リザードン（PMCG1-021）は対応にしたので、未対応の参照カードの例は、化石の秘密のベトベター（PMCG3-003）・第1弾のゴースト（PMCG1-047）か、登録を除いた登録表
  （tests/helpers.py の `NO_CHARIZARD_EFFECTS`・`no_charizard_pool`）を使います。
- 検証用デッキ `R31`・`K31`・`E31`・`P31` と組（`PAIRINGS_V0_31`）は tools/existing_effect_games.py の `--batch v0.31` です。v0.31 のカードのワザの決定への答え・特殊能力の
  使用・エネルギーをためるために番を終える手順を重ねています（v0.31 のカードのいない組の結果は変わらない）。原典で決められない場面で止まったワザは `V031_STOPS` で
  場から確かめます。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 山札からベンチに出す・ダメージカウンターでダメージが決まる・与えたぶん回復するワザの 13 枚（v0.32）

- 依頼の 13 枚（ニドラン♀ PMCG2-001・第2弾のナゾノクサ PMCG2-002・マダツボミ PMCG2-005・クラブ PMCG3-013・ニドリーナ PMCG2-008・ウツドン PMCG2-011・
  コイキング PMCG1-031・ギャラドス PMCG1-034・キングラー PMCG3-019・ルージュラ PMCG1-048・コンパン PMCG2-004・化石の秘密のズバット PMCG3-002・
  ゴルバット PMCG3-005）を、kyuura データの採用で加えました（対応ポケモン 106 → 119。写しの組 `pool_v0_32`。ワザの登録 202）。カードごとの結果・共通の処理・
  規定と根拠（DB1〜DB9・CD1〜CD5・LL1〜LL7）・止める場面・互換性・検証は docs/bench-search-counter-drain-v0.32.md。ガイドブックは読んでいません。テストの定数は
  tests/helpers.py の `V0_32_POKEMON`（第2弾のナゾノクサは `JUNGLE_ODDISH`、化石の秘密のズバットは `FOSSIL_ZUBAT`。第4弾の同じ名前のカードと取りちがえない）。
- 山札から名前の決まったたねポケモンをベンチに出すワザは、効果の型 `effects.PutBasicFromDeckOntoBench(names)`・要素 `programs.BenchFromDeck`・決定
  `decisions.BENCH_FROM_DECK`（選ぶのはワザを使ったプレイヤー。選べるものは山札の、名前が説明の「」の名前と同じたねポケモンの uid の小さい順。1 匹）です。
  カードは `zones.bench_from_deck` で手札を通さずにベンチに出します（手札に加えてからベンチに出したことにしない）。場のポケモンを作るのは `zones.enter_play`
  （v0.31 までの `engine._enter_play` の本体。手札から出す処理と共通）だけで、場に出た番は今の番（p.310 の進化の制限は手札から出したときと同じ）。
  「ベンチに空きがなければ使えない」はワザを使うための条件（`usage_problem`。`BENCH_FULL`。こんらんのコインの前）、山札に選べるものがなければ出さずに
  （p.309。H5 と同じ読み方）切ります。山札を切るのは既存の `zones.shuffle_deck` だけで、先読み（`res.dry_run`）では切りません（この要素はワザの最後の要素で
  なければならない。ほかの位置に置くと `RuntimeError`）。ログは `bench_from_deck`（出したカードは公開）・`bench_from_deck_none` と、すぐあとの `shuffle`。
  選べたほかの山札のカードはログに書かないでください。トレーナーの `SEARCH_DECK`（手札に加える）の処理・ログを流用しないでください。
- ダメージカウンターの数でダメージが決まるワザは、基本となるダメージ（p.321 の 1 段階）の値 `programs.OwnCountersTimes(per)`（じたばた。自分のカウンター
  × 10。コインなし。0 個なら 0 でダメージを与えない）・`programs.PlusDefenderCounters(per)`（ヨガのポーズ。目安 + 相手の対戦ポケモンのカウンター × 10）です。
  弱点・抵抗力・プラスパワー・ディフェンダーはそのあとの段階で、最終ダメージに直接足さないでください。コインで量を決める既存の `HeadsOwnCounters`
  （いかりのスーパーパンチ）とは別の値です。ヨガのポーズの「相手のポケモン」が相手の場のポケモンすべてを指すかは決められない（CD4）ので、相手の控え
  ポケモンにカウンターがのっているときだけ問い `opponent_pokemon_counters`（`UNRESOLVED_OPPONENT_POKEMON_COUNTERS`）で宣言の前に止めます。英語版の文面で
  決めないでください。
- 与えたぶん回復するワザ（きゅうけつ）は、効果の型 `effects.DamageAndFullDrain` と、メガドレイン・やどりぎのタネと同じ要素 `programs.Drain` の `full`
  （与えたダメージ ÷ 10 個。のっている数まで）です。`Drain` の既定（`full` が偽）はメガドレインの半分の切り上げのままで、変えないでください。与えたダメージは
  最終ダメージ（v0.4d）、ダメージを与えなかったら回復しない（「ダメージを与えたら」。Z23 の「ダメージを与えた後」とは別）、ワザを使ったポケモンが相手の
  「はんげき」などで HP 以上なら回復しない（C16）。ログの監査は `drain_heal` のとりのぞく数を登録の実装（半分・決まった数・与えたぶん）と照らします。
- 相手のワザとして使うとき（ゆびをふる・ちょうのうりょく）、ベンチに空きがなければ、説明にしたがうピッピ・条件がたりなければ使えないとするピクシーでは
  なかまをよぶ・ふえるを選べず、条件を書かないカスミのコダックでは HC9（`UNRESOLVED_COPIED_ATTACK`）です（v0.31 の「ぼーっとする」と同じ `copy_problem`）。
- 書き出しは形式 10 のまま（山札から出したポケモンの場に出た番は形式 7 から。形式 1〜6 はログの `bench_from_deck` の番で分かる）。公開の API は変えていません。
  エンジンが止める `UNRESOLVED_…` は 38 件、未解決の裁定は 39 件です。
- 検証用デッキ `G32`・`W32` と組（`PAIRINGS_V0_32`）は tools/existing_effect_games.py の `--batch v0.32` です（前の版の組の結果は変わらない）。ベンチに空きが
  なくて使えないワザと CD4 で止まったワザは `V031_STOPS` で場から確かめます。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## CD4 の再検討と、相手のエネルギーをトラッシュする・コインで失敗する／ダメージを与えられない・控えにもダメージを与えるワザの 15 枚（v0.33）

- CD4（v0.32。ルージュラの「ヨガのポーズ」の「相手のポケモン」）は、kyuura（研究の基準のコミットと HEAD）とエンジンの記録で再検討し、記録では決まらないので
  未解決のままです（docs/cd4-opponent-energy-coins-v0.33.md 2 章。p.320・p.321 の定義は太字の「相手」1 語のもの、kyuura にルージュラの記録はない、PMCG の文面で
  「相手のポケモン」はこの 1 か所だけ）。言い方の傾向や英語版の文面で決めないでください。v0.32 の「CD4 が 8 回」は、拒否のあった局の数で、ワザの宣言の拒否は
  9 回（どれも拒否のあと対戦を続けた。停止の 2 局は対戦準備の既知の未解決）。
- 依頼の 15 枚（ハクリュー PMCG1-069・化石の秘密のゴルダック PMCG3-016・わるいシャワーズ PMCG4-023・マチスのコイル PMCG5-039・ナツメのコンパン PMCG6-006・
  ニドラン♂ PMCG1-005・ニドリーノ PMCG1-010・パルシェン PMCG3-018・わるいラッタ PMCG4-046・タケシのディグダ PMCG5-044・タケシのサイホーン PMCG5-049・
  マチスのオニスズメ PMCG5-057・サカキのニドラン♀ PMCG6-003・カツラのサイホーン PMCG6-058・カツラのドードー PMCG6-064）を、kyuura データの採用で加えました
  （対応ポケモン 119 → 134。写しの組 `pool_v0_33`。ワザの登録 230）。マチスのコイル PMCG5-039 は v0.29 の PMCG5-037 と同じ名前の別のカード。テストの定数は
  tests/helpers.py の `V0_33_POKEMON`（`LT_SURGES_MAGNEMITE_30`・`FOSSIL_GOLDUCK` など）。
- 相手のエネルギーカードのトラッシュ（はかいこうせん・うずしお・はかいでんぱ・はかいビーム）は、効果の型 `DamageThenDiscardOpponentEnergy(on_heads)` と v0.31 の
  要素 `DiscardOpponentEnergy`（選ぶのはワザを使ったプレイヤー。「トラッシュさせる」も同じ）。ダメージ → （コイン）→ トラッシュ。エネルギーカードがなければ
  トラッシュせず、コインも投げない（p.309。v0.31 のスーパーデストロイと同じ）。kyuura の UQ-ENERGY-DRAIN-NO-ENERGY（特殊能力のだつりょくえき）を、これで
  解決したことにしないでください。自分のエネルギーのトラッシュ（`DiscardOwnEnergy`）と混ぜないでください。
- コインの「うら」で「相手にダメージをあたえることができない」（ニドラン♂の「つのでつつく」。`NoDamageOnTails`。`Damage` の `local_gate`）は、ワザの失敗
  （`FailOnTails`。p.323。ログ `attack_failed`）ではありません。説明に「失敗」とあるワザだけを失敗にしてください。ドリルタックルは `FailOnTailsDamage(coins=2)`
  （2 枚とも「おもて」のときだけダメージ。「おもて」の数 × のダメージにしない）。コインがダメージの要素だけを決めるワザは、「ダメージを受けない」相手に v0.4b の
  `UNRESOLVED_PREVENTED_COIN_DAMAGE` で止めます（`Damage` の `local_gate` も v0.33 から同じ。カードごとに新しい問いを加えない）。
- パルシェンの「からではさむ」（`DamageAndParalyzeOnHeadsElseFail`）は 1 枚のコインでダメージ・マヒ・失敗が決まります（マヒのコインを投げ直さない）。
  「ワザをうけない」相手には HC3（`FailOnTails` の `with_effect`）。既存のねばりつく・じごくがため（`CoinBonusDamageAndParalyze`）はバリアーの相手にもコインを
  投げる（v0.31 から。そろっていない。v0.33 では変えていない）。
- 自分の控えポケモンへのダメージ（ミニじしん。p.320 のダメージの (4)）は `effects.SELF_BENCH`（`BENCH_TARGETS`）と `BenchDamage(own=True)` です。計算は相手の
  控えと同じ（プラスパワーは変えない・ディフェンダーは変える・説明の「弱点・抵抗力に関係なく」）。自分のワザなので「相手のワザによって」の効果ははたらかない。
  相手の控えを 1 匹選ぶダメージ（かけぬける）は要素 `ChosenBenchDamage`（コイン → 決定 `select_pokemon` → ダメージ。控えがいなければコインなし。`carry`）。
- かけぬけるで、相手の対戦ポケモンへのダメージで「ダメージを受けたとき」の効果がはたらいたあとに控えを選ぶ場面は、送る効果を決定をまたいで運べない（v0.18d）
  ので、エンジンの未対応として `UNSUPPORTED_DECISION_AFTER_DAMAGE_TRIGGER`（問い `decision_after_damage_trigger`。研究の対応表の停止コードに入れない）で止めます。
  ダメージの要素のあとに決定を出す要素を加えるときは、同じ確かめを置いてください（`AttackRun.suspend` は送る効果が残ると RuntimeError）。
- 書き出しの形式・公開の API・決定の種類・ログのイベントの種類は変えていません（ログ `damage` の `target` に `self_bench`）。エンジンが止める `UNRESOLVED_…` は
  38 件、未解決の裁定は 39 件のままです。
- 検証用デッキ `N33`・`W33`・`C33` と組（`PAIRINGS_V0_33`）は tools/existing_effect_games.py の `--batch v0.33` です（前の版の組の結果は変わらない）。かけぬけるの
  未対応の場面は `V031_STOPS` で場から確かめます。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。
