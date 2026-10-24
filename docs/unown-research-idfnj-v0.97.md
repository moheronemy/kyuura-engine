# v0.97: kyuura のアンノーンの調査の取り込みと、アンノーンI・D・F・[N]・[J] の 5 枚

v0.97 は、kyuura のアンノーンI・D・F・[N]・[J] の調査（kyuura docs/unown-research-v0.97.md）を取り込み、写しの元と研究の基準を上げる移行（2 章・3 章）を独立した工程として
確かめたうえで、5 枚を登録する版です。この文書の 2 章・3 章は移行だけのコミットの内容で、カードの登録は 4 章からです。

## 1. 開始点と取り込んだ研究

- エンジンの基点は v0.96（`f3770975c34618deb4103157058603c0d1a367a6`）。作業を始めたとき（2026-10-25）の `main`（リモートも同じ）は `c4233fb427106956e8cd812eb0a93cf0cb959383`
  （PR #18 のマージ。木は v0.96 と同じ `b6a50a7`）で、後のコミットはありませんでした。作業ブランチ `claude/v0.97-unown-research-idfnj` をこの `main` から作りました。作業の木の
  未コミットの変更は `.claude/`（この作業のものではない。コミットしない）だけでした。
- 取り込む研究は kyuura `78d090c329aca58c4b5fbaefa2a1e5c089433b58`（ブランチ `claude/eloquent-lamport-5xyv5r`）。作業を始めたときの kyuura の `main` は
  `73a169063463bbf7bcaa3137d70cbf9721d11534`（PR #5 のマージ。2026-10-25 01:30）で、親は `7d3f4ca`（v0.69〜v0.96 の写しの元）と `78d090c` です。`73a1690` の木は `78d090c` の木
  （`af4de87`）と同じで、`78d090c` 以後の差分はありません。研究を含む固定のコミットとして、kyuura の `main` のマージ `73a1690` を写しの元と研究の基準にしました（v0.69 の
  `7d3f4ca` も `main` のマージを固定した）。kyuura・kyuura の `main` は変えていません。
- ルールの基準は公式ルール 2000.02.14 版のまま（neo 期のカードにも同じ）。公式ガイドブックの新しいキャプチャ・OCR・読み直しはしていません。英語版の文面・現代のルール・
  2002 年の分類で日本語の不足を補っていません。

## 2. 写しの元の移行（7d3f4ca → 73a1690）

### 2.1 kyuura の差分

`7d3f4ca` → `73a1690` の data/cards.json は、カードの追加・削除がなく（1,377 枚）、形式も 3 のままです。値が変わったカードは 4 枚だけで、写し（v0.96 の 1,169 枚）に
入っているカードはありません。

| カード | 変わった欄 | 種類 |
|---|---|---|
| neo2-023 アンノーンI・neo2-025 アンノーンD・neo2-026 アンノーンF | `pokemon.rules_text.ja`（null → 「「アンノーン」はデッキに4枚までしか入れることができません。」）・`data_gaps`（その欄が消えた）・`corrections`（台帳の記録）・`notes` | kyuura の訂正（台帳 data/curation/card_corrections.json の `FIX-neo2-023/025/026-RULES-TEXT-JA`） |
| neo2-025 アンノーンD・PF2-001 アンノーン[N] | `jp_en_differences`（［DARK df］・［NORMAL df］の日英の違い） | 出典の記録の欄 |

台帳の候補（`candidates`）には、アンノーンM・U・A のルール文の欠け（`gap_open`）、[N]・[J] のレベル（`gap_open`）、[J] の英語の「Unown Dragon」（`held_transcription_difference`）が
加わりました。どれも kyuura が直していない候補で、エンジンでも補っていません。

### 2.2 移行の連鎖

v0.69 の移行（ecb2d69 → 7d3f4ca）は、1 段だけの移行を前提に、すべての修正を「同じ前のコミット → 今のコミット」で確かめていました。2 回目の移行のために、移行を連鎖で持つように
しました（`scripts/extract_kyuura_cards.py` の `KYUURA_MIGRATIONS`。写しの書き出しの `source_migrations`）。

| 段 | 前 | あと | その段で kyuura が当てはめた修正 |
|---|---|---|---|
| v0.69 | ecb2d69 | 7d3f4ca | FIX-PMCG2-041-ATK0-NAME・FIX-PMCG2-041-LEVEL・FIX-PMCG2-046-ATK0-TEXT・FIX-GD6-010-ATK1-DAMAGE・FIX-SI-010-ATK1-NAME |
| v0.97 | 7d3f4ca | 73a1690 | FIX-neo2-023-RULES-TEXT-JA・FIX-neo2-025-RULES-TEXT-JA・FIX-neo2-026-RULES-TEXT-JA |

- 過去の段の値は書き換えていません。`PREVIOUS_KYUURA_COMMIT`（ecb2d69）は v0.68 までの写しの元（最初の段の前・採用の記録の採用したときのデータのコミット）のままで、v0.69 の段の
  `to` も 7d3f4ca のままです。修正ごとに当てはめた段（`migration`）を書き、写しの `kyuura_corrections` の `applied_in_source`・`previous_source` は段のあと・前です（v0.69 の段の
  5 件は 7d3f4ca・ecb2d69 のまま。既存の項目に加えたのは `kind`・`migration` だけ）。
- 修正の確かめ（`kyuura_correction_problems`）: 段の前のコミットの値が `before`、段のあとと写しの元の値が `after`、台帳とカードの `corrections` に同じ記録（id・欄・前・後・根拠・
  種類）。照合の記録による修正（`kyuura_source_check`）のコミットは、その段の前とあとのあいだ。欠けの修正（`transcription_omission`）は、前の値が null で、段の前の `data_gaps` に
  その欄があり、あとにないこと。
- 写す欄の比べ（`previous_copy_problems`）: 段ごとに、段の前にあったカードの写す欄が、段のあとで、その段の修正の欄と出典の記録の欄（notes・ja_text_source・source_ids・
  jp_en_differences）を除いて同じ（`migration_copy_problems`）。欠けの修正では、`data_gaps` からちょうどその欄だけが消えてよい（ほかの欠けの増減は許さない）。最初の段の前から
  写しの元までの比べ（すべての修正を当てはめる。v0.69 と同じ呼び方）も残しました。
- 採用の記録の移行（`card_sources.json` の `data_migrations`）は 2 段になりました。`scripts/check_card_sources.py` の `data_migrations` は、記録の並びの前・あと・文書が写しの
  `source_migrations` と同じ並びで、つながっていて（段の前がその前の段のあと）、最後のあとが写しのコミットで、日付が段の順であることを確かめます。採用の記録の採用したときの
  データのコミット（ecb2d69・7d3f4ca）・記録した日・外部照合の確認日と照らしたコミットは書き換えていません。外部照合の違いの kyuura の値は、照らしたコミットが修正の段の前なら
  修正の前の値でもよい（連鎖の位置で比べる。v0.69 の 1 段のときと同じ結果）。

### 2.3 カードの画像による修正（根拠 `card_image_check`）

v0.96 までの検査は、根拠 `kyuura_source_check`（kyuura の照合の記録 CC-）・`user_provided`（利用者が示した訂正）・`kyuura_existing_record`（kyuura の前の判定）だけを扱えました。
アンノーンI・D・F のルール文は、kyuura が 2026-10-24 にカードの画像（pcg-search.com となぞのばしょの 2 つのサイト）を読んで埋めたもので、根拠は `card_image_check` です。
この根拠を、ほかの根拠を広げずに、次のように確かめるようにしました（`card_image_check_problems`）。

- 画像を見たのは kyuura（`kyuura_saw_image` が真）で、エンジンは画像・公式の書籍を見ていない（`engine_saw_image` が偽）。
- 台帳に、画像ごとの画像の URL（https）・ページの URL・sha256（64 桁の 16 進数）・取得日（決めた日まで）、カードの識別（`identification`）・確かめた範囲（`scope`）・エラッタで
  ないこと（`not_errata`）・誤りの出どころ・根拠の説明がある。写しの記録の画像（`evidence`。URL・sha256・取得日）が台帳の画像と同じ。
- kyuura の照合の記録（CC-）・最新の説明（LD-）・修正のコミットを書かない（作らない）。照合の記録がその欄を照合していない。照合の記録を変えない（`card_checks_affected` が空）。
- 修正はその段で入った（段の前のコミットの台帳にない）。

2 つのサイトの画像は、kyuura の台帳の `scope` のとおり独立した 2 枚の実物の照合として数えず、CC-・LD- の代わりにもしていません。kyuura の id とサイトの番号の違い（neo2-025 が D・
サイトは 026、neo2-026 が F・サイトは 025）と、なぞのばしょの D のページの名前の既存の誤記（「アンノーン[I]」。kyuura の既存の判定）は、kyuura の記録のままです。

### 2.4 写しを作り直した結果

- `python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura` で作り直しました（写しは手で編集していない）。写しの `cards`（1,169 枚）は v0.96 と同じ（値の違いなし）で、
  変わったのは `source.commit`・`equivalent_targets`・`reprint_targets`・`engine_user_corrections` の写しの元のコミット、`source_migrations`（新規）、`kyuura_corrections`（3 件を加え、
  既存の 5 件に `kind`・`migration` を加えた）、`previous_source` の注記だけです。5 枚の登録を加えていない状態で、写しの検査・採用の記録の検査・研究の対応表の検査が通ること、
  既存の 1,169 枚の処理に使う値・登録・挙動が変わらないことを確かめました（6 章）。
- PR1-069 の名前の補正（`ENGINE_USER_CORRECTIONS`。利用者が示した訂正）・ガルーラ・ベロリンガなどの既存の修正・過去の原典照合の記録（card_verification.json）は変えていません。
  kyuura が直していない [N]・[J] のレベル・[J] の英語の名前・M・U・A のルール文の欠けは補っていません。
- テストの固定の参照データ（v0.68 までの写しの元で記録した状態の指紋など）は作り直さず、写しの元の 2 か所（`card_data.commit`・ログ `game_created` の `card_data_commit`）だけを、
  移行の連鎖を段ごとにさかのぼってもどして比べます（tests/helpers.py の `with_card_data_commit_at`。v0.69 と同じ考え方）。

## 3. 研究の基準の移行と、kyuura の論点の事例

- 研究の対応表（`kyuura_engine/data/research_links.json`）の `research_commit`・`card_data_commit` を 73a1690 にしました。`7d3f4ca` → `73a1690` の kyuura の研究の記録
  （data/sidecar/rulings.json。latest_descriptions.json・card_checks.json は変わっていない）の差分は、新しい裁定 5 件（`CR-UNOWN-DECK-LIMIT-ALL-LETTERS`・
  `CR-UNOWN-DF-PROTECTS-OWN-UNOWN`・`CR-UNOWN-DF-SOURCE-TYPE`・`CR-UNOWN-DF-AT-MOST-ONE`・`CR-UNOWN-DF-DAMAGE-STEP`）、新しい論点 1 件（`UQ-SELF-EXCLUDING-POWER-COPIES`）、
  事例・注記を加えた既存の論点 3 件（`UQ-CARD-USE-WITHOUT-TARGET`・`UQ-NON-ATTACK-DAMAGE-MODIFIERS`・`UQ-SPEED-STAR-SCOPE`）だけです。未解決の一覧（`engine_unresolved_index`。
  v0.68 までの取り込みの 156 行）・取り込みの記録（`engine_imports`）は変わっていません。kyuura の論点の数は 71 → 72 です。
- 新しい論点は kyuura の調査で立てたもので、kyuura の未解決の一覧に行がありません（kyuura の `not_in_engine_index`）。「kyuura に論点はあるが、取り込んだ版の一覧にエンジンの
  コードの行がない」ことを、「kyuura に記録がない」（`not_in_kyuura`）と分けるため、停止コードの区分 `issue_not_in_index` と、kyuura の論点の事例のうちエンジンの裁定 id のない
  もの（`kyuura_cases_without_engine_ruling`）を加えました。`scripts/check_research_links.py` は、事例の集まりが研究の基準のコミットのそのような事例のすべてと同じこと（13 件。
  v0.69 の基準からある PMCG6-044 の 1 件を含む）、エンジンの扱い（停止コード・コードのない問い・登録していない）が対応表・登録表と合うこと、`issue_not_in_index` の停止コードが
  kyuura の未解決の一覧になく、その論点の事例に結ばれていることを確かめます。停止コードの集合の比べ（kyuura の一覧のコードと対応表のコード）は緩めていません。
- わるいデンリュウの［かんでん］の CV1（`UNRESOLVED_CONDUCTIVITY_MULTIPLE_SOURCES`。v0.86）は、新しい論点の事例（neo4-046）なので `not_in_kyuura` から `issue_not_in_index`
  （`UQ-SELF-EXCLUDING-POWER-COPIES`）にしました。止める条件は変えていません（kyuura は v0.86 を取り込んでいないので、CV1 を engine_refs に結んでいない）。
- 採用の記録の `kyuura_records`（研究の基準のコミットでカードを指す kyuura の記録の id）を、7 件で新しい記録に合わせました（記録を読み直したのではなく、id の対応を直した）:
  ピジョン（PMCG1-066）・ヒノアラシ（PF1-004）に UQ-SPEED-STAR-SCOPE、エリカのハクリュー（PMCG5-066）・悪エネルギー（neo1-094）に CR-UNOWN-DF-SOURCE-TYPE、わるいデンリュウ（neo4-046）に
  UQ-SELF-EXCLUDING-POWER-COPIES、遺跡の石版（neo2-054・neo2-057）に CR-UNOWN-DECK-LIMIT-ALL-LETTERS。
