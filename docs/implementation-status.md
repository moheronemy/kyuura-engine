# 実装状況（v0.1〜v0.2f）

基準: 公式ルール 2000.02.14版（『ポケモンカードオフィシャルブック2000』pp.306〜326 [P43]）、kyuura `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`。項目ごとの根拠は [ルールの仕様](rules-2000-02-14.md) にあります。v0.2 の前のレビューの結果は [review-v0.1.md](review-v0.1.md)、公開 API の評価は [api-review.md](api-review.md) にあります。

v0.2a は、v0.1 のルールと対戦の結果を変えずに、カード効果を実装するための構造を整えた版です（[アーキテクチャ](architecture-v0.2a.md)）。v0.2b は、その構造を使ってトレーナーカード 3 枚（マサキ・きずぐすり・ポケモンいれかえ）を実装した版です（[アーキテクチャ](architecture-v0.2b.md)、[原典照合](trainers-v0.2b.md)）。v0.2c は、プラスパワーと、場に残るトレーナー・有効期限・ダメージ計算の段階への効果の適用を加えた版です（[アーキテクチャ](architecture-v0.2c.md)、[原典照合](pluspower-v0.2c.md)）。v0.2d は、コイントスと、コインの結果でダメージが変わるワザ（ドードーの「みだれづき」）を加えた版です（[アーキテクチャ](architecture-v0.2d.md)、[コイントスの規定](coin-rules-v0.2d.md)、[みだれづき](coin-attacks-v0.2d.md)）。v0.2e は、ディフェンダーと、防御側のダメージ変更・相手の番にまたがる有効期限を加えた版です（[アーキテクチャ](architecture-v0.2e.md)、[原典照合](defender-v0.2e.md)）。v0.2f は、ワザで自分に与えるダメージと、同時のきぜつ（両方のプレイヤーのポケモンが 1 つのワザできぜつする）を、ピカチュウの「かじる」「でんげき」とともに加えた版です（[アーキテクチャ](architecture-v0.2f.md)、[自分へのダメージ](self-damage-v0.2f.md)、[同時のきぜつ](simultaneous-ko-v0.2f.md)、[ピカチュウ](pikachu-v0.2f.md)）。それぞれの状況は [v0.2a の章](#v02a-で加えた構造)・[v0.2b の章](#v02b-で加えたものトレーナー)・[v0.2c の章](#v02c-で加えたものプラスパワー)・[v0.2d の章](#v02d-で加えたものコイントスとみだれづき)・[v0.2e の章](#v02e-で加えたものディフェンダー)・[v0.2f の章](#v02f-で加えたもの自分へのダメージと同時のきぜつ) にあります。

状態の区分:

- **実装済み・テスト済み**: コードがあり、その規定を確かめる自動テストがある
- **実装済み・テスト限定**: コードはあるが、対応カードでは起こらないため、手順を直接呼ぶテストか、テストがない
- **部分対応**: 原典で確定した場合は実装し、原典で決められない場合は `UnsupportedError` で止める
- **未実装**: コードがない（受け取ったら `UnsupportedError`、またはデッキに入れられない）
- **原典未確認**: 原典（誌面）で確かめていない、または確かめきれていない
- **裁定が未解決**: 原典を読んでも決められない

## 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| デッキ 60 枚ちょうど | p.308 | test_deck.py `DeckSizeTest` |
| 同じ名前 4 枚まで（基本エネルギーは制限なし、名前で数える） | p.308 | test_deck.py `SameNameTest` |
| たねポケモンが必須 | p.308 | test_deck.py `BasicPokemonTest` |
| 手札 7 枚 | p.308 | test_setup.py `test_opening_hand_is_seven` |
| たねポケモンがなければ切り直し、来るまでくりかえす | p.308 | test_setup.py `test_hand_keeps_basic_pokemon`、`MulliganTest` |
| 切り直し 1 回ごとに相手が最大 2 枚引ける（サイドの後、0〜2 枚を選べる） | p.308 | test_setup.py `test_opponent_may_draw_up_to_two_per_mulligan_after_prizes` |
| 両方が同時に切り直したら、どちらも引かない（回数が同じ場合） | p.308 | test_setup.py `test_no_draw_when_both_players_had_no_basic` |
| 対戦準備: バトル場 1 匹、ベンチ 5 匹まで（出さなくてもよい） | p.308 | test_setup.py `PlacementTest` |
| サイド 6 枚（山札の上から、両方がポケモンを出した後） | p.308 | test_setup.py `test_six_prizes_from_top_of_deck_after_both_placed` |
| ジャンケンで勝った人が先攻 | p.308 | test_setup.py `test_janken_winner_goes_first` |
| 番の最初に必ず 1 枚引く（先攻の最初の番も） | p.309 | test_turns.py `DrawTest` |
| ベンチに出す（5 匹まで、1 番に何匹でも） | p.309、p.313 | test_turns.py `BenchTest` |
| エネルギーは 1 番に 1 枚、自分のポケモン（バトル場・ベンチ）に | p.310 | test_turns.py `EnergyTest` |
| にげる（エネルギーをトラッシュ、1 番に何度でも、控えがいなければ不可、ダメージ・エネルギーはいっしょに移動） | pp.310〜311 | test_turns.py `RetreatTest` |
| ワザ: 必要なエネルギー（無色はどの色でも）、ついたままのエネルギー、使ったら番が終わる | p.309、p.320 | test_turns.py `AttackTest` |
| 先攻の最初の番もワザを使える | 本文に制限の規定がない | test_turns.py `test_first_player_may_attack_on_first_turn` |
| 相手の番には操作できない | p.309 | test_turns.py `TurnOwnershipTest` |
| ダメージ計算（基本 → 弱点 ×2 → 抵抗力 −30、0 以下は 0） | p.315、p.319、p.321 | test_combat.py `DamageTest` |
| ダメージの蓄積 | p.319 | test_combat.py `test_damage_accumulates` |
| きぜつ（HP 以上、ダメージを受けたとき）、ポケモンとエネルギーをトラッシュ | p.319、p.323 | test_combat.py `KnockOutTest` |
| サイドを 1 枚選んで取る | p.312、p.323 | test_combat.py `test_attacker_takes_one_prize` |
| ベンチからバトル場に出す | p.313、p.323 | test_combat.py `test_defender_promotes_from_bench_then_turn_passes` |
| サイドを取り終えて勝ち | p.311、p.323 | test_combat.py `test_taking_last_prize_wins`、test_integration.py |
| バトル場に出せるポケモンがいなくて負け | p.311、p.313 | test_combat.py `test_no_pokemon_to_promote_loses`、test_integration.py |
| 番の最初に山札がなくて負け（最後の 1 枚を引いた段階では負けではない） | p.309、p.311、p.312 | test_combat.py、test_integration.py `test_game_lost_by_deck_out` |
| 勝敗の表（同時に満たした条件の数で決める） | p.311 | test_judge.py（表の 9 行）、test_simultaneous_ko.py `WinTableTest`（v0.2f: 9 行すべてを対戦の中の同時のきぜつで） |
| 両方の対戦ポケモンが同時にきぜつしたら、番でないプレイヤーが先に出す（v0.2f から対戦の中で起こる） | pp.323〜324 | test_combat.py `SimultaneousKnockOutOrderTest`、test_simultaneous_ko.py `BothKnockedOutTest`・`PromotionOrderOnOpponentTurnTest`、test_pikachu_games.py |
| サドン・デスになったことの判定（v0.2f から対戦の中で起こる。延長戦は未実装） | p.311、p.324 | test_judge.py、test_simultaneous_ko.py `WinTableTest`、test_pikachu_games.py `GoldenSuddenDeathGameTest` |
| 不正な操作で状態が変わらない | — | test_turns.py `IllegalCommandsDoNotChangeStateTest`、test_setup.py |
| 同じデッキ・seed・操作列なら同じ結果、状態が共有されない | — | test_reproducibility.py |
| 未対応のカード・ワザ・操作を黙って処理しない | — | test_cards.py `ClassificationTest`、test_deck.py `SupportedCardsTest`、test_combat.py `UnsupportedAttackTest`、test_turns.py `UnsupportedActionsTest` |
| 60 枚のデッキで対戦開始から勝敗が決まるまで | — | test_integration.py `FullGameTest` |
| カードの保存則と場の形（すべての状態遷移の後に `apply_command` が検査する） | — | test_state_integrity.py `InvariantDetectionTest`・`ApplyCommandIntegrityTest`、ほかのすべてのテスト |
| 段階ごとに受け付けるコマンド以外は通らない | — | test_state_integrity.py `PhaseCommandMatrixTest` |
| 相手のカード・ポケモンを自分のものとして指定できない | — | test_state_integrity.py `OpponentCardsTest` |
| でたらめなコマンドで状態が壊れない | — | test_state_integrity.py `RandomCommandPropertyTest` |
| 乱数の固定値（Python 3.11・3.12・3.13 で同じ） | — | test_reproducibility.py `GoldenValueTest`・`GlobalRandomTest` |
| HALTED は終端で、状態は壊れていない | p.308 | test_setup.py `test_halted_state_is_consistent_and_terminal` |

## 実装済み・テスト限定

| 項目 | 根拠 | 状況 |
|---|---|---|
| ポケモンチェック | p.323 | 番と番のあいだに呼ぶが、v0.1 では処理することがない（ログに残すだけ） |
| ワザのダメージ計算の 2・6・8 段階 | p.321 | 段階の位置だけ。対応カードにそれらの効果がない（5 段階はプラスパワー v0.2c、7 段階はディフェンダー v0.2e） |

## 未実装

ルールにはあるが、まだないものです。対応するカードはデッキに入れられず（UNSUPPORTED_CARD）、対応する操作は `UnsupportedError` になります。

- 進化・退化（進化カード、`EvolvePokemon`）、最初の番の進化の制限
- 特殊状態（どく・ねむり・マヒ・こんらん）と、それによるにげる・ワザの制限、ポケモンチェックの処理
- ポケモンパワー（特殊能力、`UsePokemonPower`）
- トレーナーカード（v0.2b・v0.2c・v0.2e で対応した 5 枚のほか）、スタジアム、ポケモンのどうぐなど（ダメージ計算の 5 段階のプラスパワーは v0.2c、7 段階のディフェンダーは v0.2e で対応。2・6・8 段階の効果を持つカードはない）
- ベイビィポケモン
- 特殊エネルギー（悪・鋼、無色2個エネルギーなど）
- 効果のあるワザ（説明文のあるワザ、「+」「−」「×」のダメージ、コインを投げるワザ、ベンチへのダメージ、エネルギーをトラッシュするワザ）。v0.2d で対応したのはドードーの「みだれづき」（コイン 2 枚の「おもて」の数×10）、v0.2f で対応したのはピカチュウの「でんげき」（「うら」なら自分にも 10）だけ。ほかの自分へのダメージのワザ（エレブー「かみなりパンチ」、サンダー「かみなり」など）は未照合・未登録
- ワザによる持続する効果（すなかけ・まるまるなど）、マーカーとカウンター、変身、ポケモンいれかえ以外の入れ替えの効果、バトル場をはなれられないポケモン
- 同じタイミングで起こったことの順番を番のプレイヤーが決める処理（p.325）。同時のきぜつで両方がサイドを取る順番は、選ばせずに番のプレイヤーから取る（どちらの順でも結果が同じため。[simultaneous-ko-v0.2f.md 5 章](simultaneous-ko-v0.2f.md)）
- 同じ段階に複数のダメージ変更効果があるときに、プレイヤーが計算の順番を選ぶ処理（原文で決まっている: 2・5・6 段階はワザを使うプレイヤー、7・8 段階はワザを受けるプレイヤー。p.321〜322）
- サドン・デスの延長戦（サイド 1 枚でやり直す）
- 旧裏の複数の時期のルールの切り替え（`RuleSet` は 2000.02.14版だけ）
- 公式大会のレギュレーション（サイド 4 枚など）
- 隠れた情報の管理（プレイヤーごとに見える情報を絞る。ログも内部の完全な記録で、見せる形はない）、画面、AI、通信

## 原典未確認

| 事項 | 状況 |
|---|---|
| 照合はスキャンによる | 公式ルールとカードのページは Internet Archive のスキャン [J38] を画像で読んだ。印刷物の実物は確かめていない |
| 先攻の最初の番にワザを使えること | 本文（pp.306〜325）を画像で通読した範囲では制限の規定がない（最初の番の規定は進化だけ、p.310）。規定がないことの確認なので、読み落としの可能性は残る。kyuura は当時の資料から「制限しない」と判断している（first_turn_actions） |
| ポニータ（PMCG1-016）のワザ名 | kyuura は「けりとばす」、『オフィシャルブック2000』p.75 は「けとばす」。どちらが第1弾の印刷どおりかは未確認（[カードデータの由来](data-provenance.md)） |
| 参照カード（PMCG1-011・075） | 対戦には使わないので、『オフィシャルブック2000』と照合していない（PMCG1-014 ヒトカゲは、v0.2a で「ひっかく」を登録するために p.63 と照合した。きずぐすりは v0.2b、ドードー（PMCG1-061）は v0.2d で対戦用に移し、p.254・p.231 と照合した） |
| トレーナー 3 枚の図版の版 | p.254 のきずぐすり・ポケモンいれかえの図版には番号（⑦・⑲）があり、第1弾の版ではない可能性が高い。どの版の文面かは確かめていない。処理は最新の説明にしたがうので影響しない |
| 先攻の最初の番にトレーナーを使えること | ワザと同じく、本文に制限の規定がないことの確認（読み落としの可能性は残る）。kyuura first_turn_actions |
| 基本エネルギーの名前 | p.318 は基本エネルギーカードに名前が書かれていないとする。名前（「炎エネルギー」など）は kyuura の値をそのまま使っている（同じ名前の枚数制限の対象外なので処理には影響しない） |
| 『オフィシャルブック2000』の図版が第1弾の初版と同じ印刷か | 確かめていない |
| ネオのスターターパックの「遊びかた説明書」 | 公式ルール 2000.02.14版はこの説明書を「さらにくわしくした内容」とする（p.307）。説明書の本文は読めていない（kyuura の open_questions） |

## 裁定が未解決

原典を読んでも決められなかったものです。同時のきぜつの順番と、同じ段階のダメージ変更効果の順番は、原文で決まることを確かめました（[ルールの仕様 6章](rules-2000-02-14.md#6-曖昧になりうる処理の確認結果)）。

| 事項 | v0.1 の扱い |
|---|---|
| 両方が同時に切り直したあと、片方だけがさらに切り直したときの補償（切り直しの回数が違う場合） | 対戦を止める（`Phase.HALTED`、`UNRESOLVED_MULLIGAN_COMPENSATION`）。test_setup.py `test_unequal_mulligans_after_both_mulliganed_is_halted` |
| サドン・デスの延長戦の手順の細部（ジャンケン・切り直しのやり直し、ほかの勝利条件の扱い） | 延長戦を実装していないので決めていない（`Phase.SUDDEN_DEATH` で止める） |
| きずぐすり: 自分の場にダメージカウンターののったポケモンがいないときに使えるか（v0.2b） | `PlayTrainer` を `UnsupportedError`（`UNRESOLVED_POTION_WITHOUT_DAMAGE`）で拒否。カードは手札に残る。test_trainers.py `test_no_damaged_pokemon_is_unresolved` |
| きずぐすり: ダメージカウンターののっていないポケモンを選べるか（v0.2b） | 選ぶと `UnsupportedError`（`UNRESOLVED_POTION_UNDAMAGED_TARGET`）。決定は残る。test_trainers.py `test_undamaged_target_is_unresolved` |
| ポケモンいれかえ: 控えポケモンがいないときに使えるか（v0.2b） | `PlayTrainer` を `UnsupportedError`（`UNRESOLVED_SWITCH_WITHOUT_BENCH`）で拒否。test_trainers.py `test_no_bench_is_unresolved` |
| ワザで自分に与えるダメージに弱点・抵抗力を計算するか（ワザを使うポケモンのタイプが自分の弱点・抵抗力のタイプのとき）（v0.2f） | `UseAttack` を `UnsupportedError`（`UNRESOLVED_SELF_DAMAGE_WEAKNESS_RESISTANCE`）で拒否（コインの前。状態も乱数も変わらない）。対応カード（ピカチュウ）では起こらない。test_self_damage.py `UnresolvedSelfWeaknessTest` |

根拠と検討は [trainers-v0.2b.md](trainers-v0.2b.md)、[self-damage-v0.2f.md](self-damage-v0.2f.md)。

## v0.2a で加えた構造

ルール・カードの対応範囲は変わっていません。ここにあるのは、将来の機能のための構造です。

### 実装済み・テスト済み

| 項目 | テスト |
|---|---|
| v0.1 と同じ対戦の結果（v0.1 で記録した 15 の場面を再生し、コマンドの受け付け・拒否、最後の状態、イベントログの内容と順序が完全に同じ） | test_compat_v0_1.py |
| 効果の登録表: 対戦用のワザ 13 と、ヒトカゲの「ひっかく」を、効果のないワザ（`DamageOnly`）として明示的に登録 | test_effects.py `DefaultRegistryTest` |
| 登録のないワザは、説明文がなくても使えない（デッキにも入れられない） | test_effects.py `UnregisteredTest` |
| 説明文があっても、実装が登録されていれば使える（登録した実装が処理する） | test_effects.py `RegisteredWithTextTest`（テスト専用の実装） |
| 効果のあるワザを、効果のない実装に登録しても使えない。登録したワザ名がデータと違えば使えない | test_effects.py `RegisteredWithTextTest` |
| 同じ名前のワザでも、カードが違えば別の登録（ワザ名は識別子ではない） | test_effects.py `SameNameDifferentCardTest` |
| 登録したカードには『オフィシャルブック2000』との照合の記録がある | test_effects.py `test_every_registration_is_backed_by_a_verification_record` |
| 保留中の決定: サイドを取る・バトル場に出すを共通の決定で処理。`TakePrize`・`PromoteActive` は互換の形として残し、`ResolveDecision` と同じ結果 | test_decisions.py `EngineDecisionsTest` |
| 決定の検査: 決定するプレイヤー、決定の番号、選べないもの、選ぶ数、重複、待っている間の無関係な操作。拒否しても状態は変わらない | test_decisions.py `InvalidDecisionTest`・`RandomAnswersTest` |
| 複数段階の決定と、選んだあとの再開。決定の途中の状態の複製・pickle | test_decisions.py `MultiStepDecisionTest`（テスト専用の 2 段階の効果） |
| 場のポケモンの番号: 場に出たときに付く、重ならない、にげる・交代で変わらない、場を離れると無効、もう一度場に出ても使い回さない、複製・pickle で変わらない | test_pokemon_id.py |
| 乱数の状態の複製・保存・復元（JSON）と、指紋の区別。対戦準備のあとに乱数を使わないこと | test_rng_and_serialize.py |
| 状態の辞書の形式 2（形式 1 に項目を加えただけ） | test_rng_and_serialize.py `SerializeFormatTest` |
| 不変条件: 場のポケモンの番号、段階、決定と段階・場の形の整合性（毎回の `apply_command` で検査） | test_pokemon_id.py `InvariantTest`、test_decisions.py `DecisionInvariantTest`、ほかのすべてのテスト |
| 段階×コマンド（`ResolveDecision` と `Phase.DECISION` を加えた） | test_state_integrity.py `PhaseCommandMatrixTest` |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| `Phase.DECISION`（ワザの効果の途中の決定） | 製品の登録表に、決定を出すワザの実装はまだない。テスト専用の効果でだけ起こる（トレーナーの決定は v0.2b で製品のカードでも起こる） |
| ワザの後の、すべての場のポケモンのきぜつの判定（相手 → 自分） | v0.1 のカードできぜつするのは相手のバトル場のポケモンだけ。ほかのポケモンのきぜつは、テスト専用の効果でだけ起こる（v0.2f から、でんげきで自分のバトル場のポケモンもきぜつする。ベンチのきぜつは今もテスト専用） |
| 両方のプレイヤーが同時にサイドを取る場合の順番（番のプレイヤーが先） | v0.1 のカードでは起こらない。原文では番のプレイヤーが順番を決める（p.325）が、その選択は未実装（v0.2f: でんげきで起こる。選択を出さない理由を確かめた。[v0.2f の章](#v02f-で加えたもの自分へのダメージと同時のきぜつ)） |

### 未実装

- 特殊エネルギー・ポケモンパワーの実装を登録する欄（トレーナーの欄は v0.2b で加えた）
- `EvolvePokemon`・`UsePokemonPower` の処理（受け取ると `UnsupportedError`。`PlayTrainer` は v0.2b で対応）
- コインを投げる関数（乱数の仕組みはある）
- 進化に必要な、カードの重なり（`PokemonInPlay` はカード 1 枚）
- 場のポケモンの番号で指すコマンドの項目（`ResolveDecision` 以外）、ログの `pokemon_id`
- 見る人ごとの状態の形（非公開の情報）、合法な操作の一覧、状態を辞書からもどす処理（[アーキテクチャ 6 章・8 章](architecture-v0.2a.md)）
- 入れ子の決定（決定の続きを積む仕組み）

## v0.2b で加えたもの（トレーナー）

対応したトレーナーは、マサキ（PMCG1-074）・きずぐすり（PMCG1-071）・ポケモンいれかえ（PMCG1-073）の 3 枚です。カードごとの原典照合・裁定の分類・コード・テストの対応は [trainers-v0.2b.md](trainers-v0.2b.md)、設計は [architecture-v0.2b.md](architecture-v0.2b.md) にあります。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| トレーナーの登録表（カード id で登録、名前・文面の照合、最新の説明の記録） | p.6、p.254 | test_trainers.py `TrainerRegistryTest` |
| 登録のないトレーナーは使えない（デッキにも入れられない。効果がないものとして処理しない） | — | test_trainers.py `test_unregistered_trainer`・`TrainerRegistryTest`、test_cards.py、test_deck.py |
| `PlayTrainer`: 自分の番・手札にある・トレーナーである・登録がある・MAIN、の検査。拒否しても状態は変わらない | p.309、p.310 | test_trainers.py `PlayTrainerTest` |
| 使う順番（見せる・名前を伝える・説明にしたがう）、使ったらトラッシュ、1 番に何枚でも、使っている最中はほかの操作ができない | p.310 | test_trainers.py `PlayTrainerTest`・`TrainerDecisionTest`、test_trainer_games.py |
| マサキ: 自分の山札の上から 2 枚。足りなければ引けるだけ（1 枚・0 枚）、負けにならない。山札切れの負けは番の最初だけ | p.254、p.309、p.311、p.312 | test_trainers.py `BillTest` |
| きずぐすり: 自分の場（バトル場・ベンチ）の 1 匹、ダメージカウンターを 2 個（1 個なら 1 個）とりのぞく。数は選べない | p.254、p.312、p.319、p.320 | test_trainers.py `PotionTest` |
| ポケモンいれかえ: 自分のベンチの 1 匹とバトル場を入れ替える。にげるエネルギーを払わない。ついているカード・ダメージ・場のポケモンの番号はいっしょに移る。にげるの前後に使える | p.254、p.311、p.325 | test_trainers.py `SwitchTest` |
| 対象の選択は保留中の決定（`ResolveDecision`、場のポケモンの番号）。他人の決定・古い決定の番号・二重送信・不正な対象を拒否。複製・deepcopy・pickle・乱数の JSON の復元のあとも再開できる | — | test_trainers.py `TrainerDecisionTest` |
| 使用中のトレーナーカード（`trainer_in_use`）の保存則と、決定・段階との整合性（毎回の `apply_command` で検査） | p.310 | test_trainers.py `test_broken_trainer_state_is_detected`、ほかのすべてのテスト |
| 状態の辞書の形式 3（`trainer_in_use`）。形式 1・2 は使用中のトレーナーがあると書き出さない | — | test_trainers.py `test_card_is_in_use_during_the_decision_then_discarded` |
| トレーナーを入れた 60 枚のデッキで、正式な対戦開始から勝敗まで。3 枚とも使って効果を解決し、番を続ける。同じ入力なら同じ結果 | — | test_trainer_games.py `FullGameWithTrainersTest` |
| 先攻の最初の番にトレーナーを使える | 規定がない（p.309・p.310） | test_trainer_games.py `FirstTurnTrainerTest` |
| でたらめなコマンド（トレーナー・決定を含む）で状態が壊れない | — | test_trainer_games.py `RandomCommandsWithTrainersTest` |
| v0.1 の対戦結果（参照データの最後の状態・ログ）と乱数の固定値が変わらない | — | test_compat_v0_1.py、test_reproducibility.py |

### 部分対応

| カード | 対応 | 止める場合（原典で決められない。`UnsupportedError`） |
|---|---|---|
| マサキ | 原典で決まる場合はすべて | なし |
| きずぐすり | ダメージのあるポケモンを選ぶ場合 | 自分の場にダメージのあるポケモンがいない（`UNRESOLVED_POTION_WITHOUT_DAMAGE`）、ダメージのないポケモンを選ぶ（`UNRESOLVED_POTION_UNDAMAGED_TARGET`） |
| ポケモンいれかえ | 控えポケモンがいる場合 | 控えポケモンがいない（`UNRESOLVED_SWITCH_WITHOUT_BENCH`） |

### 未実装

- ほかのトレーナー（使うための条件があるもの、つけて使うもの（v0.2c でプラスパワーを対応）、スタジアム、きぜつを起こすものなど）
- 同じタイミングのことがらの順番を番のプレイヤーが選ぶ処理（p.325）。両方のプレイヤーがサイドを取る順番は、番のプレイヤーから順に固定している（実装上の仮定。今の対応カードでは起こらない。[trainers-v0.2b.md 6 章](trainers-v0.2b.md)）
- 特殊状態・持続する効果・「バトル場をはなれられない」状態と、ポケモンいれかえの関係（p.311・p.325。状態そのものが未実装）
- 見る人ごとのログ・状態（`draw` の `cards` などを伏せる。[architecture-v0.2b.md 9 章](architecture-v0.2b.md)）

### 原典未確認

- トレーナー 3 枚の図版の版（上の「原典未確認」の表）
- トラッシュする時点を「説明にしたがい終わったあと」としたこと（p.310 の「使った」からの読み。3 枚では結果に影響しない。SUPPORTED）
- ポケモンいれかえで、ついているカード・カウンターがいっしょに移ること（p.311 のにげるの手順の中の一般的な文からの読み。SUPPORTED）

## v0.2c で加えたもの（プラスパワー）

対応したトレーナーは、プラスパワー（PMCG1-081）です。原典照合・裁定の分類・コード・テストの対応は [pluspower-v0.2c.md](pluspower-v0.2c.md)、設計は [architecture-v0.2c.md](architecture-v0.2c.md) にあります。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| プラスパワーの登録（カード id、照合した名前・文面、最新の説明・出典 p.257） | p.6、p.257 | test_pluspower.py `PlusPowerRegistryTest`、test_trainers.py `TrainerRegistryTest` |
| `PlayTrainer` で使い、自分の対戦ポケモンにつく（使いすてではない）。不正な操作は状態を変えない | p.257、p.310、p.313 | test_pluspower.py `PlayPlusPowerTest` |
| ダメージ計算の 5 段階で +10（弱点・抵抗力のあと。途中の 0・マイナスはそのまま続ける。2 段階で 0 以下なら加わらない） | p.321 | test_pluspower.py `DamageStepTest`・`PlusPowerAttackTest` |
| 複数枚は 5 段階でそれぞれ +10 | p.310、p.321（SUPPORTED） | test_pluspower.py `test_several_pluspowers_add_up_at_step_5`・`test_resistance_with_pluspower_in_a_game` |
| 使った番の終わりにトラッシュ（ワザのあと・ワザなし・にげたあと・ポケモンいれかえのあと・きぜつさせたあと）。1 回だけ | p.257、p.309、p.323 | test_pluspower.py `TurnEndTest` |
| にげる・ポケモンいれかえで、ついているカードはポケモンといっしょに移る。同じ番にバトル場にもどれば効果がある | p.311、p.313、p.321（SUPPORTED） | test_pluspower.py `TurnEndTest`・`CombinationTest` |
| 勝敗が決まったら、番の終わりは来ない（ついたまま。勝敗のあとに効果の処理をしない） | p.311、p.323（SUPPORTED） | test_pluspower.py `test_last_prize_wins_and_the_game_ends_without_a_turn_end` |
| ついているポケモンがきぜつしたら、いっしょにトラッシュ | p.323 | test_pluspower.py `KnockOutWithAttachedTrainerTest`（テスト専用の効果） |
| ついているトレーナーの保存則・有効期限・登録の不変条件 | p.313 | test_pluspower.py `PersistenceTest` |
| 状態の辞書の形式 4（ついているトレーナー）。形式 1〜3 は拒否 | — | test_pluspower.py `PersistenceTest` |
| マサキ・きずぐすり・ポケモンいれかえとの組み合わせ。v0.2b の未解決の場面は変わらない | — | test_pluspower.py `CombinationTest` |
| プラスパワーを入れた 60 枚のデッキで、正式な対戦開始から勝敗まで。同じ入力なら同じ結果。乱数を使わない | — | test_pluspower_games.py |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| ついているトレーナーがきぜつでトラッシュされる処理 | プラスパワーは使った番の終わりにトラッシュするので、ついたままきぜつすることは今の対応カードではない。テスト専用の効果（次の番までつく）で確かめた |
| ダメージ計算の 2・6・7・8 段階の変更効果 | 段階の位置と、7 段階に受けるポケモンについているカードの効果を集める処理だけ。対応カードがない |

### 未実装

- 自分自身・控えポケモンへのダメージ（そのワザがない。プラスパワーは控えへのダメージを変えず、自分へのダメージには加わる。p.257）。自分へのダメージは v0.2f で対応した
- 加算でないダメージ変更効果と、同じ段階の順番を選ぶ決定（2・5・6 段階はワザを使うプレイヤー、7・8 段階は受けるプレイヤー。p.321）
- ワザによる持続する効果（ベンチに戻る・進化・場を離れると消える。pp.322〜323）
- ディフェンダー・特殊エネルギー・スタジアム・ポケモンのどうぐ

### 原典未確認・未解決

- UNRESOLVED の事項はありません（[pluspower-v0.2c.md 5 章](pluspower-v0.2c.md)）。
- p.257 の解説の「ワザのダメージが与えられなかったら、効果はなくなります」は、p.321 の手順（途中の 0・マイナスを認める）と矛盾しない読み方をした（[pluspower-v0.2c.md 3 章の注記](pluspower-v0.2c.md)）。

## v0.2d で加えたもの（コイントスとみだれづき）

対応したのは、コイントス（p.319）と、ドードー（PMCG1-061）のワザ「みだれづき」です。原典照合・裁定の分類・コード・テストの対応は [coin-rules-v0.2d.md](coin-rules-v0.2d.md)（コイントス）と [coin-attacks-v0.2d.md](coin-attacks-v0.2d.md)（みだれづき）、設計は [architecture-v0.2d.md](architecture-v0.2d.md) にあります。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| コイントス: 「おもて」か「うら」。対戦の乱数だけで決まり（1 枚 1 回 `getrandbits(1)`）、プレイヤーは選べない | p.319 | test_coins.py `CoinSideTest`・`FlipCountTest`・`test_rng_for_coins_is_test_only` |
| 2 枚以上は 1 枚ずつ、投げた順。余分に乱数を使わない | p.231、p.319（SUPPORTED） | test_coins.py `FlipCountTest`・`test_one_bit_per_coin_and_1_is_heads` |
| 投げる枚数・プレイヤーの誤り（効果の実装の誤り）は、乱数を使う前に `ValueError` | — | test_coins.py `test_invalid_count_is_an_implementation_error_and_uses_no_randomness` |
| 1 枚ごとのログ `coin_flip`（プレイヤー・効果・カードの uid・場のポケモンの番号・何枚目・結果） | — | test_coins.py `CoinLogTest`、test_coin_attacks.py `CoinLogInAttackTest` |
| コインの固定値（Python 3.11・3.12・3.13 で同じ） | — | test_coins.py `GoldenCoinTest`、test_coin_games.py `GoldenCoinGameTest` |
| 複製・`deepcopy`・`pickle`・乱数の JSON の保存と復元で、続きのコインが同じ。対戦どうしで乱数を共有しない。グローバルな乱数を使わない | — | test_coins.py `CoinRngTest`、test_coin_games.py `test_resume_from_a_copy_made_before_the_coins`・`test_save_the_rng_after_the_coins_and_continue` |
| 不正なコマンド・未対応・原典未解決・終わった対戦・止めた対戦・決定待ちでは、状態も乱数も変わらない。コインのあとで止まっても同じ | p.309 | test_coin_attacks.py `InvalidCommandsUseNoRandomnessTest`・`ErrorAfterFlippingTest`、test_coin_games.py `RandomCommandsWithCoinsTest` |
| みだれづきの登録（カード id・ワザの位置、照合した名前・説明文、最新の説明・出典 p.231）。登録の誤りを見つける | p.6、p.231 | test_coin_attacks.py `RegistrationTest` |
| みだれづき: コイン 2 枚、「おもて」の数×10 を相手の対戦ポケモンに。無色 1 | p.231、p.320 | test_coin_attacks.py `FuryAttackDamageTest` |
| 「おもて」0 枚: 2 段階のあとで計算を終え「ダメージを与えなかった」（弱点・抵抗力・プラスパワーは計算しない）。ワザの失敗ではないが、ワザは使ったことになり番は終わる | p.320、p.321、p.323 | `test_all_tails_is_no_damage_not_a_failure`、test_coin_pluspower.py `test_all_tails_with_pluspower_is_no_damage` |
| 弱点・抵抗力・プラスパワー（1 枚・複数枚）との計算の順番。ちょうど HP できぜつ・サイド・勝ち | p.257、p.321、p.323 | test_coin_attacks.py `KnockOutTest`、test_coin_pluspower.py |
| ドードーの弱点（雷）・抵抗力（闘 −30）・にげる 0 | p.231、p.315 | test_coin_attacks.py `DoduoAsDefenderTest` |
| ドードーを入れた 60 枚のデッキで、正式な対戦開始から勝敗まで（8 つの seed）。乱数を使うのはコインだけ。同じ入力なら同じ結果 | — | test_coin_games.py |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 弱点・抵抗力が無色のポケモンへのみだれづき | 今の対応カードにはいない。テスト専用のカード（ヒトデマンの記録を写して弱点・抵抗力だけを変えたもの）で計算の順番を確かめた |
| コインを投げたあとで、原典で決められない場合・エンジンの不具合で止まる処理 | みだれづきでは起こらない。テスト専用の効果で確かめた |

### 未実装

- ほかのコインのワザ（特殊状態・自分へのダメージ・「うら」で失敗・追加ダメージ・連続コイントス）と、コインを使うトレーナー（自分へのダメージのうち、でんげきは v0.2f で対応した）
- ワザの「失敗」（p.323「12 ワザの失敗」。ベイビィポケモンのルールなど）
- 特殊状態のコイン（こんらん・ねむり。p.309・p.311・p.323）
- ゲーム状態全体の JSON からの読み込み（乱数だけは保存・復元できる）

### 原典未確認・未解決

- UNRESOLVED の事項はありません（[coin-rules-v0.2d.md 2 章](coin-rules-v0.2d.md)、[coin-attacks-v0.2d.md 5 章](coin-attacks-v0.2d.md)）。
- ワザの説明のコインを誰が投げるかの明文はない。こんらん・ねむり・ベイビィの規定から、ワザを使うポケモン側として記録する（SUPPORTED。結果には影響しない）。
- コインの確からしさを数で書いた記述はない（p.319 の「ずる」の記述から、同じ確からしさとした。SUPPORTED）。
- p.231 の図版が第1弾の初版の印刷かは確かめていない（図版に ○30 がある）。ワザの説明の書き方が kyuura の写しと違う（意味は同じ）。収録（スターターパック・イントロパック）の書き方が違う（[coin-attacks-v0.2d.md 6 章](coin-attacks-v0.2d.md)）。

## v0.2e で加えたもの（ディフェンダー）

対応したトレーナーは、ディフェンダー（PMCG1-079）です。原典照合・裁定の分類・コード・テストの対応は [defender-v0.2e.md](defender-v0.2e.md)、設計は [architecture-v0.2e.md](architecture-v0.2e.md) にあります。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| ディフェンダーの登録（カード id、照合した名前・文面、最新の説明・出典 p.257） | p.6、p.257 | test_defender.py `DefenderRegistryTest`、test_trainers.py `TrainerRegistryTest` |
| `PlayTrainer` で使う。不正な操作（番・プレイヤー・カード・段階・決定待ち・終わった対戦・止めた対戦）は状態も乱数も変えない | p.310 | test_defender.py `PlayDefenderTest` |
| 自分の場（バトル場・ベンチ）のポケモンを選ぶ決定。相手のポケモン・存在しない番号・古い決定・別のプレイヤー・二度目の答えは拒否。複製した状態でも同じ結果 | p.257、p.313 | test_defender.py `ChooseTargetTest` |
| カードは手札 → 使用中 → ついている、の 1 か所だけにある | p.310、p.313 | `test_card_is_in_exactly_one_place` |
| ダメージ計算の 7 段階で −20（弱点・抵抗力・プラスパワーのあと。途中のマイナスはそのまま。最後に 0 以下なら 0）。複数枚はそれぞれ −20。与えるダメージは変えない | p.257、p.321 | test_defender.py `DefenderDamageTest` |
| みだれづき（コイン）と組み合わせる。「おもて」0 枚は 2 段階で終えるので 7 段階に進まない。乱数はコインのぶんだけ | p.231、p.321 | test_defender.py `CoinAttackAgainstDefenderTest` |
| 次の相手の番の終わりにトラッシュ（使った番の終わりではない。ワザを使わずに番を終えても同じ。ポケモンチェックの前）。そのあとは効果がない | p.257、p.309、p.323 | test_defender.py `DefenderExpiryTest` |
| プラスパワーとディフェンダーが同じポケモンについても、それぞれの期限でトラッシュする。両方のプレイヤーのカードが同じ番の終わりにトラッシュされる | p.257 | `test_pluspower_and_defender_on_the_same_pokemon_expire_separately`・`test_both_players_cards_expire_at_the_end_of_the_same_turn` |
| ベンチのポケモンにつける。にげる・ポケモンいれかえでいっしょに移り、同じ番にバトル場にもどれば効果がある | p.311、p.313 | `test_on_the_bench`・`test_retreat_moves_the_card`・`test_switch_moves_the_card` |
| きぜつしたらいっしょにトラッシュ（1 回だけ。期限の処理と重ならない）。最後のサイドで勝ち | p.323 | test_defender.py `KnockOutWithDefendersTest`・`test_last_prize_wins_and_the_card_goes_with_the_pokemon` |
| 勝敗が決まったら（相手の番の最初の山札切れ・最後のサイド）、番の終わりは来ないのでついたまま | p.309、p.311、p.323 | `test_game_ends_before_the_opponent_turn_ends`・`test_game_won_with_the_card_on_the_bench` |
| 状態の辞書の形式 4（発生源・持ち主・対象・期限）。形式 1〜3 は拒否。複製・`deepcopy`・`pickle` | — | test_defender.py `DefenderStateTest` |
| 有効期限の上限・使った番の持ち主・番の順番の不変条件 | p.309 | `test_broken_expiry_is_detected`・`test_turn_order_is_checked` |
| ディフェンダーを入れた 60 枚のデッキで、正式な対戦開始から勝敗まで（8 つの seed）。相手の番のダメージが減ったことをログで確かめる。プラスパワー・みだれづきとの組み合わせ。同じ入力なら同じ結果。乱数はコインだけ | — | test_defender_games.py |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| ディフェンダーをつけたポケモンが、対戦の中できぜつする場面 | 統合テストの 8 局では起こらなかった（リポジトリの外で行った負荷テストの 120 局では 6 回起きた）。盤面を直接作るテストで確かめた |
| 無色が抵抗力のポケモンへのみだれづき + ディフェンダー | テスト専用のカード（v0.2d と同じ）で計算の順番を確かめた |

### 未実装

- 自分のワザで自分が受けるダメージへの −20（p.257 の解説。そのワザがない）。v0.2f で対応した（でんげき）
- ベンチのポケモンが受けるワザのダメージへの −20（そのワザがない。ベンチへのダメージの計算を原典で確かめる必要がある）
- 7 段階の加算でない効果（鋼エネルギーなど）と、ワザを受けるプレイヤーが順番を選ぶ決定
- 第1弾の印刷の文面どおりの処理（効果の終わりとカードを捨てる時点が別）。2000.02.14版では使わない

### 原典未確認・未解決

- UNRESOLVED の事項はありません（[defender-v0.2e.md 2 章](defender-v0.2e.md)）。
- 印刷の文面と最新の説明の違いは CONFLICT として記録し、p.6 により最新の説明にしたがった。
- p.257 の図版は記号のある版で、第1弾の版ではない。kyuura にディフェンダーの文面の変更（印刷の文面と最新の説明）を分けた記録がない（[defender-v0.2e.md 6 章](defender-v0.2e.md)）。

## v0.2f で加えたもの（自分へのダメージと同時のきぜつ）

対応したカードは、ピカチュウ（PMCG1-035）の「かじる」「でんげき」です。原典照合・裁定の分類・コード・テストの対応は [self-damage-v0.2f.md](self-damage-v0.2f.md)（自分へのダメージ）、[simultaneous-ko-v0.2f.md](simultaneous-ko-v0.2f.md)（同時のきぜつ）、[pikachu-v0.2f.md](pikachu-v0.2f.md)（カード）、設計は [architecture-v0.2f.md](architecture-v0.2f.md) にあります。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| ピカチュウの登録（かじる: 説明文なし。でんげき: 照合した説明文・最新の説明・出典 p.125）。間違った登録の検出 | p.6、p.125 | test_self_damage.py `PikachuRegistrationTest`、test_effects.py |
| でんげきの要素の順番（相手に 30 → コイン 1 枚 → 「うら」なら自分に 10）。「おもて」なら自分へのダメージはない。エネルギーが足りなければ使えず、コインも投げない | p.125、p.309、p.320 | test_self_damage.py `ThunderJoltTest` |
| 自分へのダメージを p.321 の順番で計算する。プラスパワー（5 段階）・ディフェンダー（7 段階）を一度ずつ（1・2 枚とその組み合わせ）。相手のディフェンダーは自分へのダメージを変えない | p.257、p.321 | test_self_damage.py `SelfDamageModifierTest` |
| 自分のきぜつ（ちょうど HP、1 つ足りない、ディフェンダーで防ぐ、プラスパワーできぜつ）。相手がサイドを取る。ベンチがなければ負け。相手の最後のサイドなら相手の勝ち | p.312、p.323 | test_self_damage.py `SelfKnockOutTest`・`test_defender_prevents_self_knock_out`・`test_pluspower_causes_self_knock_out` |
| 同時のきぜつ: ワザの要素をすべて処理してから判定。両方をトラッシュ（ついているカードもそれぞれ）。ログ `simultaneous`。サイドは番のプレイヤー → 相手、バトル場は番でないプレイヤー → 番のプレイヤー（番がどちらでも） | p.309、p.323、p.324 | test_simultaneous_ko.py `BothKnockedOutTest`・`PromotionOrderOnOpponentTurnTest` |
| サイドを取る順番の正規化（逆の順でも、選べるもの・状態・結果が同じ） | p.312、p.325 | test_simultaneous_ko.py `PrizeOrderTest` |
| サイド・バトル場の決定のあいだのほかの操作の拒否。そのあいだ乱数を使わない | p.309 | test_simultaneous_ko.py `PrizeAndPromotionDecisionTest` |
| p.311 の表の 9 行すべてと本文の場合（サドン・デスを含む）を、同時のきぜつで起こす | p.311、p.324 | test_simultaneous_ko.py `WinTableTest` |
| 原典で決められない場合（自分のタイプが自分の弱点・抵抗力のタイプ）は、コインの前に止める（「おもて」「うら」どちらの乱数でも）。コインのあとで止まっても渡した状態・乱数は変わらない | p.321、p.322 | test_self_damage.py `UnresolvedSelfWeaknessTest` |
| 不正な操作（番・プレイヤー・ワザの位置・未登録・決定待ち・終わった対戦・止めた対戦）は状態も乱数も変えない | — | test_self_damage.py `InvalidCommandsTest` |
| ピカチュウを入れた 60 枚のデッキで、正式な対戦開始から勝敗まで（8 つの seed）。自分のきぜつ・同時のきぜつ・両方のバトル場への交代・サドン・デスが起こる。ログの要素の順番・変更効果・サイド・交代を確かめ、最後の状態から表の判定をやり直す。同じ入力なら同じ結果。乱数はコインだけ | — | test_pikachu_games.py `FullGameWithPikachuTest` |
| サドン・デスになる対戦の固定値（seed 9。Python 3.11・3.12・3.13） | p.311 | test_pikachu_games.py `GoldenSuddenDeathGameTest` |
| 正しい操作とでたらめな操作を混ぜても状態が壊れない（12 の seed） | — | test_pikachu_games.py `RandomCommandsWithPikachuTest` |

### 部分対応

| 項目 | 状況 |
|---|---|
| ワザで自分に与えるダメージの弱点・抵抗力 | 関係しない場合（自分のタイプが自分の弱点・抵抗力のタイプと違う）は計算する（どちらに決めても同じ）。関係する場合は `UNRESOLVED_SELF_DAMAGE_WEAKNESS_RESISTANCE` で止める。対応カード（ピカチュウ）では止まる場面はない |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 自分のタイプが自分の弱点・抵抗力のタイプのポケモンで止める処理 | 対応カードにはない。テスト専用のカード（ピカチュウの写しのタイプ・弱点・抵抗力を変えたもの）で確かめた |
| ベンチのポケモンのきぜつ（同時のきぜつを含む） | 判定は場のすべてのポケモンについて行うが、ベンチにダメージを与えるワザがない |

### 未実装

- 控えポケモンへのダメージ（p.320 のダメージの (2)・(4)）。受けるポケモンを選ぶ手順、控えへのダメージの計算（弱点・抵抗力・プラスパワーを計算しない。p.257）の照合が要る
- ほかの自分へのダメージのワザ（エレブー「かみなりパンチ」のダメージの目安「+」、サンダー「かみなり」など）。カードのページと照合していない
- こんらんの自分へのダメージ（特殊状態は未実装。p.322 は「弱点・抵抗力」の影響を受けると書く）
- サイドを取る順番を番のプレイヤーが選ぶ決定（p.325。結果が変わらないので出していない）
- サドン・デスの延長戦（`Phase.SUDDEN_DEATH` で止める）
- ライチュウへの進化（進化は未実装）

### 原典未確認・未解決

- UNRESOLVED: ワザの説明による自分へのダメージに弱点・抵抗力を計算するか（関係する場合だけ止める。[self-damage-v0.2f.md 2 章](self-damage-v0.2f.md)）。
- p.125 のピカチュウの図版には ○ の中の数字（13）があり、第1弾の初版の図版かはこの画像からは決められない（文面は kyuura の写しと一致）。
- kyuura に、2000年のルールでのワザによる自分へのダメージの記録がない。ピカチュウの収録商品の書き方が違う（kyuura「スターターパック」、p.125「イントロパック」）（[ルールの仕様 6章の「kyuura の記録との違い」](rules-2000-02-14.md#kyuura-の記録との違い報告事項)）。
