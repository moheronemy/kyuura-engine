# v0.114: ベイビィポケモン 13 枚・ベイビィの共通のルール・ベイビィからの進化

v0.114 は、ベイビィポケモン 13 枚（ワザ 11・特殊能力 2）を、ベイビィの共通のルール（デッキ・対戦準備・ベンチに出す・ワザを使う前のルールのコイン・ベイビィからの進化・場の分類）とともに
登録する版です。作業は 3 つのコミットに分けました。

1. 写しの元・研究の基準の移行だけのコミット（2 章。カードの登録・挙動は変えない）
2. ナツメのESPのやり直しのあとに、入れ替えの結果を運ばない不具合の限定した修正（3 章）
3. ベイビィ 13 枚と共通の処理（4 章以降）

## 1. 開始点と範囲

- 確認済みの完成版は v0.113 `2d113b5eeea0dbd4f7466e144f7a1345494405c0`（ブランチ `claude/v0.113-variable-coins-search-attachments`。リモートにある）。作業を始めたとき（2026-10-28）、
  リモートの `main` は `9e8ca5c1b9dad66afcf8cde8d534f51745d1cbac`（v0.105 を取り込んだマージ）のままで、v0.113 の祖先でした。リモートに v0.113 より後のコミットはなく、作業の木の
  未コミットのものは未追跡の `.claude/`（この作業のものではない。コミットしない）だけで、stash もありません（会話の始めの状態の一覧に出ていた変更済みのファイルは、改行の扱いの
  古い表示で、`git diff` に差はありませんでした）。
- 作業ブランチ `claude/v0.114-baby-rules-evolution` を最新の `main`（`9e8ca5c`）から作り、v0.113（`2d113b5`）を早送りで取り込みました（マージのコミットはない。実際の開始点は `2d113b5`）。
  作った時点の追跡先（`main`）は外し、同じ名前のリモートのブランチにだけプッシュします。`main`・既定のブランチ・kyuura・公開の固定デッキ・過去版の比較用の参照データは変えていません。
- 新しく採用した kyuura は `e519b99e2adcc6c2cd0998569ae5ee1101de6e89`（ブランチ `claude/baby-data-engine-v0113-handover`。親は `73a169063463bbf7bcaa3137d70cbf9721d11534`。kyuura の
  `main` には未取り込みの、公開済みの固定コミット）。kyuura の PR・マージ・変更はしていません。読んだもの: `docs/baby-preparation-engine-v0.113.md`・`docs/engine-handover-baby-v0.113.md`・
  `data/cards.json`・`data/curation/card_image_checks.json`・`data/curation/card_corrections.json`・`data/sidecar/rulings.json` のベイビィの条項・裁定・論点。
- ルールの基準は公式ルール 2000.02.14 版のままです（neo 期のカードにも同じ基準）。公式ガイドブック・Silver Bible の新しいキャプチャ・OCR・読み直し、カードの画像の照合は、エンジンでは
  していません。英語版の文面・現代のルール・後年の裁定で日本語の不足を補っていません。

## 2. 写しの元・研究の基準の移行（73a1690 → e519b99）

この章は、カードの登録・挙動を変えない移行だけのコミットの記録です（13 枚はこのコミットでは写しに入れていない）。

### 2.1 kyuura の差分

`73a1690` → `e519b99` の `data/cards.json` を全 1,377 件で比べました（形式 3 のまま。カードの追加・削除・並びの変化はない。`schema_version`・`description`・`text_availability` も同じ）。
値が変わったのはベイビィ 13 枚だけで、写し（1,250 枚）のカードの値は同じです。

| 変わった欄 | カード |
|---|---|
| `pokemon.rules_text.ja`（null → ルール文）・`data_gaps`（その欄が消えた） | neo1-022・neo1-042・neo1-044・neo1-070・neo2-033・neo2-050 の 6 枚 |
| `pokemon.evolves_to`（新しい欄。日本語名の配列。印刷の順） | 13 枚 |
| `corrections`（台帳の訂正の記録）・`notes` | 13 枚 |

kyuura の台帳（`data/curation/card_corrections.json`）には 19 件の訂正（ルール文 6 件 `FIX-<id>-RULES-TEXT-JA`・種類 `transcription_omission`、進化先 13 件 `FIX-<id>-EVOLVES-TO`・種類
`field_added_from_print`。どれも根拠 `card_image_check`）が加わり、既存の訂正は変わっていません。画像の照合の記録は新しいファイル `data/curation/card_image_checks.json`（`IMG-<id>`。
13 件）で、訂正の記録は画像の URL・sha256 を直接持たず、`image_check` でこの記録を指します（v0.97 のアンノーンI・D・F の訂正は記録の `evidence` に画像を持つ）。画像を見たのは kyuura で、
エンジンは画像を見ていません。

### 2.2 移行の連鎖

段 v0.114（`73a1690` → `e519b99`）を `scripts/extract_kyuura_cards.py` の `KYUURA_MIGRATIONS` に加えました（連鎖は ecb2d69 → 7d3f4ca → 73a1690 → e519b99）。

- v0.113 までの v0.97 の段の `to` は、写しの元の定数 `KYUURA_COMMIT` を指していました。そのまま定数だけを上げると、過去の段のあとまで e519b99 に変わります。v0.97 の段の `to` を
  `V0_97_KYUURA_COMMIT`（73a1690）に固定してから、写しの元（`KYUURA_COMMIT`）を e519b99 に上げました。v0.69・v0.97 の段の前・あと・文書・修正は書き換えていません。
- 採用の記録の移行（`card_sources.json` の `data_migrations`）に 3 段目（2026-10-28）を加えました。採用したときのデータのコミット（ecb2d69・7d3f4ca・73a1690）・記録した日・外部照合の
  確認日と照らしたコミット・既存の `ENGINE_USER_CORRECTIONS`（PR1-069 の名前）は書き換えていません（`ENGINE_USER_CORRECTIONS` の確かめは今の写しの元で通る。kyuura は PR1-069 の名前を
  まだ直していない）。
- 写しの作り直しの検査（`kyuura_correction_problems`・`previous_copy_problems`・`migration_copy_problems`）は、段ごとに、写しの組のカードの写す欄が、その段の修正の欄と出典の記録の欄を
  除いて同じことを確かめます。この段に当てはめた修正は、写しの組のカードにはありません（19 件はどれも写しの外の 13 枚。`source_migrations` の段 v0.114 の `corrections` は空）。
  写しの組のカードに台帳の知らない修正があれば書き出さない既存の検査は、そのままです。
- kyuura の対象の一覧（`data/engine_targets.json`）は、e519b99 で登録表の写しをエンジン v0.113 から作り直したので、v0.69・v0.71 で選んだカード（`mechanically_equivalent`・
  `reuse_candidate`）はどれも `registered` になり、選んだときの欄（`equivalent_to`・`nearest_registered`）もなくなりました。写しの `equivalent_targets`・`reprint_targets`（選定の記録。
  値は書き換えない）は、登録表の写しが v0.68 のままだった最後の写しの元 73a1690 の一覧から読みます（`TARGET_SELECTION_COMMIT`。v0.113 までは写しの元と同じコミットだったので、
  写しの値・コミットは同じ）。今の写しの元の一覧で、選んだカードがどれも `registered` であることを確かめます（`current_target_status_problems`）。
- 写しを作り直した結果（`python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura`。手で編集していない）: `cards`（1,250 枚）は v0.113 と同じ（値の違いなし）で、変わったのは
  `source.commit`・`source_migrations`（段 v0.114 を加えた）・`engine_user_corrections` の `source_commit` だけです。
- テストの固定の参照データ（v0.68 までの写しの元で記録した状態の指紋など）は作り直さず、写しの元の 2 か所（`card_data.commit`・ログ `game_created` の `card_data_commit`）だけを、
  移行の連鎖を段ごとにさかのぼってもどして比べます（tests/helpers.py の `with_card_data_commit_at` に段 v0.114 を加えた）。

### 2.3 研究の基準の移行

研究の対応表（`kyuura_engine/data/research_links.json`）の `research_commit`・`card_data_commit` を e519b99 にしました（`research_branch` は、このコミットのあるブランチ
`claude/baby-data-engine-v0113-handover`）。`engine_import_id`（`ENGINE-46A3E2E`。kyuura がエンジンの照合の記録を取り込んだ取り込みの id で、最新の取り込みの id ではない）は変えていません。

`73a1690` → `e519b99` の研究の記録の差分（`data/sidecar/latest_descriptions.json` は変わっていない。`data/sidecar/card_checks.json` は、サカキのニャース（PMCG6-063）の照合の記録
CC-PMCG6-063-P229 に、PR1-078 との対応の追記（`later_notes`。2026-10-27。原典は読み直していない）を加えただけ。照合の結果・`checked_fields`・確認日は変わっていない）:

| 区分 | 加わった・変わった記録 |
|---|---|
| 一般の条項（8） | GR-2000-P308-BABY-SETUP・GR-2000-P309-BABY-BENCH・GR-2000-P313-POKEMON-COMPOSITION・GR-2000-P314-BABY-RULE・GR-2000-P310-BABY-EVOLUTION・GR-2000-P315-EVOLVED-BABY・GR-2000-P323-ATTACK-FAILURE・GR-2000-P325-PRE-NEO-BABY |
| 裁定（6） | CR-BABY-RULE-COIN（CONFIRMED）・CR-BABY-RULE-COIN-STEP（SUPPORTED）・CR-BABY-RULE-NOT-POWER（SUPPORTED）・CR-BABY-WITHOUT-ATTACKS（SUPPORTED）・CR-NEUTRAL-SHIELD-EVOLVED-BABY（CONFIRMED）・CR-DEVOLUTION-SPRAY-EVOLVED-BABY（CONFIRMED） |
| 論点 | 新しい UQ-NEO-TEXT-BABY-CATEGORIES、事例を加えた UQ-ATTACK-PRE-DAMAGE-COIN-ORDER（ベイビィのコイン。neo1-042 の「card」） |
| 取り込み・エンジンの記録 | ENGINE-2D113B5（v0.113 の報告事項。`no_ruling_tables`）、`engine_positions` の 4 件（ESPの 3 件・ゆうでんの FC1） |
| 確かめ方の区分 | `checked_values` に `existing_transcription`（kyuura の既存の転記 data/Silver_Bible_structured.md の文。kyuura は原典の画像でこの文を確かめていない） |

- kyuura の研究の論点は 72 → 73 です。これはエンジンの未解決の裁定 238・停止コード 237 とは別の数です（kyuura の未解決の一覧 `engine_unresolved_index` は v0.68 までの取り込みの
  156 行のままで、kyuura が v0.69〜v0.112 をすべて取り込んだとは読んでいません）。この移行で既存の問いを解決済みにしていません。
- 採用の記録の `kyuura_records`（研究の基準のコミットでカードを指す kyuura の記録の id）を、7 件で新しい記録に合わせました（記録を読み直したのではなく、id の対応を直した）:
  退化スプレー（PMCG1-086）に CR-DEVOLUTION-SPRAY-EVOLVED-BABY、ミュウ（PR1-005・PR1-012）に CR-NEUTRAL-SHIELD-EVOLVED-BABY、すごいつりざお（neo1-074）・退化スプレーHYPER（neo2-056）・
  ポケモン育て屋夫婦（neo3-056）・イントロパック★neo のマスターボール（NIP1-021）に UQ-NEO-TEXT-BABY-CATEGORIES。
- kyuura の論点の事例のうちエンジンの裁定 id のないもの（`kyuura_cases_without_engine_ruling`）に 7 件を加えました。移行のコミットの時点ではベイビィのカードを写しに入れていないので、
  ベイビィのコインの事例（neo1-042）と、登録していないいかく（neo3-049）・げんしのしずく（neo4-038）は `unregistered`、登録しているトレーナー 4 枚の事例は、コードのない問い
  NB0（`neo_text_baby_categories`。今の写しにベイビィのカードがないので起こらない。`reachable_with_current_cards` は偽、エンジンの未解決の数に入れない）に結びました。
  カードを実装したあとの扱いは 4 章以降に書きます。
- 研究の固定元の新しい確かめ方 `existing_transcription` を根拠に持つ条項・裁定は、kyuura の分類（`checked`）のまま使い、kyuura が原典を画像で確かめたかとは分けて記録します
  （CONFIRMED だから画像で確かめた、とはしない）。

### 2.4 移行の確かめ

移行のコミットでは、写し・採用・研究の 3 つの検査と、移行に関係する既存のテストを走らせました（全体のテストは最後のカードの実装のあとに 1 回）。結果は 12 章に書きます。

## 3. ナツメのESPのやり直しのあとの入れ替えの結果（限定した修正）

kyuura の `ENG-V0113-ESP-REDO-SWITCH-RESULT`（`engine_positions`。状態 `not_fixed`）と v0.113 の文書 9.2 節の、v0.113 の残件です。エンジンの不具合の修正で、公式の裁定・kyuura の論点（UQ-）の
解決にはしていません。v0.113 で直したトラッシュ・ダメージの結果の運び（`discarded_results`・`damage_results`）は変えていません。

### 3.1 不具合

ナツメのフーディン（PMCG6-053）に手札のナツメのESP（PMCG6-087）を通常の操作（`PlayTrainer`・`ResolveDecision`）でつけ、超の色マーカーをのせたわるいアリアドス（neo4-011）の
「からめとる」（要素 `FailWithoutOpponentBench` → `ForceSwitch(carry=True)` → `Status(PARALYSIS, local_coin=HEADS, after_switch="switch")`）を［サイコリンク］で使うと、入れ替えのあと
マヒの要素のコインでESPのやり直しを聞きます。v0.113 までの続きの情報（`AttackRun.suspend` の `esp`）は、前の要素の入れ替えの結果（`ForceSwitch` が `fs.results["switch"]` に置く、入れ替えて
出た控えの番号）を運ばず、答えのあとにもう一度処理するマヒの要素が「入れ替えなかった」と読んで、新しく出てきたポケモンへのマヒを黙って省いていました。

固定した v0.113 の木（`git archive 2d113b5` で取り出した木）で、同じ盤面（ナツメのフーディンに草・水、相手のベンチ 2 匹）を通常の操作で作って確かめた結果: やり直さない「おもて」・やり直して
「うら」→「おもて」のどちらでも、新しく出てきたポケモンはマヒになりませんでした（内部エラーではなく、黙って省く）。

### 3.2 修正

- ESPの決定の続きの情報に、やり直しのあとの要素が名前で読む入れ替えの結果を `switched_results`（(名前, 入れ替えて出た控えポケモンの番号)）で運び、答えのあとに `AttackRun.restore` で
  もどします（読まなければ書かない。v0.113 までの決定の形は変えない）。入れ替え・コインを処理し直したり、前の処理全体・クロージャを保存したりしていません（運んだ値を読むだけ）。
- 不変条件（`engine._esp_redo_decision_problems`）: 運んだ入れ替えの結果は (名前, 番号) で、この番のワザを使ったプレイヤーの入れ替えのログ（`forced_switch`）の新しい対戦ポケモンで、
  相手の場にいる。
- ほかの同じ形の読み手: 登録したすべてのワザの要素の並び（`programs.BUILDERS`）で、名前で結果を書く要素（`name` の項目）と、そのあとの要素が名前で読む結果（`_result_names`）と、
  そのあいだ（読む要素を含む）にコインを投げうる要素（クラスと基本となるダメージの値のソースに `flip(` がある。広めに数える）のある組を探しました。続きの情報で運ばない種類の結果（入れ替えの
  番号・真偽の値・`LookedCount`・`MarkersRemoved`・`DealtTotal`）を、実際にコインを投げる要素があとで読む並びは、からめとるだけでした（ほかの候補は、読む要素がコインを投げない並び。
  たとえばキョウのベトベターの「ベトベトハンド」（PMCG6-007）は、コインが入れ替えの要素の中にあり、マヒの要素はコインを投げない）。
- 運べない種類の結果を、やり直しのあとの要素が読む並びが今後加わったときに黙って省かないよう、ESPを聞く前に確かめ、`UNSUPPORTED_ESP_CONTINUATION`（エンジンの未対応。先読みが宣言の前に
  見つけ、状態を変えない）で止めます（`AttackRun._esp_carry_check`。今の写しの並びでは起こらない）。研究上の未解決ではないので、研究の対応表の停止コードには入れていません。

### 3.3 確かめたこと

`tests/test_baby_rules_evolution_v0_114.py` の `EspSwitchContinuationTest`: やり直さない「おもて」・「うら」、やり直して「うら」→「おもて」・「おもて」→「うら」で、採った最後の面が「おもて」の
ときだけ入れ替えた控えがマヒ。入れ替えのログ・マヒのログは 1 回、ワザのコインは最初の 1 枚とやり直しの 1 枚。入れ替え先の決定・ESPの決定をまたいで clone・deepcopy・pickle から同じ続き。
ESPの決定への不正な答え（決めるプレイヤーの違い・選べない値・重複）は状態・乱数・ログ・決定を変えない。運んだ値を除いた v0.113 までの続きの形ではマヒを省く。不変条件の違反と
`UNSUPPORTED_ESP_CONTINUATION`（登録の型の並びを一時的に置きかえて作る）。v0.113 の `EspRealPathTest` の 5 件はそのまま通ります。

- 訂正（文書）: v0.113 の文書の 2.1 節・11 章が CC-PMCG6-063-P229 を「カスミのニャース」の照合の記録と書いていたのは誤りで、対象はサカキのニャース（PMCG6-063）です（v0.113 の文書を
  訂正した）。PR1-078（ロケット団のニャース）のレベルは欠けたままで、補っていません。
