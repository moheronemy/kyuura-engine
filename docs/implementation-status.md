# 実装状況（v0.1〜v0.4c）

基準: 公式ルール 2000.02.14版（『ポケモンカードオフィシャルブック2000』pp.306〜326 [P43]）、kyuura `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`。項目ごとの根拠は [ルールの仕様](rules-2000-02-14.md) にあります。v0.2 の前のレビューの結果は [review-v0.1.md](review-v0.1.md)、公開 API の評価は [api-review.md](api-review.md) にあります。

v0.2a は、v0.1 のルールと対戦の結果を変えずに、カード効果を実装するための構造を整えた版です（[アーキテクチャ](architecture-v0.2a.md)）。v0.2b は、その構造を使ってトレーナーカード 3 枚（マサキ・きずぐすり・ポケモンいれかえ）を実装した版です（[アーキテクチャ](architecture-v0.2b.md)、[原典照合](trainers-v0.2b.md)）。v0.2c は、プラスパワーと、場に残るトレーナー・有効期限・ダメージ計算の段階への効果の適用を加えた版です（[アーキテクチャ](architecture-v0.2c.md)、[原典照合](pluspower-v0.2c.md)）。v0.2d は、コイントスと、コインの結果でダメージが変わるワザ（ドードーの「みだれづき」）を加えた版です（[アーキテクチャ](architecture-v0.2d.md)、[コイントスの規定](coin-rules-v0.2d.md)、[みだれづき](coin-attacks-v0.2d.md)）。v0.2e は、ディフェンダーと、防御側のダメージ変更・相手の番にまたがる有効期限を加えた版です（[アーキテクチャ](architecture-v0.2e.md)、[原典照合](defender-v0.2e.md)）。v0.2f は、ワザで自分に与えるダメージと、同時のきぜつ（両方のプレイヤーのポケモンが 1 つのワザできぜつする）を、ピカチュウの「かじる」「でんげき」とともに加えた版です（[アーキテクチャ](architecture-v0.2f.md)、[自分へのダメージ](self-damage-v0.2f.md)、[同時のきぜつ](simultaneous-ko-v0.2f.md)、[ピカチュウ](pikachu-v0.2f.md)）。v0.3a は、特殊状態の共通基盤と「どく」、番と番のあいだのポケモンチェックを、ビードルの「どくばり」とともに加えた版です（[アーキテクチャ](architecture-v0.3a.md)、[特殊状態](special-conditions-v0.3a.md)、[ポケモンチェック](pokemon-check-v0.3a.md)、[ビードル](weedle-v0.3a.md)）。v0.3b は、ねむり・マヒと、それによるワザ・にげるの制限、ポケモンチェックの 3（ねむりのコイン）・4（マヒの回復）を、キャタピーの「いとをはく」・パラスの「ひっかく」「キノコのほうし」とともに加えた版です（[アーキテクチャ](architecture-v0.3b.md)、[ねむり・マヒ](sleep-paralysis-v0.3b.md)、[ポケモンチェック](pokemon-check-v0.3b.md)、[キャタピー・パラス](cards-v0.3b.md)）。v0.3c は、こんらんと、こんらん状態のポケモンのワザ（コイン・自分への 20 ダメージ）・にげる（コイン・エネルギー・同じ番の再宣言の制限）を、ロコンの「あやしいひかり」とともに加えた版です（[アーキテクチャ](architecture-v0.3c.md)、[こんらん](confusion-v0.3c.md)、[ワザ・ロコン](confusion-attacks-v0.3c.md)、[にげる](retreat-confusion-v0.3c.md)）。v0.3d は、カード・ルールを加えず、特殊状態 4 種類の総合検証・未解決の裁定の再調査・コインの前の検証・進化の準備の調査をした版です（[アーキテクチャ](architecture-v0.3d.md)、[総合検証](special-conditions-audit-v0.3d.md)、[未解決の裁定](unresolved-rulings-v0.3d.md)、[コインの前の検証](effect-preflight-v0.3d.md)、[進化の準備](evolution-readiness-v0.4.md)）。v0.4a は、たねポケモン → 1 進化ポケモンの進化（`EvolvePokemon`）を、パラセクト（パラスから進化）・ジュゴン（パウワウから進化）とともに加えた版です（[アーキテクチャ](architecture-v0.4a.md)、[進化のルール](evolution-rules-v0.4a.md)、[カード](evolution-cards-v0.4a.md)、[状態](evolution-state-v0.4a.md)）。v0.4b は、ワザによる持続する効果（番をまたいで残り、期限・ベンチ・進化・きぜつで消える）を、トランセル（キャタピーから進化）・コクーン（ビードルから進化）の「かたまる」とともに加えた版です（[アーキテクチャ](architecture-v0.4b.md)、[持続する効果](persistent-effects-v0.4b.md)、[かたまる](harden-v0.4b.md)、[ダメージ計算](persistent-damage-v0.4b.md)）。v0.4c は、1 進化ポケモン → 2 進化ポケモンの進化（たね・1 進化・2 進化の 3 枚で構成される 1 匹のポケモン）を、スピアー（コクーンから進化）の「ダブルニードル」「どくばり」とともに加えた版です（[アーキテクチャ](architecture-v0.4c.md)、[2 進化のルール](stage2-evolution-v0.4c.md)、[スピアー](beedrill-v0.4c.md)、[状態](stage2-state-v0.4c.md)）。それぞれの状況は [v0.2a の章](#v02a-で加えた構造)・[v0.2b の章](#v02b-で加えたものトレーナー)・[v0.2c の章](#v02c-で加えたものプラスパワー)・[v0.2d の章](#v02d-で加えたものコイントスとみだれづき)・[v0.2e の章](#v02e-で加えたものディフェンダー)・[v0.2f の章](#v02f-で加えたもの自分へのダメージと同時のきぜつ)・[v0.3a の章](#v03a-で加えたもの特殊状態どくポケモンチェック)・[v0.3b の章](#v03b-で加えたものねむりマヒポケモンチェックの-34)・[v0.3c の章](#v03c-で加えたものこんらん)・[v0.3d の章](#v03d-で確かめたこと特殊状態の総合検証未解決の裁定)・[v0.4a の章](#v04a-で加えたもの進化-たねポケモン--1-進化ポケモン)・[v0.4b の章](#v04b-で加えたものワザによる持続する効果とかたまる)・[v0.4c の章](#v04c-で加えたもの2-進化とスピアー) にあります。

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
| ポケモンチェック | p.323 | v0.1〜v0.2f では処理することがなかった（ログに残すだけ）。v0.3a でどくのダメージ・きぜつ、v0.3b でねむりのコイン（3）・マヒの回復（4）を処理する。こんらんはポケモンチェックで何もしない（v0.3c）（[v0.3a の章](#v03a-で加えたもの特殊状態どくポケモンチェック)・[v0.3b の章](#v03b-で加えたものねむりマヒポケモンチェックの-34)）。1（指示されたこと）は対応カードにない |
| ワザのダメージ計算の 2・6・8 段階 | p.321 | 段階の位置だけ。対応カードにそれらの効果がない（5 段階はプラスパワー v0.2c、7 段階はディフェンダー v0.2e） |

## 未実装

ルールにはあるが、まだないものです。対応するカードはデッキに入れられず（UNSUPPORTED_CARD）、対応する操作は `UnsupportedError` になります。

- 退化・ベイビィポケモンの進化（たねポケモン → 1 進化は v0.4a、1 進化 → 2 進化は v0.4c で対応した。2 進化のカードはスピアーだけ）。進化に関わるポケモンパワー・トレーナー
- 特殊状態のうち、ポケモンチェックの 1、特殊などく、特殊状態を回復するカード（どく・ねむり・マヒ・こんらんとこんらんのコインは v0.3a〜v0.3c で対応した）
- ポケモンパワー（特殊能力、`UsePokemonPower`）
- トレーナーカード（v0.2b・v0.2c・v0.2e で対応した 5 枚のほか）、スタジアム、ポケモンのどうぐなど（ダメージ計算の 5 段階のプラスパワーは v0.2c、7 段階のディフェンダーは v0.2e で対応。2・6・8 段階の効果を持つカードはない）
- ベイビィポケモン
- 特殊エネルギー（悪・鋼、無色2個エネルギーなど）
- 効果のあるワザ（説明文のあるワザ、「+」「−」「×」のダメージ、コインを投げるワザ、ベンチへのダメージ、エネルギーをトラッシュするワザ）。v0.2d で対応したのはドードーの「みだれづき」（コイン 2 枚の「おもて」の数×10）、v0.2f で対応したのはピカチュウの「でんげき」（「うら」なら自分にも 10）だけ。ほかの自分へのダメージのワザ（エレブー「かみなりパンチ」、サンダー「かみなり」など）は未照合・未登録
- ワザによる持続する効果のうち、「かたまる」（v0.4b）のほか（相手に与える「すなかけ」「からまるいと」、ほかの自分に与える効果、カウンター・マーカーをのせるタイプ、「効果を受けない」状態）、マーカーとカウンター、変身、ポケモンいれかえ以外の入れ替えの効果（ふきとばしなど）、バトル場をはなれられないポケモン
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
| ポケモンチェックの「どく」で、両方のプレイヤーのポケモンがきぜつする（v0.3a） | ダメージを与える前に対戦を止める（`Phase.HALTED`、`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`）。以後のコマンドは `UnsupportedError`。test_pokemon_check.py `DoubleKnockOutTest` |
| 特殊などく状態の重ね方（通常のどくのポケモンが特殊などくを受ける、特殊などく同士。v0.3a） | 特殊などくの効果は未実装（起こらない） |
| ポケモンチェックで、両方の対戦ポケモンがねむり状態のときのコインの順番（v0.3b） | コインを投げる前に対戦を止める（`Phase.HALTED`、`UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`）。対応カード（パラス）では起こらない。test_pokemon_check_v0_3b.py `BothAsleepTest` |
| マヒ状態のポケモンが再びマヒの効果を受けたときに、回復する番が最初の番とあとの番で違う場合（v0.3b） | `UnsupportedError`（`UNRESOLVED_REPARALYSIS_RECOVERY_TURN`。コインの前）。回復する番が同じなら処理する。対応カード（キャタピー）では起こらない。test_sleep_paralysis.py `test_reparalysis_with_a_different_recovery_turn_is_unresolved` |
| こんらんしたワザの 20 ダメージに、ワザを使うポケモンについているプラスパワー・ディフェンダーを計算するか（v0.3c） | ついていれば、こんらんのコインを投げる前に `UseAttack` を `UnsupportedError`（`UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS`）で拒否。自然な対戦 36 局で 2 回起こった。test_confusion_attacks.py `UnresolvedModifierTest` |
| 「にげる」に失敗したあとベンチに戻り（こんらんが消え）、同じ番にバトル場に戻ったポケモンが「にげる」を宣言できるか（v0.3c） | `Retreat` を `UnsupportedError`（`UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED`。エネルギー・コインの前）で拒否。次の番には宣言できる。test_confusion_retreat.py `test_failed_pokemon_back_in_the_battle_field_is_unresolved` |
| ワザの説明にコスト（エネルギーのトラッシュなど）があるワザで、こんらんの「うら」のときにコストを払うか（v0.3c） | 対応カードにない（決めていない。そのワザを加えるときに照合する） |
| 進化したあとの HP が、のっているダメージ以下になる場合（きぜつするか・いつ判定するか）（v0.4a） | `EvolvePokemon` を `UnsupportedError`（`UNRESOLVED_EVOLUTION_HP`）で拒否（状態を変える前）。対応カード（パラセクト・ジュゴン）は HP が増えるので起こらない。v0.4c のコクーン（HP 80）→ スピアー（HP 80）は HP が同じで、きぜつしていないコクーンでは起こらない（2 進化でも同じ止め方。HP 70 にしたテスト専用のスピアーで確かめた）。test_evolution_v0_4a.py `test_damage_at_or_above_the_new_hp_is_unresolved`・test_stage2_v0_4c.py `test_same_hp_evolution_and_the_unresolved_hp_case` |
| 「ダメージを受けない」状態（「かたまる」）のポケモンに、コインでダメージの量を決める要素だけのワザ（ドードーの「みだれづき」）を使うとき、無効になる要素のコインを投げるか（v0.4b） | ワザの宣言・こんらんのコインの前に `UseAttack` を `UnsupportedError`（`UNRESOLVED_PREVENTED_COIN_DAMAGE`）で拒否。状態も乱数も変わらない。自然な対戦 40 局で 13 回起こった。v0.4c のスピアーの「ダブルニードル」（同じ `CoinFlipDamage`）にも同じく当てはまる（v0.4c の自然な対戦 40 局で 5 回）。通常の相手には使える。test_harden_v0_4b.py `test_coin_damage_against_prevention_is_unresolved`・test_stage2_v0_4c.py `PreventedTargetTest`・test_effect_preflight_v0_3d.py `CoinIndependenceTest`（[persistent-damage-v0.4b.md](persistent-damage-v0.4b.md) 5 章） |

v0.3d で、上の表の v0.2b〜v0.3c の事項を原典で調べ直しました（[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md)）。どれも決められないので、止める処理を維持しています。v0.2f の「ワザで自分に与えるダメージに弱点・抵抗力を計算するか」は、p.90 の解説から SUPPORTED（計算する）にしたので、この表から外しました（[v0.3d の章](#v03d-で確かめたこと特殊状態の総合検証未解決の裁定)）。

根拠と検討は [trainers-v0.2b.md](trainers-v0.2b.md)、[self-damage-v0.2f.md](self-damage-v0.2f.md)、[pokemon-check-v0.3a.md](pokemon-check-v0.3a.md)、[special-conditions-v0.3a.md](special-conditions-v0.3a.md)、[sleep-paralysis-v0.3b.md](sleep-paralysis-v0.3b.md)、[confusion-v0.3c.md](confusion-v0.3c.md)、[confusion-attacks-v0.3c.md](confusion-attacks-v0.3c.md)、[retreat-confusion-v0.3c.md](retreat-confusion-v0.3c.md)、[pokemon-check-v0.3b.md](pokemon-check-v0.3b.md)。


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
- `EvolvePokemon`・`UsePokemonPower` の処理（受け取ると `UnsupportedError`。`PlayTrainer` は v0.2b、`EvolvePokemon` は v0.4a で対応）
- コインを投げる関数（乱数の仕組みはある）
- 進化に必要な、カードの重なり（`PokemonInPlay` はカード 1 枚）→ v0.4a で `evolution_stack` を加えた
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
- 持続する効果・「バトル場をはなれられない」状態と、ポケモンいれかえの関係（p.311・p.325。状態そのものが未実装）。どく（v0.3a）・ねむり・マヒ（v0.3b）は、ポケモンいれかえでベンチに戻ったら消える。ねむり・マヒのポケモン（にげるを宣言できない）もポケモンいれかえでは入れ替える（p.325。v0.3b）
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
- こんらんのコイン（p.309・p.311）。ねむりのコイン（ポケモンチェックの 3。p.322・p.323）は v0.3b、こんらんのコインは v0.3c で対応した
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
| ワザで自分に与えるダメージの弱点・抵抗力 | v0.2f〜v0.3c: 関係しない場合（自分のタイプが自分の弱点・抵抗力のタイプと違う）は計算し、関係する場合は `UNRESOLVED_SELF_DAMAGE_WEAKNESS_RESISTANCE` で止めた。**v0.3d から、いつも計算する**（p.90 の解説。SUPPORTED）。対応カード（ピカチュウ）では結果は同じ |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 自分のタイプが自分の弱点・抵抗力のタイプのポケモンで止める処理 | 対応カードにはない。テスト専用のカード（ピカチュウの写しのタイプ・弱点・抵抗力を変えたもの）で確かめた |
| ベンチのポケモンのきぜつ（同時のきぜつを含む） | 判定は場のすべてのポケモンについて行うが、ベンチにダメージを与えるワザがない |

### 未実装

- 控えポケモンへのダメージ（p.320 のダメージの (2)・(4)）。受けるポケモンを選ぶ手順、控えへのダメージの計算（弱点・抵抗力・プラスパワーを計算しない。p.257）の照合が要る
- ほかの自分へのダメージのワザ（エレブー「かみなりパンチ」のダメージの目安「+」、サンダー「かみなり」など）。カードのページと照合していない
- こんらんの自分へのダメージ（v0.3c で対応した。ワザの説明による自分へのダメージとは別の計算。[confusion-attacks-v0.3c.md](confusion-attacks-v0.3c.md) 5 章）
- サイドを取る順番を番のプレイヤーが選ぶ決定（p.325。結果が変わらないので出していない）
- サドン・デスの延長戦（`Phase.SUDDEN_DEATH` で止める）
- ライチュウへの進化（v0.4a で 1 進化を実装したが、ライチュウは未照合・未登録。ワザ「こうそくいどう」は持続する効果）

### 原典未確認・未解決

- UNRESOLVED: ワザの説明による自分へのダメージに弱点・抵抗力を計算するか（関係する場合だけ止める。[self-damage-v0.2f.md 2 章](self-damage-v0.2f.md)）。
- p.125 のピカチュウの図版には ○ の中の数字（13）があり、第1弾の初版の図版かはこの画像からは決められない（文面は kyuura の写しと一致）。
- kyuura に、2000年のルールでのワザによる自分へのダメージの記録がない。ピカチュウの収録商品の書き方が違う（kyuura「スターターパック」、p.125「イントロパック」）（[ルールの仕様 6章の「kyuura の記録との違い」](rules-2000-02-14.md#kyuura-の記録との違い報告事項)）。

## v0.3a で加えたもの（特殊状態・どく・ポケモンチェック）

対応したカードは、ビードル（PMCG1-004）の「どくばり」です。原典照合・裁定の分類・コード・テストの対応は [special-conditions-v0.3a.md](special-conditions-v0.3a.md)（特殊状態・どく）、[pokemon-check-v0.3a.md](pokemon-check-v0.3a.md)（ポケモンチェック）、[weedle-v0.3a.md](weedle-v0.3a.md)（カード）、設計は [architecture-v0.3a.md](architecture-v0.3a.md) にあります。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| ビードルの登録（照合した説明文・最新の説明・出典 p.19）。間違った登録の検出 | p.6、p.19 | test_special_conditions.py `WeedleRegistrationTest`、test_effects.py |
| どくばり: 相手に 10 → コイン 1 枚 → 「おもて」ならどく。「うら」ならなし。ダメージが 0 でもどく。相手がきぜつしたらコインを投げない。エネルギー不足などは状態も乱数も変えない | p.19、p.309、p.320、p.321、p.323 | `PoisonStingTest` |
| 特殊状態は場のポケモン（`pokemon_id`）が持つ。バトル場だけ | p.322 | `PoisonStateTest`・`ConditionInvariantTest` |
| どくは積み重ならない。自然に回復しない。与えたポケモンが場をはなれても消えない。きずぐすりでは消えない | p.254、p.322 | `test_already_poisoned`・`test_poison_persists_and_accumulates`・`test_source_leaving_play_does_not_cure`・`test_potion_removes_counters_not_the_poison` |
| にげる・ポケモンいれかえでベンチに戻ったら消える（同じ処理）。ダメージ・ついているカード・番号はそのまま。2 回にげて直す（p.311 の例）。もどっても復活しない | p.311、p.322、p.325 | `CureTest` |
| ポケモンチェック: 各番のあとに 1 回（先攻の最初の番も。ワザのあと・番を終えたあと・トレーナーのあと）。番の終わり → ポケモンチェック → 次の番。二重にしない | p.309、p.323 | test_pokemon_check.py `TimingTest`・`ProgressInvariantTest` |
| どくのダメージ: それぞれ 10。両方の場。弱点・抵抗力・プラスパワー・ディフェンダーは関係しない。HP 未満・ちょうど・こえる。きずぐすりのあと。ベンチに戻ったポケモンは受けない | p.321、p.322、p.323 | `PoisonDamageTest` |
| 番の終わりのトラッシュ（プラスパワー・ディフェンダー）はポケモンチェックの前 | p.257、p.309、p.323 | `test_pluspower_is_gone_before_the_check`・`test_defender_expiring_this_turn_is_discarded_first` |
| ポケモンチェックの中のきぜつ: 相手側がサイド（自分の番のあとでも、番のプレイヤーに固定しない）、持ち主が出す、出せなければ負け、最後のサイドで勝ち、ついているカードもトラッシュ、交代のあとで次の番、山札切れ | p.311、p.312、p.323 | `KnockOutInCheckTest` |
| ポケモンチェックの中の決定: 答える人・選べるもの、ほかのコマンドの拒否、状態も乱数も変えない、複製しても同じ、形式 2 以上で書き出せる（形式 1 は拒否） | — | `test_decisions_in_the_check`・`test_copies_during_the_check_give_the_same_result`・`test_formats_during_the_check` |
| 状態の保存: clone・deepcopy・pickle、形式 5、形式 1〜4 は特殊状態を拒否 | — | test_special_conditions.py `StateTest` |
| ビードルを入れた 60 枚のデッキで、正式な対戦開始から勝敗まで（8 つの seed）。どくばり 69・どくにした 36・ポケモンチェック 262・どくのダメージ 40・どくできぜつ 13・にげるで解除 22・ポケモンいれかえで解除 1・ポケモンチェックの中で勝敗 5。同じ入力なら同じ結果。乱数はコインだけ。固定値（seed 13）。どくを直さないミラーで両方がどくできぜつして止まる（seed 27）。でたらめな操作（12 の seed） | — | test_weedle_games.py |

### 部分対応

| 項目 | 状況 |
|---|---|
| ポケモンチェックのどくで両方のプレイヤーのポケモンがきぜつする | 原典で決められないので止める（`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`）。片方だけなら処理する |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 両方がどくできぜつする場面（止める） | どくを直す手順の統合テストの 8 局・リポジトリの外の負荷テスト（160 局）では起こらなかった。どくを直さないビードルのミラーでは 400 局中 6 局で起こり、そのうち seed 27 を正式な対戦開始からのテストにした（test_weedle_games.py `NaturalDoubleKnockOutTest`）。勝敗の組み合わせごとの止まり方は、盤面を直接作るテストで確かめた |
| どくのダメージが 10 以外（HP をこえる場合） | 特殊などくは未実装。テスト専用のどくのダメージ 20 で、きぜつの判定だけを確かめた |
| 抵抗力のあるポケモンへのどく | 対応カードに草の抵抗力を持つポケモンがない。テスト専用のカードで確かめた |

### 未実装

- こんらん（状態・付ける効果・こんらんのコイン）は v0.3c、ねむり・マヒ（状態・付ける効果・ワザやにげるの制限・ポケモンチェックの 3・4）は v0.3b で対応した
- ポケモンチェックの 1（「ポケモンチェックで○○する」効果）と、その順番を選ぶ決定
- 特殊などく（ダメージ 20 など）を付ける効果
- 特殊状態を回復するトレーナー、特殊状態を参照するポケモンパワー
- 進化・退化で特殊状態が消えること（v0.4a で進化を実装した。退化は未実装）
- ほかのどくのワザ（キョウのビードル・ニドリーノなど。照合していない）

### 原典未確認・未解決

- UNRESOLVED: ポケモンチェックのどくで両方がきぜつする場合（同時か・交代の順番・サイドの順番を決める人）。特殊などくの重ね方の一部。
- p.19 のビードルの図版はレアリティマークのある版で、第1弾の初版ではない（文面は一致）。
- kyuura に、2000年の「どく」の規定と、ポケモンチェックで両方がきぜつする場合の記録がない（[ルールの仕様 6章の「kyuura の記録との違い」](rules-2000-02-14.md#kyuura-の記録との違い報告事項)）。

## v0.3b で加えたもの（ねむり・マヒ・ポケモンチェックの 3・4）

対応したカードは、キャタピー（PMCG1-002）の「いとをはく」と、パラス（PMCG2-003）の「ひっかく」「キノコのほうし」です。原典照合・裁定の分類・コード・テストの対応は [sleep-paralysis-v0.3b.md](sleep-paralysis-v0.3b.md)（ねむり・マヒ）、[pokemon-check-v0.3b.md](pokemon-check-v0.3b.md)（ポケモンチェック）、[cards-v0.3b.md](cards-v0.3b.md)（カード）、設計は [architecture-v0.3b.md](architecture-v0.3b.md) にあります。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| キャタピー・パラスの登録（照合した説明文・最新の説明・出典 p.17・p.38）。間違った登録の検出（キノコのほうしを「ダメージ 0」として登録できない） | p.6、p.17、p.38 | test_caterpie_paras.py `RegistrationTest`、test_effects.py |
| いとをはく: 相手に 10 → コイン 1 枚 → 「おもて」ならマヒ。弱点。ダメージが 0 でもマヒ。相手がきぜつしたらコインを投げない。エネルギー不足は状態も乱数も変えない | p.17、p.309、p.320、p.321、p.323 | `StringShotTest` |
| キノコのほうし: ダメージを与えない（ダメージの計算・`damage` のログ・プラスパワーなし）。コインなし。ねむりにする。ひっかく 20 | p.38、p.257、p.320 | `SporeTest` |
| ねむり: ワザを使えない・にげるを宣言できない（コイン・エネルギーのトラッシュの前に拒否。エネルギーの確認より前）。ポケモンいれかえでは入れ替える。エネルギー・ベンチ・トレーナー・番を終えるはできる。二重にならない | p.309、p.311、p.322、p.325 | test_sleep_paralysis.py `SleepTest` |
| ポケモンチェックの 3: 持ち主がコイン 1 枚（どちらの番のあとでも、ねむりにした番の終わりにも）。「おもて」で回復、「うら」で続く。ログ `coin_flip`（`source: "pokemon_check"`）・`sleep_check` | p.322、p.323 | test_pokemon_check_v0_3b.py `CheckStepsTest`、`test_sleep_persists_across_checks_until_heads` |
| マヒ: ワザを使えない・にげるを宣言できない。マヒ状態になった番を持ち、次の持ち主の番の終わりのポケモンチェックで自動的に回復（コインなし）。その番の終わりには回復しない。ワザを使わずに番を終えても回復。持ち主の番にマヒなら 2 つ後の番（番の数 + 1 ではない） | p.309、p.311、p.322、p.323 | test_sleep_paralysis.py `ParalysisTest`、`test_paralysis_only_recovers_on_its_turn_without_a_coin` |
| 重複と上書き: マヒ → ねむり（CONFIRMED）・ねむり → マヒ（SUPPORTED）は置きかわる（`replaced`）。ねむり → ねむり・マヒ → マヒは二重にならない。どく + ねむり・どく + マヒ。置きかえ・回復でどくは残る。ベンチに戻ったらすべて消える | p.311、p.322 | `OverlapTest` |
| ポケモンチェックの順番: 2 どく → きぜつ・サイド・判定・交代 → 3 ねむり → 4 マヒ → 次の番。きぜつしたポケモンのコインは投げない。交代のあとでコイン。勝敗が決まったら 3・4 はしない。二重に行わない | p.311、p.313、p.323 | `PoisonKnockOutAndStepsTest`・`test_the_check_is_done_once` |
| ポケモンチェックの中の決定を待つ間: 不正な操作・決定は状態も乱数も変えない（コインを先に投げない）。複製しても同じコイン。形式 5 で書き出せる | — | `test_rejections_during_the_check_do_not_flip_coins`・`test_copies_during_the_check_give_the_same_coin`・`test_formats_during_the_check` |
| 乱数の順番: ワザのコイン → ポケモンチェックのコイン。ねむりがなければ乱数を使わない | p.309、p.323 | `AttackThenCheckTest`・`test_no_conditions_no_coin` |
| 状態の保存: clone・deepcopy・pickle・乱数の JSON 復元で同じ結果。形式 5 に `sleep`・`paralysis`。形式 1〜4 は拒否。不変条件（型・マヒの番・期限の過ぎたマヒ・ベンチ） | — | test_sleep_paralysis.py `StateTest`・`ConditionInvariantTest`・`AtomicityTest` |
| キャタピー・パラス・ビードルを入れた 60 枚のデッキで、正式な対戦開始から勝敗まで（15 局）。ねむり 123・マヒ 72・ワザの拒否 78／70・にげるの拒否 80／70・ねむりの回復 92・継続 136・マヒの回復 68・ポケモンいれかえで解除・ねむり → マヒ 1・どく + ねむり 4・どく + マヒ 2・どくできぜつ 17（うち、ねむり 2・マヒ 2）・ポケモンチェックの中で勝敗 2。同じ入力なら同じ結果。乱数はコインだけ。固定値（seed 6）。v0.3a の未解決が自然に起こる seed 127。でたらめな操作（16 の seed） | — | test_sleep_paralysis_games.py |

### 部分対応

| 項目 | 状況 |
|---|---|
| マヒの再付与 | 回復する番が変わらない場合は処理する（二重にならない）。変わる場合は原典で決められないので `UNRESOLVED_REPARALYSIS_RECOVERY_TURN` |
| ポケモンチェックの 3 | ねむりの対戦ポケモンが 1 匹なら処理する。両方なら原典で決められないので止める（`UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`） |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 両方の対戦ポケモンがねむり（止める） | 対応カードでは起こらない（ねむりにするワザを使うポケモンはねむりでない。[pokemon-check-v0.3b.md](pokemon-check-v0.3b.md) 4 章）。統合テスト 15 局・負荷テスト 400 局で 0 回。盤面を直接作るテストで確かめた |
| マヒ → ねむりの置きかえ、マヒの再付与 | 対応カードでは起こらない（マヒ状態のポケモンは相手の次の番の前に回復する）。盤面を直接作るテストで確かめた |
| 持ち主の番にマヒ状態になる場合の回復の番 | 対応カードは相手だけをマヒにする。処理を直接呼ぶテストで確かめた |

### 未実装

- こんらん（状態・ワザのコインと自分への 20・にげるのコインと失敗の記録）は v0.3c で対応した
- ポケモンチェックの 1（「ポケモンチェックで○○する」効果）
- 進化・退化で特殊状態が消えること（v0.4a で進化を実装した。退化は未実装）
- 特殊状態を回復するトレーナー、特殊状態を参照するポケモンパワー
- ほかのねむり・マヒのワザ（プリン・カイロス・マチスのコイル・ミニリュウなど。照合していない）

### 原典未確認・未解決

- UNRESOLVED: 両方の対戦ポケモンがねむりのときのコインの順番。マヒの再付与で回復する番の数え方。v0.3a の未解決（両方がどくできぜつ）は変えていない。
- p.17・p.38 の図版の版（レアリティマークの有無）は画像から読めない（文面は一致。処理に関係しない）。
- kyuura に、特殊状態の重複（p.322）・両方がねむりのコインの順番・マヒの再付与の記録がない（[ルールの仕様 6章の「kyuura の記録との違い」](rules-2000-02-14.md#kyuura-の記録との違い報告事項)）。

## v0.3c で加えたもの（こんらん）

対応したカードは、ロコン（PMCG1-015）の「あやしいひかり」です。原典照合・裁定の分類・コード・テストの対応は [confusion-v0.3c.md](confusion-v0.3c.md)（こんらん状態）、[confusion-attacks-v0.3c.md](confusion-attacks-v0.3c.md)（ワザ・ロコン）、[retreat-confusion-v0.3c.md](retreat-confusion-v0.3c.md)（にげる）、設計は [architecture-v0.3c.md](architecture-v0.3c.md) にあります。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| ロコンの登録（照合した説明文・最新の説明・出典 p.67）。間違った登録の検出 | p.6、p.67 | test_confusion_attacks.py `VulpixRegistrationTest`、test_effects.py |
| あやしいひかり: 相手に 10 → コイン 1 枚 → 「おもて」ならこんらん。弱点。ダメージが 0 でもこんらん。相手がきぜつしたらコインを投げない。エネルギー不足は状態も乱数も変えない | p.67、p.309、p.320、p.321、p.323 | `ConfuseRayTest` |
| こんらん状態: バトル場だけ。自然に回復しない（ポケモンチェックで何もしない）。二重にならない。どくと重複（どちらの順でも）。ねむり・マヒと置きかわる（どちら向きも。どくは残る）。ベンチに戻ったら消え、復活しない。エネルギー・トレーナーは使える | p.309、p.311、p.322、p.323 | test_confusion.py `ConfuseTest`・`OverlapTest`・`PersistenceTest`・`LeavingTheBattleFieldTest` |
| ワザ: 宣言のあとに持ち主がコイン 1 枚（`source: "confusion"`）。「おもて」ならワザの説明どおり（ワザの説明のコインはそのあと）。「うら」ならもとのワザの内容を処理せず、自分に 20（`confusion_damage`）。どちらもワザを使ったことになり番が終わる。登録した 7 種類のワザすべてで確かめた | p.309、p.322、p.323 | test_confusion_attacks.py `ConfusedAttackOrderTest` |
| ワザ: 宣言できない操作（エネルギー不足・ワザの位置・番・未対応のワザ）はコインの前に拒否。ワザの説明の処理が決められない場合（v0.2f の自分の弱点・抵抗力）もコインの前に止める | p.309 | `test_rejected_commands_flip_no_coin`・`test_unresolved_attack_is_stopped_before_the_confusion_coin` |
| 20 ダメージ: 弱点（×2）・抵抗力（−30）は自分のタイプと自分の弱点・抵抗力で見る（テスト専用のカード）。0 以下は 0。相手のタイプ・相手についているカードは関係しない | p.321、p.322 | `ConfusionDamageTest` |
| 自分のきぜつ: HP ちょうど・こえる。サイドは相手が取り、自分が出す。相手が最後のサイドを取れば相手の勝ち。控えがなければ相手の勝ち | p.311、p.323 | `test_knock_out_thresholds`・`test_self_knock_out_gives_the_opponent_a_prize`・`test_self_knock_out_ends_the_game` |
| にげる: エネルギーをトラッシュしてからコイン。「おもて」なら入れ替え（こんらんは消える）。「うら」なら失敗（エネルギーは戻らない、入れ替えない、番は続く）。にげるエネルギー 0・1・2。こんらんでなければコインなし | pp.310〜311 | test_confusion_retreat.py `ConfusedRetreatTest` |
| にげる: 宣言できない操作（控えがいない・エネルギーの数・重複・ついていない・控えでない・番）はエネルギーもコインも使わない | p.310、p.311 | `test_illegal_retreats_are_rejected_before_any_energy_or_coin` |
| 失敗したポケモンは同じ番にもう宣言できない（`RETREAT_ALREADY_FAILED`）。次の番には宣言できる。制限はポケモンごと（ポケモンいれかえで出た別のポケモンは宣言できる）。失敗のあとのポケモンいれかえ | p.311、p.325 | `AfterFailureTest` |
| ポケモンいれかえ: こんらん状態でもコインなしで入れ替え、こんらんは消える | p.325、p.311 | test_confusion.py `test_switch_clears_confusion_without_a_coin` |
| 既存の止める条件（両方がどくできぜつ・両方がねむり）は、こんらんがあっても同じ | p.323 | `test_double_knockout_stop_is_unchanged`・`test_sleep_coin_order_stop_is_unchanged` |
| 状態の保存: 形式 5 に `confusion`、形式 6 に `retreat_failed_turn`。形式 1〜4（こんらん）・1〜5（失敗の記録）は拒否。clone・deepcopy・pickle・乱数の JSON 復元で同じ結果。不変条件（型・ベンチ・記録の番と持ち主・番の終わりのあと・対戦準備） | — | `SerializationTest`・`InvariantTest`、test_confusion_retreat.py `test_serialization_of_the_record` |
| ロコン・ビードル・キャタピー・パラスを入れた 60 枚のデッキで、正式な対戦開始から勝敗まで（36 局）。あやしいひかり 272・こんらん 82・ワザのこんらん 成功 14／失敗 20（自分のきぜつ 17）・にげるのこんらん 成功 41／失敗 34・再宣言の拒否 34・プラスパワー／ディフェンダーで止めた 2・どく + こんらん 3・ポケモンいれかえで消えた 5・こんらんが置きかわった 1。止まった対戦 0。でたらめな操作を混ぜる検査（16 局） | — | test_confusion_games.py |

### 部分対応

| 項目 | 状況 |
|---|---|
| こんらん状態のポケモンのワザ | ダメージを変えるカード（プラスパワー・ディフェンダー）がついていなければ処理する。ついていれば原典で決められないので `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` |
| 「にげる」に失敗したポケモンの再宣言 | こんらん状態のままなら `RETREAT_ALREADY_FAILED`（CONFIRMED）。こんらんが消えてバトル場に戻ったら原典で決められないので `UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED` |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 自分のタイプが自分の弱点・抵抗力のタイプのポケモンのこんらんの 20 | 対戦に使えるカードにない。テスト専用のカード（ロコンの記録を写して弱点・抵抗力を炎にしたもの）で確かめた |
| ねむり・マヒがこんらんに置きかわる | 統合テストの 36 局では起こらない（負荷テストでは起こった）。盤面を直接作るテストで確かめた |
| こんらんが消えたあとの再宣言（未解決で止める） | 統合テストの手順では起こらない（負荷テストで 7 回）。盤面からの単体テストで確かめた |

### 未実装

- 進化・退化で特殊状態が消えること・失敗の記録の扱い（v0.4a で進化を実装した。退化は未実装）
- 特殊状態を回復するトレーナー、ワザを失敗させる効果（p.309 の手順 4）、持続する効果
- ワザの説明にコストがあるワザ（こんらんの「うら」でコストを払うかを照合していない）
- ほかのこんらんのワザ（照合していない）

### 原典未確認・未解決

- UNRESOLVED: こんらんの 20 とプラスパワー・ディフェンダー。こんらんが消えたあとの「にげる」の再宣言。ワザの説明のコストとこんらん（対応カードにない）。v0.2f（自分へのワザのダメージの弱点・抵抗力）・v0.2b（ベンチがないときのポケモンいれかえ）・v0.3a・v0.3b の未解決は変えていない。
- p.67 の図版の版（レアリティマークの有無）は画像から読めない（文面は一致。処理に関係しない）。
- kyuura に、こんらんとねむり・マヒの置きかえ・こんらんの 20 とプラスパワー・ディフェンダー・失敗のあとこんらんが消えたポケモンの再宣言・にげるエネルギー 0 のときのコインの記録がない（[ルールの仕様 6章の「kyuura の記録との違い」](rules-2000-02-14.md#kyuura-の記録との違い報告事項)）。

## v0.3d で確かめたこと（特殊状態の総合検証・未解決の裁定）

カード・ルール・コマンド・状態の形・書き出しの形式は加えていません。設計は [architecture-v0.3d.md](architecture-v0.3d.md)、検証の記録は [special-conditions-audit-v0.3d.md](special-conditions-audit-v0.3d.md)・[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md)・[effect-preflight-v0.3d.md](effect-preflight-v0.3d.md) にあります。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| 8 つの特殊状態（なし・どく・ねむり・どく + ねむり・マヒ・どく + マヒ・こんらん・どく + こんらん）が不変条件を満たし、形式 5・6 で書き出せ、複製で保たれ、形式 1〜4 では `ValueError`。ベンチにはない | p.322 | test_special_conditions_matrix_v0_3d.py `EightStatesTest` |
| ねむり・マヒ・こんらんの 3 × 3 の上書き（どくのあり・なし）。同じなら `already`、違えば前の状態を `replaced` で消してから付ける。どくは残る。マヒの再付与で回復する番が変わる場合は止め、状態は変わらない | p.322 | `OverwriteMatrixTest` |
| 8 つの状態 × ワザ・にげる・ポケモンいれかえ・トレーナー・エネルギー・ベンチに出す・決定を待つ間の操作（コインは「おもて」「うら」） | p.309、pp.310〜311、p.322、p.325 | `AttackMatrixTest`・`RetreatMatrixTest`・`OtherActionsMatrixTest`・`PendingDecisionMatrixTest` |
| 8 つの状態 × ポケモンチェック（どく 10 → ねむりのコイン → マヒの回復、こんらんは何もしない、1 回だけ）、どくのきぜつで特殊状態がなくなりコインを投げない | p.322、p.323 | `PokemonCheckMatrixTest` |
| 自分へのワザのダメージの弱点・抵抗力（自分の弱点で ×2・抵抗力で −30・プラスパワーと弱点の順番）（v0.3d で UNRESOLVED → SUPPORTED） | p.90 の解説、p.321 | test_self_damage.py `SelfWeaknessResistanceTest`、test_confusion_attacks.py `test_self_typed_pikachu_resolves_after_heads` |
| 原典で決められない 5 件の境界（止まる・止まらない・状態と乱数が変わらない） | [unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md) | test_unresolved_rulings_v0_3d.py |
| 受け付けるか・拒否のコードが、コインの結果で変わらない（7 種類の実装 × 112 の盤面 × コイン 8 通り）。マヒの再付与の確認が相手の対戦ポケモンには働かないことの証明。エンジンが `problem` を宣言と乱数の前に聞くこと | p.309、p.322、p.323 | test_effect_preflight_v0_3d.py |
| にげるの失敗の記録が、今の番のログの `retreat_failed` と対応する（不変条件） | p.311 | test_confusion.py `test_retreat_failure_record_needs_the_failure_in_the_log` |
| 4 種類を混ぜた 60 枚のデッキで、正式な対戦開始から勝敗まで（44 局）。どく 123・ねむり 271・マヒ 142・こんらん 68 回、どく + ねむり／マヒ／こんらんの重なり、ワザ・にげるの拒否、こんらんの成功・失敗、ポケモンチェックのきぜつ 52。止まった対戦 0。固定値（Python 3.11〜3.13 で同じ）。でたらめな操作を混ぜる検査（12 局） | — | test_status_games_v0_3d.py |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 自分のタイプが自分の弱点・抵抗力のタイプのポケモンの、ワザによる自分へのダメージ | 対戦に使えるカードにない。テスト専用のカード（ピカチュウの記録を写して弱点・抵抗力を雷にしたもの）で確かめた |
| ねむり・マヒ・こんらんのあいだの置きかえ | 統合テストの 44 局では起こらない。負荷テスト（400 局）で 11 回。単体テストで確かめた |

### 未実装

- 進化（v0.4 の予定）。準備の調査は [evolution-readiness-v0.4.md](evolution-readiness-v0.4.md)。`EvolvePokemon` は `UNSUPPORTED_ACTION`、進化カードはデッキに入れられない（v0.4a で 1 進化を実装した）
- そのほかは v0.3c と同じ

### 原典未確認・未解決

- UNRESOLVED のまま（調べ直しても決まらない）: こんらんの 20 とプラスパワー・ディフェンダー、失敗のあとこんらんが消えたポケモンの再宣言、ポケモンチェックの両方のどくのきぜつ・両方のねむり、マヒの再付与で回復する番が変わる場合。v0.1・v0.2b の未解決も変わらない。
- 分類を上げたもの: 自分へのワザのダメージの弱点・抵抗力（UNRESOLVED → SUPPORTED）、こんらんの 20 の抵抗力・0 以下（SUPPORTED → CONFIRMED（解説））、こんらんの「うら」でもワザを使ったことになる（SUPPORTED → CONFIRMED）。[unresolved-rulings-v0.3d.md](unresolved-rulings-v0.3d.md) 6・7 章。
- kyuura に、p.90・p.207・p.238 の解説の記述、こんらんの未解決 2 件、進化したポケモンが「別のポケモン」であることの記録がない（[ルールの仕様 6章の「kyuura の記録との違い」](rules-2000-02-14.md#kyuura-の記録との違い報告事項)）。

## v0.4a で加えたもの（進化: たねポケモン → 1 進化ポケモン）

対応したカードは、パラセクト（PMCG2-010。パラスから進化。p.39）とジュゴン（PMCG1-030。パウワウから進化。p.102）です。原典照合・裁定の分類・コード・テストの対応は [evolution-rules-v0.4a.md](evolution-rules-v0.4a.md)（ルール）、[evolution-cards-v0.4a.md](evolution-cards-v0.4a.md)（カード）、[evolution-state-v0.4a.md](evolution-state-v0.4a.md)（状態）、設計は [architecture-v0.4a.md](architecture-v0.4a.md) にあります。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| パラセクト・ジュゴンの登録（照合した説明文・最新の説明・出典 p.39・p.102）。2 進化・登録のない 1 進化はデッキに入らない | p.39、p.102、p.316 | test_evolution_v0_4a.py `EvolutionCardsTest` |
| `EvolvePokemon`: 手札の 1 進化カードを、「○○から進化」の名前の自分の場のポケモン（バトル場・ベンチ）に重ねる。1 回の番に複数 | p.309、p.310、p.324 | `EvolveTest` |
| 進化できない場合: おたがいの最初の番、今の番に場に出したポケモン、今の番に進化したポケモン、名前の違うポケモン、相手のポケモン、手札にないカード、進化カードでないカード、決定を待つ間、終わった・止めた対戦。どれも状態も乱数も変えない | p.310 | `EvolveTest`・`EvolutionAtomicityTest` |
| 進化カードは手札からバトル場・ベンチに直接出せない（対戦準備でも） | p.308、p.309 | `test_evolution_cards_cannot_be_played_as_basic_pokemon` |
| 受け継ぐもの: ダメージカウンター・エネルギー（uid と順番）・場のポケモンの番号・場に出た番。HP・ワザ・にげるはいちばん上のカード | p.310 | `InheritanceTest`・`EvolvedPokemonTest` |
| ついているプラスパワー・ディフェンダーはついたまま、効果も有効期限も変わらない（SUPPORTED） | p.257、p.310、p.321、p.322 | `test_pluspower_stays_attached_and_works`・`test_defender_stays_attached_until_the_next_opponent_turn` |
| 8 つの特殊状態のどれから進化しても、特殊状態はすべて消える（ログ `special_conditions_removed`、`reason: "evolve"`）。ダメージは消えない | p.310、p.322 | `SpecialConditionsTest` |
| こんらんで「にげる」に失敗したポケモンが進化したら、記録が消え、「にげる」を宣言できる（SUPPORTED。ベンチで進化してから戻っても同じ）。進化しないで戻った場合は未解決のまま | p.310、p.311、p.322 | `RetreatFailureTest` |
| 進化したポケモンのきぜつ（ワザ・こんらん・どく）: 重なったカード・エネルギー・トレーナーをすべてトラッシュ。サイドは 1 枚。最後のポケモンなら勝敗が決まる | p.313、p.319、p.323 | `EvolvedKnockOutTest`、`test_confused_evolved_pokemon` |
| 状態の保存: 形式 7（重なり・場に出た番・進化した番）。形式 1〜6 は進化したポケモンがいれば `ValueError`。進化していない状態は形式 1〜6 で v0.3d と同じ。clone・deepcopy・pickle | — | `StackAndSerializationTest` |
| 不変条件: 重なったカードの保存則・重なりの形・場に出た番・進化した番・進化のあとの特殊状態と失敗の記録 | p.310、p.319、p.324 | `EvolutionInvariantTest` |
| パラス・パラセクト・パウワウ・ジュゴンを入れた 60 枚のデッキで、正式な対戦開始から勝敗まで（40 局）。進化 230（バトル場 47・ベンチ 183）、拒否 113（最初の番 28・今の番に出した 85）、特殊状態からの進化 9、ダメージのあるポケモンの進化 31、ついているトレーナーのあるポケモンの進化 4、進化したポケモンのワザ 197、進化したポケモンのきぜつ 62。でたらめな進化を混ぜる検査（12 局） | — | test_evolution_games_v0_4a.py |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 今の番に進化したポケモンの 2 回目の進化（`EVOLVED_THIS_TURN`） | 対応カードに 2 進化がないので、テスト専用のカード（パラセクトから進化）で確かめた（v0.4c 注: 実在のカード（ビードル → コクーン → スピアー）で、単体テストと自然な対戦（40 局で 51 回）で確かめた。[v0.4c の章](#v04c-で加えたもの2-進化とスピアー)） |
| 進化したあとの HP がダメージ以下になる場合（`UNRESOLVED_EVOLUTION_HP`） | 対応カードでは起こらない。HP 30 にしたテスト専用のパラセクトで確かめた |
| こんらんで「にげる」に失敗したポケモンの進化 | 総合テストの 40 局では起こらない（負荷テストの 400 局で 1 回）。盤面からの単体テストで確かめた |

### 未実装

- 2 進化・退化・ベイビィポケモンの進化、進化に関わるポケモンパワー・トレーナー、持続する効果・マーカー（進化の手順 3〜5 で消すもの・起こること）（v0.4b 注: ワザによる持続する効果と、進化での解除は v0.4b で実装した。[v0.4b の章](#v04b-で加えたものワザによる持続する効果とかたまる)）
- 同じ名前の別のカード（パラセクト LV.29・ジュゴン LV.24 など）、ほかの 1 進化ポケモン（トランセル・コクーン・ライチュウなど。効果が未実装）（v0.4b 注: トランセル・コクーンは v0.4b で対応した）

### 原典未確認・未解決

- UNRESOLVED（v0.4a で加えた）: 進化したあとの HP がダメージ以下になる場合。
- UNRESOLVED のまま: こんらんで「にげる」に失敗したあと、進化しないでベンチに戻り（こんらんが消え）同じ番にバトル場に戻ったポケモンの「にげる」。v0.3d までのほかの未解決も変わらない。
- 実装上の仮定: 場のポケモンの番号は進化しても変えない。`EvolvePokemon.target` は場のポケモンの番号。v0.1 からのコマンドで場のポケモンを指す uid は、いちばん上のカードの uid だけ。
- kyuura に、進化したポケモンが「別のポケモン」であること・ついているトレーナーと持続する効果の区別・失敗したポケモンの進化・HP がダメージ以下になる進化の記録がない（[ルールの仕様 6章の「kyuura の記録との違い」](rules-2000-02-14.md#kyuura-の記録との違い報告事項)）。

## v0.4b で加えたもの（ワザによる持続する効果と「かたまる」）

対応したカードは、トランセル（PMCG1-003。キャタピーから進化。p.18）とコクーン（PMCG1-009。ビードルから進化。p.21）です。ワザによる持続する効果は、場のポケモンの `persistent_effects` に持ち、特殊状態・ついているトレーナーとは別に扱います。原典照合・裁定の分類・コード・テストの対応は [persistent-effects-v0.4b.md](persistent-effects-v0.4b.md)（持続する効果）、[harden-v0.4b.md](harden-v0.4b.md)（カード・かたまる）、[persistent-damage-v0.4b.md](persistent-damage-v0.4b.md)（ダメージ計算）、設計は [architecture-v0.4b.md](architecture-v0.4b.md) にあります。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| トランセル・コクーンの登録（かたまる・しびれごな・どくのこな。カードごとに照合した印刷の文面・最新の説明・出典 p.18・p.21） | p.18、p.21 | test_harden_v0_4b.py `HardenRegistrationTest`、test_effects.py |
| かたまる: コイン 1 枚。「おもて」なら次の相手の番に「ダメージを受けない」状態（持続する効果）を自分に与える。「うら」なら何もしない。どちらもワザを使ったことになり番は終わる。ねむり・マヒ・エネルギー不足はコインの前に拒否。こんらんならこんらんのコインが先（「うら」なら「かたまる」のコインは投げない） | 最新の説明、p.236、p.309、p.322 | `HardenTest` |
| 「ダメージを受けない」状態: そのポケモンへのダメージの要素は無効（計算しない。ログ `damage_prevented`）。10・20・30（弱点で 60）・50・抵抗力・プラスパワー・ディフェンダーのどれでも。ほかのポケモンへのダメージ（でんげきの自分への 10）は有効 | p.321 | `DamagePreventionTest` |
| ダメージ以外の効果は受ける: どく・マヒ・こんらん・ねむり。効果のコインは省かない（ダメージで相手がきぜつしないので、v0.3a 以降の「きぜつしたらコインを投げない」にも当たらない） | 最新の説明、p.321、p.44 | `AdditionalEffectsTest` |
| ポケモンチェックのどくのダメージは受ける（どちらの番でもない）。どくでのきぜつで効果も消える | p.323、p.236、p.322 | `PokemonCheckTest` |
| 期限: 効果を与えた番・ポケモンチェックでははたらかず、次の相手の番の間はたらき、その番の終わり（ポケモンチェックの前）に 1 回だけ消える。はたらく番に勝敗が決まったら、終わった状態に残る | p.236、p.18（ワザ解説）、p.323 | `ExpiryTest` |
| 状態の保存: 形式 8（`persistent_effects`）。形式 1〜7 は効果があると `ValueError`。効果のない状態は形式 1〜7 で v0.4a と同じ。clone・deepcopy・pickle | — | `SerializationTest` |
| 不変条件: 型・発生源・番・期限・置き場所（バトル場だけ）・重複・ログとの対応（消したあと・進化・ベンチに戻ったあとに残らない） | p.311、p.322、p.323 | `PersistentEffectInvariantTest` |
| 不正な操作・原典で決められない操作は、効果も乱数も変えない。決定を待つ間はほかの操作を受け付けない | — | `AtomicityTest` |
| キャタピー → トランセル、ビードル → コクーンの進化（v0.4a の規定のまま）。進化した番に「かたまる」。進化したポケモンのきぜつで下のカードもトラッシュ、サイド 1 枚 | p.309、p.310、p.313、p.323 | `EvolutionWithHardenTest` |
| トランセル・コクーン・キャタピー・ビードルとドードー・ロコン・パラス・ピカチュウを入れた 60 枚のデッキで、正式な対戦開始から勝敗まで（40 局）。進化 239、かたまる 392（「おもて」195・「うら」184・こんらんで 13）、ダメージの無効 103、無効のあとのどく 14・マヒ 19・こんらん 13、期限切れ 191、どくのきぜつでの消滅 1、進化したポケモンのきぜつ 59。でたらめな操作を混ぜる検査（12 局） | — | test_harden_games_v0_4b.py |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| ベンチに戻る（にげる・ポケモンいれかえ）・進化での効果の解除。こんらんで失敗した「にげる」では消えない。戻っても復活しない | 「かたまる」の効果は相手の番だけにあり、そのあいだ持ち主は動かないので、自然な対戦では起こらない。盤面を直接作った単体テストで確かめた（`RemovalTest`） |
| 自分へのダメージ・こんらんの 20 でのきぜつによる消滅 | 同じ（効果を与えた番に、そのポケモンが行動する盤面を作った） |
| 相手の番の、ワザ以外のダメージ（トレーナー・特殊能力）も受けない（p.236） | 対応カードに、ワザ以外でダメージを与えるものがない |

### 未実装

- 相手のポケモンに与える持続する効果（「すなかけ」「からまるいと」など）、カウンター・マーカーをのせるタイプ、「効果を受けない」状態（p.321）、持続する効果を消すカード、退化での解除
- 2 進化（バタフリー・スピアー）。ほかの 1 進化ポケモン（ライチュウなど。効果が未実装）（v0.4c 注: スピアーは v0.4c で対応した。バタフリーは未実装）

### 原典未確認・未解決

- UNRESOLVED（v0.4b で加えた）: 「ダメージを受けない」状態のポケモンに、コインでダメージの量を決める要素だけのワザを使うときのコイン（`UNRESOLVED_PREVENTED_COIN_DAMAGE`）。
- v0.4a までの未解決（`UNRESOLVED_EVOLUTION_HP`・`UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS`・`UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED`・`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`・`UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`・`UNRESOLVED_REPARALYSIS_RECOVERY_TURN`・切り直しの補償・きずぐすり・ポケモンいれかえ）は変えていない。
- 実装上の仮定: 「次の相手の番」は効果を与えた番の番号 + 1（番は交互に進む）。期限切れは番の終わりのうち、ついているトレーナーのトラッシュのあと・`turn_end` の前。「ダメージを受けない」状態のダメージの要素は計算しない（防いだ量はログにない）。
- kyuura に、「かたまる」の印刷の文面と最新の説明を区別した記録と、持続する効果の規定（ベンチ・場をはなれる・復活しない・重複・ポケモンチェック）の記録がない（[ルールの仕様 6章の「kyuura の記録との違い」](rules-2000-02-14.md#kyuura-の記録との違い報告事項)・[data-provenance.md](data-provenance.md)）。

## v0.4c で加えたもの（2 進化とスピアー）

対応したカードは、スピアー（PMCG1-012。コクーンから進化する 2 進化。p.21）です。たね・1 進化・2 進化の 3 枚で構成される 1 匹のポケモンを、v0.4a の `EvolvePokemon`・`evolution_stack` と v0.4b の持続する効果の上で扱います（状態の項目・コマンド・段階・ワザの実装・書き出しの形式は増やしていない）。原典照合・裁定の分類・コード・テストの対応は [stage2-evolution-v0.4c.md](stage2-evolution-v0.4c.md)（ルール）、[beedrill-v0.4c.md](beedrill-v0.4c.md)（カード）、[stage2-state-v0.4c.md](stage2-state-v0.4c.md)（状態）、設計は [architecture-v0.4c.md](architecture-v0.4c.md) にあります。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| スピアーの登録（ダブルニードル `CoinFlipDamage(coins=2, damage_per_heads=30)`・どくばり `PoisonOnHeads`。照合した印刷の文面・最新の説明・出典 p.21）。ビードルのどくばりとは別に、スピアーのカード id で登録。2 進化の段階だけでは対応にしない（フシギバナは未対応のまま） | p.21、p.316 | test_stage2_v0_4c.py `BeedrillCardTest`、test_effects.py |
| `EvolvePokemon` で 1 進化ポケモン → 2 進化ポケモン（同じコマンド）。バトル場・ベンチ。1 回の番に複数のポケモン | p.309、p.310、p.316、p.319、p.324 | `Stage2EvolveTest` |
| 同じ番に 1 進化したポケモンは 2 進化できない（`EVOLVED_THIS_TURN`）。次の自分の番にはできる。制限は 1 匹ごと | p.310 | `test_weedle_kakuna_beedrill_over_two_turns`・`test_bench_and_several_pokemon_in_one_turn` |
| 進化できない場合: たね → 2 進化（`EVOLUTION_NAME_MISMATCH`）、名前の違う 1 進化・2 進化、最初の番、今の番に出したポケモン、相手のポケモン、未対応の 2 進化（`UNSUPPORTED_EVOLUTION`）、決定を待つ間、終わった・止めた対戦。2 進化カードは場に直接出せない。どれも手札・重なり・特殊状態・持続する効果・乱数・ログを変えない | p.308、p.309、p.310、p.324 | `Stage2EvolveTest`・`AtomicityTest` |
| 3 枚の重なり（下から ビードル・コクーン、いちばん上がスピアー）・`cards()`・場のポケモンの番号・カードの定義の切り替え（HP・弱点・抵抗力・にげる 0・ワザ）。下のカードのワザは使えない | p.310、p.313、p.319 | `ThreeCardStructureTest` |
| 受け継ぐもの: ダメージ・エネルギー・プラスパワー・ディフェンダー（効果と有効期限）・場に出た番。HP が同じ（80 → 80）でも進化できる | p.310 | `InheritanceTest`・`test_same_hp_evolution_and_the_unresolved_hp_case` |
| 8 つの特殊状態のどれから 2 進化しても、特殊状態はすべて消える（ダメージは消えない。どくのダメージもない）。進化したあとで受けた特殊状態は不変条件で拒否しない | p.310、p.322 | `SpecialConditionsTest` |
| にげるの失敗の記録は 2 進化でも消える（SUPPORTED）。進化しないで戻った場合は未解決のまま | p.310、p.311、p.322 | `RetreatFailureTest` |
| ダブルニードル: コイン 2 枚、「おもて」の数 × 30（0・30・60。0 はワザの失敗ではない）、弱点・抵抗力・プラスパワー・ディフェンダー・きぜつ・サイド、こんらんならこんらんのコインが先、同じ seed・複製・pickle で同じ結果 | p.21、p.309、p.320、p.321 | `TwineedleTest` |
| どくばり: 40 → コイン → 「おもて」ならどく。必要なエネルギー草 3、相手がきぜつしたらコインなし、二重のどくにならない、ポケモンチェックのどくでのきぜつ | p.21、p.309、p.322、p.323 | `PoisonStingTest` |
| 「かたまる」の相手: ダブルニードルは `UNRESOLVED_PREVENTED_COIN_DAMAGE`（コインの前。こんらんのコインも投げない）、効果が消えれば使える。どくばりはダメージが無効・コインとどくは有効 | p.321 | `PreventedTargetTest`、test_effect_preflight_v0_3d.py `CoinIndependenceTest` |
| 2 進化ポケモンのきぜつ（相手のワザ・こんらん・どく・自分へのダメージ・相手のスピアーのワザ）: 3 枚・エネルギー・ついているトレーナーをすべてトラッシュ。持続する効果はトラッシュに置かない。サイドは 1 枚。交代・勝敗 | p.313、p.319、p.323 | `Stage2KnockOutTest` |
| 不変条件: 3 枚まで・下から順の段階・すべての隣り合う 2 枚の名前・重複・保存則・番号・2 進化の前の 1 進化の番・ログ `evolve` との対応 | p.310、p.319、p.324 | `Stage2InvariantTest`、test_stage2_games_v0_4c.py `test_log_must_cover_every_evolution` |
| 状態の保存: 形式 7・8 のまま（重なりが 2 つ）。形式 1〜6 は `ValueError`。clone・deepcopy・pickle | — | `test_serialization_keeps_format_8`・`test_copies_are_independent` |
| ビードル・コクーン・スピアーを入れた 60 枚のデッキで、正式な対戦開始から勝敗まで（40 局）。2 進化 79（バトル場 31・ベンチ 48）、同じ番の再進化の拒否 51、ダブルニードル 71、どくばり 55（どく 14）、ダブルニードルの未解決 5、スピアーのきぜつ 24（3 枚のトラッシュ 24）。でたらめな操作を混ぜる検査（12 局） | — | test_stage2_games_v0_4c.py |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 持続する効果（「かたまる」）を受けたコクーンの 2 進化での解除 | 効果は相手の番だけにはたらくので、自然な対戦では起こらない。盤面を直接作った単体テストで確かめた（`PersistentEffectsTest`） |
| 名前は合うが段階が合わない組み合わせ（`EVOLUTION_STAGE_MISMATCH`） | 実在のカードの組では名前の確認が先に拒否する。テスト専用のカードで確かめた |
| ワザによる自分へのダメージでの 2 進化ポケモンのきぜつ | 対応カードに自分へのダメージのワザを持つ 2 進化はない。テスト専用のカードで確かめた |
| 草の抵抗力を持つ相手へのダブルニードル | 対応カードに草の抵抗力を持つものはない。テスト専用のカードで確かめた |
| 進化した番に自分のポケモンが特殊状態になる | 対応カードにない。どくにする処理を直接呼んで確かめた |

### 未実装

- バタフリー（PMCG2-007。ふきとばし・メガドレイン）。写しにも入れていない（[architecture-v0.4c.md](architecture-v0.4c.md) 14 章に v0.4d の準備）
- 退化、ベイビィポケモン、進化を助ける・妨げるトレーナーとポケモンパワー（フシギバナなど）

### 原典未確認・未解決

- 2 進化で新しく決められなくなった事項はない。v0.4b までの未解決（`UNRESOLVED_PREVENTED_COIN_DAMAGE`・`UNRESOLVED_EVOLUTION_HP`・`UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS`・`UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED`・`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`・`UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`・`UNRESOLVED_REPARALYSIS_RECOVERY_TURN`・切り直しの補償・きずぐすり・ポケモンいれかえ・特殊などく・サドン・デスの延長戦）は変えていない。`UNRESOLVED_PREVENTED_COIN_DAMAGE` はダブルニードルにも当てはまる。
- 実装上の仮定: 場のポケモンの番号は 2 進化しても変えない。1 進化した番は状態に持たず、不変条件はログ `evolve` と照らす（盤面を直接作ったテストでは、作った重なりのログがないので状態だけの必要条件まで）。段階の不一致を `EVOLUTION_STAGE_MISMATCH` にした。
- kyuura に、2 進化に固有の記録（3 枚の構成・同じ番の 1 進化 → 2 進化）と、ダブルニードルの印刷の文面と最新の説明を区別した記録がない（[data-provenance.md](data-provenance.md)・[stage2-evolution-v0.4c.md](stage2-evolution-v0.4c.md) 5 章）。
