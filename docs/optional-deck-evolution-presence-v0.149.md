# v0.149: 任意の山札進化の決定の有無と、秘密領域の候補集合の情報漏れの修正（両モード共通）

利用者の指示（2026-11-06）で、次の 2 つを一つの限定タスクとして、両モード共通の不具合として直しました。新しい続行規約は採用していません。研究上の問い（FV1・RB1・NB1・DV2・GV1・H1・PW4
など）は決めていません。公式の裁定・研究上の解決として記録するものではありません。

- A. `PSP-OPTIONAL-DECK-EVOLUTION-DECISION-PRESENCE`（v0.148 で見つけた）: たきのぼりしんか・つきのちからで、検索の決定が出るかどうかから山札の内容が分かる
- B. `PSP-HIDDEN-SET-ASIDE-DECK-POOL`（この版で見つけた）: 熱血!・［おたけび］・マスターボール neo・`hidden_deck_pool` の候補集合が、持ち主に見えない置いておくカードを含まない

## 1. 基点と範囲

- 基点: `c399045`（v0.148 の最後。ブランチ `claude/attack-deck-evolution-preflight`。main には未マージ）。作業ブランチ `claude/optional-deck-evolution-presence`
- 作業の始まりに、利用者の作業ツリー（`C:\dev\kyuura-engine`）に改行コードだけの差分（17 ファイル。`git diff --ignore-cr-at-eol` で差 0）と `.claude/` があったので、触らずに別の作業ツリーで作業した
- 削除済みの Codex の作業は使っていない。kyuura は読み取りだけ（この版では読んでいない）
- 3 つの集合（`CS-KYUURA-CURRENT@1`・`CS-KYUURA-PLAY-S2A@1`・`CS-KYUURA-PLAY-PO@1`）の ID・版・中身・照合値は変えていない
- 盤面の種類を分ける: 構築盤面（`build_test_state`）、構築盤面からの合法な操作（`tickled`: 相手がくすぐりマシーンを使い「おもて」で番を終える）、テストだけの双子の操作
  （`swap_hidden`・`swap_set_aside`）、補助関数だけの確かめ。`new_game` からの合法な操作の列での再現はしていない（構築盤面で通ったことを、合法な対戦からの到達として数えない）

## 2. A: 任意の山札進化の決定の有無

### 2.1 時点の整理

| 時点 | たきのぼりしんか（`EvolveAttackerFromDeck`。任意） | つきのちから（`EvolveFromDeck`） |
|---|---|---|
| 宣言（受理・拒否） | 宣言の前の先読み。山札を見る前の確かめは v0.148 で配分によらない | 同じ |
| コインを投げる | なし | ワザの最初（「うら」なら山札を見ない・切らない） |
| 山札を見ることが許される | 要素の処理に入ったとき（「選び出し」） | 「おもて」のあと |
| 進化先の決定を要求する条件 | 山札にカードがあるとき（v0.149。v0.148 までは選べるカードがあるときだけ） | 同じ（v0.149） |
| 決定の形 | `SEARCH_DECK` の 0〜1 枚（「つけてよい」。選べるものが空でも最大は 1 のまま） | 選べるカードがあれば 1〜1 枚（「のせる」）、なければ 0〜0 枚（v0.84 の A3） |
| 任意の進化を断る | 0 枚の答え（決定の答えのとき。山札を見たあと） | 断れない（選べるカードがあれば 1 枚） |
| 答えのあと | 重ねる・`evolve_from_deck_declined`（0 枚。理由は本人だけ）→ 切る | 重ねる（重ねるポケモンが 2 匹以上なら `SELECT_POKEMON`）・`evolve_from_deck_none` → 切る |
| 山札が 0 枚 | 決定を出さずに `evolve_from_deck_none` と切る（枚数は公開） | 同じ |

### 2.2 相手・観戦者に見えるものと、v0.148 までの違い

- 決定の観測: `SEARCH_DECK` は `HIDDEN_COUNT_KINDS` なので、相手・観戦者には種類と決めるプレイヤーだけ（選べるものの数・空であること・`min_choices`・`max_choices` は見せない）。
  本人には選べるもの（実際の山札のカード）とカードの id
- v0.148 までは、選べるカードがなければ決定を出さずに `evolve_from_deck_none` で進んだ。相手・観戦者は、宣言のあと決定を待つか（`decision` が `{"kind": "search_deck", "player": 0}` か
  `None` か）とログで、選べる進化カードが山札にあるかを知れた。たきのぼりしんかは、0 枚の答え（`evolve_from_deck_declined`）と選べるカードがない（`evolve_from_deck_none`）のログの種類も
  違った
- 相手の答え・不正な答えの拒否の理由の文は、双子で同じ（選べるものの数・中身を書かない。`InvalidAnswerTest`）

### 2.3 v0.84 の必ず重ねる経路（A3）との共通点・相違点

- 共通: 山札にカードがあれば、選べるカードがなくても決定を出して答えを待つ。決定の有無・進み方・切る時点を山札の中身で変えない。選べるものの数は決めるプレイヤーだけ
- 相違: 必ず重ねる経路（からやぶりしんかなど）は 1〜1 枚・空なら 0〜0 枚。たきのぼりしんかは任意なので、選べるものが空でも 0〜1 枚のまま（最大の枚数を選べるものの数で小さくしない。
  v0.113 の「みんなでおどる」と同じ考え方）。任意の辞退と選べるカードがないことを、同じ公開のログ（`evolve_from_deck_declined`）にし、理由（`reason` の `declined`・`no_target`）を
  本人だけが見る（`observation.PRIVATE_FIELDS`。v0.84 のみずかきの `deck_top_take_declined` と同じ）
- 任意と必須を混同しない: たきのぼりしんかの決定は 0 枚の答えを受け付ける（任意の辞退）。つきのちからは選べるカードがあれば 0 枚の答えを受け付けない（決定の形の確かめ
  `EvolveFromDeckOnHeads.decision_problems` も、選べるカードがあれば 1〜1 枚、なければ 0〜0 枚）

### 2.4 ルール上公開される情報との区別

- 検索が実際に行われたこと（決定を待つこと・山札を切ること）は公開。どちらの双子でも同じ
- 本人が山札を見たあとに得る情報（選べるもの・選ばなかった理由）は本人だけ。相手・観戦者へ出さない
- 答えのあとの結果（場のポケモンが進化した `evolve`・しなかった）は場の公開の情報。つきのちからは「のせる」（「てよい」がない）ので、選べるカードがあれば必ず進化し、
  進化しなかったことから選べるカードがなかったことが分かる。これは原文の処理が公開する結果（v0.84 の A3・v0.105 の `test_hidden_deck_contents_do_not_leak` と同じ区別）で、
  修正の対象ではない（`test_moon_power_result_is_the_public_outcome`）。たきのぼりしんかは任意なので、進化しなかったことからは分からない

### 2.5 修正の前の再現（構築盤面と双子）

`tests/test_optional_deck_evolution_presence_v0_149.py` を修正の前の木（`c399045`）で動かした（別件の `expectedFailure` 2 つを加える前の 17 テスト。failures 35・errors 12）:

- `test_opponent_and_spectator_see_the_same_after_declaration`: 4 つの盤面（たきのぼりしんか・つきのちから × 山札とサイドの双子・山札と持ち主に見えない置いておくカードの双子）×
  3 つの集合の 12 すべてで、宣言のあとの相手・観戦者の観測が違った
- `test_waterfall_declining_and_finding_nothing_look_the_same`: 6 すべてで、0 枚の答えのあとの公開のログが違った
- errors は、修正の前の木で決定が出ない側の盤面を答えようとしたもの（決定がない）と、文書がないもの

### 2.6 修正（`kyuura_engine/resolution/programs.py`・`observation.py`・`effects.py`）

- `EvolveAttackerFromDeck.run`（任意の経路）: 山札が 0 枚なら今までどおり `evolve_from_deck_none`。そうでなければ、選べるカードが空でも決定（0〜1 枚）を出す。`resume` の 0 枚の答えは
  `evolve_from_deck_declined`（`reason` は `declined`・`no_target`）と切る
- `EvolveFromDeck.run`: 選べるカードがなく山札にカードがあれば、選べるもののない決定（0〜0 枚）を出す。`resume` の 0 枚の答えは `evolve_from_deck_none` と切る（選べるカードが
  あるのに 0 枚の答えが来たら、決定の形の誤りとして `RuntimeError`。決定の確かめが 1〜1 枚にするので、正常な操作からは来ない）
- `observation.PRIVATE_FIELDS` に `evolve_from_deck_declined` の `reason`（本人だけ）を加え、`PUBLIC_EVENTS` から移した
- `EvolveFromDeckOnHeads.decision_problems`: 選べるカードがなければ 0〜0 枚の形を受け付け、山札が 0 枚なのに決定があれば問題にする

## 3. B: 秘密領域の候補集合

### 3.1 情報の区別

| 情報 | 本人 | 相手・観戦者 | 山札の上・山札の中にありうるか |
|---|---|---|---|
| 実際の山札（うらのカード） | 中身の集合は分かる（ほかと合わせて）。どれが山札かは分からない | 枚数だけ | 当然ありうる |
| 表向きの山札（フラッシュ） | 見える | 見える | 山札にある（分かっている） |
| うらのサイド（本人にも見えない） | 同上（山札と合わせた集合だけ） | 枚数だけ | ありうる（山札のうらのカードと入れかえられる） |
| おもてのサイド（ロケット団参上!） | 見える | 見える | ありえない（サイドにあると分かっている） |
| 持ち主に見えない置いておくカード（くすぐりマシーン。`visible_to` が空） | 中身は見えない（置く前に手札で見たが、エンジンは過去の情報を使わない） | 枚数だけ | ありうると扱う（`unseen_card_pool` の山札の外の見えないカード） |
| 持ち主が見られる置いておくカード（挑戦状・クイズ） | 見える | 持ち主だけ | ありえない |

`effects.unseen_card_pool` は v0.137 から、山札のうらのカードと「山札の外の見えないカード」（うらのサイドと持ち主に見えない置いておくカード）を分けて持ちます。`possible_deck_cards`
（v0.147）と `searchable_deck_cards`（v0.148）はこれを使うので、持ち主に見えない置いておくカードを含み、おもてのサイドを含みません。

### 3.2 各確かめが保証すること

どれも「山札の上（または山札の中）に止めるカードがありうるなら、使う前に止める」確かめです。必要なのは、本人が知っている情報だけで決まる集合のうち、山札にありうるカードを
すべて含むこと（含まないと、止めるカードが山札と置いておくカードのどちらにあるかで受理・拒否が変わる）と、ありえないカードで止めないこと（止めすぎで、漏れではない）。

| 対象 | 確かめ（コード） | 時点 | v0.148 までの集合 | 必要な集合 |
|---|---|---|---|---|
| 熱血!（GD5-021） | `DiscardDeckTopThenReturnTypeEnergy.check_playable`（FV1） | 使う前（山札の上 3 枚をトラッシュする前） | 山札 + すべてのサイド | `searchable_deck_cards` |
| マスターボール neo（NIP1-021・NIP2-022） | `LookTopTakePokemonThenShuffle.check_playable`（NB1） | 使う前（上 7 枚を見る前） | 山札 + すべてのサイド | `searchable_deck_cards` |
| ［おたけび］（neo3-010） | `DiscardDeckTopAttachTypeEnergyThenEndTurn.accept_problem`（RB1・ミラクルエネルギー） | 使う機会の答え（上 5 枚をトラッシュする前） | 山札 + すべてのサイド | `searchable_deck_cards` |
| 山札の上からトラッシュするワザ（マグマラッシュ・やまくずし・マグマふんしゅつ） | `hidden_deck_pool`（FV1・数の範囲） | 宣言の前の先読み（トラッシュしたあとの要素で） | トラッシュしたカード + 残りの山札 + すべてのサイド | トラッシュしたカード + `possible_deck_cards` |

`hidden_deck_pool` は、トラッシュしたあとの山札にうらのカードがなくても、トラッシュする前はあったので、`searchable_deck_cards`（山札にうらのカードがなければ山札だけ）は使いません。
使うと、トラッシュする前の山札の中身（＝トラッシュしたカード）だけが集合に残り、宣言の前の先読みで配分が漏れます。合わせた集合（トラッシュしたカード + 山札 + うらのサイド +
見えない置いておくカード）は、配分によりません。

### 3.3 修正の前の再現

修正の前の木（`c399045`）で、止めるカード 1 枚を動かす双子を比べた（`HiddenSetAsideTwinTest`。構築盤面から相手のくすぐりマシーンを合法な操作で使った盤面）:

| 対象 | 山札とうらのサイドの双子 | 山札と持ち主に見えない置いておくカードの双子 |
|---|---|---|
| 熱血! FV1 | 同じ（どちらも拒否） | **違う**（山札なら拒否・置いておくカードなら受理） |
| マスターボール neo NB1 | 同じ | **違う** |
| ［おたけび］ RB1 | 同じ | **違う**（さらに、理由の文にレインボーエネルギーの uid） |
| マグマラッシュ FV1（`hidden_deck_pool`） | 同じ | **違う**（さらに、理由の文にレインボーエネルギーの uid） |

山札とサイドだけの双子では配分によらない（v0.147 の 1 章の「山札とサイドを合わせた集合を読む確かめは配分によらない」は、この双子の範囲では正しい）が、置いておくカードの双子を
試していませんでした（`PSP-DECK-CONTENT-PRECHECKS` の `v0149_followup`）。

## 4. B: 修正

- 熱血!・マスターボール neo・［おたけび］の候補集合を `searchable_deck_cards` に替えた
- `hidden_deck_pool` を、トラッシュしたカードと `possible_deck_cards` に替えた
- ［おたけび］の RB1 の理由の文を、uid を書かない決まった文（v0.147 の `rainbow_possible_in_deck_error`）にした。`milled_type_energy` の FV1 の問いの詳細も、uid を書かない文にした
- 止めるコードは同じ。FV1・RB1・NB1 の問いの条件（どのカードが当たるか）は変えていない

## 5. 検証

### 5.1 新しいテスト（`tests/test_optional_deck_evolution_presence_v0_149.py`。19 テスト。うち 2 つは別件の `expectedFailure`）

| クラス | 確かめること | 盤面の種類 |
|---|---|---|
| `DecisionPresenceTwinTest` | 宣言のあと・0 枚の答えのあとの相手・観戦者の観測とログが双子で同じ（3 つの集合）。つきのちからの答えのあとの結果は公開の結果として分かれる | 構築盤面・合法な操作（くすぐりマシーン）・双子 |
| `OwnerChoiceTest` | 本人の選択に実際の山札（候補あり・なし・辞退・山札 0 枚・コインの両面） | 構築盤面 |
| `InvalidAnswerTest` | 不正な答え（選べないカード・数の違う答え・相手の答え）で状態・乱数・ログが変わらない。理由の文は双子で同じ | 構築盤面・双子 |
| `SaveRestoreTest` | 決定を待つ状態を保存・復元しても同じ決定・同じ結果（pickle の往復） | 構築盤面・双子 |
| `V148PreflightTest` | v0.148 の宣言の前の双子（6 つ。H1 は判定の差しかえ）が 3 つの集合で同じ | 構築盤面・判定の差しかえ |
| `HiddenSetAsideTwinTest` | B の 4 つの対象が、山札とサイド・山札と置いておくカードの双子で同じ（3 つの集合）。理由の文に見えないカードの uid がない | 構築盤面・合法な操作・双子 |
| `SetAsideBoundaryTest` | 置いておくカードだけにあっても止める・おもてのサイドだけなら止めない・どこにもなければ受理・補助関数の集合 | 構築盤面・補助関数だけ |
| `RemainingDecisionPresenceLeakTest` | 別件（6 章）。`expectedFailure` | 構築盤面・双子 |

v0.148 の `RemainingDecisionPresenceLeakTest`（`expectedFailure`）は、`DecisionPresenceNoLeakTest` に名前を変え、印を外して、相手と観戦者の両方の観測とログが同じことを確かめる通常の
テストにしました（`tests/test_attack_deck_evolution_preflight_v0_148.py`）。

### 5.2 実行したテスト（モジュールを 1 つずつ。単独）

修正の後の木で OK: test_optional_deck_evolution_presence_v0_149（文書を書いたあと）・test_attack_deck_evolution_preflight_v0_148・test_deck_content_prechecks_v0_147・
test_search_evolution_once_attacks_v0_44・test_power_decisions_v0_42・test_power_decisions_v0_42_games・test_recovery_evolution_coin_branches_v0_105・test_private_looks_deck_movement_v0_95・
test_search_recovery_trainers_v0_73・test_entry_energy_evolution_reactions_v0_86・test_baby_rules_evolution_v0_114・test_hidden_card_trainers_v0_63・test_light_powers_evolution_v0_84・
test_declared_entry_powers_v0_43・test_remaining_stadiums_v0_74・test_fossil_hidden_info_v0_47・test_effective_pokemon_properties_v0_48・test_play_policy_family_plan・
test_stop_policy_classification・test_conventions_v0_142（規約集合の ID・版・中身・照合値と同梱の記録）・test_preset_decks_v0_20。

test_search_recovery_trainers_v0_73 の 2 つは、この環境（Windows の既定の文字コード cp932）で `read_text()` が文字コードを指定しないために読めない（この版と関係のない既存のテストの
環境依存）。`PYTHONUTF8=1` で OK。最後に、この節の 21 モジュールをすべて `PYTHONUTF8=1` で 1 つずつ動かし直し、すべて OK（新しいテストは 19 テストのうち 2 つが予期した失敗）。

### 5.3 自然な対戦（少数の固定の標本）

事前に固定: 組 v0.42（つきのちから）・v0.44（たきのぼりしんか）、seed 0〜1（`tools/existing_effect_games.py --seeds 2 --start 0`）。目的は、道具の方策が新しい選べるもののない決定に答え、
ログの監査が新しいログを受け付けること。

- v0.42: 20 局（記録の分母。組ごと 4 局 × 5 組）。終端はすべて game_over、監査の失敗 0。エリカのピッピのつきのちからは 6 回（進化 2・`evolve_from_deck_none` 4。記録には決定そのものは
  出ず、山札が 0 枚のときも同じログなので、4 回が新しい選べるもののない決定を通ったかは記録からは確かめていない）
- v0.44: 16 局。終端はすべて game_over、監査の失敗 0。ロケット団のコイキングのたきのぼりしんかは 1 回（記録の数え方では進化・`evolve_from_deck_none` のどちらでもない。選べるものが
  空の決定を通ったかは、記録からは分からない）
- 届かないまま探索は広げていない。修正の前の木との局ごとの比較はしていない（決定が 1 つ増えるので、道具の方策の選び方によっては局の進み方が変わる）

### 5.4 生成物・データ・lint の確かめ（終了コードは検査本体から）

| 検査 | 結果 |
|---|---|
| `scripts/build_stop_policy_classification.py --check` | 0 |
| `scripts/build_play_policy_family_plan.py --check` | 0 |
| `scripts/build_convention_records.py --check` | 0（同梱の記録は場面の索引の 1 行だけが変わった。規約集合の中身は同じ） |
| `scripts/check_implementation_assumptions.py --check`・`scripts/check_normalization_revalidation.py --check` | 0・0 |
| ruff 0.17.2（基点と同じ版・設定。`--statistics`） | 基点 `c399045` と同じ 492（規則ごとの数も同じ）。新しい抑制なし |
| `check_implementation_assumptions --sites` | 基点 198 → この版 198。違いは `tests/test_preset_decks_v0_20.py` 151 行（版の注記の文が変わって ID が S-6d3add18f121 から S-572e092c1f14 に替わっただけ。v0.146〜v0.148 と同じ。新しい仮定ではない）。文面は件数に合わせて変えていない |

### 5.5 実行していない検証

全体テスト・全 108 組・4,356 局の一括計測・lockstep 全体・広範囲のストレステストは実行していない（利用者の指示）。追加の総合検証の提案は 8 章。

## 6. 増えた制限・維持した経路・別件

### 6.1 意図した決定・ログ・操作列の変化

- 山札にカードがあって選べる進化カードがないとき、たきのぼりしんか・つきのちから（「おもて」）は決定を 1 つ待つ（対戦の記録のコマンドが 1 つ増える。本人は 0 枚で答える）
- たきのぼりしんかのこの場合のログは `evolve_from_deck_none` から `evolve_from_deck_declined`（`reason` `no_target`。本人だけ）に変わった。山札が 0 枚のときは `evolve_from_deck_none` のまま
- 新しいログ・決定の種類はない。状態の書き出しの形式は変えていない

### 6.2 増えた保守的な制限

- B: 持ち主に見えない置いておくカード（くすぐりマシーンで置かれた自分の手札）に止めるカード（レインボーエネルギー・ベイビィポケモンカード）があれば、山札になくても熱血!・［おたけび］・
  マスターボール neo・山札の上からトラッシュするワザが止まるようになった（置く前に手札で見たことは使わない。v0.137 の共通処理と同じ）

### 6.3 緩めたもの（明示）

- B: おもてのサイドにだけ止めるカードがあるときは止めなくなった（山札にありえない）。v0.148 までは山札とすべてのサイドを数えて止めた。FV1・RB1・NB1 の問いの条件は変えていない。
  v0.148 のしんかのうたの NB2 と同じ扱い

### 6.4 維持した正常な使用経路

- 選べる進化カードがあるとき: 本人は実際の山札のカードを選んで進化する（たきのぼりしんか・つきのちから。重ねるポケモンが 2 匹以上なら `SELECT_POKEMON`）
- 任意の辞退（たきのぼりしんかの 0 枚の答え）・コインの「うら」（つきのちからは山札を見ない・切らない）・山札が 0 枚（決定なし）
- 宣言の前の確かめ（v0.148）・必ず重ねるワザ（v0.84 の A3・v0.105）・通常の進化の制限・既存の停止
- B: どこにも止めるカードがなければ受理（熱血!など）

### 6.5 既存のテストの調整

| テスト | 本来の目的 | 調整（意図した処理の差） |
|---|---|---|
| test_search_evolution_once_attacks_v0_44 `test_waterfall_evolution_keeps_the_normal_restrictions` | 進化の制限（この番に場に出した・最初の番）でコイキングは進化できない | 選べるもののない決定（0〜1 枚）が出ることを確かめ、0 枚で答えてから同じことを確かめる。ログは `evolve_from_deck_declined`（`no_target`） |
| test_power_decisions_v0_42 `test_moon_power_evolves_from_the_deck` | 重ねられるものがなければ何もせず切る | 選べるもののない決定（0〜0 枚）に答えてから、同じログ（`evolve_from_deck_none`・`shuffle`）を確かめる |
| test_recovery_evolution_coin_branches_v0_105 `test_waterfall_evolution_stays_optional` | たきのぼりしんかの任意性（0〜1 枚）と切る条件が v0.44 のまま | 「選べるものがなければ決定を出さない」（漏れの挙動）の確かめを、決定（0〜1 枚・空）を出して 0 枚の答えで切る確かめに替えた。任意性と切る条件は同じ |
| test_attack_deck_evolution_preflight_v0_148 の 3 テスト（`test_waterfall_evolution_still_evolves_or_finds_nothing`・`test_devolved_without_any_possible_card_is_accepted`・`test_normal_evolution_limits_still_apply`） | 受理・選べるものがない・通常の進化の制限 | 選べるもののない決定に 0 枚で答えてから確かめる |

### 6.6 別件: 同じ形のほかの経路（修正していない）

同じ形（山札に選べるカードがなければ決定を出さずに `…_none` で進む）の分岐の横断で、構築盤面の双子で 2 つを確かめた。この版の範囲の外なので直さず、台帳に
`PSP-DECK-SEARCH-DECISION-PRESENCE-OTHERS`（active）として加え、`RemainingDecisionPresenceLeakTest` を `expectedFailure` で置いた:

- エリカのフシギダネの「おつかい」（`RevealTrainerFromDeck`。任意）: 決定の有無と、0 枚の答えの `reveal_from_deck_declined` と `reveal_from_deck_none` が公開で違う
- キョウのコクーンの［うか］（`CoinEvolveSelfFromDeck`。必ず重ねる特殊能力）: 答えのあとの結果は公開されるが、決定の有無はその前に分かれる（v0.84 の A3 の考え方と合わない）
- 静的な横断だけの候補（確かめていない。漏れとも安全とも数えない）: `attach_energy_from_deck_none`（6 か所）・`bench_from_deck_none`（1 か所）・ほかの `reveal_from_deck_none`（3 か所）

## 7. 候補ごとの結論

| 対象 | 結論 | 根拠 |
|---|---|---|
| たきのぼりしんかの決定の有無・辞退と選べるものなしのログ（A） | **再現して修正** | 2.5・2.6 節 |
| つきのちからの決定の有無（A） | **再現して修正**（答えのあとの結果は原文の処理が公開する） | 2.4〜2.6 節 |
| 熱血! FV1（B） | **再現して修正**（山札と置いておくカードの双子。山札とサイドの双子は修正の前も同じ） | 3.3 節 |
| マスターボール neo NB1（B） | **再現して修正**（同上） | 3.3 節 |
| ［おたけび］ RB1（B） | **再現して修正**（同上。理由の文の uid も） | 3.3 節 |
| `hidden_deck_pool`（マグマラッシュ FV1。B） | **再現して修正**（同上。理由の文の uid も）。やまくずし・マグマふんしゅつは同じ関数（個別の双子は作っていない） | 3.3 節 |
| ［おたけび］のミラクルエネルギーの確かめ | 同じ集合に替えた（双子は作っていない。**未確認**。漏れとも安全とも数えない） | 4 章 |
| 共通の候補集合・下限（`unseen_card_pool`・`possible_deck_cards`・`searchable_deck_cards`・`deck_lower_bound_where`） | 持ち主に見えない置いておくカードを含む（**調べた範囲で配分によらないことを確認**。補助関数の確かめと B の双子） | 3.1 節・`SetAsideBoundaryTest` |
| v0.148 の宣言の前の漏れの再発 | 再発なし（6 つの双子 × 3 つの集合） | `V148PreflightTest` |
| おつかい・［うか］の決定の有無 | **別の問題として分離**（再現。修正していない） | 6.6 節 |
| 同じ形の静的な候補（`attach_energy_from_deck_none` など） | **未確認** | 6.6 節 |

### 7.1 v0.148 の `RuntimeError` のガード

この版で変えた経路の範囲で確かめた: つきのちからの「先の確かめを通ったのに、実際の候補がすべて止める」ガードは、選べるカードがあるときだけに当たる（選べるカードがないときは、
この版から選べるもののない決定になり、ガードの前で決定を出す）。先の確かめ（`deck_choice_may_only_stop`）が使う集合は持ち主に見えない置いておくカードを含む（v0.148 から）。
新しい `resume` の 0 枚の答えのガード（選べるカードがあるのに 0 枚）は、決定が 1〜1 枚なので正常な操作から来ない。正常な操作から到達する反例は見つけていない（広い探索はしていない）。

## 8. 残る不具合と次の候補

- `PSP-DECK-SEARCH-DECISION-PRESENCE-OTHERS`（6.6 節。active）: おつかい・［うか］の決定の有無。直すなら、山札にカードがあれば選べるもののない決定を出す（この版と同じ形）。
  同じ形の静的な候補の確かめ
- ［おたけび］のミラクルエネルギーの経路の双子
- `new_game` からの合法な操作の列での双子（A・B とも。くすぐりマシーンの盤面は構築盤面からの合法な操作）
- 追加の総合検証の提案（実行していない）: 決定の流れが変わる 2 組（v0.42・v0.44）の全 seed と、山札の上からトラッシュするワザ・熱血!・マスターボール neo・エンテイを含む組（v0.73・
  v0.86・v0.95・v0.114）の seed 0〜1（合わせて十数分。1 組ずつ順に）と、マージの前の全体テスト 1 回

この情報漏れの監査を一区切りにできるか: A・B の範囲は一区切りにできる（双子で再現したものは直し、未確認のものは記録した）。ただし、同じ形の決定の有無の漏れ
（`PSP-DECK-SEARCH-DECISION-PRESENCE-OTHERS`）が active で、静的な候補も残るので、山札をさがす効果の決定の有無の監査は一区切りにできない。

## 追記（v0.150）

6.6 節の `PSP-DECK-SEARCH-DECISION-PRESENCE-OTHERS` は v0.150（[deck-search-decision-presence-v0.150.md](deck-search-decision-presence-v0.150.md)）で直しました（山札にカードがあれば選べるカードがなくても決定を出す。静的な候補は現行コードで数え直し、呼び出し元ごとに双子で確かめた）。`RemainingDecisionPresenceLeakTest`（`expectedFailure`）は、`OtherDecisionPresenceNoLeakTest` に名前を変えて、漏れがないことを確かめる通常のテストにしました。8 章の［おたけび］のミラクルエネルギーの確かめは、v0.150 で双子で確かめて問題がないことを確認しました（`HowlMiracleEnergyTwinTest`）。この文書の上の記述は v0.149 の時点の記録として残します。
