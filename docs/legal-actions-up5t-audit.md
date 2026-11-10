# UP-5t の静的な監査（状態の複製の上で効果を試す特殊能力 7 型の使うための条件）

U7-5e（v0.171）で候補の作成に使うことにした、状態の複製の上で効果を試す特殊能力の 7 つの型について、過去の監査で名前で解決できなかった呼び出しの先を
ソースの構文で追い、候補・inputs・check の情報源と無副作用の根拠を整理しました。**調査・設計・文書化だけで、エンジン・AI・GUI のコード、テスト、ビルド、対戦の実行はしていません。**
`kyuura_engine` を import して登録を列挙することもしていません（9 章の方法の限界）。追記（v0.178）: 6 章の案 UP-5t-C1 を利用者が採用し、v0.178.0 で実装しました（11 章）。1〜10 章は監査のときの記録のままです。

## 0. 基点と範囲

| 項目 | 値 |
|---|---|
| コードの基点 | `a0c1312586eb726a5eb84e8374c5ac211d01ad94`（`claude/pt5e-from-state-fix`。from_state の修正 `09dc7f8`・版 0.177.0 の `01317a6`、PT-5e・U-R3a・検証用 AI の追従を含む。`origin/main`（`88ad4d9`）には入っていない） |
| 読んだコードの版 | パッケージ 0.177.0（`kyuura_engine/__init__.py`） |
| 参照した文書の版 | `docs/legal-actions-u7-5e.md`（v0.171 の記録と CORR-3 の訂正）、`docs/legal-actions-u7-5-design.md`・`.json`（UP-5t の行。v0.171 の記録）、`docs/verification-ai-inventory.md`（v0.177 までの追記）、`docs/legal-actions-r5-audit.md`（UP-5t を「監査が未完了」に移した記録） |
| 作業ブランチ | `claude/up5t-audit`（専用の worktree `C:\dev\kyuura-engine-vai`。利用者の `C:\dev\kyuura-engine` は main のまま、変更なし） |
| 証跡 | `C:/dev/kyuura-engine-verification-vai/verifier/runs/up5t-audit/`（走査のスクリプト・出力・コマンド） |

## 1. UP-5t の範囲

### 1.1 起点と、過去に確かめた範囲（文書の記録）

| 項目 | 内容 | 根拠 |
|---|---|---|
| 起点 | `effects.py` の 7 つの型の `check_usable`: `ChooseFossilEvolvedThenCoinDevolveAll`・`CoinConditionOnEitherActive`・`ReturnActiveToHandWithBenchLetters`・`Shapeshift`・`StopOpponentBenchPowersThisTurn`・`SwitchOpponentChosenByOpponent`・`SwitchOpponentOnHeads`（`scripts/build_legal_actions_u7_5_design.py` の `SCAN["check_usable"]["trials"]`。`.clone` を読む型を effects.py の中で数えた） | 文書・生成器 |
| 候補の側の呼び出し | `legal_actions._power_candidates` → `_power_candidate` → `_power_verdict` → `_probe(engine.check_use_pokemon_power, state, cmd)`（`use_condition=True`）→ 型ごとの `check_usable`。`_probe` は `IllegalActionError`（候補にしない）・`UnsupportedError`（実行できない区分。コードだけを使う）を捕まえ、文は返さない | コード（今回） |
| inputs・check | 発行した候補（`_Candidate`）の値を引くだけで、エンジンの確かめを呼ばない（`legal_actions._inputs`・`_check`・`_input_problem`）。check は実行できない区分を `CANDIDATE_NOT_EXECUTABLE` で断る | コード（今回） |
| v0.171 の記録 | 「パッケージ全体の呼び出しを名前で解決した閉包（955 の関数）で、山札・サイド・置いておくカード・乱数・うらのカードの集合を読まない（読むのは場・カードの定義・本人の手札）」「名前で解決できない呼び出し（状態のメソッド・登録表の引き・正規表現）は残る」「うらのカードの定義の読みは本当のカードによらず FD1」 | `docs/legal-actions-u7-5e.md` 4 章 |
| 955 の閉包の再現性 | **保存された走査のスクリプト・出力は見つからなかった**（コミット `a1c78f2` は文書と生成器の変更だけ。証跡のフォルダにも `955` の閉包の記録はない）。件数と結論は文書の記述としてだけ残る。今回は件数を安全性・網羅の証明として扱わず、別の方法で走査し直した | 今回の読み取り |

### 1.2 対象の型と登録（テキストの検索で）

| 型 | 登録（`effects.py` のテキスト） | 入力 |
|---|---|---|
| `CoinConditionOnEitherActive(CONFUSION)` | `PMCG4-006` わるいクサイハナの［くさいかふん］ | なし |
| `CoinConditionOnEitherActive(SLEEP)` | `PMCG4-033` スリープの［えんかくさいみん］ | なし |
| `SwitchOpponentOnHeads` | `PMCG5-015` エリカのウツボットの［かおりのわな］ | なし（受理のあとの決定） |
| `Shapeshift` | `PMCG5-019` タケシのキュウコンの［ばける］ | なし（受理のあとの決定） |
| `StopOpponentBenchPowersThisTurn` | `neo2-050` ［じっとみる］ | target（相手のベンチ） |
| `SwitchOpponentChosenByOpponent` | `neo4-021` ［おいはらう］ | なし |
| `ReturnActiveToHandWithBenchLetters` | `neo2-028` ［UNDO］（`_UNDO`） | なし |
| `ChooseFossilEvolvedThenCoinDevolveAll` | `ES2-028` ［かせきか］（`_FOSSILIZE`） | なし |

7 型・8 枚。登録は `PowerKey(...)` の文字列と別名の代入を読んだもので、別の経路の動的な登録は数えていません。

### 1.3 現在のコードとの差

- 走査し直した結果（9 章）、`effects.py` で `check_usable` を直接定義する 70 の型のうち、閉包が `GameState.clone` に届くのは記録と同じ 7 型だった（増減なし）
- 候補の側の呼び出しの順（`check_use_pokemon_power` の宣言の前の確かめ → `check_usable` → DV3）は、U7-5e の記録と同じ

### 1.4 UP-5t に含めるものと対象外

- 含める: 7 型の `check_usable` から到達しうる処理（複製の上の試行と、その先の効果のフック・状態のメソッド・登録表の引き）。候補・inputs・check で外へ出る値（候補の有無・件数・順序・eligible・処理可能性・理由・停止のコード・check の結果・例外）
- 対象外: 受理のあとの処理（`resolve`・`resume`・決定）。候補の側から呼ばれないので広げない。PT-5e（トレーナー）・UP-5o（持ち主の知識の関数）・R-2・R-4・R-5 の残り
- UP-5t は未裁定・未実装の項目ではなく、情報境界の監査の残件（`legal-actions-r5-audit.md` の区分のまま）

## 2. 未解決の呼び出しの追跡

### 2.1 方法

`up5t_scan.py`（証跡）でソースの構文木だけを読み、7 つの `check_usable` を根に呼び出しを解決しました。

| 呼び出しの形 | 扱い |
|---|---|
| 素の名前 | 同じモジュールの関数・型（型は `__init__`・`__post_init__`）、import した名前（別名・相対 import） |
| `self.m`・`cls.m` | その型と基底（同じパッケージ）のメソッド。なければ「self の多態」 |
| `mod.f`（import したモジュールの別名） | そのモジュールの関数・型 |
| それ以外の `x.m(...)` | 受け手の型を推論しない。`m` を定義する型の一覧を記録。**strict の閉包**は `state.py` の型（`GameState`・`PlayerState`・`PokemonInPlay` など）のメソッドだけを含め、**broad の閉包**は同じ名前の実装をすべて含める（過大近似） |

結果（直したあとの 2 回目。9.2 節の誤りを直した）:

| 閉包 | 関数の数 |
|---|---|
| strict（実際の到達の近似） | 201 |
| broad（名前だけで広げた上限） | 2,449 |

件数はどちらも網羅・安全の証明ではありません（受け手の型を決めない・条件で到達しない枝を含む・動的な呼び出しは記録するだけ）。v0.171 の 955 とは方法が違うので比べられません。

### 2.2 名前だけで解決した呼び出しと、実際の呼び出し先

| 種類 | 数（strict） | 結論 |
|---|---|---|
| 状態のメソッドを名前で解決（`card_def`・`find_pokemon`・`is_face_down`・`clone`・`add_event`・`printed_def` など） | 129 か所 | 受け手は文脈（引数の注釈・`state.` / `trial.` / `pokemon.`）から `GameState`・`PlayerState`・`PokemonInPlay` で、同じ名前の別の実装はパッケージにない |
| 多態の呼び出し（効果のフック・登録表の引き） | 34 か所 | 下の表 |
| パッケージに実装のない属性の呼び出し（`list.append`・`str.format`・`random.Random.getstate` など） | 78 か所 | 標準の型・ライブラリ。正規表現（`re`）の呼び出しは strict の閉包にない |
| 外部のモジュール | `itertools.product`・`dataclasses.replace`・`random.Random()`・`types.MappingProxyType` | 状態を読まない。`random.Random()` は `copy_rng` の中の新しい乱数（元の乱数の状態を写すだけ） |
| 動的な呼び出し（`getattr` の値の呼び出し・関数の受け渡し・辞書の値の呼び出し） | 0（`getattr(effect, "miracle"/"supplies_attacks"/"bench_only", False)` は属性の読みだけで、呼び出さない） | — |

多態の呼び出し（strict の閉包が名前だけで解決したもの）の、同じ名前の実装の本体を文字で調べました（`hooks_scan.py`）:

| 呼び出し | 受け手 | 実装 | 秘密の読み |
|---|---|---|---|
| `effect.status_allows`・`located`・`is_working`・`suppresses`・`hp_bonus`・`units`・`is_able` | 効果の登録の値（場のポケモンの特殊能力・特殊エネルギー） | 1〜11 | なし |
| `state.effects.power_effect`・`energy_effect`・`trainer_entry`・`trainer_effect`・`play_profile` | 登録表（`EffectRegistry`。対戦の状態が参照する既定の登録） | 各 1 | なし（読むだけ） |
| `pokemon.conditions.names()` | `SpecialConditions` | 2 | なし |
| `pokemon.cards()` | `PokemonInPlay`（`zones.return_in_play_to_hand`） | 4（ほかの 2 つは山札を読む効果の型の `cards` だが、受け手が違う） | なし |
| `IDENTITY_ORACLE.assign` | `engine` の確かめの道具（グローバル） | 1 | 候補の側では `IDENTITY_ORACLE` は `None` で呼ばれない（`engine._identity_independent` の中だけで置く） |
| `previous.get`・`super().__init__` | 辞書・例外の初期化 | — | なし |

### 2.3 解決できなかったもの

- 受け手の型を推論していないので、129 か所の状態のメソッドの受け手が本当に状態の型かは文脈の読みによる（静的な型の検査はしていない）
- 登録表の値（効果のフックの実装）は、登録されているすべての実装を調べた（名前で）。どの登録が呼ばれるかは盤面で決まる（静的には決めない）

## 3. 情報源

秘密に関わる読み・おもてにする処理・乱数・グローバルの文字が、strict の閉包のどの関数にあるか（`secret_call_sites.json`）:

| 読む値 | 場所（strict の閉包） | 中身 |
|---|---|---|
| 公開の場・特殊状態・効果・回数 | 全般（`form_problems`・`max_hp_drops`・`continuous_powers`・`require_power_not_used` など） | 公開 |
| 本人の手札 | `shapeshift_choices`（使うプレイヤーの手札の進化カード）・`place_disguise`（複製の上でのせる）・`return_in_play_to_hand`（複製の上で本人の手札へ） | 本人の知識 |
| 相手の手札 | なし | — |
| 山札の内容・順序 | なし（`PlayerState.clone` の写し、`devolve` の行き先が山札のときの書き込みの分岐だけ。［かせきか］の試行はトラッシュへ） | — |
| サイドと山札の配分 | なし（`clone` の写しだけ） | — |
| **うらのカードの本当の定義** | **`conditions._prevented` → `zones.designate_face_down` → `_secret_plan_keeps`（`printed_def`）→ `reveal_face_down`**（`CoinConditionOnEitherActive` の試行の `confuse`・`put_to_sleep` から）。ほかの読みは `card_def`（うらのカードは `FACE_DOWN_DEFINITION`）・`play_as_pokemon_effect`（場での役割のあるカードだけ `printed_def`。うらのカードの定義に役割はない） | 下の 3.1 |
| 乱数 | `GameState.clone` の `copy_rng`（写すだけ）。乱数を使う処理（`flip_coins`・`shuffle`・`random.` の呼び出し）は strict の閉包にない | 消費しない |
| 記憶・既知の情報 | `possible_deck_cards` などの知識の関数は strict の閉包にない（UP-5o は別） | — |
| 診断・ログ・決定 | 複製の上の `add_event`（ログのタプルを付け替える）。`_probe` は例外のコードだけを使い、文を返さない | 外へ出るのはコード |

### 3.1 秘密を読むことと、外へ出る結果が秘密によること

`CoinConditionOnEitherActive.check_usable` は、相手と自分の対戦ポケモンのそれぞれについて、複製の上で特殊状態にして `state_stop_after`（新しく決められない姿・最大HPの低下・［ずらかる］の戻り）で比べます。

- 相手の対戦ポケモンがうらのカード（マチスの秘策で出したカードを、にげる・入れ替えでバトル場に出した）なら、複製の上の `confuse`・`put_to_sleep` が `_prevented` → `designate_face_down(by_player=state.current_player, can_lose=True)` を呼び、`_secret_plan_keeps` が本当のカード（`printed_def`）を読む
  - 「たねポケモン」なら複製の上でおもてにして特殊状態にする（本当のカードの［めんえき］などの特殊能力も読む）。「たねポケモン」でなければ複製の上でトラッシュする
  - そのあとの `state_stop_after` は、おもてにした本当のカードを含む場で比べる。決められない姿・最大HPの低下・［ずらかる］の戻りが本当のカードで変わりうる（例: 本当のカードがメタモン・相手の場の力の発生源）
- コマンドの処理（`engine._apply`）では、同じ `check_usable` が `IDENTITY_CONSULTED` の記録のもとで呼ばれ、相手のうらのカードを読んだら `_identity_independent` がありうるカードのすべてで確かめ直し、受け付けるかを本当のカードによらないものにする
- **候補の側（`legal_actions._probe`）には、この保護がない**（`legal_actions.py` は `IDENTITY_CONSULTED`・`IDENTITY_ORACLE` を使わない）。候補の作成のあいだ `IDENTITY_CONSULTED` は `None` なので記録もされない
- したがって、この場合の候補の処理可能性（`may_stop_later` か、停止のコードから決まる実行できない区分か）・理由・check の結果（`CANDIDATE_NOT_EXECUTABLE`）が、使うプレイヤーの知らない本当のカードによって変わる**読みの経路がある**（静的に確かめた）。実際に応答が変わる盤面は確かめていない（双子の計画は 6 章）
- 自分の対戦ポケモンがうらのカードのときは、`by_player` が持ち主で、本人は本当のカードを知っている（本人の知識。漏れではない）

到達: 盤面は合法な操作（マチスの秘策・にげる）で作れる（既存のテストの `to_active`）。固定デッキには `PMCG5-093`（マチスの秘策）・`PMCG4-006`・`PMCG4-033` がない（`decks.py` のテキスト）。任意のデッキの new_game から合法な操作で届くかは確かめていない（届かない理由は見つかっていない）。不整合な状態だけの経路ではない。

### 3.2 ほかの 6 型（7 型のうち）と、うらのカード

| 型 | うらのカードの扱い |
|---|---|
| `SwitchOpponentOnHeads`・`SwitchOpponentChosenByOpponent` | 相手の控えにうらのカードがあっても、複製の上の入れ替え（`_switch_active_with_bench`）はおもてにしない。比べる値は `card_def`（`FACE_DOWN_DEFINITION`）と、うらのカードを数えない `max_hp_drops` で、本当のカードを読まない |
| `StopOpponentBenchPowersThisTurn` | 指定した相手のうらのカードは、試行の前に `holds_power` が偽（うらのカードは特殊能力を持たない。本当のカードによらない）で `TARGET_WITHOUT_POWER`。入力の段では、指定するうらのカードを含む組は候補の側で確かめず `unverified`（U7-5e の F-5） |
| `Shapeshift`・`ReturnActiveToHandWithBenchLetters`・`ChooseFossilEvolvedThenCoinDevolveAll` | 自分の場・自分の手札だけ。自分のうらのカードは本人の知識 |

## 4. 無副作用の根拠

| 観点 | 読み取りの結果 |
|---|---|
| 複製の深さ | `GameState.clone` は `__dict__` の浅い写しに、`players`（`PlayerState.clone`: 山札・手札・サイド・トラッシュの list、場のポケモンは `PokemonInPlay.clone`）と乱数（`copy_rng`）を写し直す。`PokemonInPlay.clone` は `energy`・`trainers` の list を写し、ほかの項目（特殊状態・持続する効果・重なりなど）は同じ値を共有する（試行はそれらを付け替えるだけで、その場で変える書き込みは strict の閉包に見つからなかった） |
| 試行の書き込み | strict の閉包の書き込みは、複製の場のポケモンの属性の付け替え（`conditions`・`persistent_effects`・`disguise`・`super_transform`・`type_shift`）、複製の領域の list の変更（手札・トラッシュ・`trainers`）、状態の項目の付け替え（`face_down_cards`・`color_effects`・`poison_mists`・`frozen_forms`・`log`）、局所の辞書。元の状態と共有する可変の値を、その場で変える書き込みは見つからなかった |
| ログ・決定・停止・履歴 | 複製の上の `add_event`（ログのタプルの付け替え）。決定・停止は作らない（停止は例外のコードで返す） |
| 乱数 | `copy_rng` で写す。消費する処理は strict の閉包にない |
| グローバル | `persistent._SCARE_SOURCES_IN_PROGRESS`（循環の検出の集合。`try`／`finally` で必ず外す）。`zones.IDENTITY_CONSULTED.append` は `None` でない（コマンドの処理の中）ときだけで、候補の側では呼ばれない。キャッシュの装飾・ファイル・`global` の書き込みは strict の閉包にない |
| 例外の経路 | 書き込みは複製だけなので、例外で試行を抜けても元の状態は変わらない。グローバルの集合は `finally` で戻る |

前提: 元の状態が `PokemonInPlay` などの共有する値を不変として扱う規約（PT-5e の前提 B と同じ。可変の list は `clone` で写す）。登録表（`state.effects`）を読むだけで変えないこと。1 つのスレッドで動かすこと（`zones` のグローバルを並行に置かない）。

## 5. 分類

| 起点・経路 | 分類 | 根拠・前提 |
|---|---|---|
| `Shapeshift`・`ReturnActiveToHandWithBenchLetters`・`ChooseFossilEvolvedThenCoinDevolveAll` | A | 読むのは自分の場・本人の手札・公開の値。試行は複製の上だけ。前提: 4 章 |
| `SwitchOpponentOnHeads`・`SwitchOpponentChosenByOpponent` | A | 相手のうらの控えは `FACE_DOWN_DEFINITION` で扱い、おもてにしない。前提: `card_def` のうらのカードの扱い（v0.67）・4 章 |
| `StopOpponentBenchPowersThisTurn` | A | 指定するうらのカードは試行の前に本当のカードによらず断る。入力の段の F-5 の `unverified` |
| `CoinConditionOnEitherActive`（相手の対戦ポケモンがうらのカードでないとき） | A | 試行は公開の場と本人の知識だけ |
| **`CoinConditionOnEitherActive`（相手の対戦ポケモンがうらのカード）** | **C** | 候補の側の試行が本当のカード（`printed_def`）を読み、おもてにした場で停止を比べる。コマンドの処理には本当のカードによらなくする保護があるが、候補の側にはない（3.1 節）。応答が実際に変わる盤面は未確認（D の部分）。候補の側では評価しない（`unverified`）にすべき。**v0.178 で直した（11 章）** |
| 7 型の broad の閉包の残り（名前だけで広げた 2,449 のうち strict にないもの）・129 か所の状態のメソッドの受け手 | D | 受け手の型を推論していない。strict の閉包と多態のフックの本体は調べたが、受け手の取り違えがないことは静的な型の検査では確かめていない |

A の安全は、状態の不変条件（`check_invariants` のうらのカードの形など）と登録の固定に依存します。v0.177 の `from_state` の確かめは外から渡した状態の入口だけを保証し、信頼された内部の組み立て・低層の API・外部の書きかえは保証しません。

## 6. 次の最小の作業（1 単位）

**案: UP-5t-C1 — 候補の側の使うための条件の確かめで、相手のうらのカードの本当のカードを読んだら評価しない**

| 観点 | 内容 |
|---|---|
| 根拠と影響 | 5 章の C。相手の対戦ポケモンがうらのカードのとき、［くさいかふん］・［えんかくさいみん］の候補の処理可能性・理由・check の結果が、使うプレイヤーの知らない本当のカードによりうる |
| 範囲 | `legal_actions` の `_power_verdict` の `check_use_pokemon_power` の呼び出しを、エンジンと同じ記録（`zones.IDENTITY_CONSULTED` に空の list を置き、`finally` で戻す）のもとで行い、相手のうらのカードを読んだと記録されたら、結果を使わず `unverified`（理由 `face_down_reveal_not_evaluated`）にする。カード名・カード ID・型による分岐は加えない（読んだかどうかで決める）。エンジンの処理（`_apply`）・裁定は変えない |
| API・GUI・AI | 値の語彙は増えない（`unverified`・既存の理由）。その盤面の候補が `may_stop_later`・実行できない区分から `unverified` に変わる。GUI は既存の表示・check の門で扱える見込み。AI の deep は `unverified` を選ばない（boundary・代替だけ） |
| 裁定の判断 | 不要（裁定は変えない。候補の評価の範囲だけ） |
| 既存の挙動 | 候補の表示が変わる（上の盤面だけ）。submit・エンジンの受理は変わらない（エンジンは今も本当のカードによらない） |
| 最小の限定の検証 | 双子（下）・無副作用（候補・inputs・check の前後で状態・乱数・ログ・グローバルの記録が同じ。例外でも `IDENTITY_CONSULTED` が戻る）・自分のうらのカードの対戦ポケモンでは今のまま評価する（本人の知識）・相手の対戦ポケモンがうらでない盤面は変わらない・直接のコマンドとの一致（受理・拒否はエンジンのまま） |
| 完了の基準 | 双子で候補・inputs・check の応答が同じ。既存の U7-5e・U7-5g・U-R3a・P6 の関連モジュールが通る。版を上げ、配布を確かめる |
| 残る制限 | 2,449 の broad の閉包のうち strict にない部分と受け手の型（D）。受理のあとの処理は対象外 |

双子の計画（今回は実行しない）:

- 盤面: プレイヤー 0 の番の MAIN。プレイヤー 0 のバトル場にわるいクサイハナ（または スリープ）、プレイヤー 1 のバトル場に、マチスの秘策でうらにして出したカード（`tests/test_secret_plan_v0_67.py` の `board`・`place`・`to_active` の合法な経路。相手の番で出し、にげるでバトル場へ）
- 双子: プレイヤー 1 のうらのカードの本当のカードだけが違う（例: たねポケモン・たねポケモンでないカード・メタモン）。山札・手札・サイドの並びと枚数・ほかの場は同じ
- 比べる前に確かめること: プレイヤー 0 と観戦者の観測（`observe`）・公開のログが同じで、完全な状態が違う。プレイヤー 0 は本当のカードを知らない（ログの `secret_plan_placed` の `card` は持ち主だけが見る）
- 比べるもの: 候補の有無・件数・順序・eligible・処理可能性・理由・inputs・check の答え（実行できるか）・例外の有無。前後の状態・乱数・ログ・`zones` のグローバル
- 対照: プレイヤー 0 自身のうらのカードがバトル場のとき（本人の知識なので、本当のカードで変わってよい）。相手の対戦ポケモンがうらでないとき（今と同じ）
- 本人の本当のカードが違う比較や、別の seed で公開の盤面が違う対戦は、同じ意味の双子と呼ばない

UP-5t を文書の残件から閉じられる範囲: 5 章の A の 6 型と、`CoinConditionOnEitherActive` の相手の対戦ポケモンがうらでない場合。C の 1 つ（上の案）と D（受け手の型の静的な確かめ）は残る。

## 7. 確認の種類

| 種類 | 内容 |
|---|---|
| 今回静的に確かめたこと | 1〜5 章（ソースの構文とテキストの読み。走査のスクリプトと出力は証跡） |
| 既存のテストが主張していること | U7-5e の 24 件（宣言の表・代表の組の直接のコマンドとの一致・F-4 のへんしょくの双子）。U7-5e の文書の「候補・inputs・check で状態・乱数・ログを変えない」。7 型の相手のうらの対戦ポケモンの双子のテストは見つからなかった（`PMCG4-006`・`PMCG4-033` を使うテストに、うらのカードの盤面はない） |
| 保存済みの実行の証跡 | v0.171 の 955 の閉包の走査は保存されていない（文書の記述だけ） |
| 今後確かめること | 6 章の双子（C の応答が実際に変わるか、修正のあとに同じになるか）、D の受け手の型、任意のデッキの new_game からの到達 |

## 8. GUI・AI への影響（今回の監査では変えていない）

- 今は C の盤面で、候補の処理可能性が本当のカードによりうる（GUI・AI は API の値を表示・選ぶだけで、原因を補えない）
- 6 章の案を実装すれば、その盤面の候補は `unverified` になる（GUI の表示の語彙・AI の deep の条件は既存のまま）

## 9. 静的な監査の方法と限界

- 方法: `ast.parse` でパッケージの 55 のモジュールを読み、2 章の規則で呼び出しを解決した。`kyuura_engine` を import していない。登録はテキストの検索
- 走査の誤りと直し: 1 回目の走査（strict 171・broad 2,224）は、`self.m`・別名のモジュールの関数・型のメソッドの呼び出しで、呼び出し先を積む前に次へ進む誤りがあった（［かせきか］の `self.candidates` の先が欠けた）。直した 2 回目（strict 201・broad 2,449）を結果とした。1 回目の出力は上書きした（コマンドの記録に残す）
- 限界: 受け手の型を推論しない。条件で到達しない枝も含める（過大近似）、逆に、属性に入れた関数・辞書の値・`functools.partial` の先などを呼び出しとして追わない（strict の閉包では 0 件だったが、方法として見落としうる）。文字で読む秘密の読み（`.deck`・`printed_def(` など）は名前の一致で、別名を通した読みは見落としうる。正しさを件数で示すものではない

## 10. 実装・テスト・実行をしていないこと

エンジン・AI・GUI のコードの変更、テスト、ビルド、対戦、seed の探索、GUI・E2E、全体のテスト、lockstep、状態の監査は、どれもしていません。`kyuura_engine` を読み込むことも、ゲームを動かすこともしていません。

## 11. UP-5t-C1 の実装の結果（v0.178.0。利用者が 6 章の案を採用）

1〜10 章は監査のときの記録（版 0.177.0・基点 `a0c1312`）のままです。v0.178.0 で、5 章の C（相手の対戦ポケモンがうらのカードのときの `CoinConditionOnEitherActive`）だけを直しました。
裁定・コマンドの処理・効果の処理・`_identity_independent` は変えていません。

### 11.1 修正の前に観測したこと

| 確かめ | 結果 |
|---|---|
| 盤面 | 構築盤面（`tests/test_secret_plan_v0_67.py` の `board`・`place`・`to_active`・`face_down`。プレイヤー 0 がうらにして出したカードに、にげるで入れ替えて番を終える。プレイヤー 1 のバトル場にわるいクサイハナ（ロケット団のナゾノクサから進化）かスリープ）。`check_invariants` は空。new_game からの到達ではない |
| 変えた秘密 | プレイヤー 0 のうらのカードの本当のカード（コラッタ＝たねポケモン・ユンゲラー＝たねポケモンでない・メタモン） |
| 比べる前の確かめ | プレイヤー 1 と観戦者の観測・公開のログは同じ。プレイヤー 0 の観測と完全な状態は違う（全員の知識が同じではない） |
| 応答の比べ（2 つの特殊能力 × 3） | **外へ出る差は出なかった**（どれも `may_stop_later`・`continuation_not_evaluated`、check は valid、相手・観戦者への更新なし） |
| 秘密の読み | 候補の作成のあいだに、`zones._secret_plan_keeps` が相手のうらの対戦ポケモンについて呼ばれ、`IDENTITY_CONSULTED` は `None`、戻り値は本当のカードで違った（コラッタ・メタモンは真、ユンゲラーは偽）。読みは実行でも確かめた |

監査で見つけた秘密の読みは実際にあり、今回選んだ盤面では外へ出る差にならなかった、という結果です。差の出る盤面を探す広い探索はしていません（漏れの再現はしていない）。

### 11.2 方式

| 案 | 比べた結果 |
|---|---|
| 計算の前に退避する（相手の場にうらのカードがあれば評価しない） | どの特殊能力がうらのカードを試行に使うかは、型・カードを見ないと決まらない。相手の場にうらのカードがあるだけで、うらのカードに触れない特殊能力まで未評価になる。採らなかった |
| 既存の記録を使い、使ったら結果を捨てる（採用） | `designate_face_down` は、本当のカードを読む前（`_secret_plan_keeps` の前）に相手を `IDENTITY_CONSULTED` に記録する。記録は公開の場の値（うらのカードがどこにあるか）と、そこまでの公開の値による処理の順で決まるので、記録の有無そのものは秘密によらない |

- `legal_actions._probe_without_opponent_identity`: `check_use_pokemon_power` を `_probe` と同じに呼ぶ。そのあいだだけ `zones.IDENTITY_CONSULTED` を新しい空の並びにし、`finally` で前の値に必ず戻す（外側に並びがあっても、それには書かず、同じオブジェクトに戻す）。記録のうち、使うプレイヤーでない持ち主があれば「使った」
- `_power_verdict`: 使ったら、受け付ける・拒否（`IllegalActionError`）・停止（`UnsupportedError`）のどれでも結果を使わず、`unverified`・理由 `face_down_reveal_not_evaluated`。読んだあとの拒否・停止で候補の有無・理由が分かれない
- ほかの例外は捕まえない（記録だけを戻して投げ直す）。`MemoryError`・`KeyboardInterrupt`・`SystemExit` も、ふつうの不具合（`RuntimeError` など）も未確認に変えない
- エンジンの `_identity_independent`（ありうるカードを置きかえて確かめ直す）は候補の作成に持ち込んでいない。試行は複製の上のまま（読む処理そのものは残る。結果を外へ出さない）
- 自分のうらのカード（本人の知識）は記録に数えず、今までどおり評価する。カード名・カード ID・型による分岐は加えていない
- `GUARANTEE_POWER` の preconditions に 1 文を加えた（「確かめが相手のうらのカードの本当のカードを使ったら、その結果を使わない（unverified）」）

### 11.3 構造の入力と check の保証の範囲

- 対象の 2 つの特殊能力は入力のない候補（`input_disclosure` `no_input`・段なし・`choices_format` `[]`）。`unverified` にしても入力の形は変わらない
- check は、発行した候補の段と参照の構造（入力が `[]` か）だけを検査する。valid は使えること・受理・完走の保証ではない（`eligible` もエンジンが使えると判定した意味ではない）
- 送った場合の受け付けるかは、コマンドの処理（`_identity_independent`）が本当のカードによらずに決める（変えていない）

### 11.4 限定の検証

新しいモジュール `tests/test_legal_actions_up5t_c1_v0_178.py`（11 件）:

| 種類 | 確かめ |
|---|---|
| 情報境界 | 2 つの特殊能力 × 3 つの双子で、比べる前の知識の一致と、候補の有無・件数・順序・処理可能性・理由・入力の公開・inputs・check（`[]`・不正な入力）が同じ。相手・観戦者への更新なし。候補・inputs・check の前後で状態が同じ、記録の並びは `None` に戻る。修正のあとも本当のカードを読む処理は呼ばれ、読む前に相手が記録されること |
| 対照 | 相手の対戦ポケモンがおもて: `may_stop_later` のまま。自分のうらの対戦ポケモン（本人の知識）: `face_down_reveal_not_evaluated` にしない。公開の条件で使えない（こんらん）: どの双子でも候補なし |
| 記録の扱い | 使ったあとの受け付け・拒否・停止はどれも `unverified`、使っていなければ今までどおり。本人の記録は数えない。外側の並びは同じオブジェクトで、書かれない。`RuntimeError`・`KeyError`・`MemoryError`・`KeyboardInterrupt`・`SystemExit` は投げ直し、記録は戻る |
| 実行との接続 | U7・client_api・直接のコマンドの受理・拒否・診断が一致し、受け付けるかは双子で同じ（本当のカードによらない）。check の成功は受理の保証として扱わない。受理なら公開の更新・取っ手の取り直し、拒否なら無変更・本人だけへの診断 |

実行（1 つずつ別のプロセス）:

- 新しいモジュール: 1 回目は失敗 1・エラー 6（テストの作りの誤り: ねむりは相手の番の終わりのポケモンチェックで治る → こんらんに、`ActionResult` に `result` はない → `outcome`・`view`）。直して 2 回目は 11 件 OK
- 関連: `u7_5e`・`u7_5g_face_down_power`・`u_r3a_v0_175`・`p6_face_down_retreat_v0_174`・`secret_plan_v0_67`・`client_api`・`from_state_integrity_v0_177`・`u7_1`・検証用 AI の `v0176_follow`、版のあとの `preset_decks_v0_20`・`distribution` はどれも 1 回目で OK
- 検証用 AI の `test_verification_ai_v2_repeat`: 失敗 2（rules-v1-s13・mixed-v1-s13 の `candidate-contract/v1` の指紋）。use_power の保証の文だけを 0.177.0 の文に戻すと 4 つとも固定値に一致し、行動の列（`action-meaning/v2`）はどちらでも同じ（証跡の `ai_contract_probe.json`）。契約の値の変化を別の照らしが見つけた、意図した検出。AI の固定値は変えていない（AI の追従は別の作業）
- 限定の検証の合計は約 2.5 分。全体のテスト・GUI・E2E・AI の実対戦・大量の対戦・seed の探索・lockstep・状態の監査はしていない

### 11.5 版・識別・配布

- 版 0.178.0。識別方式は同じ。`legal_actions.py`（振る舞いのファイル）を変えたので `behavior_digest` が `68ee4ab4…4727` から `140f4a096d304290d82b6b825531732fe9d112dd54703589690a36526bf038b7` に変わった。`instrumentation_digest`（`d3436748…146d`）は同じ
- 0.177.0 の完全な記録・スナップショットは 0.178.0 では再実行・復元できない（既存の設計）。過去の証跡は旧い版のまま
- 配布するファイルは 62 で同じ（新しい実行時のファイルなし）。`pyproject.toml` の差は版だけで新しい依存なし。wheel の照らしは required=62・problems=0
- 配布用の固定コミット `8f5329d6fb9eeeb783f3d6f57128069ffc0d98a0` を、リポジトリの外の新しい venv に Git の URL から通常のインストールをしてスモークを 1 回した（終了コード 0）: `direct_url` のコミットが一致、site-packages から読み込み（editable でない）、版と実装の識別がソースと一致、依存なし。今回の版で作ったスナップショット（双子 2 つと、おもての対照）を復元し、［くさいかふん］の候補は双子で同じ `unverified`・`face_down_reveal_not_evaluated`・段なし・構造の check は valid、おもての対照は `may_stop_later`。相手・観戦者への更新なし

### 11.6 GUI・検証用 AI への影響（読み取りだけ。どちらも変えていない）

- GUI（最新の公開の `feature/engine-0177-from-state` の `0412561`。エンジン 0.177.0 を固定）: 契約の表の `executable_processability` に `unverified`、`reason_codes` に `face_down_reveal_not_evaluated` がある。値の語彙は増えていないので、既存の表示と check の門で扱える見込み。追従は、固定のコミット（`8f5329d` 以降）・契約の engine の値・版のテスト・use_power の保証の文の差（保証の文を照合・表示している固定例があれば、その差）の更新。項目が増えないことは、実際の動作の互換の保証ではない（GUI では確かめていない）
- 検証用 AI: deep は `unverified` を選ばない（boundary・代替だけ）。judge の `EXPLAINING_REASONS` に `face_down_reveal_not_evaluated` がある。`v2_repeat` の契約の値の固定値（rules-v1-s13・mixed-v1-s13）は、保証の文の変更で更新が要る（来歴つき）。行動の列・方策は変わらない

### 11.7 残る UP-5t

- 5 章の D: 7 型の broad の閉包のうち strict にない部分と、状態のメソッドの受け手の型の静的な確かめ（静的な監査だけ。実行で確かめていない）
- 5 章の A は静的な監査の結論で、今回の実行で確かめたのは C の 2 つの特殊能力の盤面と対照だけ
- 差の出る盤面（本当のカードで候補が変わる盤面）は再現していない。修正は、読んだら使わない方式なので、差が出る盤面でも同じ応答になる（静的な根拠と、今回の盤面での実行）
- 新しい特殊能力・トレーナーで同じ記録が付く経路は、この修正の対象（use_power の候補）では同じに扱う。トレーナーの候補（`play_trainer`）の確かめには入れていない（監査の範囲の外）
- 追記（v0.178 のあと）: D の受け手の型と、トレーナーの候補の同じ経路を、型の推論つきの走査で監査した（[legal-actions-up5t-d-trainer-audit.md](legal-actions-up5t-d-trainer-audit.md)。文書だけ）。129 か所・多態の 31 か所は型で解決し、ねむれ!ねむれ!・トロピカルウインドの候補の試行が相手のうらのバトル場の本当のカードを読む C を見つけた（案 PT-5t-C1）
