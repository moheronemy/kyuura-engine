# v0.124: 変身の共通ルール・すごいへんしん・わるいはどう

kyuura の研究（すごいへんしん・わるいはどうの調査）を採用する移行を、処理の変更・カードの登録とは別の段にしました（2 章）。その上で、確かめられた変身の共通ルールを既存の
メタモン（化石の秘密。PMCG3-042）の［へんしん］にも当てはめ（3 章）、メタモン（拡張シート第2弾赤版。ES2-032）と GR団のミュウツー（PRN-041）の 2 枚（ワザ 1・特殊能力 2）を登録します
（4 章以降）。

## 1. 開始点と範囲

- エンジンの基点は `84bf94f013238472c34687533f8aec3018797cc9`（`main`。PR #21 で v0.123 を取り込んだマージ）。木は v0.123 の最後のコミット `25552b8ca6292232e51e188d2be66af36ef7bf55` と
  同じです。2026-10-31 に fetch し、リモートの `main` が `84bf94f` のままで後続の差分がないこと、作業ツリーは利用者の `.claude/` のほかに変更がないことを確かめ、`main` から作業ブランチ
  `claude/v0.124-super-transform-dark-pulse` を作りました（実際の開始点は `84bf94f`。古い `main` の `8a597f2` からの早送りは要らない）。`.claude/` はコミットに入れていません。
- 採用した kyuura は `b9e7cff6d2b2c6b4539ec45e61bf453879adab3a`（kyuura `main` の PR #6 のマージ）。木は研究の最後のコミット `9731354f7e5c6bca08c88bbe98f9449ae96ea7a7` と同じです（どちらも木
  `c548f29`）。旧固定元は `74b3ceb883dd815495d13b9987433fb14b36e44d`。データは固定したコミットを `git show` で読み、`main` の今の値には追いません。kyuura は変えていません（変更・マージ・push
  をしていない）。
- 参照した kyuura の文書: `docs/ditto-transform-gr-mewtwo-research.md`・`docs/engine-handover-after-v0.123.md` と、固定コミットのサイドカー（`data/sidecar/rulings.json`・
  `latest_descriptions.json`・`card_checks.json`）の各レコード。kyuura の登録表の写しは v0.113 のままなので、`engine_status` を今のエンジンの登録の正本にしていません。
- ルールの基準は公式ルール 2000.02.14 版。エンジン自身は新しい画像の確認・外部照合・ガイドブックのキャプチャ・OCR・読み直しをしていません。kyuura が 2026-10-31 に読んだ原典
  （『オフィシャルブック2000』p.239・p.324・p.325。PDF 241・326・327）とカードの画像 2 枚（IMG-ES2-032・IMG-PRN-041）は kyuura の記録として再利用し、読んだ主体（kyuura）・日付・根拠の種類を
  そのまま持ちます。p.260 のポケモン回収の解説・p.72 のデッキの紹介・p.47 の囲み・『トレーナーズ』Vol.5 の要約は kyuura でも既存の転記・既存の読み取りの再利用で、新しい照合に数えていません。
- 公開の固定デッキ・過去の版の比べ用の参照データは変えていません。`CLAUDE.md` は 39 行のままです。

## 2. 写しの元・研究の基準の移行（74b3ceb → b9e7cff）

この章は、カードの登録と処理の変更を加えない移行だけのコミットの記録です（2 枚はこのコミットでは写しに入れていない。対応数は 1,358 枚のまま。版は 0.123.0 のまま）。

### 2.1 kyuura の差分と移行の連鎖

- `74b3ceb` → `b9e7cff` の `data/cards.json` を全 1,377 件で比べました（形式・カードの外の欄・id の並びは同じ）。値が変わったのは、写しの外（未登録）の 1 枚だけです。

| id | 欄 | 前（74b3ceb） | あと（b9e7cff） | kyuura の記録 |
|---|---|---|---|---|
| ES2-032 | `pokemon.powers[0].text.ja` | 「…この「すごいへんしん」の**カ**は使えず…」（片仮名） | 「…この「すごいへんしん」の**力**は使えず…」 | 訂正 FIX-ES2-032-POWER0-TEXT-JA・画像の照合 IMG-ES2-032 |

- 同じカードの `notes`・`corrections`（写すだけの欄）も変わりました。登録済みの 1,358 枚をふくむほかの 1,376 枚の値は同じです（GR団のミュウツーの値も同じ。補足の欄の「公式大会では使うことが
  できません」は kyuura が記録しただけで `play_scope` は `standard` のまま）。括弧の全角・半角や句読点は整形していません（前とあとの違いは 1 字だけ）。
- 段 v0.124（`74b3ceb` → `b9e7cff`）を `scripts/extract_kyuura_cards.py` の `KYUURA_MIGRATIONS` に加えました（連鎖は ecb2d69 → 7d3f4ca → 73a1690 → e519b99 → 2fe0bc0 → 74b3ceb → b9e7cff）。
  v0.123 の段の `to` は写しの元の定数を指していたので、`V0_123_KYUURA_COMMIT`（74b3ceb）に固定してから写しの元を上げました（v0.114・v0.121・v0.123 と同じ扱い）。過去の段の前・あと・文書・
  訂正・採用日・外部照合の日・当時の固定コミットは書き換えていません。各段の `git show` に要るコミットは、kyuura の clone の履歴にあります。
- 写しを作り直した結果（手で編集していない）: `source.commit`、`source_migrations`（段 v0.124 と、その訂正 1 件）、`kyuura_corrections`（1 件）、`engine_user_corrections` の `source_commit` だけが
  変わりました。写しのカードの値は変わっていません（ES2-032 はまだ写しにない）。

### 2.2 訂正の受け付け（転記の誤り）

- 訂正 FIX-ES2-032-POWER0-TEXT-JA は、種類 `transcription_error`・根拠 `card_image_check`・画像の照合 IMG-ES2-032 です。今の種類と根拠のまま受け付けました（生成の値の誤り・公式エラッタ・
  最新の説明と混ぜない）。台帳の記録（id・カード・欄・前・後・根拠・種類）、カードの記録の `corrections`、段の前のコミットの値が `before`・段のあとと写しの元の値が `after`、画像の照合の記録
  （カード・照合した者・照合した日・`corrections`・`print_values`・カードの識別）、画像の URL・sha256・取得日、kyuura が画像を見た・エンジンは見ていない、段の前の台帳にないことを、今までの
  画像による訂正と同じ確かめで照らしています。写しの外のカードの訂正ですが、移行の段で台帳と照らして写しの `kyuura_corrections` に挙げました（4 章で登録するときに改めて照らす必要がない）。
- 同じ段で kyuura は、書籍 p.239 の図版と最新の説明を読んだ照合の記録 CC-ES2-032-P239 も作り、同じ欄（`pokemon.powers[0].text.ja`）を訂正のあとの値で照らしています。v0.123 までの写しの道具は、
  CC- が照らした欄を画像で直す訂正を「画像の確認を CC- の代わりにした」として受け付けませんでした。次の条件をすべて満たすときだけ、この確かめから外しました（`kyuura_correction_problems`）。
  - その欄を照らす CC- が、どれも段の前のコミットの照合の記録にない（同じ段で新しく作った記録）
  - どの CC- も、その欄を訂正のあとの値と同じ値で照らし、データの誤り（`data_error`）としていない
  条件を満たさなければ今までどおり止めます（たとえば訂正のあとの値を前の値に書きかえると、CC- の値と違うので止まる。テスト `SameStepCardCheckTest`）。訂正の根拠は画像の照合のままで、CC- を
  訂正の根拠・独立した 2 件目の照合に数えていません（kyuura も、図版の文字が小さく全文の読み比べに使っていないので、独立した 2 件に数えていない）。

### 2.3 採用の記録

- 採用の記録の移行（`card_sources.json` の `data_migrations`）に 6 段目（2026-10-31）を加えました。採用したときのデータのコミット・記録した日・外部照合の確認日と照らしたコミット・当時の違いの値は
  書き換えていません。
- 研究の基準を上げたので、登録済みの 21 枚の `kyuura_records` に、そのカードを指す新しい id を加えました（記録を読み直したのではなく、id の対応を直した。`tests/helpers.py` の
  `V0_124_KYUURA_RECORDS_ADDED`）。化石のメタモン（PMCG3-042）には裁定 7（CR-TRANSFORM-COPIES-TOP-CARD・CR-TRANSFORM-NAME-AND-KIND・CR-TRANSFORM-BABY-RULE・CR-TRANSFORM-KEEPS-OWN-STATE・
  CR-TRANSFORM-NOT-NEWLY-PLAYED・CR-TRANSFORM-FROZEN-DURING-ACTION・CR-TRANSFORM-REVERT-KNOCKOUT）と論点 5、ほかのカードには論点の事例・裁定の `related_cards` の id が加わりました。

### 2.4 研究の対応表

- `research_commit`・`card_data_commit` を `b9e7cff` に、`research_branch` を `main` にしました。
- kyuura の記録の増減: 一般条項 6（GR-2000-P324-TRANSFORM-DEFINITION・TOP-CARD・NAME-AND-KIND、GR-2000-P325-TRANSFORM-OWN-STATE・NOT-NEW・DURING-ACTION）、裁定 17（CONFIRMED 12・SUPPORTED 5）、
  論点 9。既存の 3 論点（UQ-TRANSFORM-SCOPE・UQ-REACTIVE-SWITCH-DURING-ATTACK・UQ-SELF-EXCLUDING-POWER-COPIES）には日付つきの注記が加わっただけで、事例は変わっていません。kyuura の論点は
  79 → 88 です。エンジンの停止コード 292・未解決の裁定 293 とは別の数で、数を合わせていません。研究の取り込みは論点の解決ではありません（9 件とも UNRESOLVED）。
- 新しい事例 31 件を `kyuura_cases_without_engine_ruling` に結びました。移行の段では処理を変えていないので、エンジンの扱いは移行の段の実際の挙動です。

| 扱い | 件数 | 内容 |
|---|---:|---|
| `unregistered` | 9 | すごいへんしん（ES2-032）・わるいはどう（PRN-041）の事例 |
| `requires_unregistered` | 17 | 登録済みのカードの事例で、場面に ES2-032 が要るもの 12 件（ばけるキュウコン・なにかの化石・ピッピ人形・退化スプレー・エネエネ・かがくへんかガス・いあつ・無色2個／レインボーエネルギーなど）、PRN-041 が要るもの 5 件（どくのきり・みんなでばくはつ・だいばくはつ・ダークドレイン・くつろぐかおり） |
| `stop_codes` | 2 | ベイビィの姿の［へんしん］のメタモン（PMCG3-042）・やさしいほのお（neo4-021）。移行の段のエンジンは BX1（`UNRESOLVED_TRANSFORM_BABY`）で止める（`engine_issue_differs`） |
| `codeless_question` | 3 | 化石のメタモンで、移行の段のエンジンが止めていない 3 つの場面（下の表） |

| コードのない問い | 論点 | 移行の段のエンジンの挙動 |
|---|---|---|
| `transform_energy_color_list` | UQ-TRANSFORM-ENERGY-COLOR-LIST | v0.49 からの実装のまま、悪・鋼の記号も基本エネルギーで払う（8 色の読み） |
| `transform_revert_knockout_timing` | UQ-TRANSFORM-REVERT-KNOCKOUT-TIMING | ワザで相手の対戦ポケモンがきぜつしてもどったメタモンを、ワザのあとのきぜつの判定で同時にきぜつさせる |
| `transform_baby_and_basic_retreat` | UQ-TRANSFORM-BABY-AND-BASIC | でこぼこジムで、ベイビィの姿のメタモンのにげるを 1 個ぶん多くする |

  どれも「止めていない」ことの記録で、答えを決めたのではありません。3 章で止め方・処理を見直し、この表を直します。
- `requires_unregistered` の確かめ（v0.123）は、挙げたカードが同じ論点の事例のカードで登録していないことと、事例の対象が登録されていることを見ます。無色2個エネルギー（PMCG1-096）・
  レインボーエネルギー（PMCG4-065）の事例（対象 `card`）を結ぶため、特殊エネルギーの登録（`EnergyEntry`）もカードそのものの事例の登録した対象に数えるようにしました
  （`scripts/check_research_links.py` の `_registered_targets`。v0.123 まではワザ・特殊能力・トレーナーの登録だけを数えていた）。
- 最新の説明 LD-ES2-032-PWR0 は「登録のない kyuura の最新の説明」に、照合の記録 CC-ES2-032-P239 は `card_checks.not_in_engine` に挙げました（4 章で登録したら移す）。
