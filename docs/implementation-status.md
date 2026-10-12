# 実装状況（v0.1・v0.2a）

基準: 公式ルール 2000.02.14版（『ポケモンカードオフィシャルブック2000』pp.306〜326 [P43]）、kyuura `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`。項目ごとの根拠は [ルールの仕様](rules-2000-02-14.md) にあります。v0.2 の前のレビューの結果は [review-v0.1.md](review-v0.1.md)、公開 API の評価は [api-review.md](api-review.md) にあります。

v0.2a は、v0.1 のルールと対戦の結果を変えずに、カード効果を実装するための構造を整えた版です（[アーキテクチャ](architecture-v0.2a.md)）。対応しているルールとカードは v0.1 と同じです。v0.2a で加えた構造の状況は [最後の章](#v02a-で加えた構造) にあります。

状態の区分:

- **実装済み・テスト済み**: コードがあり、その規定を確かめる自動テストがある
- **実装済み・テスト限定**: コードはあるが、v0.1 のカードでは起こらないため、手順を直接呼ぶテストか、テストがない
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
| 勝敗の表（同時に満たした条件の数で決める） | p.311 | test_judge.py（表の 9 行） |
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
| 両方の対戦ポケモンが同時にきぜつしたら、番でないプレイヤーが先に出す | pp.323〜324 | v0.1 のカードでは起こらない。手順（`engine._after_knockouts`）を直接呼ぶテストだけ（test_combat.py `SimultaneousKnockOutOrderTest`） |
| サドン・デスになったことの判定 | p.311、p.324 | 判定の関数は表のテストで確かめた。対戦の中では v0.1 のカードでは起こらない。サドン・デスになったら `Phase.SUDDEN_DEATH` で止まる |
| ポケモンチェック | p.323 | 番と番のあいだに呼ぶが、v0.1 では処理することがない（ログに残すだけ） |
| ワザのダメージ計算の 2・5〜8 段階 | p.321 | 段階の位置だけ。v0.1 の対応カードにそれらの効果がない |

## 未実装

ルールにはあるが、v0.1 にはないものです。対応するカードはデッキに入れられず（UNSUPPORTED_CARD）、対応する操作は `UnsupportedError` になります。

- 進化・退化（進化カード、`EvolvePokemon`）、最初の番の進化の制限
- 特殊状態（どく・ねむり・マヒ・こんらん）と、それによるにげる・ワザの制限、ポケモンチェックの処理
- ポケモンパワー（特殊能力、`UsePokemonPower`）
- トレーナーカード（`PlayTrainer`）、スタジアム、ポケモンのどうぐ、プラスパワー・ディフェンダーなどのダメージ計算の段階
- ベイビィポケモン
- 特殊エネルギー（悪・鋼、無色2個エネルギーなど）
- 効果のあるワザ（説明文のあるワザ、「+」「−」「×」のダメージ、コインを投げるワザ、自分やベンチへのダメージ、エネルギーをトラッシュするワザ）
- 持続する効果、マーカーとカウンター、変身、入れ替えの効果、バトル場をはなれられないポケモン
- 同じタイミングで起こったことの順番を番のプレイヤーが決める処理（p.325）
- 同じ段階に複数のダメージ変更効果があるときに、プレイヤーが計算の順番を選ぶ処理（原文で決まっている: 2・5・6 段階はワザを使うプレイヤー、7・8 段階はワザを受けるプレイヤー。p.321〜322）
- サドン・デスの延長戦（サイド 1 枚でやり直す）
- 旧裏の複数の時期のルールの切り替え（`RuleSet` は 2000.02.14版だけ）
- 公式大会のレギュレーション（サイド 4 枚など）
- 隠れた情報の管理（プレイヤーごとに見える情報を絞る）、画面、AI、通信

## 原典未確認

| 事項 | 状況 |
|---|---|
| 照合はスキャンによる | 公式ルールとカードのページは Internet Archive のスキャン [J38] を画像で読んだ。印刷物の実物は確かめていない |
| 先攻の最初の番にワザを使えること | 本文（pp.306〜325）を画像で通読した範囲では制限の規定がない（最初の番の規定は進化だけ、p.310）。規定がないことの確認なので、読み落としの可能性は残る。kyuura は当時の資料から「制限しない」と判断している（first_turn_actions） |
| ポニータ（PMCG1-016）のワザ名 | kyuura は「けりとばす」、『オフィシャルブック2000』p.75 は「けとばす」。どちらが第1弾の印刷どおりかは未確認（[カードデータの由来](data-provenance.md)） |
| 参照カード（PMCG1-011・014・061・071） | 対戦には使わないので、『オフィシャルブック2000』と照合していない |
| 基本エネルギーの名前 | p.318 は基本エネルギーカードに名前が書かれていないとする。名前（「炎エネルギー」など）は kyuura の値をそのまま使っている（同じ名前の枚数制限の対象外なので処理には影響しない） |
| 『オフィシャルブック2000』の図版が第1弾の初版と同じ印刷か | 確かめていない |
| ネオのスターターパックの「遊びかた説明書」 | 公式ルール 2000.02.14版はこの説明書を「さらにくわしくした内容」とする（p.307）。説明書の本文は読めていない（kyuura の open_questions） |

## 裁定が未解決

原典を読んでも決められなかったものです。同時のきぜつの順番と、同じ段階のダメージ変更効果の順番は、原文で決まることを確かめました（[ルールの仕様 6章](rules-2000-02-14.md#6-曖昧になりうる処理の確認結果)）。

| 事項 | v0.1 の扱い |
|---|---|
| 両方が同時に切り直したあと、片方だけがさらに切り直したときの補償（切り直しの回数が違う場合） | 対戦を止める（`Phase.HALTED`、`UNRESOLVED_MULLIGAN_COMPENSATION`）。test_setup.py `test_unequal_mulligans_after_both_mulliganed_is_halted` |
| サドン・デスの延長戦の手順の細部（ジャンケン・切り直しのやり直し、ほかの勝利条件の扱い） | 延長戦を実装していないので決めていない（`Phase.SUDDEN_DEATH` で止める） |

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
| `Phase.DECISION`（ワザの効果の途中の決定） | 製品の登録表に、決定を出す実装はまだない。テスト専用の効果でだけ起こる |
| ワザの後の、すべての場のポケモンのきぜつの判定（相手 → 自分） | v0.1 のカードできぜつするのは相手のバトル場のポケモンだけ。ほかのポケモンのきぜつは、テスト専用の効果でだけ起こる |
| 両方のプレイヤーが同時にサイドを取る場合の順番（番のプレイヤーが先） | v0.1 のカードでは起こらない。原文では番のプレイヤーが順番を決める（p.325）が、その選択は未実装 |

### 未実装

- トレーナー・特殊エネルギー・ポケモンパワーの実装を登録する欄（最初のトレーナーを実装するときに加える）
- `PlayTrainer`・`EvolvePokemon`・`UsePokemonPower` の処理（受け取ると `UnsupportedError`）
- コインを投げる関数（乱数の仕組みはある）
- 進化に必要な、カードの重なり（`PokemonInPlay` はカード 1 枚）
- 場のポケモンの番号で指すコマンドの項目（`ResolveDecision` 以外）、ログの `pokemon_id`
- 見る人ごとの状態の形（非公開の情報）、合法な操作の一覧、状態を辞書からもどす処理（[アーキテクチャ 6 章・8 章](architecture-v0.2a.md)）
- 入れ子の決定（決定の続きを積む仕組み）
