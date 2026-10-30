# v0.121: 手札からの登場とワザの使用条件

v0.121（版 0.121.0）は、先行修正 A0（「なきごえ」を受けたポケモンの特殊能力のダメージの内部エラー）、写しの元・研究の基準の移行（kyuura `e519b99` → `2fe0bc0`）と、相手の手札から
場へ出すワザ・眠ったまま使えるワザ・コインと期限つきの効果を使う 9 枚（ポケモン 7・トレーナー 2。ワザ 14）を、kyuura データの採用で登録する版です。

## 1. 開始点と範囲

- 開始点は確認済みの v0.120 の最後のコミット `8bb771f37aa4e2649f76e78c1075f3e3b6210781`（ブランチ `claude/v0.120-fossil-basic-virtual-attacks`。リモートにある）。作業を始めたとき
  （2026-10-30）に fetch し、リモートの `main` は `9e8ca5c1b9dad66afcf8cde8d534f51745d1cbac` のままで v0.120 の祖先でした（`main` に後続のコミットはない）。作業ブランチ
  `claude/v0.121-hand-bench-attack-conditions` を最新の `main` から作り、v0.120 まで早送りしました（マージのコミットはない。実際の開始点は `8bb771f`）。同じ名前のリモートのブランチにだけ
  プッシュします。作業の木の未追跡の `.claude/` はこの作業のものではないので、コミットしません。
- `main`・既定のブランチ・kyuura・公開の固定デッキ・過去版の比較用の参照データは変えていません。PR の作成・マージ、強制プッシュ、履歴の書き換えもしていません。
- ルールの基準は公式ルール 2000.02.14 版のままです（neo 期のカードにも同じ基準）。**今回はエンジンとして外部照合・カード画像・ガイドブックの読み直しをしていません**。kyuura が読んだ
  記録（画像の照合 `IMG-`・書籍の照合 `CC-`・最新の説明 `LD-`）は kyuura の記録として再利用し、エンジン自身の原典の確認には数えていません。英語版の文面・現代のルール・後年の裁定で
  日本語の不足を補っていません。

## 2. A0: 「なきごえ」を受けたポケモンの特殊能力のダメージ

### 2.1 再現（固定した v0.120）

- 盤面: ピカチュウ（IP1-040）がバトル場で「なきごえ」を使い、相手のバトル場のエレキッド（neo1-044）が効果を受ける。次の相手の番に、エレキッドが［わんぱくパンチ］（自分の番ごとに
  1 回。コインの「おもて」で相手の対戦ポケモンに 20 の特殊能力のダメージ。使ったら番は終わる）を宣言する。`build_test_state` で作った盤面から、通常の `UseAttack`・`UsePokemonPower` を
  実行した（`new_game` からの対戦ではない）。
- 固定した v0.120（`git archive 8bb771f` で展開した別の木・別のプロセス）では、宣言の確かめ（「おもて」のときのダメージを決められるか。`CoinDamageOpponentActiveThenEndTurn.damage_problem`）
  が `received_power_damage` の「到達しない場面」の `RuntimeError` になった。ヒトカゲ（ES1-013）・チコリータ（PF1-001）のなきごえでも同じ。
- 隣の例: 効果を受けていないベンチのエレキッドの［わんぱくパンチ］（ラッキーがなきごえを受けた）と、はたらく番が過ぎたあとの自分の番の［わんぱくパンチ］は、どちらの版でも 20 の
  ダメージを与える。

### 2.2 原因（エンジンの不具合と、裁定の不足を分ける）

1. **前提の誤り（エンジン）**: v0.76 は、なきごえを受けたポケモンが、はたらく番（受けたポケモンの持ち主の番）に、効果を与えたポケモンへ特殊能力のダメージを与える場面を「今の対応
   カードでは起こらない」（はんげき・わるいねぞう・ファイナルビームは相手のワザのダメージで、こっそりかみつくは進化で効果が消える）として内部エラーにした。v0.114 で登録したエレキッドの
   ［わんぱくパンチ］は自分の番に使える特殊能力のダメージで、この前提に入っていなかった。
2. **裁定の不足（研究上の未解決）**: なきごえの説明（「このワザを受けた相手は、…このカードにダメージを与える時、そのダメージが「-10」される」）は、ワザのダメージに限ると書かない。
   公式ルール p.321 の計算の順番はワザによるダメージの計算で、ワザ以外のダメージを変えるかを書かない。減らすかどうかで受けるダメージ（20 か 10）が変わる。

### 2.3 直し方

- 内部エラーを、未解決の停止 GN1（`UNRESOLVED_GROWL_NON_ATTACK_DAMAGE`）に変えました。`received_power_damage` は、受けるダメージを変える特殊能力を当てはめる前に、なきごえ
  （効果がはたらく番の終わりに消える型。「なきつく」の「このカードにワザを使う時」はワザだけを書くので当たらない）を受けたポケモンから効果を与えたポケモンへの 0 より大きい特殊能力の
  ダメージで止めます。呼ぶ側は状態を変える前に聞くので、［わんぱくパンチ］は宣言の前に止まり（コインを投げない。Z9・DB1 と同じ）、状態・乱数・ログは変わりません。
- 当てはまる登録: なきごえ・なきつくのうち `ReduceDamageToSelfNextOpponentTurn` の 5 つの書き方（ヒトカゲ ES1-013・QSG-007、ドードー ES1-028・QSG-041、パウワウ ES2-006・QSG-017、
  ピカチュウ IP1-040、チコリータ PF1-001、トゲピー PR1-065 の「-20」）。カラカラの「なきつく」（`ReducedDamageToSource`）は当たらない。
- 控えにいるこのカードへのワザのダメージは、今までどおり v0.34 の NK5（`UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET`）で止めます（別の問い。変えていない）。
- 直さなかったこと: `RuntimeError` を握りつぶす・特殊能力のダメージを黙って減らす（減らさない）ことはしていない。

### 2.4 記号

GN1・`UNRESOLVED_GROWL_NON_ATTACK_DAMAGE` は、基点の木とすべての参照（`git rev-list --all` の 231 コミット）の差分に現れない記号を選びました。研究の基準 `e519b99` の kyuura には対応する
記録がないので、A0 のコミットでは研究の対応表の `kyuura_disposition` を `not_in_kyuura` にしました（移行で kyuura の新しい論点に結ぶ。3 章）。

## 3. 写しの元・研究の基準の移行（e519b99 → 2fe0bc0）

この章は、カードの登録・挙動を変えない移行だけのコミットの記録です（9 枚はこのコミットでは写しに入れていない。ピカチュウ IP1-040 の処理に使う文面の出典だけを変えた。3.4 節）。

### 3.1 kyuura の差分

- 採用した kyuura は `2fe0bc042ce187d191843819262f8036abbb343d`（ブランチ `claude/neo2-fossil-type-cost-checks`。親 `7b03fd9`、その前に次の便のカードの文面と進化データの研究
  `c932625053f4cd4d784585f8b6144121499d85ed`。kyuura main には未取り込み）。kyuura の作業ツリー・履歴は変えていない（`git show` で読むだけ）。
- `e519b99` → `2fe0bc0` の `data/cards.json` を全 1,377 件で比べました（形式 3 のまま。カードの追加・削除・並びの変化はない。カードの外の欄も同じ）。値が変わったのは 13 枚だけで、
  エンジンの写し（1,333 枚）のカードとは重なりません（写しの 1,333 枚の値は同じ。写しの作り直しで `cards` に差はない）。

| 変わった欄（エンジンが使う欄） | カード | kyuura の訂正 |
|---|---|---|
| `trainer.text.ja`（「を、」「1枚」） | neo3-053 ボロのつりざお | FIX-neo3-053-TRAINER-TEXT-JA |
| `pokemon.rules_text.ja`（null → 「アンノーン」はデッキに4枚まで…） | neo2-027・neo2-028・neo2-030 アンノーン M・U・A | FIX-<id>-RULES-TEXT-JA |
| `pokemon.evolves_from`（null → 印刷の名前） | GD3-003（マチスのピカチュウ）・ES2-011・ES2-028・ES2-029・ES3-018（なにかの化石）・PRN-039（フシギダネ）・PRN-040（わるいフシギソウ）・PRN-045（オニスズメ） | FIX-<id>-EVOLVES-FROM |
| `pokemon.stage`（stage1 → basic） | PRN-030 カポエラー | FIX-PRN-030-STAGE |

- 同じ 13 枚の付随する欄（`corrections`・`notes`・`data_gaps`・`field_sources`）も変わりました。13 件の訂正はどれも根拠がカードの画像の照合（`card_image_check`。kyuura の
  `data/curation/card_image_checks.json` の `IMG-<id>`）で、画像を見たのは kyuura です（エンジンは見ていない）。kyuura の台帳 `data/curation/card_corrections.json` に 13 件が加わり、
  既存の訂正は変わっていません。
- `c932625` → `2fe0bc0` のカード本体の値の変更は 0 です（加わったのは化石 4 枚の画像の照合 IMG-neo2-014・IMG-neo2-018・IMG-neo2-032・IMG-neo2-035 と検査・文書）。カブト neo2-014・
  カブトプス neo2-018 は水タイプで闘を使い、オムナイト neo2-032・オムスター neo2-035 は闘タイプで水を使うことを kyuura が画像で確かめました（入れ違いではない。値は写しのまま。11 章）。

### 3.2 移行の連鎖

段 v0.121（`e519b99` → `2fe0bc0`）を `scripts/extract_kyuura_cards.py` の `KYUURA_MIGRATIONS` に加えました（連鎖は ecb2d69 → 7d3f4ca → 73a1690 → e519b99 → 2fe0bc0）。

- v0.114 の段の `to` は写しの元の定数 `KYUURA_COMMIT` を指していたので、`V0_114_KYUURA_COMMIT`（e519b99）に固定してから写しの元を上げました（v0.114 で v0.97 の段にした扱いと同じ）。
  v0.69・v0.97・v0.114 の段の前・あと・文書・修正は書き換えていません。
- この段に当てはめた修正は、写しの組のカードにはありません（13 件はどれも写しの外。移行のコミットの `source_migrations` の段 v0.121 の `corrections` は空）。ボロのつりざおは 4 章の
  登録のコミットで写しに入れ、その訂正 FIX-neo3-053-TRAINER-TEXT-JA を `KYUURA_CORRECTIONS`（段 v0.121）に加えます。残る 12 枚は、移行の件数を合わせるために写しに加えていません。
- 採用の記録の移行（`card_sources.json` の `data_migrations`）に 4 段目（2026-10-30）を加えました。採用したときのデータのコミット（ecb2d69・7d3f4ca・73a1690・e519b99）・記録した日・
  外部照合の確認日と照らしたコミット・`ENGINE_USER_CORRECTIONS`（PR1-069 の名前。kyuura はまだ直していない）は書き換えていません。
- 写しを作り直した結果（手で編集していない）: `cards`（1,333 枚）は v0.120 と同じで、変わったのは `source.commit`・`source_migrations`（段 v0.121）・`engine_user_corrections` の
  `source_commit` だけです。テストの写しの元の補助（`tests/helpers.py` の `with_card_data_commit_at`）に段を加えました。

### 3.3 研究の基準の移行

研究の対応表（`research_links.json`）の `research_commit`・`card_data_commit` を 2fe0bc0 に、`research_branch` を `claude/neo2-fossil-type-cost-checks` にしました（`engine_import_id`
`ENGINE-46A3E2E` は変えていない）。`e519b99` → `2fe0bc0` の研究の記録の差分:

| 区分 | 加わった記録 |
|---|---|
| 最新の説明（42 → 47） | LD-PR1-001-ATK0・LD-PR1-003-ATK0・LD-PR1-017-ATK0・LD-IP1-040-ATK0・LD-ES3-021-ATK1（新しい欄 `applies_to_print`: 図版で照合した `figure` は PR1-003・IP1-040、見出しの配布で当てはめた `heading_listing` は PR1-001・PR1-017。PR1-017 の配布の特定は推論） |
| 書籍の照合（81 → 84） | CC-PR1-003-P127・CC-IP1-040-P127・CC-ES3-021-P156（対応表の `card_checks.not_in_engine`。エンジンの照合の記録はない） |
| 裁定（308 → 315） | CR-PIKACHU-GROWL-LATEST（CONFIRMED）・CR-PIKACHU-GROWL-OPPONENT-EFFECT（SUPPORTED）・CR-SLOWBRO-SNORE-WHILE-ASLEEP（CONFIRMED）・CR-SLOWBRO-SNORE-AWAKE-FAILS（CONFIRMED）・CR-SLOWBRO-SNORE-ONLY-THIS-ATTACK（SUPPORTED）・CR-BORO-ROD-COIN-RESULTS（CONFIRMED）・CR-BORO-ROD-POKEMON-CARDS（CONFIRMED。p.313 は既存の転記） |
| 論点（73 → 74） | 新しい UQ-GROWL-NON-ATTACK-DAMAGE。既存の UQ-COPIED-ATTACK（ES3-021 のおおいびき）・UQ-CARD-USE-WITHOUT-TARGET（neo3-053）に事例が加わった |

- kyuura の論点の数 74 は、エンジンの停止コード（A0 のあと 277）・未解決の裁定（278）とは別の数で、同じ一覧の件数として揃えていません。
- 新しい事例 4 件を `kyuura_cases_without_engine_ruling` に結びました。移行の時点で写しに入れていない ボロのつりざお・ヤドラン・PR1-003 の 3 件は `unregistered`。IP1-040 のなきごえの
  UQ-GROWL-NON-ATTACK-DAMAGE は、エンジンが止める停止コード GN1（特殊能力のダメージ。2 章）と NK5（控えのこのカードへのワザのダメージ。kyuura では UQ-REDUCED-DAMAGE-BENCH-TARGET
  に結ばれている）に結び、`engine_issue_differs` を真にしました。控えのこのカードへの特殊能力のダメージは、今の対応カードでは起こりません（相手の場のポケモンを選ぶ［こっそりかみつく］・
  ［とつぜんかみつく］は進化したばかりのポケモンが使い、進化で効果が消える）。
- GN1 の `kyuura_disposition` を `not_in_kyuura` から `issue_not_in_index` にしました（kyuura に論点と事例はあるが、kyuura の未解決の一覧に行がない）。

### 3.4 ピカチュウ IP1-040 の採用元

kyuura の新しい LD-IP1-040-ATK0・CC-IP1-040-P127・CR-PIKACHU-GROWL-LATEST・CR-PIKACHU-GROWL-OPPONENT-EFFECT・UQ-GROWL-NON-ATTACK-DAMAGE が、v0.76 から登録しているピカチュウ IP1-040 を
指します。検査（研究の対応表の 4 と 7）が、最新の説明のある登録を印刷の文面で採用していると知らせたので、移行のコミットで次をそろえました。

- 処理に使う文面を最新の説明「次の相手の番、このワザを受けた相手は、このカードにダメージを与えるとき、そのダメージが「-10」される。」（出典 LD-IP1-040-ATK0）にしました。印刷の文面
  （「このワザを受けた相手は、次の相手の番でこのカードにダメージを与える時、そのダメージが「-10」される。」）との違いは語順と「時／とき」だけです（kyuura の `meaning_change`:
  `none_apparent`）。型 `ReduceDamageToSelfNextOpponentTurn(10)`・印刷の文面の照合（`GROWL_TEXTS` の 2 つめ）・挙動は v0.76 のままで、新しい文面の書き方は加えていません。
- 採用の記録の `play_text` の `attack/0` を `LD-IP1-040-ATK0` に、`kyuura_records` を研究の基準のコミットでこのカードを指す 5 件にしました（記録を読み直したのではなく、id の対応を
  直した。採用したときのデータのコミット 7d3f4ca・記録した日は変えていない）。研究の対応表の `adopted_printed_text` から `registered` に移しました（1,356 → 1,355）。でんきショック
  （`attack/1`）は印刷の文面のまま。
- カードの値が同じことを、研究上の意味や挙動が同じことの証明にしていません。CR-PIKACHU-GROWL-OPPONENT-EFFECT（受けた相手が持つ効果で p.321 の 2 段階）は SUPPORTED（段階は推論）で、
  v0.76 の実装の読み方と同じであることを確かめました（新しい裁定として確定したのではない）。

### 3.5 移行の確かめ

移行のコミットでは、写し・採用・研究の 3 つの検査と、移行に関係する既存のテスト（移行・研究・採用・なきごえ・写しの元を読むモジュール）を走らせました（全体のテストは最後の 1 回。
結果は 13 章）。
