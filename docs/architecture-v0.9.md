# 設計の変更（v0.9）

v0.9 は、ゴースト（PMCG3-030。化石の秘密）のポケモンパワー「とうめい」（ワザによってダメージや効果を受けるときに自動的にはたらき、コインが「おもて」なら、そのダメージと効果を受けない。ねむり・マヒ・こんらんのとき、この力は消える）と、ワザ「あくむ」、進化元のゴース（PMCG3-029。したでなめる・エナジーへんかん）を加えた版です。原典の照合と裁定は [transparency-v0.9.md](transparency-v0.9.md)（T1〜T42・A4）と [haunter-line-v0.9.md](haunter-line-v0.9.md)（H1〜H13）、自動的にはたらく特殊能力の仕組みは [automatic-powers-v0.9.md](automatic-powers-v0.9.md)、確かめた結果は [v0.9-verification.md](v0.9-verification.md) です。

新しいのは「自動的にはたらく特殊能力の実装（`AttackImmunityOnHeads`。`declared = False`）」「ワザの要素の処理の境界の評価（`attack_reaches`・`evasion_power`）とワザ 1 回の中だけの記録（`AttackUse.reception`）」「公開の問い合わせ `working_evasion_power`」「2 つのワザの実装（`SleepOpponent`・`RecoverEnergyAndSelfDamage`）と決定の種類 `RECOVER_ENERGY`」「3 つのログのイベント（`evade_check`・`attack_evaded`・`recover_energy`）」「2 つの `UNRESOLVED_…` のコード」だけです。状態の項目・書き出しの形式（9 のまま）・コマンドの種類・段階は加えていません。

## 1. 既存の構造と `declared`（B1）

v0.8 までの特殊能力は、宣言して使うもの（`UsePokemonPower` → `engine._use_pokemon_power` → `check_usable`・`resolve`）と、常にはたらくもの（`declared = False`。`continuous.py` が今の状態から求める）でした。v0.9 の「とうめい」は 3 つ目の種類（決められたときに自動的にはたらく。p.323）です。

`PowerEffect.declared` の真偽値は「宣言するか」を表すには足ります（とうめいも宣言しない。`UsePokemonPower` は v0.8 と同じ `POWER_NOT_DECLARABLE`）。常にはたらく・自動的にはたらくの区別は表せませんが、エンジンがその区別を使う場所はなく、それぞれの効果を使う場所（かがくへんかガスは `continuous.py`、とうめいは `evasion_power`）が実装の型（`isinstance`）で探します。比べた案:

| 案 | 形 | 採否 |
|---|---|---|
| `declared` のまま、型で探す | 登録表・既存の API を変えない。v0.8 の `declared = False` の意味（宣言しない）はそのまま | **採用** |
| 種類の列挙（`kind = "declared" / "continuous" / "automatic"`）を `PowerEffect` に加える | 列挙を読む場所がない（どちらの効果も、使う場所が自分の型を探す）。v0.8 の `declared` と二重になり、食い違いの確認が要る | 不採用 |
| 登録表の欄を種類ごとに分ける | `PowerKey` → `PowerEntry` の 1 つの登録（照合の記録・cards.py の分類）を分けることになり、既存の API（`power_entry`・`with_powers`・`without_powers`）が変わる | 不採用 |

## 2. 自動発動の設計案（B2）

ワザの実装 18 種類（53 件）のすべてを読んで、ダメージと効果をどこで与えているかを確かめてから選びました（[automatic-powers-v0.9.md](automatic-powers-v0.9.md) 2.1 の表）。ダメージはどの実装も `deal_attack_damage` を通る（v0.2f から）が、特殊状態・入れ替えは実装ごとに `poison`・`put_to_sleep`・`paralyze`・`confuse`・入れ替えの決定を直接呼んでいます。

| 案 | 形 | 長所 | 短所 | 採否 |
|---|---|---|---|---|
| A. 各ワザの実装に個別の判定 | 実装ごとに「とうめい」のコインと記録を書く | 一部のワザでは変更が小さい | ダメージは 1 か所（`deal_attack_damage`）を通るのに、実装ごとに書くと重複する。1 つのワザで 1 回（T4）の記録を実装ごとに持つことになり、書き忘れ・二重のコインが起こりやすい（変異 4・18 の種類） | 不採用 |
| B. ワザによるダメージ・効果の適用の境界に共通の評価 | ダメージは `deal_attack_damage` の中、効果は与える直前に、共通の関数 `attack_reaches` を呼ぶ。コイン・ログ・記録は `attack_reaches` だけが行う | コイン・ログ・記録が 1 か所。ダメージは全実装が通る。効果の呼び出しは 1 行ずつ（ワザの要素の順番は実装のまま） | 効果を与える実装に呼び出しを加える必要がある（すべての実装を確かめ、表にした）。適用の単位（ワザ 1 回 × ポケモン）と時点（最終ダメージのあと）を決める必要がある | **採用** |
| C. 汎用のイベントの仕組み | 「ダメージを受ける」「効果を受ける」などのイベントを発行し、特殊能力を購読者として登録する | 将来の自動的にはたらく特殊能力に広げやすいかもしれない | 今は購読者が 1 つ（とうめい）だけ。イベントの順番・購読者の順番・取り消し・決定をまたぐ購読の状態を決める必要があり、書き出しの形式と不変条件が複雑になる。原典で決まっていない順番（T27）を仕組みが決めてしまう | 不採用（指示のとおり、今回必要のない汎用の仕組みは作らない） |

## 3. 評価する境界（B3）

候補（ダメージの計算の前・ダメージが決まったあと適用の前・効果の適用の前・対象のポケモンごとの処理の前・ワザ全体の処理の開始）を原典と照らしました。

- ワザ全体の開始（宣言のとき・こんらんのコインのとき）: 不採用。「このカードがワザによってダメージや効果を受けるとき」（p.160）で、ワザを使うときではない。ワザのコインがダメージの量を決めるワザ（みだれづき・ねばりつく）では、受けるより前にワザのコインがある（T19・T40）。最終ダメージが 0 の要素は「ダメージを受けなかった」（p.321）ので、計算の前には受けるかが分からない（T21）。
- ダメージの計算の前: 不採用（T20・T21）。
- **ダメージが決まったあと、のせる前**（`deal_attack_damage` の中。最終ダメージが 0 より大きいとき）と、**効果を与える直前**（ワザの実装の中）: 採用。受けるポケモンごとに評価する（T7・T26）。1 つのワザで 1 匹 1 回（T4）にするため、ワザ 1 回の記録を使う（4 章）。

## 4. 対象と発生源（B4）

`attack_reaches(state, use, owner, pokemon, element, *, amount=None)` が受け取る情報:

| 情報 | 持ち方 | 使い道 |
|---|---|---|
| ワザを使ったプレイヤー・ポケモン・ワザ | `AttackUse`（v0.4d から） | ログ `evade_check`（`attacker`・`attacker_pokemon_id`・`effect`） |
| 受けるポケモンと持ち主 | 引数 `pokemon`・`owner` | どの「とうめい」か（いちばん上のカード）・コインを投げるプレイヤー（T33） |
| ダメージか効果か | 引数 `element`（`ATTACK_ELEMENTS`） | ログ。ダメージなら受けなかった最終ダメージ（`amount`） |
| 1 つのワザの中の結果 | `AttackUse.reception`（場のポケモンの番号 → 受けるか） | 同じワザのあとの要素で投げない（T4）。複数のポケモンはそれぞれ（T26） |

状態（`GameState`）に加えた項目はありません。記録はワザ 1 回の処理の中だけの値で、決定をまたぐ必要がないことを確かめました（[automatic-powers-v0.9.md](automatic-powers-v0.9.md) 3 章）。「能力が発動したタイミング」は、ログの位置（`coin_flip` → `evade_check` → 要素の処理）で表します。

## 5. 乱数（B5）・原子性（B6）・きぜつ（B7）・かがくへんかガス（B8）

[automatic-powers-v0.9.md](automatic-powers-v0.9.md) の 4〜7 章。要点:

- 乱数: B5 の 7 つの保証を表にした（4 章）。コインはゴースト側のプレイヤー、1 つのワザで 1 匹 1 枚、はたらいていなければ使わない。原典で決められない場合（T19b）はワザの宣言の前に止める。
- 原子性: `apply_command` の複製のまま（新しい決定・段階を加えていない。「とうめい」はプレイヤーの選択がないので決定を出さない）。拒否はどれもコインの前。処理の途中の誤りを注入しても渡した状態は変わらない。
- きぜつ: 受けなかったダメージはのらないので、それできぜつしない。`DamageResult.knocked_out` は今のダメージで求める。きぜつの処理の時点（`_finish_attack`）は変えていない。
- かがくへんかガス: `evasion_power` が v0.8 の `continuous.suppressors_of` を聞く（判定を複製していない）。宣言する特殊能力と自動的にはたらく特殊能力の 2 つの経路から、同じ判定を聞く。

## 6. 保存形式（B9）

**形式 9 のまま（形式 10 を加えない）**。理由:

- 「とうめい」がはたらいているかは、今の状態（いちばん上のカード・特殊状態・場のベトベトン）から求める（v0.8 の案 B と同じ）。
- コインの結果（1 つのワザの中の記録）は、ワザ 1 回の処理の中で使い終わる。決定をまたいで要る対応カードはない（ふきとばしは受けるかを決めてから決定を出す）。番をまたぐ・回数を数える情報はない。
- 新しいワザの決定（エナジーへんかんの `RECOVER_ENERGY`）は、v0.4d の決定（形式 2 から）の形で表せる。

書き出しの監査の `LATEST_FORMAT` は 9 のまま。保存（pickle・`copy.deepcopy`・`clone`・形式 9）と復元のあとも同じ結果になることは `SaveRestoreTest`・`test_save_and_restore_in_the_decision`・[v0.9-verification.md](v0.9-verification.md) で確かめた。

## 7. 実装（C1〜C5）

- C1（自動発動型能力）: `AttackImmunityOnHeads(PowerEffect)`。`declared = False`、`check`（ポケモンパワー・説明文があること）、`is_working`（ねむり・マヒ・こんらんでない。どくは見ない）。登録は `PowerKey("PMCG3-030", 0)`（印刷の文面・最新の説明・出典 P43 p.160）。
- C2（ワザの処理）: `deal_attack_damage` の中（最終ダメージが 0 より大きいとき、のせる前）と、効果を与える実装 8 種類（`PoisonOnHeads`・`ParalyzeOnHeads`・`ConfuseOnHeads`・`PoisonOpponent`・`SleepOpponent`・`CoinBonusDamageAndParalyze`・`PutToSleep`・`PoisonWithoutDamage`）の特殊状態の前と、`DamageAndForceSwitch` の入れ替えの決定の前に `attack_reaches`。評価しない経路（自分への効果・こんらん・ポケモンチェック・トレーナー・特殊能力）と理由は [automatic-powers-v0.9.md](automatic-powers-v0.9.md) 2.1。
- C3（カード・ワザ）: ゴース（したでなめる = `ParalyzeOnHeads`、エナジーへんかん = `RecoverEnergyAndSelfDamage(max_cards=2, self_damage=10)`）、ゴースト（あくむ = `SleepOpponent`）。写しの `pool_v0_9`（scripts/extract_kyuura_cards.py の `POOL_V0_9`）と参照カード（第1弾のゴースト PMCG1-047）。照合の記録は card_verification.json。
- C4（ログ）: 8 章。
- C5（エラーコード）: 9 章。

## 8. ログ（C4）

| イベント | 項目 | 意味 |
|---|---|---|
| `coin_flip`（既存） | `source: "power"`・`effect`（特殊能力の `PowerKey`）・`player`（ゴースト側）・`card`・`pokemon_id`・`result` | 「とうめい」のコイン（`flip_coins` が残す。二重に記録しない） |
| `evade_check`（v0.9） | `player`・`pokemon`・`pokemon_id`・`power`・`attacker`・`attacker_pokemon_id`・`effect`（ワザの `AttackKey`）・`element`（最初に受ける要素）・`result`・`evaded` | 「とうめい」がはたらいた（判定した）。コインのすぐあとに 1 つ |
| `attack_evaded`（v0.9） | `player`・`pokemon`・`pokemon_id`・`effect`・`element`・`amount`（ダメージなら受けなかった最終ダメージ） | 受けなかった要素ごとに 1 つ（防がれたダメージ・効果） |
| `recover_energy`（v0.9） | `player`・`pokemon`・`pokemon_id`・`effect`・`cards` | エナジーへんかんで手札に加えたカード |

実際に適用された効果は、今までのイベント（`damage`・`special_condition`・`forced_switch`）です。受けたかを示す新しいイベントは加えていません（受けた要素は、判定の「うら」のあとに今までどおり処理される）。

### 8.1 ログの監査（tests/log_audit.py）

v0.9 から、ワザ（`attack` から番の終わりまで）ごとに次を確かめます。

1. はたらいている「とうめい」を持つポケモンが、ワザのダメージ（0 より大きい）・特殊状態・入れ替えを受ける前に、そのワザでの判定がある（その時点の場から求める。置きかわる特殊状態は、置きかわる前の状態で見る）。
2. 判定はワザ 1 回につき 1 匹 1 回。ワザの中だけ（ワザ・使ったポケモン・プレイヤーが合う）。
3. 判定の直前に、ゴースト側のプレイヤーの `source: "power"` のコインがあり、ポケモン・特殊能力・結果が同じ。特殊能力のコインのすぐあとに判定がある。
4. 判定したポケモンが、判定したプレイヤーの場にいて、いちばん上のカードに「とうめい」を持ち、ねむり・マヒ・こんらんでなく、はたらいているかがくへんかガスに消されていない（その時点の場から求める）。
5. 判定のすぐあと: 「おもて」なら同じ要素の `attack_evaded`、「うら」ならその要素の処理（`damage`（0 より大きい）・`special_condition`・`forced_switch`）。
6. 受けないと決まったポケモンが、そのワザでダメージ・特殊状態・入れ替えを受けていない。`attack_evaded` の前に「おもて」の判定がある。受けなかったダメージは 0 より大きい（T21）。
7. `recover_energy`: そのワザの中で、手札に加えたカードがログから組み立てたトラッシュのエネルギーカード（トラッシュ → 手札に組み立て直す）。

ログだけでは確かめられないこと（制約）:

- コインの結果が乱数と合っているか: ログには乱数の状態がない。自然な対戦のテスト（`test_randomness_is_only_coins`）が、対戦準備のあとの乱数を順に引いてコインのログと比べる。
- ダメージの計算（弱点・抵抗力・プラスパワー・ディフェンダー）が正しいか: 監査はログのダメージの量から組み立て直すが、計算をやり直さない。最終ダメージが 0 と誤って計算されると、判定がないことを見つけられない（変異 16 は単体テストで見つかる）。
- ワザの要素の順番がカードの説明どおりか: 監査はワザの説明を読まない（判定とそのあとの処理の対応・ワザの中かどうかは確かめる）。ワザのコインと「とうめい」のコインの順番は、単体テスト（`OneCoinPerAttackTest`）で確かめる。
- はたらいていない（コインを投げない）ことが正しいか: 判定がないことは、はたらいている「とうめい」があるときだけ問題にする（1）。はたらいているかを決める情報（いちばん上のカード・特殊状態・場のベトベトン）はログから組み立てている。

監査が何でも通すのではないことは、自然な対戦のログを 17 種類書きかえて、それぞれを報告することで確かめた（tests/test_haunter_games_v0_9.py の `LogAuditTransparencyTest`。D6 の 10 種類を含む。[v0.9-verification.md](v0.9-verification.md)）。

## 9. エラーコード（C5）

「とうめい」は自動的にはたらくので、正常にはたらいたこと・コインの「うら」をコマンドの拒否にしません（ワザは受け付け、ログに残す）。

| コード | 種類 | いつ | API への影響 |
|---|---|---|---|
| `POWER_NOT_DECLARABLE`（v0.8 から） | `IllegalActionError` | 「とうめい」の使用を宣言しようとした（T1・T37） | v0.8 と同じコード（説明文を「常にはたらく・決められたときに自動的にはたらく特殊能力」に直した。コードは同じ） |
| `UNRESOLVED_EVADED_EFFECT_COIN`（新しい） | `UnsupportedError` | T19b（[automatic-powers-v0.9.md](automatic-powers-v0.9.md) 4.1）。ワザの宣言の前（こんらんのコインの前。`AttackEffect.problem`） | 今まで受け付けていた「とうめい」のない対戦のワザは変わらない（前の版との比較で確かめた）。「とうめい」がはたらいているゴーストへの、`PoisonOnHeads`・`ParalyzeOnHeads`・`ConfuseOnHeads` のワザ（最終ダメージが 0 より大きい）だけを拒否する |
| `UNRESOLVED_RECOVER_ZERO_ENERGY`（新しい） | `UnsupportedError` | エナジーへんかんの決定で、トラッシュにエネルギーカードがあるのに 0 枚を選んだ（H4） | 決定に答える `ResolveDecision` の拒否。決定は待ったまま |

v0.8 までの 12 の `UNRESOLVED_…` のコードは変えていません（**R13 を含む**）。エンジンが止めるコードは 14 件（tests/test_unresolved_boundaries_v0_4e.py の `ALL_CODES`。それぞれ止まる場合と隣の止まらない場合を確かめる）。

### 9.1 拒否のコードの順番（API の約束）

v0.8 の 13 章の約束のまま。「とうめい」の宣言も、共通の確認（使うポケモン・特殊能力の有無・登録）→ `POWER_NOT_DECLARABLE` → `POWER_SUPPRESSED` の順で、かがくへんかガスがはたらいていても `POWER_NOT_DECLARABLE`（`test_declaring_under_the_gas_is_not_declarable`）。ワザの `UNRESOLVED_EVADED_EFFECT_COIN` は、ほかの確認（段階・番・エネルギー・ねむり・マヒ）がすべて通ったあと、こんらんのコインの前（v0.3c の `problem` の位置）。v0.6 の変異 19・v0.7 の変異 25 の非保証の範囲（`IllegalActionError` の理由どうしの順番）は変えていません。

## 10. 変えたもの

| 場所 | 変更 | 理由 |
|---|---|---|
| `effects.AttackImmunityOnHeads` | 加えた | C1 |
| `effects.attack_reaches`・`evasion_power`・`preview_attack_damage`・`evaded_effect_coin_problem`・`_require_not_evaded`・`ATTACK_ELEMENTS` などの定数 | 加えた | 3〜5 章 |
| `effects.AttackUse.reception` | 加えた（比較・表示に含めない） | 4 章 |
| `effects.DamageResult.evaded` | 加えた（既定 False） | 受けなかったことを後の要素に渡す |
| `effects.deal_attack_damage` | 最終ダメージが 0 より大きいとき、のせる前に `attack_reaches` | C2。受けるポケモンに、はたらいている「とうめい」がなければ v0.8 と同じ |
| 効果を与えるワザの実装 8 種類・`DamageAndForceSwitch` | 効果の前に `attack_reaches`。`PoisonOnHeads`・`ParalyzeOnHeads`・`ConfuseOnHeads` に `problem`（T19b） | C2 |
| `effects.SleepOpponent`・`effects.RecoverEnergyAndSelfDamage`・`decisions.RECOVER_ENERGY` | 加えた | C3 |
| `effects.working_evasion_power` | 加えた（`kyuura_engine` から公開） | 画面・ツールが、コマンドを送らずに「とうめい」がはたらいているかを調べるため（v0.8 の `power_suppressors` と同じ考え方） |
| `effects.DEFAULT_EFFECTS` | id を `kyuura-engine-0.9` に。ワザ 3 つ（50 → 53）とパワー 1 つ（4 → 5） | 登録の中身が変わった |
| `engine._use_pokemon_power` | `POWER_NOT_DECLARABLE` の説明文だけ | 自動的にはたらく特殊能力も含む文にした |
| `kyuura_engine.__init__`・pyproject.toml | `__version__` を `0.9.0`。`working_evasion_power` を公開 | — |
| `cards.POOL_KEYS` | `pool_v0_9` を加えた | 写しの対戦用のカードの組 |
| scripts/extract_kyuura_cards.py・kyuura_engine/data/kyuura_cards.json | `POOL_V0_9`（化石の秘密のゴース・ゴースト）と、参照カード（`REFERENCE_ONLY`）に第1弾のゴースト（PMCG1-047）を加えて写しを作り直した（参照コミット `ecb2d694` のまま。`--check` で一致） | 同じ名前の別のカードを区別するため |
| kyuura_engine/data/card_verification.json | PMCG3-029・PMCG3-030・PMCG1-047 の照合の記録 | 照合してから登録する（CLAUDE.md） |
| tests/log_audit.py | 8.1 章 | — |
| tools/stress_engine.py | ゴーストの 2 組（`haunter`・`haunter_muk`）。ゴーストが場にいる番はときどき「とうめい」の使用を試す（`POWER_NOT_DECLARABLE` になるはず）。ワザを受け付けるたびに、ワザの前の `working_evasion_power` と判定を比べる。`POWER_USERS` の最後にゴーストを加えたので、ゴーストのいない組は v0.8 と同じ操作 | 段階 C のストレス実行 |

## 11. 変えなかったもの

- コマンドの種類・段階（`Phase`）・再開先・書き出しの形式（9 のまま）・状態の項目。
- 既存のルールの処理・裁定の分類・処理の順番・きぜつの処理。v0.8 までの 12 の `UNRESOLVED_…`（R13 を含む）。
- v0.5 のエナジートランス・v0.6 のあまごい（通常の操作との区別・形式 9・R13 の停止）・v0.7 のダメージスワップ（きぜつさせない・カウンターの移動・監査）・v0.8 のかがくへんかガス（今の盤面から求める）。どれも「とうめい」の評価を通らない（T30）。
- K3（じこさいせいでトラッシュできないときの `RuntimeError`）: v0.9 のカードでも到達しない（じこさいせいはワザに「超」エネルギーが要るので、使うときに「超」の基本エネルギーカードがついている。エナジーへんかんはトラッシュから手札に動かすだけで、ついているエネルギーを変えない）。処理を変えていない。
- 固定値: tests/test_reproducibility.py、各対戦のテストの `GOLDEN_DIGEST`・`EXPECTED_COUNTS`、tests/fixtures/v0_1_reference.json・tests/fixtures/compat_base_4bd97bf.json。
- 比較の駆動（tools/compat_driver.py）。

## 12. 前の版との比較

`python3 tools/compare_engine_versions.py --base d057f57`（v0.8）: 8 つの組・50 局・11,377 手（受け付けた 6,005・拒否 5,322・内部の誤り 0）・形式の書き出し 91,016 で、食い違いは 0 局（[v0.9-verification.md](v0.9-verification.md)）。比べたのは記録のすべての項目（コマンドの受け付け・拒否のコード・状態の指紋（ログ・乱数・決定を含む）・乱数の指紋・段階・ログの長さ・形式 1〜8 の書き出し）。除いたのは効果の登録表の id（`kyuura-engine-0.8` → `kyuura-engine-0.9`）だけ。駆動の組にゴース・ゴーストはいないので、この比較は「とうめいが登場しない対戦の結果が変わらない」ことを確かめたもので、「とうめい」の正しさは単体テスト・自然な対戦・ストレス実行・変異テストで別に確かめた。

## 13. 変えた既存のテストと理由

どのテストも、確かめる内容（意図）は弱めずに、v0.9 の変更に合わせて値・一覧を直した。

| テスト | 変更 | 理由の種類 |
|---|---|---|
| tests/test_cards.py | `pool_v0_9` を確かめ、ゴース・ゴーストを対戦で使え、第1弾のゴーストを使えないことを加えた | 件数の変化（写しに v0.9 の組を加えた） |
| tests/test_effects.py | 説明文のあるワザの一覧にしたでなめる・エナジーへんかん・あくむを加え、ワザの登録の数を 50 → 53、パワーにとうめいを加えた | 件数の変化 |
| tests/test_pokemon_powers_v0_5.py | 登録は 5 つ（とうめいを加えた）。`repr` の「5 powers」 | 登録表の変化 |
| tests/test_chemical_gas_v0_8.py `test_registered_entry_matches_the_verification` | 「かがくへんかガスのほかの特殊能力はすべて宣言する」を「宣言しない特殊能力は、かがくへんかガスととうめいだけ」にした | 自動的にはたらく特殊能力を加えた（意図は「宣言しない特殊能力を取りちがえない」のまま） |
| tests/test_effect_preflight_v0_3d.py `ATTACKS`・`EVOLVED_FROM` | したでなめる・エナジーへんかん・あくむを加えた | CLAUDE.md（ワザの実装を加えたら `ATTACKS` にも加える） |
| tests/test_unresolved_boundaries_v0_4e.py | `ALL_CODES` に 2 つのコードを加え、それぞれ止まる場合と隣の止まらない場合のテストを加えた | 新しいコード |
| tests/test_trainers.py・tests/test_rng_and_serialize.py・tests/test_damage_swap_v0_7.py・tests/test_rain_dance_v0_6.py・tests/test_chemical_gas_v0_8.py・各対戦のテストの `GOLDEN_DIGEST` の前の `effects`（v0.4a〜v0.8） | 登録表の id を `kyuura-engine-0.9` にした（固定値の指紋は変えていない） | 登録表の id |
| tests/helpers.py | ゴース・ゴースト・第1弾のゴーストの定数を加えた | — |

## 14. 次の版への提案（G。実装していない）

例のカードの処理は照合していない（v0.8 の調査で画像を見たページだけを書く。実装するときに画像で照合する）。

| 種類 | 例 | 要る仕組み |
|---|---|---|
| ダメージを受けたあとにはたらく自動的な特殊能力 | カイリキー［はんげき］（p.192。v0.8 の 14 章） | `deal_attack_damage` のあと（ダメージをのせたあと）の評価。v0.9 の `attack_reaches`（受けるかを決める。のせる前）とは時点が違う。与え返すダメージがワザによるダメージか特殊能力によるダメージか（弱点・抵抗力・「とうめい」・ディフェンダーを計算するか）、きぜつの時点（ワザの要素をすべて処理したあとの `_finish_attack` で、同時のきぜつ（v0.2f の p.325）になる）、かがくへんかガス（`suppressors_of`）、受けたダメージが 0・防いだときにはたらくか、を原典で確かめる。決定がなければ形式 9 のままで済む見込み |
| 自動的に回復する特殊能力 | （未調査） | はたらく時点（番の終わり・ポケモンチェック）の位置。ポケモンチェックのどく・ねむり・マヒとの順番（p.323 の 1〜4）。コインがあれば乱数の保証（[automatic-powers-v0.9.md](automatic-powers-v0.9.md) 4 章） |
| 使用回数の制限のある特殊能力（「自分の番ごとに1回」） | v0.7 の 13 章 | 回数を状態に持つ（ログから数えない。v0.6 の `energy_attached_by_powers_this_turn` と同じ形）。書き出しの形式 10・不変条件（今の番のログと同じ数）・かがくへんかガスで消されている間の使用は数えない（宣言もない） |
| 期限のある特殊能力・特殊能力を消す期限のある効果 | まきちらせ！ベトベトガス（p.265）・ドガースのふしぎなガス（p.52） | 期限を状態に持つ（持続する効果の新しい型または `GameState` の項目）。`suppressors_of` の発生源を広げる。書き出しの形式 10・不変条件・ログの監査の組み立て直し |
| ベンチ・複数のポケモンにダメージを与えるワザ | レアコイル「じばく」（p.159 の例） | 受けるポケモンの選び方と計算（p.257。弱点・抵抗力を計算しないなど）を原典で確かめてから `deal_attack_damage` の種類を足す（CLAUDE.md）。複数の「とうめい」のポケモンが受けるとき、コインの順番は原典で決められない（T27）ので、コインの前に止める |
| ワザでほかのポケモンにエネルギーをつける | わるいマルマイン「エナジーボム」（p.159 の例） | 「とうめい」の「おもて」で、つけるはずのエネルギーカードはトラッシュ（T36。例のとおり）。つける処理の前に `attack_reaches`（新しい要素の種類） |
