# v0.125: プクリンの最新の説明・てだすけ

kyuura の研究（プクリンの最新の説明・コインで決まる枚数の不足の調査）を採用する移行を、カードの登録とは別の段にしました（2 章）。その上で、プクリン（拡張シート第1弾青版。ES1-027）
の 1 枚（ワザ 1・特殊能力 1）を登録します（3 章以降）。最新の説明を使って確定した通常の場面を動かし、未解決の境界だけを明示的に止めます。

## 1. 開始点と範囲

- エンジンの基点は `e165fe0fb3de0e73129135f8cbaa34e2aae0eb64`（v0.124 の最後のコミット。ブランチ `claude/v0.124-super-transform-dark-pulse`）。2026-10-31 に fetch し、リモートの `main` が
  `84bf94f013238472c34687533f8aec3018797cc9` のままで、この基点の祖先であること（後続の差分がない）、リモートの v0.124 のブランチが基点と同じこと、作業ツリーに利用者の `.claude/` のほかの変更がない
  ことを確かめました。`main` から作業ブランチ `claude/v0.125-wigglytuff-helping-hand` を作り、基点まで早送りしました（実際の開始点は `e165fe0`。取り込みのコミットは要らない）。`.claude/` は
  コミットに入れていません。
- 採用した kyuura は `134a664c6adf67d5604148a31b58e1a7d26d4d6d`（ブランチ `claude/eloquent-lamport-5xyv5r` の固定コミット。親は不足の研究 `6681d5c`）。旧固定元は
  `b9e7cff6d2b2c6b4539ec45e61bf453879adab3a`（調べた時点の kyuura `main` と同じ）。データは固定したコミットを `git show` で読み、ブランチの今の値には追いません。kyuura は変えていません
  （変更・マージ・push をしていない）。
- 参照した kyuura の文書: `docs/wigglytuff-unbounded-shortage-research.md`・`docs/engine-handover-after-v0.124.md` と、固定コミットのサイドカー（`data/sidecar/rulings.json`・
  `latest_descriptions.json`・`card_checks.json`）・台帳（`data/curation/card_corrections.json`）の各レコード。kyuura の登録表の写しは v0.113 のままなので、`engine_status` を今のエンジンの登録の
  正本にしていません。
- ルールの基準は公式ルール 2000.02.14 版。エンジン自身は新しいカードの画像・外部照合・ガイドブックのキャプチャ・OCR・読み直しをしていません。kyuura が 2026-10-31 に読んだ原典
  （『オフィシャルブック2000』p.226 ほか。PDF 228 ほか）は kyuura の記録として再利用し、読んだ主体（kyuura）・日付・根拠の種類をそのまま持ちます。
- 公開の固定デッキ・過去の版の比べ用の参照データは変えていません。`CLAUDE.md` は 39 行のままです。

## 2. 写しの元・研究の基準の移行（b9e7cff → 134a664）

この章は、カードの登録と処理の変更を加えない移行だけのコミットの記録です（プクリンはこのコミットでは写しに入れていない。対応数は 1,360 枚のまま。版は 0.124.0 のまま）。

### 2.1 kyuura の差分と移行の連鎖

- `b9e7cff` → `134a664` の `data/cards.json` は、ファイルのバイト列が同じです（1,377 件の全欄が同じ。新しい訂正はない）。既存の 1,360 枚の値は同じです。研究の記録が意味を変えたかは、データの
  一致とは別に 2.4 節で確かめました。
- 台帳（`data/curation/card_corrections.json`）で変わったのは、プクリン ES1-027 のふくらむの文面の候補（`held_illegible_print`）に `later_notes`（p.226 を読んだが、印刷の漢字 1 字は図版でも読めない）
  が加わったことだけです。訂正 43 件・候補の状態は同じで、エンジンも候補を訂正として扱いません。
- 段 v0.125（`b9e7cff` → `134a664`）を `scripts/extract_kyuura_cards.py` の `KYUURA_MIGRATIONS` の末尾に加えました（連鎖は ecb2d69 → 7d3f4ca → 73a1690 → e519b99 → 2fe0bc0 → 74b3ceb → b9e7cff →
  134a664）。v0.124 の段の `to` は写しの元の定数を指していたので、`V0_124_KYUURA_COMMIT`（b9e7cff）に固定してから写しの元を上げました（v0.114・v0.121・v0.123・v0.124 と同じ扱い）。過去の段の前・あと・
  文書・訂正・採用日・外部照合の日・当時の固定コミットは書き換えていません。
- 写しを作り直した結果（手で編集していない）: `source.commit`、`source_migrations`（段 v0.125。訂正 0 件）、`engine_user_corrections` の `source_commit` だけが変わりました。写しのカードの値・
  `kyuura_corrections` は変わっていません。
- v0.124 の移行の途中のコミット `6a74045` の写しの道具の潜在的な誤り（v0.124 の文書 14 章）は、v0.124 の登録のコミットで直してあります。今回は直した最後のコミット `e165fe0` を基点にし、途中の
  コミットにもどしたり、公開の履歴を書き換えたりしていません。

### 2.2 採用の記録

- 採用の記録の移行（`card_sources.json` の `data_migrations`）に 7 段目（2026-10-31）を加えました。採用したときのデータのコミット・記録した日・外部照合の確認日と照らしたコミット・当時の違いの値は
  書き換えていません。
- 研究の基準を上げて、登録済みのカードの `kyuura_records` に加わった id は、ゴローン（ES2-023）の CR-UNTIL-TAILS-NOT-CAPPED（裁定の `related_cards`。p.195 のれんぞくいわなげの解説を根拠の 1 つに
  挙げる）だけです（`tests/helpers.py` の `V0_125_KYUURA_RECORDS_ADDED`）。記録を読み直したのではなく、id の対応を直しました。

### 2.3 新しい一般の推論と既存の実装

研究の取り込みは、登録済みのカードの処理が正しいことの確かめではありません。登録済みのカードに関わる新しい記録が、既存の実装と合うかと、当てはまる範囲を確かめました。

| 記録 | 分類 | 既存の実装との関係 |
|---|---|---|
| CR-UNTIL-TAILS-NOT-CAPPED | SUPPORTED | 「うら」が出るまでのコインを資源の数で打ち切らない。登録済みのれんぞくいしなげ・れんぞくいわなげ（`CoinsUntilTailsDamage`。v0.64）・ニャースのまるもうけ（`CoinsUntilTailsDraw`。v0.118。山札の枚数で投げるのをやめない）は、上限なく投げる（打ち切る処理はない）。合う |
| GR-2000-P312-DECK-HAND-DISCARD の注記 | （条項の注記） | p.312 の「引けるだけ」は引く場面の文。エンジンの `min(H, D)` のまとめ方（`programs.draw_classes`）は引く処理の先読みだけに使い、トラッシュ・手札にもどす処理に使っていない。合う |
| GR-2000-P323-ATTACK-FAILURE の注記 | （条項の注記） | 転記の文と画像が同じことを kyuura が確かめただけ。処理は変わらない |
| CR-MOUNTAIN-CRUSH-PROCEDURE・CR-THOUGHT-WAVE-MACHINE-PROCEDURE・CR-DRY-UP-PROCEDURE・CR-DESTRUCTIVE-FIRE-TEXT | CONFIRMED | 登録していない 4 枚（7 章）の裁定。エンジンの処理に当てはめていない |

- 既存の止め方（HC6・FC1 など。UQ-STATED-COUNT-SHORT）は、今回の研究で解決済みにしていません。UQ-STATED-COUNT-SHORT の論点は問い・分類が同じで、事例が加わっただけです。

### 2.4 研究の対応表

- `research_commit`・`card_data_commit` を `134a664` に、`research_branch` を `claude/eloquent-lamport-5xyv5r` にしました。
- kyuura の記録の増減: 最新の説明 48 → 52（LD-ES1-027-ATK0・LD-ES1-027-PWR0・LD-ES2-005-ATK0・LD-QSG-055-ATK0）、照合 85 → 88（CC-ES1-027-P226・CC-ES2-005-P82・CC-QSG-055-P82）、裁定 337 → 345
  （CONFIRMED 6・SUPPORTED 2）、論点 88 → 90（UQ-HELPING-HAND-CHOICE・UQ-DESTRUCTIVE-FIRE-FAILURE）、一般条項 41 のまま（注記 2 件）。既存の 4 論点（UQ-CARD-USE-WITHOUT-TARGET・
  UQ-NON-ATTACK-DAMAGE-MODIFIERS・UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY・UQ-STATED-COUNT-SHORT）には事例と日付つきの注記が加わっただけで、問い・分類は変わっていません。kyuura の論点の数は、エンジンの
  停止コード 301・未解決の裁定 302 とは別の数で、数を合わせていません。研究の取り込みは論点の解決ではありません（2 件とも UNRESOLVED）。
- 新しい事例 11 件（論点・カード・対象の組。kyuura の同じ対象の事例は 1 つの組。はかいのほのおは 5 つ、［てだすけ］の選ぶ問いは 2 つ）を `kyuura_cases_without_engine_ruling` に結びました。移行の段では
  どのカードも登録していないので、どれも `unregistered` です。

| 論点 | 事例のカード・対象 |
|---|---|
| UQ-HELPING-HAND-CHOICE（新） | ES1-027 power/0 |
| UQ-DESTRUCTIVE-FIRE-FAILURE（新） | neo4-082 attack/1 |
| UQ-CARD-USE-WITHOUT-TARGET | ES1-027 power/0・neo4-108 trainer |
| UQ-NON-ATTACK-DAMAGE-MODIFIERS | ES1-027 attack/0 |
| UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY | neo4-082 attack/1 |
| UQ-STATED-COUNT-SHORT | neo4-082 attack/0・attack/1、neo4-108 trainer、ES2-005 attack/0、QSG-055 attack/0 |

- 4 つの最新の説明は「登録のない kyuura の最新の説明」（`kyuura_records_not_registered`）に、3 つの照合の記録は `card_checks.not_in_engine` に挙げました（プクリンを登録したら移す）。ファイヤー
  2 枚に LD- が来たことを理由に、そのカードを登録していません。
- `scripts/check_research_links.py`・`scripts/check_card_sources.py`・`scripts/extract_kyuura_cards.py --check` は、移行の段の木でどれも一致しました（採用の記録 1,273 件）。
