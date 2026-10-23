# 設計の変更（v0.6）

v0.6 は、カメックス（PMCG1-032）のポケモンパワー「あまごい」（手札の「水」エネルギーカードを自分の場の「水」ポケモンにつける）と、ワザ「ハイドロポンプ」、進化元のゼニガメ（PMCG1-023）・カメール（PMCG1-027）を加えた版です。原典の照合と裁定（R1〜R15・H1〜H5）は [rain-dance-v0.6.md](rain-dance-v0.6.md)、確かめた結果は [v0.6-verification.md](v0.6-verification.md) です。v0.5 の `PowerKey → PowerEntry → PowerEffect` の仕組みをそのまま使い、新しい仕組みは「手札から場へエネルギーカードを動かす共通の処理」と「パワーでつけた枚数の記録（形式 9）」の 2 つだけです。

## 1. コマンドの形（B1）

選ばせるものは 2 つ（つける手札のカードと、つける先の自分の場の「水」ポケモン）で、どちらも宣言の時点で使うプレイヤーに見えている（自分の手札と場）。選ぶ順番で選べるものが変わらない（カードの種類とつける先のタイプは別々に決まる）。

| 案 | 形 | 長所 | 短所 | 採否 |
|---|---|---|---|---|
| A. 今のコマンドを使う | `UsePokemonPower(player, pokemon, power=0, energy=手札のカードの uid, source=None, target=場のポケモンの番号)` | 1 つのコマンドで処理を終える（原子的。p.311 の「すべてすませてから」）。v0.5 と同じコマンド・同じ確かめる順番（共通 → パワーごと）。コマンドの種類・段階・決定・再開先を加えない（tests/test_state_integrity.py の `ALLOWED`・`sample_commands`、`command_from_dict`、v0.1 の参照データに影響しない） | 項目の意味がパワーごとに違う（エナジートランスの `energy` はついているカード、あまごいは手札のカード。あまごいは `source` を使わない） | **採用**。意味の違いはパワーの実装（`check_usable`）が確かめ、使わない項目を指定したら `POWER_CHOICE_NOT_USED` で拒否する（取りちがえを黙って通さない） |
| B. 能力ごとのコマンド | `RainDance(player, pokemon, energy, target)` など | 項目の意味がはっきりする | パワーを加えるたびにコマンドの種類が増える（エンジンがカードの種類を知ることになる。v0.2a の登録表の考え方に反する）。共通の確認（番・段階・使うポケモン・登録）を重ねて書くことになる。`ALLOWED`・`sample_commands`・書き出しの型の一覧も増える | 不採用 |
| C. 決定で選ばせる | `UsePokemonPower(player, pokemon)` → 決定「手札のどのカード」→ 決定「どのポケモン」 | 項目が要らない | 2 段階の決定と、その途中の状態（宣言したがつけていない）が要る。その状態は書き出しの形式 1〜9 で表せず、再開先（`PowerEffect.resume`・`decision_problems`）と不変条件も要る。決定の選べるものに手札のカードの uid が入り、状態に隠れた情報の並びが増える。選ぶものが宣言の時点でそろっているので、決定にする利点がない | 不採用（処理の途中で選ぶものが決まるパワーを加えるときに使う。v0.5 の architecture 9 章） |

v0.4e までの 2 つの項目（`player`・`pokemon`）だけの辞書も、今までどおり読める（あまごいには選ばせるものが足りないので `POWER_CHOICE_MISSING`）。

## 2. 手札から場への移動（B2）

`zones.attach_energy_from_hand(state, player, energy, pokemon)` を加え、手札からつける通常の操作（`engine._attach_energy`。p.310）と、あまごい（`AttachEnergyFromHand.resolve`）の両方がこれを使う。カードを動かすだけで、つけてよいかの確認・回数の記録・ログは呼ぶ側が、動かす前にすべて済ませる。

| 要件 | 実装 | テスト |
|---|---|---|
| エネルギーカードの uid が変わらない | 同じ uid を `hand` から取りのぞき、つける先の `energy` の最後に加える（複製しない・新しいカードを作らない） | `test_moves_the_same_card_from_hand`・変異 4・5・6 |
| 手札から正しく取りのぞく | `p.hand.remove(energy)`。カードの保存則（`check_invariants`）で 2 か所・0 か所を見つける | 同上・ログの監査の手札の組み立て直し |
| 正しいポケモンに加える | つける先は場のポケモンの番号で指す（`target`）。いちばん上のカードのタイプで「水」かを確かめる | `test_every_own_water_pokemon_is_a_target`・変異 8・24 |
| ほかのプレイヤーの手札・カードを操作できない | 手札は使うプレイヤーの手札だけを見る（`CARD_NOT_IN_HAND`）。つける先は自分の場のポケモンだけ（`TARGET_NOT_YOURS`）。共通の処理も、手札・持ち主・つける先の持ち主が合わなければ `RuntimeError`（確認の漏れ） | `test_cards_that_are_not_a_water_energy_in_own_hand`・`test_targets_that_are_not_own_water_pokemon`・`test_engine_never_moves_cards_on_an_unchecked_path`・変異 9・10 |
| ないカードを指定できない | ない uid は手札にないので `CARD_NOT_IN_HAND`。整数でない値は `BAD_COMMAND` | 同上・`test_choices` |
| 同じカードを 2 回使えない | 1 回目で手札から出るので、2 回目は `CARD_NOT_IN_HAND` | `test_cards_that_are_not_a_water_energy_in_own_hand` |
| 不正なコマンドで状態の一部だけが変わらない | `apply_command` は複製した状態で処理し、確かめることはすべてカードを動かす前（v0.1 から）。拒否したら渡した状態・乱数・ログは変わらない | `assert_rejected`（形式 9 の書き出し・乱数の指紋・ログ）・ストレス実行（拒否の前後の比較） |
| 乱数を使わない処理で乱数を変えない | あまごい・通常の操作は乱数を使わない | `test_moves_the_same_card_from_hand`・`test_rejections_never_use_randomness_or_change_the_counters`・自然な対戦（対戦準備のあとの乱数はコインだけ）・変異 22 |
| 隠れた情報を不必要に漏らさない | ログ `power_attach_energy` に書くカードは、つけたカード（場に出ると公開される）と使ったカメックスだけ。手札のほかのカードは書かない（通常の操作のログ `attach_energy` と同じ程度） | `test_log_has_no_hand_contents` |

### 2.1 確かめる順番（状態を変える前にすべて）

| 順 | 確かめること | コード | 場所 |
|---|---|---|---|
| 1 | コマンドの項目の型 | `BAD_COMMAND` | `commands.check_command_fields` |
| 2 | 対戦が終わっていない・止まっていない | `GAME_OVER`・止めた理由 | `apply_command` |
| 3 | 段階が `Phase.MAIN`・プレイヤーの番号・番のプレイヤー | `WRONG_PHASE`・`INVALID_PLAYER`・`NOT_YOUR_TURN` | `engine._require_turn` |
| 4 | 使うポケモンが自分の場にいる | `POKEMON_NOT_YOURS`・`POKEMON_NOT_IN_PLAY` | `engine._use_pokemon_power` |
| 5 | いちばん上のカードに、その位置の特殊能力がある・登録があってデータと合う | `NO_POKEMON_POWER`・`UNSUPPORTED_POKEMON_POWER` | 同上 |
| 6 | このカードがねむり・マヒ・こんらんでない（R9） | `POKEMON_ASLEEP`・`POKEMON_PARALYZED`・`POKEMON_CONFUSED` | `AttachEnergyFromHand.check_usable`（`effects._require_user_not_asleep_paralyzed_confused`。エナジートランスと共通） |
| 7 | `energy`・`target` がある | `POWER_CHOICE_MISSING` | 同上 |
| 8 | `source` を指定していない | `POWER_CHOICE_NOT_USED` | 同上 |
| 9 | `energy` が自分の手札にある（R4） | `CARD_NOT_IN_HAND` | 同上 |
| 10 | 基本エネルギーカードで、「水」を出す（R4） | `NOT_BASIC_ENERGY`・`WRONG_ENERGY_TYPE` | 同上 |
| 11 | `target` が自分の場のポケモン（R5） | `TARGET_NOT_IN_PLAY`・`TARGET_NOT_YOURS` | 同上（`effects._own_pokemon`。エナジートランスと共通） |
| 12 | `target` が「水」ポケモン（R5。いちばん上のカード） | `WRONG_POKEMON_TYPE` | 同上 |

そのあと宣言のログ `pokemon_power` → `resolve`（共通の処理でカードを動かす → パワーでつけた枚数を 1 増やす → ログ `power_attach_energy`）。番は終わらない（R14）。

## 3. 通常の操作との区別（B3）

| 状態の項目 | 意味 | 変えるもの | 番の最初 |
|---|---|---|---|
| `energy_attachments_this_turn`（v0.1） | 手札からつける通常の操作（p.310）の回数（1 番に 1 回まで） | `engine._attach_energy` だけ。あまごい・エナジートランスは変えない | 0 |
| `energy_attached_by_powers_this_turn`（v0.6） | この番に、ポケモンパワーの効果で手札からつけた枚数 | `AttachEnergyFromHand.resolve` だけ（エナジートランスは手札からつけないので変えない） | 0 |

- R12（通常の操作のあとのあまごい）: あまごいは `energy_attachments_this_turn` を見ない。
- R13（あまごいのあとの通常の操作）: `engine._attach_energy` が、ほかの確認（手札・基本エネルギー・`ENERGY_ALREADY_ATTACHED`・つける先）がすべて通ったあと、`energy_attached_by_powers_this_turn > 0` なら `UnsupportedError`（`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`）。ほかの理由で正しくない操作は、その理由で拒否する（止める範囲を広げない）。通常の操作をもうした番の 2 回目は、どちらの読み方でも `ENERGY_ALREADY_ATTACHED`（p.310。R13 より先に確かめる）。
- 2 つの数を 1 つにまとめなかった理由: まとめると、あまごいでつけたカードを p.310 の 1 枚に数える（R13 の読み方 B）か数えない（読み方 A）かを、どちらかに決めることになる。

## 4. 状態と書き出し（B4）

### 4.1 なぜ状態の項目が要るか

R13 で止めるには、「この番にあまごいでつけたか」を、通常の操作を受け付けるときに知る必要がある。

| 案 | 内容 | 採否 |
|---|---|---|
| 状態に持つ（`GameState.energy_attached_by_powers_this_turn`） | 番の最初に 0、あまごいで 1 増やす | **採用**。CLAUDE.md の「回数の制限のあるパワーを加えるときは、回数を状態に持つ（ログから数えない）」と同じ考え方 |
| ログから数える（今の番の `power_attach_energy`） | 項目を加えない | 不採用。ログは記録で状態の正本ではない（エンジンはログから状態を決めない。v0.4e） |
| `energy_attachments_this_turn` に足す | 項目を加えない | 不採用。R13 を「数える」に決めることになり、R12 も変わる（3 章） |
| 対戦を止める（`Phase.HALTED`） | 通常の操作が出たら対戦ごと止める | 不採用。止まるのはプレイヤーが選んだ 1 つの操作で、その操作をしなければ対戦は続けられる（v0.2b の `UNRESOLVED_POTION_WITHOUT_DAMAGE` と同じ扱い） |

### 4.2 書き出しの形式 9

- 形式 9 = 形式 8 に、上の段の `energy_attached_by_powers_this_turn`（整数）を加えたもの。場のポケモン・決定の項目は形式 8 と同じ。
- 形式 1〜8 は、この数が 0 でなければ `ValueError`（黙って落とさない。v0.2b からの方針）。0 なら形式 1〜8 の書き出しは v0.5 と同じ（項目を加えない）。数が 0 でないのは、あまごいを使った番のあいだだけ（番の最初に 0 になる）。
- 移行: v0.5 までの対戦にはあまごいがないので、v0.5 までの書き出し（形式 1〜8）はどれも数が 0 の状態を表す。形式 9 を読む側は、形式 8 以下の書き出しを数 0 として読める。形式 9 には知らない項目が 1 つ増えるので、知らない項目を拒否する読み手は形式 9 を拒否する（形式 5 以降と同じ扱い）。
- 不変条件（`engine._power_attachment_problems`。`check_invariants`）: 0 以上の整数で、今の番（最後の `turn_start` のあと）のログの `power_attach_energy` の数と同じ。ログから状態を決めるのではなく、状態とログが食い違っていないかを確かめるだけ。
- 互換性: 比較の駆動（tools/compat_driver.py）は形式 8 で比べ、`UsePokemonPower` を送らないので、変えていない（参照データ tests/fixtures/compat_base_4bd97bf.json も作り直していない）。ストレス実行（tools/stress_engine.py）は拒否の前後の比較と書き出しの監査を形式 9 にした（あまごいを使う組で形式 8 は書き出せないため）。

### 4.3 書き出しの形式 10（v0.31）

- 形式 10 = 形式 9 に `power_uses_this_turn`（この番に使った「自分の番ごとに1回使える」特殊能力。[場のポケモンの番号, 特殊能力の位置] の並び）と `energy_burn`（この番に「エナジーバーン」で「炎」エネルギーになったエネルギーカード。[場のポケモンの番号, エネルギーカードの uid] の並び）を加えたもの。どちらも番の最初・番の終わりに空。
- 形式 1〜9 は、どちらも空なら今までどおり書き出せる。空でなければ `ValueError`（黙って落とさない）。ログの監査（tests/log_audit.py）の `LATEST_FORMAT` は 10。比較の駆動（tools/compat_driver.py）は形式 8、1 歩ごとの比較（tools/engine_lockstep.py）は形式 9 のまま（v0.31 のカードを使わない対戦では 2 つの項目は空）。[held-cards-v0.31.md](held-cards-v0.31.md) 6 章。

### 4.4 書き出しの形式 11（v0.44）

- 形式 11 = 形式 10 の場のポケモンごとに `attacks_used_once`（場に出てから 1 度だけ使えるワザで、このポケモンが使ったもの。[カードの uid, ワザの位置] の並び）と `evolution_permission_turn`（トレーナー「サカキ」の許可を受けた番。なければ null）を加えたもの。`attacks_used_once` はポケモンが場にいるあいだ残り（場をはなれたらポケモンごとなくなる）、`evolution_permission_turn` は番の終わりに消える。
- 形式 1〜10 は、どちらもない（空・null）なら今までどおり書き出せる。あれば `ValueError`（黙って落とさない）。ログの監査（tests/log_audit.py）の `LATEST_FORMAT` は 11（`POKEMON_FIELDS_SINCE` に 2 つの項目）。比較の駆動（tools/compat_driver.py）は形式 8、1 歩ごとの比較（tools/engine_lockstep.py）は形式 9 のまま（v0.44 のカードを使わない対戦では 2 つの項目はない）。[search-evolution-once-attacks-v0.44.md](search-evolution-once-attacks-v0.44.md) 10 章。

### 4.5 書き出しの形式 12（v0.47）

- 形式 12 = 形式 11 に、最上位の `trainer_locks`（プレイヤーに与えた、期限のあるトレーナーカードの使用の禁止。`{"player", "source_player", "source_card", "source_card_id", "effect", "created_turn", "expires_turn"}` の並び。与えた順。なければ `[]`）を加えたもの。禁止は消える番の終わりに消える。場のポケモンの項目ではなくプレイヤーの記録なので、最上位の項目にした。
- 形式 1〜11 は、禁止がなければ今までどおり書き出せる。あれば `ValueError`（黙って落とさない）。ログの監査（tests/log_audit.py）の `LATEST_FORMAT` は 12（`TOP_FIELDS_SINCE` に `trainer_locks`）。比較の駆動（tools/compat_driver.py）は形式 8、1 歩ごとの比較（tools/engine_lockstep.py）は形式 9 のまま（v0.47 のカードを使わない対戦では禁止はない）。次の新しい形式は 13。[fossil-hidden-info-v0.47.md](fossil-hidden-info-v0.47.md) 5.3 節。

### 4.6 書き出しの形式 13（v0.48）

- 形式 13 = 形式 12 の場のポケモンごとに `type_shift`（モルフォンの［へんしょく］で色を変えた記録。`{"color", "turn", "source_card", "source_card_id", "returned_to_bench"}`。なければ null）を加えたもの。記録は場をはなれるとポケモンごとなくなり、進化すると消える。変えた色が今有効か（VS1）は記録・番・場所・特殊状態・かがくへんかガスから求める値なので書かない。
- 形式 1〜12 は、記録がなければ今までどおり書き出せる。あれば `ValueError`（黙って落とさない）。v0.48 の持続する効果の種類（`weakness_change`・`resistance_change`・`max_hp_set`）は形式 8 の `persistent_effects` の値を加えただけ。ログの監査（tests/log_audit.py）の `LATEST_FORMAT` は 13（`POKEMON_FIELDS_SINCE` に `type_shift`）。比較の駆動（tools/compat_driver.py）は形式 8、1 歩ごとの比較（tools/engine_lockstep.py）は形式 9 のまま（v0.48 のカードを使わない対戦では記録はない）。次の新しい形式は 14。[effective-pokemon-properties-v0.48.md](effective-pokemon-properties-v0.48.md) 7.4 節。

### 4.7 書き出しの形式 14（v0.49）

- 形式 14 = 形式 13 の場のポケモンごとに `disguise`（タケシのキュウコンの「ばける」でのせた進化カード。`{"card", "card_id"}`。なければ null）と、最上位の `recalls`（思い出させるの記録。`{"player", "turn", "pokemon_id", "card", "card_id", "trainer", "trainer_card_id"}` の並び。`card` は使ったときの対戦ポケモンのいちばん上のカード、`trainer` は思い出させるのカード。なければ `[]`）を加えたもの。持続する効果は、効果を与えたワザ・対象のワザがいちばん上のカードのものでないとき（［サイコリンク］・［へんしん］・「ばける」・思い出させるで使ったワザ、「ドわすれ」で選んだワザ）だけ `attack_card`・`target_attack_card`（ワザを印刷したカードの id）を書く。`power_uses_this_turn` には、のせたカードの特殊能力を使った記録（[場のポケモンの番号, 特殊能力の位置, そのカードの uid]）が入る。今の姿（［へんしん］・「ばける」）・今使えるワザは状態から求める値なので書かない（観測が書く）。
- 形式 1〜13 は、のせたカード・記録・その項目のある効果・のせたカードの特殊能力の使用の記録がなければ今までどおり書き出せる。あれば `ValueError`（黙って落とさない）。ログの監査（tests/log_audit.py）の `LATEST_FORMAT` は 14（`POKEMON_FIELDS_SINCE` に `disguise`、`TOP_FIELDS_SINCE` に `recalls`）。比較の駆動（tools/compat_driver.py）は形式 8、1 歩ごとの比較（tools/engine_lockstep.py）は形式 9 のまま（v0.49 のカードを使わない対戦ではのせたカード・記録はない）。次の新しい形式は 15。[virtual-attacks-transformation-v0.49.md](virtual-attacks-transformation-v0.49.md) 8 章。

### 4.8 書き出しの形式 15（v0.50）

- 形式 15 = 形式 14 の場のポケモンごとに `devolved_turn`（最後に退化した番。退化していなければ null）を加えたもの。`power_uses_this_turn` には、進化・退化でいちばん上で
  なくなったカードの「自分の番ごとに1回」の特殊能力の記録（[場のポケモンの番号, 特殊能力の位置, 使ったカードの uid]。`evolution.retag_power_uses`）が入る。
- 形式 1〜14 は、退化した番のあるポケモン・置きかえた記録がなければ今までどおり書き出せる。あれば `ValueError`（黙って落とさない）。ログの監査（tests/log_audit.py）の
  `LATEST_FORMAT` は 15（`POKEMON_FIELDS_SINCE` に `devolved_turn`）。比較の駆動（tools/compat_driver.py）は形式 8、1 歩ごとの比較（tools/engine_lockstep.py）は形式 9 のまま
  （v0.50 のカードを使わない対戦では退化した番はない）。次の新しい形式は 16。[mew-devolution-spray-v0.50.md](mew-devolution-spray-v0.50.md) 7 章。

### 4.9 書き出しの形式 16〜22 と 23（v0.88）

- 形式 16〜22 は、それぞれの版の文書に書いた（16 = v0.56 の `trainer_effects`・トレーナーの使用の禁止の `origin`、17 = v0.57 の `stadium`・`stadium_uses_this_turn`・`trainer_in_use.user`、
  18 = v0.58 の `trainer_stack`・`trainer_in_use.via`、19 = v0.59 の `energy_roles`、20 = v0.62 の場のポケモンの `history`、21 = v0.63 の `set_aside`・`face_up_prizes`、22 = v0.67 の
  `face_down_cards`）。
- 形式 23 = 形式 22 に、最上位の `color_effects`（特殊能力で色を変える効果の記録。ランターンの［せんすい］・ポリゴン2の［エナジーコンバーター］の「この番が終わるまで」。
  `{"kind", "player", "source", "source_card", "card_id", "power_index", "target", "color", "turn", "left_play"}` の並び。なければ `[]`）を加えたもの。記録は番の終わり・発生源の
  ねむり・マヒ・こんらんで消え、［せんすい］の発生源が場をはなれたらコマンドの終わりに消える。今の色・エネルギーの個数・続くかが決まらないか（CE1・CE2）は、記録・場・特殊状態・
  かがくへんかガスから求める値なので書かない（観測が書く）。
- 形式 1〜22 は、記録がなければ今までどおり書き出せる。あれば `ValueError`（黙って落とさない）。ログの監査（tests/log_audit.py）の `LATEST_FORMAT` は 23（`TOP_FIELDS_SINCE` に
  `color_effects`）。比較の駆動（tools/compat_driver.py）は形式 8、1 歩ごとの比較（tools/engine_lockstep.py）は形式 9 のまま（v0.88 の特殊能力を使わない対戦では記録はない）。
  次の新しい形式は 24。[type-energy-colors-v0.88.md](type-energy-colors-v0.88.md) 2 章。

## 5. ログ

```text
pokemon_power        player, pokemon（使うカメックスのいちばん上のカードの uid）, pokemon_id, power（名前 "あまごい"）, power_index, turn
power_attach_energy  player, pokemon, pokemon_id（使ったカメックス）, power（PowerKey の文字列 "PMCG1-032@power0"）,
                     energy（つけたカードの uid）, to_pokemon_id（つけた先の場のポケモンの番号）, turn
```

- 宣言 `pokemon_power`（p.311 の手順 1）のすぐあとに、処理 `power_attach_energy`（手順 3）が 1 つ。
- 手札からつける通常の操作のログ `attach_energy`（`target` はカードの uid）・エナジートランスのログ `move_energy`（場のエネルギーのつけかえ）とは別の種類。取りちがえない（変異 25 で確かめた）。

## 6. ログの監査（tests/log_audit.py）

v0.4e の約束（ダメージ・エネルギー・トラッシュを変えるログを加えたら、組み立て直しにも加える）にしたがって、次を加えた。

| 加えたもの | 確かめること |
|---|---|
| 手札の組み立て直し（すべての対戦） | 引いた（`draw`）・取ったサイド（`take_prize`）で手札に入り、切り直し（`mulligan`。見せた手札と同じか）・場に出した（`place_starting_pokemon`・`play_to_bench`）・進化（`evolve`）・つけた（`attach_energy`・`power_attach_energy`）・使った（`play_trainer`）で手札から出る。出るカードがその時点の手札にあること、対戦の終わりの手札が状態と同じこと |
| `power_attach_energy` | 直前に同じ番・同じプレイヤー・同じポケモンの宣言があること、自分のカードを自分の場のポケモンにつけたこと、そのカードが手札にあったこと、登録が手札からつけるパワーで、カードのタイプ・つける先のタイプ（その時点のいちばん上のカード）が合うこと、ワザのあと（番の終わりまで）にないこと |
| 通常の操作の回数 | 1 番に 1 回まで。あまごいでつけたあと（通常の操作をまだしていない番）にないこと（R13 はエンジンが止める） |
| 宣言と処理 | 宣言（`pokemon_power`）のすぐあとに処理（`move_energy`・`power_attach_energy`）があること（v0.5・v0.6 のパワーは決定を出さず、1 回の宣言で 1 回処理する）。ログの監査の自己テストで、宣言のあとの処理を通常の操作のログにすりかえても見つからなかったので加えた |
| 書き出しの監査 | 形式 1〜9。形式 9 の書き出しから後の形式の項目を除いたものと、各形式の書き出しが同じ。形式 10 がないこと |

監査が壊れたログ・状態を見つけることは tests/test_blastoise_games_v0_6.py `LogAuditRainDanceTest`（12 通り）で確かめた。

## 7. 変えたもの

| 場所 | 変更 | 理由 |
|---|---|---|
| `zones.attach_energy_from_hand` | 加えた（2 章） | 手札から場への移動を 1 か所にする（通常の操作とあまごいで同じ処理） |
| `engine._attach_energy` | 共通の処理を使う。R13 の停止を加えた（ほかの確認のあと・動かす前） | 3 章 |
| `engine._begin_turn` | `energy_attached_by_powers_this_turn` を 0 にする | 4 章 |
| `engine.check_invariants`・`_power_attachment_problems` | 加えた | 4.2 |
| `state.GameState.energy_attached_by_powers_this_turn` | 加えた（既定 0） | 4.1 |
| `serialize`（形式 9） | `FORMAT_VERSIONS` に 9。形式 1〜8 は数が 0 でなければ `ValueError` | 4.2 |
| `effects.AttachEnergyFromHand` | 加えた（`energy_type`・`pokemon_type`。カメックスは水・水） | あまごい（2.1） |
| `effects.ExtraEnergyDamage` | 加えた（`energy_type`・`per_energy`・`max_extra`。カメックスは水・10・2） | ハイドロポンプ（[rain-dance-v0.6.md](rain-dance-v0.6.md) 4 章） |
| `effects._require_user_not_asleep_paralyzed_confused`・`effects._own_pokemon` | エナジートランスのメソッドだったものを、あまごいと共通の関数にした。拒否のコードと順番は変えていない（メッセージの「（p.323 の最新の説明）」は「（最新の説明）」になった。メッセージは比較・テストの対象ではない） | 同じ文（「このカードが「ねむり・マヒ・こんらん」状態のとき、この力は使えない」）を同じ処理にする |
| `effects.DEFAULT_EFFECTS` | id を `kyuura-engine-0.6` に。ワザ 5 つ（ゼニガメのあわ・からにこもる、カメールのからにこもる・かみつく、カメックスのハイドロポンプ。38 → 43）とパワー 1 つ（あまごい。1 → 2）を加えた | 登録の中身が変わった |
| `cards.POOL_KEYS` | `pool_v0_6` を加えた | 写しの対戦用のカードの組 |
| scripts/extract_kyuura_cards.py・kyuura_engine/data/kyuura_cards.json | `POOL_V0_6`（ゼニガメ・カメール・カメックス）を加え、参照カードをカメックスからフーディン（PMCG1-049。登録のないパワー「ダメージスワップ」とワザ「あやしいひかり」）に替えて写しを作り直した（参照コミット `ecb2d694` のまま。`--check` で一致） | カメックスを対応にしたので、未対応のポケモンパワーを持つ 2 進化の参照カードが要る |
| kyuura_engine/data/card_verification.json | PMCG1-023・PMCG1-027・PMCG1-032 の照合の記録を加えた | 照合してから登録する（CLAUDE.md） |
| `commands.UsePokemonPower` の説明 | あまごいでの項目の意味を書いた（項目・型は変えていない） | 1 章 |
| tests/log_audit.py | 6 章 | — |
| tools/stress_engine.py | カメックスの 2 組（`blastoise`・`blastoise_mixed`）と、あまごいの使用（できそうなもの 70%・わざと不正なもの 30%）を混ぜる。拒否の前後の比較・書き出しの監査を形式 9 に。フシギバナ・カメックスのいない組は駆動と同じ操作、フシギバナだけの組は v0.5 と同じ操作（乱数の使い方を変えていない） | 段階 C のストレス実行 |
| `kyuura_engine.__version__`・pyproject.toml | `0.6.0` | 版の名前 |

## 8. 変えなかったもの

- コマンドの種類・段階（`Phase`）・決定の種類・再開先（あまごいは決定を出さない）。
- ログの既存のイベントの形（`attach_energy`・`move_energy`・`pokemon_power` など）。加えたのは `power_attach_energy` だけ。
- 乱数の使い方（あまごい・ハイドロポンプは乱数を使わない。あわ・からにこもるはコイン 1 枚で、v0.3b・v0.4b の実装と同じ）。
- 既存のルールの処理・裁定の分類・処理の順番。v0.5 までの 11 の `UNRESOLVED_…` のコード（新しく 1 つ加えた）。
- 固定値: tests/test_reproducibility.py、各対戦のテストの `GOLDEN_DIGEST`・`EXPECTED_COUNTS`、tests/fixtures/v0_1_reference.json・tests/fixtures/compat_base_4bd97bf.json（作り直していない）。
- 比較の駆動（tools/compat_driver.py）。

## 9. 前の版との比較

`python3 tools/compare_engine_versions.py --base 0fbc3ab`（v0.5）: 8 つの組・50 局・11,377 手で、受け付けた操作・拒否のコード・状態（形式 8）・乱数の指紋・段階・ログの長さ・形式 1〜8 の書き出しに食い違いはなかった（[v0.6-verification.md](v0.6-verification.md) 4 章）。比べないのは効果の登録表の id だけ（`kyuura-engine-0.5` → `kyuura-engine-0.6`）。この比較は「カメックスのいない対戦の結果が変わらない」ことを確かめたもので、あまごいの正しさは単体テスト・自然な対戦・ストレス実行・変異テストで別に確かめた。

## 10. テストの段階

| 段階 | v0.6 で加えたもの |
|---|---|
| A 速い単体テスト | tests/test_rain_dance_v0_6.py（登録と照合・手札から場へ・通常の操作との関係・特殊状態・拒否と原子性・ほかの処理との関係・ログ・書き出し・不変条件）・tests/test_squirtle_line_v0_6.py（ゼニガメ・カメール・ハイドロポンプ・進化）・tests/test_unresolved_boundaries_v0_4e.py `AttachAfterPowerAttachBoundaryTest` |
| B 決まった seed の統合テスト | tests/test_blastoise_games_v0_6.py（`new_game` からの 80 局・ログと書き出しの監査・ログの監査の自己テスト・小さなストレス実行・固定値） |
| C 大規模な実行 | tools/stress_engine.py のカメックスの 2 組・前の版との比較 |

## 11. 変えた既存のテストと理由

どのテストも、確かめる内容（意図）は変えずに、v0.6 の変更に合わせて値・カードを直した。理由はテストのコメントにも書いた。

| テスト | 変更 | 理由 |
|---|---|---|
| tests/test_cards.py `test_trainer_evolution_and_power_are_unsupported` | 未対応のポケモンパワーを持つ 2 進化の例を、カメックスからフーディンに替えた | カメックスを対応にした（パワーとワザを登録した） |
| tests/test_cards.py `test_v0_1_pool_is_ten_basic_pokemon_and_six_basic_energy` | `pool_v0_6` を確かめ、v0.1 の組の数え方からゼニガメの系統を除いた | 写しに v0.6 の組を加えた |
| tests/test_evolution_v0_4a.py `test_unsupported_evolution_cards`・`test_rejected_commands` | 未対応の 2 進化の例をフーディンに替えた（`UNSUPPORTED_EVOLUTION` のまま） | 同上 |
| tests/test_stage2_v0_4c.py `test_stage2_is_not_supported_as_a_whole`・`test_unsupported_stage2_cards`・`test_rejected_stage2_evolutions_change_nothing` | 同上 | 同上 |
| tests/test_pokemon_powers_v0_5.py `test_default_registry_registers_only_energy_trans`・`test_registry_methods_keep_the_other_registrations`・`test_unregistered_power_of_another_card_stays_unsupported` | 登録はエナジートランスとあまごいの 2 つ。登録のないパワーの例をフーディンに替え、エナジートランス・あまごいの登録をフーディンの位置に写しても使えないことを確かめる | あまごいを登録した |
| tests/test_pokemon_powers_v0_5.py `test_copies_and_serialization` | 「形式 9 はない」を「エナジートランスではパワーでつけた枚数は 0 のままで、形式 9 は形式 8 にその項目（0）を加えたもの。形式 10 はない」にした | 形式 9 を加えた（4.2） |
| tests/test_stage2_v0_4c.py `test_serialization_keeps_format_8`・tests/test_forced_switch_v0_4d.py `test_serialization_keeps_format_8`・tests/test_harden_v0_4b.py `test_format_8`・tests/test_rng_and_serialize.py `test_unknown_format_is_rejected` | 形式の一覧の最後を 9 にし、形式 9 でも重なり・決定・持続する効果の項目が形式 8 と同じことを加えた。知らない形式の例を 9 から 10 にした | 同上（2 進化・強制交代・持続する効果のために形式を加えていないことは変わらない） |
| tests/test_effects.py `test_attacks_with_text_follow_the_verified_latest_description`・`test_with_and_without_do_not_change_the_original` | 説明文のあるワザの一覧にあわ・からにこもる（2 つ）・ハイドロポンプを加え、ワザの登録の数を 38 → 43、パワーを 2 つにした | 登録を加えた |
| tests/test_trainers.py・tests/test_rng_and_serialize.py `test_format_2_adds_only_documented_fields`・各対戦のテストの `GOLDEN_DIGEST` の前の `effects`（v0.4a・v0.4b・v0.4c・v0.4d・v0.5） | 登録表の id を `kyuura-engine-0.6` にした（固定値の指紋は変えていない） | 登録の中身が変わった |
| tests/test_unresolved_boundaries_v0_4e.py | コードの一覧に `UNRESOLVED_ATTACH_AFTER_POWER_ATTACH` を加え、止まる場合と隣の止まらない場合（`AttachAfterPowerAttachBoundaryTest`）を加えた。書き出しで比べる形式をクラスごとに選べるようにした（既定は 8 のまま） | ファイルの約束（新しいコードを加えたら、止まる場合と隣の止まらない場合を加える） |
| tests/test_effect_preflight_v0_3d.py `ATTACKS` | あわ・からにこもる（ゼニガメ）・ハイドロポンプを加えた | CLAUDE.md（ワザの実装を加えたら `ATTACKS` にも加える） |
| tests/helpers.py | ゼニガメ・カメール・フーディンの定数を加え、カメックスの説明を直した | — |

## 12. この先の変更で気をつけること（ほかのポケモンパワーへの提案。実装していない）

| 種類 | 例 | 要るもの |
|---|---|---|
| 手札・山札・トラッシュからカードを出すパワー | — | `zones.attach_energy_from_hand` と同じく、ゾーンの間の移動を 1 か所の関数にし、確かめることは呼ぶ側が動かす前に済ませる。ログの監査の手札（ほかのゾーンも）の組み立て直しに加える |
| 回数の制限（「自分の番ごとに1回」） | タケシのキュウコン［ばける］（p.70） | 使った回数を状態に持つ（ポケモンごと・番ごと）。v0.6 の `energy_attached_by_powers_this_turn` と同じく、番の最初の 0・不変条件（ログとの対応）・書き出しの形式（10）を加える。進化・ベンチに戻る・番の終わりでの扱いを原典で確かめる |
| ダメージカウンターの移動 | フーディン［ダメージスワップ］（p.153。v0.6 の参照カード） | p.320「ダメージカウンターの移動」（ワザによるダメージではない）。「きぜつしないかぎり」の判定を状態を変える前に。ログの監査のダメージの組み立て直しに移動を加える |
| 常にはたらく・パワーを止める | ベトベトン［かがくへんかガス］（p.48・p.323）・わるいアーボックの「ショックアイ」（p.24。ワザの持続する効果） | `check_usable` の前に、場の常にはたらく効果・持続する効果を調べる仕組み（あまごい・エナジートランスを含むすべてのパワーの使用に影響する） |
| 特殊エネルギー | レインボーエネルギー（p.298。手札では色を持たないので、あまごいでつけられない） | 特殊エネルギーのカードと登録。あまごいのカードの判定（今は「水」の基本エネルギー）と、エナジートランスの移せるエネルギーの判定を、「場にあるときのタイプ」と「手札でのタイプ」を分けて見直す |
| R13 が決まったら | — | 原典で決まれば、`engine._attach_energy` の停止を、決まった処理（受け付ける・`ENERGY_ALREADY_ATTACHED`）に置きかえる。分類を変えるときは、根拠の誌面と読み方の比較を [unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md) のように書く |
