# v0.143: S2a の続行規約 5 件（開発用の部分的な集合 CS-KYUURA-PLAY-S2A@1）

S2a の仕様案（[play-policy-s2a-spec.md](play-policy-s2a-spec.md)）の 5 規約を採用し、登録・準備・枚数の不足・ポケモンチェック・一括の計測（S2a-0〜4）を 1 つの作業で実装した版です。

**これは開発用の部分的な集合です。** 続行側の集合 `CS-KYUURA-PLAY-S2A@1` は 5 規約の場面だけを続け、ほかの未決の場面では今の停止コードで止まります。すべての未決の場面で止まらない完成したプレイ用の集合ではありません（完全性の主張は `halts_at_undecided`）。省略したときの集合（厳密側 `CS-KYUURA-CURRENT@1`）の中身・挙動は変えていません。

## 1. 基点と承認

- 基点: `7b1d2dd471675adb9f981d5846c8a21d6d245286`（S2a の仕様案の最後のコミット。`origin/claude/play-policy-s2a-spec`）。v0.142 の最後 `fcb8bc808d65a136264e855818475e3cb2773535` を祖先に含み、エンジン・テスト・道具は fcb8bc8 と同じ（仕様案のスクリプト・テスト・文書だけが違う）。
- `origin/main` は `816bcffb86edeb3ea713ee08818a070e036fe0a8`（v0.140。v0.141・共通規約の設計案・v0.142・S2a の仕様案を含まない）。S1 と S2a の仕様案の両方を含む公開済みのコミットは 7b1d2dd だけなので、これを基点にした。
- 作業ブランチ: `claude/play-policy-s2a-impl`。利用者の `.claude/` はコミットに入れていない。kyuura は読むだけ（研究の対応表の照合 `check_research_links.py`）。

承認は 3 つを分けて記録します。

| 記録 | 状態 | 中身 |
|---|---|---|
| 進め方の承認（2026-11-04） | user_agreed | 仕様案 2 章。基礎集合の全仮定の採否を先に終えない・S2a の事例から接続する・5 規約を一組で具体化する |
| 具体的な続行仕様の承認（仕様案の時点） | not_approved | 仕様案 2 章。提案の時点の記録のまま（書き換えていない） |
| 具体的な続行仕様の採用（この版） | user_agreed | 利用者の指示「5規約をまとめて採用し、S2a-0〜4を一つの実装タスクとして進める案を採用します。」と、その依頼の採用仕様。仕様案 13 章・台帳の `continuation_agreements`（AGR-PLAY-S2A-*） |

採用は**続行側の集合の規約の採用**で、公式の裁定・エラッタ・kyuura の研究上の解決ではありません。研究上の未解決（PF1・Z29・KK1・UQ-STATED-COUNT-SHORT・PK1 ほか）は未解決のままです。未承認の仮定（CB-IMPLEMENTATION-ASSUMPTIONS）は未承認のままです。台帳の判断事項は DEC-MULLIGAN-COMPENSATION・DEC-PLAY-AS-POKEMON・DEC-SLEEP-COIN-ORDER・DEC-STATED-COUNT-SHORT・DEC-KNOCKOUT-READINGS を `partly_agreed`（続行側の対象の場面だけ）にしました。DEC-ORDER-RULE（一般の同時効果）・DEC-DEFERRED-RESUME は未決のままです。

## 2. 集合と規約

| 集合 | 区分 | 完全性 | 規約 |
|---|---|---|---|
| `CS-KYUURA-CURRENT@1`（厳密側・既定） | standard | halts_at_undecided | 利用者の指定 11・CB-IMPLEMENTATION-ASSUMPTIONS（v0.142 と同じ。照合値も同じ） |
| `CS-KYUURA-PLAY-S2A@1`（続行側） | development | halts_at_undecided | 上の 12 件と、続行規約 5 件 @1 |

- 続行規約 5 件は層 `continuation`・承認 `user_agreed`。意味の内容（`content`。対象・処理・変えないもの）と場面（停止の方針の台帳の場面 ID）を照合値に入れ、`PINNED_CONVENTION_DIGESTS`・`PINNED_SET_DIGESTS` に固定した。根拠の文書は `references`（照合値に入れない）。
- 5 規約は互いに `requires`・`conflicts` を持たず、場面は重ならない。集合の確かめ（`validate`）に、続行規約の場面が台帳の場面にあること・場面のない続行規約を受け付けないことを加えた。
- この版のエンジンが処理を持つ続行規約は `IMPLEMENTED_CONTINUATIONS`（5 件）。規約の一部だけの集合は試験の登録表でだけ作る（同梱しない）。
- 規約の意味を変えたら規約の版を上げ、それを含む集合も新しい版にする（S1 の方針のまま）。この版のあとの不具合の修正（監査・道具）は規約の意味を変えていない。

## 3. 照会と規約を当てた記録

- `conventions.continuation_for(state, code, case=None)`: 止める理由を作る分岐の手前の照会。状態の規約集合に、その場面の続行規約があり、この版が処理を持てば照会の結果を返し、なければ None（呼ぶ側は今までどおり止める）。2 つ以上の事例があるコードで事例を渡さなければ、コードだけで規約を決めない。
- `conventions.stop_without_continuation`（S1）は止める直前の確かめのまま残す。続行規約のある場面で止めようとしたら、エンジンの不具合（`RuntimeError`）。停止の例外を捕まえて続ける構造にはしていない。
- `conventions.record_application`: ログ `convention_applied`（`convention`・`version`・`scene`・`code` と、規約ごとの公開の値。書ける項目は `APPLIED_FIELDS` に限る）。観測では全員に見える（`observation.PUBLIC_EVENTS`）。手札・山札などの秘密の情報は書かない。
- 規約が実際に処理を決めたとき（厳密側なら止める場面）だけ書く。先読み・答えの確かめ・拒否した操作は状態の複製の上なので、記録は残らない。配置の拒否（4.2）は状態を変えない拒否なので記録しない。
- `engine.py`・`procedures.py`・`interruption.py`・`resolution/` に、カード ID・モードの名前の分岐は加えていない（停止コードと事例だけで引く）。

| 規約 | 記録の値 |
|---|---|
| PC-SETUP-MULLIGAN-COUNT | `rounds_both`（両方の回の数）・`rounds_single`（片方だけの回の数）・`player`（補償を受けるプレイヤー） |
| PC-SETUP-PLAY-AS-POKEMON | `players`（化石・人形があり、たね・ベイビィのない手札のプレイヤー。このあと手札を見せて切り直す） |
| PC-CHECK-SIDE-ORDER | `order`（番を終えたプレイヤー → 相手） |
| PC-COIN-COUNT-SHORT | `element`・`heads`（H）・`available`（N）・`processed`（min(H, N)）・`source`・`player`・`target_owner`・`target` |
| PC-CHECK-KO-POINT | `pokemon_ids`（1 のあとに HP 以上のポケモン） |

## 4. 規約ごとの実装と例外

### 4.1 PC-SETUP-MULLIGAN-COUNT@1（切り直しの補償）

- 場面: `UNRESOLVED_MULLIGAN_COMPENSATION#initial-setup`・`#sudden-death-segment`（`engine._deal_opening_hands`。延長戦の区間も同じ関数）。
- 両方の回のあとに片方だけの回がある並びで、片方だけの回の数 m を、もう一方のプレイヤーの補償の回数にする（両方の回は数えない）。1 回の補償は今の `DrawMulliganCards`（0〜2 枚。山札の枚数まで。受けるプレイヤーが選ぶ）、時点はサイドを置いたあと・ジャンケンの前（今と同じ）。新しい決定・乱数の消費はない。
- 両方の回だけ・片方だけの回だけの切り直しは今と同じ（記録を書かない）。補償で引いたたね・ベイビィは手札に加わるだけ（配置は終わっている。回に数えない）。

### 4.2 PC-SETUP-PLAY-AS-POKEMON@1（化石・人形の初手）

- 場面: `UNRESOLVED_PLAY_AS_POKEMON_SETUP#initial-setup`・`#sudden-death-segment`・`#setup-placement`（`engine._deal_opening_hands`・`engine._place_starting_pokemon`）。`#setup-placement` はこの版で台帳に加えた事例（仕様案の proposed_cases）。
- 対象は効果の登録の型 `PlayAsPokemon`（`effects.play_as_pokemon_in_hand`）で識別する。今の対象がなにかの化石（PMCG3-046）とピッピ人形（PMCG1-091）だけであることは、テスト（`test_target_cards_by_registration`）と仕様案の `--check` が照合する。
- 化石・人形を初手のたねポケモンに数えず、ほかにたね・ベイビィがなければ今の切り直しと同じく切り直す（手札を見せる・山札にもどす・切る・7 枚）。切り直しの回にも数える（4.1 と組み合わさる）。
- 準備の配置で化石・人形を選ぶと、続行側は `IllegalActionError`（`NOT_BASIC_POKEMON`。たねポケモンでないカードの既存の拒否と同じコード。理由の文に規約 ID）。未解決による停止（厳密側の `UnsupportedError` `UNRESOLVED_PLAY_AS_POKEMON_SETUP`）とは区別する。入力の状態・乱数・ログは変えない。
- 対戦が始まってからベンチに出す処理（v0.47）・ベイビィの初手の規則・にげる（PF2）・育て屋（PF3）・ちえくらべ（MG2）は変えていない。

### 4.3 PC-CHECK-SIDE-ORDER@1（ポケモンチェックの両側コイン）

- 場面: `UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`（両方の対戦ポケモンがねむり）・`UNRESOLVED_POKEMON_CHECK_CHAR_COIN_ORDER`（両方の場にくろこげマーカー）。
- 番を終えたプレイヤー（ポケモンチェックの直前の番のプレイヤー）の場から、次に相手の場。それぞれの場はバトル場 → ベンチ。順番を選ぶ決定は出さない。今のログの順と同じで、チェックの段階の順序は変えない。
- ねむりは 1 枚（1 匹）ずつ結果を反映する（コインの枚数は投げる直前の場の［ふかいねむり］で決める）。
- 技術的な安全の確かめ（規約そのものではない）: ねむりの回復の結果のすべての組（両方・片方ずつの 3 通り。この番に回復するマヒも続けて）を複製の上で規約の順に処理し、どの組の途中でも回復の止め方（MH1・TF1・TF2・DG1。`effects.state_stop_after`）にならないことをコインの前に確かめる。止める組があれば、コインの前にその停止コードで止める（1 匹のときと同じ形）。両方の組だけで止まる盤面は作れていない（制限: 到達可能性は未確認）。結果の分かれ方は公開のコインだけで決まり、秘密の情報で受理・拒否が変わる問い合わせはない。
- くろこげマーカーは今のコインの前の確かめ（すべての結果の組で 1・2 の確かめ）と上限（6 枚。`UNSUPPORTED_POKEMON_CHECK_CHAR_COINS`）をそのまま使う。
- 除外: きのみの順番（BY1）・コインの技術的上限・両方のきぜつ・一般の同時効果・採用済みのサイドを取る順番。

### 4.4 PC-COIN-COUNT-SHORT@1（コインで決まる枚数の不足）

- 場面: `UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT`（ファイヤーのドライアップ。DU1）・`UNRESOLVED_THOUGHT_WAVE_MACHINE_ENERGY_SHORT`（怪電波マシーン。TW1）。
- 共通のチェック地点 `interruption.check_quantity(state, required=H, available=N, …)` は処理する数を返す形にした。H ≤ N は H（今と同じ）。H > N は、続行規約があれば記録を書いて N（min(H, N)）、なければ今の途中停止（`DeferredShortage`）。カードの登録は返した数で今の H = N の経路を通る（ドライアップはワザの終わりへ、怪電波マシーンは N 枚を手札にもどしてカードをトラッシュし、番を終える）。
- H は丸めずにコインのログと記録に残し、コインを途中で打ち切らない。ナツメのESPのやり直しは最後に確定した並びで判断する。選ぶ人・対象の判定・防護と無効化は今のまま。N = 0（ドライアップ）は何もトラッシュしない。
- 先読みの組（`programs.shortage_classes`）は変えていない（h > N の組は、どれも N 枚を処理して同じに続く。h はログにだけ残る）。
- 除外: TW2 など使う前の使用条件・選んだ対象の別の未決事項・途中停止した状態の再開（厳密側で途中停止した状態は、続行側の規約で再開しない）・ほかのカードへの一般化・ひかるバンギラスの利用者の指定。

### 4.5 PC-CHECK-KO-POINT@1（ポケモンチェックでのきぜつ判定）

- 場面: `UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT`（PK1。`procedures._pokemon_check_plan`）。
- 1（くろこげマーカーのコイン・悪エネルギー・くろこげの 20・きのみ）と 2（どく）のあとに 1 回だけきぜつを判定する。HP 以上になったポケモンも判定まで場に残り、どくのダメージなど後続の処理を受ける。今の処理がこの順なので、処理は書き換えていない（止める分岐を規約で外すだけ）。
- 違いの判定（`mid_check_knockout_divergence`）は規約があっても呼び、厳密側が止める場面だけを規約の適用として記録する（仕様案は「呼ばない」としていた。処理の結果は同じ）。
- **保守的な制限（この版で見つけた）**: 場に残る読み方で 2 のあとにきぜつさせると、そのきぜつで場をはなれるポケモンのために受け付けられない状態（TK1: 写していたポケモンがきぜつしてメタモンの姿がもどり HP がダメージ以下になる、SC2: かがくへんかガスの発生源がきぜつして残りHP「10」の［ずらかる］の力がもどる、MH1・決められない姿）になる場面がある。その停止はきぜつの処理（ダメージのあと）に起こり、HP 以上のポケモンが場に残った止まった状態になる（内部エラーになる）ので、続行側では規約を当てず、ダメージの前にその停止コード（TK1・SC2 など）で止める（`procedures._knockout_stop`）。仕様案の「違いを返す 2 つの条件はどちらも場に残る読み方で決まる」は、きぜつの処理のあとの停止を見ていなかった。
- 除外: 両方のきぜつ・SC1・AL1・AL3・PO1〜PO3・KA1・VS1・DE1・BY1（今のまま止まる）。

### 4.6 規約のあいだの関係

対象の事例は重なりませんが、実行では組み合わさります。

- 化石・人形の切り直しの回が、両方 → 片方の並び（4.1）を作る。両方の規約のある集合では続き、化石・人形の規約だけの開発用の集合（試験の登録表）では `UNRESOLVED_MULLIGAN_COMPENSATION` で止まる（`test_combination_without_mulligan_rule_still_halts`）。
- くろこげマーカーのコインの前の確かめは、同じ集合のきぜつ判定の規約を使う。両側のコインの規約だけの集合（試験の登録表）では、PK1 の組がコインの前に止める理由になる（`test_side_order_and_ko_point_together`）。

## 5. 保存・観測・ログ

- 書き出しの形式は 35 のまま（新しい項目はない。ログの種類 `convention_applied` が増えただけ）。形式 34 以前には続行側の集合を表せないので `ValueError`（黙って厳密側の集合にしない。S1 の `IMPLICIT_IN_OLD_FORMATS`）。
- 集合は複製・pickle・決定待ち・延長戦で保たれる（S1 の不変条件。延長戦の準備の規約の適用を `SuddenDeathSegmentTest` で確かめた）。対戦の中で集合を切り替える操作は加えていない。
- 観測は `convention_set` の識別が変わるだけ（S1）。`convention_applied` は全員に同じ値で見える。

## 6. 監査

- `tests/log_audit.py` の `s2a_problems`: エンジンの記録・登録を読まずに、監査が独立に持つ表（規約 ID・版・場面・書いてよい項目・化石と人形のカードの一覧）とログから組み立てて照らす。準備（区間ごとに切り直しを回に分けて k・m を数え、補償の記録・補償の権利・化石と人形の手札の切り直しの前の記録）、ポケモンチェック（両方のプレイヤーのコインの前の記録と順番、きぜつ判定の記録の位置とそのチェックでのきぜつ）、枚数の不足の記録の場所、状態の集合にない規約の記録・決めていない項目を見つける。
- `v127_problems` は、枚数の不足の記録があれば、処理した数が記録の N（H > N）であることを確かめる（記録がなければ v0.127 と同じく H）。厳密側の確かめは緩めていない。
- 計測で見つけた監査の誤検出 1 件: 「同じサイドのカードを 2 回取った」。取ったサイドのカードが手札から山札にもどり、山札の上とサイドを入れかえる特殊能力（PMCG4-045。入れかえたカードの uid は秘密でログにない）でサイドに置かれて、もう一度取られた（v0.47 F47-H47 seed 2。化石の手札の切り直しのあとに初めて最後まで進んだ対戦）。エンジンの誤りではない。入れかえのない 2 回目の取得は今までどおり見つける（`_retaken_without_return`。回帰テスト `test_prize_retaken_after_deck_top_swap_is_not_flagged`）。

## 7. 道具

- `tools/existing_effect_games.py`・`tools/sudden_death_games.py` に `--conventions ID@版` を加えた（`tools/convention_choice.py`。道具だけの選び方で、エンジンの既定は変えない。監査のやり直しも同じ集合で始める）。局ごとの記録に `conventions_applied`（規約・場面ごとの回数。記録のない局は項目を書かない）。
- `tools/engine_lockstep.py` の指紋は形式 9 の書き出しなので、続行側の集合の対戦は記録できない（形式 34 以前は続行側の集合を表せない）。厳密 対 続行の比べは、計測の局を両方の集合でやり直してログを比べる別の確かめで行った（8 章）。

## 8. 一括の計測（S2a-4）

組・席・seed・方策は、共通規約の設計案の計測（v0.141 8164194、`tools/existing_effect_games.py` 全 108 バッチ・`--start 0 --seeds 4`、延長戦の道具 magnemite・swap の seed 0〜199）と同じ。計測の前に決め、結果を見て選び直していない。開発中の確かめ（4 バッチの試し）は正式な計測に数えていない。

### 8.1 厳密側（既定の集合）の不変

| 比べ | 結果 |
|---|---|
| 旧バッチ 108・延長戦 2 の出力（時間の項目を除く）と、共通規約の設計案の記録（8164194）・v0.142 の S1 の記録 | 110 / 110 が同じ（どちらとも） |
| lockstep（基点の木 7b1d2dd と今の木。`--corpus all` の既定） | 760 局・一致した歩 136,716・食い違い 0・許した差 0 |
| lockstep（同じ。5 歩ごとに pickle で保存・復元） | 760 局・一致した歩 136,716・食い違い 0・許した差 0 |

### 8.2 続行側（CS-KYUURA-PLAY-S2A@1）

4,356 局。

| 終わり方 | 厳密側 | 続行側 |
|---|---:|---:|
| 通常の終局（game_over） | 4,233 | 4,328 |
| サドン・デス（延長戦の前の区間の終わり） | 6 | 6 |
| 研究上の未決による停止（halted） | 102 | 20 |
| 途中停止（interrupted） | 13 | 0 |
| 予期しない拒否（unexpected_rejection） | 2 | 2 |
| 内部エラー・手数の上限 | 0 | 0 |
| 監査の失敗（監査した局） | 0 | 0 |

- 予期しない拒否 2 局は両側で同じ既存の局（v0.132 X132-T130 seed 0・2。`UNRESOLVED_MIND_GAMES_CHAOS_GYM_ORDER`。監査しない局 `not_audited` 2）。基点の記録でもバッチ v0.132 の終了コードは 1。
- 続行側に残る停止 20 局: `UNRESOLVED_POISON_MIST_EARLIER_POISON` 11・`UNRESOLVED_POISON_MIST_SOURCE` 7・`UNRESOLVED_POISON_CHANGE_ORDER` 1・`UNSUPPORTED_TRANSFORM_COPIED_POWER` 1（どれも 5 規約の対象外。厳密側と同じ局・同じ停止）。
- 規約の当たった局は 95 局で、厳密側でこの 5 規約の停止コードで止まった 95 局とちょうど同じ。95 局すべてが通常の終局まで進んだ（元の停止を越えたあとに別の停止に着いた局は 0）。5 規約の停止コードのない局で結果（終わり方・停止・勝者・番の数・手数・勝敗の条件）が変わった局は 0（4,261 局が同じ）。

| 厳密側の終わり方 → 続行側 | 局 |
|---|---:|
| halted UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER → game_over | 37 |
| halted UNRESOLVED_PLAY_AS_POKEMON_SETUP → game_over | 28 |
| halted UNRESOLVED_MULLIGAN_COMPENSATION → game_over | 17 |
| interrupted UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT → game_over | 9 |
| interrupted UNRESOLVED_THOUGHT_WAVE_MACHINE_ENERGY_SHORT → game_over | 4 |

| 規約・場面 | 当たった局 | 回数 |
|---|---:|---:|
| PC-CHECK-SIDE-ORDER（両方のねむり） | 37 | 160 |
| PC-SETUP-PLAY-AS-POKEMON（最初の対戦の準備） | 28 | 35 |
| PC-SETUP-MULLIGAN-COUNT（最初の対戦の準備） | 17 | 17 |
| PC-COIN-COUNT-SHORT（ドライアップ） | 9 | 17 |
| PC-COIN-COUNT-SHORT（怪電波マシーン） | 6 | 6 |
| PC-CHECK-SIDE-ORDER（両方のくろこげマーカー）・PC-CHECK-KO-POINT・延長戦の区間の準備・配置の拒否 | 0 | 0 |

- 化石・人形の 28 局のうち、両方 → 片方の切り直しで補償の規約にも当たった局はない（補償の規約の 17 局は、どれも化石・人形のない切り直しの局）。
- 怪電波マシーンの規約は 6 局で当たった。厳密側で怪電波マシーンで止まった局は 4 局で、残り 2 局は厳密側ではドライアップで先に止まった局（続けたあとに怪電波マシーンの不足にも当たった）。
- 最初の差: 規約の当たった 95 局を両方の集合で `new_game` からやり直し、ログを比べた。95 局すべてで、最初に違うログは続行側の `convention_applied`（厳密側はそこで `halted`、または途中停止の終端）。
- 勝者が変わった局: 厳密側には勝者がない（止まった）ので、勝者の比べはできない。両側の勝者の違う局は、規約の当たった 95 局のほかに 0。
- PC-CHECK-SIDE-ORDER の当たった 37 局の勝ち負け（記録だけ。基準の値は設けない）: 先攻 20 勝・後攻 17 勝。
- 延長戦の道具（magnemite・swap、各 200 局）: 両側とも 200 局すべて終局、延長戦の準備の停止 0・監査の失敗 0。延長戦の区間の準備で規約に当たった局はない（延長戦の区間の適用は構築の盤面のテストだけで確かめた）。

この 95 局は過去の停止との対応で、ほかの組・seed で完走を保証するものではありません。対象外の未決の場面に当たれば、続行側でも止まります。

## 9. 検証

**全体のテスト**（`f2eaeee` の木。1 モジュールを 1 プロセスで、並列なし。Python 3.14.6。2026-11-04 20:37〜21:52）:

| 項目 | 結果 |
|---|---|
| モジュール | 263（完了 263） |
| テスト | 7,550 |
| 失敗・エラー | 0・0 |
| 飛ばし | 1（`test_cross_version_compatibility` の大きな比較。`KYUURA_COMPAT_BASE` を設定したときだけ） |
| 終了コード 0 でないモジュール・時間切れ | なし・なし |
| 実行の前後の木の指紋（HEAD・追跡するファイルの差・追跡しない新しいファイル） | 前後で同じ（`7181e065…9b1ffb`） |

新しいテストは `test_play_policy_s2a_v0_143` の 40（監査の誤検出の回帰のテスト 1 を含む）。基点の木（`7b1d2dd`）で走らせると、
読み込みの段階で失敗する（`AttributeError`: `conventions` に `S2A_SET_ID` がない）。盤面のテストは、正規の手順で進めた盤面と、構築した盤面を
テストの名前・説明で分けている（構築した盤面は `as_play` で続行側の識別を持たせる）。厳密側と続行側の比べは、同じ盤面・同じ乱数で両方を走らせる。

全体の実行とは別に、途中で次を走らせました（全体の総数には数えない）: 監査の修正のあとの `test_play_policy_s2a_v0_143`、文書を変えたあとの
文書を読むテスト 21 モジュール（`test_play_policy_s2a_spec`・`test_play_policy_s2a_v0_143`・`test_play_policy_family_plan`・`test_stop_policy_classification`・`test_preset_decks_v0_20`・`test_sudden_death_v0_134`・`test_conventions_v0_142` と、README・対応状況・データの由来を読む版のテスト 14。どれも OK）と、上の作成スクリプトの `--check`（問題 0）。

**厳密側の不変**（8 章）: 旧バッチと延長戦の出力 110 件が根拠の記録と同じ。lockstep（`tools/engine_lockstep.py record` を基点の木と今の木で
`PYTHONHASHSEED=0 python -P -s` で走らせ、`compare`）: 対戦 760・一致した歩 136,716・食い違い 0。5 歩ごとの保存と読み込みを挟んでも同じ。

**台帳・データ・静的検査**（どれも終了コードを直接見た。パイプの末尾のコマンドの終了コードではない）:

- `scripts/build_stop_policy_classification.py --check`・`scripts/build_play_policy_family_plan.py --check`・`scripts/build_play_policy_s2a_spec.py --check`・
  `scripts/build_convention_records.py --check`: 問題 0
- `check_card_sources`・`check_research_links`・`check_implementation_assumptions --check`・`check_normalization_revalidation --check`: 終了コード 0
- 既存のデータ・固定デッキ・参照データの差は、再生成した `convention_records.json`（場面 `#setup-placement` の追加）だけ
- ruff: 基点と同じ版・同じ設定で、指摘の件数と種類が基点と同じ（492）。新しい抑制（`noqa`）はない
- kyuura（`C:/dev/kyuura`）は変更していない

## 10. 残る不具合・未決の場面・技術的な制限

- 両モード共通の既存の不具合（この版で見つけた。直していない。厳密側の挙動を変えないため）: ポケモンチェックの 2 の「どく」でかがくへんかガスの発生源がきぜつし、残りHP「10」で力が消えていた［ずらかる］の力がもどる盤面（悪エネルギー・くろこげマーカーなし）では、きぜつの処理で SC2 の停止になり、HP 以上のポケモンが場に残った状態になって `StateIntegrityError`（内部エラー。そのコマンドの拒否）になる（構築の盤面で再現。道具の対戦では観測していない）。続行側の 4.5 の場面は保守的な制限で避けたが、規約と関係しないこの盤面は両側で同じ。
- 保守的な制限: 4.5 のきぜつの処理のあとの停止（TK1・SC2・MH1・決められない姿）は、規約を当てずにダメージの前に止める。4.3 の回復の組の確かめは、両方の組だけで止まる盤面を作れていない。
- 計測で当たらなかった場面: 両方のくろこげマーカー・PK1・延長戦の区間の準備・配置の拒否は、道具の対戦で 0 局（構築の盤面のテストだけ）。
- 研究上の未解決は未解決のまま（5 規約は続行側の集合の規約で、研究上の解決ではない）。5 規約とも公式資料に記述がないことの再確認はしていない。
- 対象外で残る停止: 計測では［ポイズンミスト］の当てはまり方・どくの量（PO1〜PO3）19 局と、写した特殊能力（UNSUPPORTED_TRANSFORM_COPIED_POWER）1 局。
- 技術的な制限: lockstep の指紋（形式 9）は続行側の集合を記録できない（厳密 対 続行はログのやり直しで比べた）。

## 11. 次にまとめて扱うとよい規約群

計測で続行側に残った停止と、この版で見えた依存から:

1. **［ポイズンミスト］・どくの量の合わせ方（PO1〜PO3。S2b の候補）**: 続行側に残る停止 20 局のうち 19 局。ポケモンチェックの 2 の量の決め方なので、PC-CHECK-KO-POINT と同じポケモンチェックの規約群として扱える。
2. **ポケモンチェックの 2 のあとの両方のきぜつ（PC-CHECK-DOUBLE-KNOCKOUT）と、きぜつの処理の停止（TK1・SC2）**: 4.5 の保守的な制限を外すのに要る。あわせて 10 章の既存の不具合（SC2 の停止がダメージのあとに起こる）を両モード共通の不具合として先に直す判断が要る。
3. **きのみの順番（BY1）**: PC-CHECK-SIDE-ORDER の除外。効果の種類の順番を含む別の問いとして、ポケモンチェックの 1 の順番の規約群で扱う。
4. **化石・人形の準備以外の場面（PF2・PF3・MG2）**: PC-SETUP-PLAY-AS-POKEMON と同じカードの別の問い。にげる（PF2）は道具の対戦で拒否が多い。

どれも採用の判断の前の候補で、この版では採用していません。
