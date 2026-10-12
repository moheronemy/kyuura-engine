# 実装状況（v0.1）

基準: 公式ルール 2000.02.14版（『ポケモンカードオフィシャルブック2000』pp.306〜326 [P43]）、kyuura `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`。項目ごとの根拠は [ルールの仕様](rules-2000-02-14.md) にあります。

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
