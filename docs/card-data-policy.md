# カードデータの信頼と照合の方針（2026-10-15 から）

カードの実装を速めるため、カードデータの信頼と照合の方針を変えました。この文書は、方針・カードを実装するときの手順・記録の形式・検査をまとめたものです。`CLAUDE.md` の「カードデータの信頼と照合の方針」と、kyuura の docs/engine-readiness.md 12 章に同じ方針を書きました。

今回は方針・記録の形式・検査だけを整えました。新しいカードは加えていません。カードの効果・対戦の処理・公開の API・書き出しの形式・固定のデッキ・固定した参照データは変えていません。カードの写しの元（`KYUURA_COMMIT` = `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`）と研究の基準（`3f349085645f47d0649a6cacece3680caeae50bf`）も変えていません。エンジンの版は 0.28.0 のままです。

## 1. 方針

1. **kyuura の `data/cards.json`・`cards.csv` を、カードを実装するための信頼できる基本データとして扱います。** カードごとの原典照合の記録（kyuura の `CC-`）がないことだけを理由に、実装を止めたり原典を開いたりしません。`cards.json` と `cards.csv` は同じデータの別の形式で、両者が一致することを独立した原典照合とは数えません。
2. **カード情報の外部照合には pcg-search.com を使います。** カード名だけでなく、収録とカード番号（サイトの一覧の番号）で対象の版を決めます（同じ名前のカードが別の収録にある）。既存の照合結果は再利用し、同じカードを毎回調べ直しません。kyuura の日本語の文面が pcg-search.com の転記のカード（写しの `ja_text_source` がこのサイト。今の写しではプリン PMCG2-035）は、日本語の欄を同じサイトと照らしても独立した照合にならないので、照合したことにしません（6 章）。
3. **公式ガイドブック（『ポケモンカードオフィシャルブック2000』。通称 Silver Bible）のキャプチャ・OCR・画像の読み直しは、通常のカード実装の手順から外します。** 情報の不足や矛盾があっても、自動的にガイドブックの調査に進みません。ガイドブックを読み直すのは、利用者が明示的に依頼したときだけです。
4. **すでに記録されている最新の説明・エラッタ・裁定は、引き続き使います。** カードの印刷の文面と、処理に適用する説明（`play_text_ja`）を区別します。pcg-search.com のカードの画像だけを根拠に、既存の裁定や最新の説明を取り消しません。
5. **pcg-search.com に対象の版がない、またはアクセスできない場合は、その事実を記録します。** 外部照合ができなかったことだけでは、kyuura のデータによる実装を妨げません。挙動に影響する具体的な矛盾があるカードは、論点を記録してそのカードだけを保留にし、ほかの作業を続けます。

変えていない約束: 基準のルールは公式ルール 2000.02.14 版です。現代のルール・英語版の文面・後年の裁定で補わないこと、原典で決められない処理を `UnsupportedError`（`UNRESOLVED_…`）で止めること、未実装の効果を効果のないものとして扱わないこと、未解決の論点（kyuura の `UQ-`）の分類を推測で変えないことは、今までどおりです。

## 2. カードを実装するときの手順

1. **カードを写しに入れます。** `scripts/extract_kyuura_cards.py` のプールに id を加え、`python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura` で写しを作り直します（写しは手で編集しない。写しの元のコミットは変えない）。
2. **kyuura の既存の記録を探します。** 研究の基準のコミット（`research_links.json` の `research_commit`）で、そのカードを指す最新の説明（`LD-`。`card_id`）・照合（`CC-`。`card_id`）・裁定（`CR-`。`cards`・`related_cards`）・論点（`UQ-`。`cases`）・エラッタ（`data/rule_history.json` の `errata` の `cards`）の id を集めます。採用の記録の `kyuura_records` に、ちょうどこの集合を書きます（`scripts/check_research_links.py` が照らす）。研究の基準より新しい kyuura の記録が既定のブランチにあれば、それを使うには研究の基準を上げる作業（変わった項目の確かめ）を別に行います。
3. **処理に使う文面（`play_text_ja`）を対象（ワザ・特殊能力・トレーナー）ごとに決めます。**
   - kyuura に最新の説明（`LD-`）があれば、それにしたがいます。登録の `source` は LD- の id、研究の対応表では `latest_descriptions.registered` に挙げます。
   - エラッタ（`ERR-`・`TXT-`・`RUL-`）が処理に適用する説明を与えるなら、それにしたがいます。登録の `source` はエラッタの id です。
   - どちらもなければ、kyuura の印刷の文面（写しの文面）にしたがいます。`play_text_ja` は写しの文面と同じ、`source` は `kyuura data/cards.json`、研究の対応表では `latest_descriptions.adopted_printed_text` に挙げます。
   - 裁定（`CR-`）にはしたがい、論点（`UQ-`）に当たる場合は今までどおり止めます（停止コードと研究の対応表を加える）。
4. **必要なら pcg-search.com と照合します（任意）。** 同じ版を同じデータでもう照合していれば、その結果を再利用します。照合したら、3 章の形式で `external_checks` に残します。対象の版がない・アクセスできなかったことも残します（照合した欄は空）。
5. **矛盾があるか判断します。** kyuura の記録（`CC-` のデータの誤りなど）・外部照合の違いのうち、処理に影響する具体的な矛盾があれば、論点（`issues`）を書いて `status: on_hold` にし、そのカードは登録しません。処理に影響しない違い（ワザ名の表記など）は、論点に `affects_behavior: false` で書いて採用できます。kyuura の `CC-` のデータの誤りの欄は、どちらの場合も論点に挙げます。
6. **登録し、採用の記録を置きます。** 効果の登録表（`DEFAULT_EFFECTS`）に登録し、`kyuura_engine/data/card_sources.json` に `basis: kyuura_data`・`status: adopted` の記録を置きます。`card_verification.json` には書きません。
7. **検査を走らせます。** `python3 scripts/check_card_sources.py`、`python3 scripts/check_research_links.py --kyuura ../kyuura`、関係するテスト。

効果の実装の確かめ方（単体テスト・正式な開始からの対戦・監査・不変条件）は今までどおりです。テストが通ったことは、原典やほかの資料と照合した証拠にはなりません。

## 3. 記録の形式（`kyuura_engine/data/card_sources.json`）

形式は `kyuura-engine card sources 1` です。記録は次の 3 種類を分けます。

| 種類 | 場所 | 内容 |
|---|---|---|
| kyuura データの採用 | `card_sources.json` の `basis: kyuura_data` | 採用したデータのコミット・カード id・記録した日・処理に使う文面の根拠・確かめた kyuura の記録の id・論点・状態（採用・保留） |
| pcg-search.com との照合 | `card_sources.json` の `external_checks` | URL・確認日・対象の版（収録・カード番号）・照らした kyuura のコミット・結果・照合した欄・違い |
| 過去の原典照合 | `card_verification.json`（履歴） | 2026-10-14 までに『オフィシャルブック2000』と照合した記録。書き換えない。そのカードに外部照合を加えるときだけ、`card_sources.json` に `basis: guidebook_record` の記録を置く |

```json
{
  "format": "kyuura-engine card sources 1",
  "description": "…",
  "policy": {"since": "2026-10-15", "document": "docs/card-data-policy.md", "card_data": "kyuura data/cards.json", "external_site": "pcg-search.com"},
  "cards": {
    "<カード id>": {
      "basis": "kyuura_data",
      "name_ja": "<写しの名前>",
      "status": "adopted",
      "kyuura_commit": "<写しのコミット（KYUURA_COMMIT）>",
      "recorded_on": "YYYY-MM-DD",
      "kyuura_records": ["CC-…", "LD-…"],
      "play_text": {"attack/0": "kyuura_printed_text", "attack/1": "LD-…"},
      "external_checks": [
        {
          "site": "pcg-search.com",
          "url": "https://pcg-search.com/card/…",
          "checked_on": "YYYY-MM-DD",
          "kyuura_commit": "<照らした写しのコミット>",
          "edition": {"expansion": "<収録>", "list_number": "<一覧の番号>"},
          "result": "match",
          "checked_fields": ["name.ja", "pokemon.hp", "pokemon.attacks[0].text.ja"],
          "differences": []
        }
      ],
      "issues": []
    }
  }
}
```

| 項目 | 内容 |
|---|---|
| `basis` | `kyuura_data`（採用）か `guidebook_record`（過去の原典照合で登録したカードに外部照合を加えるだけ。`name_ja`・`external_checks` と、任意の `issues`・`notes` だけを持つ） |
| `status` | `adopted`（登録する）・`on_hold`（挙動に影響する論点があるので登録しない） |
| `kyuura_commit` | 採用したデータのコミット。写しのコミット（`KYUURA_COMMIT`）と同じ。写しの元を上げたら、採用の記録も見直す |
| `recorded_on`・`checked_on` | 方針の開始日（2026-10-15）から今日までの日付 |
| `kyuura_records` | 研究の基準のコミットで、このカードを指す kyuura の記録の id（LD-・CC-・CR-・UQ-・ERR-・TXT-・RUL-）。探して確かめた記録の一覧で、ちょうど kyuura の集合と同じ |
| `play_text` | 登録の処理に使う文面（`attack/<位置>`・`power/<位置>`・`trainer`）ごとの根拠。`kyuura_printed_text`（kyuura の印刷の文面）か、kyuura の記録の id（`LD-`・`ERR-`・`TXT-`・`RUL-`）。保留のカードは空 |
| `external_checks[].edition` | 対象の版。収録（`expansion`。サイトの収録の名前）とカード番号（`list_number`。サイトの一覧の「No」。旧裏のカードには番号が印刷されていないので、サイトの並び順の番号。kyuura の `data/ja_text_pcgsearch.json` の `list_number` と同じ意味）。照合した版には番号が要る。対象の版がない・アクセスできなかった照合では、番号は分からなければ null |
| `external_checks[].result` | `match`（照合した欄が同じ）・`differences`（違いがある）・`edition_not_listed`（対象の版がない）・`inaccessible`（アクセスできない）。後の 2 つには照合した欄・違いを書けない |
| `external_checks[].checked_fields` | 照合した欄（kyuura の文面が pcg-search.com の転記のカードは、日本語の欄（`name.ja`・`….name.ja`・`….text.ja`）を書けない。写しの欄の名前。`name.ja`・`pokemon.stage`・`pokemon.evolves_from.ja`・`pokemon.hp`・`pokemon.types`・`pokemon.weaknesses`・`pokemon.resistances`・`pokemon.retreat_cost`・`pokemon.rules_text`・`pokemon.attacks[i].name.ja`／`cost`／`damage`／`text.ja`・`pokemon.powers[i].name.ja`／`text.ja`・`trainer.text.ja`・`energy.kind`・`energy.provides`・`jp_print.level`・`jp_print.rarity`）。照合していない欄を書かない |
| `external_checks[].differences` | `field`・`kyuura`（写しの値そのまま）・`pcg_search`（サイトの値）・`affects_behavior`（処理に影響するか）。違いを見つけても kyuura のデータ・写しは直さない（kyuura への報告事項） |
| `issues` | `question`・`fields`・`affects_behavior`、任意の `kyuura_issue`（UQ-）・`note`。挙動に影響する論点があれば保留にする |

記録には、ガイドブックの照合の項目（`page`・`pdf_page`・`scan`・`card_image_text_ja`・`latest_description_ja`・`power_card_image_text_ja`・`power_latest_description_ja`・`image_check`・`rules_page`・`commentary_page`・`mismatches`）を書けません。読んでいない原典を確かめたことにしないためです。

研究の対応表（`research_links.json`）の `latest_descriptions` に、区分 `adopted_printed_text`（採用で処理に使う文面を kyuura の印刷の文面にしたワザ・特殊能力）を加えました。今は空です。最新の説明のある登録は、5 つの区分（`registered`・`recorded_in_card_checks`・`card_checks_without_text`・`registered_without_kyuura_record`・`adopted_printed_text`）のちょうど 1 つに挙げます。

2026-10-14 までに登録したカード（70 枚。ワザ 92・トレーナー 11・特殊能力 9）は、どれも過去の原典照合の記録で登録したので、採用の記録はまだありません（`cards` は空）。過去の照合の記録を新しい形式に移したり、採用の記録に置きかえたりはしていません。

## 4. 検査

| 検査 | 確かめること |
|---|---|
| `scripts/check_card_sources.py`（新規） | 形式と方針の値。決まった項目だけ（ガイドブックの項目を拒否）。カードが写しにあり名前が同じ。採用のコミットが写しのコミット。日付が方針の開始日から今日まで。登録したカードは過去の原典照合の記録か採用の記録のちょうど一方を持つ。保留のカードは登録しない・挙動に影響する論点がある。採用したカードに挙動に影響する違い・論点がない。`play_text` が登録の文面とちょうど対応し、根拠ごとに登録の文面と出典が合う（印刷の文面は写しと同じ・出典 `kyuura data/cards.json`・対応表の `adopted_printed_text` にある。LD- は出典が id・`kyuura_records` にある・対応表の `registered` と同じ）。外部照合はサイトが pcg-search.com・URL が https の pcg-search.com・版の収録と一覧の番号・結果と照合した欄・違いの組み合わせ・欄が写しのカードにある・違いの kyuura の値が写しの値・同じ版を同じデータで調べ直していない・kyuura の文面が pcg-search.com の転記のカードで日本語の欄を照合したことにしていない |
| `scripts/check_research_links.py`（4c・7 を追加） | `adopted_printed_text` の文面が研究の基準のコミットの印刷の文面と同じで、その対象の LD- と、文面のデータの誤りの記録（CC- の `data_error`）がない。採用の記録の `kyuura_records` が研究の基準のコミットの kyuura の記録と同じ。根拠にしたエラッタがそのカードを指す。CC- のデータの誤りの欄が論点にある。LD- を根拠にした採用の登録の出典（LD- の id）を受け付ける |
| tests/test_effects.py・tests/test_trainers.py・tests/test_pokemon_powers_v0_5.py（変更） | 登録したカードは、過去の原典照合の記録（ページ・最新の説明の確かめは今までどおり）か採用の記録のちょうど一方を持つ。採用の記録で登録したカードには、ガイドブックのページを求めない |
| tests/test_research_links_v0_18e.py（変更） | 最新の説明のある登録が 5 つの区分のちょうど 1 つにある |
| tests/test_card_sources.py（新規） | 同梱の記録が方針と合う（採用の記録はまだない）。方針どおりの記録（印刷の文面・LD- を根拠にした採用、保留、対象の版がない・アクセスできなかった照合、過去の原典照合のカードへの外部照合）を受け付ける。読んでいない原典を確かめたことにする記録・形の崩れた記録を拒否する（63 通り）。../kyuura があれば、研究の基準のコミットと照らす検査が、採用を受け付け、記録の見落とし・LD- を無視した印刷の文面・違う文面・データの誤り・エラッタの見落としを拒否する |

実装の整合性を確かめる検査は残しています: 登録したワザ名・説明文が写しと同じでなければ使えないこと（`attack_problem`）、説明文のあるワザの一覧、効果の型の `check`、トレーナー・特殊能力の名前と文面の照合、過去の原典照合の記録のページ・最新の説明と登録の一致、研究の対応表の照合。

## 5. 変えた指示と、履歴として残したもの

- `CLAUDE.md`: 「カードデータの信頼と照合の方針（2026-10-15〜）」を加え、「照合済みの記録の再利用」の手順の 4・5（原典に戻る）をカードの実装の手順から外し、「ルールの扱い」の「登録するカードは、先に『オフィシャルブック2000』のページと照合し…」などを、過去の原典照合の記録か採用の記録のどちらかに改めました。
- docs/verified-record-reuse.md: 冒頭に、カードの実装の手順がこの文書に移ったことを書きました（取り込みの記録は書き換えていない）。
- kyuura の docs/engine-readiness.md: 冒頭の状況に方針を加え、4 章の「カード効果を実装する前に確認すること」・7 章（どちらも 2026-10-12 の計画の記録）に 12 章を指す注記を加え、10.1 の 4・5 と 10.2 の最後の項目を改め、12 章に方針を書きました。kyuura の README の「エンジンの新しい版を取り込むとき」には、採用の記録・pcg-search.com との照合を CC- として取り込まないこと、不足する範囲の画像の確認に自動で進まないことを書きました。kyuura には `CLAUDE.md` がない（どのブランチにもない）ので、実装のときに参照する指示文書は engine-readiness.md です。kyuura のデータ・サイドカー・過去の照合の記録は変えていません。kyuura のコミットは `4c526be`（ブランチ `claude/cool-ptolemy-5vtgsg`。研究の基準の `3f34908` から、kyuura の既定のブランチ（PR #1 のマージ `6a5dfec`）まで早送りしてから加えた。研究の基準のコミットは変えていない）。
- 履歴として残したもの: `card_verification.json`（過去の原典照合の記録）、各版の文書（docs/*-v0.x.md）の「画像で読み直した」「p.N と照合した」などの記述、研究の対応表の既存の区分と kyuura への報告事項。これらはその版の作業の記録で、今のカードの実装の手順ではありません。

## 6. pcg-search.com について

- 旧裏（PMCG）・neo・VS・web・e・ADV・PCG などのカードの一覧と、カードごとのページ（種類・HP・弱点・抵抗力・にげる・ワザ・説明文・収録・レアリティ・カードの画像）がある、ファンのサイトです。kyuura は出典 N3 として使っています（拡張パック以外の商品 681 枚の転記 `data/ja_text_pcgsearch.json`、拡張パックの 1 枚（プリン PMCG2-035）の日本語の文面、転記の食い違いのカードの画像での確認。kyuura docs/sources.md・docs/research-status.md）。サイトの説明に「データの誤りや誤字脱字等が含まれる場合がございます」とあるので、外部照合で違いを見つけても、写し・kyuura のデータを直さず、違いとして記録します。
- 版の識別: 一覧（`https://pcg-search.com/card/card_list.php`）は、収録ごと（例: 「第1弾 拡張パック」「第2弾 拡張パック「ポケモンジャングル」」）に「No」（例: `001/096`。サイトの並び順で、カードに印刷された番号ではない）を付けています。カードのページは `https://pcg-search.com/card/1st/1st1032.php` の形です。サイトの番号は kyuura のカード id と別の番号です（例: 第1弾 拡張パックの一覧の `032/096` はスターミーで、kyuura の id は `PMCG1-026`）。kyuura の `jp_print.series` に複数の収録（「第1弾拡張パック、スターターパック」など）があるカードもあるので、照合した収録を書きます。
- 2026-10-15 に、記録の形式を決めるためにトップページ・一覧・カードのページ 1 つを開きました（アクセスできた）。カードの照合はしていないので、照合の記録はありません。

## 7. 確かめたこと

文書と検査だけの変更（対戦の処理は変えていない）なので、長い対戦の比較・模擬戦・性能の測定はしていません。

| 確かめたこと | 結果 |
|---|---|
| `python3 scripts/check_card_sources.py` | 「カードデータの採用と外部照合の記録は方針と合っています（記録 0 件）」 |
| `python3 scripts/check_research_links.py --kyuura ../kyuura` | 「研究の対応表は kyuura 3f349085645f47d0649a6cacece3680caeae50bf の記録と一致しています」 |
| `python3 -m unittest tests.test_card_sources tests.test_effects tests.test_trainers tests.test_pokemon_powers_v0_5 tests.test_research_links_v0_18e tests.test_cards tests.test_mutation_definitions_v0_18e` | 124 件 OK（tests/test_card_sources.py は 16 件。../kyuura と照らす 6 件を含む） |
| tests/test_card_sources.py の拒否の場面（63 通り）が、それぞれ意図した理由の文で拒否されること | 場面ごとに問題の文を出して確かめた（ほかの問題が先に出て通ってしまう場面を 1 つ直した） |
| `python3 scripts/check_card_sources.py` に偽の記録（ガイドブックのページを書いた採用の記録）を置く | 終了コード 1（テスト `test_command_line_rejects_a_false_record`） |
| `python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura --check`（写しが変わっていない） | 「kyuura ecb2d69… と一致しています」 |
| `python3 tools/run_mutants.py check`（変異の定義が今のコードに入る） | 50 件すべて ok |
| `ruff check --select F,E9 .` | 問題なし |
| `python3 -m unittest`（すべて。Python 3.13。検査のコードとテストを変えたので走らせた） | 2,177 件 OK（skipped 1）。6 分 41 秒（偽の記録で終了コード 1 になることを確かめるテスト 1 件は、この実行のあとで加え、上の関係するテストで走らせた） |
| kyuura: `python3 scripts/build_card_rulings.py --check`・`python3 scripts/build_rule_history.py --check`・`python3 -m unittest discover -s tests` | 一致・一致・150 件 OK |
| 変えていないもの: `kyuura_engine/data/kyuura_cards.json`・`card_verification.json`・tests/fixtures・`decks.py`・`engine.py`・`resolution/`・書き出し | `git diff` に出ない（`effects.py` は 3 つの登録の型の docstring だけ） |
