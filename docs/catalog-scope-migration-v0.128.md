# v0.128: kyuura の目録の分類の取り込みと、通常対戦の対象の整理

v0.128（版 0.128.0）は、kyuura `main` に取り込まれた目録の分類（`catalog_class`・`engine_scope`・`engine_scope_reason`）を写しの元・研究の基準に取り込み、通常対戦のエンジンの
実装の対象を、その明示の分類から求めるようにする版です。**新しいカードは登録していません**（対応カード 1,368 枚のまま）。

利用者の指定（kyuura 側の記録は 2026-10-31）で、次の 3 件を通常対戦のエンジンの実装の対象から外しました。**公式の使用禁止・裁定の変更・エラッタではありません。** カードの記録・
印刷の文面・出典・id は kyuura に残り、エンジンも id を付け直していません。

| id | 名前 | `catalog_class` | `play_scope` | 理由（kyuura の `engine_scope_reason` の要約） |
|---|---|---|---|---|
| PR1-038 | タッチ交代！ | `special_rule` | `kangaskhan_rule` | ガルーラルール専用のカード（専用ルールで使う） |
| PRN-048 | タッチ世代交代！ | `special_rule` | `kangaskhan_rule` | 新ガルーラルール専用のカード（専用ルールで使う） |
| PR1-079 | カードトレーナー認定証 | `award` | `standard` | 認定証のカード（対戦の手順を書いていない） |

タッチ系の 2 枚は、専用ルール（ガルーラルール・新ガルーラルール）で使うカードです。その事実は `play_scope` と理由の文に残しています。「遊べないカード」「公式に使用禁止のカード」とは
扱いません。専用ルールを実装するかは別の判断で、今回は**通常対戦**の対象から外しただけです。

## 1. 開始点と範囲

- エンジンの基点は `355589d432b39f8c985aafd55b8f9712ac1e9c91`（v0.127 の最後のコミット。公開済みのブランチ `claude/v0.127-deferred-shortage-user-promos` の先端）。2026-11-01 に fetch し、
  リモートの `main` が `cdde860268f95598331eb0f91ae560d3374c6293`（PR #22 で v0.127 をマージ）で、その木が 355589d の木と同じ（`246b61b…`）ことを確かめました。`main` から作業ブランチ
  `claude/v0.128-catalog-scope-migration` を作りました（`main` を追跡しない設定にした）。作業ツリーには利用者の `.claude/` のほかに変更はなく、`.claude/` はコミットに入れていません。
- kyuura は `main` の `71d1728938fb4c8fefde9b82779cdef74beb612d`（PR #7 のマージ。目録の分類とプロモの収録範囲の調査）に固定して読みました。kyuura は fetch しただけで、作業ツリー・
  ブランチ・履歴は変えていません（読むのは `git show <コミット>:<パス>` だけ。kyuura の checkout は `b9e7cff` のまま）。57d01f4 は 71d1728 の祖先です。
- 読んだ kyuura の文書: `docs/engine-handover-catalog-scope.md`（引き継ぎ）・`docs/catalog-promo-survey.md`（調査と整備の記録）・`docs/data-schema.md`（欄の意味）・`scripts/catalog.py`
  （目録の一覧の生成。`battle_records` は `catalog_class == "battle"` かつ `engine_scope == "target"`）。
- ルールの基準は公式ルール 2000.02.14 版のままです。カードの画像・外部照合・ガイドブックのキャプチャ・OCR・読み直しはしていません。
- 公開の固定デッキ・過去の版の比べ用の参照データは変えていません。`CLAUDE.md` は変えていません。
- 新規登録はしていません（とりかえっこプリーズ PR1-027・カツラのクイズ GD5-016・ひかるバンギラス neo4-082 なども対象のまま未登録）。

## 2. 写しの元・研究の基準の移行（57d01f4 → 71d1728）

この章は、カードの登録と処理の変更を加えない移行だけのコミットの記録です。

### 2.1 kyuura の差分（全データ）

`57d01f4` → `71d1728` の差分のファイル（34）のうち、データ（`data/`）は 8 ファイルです。推測で「同じ」とせず、エンジンが読むファイルはすべて中身で比べました。

| ファイル | エンジンが読むか | 差 |
|---|---|---|
| `data/cards.json` | 読む（写しの元） | 全 1,377 件の記録の集合・並び・id・既存の欄の値は**同じ**（欄ごとに比べた）。最上位の欄（`description`・`schema_version` 3・`text_availability`）も同じ。全件に 3 つの欄 `catalog_class`・`engine_scope`・`engine_scope_reason` が加わった。分類は `battle`・`target` 1,374、`special_rule`・`excluded` 2（PR1-038・PRN-048）、`award`・`excluded` 1（PR1-079）。`undecided` は 0 |
| `data/engine_targets.json` | 読む（検査・テスト） | `cards` 1,377 → 1,374（3 件を新しい `excluded_records` に移した。残りの 1,374 件は値・並びとも同じ）。`counts` に `excluded_records` 3、`by_category` の `candidate` 1,364 → 1,363・`special_rule_design` 4 → 2、`by_engine_status` の `new_effect_needed` 121 → 118 など（kyuura の一覧の数で、エンジンの数ではない） |
| `data/rule_history.json` | 読む（`errata` だけ。`check_research_links.py`） | `documents` の『オフィシャルブック2000』の読んだページに 4 件（p.122・p.251・p.300・p.301）が加わっただけ。`errata` ほかの欄は同じ |
| `data/sidecar/*.json`（最新の説明・裁定・照合） | 読む（研究の基準） | 差なし |
| `data/curation/card_corrections.json`・`card_image_checks.json`・`card_differences.json`・`other_products.json` | 読む | 差なし |
| `data/cards.csv` | 読まない | 目録の一覧になった（`non_game_items` の 18・`KC-` の 24 の行と、後ろに 6 つの欄）。エンジンは CSV を読まないので、CSV の全行を対戦用のカードとして扱うことはない |
| `data/curation/non_pack.json` | 読まない | `catalog_scope`（3 件の明示の指定）と、網羅の状況の文 |
| `data/curation/catalog_items.json`・`promo_survey.json` | 読まない | 新しいファイル（目録だけの項目 24 と、プロモの収録範囲の比較の記録） |
| `data/product_items.json` | 読まない | プロモの `standard_play_cards` 86 → 85 |

- 訂正（`card_corrections.json`）はこの段にありません。`KYUURA_CORRECTIONS` に段 v0.128 の訂正は加えていません。
- 目録だけの行（`PR1-015` ポケモンイラストレーター・`ES3-` のおまけのカード・`KC-0001`〜`KC-0024`）は `data/cards.json` にないので、エンジンの写しに入ることはありません。
  PR1-015 などが CSV に載ったことを理由に、写しへ加えていません。

### 2.2 移行の連鎖

- 段 v0.128（`57d01f4` → `71d1728`）を `scripts/extract_kyuura_cards.py` の `KYUURA_MIGRATIONS` の末尾に加えました（連鎖は ecb2d69 → 7d3f4ca → 73a1690 → e519b99 → 2fe0bc0 → 74b3ceb → b9e7cff →
  134a664 → 57d01f4 → 71d1728）。v0.126 の段の `to` は写しの元の定数を指していたので、`V0_126_KYUURA_COMMIT`（57d01f4）に固定してから写しの元を上げました。過去の段の前・あと・文書・訂正・
  採用日・外部照合の日・当時の固定コミットは書き換えていません。
- 写しを作り直した結果（手で編集していない）: `source.commit`、`source_migrations`（段 v0.128。訂正 0 件）、`engine_user_corrections` の `source_commit`、新しい `catalog_scope`（3 章）だけが
  変わりました。**写しのカード 1,368 枚の値は全欄が同じ**です（`cards` の配列が基点と同じ）。
- 採用の記録の移行（`card_sources.json` の `data_migrations`）に 9 段目（2026-11-01）を加えました。採用したときのデータのコミット・記録した日・外部照合の確認日と照らしたコミット・当時の違いの
  値は書き換えていません。研究の基準のサイドカーが同じなので、登録済みのカードの `kyuura_records` の id の対応は変わりません。対象外の 3 件は未登録で、採用の記録もありません。
- 研究の対応表: `research_commit`・`card_data_commit` を `71d1728`、`research_branch` を `main` にしました。kyuura の記録の数（最新の説明・照合・裁定・論点 90）は変わりません。停止コード 313・
  未解決の裁定 314 も同じです。
- テストの補助（`tests/helpers.py`）の写しの元の連鎖に段を加えました（`CARD_DATA_COMMIT_SINCE_V0_128`）。v0.126 の値を固定値で持っていたテストは、段の位置・57d01f4 を基準にした最後の
  コミット（355589d）の対応表で確かめる形にしました（`tests/test_flash_faceup_deck_v0_126.py`）。

## 3. 分類の欄の扱い（写しに入れない理由）

kyuura の新しい 3 つの欄は、**カードの写す欄（`FIELDS`）には加えず、抽出のときに使い**、その結果を書き出しの最上位の `catalog_scope` に残しました。

- 写しのカードはどれも対象（`battle`・`target`）なので、1,368 枚に同じ値を持たせても情報は増えません。
- 写す欄は、移行の段ごとに前のコミットと比べています（`migration_copy_problems`）。前の段のコミットにない欄を写す欄に加えると、過去の段の比べに例外が要ります。
- エンジンが知る必要があるのは、写しにない対象外の記録とその理由です（デッキの拒否の理由。4 章）。

抽出（`scripts/extract_kyuura_cards.py`）は、書き出すたびに次を確かめ、違えば書き出しません（`catalog_scope_problems`）。カード id ごとの例外の表は持たず、対象外の集合は kyuura の
明示の分類から求めます。

1. 写しの元の全記録に 3 つの欄があり、値が決まった値（`catalog_class` は `battle`・`special_rule`・`award`、`engine_scope` は `target`・`excluded`・`undecided`）。
2. 理由は `engine_scope` が `target` のときだけ null。`target` の記録は `battle`。
3. 写しのカード（対戦用の組と参照カード）はどれも対象（`battle` かつ `target`）。対象外・未判断の記録を写しに入れると止まります。
4. 分類から求めた対象の集合（並び）が、同じコミットの kyuura の `engine_targets.json` の `cards` と同じ。対象外の記録（id・名前・弾・商品・使用範囲・分類・理由）が `excluded_records` と同じ
   （kyuura の 2 つの生成物の食い違いを黙って受け入れない）。

`catalog_scope` の中身は、写しの元のコミット・3 つの欄の名前・対象を選ぶ条件（`target_rule`）・数（記録 1,377・対象 1,374・対象外 3）・対象外の記録（`excluded_records`。上の表の 3 件。
値は kyuura のまま）です。`undecided` の記録も対象ではありません（今は 0 件）。

## 4. エンジン: 対象外の記録のデッキの拒否と、混入の防止

- `cards.CardPool` に `excluded`（id → `ScopeExclusion`。写しの `catalog_scope.excluded_records` から読む）を加えました。写しのカード（`definitions`）とは重なりません（重なる写しは
  読み込みで `ValueError`）。`catalog_scope` のない写しは空です。対象外の記録は定義を持たないので、対戦で使える集合（`playable_ids`）・カツラのクイズの名前の候補
  （`effects.quiz_answer_names`。写しのポケモンの名前）・マチスの秘策などの受け付けの確かめで試すカード（`engine._identity_candidates`。`playable_ids` から）には入りません。
- デッキの検査（`deck.deck_problems`。`new_game` も同じ）は、対象外の記録を新しいコード **`OUT_OF_ENGINE_SCOPE`** で拒否します。文には id・名前・kyuura の目録の分類・使用範囲・理由を
  書きます（例: `OUT_OF_ENGINE_SCOPE: PR1-038 タッチ交代！（通常対戦のエンジンの実装の対象外。kyuura の目録の分類 special_rule・使用範囲 kangaskhan_rule: ガルーラルール専用のカード…）`）。
  v0.127 までは、3 件とも写しにないので `UNKNOWN_CARD`（このエンジンのカードデータにないカード）でした。未対応のカード（`UNSUPPORTED_CARD`）とは数えず、「使用禁止」とも書きません。
- 目録だけの行（`PR1-015` ポケモンイラストレーター・`ES3-` のおまけのカード・`KC-`）は `data/cards.json` にも写しにもないので、これまでどおり `UNKNOWN_CARD` です（エンジンのカードデータに
  ない、という事実のとおり）。
- `engine.py`・`resolution/` は変えていません（カード id による分岐はない）。書き出しの形式は 32 のまま（`excluded` は状態の項目ではない）。版は 0.128.0 です。

## 5. 数

| 区分 | v0.127（57d01f4） | v0.128（71d1728） |
|---|---:|---:|
| kyuura の `data/cards.json` の記録 | 1,377 | 1,377 |
| 通常対戦の対象（`battle` かつ `target`） | 1,377（分類なし。engine_targets.json の `cards`） | 1,374 |
| 対象外（`excluded`。理由つき） | — | 3（PR1-038・PRN-048・PR1-079） |
| 写しのカード・対応カード | 1,368 | 1,368（ポケモン 1,064・トレーナー 267・エネルギー 37） |
| 対象のうち未対応 | 9 | **6** |

- 対応カードの数は実測で 1,368 のままです（3 件はどれも未登録だった）。未対応は実測で 9 → 6 で、減ったのは対象外にした 3 件だけです。
- 残る 6 件: カツラのクイズ その1 GD5-016（ジム）・とりかえっこプリーズ PR1-027（プロモ。`play_scope` は `not_for_official_tournaments`、分類は `battle`・`target` のまま）・
  ナッシー PR1-075・PR1-077（プロモ）・ヤドキング neo1-049・ひかるバンギラス neo4-082。内訳は neo 2・拡張パック以外の商品 4。今回は登録していません。
- カツラのクイズの名前の候補（512）・受け付けの確かめの候補（1,151・たね 532・ベイビィ 13）は変わりません。対象外の記録・目録だけの行の名前（ポケモンイラストレーターなど）は入っていません。
- kyuura の `engine_targets.json` の `new_effect_needed` 118 などは、kyuura が写したエンジンの登録表（v0.113）での数で、エンジンの数ではありません。

## 6. 保持した v0.127 の仕様

- 枚数不足の途中停止（`Phase.HALTED`・`Halt.interruption`）と書き出しの形式 32、_のピカチュウ 2 枚の誕生日の条件を省く仕様・ハマちゃんのヤドキングの発話の条件を省く仕様、
  利用者の指定（`user_simplified_text`）と印刷の文面の採用（`adopted_printed_text` 1,390）を分けた記録は、変えていません（`effects.py`・研究の対応表の区分・採用の記録の該当部分は差なし）。
- とりかえっこプリーズ・カツラのクイズ その1・ひかるバンギラスなどの新規登録はしていません。

## 7. 検証

重い比べ（lockstep・前の版の組）と全体のテストは、どれも 1 つずつ順に行い、並行させていません。`PYTHONUTF8=1`・`PYTHONHASHSEED=0`、Python 3.14.6 です。コードの指紋は v0.126 の文書 13 章と
同じ求め方（kyuura_engine/・tests/・tools/・scripts/ の .py・.json と pyproject.toml の相対パスと中身（改行を LF にそろえた）の sha256。docs は含めない）です。比べに使った v0.127 の木は
`tools/engine_lockstep.py tree --commit 355589d`（`git archive`）で取り出しました。kyuura の作業ツリーは変えていません（`git fetch` と `git show` で読んだだけ）。

コミット: 移行 `dc076d7`（写しの元・研究の基準・採用の記録の移行の段だけ。カードの登録・処理の変更なし）、エンジン `51b2f4f`、文書 `6072579`。`6072579` の説明の「13 章の検証」は誤りで、検証は
この 7 章です（公開の履歴は書き換えていません）。

### 7.1 データの検査・静的な確かめ

- `scripts/extract_kyuura_cards.py --check`: 書き出しが kyuura 71d1728 と一致（分類の検査 `catalog_scope_problems` の問題 0）。`scripts/check_card_sources.py`: 採用の記録 1,281 件が方針と合う。
  `scripts/check_research_links.py`: 研究の対応表が kyuura 71d1728 の記録と一致。
- ruff（0.17.2。この作業の一時領域に基点と同じ版を入れた。プロジェクトの設定のまま）で、固定した v0.127 の木と規則・ファイルごとの数を比べ、482 → 482（ファイル・規則ごとの数がすべて同じ）。
  抑制・除外は加えていません。
- `tools/run_mutants.py check`: 50 の定義がすべて今のコードに当てはまります（定義の適用の確かめで、変異をすべて見つけたこととは別。定義は変えていない）。
- `CLAUDE.md` は 39 行のまま、変えていません。

### 7.2 前の版との比べ

- 固定した v0.127（`355589d`）の木と、この木を、別のプロセスで比べました（`tools/engine_lockstep.py`。標準 `--corpus all --seeds 10 --stress-seeds 2`。両方の木を `PYTHONHASHSEED=0` で記録）。
  - 生の指紋: 290 対戦とも歩 0 で食い違い（書き出しの `card_data.commit` が 57d01f4 と 71d1728 で違う）。これが生の差のすべての始まりで、正規化しない比べはここで止まります。
  - 正規化した比べ（`--card-data-commit 71d1728…=57d01f4…`。既存の限定した正規化で、もどすのは `card_data.commit` と `game_created` の `card_data_commit` の 2 か所だけ。分類の欄・
    `catalog_scope` は状態・記録に出ないので正規化の対象にしていない）: 290 対戦・48,092 歩・食い違い 0・許した差 0（もどして比べた歩 36,515）。両方の記録とも内部エラー 0。版は 0.127.0 と 0.128.0。
  - 時刻: v0.127 の木の記録 08:18:26〜08:21:05、この木の生の記録 08:21:13〜08:23:48、比べ用の記録 08:23:58〜08:27:58（2026-11-01）。
- 変えた経路（デッキの検査・カードの集合・名前の候補・同名の扱い・途中停止）を通る前の版の組を、固定した v0.127 の木とこの木で別のプロセスで走らせ（`tools/existing_effect_games.py --batch`。4 seed。
  1 版ずつ、それぞれの木の道具で。どちらも `PYTHONHASHSEED=0`・`-P -s`）、局ごとの記録を比べました（08:28:16〜08:38:07）。

  | 版 | 選んだ理由 | 局 | 差 |
  |---|---|---:|---:|
  | v0.63 | カツラのクイズ（名前の候補をカードの集合から作る） | 24 | 0 |
  | v0.67 | マチスの秘策（受け付けの確かめの候補をカードの集合から作る） | 32 | 0 |
  | v0.70 | 拡張パック以外のプロモとデッキの検査（対象外の 3 件と同じ商品の区分） | 32 | 0 |
  | v0.96 | デッキの同名の枚数の上限の経路（デッキの検査の変更の前後） | 32 | 0 |
  | v0.123 | 前の名前の移行・同名の扱い（写しの元の移行の前後） | 32 | 0 |
  | v0.127 | 直前の版。枚数不足の途中停止と書き出しの形式 32（27 局が終局・13 局が DU1/TW1 の途中停止） | 40 | 0 |

  192 局とも、所要時間（`elapsed`）を除いて記録が同じで、この木の内部エラー・予期しない拒否・監査の失敗は 0 です。全旧バッチの機械的な再実行・過去の参照データの再生成はしていません。
- 新しいカードの登録がないので、この版の正式な対戦の組は作っていません（変えた振る舞いはデッキの検査の拒否の理由だけで、対局の中には現れない）。

### 7.3 全体のテスト

tests/ の 240 モジュールを、1 つずつ別のプロセスで順に走らせました（1 worker。モジュールごとの時間切れ 3,600 秒。`python -s -m unittest -v tests.<モジュール>`）。

- コミット `6072579` の木（2026-11-01 08:38:55〜09:48:20。始めたモジュール 240・終えたモジュール 240。コードの指紋は実行の前後で `06a6e887…`（313 ファイル）で同じ）: 7,034 件、**失敗 0・エラー 0**・
  スキップ 1・終了コードが 0 でないモジュール 0・時間切れ 0。1 回目で失敗がなかったので、直して走らせ直したものはありません。
- スキップ: `tests.test_cross_version_compatibility.FullComparisonTest.test_no_differences`（大きな比較は `KYUURA_COMPAT_BASE` を設定したときだけ。既知）。
- 時間のかかったモジュール: `tests.test_card_sources` 472.2 秒、`tests.test_preflight_consolidation_v0_16c` 126.9 秒、`tests.test_effect_preflight_v0_3d` 102.4 秒。
- 基点（v0.127）の報告は 239 モジュール・7,018 件（1 回目の失敗 10 を直したあとの再実行で成功）。増えた 16 件は新しいモジュール `tests.test_catalog_scope_migration_v0_128` の 16 件です。
  基点の全体は走らせ直していません。

### 7.4 全体のあとに変えたもの

- 全体のあとは文書（この 7 章・8 章）と、この版の文書の見出しを確かめる `tests.test_catalog_scope_migration_v0_128.DocumentTest` の見出しの一覧（7 章・8 章を加えた）だけを変え、そのモジュールを
  やり直しました（結果はコミットの説明に書く）。

## 8. 制限・行っていない検証・kyuura への報告事項

- 行っていない確認: 新しいカードの画像・外部照合・ガイドブックのキャプチャ・OCR・読み直し（今回はカードの登録がない）。専用ルール（ガルーラルール・新ガルーラルール）の対戦は実装も検証もしていません。
- lockstep・前の版の組はデッキの検査を通るデッキだけを使うので、対象外の 3 件の拒否は対局の比べでは確かめていません。拒否の理由・目録だけの行との区別は 4 章のテスト（`DeckScopeTest`）で確かめました。
- kyuura の分類と `engine_targets.json` の一致は、抽出のときに機械で確かめます（3 章）。分類そのもの（どの記録を対象外にするか）の正しさは利用者の指定と kyuura の記録によるもので、エンジンでは判断していません。
- kyuura への報告事項（kyuura は変えていない）: `engine_targets.json` の状態ごとの数（`new_effect_needed` 118 など）は、kyuura が写したエンジンの登録表（v0.113）での数で、今のエンジン（対応 1,368・
  未対応 6）とは違います。古い写しであることが読み手にわかる書き方にするかは kyuura 側の判断です。
