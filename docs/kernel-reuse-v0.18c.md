# 解決の基盤の要素の再利用: ナツメのヤドン（v0.18c）

解決の基盤（`kyuura_engine/resolution/`）の既存の要素だけで、原典で確かめた実在のカードを 1 枚加えた記録です。

## 0. 結論

- ナツメのヤドン（PMCG6-044。ジム拡張第2弾闇からの挑戦）の「ぐうたらこうげき」を、R団のカビゴンの「たおれこむ」（v0.17b）と **同じ実装の型** `DamageAndSelfSleep`（要素 `Damage(OPP, Printed())` → `Status(SLEEP, target=SELF, after_damage="damage")`）で登録しました。
- 変えたのは、登録 1 つ（`effects.DEFAULT_EFFECTS`）・照合の記録 1 つ・カードの写しの組 `pool_v0_18c`・テストとストレス実行の組だけです。`engine.py`・`resolution/` のどのファイル（`kernel.py`・`programs.py`・`catalog.py`・`flow.py`・`preflight.py`・`v013_checks.py`・`contract.py`）も変えていません（0 行）。新しい要素・実装の型・効果の定義・問い・停止コード・カードごとの分岐はありません。
- ダメージを与えなかったとき（Z23）は、たおれこむと同じ問いで宣言の前に止めます（解決済みとして扱わない）。ぐうたらこうげきは超のワザなので、抵抗力 超 −30 の相手で最終ダメージが 0 になる場合（Z23-b）が、たおれこむ（無色）と違って実際のカードで起こります（自然な対戦・ストレス実行で起こった。5 章）。

## 1. 選んだ理由と、採らなかった候補

依頼の第一候補がナツメのヤドンでした。kyuura の論点 UQ-EFFECT-AFTER-NO-DAMAGE（`adf9710`）は、事例（`cases`）にたおれこむとぐうたらこうげきを挙げています。

kyuura のカードデータ（`adf9710` の `data/cards.json`）で、印刷の文面に「ダメージを与えた後（あと）」を含むワザを持つカードを探し、既存の要素だけで表せるかを比べました。

| カード | ワザ | 既存の要素だけで表せるか | 判断 |
|---|---|---|---|
| **ナツメのヤドン（PMCG6-044）** | ぐうたらこうげき（超無）30「ダメージを与えた後、自分を「ねむり」状態にする。」（ワザは 1 つ・特殊能力なし） | 表せる（たおれこむと同じ並び） | **採った** |
| わるいオコリザル（PMCG4-041） | あばれくるう（闘闘）40「ダメージを与えた後、自分は「こんらん」状態になる。」 | ワザは `Status(CONFUSION, target=SELF, after_damage=…)` で表せるが、ポケモンパワー［きょうぼう］の実装がない | 採らない（パワーを効果のないものとして扱えない。最新の説明も未照合） |
| わるいフーディン（PMCG4-035） | テレポートブラスト「のぞむなら、ダメージを与えた後、自分の控えポケモンを1匹選び、このカードと入れ替えてもよい。」・マインドショック（弱点・抵抗力の影響を受けない） | 表せない（自分の任意の入れ替えの決定・弱点・抵抗力を計算しないダメージの要素がない） | 採らない |
| キョウのドガース（PMCG6-015） | くもがくれガス（自分とついているカードを山札にもどす）・えんまく（次の相手の番のワザの失敗） | 表せない（山札にもどす移動・相手に与える持続する効果） | 採らない |
| カツラのファイヤー（PMCG6-035） | ひのとり（「うら」なら自分とついているカードを山札にもどす） | 表せない（山札にもどす移動） | 採らない |
| ナツメのヤドラン（PMCG6-048。ナツメのヤドンの進化先） | いねむり（「おもて」ならカウンターを 3 つとりのぞき、自分をねむり）・きあいずつき（次の自分の番に使えない） | 表せない（決まった数を自分からとりのぞく要素・ワザを使えなくする持続する効果がない） | 採らない（進化先がなくても、ナツメのヤドンはたねポケモンとして対戦で使える） |

## 2. 原典の照合（p.155）

『ポケモンカードオフィシャルブック2000』p.155（PDF 157 ページ）を、ページ全体 110dpi で位置を確かめ、見出し・図版・「ワザ」欄・解説を 600dpi の画像で読みました（OCR の文字は使っていない）。記録は `kyuura_engine/data/card_verification.json` の PMCG6-044（`status` は「一致」）。

| 項目 | 誌面 | kyuura の写し（`ecb2d69`。`adf9710` でも同じ） |
|---|---|---|
| 見出し | たねポケモン ナツメのヤドン LV.15／HP50、収録「ジム拡張第2弾闇からの挑戦」 | basic・HP 50・LV.15・`jp_print.series`「闇からの挑戦」（書き方の違い。エンジンは使わない） |
| 図版 | 超、ぐうたらこうげき（超・無色）30、にげる 1、弱点 超、抵抗力の欄は空、特殊能力の欄はない | 同じ |
| 図版の説明 | 「ダメージを与えた後 自分を「ねむり」状態にする。」（「後」のあとの読点は読めない） | 「ダメージを与えた後、自分を「ねむり」状態にする。」 |
| 「ワザ」欄（最新の説明） | 「●ぐうたらこうげき ダメージを与えた後、自分を「ねむり」状態にする。」 | 同じ文面（実装は `play_text_ja` にしたがう） |
| 解説 | 「でも相手にダメージを与えたら、自分がねむり状態になってしまいますので、ポケモンチェックでは何がなんでも表を出して、ねむりから回復したいものです。」ほか | — |

- 同じページの上の 2 枚（第4弾ロケット団のヤドン LV.16、第3弾化石の秘密のヤドン LV.18）は別のカードです。
- 最新の説明は、R団のカビゴンの「たおれこむ」の最新の説明（p.245）と同じ文面です（kyuura の写しのたおれこむの文面は「与えたあと」で、印刷の文面の違い）。
- 解説の「相手にダメージを与えたら」は、Z23 の「条件」の読み方とも読めますが、ダメージを与えなかった場面を書いていないので Z23 は決まりません（docs/unresolved-research-v0.18b.md 3 章）。
- kyuura（`adf9710`）には、このカードの最新の説明（`LD-`）・照合（`CC-`）の記録がありません（kyuura への報告事項。docs/research-alignment-v0.18a.md 11.4）。

## 3. 実装

| 変えたもの | 内容 |
|---|---|
| `kyuura_engine/effects.py` | `AttackKey("PMCG6-044", 0)` → `AttackEntry(DamageAndSelfSleep(), "ぐうたらこうげき", text_ja=…, play_text_ja=…, source="P43 p.155")`（+9 行。コメントを含む） |
| `kyuura_engine/cards.py` | `POOL_KEYS` に `pool_v0_18c`（+1 行） |
| `scripts/extract_kyuura_cards.py`・`kyuura_engine/data/kyuura_cards.json` | `POOL_V0_18C`。写しのコミットは `ecb2d69` のまま（`python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura`、`--check` で一致） |
| `kyuura_engine/data/card_verification.json` | PMCG6-044 の照合の記録 |
| `tests/helpers.py` | `SABRINAS_SLOWPOKE` |
| `tools/stress_engine.py` | 組 `slowpoke`・`slowpoke_mixed` を `ALL_SCENARIOS` の最後に加えた。Z23 の止まり方の確かめを、たおれこむだけから、p.321 の計算（弱点・抵抗力・プラスパワー・ディフェンダー）を場から組み立てる形に広げた（ナツメのヤドンはポケモンパワーを持たないので `POWER_USERS` は変えていない） |

- 依頼の条件との対応:
  - `engine.py` を変えない: 変えていない。
  - `kernel.py` をできれば変えない: 変えていない（`resolution/` のどのファイルも変えていない）。
  - カードごとの分岐を作らない: 登録だけで、処理はたおれこむと同じ型・同じ要素の並び。
  - Z23 を解決済みとして扱わない: 既存の問い `effect_after_no_damage`（`UNRESOLVED_EFFECT_AFTER_NO_DAMAGE`）で止める。
  - `resolution/v013_checks.py`・`resolution/contract.py` への依存を増やさない: 実装の型は v0.17b の `DamageAndSelfSleep` で、`v013_checks.VERIFIED` に入れていない。v0.13 の約束（`resolve`・`resume`）を上書きしていない（アダプタを通らない）。比べる方法 `legacy` でも、VERIFIED にない型としてすべての結果を試す方法で確かめる（v0.17d の振り分け）。
- たおれこむについての kyuura の裁定（CR-COLLAPSE-ORDER・CR-COLLAPSE-SELF-KO・CR-COLLAPSE-AFTER-KO-DEFENDER・CR-COLLAPSE-SPECIAL-CONDITIONS）は、kyuura ではたおれこむのカードの記録です。ぐうたらこうげきは最新の説明が同じ文面なので同じ処理になりますが、kyuura がこのカードに当てはめた記録ではありません（エンジンの当てはめ。報告事項）。

## 4. 新しいカードの裁定の扱い

| 場面 | 処理 | 根拠・分類 | テスト |
|---|---|---|---|
| 相手に 30 → 自分をねむり | 要素の順番どおり | p.155 の最新の説明（たおれこむの CR-COLLAPSE-ORDER と同じ文面。CONFIRMED） | `test_damage_then_self_sleep` |
| 弱点（ワンリキー 60）・ディフェンダー（10）・プラスパワーと抵抗力（10） | ダメージを与えたのでねむり | p.321 | `test_weakness_and_defender_neighbours`・`test_plus_power_against_resistance_is_not_stopped` |
| 相手をきぜつさせた | ねむり（ダメージを与えた） | CR-COLLAPSE-AFTER-KO-DEFENDER の当てはめ（SUPPORTED） | `test_knocking_out_the_defender_still_sleeps` |
| ほのおのかべの 10 で自分が HP 以上 | ねむりにしない | CR-COLLAPSE-SELF-KO の当てはめ（SUPPORTED。p.309・p.89） | `test_self_knocked_out_by_fire_wall_is_not_put_to_sleep` |
| こんらん（「おもて」で処理・「うら」で自分に 20、弱点 超で 40）・ねむり・マヒでは宣言できない | v0.3b・v0.3c の規定 | p.309・p.311・p.322（CR-COLLAPSE-SPECIAL-CONDITIONS の当てはめ） | `test_conditions_of_slowpoke` |
| 抵抗力 超 の相手で 0（Z23-b） | 宣言の前に止める | UNRESOLVED（Z23） | `test_z23_b_resistance`（4 種類の相手） |
| 「ダメージを受けない」状態（Z23-a）・「とうめい」（Z23-c） | 宣言の前に止める | UNRESOLVED（Z23） | `test_z23_a_and_c`・`test_every_preflight_mode` |

新しい裁定 id・停止コードはありません（エンジンの未解決の裁定は 24 件、停止コードは 18 件のまま）。

## 5. 確かめたこと

- tests/test_sabrinas_slowpoke_v0_18c.py（17 件）: 登録と再利用（型・要素の並びがたおれこむと同じ、新しい型がない）・ワザの処理・Z23 の停止（場合ごと・先読みの方法ごと）・正式な開始（`new_game`。60 枚・サイド 6 枚）からの 80 対戦（不変条件・ログの監査・書き出しの監査・乱数はコインだけ・保存と再開・固定値）。
  - 80 対戦で、ぐうたらこうげきを使い自分をねむりにした場面、Z23 で止まった場面（抵抗力の Z23-b を含む）、ねむりのヤドンがワザを宣言できない場面が、どれも 1 回以上起こったことを確かめる（起こらない試験を成功と数えない）。Z23 で止まった場面は、どれも場から組み立てた場合（Z23-a・Z23-b（抵抗力・ディフェンダー）・Z23-c）のどれかに当たる。
- tests/test_unresolved_research_v0_18b.py の `TargetGoneIsUnreachableTest`（Z23-d が起こらない形）は、ぐうたらこうげきも対象に含めて通る。
- ストレス実行（`python3 tools/stress_engine.py --scenario slowpoke --scenario slowpoke_mixed --seeds 40`）: 80 対戦・内部の誤り 0・監査の問題 0。Z23 で止めた 134 回のうち 132 回が抵抗力で 0 になる場合で、どれも場から確かめた。
- 固定した v0.17 との比較・変異試験・性能は docs/v0.18-verification.md。
