# 設計の変更（v0.5）

v0.5 は、ポケモンパワー（特殊能力）の基盤と、その最初のカードとしてフシギバナの「エナジートランス」、進化元のフシギダネ・フシギソウを加えた版です。原典の照合は [pokemon-powers-v0.5.md](pokemon-powers-v0.5.md)（一般の規定。B1）・[venusaur-v0.5.md](venusaur-v0.5.md)（B2）・[bulbasaur-line-v0.5.md](bulbasaur-line-v0.5.md)（B3）、処理は [energy-transfer-v0.5.md](energy-transfer-v0.5.md)（B4 を含む）、確かめた結果は [v0.5-verification.md](v0.5-verification.md) です。

## 1. 変えたもの

| 場所 | 変更 | 理由 |
|---|---|---|
| `effects.PowerKey`・`PowerUse`・`PowerEffect`・`PowerEntry` | 加えた。ポケモンパワーの識別子（カード id とパワーの位置。文字列は `"PMCG1-011@power0"`）、1 回の使用の情報、実装の基底（`check`・`check_usable`・`resolve`）、登録の 1 件（実装・照合した名前と印刷の文面・実装がしたがう最新の説明・出典） | ワザ（`AttackKey`・`AttackEffect`・`AttackEntry`）・トレーナー（`TrainerEntry`）と同じ考え方の別の欄。ポケモンパワーをワザの一種として扱わない（番を終わらせない・こんらんのコインがない・使えない特殊状態はカードごと） |
| `effects.EnergyTransfer` | 加えた（`energy_type`。フシギバナは草）。確かめることと処理は [energy-transfer-v0.5.md](energy-transfer-v0.5.md) | エナジートランス |
| `effects.EffectRegistry` | パワーの欄（`power_keys`・`power_entry`・`power_problem`・`power_effect`・`with_powers`・`without_powers`、`describe()` の `"powers"`）。ワザ・トレーナーの `with_*`・`without_*` もパワーの登録を引き継ぐ | 登録表は変えられない（新しい登録表を返す）。v0.2a からの形 |
| `effects.DEFAULT_EFFECTS` | id を `kyuura-engine-0.5` にした。ワザ 4 つ（フシギダネのやどりぎのタネ、フシギソウのつるのムチ・どくのこな、フシギバナのソーラービーム。ワザは 34 → 38）とパワー 1 つ（エナジートランス）を加えた | 登録の中身が変わったので id を変えた（v0.4e は中身を変えなかったので id を変えなかった） |
| `effects.PoisonOpponent` | 加えた（20 のあと、コインを投げずに相手をどく状態に） | フシギソウのどくのこな。コインを投げる `PoisonOnHeads` を流用しない |
| `effects.DamageAndRemoveCounters` | 加えた（ダメージを与えたら自分のダメージカウンターを `counters` 個とりのぞく）。とりのぞく部分を `_remove_attacker_counters` にし、v0.4d の `DamageAndDrain`（メガドレイン）もこれを使う（ログ `drain_heal` の項目・順番は同じ） | フシギダネのやどりぎのタネ。v0.4d の `DamageResult` で「与えたら」を判定する |
| `cards.Power`・`CardDefinition.powers` | 加えた。ポケモンパワーを 1 つずつ、登録表に実装があり、データ（名前・文面・種類）と合うかで分類する。1 つでも使えなければカードは使えない（理由「ポケモンパワー「名前」: …」） | v0.4e までは、パワーを持つカードをすべて「ポケモンパワーは未実装」で拒否していた。パワーを持つカードを一括で対応にしない |
| `cards.POOL_KEYS` | `pool_v0_5` を加えた | 写しの対戦用のカードの組 |
| scripts/extract_kyuura_cards.py・kyuura_engine/data/kyuura_cards.json | `POOL_V0_5`（フシギダネ・フシギソウ・フシギバナ）を加え、参照カードをフシギバナからカメックス（PMCG1-032）に替えて写しを作り直した（参照コミット `ecb2d694` のまま） | フシギバナを対応にしたので、未対応のポケモンパワーを持つ 2 進化の参照カードが要る |
| kyuura_engine/data/card_verification.json | PMCG1-001・PMCG1-008・PMCG1-011 の照合の記録を加えた。パワーの記録は `power_card_image_text_ja`・`power_latest_description_ja`（パワーの位置ごとの辞書）、確かめた項目は `checked_fields_power` | 照合してから登録する（CLAUDE.md） |
| `commands.UsePokemonPower` | `power`（既定 0）・`energy`・`source`・`target`（既定 None）を加えた。`pokemon` は場のポケモンの番号。`check_command_fields` は `int \| None` の項目を受け付ける。`UNSUPPORTED_COMMANDS` は空になった | B4（案 A: コマンドに明示する）。v0.4e までの 2 つの項目の辞書も読める |
| `engine._use_pokemon_power` | 加えた（`_HANDLERS` に登録）。確かめる順番は [energy-transfer-v0.5.md](energy-transfer-v0.5.md) 2 章。宣言のログ `pokemon_power` → 実装の `resolve`。処理のあとに決定・段階の変化があれば `RuntimeError`（v0.5 のパワーは決定を出さない） | p.311 の手順 1〜3 |
| tests/log_audit.py | `move_energy` の組み立て直しと、宣言・持ち主・番のプレイヤー・ワザのあとの使用の確認を加えた | v0.4e の約束（ログにエネルギーを変えるイベントを加えたら、組み立て直しにも加える） |
| tools/stress_engine.py | フシギバナの組（`POWER_SCENARIOS`）と、エナジートランスの使用を混ぜる `choose_command` を加えた。フシギバナのいない組では駆動とまったく同じ操作になる | 段階 C のストレス実行。比較の駆動（tools/compat_driver.py）は変えていない |
| `kyuura_engine.__version__`・pyproject.toml | `0.5.0` | 版の名前 |

## 2. 変えなかったもの

- 書き出しの形式（1〜8 のまま。形式 9 は加えていない。v0.5 は状態の項目を加えていない）。エナジートランスは決定を出さないので、決定の種類・段階（`Phase`）・再開先も加えていない。
- ログの既存のイベントの形（`attach_energy`・`drain_heal` など）。加えたのは `pokemon_power`・`move_energy` だけ。
- 乱数の使い方（エナジートランス・やどりぎのタネ・どくのこなは乱数を使わない）。
- 既存のルールの処理・裁定の分類・処理の順番。v0.4e までの 11 の `UNRESOLVED_…` のコード（新しい未解決のコードは加えていない）。
- 固定値: tests/test_reproducibility.py、各対戦のテストの `GOLDEN_DIGEST`・`EXPECTED_COUNTS`、tests/fixtures/v0_1_reference.json・tests/fixtures/compat_base_4bd97bf.json（作り直していない）。
- 比較の駆動（tools/compat_driver.py）。駆動は `UsePokemonPower` を送らないので、フシギバナのいない 8 つの組の比較はそのまま使える。

## 3. 前の版との比較

`python3 tools/compare_engine_versions.py --base c1e13ec`（v0.4e）: 8 つの組・50 局・11,377 手で、受け付けた操作・拒否のコード・状態（形式 8。ログ・乱数・決定・止めた理由を含む）・乱数の指紋・段階・ログの長さ・形式 1〜8 の書き出しに食い違いはなかった（[v0.5-verification.md](v0.5-verification.md) 4 章）。比べないのは効果の登録表の id だけ（`kyuura-engine-0.4d` → `kyuura-engine-0.5`）。

新しい機能の正しさ（エナジートランスの動き）は、前の版との比較では確かめられない（前の版はフシギバナを使えない）。単体テスト・自然な対戦・ストレス実行・変異テストで別に確かめた。

## 4. 登録表の id

v0.5 で効果の登録表の id を `kyuura-engine-0.4d` から `kyuura-engine-0.5` に変えた。登録の中身（ワザ 4 つ・パワー 1 つ）が変わったため（v0.4e は中身を変えなかったので id を変えなかった）。登録表の id は書き出しの形式 2 以上の `effects` に入るので、それを固定していたテスト（下の 8 章）の値を更新した。結果（それ以外の項目）は変わっていない。

## 5. 確かめる場所の分担

| 確かめること | 場所 |
|---|---|
| コマンドの項目の型 | `commands.check_command_fields` |
| 段階・番・プレイヤー（すべての操作に共通） | `engine._require_turn` |
| 使うポケモン・特殊能力の有無・登録（すべてのパワーに共通） | `engine._use_pokemon_power` |
| 使える特殊状態・選ばせるもの（パワーごと） | `PowerEffect.check_usable`（エナジートランスは `EnergyTransfer.check_usable`） |
| 登録とデータの照合（名前・文面・種類） | `EffectRegistry.power_problem`・`PowerEffect.check` |
| カードの分類（すべてのパワーが使えるか） | `cards.classify_record` |

## 6. 不変条件

v0.5 は状態の項目・段階・決定を加えていないので、`check_invariants` に新しい確認は加えていない。エネルギーの移動は、既存の不変条件（カードの保存則・ついているのは基本エネルギーだけ・場のカードの持ち主）で確かめられる（変異 3・4・13 は不変条件の違反で見つかった）。ログとの対応（移動のログ・宣言）は tests/log_audit.py の監査で確かめる（ログは状態の正本ではない）。

## 7. テストの段階

| 段階 | v0.5 で加えたもの |
|---|---|
| A 速い単体テスト | tests/test_pokemon_powers_v0_5.py（基盤・共通の確認・原子性）・tests/test_venusaur_v0_5.py（エナジートランス）・tests/test_bulbasaur_line_v0_5.py（ワザ・進化） |
| B 決まった seed の統合テスト | tests/test_bulbasaur_games_v0_5.py（`new_game` からの 48 局・ログと書き出しの監査・ログの監査の自己テスト・小さなストレス実行・固定値） |
| C 大規模な実行 | tools/stress_engine.py の `POWER_SCENARIOS`・前の版との比較 |

## 8. 変えた既存のテストと理由

どのテストも、確かめる内容（意図）は変えずに、v0.5 の変更に合わせて値・カードを直した。理由はテストのコメントにも書いた。

| テスト | 変更 | 理由 |
|---|---|---|
| tests/test_cards.py `test_trainer_evolution_and_power_are_unsupported` | 未対応のポケモンパワーを持つ 2 進化の例を、フシギバナからカメックスに替えた | フシギバナを対応にした（パワーとワザを登録した） |
| tests/test_cards.py `test_v0_1_pool_is_ten_basic_pokemon_and_six_basic_energy` | `pool_v0_5` を確かめ、v0.1 の組の数え方からフシギダネの系統を除いた | 写しに v0.5 の組を加えた |
| tests/test_evolution_v0_4a.py `test_unsupported_evolution_cards`・`test_rejected_commands` | 未対応の 2 進化の例をカメックスに替えた（`UNSUPPORTED_EVOLUTION` のまま） | 同上 |
| tests/test_stage2_v0_4c.py `test_stage2_is_not_supported_as_a_whole`・`test_unsupported_stage2_cards`・`test_rejected_stage2_evolutions_change_nothing` | 同上 | 同上 |
| tests/test_effects.py `test_attacks_with_text_follow_the_verified_latest_description`・`test_with_and_without_do_not_change_the_original` | 説明文のあるワザの一覧にやどりぎのタネ・どくのこなを加え、ワザの登録の数を 34 → 38 にした。パワーの登録表も変わらないことを加えた | 登録を加えた |
| tests/test_trainers.py・tests/test_rng_and_serialize.py・各対戦のテストの `GOLDEN_DIGEST` の前の `effects`（v0.4a・v0.4b・v0.4c・v0.4d） | 登録表の id を `kyuura-engine-0.5` にした（固定値の指紋は変えていない） | 4 章 |
| tests/test_state_integrity.py `ALLOWED`・`sample_commands`・`test_every_command_in_every_phase` | `UsePokemonPower` を `Phase.MAIN` で受け付けるコマンドに加え、ほかの段階ではほかのコマンドと同じ拒否（`WRONG_PHASE`・`GAME_OVER`・止めた理由）を確かめる。見本のコマンドは場のポケモンの番号で作る | v0.4e まではどの段階でも `UNSUPPORTED_ACTION` だった |
| tests/test_turns.py `UnsupportedActionsTest` | 未対応の操作のコマンドの種類がなくなった（`UNSUPPORTED_COMMANDS` が空）ことと、登録のないパワーが `UNSUPPORTED_POKEMON_POWER` になることを確かめる | 同上 |
| tests/test_coin_attacks.py `test_rejections_in_main` | ドードー（特殊能力なし）の使用が `NO_POKEMON_POWER` になる（乱数を使わない） | 同上 |
| tests/test_trainer_games.py `test_only_resolve_decision_is_accepted` | 決定を待つ間の `UsePokemonPower` が `WRONG_PHASE` になる（ほかのコマンドと同じ） | 同上 |
| tests/test_compat_v0_1.py | `NOW_SUPPORTED` に `use_pokemon_power` を加え、変わったコードの内訳（36 回: INVALID_PLAYER 15・WRONG_PHASE 12・NOT_YOUR_TURN 6・POKEMON_NOT_IN_PLAY 3）を docstring と新しいテストに書いた。参照データは変えていない | v0.1 で未対応だった操作を対応にしたとき（v0.2b の `play_trainer`・v0.4a の `evolve_pokemon` と同じ扱い） |
| tests/test_effect_preflight_v0_3d.py `ATTACKS` | やどりぎのタネ・どくのこなを加えた（受け付けるか・拒否のコードがコインの結果で変わらない） | CLAUDE.md（ワザの実装を加えたら `ATTACKS` にも加える） |
| tests/helpers.py | フシギダネ・フシギソウ・カメックスの定数を加えた | — |

## 9. この先の変更で気をつけること（ほかのポケモンパワーの提案。実装していない）

『オフィシャルブック2000』で確かめたカード（画像。300dpi 未満の画像は文面の細部を読みきれないので、実装の前に照合し直す）と、種類ごとの設計の提案です。どれも v0.5 では実装していません。

| 種類 | 例（誌面） | 要るもの |
|---|---|---|
| 回数の制限（「自分の番ごとに1回」） | タケシのキュウコン [ばける]（p.70「この力は、自分の番ごとに1回使える。」） | 使った回数（番ごと・ポケモンごと）を状態に持つ（`PokemonInPlay` の新しい項目。形式 9 と不変条件）。ログから数えない。進化・ベンチに戻る・番の終わりでの扱いを原典で確かめる |
| 手札のカードを使うパワー | カメックス [あまごい]（p.90「この力は、自分の番の中で何度でも使える。自分の手札から「水」エネルギーを出して、自分の場の「水」ポケモンにつける。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は使えない。」） | 手札からつけること（p.310 の 1 番に 1 回）との関係を原典で確かめる（エナジートランスの「つけかえ」とは違い、手札から出す）。ハイドロポンプ（「40+」）の実装も要る |
| ダメージカウンターの移動 | フーディン [ダメージスワップ]（p.153「この力は、自分の番の中で何度でも使える。この力によってポケモンが「きぜつ」しないかぎり、自分の場にいるポケモンにのっているダメージカウンターを、自分の場にいる別のポケモンにのせかえる。…」） | p.320「ダメージカウンターの移動」（ワザによるダメージではない・HP 以上になったらきぜつ）。「きぜつしないかぎり」の判定を状態を変える前に。ログの監査のダメージの組み立て直しに移動を加える |
| 常にはたらく・パワーを止める | ベトベトン [かがくへんかガス]（p.48・p.323「このカードが場にあるかぎり、「かがくへんかガス」以外のすべての「特殊能力」は使えず、その力も消える。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は消える。」） | 宣言しないパワー（P3）。`check_usable` の前に、場の常にはたらく効果を調べる仕組み（エナジートランスを含むすべてのパワーの使用に影響する）。「その力も消える」の範囲（常にはたらく効果・自動の効果）を原典で確かめる |
| 自動的にはたらく | [とうめい]（p.323「このカードがワザによってダメージや効果を受けるとき、コインを投げて「おもて」なら…受けない。」） | ワザの処理の途中に割りこむ（`deal_attack_damage` の前など）。コインの順番（ワザのコインとの前後）を原典で確かめる |
| 常にはたらく（にげるエネルギーを変える） | わるいベトベトン [ねんちゃくえき]（p.48「このカードが場にいるかぎり、相手の対戦ポケモンは、「にげる」ときにトラッシュするエネルギーが2個ぶん多く必要になる。…」） | にげるエネルギーの計算に場の効果を加える |
| エネルギーのタイプを変える・特殊エネルギー | レインボーエネルギー（p.16 の解説「草エネルギーとしてあつかわれる」） | 特殊エネルギーのカード・登録（今は基本エネルギーだけ）。エナジートランスで移せるエネルギーの判定を、カードの種類ではなく「草」として扱われるかで決めるように見直す |

決定を出すパワー（処理の途中で選ばせるもの）を加えるときは、ワザ（v0.4d）・トレーナー（v0.4e）と同じく `PowerEffect.resume`・`decision_problems` と再開先を加え、決定を待つ状態の不変条件と書き出し（形式 1 の扱い）を見直す。相手の番・ポケモンチェックに使うパワーを加えるときは、`UsePokemonPower` を受け付ける段階を見直す。
