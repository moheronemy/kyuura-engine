# 旧経路の撤去の監査（v0.16a）

v0.15d で標準の経路になった解決の基盤（`kyuura_engine/resolution`。以下 KERNEL）を、ワザの解決の唯一の基盤にするために、v0.13 の経路（以下「旧経路」）が今も担っている責務を、実際の参照から調べた記録です。この段階では旧経路を消していません（分析と比較の環境の準備だけ）。

- 調べたのは移行元のコミット `aa551ab`（v0.15.0。ブランチ `claude/v0.15-event-kernel-integration`）です。比べる基準は v0.15（`aa551ab`）と v0.13（`8facf3a`）の 2 つです。
- 「確認した事実」は実際の参照・実行の結果、「評価」「方針」はその解釈と判断です。
- 移行の範囲は v0.14 の判断（PARTIAL）のままです。ワザの宣言・効果・ダメージ・ダメージを受けたときの自動の効果・きぜつの判定と処理・サイドと交代・ワザの途中の決定と再開・番の終わり・持続する効果の期限を KERNEL にまとめます。トレーナー・宣言する特殊能力・進化・にげる・エネルギーをつける・対戦準備は範囲の外です（[event-migration-plan-v0.14.md](event-migration-plan-v0.14.md)）。

## 0. 要約

| 問い | 答え（確認した事実） |
|---|---|
| 旧経路の関数を範囲外のコマンドが呼ぶか | 呼ばない。旧経路の 24 の関数と経路の 3 つの名前（`engine.py` 約 490 行）は、ワザ・番の終わり・決定への答え（再開先 `attack`・`knock_out`・`post_knockout`・`take_prize`・`promote_active`）からだけ呼ばれる（2 章） |
| KERNEL は旧経路の部品を使うか | 処理では使わない（`deal_attack_damage`・`attack_reaches`・`finish_damage_elements`・`_apply_*` を呼ばない）。使うのは宣言の前の先読みの 2 か所だけ: 方法 `legacy`（比べるため）と、試す結果の数が上限を超えたときの `LEGACY_VERIFIED` の確かめ（v0.13 の止める関数 5 つ。3.3 節） |
| 旧経路に頼っているものは何か | (1) 対応表 `programs.BUILDERS` にないワザの実装（テスト専用の 21 種類のうち 19 種類。`resolution.handles` が旧経路に回す）、(2) 旧経路の内部関数を直接使うテスト（16 ファイル。経路を選ぶテストを合わせて 19 ファイル）、(3) 経路を選ぶテスト・道具（`Route`・`apply_command_via`）、(4) 比較の道具 `tools/event_kernel_compare.py`（同じ木の中で旧経路と比べる） |
| テスト専用のワザ | 21 種類（`AttackEffect` の部分型）。19 種類は v0.13 の約束（`resolve`・`resume`）で書かれ、旧経路で処理されている。決定を出すもの 2 種類（`TwoStepTestEffect`・`AttackerThenOpponentTestEffect`。2 段階・相手が決定する段階を含む）。標準の実装の部分型で `super().resolve` を呼ぶもの 2 種類（6 章） |
| 採用する方式 | **v0.13 の約束のワザを KERNEL の枠の中で処理する明示的なアダプタ**（7 章）。補助関数（`deal_attack_damage` など）は KERNEL の部品に委ねる薄い入口にし、ダメージ・自動の効果・きぜつの判定はすべて KERNEL の窓を通る。対応表にもなく、v0.13 の約束でも処理できない実装は、状態を変える前に `UNSUPPORTED_ATTACK` で拒否する |
| 宣言の前の判定（v0.13 の止める関数） | 消せない。アダプタで処理するワザの宣言の前の確認（v0.13 の約束どおり）と、上限を超えたときの確かめの 2 つが使う。v0.16c で、旧経路から独立した限定的なモジュールとして残すかを比べて決める |
| 比較の環境 | 固定した v0.13・v0.15 の木を `git archive` で展開し（`tools/engine_lockstep.py tree`）、別のプロセスで公開の `apply_command` だけを使って比べる。旧経路を消したあとも比べられる（8 章。小さな規模で 3 つの木が一致することを確かめた） |

## 1. 方法

- 参照の数え方: 名前ごとに、`kyuura_engine/`・`resolution/`・`experiments/`・`tests/`・`tools/` の `.py` で、定義の行（`def`・`class`）を除いた参照を数えました。コメント・文字列（説明）だけの参照は「説明」として分けています。数えた道具は作業用の小さなスクリプト（リポジトリには入れていない）で、数えた木は `aa551ab` です。
- 分類（A〜F）は、その名前を使っているコード（説明ではなく）から決めました。名前が古いことは分類の理由にしていません。

| 分類 | 意味 |
|---|---|
| A | KERNEL が今も必要とする（KERNEL の処理・不変条件が使う） |
| B | 範囲外の処理（トレーナー・宣言する特殊能力・進化・にげるなど）が必要とする |
| C | テストだけが使う |
| D | 比較の道具だけが使う |
| E | 旧経路だけが使う |
| F | 外から使える拡張の約束（効果の実装を加える人向け。[api-review.md](api-review.md) 3 章で「公開（実装を加える人向け）」とした `AttackEffect`・`AttackEntry`・`AttackUse` と各実装） |

## 2. 旧経路の構造と呼び出し元（確認した事実）

旧経路は `engine.py` の次の 24 の関数と、経路の 3 つの名前です。どれも、ワザ（`UseAttack`）・番の終わり（`EndTurn`）・決定への答え（`ResolveDecision`・`TakePrize`・`PromoteActive`）の処理からだけ呼ばれています（`engine.py` の中の参照をすべて確かめた。範囲外のコマンドの処理（`_play_trainer`・`_use_pokemon_power`・`_evolve_pokemon`・`_retreat`・`_attach_energy`・対戦準備）からの呼び出しはない）。

| 種類 | 関数 |
|---|---|
| ワザ | `_use_attack`（確認 → 止める関数 5 つ → 宣言 → こんらん → `effect.resolve` → `finish_damage_elements` → `_finish_attack`）・`_resume_attack` |
| きぜつの判定・処理 | `_finish_attack`・`_ko_prevention_offer`・`_resume_knock_out`・`_knock_out_after_attack`・`_post_knockout_candidates` |
| きぜつのあと | `_after_knockouts`・`_then_context`・`_post_knockout_context`・`_next_prize_or_judge`・`_promotions_after_judge`・`_offer_post_knockout`・`_resume_post_knockout`・`_next_promotion_or_end`・`_resume_take_prize`・`_resume_promote_active` |
| 番の終わり | `_end_turn_command`・`_end_turn`・`_pokemon_check` |
| 決定への答え | `_resolve`・`_resolve_decision`・`_take_prize`・`_promote_active`、表 `_RESUMERS`（6 つのうち `trainer` だけが範囲外の処理 `_resume_trainer`） |
| 経路 | `Route`・`DEFAULT_ROUTE`・`apply_command_via`（と `_apply` の振り分け） |

- 共通の手続き（`procedures.py`: `begin_turn`・`expire_at_turn_end`・`pokemon_check_poison`・`pokemon_check_sleep_and_paralysis`・`knock_out`・`finish`・`confusion_*`）と確認（`checks.py`）は v0.15a で両方の経路が使う部品にしました。KERNEL も使うので残します（A）。
- `_RESUMERS["trainer"]`（`_resume_trainer`）は範囲外のトレーナーの決定で、残します（B）。旧経路を消したあと、決定への答えは「`checks.decision_choices` で確かめる → 再開先が KERNEL の 5 つなら KERNEL、`trainer` なら `_resume_trainer`」に振り分けます（v0.15 と同じ確認・同じ順番。今の `_resolve_decision`・`_take_prize`・`_promote_active` の確認は `checks.decision_choices` と同じ関数）。
- 不変条件（`check_invariants`）は旧経路の関数を呼びません。ただし `effects` の問い合わせ（`ko_prevention_power`・`ko_prevention_suppressors`・`post_knockout_power`・`AttackEffect.decision_problems`・`retaliation_terms`）を使うので、それらは残します（A。KERNEL の結果を確かめるため）。

## 3. 参照の分類（確認した事実と分類）

参照の数は「コードの参照の数（ファイル）」です。説明だけの参照は数に入れていません。

### 3.1 経路・入口

| 名前 | 参照 | 分類 | 根拠 | v0.16 の方針 |
|---|---|---|---|---|
| `Route.LEGACY`・`Route` | engine 6・resolution 2（説明）・experiments 2・tests 16（4 ファイル）・tools 4（2 ファイル） | E・C・D | 公開の `apply_command` は `DEFAULT_ROUTE`（KERNEL）だけを使う。`LEGACY` を選ぶのはテスト（旧経路の内部を差しかえるテスト・経路の比較）と道具（`event_kernel_compare`・`engine_lockstep --route`）だけ | v0.16b で外す。テストと道具は 9 章のとおり移す |
| `DEFAULT_ROUTE` | engine 4・tests 2・tools 1 | E・C・D | 経路が 1 つになれば意味がない | v0.16b で外す |
| `apply_command_via` | engine 1・experiments 3・tests 14（4 ファイル）・tools 4（2 ファイル） | C・D | 先読みの方法・効果の定義の対応表をテストで選ぶ入口も兼ねている | 経路の引数のない内部の入口（先読みの方法・対応表を選ぶ）に置きかえる。解決の記録の入口 `apply_command_traced` は残す |
| `resolution.handles` | engine 2・experiments 2・tests 11（2 ファイル） | E・C | 受け持たないコマンドを旧経路に回すための判定。旧経路を消せば、ワザは「対応表の要素の並び」か「アダプタ」で必ず KERNEL が処理する | v0.16b で外す（決定の振り分けは 2 章のとおり） |
| `resolution.PREFLIGHT_MODES` | engine 1・resolution 6・experiments 1・tests 7（2 ファイル） | A・C | 先読みの方法（`derived`・`derived_full`・`legacy`）。経路とは別のもの | 残す（v0.16c で `legacy` の扱いを決める） |
| `LEGACY_VERIFIED` | resolution 3・tests 4（1 ファイル） | A | 上限を超えたときに v0.13 の止める関数で確かめてよい 24 種類 | v0.16c で決める（→ `resolution/v013_checks.py` の `VERIFIED` に移して残した。[preflight-consolidation-v0.16c.md](preflight-consolidation-v0.16c.md)） |

### 3.2 旧ダメージ処理境界（`effects.py`）

| 名前 | 参照 | 分類 | 根拠 | v0.16 の方針 |
|---|---|---|---|---|
| `AttackEffect.resolve`・`resume`（24 の実装） | engine 2（`_use_attack`・`_resume_attack`）・tests（テスト専用の 19 種類が上書き、`super().resolve` 2 か所、直接呼ぶ 1 か所） | E・C・F | KERNEL は対応表の型の `resolve` を呼ばない（要素の並びで処理する。tests/test_preflight_v0_15c.py の `TestOnlyAttack` は `resolve` が `AssertionError` を投げるが、KERNEL で処理できる）。v0.13 の約束で書いたテスト専用の実装は旧経路で `resolve` が呼ばれる | 24 の実装の `resolve`・`resume`（約 470 行）は v0.16b で外す。`AttackEffect` の既定の `resolve`・`resume` は「最も近い対応表の型の要素の並びを、今の枠で処理する」にする（部分型の `super().resolve` のため。7 章）。クラスの定義（`check`・`problem`・`damage_profile` など）は消さない |
| `AttackUse` | decisions 4・effects 89・engine 8・resolution 5・tests 26（8 ファイル） | A・F | KERNEL の入口（`flow._use_attack`）・不変条件（`_attack_decision_problems` が `decision_problems` に渡す）・先読み `legacy` が使う | 残す。旧経路の記録の項目（`reception`・`counterattacks`・`ko_prevention_able`・`retaliations`）は KERNEL の枠が持つので、`reception`・`ko_prevention_able` は枠を読む項目に、`counterattacks`・`retaliations` は外す（7.3 節） |
| `deal_attack_damage`・`damage_opponent_active` | effects 46・engine 1（説明）・procedures 1（説明）・tests 36（9 ファイル） | E・C・F | KERNEL は `kernel.deal_damage`（同じ結果・ログ・乱数）を使う。旧経路の 24 の `resolve` とテスト専用の実装・単体テストが呼ぶ | 実装（約 130 行）を外し、KERNEL の `deal_damage` に委ねる薄い入口にする（枠の外で呼ぶと `RuntimeError`） |
| `attack_reaches` | effects 18・tests 16（3 ファイル） | E・C・F | KERNEL は `kernel.reaches` | 同じく `kernel.reaches` に委ねる入口にする |
| `finish_damage_elements` | effects 23・engine 5・tests 6（2 ファイル） | E・C・F | KERNEL は `kernel.fire_pending`（窓を開く位置は `run_elements` が決める） | `kernel.fire_pending` に委ねる入口にする |
| `push_attack_decision`（decisions） | effects 6・tests 10（4 ファイル） | E・C・F | KERNEL は `AttackRun.suspend`（同じ決定の形。`codec.attack_decision`） | `AttackRun.suspend` に委ねる入口にする |
| `_apply_counterattack`・`_apply_retaliation`・`retaliation_use`・`PendingCounterattack`・`PendingRetaliation`・`_require_damage_elements_finished` | effects だけ（tests: `PendingCounterattack` 3） | E・C | KERNEL は `kernel.power_damage_to_damage_source`・`attack_damage_to_damage_source`・`Deferred` | v0.16b で外す（約 210 行） |
| `_skip_heal_of_knocked_out_attacker`・`_remove_attacker_counters` | effects だけ（tests: `_remove_attacker_counters` の差しかえ 1） | E | 24 の `resolve` だけが使う。KERNEL は `programs.Drain`（同じ結果・ログ） | `resolve` といっしょに外す。v0.16d の「ダメージに応じた回復」の重複は、このとき重複でなくなる |
| `_check_damage_then_effect` | effects だけ | A（v0.16b で訂正） | v0.16a では E と分類したが、実際は登録の照合（5 つの実装の `check`）が使う（v0.16b で消した写しで見つかった。docs/kernel-consolidation-v0.16b.md 1 章） | 残す |
| `damage_profile`・`DamageProfile` | effects 33・tests 22（6 ファイル） | A・C・F | 先読み `legacy`・上限を超えたときの確かめ（C18・W24・G37 の止める関数）が使う | 残す（v0.16c） |
| `opponent_effect_elements` | effects 14・resolution 2・tests 5（2 ファイル） | A・C・F | G37 の止める関数（`legacy`）が使う。KERNEL は要素の並びから求める（`programs.opponent_effect_elements`） | 残す（v0.16c） |
| `preview_attack_damage`・`damage_receiver` | effects だけ | A | 止める関数（C18・W24・G37・T19b）が使う | 残す（v0.16c） |
| `counterattack_double_knockout_problem`・`ko_prevention_attack_effect_problem`・`retaliation_double_knockout_problem` | engine 8・resolution 6（`preflight.legacy`）・tests 1 | A・E | 旧経路の `_use_attack` と先読みの `legacy`（比べる・上限を超えたとき） | 残す（v0.16c で置き場所を決める → `resolution/v013_checks.py` だけが使う）。理由の文の関数（`…_error`）は両方が使う（A） |
| `prevented_coin_damage_problem`・`evaded_effect_coin_problem` | effects だけ（`CoinFlipDamage.problem` などの実装の `problem`） | A | 上の止める関数と同じ | 残す |
| `evasion_power`・`counterattack_power`・`ko_prevention_power`・`post_knockout_power`・`ko_prevention_suppressors` | effects・engine（不変条件）・resolution（説明）・tests | A・B | 不変条件・公開の問い合わせ（`working_evasion_power` など）・止める関数が使う。KERNEL の対応表（`catalog`）は効果の型で探すので、これらを呼ばない | 残す |
| `DamageResult` | effects 10・resolution 5・tests 4 | A | `kernel.deal_damage` が返す | 残す |
| `decision_problems`・`retaliation_terms` | engine（不変条件）・effects・tests | A・F | 決定と持続する効果の不変条件 | 残す |

### 3.3 先読みが使う旧方式の判定

| 使う所 | 中身 | 分類 |
|---|---|---|
| `preflight.legacy`（方法 `legacy`） | v0.13 の `_use_attack` と同じ順番で、`effect.problem` → `procedures.confusion_damage_problem` → C18 → G37 → W24 | C・D（比べるため。`event_kernel_compare` とテスト） |
| `flow._use_attack` の `on_limit` | 試す結果の数が `MAX_BRANCHES`（4,096）を超えたとき、型が `LEGACY_VERIFIED` なら上の 5 つで確かめ、ほかは `UNSUPPORTED_PREFLIGHT_LIMIT` | A |

上限を超える盤面は、今の対応カードでも起こりえます（例: エナジーへんかんで、トラッシュのエネルギーカードが多いとき。答えの数は枚数の 2 乗ほどに増え、こんらんのコインで 2 倍になる）。上限を超えたときに一律に拒否すると、v0.13・v0.15 が受け付けていたワザを拒否するようになるので、v0.16c で慎重に比べます。

## 4. 範囲外の処理への影響（確認した事実）

- トレーナー（`_play_trainer`・`_resume_trainer`・`_finish_trainer`）・宣言する特殊能力（`_use_pokemon_power`）・進化・にげる・エネルギー・対戦準備は、旧経路の関数を呼びません。`TrainerEffect.resolve`・`PowerEffect.resolve` は範囲外の処理の実装なので残します（B。今回の撤去の対象は `AttackEffect` の 24 の実装の `resolve`・`resume` だけ）。
- KERNEL が呼ぶ特殊能力の実装のメソッド（`PreventKnockOutOnHeads.prevent`・`ReturnToHandOnKnockOut.recover`。`flow.OFFER_ACTIONS`）は残します（A）。
- 番の始まり（`procedures.begin_turn`）は対戦準備（`_report_janken_result`）とポケモンチェックの最後の両方が使います（A・B）。

## 5. 旧経路の内部に依存するテスト（確認した事実）

v0.14 の報告（テストモジュール 14 個と `tests/helpers.py`、約 105 か所）から、v0.15 で経路を選ぶテストが増えました。今のコードで数え直した結果です（コードの行の数。説明だけの行は除く）。

| 依存の種類 | ファイル | 行 | 内訳 |
|---|---|---|---|
| 経路を選ぶ（`Route`・`apply_command_via`・`apply_legacy`・`apply_kernel`・`handles`） | 7 | 91 | test_kernel_integration_v0_15（42）・test_preflight_v0_15c（21）・helpers（9）・test_counterattack_v0_10（6）・test_event_kernel_v0_14（5）・test_kernel_invariants_v0_15（4）・test_transparency_v0_9（4） |
| 旧ダメージ処理境界の関数を直接呼ぶ（`deal_attack_damage`・`attack_reaches`・`finish_damage_elements`・`push_attack_decision`・`PendingCounterattack` など） | 11 | 72 | test_counterattack_v0_10（22）・test_transparency_v0_9（14）・test_damage_drain_v0_4d（7）・test_shell_attack_v0_13（7）・test_guts_v0_11（5）・test_self_damage（4）・helpers（3）・test_damage_result_audit_v0_4e（3）・test_decision_integrity_v0_4e（3）・test_phoenix_v0_12（2）・test_rocket_moltres_v0_12（2） |
| `engine.py` の旧経路の内部関数を直接呼ぶ | 4 | 12 | test_guts_v0_11（`_ko_prevention_offer`。4）・test_phoenix_v0_12（`_post_knockout_candidates`。4）・test_combat（`_after_knockouts`。2）・test_simultaneous_ko（`_next_prize_or_judge`。1）、と import の行 |
| `AttackUse` を直接作る | 8 | 15 | 単体テストが旧ダメージ処理境界・止める関数・`damage_profile` に渡す |
| 実装の `resolve` を直接呼ぶ・`super().resolve` | 3 | 3 | test_alakazam_line_v0_7（じこさいせいの `resolve` を直接）・test_effect_preflight_v0_3d（`Spy`）・test_kernel_integration_v0_15（`SubclassedDamage`） |
| 旧経路の内部関数を差しかえる（`mock.patch`） | 2 | 8 | test_counterattack_v0_10（5。`effects._remove_attacker_counters`・`effects.push_attack_decision`・`effects.poison`・`GameState.add_event`・`engine.counterattack_double_knockout_problem`）・test_transparency_v0_9（3。`effects.put_to_sleep`・`effects.push_attack_decision`・`add_event`） |
| 宣言の前の判定を直接呼ぶ（`damage_profile`・`DamageProfile`・止める関数。残すもの） | 7 | 35 | test_guts_v0_11（8）・test_shell_attack_v0_13（7）・test_counterattack_v0_10（5）・test_giovanni_machamp_line_v0_11（5）・test_machamp_line_v0_10（5）・test_rocket_moltres_v0_12（3）・test_kernel_integration_v0_15（2） |
| experiments の互換の層（`experiments.event_kernel`） | 3 | 17 | test_event_kernel_v0_14（13）・test_event_kernel_games_v0_14（2）・test_kernel_integration_v0_15（2） |

- 旧経路そのものに依存するテスト（上の表の 2〜6 行目。`AttackUse` を残す止める関数・`damage_profile` に渡すだけの test_giovanni_machamp_line_v0_11・test_machamp_line_v0_10 を除く）は 16 ファイルです。経路を選ぶテスト（1 行目）だけのファイルを合わせると 19 ファイルになります。
- 旧経路の内部関数を差しかえるテスト（6 行目）は、v0.15b から経路 `LEGACY` を指定しています。KERNEL の同じ確かめ（窓の境界での故障の注入）は tests/test_kernel_integration_v0_15.py の `KernelAtomicityTest` にあります。
- 移す方針（v0.16b・v0.16d）: 公開の API か KERNEL の明確な内部の入口に移し、原典に基づく期待の値とテストの意図を変えません。盤面を直接作るテストは減らしません。移したテストの対応表は docs/legacy-test-migration-v0.16d.md に書きます。旧経路の関数を消す v0.16b のコミットでは、そのコミットでテストが通るように、消す関数を直接使うテストもいっしょに移します。

## 6. カスタムワザの互換性

### 6.1 テスト専用の `AttackEffect`（問い 1・2・5）

`AttackEffect` の部分型でテストの中で定義したものは 21 種類です。製品の登録表には入っていません（登録表の 24 種類はすべて `programs.BUILDERS` にある。tests/test_kernel_integration_v0_15.py が確かめる）。

| 実装（ファイル） | 約束 | 何を確かめるか | v0.15 の処理 |
|---|---|---|---|
| `TwoStepTestEffect`（helpers。test_decisions・test_state_integrity・test_forced_switch_v0_4d・test_kernel_integration_v0_15 で使う） | `resolve`・`resume`、決定 2 段階、ダメージを直接のせる | 保留中の決定（2 段階）・でたらめな答え・保存と復元・不変条件 | 旧経路 |
| `AttackerThenOpponentTestEffect`・`UndeclaredOpponentStepTestEffect`（test_decision_integrity_v0_4e） | `resolve`・`resume`・`decision_problems`、2 段階目は相手が決定 | 決定するプレイヤーが段階ごとに違う決定の不変条件・ほかのコマンドの拒否 | 旧経路 |
| `FlipThenRaise`・`BadCount`（test_coin_attacks） | `resolve`（コインのあと例外） | コインのあとの例外で、渡した状態・乱数が変わらない | 旧経路 |
| `_CoinThenFailEffect`（test_sleep_paralysis）・`FailsAfterCoin`（`SelfDamageOnTails` の部分型。test_self_damage） | `resolve` | 同上（内部の誤り・原典で決められない場合） | 旧経路 |
| `Undecidable`（`ConfuseOnHeads` の部分型。test_confusion_attacks） | `problem` だけを上書き | `problem` をこんらんのコインの前に聞く | 旧経路 |
| `Spy`（`ConfuseOnHeads` の部分型。test_effect_preflight_v0_3d） | `problem`・`resolve`（記録して `super().resolve`） | `problem` を宣言と乱数の前に 1 回聞き、こんらんの「うら」では `resolve` を呼ばない | 旧経路 |
| `SelfHit`（test_counterattack_v0_10・test_guts_v0_11・test_transparency_v0_9 に 1 つずつ） | `resolve`（自分にダメージ）・`damage_profile` | 自分のワザでは「はんげき」「こんじょう」がはたらかない・「とうめい」は自分のワザでもはたらく（C4・G4・T8） | 旧経路 |
| `FixedDamage`（test_guts_v0_11）・`Punch`（test_rocket_moltres_v0_12・test_shell_attack_v0_13）・`SelfKnockOut`（test_phoenix_v0_12） | `resolve`・`damage_profile` | かがくへんかガス（G31）・番のプレイヤーの「こんじょう」（W26）・自分のワザできぜつ（P6） | 旧経路 |
| `StarBoomerang`（test_shell_attack_v0_13） | `resolve`（`finish_damage_elements` のあと時点を記録）・`damage_profile` | 返すダメージ → 自分への効果の時点（p.89。S38・S18・S37） | 旧経路 |
| `TwoHits`（test_shell_attack_v0_13） | `resolve`（同じ相手に 2 回）・`damage_profile` | 2 回受けた返す効果は推測で返さず止める（S7） | 旧経路 |
| `RecordingEffect`（test_effects） | `resolve`（ログだけ） | 登録表の引き方 | 旧経路 |
| `SubclassedDamage`（`DamageOnly` の部分型。test_kernel_integration_v0_15） | `resolve`（記録して `super().resolve`） | 対応表の型の部分型を親の要素の並びで処理しない | 旧経路 |
| `TestOnlyAttack`・`ManyCoins`（test_preflight_v0_15c） | KERNEL の要素の並び（試験のときだけ `BUILDERS` に加える） | 先読みの範囲・上限 | KERNEL |

- **問い 3（登録表を使った独自のワザの実装の約束）**: `EffectRegistry.with_attacks(id, {AttackKey: AttackEntry(effect, name, …)})` で、`effect` は `AttackEffect` の部分型。v0.13 の約束は「`resolve(state, use)` が `deal_attack_damage`・`attack_reaches`・`finish_damage_elements`・`push_attack_decision` などを呼んで処理し、決定を出したら `resume` で続ける。宣言の前の確認は `problem`・`damage_profile`・`opponent_effect_elements` で宣言する」（[api-review.md](api-review.md) 2 章・3 章で「公開（実装を加える人向け）」）。v0.15b から、製品の登録表の実装は `BUILDERS` に要素の並びがあることも必要（テストで確かめる）になりましたが、テスト・外の登録表の実装は v0.13 の約束だけで動きます（`handles` が旧経路に回す）。
- **問い 4（`resolve`・`resume` を持つ独自のワザを KERNEL で扱えるか）**: 今は扱えません（旧経路に回す）。ただし、`resolve` が呼ぶ補助関数は、KERNEL に同じ結果・ログ・乱数の部品があります（`deal_damage`・`reaches`・`fire_pending`・`AttackRun.suspend`。決定の形も同じ `codec.attack_decision`）。補助関数を KERNEL の部品に委ねれば、`resolve` を KERNEL の枠の中で呼べます（7 章）。
- **問い 5（ワザの途中で決定を出す独自の実装）**: 2 種類あります（`TwoStepTestEffect`・`AttackerThenOpponentTestEffect`）。どちらも 2 段階で、`resume` がもう一度決定を出します。KERNEL の今の再開（`flow._resume_attack`）は、決定を出した要素の `resume` のあと次の要素へ進むだけなので、もう一度決定を出す要素を扱えるように直す必要があります。
- **問い 6（旧経路の削除が影響するテスト・拡張方法）**: テスト専用の 19 種類と、それを使う 17 のテストモジュール（6.1 節の表）、v0.13 の約束で書いた外の拡張の実装（あれば）。補助関数を直接呼ぶ単体テスト（5 章）。

### 6.2 v0.13 の約束で書いた実装だけが頼るもの

- 宣言の前の確認を、実装が宣言する（`problem`・`damage_profile`・`opponent_effect_elements`）。KERNEL の先読み（`derived`）は要素の並びを状態の複製の上で試して見つけますが、`resolve` の中身は KERNEL から見えません。たとえば G37（「こんじょう」で残ったポケモンが同じワザの効果を受けるか）は、KERNEL では効果の要素がきぜつした対象を飛ばすときに見つけますが、`resolve` が自分で飛ばすと KERNEL は気づきません。
- 先読みが `resolve` を何度も呼ぶと、実装の中の副作用（`Spy` の記録など）が何度も起こります。v0.13・v0.15 では `resolve` は実際の処理で 1 回だけ呼ばれます。

## 7. 方式の比較と採用

### 7.1 比較

| 観点 | (1) 要素の並びへの移行 | (2) 明示的なアダプタ（採用） | (3) 限定的な互換の経路 | (4) 安全な拒否 |
|---|---|---|---|---|
| 中身 | テスト専用の 19 種類を KERNEL の要素の並びに書き直し、v0.13 の約束を廃止する | v0.13 の約束で書いた実装の `resolve`・`resume` を、KERNEL の枠の中の 1 つの要素として呼ぶ。補助関数は KERNEL の部品に委ねる | 対応表にない実装だけ、旧経路で処理する（v0.15 のまま） | 対応表にない実装は拒否する |
| KERNEL の窓・順番 | 通る | ダメージ・自動の効果・送る効果・きぜつの判定は KERNEL の部品が処理するので通る。`resolve` が状態を直接書きかえる部分（`TwoStepTestEffect` のダメージなど）は、要素で書いても同じことができる（独自のコードの責任） | 通らない（旧ダメージ処理境界・旧きぜつの処理が残る） | 該当なし |
| 宣言の前の確認 | 先読み `derived` | v0.13 の約束どおり、実装の宣言（`problem` と止める関数 5 つ）。`derived` は使わない（6.2 節） | 同左 | 該当なし |
| 拡張の約束 | 変わる（`resolve`・`resume` の実装が動かなくなる） | 変わらない（記録の項目のうち 2 つを外す。7.3 節） | 変わらない | 変わる |
| テストの検証の力 | `resolve` の約束そのものを確かめるテスト（`Spy`・`Undecidable`・`FailsAfterCoin` など）は、約束がなくなるので確かめるものがなくなる | 同じテストがそのまま KERNEL の上で動く | 同じ（ただし旧経路で） | 19 種類を使うテストは書き直しが要る |
| 旧経路の撤去 | できる | できる（補助関数は入口だけが残る） | できない（ワザの処理・きぜつの処理・旧ダメージ処理境界のほぼすべてが残る） | できる |
| 中止の条件 | 6（カスタムワザの互換性を維持できない）に当たる | 当たらない | 撤去にならない | 6 に当たる |
| 実装の量 | テストの書き直し（19 種類） | アダプタ（要素 1 つ・補助関数の入口・再開の直し） | なし | なし |

### 7.2 採用: 明示的なアダプタ（v0.16b で実装する）

**判断**: (2) を採用します。理由は、v0.13 の約束（拡張の約束）を変えずに旧経路を外せる唯一の方式で、ダメージ・自動の効果・きぜつの判定が KERNEL の窓を通るからです。(1)・(4) は中止の条件 6 に当たり、(3) は撤去になりません。

アダプタの責務（v0.16b の設計の約束。docs/kernel-consolidation-v0.16b.md に詳しく書く）:

1. **どのワザに使うか（無条件に呼ばない）**: 登録されたワザの実装の型が `BUILDERS` にあれば、今までどおり要素の並び。なければ、実装が v0.13 の約束で処理できるとき（型が `AttackEffect.resolve` を上書きしているか、`BUILDERS` の型の部分型）だけアダプタ。どちらでもなければ、状態を変える前に `UnsupportedError("UNSUPPORTED_ATTACK")` で拒否する（黙って効果のないワザとして処理しない）。
2. **宣言の前の確認**: v0.13 の約束どおり、実装の `problem` → こんらんのダメージ → C18 → G37 → W24 を、同じ順番で、状態を変える前に確かめる（v0.13・v0.15 でこれらの実装に行っていた確認と同じ）。先読み `derived` は使わない（`resolve` の中身は KERNEL から見えず、副作用のある `resolve` を何度も呼ばないため）。
3. **処理**: 宣言・こんらんのコインは KERNEL のまま。ワザの枠を開き、アダプタの要素が `effect.resolve(state, use)` を呼ぶ。`use` は KERNEL の枠への入口を持ち、補助関数は KERNEL の部品に委ねる（`deal_attack_damage`・`damage_opponent_active` → `kernel.deal_damage`、`attack_reaches` → `kernel.reaches`、`finish_damage_elements` → `kernel.fire_pending`、`push_attack_decision` → `AttackRun.suspend`、`_require_not_evaded` → 枠の「とうめい」の記録）。`resolve` のあとで KERNEL が送る効果の窓を開き、きぜつの判定の窓へ進む。
4. **決定と再開**: 決定の形は v0.13 と同じ（`context` は `("use", …)` と実装の `context`）。再開は KERNEL の `_resume_attack` → `effect.resume`。`resume` がもう一度決定を出したら、そこで止まる（2 段階以上の決定）。
5. **枠の外で補助関数を呼んだら**: `RuntimeError`（KERNEL を通らずにダメージをのせることを許さない）。
6. **部分型**: 標準の 24 種類の `resolve`・`resume` は外す。`AttackEffect` の既定の `resolve`・`resume` を「最も近い `BUILDERS` の型の要素の並びを、今の枠で処理する（決定の再開も）」にして、部分型の `super().resolve` が親の処理（KERNEL の要素の並び）を使えるようにする。

制限（文書に書き、テストで確かめる）:

- アダプタで処理するワザの宣言の前の確認は、実装の宣言に頼ります（v0.13 と同じ）。宣言が足りない実装では、受け付けるかがコインの結果で変わりうる（v0.13・v0.15 と同じ）。KERNEL が実際の処理の中で見つけた原典で決められない場合は、その時点で止めます（コマンドは複製した状態で処理するので、渡した状態・乱数は変わらない）。
- 製品の登録表のワザはアダプタを使いません（24 種類はすべて `BUILDERS` にある。テストで確かめる）。新しいカードは要素の並び（`BUILDERS`）で加えます（旧経路を変える必要はない）。

### 7.3 `AttackUse` の記録の項目

`AttackUse` の 4 つの項目（`reception`・`counterattacks`・`ko_prevention_able`・`retaliations`）は旧ダメージ処理境界が書く「ワザ 1 回の中の記録」で、KERNEL では枠（`FrameState.reception`・`pending`）と解決（`Resolution.ko_prevention_able`）が持っています。

- `reception`・`ko_prevention_able`: 値の意味（場のポケモンの番号 → 真偽）が KERNEL と同じなので、KERNEL の値をそのまま読む項目（プロパティ）にします（枠の外では `RuntimeError`）。
- `counterattacks`・`retaliations`: まだ与えていない送る効果の一覧で、KERNEL の `Deferred` と形が違います。ワザの実装が読む・書くものではない（v0.12 の説明で「安定した API とは約束しない」）ので外し、外したことを文書に書きます。これを直接読み書きしているのは旧ダメージ処理境界の単体テストだけです（5 章）。

## 8. 比較の環境（v0.16a で用意した）

| 木 | 置き場所 | 作り方 |
|---|---|---|
| A: 固定した v0.13 | 作業用の場所（`…/v016/trees/v013`） | `python3 tools/engine_lockstep.py tree --commit 8facf3aeac35d3473ab382ad49b77062f86fd492 --out …/v013` |
| B: 固定した v0.15 | 作業用の場所（`…/v016/trees/v015`） | `python3 tools/engine_lockstep.py tree --commit aa551ab0601e916c3fae3195780eb0aa07761deb --out …/v015` |
| C: 作業中の v0.16 | このリポジトリ（各段階のコミット） | `--root .`（または各段階のコミットを同じ `tree` で展開） |

- `tree`（v0.16a で加えた）は、このリポジトリから `git archive` で展開し、木に `FIXED_COMMIT`（コミットと版）を書きます。空でない場所には書きません（固定した木を上書きしない）。v0.15 の作業で作った木と、ファイルの中身が同じことを確かめました（`diff -r`）。
- 比べるときは、各木の公開の API（`new_game`・`apply_command`・`state_to_dict`・`command_to_dict`・`EngineError`）だけを使い、別々のプロセス（`python3 -P -s`・`PYTHONHASHSEED=0`）でその木の `kyuura_engine` だけを読み込みます（`tools/engine_lockstep.py record`）。旧経路・経路の指定に頼らないので、v0.16 で旧経路を消したあとも、v0.13・v0.15 と同じ方法で比べられます。
- 対戦の進め方（各木の `tests/test_*_games*.py` の `play_game`、`tools/stress_engine.py` の `choose_command`）はその木のものを使います。v0.16 ではこれらの方針を変えません（v0.16e で、比べる木の間で方針のファイルが同じことを確かめる）。
- **許す差（v0.16a で道具に加えた）**: 決定への答えの `WRONG_PHASE` の理由の文は、v0.13 から段階の名前の並びが `frozenset` の並び（文字列のハッシュで決まる）で、v0.16d で決まった並びにします。v0.16 から、`record` は `WRONG_PHASE` の拒否の理由の文そのもの（`m`）も記録し、`compare` は「同じ歩・同じコマンド・どちらも `WRONG_PHASE`・今の段階が同じ・段階の名前の集まりが同じ・文と指紋が合う」ときだけ、食い違いではなく許した差として数えて例を表示します。ほかの理由の文の違い・`m` のない記録の違いは食い違いです（tests/test_lockstep_tool_v0_16.py）。
- **確かめた結果（小さな規模）**: 自然な対戦 23 方針 × 2 seed とストレス実行 26 組 × 1 seed（拒否されるコマンドを混ぜる。7 歩ごとに保存と復元）で、A と B、B と C（`aa551ab` + 道具の変更）を比べ、どちらも 72 対戦・13,362 歩で食い違い 0・許した差 0 でした。全体の規模の比較は v0.16e で行います。

### 8.1 同じ木の中の比較を、旧経路の結果の参照データに置きかえた

v0.14・v0.15 の比較のテストは、同じ盤面・同じコマンドを旧経路（`Route.LEGACY`）と KERNEL に渡して比べていました。盤面を直接作るテスト（`tests/test_event_kernel_v0_14.py` の `Both` など）は、対戦では起こりにくい組み合わせ（「とうめい」と「はんげき」・返す効果の枠の中の枠・原典で決められない場合の理由の文など）を確かめていて、別の木との 1 歩ごとの比較（自然な対戦・ストレス実行）では置きかえられません。旧経路を外すとこれらの比較ができなくなるので、v0.16a で、旧経路の結果を固定した参照データにしました。

| | |
|---|---|
| 参照データ | `tests/fixtures/legacy_reference_v0_15.json`（約 600 KB）。呼び出し 1,875 件（受け付け 1,060・拒否 815）と、対戦の 1 歩ごとの結果の連なり 37 対戦（7,014 歩） |
| 記録したもの | 呼び出しごと（テストの id と、そのテストの中の呼び出しの順番）に、渡した盤面の指紋（形式 9 の全体・乱数の指紋・コマンド）と、旧経路の結果（受け付けたら返した状態の形式 9 の全体の指紋、拒否なら例外の種類・コード・理由の文）。対戦は、対戦ごとに歩の数と、1 歩ごとの（盤面の指紋, 結果）の連なりの指紋 |
| 記録した木 | v0.16a の作業の木。`kyuura_engine/`・`experiments/` は `aa551ab` と同じ（`git diff --quiet aa551ab -- kyuura_engine experiments` で確かめた。`kyuura_engine/` の git の tree は `a616b53…`） |
| 作り方 | 旧経路がある木で `KYUURA_RECORD_LEGACY_REFERENCE=1 python3 -m unittest tests.test_event_kernel_v0_14 tests.test_event_kernel_games_v0_14 tests.test_kernel_integration_v0_15 tests.test_preflight_v0_15c`。旧経路がない木（v0.16b から）では作れない（`RuntimeError`）。今の版から作り直さない |
| 比べ方（`tests/legacy_reference.py`） | 盤面の指紋が記録と違えば失敗（テストの盤面が記録したときと違うと、比べる意味がない）。記録にない呼び出しも失敗。結果は完全に同じであること |
| 許した並べ直し | 決定への答えの `WRONG_PHASE` の理由の文の、段階の名前の並びだけを、名前の順に並べ直してから記録し比べる（この並びはプロセスごとに変わる。8 章）。ほかの理由の文・コード・例外の種類はそのまま（tests/test_legacy_reference_v0_16.py） |
| 決まっていること | 文字列のハッシュの種（`PYTHONHASHSEED`）を変えて 2 回記録し、バイト単位で同じ参照データになることと、別の種で比べても通ることを確かめた |

参照データに置きかえたテスト（v0.16a）: `test_event_kernel_v0_14` の `Both.both`（47 か所の呼び出し）と `GameTest`（対戦 5 つ）、`test_event_kernel_games_v0_14`（`tools/event_kernel_compare.py` の `Comparator` に連なりの比べを加えた。対戦 32）、`test_kernel_integration_v0_15` の `MessageTest.test_stop_messages_are_the_same_on_both_routes`・`DispatchTest` の 2 つ（対応表にないワザ = v0.16b のアダプタが同じ結果を出すことの基準になる）、`test_preflight_v0_15c` の `EquivalenceTest`（900 を超える盤面とコインの組）・`LimitTest.test_verified_fallback_accepts_like_the_v0_13_route`。v0.16a の時点では、どれも旧経路の結果と KERNEL の結果が同じ（参照データと比べて通る）。

## 9. v0.16b〜v0.16d の計画

| 段階 | 消す・移すもの | 残すもの |
|---|---|---|
| v0.16b | `engine.py` の旧経路（2 章の 24 の関数と `Route`・`DEFAULT_ROUTE`・`apply_command_via`・`resolution.handles`）。`effects.py` の旧ダメージ処理境界の実装（`deal_attack_damage`・`attack_reaches`・`finish_damage_elements` の中身、`_apply_counterattack`・`_apply_retaliation`・`retaliation_use`・`Pending*`・`_require_damage_elements_finished`）と、24 の実装の `resolve`・`resume`、それだけが使う補助（`_skip_heal_of_knocked_out_attacker`・`_remove_attacker_counters`。`_check_damage_then_effect` は登録の照合が使うので残す。v0.16b で訂正）。アダプタ（7.2 節）を加える。消す関数を直接使うテストを、そのコミットで移す | 効果の登録と照合・クラスの定義・`check`・`problem`・`damage_profile`・`opponent_effect_elements`・`decision_problems`・`retaliation_terms`・ダメージの計算・コイン・特殊状態・決定の保存と復元・持続する効果・常にはたらく効果・トレーナー・宣言する特殊能力・不変条件の問い合わせ・公開の問い合わせ・補助関数の入口 |
| v0.16c | 宣言の前の先読みの方法 `legacy`・`LEGACY_VERIFIED` の扱いを比べて決める（A: 限定的なモジュールに残す、B: 新しい共通の判定、C: 一律に拒否）。上限の前後の試験 | 決めたもの |
| v0.16d | 重複（回復・きぜつの処理・きぜつしたあとの候補・決定の再開）の整理、経路を選ぶテスト・道具の移行、`experiments/event_kernel/__init__.py` を残すか、`WRONG_PHASE` の並び（別のコミット） | — |

見積もり（確認した事実）: 消す候補のコードは `engine.py` 約 490 行、`effects.py` 約 820 行（24 の実装の `resolve`・`resume` 約 470 行を含む）です。

### 中止・延期の条件の見張り

| 条件 | 今の見込み |
|---|---|
| 1. 原典で確認できない新しい裁定が要る | 要らない（処理の意味を変えない） |
| 2. KERNEL で表せない既存の効果 | ない（24 種類は要素の並び、テスト専用の 19 種類はアダプタ） |
| 3. 未解決の裁定の止める条件が変わる | 変えない（対応表の 24 種類は KERNEL の先読みのまま、アダプタは v0.13 の確認のまま） |
| 4. 保存形式 9 を変える必要 | ない（決定の形は同じ） |
| 5. テストの検証の内容を弱める必要 | ない見込み（v0.16b・v0.16d で、移したテストの対応表を書く） |
| 6. カスタムワザの互換性を維持できない | アダプタで維持する。維持できない形が見つかったら、その部分の削除を延期する |
| 7. 上限のときの安全性 | v0.16c で確かめる |
| 8. 比較の独立性 | 8 章の環境で保つ |
| 9. 原因の分からない差 | v0.16b・v0.16e で、固定した木と比べて確かめる |
| 10. 性能 | v0.16e で測る |

## 10. 変えていないもの

v0.16a では、エンジンのコード・テストの期待の値・裁定・止める条件・保存形式・公開の API を変えていません。変えたのは次のものだけです。

- 比較の道具: `tools/engine_lockstep.py`（`tree` と、`WRONG_PHASE` の許す差の判定）、`tools/event_kernel_compare.py`（`Comparator` の参照データの連なり）
- 参照データ: `tests/legacy_reference.py`・`tests/fixtures/legacy_reference_v0_15.json`（8.1 節）
- テスト: 旧経路と比べていた所を参照データと比べるようにした（8.1 節。期待の値は旧経路の結果のまま）。新しいテスト tests/test_lockstep_tool_v0_16.py（6 件）・tests/test_legacy_reference_v0_16.py（5 件）
