# v0.123: 名前の訂正の移行とウィンディ 3 枚

kyuura の研究（v0.122 のあとの名前・文面とトレーナーの手順の調査）を採用する移行を、カードの登録とは別の段にしました（2 章）。その上で、名前が確定したウィンディ系の 3 枚・ワザ 5 を
登録します（3 章以降）。前の下調べの 8 枚のうち、ほかの 5 枚とプクリンは対象外です（6 章）。

## 1. 開始点と範囲

- エンジンの基点は `e080c9e34989fc94ad4add1e8e579738b237fd6f`（v0.122、ブランチ `claude/v0.122-unown-fossil-retreat-reactions`）。2026-10-31 に fetch し、リモートの `main` は `8a597f2`
  （基点の祖先）、作業ツリーは利用者の `.claude/` のほかに変更がないことを確かめました。`main` から作業ブランチ `claude/v0.123-arcanine-name-migration` を作り、基点まで早送りしました
  （後続の差分はない。実際の開始点は基点と同じ）。
- 採用した kyuura は `74b3ceb883dd815495d13b9987433fb14b36e44d`（ブランチ `claude/v0122-names-text-trainer-procedures`。親 `aceb98b`、その前に `1634d6b`。基点 `2fe0bc0`）。kyuura の `main` は
  `73a1690` のままで、この研究のブランチは取り込まれていません。データは固定したコミットを `git show` で読み、ブランチ名の今の値には追いません。kyuura は変えていません。
- 参照した kyuura の文書: `docs/v0122-names-text-procedures-research.md`・`docs/engine-handover-after-v0.122.md`（74b3ceb）。kyuura の登録表の写しは v0.113 のままなので、`engine_status` を
  今のエンジンの登録の正本にしていません。
- ルールの基準は公式ルール 2000.02.14 版。新しいカードの画像・外部のサイト・ガイドブックは確かめていません。kyuura が確かめた画像（IMG-）・裁定（CR-）・既存の転記は kyuura の記録として
  再利用し、エンジン自身の原典の確認に数えていません。
- 公開の固定デッキ・過去の版の比べ用の参照データは変えていません。

## 2. 写しの元・研究の基準の移行（2fe0bc0 → 74b3ceb）

この章は、カードの登録を加えない移行だけのコミットの記録です（3 枚はこのコミットでは写しに入れていない。対応数は 1,355 枚のまま。版は 0.122.0 のまま）。

### 2.1 kyuura の差分と移行の連鎖

- `2fe0bc0` → `74b3ceb` の `data/cards.json` を全 1,377 件で比べました（形式・カードの外の欄・id の並びは同じ）。値が変わったのは、写しの組の登録済みの 2 枚だけです。

| id | 欄 | 前（2fe0bc0） | あと（74b3ceb） | kyuura の記録 |
|---|---|---|---|---|
| PMCG1-019 | `name.ja` | ウインディ | ウィンディ | 訂正 FIX-PMCG1-019-NAME-JA・画像の照合 IMG-PMCG1-019 |
| PMCG6-034 | `name.ja` | カツラのウインディ | カツラのウィンディ | 訂正 FIX-PMCG6-034-NAME-JA・画像の照合 IMG-PMCG6-034 |

- 同じ 2 枚の `notes`・`corrections`（写すだけの欄）も変わりました。エンジンが処理に使う欄（`FIELDS_USED_BY_ENGINE`）で変わったのは `name.ja` だけです。ワザ・特殊能力の文面は同じで、
  PMCG1-019 のかえんほうしゃの採用元（RUL-ENERGY-DISCARD-ATTACKS）も変えていません。ほかの 1,375 枚（写しの 1,353 枚をふくむ）と、3 章で登録する 3 枚（GD5-007・IP2-032・PR1-016）の値は同じです。
- 段 v0.123（`2fe0bc0` → `74b3ceb`）を `scripts/extract_kyuura_cards.py` の `KYUURA_MIGRATIONS` に加えました（連鎖は ecb2d69 → 7d3f4ca → 73a1690 → e519b99 → 2fe0bc0 → 74b3ceb）。v0.121 の段の
  `to` は写しの元の定数を指していたので、`V0_121_KYUURA_COMMIT`（2fe0bc0）に固定してから写しの元を上げました（v0.114・v0.121 と同じ扱い）。過去の段の前・あと・文書・訂正は書き換えていません。
  各段の `git show` に要るコミットは、kyuura の clone の履歴にあります。
- 写しを作り直した結果（手で編集していない）: 2 枚の `name`・`notes`・`corrections`、`source.commit`、`source_migrations`（段 v0.123 と、その訂正 2 件）、`kyuura_corrections`（2 件）、
  `engine_user_corrections` の `source_commit` だけが変わりました。

### 2.2 生成の値の誤り（`generated_value_error`）

2 件の訂正の根拠は kyuura のカードの画像の照合（`card_image_check`）、種類は `generated_value_error` です。kyuura は拡張パックのポケモンの名前を、英語版のデータの名前と図鑑番号から種の名前
（「ウインディ」）で生成していて、印刷（小さい「ィ」）と違っていました。v0.122 までの写しの道具の `CORRECTION_KINDS` はこの種類を扱わないので、次のとおり狭く受け付けました。

- 受け付けるのは、根拠がカードの画像の照合で、欄が `GENERATED_VALUE_FIELDS`（`name.ja` だけ）にあり、前の値が文字列（欠けを埋める訂正ではない）で、前とあとが違う訂正だけ
  （`generated_value_problems`）。種類を `transcription_error` に書きかえていません。未知の種類を一律に受け付けていません（台帳の種類と違う・扱えない種類として止める）。
- ほかは今までの画像による訂正と同じ確かめです: 台帳の記録（id・カード・欄・前・後・根拠・種類）、カードの記録の `corrections`、段の前のコミットの値が `before`・段のあとと写しの元の値が
  `after`、画像の照合の記録（カード・種類・照合した者・照合した日・`corrections`・`print_values`・カードの識別）、画像の URL・sha256・取得日が写しの記録の `evidence` と同じ、kyuura が画像を見た・
  エンジンは見ていない、CC-・LD-・修正のコミットを書かない、段の前の台帳にない、段ごとの写す欄の比べ。
- IMG-PMCG1-019 は 2 つのサイト（pcg-search.com・なぞのばしょ）の画像ですが、kyuura の記録のとおり、同じ撮影・スキャンに由来するかが分からないので独立した 2 枚の照合に数えていません。
- 既存の修正・`ENGINE_USER_CORRECTIONS`（PR1-069 の名前）・`FIELDS_USED_BY_ENGINE` の扱いは変えていません。

### 2.3 採用の記録

- 採用の記録の移行（`card_sources.json` の `data_migrations`）に 5 段目（2026-10-31）を加えました。採用したときのデータのコミット（ecb2d69・7d3f4ca・73a1690・e519b99・2fe0bc0）・記録した日・
  外部照合の確認日と照らしたコミット・当時の違いの値は書き換えていません（採用し直した・照合し直したことにしていない）。
- PMCG1-019・PMCG6-034 の `name_ja` を写しの名前にそろえました。2026-10-15 の pcg-search.com との照合の違い（kyuura の値「ウインディ」「カツラのウインディ」。ecb2d69 と照らした）は当時のまま
  残し、`scripts/check_card_sources.py` の既存の仕組み（移行の前のコミットと照らした記録の、訂正の欄の値は訂正の前の値と比べる）で受け付けます。今の写しの元と照らしたことにすると、
  古い値は受け付けません。
- 2 枚の論点「どちらが印刷の表記か」は、問いを残したまま、日付つきで解決の結果を追記しました（kyuura の FIX・IMG。kyuura が 2026-10-30 に画像を見た。この照合の時点では、エンジンも kyuura も
  画像を読んでいなかった。エンジンは今回も画像を見ていない）。`affects_behavior` は false のままです（写しの名前が印刷どおりになり、違いは写しに残っていない）。data-provenance の v0.30・
  v0.31 の報告事項の 3 にも同じ追記をしました。
- `kyuura_records`: 研究の基準のコミットで、登録済みの 17 枚を新しい記録が指すようになったので、id の対応を直しました（記録を読み直したのではない）。

| 記録 | カード |
|---|---|
| CR-ARCANINE-PRINTED-NAMES | PMCG1-019・PMCG6-034・neo4-021（やさしいウインディ。`related_cards`） |
| UQ-BILINGUAL-NAME-GLOSS | PMCG2-012・SI-013（ナッシー）・neo1-090（スロットゲーム）・PMCG6-082（カツラのクイズ その3） |
| UQ-MIND-GAMES-TRAINER-STEP | PMCG1-091・PMCG3-046・PMCG5-087・PMCG5-094・neo1-085・neo1-088・neo1-092 |
| UQ-SWAP-PLEASE-OWNERSHIP | PMCG5-087 |
| UQ-FLASH-FACE-UP-DECK | PMCG1-082・ES3-035・neo4-112 |

### 2.4 研究の基準の移行

研究の対応表（`research_links.json`）の `research_commit`・`card_data_commit` を 74b3ceb に、`research_branch` を `claude/v0122-names-text-trainer-procedures` にしました（`engine_import_id`
`ENGINE-46A3E2E` は変えていない）。`2fe0bc0` → `74b3ceb` の研究の記録の差分:

| 区分 | 変化 |
|---|---|
| 裁定（315 → 320） | CR-ARCANINE-PRINTED-NAMES（CONFIRMED）・CR-MIND-GAMES-SCOPE（CONFIRMED）・CR-FLASH-PROCEDURE（CONFIRMED）・CR-SWAP-PLEASE-PROCEDURE（CONFIRMED）・CR-SWAP-PLEASE-USE-CONDITION（SUPPORTED） |
| 論点（74 → 79） | UQ-BILINGUAL-NAME-GLOSS・UQ-MIND-GAMES-OPTIONAL・UQ-MIND-GAMES-TRAINER-STEP・UQ-FLASH-FACE-UP-DECK・UQ-SWAP-PLEASE-OWNERSHIP。既存の UQ-STATED-COUNT-SHORT（ES2-035）・UQ-CHAOS-GYM-BORROWED-TURN（PR1-027）に事例が加わった |
| 最新の説明・書籍の照合・条項 | 変わらない（47・84・35） |

- kyuura の論点の数 79 は、エンジンの停止コード 292・未解決の裁定 293 とは別の数で、そろえていません。v0.122 の 8 つの停止コードは、kyuura のこの調査の対象外です（解決したことにしていない）。
- 新しい事例 25 件を `kyuura_cases_without_engine_ruling` に結びました。新しい停止コード・コードのない問いは加えていません。
  - 事例のカードを登録していない 10 件は `unregistered`（ナッシー[Exeggutor] PR1-075・PR1-077、とりかえっこプリーズ PR1-027、フラッシュ ES2-035、ヤドキング neo1-049 の［ちえくらべ］）。
  - 登録したカードの事例で、その場面が登録していない別のカードがあるときだけ起こる 15 件に、新しい扱い `requires_unregistered` を加えました（ナッシー・スロットゲーム・カツラのクイズ その3 は
    ナッシー[Exeggutor]、ポケモン再転送・ポケモン図鑑 HANDY505・ラジオとうはフラッシュか［ちえくらべ］、ピッピ人形・なにかの化石・錯乱ジム・リムーブ禁止ジム・マダツボミのとう・
    きあいのハチマキ・超エネルギー回収は［ちえくらべ］、錯乱ジムの交換したカードはとりかえっこプリーズ）。`scripts/check_research_links.py` は、挙げたカードがどれも登録されておらず、同じ論点の
    事例のカードで、事例のカードそのものではなく、事例の対象は登録されていることを確かめます。登録していないカードはデッキに入れられない（`deck_problems`）ので、その場面は起こりません。
    答えを決めたのではありません。
- CR-MIND-GAMES-SCOPE は［ちえくらべ］の適用の範囲を確かめたもので、使うかの選択・トレーナーを使う手順のどこで投げるかは論点のままです（6 章）。

### 2.5 名前と、意図した表示の差

- 移行のあと、写しの名前は印刷どおりです: 「ウィンディ」は PMCG1-019（3 章で IP2-032・PR1-016 も）、「カツラのウィンディ」は PMCG6-034（3 章で GD5-007 も）。`deck.SAME_NAME_SPELLINGS` に
  ウインディの読み替えを加えていません。全角・小文字・括弧・持ち主の名前を除く一般の正規化もしていません。
- やさしいウインディ（neo4-021）は、今回 kyuura も画像を確かめていない別の名前です。部分文字列の置きかえで「やさしいウィンディ」にしていません（写しの値・過去の記録も変えていない）。
- カツラのクイズの名前の候補は、新しい名前を別名として足すのではなく、2 枚の名前が置きかわります（509 のまま。旧名は候補に残らない）。名前を表示する出力（ログ・観測・クイズの候補）に、
  2 枚の名前の違いが出ることがあります（意図した差。前の版との比べは 13 章）。

### 2.6 移行の確かめ

移行のコミットでは、写し・採用・研究の 3 つの検査と、移行に関係するテスト（`tests/test_arcanine_name_migration_v0_123.py` の移行の 15 件と、写しの元・研究の基準・論点の数・訂正の一覧を固定値に
持つ既存のモジュール）を走らせました。全体のテストは最後の 1 回です（13 章）。
