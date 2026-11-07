# v0.160: 合法手 API の最小の実装（U7-1）

`kyuura_engine.legal_actions` は、信頼されたホストの境界で、認証した操作主体に**決定への回答**と**番を終える**の操作候補・必要な入力を返し、候補と入力からの送信を受け付けます。`kyuura_engine` の版は 0.160.0 です。

これは **U7-1 の実装**で、**U7 全体の部分実装**です。準備・ワザ・トレーナー・パワーなどの通常の番の操作、ホストの操作（ジャンケンの結果・延長戦の開始）の入口は実装していません（U7-2 以後）。応答は対応した種類とその範囲の完全性を示し、全合法手ではないことを `coverage` で表します。

仕様案は [legal-actions-api-design.md](legal-actions-api-design.md)、実装計画は [legal-actions-api-implementation-plan.md](legal-actions-api-implementation-plan.md)。識別の方式の新しい方式は実装していません（[implementation-identity-design.md](implementation-identity-design.md)）。

## 採用の記録

<!-- generated:unit-adoption begin -->
- `ADOPT-U7-1`（2026-11-07・利用者）: U7-1（決定への回答と番を終える）の最小の実装と、次の方針だけ。識別の方式の保留の判断（D-PROVENANCE ほか 7 件）・U7-2 以後の操作の種類の仕様・D-U7-DISPLAY・D-U7-COMPLETENESS の承認ではない。実装: v0.160（docs/legal-actions-u7-1.md）
  - 方針:
    - 候補の取得と実行を、信頼されたホストの境界で扱う
    - 操作主体のある操作と、対戦全体のホストの操作を区別する
    - 候補はホストが管理する不透明な取っ手に対応づける
    - 受理した操作で、その対戦の既存の取っ手を失効させる
    - 取っ手の生成にエンジンの乱数を使わない
    - ホストの再起動・状態の復元・状態の差し替えで取っ手を失効させる
    - 拒否した操作だけでは、ほかの主体の取っ手を失効させない
    - 必要な入力は段階的に取得し、組み合わせを全展開しない
    - 未裁定・未実装を候補から黙って消さず、ゲーム上の禁止と区別する
    - unverified は保証がないことを明示し、送信を許可する。最終の判定は既存のエンジンに任せる
    - 対応する操作の種類と、その範囲の完全性を明示する
  - 判断事項: D-U7-API、D-U7-TOKEN、D-U7-REFINE、D-U7-UNVERIFIED、D-U7-HOST-OPS
  - 実装単位: U7-1
<!-- generated:unit-adoption end -->

この採用を、識別の方式の保留の判断（7 件）・U7-2 以後の操作の種類の仕様・D-U7-DISPLAY・D-U7-COMPLETENESS へ広げていません（仕様案 9 章の表の状態）。

## 1. 公開の API

| 入口 | 使う人 | 内容 |
|---|---|---|
| `ActionHost(game, *, on_result=None)`・`ActionHost.start(deck0, deck1, seed, **options)` | ホスト | ホストが持つ対戦（`adapter.HostedGame`・`snapshot.RestoredGame`・`view_record.ViewHost` と同じ形）を包む。実行は包んだ対戦の `submit`（U2 の `CommandResult`）だけで、別の実行器を作らない |
| `ActionHost.session(actor)` | ホスト | 認証した操作主体（0・1）を結びつけた `ActorSession` を作る。0・1 でなければ `ValueError`（観戦者・ホストの操作の入口は U7-1 にない） |
| `ActionHost.replace_game(game)`・`invalidate()` | ホスト | 再起動・復元・状態の差し替え（新しい世代。取っ手をすべて失効）・すべての取っ手の失効 |
| `ActorSession.candidates()` | クライアント | 操作候補（状況・対応の範囲・候補の一覧。入力は段の種類だけ） |
| `ActorSession.inputs(game, revision, candidate)` | クライアント | 候補に必要な入力の段（選べるもの・数・重なり・順序・辞退・処理可能性） |
| `ActorSession.check(game, revision, candidate, choices)` | クライアント | 入力の検査（候補の公開の制約だけ。送らない。受理の保証ではない） |
| `ActorSession.submit(game, revision, candidate, choices=(), *, operation_id=None)` | クライアント | 候補と入力から既存のコマンド（`ResolveDecision`・`EndTurn`）を作り、送り手を本人にして包んだ対戦へ送る。結果は `ActionResult`（`outcome`・`refusal`・`view`） |

クライアントの入口はプレイヤーの番号を受け取りません（操作主体はホストが結びつけた値）。応答は JSON にできる dict で、状態・コマンドの写し・検証者用の値（確認値・seed・乱数・スナップショットの鍵）を持ちません。`ActionResult.view` は U2 の `CommandResult.view_for(本人)`（`ActorDiagnostic`）で、`CommandResult` そのものはホストだけが `on_result` で受け取ります（相手・観戦者への知らせ `view_for(相手)` はホストが配る）。

**ホストの責任**: 操作主体の認証と権限の確かめ、本人の `ActorSession` を本人だけに渡すこと、応答を相手・観戦者・記録に入れないこと、ホストの操作（ジャンケンの結果・延長戦の開始）を包んだ対戦へ直接送ること（U7-2 まで）、再起動・復元・差し替えで新しい `ActionHost` を作るか `replace_game` を呼ぶこと。

## 2. 決定の情報境界（D-U7-DECISION-UID の確かめ）

決定を出す箇所（`decisions.push_decision` を呼ぶ `effects.py`・`resolution/`・`reactions.py`・`engine.py`）と、観測への投影（`observation._decision`）を読みました（コードを読んだ判断。実行での網羅の確かめではない）。

- 決める人: いつも `PendingDecision.player`。U7 は決める人の `ActorSession` だけに候補を返す（ほかの人には `waiting_for_player` と空の候補）
- 相手・観戦者: 観測は種類・決める人・選ぶ数・選べるものの数だけ（`HIDDEN_COUNT_KINDS` は種類と決める人だけ）。U7 は相手・観戦者に決定の中身を返さない（観測より狭い）
- 決める人: 観測は選べるものの値（`value`）と、見えるカードなら `card_id`。U7 は**選ぶものを番号（`o1`, `o2`, …。並びは決定の選べるものの順）で表し、ホストの中で決定の値に解決する**。カードの uid は、観測が `card_id` を渡すカード（決める人に見えるカード）だけに付ける
- 山札をさがす決定（`DECK_REVEALING_KINDS`）・見た相手の手札の決定（`LOOKED_HAND_KINDS`）: 決定は効果が山札・手札を見たあとに出る（v0.150 で、決定の有無も山札の中身で変えない）。始まった検索の本人には実際のカードを示す
- それ以外のカードの決定 32 種類: 選べるものの出どころは本人の手札・トラッシュ・場のエネルギー・ついているトレーナー・スタジアム（見えるカード）。3 種類（`energy_drain_discard`・`exp_all_energy`・`magma_pool_energy`）は出どころを読み切っていない（未確認）
- 実行時の確かめ: 見えないカードが選べるものに来たら、uid も `card_id` も出さず、その選べるものと候補を `unverified`（理由 `option_not_visible`）にする。**番号に置きかえても、選べるものの数・並びからの漏れは解消しない**。そのため未確認の 3 種類とこの確かめが働いた場面は安全と称さない
- 選ぶ数・最小・最大・重なりなし: `check_choices` と同じ値（決める人に見える決定の値）
- 選ぶと止める選択（`unresolved_choices`・`unresolved_detail`）: 候補から消さず、その選択の処理可能性（コード表の分類で `unresolved_ruling`・`not_implemented`・`technical_limit`、分類のないものは `unverified`）で示す。選んで送ったときのエンジンの拒否と同じ情報（拒否は状態を変えない）

既存の観測の不具合は見つけていません（観測を直していない）。

<!-- generated:decision-kinds begin -->
| 決定の種類 | 選べるものの意味 | 選べるものの出どころ | 決める人が uid を知ってよい時点 | 相手・観戦者に見えるもの |
|---|---|---|---|---|
| `accept_request` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `allocate_damage` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `arrange_deck_top` | card | 始まった検索・見たカード（決定は効果が山札を見たあとに出る） | 決定が出た時点（検索の開始のあと） | 種類・決める人・選ぶ数・選べるものの数 |
| `attach_from_deck` | card | 始まった検索・見たカード（決定は効果が山札を見たあとに出る） | 決定が出た時点（検索の開始のあと） | 種類・決める人だけ |
| `attach_from_discard` | card | 自分のトラッシュ | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `attach_from_hand` | card | 自分の手札 | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人だけ |
| `attach_to_bench` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `bench_from_deck` | card | 始まった検索・見たカード（決定は効果が山札を見たあとに出る） | 決定が出た時点（検索の開始のあと） | 種類・決める人だけ |
| `bench_from_deck_or_hand` | card | 始まった検索・見たカード（決定は効果が山札を見たあとに出る） | 決定が出た時点（検索の開始のあと） | 種類・決める人だけ |
| `bench_from_discard` | card | 自分のトラッシュ | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `bench_guard` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `challenge_bench` | card | 始まった検索・見たカード（決定は効果が山札を見たあとに出る） | 決定が出た時点（検索の開始のあと） | 種類・決める人だけ |
| `damage_option` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `damage_reduction` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `damage_step_order` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `deck_top_from_hand` | card | 自分の手札 | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人だけ |
| `discard_energy` | card | 場のポケモンについているエネルギー（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `discard_from_hand` | card | 自分の手札 | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人だけ |
| `discard_opponent_energy` | card | 相手の場のエネルギー（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `discard_stadium` | card | 場のスタジアム（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `discard_to_deck` | card | トラッシュ（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `discard_to_deck_top` | card | 相手のトラッシュ（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `energy_drain_discard` | card | 未確認（効果の要求の options。実行時の確かめに任せる） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `entry_power` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `esp_redo` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `evolution_heal` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `evolution_song_pokemon` | pokemon | カードでない値（pokemon） | — | 種類・決める人だけ |
| `exp_all_energy` | card | 未確認（続きの情報の options。実行時の確かめに任せる） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `forced_switch` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `hand_to_active` | card | 自分の手札 | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人だけ |
| `hand_to_deck` | card | 自分の手札 | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `heal_allocation` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `janken_hand` | janken | カードでない値（janken） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `knock_out_power` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `ko_prevention` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `magma_pool_energy` | card | 未確認（反応の選択の options。実行時の確かめに任せる） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `move_energy` | card | 場のポケモンについているエネルギー（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `move_opponent_energy` | card | 相手の場のエネルギー（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `ninja_trick` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `opponent_hand_to_bench` | card | 効果で見た相手の手札 | 決定が出た時点（見たあと） | 種類・決める人だけ |
| `opponent_hand_to_deck` | card | 効果で見た相手の手札 | 決定が出た時点（見たあと） | 種類・決める人だけ |
| `optional_coin` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `optional_discard_all` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `optional_drain` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `optional_heal` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `optional_shuffle` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `peek_card` | peek_target | カードでない値（peek_target） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `post_knockout_power` | card | きぜつしたカード（トラッシュ。公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `prize_first` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `promote_active` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `quiz_answer` | name | カードでない値（name） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `quiz_attack` | number | カードでない値（number） | — | 種類・決める人だけ |
| `quiz_card` | card | 自分の手札 | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人だけ |
| `quiz_height_answer` | value | カードでない値（value） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `reaction_order` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `reaction_power` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `reaction_switch` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `recover_energy` | card | トラッシュ（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `recover_pokemon` | card | トラッシュ（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `recover_trainer` | card | トラッシュ（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `remove_counters` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `retrieve_energy` | card | トラッシュ（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `return_energy` | card | 場のポケモンについているエネルギー（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `return_to_deck` | card | 自分の手札 | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人だけ |
| `revive_source` | number | カードでない値（number） | — | 種類・決める人だけ |
| `search_deck` | card | 始まった検索・見たカード（決定は効果が山札を見たあとに出る） | 決定が出た時点（検索の開始のあと） | 種類・決める人だけ |
| `search_deck_or_discard` | card | 始まった検索・見たカード（決定は効果が山札を見たあとに出る） | 決定が出た時点（検索の開始のあと） | 種類・決める人だけ |
| `secret_plan_card` | card | 自分の手札 | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `select_attached_special_energy` | card | 相手の場の特殊エネルギー（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `select_attached_trainer` | card | 相手の場のついているトレーナー（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `select_attack` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `select_color` | color | カードでない値（color） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `select_counter_count` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `select_deck_owner` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `select_devolve_count` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `select_draw_count` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `select_evolution_card` | card | 自分の手札 | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人だけ |
| `select_exchange_card` | card | 効果で見た相手の手札 | 決定が出た時点（見たあと） | 種類・決める人・選ぶ数・選べるものの数 |
| `select_hand_card` | position | カードでない値（position） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `select_hand_positions` | position | カードでない値（position） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `select_look_count` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `select_marker_count` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `select_opponent_attack` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `select_opponent_prize` | position | カードでない値（position） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `select_pokemon` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `select_prize_card` | position | カードでない値（position） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `select_special_condition` | number | カードでない値（number） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `split_from_deck` | card | 始まった検索・見たカード（決定は効果が山札を見たあとに出る） | 決定が出た時点（検索の開始のあと） | 種類・決める人だけ |
| `stadium_from_discard` | card | トラッシュ（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `stadium_return_bench` | pokemon | カードでない値（pokemon） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `swap_with_prize` | card | 自分の手札 | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
| `take_looked_cards` | card | 始まった検索・見たカード（決定は効果が山札を見たあとに出る） | 決定が出た時点（検索の開始のあと） | 種類・決める人だけ |
| `take_looked_pokemon` | card | 始まった検索・見たカード（決定は効果が山札を見たあとに出る） | 決定が出た時点（検索の開始のあと） | 種類・決める人だけ |
| `take_looked_trainer` | card | 始まった検索・見たカード（決定は効果が山札を見たあとに出る） | 決定が出た時点（検索の開始のあと） | 種類・決める人だけ |
| `take_prize` | position | カードでない値（position） | — | 種類・決める人・選ぶ数・選べるものの数 |
| `use_discard_trainer` | card | トラッシュ（公開） | もとから見える（観測が card_id を渡すときだけ uid を付ける） | 種類・決める人・選ぶ数・選べるものの数 |
<!-- generated:decision-kinds end -->

## 3. 対応する操作と完全性

| 状況 | 本人の候補 | 完全性 | 注 |
|---|---|---|---|
| 本人の決定（サイドを取る・バトル場に出す・ほかの決定） | `take_prize`・`promote_active`・`answer_decision` の 1 つ | `complete` | どれも `ResolveDecision` で送る（エンジンは 3 つの決定の段階で同じ答えを受け付ける。`TakePrize`・`PromoteActive` と同じ選択） |
| 本人の番の main | `end_turn` | `partial`（`not_covered_kinds` にほかの 12 種類） | 全合法手ではない |
| 準備（自分が置く・引く） | なし | `partial`（`not_covered_kinds` に `place_starting`・`mulligan_draw`） | U7-1 が対応しない種類（ゲーム上できないのではない） |
| ジャンケンの結果・延長戦の開始の待ち | なし | `complete` | `waiting_for_host`（ホストの操作。U7-2） |
| 相手の番・相手の決定・相手の準備 | なし | `complete` | `waiting_for_player` |
| 終局・停止 | なし | `complete` | `game_over`・`halted` |
| 処理できない結果のあと | 例外 `HostStoppedError` | — | U2 のホストの停止の約束のまま |

## 4. 処理可能性と保証

| 区分 | U7-1 で使う場面 | 保証しないこと |
|---|---|---|
| `supported` | 使わない（受理のあとまで判定する根拠がない） | — |
| `may_stop_later` | 決定への回答・番を終える・それぞれの選択 | 受理（最終の判定は `apply_command`）・受理のあとの続き（ポケモンチェック・効果の続きで、決定待ち・停止・未裁定や未対応による拒否がありうる。先読みしない） |
| `unresolved_ruling`・`not_implemented`・`technical_limit` | 選ぶと止める選択（コード表の分類）、続けられない決定（`not_implemented`） | 候補から消さない。ホストの段で送らない（`CANDIDATE_NOT_EXECUTABLE`。ゲーム上の禁止ではない） |
| `unverified` | 見えないカードが選べるものに来た場面・分類のない停止のコード | 何も保証しない。送ることはできる（最終の判定は `apply_command`） |

候補ごとに `guarantees`（`preconditions`・`acceptance`・`after_acceptance`）を返します。番を終える操作の `preconditions` は `require_turn` と同じ公開の条件（番のプレイヤーの main）だけで、ポケモンチェックは評価していません。決定への回答の `preconditions` は入力の検査（`check`）が確かめる公開の制約で、入力をすべてそろえて初めて分かる判定（選んだものの組み合わせによる効果の続き）は送ったあとのエンジンの判定です。

例（構築盤面のテストで確かめた）: エネルギー回収の 2 枚目の決定は最小 0 で辞退を示しますが、0 枚の答えはエンジンが未裁定で拒否します（状態は変わらない）。候補は受理を保証しないので、これは契約どおりです。

## 5. 取っ手と状態の対応

- `game`: `ActionHost` ごと（世代ごと）の `secrets.token_hex(16)`。`revision`: 候補の一覧ごとの `secrets.token_hex(16)`。エンジンの乱数（`state.rng`）・状態のハッシュ・乱数の確認値・決定の番号を使わない。保存・復元しない
- 取っ手の対応: (対戦の世代, 操作主体, 候補を作った状態のオブジェクト, 候補の一覧)。状態は値・ハッシュでなく、同じオブジェクトかで比べる（`HostedGame` は受理で状態を置きかえ、拒否では同じ状態を持つ）
- 失効: 受理（U7 から送った操作でも、ホストが包んだ対戦へ直接送った操作でも）・`replace_game`・`invalidate`・新しい `ActionHost`（ホストの作り直し）・保持の上限を超えたとき。拒否（エンジンの拒否・ホストの段の拒否）では、どの主体の取っ手も失効しない
- 保持の上限: 操作主体ごとに `MAX_REVISIONS_PER_ACTOR`（4）。超えたら古い順に失効する。状態が変わった取っ手は次の問い合わせで捨てる（保持は最大 8 個、寿命は次の受理まで）

拒否（ホストの段。エンジンに渡さない。状態は変わらない。決まった文で、入力の値を文に入れない）:

| 場合 | コード |
|---|---|
| 別の対戦・前の世代 | `CANDIDATES_WRONG_GAME` |
| 知らない・失効した取っ手（状態が変わった・上限で捨てた） | `CANDIDATES_STALE` |
| 別の操作主体の取っ手 | `CANDIDATES_WRONG_ACTOR` |
| 取っ手にない候補 | `CANDIDATE_UNKNOWN` |
| 入力が制約に合わない（番号・数・重なり・値の範囲・型） | `CANDIDATE_INPUT_INVALID` |
| 処理できない選択・候補 | `CANDIDATE_NOT_EXECUTABLE` |

## 6. 利用例

```python
from kyuura_engine.legal_actions import ActionHost

# ホスト: 対戦を始め、認証した操作主体を結びつける（認証はホストの責任）
host, start = ActionHost.start(deck0, deck1, seed, on_result=lambda actor, result: broadcast(result.view_for(1 - actor), result.view_for(None)))
alice = host.session(0)          # 本人 0 の入口だけを本人 0 に渡す

# クライアント: 候補を取る
r = alice.candidates()           # {"situation": "actor_to_act", "coverage": {...}, "candidates": [{"id": "c1", "kind": "answer_decision", ...}]}
stage = alice.inputs(r["game"], r["revision"], "c1")["stages"][0]   # {"input": "choose_option", "count": {"min": 2, "max": 2}, "options": [{"id": "o1", "card": 2, "card_id": ...}, ...]}

# 決定への入力（番号で選ぶ。順序はそのまま）
result = alice.submit(r["game"], r["revision"], "c1", ["o2", "o1"])  # ActionResult(outcome="accepted", view=ActorDiagnostic(...))

# 番を終える（入力なし）
r = alice.candidates()
result = alice.submit(r["game"], r["revision"], "c1")

# 古い取っ手は拒否される → 取り直す
old = alice.submit(r["game"], r["revision"], "c1")   # ActionResult(outcome="refused", refusal=Refusal(code="CANDIDATES_STALE", ...))
r = alice.candidates()
```

表示の例:

- `processability` が `unresolved_ruling`: 「この選択は記録で裁定が決まらないため、今は処理できません（ゲーム上の禁止ではありません）」
- `not_implemented`: 「この選択・決定はエンジンが未対応です（ゲーム上の禁止ではありません）」
- `unverified`: 「処理できるかを確かめられません。送るとエンジンが判定します」
- `may_stop_later`: 「送れます。そのあとの処理で止まる・決定を求められることがあります」
- 通常の閲覧者（相手・観戦者）へ返す結果: ホストが `on_result` で受け取った `CommandResult.view_for(相手)`・`view_for(None)`（`StatusNotice`。拒否は知らせない）。本人の候補・入力は渡さない

## 7. 検証（限定）

- `tests/test_legal_actions_u7_1.py`: 構築盤面（パソコン通信の複数の選択・枚数・順序・始まった検索、「のぞむなら」の辞退、エネルギー回収の辞退の拒否、どくのきぜつからサイド・バトル場に出す決定、双子）、補助の作り（選ぶと止める選択・続けられない決定・見えないカード）、new_game からの合法な操作の列（ピカチュウの seed 0 の終局・seed 9 の延長戦の開始待ち・ドライアップの停止・停止で始まる対戦・準備・3 つの規約集合・直接の送信と同じ状態）、取っ手（受理の失効・拒否で失効しない・直接の送信・差し替え・復元・作り直し・保持の上限・エンジンの乱数）、内部エラーのあとの停止
- 双子は取っ手の文字列を比べず、取っ手を除いた候補・制約・入力の検査・診断を比べる（広い正規化をしていない）
- 全体のテスト・状態の監査・lockstep・大きな対戦は実行していない

## 8. 実装の識別・既存の API への影響

- 新しいファイル `kyuura_engine/legal_actions.py` を、識別の設計の分類表の部品 `legal_actions`（層 `api_format`）に加えた。ゲームの挙動のファイルはこれを読み込まない（依存の向きの検査）
- 現行の識別の方式（`kyuura-package-files-sha256/1`）では、このファイルと版の更新で `behavior_digest` が変わるので、v0.159 までの完全な記録・スナップショットは v0.160 では unsupported です（いつもの版の更新と同じ。識別の関数・互換の判定は変えていない）
- エンジン・観測・アダプタ・診断・規約集合（3 つの ID・版・中身・照合値）・カードデータ・固定デッキ・参照データは変えていない
