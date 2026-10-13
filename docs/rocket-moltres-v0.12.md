# R団のファイヤーのカードとワザ「ほのおのかべ」の照合と裁定（v0.12）

v0.12 で R団のファイヤー（PMCG5-020。ジム拡張第1弾 リーダーズスタジアム。たねポケモン）のワザ「ほのおのかべ」を対戦で使えるようにするために、『ポケモンカードオフィシャルブック2000』[P43] で確かめた記録です。ポケモンパワー「ふしちょう」は [phoenix-v0.12.md](phoenix-v0.12.md)、番をまたいではたらくワザの効果の仕組みは [temporary-attack-effects-v0.12.md](temporary-attack-effects-v0.12.md)、設計は [architecture-v0.12.md](architecture-v0.12.md)、確かめた結果は [v0.12-verification.md](v0.12-verification.md) です。

## 1. カードの照合

確かめ方は [phoenix-v0.12.md](phoenix-v0.12.md) 1 章と同じ（p.82 を 300dpi の画像で読み、図版と最新の説明は拡大した）。

| 項目 | p.82（図版・見出し） | kyuura の写し（`ecb2d69`） | 一致 |
|---|---|---|---|
| 名前・段階 | 「たねポケモン R団のファイヤー」 | R団のファイヤー・basic | 同じ |
| LV・HP | LV.26／HP60 | LV.26（`jp_print.level`）・60 | 同じ |
| タイプ | 炎 | fire | 同じ |
| 弱点 | 欄は空 | なし | 同じ |
| 抵抗力 | 闘 −30 | fighting −30 | 同じ |
| にげる | 無無（2） | 2 | 同じ |
| 特殊能力 | 【特殊能力】ふしちょう | `pokemon_power`「ふしちょう」 | 同じ（文面は [phoenix-v0.12.md](phoenix-v0.12.md) 3 章） |
| ワザ | ほのおのかべ（炎炎炎）40 | 「ほのおのかべ」fire×3・40 | 同じ |
| ワザの文面 | 図版（印刷の文面）「次の相手の番、このカードが相手のワザによるダメージを受けた時、（このカードが「きぜつ」するしないにかかわらず）相手にも10ダメージ」 | 同じ（かっこは ASCII） | 同じ（印刷の文面）。最新の説明とは違う（2 章） |
| 収録 | 「ジム拡張第1弾リーダーズスタジアム」 | PMCG5・リーダーズスタジアム | 同じ |

照合の記録は kyuura_engine/data/card_verification.json の PMCG5-020（`status` は「不一致あり」。印刷の文面と最新の説明の違いを `mismatches` に 2 件）。抽出の対象は scripts/extract_kyuura_cards.py の `POOL_V0_12`（`["PMCG5-020"]`）で、写しを作り直し、`--check` で確かめた（参照するコミットは `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691` のまま）。

## 2. 原文と、印刷の文面と最新の説明の違い

| 誌面 | 原文 |
|---|---|
| p.82 「ワザ」欄（最新の説明） | 「●ほのおのかべ 次の相手の番、このカードが相手のワザによるダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）相手に10ダメージを与える。」 |
| p.82 解説 | 「「ほのおのかべ」は、「R団のファイヤー」がワザによるダメージを受けたとき、そのダメージを与えた相手の対戦ポケモンに10ダメージを与える効果がついています。この10ダメージは、弱点・抵抗力の影響を受けます。これは忘れないようにしましょう。」 |
| p.89 わるいカメール「こうらがえし」（最新の説明） | 「次の相手の番、このカードが相手のワザによってダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）そのポケモンにも同じダメージを与える。（ダメージ以外の効果は与えない）」 |
| p.89 ワザ解説「相手の番ではたらく効果「こうらがえし」」 | 「このワザの効果は、相手の番に受けたワザによるダメージをダメージを与えたポケモンに与えます。「こうらがえし」によって与えるダメージのタイミングは、相手のワザによるダメージの処理を行った後で、ダメージを与えます（相手のワザによるダメージ以外の効果の処理は、その後でおこないます）。」「「ふきとばし」を受けた場合 … 「ふきとばし」のダメージを受けたタイミングでは、まだバトル場にいるので、「こうらがえし」の状態は消えません。したがって、「こうらがえし」の状態によるダメージを与えた後に「ふきとばし」の効果で「わるいカメール」はベンチにもどることになります。」「「スターブーメラン」を受けた場合 … 「スターブーメラン」のダメージを受けたタイミングで、「こうらがえし」の状態によるダメージを与えます。その後、相手はそのダメージできぜつしなければ「スターブーメラン」の効果で手札にもどることになります。」「■効果の対象：ワザを使ったポケモン自身 ■効果の持続：次の相手の番の最後 ■同じタイプのワザ：「クロスカウンター」」。図「自分の番 → 相手の番」「効果が持続」「この相手の番の最後に、「こうらがえし」の効果は消える」「ベンチにもどると、効果は消える」 |
| p.89 解説 | 「「わるいカメール」が弱点とする雷ポケモンが相手の場合は、ワザのダメージが2倍になるため、2倍のまま相手にダメージが返ります。逆に相手が「わるいカメール」の水を弱点にしていた場合は、「こうらがえし」で返すダメージは「ワザによるダメージ」なので、2倍になって相手に返ります。」 |
| p.321「8 ワザによるダメージと効果」 | 「ワザによってもたらされたダメージは、「ワザによるダメージ」と呼ばれます。」（v0.10 で読んだ） |
| p.319・p.321 | 「計算結果、ダメージが0やマイナスの数字になったときは、ポケモンは「ダメージを受けなかった」ことになります」（v0.9 で読んだ） |
| p.322〜p.323「11 特殊状態以外の「持続する効果」」 | 「「ラッキー」の「まるまる」などのようなワザは、自分自身に「持続する効果」を与えます。」「通常、「持続する効果」を受けたポケモンがベンチにもどったら、その「持続する効果」は消えてなくなります。」「「持続する効果」を受けているポケモンが場をはなれたら、「持続する効果」は消えてなくなります。」「…手札にもどったポケモンのカードを再び場に出したりしても、一度消えた「持続する効果」は復活しません。」「「持続する効果」は、特殊状態と重複することがあります。」（v0.4b で読んだ） |
| p.324 | 「1つのワザや特殊能力などによって引き起こされることがらによって複数のポケモンが「きぜつ」した場合、それらのポケモンは「同時に「きぜつ」した」ことになります。」 |

印刷の文面（kyuura の写し）「…受けた時、（このカードが「きぜつ」するしないにかかわらず）相手にも10ダメージ。」と最新の説明「…受けたとき、（それによってこのカードが「きぜつ」しても、）相手に10ダメージを与える。」は、R団のファイヤーがきぜつしても与えることで同じと読める。p.6 により最新の説明にしたがう（`AttackEntry.play_text_ja`）。kyuura の写しの値は登録の照合（`AttackEntry.text_ja`）にだけ使う。

p.82 の解説は、与える相手を「そのダメージを与えた相手の対戦ポケモン」、計算を「弱点・抵抗力の影響を受けます」とする。p.89 の「こうらがえし」は、同じ「次の相手の番、このカードが相手のワザによって（による）ダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）」の形で、ワザ解説が時点・持続・消える契機・返すダメージの分類を説明している。「ほのおのかべ」の時点・持続・消える契機は、この解説（同じ形のワザ）にしたがった（SUPPORTED）。

## 3. 裁定（W1〜W30）

分類は [phoenix-v0.12.md](phoenix-v0.12.md) 4 章と同じ。テストは tests/test_rocket_moltres_v0_12.py（盤面を直接作る。`Registration`・`EffectCreation`・`Trigger`・`KnockOut`・`CoinIndependence`・`SaveRestoreAndInvariant` の各 `…Test`）・tests/test_unresolved_boundaries_v0_4e.py の `RetaliationDoubleKnockoutBoundaryTest`・tests/test_moltres_games_v0_12.py（自然な対戦）。

### 3.1 基本（W1〜W10）

| ID | 論点 | 裁定 | 分類 | 原典・根拠 | 実装 | テスト |
|---|---|---|---|---|---|---|
| W1 | 必要なエネルギー | 炎炎炎 | CONFIRMED | p.82 の図版 | データのまま（ワザの宣言の確認は v0.1 から） | `test_registered_with_the_latest_description` |
| W2 | 基本となるダメージ | 40（相手の対戦ポケモン。p.321 の順番） | CONFIRMED | 図版の 40 | `DamageAndRetaliation.resolve` が `damage_opponent_active(state, use, 40)` | `test_damage_then_effect_on_itself` |
| W3 | 追加効果の文面 | 最新の説明にしたがう | CONFIRMED | p.82・p.6 | `AttackEntry.play_text_ja` は最新の説明、`text_ja` は写しの印刷の文面（照合用） | `test_registered_with_the_latest_description`・tests/test_effects.py の `test_attacks_with_text_follow_the_verified_latest_description` |
| W4 | 効果がはたらき始める時点 | 次の相手の番（ワザを使った番の次の番）の始まりから | CONFIRMED | 「次の相手の番」 | `Retaliation(created_turn=番, active_turn=番 + 1, …)`。`persistent.retaliation` は `active_turn` が今の番のときだけ返す（ワザを使った番の残り・ポケモンチェックでははたらかない） | `test_damage_then_effect_on_itself`・`test_not_working_on_other_turns` |
| W5 | 効果が終わる時点 | 次の相手の番の終わり | SUPPORTED | p.89 の同じ形のワザの解説「効果の持続：次の相手の番の最後」「この相手の番の最後に、「こうらがえし」の効果は消える」。最新の説明は「次の相手の番」とだけ書く | `_end_turn` の `remove_expired_persistent_effects`（ついているトレーナーのトラッシュのあと・ポケモンチェックの前。v0.4b の「かたまる」と同じ）。ログ `persistent_effect_removed`（`reason` `expired`） | `test_expires_at_the_end_of_the_next_opponent_turn`・自然な対戦（期限で消えた 170） |
| W6 | ワザを使ったあとベンチにもどる | 効果は消える | CONFIRMED | p.322「ベンチにもどったら…消えてなくなります」。p.89 の図「ベンチにもどると、効果は消える」 | 既存の契機（`forced_switch`・`retreat`・`switch`）。R団のファイヤーの持ち主は相手の番に「にげる」・トレーナーを使えないので、起こるのはふきとばし（`forced_switch`） | `test_attacker_knocked_out_skips_its_own_heal_but_not_the_whirlwind`（ふきとばし）・ストレス実行（`forced_switch` 8） |
| W7 | ワザを使ったあと特殊状態になる | 効果は消えない。特殊状態でもはたらく | CONFIRMED | p.323「「持続する効果」は、特殊状態と重複することがあります。」。特殊状態の規定に持続する効果を消すとは書かれていない。ワザの効果で特殊能力ではないので、ねむり・マヒ・こんらんの「使えない」も関係しない | 特殊状態と別の項目（`persistent_effects`）に持つ | `test_special_conditions_of_the_holder_do_not_stop_it` |
| W8 | ワザを使ったあときぜつする | 効果は消える | CONFIRMED | p.322「場をはなれたら…消えてなくなります」 | `_knock_out` の `remove_persistent_effects(..., KNOCK_OUT)` | `test_return_to_hand_and_play_again_does_not_bring_it_back`・自然な対戦（きぜつで消えた 2） |
| W9 | 「ふしちょう」で手札にもどった | 効果はない（きぜつで消えている） | CONFIRMED | 同上 | 手札のカードは効果を持たない | `test_return_to_hand_and_play_again_does_not_bring_it_back` |
| W10 | 再び場に出された | 効果は復活しない | CONFIRMED | p.322「…手札にもどったポケモンのカードを再び場に出したりしても、一度消えた「持続する効果」は復活しません。」 | 新しい場のポケモン（新しい `pokemon_id`）に効果はない | 同上 |

### 3.2 相手にダメージを与える（W11〜W20）

| ID | 論点 | 裁定 | 分類 | 原典・根拠 | 実装 | テスト |
|---|---|---|---|---|---|---|
| W11 | 条件は「相手のワザによるダメージ」か | そう。こんらんの 20・どく・特殊能力のダメージ（「はんげき」）・ダメージカウンターの移動では、はたらかない | CONFIRMED | 「相手のワザによるダメージを受けたとき」。p.321「8」（どくは「ワザによるダメージ」としてあつかわれない）。p.320（カウンターの移動は「ダメージを受けた」ことにならない） | `deal_attack_damage`（ワザのダメージの要素だけが通る）で、受けるポケモンの持ち主がワザを使ったプレイヤーでなく、最終ダメージが 0 より大きいとき、ダメージをのせる直前に `persistent.retaliation` を見て `AttackUse.retaliations` に加える | `test_counter_damage_to_the_attacker`・`test_counterattack_of_the_attacker_and_no_chain`・`test_damage_swap_is_not_damage` |
| W12 | ワザの説明（効果）によるダメージでもはたらくか | はたらく（ワザによるダメージなら、基本となるダメージか説明によるダメージかを区別しない） | SUPPORTED | p.321「ワザによってもたらされたダメージは、「ワザによるダメージ」と呼ばれます」 | ワザのダメージの要素はすべて `deal_attack_damage` を通るので区別しない。対応カードで相手の対戦ポケモンにダメージを与えるのは 1 つのワザにつき 1 回 | —（区別する処理がない。説明でダメージの量が決まるワザ（からてチョップ・みだれづきなど）も同じ `deal_attack_damage` を通る） |
| W13 | 最終ダメージが 0 | はたらかない | CONFIRMED | p.319・p.321「ダメージが0やマイナスの数字になったときは…「ダメージを受けなかった」」 | 最終ダメージが 0 より大きいときだけ加える。「ダメージを受けない」（かたまる）・「とうめい」で受けなかったときも加えない（R団のファイヤーにはどちらもないが、同じ経路） | `test_zero_damage_does_not_trigger`（抵抗力 闘 −30 で 0） |
| W14 | 与えるダメージの量 | 10（基本となるダメージ。p.321 の 1 段階） | CONFIRMED | 「相手に10ダメージを与える」 | `Retaliation.amount`（10。`DamageAndRetaliation(10)`） | `test_counter_damage_to_the_attacker` |
| W15 | 弱点 | 計算する（R団のファイヤーのタイプ 炎） | CONFIRMED | p.82 の解説「この10ダメージは、弱点・抵抗力の影響を受けます」。p.89「「ワザによるダメージ」なので、2倍になって」 | `deal_attack_damage`（発生源は R団のファイヤー。`retaliation_use`） | `test_weakness_applies`（バタフリー 弱点 炎 → 20）・自然な対戦（弱点 5） |
| W16 | 抵抗力 | 計算する | CONFIRMED | 同上 | 同上 | `test_resistance_applies`（炎の抵抗力 −30 のテスト専用の記録で 0。対応カードに炎の抵抗力を持つポケモンはない） |
| W17 | プラスパワー・ディフェンダー | R団のファイヤーのワザによるダメージとして計算する。受けるポケモン（ワザを使ったポケモン）についているディフェンダーで −20。R団のファイヤーについたプラスパワーはこの番にない | SUPPORTED | p.321（ワザによるダメージの計算の順番）・p.257（プラスパワーは「あなたの番の終わりにトラッシュする」）・p.89（返すダメージは「ワザによるダメージ」） | `deal_attack_damage` の p.321 の段階（v0.2c・v0.2e）。プラスパワーは持ち主の番に使って、その番の終わりにトラッシュするので、相手の番に R団のファイヤーについていることはない（未到達） | `test_defender_on_the_attacker_applies` |
| W18 | かがくへんかガス | 止まらない | CONFIRMED | かがくへんかガスは特殊能力を消す（p.48）。「ほのおのかべ」はワザの効果 | 何も見ない | `test_chemical_gas_does_not_stop_it`（どちらの場のベトベトンでも） |
| W19 | 「とうめい」（v0.9） | ワザによるダメージなので、受けるゴーストの「とうめい」がはたらく。コインはゴースト側（番のプレイヤー） | SUPPORTED | p.160（ゴーストの「とうめい」。「このカードがワザによってダメージや効果を受けるとき」。コインは「ゴースト」側のプレイヤー）・p.89（返すダメージは「ワザによるダメージ」） | `deal_attack_damage` の `attack_reaches`（v0.9）をそのまま通る | `test_transparency_of_the_attacker`・自然な対戦（受けなかった 10） |
| W20 | 「はんげき」（v0.10）との違い | 「ほのおのかべ」のダメージは R団のファイヤーのワザによるダメージ（弱点・抵抗力・プラスパワー・ディフェンダー・「とうめい」を計算する）。「はんげき」のダメージは特殊能力によるダメージ（どれも計算しない）。「ほのおのかべ」のダメージを受けたカイリキーの「はんげき」ははたらく。「はんげき」のダメージでは「ほのおのかべ」ははたらかない（連鎖しない） | SUPPORTED | p.82 の解説・p.89・p.321「8」・p.192（v0.10 の C13） | `counterattack`（v0.10）は流用していない。`_apply_retaliation` は `deal_attack_damage` を通し、その最後に `finish_damage_elements`（受けたポケモンの「はんげき」）。比較の表は [temporary-attack-effects-v0.12.md](temporary-attack-effects-v0.12.md) 5 章 | `test_counterattack_of_the_attacker_and_no_chain`・自然な対戦（「ほのおのかべ」のあとの「はんげき」16） |

### 3.3 順番ときぜつ（W21〜W25）

| ID | 論点 | 裁定 | 分類 | 原典・根拠 | 実装 | テスト |
|---|---|---|---|---|---|---|
| W21 | 元のワザの処理のどこで与えるか | 相手のワザのダメージの処理（自分へのダメージ・「はんげき」を含む）のあと、ダメージ以外の効果（コイン・特殊状態・入れ替え・回復）の前 | SUPPORTED | p.89 の解説「相手のワザによるダメージの処理を行った後で、ダメージを与えます（相手のワザによるダメージ以外の効果の処理は、その後でおこないます）」と「ふきとばし」「スターブーメラン」の例 | `finish_damage_elements`（v0.10 の「はんげき」と同じ時点。ワザの実装が効果の前に呼ぶ・エンジンが `resolve`・`resume` のあとに呼ぶ）。呼ばずに効果に進むと `RuntimeError`（`_require_damage_elements_finished` は `retaliations` も見る） | `test_order_after_damage_before_effects`（どくばりのコインより先・でんげきの自分へのダメージより後） |
| W22 | 与える R団のファイヤーがそのダメージできぜつする | それでも与える | CONFIRMED | 「（それによってこのカードが「きぜつ」しても、）」 | きぜつの処理はワザのあと（`engine._finish_attack`。変えていない）。そのあと「ふしちょう」 | `test_moltres_knocked_out_still_hits`・自然な対戦 |
| W23 | 「ほのおのかべ」のダメージでワザを使ったポケモンがきぜつする | ワザのあとのきぜつの判定できぜつする（サイドは R団のファイヤーの持ち主）。きぜつしたワザを使ったポケモン自身への効果（回復）は処理しない。相手への効果（ふきとばし）は処理する。ワザを使ったポケモンが同じワザの自分へのダメージですでに HP 以上なら与えない | SUPPORTED | p.89「その後、相手はそのダメージできぜつしなければ「スターブーメラン」の効果で手札にもどる」・p.309「処理の対象がなくなってしまっている場合、その内容は無視して」・v0.10 の C15・C16 | `_apply_retaliation`（すでに HP 以上なら `retaliation_skipped`）。回復は `_remove_attacker_counters` が `drain_heal_skipped`（v0.10）。ふきとばしの決定を待つ間、ワザを使ったポケモンが HP 以上で場に残ることは v0.10 の例外（`_counter_knocked_out_attacker_awaiting`）で許し、`retaliation` のダメージも数える | `test_attacker_knocked_out_by_the_counter_damage`・`test_attacker_knocked_out_skips_its_own_heal_but_not_the_whirlwind`・`test_attacker_already_knocked_out_by_its_own_damage`・自然な対戦（「ほのおのかべ」できぜつ 6） |
| W24 | 両方がきぜつする（R団のファイヤーがワザのダメージで、ワザを使ったポケモンが「ほのおのかべ」のダメージで。「ほのおのかべ」がなければきぜつしない） | 原典で決められない（2 匹が「同時に「きぜつ」した」ことになるか） | **UNRESOLVED** | p.324「1つのワザや特殊能力などによって引き起こされることがら」に、前の番のワザが与えた効果のダメージが含まれるかが書かれていない。同時でなければ、どちらを先に処理するかの規定がない。同時かどうかで、サイドを取る順番・バトル場に出す順番（番でないプレイヤーが先。p.323）・勝ち負け（両方が最後のサイドを取る・両方が出せない → サドン・デス。p.311）が変わる。v0.10 の C18 と同じ問い | ワザの宣言の前（G37 の確認のあと、こんらんのコインの前）に `UnsupportedError`（`UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`。`effects.retaliation_double_knockout_problem`）。ワザのダメージの候補（`damage_profile` の `pairs()`。同じコインの結果でいっしょに起こる組）と状態を変えない計算（`preview_attack_damage`）で求めるので、コインの結果で受け付けるかが変わらない。「ほのおのかべ」のダメージで、ワザを使ったポケモンの「はんげき」が R団のファイヤーに与える 10 も数える。勝者を推測で決めない。「こんじょう」で解決したことにしない | `RetaliationDoubleKnockoutBoundaryTest`・`test_hurricane_punch_is_stopped`・`CoinIndependenceTest`・自然な対戦（止まった 1） |
| W25 | 次の相手の番に何回もワザを受ける | ワザは 1 つの番に 1 回（p.309）なので、はたらくのは 1 回まで。1 つのワザで R団のファイヤーがダメージを受けるのも 1 回 | CONFIRMED（ワザは 1 回）・未到達（1 つのワザで 2 回） | p.309 | 効果は消えずにその番の終わりまで残る（はたらいたことで消さない）。1 つのワザで「はんげき」と「ほのおのかべ」が合わせて 2 つ以上はたらくと `RuntimeError`（v0.10 の C34・C35 と同じ問い。今の対応カードでは起こらない） | `test_counter_damage_to_the_attacker`（はたらいたあとも効果は残る） |

### 3.4 加えた論点（W26〜W30）

| ID | 論点 | 裁定 | 分類 | 原典・根拠 | 実装 | テスト |
|---|---|---|---|---|---|---|
| W26 | 「ほのおのかべ」のダメージで、番のプレイヤーのサカキのカイリキーが HP 以上になる | 「相手のワザによるダメージ」で「きぜつ」するので「こんじょう」を使える（番のプレイヤーが決める） | SUPPORTED（未到達） | v0.11 の G3（「相手のワザによるダメージで」）・p.89（返すダメージは「ワザによるダメージ」） | `_ko_prevention_offer` は v0.12 から番のプレイヤーのポケモンも見る（記録 `ko_prevention_able` は `_apply_retaliation` がきっかけのワザと共有する）。ハリケーンパンチ（最大 90）では R団のファイヤー（HP 60）がきぜつしうるので、対応カードでは W24 が先に止める | `test_turn_player_guts_after_counter_damage`（テスト専用の効果）・`test_hurricane_punch_is_stopped` |
| W27 | 同じポケモンが続けて使う | 前の効果は期限で消えているので重ならない。新しい効果になる | CONFIRMED | W4・W5 | 番 N の効果は番 N+1 の終わりに消え、番 N+2 のワザで新しい効果を与える。不変条件が重複を拒否する | `test_used_again_after_it_expired` |
| W28 | 相手へのダメージを与えなかった（相手が「ダメージを受けない」・「とうめい」で受けなかった・最終ダメージ 0） | それでも自分への効果は与える | SUPPORTED | 説明に「ダメージを与えたら」がない（v0.4b のかたまる・v0.4d のメガドレインとの違い） | `DamageAndRetaliation.resolve` は `DamageResult` を見ない | `test_effect_even_if_the_damage_is_prevented_or_evaded` |
| W29 | ワザを使ったあと、相手の「はんげき」で R団のファイヤーが HP 以上になった | きぜつするので効果を与えない（与えても、きぜつで消える） | SUPPORTED | p.89「その後、相手はそのダメージできぜつしなければ」・p.309・p.322 | ログ `persistent_effect_skipped`（`reason` `knocked_out`）。そのあと「ふしちょう」（番のプレイヤーが決める） | `test_knocked_out_by_counterattack_on_its_own_turn`（tests/test_phoenix_v0_12.py）・自然な対戦（1） |
| W30 | 乱数 | 「ほのおのかべ」は乱数を使わない。「とうめい」のコインだけ | 実装上の仮定（説明にコインがない） | — | `retaliation_double_knockout_problem` は乱数を使わない | `test_damage_then_effect_on_itself`・`test_acceptance_does_not_depend_on_the_coins` |

## 4. ログ

| イベント | いつ | 項目 |
|---|---|---|
| `persistent_effect_added` | ほのおのかべのダメージ（と相手の「はんげき」）のあと | v0.4b の形（`player`・`pokemon`・`pokemon_id`・`persistent_effect`（`retaliation`）・`source_card`・`source_player`・`active_turn`・`effect`（ワザ））。与えるダメージ（`amount`）・ワザの位置は状態の効果（`Retaliation`）にある |
| `persistent_effect_skipped` | 「はんげき」で HP 以上になったので効果を与えない（W29） | `player`・`pokemon`・`pokemon_id`・`persistent_effect`・`effect`・`reason`（`knocked_out`） |
| `retaliation` | 次の相手の番に、相手のワザのダメージの処理のあと（W21） | `player`・`pokemon`・`pokemon_id`（効果を持つポケモン）・`persistent_effect`・`source_card`・`effect`（効果を与えたワザ）・`trigger`（きっかけのワザ）・`attacker`・`attacker_pokemon`・`attacker_pokemon_id`・`amount`（基本となるダメージ） |
| `damage`（`retaliation` True） | `retaliation` のすぐあと（または `damage_prevented`・`evade_check`・`attack_evaded`） | v0.2f の `damage` の項目に `retaliation`・`effect`・`pokemon_id`（受けたポケモン）を加えたもの |
| `retaliation_skipped` | ワザを使ったポケモンが自分へのダメージですでに HP 以上（W23） | `retaliation` と同じ項目（`amount` なし）と `reason`（`knocked_out`） |
| `persistent_effect_removed` | 期限・きぜつ・ベンチにもどる（v0.4b） | `reason`: `expired`・`knock_out`・`forced_switch` など |

## 5. kyuura の記録との違い（報告事項。kyuura は変更していない）

- kyuura の写しの「ほのおのかべ」の文面（`pokemon.attacks[0].text.ja`）は印刷の文面で、最新の説明と区別した記録がない。誤りとは決めない（照合の記録の `mismatches`）。
- kyuura の rule_history.json・rule_differences.json には、「次の相手の番」にはたらくワザの効果（p.89 の「相手の番ではたらく効果」）の時点・持続・消える契機の記録がない（v0.4b の報告と同じ種類）。
