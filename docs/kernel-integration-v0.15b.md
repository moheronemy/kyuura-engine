# 解決の基盤の本番への統合（v0.15b）

v0.14 のプロトタイプ（`experiments/event_kernel/`）を、本番のパッケージの内部の部品 `kyuura_engine/resolution/` にしました。コマンドを処理する経路を 2 つ（v0.13 の経路 `LEGACY`・解決の基盤 `KERNEL`）持ち、比較のテストと道具から経路を明示して選べます。v0.15b では標準の経路（公開の `apply_command` が使う経路）は `LEGACY` のままで、切り替えは全体の検証のあと（v0.15d）に行います。v0.13 の経路は消していません（v0.16 で外す候補）。

- 「確認した事実」は実際に動かした結果、「評価」はその解釈です。
- ルールの意味（処理・ログの形と順番・乱数の使い方・拒否のコードと順番・止める条件）は変えていません（7 章で、固定した v0.13 と別のプロセスで比べた）。
- 依存の整理（v0.15a）は [integration-dependencies-v0.15a.md](integration-dependencies-v0.15a.md)、仕組みの設計は [event-model-v0.14.md](event-model-v0.14.md)。

## 1. 置き場所（コードの複製はない）

| 置き場所 | 中身 |
|---|---|
| `kyuura_engine/resolution/`（9 ファイル。`git mv` で移したので履歴が続く） | `events`（窓・枠・枠の表・解決の記録）・`catalog`（効果の定義の対応表）・`kernel`（ダメージの要素の窓・送る効果・きぜつの判定）・`programs`（ワザの要素の並び）・`questions`（原典で決められない場合の表）・`preflight`（宣言の前の先読み）・`codec`（続きの情報と決定の相互の変換）・`flow`（コマンドの処理。入口 `handles`・`handle`・`Context`） |
| `experiments/event_kernel/__init__.py`（74 行） | v0.14 のテスト・道具が使う名前を本番の部品につなぐだけの互換の層。下のモジュールの名前（`experiments.event_kernel.kernel` など）は `sys.modules` に本番のモジュールそのものを登録する（試験で対応表を差しかえると本番の部品が変わる）。`apply_command` は経路 `KERNEL` を指定した `engine.apply_command_via` |

- 読み込みは相対（`from ..effects import …`）にしました。中身の変更は 2〜5 章のものだけです。
- 互換の層がコードを複製していないこと（`experiments.event_kernel.kernel is kyuura_engine.resolution.kernel`・`experiments/event_kernel/` に `__init__.py` しかない）はテストで確かめています（tests/test_kernel_integration_v0_15.py の `DependencyTest`）。互換の層を外すかは v0.16 で決めます。
- 解決の基盤は公開の API ではありません（`kyuura_engine.__all__` に加えていない。テストで確かめている）。

## 2. 経路（`engine.Route`）

| | |
|---|---|
| `Route.LEGACY` | v0.13 の経路（`engine.py` の `_use_attack`・`_finish_attack`・`_RESUMERS` など） |
| `Route.KERNEL` | 解決の基盤（`kyuura_engine/resolution`）。受け持つコマンドだけを処理し、ほかは v0.13 の処理（3 章） |
| `engine.DEFAULT_ROUTE` | 公開の `apply_command` が使う経路。モジュールの定数で、処理の途中で書きかえない。v0.15b では `LEGACY` |
| `engine.apply_command_via(state, command, *, route, preflight, catalog)` | 内部の入口。経路を引数で選ぶ（比較・試験用）。`preflight`・`catalog` は経路 `KERNEL` の設定 |
| `engine.apply_command_traced(state, command, *, preflight, catalog)` | 内部の入口。経路 `KERNEL` で処理し、(新しい状態, 解決の記録) を返す |

- **公開の `apply_command(state, command)` の呼び方は変えていません**（引数・戻り値・例外。テストで引数を確かめている）。
- **経路と先読みの方法は別のものです。** 経路は「どの実装でコマンドを処理するか」、先読みの方法（`resolution.PREFLIGHT_MODES` の `derived`・`legacy`）は「経路 `KERNEL` が、宣言の前に原典で決められない場合をどう確かめるか」です。`derived` は仕組みの共通の検出をコインと決定のすべての結果で試し、`legacy` は v0.13 の止める関数を呼びます。4 つの組み合わせのどれでも結果が同じことをテストで確かめています（`RouteTest.test_route_and_preflight_are_different_settings`）。
- **グローバルな可変フラグで切り替えません。** 経路はコマンドごとの引数で、設定（`resolution.Context`。先読みの方法・対応表・解決の記録）はコマンドごとに作ります。経路を選んで処理しても、`engine`・`resolution` のモジュールの値が変わらないことをテストで確かめています。

### コマンドの入口（両方の経路で同じ）

`engine._apply` が、どちらの経路でも同じ順番で次を行います。

1. 未対応のコマンド（`UNSUPPORTED_ACTION`）→ 知らないコマンド（`UNKNOWN_COMMAND`）→ 項目の型（`check_command_fields`）
2. 終わった対戦（`GAME_OVER`）・サドン・デス・止めた対戦（`HALTED` のコード）
3. 状態の複製（`clone`）
4. 経路が `KERNEL` で `resolution.handles(state, command)` なら `resolution.handle(複製, command, 設定)`、それ以外は v0.13 の処理（`_HANDLERS`）
5. 不変条件（`_require_integrity`）

渡した状態を変えないこと・返す状態を不変条件で確かめることは、経路によりません。

## 3. 受け持つコマンド（`resolution.handles`）

| コマンド | 経路 `KERNEL` で解決の基盤が処理するとき |
|---|---|
| `UseAttack` | ワザの実装の型が要素の並びの対応表（`programs.BUILDERS`）にあるとき。確認（`checks.attack_request`）で拒否されるワザも受け持つ（どちらの経路も同じ関数で、同じ例外で拒否する） |
| `EndTurn` | いつも |
| `ResolveDecision`・`TakePrize`・`PromoteActive` | 保留中の決定の再開先が `knock_out`・`post_knockout`・`take_prize`・`promote_active` のとき。再開先が `attack` なら、続きの情報のワザの実装の型が対応表にあるとき |
| ほか（トレーナー・ポケモンパワーの宣言・進化・にげる・エネルギー・対戦準備、再開先がトレーナーなどの決定への答え） | 受け持たない（どちらの経路でも v0.13 の処理） |

- `ResolveDecision` をすべて解決の基盤に送ってはいません。再開先で振り分けます。
- **対応表にないワザの実装は v0.13 の処理にまかせます。** 対応表は型が完全に一致するものだけです（部分型も対応表にない）。製品の登録表のワザの実装（24 種類）はすべて対応表にあり（テストで確かめている）、v0.13 の処理になるのは、試験の登録表の実装（v0.13 の `AttackEffect.resolve` の約束だけで書いた、テストの中で定義した実装。`TwoStepTestEffect`・`StarBoomerang` など）だけです。こうすると、効果の登録表に実装を加える方法（`AttackEffect` の約束）を変えずに済み、対応表にない実装を黙って効果のないワザとして処理することもありません。
- 決定の形は両方の経路で同じ（形式 9。[event-model-v0.14.md](event-model-v0.14.md) 5 章）なので、どちらの経路が出した決定も、どちらの経路でも続けられます。v0.13 の処理で出したワザの途中の決定（対応表にない実装）は、答えも v0.13 の処理で続きます（`DispatchTest.test_effects_outside_the_table_use_the_v0_13_path`）。

## 4. 依存の向き

```
engine.py ──→ resolution/ ──→ checks.py・procedures.py ──→ state・effects・damage・coins・conditions・persistent・zones・judge…
    └──────────────────────────→ checks.py・procedures.py
```

- `resolution/`・`checks.py`・`procedures.py` は `engine.py` を読み込みません（`engine → resolution → engine` の循環はない）。`checks.py`・`procedures.py` は `resolution/` も読み込みません。どちらもテストで `ast` を使って確かめています（`DependencyTest`）。
- **v0.13 の経路は解決の基盤を使いません。** `engine.py` で `resolution` を使うのは、経路を選ぶ入口（`_apply`・`_kernel_options`・`apply_command_via`・`apply_command_traced`。型の注釈を含む）だけです（テストで確かめている）。v0.13 の経路の処理（`_use_attack` など）は v0.15a と同じで、比べる基準として独立しています。
- 両方の経路が使う共通の部品（`checks`・`procedures`・効果とダメージの計算・ログを書く関数）を変えると両方の経路が同じように変わるので、同じ木の中の比較では見つかりません。そのため 7 章では、固定した v0.13（`8facf3a`）の木を別のプロセスで動かして比べました。

## 5. 止める理由の文を両方の経路で同じにした

v0.14 のプロトタイプは、原典で決められない場合に v0.13 と同じコードで止めましたが、理由の文（`UnsupportedError.message`）は問いの表（`questions.QUESTIONS`）の一般的な文で、v0.13 の文（ポケモンの番号・ダメージの量・効果の名前を書く）と違っていました。既存のテストが理由の文を確かめているもの（`test_shell_attack_v0_13` の「こうらがえし」・壊れた盤面の「番の進み方の前提」）は、経路 `KERNEL` では通りませんでした。

v0.15b では、v0.13 の止める関数が作っていた理由の文を `effects` の共通の関数にし、両方の経路が使います（文の複製はない）。

| コード | 共通の関数 | 解決の基盤で文に書く値 |
|---|---|---|
| `UNRESOLVED_PREVENTED_COIN_DAMAGE` | `effects.prevented_coin_damage_error` | 受けるポケモン・無効にする効果の種類（`first_void` の効果） |
| `UNRESOLVED_EVADED_EFFECT_COIN` | `effects.evaded_effect_coin_error` | 受けるポケモン・受けなかったダメージの要素の最終ダメージ（`FrameState.evaded`） |
| `UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT` | `effects.counterattack_double_knockout_error` | 特殊能力のダメージの枠の発生源・のせたダメージ（`FrameState.applied`）・受けたポケモン |
| `UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT` | `effects.retaliation_double_knockout_error` | 返す効果の枠の発生源・枠を起こした効果（`FrameState.origin`。種類と名前）・返すダメージの最終ダメージ（`FrameState.applied`）・受けたポケモン |
| `UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT` | `effects.ko_prevention_attack_effect_error` | 受けるポケモン・ワザが相手に与える効果の要素の種類（`programs.opponent_effect_elements`。要素の並びから求める） |
| `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` | `procedures.confusion_damage_problem`（v0.15a で共通にした） | 判定も同じ関数 |
| `UNRESOLVED_REPARALYSIS_RECOVERY_TURN` | `conditions.paralysis_problem`（v0.14 から共通） | 判定も同じ関数 |

- 文に書く値は、枠の値（`FrameState` の `origin`・`applied`・`evaded`）から読みます。解決の記録（`Trace`）からは読みません（記録は結果に影響しない）。
- G37 の効果の要素の種類は、v0.13 ではワザの実装の宣言（`AttackEffect.opponent_effect_elements`）でしたが、解決の基盤では要素の並びから求めます（特殊状態の要素の種類・入れ替えの要素）。登録されたすべてのワザで両者が同じことをテストで確かめています（`DispatchTest.test_opponent_effect_elements_come_from_the_program`）。
- 文の値がコインの結果で変わる場合（こうらがえしで返すダメージ）、v0.13 は「同じコインの結果でいっしょに起こるダメージの組」（`DamageProfile.pairs()`）の順に最初に当たった組の値を書き、先読み `derived` は試した順（コインは「うら」から。辞書順）に最初に当たった結果の値を書きます。今の対応カードでは、どちらも「当たる結果のうち、相手へのダメージがいちばん小さいもの」になります（ダメージの組は「おもて」の数の小さい順で、当たる条件は「おもて」の数について単調）。v0.14 の止める場合の盤面と、コインの結果で返す量が変わる盤面（みだれづき・ハリケーンパンチとこうらがえし・みだれづきとはんげき）の 97 の盤面（v0.13 の経路で止めるのは 43）を、両方の経路・2 つの先読みで比べ、例外の種類・コード・理由の文がすべて同じでした（`MessageTest`。不変条件を満たす盤面だけ）。
- 枠の表（`events.SPAWNS`）にない連鎖で止めるときの `RuntimeError` に、規定から起こらない理由（`events.SPAWN_REFUSALS`。返すダメージで返す効果がはたらかないのは番の進み方の前提による。v0.13 の S45）を書くようにしました。v0.13 の経路の同じ場合の文と同じ前提を書きます。

確認した事実: 理由の文を共通の関数にした変更で、v0.13 の経路の文は変わっていません（7 章の固定した v0.13 との比較で、拒否の理由の文の指紋も比べた）。

## 6. テストの変更

- 新しいテスト tests/test_kernel_integration_v0_15.py（21 件）: 経路の選び方（`RouteTest`）・依存の向き（`DependencyTest`）・受け持つコマンドの振り分けと v0.13 の処理へのまかせ方（`DispatchTest`）・理由の文（`MessageTest`）・解決の基盤の経路の原子性（`KernelAtomicityTest`）・先読みを外しても推測で進めないこと（`KernelGuardTest`）。
- **v0.13 の経路の内部の関数を差しかえる 3 件のテストは、経路 `LEGACY` を明示しました**（確かめる内容・期待は変えていない）。標準の経路が `KERNEL` になると、差しかえた関数を通らずに処理されて、確かめたい v0.13 の経路の性質を確かめられなくなるためです。
  - tests/test_counterattack_v0_10.py `AtomicityTest.test_internal_error_after_the_counter`（`effects._remove_attacker_counters`・`effects.push_attack_decision`・`effects.poison` を差しかえる）
  - tests/test_counterattack_v0_10.py `InvariantTest.test_double_knock_out_guard_after_the_preflight`（`engine.counterattack_double_knockout_problem` を外す）
  - tests/test_transparency_v0_9.py `AtomicityTest.test_internal_error_after_the_power_coin`（`effects.put_to_sleep`・`effects.push_attack_decision` を差しかえる）

  同じ盤面で、解決の基盤の経路の同じ所（ログ・回復・入れ替えの決定（`codec.push_decision`）・特殊状態（`programs.APPLY_CONDITION`））に誤りを注入するテスト（`KernelAtomicityTest`。2 つの先読みで）と、先読みを外しても実際の処理が同じ検出で同じコードの拒否にするテスト（`KernelGuardTest`。v0.14 の 7 つの止める場合）を加えました。v0.13 の経路は、宣言の前の確認を外すと「はんげき」を与えるところで `RuntimeError` にしますが、解決の基盤は、先読みと同じ検出（きぜつの原因の枠）なので、同じコードの `UnsupportedError` で止めます（推測で進めない点は同じ）。
- 経路を指定する補助（tests/helpers.py の `apply_legacy`・`apply_kernel`）を加えました。
- v0.14 の比較のテスト（tests/test_event_kernel_v0_14.py の `Both`）と道具（`tools/event_kernel_compare.py`・`tools/engine_lockstep.py`）は、拒否の理由の文も比べるようにしました（強めた）。
- テストの数: 1,731 → 1,752。既存のテストの期待値は変えていません。

## 7. 確かめたこと（確認した事実）

（7 章の数は、このコミットのコードで得たもの。）

| 確認 | 結果 |
|---|---|
| `python3 -m unittest`（標準の経路 `LEGACY`。3.11・3.12・3.13） | どれも 1,752 件 OK（skipped 1。大きな比較の `KYUURA_COMPAT_BASE` のテスト） |
| 標準の経路を `KERNEL` にした写し（`DEFAULT_ROUTE` の 1 行だけを変えた木）で `python3 -m unittest` | 1,752 件 OK（skipped 2。1 つは上と同じ、もう 1 つは写しの横に `../kyuura` の clone がないため（`test_cards` の写しの照合）。経路によるものではない） |
| 固定した v0.13（`8facf3a` を `git archive` で取り出した木。A）と、この木の経路 `LEGACY`（B）・経路 `KERNEL` の先読み `derived`（C1）・`legacy`（C2）を、別々のプロセス（`python3 -I`）で同じ対戦を進めて比べた（`tools/engine_lockstep.py`。対戦のテストの方針 23 × seed 0〜99 と、ストレス実行 26 組 × seed 0〜9（拒否されるコマンドを 5% 混ぜる）。7 歩ごとに状態を pickle で保存・復元してから続けた） | 2,560 対戦・350,533 歩（うち経路 `KERNEL` が受け持つ種類のコマンド 140,707。拒否 53,809、うち原典で決められない場合の拒否 3,669）で、A と B・C1・C2 のどれも、すべての歩で、受け付けたか・拒否の例外の種類とコードと理由の文の指紋・書き出しの形式 9 の全体の指紋（ログ・乱数の指紋・決定を含む）・対戦の始めの状態の指紋が同じ（食い違い 0）。保存・復元は各 41,228 回 |
| 同じプロセスの中で、経路 `LEGACY` と経路 `KERNEL`（2 つの先読み）を 1 歩ごとに比べ、`KERNEL` の結果の状態から交互に続けた（`tools/event_kernel_compare.py --mode both --mixed`） | 対戦のテストの方針 23 × seed 0〜19 と、ストレス実行 26 組 × seed 0〜9（`--stress-seeds 10 --natural-seeds 20`）。720 対戦・127,250 歩（うち受け持つ種類 46,314）で食い違い 0（拒否の理由の文も比べた） |
| `ruff check --select F,E9 .` | 問題なし |

### 比較で見つかった、v0.13 からある理由の文の揺れ

最初の記録（文字列のハッシュの乱数化を止めていないプロセス）では、A と C1・C2 の間で 130 歩が食い違いました。どれも、決定への答えを
段階の違いで拒否する `WRONG_PHASE` の理由の文だけの違い（例外の種類・コード・状態は同じ）でした。原因は v0.13 の文の作り方です。
`checks.require_phase`（v0.13 の `engine._require_phase`）は、許す段階を引数の順に並べて書き、決定への答えでは `frozenset` の
`decisions.DECISION_PHASES` を渡しています。`frozenset` の並びは文字列のハッシュで決まり、ハッシュはプロセスごとに乱数化されるので、
同じ v0.13 の木でもプロセスによって「take_prize, decision, promote_active」のように並びが変わります（確認した事実: 固定した v0.13 の木で
6 回起動して 4 通りの並び）。A と B は偶然同じ並びでした。経路による違いではありません。

- v0.15 ではエンジンの文を変えていません（v0.13 と同じ動きを保つため）。比べる道具（`tools/engine_lockstep.py record`）は、ハッシュの
  乱数化を止めたプロセス（`PYTHONHASHSEED=0`。乱数化されていれば自分を起動し直す）で記録するようにし、7 章の表の比較はそれで行いました。
- 状態・ログ・乱数には影響しません（ログ・書き出しに `frozenset` の並びは入らない。形式 9 の全体の指紋はどの記録でも同じ）。
- v0.16 への提案: `DECISION_PHASES` を並びの決まった値にする（理由の文が変わるので、v0.13 との比較の基準をそのときに決める）。

## 8. v0.15b でしていないこと

- 標準の経路の切り替え（v0.15d。全体の検証のあと）。
- 先読みの効率化・上限（v0.15c）。
- v0.13 の経路の削除（v0.16 の候補）。
- 解決の基盤に残る v0.13 の処理の写し: 回復（`programs.Drain`。v0.13 の `effects._remove_attacker_counters` と同じ計算）と、きぜつの処理の窓（ふしちょうの写し）は、v0.14 のまま解決の基盤の中にあります。v0.13 の経路を外すとき（v0.16）に 1 つにします。
