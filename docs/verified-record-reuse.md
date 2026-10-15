# 照合済みの記録の再利用と、照合の記録の kyuura への取り込み（2026-10-15）

v0.19 の準備として、原典（『ポケモンカードオフィシャルブック2000』のスキャン [J38] など）を同じ範囲で何度も読み直さないための手順を決め、エンジンの照合の記録のうち kyuura（研究の正本）に入っていなかったものを kyuura に記録しました。

- エンジンの版は 0.18.0 のままです。`engine.py`・`kyuura_engine/resolution/`・公開の API・書き出しの形式・カードの写しの元（`KYUURA_COMMIT` = `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`）・固定した参照データは変えていません。新しいカードの効果・解決の基盤の機能も加えていません。
- 変えたのは、研究の基準のコミット（`kyuura_engine/data/research_links.json`）・対応表の検査（`scripts/check_research_links.py`）・そのテスト（tests/test_research_links_v0_18e.py）・文書（`CLAUDE.md`・この文書ほか）です。
- 原典の画像は、今回は 1 ページも読み直していません。

## 1. 手順

`CLAUDE.md` の「照合済みの記録の再利用」と、kyuura の docs/engine-readiness.md 10 章に、同じ手順を書きました。

1. 原典を開く前に、既存の記録を探す（2 章の場所）。
2. 対象（カード id・ワザや特殊能力の位置と名前）とルールの版（2000.02.14 版。最新の説明は『オフィシャルブック2000』）が一致し、必要な項目の照合の結果と出典（資料・ページ・確認日・確認の方法・照合した項目）が確かめられれば、再利用する。
3. 新しいセッションになった、確認日が古い、実装する人が変わった、だけを理由に読み直さない。
4. 既存の記録で判断できない部分（照合していない欄・記録のあとで変わったデータ・記録どうしの矛盾・新しい相互作用）だけ、原典に戻る。
5. 原典に戻る前に、既存の記録で何が足りないかを具体的に書く。

再利用は、記録された確認の範囲に限ります。テストが通ったことだけを原典と照合した証拠にせず、再利用で SUPPORTED・UNRESOLVED などの分類を変えません。既存の「登録するカードは、先に…ページと照合し」（`CLAUDE.md` のルールの扱い）と各版の文書の「画像で読み直した」は、照合の記録がないとき、または手順の 4 に当たるときの手順です。

## 2. 記録の場所

| 場所 | 記録していること |
|---|---|
| `kyuura_engine/data/card_verification.json` の `cards.<id>` | ページ（`page`・`pdf_page`）、照合の結果（`status`・`mismatches`）、図版の文面（`card_image_text_ja`）、最新の説明（`latest_description_ja`）、特殊能力（`power_…`）、確認日（`checked_on`。v0.2 以降の記録）、方法と所見（`notes`）。v0.1 の 16 枚はカードごとの日付がなく、ファイルの `checked_on`（v0.1 のコミット `03766e0` の値）と docs/data-provenance.md によります（今回取り込んだのはそのうち 15 枚。ワンリキー PMCG1-053 はすでに kyuura に記録があった） |
| 各版の裁定の文書（docs/rules-2000-02-14.md・docs/*-v0.x.md の裁定の表） | 規定ごとの分類（CONFIRMED・SUPPORTED・UNRESOLVED・CONFLICT）と根拠の誌面 |
| docs/data-provenance.md | 写しの由来、カードごとの照合の結果、kyuura との食い違い |
| kyuura `data/sidecar/`（最新の説明 LD-・照合 CC-・裁定 CR-・論点 UQ-） | 研究の正本。CC- の `checked_fields`・`fields_not_checked`・`verification`、LD- の `differences`・`image_check`。エンジンから取り込んだ記録は `import_provenance` を持つ |
| kyuura `data/rule_history.json` の `documents`（P43 の `pages` の `refs`） | ページごとに、どの記録がそのページを使ったか |
| `kyuura_engine/data/research_links.json` | エンジンの停止コード・登録・照合の記録と kyuura の id の対応（文面・分類は写さない） |

## 3. 2026-10-15 の取り込み

v0.18（`46a3e2e`）の `research_links.json` は、最新の説明 34 件（`registered_without_kyuura_record`）と照合の記録 34 枚（`engine_verified_without_kyuura_record`）を「kyuura に記録がない」としていました。これは「原典と照合していない」という意味ではありません。34 件・34 枚とも、エンジンが原典の画像で照合した記録があります（2026-10-12。ナツメのヤドンは 2026-10-14）。kyuura の記録と突き合わせて、次のように分けました。

### 3.1 最新の説明 34 件

| 区分 | 件数 | 扱い | 対応表の区分 |
|---|---|---|---|
| kyuura の CC- に、印刷の文面と同じものとしてすでに記録されていた | 16 | 再利用（kyuura の記録は変えていない） | `recorded_in_card_checks` |
| kyuura の CC- に、データの誤りの候補としてすでに記録されていた（ケーシィのねんりきの読点。資料の値がエンジンの最新の説明と同じ） | 1 | 再利用（変えていない） | `recorded_in_card_checks` |
| kyuura に記録がなく、印刷の文面と同じ | 11 | 取り込んだ CC- の照合した欄に入れた（kyuura は、文面が同じ最新の説明を LD- にしない） | `recorded_in_card_checks` |
| kyuura に記録がなく、印刷の文面と違う | 5 | LD- として取り込んだ（トランセル・コクーンのかたまる、スピアーのダブルニードル、バタフリーのふきとばし・メガドレイン） | `registered` |
| 図版も kyuura の文面と違い、図版の版が決まらない（ドードーのみだれづき） | 1 | LD- にもデータの誤りにもせず、CC- の照合しない欄・調査課題にした | `card_checks_without_text` |

再利用 17 件・取り込み 16 件（CC- の照合した欄 11・LD- 5）・不足として記録 1 件です。LD- の違いの種類（`clarification`・`wording`）は、kyuura の既存の記録の分け方に合わせました（例: トランセル・コクーンのかたまるは、kyuura にすでにあるゼニガメのからにこもる `LD-PMCG1-023-ATK1` と同じ「…ダメージを受けない。（ダメージ以外の効果は受ける）」への言いかえなので、同じ `clarification`）。

### 3.2 照合の記録 34 枚

34 枚とも CC- として取り込みました（v0.1 のたねポケモン・基本エネルギー、v0.2〜v0.4 のポケモン・トレーナー、参照カードのヒトカゲ、v0.18c のナツメのヤドン）。照合した欄（`checked_fields`）はエンジンの記録の範囲だけで、エンジンが照合していない欄は `fields_not_checked` にしました。

- v0.1 のたねポケモンは、名前・段階・特殊能力の欄がエンジンの v0.1 の照合の項目にないので、照合した欄に入れていません。
- トレーナーは名前（マサキは文面も）だけです。kyuura のサイドカーにトレーナーの最新の説明の形式がないので、文面の違いは CC- の所見にだけ書きました。
- 基本エネルギーは、公式ルール p.318 の種類だけを照合した記録です（カードごとのページはない）。
- ヒトカゲのひのこ（エンジンが登録していないワザ）と、ドードーのみだれづきの文面は、照合した欄に入れていません。

### 3.3 確認日と取り込んだ日

kyuura の取り込んだ記録は `import_provenance`（`kind` `engine_record`・`imported_on` 2026-10-15・`kyuura_reread_source` false）と、`verification` の `by` `kyuura-engine`（原典の確認日 `source_checked_on`・その根拠・方法・範囲）を持ちます。kyuura が画像を読み直したことにはしていません（kyuura の `scripts/build_card_rulings.py` が、`by: kyuura` と `import_provenance` のどちらもない記録・両方ある記録・確認日が取り込んだ日より後の記録をエラーにする）。エンジンの記録の場所は、33 枚が kyuura の取り込み `ENGINE-D90BCE1`（v0.17。この 33 枚の記録は、加えたときから v0.18 まで変わっていない）、ナツメのヤドンが新しい取り込み `ENGINE-46A3E2E`（v0.18。裁定の表のない版）です。

### 3.4 kyuura のコミット

ブランチ `claude/cool-ptolemy-5vtgsg`（kyuura の既定のブランチには取り込んでいない）。

| コミット | 内容 |
|---|---|
| `6a8dd12` | 再利用の手順（docs/engine-readiness.md 10 章）と、原典を確かめた人の区別（`import_provenance`）の検査 |
| `5f345f3` | 照合の記録 34 枚（CC-）・最新の説明 5 件（LD-）・v0.18 の取り込み（`ENGINE-46A3E2E`）・ページの記録（P43 に 19 ページを加え、5 ページに参照を加えた） |
| `3f34908` | 調査の状況のページと準備状況の 10 章に、取り込みのコミットを記入 |

## 4. 研究の基準を上げたこと

研究の基準を `adf97107ee0d9755cd7ddedae298ecb02914128e` から `3f349085645f47d0649a6cacece3680caeae50bf` に上げました。上げる前に、kyuura の差分（`adf9710..3f34908`）を確かめました。

- kyuura のカードデータ（`data/cards.json`）・ルールの違い（`rule_differences.json`）は変わっていない。カードの写しの元（`ecb2d69`）も変えていないので、エンジンが使う項目は同じ（`check_research_links.py` の `card_data_differences` も変わらない）。
- サイドカーは追加だけ: 最新の説明 25 → 30 件、照合 30 → 64 件。既存の LD-・CC-、論点（19 件）・裁定・エンジンの未解決の一覧は変わっていない。分類の違い（17 件）も変わっていない。
- エンジンの側で変えたこと:
  - `research_links.json`: `research_commit`・`research_branch`・`engine_import_id`（`ENGINE-46A3E2E`）。最新の説明は 4 つの区分（`registered` 25・`recorded_in_card_checks` 28・`card_checks_without_text` 1・`registered_without_kyuura_record` 0）、照合の記録は `engine_verified` 62 枚・`engine_verified_without_kyuura_record` 0 枚。
  - `scripts/check_research_links.py`: `recorded_in_card_checks` の文面（照合した欄のワザの文面、またはデータの誤りの資料の値がエンジンの最新の説明と同じ）とページ、`card_checks_without_text` が照合した欄にないこと、kyuura の取り込んだ記録（`import_provenance`）のページ・確認日がエンジンの `card_verification.json` と同じこと、`engine_import_id` が kyuura の取り込みにあることを確かめる。
  - tests/test_research_links_v0_18e.py: 研究の基準のコミットと、最新の説明の 4 つの区分（重ならず、合わせるとエンジンの登録と同じ）。

## 5. 原典の再確認が必要な項目

今回は、原典の再確認が必要な項目はありませんでした（手順の 4 に当たる項目は、取り込みの範囲から外して不足として記録した）。次の項目は既存の記録では決まらないので、必要になったときに原典（またはほかの資料）に戻ります。

| 項目 | 既存の記録で足りないこと | 戻る先 |
|---|---|---|
| ドードー（PMCG1-061）のみだれづきの印刷の文面 | kyuura の文面「…ダメージをあたえる。」は、p.231 の図版（「…ダメージ」まで）とも最新の説明とも違う。図版が第1弾の初版の印刷かが決まらない。エンジンの処理は最新の説明にしたがうので変わらない | 第1弾の初版のカードの画像（この本では決まらない） |
| トレーナー（きずぐすり・ポケモンいれかえ・ディフェンダー）の最新の説明 | kyuura に、トレーナーの最新の説明を記録する形式がない（違いは CC- の所見だけ。プラスパワーは kyuura の `ERR-PLUSPOWER`） | kyuura の形式を加える作業（原典の読み直しは要らない。エンジンの記録に文面がある） |
| ヒトカゲ（PMCG1-014）のひのこ | エンジンは図版の文面を記録していない（ひのこは未登録） | p.63 の図版（ひのこを登録するときだけ） |
| v0.1 のたねポケモン 9 枚の名前・段階・特殊能力の欄 | エンジンの v0.1 の照合の項目に入っていない | 各カードのページ（必要なときだけ） |
| 基本エネルギー 6 枚 | カードごとのページがなく、公式ルール p.318 の種類だけを照合した | カードの画像（必要なときだけ） |

## 6. 残った不足・矛盾

- ポニータ（PMCG1-016）のワザ名: kyuura のカードデータは「けりとばす」、p.75 は「けとばす」。エンジンは v0.1 から報告していました（docs/data-provenance.md）。kyuura は今回、CC-PMCG1-016-P75 にデータの誤りの候補として記録しましたが、`data/cards.json` は直していません（kyuura の作業）。エンジンはワザ名を処理に使わないので、写しの値のまま使います。
- kyuura の LD- のうちエンジンが登録していない 5 件（`kyuura_records_not_registered`。未対応のカード）は変わっていません。
- 分類の違い 17 件（エンジンの過去の版の SUPPORTED と kyuura の CONFIRMED など。v0.18a）は、推測で統一していません。どれも処理は同じです。
- 未解決の裁定 24 件・停止コード 18 件・kyuura の論点 19 件は変わっていません（再利用で分類を変えていない）。
- 研究の基準のコミット（`3f34908`）は kyuura の既定のブランチに取り込まれていません（取り込みは自動では行わない）。`git clone` はすべてのブランチを取得するので、ブランチがある限り読めます。
- kyuura に取り込んだ記録は、もとはエンジンの記録です。kyuura が独立に原典を確かめた記録（`by: kyuura`）として数えないでください（kyuura の調査の状況のページは、原典を確かめた人ごとに数を分けている）。

## 7. 確かめたこと

実装を変えていないので、長い対戦の比較・性能の測定はしていません。

| 確かめたこと | 結果 |
|---|---|
| kyuura: `python3 scripts/build_card_rulings.py --check`・`build_rule_history.py --check` ほか生成した文書の検査 | 一致 |
| kyuura: `python3 -m unittest`（137 件） | OK |
| エンジン: `python3 scripts/check_research_links.py --kyuura ../kyuura` | 「研究の対応表は kyuura 3f349085645f47d0649a6cacece3680caeae50bf の記録と一致しています」 |
| エンジン: 対応表を壊した 5 通り（2 つの区分に同じ登録・文面の違う CC- への対応・照合した欄に文面がある登録を `card_checks_without_text` に移す・kyuura にない取り込みの id・研究の基準を `adf9710` に戻す）で検査が失敗すること | 5 通りとも失敗（終了コード 1。`adf9710` に戻すと 55 件の違い）。元に戻した対応表で成功 |
| エンジン: 関連するテスト（tests/test_research_links_v0_18e.py・tests/test_mutation_definitions_v0_18e.py・tests/test_effects.py・tests/test_trainers.py） | 73 件 OK |
| エンジン: `python3 tools/run_mutants.py check`（変異の定義が今のコードにちょうど 1 か所で入り、構文として正しいか） | 50 件すべて ok（研究の対応表の停止コードを 1 つ落とす変異 V03 も、対応表を変えたあとも入る） |
| エンジン: `python3 -m unittest`（すべて。Python 3.13） | 1,926 件 OK（skipped 1）。5 分 49 秒 |
| エンジン: `ruff check --select F,E9 .` | 問題なし |

変異試験の `witness`・`full`（C 段階）、長い対戦の比較（`tools/engine_lockstep.py`）・性能の測定は走らせていません（実装を変えていない）。
