# 旧経路の撤去と解決の基盤の一本化の最終監査（v0.16e）

v0.16（版 0.16.0）の最終のコードを、固定した v0.13（`8facf3a`）・固定した v0.15（`aa551ab`）と、別々の木・別々のプロセスで同じ入力を与えて比べ、テスト・不変条件・変異試験・性能を確かめました。同じ木の中で旧経路と新経路を比べる方法は使っていません（v0.16b で旧経路を外したので、比べる基準は固定した前の版の木と、旧経路の結果の参照データ）。

- 前の段階: [legacy-removal-audit-v0.16a.md](legacy-removal-audit-v0.16a.md)（監査と比較の環境）・[kernel-consolidation-v0.16b.md](kernel-consolidation-v0.16b.md)（撤去）・[preflight-consolidation-v0.16c.md](preflight-consolidation-v0.16c.md)（先読み）・[legacy-test-migration-v0.16d.md](legacy-test-migration-v0.16d.md)（重複処理・テストの移行・`WRONG_PHASE`）。
- 裁定・止める条件・コード・書き出しの形式 9・ログ・乱数の使い方は変えていません（4 章で確かめた）。

## 1. 結論

| 項目 | 結果 |
|---|---|
| 判定 | **完了**（旧ワザ解決経路はない。v0.13 の止める関数は、限定的な互換の部品 `resolution/v013_checks.py` に、理由と外す条件を書いて残した。9 章） |
| 固定した v0.13 との比較 | 2,560 対戦・350,533 歩で食い違い 0。許した差は決定への答えの `WRONG_PHASE` の理由の文の段階の並び 202 件だけ（3 章） |
| 固定した v0.15 との比較 | 同じく食い違い 0・許した差 202 件（同じ 202 件） |
| テスト | Python 3.11・3.12・3.13 で 1,819 件が通る（飛ばすのは 1 件で v0.15 と同じ）。v0.15 の 1,780 件から、加えた 45・外した 6（どれも置きかえ） |
| 不変条件・変異試験 | 不変条件 1〜12 を、ふだんのテストに加えて 43,520 歩（対戦のテストの方針 23 × 10 seed・ストレス実行 26 組 × 5 seed）で確かめ、違反 0。34 の変異（v0.15d の 20 を合わせたものと、旧経路の撤去を狙った 14）をすべて見つけた |
| 性能 | 固定した v0.13 の 1.28 倍（解決の基盤が受け持つコマンド全体）・1.46 倍（受け付けたワザ）。目標（1.5 倍・2.0 倍以内）を満たす。v0.15 より 7〜8% 速い（6 章） |

## 2. 比べた木と方法

| 記号 | 木 | 作り方 | 使う入口 |
|---|---|---|---|
| A | 固定した v0.13（`8facf3aeac35d3473ab382ad49b77062f86fd492`。版 0.13.0） | `tools/engine_lockstep.py tree --commit 8facf3a`（`git archive`） | 公開の `apply_command` |
| B | 固定した v0.15（`aa551ab0601e916c3fae3195780eb0aa07761deb`。版 0.15.0） | `tools/engine_lockstep.py tree --commit aa551ab` | 公開の `apply_command`（標準の経路 `KERNEL`） |
| C | v0.16 の最終のコード（版 0.16.0。作業ツリー） | — | 公開の `apply_command`（先読み `derived`） |
| Cf | C | — | 内部の入口 `apply_command_with(..., preflight="derived_full")` |
| Cl | C | — | 内部の入口 `apply_command_with(..., preflight="legacy")`（v0.13 の止める関数。`v013_checks`） |

- 記録（`tools/engine_lockstep.py record`）は木ごとに別のプロセス（`python3 -I`、`PYTHONHASHSEED=0`）で、その木の `kyuura_engine` だけを読み込みます。1 歩ごとに、コマンドの指紋・受け付けたか・拒否なら例外の種類とコードと理由の文の指紋（決定への答えの `WRONG_PHASE` は文そのものも）・受け付けたら書き出しの形式 9 の全体の指紋を記録します。形式 9 には、状態のすべての項目（場・手札・トラッシュ・サイド・持続する効果・特殊状態・ついているトレーナー）・公開のログ・乱数の指紋・保留中の決定・きぜつ・勝敗・止めた理由が入っています。7 歩ごとに状態を pickle で保存・復元してから続けます。
- 対戦の集まり: 対戦のテストの方針 23 × seed 0〜99（`play_game`）と、ストレス実行 26 組 × seed 0〜9（`choose_command`。拒否されるコマンドを 5% 混ぜる）。方針のファイル（23 の対戦のテストのモジュール・`tools/stress_engine.py`・`tools/compat_driver.py`・`tests/log_audit.py`）は 3 つの木で同じ内容（sha256 が同じ）。`tests/helpers.py` は、v0.15 で加えた入口（`apply_kernel` など）だけが違い、対戦の方針が使う部分は同じ。
- 比較（`compare`）は対戦ごと・歩ごとに記録が同じかを確かめ、違えば最初の食い違いを報告します。許すのは、同じ歩・同じコマンドで、どちらも `IllegalActionError`・`WRONG_PHASE`、今の段階が同じで、並べた段階の名前の集まりが同じ（並びだけが違う）理由の文だけです（文そのものと記録した指紋の一致も確かめる。tests/test_lockstep_tool_v0_16.py）。歩の数が違う対戦は食い違いです。

## 3. 比較の結果

| 比較 | 対戦 | 一致した歩 | 食い違い | 許した差 |
|---|---|---|---|---|
| A（v0.13）と C（v0.16） | 2,560 | 350,533 | **0** | 202（`WRONG_PHASE` の段階の名前の並び） |
| B（v0.15）と C（v0.16） | 2,560 | 350,533 | **0** | 202（同上） |
| A と B（基準どうし） | 2,560 | 350,533 | 0 | 0 |
| A と Cf・A と Cl | 2,560 | 350,533 | 0 | 202（同上） |
| B と Cf・B と Cl | 2,560 | 350,533 | 0 | 202（同上） |
| C と Cf・C と Cl（先読みの方法どうし） | 2,560 | 350,533 | 0 | 0 |

記録の数（5 つの記録で同じ）: 歩 350,533・解決の基盤が受け持つ種類のコマンド 140,707・拒否 53,809・保存と復元 41,228・対戦のテスト自身の確認の失敗 0。どの対戦も、同じ seed で歩の数が同じ（歩の数が違えば食い違いとして数える）。

原典で決められない場合の拒否（5 つの記録で同じ数・同じ歩）: `UNRESOLVED_POTION_WITHOUT_DAMAGE` 2,101、`UNRESOLVED_POTION_UNDAMAGED_TARGET` 644、`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH` 340、`UNRESOLVED_EVADED_EFFECT_COIN` 219、`UNRESOLVED_SWITCH_WITHOUT_BENCH` 179、`UNRESOLVED_PREVENTED_COIN_DAMAGE` 88、`UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT` 42、`UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT` 38、`UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` 14、`UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT` 4（合わせて 3,669。v0.15d の比較と同じ）。

### 3.1 許した差（`WRONG_PHASE`）の確かめ

`WRONG_PHASE` の拒否は 3 つの記録とも 1,395 件で、そのうち決定への答えの拒否（理由の文に 3 つの段階を並べるもの）が 202 件（`main` で 198・`setup_first_player` で 2・`setup_placement` で 2）です。A・B（`PYTHONHASHSEED=0`）の文は「… decision, take_prize, promote_active のときだけ」、C は「… take_prize, promote_active, decision のときだけ」で、許した差の 202 件はこの 202 件とちょうど同じです。ほかの 1,193 件の `WRONG_PHASE` の文は 3 つの記録で同じです。原因は v0.16d の `decisions.DECISION_PHASE_ORDER`（コミット `0618e1c`。[legacy-test-migration-v0.16d.md](legacy-test-migration-v0.16d.md) 5 章）で、例外の種類・コード・受け付ける段階・状態・ログ・乱数は同じです。

### 3.2 共通の部品の変異が比較で見つかること

両方の版が使う共通の部品（`conditions.CONFUSION_DAMAGE`。こんらんの 20）を 30 にした写しを、固定した v0.13（A）と比べると、10 対戦のうち 2 対戦で食い違いを見つけた（`test_confusion_games` の seed 1 の 124 歩目・seed 8 の 113 歩目。v0.15d の同じ確かめと同じ位置）。旧経路を外したあとも、固定した前の版の木との比較が、共通の部品の誤りを見つけることを確かめた（同じ木の中の比較には頼らない）。

### 3.3 前の版との比較の駆動（v0.4e からの道具）

`tools/compare_engine_versions.py`（v0.4e からの比較の駆動。公開の API だけを使い、形式 1〜8 の書き出しも比べる）で、基準を固定した v0.13（`--base 8facf3a`）と固定した v0.15（`--base aa551ab`）にして、今の木と比べた: どちらも 50 対戦・記録 11,377（受け付けた 6,005・拒否 5,322・内部の誤り 0）・書き出し 91,016 で食い違い 0。v0.4d の参照データ（tests/fixtures/compat_base_4bd97bf.json）・v0.1 の参照データ（tests/fixtures/v0_1_reference.json）との比較もふだんのテストで通る（作り直していない）。

## 4. テスト

| 確認 | 結果 |
|---|---|
| `python3 -m unittest`（段階 A・B） | Python 3.11・3.12・3.13 で 1,819 件が通る（skipped 1: tests/test_cross_version_compatibility.py の大きな比較。`KYUURA_COMPAT_BASE` を設定したときだけ。v0.15 と同じ）。1 回の時間は 428〜460 秒 |
| 既存のテストと新しいテスト | v0.15 の 1,780 件から、加えた 45（参照データ 5・比較の道具 6・アダプタ 11・入口と依存の置きかえ 6・先読みの整理 14・`WRONG_PHASE` 3）、外した 6（どれも置きかえ。対応表は [legacy-test-migration-v0.16d.md](legacy-test-migration-v0.16d.md) 6・8 章） |
| ruff（`ruff check --select F,E9 .`） | 指摘なし |
| カードデータの照合（`scripts/extract_kyuura_cards.py --kyuura ../kyuura --check`） | 写しは kyuura の `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691` と一致。kyuura の clone は変更なし（`git status` が空） |
| ログの監査（tests/log_audit.py） | ふだんのテストの対戦（new_game からの対戦のテスト・ストレス実行の小さな実行）で、ダメージ・エネルギー・トラッシュ・サイド・手札・特殊状態の組み立て直しと状態が一致する |
| 書き出しの監査（`serialization_problems`） | 形式 1〜9 で一致（形式 9 のまま。`LATEST_FORMAT` 9） |
| ストレス実行（`tools/stress_engine.py`。既定: 26 組 × 40 seed・600 歩・拒否 5%・書き出しの確かめ） | 1,040 対戦・受け付けた 146,556・できない 162,321・未対応 0・原典で決められない（拒否）9,824・HALTED 35・GAME_OVER 888・内部の誤り 0。**分類したすべての数が v0.15d の実行と同じ**（ポケモンパワー・はんげき・こんじょう・ふしちょう・ほのおのかべ・こうらがえしの数を含む） |
| 先読みの方法どうしの比較（`tools/event_kernel_compare.py --mode all --mixed`。対戦のテストの方針 23 × seed 0〜19・ストレス実行 26 組 × seed 0〜9、交互の状態） | 食い違い 0 |
| API の互換性 | 公開の `apply_command` の呼び方・公開の名前（`EntryTest`）、v0.1・v0.4d の参照データ、`compare_engine_versions.py`（3.3 節）。`UsePokemonPower` の v0.4e の辞書なども既存のテストで通る |

## 5. 変異試験

最終のコードに 1 か所ずつ誤りを入れた写し（34 個）で、テスト（解決の基盤・先読み・アダプタ・決定・効果・対戦のテストなど 26 モジュール）が失敗するかを確かめました（変異の一覧と置きかえる文字列は、このリポジトリの外の試験用のスクリプトに置いた。v0.15d と同じ方法）。M01〜M20 は v0.15d の変異を v0.16 のコードに合わせたもの（M12・M15・M19・M20 は、置きかえる所が v0.16b〜v0.16d で変わったので、同じ種類の誤りを今の場所に入れた）、R01〜R14 は旧経路の撤去で起こりやすい誤り（アダプタ・枠の入口・決定の再開・`v013_checks`・先読みの数え方・`WRONG_PHASE`・重複を統合した処理）を狙ったものです。

| 変異 | 入れた誤り | 見つけたテスト |
|---|---|---|


確認した事実: **34 の変異のすべてをテストが見つけた**（見つけなかった変異は 0）。R07（`WRONG_PHASE` の並びを集合の並びにもどす）は、`PYTHONHASHSEED` を変えた別のプロセスの確かめ（tests/test_wrong_phase_message_v0_16d.py）が見つける。R13（補助関数が枠の外でも何もせずに進む）・R03（アダプタが別の状態を受け付ける）は、v0.16b で加えたアダプタのテストだけが見つける（ほかのテストは枠の中で補助関数を呼ぶ）。

## 6. 性能

最終のコード（C）を、v0.15d と同じ方法（同じ機械・Python 3.13.16・別々のプロセス・ほかの処理なし・対戦のテストの方針 23 × seed 0〜19 とストレス実行 26 組 × seed 0〜2・A → B → C を 3 回くり返した中央値。`tools/engine_lockstep.py record --timing`。時間は `apply_command` の呼び出しだけ）で測りました（確認した事実。ミリ秒）。

| コマンド | A（v0.13） | B（v0.15） | C（v0.16） | 3 回の値 |
|---|---|---|---|---|
| 対象コマンド全体（31,152 回） | 0.300 | 0.412（1.37×） | **0.383（1.28×）** | A [0.2985, 0.3, 0.3078]・B [0.3987, 0.4129, 0.4121]・C [0.3807, 0.3831, 0.4075] |
| 受け付けたワザ（12,799 回） | 0.390 | 0.617（1.58×） | **0.568（1.46×）** | A [0.387, 0.39, 0.4035]・B [0.5932, 0.617, 0.6179]・C [0.5618, 0.5677, 0.6077] |
| ワザ（拒否を含む）（16,552 回） | 0.319 | 0.502（1.58×） | 0.462（1.45×） | A [0.3163, 0.3188, 0.3296]・B [0.4842, 0.5024, 0.5037]・C [0.4573, 0.4616, 0.4946] |
| 番の終わり（8,798 回） | 0.289 | 0.309（1.07×） | 0.299（1.03×） | A [0.289, 0.2869, 0.2892]・B [0.3073, 0.3113, 0.3095]・C [0.2987, 0.2972, 0.3149] |
| 決定への答え（5,802 回） | 0.266 | 0.306（1.15×） | 0.289（1.09×） | A [0.262, 0.266, 0.2738]・B [0.2936, 0.3115, 0.3064]・C [0.2868, 0.2893, 0.2994] |

- 目標（対象コマンド全体で v0.13 の 1.5 倍以内・受け付けたワザで 2.0 倍以内）を満たす（1.28 倍・1.46 倍）。
- v0.15 からの退行はない（C は B の 0.92〜0.97 倍）。速くなったのは、振り分けで経路と対応表を確かめる処理（`resolution.handles`・`Route`）を外したことと、ワザの入口が 1 つになったことによる（推定。測った事実は上の値）。
- B の倍率は v0.15d の測定（1.32 倍・1.48 倍）より少し大きい（同じ方法で、機械の状態による揺れ。比べるのは同じ回に測った A・B・C の値）。

## 7. 独立した不変条件（重点）

解決の基盤の独立した不変条件 1〜12（tests/test_kernel_invariants_v0_15.py。[event-integration-verification-v0.15d.md](event-integration-verification-v0.15d.md) 4 章）を、ふだんのテスト（特殊能力・持続する効果がはたらく対戦のテストの方針 8 つ × seed 0〜9、ストレス実行 26 組 × seed 0〜1）に加えて、広い対戦の集まりで確かめました（C 段階。同じ `Recorder` を使う）。

| 対戦の集まり | 歩 | 解決の基盤が受け持ったコマンド | 発動 | 開いた枠 | 解決の基盤の決定を待つ状態 | 拒否 | 原典で決められない場合の拒否 | 違反 |
|---|---|---|---|---|---|---|---|---|
| 対戦のテストの方針 23 × seed 0〜9 | 25,779 | 11,181 | 90 | 6,000 | 2,661 | 1,755 | 31 | **0** |
| ストレス実行 26 組 × seed 0〜4（拒否 5%） | 17,741 | 7,447 | 56 | 2,290 | 943 | 15,892 | 14 | **0** |

依頼の重点と、確かめているもの:

| 重点 | 確かめているもの |
|---|---|
| 処理窓の順序 | 不変条件 1（窓の順番）。変異 M01・M02 |
| 枠の連鎖 | 不変条件 2・3（枠の表・許されない連鎖）。変異 M01 |
| 同じ効果の重複発動 | 不変条件 4（二重の処理）。変異 M02 |
| 抑止された能力の扱い | 不変条件 5（はたらいていない特殊能力が発動しない。v0.13 の公開の問い合わせと照らす）。変異 M04 |
| 持続効果の期限 | 不変条件 6（はたらく番だけ）。tests/test_harden_v0_4b.py・test_rocket_moltres_v0_12.py・test_shell_attack_v0_13.py。変異 M05 |
| 決定による中断・再開 | 不変条件 8（決定を待つ状態）・9（保存・復元の連続性）。アダプタの 2 段階の決定（tests/test_contract_adapter_v0_16.py `DecisionTest`）。変異 M20・R04・R10 |
| 未解決裁定の停止 | 不変条件 11（受け付けた処理に問いがない）。3 章の比較（止めた数・コード・歩が同じ）。`UNRESOLVED_…` の境界のテスト。変異 M06・M07・M09・M18 |
| 原子性 | 不変条件 10（拒否で状態・乱数・ログが変わらない）。故障の注入（`KernelAtomicityTest`・`AtomicityTest`。v0.16d から注入した誤りそのものを確かめる）。変異 M08・M19 |
| 内部トレースが結果に影響しないこと | 不変条件 12（記録をとらない処理と、受け付けた状態・乱数・拒否を比べる）。変異 M17 |
| カスタムワザの扱い | tests/test_contract_adapter_v0_16.py（11 件）とテスト専用の 19 種類を使う既存のテスト。変異 M12・R01〜R05・R08・R09・R13 |
| 先読み上限とフォールバック | tests/test_preflight_consolidation_v0_16c.py・test_preflight_v0_15c.py `LimitTest`。変異 M14・M15・R06・R14 |
| 保存・復元後の動作 | 不変条件 9。3 章の比較（7 歩ごとに保存・復元。41,228 回）。tests/test_contract_adapter_v0_16.py の 2 段階の決定の保存・復元 |

## 8. 完了条件と中止条件

### 8.1 完了条件

| 完了条件 | 判定 | 根拠 |
|---|---|---|
| v0.15 の KERNEL が標準のワザ解決基盤として維持されている | 満たす | ワザ・番の終わり・きぜつのあとの決定を処理するのは `resolution` だけ（tests/test_kernel_integration_v0_15.py の `DispatchTest`・`EntryTest`） |
| 旧ワザ解決経路の重複処理が整理・削除されている | 満たす | 旧経路の 28 の名前・旧ダメージ処理境界の 7 の名前を外し、戻らないことを確かめる（`EntryTest`）。重複の調査（[legacy-test-migration-v0.16d.md](legacy-test-migration-v0.16d.md) 2 章） |
| 移行対象外のコマンドが正常に動作する | 満たす | トレーナー・特殊能力・進化・にげる・エネルギー・対戦準備は engine.py のまま、解決の基盤を使わない（`DependencyTest.test_out_of_scope_handlers_do_not_use_the_kernel`）。3 章の比較の全コマンド |
| 標準カード 24 種類が正常に動作する | 満たす | 製品の登録表のワザの実装 24 種類は、どれも要素の並び（`programs.BUILDERS`）で処理する（`DispatchTest.test_every_registered_attack_is_handled_by_the_kernel`）。3 章の比較 |
| テスト専用のカスタム効果の互換性が保護されている | 満たす | v0.13 の約束の実装 19 種類は書きかえずにアダプタで動く（tests/test_contract_adapter_v0_16.py と既存のテスト）。処理できない実装は `UNSUPPORTED_ATTACK` で拒否 |
| 先読み上限時の安全性が保証されている | 満たす | 上限を超えたら途中までの結果を使わない（`BranchLimitBoundaryTest`）。製品のワザは正しい盤面で上限に届かない（3,250 通り。`ProductBoundTest`） |
| 旧方式の事前判定を残した場合、その理由と範囲が明確である | 満たす | `resolution/v013_checks.py` の 3 つの使い道・外す条件（[preflight-consolidation-v0.16c.md](preflight-consolidation-v0.16c.md) 2・6 章）。使う所が広がらないことを確かめる（`DependencyTest`） |
| 旧経路の内部関数に依存するテストを適切に移行している | 満たす | 対応表（[legacy-test-migration-v0.16d.md](legacy-test-migration-v0.16d.md) 6 章）。外したテスト 6 件はすべて置きかえ。別の理由で通っていたテスト 1 件を見つけて直した |
| 既存の裁定と停止条件を変えていない | 満たす | 3 章（止めた数・コード・歩が同じ）。`UNRESOLVED_…` の境界のテスト（tests/test_unresolved_boundaries_v0_4e.py） |
| 公開 API を変更していない | 満たす | `apply_command(state, command)` の呼び方・公開の名前（`EntryTest.test_public_apply_command_is_unchanged`）。v0.1 の参照データ・v0.4d の参照データとの比較（4 章） |
| 保存形式 9 を変更していない | 満たす | 書き出しの形式の監査（`serialization_problems`）。3 章の比較は形式 9 の全体の指紋 |
| 公開ログと乱数の再現性を維持している | 満たす | 3 章（ログ・乱数の指紋が同じ）。tests/test_reproducibility.py の固定値を変えていない |
| 固定 v0.15 との比較で説明できない差異が 0 である | 満たす | 3 章（食い違い 0。許した差 202 件は 3.1 節で原因を確かめた） |
| 固定 v0.13 との比較で説明できない差異が 0 である | 満たす | 同上 |
| Python 3.11・3.12・3.13 でテストが成功している | 満たす | 4 章 |
| 独立した不変条件と変異試験に合格している | 満たす | 5・7 章 |
| 性能の目標を満たしている | 満たす | 6 章 |
| 削除対象と残存依存が文書化されている | 満たす | 9 章・[kernel-consolidation-v0.16b.md](kernel-consolidation-v0.16b.md) 2・5 章・[preflight-consolidation-v0.16c.md](preflight-consolidation-v0.16c.md) 6 章 |

### 8.2 中止条件

| 中止条件 | 判定 |
|---|---|
| 1. 原典で確認できない新しい裁定が必要になる | 当たらない（新しい裁定はない。T27・C34/C35 など既存の問いは止める処理のまま） |
| 2. 旧経路を削除すると、KERNEL で表現できない既存の効果がある | 当たらない（製品の 24 種類は要素の並び、v0.13 の約束の実装はアダプタ） |
| 3. 未解決裁定の停止条件が変わる | 当たらない（3 章） |
| 4. 保存形式 9 を変更する必要がある | 当たらない |
| 5. 既存テストの検証内容を弱める必要がある | 当たらない（期待を変えた 3 件は根拠つきで、確かめる内容は同じか強い。別の理由で通っていた 1 件は強めた。[legacy-test-migration-v0.16d.md](legacy-test-migration-v0.16d.md) 6.4・7 章） |
| 6. カスタムワザの互換性を維持できない | 当たらない（アダプタ。v0.13 の約束を変えていない） |
| 7. 探索上限時の安全性を保証できない | 当たらない（v0.16c。v0.15c の 4,097 通りの数え方の差は直した） |
| 8. 旧経路削除によって、比較の独立性を失う | 当たらない（固定した木と別のプロセスで比べる。旧経路の結果の参照データ） |
| 9. 原因不明の状態・ログ・乱数の差異が生じる | 当たらない（3 章） |
| 10. 性能基準を超過し、改善できない | 当たらない（6 章） |

## 9. 削除したもの・残したもの

| 区分 | 内容 |
|---|---|
| 削除した（v0.16b） | `engine.py` の旧経路の関数 24・表 `_RESUMERS`・経路（`Route`・`DEFAULT_ROUTE`・`apply_command_via`）、`effects.py` の標準の実装 24 種類の `resolve`・`resume`・旧ダメージ処理境界（`PendingCounterattack`・`PendingRetaliation`・`_apply_counterattack`・`_apply_retaliation`・`_require_damage_elements_finished`・`_skip_heal_of_knocked_out_attacker`・`_remove_attacker_counters`）、`resolution.handles` |
| 削除した（v0.16c〜d） | `preflight.legacy`・`LEGACY_VERIFIED`（`v013_checks` に移した）、実験用の互換の層（`experiments/`）、使われない解決の記録の型（`Delegated`・`ElementSkipped`） |
| コードの量 | `kyuura_engine/` は v0.15 の 12,389 行から 11,266 行（15 ファイル、+531・−1,654）。`engine.py` 2,327 → 1,784、`effects.py` 4,152 → 3,349。加えたのは `resolution/contract.py`（190 行）・`resolution/v013_checks.py`（68 行） |
| 残した（理由・外す条件） | `resolution/v013_checks.py`（v0.13 の止める関数。アダプタ・上限を超えたとき・比べる方法 `legacy` の 3 つ。[preflight-consolidation-v0.16c.md](preflight-consolidation-v0.16c.md) 6 章）。v0.13 の約束の補助関数（`deal_attack_damage`・`attack_reaches`・`finish_damage_elements`・`push_attack_decision`）と `AttackEffect.resolve`・`resume` の約束（解決の基盤に委ねる入口。外の拡張の約束なので、外すには告知が要る）。`effects` の止める関数 3 つと `damage_profile`・`preview_attack_damage`・`opponent_effect_elements` の宣言（`v013_checks` だけが使う） |
| 残る依存 | 旧経路の結果の参照データ（tests/fixtures/legacy_reference_v0_15.json）は、旧経路のある木（v0.16a）でしか作り直せない。盤面を直接作る比較のテストの呼び出しを変えるときは、同じ性質を確かめる別のテストを書く |
| まだ確かめていないこと | v0.13 の約束で書いた外の拡張（このリポジトリの外）は見つかっていない（あればアダプタで動く想定で、アダプタの試験はテスト専用の 19 種類で確かめた）。`v013_checks` の答えと `derived` の答えが同じことは、製品の 24 種類の対戦（3 章の Cl）で確かめた事実で、すべての盤面での証明ではない（上限を超える盤面は正しい対戦では起こらない） |
