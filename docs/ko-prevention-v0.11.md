# きぜつの判定ときぜつの処理のあいだ（v0.11）

v0.11 で、ワザのあとのきぜつの判定から実際のきぜつの処理（トラッシュ・サイド・交代・勝ち負け）までのあいだに、原典にもとづく特殊能力の使用（プレイヤーの選択・コイン・状態の変更）を挟めるようにしました。最初の対応カードはサカキのカイリキーの「こんじょう」（[guts-v0.11.md](guts-v0.11.md)）です。設計の比較は [architecture-v0.11.md](architecture-v0.11.md)。

汎用のイベントの仕組み（購読・発行）は作っていません。v0.2a の決定（`push_decision`・再開先 `_RESUMERS`）と、v0.10 までのワザの処理の境界（`deal_attack_damage`・`finish_damage_elements`・`_finish_attack`）をそのまま使い、きぜつの処理の前に 1 か所の境界（`_ko_prevention_offer`）と 1 つの決定の種類（`KO_PREVENTION`）を加えただけです。

## 1. 処理の順番

v0.10 までのワザの処理（`engine._use_attack`）:

1. 宣言の前の確認（`effect.problem`・こんらんのダメージの変更効果・C18・v0.11 の G37）
2. 宣言（`attack`）→ こんらんのコイン
3. ワザの要素（`effect.resolve`。ダメージ → 「はんげき」（`finish_damage_elements`）→ ダメージ以外の効果）
4. ワザのあと（`_finish_attack`）: HP 以上のポケモンをきぜつさせる → サイド → 勝ち負け → 交代 → 番の終わり

v0.11 の 4:

```
_finish_attack(state, use)
  └ _ko_prevention_offer(state, use)       # きぜつの判定: こんじょうを使えるポケモンがいるか
       ├ いる → push_decision(KO_PREVENTION, player=持ち主, options=(番号,), min 0, max 1, resume="knock_out")
       │         └（持ち主が答える）_resume_knock_out
       │              ├ 選ばない → ko_prevention_declined
       │              └ 選ぶ     → ko_prevention_declared → coin_flip → ko_prevented（残り HP 10）／ko_prevention_failed
       │              └ _knock_out_after_attack(state)
       └ いない → _knock_out_after_attack(state)   # v0.10 までの _finish_attack の本体（そのとき HP 以上のポケモンをきぜつ → サイド → …）
```

- 決定を出すのは、ワザの要素をすべて処理したあと（G2・G42。p.309「ワザを使っている最中に、…特殊能力の使用を宣言してはいけません」）。
- 答えのあとは、決定を出さずにきぜつの処理へ進む（同じきぜつの判定で 2 度決めさせない。G14）。
- 「おもて」で残り HP 10 になったポケモンは HP 未満なので、`_knock_out_after_attack` は数えない（トラッシュ・サイド・交代・勝ち負けに入らない。G33〜G36）。
- 同じワザでワザを使ったポケモンも HP 以上なら、こんじょうのあとで、そのとき HP 以上のポケモンをまとめてきぜつさせる（2 匹なら同時のきぜつ。p.324。G38）。

## 2. 使えるかの判定（`_ko_prevention_offer`）

決定を出すのは、次のすべてを満たすポケモンだけ:

| 条件 | 規定 | 求め方 |
|---|---|---|
| ワザを使われた側（番でないプレイヤー）の場のポケモン（場所は問わない） | G3・G4・G8 | `1 - state.current_player` の `in_play()` |
| HP 以上のダメージ | G2 | `damage >= hp`（いちばん上のカードの HP） |
| いちばん上のカードに「こんじょう」（`PreventKnockOutOnHeads`）が登録されている | p.310 | `effects.ko_prevention_power` |
| このワザのダメージを受けたときに、ねむり・マヒ・こんらんでなかった | G25〜G29 | `AttackUse.ko_prevention_able`（`deal_attack_damage` が、相手のワザのダメージ（最終ダメージが 0 より大きい）をのせる前に記録する） |
| はたらいているかがくへんかガスに消されていない | G31 | `continuous.suppressors_of`（`ko_prevention_suppressors`。判定を複製しない） |

- 番でないプレイヤーのポケモンが番の途中で HP 以上になるのは、そのワザのダメージを受けたときだけ（どく・こんらん・自分へのダメージ・「はんげき」は番のプレイヤー側か、ポケモンチェック）。こんじょうを持つ HP 以上のポケモンに記録がなければ、エンジンの不具合として `RuntimeError` で止める（決定をまたいで `AttackUse` が新しくなった場合など。今の対応カードでは G37 の止める処理が先にはたらくので起こらない）。
- 2 匹以上が当てはまる場合は、宣言の順番が原典で決められない（G16・G40）。今の対応カードでは起こらないので `RuntimeError`。
- ポケモンチェックのきぜつ（どく）は `_pokemon_check` → `_after_knockouts` の経路で、この境界を通らない（G7）。

## 3. 決定（`KO_PREVENTION`）

| 項目 | 値 |
|---|---|
| `kind` | `"ko_prevention"`（`decisions.KO_PREVENTION`）。段階は既存の `Phase.DECISION` |
| `player` | そのポケモンの持ち主（ワザを使われた側）。番のプレイヤー・番の番号は変えない |
| `options` | そのポケモンの番号 1 つ |
| `min_choices`・`max_choices` | 0・1（選ばない = 使わない。G10） |
| `resume` | `"knock_out"`（`engine._resume_knock_out`） |
| `context` | `"attack"` = (ワザを使ったプレイヤー, 場のポケモンの番号, カード id, ワザの位置)、`"power"` = (カード id, パワーの位置) |

- コインは答えのあと（宣言のあと）に投げる。決定を出したときは乱数を使っておらず、決定の中身にコインの結果はない（G12・G13）。
- 決定を待つ間は、ほかの操作をできない（`Phase.DECISION`。答えは `ResolveDecision` だけ。p.309・p.311）。拒否は状態・ログ・乱数を変えない（`apply_command` は複製して処理する）。
- 書き出しの形式 2 以上の `decision` で表せる（新しい形式はない。形式 9 のまま）。形式 1 は `ValueError`（黙って落とさない）。

## 4. 不変条件

- 場の形: HP 以上のダメージのポケモンが場に残るのは、v0.10 の例外（ワザの途中の決定を待つ間の「はんげき」で HP 以上になったワザを使ったポケモン）と、v0.11 の `_ko_prevention_awaiting`（この決定を待つ間の、決定の対象のポケモンと、同じワザの自分へのダメージ・「はんげき」で HP 以上になったワザを使ったポケモン）だけ。
- 決定の形（`_ko_prevention_decision_problems`）: 種類と再開先の組、選ぶ数、決定するのは番でないプレイヤー、`"attack"` が番のプレイヤーのバトル場のポケモンで今の番にそのワザのログ `attack` がちょうど 1 回、対象のポケモンのいちばん上のカードの `"power"` の位置に「こんじょう」、HP 以上、ねむり・マヒ・こんらんでない、かがくへんかガスに消されていない、最後のワザの宣言のあとにそのポケモンが受けたワザのダメージのログ（今のダメージ）があり、きぜつ・こんじょうのログがまだない。

## 5. ログ

| イベント | いつ | 項目 |
|---|---|---|
| `ko_prevention_declined` | 使わないと答えた | `player`・`pokemon`・`pokemon_id`・`power`（`PowerKey` の文字列）・`total_damage` |
| `ko_prevention_declared` | 使うと答えた（宣言。p.311 の手順 1） | 同上と `hp` |
| `coin_flip` | 宣言のすぐあと | `source: "power"`・`effect`（`PowerKey`）・`player`（持ち主）・`pokemon_id` |
| `ko_prevented` | 「おもて」 | `player`・`pokemon`・`pokemon_id`・`power`・`result`・`damage_before`・`total_damage`（HP − 10）・`remaining_hp` |
| `ko_prevention_failed` | 「うら」 | `player`・`pokemon`・`pokemon_id`・`power`・`result`・`total_damage` |

候補名の `ko_prevention_check` は使っていない（この版の `*_check`（`sleep_check`・`confusion_check`・`evade_check`）は自動のコインの結果のイベントの名前で、宣言する特殊能力の宣言とコインの結果を分けて残すため）。v0.5 の `pokemon_power`（自分の番の MAIN で宣言する特殊能力）は使っていない（ワザのあとの相手の宣言を、自分の番の宣言と混ぜないため）。決定そのものはログに残さない（v0.2a からの約束）。答えは `ko_prevention_declined`・`ko_prevention_declared` が記録する。

## 6. これからきぜつを防ぐ・きぜつするときの特殊能力を加えるときの約束

- ワザのあとのきぜつの判定で使う特殊能力は、`_ko_prevention_offer` の条件（発生源・特殊状態の判定の時点・かがくへんかガス）をカードの説明ごとに原典で確かめてから加える。きぜつの原因（ワザ・どく・特殊能力）を区別しない効果を、すべてのきぜつに当てはめない。
- ポケモンチェックのきぜつ（どく）・特殊能力のダメージによるきぜつに当てはまる効果を加えるときは、その経路（`_pokemon_check`・`_apply_counterattack`）にも同じ境界が要る。順番を原典で確かめるまで加えない。
- 同じきぜつの判定で使える効果が 2 つ以上になる場合（2 匹のこんじょう・きあいのハチマキ（A6）など）は、順番を原典で確かめるまで、宣言の前に止める（今は `RuntimeError`。G16・G40）。
- ダメージのあとに相手に効果を与えるワザを加えるときは、`AttackEffect.opponent_effect_elements` を宣言する（G37 の止める処理が使う。tests/test_guts_v0_11.py が実装と宣言の組を確かめる）。
- 「きぜつしたとき」に使う特殊能力（R団のファイヤーの［ふしちょう］など）は、きぜつの処理（トラッシュ）のあとで、別の境界になる（v0.11 では扱わない）。
