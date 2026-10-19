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

- プレイヤーの選択を待つ処理は、`kyuura_engine/decisions.py` の `push_decision` で保留中の決定（`GameState.decision`）を作り、engine.py の再開先（`_RESUMERS`。v0.16b から `engine._answer_decision` が、再開先が `resolution.RESUMES` なら解決の基盤、`trainer` なら `_resume_trainer`、v0.42 から `power` なら `_resume_power`、v0.57 から `stadium` なら `_resume_stadium` に振り分ける）で続けます。段階や保留中のリストを別に増やさないでください。決定は一度に 1 つです。
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
- ワザの効果の実装で、ワザを使う前に分かる「原典で決められない場合」は `AttackEffect.problem` で返します（v0.3c。エンジンがこんらんのコインの前に聞く。v0.3d の対応カードの実装はどれも既定の None）。受け付けるか・拒否のコードがコインの結果で変わらないことを tests/test_effect_preflight_v0_3d.py の `CoinIndependenceTest` で確かめているので、ワザの実装を加えたら `ATTACKS` にも加えます（docs/effect-preflight-v0.3d.md）。こんらんの 20 にプラスパワー・ディフェンダーを計算するかは決められないので、ワザを使うこんらん状態のポケモンにダメージを変えるカードがついていれば、コインの前に `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` で止めます（`engine._confusion_damage_problem`）。v0.46 から、こんらんの 20 に当てはまりうる常にはたらく特殊能力（くつろぐかおり・きょうぼう・なぞのかべ・ふしぎなバリアー）がはたらいているときも、同じコードで止めます（下の「常にはたらく特殊能力の共通の処理（v0.46）」）。
- こんらんで「にげる」に失敗した記録（v0.3c）は、場のポケモンの `PokemonInPlay.retreat_failed_turn`（失敗した番の番号）に持ち、`_end_turn` で消します。プレイヤー単位の「この番はもうにげられない」フラグや、`GameState` の別の一覧にしないでください（p.311 の制限はポケモンごと）。こんらんのまま再宣言したら `RETREAT_ALREADY_FAILED`、失敗のあとこんらんが消えて同じ番にバトル場に戻ったポケモンの宣言は原典で決められないので `UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED`（どちらもエネルギー・コインの前）。形式 1〜5 はこの記録を書き出せない（`ValueError`）ので、形式 6 で比べます。記録は、今の番のログの `retreat_failed`（同じ `pokemon_id`）と対応することを不変条件で確かめています（v0.3d）。テストで記録を置くときは、`build_test_state` の `"retreat_failed_turn"` か、対応するログといっしょに置いてください。進化したら記録を消します（v0.4a。ログ `retreat_failure_cleared`。SUPPORTED。docs/evolution-rules-v0.4a.md の R1）。特殊状態を消す処理（`clear_special_conditions`）には含めず、進化の処理の中で別に消します。特殊状態を回復するトレーナーを加えるときは、この記録の扱いを見直してください。
- ダメージの目安の数字がないワザ（パラスの「キノコのほうし」）は、ダメージの要素がないワザとして実装します（`PutToSleep`。ダメージの計算も `damage` のログもない）。`DamageOnly` に 0 を渡す登録にしないでください（docs/sleep-paralysis-v0.3b.md 4 章）。
- ログのイベントに `turn` の項目を渡さないでください（`add_event` が `ValueError`。ログの `turn` はいつも今の番。マヒの番は `paralyzed_turn`）。
- ログは内部の完全な記録です（引いたカードなどの隠れた情報を含む）。イベントを加えるときは、隠す情報を決まった項目にだけ入れます（docs/architecture-v0.2b.md 9 章）。v0.47 から、プレイヤーに渡す観測（`kyuura_engine/observation.py` の `observe`・`visible_log`）がイベントの種類ごとの見える範囲（`PRIVATE_FIELDS`・`PUBLIC_EVENTS`）を持つので、イベントの種類を加えたら、どちらかの表に加えてください（ない種類は `ValueError`。下の「なにかの化石・ピッピ人形…（v0.47）」）。
- 進化（v0.4a）は、たねポケモン → 1 進化ポケモン、v0.4c から 1 進化ポケモン → 2 進化ポケモンも、同じ `EvolvePokemon(player, card, target)`（`engine._evolve_pokemon`）で扱います。ベイビィ・進化に関わるカードの効果は未実装で（v0.25 のポケモン育て屋さん・v0.42 のエリカのピッピの「つきのちから」を除く。どちらも進化の手順 `evolution.place_evolution_card` を通常の進化と共通に使う。退化は v0.50 のミュウの「たいかビーム」・退化スプレーで、共通の処理 `evolution.devolve`。下の「退化の共通の処理…（v0.50）」）、ベイビィのカードは分類（cards.py）で拒否します。2 進化のカードは段階では拒否せず、1 進化と同じカードごとの条件（進化元の名前・ワザの登録・ポケモンパワーの登録）で分類します（2 進化の段階だからといって一括で対応にしない）。v0.4c〜v0.4e は「ポケモンパワーなし」が条件で、フシギバナは未対応でした。v0.5 でポケモンパワーの登録表を加え、フシギバナのパワー（エナジートランス）とワザ（ソーラービーム）を登録したので、フシギバナは対応になりました（下の「ポケモンパワー（v0.5）」。v0.6 でカメックス、v0.7 でフーディンも対応にした。未対応のパワーを持つ 2 進化の例はリザードン PMCG1-021）。確かめる順番とコードは docs/evolution-rules-v0.4a.md 3 章と docs/stage2-evolution-v0.4c.md 3 章のとおりで、どれも状態を変える前に拒否します。名前は合うが段階が合わない組み合わせ（テスト専用のカードだけで起こる）は `EVOLUTION_STAGE_MISMATCH`（v0.4c）。
- 進化しているポケモンは、いちばん上のカードを `PokemonInPlay.card`、下に重なったカードを `PokemonInPlay.evolution_stack`（下から順。進化していなければ `()`）に持ちます。場のポケモンの番号（`pokemon_id`）は進化しても変えません（実装上の仮定）。p.310 の「別のポケモン」は、いちばん上のカード・`evolved_turn`（いまの姿に進化した番）・特殊状態と失敗の記録と持続する効果（v0.4b）を消すことで表します。進化の条件の「その番の最初から場に出ていた」は `played_turn`（場に出た番。対戦準備は 0。`_enter_play` だけで決める。にげる・交代では変えない）と `evolved_turn` で確かめます（`current_form_turn`）。HP・タイプ・弱点・抵抗力・にげる・ワザは、どの処理もいちばん上のカードの定義を使い、下のカードの定義を見ないでください（v0.49 から、今の姿の定義 `effects.form_def`。［へんしん］・「ばける」のないポケモンではいちばん上のカード。下のカードのワザを使うのは思い出させるの記録の範囲だけ。下の「ワザの出どころ・今の姿（v0.49）」）。
- 進化ではダメージ・エネルギー・ついているトレーナー（`PokemonInPlay.trainers`。効果と有効期限も）を変えません（p.310。ついているトレーナーの効果が続くのは SUPPORTED。docs/evolution-rules-v0.4a.md の E8'）。進化で消える「持続する効果」（p.322・p.323）を持つワザを加えるときは、進化の処理で消します（ついているカードの効果とは分ける）。
- 進化したポケモンがきぜつしたら、`PokemonInPlay.cards()`（重なったカードすべて）をトラッシュします（p.313）。サイドは 1 匹につき 1 枚のままです。
- 進化したあとの HP が、のっているダメージ以下になる場合は原典で決められないので、状態を変える前に `UnsupportedError`（`UNRESOLVED_EVOLUTION_HP`）で止めます。進化の手順の中できぜつを判定しないでください。
- 重なりの形（3 枚まで、下から順の段階 たね → 1 進化 → 2 進化（`cards.EVOLUTION_STAGES`）、すべての隣り合う 2 枚で上のカードの「○○から進化」が下のカードの名前、進化した番の範囲、2 進化の前に 1 進化できる持ち主の番があること、進化した番の特殊状態はログ `evolve` のあとに付いたもの）は `engine._evolution_problems` の不変条件で確かめています。1 進化した番は状態に持たず（`evolved_turn` は最新の進化の番）、そのポケモンの番号のログ `evolve` が重なりの上の側の移り変わりと順番どおりに対応し、番が増えていき、最後の番が `evolved_turn` であることを `_evolution_log_problems` で確かめます（v0.4c。`new_game` からの対戦ではすべての移り変わりにログが要る）。1 進化した番を状態に加えなかった理由（進化の条件に要らない・形式 9 を避ける・ログで確かめられる）は docs/stage2-state-v0.4c.md 5 章。テストで進化したポケモンを置くときは、`build_test_state` の `"evolved_from"`（1 進化は下のたねポケモンのカード id、2 進化は下のカード id のリスト [たね, 1 進化]。v0.4c）・`"evolved_turn"`・`"played_turn"` を使ってください（作った重なりのログは置かないので、不変条件はあるログだけを確かめる）。
- 形式 1〜6 は進化しているポケモンを書き出せない（`ValueError`）ので、進化のある対戦は形式 7 で比べます。進化していない状態は形式 1〜6 で今までと同じに書き出します（`played_turn` はログから分かるので古い形式には入れない）。
- 2 進化（v0.4c）は、v0.4a の前提（docs/architecture-v0.4a.md 10 章・docs/architecture-v0.4b.md 14 章・docs/evolution-state-v0.4a.md）を見直して、重なりの長さを 1 から 2 までに広げました（いちばん下がたねポケモン・`EVOLVED_THIS_TURN` は変えていない。同じ番の 1 進化 → 2 進化もこれで拒否する）。2 進化ポケモンがきぜつしたら 3 枚すべてとついているカードをトラッシュし、サイドは 1 枚です。退化・ベイビィ・1 進化を飛ばす進化を加えるときは、先に docs/architecture-v0.4c.md 14 章・docs/stage2-state-v0.4c.md 5 章の前提（重なりの上の側とログ `evolve` の対応、いちばん下がたねポケモン、`EVOLUTION_STAGES`）を見直し、原典と照合します（v0.25 でポケモン育て屋さんの 1 進化を飛ばす進化を加えたときに見直した。下の「ポケモン育て屋さん（v0.25）」・docs/pokemon-breeder-v0.25.md 6 章。v0.50 で退化を加えたときにも見直し、退化のログ `devolve` があれば重なりを進化・退化のログを逆にたどって確かめる形にした。docs/mew-devolution-spray-v0.50.md 8 章）。
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
- 書き出しの監査（`serialization_problems`）は、形式 1〜22（v0.6 から 9、v0.31 から 10、v0.44 から 11、v0.47 から 12、v0.48 から 13、v0.49 から 14、v0.50 から 15、v0.56 から 16、v0.57 から 17、v0.58 から 18、v0.59 から 19、v0.62 から 20、v0.63 から 21、v0.67 から 22）が表せる状態だけを書き出し、最新の形式（`LATEST_FORMAT` = 22）から後の項目を除いたものと同じになることを確かめます。状態の項目を加えたら `required_format`・`POKEMON_FIELDS_SINCE`・`TOP_FIELDS_SINCE` を更新してください。形式 23 を加えるときは、監査の `LATEST_FORMAT` と docs/architecture-v0.6.md 4 章を見直します。
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
- どの特殊能力があるかは、いちばん上のカードの定義で決めます（進化前のカードの特殊能力は使えない。p.310）。v0.49 から、今の姿（［へんしん］・「ばける」）のカードの特殊能力と、それを印刷したカードの uid（`effects.powers_of` の `PowerSlot`）で決めます（「ばける」でのせたカードの下のタケシのキュウコンの「ばける」も持つ）。
- 使う前の共通の確認は `engine._use_pokemon_power`、パワーごとの確認（使えない特殊状態・説明が選ばせるもの）は `PowerEffect.check_usable` で、どちらも状態を変える前に済ませます（拒否で状態・乱数・ログが変わらない）。原典で決められない場合は、成功を仮定せず `UnsupportedError`（`UNRESOLVED_…`）で止めます。特殊状態の制限はパワーの説明ごとです。ワザ・にげるの制限（`engine._require_not_asleep_or_paralyzed`・こんらんのコイン）を流用しないでください。
- 「何度でも使える」パワーの回数は数えません。回数の制限のあるパワー（「自分の番ごとに1回」など）を加えるときは、回数を状態に持ちます（ログから数えない。書き出しの新しい形式と不変条件が要る。v0.6 の `energy_attached_by_powers_this_turn` と同じ形。v0.31 のしぜんになおるは `power_uses_this_turn`（形式 10）で、同じ形のパワーは `PowerEffect.once_per_turn = True` にすればこの記録を使える。v0.42 から宣言のときに記録する。v0.44 で形式 11（場のポケモンの `attacks_used_once`・`evolution_permission_turn`）、v0.47 で形式 12（最上位の `trainer_locks`）、v0.48 で形式 13（場のポケモンの `type_shift`）、v0.49 で形式 14（場のポケモンの `disguise`・最上位の `recalls`）、v0.50 で形式 15（場のポケモンの `devolved_turn`）、v0.56 で形式 16（最上位の `trainer_effects`・トレーナーの使用の禁止の `origin`）、v0.57 で形式 17（最上位の `stadium`・`stadium_uses_this_turn`・`trainer_in_use.user`）、v0.58 で形式 18（最上位の `trainer_stack`・`trainer_in_use.via`）、v0.59 で形式 19（最上位の `energy_roles`）、v0.62 で形式 20（場のポケモンの `history`）、v0.63 で形式 21（最上位の `set_aside`・`face_up_prizes`）、v0.67 で形式 22（最上位の `face_down_cards`）を加えた。次の新しい形式は 23）。v0.50 から、記録は使ったカードで区別する（いちばん上のカードが進化・退化で変わる直前に (番号, 位置, 使ったカード) に置きかえる。`evolution.retag_power_uses`）。v0.5 のパワーは決定を出しません。決定を出すパワーは、ワザ（v0.4d）・トレーナー（v0.4e）と同じく `resume`・`decision_problems` と再開先（v0.42 の `"power"`）で扱います（下の「特殊能力の決定・再開・使用後の処理と 15 枚（v0.42）」）。自動的にはたらく・常にはたらくパワーは宣言しないので、`UsePokemonPower` の形では扱いません（どちらも `PowerEffect.declared = False`。常にはたらくパワーは下の「かがくへんかガス（v0.8）」・「常にはたらく特殊能力の共通の処理（v0.46）」、自動的にはたらくパワーは下の「とうめい（v0.9）」「はんげき（v0.10）」。docs/architecture-v0.5.md 9 章）。決められたときにしか使えない（宣言する）パワーは `declared = True` のまま `check_usable` で拒否し、決められたときにエンジンが決定で使うかを聞きます（下の「こんじょう（v0.11）」。場に出たときに 1 度だけ使えるパワーも同じ形で、`effects.EntryPower` と決定 `entry_power`。下の「宣言して使う特殊能力と場に出たときの特殊能力の入口（v0.43）」）。
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
- ロケット団のベトベター（PMCG4-004）の「どくガス」は `PoisonWithoutDamage`（ダメージの目安なし・コインなし。ダメージの目安のあるワザの `PoisonOpponent` を流用しない）、「ねばりつく」は `CoinBonusDamageAndParalyze(bonus=20)`（コイン → 基本となるダメージ（「おもて」なら + 20）→ きぜつしていなければマヒ。「ダメージを受けない」相手にもコインを投げる）、ベトベトンの「ヘドロこうげき」は `PoisonOnHeads` です。裁定は docs/grimer-line-v0.8.md（M1〜M9）。化石の秘密のベトベター（PMCG3-003）は v0.36 まで参照カード（「ちいさくなる」が未実装）で、v0.37 で対応にした（下の「既存の効果の再利用…（v0.37）」）。
- 書き出しは形式 9 のままです（v0.8 で状態の項目・形式を加えていない。監査の `LATEST_FORMAT` も 9）。
- ストレス実行（tools/stress_engine.py）は、ベトベトンの組（`muk`・`muk_mixed`）でかがくへんかガスの場面を混ぜます。`POWER_USERS` の並びの最後にベトベトンを加えたので、ベトベトンのいない組の操作（乱数の使い方）は v0.7 と同じです。比較の駆動（tools/compat_driver.py）は変えていません。

## とうめいと自動的にはたらく特殊能力（v0.9）

- ゴースト（PMCG3-030。化石の秘密）の「とうめい」は `effects.AttackImmunityOnHeads`（`PowerKey("PMCG3-030", 0)`）です。決められたとき（ワザによってダメージや効果を受けるとき）に自動的にはたらき、使用を宣言しない（p.323）ので `declared = False` で、`UsePokemonPower` は `POWER_NOT_DECLARABLE`。裁定は docs/transparency-v0.9.md（T1〜T42・A4）、仕組みは docs/automatic-powers-v0.9.md、設計は docs/architecture-v0.9.md、確かめた結果は docs/v0.9-verification.md。第1弾のゴースト（PMCG1-047）は同じ名前の別のカード（v0.44 まで参照カード。v0.45 で対応にした。とうめいを持たない）で、取りちがえないでください。
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
- 「わるいねぞう」の 20 は特殊能力によるダメージです（p.245。CONFIRMED）。弱点・抵抗力を計算するかは原典で決まらない（Z9）ので、`ignores_weakness_resistance = False` の特殊能力のダメージで、受けるポケモンの弱点・抵抗力が与えるポケモンのタイプなら、問い `power_damage_weakness_resistance` で止めます（R団のカビゴンは無色で、今のカードでは起こらない。v0.61 で［ファイナルビーム］で起こるようになり、停止コード `UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE` を付けた）。はんげきは `ignores_weakness_resistance = True`（「弱点・抵抗力」に関係なく）。そろってのきぜつ（Z13）は C18 と同じ問い・同じコード `UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT` で、理由の文は特殊能力の名前とページ（`effects.power_name_and_page`。はんげきは v0.16 までと同じ文）です。新しいコードにしないでください。
- 「たおれこむ」は `effects.DamageAndSelfSleep`（`AttackKey("PMCG6-073", 0)`。要素の並び `Damage(OPP)` → `Status(SLEEP, target=SELF, after_damage="damage")`）です。要素 `Status` の `target`（`OPP`・`SELF`）と `after_damage`（「ダメージを与えた後」の効果の、もとのダメージの要素の名前）は汎用の項目で、カードごとの要素を加えないでください。自分への効果も `reaches` で「とうめい」を評価し、対象が HP 以上なら飛ばします（自分がこんじょうを使える場合は G37 と同じ問いでコードのない `ko_prevention_self_effect`。今のカードでは起こらない）。
- 「ダメージを与えた後、…」の効果で、そのダメージの要素がダメージを与えなかった（`DamageResult.dealt` が 0。ディフェンダーで 0・「ダメージを受けない」状態・「とうめい」）ときに効果を与えるかは原典で決まらない（Z23）ので、宣言の前に `UNRESOLVED_EFFECT_AFTER_NO_DAMAGE`（問い `effect_after_no_damage`。優先度 10）で止めます。「ダメージを与えた後」の効果を加えるときは `after_damage` を書いてください。成功を仮定するテストを書かないでください。
- キョウのベトベトン（PMCG6-023）の「だつりょくえき」は実装を延期しました（v0.17c。DEFER。docs/kogas-muk-event-design-v0.17c.md）。宣言する特殊能力か（DR1）・処理する時点（DR6）が原典で決まらず、今の KERNEL はダメージの要素のあとの窓の中で決定を出して続けられません（`AttackRun.suspend` は送る効果が残っていれば RuntimeError。決定をまたいで `FrameState`・`Resolution` の値は残らない）。カードは分類で拒否したままにしてください（効果のないものとして扱わない）。実装するときは、同じ文書 6 章の手順（自動なら続きの情報を既存の `decision.context` に明示的なデータで持つ案 B、宣言するならきぜつの判定の窓の任意の効果の拡張）にしたがいます。`PendingDecision` に項目を加える形（案 A）は形式 9 を保てないので採らないでください。（v0.68 で、DR1・DR6 を採用の仕様にして案 B で実装した。下の「ガルーラ・キョウのベトベトン・イマクニ？のドードーと、マチスの秘策の受け付けの修正（v0.68）」。この段落は v0.17c の時点の約束。）
- 比べる方法 `legacy`（v0.13 の止める関数の先読み）は、`v013_checks.VERIFIED` の型だけにそれを使い、ほかの型（v0.17 から加えた型）はすべての結果を試す方法で確かめます（v0.17d。`flow._use_attack`）。v0.13 の止める関数は v0.17 の問い（Z23 など）を知らず、使うとコインの結果で受け付けるかが変わります（docs/card-extensibility-verification-v0.17d.md 6 章。tests/test_rocket_snorlax_v0_17b.py `test_no_damage_stops_in_every_preflight_mode`）。新しい型を `legacy` のためだけに `VERIFIED` に加えないでください。
- エンジンが止める `UNRESOLVED_…` は 18 件（v0.16 までの 17 件は変えていない）、未解決の裁定は 24 件（Z9・Z23 を加えた。Z13 は C18、Z18 は C34/C35 と同じ問い）。だつりょくえきの DR1・DR6・DR8・DR13・DR18 は、カードが未対応なのでエンジンの止める処理はなく、延期の理由として記録しています。
- 書き出しは形式 9 のまま、ログのイベントの種類・状態の型・`engine.py` は変えていません。ストレス実行の組 `snorlax`・`snorlax_mixed` は `ALL_SCENARIOS` の最後、`POWER_USERS` の最後に R団のカビゴンを加えたので、R団のカビゴンのいない組の操作は v0.16 と同じです。固定した v0.16（`15770c6`）との比較は、`tools/engine_lockstep.py record` の `--scenarios` に v0.16 の 26 組を渡して新しいカードの組を除きます（docs/card-extensibility-verification-v0.17d.md 3 章）。新しいカードの対戦のテストは tests/v017_games.py の `play_game(decks, seed, ...)`（v0.13 の対戦の手順をデッキを引数にして使う）。

## 研究データとの同期と検証の再現性（v0.18）

- 研究の基準は kyuura `3f349085645f47d0649a6cacece3680caeae50bf`（v0.18 は `adf97107ee0d9755cd7ddedae298ecb02914128e`。2026-10-15 に上げた。上の「研究資料の参照コミットを固定する」）。エンジンの停止コード・問い・未解決の裁定・登録した最新の説明・照合の記録と、kyuura の id（論点 UQ-・裁定 CR-・最新の説明 LD-・照合 CC-）の対応は `kyuura_engine/data/research_links.json` に持ちます。kyuura の記録（文面・分類・根拠）を写さないでください（id の対応だけ。正本は kyuura）。docs/research-alignment-v0.18a.md。
- 停止コード・問い（`questions.QUESTIONS`）・最新の説明のある登録（`play_text_ja`）・照合の記録を加えたら、対応表も直します（tests/test_research_links_v0_18e.py が、エンジンの側の集合と対応表を照らす）。最新の説明のある登録は、kyuura の LD-（`registered`）・印刷の文面と同じで kyuura の CC- に書かれたもの（`recorded_in_card_checks`）・CC- はあるがワザの文面を照合していないもの（`card_checks_without_text`）・kyuura に記録なし（`registered_without_kyuura_record`）・kyuura データの採用で処理に使う文面を kyuura の印刷の文面にしたもの（`adopted_printed_text`。2026-10-15 からの方針。エンジンが原典と照合した記録ではない）・処理に使う文面を kyuura のエラッタ（ERR-・TXT-・RUL-）にしたもの（`errata_text`。v0.30）・処理に使う文面を kyuura の data/curation/card_differences.json の記録（確度: 確実）の最新の説明にしたもの（`difference_text`。v0.31。ピッピの「ゆびをふる」・v0.42 のカイリューの［かけつける］。LD- がない）のちょうど 1 つに挙げます（2026-10-15 から）。エラッタの記録の `cards` にないカードに、記録の範囲（「…はすべて同じ処理」など）として当てはめるときは、`errata_scope` に記録の文の引用・記録が挙げるカードの同じ印刷の文面・対象を書きます（v0.30。検査が研究の基準のコミットの記録と照らす。印刷の文面が違うカードに当てはめない）。kyuura に記録がなければ `registered_without_kyuura_record`・`engine_verified_without_kyuura_record` に挙げ、kyuura への報告事項にします（2026-10-15 の取り込みで空になり、v0.19 で `engine_verified_without_kyuura_record` にオーキドはかせ（PMCG1-077）、v0.21 で突風（PMCG1-072）、v0.22 でパソコン通信（PMCG1-090）、v0.23 でエネルギー回収（PMCG1-076）、v0.24 でポケモン交換おじさん（PMCG1-093）、v0.25 でポケモン育て屋さん（PMCG1-094）、v0.27 でストライク（PMCG2-017。`registered_without_kyuura_record` にも「つるぎのまい」の PMCG2-017/attack/0）、v0.28 で既存の効果の型で加えたポケモン 10 枚（`registered_without_kyuura_record` に説明文のあるワザ 13）を加えた。kyuura に記録ができたら、検査が一覧を直すよう知らせる）。v0.29 の採用の記録で加えたポケモン 14 枚の説明文のあるワザ 14 は `adopted_printed_text` に挙げています（kyuura への報告事項ではない。v0.30 でとっしん・第4弾のポニータのひのこを加えて 16。v0.31〜v0.51 の採用で加えたワザ・特殊能力も同じ区分）。kyuura の未解決の一覧（`engine_unresolved_index`）にまだない停止コードは、`stop_codes` の `kyuura_disposition` を `not_in_kyuura` にします（v0.21 の `UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH`・v0.22 の `UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK`・v0.23 の `UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET`・`UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE`・v0.31 の HC1〜HC10 の 10 件・v0.32 の CD4（`UNRESOLVED_OPPONENT_POKEMON_COUNTERS`）・v0.34 の TP3（`UNRESOLVED_SPECIAL_POISON_OVERWRITE`）・NK5（`UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET`）・v0.36 の AC6（`UNRESOLVED_ATTACK_CHECK_CONFUSION`）・RD9（`UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT`）・v0.37 の JS1（`UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE`）・v0.38 の GK1（`UNRESOLVED_DAMAGE_TRIGGER_TIMING`）・v0.39 の GS1（`UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE`）・v0.40 の SG1（`UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED`）・v0.41 の CX1（`UNRESOLVED_COUNTER_TRANSFER_PROTECTED`）・v0.42 の PW1（`UNRESOLVED_POWER_SWITCH_WITHOUT_OPPONENT_BENCH`）・PW2（`UNRESOLVED_POWER_DISCARD_WITHOUT_HAND`）・v0.43 の PW3（`UNRESOLVED_POWER_ZERO_CARDS`）・PW4（`UNRESOLVED_ENTRY_POWER_DURING_ATTACK`）・v0.44 の FC1（`UNRESOLVED_STATED_CARDS_SHORT`）・TR1（`UNRESOLVED_TRAINER_WITHOUT_TARGET`）・v0.45 の GV1（`UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK`）・AC13（`UNRESOLVED_MULTIPLE_ATTACK_CHECKS`）・v0.46 の CP1（`UNRESOLVED_CALMING_AROMA_RETALIATION`）・CP2（`UNRESOLVED_RETREAT_COST_FLOOR`）・v0.47 の PF1（`UNRESOLVED_PLAY_AS_POKEMON_SETUP`）・PF2（`UNRESOLVED_PLAY_AS_POKEMON_RETREAT`）・PF3（`UNRESOLVED_BREEDER_ON_PLAY_AS_POKEMON`）・KA1（`UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER`）・v0.48 の VS1（`UNRESOLVED_SHIFT_COLOR_DURATION`）・PG1（`UNRESOLVED_CHANGE_ABSENT_WEAKNESS_RESISTANCE`）・MH1（`UNRESOLVED_MAX_HP_DROP`）・v0.49 の TE1（`UNRESOLVED_TRANSFORM_ENERGY_COUNT`）・TF1（`UNRESOLVED_TRANSFORM_COPIED_POWER`）・TF2（`UNRESOLVED_TRANSFORM_MODIFIED_DEFENDER`）・DG1（`UNRESOLVED_SHAPESHIFT_SUPPRESSED`）・DG2（`UNRESOLVED_SHAPESHIFT_ENTRY_POWER`）・DG3（`UNRESOLVED_SHAPESHIFT_AGAIN`）・VA1（`UNRESOLVED_VIRTUAL_ONCE_ATTACK`）・RC1（`UNRESOLVED_RECALL_WITHOUT_PRE_EVOLUTION_ATTACK`）・RC2（`UNRESOLVED_RECALL_EARLIER_STAGE`）・RC3（`UNRESOLVED_RECALL_TARGET_CHANGED`）・RC4（`UNRESOLVED_RECALL_FORM`）・v0.50 の DV1（`UNRESOLVED_DEVOLUTION_INTERMEDIATE_KNOCKOUT`）・DV2（`UNRESOLVED_EVOLVE_AFTER_DEVOLUTION`）・DV3（`UNRESOLVED_POWER_REUSE_AFTER_DEVOLUTION`）・DV4（`UNRESOLVED_DEVOLUTION_SPRAY_WITHOUT_TARGET`）・DV5（`UNRESOLVED_DEVOLUTION_TARGET_DISGUISED`）・v0.51 の RV1（`UNRESOLVED_REVIVE_WITHOUT_TARGET`）・FT1（`UNRESOLVED_POKEMON_FLUTE_WITHOUT_TARGET`）。kyuura に記録ができたら検査が知らせる）。kyuura の未解決の一覧でコードのない行に、エンジンが停止コードを付けたもの（v0.31 の T27・C34/C35・G40・P19・P32）は、`kyuura_index_engine_key` でその行を指します。エンジンが一般の規定・裁定として当てはめた kyuura の記録（退化の規定など。v0.50。トラッシュからベンチに出すワザの手順・ダメージカウンターの規定。v0.51）は、`applied_rule_records` に id・種類・エンジンの番号だけで結びます（検査が研究の基準のコミットに記録があることと種類を確かめる。記録の文面は写さない）。`../kyuura` があれば `python3 scripts/check_research_links.py --kyuura ../kyuura` が、論点の分類（UNRESOLVED のままか）・エンジンの未解決の一覧・分類の違い・最新の説明の文面・照合の記録・カードデータの違いを、研究の基準のコミットの記録と照らします。kyuura で論点が UNRESOLVED でなくなったら、このスクリプトが失敗します。そのときは、根拠を docs に書いてから止める処理を見直します（エンジンの判断で先に決めない）。
- カードの写しの元（`KYUURA_COMMIT` = `ecb2d69`）と研究の基準（`3f34908`。v0.18 は `adf9710`）は別に持ちます。状態はカードデータの元のコミット（`state.card_data.commit`・ログ `game_created`）を持ち、写しのコミットを上げると固定した参照データがすべて変わるからです。エンジンが使う項目が 2 つのコミットで同じことは、上のスクリプトが確かめます（違いは対応表の `card_data_differences` だけ）。
- 分類（CONFIRMED・SUPPORTED）は kyuura の記録を正本にします。エンジンの過去の版の裁定の表は当時の記録として書き換えません（v0.18a の分類の違い 17 件。どれも処理は同じ）。コインの有無・順番だけが変わる論点（kyuura の rng_only）を、実装の約束として決めることは v0.18 では採っていません（docs/research-alignment-v0.18a.md 7 章）。
- Z23 は、ダメージを与えなかった場合を Z23-a（要素が無効）・Z23-b（計算の結果が 0。ディフェンダー・抵抗力）・Z23-c（「とうめい」）・Z23-d（対象がいない。今のワザでは起こらない）に分けて記録しています（docs/unresolved-research-v0.18b.md 3 章）。どれか 1 つの答えが見つかっても、ほかの場合を同じに扱わないでください（理由の文が場合を書く。tests/test_unresolved_research_v0_18b.py）。「ダメージを与えた後」の効果のダメージの要素は、並びの最初でコインで飛ばされない形にしています（Z23-d が起こらない。崩すワザを加えるときは Z23-d を原典で確かめる）。
- ナツメのヤドン（PMCG6-044。v0.18c）の「ぐうたらこうげき」は、たおれこむと同じ実装の型 `DamageAndSelfSleep` の登録だけです（カードごとの分岐・新しい要素はない）。超のワザなので、抵抗力 超 の相手で Z23-b が起こります（止める）。docs/kernel-reuse-v0.18c.md。
- 窓の途中の決定（ダメージの要素のあとの窓で決定を出す効果）は、v0.18d でも DEFER です（docs/mid-window-decisions-v0.18d.md）。p.100［にげこむ］のとおり、宣言する特殊能力でもワザの最中（ダメージのあと・効果の前）に使う例があるので、だつりょくえきは DR1 がどちらでも案 B（`decision.context` の明示的な続きの情報）が要る可能性があります。実装するときは同じ文書の 6 章の 6 つの性質を受け入れの条件にし、9 章の手順にしたがいます。tests/test_mid_window_decisions_v0_18d.py は設計の前提（`FrameState` の項目・送る効果が残ると止まれない・決定を出す送る効果がない）を固定しています。テストの期待だけを変えないでください。（v0.68 で、だつりょくえきの決定を、ダメージの要素のまとまりのあとの要素のあいだの決定（v0.65 の形）として加え、テストの固定を直した。下の v0.68 の節。）
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
- 「「60」になる」は p.321 の 2 段階で、ダメージをその数にする効果（`damage.DamageModifier` の `operation=SET`。既定は `ADD`）です。最終ダメージに直接足したり、最終ダメージを 2 倍にしたり、8 段階で置きかえたりしないでください。弱点・抵抗力・プラスパワー・ディフェンダーはそのあとの段階で計算します。同じ段階に加算でない効果とほかの効果が重なったら、計算の順番を選ぶ決定（p.321。2 段階はワザを使うプレイヤー）がないので `calculate_attack_damage` が `RuntimeError` で止めます（今の対応カードでは起こらない）。2 段階のほかの効果を加えるときは、先に順番を選ぶ決定を加えてください（v0.35 で加えた。下の「可変枚数のコインの先読みとダメージの計算の順番の決定（v0.35）」）。
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
- リザードン（PMCG1-021）は対応にしたので、未対応の参照カードの例は、キョウのベトベトン（PMCG6-023。v0.68 で対応にしたので、v0.68 からは登録を除いた登録表だけ）か、登録を除いた登録表
  （tests/helpers.py の `NO_CHARIZARD_EFFECTS`・`no_charizard_pool`。v0.37 で対応にした化石の秘密のベトベターは `NO_FOSSIL_GRIMER_EFFECTS`・`no_fossil_grimer_pool`、
  v0.45 で対応にした第1弾のゴースト（PMCG1-047）は `NO_BASE_HAUNTER_EFFECTS`・`no_base_haunter_pool`）を使います。
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
  投げる（v0.31 から。そろっていない。v0.33 では変えていない。v0.34 で、コインが決めるものから同じ HC3 にそろえた。`with_effect` の旗は外した。下の v0.34 の節）。
- 自分の控えポケモンへのダメージ（ミニじしん。p.320 のダメージの (4)）は `effects.SELF_BENCH`（`BENCH_TARGETS`）と `BenchDamage(own=True)` です。計算は相手の
  控えと同じ（プラスパワーは変えない・ディフェンダーは変える・説明の「弱点・抵抗力に関係なく」）。自分のワザなので「相手のワザによって」の効果ははたらかない。
  相手の控えを 1 匹選ぶダメージ（かけぬける）は要素 `ChosenBenchDamage`（コイン → 決定 `select_pokemon` → ダメージ。控えがいなければコインなし。`carry`）。
- かけぬけるで、相手の対戦ポケモンへのダメージで「ダメージを受けたとき」の効果がはたらいたあとに控えを選ぶ場面は、送る効果を決定をまたいで運べない（v0.18d）
  ので、エンジンの未対応として `UNSUPPORTED_DECISION_AFTER_DAMAGE_TRIGGER`（問い `decision_after_damage_trigger`。研究の対応表の停止コードに入れない）で止めます。
  ダメージの要素のあとに決定を出す要素を加えるときは、同じ確かめを置いてください（`AttackRun.suspend` は送る効果が残ると RuntimeError）。
  （v0.34 で、送る効果を決定の `context` で運ぶようにして、この止める処理と問いを外した。下の v0.34 の節。）
- 書き出しの形式・公開の API・決定の種類・ログのイベントの種類は変えていません（ログ `damage` の `target` に `self_bench`）。エンジンが止める `UNRESOLVED_…` は
  38 件、未解決の裁定は 39 件のままです。
- 検証用デッキ `N33`・`W33`・`C33` と組（`PAIRINGS_V0_33`）は tools/existing_effect_games.py の `--batch v0.33` です（前の版の組の結果は変わらない）。かけぬけるの
  未対応の場面は `V031_STOPS` で場から確かめます。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## バリアーに対するコインの見直し・ダメージのあとの決定をまたぐ処理と 14 枚（v0.34）

- 依頼の 15 枚のうち 14 枚（ギャロップ PMCG2-019・ブースター PMCG2-020・シャワーズ PMCG2-023・サンダース PMCG2-026・エレブー PMCG1-041・ケンタロス PMCG2-042・
  タケシのロコン PMCG5-018・サカキのカイロス PMCG6-024・カツラのガルーラ PMCG6-069・ドガース PMCG1-006・ニドキング PMCG1-013・ナッシー PMCG2-012・
  カラカラ PMCG2-029・ガラガラ PMCG2-032）を、kyuura データの採用で加えました（対応ポケモン 134 → 148。写しの組 `pool_v0_34`。ワザの登録 257）。ガルーラ PMCG2-046 は
  pcg-search.com との照合でこどものおつかいのコインの有無が違う（挙動に影響する）ので保留（`card_sources.json` の `on_hold`。登録しない。写しには保留の記録のために
  入れた。v0.68 で、利用者が示した訂正を写しの作り直しで当てはめて登録した。下の v0.68 の節）。カードごとの結果・共通の処理・規定（TP1〜TP4・NK1〜NK5）・止める場面・互換性・検証は docs/barrier-resume-coin-bonus-v0.34.md。ガイドブックは読んでいません。
  テストの定数は tests/helpers.py の `V0_34_POKEMON`（14 枚）・`V0_34_POOL`（15 枚）。タケシのロコン・サカキのカイロス・カツラのガルーラは、名前の似た別のカードと
  取りちがえないでください。
- 要素の並びのコイン（`Coin`）と失敗するコイン（`FailOnTails`）は、投げる前に `programs.void_coin_question` を呼びます。コインの結果で処理が決まる要素
  （`Element.coin_dependent`）がどれも相手の対戦ポケモンへの要素（`Element.coin_receiver` が `"damage"`・`"effect"`）で、どれも無効なら、T19b・HC3（効果を含む）・
  v0.4b の `UNRESOLVED_PREVENTED_COIN_DAMAGE`（ダメージだけ）で止め、ほかは投げます（自分へのダメージ・自分への効果・トラッシュ・ドローなど有効な要素があれば投げる。
  kyuura の CR-STICKY-VS-PREVENTED と同じ読み方）。これでねばりつく・じごくがためもバリアーの相手に HC3 になりました（v0.33 まで投げていた。既存の動作の変更）。
  止めるかを型の旗やカード id で決めないでください。コインを使う要素を加えるときは `coin_dependent`・`coin_receiver` を確かめてください（既定は None = 有効）。
- ダメージの要素のあとに決定を出す要素（`ChosenBenchDamage`。かけぬける・v0.34 のうしろなげ）は、まだ処理していない送る効果（「ダメージを受けたとき」の効果）を、
  決定の `context` の `frame` の `pending`（(持ち主, ポケモンの番号, 効果の定義の名前, 受けたダメージ)）で運び、再開のときに `kernel.restore_deferred` が今の場の
  効果から作り直します（`AttackRun.suspend(carry=True)`。v0.18d の案 B の持ち方。`PendingDecision` に項目を加えない）。送る効果は、控えへのダメージのあと・ダメージ以外の
  効果の前に処理します（p.89）。`carry` でない決定の前に送る効果が残っていれば、今までどおりエンジンの不具合（RuntimeError）です。運ぶ値は不変条件
  （`engine._carried_deferred_problems`）が場とログで確かめます。窓の途中の決定（だつりょくえきのような、ダメージの要素のあとの窓の中で決定を出す効果）は
  加えていません（v0.18d の DEFER のまま。v0.68 でだつりょくえきの決定を加えた）。
- 特殊などく（ニドキングの「どくどく」）は `Status(POISON, poison_damage=20)` と `conditions.poison(..., damage=20)` で、どく状態の量（`Poison.damage`）を 20 に
  します（p.322 の「どく状態にかかる」もの。v0.3a の 13）。通常のどくを 2 回にする形にしないでください。受けるダメージの違うどく状態から特殊などくにする場合
  （v0.3a の 15。TP3）は宣言の前に `UNRESOLVED_SPECIAL_POISON_OVERWRITE` で止めます。特殊などく → 通常のどく（v0.3a の 14）は既存の処理のまま。
- カラカラの「なきつく」は相手に与える持続する効果 `state.ReducedDamageToSource`（`on_opponent`・`expires_at_turn_start`）で、受けたポケモンが「このカード」に
  ワザでダメージを与えるとき p.321 の 2 段階で量をへらします（`effects.attack_damage_modifiers`）。期限は説明のとおり次の自分の番の始め（`procedures.begin_turn` の
  `remove_turn_start_expired_persistent_effects`）。番の始めに消える効果を加えるときは `expires_at_turn_start` を使ってください。カラカラが控えにいるときの控えへの
  ダメージは NK5（`UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET`）で止めます。同じ 2 段階に「その数にする」効果（つるぎのまい）とほかの効果が重なったら、順番の決定が
  未対応なので `UNSUPPORTED_DAMAGE_STEP_ORDER`（研究の対応表の停止コードに入れない）で止めます（v0.35 で、ダメージの要素では順番の決定を出すようにした）。
- ギャロップの「こうそくいどう」はバリアーと同じ `AttackBarrier`（`SelfPersistent` の `local_coin`）、ナッシーの「テレポート」は要素 `SelfSwitch`（入れ替えは
  `effects._switch_active_with_bench(..., effect=)`。ログ `switch` に `effect`）、「たまなげMAX」は値 `HeadsTimesAttachedEnergy`（コインの数 = `state.energy_types` の数。
  先読みは 2 のエネルギーの数乗。13 枚から `UNSUPPORTED_PREFLIGHT_LIMIT`。v0.35 で「おもて」の数でまとめ、エネルギーの数 + 1 通り）、ガラガラの「たすけをよぶ」は `BenchFromDeck` の `pokemon_type`（闘のたねポケモン）、
  ドガースの「くさいガス」は `Status` の `otherwise`（同じコインの「うら」）、かみなりパンチ・あばれるは `CoinBonusOrSelfDamage`（1 枚のコイン）、ブースターの
  「かえんほうしゃ」は `DiscardEnergyBeforeDamage(炎, 1, "effect", "fail")`（トラッシュの時点は RUL-ENERGY-DISCARD-ATTACKS の範囲としてワザの効果。処理に使う文面は
  印刷の文面）。v0.34 の型は tests/helpers.py の `ATTACK_TYPES_SINCE_V0_17` にあり、`v013_checks.VERIFIED` に入れていません。
- エンジンが止める `UNRESOLVED_…` は 40 件、未解決の裁定は 41 件です（TP3・NK5 を加えた。どちらも kyuura の未解決の一覧にない `not_in_kyuura`）。書き出しの形式は
  10 のまま（持続する効果の種類 `reduced_damage_to_source` は形式 8 から。量を書く）。公開の API は変えていません。ログの監査（tests/log_audit.py）は、特殊などくの量・
  ポケモンチェックのどくの量・なきつくの 2 段階と期限・たすけをよぶのタイプを確かめます。
- 検証用デッキ `F34`・`G34`・`C34` と組（`PAIRINGS_V0_34`）は tools/existing_effect_games.py の `--batch v0.34` です（前の版の組の結果は変わらない）。TP3・NK5・HC4
  （シャワーズのみずでっぽう）で止まったワザは `V031_STOPS` で場から確かめます。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 可変枚数のコインの先読みとダメージの計算の順番の決定と 5 枚（v0.35）

- 依頼の 5 枚（マチスのコラッタ PMCG5-056・マチスのラッタ PMCG5-059・カスミのニョロモ PMCG5-022・カスミのニョロゾ PMCG5-029・カツラのケンタロス PMCG6-065）を、
  kyuura データの採用で加えました（対応ポケモン 148 → 153。写しの組 `pool_v0_35`。ワザの登録 267）。まとめる条件・順番の決定の仕様・カードごとの結果・互換性・
  検証は docs/coin-groups-damage-order-v0.35.md。ガイドブックは読んでいません。テストの定数は tests/helpers.py の `V0_35_POKEMON`（`LT_SURGES_RATTATA` など）。
  v0.35 の効果の型は `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません。
- 先読み（`resolution/preflight.py`）は、結果を「おもて」の数だけで使うコインを「おもて」の数でまとめて試します（`Oracle.coin_group`。n 枚を n + 1 通り）。
  まとめてよいかは、コインを投げる要素・値が宣言します（`coins.flip_coins`・`AttackRun.flip` の `by_heads`、基本となるダメージの値の ClassVar `by_heads`、
  2 枚以上か枚数が状態で決まる `Coin`、`FailOnTails`）。カード id で決めないでください。投げた順番・何枚目の面を使う要素（`CoinSide` の `gate`）がある
  コインはまとめられないので、`Coin` が `RuntimeError` で止めます。コインのあとの決定（カードの選び方）は、まとめずにすべての答えを試します（選び方の違いを
  同じものとみなさない）。相手と自分へのダメージを同じコインで決めるワザは、組のまま試します（別々に数えた結果を組み合わせない）。
- まとめた先読みの決まった並び（「うら」→「おもて」）は、1 枚ずつ試す先読みで最初に試す並びなので、当たる問いと理由の文は 1 枚ずつ試すときと同じです。
  実際の対戦の乱数（`random.Random`）は `coin_group` を持たないので、今までどおり 1 枚ずつ投げます（乱数・ログ・確率を変えない）。`derived` の記録
  （`RecordingRandom`）は元の乱数で 1 枚ずつ投げ、(「おもて」の数, 枚数 + 1) を 1 つの値として記録します（`tokens`）。上限の数 `MAX_BRANCHES`（4,096）と、
  上限を超えたときの扱いは変えていません。上限を回避するために上限の数を上げないでください。
- `CoinFlipDamage`（`HeadsTimes`）はまとめません（`by_heads` は False。登録で決まった 4 枚以下で、v0.15c・v0.16c の上限の境界のテストがこの値の 1 枚ずつの
  木を基準にしている）。れんぞくファイヤーボールは、コインはまとめるが、トラッシュするカードの選び方が 2 の n 乗通りのままで、炎 13 枚から
  `UNSUPPORTED_PREFLIGHT_LIMIT` が残ります。
- p.321 の 2・5〜8 段階の変更効果は `damage.DamageModifier` の `operation`（`ADD`・`SET`・`MULTIPLY`）で区別します。同じ段階に加算でない効果を含む 2 つ以上の
  効果があり、順番によって結果（最終ダメージと 2 段階で終えるか）が変わるときだけ、`calculate_attack_damage` が `DamageOrderRequired` を投げ、ダメージの要素
  （`programs.Damage`）が `DAMAGE_STEP_CHOOSER` のプレイヤーに決定 `damage_step_order` を出します（選べるものは `damage.step_orders` の位置。`context` に
  決定を出した要素の位置・基本となるダメージ・段階・受けるポケモン・変更効果・選べる順番。`carry=True`）。再開は、選んだ順番を `orders` に渡して計算し直す
  だけで、コインを投げ直しません。順番で結果が変わらなければ決定を出さないでください。コードで順番を決めて計算しないでください。決定を出せない呼ぶ側
  （控えへのダメージ・返す効果のダメージ・v0.13 の約束のワザ・前の要素がダメージを与えた並び）は、問い `damage_step_order`（`UNSUPPORTED_DAMAGE_STEP_ORDER`）
  で止めます。不変条件は `engine._damage_order_decision_problems`。ログ `damage` の `modifiers` は v0.34 と同じ集めた順番で、順番を選んだ段階のものだけを
  その位置の中で並べかえます（`step_orders`・`damage_multiplied` は該当するときだけ）。
- 「きあいだめ」は v0.27 の `NextTurnAttackDamage` に `operation`（`NEXT_TURN_MULTIPLY`）と `includes_self_damage` を明示した値です（種類
  `next_turn_attack_damage_multiplier`）。「つるぎのまい」の「その数にする」の値を 2 倍の意味に流用しないでください。自分へのダメージに当てはめるのは、説明に
  「(自分へのダメージも2倍)」があるときだけ（`card_problems` が変わるワザの「自分にも」と照らす）。
- 「あわあわ」は自分自身の `CannotUseOwnAttack`（はたらく番は与えた番 + 2）、「ドわすれ」は相手に与える `CannotUseAttack`（与えた番 + 1。選ぶのはワザを使った
  プレイヤー、決定 `select_opponent_attack`、選べるものは相手の対戦ポケモンのいちばん上のカードのワザの位置）です。使えないワザは `checks.attack_request` が
  `ATTACK_LOCKED` で拒否します（「しっぽをふる」と同じ場所）。ワザは位置で表し、名前では探さないでください。消える契機は v0.4b と同じです（進化で消える）。
- ウォーターパンチは、ついている「水」エネルギーの数（`state.energy_types`。カードの枚数ではない）だけコインを投げます。基本エネルギーでないカードが
  ついていれば `RuntimeError`（特殊エネルギーを加えるときに数え方を確かめる）。ぜんりょくとっしんは、同じ 4 枚のコイン（`Coin`）の「おもて」の数で相手へ、
  「うら」の数（`TailsOfCoin`）で自分へのダメージです（別々に投げない）。
- 書き出しは形式 10 のまま（持続する効果の種類 `next_turn_attack_damage_multiplier`・`cannot_use_own_attack`・`cannot_use_attack`、決定の種類
  `damage_step_order`・`select_opponent_attack` の値を加えた）。新しい未解決はありません（停止コード 40 件・未解決の裁定 41 件）。
- 検証用デッキ `S35` と組（`PAIRINGS_V0_35`）は tools/existing_effect_games.py の `--batch v0.35` です。公開の固定のデッキ・既存の変種には入れていません。
  勝敗で採用を判断しないでください。

## p.309 の手順 4 のコイン・「にげる」ことができない効果・自分を山札にもどす効果と 11 枚（v0.36）

- 依頼の 11 枚（サンド PMCG1-051・サンドパン PMCG3-036・ブーバー（化石の秘密）PMCG3-008・タッツー PMCG3-014・カスミのタッツー PMCG5-025・キョウのポッポ PMCG6-062・
  わるいサンダース PMCG4-029・カスミのパウワウ PMCG5-023・マチスのオニドリル PMCG5-064・キョウのドガース PMCG6-015・エリカのマダツボミ PMCG5-005）を、kyuura データの
  採用で加えました（対応ポケモン 153 → 164。写しの組 `pool_v0_36`。ワザの登録 286）。規定と根拠（AC1〜AC14・RL1〜RL5・RD1〜RD12）・カードごとの結果・互換性・検証は
  docs/sand-attack-retreat-lock-v0.36.md。ガイドブックは読んでいません。テストの定数は tests/helpers.py の `V0_36_POKEMON`（`FOSSIL_MAGMAR`・`KOGAS_KOFFING` など。
  第1弾のブーバー PMCG1-020・第1弾／第4弾のドガース・第2弾のマダツボミ、同じ名前の別の版と取りちがえない）。v0.36 の効果の型は `ATTACK_TYPES_SINCE_V0_17` に加え、
  `v013_checks.VERIFIED` には入れていません。
- p.309 のワザを使う手順 4「ワザを失敗させたりワザの内容を変えてしまう効果」（すなかけ・えんまく・サンダーフラッシュ・しんきろう）は、相手に与える持続する効果
  `state.AttackCoinCheck`（`on_opponent`。はたらく番は与えた番 + 1。`single_use` はサンドの「すなかけ」の「効果は1回できえる」だけ）です。効果を受けたポケモンが
  ワザを使うとき、`resolution.flow._attack_check_failed` が宣言（手順 3）のあと・こんらんのコイン（手順 5）とワザの要素の前に、`procedures.attack_coin_check`
  （持ち主が `flip_coins` の `source="attack_check"`、ログ `attack_check`、「1回できえる」なら理由 `used` で消す）でコインを投げます。「うら」ならログ
  `attack_failed`（`reason` `attack_check`）→ ワザの要素を処理せずに `_finish_attack`（ワザは使ったことになり、番は終わる。p.323 の 12）。ワザの要素のコイン
  （`Coin`・`FailOnTails`）や「とうめい」のコインと混ぜないでください。宣言できないワザ（ねむり・マヒ・しっぽをふる・使えないワザ・エネルギー不足・未対応）は
  この前に拒否するので、コインを投げません。決定のあとの再開（`resume`）で投げ直さないでください。
- 手順 4 の効果の文面は 5 通りあり、`effects.ATTACK_COIN_CHECK_TEXTS`（文面 → `single_use`）で照らします。型 `DamageThenAttackCoinCheck(single_use)` の `check` が
  登録の文面と値の組を確かめます。ワザの名前が同じ（すなかけ・えんまく）ことで同じ設定にしないでください（キョウのポッポの「すなかけ」は 1 回では消えない）。
- こんらん状態のポケモンが手順 4 の効果を受けてワザを使う場合（AC6。手順 4 で失敗したあとに手順 5 をするかを p.309 が書かない）は、コインの前に問い
  `attack_check_confusion`（`UNRESOLVED_ATTACK_CHECK_CONFUSION`）で止めます。「おもて」の先のワザの内容で止める問いに当たるなら、先読みが宣言の前に止めます
  （受け付けるかが手順 4 のコインで変わらない）。2 つ以上の手順 4 の効果は、v0.44 まで対応カードで起こらず `RuntimeError` でしたが、v0.45 の期限のない「スミをかける」で起こるので、AC13
  （`UNRESOLVED_MULTIPLE_ATTACK_CHECKS`。コインの前・AC6 より先）で止めます（下の v0.45 の節）。手順 4 の効果を加えるとき（ベイビィ
  ポケモンのルールなど）は、この順番と問いを見直してください。
- 「にげる」ことができない効果（アイスバーン・わしづかみ）は相手に与える持続する効果 `state.CannotRetreat` で、`engine._retreat` が、ねむり・マヒの確認のあと・
  エネルギーのトラッシュとこんらんのコインの前に `IllegalActionError("RETREAT_PREVENTED")` で拒否します（`persistent.cannot_retreat`）。ポケモンいれかえ・
  テレポート（入れ替え）は制限しません（p.325）。ワザも制限しません。
- 自分を山札にもどす効果（キョウのドガースの「くもがくれガス」）は要素 `programs.ReturnSelfToDeck`（「ダメージを与えた後」の効果。`after_damage`）と
  `zones.return_in_play_to_deck`（重なったカード・エネルギー・ついているトレーナーを持ち主の山札の下に。ログ `return_in_play_to_deck`）→ 持続する効果を理由
  `return_in_play_to_deck` で消す → 山札を切る（先読みでは切らない）です。きぜつとして扱わないでください（サイド・ログ `knock_out`・きぜつしたときの特殊能力は
  ない）。バトル場が空くので、ワザのあとの既存の勝ち負けの判定とバトル場に出す決定（`promote_active`）に進みます（控えがいなければ負け）。同じワザでポケモンが
  HP 以上になる場合（RD9）は問い `return_in_play_to_deck_with_knockout`（`UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT`）で宣言の前に止め、ダメージを与えなかった
  場合（RD8）は既存の Z23 です。v0.24 のポケモン交換おじさんの決定の種類・ログ `return_to_deck`（手札 → 山札。`zones.return_hand_to_deck`）とは別の処理・名前です。
  名前・値を混ぜないでください（tests/test_pokemon_trader_v0_24.py が engine.py・resolution/ に `RETURN_TO_DECK` がないことを確かめる）。
- 不変条件（`engine._given_by_attack_problems`）は、効果を与えたワザ（ログ `persistent_effect_added` の `effect`）の登録の `attack_check_terms()`・`retreat_lock_terms()`
  と効果を照らします。手順 4・「にげる」の効果を与えるワザを加えたら、これらを書いてください。テストで効果を置くときは、実際にワザを使って作ってください。
- まねるワザで「ドわすれ」をまねると、効果 `CannotUseAttack` が効果を与えたポケモンのカードのワザの位置で記録されるため表せないので、エンジンの未対応
  （`OpponentAttackLock.copy_problem`。`UNSUPPORTED_COPIED_ATTACK`）にしました（v0.35 は不変条件の違反になっていた）。まねた手順 4・「にげる」・くもがくれガスの
  効果は対応で、発生源はまねたポケモンです。
- 書き出しは形式 10 のまま（持続する効果の種類 `attack_coin_check`（`single_use`）・`cannot_retreat`。形式 8 から書ける）。公開の API は変えていません。ログの監査
  （tests/log_audit.py）は、手順 4 のコインの並び（`attack` → `coin_flip` → `attack_check` →「1回できえる」の消去 →「うら」の `attack_failed`）・「にげる」ことが
  できないポケモンの「にげる」・山札にもどしたカードの組み立て直しとそのあとの `shuffle` を確かめます。
- エンジンが止める `UNRESOLVED_…` は 42 件、未解決の裁定は 43 件です（AC6・RD9 を加えた。どちらも kyuura の未解決の一覧にない `not_in_kyuura`）。
- 検証用デッキ `W36`・`K36` と組（`PAIRINGS_V0_36`）は tools/existing_effect_games.py の `--batch v0.36` です（前の版の組の結果は変わらない）。「にげる」ことが
  できない効果を受けたはたらく番に 1 度だけ「にげる」を宣言する手順（`_v036_retreat_probe`）を重ね、拒否 `RETREAT_PREVENTED` は場から確かめます
  （tests/v017_games.py の `play_game` も同じ）。RD9 で止まったワザは `V031_STOPS` で場から確かめます。公開の固定のデッキ・既存の変種には入れていません。
  勝敗で採用を判断しないでください。

## 既存の効果の再利用・文面の違いの受け付け・新しい要素の組み合わせと 15 枚（v0.37）

- 依頼の 15 枚（サイホーン PMCG2-030・化石の秘密のベトベター PMCG3-003・ロケット団のイーブイ PMCG4-049・タケシのサンド PMCG5-043・ナツメのスリープ PMCG6-045・
  ライチュウ PMCG1-038・ダグトリオ PMCG1-056・ニョロゾ PMCG1-028・ニョロボン PMCG1-033・化石の秘密のアーボ PMCG3-001・タケシのイワーク PMCG5-048・ニャース PMCG2-036・
  キョウのモンジャラ PMCG6-009・カスミのコイキング PMCG5-028・ペルシアン PMCG2-039）を加えました（対応ポケモン 164 → 179。写しの組 `pool_v0_37`。ワザの登録 314）。
  カードごとの結果・文面の違いの扱いと根拠・共通の処理・互換性・検証は docs/fifteen-reused-effects-v0.37.md。ガイドブックは読んでいません。テストの定数は
  tests/helpers.py の `V0_37_POKEMON`（15 枚）・`V0_37_ADOPTED`（採用の 14 枚）。同じ名前の別のカード（`ROCKET_EEVEE` と `EEVEE`、`FOSSIL_EKANS` と `ROCKET_EKANS`、
  `MEOWTH` と `GIOVANNIS_MEOWTH`、`KOGAS_TANGELA` と `TANGELA`、`MISTYS_MAGIKARP` と `MAGIKARP` など）と取りちがえないでください。v0.37 の効果の型は
  `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません。
- 化石の秘密のベトベターは v0.8 の過去の原典照合の記録（`card_verification.json`。p.47）で登録し、`card_sources.json` には pcg-search.com の照合だけを書きます
  （`basis: guidebook_record`）。照合の記録（履歴）を書き換えないでください。採用の記録を作らないでください（登録したカードは記録をちょうど 1 つ持つ）。
  v0.36 まで参照カードだったので、「登録のないワザを持つカードはデッキに入らない」性質は `NO_FOSSIL_GRIMER_EFFECTS` で確かめます。
- 文面の違い: 型の `check` が受け付ける説明の一覧（`SELF_BARRIER_ON_HEADS_TEXTS`・`LOCK_OPPONENT_ATTACK_TEXTS`・`cannot_attack_on_heads_texts`・
  `reduce_damage_next_turn_texts`・`extra_energy_damage_texts`・`DamageThenReduceDamageToSelf` の 4 通り・`DamageAndOwnBenchDamage` の `weakness_resistance_stated`）に、
  意味が同じと記録で確かめた書き方だけを加えました。写し・採用した印刷の文面を書き換えたり、文面の確かめを一律に外したりしないでください。一覧にない書き方の
  カードを加えるときは、意味が同じかを既存の記録で確かめてから一覧に加え、受け付けない書き方のテストも加えます（tests/test_fifteen_reused_effects_v0_37.py の
  `TextVariantTest`）。v0.36 まで形だけを確かめていた `CannotAttackOnHeads`・`ReduceDamageNextTurn`・`ExtraEnergyDamageMixed` も、v0.37 から書き方を確かめます。
- ダメージのないワザ・ダメージのあとの自分の効果は、ダメージのある型を 0 ダメージに広げず、既存の要素の組み合わせの型で表します: `PoisonOnHeadsWithoutDamage`
  （どくえき）・`ParalyzeOnHeadsWithoutDamage`（うなりごえ）・`DamageThenDrawOnHeads`（ねこにこばん。ダメージ → コイン → 引く）・`DrawOnHeads`（つるでさがす）・
  `SelfBarrierOnHeads`（しんだふり。`AttackBarrier`。ダメージだけを受けない `PreventDamage` とは別）・`DamageThenReduceDamageToSelf`（かみつく。なきつくと同じ
  `ReducedDamageToSource`）。同じ説明の文面でも、ダメージの目安の有無で型を分けてください。引くのは自分の効果なので、相手が「ワザをうけない」状態でも、
  このワザのダメージで HP 以上になっても、コインを投げて引きます（v0.34 の `void_coin_question`。山札が足りなければ引けるだけ。p.312）。
- JS1: 説明に「弱点・抵抗力」に関係なくのない自分の控えへのダメージ（ダグトリオの「じしん」。`DamageAndOwnBenchDamage(10, weakness_resistance_stated=False)`）に
  弱点・抵抗力を計算するかは、2000.02.14 版の記録で決まりません（kyuura の rule_history.json の `bench_weakness` は第2版の時期の会報と第4版の冊子の記録だけ。
  当時の別の版の規定を混ぜない）。`programs.BenchDamage` の `weakness_resistance` が None のときだけ、控えのポケモンごとに 2 つの読み方の最終ダメージを
  `kernel.weakness_resistance_matters` で比べ、違えば問い `bench_damage_weakness_resistance`（`UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE`）で宣言の前に止めます。
  読み方で結果が変わらなければ止めません。カード別のコードにしないでください（問いはワザの型で決める）。ミニじしん（v0.33。`weakness_resistance=False`）は
  変えていません。説明に弱点・抵抗力のない控えへのダメージのワザを加えるときは、同じ問い（JS1）に当たるかを確かめてください（問いの理由の文はじしんを例に書いている）。
- ニョロボンの「みずでっぽう」は v0.31 の `ExtraEnergyDamageMixed`（HC4 のコードのまま。新しいコードにしない）、ニョロゾの「ドわすれ」をまねるのは v0.36 からの
  エンジンの未対応（`UNSUPPORTED_COPIED_ATTACK`）のままです。
- エンジンが止める `UNRESOLVED_…` は 43 件、未解決の裁定は 44 件です（JS1 を加えた。kyuura の未解決の一覧にない `not_in_kyuura`）。書き出しの形式は 10 のまま、
  公開の API・ログのイベントの種類・決定の種類・持続する効果の型は変えていません。
- 検証用デッキ `F37`・`W37`・`L37`・`G37` と組（`PAIRINGS_V0_37`）は tools/existing_effect_games.py の `--batch v0.37` です（前の版の組の結果は変わらない）。
  F37 のポケモンは闘に弱点・抵抗力を持たないので、対戦では JS1 は起こりません（境界は単体テスト）。JS1・HC4 で止まったワザは `V031_STOPS` で場から確かめます。
  公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 控えへのダメージ・入れ替え・同じコインの複数の効果・軽減・山札にもどる効果の 15 枚（v0.38）

- 依頼の 15 枚（フリーザー PMCG3-023・サワムラー PMCG3-039・エリカのモンジャラ PMCG5-006・タケシのロコン PMCG5-017・タケシのゴルバット PMCG5-008・アーボック PMCG3-004・
  サイドン PMCG2-033・カツラのポニータ PMCG6-028・カツラのギャロップ PMCG6-030・キョウのピジョン PMCG6-070・キョウのビードル PMCG6-001・サカキのニドリーナ PMCG6-012・
  ナツメのポリゴン PMCG6-066・ケーシィ PMCG4-031・キョウのポッポ PMCG6-067）を、kyuura データの採用で加えました（対応ポケモン 179 → 194。写しの組 `pool_v0_38`。
  ワザの登録 343）。カードごとの結果・共通の処理・規定と根拠（BC1〜BC6・SW1〜SW3・MC1〜MC4・BA1・LP1〜LP3・GK1）・互換性・検証は docs/bench-switch-combined-v0.38.md。
  ガイドブックは読んでいません。テストの定数は tests/helpers.py の `V0_38_POKEMON`。同じ名前の別のカード（`BROCKS_VULPIX_50`（PMCG5-017）と `BROCKS_VULPIX`
  （PMCG5-018）、`KOGAS_PIDGEY_40`（PMCG6-067）と `KOGAS_PIDGEY`（PMCG6-062）、`ROCKET_ABRA`（PMCG4-031）と `ABRA`（PMCG1-043）など）と取りちがえないでください。
  v0.38 の効果の型は `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません。
- 相手の控えを選ぶダメージは v0.33 の要素 `ChosenBenchDamage`（`local_coin=None`）です。説明に「相手に控えポケモンがいないとき、このワザは使えない」がある
  ワザ（のびるキック。`ChooseOpponentBenchDamage(requires_bench=True)`・要素の `required`）だけ、ワザを使うための条件（`usage_problem`。`NO_OPPONENT_BENCH`）に
  します。同じ記述のないワザ（のびるつる・ほのおのわ）は、控えがいなくても使え、何もしません（p.309）。似た別のカードの条件を推測で当てはめないでください。
  相手のワザとして使うときの条件は `ChosenBenchDamage.copy_problem`（ピクシー・ピッピは選べない、カスミのコダックは HC9）。
- コインが決める要素のどれにも処理の対象がなければ、コインを投げません（`Element.has_target`。今は `BenchDamage` だけが上書きし、控えがいなければ対象がない。
  ふぶきで両方に控えがいない）。`void_coin_question` には対象のある要素だけを渡します（ふみあらすを控えのいない「ダメージを受けない」「ワザをうけない」相手に
  使うと v0.4b の問い）。投げなかったコインの面はどちらでもありません（`AttackRun.coin_is`）。処理の対象がなくなりうる要素を加えたら `has_target` を上書きして
  ください。同じコインで複数の効果を決めるワザ（ふぶき・ふみあらす・こうそくひこう・きけんなはり）は、ワザ全体のコイン（`Coin`）か `Status` の `otherwise` で
  表し、要素ごとに投げ直さないでください（`SelfPersistent.gate` を加えた）。
- 入れ替えの要素に要素のコイン（`ForceSwitch.local_coin`（いかくこうげき。相手が選ぶ）・`SelfSwitch.local_coin`（けりにげ。自分が選ぶ））を加えました。入れ替えの
  対象がない（相手の対戦ポケモンが HP 以上・控えがいない・ワザを使ったポケモンが HP 以上）なら投げません。相手への入れ替えを決めるコインは、「とうめい」で
  受けないと決まった相手に T19b、「ワザをうけない」相手に HC3 で止めます。自分の入れ替えは自分への効果なので投げます。
- GK1（新規。`UNRESOLVED_DAMAGE_TRIGGER_TIMING`）: 「ダメージを受けたとき」の効果（はんげき・わるいねぞう・ほのおのかべ・こうらがえし）がはたらいていて、ワザの
  要素がダメージ以外の効果のあとにもう一度ダメージの要素を持つ（サイドンの「げきとつ」の入れ替え → 自分にも 20）と、その効果を処理する時点（ダメージの処理を
  すべてのせたあと、かつダメージ以外の効果の前。CR-COUNTERATTACK-TIMING・CR-FIRE-WALL-TIMING・CR-SHELL-ATTACK-TIMING）がないので、`programs.run_elements` が
  問い `damage_trigger_timing` で宣言の前に止めます（先読みが見つける）。効果がはたらかなければ止めません。「ダメージ → 効果 → ダメージ」の並びのワザを加える
  ときは、同じ問いに当たります（カード別のコードにしない）。
- 自分を山札にもどす要素（v0.36 の `ReturnSelfToDeck`）に、もどす前にカウンターをとりのぞいてついているカードをトラッシュする `discard_attached`（ケーシィの
  「いなくなる」。`zones.discard_attached_cards`・ログ `discard_attached_cards`）と、もどしたあと切らない `shuffle=False`（キョウのポッポの「でんれい」）を加えました。
  いなくなるはついているカードをトラッシュ、でんれい・くもがくれガスは山札です（この違いを保ってください）。説明にない途中のシャッフルを加えないでください。
  場から山札にもどる処理はきぜつではありません（サイド・ログ `knock_out`・きぜつしたときの特殊能力はない）。重なったカードはポケモン自身（v0.36 の RD2）。
- でんれいは、もどす → 控えから対戦ポケモンを出す（要素 `PromoteFromBench`。ワザを使ったプレイヤーが選ぶ。`zones.promote_from_bench`（きぜつのあとのバトル場に
  出す決定と共通。ワザの効果のときだけログに `effect`））→ 山札から「キョウのポッポ」以外のポケモンを見せて手札に加える（要素 `RevealPokemonFromDeck`。決定
  `SEARCH_DECK`（再開先 `"attack"`）。`effects.deck_pokemon_candidates`（名前の完全一致で除く）。v0.24 の `zones.reveal_deck_to_hand`（ワザの効果のときだけログに
  `effect`）。選べるものがなければログ `reveal_from_deck_none`）→ 切る（1 回）。控えがいなければ出せず、さがして切ってから、ワザのあとの勝ち負けの判定で負けます。
- ワザを使ったポケモンが場をはなれたあとのワザの途中の決定は、実装が `AttackEffect.leaves_play_before_decisions = True` のときだけ許します（不変条件
  `engine._returned_attacker`。今の番のワザの宣言がちょうど 1 回、そのあとに同じポケモンを同じワザの効果で山札にもどしたログ `return_in_play_to_deck` がちょうど
  1 回。その間だけ番のプレイヤーのバトル場が空でよい）。続きの情報のポケモンは枠の番号（`frame.source_pid`）で持ちます。この例外を広げないでください。
- 書き出しの形式は 10 のまま、公開の API・決定の種類・持続する効果の型は変えていません。新しいログのイベントは `discard_attached_cards`・`reveal_from_deck_none`。
  エンジンが止める `UNRESOLVED_…` は 44 件、未解決の裁定は 45 件です（GK1 を加えた。kyuura の未解決の一覧にない `not_in_kyuura`）。
- 検証用デッキ `F38`・`G38`・`C38` と組（`PAIRINGS_V0_38`。`C38` 対 `P31` を含む）は tools/existing_effect_games.py の `--batch v0.38` です（前の版の組の結果は
  変わらない）。v0.38 のカードの使えるワザをすべて 1 度は使い、使っていないワザのエネルギーが足りないときは番を終える手順（`v038_wait_…`）を重ねています。
  のびるキックの `NO_OPPONENT_BENCH` と GK1 で止まったワザは `V031_STOPS` で場から確かめます。公開の固定のデッキ・既存の変種には入れていません。
  勝敗で採用を判断しないでください。

## じばく・控えへのダメージ・場のポケモンの数でダメージが決まるワザの 15 枚（v0.39）

- 依頼の 15 枚（コイル PMCG1-036・レアコイル PMCG1-039・マタドガス PMCG3-006・レアコイル PMCG3-025・ピカチュウ PMCG2-024・ライチュウ PMCG3-024・マルマイン PMCG2-025・
  キョウのドガース PMCG6-008・カスミのニョロボン PMCG6-039・コイル PMCG4-026・プクリン PMCG2-045・ニドクイン PMCG2-013・キョウのマタドガス PMCG6-016・ポッポ PMCG1-059・
  エリカのパラス PMCG5-004）を、kyuura データの採用で加えました（対応ポケモン 194 → 209。写しの組 `pool_v0_39`。ワザの登録 368）。カードごとの結果・共通の処理・
  規定と根拠（SD1〜SD7・SB1・SP1〜SP2・GS1〜GS2・TB1〜TB3・WR1・FG1・CT1〜CT3・EX1・TG1・DS1〜DS2・WG1）・互換性・検証は docs/selfdestruct-spread-count-v0.39.md。
  ガイドブックは読んでいません。テストの定数は tests/helpers.py の `V0_39_POKEMON`。同じ名前の別のカード（`MAGNEMITE`（PMCG1-036）と `ROCKET_MAGNEMITE`
  （PMCG4-026）、`MAGNETON`（PMCG1-039）と `FOSSIL_MAGNETON`（PMCG3-025）、`JUNGLE_PIKACHU`（PMCG2-024）と `PIKACHU`（PMCG1-035）、`FOSSIL_RAICHU`（PMCG3-024）と
  `RAICHU`（PMCG1-038）、`KOGAS_KOFFING_40`（PMCG6-008）と `KOGAS_KOFFING`（PMCG6-015））と取りちがえないでください。v0.39 の効果の型は `ATTACK_TYPES_SINCE_V0_17` に
  加え、`v013_checks.VERIFIED` には入れていません。
- じばくは `effects.SelfDestruct`（相手 → 自分 → 相手の控え → 自分の控え。きぜつの処理・番の終わりはワザのあと）です。自分へのダメージは、ワザによる自分への
  ダメージ（v0.2f・v0.3d。プラスパワー・ディフェンダー・弱点・抵抗力を計算する）で、残りの HP に関係なく自分をきぜつさせる処理にしないでください（ディフェンダーで
  残ることがある）。第1弾の文面（控えへのダメージに「弱点・抵抗力」の記述がない。`weakness_resistance_stated=False`）と第3弾の文面（「弱点・抵抗力」に関係なく）を
  区別してください（型の `check` が文面で照らす）。
- 説明に「弱点・抵抗力」に関係なくのない控えへのダメージ（第1弾のじばく・スパーク・ビリビリ）は、v0.37 の JS1 と同じ問い（`bench_damage_weakness_resistance`）・
  同じコードです。新しい問いを加えないでください。`BenchDamage` は受ける控えのどれかで読み方の結果が変われば宣言の前に、相手の控えを 1 匹選ぶ
  `ChosenBenchDamage(weakness_resistance=None)`（スパーク）は選ぶ控えごとに（選べるが選ぶと止める `unresolved_choices`。どの控えでも変われば宣言の前）止めます。
- ソニックブーム（`DamageIgnoringWeaknessResistance`）が計算しないのは、相手の弱点・抵抗力（p.321 の 3・4 段階）だけです。プラスパワー・ディフェンダー・
  「ダメージを受けない」状態・「とうめい」などはそのまま処理します。ワザ全体を特殊能力・防御効果を無視するワザにしないでください。
- 相手の控えから最大 N 匹を選ぶ要素 `programs.ChosenBenchDamages`（ギガスパーク）は、決定 `SELECT_POKEMON`（ワザを使ったプレイヤー。`min_choices` 0・
  `max_choices` は min(N, 控えの数)。重複は `DUPLICATE_CHOICE`）です。0 匹の答えは GS1（`UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE`。決定は待ったまま）で止めます。
  H4・ER9 の答えで決めないでください。先読みは 1 匹以上のすべての答え（選ぶポケモン・数・順番）を試します（`all_answers(decision, minimum=1)`。選ぶ控えで結果が
  違えば同じものとみなさない）。相手に控えがいなければ決定を出しません。
- 受ける控えをタイプでしぼるのは `BenchDamage.same_type_as_opponent_active`（ビリビリ。「同じ色」はタイプ。p.311 の「色（タイプ）」の記録）・`exclude_type`
  （ウォーターリング）です。タイプは、その要素を処理する時点の場のポケモンのいちばん上のカードのタイプです。
- 場のポケモンの数でダメージが決まるワザは、値 `programs.PrintedPlusPokemonCount`（p.321 の 1 段階の基本となるダメージ = 目安 + 数 × `per`）と
  `programs.counted_pokemon` で数えます（進化して重なったカードは 1 匹。名前はいちばん上のカードの名前の完全一致。名前の一部・収録の弾で判定しない）。数える
  範囲（`own_bench`・`own_in_play`）と名前の組は `effects.POKEMON_COUNT_TEXTS` にあるものだけです（文面の書き方と照らす）。実際の処理と先読み（`damage_profile`）は
  同じ関数で数えます。最終ダメージに直接足さないでください。
- とつぜんばくはつ（`CoinBonusDamageAndSelfDamage`）・きけんなほうし（`CoinPoisonAndBenchDamage`）は、1 枚のコイン（`Coin`）で複数の要素を決めます（要素ごとに
  投げ直さない。片方の要素だけが無効・対象なしでも、残る要素があれば投げる。v0.34 の `void_coin_question`・v0.38 の `has_target`）。どくどくガス
  （`DamageThenSpecialPoisonOnHeads`）は v0.34 のどくどくと同じ特殊などく（`Poison(20)`。通常のどくを 2 回にしない）で、TP3・HC3 はそのまま当てはまります。
- ログの監査（tests/log_audit.py）の特殊などくの量の確かめは、`DamageAndSpecialPoison`・`DamageThenSpecialPoisonOnHeads` の登録の量で照らします。特殊などくを
  与える型を加えたら、監査にも加えてください。
- 書き出しの形式は 10 のまま、公開の API・ログのイベントの種類・決定の種類・持続する効果の型は変えていません。エンジンが止める `UNRESOLVED_…` は 45 件、
  未解決の裁定は 46 件です（GS1 を加えた。kyuura の未解決の一覧にない `not_in_kyuura`）。
- 検証用デッキ `L39`・`G39`・`C39`・`N39` と組（`PAIRINGS_V0_39`）は tools/existing_effect_games.py の `--batch v0.39` です（前の版の組の結果は変わらない）。
  スパーク・ギガスパークの控えの選択は `_v039_decision`（JS1 の選択を避け、ギガスパークは 1・2・3 匹を順に選ぶ。0 匹は選ばない）、v0.39 のカードも v0.38 の
  エネルギーをためる手順を使います。JS1・TP3 で止まったワザは `V031_STOPS` で場から確かめます（JS1 の確かめ `_bench_reading_matters` は第1弾のじばく・ビリビリ・
  スパークも見る）。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 場の数・条件付きの効果・入れ替え・カードの移動の 15 枚（v0.40）

- 依頼の 15 枚（キョウのズバット PMCG6-005・キョウのゴルバット PMCG6-014・わるいマタドガス PMCG4-011・わるいスリーパー PMCG4-037・サカキのニドラン♂ PMCG6-004・
  サカキのニドリーノ PMCG6-013・サカキのニドキング PMCG6-021・サカキのニドクイン PMCG6-020・わるいゴーリキー PMCG4-042・わるいカイリキー PMCG4-044・
  エリカのウツドン PMCG5-011・カスミのシードラ PMCG5-034・タケシのマンキー PMCG5-045・マンキー PMCG4-039・オコリザル PMCG2-031）を、kyuura データの採用で加えました
  （対応ポケモン 209 → 224。写しの組 `pool_v0_40`。ワザの登録 396）。カードごとの結果・共通の処理・規定と根拠（GR1〜GR5・NE1〜NE5・BM1〜BM3・RC1・HD1・IM1〜IM6・
  LR1〜LR2・DO1〜DO4・FL1〜FL3・ST1・SH1〜SH2・RM1）・SG1・互換性・検証は docs/count-condition-switch-return-v0.40.md。ガイドブックは読んでいません。テストの定数は
  tests/helpers.py の `V0_40_POKEMON`。名前の似た別のカード（`GIOVANNIS_NIDORAN_M` と `NIDORAN_M`、`DARK_WEEZING` と `FOSSIL_WEEZING`・`KOGAS_WEEZING`、`BROCKS_MANKEY` と
  `MANKEY`、`DARK_MACHAMP` と `MACHAMP` など）と取りちがえないでください。v0.40 の効果の型は `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません。
- 山札から好きなだけベンチに出す要素 `programs.BenchFromDeckAny`（むれでおそう）は、v0.32 の決定 `BENCH_FROM_DECK`（0〜min(ベンチの空き, 選べるもの)）と
  `zones.bench_from_deck` を使い、出したら 1 回だけ切ります。0 枚は「のぞむなら」の選ばないことで、出さず・切らない（ログ `bench_from_deck_declined`。実装上の判断）。
  v0.39 の GS1（「最大3匹」の 0 匹）と同じ問いとして扱わないでください。ダメージは出したあとの場の数（値 `PokemonCountTimes`。v0.39 の `counted_pokemon`）。
- ワザの効果で山札を切るのは `programs.shuffle_in_attack` だけです（ログ `shuffle` に `effect`。`zones.shuffle_deck` の `effect` は渡したときだけ書く）。先読み
  （`res.dry_run`）では切らず、切る要素のあとに山札の並びを使う要素（`Element.reads_deck_order`）があれば止めます。山札の並びを使う要素を加えたら `reads_deck_order` を
  書いてください。
- みんなでばくはつ（`NamedPokemonExplosion`）は、お互いの場の名前の合うポケモンの数 × 20 のあと、名前の合う相手の対戦ポケモン・自分・お互いの控えにそれぞれ 20
  （`Damage.names`・`BenchDamage.names`）。通常のじばくに置きかえないでください。相手の対戦ポケモンへのダメージの要素が 2 つあるのは対応カードでこのワザだけで、
  どれも p.321 で別々に計算します（NE3）。控えへのダメージは JS1。
- ベンチをあやつる（`OpponentFlipsTailsDamage`）のコインは相手プレイヤーが投げます（値の `flipped_by_opponent`・`AttackRun.flip` の `player`）。
- ワザを使うための条件（いかりのいちげきの自分のカウンター 2 つ以上 `NOT_ENOUGH_DAMAGE_COUNTERS`、ひきずりだす・さそってとかす・つまみだすの相手の控え
  `NO_OPPONENT_BENCH`）は実装の `usage_problem` で、状態を変える前・こんらんのコインの前に拒否します。相手のワザとして使うときは要素の `copy_problem`。
- すごむ（`AttackLockWhileSourceActive`）は相手に与える持続する効果 `state.CannotAttackWhileSourceActive`（はたらく番は次の相手の番）です。最大 HP 50 以下は効果を
  与えるときに確かめ、「このカードがバトル場にいる限り」はワザの宣言のときに `persistent.cannot_attack_while_source_active` で確かめます（「しっぽをふる」と同じ場所・
  同じコード `ATTACK_PREVENTED`）。効果を与えたポケモンがはなれても効果そのものは消しません。同じ番にもどる場合は SG1（新規。
  `UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED`）で、突風（v0.21）がそのポケモンを選ぶ答えを止めます（選べるが選ぶと止める。それしか選べなければ使う前に止める）。
  相手のポケモンをバトル場に出す手段を加えるときは、SG1 に当たるかを確かめてください。不変条件は登録の `conditional_lock_terms()` と照らします。
- ひきずりだす・さそってとかす（`SwitchOpponentThenDamage`）は、ワザを使ったプレイヤーが選ぶ入れ替え（`ForceSwitch(chooser="attacker", required=True, carry=True)`）の
  あと、新しい対戦ポケモンにダメージ。入れ替えは入れ替える前の対戦ポケモンへの効果（v0.31 のかどわかす）で、「とうめい」の結果を決定をまたいで運ぶ（T27 を見つける）。
  ダメージのあとの入れ替え（なぐりとばす・ふきとばし）と取りちがえないでください。
- つまみだす（`ReturnOpponentActiveToDeck`・要素 `ReturnOpponentToDeck`）は、v0.36 の `zones.return_in_play_to_deck` を持ち主（相手）で呼び、持続する効果を消し、
  持ち主の山札を切ります。きぜつではありません。空いたバトル場は、ワザのあとに相手が自分の控えから選んで出します。同じワザで HP 以上になる場合は RD9。
- ラブラリアットの「「100」になる」は p.321 の 1 段階（値 `AmountIfOwnBenchNamed`）で、v0.27 の「つるぎのまい」（2 段階の持続する効果）ではありません。
- 書き出しの形式は 10 のまま、公開の API・決定の種類は変えていません。新しいログのイベントは `bench_from_deck_declined`。エンジンが止める `UNRESOLVED_…` は 46 件、
  未解決の裁定は 47 件です（SG1 を加えた。kyuura の未解決の一覧にない `not_in_kyuura`）。
- 検証用デッキ `G40`・`N40`・`F40`・`P40` と組（`PAIRINGS_V0_40`）は tools/existing_effect_games.py の `--batch v0.40` です（前の版の組の結果は変わらない）。
  むれでおそうの出す数は番の番号で 選べるだけ・0 枚・1 枚、ひきずりだす・さそってとかすの控えは 最後・最初 を順に選ぶ（`_v040_decision`）。使うための条件で拒否
  されたワザ（`NOT_ENOUGH_DAMAGE_COUNTERS`・`ATTACK_PREVENTED`・`NO_OPPONENT_BENCH`）は `V031_STOPS` で場から確かめます。公開の固定のデッキ・既存の変種には入れて
  いません。勝敗で採用を判断しないでください。

## 回復・ダメージカウンターの移動・特殊状態の変化の 15 枚（v0.41）

- 依頼の 15 枚（クサイハナ PMCG2-009・ウツボット PMCG2-016・シードラ PMCG3-020・わるいペルシアン PMCG4-048・カツラのファイヤー PMCG6-035・ヤドン PMCG4-032・
  エリカのナゾノクサ PMCG5-002・エリカのナゾノクサ PMCG5-003・エリカのクサイハナ PMCG5-009・ナツメのコダック PMCG6-036・ナツメのゴルダック PMCG6-038・
  ナツメのモルフォン PMCG6-022・ナツメのヤドラン PMCG6-048・エリカのプリン PMCG5-058・R団のミュウツー PMCG6-055）を、kyuura データの採用で加えました（対応ポケモン
  224 → 239。写しの組 `pool_v0_41`。ワザの登録 425）。カードごとの結果・共通の処理・規定と根拠（HL1〜HL7・MV1〜MV4・XC1〜XC2・SS1〜SS7・LU1〜LU2・PH1・SN1〜SN2・
  FH1・GP1・SE1）・CX1・互換性・検証は docs/heal-counter-status-v0.41.md。ガイドブックは読んでいません。テストの定数は tests/helpers.py の `V0_41_POKEMON`。
  同じ名前の 2 枚のエリカのナゾノクサ（`ERIKAS_ODDISH`（PMCG5-002。HP 50）・`ERIKAS_ODDISH_40`（PMCG5-003。HP 40））、ロケット団のヤドン（`ROCKET_SLOWPOKE`）と
  化石の秘密のヤドン（`SLOWPOKE`）、名前の似た別のカード（`GLOOM` と `ERIKAS_GLOOM`、`SEADRA` と `MISTYS_SEADRA`、`DARK_PERSIAN` と `PERSIAN`、`BLAINES_MOLTRES` と
  `MOLTRES`・`ROCKETS_MOLTRES`、`SABRINAS_PSYDUCK` と `PSYDUCK`・`MISTYS_PSYDUCK`、`ERIKAS_JIGGLYPUFF` と `JIGGLYPUFF`、`ROCKETS_MEWTWO` と `MEWTWO`）と取りちがえない
  でください。v0.41 の効果の型は `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません。
- 回復（ダメージカウンターをとりのぞく）は要素 `programs.HealCounters` 1 つで表します（`scope` は `HEAL_SELF`・`HEAL_OWN_ALL`・`HEAL_BOTH_ALL`、数は `counters` か
  ワザ全体のコインの「おもて」の数 `heads_of`、`gate`・`local_coin`）。のっている数まで・0 個のポケモンは効果を受けない（GR-2000-P320-RECOVERY）。とりのぞくポケモン
  ごとに `reaches`（要素の種類 `heal`）で「ワザをうけない」状態・「とうめい」を評価し、ログはポケモンごとの `attack_heal`。説明に「ダメージを与えたら」のない回復に、
  やどりぎのタネ（`Drain`）の条件を付けないでください（説明に書かれた条件だけ）。回復の対象がないこと（0 個・自分が HP 以上）は、そのあとの別の内容（いねむりの
  ねむり）を止めません（GR-2000-P309-ATTACK-PROCEDURE）。メガドレインなどの `Drain`・ログ `drain_heal` と混ぜないでください。
- ダメージカウンターを相手にのせる・取り替える（ダメージシフト `ShiftCountersToOpponent`・チェンジダメージ `SwapCounters`）は、ダメージの処理（`kernel.deal_damage`）を
  通さないダメージカウンターの移動です（GR-2000-P320-COUNTER-MOVE。弱点・抵抗力・プラスパワー・ディフェンダー・「ダメージを受けない」状態を計算せず、「ダメージを
  受けたとき」の効果ははたらかない）。通常のダメージのログ（`damage`）に置きかえないでください（ログ `place_damage_counters`・`swap_damage_counters`）。チェンジダメージは
  取り替える前の双方の数で処理し、片方を変えてから変えたあとの数をもう片方に渡さないでください。HP 以上になったポケモンは `programs._counters_changed`（`track_ko`・
  `ko_prevention_able` を偽。こんじょうは使えない）でワザのあとのきぜつの判定に入ります。相手がその効果を受けない（「ワザをうけない」状態・「とうめい」）とき
  自分の側を処理するかは決まらない（CX1。`UNRESOLVED_COUNTER_TRANSFER_PROTECTED`）ので宣言の前に止めます。移す・取り替えるカウンターがないなら止めません。
- ミラクルかふんは要素 `ChosenStatus` と決定 `decisions.SELECT_SPECIAL_CONDITION`（選ぶのはワザを使ったプレイヤー（実装上の判断）。選べるものは
  `effects.CHOSEN_CONDITIONS` の番号。`carry`。マヒの再付与は `unresolved_choices`）。ひなたぼっこは要素 `AttachFromDeck` と決定 `decisions.ATTACH_FROM_DECK`
  （0〜1 枚）・`zones.attach_from_deck`（山札から直接つける。手札からつける通常の操作 `energy_attachments_this_turn`・特殊能力の回数には数えない。どの場合も
  `shuffle_in_attack` で切る。つけたら `effects.after_energy_attached`）。手札からつける処理（`zones.attach_energy_from_hand`）を流用しないでください。
- ダメージの要素のあとのワザ全体のコイン（`Coin`。ねこにこばん・げんかくおんぱ）は、あとにダメージの要素がなければ、そのコインの前に「ダメージを受けたとき」の効果を
  処理します（`programs.run_elements`。CR-COUNTERATTACK-TIMING。v0.40 までは内部エラー）。あとにダメージの要素があるコインは今までどおり `RuntimeError` です。
  コインの面に「おもて」の数の下限 `AtLeast(count)`、`Status.has_target`（対象がこのワザで HP 以上なら処理の対象がない）を加えました。
- 既存の要素の項目: `SelfAttackLock.local_coin` の `None`（コインなしで与える。きあいずつき）・`OpponentRetreatLock.local_coin`（ようかいえき）。きあいずつきを相手の
  ワザとして使うのは v0.35 からのエンジンの未対応（`UNSUPPORTED_COPIED_ATTACK`）です。ひのとりは v0.36 の `ReturnSelfToDeck`（「うら」）で、RD9・Z23 を既存の問いの
  まま使います。
- 型の `check` が受け付ける書き方に、さそうかおりの「選び」（`SWITCH_OPPONENT_ACTIVE_TEXTS`。v0.40 までは形だけ）・シードラのこうそくいどう（`SELF_BARRIER_ON_HEADS_TEXTS`）・
  みずでっぽう（`extra_energy_damage_texts`）を加えました。
- 書き出しの形式は 10 のまま、公開の API・状態の型・持続する効果の型は変えていません。新しい決定の種類は `select_special_condition`・`attach_from_deck`、新しいログの
  イベントは `place_damage_counters`・`swap_damage_counters`・`attach_energy_from_deck`・`attach_energy_from_deck_none`。エンジンが止める `UNRESOLVED_…` は 47 件、
  未解決の裁定は 48 件です（CX1 を加えた。kyuura の未解決の一覧にない `not_in_kyuura`）。
- ログの監査（tests/log_audit.py）は、`attack_heal` をポケモンごとに 1 回・とりのぞいてよいポケモンを登録の実装で確かめ、`place_damage_counters`（とりのぞいた数と
  同じ）・`swap_damage_counters`（取り替える前の双方の数）・`attach_energy_from_deck`（山札の登録のタイプの基本エネルギーカード。すぐあとに切る）を組み立て直します。
  ダメージカウンターを動かすワザを加えたら、監査にも加えてください。
- 検証用デッキ `G41`・`P41`・`C41`・`R41` と組（`PAIRINGS_V0_41`。`G41` 対 `P31`・`R41` 対 `F37` を含む）は tools/existing_effect_games.py の `--batch v0.41` です
  （前の版の組の結果は変わらない）。ミラクルかふん・ひなたぼっこの選び方は `_v041_decision`。CX1・RD9・Z23（「ダメージを与えた後」の効果のあるワザすべて）・
  ゆうわくの `NO_OPPONENT_BENCH` は `V031_STOPS` で場から確かめます。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 特殊能力の決定・再開・使用後の処理と 15 枚（v0.42）

- 依頼の 15 枚（ナツメのルージュラ PMCG6-052・ラフレシア PMCG2-014・ヤドラン PMCG3-028・ゲンガー PMCG3-031・エリカのラフレシア PMCG5-014・ナツメのケーシィ PMCG6-043・
  ナツメのユンゲラー PMCG6-047・カイリュー PMCG3-043・エリカのウツボット PMCG5-015・わるいユンゲラー PMCG4-034・わるいフーディン PMCG4-035・メノクラゲ PMCG3-011・
  ドククラゲ PMCG3-017・エリカのピッピ PMCG5-060・エリカのピクシー PMCG5-065）を、kyuura データの採用で、どのワザも、どの特殊能力も登録して加えました（対応ポケモン
  239 → 254。写しの組 `pool_v0_42`。ワザの登録 446・特殊能力の登録 20）。カードごとの結果・共通の処理・規定と根拠・PW1・PW2・互換性・検証は
  docs/power-decisions-v0.42.md。ガイドブックは読んでいません。テストの定数は tests/helpers.py の `V0_42_POKEMON`。同じ名前・似た名前の別のカード（`SABRINAS_JYNX` と
  `JYNX`、`SLOWBRO`（PMCG3-028）と `SABRINAS_SLOWBRO`、`ERIKAS_VILEPLUME` と `VILEPLUME`、`SABRINAS_ABRA` と `ABRA`・`ROCKET_ABRA`、`SABRINAS_KADABRA` と `DARK_KADABRA`・
  `KADABRA`、`ERIKAS_VICTREEBEL` と `VICTREEBEL`、`ERIKAS_CLEFAIRY` と `CLEFAIRY`、`ERIKAS_CLEFABLE` と `CLEFABLE`）と取りちがえないでください。進化元は名前の完全一致で
  決め、収録の弾で制限しません（ヤドランは 2 枚のヤドンから、わるいユンゲラーは 2 枚のケーシィから進化でき、ナツメのヤドン・ナツメのケーシィからは進化できない）。
  ワザだけを登録して、特殊能力を持つカードを対応と数えないでください（特殊能力の登録がなければ分類が未対応にする）。v0.42 のワザの型は `ATTACK_TYPES_SINCE_V0_17` に
  加え、`v013_checks.VERIFIED` には入れていません。
- 宣言して使う特殊能力の処理の途中の決定は、実装の `resolve` が `decisions.push_power_decision`（再開先 `"power"`。`context` の `"use"` は (プレイヤー, 場のポケモンの番号,
  カード id, 特殊能力の位置)）で出し、`engine._answer_decision` → `engine._resume_power` → `PowerEffect.resume` で続けます（段階は既存の `Phase.DECISION`。新しい段階・
  コマンド・保留中のリストを加えない）。決定を出す特殊能力は `PowerEffect.decision_problems` で決定の形を宣言します（不変条件 `engine._power_decision_problems`）。
  `resume` は宣言・回数の記録・コインを繰り返しません。形式 1 の書き出しは再開先 `"power"` の決定を `ValueError` にします。
- 「自分の番ごとに1回」の特殊能力（`PowerEffect.once_per_turn`）は、宣言（ログ `pokemon_power`）のときに `GameState.power_uses_this_turn` に記録します（コインの「うら」・
  決定の途中でも使ったことになる。ログから数えない）。回数の確認は実装の `check_usable` の `effects.require_power_not_used`（`POWER_ALREADY_USED`）。v0.31 のしぜんになおるの
  記録の時点も宣言のときに移しました（状態の結果は同じ）。
- 特殊能力はワザではありません。使っても番は終わらず、こんらんのコインを投げず、ワザのログ・ワザの窓はありません。特殊能力を `AttackEffect`・ワザの要素の並びで
  処理しないでください。
- 特殊能力の処理（宣言・決定への答え）が終わったら、`engine._after_power_step` が `resolution.after_power` を呼びます。HP 以上のポケモンがいれば、ワザのあとと同じ
  きぜつの処理（ログ `knock_out` の `timing` は `"power"`）→ サイド → 勝ち負け → ふしちょう → バトル場に出す、きぜつがなくバトル場が空いていれば勝ち負け → バトル場に
  出す、で、続きは `continue_turn`（`procedures.CONTINUE_TURN`。終わったら番のプレイヤーの `Phase.MAIN` にもどる。ワザのあとの続き・ポケモンチェックの `next_turn` と
  混ぜない）。こんじょう・みちづれは候補にしません。きぜつの処理をするのは、実装が `PowerEffect.may_knock_out = True`（説明に「きぜつ」しない範囲の条件がない。今は
  ゲンガーの［のろい］だけ）の特殊能力のあとだけです。ほかの特殊能力のあとに HP 以上のポケモンがいれば、きぜつにせず不変条件で止めます（ダメージスワップ・
  へんなこうどうの確認の漏れを黙ってきぜつにしない。v0.7 の二重の確かめ）。「きぜつ」させうる特殊能力を加えるときは、説明の条件を確かめて `may_knock_out` を書いて
  ください。不変条件 `engine._power_aftermath_problems` は、続き `continue_turn` の決定の前の今の番の最後の宣言が特殊能力の宣言であることを確かめます。
- ［のろい］（`MoveOpponentDamageCounter`）は相手の場のポケモンのあいだでダメージカウンターを 1 つ動かします。文面にない「きぜつさせてはいけない」条件を付けないで
  ください。カウンターの移動はダメージではありません（GR-2000-P320-COUNTER-MOVE）。ワザによるダメージに置きかえず、弱点・抵抗力・ディフェンダー・「とうめい」・
  「ワザをうけない」状態・はんげきを当てはめないでください（ワザを防ぐ効果は特殊能力の効果には当てはまらない。CX1 は当たらない）。ログ `move_damage_counter` の
  `owner` はカウンターの持ち主。［へんなこうどう］（`MoveDamageCounterToSelf`）は移動先がこのカードで、きぜつさせる移動は `WOULD_KNOCK_OUT`（1 回の使用で 1 個は
  ダメージスワップの S3 と同じ実装上の仮定）。
- ［おくびょう］（`ReturnSelfToHand`）とワザの「ようせいのきせき」（要素 `ReturnOwnPokemonToHand`）は、場のポケモンを手札にもどす `zones.return_in_play_to_hand`
  （ログ `return_in_play_to_hand`・持続する効果を消す理由 `return_in_play_to_hand`）です。きぜつではありません（サイド・ログ `knock_out`・きぜつしたときの特殊能力はない）。
  v0.36 の山札にもどす処理（`return_in_play_to_deck`。行き先が山札・切る）と行き先・切るかが違うので、流用しないでください。おくびょうはダメージカウンターをすべて
  とりのぞき、ついているカードをトラッシュしてから手札にもどします（ようせいのきせきは、重なったカード・ついているカードとともに手札にもどす）。空いたバトル場は
  特殊能力なら使用後の処理、ワザならワザのあとに控えから出し、控えがいなければ負け。
- ［ぼうぎょかふん］（エリカのラフレシア。`ConfuseDamageSourceOnHeads`）は自動的にはたらく反応で、効果の定義 `catalog.DEFENSIVE_POLLEN`（はんげき・わるいねぞうと
  同じ DEFER の窓。処理 `kernel.power_confusion_to_damage_source`。決定を出さない）です。新しい項目 `EffectDefinition.active_only` で、バトル場で受けたワザのダメージに
  だけはたらきます。説明のとおり特殊状態・このカードのきぜつでは止まらず（`disabled_by` は空）、かがくへんかガスでは止まります。ダメージを与えたポケモンがすでに
  HP 以上ならコインを投げません（ログ `power_confusion_skipped`）。
- ワザによる進化（エリカのピッピの「つきのちから」。要素 `EvolveFromDeck`）は、山札の進化カード（`effects.deck_evolution_candidates`）を通常の進化と同じ手順
  （`evolution.place_evolution_card`。ログ `evolve` の `source_zone` は `deck`・`effect`）で重ね、山札を切ります。進化の制限（おたがいの最初の番・その番に出した
  ポケモン・その番に進化したポケモン）は通常の進化と共通の `evolution.evolution_block` で確かめます。ワザによる進化だからといって制限を免除しないでください。
- ワザの要素: よいおこない（`ChosenOpponentHealThenDraw`。決定 `remove_counters`）・エネループ（`ReturnOwnEnergyToHand`。`DiscardOwnEnergy` の部分型で行き先が手札。
  決定 `return_energy`・ログ `return_energy_to_hand`。こんらん状態で使うときは HC1）・ライフダウン（`CountersToRemainingHp`。ダメージではない。ログ
  `place_damage_counters`）・テレポートブラスト（`SelfSwitch` の `optional`・`after_damage`。0 匹なら `switch_declined`）。マインドショック（v0.39 の
  `DamageIgnoringWeaknessResistance`）が計算しないのは相手の弱点・抵抗力だけです。防御効果・特殊能力を無視する範囲に広げないでください。
- 同じ問いは既存の記録・コードを使います: ヒーリングの自分の場にカウンターがない（HC8）・よいおこないの 0 個とようせいのきせきの 0 匹（HC5）・エネループのこんらん
  （HC1）・テレポートブラストのダメージを与えなかった場合（Z23）・かおりのわなのすごむの効果を与えたポケモン（SG1）・ライフダウンの「ワザをうけない」「とうめい」の
  相手（HC3・T19b）・つきのちから（`UNRESOLVED_EVOLUTION_HP`）。新しい未解決は PW1（かおりのわなを相手に控えがいないとき。
  `UNRESOLVED_POWER_SWITCH_WITHOUT_OPPONENT_BENCH`。突風の GW5 とは別の問い）・PW2（ぶっしつこうかんを手札がないとき。`UNRESOLVED_POWER_DISCARD_WITHOUT_HAND`。
  パソコン通信の使うための条件で補わない）で、どちらも宣言の前に止めます。エンジンが止める `UNRESOLVED_…` は 49 件、未解決の裁定は 50 件です（どちらも kyuura の
  未解決の一覧にない `not_in_kyuura`）。
- カイリューの［かけつける］の処理に使う文面は、kyuura の data/curation/card_differences.json の PMCG3-043（確度: 確実）の最新の説明です（研究の対応表の
  `difference_text`。LD- はない）。ほかは kyuura の印刷の文面（`adopted_printed_text`）。
- 書き出しの形式は 10 のまま、公開の API・状態の型・持続する効果の型は変えていません。新しい決定の種類は `remove_counters`・`return_energy`、新しいログのイベントは
  `power_confusion`・`power_confusion_skipped`・`return_energy_to_hand`・`return_in_play_to_hand`・`evolve_from_deck_none`・`switch_declined`（既存のイベントに加えた項目は
  docs の 10 章）。ログの監査（tests/log_audit.py）は、特殊能力の宣言のすぐあとの処理・特殊能力のコインのすぐあとの結果・のろいのあとの `timing: power` のきぜつ・
  手札にもどしたポケモン・山札から重ねた進化を確かめ、組み立て直しに含めます。特殊能力の処理を加えたら、監査にも加えてください。
- 検証用デッキ `G42`・`P42`・`D42`・`W42` と組（`PAIRINGS_V0_42`。`D42` 対 `P31` を含む）は tools/existing_effect_games.py の `--batch v0.42` です（前の版の組の結果は
  変わらない）。特殊能力を使う手順は `_v042_power`、決定の答え方は `_v042_decision`。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 宣言して使う特殊能力と場に出たときの特殊能力の入口と 9 枚（v0.43）

- 依頼の 9 枚（わるいクサイハナ PMCG4-006・スリープ PMCG4-033・ヒトカゲ PMCG4-012・エリカのマダツボミ PMCG5-010・マチスのレアコイル PMCG5-040・わるいハクリュー PMCG4-052・
  わるいゴルバット PMCG4-009・わるいヤドラン PMCG4-036・わるいカイリュー PMCG4-053）を、kyuura データの採用で、どのワザも、どの特殊能力も登録して加えました（対応ポケモン
  254 → 263。写しの組 `pool_v0_43`。ワザの登録 455・特殊能力の登録 29）。カードごとの結果・経路ともどり方・規定と根拠・PW3・PW4・互換性・検証は
  docs/declared-entry-powers-v0.43.md。ガイドブックは読んでいません。テストの定数は tests/helpers.py の `V0_43_POKEMON`。同じ名前の別のカード（`ROCKET_DROWZEE` と
  `DROWZEE`、`ROCKET_CHARMANDER` と `CHARMANDER`、`ERIKAS_BELLSPROUT_40`（PMCG5-010）と `ERIKAS_BELLSPROUT`（PMCG5-005））・名前の似た別のカード（`DARK_GLOOM` と `GLOOM`・
  `ERIKAS_GLOOM`、`LT_SURGES_MAGNETON` と `MAGNETON`、`DARK_DRAGONAIR` と `DRAGONAIR`、`DARK_GOLBAT` と `GOLBAT`、`DARK_SLOWBRO` と `SLOWBRO`、`DARK_DRAGONITE` と
  `DRAGONITE`）と取りちがえないでください。ワザだけを登録して、特殊能力を持つカードを対応と数えないでください。v0.43 のワザの型 `ChooseOpponentPokemonDamage` は
  `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません。
- 宣言して使う 6 つ（`CoinConditionOnEitherActive`・`TakeEnergyToSelf`・`TakeEnergiesToSelf`・`ChargeBenchEnergyToSelf`・`SearchEvolutionCardToHand`）は、v0.42 の特殊能力の
  共通の処理（宣言・`power_uses_this_turn` の宣言のときの記録・`push_power_decision`・再開先 `"power"`・`resolution.after_power`）をそのまま使います。特殊能力はワザでは
  ないので、ワザを使うときのこんらんのコイン・ワザを防ぐ効果（「ワザをうけない」・「とうめい」・「ダメージを受けない」）を当てはめないでください。日本語の説明に
  ない回数の制限（エナジーチャージ）・英語版の文面の条件を加えないでください。ようぶんきゅうしゅうは 1 回の使用で最大 2 枚です（1 枚ずつ何度も使う形にしない）。
  エネルギーのつけかえは同じ uid のカードを動かすだけで、手札からつける通常の操作の回数（`energy_attachments_this_turn`）を変えません（ログ `move_energy`）。
  エナジーバーンで「炎」になっているカードの判定は HC10（`UNRESOLVED_ENERGY_BURN_TRANSFER`）の既存のコードです。
- 場に出たときに 1 度だけ使える特殊能力は `effects.EntryPower`（`from_hand_only`: 「手札から出した時」「手札から場に出した時」なら真、「場に出た時」なら偽。
  `accept_problem`: 使うを選ぶと止める場合）です。使うかは持ち主が決めます（宣言する特殊能力。自動的にはたらく形にしない）。場に出す処理のあとに
  `effects.offer_entry_power` が決定 `entry_power`（持ち主・(そのポケモンの番号,)・0〜1 個・再開先 `"power"`・`context` の `"entry"`（経路）と `"return_to"`
  （もとの処理））を出し、`engine._resume_power` が、使わないならログ `entry_power_declined`、使うならログ `pokemon_power`（`entry`）→ 実装の `resolve` で続けます。
  `UsePokemonPower` では使えません（`POWER_NOT_USABLE_NOW`。機会が過ぎたあとに `MAIN` から使えない）。はたらいているかがくへんかガスに消された特殊能力には機会を
  出しません。新しい段階・コマンド・保留中のリストを加えないでください。
- 使う機会を出す場所は、手札からの進化（`engine._evolve_pokemon`）とポケモン育て屋さん（`EvolveBasicToStage2.resume`。`return_to` は ("trainer", プレイヤー, カード,
  カード id) で、特殊能力の処理のあとに `engine._finish_trainer` でトラッシュにもどる）の 2 か所だけです。ワザで山札から重ねる進化（つきのちから）では、「手札から」の
  特殊能力に機会はなく、「場に出た時」の特殊能力は PW4（`UNRESOLVED_ENTRY_POWER_DURING_ATTACK`。選べるが選ぶと止める（`entry_power_choices`）・どれもそうなら宣言の前）
  です。たねポケモンの場に出たときの特殊能力・ほかの場に出す経路を加えるときは、その経路に `offer_entry_power` を加え、不変条件
  （`engine._entry_power_decision_problems`。直前のログが進化であることなど）を見直してください。決定の不変条件の「答えられる選択」の数は、`entry_power` だけ 0 を
  許します（使わないがいつも答えになる。ほかの決定に広げない）。
- 特殊能力によるダメージ（こっそりかみつく。`DamageOpponentPokemonOnEntry`。ログ `power_damage`）は、ワザのダメージの計算（p.321）をせず、弱点・抵抗力・プラスパワー・
  ディフェンダー・「ダメージを受けない」状態・「とうめい」・「ダメージを受けたとき」の効果・こんじょうを当てはめません（CR-COUNTERATTACK-IS-POWER-DAMAGE と同じ読み方）。
  `kernel.deal_damage` を通さないでください。きぜつさせうるかは実装の `may_knock_out`（こっそりかみつく・のろい）で決め、きぜつ・サイド・勝ち負け・バトル場に出す
  処理は v0.42 の `after_power` です。カード id で分けないでください。
- PW3（`UNRESOLVED_POWER_ZERO_CARDS`）は、選ぶカードが 0 枚になる特殊能力（ようぶんきゅうしゅう・しんかのひかり・てしたをよぶ）で共通の 1 つの問いです。カードごとに
  別の問い・コードにしないでください。使っても使わなくても状態が同じ場合（つりあげるの 0 枚・エナジーチャージの 0 枚）は止めません（実装上の判断）。v0.23 の ER9・
  v0.9 の H4 の答えで PW3 を決めないでください。エンジンが止める `UNRESOLVED_…` は 51 件、未解決の裁定は 52 件です（PW3・PW4 は kyuura の未解決の一覧にない
  `not_in_kyuura`）。
- v0.42 のつきのちから（`programs.EvolveFromDeck`）が、重ねられるカードがどれも選ぶと止める場合に選べる答えのない決定を出していた潜在的な不具合を直しました（問い
  `evolution_hp_every_card`。既存のコード `UNRESOLVED_EVOLUTION_HP`。今のカードでは起こらない）。
- 書き出しの形式は 10 のまま、公開の API・状態の型は変えていません。新しい決定の種類は `entry_power`・`move_energy`・`recover_pokemon`、新しいログのイベントは
  `entry_power_declined`・`power_damage`・`recover_pokemon`・`recover_pokemon_none`（既存のイベントに加えた項目は docs の 10 章）。ログの監査（tests/log_audit.py）は、
  手札から進化させたあとの使う機会の答え（答えのない機会・2 度の答え）・宣言の `entry`・つけかえの行き先とタイプ・コインのあとの特殊状態の側・特殊能力のダメージと
  そのあとのきぜつ・つりあげるで手札に加えたカード・特殊能力で切る処理とベンチに出した枚数を確かめ、組み立て直しに含めます。
- 検証用デッキ `G43`・`R43`・`L43` と組（`PAIRINGS_V0_43`。`G43` 対 `P31` を含む）は tools/existing_effect_games.py の `--batch v0.43` です（前の版の組の結果は
  変わらない）。特殊能力を使う手順は `_v043_power`、決定の答え方は `_v043_decision`（使う機会は 4 回に 1 回使わない。v0.43 の決定は元の手順より先に答える）。
  公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 検索・進化・1 度だけ使えるワザのポケモン 14 枚とトレーナーのサカキ（v0.44）

- 依頼の 15 枚（ディグダ PMCG4-038・ニャース PMCG4-047・エリカのフシギダネ PMCG5-007・カスミのヒトデマン PMCG5-027・コイキング PMCG4-020・キョウのコクーン PMCG6-011・
  キョウのスピアー PMCG6-018・カモネギ PMCG1-063・サカキのコイキング PMCG6-037・サカキのギャラドス PMCG6-040・ナツメのバリヤード PMCG6-046・カツラのマンキー PMCG6-056・
  _____のラッキー PMCG6-075・サカキのペルシアン PMCG6-071・サカキ PMCG6-095）を、kyuura データの採用で、どのワザも、どの特殊能力も、トレーナーも登録して加えました（対応
  ポケモン 263 → 277。写しの組 `pool_v0_44`。ワザの登録 479・特殊能力の登録 31・トレーナーの登録 12）。カードごとの結果・共通の処理・経路・記録の方法・規定と根拠・
  FC1・TR1・GV1・互換性・検証は docs/search-evolution-once-attacks-v0.44.md。ガイドブックは読んでいません。テストの定数は tests/helpers.py の `V0_44_POKEMON`（14 枚）・
  `V0_44_CARDS`（15 枚。サカキが最後）。同じ名前の別のカード（`ROCKET_DIGLETT` と `DIGLETT`、`ROCKET_MEOWTH` と `MEOWTH`、`ROCKET_MAGIKARP` と `MAGIKARP`）・名前の似た別の
  カード（`MISTYS_STARYU` と `STARYU`、`BLANK_CHANSEY` と `CHANSEY`、`GIOVANNIS_PERSIAN` と `PERSIAN`・`DARK_PERSIAN`、`GIOVANNIS_GYARADOS` と `GYARADOS`、
  `GIOVANNIS_MAGIKARP` と `MAGIKARP`・`MISTYS_MAGIKARP`）と取りちがえないでください。v0.44 のワザの型は `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には
  入れていません。スターブーメランの処理に使う文面は kyuura の最新の説明 LD-PMCG5-027-ATK0（研究の対応表の `registered`）。
- 場に出てから 1 度だけ使えるワザ（`AttackEffect.once_after_entering_play`。ネギでたたく・りゅうのきおく・ひっさつばり）は、場のポケモンの記録
  `PokemonInPlay.attacks_used_once`（(カードの uid, ワザの位置)）で表します。記録するのはワザの宣言のとき（`resolution.flow._attack_body`。ログ `once_attack_recorded`。
  手順 4 のコイン・こんらんのコインより前）で、コインの「うら」・こんらんの「うら」でも使ったことになります（p.323 の 12・v0.3d の A12）。2 回目は `checks.attack_request` が
  エネルギーの確認の前に `ATTACK_ALREADY_USED`。ログを読み直して数えないでください。場をはなれたら（場のポケモンの番号ごと）記録もなくなります。ベンチにもどる・進化する
  だけでは残ります。相手のワザとして使うのはエンジンの未対応（`unsupported_choices`・`UNSUPPORTED_COPIED_ATTACK`。記録をどのポケモンに付けるかが表せない）。
- トレーナーのサカキ（`effects.EvolutionPermissionForOwnerPokemon("サカキ")`）は、選んだ自分の場の「サカキの」ポケモン（名前が「サカキの」で始まる）の
  `PokemonInPlay.evolution_permission_turn` に今の番を記録します（ログ `evolution_permission`）。許可は手札から重ねる進化（通常の操作・ポケモン育て屋さん）の
  「その番に場に出した」「その番に進化した」の 2 つの制限だけを外します（`evolution.turn_restriction`。カードの文面がルールに優先する。GR-2000-P307-CARD-OVER-RULE）。
  おたがいの最初の番の制限・名前・段階は変えません（英語版の「or if this is your first turn」を持ち込まない）。許可は番の終わりに消えます（`procedures.expire_at_turn_end`）。
  サカキのポケモンがいなければ TR1（`UNRESOLVED_TRAINER_WITHOUT_TARGET`。使う前）。不変条件 `engine._evolution_permission_problems` と、進化の不変条件の許可のある場合の
  例外（`_evolution_permitted`。許可のログが進化より前にあるときだけ）を広げないでください。
- 山札から重ねる効果（ワザのたきのぼりしんか・つきのちから、特殊能力の［うか］）で、サカキの許可だけで制限が外れる組は GV1（問い `evolution_permission_from_deck`）。
  v0.44 ではコードのない問い（起こらないとした）でしたが、つきのちからは自分の場のほかのポケモンも進化させるので起こり、内部エラーになっていました。v0.45 で停止コード
  `UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK` を付けました（下の v0.45 の節。裁定は未解決のまま）。`evolution.PERMISSION_FROM_DECK_CODE` は
  `evolution_block(from_deck=True)` が返す印で、停止コードではありません（呼ぶ側が止める）。
- 特殊能力で山札のカードを重ねる進化（［うか］。`CoinEvolveSelfFromDeck`）は `evolution.place_evolution_card(..., power=)`（ログ `evolve` の `power`・`source_zone`）で、
  通常の進化の制限（`evolution_block(from_deck=True)`）を当てはめます。特殊能力なので番は終わりません（自分の番ごとに 1 回。「うら」でも使ったことになる）。
- ［ボスをよぶ］（`SearchNamedTrainerOnEntry`）は v0.43 の `EntryPower`（「手札から場に出した時」）。山札のサカキ（名前の完全一致）を手札に加え（`search_deck`。見せる
  指示がないので非公開）、切ります。山札にサカキがなければ PW3。
- 新しい要素: `RevealTrainerFromDeck`（おつかい）・`EvolveAttackerFromDeck`（たきのぼりしんか）・`ReturnAttackerToHand`（スターブーメラン。きぜつではない。同じワザで
  HP 以上になるポケモンがいれば RD9）・`ReturnHandToDeck`・`ReturnHandThenRevealEnergy`（ラッキーたまご・てじな。決定 `hand_to_deck`。`zones.return_hand_cards_to_deck`。
  ログ `hand_to_deck` の `cards` は非公開）・`OpponentDiscardToDeckTop`（わるいいたずら。決定 `discard_to_deck_top`。`zones.put_discard_on_deck_top`。切らない）。v0.24 の
  `zones.return_hand_to_deck`（ポケモン交換おじさん。見せる。ログ `return_to_deck`）と混ぜないでください。v0.43 の `ChosenOpponentPokemonDamage` に要素のコイン
  `local_coin` を加えた（こばんなげ）。
- FC1（新規。`UNRESOLVED_STATED_CARDS_SHORT`。問い `stated_cards_short`）: 説明が決まった枚数を選ばせるとき選べるカードが足りない場合。ラッキーたまご（手札が 2 枚より少ない。
  ワザの宣言の前）・てじな（もどす枚数より山札の基本エネルギーカードが少なく 1 枚以上。段階 1 の答え）で共通の 1 つの問いです。カードごとの問いにしないでください。
  てじなの 0 枚は v0.39 の GS1、山札の基本エネルギーカードが 0 枚なら対象がない（見せずに切る。p.309）。
- 先読みは、手札・山札・トラッシュのカードを選ぶ決定で、同じカード id の答えを 1 つにまとめます（`programs.card_id_answers`）。場のポケモンを選ぶ決定には使わないでください。
- 書き出しの形式 11 = 形式 10 + 場のポケモンの `attacks_used_once`・`evolution_permission_turn`（形式 1〜10 は、どちらかがあると `ValueError`）。監査の `LATEST_FORMAT` は 11。
  新しい決定の種類は `hand_to_deck`・`discard_to_deck_top`、新しいログのイベントは `once_attack_recorded`・`evolution_permission`・`hand_to_deck`・`put_discard_on_deck_top`・
  `reveal_from_deck_declined`・`evolve_from_deck_declined`。ログの監査（tests/log_audit.py）は、これらの組み立て直しと、許可と同じ番の 2 回の進化・1 度だけ使えるワザの記録・
  相手のワザとして使ったワザの効果のログ（`copy_attack` の `copied`。`_same_attack`）を確かめます。エンジンが止める `UNRESOLVED_…` は 53 件、未解決の裁定は 55 件（FC1・TR1 は
  `not_in_kyuura`、GV1 は `codeless_questions`。v0.45 で GV1 を停止コードにした）。
- 検証用デッキ `K44`・`V44`・`W44` と組（`PAIRINGS_V0_44`。`W44` 対 `P31` を含む）は tools/existing_effect_games.py の `--batch v0.44` です（前の版の組の結果は変わらない）。
  決定の答え方は `_v044_decision`（元の手順より先に答える）、［うか］は `_v044_power`、サカキと許可のある進化は `_v044_trainer`。FC1・RD9・`ATTACK_ALREADY_USED` は
  `V031_STOPS` で場から確かめます。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 条件つきのダメージ・エネルギーの移動とトラッシュ・受けたダメージを返す効果などのポケモン 15 枚と GV1 の停止コード（v0.45）

- 依頼の 15 枚（第1弾のゴースト PMCG1-047・カスミのタッツー PMCG5-024・カスミのジュゴン PMCG5-031・キョウのアーボ PMCG6-002・キョウのアーボック PMCG6-019・
  キョウのベトベター PMCG6-007・わるいカメックス PMCG4-024・わるいレアコイル PMCG4-030・カツラのリザードン PMCG6-032・R団のサンダー PMCG6-042・イワーク PMCG1-054・
  ラッタ PMCG1-062・R団のエビワラー PMCG5-054・タケシのイシツブテ PMCG5-047・サカキのニャース PMCG6-068）を、どのワザも登録して加えました（対応ポケモン 277 → 292。
  写しの組 `pool_v0_45`。写し 299 → 313 枚。ワザの登録 479 → 507）。カードごとの結果・GV1・v0.44 の文書の訂正・再利用した処理と新しい処理・規定と根拠・互換性・検証は
  docs/conditional-damage-energy-v0.45.md。ガイドブックは読んでいません。テストの定数は tests/helpers.py の `V0_45_POKEMON`（15 枚）・`V0_45_ADOPTED`（採用の 14 枚）。
  同じ名前の別のカード（`MISTYS_HORSEA_50`（PMCG5-024）と `MISTYS_HORSEA`（PMCG5-025）、`BROCKS_GEODUDE_40`（PMCG5-047）と `BROCKS_GEODUDE`（PMCG5-046）、
  `GIOVANNIS_MEOWTH_40`（PMCG6-068）と `GIOVANNIS_MEOWTH`（PMCG6-063）、`BASE_HAUNTER`（PMCG1-047）と `HAUNTER`（PMCG3-030））・名前の似た別のカード（`ROCKETS_ZAPDOS` と
  `ZAPDOS`、`ROCKETS_HITMONCHAN` と `HITMONCHAN`、`DARK_BLASTOISE` と `BLASTOISE` など）と取りちがえないでください。v0.45 のワザの型 18 は `ATTACK_TYPES_SINCE_V0_17` に
  加え、`v013_checks.VERIFIED` には入れていません。
- 第1弾のゴーストは v0.9 の過去の原典照合の記録（`card_verification.json`。p.160）で登録し、`card_sources.json` には pcg-search.com の照合だけを書きます
  （`basis: guidebook_record`。採用の記録を作らない。照合の記録（履歴）を書き換えない）。処理に使う文面はその記録の最新の説明（ゆめくいは「相手が「ねむり」状態で
  ないとき、このワザは失敗する。」。印刷の文面の「ねむり」のときだけダメージをあたえる、にしたがわない）。v0.44 までの参照カードとしての性質は
  `NO_BASE_HAUNTER_EFFECTS`・`no_base_haunter_pool` で確かめます。R団のエビワラーの「クロスカウンター」の処理に使う文面は kyuura の最新の説明 LD-PMCG5-054-ATK0、
  ほかは kyuura の印刷の文面です。
- GV1（v0.44 のコードのない問い `evolution_permission_from_deck`）は、つきのちから（自分の場のほかのポケモンも進化させる）で起こり、公開の `apply_command` が内部エラーに
  なっていました。停止コード `UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK` を付けました（`resolution/questions.py`。要素 `EvolveFromDeck`・`EvolveAttackerFromDeck` が問いを投げ、
  特殊能力の［うか］は `effects.PERMISSION_FROM_DECK_STOP_CODE`）。裁定は未解決のままです（許可のあるポケモンを重ねられることにも、重ねられないことにもしない）。
  止めるのは宣言の前（先読みが見つける。コインの前）で、状態・乱数・ログは変わりません。つきのちからの対象・進化の制限・許可の意味を狭めないでください（前の番から
  場にいるサカキのコイキングには、許可の有無に関係なく重ねられる。この番に場に出して許可のないポケモンは通常の進化の制限で選べるものに入らない。tests の `Gv1Test`）。
- v0.44 の文書の訂正: サカキのペルシアンは 1 進化なので、ポケモン育て屋さんでは場に出せません。［ボスをよぶ］を使う機会は、手札のサカキのペルシアンをサカキのニャースに
  重ねる通常の進化だけです。ポケモン育て屋さんで重ねたあとの場に出たときの特殊能力の例はわるいカイリュー（v0.43。［てしたをよぶ］）です（v0.44 の文書に「v0.45 の訂正」として
  書いた。エンジンの処理は変えていない）。
- 期限のない手順 4 の効果（スミをかけるの「それ以後」）は `AttackCoinCheck.lasting`（はたらく番とそれ以後の番。`active_on(turn)`）です。期限（`expired`）では消えず、
  バトル場をはなれる・進化・きぜつ・山札や手札にもどると消えます（`persistent.lasting`）。v0.36 の「次の相手の番」の効果の期限は変えていません。期限のない効果と
  もう 1 つの手順 4 の効果は同じポケモンに重なりうるので、そのポケモンがワザを使うとき、宣言のあと・コインの前（こんらんの AC6 より先）に AC13
  （`UNRESOLVED_MULTIPLE_ATTACK_CHECKS`。問い `multiple_attack_checks`。`flow._attack_check_failed`）で止めます。効果ごとにコインを投げる・1 枚で両方を決めるのどちらにも
  決めないでください。不変条件は、期限のない効果だけ同じ種類の重なりを許します（`engine._persistent_effect_problems`。広げない）。登録の `attack_check_terms()` は
  期限のない効果では (型, 「1回できえる」か, True) です。
- 8 段階の「決まった数より小さければ 0 にする」効果（かたくなる）は、自分自身の持続する効果 `state.ZeroDamageBelow`（はたらく番は次の相手の番）と、ダメージの変更効果の
  計算 `damage.ZERO_IF_BELOW`（その段階のダメージがしきい値より小さければ 0、以上ならそのまま）です。`effects.attack_damage_modifiers` が 8 段階に加え、ログ `damage` に
  `damage_zero_below` を残します。v0.4b の「ダメージを受けない」状態（計算の前に無効）・v0.31 の `DamageReduction`（へらす）と混ぜないでください。不変条件は登録の
  `threshold_terms()` と照らします（`engine._zero_damage_below_problems`）。
- 受けたダメージを返す効果に倍数とはたらくときのコインを加えました（クロスカウンター。`Retaliation` の `multiplier`・`on_heads`。種類 `retaliation_received_damage_scaled`。
  `Retaliation.terms()` を登録の `retaliation_terms()` と照らす）。コインは効果がはたらくとき（`kernel.attack_damage_to_damage_source`。v0.12・v0.13 と同じ時点）に効果を
  持つポケモンの持ち主が投げ、「うら」ならログ `retaliation_skipped` の理由 `coin_tails`。ダメージを与えたポケモンがすでに HP 以上なら投げません。返す量は受けた最終ダメージの
  倍数で、ワザによるダメージとして `deal_damage` を通します。そろってのきぜつは W24/S37 と同じ `UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`（新しいコードにしない）。ほのおのかべ・
  こうらがえしの値・ログ・書き出しは変えていません。相手のワザとして使うのはエンジンの未対応（`UNSUPPORTED_COPIED_ATTACK`）です。
- 抵抗力だけを計算しないダメージ（スパイラルショット）は要素 `Damage` の `resistance=False`（`calculate_attack_damage(..., resistance=False)`。ログ `ignore_resistance`）です。
  v0.39 のソニックブーム（弱点・抵抗力の両方）と混ぜないでください。
- 相手のエネルギーを相手の控えにつけかえる要素 `MoveOpponentEnergyToBench`（じりょくせん。決定 `move_opponent_energy`。ログ `move_opponent_energy`）は、はがすのが
  相手の対戦ポケモンへの効果（要素の種類 `ENERGY_MOVE_ELEMENT`。「ワザをうけない」「とうめい」を評価する）で、つける控えが「とうめい」で受けなければ持ち主のトラッシュ
  （CR-TRANSPARENCY-ENERGY-BOMB と同じ読み方。実装上の判断）。手札からつける通常の操作の回数には数えず、つけたら `effects.after_energy_attached` を呼びます。
- 多いエネルギーをトラッシュする要素は `DiscardOwnEnergy.excess_over_cost`（ファイヤーブレス。必要なエネルギーより多い炎の基本エネルギーカードをすべて。ワザの効果）と
  値 `PlusPerDiscarded`。条件の要素と値は `FailUnlessOpponentStatus`（ゆめくい。ワザの失敗。ログ `attack_failed` の `reason` `condition`）・`SelfStatusCheck`・`Status` の
  `if_result`・`after_switch`・値 `PrintedTimesIfDefenderType`・`IfSelfStatus`・`PerAttachedEnergyCards`・`HalfRemainingHp`。どくをためるの自分へのどくは、特殊などくの
  ポケモンを通常のどくにします（v0.3a の 14）。
- 山札の要素: `BenchFromDeck` の `owner`（「タケシの」たねポケモン。名前の始まりで決める）・`optional`（0〜1 匹）・`local_coin`（「うら」なら何もしない・切らない）、
  `OpponentDeckTopDiscardTrainerElseHand`（てつだうふり）とゾーンの関数 `zones.take_deck_top`（相手の山札の一番上を動かす。ログ `take_deck_top`。カードを引く処理
  `draw_cards` ではない。山札は切らない）。`AttachFromDiscard.exact`（ちょうど 1 枚。プラズマ）。
- 書き出しの形式は 11 のまま、公開の API は変えていません。持続する効果の種類 `zero_damage_below`・`retaliation_received_damage_scaled` と `attack_coin_check` の
  `lasting`（期限のない効果だけ）は形式 8 から書けます（既定の値の効果は v0.44 と同じ形）。新しい決定の種類は `move_opponent_energy`、新しいログのイベントは
  `move_opponent_energy`・`take_deck_top`（既存のイベントに加えた項目は docs の 8 章）。エンジンが止める `UNRESOLVED_…` は 55 件、未解決の裁定は 56 件です
  （GV1・AC13 は kyuura の未解決の一覧にない `not_in_kyuura`。GV1 は v0.44 から裁定に数えている）。
- ログの監査（tests/log_audit.py）は、`move_opponent_energy`・`take_deck_top` の組み立て直しと、クロスカウンターの直前の持ち主のコイン・倍数・受けたダメージ、期限のない
  手順 4 の効果（期限で消えない・ワザを使うたびのコイン）、かたくなるの 8 段階の記録、たすけをよぶの「タケシの」たねポケモンを確かめます。
- 検証用デッキ `G45`・`R45`・`F45`・`W45` と組（`PAIRINGS_V0_45`。`G45` 対 `P31` を含む）は tools/existing_effect_games.py の `--batch v0.45` です（前の版の組の結果は
  変わらない）。決定の答え方は `_v045_decision`。AC13・W24 で拒否されたワザは `V031_STOPS` で場から確かめます。公開の固定のデッキ・既存の変種には入れていません。
  勝敗で採用を判断しないでください。

## 常にはたらく特殊能力の共通の処理と 11 枚（v0.46）

- 依頼の 11 枚（常にはたらく特殊能力を持つバリヤード PMCG2-027［なぞのかべ］・エリカのミニリュウ PMCG5-063［ふしぎなバリアー］・エリカのフシギソウ PMCG6-010［くつろぐかおり］・
  わるいオコリザル PMCG4-041［きょうぼう］・ドードリオ PMCG2-040［にげるサポート］・わるいベトベトン PMCG4-007［ねんちゃくえき］・わるいラフレシア PMCG4-010［アレルギーかふん］・
  カビゴン PMCG2-047［めんえき］と、エリカのフシギバナ PMCG6-017・エリカのタマタマ PMCG5-012・エリカのナッシー PMCG5-013）を、kyuura データの採用で、どのワザも、どの特殊能力も
  登録して加えました（対応ポケモン 292 → 303。写しの組 `pool_v0_46`。写し 313 → 324 枚。ワザの登録 507 → 521・特殊能力の登録 31 → 39）。カードごとの結果・共通の処理・
  計算の操作・規定と根拠・CP1・CP2・互換性・検証は docs/continuous-powers-v0.46.md。ガイドブックは読んでいません。テストの定数は tests/helpers.py の `V0_46_POKEMON`。
  名前の似た別のカード（`MR_MIME` と `SABRINAS_MR_MIME`、`SNORLAX` と `ROCKETS_SNORLAX`、`DARK_MUK` と `MUK`、`DARK_VILEPLUME` と `VILEPLUME`・`ERIKAS_VILEPLUME` など）と
  取りちがえないでください。特殊能力を持つ 8 枚は、特殊能力の登録を除くと未対応です（ワザだけの登録で対応と数えない）。v0.46 のワザの型は `ATTACK_TYPES_SINCE_V0_17` に加え、
  `v013_checks.VERIFIED` には入れていません。
- 常にはたらく特殊能力は `effects.ContinuousPower`（`PowerEffect` の部分型。`declared = False`。`UsePokemonPower` は `POWER_NOT_DECLARABLE`）の部分型で加えます。
  はたらいているかは問い合わせのたびに `effects.continuous_powers(state, 型)` が、場のポケモン・いちばん上のカード・場所（`location`: `CONTINUOUS_IN_PLAY`・`CONTINUOUS_ACTIVE`・
  `CONTINUOUS_BENCH`）・特殊状態・かがくへんかガス（`continuous.suppressors_of`）から求めます。「はたらいている」の印・一覧を状態に持ったり、ログから決めたりしないで
  ください。効果の定義の対応表（`resolution/catalog.py`）にも入れません（窓の中の反応ではなく、処理がその時点の場から問い合わせる）。
- 特殊状態の条件は説明ごとに型で宣言します（`blocked_by_status`: ねむり・マヒ・こんらんで消える（既定）、`requires_confusion`: こんらんの時だけはたらく（きょうぼう）、
  `status_at_attack`: 「ワザが使われた時、すでに…」（くつろぐかおり））。一律に「特殊状態で消える」にしないでください。どくはどの説明にもないので関係しません。
  `status_at_attack` は、解決の基盤がワザの宣言のときに写した特殊状態（`Resolution.attack_status`。`effects.status_at_attack_blocked`）で決め、決定をまたぐときは続きの情報
  （決定の `context` の `attack_status`。空なら書かない）で運びます。ダメージを計算する時の特殊状態で決め直さないでください。
- 問い合わせる場所は決まっています（型で探し、`engine.py`・`resolution/` にカード id の分岐を加えない）: ワザのダメージ（`effects.attack_damage_modifiers` の
  `continuous_attack_damage_modifiers`。`kernel.deal_damage` と `preview_attack_damage` が同じ関数）・特殊能力のダメージ（`effects.received_power_damage`）・こんらんの 20
  （`procedures.confusion_damage_problem` の `confusion_power_modifiers`）・「にげる」（`effects.retreat_cost`）・トレーナー（`effects.trainer_lock_sources`）・特殊状態に
  する処理（`conditions` の付ける関数の共通の入口 `_prevented` → `effects.status_immunity`）。ほかの経路に同じ判定を複製しないでください。
- p.321 の段階の中の計算に `damage.ZERO_IF_AT_LEAST`（なぞのかべ）・`SET_IF_AT_LEAST`（ふしぎなバリアー。`DamageModifier.threshold`）・`HALVE_UP`（くつろぐかおり）・
  `HALVE_DOWN`（リフレクター）を加えました（`operation`。しきい値はその段階の直前のダメージと比べる。半分の丸めはダメージカウンターの単位。ログ `damage` の
  `damage_zero_at_least`・`damage_set_if_at_least`・`damage_halved` は当てはめたときだけ）。最終ダメージを直接書きかえたり、ワザの要素を無効にする処理にしたりしないで
  ください（なぞのかべで 0 でも、ダメージ以外の効果は受ける）。v0.45 の `ZERO_IF_BELOW`（かたくなる）とは比べる向きが逆です。段階は kyuura の GR-2000-P321-DAMAGE-ORDER の
  持ち主の区別（ワザを使うポケモンの効果は 2、受けるポケモンの効果は 8、それ以外は 6）で決め、同じ段階で順番によって結果が変わるときは v0.35 の決定 `damage_step_order`
  で選ばせます（コードで順番を決めない）。
- くつろぐかおりは 1 つのダメージの要素に 1 回だけ当てはめます（二重に当てはめない）。特殊能力のダメージ（はんげき・わるいねぞう）はワザのダメージではないので当てはめません。
  返す効果のダメージ（ほのおのかべ・こうらがえし・クロスカウンター）に当てはめるかは決まらない（CP1）ので、当てはめるかどうかで結果が変わるとき、ワザの宣言の前に
  `UNRESOLVED_CALMING_AROMA_RETALIATION`（問い `calming_retaliation`）で止めます。リフレクターはワザによる持続する効果 `state.HalvedDamage`（はたらく番は次の相手の番。
  不変条件は登録の `halved_terms()` と照らす）で、くつろぐかおりとは段階・丸め・発生源が違います（計算の部品だけを共通にした）。
- きょうぼうがはたらくのはこんらん状態の時だけなので、こんらんの 20 に当てはめるか（v0.3c と同じ問い）で、こんらん状態のわるいオコリザルのワザは、どの先読みの方法でも
  コインの前に `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` で止まります（+30 は対戦では起こらない）。これを避けるためにこんらんの 20 の扱いを決めないでください。
- 「にげる」のエネルギーの数は `effects.retreat_cost(state, player)`（`RetreatCost`。`minimum`〜`maximum`）だけで求めます。印刷の数だけを読む経路を残さないでください
  （`engine._retreat` は `retreat_cost` だけを使う）。ねんちゃくえきは決まって + 2、にげるサポートは「少なくできる」ので − 1 ずつ（少なくするかは「にげる」のプレイヤーが
  トラッシュする数で決める）、最後に 0 で下限をつけます。少なくすると増やすの当てはめ方で答えが変わる数は CP2（`UNRESOLVED_RETREAT_COST_FLOOR`。エネルギーのトラッシュ・
  こんらんのコインの前）で止めます。範囲の外は `WRONG_RETREAT_COST`（特殊能力のないときの理由の文は v0.45 と同じ）。ポケモンいれかえ・突風・ワザの入れ替えには関係しません。
  数が特殊能力で変わったときだけ、ログ `retreat`・`retreat_failed` に `retreat_cost`・`retreat_cost_printed`・`retreat_cost_increases`・`retreat_cost_reductions` を書きます。
- アレルギーかふんは、`engine._play_trainer` がカードを手札から出す前に `TRAINER_PREVENTED`（`IllegalActionError`）で拒否します（状態・乱数・ログが変わらない）。すでについている
  トレーナー・使っている最中のトレーナーは止めません。
- めんえきは特殊状態にならない効果で、すでにある特殊状態を回復しません。防いだらログ `special_condition_prevented`（状態は変えない）。防がれて結果が変わらない原典で
  決められない確かめ（マヒの再付与・TP3・コインのない Z23）は聞きません（`programs.Status`・`ReparalysisGuard`。不要な停止にしない）。効果を決めるコインは今までどおり投げます。
- 関連する 3 枚のワザ: せいちょう（`AttachEnergyFromHandOnHeads`。決定 `attach_from_hand`。`zones.attach_energy_from_hand` を使い、手札からつける通常の操作の回数・
  特殊能力の回数に数えない。ログ `attach_energy_from_hand`。0 枚は HC7）、かくさんソーラービーム（`DamageThenExactBenchTargets`。「2匹」はちょうど 2 匹。控え 1 匹は FC1、
  0 匹は対象なし。「最大2匹」の GS1 と混同しない）、リフレクター（`HalveDamageNextTurn`）、タマゴばくだん（`SelfDamageInsteadOnTails`。ワザの失敗にしない）、
  サイコエクスチェンジ（`ShuffleHandIntoDeckThenDraw`。もどす → 切る → 引く。もどしたカードは公開しない。ログ `hand_to_deck`）、ふみつけ（既存の `CoinBonusDamage`）。
- エンジンが止める `UNRESOLVED_…` は 57 件、未解決の裁定は 58 件です（CP1・CP2 は kyuura の未解決の一覧にない `not_in_kyuura`）。書き出しの形式は 11 のまま（持続する効果の
  種類 `halved_damage` は形式 8 から）。公開の API の呼び方は変えていません（公開の問い合わせ `retreat_cost`・`trainer_lock_sources`・`status_immunity` を加えた）。新しい
  拒否のコードは `TRAINER_PREVENTED`、新しい決定の種類は `attach_from_hand`、新しいログのイベントは `special_condition_prevented`・`attach_energy_from_hand`。
- ログの監査（tests/log_audit.py）は、ワザのダメージごとにはたらいている常にはたらく特殊能力とリフレクターの記録（段階・計算・順番）、こんらんのダメージに当てはまる特殊能力が
  ないこと、「にげる」の数の範囲と CP2・記録、アレルギーかふんがはたらいているときのトレーナーの使用がないこと、めんえきのポケモンが特殊状態にならないこと、
  `attach_energy_from_hand`・サイコエクスチェンジの組み立て直しを確かめます。常にはたらく特殊能力を加えたら、監査にも加えてください。
- 検証用デッキ `G46`・`P46`・`D46` と組（`PAIRINGS_V0_46`。`G46` 対 `P31` を含む）は tools/existing_effect_games.py の `--batch v0.46` です（前の版の組の結果は変わらない）。
  決定の答え方は `_v046_decision`、「にげる」は `_v046_retreat`。`WRONG_RETREAT_COST`（特殊能力で変わった数）・CP2・`TRAINER_PREVENTED` は場から確かめます。公開の固定の
  デッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## なにかの化石・ピッピ人形と化石のポケモン・見えない情報・期限のあるトレーナーの使用の禁止と 13 枚（v0.47）

- 依頼の 13 枚（なにかの化石 PMCG3-046・ピッピ人形 PMCG1-091（どちらもトレーナー）・オムナイト PMCG3-015［おみとおし］・オムスター PMCG3-021・カブト PMCG3-035［カブトアーマー］・
  カブトプス PMCG3-040・プテラ PMCG3-041［げんしのちから］・マンキー PMCG2-028［スパイ］・コラッタ（ロケット団）PMCG4-045［わるふざけ］・スリーパー PMCG3-032・マチスのイーブイ
  PMCG5-062・マチスのサンダース PMCG5-042・コダック（化石の秘密）PMCG3-010）を、kyuura データの採用で、どのワザも、どの特殊能力も、どのトレーナーの効果も登録して加えました
  （対応ポケモン 303 → 314。写しの組 `pool_v0_47`。写し 324 → 337 枚。ワザの登録 521 → 538・特殊能力の登録 39 → 44・トレーナーの登録 12 → 14）。カードごとの結果・共通の処理・
  規定と根拠・PF1・PF2・PF3・KA1・互換性・検証は docs/fossil-hidden-info-v0.47.md。ガイドブックは読んでいません。テストの定数は tests/helpers.py の `V0_47_POKEMON`（11 枚）・
  `V0_47_TRAINERS`・`V0_47_CARDS`（13 枚）。名前の似た別のカード（`JUNGLE_MANKEY` と `MANKEY`・`BROCKS_MANKEY`、`ROCKET_RATTATA` と `RATTATA`・`LT_SURGES_RATTATA`、`HYPNO` と
  `DARK_HYPNO`、`LT_SURGES_EEVEE` と `EEVEE`・`ROCKET_EEVEE`、`LT_SURGES_JOLTEON` と `JOLTEON`・`DARK_JOLTEON`、`FOSSIL_PSYDUCK` とほかのコダック）と取りちがえないでください。
  v0.47 のワザの型は `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません。
- ポケモンとして場に出せるトレーナーカード（`effects.PlayAsPokemon`）の印刷の分類はトレーナーカードのままです（写し・印刷の `CardDefinition` を変えない）。カードの定義は場所で
  決まり、`GameState.card_def(uid)` は、そのカードが場のポケモンを作っているカード（いちばん上か、下に重なったカード）のあいだだけ場での役割の定義（`category` "pokemon"・
  HP 10・タイプなし・弱点なし・抵抗力なし・ワザなし・特殊能力なし・`play_role`）を返します。手札・山札・サイド・トラッシュ・使用中ではトレーナーカードです（デッキの検査・
  切り直し・カードを選ぶ効果・トレーナーの使用の禁止もその分類）。場所によらない定義は `printed_def`・`in_play_def`（ログから場を組み立て直す監査・不変条件が使う）。
  「場にいる」の印を状態に持ったり、カード id で分けたりしないでください（`engine.py`・`resolution/` にカード id の分岐はない）。場の HP 10 などは pcg-search.com の同じ版の
  ページの値で、採用の記録に書いた（kyuura のトレーナーのデータに欄がない。kyuura への報告事項）。
- 使う（`PlayTrainer`）と、ベンチの最後にポケモンとして出し（`zones.put_trainer_into_play`。ログ `play_trainer_as_pokemon`）、トラッシュしません（`TrainerEffect.enters_play`）。
  ベンチに空きがなければ手札から出す前に `BENCH_FULL`。トレーナーカードを使うことなので、トレーナーの使用の禁止で止まります。場のポケモンの規定（エネルギー・ついている
  トレーナー・特殊状態・入れ替え）のままで、英語版の「can't be …」「can't retreat」を持ち込まないでください。なにかの化石には「なにかの化石から進化」の 1 進化カードを通常の
  進化の手順で重ねます（p.310 の制限も同じ）。
- 進化カードがのっていない（いちばん上が場での役割のカード）なら「きぜつ」してもカウントされません（`effects.counts_as_knockout`。きぜつの処理の前に聞く）。トラッシュは
  するが相手はサイドを取らず、ログ `knock_out` に `counted: False`（カウントされるきぜつのログは v0.46 と同じ）。ワザのあと・特殊能力のあと・ポケモンチェックのどれも
  解決の基盤の `_knock_out_all` を通します。サイドの数に関わる不変条件・監査も、カウントされないきぜつを数えません。
- 場からすてる操作は新しいコマンド `DiscardFromPlay(player, pokemon)`（`engine._discard_from_play`。自分の番の `MAIN` だけ。進化カードがのっていない場での役割のポケモンだけ。
  ついているカードもトラッシュ。ログ `discard_from_play`。持続する効果は理由 `discard_from_play`）です。きぜつ・トレーナーの使用・特殊能力ではありません（禁止・ガスで
  止まらない）。バトル場が空いたら `resolution.after_power`（v0.42 の特殊能力のあとと同じ続き）。拒否は `NOT_DISCARDABLE`・`POKEMON_NOT_YOURS`・`POKEMON_NOT_IN_PLAY`・
  `NOT_YOUR_TURN`（どれも状態を変える前）。
- 決められない場合（新しい停止コード）: PF1（`UNRESOLVED_PLAY_AS_POKEMON_SETUP`。対戦準備で手札にたねポケモンがなく、なにかの化石・ピッピ人形がある → 切り直しの前に
  `Phase.HALTED`。これらを最初のポケモンとして出す操作 → `UnsupportedError`。1997 年の会報（kyuura rule_history.json の P35）は別の版の記録なので使わない）・
  PF2（`UNRESOLVED_PLAY_AS_POKEMON_RETREAT`。バトル場のこれらの「にげる」。エネルギー・コインの前。`effects.retreat_cost` も投げる。ポケモンいれかえ・突風は使える）・
  PF3（`UNRESOLVED_BREEDER_ON_PLAY_AS_POKEMON`。ポケモン育て屋さんで場のなにかの化石に 2 進化カード）・KA1（`UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER`。ポケモンチェックの
  どくのダメージに［カブトアーマー］を当てはめると量が変わる → ダメージの前に `Phase.HALTED`）。どれも推測で決めないでください。
- タイプ（色）のない場のポケモン: 「相手の対戦ポケモンと同じ色の控えポケモン」（v0.39 のビリビリ）で相手の対戦ポケモンがこれらなら、同じ色の控えはいない（実装上の判断。
  `programs.BenchDamage.targets`。None を「タイプでしぼらない」と読まない）。
- 常にはたらく特殊能力（v0.46 の `ContinuousPower`）: ［おみとおし］（`RevealOpponentHand`。観測で相手の手札を全員に見せるだけで、ゲームの処理は変えない。
  `effects.hand_revealed_by`）・［カブトアーマー］（`HalveDamageReceived`。8 段階の `HALVE_DOWN`。特殊能力のダメージにも。こんらん状態では使えないので、こんらんの 20 は
  そのまま）・［げんしのちから］（`PreventEvolution`。`effects.evolution_preventers`。進化の入口の共通の確かめ `evolution.evolution_block` の最初に聞く。どの入口も
  `EVOLUTION_PREVENTED`。ポケモン育て屋さんも使う前に止める。進化カードを手札に加える効果は止めない）。はたらいているかは今の場から求めます（v0.46 と同じ）。
- 見えないカードを扱う効果: ［スパイ］（`PeekCard`。決定 `peek_card` は位置で選ぶ。`zones.look_at_card`。カードを動かさない）・［わるふざけ］（`SwapPrizeWithDeckTop`。決定
  `select_prize_card`。`zones.swap_prize_with_deck_top`。だれも見ない・切らない）・みらいよち（要素 `ArrangeDeckTop`。決定 `select_deck_owner` → `select_look_count` →
  `arrange_deck_top`。山札があるときの 0 枚は GS1）・おどろかす（要素 `LookHandCardToDeck`。決定 `select_hand_card`。見る → 相手が山札にもどす → 切る。相手の手札 0 枚は FC1）。
  裏向き・見えないカードを選ぶ決定の選べるものは位置・プレイヤー・数で、カードの uid を入れないでください（見る前に内容を漏らさない）。英語版の「random」を持ち込まないで
  ください（使ったプレイヤーが位置で選ぶ）。見られる・入れかえるカードがない［スパイ］・［わるふざけ］は PW3。
- プレイヤーに渡す観測（`kyuura_engine/observation.py`。公開の `observe(state, viewer)`・`visible_log(state, viewer)`）: 状態とログは内部の完全な記録のままで、観測が見て
  よい情報だけを取り出します（手札は持ち主（［おみとおし］がはたらいていれば全員）、山札・サイドは枚数だけで uid も渡さない、対戦準備のポケモンは表にするまで持ち主だけ、
  決定の選べるものは決めるプレイヤーだけ、カードの id は見えるカードだけ）。決定の種類を加えたら `OPTION_MEANINGS` に、ログのイベントの種類を加えたら `PRIVATE_FIELDS`・
  `PUBLIC_EVENTS` に加えてください（ない種類は `ValueError`。黙って全部を見せない）。観測のかわりに `GameState`・ログ・`state_to_dict` をプレイヤーに渡さないでください。
  ログの監査の `observation_problems`（tests/log_audit.py）が、観測を状態から別に求めて照らします。
- 期限のあるトレーナーの使用の禁止（ずつう `LockOpponentTrainersNextTurn`・こうしゅうは `DamageThenLockOpponentTrainersOnHeads`。要素 `LockOpponentTrainers`）は、相手プレイヤーに
  与える記録 `GameState.trainer_locks`（`state.TrainerUseLock`。消える番は与えた番 + 1 で、その番の終わりに `procedures.remove_expired_trainer_locks` が消す。ログ
  `trainer_lock_added`・`trainer_lock_removed`）です。場のポケモンの持続する効果にしないでください（入れ替え・場をはなれることでは消えない）。確かめるのは
  `effects.trainer_use_blockers`（v0.46 の［アレルギーかふん］と別の記録として、それぞれの期間で判定）だけで、`engine._play_trainer` が手札から出す前に `TRAINER_PREVENTED`。
  場のポケモンへの効果ではないので「ワザをうけない」「とうめい」を評価しません。不変条件は `engine._trainer_lock_problems`（登録の `lock_terms()`・ログとの対応）。
  v0.56 から、ロケット団の実験の「うら」の禁止も同じ記録（`origin="trainer"`。使ったプレイヤー自身に与え、消える番は使った番 + 2）で持ちます。ワザの禁止（`origin="attack"`）とは別の記録で、
  同じ消える番に重なってもそれぞれ消えます（下の「相手の決定・番の終わり・期限のある効果のトレーナー 10 枚（v0.56）」）。
- 書き出しの形式 12 = 形式 11 + 最上位の `trainer_locks`（形式 1〜11 は禁止があると `ValueError`）。監査の `LATEST_FORMAT` は 12（v0.48 で 13、v0.49 で 14、v0.50 で 15、v0.56 で 16、v0.57 で 17）。次の新しい形式は 13（v0.48 で加えた。その次は 14（v0.49 で加えた）、15（v0.50 で加えた）、16（v0.56 で加えた）、17（v0.57 で加えた））。場のなにかの化石・
  ピッピ人形は書き出しの形を変えません。新しい決定の種類は `peek_card`・`select_prize_card`・`select_deck_owner`・`select_look_count`・`arrange_deck_top`・`select_hand_card`、
  新しいログのイベントは `play_trainer_as_pokemon`・`discard_from_play`・`look_at_card`・`look_at_deck_top`・`look_at_deck_top_none`・`arrange_deck_top`・
  `swap_prize_with_deck_top`・`trainer_lock_added`・`trainer_lock_removed`、新しい拒否のコードは `EVOLUTION_PREVENTED`・`NOT_DISCARDABLE`。エンジンが止める `UNRESOLVED_…` は
  61 件、未解決の裁定は 62 件です（PF1〜PF3・KA1 は kyuura の未解決の一覧にない `not_in_kyuura`）。
- こんらんの 20 にプラスパワー・ディフェンダーを計算するか（v0.3c）の止める処理は、読み方ごとの結果を比べずに止めます。v0.47 のプテラ（闘・抵抗力 闘）は、こんらんの 20 が
  0 になり、プラスパワーが 1 枚以下ならどの読み方でも同じ結果ですが、止める処理は変えていません（範囲がこの組だけ必要より広い。tests/test_unresolved_rulings_v0_3d.py）。
- 道具・テストの手順でバトル場のポケモンのにげるエネルギーを印刷の値で読むときは、場での役割のポケモン（値が None）を扱ってください（tests/helpers.py の
  `driver_retreat_cost`）。対戦のテストの `play_game`（tests/v017_games.py）は、PF2・`EVOLUTION_PREVENTED`・`TRAINER_PREVENTED` を場から確かめてから別の操作を続けます。
- 検証用デッキ `F47`・`H47`・`A47` と組（`PAIRINGS_V0_47`。`H47` 対 `P31` を含む）は tools/existing_effect_games.py の `--batch v0.47` です（前の版の組の結果は変わらない）。
  決定の答え方は `_v047_decision`、特殊能力は `_v047_power`、場に出す・すてる・PF2 を試す手順は `_v047_trainer`。v0.47 のカードがある対戦では、受け付けた操作ごとに観測を
  確かめます。PF1 で対戦準備が止まる局があります（既知の未解決）。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 場のポケモンの今有効な最大HP・タイプ・弱点・抵抗力と 7 枚（v0.48）

- 依頼の 7 枚（ポリゴン（第1弾）PMCG1-064・ポリゴン（ロケット団）PMCG4-050・モルフォン PMCG2-015［へんしょく］・ナツメのゴース PMCG6-049［ガスのからだ］・ナツメのゴースト
  PMCG6-050・ナツメのゲンガー PMCG6-054・キョウのメタモン PMCG6-072）を、kyuura データの採用で、どのワザも、どの特殊能力も登録して加えました（対応ポケモン 314 → 321。
  写しの組 `pool_v0_48`。写し 337 → 344 枚。ワザの登録 538 → 549・特殊能力の登録 44 → 46）。カードごとの結果・共通の処理・点検した処理・規定と根拠・VS1・PG1・MH1・
  互換性・検証は docs/effective-pokemon-properties-v0.48.md。ガイドブックは読んでいません。テストの定数は tests/helpers.py の `V0_48_POKEMON`。同じ名前の別のカード
  （`PORYGON`（PMCG1-064）と `ROCKET_PORYGON`（PMCG4-050））・名前の似た別のカード（`SABRINAS_GASTLY` と `GASTLY`、`SABRINAS_HAUNTER` と `HAUNTER`・`BASE_HAUNTER`、
  `SABRINAS_GENGAR` と化石の秘密のゲンガー、`KOGAS_DITTO` とメタモン）と取りちがえないでください。v0.48 のワザの型 8 は `ATTACK_TYPES_SINCE_V0_17` に加え、
  `v013_checks.VERIFIED` には入れていません。
- 場のポケモンの最大HP・タイプ（色）・弱点・抵抗力は、`effects.max_hp`・`weakness_of`・`resistance_of`・`type_readings`（公開）と `definition_views`（ダメージの計算に
  渡す今有効な値の定義）で求めます。印刷の定義（`printed_def`）・場での役割の定義（v0.47。`card_def`）・共有する `CardDefinition` を書きかえないでください（違う値は
  `dataclasses.replace` の新しい値。状態に持たない）。HP・タイプ・弱点・抵抗力を読む処理を加えるときは、カードの定義の `hp`・`pokemon_type`・`weakness`・`resistance` を
  直接読まず、この問い合わせを使ってください（ダメージ・こんらんの 20・特殊能力のダメージ・きぜつの判定・残り HP を使うワザ・最大HPの条件・進化の確認・色で選ぶ対象・
  タイプで決まる特殊能力・観測。docs 2.3 節の表）。場以外のカードには当てはめません（問い合わせは場のポケモンを受け取る）。カード id で分ける処理を `engine.py`・
  `resolution/` に加えないでください（型で探す）。
- 今有効な値を求めるのに要る履歴だけを状態に持ちます: ワザによる持続する効果 `WeaknessChange`（テクスチャー1。相手に与える）・`ResistanceChange`（テクスチャー2。色だけ。
  数は変えない）・`MaxHpSet`（きょだいか。最大HP 80）は、与えたときからはたらき（`turns_until_active` 0）、期限では消えず（`lasting`）、ベンチにもどる・場をはなれる・進化・
  きぜつで消えます。同じ型の効果をもう一度与えるときは `persistent.replace_persistent_effect`（前の効果を理由 `replaced` で消す）。［へんしょく］は場のポケモンの記録
  `PokemonInPlay.type_shift`（`TypeShift`。色・番・いちばん上のカード・ベンチにもどったか。進化で消す。書き出しの形式 13）。［ガスのからだ］（`MaxHpPerAttachedEnergyCards`。
  v0.46 の `ContinuousPower`）は記録を持たず、今の場から求めます。「きょだいか」の効果の有無は、最大HP（`max_hp`）と「はたく」（値 `AmountIfSelfMaxHpSet`）が同じ問い合わせ
  `persistent.max_hp_set` で見ます。
- ［へんしょく］で変えた色がいつまで続くかは決まりません（VS1。`UNRESOLVED_SHIFT_COLOR_DURATION`）。決まっているのは、使った番のうちで、ベンチにもどっておらず、
  いちばん上のカードが同じで、力が消えていない（ねむり・マヒ・こんらん・かがくへんかガスでない）ときだけ（`type_shift_determined`）で、それ以外は 2 つの読み方
  （`type_readings` が (変えた色, 印刷の色)）を持ちます。色を読む処理は `same_for_type_readings`（または読み方ごとの比べ）で、2 つの読み方で結果が変わるときだけ止めます。
  どちらか 1 つを選んで続けないでください。力を使えなくすること（特殊状態・ガス）と、変えた色を消すことを同じ処理にしないでください。［へんしょく］で選べる色は場にいる
  ポケモンの今有効な色（無色を含む。場での役割のポケモンは色がない）。
- テクスチャー1・2で選べる色は無色以外の 8 つ（悪・鋼を含む。実装上の判断。`effects.NON_COLORLESS_CHOICES`）。弱点・抵抗力を持たないポケモンの弱点・抵抗力を変える場合は
  PG1（`UNRESOLVED_CHANGE_ABSENT_WEAKNESS_RESISTANCE`。宣言の前）で止めます。英語版の文面の条件を持ち込まないでください。
- 最大HPがダメージ以外の原因で下がり、のっているダメージ以下になる場合: ワザの効果で下がったら、ワザのあとのきぜつの判定（GR-2000-P323-KNOCKOUT）。そのポケモン自身を
  進化させる場合は既存の H1（`UNRESOLVED_EVOLUTION_HP`。`effects.evolution_hp` で求める）。それ以外（にげる・トレーナー・特殊能力・進化によるかがくへんかガス・
  ポケモンチェックの回復など）は MH1（`UNRESOLVED_MAX_HP_DROP`）で、その操作を受け付けません（`engine._apply` が `effects.max_hp_drops` で比べる）。コインの結果で
  受け付けるかが変わらないよう、にげる（`engine._retreat_max_hp_drop_check`）・ポケモンいれかえ／突風（手札から出す前。`effects.switch_max_hp_drop_check`）・かおりのわな
  （コインの前）・ポケモンチェック（ねむりのコイン・マヒの回復の前に `Phase.HALTED`）は先に確かめます。最大HPを下げうる操作・効果を加えるときは、同じ確かめを置いて
  ください（決定への答えで MH1 に当たると答えられない決定が残る）。H1 を別の原因に広げないでください。ワザの途中の決定を待つあいだに下がる場合は
  `UNSUPPORTED_MAX_HP_DROP_DURING_ATTACK`（エンジンの未対応。研究の対応表の停止コードに入れない）。
- 最大HPをその数にする効果と大きくする特殊能力が同じポケモンに同時にはたらく場合は、順番が決まらないので `max_hp` が `RuntimeError` です（今の写しでは起こらない）。
  そのようなカードを加えるときは、先に問いを加えてください。
- ナイトスピリッツは、自分の場の名前の合うポケモンの数（いちばん上のカードの名前の完全一致。重なったカードを数えない。名前は登録の引数 `names`）だけコインを投げ、
  「おもて」の数でまとめて先読みします。ダメージぞうふくはダメージカウンターをのせる効果（ワザによるダメージではない。GR-2000-P320-COUNTER-MOVE）。やみのこえは v0.40 の
  `ReturnOpponentToDeck`（`required` が偽。控えが要るという条件を持ち込まない）。
- 観測（`observe`）の場のポケモンの `hp` は今有効な最大HPです（カードの定義の HP は `printed_hp`）。`pokemon_type`（VS1 で決まらなければ None）・`pokemon_type_readings`・
  `weakness`・`resistance`・`resistance_value`・`type_shift` を加えました。書き出し（`state_to_dict`）の `hp` はカードの定義の HP のままです。新しい決定の種類は
  `select_color`、新しいログのイベントは `type_shift`、持続する効果の種類は `weakness_change`・`resistance_change`（`color`）・`max_hp_set`（`amount`）、消える理由は
  `replaced`。ログの監査（tests/log_audit.py）は、ログから組み立てた今有効な最大HP・弱点・抵抗力・色の読み方をエンジンの問い合わせと照らします。
- 書き出しの形式 13 = 形式 12 + 場のポケモンの `type_shift`（形式 1〜12 は記録があると `ValueError`）。監査の `LATEST_FORMAT` は 13（v0.49 で 14、v0.50 で 15）。次の新しい形式は 14（v0.49 で加えた。その次は 15（v0.50 で加えた））。
- エンジンが止める `UNRESOLVED_…` は 64 件、未解決の裁定は 65 件です（VS1・PG1・MH1 は kyuura の未解決の一覧にない `not_in_kyuura`）。
- 検証用デッキ `C48`・`S48` と組（`PAIRINGS_V0_48`。`C48` 対 `S48`・`C48` 対 `P31`・`S48` 対 `P31`）は tools/existing_effect_games.py の `--batch v0.48` です（前の版の
  組の結果は変わらない）。［へんしょく］は `_v048_power`、色の決定は `_v048_decision`。MH1 と［ガスのからだ］のポケモンの進化の H1 は、tests/v017_games.py の `play_game`
  が場から確かめ、その番はそのカードを手順に見せません（`make_policy`）。PG1 は `V031_STOPS` で場から確かめます。公開の固定のデッキ・既存の変種には入れていません。
  勝敗で採用を判断しないでください。

## ワザの出どころ・今の姿と、ナツメのフーディン・メタモン・タケシのキュウコン・思い出させる（v0.49）

- 依頼の 4 枚（ナツメのフーディン PMCG6-053［サイコリンク］・メガバーン、メタモン PMCG3-042［へんしん］、タケシのキュウコン PMCG5-019「ばける」・おにび、トレーナーの思い出させる
  PMCG5-071）を、kyuura データの採用で、どのワザも、どの特殊能力も、トレーナーも登録して加えました（対応ポケモン 321 → 324。写しの組 `pool_v0_49`。写し 344 → 348 枚。ワザの登録
  549 → 551・特殊能力の登録 46 → 49・トレーナーの登録 14 → 15）。カードごとの結果・共通の処理・2000年2月の基準と後のエラッタの区別・未解決・技術的な制限・実装上の仮定・互換性・
  検証は docs/virtual-attacks-transformation-v0.49.md。ガイドブックは読んでいません。テストの定数は tests/helpers.py の `V0_49_POKEMON`・`V0_49_CARDS`。名前の似た別のカード
  （`DITTO`（PMCG3-042）と `KOGAS_DITTO`（PMCG6-072）、`SABRINAS_ALAKAZAM` と `ALAKAZAM`・`DARK_ALAKAZAM`）と取りちがえないでください。
- 場のポケモンについて、実際のカード（uid・持ち主。`PokemonInPlay.card`・`evolution_stack`・`disguise`）・今の姿（`effects.current_form` → `Form`。`printed`・`transform`
  （［へんしん］）・`disguise`（「ばける」）。定義は `form_def`）・今使えるワザとその出どころ（`available_attacks` → `AttackOption`。ワザを印刷したカードの uid `card`・
  `AttackKey`・経路 `route`・供給するポケモン `provider`・選ぶと止める理由 `problem`）・今持つ特殊能力とその出どころ（`powers_of` → `PowerSlot`）を区別します。どれも状態に
  持たず、問い合わせのたびに今の場から求めます。印刷の定義・共有する `CardDefinition`・カードの id を書きかえて姿を変えないでください。v0.48 の今有効な最大HP・タイプ・弱点・
  抵抗力の問い合わせは、もとにする定義を今の姿の定義にしました（`printed` なら v0.48 と同じ値）。名前・HP・タイプ・ワザ・特殊能力・にげる・段階を読む処理を加えるときは、
  いちばん上のカードの定義を直接読まず、これらの問い合わせを使ってください。`engine.py`・`resolution/` にカード id の分岐を加えないでください。
- ワザは、印刷したカードの uid とワザの位置で指します（`UseAttack(player, attack_index, card=None)`。None は今の姿のカード。v0.48 までの呼び方・辞書はそのまま。既定の None は
  辞書に書かない）。特殊能力も同じ（`UsePokemonPower(..., card=None)`）。ワザの名前・一覧の位置で指さないでください。効果の登録は `AttackKey`（ワザを印刷したカードの id と位置）で
  引き、ワザを実行するのはいつもバトル場のワザを使ったプレイヤーのポケモンです（必要なエネルギー・説明の条件・自分へのダメージ・「このカード」・弱点・抵抗力のタイプはそのポケモン
  について処理する。供給するポケモン・重なった進化前のカードは処理しない）。ワザのログ `attack` の `card`・`card_id`・`route`・`provider` は出どころがいちばん上のカードでない
  ときだけ書きます。ワザを使ったポケモンの不変条件は、ワザのログの `card_id` と比べます（いちばん上のカードと比べない）。
- 必要なエネルギー: ［サイコリンク］・思い出させるのワザは自分のワザとしてそのまま払います。「ゆびをふる」の支払いの免除（v0.31）を流用しないでください。［へんしん］の
  メタモンは、エネルギーカードをどの色としても使えます（`any_color_energy`・`attack_cost_payable`。1 枚 1 つ。二重に数えない）。説明がタイプのエネルギーを数える・選ぶときの
  読み方（`energy_type_readings`）で結果が変わるときだけ TE1 で止めます。
- 使用禁止（メガバーン・ドわすれ・あわあわ・きあいずつき）と 1 度だけ使えるワザは `AttackKey` で探します。効果を与えたワザがいちばん上のカードのものでなければ、持続する効果に
  `attack_card`・`target_attack_card`（書き出しの形式 14）を書きます。1 度だけ使えるワザをほかのカードのワザとして使うのは VA1。まねるワザ（ゆびをふる・ちょうのうりょく・
  ドわすれ）は相手の対戦ポケモンが今持つワザから `AttackKey` ごとに 1 つ選びます（`held_attack_keys`。選べるものが v0.48 と同じなら決定の形も同じ）。
- ［サイコリンク］（`AttacksOfOwnTypePokemon`。常にはたらく）は、自分の場のこのカード以外の今有効なタイプ「超」のポケモンの、今の姿のカードのワザを持ちます（ほかの
  ［サイコリンク］・思い出させるで持つワザは数えない。再帰しない）。VS1 で供給するかが変わるワザは選ぶと止めます。
- ［へんしん］（`TransformIntoDefender`。常にはたらく）は、バトル場にいて特殊状態（ねむり・マヒ・こんらん）・かがくへんかガスでないとき、相手の対戦ポケモンのいちばん上の
  カードを今の姿にします（相手の受けている効果は写さない。メタモンどうしは相手のいちばん上のカード）。写した特殊能力（TF1）・相手がばけている・ポケモンとして出したトレーナー
  （TF2）は決まりません。英語版の「always has this Pokémon Power」を持ち込まないでください。
- 「ばける」（`Shapeshift`。宣言して使う。自分の番に 1 回）は、手札の進化カードを `PokemonInPlay.disguise` にのせます（進化ではない。ログ `disguise`。もどすのはコマンド
  `RemoveDisguise(player, pokemon)`（ログ `disguise_removed` の `reason` `revert`。のせていなければ `NOT_DISGUISED`）か、ねむり・マヒ・こんらんにする処理（`reason`
  `special_condition`））。2000.02.14 版（2000年2月）の基準で、のせたカードの特殊能力ははたらき、使えます。kyuura の ERR-BROCK-NINETALES（『トレーナーズ』Vol.6・2000年5月）の
  「はたらかず、使うこともできない」はこの基準のあとの変更なので持ち込まないでください（同じ記録の p.69 の「手札から場に出したときに使える能力は、[ばける]で場に出したときには
  使えません」にはしたがう。「場に出た時」の特殊能力は DG2）。のせたカードのあるポケモンは進化・退化できません（`evolution_forbidden`。［へんしん］のメタモンも）。DG1・DG3・
  手札に進化カードがない PW3・もどす操作の MH1 は既存の・新しい問いで止めます。
- 思い出させる（`RecallPreEvolutionAttacks`）は、この番の記録（`GameState.recalls` の `RecallEffect`。ログ `recall`。番の終わりに消える）を置き、使ったときの対戦ポケモンに
  実際に重なっている進化前のカードのワザを、そのポケモンのワザとして使わせます（GR-2000-P310-EVOLUTION の「進化前に持っていたワザ」。すぐ下のカードのワザは使える）。英語版の
  「any Evolution card attached to it」で範囲を広げないでください（2 進化のいちばん下は RC2）。RC1・RC3・RC4 は記録で決まりません。
- 新しく決められない姿（TF1・TF2・DG1。`effects.form_problems`）を作るコマンドは受け付けません（`engine._apply` の `_fresh_form_problem`）。決定への答えでどの答えでもそうなるなら、
  その前の状態で `Phase.HALTED`（答えのない決定を残さない。`_decision_has_unstopped_answer`）。トレーナーの効果の途中の決定は使用中のトレーナーを残して止められないので、
  `engine._trainer_dead_end` が、どの答えの続きも受け付けられない使う・答えを受け付けません（状態の複製の上で深さ優先。答えは 256 まで）。かおりのわなは、どの控えでも止まるなら
  コインの前に止めます（`effects.switch_choice_stops`）。MH1 の入れ替えの確かめ（`switch_max_hp_drop_check`）は、どの控えでも下がるときだけ使う前に止めます（v0.48 は最初の控え
  だけで確かめていた）。新しく姿を変える効果・入れ替える効果を加えるときは、これらの確かめを通してください。
- 「最大HPを決まった数にする効果と大きくする特殊能力」の組（v0.48 の `max_hp` の RuntimeError）は、v0.49 でも到達しません（［ガスのからだ］は TF1 で写さない）。到達する組を作る
  カードを加えるときは、先に問いを加えてください。
- v0.49 で直した既存の不具合: `carry` でない決定（エネルギーのトラッシュなど）をまたぐと、もう HP 以上のポケモンのこんじょうの写しがなくなり、きぜつの判定が内部エラー
  （わるいリザードンの「れんぞくファイヤーボール」とサカキのカイリキー。v0.48 の木でも起こる）。`AttackRun.suspend` が、そのポケモンの写しだけを `frame` の `guts` で運びます
  （HP 以上のポケモンがいなければ v0.48 と同じ決定の形）。
- 書き出しの形式 14 = 形式 13 + 場のポケモンの `disguise`（`{"card", "card_id"}` か None）・最上位の `recalls`（持続する効果の `attack_card`・`target_attack_card` は値があるとき
  だけ）。形式 1〜13 は、のせたカード・記録・その項目のある効果・のせたカードの特殊能力の使用の記録があると `ValueError`。監査の `LATEST_FORMAT` は 14（v0.50 で 15）。次の新しい形式は 15（v0.50 で加えた。その次は 16）。
  今の姿・今使えるワザは書き出さず、観測（`observe` の場のポケモンの `form`・`disguise`・`attacks`・`powers`）が書きます。新しいログのイベントは `disguise`・`disguise_removed`・
  `recall`（どれも公開）、新しい拒否のコードは `NOT_DISGUISED`。
- エンジンが止める `UNRESOLVED_…` は 75 件、未解決の裁定は 76 件です（TE1・TF1・TF2・DG1・DG2・DG3・VA1・RC1・RC2・RC3・RC4 の 11 件。どれも kyuura の未解決の一覧にない
  `not_in_kyuura`）。
- ログの監査（tests/log_audit.py）は、のせたカードの組み立て直し（手札 → のせたカード → トラッシュ）と、今の姿で求めた最大HP・弱点・抵抗力・色・特殊能力をエンジンの問い合わせと
  照らします。姿を変える処理を加えたら、監査にも加えてください。
- 検証用デッキ `A49`・`D49` と組（`PAIRINGS_V0_49`。`A49` 対 `D49`・`A49` 対 `P31`・`D49` 対 `P31`）は tools/existing_effect_games.py の `--batch v0.49` です（前の版の組の結果は
  変わらない）。出どころがいちばん上のカードでないワザを優先する手順は `_v049_attack`、「ばける」・もどす操作は `_v049_power`、思い出させるは `_v049_trainer`、決められない姿・
  MH1 で拒否される決定の答えは `_v049_answer`。tests/v017_games.py の `play_game` は TF1・TF2・DG1〜DG3・MH1・RC1・RC4 を場から確かめてから別の操作を続けます。公開の固定の
  デッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 退化の共通の処理と、ミュウ・退化スプレー（v0.50）

- 依頼の 2 枚（ミュウ PMCG3-033 のサイコウェーブ・たいかビーム、トレーナーの退化スプレー PMCG1-086）を、kyuura データの採用で、どのワザも、トレーナーも登録して加えました（対応ポケモン
  324 → 325。写しの組 `pool_v0_50`。写し 348 → 350 枚。ワザの登録 551 → 553・特殊能力の登録 49・トレーナーの登録 15 → 16）。カードごとの結果・共通の処理・トレーナーのあとの進行・
  再利用した記録と導いた処理・未解決・実装上の仮定・互換性・検証は docs/mew-devolution-spray-v0.50.md。ガイドブックは読んでいません。英語版の文面・「退化スプレーHYPER」の文面を
  持ち込まないでください。テストの定数は tests/helpers.py の `MEW`・`DEVOLUTION_SPRAY`・`V0_50_POKEMON`・`V0_50_CARDS`。v0.50 のワザの型（`DamageTimesDefenderEnergyCards`・
  `DevolveChosenPokemon`）は `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません。
- 退化の規定は kyuura の記録の再利用です（研究の対応表の `applied_rule_records`。GR-2000-P324-DEVOLUTION・CR-SHELL-ATTACK-ENDS-ON-DEVOLUTION・CR-CHEMICAL-GAS-LEAVES・
  GR-2000-P323-KNOCKOUT）。退化で最大HPがのっているダメージ以下になったポケモンのきぜつは、p.323「16」・p.319・p.324「19」から導いた処理（SUPPORTED）で、第4版の冊子の記録を
  根拠にしていません。H1・MH1 を退化に機械的に当てはめないでください（docs 2 章）。
- 退化は `evolution.devolve(state, owner, target, count, destination=…, by_player=…, effect=… | trainer=…)` だけで行います（たいかビーム・退化スプレーで共通）。通常の進化を逆に
  たどる処理・「ばける」をもどす処理（`RemoveDisguise`）を流用しないでください。対象は実際に進化カードが重なっているポケモン（`effects.devolution_candidates`。今の姿ではなく
  実際の重なり。［へんしん］のメタモンは入らない）で、上から順にはがします（ポケモン育て屋さんの重なりからは 1 枚でたねポケモンにもどる。飛ばした 1 進化カードを作らない）。
  行き先はたいかビームが持ち主の手札、退化スプレーが持ち主のトラッシュ。退化したら特殊状態・持続する効果（理由 `devolve`）・にげるの失敗の記録・［へんしょく］の記録・はがした
  カードの 1 度だけ使えるワザの記録を消し、ダメージ・エネルギー・ついているトレーナー・場のポケモンの番号・場に出た番は残します（すべての履歴を一律に消さない）。退化した番は
  `PokemonInPlay.devolved_turn`（`current_form_turn` は場に出た番・進化した番と退化した番の遅いほう）。今の姿・最大HP・ワザ・特殊能力は v0.48・v0.49 の問い合わせが残ったいちばん上の
  カードから求めます。ログは `devolve`（公開）。
- 「自分の番ごとに1回」の特殊能力の記録は、いちばん上のカードが進化・退化で変わる直前に `evolution.retag_power_uses` が (番号, 位置) を (番号, 位置, 使ったカード) に置きかえます
  （v0.49 までは進化したカードの同じ位置の特殊能力を止めていた。意図した変更。docs 8 章）。退化でまたいちばん上になったカードの記録がこの番にあるときの再使用は DV3 です。
- 退化スプレーは、使ったプレイヤーが自分の進化ポケモンを選び（`select_pokemon`）、はがす枚数を選ぶ（新しい決定 `select_devolve_count`。0 枚は「ことができる」の、はがさないこと。
  ログ `devolve_declined`）。トレーナーで場のポケモンがきぜつしうる実装は `TrainerEffect.may_knock_out = True` にし、`engine._finish_trainer` がカードをトラッシュしてから
  `resolution.after_trainer`（ログ `knock_out` の `timing` は `trainer`。サイド → 勝ち負け → バトル場に出す → `continue_turn` で同じ番の `MAIN`）を呼びます。v0.42 の
  `after_power` と同じ形です。トレーナーの処理が使う解決の基盤の名前は `Context`・`after_trainer` だけです（tests/test_kernel_integration_v0_15.py の `DependencyTest`）。
  ほかのトレーナーのあとに HP 以上のポケモンがいれば、きぜつにせず不変条件で止めます。
- たいかビームはワザの効果なので、はがす前に「ワザをうけない」状態・「とうめい」を評価します（要素の種類 `devolve`。自分のポケモンでも評価する）。進化ポケモンがいなければ
  何もしません（ログ `devolve_none`）。サイコウェーブは相手の対戦ポケモンについているエネルギーカードの枚数 × 10（1 段階。サイコキネシスの `DamagePlusDefenderEnergy` と別の型）。
- 決まらない場合（新しい停止コード）: DV1（`UNRESOLVED_DEVOLUTION_INTERMEDIATE_KNOCKOUT`。複数枚はがす途中の重なりできぜつするかで結果が変わる枚数。選べるが選ぶと止める）・
  DV2（`UNRESOLVED_EVOLVE_AFTER_DEVOLUTION`。今の番に退化したポケモンを同じ番に進化させる。進化の入口の共通の確かめ `evolution.evolution_block`・ポケモン育て屋さん・山札から
  重ねるワザ・［うか］。サカキの許可があっても）・DV3（`UNRESOLVED_POWER_REUSE_AFTER_DEVOLUTION`）・DV4（`UNRESOLVED_DEVOLUTION_SPRAY_WITHOUT_TARGET`。使う前）・DV5
  （`UNRESOLVED_DEVOLUTION_TARGET_DISGUISED`。「ばける」のポケモン。選べるが選ぶと止める。どれもそうなら宣言の前・使う前）。どれも推測で決めないでください（DV1 を「はがし終えて
  から判定」「1 枚ずつ判定」のどちらにもしない。DV2 で進化の制限を当てはめる・外すのどちらにもしない）。v0.13 の S29・v0.8 の G16 は、退化させるカードがなかったので「到達しない」
  「未実装」としていたもので、v0.50 から kyuura の CR-SHELL-ATTACK-ENDS-ON-DEVOLUTION・CR-CHEMICAL-GAS-LEAVES にしたがって処理します（停止コードではない）。
- 自分のポケモンの退化で相手の［へんしん］のメタモンの最大HPが下がり、のっているダメージ以下になる場合は v0.48 の MH1（その答えを受け付けない）です。
- 書き出しの形式 15 = 形式 14 + 場のポケモンの `devolved_turn`（`power_uses_this_turn` に置きかえた 3 つの値の記録も入る）。形式 1〜14 は、退化した番・その記録があると
  `ValueError`。監査の `LATEST_FORMAT` は 15（v0.56 で 16、v0.57 で 17）。次の新しい形式は 16（v0.56 で加えた。その次は 17（v0.57 で加えた））。新しい決定の種類は `select_devolve_count`、新しいログのイベントは `devolve`・`devolve_declined`・`devolve_none`
  （どれも公開）。観測の場のポケモンに `devolved_turn`。公開の API の呼び方・コマンドは変えていません。
- 不変条件: 退化した番（`engine._devolution_state_problems`）・重なりと進化・退化のログ（`_stack_history_problems`。退化のログがあれば逆にたどって重なりを組み立て直す）・
  置きかえた特殊能力の使用の記録（`_turn_power_problems`）。ログの監査（tests/log_audit.py）は、退化の組み立て直し（重なり・手札・トラッシュ・特殊状態・持続する効果・退化した番）・
  `timing: trainer` のきぜつ・DV2・たいかビームの「とうめい」の判定のすぐあとの `devolve` を確かめます。退化・場のカードをはがす処理を加えたら、監査にも加えてください。
- エンジンが止める `UNRESOLVED_…` は 80 件、未解決の裁定は 81 件です（DV1〜DV5 は kyuura の未解決の一覧にない `not_in_kyuura`）。
- 検証用デッキ `M50`・`E50` と組（`PAIRINGS_V0_50`。`M50` 対 `E50`・`E50` 対 `M50`・`M50` 対 `P31`・`M50` 対 `D49`）は tools/existing_effect_games.py の `--batch v0.50` です
  （前の版の組の結果は変わらない）。たいかビームの選び方は `_v050_beam_decision`、退化スプレーは `_v050_trainer`・`_v050_decision`。DV5 は `V031_STOPS` で場から確かめ、
  tests/v017_games.py の `play_game` は DV2・DV3 を場から確かめてから別の操作を続けます。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## トラッシュのたねポケモンを持ち主のベンチに出す共通の処理と、ナツメのスリーパー・元気のかけら・ポケモンの笛（v0.51）

- 依頼の 3 枚（ナツメのスリーパー PMCG6-051 のよみがえらせる・ふりこののろい、トレーナーの元気のかけら PMCG1-078・ポケモンの笛 PMCG1-084）を、kyuura データの採用で、どのワザも、
  トレーナーも登録して加えました（対応ポケモン 325 → 326。写しの組 `pool_v0_51`。写し 350 → 353 枚。ワザの登録 553 → 555・特殊能力の登録 49・トレーナーの登録 16 → 18）。
  カードごとの結果・共通の処理・再利用した記録・未解決・技術的な制限・実装上の仮定・互換性・検証は docs/discard-to-bench-v0.51.md。ガイドブックは読んでいません。英語版の文面
  （「Basic Pokémon card」「(You can't play … if … Bench is full.)」）・のちの版の文面（ポケモンジム第1弾の元気のかけら）で、日本語版の条件を補わないでください。テストの定数は
  tests/helpers.py の `SABRINAS_HYPNO`・`REVIVE`・`POKEMON_FLUTE`・`V0_51_POKEMON`・`V0_51_CARDS`（`SABRINAS_HYPNO` と化石の秘密のスリーパー `HYPNO`、`SABRINAS_DROWZEE` と
  `DROWZEE` を取りちがえない）。v0.51 のワザの型は `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません。
- トラッシュのたねポケモンのカードを場に出すのは `zones.bench_from_discard(state, card, *, counters=0)` だけです（3 枚で共通）。同じ uid・同じ持ち主のまま、持ち主のトラッシュから
  持ち主のベンチの最後に出し、場のポケモンは手札・山札から出すときと同じ `zones.enter_play` で作ります（新しい場のポケモンの番号・場に出た番は今の番。その番には進化できない）。
  前に場にいたときのもの（ダメージ・特殊状態・ついていたカード・持続する効果・使用の記録・場のポケモンの番号）を引き継がない・カードを複製しない・手札を通さない・山札を切らない
  でください。カードの持ち主・置いていたトラッシュ・出すベンチはいつも同じプレイヤーで、効果を使ったプレイヤー・選んだプレイヤーとは別に扱います（ポケモンの笛は、使った
  プレイヤーが選び、相手のベンチに出る）。出してよいかの確認とログは呼ぶ側で、確認の漏れは `RuntimeError`（状態を変える前）。ほかのゾーンから場に出す効果を加えるときも、この関数か
  `enter_play` を通してください。
- 選べるカードは `effects.bench_from_discard_candidates(state, players)`（トラッシュにある間の定義がたねポケモンのカードのうち、持ち主のベンチに空きがあるもの。空きは持ち主の
  側で確かめる）だけで求めます。なにかの化石・ピッピ人形はトラッシュではトレーナーカード（v0.47）なので入りません。ベンチの上限は共通のルールの値（`rules.max_bench`）です。
- 「HPの半分(切り捨て)のダメージカウンター」は `effects.half_hp_counters`（HP をダメージカウンターの数で表して半分にし切り捨てる。GR-2000-P319-HP-AND-DAMAGE）。のせる
  カウンターはダメージではありません（GR-2000-P320-COUNTER-MOVE。`kernel.deal_damage` を通さない）。元気のかけらは出す前のカードの HP（「のせた状態でベンチに出す」。
  ログ `bench_from_discard` の `counters`・`damage`）、よみがえらせるは出したあとの今有効な最大HP（`max_hp`。「ベンチに出す。そして、…のせる」。ログ `place_damage_counters`）
  で数えます。今の対応カードでは同じ値です（tests がすべてのたねポケモンで確かめる）。ベンチに出しただけで最大HPが変わるたねポケモンを加えるときは、この違いを見直してください。
- よみがえらせるのカウンターは場のポケモンへのワザの効果なので、のせる前に「ワザをうけない」状態・「とうめい」を評価します（`reaches` の `damage_counters`。自分のポケモンにも）。
  出せるカードがなければ決定を出さずに何もしません（ログ `bench_from_discard_none`。GR-2000-P309-ATTACK-PROCEDURE）。元気のかけら・ポケモンの笛の「出せるカードがない」は
  RV1（`UNRESOLVED_REVIVE_WITHOUT_TARGET`）・FT1（`UNRESOLVED_POKEMON_FLUTE_WITHOUT_TARGET`）で、使う前（`check_playable`。トレーナーの使用の禁止 `TRAINER_PREVENTED` より後）に
  止めます。ワザとトレーナーの「対象なし」を一律に扱わないでください。RV1 と FT1 は別の問いで、ほかのカードの停止コード（PW3・DV4 など）を流用しないでください。元気のかけらの
  kyuura の再録の分類（「書き方だけ」）で RV1 を決めないでください（v0.21 の GW5 と同じ）。
- 元気のかけらの「トラッシュ」「ベンチ」は使ったプレイヤーのもの（RB10。実装上の読み方）。ポケモンの笛はカウンターをのせません。トレーナーの 0 枚は「ことができる」の、出さない
  こと（ログ `bench_from_discard_declined`）。よみがえらせるは 1 枚（省略できない）。2 枚のトレーナーは `may_knock_out` が偽で、v0.50 の `resolution.after_trainer` を呼びません
  （トレーナーのあとの処理を一律に当てはめない）。
- 場に出たときの特殊能力（v0.43 の `EntryPower`）を持つカードは、今の対応カードではどれも進化カードで、トラッシュから出す経路では起こりません。トラッシュから出したことを、
  手札から出したこと（ログ `play_to_bench`）として記録しないでください。「場に出た時」の特殊能力を持つたねポケモンを加えるときは、トラッシュから出す経路の使う機会を決めてから
  `effects.discard_entry_power_guard`（今は `RuntimeError`）を置きかえてください。
- ふりこののろい（`CoinsPerDefenderCountersDamage(20)`。値 `programs.HeadsPerDefenderCounters`）は、相手の対戦ポケモンのダメージカウンターの数だけコインを投げ、「おもて」の数 × 20 が
  p.321 の 1 段階です。v0.11 の「いかりのスーパーパンチ」（`HeadsOwnCounters`）・v0.32 の「じたばた」とは別の型です。0 個ならコインを投げず 0。先読みは「おもて」の数でまとめ
  （`by_heads`）、実際の対戦では 1 枚ずつ投げます。「ダメージを受けない」相手にカウンターがあれば v0.4b の `UNRESOLVED_PREVENTED_COIN_DAMAGE`。
- ［サイコリンク］・［へんしん］・相手のワザとして使うよみがえらせる・ふりこののろいは、v0.49・v0.31 の共通の処理のまま（必要なエネルギーを払う・まねたときは説明の条件）です。
- 書き出しの形式は 15 のまま（状態の項目を加えていない。監査の `LATEST_FORMAT` も 15。次の新しい形式は 16）。新しい決定の種類は `bench_from_discard`（観測の選べるものの意味は
  `card`）、新しいログのイベントは `bench_from_discard`・`bench_from_discard_declined`・`bench_from_discard_none`（どれも公開）。公開の API の呼び方・コマンドは変えていません。
  ログの監査（tests/log_audit.py）は、トラッシュから出したカードの組み立て直し（持ち主のトラッシュ → 持ち主のベンチ）・出どころ・新しい場のポケモンの番号・カウンター・
  場に出た番を確かめます。トラッシュ・場のあいだでカードを動かす効果を加えたら、監査にも加えてください。
- エンジンが止める `UNRESOLVED_…` は 82 件、未解決の裁定は 83 件です（RV1・FT1 は kyuura の未解決の一覧にない `not_in_kyuura`）。
- 検証用デッキ `H51`・`S51` と組（`PAIRINGS_V0_51`。`H51` 対 `E50`・`E50` 対 `H51`・`H51` 対 `P31`・`S51` 対 `H51`）は tools/existing_effect_games.py の `--batch v0.51` です
  （前の版の組の結果は変わらない）。よみがえらせるの選び方・トレーナーの 0 枚は `_v051_decision`、元気のかけら・ポケモンの笛は `_v051_trainer`（RV1・FT1 の場面では使わない）。
  出したポケモンのそのあとの行動は `card_uses` の `revived_then_…` で数えます。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 場のポケモンを場から手札・山札にもどす共通の処理と、フジろうじん・ポケモン回収・エリカのハクリュー（v0.52）

- 依頼の 3 枚（トレーナーのフジろうじん PMCG3-048・ポケモン回収 PMCG1-092、エリカのハクリュー PMCG5-066 のふぶき・つれさる）を、kyuura データの採用で、どのワザも、トレーナーも
  登録して加えました（対応ポケモン 326 → 327。写しの組 `pool_v0_52`。写し 353 → 356 枚。ワザの登録 555 → 557・特殊能力の登録 49・トレーナーの登録 18 → 20）。カードごとの結果・
  場をはなれるカードと行き先・場をはなれたあとの進行・再利用した記録・未解決・実装上の仮定・互換性・検証は docs/field-return-v0.52.md。ガイドブックは読んでいません。英語版の文面
  （「Shuffle it … into your deck」「return its Basic Pokémon card to your hand. (Discard all cards attached to that card.)」「Then, your opponent …」）で日本語版の条件を補わないで
  ください。テストの定数は tests/helpers.py の `MR_FUJI`・`SCOOP_UP`・`ERIKAS_DRAGONAIR`・`V0_52_POKEMON`・`V0_52_CARDS`（`ERIKAS_DRAGONAIR` と第1弾のハクリュー・わるいハクリューを
  取りちがえない）。v0.52 のワザの型 `ReturnBothActivesToDeck` は `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません。
- 場のポケモンが場をはなれるとき、どのカードも同じ uid・同じ持ち主のまま動かします（複製しない）。山札にもどすのは `zones.return_in_play_to_deck`（v0.36。v0.52 からトレーナーの
  出どころ `trainer`（ログの `trainer_card`）も渡せる。`effect` とどちらか一方）、ポケモン回収は新しい `zones.return_basic_to_hand`（重なりのいちばん下のカードだけを手札に、
  進化カード（「ばける」でのせたカードも進化カード）・エネルギーカードをトラッシュに。ダメージカウンターはなくなる。ログ `return_basic_to_hand`）です。v0.42 の
  `return_in_play_to_hand`（すべて手札へ）・v0.38 の `discard_attached_cards`（進化カードを動かさない）を、動かし方の違う効果に流用しないでください。持続する効果は呼ぶ側が消します
  （フジろうじん・つれさるは理由 `return_in_play_to_deck`、ポケモン回収は `return_in_play_to_hand`。GR-2000-P322-PERSISTENT-EFFECTS）。場をはなれたのはきぜつではありません
  （サイド・ログ `knock_out`・きぜつしたときの特殊能力はない。GR-2000-P312-FIELD）。場に出し直したポケモンは新しいポケモンです（新しい場のポケモンの番号・その番には進化できない）。
- 自分のバトル場のポケモンを場からはなれさせうるトレーナーは `TrainerEffect.empties_active = True` にします（今はポケモン回収だけ。カード id で分けない）。使い終えて（カードを
  トラッシュして）から `engine._finish_trainer` が `resolution.after_trainer` を呼び、きぜつがなくバトル場が空いたプレイヤーがいれば、勝ち負けの判定 → バトル場に出す決定
  （`promote_active`）→ 同じ番の `Phase.MAIN`（`CONTINUE_TURN`）に進みます（v0.42 の `after_power` と同じ形。v0.50 の `may_knock_out` のきぜつの処理は変えていない）。
  トレーナーの効果の途中でバトル場に出す決定を出さないでください（使用中のカードを残さない）。不変条件（`engine._power_aftermath_problems`）は、`empties_active` のトレーナーの
  あとに、バトル場のポケモンを手札にもどしたログ（`return_basic_to_hand` の `zone` が `active`）があることを確かめます。広げないでください。
- つれさる（要素 `programs.ReturnBothActivesToDeck`）は、自分 → 相手の順に、受けるか（「ワザをうけない」状態・「とうめい」。`reaches`）を評価して、受けるならもどして持続する効果を
  消し、そのあと、もどした側の山札を自分 → 相手の順に切ります（先読みでは切らない）。受けない側はもどさず、その山札も切りません。自分がもどったあとも相手の処理を続けます（ワザの
  処理を打ち切らない）。空いたバトル場は、ワザのあとの既存の勝ち負けの判定・バトル場に出す決定でうめます（両方空けば p.311 の表で判定。途中で勝者を決めない）。もどす順・切る順は
  実装上の判断で、英語版の「Then」を根拠にしないでください。相手に控えがいなくても使えます（つまみだすの条件を持ち込まない）。ログの監査は、1 回のワザで `return_in_play_to_deck`
  を 2 回まで（`returns_both_actives` の型だけ）許し、もどした順に同じワザの `shuffle` が続くことを確かめます。
- ふぶきは v0.38 のフリーザーと同じ型 `DamageThenCoinBenchDamageEitherSide`（1 枚のコイン。要素ごとに投げ直さない）で、型の `check` にエリカのハクリューの書き方（「コインを投げ、」・
  かっこのない「「弱点・抵抗力」に関係なく、」）を加えました。意味の違う書き方は受け付けません。
- 決められない場合（新しい停止コード。どれも `not_in_kyuura`）: FJ1（`UNRESOLVED_MR_FUJI_WITHOUT_BENCH`。自分に控えがいないときのフジろうじん。使う前）・SU1
  （`UNRESOLVED_SCOOP_UP_ATTACHED_TRAINER`。ポケモン回収で、トレーナーカードがついているポケモン。日本語の文面にトレーナーカードの行き先がない。選べるが選ぶと止める・どれもそうなら
  使う前）・SU2（`UNRESOLVED_SCOOP_UP_LAST_POKEMON`。控えがいないときのバトル場のポケモン。選べるが選ぶと止める。両方に当たれば SU1）。ほかのカードの「対象がない」ときの問い
  （GW5・TR1・RV1）・使うための条件を流用しないでください。ポケモン回収・フジろうじんでほかのポケモンの最大HPが下がる場面は v0.48 の MH1 のままです（新しいコードにしない）。
  エンジンが止める `UNRESOLVED_…` は 85 件、未解決の裁定は 86 件です。
- 書き出しの形式は 15 のまま（状態の項目を加えていない。監査の `LATEST_FORMAT` も 15。次の新しい形式は 16）。新しいログのイベントは `return_basic_to_hand`（公開）。新しい決定の
  種類・拒否のコード・公開の API の呼び方は変えていません。
- 検証用デッキ `R52` と組（`PAIRINGS_V0_52`。`R52` 対 `H51`・`H51` 対 `R52`・`R52` 対 `E50`・`R52` 対 `P31`）は tools/existing_effect_games.py の `--batch v0.52` です（前の版の組の
  結果は変わらない）。フジろうじん・ポケモン回収は `_v052_trainer`・`_v052_decision`（受け付ける答えだけを選ぶ。手札を隠した写しではなく本当の状態で確かめる `_V052_REAL`）、
  もどしたカードのそのあとの行動は `card_uses` の `returned_…` で数えます。D49（メタモン）は、エリカのミニリュウの［ふしぎなバリアー］を写す対戦準備で既存の TF1 に当たるので
  組にしていません（「ばける」・［へんしん］の場面は単体テスト）。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 山札・トラッシュからカードを選ぶトレーナー 10 枚（v0.53）

- 依頼の 10 枚（エネルギー転送 PMCG3-044・モンスターボール PMCG2-048・ボスのやりかた PMCG4-060・タケシの育て方 PMCG5-077・カスミのなみだ PMCG5-069・エリカのお付き PMCG5-072・
  メンテナンス PMCG1-085・ダウジングマシーン PMCG1-087・リサイクル PMCG3-047・夜の廃品回収 PMCG4-057）を、kyuura データの採用で登録しました（トレーナーの登録 20 → 30。写しの組
  `pool_v0_53`。写し 356 → 366 枚）。カードごとの結果・条件・選べるもの・見せるか・順番・未解決・実装上の読み方・互換性・検証は docs/search-retrieval-trainers-v0.53.md。ガイドブックは
  読んでいません。英語版の文面（「basic Energy」「Basic Pokémon or Evolution card」「in order to」「shuffle them into your deck」など）・ほかのカードの記録で、日本語版の条件を補わない
  でください。テストの定数は tests/helpers.py の `ENERGY_SEARCH`〜`NIGHTLY_GARBAGE_RUN`・`V0_53_CARDS`。
- 共通の処理は `effects.CardFilter`（選べるカードの種類。説明の言葉と 1 対 1 の決まった種類と名前の始まりだけ。汎用の条件の書き方にしない。カード id の一覧で決めない）・
  `SearchDeckTrainer`（山札をさがして手札に加える 6 枚。最大の枚数・選ばなくてよいか・見せるか・コイン・使うための条件）・`TakeFromDiscardTrainer`（トラッシュから手札 `TO_HAND`・
  山札の一番上 `TO_DECK_TOP`・山札 `TO_DECK` へ 3 枚）・`ReturnHandToDeckThenDraw`（メンテナンス）です。型の `check` が、登録の値と文面の言葉（見せ・てよい／ことができる・コイン・
  最大の枚数・使うための条件の文・行き先）を照らします。似たトレーナーを加えるときは、まずこれらの引数で表せるかを確かめ、カードごとの型を作らないでください。既存のパソコン通信・
  エネルギー回収・ポケモン交換おじさんの型は変えていません（動き・ログ・決定の形を保つため）。
- 選べるカードの種類は、その場所の印刷の定義（`GameState.card_def`）で決めます（山札・トラッシュのなにかの化石・ピッピ人形はトレーナーカード）。「わるいポケモンへの「進化カード」」
  は進化カード自身の名前（進化元が「わるい」だと仮定しない）、「「水」エネルギーカード」は「水」の基本エネルギーカード（ほかの色として使えるエネルギーを数えない）です。
- 見せる指示（「相手プレイヤーに見せてから」「選んだカードは相手に見せる」）があれば `reveal_deck_to_hand`（ログ `reveal_from_deck`。公開）、なければ `search_deck_to_hand`（ログ
  `search_deck`。カードは使ったプレイヤーだけ。エネルギー転送）。手札を見せずに山札にもどす（エリカのお付きの使うための条件・メンテナンス）のは `zones.return_hand_cards_to_deck`
  （v0.53 からトレーナーの出どころ `trainer`。ログ `hand_to_deck` の `trainer_card`）。トラッシュは公開の情報なので、トラッシュから動かしたカード（`retrieve_trainer`・
  `put_discard_on_deck_top`・`discard_to_deck`）は公開。選ばずに終わったログ `trainer_take_none` の理由（選べるカードがなかった・選ばなかった）は山札の中身の情報なので使ったプレイヤー
  だけが見ます。山札の選べるもの・手札のほかのカードをログに書かないでください。
- 「てよい」「ことができる」は選ばなくてよい（0 枚）と読み（v0.50・v0.51 と同じ）、選べるカードがないときも止めずに選ばずに終わり、山札をさがすものは山札を切ります（SR1）。
  選ばなくてよいと書かれていない 1 枚（エネルギー転送・ボスのやりかた・タケシの育て方・リサイクル）で選べるカードがない場面は ST1（`UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET`。
  使う前。リサイクルはコインの前）、夜の廃品回収の 0 枚・選べるカードがない場面は NG1（`UNRESOLVED_NIGHTLY_GARBAGE_RUN_ZERO_CHOICE`）、メンテナンスの手札が足りない場面は v0.44 の
  FC1（`UNRESOLVED_STATED_CARDS_SHORT`。印刷の文面に「使えない」がないので使うための条件にしない）です。パソコン通信の CS6・エネルギー回収の ER9・ER10・サカキの TR1・元気の
  かけらの RV1・ギガスパークの GS1 の答えを流用しないでください（どれも別のカードの問い）。カスミのなみだ・エリカのお付き（「使えない」と書かれている）・ダウジングマシーン
  （「すてることによって」。DM1）の手札が足りない場面は、使うための条件（`INSUFFICIENT_CARDS_IN_HAND`）です。
- 前の段階で動いたカードは次の段階の選べるものに入ります（エリカのお付きでもどしたカード・ダウジングマシーンですてたトレーナーカード（DM2。エネルギー回収のただし書きがない））。
  選べるものは条件のあとに求めてください。使っている最中のトレーナーはまだトラッシュにない（選べない）。不正な答えで、すんだ条件・コインを取り消さないでください。
- モンスターボール・リサイクルのコインは `flip_coins(..., source="trainer", effect=カード id, card=使っているカード)` で 1 枚だけ投げ（投げ直さない）、使うための確かめのあと・カードを
  見る前です。「うら」なら何もしない（モンスターボールは山札を切らない。MB1。v0.44 のおつかいと同じ読み方）。メンテナンスは もどす → 切る → 1 枚引く（切る前に引かない）。リサイクルは
  山札の一番上に置き、切りません。10 枚とも場を変えないので、`may_knock_out`・`empties_active` は偽（きぜつ・バトル場に出す処理をしない）。
- 夜の廃品回収の kyuura の種類 `rockets_secret_machine`（ロケット団秘密メカ）は、この種類だけのときに受け付けます（`TakeFromDiscardTrainer.secret_machine_ok`。規定の記録にこの種類を
  区別する規定がなく、参照するカードもない。RS1）。この種類を参照するカードを加えるときは見直してください。ほかの種類のトレーナーは今までどおり拒否します。
- 書き出しの形式は 15 のまま（状態の項目を加えていない。次の新しい形式は 16）。新しい決定の種類は `discard_to_deck`（観測の意味は `card`）、新しいログのイベントは `retrieve_trainer`・
  `discard_to_deck`（公開）・`trainer_take_none`（`reason` は使ったプレイヤーだけ）。`coin_flip` の `source` に `"trainer"`。公開の API の呼び方は変えていません。ログの監査
  （tests/log_audit.py）は、これらの組み立て直しと、トレーナー 1 回ぶんのイベントの並び（`search_retrieval_problems`）を確かめます。山札・トラッシュのカードを動かすトレーナーを
  加えたら、監査にも加えてください。エンジンが止める `UNRESOLVED_…` は 87 件、未解決の裁定は 88 件です（ST1・NG1 は kyuura の未解決の一覧にない `not_in_kyuura`）。
- 検証用デッキ `S53`・`R53` と組（`PAIRINGS_V0_53`。`S53` 対 `R53`・`S53` 対 `P31`・`R53` 対 `H51`・`R53` 対 `K44`）は tools/existing_effect_games.py の `--batch v0.53` です
  （前の版の組の結果は変わらない）。トレーナーは `_v053_trainer`（受け付けるときだけ使う。止まる場面はコードごとに数える）、決定は `_v053_decision`。選んだカードのそのあとの使い道は
  `card_uses` の `taken_then_…`。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 手札の入れ替え・ドロー・情報の確認のトレーナー 10 枚（v0.54）

- 依頼の 10 枚（にせオーキドはかせ PMCG1-089・にせオーキドの逆襲 PMCG4-059・ギャンブラー PMCG3-045・ナツメの眼 PMCG6-078・カツラの奥の手 PMCG6-081・エリカ PMCG5-083・
  スパイ作戦 PMCG5-088・カツラのギャンブル PMCG6-076・ミニスカート PMCG1-095・ポケモン図鑑 HANDY505 PMCG1-082）を、kyuura データの採用で登録しました（トレーナーの登録 30 → 40。写しの組
  `pool_v0_54`。写し 366 → 376 枚）。カードごとの結果・条件・順番・枚数・見せるか・未解決・実装上の読み方・互換性・検証は docs/hand-deck-trainers-v0.54.md。ガイドブックは読んでいません。
  英語版の文面（カツラの奥の手の「Show your hand」など）・2002 年の「サポーター適用カード」（kyuura MIX-SUPPORTER-ERRATA）・現代のサポーターの規定で、日本語版の条件を補わないで
  ください。テストの定数は tests/helpers.py の `IMPOSTER_OAK`〜`POKEDEX`・`V0_54_CARDS`。
- 共通の処理は `effects.ReturnHandsToDeckTrainer`（もどすプレイヤー `HANDS_OPPONENT`・`HANDS_SELF`・`HANDS_BOTH`・もどすカード `"all"`・`"trainers"`・見せ合うか・引く枚数の決め方
  （決まった数 `draw`・もどした枚数 `draw_returned`・コイン `coin_draws` のちょうど 1 つ）・使うための条件 `discard_cost`）・`DrawIfOnlyNamedInHand`・`EachPlayerMayDraw`・
  `DiscardFromHandThenDrawTrainer`（相手の手札を見るか・「のぞむなら」か・コイン・倍数）・`ArrangeOwnDeckTopTrainer` です。型の `check` が登録の値と文面の言葉を照らします。似た
  トレーナーを加えるときは、まずこれらの引数で表せるかを確かめ、カードごとの型・汎用の条件の書き方を作らないでください。
- 両方のプレイヤーの処理（見せる・もどす・切る・引く）は、使ったプレイヤー → 相手の順（実装上の順番。HD1）。もどすカードが 0 枚でも、もどすプレイヤーの山札は切る（HD2）。
  もどす枚数（ナツメの眼）はプレイヤーごとに数え、使っているこのカード（`trainer_in_use`）は数えない。効果で引く枚数は、山札が足りなければ引けるだけ（p.312。`_draw_up_to`）。
- 相手の手札をもどさせる・相手に引かせる（にせオーキドはかせ・逆襲）のに相手の決定はありません。エリカの相手の枚数は相手自身が決め（決定 `select_draw_count`、`context` の
  `"stage"` が 1）、それを許すのはエリカの `decision_problems` だけです（ほかのトレーナーの「決めるのは使ったプレイヤー」の約束を緩めない）。
- 見る・見せるのは 1 回だけです: スパイ作戦は `zones.look_at_hand`（ログ `look_at_hand` の `cards` は見たプレイヤーと持ち主だけ）、ミニスカートは `zones.reveal_hand`・
  `return_revealed_hand_cards_to_deck`（公開）。観測の手札の見え方（`hand_visible_to`・［おみとおし］）を変えないでください（あとで手札に加わったカードを公開しない）。ポケモン図鑑は
  みらいよちと同じ決定 `select_look_count`・`arrange_deck_top` とログ（出どころは `trainer_card`）で、自分の山札だけ・手札に加えない・切らない。0 枚は「ことができる」の見ないこと
  （`look_at_deck_top_declined`。GS1 を当てはめない）。
- ミニスカートのトレーナーカードは、手札にある間の印刷の分類（`CardFilter("trainer")`。`category`）で、なにかの化石・ピッピ人形・種類（`trainer_kinds`）のあるトレーナーも含みます。
  v0.53 の `secret_machine_ok` は夜の廃品回収自身の登録の印で、選べるカードの種類とは別です（v0.53 の節の「ほかの種類のトレーナーは今までどおり拒否します」は、ほかの種類の
  トレーナーを登録しないという意味。選べるカード・もどすカードから種類で除く意味ではない）。
- 使うための条件: にせオーキドの逆襲は v0.53 の `_hand_cost_problem`（`INSUFFICIENT_CARDS_IN_HAND`）、カツラの奥の手は `OTHER_CARDS_IN_HAND`（名前の完全一致。同じ名前のカードは
  よい。手札を見せない）。カツラのギャンブルの「好きなだけ」（「のぞむなら」がない）の 0 枚は v0.31 の HC5（`UNRESOLVED_DISCARD_ANY_NUMBER_ZERO`。0 枚の答え・手札がこのカードだけの
  とき）で、スパイ作戦（「のぞむなら」がある）の 0 枚は受け付けます。似た言い回しのカードの問いを自動で当てはめないでください。
- 状態の項目・書き出しの形式（15）・公開の API の呼び方は変えていません。新しい決定の種類は `select_draw_count`、新しいログのイベントは `reveal_hand`・`revealed_hand_to_deck`・
  `look_at_hand`・`trainer_draw_declined`・`trainer_discard_declined`・`look_at_deck_top_declined`、新しい拒否のコードは `OTHER_CARDS_IN_HAND`。新しい停止コード・未解決の裁定は
  ありません（87 件・88 件のまま）。ログの監査（tests/log_audit.py の `hand_deck_problems`）は、トレーナー 1 回ぶんのイベントの並び・引いた枚数の上限・プレイヤーの順番と、
  見せた・見た手札の組み立て直しを確かめます。手札・山札を動かす・見るトレーナーを加えたら、監査にも加えてください。
- 検証用デッキ `H54`・`D54` と組（`PAIRINGS_V0_54`。`H54` 対 `D54`・`D54` 対 `H54`・`H54` 対 `R53`・`D54` 対 `P31`）は tools/existing_effect_games.py の `--batch v0.54` です
  （前の版の組の結果は変わらない）。トレーナーは `_v054_trainer`（受け付けるときだけ使う）、決定は `_v054_decision`（相手の決定にも答える）。`D54` のなにかの化石で、対戦準備が既知の
  PF1 で止まる局があります。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## すぐに使い終わるトレーナー 16 枚（v0.55）

- 依頼の 16 枚（カスミのいかり PMCG5-075・ロケット団のおねーさん PMCG4-061・礼儀作法 PMCG5-082・トラッシュ交換 PMCG6-077・エネルギー・リムーブ PMCG1-070・超エネルギーリムーブ
  PMCG1-088・いいきずぐすり PMCG1-075・なんでもなおし PMCG1-080・ポケモンセンター PMCG1-083・ねむれ!ねむれ! PMCG4-054・エネルギーサーキュレート PMCG5-067・エリカの親切 PMCG5-084・
  タケシ PMCG5-089・サカキの切り札 PMCG6-096・ナツメ PMCG6-098・ワープポイント PMCG6-080）を、kyuura データの採用で登録しました（トレーナーの登録 40 → 56。写しの組 `pool_v0_55`。
  写し 376 → 391 枚）。カードごとの結果・条件・対象・順番・枚数・見せるか・未解決・実装上の読み方・互換性・検証は docs/instant-trainers-v0.55.md。ガイドブックは読んでいません。
  英語版の文面（「Your Active Pokémon」「up to 2」「in order to」など）・のちのルール・kyuura の MIX-ENERGY-REMOVAL・MIX-SUPER-ENERGY-REMOVAL（2000.02.14 版のあとの再録・大会の記録）・
  2002 年のサポーターの規定で、日本語版の条件を補わないでください。テストの定数は tests/helpers.py の `MISTYS_WRATH`〜`WARP_POINT`・`V0_55_CARDS`（トレーナーの `BROCK_TRAINER`・
  `SABRINA_TRAINER` を、「タケシの」「ナツメの」ポケモン・ナツメの眼と取りちがえない）。
- いいきずぐすりは v0.54 まで「実装を登録していないトレーナー」の参照カードでした。その性質を確かめるテストは、登録だけを除いた登録表（tests/helpers.py の `NO_SUPER_POTION_EFFECTS`・
  `no_super_potion_pool`）を使います。参照カード（`REFERENCE_ONLY`）は キョウのベトベトン PMCG6-023 だけです（v0.68 で対応にし、`REFERENCE_ONLY` は空になった）。
- 意味ごとの共通の型: `effects.DiscardAttachedEnergyTrainer(text, opponent_cards, own_cost)`（エネルギー・リムーブ・超エネルギーリムーブ）・`HealEachDamagedPokemonTrainer(text, who,
  counters, discard_energy)`（ポケモンセンター・エリカの親切・タケシ。`HEAL_SELF`・`HEAL_BOTH`）。ほかは 1 枚ずつの型（`LookTopTakeRestDiscardTrainer`・`OpponentHandTrainerToDeck`・
  `DiscardPileExchange`・`DiscardEnergyThenHealTrainer`・`CureSpecialConditionsTrainer`・`CoinStatusOnOpponentActiveTrainer`・`ReturnBasicEnergyToHandTrainer`・
  `HealOwnerPokemonThenDiscardHand`・`MoveAllEnergyBetweenOwnerPokemon`・`SwitchBothActivesTrainer`）。礼儀作法は v0.53 の `SearchDeckTrainer` に `no_basic_in_hand`（使うための条件
  `BASIC_POKEMON_IN_HAND`）・`reveal_hand`（さがす前に手札を見せる）と `CardFilter("basic_pokemon")` を加えたものです。似たトレーナーを加えるときは、まずこれらの引数で表せるかを
  確かめ、汎用の条件の書き方・カード id の分岐を作らないでください。型の `check` が文面の言葉と登録の値を照らします。
- 場のエネルギーカードを動かすのは `zones.discard_attached_energy_cards`（持ち主のトラッシュ。ログ `trainer_discard_energy` の `player` は持ち主・`user` は使ったプレイヤー）・
  `return_attached_energy_to_hand`（`trainer_return_energy`）・`move_attached_energy`（はがしたカードすべてを 1 回でつけなおす。`trainer_move_energy`。つけたあとカードごとに
  `effects.after_energy_attached`）だけです。手札からつける通常の操作の回数・特殊能力でつけた枚数は変えません。ほかのゾーンの関数は `take_looked_deck_cards`（`looked_to_hand` は
  使ったプレイヤーだけ・`looked_to_discard` は公開）・`opponent_hand_card_to_deck`（`opponent_hand_to_deck` の `card` は持ち主と見たプレイヤーだけ）・`discard_pile_to_deck`・
  `deck_top_to_discard`（公開）。どれも同じ uid・同じ持ち主のまま動かします。
- 選ぶのはワープポイントの段階 0 を除き使ったプレイヤーです（相手のポケモン・手札・エネルギーカードも）。ワープポイントは相手プレイヤーが先に自分の控えを選び（その決定を許すのは
  このカードの `decision_problems` だけ）、控えがいないプレイヤーは入れ替えません（`trainer_switch_skipped`。どちらにも控えがいなくても使える）。トレーナーの効果なので「ワザを
  うけない」状態・「とうめい」は当てはめません。エリカの親切は使ったプレイヤー → 相手の順（EK1）。
- 使うための条件（「…ことによって」「…時だけ、使える」）は手札から出す前の `IllegalActionError`（超エネルギーリムーブ・いいきずぐすりの `NO_ENERGY_TO_DISCARD`、礼儀作法の
  `BASIC_POKEMON_IN_HAND`）。条件のエネルギーカードのトラッシュは、そのあとの段階の不正な答え・止める答えで取り消しません。
- 決められない場合（新しい停止コード 8 件。どれも `not_in_kyuura`）: MW1（`UNRESOLVED_MISTYS_WRATH_SHORT_DECK`。山札 7 枚未満。「引けるだけ」を見る処理に当てはめない）・EM1
  （`UNRESOLVED_ENERGY_REMOVAL_WITHOUT_TARGET`）・SP1（`UNRESOLVED_SUPER_POTION_UNDAMAGED_TARGET`）・FH1（`UNRESOLVED_FULL_HEAL_SCOPE`。特殊状態のポケモンが自分の対戦ポケモン
  だけなら回復し、ほかは使う前に止める）・GL1（`UNRESOLVED_LAST_RESORT_WITHOUT_TARGET`）・GL2（`UNRESOLVED_LAST_RESORT_UNDAMAGED_TARGET`）・SB1
  （`UNRESOLVED_SABRINA_WITHOUT_TWO_POKEMON`）・SB2（`UNRESOLVED_SABRINA_SOURCE_WITHOUT_ENERGY`）。対象を選ぶ問い（SP1・GL2・SB2）は選べるが選ぶと止め、どれもそうなら使う前に
  止めます。既存の問い: 超エネルギーリムーブの 2 枚より少ないポケモンは v0.44 の FC1（のちの版の「2 枚まで」を持ち込まない）、ワープポイントの「すごむ」は v0.40 の SG1（使った
  プレイヤーに控えがいないときだけ。WP1）、最大HPが下がる答え（いいきずぐすり・エネルギーサーキュレート・ナツメ・ワープポイント）はエンジンの共通の MH1（カードごとの確かめ・途中の
  状態の確かめを加えない）。ほかのカードの「対象がない」ときの問いの答えを流用しないでください。エンジンが止める `UNRESOLVED_…` は 95 件、未解決の裁定は 96 件です。
- 「全員から」の効果（ポケモンセンター・エリカの親切・タケシ）は、ダメージカウンターのあるポケモンがいなければ何も起こらずに使い終わります（HE1。選ばせる効果の「対象がない」とは
  別）。いいきずぐすりのとりのぞく数は 0〜min(4, のっている数)（決定 `select_counter_count`）。ねむれ!ねむれ!は「おもて」で特殊状態にしたあとの状態が受け付けられないなら、コインの
  前に止めます（`state_stop_after`）。ロケット団のおねーさんはトレーナーカードがなければ切りません（RS1）。
- ロケット団秘密メカの種類（`rockets_secret_machine`）だけを持つトレーナーの受け付けは、夜の廃品回収（v0.53）とねむれ!ねむれ!で共通の `effects.secret_machine_ok` です。ほかの種類の
  トレーナーを一律に受け付けないでください（この種類を参照するカードを加えるときに見直す）。
- 状態の項目・書き出しの形式（15）・公開の API の呼び方は変えていません（次の新しい形式は 16）。新しい決定の種類は `take_looked_cards`・`opponent_hand_to_deck`（観測の
  `LOOKED_HAND_KINDS`。決めるプレイヤーに見た相手の手札が見える）・`select_counter_count`、新しいログのイベントは `trainer_discard_energy`・`trainer_return_energy`・
  `trainer_move_energy`・`trainer_switch_skipped`・`discard_pile_to_deck`・`deck_top_to_discard`・`looked_to_discard`（公開）・`looked_to_hand`・`opponent_hand_to_deck`（非公開の
  項目あり）、`special_conditions_removed` の理由 `cured`。ログの監査（tests/log_audit.py の `instant_trainer_problems`）は、トレーナー 1 回ぶんのイベントの並び・動かしたカードの
  数・側・出どころと、新しいイベントの組み立て直しを確かめます。場・手札・山札・トラッシュのカードを動かすトレーナーを加えたら、監査にも加えてください。
- 検証用デッキ `G55`・`U55` と組（`PAIRINGS_V0_55`。`G55` 対 `U55`・`U55` 対 `G55`・`G55` 対 `S48`・`U55` 対 `H54`）は tools/existing_effect_games.py の `--batch v0.55` です
  （前の版の組の結果は変わらない）。トレーナーは `_v055_trainer`（受け付けるときだけ使う）、決定は `_v055_decision`（相手の決定にも答える）。なんでもなおしは対戦の場面ではいつも
  FH1 で、回復は単体テストで確かめます。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 相手の決定・番の終わり・期限のある効果のトレーナー 10 枚（v0.56）

- 依頼の 10 枚（エリカの香水 PMCG5-073・マチス PMCG5-092・ロケット団のワナ PMCG5-096・ロケット団員 PMCG6-089・マチスの交渉 PMCG5-081・カスミのわがまま PMCG5-086・カスミ PMCG5-085・
  キョウ PMCG6-094・見えない壁 PMCG6-079・ロケット団の実験 PMCG6-091）を、kyuura データの採用で登録しました（トレーナーの登録 56 → 66。写しの組 `pool_v0_56`。写し 391 → 401 枚）。
  カードごとの結果・共通の進行・順番・未解決・実装上の読み方・互換性・検証は docs/trainer-decisions-turn-effects-v0.56.md。ガイドブックは読んでいません。英語版の文面・現代のルール・
  2002 年のサポーターの規定で、日本語版の条件を補わないでください。テストの定数は tests/helpers.py の `ERIKAS_PERFUME`〜`ROCKETS_EXPERIMENT`・`V0_56_CARDS`（トレーナーの
  `LT_SURGE_TRAINER`・`MISTY_TRAINER`・`KOGA_TRAINER` を、「マチスの」「カスミの」「キョウの」ポケモン・マチスの交渉・カスミのわがままと取りちがえない）。
- 共通の進行は 10 枚に要るものだけです（汎用の効果の書き方・カード id の分岐を作らない）: 相手プレイヤーに答えさせる決定 `accept_request`（決めるのは相手。それを許すのは
  そのカードの `decision_problems` だけ。答えはログ `request_answered`）、手札のたねポケモンを場に出す `zones.hand_to_bench_by_effect`（持ち主のベンチ）・`hand_basic_to_active`
  （どちらも `zones.enter_play` で新しい場のポケモンを作る）、使用中のカードをトラッシュしてから番を終える（`TrainerEffect.may_end_turn` の実装の `resolve`・`resume` が
  `effects.END_TURN` を返したら、`engine._finish_trainer` がトラッシュしてから `resolution.end_turn_after_trainer`。効果の中で番を終えない）、きぜつによらずサイドを取る
  （`zones.take_prize_by_trainer`。ログ `knock_out`・`take_prize` を作らない。`TrainerEffect.takes_prizes` の実装は、使い終えてから `resolution.after_trainer` が p.311 の表で
  判定する。効果の途中で対戦を終えない）、期限のある効果（下）。トレーナーの処理が使う解決の基盤の名前は `Context`・`after_trainer`・`end_turn_after_trainer` だけです
  （tests/test_kernel_integration_v0_15.py の `DependencyTest`）。
- 場に出たときに使える特殊能力（v0.43 の `EntryPower`）を持つたねポケモンは写しにない（どれも進化カード）ので、エリカの香水・マチスで場に出すカードは
  `effects.placed_entry_power_guard` が状態を変える前に `RuntimeError` で止めます（エンジンの制限）。そのようなたねポケモンを加えるときは、相手の効果で「出させ」られたときに
  「手札から出した時」の機会があるかを決めてから、トレーナーの途中で特殊能力の決定を出して残りにもどる処理に置きかえてください。
- 期限のある効果（カスミ・キョウ・見えない壁）は、場のポケモンに写さず、使ったプレイヤーの記録 `GameState.trainer_effects`（`state.TrainerTurnEffect`。種類 `ATTACK_DAMAGE_BONUS`・
  `POISON_ON_ATTACK_DAMAGE`・`BENCH_ATTACK_DAMAGE_PREVENTION`・与えた番・消える番）に持ち、はたらく時点の場で問い合わせます（`effects.trainer_turn_effects`・
  `trainer_attack_damage_bonuses`・`trainer_poison_effects`・`bench_damage_preventions`）。消える番の終わりに `procedures.expire_at_turn_end` が消します（ログ `trainer_effect_added`・
  `trainer_effect_removed`）。登録の値は `TrainerEffect.turn_effect_terms()` で、不変条件 `engine._trainer_effect_problems` が照らします。「はたらいている」の印を場のポケモンに
  付けないでください（入れ替え・進化・場をはなれることでは消えない。使ったときの場で決めない）。
- カスミの + 20 は p.321 の 6 段階（kyuura の GR-2000-P321-DAMAGE-ORDER の「それ以外の効果」）で、`effects.attack_damage_modifiers` が相手の対戦ポケモンへのダメージにだけ加えます
  （控えへのダメージ・自分へのダメージに加えない。「カスミのポケモン」はダメージの時点の今の姿の名前）。最終ダメージに直接足さないでください。自分にもダメージを与えるワザで、
  当てはめるかで結果が変わるときは MS1（`UNRESOLVED_MISTY_SELF_DAMAGE`。宣言の前）。キョウのどくは、ダメージをのせたあと（`kernel.deal_damage`。最終ダメージが 0 より大きい相手の
  対戦ポケモンだけ）に `conditions.poison` で与えます（どくは 1 つ。受けたポケモンが HP 以上なら飛ばし、こんじょうを使えるなら G37）。同じワザの受けるダメージの違う特殊などくとの
  順番は KG1（`UNRESOLVED_KOGA_POISON_ORDER`）。見えない壁は解決の基盤の効果の定義 `catalog.INVISIBLE_WALL`（`Origin.TRAINER_EFFECT`・VOID・`BEFORE_DAMAGE` だけ）で、受ける時点の
  持ち主の控えへのワザのダメージの要素を無効にします（特殊状態・かがくへんかガスで消えない。特殊能力のダメージ・カウンターの移動には当てはめない）。コインが決めるのが控えへの
  ダメージだけで、その控えがどれも無効なら v0.4b の `UNRESOLVED_PREVENTED_COIN_DAMAGE`（要素の `coin_receiver` が `"bench"`・`BenchDamage.void_for_all`）。新しいコードにしない。
- ロケット団の実験の「うら」は v0.47 の `TrainerUseLock` を `origin="trainer"`（使ったプレイヤー自身・消える番は使った番 + 2 = `SELF_TRAINER_LOCK_TURNS`。`add_self_trainer_lock`）で
  使います。ワザの禁止（`origin="attack"`）とは別の記録で、同じ消える番に重なってもそれぞれの記録が消えます（ワザの禁止を与える要素は、同じ出どころの禁止だけを「すでにある」と
  比べる）。不変条件 `engine._trainer_lock_problems` は出どころごとの期間と登録の `tails_self_lock` を照らします。
- 決められない場合（新しい停止コード 6 件。どれも `not_in_kyuura`）: LS1（`UNRESOLVED_LT_SURGE_WITHOUT_BASIC`。マチスで手札にたねポケモンがない）・RT1
  （`UNRESOLVED_ROCKETS_TRAP_ZERO_CHOICE`。ワナの 0 個の答え・相手の手札 0 枚（コインの前））・RG1（`UNRESOLVED_ROCKET_GRUNT_WITHOUT_BENCH`。相手に控えがいない（コインの前））・
  MY1（`UNRESOLVED_MISTYS_WISH_WITHOUT_HAND`）・MS1・KG1。再利用: ロケット団の実験の山札 0 枚は v0.53 の ST1、最大HPの低下は MH1（範囲を広げない）。ほかのカードの「対象がない」
  ときの問い（NG1・GS1・ER9・GW5 など）の答えを流用しないでください。エンジンが止める `UNRESOLVED_…` は 101 件、未解決の裁定は 102 件です。
- 見えない情報: ロケット団のワナの決定の選べるものは相手の手札の位置（`select_hand_positions`。カードの uid を入れない。観測の意味は `position`）、もどしたカードは持ち主だけ
  （ログ `hand_positions_to_deck`）。カスミのわがままで見たサイドは見たプレイヤーだけ（`look_at_card`）で、続きの情報（決定の `context`）には位置だけを書きます。マチスの交渉で取った
  サイド（`trainer_take_prize`）・わがままで入れかえたカード（`swap_prize_with_hand`）は持ち主だけ。エリカの香水は見た手札から選ぶ決定（`LOOKED_HAND_KINDS`）で、観測の手札は公開しません。
- 書き出しの形式 16 = 形式 15 + 最上位の `trainer_effects` とトレーナーの使用の禁止の `origin`（形式 1〜15 は、期限のある効果・出どころが `trainer` の禁止があると `ValueError`）。
  監査の `LATEST_FORMAT` は 16（v0.57 で 17）。次の新しい形式は 17（v0.57 で加えた。その次は 18）。新しい決定の種類は `accept_request`・`opponent_hand_to_bench`・`select_hand_positions`・`hand_to_active`・`swap_with_prize`、
  新しいログのイベントは `trainer_bench_from_hand`・`trainer_hand_to_active`・`request_answered`・`trainer_effect_added`・`trainer_effect_removed`・`trainer_turn_end`（公開）・
  `hand_positions_to_deck`・`trainer_take_prize`・`swap_prize_with_hand`（非公開の項目あり）。公開の API の呼び方は変えていません。ログの監査（tests/log_audit.py）は、これらの
  組み立て直しと、トレーナーで取ったサイドの数・期限のある効果の期限・出どころがトレーナーの禁止・トレーナーによる番の終わりを確かめます。
- tools/existing_effect_games.py の `run` は、同じデッキの組が席を入れかえて 2 回ある組の一覧で同じ局（デッキの中身・席・seed）を 2 回行わない（`duplicates` に数える。`main` は
  予定 `planned` と行った局数 `distinct` を出す）。組の一覧に、席を入れかえただけの組を加えないでください（`run` が席を入れかえる）。
- 検証用デッキ `M56`・`K56` と組（`PAIRINGS_V0_56`。`M56` 対 `K56`・`K56` 対 `P31`・`M56` 対 `G55`・`K56` 対 `U55`）は tools/existing_effect_games.py の `--batch v0.56` です
  （前の版の組の結果は変わらない）。トレーナーは `_v056_trainer`（受け付けるときだけ使う。マチスは手順がたねポケモンをベンチに出す前に試す）、決定は `_v056_decision`（相手の
  たずねる決定にも答え、オーケー・オーケーでないを交互に）。MS1・KG1 は `V031_STOPS` で場から確かめます。なんでもなおしは、キョウのどくを受けた自分の対戦ポケモンだけの場面で
  回復します（v0.55 の持ち越し）。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## スタジアム 14 枚と、その共通の処理（v0.57）

- 依頼の 14 枚（ニビシティジム PMCG5-079・ハナダシティジム PMCG5-080・抵抗力低下ジム PMCG5-091・ロケット団の特訓ジム PMCG5-095・グレンタウンジム PMCG6-085・タマムシシティジム PMCG5-078・
  セキチクシティジム PMCG6-086・ヤマブキシティジム PMCG6-090・せまいジム PMCG5-070・ロケット団の爆発ジム PMCG6-092・トキワシティジム PMCG6-097・クチバシティジム PMCG5-076・
  リムーブ禁止ジム PMCG5-094・錯乱ジム PMCG5-087）を、kyuura データの採用で登録しました（トレーナーの登録 66 → 80。写しの組 `pool_v0_57`。写し 401 → 415 枚）。カードごとの結果・共通の
  処理・未解決・実装上の判断・互換性・検証は docs/stadiums-v0.57.md。ガイドブックは読んでいません。英語版の文面（「your opponent returns a Pokémon first」「(or 1 if it only has 1)」
  「put damage counters」など）・現代のルール・後年の規定で、日本語版の条件を補わないでください。テストの定数は tests/helpers.py の `PEWTER_CITY_GYM`〜`CHAOS_GYM`・`V0_57_CARDS`。
- スタジアムの一般の規定は kyuura の rule_differences の「stadium」の 2000.02.14 版の行と GR-2000-P312-FIELD（境界線上に出し、両方の場に出ているカード。場に 1 枚。新しいスタジアムが
  場に出たら古いものを持ち主のトラッシュに）です。2003 年の `MIX-ADV-RULES-2003`（1 番に 1 枚）を使わないでください（1 番に出せる枚数・同じ名前のスタジアムを制限しない）。
- 場のスタジアムは `GameState.stadium`（`state.StadiumInPlay(owner, card, placed_turn)`。実際のカード 1 枚）だけに持ち、効果は問い合わせのたびに、効果の登録表のそのカードの実装
  （`effects.StadiumEffect` の部分型）から求めます（`stadiums.stadium_in_play`・`effects.stadium_of`。型で探す）。効果の結果を状態・カードの定義・共有するルールの値（`RuleSet`）に
  写したり、カード id で分けたりしないでください（`engine.py`・`resolution/` にカード id の分岐はない）。かがくへんかガス・特殊状態ではスタジアムの効果は消えません。
- 手札から出すのはトレーナーカードを使うこと（禁止で止まる。`engine._play_stadium`・`zones.place_stadium`。ログ `stadium_placed`・`stadium_discarded`）で、トラッシュせず場に出します。
  錯乱ジムのコインはスタジアムカードには投げません。型の `check` は、置き方の文の 3 通りの書き方（`STADIUM_REPLACEMENT_TEXTS`）を確かめます。
- 自分の番に使う効果（タマムシ・セキチク・ヤマブキ）は新しいコマンド `UseStadium(player, energy=None)`（`engine._use_stadium`。ログ `stadium_used`）で、決定は再開先 `"stadium"`
  （`engine._resume_stadium`。段階 `narrow`・`fuchsia`・`evolution_heal`）、終わったら `resolution.after_stadium`（空いたバトル場の勝ち負け・交代 → 同じ番の `MAIN`。v0.42 の
  `after_power` と同じ形）です。「自分の番ごとに1回」の記録は `GameState.stadium_uses_this_turn`（(使ったプレイヤー, スタジアムカード)。ログから数えない）。トレーナーを手札から使うこと・
  特殊能力の使用ではありません。スタジアムの処理が使う解決の基盤の名前は `Context`・`after_stadium` だけです（tests/test_kernel_integration_v0_15.py の `DependencyTest`）。
- ベンチの数の上限は `stadiums.bench_limit`・`bench_has_room`（せまいジムの 4 匹）だけで求めます。ベンチに出すどの経路（手札・山札・トラッシュから・効果で出させる・ポケモンとして出す
  トレーナー）も、道具・テストの手順も、`rules.max_bench`・5 を直接読まないでください。せまいジムが場に出た時の手札にもどす決定（`STADIUM_RETURN_BENCH`。決めるのはベンチの持ち主。
  両方が 5 匹なら番でないプレイヤーが先。実装上の順番）を待つ間だけ、上限より多いベンチを不変条件が許します（`engine._narrow_cleanup_pending`。広げない）。
- ダメージの計算は `damage.calculate_with_stadium`・`effects.stadium_damage_options`（ニビの 4 段階・グレンの 3 段階を計算しない、抵抗力低下ジムの抵抗力の数（`resistance_of`）、
  クチバの 6 段階の + 10）で、`kernel.deal_damage` と `preview_attack_damage` が同じ関数を使います。最終ダメージに直接足さないでください。にげるの数は `effects.retreat_cost` の
  `stadium_increases`・`stadium_reductions`（決まって変える。選べない）で、特殊能力の増減と下限 0 の当てはめ方で答えが変わる数は v0.46 の CP2 です（新しいコードにしない）。
- 反応は決まった処理の入口から問い合わせます: 爆発ジム（手札のたねポケモンをベンチに出す時。持ち主のコイン。「うら」なら 20 ダメージ。ワザ・特殊能力のダメージではない。EX1）、
  トキワシティジム（進化させるすべての経路で、進化の手順のあと・場に出たときの特殊能力の機会の前に `effects.offer_evolution_heal`。決定 `EVOLUTION_HEAL`。続きの情報の `after_heal`
  （汎用の `then` は番の続きの値なので使わない）。VG1。H1 はとりのぞく前）、クチバシティジム（`UseAttack.stadium_coin`。宣言のあと・ワザの要素の前に `flow._stadium_attack_coin`。
  結果は続きの情報の `stadium_coin` で運び、投げ直さない。「うら」は `programs.with_stadium_self_damage`。VM1。v0.13 の約束の実装は `UNSUPPORTED_ATTACK`、`legacy` の先読みは使わない）、
  リムーブ禁止ジム（名前を「・」を除いて比べる。追加の 2 枚は手札から出したあと・効果の前。続きの情報の `stadium_cost`）、錯乱ジム（次の項）。
- 錯乱ジム: コインは手札から出したあと（p.310 の手順 1・2）・使うための条件を払う前（ログ `chaos_check`）。「うら」なら使ったプレイヤーは使えず、相手プレイヤーが使えるか
  （`stays_in_play`・`enters_play` のカードは使えない。条件を相手として満たせない・禁止なら使えない）を確かめ、決定 `ACCEPT_REQUEST`（決めるのは相手。続きの情報の `chaos`）で聞きます。
  使うなら `TrainerInUse.user` に記録し、トレーナーの処理は `using_player` で「あなた」を決めます（番のプレイヤーは変えない）。カードはいつも持ち主のトラッシュ。説明が使ったプレイヤーの
  番を書くトレーナー（`TrainerEffect.refers_to_user_turn`）を相手が使うことを選ぶと CH1。トレーナーを加えるときは `refers_to_user_turn` を確かめてください。「使わない」が答えにならない
  決定にしないでください（決定の不変条件は、この決定・`EVOLUTION_HEAL`・`ENTRY_POWER` だけ答えられる選択 0 を許す）。
- 決められない場合（新しい停止コード 8 件。どれも `not_in_kyuura`）: STB1（`UNRESOLVED_STADIUM_ACTIVATION_UNDER_TRAINER_BAN`。禁止がはたらいているプレイヤーの `UseStadium`）・TG1
  （`UNRESOLVED_CELADON_GYM_WITHOUT_CONDITION`）・FG1（`UNRESOLVED_FUCHSIA_GYM_AFTER_REPLACEMENT`）・FG2（`UNRESOLVED_FUCHSIA_GYM_WITHOUT_TARGET`。コインの前）・EX1
  （`UNRESOLVED_MINEFIELD_DAMAGE_RECEIVED_POWER`）・VG1（`UNRESOLVED_VIRIDIAN_GYM_ONE_COUNTER`）・VM1（`UNRESOLVED_VERMILION_GYM_ATTACK_ORDER`）・CH1（`UNRESOLVED_CHAOS_GYM_BORROWED_TURN`）。
  再利用: CP2・H1・MH1（範囲を広げない）。ほかのカードの問いの答えを流用しないでください。到達しない場面（爆発ジムのダメージできぜつ・特殊能力で「サカキのポケモン」を山札から進化）は
  `RuntimeError`。エンジンが止める `UNRESOLVED_…` は 109 件、未解決の裁定は 110 件です。
- 書き出しの形式 17 = 形式 16 + 最上位の `stadium`・`stadium_uses_this_turn` と `trainer_in_use.user`（形式 1〜16 は、どれかがあると `ValueError`）。監査の `LATEST_FORMAT` は 17（v0.58 で 18）。
  次の新しい形式は 18（v0.58 で加えた。その次は 19）。新しい決定の種類は `stadium_return_bench`・`evolution_heal`（観測の意味は `pokemon`）、新しいログのイベント（公開）は `stadium_placed`・`stadium_discarded`・
  `stadium_used`・`stadium_discard_energy`・`stadium_return_energy`・`stadium_damage`・`evolution_heal`・`evolution_heal_declined`・`stadium_attack_coin`・`chaos_check`・`chaos_answered`・
  `chaos_not_borrowable`。ログの監査（tests/log_audit.py）は場のスタジアム・使った記録・借りて使うプレイヤー・スタジアムの効果で動いたカードとダメージ・にげるの数の読み方・ベンチの
  上限を組み立て直します。スタジアムのイベントを加えたら、監査（トレーナー 1 回ぶんの並びの確かめから除く `_without_stadium_steps` を含む）にも加えてください。
- 検証用デッキ `L57`・`D57` と組（`PAIRINGS_V0_57`。`L57` 対 `D57`・`L57` 対 `U55`・`D57` 対 `M56`・`D57` 対 `P31`）は tools/existing_effect_games.py の `--batch v0.57` です（前の版の組の
  結果は変わらない）。スタジアムを出す・使う手順は `_v057_trainer`・`_v057_stadium`、クチバのコインは `_v057_attack`、決定は `_v057_decision`（受け付ける答えだけを選ぶ）。関連する
  「○○の」ポケモン（写しにないもの）は加えていません。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## スタジアムの処理を再利用するカード 3 枚と特殊エネルギー 4 枚（v0.58）

- 依頼の 7 枚（タケシのゴローン PMCG5-052・タケシのゴローニャ PMCG5-053・ナツメのサイキックコントロール PMCG6-088・無色2個エネルギー PMCG1-096・きずぐすり配合エネルギー PMCG4-063・
  なんでもなおし配合エネルギー PMCG4-064・レインボーエネルギー PMCG4-065）を、kyuura データの採用で、どのワザも、トレーナーも、特殊エネルギーも登録しました（対応ポケモン 327 → 329。
  写しの組 `pool_v0_58`。写し 415 → 422 枚・対応するカード 413 → 420 枚。ワザの登録 557 → 561・特殊能力の登録 49・トレーナーの登録 80 → 81・特殊エネルギーの登録 0 → 4）。カードごとの結果・共通の処理・再利用した
  記録（SE1〜SE5）・未解決・実装上の読み方・互換性・検証は docs/stadium-reuse-special-energy-v0.58.md。ガイドブックは読んでいません。英語版の文面（「Provides ColorlessColorless」
  「only provides 1 Energy at a time」「The card stays in your opponent's discard pile」など）・現代のルールで日本語の不足を補わないでください。テストの定数は tests/helpers.py の
  `BROCKS_GRAVELER`・`BROCKS_GOLEM`・`SABRINAS_PSYCHIC_CONTROL`・`DOUBLE_COLORLESS_ENERGY`・`POTION_ENERGY`・`FULL_HEAL_ENERGY`・`RAINBOW_ENERGY`・`V0_58_POKEMON`・`V0_58_ENERGIES`・
  `V0_58_CARDS`（`POTION_ENERGY` はトレーナーの `POTION`、`FULL_HEAL_ENERGY` は `FULL_HEAL` と別のカード）。
- 特殊エネルギーは、効果の登録表の `energies`（カード id → `EnergyEntry`。実装は `effects.SpecialEnergyEffect` の部分型）で登録します。登録のない特殊エネルギーは分類が未対応にします
  （名前・説明文・kyuura の `energy.provides` で一括に対応にしない）。印刷の定義（`CardDefinition`）を基本エネルギーに書きかえないでください。同じ名前 4 枚の制限の例外は基本エネルギー
  だけです（GR-2000-P308-SAME-NAME）。
- 無色2個エネルギーは kyuura の日本語の説明が null・`energy.provides` が空です。空の `provides` を「エネルギーを出さない」と読まず、カードの名前と pcg-search.com の同じ版のカードの
  「無色」の記号 2 つで「無色」2 個にしました（`ColorlessUnitsByName`。採用の記録の `play_text` は `card_name_and_edition_symbols`。`scripts/check_card_sources.py` が名前と照らす）。
- カードの枚数・エネルギーの個数・色の割り当てを分けます。ついているカード 1 枚が出すエネルギーは `effects.energy_units`（1 個ずつ、使えるタイプの集まり。無色2個エネルギーは無色 2 個、
  レインボーエネルギーは「6 色のどれか」1 個（合計 1 個。色ごとに数えない）、エナジーバーンのカードは 1 個ずつ「炎」）、並びは `attached_units`、個数は `energy_unit_count` だけで
  求めます。ワザに必要なエネルギーは `effects.attack_cost_payable`（`cards.can_pay_with_units`）、にげるは個数で数えます。`state.energy_types`（カード 1 枚 1 つのタイプ）を、支払い・
  エネルギーの数え方に新しく使わないでください（特殊エネルギーの `provides` は None）。「X」エネルギーを数える・選ぶ処理を加えるときは、レインボーエネルギーの扱い（RB1・RB2・RB3）を
  `programs.transform_energy_question`・`rainbow_attach_question`・`effects.require_energy_type_determined` で確かめてください。
- つけたときの効果（回復・10 ダメージ）は、手札から出してつけたときだけ（`energy_attached_from_hand`。手札からつける通常の操作・あまごい・せいちょう。GR-2000-P310-ATTACH-ENERGY）。
  場のカードの移動・山札やトラッシュからつける効果では起こしません（CR-ENERGY-TRANS-NOT-ATTACHMENT と同じ読み方）。手札からエネルギーカードをつける処理を加えるときは、つける前に
  `attach_from_hand_problem`、つけたあとに `energy_attached_from_hand` → `after_energy_attached` を呼び、きぜつしうるなら `resolution.after_energy`（ログ `knock_out` の `timing` は
  `energy`）にしてください。レインボーエネルギーの 10 はワザ・特殊能力のダメージではありません（弱点・抵抗力・プラスパワー・ディフェンダー・「とうめい」・「ダメージを受けたとき」の
  効果を当てはめない。ログ `energy_damage`）。なんでもなおし配合エネルギーの対象はつけたポケモンで、トレーナーのなんでもなおしの FH1 は当てはまりません。
- 場の外（手札・山札・トラッシュ）の特殊エネルギーは「基本エネルギーカード」ではありません（ERR-ENERGY-RETRIEVAL の読み方）。レインボーエネルギーは、ワザ・にげるの支払いと
  エナジートランスの「草」（CR-ENERGY-TRANS-RAINBOW。CONFIRMED。移動で 10 ダメージは受けない）だけが決まっています。あまごいに CR-ENERGY-TRANS-RAINBOW を当てはめないでください（RB2）。
- にげる: 無色2個エネルギーは分けてトラッシュできません。余計なカードを除いても足りる選び方は `WRONG_RETREAT_COST`（基本エネルギーだけの理由の文は v0.57 と同じ）、どのカードを除いても
  足りなくなる選び方で個数がにげるエネルギーより多いもの（無色2個エネルギーでにげる 1）は RT1。
- ばくれつ（`SelfDestructThenDiscardStadium`）は v0.39 のじばくに、場のスタジアムをトラッシュする要素 `programs.DiscardStadium`（v0.57 の `zones.discard_stadium`。ログ
  `stadium_discarded` の `reason` `attack`・`effect`、スタジアムがなければ `stadium_discard_none`）を加えた型です。いわなだれは v0.39 の `DamageThenChosenBenchTargets` の書き方の違い。
- ナツメのサイキックコントロール（`UseOpponentDiscardTrainer`）: コイン → 「おもて」なら相手のトラッシュの使えるトレーナー（`discard_trainer_use_choices`。ポケモンにつけて使う・場に
  出して使う・スタジアムを除く。使うための条件・リムーブ禁止ジムの追加の条件を使ったプレイヤーの手札・場で満たせないものを除く）から 0〜1 枚（決定 `use_discard_trainer`。0 枚は
  使わない）。選んだら `resume` が `effects.UseDiscardTrainer` を返し、エンジンが外側の使用を `GameState.trainer_stack` に積んで、カードを相手のトラッシュから使用中の場所に移し
  （同じ uid・持ち主のまま。`TrainerInUse.via` は外側のカード）、手札から使うときと同じ手順（錯乱ジムのコイン → リムーブ禁止ジムの追加の条件 → 効果）で内側の使用を始めます。
  内側のカードは持ち主のトラッシュに、外側のカードはそのあと使ったプレイヤーのトラッシュにもどります（`engine._finish_outer_trainers`）。カードの物理的な置き場所（使用中・持ち主の
  トラッシュ）と使用の記録（使うプレイヤー・外側の使用）を分けて持ってください。錯乱ジムのコインは使用ごと（外側の結果を内側に持ち越さない）、CH1 は使うプレイヤーが番のプレイヤーで
  ないときだけ。決定の不変条件は、使わない（0 個）がいつも答えになる例外にこの決定を加えた（広げない）。
- 新しい停止コードは RB1（`UNRESOLVED_RAINBOW_ENERGY_TYPE`）・RB2（`UNRESOLVED_RAINBOW_ATTACH_AS_TYPE`）・RB3（`UNRESOLVED_RAINBOW_AS_BASIC_ENERGY_CARD`）・RB4
  （`UNRESOLVED_RAINBOW_DAMAGE_RECEIVED_POWER`）・TE2（`UNRESOLVED_TRANSFORM_SPECIAL_ENERGY`）・RT1（`UNRESOLVED_RETREAT_OVERPAY`）の 6 件（どれも `not_in_kyuura`）。エンジンが止める
  `UNRESOLVED_…` は 115 件、未解決の裁定は 116 件です。特殊エネルギーのつけたときの効果と、つけたときにはたらく特殊能力が同じタイミングに起こる組（SE2。今の写しでは起こらない）は
  `RuntimeError` です。そのようなカードを加えるときは、番のプレイヤーが順番を決める決定（GR-2000-P325-SAME-TIMING）を先に加えてください。
- 書き出しの形式 18 = 形式 17 + 最上位の `trainer_stack` と `trainer_in_use.via`（形式 1〜17 は、どちらかがあると `ValueError`）。監査の `LATEST_FORMAT` は 18（v0.59 で 19）。次の新しい形式は 19（v0.59 で加えた。その次は 20）。
  新しい決定の種類は `use_discard_trainer`（観測の意味は `card`）、新しいログのイベント（公開）は `energy_heal`・`energy_damage`・`stadium_discard_none`・`discard_trainer_use_none`・
  `discard_trainer_use_declined`。ログの監査（tests/log_audit.py）は、特殊エネルギーの効果のダメージ・内側の `play_trainer`（持ち主のトラッシュから）・外側のカードのトラッシュ・
  ばくれつのスタジアム・にげるの個数を組み立て直します。
- 検証用デッキ `E58`・`R58` と組（`PAIRINGS_V0_58`。`E58` 対 `R58`・`E58` 対 `U55`・`R58` 対 `H54`・`E58` 対 `L57`）は tools/existing_effect_games.py の `--batch v0.58` です（前の版の
  組の結果は変わらない）。特殊エネルギーをつける手順は `_v058_energy`、サイキックコントロールは `_v058_trainer`・`_v058_decision`、無色2個エネルギーでの「にげる」は `_v058_retreat`、
  数えた結果は `v058_uses`。tests/v017_games.py の `play_game` は RB1〜RB4・TE2・RT1 を場から確かめてから別の操作を続けます。公開の固定のデッキ・既存の変種には入れていません。
  勝敗で採用を判断しないでください。

## 特殊能力を止める効果・エネルギーをつける操作を変える効果の 6 枚（v0.59）

- 依頼の 6 枚（マルマイン PMCG1-040 の［エネエネ］・でんげき、カツラ PMCG6-093、タケシの保護 PMCG5-090、カスミのメノクラゲ PMCG5-030 のクリスタルビーム、わるいアーボック PMCG4-008 の
  ショックアイ・どくのきり、まきちらせ!ベトベトガス PMCG4-056）を、kyuura データの採用で、どのワザも、特殊能力も、トレーナーも登録しました（対応ポケモン 329 → 332・トレーナーの登録 81 → 84・
  写しの組 `pool_v0_59`。写し 422 → 428 枚・対応するカード 420 → 426 枚。ワザの登録 561 → 565・特殊能力の登録 49 → 50）。カードごとの結果・共通の処理・再利用した記録（PS-R1〜PS-R3）・
  未解決・実装上の判断・互換性・検証は docs/energy-control-power-suppression-v0.59.md。ガイドブックは読んでいません。英語版の文面（「that power stops working」「Playing additional copies
  of this card this turn has no effect」など）・2000.02.14 版のあとの記録（2000年3月の『トレーナーズ』の［エネエネ］の 8 色）で日本語の不足を補わないでください。テストの定数は
  tests/helpers.py の `BUZZAP_ELECTRODE`・`BLAINE_TRAINER`・`BROCKS_PROTECTION`・`MISTYS_TENTACOOL`・`DARK_ARBOK`・`GOOP_GAS_ATTACK`・`V0_59_POKEMON`・`V0_59_TRAINERS`・`V0_59_CARDS`
  （`MISTYS_TENTACOOL` と化石の秘密のメノクラゲ、`DARK_ARBOK` と化石の秘密・キョウのアーボック、`BLAINE_TRAINER` と「カツラの」ポケモン・カツラの奥の手・カツラのギャンブルを取りちがえない）。
  v0.59 のワザの型は `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません。
- 特殊能力が「使えず、その力も消え」ているかは `continuous.power_suppressed(state, power)`（かがくへんかガスの `suppressors_of` と、まきちらせ!ベトベトガスの `goop_gas_effects`）だけで
  聞きます。v0.8〜v0.58 の節で `continuous.suppressors_of` を聞くとしている場所は、v0.59 からこの関数で読みかえてください（判定を複製しない）。「使うことができず」は宣言して使う
  特殊能力の使用、「その力も消える」は常にはたらく・自動的にはたらく特殊能力の力（kyuura の CR-CHEMICAL-GAS-USE-VS-POWER）。ショックアイ（「使うことができない」だけ）は、相手に与える
  持続する効果 `state.CannotUsePowers`（与えた番から次の相手の番の終わりまで。ベンチでもよい `bench_ok`）で、宣言（`POWER_USE_PREVENTED`）と宣言して使う特殊能力の使う機会
  （こんじょう・ふしちょう・場に出たときの特殊能力。`catalog.offer_stopped`）だけを止めます。常にはたらく・自動的にはたらく力は消さないでください。
- まきちらせ!ベトベトガスは使ったプレイヤーの期限のある効果（v0.56 の `TrainerTurnEffect`。種類 `POWER_SUPPRESSION`。消える番は使った番 + 1）で、かがくへんかガスも止めます
  （CR-POWER-BACK-AFTER-RECOVERY。p.265 の解説の記録）。場のポケモンに印を付けないでください。止める範囲（使った時点で場にいたポケモンだけか）は決まらない（GG1。
  `UNRESOLVED_GOOP_GAS_NEW_POKEMON`）ので、効果のはたらく間に特殊能力を持つポケモンを場に出す・進化させる・退化させる操作を、状態を変える前に止めます（`effects.goop_gas_entry_check`。
  `zones.enter_play`・`evolution.place_evolution_card`・`evolution.devolve`）。ほかのゾーンから場に出す・進化・退化の経路を加えるときも、この関数を通る形にしてください。
- エネルギーカードをつける経路は、どれも `effects.energy_attach_block`（クリスタルビームの `state.CannotAttachEnergy`。はたらく番は次の相手の番）を聞きます（手札からつける通常の操作・
  カツラ・あまごい `ENERGY_ATTACH_PREVENTED`、ワザで手札・山札・トラッシュからつける効果は選べるものから除く）。場のエネルギーのつけかえ・［エネエネ］がこれに当たるかは決まらない
  （CB1。`UNRESOLVED_ATTACH_BLOCK_SCOPE`）ので、受けたポケモンを移動先・つける先に選ぶと止めます。CR-ENERGY-TRANS-NOT-ATTACHMENT（v0.58）でこの範囲を決めないでください。
  エネルギーカードをつける経路を加えるときは、この関数を聞いてください。
- 相手のワザ・トレーナーではがせないエネルギー（タケシの保護 `ProtectAttachedEnergy`。ついているトレーナーの有効期限 `discard_at_end_of_turn` が None = 場をはなれるまで）は、
  はがす効果が選べるものを決めるときに `effects.energy_removal_protected(state, owner, pokemon, by_player)` で除きます（`by_player` はワザ・トレーナーを使うプレイヤー。持ち主なら
  関係しない）。相手のエネルギーカードをはがす効果を加えるときは、この関数を聞いてください。
- カツラ（`TrainerTurnEffect` の種類 `FIRE_DOUBLE_ATTACH`。この番だけ）は、手札からつける通常の操作 1 回（`AttachEnergy.energy2`。既定 None は辞書に書かない）で「炎」エネルギーカード
  2 枚を同じ「カツラのポケモン」につけます。2 回目の通常の操作で 2 枚目をつけるのは BL1（`UNRESOLVED_BLAINE_SECOND_ATTACH`）。1 番に 1 回の操作の数え方を変えないでください。
- ［エネエネ］（`ConvertSelfToEnergy`。宣言して使う）は、つける先（決定 `select_pokemon`）→ 色（決定 `select_color`）を選んでから、使用後の処理（`resolution.after_power`）が
  マルマインをきぜつさせ（ログ `knock_out` の `to_energy`。いちばん上のカードはトラッシュしない）→ 同じ uid のカードをつける先のエネルギーに加え（`attach_converted_energy`。ログ
  `energy_conversion`）→ 相手がサイドを取ります。エネルギーとしての役割は `GameState.energy_roles`（`EnergyRole`）に持ち、そのカードが場のポケモンについているあいだだけ
  `GameState.card_def` が特殊エネルギーの種類の定義（`energy_role_definition`）を返します。印刷の定義を書きかえないでください。ついていなくなった役割の記録は `engine._apply` が
  コマンドの終わりに消します。BZ1（相手のポケモン）・BZ2（「「X」エネルギー(カード)」として数える・選ぶ・つけたときの効果。RB1 と同じ場所で聞く）・BZ3（無色・悪・鋼）・
  BZ4（「ばける」）で止めます。手札からつける通常の操作・特殊エネルギーのつけたときの効果に数えないでください。
- ショックアイでこんじょうを使えるポケモンを選ぶ場面は G37 です。宣言の前の先読みは、選ぶ答えのどれかが問いに当たれば宣言の前に止めるので、そのようなポケモンが相手の場にいると
  ほかのポケモンを選ぶつもりでもワザを使えません（v0.15c からの先読みの動き。変えていない）。
- 書き出しの形式 19 = 形式 18 + 最上位の `energy_roles`（形式 1〜18 は記録があると `ValueError`）。監査の `LATEST_FORMAT` は 19（v0.62 で 20、v0.63 で 21）。次の新しい形式は 20（v0.62 で加えた。その次は 21（v0.63 で加えた））。持続する効果の種類
  `cannot_use_powers`・`cannot_attach_energy` は形式 8 から書けます。新しい拒否のコードは `POWER_USE_PREVENTED`・`ENERGY_ATTACH_PREVENTED`・`DOUBLE_ATTACH_NOT_ALLOWED`・
  `NOT_FIRE_ENERGY`、新しいログのイベント（公開）は `energy_conversion`。不変条件 `engine._energy_role_problems`。ログの監査（tests/log_audit.py）は、まきちらせ!ベトベトガスの
  はたらく間の特殊能力の宣言・カツラの 2 枚・［エネエネ］のきぜつとエネルギーの組み立て直し・役割のカードの個数を確かめます。
- エンジンが止める `UNRESOLVED_…` は 122 件、未解決の裁定は 123 件です（GG1・BL1・CB1・BZ1〜BZ4 は kyuura の未解決の一覧にない `not_in_kyuura`）。
- 検証用デッキ `Z59`・`B59` と組（`PAIRINGS_V0_59`。`Z59` 対 `B59`・`Z59` 対 `R58`・`B59` 対 `U55`・`Z59` 対 `D46`）は tools/existing_effect_games.py の `--batch v0.59` です（前の版の
  組の結果は変わらない）。［エネエネ］は `_v059_power`・`_v059_decision`、カツラ・タケシの保護・まきちらせ!ベトベトガスは `_v059_trainer`・`_v059_energy`（手順がつける前にカツラを使う）、
  数えた結果は `v059_uses`。tests/v017_games.py の `play_game` は GG1・`ENERGY_ATTACH_PREVENTED`・BL1・CB1・`POWER_USE_PREVENTED`・まきちらせ!ベトベトガスの `POWER_SUPPRESSED` と、
  役割のカード（1 枚 2 個）で数が変わる「にげる」を場から確かめてから別の操作を続けます。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 控えへのコイン・ダメージを受けない効果・攻撃するときの特殊能力・相手の効果を受けないダメージの 4 枚（v0.60）

- 依頼の 4 枚（サンダー（化石の秘密）PMCG3-026 のサンダーストーム、R団のストライク PMCG5-016 のかげぶんしん・こうそくカマ、カスミのギャラドス PMCG5-035 の［はんこう］・ハイドロクラッシュ、
  タケシのサンドパン PMCG5-050 のスピードスター・とげボール）を、kyuura データの採用で、どのワザも、特殊能力も登録しました（対応ポケモン 332 → 336・写しの組 `pool_v0_60`。写し 428 → 432 枚・
  対応するカード 426 → 430 枚。ワザの登録 565 → 571・特殊能力の登録 50 → 51。PMCG1〜PMCG6 の未対応は 31 → 27 枚）。カードごとの結果・共通の処理・未解決・実装上の読み方・互換性・検証は
  docs/coins-defense-rebellion-v0.60.md。ガイドブックは読んでいません。英語版の文面（「(or is Benched or is evolved)」「that attack does nothing」など）で日本語の不足を補わないでください。
  テストの定数は tests/helpers.py の `FOSSIL_ZAPDOS`・`ROCKETS_SCYTHER`・`MISTYS_GYARADOS`・`BROCKS_SANDSLASH`・`V0_60_POKEMON`・`V0_60_CARDS`（`FOSSIL_ZAPDOS` と第1弾の `ZAPDOS`、
  `ROCKETS_SCYTHER` とストライク `SCYTHER`、`MISTYS_GYARADOS` と `GYARADOS`・`GIOVANNIS_GYARADOS`、`BROCKS_SANDSLASH` と `SANDSLASH` を取りちがえない）。v0.60 のワザの型は
  `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません。
- 相手の控えそれぞれにコインを投げる効果は要素 `programs.CoinPerOpponentBench`（その時点のベンチの並びの順に 1 匹 1 枚、1 回の `flip` で投げ、ログ `bench_coin_results` に控えと面の対応。
  すべて投げてから「おもて」の控えにダメージ、そのあと「うら」の数で自分へのダメージ）です。「おもて」の数でまとめないでください（どの控えかが要る）。はたらいている「とうめい」の控えの
  後ろにほかの控えがいれば、コインの割り当てが投げ方で変わるので TS1（`UNRESOLVED_BENCH_COIN_TRANSPARENCY_ORDER`。宣言の前）で止めます。2 匹以上の「とうめい」は T27 のままです。
- 「相手のワザのダメージを受ける時、相手プレイヤーがコインを投げ、「うら」ならそのダメージを受けない」効果は、自分自身の持続する効果 `state.TailsDamageGuard`（与えた番からはたらき、
  期限では消えない。種類 `tails_damage_guard`）で、`kernel.deal_damage` がダメージをのせる直前（最終ダメージが 0 より大きい相手のワザのダメージだけ）に `damage_guard_passes` で聞きます
  （ログ `damage_guard_check`。「うら」は `DamageResult.dodged`）。ダメージを受けたら、どの経路のダメージでも `persistent.remove_on_damage`（理由 `damaged`）で消します。ダメージを
  のせる処理を加えるときは、ダメージのログのあとに `remove_on_damage` を呼んでください（ダメージカウンターをのせる・移す効果はダメージではないので呼ばない）。ダメージ以外の効果は
  そのまま受けます（ワザ全体を無効にしない）。受けなかったダメージのあとの「ダメージを与えた後」の効果は既存の Z23 です。
- ［はんこう］（`effects.FailAndReturnOnAttack`。自動的にはたらく特殊能力。`declared = False`）は、p.309 の手順 4 の効果として、宣言のあと・こんらんのコインの前に
  `flow._rebellion_failed` が持ち主のコイン 2 枚を投げます（ログ `rebellion_check`）。すべて「うら」ならワザの失敗（`attack_failed` の `reason` `power`）→ v0.36 の
  `zones.return_in_play_to_deck`（出どころ `power`）→ 持続する効果を消す → 山札を切る。きぜつではありません。手順 4 の効果として数えるので、ほかの手順 4 の効果と重なれば AC13、
  クチバシティジムのコインとは VM1 です。こんらんでは止めません（失敗したらポケモンは場にいないので、AC6 の読み方で結果が変わらない）。ワザを使う時にはたらく特殊能力を加えるときは、
  `effects.attack_rebellion_powers` と同じく `continuous.power_suppressed` で聞き、手順 4 の効果の数え方（`flow._attack_check_failed`）を見直してください。
- 相手の対戦ポケモン自身が持っている効果を計算しないダメージ（スピードスター）は、要素 `Damage` の `defender_effects=False`（`kernel.deal_damage` の `defender_effects`。相手の対戦
  ポケモンへのダメージだけ）です。弱点・抵抗力・ついているトレーナー・受けるポケモンの持続する効果・受けるポケモン自身の特殊能力（`effects.attack_damage_modifiers` の `exclude`・
  `kernel.first_void` の `held_by_receiver`・「とうめい」・かげぶんしん）を計算せず、ワザを使うポケモン・プレイヤー・スタジアムの効果と、ダメージを受けたあとの反応は今までどおりです。
  効果を持っているのがだれかで分け、だれが与えたかで分けないでください。相手の場のほかのポケモンの特殊能力を含むかは SS1（コードのない問い `speed_star_scope`。今の写しでは起こらない）。
  バトル場以外ではたらくワザのダメージを変える特殊能力を加えるときは、SS1 に当たるかを確かめてください。
- 書き出しの形式は 19 のまま（監査の `LATEST_FORMAT` も 19。次の新しい形式は 20。v0.62 で加えた）。持続する効果の種類 `tails_damage_guard` は形式 8 から書けます。新しいログのイベント（公開）は
  `bench_coin_results`・`damage_guard_check`・`rebellion_check`。公開の API の呼び方・コマンド・決定の種類・拒否のコードは変えていません。エンジンが止める `UNRESOLVED_…` は 123 件、
  未解決の裁定は 125 件です（TS1・SS1。kyuura の未解決の一覧にない）。
- ログの監査（tests/log_audit.py）は、かげぶんしんの効果・コイン・ダメージのすぐあとの消去、［はんこう］のコインの並びと山札にもどしたポケモン、スピードスターのダメージに「とうめい」の
  判定がないことを確かめます。v0.59 のまきちらせ!ベトベトガスで消えた「とうめい」・［はんげき］を監査が数えていなかったのを直しました（`goop_gases`）。
- 検証用デッキ `Z60`・`M60` と組（`PAIRINGS_V0_60`。`Z60` 対 `M60`・`M60` 対 `Z59`・`Z60` 対 `D46`・`Z60` 対 `P31`）は tools/existing_effect_games.py の `--batch v0.60` です（前の版の
  組の結果は変わらない）。数えた結果は `v060_uses`。TS1・T27（控えにもダメージ・効果を与えるワザと「とうめい」2 匹以上）・Z23（かげぶんしん）・AC13（［はんこう］を含む）は `V031_STOPS`
  で場から確かめます。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## ワザ・にげる・残りHPではたらく特殊能力とトレーナーのダメージの 4 枚（v0.61）

- 依頼の 4 枚（わるいギャラドス PMCG4-025 の［ファイナルビーム］・れいとうビーム、わるいダグトリオ PMCG4-043 の［おとしあな］・つきおとす、タケシのオコリザル PMCG5-051 の［ずらかる］・
  おおあばれ、トレーナーのバトル場は穴だらけ! PMCG4-055）を、kyuura データの採用で、どのワザも、特殊能力も、トレーナーも登録しました（対応ポケモン 336 → 339・トレーナーの登録 84 → 85・
  写しの組 `pool_v0_61`。写し 432 → 436 枚・対応するカード 430 → 434 枚。ワザの登録 571 → 574・特殊能力の登録 51 → 54。PMCG1〜PMCG6 の未対応は 27 → 23 枚）。カードごとの結果・
  共通の処理・時点の根拠・未解決・実装上の判断・互換性・検証は docs/reactive-powers-trainer-damage-v0.61.md。ガイドブックは読んでいません。英語版の文面で日本語の不足を補わないで
  ください。テストの定数は tests/helpers.py の `DARK_GYARADOS`・`DARK_DUGTRIO`・`BROCKS_PRIMEAPE`・`DIGGER`・`V0_61_POKEMON`・`V0_61_CARDS`（`DARK_GYARADOS` と `GYARADOS`・
  `GIOVANNIS_GYARADOS`・`MISTYS_GYARADOS`、`DARK_DUGTRIO` と `DUGTRIO`、`BROCKS_PRIMEAPE` と `PRIMEAPE`・`DARK_PRIMEAPE` を取りちがえない）。v0.61 のワザの型は
  `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません。
- ［ファイナルビーム］（`effects.BeamOnKnockOut`）は使用を宣言する任意の特殊能力で、時点はこんじょう（v0.11）と同じきぜつの判定の窓です（解決の基盤の効果の定義 `catalog.FINAL_BEAM`。
  決定 `decisions.KNOCK_OUT_POWER`。続きの情報・再開先 `"knock_out"` はこんじょうと共通で、決定の種類で分ける）。自動的にはたらく形・別の段階にしないでください。使えるのは、
  相手のワザの分類の枠（ワザのダメージ・返す効果のダメージ・ワザでのせたダメージカウンター）で HP 以上になったときだけです（`kernel.ko_cause`。特殊能力のダメージ・どく・こんらん・
  トレーナー・自分のワザでは使えない）。きぜつの判定の時点のねむり・マヒ・こんらん・`catalog.offer_stopped`（ガス・まきちらせ!ベトベトガス・ショックアイ）で使えません。コインは
  答えのあとに持ち主が 1 枚だけ投げ、「水」の基本エネルギーカードの数（使った時点。1 枚 1 個）× 20 の特殊能力のダメージ（ワザのダメージの計算をしない。`received_power_damage` は
  当てはめる）。使うを選ぶと止める場合（Z9・RB1・BZ2・勝ち負けが決まる同時のきぜつの C18）は `unresolved_choices` にし、使わないはいつも答えになります（決定の不変条件の例外に
  `knock_out_power` を加えた。広げない）。きぜつするときに使える特殊能力が 2 つ以上なら G40、みちづれできぜつする場合は HC2（v0.31 のコードのない問い `destiny_bond_with_ko_prevention` に
  `UNRESOLVED_DESTINY_BOND_KNOCKOUT` を付けた）。
- ［おとしあな］（`effects.DamageOnOpponentRetreat`。宣言しない）は「にげる」（`engine._retreat`）だけではたらきます（ポケモンいれかえ・突風・ワザの入れ替えは「にげる」ではない。p.325）。
  入れ替えが成り立ったあとに `resolution.after_retreat` が、はたらく［おとしあな］ごと（`effects.retreat_trap_powers`。相手の場の並び）に、にげたプレイヤーのコイン 1 枚（ログ
  `sinkhole_check`）→「うら」ならベンチにもどったポケモンに 20 の特殊能力のダメージ（ログ `sinkhole_damage`）→［ずらかる］→ きぜつ（ログ `knock_out` の `timing` は `"retreat"`）・
  サイド・勝ち負け・バトル場に出す → 同じ番（`CONTINUE_TURN`）。「にげる」の時点で結果が変わる場合（こんらん・受けるダメージがバトル場とベンチで違う）は、エネルギーのトラッシュと
  コインの前に SH1（`UNRESOLVED_SINKHOLE_TIMING`。`engine._sinkhole_check`）。にげられなくする処理にしないでください。つきおとす（`OpponentCoinTailsBonusDamage`）は相手プレイヤーの
  コイン 1 枚で 1 段階に + 20 で、v0.40 の `OpponentFlipsTailsDamage` とは別の型です。
- ［ずらかる］（`effects.ReturnToDeckAtRemainingHp`。宣言しない）は、残りHP（今有効な最大HP − ダメージ）がちょうど 10 で力がはたらいているとき、決まった時点（`kernel.settle_scram`。
  ワザの要素のダメージのまとまりのあと・ダメージ以外の要素のあと・きぜつの判定の窓の始め・［ファイナルビーム］のダメージのあと・特殊能力・エネルギー・トレーナー・にげる・
  ポケモンチェックのどくのあと）に、v0.36 の `zones.return_in_play_to_deck`（出どころ `power`）→ 持続する効果を消す → 山札を切る、です（ログ `scram`。きぜつではない）。残りHPを
  変える処理を加えるときは、そのあとの決まった時点で `settle_scram` を呼んでください（ワザの外は `flow._settle_outside_attack`）。結果が時点で変わる場合（「10」を通る・ワザの途中で
  ポケモンによる要素が残る・2 匹が同時）は SC1（`UNRESOLVED_SCRAM_TIMING`）、力が消えていたあいだに「10」になり力がもどる場合は SC2（`UNRESOLVED_SCRAM_POWER_RESTORED`。
  `engine._apply` が操作の前の状態（`dormant_scram`）と比べる。`state_stop_after` にも加えた）。ポケモンによらない要素は `Element.independent_of_pokemon`（今は `DiscardStadium`）で、
  おおあばれで自分が山札にもどっても場のスタジアムをトラッシュします。ワザの途中の決定をまたぐときは、HP 以上になったポケモンのきぜつの原因を続きの情報の `frame` の `ko_by` で運びます。
- バトル場は穴だらけ!（`effects.AlternateCoinsUntilTailsDamage`）は、実際に使ったプレイヤー → 相手 → … の順に「うら」が出るまでコインを投げ（上限なし。50% の近道をしない。ログ
  `digger_result`）、「うら」を出したプレイヤーの対戦ポケモンに 10 のトレーナーのダメージ（`effects.trainer_damage`。ログ `trainer_damage`。ワザ・特殊能力のダメージの計算をしない）。
  「ダメージを受けない」状態なら受けません（v0.28 の p.235 の解説の記録の再利用。ログ `trainer_damage_prevented`）。受けるダメージを変えるほかの効果で量が変わるときは TD1
  （`UNRESOLVED_TRAINER_DAMAGE_REDUCTION`）。結果は「うら」の側だけで決まるので、コインの前に両方の結果を状態の複製で確かめます（`resolution.trainer_damage_stop`）。きぜつの処理は
  使い終えてトラッシュしたあと（`may_knock_out`。`resolution.after_trainer` がこのコマンドのログ `trainer_damage` のポケモンもきぜつさせる）。
- 書き出しの形式は 19 のまま（監査の `LATEST_FORMAT` も 19。次の新しい形式は 20。v0.62 で加えた）。公開の API の呼び方・コマンド・拒否のコードは変えていません。新しい決定の種類は `knock_out_power`、
  新しいログのイベント（公開）は `knock_out_power_declined`・`knock_out_power_declared`・`knock_out_power_failed`・`knock_out_power_damage`・`scram`・`sinkhole_check`・`sinkhole_damage`・
  `digger_result`・`trainer_damage`・`trainer_damage_prevented`。解決の基盤の入口に `after_retreat`・`trainer_damage_stop` を加えました（tests/test_kernel_integration_v0_15.py の
  `DependencyTest`）。エンジンが止める `UNRESOLVED_…` は 128 件、未解決の裁定は 129 件です（SH1・SC1・SC2・TD1 は kyuura の未解決の一覧にない `not_in_kyuura`、Z9 は
  `kyuura_index_engine_key`）。
- ログの監査（tests/log_audit.py）は、［おとしあな］・［ファイナルビーム］のコインのすぐあとの結果、［おとしあな］・［ファイナルビーム］・トレーナーのダメージの組み立て直し、
  ［ずらかる］で山札にもどしたポケモン（すぐ前のログ `scram`）、バトル場は穴だらけ!のあとの `timing: trainer` のきぜつを確かめます。
- 検証用デッキ `G61`・`P61` と組（`PAIRINGS_V0_61`。`G61` 対 `P61`・`P61` 対 `M60`・`G61` 対 `Z60`・`G61` 対 `P31`）は tools/existing_effect_games.py の `--batch v0.61` です（前の版の
  組の結果は変わらない）。［ファイナルビーム］の答えは `_v061_decision`、バトル場は穴だらけ!は `_v061_trainer`、わるいダグトリオの相手の「にげる」は `_v061_retreat`、数えた結果は
  `v061_uses`。tests/v017_games.py の `play_game` は SH1・SC1・SC2・TD1 を場から確かめてから別の操作を続けます（`v061_stop_expected`）。tests/helpers.py の `trainer_policy_command` は、
  選べる答えがない（使うと止める）決定に、選ばない答えを返します。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。


## 前の番のワザの履歴を読むワザ・相手を手札にもどすワザの 5 枚と、確定した修正を当てはめたベロリンガ（v0.62）

- 依頼の 6 枚（ピジョン PMCG1-066 のふきとばし・オウムがえし、オニスズメ PMCG2-034 のつつく・オウムがえし、オニドリル PMCG2-038 のこうそくいどう・ドリルくちばし、ピジョット PMCG2-043 の
  つばさでうつ・ハリケーン、タケシのダグトリオ PMCG6-060 のあながくれ・ドリルホール、ベロリンガ PMCG2-041 のまきつくベロ・ちょうおんぱ）を、kyuura データの採用で、どのワザも登録しました
  （対応ポケモン 339 → 345・写しの組 `pool_v0_62`。写し 436 → 442 枚・対応するカード 434 → 440 枚。ワザの登録 574 → 586。PMCG1〜PMCG6 の未対応は 23 → 17 枚）。履歴の意味と時点・
  ピジョンとオニスズメの違い・修正の採用・未解決・互換性・検証は docs/history-attacks-v0.62.md。ガイドブックは読んでいません。テストの定数は tests/helpers.py の `PIDGEOTTO`・`SPEAROW`・
  `FEAROW`・`PIDGEOT`・`BROCKS_DUGTRIO`・`LICKITUNG`・`V0_62_POKEMON`・`V0_62_CARDS`（`BROCKS_DUGTRIO` と第1弾・わるいダグトリオ、`FEAROW` とマチスのオニドリルを取りちがえない）。v0.62 の
  効果の型は `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません。
- 前の番のことを読むワザのために、場のポケモンの `PokemonInPlay.history`（`kyuura_engine/history.py`）に 3 種類を分けて持ちます: 使ったワザ（`AttackUsed`。宣言のとき
  `resolution.flow._attack_body`。相手のワザ・受けたワザを自分のワザとして使ったら処理したワザ `processed`。`programs.apply_redirect`）・受けた相手のワザと実際に受けた結果
  （`AttackReceived`。解決の基盤の `kernel.deal_damage`・`kernel.reaches` がこのポケモンを対象にしたとき。最終ダメージの合計・受けた要素・受けなかった要素と理由）・ワザ以外で受けた
  こと（`OtherReceived`。`engine._apply` がワザ・番の終わり・ワザの途中の決定への答え以外のコマンドの前後で、番でないプレイヤーの場のポケモンを比べる。`history.open_probe`・
  `close_probe`）。1 つの「直前のワザ」にまとめないでください（ピジョンは受けたワザ、オニスズメは受けた結果を読む）。記録は状態の正本です。ログ・過去のコマンドを読み直して作ったり、
  今の盤面から逆算したりしないでください。過去のカードの uid は「このカード」の確かめにだけ使います。
- 記録するのは、履歴を読むワザ（`AttackEffect.reads_history`）を持つカードが対戦のカードの定義にあるときだけです（`history.history_needed`。ないときの状態・書き出し・ログは v0.61 と
  同じ）。受けた記録は、番のプレイヤーのワザが相手の場のポケモンを対象にしたときだけ（自分へのダメージ・自分の控えへの効果・返す効果のダメージは記録しない）。進化・退化で消し
  （`history.clear_history`。p.310 の別のポケモン）、にげる・入れ替え・［へんしん］・「ばける」では残し、番の最初に 2 つ前より古い記録を消します（`history.prune`。`procedures.begin_turn`）。
  読むときは記録のカードと今の姿になった番も確かめます（`history._this_card`）。不変条件は `engine._history_problems`。ダメージ・効果を与える処理を解決の基盤の外に加えるときは、
  受けた記録をどう作るかを決めてください（ワザの外のものはコマンドの前後の比べで `OtherReceived` になる）。
- 「1回で消える」は消費の状態を持たずに表します（読むのは前の相手の番の記録だけで、ワザは番に 1 回）。読み方で結果が変わる続く効果は OM1 で止めます。
- ドリルホール（`DamageIfUsedAttackLastTurn`）は、前の自分の番（今の番 − 2）の使った記録の宣言したワザが同じカードの位置 0・名前「あながくれ」なら使えます。使えなければワザを使うための
  条件 `PREVIOUS_ATTACK_NOT_USED`（エネルギーの確認のあと・こんらんのコインの前）。宣言が失敗しても使ったことになります（宣言のときの記録）。ほかのワザで「あながくれ」を自分のワザとして
  使った記録は ED1（コードのない問い。今の写しでは起こらない）。
- ピジョンのオウムがえし（`RepeatReceivedAttack`・要素 `programs.RepeatReceivedAttack`）は、受けた記録の処理したワザの要素の並びに切りかえ、このワザの枠の中でピジョンのワザとして
  処理します（v0.31 の「ゆびをふる」と同じ `run.redirect`。コイン・計算・選ぶものは新しく決める。前の結果を使わない。今の相手のワザから選び直さない）。ダメージの要素だけを受けなかった・
  受けたワザが相手のワザを自分のワザとして使ったものなら MM1、出すワザのエネルギー・条件をピジョンでみたさなければ MM2、場に出てから 1 度だけ使えるワザ・要素の並びのないワザは
  `UNSUPPORTED_MIRROR_MOVE_ATTACK`。出したふきとばしは相手が選ぶ決定のまま（`decision_problems` が `context` の `copied` に委ねる）。
- オニスズメのオウムがえし（`ReflectReceivedDamageAndEffects`）は、受けた最終ダメージの合計をこのワザの基本となるダメージ（p.321 の 1 段階）にして、このワザのダメージとして計算し直し
  （こうらがえしと同じ読み方。GR-2000-P321-ATTACK-DAMAGE）、受けたマヒを与えます。受けたダメージをそのまま相手にのせる・カウンターを移す処理にしないでください。続く効果（ねむり・
  こんらん・どく・持続する効果）は OM1、ワザ以外で受けたものがあれば OM2、ほかの効果（入れ替え・エネルギー・カウンター・回復など）は `UNSUPPORTED_MIRROR_MOVE_EFFECT`。与える効果の
  種類を加えるときは `effects.REFLECTABLE_RECEIVED_ELEMENTS`・`LASTING_RECEIVED_ELEMENTS` を見直してください。
- ハリケーン（`DamageThenReturnOpponentToHand`・要素 `programs.ReturnOpponentToHand`）は、ダメージのあと相手の対戦ポケモンが HP 以上でなければ、v0.42 の `zones.return_in_play_to_hand`
  で持ち主の手札にもどし、持続する効果を消します（きぜつではない）。「とうめい」・「ワザをうけない」を評価し、G37・RD9・SC1 は既存の問いのまま。
- ベロリンガのワザ 0 の名前・レベルは、kyuura の照合の記録 CC-PMCG2-041-P234（研究の基準のコミットの記録。修正のコミット `f52a8e2`）の確定した修正を、写しの作り直しの道具で
  当てはめます（`scripts/extract_kyuura_cards.py` の `CONFIRMED_CORRECTIONS`・`apply_corrections`・`correction_problems`。写しの `corrections` に出どころを書く）。写しを手で直したり、
  写しの元のコミット（`KYUURA_COMMIT`）を一括に上げたりしないでください。修正を加えるときは、前の値・あとの値・記録の id・修正のコミット・記録のコミットを書き、作り直しの検査
  （前の値が写しの元・あとの値が修正のコミット・記録に修正がある・子孫・ほかの項目が変わっていない）が通ることを確かめてください。ガルーラ PMCG2-046 の保留は別の問題です（v0.68 で、利用者が示した訂正 `USER_PROVIDED_CORRECTIONS` として別に持つ）。
- 書き出しの形式 20 = 形式 19 + 場のポケモンの `history`（`serialize.history_record`。形式 1〜19 は記録があると `ValueError`）。監査の `LATEST_FORMAT` は 20（v0.63 で 21）。次の新しい形式は 21（v0.63 で加えた。その次は 22）。
  観測（`observe`）の場のポケモンに `history`（公開の情報）。新しいログのイベント（公開）は `mirror_move_none`・`reflect_received`、`copy_attack` に `received_turn`。新しい拒否のコードは
  `PREVIOUS_ATTACK_NOT_USED`。ログの監査（tests/log_audit.py）は、ハリケーンで手札にもどしたポケモンを確かめます。
- エンジンが止める `UNRESOLVED_…` は 132 件、未解決の裁定は 134 件です（MM1・MM2・OM1・OM2 は kyuura の未解決の一覧にない `not_in_kyuura`、ED1 は `codeless_questions`）。
- 検証用デッキ `H62`・`D62` と組（`PAIRINGS_V0_62`。`H62` 対 `D62`・`H62` 対 `G61`・`D62` 対 `M60`・`H62` 対 `P31`）は tools/existing_effect_games.py の `--batch v0.62` です（前の版の
  組の結果は変わらない）。履歴を読むワザは `_v062_attack`（ドリルホールを使える番に使い、2 回に 1 回あながくれ。オウムがえしは受けた記録があれば使う）、数えた結果は `v062_uses`。
  MM1・MM2・OM1・OM2・未対応・`PREVIOUS_ATTACK_NOT_USED` は `V031_STOPS` で場から確かめます（オウムがえしで出すワザの型も見る `_attack_and_copied_types`）。受けたマヒを与える場面は、
  マヒのあいだはワザを使えないので対戦では起こりにくく、単体テストで確かめます。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## 公開・非公開の状態を扱うトレーナー 4 枚と、一時的に置いておくカード（v0.63）

- 依頼の 4 枚（ロケット団参上! PMCG4-062・くすぐりマシーン PMCG6-084・たたきつけろ!挑戦状 PMCG4-058・カツラのクイズ その3 PMCG6-082）を、kyuura データの採用で登録しました（トレーナーの
  登録 85 → 89・写しの組 `pool_v0_63`。写し 442 → 446 枚・対応するカード 440 → 444 枚。PMCG1〜PMCG6 の未対応は 17 → 13 枚）。カードごとの順番と根拠・状態の設計・未解決・実装上の読み方・
  互換性・検証は docs/hidden-card-trainers-v0.63.md。公式ガイドブックは読んでいません。英語版の文面（「for the rest of the game」「(or if both Benches are full)」など）・現代のルール・
  2000.02.14 版のあとの規定で、日本語の不足を補わないでください。テストの定数は tests/helpers.py の `HERE_COMES_TEAM_ROCKET`・`TICKLING_MACHINE`・`CHALLENGE`・`BLAINES_QUIZ_3`・`V0_63_CARDS`。
- カードの物理的な置き場所・見える範囲・決まった選択と期限を分けて持ちます。手札・山札・ベンチ・トラッシュ・サイドのどれでもない一時的な置き場所は `GameState.set_aside`
  （`state.SetAsideCards`。種類 `hand_set_aside`・`face_down_bench`・`quiz_card`、持ち主・同じ uid のカード・見られるプレイヤー `visible_to`・出どころ・置いた番・もどす番）だけに持ちます。
  手札に「使えない」「見えない」印を付けて残す・ベンチのポケモンにうらの印を付ける・カードを複製する形にしないでください（手札の枚数・手札を動かす効果・手札を見る効果・使うための
  条件・ベンチの数え方が、置いたカードを数えない）。動かすのは `zones.set_aside_hand`・`set_aside_face_down_bench`・`reveal_face_down_bench`・`set_aside_quiz_card`・`return_set_aside`・
  `return_expired_set_aside` だけで、期限のもどしは番の終わりの窓（`procedures.expire_at_turn_end` の最初）です。不変条件は `engine._set_aside_problems`（カードの保存則は置いたカード・
  使用中・外側の使用を含む）。
- おもてのサイドは `GameState.face_up_prizes`（カードごと）。プレイヤーごとの「すべておもて」の印にしないでください（あとからサイドに置かれたカードは裏のまま）。カードがサイドを
  はなれたら `zones.prize_left` で除き、取った・入れかえたログに項目 `face_up`（全員に見えていた項目の名前）を書きます。サイドからカードを動かす処理を加えるときは、`prize_left` を
  呼んでください（不変条件 `engine._face_up_prize_problems`）。
- ロケット団参上!（`RevealAllPrizesTrainer`）はそのときサイドにあるカードだけをおもてにし、再利用できます。くすぐりマシーン（`CoinSetAsideOpponentHandElseEndTurn`。kyuura の種類
  `rockets_secret_machine`）は「おもて」で相手の手札をすべて置き（だれも見ない。0 枚なら置かない）、次の相手の番の終わりに同じカードを置いた順にもどします（対戦が先に終わったら
  置いたまま）。「うら」は `END_TURN`。説明が使ったプレイヤーの番を書くので錯乱ジムで借りると CH1。
- たたきつけろ!挑戦状（`ChallengeBenchFromDecks`）は相手にたずね（`ACCEPT_REQUEST`）、受けないなら 2 枚引き、受けるなら使ったプレイヤー → 相手の順に自分の山札のたねポケモンを
  0〜min(ベンチの空き（`stadiums.bench_limit`）, 選べる枚数) 枚選んでうらに置き（決定 `challenge_bench`）、出し終わったら表にして場に出し（`enter_play`）、それぞれの山札を切ります。
  選べるカードがない・ベンチに空きがないプレイヤーは選ばずに次へ進みます。選べるのに 0 枚は v0.31 の HC5（同じ問い）、まきちらせ!ベトベトガスの間の特殊能力を持つたねポケモンは
  v0.59 の GG1（選べるが選ぶと止める）。新しいコードにしないでください。
- カツラのクイズ その3（`BlainesQuiz`）は、手札のワザを持つポケモンのカードを伏せて置き（`quiz_card`）、ワザの名前だけを伝え（`quiz_attack`。ログ `quiz_hint`）、相手が名前を答え
  （`quiz_answer`。候補は `effects.quiz_answer_names`（同梱のカードのデータとこの対戦の定義のポケモンの名前）で、置いたカード・手札によらない）、おもてにして名前の完全一致で判定し、
  引いて、置いたカードを手札にもどします。候補にない値は不正な操作で、正解でない答えとは別です。手札にワザを持つポケモンのカードがなければ QZ1
  （`UNRESOLVED_BLAINES_QUIZ_WITHOUT_POKEMON`。使う前）。メタモン（ワザがない）は選べません。
- 観測: プレイヤーごとの `prizes.face_up`・`set_aside`（枚数・出どころ・もどす番は全員、カードは見られるプレイヤーにだけ）。`challenge_bench`・`quiz_card`・`quiz_attack` は決めるプレイヤーで
  ない人に種類と決めるプレイヤーだけを見せます（`observation.HIDDEN_COUNT_KINDS`。選ぶ数・選べるものの数が見えないカードの数を漏らすため）。見えないカードを選ぶ決定を加えたら、数の
  漏れも確かめてください。ログの項目 `face_up` の項目は `visible_event` が全員に見せます。
- 番を終えるトレーナー（`may_end_turn`）の使用のあと、`engine._finish_trainer` は使ったプレイヤー（`TrainerInUse.using_player`）の番を終えます（v0.62 までは使用の記録の `player` =
  カードの持ち主を渡していて、サイキックコントロールで使ったロケット団員の「うら」で NOT_YOUR_TURN になっていた）。
- トレーナーの効果の途中の答えの確かめ（`engine._trainer_dead_end`・`_decision_has_unstopped_answer`）は、答えを順に作る `resolution.programs.iter_answers` と数だけを求める
  `answer_count` を使います（`all_answers` は `list(iter_answers(...))`。答えの並び・上限は変えていない）。
- 書き出しの形式 21 = 形式 20 + 最上位の `set_aside`・`face_up_prizes`（形式 1〜20 は、どちらかがあると `ValueError`）。監査の `LATEST_FORMAT` は 21。次の新しい形式は 22。新しい決定の
  種類は `challenge_bench`・`quiz_card`・`quiz_attack`・`quiz_answer`、新しいログのイベントは `prizes_revealed`・`face_down_revealed`・`quiz_hint`・`quiz_answer`・`quiz_reveal`（公開）・
  `set_aside_hand`・`set_aside_returned`・`face_down_bench`・`challenge_bench_skipped`・`quiz_card_set`（非公開の項目あり）。ログの監査（tests/log_audit.py）は、置いたカード・おもての
  サイドの組み立て直しと、取った・入れかえたカードの `face_up`・期限のもどし・クイズの判定を確かめます。
- エンジンが止める `UNRESOLVED_…` は 133 件、未解決の裁定は 135 件です（QZ1 は kyuura の未解決の一覧にない `not_in_kyuura`）。
- 検証用デッキ `T63`・`Q63` と組（`PAIRINGS_V0_63`。`T63` 対 `Q63`・`T63` 対 `H62`・`Q63` 対 `K56`）は tools/existing_effect_games.py の `--batch v0.63` です（前の版の組の結果は変わらない）。
  4 枚は `_v063_trainer`、挑戦状・クイズの決定は `_v063_decision`（相手の決定にも答え、受ける・受けない、正解・不正解を番の番号とカードの番号で回す。HC5 の 0 枚は選ばない）、数えた結果は
  `v063_uses`。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。


## 「うら」が出るまで投げるコインと、その先読みの有限の組と、化石の秘密のイシツブテの系統 3 枚（v0.64）

- 依頼の 3 枚（イシツブテ PMCG3-034 のれんぞくいしなげ、ゴローン PMCG3-037 のかたくなる・いわおとし、ゴローニャ PMCG3-038 のいわころがり・じばく。どれも化石の秘密）を、kyuura データの
  採用で、どのワザも登録しました（対応ポケモン 345 → 348・写しの組 `pool_v0_64`。写し 446 → 449 枚・対応するカード 444 → 447 枚。ワザの登録 586 → 591。PMCG1〜PMCG6 の未対応は 13 → 10 枚）。
  カードごとの判断・有限の組の根拠・未解決とエンジンの未対応・互換性・検証は docs/geodude-line-unbounded-coins-v0.64.md。ガイドブックは読んでいません。テストの定数は tests/helpers.py の
  `FOSSIL_GEODUDE`・`FOSSIL_GRAVELER`・`FOSSIL_GOLEM`・`V0_64_POKEMON`・`V0_64_CARDS`（「タケシの」系統（`BROCKS_GEODUDE` など）と取りちがえない。進化元は名前の完全一致）。v0.64 の型
  `CoinsUntilTailsDamage` は `ATTACK_TYPES_SINCE_V0_17` に加え、`v013_checks.VERIFIED` には入れていません（`damage_profile` は `NotImplementedError`）。
- 「うら」が出るまで投げるコインは `coins.flip_until_tails` だけで投げます（1 枚 1 回 `getrandbits(1)`。上限・打ち切り・分布が同じ別の乱数の使い方にしない。ログは 1 枚ごとの `coin_flip` に
  `until: "tails"`）。値 `programs.HeadsUntilTails(per)` が「おもて」の数 × `per` を p.321 の 1 段階にし、要素 `Damage` は値が `flip_until_tails` を持つときだけそれを使います。1 枚目が「うら」なら
  基本となるダメージ 0 で、ワザの失敗（`attack_failed`）にしないでください。順番の決定をまたぐときは基本となるダメージを続きの情報で運び、投げ直しません。
- 宣言の前の先読みは、コインの結果を 1 つずつ試せないので、「おもて」の数 h を有限の組に分け、組ごとにいちばん小さい h だけを試します（`resolution/unbounded.py` の `head_classes`。
  `preflight.Oracle.coin_run`・`RecordingRandom.record_run`）。組の key は実際の処理と同じ関数（`kernel.attack_modifiers_of`・`with_stadium_coin`・`compute_damage`・
  `calming_retaliation_differs`・`deferred_receivers`）で求めた、計算の木と、残りの HP でまとめた最終ダメージと、受けたダメージで量が決まる返す効果の結果です。h が後の処理に入る場所を
  加える（h を読む新しい効果・受けたダメージの量を読む新しい処理を先読みの範囲に加える）ときは、key に加え、docs 3.2 節の根拠を見直してください。key の関数と `deal_damage` の計算を別々に
  書かないでください（同じ関数を使う）。代表の値は先読みの複製の上だけで使います。
- 有限の根拠は、計算の操作（`unbounded.SUPPORTED_OPERATIONS`）が入力が十分大きければ一定か減らないことで、h_s・周期を盤面から求めます。`damage.DAMAGE_OPERATIONS` に操作を加えたら、
  `SUPPORTED_OPERATIONS` に加える前に根拠（一定か減らない・周期）を確かめてください。前提を満たさない場（対応しない操作・ダメージカウンターの単位でない数・既定でない要素の項目）は、推測せず
  問い `unbounded_coin_preflight`（`UNSUPPORTED_UNBOUNDED_COIN_PREFLIGHT`。エンジンの未対応。研究の対応表の停止コードに入れない）で止めます。実際の h の key が組にないなら `RuntimeError` です。
  `MAX_BRANCHES` を上げて上限なしのコインを試す形にしないでください。テストで長いコインの並びを決めるときは tests/helpers.py の `with_coin_bits`（乱数の内部の状態を直接決める。624 枚まで）。
- かたくなるは既存の `ZeroDamageBelowNextTurn(40)`（`effects.zero_damage_below_texts` にゴローンの書き方を 1 通り）、じばくは既存の `SelfDestruct(100, 20, True)`（`SELF_DESTRUCT_TEXTS[True]` に
  読点のない書き方を 1 通り。スタジアムをトラッシュする「ばくれつ」の書き方には加えていない）です。書き方の比べ方を一律に緩めないでください。
- 書き出しの形式は 21 のまま（監査の `LATEST_FORMAT` も 21。次の新しい形式は 22）。公開の API の呼び方・コマンド・決定の種類・ログのイベントの種類は変えていません（`coin_flip` に項目 `until`）。
  新しい未解決の裁定はなく、エンジンが止める `UNRESOLVED_…` は 133 件、未解決の裁定は 135 件のままです。
- 検証用デッキ `G64` と組（`PAIRINGS_V0_64`。`G64` 対 `H62`・`D46`・`P61`・`W45`）は tools/existing_effect_games.py の `--batch v0.64` です（前の版の組の結果は変わらない）。数えた結果は
  `v064_uses`。ゆびをふる・オウムがえしでれんぞくいしなげを使う場面は単体テストで確かめます。公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## ワザの最中の任意の決定と、変わり身の術・カスミのドククラゲ・タケシのサイドン（v0.65）

### 対象と数

- 依頼の 3 枚を、kyuura データの採用で、どのワザも、特殊能力も、トレーナーも登録しました。
  - キョウ秘伝,変わり身の術 PMCG6-083
  - カスミのドククラゲ PMCG5-033（［にげこむ］・クラゲどく）
  - タケシのサイドン PMCG5-055（［ベンチガード］・ラリアット）
- 数の変化:

  | | v0.64 | v0.65 |
  |---|---|---|
  | 対応ポケモン | 348 | 350 |
  | トレーナーの登録 | 89 | 90 |
  | 写し | 449 枚 | 452 枚 |
  | 対応するカード | 447 枚 | 450 枚 |
  | ワザの登録 | 591 | 593 |
  | 特殊能力の登録 | 54 | 56 |
  | PMCG1〜PMCG6 の未対応 | 10 | 7 |

- 写しの組は `pool_v0_65`。
- カードごとの結果・3 つの時点・続きの情報・未解決・実装上の判断・互換性・検証は docs/reactive-decisions-v0.65.md。
- 公式ガイドブックのキャプチャ・OCR・読み直しは行っていません。英語版の文面・現代のルールで日本語の不足を補わないでください。
- テストの定数は tests/helpers.py の `KOGAS_NINJA_TRICK`・`MISTYS_TENTACRUEL`・`BROCKS_RHYDON`・`V0_65_POKEMON`・`V0_65_CARDS`。

### ［にげこむ］の文面の出典

- 処理に使う文面は、このリポジトリの v0.18b の記録の再利用です（`card_sources.json` の `play_text` は `kyuura-engine docs/unresolved-research-v0.18b.md#4.1`）。
  - 記録は docs/unresolved-research-v0.18b.md 4.1 の p.100 の最新の説明と解説で、2026-10-14 に読みました。
  - v0.65 では原典を開いていません。
- その記録について、次のことを区別してください。
  - 元の確認日（2026-10-14）は、v0.65 の採用の日（2026-10-18）と別です。
  - 記録の範囲は［にげこむ］の最新の説明と解説だけです。カードの全体を照合した記録とせず、`card_verification.json` に加えないでください。
  - kyuura が p.100 を確かめた記録としないでください（研究の対応表の `registered_without_kyuura_record`）。
  - kyuura の印刷の文面（「ダメージ以外の効果」を受けない文がない）と最新の説明の違いを、転記の誤りとしないでください。
- `scripts/check_card_sources.py` の `ENGINE_RECORDS` が、この形の根拠（出典・印刷の文面と違うこと・記録の文書にある文面・研究の対応表）を確かめます。

### 3 つの決定と時点

ワザを受ける側（ワザを使っていないプレイヤー）が、ワザの途中の決定で使うかを選びます。再開先は既存の `"attack"` です。

| 効果 | 決定 | 時点 |
|---|---|---|
| 変わり身の術 | `ninja_trick` | 宣言が受け付けられたあと・ワザの要素の前 |
| ［ベンチガード］ | `bench_guard` | 控えへのワザのダメージを計算したあと・のせる前（`kernel.bench_guard_answer`） |
| ［にげこむ］ | `reaction_switch` | ダメージの要素のまとまりのあと・最初のダメージ以外の要素の前、またはワザの要素の最後（`programs.run_elements` の `offer_flee`） |

- 自動的にはたらく形・強制にしないでください。ワザのあとに動かさないでください。
- 新しい段階・コマンド・保留中のリストを加えないでください。
- 決めるのが相手であることを許すのは `engine._reaction_decision_problems` だけです。広げないでください。

### 続きの情報

- 続きの情報は決定の `context` の明示的なデータで持ちます。オブジェクトへの参照を持たないでください。
  - 変わり身の術・［にげこむ］は `boundary`（再開する要素の位置）。
  - ［ベンチガード］は `element` と `bench_guard`（残りの控えのダメージの並び・要素の続き）。
  - まだ聞いていない［にげこむ］の候補・入れ替えた記録は `frame` の `flee`・`fled`。
- `PendingDecision` に項目を加えないでください。
- 再開は答えを当てはめてから続けます。宣言・それまでのコイン・ダメージを繰り返さず、答えのあとでコインを投げ直さないでください。

### 変わり身の術

- バトル場の今の姿の名前が「キョウの」で始まるポケモンにつけます（いなければ TR1）。有効期限はありません（`discard_at_end_of_turn` None）。
- つけたポケモンがバトル場をはなれて控えにもどったら、`effects.discard_on_leaving_active` がトラッシュします（ログ `discard_attached_trainer` の `reason` `left_active`）。
  - 呼ぶのは、にげる・ポケモンいれかえ・突風・ワザの効果の入れ替え・マチス・変わり身の術・［にげこむ］のすべての経路です。
  - バトル場から控えにもどす経路を加えるときは、この関数を呼んでください。
- 入れ替えは「にげる」ではありません（`effects._switch_active_with_bench` の `trainer`）。

### ［にげこむ］

- ダメージを受けたとき（`kernel.receiving`）に、受けたときの特殊状態で候補にします。あとの特殊状態で決め直さないでください。
- 使ったら、そのワザの残りの「ダメージ以外の効果」を、このポケモンにもかわりに出たポケモンにも与えません。
  - `kernel.reaches` がログ `flee_effect_skipped` を残し、履歴に `fled` を記録します。
  - その効果を決めるコインも投げません（`AttackRun.knocked_out`）。

### ［ベンチガード］

- 聞く場面: 自分のほかのタケシのサイドンがベンチにいて、自分の控えポケモンがワザのダメージの要素で 10 以上を受けるとき。自分のワザでも聞きます。
- 選ぶ数は 0〜min(サイドンの数, ダメージ ÷ 10)。もとのダメージを 10 × 数だけ減らし、サイドンに 10 ずつのせます。
  - ログ `damage` の `amount` は減らしたあとの量で、`bench_guard` に (サイドン, 10)。サイドンごとにログ `bench_guard`。
- 控えへのダメージを与える要素は `programs.guarded_damages` で与えます（`Element.guards_bench`）。控えへのダメージを与える要素を加えたら、同じ形にしてください。
- ワザでないダメージの［ベンチガード］はエンジンの未対応です。状態を変える前に `UNSUPPORTED_BENCH_GUARD_OUTSIDE_ATTACK` で止めます（`effects.bench_guard_outside_attack_check`）。
  - 控えポケモンにワザでないダメージを与える処理を加えるときは、この関数を呼んでください。

### 決められない場合

- 新しい停止コードは 8 件で、どれも `not_in_kyuura` です。
  - NT1 `UNRESOLVED_NINJA_TRICK_ATTACK_COIN_ORDER`
  - NT2 `UNRESOLVED_NINJA_TRICK_LEAVES_WITH_POKEMON`
  - NT3 `UNRESOLVED_NINJA_TRICK_UNDER_TRAINER_BAN`
  - RX1 `UNRESOLVED_REACTIVE_SWITCH_TRANSFORMED_ATTACKER`
  - FL1 `UNRESOLVED_FLEE_DURING_OWN_ATTACK`
  - BG1 `UNRESOLVED_BENCH_GUARD_RECOMPUTE`
  - BG2 `UNRESOLVED_BENCH_GUARD_ZERO_DAMAGE_REACTION`
  - KD1 `UNRESOLVED_REACTION_BY_KNOCKED_OUT_POKEMON`（同じワザのダメージで HP 以上になったポケモンの［にげこむ］・［ベンチガード］。こんじょう・［ファイナルビーム］には当てはめない）
- コードのない問いは FL0 `flee_then_damage`・BG0 `bench_guard_element` です。
- 選べるが選ぶと止める形では、「使わない」がいつも答えになります（決定の不変条件の例外にこの 3 つを加えた。広げない）。
- 推測で決めないでください。実装の順番で決めないでください。
- エンジンが止める `UNRESOLVED_…` は 141 件、未解決の裁定は 143 件です。

### 変えていないもの

- だつりょくえきの DR1・DR6 は未解決のままです。v0.65 の仕組みで決まったことにしないでください（v0.68 で採用の仕様として実装したが、裁定としては未解決のまま）。
- 書き出しの形式は 21 のまま（次の新しい形式は 22）です。公開の API の呼び方・コマンドも変えていません。
- 新しいログのイベント（公開）: `ninja_trick`・`ninja_trick_declined`・`flee`・`flee_declined`・`flee_effect_skipped`・`bench_guard`。

### 検証用デッキ

- 検証用デッキ `K65`・`R65` と組 `PAIRINGS_V0_65` は tools/existing_effect_games.py の `--batch v0.65` です。
  - 組は `K65` 対 `R65`・`R65` 対 `L39`・`R65` 対 `Z60`・`K65` 対 `H62`。
  - 前の版の組の結果は変わりません。
- 手順:
  - 決定の答え方は `_v065_decision`（止める選択は選ばない）、変わり身の術は `_v065_trainer`。
  - 数えた結果は `v065_uses`。
  - NT1・NT2 で止まったワザは `V031_STOPS` で場から確かめます。
- 公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## のぞむなら選ぶ・両方が選ぶトレーナーと、お上品攻撃・ナツメのESP・カスミの勝負（v0.66）

### 対象と数

- 依頼の 3 枚のトレーナーを、kyuura データの採用で登録しました。
  - お上品攻撃 PMCG5-074
  - ナツメのESP PMCG6-087
  - カスミの勝負 PMCG5-068
- 数の変化:

  | | v0.65 | v0.66 |
  |---|---|---|
  | 対応ポケモン | 350 | 350 |
  | トレーナーの登録 | 90 | 93 |
  | 写し | 452 枚 | 455 枚 |
  | 対応するカード | 450 枚 | 453 枚 |
  | ワザの登録 | 593 | 593 |
  | 特殊能力の登録 | 56 | 56 |
  | PMCG1〜PMCG6 の未対応 | 7 | 4 |

- 写しの組は `pool_v0_66`。
- カードごとの結果・計算の段階・やり直す時点・じゃんけん・未解決・実装上の判断・互換性・検証は docs/optional-trainers-v0.66.md。
- 公式ガイドブックのキャプチャ・OCR・読み直しは行っていません。英語版の文面（「at the end of your turn」「rounded to the nearest 10」「re-flip those coins once」
  「flip a coin」）・現代のルールで日本語の不足を補わないでください。
- テストの定数は tests/helpers.py の `CHARITY`・`SABRINAS_ESP`・`MISTYS_DUEL`・`V0_66_CARDS`。

### ついているトレーナーの有効期限の行き先

- 有効期限の番の終わりにトラッシュするか手札にもどすかは、トレーナーの実装の `TrainerEffect.expiry_destination`（`EXPIRE_TO_DISCARD`・`EXPIRE_TO_HAND`）で決めます
  （`procedures.discard_expired_attachments`。手札ならログ `return_attached_trainer`）。カード id で分けないでください。
- もどす手札は、つけたプレイヤー（`AttachedTrainer.player`）のものです。つけたプレイヤーとカードの持ち主が違えばエンジンの不具合です。
- お上品攻撃の期限（「相手の番が終わったら、手札にもどす」）は、kyuura の card_differences の PMCG5-074 の再利用です。きぜつしたら今までどおりトラッシュします。

### お上品攻撃（p.321 の 5 段階の選べる減少）

- ワザを使うポケモンについているトレーナーカードの効果なので p.321 の 5 段階です（GR-2000-P321-DAMAGE-ORDER）。`effects.attack_damage_modifiers` が `damage.REDUCE_CHOICE` を加えます。
  最終ダメージから差し引かないでください。
- 同じ 5 段階の加算の効果（プラスパワー）のあとに減らし、6〜8 段階は減らしたあとのダメージで計算します。5 段階に加算でない効果と減らす効果が重なったら `RuntimeError`。
- 減らす量はダメージカウンターの単位（10）ずつ、0〜5 段階のダメージです（GR-2000-P319-HP-AND-DAMAGE。実装上の読み方）。
- 量はワザを使ったプレイヤーが決定 `damage_reduction` で選びます（`damage.DamageReductionRequired`。ダメージの要素が出す。`carry=True`）。選べるものが 0 だけなら決定を出しません。
  減らしたときだけログ `damage` に `damage_reduced`。
- 相手の対戦ポケモンへのダメージだけです（控え・自分へのダメージに当てはめない）。減らしたダメージは、受けたダメージで量が決まる返す効果の「受けたダメージ」に含みます
  （CR-SHELL-ATTACK-ATTACKER-PLUSPOWER）。
- 0 より小さくして結果が変わる場合は CA1（`UNRESOLVED_CHARITY_BELOW_ZERO`。問い `charity_below_zero`。宣言の前）。
- 決定を出せない呼ぶ側（返す効果のダメージ・v0.13 の約束のワザ・前の要素がダメージを与えた並び）はエンジンの未対応 `UNSUPPORTED_DAMAGE_REDUCTION_DECISION`
  （問い `damage_reduction_decision`。研究の対応表の停止コードに入れない）。
- 先読みは、計算の結果が同じ量をまとめて試します（`programs.reduction_answers`）。「うら」が出るまで投げるコイン（v0.64）の組の key に減らす量の選び方を加えました
  （`resolution/unbounded.py`）。残りの HP で選べる量・実際の対戦のコインに上限をつけないでください。
- v0.13 の止める関数が使う `effects.preview_attack_damage` は減らす量を 0 として計算します（技術的な制限。標準の先読み `derived` は試す）。

### ナツメのESP（説明文のコインのやり直し）

- つける先は、今の姿の名前が「ナツメの」で始まる自分の場のポケモン（決定 `select_pokemon`。いなければ TR1）。使った番の終わりにトラッシュします。
- やり直せるのは、解決の基盤の `AttackRun.flip`（ワザの説明文のコイン）だけです。こんらん・手順 4 の効果・スタジアム・「とうめい」・［はんこう］のコインに当てはめないでください。
- 説明文のコインを投げた直後・結果を使う前に、ワザを使ったプレイヤーに決定 `esp_redo` で聞きます（`programs.suspend_esp_redo`。`carry=True`。続きの情報の `esp`）。
  - やり直すなら同じ枚数をすべて投げ直し、やり直した結果だけを使います（一部だけを投げ直さない。ログ `esp_redo` に最初とやり直しの結果）。やり直さないならログ `esp_redo_declined`。
  - 再開は答えを当てはめてから決定を出した要素をもう一度処理し、その `flip` は決定の前（やり直したならやり直し）の結果を使います（`AttackRun.esp_preset`。投げ直さない）。
  - 聞くのは 1 つのワザで 1 回です（`AttackRun.esp_done`）。2 回目の説明文のコインは ES0（コードのない問い `esp_separate_coin_tosses`）。
- ES1（相手プレイヤーが投げるコイン）・ES2（2 枚以上）・ES3（「ナツメのポケモン」でなくなった）は、やり直すを選ぶと止めます（`effects.esp_redo_problem`）。
  「やり直さない」はいつも答えになります（決定の不変条件の例外にこの決定を加えた。広げない）。
- 説明文のコインのワザを「先にすべて投げる」形に書きかえないでください。説明文のコインを投げる要素を加えるときは、`AttackRun.flip` を通してください。
- 「うら」が出るまで投げるコイン（`coins.flip_until_tails`）とESPの組み合わせは今の写しでは起こらず、起こったらエンジンの不具合として止めます。

### カスミの勝負（じゃんけん）

- 使ったプレイヤー → 相手の順に手を決定 `janken_hand`（0 グー・1 チョキ・2 パー）で決めます。決める人が段階で変わるのを許すのは、このカードの `decision_problems` だけです。
- 1 人目の手は 2 人目の決定の続きの情報（`context` の `first`）にだけ持ちます。観測・ログに、両方が決める前の手を書かないでください。両方が決めたらログ `duel_janken`（公開）。
  対戦準備のじゃんけんのログ `janken` と別のイベントです。
- あいこはくり返します（回数の上限なし）。勝ち負けをコイン・乱数で決めないでください。手をカードとして表さないでください。
- 勝ったプレイヤーの手札（使っているこのカードは含まない）を `zones.return_hand_cards_to_deck` でもどし → 切る → 5 枚引く（引けるだけ）。使ったプレイヤー・カードの持ち主・
  勝ったプレイヤーは別の値です。
- 場を変えないトレーナーは `TrainerEffect.changes_field = False` にでき、`engine._trainer_dead_end` の確かめをしません（あいこのくり返しを深く試さない）。場を変えうるトレーナーに
  付けないでください。

### 変えていないもの

- 書き出しの形式は 21 のまま（次の新しい形式は 22）です。公開の API の呼び方・コマンドも変えていません。
- 新しい決定の種類: `damage_reduction`・`esp_redo`（観測の意味は `number`）・`janken_hand`（`janken`）。新しいログのイベント（公開）: `esp_redo`・`esp_redo_declined`・`duel_janken`・
  `return_attached_trainer`。
- エンジンが止める `UNRESOLVED_…` は 145 件、未解決の裁定は 147 件です（CA1・ES1〜ES3 は `not_in_kyuura`。ES0 は数えない）。
- だつりょくえきの DR1・DR6 は未解決のままです。

### 検証用デッキ

- 検証用デッキ `S66`・`C66` と組 `PAIRINGS_V0_66`（`S66` 対 `C66`・`C66` 対 `P46`・`S66` 対 `H62`・`C66` 対 `R65`）は tools/existing_effect_games.py の `--batch v0.66` です。
  前の版の組の結果は変わりません。
- 手順は `_v066_trainer`・`_v066_decision`（相手の決定にも答える。じゃんけんは 2 人の回し方を変える）、数えた結果は `v066_uses`。
- 公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## マチスの秘策と、うらのカード・先読みのフォールバックの修正（v0.67）

### 対象と数

- 依頼の 1 枚のトレーナー（マチスの秘策 PMCG5-093）を、kyuura データの採用で登録しました。
- 数の変化:

  | | v0.66 | v0.67 |
  |---|---|---|
  | トレーナーの登録 | 93 | 94 |
  | 写し | 455 枚 | 456 枚 |
  | 対応するカード | 453 枚 | 454 枚 |
  | PMCG1〜PMCG6 の未対応 | 4 | 3 |
  | 書き出しの形式 | 21 | 22 |

- 写しの組は `pool_v0_67`。カードごとの結果・おもてにする時・見えない情報・未解決・実装上の判断・互換性・検証は docs/secret-plan-preflight-v0.67.md。
- 公式ガイドブックのキャプチャ・OCR・読み直しは行っていません。英語版の文面（「(You can't play this card if your Bench is full.)」「Flip the card if either player needs to know what it is」）・
  現代のルールで日本語の不足を補わないでください。
- テストの定数は tests/helpers.py の `LT_SURGES_SECRET_PLAN`・`V0_67_CARDS`。

### うらのカードの持ち方

- うらのカードは `GameState.face_down_cards`（uid の並び）だけに持ちます（`GameState.is_face_down`）。v0.63 の置いておくカード（`SetAsideCards`）・場のポケモンの印にしないでください。
- うらのあいだ、`GameState.card_def(uid)` は `cards.FACE_DOWN_DEFINITION` を返します（種類「ポケモン」・段階「たね」・特殊能力なし）。ほかの項目（`FACE_DOWN_HIDDEN_FIELDS`）を読むと
  `HiddenPropertyRead`（FD1。`UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY`）。印刷の定義・共有する `CardDefinition`・カードの id を書きかえないでください。
- 場のポケモンを調べる共通の処理（`effects.knocked_by_hp`・`max_hp_drops`・`kernel.knocked_out`）は、うらのカードを飛ばします。場のポケモンの定義を読む処理を加えるときは、
  うらのカードを飛ばすか、おもてにする（指定する）かを決めてください。`damage >= max_hp` を直接書かず `knocked_by_hp` を使ってください。
- 不変条件（`engine._face_down_pokemon_problems`・`_face_down_list_problems`）は、うらのあいだにダメージ・特殊状態・持続する効果・ついているトレーナー・重なり・のせたカード・
  ほかの記録がないことを確かめます。

### おもてにする時

- 自分の番の `MAIN` に選んで（`RevealFaceDown`。ログ `secret_plan_revealed` の `cause` `choice`）・自分の操作（ワザ・にげる・特殊能力・進化。`engine._reveal_for_action`）・
  ダメージや効果を受ける時（`kernel.designate`（`deal_damage`・`reaches`）・`conditions._prevented`・`effects.trainer_damage`・決定の答えの指定 `engine._designate_answer`・特殊能力の
  選ばせるもの・トレーナーをつける・つけたときの効果のある特殊エネルギー）。おもてにするのは `zones.reveal_face_down`、指定は `zones.designate_face_down` だけです。
  ダメージ・効果を与える処理を加えるときは、そのまえにこれらを通してください。
- 全体に働く効果ではおもてにしません（かがくへんかガスの p.277 の解説の記録の再利用。広げない）。
- たねポケモンでなければ、ついているカードごとトラッシュ（ログ `secret_plan_discarded`。きぜつではない。サイドは取られない）。空いたバトル場は `resolution.after_power`・
  `after_trainer` で出します（不変条件 `engine._power_aftermath_problems` は `secret_plan_discarded` の `zone` が `active` のときの続きを許す）。
- 自分の操作で、おもてにしたたねポケモンの操作が受け付けられなければ、コマンドごと拒否します（うらのまま）。うらにして出した番には進化できません。
- ワザの途中にトラッシュしたポケモンは `Resolution.secret_lost` に記録し（決定をまたぐときは続きの情報で運ぶ）、ダメージは `DamageResult.lost`。対象がいなくなったら効果が終わる
  トレーナーは `TrainerEffect.ends_on_lost_target`、ほかの扱えない指定は `UNSUPPORTED_SECRET_PLAN_LOST_TARGET`（エンジンの未対応）。

### 見えない情報

- 観測は本当のカード（`real`）を持ち主だけに見せ、HP・タイプ・ワザなどは書きません。ログの写しは、見る人の相手の今うらのカードの uid を、カードの uid を書く項目
  （`observation.UID_FIELDS` と `…_card`・`…_cards`）から除きます。カードの uid を書くログの項目を加えるときは、この名前の決まりにしたがってください（場のポケモンの番号は `pokemon_id`）。
- 相手のうらのカードがあり、相手のコマンドの処理が本当のカードを使ったら（`zones.IDENTITY_CONSULTED`）、`engine._identity_independent` が持ち主のデッキのカードの id のすべての組で
  同じコマンドを確かめます（受け付けるか・拒否の種類とコード。理由の文に本当のカードを書かない）。組が 256 を超えたら `UNSUPPORTED_SECRET_PLAN_IDENTITIES`。この確かめを外して、
  本当のカードの結果で受け付けるかを決めないでください。

### 先読みのフォールバックの修正（v0.66 の文書 2.5 節）

- `flow.legacy_unknown_features` が、ワザを使うポケモンについているお上品攻撃（`reduces_attack_damage`）・場のうらのカードを見つけたら、上限を超えたときに v0.13 の止める関数で
  確かめず `UNSUPPORTED_PREFLIGHT_LIMIT`、比べる方法 legacy は `derived_full`、v0.13 の約束の実装は `UNSUPPORTED_LEGACY_PREFLIGHT`。v0.13 の止める関数が知らない選択・役割を
  加えたら、ここに加えてください。上限の数（`MAX_BRANCHES` = 4,096）を上げないでください。

### 決められない場合と変えていないもの

- 新しい停止コードは FD1（`UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY`）・FD2（`UNRESOLVED_SECRET_PLAN_MINEFIELD`。爆発ジム。出すと止める）の 2 件で、どちらも `not_in_kyuura`。
  ［へんしん］のメタモンが相手のうらのカードを写す場面は FD1 で止めます（v0.49 の TF2 と同じ形）。決定への答えがどれも FD1 なら、答えのない決定を残さずに、その前の状態で
  対戦を止めます（`Phase.HALTED`。`engine._apply`）。エンジンが止める `UNRESOLVED_…` は 147 件、未解決の裁定は 149 件です。
- 書き出しの形式 22 = 形式 21 + 最上位の `face_down_cards`（形式 1〜21 はうらのカードがあると `ValueError`）。監査の `LATEST_FORMAT` は 22。次の新しい形式は 23。
- 新しいコマンド `RevealFaceDown(player, pokemon)`・拒否のコード `NOT_FACE_DOWN`・決定の種類 `secret_plan_card`（観測の意味は `card`。出さない（0 個）がいつも答え）・
  ログのイベント `secret_plan_placed`（`card` は持ち主だけ）・`secret_plan_none`・`secret_plan_declined`・`secret_plan_revealed`・`secret_plan_discarded`・`secret_plan_target_lost`。

### 検証用デッキ

- 検証用デッキ `L67` と組 `PAIRINGS_V0_67`（`L67` 対 `C66`・`R65`・`S66`・`G64`）は tools/existing_effect_games.py の `--batch v0.67` です。前の版の組の結果は変わりません。
- 手順は `_v067_trainer`・`_v067_decision`・`_v067_reveal`、数えた結果は `v067_uses`。既存の手順で場のポケモンの定義を読むところは、うらのカードを飛ばします。
- 公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。

## ガルーラ・キョウのベトベトン・イマクニ？のドードーと、マチスの秘策の受け付けの修正（v0.68）

### 対象と数

- PMCG1〜PMCG6 の残りのポケモン 3 枚（ガルーラ PMCG2-046・キョウのベトベトン PMCG6-023・イマクニ？のドードー PMCG6-074）を、どのワザも、特殊能力も登録しました。
- 数の変化:

  | | v0.67 | v0.68 |
  |---|---|---|
  | 対応ポケモン | 350 | 353 |
  | トレーナー・エネルギー | 94・10 | 94・10 |
  | 写し・対応するカード | 456・454 枚 | 457・457 枚 |
  | ワザの登録 | 593 | 597 |
  | 特殊能力の登録 | 56 | 58 |
  | PMCG1〜PMCG6 の未対応 | 3 | 0 |

- 写しの組は `pool_v0_68`（キョウのベトベトン・イマクニ？のドードー。ガルーラは v0.34 の写しにあった）。`REFERENCE_ONLY` は空です。
- カードごとの結果・採用の仕様・簡略化した仕様・情報漏れの修正・未解決・検証は docs/final-pmcg-cards-v0.68.md。
- 公式ガイドブックのキャプチャ・OCR・読み直しは行っていません。テストの定数は tests/helpers.py の `KANGASKHAN`・`KOGAS_MUK`・`IMAKUNI_DODUO`・`V0_68_POKEMON`・`V0_68_CARDS`。

### ガルーラ（利用者が示した訂正）

- こどものおつかいの文面は、利用者が実物のカード画像で確かめたと示した訂正（「自分の山札の上からカードを1枚ひいて、手札に加える。」。コインなし）です。
  写しの作り直しの道具の `USER_PROVIDED_CORRECTIONS`（写しの `user_provided_corrections`。前の値・あとの値・`basis` `user_provided`・示した日・`engine_saw_image` False）で当てはめます。
- kyuura の確定した修正（v0.62 の `CONFIRMED_CORRECTIONS`。記録の id・修正のコミットを持つ）と混ぜないでください。記録の id・コミットを作らない・エラッタや別の版として扱わない・
  エンジンが画像を見たことにしないでください（`user_correction_problems` が拒否する）。写しを手で直さないでください。
- 処理: こどものおつかいは `DrawCardsAttack(1)`（コイン・乱数を使わない。山札が 0 枚なら引かず、負けにならない。p.312）、れんぞくパンチは `CoinFlipDamage(4, 20)`。
- 研究の対応表は `user_corrected_text`、採用の記録の `play_text` は `user_provided_correction`。

### キョウのベトベトン［だつりょくえき］（採用の仕様）

- DR1（自動的にはたらく。コインは必ず投げる。使わない選択はない）は kyuura の MIX-POWER-ERRATA・MIX-POWER-SPLIT を**この特殊能力に限って**採用した仕様です。
  2000.02.14 版の裁定として決まったことにしない・2002 年のほかの変更を持ち込まないでください。
- DR6（そのワザのすべての対象へのダメージのあと・ダメージ以外の効果の前）は p.89 の「こうらがえし」の解説からの類推で、採用の仕様です。公式に決まったことにしないでください。
- 登録の根拠は v0.17c の過去の原典照合の記録（`card_verification.json`。p.49）で、`card_sources.json` は `basis: guidebook_record`。処理に使う文面は p.49 の最新の説明（LD-PMCG6-023-PWR0）。
- 効果の定義は `catalog.ENERGY_DRAIN`（はんげきと同じ窓。DEFER）、処理は `kernel.drain_energy_from_damage_source`。受けるとき（`kernel.receiving`）に、相手のワザの分類のダメージ
  （返す効果のダメージを含む）で最終ダメージが 0 より大きいときだけ候補にします（どく・こんらん・特殊能力のダメージ・カウンターの移動ではない）。特殊状態・ガスは受けるときの
  状態で決め、どくは関係しない。バトル場でもベンチでもはたらき、そのダメージできぜつしてもはたらきます。ショックアイ（宣言して使う特殊能力の使用の禁止）では止まりません。
- 処理はダメージの要素のまとまりのあとの窓（`programs.fire_or_suspend`。`run_elements` が `fire_pending` を直接呼ばない）で、持ち主のコイン（ログ `energy_drain_check`）→「おもて」なら
  持ち主の決定 `energy_drain_discard`（ダメージを与えたポケモンのエネルギーカード。ちょうど 1 つ。`carry`）→ そのカードの持ち主のトラッシュ（ログ `energy_drain_discard`）。
  続きの情報は決定の `context` の `boundary`・`drain`・`frame`（v0.65 の要素のあいだの決定と同じ。`PendingDecision` に項目を加えない）。再開で宣言・コイン・ダメージ・送る効果・
  きぜつの判定をくり返さないでください。決定の形は `engine._reaction_decision_problems`。
- DR8（処理する時点でダメージを与えたポケモンが HP 以上）は `UNRESOLVED_ENERGY_DRAIN_ATTACKER_KNOCKED_OUT`、DR13（エネルギーカードがない）は `UNRESOLVED_ENERGY_DRAIN_NO_ENERGY`
  （どちらも `not_in_kyuura`。宣言の前の先読みが見つける）。DR18・DR19 は既存の C34/C35（`UNRESOLVED_MULTIPLE_DAMAGE_TRIGGERS`）。ダメージとダメージ以外の効果を交互に与える
  ワザの順番は変えていません（GK1 のまま）。v0.13 の約束の実装が自分で窓を開いて決定が要るときはエンジンの未対応 `UNSUPPORTED_ENERGY_DRAIN_DECISION`。v0.13 の止める関数は
  だつりょくえきを知らないので、`flow.legacy_unknown_features` が見つけます。

### イマクニ？のドードー（簡略化した仕様）

- 印刷の文面はデータのまま持ち、照合に使います。処理は簡略化した仕様（出典 `kyuura-engine docs/final-pmcg-cards-v0.68.md#4`。研究の対応表の `engine_simplified_text`）で、
  公式の裁定・エラッタではありません。
- ハモる（`SimplifiedSongDamage`）はすぐに 30 ダメージを与えるふつうのワザ（相手のワザとして使っても 30）。［にげまくり］（`SimplifiedRunAway`。宣言しない）は投げる動作を処理せず、
  にげるはふつうの「にげる」（にげるエネルギー 0）。
- この 2 つの型は、このカードの印刷の文面と同じときだけ登録できます。未対応のワザ・特殊能力を効果のないものとして受け付ける一般の仕組みにしないでください。

### マチスの秘策の受け付けの修正

- v0.67 の `engine._identity_independent` は、ありうるカードをうらのカードの持ち主の本当のデッキから作り、受け付けるかが見えないデッキの中身で変わっていました（利用者の再現例。
  docs 5 章）。
- v0.68 から、ありうるカードは公開の情報（対応しているカードの一覧。`engine._public_pool`）だけから作り、このコマンドが効果の対象として指定した（`zones.designate_face_down`・
  `reveal_face_down`。`zones.IDENTITY_ORACLE` が割り当てる）相手のうらのカードだけを、指定した順に試します。たねポケモンでないカードは、トラッシュしたあとに項目を読まなければ
  1 回だけ試します。試す回数の上限は 512 で、2 枚以上を指定するコマンドは `UNSUPPORTED_SECRET_PLAN_IDENTITIES`（エンジンの未対応。公開の情報だけで決まる）。
- デッキ・山札・手札の中身で、受け付けるか・拒否の種類・コード・理由の文を変えないでください。理由の文から数を除くだけ・両方を拒否する直し方にしないでください。
  公式の未解決の裁定ではありません（研究の対応表の停止コードに入れない）。
- 2 枚以上を指定するコマンドは、v0.67 では見えないデッキの種類が少なければ受け付けていたもの（化石の秘密のゴローニャのじばくなど）も、v0.68 では受け付けません（実装の制限。
  自然な対戦でも起こる。対戦の手順は `V031_STOPS` で場から確かめて別の操作を続ける）。
- うらのカードを指定する経路を加えるときは、`zones.designate_face_down` を通してください（割り当てる前のうらのカードを読むとエンジンの不具合として止まる）。

### 変えていないもの

- 書き出しの形式は 22 のまま（次の新しい形式は 23）。公開の API の呼び方・コマンドも変えていません。
- 新しい決定の種類は `energy_drain_discard`（観測の意味は `card`）、新しいログのイベント（公開）は `energy_drain_check`・`energy_drain_discard`。
- エンジンが止める `UNRESOLVED_…` は 149 件、未解決の裁定は 151 件です。

### 検証用デッキ

- 検証用デッキ `K68` と組 `PAIRINGS_V0_68`（`K68` 対 `R65`・`C66`・`L67`・`P31`）は tools/existing_effect_games.py の `--batch v0.68` です。前の版の組の結果は変わりません。
- イマクニ？のドードーの「にげる」は `_v068_retreat`、数えた結果は `v068_uses`。だつりょくえきの決定には元の手順が答えます。
- 公開の固定のデッキ・既存の変種には入れていません。勝敗で採用を判断しないでください。
