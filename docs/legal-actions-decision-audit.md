# v0.162: U7 の決定の入力の監査（情報境界と答えの並び）

v0.161 で情報境界が未確認だった決定 39 種類（`legal_actions.DISCLOSURE_CONFIRMED_KINDS` の外）について、決定を出すすべての箇所の情報源と、回答の適用の並びを調べ、確かめた入力を U7 で示せるようにしました。`kyuura_engine` の版は 0.162.0 です。操作の種類は増やしていません（決定への回答と番を終えるだけ）。エンジンの処理・観測・決定の意味は変えていません。

「未確認の 39 種類」は不具合 39 件という意味ではありません。調べる前は、漏れとも安全とも数えていません。

## 1. 結論

- 39 種類すべてで、選べるもの・選ぶと止める選択（`unresolved_choices`・`unresolved_detail`）・選ぶ数の式は、公開の値・本人のカード・始まった検索・持ち主の知識の関数だけから決まり、本人が知らない秘密の配分を読む出し方は見つからなかった（コードを読んだ判断。2 章の方法）
- 分類（39 種類）: A（情報境界を確かめ、公開できる）38 種類、B（確かめた条件の下だけ公開できる）1 種類（`select_pokemon`。出し方の 1 つは山札の検索のあとだけに出る。条件は出し方の構造で満たされる）、C（不具合を再現し限定修正）0、D（未確認のため非公開）0、E（U7 の外の別件）0
- 答えの並び（39 種類）: 意味がある 6・意味がない 8・選ぶ数が 1 以下 25・未確認 0（3 章）
- U7 は決定の 96 種類すべてで入力を示す。見えないカードが選べるものに来た場面の実行時の確かめ（入力全体を返さない）はそのまま残す
- 不具合は見つけていない（観測・エンジンを直していない）

## 2. 方法

1. **出し方の洗い出し**: `scripts/legal_actions_decision_sites.py` の `scan()` が、パッケージの AST から決定を出す呼び出し（`decisions.push_*`・`AttackRun.suspend`・`codec` の決定・`_boundary_answer`・`_push_cards`）を集め、種類を解決する（定数・クラス属性とその部分型・既知の動的な出し方 `DYNAMIC`）。種類を値として受け取るだけの包み（`WRAPPERS`）は呼ぶ側を数える。走査の結果は 317 の呼び出し・309 の (種類, ファイル, クラス, 関数) の組で、種類の分からない呼び出しはない
2. **情報源のたどり**: 出し方ごとに、選べるものの式の名前の代入を囲む関数の中でさかのぼり、式と代入で呼ぶ補助関数（同じモジュールの関数・同じクラスと基底クラスのメソッド）の本体を深さ 4 まで集め、秘密の領域を指しうる語（山札・サイド・手札・置いておくカード・裏のカード・乱数）と、裏のカードの守りを通らない定義の読み取り（`printed_def`・`definitions[...]`）に印を付けた（監査の補助の道具。リポジトリの外。印がないことは安全の証明ではなく、読む順番の手がかり）
3. **人が読んだ範囲**: 印の付いた出し方（選べるもの 32・選ぶと止める選択と選ぶ数 25・直接の定義の読み取り 8）と、たどれなかった式（`request.options`・`need.choices` など 6）と、動的な出し方（20）を読んだ。印のない出し方は、選べるもの・代入・補助関数の名前の一覧を読んだ
4. **裏のカード**: `GameState.card_def` は、うらにしてベンチに出したカード（マチスの秘策）に `FACE_DOWN_DEFINITION` を返す。裏のカードの印が付いた出し方は、どれも裏であること（公開）だけで一律に除くか選ぶと止める選択にし、本当のカードを読まない（直接の定義の読み取りは、裏でないことを確かめたあとか、公開のカード・答えの適用）
5. **答えの並び**: 選ぶ数の上限が 1 でない出し方（39 種類のうち 14 種類）について、回答の適用（`resume`・`apply` とそこから呼ぶゾーンの関数）まで読んだ

実行での確かめ（構築盤面・new_game からの操作の列）は 5 章。長い到達の探索はしていない。

### 2.1 情報源の区分

<!-- generated:audit-categories begin -->
| 区分 | 意味 |
|---|---|
| `public` | 公開の値（場のポケモン・ついているカード・トラッシュ・公開の枚数・決まった語彙） |
| `own_cards` | 本人の手札と本人に見えるカード（決める人が持ち主） |
| `started_search` | 正当に始まった検索・閲覧で本人が見ているカード（契約の例外） |
| `owner_knowledge` | 選べるものは公開・本人のカード。選ぶと止める選択は持ち主の知識だけで決まる関数（searchable_deck_cards・deck_target_lower_bound など） |
| `inherits` | 退避した決定を同じ種類・選べるもので戻す（元の出し方の情報源を引き継ぐ） |

| 答えの並び | 意味 |
|---|---|
| `single` | 選ぶ数が 1 以下 |
| `significant` | 答えの並びが結果（ゾーンの並び・ログ・解決の順）に入る |
| `not_significant` | 適用の前に決まった並びに直す |
| `unconfirmed` | 確かめていない（v0.162 の対象の 39 種類の外） |
<!-- generated:audit-categories end -->

## 3. 種類ごとの結論

<!-- generated:audit-kinds begin -->
| 決定の種類 | 出し方の数 | 情報源の区分 | U7 の入力 | 答えの並び |
|---|---|---|---|---|
| `accept_request` | 6 | public 6 | confirmed | single |
| `allocate_damage` | 1 | public 1 | confirmed | single |
| `arrange_deck_top` | 4 | started_search 4 | confirmed（契約の例外） | significant |
| `attach_from_deck` | 8 | started_search 8 | confirmed（契約の例外） | unconfirmed |
| `attach_from_discard` | 2 | public 2 | confirmed | not_significant |
| `attach_from_hand` | 2 | own_cards 2 | confirmed | not_significant |
| `attach_to_bench` | 4 | public 4 | confirmed | single |
| `bench_from_deck` | 9 | started_search 9 | confirmed（契約の例外） | unconfirmed |
| `bench_from_deck_or_hand` | 1 | started_search 1 | confirmed（契約の例外） | single |
| `bench_from_discard` | 6 | public 6 | confirmed | single |
| `bench_guard` | 2 | public 2 | confirmed | significant |
| `challenge_bench` | 1 | started_search 1 | confirmed（契約の例外） | unconfirmed |
| `damage_option` | 2 | public 2 | confirmed | single |
| `damage_reduction` | 1 | public 1 | confirmed | single |
| `damage_step_order` | 1 | public 1 | confirmed | single |
| `deck_top_from_hand` | 1 | own_cards 1 | confirmed | single |
| `discard_energy` | 6 | public 6 | confirmed | significant |
| `discard_from_hand` | 10 | own_cards 10 | confirmed | unconfirmed |
| `discard_opponent_energy` | 6 | public 6 | confirmed | not_significant |
| `discard_stadium` | 1 | public 1 | confirmed | single |
| `discard_to_deck` | 5 | public 5 | confirmed | not_significant |
| `discard_to_deck_top` | 2 | public 2 | confirmed | unconfirmed |
| `energy_drain_discard` | 1 | public 1 | confirmed | single |
| `entry_power` | 1 | public 1 | confirmed | single |
| `esp_redo` | 1 | public 1 | confirmed | single |
| `evolution_heal` | 4 | public 4 | confirmed | single |
| `evolution_song_pokemon` | 2 | owner_knowledge 2 | confirmed | single |
| `exp_all_energy` | 2 | public 2 | confirmed | single |
| `forced_switch` | 1 | public 1 | confirmed | single |
| `hand_to_active` | 1 | own_cards 1 | confirmed | single |
| `hand_to_deck` | 5 | own_cards 5 | confirmed | unconfirmed |
| `heal_allocation` | 1 | public 1 | confirmed | single |
| `janken_hand` | 2 | public 2 | confirmed | single |
| `knock_out_power` | 1 | public 1 | confirmed | single |
| `ko_prevention` | 1 | public 1 | confirmed | single |
| `magma_pool_energy` | 2 | public 2 | confirmed | single |
| `move_energy` | 5 | public 5 | confirmed | significant |
| `move_opponent_energy` | 2 | public 2 | confirmed | single |
| `ninja_trick` | 1 | public 1 | confirmed | single |
| `opponent_hand_to_bench` | 3 | started_search 3 | confirmed（契約の例外） | unconfirmed |
| `opponent_hand_to_deck` | 4 | started_search 4 | confirmed（契約の例外） | single |
| `optional_coin` | 1 | public 1 | confirmed | single |
| `optional_discard_all` | 1 | public 1 | confirmed | single |
| `optional_drain` | 1 | public 1 | confirmed | single |
| `optional_heal` | 1 | public 1 | confirmed | single |
| `optional_shuffle` | 1 | public 1 | confirmed | single |
| `peek_card` | 1 | own_cards 1 | confirmed | single |
| `post_knockout_power` | 2 | public 2 | confirmed | single |
| `prize_first` | 2 | public 2 | confirmed | single |
| `promote_active` | 2 | public 2 | confirmed | single |
| `quiz_answer` | 3 | public 3 | confirmed | single |
| `quiz_attack` | 1 | public 1 | confirmed | single |
| `quiz_card` | 3 | own_cards 3 | confirmed | single |
| `quiz_height_answer` | 1 | public 1 | confirmed | single |
| `reaction_order` | 2 | public 2 | confirmed | single |
| `reaction_power` | 2 | public 2 | confirmed | single |
| `reaction_switch` | 1 | public 1 | confirmed | single |
| `recover_energy` | 3 | public 3 | confirmed | significant |
| `recover_pokemon` | 4 | public 4 | confirmed | not_significant |
| `recover_trainer` | 5 | public 5 | confirmed | not_significant |
| `remove_counters` | 1 | public 1 | confirmed | single |
| `retrieve_energy` | 2 | own_cards 1・public 1 | confirmed | not_significant |
| `return_energy` | 3 | public 3 | confirmed | significant |
| `return_to_deck` | 2 | own_cards 1・owner_knowledge 1 | confirmed | single |
| `revive_source` | 1 | own_cards 1 | confirmed | single |
| `search_deck` | 21 | started_search 21 | confirmed（契約の例外） | unconfirmed |
| `search_deck_or_discard` | 1 | started_search 1 | confirmed（契約の例外） | single |
| `secret_plan_card` | 1 | own_cards 1 | confirmed | single |
| `select_attached_special_energy` | 1 | public 1 | confirmed | single |
| `select_attached_trainer` | 1 | public 1 | confirmed | single |
| `select_attack` | 2 | public 2 | confirmed | single |
| `select_color` | 6 | public 6 | confirmed | single |
| `select_counter_count` | 2 | public 2 | confirmed | single |
| `select_deck_owner` | 1 | public 1 | confirmed | single |
| `select_devolve_count` | 1 | public 1 | confirmed | single |
| `select_draw_count` | 3 | public 3 | confirmed | unconfirmed |
| `select_evolution_card` | 4 | own_cards 4 | confirmed | single |
| `select_exchange_card` | 2 | started_search 2 | confirmed（契約の例外） | single |
| `select_hand_card` | 1 | public 1 | confirmed | single |
| `select_hand_positions` | 1 | public 1 | confirmed | not_significant |
| `select_look_count` | 3 | public 3 | confirmed | single |
| `select_marker_count` | 1 | public 1 | confirmed | single |
| `select_opponent_attack` | 1 | public 1 | confirmed | single |
| `select_opponent_prize` | 1 | public 1 | confirmed | single |
| `select_pokemon` | 67 | own_cards 1・public 65・started_search 1 | confirmed | significant |
| `select_prize_card` | 4 | public 4 | confirmed | single |
| `select_special_condition` | 2 | public 2 | confirmed | single |
| `split_from_deck` | 1 | started_search 1 | confirmed（契約の例外） | unconfirmed |
| `stadium_from_discard` | 1 | public 1 | confirmed | single |
| `stadium_return_bench` | 1 | public 1 | confirmed | single |
| `swap_with_prize` | 1 | own_cards 1 | confirmed | single |
| `take_looked_cards` | 4 | started_search 4 | confirmed（契約の例外） | unconfirmed |
| `take_looked_pokemon` | 1 | started_search 1 | confirmed（契約の例外） | single |
| `take_looked_trainer` | 1 | started_search 1 | confirmed（契約の例外） | single |
| `take_prize` | 3 | public 3 | confirmed | single |
| `use_discard_trainer` | 1 | public 1 | confirmed | single |
<!-- generated:audit-kinds end -->

共通処理ごとの根拠（39 種類。調査の順序どおり）:

- **頻出の決定**: `select_pokemon`（67 の出し方）は、場のポケモンの番号（`in_play()`・`bench`）を、公開の状態（ダメージ・名前・タイプの読み方・進化の重なり・持続する効果・裏であること）で絞る。山札からの進化の 2 経路のうち、ワザの `EvolveChosenFromDeck` の止める理由は山札を見る前の公開の問い（`self_deck_evolution_open_question`。v0.105）、`EvolveFromDeck.resume` は山札の検索（`search_deck`）で本人が選んだカードについての対象（B）。`select_color` は決まった色の語彙と、場のカード・効果の読み方
- **複数カード・トラッシュ・付け替え**: `discard_energy`・`discard_opponent_energy`・`move_energy`・`move_opponent_energy`・`return_energy`・`attach_to_bench` は場のポケモンについているカード（公開）、`recover_*`・`retrieve_energy`・`bench_from_discard`・`discard_to_deck`・`stadium_from_discard`・`use_discard_trainer`・`attach_from_discard` はトラッシュ（公開）、`attach_from_hand`・`return_to_deck`・`secret_plan_card`・`quiz_card`・`select_evolution_card`・`revive_source` は本人の手札（`return_to_deck` の止める理由は持ち主の知識の下限 `deck_target_lower_bound`）
- **特殊な検索・コピー・反応**: `evolution_song_pokemon` の選べるものは本人の場のポケモン全部、止める理由は持ち主の知識の関数（`searchable_deck_cards`・`deck_choice_may_only_stop`。v0.148〜v0.149）。`select_attack` は場のポケモンのワザ（公開）。`ninja_trick`・`reaction_switch`・`ko_prevention`・`bench_guard`・`post_knockout_power` は相手のワザ・きぜつへの反応で、選べるものは控え・反応するポケモン・きぜつしたカード（公開）。`damage_reduction` は計算したダメージ（公開）までの範囲、`select_hand_positions` は相手の手札の枚数（公開）の位置、`select_opponent_prize` は相手のうらのサイドの位置（公開の枚数）、`select_deck_owner` は 2 人のプレイヤー
- **同じ種類の別の出し方**: 出し方ごとの表（4 章）に分けた。同じ種類で情報源の区分が違う出し方（例: `select_pokemon` の public と started_search）は、どれも公開してよい区分なので種類として公開する
- **退避した決定の復元**（`reactions._run_step` の RESTORE）: 退避した決定を同じ種類・選べるもので戻す。元の出し方の情報源を引き継ぐ
- **相手の番に答える決定**: `bench_guard`・`ninja_trick`・`reaction_switch`・`ko_prevention`・`energy_drain_discard`・`exp_all_energy` などは、ワザを使うプレイヤーでない人が決める。U7 は決定の回答者を番・段階より先に決める（v0.161）

### 3.1 答えの並び

- **意味がある**（6）: `bench_guard`（かわりに受けるサイドンの並び）・`discard_energy`（ワザの `DiscardOwnEnergy`）・`move_energy`（バブルジャンプ）・`recover_energy`（ワザの `RecoverEnergy`）・`return_energy`（ワザの `ReturnOwnEnergyToHand`）・`select_pokemon`（`ChosenBenchDamages` のダメージの順）。どれも、ゾーンの並び・ログ・ダメージときぜつの処理の順に入る。同じ種類のほかの出し方は決まった並びに直すが、種類としては意味があるに分ける
- **意味がない**（8）: `attach_from_discard`・`attach_from_hand`・`discard_opponent_energy`・`discard_to_deck`・`recover_pokemon`・`recover_trainer`・`retrieve_energy`・`select_hand_positions`。どの複数選択の出し方も、適用の前に場・トラッシュ・手札の並び（または位置の小さい順）に直す（カードの移動・ログ・乱数は答えの並びによらない）
- **選ぶ数が 1 以下**（25）: すべての出し方で上限が 1
- v0.161 の確かめ（`arrange_deck_top` は意味がある）は変えていない。39 種類の外で複数選択の出し方があり、並びを確かめていない種類（`discard_from_hand`・`hand_to_deck`・山札の検索の種類など）は `unconfirmed` のまま（入力は示す。順不同と称さない）
- U7 は `inputs`・`check`・`submit` で並びを変えず、集合にしない。重なりは `check_choices` と同じく不正。選ぶ数（`count`）と並び（`order`）は別の項目

## 4. 出し方ごとの一覧

<!-- generated:audit-sites begin -->
| 決定の種類 | 出し方（ファイル・クラス.関数） | 決める人 | 選べるものの式 | 選ぶ数の上限 | 情報源 | 答えの並び |
|---|---|---|---|---|---|---|
| `accept_request` | `effects.py` EachPlayerMayReturnHandThenDrawOnEntry._ask | `player` | `(1,)` | `1` | public | single |
| `accept_request` | `effects.py` EachPlayerSearchToolOnEntry._ask | `self._chooser(use, stage)` | `(1,)` | `1` | public | single |
| `accept_request` | `effects.py` LookOpponentPrizesMayRedeal.resolve | `use.player` | `(1,)` | `1` | public | single |
| `accept_request` | `effects.py` ._ask_opponent | `1 - use.player` | `(1,)` | `1` | public | single |
| `accept_request` | `effects.py` SwapPleaseTrainer.resume | `opponent` | `(1,)` | `1` | public | single |
| `accept_request` | `engine.py` ._chaos_tails | `borrower` | `(1,)` | `1` | public | single |
| `allocate_damage` | `resolution/programs.py` AllocateDamage.run | `chooser` | `tuple(range(len(table)))` | `1` | public | single |
| `arrange_deck_top` | `effects.py` ArrangeOwnDeckTopTrainer.resume | `use.player` | `cards` | `count` | started_search | significant |
| `arrange_deck_top` | `effects.py` FlashTrainer._offer | `player` | `cards` | `FLASH_COUNT` | started_search | significant |
| `arrange_deck_top` | `effects.py` ShuffleThenArrangeDeckTop.resolve | `use.player` | `cards` | `self.look` | started_search | significant |
| `arrange_deck_top` | `resolution/programs.py` ArrangeDeckTop._look | `run.player` | `cards` | `count` | started_search | significant |
| `attach_from_deck` | `effects.py` CoinAttachEnergyFromDeckToOwnPokemon.resolve | `use.player` | `cards` | `1` | started_search | single |
| `attach_from_deck` | `effects.py` CoinAttachFromDeckOnEntry.resolve | `use.player` | `options` | `self.max_cards` | started_search | unconfirmed |
| `attach_from_deck` | `resolution/programs.py` AttachBasicEnergyFromDeckToSelf.run | `run.player` | `options` | `count` | started_search | unconfirmed |
| `attach_from_deck` | `resolution/programs.py` AttachFromDeck.run | `run.player` | `candidates` | `high` | started_search | unconfirmed |
| `attach_from_deck` | `resolution/programs.py` AttachFromDeckByHeads.run | `run.player` | `cards` | `heads` | started_search | unconfirmed |
| `attach_from_deck` | `resolution/programs.py` AttachFromDeckToBench._bench_first_resume | `run.player` | `candidates` | `1 if candidates else 0` | started_search | unconfirmed |
| `attach_from_deck` | `resolution/programs.py` AttachFromDeckToBench.run | `run.player` | `candidates` | `1 if candidates else 0` | started_search | unconfirmed |
| `attach_from_deck` | `resolution/programs.py` AttachFromDeckUpToNamedCount.run | `run.player` | `self.candidates(run)` | `count` | started_search | unconfirmed |
| `attach_from_discard` | `effects.py` CoinAttachFromDiscardToTypePokemon.resolve | `use.player` | `cards` | `1` | public | single |
| `attach_from_discard` | `resolution/programs.py` AttachFromDiscard.run | `run.player` | `candidates` | `count` | public | not_significant |
| `attach_from_hand` | `resolution/programs.py` AttachFromHand.run | `run.player` | `candidates` | `min(self.max_cards, len(candidates))` | own_cards | not_significant |
| `attach_from_hand` | `resolution/programs.py` AttachFromHandToChosen.resume | `run.player` | `cards` | `min(self.max_cards, len(cards))` | own_cards | not_significant |
| `attach_to_bench` | `resolution/programs.py` AttachFromDeckToBench._bench_first_run | `run.player` | `[p.pokemon_id for p in self.targets(run)]` | `1` | public | single |
| `attach_to_bench` | `resolution/programs.py` AttachFromDeckToBench.resume | `run.player` | `[p.pokemon_id for p in self.targets(run)]` | `1` | public | single |
| `attach_to_bench` | `resolution/programs.py` MoveOneEnergyToBench.resume | `run.player` | `[p.pokemon_id for p in bench]` | `1` | public | single |
| `attach_to_bench` | `resolution/programs.py` MoveOwnEnergyToBench._next | `run.player` | `[p.pokemon_id for p in run.state.players[run.player].bench]` | `1` | public | single |
| `bench_from_deck` | `effects.py` BenchBasicsFromDeckOnEntry.resolve | `use.player` | `deck_basic_pokemon(state, use.player, text_era(use.key.card_id))` | `self._limit(state, use)` | started_search | unconfirmed |
| `bench_from_deck` | `effects.py` BenchNameGroupFromDeckOnEntry.resolve | `use.player` | `options` | `1` | started_search | single |
| `bench_from_deck` | `effects.py` BenchNameGroupFromDeckTrainer.resolve | `use.player` | `options` | `1` | started_search | single |
| `bench_from_deck` | `effects.py` CoinBenchNamedFromDeck.resolve | `use.player` | `options` | `1 if options else 0` | started_search | unconfirmed |
| `bench_from_deck` | `effects.py` CoinBenchOwnerBasicFromDeckStadium.activate | `player` | `candidates` | `1` | started_search | single |
| `bench_from_deck` | `effects.py` CoinReviveFromDeck.resolve | `use.player` | `options` | `1 if options else 0` | started_search | unconfirmed |
| `bench_from_deck` | `effects.py` EachPlayerMayBenchBasicFromDeck._offer | `player` | `options` | `1` | started_search | single |
| `bench_from_deck` | `resolution/programs.py` BenchFromDeck.run | `run.player` | `candidates` | `high` | started_search | unconfirmed |
| `bench_from_deck` | `resolution/programs.py` BenchFromDeckAny.run | `run.player` | `candidates` | `min(space, len(candidates))` | started_search | unconfirmed |
| `bench_from_deck_or_hand` | `effects.py` FossilEggRevive.resume |  | `revival_deck_cards(state, use.player, REVIVE_FOSSIL) + hand` | `1` | started_search | single |
| `bench_from_discard` | `effects.py` BenchBasicFromOwnDiscardThenCounters.resolve | `use.player` | `self.candidates(state, use)` | `1` | public | single |
| `bench_from_discard` | `effects.py` DiscardEnergyThenBenchBasicFromDiscard.resume | `use.player` | `options` | `1` | public | single |
| `bench_from_discard` | `effects.py` _BenchBasicFromDiscardTrainer.resolve | `use.player` | `self.candidates(state, use)` | `1` | public | single |
| `bench_from_discard` | `resolution/programs.py` BenchBabyOrBasicFromOwnDiscard.run | `run.player` | `candidates` | `1` | public | single |
| `bench_from_discard` | `resolution/programs.py` BenchFromEitherDiscard.run | `run.player` | `candidates` | `1` | public | single |
| `bench_from_discard` | `resolution/programs.py` BenchFromOpponentDiscard.run | `run.player` | `candidates` | `1` | public | single |
| `bench_guard` | `resolution/programs.py` CoinPerOpponentPokemon._deal | `request.owner` | `list(request.options)` | `request.max_choices` | public | significant |
| `bench_guard` | `resolution/programs.py` .guarded_damages | `request.owner` | `list(request.options)` | `request.max_choices` | public | significant |
| `challenge_bench` | `effects.py` ChallengeBenchFromDecks._offer | `chooser` | `candidates` | `min(room, len(candidates))` | started_search | unconfirmed |
| `damage_option` | `resolution/programs.py` .guarded_damages | `owner` | `(receiver.pokemon_id,)` | `1` | public | single |
| `damage_option` | `resolution/programs.py` .suspend_damage_option | `owner` | `(receiver.pokemon_id,)` | `1` | public | single |
| `damage_reduction` | `resolution/programs.py` .suspend_damage_reduction | `run.player` | `tuple(need.choices)` | `1` | public | single |
| `damage_step_order` | `resolution/programs.py` .suspend_step_order | `chooser` | `tuple(range(len(permutations)))` | `1` | public | single |
| `deck_top_from_hand` | `effects.py` DrawThenPutHandCardOnDeckTop.resolve | `use.player` | `tuple(side.hand)` | `1` | own_cards | single |
| `discard_energy` | `effects.py` DiscardAttachedEnergyTrainer.resolve | `use.player` | `_attached_cards(state.players[use.player].in_play())` | `self.own_cost` | public | not_significant |
| `discard_energy` | `effects.py` DiscardEnergyThenHealTrainer.resume | `use.player` | `tuple(target.energy)` | `1` | public | single |
| `discard_energy` | `resolution/programs.py` DiscardEachType._ask | `run.player` | `self.options(run, index)` | `1` | public | single |
| `discard_energy` | `resolution/programs.py` DiscardOwnEnergy.run | `run.player` | `candidates` | `len(candidates)`<br>`needed` | public | significant |
| `discard_energy` | `resolution/programs.py` OptionalDiscardBenchDamage.run | `run.player` | `candidates` | `1` | public | single |
| `discard_energy` | `resolution/programs.py` OptionalDiscardForBonus.run | `run.player` | `candidates` | `top` | public | not_significant |
| `discard_from_hand` | `effects.py` DiscardEnergyThenBenchBasicFromDiscard.resolve | `use.player` | `_energy_cards_in_hand(state, use)` | `self.discard` | own_cards | unconfirmed |
| `discard_from_hand` | `effects.py` DiscardFromHandThenDrawTrainer.resolve | `use.player` | `hand` | `len(hand)` | own_cards | unconfirmed |
| `discard_from_hand` | `effects.py` DiscardFromHandThenRetrieveEnergy.resolve | `use.player` | `state.players[use.player].hand` | `self.discard` | own_cards | unconfirmed |
| `discard_from_hand` | `effects.py` DiscardFromHandThenSearchDeck.resolve | `use.player` | `state.players[use.player].hand` | `self.discard` | own_cards | unconfirmed |
| `discard_from_hand` | `effects.py` DiscardThenDraw.resolve | `use.player` | `tuple(state.players[use.player].hand)` | `1` | own_cards | single |
| `discard_from_hand` | `effects.py` ReturnHandsToDeckTrainer.resolve | `use.player` | `state.players[use.player].hand` | `self.discard_cost` | own_cards | unconfirmed |
| `discard_from_hand` | `effects.py` SearchDeckTrainer.resolve | `use.player` | `hand` | `self.discard_cost` | own_cards | unconfirmed |
| `discard_from_hand` | `effects.py` TakeFromDiscardTrainer.resolve | `use.player` | `state.players[use.player].hand` | `self.discard_cost` | own_cards | unconfirmed |
| `discard_from_hand` | `effects.py` TrainerTurnEffectTrainer.resolve | `use.player` | `state.players[use.player].hand` | `self.discard_cost` | own_cards | unconfirmed |
| `discard_from_hand` | `engine.py` ._start_trainer_use | `use.player` | `tuple(state.players[use.player].hand)` | `extra_cost[1].discard` | own_cards | unconfirmed |
| `discard_opponent_energy` | `effects.py` DiscardAttachedEnergyTrainer._opponent_stage | `use.player` | `_attached_cards(self._removable(state, use))` | `1` | public | single |
| `discard_opponent_energy` | `effects.py` DiscardAttachedEnergyTrainer.resume | `use.player` | `tuple(target.energy)` | `self.opponent_cards` | public | not_significant |
| `discard_opponent_energy` | `resolution/programs.py` DiscardChosenTypedEnergyUntilTails.run | `run.player` | `options` | `heads` | public | not_significant |
| `discard_opponent_energy` | `resolution/programs.py` DiscardOpponentEnergy._next | `run.player` | `options` | `1` | public | single |
| `discard_opponent_energy` | `resolution/programs.py` DiscardOpponentEnergyByHeads.run | `run.player` | `options` | `heads` | public | not_significant |
| `discard_opponent_energy` | `resolution/programs.py` DiscardOpponentEnergyUpToHeads.run | `run.player` | `options` | `count` | public | not_significant |
| `discard_stadium` | `resolution/programs.py` OptionalDiscardStadium.run | `run.player` | `(stadium.card,)` | `1` | public | single |
| `discard_to_deck` | `effects.py` CoinReturnEnergyFromDiscardToDeck.resolve | `use.player` | `options` | `min(self.count, len(options))` | public | not_significant |
| `discard_to_deck` | `effects.py` EachPlayerReturnDiscardToDeckThenHandLock._offer | `player` | `options` | `min(self.max_count, len(options))` | public | not_significant |
| `discard_to_deck` | `effects.py` TakeFromDiscardTrainer._choose | `use.player` | `options` | `high` | public | not_significant |
| `discard_to_deck` | `resolution/programs.py` CoinDiscardCardToDeckThenShuffle.run | `run.player` | `discard` | `1` | public | single |
| `discard_to_deck` | `resolution/programs.py` EachPlayerStep._offer | `player` | `options` | `high` | public | not_significant |
| `discard_to_deck_top` | `effects.py` TakeFromDiscardTrainer._choose | `use.player` | `options` | `high` | public | unconfirmed |
| `discard_to_deck_top` | `resolution/programs.py` OpponentDiscardToDeckTop.run | `run.player` | `list(run.state.players[1 - run.player].discard)` | `1` | public | single |
| `energy_drain_discard` | `resolution/programs.py` .fire_or_suspend | `request.entry[0]` | `list(request.options)` | `1` | public | single |
| `entry_power` | `effects.py` .offer_entry_power | `owner` | `(pokemon.pokemon_id,)` | `1` | public | single |
| `esp_redo` | `resolution/programs.py` .suspend_esp_redo | `run.player` | `(1,)` | `1` | public | single |
| `evolution_heal` | `effects.py` .offer_evolution_heal | `owner` | `(pokemon.pokemon_id,)` | `1` | public | single |
| `evolution_heal` | `resolution/programs.py` EachPlayerEvolvesFromDeck.resume | `player` | `(pokemon.pokemon_id,)` | `1` | public | single |
| `evolution_heal` | `resolution/programs.py` EvolveChosenFromDeck.resume | `run.player` | `(target.pokemon_id,)` | `1` | public | single |
| `evolution_heal` | `resolution/programs.py` .suspend_evolution_heal | `owner` | `(pokemon.pokemon_id,)` | `1` | public | single |
| `evolution_song_pokemon` | `resolution/programs.py` EachPlayerEvolvesFromDeck._offer | `player` | `options` | `1` | owner_knowledge | single |
| `evolution_song_pokemon` | `resolution/programs.py` EachPlayerStep._offer | `player` | `options` | `high` | owner_knowledge | single |
| `exp_all_energy` | `resolution/codec.py` .exp_all_decision | `player` | `options` | `1` | public | single |
| `exp_all_energy` | `resolution/flow.py` ._finish_attack | `owner` | `exp_all_options(state, active)` | `1` | public | single |
| `forced_switch` | `resolution/programs.py` ForceSwitch.run | `chooser` | `list(options)` | `1` | public | single |
| `hand_to_active` | `effects.py` BenchActiveThenHandBasicToActive.resolve | `use.player` | `_hand_basics(state, use.player, text_era(use.card_id))` | `1` | own_cards | single |
| `hand_to_deck` | `effects.py` DrawThenReturnHandCardsToDeck.resolve | `use.player` | `state.players[use.player].hand` | `self.count` | own_cards | unconfirmed |
| `hand_to_deck` | `effects.py` ReturnHandToDeckThenDraw.resolve | `use.player` | `state.players[use.player].hand` | `self.count` | own_cards | unconfirmed |
| `hand_to_deck` | `effects.py` SearchDeckTrainer.resolve | `use.player` | `hand` | `self.return_cost` | own_cards | unconfirmed |
| `hand_to_deck` | `resolution/programs.py` ReturnHandThenRevealEnergy.run | `run.player` | `list(hand)` | `min(self.max_cards, len(hand))` | own_cards | unconfirmed |
| `hand_to_deck` | `resolution/programs.py` ReturnHandToDeck.run | `run.player` | `list(hand)` | `self.count` | own_cards | unconfirmed |
| `heal_allocation` | `resolution/programs.py` AllocateHeal.run | `self.owner(run)` | `tuple(range(len(table)))` | `1` | public | single |
| `janken_hand` | `effects.py` RockPaperScissorsRefreshHand._ask | `use.player` | `range(len(JANKEN_HANDS))` | `1` | public | single |
| `janken_hand` | `effects.py` RockPaperScissorsRefreshHand.resume | `1 - use.player` | `range(len(JANKEN_HANDS))` | `1` | public | single |
| `knock_out_power` | `resolution/flow.py` ._finish_attack | `owner` |  | `1` | public | single |
| `ko_prevention` | `resolution/flow.py` ._finish_attack | `owner` |  | `1` | public | single |
| `magma_pool_energy` | `reactions.py` .process | `choice.player` | `choice.options` | `1` | public | single |
| `magma_pool_energy` | `resolution/programs.py` ._apply_move | `choice.player` | `list(choice.options)` | `1` | public | single |
| `move_energy` | `effects.py` ChargeBenchEnergyToSelf.resolve | `use.player` | `options` | `len(options)` | public | not_significant |
| `move_energy` | `effects.py` GatherTypeEnergyCardsToSelf.resolve | `use.player` | `options` | `min(self.max_cards, len(options))` | public | not_significant |
| `move_energy` | `effects.py` TakeEnergiesToSelf.resolve | `use.player` | `options` | `min(self.max_cards, len(options))` | public | not_significant |
| `move_energy` | `resolution/programs.py` BubbleJump.resume | `run.player` | `tuple(attacker.energy)` | `self.count` | public | significant |
| `move_energy` | `resolution/programs.py` MoveOneEnergyToBench.run | `run.player` | `candidates` | `1` | public | single |
| `move_opponent_energy` | `resolution/programs.py` MoveOpponentEnergyToBench.run | `run.player` | `energies` | `1` | public | single |
| `move_opponent_energy` | `resolution/programs.py` MoveOpponentFieldEnergy.run | `run.player` | `options` | `1` | public | single |
| `ninja_trick` | `resolution/programs.py` .offer_ninja_trick | `owner` | `options` | `1` | public | single |
| `opponent_hand_to_bench` | `effects.py` LookOpponentHandThenBenchBasics.resolve | `use.player` | `options` | `min(space, len(options))` | started_search | unconfirmed |
| `opponent_hand_to_bench` | `resolution/programs.py` EachPlayerHandToBench._stage | `chooser` | `candidates` | `min(space, len(candidates))` | started_search | unconfirmed |
| `opponent_hand_to_bench` | `resolution/programs.py` OpponentHandToBenchThenSwitch.run | `run.player` | `candidates` | `1` | started_search | single |
| `opponent_hand_to_deck` | `effects.py` CoinLookOpponentHandMayReturnTrainer.resolve | `use.player` | `trainers` | `1` | started_search | single |
| `opponent_hand_to_deck` | `effects.py` LookOpponentHandReturnOneThenMayDraw.resolve | `use.player` | `state.players[opponent].hand` | `1` | started_search | single |
| `opponent_hand_to_deck` | `effects.py` OpponentHandTrainerToDeck.resolve | `use.player` | `options` | `1` | started_search | single |
| `opponent_hand_to_deck` | `resolution/programs.py` LookHandTrainerToDeck.run | `run.player` | `trainers` | `1` | started_search | single |
| `optional_coin` | `resolution/programs.py` OptionalCoin.run | `run.player` | `(1,)` | `1` | public | single |
| `optional_discard_all` | `resolution/programs.py` OptionalDiscardAll.run | `run.player` | `(1,)` | `1` | public | single |
| `optional_drain` | `resolution/programs.py` Drain.run | `run.player` | `(attacker.pokemon_id,)` | `1` | public | single |
| `optional_heal` | `resolution/programs.py` OptionalHealSelf.run | `run.player` | `(attacker.pokemon_id,)` | `1` | public | single |
| `optional_shuffle` | `effects.py` CoinPeekOpponentDeckTopMayShuffle.resolve | `use.player` | `(opponent,)` | `1` | public | single |
| `peek_card` | `effects.py` PeekCard.resolve | `use.player` | `range(len(targets))` | `1` | own_cards | single |
| `post_knockout_power` | `resolution/codec.py` .post_knockout_decision | `owner` | `(card,)` | `1` | public | single |
| `post_knockout_power` | `resolution/flow.py` ._offer_post_knockout |  |  | `1` | public | single |
| `prize_first` | `resolution/codec.py` .prize_first_decision | `state.current_player` | `sorted(set(cont.remaining))` | `1` | public | single |
| `prize_first` | `resolution/flow.py` ._next_prize_or_judge |  |  | `1` | public | single |
| `promote_active` | `resolution/codec.py` .promote_decision | `player` | `[p.pokemon_id for p in state.players[player].bench]` | `1` | public | single |
| `promote_active` | `resolution/flow.py` ._next_promotion_or_end |  |  | `1` | public | single |
| `quiz_answer` | `effects.py` BlainesQuiz.resume | `1 - use.player` | `range(len(names))` | `1` | public | single |
| `quiz_answer` | `effects.py` GuessOpponentPrizeKind.resume | `use.player` | `range(len(FLIP_KIND_NAMES))` | `1` | public | single |
| `quiz_answer` | `effects.py` SetAsideGuessKindQuiz.resume | `1 - use.player` | `range(len(self.names()))` | `1` | public | single |
| `quiz_attack` | `effects.py` BlainesQuiz.resume | `use.player` | `range(len(attacks))` | `1` | public | single |
| `quiz_card` | `effects.py` BlainesHeightQuiz.resolve | `use.player` | `candidates` | `1` | own_cards | single |
| `quiz_card` | `effects.py` BlainesQuiz.resolve | `use.player` | `quiz_candidates(state, use.player)` | `1` | own_cards | single |
| `quiz_card` | `effects.py` SetAsideGuessKindQuiz.resolve | `use.player` | `self.candidates(state, use)` | `1` | own_cards | single |
| `quiz_height_answer` | `effects.py` BlainesHeightQuiz.resume | `1 - use.player` | `()` | `1` | public | single |
| `reaction_order` | `reactions.py` ._process_same | `state.current_player` | `range(len(order))` | `1` | public | single |
| `reaction_order` | `resolution/programs.py` ._settle_move_step | `state.current_player` | `list(range(len(live)))` | `1` | public | single |
| `reaction_power` | `engine.py` ._offer_trainer_reaction | `owner` | `(holder.pokemon_id,)` | `1` | public | single |
| `reaction_power` | `reactions.py` ._offer_use | `owner` | `(pid,)` | `1` | public | single |
| `reaction_switch` | `resolution/programs.py` .offer_flee | `owner` | `options` | `1` | public | single |
| `recover_energy` | `resolution/programs.py` RecoverEnergy.run | `run.player` | `candidates` | `min(self.max_cards, len(candidates))` | public | significant |
| `recover_energy` | `resolution/programs.py` RecoverEnergyByHeads.run | `run.player` | `candidates` | `heads` | public | not_significant |
| `recover_energy` | `resolution/programs.py` RecoverSpecialEnergy.run | `run.player` | `candidates` | `1` | public | single |
| `recover_pokemon` | `effects.py` CoinTakeEvolutionOrBasicFromDiscard.resolve | `use.player` | `options` | `1` | public | single |
| `recover_pokemon` | `effects.py` CoinsTakePokemonOrTrainerFromDiscard.resolve | `use.player` | `discard_cards_matching(state, use.player, target)` | `1` | public | single |
| `recover_pokemon` | `effects.py` RecoverPokemonFromDiscardOnEntry.resolve | `use.player` | `cards` | `min(self.max_cards, len(cards))` | public | not_significant |
| `recover_pokemon` | `resolution/programs.py` EachPlayerStep._offer | `player` | `options` | `high` | public | not_significant |
| `recover_trainer` | `effects.py` CoinRecoverNamedFromDiscard.resolve | `use.player` | `self.options(state, use)` | `1` | public | single |
| `recover_trainer` | `effects.py` CoinRecoverTrainerWithBenchLetters.resolve | `use.player` | `self.options(state, use)` | `1` | public | single |
| `recover_trainer` | `effects.py` CoinsTakePokemonOrTrainerFromDiscard.resolve | `use.player` | `discard_cards_matching(state, use.player, target)` | `1` | public | single |
| `recover_trainer` | `effects.py` TakeFromDiscardTrainer._choose | `use.player` | `options` | `high` | public | not_significant |
| `recover_trainer` | `resolution/programs.py` RecoverTrainer.run | `run.player` | `candidates` | `1` | public | single |
| `remove_counters` | `resolution/programs.py` ChosenOpponentHealThenDraw.resume | `run.player` | `range(counters + 1)` | `1` | public | single |
| `restore` | `reactions.py` ._run_step | `player` | `options` | `high` | inherits | unconfirmed |
| `retrieve_energy` | `effects.py` CoinRetrieveBasicEnergyStadium.activate | `player` | `self.candidates(state, player)` | `1` | public | single |
| `retrieve_energy` | `effects.py` DiscardFromHandThenRetrieveEnergy.resume | `use.player` | `options` | `min(self.retrieve, len(options))` | own_cards | not_significant |
| `return_energy` | `effects.py` CoinsUntilTailsReturnOpponentActiveEnergyThenEndTurn.resolve | `use.player` | `tuple(options)` | `heads` | public | not_significant |
| `return_energy` | `effects.py` ReturnBasicEnergyToHandTrainer.resolve | `use.player` | `options` | `len(options)` | public | not_significant |
| `return_energy` | `resolution/programs.py` DiscardOwnEnergy.run | `run.player` | `candidates` | `len(candidates)`<br>`needed` | public | significant |
| `return_to_deck` | `effects.py` ReturnHandEnergyThenCoinSearchBasicEnergy.resolve | `use.player` | `options` | `1` | owner_knowledge | single |
| `return_to_deck` | `effects.py` TradePokemonWithDeck.resolve | `use.player` | `options` | `1` | own_cards | single |
| `revive_source` | `effects.py` FossilEggRevive.resolve | `use.player` | `options` | `1` | own_cards | single |
| `search_deck` | `effects.py` BreederCoupleSearch._next | `use.player` | `options` | `1 if options else 0` | started_search | unconfirmed |
| `search_deck` | `effects.py` CoinEvolveSelfFromDeck.resolve | `use.player` | `candidates` | `count` | started_search | unconfirmed |
| `search_deck` | `effects.py` CoinsSearchBasicEnergyPerHeads.resolve | `use.player` | `deck_cards_matching(state, use.player, self.TARGET)` | `heads` | started_search | unconfirmed |
| `search_deck` | `effects.py` DiscardFromHandThenSearchDeck.resume | `use.player` | `sorted(state.players[use.player].deck)` | `self.search` | started_search | unconfirmed |
| `search_deck` | `effects.py` EachPlayerSearchToolOnEntry.resume | `player` | `options` | `1 if options else 0` | started_search | unconfirmed |
| `search_deck` | `effects.py` ReturnHandEnergyThenCoinSearchBasicEnergy.resume | `use.player` | `options` | `min(self.count, len(options))` | started_search | unconfirmed |
| `search_deck` | `effects.py` SearchDeckTrainer._search | `use.player` | `options` | `min(self.count, len(options))` | started_search | unconfirmed |
| `search_deck` | `effects.py` SearchDeckWithBenchLettersToHand.resolve | `use.player` | `self.options(state, use)` | `1` | started_search | single |
| `search_deck` | `effects.py` SearchEvolutionCardToHand.resolve | `use.player` | `deck_evolution_cards(state, use.player)` | `1` | started_search | single |
| `search_deck` | `effects.py` SearchNamedTrainerOnEntry.resolve | `use.player` | `deck_named_trainer_cards(state, use.player, self.name)` | `1` | started_search | single |
| `search_deck` | `effects.py` TradePokemonWithDeck.resume | `use.player` | `options` | `1` | started_search | single |
| `search_deck` | `reactions.py` ._offer_search | `owner` | `candidates` | `count` | started_search | unconfirmed |
| `search_deck` | `resolution/programs.py` EachPlayerEvolvesFromDeck.resume | `player` | `cards` | `1 if cards else 0` | started_search | unconfirmed |
| `search_deck` | `resolution/programs.py` EvolveAttackerFromDeck._required_run | `run.player` | `()`<br>`candidates` | `0`<br>`1` | started_search | unconfirmed |
| `search_deck` | `resolution/programs.py` EvolveAttackerFromDeck.run | `run.player` | `candidates` | `1` | started_search | single |
| `search_deck` | `resolution/programs.py` EvolveChosenFromDeck._next | `run.player` | `()`<br>`candidates` | `0`<br>`1` | started_search | unconfirmed |
| `search_deck` | `resolution/programs.py` EvolveFromDeck.run | `run.player` | `()`<br>`tuple(candidates)` | `0`<br>`1` | started_search | unconfirmed |
| `search_deck` | `resolution/programs.py` ReturnHandThenRevealEnergy.resume | `run.player` | `E.deck_basic_energy_cards(state, run.player)` | `wanted` | started_search | unconfirmed |
| `search_deck` | `resolution/programs.py` RevealNamedPokemonFromDeck.run | `run.player` | `candidates` | `high` | started_search | unconfirmed |
| `search_deck` | `resolution/programs.py` RevealPokemonFromDeck.run | `run.player` | `candidates` | `1 if candidates else 0` | started_search | unconfirmed |
| `search_deck` | `resolution/programs.py` RevealTrainerFromDeck.run | `run.player` | `self.candidates(run)`<br>`candidates` | `heads`<br>`high` | started_search | unconfirmed |
| `search_deck_or_discard` | `effects.py` SearchNamedFromDeckOrDiscard.resolve | `use.player` | `options` | `1` | started_search | single |
| `secret_plan_card` | `effects.py` PlaceFaceDownOnBench.resolve | `use.player` | `candidates` | `1` | own_cards | single |
| `select_attached_special_energy` | `resolution/programs.py` ReturnAttachedSpecialEnergyToDeck.run | `run.player` | `options` | `1` | public | single |
| `select_attached_trainer` | `resolution/programs.py` ReturnAttachedTrainerToDeck.run | `run.player` | `options` | `1` | public | single |
| `select_attack` | `resolution/programs.py` CopyChosenAttack.run | `run.player` | `options` | `1` | public | single |
| `select_attack` | `resolution/programs.py` CopyOpponentAttack.run | `run.player` | `options` | `1` | public | single |
| `select_color` | `effects.py` ConvertBasicEnergyColor.resolve | `use.player` | `NON_COLORLESS_CHOICES` | `1` | public | single |
| `select_color` | `effects.py` ConvertSelfToEnergy.resume | `use.player` | `options` | `1` | public | single |
| `select_color` | `effects.py` ShiftColor.resolve | `use.player` | `sorted(sure \| maybe)` | `1` | public | single |
| `select_color` | `resolution/programs.py` ChooseColor.run | `run.player` | `options` | `1` | public | single |
| `select_color` | `resolution/programs.py` OpponentWeaknessColor.run | `run.player` | `E.NON_COLORLESS_CHOICES` | `1` | public | single |
| `select_color` | `resolution/programs.py` SelfResistanceColor.run | `run.player` | `E.NON_COLORLESS_CHOICES` | `1` | public | single |
| `select_counter_count` | `effects.py` DiscardEnergyThenHealTrainer.resume | `use.player` | `tuple(range(min(self.max_counters, target.damage // per) + 1))` | `1` | public | single |
| `select_counter_count` | `effects.py` HealNamedPokemonUpTo.resume | `use.player` | `tuple(range(min(self.counters, target.damage // per) + 1))` | `1` | public | single |
| `select_deck_owner` | `resolution/programs.py` ArrangeDeckTop.run | `run.player` | `owners` | `1` | public | single |
| `select_devolve_count` | `effects.py` DevolveOwnPokemon.resume | `use.player` | `range(len(pokemon.evolution_stack) + 1)` | `1` | public | single |
| `select_draw_count` | `effects.py` EachPlayerMayDraw._offer | `player` | `self._options(state, player)` | `1` | public | single |
| `select_draw_count` | `effects.py` LookOpponentHandReturnOneThenMayDraw.resume | `opponent` | `range(min(self.max_draw, len(state.players[opponent].deck)) + 1)` | `1` | public | single |
| `select_draw_count` | `resolution/programs.py` EachPlayerStep._offer | `player` | `options` | `high` | public | unconfirmed |
| `select_evolution_card` | `effects.py` EvolveBasicToStage2.resume | `use.player` | `[uid for uid, _ in entries]` | `1` | own_cards | single |
| `select_evolution_card` | `effects.py` FossilEggRevive.resolve |  | `hand` | `1` | own_cards | single |
| `select_evolution_card` | `effects.py` FossilEggRevive.resume |  | `hand` | `1` | own_cards | single |
| `select_evolution_card` | `effects.py` Shapeshift.resolve | `use.player` | `options` | `1` | own_cards | single |
| `select_exchange_card` | `effects.py` SwapPleaseTrainer.resolve | `use.player` | `state.players[opponent].hand` | `1` | started_search | single |
| `select_exchange_card` | `effects.py` SwapPleaseTrainer.resume | `opponent` | `state.players[use.player].hand` | `1` | started_search | single |
| `select_hand_card` | `resolution/programs.py` LookHandCardToDeck.run | `run.player` | `tuple(range(len(hand)))` | `1` | public | single |
| `select_hand_positions` | `effects.py` CoinReturnOpponentHandPositions.resolve | `use.player` | `range(size)` | `min(self.count, size)` | public | not_significant |
| `select_look_count` | `effects.py` ArrangeOwnDeckTopTrainer.resolve | `use.player` | `self._count_options(state, use)` | `1` | public | single |
| `select_look_count` | `effects.py` LookDeckTopStadium.activate | `player` | `self.counts(state, player)` | `1` | public | single |
| `select_look_count` | `resolution/programs.py` ArrangeDeckTop.resume | `run.player` | `tuple(range(min(self.max_cards, len(deck)) + 1))` | `1` | public | single |
| `select_marker_count` | `resolution/programs.py` OptionalRemoveOwnMarkers.run | `run.player` | `tuple(range(top + 1))` | `1` | public | single |
| `select_opponent_attack` | `resolution/programs.py` OpponentAttackLock.run | `run.player` | `tuple(range(len(entries)))` | `1` | public | single |
| `select_opponent_prize` | `effects.py` GuessOpponentPrizeKind.resolve | `use.player` | `self.positions(state, use)` | `1` | public | single |
| `select_pokemon` | `effects.py` AttachedDamageReduction.resolve | `use.player` | `[pokemon.pokemon_id for pokemon in own]` | `1` | public | single |
| `select_pokemon` | `effects.py` AttachedEffectGuard.resolve | `use.player` | `[pokemon.pokemon_id for pokemon in own]` | `1` | public | single |
| `select_pokemon` | `effects.py` BreederCoupleSearch.resolve | `use.player` | `targets` | `min(2, len(targets))` | public | not_significant |
| `select_pokemon` | `effects.py` ChooseFossilEvolvedThenCoinDevolveAll.resolve | `use.player` | `options` | `1` | public | single |
| `select_pokemon` | `effects.py` ChooseOwnPokemonCoinsHeal.resolve | `use.player` | `[p.pokemon_id for p in own]` | `1` | public | single |
| `select_pokemon` | `effects.py` CoinAttachEnergyFromDeckToOwnPokemon.resume | `use.player` | `targets` | `1` | public | single |
| `select_pokemon` | `effects.py` CoinAttachFromDiscardToTypePokemon.resume | `use.player` | `targets` | `1` | public | single |
| `select_pokemon` | `effects.py` CoinReturnOpponentPokemonToHandOnEntry.resolve | `use.player` | `options` | `1` | public | single |
| `select_pokemon` | `effects.py` CoinReturnOtherGroupToHandOnEntry.resolve | `use.player` | `self.options(state, use.player, use.pokemon_id)` | `1` | public | single |
| `select_pokemon` | `effects.py` CoinReturnOwnPokemonWithAttachedToHand.resolve | `use.player` | `candidates` | `1` | public | single |
| `select_pokemon` | `effects.py` CoinReturnOwnerPokemonStadium.activate | `player` | `self.targets(state, player)` | `1` | public | single |
| `select_pokemon` | `effects.py` CoinsReturnOpponentBenchElseEndTurn.resolve | `use.player` | `[p.pokemon_id for p in state.players[1 - use.player].bench]` | `1` | public | single |
| `select_pokemon` | `effects.py` ConvertSelfToEnergy.resolve | `use.player` | `options` | `1` | public | single |
| `select_pokemon` | `effects.py` DamageOpponentPokemonOnEntry.resolve | `use.player` | `[p.pokemon_id for p in state.players[1 - use.player].in_play()]` | `1` | public | single |
| `select_pokemon` | `effects.py` DevolveOneToHandWithBan.resolve | `use.player` | `candidates` | `1` | public | single |
| `select_pokemon` | `effects.py` DevolveOwnPokemon.resolve | `use.player` | `candidates` | `1` | public | single |
| `select_pokemon` | `effects.py` DiscardAttachedEnergyTrainer._opponent_stage | `use.player` | `[p.pokemon_id for p in opponent]` | `1` | public | single |
| `select_pokemon` | `effects.py` DiscardDeckTopAttachTypeEnergyThenEndTurn._next | `use.player` | `targets` | `1` | public | single |
| `select_pokemon` | `effects.py` DiscardEnergyThenHealTrainer.resolve | `use.player` | `[p.pokemon_id for p in targets]` | `1` | public | single |
| `select_pokemon` | `effects.py` EvolutionPermissionForOwnerPokemon.resolve | `use.player` | `owner_pokemon(state, use.player, self.owner)` | `1` | public | single |
| `select_pokemon` | `effects.py` EvolveBasicToStage2.resolve | `use.player` | `options` | `1` | own_cards | single |
| `select_pokemon` | `effects.py` HealNamedPokemonUpTo.resolve | `use.player` | `options` | `1` | public | single |
| `select_pokemon` | `effects.py` HealOwnPokemonOnHeads.resolve | `use.player` | `_damaged_own_pokemon(state, use.player)` | `1` | public | single |
| `select_pokemon` | `effects.py` HealOwnerPokemonThenDiscardHand.resolve | `use.player` | `self._targets(state, use)` | `1` | public | single |
| `select_pokemon` | `effects.py` MoveAllEnergyBetweenOwnerPokemon.resolve | `use.player` | `self._targets(state, use)` | `1` | public | single |
| `select_pokemon` | `effects.py` MoveAllEnergyBetweenOwnerPokemon.resume | `use.player` | `[pid for pid in self._targets(state, use) if pid != choices[0]]` | `1` | public | single |
| `select_pokemon` | `effects.py` OpponentChoosesMySwitchThenISwitchTheirs._offer | `chooser` | `[p.pokemon_id for p in bench]` | `1` | public | single |
| `select_pokemon` | `effects.py` PinpointLens.resolve | `use.player` | `[pokemon.pokemon_id for pokemon in own]` | `1` | public | single |
| `select_pokemon` | `effects.py` PokemonToolEffect.resolve | `use.player` | `tool_targets(state, use.player)` | `1` | public | single |
| `select_pokemon` | `effects.py` ProtectAttachedEnergy.resolve | `use.player` | `self._targets(state, use)` | `1` | public | single |
| `select_pokemon` | `effects.py` RedoAttackCoins.resolve | `use.player` | `self._targets(state, use.player)` | `1` | public | single |
| `select_pokemon` | `effects.py` RemoveDamageCounters.resolve | `use.player` | `[pokemon.pokemon_id for pokemon in own]` | `1` | public | single |
| `select_pokemon` | `effects.py` ReturnBenchedPokemonToDeck.resolve | `use.player` | `self._candidates(state, use.player)` | `1` | public | single |
| `select_pokemon` | `effects.py` ReturnOwnPokemonBasicToHand.resolve | `use.player` | `self._candidates(state, use.player)` | `1` | public | single |
| `select_pokemon` | `effects.py` SuperTransformPower.resolve | `use.player` | `options` | `1` | public | single |
| `select_pokemon` | `effects.py` SwitchBothActivesTrainer._offer | `player` | `[p.pokemon_id for p in bench]` | `1` | public | single |
| `select_pokemon` | `effects.py` SwitchOpponentChosenByOpponent.resolve | `1 - use.player` | `[p.pokemon_id for p in state.players[1 - use.player].bench]` | `1` | public | single |
| `select_pokemon` | `effects.py` SwitchOpponentOnHeads.resolve | `use.player` | `[pokemon.pokemon_id for pokemon in bench]` | `1` | public | single |
| `select_pokemon` | `effects.py` SwitchOpponentWithBench.resolve | `use.player` | `[pokemon.pokemon_id for pokemon in bench]` | `1` | public | single |
| `select_pokemon` | `effects.py` SwitchWithBench.resolve | `use.player` | `[pokemon.pokemon_id for pokemon in bench]` | `1` | public | single |
| `select_pokemon` | `reactions.py` ._lightning_burst | `opponent` | `[p.pokemon_id for p in state.players[opponent].bench]` | `1` | public | single |
| `select_pokemon` | `reactions.py` ._vine_pull | `opponent` | `[p.pokemon_id for p in state.players[opponent].bench]` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` AttachFromDeckByHeads._ask_target | `run.player` | `targets` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` AttachFromHandToChosen.run | `run.player` | `options` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` BatonPass.run | `run.player` | `options` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` BubbleJump.run | `run.player` | `[p.pokemon_id for p in state.players[run.player].bench]` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` ChooseOpponentBench.run | `run.player` | `[p.pokemon_id for p in bench]` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` ChooseTarget.run | `player` | `options` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` ChosenBenchCoinDamage.run | `run.player` | `[p.pokemon_id for p in bench]` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` ChosenBenchDamage.run | `run.player` | `[p.pokemon_id for p in bench]` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` ChosenBenchDamages.run | `run.player` | `[p.pokemon_id for p in bench]` | `min(self.max_targets, len(bench))` | public | significant |
| `select_pokemon` | `resolution/programs.py` ChosenOpponentHealThenDraw.run | `run.player` | `[p.pokemon_id for p in pokemon]` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` CoinChosenSideHeal.run | `run.player` | `options` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` DevolveChosenPokemon.run | `run.player` | `options` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` DevolveOpponentToDeck.run | `run.player` | `options` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` EvolveChosenFromDeck.run | `run.player` | `targets` | `len(targets)` | public | not_significant |
| `select_pokemon` | `resolution/programs.py` EvolveFromDeck.resume | `run.player` | `targets` | `1` | started_search | single |
| `select_pokemon` | `resolution/programs.py` HealChosenOwnBench.run | `run.player` | `[p.pokemon_id for p in bench]` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` MoveOpponentEnergyToBench.resume | `run.player` | `[pokemon.pokemon_id for pokemon in p.bench]` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` MoveOpponentFieldEnergy.resume | `run.player` | `[pokemon.pokemon_id for pokemon in p.in_play()]` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` OptionalDiscardBenchDamage.resume | `run.player` | `[p.pokemon_id for p in bench]` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` PromoteFromBench.run | `run.player` | `[pokemon.pokemon_id for pokemon in p.bench]` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` ReturnOwnBenchToDeck.run | `run.player` | `[p.pokemon_id for p in bench]` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` ReturnOwnPokemonToHand.run | `run.player` | `options` | `len(options)` | public | not_significant |
| `select_pokemon` | `resolution/programs.py` SelfSwitch.run | `run.player` | `[p.pokemon_id for p in bench]` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` SwitchSelfThenStatusGuard.run | `run.player` | `[p.pokemon_id for p in bench]` | `1` | public | single |
| `select_pokemon` | `resolution/programs.py` WashOwnBench.run | `run.player` | `[p.pokemon_id for p in bench]` | `1` | public | single |
| `select_prize_card` | `effects.py` AskOpponentEachTakePrizeElseDraw._offer_prize | `player` | `range(len(state.players[player].prizes))` | `1` | public | single |
| `select_prize_card` | `effects.py` LookOwnPrizeCard.resolve | `use.player` | `range(len(state.players[use.player].prizes))` | `1` | public | single |
| `select_prize_card` | `effects.py` LookPrizeAskSwapElseDraw.resolve | `use.player` | `range(len(state.players[use.player].prizes))` | `1` | public | single |
| `select_prize_card` | `effects.py` SwapPrizeWithDeckTop.resolve | `use.player` | `range(len(state.players[use.player].prizes))` | `1` | public | single |
| `select_special_condition` | `effects.py` ConditionOwnActiveTrainer.resolve | `use.player` | `range(len(DANCE_CONDITIONS))` | `1` | public | single |
| `select_special_condition` | `resolution/programs.py` ChosenStatus.run | `run.player` | `self.choices()` | `1` | public | single |
| `split_from_deck` | `resolution/programs.py` .fire_or_suspend | `request.entry[0]` | `list(request.options)` | `1 if request.options else 0` | started_search | unconfirmed |
| `stadium_from_discard` | `effects.py` CoinPutStadiumFromDiscard.resolve | `use.player` | `self.candidates(state, use.player)` | `1` | public | single |
| `stadium_return_bench` | `effects.py` BenchLimitStadium._ask | `player` | `[p.pokemon_id for p in state.players[player].bench]` | `1` | public | single |
| `swap_with_prize` | `effects.py` LookPrizeAskSwapElseDraw.resume | `use.player` | `state.players[use.player].hand` | `1` | own_cards | single |
| `take_looked_cards` | `effects.py` LookTopTakeRestDiscardTrainer.resolve | `use.player` | `cards` | `self.take` | started_search | unconfirmed |
| `take_looked_cards` | `resolution/programs.py` EachPlayerLooksTakesBasicEnergy._offer | `player` | `options` | `len(options)` | started_search | unconfirmed |
| `take_looked_cards` | `resolution/programs.py` EachPlayerStep._offer | `player` | `options` | `high` | started_search | unconfirmed |
| `take_looked_cards` | `resolution/programs.py` LookTopTakeOne.run | `run.player` | `looked` | `1` | started_search | single |
| `take_looked_pokemon` | `effects.py` LookTopTakePokemonThenShuffle.resolve | `use.player` | `options` | `1` | started_search | single |
| `take_looked_trainer` | `effects.py` LookTopTakeTrainerThenShuffleLock.resolve | `use.player` | `options` | `1` | started_search | single |
| `take_prize` | `resolution/codec.py` .prize_decision | `player` | `range(len(state.players[player].prizes))` | `1` | public | single |
| `take_prize` | `resolution/flow.py` ._next_prize_or_judge |  |  | `1` | public | single |
| `take_prize` | `resolution/flow.py` ._resume_prize_first |  |  | `1` | public | single |
| `use_discard_trainer` | `effects.py` UseOpponentDiscardTrainer.resolve | `use.player` | `options` | `1` | public | single |
<!-- generated:audit-sites end -->

`python scripts/build_legal_actions_api_design.py --check` は、この一覧（`scripts/legal_actions_decision_sites.py` の `AUDIT`）とコードの走査を (種類, ファイル, クラス, 関数) の組で照らします。決定を出す箇所が加わる・消える・動的な出し方の種類が分からないと失敗します（数だけを固定する検査ではない）。種類ごとの情報境界・答えの並びが出し方の判定から決まることと、`legal_actions` の集合と同じことも確かめます。

## 5. 実行での確かめ（限定）

`tests/test_legal_actions_decision_audit.py`（構築盤面・補助の作り・new_game からの操作の列を分けて書いた）:

- 新しく公開した種類の情報源と表示（`select_pokemon`・`select_color`・`discard_energy`・`retrieve_energy`・`bench_from_discard` などの代表の盤面）
- 同じ種類の複数の出し方（`select_pokemon` のトレーナー・ワザ・パワー、`discard_energy` のトレーナー・ワザ）
- 秘密の配分（山札とサイド）を変えた双子での候補・制約・理由・不正な入力への答え
- 検索の前後（ポケモン育て屋夫婦・ワザの山札からの進化）
- 相手の番に答える決定、複数選択・数・重なり・並び（意味がある・ない）、U7 と直接の送信の一致、取得での状態・乱数・ログの不変、取っ手の契約、3 つの規約集合

## 6. 残る事項

- 情報源の分類はコードを読んだ判断で、すべての出し方を実行したわけではない（実行は代表の盤面）。新しいカード・効果で決定を出す箇所が加わると `--check` が失敗し、分類を書くまで公開の一覧に入らない
- 見えないカードが選べるものに来た場面の実行時の確かめは残す（起こらない想定。起これば入力全体を返さない）
- 39 種類の外の答えの並び（`unconfirmed` の 12 種類）は確かめていない
- 処理可能性（受理・受理のあとの続き）は今までどおり保証しない（`may_stop_later`）

### 6.1 保守のルール（v0.163）

出し方の一覧と走査の照らしは、出し方の組（種類・ファイル・クラス・関数）が加わる・消えると失敗するが、既にある出し方の選べるもの・制約・情報源・回答の処理が変わったことまでは見つけない。次を保守のルールにする:

- 決定の選べるもの・選ぶと止める選択・選ぶ数・情報源・回答の適用を変えたら、その出し方を再監査し、`AUDIT` の判定を書き直す
- 種類の名前や出し方の組の一致だけで、安全性と答えの並びの分類を引き継がない
- 変更の影響を受ける共通処理（`zones`・`effects` の補助関数など）と、それを呼ぶすべての出し方を確かめる

## 7. 通常の対戦で U7 の外の送信が必要な場面

- 決定への回答: なし（96 種類すべてで入力を示す）。ただし、この版が続けられない決定（`not_implemented`）・実行時の確かめが働いた場面（`INPUT_BOUNDARY_UNCONFIRMED`）は、ホストが直接送るか止める
- 準備（たねポケモンを置く・補償の引く枚数）・ホストの操作（ジャンケンの結果・延長戦の開始）: v0.163（U7-2）で U7 の入口から送れる（[legal-actions-u7-2.md](legal-actions-u7-2.md)）
- 番を終える以外の番の操作: U7-3 以後まで、ホストが直接送る
- ホストが直接送って進められることを、U7 の対応として数えない

## 8. v0.160・v0.161 の判断の訂正の経過

- v0.160: 「カードの決定 32 種類の出どころは見えるカード」としたが、種類の名前と一部の出し方からの判断だった（v0.161 で訂正）
- v0.161: 出し方の式の形で 43 種類を確かめ、39 種類を未確認として入力を返さないようにした（未確認を安全と数えない）。式の形の分類は正規表現による抽出で、動的な出し方（種類を属性・引数で渡す 20 の呼び出し）を数えていなかった
- v0.162: AST の走査で動的な出し方を含むすべての出し方を数え、39 種類の情報源と答えの並びを出し方ごとに確かめた。v0.161 で確かめた 43 種類の動的な出し方（ラジオとう・おたがいの引く枚数・見たカードから取る）も同じ走査で一覧に入れ、情報源が公開の値・見たカードであることを確かめた（43 種類の判断は変わらない）

## 9. ロードマップ（今回の範囲の外）

1. 今回の決定の入力の監査で、決定への回答の入力を一区切りにする
2. U7-2: 準備（たねポケモンを置く・引き直し）とホストの操作（ジャンケンの結果・延長戦の開始）
3. U7-3〜U7-5（通常の操作・ワザ・トレーナーとパワー）。単位ごとに、最小のアダプタ（GUI・単純な AI への接続の確かめ）を挟む
4. U7 の節目の総合検証（全体のテスト・lockstep の固定した対戦・状態の監査）
5. AI・GUI の実用化、識別の方式の移行、オンライン対戦の設計

ロードマップの前提:

- GUI には完全な `GameState` ではなく、許可された観測（`observe`・U7 の応答・`view_for`）を渡す
- 再接続は今の観測で復帰し、閲覧用記録（U5）は履歴に使う
- `operation_id` による重複の排除は未実装の別の契約（今は結果に写すだけ）
- 厳密側（`CS-KYUURA-CURRENT@1`）は未決の場面で止め、プレイ側（`CS-KYUURA-PLAY-S2A@1`・`CS-KYUURA-PLAY-PO@1`）は採用済みの続行規約の範囲だけ続ける
- 最小の GUI・単純な AI による接続の確かめと、本格的な作り込みを分ける
