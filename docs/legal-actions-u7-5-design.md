# U7-5: 残る操作の候補・入力・実行の仕様（調査と仕様。承認前）

U7-5 の対象の 7 種類のコマンド（`PlayTrainer`・`UsePokemonPower`・`UseStadium`・`RemoveDisguise`・`DiscardFromPlay`・`RevealFaceDown`・`CheckFaceUpDeckCard`）について、宣言の入力・情報源・共通の処理を調べ、安全に実装できる単位に分けるための仕様です。候補の追加・エンジンの動作の変更はしていません。実装の単位と順序は [legal-actions-u7-5-implementation-plan](legal-actions-u7-5-implementation-plan.md) にあります。

- 構造化した仕様: [legal-actions-u7-5-design.json](legal-actions-u7-5-design.json)。表は `scripts/build_legal_actions_u7_5_design.py` が JSON と同じ元から作ります（`--write`・`--check`）
- 上位の仕様: [legal-actions-api-design](legal-actions-api-design.md)・[legal-actions-api-implementation-plan](legal-actions-api-implementation-plan.md)。U7-4 までの単位: [U7-3](legal-actions-u7-3.md)・[U7-4](legal-actions-u7-4.md)
- 名前: 指定どおり `legal-actions-u7-5-design.md`・`.json`・`legal-actions-u7-5-implementation-plan.md`。既存の `legal-actions-u7-N.md` は実装した単位の記録なので、承認前の仕様と区別するため `-design` を付けました
- コードの参照は「ファイル::名前」（関数・クラス・定数・「クラス.メソッド」）で書き、`--check` が AST で在ることを確かめます。行番号には頼りません

<!-- generated:rest-adoption begin -->
- `U7-5-DESIGN`（2026-11-08）: U7-5 の調査・仕様・実装計画（候補の追加・エンジンの動作の変更はしない）
- 状態: `proposed`・承認 `not_approved`・基点 `1ad7f6bf9b3f72212ec6799080ffecabd3cd3824`
<!-- generated:rest-adoption end -->

## 1. 対象と coverage の照合

`commands.COMMAND_TYPES` の 20 種類のうち、`legal_actions.IMPLEMENTED_KINDS` に候補の種類がないのは、この 7 種類だけです（`--check` がコマンドの型・U7 の仕様案の `operations`・`MAIN_KINDS` と照らします）。範囲はコマンドと処理の経路で決め、カードの名前の似かたでは決めていません。

ただし、7 種類で「残る操作」をすべて説明できるわけではありません。実装済みの種類の中に、候補にしていない入力の経路が 2 つ残ります。

<!-- generated:rest-residual begin -->
| ID | コマンド | 経路 | 今 | 提案 |
|---|---|---|---|---|
| R-1 | `AttachEnergy` | energy2（カツラの効果の 2 枚目の「炎」エネルギー） | U7-3 が使わない（docs/legal-actions-u7-3.md） | U7-5g（残りの経路）で、U7-3 の attach_energy に任意の 3 段目を加えるか決める（D-U75-ENERGY2） |
| R-2 | `UseAttack` | 自分のうらのバトル場のポケモンの、宣言といっしょに選ぶもの | U7-4 は示さない（unverified） | U7-5b（うらのカード）の本人の知識の扱いが決まってから見直す |
<!-- generated:rest-residual end -->

「すべてのコマンドの型に種類がある」ことだけでは U7 全体を complete と称せません。基準は 7 章の C-1〜C-6 です。

## 2. コマンドごとの調査

各コマンドの主体・段階・受理のあとの決定・効果の順序・回数の制限・規約集合による違いです。

<!-- generated:rest-commands begin -->
| コマンド | 種類 | 主体 | 段階 | 受理のあとの決定 | 順序 | 回数・禁止 | 規約集合 |
|---|---|---|---|---|---|---|---|
| `PlayTrainer` | `play_trainer` | 番のプレイヤー（player） | Phase.MAIN（checks.require_turn）。決定を待つあいだは段階が DECISION なので使えない | 錯乱ジムのコイン（使うための条件の前。「うら」なら相手がかわりに使うかの決定 ACCEPT_REQUEST）<br>相手の［ちえくらべ］を使うかの決定（REACTION_POWER。決めるのは相手）<br>リムーブ禁止ジムの追加の条件（手札 2 枚。決定 DISCARD_FROM_HAND）<br>トレーナーの効果の決定（対象・枚数・山札の検索・見たカード。push_trainer_decision）<br>サイキックコントロール: 相手のトラッシュのトレーナーを使う決定（USE_DISCARD_TRAINER）と、その内側の使用（_start_nested_trainer。事前確認をもう一度しない） | 手札から出して見せ名前を伝える（ログ play_trainer。公開）→ スタジアムなら場に出す → 錯乱ジムのコイン → 追加の条件 → 使うための条件と説明 → トラッシュ（使用中は trainer_in_use） | 1 番に何枚でも（p.310）。使う条件は effect.check_playable。禁止は trainer_use_blockers（［アレルギーかふん］・期限のある禁止）。番を終えるトレーナー（may_end_turn）がある | 手札から使う前の確かめに、続行規約の照会は見つからない（effects.py の中の呼び出しの閉包。ほかのモジュールは追っていない）。受理のあとのきぜつ・ポケモンチェックで集合の違いが出うる |
| `UsePokemonPower` | `use_power` | 番のプレイヤー | Phase.MAIN。自分の場（バトル場・ベンチ）のポケモン。相手の番・ポケモンチェック・反応の特殊能力は決定（このコマンドでない） | 特殊能力のコイン（resolve の中）<br>効果の決定（push_power_decision。再開先 power）<br>あまごいでつけた事実への反応（reactions.attach_steps）<br>使用後の処理（resolution.after_power。きぜつ・サイド・バトル場に出す決定） | うらのカードをおもてにする・指定したうらのカードをおもてにする（_reveal_for_action）→ 番 → 特殊能力の確かめ → 宣言（ログ pokemon_power）→ 回数の記録 → 処理 | 「自分の番ごとに1回」（once_per_turn。power_uses_this_turn。宣言のときに記録）。消す効果（かがくへんかガス・まきちらせ!ベトベトガス・スタンウェーブ・［いあつ］・期限のある抑止・ショックアイ） | 事前確認から続行規約の照会は見つからない（effects.py の中の閉包）。［ポイズンミスト］の量（PO の集合）は受理のあとのポケモンチェック |
| `UseStadium` | `use_stadium` | 番のプレイヤー（スタジアムの持ち主でなくてよい） | Phase.MAIN。番でないプレイヤーは使えない（require_turn） | スタジアムのコイン（activate の中。「うら」でも使ったことになる）<br>決定（再開先 stadium。セキチクシティジムのポケモン・ラジオとうの見る枚数・キョウの忍者ジムの山札のカード・エネルギーの回収）<br>空いたバトル場の勝ち負け・交代（resolution.after_stadium） | 番 → 場のスタジアム → check_activation → ログ stadium_used → 回数の記録（records_uses）→ activate | 「自分の番ごとに1回」はプレイヤーとカードの組（stadium_uses_this_turn）。SX2・LK1・RS1・STB1（トレーナーの使用の禁止） | 事前確認から続行規約の照会は見つからない |
| `RemoveDisguise` | `remove_disguise` | 番のプレイヤー | Phase.MAIN。特殊能力の宣言・トレーナーの使用ではない（回数・禁止は関係しない） | なし（決定を出さない） | 番 → 自分の場のポケモン → disguise がある → のせたカードをトラッシュ（ログ disguise_removed）→ 処理のあとの確かめ（MH1・TK1） | 回数の制限なし（説明が許す操作） | 違いなし（受理のあとの決定がない） |
| `DiscardFromPlay` | `discard_from_play` | 番のプレイヤー | Phase.MAIN。トレーナーの使用・特殊能力ではない | バトル場が空いたら勝ち負け・バトル場に出す決定（resolution.after_power） | 番 → 自分の場のポケモン → play_as_pokemon_effect・discardable_from_play → leave_lock → トラッシュ（ログ discard_from_play）→ 持続する効果を消す → after_power | 回数の制限なし。バトル場をはなれられない効果（LEAVE_ACTIVE_PREVENTED） | 受理のあとの勝ち負け・交代で、きぜつの時点の規約（S2a）は通らない（きぜつではない） |
| `RevealFaceDown` | `reveal_face_down` | 番のプレイヤー（うらのカードの持ち主） | Phase.MAIN。決定を待つあいだ・処理の途中には割りこまない | 「たねポケモン」でなければ、ついているカードといっしょにトラッシュ（ログ secret_plan_discarded）<br>空いたバトル場の勝ち負け・交代（resolution.after_power） | 番 → 自分の場のポケモン → うらである → おもてにする（ログ secret_plan_revealed。本当のカードの id を全員に公開）→ 残るか（本当のカード）→ after_power | 回数の制限なし | 違いなし（本当のカードの種類で分かれるだけ） |
| `CheckFaceUpDeckCard` | `check_face_up_deck` | どちらのプレイヤーでも（番・段階を確かめない） | 番・段階を確かめない（対戦の終わり・延長戦の前・停止はエンジンの入口で拒否）。どの場合も受け付けない | なし（受け付けない） | プレイヤー → おもての位置（NOT_FACE_UP）→ いちばん上（ALREADY_VISIBLE）→ 持ち主（ALREADY_KNOWN）→ FU2 で止める | 受け付けない | 違いなし |
<!-- generated:rest-commands end -->

全項目と既定値（型と既定値はコードから取ります）と、各値を誰がいつ知るかです。`declaration_required` は宣言に必須、`declaration_optional` は宣言といっしょに選ぶ任意の指定、`not_input` は主体（取っ手が決める）です。

<!-- generated:rest-fields begin -->
| コマンド | 項目 | 型 | 既定値 | 分類 | 意味 | 誰がいつ知るか |
|---|---|---|---|---|---|---|
| `PlayTrainer` | `player` | `int` | required | `not_input` | 使うプレイヤー | 主体（取っ手が決める） |
| `PlayTrainer` | `card` | `int` | required | `declaration_required` | 手札のトレーナーカードの uid | 本人だけが手札の中身を知る（相手は手札の枚数だけ） |
| `UsePokemonPower` | `player` | `int` | required | `not_input` | 使うプレイヤー | 主体 |
| `UsePokemonPower` | `pokemon` | `int` | required | `declaration_required` | 特殊能力を使う自分の場のポケモンの番号 | 公開（場の番号） |
| `UsePokemonPower` | `power` | `int` | 0 | `declaration_required` | 特殊能力の位置（印刷の順） | 公開（おもてのカード）。本人のうらのカードは本人だけ（ただし宣言の前におもてにする） |
| `UsePokemonPower` | `energy` | `int \| None` | None | `declaration_optional` | 説明が選ばせるエネルギーカードの uid（ついているカード、または本人の手札のカード） | ついているカードは公開。手札のカードは本人だけ |
| `UsePokemonPower` | `source` | `int \| None` | None | `declaration_optional` | 説明が選ばせる移動元の場のポケモンの番号 | 公開 |
| `UsePokemonPower` | `target` | `int \| None` | None | `declaration_optional` | 説明が選ばせる先の場のポケモンの番号（自分・相手） | 公開。相手のうらのカードを指すと、その本当のカードは相手だけが知る |
| `UsePokemonPower` | `card` | `int \| None` | None | `declaration_optional` | 特殊能力を印刷したカードの uid（「ばける」でのせたカード・［へんしん］の写し） | 公開（のせたカード・相手のバトル場のカード） |
| `UseStadium` | `player` | `int` | required | `not_input` | 使うプレイヤー | 主体 |
| `UseStadium` | `energy` | `int \| None` | None | `declaration_optional` | 説明が選ばせるエネルギーカードの uid（タマムシシティジム・ヤマブキシティジム） | 公開（場についているカード） |
| `RemoveDisguise` | `player` | `int` | required | `not_input` | 主体 | 主体 |
| `RemoveDisguise` | `pokemon` | `int` | required | `declaration_required` | のせたカードをトラッシュする自分の場のポケモンの番号 | 公開（disguise は公開のログで出した） |
| `DiscardFromPlay` | `player` | `int` | required | `not_input` | 主体 | 主体 |
| `DiscardFromPlay` | `pokemon` | `int` | required | `declaration_required` | すてる自分の場のなにかの化石・ピッピ人形の番号 | 公開（場のおもてのカード） |
| `RevealFaceDown` | `player` | `int` | required | `not_input` | 主体 | 主体 |
| `RevealFaceDown` | `pokemon` | `int` | required | `declaration_required` | おもてにする自分の場のうらのカードの番号 | うらであることは公開（secret_plan_placed）。本当のカードは本人だけ |
| `CheckFaceUpDeckCard` | `player` | `int` | required | `not_input` | 確かめたいプレイヤー | 主体 |
| `CheckFaceUpDeckCard` | `owner` | `int` | required | `declaration_required` | 山札の持ち主 | 公開 |
| `CheckFaceUpDeckCard` | `position` | `int` | required | `declaration_required` | 山札の上からの位置（0 がいちばん上） | おもての枚数（face_up_count）は公開。いちばん上は全員、下は持ち主だけが知る |
<!-- generated:rest-fields end -->

止める場面（未裁定・未対応・技術的な上限）です。コードは定数から JSON を作るときに取ります。

<!-- generated:rest-stops begin -->
| コマンド | 場面 | 参照 | コード | 説明 |
|---|---|---|---|---|
| `PlayTrainer` | MG1 | `kyuura_engine/effects.py::MIND_GAMES_CHAOS_GYM_CODE` | `UNRESOLVED_MIND_GAMES_CHAOS_GYM_ORDER` | 場に錯乱ジムと相手の［ちえくらべ］（スタジアム以外）。手札から出す前に止める |
| `PlayTrainer` | 登録なし | `kyuura_engine/engine.py::_play_trainer` | （定数でない） | 登録表にないトレーナー（trainer_problem の理由つき。処理可能性 not_implemented） |
| `PlayTrainer` | カードごと | `kyuura_engine/effects.py::TrainerEffect.check_playable` | （定数でない） | 77 の実装の未裁定・未対応（FU3・PT1・AL2・MH1 など。診断のコード表で分類） |
| `UsePokemonPower` | DV3 | `kyuura_engine/effects.py::POWER_REUSE_AFTER_DEVOLUTION_CODE` | `UNRESOLVED_POWER_REUSE_AFTER_DEVOLUTION` | 退化して戻ったカードでこの番に使っていた |
| `UsePokemonPower` | TF1・SV3 | `kyuura_engine/effects.py::copied_declared_power_problem` | （定数でない） | 写した特殊能力の使用 |
| `UsePokemonPower` | 登録なし | `kyuura_engine/engine.py::_use_pokemon_power` | （定数でない） | 登録表にない特殊能力（not_implemented） |
| `UsePokemonPower` | 秘策の対象 | `kyuura_engine/zones.py::SECRET_PLAN_LOST_TARGET_CODE` | `UNSUPPORTED_SECRET_PLAN_LOST_TARGET` | 指定したうらのカードが「たねポケモン」でない |
| `UsePokemonPower` | 割り当ての上限 | `kyuura_engine/engine.py::SECRET_PLAN_IDENTITIES_CODE` | `UNSUPPORTED_SECRET_PLAN_IDENTITIES` | 相手のうらのカードを 2 枚以上指定（受け付けるかを本当のカードによらないものにできない） |
| `UseStadium` | カードごと | `kyuura_engine/effects.py::StadiumEffect.check_activation` | （定数でない） | 9 の実装（STB1・LK1・FG1・NJ1・GG1・TG1・RB3 など） |
| `RemoveDisguise` | MH1・TK1 | `kyuura_engine/engine.py::_apply_once` | （定数でない） | 元の姿の最大HPがのっているダメージ以下（処理のあとの確かめ） |
| `DiscardFromPlay` | FD1 | `kyuura_engine/errors.py::SECRET_PLAN_HIDDEN_CODE` | `UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY` | 本人のうらのカードを指すと NOT_DISCARDABLE ではなく FD1（F-2） |
| `CheckFaceUpDeckCard` | FU2 | `kyuura_engine/faceup.py::FACE_UP_DECK_CHECK_CODE` | `UNRESOLVED_FACE_UP_DECK_CHECK` | 相手の山札の 2 枚目より下のおもてのカードを確かめてよいかが決まらない |
<!-- generated:rest-stops end -->

### 2.1 操作群ごとの要点

- **PlayTrainer**: 宣言の入力は `card` だけです。対象・コスト・枚数・山札の検索は、すべて受理のあとの決定です。
  - 手札以外から使う経路（サイキックコントロールで相手のトラッシュから、錯乱ジムの「うら」で相手がかわりに使う）は、どちらも決定（`USE_DISCARD_TRAINER`・`ACCEPT_REQUEST`）で、コマンドではありません。サイキックコントロールの内側の使用（`_start_nested_trainer`）は、使うための条件を確かめ直しません（選べるものの作成で `borrow_unusable_reason` を通しています）。
  - なにかの化石・ピッピ人形（`PlayAsPokemon`。2 件）は、ポケモンとして場に出すトレーナーの使用です。どうぐなどの場に残るカード（`stays_in_play`。29 件）とスタジアム（41 件）も同じコマンドです。
  - 番を終えるトレーナー（`may_end_turn`。5 件）は、効果の中で番を終えます。使用中のカードは `trainer_in_use` にあり、使い終わるとトラッシュします。
  - 錯乱ジムと［ちえくらべ］が同時にかかわる場面は MG1 で手札から出す前に止めます。この仕様はタイミングを決め直していません。
- **UsePokemonPower**: 宣言の入力は `pokemon`・`power` と、説明が選ばせる `energy`・`source`・`target`（と写し・のせたカードの `card`）です。
  - 選ばせるものの形は型ごとに 9 通りあります（5 章）。形を宣言する登録はなく、`check_usable` の中にだけあります。
  - 「自分の番ごとに1回」は宣言のときに記録します（コインの「うら」・決定の途中でも使ったことになる）。
  - 場に出たとき・きぜつのとき・ダメージを受けたときの特殊能力は、決定（使う機会）で使います。このコマンドでは使えません。ワザといっしょに使う特殊能力は `UseAttack`（U7-4）です。
  - 本人のうらのカードが使うときは、宣言の前におもてにします（`_reveal_for_action`）。相手のうらのカードを `source`・`target` で指すと、エンジンは本当のカードをすべて置きかえて試します（`_identity_independent`。D）。
- **UseStadium**: 番のプレイヤーなら、スタジアムの持ち主でなくても使えます。番でないプレイヤーは使えません。回数はプレイヤーとカードの組で数えます。宣言の入力は `energy`（2 つの実装だけ）です。コインのあとの選択は決定です。
- **RemoveDisguise・DiscardFromPlay**: 対象は自分の場のポケモンの番号です。どちらも説明が許す任意の操作で、特殊能力・トレーナーの使用ではありません（回数・禁止・かがくへんかガスは関係しません）。
  - `DiscardFromPlay` はついているカードもトラッシュし、きぜつではありません（サイドはありません）。バトル場が空けば勝ち負け・バトル場に出す決定に進みます。
  - `RemoveDisguise` は、元の姿の最大HPがのっているダメージ以下になれば、処理のあとの確かめ（MH1・TK1）で受け付けません。
- **RevealFaceDown・CheckFaceUpDeckCard**: 「表にする操作」と「本人が見る操作」の違いです。
  - `RevealFaceDown` は本人のうらのカードを全員に公開します（ログ `secret_plan_revealed` が本当のカードの id を持つ）。残るかどうかは本当のカードで決まり、本人は観測の `real` で前から知っています。おもてにする前に、相手・観戦者の観測はうらのカードの uid を隠しています（`observation._mask_face_down`）。
  - `CheckFaceUpDeckCard` は何も公開しません。どの場合も受け付けず、理由の文にカードを書きません。いちばん上のおもてのカードは観測の `face_up_top` で全員に、下のおもてのカードは持ち主だけに `known_face_up` で出ています。おもての枚数は公開（`face_up_count`）なので、どの位置がおもてかは公開の情報で決まります。

## 3. 情報源の分類

候補・inputs・check で使う判定を、A〜E に分けました。既存の関数が状態を変えないことだけでは、安全とは判断していません。

<!-- generated:rest-sources begin -->
| 分類 | 意味 | 候補での使い方 |
|---|---|---|
| `A` | 公開情報と本人の知識だけで判断できる（場・トラッシュ・公開の枚数・番・特殊状態・本人の手札・本人のうらのカードの本当のカード） | 候補・inputs・check に使ってよい（本人の候補だけ。相手・観戦者には出さない） |
| `A-own` | A のうち、本人の見えないカードの集合だけで決まる持ち主の知識の関数（unseen_card_pool・deck_target_lower_bound・possible_deck_cards・searchable_deck_cards。v0.137〜v0.151 で山札とサイドの配分によらないことを確かめた） | 本人の候補だけに使ってよい。単位ごとに秘密の配分を変えた双子で確かめる（関数の既存の根拠を、候補の経路の根拠に数えない） |
| `B` | 宣言の入力がそろうと判断できる（特殊能力の energy・source・target、スタジアムの energy の組） | inputs で組ごとに確かめ、check でそろった入力をもう一度確かめる（全組み合わせを先に列挙しない） |
| `C` | 受理のあとのコイン・検索・決定で判断する（錯乱ジムのコイン・特殊能力のコイン・トレーナーの効果の決定・［ちえくらべ］の答えなど） | 候補に持ち込まない。受理のあと answer_decision の候補で答える |
| `D` | 秘密の状態を読む・実際の状態の上で処理を試すので、候補 API に使えない（処理のあとの確かめ・うらのカードの割り当ての試行・答えの続きの試行） | 使わない。この確かめで止まりうる候補は may_stop_later（または unverified） |
| `E` | 情報源・安全性が未確認（状態の複製の上で効果を試す事前確認で、読む値をたどっていないもの・他のモジュールへの呼び出しをたどっていないもの） | 公開してよいと仮定しない。たどるまで、その確かめに当たる候補は unverified（実装計画で対応済みに数えない） |
<!-- generated:rest-sources end -->

<!-- generated:rest-checks begin -->
| ID | コマンド | 参照 | 分類 | 使い方 | 説明 |
|---|---|---|---|---|---|
| PT-1 | `PlayTrainer` | `kyuura_engine/checks.py::require_turn` | `A` | `candidates` | 番・段階 |
| PT-2 | `PlayTrainer` | `kyuura_engine/engine.py::_require_in_hand` | `A` | `candidates` | 本人の手札 |
| PT-3 | `PlayTrainer` | `kyuura_engine/effects.py::trainer_use_blockers` | `A` | `candidates` | 場の力・期限のある禁止（公開） |
| PT-4 | `PlayTrainer` | `kyuura_engine/effects.py::EffectRegistry.trainer_effect` | `A` | `candidates` | 登録の有無（本人の手札のカードの定義と登録表） |
| PT-5 | `PlayTrainer` | `kyuura_engine/effects.py::TrainerEffect.check_playable` | `A` | `candidates` | 77 の実装のうち、下の 2 群を除くもの（場・トラッシュ・枚数・本人の手札） |
| PT-5o | `PlayTrainer` | `kyuura_engine/effects.py::deck_target_lower_bound` | `A-own` | `candidates` | 持ち主の知識の関数を呼ぶ 6 の実装（scan.check_playable.owner_knowledge） |
| PT-5e | `PlayTrainer` | `kyuura_engine/effects.py::state_stop_after` | `E` | `none` | 状態の複製の上で効果を試す 11 の実装（scan.check_playable.trials）。引く・クイズなど、実際の山札の並びを読みうる試行があり、たどっていない |
| PT-6 | `PlayTrainer` | `kyuura_engine/effects.py::stadium_trainer_cost` | `A` | `candidates` | リムーブ禁止ジム（本人の手札の枚数） |
| PT-7 | `PlayTrainer` | `kyuura_engine/effects.py::trainer_reaction_sources` | `A` | `candidates` | 相手の場の［ちえくらべ］と錯乱ジム（MG1） |
| PT-8 | `PlayTrainer` | `kyuura_engine/engine.py::_trainer_reaction_decline_check` | `D` | `none` | 使わない答えの続きを実際の状態の複製で処理する |
| PT-9 | `PlayTrainer` | `kyuura_engine/engine.py::_trainer_dead_end` | `D` | `none` | 効果の途中の決定の答えを状態の複製の上で試す |
| PT-10 | `PlayTrainer` | `kyuura_engine/engine.py::_chaos_tails` | `C` | `none` | 錯乱ジムの「うら」。相手がかわりに使えるか（F-1） |
| UP-0 | `UsePokemonPower` | `kyuura_engine/engine.py::_reveal_for_action` | `D` | `none` | 使うポケモン・指定したうらのカードを、確かめの前におもてにする。相手のうらのカードを指せば _identity_independent の試行になる |
| UP-1 | `UsePokemonPower` | `kyuura_engine/checks.py::require_turn` | `A` | `candidates` | 番・段階 |
| UP-2 | `UsePokemonPower` | `kyuura_engine/effects.py::powers_of` | `A` | `candidates` | 今の姿・のせたカード・写しの特殊能力（本人のうらのカードは unverified） |
| UP-3 | `UsePokemonPower` | `kyuura_engine/continuous.py::suppressors_of` | `A` | `candidates` | かがくへんかガスほか、消す効果の 6 つの確かめ（goop_gas_effects・powers_stopped・scared_by・power_suppressed・powers_use_prevented も同じ） |
| UP-4 | `UsePokemonPower` | `kyuura_engine/effects.py::copied_declared_power_problem` | `A` | `candidates` | 写した特殊能力（TF1・SV3） |
| UP-5 | `UsePokemonPower` | `kyuura_engine/effects.py::PowerEffect.check_usable` | `B` | `inputs` | 宣言の入力（energy・source・target）がそろうと決まる。入力のない 45 の実装は A として候補に使える |
| UP-5o | `UsePokemonPower` | `kyuura_engine/effects.py::possible_deck_cards` | `A-own` | `candidates` | 持ち主の知識の関数を呼ぶ 4 の実装（scan.check_usable.owner_knowledge） |
| UP-5e | `UsePokemonPower` | `kyuura_engine/effects.py::state_stop_after` | `E` | `none` | 状態の複製の上で効果を試す 7 の実装（scan.check_usable.trials） |
| UP-6 | `UsePokemonPower` | `kyuura_engine/effects.py::power_reuse_after_devolution` | `A` | `candidates` | DV3（停止として表示） |
| US-1 | `UseStadium` | `kyuura_engine/stadiums.py::stadium_in_play` | `A` | `candidates` | 場のスタジアム |
| US-2 | `UseStadium` | `kyuura_engine/effects.py::StadiumEffect.check_activation` | `B` | `inputs` | energy を選ばせる 2 の実装は入力がそろうと決まる。ほかは A。キョウの忍者ジムは A-own |
| US-3 | `UseStadium` | `kyuura_engine/effects.py::CoinReturnOwnerPokemonStadium.check_activation` | `A` | `candidates` | 本人のうらのカードがあると、対象を調べる途中で FD1（F-3。本当のカードによらない） |
| RD-1 | `RemoveDisguise` | `kyuura_engine/engine.py::_remove_disguise` | `A` | `candidates` | 番・自分の場・disguise（どれも公開） |
| RD-2 | `RemoveDisguise` | `kyuura_engine/effects.py::max_hp_drops` | `D` | `none` | 処理のあとの確かめ（MH1・TK1）。値は公開だが、処理を試さないと決めない |
| DF-1 | `DiscardFromPlay` | `kyuura_engine/effects.py::play_as_pokemon_effect` | `A` | `candidates` | おもてのカードの場での役割。うらのカードには呼ばない（F-2） |
| DF-2 | `DiscardFromPlay` | `kyuura_engine/persistent.py::leave_lock` | `A` | `candidates` | バトル場をはなれられない効果 |
| RF-1 | `RevealFaceDown` | `kyuura_engine/engine.py::_reveal_face_down` | `A` | `candidates` | 番・自分の場・うらである（公開） |
| RF-2 | `RevealFaceDown` | `kyuura_engine/zones.py::reveal_face_down` | `A` | `candidates` | 残るか・トラッシュかは本人の本当のカードで決まる（本人の知識）。候補に結果を書くなら本人だけ |
| CF-1 | `CheckFaceUpDeckCard` | `kyuura_engine/engine.py::_check_face_up_deck_card` | `A` | `candidates` | おもての枚数（公開）・持ち主・位置 |
| X-1 | 共通 | `kyuura_engine/engine.py::_identity_independent` | `D` | `none` | 相手のうらのカードを置きかえてコマンドを試す（最大 512 回） |
| X-2 | 共通 | `kyuura_engine/engine.py::_apply_once` | `D` | `none` | 処理のあとの確かめ（決められない姿・MH1・［ずらかる］・おもての山札・ミラクルエネルギー・［でんせつのからだ］・反応の決定の行きどまり） |
<!-- generated:rest-checks end -->

コマンドごとの確かめの ID:

<!-- generated:rest-command-index begin -->
- `PlayTrainer`: PT-1・PT-2・PT-3・PT-4・PT-5・PT-5o・PT-5e・PT-6・PT-7・PT-8・PT-9・PT-10
- `UsePokemonPower`: UP-0・UP-1・UP-2・UP-3・UP-4・UP-5・UP-5o・UP-5e・UP-6
- `UseStadium`: US-1・US-2・US-3
- `RemoveDisguise`: RD-1・RD-2
- `DiscardFromPlay`: DF-1・DF-2
- `RevealFaceDown`: RF-1・RF-2
- `CheckFaceUpDeckCard`: CF-1
<!-- generated:rest-command-index end -->

### 3.1 カードごとの確かめの走査

トレーナー・特殊能力・スタジアムの確かめは、カードの登録ごとの実装（77・70・9 のメソッド）です。`effects.py` の中の呼び出しの閉包をたどり、次の 2 つの群を集めました（`--check` が走査をやり直して照らします）。

- 持ち主の知識の関数を呼ぶ群（A-own）: 本人の見えないカードの集合だけで決まる下限を読みます。本人の候補には使えますが、相手には出しません。
- 状態の複製の上で効果を試す群（E）: クイズ・引く・入れ替えの試行です。実際の山札の並びや相手の場のうらのカードを読みうるので、たどるまで unverified です。

走査はほかのモジュールへの呼び出しを追いません。走査で見つからないことは、読まないことの証明ではありません。3 件の監査（トレーナー・特殊能力・スタジアムと残りの 4 種類）で各実装を読みましたが、E の群の読む値はまだたどっていません。

<!-- generated:rest-scan begin -->
| 確かめ | 実装の数 | 持ち主の知識の関数を呼ぶ（A-own） | 状態の複製で試す（E） |
|---|---|---|---|
| `check_playable` | 77 | `BenchNameGroupFromDeckTrainer`<br>`CoinsSearchBasicEnergyPerHeads`<br>`DiscardDeckTopThenReturnTypeEnergy`<br>`LookTopTakePokemonThenShuffle`<br>`ReturnHandEnergyThenCoinSearchBasicEnergy`<br>`SearchDeckTrainer` | `BlainesHeightQuiz`<br>`BlainesQuiz`<br>`CoinHealAndCureOwnActive`<br>`CoinHealBothElseSleepBoth`<br>`CoinStatusOnOpponentActiveTrainer`<br>`ConditionOwnActiveTrainer`<br>`GuessOpponentPrizeKind`<br>`SetAsideGuessKindQuiz`<br>`SwapPleaseTrainer`<br>`SwitchOpponentWithBench`<br>`SwitchWithBench` |
| `check_usable` | 70 | `CoinAttachEnergyFromDeckToOwnPokemon`<br>`CoinEvolveSelfFromDeck`<br>`SearchDeckWithBenchLettersToHand`<br>`SearchEvolutionCardToHand` | `ChooseFossilEvolvedThenCoinDevolveAll`<br>`CoinConditionOnEitherActive`<br>`ReturnActiveToHandWithBenchLetters`<br>`Shapeshift`<br>`StopOpponentBenchPowersThisTurn`<br>`SwitchOpponentChosenByOpponent`<br>`SwitchOpponentOnHeads` |
| `check_activation` | 9 | `CoinBenchOwnerBasicFromDeckStadium` | なし |

| 登録 | 数 |
|---|---|
| `trainers` | 269 |
| `stadiums` | 41 |
| `usable_stadiums` | 21 |
| `play_as_pokemon` | 2 |
| `stays_in_play` | 29 |
| `may_end_turn` | 5 |
| `powers` | 183 |
| `declared` | 104 |
| `entry_or_triggered` | 21 |
| `decision_or_with_attack` | 12 |
| `command_usable` | 71 |
<!-- generated:rest-scan end -->

## 4. 共通化できる判定と、使えない先読み

U7-3・U7-4 と同じく、処理の受理の前の部分を、同じ順番・同じコード・同じ文のまま関数にして候補の作成と入力の検査に使えます。今回は関数化していません。切り出す範囲と依存は次のとおりです。

| コマンド | 切り出す関数（案） | 範囲 | 含めないもの |
|---|---|---|---|
| `PlayTrainer` | `check_play_trainer` | `_play_trainer` の `require_turn` から MG1 の確かめまで（手札から出す前）。依存: `trainer_use_blockers`・`EffectRegistry.trainer_effect`・`trainer_problem`・`check_playable`・`stadium_trainer_cost`・`trainer_reaction_sources`・`stadium_of` | 手札から出したあと。`_apply_once` の `_trainer_reaction_decline_check`・`_trainer_dead_end`（D） |
| `UsePokemonPower` | `check_use_pokemon_power` | `_use_pokemon_power` の `require_turn` から `power_reuse_after_devolution` まで（宣言のログの前）。依存: `powers_of`・`current_form`・消す効果の 6 つの関数・`copied_declared_power_problem`・`copied_source_use_problem`・`check_usable` | `_reveal_for_action`（処理の前に入口が呼ぶ。うらのカードをおもてにする）・`_identity_independent`（D） |
| `UseStadium` | `check_use_stadium` | `require_turn`・`stadium_in_play`・`check_activation` | `activate` のコインと決定（C） |
| `RemoveDisguise` | `check_remove_disguise` | `require_turn` から `NOT_DISGUISED` まで | 処理のあとの MH1・TK1（D） |
| `DiscardFromPlay` | `check_discard_from_play` | `require_turn` から `leave_lock` まで | `after_power` の勝ち負け・交代 |
| `RevealFaceDown` | `check_reveal_face_down` | `require_turn` から `NOT_FACE_DOWN` まで | `reveal_face_down`（本当のカードで分かれる） |
| `CheckFaceUpDeckCard` | 要らない | 処理そのものが確かめだけ（状態を変えない） | なし |

使えない先読み（D）は、どのコマンドにもかかわる処理のあとの確かめです（`_apply_once`。決められない姿・MH1・［ずらかる］・おもての山札・ミラクルエネルギー・［でんせつのからだ］・反応の決定の行きどまり）。トレーナーの `_trainer_reaction_decline_check`・`_trainer_dead_end`、相手のうらのカードの `_identity_independent` も同じです。これらは実際の状態の複製の上で処理を試すので、候補・inputs・check に持ち込みません。U7-4 と同じく、候補は `apply_command` を試して通るものだけを返す形にしません。

## 5. 登録が宣言の入力に影響する経路

コマンドで使える宣言する特殊能力（71 件・56 の型）の、選ばせるものの形です。形は監査で `check_usable` を読んで決めました。静的な走査では形を決められないので、`--check` は型の所属だけを照らします。

<!-- generated:rest-power-shapes begin -->
| 宣言の入力の形 | 型の数 | 型 |
|---|---|---|
| `E(attached)+S(own)+T(own)` | 2 | `EnergyTransfer`<br>`MoveEnergyAmongNamed` |
| `E(attached)+S(own)` | 2 | `TakeEnergyToSelf`<br>`ConvertBasicEnergyColor` |
| `E(hand)+T(own)` | 1 | `AttachEnergyFromHand` |
| `E(hand)` | 1 | `DiscardTypeEnergyFromHand` |
| `S(own)+T(own)` | 1 | `MoveDamageCounter` |
| `S(opp)+T(opp)` | 1 | `MoveOpponentDamageCounter` |
| `S(own)` | 2 | `MoveDamageCounterToSelf`<br>`MoveGroupCounterToSelf` |
| `T(opp bench)` | 1 | `StopOpponentBenchPowersThisTurn` |
| `none` | 45 | `ChargeBenchEnergyToSelf`<br>`ChooseFossilEvolvedThenCoinDevolveAll`<br>`CoinAttachEnergyFromDeckToOwnPokemon`<br>`CoinAttachFromDiscardToTypePokemon`<br>`CoinBenchNamedFromDeck`<br>`CoinConditionOnEitherActive`<br>`CoinDamageOpponentActiveThenEndTurn`<br>`CoinEachPlayerLooksOpponentHand`<br>`CoinEachPlayerShufflesOpponentDeck`<br>`CoinEvolveSelfFromDeck`<br>`CoinFossilAttackBonusThisTurn`<br>`CoinGroupAttackImmunityNextTurn`<br>`CoinLookOpponentHandMayReturnTrainer`<br>`CoinPeekOpponentDeckTopMayShuffle`<br>`CoinPoisonMistUntilNextTurn`<br>`CoinPutStadiumFromDiscard`<br>`CoinRecoverNamedFromDiscard`<br>`CoinRecoverTrainerWithBenchLetters`<br>`CoinReviveFromDeck`<br>`ConvertAttachedEnergy`<br>`ConvertSelfToEnergy`<br>`CureBothActivesOncePerTurn`<br>`CureOneActiveConditionOnHeadsFromBench`<br>`DiscardThenDraw`<br>`DrawThenPutHandCardOnDeckTop`<br>`GatherTypeEnergyCardsToSelf`<br>`HealOwnPokemonOnHeads`<br>`LookOpponentDeckTopKeepOrder`<br>`LookOwnPrizeCard`<br>`PeekCard`<br>`RemoveOwnCounterOncePerTurn`<br>`ReturnActiveToHandWithBenchLetters`<br>`ReturnHandThenDrawSameWithBenchLetters`<br>`ReturnSelfToHand`<br>`SearchDeckWithBenchLettersToHand`<br>`SearchEvolutionCardToHand`<br>`Shapeshift`<br>`ShiftColor`<br>`SuperTransformPower`<br>`SwapPrizeWithDeckTop`<br>`SwitchOpponentChosenByOpponent`<br>`SwitchOpponentOnHeads`<br>`SwitchSelfFromBench`<br>`TakeEnergiesToSelf`<br>`TypeChangeSelfUntilTurnEnd` |

宣言のコマンドで使えない宣言する特殊能力の型（決定・ワザといっしょに使う）: `EntryPower`・`TriggeredPower`・`PreventKnockOutOnHeads`・`ReturnToHandOnKnockOut`・`BeamOnKnockOut`・`FleeAfterAttackDamage`・`TakeBenchDamageInstead`・`BenchNamedFromDeckOnAttackDamage`・`ReturnToDeckOnHeadsInsteadOfKnockOut`・`ExtraEnergyDamageWithAttack`・`AttackDeclaredPower`・`CoinsUntilTailsBonusToGroupAttack`・`CounterBonusToGroupAttack`
<!-- generated:rest-power-shapes end -->

スタジアムの使ってよい効果（21 件・8 の型）の形です。

<!-- generated:rest-stadium-shapes begin -->
| 宣言の入力の形 | 型 |
|---|---|
| `E(attached, own)` | `CureByDiscardingEnergyStadium`<br>`ReturnBasicEnergyStadium` |
| `none` | `CoinReturnOwnerPokemonStadium`<br>`CoinDrawStadium`<br>`CoinRetrieveBasicEnergyStadium`<br>`CoinBenchOwnerBasicFromDeckStadium`<br>`CoinHealOwnActiveStadium`<br>`LookDeckTopStadium` |
| `not_usable` | `StadiumEffect` |
<!-- generated:rest-stadium-shapes end -->

トレーナーは宣言の入力が `card` だけなので、登録は入力の形に影響しません（効果の決定の形は U7-1 の決定の監査の範囲です）。

## 6. 入力の契約と GUI への影響

既存の段階的な入力と `options_by_choice` を、どこまで使えるかです。

<!-- generated:rest-inputs begin -->
| 必要な入力 | 既存の形 | 変更 |
|---|---|---|
| 1 段（手札のトレーナー・場のポケモン 1 匹・おもての位置） | choose_option の 1 段（U7-3 の play_basic と同じ） | なし |
| 特殊能力 → 1 つの選ばせるもの（E(hand)・S(own)・T(opp bench)） | 2 段 + options_by_choice（U7-3 の _pair_candidate・U7-4 の宣言の選択） | なし |
| 特殊能力 → E → T（エナジートランス・あまごいなど。S は E がついているポケモンで決まる） | 2 段目の選べるものの番号を組ごとに分け、3 段目の options_by_choice を 2 段目の番号で引く | depends_on_stage に 2 を許す（追加だけ。形式の版 1 のまま。既存のクライアントが 1 だけを仮定していれば読めない） |
| スタジアム → E（タマムシ・ヤマブキ） | 1 段（energy の組は 1 つだけなので 2 段にしない。使う候補が 1 つのときは options の各要素がエネルギーカード） | なし |
| 選ばせるもののない特殊能力・スタジアム | 段のない候補（end_turn と同じ） | なし |
| 受理のあとの決定（対象・枚数・検索・コイン後の選択） | answer_decision（U7-1） | なし。宣言の前へ移さない |

- 宣言の前の入力を全組み合わせで列挙しない（段ごとに、前の段の番号で引く）
- 宣言のあとの決定を宣言の前へ移さない（トレーナーの対象・枚数、スタジアムのコインのあとの選択）
- 任意の辞退（宣言しない）・0 個の選択（energy を選ばない）・答えの並び（order）を区別する。宣言の選択は並びに意味がない（order: not_applicable）
- カード名・カード ID による共通処理の分岐を前提にしない。選ばせるものの形は、型ごとの宣言（登録の要素）から作る
- 選ばせるものの形の宣言は今の登録にない（check_usable の中にだけある）。最小の拡張: PowerEffect・StadiumEffect の型に、選ばせるもの（項目・指す場所）の宣言を加え、check_usable と食い違わないことを型ごとのテストで確かめる（D-U75-INPUT-DECL。エンジンの挙動は変えない）
<!-- generated:rest-inputs end -->

GUI がすでに扱う入力の形との共通点・相違点です。GUI リポジトリは読んだだけで、変更していません。実行していない互換性は保証しません。

<!-- generated:rest-gui begin -->
| 項目 | GUI（固定コミット d0c5cfa） | U7-5 | 共通 |
|---|---|---|---|
| 入力の種類 | choose_option・choose_value（contract/kyuura-client-api-v1.json） | choose_option だけ | はい |
| 2 段と options_by_choice | 固定コミット d0c5cfa（v0.164）の GUI は U7-3・U7-4 の候補を知らない（実装された種類は決定・準備・番を終えるだけ） | 使う | いいえ |
| 3 段目の depends_on_stage = 2 | 未対応（前提がない） | 特殊能力の E → T で使う（提案） | いいえ |
| 処理可能性・input_disclosure の語彙 | 契約の表と同じ 6 区分・3 区分 | 変えない | はい |
| 候補の種類 | turn_kinds_not_covered に 12 種類（エンジンを更新すると契約のテストが食い違う） | 7 種類を足す | いいえ |
<!-- generated:rest-gui end -->

## 7. 処理可能性と coverage

次の 4 つを別々に表します。既存の 6 区分（`supported`・`may_stop_later`・`unresolved_ruling`・`not_implemented`・`technical_limit`・`unverified`）と `input_disclosure` を使い、新しい区分は足しません。

<!-- generated:rest-axes begin -->
| コマンド | 候補として表示 | 入力を公開 | エンジンへ送信 | 受理のあとに停止しうる |
|---|---|---|---|---|
| `PlayTrainer` | 本人の手札のトレーナーごと（ゲーム上できないものは出さない。登録なし・未裁定は消さずに表示） | confirmed（手札のカードの番号だけ） | may_stop_later・unverified（試行の 11 の実装）・not_implemented と停止は送れない | コイン・決定・［ちえくらべ］・使わない答えの続きの確かめ（D）で止まりうる。supported にしない |
| `UsePokemonPower` | 自分の場のポケモンの宣言する特殊能力ごと（決定・ワザといっしょの特殊能力は出さない） | 形の宣言がある型は confirmed、ない型は unconfirmed（INPUT_BOUNDARY_UNCONFIRMED） | may_stop_later・unverified | コイン・決定・反応・相手のうらのカードの割り当ての試行（D） |
| `UseStadium` | 場のスタジアムに使ってよい効果があるとき（番のプレイヤーだけ） | confirmed（energy の 2 の実装）・no_input | may_stop_later（コインのあとの決定） | コイン・決定・空いたバトル場 |
| `RemoveDisguise` | disguise のある自分の場のポケモン | confirmed | may_stop_later（MH1・TK1） | 決定なし。処理のあとの確かめ（D）だけ |
| `DiscardFromPlay` | 自分の場のおもての化石・人形（うらのカードは出さない） | confirmed | supported の条件は U7-3 と同じ（受理のあとの停止のもとが場にないことを公開の情報で確かめた場合）。ほかは may_stop_later | バトル場が空けば勝ち負け・交代 |
| `RevealFaceDown` | 自分の場のうらのカード | confirmed | may_stop_later（トラッシュのあとの処理） | 本当のカードで残るか決まる（本人は知る） |
| `CheckFaceUpDeckCard` | 相手の山札の 2 枚目より下のおもての位置だけを unresolved_ruling（FU2）で表示（D-U75-FACE-UP） | no_input（位置は候補ごと） | 送れない（どの場合も受け付けない） | なし |
<!-- generated:rest-axes end -->

U7 全体の完了の基準（案）と、D-U7-COMPLETENESS・D-U7-DISPLAY の今回決める部分と保留できる部分です。

<!-- generated:rest-completion begin -->
| ID | 基準 |
|---|---|
| C-1 | 対応するコマンドと宣言の経路: プレイヤーのコマンドの型すべてに候補の種類があり、7 種類の外に残る経路（R-1・R-2）を一覧で示す |
| C-2 | 必要な入力の取得と送信: 宣言の前の入力を段で取得でき、check と submit が同じエンジンの確かめを通る。受理のあとの決定は answer_decision で答えられる |
| C-3 | 未対応・未確認の経路の明示: not_implemented・unresolved_ruling・technical_limit・unverified の候補を消さない。E の確かめを対応済みに数えない |
| C-4 | 情報境界: 候補・inputs・check が D の確かめを呼ばない。A-own を使う経路ごとに秘密の配分を変えた双子が通る。拒否は相手・観戦者に知らせない |
| C-5 | 直接実行との一致: 候補どおりの送信と直接のコマンドで、状態・乱数・ログ・診断が一致する（意図した差は文書に書く） |
| C-6 | 段階・主体ごとの coverage: 段階（準備・番・決定・ホスト）と主体（番のプレイヤー・番でないプレイヤー・ホスト）ごとに evaluated・not_covered を示す。complete と称するのは、その段階・主体の種類がすべて evaluated で、E の確かめが残らないときだけ |

| 判断事項 | 今回決める部分 | 保留できる部分 |
|---|---|---|
| `D-U7-COMPLETENESS` | U7-5 の各単位のあとも main は partial のまま（E の確かめと R-1・R-2 が残るため）。complete の条件を C-6 で表すこと | U7-5 のすべての単位のあと、E が残らない段階・主体だけを complete と称するかの採用 |
| `D-U7-DISPLAY` | U7-5 で新しい区分を足さない（6 区分のまま）。CheckFaceUpDeckCard の FU2 を unresolved_ruling で表示し送れないこと | 区分ごとの GUI の表示（色・送信のボタン）。GUI の追従のときに決める |
<!-- generated:rest-completion end -->

## 8. 調査で見つけたこと

エンジンの動作は直していません。裁定・規約として処理していません。

<!-- generated:rest-findings begin -->
| ID | 種類 | 状態 | 内容 | 再現・根拠 | 参照 | 影響範囲 |
|---|---|---|---|---|---|---|
| F-1 | 情報境界（要判断） | `reproduced` | 錯乱ジムの「うら」で、相手がかわりに使えるかの確かめ（borrow_unusable_reason → check_playable）が相手の手札の中身を読み、その結果が公開のログ chaos_not_borrowable（理由にコード）と、決定 ACCEPT_REQUEST が出るかで、使ったプレイヤーに伝わる | 双子（使ったプレイヤーの手札にポケモン育て屋さんとリザードン、場にヒトカゲ。相手のバトル場もヒトカゲ。相手の手札 1 枚がリザードンか水エネルギーかだけが違う）で、片方は ACCEPT_REQUEST（相手）、片方は chaos_not_borrowable（NO_EVOLUTION_TARGET） | `kyuura_engine/engine.py::_chaos_tails`<br>`kyuura_engine/effects.py::borrow_unusable_reason` | U7 の候補は作らないが、受理のあとの決定と公開のログで起こる。U7-5c の双子はこの経路を含めない（含めると一致しない）。裁定・規約として扱わない（D-U75-CHAOS） |
| F-2 | 拒否のコードの不一致 | `reproduced` | 本人のうらのカードを DiscardFromPlay で指すと、NOT_DISCARDABLE ではなく FD1（HiddenPropertyRead）で拒否する（理由の文を作るときに名前を読む） | マチスの秘策でうらにしたディグダ・プラスパワー・ユンゲラーのどれでも同じ FD1（本当のカードによらない。漏れではない） | `kyuura_engine/engine.py::_discard_from_play`<br>`kyuura_engine/effects.py::play_as_pokemon_effect` | U7-5a はうらのカードを候補に出さず、この確かめに当てない。エンジンの拒否のコードは変えない |
| F-3 | 保守的な停止 | `code_basis` | セキチクシティジムの対象を調べる途中で、本人の場にうらのカードがあると、ほかに対象があっても FD1 で止まりうる | 監査で CoinReturnOwnerPokemonStadium.check_activation の対象の走査が form_def(...).name_ja を読むことを確かめた（再現はしていない） | `kyuura_engine/effects.py::CoinReturnOwnerPokemonStadium.check_activation` | 本当のカードによらない。U7-5d で双子に含める |
| F-4 | 保守的な停止（未確認） | `unconfirmed` | ［シフト］の色の候補（shift_color_options）と ConvertSelfToEnergy の対象の確かめが、相手のうらのカードの項目を読み、FD1 で止まりうる | 監査の読み取りだけ（再現していない） | `kyuura_engine/effects.py::ShiftColor.check_usable`<br>`kyuura_engine/effects.py::ConvertSelfToEnergy.check_usable` | U7-5e で E として扱い、双子で確かめる |
| F-5 | 入口の確かめの順 | `code_basis` | UsePokemonPower は、指定した source・target・energy のうらのカードを、番の確かめ・入力の形の確かめより前におもてにする（_reveal_for_action）。拒否のコードは _identity_independent が本当のカードによらないものにそろえる | engine.py の _reveal_for_action と _apply_checked を読んだ（再現していない） | `kyuura_engine/engine.py::_reveal_for_action`<br>`kyuura_engine/engine.py::_apply_checked` | 候補の作成はこの順を写さない。相手のうらのカードを指す入力は unverified（D-U75-POWER-FACE-DOWN） |
| F-6 | 入口の確かめの範囲 | `code_basis` | CheckFaceUpDeckCard は番・段階を確かめない（どの場合も受け付けないので、状態は変わらない） | engine.py の _check_face_up_deck_card | `kyuura_engine/engine.py::_check_face_up_deck_card` | 番でない主体の候補に出すかは D-U75-FACE-UP |
<!-- generated:rest-findings end -->

F-1・F-2 の再現は、作業用のスクリプト（リポジトリの外）で、既存のテストの盤面の補助関数（`tests/test_stadiums_v0_57.py`・`tests/test_secret_plan_v0_67.py`）を使って確かめました。状態は変えていません（F-2 は拒否の前後で状態・乱数が同じことも確かめた）。

## 9. 採用の判断が必要な事項

<!-- generated:rest-adoption-needed begin -->
| ID | 問い | 推奨 |
|---|---|---|
| `D-U75-ORDER` | 実装の単位と順（U7-5a → b → c → d → e → f → g） | この順（共通の処理と情報境界の易しい順。GUI の対戦への効果は c が大きいが、a・b の型を先に固める） |
| `D-U75-FIRST` | 最初の単位を U7-5a（RemoveDisguise・DiscardFromPlay）にするか | する（7 章の根拠） |
| `D-U75-CHAINED` | 3 段目の options_by_choice を 2 段目の番号で引く（depends_on_stage = 2） | 形式の版 1 のまま追加として許す。GUI の追従の文書に書く |
| `D-U75-INPUT-DECL` | 特殊能力・スタジアムの型に、選ばせるものの宣言を加える（挙動は変えない） | 加える。宣言のない型は input_disclosure を unconfirmed にする |
| `D-U75-POWER-FACE-DOWN` | 相手のうらのカードを指す特殊能力の入力を、候補でどう示すか | unverified（選べるものには出し、送ればエンジンが判定する） |
| `D-U75-REVEAL-OUTCOME` | RevealFaceDown の候補に、本人のうらのカードが残るか（たねポケモンか）を書くか | 書かない（本人は観測の real で知っている。候補の項目を増やさない） |
| `D-U75-FACE-UP` | CheckFaceUpDeckCard を候補にどう出すか（番でない主体を含めるか） | 番のプレイヤーの候補に unresolved_ruling だけで出す。番でない主体には出さない |
| `D-U75-CHAOS` | F-1（錯乱ジムの借りる確かめの公開）をどう扱うか | U7-5 では直さない。エンジンの別の作業として、原典の記録と照らして扱いを決める（推測で裁定にしない） |
| `D-U75-ENERGY2` | R-1（カツラの 2 枚目）を U7-5g で attach_energy の任意の段として加えるか | 加える（U7-3 の候補に任意の 3 段目。追加だけ） |
<!-- generated:rest-adoption-needed end -->

## 10. 検証と未確認

- 実行した確かめ: この仕様の整合の検査（`--check`）、検査を壊して確かめるテスト（`tests/test_legal_actions_u7_5_design.py`）、関係する生成物の検査、変更したスクリプト・テストの lint。結果は実装計画の 6 章にあります
- 未確認:
  - E の群（試行の 11＋7 の実装）の読む値
  - 走査がほかのモジュールへの呼び出しを追わないこと
  - F-3・F-4・F-5 の再現
  - GUI での動作
