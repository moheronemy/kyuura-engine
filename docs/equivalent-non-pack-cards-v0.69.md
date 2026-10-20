# v0.69: kyuura の形式 3 のカードデータへの移行と、拡張パック以外の商品の同じカード 96 枚

v0.68（`24bfbe2`）から作業しました。ブランチは `claude/v0.69-equivalent-non-pack-cards` です。作業は 2 段階に分けました。

- **A（移行）**: 写しの元と研究の基準を kyuura `7d3f4ca76c084774efb4ac6a1d3a943387e183c3`（kyuura の main。形式 3 のカードデータと、v0.68 までのエンジンの記録を取り込んだ研究の記録）に上げた。対応するカードは増やさず、v0.68 の 457 枚の動きが同じことを確かめた（2 章・6 章）。
- **B（登録）**: kyuura の `data/engine_targets.json` の `engine_status` が `mechanically_equivalent` の記録 96 枚を、元のカードの登録を写して登録した（3 章〜5 章）。

公式ガイドブック（『オフィシャルブック2000』）のキャプチャ・OCR・読み直しはしていません。pcg-search.com も、この作業では開いていません（96 枚の外部照合はしていない。4 章）。kyuura は変えていません。

## 1. 数

数は効果の登録表と写しから数え直しました（tests/test_equivalent_non_pack_cards_v0_69.py `TableTest.test_counts`）。依頼の見込みの数と同じです。

| | v0.68 | v0.69 |
|---|---|---|
| 写しのカード・対応するカード | 457・457 | 553・553 |
| 対応ポケモン | 353 | 410 |
| トレーナー | 94 | 113 |
| エネルギー（基本・特殊） | 10（6・4） | 30（18・12） |
| ワザの登録 | 597 | 689 |
| 特殊能力の登録 | 58 | 68 |
| 特殊エネルギーの登録 | 4 | 12 |
| 書き出しの形式 | 22 | 22 |
| エンジンが止める `UNRESOLVED_…` | 149 | 149 |
| 未解決の裁定 | 151 | 151 |
| 版 | 0.68.0 | 0.69.0 |

96 枚の内訳は、ポケモンジム（GD1〜GD6）52 枚、イントロパック（IP1・IP2）14 枚、プロモーション（PR1）20 枚、2001 年のイントロパック（NIP1・NIP1X・NIP2）10 枚です。種類では、ポケモン 57 枚・トレーナー 19 枚・エネルギー 20 枚（基本エネルギー 12 枚・無色2個エネルギー 8 枚）です。

数はほかとまとめていません。kyuura の論点（UQ-）は 71 件、エンジンの未解決の裁定は 151 件、停止コードは 149 件で、同じ論点を指す停止コードもそれぞれ数えます。

## 2. 写しの移行（A）

### 2.1 写しの元と、写す欄

- `scripts/extract_kyuura_cards.py` の `KYUURA_COMMIT` を `7d3f4ca` にした。v0.68 までの写しの元（`ecb2d69`）は `PREVIOUS_KYUURA_COMMIT` として残し、書き出すたびに比べる（2.3 節）。
- kyuura のカードデータは形式 3（`schema_version` 3、1,377 件）になった。写しに加えた欄は次のとおり（出典の確認用。エンジンの処理には使わない）。
  - いつもある欄: `product_group`（商品の種類）・`play_scope`（使える範囲）・`data_gaps`（欠けている欄）・`same_card_group`（商品をまたいだ同じカードの組）
  - あるときだけある欄（`fields_copied_when_present`。ないときは写しにも書かない）: `field_sources`（欄の出どころ）・`copies`（同じカードの別のページ）・`corrections`（kyuura が当てはめた修正の記録）
  - 写さない欄: `seq`・`rarity_jp`・`en_print`・`en_reprints`（処理にも出典の確かめにも使わない）
- 書き出しの形式の名前は `kyuura-engine card extract 1` のままです。項目を加えただけで、読む側（`kyuura_engine/cards.py`）は加えた項目を読みません。
- 書き出しに加えた最上位の項目: `fields_copied_when_present`・`previous_source`（前の写しの元と、比べたときに変わってよい欄）・`kyuura_corrections`（2.2 節）・`equivalent_targets`（kyuura の `engine_targets.json` の `mechanically_equivalent` の記録の写し。3 章）。外した項目: `corrections`（v0.62）・`user_provided_corrections`（v0.68）。
- 写しの組の鍵は 1 か所（`POOLS`）にまとめた。並びと中身は v0.68 までと同じで、最後に `pool_v0_69` を加えた（`kyuura_engine/cards.py` の `POOL_KEYS` にも加えた）。
- 写しは手で直していません。`python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura` で作り直しました。写しに入れたのは対戦用の組（553 枚）だけで、kyuura のほかの記録（824 件）は写していません。

### 2.2 二重の修正をしない

v0.62 と v0.68 は、写しの元（`ecb2d69`）の値に、エンジンが修正を当てはめていました。kyuura は `7d3f4ca` で同じ修正を `data/cards.json` に当てはめ、台帳（`data/curation/card_corrections.json`）に記録しました。エンジンは修正を当てはめ直さず、台帳を確かめます（`KYUURA_CORRECTIONS`・`kyuura_correction_problems`）。

| 台帳の記録 | カード・欄 | 前 → あと | 根拠 | v0.68 までのエンジン |
|---|---|---|---|---|
| FIX-PMCG2-041-ATK0-NAME | ベロリンガ PMCG2-041 `pokemon.attacks[0].name.ja` | したでなめる → まきつくベロ | kyuura の照合（CC-PMCG2-041-P234・修正のコミット `f52a8e2`） | `CONFIRMED_CORRECTIONS`（v0.62） |
| FIX-PMCG2-041-LEVEL | ベロリンガ PMCG2-041 `jp_print.level` | 29 → 26 | 同上 | 同上 |
| FIX-PMCG2-046-ATK0-TEXT | ガルーラ PMCG2-046 `pokemon.attacks[0].text.ja` | 「コインを投げて「おもて」なら、」を除く | 利用者が示した訂正（`user_provided`。kyuura も画像を見ていない） | `USER_PROVIDED_CORRECTIONS`（v0.68） |

書き出すたびに確かめること（どれかが違えば書き出さない）:

- 台帳とカードの記録の `corrections` に、同じ id・欄・前・あと・根拠の記録がある
- `7d3f4ca` の値が「あと」、`ecb2d69` の値が「前」（修正が当てはまっていて、二重に当てはめていない）
- kyuura の照合の修正は、照合の記録の `corrections` に同じ修正があり、修正のコミットが `ecb2d69` のあと・`7d3f4ca` の前にある
- 利用者が示した訂正は、照合の記録・修正のコミットを書かず、kyuura もエンジンも画像を見ていない（`kyuura_saw_image`・`engine_saw_image` は False）
- 写しのカードに、ここに挙げていない台帳の修正がない（知らない修正を黙って受け入れない）

ガルーラの文面の出どころは変わりません。利用者が示した転記の誤りの訂正で、公式エラッタ・別の版の文面・画像の読み直しではありません。登録の根拠の名前（`user_provided_correction`）も変えていません。出典の文字列を `kyuura data/cards.json + data/curation/card_corrections.json (user_provided)` にし、研究の対応表の `user_corrected_text` を台帳の記録（`kyuura data/curation/card_corrections.json#FIX-PMCG2-046-ATK0-TEXT`）に結びました。

### 2.3 v0.68 の 457 枚の比較

`ecb2d69` と `7d3f4ca` の 457 枚を、v0.68 の写す欄で比べました（`previous_copy_problems`。書き出すたびに確かめる）。台帳の修正の欄を当てはめると、処理に使う欄はすべて同じです。違ったのは出典の記録の欄だけです。

| 欄 | 違ったカード | 中身 |
|---|---|---|
| `source_ids` | 457 枚すべて | `pcg_search`（pcg-search.com のページ）を加えた |
| `notes` | ベロリンガ PMCG2-041・ガルーラ PMCG2-046 | 修正の記録を書き足した |
| `ja_text_source` | ベロリンガ PMCG2-041 | 日本語の文面の出典を p.234 にした |
| `jp_en_differences` | キョウのベトベトン PMCG6-023 | だつりょくえきの英語版の記録 |

加えた欄（`product_group` など）はどのカードでも新しい値です。

## 3. 96 枚の対応

### 3.1 対象

- kyuura の `data/engine_targets.json`（`7d3f4ca`）の `engine_status` が `mechanically_equivalent` の記録の**すべて**です。種類（`category`）でしぼっていません。無色2個エネルギー 8 枚は日本語の説明が欠けているので `data_missing` です。
- 書き出すたびに、`POOL_V0_69` が `engine_targets.json` の `mechanically_equivalent` のすべて（並びも）と同じことを確かめます（`equivalent_target_problems`）。
- 対応する元のカード（`equivalent_to`）は、どれもちょうど 1 枚で、v0.68 で登録したカードです。kyuura の同じカードの組（`same_card_group`）も、96 枚すべてで元のカードと同じです。
- kyuura の `engine_targets.json` は作り直していません（kyuura の作業）。

### 3.2 登録の写し方

- `kyuura_engine/effects.py` の `EQUIVALENT_CARDS`（84 枚。新しい id → 元のカードの id）と `_with_equivalent_cards` が、元のカードの登録（ワザ・特殊能力・トレーナー・特殊エネルギー）を新しい id ごとに写します。登録の値は元のカードと同じもの（効果の実装・照合した文面・処理に使う文面・出典）です。
- 基本エネルギー 12 枚は登録がない（公式ルールの規定だけで扱う）ので、`EQUIVALENT_BASIC_ENERGY` に対応だけを書きました。
- 同じ名前のカードを自動で対応させていません。表に書いたカードだけです。
- `_with_equivalent_cards` は、元のカードに登録がない・新しい id にすでに登録がある・元のカードがほかのカードの写し、のどれかで `RuntimeError` にします。
- 登録の照合（名前・説明文・実装の `check`）は、新しい id のデータでも行います。新しい id のデータが違えば、そのカードは未対応になります（`ParityTest.test_data_mismatch_makes_the_card_unsupported`）。
- `engine.py`・`resolution/` にカード id の分岐はありません。状態・ログ・書き出しには新しい id と uid をそのまま持ちます（元の id に置きかえない）。
- 効果の登録表の id は `kyuura-engine-0.13` のままです。

### 3.3 比べた欄

96 枚すべてで、元のカードと次の欄が同じことを確かめました（`ParityTest`。`scripts/check_card_sources.py` の `engine_view` と、写しから作ったカードの定義）。

- ポケモン: 段階・進化元・HP・タイプ・弱点・抵抗力・にげる・ルールの文・特殊能力（種類・名前・説明）・ワザ（名前・エネルギー・ダメージ・説明）
- トレーナー: 種類・説明
- エネルギー: 種類・出すもの・説明

英語の欄・図鑑番号・レベル・レアリティは比べていません（処理に使わない）。

### 3.4 一覧

「登録」の欄は、新しい id の登録（元のカードと同じもの）と、処理に使う文面のあるワザ・特殊能力の、元のカードの根拠の区分（研究の対応表 `research_links.json` の `latest_descriptions` の区分）です。

| 新しい id | 名前 | 商品 | 発売 | 元のカード | 種類 | 登録（元のカードの根拠の区分） |
|---|---|---|---|---|---|---|
| GD1-002 | タケシのロコン | ポケモンジム第1弾「ニビシティジム タケシ」 | 1998-04-26 | PMCG5-018 | ポケモン | attack/0・attack/1（adopted_printed_text） |
| GD1-009 | タケシのゴローニャ | ポケモンジム第1弾「ニビシティジム タケシ」 | 1998-04-26 | PMCG5-053 | ポケモン | attack/0（adopted_printed_text）・attack/1 |
| GD1-011 | タケシのイワーク | ポケモンジム第1弾「ニビシティジム タケシ」 | 1998-04-26 | PMCG5-048 | ポケモン | attack/0（adopted_printed_text）・attack/1 |
| GD1-013 | タケシのサイドン | ポケモンジム第1弾「ニビシティジム タケシ」 | 1998-04-26 | PMCG5-055 | ポケモン | attack/0（adopted_printed_text）・power/0（adopted_printed_text） |
| GD1-015 | 思い出させる | ポケモンジム第1弾「ニビシティジム タケシ」 | 1998-04-26 | PMCG5-071 | トレーナー | trainer |
| GD1-019 | タケシの育て方 | ポケモンジム第1弾「ニビシティジム タケシ」 | 1998-04-26 | PMCG5-077 | トレーナー | trainer |
| GD1-025 | 無色2個エネルギー | ポケモンジム第1弾「ニビシティジム タケシ」 | 1998-04-26 | PMCG1-096 | エネルギー | energy |
| GD2-004 | カスミのドククラゲ | ポケモンジム第1弾「ハナダシティジム カスミ」 | 1998-04-26 | PMCG5-033 | ポケモン | attack/0（adopted_printed_text）・power/0（registered_without_kyuura_record） |
| GD2-008 | カスミのタッツー | ポケモンジム第1弾「ハナダシティジム カスミ」 | 1998-04-26 | PMCG5-025 | ポケモン | attack/0・attack/1（adopted_printed_text） |
| GD2-010 | カスミのトサキント | ポケモンジム第1弾「ハナダシティジム カスミ」 | 1998-04-26 | PMCG5-026 | ポケモン | attack/0（adopted_printed_text）・attack/1（adopted_printed_text） |
| GD2-012 | カスミのヒトデマン | ポケモンジム第1弾「ハナダシティジム カスミ」 | 1998-04-26 | PMCG5-027 | ポケモン | attack/0（registered） |
| GD2-015 | カスミ | ポケモンジム第1弾「ハナダシティジム カスミ」 | 1998-04-26 | PMCG5-085 | トレーナー | trainer |
| GD2-016 | カスミのいかり | ポケモンジム第1弾「ハナダシティジム カスミ」 | 1998-04-26 | PMCG5-075 | トレーナー | trainer |
| GD2-017 | カスミの勝負 | ポケモンジム第1弾「ハナダシティジム カスミ」 | 1998-04-26 | PMCG5-068 | トレーナー | trainer |
| GD2-018 | カスミのなみだ | ポケモンジム第1弾「ハナダシティジム カスミ」 | 1998-04-26 | PMCG5-069 | トレーナー | trainer |
| GD2-024 | 無色2個エネルギー | ポケモンジム第1弾「ハナダシティジム カスミ」 | 1998-04-26 | PMCG1-096 | エネルギー | energy |
| GD3-001 | マチスのピカチュウ | ポケモンジム第2弾「クチバシティジム マチス」 | 1998-07-25 | PMCG5-036 | ポケモン | attack/0（adopted_printed_text） |
| GD3-004 | マチスのコイル | ポケモンジム第2弾「クチバシティジム マチス」 | 1998-07-25 | PMCG5-039 | ポケモン | attack/0（adopted_printed_text）・attack/1（adopted_printed_text） |
| GD3-005 | マチスのコイル | ポケモンジム第2弾「クチバシティジム マチス」 | 1998-07-25 | PMCG5-037 | ポケモン | attack/0（adopted_printed_text）・attack/1 |
| GD3-006 | マチスのレアコイル | ポケモンジム第2弾「クチバシティジム マチス」 | 1998-07-25 | PMCG5-040 | ポケモン | attack/0（adopted_printed_text）・power/0（adopted_printed_text） |
| GD3-007 | マチスのビリリダマ | ポケモンジム第2弾「クチバシティジム マチス」 | 1998-07-25 | PMCG5-038 | ポケモン | attack/0（adopted_printed_text）・attack/1（adopted_printed_text） |
| GD3-015 | エネルギーサーキュレート | ポケモンジム第2弾「クチバシティジム マチス」 | 1998-07-25 | PMCG5-067 | トレーナー | trainer |
| GD3-016 | スパイ作戦 | ポケモンジム第2弾「クチバシティジム マチス」 | 1998-07-25 | PMCG5-088 | トレーナー | trainer |
| GD3-021 | マチス | ポケモンジム第2弾「クチバシティジム マチス」 | 1998-07-25 | PMCG5-092 | トレーナー | trainer |
| GD3-022 | マチスの交渉 | ポケモンジム第2弾「クチバシティジム マチス」 | 1998-07-25 | PMCG5-081 | トレーナー | trainer |
| GD3-025 | 無色2個エネルギー | ポケモンジム第2弾「クチバシティジム マチス」 | 1998-07-25 | PMCG1-096 | エネルギー | energy |
| GD4-002 | エリカのナゾノクサ | ポケモンジム第2弾「タマムシシティジム エリカ」 | 1998-07-25 | PMCG5-002 | ポケモン | attack/0（adopted_printed_text）・attack/1（adopted_printed_text） |
| GD4-006 | エリカのマダツボミ | ポケモンジム第2弾「タマムシシティジム エリカ」 | 1998-07-25 | PMCG5-005 | ポケモン | attack/0（adopted_printed_text） |
| GD4-008 | エリカのウツボット | ポケモンジム第2弾「タマムシシティジム エリカ」 | 1998-07-25 | PMCG5-015 | ポケモン | attack/0・power/0（adopted_printed_text） |
| GD4-010 | エリカのナッシー | ポケモンジム第2弾「タマムシシティジム エリカ」 | 1998-07-25 | PMCG5-013 | ポケモン | attack/0（adopted_printed_text）・attack/1（adopted_printed_text） |
| GD4-011 | エリカのモンジャラ | ポケモンジム第2弾「タマムシシティジム エリカ」 | 1998-07-25 | PMCG5-006 | ポケモン | attack/0・attack/1（adopted_printed_text） |
| GD4-013 | エリカのミニリュウ | ポケモンジム第2弾「タマムシシティジム エリカ」 | 1998-07-25 | PMCG5-063 | ポケモン | attack/0（adopted_printed_text）・power/0（adopted_printed_text） |
| GD4-016 | エリカ | ポケモンジム第2弾「タマムシシティジム エリカ」 | 1998-07-25 | PMCG5-083 | トレーナー | trainer |
| GD4-017 | エリカのお付き | ポケモンジム第2弾「タマムシシティジム エリカ」 | 1998-07-25 | PMCG5-072 | トレーナー | trainer |
| GD4-018 | エリカの香水 | ポケモンジム第2弾「タマムシシティジム エリカ」 | 1998-07-25 | PMCG5-073 | トレーナー | trainer |
| GD4-026 | 礼儀作法 | ポケモンジム第2弾「タマムシシティジム エリカ」 | 1998-07-25 | PMCG5-082 | トレーナー | trainer |
| GD4-028 | 無色2個エネルギー | ポケモンジム第2弾「タマムシシティジム エリカ」 | 1998-07-25 | PMCG1-096 | エネルギー | energy |
| GD5-002 | カツラのロコン | ポケモンジム第3弾「グレンタウンジム カツラ」 | 1999-02-26 | PMCG6-026 | ポケモン | attack/0（adopted_printed_text）・power/0（adopted_printed_text） |
| GD5-004 | カツラのキュウコン | ポケモンジム第3弾「グレンタウンジム カツラ」 | 1999-02-26 | PMCG6-033 | ポケモン | attack/0（adopted_printed_text）・power/0（adopted_printed_text） |
| GD5-009 | カツラのポニータ | ポケモンジム第3弾「グレンタウンジム カツラ」 | 1999-02-26 | PMCG6-028 | ポケモン | attack/0（adopted_printed_text） |
| GD5-010 | カツラのギャロップ | ポケモンジム第3弾「グレンタウンジム カツラ」 | 1999-02-26 | PMCG6-030 | ポケモン | attack/0・attack/1（adopted_printed_text） |
| GD5-012 | カツラのドードー | ポケモンジム第3弾「グレンタウンジム カツラ」 | 1999-02-26 | PMCG6-064 | ポケモン | attack/0（adopted_printed_text）・attack/1（adopted_printed_text） |
| GD5-014 | カツラ | ポケモンジム第3弾「グレンタウンジム カツラ」 | 1999-02-26 | PMCG6-093 | トレーナー | trainer |
| GD5-015 | カツラのギャンブル | ポケモンジム第3弾「グレンタウンジム カツラ」 | 1999-02-26 | PMCG6-076 | トレーナー | trainer |
| GD5-025 | 無色2個エネルギー | ポケモンジム第3弾「グレンタウンジム カツラ」 | 1999-02-26 | PMCG1-096 | エネルギー | energy |
| GD6-003 | ナツメのユンゲラー | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | 1999-02-26 | PMCG6-047 | ポケモン | attack/0（adopted_printed_text）・attack/1 |
| GD6-004 | ナツメのフーディン | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | 1999-02-26 | PMCG6-053 | ポケモン | attack/0（adopted_printed_text）・power/0（adopted_printed_text） |
| GD6-013 | ナツメのポリゴン | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | 1999-02-26 | PMCG6-066 | ポケモン | attack/0・attack/1（adopted_printed_text） |
| GD6-017 | ナツメ | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | 1999-02-26 | PMCG6-098 | トレーナー | trainer |
| GD6-018 | ナツメのESP | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | 1999-02-26 | PMCG6-087 | トレーナー | trainer |
| GD6-019 | ナツメの眼 | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | 1999-02-26 | PMCG6-078 | トレーナー | trainer |
| GD6-026 | 無色2個エネルギー | ポケモンジム第3弾「ヤマブキシティジム ナツメ」 | 1999-02-26 | PMCG1-096 | エネルギー | energy |
| IP1-002 | スリープ | イントロパック(フシギダネデッキ) | 1999-07-30 | PMCG1-045 | ポケモン | attack/0・attack/1（recorded_in_card_checks） |
| IP1-004 | 草エネルギー | イントロパック(フシギダネデッキ) | 1999-07-30 | PMCG1-097 | エネルギー | なし（基本エネルギー） |
| IP1-006 | 雷エネルギー | イントロパック(フシギダネデッキ) | 1999-07-30 | PMCG1-100 | エネルギー | なし（基本エネルギー） |
| IP1-013 | ピカチュウ | イントロパック(フシギダネデッキ) | 1999-07-30 | PMCG1-035 | ポケモン | attack/0・attack/1（recorded_in_card_checks） |
| IP1-023 | 無色2個エネルギー | イントロパック(フシギダネデッキ) | 1999-07-30 | PMCG1-096 | エネルギー | energy |
| IP1-024 | 超エネルギー | イントロパック(フシギダネデッキ) | 1999-07-30 | PMCG1-101 | エネルギー | なし（基本エネルギー） |
| IP2-001 | ガーディ | イントロパック(ゼニガメデッキ) | 1999-07-30 | PMCG1-018 | ポケモン | attack/0 |
| IP2-002 | ディグダ | イントロパック(ゼニガメデッキ) | 1999-07-30 | PMCG1-052 | ポケモン | attack/0・attack/1 |
| IP2-004 | 炎エネルギー | イントロパック(ゼニガメデッキ) | 1999-07-30 | PMCG1-098 | エネルギー | なし（基本エネルギー） |
| IP2-005 | 水エネルギー | イントロパック(ゼニガメデッキ) | 1999-07-30 | PMCG1-099 | エネルギー | なし（基本エネルギー） |
| IP2-012 | 闘エネルギー | イントロパック(ゼニガメデッキ) | 1999-07-30 | PMCG1-102 | エネルギー | なし（基本エネルギー） |
| IP2-014 | プリン | イントロパック(ゼニガメデッキ) | 1999-07-30 | PMCG2-035 | ポケモン | attack/0（recorded_in_card_checks）・attack/1 |
| IP2-025 | 無色2個エネルギー | イントロパック(ゼニガメデッキ) | 1999-07-30 | PMCG1-096 | エネルギー | energy |
| IP2-035 | ワンリキー | イントロパック(ゼニガメデッキ) | 1999-07-30 | PMCG1-053 | ポケモン | attack/0 |
| PR1-019 | わるいペルシアン | プロモ(旧裏) | 1997-11-18 | PMCG4-048 | ポケモン | attack/0（adopted_printed_text）・attack/1（adopted_printed_text） |
| PR1-031 | カスミのヒトデマン | プロモ(旧裏) | 1998-02-15 | PMCG5-027 | ポケモン | attack/0（registered） |
| PR1-032 | タケシのイワーク | プロモ(旧裏) | 1998-02-15 | PMCG5-048 | ポケモン | attack/0（adopted_printed_text）・attack/1 |
| PR1-039 | エリカのミニリュウ | プロモ(旧裏) | 1998-07-15 | PMCG5-063 | ポケモン | attack/0（adopted_printed_text）・power/0（adopted_printed_text） |
| PR1-047 | エリカのフシギダネ | プロモ(旧裏) | 1998-11-15 | PMCG5-007 | ポケモン | attack/0（adopted_printed_text）・attack/1（adopted_printed_text） |
| PR1-048 | カスミのメノクラゲ | プロモ(旧裏) | 1998-11-15 | PMCG5-030 | ポケモン | attack/0（adopted_printed_text） |
| PR1-049 | タケシのマンキー | プロモ(旧裏) | 1998-11-15 | PMCG5-045 | ポケモン | attack/0（adopted_printed_text）・attack/1（adopted_printed_text） |
| PR1-050 | マチスのサンダース | プロモ(旧裏) | 1998-11-15 | PMCG5-042 | ポケモン | attack/0（adopted_printed_text）・attack/1（adopted_printed_text） |
| PR1-061 | マンキー | プロモ(旧裏) | 1999-05-22 | PMCG2-028 | ポケモン | attack/0・power/0（adopted_printed_text） |
| PR1-076 | コダック | プロモ(旧裏) | 1999-09-22 | PMCG3-010 | ポケモン | attack/0（adopted_printed_text）・attack/1（adopted_printed_text） |
| PR1-080 | ギャラドス | プロモ(旧裏) | 1999 | PMCG1-034 | ポケモン | attack/0・attack/1（adopted_printed_text） |
| PR1-081 | ピカチュウ | プロモ(旧裏) | 1999 | PMCG1-035 | ポケモン | attack/0・attack/1（recorded_in_card_checks） |
| PR1-082 | ニョロモ | プロモ(旧裏) | 1999 | PMCG1-024 | ポケモン | attack/0（adopted_printed_text） |
| PR1-083 | フシギダネ | プロモ(旧裏) | 1999 | PMCG1-001 | ポケモン | attack/0（registered） |
| PR1-084 | コイキング | プロモ(旧裏) | 1999 | PMCG1-031 | ポケモン | attack/0・attack/1（adopted_printed_text） |
| PR1-085 | ゼニガメ | プロモ(旧裏) | 1999 | PMCG1-023 | ポケモン | attack/0（recorded_in_card_checks）・attack/1（registered） |
| PR1-086 | ドガース | プロモ(旧裏) | 1999 | PMCG1-006 | ポケモン | attack/0（adopted_printed_text） |
| PR1-087 | ラッキー | プロモ(旧裏) | 1999 | PMCG1-068 | ポケモン | attack/0（registered）・attack/1（recorded_in_card_checks） |
| PR1-088 | フリーザー | プロモ(旧裏) | 1999 | PMCG3-023 | ポケモン | attack/0（adopted_printed_text）・attack/1（adopted_printed_text） |
| PR1-089 | ヒトカゲ | プロモ(旧裏) | 1999 | PMCG1-014 | ポケモン | attack/0・attack/1（errata_text） |
| NIP1-003 | 草エネルギー | イントロパック★neo(チコリータデッキ) | 2001-04-06 | PMCG1-097 | エネルギー | なし（基本エネルギー） |
| NIP1-005 | 炎エネルギー | イントロパック★neo(チコリータデッキ) | 2001-04-06 | PMCG1-098 | エネルギー | なし（基本エネルギー） |
| NIP1-006 | 闘エネルギー | イントロパック★neo(チコリータデッキ) | 2001-04-06 | PMCG1-102 | エネルギー | なし（基本エネルギー） |
| NIP1-010 | ドガース | イントロパック★neo(チコリータデッキ) | 2001-04-06 | PMCG4-005 | ポケモン | attack/0・attack/1（adopted_printed_text） |
| NIP1-012 | ガーディ | イントロパック★neo(チコリータデッキ) | 2001-04-06 | PMCG1-018 | ポケモン | attack/0 |
| NIP1X-003 | ワンリキー | イントロパック★neo(チコリータデッキ：拡張カード) | 2001-04-06 | PMCG4-040 | ポケモン | attack/0・attack/1 |
| NIP2-001 | ピカチュウ | イントロパック★neo(ワニノコデッキ) | 2001-04-06 | PMCG1-035 | ポケモン | attack/0・attack/1（recorded_in_card_checks） |
| NIP2-005 | 水エネルギー | イントロパック★neo(ワニノコデッキ) | 2001-04-06 | PMCG1-099 | エネルギー | なし（基本エネルギー） |
| NIP2-006 | 雷エネルギー | イントロパック★neo(ワニノコデッキ) | 2001-04-06 | PMCG1-100 | エネルギー | なし（基本エネルギー） |
| NIP2-007 | 超エネルギー | イントロパック★neo(ワニノコデッキ) | 2001-04-06 | PMCG1-101 | エネルギー | なし（基本エネルギー） |

## 4. 根拠と記録

### 4.1 採用の記録

84 枚（基本エネルギーを除く）に、`card_sources.json` の採用の記録を置きました。

- `basis` は `kyuura_data`、`status` は `adopted`、`kyuura_commit` は `7d3f4ca`（採用したデータのコミット）、`recorded_on` は 2026-10-19。
- 新しい項目 `equivalent_to` に元のカードを書き、`play_text` の値はどれも `equivalent_registration` です。処理に使う文面の根拠は、元のカードの根拠（元のカードの記録・研究の対応表の区分）です。
- `external_checks` は空です。新しい id のカードの画像・pcg-search.com のページは照合していません。元のカードの照合の記録（CC-）・最新の説明（LD-）を、新しい商品のカードを照合したものとして写していません。
- `kyuura_records` は、研究の基準のコミットで新しい id を指す kyuura の記録の id です（96 枚とも、kyuura に新しい id を指す記録はなかった）。
- 基本エネルギー 12 枚には記録を置いていません（登録がない。v0.68 までの基本エネルギーと同じ）。

`scripts/check_card_sources.py` の `equivalent_problems` が確かめること:

- `effects.EQUIVALENT_CARDS` と写しの `equivalent_targets` の元のカードが、記録の `equivalent_to` と同じ
- 元のカードに登録の根拠（過去の原典照合の記録か採用の記録）がある
- 写しの処理に使う欄（日本語）と同じカードの組が、元のカードと同じ
- 登録が元のカードの登録と同じもの（`is`）
- `play_text` が、処理に使う文面のある登録のすべてで `equivalent_registration`
- 外部照合を書いていない
- 研究の対応表の `equivalent_registrations` に、ワザ・特殊能力の登録がある

### 4.2 最新の説明・エラッタは再録にも当てはまるか

元のカードの最新の説明（LD-）・エラッタ（ERR-・TXT-・RUL-）・kyuura の日英の違いの記録は、カード id ごとの記録です。新しい id にも当てはめるのは、次の 2 つが研究の基準のコミットで確かめられるときだけです（`scripts/check_research_links.py` の 4g）。

- 新しい id と元のカードが、kyuura の同じカードの組（`same_card_group`）にある
- 新しい id の印刷の文面が、元のカードの印刷の文面と同じ

たとえば、カスミのヒトデマンの新しい id（GD2-012・PR1-031）のスターブーメランは、元のカード（PMCG5-027）の最新の説明 LD-PMCG5-027-ATK0 にしたがいます。研究の対応表の `equivalent_registrations` は 74 件（ワザ・特殊能力で、処理に使う文面のあるもの）です。トレーナー・特殊エネルギーの登録も元のカードと同じものです。

### 4.3 無色2個エネルギーの新しい id（8 枚）

- kyuura の日本語の説明は null（`data_gaps` に `energy.text.ja`）です。説明の文面を作っていません。
- 登録は v0.58 の `ColorlessUnitsByName(2)`（出典 `DCE_SOURCE`）と同じものです。根拠は、名前（無色2個エネルギー）・種類（特殊エネルギー）・個数（無色 2 個）が元のカード PMCG1-096 と同じことです。PMCG1-096 の記号の照合（pcg-search.com 1st1096）を、新しい id の版の照合として数えていません。
- 1 枚で無色 2 個（カードの枚数と個数を分ける）・ワザとにげるの支払い・基本エネルギーカードではない（エネルギー回収などの対象にならない）ことを、新しい id で確かめました（`DoubleColorlessTest`・`DceUnitsReprintTest`・`DceRetreatReprintTest`）。

### 4.4 2001 年に発売したカード（10 枚）

NIP1-003・NIP1-005・NIP1-006・NIP1-010・NIP1-012・NIP1X-003・NIP2-001・NIP2-005・NIP2-006・NIP2-007 は、2001-04-06 に発売したイントロパック（neo）のカードです。

- 発売日は kyuura の記録（2001-04-06）のまま持ちます。2000.02.14 版までに発売したカードとは扱いません（採用の記録の `notes` に書いた）。
- 処理は元のカードと同じで、2000.02.14 版のルールで扱います。のちのルール・ベイビィのルールを持ち込んでいません（10 枚ともベイビィではない）。

### 4.5 同じ名前の 4 枚の制限・進化

- 同じ名前の 4 枚の制限は、id をまたいで名前で数えます（v0.1 からの `deck_problems` のまま）。基本エネルギーは制限なし。無色2個エネルギーも名前で 4 枚まで（`DeckTest`）。
- 進化は名前と段階で決まります（商品によらない）。たとえば ナツメのケーシィ（PMCG6-043）→ ナツメのユンゲラー（GD6-003）→ ナツメのフーディン（PMCG6-053）（`MixedEvolutionTest`）。

## 5. マチスの秘策の受け付けるかの確かめ

v0.68 の確かめ（`engine._identity_independent`）は、ありうるカードを対応しているカードの一覧から作り、1 枚ずつ試します（試す回数の上限 512）。対応しているカードが 553 枚になると、たねポケモンでないカードを 1 枚ずつ試す場面で回数が上限を超え、v0.68 で受け付けていたコマンドを受け付けなくなります。

- v0.69 から、処理が同じカードを 1 枚で代表します（`engine._identity_candidates`・`_behavior_key`）。処理が同じとは、カードの定義が id と英語の欄を除いて同じで、効果の登録表のそのカードの登録が同じもの（`is`）であることです。代表は、写しの表（`EQUIVALENT_CARDS`・`EQUIVALENT_BASIC_ENERGY`）の新しい id でないカードです。
- 試すカードは v0.68 と同じ 457 枚（同じ並び）です。公開の情報（対応しているカードの一覧と効果の登録表）だけで決まり、見えないデッキの中身によりません。
- 2 枚以上を指定するコマンドの制限（`UNSUPPORTED_SECRET_PLAN_IDENTITIES`）と上限の数（512）は変えていません。
- カツラのクイズ その3の答えの候補（`quiz_answer_names`）は名前の集まりなので、新しい id で同じ名前が重なりません。

## 6. 互換性

### 6.1 状態の写しの元

状態は写しの元を `card_data.commit`（`state_to_dict`）とログ `game_created` の `card_data_commit` に持ちます。写しの元を上げたので、新しい対戦の状態・ログ・指紋は、この 2 か所が変わります。

- 固定の参照データ（tests/fixtures/v0_1_reference.json・tests/test_reproducibility.py の固定値など）は作り直していません。
- 比べるときは、まず生の構造で比べ（違いは上の 2 か所だけ）、次に、この 2 か所だけを確かめた移行（`7d3f4ca` → `ecb2d69`）でもどして比べます（tests/helpers.py の `with_card_data_commit_before_v0_69`）。もどす前の値が `7d3f4ca` でなければ失敗します。状態の指紋・ログ・乱数・`card_data` のほかの項目は除いていません。
- 書き出しの形式は 22 のままです。古い保存（v0.68 までの写しの元の状態）を読む口はもともとありません（エンジンは状態を pickle と `state_to_dict` で扱い、`state_to_dict` の結果から状態を作り直す API はない）。v0.68 で保存した pickle の状態は、写しの元が `ecb2d69` のまま続きます（状態のカードの定義を持つので、写しを読み直さない）。v0.68 の木で作った対戦の始めの状態を pickle にし、v0.69 で読んで不変条件を確かめ、最後まで進めました（37 手で終わり、写しの元は `ecb2d69` のまま。手で確かめたことで、自動テストにはしていない）。

### 6.2 v0.68 との比較（別のプロセス）

固定した v0.68（`24bfbe2`）と、別の木・別のプロセスで比べました。

| 比べたもの | A（移行だけ） | 最終のコード |
|---|---|---|
| 1 歩ごとの比較（tools/engine_lockstep.py。対戦のテストの 20 seed・ストレス実行の 10 seed） | 760 対戦・136,537 歩で食い違い 0（許した差 0） | 760 対戦・136,537 歩で食い違い 0（許した差 0）。もどす前の指紋は記録した 94,243 歩すべてで違う |
| 検証用デッキの対戦（v0.28〜v0.68 の組・2 seed・席の入れかえ。終わり方・手数・コマンド・状態・ログ・乱数・観測・拒否） | 608 局すべて同じ | 608 局すべて同じ（対戦の道具の結果に加えた新しい項目 `v069`（v0.69 の新しい id の使用の数。数えるだけ）を除いて比べた） |

- 1 歩ごとの比較は、tools/engine_lockstep.py の `record --card-data-commit 7d3f4ca…=ecb2d69…`（v0.69 で加えた）で、もどした指紋で比べ、もどす前の指紋の違いも数えます。A では、もどす前の指紋は記録した 94,243 歩すべてで違い（写しの元の 2 か所）、もどした指紋はすべて同じでした。
- 検証用デッキの対戦は、もどす前の状態・ログが 608 局すべてで違い、もどしたあとはすべて同じでした。

## 7. 研究の対応表の移行

研究の基準を `3f34908` から `7d3f4ca` に上げました（`research_links.json` の `research_commit`・`card_data_commit`。ブランチは kyuura の main）。

- 停止コード 149 件のうち 124 件の kyuura の処理を、kyuura の未解決の一覧（`engine_unresolved_index`）に合わせた。123 件は `not_in_kyuura`（kyuura への報告事項）だったもので、kyuura が論点（UQ-）に結んだ。進化のあとの HP（`UNRESOLVED_EVOLUTION_HP`）は `out_of_scope` から `issue`（UQ-EVOLUTION-HP-BELOW-DAMAGE）になった。同じ論点を指す停止コードをまとめていない。
- kyuura の一覧でコードのない行を指していた 8 件（T27・C34/C35・G40・P19・P32・Z9・DR8・DR13 の `kyuura_index_engine_key`）は、kyuura が停止コードを書いたので外した。
- コードのない問い 5 件の論点: SS1 → UQ-SPEED-STAR-SCOPE、ED1 → UQ-COPIED-ATTACK、FL0・BG0 → UQ-REACTIVE-SWITCH-DURING-ATTACK、ES0 → UQ-ESP-REDO。
- kyuura の論点の数を 19 から 71 にした（`counts.kyuura_issues`）。
- だつりょくえきの採用の仕様（DR1・DR6）・イマクニ？のドードーの簡略化した仕様・マチスの秘策の受け付けの制限は、裁定ではないまま（kyuura の `engine_positions` の記録。エンジンの区分は変えていない）。
- 照合の記録（CC-）17 件を `engine_verified` に加え、`engine_verified_without_kyuura_record` を空にした（ワザのある 11 枚と、トレーナー 6 枚）。
- 最新の説明（LD-）: 6 件（PMCG2-017・PMCG1-026・PMCG1-068・PMCG2-006・PMCG3-012・PMCG3-022 のワザ）を `registered` に、照合の記録に文面のある 8 件を `recorded_in_card_checks` に移した。`registered_without_kyuura_record` に残るのはカスミのドククラゲの［にげこむ］（このリポジトリの記録の再利用。v0.65）だけ。
- トレーナーの最新の説明（LD-…-TRAINER。6 件。オーキドはかせ・突風・パソコン通信・エネルギー回収・ポケモン交換おじさん・ポケモン育て屋さん）は、新しい区分 `registered_trainers` に結び、登録の処理に使う文面・出典のページと照らす（`check_research_links.py` の 4 章に加えた）。
- 採用の記録の `kyuura_records`（研究の基準のコミットでそのカードを指す kyuura の記録の id）を 92 件で直した。kyuura が論点（UQ-）に結んだ停止コードのカードで、記録を読み直したのではなく、id の対応を直したもの。
- 採用の記録の `kyuura_commit`（採用したときのデータのコミット）・`recorded_on`・外部照合の確認日と照らしたコミットは書き換えていない。写しの元の移行は `card_sources.json` の `data_migrations` に 1 件書き、検査（`data_migrations`）が、移行の前のコミットが写しの `previous_source`（作り直しの検査で比べたコミット）と同じことを確かめる。
- 研究の対応表の `engine_import_id` は `ENGINE-46A3E2E` のまま（kyuura の取り込みの記録はそのままある）。

## 8. 検証

### 8.1 確かめたこと

- 写しの作り直し: `python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura --check`
- 記録の検査: `python3 scripts/check_card_sources.py`・`python3 scripts/check_research_links.py --kyuura ../kyuura`
- 96 枚すべての欄・同じカードの組・登録（`ParityTest`）、表と数（`TableTest`）、記録（`RecordTest`）
- 新しい id の動き（単体テスト）: v0.31〜v0.66 の仕組みのテストのクラス 16 個を、カードの定数だけを新しい id に置きかえてもう一度走らせた（`substituted`。テストの中身・期待は変えない）。［にげこむ］（GD2-004）・［ベンチガード］（GD1-013）の決定と再開・エナジーチャージ（GD3-006）・かおりのわな（GD4-008）・しぜんになおる（GD5-002）・ほのおでかいふく（GD5-004）・ふしぎなバリアー（GD4-013・PR1-039）・サイコリンクのワザと出どころ（GD6-004）・スパイの見えない情報（PR1-061）・ナツメのESP（GD6-018）・カスミの勝負（GD2-017）・エリカの香水（GD4-018）・マチス（GD3-021）・マチスの交渉（GD3-022）・無色2個エネルギー（GD1-025・IP2-025）
- 版をまたいだ進化・4 枚の制限・基本エネルギー・無色2個エネルギー・保存（pickle）と書き出し（`MixedEvolutionTest`・`DeckTest`・`DoubleColorlessTest`・`SaveRestoreTest`）
- マチスの秘策の試すカード（`SecretPlanPoolTest`）
- 正式な対戦開始からの対戦（`--batch v0.69` の 3 組・4 seed・席の入れかえの 24 局。すべて勝敗で終わり、ログ・書き出し・観測の監査の問題 0。新しい id の特殊エネルギー・宣言して使う特殊能力・トレーナーの使用を `v069_uses` で数えた）
- v0.68 との別のプロセスでの比較（6.2 節）
- 変異試験の定義（tests/test_mutation_definitions_v0_18e.py。どの変異も今のコードに入る。変異試験そのものは走らせていない）
- ruff（v0.68 の木は 495 件、v0.69 は 486 件。v0.69 の変更で新しい指摘はなく、さわったテストのファイルの読み込みの並び（I001）を直した分だけ減った）
- 全体のテスト（最終のコードの写しの木で、走らせている間はファイルを変えずに `python3 -m unittest` を走らせた。結果はコミットのメッセージに書いた）

### 8.2 していないこと

- 96 枚のカードの画像・pcg-search.com のページの照合（外部照合なし）。ガイドブックの読み直し。
- 変異試験のすべての実行・Python の複数の版・性能の測定。
- 固定のデッキの変更・カードの強さの評価。
- kyuura の `engine_targets.json` の作り直し（kyuura の作業。引き継ぎの事項）。

## 9. 限界・報告事項

- 対戦の手順（tools/existing_effect_games.py）は、カードの手順をカード id で選ぶので、新しい id のカードの多くは v0.69 の手順（`_v069_step`・`_v069_decision`。受け付けるなら使う・受け付ける最初の答え）で使います。手順は対戦相手の AI ではなく、勝敗で判断していません。
- kyuura への報告事項: kyuura の `engine_targets.json` の `engine_reference` は v0.68 の登録の写しです。v0.69 の登録（96 枚）を写すと、96 枚の `engine_status` が `registered` になります（kyuura の作業）。
