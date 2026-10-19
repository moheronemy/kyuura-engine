# v0.70: 拡張パック以外の商品のポケモン 82 枚（既存の効果の再利用）

拡張パック以外の商品（ジムデッキ・イントロパック・クイックスターターギフト・拡張シート・プロモなど）のポケモン 82 枚を、kyuura データの採用で、どのワザも登録して
対応にしました。目的は対応するカードを増やすことで、カードの強さ・勝率・デッキの釣り合いは評価していません。

- 基準: v0.69（`f7a2ad87c359f0bdf623464318bbced04da41b2a`）。作業ブランチ `claude/v0.70-non-pack-effect-reuse`。開始時に `main`（v0.62 のマージ `1b890ee`）は v0.69 の祖先で、
  `main`・`claude/cool-ptolemy-5vtgsg` に v0.69 のあとの差分はありませんでした。未コミットの変更もありませんでした。
- カードの写しの元・研究の基準は、どちらも kyuura `7d3f4ca76c084774efb4ac6a1d3a943387e183c3` のまま（v0.69 と同じ）。kyuura は変えていません。
- ルールの基準（2000.02.14 版）・公開の固定のデッキ・固定の参照データ・書き出しの形式（22）は変えていません。後年に発売したカード（2001 年のイントロパック・プロモなど）も、
  今回の日本語の効果を既存のルールで扱い、発売日を理由に後年のルールを持ち込んでいません。
- 公式ガイドブックのキャプチャ・OCR・読み直しはしていません。英語版の文面・現行のルール・後年の裁定で補っていません。

## 1. 数

登録から数え直した値です（tests/test_non_pack_effect_reuse_v0_70.py の `TargetTest.test_counts_from_the_registry`）。

| | v0.69 | v0.70 |
|---|---|---|
| 写し・対応するカード | 553・553 | 635・635（kyuura の data/cards.json は 1,377 件） |
| 対応ポケモン・トレーナー・エネルギー | 410・113・30 | 492・113・30 |
| ワザの登録 | 689 | 825（136 を加えた。説明文のないワザ 51・説明文のあるワザ 85） |
| 特殊能力・トレーナー・特殊エネルギーの登録 | 68・113・12 | 68・113・12（変えていない） |
| 書き出しの形式 | 22 | 22 |
| エンジンが止める `UNRESOLVED_…`・未解決の裁定 | 149・151 | 149・151（新しい問いはない） |

82 枚のうち 12 枚は、ほかの v0.70 のカードと処理に使う欄（日本語）が同じです（5 章）。82 種類の新しい効果が増えたのではありません。新しい効果の型は 2 つです（4 章）。

## 2. 82 枚と、使う型・パラメーター

写しの組は `pool_v0_70`（scripts/extract_kyuura_cards.py の `POOL_V0_70`。並びは依頼の並び）。82 枚とも kyuura data/engine_targets.json（7d3f4ca）の `engine_status` が
`reuse_candidate`・`play_scope` が `standard` のポケモンで、v0.69 までの 553 枚に入っていません（`TargetTest.test_targets_are_the_requested_82_cards`）。どのカードも
特殊能力を持ちません。

進化元は、名前の完全一致と段階で、対応しているカードにあります（形容詞を除く・名前の一部で推測することはしない。`UnsupportedWithoutRegistrationTest.test_evolution_lines_by_exact_name_and_stage`）。
チコリータ → ベイリーフ・ワニノコ → アリゲイツ・メリープ → モココは、どちらも今回の対象です。ベイビィの仕組みは加えていません。

| id | 名前 | 段階（進化元） | 発売 | ワザ（必要なエネルギー・ダメージ）→ 型（パラメーター） |
|---|---|---|---|---|
| GD1-004 | タケシのサンドパン | 1 進化（タケシのサンド） | 1998-04-26 | ぜんしんばり（闘闘・10）→ DamageThenPoisonAndParalyzeOnHeads()<br>サンドストーム（闘闘・20）→ DamageThenAttackCoinCheck(single_use=False) |
| GD1-008 | タケシのゴローン | 1 進化（タケシのイシツブテ） | 1998-04-26 | いわなげ（闘無無・20×）→ CoinFlipDamage(coins=3, damage_per_heads=20) |
| GD2-005 | カスミのパウワウ | たね | 1998-04-26 | オーロラビーム（水無・20）→ DamageOnly |
| GD2-009 | カスミのトサキント | たね | 1998-04-26 | つのでつつく（水・30）→ FailOnTailsDamage(coins=1) |
| GD2-013 | カスミのヒトデマン | たね | 1998-04-26 | スピードスター（水無・20）→ DamageIgnoringDefenderEffects() |
| GD2-014 | カスミのスターミー | 1 進化（カスミのヒトデマン） | 1998-04-26 | みずでっぽう（水・10+）→ ExtraEnergyDamage(energy_type=WATER, per_energy=10, max_extra=2)<br>バブルこうせん（水水水・30）→ ParalyzeOnHeads() |
| GD3-002 | マチスのピカチュウ | たね | 1998-07-25 | たいでん（無・—）→ AttachEnergyFromDiscardToSelf(energy_type=LIGHTNING)<br>でんきしっぽ（雷雷・20）→ ParalyzeOnHeads() |
| GD3-008 | マチスのビリリダマ | たね | 1998-07-25 | ブレイクボール（雷無・30）→ SelfDamageOnTails(self_damage=10) |
| GD3-013 | マチスのオニスズメ | たね | 1998-07-25 | ドリルくちばし（無・20）→ DamageOnly |
| GD4-005 | エリカのマダツボミ | たね | 1998-07-25 | どくのしる（草・10）→ PoisonOnHeads()<br>つるのムチ（草草・30）→ DamageOnly |
| GD5-008 | カツラのポニータ | たね | 1999-02-26 | こうそくいどう（炎無・20）→ DamageThenSelfBarrierOnHeads() |
| GD5-013 | カツラのドードリオ | 1 進化（カツラのドードー） | 1999-02-26 | きあいづき（無無・50）→ FailOnTailsDamage(coins=1) |
| GD6-006 | ナツメのゴース | たね | 1999-02-26 | まとわりつく（超無・20）→ DamageThenRetreatLock() |
| ES1-004 | ビードル | たね | 1998-03-23 | つつく（無・10）→ DamageOnly<br>どくのつの（草・—）→ PoisonWithoutDamage() |
| ES1-008 | ズバット | たね | 1998-03-23 | かみつく（無・10）→ DamageOnly<br>あやしいおんぱ（草無・10）→ ConfuseOnHeads() |
| ES1-012 | カイロス | たね | 1998-03-23 | はさんでなげる（草・10+）→ CoinBonusDamage(bonus=10)<br>きりさく（無無無・30）→ DamageOnly |
| ES1-016 | ニョロモ | たね | 1998-03-23 | あわ（水・10）→ ParalyzeOnHeads() |
| ES1-017 | ニョロゾ | 1 進化（ニョロモ） | 1998-03-23 | ぐるぐる（水水・—）→ StatusByCoinWithoutDamage(heads=confusion, tails=sleep)<br>のしかかり（水無無・20）→ ParalyzeOnHeads() |
| ES1-018 | ニョロボン | 2 進化（ニョロゾ） | 1998-03-23 | メガトンパンチ（水水・30）→ DamageOnly<br>ハイドロポンプ（水水水・40+）→ ExtraEnergyDamage(energy_type=WATER, per_energy=10, max_extra=2) |
| ES1-024 | ポッポ | たね | 1998-03-23 | かぜおこし（無・10）→ DamageOnly<br>でんこうせっか（無無・10+）→ CoinBonusDamage(bonus=20) |
| ES1-030 | ベロリンガ | たね | 1998-03-23 | なめる（無・—）→ ParalyzeOnHeadsWithoutDamage()<br>ふみつけ（無無・20+）→ CoinBonusDamage(bonus=10) |
| ES1-032 | イーブイ | たね | 1998-03-23 | かじる（無・10）→ DamageOnly<br>とびかかる（無・20）→ FailOnTailsDamage(coins=1) |
| ES2-008 | シェルダー | たね | 1998-06-17 | しおふき（水無・20+）→ ExtraEnergyDamageMixed(energy_type=WATER, per_energy=10, max_extra=2) |
| ES2-009 | クラブ | たね | 1998-06-17 | あわ（水・10）→ ParalyzeOnHeads()<br>はさみギロチン（水無無・30）→ DamageOnly |
| ES2-010 | ラプラス | たね | 1998-06-17 | うたう（無・—）→ SleepOnHeadsWithoutDamage()<br>なみのり（水水・30）→ DamageOnly |
| ES2-019 | ルージュラ | たね | 1998-06-17 | れいとうパンチ（水・10）→ ParalyzeOnHeads()<br>コールドブレス（水水・20）→ DamageThenSleepOnHeads() |
| ES2-022 | ゴーリキー | 1 進化（ワンリキー） | 1998-06-17 | メガトンキック（闘闘・30）→ DamageOnly<br>ワンツーパンチ（闘闘闘・30+）→ CoinBonusDamage(bonus=20) |
| ES2-026 | サワムラー | たね | 1998-06-17 | にどげり（闘闘・30×）→ CoinFlipDamage(coins=2, damage_per_heads=30)<br>まわしげり（闘闘無・30）→ ParalyzeOnHeads() |
| ES2-031 | オニドリル | 1 進化（オニスズメ） | 1998-06-17 | でんこうせっか（無無・10+）→ CoinBonusDamage(bonus=20)<br>ドリルこうか（無無無・50）→ FailOnTailsDamage(coins=1) |
| ES3-015 | タッツー | たね | 1998-11-24 | かくれる（無・—）→ SelfBarrierOnHeads()<br>みずでっぽう（水・10+）→ ExtraEnergyDamage(energy_type=WATER, per_energy=10, max_extra=2) |
| ES3-033 | ガルーラ | たね | 1998-11-24 | かみつく（無無・20）→ DamageOnly<br>テールドロップ（無無無・80）→ FailOnTailsDamage(coins=2) |
| QSG-006 | カイロス。ES1-012 と同じデータ | たね | 1998-12-04 | はさんでなげる（草・10+）→ CoinBonusDamage(bonus=10)<br>きりさく（無無無・30）→ DamageOnly |
| QSG-014 | ニョロモ。ES1-016 と同じデータ | たね | 1998-12-04 | あわ（水・10）→ ParalyzeOnHeads() |
| QSG-015 | ニョロゾ。ES1-017 と同じデータ | 1 進化（ニョロモ） | 1998-12-04 | ぐるぐる（水水・—）→ StatusByCoinWithoutDamage(heads=confusion, tails=sleep)<br>のしかかり（水無無・20）→ ParalyzeOnHeads() |
| QSG-016 | ニョロボン。ES1-018 と同じデータ | 2 進化（ニョロゾ） | 1998-12-04 | メガトンパンチ（水水・30）→ DamageOnly<br>ハイドロポンプ（水水水・40+）→ ExtraEnergyDamage(energy_type=WATER, per_energy=10, max_extra=2) |
| QSG-019 | ラプラス。ES2-010 と同じデータ | たね | 1998-12-04 | うたう（無・—）→ SleepOnHeadsWithoutDamage()<br>なみのり（水水・30）→ DamageOnly |
| QSG-031 | ルージュラ。ES2-019 と同じデータ | たね | 1998-12-04 | れいとうパンチ（水・10）→ ParalyzeOnHeads()<br>コールドブレス（水水・20）→ DamageThenSleepOnHeads() |
| QSG-036 | ゴーリキー。ES2-022 と同じデータ | 1 進化（ワンリキー） | 1998-12-04 | メガトンキック（闘闘・30）→ DamageOnly<br>ワンツーパンチ（闘闘闘・30+）→ CoinBonusDamage(bonus=20) |
| QSG-042 | ベロリンガ。ES1-030 と同じデータ | たね | 1998-12-04 | なめる（無・—）→ ParalyzeOnHeadsWithoutDamage()<br>ふみつけ（無無・20+）→ CoinBonusDamage(bonus=10) |
| QSG-044 | ガルーラ。ES3-033 と同じデータ | たね | 1998-12-04 | かみつく（無無・20）→ DamageOnly<br>テールドロップ（無無無・80）→ FailOnTailsDamage(coins=2) |
| SI-001 | レディバ | たね | 1999-07-17 | かじる（無・10）→ DamageOnly<br>こうそくいどう（草草・20）→ DamageThenSelfBarrierOnHeads() |
| SI-005 | ピジョット | 2 進化（ピジョン） | 1999-07-17 | マッハひこう（無無・40）→ FailOnTailsDamage(coins=1)<br>カッターウインド（無無無無・50）→ DamageOnly |
| SI-006 | イワーク | たね | 1999-07-17 | たたきつける（無無・20×）→ CoinFlipDamage(coins=2, damage_per_heads=20)<br>のしかかり（闘闘闘闘・40）→ ParalyzeOnHeads() |
| SI-007 | トゲピー | たね | 1999-07-17 | おおごえでなく（無・10）→ ConfuseOnHeads() |
| SI-009 | ラッタ | 1 進化（コラッタ） | 1999-07-17 | するどいまえば（無無・10+）→ CoinBonusDamage(bonus=30) |
| SI-015 | カメール | 1 進化（ゼニガメ） | 1999-07-17 | みずでっぽう（水水・20+）→ ExtraEnergyDamage(energy_type=WATER, per_energy=10, max_extra=2) |
| IP1-001 | フシギダネ | たね | 1999-07-30 | たいあたり（無・10）→ DamageOnly<br>はっぱカッター（草草・30）→ DamageOnly |
| IP1-016 | ニャース | たね | 1999-07-30 | かみつく（無・10）→ DamageOnly<br>みだれひっかき（無無・10×）→ CoinFlipDamage(coins=3, damage_per_heads=10) |
| IP1-026 | エレブー | たね | 1999-07-30 | でんきショック（雷雷無・30）→ ParalyzeOnHeads() |
| IP1-030 | ドードー | たね | 1999-07-30 | みだれづき（無・10×）→ CoinFlipDamage(coins=2, damage_per_heads=10) |
| IP1-037 | ルージュラ | たね | 1999-07-30 | はたく（無・10）→ DamageOnly<br>おうふくビンタ（超無・20×）→ CoinFlipDamage(coins=2, damage_per_heads=20) |
| IP1-039 | ドガース | たね | 1999-07-30 | どくガス（草・10）→ PoisonOnHeads()<br>こんらんガス（草草・20）→ ConfuseOnHeads() |
| IP2-003 | カメール | 1 進化（ゼニガメ） | 1999-07-30 | あわ（水・10）→ ParalyzeOnHeads()<br>なみのり（水水・30）→ DamageOnly |
| IP2-013 | オニスズメ | たね | 1999-07-30 | つつく（無・10）→ DamageOnly<br>つばさでうつ（無無・20）→ DamageOnly |
| IP2-016 | ゼニガメ | たね | 1999-07-30 | かみつく（水・10）→ DamageOnly<br>ロケットずつき（水無・20）→ DamageOnly |
| IP2-039 | ブーバー | たね | 1999-07-30 | ほのおパンチ（炎・20）→ DamageOnly<br>スモッグ（炎炎・20）→ PoisonOnHeads() |
| PF1-007 | ワニノコ | たね | 1999-12-10 | かみつく（無・10）→ DamageOnly<br>いかり（水無・10+）→ DamagePlusOwnCounters(per=10) |
| PF2-004 | エーフィ | 1 進化（イーブイ） | 2000-07-08 | でんこうせっか（無無・10+）→ CoinBonusDamage(bonus=20)<br>サイケこうせん（超超無・30）→ ConfuseOnHeads() |
| NIP1-001 | チコリータ | たね | 2001-04-06 | たいあたり（無・10）→ DamageOnly<br>はっぱカッター（草無・20）→ DamageOnly |
| NIP1-002 | ヒマナッツ | たね | 2001-04-06 | ぶつかる（無・10）→ DamageOnly |
| NIP1-008 | ヒメグマ | たね | 2001-04-06 | ひっかく（無・10）→ DamageOnly<br>みだれひっかき（無無・10×）→ CoinFlipDamage(coins=3, damage_per_heads=10) |
| NIP1-016 | ヒノアラシ | たね | 2001-04-06 | ひをふく（炎・10+）→ CoinBonusDamage(bonus=10) |
| NIP1-022 | パラス | たね | 2001-04-06 | ねむりのほうし（草・10）→ DamageThenSleepOnHeads()<br>ひっかく（無無・20）→ DamageOnly |
| NIP1-024 | ベイリーフ | 1 進化（チコリータ） | 2001-04-06 | たいあたり（無無・20）→ DamageOnly<br>ねむりごな（草草無・30）→ SleepOpponent() |
| NIP2-002 | マリル | たね | 2001-04-06 | たいあたり（無・10）→ DamageOnly<br>ころがる（無無・20）→ DamageOnly |
| NIP2-003 | ホーホー | たね | 2001-04-06 | ける（無・20）→ FailOnTailsDamage(coins=1) |
| NIP2-004 | アリゲイツ | 1 進化（ワニノコ） | 2001-04-06 | きりさく（無無・20）→ DamageOnly<br>かみつく（水無無・40）→ DamageOnly |
| NIP2-016 | ワニノコ | たね | 2001-04-06 | ひっかく（無・10）→ DamageOnly<br>かみつく（水無・20）→ DamageOnly |
| NIP2-018 | メリープ | たね | 2001-04-06 | でんげき（雷無・30）→ SelfDamageOnTails(self_damage=10) |
| NIP2-024 | ハリーセン | たね | 2001-04-06 | どくばり（水無・20）→ PoisonOnHeads() |
| NIP2-026 | モココ | 1 進化（メリープ） | 2001-04-06 | たいあたり（無無・20）→ DamageOnly<br>でんきショック（雷雷無・30）→ ParalyzeOnHeads() |
| NIP2X-004 | ネイティ | たね | 2001-04-06 | あやしいひかり（超・10）→ ConfuseOnHeads() |
| PR1-011 | なみのりピカチュウ | たね | 1997-08 | なみのり（水水・30）→ DamageOnly |
| PR1-014 | なみのりピカチュウ。PR1-011 と同じデータ | たね | 1997-08-15 | なみのり（水水・30）→ DamageOnly |
| PR1-045 | ディグダ | たね | 1998-11-13 | つつく（闘・10）→ DamageOnly<br>ころばす（闘無・20+）→ CoinBonusDamage(bonus=10) |
| PR1-066 | マリル | たね | 1999-06-15 | みずでっぽう（水水・20+）→ ExtraEnergyDamage(energy_type=WATER, per_energy=10, max_extra=2) |
| PR1-069 | ミュウ（kyuura の名前は「？？？」） | たね | 1999 | Psyche(サイケ)（超超・40）→ DamageOnly |
| PRN-006 | チコリータ | たね | 2000 | たいあたり（無・10）→ DamageOnly<br>リフレクター（草・—）→ HalveDamageNextTurn() |
| PRN-009 | チコリータ。PRN-006 と同じデータ | たね | 2000 | たいあたり（無・10）→ DamageOnly<br>リフレクター（草・—）→ HalveDamageNextTurn() |
| PRN-013 | ルージュラ。ES2-019 と同じデータ | たね | 2000-01-22 | れいとうパンチ（水・10）→ ParalyzeOnHeads()<br>コールドブレス（水水・20）→ DamageThenSleepOnHeads() |
| PRN-038 | ノコッチ | たね | 2001-01-01 | にらむ（無・—）→ ParalyzeOnHeadsWithoutDamage()<br>ドリルしっぽ（無無・10+）→ CoinBonusDamage(bonus=20) |
| PRN-047 | ハネッコ | たね | 2001-07-23 | ころがりタックル（草・20）→ DamageOnly |

型の内訳（ワザの数）: DamageOnly 51・ParalyzeOnHeads 15・CoinBonusDamage 13・FailOnTailsDamage 8（2 枚のコインは 2）・CoinFlipDamage 7・ExtraEnergyDamage 6・ConfuseOnHeads 5・
DamageThenSleepOnHeads 4・PoisonOnHeads 4・ParalyzeOnHeadsWithoutDamage 3・DamageThenSelfBarrierOnHeads 2・SelfDamageOnTails 2・SleepOnHeadsWithoutDamage 2・
HalveDamageNextTurn 2・StatusByCoinWithoutDamage 2（v0.70）・ほかは 1 つずつ（DamageThenPoisonAndParalyzeOnHeads・DamageThenAttackCoinCheck・DamageIgnoringDefenderEffects・
DamageThenRetreatLock・PoisonWithoutDamage・SleepOpponent・DamagePlusOwnCounters・SelfBarrierOnHeads・ExtraEnergyDamageMixed・AttachEnergyFromDiscardToSelf（v0.70））。

## 3. 資料と記録

### 3.1 kyuura のデータの採用

- kyuura の data/cards.json（7d3f4ca）を基本データとして採用しました（`card_sources.json` の 82 件。`basis: kyuura_data`・`status: adopted`・`kyuura_commit` は 7d3f4ca・
  記録した日 2026-10-19）。処理に使う文面は、説明文のあるワザ 85 のどれも kyuura の印刷の文面です（`play_text` は `kyuura_printed_text`。研究の対応表の `adopted_printed_text`）。
- 研究の基準のコミットで、82 枚の id を指す記録を探しました（data/sidecar の最新の説明 LD-・照合 CC-・裁定 CR-・論点 UQ-、data/rule_history.json のエラッタ、
  data/curation の修正・日英の違い）。どのカードを指す記録もありません（`kyuura_records` は空。scripts/check_research_links.py が研究の基準のコミットの記録と照らす）。
  一般の規定と既存の照合の記録（型の根拠）は再利用しました。別のカードの照合（P43 のページなど）を、今回のカードの原典照合として写していません。
- kyuura の日本語の文面は 82 枚とも pcg-search.com の転記です（写しの `ja_text_source`。PR1-069 の名前の訂正を除く）。同じサイトでの日本語の欄の照合は独立した照合に
  ならないので、新しい外部照合はしていません（`external_checks` は空）。版は kyuura の `copies`（サイトのページと一覧の番号）で、カード名ではなく id で決めています。
  アクセスできない・CC- がないことだけを理由に保留にしたカードはありません。
- 新しい疑問（論点）は生じていません。保留にしたカードもありません。

### 3.2 PR1-069 の名前（利用者が示した訂正）

- kyuura の名前は「？？？」です。利用者が、このカードをミュウ（Ancient Mew）と同定し、カード画像と補助資料の URL
  （https://bulbapedia.bulbagarden.net/wiki/Ancient_Mew_(The_Power_of_One_promo)）を示しました。名前の訂正の根拠は「利用者の同定と、利用者が示した画像」で、URL は
  利用者が示した補助資料です。この作業では、URL の本文をネットワークのプロキシ（403）で取得できておらず、サイトの本文を検証した・ルーン文字のすべての項目を解読した、
  とは記録していません。エンジンは画像を読んでいません。追加のガイドブックの調査はしていません。
- カード id は PR1-069 のまま、ルールに使う日本語の名前を「ミュウ」にしました。訂正したのは `name.ja` だけで、HP 30・超タイプ・弱点 超・にげる 2・ワザ「Psyche(サイケ)」
  （超超・40・説明なし。DamageOnly）は kyuura のデータのままです。
- kyuura は変えず、写しの作り直しで、エンジンが明示的な訂正を当てはめます（scripts/extract_kyuura_cards.py の `ENGINE_USER_CORRECTIONS`・`engine_user_correction_problems`・
  `apply_engine_user_corrections`。書き出しの `engine_user_corrections` に、元のコミット・元の値・採用した値・利用者が示した根拠を別々に書く）。v0.69 の `KYUURA_CORRECTIONS`
  （kyuura が当てはめた修正を台帳で確かめる表）には入れていません。
  - 写しの元の値が「？？？」なら当てはめ、すでに「ミュウ」なら当てはめず（二重に当てはめない）表を移すよう知らせて書き出しません。どちらでもない値・kyuura の台帳やカードの
    記録に同じ欄の修正があるときも書き出しません。
  - 採用の記録の `user_name_correction`（kyuura の値・採用した値・根拠）を scripts/check_card_sources.py が写しの訂正と照らします（訂正のないカードに書けず、訂正のある
    カードには要る）。名前の比べ方そのもの（採用の記録の名前 = 写しの名前）は変えていません。
  - scripts/check_research_links.py の 6（研究の基準のコミットと写しの比べ）は、研究の対応表の `engine_user_corrections`・写し・作り直しの表が同じ訂正で、研究の基準の
    コミットの値が訂正の前の値のときだけ、その欄を訂正のあとの値にして比べます（ほかの欄・ほかのカードの比べ方は変えていない）。
  - kyuura への報告事項にしました（docs/data-provenance.md）。
- 同じ名前 4 枚の制限で、PMCG3-033 などのミュウと同じ名前として数えます（混ぜて合計 4 枚は受け付け、5 枚は `TOO_MANY_COPIES`。`AncientMewTest`）。ほかのミュウの定義・
  カード id は変えていません。名前「ミュウ」は前からあるので、カツラのクイズの名前の候補は、このカードのためには増えていません（「？？？」も候補にない）。

## 4. 再利用の設計

### 4.1 既存の型（77 件）

既存の型の登録を、同じ文面の既存の登録と、ダメージの目安の有無・コインの枚数・追加の量・ワザを使う条件・効果の順番・必要なエネルギーで選びました。型の `check` は
変えていません（下の 4.2 の書き方の追加を除く）。

- 必要なエネルギーが「水」だけのみずでっぽう・ハイドロポンプ 6 つ（GD2-014 ワザ 0・ES1-018 ワザ 1・ES3-015 ワザ 1・QSG-016 ワザ 1・SI-015 ワザ 0・PR1-066 ワザ 0）は
  `ExtraEnergyDamage(WATER, 10, 2)`（v0.6）です。同じ文面の第4弾のコダックの登録 `ExtraEnergyDamageMixed` を写していません（その型の `check` は無色のないワザを拒否する）。
  「多い水」はワザごとの必要な数から数えます（`programs.ExtraEnergy`）。今の共通の処理で、ついているエネルギーカード 1 枚につき「水」の基本エネルギーカードだけを数え、
  無色2個エネルギーは数えず、レインボーエネルギー（RB1）・［エネエネ］のカード（BZ2）・［へんしん］（TE1）で数え方が決まらなければ止めます。混ざったエネルギーの HC4 は
  当てはめていません（多い「水」の数え方が決まる）。必要なエネルギーに無色がまざるシェルダー（ES2-008）の「しおふき」だけは `ExtraEnergyDamageMixed`（HC4 の問いのまま）。
- ガルーラ（ES3-033・QSG-044）は「かみつく」「テールドロップ」の版です。PMCG2-046 の「こどものおつかい」の訂正は別のカードの別のワザで、持ち込んでいません。テールドロップは
  コイン 2 枚がどちらも「おもて」のときだけ成功する `FailOnTailsDamage(coins=2)`（「おもて」の数に比例しない）。
- PR1-069 は 3.2 の名前の訂正に加えて `DamageOnly`。

### 4.2 説明の書き方の追加（2 件）

カツラのポニータ（GD5-008）のワザ 0・レディバ（SI-001）のワザ 1 の「こうそくいどう」（ダメージあり）は、`DamageThenSelfBarrierOnHeads` で、`SELF_BARRIER_ON_HEADS_TEXTS` に
「コインを投げて「おもて」なら、次の相手の番、このカードはワザによるダメージや効果を受けない。」を 1 通り加えました。v0.37 のカスミのコイキングの「しんだふり」
（`SelfBarrierOnHeads`。ダメージなし）と同じ文で、v0.41 のシードラの書き方の語順違いです（意味を確かめた明示的な 1 通り。一般の正規化はしていない）。ダメージ → コイン →
自分への持続する効果 `AttackBarrier` の順と、相手がダメージを受けない場合の扱いは既存の型のままです。ダメージのない `SelfBarrierOnHeads` は使いません（タッツー ES3-015 の
「かくれる」はダメージがないので `SelfBarrierOnHeads`。v0.37 の書き方と同じ）。

### 4.3 既存の要素の組み合わせ（3 件・小さな型 2 つ）

1. マチスのピカチュウ（GD3-002）の「たいでん」: `AttachEnergyFromDiscardToSelf(LIGHTNING)`。要素は v0.45 の `DamageThenAttachEnergyFromDiscardToSelf` からダメージの要素を除いた
   `AttachFromDiscard(LIGHTNING, 1, exact=True)` だけ。トラッシュに「雷」の基本エネルギーカードがあれば、ワザを使ったプレイヤーが 1 枚を選び（決定 `attach_from_discard`。1 枚でも
   決定を出し、0 枚は選べない）、自分につけます。なければ何もつけずに続けます。手札からつける通常の操作の回数・特殊能力でつけた枚数に数えません。つけたら
   `effects.after_energy_attached`。レインボーエネルギー（RB2）・つけることができない効果（v0.59 のクリスタルビーム）は共通の処理です。マチスのエレブーの「最大2枚」
   （`AttachDiscardEnergyToSelf`。0 枚は HC7）とは別の文面・別の型で、HC7 は入りません。
2. ニョロゾ（ES1-017・QSG-015）の「ぐるぐる」: `StatusByCoinWithoutDamage(CONFUSION, SLEEP)`。要素は v0.41 の `DamageThenStatusByCoin` からダメージの要素を除いた
   `Status(CONFUSION, local_coin=おもて, otherwise=SLEEP)` だけ。コインは 1 枚で、「うら」をワザの失敗にせず、投げ直しません。相手がワザを受けない（HC3）・「とうめい」で
   受けないと決まっている（T19b）・特殊状態の重なりは共通の処理です。

どちらも `DamageOnly` 系の型を 0 ダメージに広げず、ダメージのない型にしました（ダメージの要素も、ログ `damage` もない）。`programs.BUILDERS` の要素の並びで加え、v0.13 の
約束では書いていません（`v013_checks.VERIFIED` に入れていない。tests/helpers.py の `ATTACK_TYPES_SINCE_V0_17` に加えた）。`engine.py`・`resolution/` にカード id の分岐はありません。

## 5. 同じデータのカードと、v0.69 の写しの表との違い

- v0.69 の `EQUIVALENT_CARDS` は、kyuura の `mechanically_equivalent`（前の版で登録したカードと、ゲームに使う欄が全部同じカード）の表です。今回の 82 枚は、文面・HP・ワザの組などが
  登録したカードと違うので、この表に加えていません（登録は id ごとに書いた）。
- 82 枚のうち 12 枚は、ほかの v0.70 のカードと、処理に使う欄（日本語）が同じです（kyuura の同じカードの組）。登録は id ごとに書いたうえで、同じ値の登録を同じ不変なオブジェクトに
  置きかえます（effects.py の `SAME_DATA_CARDS_V0_70`・`_with_shared_entries`。どちらにもワザだけがあり、ワザの位置の組と登録の値が同じでなければ `RuntimeError`）。
  写しのデータが同じことは `SharedEntriesTest` が確かめます。
  - QSG-006 = ES1-012（カイロス）・QSG-014 = ES1-016（ニョロモ）・QSG-015 = ES1-017（ニョロゾ）・QSG-016 = ES1-018（ニョロボン）・QSG-042 = ES1-030（ベロリンガ）・
    QSG-019 = ES2-010（ラプラス）・QSG-031 = PRN-013 = ES2-019（ルージュラ）・QSG-036 = ES2-022（ゴーリキー）・QSG-044 = ES3-033（ガルーラ）・PR1-014 = PR1-011
    （なみのりピカチュウ）・PRN-009 = PRN-006（チコリータ）
- 同じ商品の元データの id は消したり統合したりしていません（状態・ログ・書き出しにはそれぞれの id がそのまま残る）。パラメーターの違うカードを同じものにしていません。

## 6. マチスの秘策・カツラのクイズ（公開の情報の候補）

- マチスの秘策の受け付けるかの確かめ（`engine._identity_independent`）で試すカードは、今までどおり公開の情報（対応しているカードの一覧と効果の登録表）だけから作ります
  （`engine._identity_candidates`。処理の同じカードを 1 枚で代表する）。82 枚が加わり、試すカードは v0.69 の 457 枚から 527 枚になりました（処理の違うカード 70 種類。
  同じデータの 12 枚は 1 枚で代表する）。上限（`_IDENTITY_TRIAL_LIMIT` = 512）・2 枚以上を指定するコマンドの制限は変えていません。見えないデッキの中身で受け付けるかを
  変えていません（v0.68 の `SecretPlanLeakTest` がそのまま通る）。
- 1 枚を指定するコマンドの試す回数は、割り当てる前 1 回 + たねポケモン 241 + 「たねポケモンでない」1 = 243 回（v0.69 は 189 回）。トラッシュしたあとに、たねポケモンでない
  カードのほかの項目を読む処理があると、たねポケモンでないカード 286 を加えて 529 回になり、上限を超えて `UNSUPPORTED_SECRET_PLAN_IDENTITIES` になります（v0.69 は 459 回で
  受け付けていた）。マチスの秘策のテスト（tests/test_secret_plan_v0_67.py・tests/test_final_pmcg_cards_v0_68.py）と v0.67 の検証用デッキの対戦（2 seed）で、この読む処理に
  入った確かめは 0 回でした（scratchpad の計測。受け付けるかの差は再現されなかった）。今の処理の中でこの経路に入る盤面は見つけておらず、作っていません。入る盤面が
  見つかれば、受け付けるかが v0.69 と変わる（拒否になる）ことを、ここに書いた理由で説明できます（上限は上げない）。
- カツラのクイズ その3 の答えの候補（`effects.quiz_answer_names`。同梱のカードのデータとこの対戦の定義のポケモンの名前）に、v0.70 の新しい名前 21 種類（なみのりピカチュウ・アリゲイツ・エーフィ・
  カスミのスターミー・カツラのドードリオ・チコリータ・トゲピー・ネイティ・ノコッチ・ハネッコ・ハリーセン・ヒノアラシ・ヒマナッツ・ヒメグマ・ベイリーフ・ホーホー・マリル・メリープ・
  モココ・レディバ・ワニノコ）が加わりました。候補の並び（位置）が変わるので、位置で答える決定は、同じ名前でも位置が変わります。比べ方は 7.2 節。「ミュウ」は前からあり、PR1-069 の
  ためには増えていません（「？？？」は候補にない）。

## 7. 検証

### 7.1 確かめたこと

- 写しの作り直し: `python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura --check`
- 記録の検査: `python3 scripts/check_card_sources.py`・`python3 scripts/check_research_links.py --kyuura ../kyuura`
- 単体テスト（tests/test_non_pack_effect_reuse_v0_70.py）:
  - 対象と数（`TargetTest`）: 82 枚が依頼の id と同じで v0.69 までの 553 枚にない・どのワザも登録した・型とパラメーターの表（説明文のあるワザ 85）・説明文のないワザ 51 が
    `DamageOnly`・必要なエネルギーが「水」だけの 6 つが `ExtraEnergyDamage`・新しい型が要素の並びの型・`engine.py`・`resolution/` に 82 枚の id がない。
  - 登録を除けば未対応にもどる（82 枚すべて・1 つのワザだけ）。データ（文面・コインの枚数・ダメージの形・必要なエネルギー・追加の量）を変えれば未対応になる代表 10 例。
    新しい型・加えた書き方が、ほかの文面・ダメージの有無を拒否する。進化元が名前の完全一致と段階で対応しているカードにある（`UnsupportedWithoutRegistrationTest`）。
  - 同じデータの 12 枚が同じデータで登録の値を共有する・ほかに同じデータの組がない・違う登録をまとめない（`SharedEntriesTest`）。
  - ぐるぐる（`SwirlTest`）: 「おもて」でこんらん・「うら」でねむり、ワザのコインは 1 枚、ログ `damage` がない、投げ直さない、相手が「ワザをうけない」状態なら HC3 でコインの前に止める
    （どの先読みの方法でも、状態・乱数・ログを変えない）、3 つの先読みの方法で同じ結果、受け付けないコマンド（エネルギー不足）でコインを使わない。
  - たいでん（`StaticChargeTest`）: 決定の形（種類・ワザを使ったプレイヤー・ちょうど 1 枚・選べるもの・再開先）、つける・手札からつける回数を変えない・ログ `damage` がない・
    番が終わる、選べるものがなければ何もしない、選べないカード・0 枚・重複・相手プレイヤーの答えを拒否し状態を変えない、決定を待つあいだの複製・pickle・書き出しと再開、
    トラッシュのレインボーエネルギー（RB2）、クリスタルビームを受けた番、3 つの先読みの方法で同じ結果、不変条件（カードの保存則）と書き出しの監査。
  - こうそくいどう・かくれる・みずでっぽう・テールドロップ（`ReusedTypeTest`）: ダメージ → コイン → `AttackBarrier` の順と「うら」、ダメージのないかくれる、多い「水」の数え方
    （上限 2・無色2個エネルギーを数えない・ニョロボンのハイドロポンプ）、ついているレインボーエネルギー（RB1）、テールドロップの 4 通りのコイン、3 つの先読みの方法。
  - PR1-069（`AncientMewTest`・`ExtractionCorrectionTest`・`RecordTest`）: 名前だけを訂正し、ほかの欄は kyuura のデータ、ほかのミュウと混ぜて 4 枚は受け付け 5 枚は
    `TOO_MANY_COPIES`、クイズの名前の候補が増えない、訂正の確かめ（誤った前の値・根拠・画像を見たという記録・記録の id・ほかの欄・ほかのカード・2 重の訂正を拒否する。
    kyuura がすでに同じ値なら二重に当てはめず知らせる。前後のどちらでもない値も知らせる）、研究の対応表の検査が訂正の記録のないとき・違う値のときに問題にする、
    採用の記録の `user_name_correction` の検査。
  - マチスの秘策の試すカード（`SecretPlanCandidatesTest`）。
- 既存の共通の境界テストに、v0.70 のワザを加えて走らせた: T19b（ゴーストの「とうめい」。tests/test_transparency_v0_9.py の `EvadedEffectCoinTest` に v0.70 の
  ParalyzeOnHeads・PoisonOnHeads・ConfuseOnHeads のワザ 24。サワムラーの「まわしげり」は最終ダメージが 0 なので止めない）・こんらんの 20（tests/test_unresolved_rulings_v0_3d.py。
  超・弱点 超の 7 枚は 40）・相手に効果を与える要素の宣言（tests/test_guts_v0_11.py。`StatusByCoinWithoutDamage`）。
- 正式な対戦開始からの対戦（`GameTest`。tools/existing_effect_games.py の `--batch v0.70`。W70・L70・C70・B70 の 4 組・2 seed・席の入れかえの 16 局）: 16 局すべて勝敗で終わり（`game_over`）、ログ・書き出し・観測の監査の問題 0、想定外の拒否・内部エラー 0。
  どのデッキも v0.70 のカードと前の版のカードを混ぜ、同じ名前は版をまたいで 4 枚まで（C70 は PR1-069 と PMCG3-033 のミュウを 2 枚ずつ）。デッキに入れたのは 82 枚のうち 60 枚。
  使われたワザ（16 局）: GD3-002 たいでん・ES1-017 ぐるぐる／のしかかり・SI-001 かじる／こうそくいどう・GD2-014 みずでっぽう／バブルこうせん・ES1-018 メガトンパンチ／ハイドロポンプ・PR1-066 みずでっぽう・ES3-033 かみつく／テールドロップ・PR1-069 Psyche(サイケ)・GD1-004 ぜんしんばり／サンドストーム・GD1-008 いわなげ・GD6-006 まとわりつく・GD5-013 きあいづき・PF2-004 でんこうせっか／サイケこうせん・NIP1-024 たいあたり／ねむりごな・NIP2-026 たいあたり／でんきショック・NIP2X-004 あやしいひかり ほか（v0.70 のワザ 54。tests の USED_IN_GAMES に代表 15 を固定）。たいでんは 2 回使われたが、どちらもトラッシュに「雷」エネルギーカードがなく何もつけなかった。テールドロップは 4 回とも失敗した。
  カツラのポニータの「こうそくいどう」は使われなかった（つける場合・成功する場合・ポニータは単体テストで確かめた）。デッキに入れなかった 22 枚（ES1-004・ES1-008・ES1-012・
  ES2-008・ES2-009・GD2-005・GD2-009・GD3-013・IP1-001・IP1-016・IP1-030・IP2-039・NIP1-008・NIP1-016・NIP2-003・PR1-011・PR1-014・PR1-045・QSG-006・QSG-014・SI-006・
  SI-009）は、登録・型とパラメーターの表・データの照合だけで確かめた（同じ型の仕組みは前の版の対戦と単体テストで確かめてある）。大量の seed の探索・勝率の評価はしていない。
- v0.69 との別のプロセスでの比較（7.2 節）。
- 変異試験の定義の確かめ（`python3 tools/run_mutants.py check`。50 件すべて今のコードに入る。当たらなくなった定義はなく、証人を走らせ直す必要はなかった）。
- ruff: v0.69 の木は 486 件、v0.70 は 486 件（同じ指摘。v0.70 の変更で新しい指摘はない。新しいテストのファイルの読み込みの並び・使わない読み込み・文字列の split を直した。既存の指摘は直していない）
- 全体のテスト: 最終のコードで 1 回（走らせている間はファイルを変えない）。結果はコミットのメッセージに書いた。

### 7.2 v0.69 との比較（別のプロセス）

固定した v0.69（`f7a2ad8`）と、別の木・別のプロセスで比べました。写しの元のコミットは同じ（7d3f4ca）なので、写しの元の移行（v0.69 の `--card-data-commit`）は使っていません。

| 比べたもの | 結果 |
|---|---|
| 1 歩ごとの比較（tools/engine_lockstep.py。対戦のテストの 20 seed・ストレス実行の 10 seed） | 760 対戦・136,537 歩で食い違い 0（許した差 0） |
| 検証用デッキの対戦（v0.28〜v0.69 の組・2 seed・席の入れかえ。終わり方・手数・コマンド・状態・ログ・乱数・観測・結果） | 620 局（v0.69 の組を含む）。609 局はすべて同じ。11 局（v0.63 の組。カツラのクイズ その3 のある対戦）は、コマンドだけが違い、状態・ログ・乱数・観測・結果は同じ |

- 違った 11 局のコマンドは、どれもクイズの答えの決定（`quiz_answer`）への答えで、違ったコマンドの数（合わせて 35）は、それぞれの局のクイズの答えの数と同じでした。答えの選べるもの（名前の
  候補）に v0.70 の新しい名前 21 種類が加わって並びが変わったので、同じ名前を選ぶ答えの位置（`choices` の値）が変わりました。ログのクイズの記録（`quiz_hint`・`quiz_answer`（答えた名前）・
  `quiz_reveal`）は 11 局すべてで同じで、状態・乱数も同じです（対戦の手順は名前で答えを選ぶ。scratchpad の比べ）。差を一括で許したり、ログの項目を除いたりしていません。
- 変えた共通の処理（説明の書き方の一覧・新しい型・登録の値の共有・作り直しと検査の道具）を通る前の版のカードの組: ギャロップ・ライチュウ・シードラの「こうそくいどう」（v0.34・v0.37・v0.41）、
  エリカのナゾノクサの「へんなこな」（v0.41）、R団のサンダーの「プラズマ」（v0.45）の組はどれも上の 620 局に含まれ、すべて同じでした。

### 7.3 していないこと

- 82 枚のカードの画像・pcg-search.com のページの照合（新しい外部照合なし）。ガイドブックの読み直し。PR1-069 の補助資料の URL の本文の取得・検証。
- 変異試験のすべての実行・Python の複数の版・性能の測定（具体的な新しい懸念がない）。
- 大規模な全バッチの反復（v0.28〜v0.69 の組は 2 seed だけ）。
- 固定のデッキの変更・カードの強さの評価。

## 8. 限界・報告事項

- kyuura への報告事項: PR1-069 の名前「？？？」（利用者の同定では「ミュウ」。エンジンは写しの作り直しで訂正を当てはめている。docs/data-provenance.md）。
- 対象外（作業を広げていない）: GD5-007「カツラのウィンディ」と IP2-032「ウィンディ」は、対応済みの「カツラのウインディ」「ウインディ」と表記が違い、名前の完全一致による同じ名前
  4 枚の制限では別の名前になります。kyuura の訂正の候補は進化への影響なしを記録していますが、これらの版を混ぜるときの同じ名前の制限は別に検討が要るので、データを黙って
  直したり、別の名前のまま 4 + 4 枚を受け付けたりしていません（どちらも未対応のまま）。
- マチスの秘策: 6 章の試す回数の上限（529 > 512 になりうる経路）。
- 新しい論点・停止コードはありません（停止コード 149・未解決の裁定 151 のまま。維持することを目的にしたのではなく、新しい問いが起こらなかった）。
