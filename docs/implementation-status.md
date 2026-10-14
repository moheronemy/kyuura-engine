# 実装状況（v0.1〜v0.17）

基準: 公式ルール 2000.02.14版（『ポケモンカードオフィシャルブック2000』pp.306〜326 [P43]）、kyuura `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`。項目ごとの根拠は [ルールの仕様](rules-2000-02-14.md) にあります。v0.2 の前のレビューの結果は [review-v0.1.md](review-v0.1.md)、公開 API の評価は [api-review.md](api-review.md) にあります。

v0.2a は、v0.1 のルールと対戦の結果を変えずに、カード効果を実装するための構造を整えた版です（[アーキテクチャ](architecture-v0.2a.md)）。v0.2b は、その構造を使ってトレーナーカード 3 枚（マサキ・きずぐすり・ポケモンいれかえ）を実装した版です（[アーキテクチャ](architecture-v0.2b.md)、[原典照合](trainers-v0.2b.md)）。v0.2c は、プラスパワーと、場に残るトレーナー・有効期限・ダメージ計算の段階への効果の適用を加えた版です（[アーキテクチャ](architecture-v0.2c.md)、[原典照合](pluspower-v0.2c.md)）。v0.2d は、コイントスと、コインの結果でダメージが変わるワザ（ドードーの「みだれづき」）を加えた版です（[アーキテクチャ](architecture-v0.2d.md)、[コイントスの規定](coin-rules-v0.2d.md)、[みだれづき](coin-attacks-v0.2d.md)）。v0.2e は、ディフェンダーと、防御側のダメージ変更・相手の番にまたがる有効期限を加えた版です（[アーキテクチャ](architecture-v0.2e.md)、[原典照合](defender-v0.2e.md)）。v0.2f は、ワザで自分に与えるダメージと、同時のきぜつ（両方のプレイヤーのポケモンが 1 つのワザできぜつする）を、ピカチュウの「かじる」「でんげき」とともに加えた版です（[アーキテクチャ](architecture-v0.2f.md)、[自分へのダメージ](self-damage-v0.2f.md)、[同時のきぜつ](simultaneous-ko-v0.2f.md)、[ピカチュウ](pikachu-v0.2f.md)）。v0.3a は、特殊状態の共通基盤と「どく」、番と番のあいだのポケモンチェックを、ビードルの「どくばり」とともに加えた版です（[アーキテクチャ](architecture-v0.3a.md)、[特殊状態](special-conditions-v0.3a.md)、[ポケモンチェック](pokemon-check-v0.3a.md)、[ビードル](weedle-v0.3a.md)）。v0.3b は、ねむり・マヒと、それによるワザ・にげるの制限、ポケモンチェックの 3（ねむりのコイン）・4（マヒの回復）を、キャタピーの「いとをはく」・パラスの「ひっかく」「キノコのほうし」とともに加えた版です（[アーキテクチャ](architecture-v0.3b.md)、[ねむり・マヒ](sleep-paralysis-v0.3b.md)、[ポケモンチェック](pokemon-check-v0.3b.md)、[キャタピー・パラス](cards-v0.3b.md)）。v0.3c は、こんらんと、こんらん状態のポケモンのワザ（コイン・自分への 20 ダメージ）・にげる（コイン・エネルギー・同じ番の再宣言の制限）を、ロコンの「あやしいひかり」とともに加えた版です（[アーキテクチャ](architecture-v0.3c.md)、[こんらん](confusion-v0.3c.md)、[ワザ・ロコン](confusion-attacks-v0.3c.md)、[にげる](retreat-confusion-v0.3c.md)）。v0.3d は、カード・ルールを加えず、特殊状態 4 種類の総合検証・未解決の裁定の再調査・コインの前の検証・進化の準備の調査をした版です（[アーキテクチャ](architecture-v0.3d.md)、[総合検証](special-conditions-audit-v0.3d.md)、[未解決の裁定](unresolved-rulings-v0.3d.md)、[コインの前の検証](effect-preflight-v0.3d.md)、[進化の準備](evolution-readiness-v0.4.md)）。v0.4a は、たねポケモン → 1 進化ポケモンの進化（`EvolvePokemon`）を、パラセクト（パラスから進化）・ジュゴン（パウワウから進化）とともに加えた版です（[アーキテクチャ](architecture-v0.4a.md)、[進化のルール](evolution-rules-v0.4a.md)、[カード](evolution-cards-v0.4a.md)、[状態](evolution-state-v0.4a.md)）。v0.4b は、ワザによる持続する効果（番をまたいで残り、期限・ベンチ・進化・きぜつで消える）を、トランセル（キャタピーから進化）・コクーン（ビードルから進化）の「かたまる」とともに加えた版です（[アーキテクチャ](architecture-v0.4b.md)、[持続する効果](persistent-effects-v0.4b.md)、[かたまる](harden-v0.4b.md)、[ダメージ計算](persistent-damage-v0.4b.md)）。v0.4c は、1 進化ポケモン → 2 進化ポケモンの進化（たね・1 進化・2 進化の 3 枚で構成される 1 匹のポケモン）を、スピアー（コクーンから進化）の「ダブルニードル」「どくばり」とともに加えた版です（[アーキテクチャ](architecture-v0.4c.md)、[2 進化のルール](stage2-evolution-v0.4c.md)、[スピアー](beedrill-v0.4c.md)、[状態](stage2-state-v0.4c.md)）。v0.4d は、ワザの途中で相手プレイヤーの決定を待って同じワザを再開する処理（相手の強制交代）と、ワザが与えたダメージの結果を後の要素に渡して回復する処理を、バタフリー（トランセルから進化する 2 進化）の「ふきとばし」「メガドレイン」とともに加えた版です（[アーキテクチャ](architecture-v0.4d.md)、[強制交代](forced-switch-v0.4d.md)、[与えたダメージと回復](damage-drain-v0.4d.md)、[バタフリー](butterfree-v0.4d.md)）。v0.4e は、カード・ルールを加えず、v0.4a〜v0.4d の総合監査（組み合わせの表・不変条件・ログと書き出しの監査・前の版との比較・負荷・変異）と、見つけた不変条件の検出の漏れの修正、比較と負荷の道具をした版です（[総合監査](integration-audit-v0.4e.md)、[組み合わせの表](interaction-matrix-v0.4e.md)、[互換性](compatibility-v0.4e.md)、[未解決の範囲](unresolved-audit-v0.4e.md)、[アーキテクチャ](architecture-v0.4e.md)、[v0.5 の準備](v0.5-readiness.md)）。v0.5 は、ポケモンパワー（特殊能力）の基盤（`UsePokemonPower`・パワーの登録表）を、フシギバナの「エナジートランス」と、進化元のフシギダネ（やどりぎのタネ）・フシギソウ（つるのむち・どくのこな）とともに加えた版です（[アーキテクチャ](architecture-v0.5.md)、[ポケモンパワーの規定](pokemon-powers-v0.5.md)、[フシギバナ](venusaur-v0.5.md)、[フシギダネ・フシギソウ](bulbasaur-line-v0.5.md)、[エナジートランスの処理](energy-transfer-v0.5.md)、[確かめた結果](v0.5-verification.md)）。v0.6 は、カメックスのポケモンパワー「あまごい」（手札の「水」エネルギーカードを自分の場の「水」ポケモンにつける）とワザ「ハイドロポンプ」、進化元のゼニガメ・カメールを加えた版です（[原典の照合と裁定](rain-dance-v0.6.md)、[アーキテクチャ](architecture-v0.6.md)、[確かめた結果](v0.6-verification.md)）。v0.7 は、フーディンのポケモンパワー「ダメージスワップ」（自分の場のポケモンのダメージカウンターを、きぜつさせない範囲で自分の場の別のポケモンへのせかえる）とワザ「あやしいひかり」、進化元のケーシィ（ねんりき）・ユンゲラー（じこさいせい・ちょうねんりき）を加えた版です（[ダメージスワップの照合と裁定](damage-swap-v0.7.md)、[ケーシィ・ユンゲラー・フーディン](alakazam-line-v0.7.md)、[アーキテクチャ](architecture-v0.7.md)、[確かめた結果](v0.7-verification.md)）。v0.8 は、ベトベトンのポケモンパワー「かがくへんかガス」（常にはたらいていて宣言しない。場にいるかぎり、ほかのすべての特殊能力を使えなくし、その力も消す。ねむり・マヒ・こんらんのときは消える）とワザ「ヘドロこうげき」、進化元のロケット団のベトベター（どくガス・ねばりつく）を加えた版です（[かがくへんかガスの照合と裁定](chemical-gas-v0.8.md)、[ベトベター・ベトベトン](grimer-line-v0.8.md)、[常にはたらく効果](continuous-effects-v0.8.md)、[アーキテクチャ](architecture-v0.8.md)、[確かめた結果](v0.8-verification.md)）。v0.9 は、化石の秘密のゴーストのポケモンパワー「とうめい」（ワザによってダメージや効果を受けるときに自動的にはたらき、コインが「おもて」なら、そのダメージと効果を受けない。ねむり・マヒ・こんらんのときは消える）とワザ「あくむ」、進化元の化石の秘密のゴース（したでなめる・エナジーへんかん）を加えた版です（[とうめいの照合と裁定](transparency-v0.9.md)、[ゴース・ゴースト](haunter-line-v0.9.md)、[自動的にはたらく特殊能力](automatic-powers-v0.9.md)、[アーキテクチャ](architecture-v0.9.md)、[確かめた結果](v0.9-verification.md)）。v0.10 は、カイリキーのポケモンパワー「はんげき」（相手のワザによってダメージを受けたときに自動的にはたらき、それによってきぜつしても、ダメージを与えたポケモンに弱点・抵抗力に関係なく 10 ダメージ。ダメージを受けるとき、すでにねむり・マヒ・こんらんならはたらかない）とワザ「ちきゅうなげ」、進化元のゴーリキー（からてチョップ・じごくぐるま）を加えた版です（[はんげきの照合と裁定](counterattack-v0.10.md)、[ワンリキー・ゴーリキー・カイリキー](machamp-line-v0.10.md)、[ダメージを受けたあとにはたらく特殊能力](post-damage-powers-v0.10.md)、[アーキテクチャ](architecture-v0.10.md)、[確かめた結果](v0.10-verification.md)）。それぞれの状況は [v0.2a の章](#v02a-で加えた構造)・[v0.2b の章](#v02b-で加えたものトレーナー)・[v0.2c の章](#v02c-で加えたものプラスパワー)・[v0.2d の章](#v02d-で加えたものコイントスとみだれづき)・[v0.2e の章](#v02e-で加えたものディフェンダー)・[v0.2f の章](#v02f-で加えたもの自分へのダメージと同時のきぜつ)・[v0.3a の章](#v03a-で加えたもの特殊状態どくポケモンチェック)・[v0.3b の章](#v03b-で加えたものねむりマヒポケモンチェックの-34)・[v0.3c の章](#v03c-で加えたものこんらん)・[v0.3d の章](#v03d-で確かめたこと特殊状態の総合検証未解決の裁定)・[v0.4a の章](#v04a-で加えたもの進化-たねポケモン--1-進化ポケモン)・[v0.4b の章](#v04b-で加えたものワザによる持続する効果とかたまる)・[v0.4c の章](#v04c-で加えたもの2-進化とスピアー)・[v0.4d の章](#v04d-で加えたもの相手の強制交代与えたダメージによる回復バタフリー)・[v0.4e の章](#v04e-で確かめたことv04av04d-の総合監査)・[v0.5 の章](#v05-で加えたものポケモンパワーとフシギバナ)・[v0.6 の章](#v06-で加えたものあまごいとカメックス)・[v0.7 の章](#v07-で加えたものダメージスワップとフーディン)・[v0.8 の章](#v08-で加えたものかがくへんかガスとベトベトン)・[v0.9 の章](#v09-で加えたものとうめいとゴースト)・[v0.10 の章](#v010-で加えたものはんげきとカイリキー)・[v0.11 の章](#v011-で加えたものこんじょうとサカキのカイリキー) にあります。

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

- 退化・ベイビィポケモンの進化（たねポケモン → 1 進化は v0.4a、1 進化 → 2 進化は v0.4c で対応した。2 進化のカードはスピアー（v0.4c）・バタフリー（v0.4d）・フシギバナ（v0.5）・カメックス（v0.6）・フーディン（v0.7）・カイリキー（v0.10）だけ）。進化に関わるポケモンパワー・トレーナー
- 特殊状態のうち、ポケモンチェックの 1、特殊などく、特殊状態を回復するカード（どく・ねむり・マヒ・こんらんとこんらんのコインは v0.3a〜v0.3c で対応した）
- ポケモンパワー（特殊能力）のうち、フシギバナの「エナジートランス」（v0.5）・カメックスの「あまごい」（v0.6）・フーディンの「ダメージスワップ」（v0.7）・ベトベトンの「かがくへんかガス」（v0.8。常にはたらく）・ゴーストの「とうめい」（v0.9。自動的にはたらく）・カイリキーの「はんげき」（v0.10。ダメージを受けたときに自動的にはたらく）・サカキのカイリキーの「こんじょう」（v0.11。きぜつするときに使える）・R団のファイヤーの「ふしちょう」（v0.12。きぜつしたときに使える）のほか。「とうめい」「はんげき」のほかの自動的にはたらく特殊能力（［ショックボム］・［わるいねぞう］など）、こんじょうのほかのきぜつするとき・ふしちょうのほかのきぜつしたときに使える特殊能力、かがくへんかガスのほかの常にはたらいている特殊能力、回数の制限のある特殊能力、かがくへんかガスのほかの特殊能力を止める効果（まきちらせ！ベトベトガス・ふしぎなガスなど期限のあるもの）、相手の番・ポケモンチェックに使う特殊能力、決定を出す特殊能力（[architecture-v0.5.md](architecture-v0.5.md) 9 章・[architecture-v0.6.md](architecture-v0.6.md) 12 章・[architecture-v0.7.md](architecture-v0.7.md) 13 章・[architecture-v0.8.md](architecture-v0.8.md) 14 章・[architecture-v0.9.md](architecture-v0.9.md) 14 章・[architecture-v0.10.md](architecture-v0.10.md) 17 章・[architecture-v0.11.md](architecture-v0.11.md) 16 章・[architecture-v0.12.md](architecture-v0.12.md) 16 章）。登録のないパワーを持つカードはデッキに入らず、使用は `UNSUPPORTED_POKEMON_POWER`
- トレーナーカード（v0.2b・v0.2c・v0.2e で対応した 5 枚のほか）、スタジアム、ポケモンのどうぐなど（ダメージ計算の 5 段階のプラスパワーは v0.2c、7 段階のディフェンダーは v0.2e で対応。2・6・8 段階の効果を持つカードはない）
- ベイビィポケモン
- 特殊エネルギー（悪・鋼、無色2個エネルギーなど）
- 効果のあるワザ（説明文のあるワザ、「+」「−」「×」のダメージ、コインを投げるワザ、ベンチへのダメージ、エネルギーをトラッシュするワザ）。v0.2d で対応したのはドードーの「みだれづき」（コイン 2 枚の「おもて」の数×10）、v0.2f で対応したのはピカチュウの「でんげき」（「うら」なら自分にも 10）だけ。ほかの自分へのダメージのワザ（エレブー「かみなりパンチ」、サンダー「かみなり」など）は未照合・未登録。v0.3a 以降に加えたワザは各版の章（エネルギーをトラッシュするワザは、ユンゲラーの「じこさいせい」（v0.7）だけ）
- ワザによる持続する効果のうち、「かたまる」（v0.4b）・「ほのおのかべ」（v0.12）・「こうらがえし」（v0.13）のほか（「クロスカウンター」などのほかの相手の番ではたらく効果、相手に与える「すなかけ」「からまるいと」、ほかの自分に与える効果、カウンター・マーカーをのせるタイプ、「効果を受けない」状態）、マーカーとカウンター、変身、ポケモンいれかえ以外の入れ替えの効果（ふきとばしなど）、バトル場をはなれられないポケモン
- 同じタイミングで起こったことの順番を番のプレイヤーが決める処理（p.325）。同時のきぜつで両方がサイドを取る順番は、選ばせずに番のプレイヤーから取る（どちらの順でも結果が同じため。[simultaneous-ko-v0.2f.md 5 章](simultaneous-ko-v0.2f.md)）。「ふしちょう」とサイド・勝ち負け・バトル場に出すの順番も、選ばせずに正規化している（[post-knockout-powers-v0.12.md 3 章](post-knockout-powers-v0.12.md)）
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
| 参照カード（PMCG1-021・075・PMCG3-003・PMCG1-047。v0.4e までは PMCG1-011 フシギバナ、v0.5 では PMCG1-032 カメックス、v0.6 では PMCG1-049 フーディン、v0.10 では PMCG6-061 サカキのカイリキー。どれも照合して対応にした） | 対戦には使わないので、『オフィシャルブック2000』と照合していない（リザードン（PMCG1-021。登録のないパワー「エナジーバーン」とワザ「ほのおのうず」）は v0.7 で照合していない。化石の秘密のベトベター（PMCG3-003）は v0.8 で p.47 と照合したが、「ちいさくなる」が未実装なので参照カードのまま。第1弾のゴースト（PMCG1-047）は v0.9 で p.160 の見出しと「ワザ」欄を照合したが、「ゆめくい」（ワザの失敗）が未実装なので参照カードのまま。PMCG1-014 ヒトカゲは、v0.2a で「ひっかく」を登録するために p.63 と照合した。きずぐすりは v0.2b、ドードー（PMCG1-061）は v0.2d で対戦用に移し、p.254・p.231 と照合した） |
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
| あまごいでつけたあと、その番にまだ手札からつける通常の操作をしていないときの、通常の操作（v0.6。p.310「1回の自分の番ごとに1枚だけ」にあまごいでつけたカードを数えるか） | カードを動かす前に `AttachEnergy` を `UnsupportedError`（`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`）で拒否（ほかの確認がすべて通ったあと）。状態・乱数・ログは変わらない。次の自分の番には通常の操作ができる。通常の操作でつけたあとのあまごいは使える（どちらの読み方でも同じ。R12）。自然な対戦 80 局で 17 回止めた。test_rain_dance_v0_6.py `test_attaching_from_hand_after_rain_dance_is_not_decided`・test_unresolved_boundaries_v0_4e.py `AttachAfterPowerAttachBoundaryTest`（[rain-dance-v0.6.md](rain-dance-v0.6.md) の R13） |
| 「とうめい」がはたらいているゴーストに「ダメージ → ワザを使う側のコイン → 相手を特殊状態にする」ワザを使い、ダメージの要素の「とうめい」が「おもて」になったあと、そのワザのコイン（受けないポケモンへの効果だけを決める）を投げるか（v0.9） | ダメージの要素の最終ダメージが 0 より大きい（「とうめい」のコインを投げうる）とき、ワザの宣言・こんらんのコインの前に `UseAttack` を `UnsupportedError`（`UNRESOLVED_EVADED_EFFECT_COIN`）で拒否。状態も乱数も変わらない。最終ダメージが 0 なら止めない。自然な対戦 80 局で 43 回止めた。test_transparency_v0_9.py `EvadedEffectCoinTest`・`CoinIndependenceTest`・test_unresolved_boundaries_v0_4e.py `EvadedEffectCoinBoundaryTest`（[transparency-v0.9.md](transparency-v0.9.md) の T19b） |
| ゴースの「エナジーへんかん」で、トラッシュにエネルギーカードがあるのに 0 枚を選べるか（v0.9。「最大2枚」が 0 枚を含むか） | 決定で 0 枚を選ぶと `ResolveDecision` を `UnsupportedError`（`UNRESOLVED_RECOVER_ZERO_ENERGY`）で拒否。決定は待ったまま（1 枚以上を選び直せる）。test_haunter_line_v0_9.py `test_zero_cards_is_unresolved`・test_unresolved_boundaries_v0_4e.py `RecoverZeroEnergyBoundaryTest`（[haunter-line-v0.9.md](haunter-line-v0.9.md) の H4） |
| 1 つのワザで、複数の「とうめい」のポケモンがダメージや効果を受けるときのコインの順番（v0.9） | 対応カードにベンチ・複数のポケモンにダメージや効果を与えるワザがないので起こらない（決めていない。そのワザを加えるときに、コインの前に止める処理を加える。[transparency-v0.9.md](transparency-v0.9.md) の T27） |
| カイリキーがワザのダメージできぜつし、ワザを使ったポケモンが「はんげき」のダメージできぜつする（「はんげき」がなければきぜつしない）とき、2 匹が「同時に「きぜつ」した」ことになるか（v0.10。p.324 の「1つのワザや特殊能力などによって引き起こされることがら」に、ワザがはたらかせた特殊能力のダメージが含まれるか） | ワザの宣言・こんらんのコインの前に `UseAttack` を `UnsupportedError`（`UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT`）で拒否（コインのどの結果でもその場合になりうるとき）。状態・乱数・ログは変わらない。勝者を推測で決めない。自然な対戦 80 局で 1 回、ストレス実行 400 局で 21 回起こった。test_counterattack_v0_10.py `test_both_knocked_out_by_counter_is_unresolved`・`CoinIndependenceTest`・test_unresolved_boundaries_v0_4e.py `CounterattackDoubleKnockoutBoundaryTest`（[counterattack-v0.10.md](counterattack-v0.10.md) の C18） |
| 1 つのワザで、2 つ以上の「はんげき」がはたらくときに与える順番（v0.10） | 対応カードに、相手の複数のポケモンにダメージを与えるワザがないので起こらない（決めていない。起こったらエンジンの不具合として `RuntimeError`。そのワザを加えるときに、宣言の前に止める処理を加える。[counterattack-v0.10.md](counterattack-v0.10.md) の C34・C35） |
| サカキのカイリキーの「こんじょう」を使えるポケモンが、ワザのダメージで HP 以上になり、同じワザでそのポケモンに効果（特殊状態・入れ替え）を与えるとき、「おもて」で「きぜつ」しなかったポケモンがその効果を受けるか（v0.11。こんじょうはワザのあとのきぜつの判定で使う（p.309）が、HP 以上になったポケモンにはあとの効果を与えない（v0.4d。p.89）） | ワザの宣言・こんらんのコインの前に `UseAttack` を `UnsupportedError`（`UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT`）で拒否（ダメージの候補のどれかで HP 以上になりうるとき。状態・乱数・ログは変わらない）。使えない（ねむり・マヒ・こんらん・かがくへんかガス）・HP 以上にならないなら止めない。test_guts_v0_11.py `G37Test`・test_unresolved_boundaries_v0_4e.py `KoPreventionAttackEffectTest`（[guts-v0.11.md](guts-v0.11.md) の G37・G30） |
| 同じきぜつの判定で、こんじょう（などきぜつするときに使える特殊能力）を使えるポケモンが 2 匹以上いるときの宣言の順番（v0.11） | 対応カードに、相手の複数のポケモンにダメージを与えるワザがないので起こらない（決めていない。起こったらエンジンの不具合として `RuntimeError`。そのワザ・効果（きあいのハチマキなど）を加えるときに、宣言の前に止める処理を加える。[guts-v0.11.md](guts-v0.11.md) の G40・G16） |
| R団のファイヤーがワザのダメージで、ワザを使ったポケモンが「ほのおのかべ」のダメージで、そろってきぜつする（「ほのおのかべ」がなければきぜつしない）とき、2 匹が「同時に「きぜつ」した」ことになるか（v0.12。p.324 の「1つのワザや特殊能力などによって引き起こされることがら」に、前の番のワザが与えた効果のダメージが含まれるか。v0.10 の C18 と同じ問い） | ワザの宣言・こんらんのコインの前に `UseAttack` を `UnsupportedError`（`UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`）で拒否（同じコインの結果でいっしょに起こるダメージの組のどれかでその場合になりうるとき。「ほのおのかべ」のダメージで、ワザを使ったポケモンの「はんげき」が与える 10 も数える）。状態・乱数・ログは変わらない。勝者を推測で決めない。「こんじょう」で解決したことにしない。自然な対戦 100 局で 1 回、ストレス実行 400 局で 10 回起こった。test_rocket_moltres_v0_12.py `test_hurricane_punch_is_stopped`・`CoinIndependenceTest`・test_unresolved_boundaries_v0_4e.py `RetaliationDoubleKnockoutBoundaryTest`（[rocket-moltres-v0.12.md](rocket-moltres-v0.12.md) の W24） v0.13 で、わるいカメールがワザのダメージで、ワザを使ったポケモンが「こうらがえし」で返すダメージで、そろってきぜつしうる場合（S37）も同じ問いなので、同じコードで止める（新しいコードではない。返す量は組ごとに受けたダメージで計算する。[shell-attack-v0.13.md](shell-attack-v0.13.md)） |
| かがくへんかガスを持つポケモンと R団のファイヤーが同じきぜつの判定できぜつするとき、「ふしちょう」を使えるか（v0.12。ガスがきぜつの時点ではたらいているか、手札に加える時点で消えているか） | 対応カードでは起こらない（W24・`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT` が先に止める。決めていない。起こったらエンジンの不具合として `RuntimeError`。[phoenix-v0.12.md](phoenix-v0.12.md) の P19） |
| 同じきぜつで、きぜつしたときに使える特殊能力（「ふしちょう」）の候補が 2 つ以上あるときの順番（v0.12） | 対応カードでは起こらない（R団のファイヤーが 2 匹同時にきぜつする場合は先に止めている。決めていない。起こったらエンジンの不具合として `RuntimeError`。[phoenix-v0.12.md](phoenix-v0.12.md) の P32） |
| 「ダメージを受けない」状態（「かたまる」）のポケモンに、コインでダメージの量を決める要素だけのワザ（ドードーの「みだれづき」）を使うとき、無効になる要素のコインを投げるか（v0.4b） | ワザの宣言・こんらんのコインの前に `UseAttack` を `UnsupportedError`（`UNRESOLVED_PREVENTED_COIN_DAMAGE`）で拒否。状態も乱数も変わらない。自然な対戦 40 局で 13 回起こった。v0.4c のスピアーの「ダブルニードル」（同じ `CoinFlipDamage`）にも同じく当てはまる（v0.4c の自然な対戦 40 局で 5 回）。通常の相手には使える。test_harden_v0_4b.py `test_coin_damage_against_prevention_is_unresolved`・test_stage2_v0_4c.py `PreventedTargetTest`・test_effect_preflight_v0_3d.py `CoinIndependenceTest`（[persistent-damage-v0.4b.md](persistent-damage-v0.4b.md) 5 章） |
| 「わるいねぞう」（特殊能力によるダメージ）の 20 に弱点・抵抗力を計算するか（v0.17b。Z9） | 計算するかで結果が変わる場合（受けるポケモンの弱点・抵抗力が与えるポケモンのタイプ）だけ止める（コードのない問い `power_damage_weakness_resistance`。R団のカビゴンは無色で、無色の弱点・抵抗力を持つカードはないので起こらない）。test_rocket_snorlax_v0_17b.py `test_weakness_resistance_guard` |
| 「ダメージを与えた後、…」の効果（たおれこむ）で、そのダメージの要素がダメージを与えなかったときに効果を与えるか（v0.17b。Z23） | ワザの宣言の前に `UseAttack` を `UnsupportedError`（`UNRESOLVED_EFFECT_AFTER_NO_DAMAGE`）。test_rocket_snorlax_v0_17b.py `test_no_damage_stops_before_the_attack`、test_unresolved_boundaries_v0_4e.py `EffectAfterNoDamageBoundaryTest` |
| キョウのベトベトンの「だつりょくえき」が宣言する特殊能力か・処理する時点・ダメージを与えたポケモンがすでに HP 以上のとき・エネルギーカードがないとき・ほかの効果と重なるとき（v0.17c。DR1・DR6・DR8・DR13・DR18） | カードを未対応にしたまま（実装を延期。エンジンの止める処理はない）。[kogas-muk-event-design-v0.17c.md](kogas-muk-event-design-v0.17c.md) |

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

- バタフリー（PMCG2-007。ふきとばし・メガドレイン）。写しにも入れていない（[architecture-v0.4c.md](architecture-v0.4c.md) 14 章に v0.4d の準備）（v0.4d 注: v0.4d で対応した。[v0.4d の章](#v04d-で加えたもの相手の強制交代与えたダメージによる回復バタフリー)）
- 退化、ベイビィポケモン、進化を助ける・妨げるトレーナーとポケモンパワー（フシギバナなど）

### 原典未確認・未解決

- 2 進化で新しく決められなくなった事項はない。v0.4b までの未解決（`UNRESOLVED_PREVENTED_COIN_DAMAGE`・`UNRESOLVED_EVOLUTION_HP`・`UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS`・`UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED`・`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`・`UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`・`UNRESOLVED_REPARALYSIS_RECOVERY_TURN`・切り直しの補償・きずぐすり・ポケモンいれかえ・特殊などく・サドン・デスの延長戦）は変えていない。`UNRESOLVED_PREVENTED_COIN_DAMAGE` はダブルニードルにも当てはまる。
- 実装上の仮定: 場のポケモンの番号は 2 進化しても変えない。1 進化した番は状態に持たず、不変条件はログ `evolve` と照らす（盤面を直接作ったテストでは、作った重なりのログがないので状態だけの必要条件まで）。段階の不一致を `EVOLUTION_STAGE_MISMATCH` にした。
- kyuura に、2 進化に固有の記録（3 枚の構成・同じ番の 1 進化 → 2 進化）と、ダブルニードルの印刷の文面と最新の説明を区別した記録がない（[data-provenance.md](data-provenance.md)・[stage2-evolution-v0.4c.md](stage2-evolution-v0.4c.md) 5 章）。

## v0.4d で加えたもの（相手の強制交代・与えたダメージによる回復・バタフリー）

対応したカードは、バタフリー（PMCG2-007。トランセルから進化する 2 進化。p.19）です。ワザの途中で相手プレイヤーの決定（`forced_switch`）を待ち、答えのあとで同じワザの続きを処理する（v0.2a のワザの途中の決定を、相手が決定する形で初めて製品のカードで使った）ことと、ワザのダメージの要素の結果（`DamageResult`）を後の要素に渡すことを加えました（コマンド・段階・状態の項目・書き出しの形式は増やしていない）。原典照合・裁定の分類・コード・テストの対応は [forced-switch-v0.4d.md](forced-switch-v0.4d.md)（ふきとばし）、[damage-drain-v0.4d.md](damage-drain-v0.4d.md)（メガドレイン）、[butterfree-v0.4d.md](butterfree-v0.4d.md)（カード）、設計は [architecture-v0.4d.md](architecture-v0.4d.md) にあります。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| バタフリーの登録（ふきとばし `DamageAndForceSwitch`・メガドレイン `DamageAndDrain`。照合した印刷の文面・最新の説明・出典 p.19）。2 つのワザがどちらも登録されているときだけ対応 | p.19 | test_butterfree_v0_4d.py `ButterfreeCardTest`、test_effects.py |
| キャタピー → トランセル → バタフリー（v0.4c の 2 進化の処理のまま）。同じ番の再進化・たね → 2 進化・最初の番は拒否。3 枚の重なり・受け継ぐもの・消えるもの・きぜつで 3 枚とサイド 1 枚 | p.310、p.313、p.319、p.323 | `ButterfreeEvolutionTest`・`ButterfreeKnockOutTest` |
| ふきとばし: 20 → 相手の決定（決定するのは相手、番のプレイヤーは変えない、選べるものは相手のベンチのポケモンの番号）→ 入れ替え → ワザのあとの処理（1 回だけ） | p.19、p.89、p.213、p.309 | test_forced_switch_v0_4d.py `WhirlwindFlowTest` |
| 控え 0 匹（入れ替えない・決定なし）・1 匹（決定を出す）・2 匹以上（どれでも選べる） | p.19 | 同上 |
| 誤った答え（ワザを使ったプレイヤー・ない番号・相手のバトル場・自分のベンチ・古い番号・複数・重複・空・決定なし）と、決定を待つ間のほかの操作の拒否。状態・決定・乱数・ログを変えない | p.309 | `InvalidAnswerTest`、test_butterfree_games_v0_4d.py `RandomCommandsWithButterfreeTest` |
| 20 で相手がきぜつするなら入れ替えない（SUPPORTED）。サイド・交代・勝ち（控えなし・最後のサイド） | p.309、p.323、p.89、p.213 | `KnockOutTest` |
| 強制交代: 番号・ダメージ・エネルギー・ついているトレーナー（有効期限も）・重なり・場に出た番・進化した番は変わらない。特殊状態（4 種類と組み合わせ）・持続する効果は消える（理由 `forced_switch`）。にげるエネルギー・こんらんのコインはない。にげるの失敗の記録は付かない | p.311、p.322、p.325 | `InheritanceTest` |
| 「ダメージを受けない」相手・最終ダメージ 0 の相手も入れ替える | p.321 | `test_persistent_effect_is_removed`・`test_zero_damage_still_switches` |
| `DamageResult`: 受けたポケモン・防いだか・最終ダメージ（防いだら None）・きぜつするか。ログ・ダメージの値は v0.4c と同じ | p.319、p.321 | test_damage_drain_v0_4d.py `DamageResultTest` |
| メガドレイン: 与えた最終ダメージ（弱点・抵抗力・プラスパワー・ディフェンダーのあと。HP で上限を付けない）の半分を 10 単位に切り上げ、バタフリーから、のっている数までとりのぞく。与えなかった（0・防いだ）ら回復しない | p.19、p.319、p.320、p.321 | `MegaDrainTest` |
| こんらん状態のバタフリー: 「おもて」ならワザを処理、「うら」なら入れ替え・ダメージ・回復なし（自分に 20） | p.309 | `ConfusedButterfreeTest`・`ConfusedMegaDrainTest` |
| 不変条件: ワザの決定の共通の確認（番のプレイヤー・バトル場のポケモン・カード id・今の番のワザのログ）と、ふきとばしの決定の形（`decision_problems`）。持続する効果のログとの対応に `forced_switch` | — | `PendingDecisionStateTest.test_invariants_reject_broken_decisions` |
| 決定を待つ状態の clone・deepcopy・pickle（写しで同じ答え → 同じ結果）。書き出しは形式 8 のまま（形式 1 は `ValueError`） | — | `PendingDecisionStateTest`・`ButterfreeCopyTest` |
| 正式な対戦開始から 40 局: バタフリーへの進化 72、ふきとばし 133（相手の選択 82、控えなし 11、きぜつ 38、特殊状態の解除 4、持続する効果の解除 6）、メガドレイン 39（回復 32、0 個 7）、バタフリーのきぜつ 20（どれも 3 枚） | — | test_butterfree_games_v0_4d.py |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 「ダメージを受けない」状態の相手へのメガドレイン（回復しない） | 自然な対戦 40 局では起こらなかった。盤面を直接作ったテストで確かめた（`test_prevented_damage_no_heal`） |
| 最終ダメージ 0 のメガドレイン（抵抗力 草 −30 とディフェンダー） | 対応カードに草の抵抗力を持つものはない。テスト専用のカードで確かめた（`test_no_damage_dealt_no_heal`・`test_dealt_damage_table`） |
| こんらんで「にげる」に失敗したバタフリーのふきとばし（バタフリーの記録はそのまま、番の終わりに消える） | 盤面を直接作ったテストで確かめた（`test_retreat_failure_record_is_not_touched`） |

### 未実装

- ほかの「相手の強制交代」「与えたダメージによる回復」のワザを持つカード（同じ実装で登録できるかは、カードごとに照合してから）
- 控えポケモンへのダメージ（p.320 の (2)・(4)）、退化、ベイビィポケモン、ポケモンパワー、特殊エネルギー、スタジアム

### 原典未確認・未解決

- v0.4d で新しく決められなくなった事項はない（[forced-switch-v0.4d.md](forced-switch-v0.4d.md) 9 章・[damage-drain-v0.4d.md](damage-drain-v0.4d.md) 8 章）。v0.4c までの未解決（`UNRESOLVED_PREVENTED_COIN_DAMAGE`・`UNRESOLVED_EVOLUTION_HP`・`UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS`・`UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED`・`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`・`UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`・`UNRESOLVED_REPARALYSIS_RECOVERY_TURN`・切り直しの補償・きずぐすりの 2 つ・`UNRESOLVED_SWITCH_WITHOUT_BENCH`・特殊などく・サドン・デスの延長戦）は変えていない。
- SUPPORTED（原典から導いた）: ふきとばしの 20 で相手がきぜつするなら入れ替えない、「ダメージを受けない」相手へのメガドレインは回復しない、メガドレインで相手がきぜつしても回復する。
- 実装上の仮定: 控えが 1 匹でもふきとばしの決定を出す。ベンチにもどったポケモンは選ばれた控えの位置に入る。ワザの効果による相手の入れ替えのログは `forced_switch`。
- kyuura に、バタフリーの 2 つのワザの印刷の文面と最新の説明を区別した記録と、ワザの効果による相手の入れ替え・「与えたダメージ」の記録がない（[data-provenance.md](data-provenance.md)・[butterfree-v0.4d.md](butterfree-v0.4d.md) 5 章）。

## v0.4e で確かめたこと（v0.4a〜v0.4d の総合監査）

カード・ルール・コマンド・段階・状態の項目・書き出しの形式（形式 1〜8 のまま）・ログの形・効果の登録表は変えていません。受け付ける操作・拒否のコード・状態・ログ・乱数は v0.4d（`4bd97bf`）と同じです（[compatibility-v0.4e.md](compatibility-v0.4e.md)）。監査の記録は [integration-audit-v0.4e.md](integration-audit-v0.4e.md)、設計の変更は [architecture-v0.4e.md](architecture-v0.4e.md) にあります。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| 進化（6 系統）× 特殊状態 8 通り × ついているカード（プラスパワー・ディフェンダー・両方・2 枚）× にげるの失敗の記録 × 持続する効果（作成可能）。ログの順番・乱数・書き出し | p.309、p.310、p.322、p.323 | test_combined_state_v0_4e.py `EvolutionCombinationTest` |
| にげる・ポケモンいれかえ・ふきとばし・きぜつ × 段階 × 特殊状態 8 通り × 持続する効果 × ついているカード × 控えの数。ディフェンダーはベンチでも有効期限にトラッシュ、持続する効果は二度消えない | p.311、p.313、p.322、p.323、p.325、p.19、p.213 | `ExitPathCombinationTest`・`ForcedSwitchCombinationTest`・`PoisonKnockOutWithPersistentEffectTest` |
| `DamageResult` の表（自分へ・抵抗力で 0・ディフェンダーで負・ちょうど HP・超える・防いだ）、メガドレインの表（与えたダメージ 11 通り × のっているダメージ 6 通り） | p.19、p.257、p.319〜p.321 | test_damage_result_audit_v0_4e.py |
| 段階ごとに決定する人が変わる 2 段階の決定（テスト専用の効果）、決定を待つ間の操作、すべての決定の種類での複製、v0.1 の答えのコマンド | p.309、p.312、p.313、p.323 | test_decision_integrity_v0_4e.py |
| 原典で決められない 11 件の止まる場合・隣の止まらない場合・拒否と HALTED の区別 | [unresolved-audit-v0.4e.md](unresolved-audit-v0.4e.md) | test_unresolved_boundaries_v0_4e.py |
| 不変条件（v0.4e で強めた）: トレーナーの決定の形（`TrainerEffect.decision_problems`）、サイド・交代の決定の再開先と選ぶ数、サイドを取る「だれが何枚」（きぜつから）、両方が出すときの順番、番の番号と番の始まりのログ。壊した状態の検出（12.7 の 10 種類）と、正しい状態を拒否しないこと | p.254、p.257、p.309、p.312、p.313、p.323〜p.325 | test_state_corruption_v0_4e.py |
| すべての対応カードの 48 局（正式な開始から）。ログだけから組み立て直した場のポケモンのダメージ・エネルギー・トラッシュ・サイドが状態と同じ。書き出しの形式 1〜8 は表せる状態だけを書き出し、形式 8 から後の項目を除いたものと同じ | — | test_combined_games_v0_4e.py（tests/log_audit.py） |
| 前の版（v0.4d）の参照データとの比較（4 局・約 480 手）、比べる道具のセルフテスト | — | test_cross_version_compatibility.py |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 前の版との大きな比較（8 組・50 局・11,377 手。食い違い 0） | ふだんのテストでは走らせない。`python3 tools/compare_engine_versions.py --base 4bd97bf`（[compatibility-v0.4e.md](compatibility-v0.4e.md)） |
| 大規模なストレス実行（800 局・受け付けた 108,543 手。内部の誤り 0） | ふだんのテストでは走らせない。`python3 tools/stress_engine.py`（小さな実行（8 局）はテストに含む） |
| 持続する効果を受けているポケモンの進化・にげる・ポケモンいれかえ、相手のマヒを強制交代で消す | 今の対応カードでは対戦で起こらない（作成可能）。盤面を直接作ったテストで確かめた（[interaction-matrix-v0.4e.md](interaction-matrix-v0.4e.md)） |

### 未実装

- v0.4d と同じ。ポケモンパワー（`UsePokemonPower` は `UNSUPPORTED_ACTION`）の基盤は先行して実装していない（[v0.5-readiness.md](v0.5-readiness.md)）

### 原典未確認・未解決

- 分類・処理の順番は変えていない（原典に新しい根拠がない）。11 件の `UNRESOLVED_…` は v0.4d と同じ範囲で止める（[unresolved-audit-v0.4e.md](unresolved-audit-v0.4e.md)）。
- 実装上の仮定（v0.4e で加えた不変条件の前提）: 同時のきぜつで両方がサイドを取る順番は確かめない（p.325 で番のプレイヤーが選べる。エンジンは番のプレイヤーからに正規化している）。
- 2000.02.14版のポケモンパワーの一般の規定は、原典で確かめていない（kyuura の記録も第4版の冊子だけ。[v0.5-readiness.md](v0.5-readiness.md) B1）。

## v0.5 で加えたもの（ポケモンパワーとフシギバナ）

ポケモンパワー（2000.02.14 版の用語では「特殊能力」）の基盤と、フシギバナの「エナジートランス」、進化元のフシギダネ・フシギソウを加えました（[アーキテクチャ](architecture-v0.5.md)）。一般の規定の照合は [pokemon-powers-v0.5.md](pokemon-powers-v0.5.md)、カードの照合は [venusaur-v0.5.md](venusaur-v0.5.md)・[bulbasaur-line-v0.5.md](bulbasaur-line-v0.5.md)、処理は [energy-transfer-v0.5.md](energy-transfer-v0.5.md)、確かめた結果は [v0.5-verification.md](v0.5-verification.md) です。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| ポケモンパワーの登録表（`PowerKey`・`PowerEntry`・`PowerEffect`）。登録して、データ（名前・印刷の文面・種類）と合うパワーだけを使える。パワーを持つカードは、すべてのパワーとワザが使えるときだけデッキに入る。ワザとは別の仕組み | CLAUDE.md、p.311・p.323 | test_pokemon_powers_v0_5.py `PowerRegistryTest`、test_cards.py |
| `UsePokemonPower(player, pokemon, power, energy, source, target)`。場のポケモンの番号で指す。v0.4e までの 2 つの項目の形も読める | p.311 | `CommandFormTest`、test_compat_v0_1.py |
| 使う前の共通の確認（番のプレイヤーの `Phase.MAIN`・自分の場のポケモン・いちばん上のカードの特殊能力・登録）。決定を待つ間・ワザのあと・相手の番は不可。拒否で状態・乱数・ログが変わらない | p.309〜p.311、p.323 | `CommonChecksTest`、test_state_integrity.py |
| 使っても番は終わらない。何度でも使え、回数を数えない。ベンチのポケモンも使える。エネルギーがなくても使える。複数のポケモンが使える | p.311、p.323 | `TurnContinuesTest`、test_venusaur_v0_5.py |
| 進化したら、進化前のカードの特殊能力は使えない（いちばん上のカードで決める） | p.310 | `test_pre_evolution_power_cannot_be_used` |
| エナジートランス: 自分の場のポケモンについている「草」の基本エネルギーカード 1 枚を、自分の場の別のポケモンにつけかえる（同じ uid）。フシギバナ自身を移動元・移動先にできる | p.16、p.323 | `EnergyTransMoveTest`・`EnergyTransRejectionTest` |
| このカードがねむり・マヒ・こんらんなら使えない（どくだけなら使える。移動元・移動先の特殊状態は関係しない） | p.16、p.322、p.323 | `SpecialConditionTest`（8 通り） |
| 手札からエネルギーをつけた回数を使わない。乱数を使わない | p.16 の解説、p.310 | `test_attaching_from_hand_is_a_separate_action`、`test_moves_the_same_card` |
| ワザ・にげるに必要なエネルギーは、そのときついているエネルギーで決まる（つけかえで変わる） | p.311、p.320 | `CostRecomputationTest` |
| 進化・にげる・ポケモンいれかえ・ふきとばし・きぜつとの関係 | p.310、p.311、p.313、p.323 | `EvolutionInterplayTest` |
| ログ `pokemon_power`（宣言）・`move_energy`（つけかえ）。ログの監査の組み立て直しに加え、壊したログ・状態を見つける | p.311 | test_bulbasaur_games_v0_5.py `LogAuditMoveEnergyTest` |
| フシギダネ（やどりぎのタネ: 与えたら 1 個とりのぞく）・フシギソウ（つるのむち・どくのこな: コインなしでどく状態）・フシギバナ（ソーラービーム）。照合した印刷の文面・最新の説明・出典 | p.13・p.14・p.16 | test_bulbasaur_line_v0_5.py、test_effects.py |
| 60 枚のデッキで、正式な開始から勝敗まで（48 局。エナジートランス 383 回・特殊状態で拒否 8 回・つけかえたエネルギーのトラッシュ 13 回など）。ログ・書き出しの監査 | — | test_bulbasaur_games_v0_5.py |
| 前の版（v0.4e の c1e13ec）との比較（8 組・50 局・11,377 手。食い違い 0） | — | [v0.5-verification.md](v0.5-verification.md)（`python3 tools/compare_engine_versions.py --base c1e13ec`） |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 大規模なストレス実行（フシギバナの組を含む） | ふだんのテストでは走らせない。`python3 tools/stress_engine.py`（小さな実行はテストに含む）。結果は [v0.5-verification.md](v0.5-verification.md) |
| エナジートランスの移動元・移動先の特殊状態 | ベンチのフシギバナから、特殊状態のバトル場のポケモンを移動元・移動先にする盤面は、盤面を直接作ったテストで確かめた |

### 未実装

- 1 回の使用で 2 枚以上をつけかえる（実装上の仮定で 1 回 1 枚。結果は同じ。[energy-transfer-v0.5.md](energy-transfer-v0.5.md) 3 章）
- 特殊エネルギー（レインボーエネルギーなど。p.16 の解説は「草エネルギーとしてあつかわれる」とする）
- ほかのポケモンパワー（上の「未実装」と [architecture-v0.5.md](architecture-v0.5.md) 9 章）

### 原典未確認・未解決

- 新しい `UNRESOLVED_…` は加えていない（v0.5 の対応カードの処理で、原典で決められない場合は見つからなかった）。11 件は v0.4e と同じ。
- 実装上の仮定: 1 回の使用で 1 枚、条件にしたがえない使用は宣言もなかったものとして拒否する（[pokemon-powers-v0.5.md](pokemon-powers-v0.5.md) 3 章）。
- SUPPORTED: どく状態のフシギバナが使えること、つけかえが手札からつけることではないこと、移すのがエネルギーカード（同じカード）であること（[venusaur-v0.5.md](venusaur-v0.5.md) 3 章）。

## v0.6 で加えたもの（あまごいとカメックス）

カメックスのポケモンパワー「あまごい」とワザ「ハイドロポンプ」、進化元のゼニガメ・カメールを加えました（[アーキテクチャ](architecture-v0.6.md)）。原典の照合と裁定（R1〜R15・H1〜H5）は [rain-dance-v0.6.md](rain-dance-v0.6.md)、確かめた結果は [v0.6-verification.md](v0.6-verification.md) です。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| あまごい: 自分の番の中で何度でも、自分の手札の「水」の基本エネルギーカード 1 枚（同じ uid）を、自分の場の「水」ポケモン（バトル場・ベンチ・カメックス自身）につける。番は終わらない。乱数を使わない | p.90、p.311、p.323（R1〜R8・R14） | test_rain_dance_v0_6.py `RainDanceAttachTest` |
| このカードがねむり・マヒ・こんらんなら使えない（どくなら使える。つける先の特殊状態は関係しない） | p.90、p.322、p.323（R9・R10） | `SpecialConditionTest` |
| 手札にないカード・相手のカード・水でないエネルギー・水でないポケモン・相手のポケモン・移動元の指定・決定を待つ間・相手の番・ワザのあとを拒否し、状態・乱数・ログを変えない | p.90、p.309〜p.311 | `RejectionTest` |
| 通常の操作（p.310）の回数を変えない。通常の操作でつけたあとも使える（R12。SUPPORTED）。あまごいでつけた枚数を別に数える（`energy_attached_by_powers_this_turn`。番の最初に 0。不変条件でログと対応） | p.90、p.307、p.310 | `NormalAttachmentTest`・`LogSerializationInvariantTest` |
| 手札から場へ動かす共通の処理（`zones.attach_energy_from_hand`。通常の操作と共通） | p.310 | `test_engine_never_moves_cards_on_an_unchecked_path`・すべての通常の操作のテスト |
| 進化した番のカメックスが使える（R15）。進化前のカメールは使えない。つけたエネルギーは進化・入れ替え・にげるでついたまま、きぜつでトラッシュ。ワザ・にげるに必要なエネルギーはそのときついているもので決まる | p.310、p.311、p.313、p.320、p.323 | `InteractionTest` |
| ハイドロポンプ: 必要な 3 個より多い「水」エネルギー 1 個につき 10 を 2 個まで、基本となるダメージに加える | p.90、p.88 の解説、p.320、p.321（H1〜H5） | test_squirtle_line_v0_6.py `HydroPumpTest` |
| ゼニガメ（あわ・からにこもる）・カメール（からにこもる・かみつく）と、ゼニガメ → カメール → カメックスの進化 | p.87、p.88、p.310 | test_squirtle_line_v0_6.py |
| ログ `power_attach_energy`。ログの監査で手札とあまごいを組み立て直し、壊したログ・状態を見つける（12 通り） | p.311 | test_blastoise_games_v0_6.py `LogAuditRainDanceTest` |
| 書き出しの形式 9（形式 1〜8 は、あまごいでつけた枚数が 0 でなければ `ValueError`） | — | `test_format_9`・書き出しの監査 |
| 60 枚のデッキで、正式な開始から勝敗まで（80 局。あまごい 187 回・ベンチのカメックスから 46 回・通常の操作のあとの使用 105 回・R13 で止めた 17 回・つけたエネルギーのトラッシュ 21 回など）。ログ・書き出しの監査 | — | test_blastoise_games_v0_6.py |
| 前の版（v0.5 の 0fbc3ab）との比較（8 組・50 局・11,377 手。食い違い 0） | — | [v0.6-verification.md](v0.6-verification.md)（`python3 tools/compare_engine_versions.py --base 0fbc3ab`） |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 大規模なストレス実行（カメックスの組を含む） | ふだんのテストでは走らせない。`python3 tools/stress_engine.py`（小さな実行はテストに含む）。結果は [v0.6-verification.md](v0.6-verification.md) |

### 未実装

- 1 回の使用で 2 枚以上をつける（実装上の仮定で 1 回 1 枚。結果は同じ。R3）
- 特殊エネルギー（レインボーエネルギーは手札では色を持たないので、あまごいでつけられない。p.298）
- ほかのポケモンパワー（上の「未実装」と [architecture-v0.6.md](architecture-v0.6.md) 12 章）

### 原典未確認・未解決

- 新しい `UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`（R13。上の「裁定が未解決」）。v0.5 までの 11 件は変えていない（12 件）。
- 実装上の仮定: 1 回の使用で 1 枚（R3）、必要なエネルギーがすべて同じタイプのワザだけを `ExtraEnergyDamage` に登録できる（H5）。
- SUPPORTED: バトル場・ベンチのどちらにもつけられる（R6）、どくのカメックスが使える・つける先の特殊状態は関係しない（R9・R10）、通常の操作のあとのあまごい（R12）、進化した番に使える（R15）、ハイドロポンプの数え方（H3）。

## v0.7 で加えたもの（ダメージスワップとフーディン）

フーディンのポケモンパワー「ダメージスワップ」とワザ「あやしいひかり」、進化元のケーシィ（ねんりき）・ユンゲラー（じこさいせい・ちょうねんりき）を加えました（[アーキテクチャ](architecture-v0.7.md)）。原典の照合と裁定は [damage-swap-v0.7.md](damage-swap-v0.7.md)（S1〜S25・A4）と [alakazam-line-v0.7.md](alakazam-line-v0.7.md)（K1〜K10）、確かめた結果は [v0.7-verification.md](v0.7-verification.md) です。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| ダメージスワップ: 自分の番の中（ワザの前）で何度でも、自分の場のポケモン（バトル場・ベンチ・フーディン自身）にのっているダメージカウンター 1 個を、自分の場の別のポケモンへのせかえる。バトル場・ベンチのどちらのフーディンでも使える。番は終わらない。乱数を使わない | p.153、p.308、p.311、p.323（S1〜S6・S10〜S15・S21） | test_damage_swap_v0_7.py `MoveTest` |
| のせるとダメージが HP と同じか大きくなる（きぜつする）ポケモンには移せない（状態を変える前に `WOULD_KNOCK_OUT`）。きぜつの処理は起こらない | p.153、p.319、p.320、p.323（S16〜S18・S24・A4） | `KnockOutProhibitionTest` |
| このカードがねむり・マヒ・こんらんなら使えない（選ばせるものより先に確かめる）。どくなら使える。移動元・移動先の特殊状態は関係しない | p.153、p.322、p.323（S7〜S9） | `RejectionTest`・`MoveTest` |
| 選ばせるものの不足・エネルギーの指定・相手のポケモン・ない番号・同じポケモン・カウンターのない移動元・相手の番・決定を待つ間を拒否し、状態・乱数・ログを変えない | p.153、p.309〜p.311 | `RejectionTest` |
| 移したカウンターはダメージではない（弱点・抵抗力・プラスパワー・ディフェンダー・「ダメージを受けない」状態を計算しない）。きずぐすり・じこさいせいでとりのぞける。進化・にげるでついていく。あまごいの枚数（R13）に数えない | p.310、p.311、p.320、p.323（S19・S20・S22・S23・S25） | `InteractionTest`・`test_moved_counters_are_not_damage` |
| ケーシィ（ねんりき）・ユンゲラー（じこさいせい・ちょうねんりき）・フーディン（あやしいひかり）と、ケーシィ → ユンゲラー → フーディンの進化。こんらんの超のポケモンは自分の弱点で 40 | p.149、p.151、p.153、p.310、p.322（K1〜K10） | test_alakazam_line_v0_7.py |
| じこさいせい: ワザを使うプレイヤーが、ついている「超」の基本エネルギーカードから 1 枚選んでトラッシュし（決定 `DISCARD_ENERGY`）、ダメージカウンターをすべてとりのぞく | p.151、p.309、p.320（K2〜K6） | `KadabraRecoverTest` |
| ログ `move_damage_counter`・`discard_energy`・`remove_all_damage_counters`。ログの監査でダメージカウンターの移動・じこさいせいを組み立て直し、壊したログ・状態を見つける（17 通り・きぜつするダメージ・じこさいせい 5 通り） | p.311 | test_alakazam_games_v0_7.py `LogAuditDamageSwapTest`・`LogAuditRecoverTest` |
| 書き出しは形式 9 のまま（新しい形式・状態の項目を加えていない） | — | `test_no_new_format`・書き出しの監査 |
| 60 枚のデッキで、正式な開始から勝敗まで（80 局。ダメージスワップ 1,000 回・ベンチのフーディンから 422 回・きぜつさせる移動の拒否 20 回・じこさいせい 37 回など）。ログ・書き出しの監査 | — | test_alakazam_games_v0_7.py |
| 前の版（v0.6 の 787fff9）との比較（8 組・50 局・11,377 手。食い違い 0） | — | [v0.7-verification.md](v0.7-verification.md)（`python3 tools/compare_engine_versions.py --base 787fff9`） |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 大規模なストレス実行（フーディンの組を含む） | ふだんのテストでは走らせない。`python3 tools/stress_engine.py --scenario alakazam --scenario alakazam_mixed`（小さな実行はテストに含む）。結果は [v0.7-verification.md](v0.7-verification.md) |
| じこさいせいで「超」エネルギーカードをトラッシュできないとき（K3。効果はなくなる） | ワザに必要なエネルギー（超超）は今の対応カードでは「超」の基本エネルギーでしか払えないので起こらない。起こったらエンジンの不具合として `RuntimeError`（`test_unreachable_case_stops_loudly`）。特殊エネルギーを加えるときに処理とテストを加える |

### 未実装

- 1 回の使用で 2 個以上を移す（実装上の仮定で 1 回 1 個。たどりつける状態は同じ。S3・S18）
- 退化・進化前のワザを使う効果（ダメージカウンターの扱いを原典で確かめる。[architecture-v0.7.md](architecture-v0.7.md) 13 章）
- ほかのポケモンパワー（常にはたらく・パワーを止める・回数の制限・割り込み型。上の「未実装」と [architecture-v0.7.md](architecture-v0.7.md) 13 章）

### 原典未確認・未解決

- 新しい `UNRESOLVED_…` のコードはない（ダメージスワップ・ケーシィの系統で原典で決められない場合は見つからなかった）。v0.6 までの 12 件は変えていない（R13 を含む）。
- 実装上の仮定: 1 回の使用で 1 個（S3）、途中の状態はない（S18）、不正な宣言は宣言もなかったものとして拒否（A4。v0.5 の P12）、じこさいせいはエネルギーが 1 枚でも決定を出す（K2）。
- SUPPORTED: フーディン自身が移動元（S5）、進化した番に使える（S6）、どくのフーディンが使える（S8）、移動元・移動先の特殊状態は関係しない（S9）、ベンチ → バトル場・ベンチ → ベンチ（S12）、ほかのパワーとの関係（S20）、じこさいせいでトラッシュするカードを選ぶのはワザを使うプレイヤー（K2）、カウンターがなくてもじこさいせいを使える（K4）。

## v0.8 で加えたもの（かがくへんかガスとベトベトン）

ベトベトン（PMCG3-007）のポケモンパワー「かがくへんかガス」とワザ「ヘドロこうげき」、進化元のロケット団のベトベター（PMCG4-004。どくガス・ねばりつく）を加えました（[アーキテクチャ](architecture-v0.8.md)）。原典の照合と裁定は [chemical-gas-v0.8.md](chemical-gas-v0.8.md)（G1〜G33・A4）と [grimer-line-v0.8.md](grimer-line-v0.8.md)（M1〜M9）、常にはたらく効果の求め方は [continuous-effects-v0.8.md](continuous-effects-v0.8.md)、確かめた結果は [v0.8-verification.md](v0.8-verification.md) です。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| かがくへんかガスは常にはたらいていて、使用を宣言しない（`UsePokemonPower` は `POWER_NOT_DECLARABLE`）。はたらいているかは、今の状態（場・いちばん上のカード・特殊状態）から求める（状態・書き出しの形式・ログのイベントを加えていない） | p.48、p.311、p.323（G1・G30） | test_chemical_gas_v0_8.py `test_the_gas_is_not_declared`・`GasEvaluationTest` |
| 場（バトル場・ベンチ）にいるかぎり、両方のプレイヤーの「かがくへんかガス」以外のすべての特殊能力（エナジートランス・あまごい・ダメージスワップ）を使えなくする（`POWER_SUPPRESSED`。宣言の前に拒否し、状態・乱数・ログを変えない）。手札・山札・トラッシュ・サイドでははたらかない | p.48、p.308、p.323（G2〜G5・G22〜G24・G31） | `SuppressionTest`（16 通りの盤面 × 3 つの特殊能力） |
| ベトベトンがねむり・マヒ・こんらんならはたらかない（どくならはたらく）。複数のベトベトンは 1 匹でもはたらいていれば消す。かがくへんかガスどうしは消し合わない | p.48、p.322、p.323（G9〜G12・G14・G20・G21） | `GasEvaluationTest`・`SuppressionTest` |
| 進化した番からはたらく。きぜつ・特殊状態からの回復（ねむりのコイン・マヒの回復・にげる・ポケモンいれかえ・ふきとばし・進化）のあと、同じ番でも答えが変わる。すませた特殊能力の結果は戻さない | p.310、p.311、p.322、p.323（G13・G15・G17・G19・G25〜G27） | `TransitionTest` |
| ワザ・トレーナー・手札からつける通常の操作・進化・にげる・番の終わりは止めない。R13（`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`）は変えていない | p.48、p.309、p.310（G8・G28・G29） | `OtherActionsTest`・`test_r13_is_unchanged` |
| ロケット団のベトベター（どくガス: ダメージなし・コインなしでどく。ねばりつく: コインで「おもて」なら 10 + 20 でマヒ）・ベトベトン（ヘドロこうげき: 30・コインでどく）と、ベトベター → ベトベトンの進化 | p.45、p.48、p.309、p.310、p.320、p.321（M1〜M9） | test_grimer_line_v0_8.py |
| ログの監査で、特殊能力の宣言のたびに、その時点の場（組み立て直したいちばん上のカード・ねむり・マヒ・こんらん）ではたらいているかがくへんかガスを求めて、消されている特殊能力の使用・かがくへんかガスの宣言がないことを確かめる | p.311 | test_muk_games_v0_8.py `LogAuditGasTest` |
| 保存（pickle・`copy.deepcopy`・`clone`・形式 9）と復元のあとも、同じ答え・同じ結果 | — | `SaveRestoreTest` |
| 60 枚のデッキで、正式な開始から勝敗まで（80 局。かがくへんかガスで拒否 310 回（エナジートランス 125・あまごい 32・ダメージスワップ 153）・自分のベトベトンで 206・相手のベトベトンで 145・はたらいたあとにまた使った 83 回・ベトベトンが場にいて力が消えているときに使った 24 回など）。ログ・書き出しの監査 | — | test_muk_games_v0_8.py |
| 前の版（v0.7 の 22cbe24）との比較（8 組・50 局・11,377 手。食い違い 0） | — | [v0.8-verification.md](v0.8-verification.md)（`python3 tools/compare_engine_versions.py --base 22cbe24`） |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 大規模なストレス実行（ベトベトンの組を含む） | ふだんのテストでは走らせない。`python3 tools/stress_engine.py --scenario muk --scenario muk_mixed`（小さな実行はテストに含む）。結果は [v0.8-verification.md](v0.8-verification.md) |
| 「その力も消える」（常にはたらく・自動的にはたらく特殊能力の効果を消す） | 規定は確かめた（G6・G7）が、v0.8 の対応カードに、かがくへんかガスのほかの常にはたらく・自動的にはたらく特殊能力がないので、処理する対象がない |

### 未実装

- ベトベトンの退化・手札に戻す効果（規定は G16・G18。いちばん上のカードで決めているので、加えればそのまま反映される）
- 期限のある「特殊能力を消す」効果（まきちらせ！ベトベトガス p.265・ドガースのふしぎなガス p.52）、自動的にはたらく特殊能力（[architecture-v0.8.md](architecture-v0.8.md) 14 章）
- 化石の秘密のベトベター（PMCG3-003。「ちいさくなる」の持続する効果が未実装。参照カード）

### 原典未確認・未解決

- 新しい `UNRESOLVED_…` のコードはない（かがくへんかガス・ベトベターの系統で原典で決められない場合は見つからなかった）。v0.7 までの 12 件は変えていない（R13 を含む）。
- 実装上の仮定: かがくへんかガスの宣言を拒否するコード（G30）、拒否のコードの順番（G32）、消された特殊能力の使用は宣言もなかったものとして拒否（v0.5 の P12 と同じ）。
- SUPPORTED: 「使えず」と「その力も消える」の書き分け（G6）、どくのベトベトンははたらく（G12）、特殊状態から回復したらまたはたらく（G13）、すませた特殊能力の結果は戻さない（G27）、ねばりつくの相手がきぜつしたらマヒにしない（M5）、「ダメージを受けない」相手にもねばりつくのコインを投げてマヒにする（M6）。

## v0.9 で加えたもの（とうめいとゴースト）

化石の秘密のゴースト（PMCG3-030）のポケモンパワー「とうめい」とワザ「あくむ」、進化元の化石の秘密のゴース（PMCG3-029。したでなめる・エナジーへんかん）を加えました（[アーキテクチャ](architecture-v0.9.md)）。原典の照合と裁定は [transparency-v0.9.md](transparency-v0.9.md)（T1〜T42・A4）と [haunter-line-v0.9.md](haunter-line-v0.9.md)（H1〜H13）、自動的にはたらく特殊能力の仕組みは [automatic-powers-v0.9.md](automatic-powers-v0.9.md)、確かめた結果は [v0.9-verification.md](v0.9-verification.md) です。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| 「とうめい」は自動的にはたらき、使用を宣言しない（`UsePokemonPower` は `POWER_NOT_DECLARABLE`。かがくへんかガスがはたらいていても同じコード） | p.159、p.323（T1・T37） | test_transparency_v0_9.py `test_cannot_be_declared`・`test_declaring_under_the_gas_is_not_declarable` |
| ワザによってダメージ（最終ダメージが 0 より大きい）や効果（どく・ねむり・マヒ・こんらん・入れ替え）を受けるとき、ゴースト側のプレイヤーがコインを投げ、「おもて」ならそのワザのダメージと効果をすべて受けない。1 つのワザにつき 1 匹 1 回で、結果をそのワザの残りの要素に使う | p.159、p.160、p.309、p.320（T2〜T6・T22・T23・T28・T32・T33） | `BasicTest`・`OneCoinPerAttackTest` |
| ワザのコインとの順番は要素の順番どおり（みだれづき・ねばりつくはワザのコインが先、でんげきの自分へのダメージのコインはあと）。最終ダメージ（弱点・抵抗力・プラスパワー・ディフェンダー）が決まってから評価し、0 なら投げない | p.309、p.321（T19・T20・T21・T39・T40） | `OneCoinPerAttackTest`・`DamageCalculationTest` |
| ねむり・マヒ・こんらんなら消える（コインを投げない）。どくでははたらく。回復したら、またはたらく。進化した直後からはたらく | p.160、p.310、p.323（T9〜T13・T16・T38） | `BasicTest` |
| かがくへんかガスがはたらいていれば消える（自分・相手のどちらのベトベトンでも。v0.8 の判定を使う）。ベトベトンがきぜつ・こんらんしたら、またはたらく | p.48、p.323（T14・T15。A4-3） | `ChemicalGasTest` |
| ワザは失敗にならない（エネルギーはついたまま・番は終わる）。ワザを使う側への要素は処理する。受けなかったら「ダメージを与えたら」の回復は起こらない。受けなかったダメージではきぜつしない | p.159、p.309、p.319、p.321（T17・T18・T31・T41。A4-2） | `AttackSucceedsTest`・`test_thundershock_power_coin_before_the_attackers_self_damage` |
| トレーナー・特殊能力・ポケモンチェックのどく・こんらんの 20 にははたらかない。「ふきとばし」で相手がベンチのゴーストを選んでバトル場に出すときは評価しない | p.159、p.321、p.323（T11・T23・T29・T30・T34・T35） | `NotAnAttackTest`・`test_whirlwind_choosing_a_bench_haunter_needs_no_coin` |
| ベンチ・自分のワザ・複数のポケモン・同じワザの中の記録（関数を直接呼ぶ。テスト専用の自分へのダメージの効果） | p.159（T7・T8・T24〜T26） | `DirectReceptionTest` |
| 化石の秘密のゴース（したでなめる: コインでマヒ。エナジーへんかん: トラッシュのエネルギーカードを最大 2 枚、ワザの途中の決定で選んで手札に加え、その後、自分に 10）・ゴースト（あくむ: 10 のあとコインなしでねむり）と、ゴース → ゴーストの進化 | p.158、p.160、p.309、p.310、p.320〜p.322（H1〜H13） | test_haunter_line_v0_9.py |
| 受け付けるか・拒否のコードがコインの結果で変わらない（相手がゴーストのとき。27 のワザ × こんらん × 6 つの状態 × かがくへんかガス、16 通りのコイン） | p.309 | `CoinIndependenceTest` |
| 処理の途中の内部の誤り（注入）・拒否で、渡した状態・乱数・ログは変わらない。保存（pickle・deepcopy・形式 9）と復元のあとも同じ結果（決定のあとでコインを投げ直さない） | — | `AtomicityTest`・`SaveRestoreTest` |
| ログの監査で、判定（`evade_check`）の前のコイン・判定のあとの処理・受けないと決まったポケモンが受けていないこと・はたらいている「とうめい」の判定のないダメージと効果・エナジーへんかんのトラッシュから手札、を確かめる。ログを 17 種類書きかえて、それぞれを見つける | p.159、p.160 | test_haunter_games_v0_9.py `LogAuditTransparencyTest` |
| 60 枚のデッキで、正式な開始から勝敗まで（80 局。ゴーストへの進化 161 回・判定 207 回（「おもて」97・「うら」110）・受けなかったダメージ 56 件（合計 940）・受けなかった効果 53 件・かがくへんかガスで消えていたゴーストへのワザ 91 回・特殊状態で消えていたゴーストへのワザ 15 回・T19b で止めた 43 回など）。ログ・書き出しの監査 | — | test_haunter_games_v0_9.py |
| 前の版（v0.8 の d057f57）との比較（8 組・50 局・11,377 手。食い違い 0） | — | [v0.9-verification.md](v0.9-verification.md)（`python3 tools/compare_engine_versions.py --base d057f57`） |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 大規模なストレス実行（ゴーストの組を含む） | ふだんのテストでは走らせない。`python3 tools/stress_engine.py --scenario haunter --scenario haunter_muk`（小さな実行はテストに含む）。結果は [v0.9-verification.md](v0.9-verification.md) |
| ベンチのゴースト・自分のワザで自分を対象にするワザ・複数のポケモンへのワザでの「とうめい」 | 規定は確かめた（T7・T8・T24〜T26）が、対応カードにそのワザがないので、自然な対戦では起こらない（ベンチでの判定 0 回）。関数を直接呼ぶテストとテスト専用の効果で確かめた |
| 自分への効果のワザ（かたまる・からにこもる・じこさいせい・回復）と「とうめい」 | 対応カードで「とうめい」を持つポケモンがそのワザを使わないので、評価していない（未到達。[automatic-powers-v0.9.md](automatic-powers-v0.9.md) 2.1） |

### 未実装

- 「とうめい」のほかの自動的にはたらく特殊能力（カイリキー［はんげき］など）、ベンチ・複数のポケモンにダメージや効果を与えるワザ、ワザでほかのポケモンにエネルギーをつける効果（T36）（[architecture-v0.9.md](architecture-v0.9.md) 14 章）
- 第1弾のゴースト（PMCG1-047。「ゆめくい」のワザの失敗が未実装。参照カード）

### 原典未確認・未解決

- 新しい `UNRESOLVED_…` のコードは 2 件（`UNRESOLVED_EVADED_EFFECT_COIN`・`UNRESOLVED_RECOVER_ZERO_ENERGY`）。v0.8 までの 12 件は変えていない（R13 を含む）。T27（複数の「とうめい」のポケモンのコインの順番）は起こらないので止める処理を加えていない。
- 実装上の仮定: 宣言を拒否するコード（T37）、ログの形（`evade_check`・`attack_evaded`・`recover_energy`）、ワザ 1 回の中だけの記録（`AttackUse.reception`）、エナジーへんかんを決定で選ぶこと（H10）。
- SUPPORTED: 1 つのワザにつき 1 回（T4）、「うら」のあとで投げ直さない（T6）、どくでははたらく（T12）、回復したらまたはたらく（T13）、ワザのコインとの順番（T19）、最終ダメージが決まってから評価（T20）、最終ダメージ 0 なら投げない（T21）、記録の結果をワザの残りに使う（T32）、ディフェンダーとの関係（T39）、ダメージの量のコインが先（T40）、「ダメージを与えたら」の回復は起こらない（T41）、トラッシュにエネルギーがなければ自分へのダメージだけ（H5）、自分へのダメージの計算（H7）。

## v0.10 で加えたもの（はんげきとカイリキー）

カイリキー（PMCG1-057）のポケモンパワー「はんげき」とワザ「ちきゅうなげ」、進化元のゴーリキー（PMCG1-055。からてチョップ・じごくぐるま）を加えました（ワンリキーは v0.1 から。[アーキテクチャ](architecture-v0.10.md)）。原典の照合と裁定は [counterattack-v0.10.md](counterattack-v0.10.md)（C1〜C43・A4）と [machamp-line-v0.10.md](machamp-line-v0.10.md)（M1〜M12）、ダメージを受けたあとに自動的にはたらく特殊能力の仕組みは [post-damage-powers-v0.10.md](post-damage-powers-v0.10.md)、確かめた結果は [v0.10-verification.md](v0.10-verification.md) です。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| 「はんげき」は自動的にはたらき、使用を宣言しない（`UsePokemonPower` は `POWER_NOT_DECLARABLE`） | p.192、p.323（C1） | test_counterattack_v0_10.py `test_cannot_be_declared` |
| 相手のワザのダメージ（最終ダメージが 0 より大きい）を受けたとき、ダメージを与えたポケモン（ワザを使ったポケモン）に、弱点・抵抗力に関係なく 10。受けたダメージの量・カイリキーのきぜつによらない。ワザごとに何度でも | p.192、p.203（C2・C3・C10〜C12・C17・C41・C42） | `BasicTest` |
| 自分のワザ・こんらんの 20・どく・ダメージスワップ・特殊能力のダメージ・0 ダメージ・ダメージのないワザでははたらかない。「はんげき」の 10 は特殊能力によるダメージで、ディフェンダーで減らず、別の「はんげき」をはたらかせない（連鎖しない） | p.138、p.245、p.319〜p.322（C4〜C8・C13・C14・C37・C40） | `SourceTest`・`test_defender_on_the_attacker_does_not_reduce` |
| ダメージを受けるとき、すでにねむり・マヒ・こんらんならはたらかない。どくでははたらく。同じワザの効果でダメージのあとに特殊状態になってもはたらく。回復したら、またはたらく | p.192、p.20（C19〜C23・C26） | `ConditionTest` |
| かがくへんかガスがはたらいていれば消える（自分・相手のどちらのベトベトンでも。v0.8 の判定を使う）。ベトベトンが場をはなれたら、またはたらく | p.48、p.323（C24・C25） | `GasTest` |
| 与えるのは、ワザのダメージの処理（自分へのダメージを含む）のあと、ダメージ以外の効果（ワザのコイン・特殊状態・入れ替え・回復）の前。「はんげき」できぜつしたワザを使ったポケモンの回復は処理せず、相手への入れ替えは処理する。自分へのダメージですでにきぜつしていれば与えない | p.89、p.309、p.320、p.321（C15・C16・C27〜C29） | `OrderTest` |
| きぜつ・サイド・交代・勝ち負けはワザのあと（v0.2f のまま）。カイリキーだけ・ワザを使ったポケモンだけ・1 つのワザによる同時のきぜつ（サドン・デスを含む）。「はんげき」のきぜつのサイドはカイリキーの持ち主が取る | p.311、p.323、p.324（C17・C30〜C33・C38。A4-1・A4-6） | `KnockOutTest` |
| ゴーリキー（からてチョップ: 50 − 自分のダメージカウンターの数 × 10 が基本となるダメージ、0 以下ならダメージを与えない。じごくぐるま: 60 のあと自分にも 20）・カイリキー（ちきゅうなげ 60）と、ワンリキー → ゴーリキー → カイリキーの進化 | p.189、p.190、p.192、p.310、p.319〜p.321（M1〜M12） | test_machamp_line_v0_10.py |
| 受け付けるか・拒否のコードがコインの結果で変わらない（相手の対戦ポケモンがカイリキーのとき。登録表のワザ × こんらん × カイリキーの 5 つの状態 × あと 10 で HP か、8 通りのコイン） | p.309 | `CoinIndependenceTest` |
| 処理の途中の内部の誤り（注入）・拒否で、渡した状態・乱数・ログは変わらない。保存（pickle・deepcopy・形式 9）と復元のあとも同じ結果（決定のあとで「はんげき」を二度与えない） | — | `AtomicityTest`・`SaveRestoreTest` |
| ワザの途中の決定（ふきとばし）を待つ間だけ、「はんげき」で HP 以上になったワザを使ったポケモンが場に残る（不変条件の例外は、決定の `context` とログで確かめる狭いもの） | p.309、p.89（C16・C30） | `InvariantTest` |
| ログの監査で、はたらいた「はんげき」がそのワザの中に 1 回あり、ダメージ以外の効果・きぜつより先にあること、はたらかないはずの「はんげき」がないこと、相手・量・ダメージ・きぜつの印・回復・ほかのきぜつを確かめる。ログを 18 種類書きかえて、それぞれを見つける | p.89、p.192 | test_machamp_games_v0_10.py `LogAuditCounterattackTest` |
| 60 枚のデッキで、正式な開始から勝敗まで（80 局。カイリキーへの進化 50 回・「はんげき」67 回（合計 670）・ワザを使ったポケモンをきぜつさせた 11 回・きぜつしたカイリキーの「はんげき」2 回・かがくへんかガスで消えていたカイリキーへのワザ 3 回・特殊状態で消えていたカイリキーへのワザ 1 回・C18 で止めた 1 回など）。ログ・書き出しの監査 | — | test_machamp_games_v0_10.py |
| 前の版（v0.9 の 995504e）との比較（8 組・50 局・11,377 手。食い違い 0） | — | [v0.10-verification.md](v0.10-verification.md)（`python3 tools/compare_engine_versions.py --base 995504e`） |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 大規模なストレス実行（カイリキーの組を含む） | ふだんのテストでは走らせない。`python3 tools/stress_engine.py --scenario machamp --scenario machamp_mixed`（小さな実行はテストに含む）。結果は [v0.10-verification.md](v0.10-verification.md) |
| ベンチのカイリキーの「はんげき」・「とうめい」で受けなかったダメージ・「ダメージを受けない」状態のカイリキー | 規定は確かめた（C9・C36）が、対応カードにベンチにダメージを与えるワザがなく、カイリキーは「とうめい」「かたまる」を持たないので、自然な対戦では起こらない（ベンチからの「はんげき」0 回）。関数を直接呼ぶテストで確かめた |
| 1 つのワザで 2 つ以上の「はんげき」 | 対応カードで起こらない（C34・C35）。起こったらエンジンの不具合として止めることを確かめた（`test_two_pending_counters_are_not_ordered`） |

### 未実装

- 「はんげき」のほかの「ダメージを受けたとき」にはたらく特殊能力（［ショックボム］・［わるいねぞう］・［どくのたいえき］）とワザ（「こうらがえし」・「クロスカウンター」）、きぜつを取り消す特殊能力（サカキのカイリキーの［こんじょう］。v0.11 で対応した）、ベンチ・複数のポケモンにダメージを与えるワザ（[architecture-v0.10.md](architecture-v0.10.md) 17 章）
- サカキのカイリキー（PMCG6-061。v0.10 では参照カード。v0.11 で対応した）

### 原典未確認・未解決

- 新しい `UNRESOLVED_…` のコードは 1 件（`UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT`。C18 (b)）。v0.9 までの 14 件は変えていない（R13・T19b・H4 を含む）。コードのない T27 も変えていない。C34・C35（複数の「はんげき」の順番）は起こらないので止める処理（コード）を加えていない。
- 実装上の仮定: 宣言を拒否するコード（C1）、ログの形（`counterattack`・`counterattack_skipped`・`drain_heal_skipped`）、ワザ 1 回の中だけの記録（`AttackUse.counterattacks`）、自分へのダメージですでにきぜつしている相手に与えない（C15。与えても結果は同じ）。
- SUPPORTED: 与える時点（C2・C27〜C29）、特殊能力によるダメージ（C13）、連鎖しない（C14）、与える相手がいないとき（C15）、「はんげき」できぜつしたあとの効果（C16）、どくでははたらく（C22）、回復したらまたはたらく（C26）、ディフェンダー・プラスパワー（C37）、からてチョップの 1 段階（M4）・ダメージカウンターを数える（M7）、じごくぐるまの自分へのダメージの計算（M9）。
- 『ポケモンカード ファンクラブ vol.3』の改訂文面（二次資料の情報）は、誌面を確かめられなかったので使っていない。


## v0.11 で加えたもの（こんじょうとサカキのカイリキー）

サカキのカイリキー（PMCG6-061）のポケモンパワー「こんじょう」とワザ「ハリケーンパンチ」、進化元のサカキのワンリキー（PMCG6-057。チョップ・いかりのスーパーパンチ）・サカキのゴーリキー（PMCG6-059。いちかばちか・じごくがため）を加えました（[アーキテクチャ](architecture-v0.11.md)）。原典の照合と裁定は [guts-v0.11.md](guts-v0.11.md)（G1〜G42・A4〜A6）と [giovanni-machamp-line-v0.11.md](giovanni-machamp-line-v0.11.md)（L1〜L14）、きぜつの判定ときぜつの処理のあいだの仕組みは [ko-prevention-v0.11.md](ko-prevention-v0.11.md)、確かめた結果は [v0.11-verification.md](v0.11-verification.md) です。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| 「こんじょう」は使用を宣言する特殊能力で、使うかは持ち主が決める（強制ではない）。決められたとき（相手のワザによるダメージで「きぜつ」するとき）にしか使えず、`UsePokemonPower` は `POWER_NOT_USABLE_NOW` | p.193、p.311、p.100（G1・G10・G41。A4） | test_guts_v0_11.py `RegistrationTest`・`UseTest` |
| 使うかの決定（`ko_prevention`。選ぶ数 0〜1。ワザを使われた側のプレイヤー）を、ワザの要素をすべて処理したあと、きぜつの処理（トラッシュ・サイド・交代・勝ち負け）の前に出す。決定の時点ではコインを投げていない。待つ間はほかの操作をできない。答えのあとは、同じきぜつの判定で 2 度決めない | p.309、p.311、p.323、p.324（G2・G12〜G14・G32・G42） | `OfferTest`・`DecisionTest` |
| 使うと答えたら宣言してコインを 1 枚（持ち主）。「おもて」なら「きぜつ」せず残り HP 10（ダメージ = HP − 10。ダメージは受けたまま）、「うら」・使わないならふつうにきぜつ | p.193、p.285、p.311、p.319（G11・G13・G15・G17〜G24） | `UseTest` |
| 相手のワザによるダメージ（最終ダメージが 0 より大きい）だけ。自分のワザ・こんらんの 20・どく・「はんげき」の 10・ダメージスワップでは使えない | p.193、p.320、p.321（G3〜G7） | `SourceTest` |
| ダメージを受けるとき、すでにねむり・マヒ・こんらんなら使えない。どくは関係しない。かがくへんかガスがはたらいていれば使えない（v0.8 の判定を使う）。場所（ベンチ）は見ない | p.193、p.48、p.323（G8・G25〜G31） | `ConditionAndGasTest` |
| 生き残ったらサイドは取られず、交代もない。最後のポケモン・最後のサイド。ワザを使ったポケモンも HP 以上なら、こんじょうのあとで同時にきぜつ。C18 は変えない | p.311、p.323、p.324（G33〜G39） | `KnockOutAndPrizeTest` |
| こんじょうを使えるポケモンにワザのダメージで HP 以上のダメージを与えうるうえ、同じワザで効果を与えるワザは、宣言の前に止める（G37）。ワザの実装が宣言する効果の種類と、実装の呼び出しが合う | p.89、p.309（G37） | `G37Test`・`KoPreventionAttackEffectTest` |
| サカキのワンリキー（チョップ・いかりのスーパーパンチ）・サカキのゴーリキー（いちかばちか・じごくがため）・サカキのカイリキー（ハリケーンパンチ）と、進化の系統 | p.189、p.191、p.193、p.310、p.320、p.321（L1〜L14） | test_giovanni_machamp_line_v0_11.py |
| 受け付けるか・拒否のコードがコインの結果で変わらない（v0.11 の 5 つのワザを加えた） | p.309 | `CoinIndependenceTest`（test_effect_preflight_v0_3d.py・test_counterattack_v0_10.py） |
| 決定を待つ状態の保存（pickle・deepcopy・clone）と再開で同じ結果。拒否・不正な答えで状態・乱数・ログは変わらない | — | `DecisionTest`・test_giovanni_games_v0_11.py `test_replay_and_save_restore_at_the_decision` |
| 決定を待つ間だけ、HP 以上のダメージのポケモン（決定の対象と、同じワザで HP 以上になったワザを使ったポケモン）が場に残る（不変条件の狭い例外）。決定の形・ログとの対応を不変条件で確かめる | p.309 | `_ko_prevention_awaiting`・`_ko_prevention_decision_problems`（test_guts_v0_11.py の各テストの `check_invariants`） |
| ログの監査で、こんじょうの決定の答え・宣言・コイン・結果・残り HP・きぜつ・サイドの対応を確かめる。ログを 14 種類書きかえて、それぞれを見つける | p.193、p.311 | test_giovanni_games_v0_11.py `LogAuditGutsTest` |
| 60 枚のデッキで、正式な開始から勝敗まで（100 局。サカキのカイリキーへの進化 79 回・こんじょうの決定 36 回（使う 20: 「おもて」12・「うら」8、使わない 16）・かがくへんかガスで使えずきぜつ 3 回・ハリケーンパンチ 105 回など）。ログ・書き出しの監査 | — | test_giovanni_games_v0_11.py |
| 前の版（v0.10 の 43ec8ba）との比較（8 組・50 局・11,377 手。食い違い 0） | — | [v0.11-verification.md](v0.11-verification.md)（`python3 tools/compare_engine_versions.py --base 43ec8ba`） |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 大規模なストレス実行（サカキのカイリキーの組を含む） | ふだんのテストでは走らせない。`python3 tools/stress_engine.py --scenario giovanni --scenario giovanni_mixed`（小さな実行はテストに含む）。結果は [v0.11-verification.md](v0.11-verification.md) |
| ベンチのサカキのカイリキーへの決定・特殊状態で使えずにきぜつ・どくのきぜつ | 規定は確かめた（G7・G8・G25〜G27）が、対応カードにベンチにダメージを与えるワザがないので、ベンチは自然な対戦では起こらない（0 回）。盤面を直接作ったテストと関数で確かめた。特殊状態・どくは 100 局の自然な対戦では 0 回で、ストレス実行では起こった（特殊状態 2 回・どく 10 回） |
| 同じきぜつの判定でこんじょうを使えるポケモンが 2 匹以上 | 対応カードで起こらない（G40）。起こったらエンジンの不具合として止める（`RuntimeError`） |

### 未実装

- こんじょうのほかのきぜつを防ぐ効果（きあいのハチマキ（ネオ。2000.02.14 版の範囲の外））・きぜつしたときに使える特殊能力（R団のファイヤーの［ふしちょう］）、ポケモンチェックのきぜつ・特殊能力のダメージによるきぜつで使える効果、ベンチ・複数のポケモンにダメージを与えるワザ（[architecture-v0.11.md](architecture-v0.11.md) 16 章）

### 原典未確認・未解決

- 新しい `UNRESOLVED_…` のコードは 1 件（`UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT`。G37）。コードのない G40（2 匹以上の順番）。v0.10 までの 15 件のコードと、コードのない T27・C34/C35 は変えていない（R13・T19b・H4・C18 を含む）。未解決の裁定は 19 件（コードのある 16 件）。
- 実装上の仮定: 決定の形（選べるものはそのポケモンの番号 1 つ・選ばない = 使わない・`context`）、ログの形（`ko_prevention_declined`・`ko_prevention_declared`・`ko_prevented`・`ko_prevention_failed`）、ワザ 1 回の中だけの記録（`AttackUse.ko_prevention_able`）、`UsePokemonPower` を拒否するコード（`POWER_NOT_USABLE_NOW`）。
- SUPPORTED: 宣言する特殊能力で任意（G1・G10）、使う時点（G2・G12・G32・G42）、「はんげき」のダメージは当たらない（G5）、場所（G8）、回数（G9・G24）、2 度決めない（G14）、コインを投げるプレイヤー（G15）、いちばん上のカードの HP（G20）、ダメージを受けたことは成立する（G22）、どくは使える（G28）、同時のきぜつ（G38）、いちかばちかの自分への 100 の計算（L8）・「うら」のときの「とうめい」「はんげき」（L9）・「ダメージを受けない」相手へのいちかばちか（L10）。
- 当時の公式の Q&A・訂正は見つけられなかった（[guts-v0.11.md](guts-v0.11.md) 1 章）。

## v0.12 で加えたもの（ふしちょう・ほのおのかべと R団のファイヤー）

R団のファイヤー（PMCG5-020）のポケモンパワー「ふしちょう」とワザ「ほのおのかべ」を加えました（[アーキテクチャ](architecture-v0.12.md)）。原典の照合と裁定は [phoenix-v0.12.md](phoenix-v0.12.md)（P1〜P35）と [rocket-moltres-v0.12.md](rocket-moltres-v0.12.md)（カードの照合・W1〜W30）、きぜつしたあとに使う特殊能力の仕組みは [post-knockout-powers-v0.12.md](post-knockout-powers-v0.12.md)、番をまたいではたらくワザの効果は [temporary-attack-effects-v0.12.md](temporary-attack-effects-v0.12.md)、確かめた結果は [v0.12-verification.md](v0.12-verification.md) です。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| 「ふしちょう」は使用を宣言する特殊能力で、使うかは持ち主が決める（任意）。このカードが「きぜつ」したときにしか使えず、場にいるときの `UsePokemonPower` は `POWER_NOT_USABLE_NOW` | p.82、p.311、p.323（P1〜P3） | test_phoenix_v0_12.py `RegistrationTest`・`OfferTest` |
| 使うかの決定（`post_knockout_power`。選ぶ数 0〜1。選べるものはトラッシュのそのカード）を、きぜつの処理（トラッシュ）・サイド・勝ち負けの判定のあと、対戦が続くときだけ、バトル場に出す前に出す（正規化した順番）。対戦が終わるなら決めさせない。答えのあとは同じきぜつで 2 度決めない | p.82、p.311、p.323〜p.325（P4・P12・P20・P21・P27〜P30） | `OfferTest`・`GameEndTest` |
| 使ったら、このカード（同じ uid）だけをトラッシュから手札に加え、相手に見せる。ついていたエネルギー・トレーナーはトラッシュに残る。相手はサイドを取る。手札にもどったカードはダメージ・特殊状態・持続する効果を持たず、持ち主の番にふつうにベンチに出せる | p.82、p.322、p.323（P22〜P26・P31） | `OfferTest` |
| きぜつの原因を問わない（相手のワザ・自分のワザ・相手の「はんげき」・ポケモンチェックのどく）。ダメージスワップではきぜつしない。場所の制限はない | p.82、p.153、p.323（P5〜P11） | `CauseTest` |
| ねむり・マヒ・こんらんのまま「きぜつ」するときは使えない（どくは関係しない）。かがくへんかガスがはたらいていれば使えない（v0.8 の判定を使う）。どちらもきぜつの処理（トラッシュ）の前に求める | p.82、p.48、p.322（P13〜P18） | `SpecialConditionTest`・`GasTest` |
| 「ほのおのかべ」: 相手に 40 のあと、自分に「次の相手の番」にはたらく持続する効果（`Retaliation`）。相手へのダメージを与えたかに関わらず与える。次の相手の番の終わりに消える。ベンチにもどる・きぜつで消え、復活しない | p.82、p.89、p.322（W1〜W10・W27・W28） | test_rocket_moltres_v0_12.py `EffectCreationTest`・`KnockOutTest` |
| 次の相手の番、相手のワザによるダメージ（最終ダメージ > 0）を受けたとき、ダメージを与えた相手の対戦ポケモンに 10。R団のファイヤーのワザによるダメージ（弱点・抵抗力・ディフェンダー・「とうめい」を計算する）。受けたカイリキーの「はんげき」がはたらき、連鎖しない。かがくへんかガス・特殊状態で止まらない。与えるのは相手のワザのダメージの処理のあと・ダメージ以外の効果の前 | p.82、p.89、p.321（W11〜W21） | `TriggerTest` |
| R団のファイヤーがそのダメージできぜつしても与える。ワザを使ったポケモンが自分へのダメージですでに HP 以上なら与えない。「ほのおのかべ」できぜつしたワザを使ったポケモンの回復は処理せず、相手への効果（ふきとばし）は処理する。「ほのおのかべ」のダメージで HP 以上になった番のプレイヤーのサカキのカイリキーは「こんじょう」を使える（テスト専用の効果で確かめる） | p.82、p.89、p.309（W22・W23・W26・W29） | `KnockOutTest` |
| 両方がきぜつしうる場合は、ワザの宣言の前に止める（W24） | p.324（W24） | `RetaliationDoubleKnockoutBoundaryTest`・`CoinIndependenceTest` |
| 受け付けるか・拒否のコードがコインの結果で変わらない（「ほのおのかべ」を加えた。効果がはたらく R団のファイヤーへの、対応カードのすべてのワザ） | p.309 | `CoinIndependenceTest`（test_effect_preflight_v0_3d.py・test_rocket_moltres_v0_12.py） |
| 決定を待つ状態・効果のある状態の保存（pickle・deepcopy・clone）と再開で同じ結果。拒否・不正な答えで状態・乱数・ログは変わらない。書き出しは形式 9（形式 1〜7 は効果があれば、形式 1 は決定があれば `ValueError`） | — | `AtomicityAndSaveTest`・`SaveRestoreAndInvariantTest`・test_moltres_games_v0_12.py `test_replay_and_save_restore_at_the_decision` |
| 不変条件: 「ふしちょう」の決定・候補（カードが持ち主のトラッシュにあり、直前のきぜつのカード、登録、ガス）、「ほのおのかべ」の効果（発生源・番・期限・置き場所・登録のワザと量） | — | `test_invariants_reject_a_broken_decision`・`test_invariants` |
| ログの監査で、「ふしちょう」の答え・時点・回収と、「ほのおのかべ」の効果・返すダメージ・期限を確かめる。ログを 16 種類書きかえて、それぞれを見つける | p.82、p.89 | test_moltres_games_v0_12.py `LogAuditMoltresTest` |
| 60 枚のデッキで、正式な開始から勝敗まで（100 局。R団のファイヤーのきぜつ 79 回: 決定 32（使う 21・使わない 11）・特殊状態で使えない 34・ガスで使えない 4・対戦の終わりで決めさせない 9。手札にもどしたカードを再び場に出した 19 回。ほのおのかべ 199 回・効果 198（期限で消えた 170・きぜつで消えた 2・対戦の終わりに残った 26）・はたらいた 27・ダメージ 17 件（合計 220）・「とうめい」で受けなかった 10・きぜつさせた 6 など）。ログ・書き出しの監査 | — | test_moltres_games_v0_12.py |
| 前の版（v0.11 の 8bd1e5b）との比較（8 組・50 局・11,377 手。食い違い 0） | — | [v0.12-verification.md](v0.12-verification.md)（`python3 tools/compare_engine_versions.py --base 8bd1e5b`） |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 大規模なストレス実行（R団のファイヤーの組を含む） | ふだんのテストでは走らせない。`python3 tools/stress_engine.py --scenario moltres --scenario moltres_mixed`（小さな実行はテストに含む）。結果は [v0.12-verification.md](v0.12-verification.md) |
| ベンチの R団のファイヤーのきぜつ・自分のワザの自分へのダメージによるきぜつ | 規定は確かめた（P6・P11）が、対応カードにベンチにダメージを与えるワザがなく、R団のファイヤーに自分へのダメージのワザはないので、自然な対戦では起こらない。関数とテスト専用の効果で確かめた |
| 「ほのおのかべ」の抵抗力・プラスパワー・番のプレイヤーの「こんじょう」 | 対応カードに炎の抵抗力を持つポケモンがない（テスト専用の記録で確かめた）。R団のファイヤーにプラスパワーがついている相手の番はない。番のプレイヤーの「こんじょう」は W24 が先に止める（テスト専用の効果で確かめた） |
| ガスの発生源もいっしょにきぜつ（P19）・「ふしちょう」の候補が 2 つ以上（P32）・1 つのワザで「はんげき」と「ほのおのかべ」が合わせて 2 つ以上 | 対応カードで起こらない。起こったらエンジンの不具合として止める（`RuntimeError`） |

### 未実装

- 「ふしちょう」のほかのきぜつしたときに使える特殊能力、「ほのおのかべ」のほかの相手の番ではたらくワザの効果（わるいカメールの「こうらがえし」など）、相手に与える持続する効果（すなかけ・からまるいと）、ベンチ・複数のポケモンにダメージを与えるワザ（[architecture-v0.12.md](architecture-v0.12.md) 16 章）

### 原典未確認・未解決

- 新しい `UNRESOLVED_…` のコードは 1 件（`UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`。W24）。コードのない P19（ガスの発生源もいっしょにきぜつ）・P32（候補が 2 つ以上）。v0.11 までの 16 件のコードと、コードのない T27・C34/C35・G40 は変えていない（R13・T19b・H4・C18・G37 を含む）。未解決の裁定は 22 件（コードのある 17 件）。
- 原典で順番が決まらないが結果が変わらないので止めずに正規化したもの: 「ふしちょう」とサイド・バトル場に出す・勝ち負けの順番（P27・P28・P30。[post-knockout-powers-v0.12.md](post-knockout-powers-v0.12.md) 3 章）。未解決の件数には数えていない（v0.2f のサイドを取る順番と同じ扱い）。
- 実装上の仮定: 決定の形（選べるものはトラッシュのそのカード 1 枚・選ばない = 使わない・`context`）、ログの形（`post_knockout_power_declined`・`post_knockout_power_declared`・`return_to_hand`・`retaliation`・`retaliation_skipped`・`persistent_effect_skipped`）、候補の情報（持ち主・uid・カード id・パワーの位置）、持続する効果の値（`Retaliation`）、ワザ 1 回の中だけの記録（`AttackUse.retaliations`）。
- SUPPORTED: 宣言する特殊能力で任意（P1・P2）、原因を問わない（P6・P8・P9）、場所（P11）、回数（P12）、どくは使える（P16）、再び場に出せる（P26）、効果の終わる時点（W5）、ワザの説明によるダメージ（W12）、プラスパワー・ディフェンダー（W17）、「とうめい」（W19）、「はんげき」との関係（W20）、与える時点（W21）、きぜつしたワザを使ったポケモン（W23）、番のプレイヤーの「こんじょう」（W26）、相手にダメージを与えなくても効果を与える（W28）、「はんげき」で HP 以上なら効果を与えない（W29）。
- 当時の公式の Q&A・訂正は見つけられなかった（[phoenix-v0.12.md](phoenix-v0.12.md) 1 章）。

## v0.13 で加えたもの（こうらがえし・おうふくびんたとわるいカメール・第4弾のゼニガメ）

わるいカメール（PMCG4-021）のワザ「こうらがえし」「おうふくびんた」と、進化元の第4弾のゼニガメ（PMCG4-018）の「こうらアタック」を加えました（[アーキテクチャ](architecture-v0.13.md)）。原典の照合と裁定は [shell-attack-v0.13.md](shell-attack-v0.13.md)（S1〜S49）、カードの照合は [dark-wartortle-v0.13.md](dark-wartortle-v0.13.md)、量が受けたダメージで決まる効果の仕組みは [variable-retaliation-v0.13.md](variable-retaliation-v0.13.md)、確かめた結果は [v0.13-verification.md](v0.13-verification.md) です。

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| 第4弾のゼニガメ（こうらアタック 20）・わるいカメール（おうふくびんた・こうらがえし）を使える。「ゼニガメから進化」は名前で決まり、第4弾・第1弾のどちらのゼニガメからも進化できる（デッキでは合わせて 4 枚まで） | p.88、p.89、p.308、p.310（S43・S44） | test_shell_attack_v0_13.py `RegistrationTest` |
| おうふくびんた: コイン 2 枚の「おもて」の数 × 10（既存の `CoinFlipDamage`） | p.89（S42） | `EffectCreationTest.test_doubleslap` |
| こうらがえし: ダメージなし・コインなし。自分に、次の相手の番にはたらく持続する効果（`Retaliation`、`basis` `received_damage`）。次の相手の番の終わりに消える。ベンチにもどる・きぜつで消え、復活しない。特殊状態・かがくへんかガスで止まらない | p.89、p.322、p.323（S1〜S4・S26〜S33） | `EffectCreationTest`・`RemovalAndChainTest`・`InteractionTest` |
| 次の相手の番、相手のワザによるダメージ（最終ダメージ > 0）を受けたとき、受けたダメージ（最終ダメージ。HP で上限をつけない）と同じ量を基本となるダメージにして、ダメージを与えたポケモンに返す。元のワザの基本となるダメージではない。わるいカメールがきぜつしても返す | p.89、p.279、p.321（S5・S9〜S19） | `ReceivedDamageTest` |
| 返すダメージは「こうらがえし」のワザによるダメージ（弱点・抵抗力・ディフェンダー・「とうめい」を計算する。受けたカイリキーの「はんげき」がはたらき、連鎖しない） | p.89、p.160、p.192、p.321「8」（S20〜S25・S45） | `ReturnDamageTest`・`RemovalAndChainTest` |
| 返すのは相手のワザのダメージの処理のあと・ダメージ以外の効果の前。ワザを使ったポケモンが返すダメージで HP 以上なら、そのポケモン自身への効果（メガドレインの回復・ほのおのかべの効果）は処理せず、相手への効果（ふきとばし）は処理する。ダメージ以外の効果は返さない | p.89（スターブーメラン・ふきとばしの例）、p.309（S34・S35・S38・S40・S41） | `OrderTest`・`StarBoomerangMockTest`（テスト専用の模擬のワザ） |
| 両方がきぜつしうる場合は、ワザの宣言の前に止める（S37。W24 と同じコード） | p.324（S37） | `DoubleKnockOutTest`・`CoinIndependenceTest`（test_effect_preflight_v0_3d.py） |
| 「ほのおのかべ」（固定の量 10）は v0.12 と同じ値・ログ・書き出し | p.82 | test_rocket_moltres_v0_12.py・`test_fire_wall_and_shell_attack_in_turn`・v0.12 の自然な対戦の固定値 |
| 効果のある状態の保存（pickle・deepcopy・clone）と再開で同じ結果。拒否で状態・乱数・ログは変わらない。書き出しは形式 9（種類 `retaliation_received_damage`。形式 1〜7 は効果があれば `ValueError`） | — | `SaveRestoreAndInvariantTest`・`AtomicityTest`・test_dark_wartortle_games_v0_13.py |
| 不変条件: 効果の決め方・ワザの位置・量が登録（`retaliation_terms`）と合う | — | `test_invariants` |
| ログの監査で、受けたダメージ・基本となるダメージ・効果の種類を確かめる。ログを 16 種類書きかえて、それぞれを見つける | p.89、p.321 | test_dark_wartortle_games_v0_13.py `LogAuditShellAttackTest` |
| 60 枚のデッキで、正式な開始から勝敗まで（100 局。99 局は勝敗が決まり、1 局は対戦準備の既存の未解決の裁定で止まった）。わるいカメールへの進化 202、おうふくびんた 334、こうらがえし 409、効果がはたらいた 151（返したダメージ 143・「とうめい」で受けなかった 8。受けたダメージの合計 2480・返したダメージの合計 2580）、S37 で止めたワザ 34 | — | test_dark_wartortle_games_v0_13.py |
| 前の版（v0.12 の b8054af）との比較（8 組・50 局・11,377 手。食い違い 0）。R団のファイヤーの自然な対戦 100 局・12,266 手を v0.12 と v0.13 で再生して、手ごとの状態（形式 9）・乱数が同じ | — | [v0.13-verification.md](v0.13-verification.md) |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| 大規模なストレス実行（わるいカメールの組を含む） | ふだんのテストでは走らせない。`python3 tools/stress_engine.py --scenario wartortle --scenario wartortle_mixed`。結果は [v0.13-verification.md](v0.13-verification.md) |
| 受ける側の抵抗力（S12）・返すダメージの受ける側の抵抗力（S22） | 対応カードに、わるいカメールの抵抗力・水の抵抗力を持つポケモンがない（テスト専用の記録で確かめた） |
| 番のプレイヤーの「こんじょう」（S46） | ハリケーンパンチは S37 で必ず止まるので、自然な対戦では起こらない（テスト専用の効果で確かめた） |
| 進化・にげる・ポケモンいれかえで効果が消える（S28）・手札や山札にもどる（S30） | 効果を持つ間に持ち主の番は来ないので起こらない。共通の関数を直接呼んで確かめた |
| 1 つのワザで 2 回以上ダメージを受ける（S7）・連鎖（S45） | 対応カード・番の進み方で起こらない。起こったらエンジンの不具合として止める（`RuntimeError`。テスト専用の効果・壊した盤面で確かめた） |

### 未実装

- わるいカメックス、カスミのヒトデマン（スターブーメラン。テスト専用の模擬のワザで順番だけを確かめた）、R団のエビワラー（クロスカウンター）、ほかの相手の番ではたらくワザの効果、相手に与える持続する効果（すなかけ・からまるいと）、ベンチ・複数のポケモンにダメージを与えるワザ（[architecture-v0.13.md](architecture-v0.13.md) 16 章）

### 原典未確認・未解決

- 新しい未解決の裁定・`UNRESOLVED_…` のコードはない。S37 は W24（`UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`）と、S7 は C34/C35 と同じ問いとして扱った。未解決の裁定は 22 件（コードのある 17 件）のまま。
- 実装上の仮定: 効果の決め方の値（`basis`）・種類の名前（`retaliation_received_damage`）、受けたダメージをワザ 1 回の中の値にすること（`PendingRetaliation.received`）、ログの形（`retaliation` の `basis`・`received_damage`）、期限とついているトレーナーのトラッシュの前後（S33）。
- SUPPORTED: 受けたダメージに抵抗力・プラスパワー・ディフェンダーを含む（S12〜S14）、返すダメージの抵抗力・ディフェンダー・「とうめい」・「はんげき」（S22〜S25）、返すダメージできぜつしたワザを使ったポケモンへの効果の一般化（S35）・相手への効果（S40）、番のプレイヤーの「こんじょう」（S46）、特殊状態のわるいカメールも返す（S47）。
- 当時の公式の Q&A・訂正は見つけられなかった（[shell-attack-v0.13.md](shell-attack-v0.13.md) 9 章）。

## v0.14 で確かめたこと（汎用のイベント・効果の解決の試作）

v0.14 は、本番のエンジン（`kyuura_engine/`。版 0.13.0）を変えずに、カード効果ごとの専用の処理を汎用のイベント・効果の解決の仕組みに移すのが適切かを、本番の外（`experiments/event_kernel/`）の動くプロトタイプで確かめた版です（[現行の分析](event-architecture-audit-v0.14.md)、[設計案の比較](event-architecture-options-v0.14.md)、[イベントモデル](event-model-v0.14.md)、[検証](event-prototype-verification-v0.14.md)、[移行計画](event-migration-plan-v0.14.md)）。対応するカード・ルール・裁定・未解決の事項は v0.13 と同じです。

### 確かめたこと

| 項目 | 結果 | テスト・道具 |
|---|---|---|
| プロトタイプ（ワザ・番の終わり・きぜつのあとの決定を処理）と v0.13 の、1 歩ごとの状態（形式 9 の全体）・乱数・拒否のコードの比較 | 食い違い 0（対戦のテストの方針 23 × 100 seed を 2 つの先読みで、ストレス実行 26 組、交互の状態） | tests/test_event_kernel_games_v0_14.py・`tools/event_kernel_compare.py` |
| とうめい・はんげき・こんじょう・ふしちょう・こうらがえし・ほのおのかべ・かたまる・かがくへんかガス（特殊状態・発生源・ダメージの分類を含む） | v0.13 と同じ。共通の仕組み（窓・枠・対応表）が候補・順番を決めたことを解決の記録で確かめた | tests/test_event_kernel_v0_14.py |
| 原典で決められない場合（7 つのコード） | 共通の先読みが、v0.13 の止める関数を使わずに同じコードで止めた | `UnresolvedTest` |
| 本番の既存のテスト | 本番を変えていないので、そのまま通る（v0.14 のテストと合わせて 1,731 件。Python 3.11・3.12・3.13） | `python3 -m unittest` |

### 未実装（プロトタイプ）

- ベンチへのダメージ・複数のポケモンへのダメージ・窓の中の決定、トレーナー・宣言して使う特殊能力などほかのコマンド（v0.13 のエンジンに渡す）。
- 本番への組み込み（v0.15 以降。移行計画の結論は PARTIAL）。

## v0.15 で変えたこと（解決の基盤の本番への統合）

v0.15 は、v0.14 のプロトタイプを本番の内部の部品（`kyuura_engine/resolution/`）にし、ワザ・番の終わり・きぜつのあとの決定の解決を、標準でこの基盤（経路 `KERNEL`）で処理するようにした版です（版 0.15.0）。対応するカード・ルール・裁定・未解決の事項（エンジンが止める `UNRESOLVED_…` 17 件・未解決の裁定 22 件）・書き出しの形式 9 は v0.13 と同じです（[依存の整理](integration-dependencies-v0.15a.md)、[統合](kernel-integration-v0.15b.md)、[先読み](preflight-optimization-v0.15c.md)、[検証と切り替え](event-integration-verification-v0.15d.md)）。

| 項目 | 状況 | 文書・テスト |
|---|---|---|
| 公開の `apply_command(state, command)` | 呼び方・約束は同じ。標準の経路は `KERNEL`（v0.15d から）。経路を選ぶ内部の入口は `engine.apply_command_via` | tests/test_kernel_integration_v0_15.py |
| 経路 `KERNEL` が受け持つコマンド | ワザ（実装の型が要素の並びの対応表にあるもの）・番の終わり・再開先が `attack`・`knock_out`・`post_knockout`・`take_prize`・`promote_active` の決定への答え。ほかは v0.13 の処理 | [統合](kernel-integration-v0.15b.md) 3 章 |
| v0.13 の経路（`LEGACY`） | 残している（比べる基準。v0.16 で外す候補） | [統合](kernel-integration-v0.15b.md) 4 章 |
| 原典で決められない場合 | 止める条件・コード・理由の文は v0.13 と同じ（理由の文を `effects` の共通の関数にした） | [統合](kernel-integration-v0.15b.md) 5 章 |
| 宣言の前の先読み | 実際の処理を先に行い、試していない結果だけを試す（`derived`）。決定のすべての答えを試す。上限 4,096 | [先読み](preflight-optimization-v0.15c.md) |
| 固定した v0.13 との比較 | 2,560 対戦・350,533 歩を別のプロセスで比べ、経路 `LEGACY`・`KERNEL`（3 つの先読み）のどれも食い違い 0（受け付けたか・例外の種類とコードと理由の文・形式 9 の全体・保存と復元） | [検証と切り替え](event-integration-verification-v0.15d.md) 3 章 |
| 解決の基盤の独立した不変条件・変異試験 | 12 の不変条件を対戦の 1 歩ごとに確かめた。20 の変異をすべて見つけた | tests/test_kernel_invariants_v0_15.py、[検証と切り替え](event-integration-verification-v0.15d.md) 4・5 章 |
| 性能 | 固定した v0.13 の 1.32 倍（解決の基盤が受け持つコマンド全体）・1.48 倍（受け付けたワザ）。同じ機械・同じ Python・3 回の中央値 | [先読み](preflight-optimization-v0.15c.md) 5 章、[検証と切り替え](event-integration-verification-v0.15d.md) 7 章 |

### 見つけた事項

- v0.13 の `WRONG_PHASE` の理由の文（決定への答えの段階の違い）は、`frozenset` の並びで書くので、プロセスごと（文字列のハッシュの乱数化）に段階の並びが変わる。状態・ログ・乱数には影響しない。エンジンは変えていない（v0.16 への提案。[統合](kernel-integration-v0.15b.md) 7 章）。
- v0.14 の先読みは、エナジーへんかんの答えを枚数ごとの代表だけで試していた。v0.15c で、すべての答えを試すようにした（今の対応カードでは結果は同じ）。

## v0.16 で変えたこと（旧経路の撤去と解決の基盤の一本化）

v0.16 は、v0.13 のワザの解決の経路を外し、ワザ・番の終わり・きぜつのあとの決定の解決を、解決の基盤（`kyuura_engine/resolution/`）だけで処理するようにした版です（版 0.16.0）。対応するカード・ルール・裁定・未解決の事項（エンジンが止める `UNRESOLVED_…` 17 件・未解決の裁定 22 件）・書き出しの形式 9・ログ・乱数の使い方は v0.13・v0.15 と同じです（[監査](legacy-removal-audit-v0.16a.md)、[撤去](kernel-consolidation-v0.16b.md)、[先読み](preflight-consolidation-v0.16c.md)、[テストの移行](legacy-test-migration-v0.16d.md)、[最終監査](kernel-consolidation-verification-v0.16e.md)）。

| 項目 | 状況 | 文書・テスト |
|---|---|---|
| 公開の `apply_command(state, command)` | 呼び方・約束は同じ。経路（`Route`・`apply_command_via`）はない。解決の設定（先読みの方法）を選ぶ内部の入口は `engine.apply_command_with`・`apply_command_traced` | tests/test_kernel_integration_v0_15.py の `EntryTest` |
| 解決の基盤が処理するコマンド | ワザ・番の終わり（`resolution.COMMANDS`）と、再開先が `attack`・`knock_out`・`post_knockout`・`take_prize`・`promote_active` の決定への答え（`resolution.RESUMES`）。トレーナーの決定と範囲外のコマンドは engine.py | [撤去](kernel-consolidation-v0.16b.md) 4 章 |
| v0.13 の約束で書いたワザの実装（`AttackEffect.resolve`・`resume`） | 解決の基盤の枠の中のアダプタ（`resolution/contract.py`）で処理する。どちらも持たない実装は `UNSUPPORTED_ATTACK` で拒否（効果のないワザにしない）。製品の 24 種類は要素の並び | tests/test_contract_adapter_v0_16.py、[撤去](kernel-consolidation-v0.16b.md) 3 章 |
| v0.13 の止める関数 | 限定的な互換の部品 `resolution/v013_checks.py` の 3 つの使い道（アダプタ・上限を超えたとき・比べる方法 `legacy`）だけ | tests/test_preflight_consolidation_v0_16c.py、[先読み](preflight-consolidation-v0.16c.md) |
| 先読みの上限 | 4,096。`derived` も実際の処理の結果を数える（v0.15c はちょうど 4,097 通りのコインだけの木を受け付けていた。v0.16c で直した。製品のカードでは起こらない） | [先読み](preflight-consolidation-v0.16c.md) 4 章 |
| `WRONG_PHASE`（決定への答え）の理由の文 | 段階の並びを決まった順番にした（v0.15 まではプロセスごとに変わっていた） | tests/test_wrong_phase_message_v0_16d.py、[テストの移行](legacy-test-migration-v0.16d.md) 5 章 |
| 実験用の互換の層（`experiments/`） | 外した | [テストの移行](legacy-test-migration-v0.16d.md) 4 章 |
| 固定した v0.13・v0.15 との比較 | 2,560 対戦・350,533 歩を別のプロセスで比べ、どちらとも食い違い 0（許した差は `WRONG_PHASE` の段階の並び 202 件だけ） | [最終監査](kernel-consolidation-verification-v0.16e.md) 3 章 |
| 性能 | 固定した v0.13 の 1.28 倍（解決の基盤が受け持つコマンド全体）・1.46 倍（受け付けたワザ）。v0.15 より 7〜8% 速い | [最終監査](kernel-consolidation-verification-v0.16e.md) 6 章 |

### 見つけた事項

- v0.15c の先読み `derived` は、結果がちょうど 4,097 通りのコインだけの木で、実際の処理の結果を上限に数えず受け付けていた（`derived_full` は拒否）。v0.16c で直した（製品のカードのコインだけの木は 64 通り以下で起こらない）。
- 移したテストのうち 1 件（じこさいせいの K3）は、v0.16b〜v0.16c のあいだ、解決の基盤の枠の外の誤りで通っていて、K3 を確かめていなかった。v0.16d で直した（[テストの移行](legacy-test-migration-v0.16d.md) 7 章）。

## v0.17 で加えたもの（実カードによる解決の基盤の拡張性の実証）

v0.17 は、実際のカードを解決の基盤に加えて、拡張性を確かめた版です（版 0.17.0）。

- [カードの選定](card-selection-v0.17a.md)
- [既存の要素だけのカード](card-implementation-v0.17a.md)
- [R団のカビゴン](rocket-snorlax-v0.17b.md)
- [キョウのベトベトンの設計の検証](kogas-muk-event-design-v0.17c.md)
- [拡張性の検証](card-extensibility-verification-v0.17d.md)

### 実装済み・テスト済み

| 項目 | 根拠 | テスト |
|---|---|---|
| モンジャラ（PMCG1-007。しめつける 20・コインが「おもて」ならマヒ、どくのこな 20・どく）を、既存の実装の型の登録だけで使える | p.55 | test_existing_elements_v0_17a.py `TangelaTest` |
| サカキのニャース（PMCG6-063。ねこノミ・ダメージなし・コインが「おもて」ならこんらん、ねこキック 30）を、既存の要素の新しい並びで使える | p.229 | `GiovannisMeowthTest` |
| R団のカビゴン（PMCG6-073）の［わるいねぞう］: ねむり状態で相手のワザによるダメージ（最終ダメージ > 0）を受けたとき、それによってきぜつしても、ダメージを与えたポケモンに 20（特殊能力によるダメージ。宣言しない）。ねむりでなければはたらかない。かがくへんかガスで消える | p.245（Z1〜Z20） | test_rocket_snorlax_v0_17b.py `RestlessSleepTest` |
| R団のカビゴンのたおれこむ: 20 のあと、自分をねむり状態に（自分への効果も「とうめい」を評価。ねむりにする前に自分が HP 以上なら飛ばす） | p.245・p.155（Z21〜Z30） | `TumbleTest` |
| R団のカビゴンがワザのダメージで、ワザを使ったポケモンが 20 で、そろってきぜつしうる場合は、宣言の前に止める（C18 と同じコード） | p.324（Z13） | `test_double_knock_out_stops_before_the_attack` |
| 「ダメージを与えた後」の効果で、ダメージを与えなかったときは宣言の前に止める（Z23。どの先読みの方法でも、コインの結果によらない） | p.155・p.245・p.309・p.319〜p.321 | `test_no_damage_stops_before_the_attack`・`test_no_damage_stops_in_every_preflight_mode`・test_unresolved_boundaries_v0_4e.py `EffectAfterNoDamageBoundaryTest` |
| 60 枚のデッキで、正式な開始から勝敗まで（モンジャラ・サカキのニャース 80 局、R団のカビゴン 80 局）。不変条件・ログの監査・書き出しの監査・乱数はコインだけ・同じ操作の列で同じ結果・保存と再開。固定値 2 局 | — | `NaturalGamesTest`・`GoldenGameTest`（2 つのファイル） |
| 固定した v0.16 との比較（既存のカードの対戦 2,560・350,533 歩。標準と比べる方法 `legacy` の両方）で食い違い 0 | — | [拡張性の検証](card-extensibility-verification-v0.17d.md) 3 章 |
| 変異試験 46 / 46、解決の基盤の不変条件の掃引 60,093 歩で失敗 0、ストレス実行 1,120 対戦で内部の誤り 0 | — | 同 5 章・6 章 |

### 実装済み・テスト限定

| 項目 | 状況 |
|---|---|
| ストレス実行の組 `snorlax`・`snorlax_mixed` | ふだんのテストでは走らせない。`python3 tools/stress_engine.py --scenario snorlax --scenario snorlax_mixed` |
| ［わるいねぞう］の 20 の弱点・抵抗力（Z9） | 今のカードでは結果が変わらない（無色の弱点・抵抗力のカードがない）。変わる場合に止めることを、テスト専用のカードの組で確かめた |
| ねむりにする前に自分が HP 以上でこんじょうを使える場合（Z22） | 今のカードでは起こらない。コードのない問いで止める |

### 未実装

- キョウのベトベトン（PMCG6-023）の［だつりょくえき］と、ワザ「ヘドロのうず」。
  - 宣言する特殊能力か・処理する時点が原典で決まらず、今の解決の基盤はダメージの要素のあとの窓の中で決定を出して続けられないので、実装を延期した（DEFER）。
  - カードは分類で拒否する。延期を解く条件は [kogas-muk-event-design-v0.17c.md](kogas-muk-event-design-v0.17c.md) 6 章。
- ナツメのヤドン（ぐうたらこうげき。たおれこむと同じ文面）などは加えていない。

### 原典未確認・未解決

- 新しい未解決の裁定は 2 件（Z9・Z23）で、合わせて 24 件。新しいコードは `UNRESOLVED_EFFECT_AFTER_NO_DAMAGE` の 1 件で、合わせて 18 件。
- Z13 は C18、Z18 は C34/C35、Z22 の自分への効果は G37、Z29 は v0.3b と同じ問いで、新しい裁定にしていない。v0.16 までの未解決は削除・緩和していない。
- だつりょくえきの未解決（DR1・DR6・DR8・DR13・DR18）は、カードが未対応なので、エンジンの止める処理はない（延期の理由）。

### 見つけた事項

- 比べる方法 `legacy`（v0.13 の止める関数の先読み）は、v0.17 から加えた `VERIFIED` にない型にも v0.13 の止める関数を使っていた。そのため、たおれこむを「とうめい」のゴーストに使う歩で、コインが「うら」なら受け付けていた（Z23 を知らない）。
- v0.17d で、`legacy` が v0.13 の止める関数を使うのを `VERIFIED` の型だけにした。公開の `apply_command`（標準の先読み）は影響を受けていない（[拡張性の検証](card-extensibility-verification-v0.17d.md) 6.4 章）。
