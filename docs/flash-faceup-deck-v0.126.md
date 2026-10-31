# v0.126: フラッシュと表向きの山札

kyuura の研究（ちえくらべ・フラッシュ・とりかえっこプリーズの調査）を採用する移行を、カードの登録とは別の段にしました（2 章）。その上で、フラッシュ（拡張シート第2弾赤版。ES2-035）の
トレーナー 1 枚を登録します（3 章以降）。カードの向き・プレイヤーが知る情報・いま公開されている範囲を分け、確定した通常の経路を動かし、未解決の操作だけを明示的に止めます。

## 1. 開始点と範囲

- エンジンの基点は `19c22051d10ec2a7610e7c7641b2c6053bd5c3f1`（v0.125 の最後のコミット。ブランチ `claude/v0.125-wigglytuff-helping-hand`）。2026-10-31 に fetch し、リモートの `main` が
  `84bf94f013238472c34687533f8aec3018797cc9` のままで、この基点の祖先であること（`main` に後続の差分がない）、作業ツリーに利用者の `.claude/` のほかの変更がないことを確かめました。`main` から作業ブランチ
  `claude/v0.126-flash-faceup-deck` を作り、基点まで早送りしました（実際の開始点は `19c2205`。取り込みのコミットは要らない）。`.claude/` はコミットに入れていません。
- 採用した kyuura は `57d01f45cfb8b086d03dc0525b329cf6adeff69b`（ブランチ `claude/trainer-reaction-faceup-deck-ownership-research` の固定コミット。親は検査 `645f0a8`、その親はデータ `169cdd3`。
  基点は `134a664`）。旧固定元は `134a664c6adf67d5604148a31b58e1a7d26d4d6d`。調べた時点の kyuura `main` は `b9e7cff` で、この研究は取り込まれていません。固定したコミットを `git show` で読み、`main` への
  取り込みを待たず、ブランチの今の値にも追いません。kyuura は変えていません（変更・マージ・push をしていない）。
- 参照した kyuura の文書: `docs/trainer-reaction-faceup-ownership-research.md`・`docs/engine-handover-trainer-procedures.md` と、固定コミットのサイドカー（`data/sidecar/rulings.json`・
  `latest_descriptions.json`・`card_checks.json`）・台帳（`data/curation/card_corrections.json`・`card_image_checks.json`）の各レコード。kyuura の登録表の写しは v0.113 のままなので、`engine_status` を今の
  エンジンの登録の正本にしていません。
- ルールの基準は公式ルール 2000.02.14 版。エンジン自身は新しいカードの画像・外部照合・ガイドブックのキャプチャ・OCR・読み直しをしていません。kyuura が 2026-10-31 に読んだ原典
  （『オフィシャルブック2000』p.270・p.228 ほか）とカードの画像（IMG-ES2-035・IMG-PR1-027）は kyuura の記録として再利用し、読んだ主体（kyuura）・日付・根拠の種類をそのまま持ちます。
- 公開の固定デッキ・過去の版の比べ用の参照データは変えていません。`CLAUDE.md` は 39 行のままです。

## 2. 写しの元・研究の基準の移行（134a664 → 57d01f4）

この章は、カードの登録と処理の変更を加えない移行だけのコミットの記録です（フラッシュはこのコミットでは写しに入れていない。対応数は 1,361 枚のまま。版は 0.125.0 のまま）。

### 2.1 kyuura の差分と移行の連鎖

- `134a664` → `57d01f4` の `data/cards.json` 全 1,377 件を欄ごとに比べ、値が変わったのは写しの外（未登録）のとりかえっこプリーズ PR1-027 の `trainer.text.ja` の読点 1 つ（「…ある時だけ使える)」→
  「…ある時だけ、使える)」）と、同じカードの `notes`・`corrections` だけでした。登録済みの 1,361 枚と、この版で登録するフラッシュ ES2-035 の値は同じです（ES2-035 は別に、全欄が同じことを確かめた）。
  名前の末尾の「！」（印刷にあり kyuura にない）は kyuura が直していない報告事項で、エンジンも直していません。
- 訂正 FIX-PR1-027-TEXT-JA（`transcription_error`・根拠 `card_image_check`・画像の照合 IMG-PR1-027。kyuura が pcg-search.com の画像と『オフィシャルブック2000』p.293 の図版で読点を確かめた）を
  `KYUURA_CORRECTIONS`（段 v0.126）に挙げ、台帳・カードの記録・画像の照合の記録の値（前・あと・根拠・画像の sha256）と照らしました。画像を見たのは kyuura で、エンジンは画像を見ていません
  （`engine_saw_image: false`）。括弧・句読点を一般的に正規化して一致させてはいません（前とあとの違いは読点 1 つだけ）。
- 段 v0.126（`134a664` → `57d01f4`）を `scripts/extract_kyuura_cards.py` の `KYUURA_MIGRATIONS` の末尾に加えました（連鎖は ecb2d69 → 7d3f4ca → 73a1690 → e519b99 → 2fe0bc0 → 74b3ceb → b9e7cff →
  134a664 → 57d01f4）。v0.125 の段の `to` は写しの元の定数を指していたので、`V0_125_KYUURA_COMMIT`（134a664）に固定してから写しの元を上げました。過去の段の前・あと・文書・訂正・採用日・
  外部照合の日・当時の固定コミットは書き換えていません。
- 写しを作り直した結果（手で編集していない）: `source.commit`、`source_migrations`（段 v0.126。訂正 1 件）、`kyuura_corrections`（FIX-PR1-027-TEXT-JA が加わった）、`engine_user_corrections` の
  `source_commit` だけが変わりました。写しのカードの値は変わっていません（PR1-027 は写しに入れない）。

### 2.2 採用の記録

- 採用の記録の移行（`card_sources.json` の `data_migrations`）に 8 段目（2026-10-31）を加えました。採用したときのデータのコミット・記録した日・外部照合の確認日と照らしたコミット・当時の違いの値は
  書き換えていません。
- 研究の基準を上げて、登録済みのカードの `kyuura_records` に加わった id は次の 4 件です（`tests/helpers.py` の `V0_126_KYUURA_RECORDS_ADDED`）。記録を読み直したのではなく、id の対応を直しました。

| カード | 加わった記録 | 結び付き |
|---|---|---|
| サカキのニャース PMCG6-068 | CR-FLASH-TOP-CARD-SEEN | 裁定の `related_cards`（p.228 のてつだうふりの解説が根拠） |
| 錯乱ジム PMCG5-087 | CR-CHAOS-GYM-COIN-BEFORE-CONDITIONS | 裁定の `cards` |
| neo1-085・neo1-088 | CR-MIND-GAMES-STADIUM-TOOL | 裁定の `related_cards`（ちえくらべの対象になるスタジアム・どうぐの例） |

### 2.3 新しい記録と既存の実装

研究の取り込みは、登録済みのカードの処理が正しいことの確かめではありません。新しい記録を、フラッシュの記録と、ちえくらべ・交換の記録に分けて、既存の実装と合うかと当てはまる範囲を確かめました。

| 記録 | 分類 | 対象 | 既存の実装との関係 |
|---|---|---|---|
| CR-FLASH-TOP-CARD-SEEN | CONFIRMED | フラッシュ ES2-035（related: サカキのニャース PMCG6-068） | 移行の段ではフラッシュを登録していないので、表向きの山札は起こらない。登録（3 章以降）で、表向きのいちばん上のカードを双方の観測に出し、てつだうふりの代表経路を確かめる |
| CR-FLASH-PROCEDURE | CONFIRMED（既存。134a664 から同じ） | フラッシュ | 同上 |
| CR-CHAOS-GYM-COIN-BEFORE-CONDITIONS | SUPPORTED | 錯乱ジム PMCG5-087 | v0.57 の錯乱ジムのコインは、トレーナーカードの使うための条件の前（`engine._chaos_tails`）。「うら」で相手がかわりに使うときは、相手が条件を満たす。合う（今のコードの順番を、この裁定の根拠にはしていない） |
| CR-MIND-GAMES-STADIUM-TOOL | CONFIRMED | ヤドキング neo1-049（related: neo1-085・neo1-088） | ヤドキングは登録していない（この版でも登録しない）。処理に当てはめていない |
| CR-SWAP-PLEASE-USE-IN-GAME・CR-SWAP-PLEASE-REAL-TRADE-SEPARATE | CONFIRMED・SUPPORTED | とりかえっこプリーズ PR1-027 | 登録していない（この版でも登録しない）。持ち主（UQ-SWAP-PLEASE-OWNERSHIP）の一般の基盤は加えていない |
| CR-SWAP-PLEASE-PROCEDURE・CR-SWAP-PLEASE-USE-CONDITION | SUPPORTED（既存） | PR1-027 | 根拠の引用が訂正のあとの文面（読点）に合わせて直り、注記が加わった。結論・分類は同じ |
| GR-2000-P310-TRAINERS の注記 | （条項の注記） | — | p.310 の手順 2（名前を伝える）を kyuura が読んだ注記。確かめ方の値（エンジンの記録の取り込み）は同じ。処理は変わらない |

- 4 つの論点（UQ-MIND-GAMES-OPTIONAL・UQ-MIND-GAMES-TRAINER-STEP・UQ-FLASH-FACE-UP-DECK・UQ-SWAP-PLEASE-OWNERSHIP）は、出典・監査・注記が加わっただけで、問い・事例・分類（UNRESOLVED）は
  同じです。どれも未解決のままとし、研究の指摘をエンジンの新しい公式裁定に置き換えていません。

### 2.4 研究の対応表

- `research_commit`・`card_data_commit` を `57d01f4` に、`research_branch` を `claude/trainer-reaction-faceup-deck-ownership-research` にしました。
- kyuura の記録の増減: 最新の説明 52 → 54（LD-ES2-035-TRAINER・LD-PR1-027-TRAINER）、照合 88 → 90（CC-ES2-035-P270・CC-PR1-027-P293）、裁定 345 → 350（CONFIRMED 3・SUPPORTED 2）、
  論点 90 → 90、一般条項 41 のまま（注記 1 件）。kyuura の論点の数は、エンジンの停止コード・未解決の裁定とは別の数で、数を合わせていません。
- 2 つのトレーナーの最新の説明は、どちらもこの段では登録していないので、新しい欄 `latest_descriptions.trainer_records_not_registered` に挙げました（これまでのトレーナーの最新の説明は登録した
  ものだけで、`registered_trainers` に結んでいた）。`scripts/check_research_links.py` は、2 つの欄が重ならず、合わせて kyuura のトレーナーの最新の説明のすべてと同じこと、登録していない欄のカードが
  登録されていないことを確かめます。2 つの照合の記録は `card_checks.not_in_engine` に挙げました（照合の記録はエンジンの照合の記録ではないので、登録のあとも `not_in_engine`）。
- 論点の事例は増えていないので、`kyuura_cases_without_engine_ruling` の事例は変えていません。フラッシュの事例（UQ-FLASH-FACE-UP-DECK の ES2-035・UQ-STATED-COUNT-SHORT の ES2-035）は、この段では
  `unregistered`、ポケモン再転送 ES3-035・ポケモン図鑑 HANDY505 PMCG1-082・ラジオとう neo4-112 の事例は `requires_unregistered`（ES2-035・neo1-049）のままです。ちえくらべ・とりかえっこプリーズの事例は
  登録しないので、登録のあとも変えません。
- `scripts/check_research_links.py`・`scripts/check_card_sources.py`・`scripts/extract_kyuura_cards.py --check` は、移行の段の木でどれも一致しました（採用の記録 1,274 件）。
