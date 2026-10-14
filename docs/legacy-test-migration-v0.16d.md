# 重複処理の統合とテストの移行（v0.16d）

v0.16b で v0.13 のワザの解決の経路を外したあとに残った、重複する処理・旧経路に依存するテスト・実験用の互換の層・`WRONG_PHASE` の理由の文を整理しました。v0.16a〜v0.16d で移したテストの対応表もここにまとめます。

- 依頼: 重複する処理（ダメージに応じた回復・`programs.Drain`・きぜつの処理・きぜつしたあとの任意の効果の候補・決定の再開）を調べ、ルールの意味が同じものだけを統合する（見た目が似ていても時点・対象の扱いが違えば共通にしない）。旧経路の内部の関数を使うテストを今のコードで数え直し、公開の API か KERNEL の明確な内部の入口に移す（原典に基づく期待・テストの意図・盤面を直接作るテストを減らさない。件数だけでなく確かめているルールの条件を保つ）。互換の層を残すか外すかを決める。`WRONG_PHASE` の理由の文を決まった並びにする（独立したコミット）。
- 前提: [legacy-removal-audit-v0.16a.md](legacy-removal-audit-v0.16a.md)（5 章: v0.15 の木の依存の数）・[kernel-consolidation-v0.16b.md](kernel-consolidation-v0.16b.md)・[preflight-consolidation-v0.16c.md](preflight-consolidation-v0.16c.md)。
- 裁定・止める条件・コード・状態・ログ・乱数は変えていません（`WRONG_PHASE` の理由の文の段階の並びだけが変わる。5 章）。

## 1. 結論

| 項目 | 結果 |
|---|---|
| 重複する処理（6.1） | 依頼の 5 つは、v0.16b で旧経路の側を外したので、どれも 1 か所の実装になっている（2 章）。見た目が似ていても意味の違う処理（きぜつの一覧の順番・回復の種類・不変条件の確かめ）は統合しない。使われない解決の記録の型 2 つ（`Delegated`・`ElementSkipped`）を外した |
| テストの依存（6.2） | 同じ数え方で v0.15（`aa551ab`）と今を比べた（3 章）。経路を選ぶ名前は 40 行・7 ファイル → 1 行（参照データを作るときだけ）、`engine.py` の内部の関数は 9 行・4 ファイル → 1 行（振り分けの表 `_HANDLERS` の確かめ）、互換の層は 65 行・3 ファイル → 0 |
| 移したテスト | v0.15 から、42 のテストメソッドと 14 の補助の関数（変えた 12・加えた 1・外した 1）を変えた（6 章の対応表）。外したテストは 6 件で、どれも同じ性質を確かめる新しいテストに置きかえた（外しただけのテストはない） |
| 移したあとの確かめ | 枠の外の誤りを別の型にした写しで全体を走らせ、旧経路の名残で「別の理由で通っていた」テストを 1 件見つけて直した（じこさいせいの K3。7 章）。故障を注入するテストは、注入した誤りそのものが出たことを確かめるようにした |
| 実験用の互換の層（6.3） | **外した**（4 章）。テストと比較の道具は `kyuura_engine.resolution` と `engine` の内部の入口を直接使う。コードの複製・`sys.modules` の別名はない（テストで確かめる） |
| `WRONG_PHASE`（6.4） | 決まった並び（段階の定義の順）にした（独立したコミット `0618e1c`。5 章） |
| テストの数 | v0.15 の 1,780 → v0.16d の 1,819（加えた 45・外した 6。外した 6 件は置きかえ） |

## 2. 重複する処理の調査（6.1）

### 2.1 依頼の 5 つ

| 処理 | v0.15 の実装（旧経路 / KERNEL） | v0.16d の実装 | 判断 |
|---|---|---|---|
| ダメージに応じた回復（メガドレイン・やどりぎのタネ） | `effects._remove_attacker_counters`（旧経路。`DamageAndDrain.resolve` などから）/ `programs.Drain`（KERNEL） | `programs.Drain` だけ（v0.16b で旧経路の側を外した） | 統合済み。ログ `drain_heal`・`drain_heal_skipped` の形は同じ（参照データ・固定した v0.13 との比較で確かめる） |
| `programs.Drain` | 上と同じ | 同じ | 同じ |
| きぜつの処理（トラッシュ・ログ `knock_out`） | `engine._after_knockouts` などの旧経路の一連の処理 / `flow._knock_out_after_attack` | `procedures.knock_out`（1 匹のきぜつ）を、ワザのあと（`flow._knock_out_after_attack`）とポケモンチェック（`flow._pokemon_check`）の 2 か所が使う | 統合済み。2 か所の違い（同時のきぜつの印 `simultaneous`・時点 `timing="pokemon_check"`）はログの項目で、ルールの意味（原因）が違うので引数で分ける |
| きぜつしたあとの任意の効果の候補（ふしちょう） | `engine._post_knockout_candidates`（旧経路）/ `kernel.capture_post_knockout` | `kernel.capture_post_knockout` を、ワザのあととポケモンチェックの 2 か所が使う | 統合済み |
| 決定の再開 | `engine._RESUMERS`（旧経路の 6 つの再開先）/ `resolution` の再開 | 入口は `engine._answer_decision` の 1 つ（確認は `checks.decision_choices`）。再開先が `resolution.RESUMES` なら `resolution.resume_decision`、`trainer` なら `engine._resume_trainer` | 統合済み。トレーナーの決定は KERNEL の範囲外（依頼の範囲外のコマンド）なので、再開の処理を分けたまま |

### 2.2 似ているが統合しないもの

| 処理 | 違い | 判断 |
|---|---|---|
| ワザのあとのきぜつの一覧（`kernel.knocked_out`）と、ポケモンチェックのきぜつの一覧（`procedures.pokemon_check_poison` の戻り値） | 並びの定義が違う: ワザのあとは「番でないプレイヤー → 番のプレイヤー」（p.323〜324。v0.13 と同じ）、ポケモンチェックは「番を終えたプレイヤーの場から」（ログ `poison_damage` の順。v0.13 と同じ）。ポケモンチェックでは両方のプレイヤーのきぜつを先に止める（`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`）ので結果は同じになるが、並びの意味が違う | 統合しない（並びを変えるとログの順番の約束が変わる） |
| メガドレイン（`programs.Drain`。与えたダメージから）・じこさいせい（`programs.DiscardEnergyHealAll`。すべて）・きずぐすり（トレーナー。ログ `remove_damage_counters`） | 発生条件・量・ログの形が違う（CLAUDE.md「きずぐすりのログの形は変えない」） | 統合しない |
| きぜつの判定の任意の効果（こんじょう。`kernel.ko_prevention_offers`）と、きぜつしたあとの任意の効果（ふしちょう。`kernel.capture_post_knockout`） | 窓（トラッシュの前 / 勝ち負けの判定のあと）・条件（相手のワザのダメージ / 原因を問わない）が違う（CLAUDE.md v0.12「こんじょうの処理を流用しない」） | 統合しない |
| 不変条件（`engine._post_knockout_candidate_problems`・`_ko_prevention_decision_problems` など）と KERNEL の候補の求め方 | 不変条件は、KERNEL とは別に状態とログから組み立て直して確かめる（同じ関数を使うと、確かめが自分自身を確かめることになる） | 統合しない（独立した確かめのまま） |
| HP 以上かの比較（`damage >= hp`）が 10 か所ほど | 比較そのものは同じだが、使う時点（ダメージを受ける前・のせたあと・候補の判定・不変条件）と対象が違い、どれも 1 行 | 共通の関数にしない（表面的に似ているだけ。変えても確かめの対象が増えない） |

### 2.3 使われない名残

解決の記録の型のうち、`events.Delegated`（「v0.13 に渡したコマンド」。v0.14 のプロトタイプが範囲外のコマンドを v0.13 に渡したときの記録）と `events.ElementSkipped` は、v0.15b から記録する所がなく、どのコード・テスト・道具からも使われていませんでした（v0.15 の木でも同じ）。旧経路への委譲の名残なので外しました。状態・ログ・書き出しには関係しません（解決の記録は状態に保存しない）。

## 3. テストの依存の数え直し（6.2）

v0.14 の報告（テストモジュール 14 個と `tests/helpers.py`、約 105 か所。名前を grep した数）と v0.16a の数え直し（v0.15 の木、コードの行の数）のあと、今のコードで数え直しました。数え方: テストのモジュールごとに、読み込んだ名前（`from … import …`）を追い、その名前を使うコードの行（構文木の名前。文字列・コメントは数えない）を数える。同じ数え方で、固定した v0.15（`aa551ab`）と今（v0.16d）を比べます。

| 依存の種類 | v0.15（`aa551ab`） | v0.16d | 変わったこと |
|---|---|---|---|
| 経路を選ぶ（`Route`・`apply_command_via`・`apply_legacy`・`handles`） | 7 ファイル・40 行 | 1 ファイル・1 行 | 残るのは tests/legacy_reference.py の参照データを作るとき（旧経路のある v0.16a の木でだけ。ない木では `RuntimeError`）だけ |
| 解決の設定を選ぶ内部の入口（`apply_command_with`・`apply_command_traced`・`apply_kernel`） | 3 ファイル・29 行 | 8 ファイル・51 行 | 経路を選ぶテストの移し先（v0.16b）と互換の層の移し先（v0.16d） |
| v0.13 の約束の補助関数（`deal_attack_damage`・`attack_reaches`・`finish_damage_elements`・`push_attack_decision` など） | 11 ファイル・44 行 | 12 ファイル・59 行 | 補助関数は KERNEL の枠への入口になった（v0.16b）。直接呼ぶ単体テストは `resolution.open_attack` で枠を開く。増えたのはアダプタのテスト（tests/test_contract_adapter_v0_16.py の 14 行） |
| `engine.py` の内部の関数（`_ko_prevention_offer`・`_post_knockout_candidates`・`_after_knockouts`・`_next_prize_or_judge` など） | 4 ファイル・9 行 | 1 ファイル・1 行 | 旧経路の関数は外した。残るのは振り分けの表 `engine._HANDLERS` の確かめ（tests/test_kernel_integration_v0_15.py） |
| KERNEL の部品（`kyuura_engine.resolution`） | 3 ファイル・88 行 | 16 ファイル・193 行 | 旧経路の関数の移し先（`flow`・`kernel`・`codec`・`programs`）と互換の層の移し先 |
| `AttackUse` を直接作る | 8 ファイル・15 行 | 5 ファイル・8 行 | 補助関数に渡すものは `open_attack` に移した。残るのは、宣言の前の確認（`damage_profile`）に渡すものと、比較・ハッシュに入口が含まれないことの確かめ |
| 実装の `resolve` を直接呼ぶ | 4 ファイル・9 行 | 5 ファイル・10 行 | トレーナーの `resolve`（test_defender。範囲外）、`super().resolve`（アダプタで処理する部分型）、じこさいせいの K3（v0.16d から枠の中で。7 章）、アダプタのテスト |
| 内部の関数を差しかえる（`mock.patch`） | 5 ファイル・21 行 | 6 ファイル・23 行 | 旧経路の関数を差しかえていた 8 か所は、KERNEL の同じ所に移した（6.3 節） |
| 宣言の前の判定（`damage_profile`・止める関数。残すもの） | 6 ファイル・12 行 | 6 ファイル・12 行 | 変えていない（v0.16c で `v013_checks` の外の使い道はない） |
| 互換の層（`experiments.event_kernel`） | 3 ファイル・65 行 | 0 | v0.16d で外した（4 章） |

（v0.16a 5 章の表は grep で名前を数えたもので、この表とは数え方が違います。v0.15 の木の数がそれぞれ違うのはそのためです。）

## 4. 実験用の互換の層（6.3）

`experiments/event_kernel/__init__.py` は、v0.15b で本番の部品（`kyuura_engine/resolution`）になった v0.14 のプロトタイプの名前を、v0.14 のテストと比較の道具のためにつなぐ層でした（`sys.modules` に本番のモジュール 8 つを `experiments.event_kernel.*` の名前でも登録し、`apply_command`・`owned` の 2 つの関数を持つ）。

| 観点 | 残す | 外して、テストと道具を本番の内部の入口に移す |
|---|---|---|
| 使う所 | — | このリポジトリの中の 3 つだけ（tests/test_event_kernel_v0_14.py・tools/event_kernel_compare.py・tests/test_kernel_integration_v0_15.py の確かめ）。外の利用者はいない（公開の API でない。`pyproject.toml` のパッケージは `kyuura_engine` だけ） |
| 正しさ | 同じモジュールが 2 つの名前を持ち、差しかえ（`mock.patch`）がどちらの名前でも効く。読む人がどちらが正本か迷う | 正本は 1 つ |
| 移す費用 | なし | 名前の置きかえだけ（テストの名前・盤面・呼び出しの順番は同じなので、参照データ legacy_reference_v0_15.json の呼び出しの鍵も同じ） |
| 依頼の条件 | — | コードの複製・不要な `sys.modules` の操作を残さない |

外しました（`44e8d9d`）。移したもの:

| 使う所 | v0.16c まで | v0.16d |
|---|---|---|
| tests/test_event_kernel_v0_14.py | `K.apply_command`・`K.apply_command_traced`・`K.PREFLIGHT_MODES`・`K.BUILDERS`、`experiments.event_kernel` の `catalog`・`codec`・`events`・`kernel`・`questions`・`preflight`・`flow`・`programs` | `engine.apply_command_with`・`engine.apply_command_traced`、`kyuura_engine.resolution` の同じ名前 |
| tools/event_kernel_compare.py | `K.owned`・`K.apply_command_traced`・`experiments.event_kernel.events` | `resolution.processes`・`engine.apply_command_traced`・`resolution.events` |
| tests/test_kernel_integration_v0_15.py `DependencyTest.test_compatibility_layer_is_not_a_copy` | 互換の層の名前が本番のモジュールそのものを指す | `test_no_copy_of_the_kernel_remains`: `experiments` がない・どのコード（本番・テスト・道具・scripts）も読み込まない・本番のモジュールが別の名前で `sys.modules` に登録されていない（互換の層がある木では 8 つの別名を見つけることを確かめた） |

比較の道具は、移したあとも同じ結果です（`--corpus natural --modules test_moltres_games_v0_12 --natural-seeds 3 --mode all` と `--corpus stress --stress-seeds 1 --mode both --mixed` で食い違い 0）。

## 5. `WRONG_PHASE` の理由の文（6.4）

| | v0.13〜v0.16c | v0.16d（`0618e1c`） |
|---|---|---|
| 書き方 | 決定を待つ段階の集合 `decisions.DECISION_PHASES`（`frozenset`）の並び。文字列のハッシュの乱数化で、プロセスごとに並びが変わる | 段階の定義の順の並び `decisions.DECISION_PHASE_ORDER`（`take_prize, promote_active, decision`） |
| 例（`main` の段階で決定に答えた） | `PYTHONHASHSEED=0`: 「今は main。この操作は decision, take_prize, promote_active のときだけ」、`=1`: 「… take_prize, decision, promote_active …」 | どの seed でも「今は main。この操作は take_prize, promote_active, decision のときだけ」 |
| 例外の種類・コード | `IllegalActionError`・`WRONG_PHASE` | 同じ |
| 受け付ける段階 | `DECISION_PHASES` | 同じ（`DECISION_PHASES` は `frozenset(DECISION_PHASE_ORDER)`） |
| 状態・ログ・乱数 | — | 変わらない（拒否は状態を変えない） |

- 確かめたテスト: tests/test_wrong_phase_message_v0_16d.py（理由の文・拒否で状態・乱数が変わらない・受け付ける段階、`PYTHONHASHSEED` を 0・1・2・3・4242・random にした別のプロセスで同じ文。集合の並びはこれらの seed で変わる）。
- 固定した v0.13・v0.15 との比較（tools/engine_lockstep.py。記録は `PYTHONHASHSEED=0`）では、決定への答えの `WRONG_PHASE` の理由の文が「decision, take_prize, promote_active」から「take_prize, promote_active, decision」に変わります。`compare` は、段階の名前の並びだけが違い、ほかがすべて同じ拒否を `wrong_phase_order_only` として数え、ほかの理由の文の違いは食い違いにします（v0.16a）。参照データ（tests/legacy_reference.py）は段階の名前を並べかえて比べます。
- ほかの `WRONG_PHASE`（1 つの段階だけを受け付ける操作）の理由の文は、もとから決まった文で、変えていません。

## 6. 移したテストの対応表（v0.16a〜v0.16d）

「性質」は、そのテストが確かめているルールの条件・エンジンの性質です。移したあとも同じ性質を確かめます（盤面・原典に基づく期待の値は変えていない。変えたものは 6.4 節）。

### 6.1 旧経路の結果と比べていたテスト（v0.16a: 参照データに移した）

v0.15 までは同じ木の中で旧経路（`apply_legacy`・`Route.LEGACY`）の結果と比べていました。旧経路のある木（v0.16a。`kyuura_engine/` は `aa551ab` と同じ）で旧経路の結果を記録した参照データ（tests/fixtures/legacy_reference_v0_15.json。呼び出し 1,875 件・対戦の連なり 37）と比べるようにしました。盤面の指紋が記録と違えば失敗します。

| テスト | v0.15 | v0.16a から | 性質 |
|---|---|---|---|
| test_event_kernel_v0_14 `Both.both`（42 件のテストが使う） | 旧経路と KERNEL を同じ状態で処理して比べる | KERNEL の結果を参照データと比べる | 状態（形式 9 の全体・ログ・乱数の指紋・決定）・拒否の種類・コード・理由の文が v0.13 と同じ |
| test_event_kernel_v0_14 `GameTest.test_reproducible_and_audited` | 旧経路と KERNEL で対戦を進める | 参照データの対戦の連なり | new_game からの対戦が v0.13 と同じ・再現できる・監査を通る |
| test_event_kernel_games_v0_14 の 3 件（`test_natural_policies_in_both_modes`・`…_with_mixed_states`・`test_stress_scenarios_in_both_modes_with_mixed_states`） | `Comparator` が 1 歩ごとに旧経路と比べる | `Comparator(reference=…)` が参照データと比べる | 対戦の 1 歩ごとに v0.13 と同じ |
| test_kernel_integration_v0_15 `MessageTest.test_stop_messages_are_the_same_on_both_routes` | 旧経路の理由の文と比べる | 参照データ | 止める理由の文が v0.13 と同じ |
| test_kernel_integration_v0_15 `DispatchTest.test_effects_outside_the_table_use_the_v0_13_path`・`test_subclass_of_a_table_entry_is_not_compiled` | 旧経路の結果と比べる | 参照データ（v0.16b からアダプタで処理した結果と比べる） | 対応表にない実装（v0.13 の約束）の結果が v0.13 と同じ |
| test_preflight_v0_15c `EquivalenceTest.test_derived_matches_derived_full_and_the_v0_13_route`・`test_the_real_run_happens_once`、`LimitTest.test_verified_fallback_accepts_like_the_v0_13_route` | 旧経路の結果と比べる | 参照データ | 先読みの方法によらず v0.13 と同じ結果・実際の処理は 1 回 |

参照データそのものの確かめ: tests/test_legacy_reference_v0_16.py（5 件。旧経路のある木で記録したこと・盤面が違えば比べない・知らない呼び出しは失敗・`WRONG_PHASE` の並びだけを正規化）。固定した木との比較の道具: tests/test_lockstep_tool_v0_16.py（6 件）。

### 6.2 旧経路の関数を直接呼んでいたテスト（v0.16b）

| テスト | v0.15 | v0.16b から | 性質（根拠） |
|---|---|---|---|
| helpers `apply_legacy` | 経路 `LEGACY` で処理する | 外した（使っていたテストは下の各行） | — |
| helpers `apply_kernel` | `apply_command_via(..., route=Route.KERNEL)` | `engine.apply_command_with` | 解決の設定（先読みの方法）を選んで処理する |
| test_combat `SimultaneousKnockOutOrderTest.test_non_turn_player_promotes_first`・`test_both_cannot_field_is_sudden_death_and_not_continued` | `engine._after_knockouts(state)` | `flow._after_knockouts(Resolution(state), (), None, ())` | バトル場に出す順番（番でないプレイヤーが先。pp.323〜324）・両方が出せなければサドンデス（p.311） |
| test_simultaneous_ko `PrizeOrderTest.test_order_does_not_change_the_result`（補助の `finish`） | `engine._next_prize_or_judge(state, order)` | `flow._next_prize_or_judge(Resolution(state), order, None, ())` | 同時のきぜつでサイドを取る順番は結果を変えない（p.325。正規化の根拠） |
| test_phoenix `CauseTest.test_location_is_not_restricted`・`GasTest.test_gas_source_knocked_out_at_the_same_time_is_unresolved`・`test_two_candidates_are_an_engine_error`（補助の `_post_knockout_candidates`） | `engine._post_knockout_candidates` | `kernel.capture_post_knockout`（コードのない問いはコマンドの入口と同じく `questions.to_error` で `RuntimeError`） | ふしちょうの候補（場所を問わない。P）・ガスの発生源がいっしょにきぜつ（P19）・候補が 2 つ以上（P32）はエンジンの不具合として止める |
| test_guts `SourceTest.test_offer_needs_this_attacks_damage`・`ConditionAndGasTest.test_bench_location_is_not_restricted` | `engine._ko_prevention_offer(state, use)`・`use.ko_prevention_able` | `kernel.ko_prevention_offers(Resolution(state))`・`res.ko_prevention_able` | こんじょうを使えるのは、そのワザのダメージで HP 以上になったポケモン（G3〜G7）・場所を問わない |
| test_guts `G37Test.test_declared_elements_match_the_implementations` | 実装の `resolve` の中の `attack_reaches` の呼び出しを読む | 登録されたワザの要素の並び（`programs.opponent_effect_elements`）と実装の宣言を照らす | G37 の宣言の書き忘れで見落とさない |
| test_counterattack `ConditionTest.test_evaluated_when_receiving_not_at_declaration` | `AttackUse` を作り `use.counterattacks` を見る | `open_attack` の枠で `runtime.pending` を見る | はたらくかはダメージを受けるときの状態で決める（C） |
| test_counterattack `DirectTest` の 4 件（`test_pending_is_applied_at_the_end_of_the_damage_elements`・`test_two_pending_counters_are_not_ordered`・`test_damage_not_received_does_not_trigger`・`test_memo_is_not_state`） | `AttackUse.counterattacks`・`PendingCounterattack` | `open_attack` の枠の送る効果の列（`runtime.pending`・`kernel.Deferred`） | ダメージの要素のあとに与える（p.89）・2 つ以上は順番が決められない（C34・C35）・受けなかったダメージではたらかない・ワザ 1 回の中の値は状態でない |
| test_transparency `DirectReceptionTest.test_each_haunter_flips_once_per_attack`・`test_attack_use_memo_is_not_state` | `AttackUse` を作り `use.reception` を見る | `open_attack` の枠 | 同じワザの同じポケモンは 1 回だけ投げる（T4）・記録は状態でない（2 匹目は 6.4 節） |
| test_damage_drain `DamageResultTest` の 5 件（補助の `use`） | `AttackUse` を作り `deal_attack_damage` に渡す | `open_attack(state, 0, attack_index=MEGA_DRAIN)` | `DamageResult`（計算した 0 と防いだことの区別・HP で上限をつけない。p.319） |
| test_damage_result_audit `DamageResultTableTest.test_table`・`test_prevented_is_never_knocked_out_by_the_element`（補助の `deal`） | 同上 | `open_attack` | 同上（監査の表） |
| test_kernel_invariants（補助の `Recorder`） | `resolution.handles`・`apply_command_via(..., route=KERNEL)` | `resolution.processes`・`apply_command_with` | 解決の基盤の独立した不変条件（1〜12）を対戦の 1 歩ごとに確かめる |
| test_event_kernel_games `LockstepGamesTest.test_a_divergence_is_reported` | 旧経路と違う結果を食い違いとして報告する | 参照データと違う結果を報告する | 比較の道具が食い違いを見落とさない |
| test_alakazam_line `KadabraRecoverTest.test_unreachable_case_stops_loudly`（v0.16d で直した。7 章） | 実装の `resolve` を直接呼ぶ（K3 で `RuntimeError`） | `open_attack` の枠で呼び、K3 の理由の文を確かめる | トラッシュできないときは黙って処理しない（K3） |
| test_unresolved_boundaries `CodeListTest.test_every_code_in_the_engine_is_covered_here` | `kyuura_engine/*.py` の `UNRESOLVED_…` を数える | `rglob`（解決の基盤 `resolution/` も数える） | エンジンが止めるすべてのコードに、止まる場合と隣の止まらない場合がある |
| test_kernel_integration `RouteTest` の 4 件 | 経路の選び方 | `EntryTest` の 4 件（`test_public_apply_command_is_unchanged`・`test_settings_are_chosen_explicitly`・`test_preflight_modes_give_the_same_result`・`test_no_module_state_changes`）。外した名前（旧経路の 28・旧ダメージ処理境界の 7）が戻らないことも確かめる | 公開の `apply_command` の呼び方は変えない・設定は引数で選ぶ・グローバルな可変フラグで切り替えない |
| test_kernel_integration `DependencyTest.test_legacy_handlers_do_not_use_the_kernel` | 旧経路の処理は解決の基盤を使わない | `test_out_of_scope_handlers_do_not_use_the_kernel`（範囲外のコマンドの処理は解決の基盤を使わない） | 依存の向き・範囲 |
| test_kernel_integration `DispatchTest.test_target_commands`・`test_every_registered_attack_is_handled_by_the_kernel`・`test_opponent_effect_elements_come_from_the_program` | `resolution.handles` で受け持つかを見る | `resolution.COMMANDS`・`RESUMES`・`engine._HANDLERS`・解決の記録で、どこが処理したかを見る（トレーナーの決定は engine.py） | 振り分け |
| test_kernel_integration `KernelGuardTest.test_questions_are_detected_in_the_real_run`・`MessageTest.test_refused_chain_names_the_assumption` | 旧経路と KERNEL の両方 | KERNEL だけ（旧経路の側は参照データ・固定した木の比較で） | 先読みを外しても実際の処理が同じ問いで止める・番の進み方の前提を理由の文に書く |

### 6.5 互換の層の名前の置きかえ（v0.16d）

tests/test_event_kernel_v0_14.py の 7 件（`UnresolvedTest` の 3 件・`ChainAndAtomicityTest` の 3 件・`CatalogTest.test_every_registered_attack_has_a_program`）と補助の `GameTest.play` は、互換の層の名前（`K.apply_command`・`K.PREFLIGHT_MODES`・`K.BUILDERS`・`experiments.event_kernel.preflight` など）を、本番の同じもの（`engine.apply_command_with`・`resolution.PREFLIGHT_MODES` など）に置きかえただけです（4 章。盤面・期待・呼び出しの順番は同じ）。

### 6.6 新しく加えたテスト

tests/test_contract_adapter_v0_16.py（11 件。v0.13 の約束で書いた実装のアダプタ: どの実装に使うか・処理できない実装の拒否・補助関数が KERNEL の窓を通ること・別の状態の拒否・窓の順番・枠の外の誤り・2 段階の決定と保存・復元・宣言の前の確認・部分型）。

### 6.3 故障の注入の移しかえ

旧経路の内部の関数を差しかえていたテスト（v0.15 は経路 `LEGACY` を指定）は、KERNEL の同じ処理の境界に誤りを注入するようにしました（v0.16b）。v0.16d から、注入した誤りそのもの（「注入した誤り」）が出たことも確かめます（差しかえた所を処理が通ったこと。ほかの誤りで通らない）。

| テスト | 注入する所（v0.15・旧経路） | 注入する所（v0.16b〜・KERNEL） |
|---|---|---|
| test_counterattack `AtomicityTest.test_internal_error_after_the_counter` | ログ `counterattack`・`effects._remove_attacker_counters`・`effects.push_attack_decision`・`effects.poison` | ログ `counterattack`・ログ `drain_heal`・`codec.push_decision`・`programs.APPLY_CONDITION[POISON]` |
| test_transparency `AtomicityTest.test_internal_error_after_the_power_coin` | `effects.put_to_sleep`・`effects.push_attack_decision`・ログ `attack_evaded` | `programs.APPLY_CONDITION[SLEEP]`・`codec.push_decision`・ログ `attack_evaded` |
| test_counterattack `InvariantTest.test_double_knock_out_guard_after_the_preflight` | `engine.counterattack_double_knockout_problem` を外す | 先読み（`preflight.derived`・v0.16c から `v013_checks.check`）を外す（6.4 節） |
| test_kernel_integration `KernelAtomicityTest`（v0.15b からの KERNEL 側の同じ確かめ） | — | 変えていない（v0.16d で注入した誤りの確かめを加えた） |

### 6.4 期待の値を変えたテスト（根拠）

旧経路の関数を直接呼んでいた単体テストのうち、KERNEL の同じ部品で呼ぶと答えが違うものが 3 つありました。どれも公開の API の動きは v0.15（標準の経路は v0.15d から KERNEL）と同じで、対応カードでは起こらない場合です。

| テスト | v0.15（旧経路の補助関数） | v0.16b〜（KERNEL） | 根拠 |
|---|---|---|---|
| test_transparency `DirectReceptionTest.test_each_haunter_flips_once_per_attack` | 1 つのワザで 2 匹目の「とうめい」も評価してコインを投げた | 2 匹目の前に止める（コードのない問い `multiple_evasion`。コマンドの入口で `RuntimeError`）。1 匹目の確かめ（T4）と、新しいワザで投げ直すことは同じ | T27（1 つのワザで複数の「とうめい」のコインの順番は原典で決められない。docs/transparency-v0.9.md・CLAUDE.md v0.9）。旧経路の補助関数は対応カードで起こらないこの場合を止めていなかった |
| test_counterattack `InvariantTest.test_double_knock_out_guard_after_the_preflight` | 宣言の前の確認を外すと、「はんげき」を与えるところで `RuntimeError` | 先読みを外しても、実際の処理のきぜつの判定（原因の枠が分かれたきぜつ）で、宣言の前と同じ `UnsupportedError(UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT)` で止める | C18（docs/counterattack-v0.10.md）。黙って同時のきぜつにしないことは同じ |
| test_counterattack `DirectTest.test_two_pending_counters_are_not_ordered` | `finish_damage_elements` が `RuntimeError` | 問い `multiple_deferred_effects`（`OpenQuestion`）。コマンドの入口と同じ `questions.to_error` で `RuntimeError`（理由の文に C34・C35） | C34・C35 |

## 7. 移したテストが目的の所で失敗することの確かめ

旧経路を外すと、補助関数は KERNEL の枠の中でだけ使えるようになり、枠の外で呼ぶと `RuntimeError` になります（v0.16b）。`RuntimeError` を期待するテストが、本来の理由ではなく「枠の外」の誤りで通っていないかを、次の写しで確かめました。

- 方法: 今の木の写しで、「枠の外」の誤り（`effects._runtime`）と「別の状態」の誤り（`ContractRuntime._check`）を、`RuntimeError` でない別の例外にして、テスト全体を走らせる。
- 結果: 失敗は 8 件。7 件は、この 2 つの誤りそのものを確かめるテスト（tests/test_contract_adapter_v0_16.py の `OutsideFrameTest.test_helpers_need_the_kernel_frame` の 6 つの呼び出し・`WindowTest.test_a_different_state_is_refused`）で、期待どおり。**1 件（tests/test_alakazam_line_v0_7.py の `KadabraRecoverTest.test_unreachable_case_stops_loudly`）は、じこさいせいの「トラッシュできないとき」（K3。docs/alakazam-line-v0.7.md）の `RuntimeError` を確かめるテストが、v0.16b〜v0.16c は枠の外の誤りで通っていた**（K3 の確かめになっていなかった）。
- 直し: `resolution.open_attack` で枠を開いて実装の `resolve` を呼び、K3 の理由の文（「「超」エネルギーカードがない」）と、状態・決定が変わらないことを確かめるようにした。直したテストは、写しでも通る。
- 故障の注入: 6.3 節の 3 つのテストの補助（`assert_unchanged`）が、注入した誤りの文を確かめるようにした（差しかえた所を通らずにほかの `RuntimeError` で通ることがない）。

## 8. テストの数

| 段階 | 数 | 内訳 |
|---|---|---|
| v0.15（`aa551ab`） | 1,780 | — |
| v0.16a | 1,791 | 参照データ 5・比較の道具 6 |
| v0.16b | 1,802 | アダプタ 11。`RouteTest` の 4 件 → `EntryTest` の 4 件（`test_public_apply_command_is_unchanged` → 同じ名前、`test_routes_are_chosen_explicitly` → `test_settings_are_chosen_explicitly`、`test_route_and_preflight_are_different_settings` → `test_preflight_modes_give_the_same_result`、`test_no_module_state_selects_the_route` → `test_no_module_state_changes`）、`test_legacy_handlers_do_not_use_the_kernel` → `test_out_of_scope_handlers_do_not_use_the_kernel` |
| v0.16c | 1,816 | 依存 5・上限の境界 5・上限を超えたとき 2・製品の上界 2 |
| v0.16d | 1,819 | `WRONG_PHASE` 3。`test_compatibility_layer_is_not_a_copy` → `test_no_copy_of_the_kernel_remains` |

v0.15 から加えたテストは 45 件、外したテストは 6 件（v0.16b の 5 件・v0.16d の 1 件）で、外した 6 件はどれも同じ性質を確かめるテストに置きかえました（6.2 節・4 章）。変えたテストメソッドは 42 件、補助の関数は 14（変えた 12: helpers の `apply_kernel`・test_counterattack の `AtomicityTest.assert_unchanged`・`DirectTest.use`・test_damage_drain の `DamageResultTest.use`・test_damage_result_audit の `deal`・test_event_kernel_v0_14 の `Both.both`・`GameTest.play`・test_kernel_integration の `KernelAtomicityTest.assert_unchanged`・test_kernel_invariants の `Recorder.__call__`・test_simultaneous_ko の `PrizeOrderTest.finish`・test_transparency の `DirectReceptionTest.use`・`AtomicityTest.assert_unchanged`、加えた 1: test_phoenix の `_post_knockout_candidates`、外した 1: helpers の `apply_legacy`）です。ふだんのテストで飛ばすのは 1 件（tests/test_cross_version_compatibility.py の大きな比較。`KYUURA_COMPAT_BASE` を設定したときだけ）で、v0.15 と同じです。

## 9. 残したこと

- 宣言の前の判定（`damage_profile`・v0.13 の止める関数）を直接呼ぶテスト（12 行）は、`v013_checks` の使い道（v0.16c）が残るので、そのまま。
- 参照データ（tests/fixtures/legacy_reference_v0_15.json）は旧経路のある木でしか作れないので、記録した呼び出しの盤面・順番を変えるときは、同じ性質を確かめる別のテストを docs に書く（v0.16a の約束のまま）。
