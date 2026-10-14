# 旧ワザ解決経路の撤去（v0.16b）

v0.13 の経路（`engine.py` の旧ワザ解決経路・旧きぜつの処理・旧決定の再開と、`effects.py` の旧ダメージ処理境界・旧自動効果の解決・標準の実装の `resolve`・`resume`）を外し、ワザ・番の終わり・きぜつのあとの決定を、効果の解決の基盤（`kyuura_engine/resolution`。以下 KERNEL）だけが処理するようにしました。v0.13 の約束（`AttackEffect.resolve`・`resume`）で書いたワザの実装は、KERNEL の枠の中で処理する明示的なアダプタ（`resolution/contract.py`）で引き続き使えます（拡張の約束を変えない）。

- 監査と方式の判断は [legacy-removal-audit-v0.16a.md](legacy-removal-audit-v0.16a.md)（7 章）。この文書はその実装です。
- 「確認した事実」は実際に動かした結果、「方針」は判断です。
- ルールの意味（処理・ログの形と順番・乱数の使い方・拒否のコードと順番・止める条件）・保存形式 9・公開の API は変えていません（7 章で、固定した v0.15 と別のプロセスで比べた）。

## 1. 消したもの

| 置き場所 | 消したもの | 行（確認した事実） |
|---|---|---|
| `engine.py` | 旧経路の 24 の関数（`_use_attack`・`_resume_attack`・`_finish_attack`・`_ko_prevention_offer`・`_resume_knock_out`・`_knock_out_after_attack`・`_post_knockout_candidates`・`_after_knockouts`・`_then_context`・`_post_knockout_context`・`_next_prize_or_judge`・`_promotions_after_judge`・`_offer_post_knockout`・`_resume_post_knockout`・`_next_promotion_or_end`・`_resume_take_prize`・`_resume_promote_active`・`_end_turn_command`・`_end_turn`・`_pokemon_check`・`_resolve`・`_resolve_decision`・`_take_prize`・`_promote_active`）、表 `_RESUMERS`、経路の `Route`・`DEFAULT_ROUTE`・`apply_command_via` | 2,327 → 1,784 行 |
| `effects.py` | 標準の 24 の実装の `resolve`・`resume`（と `DamageAndForceSwitch._skip`）、旧ダメージ処理境界の実装（`deal_attack_damage`・`attack_reaches`・`finish_damage_elements` の中身）、旧自動効果の解決（`_apply_counterattack`・`_apply_retaliation`・`PendingCounterattack`・`PendingRetaliation`・`_require_damage_elements_finished`）、`resolve` だけが使った補助（`_skip_heal_of_knocked_out_attacker`・`_remove_attacker_counters`）、`AttackUse` の記録の項目 `counterattacks`・`retaliations` | 4,152 → 3,349 行 |
| `resolution/flow.py` | 旧経路に回すための振り分け `handles`・`_continued_attack_effect`・`_answer` | — |

本番のコード（`kyuura_engine/`・`experiments/`・`tools/`）の差は、1,618 行を消し、297 行を書きかえ・加え、`resolution/contract.py`（190 行。アダプタ）を加えました。

**v0.16a の分類の訂正**: v0.16a の監査（3.2 節）は `_check_damage_then_effect` を「24 の `resolve` だけが使う」と分類しましたが、実際は登録の照合（`check`）が使っていました（5 つの実装）。v0.16b では消していません（消した写しで `F821` になって分かった）。

## 2. 残したもの（消さない理由）

| もの | 理由（分類） |
|---|---|
| 効果の登録と照合（`EffectRegistry`・`AttackEntry`・各実装の `check`・`_check_damage_then_effect`） | 登録の照合（A） |
| 各実装のクラスと、`problem`・`damage_profile`・`opponent_effect_elements`・`decision_problems`・`retaliation_terms`・量の値 | 要素の並び（`BUILDERS`）が値を読む・不変条件・宣言の前の確認（v0.13 の止める関数。v0.16c）（A） |
| v0.13 の止める関数（`counterattack_double_knockout_problem`・`ko_prevention_attack_effect_problem`・`retaliation_double_knockout_problem`・`prevented_coin_damage_problem`・`evaded_effect_coin_problem`・`preview_attack_damage`・`damage_receiver`・`retaliation_use`）と理由の文の関数 | 上限を超えたときの確かめ・先読み `legacy`・アダプタの宣言の前の確認（A。v0.16c で扱いを決める） |
| 補助関数の入口（`deal_attack_damage`・`damage_opponent_active`・`attack_reaches`・`finish_damage_elements`・`decisions.push_attack_decision`・`_require_not_evaded`） | v0.13 の約束の実装が呼ぶ（F）。中身は KERNEL の部品に委ねる（3 章） |
| ダメージの計算・コイン・特殊状態・持続する効果・常にはたらく効果・決定の保存と復元・公開の問い合わせ（`working_*`・`available_ko_prevention_power`）・不変条件の問い合わせ（`ko_prevention_power`・`post_knockout_power` など） | A・B |
| トレーナー（`TrainerEffect.resolve` など）・宣言する特殊能力（`PowerEffect.resolve` など）・進化・にげる・エネルギー・対戦準備 | 範囲外（B） |
| `_resume_trainer`・`_finish_trainer` | トレーナーの決定（範囲外。B） |

## 3. カスタムワザのアダプタ（`resolution/contract.py`）

### 3.1 どの実装に使うか（`contract.program_for`）

1. 実装の型が対応表（`programs.BUILDERS`。型が完全に一致するもの）にあれば、要素の並び（v0.15 と同じ）。
2. なければ、v0.13 の約束で処理できる実装（型が `AttackEffect.resolve` を上書きしているか、対応表の型の部分型。`follows_contract`）だけ、アダプタの要素 1 つ（`Contract`）の並び。
3. どちらでもなければ、状態を変える前に `UnsupportedError("UNSUPPORTED_ATTACK")`（理由の文に実装の型と `implementation_id`）。黙って効果のないワザとして処理しません。`UNSUPPORTED_ATTACK` は登録のないワザと同じコード（新しいコードは加えていない）で、確認の順番は `checks.attack_request`（番・ワザの位置・ねむり・マヒ・登録・エネルギー）のあと、宣言・こんらんのコインの前です。

製品の登録表の 24 種類はすべて 1 です（tests/test_kernel_integration_v0_15.py の `test_every_registered_attack_is_handled_by_the_kernel` が、対応表にあり、アダプタでないことを確かめる）。

### 3.2 処理（KERNEL の窓を通る）

宣言・こんらんのコインは KERNEL のまま（`flow._attack_body`）。ワザの枠（`FrameKind.ATTACK`）を開き、`Contract.run` が `effect.resolve(state, use)` を呼びます。`use` は KERNEL の枠への入口（`AttackUse.runtime` = `ContractRuntime`）を持ち、補助関数はそれに委ねます。

| 補助関数（v0.13 の約束） | v0.16b の処理 |
|---|---|
| `deal_attack_damage`・`damage_opponent_active` | `kernel.deal_damage`（「ダメージを受けない」状態・計算・「とうめい」・ダメージを受けたときの効果の候補・きぜつの原因の記録） |
| `attack_reaches` | `kernel.reaches`（「とうめい」。効果の要素は、送る効果が残っていれば `RuntimeError`。1 つのワザで 2 匹目の「とうめい」は T27 で止める） |
| `finish_damage_elements` | `kernel.fire_pending`（ダメージの要素のあとの窓。2 つ以上は C34・C35 で止める） |
| `decisions.push_attack_decision` | `AttackRun.suspend`（決定の形は v0.13 と同じ。送る効果が残っていれば `RuntimeError`） |
| `_require_not_evaded`・`AttackUse.reception` | 枠の「とうめい」の記録（`FrameState.reception`） |
| `AttackUse.ko_prevention_able` | 解決の記録の写し（`Resolution.ko_prevention_able`） |

`resolve` のあと、KERNEL が送る効果の窓を開き（v0.13 の `_use_attack` が `finish_damage_elements` を呼んでいたのと同じ）、きぜつの判定の窓（`flow._finish_attack`）へ進みます。補助関数に処理中の状態と別の状態を渡すと `RuntimeError` です。

### 3.3 決定と再開・標準の実装の部分型

- 決定の形は v0.13 と同じです（`context` は `("use", …)` と実装の `context`。保存形式 9 のまま）。答えのあと `flow._resume_attack` → `Contract.resume` → `effect.resume` で、`resume` がもう一度決定を出したら、そこで止まります（2 段階以上の決定。`programs.decision_index` は要素の `decides` で決定を出した要素を探す）。
- 標準の 24 種類は `resolve`・`resume` を持ちません。`AttackEffect` の既定の `resolve`・`resume` は、最も近い対応表の型の要素の並びを今の枠の中で処理します（`ContractRuntime.run_builtin`・`resume_builtin`）。部分型の `super().resolve` は親の処理（KERNEL の要素の並び）になります。

### 3.4 宣言の前の確認と制限

- アダプタで処理するワザの宣言の前の確認は、v0.13 の約束どおり実装の宣言です（`preflight.legacy`。v0.16c から `resolution/v013_checks.py` の `check`。`effect.problem` → こんらんのダメージ → C18 → G37 → W24 の順。解決の記録には先読みの方法 `contract` と残す）。先読み `derived`・`derived_full` は使いません（`resolve` の中身は KERNEL から見えず、副作用のある `resolve` を複製の上で何度も呼ばないため。v0.13・v0.15 でこれらの実装に行っていた確認と同じ）。要求した先読みの方法によりません。
- **制限**: 宣言が足りない実装（たとえば相手に効果を与えるのに `opponent_effect_elements` を宣言しない）では、受け付けるかがコインの結果で変わりうる（v0.13・v0.15 と同じ）。KERNEL が実際の処理の中で原典で決められない場合に当たれば、その時点で止めます（コマンドは複製した状態で処理するので、渡した状態・乱数は変わらない）。実装の中で状態を直接書きかえる部分（`TwoStepTestEffect` のダメージなど）は、KERNEL の窓を通りません（要素の並びの独自の要素でも同じ。独自のコードの責任）。
- **`AttackUse` の項目**: `reception`・`ko_prevention_able` は KERNEL の値を読む項目（枠の外では `RuntimeError`）にし、`counterattacks`・`retaliations`（まだ与えていない送る効果。KERNEL の `kernel.Deferred` と形が違い、ワザの実装が読み書きするものではない）は外しました。`AttackUse` は新しく `runtime`（比較・ハッシュ・表示に含めない）を持ちます。これらが拡張の約束で変わった点のすべてです（4 つの項目を直接読み書きしていたのは、旧ダメージ処理境界の単体テストだけでした）。
- 枠の外（`runtime` のない `AttackUse`）で補助関数を呼ぶと `RuntimeError`（KERNEL を通らずにダメージをのせない）。単体テストは `resolution.open_attack(state, player)` で枠を開いて呼びます。

## 4. 入口と振り分け

| | |
|---|---|
| `apply_command(state, command)` | 公開。呼び方・戻り値・例外は変えていない（tests/test_kernel_integration_v0_15.py の `EntryTest`） |
| `engine.apply_command_with(state, command, *, preflight, catalog)` | 内部の入口（v0.15b の `apply_command_via` の経路の引数のない形）。先読みの方法・効果の定義の対応表を選ぶ（試験・比較用） |
| `engine.apply_command_traced(...)` | 内部の入口（v0.15b のまま）。解決の記録を返す |
| `engine._HANDLERS` | `UseAttack`・`EndTurn` は `resolution.handle`。決定への答え（`ResolveDecision`・`TakePrize`・`PromoteActive`）は `engine._answer_decision`。範囲外のコマンドは engine.py の処理 |
| `engine._answer_decision` | 確認は `checks.decision_choices`（v0.15 と同じ確認・順番・コード）。再開先が `resolution.RESUMES`（attack・knock_out・post_knockout・take_prize・promote_active）なら `resolution.resume_decision`、`trainer` なら `_resume_trainer`。不変条件の再開先の一覧は `engine.DECISION_RESUMES` |
| `resolution.processes(state, command)` | KERNEL が処理するコマンドか（数を数える・試験のための問い合わせ。振り分けには使わない） |

経路を選ぶ名前（`Route`・`DEFAULT_ROUTE`・`apply_command_via`）と `resolution.handles` は外しました（戻っていないことを `EntryTest.test_public_apply_command_is_unchanged` が確かめる）。比較の道具は、v0.15 の木では `apply_command_via`、v0.16b からの木では `apply_command_with` を使います（`tools/engine_lockstep.py`）。

## 5. 旧い名前と新しい場所（CLAUDE.md・v0.10〜v0.13 の文書を読むため）

| v0.13〜v0.15 の名前 | v0.16b の処理 |
|---|---|
| `engine._use_attack` | `resolution.flow._use_attack`（確認は `checks.attack_request`） |
| `engine._finish_attack`・`_ko_prevention_offer`・`_resume_knock_out`・`_knock_out_after_attack` | `flow._finish_attack`（`kernel.check_simultaneous`・`kernel.ko_prevention_offers`）・`flow._resume_ko_check`・`flow._knock_out_after_attack` |
| `engine._post_knockout_candidates` | `kernel.capture_post_knockout` |
| `engine._after_knockouts`・`_next_prize_or_judge`・`_promotions_after_judge`・`_offer_post_knockout`・`_resume_post_knockout`・`_next_promotion_or_end`・`_resume_take_prize`・`_resume_promote_active` | `flow` の同じ名前の関数（`res` を受け取る）・`flow._resume_promote` |
| `engine._end_turn`・`_pokemon_check`・`_end_turn_command` | `flow._end_turn`・`flow._pokemon_check`・`flow._end_turn_command`（共通の手続きは `procedures`） |
| `engine._resume_attack` | `flow._resume_attack` |
| `effects.deal_attack_damage`（の中身） | `kernel.deal_damage`（`deal_attack_damage` は入口として残る） |
| `effects.attack_reaches`（の中身） | `kernel.reaches` |
| `effects.finish_damage_elements`（の中身）・`_apply_counterattack`・`_apply_retaliation` | `kernel.fire_pending`・`kernel.power_damage_to_damage_source`・`kernel.attack_damage_to_damage_source` |
| `AttackUse.counterattacks`・`retaliations` | 枠の送る効果の列（`FrameState.pending`。`kernel.Deferred`） |
| 標準の実装の `resolve`・`resume` | `programs.BUILDERS` の要素の並び |
| `engine.Route`・`apply_command_via` | なし（`apply_command_with`） |

## 6. テストの移行（このコミットで、消した関数を使っていたテストを移した）

| テスト | 移した内容（意図と期待の値は保つ） |
|---|---|
| tests/helpers.py | `apply_legacy` を外し、`apply_kernel` は `apply_command_with`（解決の設定を選ぶ） |
| test_counterattack_v0_10 | `DirectTest`（5 件）は `open_attack` の枠で補助関数を呼び、まだ与えていない「はんげき」は `runtime.pending` で見る。C34・C35 は 2 つの `Deferred` を置いて、コードのない問い `multiple_deferred_effects`（入口で `RuntimeError`）を確かめる。`test_internal_error_after_the_counter` は誤りを注入する所を KERNEL の同じ境界（ログ `counterattack`・`drain_heal`・`codec.push_decision`・`programs.APPLY_CONDITION`）にした。`test_double_knock_out_guard_after_the_preflight` は KERNEL の先読み（`preflight.derived`・`legacy`）を外して、実際の処理が同じコード（`UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT`）で止めることを確かめる（v0.13 の経路は `RuntimeError` だった。KERNEL の検出は先読みと同じなので同じコードの拒否。v0.15b の `KernelGuardTest` と同じ考え方） |
| test_transparency_v0_9 | `DirectReceptionTest` を `open_attack` の枠にした。**期待の変更 1 件**: `test_each_haunter_flips_once_per_attack` で、1 つのワザで 2 匹目の「とうめい」を評価すると、KERNEL は T27（コインの順番が原典で決められない。docs/transparency-v0.9.md・CLAUDE.md）としてコインの前に止める（コードのない問い `multiple_evasion`）。v0.13 の補助関数は 2 匹目も評価していた（対応カードでは起こらない）。製品の登録表のワザの結果は変わらない（7 章） |
| test_guts_v0_11 | `_ko_prevention_offer` の 2 件は KERNEL のきぜつの判定の窓（`kernel.ko_prevention_offers`）で確かめる。`test_declared_elements_match_the_implementations` は、実装の `resolve` の中の `attack_reaches` の呼び出しを読む代わりに、登録されたワザの要素の並びから効果の要素を求めて、宣言と比べる |
| test_phoenix_v0_12 | `_post_knockout_candidates` を KERNEL のきぜつの処理の窓（`kernel.capture_post_knockout`）にした（P19・P32 はコードのない問いを入口と同じく `RuntimeError` にして確かめる） |
| test_combat・test_simultaneous_ko | `engine._after_knockouts`・`_next_prize_or_judge` を `flow` の同じ関数にした |
| test_damage_result_audit_v0_4e・test_damage_drain_v0_4d | `AttackUse` を直接作る代わりに `open_attack` の枠で `deal_attack_damage` を呼ぶ |
| test_unresolved_boundaries_v0_4e | `CodeListTest` が数えるエンジンのファイルに `resolution/` を含めた（`UNRESOLVED_RECOVER_ZERO_ENERGY` は `programs.py` だけになった） |
| test_kernel_integration_v0_15 | `RouteTest` を `EntryTest`（公開の API・設定の選び方・モジュールの値・消した名前が戻っていない）に、`DependencyTest` の 1 件を「範囲外のコマンドの処理は解決の基盤を使わない」に、`DispatchTest` を振り分け（`COMMANDS`・`RESUMES`・トレーナーの決定は engine.py）とアダプタ（参照データと同じ結果）にした |
| test_kernel_invariants_v0_15 | 受け持つかを `resolution.processes`、記録をとらない処理を `apply_command_with` で求める |
| test_event_kernel_games_v0_14 | `test_a_divergence_is_reported` は、KERNEL の答えを変えると参照データ（v0.13 の連なり）と違うと報告すること、先読みの方法の 1 つだけを変えると `Divergence` になることを確かめる |
| 新しい tests/test_contract_adapter_v0_16.py（11 件） | アダプタの選び方と拒否・窓（標準のワザと同じログ・順番を守らない実装を止める・別の状態）・宣言の前の確認（`resolve` は 1 回・`problem` が宣言の前）・2 段階の決定と保存と復元・標準の実装の部分型（ふきとばし）・枠の外の補助関数 |

テスト専用のワザ 19 種類は書きかえていません（v0.13 の約束のまま、アダプタで動く）。全体の移行の対応表は docs/legacy-test-migration-v0.16d.md にまとめます。

## 7. 確かめたこと（確認した事実）

- `python3 -m unittest`: Python 3.11・3.12・3.13 で 1,802 件が通る（skipped 1。v0.16a の 1,791 件 + アダプタの 11 件。消したテストはない）。
- 参照データ（v0.16a。旧経路の結果）との比較: 盤面を直接作る比較のテスト（呼び出し 1,875 件・対戦 37）がすべて一致。対応表にない実装（2 段階の決定・`DamageOnly` の部分型）のアダプタの結果も、旧経路で記録した結果と一致。
- 固定した v0.15（`aa551ab`）と別のプロセスで比べた（`tools/engine_lockstep.py`。自然な対戦 23 方針 × 10 seed・ストレス実行 26 組 × 3 seed・拒否されるコマンドを混ぜる・7 歩ごとに保存と復元）: 308 対戦・56,739 歩で食い違い 0・許した差 0。
- `ruff check --select F,E9 .`: 問題なし。

## 8. していないこと

- 宣言の前の先読みの方法 `legacy` と `LEGACY_VERIFIED` の扱い（v0.16c → [preflight-consolidation-v0.16c.md](preflight-consolidation-v0.16c.md)。案 A で `resolution/v013_checks.py` に分けて残した）。
- 重複の整理・`experiments/event_kernel/__init__.py` を残すか・`WRONG_PHASE` の並び（v0.16d）。
- 全体の規模の比較・性能・変異試験（v0.16e）。
