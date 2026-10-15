# 研究データとエンジンの裁定の照合（v0.18a）

v0.18 の研究の基準にした kyuura のコミットを固定し、kyuura の記録（裁定・論点・最新の説明・照合）とエンジンの裁定・停止コード・実装上の仮定を対応づけた記録です。この段階では、エンジンの処理とカードの写しは変えていません（加えたのは研究の基準の記録と対応表、直したのは文書の誤りです。12 章）。

## 0. 要約

- 研究の基準: kyuura `adf97107ee0d9755cd7ddedae298ecb02914128e`（ブランチ `claude/engine-findings-through-v0.17`、2026-10-14）。エンジン v0.17（`d90bce1`）までの研究成果を取り込んだコミットで、kyuura の既定のブランチ（`claude/eloquent-lamport-5xyv5r`、`bcf38c7`）にはまだ取り込まれていません（1 章）。`kyuura_engine/data/research_links.json` の `research_commit` に記録しました。
- カードの写しの元（`KYUURA_COMMIT`）は `ecb2d69` のままです。`adf9710` から作り直した写しは、エンジンが使う項目がどのカードも同じでした（1.1）。写しのコミットを上げると、状態が持つカードデータのコミットが変わり、固定した参照データをすべて作り直すことになるので、上げていません（1.2）。
- 研究側は更新されています。エンジンの v0.5〜v0.17 の裁定の表 471 件を取り込み、論点 19 件・最新の説明 25 件・照合 30 件を記録しています。
- 公式の資料で新しく確定した裁定のうち、エンジンの未解決の裁定を解くものは **ありません**。kyuura は当時の公式の Q&A・大会の裁定・雑誌を探しておらず、どの論点も「資料が足りない」（`official_material: insufficient`）のままです（4 章）。
- 分類の違いは 17 件（エンジンの SUPPORTED などを kyuura が CONFIRMED にしたもの 14 件、エンジンの CONFIRMED を kyuura が SUPPORTED にしたもの 3 件）。どれも処理の結果は同じで、コードは変えません（4・5 章）。
- エンジンの未解決の裁定 24 件（停止コード 18 件）と、kyuura の論点 19 件は数え方が違います。対応は 6・9 章の表のとおりで、食い違い（片方だけが「決まった」とするもの）はありません。
- エンジンが登録しているワザ・特殊能力の最新の説明（`play_text_ja`）20 件は、kyuura の記録（`LD-`）と文字列まで一致しました（10 章）。
- kyuura が報告したエンジンの文書の誤り（キョウのベトベターの id、ベロリンガの文面の出典、マチスのマルマインの所在）を直しました（11.2）。

## 1. 研究の基準のコミット

| 項目 | 値 |
|---|---|
| リポジトリ | https://github.com/moheronemy/kyuura |
| コミット | `adf97107ee0d9755cd7ddedae298ecb02914128e`（2026-10-14 18:34 UTC「調査の状況のページに、数を数えたコミット（f7186bd）を記入」） |
| ブランチ | `claude/engine-findings-through-v0.17`（`origin` にある。既定のブランチ `claude/eloquent-lamport-5xyv5r`（`bcf38c7`）には取り込まれていない） |
| 選んだ理由 | kyuura の docs/engine-readiness.md 9.8「エンジン v0.18 が写す kyuura のコミットは、この取り込みのブランチ `claude/engine-findings-through-v0.17` の最後のコミット」 |
| カードの写しの元 | `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`（v0.1〜v0.18。変えていない） |
| 読み方 | `git show <コミット>:<パス>`（kyuura の作業ツリー・履歴は変えない。この作業の clone の HEAD は `0cb48e0` のまま） |

既定のブランチに取り込まれていないコミットを基準にしたので、kyuura 側でブランチを書き換えると、このコミットに届かなくなるおそれがあります。`git clone` は既定ですべてのブランチを取得するので、ブランチがある限り `scripts/extract_kyuura_cards.py` で読めます。kyuura 側でブランチを取り込んだら（または消すことになったら）、エンジン側で基準を見直します（報告事項 11.4）。

### 1.1 カードデータの違い（`ecb2d69` → `adf9710`）

kyuura の `data/cards.json` の差分（`git diff`）は 2 枚だけです。

| カード | 変わった項目 | エンジンの写し |
|---|---|---|
| ベロリンガ（PMCG2-041） | ワザ 1 の名前（したでなめる → まきつくベロ）・`jp_print.level`（29 → 26）・`ja_text_source`・`notes` | 写していない（v0.17a の候補で、採らなかった） |
| キョウのベトベトン（PMCG6-023） | `jp_en_differences` に「だつりょくえき」の英語版の「if it has any」の記録を加えた | 参照カード（`reference_only`）。処理には使わない項目 |

`KYUURA_COMMIT` を `adf9710` にした写しを作業ツリーの外で作って比べた差分も、`source.commit` と PMCG6-023 の `jp_en_differences` だけでした。エンジンが使う項目（名前・HP・タイプ・弱点・抵抗力・にげる・ワザ・特殊能力・進化）はどのカードも変わっていないので、照合の記録（`card_verification.json`）は `adf9710` に対しても有効です（v0.18e から `python3 scripts/check_research_links.py --kyuura ../kyuura` が確かめる）。

### 1.2 写しのコミットを上げなかった理由

最初は写しのコミット（`KYUURA_COMMIT`）を `adf9710` に上げて全テストを流しました（Python 3.13）。1,888 件のうち失敗が 1,904 件（subTest を含む）出ました（v0.1 との互換の参照データの 15 件、対戦の固定値、v0.13・v0.15 の参照データとの比較、v0.14 の比較のテストなど）。

- 原因: 対戦の状態はカードデータの元のコミットを持ち（`state.card_data.commit`。形式 1〜9 の書き出しの `card_data`）、ログ `game_created` にも `card_data_commit` を書きます。固定した参照データ（tests/fixtures/v0_1_reference.json・compat_base_4bd97bf.json・legacy_reference_v0_15.json）と固定値は、この値を含みます。
- 処理は変わらない差分のために、作り直してはいけない参照データ（CLAUDE.md）を作り直すか、比較からこの値を除くことになります。どちらも v0.18 の目的（研究と同じ出典・裁定を追跡できること）に要りません。
- そこで、写しのコミットは `ecb2d69` のまま、研究の基準 `adf9710` を別に記録しました（`research_links.json`）。エンジンが使う項目が 2 つのコミットで同じことは、写しを作り直さずに確かめます（v0.18e のスクリプト）。
- 写しのコミットを上げるのは、エンジンが使う項目が kyuura で変わったとき（例: フシギソウ・ケーシィのデータの誤りの候補を kyuura が直したとき。10 章）です。そのときは、参照データとの比較からカードデータのコミットを除く方法を、比較の道具ごとに決めてから行います（v0.19 の課題）。

## 2. 読んだ資料

- エンジン: docs/card-extensibility-verification-v0.17d.md・docs/rocket-snorlax-v0.17b.md・docs/kogas-muk-event-design-v0.17c.md・docs/preflight-consolidation-v0.16c.md・docs/kernel-consolidation-verification-v0.16e.md・docs/rules-2000-02-14.md・docs/implementation-status.md・docs/data-provenance.md・`kyuura_engine/resolution/questions.py`・`kyuura_engine/data/card_verification.json`。
- kyuura（`adf9710`）: docs/rules/card-rulings.md・docs/engine-readiness.md（9 章）・docs/research-status.md・docs/data-schema.md・data/sidecar/rulings.json・data/sidecar/latest_descriptions.json・data/sidecar/card_checks.json・scripts/build_card_rulings.py・tests/test_engine_imports_v014_v017.py。

確かめ方:

```sh
git -C ../kyuura show adf97107ee0d9755cd7ddedae298ecb02914128e:data/sidecar/rulings.json > /tmp/rulings.json   # 読むだけ
python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura --check
```

## 3. 識別子の対応のしかた

| 側 | 識別子 | 内容 |
|---|---|---|
| エンジン | 裁定の id（`Z9`・`DR1`・`C18` など） | 文書ごとの番号。版が違えば同じ id でも別の裁定（v0.6 の H1 と v0.9 の H1 など）。kyuura の `engine_refs` は（取り込みの id・版・文書・id）の組で指す |
| エンジン | 停止コード（`UNRESOLVED_…`） | エンジンの実装の止め方。公式の裁定ではない |
| エンジン | コードのない問い（`questions.QUESTIONS` の `code` が None） | 起こったら止める問い（`power_damage_weakness_resistance` など） |
| kyuura | `CR-…`（裁定。CONFIRMED・SUPPORTED） | 根拠（`basis`）と推論（`inference`）つき |
| kyuura | `UQ-…`（未解決の論点） | 結果への影響（`audit.game_effect`）・解決に要る資料・調べた範囲つき |
| kyuura | `LD-<カード>-ATK<n>/PWR<n>` | 最新の説明の記録（印刷の文面・エラッタと区別） |
| kyuura | `CC-<カード>-<出典>` | 印刷物との照合の記録（データの誤り・直したもの・欠けた値） |
| kyuura | `GR-…` | 公式ルールの条項 |
| kyuura | `ENGINE-<7 桁>` | エンジンの取り込みの記録（v0.17 は `ENGINE-D90BCE1`） |
| kyuura | `engine_unresolved_index` | エンジンの未解決の項目と論点の対応（28 項目。処理 `issue`・`out_of_scope`・`implementation_only`・`not_yet_imported`） |

kyuura は停止コードを論点の文に書かず、`engine_refs` と `engine_unresolved_index` にだけ書いています。エンジン側も、kyuura の論点 id をエンジンの停止コードの代わりにしません（この段階で、エンジンから kyuura の id を引ける対応表 `kyuura_engine/data/research_links.json` を加えた）。

## 4. 比較 1: 公式に確認された裁定（CONFIRMED）

- kyuura の裁定 235 件のうち CONFIRMED 159 件、SUPPORTED 76 件。エンジンの裁定 id ごとの kyuura の分類は、CONFIRMED 249・SUPPORTED 102・両方 23・未解決 34・条項と照合だけ 45・取り込んでいない 18（kyuura docs/engine-readiness.md 9.6。計 471）。
- **新しい資料で確定した裁定はない**: kyuura の今回の監査で新しく読んだ資料は『オフィシャルブック2000』（P43）のページだけです（pp.49・55・138・155・229・245 を 600dpi で読み直した）。どの論点の `audit.new_sources` も `resolves: false` です。当時の Q&A・大会の裁定・雑誌の記事は探していません。
- kyuura がエンジンの分類より強く（CONFIRMED に）したものは 14 件です。どれも同じ『オフィシャルブック2000』の記述を「解釈の選択なしに導かれる」と判断したもので、エンジンの処理は同じです（コードを変えない）。

| kyuura の記録 | エンジンの id（版） | エンジンの分類 | kyuura の理由（要約） | エンジンの処理 |
|---|---|---|---|---|
| CR-SHELL-ATTACK-ENDS-ON-DEVOLUTION | S29（v0.13） | 到達しない | p.324「19」が退化で持続する効果から回復すると書く | 退化は未実装（変えない） |
| CR-ENERGY-TRANS-RAINBOW | V12（v0.5） | 該当なし（未対応） | p.16 の解説がそのまま書く | 特殊エネルギーは未実装（変えない） |
| CR-RAIN-DANCE-BENCH | R6（v0.6） | SUPPORTED | p.312 に「場」の定義の文がある | 同じ（ベンチにもつけられる） |
| CR-HYDRO-PUMP-DAMAGE | H3（v0.6） | SUPPORTED | 最新の説明から同じ値、解説が数を書く | 同じ |
| CR-DAMAGE-SWAP-ALAKAZAM-ITSELF | S5（v0.7。移動元） | 移動元 SUPPORTED | 「自分の場にいるポケモン」に除外がない | 同じ |
| CR-DAMAGE-SWAP-ACTIVE-AND-BENCH | S12（v0.7） | 一部 SUPPORTED | p.312 の「場」の定義 | 同じ |
| CR-SELF-DAMAGE-IS-ATTACK-DAMAGE | H7（v0.9） | SUPPORTED | p.320「(3)」がそのまま書く（計算の部分は別の記録） | 同じ |
| CR-GUTS-BENCH | G8（v0.11） | SUPPORTED・未到達 | p.311・p.323 の「ベンチ…も使うことができます」 | 同じ |
| CR-PHOENIX-ANY-CAUSE | P6・P8・P9（v0.12） | SUPPORTED | 最新の説明が原因を限らない | 同じ |
| CR-RESTLESS-SLEEP-ZERO | Z17（v0.17） | SUPPORTED | p.319 が 0 ダメージを「受けなかった」とする | 同じ |
| CR-RESTLESS-SLEEP-NO-CHAIN | Z10（v0.17） | SUPPORTED | p.245 が特殊能力のダメージと明記 | 同じ |
| CR-RESTLESS-SLEEP-VS-GUTS | Z19（v0.17） | SUPPORTED | こんじょうは「相手のワザによる」に限る | 同じ |
| CR-ENERGY-DRAIN-ZERO | DR4（v0.17） | SUPPORTED | p.319 | カードは延期（変えない） |
| CR-ENERGY-DRAIN-STATUS | DR15（v0.17） | CONFIRMED・SUPPORTED | 最新の説明「ダメージを受けるとき、すでに」 | カードは延期（変えない） |

## 5. 比較 2: 資料から支持される推論（SUPPORTED）

kyuura がエンジンの CONFIRMED を SUPPORTED にしたものは 3 件です。読み方に推論が要るとして分類をそろえたもので、エンジンの処理は同じです。エンジンの規定の文（CLAUDE.md・各版の文書）は「SUPPORTED を根拠なく CONFIRMED にしない」の向きで、弱める変更は処理に影響しません。

| kyuura の記録 | エンジンの id（版） | エンジンの分類 | kyuura の理由（要約） |
|---|---|---|---|
| CR-EFFECTS-AFTER-KO | I4（v0.5）・K1・K9（v0.7）・M8（v0.8）・H1・H12（v0.9）・L11（v0.11） | CONFIRMED | きぜつの時点（HP 以上で処理の対象がなくなるか）が規定に書かれていない |
| CR-KARATE-CHOP-DAMAGE | M5・M6（v0.10） | CONFIRMED | 引く数を 1 段階のダメージとする読み方（M4。SUPPORTED）が前提 |
| CR-FIRE-WALL-EXPIRY | W27（v0.12） | CONFIRMED | 次の相手の番の終わりに消える（W5。SUPPORTED）が前提 |

- 今後エンジンの文書で分類を引くときは、kyuura の分類（正本）を書き、エンジンの版の表の分類は当時の記録として残します（過去の版の表は書き換えない）。
- 回帰の確かめ: 17 件とも処理は同じなので、既存のテスト（例: tests/test_rocket_snorlax_v0_17b.py `test_zero_or_prevented_damage_does_not_trigger`（Z17）、tests/test_damage_swap_v0_7.py（S5・S12）、tests/test_guts_v0_11.py（G8）、tests/test_phoenix_v0_12.py（P6・P8・P9）、tests/test_rocket_moltres_v0_12.py（W5・W27））がそのまま回帰を確かめます。分類を変えたことでテストの期待は変えていません。

## 6. 比較 3: 未解決の裁定

エンジンの数え方は未解決の裁定 24 件（停止コード 18 件・コードのない問い 6 件）で、延期したキョウのベトベトンの DR1・DR6・DR8・DR13・DR18 は数に入りません。kyuura の数え方は論点 19 件です。

| エンジンの項目（版） | 停止コード | kyuura の論点 | kyuura の結果への影響 |
|---|---|---|---|
| R13（v0.6） | `UNRESOLVED_ATTACH_AFTER_POWER_ATTACH` | UQ-RAIN-DANCE-ATTACH-COUNT | game_result |
| 「ダメージを受けない」相手のコインのダメージ（v0.4b） | `UNRESOLVED_PREVENTED_COIN_DAMAGE` | UQ-COIN-IN-NULLIFIED-ELEMENT | rng_only |
| T19b（v0.9。v0.11 の L5・L13 も） | `UNRESOLVED_EVADED_EFFECT_COIN` | UQ-COIN-IN-NULLIFIED-ELEMENT | rng_only |
| H4（v0.9） | `UNRESOLVED_RECOVER_ZERO_ENERGY` | UQ-ENERGY-CONVERSION-ZERO | game_result |
| C18（v0.10。v0.17 の Z13 も） | `UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT` | UQ-COUNTERATTACK-DOUBLE-KO | game_result |
| G37（v0.11。G30・v0.17 の Z22 も） | `UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT` | UQ-GUTS-ATTACK-EFFECT | game_result |
| W24（v0.12。v0.13 の S37 も） | `UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT` | UQ-RETALIATION-DOUBLE-KO | game_result |
| Z23（v0.17） | `UNRESOLVED_EFFECT_AFTER_NO_DAMAGE` | UQ-EFFECT-AFTER-NO-DAMAGE | game_result |
| 両方ねむりのコインの順番（v0.3b。v0.17 の Z29 も） | `UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER` | UQ-POKEMON-CHECK-SLEEP-COIN-ORDER | rng_only |
| T27（v0.9） | なし（起こらない） | UQ-TRANSPARENCY-COIN-ORDER | rng_only |
| C34/C35（v0.10。S7・Z18・DR18 も） | なし（起こらない。起こったら RuntimeError） | UQ-MULTIPLE-DAMAGE-TRIGGERS-ONE-ATTACK | game_result |
| G40（v0.11。G16 も） | なし（起こらない） | UQ-KO-PREVENTION-ORDER | not_analyzed |
| P19（v0.12） | なし（起こらない） | UQ-PHOENIX-GAS-SOURCE-KO | game_result |
| P32（v0.12） | なし（起こらない） | UQ-POST-KO-POWERS-ORDER | not_analyzed |
| Z9（v0.17） | なし（コードのない問い。今のカードでは起こらない） | UQ-POWER-DAMAGE-WEAKNESS-RESISTANCE | game_result |
| 切り直しの補償（v0.1） | `UNRESOLVED_MULLIGAN_COMPENSATION` | なし（kyuura は対象外。調べていない） | — |
| きずぐすりの条件 2 件（v0.2b） | `UNRESOLVED_POTION_WITHOUT_DAMAGE`・`UNRESOLVED_POTION_UNDAMAGED_TARGET` | なし（同上） | — |
| ポケモンいれかえの条件（v0.2b） | `UNRESOLVED_SWITCH_WITHOUT_BENCH` | なし（同上） | — |
| ポケモンチェックのどくで両方きぜつ（v0.3a） | `UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT` | なし（同上） | — |
| マヒの再付与（v0.3b） | `UNRESOLVED_REPARALYSIS_RECOVERY_TURN` | なし（同上） | — |
| こんらんの 20 とダメージを変えるカード（v0.3c） | `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` | なし（同上） | — |
| にげるに失敗したあとの再宣言（v0.3c） | `UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED` | なし（同上） | — |
| 進化したあとの HP（v0.4a） | `UNRESOLVED_EVOLUTION_HP` | なし（同上） | — |
| DR1（v0.17c。カードは延期） | なし（数えない） | UQ-ENERGY-DRAIN-DECLARATION（DR12 も） | game_result |
| DR6（v0.17c） | なし（数えない） | UQ-ENERGY-DRAIN-TIMING | not_analyzed |
| DR8（v0.17c） | なし（数えない） | UQ-ENERGY-DRAIN-ATTACKER-KO | not_analyzed |
| DR13（v0.17c） | なし（数えない） | UQ-ENERGY-DRAIN-NO-ENERGY | rng_only |
| P27・P28・P30（v0.12。エンジンは順番を正規化） | なし（実装上の仮定） | UQ-PHOENIX-KO-PROCESS-ORDER | order_only |

- 未解決の裁定 24 件のうち、15 項目が kyuura の論点 14 件に対応します（v0.4b のコインのダメージと T19b は、kyuura では 1 つの論点）。停止コードのある v0.1〜v0.4b の 9 件は、kyuura の取り込みの範囲（v0.5〜v0.17）の外で、kyuura は論点にしていません（`out_of_scope`。原典のページを確かめていない）。エンジンの再調査の記録は docs/unresolved-rulings-v0.3d.md です（kyuura への報告事項 11.4）。
- kyuura の論点 19 件のうち、エンジンの未解決の数に入らないのは 5 件です。DR1・DR6・DR8・DR13 はカードを延期したため、UQ-PHOENIX-KO-PROCESS-ORDER はエンジンが順番を正規化している（結果が同じことを確かめた実装上の仮定。docs/post-knockout-powers-v0.12.md 3 章）ためです。エンジンは正規化を「ルールの裁定ではない」と書いており、kyuura が論点にしていることと矛盾しません。
- **片方だけが「決まった」とする項目はありません**。エンジンの未解決の 24 件はどれも kyuura で UNRESOLVED の論点か対象外で、kyuura の論点 19 件はどれもエンジンで止める・起こらない・延期・正規化（仮定）のどれかです。

## 7. 比較 4: エンジンの実装上の仮定

- kyuura が取り込んでいないエンジンの裁定 18 件（対象外 14・保留 4）は、エンジンが「実装上の仮定」「実装の設計」とした判断などです（kyuura docs/rules/card-rulings.md 7 章）。v0.17 では DR14（保留。処理する時点による）・DR20（対象外。先読みの範囲の設計）。
- 1 回の使用で 1 枚（エナジートランス）・1 個（ダメージスワップ）、場のポケモンの番号の持ち方、同時のきぜつで両方がサイドを取る順番の正規化、「ふしちょう」の順番の正規化は、エンジンの文書で実装上の仮定と書いており、kyuura もそう扱っています。
- **コインの有無・順番だけが変わる論点（rng_only）4 件**: kyuura は「盤面が変わらないとみられるので（kyuura の推論）、エンジンの実装の約束（乱数の割り当て）として決める選択肢がある」と書いています（engine-readiness 9.8）。v0.18 では **採りません**。
  - 対象: UQ-COIN-IN-NULLIFIED-ELEMENT（`UNRESOLVED_PREVENTED_COIN_DAMAGE`・`UNRESOLVED_EVADED_EFFECT_COIN`）・UQ-TRANSPARENCY-COIN-ORDER（T27。起こらない）・UQ-ENERGY-DRAIN-NO-ENERGY（カードは延期）・UQ-POKEMON-CHECK-SLEEP-COIN-ORDER。
  - 理由 1: 盤面が変わらないことは kyuura の推論で、kyuura 自身が「コインを投げたことそのものが意味を持つカードがあるかは調べていない」と書いています。
  - 理由 2: 決めると、今止めている盤面で乱数の続きが変わり、固定した v0.17 との比較（v0.18 の完了条件）で、説明できる差を新しく作ることになります。v0.18 の範囲は「研究と同じ出典・裁定を追跡できる状態にする」で、止め方を変える根拠になる新しい資料はありません。
  - 決めるなら、実装の約束（裁定ではない）として、論点ごとに乱数の割り当てを文書にし、停止コードの分類（`UNRESOLVED_…`）を外す理由を docs/unresolved-rulings-v0.3d.md の形で書く必要があります（v0.19 の課題。docs/v0.18-verification.md）。

## 8. 比較 5: エンジンが対応していない事例

| kyuura の記録 | 内容 | エンジン |
|---|---|---|
| LD-PMCG5-027-ATK0 | カスミのヒトデマン「スターブーメラン」 | 未実装（v0.13 のテスト専用の模擬のワザで順番だけ確かめた） |
| LD-PMCG5-054-ATK0 | 「クロスカウンター」 | 未実装（量の決め方の違う返す効果） |
| LD-PMCG3-003-ATK1 | 化石の秘密のベトベター「ちいさくなる」 | 未実装（参照カード） |
| LD-PMCG1-047-ATK1 | 第1弾のゴースト「ゆめくい」 | 未実装（参照カード） |
| LD-PMCG6-023-PWR0 | キョウのベトベトン「だつりょくえき」 | 延期（v0.17c。v0.18d で見直す） |
| UQ-EFFECT-AFTER-NO-DAMAGE の事例 | ナツメのヤドン（PMCG6-044）「ぐうたらこうげき」 | v0.18c で加える（Z23 の場合は止める。docs/kernel-reuse-v0.18c.md） |
| UQ-EFFECT-AFTER-NO-DAMAGE の到達性 | わるいフーディン「テレポートブラスト」・わるいオコリザル「あばれくるう」・キョウのドガース「くもがくれガス」・カツラのファイヤー「ひのとり」（kyuura は最新の説明を確かめていない） | 未実装 |
| UQ-POWER-DAMAGE-WEAKNESS-RESISTANCE の到達性 | マチスのマルマイン［ショックボム］（雷。kyuura の data/ja_text_pcgsearch.json のジムデッキの記録にある） | 未実装。加えると Z9 が起こりうる（雷の弱点・抵抗力のカードがある） |

## 9. 比較 6: 停止コードと論点 id

停止コード 18 件と kyuura の論点の対応です（`tests/test_unresolved_boundaries_v0_4e.py` の `ALL_CODES` と同じ 18 件）。

| 停止コード | kyuura の論点 | kyuura の `engine_unresolved_index` の処理 |
|---|---|---|
| `UNRESOLVED_MULLIGAN_COMPENSATION` | — | out_of_scope |
| `UNRESOLVED_POTION_WITHOUT_DAMAGE` | — | out_of_scope |
| `UNRESOLVED_POTION_UNDAMAGED_TARGET` | — | out_of_scope |
| `UNRESOLVED_SWITCH_WITHOUT_BENCH` | — | out_of_scope |
| `UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT` | — | out_of_scope |
| `UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER` | UQ-POKEMON-CHECK-SLEEP-COIN-ORDER | issue |
| `UNRESOLVED_REPARALYSIS_RECOVERY_TURN` | — | out_of_scope |
| `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` | — | out_of_scope |
| `UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED` | — | out_of_scope |
| `UNRESOLVED_EVOLUTION_HP` | — | out_of_scope |
| `UNRESOLVED_PREVENTED_COIN_DAMAGE` | UQ-COIN-IN-NULLIFIED-ELEMENT | issue |
| `UNRESOLVED_ATTACH_AFTER_POWER_ATTACH` | UQ-RAIN-DANCE-ATTACH-COUNT | issue |
| `UNRESOLVED_EVADED_EFFECT_COIN` | UQ-COIN-IN-NULLIFIED-ELEMENT | issue |
| `UNRESOLVED_RECOVER_ZERO_ENERGY` | UQ-ENERGY-CONVERSION-ZERO | issue |
| `UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT` | UQ-COUNTERATTACK-DOUBLE-KO | issue |
| `UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT` | UQ-GUTS-ATTACK-EFFECT | issue |
| `UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT` | UQ-RETALIATION-DOUBLE-KO | issue |
| `UNRESOLVED_EFFECT_AFTER_NO_DAMAGE` | UQ-EFFECT-AFTER-NO-DAMAGE | issue |

コードのない問い（`questions.QUESTIONS`）: `power_damage_weakness_resistance`（Z9 → UQ-POWER-DAMAGE-WEAKNESS-RESISTANCE）、`ko_prevention_self_effect`（Z22 → UQ-GUTS-ATTACK-EFFECT の事例）。`decisions.py` の `UNRESOLVED_RULING` は、トレーナーの決定の `unresolved_choices` の既定の値で、カードの登録では使っていません（停止コードの数に入れない）。

## 10. 最新の説明（LD）と照合（CC）

- エンジンが登録しているワザ・特殊能力のうち、kyuura に最新の説明の記録があるもの 20 件は、`play_text_ja` と kyuura の `latest_description.text_ja` が文字列まで一致しました（ページも同じ）: LD-PMCG4-021-ATK0・ATK1、LD-PMCG5-020-ATK0・PWR0、LD-PMCG1-001-ATK0、LD-PMCG1-011-PWR0、LD-PMCG1-023-ATK1、LD-PMCG1-027-ATK0、LD-PMCG1-032-PWR0・ATK0、LD-PMCG1-046-ATK0、LD-PMCG1-049-PWR0、LD-PMCG3-007-PWR0、LD-PMCG3-030-PWR0、LD-PMCG3-029-ATK1、LD-PMCG1-057-PWR0、LD-PMCG1-055-ATK0、LD-PMCG6-061-PWR0、LD-PMCG6-073-PWR0・ATK0。残りの 5 件は 8 章の未対応のもの。
- kyuura の照合 30 件のうち 28 件は、エンジンの照合の記録のあるカードです。kyuura がデータの誤りの候補（`fix_status: candidate`。kyuura のデータはまだ直していない）とした 2 件は、エンジンも v0.5・v0.7 で「不一致あり」として記録済みでした。
  - CC-PMCG1-008-P43（フシギソウ「つるのムチ」／誌面「つるのむち」）: エンジンは写しの値で登録を照合している（処理は変わらない）。
  - CC-PMCG1-043-P43（ケーシィ「ねんりき」の読点）: エンジンは最新の説明にしたがう（処理は変わらない）。
  - kyuura が直したら、写しを作り直して登録の照合の名前を見直します（v0.19 以降）。
- 残りの 2 件（CC-PMCG2-041-P234 ベロリンガ・CC-PMCG5-048-P200 タケシのイワーク）は、エンジンの写しにないカードです。
- エンジンに kyuura の照合・最新の説明の記録がないカード: v0.1〜v0.4 のカード（kyuura の取り込みの範囲の外）と、v0.18c で加えるナツメのヤドン（エンジンが p.155 を照合した。kyuura への報告事項）。

## 11. 研究とエンジンの違いの扱い

### 11.1 分類の違い（17 件）

4・5 章のとおり、どれも処理は同じなのでコードを変えません。エンジンの過去の版の表は書き換えず、v0.18 から加えた対応表（`kyuura_engine/data/research_links.json`）に kyuura の分類を記録します。

### 11.2 エンジンの文書の誤り（この段階で直した）

| 誤り | 正しい値 | 直した所 |
|---|---|---|
| キョウのベトベターを「PMCG6-020」と書いた（kyuura の PMCG6-020 はサカキのニドクイン） | PMCG6-007 | docs/kogas-muk-event-design-v0.17c.md 6 章・docs/data-provenance.md |
| ベロリンガ（PMCG2-041）の文面の転記元を「ポケモンWiki」と書いた | なぞのばしょ（https://nazonobasho.com/pmcg02-043-beroringa/）。kyuura は `adf9710` で出典の誤記として直した（CC-PMCG2-041-P234） | docs/card-selection-v0.17a.md 7 章 |
| ［ショックボム］のカード（マチスのマルマイン）を写しの元データで見つけられなかったと書いた | kyuura の `data/cards.json`（拡張パックの 780 枚）にはないが、ジムデッキの記録（`data/ja_text_pcgsearch.json` の「ポケモンジム第2弾「クチバシティジム マチス」」009/025）にある | docs/card-extensibility-verification-v0.17d.md 10 章 |

### 11.3 数え方の違い

- エンジン: 未解決の裁定 24 件（停止コード 18 件）。延期したカードの DR の問いは数えない。
- kyuura: 論点 19 件（`engine_unresolved_index` は 28 項目で、うち DR の 4 項目は `in_engine_count: false`）。
- どちらの数も、相手の数の代わりにしません（`research_links.json` は、項目ごとに両方の id を持つ）。

### 11.4 kyuura への報告事項（kyuura 側の作業）

1. 基準にしたコミット `adf9710` は既定のブランチに取り込まれていない。取り込むか、ブランチを残すかを決めてほしい（消えるとエンジンの研究の基準を読めない）。
2. 停止コードのある v0.1〜v0.4b の 9 件（`out_of_scope`）は、エンジンの docs/unresolved-rulings-v0.3d.md で原典を調べ直した記録がある。kyuura で論点にするかの判断材料にしてほしい。
3. ナツメのヤドン（PMCG6-044）の最新の説明（p.155）をエンジンが照合した（v0.18c。docs/kernel-reuse-v0.18c.md）。kyuura に `LD-PMCG6-044-ATK0`・照合の記録はない。
4. フシギソウ・ケーシィのデータの誤りの候補（CC-PMCG1-008-P43・CC-PMCG1-043-P43）は、エンジンも同じ違いを記録している（エンジンの記録は調査の履歴で、原典ではない）。

## 12. この段階で変えたもの

- `kyuura_engine/data/research_links.json` を加えた（研究の基準のコミット、停止コード・未解決の裁定と kyuura の論点の対応、分類の違い 17 件）。v0.18e で、最新の説明・照合の記録の対応と、検査（スクリプトとテスト）を加える。
- `kyuura_engine/data/card_verification.json` の PMCG6-023 の注（kyuura が最新の説明を別に記録したこと）。
- 11.2 の文書の誤り。README.md・CLAUDE.md・docs/rules-2000-02-14.md・docs/data-provenance.md に研究の基準のコミットを書いた。
- カードの写し（`KYUURA_COMMIT`・`kyuura_cards.json`）・処理・状態の形・ログ・書き出しの形式・公開の API は変えていない。
