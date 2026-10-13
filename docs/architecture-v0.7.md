# 設計の変更（v0.7）

v0.7 は、フーディン（PMCG1-049）のポケモンパワー「ダメージスワップ」（自分の場のポケモンのダメージカウンターを、自分の場の別のポケモンへのせかえる。きぜつさせない）と、ワザ「あやしいひかり」、進化元のケーシィ（PMCG1-043。ねんりき）・ユンゲラー（PMCG1-046。じこさいせい・ちょうねんりき）を加えた版です。原典の照合と裁定は [damage-swap-v0.7.md](damage-swap-v0.7.md)（S1〜S25・A4）と [alakazam-line-v0.7.md](alakazam-line-v0.7.md)（K1〜K10）、確かめた結果は [v0.7-verification.md](v0.7-verification.md) です。v0.5 の `PowerKey → PowerEntry → PowerEffect` の仕組みをそのまま使い、新しいのは「ダメージカウンターを 1 個のせかえる実装（`MoveDamageCounter`）とログ `move_damage_counter`」「きぜつの判定の式を 1 か所にした関数（`would_be_knocked_out`）」「ワザを使うプレイヤーがトラッシュするエネルギーを選ぶ決定（`DISCARD_ENERGY`。v0.4d のワザの途中の決定の仕組みを使う）」だけです。状態の項目・書き出しの形式・コマンドの種類・段階は加えていません。

## 1. コマンドの形（B1）

選ばせるものは 2 つ（移動元と移動先の自分の場のポケモン）で、どちらも宣言の時点で使うプレイヤーに見えている（自分の場）。

| 案 | 形 | 長所 | 短所 | 採否 |
|---|---|---|---|---|
| A. 今のコマンドを使う | `UsePokemonPower(player, pokemon, power=0, energy=None, source=移動元の場のポケモンの番号, target=移動先の場のポケモンの番号)` | 1 つのコマンドで処理を終える（原子的。p.311「すべてすませてから」）。`source`・`target` は v0.5 のエナジートランスと同じ「移動元・移動先の場のポケモン」の意味で、新しい意味づけをしない。コマンドの種類・段階・決定・再開先を加えない（`ALLOWED`・`sample_commands`・`command_from_dict`・v0.1 の参照データ・比較の駆動に影響しない） | 移す数を指定する項目がない（1 回 1 個。2 章） | **採用**。使わない `energy` を指定したら `POWER_CHOICE_NOT_USED`（取りちがえを黙って通さない。v0.6 と同じ） |
| B. 能力ごとの引数（`count` など）を加える | `UsePokemonPower(..., source, target, count)` | 1 回のコマンドで何個も移せる | すべてのパワーのコマンドに、ほかのパワーでは意味のない項目が増える（v0.4e までの辞書・比較の駆動・書き出しに影響）。1 回に何個移すかは原典で決まっていない（S3）ので、この項目は原典の言葉に対応しない。途中のきぜつの扱い（2 章）を確かめる処理が要る | 不採用 |
| C. 専用のコマンド | `MoveDamageCounter(player, pokemon, source, target)` | 項目の意味がはっきりする | パワーを加えるたびにコマンドの種類が増える（エンジンがカードの種類を知ることになる。v0.2a の登録表の考え方に反する）。共通の確認（番・段階・使うポケモン・登録・宣言のログ）を重ねて書く | 不採用 |
| D. 複数段階の決定 | `UsePokemonPower(player, pokemon)` → 決定「移動元」→ 決定「移動先」（→「数」） | 項目が要らない | 宣言したがまだ移していない途中の状態が要る（書き出しの形式 1〜9 で表せない・再開先・`decision_problems`・不変条件が要る）。選ぶものが宣言の時点でそろっているので、決定にする利点がない | 不採用（処理の途中で選ぶものが決まるパワーを加えるときに使う。v0.5 の architecture 9 章） |

v0.4e までの 2 つの項目（`player`・`pokemon`）だけの辞書も、今までどおり読める（ダメージスワップには選ばせるものが足りないので `POWER_CHOICE_MISSING`）。

## 2. 移動の単位（B2）

**1 回の使用で 1 個**（実装上の仮定。S3）。比べた案:

| 案 | 内容 | きぜつの禁止との関係 | 採否 |
|---|---|---|---|
| 1 回 1 個 | `UsePokemonPower` 1 つで 1 個。何度でも使える（S2） | 1 回ごとに「のせたらきぜつするか」を確かめれば足りる。途中の状態がない | **採用** |
| 1 回に何個でも（同じ移動元 → 同じ移動先） | `count` 個をまとめて | 最後の状態だけを確かめれば足りる（移動先のダメージは増えていくだけ）が、コマンドの項目が要る（1 章の B） | 不採用 |
| 1 回に何個でも（いくつもの移動元・移動先） | 移動の一覧をまとめて | 一覧の順番に処理すると途中で HP 以上になる場合と、最後の状態では HP 未満の場合がありうる。どちらで判定するかを決める必要がある（原典は「この力によってポケモンが「きぜつ」しないかぎり」とだけ書く） | 不採用 |

1 回 1 個にしても、まとめて移す使い方と同じ最後の状態に、途中できぜつすることなくたどりつける（[damage-swap-v0.7.md](damage-swap-v0.7.md) 4 章の証明）。たどりつける状態は変わらず、途中の状態の扱いという原典で決まっていない問いを作らない。英語版の文面（「move 1 damage counter」）で決めたのではない。

## 3. 確かめる順番と不変条件（B3）

### 3.1 確かめる順番（状態を変える前にすべて）

| 順 | 確かめること | コード | 場所 |
|---|---|---|---|
| 1 | コマンドの項目の型 | `BAD_COMMAND` | `commands.check_command_fields` |
| 2 | 対戦が終わっていない・止まっていない | `GAME_OVER`・止めた理由 | `apply_command` |
| 3 | 段階が `Phase.MAIN`・プレイヤーの番号・番のプレイヤー | `WRONG_PHASE`・`INVALID_PLAYER`・`NOT_YOUR_TURN` | `engine._require_turn` |
| 4 | 使うポケモンが自分の場にいる | `POKEMON_NOT_YOURS`・`POKEMON_NOT_IN_PLAY` | `engine._use_pokemon_power` |
| 5 | その位置に特殊能力がある・実装が登録されている | `NO_POKEMON_POWER`・`UNSUPPORTED_POKEMON_POWER` | 同上 |
| 6 | 使うフーディンがねむり・マヒ・こんらんでない（S7） | `POKEMON_ASLEEP`・`POKEMON_PARALYZED`・`POKEMON_CONFUSED` | `MoveDamageCounter.check_usable`（`_require_user_not_asleep_paralyzed_confused`） |
| 7 | 移動元・移動先を指定した・エネルギーを指定していない | `POWER_CHOICE_MISSING`・`POWER_CHOICE_NOT_USED` | 同上 |
| 8 | 移動元・移動先が自分の場のポケモン（S10・S11・S13） | `SOURCE_NOT_IN_PLAY`・`SOURCE_NOT_YOURS`・`TARGET_NOT_IN_PLAY`・`TARGET_NOT_YOURS` | 同上（`_own_pokemon`） |
| 9 | 移動元と移動先が別（S14） | `SAME_POKEMON` | 同上 |
| 10 | 移動元にダメージカウンターがある（S15） | `NO_DAMAGE_COUNTERS` | 同上 |
| 11 | 移動先に 1 個のせてもきぜつしない（S16・S17） | `WOULD_KNOCK_OUT` | 同上（`would_be_knocked_out`） |

確かめることはどれも宣言のログより前で、`apply_command` は複製した状態で処理するので、拒否したら渡した状態・乱数・ログは変わらない（v0.1 からの約束。`assert_rejected`・ストレス実行の拒否の前後の比較・変異 11）。

### 3.2 不変条件

| 要件 | 確かめるところ |
|---|---|
| 移動元・移動先が自分の場のポケモン | 3.1 の 8（状態を変える前）。ログの監査（持ち主・場にいるか） |
| 移動元に十分なカウンター・ダメージが負にならない | 3.1 の 10。`check_invariants`（ダメージは 0 以上・10 の倍数・HP 未満。v0.1 から）。ログの監査（組み立てたダメージ） |
| 合計のダメージが変わらない（保存） | 1 回の移動で移動元 −10・移動先 +10。状態だけからは前の値が分からないので、ログの監査がダメージを組み立て直して状態と比べる。単体テスト `test_random_sequences_never_knock_out`（300 回）・`test_any_number_of_times_one_counter_each` |
| 禁止されたきぜつがない | 3.1 の 11（状態を変える前）。そのうえで `check_invariants`（場のポケモンのダメージは HP 未満）が二重に確かめる（実装の確認が壊れていたら `StateIntegrityError`。`test_invariants_catch_a_broken_check`）。ログの監査（移動のあとのダメージが HP 以上なら報告） |
| ダメージ以外を変えない | `resolve` は 2 つの `damage` とログだけを変える（`test_nothing_else_changes`） |
| 拒否したら何も変えない | 3.1 の最後 |

ダメージカウンターの移動は「ワザによるダメージ」として扱わない（p.320。S19）。`effects.deal_attack_damage` を通さないので、弱点・抵抗力・プラスパワー・ディフェンダー・「ダメージを受けない」状態（v0.4b）を計算しない。

## 4. きぜつの判定（B4）

| 案 | 内容 | 採否 |
|---|---|---|
| 移したあとで、通常のきぜつの処理（`engine._after_knockouts`）にまかせる | 移してからきぜつを判定し、きぜつしたらトラッシュ・サイド | 不採用。原典は「この力によってポケモンが「きぜつ」しないかぎり」で、きぜつさせる移動はできない（S17）。移してから処理すると、サイド・交代が起こってしまう |
| 移す前に、同じ式で「のせたらきぜつするか」を確かめて拒否する | `would_be_knocked_out(state, target, target.damage + 10)` | **採用** |

`effects.would_be_knocked_out(state, pokemon, damage)` は、きぜつの判定と同じ式（ダメージが HP と同じか大きい。p.319・p.320・p.323。HP はいちばん上のカード。p.310）を 1 か所に書いた関数。今までのきぜつの判定（エンジンの `damage >= hp` の箇所）は、大きな変更を避けるために書きかえていない（同じ式であることは変異 17・18 と `test_boundary_for_each_damage` で確かめた）。

## 5. ログ（B5）

```text
pokemon_power        player, pokemon（使うフーディンのいちばん上のカードの uid）, pokemon_id, power（名前 "ダメージスワップ"）, power_index, turn
move_damage_counter  player, pokemon, pokemon_id（使ったフーディン）, power（PowerKey の文字列 "PMCG1-049@power0"）, count（1）,
                     from_pokemon_id, to_pokemon_id, from_total_damage, to_total_damage（移したあとのダメージ）, turn
```

- 宣言 `pokemon_power`（p.311 の手順 1）のすぐあとに、処理 `move_damage_counter`（手順 3）が 1 つ。
- `damage`（ワザのダメージ）・`remove_damage_counters`（きずぐすり）・`drain_heal`（メガドレイン・やどりぎのタネ）・`move_energy`（エナジートランス）とは別の種類。書くのは場の公開の情報だけ（手札などの非公開の情報を書かない）。

### 5.1 ログの監査（tests/log_audit.py）

v0.4e の約束（ダメージ・エネルギー・トラッシュを変えるログを加えたら、組み立て直しにも加える）にしたがって、次を加えた。

| 加えたもの | 確かめること |
|---|---|
| `move_damage_counter` | 直前に同じ番・同じプレイヤー・同じポケモンの宣言があること、登録がダメージカウンターを移す特殊能力で、使ったポケモンのいちばん上のカードのもの（ほかのパワーの名前ですりかえていない）、`count` が 1、移動元・移動先が自分の場のポケモンで別のもの、移動元に組み立てたダメージが 10 以上あった、移したあとのダメージ（`from_total_damage`・`to_total_damage`）が組み立てと同じ、移動先のダメージが HP（その時点のいちばん上のカード）未満、ワザのあと（番の終わりまで）にないこと |
| `discard_energy`（じこさいせい） | ワザを使ったポケモンについていたエネルギーカードで、持ち主のトラッシュへ（エネルギーとトラッシュの組み立て直し） |
| `remove_all_damage_counters`（じこさいせい） | ダメージの組み立て直し（`total_damage` が組み立てと同じ）。1 回のワザでトラッシュととりのぞく処理が 1 回ずつ |
| 宣言と処理 | 宣言のすぐあとの処理に `move_damage_counter` を加えた |

監査が壊れたログ・状態を見つけることは tests/test_alakazam_games_v0_7.py `LogAuditDamageSwapTest`（17 通り。移動元が減らない・移動先が増えない・逆向き・数・ない番号・相手のポケモン・宣言なし・処理のない宣言・順番の入れかえ・ほかのパワー・ワザや番の終わりのあと・状態だけの変化）と `test_detects_a_knock_out_by_moving`（移動できぜつするダメージ）・`LogAuditRecoverTest`（5 通り）で確かめた。

監査で見つけられないこと（ログに書かない情報なので、単体テスト・変異テストで確かめる）: 使ったフーディンがその時点でねむり・マヒ・こんらんだったか（監査は特殊状態を組み立て直さない）・ダメージスワップを使えなかった番に使えなかった理由・拒否したコマンド（ログに残らない）・じこさいせいでどのカードを選べたか（決定の選べるものはログに書かない）。

## 6. 状態と書き出し（B6）

**形式 9 のまま（形式 10 を加えない）**。理由:

- 移したカウンターは、場のポケモンの `damage`（v0.1 から）で表せる。
- ダメージスワップは何度でも使える（S2）ので、使った回数を状態に持つ必要がない（回数の制限のあるパワーを加えるときは状態に持つ。v0.5 の約束）。
- じこさいせいの決定（`DISCARD_ENERGY`）は、v0.4d からあるワザの途中の決定（`resume="attack"`）の形で表せる（形式 2 以上。進化したユンゲラーがいれば形式 7 以上。形式 1 はワザの途中の決定を書き出せない）。

書き出しの監査の `LATEST_FORMAT` は 9 のまま。ダメージスワップを使った状態も、形式 7〜9 で同じダメージを書き出す（`test_no_new_format`）。

## 7. ユンゲラーの「じこさいせい」の決定

v0.4d のワザの途中の決定の仕組み（`push_attack_decision`・`AttackEffect.resume`・`decision_problems`・`engine._attack_decision_problems`）をそのまま使った。新しい段階・コマンド・再開先は加えていない。

- 決定の種類 `DISCARD_ENERGY`（decisions.py に加えた定数）。決定するのはワザを使ったプレイヤー（番のプレイヤー）。選べるものは、ワザを使ったポケモンについている「超」の基本エネルギーカードの uid（ついている順）。1 枚選ぶ。
- `resume` は決定のあとの要素（トラッシュ → すべてとりのぞく）だけを処理し、宣言・エネルギーの確認・こんらんのコインを繰り返さない。
- `decision_problems` が決定の形（種類・プレイヤー・選ぶ数・選べるもの）を確かめる（不変条件）。

## 8. 変えたもの

| 場所 | 変更 | 理由 |
|---|---|---|
| `effects.MoveDamageCounter` | 加えた（ダメージスワップ） | 3 章 |
| `effects.would_be_knocked_out` | 加えた | 4 章 |
| `effects.DiscardEnergyAndRemoveAllCounters` | 加えた（`energy_type`。ユンゲラーは超） | じこさいせい（7 章・[alakazam-line-v0.7.md](alakazam-line-v0.7.md)） |
| `decisions.DISCARD_ENERGY` | 加えた | 7 章 |
| `effects.DEFAULT_EFFECTS` | id を `kyuura-engine-0.7` に。ワザ 4 つ（ケーシィのねんりき、ユンゲラーのじこさいせい・ちょうねんりき、フーディンのあやしいひかり。43 → 47）とパワー 1 つ（ダメージスワップ。2 → 3）を加えた | 登録の中身が変わった |
| `engine._use_pokemon_power` | 説明と、決定・段階の確認の文言（「v0.5〜v0.7 の特殊能力は決定を出さない」）だけ | 処理は変えていない |
| `cards.POOL_KEYS` | `pool_v0_7` を加えた | 写しの対戦用のカードの組 |
| scripts/extract_kyuura_cards.py・kyuura_engine/data/kyuura_cards.json | `POOL_V0_7`（ケーシィ・ユンゲラー・フーディン）を加え、参照カードをフーディンからリザードン（PMCG1-021。登録のないパワー「エナジーバーン」とワザ「ほのおのうず」）に替えて写しを作り直した（参照コミット `ecb2d694` のまま。`--check` で一致） | フーディンを対応にしたので、未対応のポケモンパワーを持つ 2 進化の参照カードが要る |
| kyuura_engine/data/card_verification.json | PMCG1-043・PMCG1-046・PMCG1-049 の照合の記録を加えた | 照合してから登録する（CLAUDE.md） |
| tests/log_audit.py | 5.1 | — |
| tools/stress_engine.py | フーディンの 2 組（`alakazam`・`alakazam_mixed`。`alakazam_mixed` はフシギバナ・カメックス・フーディンを同じデッキに）と、ダメージスワップの使用（できそうなもの 70%・わざと不正なもの 30%）を混ぜる。`POWER_USERS` の最後にフーディンを加えたので、フーディンのいない組は v0.6 と同じ操作（乱数の使い方を変えていない） | 段階 C のストレス実行 |
| `kyuura_engine.__version__`・pyproject.toml | `0.7.0` | 版の名前 |

## 9. 変えなかったもの

- コマンドの種類・段階（`Phase`）・再開先・書き出しの形式（9 のまま）・状態の項目。
- ログの既存のイベントの形。加えたのは `move_damage_counter`・`discard_energy`・`remove_all_damage_counters` だけ。
- 乱数の使い方（ダメージスワップ・じこさいせいは乱数を使わない。ねんりき・あやしいひかりはコイン 1 枚で、v0.3b・v0.3c の実装と同じ）。
- 既存のルールの処理・裁定の分類・処理の順番。v0.6 までの 12 の `UNRESOLVED_…` のコード（新しいコードは加えていない）。**R13（`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`）は変えていない**（ダメージスワップは R13 の判定に数えない）。
- 固定値: tests/test_reproducibility.py、各対戦のテストの `GOLDEN_DIGEST`・`EXPECTED_COUNTS`、tests/fixtures/v0_1_reference.json・tests/fixtures/compat_base_4bd97bf.json（作り直していない）。
- 比較の駆動（tools/compat_driver.py）。

## 10. 前の版との比較

`python3 tools/compare_engine_versions.py --base 787fff9`（v0.6）: 8 つの組・50 局・11,377 手で、食い違いはなかった（[v0.7-verification.md](v0.7-verification.md) 3.2）。比べないのは効果の登録表の id だけ（`kyuura-engine-0.6` → `kyuura-engine-0.7`）。駆動は `UsePokemonPower` を送らず、比べた組にケーシィの系統はいないので、この比較は「フーディンの系統のいない対戦の結果が変わらない」ことを確かめたもので、ダメージスワップの正しさは単体テスト・自然な対戦・ストレス実行・変異テストで別に確かめた。

## 11. 変えた既存のテストと理由

どのテストも、確かめる内容（意図）は弱めずに、v0.7 の変更に合わせて値・カードを直した。理由はテストのコメントにも書いた。

| テスト | 変更 | 理由の種類 |
|---|---|---|
| tests/test_cards.py `test_trainer_evolution_and_power_are_unsupported` | 未対応のポケモンパワーを持つ 2 進化の例を、フーディンからリザードンに替えた。「名前が同じワザでも、カードごとの登録がなければ未対応」（v0.6 までフーディンの「あやしいひかり」で確かめていた）は、フーディンのワザの登録を除いた登録表で確かめ続ける | 参照カードの置き換え |
| tests/test_cards.py `test_v0_1_pool_is_ten_basic_pokemon_and_six_basic_energy` | `pool_v0_7` を確かめ、v0.1 の組の数え方からケーシィの系統を除いた | 件数の変化（写しに v0.7 の組を加えた） |
| tests/test_evolution_v0_4a.py `test_unsupported_evolution_cards`・`test_rejected_commands` | 未対応の 2 進化の例をリザードンに替えた（`UNSUPPORTED_EVOLUTION` のまま） | 参照カードの置き換え |
| tests/test_stage2_v0_4c.py `test_stage2_is_not_supported_as_a_whole`・`test_unsupported_stage2_cards`・`test_rejected_stage2_evolutions_change_nothing` | 同上 | 参照カードの置き換え |
| tests/test_pokemon_powers_v0_5.py `test_default_registry_registers_only_energy_trans`・`test_registry_methods_keep_the_other_registrations`・`test_unregistered_power_of_another_card_stays_unsupported` | 登録は 3 つ（エナジートランス・あまごい・ダメージスワップ）。登録のないパワーの例をリザードンに替え、3 つの登録をリザードンの位置に写しても使えないことを確かめる | 登録表・参照カードの置き換え |
| tests/test_rain_dance_v0_6.py `test_card_values`・`test_registered_entry_matches_the_verification` | 参照カードはフーディンではなくリザードン。登録表の id を `kyuura-engine-0.7` に | 参照カードの置き換え・登録表の id |
| tests/test_effects.py `test_attacks_with_text_follow_the_verified_latest_description`・`test_with_and_without_do_not_change_the_original` | 説明文のあるワザの一覧にねんりき・じこさいせい・あやしいひかり（フーディン）を加え、ワザの登録の数を 43 → 47、パワーを 3 つにした | 件数の変化 |
| tests/test_trainers.py `test_default_registry_has_exactly_the_registered_cards`・tests/test_rng_and_serialize.py `test_format_2_adds_only_documented_fields`・各対戦のテストの `GOLDEN_DIGEST` の前の `effects`（v0.4a・v0.4b・v0.4c・v0.4d・v0.5・v0.6） | 登録表の id を `kyuura-engine-0.7` にした（固定値の指紋は変えていない） | 登録表の id |
| tests/test_unresolved_rulings_v0_3d.py `test_the_stop_is_needed_for_every_playable_pokemon` | プラスパワー・ディフェンダーがついていないときの、こんらんの 20 の期待値を、固定の 20 から「1 通りの読み方の値（`calculate_confusion_damage`。弱点・抵抗力だけ）」にした。超のポケモン（ケーシィ・ユンゲラー・フーディン）が 40 になり、それ以外が 20 のままであることを加えて確かめる | 原典に基づく修正（前提の変化）。p.322「このダメージは「弱点・抵抗力」の影響を受けます」により、自分のタイプを弱点に持つポケモンは 40。v0.6 までは対戦に使えるポケモンにそのようなポケモンがなく、20 と書けていた。確かめる内容（ついていなければ読み方は 1 通り・ついていれば読み方で結果が変わる）は変えていない |
| tests/test_effect_preflight_v0_3d.py `ATTACKS`・`EVOLVED_FROM` | ねんりき・じこさいせい・ちょうねんりき・あやしいひかりを加えた | CLAUDE.md（ワザの実装を加えたら `ATTACKS` にも加える） |
| tests/helpers.py | ケーシィ・ユンゲラー・リザードンの定数を加え、フーディンの説明を直した | — |

v0.6 のテスト（tests/ の全体）を v0.7 のコードで実行すると、上の 23 件のほかに、tests/test_bulbasaur_games_v0_5.py `PowerStressSmokeTest.test_small_power_stress_run` も落ちる（[v0.7-verification.md](v0.7-verification.md) 4.2）。ストレス実行の組（`POWER_SCENARIOS`）にフーディンの組が加わり、v0.6 の tests/log_audit.py がダメージカウンターの移動を組み立て直せないためで、このテストは変えていない（v0.7 の監査に組み立て直しを加えたので、そのまま通る）。

テストのバグの修正（意図に合わせた修正）は、v0.7 では v0.6 までのテストにはなかった。

## 12. 拒否のコードの順番（v0.6 の変異 19 の再検討）

v0.6 の変異 19（通常の操作の「1 番に 1 枚」の確認を、つける先の確認のあとに移す）は見つからなかった。2 つ以上の理由で正しくないコマンドに、どのコードを返すかだけが変わる変異で、どちらでも拒否され状態は変わらない。

**API の約束として保証されている順番**（テストで固定している）:

1. コマンドの型（`BAD_COMMAND`）→ 対戦の終わり・止まり → 段階・プレイヤー・番（`_require_turn`）→ 共通の確認（使うポケモン・特殊能力の有無・登録）→ パワーごとの確認。パワーごとの確認では、使えない特殊状態（`POKEMON_ASLEEP` など）を選ばせるものより先に確かめる（v0.5 の P11・v0.6 の R9・v0.7 の S7。説明の「使えない」は使うための条件で、選ばせるものはそのあとの処理の内容）。テスト: `test_special_conditions_of_the_user`（選ばせるものが正しくなくても特殊状態のコード）・変異 24（見つかる）。
2. 原典で決められないことで止めるコード（`UNRESOLVED_…`）は、ほかの確認がすべて通ったあと（止めるのは、そのコマンドがほかの点では正しいときだけ）。テスト: v0.6 の変異 35（見つかる）・tests/test_unresolved_boundaries_v0_4e.py。

**保証していない順番**: それ以外の、ルール上の拒否（`IllegalActionError`）の理由どうしの順番（v0.6 の変異 19 の「1 番に 1 枚」とつける先、v0.7 の変異 25 の「同じポケモン」と「カウンターがない」など）。理由:

- docs/api-review.md は、エラーコードの一覧を公開の約束にしているが、2 つ以上の理由で正しくないコマンドにどのコードを返すかは、v0.1 から書いていない（どれを返しても拒否で、状態は変わらない）。
- 原典にも順番の規定はない（「つけることはできません」「別のポケモン」はどれも、できないことだけを書く）。
- 順番をテストで固定すると、実装の都合が約束になり、確認を整理する変更（v0.6 の `_own_pokemon` の共通化のような）を妨げる。

そのため、v0.6 の変異 19 と v0.7 の変異 25 にはテストを加えていない。ただし、版の間でこの順番が変わったことは、比較の道具（tools/compare_engine_versions.py。拒否のコードの列を比べる）が、比べた操作の範囲で見つける。

## 13. この先の変更への提案（実装していない）

例のページは、OCR で位置を探したもの・v0.7 の調査で画像を見たもの（p.98・p.248）で、カードの処理は照合していない（実装するときに画像で照合する）。

| 種類 | 例 | 要るもの |
|---|---|---|
| 常にはたらく・パワーを止めるパワー | ベトベトン［かがくへんかガス］（p.48・p.323）・わるいアーボックの「ショックアイ」（ワザの持続する効果。p.24） | `check_usable` の前に、場の常にはたらく効果・持続する効果を調べる仕組み（エナジートランス・あまごい・ダメージスワップを含むすべてのパワーの使用に影響する）。p.311・p.323 の「常にはたらいているため、使用を宣言しない特殊能力」の扱い（宣言しないので `UsePokemonPower` の形では扱わない） |
| 回数の制限（「自分の番ごとに1回」） | タケシのキュウコン［ばける］（p.70）・わるいユンゲラー［ぶっしつこうかん］（p.152）・わるいハクリュー［しんかのひかり］（p.248） | 使った回数を状態に持つ（ポケモンごと・番ごと）。v0.6 の `energy_attached_by_powers_this_turn` と同じく、番の最初の 0・不変条件（ログとの対応）・書き出しの形式 10。進化・ベンチに戻る・番の終わりでの扱いを原典で確かめる |
| 割り込み型・自動的にはたらくパワー | カイリキー［はんげき］（p.192）・カイリュー［いやしのかぜ］（進化させたとき 1 度。p.248）・メノクラゲ［おくびょう］（p.98） | 決められたときに自動的にはたらく特殊能力（p.311・p.323）。ダメージ・進化の処理の途中で、決定や処理を差しこむ仕組み（ワザの途中の決定（v0.4d）と同じ考え方で、再開先・`decision_problems` を加える）。「ダメージを受けたとき」は p.319 の「ダメージを与えたポケモン」・p.320 の「移動は「ダメージを受けた」ことにならない」（ダメージスワップでは起こらない）を確かめる |
| 進化前のワザを使う・退化 | 「思い出させる」（p.153 の解説。ユンゲラーの「じこさいせい」をフーディンが使う）・退化させるカード | p.310「進化前のポケモンのカードに書かれている内容のすべては無効」との関係、重なりの下のカードのワザを使う仕組み。退化では p.323（ダメージカウンターはそのまま）と、HP が下がったときのきぜつ（`UNRESOLVED_EVOLUTION_HP` と同じ種類の問い）を確かめる |
| 特殊エネルギー | レインボーエネルギー（p.298） | じこさいせいの「トラッシュできないとき」（K3）が起こりうるので、その処理とテストを加える。あまごい・エナジートランスのカードの判定も見直す |
| R13 が決まったら | — | v0.6 と同じ（`engine._attach_energy` の停止を決まった処理に置きかえ、分類を変える根拠を書く） |
