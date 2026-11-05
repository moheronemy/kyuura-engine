# 実装上の仮定・採用仕様・簡略化の一覧

この文書は、厳密モード・プレイ用モードの基礎集合を確定する準備（判断事項 DEC-BASELINE-CENSUS の材料）として、現行エンジンが公式資料で確定していない部分をどう補って処理して
いるかを数え上げた記録です。**調査・照合・分類・文書化だけです。** 仮定の採否・モードの実装・裁定の変更・既存の動作の変更はしていません。エンジン・既存のテスト・カードの登録・
カードデータ・固定デッキ・参照データ・kyuura・利用者の `.claude/` は変えていません。

**一覧に載せたことは、基礎集合に入れたことを意味しません。** 採否は判断事項（[ruleset-mode-decisions.md](ruleset-mode-decisions.md) の DEC-BASELINE-NONUSER・
DEC-CARD-DATA-CORRECTIONS）で利用者が決めます。研究の論点（UQ-…）・停止コード（UNRESOLVED_…）は、この一覧で解決済みにしていません。

- 構造化した台帳（正本）: [implementation-assumptions.json](implementation-assumptions.json)
- 検査と表の生成: `python scripts/check_implementation_assumptions.py --check`（`--write` で集計と下の表を台帳から書く。`--sites` で今の木の候補箇所と台帳を比べる）
- 候補箇所の抽出: `scripts/implementation_assumptions_scan.py`（読むだけ）

## 1. 基点と範囲

| 項目 | 値 |
|---|---|
| 基点 | `d060a0ab6511ba01710c63db2779a3fd45ec042a`（`origin/main`。PR #33 のマージ）。規約集合の設計の最終コミット `d89a023c15613752505e6bad6b9a6c8c28a2e356` と同じ木。版 0.138.0 |
| 公開ブランチ | `origin/claude/ruleset-mode-design`（d89a023）・v0.136〜v0.138 の公開ブランチは、どれも基点に含まれる |
| 作業ブランチ | `claude/implementation-assumptions`（基点から作った） |
| kyuura（固定研究基準） | `71d1728938fb4c8fefde9b82779cdef74beb612d`（`research_links.json` の `research_commit`・`card_data_commit`）。記録は `git show 71d1728:<path>` で読んだ |
| kyuura（その他） | ローカルの checkout `b9e7cff`（2026-10-31。固定コミットの祖先で、より古い）・`origin/main` `9242b9b`。読んだだけ。どの記録をどの時点で読んだかは台帳の `kyuura` |

kyuura の記録の時点の区別:

- 利用者指定の kyuura 側の記録は `docs/engine-user-promo-simplifications.md`・`docs/engine-user-swap-ownership.md` の 2 つだけで、どちらも**固定研究基準 71d1728 にある**
  （ローカルの checkout にはない。`9242b9b` の同じファイルは同じ内容）。v0.129・v0.131〜v0.134 の指定に当たる kyuura の記録はない。
- カツラのクイズ その1 の身長の値（kyuura `9242b9b`）は**固定研究基準より後の記録**です。両者の関係はこの一覧では確かめていません。
- v0.128 の目録の分類の「kyuura 側の記録（2026-10-31）」の時点は確かめていません。

### 1.1 調べた範囲

- **文書**: `docs/*.md` の 267 文書をすべて走査し、候補の語のある 204 文書を読んだ（設計の作業で数えた「78 文書」は「実装上の仮定」の語の数で、入口として使い、完成条件にしていない）。
- **コード・テスト・スクリプト**: `kyuura_engine/`・`tests/`・`scripts/` の候補の語のある行（コメント・docstring）と、各項目の実装・テスト。
- **キーワードのない固定順序・既定値・フォールバック**: 版の文書を読む中で見つけたもの（`found_by: keywordless_review`）と、エンジンの主要 13 モジュールの見直し（台帳の
  `keywordless_review_scope`。モジュールごとに、読んだ範囲と見つからなかったことを記録。`decisions.py`・`movement.py` は冒頭と語の検索だけ）。
- **既存の台帳**: 停止の方針の台帳（`stop-policy-classification.json`）の規約 18 対象、棚卸し（`pre-freeze-gap-inventory.json`）、研究の対応表（`research_links.json`）。

候補の語（`scripts/implementation_assumptions_scan.py` の `KEYWORDS`）: 実装上の仮定・実装上の読み方・採用した仕様・採用の仕様・類推・正規化・結果が同じ・結果は同じ・
結果が変わらない・結果は変わらない・後年の資料・簡略化・簡略ルール・利用者指定・利用者の指定・利用者が指定。**語に当たったことは仮定であることを意味しません。** 前後の説明・
コード・テストを読んで、候補箇所ごとに整理しました（項目の主な記載 `item`・繰り返し `merged`・除外 `excluded`・未確認 `unconfirmed`）。

## 2. 正本と参照の分担

| 情報 | 正本 | この一覧での扱い |
|---|---|---|
| 項目（仮定・採用仕様・正規化の内容・適用条件・状態・群・別の扱いの影響）・候補箇所の整理・食い違い・採否判断の順序の案 | **この一覧の台帳** | 持つ |
| 合意・基礎集合の区分・18 対象の承認の記録 | 停止の方針の台帳 `conventions`（`scripts/build_stop_policy_classification.py`） | ID を `ledger_refs` で引くだけ。承認の文は台帳と同じものを引き、`--check` が根拠の文書にあることを確かめる |
| 停止コード・問題の項目（PSP-*・GAP-*） | 棚卸し・停止の方針の台帳 | 複製しない（除外の理由に参照だけ） |
| 研究の論点・停止コードの対応 | `research_links.json` | 参照だけ。論点の状態を変えない |
| 利用者指定の挙動 | エンジンの登録の記録（`effects.USER_SIMPLIFICATIONS` など） | 参照だけ |
| 採否 | 判断事項（ruleset-mode-decisions.md・stop-policy-decisions.md） | この一覧では決めない |

停止の方針の台帳の `mode_policy_status`・判断事項の状態は変えていません。

## 3. 分類の基準

| 分類 | 意味 | 主要な一覧 |
|---|---|---|
| 1 `official_direct` | 公式情報から直接確定している | 除外（理由 `official_direct`） |
| 2 `inference` | 公式情報からの推論・類推を含む（SUPPORTED の記録を含む。SUPPORTED の印だけで仮定と断定しない） | ○ |
| 3 `normalization` | 結果が同じことを根拠にした実装上の正規化（何と何を比べたか・成立条件・検証範囲を `equivalence` に記録） | ○ |
| 4 `engine_adopted` | 公式では決まらないが、エンジンが採っている挙動（エンジンの簡略化を含む） | ○ |
| 5 `later_source` | 後年・別版・別言語の資料を限定的に採用 | ○ |
| 6 `user_specified` | 利用者の明示指定（指定の文・日・文書があるものだけ） | ○ |
| 7 `data_correction` | データ訂正・表記・目録の扱い（カードデータの層） | 項目として記録（基礎集合は DEC-CARD-DATA-CORRECTIONS） |
| 8 `implementation_method` | 純粋な実装方式・最適化・状態の持ち方・ログ・API の形 | 主に除外。対戦の識別に関わる 4 件だけ項目 |
| 9 `unresolved_stop` | 未解決として停止している | 除外 |
| 10 `defect_or_unsupported` | 不具合・未対応・確認不足・内部ガード・探索上限・情報漏れ | 除外（内部ガード・探索上限・情報漏れの保護を規約として数えない） |

状態（`status`）: `adopted_current`（現行コードで採用中を確かめた）・`documented_impl_unverified`（文書にはあるが実装を確認できない。**実装されていないとは読まない**）・
`superseded`（以前は採用したが後の版で変わった）・`merged_duplicate`（他の項目へ統合した重複記載。ID は残す）・`unconfirmed`。

群（`baseline_group`。採否の判断材料。**採否ではない**）: `approved_user`（承認済み指定として基礎集合に含まれる）・`needs_decision`（追加の採否判断が要る）・
`needs_research`（研究で確認すべき）・`technical`（実装方式で、規約として識別する必要が薄い。この群に入れたことも案で、未決）・`defect_separate`・`history`。

確認の段階（`verification`）: `doc`（文書の記載）・`code`（コードの処理）・`tests_read`（既存テストの内容）・`tests_run`（今回選んだテストを実行）・`reach_unconfirmed`
（別の扱いの影響の軸に未確認がある。到達経路・影響は未確認）。テストがあることは公式根拠でも利用者承認でもありません。テストの期待値を裁定の根拠にしていません。

別の扱いにすると変わる結果（`alternative_impact`）は、勝敗 `outcome`・合法操作 `legal_actions`・カードの移動 `card_movement`・乱数順序 `rng_order`・公開情報 `public_info`・
保存再生 `save_replay` に分け、確かめていない軸は `unconfirmed` のままにしました（推測で埋めない）。

### 3.1 項目の単位と数え方

- 同じ仮定が複数の版の文書に繰り返されていれば 1 項目にまとめ、`doc_refs` に参照（`role`: primary・repeat・summary・history）を列挙しました。
- 同じ言い回しでも適用条件・結果が違えば分けました（例: エナジートランス・あまごい・ダメージスワップの「1 回 1 枚・1 個」は別の項目。山札を切るかの扱いは効果ごとの項目）。
- ID は `IA-` と意味のスラッグで、行番号・掲載順に依存しません。統合した重複は `merged_duplicate` として ID を残し、`merged_into` で統合先を指します。
- **規約数と適用対象を分けて数えます。** 利用者指定は 9 規約（USER-ID の数）で、登録対象はカードの位置 12（台帳の `targets_registered`）。停止の方針の台帳の「18 件」は登録対象の数
  （利用者指定 12・エンジンの簡略化 2・実装上の仮定 3・データの訂正 1）で、この一覧では 16 項目に当たります（下の 7 章）。

## 4. 集計

<!-- generated:counts begin（scripts/check_implementation_assumptions.py --write が台帳から書く。手で直さない） -->
| 集計 | 値 |
|---|---|
| 走査した文書（docs/*.md） | 267 |
| 候補箇所のある文書 | 204 |
| 候補箇所のあるファイル（文書・コード・テスト・スクリプト） | 319 |
| 候補箇所（行） | 1553 |
| 候補箇所の内訳（面） | doc 1004・kyuura_engine 237・scripts 138・tests 174 |
| 候補箇所の整理 | excluded 663・item 168・merged 722 |
| 除外の理由 | data_correction 2・defect_or_unsupported 13・implementation_method 182・meta_reference 321・negation 78・official_direct 5・other 29・unresolved_stop 33 |
| 項目（重複記載を含む） | 287 |
| 重複統合後の項目 | 272 |
| 分類別（重複統合後） | data_correction 3・engine_adopted 78・implementation_method 4・inference 111・later_source 1・normalization 66・user_specified 9 |
| 状態別（すべての項目） | adopted_current 257・documented_impl_unverified 13・merged_duplicate 15・superseded 2 |
| 群別（重複統合後） | approved_user 9・history 2・needs_decision 159・needs_research 48・technical 54 |
| 主要な一覧（分類 2〜6） | 265 |
| 　うち現行コードで採用中 | 250 |
| 　うち利用者承認あり | 9 |
| 　うち利用者承認なし | 256 |
| 　うち状態が未確認・実装を確認できない | 13 |
| 　うち未確認事項を持つ | 153 |
| 　確認の段階（該当する項目の数。重なる） | doc 256・code 250・tests_read 162・tests_run 14・reach_unconfirmed 248 |
| 　うち文書の記載だけを確認 | 15 |
| 承認ありの項目（データの訂正を含むすべての分類） | 10 |
| 利用者指定の規約（USER-ID の数） | 9 |
| 利用者指定の登録対象（カードの位置の数） | 12 |
| キーワードのない見直しで見つけた項目 | 26 |
| 食い違い | 54 |
<!-- generated:counts end -->

読み方:

- 除外した候補箇所の多くは、語に当たっただけの方針・台帳の説明（`meta_reference`）、仮定がないことの記載（`negation`）、実装方式（`implementation_method`）です。
- 主要な一覧（分類 2〜6）のうち、利用者承認があるのは利用者指定の 9 規約だけです。**ほかはどれも利用者の個別の承認の記録がありません**（通常のカード登録の依頼を、仮定への承認と
  読み替えていません）。
- `adopted_current` は「現行コードで処理を確かめた」で、公式に正しいことでも、採用を承認したことでもありません。

## 5. 承認の扱い

### 5.1 承認済みの利用者指定（基礎集合に含まれる。合意 AGR-MODE-BASELINE-USER）

<!-- generated:items-approved begin（scripts/check_implementation_assumptions.py --write が台帳から書く。手で直さない） -->
| ID | 名称 | 分類 | 状態 | 承認 | 対象 | 確認 |
|---|---|---|---|---|---|---|
| `IA-USER-BILINGUAL-NAME-JAPANESE` | ナッシー［Exeggutor］の英語併記を判定に使わない | 6 | adopted_current | あり | PR1-075 ナッシー［Exeggutor］の名前・進化元・ワザ名・PR1-077 ナッシー［Exeggutor］の名前・進化元・ワザ名 | doc・code・tests_read・tests_run・reach_unconfirmed |
| `IA-USER-BIRTHDAY-COIN-ONLY` | おたんじょうびの誕生日の条件を省く | 6 | adopted_current | あり | PR1-044 _のピカチュウ ワザ 0 おたんじょうび・PR1-090 _のピカチュウ ワザ 0 おたんじょうび | doc・code・tests_read・tests_run・reach_unconfirmed |
| `IA-USER-DESTRUCTIVE-FIRE-DECLARE-ORDER-UP-TO` | はかいのほのおの宣言の条件・順番・不足 | 6 | adopted_current | あり | neo4-082 ひかるバンギラス ワザ 1 はかいのほのお | doc・code・tests_read・tests_run・reach_unconfirmed |
| `IA-USER-MIND-GAMES-OPTIONAL-BEFORE-COST` | ［ちえくらべ］は任意・使えるかの確認のあと支払いの前 | 6 | adopted_current | あり | neo1-049 ヤドキング ［ちえくらべ］ | doc・code・tests_read・tests_run・reach_unconfirmed |
| `IA-USER-MOUNTAIN-CRUSH-MILL-UP-TO-DECK` | マウンテンクラッシュは山札の枚数までトラッシュ | 6 | adopted_current | あり | neo4-082 ひかるバンギラス ワザ 0 マウンテンクラッシュ | doc・code・tests_read・tests_run・reach_unconfirmed |
| `IA-USER-QUIZ-HEIGHT-OFFICIAL-ZUKAN` | カツラのクイズ その1 の正解に公式図鑑の身長 | 6 | adopted_current | あり | GD5-016 カツラのクイズ その1 の正解 | doc・code・tests_read・tests_run・reach_unconfirmed |
| `IA-USER-SPOKEN-CONDITION-IGNORED` | こまったなあ・どつくの発話の条件を省く | 6 | adopted_current | あり | PR1-072 ハマちゃんのヤドキング ワザ 0 こまったなあ・PR1-072 ハマちゃんのヤドキング ワザ 1 どつく | doc・code・tests_read・tests_run・reach_unconfirmed |
| `IA-USER-SUDDEN-DEATH-OWNERSHIP-RESET` | 延長戦の開始で交換したカードを出所へもどす | 6 | adopted_current | あり | StartSuddenDeath（延長戦を始める操作）のときの、とりかえっこプリーズで所有者が変わったカード | doc・code・tests_read・tests_run・reach_unconfirmed |
| `IA-USER-SWAP-OWNERSHIP-RECEIVER` | とりかえっこプリーズで交換した 2 枚の所有者は受取側 | 6 | adopted_current | あり | PR1-027 とりかえっこプリーズで交換が成立した 2 枚 | doc・code・tests_read・tests_run・reach_unconfirmed |
<!-- generated:items-approved end -->

各項目の承認の根拠（文書・日・指定の文）は台帳の `approval.evidence` にあり、停止の方針の台帳の記録と同じ文です。照合したこと（統括。対象 ID は写しの名前で確認）:

| 既存の指定 | 対象（写しで確認） | 根拠 | 確かめた範囲と、指定に含まれない隣の場面 |
|---|---|---|---|
| 誕生日・発話条件の省略 | PR1-044・PR1-090（_のピカチュウ おたんじょうび）、PR1-072（ハマちゃんのヤドキング こまったなあ・どつく） | v0.127 4.1 節（2026-11-01） | 指定は省く条件だけ。名前「_のピカチュウ」の扱い・コピーへの当てはめ（`IA-BLANK-OWNER-NAME-PIKACHU-LITERAL`・`IA-SIMPLIFICATION-COPY-SCOPE`）は指定の文の外で、承認なし |
| 公式図鑑の身長参照 | GD5-016 カツラのクイズ その1 | v0.129 3 章（2026-11-01） | 指定は参照値。整数 cm の完全一致・図鑑番号だけで引くこと（`IA-QUIZ-HEIGHT-EXACT-INTEGER-CM`・`IA-QUIZ-HEIGHT-DEX-ONLY-LOOKUP`）はエンジンの解釈 |
| 交換後の所有者 | PR1-027 とりかえっこプリーズ | v0.130 3 章（2026-11-01） | 指定は受取側を所有者にすること。再交換・つけたカード・デッキの制限の細部（`IA-SWAP-OWNERSHIP-SCOPE-EXTENSIONS`）は kyuura の仕様の書き起こしと実装の解釈で、指定の文そのものではない |
| 延長戦での所有者リセット | StartSuddenDeath | v0.134 2.2 節（2026-11-02） | 指定の文は「元の所有者へ戻す」。再交換のときに最初の出所へもどす読みはエンジンの解釈（`DISC-SUDDEN-DEATH-ORIGIN-READING`） |
| ナッシーの日英併記 | PR1-075・PR1-077 ナッシー［Exeggutor］ | v0.131 3 章（2026-11-01） | 判定に使わないことが指定。ログ・観測での名前の使い方・研究の事例の分類（`IA-BILINGUAL-NAME-JUDGED-NAME-ALL-PATHS` の一部）は指定の文の外 |
| ちえくらべの任意性と時点 | neo1-049 ヤドキング［ちえくらべ］ | v0.132 3 章（2026-11-01） | 錯乱ジムとの前後（MG1）は含まれない。機会を出す範囲・使わない枝の先読みはエンジンの解釈 |
| ひかるバンギラスの処理 | neo4-082 マウンテンクラッシュ・はかいのほのお | v0.133 3.1・3.2 節（2026-11-01） | 炎を基本エネルギーカードで数えること（`IA-DESTRUCTIVE-FIRE-COUNT-BASIC-FIRE-CARDS`）・ESP のやり直しの細部はエンジンの解釈 |

データの訂正 PR1-069 の名前（ミュウ）は、利用者が同定して示した訂正（2026-10-19。`scripts/extract_kyuura_cards.py` の `ENGINE_USER_CORRECTIONS`）で、承認ありの記録ですが、
規約の承認ではなくカードデータの層の訂正です（`IA-DATA-PR1-069-NAME`。基礎集合での扱いは DEC-CARD-DATA-CORRECTIONS）。

### 5.2 承認の記録がない既存の簡略化・仮定

| 項目 | 対象（写しで確認） | 出典と採用の時点 | 承認 |
|---|---|---|---|
| `IA-ENGINE-SIMPLIFIED-PMCG6-074-ATTACK`・`-POWER` | **イマクニ？のドードー PMCG6-074**（ハモる・［にげまくり］） | docs/final-pmcg-cards-v0.68.md 4 章（v0.68。エンジンの簡略化した仕様） | なし（v0.68 の依頼は通常のカード登録） |
| `IA-PHOENIX-KO-PROCESS-ORDER` | **R団のファイヤー PMCG5-020**（ふしちょう） | docs/post-knockout-powers-v0.12.md 3 章（v0.12。P27・P28・P30） | なし |
| `IA-ENERGY-DRAIN-AUTOMATIC` | **キョウのベトベトン PMCG6-023**（だつりょくえき。英名 Energy Drain） | v0.17c で UNRESOLVED（DR1・DR12）→ docs/final-pmcg-cards-v0.68.md 3 章で採用（v0.68）。根拠は 2002-05-24 の Q&A・『トレーナーズ』Vol.13（後年の資料） | なし。CLAUDE.md の「後年の裁定で補わない」との関係は未判断 |
| `IA-ENERGY-DRAIN-TIMING` | 同上 | v0.17c で UNRESOLVED（DR6）→ v0.68 で採用（p.89 のこうらがえしの解説からの類推） | なし |
| `IA-DATA-CATALOG-SCOPE-EXCLUSIONS` | PR1-038・PRN-048・PR1-079（目録の分類で通常対戦の対象外） | docs/catalog-scope-migration-v0.128.md（v0.128） | **承認済みに数えない**: 文書は「利用者の指定（kyuura 側の記録は 2026-10-31）」と書くが、指定の文の引用がなく、kyuura の記録も確かめていない |

過去の文書の誤り（転記していない）: `pre-freeze-gap-inventory.md` 74 行は、ドードーの簡略化 2 対象を「キョウのベトベトンのエンジン簡略化」と書いています（`DISC-ENGINE-SIMPLIFIED-PMCG6-074-ATTACK`。
今回は直していない）。stop-policy-decisions.md の同じ取り違えは、設計の作業で訂正が追記済みです。

## 6. 採否の判断が要る項目・研究で確認すべき項目

### 6.1 追加の採否判断が要る（`needs_decision`）

<!-- generated:items-decision begin（scripts/check_implementation_assumptions.py --write が台帳から書く。手で直さない） -->
| ID | 名称 | 分類 | 状態 | 承認 | 対象 | 確認 |
|---|---|---|---|---|---|---|
| `IA-ATTACH-TO-TRANSPARENT-BENCH-TRASH` | つける控えが「とうめい」で受けないときカードを持ち主のトラッシュに置く | 2 | adopted_current | なし | v0.84 のつける効果・v0.72 の DamageThenMoveOneEnergyToBench | doc・code・tests_read・reach_unconfirmed |
| `IA-ATTACK-FAILURE-COIN-GOVERNS-ALL` | 「このワザは失敗する」のコインは残りの要素すべてを決める | 2 | adopted_current | なし | ダブルラリアット・とげでつつく・… | doc・code・tests_read・reach_unconfirmed |
| `IA-ATTACK-ONLY-PROHIBITION` | もうとっしん・ネギでつくの禁止はこのワザだけ | 2 | adopted_current | なし | もうとっしん・ネギでつく（カモネギ neo3-046） | doc・code・tests_read・reach_unconfirmed |
| `IA-BASE-DAMAGE-COUNT-ADDITIONS` | 目安への追加・数の計算は 1 段階の基本となるダメージ | 2 | adopted_current | なし | いかりのとっしん・ローリングニードル・… | doc・code・tests_read・reach_unconfirmed |
| `IA-BERRY-MANDATORY` | きのみ類は条件を満たせば必ず処理する（使うかを選ばない） | 2 | adopted_current | なし | きのみ・おうごんのみ・… | doc・code・tests_read・reach_unconfirmed |
| `IA-BUBBLE-JUMP-EFFECT-MEANS-NONDAMAGE` | バブルジャンプの「このワザの効果はすべてなくなる」はダメージ以外の効果 | 2 | adopted_current | なし | バブルジャンプ | doc・code・tests_read・reach_unconfirmed |
| `IA-CLEFAIRY-DOLL-NOT-TRAINER-ON-FIELD` | 場のピッピ人形・うらのカードをトレーナーカードとしてあつかわない | 2 | adopted_current | なし | ピッピ人形・うらのカード（マチスの秘策） | doc・code・tests_read・reach_unconfirmed |
| `IA-COIN-SKIPPED-WITHOUT-TARGET` | 決める要素のどれにも対象がなければコインを投げない | 2 | adopted_current | なし | ふぶき・ふみあらす PMCG6-030・… | doc・code・tests_read・reach_unconfirmed |
| `IA-COIN-WORDING-SINGLE-COIN` | へんずつう・ヘッドプレス・からではさむ・レインボーパウダーのコインの読み方 | 2 | adopted_current | なし | へんずつう（コダック）・ヘッドプレス・… | doc・code・tests_read・reach_unconfirmed |
| `IA-CONDITION-BONUS-READINGS-V0108` | もうどく・たたきおこす・かえんほうしゃの読み方 | 2 | adopted_current | なし | もうどく・たたきおこす・… | doc・code・tests_read・reach_unconfirmed |
| `IA-COUNTER-AMOUNT-ACTUAL-FINAL-DAMAGE` | カウンターの量は同じワザの中で実際に受けた最終ダメージ | 2 | adopted_current | なし | カウンター（ソーナンス） | doc・code・tests_read・reach_unconfirmed |
| `IA-DECK-EVOLVE-CASE-SPLIT` | 山札からの進化（からやぶりしんか・ひざしをあびる）の場合分けと切る条件 | 2 | adopted_current | なし | からやぶりしんか・ひざしをあびる | doc・code・tests_read・reach_unconfirmed |
| `IA-DEVOLVE-REMOVES-MARKERS-COUNTERS` | 退化でマーカー・カウンターを取りのぞく | 2 | adopted_current | なし | くろこげマーカー・のろいマーカー・… | doc・code・tests_read・reach_unconfirmed |
| `IA-DRAIN-OPTIONAL-ALL-OR-NOTHING` | きゅうけつの「取りのぞいてよい」は与えたぶんを取りのぞくかの選択 | 2 | adopted_current | なし | きゅうけつ（v0.72） | doc・code・tests_read・reach_unconfirmed |
| `IA-ENERGY-DRAIN-TIMING` | だつりょくえきを処理する時点（DR6） | 2 | adopted_current | なし | PMCG6-023 キョウのベトベトン 特殊能力 だつりょくえき | doc・code・tests_read・tests_run・reach_unconfirmed |
| `IA-FLY-BARRIER-ONLY-ON-HEADS` | PR1-018 のそらをとぶの防護は「おもて」のときだけ・全面のバリアー | 2 | adopted_current | なし | そらをとぶ（PR1-018 そらをとぶピカチュウ ほか 3 つ） | doc・code・tests_read・reach_unconfirmed |
| `IA-FROLIC-USER-CHOOSES-BENCH` | はしゃぐで入れ替える控えはワザを使ったプレイヤーが選ぶ | 2 | adopted_current | なし | はしゃぐ（トゲピー） | doc・code・tests_read・reach_unconfirmed |
| `IA-GREEN-SHIELD-NEUTRAL-DAMAGE-SCOPE` | ［グリーンシールド］・［ニュートラルダメージ］の範囲 | 2 | adopted_current | なし | ［グリーンシールド］（トランセル）・［ニュートラルダメージ］（バリヤード） | doc・code・tests_read・reach_unconfirmed |
| `IA-GRUDGE-PRIZES-TAKEN-COUNT` | おんねんの取った数は準備で置く数 − 今のサイドの枚数 | 2 | adopted_current | なし | おんねん | doc・code・tests_read・reach_unconfirmed |
| `IA-HEALING-READINGS-V0104` | v0.104 の回復の読み方（0 個・すべて・コインの順・ねむる・フラワーダンス） | 2 | adopted_current | なし | フシギダネ・あまいみつ・… | doc・code・tests_read・reach_unconfirmed |
| `IA-HEALING-WIND-TARGETS-AT-APPLICATION` | ［いやしのかぜ］・ほのおのまもりは効果を与えたときの自分の場のポケモン全員 | 2 | adopted_current | なし | ［いやしのかぜ］・ほのおのまもり | doc・code・tests_read・reach_unconfirmed |
| `IA-HELP-ZERO-HAND-HD2` | ［HELP］の手札 0 枚は使える（切って 0 枚引き、回数を使う） | 2 | adopted_current | なし | ［HELP］（アンノーンH） | doc・code・tests_read・reach_unconfirmed |
| `IA-HP-ZERO-SOURCE-STAYS-UNTIL-KO-PROCESSING` | HP 以上になった発生源もきぜつの処理の前は場にいて力がはたらく | 2 | adopted_current | なし | ［KEEP］（アンノーンK）・［グリーンシールド］・［ニュートラルダメージ］ | doc・code・tests_read・reach_unconfirmed |
| `IA-IGNORE-EFFECTS-SCOPE-RECIPIENT-OWN` | 効果を除くダメージは受けるポケモン自身の効果だけを除く（反応は残る） | 2 | adopted_current | なし | スピードスター・だましうち・… | doc・code・tests_read・reach_unconfirmed |
| `IA-KEEP-SCOPE-READINGS` | ［KEEP］の範囲（相手の＝実際の使い手、トラッシュ部分だけ無効、2 匹でも 1 回） | 2 | adopted_current | なし | ［KEEP］（アンノーンK） | doc・code・tests_read・reach_unconfirmed |
| `IA-KO-SURVIVAL-SPEED-STAR` | スピードスターのダメージでもこらえる・こうてつかで生き残る | 2 | adopted_current | なし | こらえる・こうてつか・… | doc・code・tests_read・reach_unconfirmed |
| `IA-LARVITAR-SOURCE-EVOLUTION-NOT-END` | ヨーギラスの効果は発生源の進化で消えない | 2 | adopted_current | なし | ヨーギラスのワザ（v0.92） | doc・code・tests_read・reach_unconfirmed |
| `IA-LASTING-EFFECT-PERSISTS-AFTER-SOURCE-LEAVES` | 発生源が場をはなれても効果は消えない（書かれていない） | 2 | adopted_current | なし | やみのはどう・マイナスイオン・… | doc・code・tests_read・reach_unconfirmed |
| `IA-LEAVE-CONDITION-WORDING-AS-GENERAL-RULE` | 「相手がバトル場をはなれたとき」を一般規定と同じ内容と読む | 2 | adopted_current | なし | こおりつかせる（v0.93）・クモのす（v0.92） | doc・code・tests_read・reach_unconfirmed |
| `IA-METAL-ENERGY-PER-CARD-REDUCTION` | 鋼エネルギー（NIP1X-010）は悪エネルギーのカードごとのダメージを -10 | 2 | adopted_current | なし | 鋼エネルギー NIP1X-010・悪エネルギー neo1-094・PRN-002 | doc・code・tests_read・reach_unconfirmed |
| `IA-MEW-NEUTRAL-SHIELD-SCOPE` | ミュウの守る範囲（持つ個体・判定時の状態・実際の使い手・今の姿） | 2 | adopted_current | なし | ミュウ（v0.103） | doc・code・tests_read・reach_unconfirmed |
| `IA-MINUS-ION-SWEET-TALK-ALL-RECIPIENTS` | マイナスイオン・あまえるの減算は受けるのがだれでも当てはめる | 2 | adopted_current | なし | マイナスイオン・あまえる | doc・code・tests_read・reach_unconfirmed |
| `IA-MULTI-COLOR-DISCARD-ALL-OR-NOTHING` | 色ごとのトラッシュが足りなければ 1 枚もトラッシュせず、続く要素も処理しない | 2 | adopted_current | なし | エレメンタルブラスト・しゃくねつのほのお・… | doc・code・tests_read・reach_unconfirmed |
| `IA-MURKROW-FEINT-SCOPE-RECIPIENT-ONLY` | ヤミカラスのだましうちは受けるポケモン自身の効果だけを除く | 2 | adopted_current | なし | だましうち（ヤミカラス） | doc・code・tests_read・reach_unconfirmed |
| `IA-NAME-COUNT-EXACT-CURRENT-FORM` | 名前で数える効果は今の姿の名前の完全一致 | 2 | adopted_current | なし | みんなでスパーク・なかまのちから・… | doc・code・tests_read・reach_unconfirmed |
| `IA-NO-SHUFFLE-WHEN-NOTHING-SEARCHED` | 選ばない・コインで何もしない場合は山札を切らない／ぎゃくりゅうは 0 枚でも切る | 2 | adopted_current | なし | エネルギーアーク・エネルギーチャージ・… | doc・code・tests_read・reach_unconfirmed |
| `IA-PAINT-MARKER-PRECEDES-FORM-TYPE` | 色マーカーの色を今の姿のカードのタイプより先に読む | 2 | adopted_current | なし | ペイント（色マーカー）・ばける・… | doc・code・tests_read・reach_unconfirmed |
| `IA-PERFORM-FINSLAP-HISTORY-READINGS` | ［PERFORM］・ひれがえしの受けたダメージの記録の読み方 | 2 | adopted_current | なし | ［PERFORM］（アンノーンP）・ひれがえし（タッツー） | doc・code・tests_read・reach_unconfirmed |
| `IA-PRIVATE-LOOK-MISC-READINGS-V095` | v0.95 の閲覧・山札移動のその他の読み方 | 2 | adopted_current | なし | ［みやぶる］・［わるぢえ］・… | doc・code・tests_read・reach_unconfirmed |
| `IA-PURIN-HEAL-OPTIONAL-ALL-OR-NOTHING` | プリンの「取り除くことができる」は取り除くかの選択（1 個か 0 個） | 2 | adopted_current | なし | かいふく（プリン） | doc・code・reach_unconfirmed |
| `IA-QUIZ-HEIGHT-HINT-PRINTED-CARD-NAME` | カツラのクイズ その1 で伝える名前はカードの名前のまま | 2 | adopted_current | なし |  | doc・code・tests_read・reach_unconfirmed |
| `IA-READINGS-ARCANINE-RAGING-FLAME` | v0.123 のいかりのほのおの読み方 | 2 | documented_impl_unverified | なし | いかりのほのお（PR1-016 ほか） | doc・reach_unconfirmed |
| `IA-READINGS-DAMAGE-REACTIONS-POISON-SLEEP` | v0.119 の受けるダメージの選択・どく・ねむり・場の効果の読み方 | 2 | documented_impl_unverified | なし | ［シェルアーマー］・［かたいから］・… | doc・reach_unconfirmed |
| `IA-READINGS-FOSSIL-VIRTUAL-ATTACKS` | v0.120 の許可で使うワザ・化石の復活の読み方 | 2 | documented_impl_unverified | なし | ［げんしのきおく］・［にんぎょうつかい］・… | doc・reach_unconfirmed |
| `IA-READINGS-HAND-BENCH-ATTACK-CONDITIONS` | v0.121 の手札からの登場とワザの使用条件の読み方 | 2 | documented_impl_unverified | なし | でんじほう・ぶきみなとおぼえ・… | doc・reach_unconfirmed |
| `IA-READINGS-UNBOUNDED-COINS-HEAL-ALLOCATION` | v0.118 の上限なしコイン・ESP・回復の配分の読み方 | 2 | documented_impl_unverified | なし | アンノーンX［XXXXX］・ふしぎなかおり・… | doc・reach_unconfirmed |
| `IA-READINGS-UNOWN-FOSSIL-RETREAT` | v0.122 のアンノーンの併用・化石の進化履歴・退却時の反応の読み方 | 2 | documented_impl_unverified | なし | ［ANGER］・［XXXXX］・… | doc・reach_unconfirmed |
| `IA-READINGS-WIGGLYTUFF-HELPING-HAND` | v0.125 の［てだすけ］とふくらむの読み方 | 2 | documented_impl_unverified | なし | ［てだすけ］・ふくらむ（v0.125 のプクリン） | doc・reach_unconfirmed |
| `IA-REBEL-COIN-THROWN-UNDER-LEAVE-LOCK` | ［はんこう］はコインがワザの失敗も決めるので投げる | 2 | adopted_current | なし | ［はんこう］ | doc・code・reach_unconfirmed |
| `IA-REBELLION-AS-STEP4-ATTACK-CHECK` | ［はんこう］を p.309 の手順 4 の効果と読む | 2 | adopted_current | なし | PMCG5-035 カスミのギャラドス［はんこう］ | doc・code・tests_read・reach_unconfirmed |
| `IA-RECYCLE-ENERGY-NOT-TOWER` | リサイクルエネルギーの効果はポケモンタワーで消えない | 2 | adopted_current | なし | リサイクルエネルギー neo1-096・ポケモンタワー | doc・code・reach_unconfirmed |
| `IA-REVIVE-OWN-DISCARD-AND-BENCH` | 元気のかけらは自分のトラッシュ・自分のベンチ | 2 | adopted_current | なし | PMCG1-078 元気のかけら | doc・code・tests_read・reach_unconfirmed |
| `IA-SCOOP-UP-DISGUISE-CARD-DISCARDED` | 「ばける」でのせたカードの行き先 | 2 | adopted_current | なし | PMCG1-092 ポケモン回収・PMCG3-048 フジろうじん・… | doc・code・tests_read・reach_unconfirmed |
| `IA-SCREECH-ATTACK-DAMAGE-ANY-TURN` | いやなおとの「ワザによるダメージ」をだれの番かで決めない | 2 | adopted_current | なし | いやなおと（v0.92）・かみくだく（v0.108） | doc・code・reach_unconfirmed |
| `IA-SHUFFLE-WHEN-SEARCHED-DECK-NONEMPTY` | 山札をさがす効果は山札にカードがあれば（選べなくても）切る | 2 | adopted_current | なし | あたためる・からやぶりしんか・… | doc・code・reach_unconfirmed |
| `IA-SKETCH-PERISH-SONG-READINGS` | スケッチ・ほろびのうたの読み方 | 2 | adopted_current | なし | スケッチ（ドーブル）・ほろびのうた（ムウマ） | doc・code・reach_unconfirmed |
| `IA-THREATEN-STEAL-NO-CARD-SHUFFLE` | おどす・とりさるで選べるカードがなくても相手の山札を切る | 2 | adopted_current | なし | おどす・とりさる | doc・code・reach_unconfirmed |
| `IA-TIMED-GUARD-ACTUAL-USER-AND-PSYCHIC-PANIC` | ぬるぬる・かわすの「相手のワザ」は実際の使い手、サイコパニックの 60 は 1 段階 | 2 | adopted_current | なし | ぬるぬる・かわす・… | doc・code・reach_unconfirmed |
| `IA-TIMED-GUARD-COIN-PER-DAMAGE-ELEMENT` | 受けるときのコインはダメージの要素ごと・効果は消えない | 2 | adopted_current | なし | ブリンク・ぬるぬる・… | doc・code・reach_unconfirmed |
| `IA-TOOL-SELF-DISCARD-TIMING` | はんげきのツメ・きあいのハチマキ・学習装置のトラッシュの時点 | 2 | adopted_current | なし | はんげきのツメ・きあいのハチマキ・… | doc・code・reach_unconfirmed |
| `IA-UNOWN-BYVG-READINGS` | アンノーンB・Y・V・G の読み方 | 2 | adopted_current | なし | ［BEAR］・［YIELD］・… | doc・code・reach_unconfirmed |
| `IA-V080-TRAINER-READINGS` | v0.80 の neo トレーナーの読み方（てよい・最大・にせオーキドの発明） | 2 | adopted_current | なし | にせオーキドの発明・v0.80 の選ぶトレーナー | doc・code・reach_unconfirmed |
| `IA-V083-MISC-READINGS` | v0.83 の読み方（きんいろのうろこ・サンダースコール・借りたワザ） | 2 | adopted_current | なし | きんいろのうろこ・サンダースコール・… | doc・code・reach_unconfirmed |
| `IA-V085-MISC-READINGS` | v0.85 の読み方（［ファイヤーレイズ］・あまいかおり） | 2 | adopted_current | なし | ［ファイヤーレイズ］（リザードン PF2-009）・あまいかおり（ベイリーフ neo1-009） | doc・code・reach_unconfirmed |
| `IA-WARP-POINT-SG1-ONLY-WITHOUT-BENCH` | ワープポイントの SG1 は使ったプレイヤーに控えがいないときだけ | 2 | adopted_current | なし | PMCG6-080 ワープポイント | doc・code・tests_read・reach_unconfirmed |
| `IA-WILL-O-WISP-DAMAGE-TO-CURRENT-ACTIVE` | きつねびで入れ替わらなければダメージはそのままのバトル場のポケモンへ | 2 | adopted_current | なし | きつねび | doc・code・reach_unconfirmed |
| `IA-WONDER-WALL-NONATTACK-DAMAGE` | なぞのかべをワザでない特殊能力のダメージにも当てる | 2 | adopted_current | なし | PMCG2-027 バリヤード［なぞのかべ］ | doc・code・reach_unconfirmed |
| `IA-ALL-CLEAR-OTHER-EFFECTS-SCOPE` | オールクリアの「その他の効果」の範囲（番で消える効果は残す） | 3 | adopted_current | なし | オールクリア（ポリゴン PRN-023） | doc・code・tests_read・reach_unconfirmed |
| `IA-BENCH-GUARD-NO-REAPPLY-ON-ABSORBED` | ［ベンチガード］でかわりに受けた 10 に、もう一度［ベンチガード］・受けたときの効果を当てない | 3 | adopted_current | なし | PMCG5-055 タケシのサイドン［ベンチガード］・kernel.deal_damage | code・reach_unconfirmed |
| `IA-DAMAGE-MODIFIER-ORDER-CHOICE-WHEN-DIFFERENT` | 同じ段階のダメージを変える効果の順番は、結果が変わるときだけ選ばせる | 3 | adopted_current | なし | p.321 のダメージ計算・PMCG5-085 カスミ 2 枚（6 段階の加算 2 つ） | doc・code |
| `IA-DAMAGE-SWAP-ONE-COUNTER-PER-USE` | ダメージスワップは 1 回の使用で 1 個を移す | 3 | adopted_current | なし | PMCG1-049 フーディン［ダメージスワップ］・MoveDamageCounter・… | doc・code |
| `IA-ENERGY-CHARGE-NO-TARGET-UNUSABLE` | エナジーチャージは 0 枚・選べるカードがないとき使えない | 3 | adopted_current | なし | PMCG5-040 マチスのレアコイル［エナジーチャージ］ | doc・code・tests_read・reach_unconfirmed |
| `IA-ENERGY-TRANSFER-ONE-CARD-PER-USE` | エナジートランスは 1 回の使用で 1 枚をつけかえる | 3 | adopted_current | なし | PMCG1-011 フシギバナ［エナジートランス］・EnergyTransfer・… | doc・code |
| `IA-IMMUNITY-SKIPS-STATUS-QUESTIONS` | めんえきで防がれる特殊状態について未解決の問いを聞かない | 3 | adopted_current | なし | PMCG2-047 カビゴン［めんえき］ | doc・code・tests_read・reach_unconfirmed |
| `IA-KO-PROCESS-AFTER-ALL-ATTACK-ELEMENTS` | ワザのきぜつの処理をワザの要素のあとにまとめる時点 | 3 | adopted_current | なし | でんげき（PMCG1-035）・ふきとばし（PMCG2-007）・… | doc・code・tests_read・reach_unconfirmed |
| `IA-KO-SURVIVAL-FURTHER-DAMAGE-NOT-STOPPED` | HP 以上にした効果の範囲のダメージをさらに受けても KS1 で止めない | 3 | adopted_current | なし | こらえる・こうてつか | doc・code・tests_read・reach_unconfirmed |
| `IA-LEAVE-LOCKED-OPTIONAL-SELF-SWITCH-NOT-ASKED` | はなれられないポケモンには任意の入れ替え（変わり身の術・［にげこむ］）を聞かない | 3 | adopted_current | なし | 変わり身の術・［にげこむ］ | doc・code・reach_unconfirmed |
| `IA-MULLIGAN-COMP-PER-MULLIGAN` | 切り直しの補償を 1 回ごとに 0〜2 枚選ぶ | 3 | adopted_current | なし | 準備の切り直し | doc・code・tests_read・reach_unconfirmed |
| `IA-PHOENIX-KO-PROCESS-ORDER` | ふしちょうとサイド・勝ち負け・バトル場に出すの順番の正規化 | 3 | adopted_current | なし | PMCG5-020 R団のファイヤー 特殊能力 ふしちょう | doc・code・tests_read・tests_run・reach_unconfirmed |
| `IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO` | 同時のきぜつで両方がサイドを取る順番 | 3 | adopted_current | なし | 同時のきぜつのサイド・PMCG1-035 でんげき（v0.2f で実際に起こる）・… | doc・code・tests_read |
| `IA-RAIN-DANCE-ONE-CARD-PER-USE` | あまごいは 1 回の使用で 1 枚をつける | 3 | adopted_current | なし | PMCG1-032 カメックス［あまごい］・AttachEnergyFromHand・… | doc・code・reach_unconfirmed |
| `IA-RETREAT-REPLACEMENT-CHOSEN-BEFORE-COIN` | にげるの入れ替え先をこんらんのコインの前に指定 | 3 | adopted_current | なし | にげる（こんらん） | doc・code |
| `IA-RUN-AWAY-FIXED-TIMING` | ［ずらかる］の決まった時点 | 3 | adopted_current | なし | PMCG5-051 タケシのオコリザル［ずらかる］ | doc・code・tests_read・reach_unconfirmed |
| `IA-SELF-THEN-OPPONENT-ORDER` | 「自分と相手」の効果は自分 → 相手の順 | 3 | adopted_current | なし | ゆめみのまい・くさいにおい（エリカのクサイハナ GD4-003。v0.72）・やさしいうた（v0.104） | doc・code・tests_read・reach_unconfirmed |
| `IA-SINKHOLE-TIMING-AFTER-SWITCH` | ［おとしあな］は SH1 に当たらなければ入れ替えのあとに処理 | 3 | adopted_current | なし | PMCG4-043 わるいダグトリオ［おとしあな］ | doc・code・tests_read・reach_unconfirmed |
| `IA-TOWER-PHOENIX-OPPORTUNITY-NOT-OFFERED` | ポケモンタワーの下ではふしちょう・［つりあげる］の機会を出さない | 3 | adopted_current | なし | ふしちょう（ファイヤー）・［つりあげる］・… | doc・code・reach_unconfirmed |
| `IA-TRAINER-DISCARD-AFTER-RESOLUTION` | 使用中のトレーナーを説明が終わってからトラッシュする時点 | 3 | adopted_current | なし | トレーナー全般（v0.2b のきずぐすり・ポケモンいれかえ・マサキ）・PMCG1-077 オーキドはかせ・… | doc・code・reach_unconfirmed |
| `IA-BENCH-FROM-DISCARD-FULL-BENCH-EXCLUDED` | 持ち主のベンチに空きのないカードは選べるものに入れない | 4 | adopted_current | なし | PMCG1-078 元気のかけら・PMCG1-084 ポケモンの笛・… | doc・code・reach_unconfirmed |
| `IA-BILINGUAL-NAME-JUDGED-NAME-ALL-PATHS` | 判定用の名前「ナッシー」「ふみつけ」をすべての名前の比べに使う | 4 | adopted_current | なし | PR1-075・PR1-077・… | doc・code・reach_unconfirmed |
| `IA-BLAINE-SECOND-COPY-NO-STACK` | 2 枚目のカツラは効果を重ねずに使える | 4 | adopted_current | なし | PMCG6-093 カツラ | doc・code・reach_unconfirmed |
| `IA-BLANK-OWNER-NAME-PIKACHU-LITERAL` | _のピカチュウの名前をそのまま 1 つの名前として扱う | 4 | adopted_current | なし | PR1-044・PR1-090・… | doc・code・reach_unconfirmed |
| `IA-CHAOS-GYM-COINS-OUTER-INNER-SEPARATE` | サイキックコントロールの外側・内側の錯乱ジムのコインは別々 | 4 | adopted_current | なし | PMCG6-088 ナツメのサイキックコントロール・PMCG5-087 錯乱ジム | doc・code・reach_unconfirmed |
| `IA-CONVERSION-COLORS-EIGHT` | テクスチャーで選べる色は無色以外の 8 つ | 4 | adopted_current | なし | PMCG1-064 ポリゴン テクスチャー1・テクスチャー2 | doc・code・reach_unconfirmed |
| `IA-CONVERSION1-REAPPLY-REPLACES` | テクスチャー1の重ねがけは置きかえる | 4 | adopted_current | なし | PMCG1-064 ポリゴン テクスチャー1 | doc・code・reach_unconfirmed |
| `IA-DEEP-SEARCH-REQUIRED-COUNT-FIXED` | 必須の山札の検索は 1 枚、エネルギーアークはコインの前に 2 枚を確かめる | 4 | adopted_current | なし |  | doc・code・tests_read・reach_unconfirmed |
| `IA-DEFERRED-SHORTAGE-INTERRUPTION` | 枚数不足の途中停止で、そこまでの処理を残して終端にする | 4 | adopted_current | なし | ES2-005・QSG-055・… | doc・code・tests_read・reach_unconfirmed |
| `IA-DEVOLUTION-ONCE-ATTACK-RECORD-KEPT` | 退化で残ったカードの 1 度だけ使えるワザの記録を残す | 4 | adopted_current | なし | PMCG1-086 退化スプレー・PMCG3-033 ミュウ たいかビーム | doc・code・tests_read・reach_unconfirmed |
| `IA-DEVOLUTION-SPRAY-ZERO-AND-ORDER` | 退化スプレーの決定の順番と 0 枚 | 4 | adopted_current | なし | PMCG1-086 退化スプレー・PMCG3-033 ミュウ たいかビーム | doc・code・tests_read・reach_unconfirmed |
| `IA-DISGUISE-KEEPS-TOP-POWER` | 「ばける」でのせたあともいちばん上のカードの「ばける」を持つ | 4 | adopted_current | なし | PMCG5-019 タケシのキュウコン「ばける」 | doc・code・tests_read・reach_unconfirmed |
| `IA-DISGUISE-PERSISTS-ON-BENCH` | 「ばける」でのせたカードはベンチでものせたまま | 4 | adopted_current | なし | PMCG5-019 タケシのキュウコン「ばける」 | doc・code・tests_read・reach_unconfirmed |
| `IA-DOWSING-DISCARD-AS-PLAY-CONDITION` | ダウジングマシーンの 2 枚すてるを使うための条件と読む | 4 | adopted_current | なし | PMCG1-087 ダウジングマシーン | doc・code・tests_read・reach_unconfirmed |
| `IA-DOWSING-DISCARDED-TRAINER-SELECTABLE` | ダウジングマシーンですてたトレーナーを選べる | 4 | adopted_current | なし | PMCG1-087 ダウジングマシーン | doc・code・tests_read・reach_unconfirmed |
| `IA-DOWSING-OWN-DISCARD` | ダウジングマシーンのトラッシュは自分のトラッシュ | 4 | adopted_current | なし | PMCG1-087 ダウジングマシーン | doc・code・tests_read・reach_unconfirmed |
| `IA-DURING-ATTACK-POWER-SUPPRESSION-PERIOD` | 「このワザを使っているあいだ」の特殊能力の抑止の期間（オールクリア） | 4 | adopted_current | なし | オールクリア（ポリゴン PRN-023） | doc・code・tests_read・reach_unconfirmed |
| `IA-ENERGY-BURN-UNIT-COUNT` | エナジーバーンで無色2個エネルギーは「炎」2 個 | 4 | adopted_current | なし | PMCG1-021 リザードン［エナジーバーン］・無色2個エネルギー | doc・code・reach_unconfirmed |
| `IA-ENERGY-DRAIN-RECEIPT-CONDITIONS` | だつりょくえきの候補になる条件と状態の評価時点 | 4 | adopted_current | なし | PMCG6-023 キョウのベトベトン［だつりょくえき］ | doc・code・tests_read・reach_unconfirmed |
| `IA-ENGINE-SIMPLIFIED-PMCG6-074-ATTACK` | イマクニ？のドードーのハモるの簡略化 | 4 | adopted_current | なし | PMCG6-074 イマクニ？のドードー ワザ 0 ハモる | doc・code・tests_read・tests_run・reach_unconfirmed |
| `IA-ENGINE-SIMPLIFIED-PMCG6-074-POWER` | イマクニ？のドードーの［にげまくり］の簡略化 | 4 | adopted_current | なし | PMCG6-074 イマクニ？のドードー 特殊能力 にげまくり | doc・code・tests_read・tests_run・reach_unconfirmed |
| `IA-ERIKA-OPPONENT-COUNT-BY-OPPONENT` | エリカの相手の枚数は相手自身が決める | 4 | adopted_current | なし | PMCG5-083 エリカ | doc・code・tests_read・reach_unconfirmed |
| `IA-FLING-RETURN-ORDER-AND-UNAFFECTED-DECK` | つれさるの処理の順番と、受けなかった側の山札を切らない | 4 | adopted_current | なし | PMCG5-066 エリカのハクリュー つれさる | doc・code・tests_read・reach_unconfirmed |
| `IA-FOSSIL-ROLE-COLORLESS-NONE` | 場での役割のポケモンのタイプは「なし」 | 4 | adopted_current | なし | なにかの化石・ピッピ人形 | doc・code・reach_unconfirmed |
| `IA-GAS-BODY-COUNTS-BASIC-ENERGY-CARDS` | ガスのからだは基本エネルギーカードの枚数で数える | 4 | adopted_current | なし | PMCG6-049 ナツメのゴース［ガスのからだ］ | doc・code・tests_read・reach_unconfirmed |
| `IA-GENTLE-CONDITION-AT-DAMAGE-TIME` | やさしいほのお等の条件はダメージを計算する時点の相手の今の姿で決める | 4 | adopted_current | なし | やさしいほのお・やさしいキック・… | doc・code・tests_read・reach_unconfirmed |
| `IA-HAND-PICK-BY-POSITION-NOT-RANDOM` | 相手の手札を位置で選ぶ（無作為にしない） | 4 | adopted_current | なし | PMCG2-028 マンキー［スパイ］・PMCG5-062 マチスのイーブイ おどろかす | doc・code・tests_read・reach_unconfirmed |
| `IA-HAND-RETURN-SHUFFLE-EVEN-ZERO` | もどすカードが 0 枚でも山札を切る | 4 | adopted_current | なし | v0.54 の手札を山札にもどすトレーナー | doc・code・tests_read・reach_unconfirmed |
| `IA-HEAL-ALL-NO-TARGET-RESOLVES` | 全員から取る回復はダメージカウンターがなければ何も起こらずに使い終わる | 4 | adopted_current | なし | PMCG5-084 エリカの親切・PMCG5-089 タケシ・… | doc・code・tests_read・reach_unconfirmed |
| `IA-INCREASE-BENCH-SPACE-AFTER-ENTRY` | ［INCREASE］のベンチの空きは場に出したあとのベンチで決める | 4 | adopted_current | なし | ［INCREASE］ | doc・code・tests_read・reach_unconfirmed |
| `IA-KO-SEQUENCE-PRIZE-JUDGE-PROMOTE` | きぜつのあとの順番（サイド → 勝ち負け → バトル場に出す） | 4 | adopted_current | なし | きぜつのあとの手順 | doc・code・reach_unconfirmed |
| `IA-KO-SURVIVAL-PERIOD-AND-TIMING` | こらえる・こうてつかの期間・残りHP 10 の処理時点 | 4 | adopted_current | なし | こらえる・こうてつか | doc・code・tests_read・reach_unconfirmed |
| `IA-MIND-GAMES-DECLINE-BRANCH-PREFLIGHT` | ［ちえくらべ］の機会を出す前に、使わない枝を最後まで確かめる | 4 | adopted_current | なし | neo1-049/power/0 | doc・code・tests_read・reach_unconfirmed |
| `IA-MIRROR-MOVE-COPIED-MIRROR-MOVE-RECORD` | ピジョンがオニスズメのオウムがえしを出すと、ピジョンの受けた記録を与える | 4 | adopted_current | なし | PMCG1-066 ピジョン オウムがえし・PMCG2-034 オニスズメ オウムがえし | doc・code・reach_unconfirmed |
| `IA-MISS-TRAINER-CLASS-IN-HAND` | ミニスカートのトレーナーカードは手札にある間の印刷の分類 | 4 | adopted_current | なし | PMCG1-095 ミニスカート | doc・code・tests_read・reach_unconfirmed |
| `IA-MULLIGAN-COMP-TIMING-AFTER-PRIZES` | 切り直しの補償はサイドのあと・ジャンケンの前 | 4 | adopted_current | なし | 準備の切り直し | doc・code・tests_read・reach_unconfirmed |
| `IA-POKE-BALL-TAILS-NO-SHUFFLE` | モンスターボールの「うら」では山札を切らない | 4 | adopted_current | なし | PMCG2-048 モンスターボール | doc・code・tests_read・reach_unconfirmed |
| `IA-POKEDEX-ZERO-IS-NOT-LOOKING` | ポケモン図鑑の 0 枚は見ないこと | 4 | adopted_current | なし | ポケモン図鑑 | doc・code・tests_read・reach_unconfirmed |
| `IA-PSYCHIC-CONTROL-CARD-TO-IN-USE` | ナツメのサイキックコントロールのカードは使用中の場所に移る | 4 | adopted_current | なし | PMCG6-088 ナツメのサイキックコントロール | doc・code・tests_read・reach_unconfirmed |
| `IA-PSYCHIC-LINK-PER-SOURCE` | サイコリンクで同じワザを 2 匹が供給するときは出どころごとに選べる | 4 | adopted_current | なし | PMCG6-053 ナツメのフーディン［サイコリンク］ | doc・code・tests_read・reach_unconfirmed |
| `IA-QUIZ-HEIGHT-DEX-ONLY-LOOKUP` | 身長の参照値は図鑑番号だけで引き、なければ選ぶと止める | 4 | adopted_current | なし | GD5-016/trainer | doc・code・tests_read・reach_unconfirmed |
| `IA-QUIZ-HEIGHT-EXACT-INTEGER-CM` | 身長の答えは整数 cm の完全一致 | 4 | adopted_current | なし | GD5-016/trainer | doc・code・tests_read・reach_unconfirmed |
| `IA-RAID-PRIZES-REVEAL-SCOPE` | ロケット団参上!でおもてにするのは使ったときのサイドだけ | 4 | adopted_current | なし | PMCG4-062 ロケット団参上! | doc・code・tests_read・reach_unconfirmed |
| `IA-REACTION-EVOLUTION-AFTER-PENDING` | 反応で起こった進化への反応は待っている反応のあとに処理する | 4 | adopted_current | なし | v0.86 の反応の特殊能力 | doc・code・reach_unconfirmed |
| `IA-READINGS-TRANSFORM-DARK-PULSE` | v0.124 の変身の姿の固定の範囲・解除の位置とわるいはどうのコインの位置 | 4 | documented_impl_unverified | なし | ES2-032［すごいへんしん］・PMCG3-042 へんしん・… | doc・reach_unconfirmed |
| `IA-RECALL-SAME-POKEMON-ONLY` | 思い出させるのワザはバトル場のポケモンが記録と同じときだけ選べる | 4 | adopted_current | なし | PMCG5-071 思い出させる | doc・code・tests_read・reach_unconfirmed |
| `IA-REDUCE-DAMAGE-STEP-OF-TEN` | お上品攻撃の減らす量は 10 単位で 0 から 5 段階のダメージまで | 4 | adopted_current | なし | PMCG5-074 お上品攻撃 | doc・code・tests_read・reach_unconfirmed |
| `IA-RETURNED-CARDS-NOT-SHOWN` | ラッキーたまご・てじなで山札にもどしたカードを見せない | 4 | adopted_current | なし | ラッキーたまご・てじな | doc・code・tests_read・reach_unconfirmed |
| `IA-ROCKET-SNEAK-NO-SHUFFLE-WITHOUT-TRAINER` | ロケット団のおねーさんはトレーナーがなければ山札を切らない | 4 | adopted_current | なし | PMCG4-061 ロケット団のおねーさん | doc・code・tests_read・reach_unconfirmed |
| `IA-SABRINA-REATTACH-THEN-EVALUATE` | ナツメは 1 回でつけなおし、そのあとカードごとに特殊能力を評価 | 4 | adopted_current | なし | PMCG6-098 ナツメ | doc・code・tests_read・reach_unconfirmed |
| `IA-SEARCH-SHUFFLE-WITHOUT-CHOICE` | 選ばない・選べないときも山札を切る | 4 | adopted_current | なし | v0.53 の山札をさがすトレーナー 4 枚 | doc・code・tests_read・reach_unconfirmed |
| `IA-SECRET-PLAN-NOT-PLAY-CONDITION` | マチスの秘策は手札・ベンチがなくても使える（何もしない） | 4 | adopted_current | なし | PMCG5-093 マチスの秘策 | doc・code・tests_read・reach_unconfirmed |
| `IA-SECRET-PLAN-REVEAL-OWN-MAIN-ONLY` | マチスの秘策のうらのカードは自分の番の MAIN でだけおもてにできる | 4 | adopted_current | なし | PMCG（マチスの秘策）の RevealFaceDown・engine._reveal_face_down | doc・code・reach_unconfirmed |
| `IA-SHIFT-COLOR-CHOICES-FIELD-COLORS` | へんしょくで選べる色は場にいるポケモンの今有効な色 | 4 | adopted_current | なし | PMCG2-015 モルフォン［へんしょく］ | doc・code・tests_read・reach_unconfirmed |
| `IA-SIMPLIFICATION-COPY-SCOPE` | 利用者の簡略ルールをコピー・ほかのポケモンの使用にも当てはめる | 4 | adopted_current | なし | PR1-044/attack/0・PR1-072/attack/0 | doc・code・tests_read・reach_unconfirmed |
| `IA-SPY-OPERATION-LOOK-EMPTY-HAND` | スパイ作戦は相手の手札が 0 枚でも見る処理をして続ける | 4 | adopted_current | なし | PMCG5-088 スパイ作戦 | doc・code・tests_read・reach_unconfirmed |
| `IA-SPY-OPERATION-SINGLE-OPTIONAL` | スパイ作戦のトラッシュと引くことは 1 つの「のぞむなら」 | 4 | adopted_current | なし | PMCG5-088 スパイ作戦 | doc・code・tests_read・reach_unconfirmed |
| `IA-SUDDEN-DEATH-PRIZES-TAKEN-PER-SEGMENT` | 延長戦の「取ったサイドの数」は今の区間だけで数える | 4 | adopted_current | なし | ES3-023（おんねん） | doc・code・tests_read・reach_unconfirmed |
| `IA-SUDDEN-DEATH-RESTART-READING` | 延長戦はジャンケン・切り直しから全部やり直す | 4 | adopted_current | なし | サドン・デス（p.324） | doc・code・tests_read・reach_unconfirmed |
| `IA-SWAP-OWNERSHIP-SCOPE-EXTENSIONS` | 交換の所有者規則の細部（再交換・つけたカード・デッキの制限） | 4 | adopted_current | なし | PR1-027・PMCG5-087（錯乱ジム）の事例 | doc・code・tests_read・reach_unconfirmed |
| `IA-SWAP-REVEAL-HAND-OPPONENT-ONLY` | 「相手プレイヤーにあなたの手札を見せ」は相手だけが見る | 4 | adopted_current | なし | PR1-027/trainer | doc・code・tests_read・reach_unconfirmed |
| `IA-SWIFT-EFFECTS-BY-HOLDER` | スピードスターの除く効果は持っているのがだれかで分ける | 4 | adopted_current | なし | PMCG5-050 タケシのサンドパン スピードスター | doc・code・tests_read・reach_unconfirmed |
| `IA-SWIFT-POST-DAMAGE-REACTIONS-APPLY` | スピードスターでもダメージを受けたあとの反応ははたらく | 4 | adopted_current | なし | PMCG5-050 タケシのサンドパン スピードスター | doc・code・tests_read・reach_unconfirmed |
| `IA-THUNDERSTORM-COINS-BEFORE-DAMAGE` | サンダーストームはすべてのコインを投げてからダメージ | 4 | adopted_current | なし | PMCG3-026 サンダー サンダーストーム | doc・code・tests_read・reach_unconfirmed |
| `IA-TICKLE-MACHINE-RETURN-ORDER` | くすぐりマシーンは置いた順にもどす・挑戦状で表にする順 | 4 | adopted_current | なし | PMCG6-084 くすぐりマシーン・挑戦状・… | doc・code・tests_read・reach_unconfirmed |
| `IA-TRANSPARENCY-EVALUATED-ON-OWN-POKEMON` | 自分のポケモンにも「とうめい」を評価する | 4 | adopted_current | なし | PMCG3-033 ミュウ たいかビーム・PMCG6-051 ナツメのスリーパー よみがえらせる | doc・code・tests_read・reach_unconfirmed |
| `IA-XXXXX-CONCURRENT-DECLARATION-REJECTED` | 同じ宣言で 2 匹の同じグループの力を指すと、あとの力を拒否する | 4 | adopted_current | なし | アンノーンX［XXXXX］（v0.122）・［ANGER］ | code・reach_unconfirmed |
| `IA-ZOOM-COST-AT-RETREAT-DECLARATION` | ［ZOOM］の払う数は「にげる」の宣言のときの場で決める | 4 | adopted_current | なし | ［ZOOM］ | doc・code・reach_unconfirmed |
| `IA-ENERGY-DRAIN-AUTOMATIC` | だつりょくえきは自動的にはたらく（DR1・DR12） | 5 | adopted_current | なし | PMCG6-023 キョウのベトベトン 特殊能力 だつりょくえき | doc・code・tests_read・tests_run・reach_unconfirmed |
| `IA-DATA-CATALOG-SCOPE-EXCLUSIONS` | PR1-038・PRN-048・PR1-079 を通常対戦の対象から外す（目録の分類） | 7 | adopted_current | なし | PR1-038 タッチ交代！・PRN-048 タッチ世代交代！・… | doc・code・tests_run・reach_unconfirmed |
| `IA-DATA-KYUURA-CORRECTIONS` | kyuura のデータに入った訂正（KYUURA_CORRECTIONS） | 7 | adopted_current | なし | scripts/extract_kyuura_cards.py KYUURA_CORRECTIONS の各訂正 | doc・code・tests_run・reach_unconfirmed |
| `IA-DATA-PR1-069-NAME` | PR1-069 の名前をミュウにする（データの訂正） | 7 | adopted_current | あり | PR1-069 の name.ja | doc・code・tests_read・tests_run・reach_unconfirmed |
<!-- generated:items-decision end -->

### 6.2 研究で確認すべき（`needs_research`）

<!-- generated:items-research begin（scripts/check_implementation_assumptions.py --write が台帳から書く。手で直さない） -->
| ID | 名称 | 分類 | 状態 | 承認 | 対象 | 確認 |
|---|---|---|---|---|---|---|
| `IA-COUNTERATTACK-DEAL-AFTER-DAMAGE-ELEMENTS` | 「はんげき」はそのワザのダメージの要素のあと、ダメージ以外の効果の前に与える | 2 | adopted_current | なし | PMCG1-008 カイリキー［はんげき］・R団のカビゴン［わるいねぞう］・… | doc・code・tests_read・reach_unconfirmed |
| `IA-DECK-GROUP-LIMIT-ALL-GROUP-CARDS` | 「アンノーン」のデッキ 4 枚の上限をグループのカード全体に当てる | 2 | adopted_current | なし | アンノーン各種（neo2〜neo4） | doc・code・reach_unconfirmed |
| `IA-DECK-SAME-NAME-SPELLING-VARIANT` | 空白だけが違う「ポケモン図鑑 HANDY505」をデッキの同じ名前として数える | 2 | adopted_current | なし | GD1-022・GD5-023・… | doc・code・reach_unconfirmed |
| `IA-DESTRUCTIVE-FIRE-COUNT-BASIC-FIRE-CARDS` | はかいのほのおの炎エネルギーカードは基本エネルギーカードで数える | 2 | adopted_current | なし | neo4-082/attack/1 | doc・code・tests_read・reach_unconfirmed |
| `IA-DRY-UP-ZERO-WATER-TARGET-SELECTABLE` | ドライアップで水 0 枚のポケモンを止めずに選べる | 2 | adopted_current | なし |  | doc・code・tests_read・reach_unconfirmed |
| `IA-FLAME-WALL-EXPIRY-AND-DAMAGE-CLASS-BY-P89` | 「ほのおのかべ」の期限と 10 の分類を p.89 の同じ形のワザから決める | 2 | adopted_current | なし | R団のファイヤー［ほのおのかべ］・ほのおのかべ・こうらがえしのダメージの分類と量 | doc・code・reach_unconfirmed |
| `IA-FORCED-SWITCH-SKIPPED-ON-KO` | ふきとばしの 20 で相手がきぜつしたら入れ替えない | 2 | adopted_current | なし | PMCG2-007 バタフリー ふきとばし | doc・code・tests_read・reach_unconfirmed |
| `IA-GUTS-OFFER-AFTER-ALL-ATTACK-ELEMENTS` | こんじょうはワザの要素をすべて処理したあとのきぜつの判定で聞く | 2 | adopted_current | なし | サカキのカイリキー［こんじょう］・kernel.ko_prevention_offers・… | doc・code・reach_unconfirmed |
| `IA-INF-ATTACHED-TRAINER-PERSISTS-THROUGH-BENCH` | ついているトレーナーはベンチを経ても効果がある | 2 | adopted_current | なし | ついているトレーナーはベンチを経ても効果がある | doc・code・reach_unconfirmed |
| `IA-INF-ATTACK-VALUE-READINGS` | ハイドロポンプ・からてチョップの計算の読み方 | 2 | documented_impl_unverified | なし | ハイドロポンプ・からてチョップの計算の読み方 | doc・code・reach_unconfirmed |
| `IA-INF-CHEMICAL-GAS-SCOPE` | かがくへんかガスのはたらく状態と結果 | 2 | documented_impl_unverified | なし | かがくへんかガスのはたらく状態と結果 | doc・code・reach_unconfirmed |
| `IA-INF-CONFUSED-ZERO-RETREAT-FLIPS` | にげるエネルギー 0 のこんらんのポケモンもコインを投げる | 2 | adopted_current | なし | にげるエネルギー 0 のこんらんのポケモンもコインを投げる | doc・code・reach_unconfirmed |
| `IA-INF-DAMAGE-SWAP-SCOPE` | ダメージスワップの移動元・移動先と使える状態 | 2 | adopted_current | なし | ダメージスワップの移動元・移動先と使える状態 | doc・code・reach_unconfirmed |
| `IA-INF-ENERGY-TRANSFER-SCOPE` | エナジートランスの使える状態と数え方 | 2 | adopted_current | なし | エナジートランスの使える状態と数え方 | doc・code・reach_unconfirmed |
| `IA-INF-EVOLUTION-KEEPS-TRAINER-CLEARS-RETREAT-FAIL` | 進化でついているトレーナーの効果は続き、にげるの失敗の記録は消える | 2 | adopted_current | なし | 進化でついているトレーナーの効果は続き、にげるの失敗の記録は消える | doc・code・reach_unconfirmed |
| `IA-INF-EXCLUSIVE-CONDITION-REPLACE` | ねむり・マヒ・こんらんは後から受けた状態に置きかわる | 2 | documented_impl_unverified | なし | ねむり・マヒ・こんらんは後から受けた状態に置きかわる | doc・code・reach_unconfirmed |
| `IA-INF-MEGA-DRAIN` | メガドレインの回復の条件と時点 | 2 | adopted_current | なし | メガドレインの回復の条件と時点 | doc・code・reach_unconfirmed |
| `IA-INF-NEXT-OPP-TURN-EFFECT-ENDS-AT-ITS-END` | 「次の相手の番」の効果は次の相手の番の終わりに消える | 2 | adopted_current | なし | 「次の相手の番」の効果は次の相手の番の終わりに消える | doc・code・reach_unconfirmed |
| `IA-INF-PHOENIX-OPTIONAL` | ふしちょうは使うかを選べる | 2 | adopted_current | なし | ふしちょうは使うかを選べる | doc・code・reach_unconfirmed |
| `IA-INF-PREVENT-DAMAGE-NULLIFIES-ELEMENT` | 「ダメージを受けない」状態は段階ではなく要素の無効 | 2 | adopted_current | なし | 「ダメージを受けない」状態は段階ではなく要素の無効 | doc・code・reach_unconfirmed |
| `IA-INF-RAIN-DANCE-SCOPE` | あまごいの使える場面とつける先 | 2 | adopted_current | なし | あまごいの使える場面とつける先 | doc・code・reach_unconfirmed |
| `IA-INF-SELF-RECOVER` | じこさいせいの選ぶ人と使える条件 | 2 | documented_impl_unverified | なし | じこさいせいの選ぶ人と使える条件 | doc・code・reach_unconfirmed |
| `IA-INF-SNORE-AUTOMATIC` | わるいねぞうは自動的にはたらく | 2 | adopted_current | なし | わるいねぞうは自動的にはたらく | doc・code・reach_unconfirmed |
| `IA-INF-STICKY-NO-PARALYSIS-ON-KO` | ねばりつくのダメージで相手がきぜつしたらマヒにしない | 2 | adopted_current | なし | ねばりつくのダメージで相手がきぜつしたらマヒにしない | doc・code・reach_unconfirmed |
| `IA-MIND-GAMES-OPPORTUNITY-SCOPE` | ［ちえくらべ］の機会を出す範囲 | 2 | adopted_current | なし | neo1-049/power/0 | doc・code・tests_read・reach_unconfirmed |
| `IA-MOUNTAIN-CRUSH-ESP-REDO-FROM-MILL` | マウンテンクラッシュの ESP のやり直しはダメージをくり返さない | 2 | adopted_current | なし |  | doc・code・tests_read・reach_unconfirmed |
| `IA-POISON-STING-NO-COIN-ON-KO` | どくばりのダメージで相手がきぜつしたらコインを投げない | 2 | adopted_current | なし | PMCG1-004 ビードル どくばり（v0.3a） | doc・code・tests_read |
| `IA-POKEMON-CHECK-KO-BEFORE-SLEEP` | ポケモンチェックのきぜつの処理をどくのあと・ねむりの前に行う | 2 | adopted_current | なし | ポケモンチェック | doc・code・tests_read・reach_unconfirmed |
| `IA-POWER-EFFECT-PERSISTS-AFTER-USER-LEAVES` | 使ったポケモンが場をはなれても特殊能力の効果は続く | 2 | adopted_current | なし | ［QUICKEN］・［げんしのゆめ］ | doc・code・reach_unconfirmed |
| `IA-QUIZ-CHAOS-GYM-BORROWER-IS-YOU` | 錯乱ジムで借りたクイズの「あなた」は借りたプレイヤー | 2 | adopted_current | なし |  | doc・code・tests_read・reach_unconfirmed |
| `IA-READINGS-BABY-RULES-CARDS` | ベイビィの 13 枚の個別の読み方 | 2 | adopted_current | なし | なげキッス・［わんぱくパンチ］・… | doc・reach_unconfirmed |
| `IA-READINGS-ENERGY-MOVEMENT-ATTACH-DEVOLUTION` | 付け替え・ついた時の効果・回収の読み方 | 2 | adopted_current | なし | バトンタッチ・エナジーサイクル・… | doc・reach_unconfirmed |
| `IA-READINGS-FIELD-ENERGY-CARD-ATTACKS` | サイコクラッシュ・シンクロウェーブの数え方と条件の時点（実装上の読み方） | 2 | adopted_current | なし | サイコクラッシュ・シンクロウェーブ | doc・reach_unconfirmed |
| `IA-READINGS-RETREAT-RETURN-POWERS` | ［CHASE］・おいうち・もちさるなどの読み方 | 2 | adopted_current | なし | ［CHASE］・おいうち・… | doc・reach_unconfirmed |
| `IA-READINGS-SPREAD-DAMAGE` | なぎたおすのコインの投げ手・順番と配分の読み方 | 2 | adopted_current | なし | なぎたおす・びっくりサンダー・… | doc・reach_unconfirmed |
| `IA-READINGS-VARIABLE-COINS-SEARCH-ATTACH` | みんなでおどる・ゆうでん・ダークフレイム・ファイヤーラッシュ・くろいキバの読み方 | 2 | adopted_current | なし | みんなでおどる・ゆうでん・… | doc・reach_unconfirmed |
| `IA-READINGS-WATER-ENERGY-COIN-DRAW` | しょくしゅをつかう・ふしょくえき・どくばりの読み方 | 2 | adopted_current | なし | しょくしゅをつかう・ふしょくえき・… | doc・reach_unconfirmed |
| `IA-SELF-ATTACK-DAMAGE-WEAKNESS-RESISTANCE` | ワザの説明による自分へのダメージに弱点・抵抗力を計算する | 2 | adopted_current | なし | PMCG1-035 でんげき・自分へのダメージのワザ全般 | doc・code・tests_read・reach_unconfirmed |
| `IA-STADIUM-SAME-NAME-AND-COUNT-UNRESTRICTED` | スタジアムは 1 番に何枚でも、同じ名前でも出せる | 2 | adopted_current | なし | スタジアムカード全般（v0.57〜）・engine._play_stadium・… | doc・code・reach_unconfirmed |
| `IA-TRANSPARENCY-ONE-FLIP-RESULT-FIXED-FOR-ATTACK` | 「とうめい」は 1 つのワザで 1 匹 1 回だけ投げ、その結果をワザの残りに使う | 2 | adopted_current | なし | 化石の秘密のゴースト・第1弾のゴースト［とうめい］・kernel の FrameState.reception・… | doc・code・reach_unconfirmed |
| `IA-DV1-PROCEED-WHEN-COUNTS-AGREE` | DV1 はどちらの判定でも結果が同じ枚数だけ受け付ける | 3 | adopted_current | なし | PMCG1-086 退化スプレー | doc・code・tests_read・reach_unconfirmed |
| `IA-FLY-BARRIER-SCOPE-EQUIVALENT` | 2 つのそらをとぶの防護の範囲の書き方の違いを同じ結果とする | 3 | adopted_current | なし | そらをとぶ（2 つの書き方） | doc・code・reach_unconfirmed |
| `IA-FULL-HEAL-AGREEING-READINGS` | なんでもなおしはどの読み方でも結果が同じときだけ回復する | 3 | adopted_current | なし | PMCG1-080 なんでもなおし | doc・code・tests_read・reach_unconfirmed |
| `IA-HC1-NONCONFUSED-PROCEED` | はがしてすてるワザは、こんらんでなければ時点の読み方によらず処理 | 3 | adopted_current | なし | ほのおのうず・10まんボルト・… | doc・code・tests_read・reach_unconfirmed |
| `IA-JS1-PROCEED-WHEN-READINGS-AGREE` | JS1 は読み方で最終ダメージが変わるときだけ止める | 3 | adopted_current | なし | じしん・PMCG1-039 レアコイル じばく・… | doc・code・tests_read・reach_unconfirmed |
| `IA-NO-STOP-WHEN-READINGS-COINCIDE` | 未解決の問いでも読み方の結果が同じ場面は止めない | 3 | adopted_current | なし | v0.119〜v0.121 の停止コード・［DARK df］・［NORMAL df］など（v0.97）・… | doc・code・tests_read・reach_unconfirmed |
| `IA-POWER-DAMAGE-WR-SKIPPED-WHEN-NO-DIFFERENCE` | 特殊能力のダメージの弱点・抵抗力は、結果が変わらない範囲だけ計算せずに進める | 3 | adopted_current | なし | R団のカビゴン［わるいねぞう］・kernel.power_damage_to_damage_source・… | doc・code |
| `IA-FLASH-FACE-UP-DECK-READINGS` | フラッシュのおもての山札の受け付ける読み方 | 4 | adopted_current | なし | ES2-035 フラッシュ | doc・code・reach_unconfirmed |
<!-- generated:items-research end -->

### 6.3 技術的な実装方式・過去の記録（`technical`・`history`）

<!-- generated:items-other begin（scripts/check_implementation_assumptions.py --write が台帳から書く。手で直さない） -->
| ID | 名称 | 分類 | 状態 | 承認 | 対象 | 確認 |
|---|---|---|---|---|---|---|
| `IA-ATTACK-COIN-FLIPPER-ATTACKER-SIDE` | ワザの説明のコインを投げるプレイヤー | 2 | adopted_current | なし | ワザのコイン全般・ブリンク（v0.109 で同じ規約を当てはめ） | doc・code |
| `IA-NEXT-OPPONENT-TURN-AS-PLUS-ONE` | 「次の相手の番」を与えた番 + 1 で表す | 2 | adopted_current | なし | ディフェンダー（v0.2e）・かたまる（v0.4b）・… | doc・code・reach_unconfirmed |
| `IA-POWER-ONE-CARD-PER-USE` | エネルギーを動かす・すてる特殊能力は 1 回の使用で 1 枚 | 2 | adopted_current | なし | ［どしゃぶり］（オーダイル PF1-009・NIP2X-001）・［でんじりょく］（レアコイル neo3-045） | doc・code・tests_read・reach_unconfirmed |
| `IA-REASSURE-NO-NAME-READING` | ［REASSURE］はダメージカウンターのないポケモンの名前を読まない | 2 | adopted_current | なし | ［REASSURE］ | doc・code・reach_unconfirmed |
| `IA-BENCH-ONLY-POWER-STATUS-CLAUSE-OMITTED` | ベンチでだけ使う特殊能力の特殊状態の制限を処理しない | 3 | adopted_current | なし | PMCG3-043 カイリュー［かけつける］ | doc・code・reach_unconfirmed |
| `IA-BERRY-BATCH-NO-INTERMEDIATE-CHECK` | きのみどうしはまとめて処理し、途中の状態を確かめない | 3 | adopted_current | なし | きのみ類 | doc・code・tests_read・reach_unconfirmed |
| `IA-BOTH-PLAYERS-ORDER-USER-FIRST` | 両方のプレイヤーの処理は使ったプレイヤー → 相手の順 | 3 | adopted_current | なし | PMCG4-062 ロケット団参上!・PMCG5-084 エリカの親切・… | doc・code |
| `IA-CHOSEN-BENCH-DAMAGE-ANSWER-ORDER` | 選んだ控えへのダメージは答えの並びの順 | 3 | adopted_current | なし | 化石の秘密のライチュウ ギガスパーク（v0.39） | code・reach_unconfirmed |
| `IA-COIN-FLIP-ONE-AT-A-TIME` | 2 枚以上のコインを 1 枚ずつ投げる | 3 | adopted_current | なし | みだれづき（v0.2d）・コインを複数枚投げるワザ全般 | doc・code |
| `IA-COUNTERATTACK-SKIP-ATTACKER-ALREADY-KO` | 自分へのダメージですでに HP 以上のポケモンに「はんげき」を与えない | 3 | adopted_current | なし | PMCG1-008 カイリキー［はんげき］・kernel.power_damage_to_damage_source・… | doc・code・tests_read |
| `IA-DAMAGE-STEP-ADDITIVE-ORDER-NOT-ASKED` | 同じ段階の加算の変更効果の順番を選ばせない | 3 | adopted_current | なし | プラスパワー（複数枚）・ディフェンダー（複数枚） | doc・code |
| `IA-DARK-PULSE-COIN-POSITION` | ［わるいはどう］のコインを投げる位置 | 3 | adopted_current | なし | ［わるいはどう］（effects.DarkPulse。v0.124） | code・reach_unconfirmed |
| `IA-DECK-RETURN-BOTTOM-BEFORE-SHUFFLE` | あとで必ず切る山札にもどす位置は一番下 | 3 | adopted_current | なし | PMCG1-093 ポケモン交換おじさん・くもがくれガス（v0.36 RD10）・… | doc・code |
| `IA-DW2-NO-POWER-NOT-STOPPED` | DW2 は効果を受けないポケモンが特殊能力を持たなければ止めない | 3 | adopted_current | なし | やみのはどう | doc・code・tests_read・reach_unconfirmed |
| `IA-EXP-ALL-NOT-ASKED-WHEN-HOLDER-KO` | 学習装置の持ち主も同じ判定できぜつするなら聞かない | 3 | adopted_current | なし | 学習装置 neo4-109 | doc・code・tests_read・reach_unconfirmed |
| `IA-FLEE-OFFER-ONCE-PER-POKEMON` | ［にげこむ］の機会は同じワザで同じポケモンに 1 つ | 3 | adopted_current | なし | ［にげこむ］（REACTION_SWITCH）・kernel.receiving | code・reach_unconfirmed |
| `IA-HARDEN-THRESHOLD-30` | かたくなるの「20以下」をしきい値 30 として扱う | 3 | adopted_current | なし | かたくなる（v0.105・v0.106） | doc・code・tests_read・reach_unconfirmed |
| `IA-LIGHTNING-BOLT-UNITS-SEPARATE-WHEN-NO-MODIFIER` | エレブーのかみなりショック等: 変更がなければ単位ごとに別々に計算 | 3 | adopted_current | なし | エレブー（ひらいしん・かみなりショック。v0.91） | doc・code・tests_read・reach_unconfirmed |
| `IA-MARKER-ADJACENT-SAME-RESULT-NOT-STOPPED` | CM1・KR1 の隣で結果が同じ場面は止めない | 3 | adopted_current | なし | ペイント・かんぜんかいふく（ミュウツー）・… | doc・code・tests_read・reach_unconfirmed |
| `IA-OCTAZOOKA-HEREAFTER-EXISTING-VALUE` | オクタンほうの「以後」を既存の値で表す | 3 | adopted_current | なし | オクタンほう（v0.93） | doc・code・tests_read・reach_unconfirmed |
| `IA-PARALYSIS-REAPPLY-PROCEED-WHEN-SAME-TURN` | マヒの再付与で回復する番が同じなら進める | 3 | adopted_current | なし | マヒにする効果全般 | doc・code・tests_read |
| `IA-PERSISTENT-EFFECT-EXPIRY-ORDER` | 番の終わりの中の期限切れの順番（トレーナー → 持続する効果 → 失敗の記録） | 3 | adopted_current | なし | 持続する効果全般・procedures._expire_at_turn_end・… | doc・code・reach_unconfirmed |
| `IA-POISON-BYPASSES-DAMAGE-THRESHOLD-POWERS` | どくのダメージをしきい値のある特殊能力に通さない | 3 | adopted_current | なし | PMCG2-027 バリヤード［なぞのかべ］・ポケモンチェックのどく | doc・code・tests_read・reach_unconfirmed |
| `IA-POKEMON-CHECK-DARKNESS-BEFORE-BERRY` | 結果が変わらないときは悪エネルギー → きのみの順で処理する | 3 | adopted_current | なし | きのみ・おうごんのみ・きせきのみ・悪エネルギー | doc・code・tests_read・reach_unconfirmed |
| `IA-POKEMON-CHECK-DARKNESS-EFFECT-ORDER` | 悪エネルギーの効果どうしの順番はログの順（結果が変わらない） | 3 | adopted_current | なし | 悪エネルギー neo1-094・PRN-002・NIP2X-010 | doc・code・tests_read・reach_unconfirmed |
| `IA-POKEMON-CHECK-POISON-ALL-THEN-KO` | ポケモンチェックのどくをすべて与えてからきぜつを処理 | 3 | adopted_current | なし | どく | doc・code・reach_unconfirmed |
| `IA-POWER-INVALID-USE-REJECTED-AS-UNDECLARED` | 使えない特殊能力の使用は、宣言もなかったものとして拒否する | 3 | adopted_current | なし | UsePokemonPower の拒否・かがくへんかガスで消された特殊能力（POWER_SUPPRESSED）・… | doc・code |
| `IA-PREFLIGHT-COUNT-CAPPED-HEAD-CLASSES` | 上限なしコインの先読みで、資源の枚数以上を 1 つの組にまとめる | 3 | adopted_current | なし | まるもうけ（v0.118）・neo4-082/attack/0 | doc・code・tests_read・reach_unconfirmed |
| `IA-PREFLIGHT-ENERGY-DISCARD-BY-CARD-KIND` | 先読みでトラッシュするカードを種類ごとに 1 つだけ試す | 3 | adopted_current | なし | ES2-005/attack/0・QSG-055/attack/0・… | doc・code・tests_read・reach_unconfirmed |
| `IA-PREFLIGHT-SHORTAGE-OVER-CLASS` | 先読みで N+1 以上のおもての数を 1 つの組にまとめる（ドライアップ） | 3 | adopted_current | なし | ES2-005/attack/0・QSG-055/attack/0 | doc・code・tests_read・reach_unconfirmed |
| `IA-PRESENT-DAMAGE-ELEMENTS-FIRST` | プレゼントの要素はダメージを先に並べる | 3 | adopted_current | なし | プレゼント（v0.105） | doc・code・tests_read・reach_unconfirmed |
| `IA-RECOVER-ON-ENTRY-ZERO-AS-DECLINE` | ［つりあげる］の 0 枚は使わないことで表す | 3 | adopted_current | なし | わるいヤドラン［つりあげる］・effects.RecoverPokemonFromDiscardOnEntry | code・reach_unconfirmed |
| `IA-REPEATABLE-POWER-ONE-UNIT-PER-USE` | 何度でも使える効果は 1 回の使用で 1 個（1 枚） | 3 | adopted_current | なし | ヤドランの［へんなこうどう］・PMCG6-090 ヤマブキシティジム | doc・code・tests_read・reach_unconfirmed |
| `IA-SAME-AMOUNT-MULTI-SOURCE-FIELD-ORDER` | 同じ量の複数の発生源は場の並びで処理する（おとしあな・まきびし・ヒートプレート） | 3 | adopted_current | なし | わるいダグトリオ［おとしあな］（PMCG4-043）・［まきびし］・… | code・reach_unconfirmed |
| `IA-SELF-KO-TO-ENERGY-ORDER` | ［エネエネ］はきぜつ → エネルギーとしてつける → サイド → 勝ち負けの順 | 3 | adopted_current | なし | マルマイン［エネエネ］・flow._knock_out_to_energy | code・reach_unconfirmed |
| `IA-SELFDESTRUCT-ELEMENT-ORDER` | じばくの要素の順番 | 3 | adopted_current | なし | PMCG1-039 レアコイル じばく・PMCG3-025 レアコイル じばく・… | doc・code・tests_read・reach_unconfirmed |
| `IA-SETUP-POKEMON-IN-PLAY-BEFORE-FIRST-TURN` | 準備で出したポケモンは最初の番より前から場にいる | 3 | adopted_current | なし | 進化の条件（p.310） | doc・code・reach_unconfirmed |
| `IA-SINGLE-USE-COIN-CHECK-EXPIRES-ON-FLIP` | 「効果は1回できえる」は手順 4 のコインを投げたら消える | 3 | adopted_current | なし | サンド すなかけ | doc・code・tests_read・reach_unconfirmed |
| `IA-TEXT-WORDING-VARIANTS-SAME-TYPE` | 語順・助詞・併記の違う文面を同じ型として受け付ける | 3 | adopted_current | なし | neo1-049/attack/0・PR1-075/attack/0・… | doc・code・tests_read・reach_unconfirmed |
| `IA-TRANSFORM-EVOLUTION-BAN-REGARDLESS-OF-ACTIVITY` | ［へんしん］の進化の禁止ははたらいているかを見ない | 3 | adopted_current | なし | メタモン［へんしん］・effects.evolution_forbidden | code・reach_unconfirmed |
| `IA-TURN-END-DISCARD-ORDER` | 番の終わりのトラッシュの順番 | 3 | adopted_current | なし | プラスパワー・ディフェンダー・… | doc・code・tests_read |
| `IA-BENCH-FROM-DISCARD-CANDIDATE-ORDER` | トラッシュから出す選べるものの並び | 4 | documented_impl_unverified | なし | PMCG1-078 元気のかけら・PMCG1-084 ポケモンの笛 | doc・code・reach_unconfirmed |
| `IA-BLINK-COIN-THROWER-OWNER` | ブリンクのコインを投げる人は持ち主として記録する | 4 | adopted_current | なし | ブリンク | doc・code・tests_read・reach_unconfirmed |
| `IA-CHAR-MARKER-COIN-ORDER-FIELD` | 1 人のプレイヤーのくろこげマーカーのコインの順番は場の並び | 4 | adopted_current | なし | くろこげマーカー | doc・code・tests_read・reach_unconfirmed |
| `IA-DARK-DRAIN-COIN-ORDER-FIELD` | ダークドレインのコインの順番はバトル場 → ベンチの並び | 4 | adopted_current | なし | ダークドレイン | doc・code・tests_read・reach_unconfirmed |
| `IA-ENERGY-CHARGE-REATTACH-FIELD-ORDER` | つけかえる順番は場の並び | 4 | adopted_current | なし | PMCG5-040 マチスのレアコイル［エナジーチャージ］・PMCG5-010 エリカのマダツボミ［ようぶんきゅうしゅう］ | doc・code・tests_read・reach_unconfirmed |
| `IA-FUTURE-SIGHT-DECISION-ORDER` | みらいよちの決める順番 | 4 | adopted_current | なし | PMCG3-032 スリーパー みらいよち | doc・code・tests_read・reach_unconfirmed |
| `IA-PRIZE-OVERFLOW-TAKE-REMAINING` | 取るサイドが残りより多いときは残りだけ | 4 | adopted_current | なし | 複数のきぜつ | doc・code・reach_unconfirmed |
| `IA-QUIZ-ANSWER-CANDIDATES-BUNDLED-POOL` | カツラのクイズ その3の答えの候補は同梱のカードのデータの名前 | 4 | adopted_current | なし | PMCG6-082 カツラのクイズ その3 | doc・code・tests_read |
| `IA-SINGLE-CHOICE-DECISION-STILL-ISSUED` | 選べるものが 1 つでも決定を出す | 4 | adopted_current | なし | ドわすれ・かなしばり（v0.76）・ポケモンのどうぐ（v0.81）・… | doc・code・reach_unconfirmed |
| `IA-BENCH-POSITION-ON-SWITCH` | 入れ替えでもとのバトル場のポケモンは控えのいた位置に入る | 8 | adopted_current | なし | ポケモンいれかえ・ふきとばし・… | doc・code |
| `IA-ENERGY-STAYS-ATTACHED-BETWEEN-DECISIONS` | 2 つの決定のあいだカードはワザを使ったポケモンについたまま | 8 | adopted_current | なし | v0.72 の移すワザ | doc・code・tests_read・reach_unconfirmed |
| `IA-ORACLE-CHECK-FIXED-ORDER-USER-FIRST` | 使う前の引き方の確かめは使ったプレイヤー → 相手の決まった順 | 8 | adopted_current | なし |  | doc・code・reach_unconfirmed |
| `IA-SUDDEN-DEATH-DECK-UID-ORDER-THEN-SHUFFLE` | 延長戦の山札は uid の順に置いてから切る・乱数は続ける | 8 | adopted_current | なし |  | doc・code・tests_read・reach_unconfirmed |
| `IA-POKEMON-CHECK-STEP1-2-KO-TIMING` | ポケモンチェックの 1 と 2 のあいだのきぜつの判定時点（v0.78。v0.79 で PK1 に変更） | 3 | superseded | なし | 悪エネルギー・どく | doc・code・tests_read・reach_unconfirmed |
| `IA-RX1-NOT-ASKED-WITHOUT-LATER-DAMAGE` | あとにダメージの要素のないワザでは RX1 を聞かない | 3 | superseded | なし | ふきとばし・こうそくスピン | doc・code・tests_read・reach_unconfirmed |
<!-- generated:items-other end -->

`technical` に入れたものも、規約として識別しないと決めたものではありません（案）。正規化の検証範囲は項目ごとに記録のままで、全局面へ一般化していません。

## 7. 既存の台帳の 18 対象との対応

<!-- generated:existing-ledger begin（scripts/check_implementation_assumptions.py --write が台帳から書く。手で直さない） -->
| 停止の方針の台帳の規約 | 区分 | この一覧の項目 |
|---|---|---|
| `POLICY:user_simplified_text:PR1-044/attack/0` | user_specified | `IA-USER-BIRTHDAY-COIN-ONLY` |
| `POLICY:user_simplified_text:PR1-072/attack/0` | user_specified | `IA-USER-SPOKEN-CONDITION-IGNORED` |
| `POLICY:user_simplified_text:PR1-072/attack/1` | user_specified | `IA-USER-SPOKEN-CONDITION-IGNORED` |
| `POLICY:user_simplified_text:PR1-090/attack/0` | user_specified | `IA-USER-BIRTHDAY-COIN-ONLY` |
| `POLICY:user_specified_references:GD5-016/trainer` | user_specified | `IA-USER-QUIZ-HEIGHT-OFFICIAL-ZUKAN` |
| `POLICY:user_specified_rules:PR1-027/trainer` | user_specified | `IA-USER-SWAP-OWNERSHIP-RECEIVER` |
| `POLICY:user_specified_rules:neo1-049/power/0` | user_specified | `IA-USER-MIND-GAMES-OPTIONAL-BEFORE-COST` |
| `POLICY:user_specified_rules:neo4-082/attack/0` | user_specified | `IA-USER-MOUNTAIN-CRUSH-MILL-UP-TO-DECK` |
| `POLICY:user_specified_rules:neo4-082/attack/1` | user_specified | `IA-USER-DESTRUCTIVE-FIRE-DECLARE-ORDER-UP-TO` |
| `POLICY:user_specified_names:PR1-075/name` | user_specified | `IA-USER-BILINGUAL-NAME-JAPANESE` |
| `POLICY:user_specified_names:PR1-077/name` | user_specified | `IA-USER-BILINGUAL-NAME-JAPANESE` |
| `POLICY:engine_simplified_text:PMCG6-074/attack/0` | engine_simplification | `IA-ENGINE-SIMPLIFIED-PMCG6-074-ATTACK` |
| `POLICY:engine_simplified_text:PMCG6-074/power/0` | engine_simplification | `IA-ENGINE-SIMPLIFIED-PMCG6-074-POWER` |
| `POLICY:implementation_assumption:1` | implementation_assumption | `IA-PHOENIX-KO-PROCESS-ORDER` |
| `POLICY:implementation_assumption:2` | implementation_assumption | `IA-ENERGY-DRAIN-AUTOMATIC` |
| `POLICY:implementation_assumption:3` | implementation_assumption | `IA-ENERGY-DRAIN-TIMING` |
| `CONV:USER-SUDDEN-DEATH-OWNERSHIP-RESET` | user_specified | `IA-USER-SUDDEN-DEATH-OWNERSHIP-RESET` |
| `CONV:USER-PRIZE-ORDER-ALWAYS-CHOSEN` | user_specified |  |
| `CONV:USER-PRIZE-ORDER-PER-PLAYER` | user_specified |  |
| `CONV:ENGINE-USER-CORRECTION:PR1-069/name.ja` | card_data_correction | `IA-DATA-PR1-069-NAME` |
<!-- generated:existing-ledger end -->

18 対象は 16 項目に当たります（誕生日の 2 対象・発話の 2 対象・ナッシーの 2 対象が、それぞれ 1 規約）。`--check` は、18 対象のすべてがどれかの項目に対応し、台帳の利用者指定には
承認の根拠がある項目だけが、利用者指定でないものには利用者指定でない項目だけが対応することを確かめます。

## 8. 重要な食い違い

コードと文書が食い違う場合も、今回はどちらも直していません。台帳の `discrepancies` に、種類（`kind`）とともに記録しました。

<!-- generated:discrepancies begin（scripts/check_implementation_assumptions.py --write が台帳から書く。手で直さない） -->
| ID | 項目 | 内容 |
|---|---|---|
| `DISC-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO` | IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO | simultaneous-ko-v0.2f.md 5 章の前提（サイドに関わるカードがない）は、v0.106 のおんねん・マチスの交渉・にせオーキドの発明・サイドを見せる/入れかえる力の登録で崩れているが、正規化を見直した記録を見つけていない。テスト PrizeOrderTest はでんげきの盤面 1 つだけ |
| `DISC-POWER-DAMAGE-WR-SKIPPED-WHEN-NO-DIFFERENCE` | IA-POWER-DAMAGE-WR-SKIPPED-WHEN-NO-DIFFERENCE | rules 6 章 564 行は「変わる場合はコードのない問いで止める」とするが、コードには UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE（Z9）がある |
| `DISC-POISON-STING-NO-COIN-ON-KO` | IA-POISON-STING-NO-COIN-ON-KO | 「結果は同じ」と書くが、投げる読み方と乱数の消費が 1 回違い、同じ seed の対戦の続きが変わりうる（文書自身も「乱数の使い方だけが違う」と書く） |
| `DISC-SELF-ATTACK-DAMAGE-WEAKNESS-RESISTANCE` | IA-SELF-ATTACK-DAMAGE-WEAKNESS-RESISTANCE | rules 4 章の表（247 行）に v0.2f の「関係する場合だけ止める」行（UnresolvedSelfWeaknessTest）が残っており、6 章 484 行・v0.3d の変更と食い違う |
| `DISC-POWER-DAMAGE-WR-SKIPPED-WHEN-NO-DIFFERENCE-2` | IA-POWER-DAMAGE-WR-SKIPPED-WHEN-NO-DIFFERENCE | rules-2000-02-14.md 564 行（と rocket-snorlax-v0.17b.md）は、結果が変わる場合を「コードのない問い（RuntimeError）で止める」と書くが、resolution/questions.py では v0.61 から停止コード UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE が付いている（v0.17b の文書は当時の記録） |
| `DISC-RAIN-DANCE-ONE-CARD-PER-USE` | IA-RAIN-DANCE-ONE-CARD-PER-USE | あまごいの印刷の文面「1度に何枚でも」は 1 回に複数枚をつける読み方を示す文面で、最新の説明（枚数を書かない）を採って 1 回 1 枚にした。同値は基本エネルギーだけの範囲の論証 |
| `DISC-BOTH-PLAYERS-ORDER-USER-FIRST` | IA-BOTH-PLAYERS-ORDER-USER-FIRST | v0.55 EK1・v0.63 は「ログの並びだけを決めた・結果は同じ」と書くが、同じ順番の規約 HD1（v0.54）は山札を切る・引く処理を含み、乱数の割り当て順に依存しうる。文書は HD1 に結果の同一性を書いていない |
| `DISC-DECK-RETURN-BOTTOM-BEFORE-SHUFFLE` | IA-DECK-RETURN-BOTTOM-BEFORE-SHUFFLE | PT7 は「ルール上の結果は変わらない（切ったあとの並びは乱数の割り当てで変わる）」と書き、v0.36 RD10 は「結果の分布は同じ」と書く。同じ seed の再現性まで同じという意味ではない |
| `DISC-ENERGY-DRAIN-AUTOMATIC` | IA-ENERGY-DRAIN-AUTOMATIC | v0.68 は採用の仕様と書くが、利用者の明示指定の記録（指定の文・日）は v0.68 の本文にない。承認の状態は確認できない |
| `DISC-MEW-NEUTRAL-SHIELD-SCOPE` | IA-MEW-NEUTRAL-SHIELD-SCOPE | 「相手の」の解釈が、ミュウ（v0.103）・［KEEP］（v0.101）・ぬるぬる／かわす（v0.109）では実際の使い手、既存のエフェクトガード等では今の番のプレイヤーのまま（v0.103 は一括して変えていないと明記）。同じ語の読み方が型ごとに違う。 |
| `DISC-POKEMON-CHECK-STEP1-2-KO-TIMING` | IA-POKEMON-CHECK-STEP1-2-KO-TIMING | v0.78 は片方のプレイヤーだけのきぜつを「どの時点でも結果が変わらない」としたが、v0.79 で変わる場合があったと訂正（PK1）。v0.78 文書の記述は古いまま残る。 |
| `DISC-NO-SHUFFLE-WHEN-NOTHING-SEARCHED` | IA-NO-SHUFFLE-WHEN-NOTHING-SEARCHED | 対象 0 枚のときに山札を切るかが効果ごとに違う（ぎゃくりゅう・おどす／とりさるは切る、すくいあげる・エネルギーアークは切らない）。それぞれ文面から読んだとするが、共通の基準は文書にない。 |
| `DISC-USER-QUIZ-HEIGHT-OFFICIAL-ZUKAN` | IA-USER-QUIZ-HEIGHT-OFFICIAL-ZUKAN | v0.129〜v0.131 の文書は『カツラのクイズ その3 は使う前の確かめをせず答えの段で FU3（正誤が漏れうる）』と書くが、v0.135 で その3 も使う前に止めるよう変わった。古い版の文書の制限の記載は今のコードと合わない（履歴としては正しい）。 |
| `DISC-SUDDEN-DEATH-PRIZES-TAKEN-PER-SEGMENT` | IA-SUDDEN-DEATH-PRIZES-TAKEN-PER-SEGMENT | effects.prizes_taken の docstring の前半は『Rules.prize_count − 今のサイドの枚数』と書き、本体と v0.134 の追記は initial_prize_count。docstring の前半が古い（挙動の食い違いではない）。 |
| `DISC-ENGINE-SIMPLIFIED-PMCG6-074-ATTACK` | IA-ENGINE-SIMPLIFIED-PMCG6-074-ATTACK | pre-freeze-gap-inventory.md 74 行が、エンジンの簡略化 2 対象を「キョウのベトベトンのエンジン簡略化2対象」と書く。簡略化の対象はイマクニ？のドードー PMCG6-074（写しで確認）で、キョウのベトベトンは PMCG6-023（だつりょくえき。実装上の仮定 2・3）。stop-policy-decisions.md 39 行の同じ取り違えは 42 行で訂正済みだが、pre-freeze-gap-inventory.md は訂正されていない（文書の誤り。コードの食い違いではない） |
| `DISC-READINGS-WIGGLYTUFF-HELPING-HAND` | IA-READINGS-WIGGLYTUFF-HELPING-HAND | rules-2000 7 章 v0.125 の行（1019 行）は、ふくらむの「次の相手の番」をどくに当てはめない読みを v0.125 のプクリンだけに入れ、同じ書き方の既存の登録（ちいさくなる・neo4-085 のふくらむなど）は v0.124 までの実装のままと書く。同じ文面で読み方が版によって分かれている（意図した据え置きとして記録されている） |
| `DISC-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO-2` | IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO | implementation-status.md は同じ正規化を 347 行では「実装上の仮定（今の対応カードでは起こらない）」、79・496・921 行では「結果が同じための正規化」と書く。分類の言い方が版の節で揃っていない（挙動の食い違いではない） |
| `DISC-POKEMON-CHECK-STEP1-2-KO-TIMING-2` | IA-POKEMON-CHECK-STEP1-2-KO-TIMING | procedures.pokemon_check_poison の docstring（178 行）は v0.78 の「1 と 2 のあいだのきぜつの判定の時点は決めない（どの時点でも結果が変わらない場合だけを処理する）」をそのまま書き、v0.79 の PK1（UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT。_pokemon_check_plan が mid_check_knockout_divergence で止める）への変更を書いていない。コードは PK1 を処理している |
| `DISC-PREFLIGHT-ENERGY-DISCARD-BY-CARD-KIND` | IA-PREFLIGHT-ENERGY-DISCARD-BY-CARD-KIND | 項目の適用範囲はドライアップ・はかいのほのおのエネルギーのトラッシュだが、programs.card_id_answers（6692 行。v0.15c の手札・山札・トラッシュのカードをカード id でまとめる先読み）が同じ形の正規化をより広い要素に当てている。項目の applies_when を広げるか別項目にするかの判断が要る |
| `DISC-BENCH-POSITION-ON-SWITCH` | IA-BENCH-POSITION-ON-SWITCH | 項目は入れ替えでもとのバトル場のポケモンが控えのいた位置に入るとするが、マチス（zones.hand_basic_to_active）ではベンチの最後にもどす。場の並びは複数のコインの順（くろこげマーカー・おとしあな等）に使うので、位置の扱いが 2 通りあることを項目に書く必要がある |
| `DISC-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO-3` | IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO | simultaneous-ko-v0.2f.md 5 章の正規化の理由 2（情報）と前提（サイドを見る・入れ替えるカードがない）は、v0.63 のおもてのサイド（ロケット団参上!・カードめくりゲーム）以降の現行コードでは字義どおりには成り立たない。後に取るプレイヤーは先のプレイヤーの取ったおもてのカードを見てから選べる。カードの動き・乱数・勝敗は同じ選択の組なら同じ。文書が求める見直しの記録は見つからない |
| `DISC-RAIN-DANCE-ONE-CARD-PER-USE-2` | IA-RAIN-DANCE-ONE-CARD-PER-USE | v0.6 の正規化の条件（つけたことで引き起こされることがない）は、v0.86 の「手札からエネルギーをつけたとき」にはたらく力・v0.116 の status_on_energy_attach が、あまごいでつけた事実にも反応するようになってから字義どおりには成り立たない。1 枚ずつの使用の連続と、まとめてつける読み方で反応の回数が同じかの記録は見つからない |
| `DISC-TRAINER-DISCARD-AFTER-RESOLUTION` | IA-TRAINER-DISCARD-AFTER-RESOLUTION | rules 5 章は「3 枚では、トラッシュの時点で結果は変わらない」とする正規化だが、v0.55 のトラッシュ交換（PMCG6-077）はトラッシュの枚数を数えて山札にもどすので、使っているカードをトラッシュに含めるかで結果が変わる。エンジンは含めない読み方を採っている（DiscardPileExchange） |
| `DISC-BOTH-PLAYERS-ORDER-USER-FIRST-2` | IA-BOTH-PLAYERS-ORDER-USER-FIRST | v0.54 の HD1 は「どちらの順でも結果の分布は同じ。乱数の使い方の順番だけ」とするが、同じ順番を当てはめた v0.80 のタイムカプセル（neo1-091）・ポケモンマーチ（neo1-076）は各プレイヤーが選ぶ決定を順に出すので、相手は使ったプレイヤーの選択（公開）を見てから選ぶ。情報の順番が変わる点は記録にない |
| `DISC-INF-STICKY-NO-PARALYSIS-ON-KO` | IA-INF-STICKY-NO-PARALYSIS-ON-KO | rules 6 章（532 行）・forced-switch-v0.4d の実装の記述は DamageResult.knocked_out で判断するとするが、現行コードは共通の要素（programs.Status・ForceSwitch）が AttackRun.knocked_out（今のダメージと HP）で判定する。結果は同じだが、文書の実装欄が旧い |
| `DISC-DAMAGE-SWAP-ONE-COUNTER-PER-USE` | IA-DAMAGE-SWAP-ONE-COUNTER-PER-USE | phase 1 の項目の applies_when のカード番号が写しと合わない: フーディンは PMCG1-049（PMCG1-001 はフシギダネ）、フシギバナ（IA-ENERGY-TRANSFER-ONE-CARD-PER-USE）は PMCG1-011（PMCG1-015 はロコン）、カメックス（IA-RAIN-DANCE-ONE-CARD-PER-USE）は PMCG1-032（PMCG1-002 はキャタピー）。文書・コードは正しい番号を使っている |
| `DISC-DEVOLUTION-ONCE-ATTACK-RECORD-KEPT` | IA-DEVOLUTION-ONCE-ATTACK-RECORD-KEPT | v0.50 の文書の「消えるもの」にない ワザの履歴（v0.62 clear_history）とマーカー・カウンター（v0.90 remove_markers）を、現行の evolution.devolve は退化で消す。v0.50 の文書の列挙が現行と合わない（後の版の文書での記載は未確認）。 |
| `DISC-ENERGY-CHARGE-NO-TARGET-UNUSABLE` | IA-ENERGY-CHARGE-NO-TARGET-UNUSABLE | 等価の根拠（回数の制限がないので使ったことになるかで結果が変わらない）は盤面の結果だけの等価で、使用の宣言のログ（公開）と合法手の有無では差が出る。 |
| `DISC-FULL-HEAL-AGREEING-READINGS` | IA-FULL-HEAL-AGREEING-READINGS | v0.55 文書の判断の一覧（250 行）は FH2 を「なんでもなおしは、どの読み方でも結果が同じ場合だけ回復する」とするが、コードの FH2（v0.72。FULL_HEAL_WITHOUT_CONDITION_CODE）は「再録の版で自分の対戦ポケモンに特殊状態がないとき」で、同じ ID が別の内容に使われている |
| `DISC-HC1-NONCONFUSED-PROCEED` | IA-HC1-NONCONFUSED-PROCEED | v0.31 文書の成立条件は「こんらんでなければ」だけだが、v0.114 から相手のバトル場のベイビィポケモンのルールのコインがあるときも HC1 で止める（こんらんでなくても止まる場面がある） |
| `DISC-POISON-BYPASSES-DAMAGE-THRESHOLD-POWERS` | IA-POISON-BYPASSES-DAMAGE-THRESHOLD-POWERS | v0.46 文書は「どくの処理は通していません」と書くが、v0.47 から ZeroLargeDamageReceived.poison_damage_modifier でなぞのかべもどくの処理を通り、量が変わるかを計算して止める（10・20 では止めない結果は同じ） |
| `DISC-IMMUNITY-SKIPS-STATUS-QUESTIONS` | IA-IMMUNITY-SKIPS-STATUS-QUESTIONS | v0.46 文書はカビゴンの［めんえき］だけを書くが、status_immunity は v0.84 からきらめきタッチの効果も返すので、同じ問いを聞かない処理がそれにも当たる |
| `DISC-JS1-PROCEED-WHEN-READINGS-AGREE` | IA-JS1-PROCEED-WHEN-READINGS-AGREE | 項目（文書の要約）は「変わるときだけ宣言の前に止め」とするが、スパーク（ChosenBenchDamage）は変わる控えを選べて選ぶと止め、どの控えでも変わるときだけ宣言の前に止める（v0.39 文書の記載とは合う） |
| `DISC-POKEDEX-ZERO-IS-NOT-LOOKING` | IA-POKEDEX-ZERO-IS-NOT-LOOKING | PD1 は PMCG1-082 の文面だけに当たる。再録の版（GD1-022・GD5-023。「最大5枚」）は v0.72 から zero_allowed=False で、0 枚を見ないこととして受け付けない |
| `DISC-RECALL-SAME-POKEMON-ONLY` | IA-RECALL-SAME-POKEMON-ONLY | 文書は「同じときだけ選べる」と書くが、コードは違うときも選べるものに入れ、選ぶと RC3（UNRESOLVED_RECALL_TARGET_CHANGED）で止める（選べないのではなく止める） |
| `DISC-SCOOP-UP-DISGUISE-CARD-DISCARDED` | IA-SCOOP-UP-DISGUISE-CARD-DISCARDED | MrFujiTest.test_disguise_and_fossil_go_with_the_stack の docstring は「ばける」でのせたカードも確かめるとするが、中身はなにかの化石の重なりだけで disguise の場面を作っていない |
| `DISC-SEARCH-SHUFFLE-WITHOUT-CHOICE` | IA-SEARCH-SHUFFLE-WITHOUT-CHOICE | 文書の対象「山札をさがす 4 枚」と v0.53 の表で選ばなくてよい山札をさがすトレーナー（3 枚に見える）の数が合わない。また共通の処理 SearchDeckTrainer は後の版のカードにも使われ、対象が 4 枚に限られない |
| `DISC-SABRINA-REATTACH-THEN-EVALUATE` | IA-SABRINA-REATTACH-THEN-EVALUATE | v0.55 の文書・docstring は after_energy_attached と書くが、現行は v0.116 の energy_attached_by_effect と AT1 の事前確認に置きかわっている（読み方は同じ） |
| `DISC-SINKHOLE-TIMING-AFTER-SWITCH` | IA-SINKHOLE-TIMING-AFTER-SWITCH | 文書 v0.61 3.3 は (b)（受けるダメージがバトル場とベンチで違う）は今の写しでは起こらないと書くが、v0.65 で［ベンチガード］が加わり、ベンチでだけ受けるダメージが変わりうる。コードは SH1 ではなく UNSUPPORTED_BENCH_GUARD_OUTSIDE_ATTACK で止める（黙って入れ替えのあとに処理しない） |
| `DISC-SWIFT-EFFECTS-BY-HOLDER` | IA-SWIFT-EFFECTS-BY-HOLDER | 文書 v0.60 5 章は SS1 を今の写しでは起こらないコードのない問いと書くが、v0.97 からアンノーン[N] で起こり、停止コード UNRESOLVED_SPEED_STAR_SCOPE を持つ |
| `DISC-THUNDERSTORM-COINS-BEFORE-DAMAGE` | IA-THUNDERSTORM-COINS-BEFORE-DAMAGE | 文書は 1 匹ずつ投げても分布は同じと書くが、v0.65 の［ベンチガード］の決定はすべてのコインの結果のあとに出るので、1 匹ずつの読み方とは決定のときに分かっている情報が違い、結果が変わりうる（文書に記載なし。TS1 のような止め方はない） |
| `DISC-WARP-POINT-SG1-ONLY-WITHOUT-BENCH` | IA-WARP-POINT-SG1-ONLY-WITHOUT-BENCH | 文書 v0.55 は使ったプレイヤーに控えがいれば SG1 の問いにならないと書くが、コードは v0.93（バトル場をはなれられない）・v0.117（［でんせつのからだ］）で控えがいても止める条件を加えている（文書は当時の範囲） |
| `DISC-NO-SHUFFLE-WHEN-NOTHING-SEARCHED-2` | IA-NO-SHUFFLE-WHEN-NOTHING-SEARCHED | 同じ書き方（「…「おもて」の数ぶんの…を山札から選び出し…。その後、その山札をよく切る」）で、エネルギーアーク（トレーナー）は「おもて」0 で切らず、デンリュウのゆうでん・ピッピのみんなでおどる（ワザ、v0.113）は 0 でも切る。コードは「読み方は移さない」と書くが理由の記録がない。また任意の回収・検索で 0 枚のとき、すくいあげるは切らず、おつかい（RevealTrainerFromDeck）・SR1 は切る。共通の基準は見つからない（意図した違いか未確認） |
| `DISC-HEALING-WIND-TARGETS-AT-APPLICATION` | IA-HEALING-WIND-TARGETS-AT-APPLICATION | v0.86 文書 8.1 は「ほのおのまもりは効果を与えたときの自分の場のポケモン全員」と書くが、コードは与えたときの控えに効果を与えるだけで、あとから控えになったポケモン・バトル場に出た受けたポケモンへの当てはめは PL1（UNRESOLVED_PROTECTIVE_FLAME_SCOPE）で止める。「あとから出たポケモンは含めない」という読みは採用されていない |
| `DISC-NAME-COUNT-EXACT-CURRENT-FORM` | IA-NAME-COUNT-EXACT-CURRENT-FORM | v0.106・v0.88 の文書の「今の姿の名前の完全一致」は、v0.124 で変身したポケモンが変身の前後の両方の名前で当たるように変わったことを反映していない |
| `DISC-GRUDGE-PRIZES-TAKEN-COUNT` | IA-GRUDGE-PRIZES-TAKEN-COUNT | v0.106 の文書の「準備で置く数 − 今のサイドの枚数」は、v0.134 で準備で置く数が今の区間の枚数（延長戦は 1 枚）になったことを反映していない |
| `DISC-BERRY-BATCH-NO-INTERMEDIATE-CHECK` | IA-BERRY-BATCH-NO-INTERMEDIATE-CHECK | v0.81a の文書の「きのみどうしの途中の状態は確かめず組（2^k）だけ比べる」は v0.82 で変わり、ほかのポケモンの問い合わせを変えるきのみは並べ方をすべて比べ、まとまりごとに受け付けられない状態を確かめる |
| `DISC-KO-SURVIVAL-FURTHER-DAMAGE-NOT-STOPPED` | IA-KO-SURVIVAL-FURTHER-DAMAGE-NOT-STOPPED | 止めない正規化の検証範囲として文書 5.2 が挙げる場面は、どれも KS1 で止める場面で、止めない場面（同じワザの 2 つ目のダメージ・返す効果）のテストが見つからない |
| `DISC-LEAVE-LOCKED-OPTIONAL-SELF-SWITCH-NOT-ASKED` | IA-LEAVE-LOCKED-OPTIONAL-SELF-SWITCH-NOT-ASKED | 変わり身の術・［にげこむ］を、はなれられないポケモンで聞かない処理（usable_ninja_tricks・offer_flee）を確かめるテストが見つからない |
| `DISC-POWER-EFFECT-PERSISTS-AFTER-USER-LEAVES` | IA-POWER-EFFECT-PERSISTS-AFTER-USER-LEAVES | 項目の文は［QUICKEN］と［げんしのゆめ］をまとめて「使ったポケモンが場にいて特殊能力が消えているときは PM1 で止める」と書くが、［QUICKEN］は QK1（UNRESOLVED_QUICKEN_EFFECT_SUPPRESSED。effects.quicken_suppressed_question・v0.117 文書 312 行）、PM1 は［げんしのゆめ］（effects.fossil_attack_bonus_problem）。コードと各版の文書は一致し、フェーズ 1 の項目の文の誤り |
| `DISC-RX1-NOT-ASKED-WITHOUT-LATER-DAMAGE` | IA-RX1-NOT-ASKED-WITHOUT-LATER-DAMAGE | v0.94 文書 7 章は RX1 を今も働く停止として書くが、v0.124 で処理のあいだの姿の固定（CR-TRANSFORM-FROZEN-DURING-ACTION）が入り、ForceSwitch._form_changes は form_frozen で () を返すので、ワザの効果の入れ替えでは RX1 も「聞かない」正規化も働かない（v0.124 文書 3.5 節が置きかえを明記。テスト DragOutTransformTest のコメントも同じ）。v0.94 文書は履歴のまま更新されていない |
| `DISC-THREATEN-STEAL-NO-CARD-SHUFFLE` | IA-THREATEN-STEAL-NO-CARD-SHUFFLE | 項目の文「おどすで相手の手札も山札も 0 枚ならコインを投げない（p.309・v0.45）」を、CoinLookOpponentHandTrainerToDeck の説明（見る前にトレーナーがないことでコインを省かない）では確かめられなかった。両方 0 枚の分岐の位置は未確認（食い違いと断定しない） |
| `DISC-UNOWN-BYVG-READINGS` | IA-UNOWN-BYVG-READINGS | IA-UNOWN-BYVG-READINGS と同じ記載（v0.98 文書 7 章・rules-2000-02-14.md の v0.98 の参照）の重複項目 |
| `DISC-SUDDEN-DEATH-ORIGIN-READING` | IA-USER-SUDDEN-DEATH-OWNERSHIP-RESET | 指定の文は「とりかえっこプリーズで交換したカードは、元の所有者へ戻す。」。エンジン（sudden_death.USER_SUDDEN_DEATH_OWNERSHIP_RESET）は「元の所有者」を、再交換があっても最初のデッキに入れたプレイヤー（出所 origin）と読む。再交換の場合の読みは指定の文だけでは決まらない（エンジンの解釈）。挙動は変えていない |
<!-- generated:discrepancies end -->

要点:

1. **正規化の前提が後の版で崩れたもの（`premise_changed`）**。「結果が同じ」の根拠が、のちに登録したカードで字義どおりには成り立たないのに、見直しの記録がない。
   - 同時のきぜつでサイドを取る順番（v0.2f）。v0.63 以降の表向きのサイドでは、後に取るプレイヤーが、先に取られたカードを見てから選べる。カードの移動・乱数・結果は同じで、決定の時点の情報だけが違う。テストは裏向きのサイドの盤面だけ。
   - 使ったトレーナーをトラッシュする時点（v0.2b）。トラッシュ交換（PMCG6-077）では結果が変わり、エンジンは「含めない」読みを採っている。
   - あまごい（v0.6）。v0.86・v0.116 の「つけたとき」の反応がある。
   - 両方のプレイヤーの処理の順（HD1）。タイムカプセル・ポケモンマーチでは、相手が公開の選択を見てから選べる。
   - おとしあな・サンダーストーム。v0.65 の［ベンチガード］がある。
   - ワープポイント、HC1、スピードスター、めんえき、なぞのかべとどく、名前で数える効果、おんねん。
2. **「結果が同じ」が限られた意味のもの（`equivalence_scope`）**。
   - どくばりで相手がきぜつしたらコインを投げない。乱数の消費が 1 回少なく、同じ seed の続きが変わる。
   - 山札の一番下にもどしてから切る。分布は同じだが、並びは違う。
   - エネルギーチャージの 0 枚。盤面は同じだが、宣言のログと合法手は違う。
3. **文書とコードの食い違い（`doc_vs_code`）**。
   - Z9 は「コードのない問いで止める」と書くが、停止コード `UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE` がある。
   - 思い出させるワザは「同じときだけ選べる」と書くが、実際は違うときも選べ、選ぶと RC3 で止まる。
   - ほのおのまもりは「与えたときの全員」と書くが、実際はあとの当てはめを PL1 で止める。
   - 入れ替えの位置は通常とマチスで 2 通りある。
   - ほかに、ID の FH2 が 2 つの意味で使われている、ポケモンチェックの docstring が v0.78 のままになっている、など。
4. **似た文面の扱いが効果ごとに違うもの（`inconsistent_handling`）**。
   - 対象 0 枚のときに山札を切るか。エネルギーアークは切らず、ゆうでん・みんなでおどる・ぎゃくりゅうは切る。共通の基準・理由の記録がない。
   - 「相手の」の読み方。実際の使い手で読む型と、今の番のプレイヤーで読む型がある。
   - ふくらむの「次の相手の番」の読み方が版で分かれている。
   - 統一も、意図した違いかの判断もしていません。
5. **この一覧の作成中に直した記載（`ledger_internal`）**。どれも、調べる前の版の記載の誤りや重複です。文書・コードは変えていません。
   - 3 項目のカード番号。フーディン PMCG1-049・フシギバナ PMCG1-011・カメックス PMCG1-032 が正しく、誤っていた番号は別のカードでした。
   - ［QUICKEN］の止め方（QK1）。
   - 重複した 1 項目の統合。

## 9. 除外した重要な候補

台帳の `notable_exclusions` に、除外の理由と参照を残しました。採否の判断で見落としやすいもの:

- **情報漏れの修正の保守的な制限**（10。v0.129〜v0.138）。次の 2 つは、合法手を決めています。規約集合の要素ではなく、両モード共通の安全境界（AGR-MODE-SAFETY）の側で扱います。
  - クイズ・カードめくりゲームで、両方の結果の引き方を使う前に確かめること。
  - 山札の検索・遺跡の石版・エネルギー増幅装置で、本人に見えない自分のカードから下限 max(0, K−C) を求めて止めること。前提として「持ち主は自分のデッキリストを知っている」を採っていますが、観測には入っていません。
- **止める範囲が必要より広い停止**（9）。こんらんの 20 とダメージを変えるカードの停止は、プテラ・グライガーの組では、読み方の結果が同じでも止めます（v0.3c のまま）。RX1 も、同じゲーム用データの再録で止めます。
- **乱数・再生の約束の実装方式**（8）。次のものは、同じ seed の再生の約束として固定されています。分布は同じで、規約ではありません。保存と再生の識別で必要になります。
  - 山札を uid の順に置き、プレイヤー 0 → 1 の順に切ること。
  - コインを `getrandbits(1)` で決めること。
  - 0・1 枚の山札を切るときに乱数を使わないこと。
- **選べるものが 1 つでも決定を出す（K2）・拒否のコードの順番**（8。API の形）。

## 10. 採否を決める順序（案）

台帳の `decision_order` に、各段の項目 ID を列挙しました。**どれも決めていません。**

| 順 | 対象 | 理由 |
|---:|---|---|
| 1 | 既存台帳の利用者指定でない 5 件（ドードー 2・ふしちょう・だつりょくえき 2） | DEC-BASELINE-NONUSER で名指しされている |
| 2 | 後年の資料による採用（分類 5。今はだつりょくえきの DR1 の 1 件） | CLAUDE.md の「後年の裁定で補わない」との関係を判断する必要 |
| 3 | 前提の崩れ・食い違いのある正規化 | 比べる範囲を確かめ直すか、選ばせる・止めるかを先に決める |
| 4 | 結果・乱数・合法手に影響しうるエンジンの採用（分類 4） | 入れないなら止める場面・続行規約が要る |
| 5 | 推論・類推（分類 2）と研究で確認すべき項目 | 研究で確かめるか、推論のまま入れるか |
| 6 | 残りの正規化・技術的な実装方式 | 規約として識別しない案を一括で確かめる |

## 11. 確認していない範囲

- **照合の深さ**: 主要な一覧の項目の多くはコードの処理まで確かめました（集計の「確認の段階」）。ただし、次は確かめきれていません。
  - テストの中身まで読んだのは一部です。
  - 今回テストを実行したのは、既知の項目に結び付く 19 のテストのクラス・モジュール（112 件 OK）だけです。
  - ほかの項目の `tests_read` は、テストを読んだことで、実行ではありません。
  - 状態が `documented_impl_unverified` の項目（集計の「状態別」）は、主に v0.1〜v0.7 の推論の記録と、v0.118〜v0.125 の読み方の束です。
- **到達経路と影響**: 別の扱いの影響の軸のうち多くは `unconfirmed` です（`reach_unconfirmed`）。到達の頻度・組み合わせで初めて起こる場面は調べていません。
- **項目の粒度**: v0.111〜v0.125 の「実装上の読み方」は、版ごとの束（`IA-READINGS-*`）のままです。カードごとに分けるかは採否の判断の前に決めます。くすぐりマシーンの項目も 3 つの読みを束ねています。
- **キーワードのない見直し**: エンジンの 13 モジュールを読んだ深さに差があります（台帳の `keywordless_review_scope`）。`effects.py`・`resolution/` のカードごとの登録の固定順序は、候補の語のある箇所と、版の文書から見つけたものだけです。
- **kyuura**: カツラのクイズの値（9242b9b）・v0.128 の目録の記録と、固定研究基準の関係。
- **作業の分担**: 候補箇所の整理と項目の照合は、版の範囲・項目で分けた調査で行いました（台帳の `origin_partitions`）。統括は、既知の項目の照合、重複の統合、食い違いの分類を行い、照合の担当が見つけた誤りの一部を直しました。それ以外の各項目の記述は、照合の担当の確認のままです。

## 12. 検証

| 検証 | 内容 |
|---|---|
| ID の一意性・参照切れ | `--check`: 項目・候補箇所・食い違いの ID の重複、統合先・候補箇所の項目・食い違いの項目・採否の順序の項目が一覧にあること、文書・コード・テストのファイルがあること、コードの名前・テストのクラスとメソッドがあること |
| 候補箇所の整理 | `--check`: 各候補箇所が item・merged・excluded・unconfirmed のどれかで、除外には理由の区分と理由がある。`--sites`: 今の木の走査と台帳の候補箇所の差（基点の時点では差なし。後の正当な文書の変更で差が出るのは数え上げのやり直しの合図で、テストの失敗にしない） |
| 承認の根拠 | `--check`: 利用者承認は利用者指定・利用者が示したデータの訂正だけで、文書・日・指定の文があり、指定の文が根拠の文書にある。利用者指定は承認の根拠を持つ。停止の方針の台帳の 18 対象との対応 |
| 研究の論点を解決済みにしない | `--check`: UQ- を持つ項目の内容に「解決済み」などと書かない。研究の論点の状態を持たない |
| 現行と過去の区別 | 状態 `superseded`・`merged_duplicate` と群 `history` |
| 集計と台帳の一致 | `--check`: `counts` を台帳から数え直した値と同じ。この文書の生成した表が台帳と同じ |
| 動作が変わっていないこと | 変えたのは文書 2 つ（この文書と台帳）・設計の文書 2 つの参照・スクリプト 2 つ・台帳のテスト 1 つだけ。`kyuura_engine/`・既存のテスト・カードデータ・固定デッキ・参照データは変えていない（`git diff --stat` で確認） |

単体テスト `tests/test_implementation_assumptions.py` は、台帳の内部の整合（`--check` と同じ）と、検査が誤りを見つけることを確かめます。件数を写した期待値は持ちません。

## 13. 保守

- 項目を加える・直すときは台帳（JSON）を直し、`--write` で集計と表を書き直します。表を手で直しません。
- 仮定の採否を決めたら、判断事項の文書と停止の方針の台帳に記録し、この一覧の `baseline_decision` を合わせます（採否をこの一覧だけで決めない）。
- 版の文書が増えて `--sites` に新しい候補箇所が出たら、その版の作業で整理を加えます。

## 14. 追記（後の調査）

後の調査の結果は、この一覧の項目・状態・群・集計を書き換えずに、台帳の `addenda` に参照として足します（集計 `counts` には入れません。上の各章は元の調査時点の記録です）。`--check` は追記の ID・種類・参照先・項目があることを確かめます。

<!-- generated:addenda begin（scripts/check_implementation_assumptions.py --write が台帳から書く。手で直さない） -->
| 追記 | 日 | 基点 | 種類 | 項目 | 参照先 | 内容 |
|---|---|---|---|---|---|---|
| `ADD-NORMALIZATION-REVALIDATION` | 2026-11-03 | `2d67820` | revalidation | 26 項目 | [docs/normalization-revalidation.json](normalization-revalidation.md) | 採否判断の順序 3 段目の 20 項目と、範囲を広げた 6 項目の正規化の成立条件を、現行コード・テスト・再現で確かめ直した結果（分類 A〜D・優先・推奨対応の提案）。この一覧の項目の記載・状態・群・集計は元の調査時点のまま |
| `ADD-CATALOG-SCOPE-APPROVAL-QUOTE` | 2026-11-03 | `2d67820` | approval_supplement | 1 項目 | [docs/normalization-revalidation.json](normalization-revalidation.md) | 利用者が示した指示の文（3 枚の非対戦カードへの移管）を approval_supplement に収録。承認は 3 枚の移管だけで、分類方式・記録と ID の設計・拒否の仕方は承認なし。この項目の approval は元の調査時点の記録として書き換えていない |
| `ADD-V0139-PRIZE-ORDER-HC1-FIX` | 2026-11-03 | `4ded418` | fix | 2 項目 | [docs/prize-order-hc1-fix-v0.139.md](prize-order-hc1-fix-v0.139.md) | v0.139 で 2 項目の論点を直した（両モード共通の不具合として）。サイド: 両方がサイドを取り、どちらかのサイドにおもてのカードがあるとき、番のプレイヤーが次に取るプレイヤーを選ぶ決定（prize_order。p.325）を出す（すべてうらなら v0.2f の正規化のまま）。HC1: p.309 の手順 4 のコイン（すなかけなど・［はんこう］）があるときも、こんらん・ベイビィと同じくコインの前に UNRESOLVED_DISCARD_ENERGY_TIMING で止める（HC1 は未解決のまま）。元の項目の記載・状態・集計は元の調査の時点のまま |
| `ADD-PRIZE-ORDER-FOLLOWUP` | 2026-11-03 | `789f58e` | followup | 1 項目 | [docs/prize-order-followup.json](prize-order-followup.md) | v0.139 のあとの追加の検証（調査・再現・分類だけ。動作は変えていない）。本人だけが知るうらのサイド: 位置ごとの知識だけでは今の観測で順番による差はないが、［おみとおし］で先に取るプレイヤーの手札が見えると、どのサイドもうらでも後のプレイヤーの観測が変わる（合法な操作で再現。今の条件に加える必要がある候補）。単位: 1 枚ごと（今）とプレイヤーごとで、届く並び・決定の数・決定の時点の情報が変わり、カードの動き・勝ち負けは変わらない。保存形式 34: 既存の約束の範囲内。v0.138 は prize_order の写しを読み込み、再開で RuntimeError。この項目の記載・状態・集計は元の調査時点のまま |
| `ADD-PRIZE-ORDER-UNIT-ASSUMPTION` | 2026-11-03 | `789f58e` | assumption | 1 項目 | [docs/prize-order-followup.json](prize-order-followup.md) | v0.139 で加えた実装上の仮定（p.325 の一般規定は公式資料、同時のきぜつのサイドへの当てはめは v0.2f の導出、単位と決める時点は v0.86 の反応の順番からの類推と実装の選択）。利用者の承認はない。比べた読みと差は docs/prize-order-followup.md 2 章 |
| `ADD-V0140-PRIZE-ORDER-USER-RULE` | 2026-11-03 | `d631038` | user_rule | 1 項目 | [docs/prize-order-user-rule-v0.140.md](prize-order-user-rule-v0.140.md) | v0.140 で利用者の指定 2 点を採った（両方が取るときはいつも番のプレイヤーが先に取るプレイヤーを選ぶ・選ばれたプレイヤーがまとめて取る）。v0.2f の正規化・v0.139 の「おもてのサイドがあるときだけ」の条件・追加検証で台帳に加えた「1 枚ごと」の仮定（ADD-PRIZE-ORDER-UNIT-ASSUMPTION）を置きかえた。公式の裁定・研究上の解決ではない。p.325 の一般規定とその当てはめの導出は変えていない。取ったサイドの位置の観測は今のまま（承認ではない）。この項目の記載・状態・集計は元の調査時点のまま |
| `ADD-V0140-UNSUPPORTED-DECISION-FIX` | 2026-11-03 | `d631038` | fix | 1 項目 | [docs/prize-order-user-rule-v0.140.md](prize-order-user-rule-v0.140.md) | 追加検証の FU-D2 を直した: この版が扱えない再開先の決定を待つ状態（後の版の状態の写し・v0.139 の prize_order）は、観測・コマンドの前に UNSUPPORTED_DECISION で拒否する（内部エラーにしない）。知っている再開先の壊れた状態は StateIntegrityError。前の版の動きは変えられない。この項目の記載・状態・集計は元の調査時点のまま |
| `ADD-V0141-PRIZE-ORDER-CLEANUP` | 2026-11-04 | `c68b3cd` | followup | 1 項目 | [docs/prize-order-v0140-cleanup-v0.141.md](prize-order-v0140-cleanup-v0.141.md) | v0.140 の後の整理（規約は変えていない）: 旧経路の記録と全体では比べない対戦を、規約の変更が加えた差（決定の番号・first・prize_first の歩）だけに限り、従来の順のやり直しが記録と同じことを求める。対戦のテストの accepted の増加が prize_first の答えの数と同じことを基点の木で確かめ、答えを別に数える。両方が取る並びに first がない状態は、前の版で正しく作った状態と区別できないので、ADD-V0140-UNSUPPORTED-DECISION-FIX の「壊れた状態」ではなく、続けるのに必要な情報の不足として拒否する（StateIntegrityError のまま。文だけ変えた）。比べて観測した差と仕様上起こりうる差（取る順番で後の情報・選択・勝敗が変わりうる）を分けて記録した。この項目の記載・状態・集計・前の追記は元のまま |
| `ADD-V0145-POISON-MIST-PLAY-PO` | 2026-11-05 | `f03238c` | followup | 1 項目 | [docs/poison-mist-play-po-v0.145.md](poison-mist-play-po-v0.145.md) | v0.145 で、この項目のどくの量の読み方（特殊などく・［ポイズンミスト］を鋼エネルギーより先・ほかの順番は決めない・2 つ以上を足さない）が止めていた PO1〜PO3 のうち、PO1・PO2・PO3 の #source-left を、利用者が採用した続行規約（PC-POISON-AMOUNT-ORDER@1・PC-POISON-MIST-TARGETS@1・PC-POISON-MIST-SOURCE-LEFT@1）として、開発用の集合 CS-KYUURA-PLAY-PO@1 だけで続ける。厳密側（既定）・S2a の集合の挙動は今のまま止める。2 つ以上の記録を足さないのは v0.119 の扱いのまま（新しい裁定ではない）。PO3 の #power-lost は続行側でも止める。この項目の記載・状態（承認なし）・集計・前の追記は元のまま |
<!-- generated:addenda end -->
