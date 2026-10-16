# v0.39: じばく・控えへのダメージ・場のポケモンの数でダメージが決まるワザの 15 枚

v0.38（`0f6f601`。版 0.38.0）から作業ブランチ `claude/v0.39-selfdestruct-spread-count` を作り、依頼の 15 枚を加えました（版 0.39.0）。

1. 依頼の 15 枚（【じばく】コイル PMCG1-036・レアコイル PMCG1-039・マタドガス PMCG3-006・レアコイル PMCG3-025、【控えへのダメージ】ピカチュウ PMCG2-024・
   ライチュウ PMCG3-024・マルマイン PMCG2-025・キョウのドガース PMCG6-008・カスミのニョロボン PMCG6-039、【場の数によるダメージ】コイル PMCG4-026・
   プクリン PMCG2-045・ニドクイン PMCG2-013、【既存の要素の組み合わせ】キョウのマタドガス PMCG6-016・ポッポ PMCG1-059・エリカのパラス PMCG5-004）を、どのワザも
   登録して対応にした（1 章。保留なし。特殊能力を持つカードはない）。対応ポケモン 194 → 209、ワザの登録 343 → 368（特殊能力 12 のまま）、写し 215 → 230 枚。
2. 必要な共通の処理を、既存の要素の組み合わせと、要素の小さな項目の追加で加えた（3 章）。新しい要素は、相手の控えから最大 N 匹を選ぶ `ChosenBenchDamages` と、
   場のポケモンの数を基本となるダメージに加える値 `PrintedPlusPokemonCount` の 2 つだけ。控えへのダメージの要素 `BenchDamage` には、受ける控えをタイプでしぼる
   項目（相手の対戦ポケモンと同じタイプ・あるタイプ以外）を、相手の控えを 1 匹選ぶ要素 `ChosenBenchDamage` には、説明に弱点・抵抗力の記述がない場合（JS1 を
   選ぶ控えごとに確かめる）を加えた。
3. ライチュウ（化石の秘密）の「ギガスパーク」の「相手の控えポケモンから最大3匹を選び」で、相手に控えがいるときに 0 匹を選べるかは記録から決まらないので、
   0 匹の答えを決定の答えのときに止める（新しい未解決 GS1。`UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE`。5 章）。停止コード 44 → 45、未解決の裁定 45 → 46。
   第1弾のじばく・スパーク・ビリビリの、説明に「弱点・抵抗力」に関係なくのない控えへのダメージは、v0.37 の JS1 と同じ問い・同じコードで、新しい問いを加えて
   いない（6 章）。

開始の時点で、作業ツリーに未コミットの変更はなく、v0.38 のあとの保守の変更もありませんでした（`git fetch` のあと、`main`（`f50a9ab`）は `0f6f601` の祖先で、
`claude/v0.38-bench-switch-combined` は `0f6f601` のまま。リモートに v0.39 のブランチはない）。ガイドブック（『オフィシャルブック2000』）のキャプチャ・OCR・画像の
読み直しは行っていません。読んでいない原典を確かめたことにする記録は作っていません。足りない裁定を現代のルールから推測して決めていません。今回の作業に関係しない
未解決と、保留中のガルーラ（PMCG2-046）・ベロリンガは再調査していません。研究の基準（kyuura `3f34908`）・写しの元（`ecb2d69`）・固定した参照データ・公開の
固定のデッキは変えていません。`engine.py`・`resolution/` にカード id での分岐を加えていません（tests/test_selfdestruct_spread_count_v0_39.py の
`test_no_card_specific_branch_in_the_engine`）。

## 1. カードごとの結果

15 枚とも対応にしました。どのワザも登録し、ワザの一部だけの登録はありません。15 枚とも kyuura データの採用（`card_sources.json` の `basis: kyuura_data`）で、
処理に使う文面は kyuura の印刷の文面です（研究の基準のコミットに、15 枚を指す kyuura の最新の説明・エラッタ・論点・照合の記録はない。裁定は、レアコイル PMCG1-039
を `related_cards` に挙げる CR-TRANSPARENCY-BENCH・CR-TRANSPARENCY-MULTIPLE-TARGETS の 2 件だけで、その採用の記録の `kyuura_records` に書いた）。説明文のある
21 のワザを研究の対応表の `adopted_printed_text` に加えました。説明文のない 4 のワザは `DamageOnly` です。

| カード | id | 版（pcg-search.com の一覧の番号） | ワザ | 実装 | 結果 |
|---|---|---|---|---|---|
| コイル | PMCG1-036 | 第1弾 037/096 | でんじは（雷）10・じばく（雷無）40 | `ParalyzeOnHeads`・`SelfDestruct(40, 10, weakness_resistance_stated=False)` | 対応（ロケット団のコイル PMCG4-026 とは同じ名前の別のカード） |
| レアコイル | PMCG1-039 | 第1弾 038/096 | でんじは（雷雷無）30・じばく（雷雷無無）80 | `ParalyzeOnHeads`・`SelfDestruct(80, 20, False)` | 対応（コイルから進化。第1弾・ロケット団のどちらのコイルからも） |
| マタドガス | PMCG3-006 | 化石の秘密 007/048 | スモッグ（草草）20・じばく（草草無）60 | `PoisonOnHeads`・`SelfDestruct(60, 10, True)` | 対応（ドガースから進化。第1弾・ロケット団のどちらのドガースからも。キョウのマタドガスとは別の名前のカード） |
| レアコイル | PMCG3-025 | 化石の秘密 025/048 | ソニックブーム（雷無）20・じばく（雷雷雷雷）100 | `DamageIgnoringWeaknessResistance`・`SelfDestruct(100, 20, True)` | 対応（コイルから進化。サイトの文面は「弱点・抵抗カ」。2 章） |
| ピカチュウ | PMCG2-024 | ポケモンジャングル 024/048 | スパーク（雷雷）20 | `DamageThenChosenBenchDamage(10, weakness_resistance_stated=False)` | 対応（ワザは 1 つ。第1弾のピカチュウ PMCG1-035・マチスのピカチュウとは別のカード。選ぶ控えごとに JS1） |
| ライチュウ | PMCG3-024 | 化石の秘密 024/048 | ギガスパーク（雷雷雷雷）30 | `DamageThenChosenBenchTargets(3, 10)` | 対応（ピカチュウから進化。第1弾のライチュウ PMCG1-038 とは別のカード。0 匹は GS1） |
| マルマイン | PMCG2-025 | ポケモンジャングル 025/048 | たいあたり（無無）20・ビリビリ（雷雷雷）20 | `DamageOnly`・`DamageThenSameTypeBenchDamage(10)` | 対応（ビリリダマから進化。第1弾・ロケット団のどちらのビリリダマからも。わるいマルマインとは別のカード） |
| キョウのドガース | PMCG6-008 | 闇からの挑戦 014/098 | おならガス（草）10 | `DamageThenCoinBenchDamageBothSides(10)` | 対応（ワザは 1 つ。同じ名前の PMCG6-015（015/098。v0.36）とは別のカード） |
| カスミのニョロボン | PMCG6-039 | 闇からの挑戦 036/098 | ウォーターリング（水水無無）30 | `DamageThenOtherTypeBenchDamageBothSides(水, 10)` | 対応（カスミのニョロゾから進化する 2 進化。第1弾のニョロボンとは別のカード。サイトの文面は「弱点・抵抗カ」） |
| コイル | PMCG4-026 | ロケット団 026/065 | たいあたり（無無）20・ちょくれつじりょく（雷無）10+ | `DamageOnly`・`DamagePlusPokemonCount(10, own_bench, ("コイル", "レアコイル", "わるいレアコイル"))` | 対応（第1弾のコイルとは同じ名前の別のカード） |
| プクリン | PMCG2-045 | ポケモンジャングル 039/048 | こもりうた（無）・ともだちのわ（無無無）10+ | `PutToSleep`・`DamagePlusPokemonCount(10, own_bench)` | 対応（プリンから進化） |
| ニドクイン | PMCG2-013 | ポケモンジャングル 004/048 | ラブラブアタック（草無）20+・メガトンパンチ（草草無無）50 | `DamagePlusPokemonCount(20, own_in_play, ("ニドキング",))`・`DamageOnly` | 対応（ニドリーナ PMCG2-008 から進化する 2 進化。サカキのニドリーナからは進化できない） |
| キョウのマタドガス | PMCG6-016 | 闇からの挑戦 016/098 | とつぜんばくはつ（草草）10+・どくどくガス（草草無）20 | `CoinBonusDamageAndSelfDamage(30, 30)`・`DamageThenSpecialPoisonOnHeads(20)` | 対応（キョウのドガースから進化。PMCG6-008・PMCG6-015 のどちらからも） |
| ポッポ | PMCG1-059 | 第1弾 059/096 | かぜおこし（無無）10 | `DamageAndForceSwitch`（v0.4d のふきとばしと同じ型） | 対応（ワザは 1 つ。サイトのワザの名前は「ふきとばし」。2 章。キョウのポッポとは別の名前のカード） |
| エリカのパラス | PMCG5-004 | リーダーズスタジアム 009/096 | はさむ（無）10・きけんなほうし（草草） | `DamageOnly`・`CoinPoisonAndBenchDamage(10)` | 対応（ワザは 2 つ。第2弾のパラスとは別の名前のカード） |

進化は、印刷の「○○から進化」と名前が完全に一致するポケモンで照らします（コイル → レアコイル（2 種類とも）、ドガース → マタドガス、ピカチュウ → ライチュウ（化石の
秘密）、ビリリダマ → マルマイン、プリン → プクリン、カスミのニョロゾ → カスミのニョロボン、ニドリーナ → ニドクイン、キョウのドガース → キョウのマタドガス。収録の
弾では制限しない）。名前の似た別のカード（マチスのコイル → レアコイル、キョウのドガース → マタドガス、ドガース → キョウのマタドガス、マチスのピカチュウ →
ライチュウ、マチスのビリリダマ → マルマイン、ニョロゾ → カスミのニョロボン、サカキのニドリーナ → ニドクイン）からは進化できません（`EvolutionTest`）。

## 2. カードデータと pcg-search.com との照合

- 写しは既存の手順（`python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura`）で作り直しました（組 `pool_v0_39`。参照するコミット `ecb2d69` は変えていない）。
  ほかのカードの記録は変わっていません。15 枚とも kyuura の日本語の文面の出典（`ja_text_source`）は pcg-search.com ではありません（nazonobasho.com・ポケモン
  wiki）ので、pcg-search.com との照合は独立した照合です。
- pcg-search.com の同じ版のページと照合しました（2026-10-16。照合した欄は名前・段階・HP・タイプ・弱点・抵抗力・にげる・ワザの名前・エネルギー・ダメージ・
  説明文。カードの画像は読んでいない）。版はカード名だけでなく、収録とサイトの一覧の番号・HP・ワザで決めました。12 件は `match`、3 件は `differences`
  （どれも処理に影響しない。`affects_behavior: false`）です。
  - レアコイル（化石の秘密 025/048）の「ソニックブーム」・カスミのニョロボン（036/098）の「ウォーターリング」: サイトの文面は「弱点・抵抗カ」（「力」がカタカナの
    「カ」）。ほかは同じで、処理は変わらない（サイトの文字の違い。kyuura のデータは「弱点・抵抗力」のまま）。
  - ポッポ（059/096）: サイトのワザの名前は「ふきとばし」、kyuura は「かぜおこし」。説明文・エネルギー・ダメージは同じ。kyuura の CR-TRANSPARENCY-WHIRLWIND の注
    （p.159 の例がポッポのワザを「ふきとばし」とする。kyuura は「データの誤りとは決めていない（報告事項）」）と同じ違いです。登録は写しの名前「かぜおこし」で
    照らし、kyuura のデータ・写しは変えていません（kyuura への報告事項。11 章）。
  - 第1弾のコイル（037/096）とロケット団のコイル（026/065）、第1弾のレアコイル（038/096）と化石の秘密のレアコイル（025/048）、キョウのドガースの 014/098
    （HP40・おならガス）と 015/098（PMCG6-015）は、同じ名前の別のカードで、HP・ワザで版を決めました。マタドガス・レアコイル・ポッポ・ニドクインなど、サイトの
    一覧の番号が kyuura の id の番号と違うカードがあります（上の表）。
- 採用の記録（`card_sources.json`）は 15 件 `adopted`（`kyuura_commit` は `ecb2d69`、記録した日は 2026-10-16、説明文のあるワザの `play_text` は
  `kyuura_printed_text`）。過去の原典照合の記録（`card_verification.json`）には加えていません。ガイドブックの項目は書いていません。

## 3. 共通の処理

### 3.1 新しく加えた型

どれも解決の基盤の要素の並び（`programs.BUILDERS`）で処理し、v0.13 の約束（`resolve`・`resume`）は上書きしていません。`v013_checks.VERIFIED` には入れず、
tests/helpers.py の `ATTACK_TYPES_SINCE_V0_17` に加えました。型の `check` は、登録したワザの印刷の文面と同じ書き方だけを受け付けます（`TextTest`）。

| 型 | 要素の並び | 使うワザ |
|---|---|---|
| `SelfDestruct(self_damage, bench_damage, weakness_resistance_stated)` | `Damage(相手)` → `Damage(自分, self_damage)` → `BenchDamage(相手の控え)` → `BenchDamage(自分の控え)` | じばく 4 つ。第1弾の文面（「自分と相手に…お互いの控えポケモン全員にも」）は `weakness_resistance_stated=False`（控えへのダメージは JS1 で確かめる）、第3弾の文面（「自分にも…「弱点・抵抗力」に関係なく」）は `True` |
| `DamageIgnoringWeaknessResistance` | `Damage(相手, weakness_resistance=False)` | ソニックブーム（文面のワザの名前が登録のワザの名前と同じものだけ） |
| `DamageThenChosenBenchTargets(max_targets, bench_damage)` | `Damage(相手)` → `ChosenBenchDamages(最大 max_targets 匹)` | ギガスパーク |
| `DamageThenSameTypeBenchDamage(bench_damage)` | `Damage(相手)` → `BenchDamage(相手の控え, 同じタイプ, JS1)` → `BenchDamage(自分の控え, 同じタイプ, JS1)` | ビリビリ |
| `DamageThenCoinBenchDamageBothSides(bench_damage)` | `Coin` → `Damage(相手)` → `BenchDamage(相手の控え, おもて)` → `BenchDamage(自分の控え, おもて)` | おならガス（v0.38 の `DamageThenCoinBenchDamageEitherSide`（ふぶき。片方の控え）とは別の型。互いの文面を受け付けない） |
| `DamageThenOtherTypeBenchDamageBothSides(excluded_type, bench_damage)` | `Damage(相手)` → `BenchDamage(相手の控え, そのタイプ以外)` → `BenchDamage(自分の控え, そのタイプ以外)` | ウォーターリング（水以外） |
| `DamagePlusPokemonCount(per, scope, names)` | `Damage(相手, PrintedPlusPokemonCount)` | ちょくれつじりょく・ともだちのわ・ラブラブアタック（`scope` と `names` の組は、文面の書き方の表 `POKEMON_COUNT_TEXTS` にあるものだけ。ないものは作れない） |
| `CoinBonusDamageAndSelfDamage(bonus, self_damage)` | `Coin` → `Damage(相手, 目安 + おもてなら bonus)` → `Damage(自分, self_damage, おもて)` | とつぜんばくはつ（ダメージの候補は同じコインの組 `outcomes`。C18 などの先読みが組のまま試す） |
| `DamageThenSpecialPoisonOnHeads(poison_damage)` | `Damage(相手)` → `Status(どく, 要素のコイン おもて, poison_damage)` | どくどくガス（v0.34 のどくどく（コインなし）と同じ特殊などく。`opponent_effect_elements` はどく） |
| `CoinPoisonAndBenchDamage(bench_damage)` | `Coin` → `BenchDamage(相手の控え, おもて)` → `Status(どく, おもて)` | きけんなほうし（ダメージの目安なし。`opponent_effect_elements` はどく） |

既存の型の登録: でんじは（2 つ）は `ParalyzeOnHeads`、スモッグは `PoisonOnHeads`、こもりうたは `PutToSleep`、かぜおこしは `DamageAndForceSwitch`（v0.4d）、
スパークは v0.38 の `DamageThenChosenBenchDamage` に項目 `weakness_resistance_stated=False` を加えたもの（v0.38 のほのおのわは既定の `True` のまま）、説明文のない
4 つは `DamageOnly`。

### 3.2 要素に加えた項目と新しい要素

- `BenchDamage.same_type_as_opponent_active`: 受ける控えを、相手の対戦ポケモンと同じタイプのポケモンだけにする（ビリビリ）。`BenchDamage.exclude_type`: そのタイプ
  以外のポケモンだけにする（ウォーターリング）。タイプはどれも、この要素を処理する時点の場のポケモンのいちばん上のカードのタイプです（進化したポケモンは
  いちばん上のカード。相手の対戦ポケモンがワザのダメージで HP 以上になっていても、きぜつの処理の前なので、そのポケモンのタイプで決める）。既定は今までどおり
  （すべての控え）。
- `ChosenBenchDamage.weakness_resistance` に `None` を加えた（スパーク）。説明が弱点・抵抗力について書いていないとき、選べる控えのうち、計算するかどうかで最終
  ダメージが変わるポケモン（`kernel.weakness_resistance_matters`。v0.37 の JS1 と同じ関数）は、選べるが選ぶと止める（決定の `context` の `unresolved_choices`。
  v0.31 の HC9 と同じ形）。選べるどのポケモンでも変わるなら、宣言の前に止める（先読みが見つける）。選んだポケモンだけが受けるので、ほかの控えを選ぶ処理は
  止めない。既定の `False`（弱点・抵抗力なし）は今までどおり。
- 新しい要素 `ChosenBenchDamages(base, max_targets)`（ギガスパーク）: 選ぶのはワザを使ったプレイヤー（決定 `SELECT_POKEMON`。`min_choices` 0・`max_choices` は
  min(`max_targets`, 控えの数)。同じポケモンを 2 回選べない（`decisions.check_choices` の `DUPLICATE_CHOICE`））。控えがいなければ決定を出さない。0 匹の答えは GS1。
  ダメージの要素なので、前の要素の送る効果を決定をまたいで運ぶ（v0.34 の `carry`）。先読みは 1 匹以上のすべての答え（選ぶポケモン・数・順番）を試し、0 匹は試さない
  （`all_answers(decision, minimum=1)`。0 匹は答えのときに止めるもので、宣言を止める理由ではない）。
- 新しい値 `PrintedPlusPokemonCount(per, scope, names)` と関数 `counted_pokemon`: ダメージの目安の数字 + 数えた場のポケモンの数 × `per` を、p.321 の 1 段階の基本と
  なるダメージにする。数えるのはダメージの要素を処理する時点の場のポケモン（進化して重なったカードは 1 匹）で、名前はいちばん上のカードの `name_ja` の完全一致
  （名前の一部・収録の弾では見ない）。`scope` は `own_bench`（自分のベンチ）・`own_in_play`（自分の場。バトル場とベンチ）。実際の処理と先読み（C18・W24 などの
  ダメージの候補 `damage_profile`）は同じ関数で数える。

### 3.3 ログ・決定・状態

- 新しいログのイベント・決定の種類・持続する効果の型・状態の項目はありません。書き出しの形式は 10 のままです。じばくの自分の控えへのダメージはログ `damage` の
  `target` が `self_bench`（v0.33 から）、ギガスパークは選んだ数だけ `opponent_bench` のダメージのログが並びます。
- ログの監査（tests/log_audit.py）の特殊などくの量の確かめを、どくどくガス（`DamageThenSpecialPoisonOnHeads`）にも当てはめました（v0.34 は `DamageAndSpecialPoison`
  だけを見ていたので、どくどくガスでどく状態にしたログの量 20 を、通常のどくの 10 と比べて監査が失敗していた。エンジンの処理は正しく、監査の確かめの漏れ）。

### 3.4 解消した制限・再利用したもの

- 今回のカード群に必要な処理で、残したエンジンの制限はありません。15 枚の 25 のワザは、どれもまねるワザ（ピクシー・ピッピの「ゆびをふる」・カスミのコダックの
  「ちょうのうりょく」）としても処理します（7 章）。
- 再利用: v0.2f・v0.3d の自分へのダメージ（プラスパワー・ディフェンダー・弱点・抵抗力）、v0.2f の同時のきぜつ（サイド・バトル場に出す順番）、v0.4d の相手が選ぶ
  入れ替え、v0.3a の特殊などく、v0.34 の `void_coin_question`・決定をまたいで運ぶ送る効果、v0.37 の JS1、v0.38 の `Element.has_target`（コインが決める要素に
  対象がなければ投げない）。

## 4. 規定と根拠

どれも既存の記録の再利用と印刷の文面で決めました（ガイドブックは読んでいない）。記録で決まらない場面は 5 章の GS1 と、6 章の既存の問いだけです。

| id | 規定 | 根拠 | テスト |
|---|---|---|---|
| SD1 | じばくの要素の順番は、相手の対戦ポケモン → 自分 → 相手の控えの全員 → 自分の控えの全員。ワザの途中ではきぜつの処理・番の終わりをしない（すべての要素のあと） | 印刷の文面の順。p.309・p.324（きぜつはワザのあと）。どの要素も場を変えない（きぜつの処理はワザのあと）ので、順番で結果は変わらない | `SelfDestructTest.test_order_amounts_and_targets` |
| SD2 | じばくの自分へのダメージは、ワザによる自分へのダメージ（p.320 の (3)）で、ワザを使うポケモンのタイプと自分の弱点・抵抗力・プラスパワー・ディフェンダーを計算する。のっているダメージに加え、HP 以上になればワザのあとできぜつする。残りの HP に関係なく自分をきぜつさせる処理にしない（ディフェンダーをつけたコイルは 20 を受けて残る） | v0.2f（p.257 の解説。SUPPORTED）・v0.3d（p.90 の解説。SUPPORTED） | `test_self_damage_is_calculated_not_an_automatic_knock_out`・`CopyTest.test_self_destruct_copied_hurts_the_copier` |
| SD3 | 第1弾のじばく（コイル・レアコイル PMCG1-039）の控えへのダメージは、説明に弱点・抵抗力の記述がない。どちらかの控えに、読み方で受けるダメージが変わるポケモンがいれば JS1 で宣言の前に止める。いなければ止めない（結果は同じ） | v0.37 の JS1（同じ問い・同じコード。6 章） | `test_first_set_bench_damage_follows_js1` |
| SD4 | 第3弾のじばく（マタドガス・レアコイル PMCG3-025）の控えへのダメージは弱点・抵抗力を計算しない。相手の対戦ポケモンへのダメージは計算する（説明が控えのダメージだけに書く） | 印刷の文面「お互いの控えポケモン全員にも、「弱点・抵抗力」に関係なく」 | `test_fossil_bench_damage_ignores_weakness_and_resistance` |
| SD5 | 両方の対戦ポケモン・控えがきぜつしたら、サイドは番のプレイヤーから取り（同時のきぜつの正規化）、バトル場に出すのは番でないプレイヤーから。自分に控えがいなければ、サイドを取ったあとの判定で負ける | v0.2f（p.323〜p.325・p.311） | `test_double_knock_out_prizes_and_promotion_order`・`test_attacker_without_bench_loses_after_the_prizes` |
| SD6 | 相手の対戦ポケモンが「ダメージを受けない」状態なら、そのポケモンへの要素だけが無効で、自分・控えへのダメージは処理する。相手の「はんげき」（バトル場・控えのどちらのカイリキーも）はダメージの要素をすべて処理したあとで、じばくですでに HP 以上なら与えない（`counterattack_skipped`）。じばくは「ダメージ → 入れ替え → 自分にも」の並びではないので GK1 に当たらない | p.321・v0.4b。CR-COUNTERATTACK-TIMING・v0.10 の C15。GK1 は v0.38 のげきとつの並びだけ（6 章） | `test_prevented_or_barrier_opponent_still_takes_self_and_bench_damage`・`test_counterattack_is_skipped_when_the_attacker_is_already_knocked_out` |
| SD7 | 控えのゴースト（化石の秘密）の「とうめい」は、じばくの控えへのダメージを受けるときも判定する（受けるポケモンごと。ゴーストだけがコインを投げる）。2 匹以上なら T27 | kyuura の CR-TRANSPARENCY-BENCH・CR-TRANSPARENCY-MULTIPLE-TARGETS（kyuura が p.159 の解説を読んだ記録。レアコイルの「じばく」の例）。v0.9 の T7・T27 | `test_transparency_on_bench_is_judged` |
| SB1 | ソニックブームが受けないのは、相手の弱点・抵抗力（p.321 の 3・4 段階）だけ。プラスパワー・ディフェンダー・「ダメージを受けない」状態・「とうめい」は今までどおり | 印刷の文面「相手の「弱点・抵抗力」の影響を受けない」。p.321 | `SonicBoomTest` |
| SP1 | スパーク: 相手の対戦ポケモンに 20 のあと、ワザを使ったプレイヤーが相手の控えを 1 匹選び 10。相手に控えがいなければ「この効果はない」ので決定を出さない | 印刷の文面。v0.38 のほのおのわ（BC3） | `SparkTest.test_chooser_options_and_amounts`・`test_without_opponent_bench_only_the_active_takes_damage` |
| SP2 | スパークの控えへのダメージは、説明に弱点・抵抗力の記述がない。読み方で受けるダメージが変わる控えは、選べるが選ぶと JS1（決定は待ったまま）。どの控えでも変わるなら宣言の前に JS1 | v0.37 の JS1。選んだ控えだけが受ける（ほかの控えの処理は記録で決まる） | `test_js1_only_for_the_choices_whose_result_differs`・`test_every_choice_differs_stops_before_the_declaration` |
| GS2 | ギガスパーク: ワザを使ったプレイヤーが、相手の控えから 1〜min(3, 控えの数) 匹を選び、それぞれに弱点・抵抗力に関係なく 10。同じポケモンを 2 回選べない。相手に控えがいなければ決定を出さない。0 匹は GS1（5 章） | 印刷の文面（「最大3匹を選び」「それぞれ」）。p.309（対象がない） | `GigaSparkTest` |
| TB1 | ビリビリの「同じ色」はタイプ。お互いの控え（「(自分の控えポケモンも含まれる)」）の、相手の対戦ポケモンと同じタイプのポケモン全員に 10 | 印刷の文面。p.311 の「どの色（タイプ）のエネルギー」（v0.3c の docs/confusion-v0.3c.md に記録した p.311 の文。色とタイプを同じものとして書く） | `TypeFilteredBenchTest.test_thunder_jolt_hits_same_type_bench_on_both_sides` |
| TB2 | タイプは、この要素を処理する時点の、いちばん上のカードのタイプ（相手の対戦ポケモン・控えのどちらも） | p.310（進化したポケモンの情報はいちばん上のカード。CLAUDE.md の進化の約束） | `test_type_is_the_current_top_card_type` |
| TB3 | ビリビリの控えへのダメージは、説明に弱点・抵抗力の記述がない。受ける控えのどれかで読み方で結果が変われば JS1 で宣言の前に止める | v0.37 の JS1 | `test_thunder_jolt_js1` |
| WR1 | ウォーターリング: お互いのベンチの「水」以外のポケモン全員に、弱点・抵抗力に関係なく 10。相手の対戦ポケモンへの 30 は弱点・抵抗力を計算する | 印刷の文面 | `test_water_ring_hits_every_non_water_bench` |
| FG1 | おならガス: 1 枚のコイン。「おもて」ならお互いの控え全員に弱点・抵抗力に関係なく 10。お互いに控えがいなければ、コインが決める要素に対象がないので投げない。どちらかにいれば投げる | 印刷の文面。v0.38 の `has_target`（p.309） | `FartGasTest` |
| CT1 | 場のポケモンの数で決まるダメージは、基本となるダメージ（p.321 の 1 段階）。弱点・抵抗力・プラスパワー・ディフェンダーは、そのあとの段階 | 印刷の文面（「…ダメージを追加する」）。p.321 | `CountDamageTest.test_count_is_the_base_damage_before_weakness_and_pluspower` |
| CT2 | 数えるのは場のポケモン（進化して重なったカードは 1 匹）で、名前はいちばん上のカードの名前の完全一致。ちょくれつじりょくは自分のベンチの「コイル」「レアコイル」「わるいレアコイル」（対応していないわるいレアコイルも名前のまま数える。マチスのコイルは名前が違うので数えない）、ともだちのわは自分の控えポケモンすべて、ラブラブアタックは自分の場（バトル場とベンチ）の「ニドキング」 | 印刷の文面。p.310（進化したポケモンは 1 匹） | `test_magnemite_chain_counts_only_the_named_bench_pokemon`・`test_friendship_ring_counts_every_own_bench_pokemon`・`test_lovely_attack_counts_own_nidoking_in_play` |
| CT3 | 数えるのはダメージの要素を処理する時点。実際の処理と、宣言の前の先読み（C18 などのダメージの候補）は同じ関数で数える。まねるワザでは、まねたポケモンの側の場を数える | v0.15c・v0.16c の先読みの約束 | `test_preflight_uses_the_same_count`・`CopyTest.test_counts_are_taken_on_the_copier_side`・`PreflightParityTest` |
| EX1 | とつぜんばくはつ: 1 枚のコインで、「おもて」なら 30 を追加し（40）、自分にも 30。「うら」なら 10 だけ。要素ごとに投げ直さない。相手が「ダメージを受けない」状態でも、自分へのダメージ（有効な要素）があるのでコインを投げる | 印刷の文面。v0.34 の `void_coin_question` | `SuddenExplosionTest` |
| TG1 | どくどくガス: 20 のあと 1 枚のコインで、「おもて」なら特殊などく（ポケモンチェックで 20）。通常のどくを 2 回にしない。通常のどくのポケモンへは v0.34 の TP3、「ワザをうけない」相手へは v0.31 の HC3（コインの前） | 印刷の文面。v0.3a の 13（特殊などく）・15（TP3）・14 | `ToxicGasTest` |
| DS1 | きけんなほうし: 1 枚のコインで、「おもて」なら相手の控え全員に弱点・抵抗力に関係なく 10 のあと、相手の対戦ポケモンをどく。「うら」なら何もしない | 印刷の文面。p.309 の手順 6（ダメージのあとにダメージ以外の効果。v0.4d の記録） | `DangerousSporeTest.test_heads_bench_then_poison_tails_nothing` |
| DS2 | きけんなほうしの片方の要素だけが無効・対象なしの場合: 控えがいなくても、どくに対象があるので投げ、「おもて」ならどくだけ。相手がバリアーでも、控えへのダメージ（有効）があるので投げ、どくは受けない。相手が「ダメージを受けない」状態でも、どく（ダメージ以外の効果）は受ける。バリアーで控えもいなければ HC3 | v0.34 の `void_coin_question`・v0.38 の `has_target`・v0.4b・v0.31 の HC3 | `test_one_side_without_target_or_void` |
| WG1 | かぜおこし: 10 のあと、相手が選ぶ控えと入れ替える。相手に控えがいなければダメージだけ（`forced_switch_skipped`） | 印刷の文面（v0.4d のふきとばしと同じ説明）。v0.4d の F3 | `GustTest` |

## 5. GS1: ギガスパークの「最大3匹」で 0 匹を選べるか

| 項目 | 内容 |
|---|---|
| 問い | 相手の控えポケモンがいるとき、ギガスパークの「相手の控えポケモンから最大3匹を選び」で 0 匹を選べるか（控えへのダメージを与えないことを選べるか） |
| 記録で確かめたこと | kyuura の研究の基準のコミット（`3f34908`）に、ギガスパーク・化石の秘密のライチュウを指す記録はない。エンジンの記録で同じ言い回しの問いは、v0.9 のエナジーへんかんの H4（「最大2枚」の 0 枚）と v0.23 のエネルギー回収の ER9（「最大2枚」の 0 枚）で、どちらも記録から決まらず未解決（UNRESOLVED） |
| 決まらない理由 | 説明の「最大3匹」は上限だけを書き、下限を書いていない。0 匹を選べれば控えへのダメージを与えないことになり、選べなければ 1 匹以上に与える。H4・ER9 は別のカードの問いで、それらの答えでこの問いを決めない（CLAUDE.md の約束。現代のルールからも推測しない） |
| 処理 | 相手に控えがいるとき、決定（`SELECT_POKEMON`）は `min_choices` 0 で出し、0 匹の答えを `UnsupportedError`（`UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE`）で止める。決定は待ったままで、状態・乱数・ログは変わらない（1 匹以上を選び直せる）。相手に控えがいなければ決定を出さない（処理の対象がない。p.309） |
| 影響の範囲 | ギガスパーク（自分のワザ・まねるワザ）の 0 匹の答えだけ。1〜3 匹の答え・ほかのワザは止めない。宣言は止めない（1 匹以上を選べば処理できる。先読みは 0 匹を試さない） |
| 研究の対応表 | `stop_codes` の `UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE`（`kyuura_disposition: not_in_kyuura`。kyuura の未解決の一覧にない。kyuura への報告事項） |
| テスト | `GigaSparkTest.test_zero_targets_is_gs1_and_the_decision_waits`・`CopyTest.test_giga_spark_copied_keeps_gs1`・`IntegrityTest.test_rejections_keep_the_state`・tests/test_unresolved_boundaries_v0_4e.py |

## 6. 既存の問いとの関係（JS1・GK1・C18・C34/C35・T27・TP3・HC3）

- **JS1**（v0.37。説明に「弱点・抵抗力」に関係なくのない控えへのダメージ）: 第1弾のじばく（お互いの控え）・スパーク（選んだ控え）・ビリビリ（同じタイプの控え）が
  当たります。同じ問い（`bench_damage_weakness_resistance`）・同じコード（`UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE`）で、新しい問いを加えていません。止めるのは、
  受ける控え（スパークは選んだ控え）のどれかで、計算するかどうかで受けるダメージが変わるときだけです（変わらなければ、どちらの読み方でも結果は同じ）。問いの理由の
  文は v0.37 のじしんを例に書いた文のまま、止めた控えのポケモンの番号を加えます。第3弾のじばく・ギガスパーク・おならガス・ウォーターリング・きけんなほうしは
  説明に「弱点・抵抗力」に関係なくがあるので当たりません。
- **GK1**（v0.38。ダメージ → 入れ替え → 自分にもの並びで「ダメージを受けたとき」の効果がはたらく）: じばく・とつぜんばくはつは、自分へのダメージの前にダメージ
  以外の効果をはさまない（ダメージの要素だけが続く）ので、記録の時点（ダメージの処理をすべてのせたあと、かつダメージ以外の効果の前）がそのまま当てはまります。
  GK1 の問いは v0.38 の並びのワザだけに当てはまり、今回のワザに一律に当てはめていません（`test_counterattack_is_skipped_when_the_attacker_is_already_knocked_out`。
  はんげきがはたらいても止まらない）。
- **C18・W24**（「ダメージを受けたとき」の効果による同時のきぜつ）: 場の数で変わるダメージ・ギガスパークの選ぶ控えごとに、今までどおり宣言の前に確かめます
  （`test_preflight_uses_the_same_count`・`test_each_choice_is_checked_separately_in_the_preflight`。選ぶ控えで結果が違えば、先読みは同じものとみなさない）。
- **C34/C35・T27**（2 つ以上の「ダメージを受けたとき」の効果・2 匹以上の「とうめい」）: 控え全員・選んだ控えへのダメージで起こりうる場面は、v0.31 からの停止
  コードのままです（今回の対戦のデッキには該当するポケモンがいない）。
- **TP3**（v0.34。受けるダメージの違うどく状態から特殊などく）・**HC3**（v0.31。「ワザをうけない」相手への効果だけを決めるコイン）: どくどくガス・きけんなほうしに、
  該当する場面だけで当てはめました（4 章の TG1・DS2）。

## 7. まねるワザ

ピクシー・ピッピ（「ゆびをふる」）・カスミのコダック（「ちょうのうりょく」）が、15 枚の 25 のワザをまねる場合を確かめました（`CopyTest`）。

- 25 のワザ × 3 匹のどれも、内部のエラーにならず処理します（今回の盤面ではどれも受け付けた。決まったコードの拒否もなかった。拒否のときは `UNRESOLVED_`・
  `UNSUPPORTED_` のコードであることを確かめる）。使うための条件のあるワザはないので、選べるかの条件（ピクシーの「使えない」・ピッピの「説明にしたがう」・カスミの
  コダックの HC9）で選べなくなるワザはありません。
- 自分へのダメージ・自分の控えへのダメージ（じばく・とつぜんばくはつ）はまねたポケモンの側、数える場（ちょくれつじりょく・ともだちのわ・ラブラブアタック）も
  まねたポケモンの側です。JS1 は、まねたポケモンのタイプで確かめます（ピクシー・ピッピは無色で、無色の弱点・抵抗力を持つカードはない）。ギガスパークの 0 匹は
  まねても GS1 です。
- エンジンの未対応として記録したもの（`UNSUPPORTED_COPIED_ATTACK` など）は、今回のワザにはありません。

## 8. 対戦

正式な開始（`new_game`・60 枚・サイド 6 枚）からの小規模な対戦で、15 枚の登場・進化・25 のワザと、そのあとの対戦の継続を確かめました（tests/test_selfdestruct_spread_count_v0_39_games.py。
`python3 tools/existing_effect_games.py --batch v0.39`）。seed を探し回っていません（最初の 6 つの seed）。勝率・カードの強さ・デッキの釣り合いは評価していません。

- 検証用デッキ（tools/existing_effect_games.py。公開の固定のデッキ・前の版の検証用デッキには入れていない。同じ名前のカードは合わせて 4 枚まで）:
  - `L39`（雷）: コイル（第1弾・ロケット団）2 枚ずつ・レアコイル（第1弾・化石の秘密）2 枚ずつ・ピカチュウ（ジャングル）4・ライチュウ（化石の秘密）3・ビリリダマ
    （第1弾）4・マルマイン 3、トレーナー 12、雷エネルギー 26
  - `G39`（草）: キョウのドガース（PMCG6-008）4・キョウのマタドガス 3・ドガース（第1弾）4・マタドガス（化石の秘密）3・エリカのパラス 4、トレーナー 12、草エネルギー 30
  - `C39`（無色・水）: ポッポ 4・プリン 4・プクリン 3・カスミのニョロモ 4・カスミのニョロゾ 3・カスミのニョロボン 2、トレーナー 12、水エネルギー 28
  - `N39`（草）: ニドラン♀ 4・ニドリーナ 3・ニドクイン 3・ニドラン♂ 4・ニドリーノ 3・ニドキング 2、トレーナー 12、草エネルギー 29
- 組（`PAIRINGS_V0_39`）: `L39` 対 `C39`・`C39` 対 `G39`・`G39` 対 `N39`・`N39` 対 `L39`。席を入れかえて seed 0〜5（48 局）。
- 手順: v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順と、使っていないワザのためにエネルギーをためる手順（v0.38 と同じ）を重ね、
  スパーク・ギガスパークの控えの選び方（JS1 の選択を避ける。ギガスパークは 1・2・3 匹を順に選ぶ。0 匹は選ばない）を加えた（対戦相手の AI ではない）。JS1・TP3
  で止まったワザは、場から確かめてから別の操作を続ける（`V031_STOPS`。JS1 の確かめを第1弾のじばく・ビリビリ・スパークに、TP3 の確かめをどくどくガスに広げた）。

| 終わり方 | 局数 |
|---|---|
| 通常の勝敗（`game_over`） | 43 |
| サドンデス（`sudden_death`） | 3 |
| 既知の裁定による停止（`halted`。対戦準備の `UNRESOLVED_MULLIGAN_COMPENSATION`） | 2 |
| 手数の上限・想定外の拒否・内部エラー・監査の失敗 | 0 |

- `UNRESOLVED_…` でワザの宣言を拒否されたあと、別の操作で続けた回数: JS1 が 6 回（`L39` 対 `C39`。控えのポッポ（雷に弱点）があるときの第1弾のじばく 2 回・
  ビリビリ 4 回）。GS1 は起こらない（手順が 0 匹を選ばない。境界は単体テスト）。
- 15 枚がどれも場に出て（進化先 9 枚は通常の進化の操作で）、25 のワザがどれも使われました。じばくの自分へのダメージとお互いの控えへのダメージ、スパーク・
  ギガスパーク（1・2・3 匹）・ビリビリ・おならガス・ウォーターリング・きけんなほうしの控えへのダメージ、ともだちのわ（基本となるダメージ 20〜60）・ラブラブ
  アタック（20・40・60）の数で変わるダメージ、とつぜんばくはつの両面（10・40 と自分への 30）、どくどくガスの特殊などく（ポケモンチェックで 20）、かぜおこしの
  入れ替えが起こりました。どの局も、受け付けた操作の列を `new_game` からやり直したログが同じで、不変条件・ログの監査・書き出しの監査が通りました。
- ちょくれつじりょくは 48 局で 1 回（そのとき自分のベンチにコイル・レアコイルはいなかった。数えたダメージの境界は単体テスト `CountDamageTest`）。対戦のデッキは
  雷のポケモンの控えに雷の弱点・抵抗力を持つポケモンがいないので、自分の控えでの JS1 は単体テストで確かめました。

## 9. 互換性

- 公開の API・状態・書き出しの形式（10）・ログのイベントの種類・決定の種類・持続する効果の型は変えていません。
- 既存の型・要素に加えた項目は、どれも既定の値で今までの動作のままです（`BenchDamage` の 2 項目、`ChosenBenchDamage.weakness_resistance` の `None`、
  `DamageThenChosenBenchDamage.weakness_resistance_stated` の既定 `True`）。v0.38 のほのおのわの登録は変えていません。
- 既存の動作の変更はありません。ログの監査（テストの道具）の特殊などくの確かめを、どくどくガスに広げただけです（3.3 節）。
- 前の版のテストのうち、全体の数（停止コード・未解決の裁定・登録の数・写しの組・採用の記録の数）を確かめるテストの期待を、v0.39 の数に直しました
  （tests/test_effects.py・test_cards.py・test_card_sources.py・test_cd4_opponent_energy_coins_v0_33.py・test_research_links_v0_18e.py・
  test_unresolved_boundaries_v0_4e.py・test_guts_v0_11.py・test_transparency_v0_9.py）。v0.38 のテストからは、後の版で増える全体の数の確かめを外しました（全体の数は
  tests/test_cd4_opponent_energy_coins_v0_33.py と tests/test_research_links_v0_18e.py が確かめる）。
- 固定した v0.38 との比較の結果は 10.2 節。

## 10. 検証

### 10.1 テスト

- 単体テスト（tests/test_selfdestruct_spread_count_v0_39.py。66 件）: カードの登録と記録・説明の文面・進化・じばく・ソニックブーム・スパーク・ギガスパーク・
  タイプでしぼる控えへのダメージ・おならガス・場のポケモンの数・とつぜんばくはつ・どくどくガス・きけんなほうし・かぜおこし・まねるワザ・不変条件と書き出しと
  保存と拒否の原子性・先読みの 3 つの方法の一致と 1 枚のコイン・文書。
- 正式な開始からの対戦（tests/test_selfdestruct_spread_count_v0_39_games.py。6 件・48 局）: 8 章。

### 10.2 固定した v0.38 との比較

最終のコードで、固定した v0.38（`0f6f601`。`tools/engine_lockstep.py tree` で展開した木）と、別のプロセスで比べました。比較の差を包括的に許す設定はしていません。

| 比較 | 範囲 | 結果 |
|---|---|---|
| `tools/engine_lockstep.py record --corpus all --seeds 10 --stress-seeds 2 --save-every 7` → `compare` | 290 局・48,092 歩（v0.38 までの自然な対戦・ストレス実行の組。保存と復元 5,068 回を含む） | 食い違い 0・許した差 0 |
| 前の版の検証用デッキの対戦（作業用の道具。各木の公開の API と、その木の tools/existing_effect_games.py だけを読み込み、受け付けた操作の列・最後の状態（形式 10）の指紋・ログ・乱数・拒否の数を比べる） | `--batch` v0.28〜v0.38 の 36 組 × 席の入れかえ × seed 0〜4 = 360 局・45,691 歩 | 違い 0 |

### 10.3 検査

| 検査 | 結果 |
|---|---|
| `python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura --check` | kyuura `ecb2d69` と一致 |
| `python3 scripts/check_card_sources.py` | 記録 152 件。方針と合っている |
| `python3 scripts/check_research_links.py --kyuura ../kyuura` | 研究の基準 `3f34908` の記録と一致 |
| `ruff check --select F,E9 .` | All checks passed |
| `python3 tools/run_mutants.py check`（変異の定義が今のコードに入るか） | どの変異も ok（M10 は直したあと。下の注） |
| `python3 tools/run_mutants.py witness M10` | 元のコードで証人のテスト 2 件が通り、変異で 2 件とも失敗する |

M10（v0.15d。エナジーへんかんの先読みの答えを代表だけにもどす変異）の置きかえる前の文字列 `return all_answers(decision, minimum=1)` が、ギガスパークの
`ChosenBenchDamages.dry_choices` にも現れて 2 か所になり、変異が入らなくなりました（全体のテストの tests/test_mutation_definitions_v0_18e.py で見つけた）。変異を消さず、
エナジーへんかんの行の直前の注を含めた文字列にして、同じ誤りを今のコードに入れるように直しました（tools/mutants.py。CLAUDE.md の v0.18 の約束）。

### 10.4 全体のテスト

最終のコード（M10 を直したあと）で `python3 -m unittest` を走らせ、2,775 件 OK（skipped 1）でした。M10 を直す前の 1 回目は、tests/test_mutation_definitions_v0_18e.py の
M10 が入らない 1 件で失敗しました（10.3 節の注）。

### 10.5 行っていないこと

- 変異試験の実行（`witness`・`full`）・性能の測定・複数の Python での実行は、依頼のとおり行っていません。
- ガイドブックの読み直し・pcg-search.com 以外の外部照合は行っていません。

## 11. 未解決・限界・報告事項

- 新しい未解決の裁定は GS1 の 1 件（5 章）。エンジンが止める `UNRESOLVED_…` は 45 件、未解決の裁定は 46 件。
- 既存の問い（JS1・TP3・HC3・C18・W24・C34/C35・T27）は、該当する場面だけに当てはめ、分類を変えていません（6 章）。
- エンジンの未対応として残ったものはありません。
- kyuura への報告事項（kyuura のデータ・記録は変えていない。[data-provenance.md](data-provenance.md) の v0.39 の章）:
  1. GS1 が kyuura の未解決の一覧にない（研究の対応表の `stop_codes` で `not_in_kyuura`）。
  2. ポッポ（PMCG1-059）のワザの名前: kyuura は「かぜおこし」、pcg-search.com は「ふきとばし」（kyuura の CR-TRANSPARENCY-WHIRLWIND の注と同じ違い）。
  3. pcg-search.com のソニックブーム・ウォーターリングの文面の「弱点・抵抗カ」は、サイトの文字の違い（kyuura のデータの誤りではない。参考）。
