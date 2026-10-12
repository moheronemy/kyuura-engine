# キャタピー・パラス（v0.3b）: 原典照合と実装

v0.3b で対応したキャタピー（PMCG1-002、第1弾）の「いとをはく」と、パラス（PMCG2-003、第2弾ポケモンジャングル）の「ひっかく」「キノコのほうし」について、原典で確かめたこと、実装、テストを対応づけた記録です。ねむり・マヒの規定は [sleep-paralysis-v0.3b.md](sleep-paralysis-v0.3b.md)、ポケモンチェックは [pokemon-check-v0.3b.md](pokemon-check-v0.3b.md)、設計は [architecture-v0.3b.md](architecture-v0.3b.md) にあります。

- カード id: `PMCG1-002`・`PMCG2-003`（kyuura の参照コミット `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691` の data/cards.json。読むだけ）。英語版は Base Set の 45（キャタピー）、Jungle の 59（パラス）（kyuura `source_ids.pokemontcg`）
- カードの処理: 『ポケモンカードオフィシャルブック2000』のカードのページの「最新の説明」（p.6）
- 照合の方法: Internet Archive のスキャン [J38] の PDF の p.19（誌面 p.17）・p.40（誌面 p.38）を 300dpi の画像にし、見出し・図版・「ワザ」欄・解説を目で読んだ（2026-10-12）。OCR の文字はページを探すのに使っただけ
- 照合の記録: `kyuura_engine/data/card_verification.json` の PMCG1-002・PMCG2-003（どちらも「一致」）。写しの組は `pool_v0_3b`（`scripts/extract_kyuura_cards.py` の `POOL_V0_3B`。写しを作り直し、`--check` で一致）

## 1. キャタピー（PMCG1-002）

| 項目 | kyuura の写し | 『オフィシャルブック2000』p.17 | 結果 |
|---|---|---|---|
| 見出し | — | 「たねポケモン キャタピー LV.13／HP40」 | 一致（`jp_print.level` 13、HP 40、たね） |
| 収録 | `jp_print.series`「第1弾拡張パック、スターターパック」 | 「ポケモンカード第1弾」 | 第1弾は一致（書き方が違う。エンジンは使わない項目） |
| タイプ | 草 | 図版: 草 | 一致 |
| ワザ | いとをはく、草 1、10、「コインを投げて「おもて」なら、相手を「マヒ」状態にする。」 | 図版: いとをはく（草）10「コインを投げて「おもて」なら 相手を「マヒ」状態にする」。最新の説明「●いとをはく コインを投げて「おもて」なら、相手を「マヒ」状態にする。」 | 一致（kyuura の説明文は最新の説明と一字一句同じ）。ワザは 1 つ |
| にげる | 1 | 図版: 無色 1 | 一致 |
| 弱点・抵抗力 | 弱点 炎 ×2、抵抗力なし | 図版: 弱点 炎、抵抗力の欄は空 | 一致 |
| 解説 | — | 「草ポケモンの特徴は、マヒ、どくなどの特殊状態を与えるワザによくあらわれています。「いとをはく」は、キャタピーらしいワザです。コイントスで表を出すと、相手の対戦ポケモンをマヒ状態にします。マヒ状態にされたポケモンは、ワザを使うことも逃げることもできません。…」 | 公式ルール p.322 のマヒの記述と合う。処理に関わるほかの記述はない |

図版の右下のマーク（レアリティマークの有無）は、この画像では読めません。第1弾の初版（kyuura `jp_print.remarks`「初版はレアリティマークなし」）の図版かどうかは決めていません。エラッタの記録はありません。

### 処理（`effects.ParalyzeOnHeads`、登録表 `AttackKey("PMCG1-002", 0)`、出典 `P43 p.17`）

| 順 | 処理 | 根拠 |
|---|---|---|
| 0 | 使えるかの確認（番・ワザの位置・ねむり／マヒでないこと・登録・必要なエネルギー 草 1）。だめなら拒否し、コインも投げない | p.309 手順 1〜3 |
| 1 | 相手の対戦ポケモンに 10（説明の最初に省略されている「相手の対戦ポケモンに10ダメージ。」）。p.321 の順番で計算 | p.320（シードラの「あわ」の例と同じ形）・p.321 |
| 2 | 相手が 1 で HP 以上になったら（きぜつ）、マヒにする内容は対象がいないので無視する。コインも投げない | p.309・p.323 |
| 3 | マヒの再付与で回復する番が原典で決められない場合は、コインの前に止める（`paralysis_problem`。対応カードでは起こらない） | p.322（[sleep-paralysis-v0.3b.md](sleep-paralysis-v0.3b.md) 3.1） |
| 4 | コインを 1 枚投げる（ワザを使う側のプレイヤー。`source: "attack"`、`effect: "PMCG1-002#0"`） | p.17・p.319 |
| 5 | 「おもて」なら相手の対戦ポケモンをマヒ状態にする（マヒ状態になった番を持つ。ねむりなら置きかわる。どくは残る）。「うら」なら何もしない | p.17・p.322 |
| 6 | ワザのあと: きぜつ・サイド・交代 → 番の終わり → ポケモンチェック。マヒは、相手の次の番の終わりのポケモンチェックで回復する | p.309・p.322・p.323 |

マヒにするのは「効果」で、ダメージではありません。1 のダメージが 0（ディフェンダーなど）でも、「おもて」ならマヒ状態にします。

| 相手の対戦ポケモン | いとをはくのダメージ | コイン | 結果 |
|---|---|---|---|
| ガーディ（HP60、弱点 水） | 10 | おもて | マヒ（相手の次の番はワザ・にげるができず、その番の終わりに回復） |
| ガーディ | 10 | うら | なし |
| ディグダ（HP30、弱点 草） | 10 × 2 = 20 | おもて | マヒ |
| コラッタ（HP30、ダメージ 20） | 10 → きぜつ | 投げない | — |
| ねむりのガーディ | 10 | おもて | ねむりが消えてマヒ（そのポケモンチェックでねむりのコインは投げない） |
| どくのガーディ | 10 | おもて | どく + マヒ |

## 2. パラス（PMCG2-003）

| 項目 | kyuura の写し | 『オフィシャルブック2000』p.38 | 結果 |
|---|---|---|---|
| 見出し | — | 「たねポケモン パラス LV.8／HP40」 | 一致（`jp_print.level` 8、HP 40、たね） |
| 収録 | `jp_print.series`「ポケモンジャングル」 | 「ポケモンカード第2弾ポケモンジャングル」 | 一致 |
| タイプ | 草 | 図版: 草 | 一致 |
| ワザ 1 | ひっかく、無色 2、20、説明なし | 図版: ひっかく（無無）20。「ワザ」欄「●ひっかく」（説明文なし） | 一致 |
| ワザ 2 | キノコのほうし、草 2、ダメージなし（`damage` が null）、「相手を「ねむり」状態にする。」 | 図版: キノコのほうし（草草）、ダメージの目安の数字なし、「相手を「ねむり」状態にする。」。最新の説明「●キノコのほうし 相手を「ねむり」状態にする。」 | 一致（kyuura の説明文は最新の説明と一字一句同じ） |
| にげる | 1 | 図版: 無色 1 | 一致 |
| 弱点・抵抗力 | 弱点 炎 ×2、抵抗力なし | 図版: 弱点 炎、抵抗力の欄は空 | 一致 |
| 解説 | — | 「バトル場に出てすぐに、無色２個エネルギーカードをつけることができれば、いきなり20ダメージ与えられます。」「草エネルギー２個で使える「キノコのほうし」は、相手の対戦ポケモンを確実にねむり状態にできるのですが、ダメージを与えることはできません。ねむり状態は相手プレイヤーがポケモンチェックの間に回復することもあるので、戦い方がむずかしいところです。」 | データと合う。キノコのほうしはダメージの要素のないワザ（コインも投げない） |

図版の右下のマークは、この画像では読めません。エラッタの記録はありません。

### 処理

**ひっかく**（`DamageOnly`、`AttackKey("PMCG2-003", 0)`）: 説明のないワザ。相手の対戦ポケモンに 20（p.309 の手順 6、p.320・p.321）。無色 2 なので、どのエネルギーでも払える。

**キノコのほうし**（`effects.PutToSleep`、`AttackKey("PMCG2-003", 1)`、出典 `P43 p.38`）:

| 順 | 処理 | 根拠 |
|---|---|---|
| 0 | 使えるかの確認（番・ワザの位置・ねむり／マヒでないこと・登録・必要なエネルギー 草 2） | p.309 手順 1〜3 |
| 1 | 相手の対戦ポケモンをねむり状態にする（もうねむりなら二重にしない。マヒなら置きかわる。どくは残る） | p.38・p.322 |
| 2 | ワザのあと: 番の終わり → ポケモンチェック。ねむりにした番の終わりのポケモンチェックから、持ち主がコインを投げる | p.309・p.322・p.323 |

ダメージの目安の数字がないので、説明の最初に省略されている「相手に○○ダメージ。」はありません（p.320 の省略は目安の数字があるときのもの）。ダメージの計算（p.321）をせず、`damage` のログもありません。プレイヤーの選択・コインはありません。「ダメージ 0」として `DamageOnly` に登録することはしていません（[sleep-paralysis-v0.3b.md](sleep-paralysis-v0.3b.md) 4 章）。

## 3. ログ

```
# いとをはく
attack            {player, pokemon, attack: "いとをはく", attack_index: 0}
damage            {player（相手）, pokemon, amount, steps, …}
coin_flip         {player, source: "attack", effect: "PMCG1-002#0", card, pokemon_id, number: 1, count: 1, result}
[special_conditions_removed {conditions: ("sleep",), reason: "replaced"}]   ← ねむりのポケモンが「おもて」のとき
special_condition {player（相手）, pokemon, pokemon_id, condition: "paralysis", paralyzed_turn, recovery_turn, effect: "PMCG1-002#0"[, already: true]}

# キノコのほうし
attack            {player, pokemon, attack: "キノコのほうし", attack_index: 1}
[special_conditions_removed {conditions: ("paralysis",), reason: "replaced"}]
special_condition {player（相手）, pokemon, pokemon_id, condition: "sleep", effect: "PMCG2-003#1"[, already: true]}
turn_end / pokemon_check / coin_flip {source: "pokemon_check", effect: "sleep", player（相手）} / sleep_check {recovered} / …
```

## 4. 実装しなかったワザ・カード

- キャタピー・パラスのほかのワザはありません（キャタピーは 1 つ、パラスは 2 つとも登録した）。
- 進化（トランセル・バタフリー・パラセクト）は未実装です。

## 5. 対応コードとテスト

| 事項 | コード | テスト |
|---|---|---|
| 登録・照合の記録・カードデータ | `effects.DEFAULT_EFFECTS`・`card_verification.json`・`scripts/extract_kyuura_cards.py` | test_caterpie_paras.py `RegistrationTest`、test_effects.py `test_attacks_with_text_follow_the_verified_latest_description`・`test_every_registration_is_backed_by_a_verification_record`、test_cards.py |
| 登録の誤りを見つける | `ParalyzeOnHeads.check`・`PutToSleep.check`・`DamageOnly.check` | `test_wrong_registrations_are_detected` |
| いとをはく | `effects.ParalyzeOnHeads` | test_caterpie_paras.py `StringShotTest` |
| キノコのほうし・ひっかく | `effects.PutToSleep`・`DamageOnly` | test_caterpie_paras.py `SporeTest` |
| ねむり・マヒの規定 | `conditions`・`engine` | test_sleep_paralysis.py・test_pokemon_check_v0_3b.py |
| 正式な対戦開始から | — | test_sleep_paralysis_games.py |

## 6. 未解決事項

- マヒの再付与で回復する番が変わる場合（[sleep-paralysis-v0.3b.md](sleep-paralysis-v0.3b.md) 3.1。対応カードでは起こらない）
- 両方の対戦ポケモンがねむりのときのコインの順番（[pokemon-check-v0.3b.md](pokemon-check-v0.3b.md) 4 章。対応カードでは起こらない）
- 図版が第1弾の初版の図版かどうか（処理には関係しない）
