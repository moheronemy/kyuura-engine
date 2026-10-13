# 設計の変更（v0.8）

v0.8 は、ベトベトン（PMCG3-007）のポケモンパワー「かがくへんかガス」（常にはたらいていて宣言しない特殊能力。場にいるかぎり、ほかのすべての特殊能力を使えなくし、その力も消す。ねむり・マヒ・こんらんのときは消える）と、ワザ「ヘドロこうげき」、進化元のロケット団のベトベター（PMCG4-004。どくガス・ねばりつく）を加えた版です。原典の照合と裁定は [chemical-gas-v0.8.md](chemical-gas-v0.8.md)（G1〜G33・A4）と [grimer-line-v0.8.md](grimer-line-v0.8.md)（M1〜M9）、常にはたらく効果の求め方は [continuous-effects-v0.8.md](continuous-effects-v0.8.md)、確かめた結果は [v0.8-verification.md](v0.8-verification.md) です。

新しいのは「常にはたらく特殊能力の実装（`SuppressOtherPowers`。`PowerEffect.declared = False`）」「効果を今の状態から求める関数（kyuura_engine/continuous.py）」「特殊能力の使用の 2 つの拒否のコード（`POWER_NOT_DECLARABLE`・`POWER_SUPPRESSED`）」「2 つのワザの実装（`PoisonWithoutDamage`・`CoinBonusDamageAndParalyze`）」だけです。状態の項目・書き出しの形式・コマンドの種類・段階・決定・ログのイベントの種類は加えていません。

## 1. 効果の持ち方（B1）

かがくへんかガスがはたらいているかは、場（両方のプレイヤー）・いちばん上のカード・特殊状態で決まる。比べた案:

| 案 | 形 | 長所 | 短所 | 採否 |
|---|---|---|---|---|
| A. 状態に持つ | `GameState` に「消されている特殊能力」や「はたらいているベトベトン」の一覧、または `PokemonInPlay` に「はたらいている」の印を持ち、変化のたびに更新する | 問い合わせが軽い | 更新の契機が多い（進化・きぜつ・ワザの効果の特殊状態・ポケモンチェックのねむりのコイン・マヒの回復・にげる・ポケモンいれかえ・ふきとばし・進化での回復）。1 か所でも更新を忘れると古い値が残る（変異 10・21・22 の種類の不具合）。場と特殊状態から決まる値を二重に持つので、食い違いを確かめる不変条件が要る。書き出しの形式 10 が要る（形式 1〜9 で表せない） | 不採用 |
| B. 今の状態から求める | 問い合わせのたびに、場のポケモン・いちばん上のカード・特殊状態・効果の登録表から求める（`continuous.suppressors_of`） | 状態を増やさない（形式 9 のまま）。どの変化のあとでも答えが古くならない。保存・復元・複製で同じ答え。不変条件を増やさない | 問い合わせのたびに場を見る（多くて 12 匹 × 特殊能力の数。負担は小さい） | **採用** |
| C. ログのイベントで表す | `gas_on`・`gas_off` のようなイベントを残し、ログを読んで今はたらいているかを決める | 切り替わりがログで見える | ログは記録で、状態の正本ではない（CLAUDE.md。エンジンはログから状態を決めない）。切り替わりを残す処理は、案 A と同じく変化のすべての場所に要る。過去のログを読む処理は、ログの長さとともに重くなる | 不採用 |

案 B が成り立つのは、かがくへんかガスの条件（G2・G9〜G12・G15・G17）が、どれも今の状態にある項目（v0.7 までの形式 9 に入っている）で決まり、期限や過去の出来事に依存しないからである。期限のある「特殊能力を消す」効果（まきちらせ！ベトベトガス（p.265）・ドガースのふしぎなガス（p.52）。どちらも「次の相手の番が終わるまで」）を加えるときは、期限を状態に持つ必要がある（[continuous-effects-v0.8.md](continuous-effects-v0.8.md) 6 章）。

## 2. 確かめる順番（B2）

`engine._use_pokemon_power` の確かめる順番（状態を変える前にすべて）。v0.8 で加えたのは 6・7。

| 順 | 確かめること | コード | 場所 |
|---|---|---|---|
| 1 | コマンドの項目の型 | `BAD_COMMAND` | `commands.check_command_fields` |
| 2 | 対戦が終わっていない・止まっていない | `GAME_OVER`・止めた理由 | `apply_command` |
| 3 | 段階が `Phase.MAIN`・プレイヤーの番号・番のプレイヤー | `WRONG_PHASE`・`INVALID_PLAYER`・`NOT_YOUR_TURN` | `engine._require_turn` |
| 4 | 使うポケモンが自分の場にいる | `POKEMON_NOT_YOURS`・`POKEMON_NOT_IN_PLAY` | `engine._use_pokemon_power` |
| 5 | その位置に特殊能力がある・実装が登録されている | `NO_POKEMON_POWER`・`UNSUPPORTED_POKEMON_POWER` | 同上 |
| 6 | 宣言して使う特殊能力である（G1・G30） | `POWER_NOT_DECLARABLE` | 同上（`effect.declared`） |
| 7 | はたらいているかがくへんかガスに消されていない（G22〜G24・G31・G32） | `POWER_SUPPRESSED` | 同上（`continuous.suppressors_of`） |
| 8 | パワーごとの確認（使うポケモンの特殊状態 → 選ばせるもの → …） | v0.5〜v0.7 のとおり | `PowerEffect.check_usable` |
| 9 | 宣言のログ → 処理 | — | `resolve` |

6・7 を 8 より前にした理由: 消されている特殊能力は、p.311 の「そのとき使うことのできるもの」ではない。パワーごとの条件（使うポケモンの特殊状態・選ばせるもの）は、使うことのできる特殊能力の使い方の条件で、そのあとに確かめる（G32。実装上の仮定だが API の約束としてテストで固定する。13 章）。6 を 7 より前にしたのは、宣言しない特殊能力（かがくへんかガス）は、消されているかどうかに関係なく宣言の対象でないから（かがくへんかガスは名前で除かれるので、7 に当たることもない）。

拒否はどれも宣言のログより前で、`apply_command` は複製した状態で処理するので、渡した状態・乱数・ログは変わらない（v0.1 からの約束。`assert_rejected`・ストレス実行の拒否の前後の比較・変異 18〜20 と 18'〜20'）。

`POWER_SUPPRESSED`・`POWER_NOT_DECLARABLE` は、どちらも `IllegalActionError`（ルール上できない操作）。原典で決まっている（G1・G22〜G24。CONFIRMED）ので、`UnsupportedError`（未対応・原典で決められない）にしない。拒否の説明文に、消しているベトベトンの場のポケモンの番号を書く。

## 3. 複数のベトベトン（B3）

- 両方のプレイヤーの場にいるどのベトベトンも、両方のプレイヤーの特殊能力を消す（G4・G20）。持ち主を見ない。
- 1 匹でもはたらいていれば消す。はたらいているかはベトベトンごとに、そのベトベトンの特殊状態で決める（G14）。
- かがくへんかガスどうしは消し合わない（G5・G21）。名前で除くので、どの順番で求めても答えは 1 つ（[continuous-effects-v0.8.md](continuous-effects-v0.8.md) 4 章）。
- `suppressors_of` が返す番号の並びは、プレイヤー 0 → 1、それぞれバトル場 → ベンチの順（説明文と公開の関数の結果を決まった並びにするため。ルールの意味はない）。

## 4. 求め直す契機（B4）

案 B なので、求め直す処理・契機の一覧はコードにない。答えを変える状態の変化（進化・きぜつ・特殊状態になる・回復する・ベンチに戻る）と、それぞれのテストは [continuous-effects-v0.8.md](continuous-effects-v0.8.md) 3 章。エンジンが問い合わせるのは特殊能力の使用の受け付け（2 章の 7）だけで、v0.8 の対応カードにほかの常にはたらく・自動的にはたらく特殊能力がないので、「その力も消える」がほかの処理に影響することはない（G6・G7）。

## 5. 状態と書き出し（B5）

**形式 9 のまま（形式 10 を加えない）**。理由:

- かがくへんかガスは状態から求める（1 章の案 B）。求めるのに使う項目（場のポケモン・いちばん上のカード・重なり・特殊状態）は形式 7〜9 に入っている。
- かがくへんかガスは何度も使う・回数のある特殊能力ではない（宣言しない）。
- ベトベター・ベトベトンのワザは、v0.3a〜v0.3b のどく・マヒ・コインと、v0.4a の進化で表せる。

書き出しの監査の `LATEST_FORMAT` は 9 のまま。保存（pickle・`copy.deepcopy`・`clone`・形式 9）と復元のあとも同じ答えになることは `SaveRestoreTest` と [v0.8-verification.md](v0.8-verification.md) 2.3 で確かめた。

## 6. ログ（B6）

- **ログのイベントの種類は加えていない**。かがくへんかガスがはたらき始めた・消えたことはログに残さない（状態から求めるので、残すと案 C の短所と同じく、変化のすべての場所に処理が要る）。はたらき始めた・消えた原因のイベント（`evolve`・`knock_out`・`special_condition`・`special_conditions_removed`・`sleep_check`・`paralysis_end` など）は今までどおり残る。
- 拒否した操作はログに残らない（v0.1 から）。消されて使えなかった特殊能力の使用は、拒否のコード `POWER_SUPPRESSED` で分かる。宣言のログ（`pokemon_power`）もない（宣言の前に拒否する。v0.5 の P12 と同じ）。
- ベトベター・ベトベトンのワザのログは、今までのイベント（`attack`・`coin_flip`・`damage`・`damage_prevented`・`special_condition`）だけ。

### 6.1 ログの監査（tests/log_audit.py）

最後の状態だけから過去の特殊能力の使用の正しさを決めないように、宣言のたびに、その時点の場を組み立て直して確かめる。

| 加えたもの | 確かめること |
|---|---|
| ねむり・マヒ・こんらんの組み立て直し | `special_condition`（`sleep`・`paralysis`・`confusion`。`already` は除く）で付け、`special_conditions_removed`（どの理由でも）で消し、`knock_out` で消す。重ならない（付けるときに、ほかのものが残っていない）。最後に、場のポケモンの `conditions.exclusive` と同じ |
| 特殊能力の宣言（`pokemon_power`） | 宣言した名前・位置が、その時点のいちばん上のカードの特殊能力と同じ。宣言しない特殊能力（`declared` が False）の宣言でない。その時点の場（組み立てたいちばん上のカード・特殊状態）ではたらいているかがくへんかガスに消されている特殊能力でない |

監査が壊れたログを見つけることは tests/test_muk_games_v0_8.py `LogAuditGasTest`（特殊状態の消えたログ → 消されている特殊能力の使用・かがくへんかガスの宣言・ほかの特殊能力の名前・ログのない特殊状態）と変異 26〜28 で確かめた。

監査で見つけられないこと: どくの組み立て直し（かがくへんかガスに関係しないので加えていない）・拒否したコマンド（ログに残らない）。

## 7. ベトベター・ベトベトンのワザ

| ワザ | 実装 | 新しいか | 理由 |
|---|---|---|---|
| どくガス（ベトベター） | `PoisonWithoutDamage` | 新しい | ダメージの目安がない（ダメージの要素がない）。v0.5 の `PoisonOpponent`（どくのこな）はダメージの目安があるワザ用で、`damage` のログを出す。`PutToSleep`（キノコのほうし）と同じ考え方で別にした（M1） |
| ねばりつく（ベトベター） | `CoinBonusDamageAndParalyze(bonus=20)` | 新しい | コイン → 基本となるダメージ（「おもて」なら + 20）→「おもて」かつきぜつしていなければマヒ（M2〜M6）。`check` で「+」のある目安のワザだけに登録できる |
| ヘドロこうげき（ベトベトン） | `PoisonOnHeads` | v0.3a の実装 | ビードルの「どくばり」と同じ処理（M8） |

ワザの実装を加えたので、tests/test_effect_preflight_v0_3d.py の `ATTACKS` に 3 つを加えた（CLAUDE.md。受け付けるか・拒否のコードがコインの結果で変わらない）。

## 8. 既存の仕様の保護

| 仕様 | v0.8 の扱い | 確かめ方 |
|---|---|---|
| R13（`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`） | 変えていない。かがくへんかガスは R13 を決めない（G29）。`energy_attached_by_powers_this_turn` を変えない | `test_r13_is_unchanged`・`test_r13_state`・自然な対戦（5 回止まった）・ストレス実行 |
| じこさいせいの「トラッシュできないとき」（K3。`RuntimeError`） | 起こらないまま。v0.8 は特殊エネルギーを加えず、かがくへんかガスはワザに影響しない（G8）。ベトベター・ベトベトンのワザはエネルギーを動かさない | ストレス実行・自然な対戦で内部の誤り 0 |
| 拒否のコードの順番（v0.6 の変異 19・v0.7 の変異 25） | v0.7 の 12 章の決定のまま（保証しない順番はテストで固定しない）。保証する順番に 2 章の 6・7 を加えた | 13 章・変異 24 |
| エナジートランス・あまごい・ダメージスワップの処理 | `check_usable`・`resolve` は変えていない。かがくへんかガスがはたらいていなければ v0.7 と同じ | v0.7 のテストを v0.8 のコードで実行（11 章）・前の版との比較（10 章）・ストレス実行のベトベトンのいない組（v0.7 と同じ数） |
| 比較の駆動・参照データ | tools/compat_driver.py・tests/fixtures/compat_base_4bd97bf.json・tests/fixtures/v0_1_reference.json を変えていない（作り直していない） | `git diff` |

## 9. 変えたもの

| 場所 | 変更 | 理由 |
|---|---|---|
| kyuura_engine/continuous.py | 加えた（`working_power_suppressors`・`suppressors_of`・`power_suppressors`） | 1 章 |
| `effects.PowerEffect.declared` | 加えた（クラス変数。既定 True） | 常にはたらく特殊能力を区別する（[continuous-effects-v0.8.md](continuous-effects-v0.8.md) 1 章） |
| `effects.SuppressOtherPowers` | 加えた（かがくへんかガス。`exempt_name`・`is_working`・`suppresses`） | G1〜G33 |
| `effects.PoisonWithoutDamage`・`effects.CoinBonusDamageAndParalyze` | 加えた | 7 章 |
| `effects.DEFAULT_EFFECTS` | id を `kyuura-engine-0.8` に。ワザ 3 つ（47 → 50）とパワー 1 つ（3 → 4）を加えた | 登録の中身が変わった |
| `engine._use_pokemon_power` | 2 章の 6・7 を加えた | — |
| `kyuura_engine.__init__` | `power_suppressors`・`working_power_suppressors` を公開。`__version__` を `0.8.0`（pyproject.toml も） | 画面などが、使えない理由をコマンドを送らずに調べるため |
| `cards.POOL_KEYS` | `pool_v0_8` を加えた | 写しの対戦用のカードの組 |
| scripts/extract_kyuura_cards.py・kyuura_engine/data/kyuura_cards.json | `POOL_V0_8`（ロケット団のベトベター・ベトベトン）と、参照カード（`REFERENCE_ONLY`）に化石の秘密のベトベター（PMCG3-003）を加えて写しを作り直した（参照コミット `ecb2d694` のまま。`--check` で一致） | ベトベトンの進化元。化石の秘密のベトベターは「ちいさくなる」が未実装で、デッキに入らないことを確かめるため |
| kyuura_engine/data/card_verification.json | PMCG4-004・PMCG3-007・PMCG3-003 の照合の記録を加えた（PMCG3-007 には p.323 の例 `power_rules_example_ja` も） | 照合してから登録する（CLAUDE.md） |
| tests/log_audit.py | 6.1 | — |
| tools/stress_engine.py | ベトベトンの 2 組（`muk`・`muk_mixed`）。ベトベトンが場にいる番はときどきかがくへんかガスの使用を試す（`POWER_NOT_DECLARABLE` になるはず）。特殊能力の使用のたびに、公開の関数 `power_suppressors` で消されているかを求め、受け付けた・拒否したことと食い違えば問題として数える。`POWER_USERS` の最後にベトベトンを加えたので、ベトベトンのいない組は v0.7 と同じ操作 | 段階 C のストレス実行 |

## 10. 変えなかったもの

- コマンドの種類・段階（`Phase`）・決定の種類・再開先・書き出しの形式（9 のまま）・状態の項目・ログのイベントの種類。
- 乱数の使い方（かがくへんかガスは乱数を使わない。どくガスはコインなし。ねばりつく・ヘドロこうげきはコイン 1 枚）。
- 既存のルールの処理・裁定の分類・処理の順番。v0.7 までの 12 の `UNRESOLVED_…` のコード（新しいコードは加えていない）。**R13 は変えていない**。
- 固定値: tests/test_reproducibility.py、各対戦のテストの `GOLDEN_DIGEST`・`EXPECTED_COUNTS`、tests/fixtures/v0_1_reference.json・tests/fixtures/compat_base_4bd97bf.json。
- 比較の駆動（tools/compat_driver.py）。

## 11. 前の版との比較

`python3 tools/compare_engine_versions.py --base 22cbe24`（v0.7）: 8 つの組・50 局・11,377 手（受け付けた 6,005・拒否 5,322・内部の誤り 0）・形式の書き出し 91,016 で、食い違いはなかった（[v0.8-verification.md](v0.8-verification.md) 3.2）。比べないのは効果の登録表の id だけ（`kyuura-engine-0.7` → `kyuura-engine-0.8`）。駆動は `UsePokemonPower` を送らず、比べた組にベトベター・ベトベトンはいないので、この比較は「ベトベトンのいない対戦の結果が変わらない」ことを確かめたもので、かがくへんかガスの正しさは単体テスト・自然な対戦・ストレス実行・変異テストで別に確かめた。

## 12. 変えた既存のテストと理由

どのテストも、確かめる内容（意図）は弱めずに、v0.8 の変更に合わせて値・一覧を直した。テストのバグの修正は、v0.8 では v0.7 までのテストにはなかった。v0.7 のテストを v0.8 のコードで実行した結果は [v0.8-verification.md](v0.8-verification.md) 4.3。

| テスト | 変更 | 理由の種類 |
|---|---|---|
| tests/test_cards.py `test_v0_1_pool_is_ten_basic_pokemon_and_six_basic_energy` | `pool_v0_8` を確かめ、v0.1 の組の数え方からベトベター・ベトベトンを除いた | 件数の変化（写しに v0.8 の組を加えた） |
| tests/test_effects.py `test_attacks_with_text_follow_the_verified_latest_description`・`test_with_and_without_do_not_change_the_original` | 説明文のあるワザの一覧にヘドロこうげき・どくガス・ねばりつくを加え、ワザの登録の数を 47 → 50、パワーを 4 つにした | 件数の変化 |
| tests/test_pokemon_powers_v0_5.py `test_default_registry_registers_only_energy_trans`・`test_registry_methods_keep_the_other_registrations` | 登録は 4 つ（かがくへんかガスを加えた）。`repr` の「4 powers」 | 登録表の変化 |
| tests/test_pokemon_powers_v0_5.py `test_registration_follows_the_verified_latest_description` | 図版の印刷の文面が kyuura の写しと違うと読めたとき（ベトベトンの「すべて／全て」）は、照合の記録の不一致（`mismatches`）に kyuura の値と図版の読みが書いてあることを確かめる（登録の照合は kyuura の写しの値のまま） | 照合の記録の形（図版の読みを kyuura の写しと別に記録した最初のカード） |
| tests/test_effect_preflight_v0_3d.py `ATTACKS`・`EVOLVED_FROM` | どくガス・ねばりつく・ヘドロこうげきを加えた | CLAUDE.md（ワザの実装を加えたら `ATTACKS` にも加える） |
| tests/test_trainers.py・tests/test_rng_and_serialize.py・tests/test_damage_swap_v0_7.py・tests/test_rain_dance_v0_6.py・各対戦のテストの `GOLDEN_DIGEST` の前の `effects`（v0.4a・v0.4b・v0.4c・v0.4d・v0.5・v0.6・v0.7） | 登録表の id を `kyuura-engine-0.8` にした（固定値の指紋は変えていない） | 登録表の id |
| tests/helpers.py | ロケット団のベトベター・ベトベトン・化石の秘密のベトベターの定数を加えた | — |

## 13. 拒否のコードの順番（API の約束の更新）

v0.7 の 12 章の約束に、v0.8 の 2 つのコードを加えた。

**API の約束として保証されている順番**（テストで固定している）:

1. コマンドの型（`BAD_COMMAND`）→ 対戦の終わり・止まり → 段階・プレイヤー・番（`_require_turn`）→ 共通の確認（使うポケモン・特殊能力の有無・登録）→ **宣言しない特殊能力（`POWER_NOT_DECLARABLE`）→ かがくへんかガス（`POWER_SUPPRESSED`）**→ パワーごとの確認。パワーごとの確認では、使えない特殊状態を選ばせるものより先に確かめる。テスト: `test_suppression_is_a_common_check`（使うフーディンがこんらんでも、選ばせるものが足りなくても、使わないエネルギーを指定しても `POWER_SUPPRESSED`。番・使うポケモン・特殊能力の位置の誤りは今までのコードが先）・`test_the_gas_is_not_declared`・変異 24（見つかる）。
2. 原典で決められないことで止めるコード（`UNRESOLVED_…`）は、ほかの確認がすべて通ったあと。

**保証していない順番**: それ以外の、ルール上の拒否（`IllegalActionError`）の理由どうしの順番（v0.6 の変異 19・v0.7 の変異 25）。v0.7 の 12 章の理由のまま、テストを加えていない。

## 14. この先の変更への提案（実装していない）

例のページは、v0.8 の調査で画像を見たもの（p.52・p.265・p.277・p.323）と、v0.7 の 13 章のもの。カードの処理は照合していない（実装するときに画像で照合する）。

| 種類 | 例 | 要るもの |
|---|---|---|
| 自動的にはたらく特殊能力 | ゴースト［とうめい］（p.159・p.323）・カイリキー［はんげき］（p.192）・メノクラゲ［おくびょう］（p.98） | はたらく時点（ダメージの計算・ダメージを受けたとき・進化させたとき）に、`continuous.suppressors_of` を聞いてから効果を使う。決定を出すものは再開先・`decision_problems` |
| 常にはたらく特殊能力（かがくへんかガス以外） | プテラ［げんしのちから］（p.265 の解説に名前があるだけで、種類・説明は照合していない） | その効果を使う前に `suppressors_of` を聞く。循環しないことの確かめ直し（[continuous-effects-v0.8.md](continuous-effects-v0.8.md) 4 章） |
| 期限のある「特殊能力を消す」効果 | まきちらせ！ベトベトガス（p.265）・ドガースのふしぎなガス（p.52） | 期限を状態に持つ（持続する効果の新しい型または `GameState` の項目）。`suppressors_of` の発生源を広げる。書き出しの形式 10・不変条件・ログの監査の組み立て直し |
| 退化・手札に戻す | 退化させるカード・手札に戻すトレーナー | いちばん上のカードで決めているので、かがくへんかガスはそのまま反映される（G16・G18）。テストを加える |
| 化石の秘密のベトベター | 「ちいさくなる」（p.47） | ワザによって受けるダメージを減らす持続する効果（p.321 の 8 段階）。v0.4b の持続する効果の型を加える |
| 回数の制限（「自分の番ごとに1回」） | v0.7 の 13 章のとおり | 消されている間の使用は回数に数えない（宣言もない）ことを、回数の記録と合わせて確かめる |
| R13 が決まったら | — | v0.6 と同じ |
