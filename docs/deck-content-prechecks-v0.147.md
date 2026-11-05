# v0.147: 秘密の山札の内容で、使う前の受理・拒否・理由が変わる処理の修正（両モード共通）

使う前の確かめ（コインの前・山札を見る前）が、本人にも見えない山札の中身を読み、山札とサイドの配分によって受理・拒否・コード・理由の文が変わる処理を、一つの調査・修正の単位として
調べ、同じ原因・共通処理で直せるものを直した版です。**新しい続行規約は採用していません**。研究上の問い（PW3・DV2・GV1・RB2・GG1・H1）は決めていません。既存の規約集合
（CS-KYUURA-CURRENT@1・CS-KYUURA-PLAY-S2A@1・CS-KYUURA-PLAY-PO@1）の ID・版・中身・照合値は変えていません。この版の変更は**実装上の安全対策**で、裁定でも利用者の指定でもありません。

| 項目 | 値 |
|---|---|
| 基点 | `b155a7de8365909b3d57a5d85551d614027a59c1`（v0.146 の最後。`origin/claude/play-set-verification-ninja-gym`） |
| 基点を選んだ理由 | `origin/main` は `816bcffb86edeb3ea713ee08818a070e036fe0a8`（v0.140）で、v0.141〜v0.146 は公開済みの作業ブランチだけにある。v0.146 の最後は `main` に取り込まれていない |
| 作業ブランチ | `claude/secret-deck-precheck-leaks` |
| 版 | 0.147.0 |
| kyuura | 読んでいない（変更・コミット・push もしていない）。固定コミット `71d1728938fb4c8fefde9b82779cdef74beb612d` のまま |
| 変えていないもの | カードの写し・採用の記録・研究の対応表・固定デッキ・過去の参照データ・状態の書き出しの形式（35）・探索の上限・既存の規約集合・`engine.py`・`resolution/` |

## 1. 横断

停止の方針の台帳の候補（`PSP-INCREASE-ENTRY-PW3-ORACLE`・`PSP-COCOON-DV2-ORACLE`・`PSP-DECK-CONTENT-PRECHECKS` の残り）と、関連の候補（アンノーンF の［FIND］・アンノーン[J] の
［JOIN］・サカキのペルシアンの［ボスをよぶ］・同じ必須の検索の特殊能力）を、確かめた不具合とは扱わずに、まとめて調べました。

分類の時点の横断（`PSP-DECK-CONTENT-PRECHECKS`）は `check_playable`・`check_usable` だけを見ていて、場に出たときの特殊能力の使う機会の答え（`accept_problem`）を見ていませんでした。
この版では、`kyuura_engine/effects.py` のクラスの使う前の確かめ（`check_playable`・`check_usable`・`accept_problem`・`check_activation`・`usage_problem` と、そこから呼ぶ同じクラスの
メソッド）のうち、山札の中身を読むもの（`.deck` を `len()` の外で読む・名前に `deck` を含む関数を呼ぶ。配分を読まない共通処理 `deck_target_lower_bound`・`deck_lower_bound_where`・
`unseen_card_pool`・`bench_entry_unconfirmed` を除く）を AST で挙げました（静的な候補。23 のメソッド）。

| 読み方 | クラス | 扱い |
|---|---|---|
| 山札の枚数・空か | DiscardFromHandThenSearchDeck・PeekCard・SwapPrizeWithDeckTop・LookTopTakeRestDiscardTrainer・ShuffleThenArrangeDeckTop・RevealDeckTopTakeSameNamed・LookTopTakeTrainerThenShuffleLock・CoinPeekOpponentDeckTopMayShuffle・LookOpponentDeckTopKeepOrder・DrawThenPutHandCardOnDeckTop | 公開の枚数だけ。配分によらない |
| 山札とサイドを合わせた集合 | DiscardDeckTopThenReturnTypeEnergy（熱血!）・LookTopTakePokemonThenShuffle（ベイビィ）・DiscardDeckTopAttachTypeEnergyThenEndTurn（［おたけび］） | 配分によらない（4 章に残る性質） |
| 公開のおもてのカードの位置 | FlashTrainer | 配分によらない |
| 配分を読まない下限（v0.146 で直した） | CoinBenchOwnerBasicFromDeckStadium（忍者ジム） | 直したもの |
| **山札だけを読む** | SearchEvolutionCardToHand・BenchBasicsFromDeckOnEntry・CoinEvolveSelfFromDeck・SearchNamedTrainerOnEntry・CoinAttachFromDeckOnEntry・BenchNameGroupFromDeckOnEntry・SearchDeckWithBenchLettersToHand・CoinAttachEnergyFromDeckToOwnPokemon | **2 章で双子を比べた（8 クラス）** |

ワザ（`AttackEffect`）の使う前の確かめ（`usage_problem`）は山札の中身を読みません。ただし、ワザの宣言の前の先読み（`resolution/preflight`）は、ワザの要素（`resolution/programs.py`）を
実際の山札のある状態の複製で試すので、要素が山札の中身で問いを出すと宣言が拒否されます（4 章）。

## 2. 修正の前の再現（構築盤面）

山札だけを読む 8 クラスの 10 の場面を、基点の木で、テスト専用の盤面（`build_test_state`）で確かめました。対象のカード 1 枚が山札にある状態と、そのカードをうらのサイド（6 枚）の
1 枚と入れかえた双子（3 者の観測・ログの写し・持ち主が知っている所有カードの集合・乱数が同じ）に、同じコマンドを送り、`log_audit.twin_command_problems`（`owner_knowledge`）で比べました。

| 場面 | 送ったコマンド | 山札にある | サイドにある |
|---|---|---|---|
| しんかのひかり（わるいハクリュー PMCG4-052） | 使う宣言 | 受理 | PW3 |
| てしたをよぶ（わるいカイリュー PMCG4-053） | 手札から進化 → 使う機会に「使う」 | 受理 | PW3 |
| ［うか］（キョウのコクーン PMCG6-011。退化スプレーで今の番に退化） | 使う宣言 | DV2 | 受理 |
| ［ボスをよぶ］（サカキのペルシアン PMCG6-071） | 手札から進化 → 「使う」 | 受理 | PW3 |
| ファイヤーブースト（バクフーン PF1-006。対象はレインボーエネルギー） | 手札から進化 → 「使う」 | RB2（理由の文に uid） | 受理 |
| ［INCREASE］（アンノーンI neo2-023） | ベンチに出す → 「使う」 | 受理 | PW3 |
| ［FIND］（アンノーンF neo2-026） | 使う宣言 | 受理 | PW3 |
| ［JOIN］（アンノーン[J] PRN-034） | 使う宣言 | 受理 | PW3 |
| ［YIELD］（アンノーンY neo3-033） | 使う宣言 | 受理 | PW3 |
| ［YIELD］（山札のエネルギーはレインボーエネルギーだけ） | 使う宣言 | RB2（理由の文に uid） | PW3 |

どれも拒否は状態を変えないので、毎番（使う機会の答えは、拒否のあと「使わない」を答え直して）くりかえせる無料の問い合わせでした。修正の前の木で、新しいテスト
（`tests/test_deck_content_prechecks_v0_147.py`）は failures 40・errors 9 です（双子の比べは 10 の場面 × 3 つの集合の 30 がすべて失敗）。

**限界**: 再現は構築盤面だけです。`new_game` からの合法な操作の列で双子を作って確かめてはいません（長い探索をしていない）。［うか］の GV1（キョウのコクーンは「サカキの」ポケモンでは
ないので、今の写しでは起こらない）・H1（キョウのコクーン HP 60・キョウのスピアー HP 80 で、盤面を通常のダメージで作れない）の経路は確かめていません（漏れとも安全とも数えない）。

## 3. 修正

### 3.1 共通処理

- `effects.deck_lower_bound_where`（v0.138）・`deck_target_lower_bound`（v0.137）: 本人に見えない自分のカード（山札のうら・うらのサイド・見られない置いておくカード。
  `unseen_card_pool`）のうち対象が K 枚、山札の外の見えないカードが C 枚なら、山札に少なくとも max(0, K − C) 枚。K は持ち主が知っている集合、C は公開の枚数だけで決まる
- `effects.possible_deck_cards`（新規）: 山札にあるかもしれないカード。山札のすべてのカード（おもてのカードを含む）と、山札の外の見えないカードを合わせたもの（uid の小さい順）。
  合わせた集合は持ち主が知っているので、配分によらない。山札にあると止めるカードの「あるかもしれない」に使う
- `effects._power_deck_target_unconfirmed`（新規）: 下限が 1 より少ないときの PW3。理由の文は決まった文（`DECK_TARGET_UNCONFIRMED_DETAIL`。カードの名前・uid・枚数・位置を書かない）
- `effects.rainbow_possible_in_deck_error`（新規）: 山札にあるかもしれないカードにレインボーエネルギーがあるときの RB2。理由の文は決まった文（v0.146 までの `rainbow_attach_error` は uid の並びを書いた）

### 3.2 実装ごとの修正

| 実装 | v0.146 まで | v0.147 |
|---|---|---|
| しんかのひかり・てしたをよぶ・［ボスをよぶ］・［FIND］・［JOIN］ | 実際の山札に対象があるか | 下限が 1 より少なければ同じコード（PW3）で止める |
| ［INCREASE］ | 実際の山札の候補・候補がどれもベンチに出すと止めるなら最後のカードの理由の文 | 下限（`deck_target_lower_bound`）と、ベンチに出しても止めないカードの下限（`bench_entry_unconfirmed`。v0.138。v0.146 の忍者ジムと同じ） |
| ［YIELD］・［GIVE］ | 実際の山札の候補・どれもレインボーエネルギーなら RB2 | 止めない対象（`energy` のカード）を下限で確かめられなければ、山札にあるかもしれないカードにレインボーエネルギーがあれば RB2、なければ PW3 |
| ファイヤーブースト | 実際の山札にレインボーエネルギーがあれば RB2 | 山札にあるかもしれないカードにあれば RB2 |
| ［うか］の GV1・DV2 | 実際の山札の「キョウのスピアー」と組を作るか | 山札にあるかもしれないカードと組を作るか |
| ［うか］の H1 | 実際の山札の候補がどれも HP の問いに当たるか | 当たるカードがあるかもしれず、当たらないカードを下限で確かめられなければ止める |
| てしたをよぶの NB1（neo の説明のベイビィ） | 実際の山札で `card_is_basic_in_text_or_stop` | 山札にあるかもしれないカードに決まらないカードがあれば止める（今の写しのわるいカイリューはネオより前の説明なので当たらない） |

停止の方針の台帳: `PSP-INCREASE-ENTRY-PW3-ORACLE`・`PSP-COCOON-DV2-ORACLE` を fixed にし、同じ横断で見つけたほかの 6 クラスを `PSP-POWER-PRECHECK-DECK-ORACLE`（fixed）に
まとめ、候補 `PSP-DECK-CONTENT-PRECHECKS` を fixed にしました（［うか］の GV1・H1 は確かめていないことを記録）。ワザの先読みの漏れは `PSP-ATTACK-DECK-EVOLUTION-PREFLIGHT-ORACLE`（active）。

コードは今までと同じ（PW3・RB2・DV2・GV1・H1・GG1）で、止める条件が配分を読まない確かめになりました。公開の情報で決まる確かめ（ベンチに空きがない・ベンチの文字がそろわない・
つけられるポケモンがいない・特殊状態・特殊能力を消す効果）は変えていません。

### 3.3 段階の区別

- **使う前**（使う宣言・使う機会の答え。コインの前・山札を見る前）: 3.2 節の確かめ。持ち主の知識と公開の情報だけで決まる
- **山札をさがしたあと**（決定 `SEARCH_DECK`・`BENCH_FROM_DECK`・`ATTACH_FROM_DECK`。本人が山札を見る）: 選べるもの・選ぶと止める選択（`unresolved_choices`）は、今までどおり実際の
  山札で決める（観測には種類・プレイヤーだけを出す）
- 受理したら、そのあとの決定に選べる対象のカードが必ずある（下限が 1 以上）ので、先読み（受理）と実際の実行が一致する（`AcceptedPathTest`）

## 4. 直していない漏れ・残る候補

| 項目 | 分類 | 状態 |
|---|---|---|
| `PSP-ATTACK-DECK-EVOLUTION-PREFLIGHT-ORACLE`: 山札から進化カードを重ねるワザ（たきのぼりしんかなど）の宣言の前の先読みが、`resolution/programs.py` の要素で実際の山札の組（DV2・GV1）を読む | 確かめた漏れ（構築盤面）。ギャラドスを退化スプレーではがしたロケット団のコイキング、見えないギャラドス 1 枚が山札／サイドで、たきのぼりしんかの宣言が DV2／受理。理由の文に山札の進化カードの uid を書く | **active（直していない）**。ワザの先読みの経路は、H1・PW4・NB2 など同じ要素の山札を読むほかの問いも含み、範囲が広がるので、この版では変えない。`RemainingAttackLeakTest` が記録する |
| 同じ要素の H1・PW4・NB2 の問い（`resolution/programs.py`） | 未確認の候補（静的） | 比較プローブしていない |
| 熱血!・［おたけび］・マスターボール（ベイビィ）の「山札とサイドを合わせた集合」は、持ち主に見えない置いておくカードを含まない | 未確認の候補（静的）。山札と見えない置いておくカードの配分で変わる可能性 | 今の写しで、見えない置いておくカードと山札の配分が持ち主に分からない場面があるかは調べていない |
| ［おたけび］などの `rainbow_attach_error` の理由の文の uid（山札とサイドを合わせた集合のカード） | 理由の文の情報（配分にはよらない） | 変えていない |

## 5. 増えた保守的な制限と、残る情報上の性質

- **保守的な制限**: 実際には山札に対象があっても、下限が 1 より少なければ止めます。サイドがうら 6 枚の間は、見えない対象が 7 枚以上要ります。「アンノーン」・「サカキ」は
  デッキに 4 枚までなので、［INCREASE］・［ボスをよぶ］は、サイドを 3 枚以上取るまで使えません。［うか］（退化した番）・ファイヤーブーストは、止めるカードがサイドにだけあっても止めます
- **計測した影響**（`tools/existing_effect_games.py`。規模を抑えた確かめで、全バッチの計測ではない）:
  - v0.97 の組（席の両方・seed 0〜3 の 32 局）で［INCREASE］を使った回数: v0.146 の木 9 → この版 0
  - v0.44 の組（V44・W44 の seed 0・1）: ［ボスをよぶ］→ サカキ → 許可のある進化の流れは、v0.146 までは V44 が先の席の 2 局で起き、この版では反対の席の 2 局で起きる
  - v0.43 の組の 48 局: てしたをよぶ（L43 のたねポケモンは 8 枚）のポケモン育て屋さんの経路 2 回は、どちらも使わない答えになった（使う答えの経路は構築盤面のテストが確かめる）
- **受理が伝える集計の情報**: 受理（使った事実は公開）は、相手・観戦者に「使ったプレイヤーの見えない対象のカードが C + 1 枚以上ある」ことを伝えます（v0.146 までは「山札にある」）。
  使ったプレイヤーの非公開の情報で、相手はこの確かめを試せません
- **理由の文**: 使う前の拒否の理由の文は決まった文で、カードの名前・uid・枚数・位置を書きません（PW3 の前半の対象の名前は登録の説明の名前で、山札の中身ではない）
- **研究上の問い**: 対象がないときに使えるか（PW3）・退化した番に重ねられるか（DV2）・レインボーエネルギーを選べるか（RB2）などは未解決のままです。対象がなければ無条件に使える・
  0 枚を選べる・空振りできる、といった規約は採用していません。例外を握りつぶしていません（エンジンの不具合の確かめは `RuntimeError` のまま）

## 6. 検証

この版では、利用者の指示で、全体のテスト・全 108 バッチ・全 4,356 局の計測は実行していません（6.4 節）。関係するテストのモジュールを 1 つずつ実行しました。

### 6.1 新しいテスト（`tests/test_deck_content_prechecks_v0_147.py`）

- `TwinTest`: 2 章の 10 の場面 × 3 つの集合（今の挙動・S2a・PO）で、双子の受理・拒否・コード・理由の文が同じ。理由の文にカードの uid がない
- `LowerBoundTest`: 下限の境界（サイド 1 枚で対象 0・1 枚は止め、2 枚は受理。サイド 0 枚で 1 枚は受理。サイド 6 枚で 6 枚は止め、7 枚は受理）
- `AcceptedPathTest`: 受理のあとの決定に対象がある（先読みと実行の一致）・拒否は状態・乱数・ログを変えず、くりかえしても同じ・使う機会の「使わない」はどの配分でも受理・保存と復元で同じ結果
- `PossiblePresenceTest`・`MixedStopTest`: サイドにだけある止めるカードでも止める・見えるカードになければ受理・［YIELD］のレインボーエネルギーだけの RB2 と、山札を見たあとの選ぶと止める選択・
  ベトベトガスのもとの［INCREASE］の GG1 の決まった理由の文
- `KeptStopsTest`: 公開の情報で決まる止め方（ベンチに空きがない PW3・文字がそろわない）は同じ
- `RemainingAttackLeakTest`: 直していないワザの先読みの漏れの記録（4 章）

### 6.2 前の受理の条件を前提にしていたテストの調整

調整の前に、それぞれのテストが何を確かめるかを見て、確かめる目的を保つように直しました（期待値を今の出力に合わせるだけの変更はしていない）。

| テスト | 確かめること | 調整 |
|---|---|---|
| test_declared_entry_powers_v0_43（しんかのひかり・てしたをよぶ・不変条件） | 特殊能力の処理 | 盤面をサイド 0 枚に（持ち主が山札の対象を確かめられる盤面）。PW3 の盤面は変えていない |
| test_search_evolution_once_attacks_v0_44 `GiovanniTest` | ［ボスをよぶ］の処理 | 同上 |
| 同 `GameTest`（正式な対戦） | 流れが正式な対戦で起こる | 同じ seed 0・1 の両方の席を見る（5 章） |
| test_unown_idfnj_powers_v0_97（［INCREASE］・［FIND］・［JOIN］） | 特殊能力の処理・GG1 | サイド 0 枚に。GG1 のテストは、山札のアンノーンを確かめられる盤面で `bench_entry_unconfirmed` の GG1 を確かめる |
| test_unown_bear_yield_vanish_give_v0_98（［YIELD］・［INCREASE］の経路） | 特殊能力の処理 | サイド 0 枚に |
| test_oracle_leak_fixes_v0_138 `test_increase_is_unchanged_and_recorded` | v0.138 の時点で［INCREASE］を直していない記録 | `test_increase_recorded_here_and_fixed_in_v0_147` に替え、v0.147 で直したことを確かめる（v0.138 の文書の記録は同じ） |
| test_deck_search_oracle_v0_137 `AuditPrecisionTest`（監査の回帰テスト） | 山札にもどったカードを山札から出すログを監査が問題にしない | 標本の対戦（J97 対 F97 の seed 3）で［INCREASE］を使わなくなった。対戦を作る間だけ v0.146 までの確かめにもどして同じ対戦を作り、監査は今のコードで行う（受理の条件のテストではない） |
| test_declared_entry_powers_v0_43_games `test_breeder_route_returns_to_the_trainer` | ポケモン育て屋さんの経路でトレーナーの処理にもどる | 正式な対戦では使わない答えだけになった（5 章）。使う答えの経路は構築盤面のテスト（v0.43 の `SummonMinionsTest`）が確かめる |

`tools/existing_effect_games.py` の v0.43 の手順（しんかのひかりを使うか）は、実際の山札の進化カードを読んでいたので、エンジンと同じ下限に替えました（替えないと、エンジンが拒否する宣言を
送り、想定外の拒否になる）。v0.97・v0.98 の手順はエンジンに試して受け付けるときだけ使うので変えていません。

### 6.3 実行したテスト・確かめ

- 関係するモジュール（1 つずつ。単独）: test_deck_content_prechecks_v0_147・test_deck_search_oracle_v0_137・test_declared_entry_powers_v0_43・test_declared_entry_powers_v0_43_games・
  test_discard_to_bench_v0_51・test_effects・test_entry_powers_energy_lifecycle_v0_85・test_fossil_hidden_info_v0_47・test_history_attacks_v0_62・test_mew_devolution_v0_50・
  test_oracle_leak_fixes_v0_138・test_pokemon_powers_v0_5・test_search_evolution_once_attacks_v0_44・test_trainer_decisions_turn_effects_v0_56・test_unown_bear_yield_vanish_give_v0_98・
  test_unown_idfnj_powers_v0_97・test_unown_perform_help_history_v0_99・test_unown_research_idfnj_v0_97・test_unresolved_rulings_v0_3d・test_virtual_attacks_transformation_v0_49・
  test_field_energy_card_counts_v0_111（B98 の対戦）・test_damage_reactions_poison_sleep_v0_119（M85 の対戦）・台帳と版の文書のテスト。結果は 6.5 節
- 対戦: 事前に決めた条件の少数の構成だけ（5 章の v0.97 の 32 局・v0.44 の 8 局。v0.43 の 48 局はテストの中）。監査の標本の取り直し（v0.97 の seed 0〜7・v0.43・v0.87・v0.96 の seed 0〜3）
  では見つからず、6.2 節の方法にした
- 生成・データの確かめ: 停止の方針の台帳（`build_stop_policy_classification.py`）を `--write` で作り直し、`--check`。ほかの生成器・`check_implementation_assumptions --check`・
  `--sites`・`check_normalization_revalidation --check`
- ruff（0.17.2。同じ設定・範囲 `ruff check --statistics .`）を基点と比べた

### 6.4 実行していない検証

- 全体のテスト（269 モジュール）・全 108 バッチ・全 4,356 局の計測・lockstep は、利用者の指示で実行していません。変えたのは 8 クラスの使う前の確かめと、v0.43 の道具の手順 1 つです。
  これらのカードを使う対戦の組（v0.43・v0.44・v0.85・v0.97・v0.98 など）の全体の計測をやり直すと、5 章の影響の全体の数が分かります（所要時間の見込みは、1 局 1〜2 秒で、組 1 つ
  （24〜48 局）につき 1 分前後）
- `new_game` からの合法な操作の列での双子の再現

### 6.5 結果

| 確かめ | 結果 |
|---|---|
| 新しいテスト（修正の前の木） | failures 40・errors 9（双子の比べの 30 の組み合わせがすべて失敗。errors は新しい関数・理由の文の uid） |
| 新しいテスト（この版） | 18 テスト・OK |
| 6.3 節の関係するモジュール（22。1 つずつ） | すべて OK（v0.43 の対戦のモジュールは、道具の手順を替えたあとにもう一度、モジュール全体を実行した） |
| 台帳・設計案・同梱の記録・実装上の仮定・正規化の再検証・版のテスト（test_stop_policy_classification・test_play_policy_family_plan・test_conventions_v0_142・test_implementation_assumptions・test_normalization_revalidation・test_preset_decks_v0_20） | すべて OK |
| 生成器の `--check`（停止の方針の台帳・設計案・同梱の記録・S2a と PO の仕様案） | すべて 0。台帳・設計案・同梱の記録は `--write` で作り直した（台帳の基点・分類の時点の集計・道具の証拠・更新の記録の前の 8 つは同じ。項目の削除なし） |
| 規約集合の照合値 | 3 つの集合とも固定の値と同じ（同梱の記録の場面の索引だけが、台帳の現在有効な項目に合わせて変わった。集合の中身ではない） |
| `check_implementation_assumptions --check`・`check_normalization_revalidation --check` | 0 |
| `check_implementation_assumptions --sites` | 新しい候補箇所 197（基点 194）。この表を書く前の差は 2 つ: `tests/test_preset_decks_v0_20.py` 151 行の版の注記の文が変わって ID が替わったもの（S-db0855041bd0 → S-e0b98bda0b46。v0.146 と同じ）と、この文書の冒頭の「裁定でも利用者の指定でもありません」（S-e3a00a271a99。この版の変更の分類の記述で、新しい仮定ではない）。言い換えはしていない。この表の 2 行（確かめの名前を書いた行と、この行）も、語を引用しているので候補箇所になる（分類の記録そのもので、新しい仮定ではない） |
| ruff 0.17.2（`ruff check --statistics .`） | 基点・この版とも 492 件で、規則ごとの件数も同じ（新しいテストで出た未使用の変数・import の並びは直した）。加えた抑制（`noqa`）はない |
