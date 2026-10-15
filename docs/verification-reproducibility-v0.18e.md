# 検証の再現性: 変異試験の版管理と研究の対応の追跡（v0.18e）

v0.17 までの変異試験は、定義と実行の道具を作業ごとの外の場所に置いていたので、どの版で何を走らせたかを、リポジトリから再現・確認できませんでした。v0.18e で、変異の定義と実行の道具をリポジトリに入れ、研究（kyuura）の id・出典をエンジンから追跡できるようにしました。

## 0. 要約

- 変異の定義: `tools/mutants.py`（50 件。v0.17d までの 46 件を移し、v0.18e の 4 件を加えた）。実行: `tools/run_mutants.py`（`check`・`witness`・`full`）。
- 変異ごとに「証人のテスト」（元のコードで通り、変異で失敗するはずのテスト）を定義に持ち、変異が狙った欠陥を実際に起こしたことを確かめます。構文の誤りの変異は `invalid` として、見つけた数に入れません。
- ふだんのテスト（A 段階）に、定義が今のコードに入ること（ちょうど 1 か所・構文として正しい・証人のテストがある）を確かめるテストを加えました（tests/test_mutation_definitions_v0_18e.py）。
- 研究の対応: `kyuura_engine/data/research_links.json`（v0.18a）に、最新の説明・照合の記録の対応を加え、`scripts/check_research_links.py`（kyuura の研究の基準のコミットと照らす）と tests/test_research_links_v0_18e.py（エンジンの側の集合と照らす）を加えました。
- 結果（v0.18 の最終のコードで実行したもの。3 章）: 変異 50 件のすべてで、変異を入れた写しのテストが失敗しました（`full`。見落とし 0・構文の誤り 0・入らない 0）。50 件のすべてで、証人のテストがすべて失敗しました（`witness`）。元の木では、全体の実行の 33 モジュール・証人のテスト 66 個がすべて通りました。

## 1. 変異の定義（版管理）

`tools/mutants.py` の `Mutant`:

| 項目 | 内容 |
|---|---|
| `id`・`title` | M01〜M20（v0.15d。v0.16e で今のコードに合わせた）・R01〜R14（v0.16e）・S01〜S12（v0.17d）・V01〜V04（v0.18e） |
| `path`・`old`・`new` | ファイルと、置きかえる前の文字列（ちょうど 1 か所）・置きかえたあとの文字列 |
| `origin` | 最初に作った版 |
| `witnesses`（`WITNESSES`） | 元のコードで通り、変異で失敗するはずのテストの id。v0.18e の全体の実行で失敗したテストの中から、変異の狙いに合うもの（1〜3 個）を選んだ |

`MODULES` は全体の実行で走らせるテストのモジュールです（v0.17d の 29 と、v0.18 で加えた 4。33 個）。定義そのものの検査（tests/test_mutation_definitions_v0_18e.py）は入れていません。

v0.18e で加えた変異:

| id | 欠陥 | 狙い |
|---|---|---|
| V01 | Z23 の理由の文で場合を取り違える（要素が無効と最終ダメージが 0） | Z23 の場合分け（v0.18b）を、理由の文で区別していること |
| V02 | 送る効果が残っていてもワザの途中の決定を出す | 窓の途中で黙って止まらないこと（v0.18d の設計の前提） |
| V03 | 研究の対応表から停止コードを 1 つ落とす | 対応表とエンジンの停止コードの集合が同じこと（v0.18e） |
| V04 | 「ダメージを与えた後」の効果の前にワザのコインを置く | Z23-d が起こらない形（v0.18b） |

## 2. 実行の道具

```sh
python3 tools/run_mutants.py check                                   # 定義の検査（速い。木を変えない）
python3 tools/run_mutants.py witness --jobs 3 --out witness.jsonl    # 証人のテストだけ（元の木で通る → 変異で失敗する）
python3 tools/run_mutants.py full --jobs 3 --out full.jsonl          # MODULES のすべて（C 段階）
python3 tools/run_mutants.py full M01 S09 --jobs 2                   # 変異を選ぶ
```

- 変異は `--work`（省略で一時ディレクトリ）の下に作った木の写し（`.git`・`__pycache__` を除く）に入れます。作業ツリーは変えません。
- `witness`・`full` は、まず元の木で同じテストを走らせ、すべて通ることを確かめます（結果の最初の行 `baseline`）。通らなければ、変異の結果を数えません。
- 1 つの変異の結果（JSON Lines）: `id`・`status`・`returncode`・`failing`（失敗したテストの id。subTest はまとめる）・`summary`・`seconds`。
- 状態:

| 状態 | 意味 | 見つけた数に入れるか |
|---|---|---|
| `not_applied` | 置きかえる前の文字列がちょうど 1 か所にない | 入れない（定義を直す） |
| `invalid` | 置きかえたあとがコンパイルできない・JSON として読めない | 入れない |
| `detected`（full） | どれかのテストが失敗した | 入れる |
| `survived`（full） | すべて通った | 見落とし |
| `witness_failed`（witness） | 証人のテストがすべて失敗した（狙った欠陥を起こした） | — |
| `witness_passed`（witness） | 証人のテストに通ったものがある | 狙った欠陥を起こしていない |

## 3. v0.18 の結果

v0.18 の最終のコード（v0.18c・v0.18d のコミットのあと、変異の定義と道具を加えた作業ツリー）で、2026-10-14 に実行しました（Python 3.13・4 コア。`--jobs 3`）。

| 実行 | 元の木 | 結果 |
|---|---|---|
| `python3 tools/run_mutants.py full --jobs 3` | 33 モジュール OK（200 秒） | 50 / 50 `detected`（`survived`・`invalid`・`not_applied` は 0）。失敗したテストの数は 1〜298（変異ごと）。1 つの変異で 51〜205 秒、合計 9,446 秒 |
| `python3 tools/run_mutants.py witness --jobs 3` | 証人のテスト 66 個 OK（82 秒） | 50 / 50 `witness_failed`（証人のテストがすべて失敗した） |
| `python3 tools/run_mutants.py check` | — | 50 件すべて `ok`（ちょうど 1 か所・構文として正しい。証人 1 個が 11 件、2 個が 39 件） |

- v0.17d の報告（46 / 46）は v0.17 のコードで走らせた結果で、ここに数えていません。この表は v0.18 のコードで走らせ直した結果です。
- 全体の実行の結果（失敗したテストの一覧つき）は、作業の外の記録（JSON Lines）にあり、リポジトリには入れていません。同じ結果は上のコマンドで作り直せます（乱数は seed から作るので、テストの結果は同じになる）。

| id | 変異 | 版 | 全体の実行 | 失敗したテスト | 証人のテスト（witness） |
|---|---|---|---|---|---|
| M01 | 枠の表に返す効果 → 返す効果を加える | v0.15d | detected | 3 | witness_failed: `test_kernel_integration_v0_15.MessageTest.test_refused_chain_names_the_assumption`, `test_shell_attack_v0_13.RemovalAndChainTest.test_chain_is_refused_even_in_a_broken_state` |
| M02 | 送る効果を処理したあと列を空にしない | v0.15d | detected | 51 | witness_failed: `test_contract_adapter_v0_16.WindowTest.test_effects_before_the_deferred_window_are_refused`, `test_counterattack_v0_10.AtomicityTest.test_internal_error_after_the_counter` |
| M03 | 自分のワザのダメージでも受けたときの効果 | v0.15d | detected | 3 | witness_failed: `test_counterattack_v0_10.SourceTest.test_own_attack_does_not_trigger`, `test_guts_v0_11.SourceTest.test_own_attack_self_damage_does_not_offer` |
| M04 | かがくへんかガスを見ない | v0.15d | detected | 19 | witness_failed: `test_counterattack_v0_10.CoinIndependenceTest.test_acceptance_does_not_depend_on_the_coins`, `test_counterattack_v0_10.GasTest.test_either_players_muk_suppresses` |
| M05 | 持続する効果のはたらく番を見ない | v0.15d | detected | 2 | witness_failed: `test_harden_v0_4b.RemovalTest.test_knock_out_by_self_damage_and_confusion`, `test_event_kernel_v0_14.SharedFilterTest.test_persistent_effect_works_only_on_its_turn` |
| M06 | 同時のきぜつの原因を確かめない | v0.15d | detected | 33 | witness_failed: `test_counterattack_v0_10.CoinIndependenceTest.test_acceptance_does_not_depend_on_the_coins`, `test_counterattack_v0_10.InvariantTest.test_double_knock_out_guard_after_the_preflight` |
| M07 | 先読み: コインのあとも試さない | v0.15d | detected | 33 | witness_failed: `test_counterattack_v0_10.CoinIndependenceTest.test_acceptance_does_not_depend_on_the_coins`, `test_counterattack_v0_10.KnockOutTest.test_unresolved_regardless_of_the_coins` |
| M08 | 先読み: 実際の処理の乱数をもどさない | v0.15d | detected | 15 | witness_failed: `test_alakazam_line_v0_7.KadabraRecoverTest.test_pending_decision_survives_copies`, `test_counterattack_v0_10.SaveRestoreTest.test_restored_decision_resumes_after_the_counter` |
| M09 | 先読み: 最後のコインの逆を試さない | v0.15d | detected | 23 | witness_failed: `test_counterattack_v0_10.CoinIndependenceTest.test_acceptance_does_not_depend_on_the_coins`, `test_counterattack_v0_10.KnockOutTest.test_unresolved_regardless_of_the_coins` |
| M10 | エナジーへんかんの答えを代表だけにもどす | v0.15d | detected | 5 | witness_failed: `test_preflight_consolidation_v0_16c.ProductBoundTest.test_recover_energy_on_a_legal_board_stays_below_the_limit`, `test_preflight_consolidation_v0_16c.ProductBoundTest.test_recover_energy_reaches_the_limit_only_on_an_impossible_board` |
| M11 | 答えの順番を試さない | v0.15d | detected | 5 | witness_failed: `test_preflight_consolidation_v0_16c.BranchLimitBoundaryTest.test_derived_and_derived_full_agree_at_every_count`, `test_preflight_consolidation_v0_16c.ProductBoundTest.test_recover_energy_on_a_legal_board_stays_below_the_limit` |
| M12 | 対応表の型の部分型を親の型の並びで処理する | v0.15d | detected | 3 | witness_failed: `test_contract_adapter_v0_16.BuiltinTest.test_subclass_without_resolve_uses_the_parent_program`, `test_contract_adapter_v0_16.SelectionTest.test_which_implementations_use_the_adapter` |
| M13 | きぜつの順番を逆にする | v0.15d | detected | 9 | witness_failed: `test_guts_v0_11.KnockOutAndPrizeTest.test_attacker_is_also_knocked_out`, `test_simultaneous_ko.BothKnockedOutTest.test_full_sequence` |
| M14 | 上限の境目を 1 つずらす | v0.15d | detected | 4 | witness_failed: `test_preflight_consolidation_v0_16c.BranchLimitBoundaryTest.test_derived_and_derived_full_agree_at_every_count`, `test_preflight_consolidation_v0_16c.BranchLimitBoundaryTest.test_v0_15c_off_by_one_is_fixed` |
| M15 | 上限を超えても受け付ける | v0.15d | detected | 5 | witness_failed: `test_preflight_consolidation_v0_16c.BranchLimitBoundaryTest.test_derived_and_derived_full_agree_at_every_count`, `test_preflight_consolidation_v0_16c.BranchLimitBoundaryTest.test_v0_15c_off_by_one_is_fixed` |
| M16 | ダメージを受けない状態を見ない | v0.15d | detected | 23 | witness_failed: `test_counterattack_v0_10.DirectTest.test_damage_not_received_does_not_trigger`, `test_damage_drain_v0_4d.DamageResultTest.test_prevented_is_not_calculated` |
| M17 | 解決の記録で結果を決める | v0.15d | detected | 1 | witness_failed: `test_kernel_invariants_v0_15.KernelInvariantGameTest.test_invariants_in_natural_games` |
| M18 | 理由の文の返す量を変える | v0.15d | detected | 3 | witness_failed: `test_kernel_integration_v0_15.MessageTest.test_stop_messages_are_the_same_on_both_routes`, `test_preflight_v0_15c.EquivalenceTest.test_derived_matches_derived_full_and_the_v0_13_route` |
| M19 | 複製でなく渡された状態を変える | v0.15d | detected | 298 | witness_failed: `test_pokemon_powers_v0_5.AtomicityTest.test_apply_command_does_not_change_the_given_state`, `test_counterattack_v0_10.AtomicityTest.test_accepted_command_does_not_change_the_input` |
| M20 | こんじょうの決定への答えを解決の基盤に送らない | v0.15d | detected | 26 | witness_failed: `test_guts_v0_11.ConditionAndGasTest.test_poisoned_can_use`, `test_guts_v0_11.DecisionTest.test_answering_is_deterministic` |
| R01 | 処理できない実装を効果のないワザにする | v0.16e | detected | 2 | witness_failed: `test_contract_adapter_v0_16.SelectionTest.test_unprocessable_implementation_is_refused_before_anything`, `test_contract_adapter_v0_16.SelectionTest.test_which_implementations_use_the_adapter` |
| R02 | v0.13 の約束の実装を先読み derived で複製の上でも処理する | v0.16e | detected | 18 | witness_failed: `test_contract_adapter_v0_16.DecisionTest.test_two_step_decisions_with_save_and_restore`, `test_contract_adapter_v0_16.PreflightTest.test_problem_stops_before_the_declaration` |
| R03 | アダプタが別の状態を受け付ける | v0.16e | detected | 1 | witness_failed: `test_contract_adapter_v0_16.WindowTest.test_a_different_state_is_refused` |
| R04 | 答えのあとにもう一度出した決定で止まらない | v0.16e | detected | 12 | witness_failed: `test_contract_adapter_v0_16.DecisionTest.test_two_step_decisions_with_save_and_restore`, `test_decision_integrity_v0_4e.DecisionCopyTest.test_copies_at_every_decision` |
| R05 | アダプタの宣言の前の確認で実装の problem を聞かない | v0.16e | detected | 3 | witness_failed: `test_contract_adapter_v0_16.PreflightTest.test_problem_stops_before_the_declaration`, `test_contract_adapter_v0_16.PreflightTest.test_resolve_once_and_contract_checks_whatever_the_preflight_mode` |
| R06 | 先読み siblings の上限で実際の処理を数えない（v0.15c にもどす） | v0.16e | detected | 2 | witness_failed: `test_preflight_consolidation_v0_16c.BranchLimitBoundaryTest.test_derived_and_derived_full_agree_at_every_count`, `test_preflight_consolidation_v0_16c.BranchLimitBoundaryTest.test_v0_15c_off_by_one_is_fixed` |
| R07 | WRONG_PHASE の段階の並びを集合の並びにもどす | v0.16e | detected | 2 | witness_failed: `test_wrong_phase_message_v0_16d.WrongPhaseMessageTest.test_message_uses_the_phase_definition_order` |
| R08 | AttackUse の比較に枠への入口を含める | v0.16e | detected | 2 | witness_failed: `test_counterattack_v0_10.DirectTest.test_memo_is_not_state`, `test_transparency_v0_9.DirectReceptionTest.test_attack_use_memo_is_not_state` |
| R09 | 補助関数 finish_damage_elements が何もしない | v0.16e | detected | 7 | witness_failed: `test_contract_adapter_v0_16.OutsideFrameTest.test_helpers_need_the_kernel_frame`, `test_contract_adapter_v0_16.WindowTest.test_effects_before_the_deferred_window_are_refused` |
| R10 | トレーナーの決定への答えを解決の基盤に送る | v0.16e | detected | 41 | witness_failed: `test_chemical_gas_v0_8.TransitionTest.test_switch_and_retreat_bring_the_gas_back`, `test_damage_drain_v0_4d.MegaDrainTest.test_dealt_damage_table` |
| R11 | メガドレインが与えていないダメージでも回復する | v0.16e | detected | 3 | witness_failed: `test_damage_drain_v0_4d.MegaDrainTest.test_no_damage_dealt_no_heal`, `test_damage_drain_v0_4d.MegaDrainTest.test_prevented_damage_no_heal` |
| R12 | 同時のきぜつの印をつけない | v0.16e | detected | 7 | witness_failed: `test_counterattack_v0_10.OrderTest.test_attacker_already_knocked_out_by_its_own_damage`, `test_guts_v0_11.KnockOutAndPrizeTest.test_attacker_is_also_knocked_out` |
| R13 | 補助関数が枠の外でも何もせずに進む | v0.16e | detected | 1 | witness_failed: `test_contract_adapter_v0_16.OutsideFrameTest.test_helpers_need_the_kernel_frame` |
| R14 | v0.13 の止める関数の上限の型を製品のすべてに広げる | v0.16e | detected | 1 | witness_failed: `test_preflight_v0_15c.LimitTest.test_verified_implementations_are_the_v0_13_ones` |
| S01 | ねむりでない状態でも発動する | v0.17d | detected | 8 | witness_failed: `test_rocket_snorlax_v0_17b.RegistrationTest.test_catalog_and_implementation_agree`, `test_rocket_snorlax_v0_17b.RestlessSleepTest.test_double_knock_out_stops_before_the_attack` |
| S02 | ねむり状態で発動しない（通常の特殊状態の抑止をそのまま当てはめる） | v0.17d | detected | 17 | witness_failed: `test_rocket_snorlax_v0_17b.RegistrationTest.test_card_and_registration`, `test_rocket_snorlax_v0_17b.RegistrationTest.test_catalog_and_implementation_agree` |
| S03 | かがくへんかガスを無視する | v0.17d | detected | 2 | witness_failed: `test_rocket_snorlax_v0_17b.RestlessSleepTest.test_chemical_gas` |
| S04 | ダメージを受けていないのに発動する | v0.17d | detected | 16 | witness_failed: `test_rocket_snorlax_v0_17b.RestlessSleepTest.test_zero_or_prevented_damage_does_not_trigger` |
| S05 | きぜつした場合に効果を消してしまう | v0.17d | detected | 36 | witness_failed: `test_rocket_snorlax_v0_17b.RestlessSleepTest.test_double_knock_out_stops_before_the_attack`, `test_rocket_snorlax_v0_17b.RestlessSleepTest.test_knocked_out_snorlax_still_returns` |
| S06 | 不正なダメージ分類（特殊能力のダメージをワザの分類の枠で処理する） | v0.17d | detected | 30 | witness_failed: `test_rocket_snorlax_v0_17b.RestlessSleepTest.test_double_knock_out_stops_before_the_attack`, `test_rocket_snorlax_v0_17b.TumbleTest.test_counterattack_comes_before_self_sleep` |
| S07 | 処理窓を誤る（受けた直後に処理する） | v0.17d | detected | 18 | witness_failed: `test_rocket_snorlax_v0_17b.RestlessSleepTest.test_attacker_already_knocked_out_by_its_own_damage`, `test_contract_adapter_v0_16.WindowTest.test_effects_before_the_deferred_window_are_refused` |
| S08 | 同じ効果を二重に発動する | v0.17d | detected | 87 | witness_failed: `test_rocket_snorlax_v0_17b.RestlessSleepTest.test_asleep_snorlax_returns_20`, `test_rocket_snorlax_v0_17b.RestlessSleepTest.test_attacker_already_knocked_out_by_its_own_damage` |
| S09 | 未解決を勝手に解決する（Z23: ダメージを与えなくても自分をねむりにする） | v0.17d | detected | 16 | witness_failed: `test_rocket_snorlax_v0_17b.TumbleTest.test_no_damage_stops_before_the_attack`, `test_rocket_snorlax_v0_17b.TumbleTest.test_no_damage_stops_in_every_preflight_mode` |
| S10 | 未解決を勝手に解決する（Z9: 弱点・抵抗力を計算しないで進む） | v0.17d | detected | 1 | witness_failed: `test_rocket_snorlax_v0_17b.RestlessSleepTest.test_weakness_resistance_guard` |
| S12 | 比べる方法 legacy で VERIFIED にない型も v0.13 の止める関数で確かめる | v0.17d | detected | 1 | witness_failed: `test_rocket_snorlax_v0_17b.TumbleTest.test_no_damage_stops_in_every_preflight_mode` |
| S11 | 未解決を勝手に解決する（C18: わるいねぞうのそろってのきぜつを止めない） | v0.17d | detected | 4 | witness_failed: `test_rocket_snorlax_v0_17b.RestlessSleepTest.test_double_knock_out_stops_before_the_attack` |
| V01 | Z23 の理由の文で場合を取り違える（要素が無効と最終ダメージが 0） | v0.18e | detected | 6 | witness_failed: `test_unresolved_research_v0_18b.EffectAfterNoDamageSubcaseTest.test_z23_a_prevented_element`, `test_unresolved_research_v0_18b.EffectAfterNoDamageSubcaseTest.test_z23_b_zero_by_defender` |
| V02 | 送る効果が残っていてもワザの途中の決定を出す（窓の途中で黙って止まる） | v0.18e | detected | 2 | witness_failed: `test_mid_window_decisions_v0_18d.DesignAssumptionTest.test_suspend_refuses_pending_effects`, `test_counterattack_v0_10.DirectTest.test_effects_and_decisions_need_the_counter_first` |
| V03 | 研究の対応表から停止コードを 1 つ落とす（Z23 の停止コードの名前を誤る） | v0.18e | detected | 2 | witness_failed: `test_research_links_v0_18e.ResearchLinksTest.test_every_question_is_linked_to_its_rulings`, `test_research_links_v0_18e.ResearchLinksTest.test_every_stop_code_is_linked` |
| V04 | 「ダメージを与えた後」の効果の前にワザのコインを置く（Z23-d が起こりうる形にする） | v0.18e | detected | 35 | witness_failed: `test_unresolved_research_v0_18b.TargetGoneIsUnreachableTest.test_after_damage_effects_follow_an_unconditional_first_damage_element` |


## 4. 移した変異と移していない変異

移した（`tools/mutants.py` にあり、v0.18 の最終のコードで走らせた）:

| 版 | id | 数 | 元の定義 |
|---|---|---|---|
| v0.15d（v0.16e で今のコードに合わせた） | M01〜M20 | 20 | v0.16e・v0.17d の作業の外の道具（docs/kernel-consolidation-verification-v0.16e.md 5 章・docs/card-extensibility-verification-v0.17d.md 5 章） |
| v0.16e | R01〜R14 | 14 | 同上 |
| v0.17d | S01〜S12 | 12 | docs/card-extensibility-verification-v0.17d.md 5 章 |
| v0.18e | V01〜V04 | 4 | この文書 1 章 |

移していない（定義がリポジトリになく、文書に書いた内容だけが残る。v0.18 では走らせていない）:

| 版 | 文書 | 文書に書いた数 | 移していない理由 |
|---|---|---|---|
| v0.3c〜v0.3d | docs/confusion-v0.3c.md 8 章・docs/special-conditions-audit-v0.3d.md 11 章 | 0・17 件 | 定義の文字列が文書にない（変異の内容の説明だけ）。v0.16b で外した旧経路の関数を対象にしたものがある |
| v0.4a〜v0.4e | docs/evolution-state-v0.4a.md 11 章・docs/harden-v0.4b.md 11 章・docs/stage2-state-v0.4c.md 13 章・docs/architecture-v0.4d.md 12 章・docs/integration-audit-v0.4e.md 11 章 | 文書ごとに 0〜24 | 同上 |
| v0.5〜v0.13 | docs/v0.5-verification.md〜docs/v0.13-verification.md の 4 章 | 26〜42 個（版ごと） | 同上。多くは v0.13 の経路（`engine._finish_attack`・`effects._apply_counterattack` など。v0.16b で外した）を対象にしていて、今のコードには同じ場所がない |
| v0.14 | docs/event-prototype-verification-v0.14.md 8 章 | M01〜M27 | プロトタイプ（`experiments/event_kernel`。v0.16d で外した）が対象 |
| v0.15d（元の形） | docs/event-integration-verification-v0.15d.md 5 章 | M01〜M20 | v0.16e で今のコードに合わせた形を移した（上の表） |

- 移していない変異を、v0.18 で「通った（見つけた）」とは数えていません。
- 移すときは、同じ欠陥を今のコード（解決の基盤）の場所に入れる定義を書き、証人のテストを選んでから `tools/mutants.py` に加えます。v0.13 の経路にしかない欠陥（外した関数の誤り）は、今のコードでは起こらないので移しません。

## 5. 研究の対応の追跡

| 道具 | 確かめること | いつ走らせるか |
|---|---|---|
| `kyuura_engine/data/research_links.json` | 研究の基準のコミット・停止コード 18 件と論点・コードのない問い・起こらない未解決・延期したカードの問い・実装上の仮定・Z23 の場合・分類の違い 17 件・最新の説明（登録 20 件の LD- の id、kyuura に記録のない 34 件、登録のない kyuura の記録 5 件）・照合の記録（CC- 28 件、kyuura に記録のない 34 枚）・カードデータの違い | — |
| tests/test_research_links_v0_18e.py | エンジンの停止コード・問い・最新の説明のある登録・照合の記録の集合が、対応表と同じ。エンジンの裁定 id が文書にある。数（24・18・19） | ふだんのテスト（A 段階） |
| `scripts/check_research_links.py --kyuura ../kyuura` | 論点がすべてあり UNRESOLVED・kyuura の論点がすべて対応表にある・エンジンの未解決の一覧が同じ・分類の違いの記録・最新の説明の文面とページ・照合の記録・カードデータの違い | ../kyuura があるとき（テストからも呼ぶ） |

- kyuura の記録（文面・根拠・分類）を写していません。対応表は id と、照らした結果の違い（`card_data_differences`）だけです。
- kyuura が研究を進めたら（論点が解決した・分類が変わった・新しい記録）、研究の基準のコミットを上げ、スクリプトの違いを 1 つずつ docs に書いてから、エンジンの処理を見直します。
- 停止コード・問い・登録・照合の記録をエンジンに加えたのに対応表を直さないと、A 段階のテストが失敗します（変異 V03 で確かめた）。

## 6. 残る課題

- 証人のテストは 1 つの変異につき 1〜3 個で、変異のすべての影響を表すものではありません（全体の実行で見つけたテストの一覧は、結果の JSON Lines にある）。
- v0.13 の経路を対象にした古い変異（4 章）は移していません。
- 変異の全体の実行は 1 つの変異で数分かかり、ふだんのテストに入れていません。
