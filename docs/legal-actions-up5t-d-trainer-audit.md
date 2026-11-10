# UP-5t の D の絞り込みと、トレーナーの候補の情報境界の静的な監査（文書だけ。エンジンの版は 0.178.0 のまま）

UP-5t の監査（[legal-actions-up5t-audit.md](legal-actions-up5t-audit.md)）の 5 章で D（根拠不足で未確認）として残した、呼び出し先・受け手の型の範囲を、型注釈から受け手を推論する走査で絞りました。
同じ走査で、トレーナーの候補（`play_trainer`）の確かめが相手のうらのカードの本当のカードを読む経路を調べました。

**この作業は調査・設計・文書化だけです。** 次のことはしていません。

- エンジン・AI・GUI のコードの変更、テスト、ビルド、対戦の実行
- `kyuura_engine` の import（登録は列挙していません）

特殊能力の側の対策（UP-5t-C1）をトレーナーへ一律に当てはめることは前提にせず、案を比べました（6 章）。

## 0. 基点と範囲

| 項目 | 値 |
|---|---|
| コードの基点 | `ad2bd430`（`origin/claude/vai-0178-follow`）。含むコミット: UP-5t-C1 の実装 `c01c1b5`、版 0.178.0・配布の固定コミット `8f5329d6fb9eeeb783f3d6f57128069ffc0d98a0`、文書 `7ef45be`、検証用 AI の追従 `b64fc82`・`ad2bd43` |
| `main` との関係 | `origin/main`（`88ad4d9`）には入っていません（基点は `main` より 81 コミット先）。`main` のエンジンは 0.171.0 のままです |
| 読んだコードの版 | パッケージ 0.178.0（`kyuura_engine/__init__.py`）。UP-5t の監査の基点 `a0c1312`（0.177.0）との差は、`legal_actions.py`（UP-5t-C1）と版だけです |
| 参照した文書の版 | UP-5t の監査（0.177.0 で書いた 1〜10 章と、0.178.0 の 11 章）、PT-5e の監査（0.175.0 の 1〜8 章と、0.176.0 の 9 章）、U7-5c（v0.169）、U7-5e（v0.171 と CORR-3）、`legal-actions-u7-5-design.json`（v0.171 の走査の記録）、`verification-ai-inventory.md`（v0.178 のあとの追記まで） |
| 作業ブランチ | `claude/up5t-d-trainer-audit`（専用の worktree `C:\dev\kyuura-engine-up5td`）。利用者の `C:\dev\kyuura-engine` は `main` のまま変えていません |
| 証跡 | `C:/dev/kyuura-engine-verification-vai/verifier/runs/up5t-d-trainer-audit/`（走査と集計のスクリプト・出力・コマンドの記録）。保存先のマニフェストは、既存の 632 件のハッシュを照らして不一致 0 を確かめてから、`manifest_update.py`（`records.write_manifest` と同じ形式。`kyuura_engine` を import しないために写した）で書き直した: 641 ファイル、`sha256.json` は `f5e287daf887f7cba1707778b5ff1288c7cbb240226c9d999147ef804d410e96` |

範囲は、候補・inputs・check から到達する処理です。受理のあとの処理も、候補の側の試行から呼ばれる部分は含めました。

- inputs・check は、発行した候補を引くだけです（`legal_actions._inputs`・`_check`・`_input_problem`・`ActionHost._lookup`）
- エンジンの確かめを呼ぶのは候補の作成だけです。ここを起点にしました

## 1. 既存の監査の根拠の確認

| 資料 | 確かめたこと |
|---|---|
| UP-5t の監査（1〜10 章） | 7 型の `check_usable` を根にした走査（strict 201・broad 2,449）。状態のメソッドを名前で解決した 129 か所と多態の 34 か所を、受け手の型の静的な確認がないので D とした |
| UP-5t の監査（11 章、UP-5t-C1） | `_probe_without_opponent_identity` が `zones.IDENTITY_CONSULTED` を空の並びにして `check_use_pokemon_power` を呼ぶ。相手が記録されたら `unverified`（`face_down_reveal_not_evaluated`）にする。トレーナーの候補（`play_trainer`）には入れていない（11.7 節） |
| PT-5e の監査（9 章、v0.176） | 実際の山札から引いて試す 5 型（6 枚）。結果は本人の手札・公開の枚数・おもての山札の並びの不変条件（`faceup.prefix_problems`）で決まる。不変条件が崩れた状態では候補で呼ばない（`unverified`） |
| U7-5c（4 章・10 章） | 場だけを試す 6 型（`PLAYABLE_BOARD_TRIALS`）は「山札・サイド・手札・置いておくカード・うらのカードの集合を読まない」と書いた（4.2 節）。ただし、たどったのは effects.py の閉包と、別のモジュールの関数の 1 段目までで、2 段目より先は名前と読む属性だけを見た（10 章） |
| U7-5 の設計の走査（`scripts/build_legal_actions_u7_5_design.py`） | effects.py の中の呼び出しだけをたどり、`.clone` を作る型（trials 11）と持ち主の知識の関数を呼ぶ型（6）を数えた。ほかのモジュールは追っていない |
| U7-5e・CORR-3 | 7 型の記録（「955 の閉包で山札・サイド…を読まない」）。955 の閉包の走査は保存されていない |
| `verification-ai-inventory.md` 7 章 | UP-5t の行は「残るのは D（静的な監査だけ）」。PT-5e の行は v0.176・v0.177 で対処済み |
| 保存済みの走査 | `verifier/runs/up5t-audit/`（`up5t_scan.py`・`scan_output.json`・`hooks_scan.py`・`secret_sites.py`・`commands.txt`）。今回はこれを読み、作り直していない |

経緯の記録として、次の 3 点をそのまま残します。

- UP-5t の監査の 1 回目の走査には誤りがありました（呼び出し先を積む前に次へ進む。strict 171・broad 2,224）。直した 2 回目が 201・2,449 です（同じ文書の 9.2 節）
- v0.171 の 955 の閉包は、スクリプトも出力も保存されていません（文書の記述だけ）
- 件数はどれも、その時の走査の方法による近似で、網羅の証明ではありません

今回の比べで分かったことが 2 点あります。

1. **以前の broad の閉包（2,449）は上限ではありませんでした。**
   - 今回の型つきの閉包（528）のうち 69 の関数は、broad に入っていません（`closure_compare.txt`）
   - 原因: 以前の走査は `self.m` を定義した型から上へだけ引き、下の型の上書き（基底のメソッドの中の `self.texts()` などが下の型の実装に届く）を追っていませんでした
   - 69 はどれも登録の文面を照らすメソッド（`texts`・`text_problems` など）で、本当のカード・山札・手札を読む文字はありません
   - 以前の strict の 201 は、すべて今回の閉包に入っています
2. **U7-5c 4.2 節の記録は、6 型のうち 2 型について正しくありません**（3 章の CORR-4）。
   - 「場だけを試す 6 型は、うらのカードの中身を読まない」と書いていますが、別のモジュールの 2 段目より先の `conditions._prevented` → `zones.designate_face_down` を見ていませんでした

## 2. 方法

`typed_scan.py`（証跡）で、パッケージの 55 のモジュールをソースの構文だけで読みました。UP-5t の監査の `up5t_scan.py` との違いは次のとおりです。

| 項目 | 扱い |
|---|---|
| 受け手の型 | 引数・項目（dataclass の注釈）・戻り値の型注釈と、代入・`for`・タプルの展開・内包・`getattr(x, "名前")` から推論した。流れによらず、変数ごとに代入された型の和をとる |
| 型が分かったメソッドの呼び出し | その型の継承の上（MRO）の 1 つと、下の型の上書きのすべて（クラス階層による解決）に限る |
| `self.m`・`cls.m` | 定義した型の継承の上と、下の型の上書き（以前の走査は上だけ） |
| `super().m` | MRO の次の型から引く |
| 型が分からない受け手 | 同じ名前の実装すべてに広げる（以前の broad と同じ過大近似）。「型の分からない受け手」として記録する |
| 呼ばずに値として渡した関数 | `partial(f, …)`、辞書の値、`key=` などを「受け渡し」の辺として閉包に含める |
| 関数の中の import | 別名として解決する（`from .zones import designate_face_down` など） |
| 読む先の印 | 本当のカードを読む関数（`printed_def`・`in_play_def`・`_secret_plan_keeps`・`designate_face_down`・`reveal_face_down`・`conditions._prevented`・`movement.designate`）への呼び出し元を、閉包ごと・根ごとにすべて集めた。文字の検索で、`definitions[…]`・`cards[…].card_id`・山札・手札・サイド・乱数・グローバル・キャッシュの読みも記録した |

根は次の 3 つです。

- UP-5t の 7 型の `check_usable`（以前と同じ。まとめた閉包と、型ごとの閉包）
- `legal_actions._trainer_candidate`
- 77 の `check_playable` の実装のそれぞれ

実行の経緯は `commands.txt` にあります。1 回目は走査の誤り（組み込みの名前の判定）で終了コード 1、2・3 回目は 0 で、3 回目は根ごとの集計を加えて 2 回目の出力を上書きしました。

## 3. UP-5t の D の具体化

### 3.1 結果の要約

| 以前の D の項目 | 今回の結果 |
|---|---|
| 状態のメソッドを名前で解決した 129 か所 | 129 か所すべてで、受け手が state.py の型（`GameState`・`PlayerState`・`PokemonInPlay`・`SpecialConditions`）だと推論できた（128 は型だけ、1 は型とパッケージの外の値の和） |
| 多態の呼び出し 34 か所 | 31 か所は、型・組み込みの型・`super` で解決した（下の表）。残る 3 か所は、`IDENTITY_ORACLE.assign` の 2 か所と、例外の初期化（`Exception.__init__`）の 1 か所 |
| 型つきの閉包で、型の分からない受け手 | 4 か所。`IDENTITY_ORACLE.assign` ×2 と、辞書の `get` ×2（`FULL_HEAL_TEXTS.get`・`expected.get`。名前が `CardPool.get` と同じなので名前では広がる） |
| 型の分からない受け手で、同じ名前の実装がパッケージにないもの | 98 か所。`format` 49・`append` 31・`items` 9・`values` 3・`group` 2・`__new__`・`update`・`setstate`・`getstate` 各 1。標準の型のメソッドで、パッケージの処理に入らない |
| 本当のカードを読む関数に届く型（7 型ごとの閉包） | `CoinConditionOnEitherActive` だけ（`confuse`・`put_to_sleep` → `_prevented` → `designate_face_down`）。v0.178 で対処済み。ほかの 6 型は届かない。`ChooseFossilEvolvedThenCoinDevolveAll` は `printed_def`・`in_play_def` に届くが、どちらもうらでないカードの読み（3.2 節） |

型つきの閉包の大きさ（528）は以前の strict（201）より大きくなりました。増えた 327 の入口は次のとおりです。

| 入口 | 関数の数 |
|---|---|
| 登録表の `power_effect` → `power_problem` → 登録した型の `check`（文面の照らし） | 166 |
| `play_profile` → トレーナーの登録の `check` | 122 |
| `energy_effect` | 14 |
| 特殊エネルギーの `units` | 11 |
| ［ずらかる］などの `is_able` | 7 |
| その他（`is_working`・`hp_bonus`・`located`・`trainer_entry`・`suppresses`・`status_allows`・`_IdentityOracle.assign`） | 各 1 |

どれも、型が分かったうえで下の型をすべて含めた過大近似です。登録表に実際に入っている型は、実行時の値で決まります。

### 3.2 一覧（多態の 34 か所と、型の確定・未確定）

「到達」は、候補の作成（`_power_candidates` → `_power_verdict` → `check_use_pokemon_power` → `check_usable`）から届くかです。

| 起点と呼び出し式 | 受け手・引数の由来 | ありうる型・実装 | 到達 | 読む・変える | 根拠 | 残る不確実性 |
|---|---|---|---|---|---|---|
| `conditions.clear_special_conditions`: `pokemon.conditions.names()` | `pokemon: PokemonInPlay` の項目 `conditions: SpecialConditions` | `SpecialConditions.names` | する | 特殊状態の名前（公開） | 型注釈 | なし |
| `continuous.scaring_powers`・`effects._own_working_continuous`・`continuous_powers`・`status_immunity`・`transform_works`: `effect.status_allows`・`located` | `PowerSlot.effect: PowerEffect \| None`、登録表の `power_effect` の戻り値 | `ContinuousPower.status_allows`・`located`（下の型に上書きなし） | する | 場の特殊状態・場所（公開） | 型注釈・クラス階層 | 登録された値の型は実行時に決まる（登録表の固定が前提） |
| `continuous.suppressors_of`: `effect.is_working`・`suppresses` | `SuppressOtherPowers` に絞った値（`isinstance` の後） | `SuppressOtherPowers.is_working`・`suppresses` | する | 場（公開） | 型注釈 | なし |
| `effects.scram_working`: `slot.effect.is_able(pokemon)` | `PowerEffect` | `is_able` の 7 実装（`BeamOnKnockOut` ほか） | する | 場のダメージ・特殊状態（公開）。7 実装の本体に、秘密の読みの文字はない | クラス階層・本体の文字 | 7 実装のどれが呼ばれるかは登録で決まる |
| `effects._printed_units`・`_wild_growth_card`: `effect.units()` | `energy_effect` の戻り値 `SpecialEnergyEffect \| None` | `units` の 11 実装 | する | 特殊エネルギーのエネルギーの数（公開） | クラス階層 | 同上 |
| `effects.max_hp_bonus`: `effect.hp_bonus(state, pokemon)` | `ContinuousPower` | `MaxHpPerAttachedEnergyCards.hp_bonus` | する | ついているエネルギー（公開） | 型注釈 | なし |
| `_miracle_effect`・`special_energy_effect`・`card_power_slots`・`ninja_tricks`・`stadium_in_play`・`_ninja_trick_guard`・`play_as_pokemon_effect`・`card_def`・`in_play_def`: `state.effects.energy_effect`・`power_effect`・`trainer_entry`・`trainer_effect`・`play_profile` | `GameState.effects: EffectRegistry` | `EffectRegistry` の各メソッド（1 つずつ） | する | 登録表を読む。`play_profile` は登録表のメモ（`_profiles`）に書く（4 章） | 型注釈 | 登録表の差し替えがないこと（前提） |
| `effects.play_as_pokemon_effect`: `state.printed_def(pokemon.card)` | 場のポケモン | `GameState.printed_def` | する | 本当の定義。ただし前の行の `card_def(pokemon.card).play_role` が None なら読まない。うらのカードの定義（`FACE_DOWN_DEFINITION`）に役割はない | 本体 | なし |
| `evolution.devolve` → `goop_gas_entry_check` → `in_play_def(card)` | ［かせきか］の試行で、自分の進化したポケモンの重なりのカード | `GameState.in_play_def` | する | 重なりのカード（公開・自分のカード） | 本体 | なし |
| `effects.max_hp_drops`: `previous.get(…)` | 局所の辞書 | `dict.get` | する | 局所 | 型推論（組み込み） | なし |
| `effects.ChooseFossilEvolvedThenCoinDevolveAll.candidates`: `devolve_count_problems(…).get(count)` | 戻り値の辞書 | `dict.get` | する | 局所 | 戻り値の注釈 | なし |
| `persistent._scared_source`: `_SCARE_SOURCES_IN_PROGRESS.add(key)` | モジュールの集合 | `set.add` | する | グローバルの集合（`try`／`finally` で外す） | 本体 | 1 つのスレッドで動かすこと（前提） |
| `MaxHpOrderUndetermined.__init__`・`EngineError.__init__`: `super().__init__` | 例外の型 | `EngineError.__init__` → `Exception.__init__` | する | なし | MRO | なし |
| `zones.designate_face_down`・`reveal_face_down`: `IDENTITY_ORACLE.assign(state, pokemon.card)` | モジュールのグローバル（初期値 `None`、注釈なし） | `engine._IdentityOracle.assign`（値を置くのは `engine._identity_independent` だけで、`finally` で戻す） | **値が `None` なので呼ばれない**（候補の作成の中で値が置かれない根拠: パッケージで `legal_actions` を import するのは `client_api` だけで、エンジンの確かめの中から候補を作る経路がない） | 置かれれば本当のカードを割り当てる | 本体・import の関係 | 型は推論できない。1 つのスレッド・外からの書きかえがないことが前提 |
| `FULL_HEAL_TEXTS.get`・`expected.get`（`CureSpecialConditionsTrainer.check`・`TrainerTurnEffectTrainer.check`） | モジュールの辞書・局所の辞書（注釈なし） | `dict.get`（名前では `CardPool.get`・`Catalog.get` に広がる） | `play_profile` の登録の `check` を通って届く | 登録の文面 | 値の文（辞書の表示） | 型の推論はしていない（文で確かめた） |

`ChooseFossilEvolvedThenCoinDevolveAll` の `printed_def`・`in_play_def` は、自分の場のうらでないカードの読みです（UP-5t の監査の 5 章の A のまま）。

### 3.3 broad の経路と実際の候補処理の経路の分け方

| 経路 | 扱い |
|---|---|
| 型の分からない受け手を名前で広げた先（`get` → `CardPool.get`・`Catalog.get`、`count` → `resolution.programs` の `count` など） | 受け手が辞書・リストと読めるので、実際の到達から外した（3.2 節の最後の行。トレーナーの閉包の `heights.heights_problems` の `every.count(n)` は `list.count`、`faceup._looked` などの `event.get` はログの辞書） |
| クラス階層で含めた下の型の実装（`units`・`is_able`・登録の `check`） | 実際にどれが呼ばれるかは登録表で決まる。全部を含めたまま調べ、本当のカードを読む関数に届くものはなかった |
| `IDENTITY_ORACLE.assign` | 候補の作成では値が `None` で呼ばれない（3.2 節） |

### 3.4 残る D

静的には閉じられず、前提として残るものです。

- 型注釈が実際の値と合うこと（流れによらない推論。`Any` の項目、たとえば `persistent_effects: tuple[Any, ...]` のメソッドは名前で解決した）
- 登録表（`state.effects`）を実行時に差し替えないこと、登録した値の型が注釈どおりであること
- 1 つのスレッドで動かすこと（`zones` のグローバルを並行に置かない）、外からの書きかえ（モンキーパッチ）がないこと
- 動的な登録（実行時に組み立てる表）は、ソースの登録の式としてだけ見ている

## 4. トレーナーの候補の情報境界

### 4.1 経路

`_trainer_candidate`（`legal_actions.py:1506`）は、本人の手札のトレーナーカードごとに次の順で処理します。

1. `_use_condition_evaluated` で、使うための条件を呼ぶかを決める
2. `_probe(partial(check_play_trainer, use_condition=…))` で確かめる
3. `check_play_trainer`（`engine.py:2001`）の中の順は次のとおり
   1. 番・手札・トレーナーカードであること
   2. `trainer_use_blockers`
   3. 登録表
   4. `effect.check_playable`
   5. `stadium_trainer_cost`
   6. `trainer_reaction_sources`（MG1）

確かめの結果の使われ方は次のとおりです。

- `IllegalActionError`: 選べるものから外す
- `UnsupportedError`: 実行できない区分
- 通れば `may_stop_later`（理由 `preflight_not_evaluated`・`continuation_not_evaluated`）

候補の値（選べるものの有無・数・並び、`eligible`、処理可能性、理由、check の `CANDIDATE_NOT_EXECUTABLE`）は、この結果で決まります。

今は `PLAYABLE_NOT_EVALUATED` が空です。PT-5e の 5 型（おもての山札の不変条件が成り立つとき）を含め、effects.py で定義した条件はすべて候補の作成で呼びます。

`check_play_trainer` の `check_playable` の前と後の確かめ（番・手札・使用の禁止・登録・リムーブ禁止ジム・MG1）は、本当のカードを読む関数に届きません（読む関数の呼び出し元の一覧に、これらからの経路はない）。

### 4.2 77 の `check_playable` の群

`analysis_output.json` の `playable_groups` です。77 は基底の `TrainerEffect` を含む数です。

| 群 | 数 | 型 | 秘密に関わる読み |
|---|---|---|---|
| 相手のバトル場をおもてにする試行 | 2 | `CoinStatusOnOpponentActiveTrainer`（ねむれ!ねむれ! `PMCG4-054`）・`CoinHealBothElseSleepBoth`（トロピカルウインド `PR1-074`） | 相手のバトル場がうらのカードなら、複製の上の `put_to_sleep` → `_prevented` → `designate_face_down`（`by_player` は番のプレイヤー＝使う人）→ `_secret_plan_keeps`（`printed_def`） |
| 自分のバトル場をおもてにする試行 | 1 | `ConditionOwnActiveTrainer`（イマクニ？ `PR1-013`・おどれ！neo★イマクニ？ `PRN-026`） | 自分のうらのカードだけ（`by_player` が持ち主）。本人の知識 |
| おもてにしない場の試行 | 3 | `SwitchWithBench`・`SwitchOpponentWithBench`・`CoinHealAndCureOwnActive` | 本当のカードを読む関数に届かない。`printed_def` は使うトレーナー自身（`trainer_card_effect`。本人の手札） |
| PT-5e（山札から引いて試す） | 5 | `BlainesQuiz`・`BlainesHeightQuiz`・`SetAsideGuessKindQuiz`・`GuessOpponentPrizeKind`・`SwapPleaseTrainer` | 山札の上のカードを複製の上で引くが、結果はおもての山札の不変条件のもとで公開の枚数だけで決まる（PT-5e の監査 2.3 節）。不変条件が崩れていれば候補で呼ばない |
| 持ち主の知識の関数 | 6 | `BenchNameGroupFromDeckTrainer` ほか（U7-5c 4.1 節） | 山札とサイドを合わせた下限（本人の山札の順序・配分を読まない）。`BenchNameGroupFromDeckTrainer` の `in_play_def` は、この下限の述語の中の自分のカードの読み |
| おもての山札の位置を読む（試行なし） | 7 | `DrawCards`・`CoinDrawTrainer`・`DiscardHandAndDraw`・`DiscardFromHandThenDrawTrainer`・`ArrangeOwnDeckTopTrainer`・`TakeFromDiscardTrainer`・`FlashTrainer` | 山札の中のおもてのカードの位置。おもての山札の不変条件（上から続く）のもとでは、公開のおもての枚数だけで決まる。PT-5e と違い、候補の側のガードはない（4.5 節） |
| ほか | 52 | 本人の手札・本人のトラッシュ・場・相手の手札とサイドの枚数（空か）・山札の枚数を読む | `printed_def` は使うトレーナー自身か、うらでないポケモンの重なりの下のカード（`evolved_from_baby` は `is_face_down` を先に確かめる）。本当のカードを読む関数に届かない |

別名を通したカードの識別の読み（`cards[…].card_id`・`definitions[…]`・`definitions.values()`）を、トレーナーと UP-5t の閉包の全関数で文字で探しました（20 か所）。

- 読む対象は、ついているトレーナー・効果の発生源の記録・スタジアム・重なり・本人の手札・カードの一覧（公開）か、記録機構（`_IdentityOracle.assign`・`reveal_face_down` のログ）の中だけでした
- うらのカードの uid から識別を読むものはありませんでした（`analysis_output.json` の `aliased_identity_reads`）

### 4.3 相手のバトル場をおもてにする 2 型（C）

| 区別 | ねむれ!ねむれ!（`CoinStatusOnOpponentActiveTrainer`） | トロピカルウインド（`CoinHealBothElseSleepBoth`） |
|---|---|---|
| 試行 | `check_playable`（`effects.py:18792`）: 相手のバトル場の［でんせつのからだ］（公開）を確かめ、複製の上で相手のバトル場を「ねむり」にして `state_stop_after(state, trial)`（新しく決められない姿・最大HPの低下・［ずらかる］の戻り） | `check_playable`（`effects.py:32486`）: 「おもて」（両方のバトル場のダメージカウンターを除く）と「うら」（両方を「ねむり」）を、それぞれ複製の上で `_trial_stop` → `state_stop_after`。使う人のバトル場 → 相手のバトル場の順 |
| 秘密を読むこと | **ある（静的に確かめた）**。相手のバトル場がうらなら、`_prevented`（`conditions.py:73`）→ `designate_face_down(by_player=state.current_player, can_lose=True)`（`zones.py:138`）→ `_secret_plan_keeps` が本当のカードの印刷の定義を読む | **ある（静的に確かめた）**。「うら」の試行で同じ経路。「おもて」の試行は、うらのカードのダメージが 0（不変条件）なので何もせず、おもてにしない |
| 返す判定が秘密によりうること | **ありうる（静的な根拠）**。本当のカードが「たねポケモン」ならおもてにして「ねむり」にする（本当のカードの［めんえき］などで防ぐ）。「たねポケモン」でなければ、複製の上でトラッシュする（ついているエネルギー、リサイクルエネルギーの戻り、`remove_source_left_effects`）。そのあとの `state_stop_after` は、本当のカードを含む場（またはいなくなった場）と比べるので、停止のコード（実行できない区分か `may_stop_later` か）が本当のカードで変わりうる | 同じ（「うら」の試行。「おもて」の試行で止まれば「うら」の試行に進まない） |
| 外へ出る差の再現 | **していない**。UP-5t-C1 の特殊能力の盤面（同じ `designate_face_down` の経路）では、修正の前に外へ出る差は出なかった（UP-5t の監査 11.1 節）。トレーナーの盤面は実行していない | 同じ |
| 候補の側の保護 | ない。`_trainer_candidate` は `IDENTITY_CONSULTED` を置かずに `check_play_trainer` を呼ぶ（UP-5t-C1 は `use_power` だけ） | 同じ |
| 送った場合 | `engine._apply_checked`（`engine.py:627`）が `IDENTITY_CONSULTED` を置いて処理し、相手が記録されたら `_identity_independent` がありうるカードのすべてで確かめ直す。受け付けるか・拒否の理由は本当のカードによらない | 同じ |
| 到達 | 相手がマチスの秘策でうらにして出したカードを、にげる・入れ替えでバトル場に出した盤面（UP-5t-C1 の構築盤面 `opponent_face_down` と同じ形で、使う人の手札にこのトレーナーを持たせる）。任意のデッキの new_game から届くかは確かめていない | 同じ |

トラッシュになる側の枝の停止も確かめました。

- `reveal_face_down` のトラッシュの処理は、`energy_discard_plan(…, "rule")` を `by_player` なしで呼ぶので、エコロジムの `UnsupportedError` の枝に入りません
- `RuntimeError` は、うらのカードにダメージ・重なりなどがあるときだけです。これは `check_invariants` の `_face_down_pokemon_problems` が禁じる形です
- 不変条件が成り立つ状態では、トラッシュの枝から例外は出ません。違いは `state_stop_after` の比べだけです

### 4.4 対照（秘密に依存しないもの）

- イマクニ？・おどれ！neo★イマクニ？（`ConditionOwnActiveTrainer`）: 自分のバトル場がうらのカードなら、自分の本当のカードを読みます。`designate_face_down` は持ち主を記録しません。本人の知識で、漏れではありません
- `SwitchOpponentWithBench`: 相手のうらの控えをバトル場に出す試行は、おもてにしません（UP-5t の監査 3.2 節と同じ `_switch_active_with_bench`）。比べる値は `card_def`（`FACE_DOWN_DEFINITION`）です
- ［でんせつのからだ］の確かめ（`trainer_effect_blocked`）: うらのカードは特殊能力を持たない定義なので、本当のカードによらず偽です
- 項目を読んで止まる経路（`HiddenPropertyRead`、FD1）: 本当のカードによらない停止で、漏れではありません（U7-5 の F-2・F-4 と同じ）

### 4.5 公開の情報への依存（PT-5e で確かめた前提）

おもての山札の位置を読む 12 型（PT-5e の 5 型と、上の表の 7 型）は、`faceup.prefix_problems`（おもてのカードは山札の上から続く）のもとで、公開のおもての枚数だけで結果が決まります。

- 候補の作成でこの不変条件を確かめてから呼ぶのは、PT-5e の 5 型だけです（`_use_condition_evaluated`）
- ほかの 7 型は確かめずに呼びます
- 公開の入口（`ClientHub.from_state`・`ActionHost.from_state`）は v0.177 から不変条件を確かめます
- 信頼された内部の組み立て・低層の API・外からの書きかえで崩れた状態では、7 型の結果が山札の中の位置（本人の山札の順序を含む）に依存しえます。今回は前提として記録し、変更は提案しません（6 章）

### 4.6 本人の知識と相手だけの情報

| 情報 | 扱い |
|---|---|
| 本人の手札（カード・並び） | 本人の知識。多くの条件が読む |
| 本人のうらのカードの本当のカード | 本人の知識（持ち主は記録されない） |
| 本人の山札の順序・サイドとの配分 | **本人が知っているとは仮定しない**。持ち主の知識の関数は山札とサイドを合わせた下限を使う。PT-5e の 5 型・おもての位置の 7 型は不変条件のもとで公開の枚数に落ちる |
| 相手の手札 | 枚数（空か）だけ（`CoinReturnOpponentHandPositions`・`LookOpponentHandReturnOneThenMayDraw`・`SwapPleaseTrainer`） |
| 相手のサイド | 枚数とおもての記録だけ（`GuessOpponentPrizeKind`・`AskOpponentEachTakePrizeElseDraw`） |
| **相手のうらのカードの本当のカード** | 相手だけが知る。4.3 節の 2 型の試行だけが読む |

### 4.7 CORR-4（U7-5c 4.2 節・設計の PT-5t の記録の訂正）

- **訂正の対象**: U7-5c の 4.2 節と、`legal-actions-u7-5-design.json` の PT-5t の行の記録。「場だけを試す 6 型は、山札・サイド・手札・置いておくカード・うらのカードの中身を読まない」
- **正しくは**: 6 型のうち、ねむれ!ねむれ!（`CoinStatusOnOpponentActiveTrainer`）とトロピカルウインド（`CoinHealBothElseSleepBoth`）は、相手のバトル場がうらのカードのとき、複製の上の「ねむり」の試行で本当のカードの印刷の定義を読む（4.3 節）
- **原因**: U7-5c は、別のモジュールの関数の 1 段目（`conditions.put_to_sleep`）までをたどり、2 段目より先（`_prevented` → `zones.designate_face_down`）は名前と読む属性だけを見た。限界は U7-5c の 10 章に書いてあったが、4.2 節の結論はその限界を反映していなかった
- **扱い**:
  - 過去の記録の本文は書き換えず、U7-5c の 10 章に、この節への参照を加えた
  - 設計の JSON は生成した記録なので変えていない
  - コードの扱い（`PLAYABLE_BOARD_TRIALS` で候補の作成で呼ぶ）は v0.169 から変わっていない

## 5. 無副作用と記録機構

### 5.1 試行の複製と書き込み

対象は、4.3 節の 2 型と、自分のバトル場の 1 型の試行の経路です。

| 観点 | 読み取りの結果 |
|---|---|
| 複製の深さ | `GameState.clone`（`state.py:2617`）は `__dict__` の浅い写しで、`players` を `PlayerState.clone` で、乱数を `copy_rng` で写し直す。`PlayerState.clone` は山札・手札・サイド・トラッシュの list と場のポケモン（`PokemonInPlay.clone`。`energy`・`trainers` の list を写す）を写す。`cards`・`definitions`（読み取り専用の写像）、`effects`（登録表）、`log`・`face_down_cards`（タプル）は共有する |
| 各領域・場のカード | 試行の書き込みは、複製の属性の付け替えと、複製の list の変更だけ。<br>・`face_down_cards = tuple(…)`<br>・`p.active = None`・`del p.bench[i]`<br>・`p.discard.append`・`hand.append`（リサイクルエネルギー）<br>・`pokemon.conditions = …`・`pokemon.persistent_effects = tuple(…)`（`remove_persistent_effects`・`_mark_source_left` は `dataclasses.replace` とタプルの付け替え） |
| ログ・決定・停止・履歴 | `add_event` はログのタプルを付け替える（複製の上）。決定は出さない。停止は例外のコードで返す |
| 乱数 | `copy_rng` で写すだけ。`flip_coins`・`shuffle`・`random.` の呼び出しは、トレーナーの閉包の試行の経路にない（`resolve` は呼ばれない） |
| グローバルの記録状態・登録 | 次の 4 つ。<br>・`zones.IDENTITY_CONSULTED`: 候補の作成では `None` で、追記しない<br>・`zones.IDENTITY_ORACLE`: `None`<br>・`persistent._SCARE_SOURCES_IN_PROGRESS`: `try`／`finally` で戻す<br>・**登録表のメモ `EffectRegistry._profiles`**: `play_profile` が定義ごとの結果を共有の辞書に書く。値は定義だけで決まる（同じ定義には同じ結果）。トラッシュ・おもての試行で本当のカードの定義を引くと、その定義の項目が加わりうる。外へ出る値・結果には効かないが、元の状態と共有する可変の値への書き込みは、これと `heights.load_species_heights`・`diagnostics.default_catalog` のキャッシュだけ |
| 例外のときの復元 | 書き込みは複製だけなので、例外で試行を抜けても元の状態は変わらない。グローバルの集合は `finally` で戻る。メモは残る（値は定義だけで決まる） |

前提は UP-5t の監査 4 章と同じです。

- 元の状態の共有する値（`PokemonInPlay` の不変の項目など）を、その場で変えないこと
- 登録表を変えないこと
- 1 つのスレッドで動かすこと

### 5.2 記録機構（UP-5t-C1 の方式）をトレーナーに当てはめた場合の評価

UP-5t-C1 の `_probe_without_opponent_identity` と同じ扱いを、`check_play_trainer` の呼び出しに付けた場合を、結果ごとに評価しました。

| 結果 | 記録あり（相手のうらのカードを使った） | 記録なし |
|---|---|---|
| 受け付ける（例外なし） | 結果を使わず `unverified`。本当のカードによらない | 今のまま `may_stop_later` |
| `IllegalActionError` | **選べるものから外さず** `unverified`（外すと、本当のカードで選べるものの数・並びが変わりうる） | 今のまま外す |
| `UnsupportedError` | 停止のコードを使わず `unverified` | 今のまま実行できない区分 |
| ほかの例外（`RuntimeError`・`KeyError`・`MemoryError`・`KeyboardInterrupt`・`SystemExit` など） | 記録だけを戻して投げ直す（未確認に変えない） | 同じ |

記録が付くかどうかそのものが、本当のカードによらないことを確かめました。記録は `designate_face_down` の中の、本当のカードを読む前に付きます（`zones.py:151`）。

- ねむれ!ねむれ!
  - 記録の前の処理: 相手のバトル場の［でんせつのからだ］（公開）→ 複製 → `put_to_sleep` → `_require_active` → `_prevented` の `is_face_down`（公開）
  - 記録の有無は「相手のバトル場がうら」かつ「［でんせつのからだ］で止まらない」で決まる
- トロピカルウインド
  - 「おもて」の試行は、ダメージカウンターの数（公開）と［でんせつのからだ］（公開）だけで止まるかが決まる。止まれば記録の前に終わる
  - 「うら」の試行は、自分のバトル場 → 相手のバトル場の順。自分のバトル場の処理は本人の知識で、双子（相手の本当のカードだけが違う）では同じ
  - 相手のバトル場の `_prevented` で記録が付く
- 外側に記録の並びがある場合（エンジンの処理の中で呼ばれた場合）: UP-5t-C1 と同じく、新しい並びにして外側に書かず、同じオブジェクトに戻す。今の構造では、候補の作成はエンジンの処理の中から呼ばれない（`legal_actions` を import するのは `client_api` だけ）

トレーナーで特に注意すること:

- 記録が付いたあとの `stadium_trainer_cost`（リムーブ禁止ジムの追加の条件。公開）・MG1（公開）の拒否・停止も、`unverified` に覆われる
  - 公開の値で決まる拒否まで見えなくなる（漏れではないが、精度が下がる）
  - 6.2 の案 B' で分けられる
- 1 枚ずつ確かめるので、記録は手札のトレーナーカードごとに作り直す（1 枚の記録をほかのカードに持ち越さない）

## 6. 比べた案と、次の最小の作業

### 6.1 結論

**変更は要ります**（4.3 節の C）。公開の情報で事前に区別する案と、記録の案を比べ、記録の案（6.2 の B）を 1 単位として提案します。

### 6.2 比べた案

| 案 | 内容 | 利点 | 欠点 |
|---|---|---|---|
| A. 変更しない | 今のまま | なし | 4.3 節の C が残る（静的には判定が本当のカードによりうる） |
| P. 公開の情報で事前に区別する | 相手のバトル場がうら（公開）で、条件の型が 2 型（`CoinStatusOnOpponentActiveTrainer`・`CoinHealBothElseSleepBoth`）なら、条件を呼ばず `unverified`（`use_condition_not_evaluated` か `face_down_reveal_not_evaluated`） | 秘密を読む処理そのものを候補の作成で走らせない。記録の仕組みに頼らない | 型の名前の一覧が増える（`PLAYABLE_*` と同じ形）。新しい型が同じ経路に入っても一覧に加えるまで漏れる（走査・テストで見張る必要）。［でんせつのからだ］で止まる場合など、読まない場合まで未評価になる |
| B. 記録の案（UP-5t-C1 と同じ） | `check_play_trainer` を新しい空の `IDENTITY_CONSULTED` のもとで呼び、使う人でない持ち主が記録されたら、受け付ける・拒否・停止のどれでも結果を使わず `unverified`（`face_down_reveal_not_evaluated`） | 型・カードの名前によらない（読んだかどうかで決める）。新しい試行の型にも同じに効く。特殊能力の側と同じ仕組みで、記録の有無が公開の値で決まることは 5.2 節で確かめた | 秘密を読む処理は候補の作成で走る（結果を外へ出さない）。`check_playable` のあとの公開の拒否・停止まで覆う（5.2 節） |
| B'. 記録の案 + 公開の部分を先に分ける | B の前に `use_condition=False` で 1 回呼び、公開の確かめ（番・禁止・登録・リムーブ禁止ジム・MG1）の拒否・停止はその結果を使う。通れば B | 公開の拒否を覆わない | 呼ぶ回数が 2 倍。エンジンの順（`check_playable` が先）と、拒否のコードの優先が変わる場合がある（使うための条件の停止より、リムーブ禁止ジムの拒否が先に見える）。`use_condition=False` の扱いは既存の未評価の型と同じなので、前例はある |

推奨は B です。

- 特殊能力の側と同じ仕組み・同じ理由のコードで、GUI・AI の扱いが既存のまま
- 対象の盤面は、相手のバトル場がうらのカードで、手札に 2 型のトレーナーがあるときだけ。公開の拒否を覆うことによる精度の低下も、この盤面に限られる
- B' は、実装の単位で利用者が選べるように記しておきます

### 6.3 案 PT-5t-C1（1 単位）

| 観点 | 内容 |
|---|---|
| 根拠と影響 | 4.3 節。相手のバトル場がうらのカードのとき、ねむれ!ねむれ!・トロピカルウインドの候補の選べるもの・`eligible`・処理可能性・理由・check の結果（`CANDIDATE_NOT_EXECUTABLE`）が、使う人の知らない本当のカードによりうる |
| 対象 | `legal_actions._trainer_candidate` の `check_play_trainer` の呼び出し（使うための条件を呼ぶとき）。2 型を含む、試行が相手のうらのカードを使ったすべての場合 |
| 対象外 | エンジンの処理（`_apply`・`_identity_independent`）、裁定、効果の処理、ほかの候補の種類、PT-5e のガード、4.5 節の 7 型の前提、受理のあとの処理 |
| 最小の変更 | `legal_actions.py` だけ。<br>・UP-5t-C1 の `_probe_without_opponent_identity` を、確かめの関数とコマンドを受ける形に一般化する（または同じ形の関数を加える）<br>・`_trainer_candidate` で使ったら、その選べるものを `unverified`・理由 `face_down_reveal_not_evaluated`（と既存の `preflight_not_evaluated`・`continuation_not_evaluated`）にする。拒否でも外さない<br>・`GUARANTEE_TRAINER` の preconditions に 1 文を加える<br>・カード名・カード ID・型による分岐は加えない |
| 裁定・ゲーム処理 | 変えない（候補の評価の範囲だけ。送った場合はエンジンが今も本当のカードによらずに決める） |
| GUI への影響 | 値の語彙は増えない（`unverified`・`face_down_reveal_not_evaluated` は契約の表にあり、GUI の 0.178.0 の追従で表示の文を直してある）。トレーナーの選べるものに `unverified` が出るのは既存（`use_condition_not_evaluated`）。追従は固定のコミット・契約の engine の値・版のテスト。保証の文を照らす固定例があればその差 |
| AI への影響 | deep は `unverified` を選ばない（boundary・代替だけ）。`v2_repeat` の契約の値の固定値は、トレーナーの保証の文が加わると、トレーナーの候補を含む記録で変わりうる（どの記録が含むかは確かめていない。原因を確かめて来歴つきで更新。AI の追従は別の作業） |
| 双子の限定の検証 | 4.3 節の盤面（構築盤面。`tests/test_secret_plan_v0_67.py` の `board`・`place`・`to_active`・`face_down` と、使う人の手札にトレーナーを持たせる `opponent_hand`）。<br>・2 型 × 本当のカード 3 種（`RATTATA`＝たねポケモン・`KADABRA`＝たねポケモンでない・`DITTO`）<br>・**比べる前に確かめること**: 使う人と観戦者の観測・公開のログが同じで、相手本人の観測と完全な状態が違う<br>・本人の本当のカードが違う比較や、別の seed で公開の盤面が違う対戦は、同じ知識の双子と呼ばない<br>・比べるもの: 候補の有無・件数・順序・選べるものの数と並び・`eligible`・処理可能性・理由・inputs・check（正しい入力・不正な入力）・例外の有無。相手・観戦者への更新がないこと |
| 対照 | 次の 4 つ。<br>・相手のバトル場がおもて（今のまま `may_stop_later`）<br>・相手のうらのカードがベンチだけ（試行がおもてにしないので記録なし。今のまま）<br>・自分のバトル場がうらのカードでイマクニ？（本人の知識。`face_down_reveal_not_evaluated` にしない）<br>・トロピカルウインドの「おもて」の試行で止まる盤面があれば、記録の前の公開の停止のまま |
| 無副作用 | 候補・inputs・check の前後で、状態・乱数・ログ・決定が同じ。`IDENTITY_CONSULTED` は `None` に戻る。外側の並びは同じオブジェクトで書かれない。`RuntimeError`・`KeyError`・`MemoryError`・`KeyboardInterrupt`・`SystemExit` は投げ直し、記録は戻る（UP-5t-C1 の 11.4 節と同じ形） |
| 実行との接続 | U7・client_api・直接のコマンド（`apply_command(PlayTrainer)`）の受理・拒否が双子で同じ（受理のあとのコイン・公開は比べない）。check の成功を受理の保証として扱わない |
| 上限と完了の基準 | 新しいテストのモジュール 1 つ（双子 6 組・対照 4・記録の扱い）と、関連のモジュール（`u7_5c`・`up5t_c1_v0_178`・`pt5e`・`secret_plan_v0_67`・`client_api`・`from_state_integrity_v0_177`・`u7_1`）を 1 つずつ。全体のテスト・seed の探索・大量の対戦・GUI・E2E はしない。双子で応答が同じで、関連のモジュールが通れば完了。版を上げ（`behavior_digest` が変わる）、配布を確かめる |
| 残る制限 | 4.5 節の 7 型の前提（崩れた状態の低層の入口）。3.4 節の D。差の出る盤面の再現はしない（読んだら使わない方式なので、差が出る盤面でも同じ応答になる、という静的な根拠と、選んだ盤面での実行）。任意のデッキの new_game からの到達 |

最大 3 件のうち、ほかの 2 件は今回は提案しません。

- 4.5 節の 7 型のガードの非対称: 公開の入口が v0.177 から不変条件を確かめるので、必要性が低い
- 3.4 節の D: 静的には閉じられない前提で、実行の確かめで得られる範囲も限られる

## 7. 分類

| 起点・経路 | 分類 | 根拠・前提 |
|---|---|---|
| UP-5t: 状態のメソッドの 129 か所 | A | 受け手の型を型注釈から推論（3.1 節）。前提: 注釈が実際の値と合う |
| UP-5t: 多態の 31 か所（型・組み込み・`super` で解決） | A | 3.2 節。クラス階層の実装すべての本体を調べ、本当のカードを読む関数に届くのは既知の経路だけ。前提: 登録表の固定 |
| UP-5t: `IDENTITY_ORACLE.assign` の 2 か所 | A（前提つき） | 候補の作成では値が `None`。前提: 1 つのスレッド・外からの書きかえがない・候補の作成がエンジンの確かめの中から呼ばれない |
| UP-5t: `CoinConditionOnEitherActive`（相手のバトル場がうら） | C（v0.178 で対処済み） | UP-5t の監査 11 章 |
| UP-5t: 型注釈・登録・スレッドの前提そのもの | D | 3.4 節。静的には閉じられない |
| トレーナー: `check_play_trainer` の `check_playable` 以外の確かめ | A | 公開の値・本人の手札。本当のカードを読む関数に届かない |
| トレーナー: 52 型（ほか）・おもてにしない試行 3 型 | A | 4.2 節。前提: 登録表の固定・状態の不変条件 |
| トレーナー: PT-5e の 5 型 | A（前提つき） | PT-5e の監査。候補の側のガードで不変条件を確かめてから呼ぶ |
| トレーナー: おもての位置を読む 7 型 | A（前提つき） | 不変条件のもとで公開の枚数だけ。候補の側のガードはなく、公開の入口（`from_state`）が保証する。低層の入口・外からの書きかえは保証しない |
| トレーナー: 持ち主の知識の 6 型 | A | U7-5c 4.1 節（双子で確かめ済み） |
| トレーナー: イマクニ？・おどれ！neo★イマクニ？ | A | 本人の知識（自分のうらのカード） |
| **トレーナー: ねむれ!ねむれ!・トロピカルウインド（相手のバトル場がうら）** | **C** | 4.3 節。候補の側の試行が本当のカードを読み、判定が本当のカードによりうる。候補の側に保護がない。案 PT-5t-C1 |
| トレーナー: 同じ 2 型（相手のバトル場がうらでない） | A | 試行は公開の場と本人の知識だけ |
| B（安全な部分と未評価にすべき部分を分ける） | 該当なし（案 B' の形でだけ現れる） | 2 型の判定は 1 つの試行の結果なので、型の中では分けられない。`check_play_trainer` の公開の確かめと条件を分けるのは案 B' |

A の安全は、状態の不変条件（うらのカードの形・おもての山札の並び）、登録表の固定、1 つのスレッドに依存します。

`from_state` の確かめは、外から渡した状態の入口だけを保証します。次は保証しません。

- 信頼された内部の組み立て（`HostedGame(state)` など）
- 低層の API
- 外からの書きかえ

## 8. 閉じられる範囲・静的な確認・実行の確認が要る範囲

| 区分 | 内容 |
|---|---|
| 今回の監査で閉じられる | 次の 3 つ。<br>・UP-5t の D のうち、受け手の型の取り違えの懸念（129 か所と多態の 31 か所。型で解決した）<br>・`IDENTITY_ORACLE` の 2 か所（前提つきの A）<br>・トレーナーの 77 実装のうち、本当のカードを読む関数に届くのは 3 型で、相手の本当のカードは 2 型だけ |
| 静的な確認にとどまる | 7 章の A のすべて（実行で確かめたのは UP-5t-C1 の特殊能力の盤面だけ）。4.3 節の「判定が本当のカードによりうる」こと。5 章の無副作用 |
| 実行の確認が要る | 4.3 節の 2 型で、外へ出る差が実際に出るか（今回は再現しない）。PT-5t-C1 を実装した場合の双子・対照・無副作用・直接のコマンドとの一致（6.3 節）。任意のデッキの new_game からの到達 |

## 9. GUI・AI への影響（今回は変えていない）

- 今は 4.3 節の盤面で、トレーナーの選べるもの・処理可能性が本当のカードによりうる
  - GUI・AI は API の値を表示・選ぶだけで、原因を補えない
  - 送った場合の受け付けるかは、エンジンが本当のカードによらずに決める
- PT-5t-C1 を実装した場合は、6.3 節のとおり

## 10. 静的な監査の方法と限界

- 方法: `ast.parse` でパッケージの 55 のモジュールを読みました。`kyuura_engine` は import していません。登録はソースの式としてだけ見ました
- 型の推論は流れによりません。分岐で型が絞られる場合（`isinstance` の後など）は区別せず、和をとります。`Any` の項目・注釈のない戻り値は「分からない型」で、名前で広げました
- クラス階層で下の型をすべて含めたので、登録されていない型の実装も含みます（過大近似）。逆に、属性に入れた関数・`getattr` の名前が変数の呼び出しは追えません。閉包の中では、関数の引数として渡した callable の 3 か所（`_probe` の `check`・`_trial_stop` の `apply`・`deck_lower_bound_where` の `predicate`）を、渡す側の受け渡しの辺で追いました
- 本当のカードの読みは、関数への呼び出し（型で解決）と文字の検索で見ました。別名を通した読みは、`cards[…]`・`definitions` の使い方の文字で探しましたが、見落としはありえます
- 件数（528・771 など）は今回の方法による近似で、網羅や安全の証明ではありません。以前の件数（201・2,449・955）とは方法が違うので、比べられるのは 1 章に書いた包含の関係だけです
- 判定が本当のカードによりうることは、静的な読みで示しました。外へ出る差は再現していません

## 11. 実装・テスト・実行をしていないこと

- 次のことは、どれもしていません
  - エンジン・AI・GUI・renderer・kyuura のコードの変更
  - カードデータ・固定デッキ・規約集合・裁定・識別方式・版の変更
  - テスト、ビルド、対戦、seed の探索、GUI・E2E、全体のテスト、lockstep、状態の監査
  - `kyuura_engine` の読み込み（import）
- 走査と集計は、ソースの構文・テキストと保存済みの JSON を読むスクリプトだけです（証跡の `commands.txt`）
- 計画のファイルは作業の前に保存していません。走査を始めたあとで、方法と範囲をこの文書と証跡に書きました
