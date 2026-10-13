# 設計の変更（v0.13）

v0.13 では、わるいカメール（PMCG4-021）のワザ「こうらがえし」「おうふくびんた」と、第4弾のゼニガメ（PMCG4-018）の「こうらアタック」を対応にしました。v0.12 の `state.Retaliation`（固定の量を返す「ほのおのかべ」）を、受けたダメージと同じ量を返す形にも使えるように、最小限に広げました。

関連する文書:

- 裁定: [shell-attack-v0.13.md](shell-attack-v0.13.md)
- カードの照合: [dark-wartortle-v0.13.md](dark-wartortle-v0.13.md)
- 仕組みと設計案の比較: [variable-retaliation-v0.13.md](variable-retaliation-v0.13.md)
- 確かめた結果: [v0.13-verification.md](v0.13-verification.md)

## 1. v0.12 の前提

[architecture-v0.12.md](architecture-v0.12.md) と [temporary-attack-effects-v0.12.md](temporary-attack-effects-v0.12.md) のとおりです。

- 持続する効果 `Retaliation` は、効果を持つポケモンの `persistent_effects` にあります。
- 判定は `deal_attack_damage`、与えるのは `finish_damage_elements`（`_apply_retaliation`）です。
- 返すダメージは、効果を与えたワザによるダメージとして `deal_attack_damage` を通します。
- W24（両方のきぜつ）は、宣言の前に `UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT` で止めます。

## 2. `Retaliation` の拡張（B2。案 B）

| 項目 | v0.12 | v0.13 |
|---|---|---|
| `amount` | `int`（10） | `int | None`。`basis` が `fixed` なら整数、`received_damage` なら None |
| `basis` | なし | `str`。既定は `RETALIATION_FIXED`（`"fixed"`）。`RETALIATION_RECEIVED`（`"received_damage"`）を加えた |
| `kind` | クラスの値 `"retaliation"` | 決め方から求める値（property）。`fixed` は `"retaliation"`（v0.12 と同じ）、`received_damage` は `"retaliation_received_damage"` |
| `base_damage(received)` | なし | 与えるダメージの基本となるダメージ。`fixed` は `amount`、`received_damage` は `received` |
| 値の確認 | なし | `__post_init__` が組を確かめる（`ValueError`） |

- `kind` はクラスの値から property になりました。`Retaliation.kind`（クラスから読む）を使っていた `DamageAndRetaliation.resolve` の 1 か所は、`RETALIATION_KINDS[RETALIATION_FIXED]` にしました。
- 固定の量の効果の値・ログ・書き出しは、v0.12 と同じです。
- `repr` には `basis='fixed'` が加わります（README の v0.12 の例の出力を直した）。

設計案（A〜D）の比較は [variable-retaliation-v0.13.md](variable-retaliation-v0.13.md) 2 章にあります。

## 3. 受けたダメージの受け渡し（B3）

- `effects.PendingRetaliation` に `received`（受けたダメージ = その要素の最終ダメージ）を加えました。
  - `deal_attack_damage` が、ダメージをのせる直前に記録します（v0.12 の記録に値を足しただけ）。
  - `base_damage` property は `effect.base_damage(received)` です。
- `_apply_retaliation` は、基本となるダメージを `pending.base_damage` にしました。v0.12 は `pending.effect.amount` でした。
- 受けたダメージはワザ 1 回の中の値（`AttackUse.retaliations`。比較・表示に含めない）で、状態の項目にしていません。

## 4. 新しいワザの実装

- `effects.ReturnReceivedDamage`（`implementation_id` `return_received_damage`）
  - ダメージの目安のないワザだけを登録できます（`check`）。
  - `resolve` は、自分に `Retaliation(basis=received_damage, amount=None, active_turn=番 + 1, attack_index=位置)` を与えるだけです（コインなし・乱数なし）。
  - `retaliation_terms()` は `("received_damage", None)` を返します。
- `DamageAndRetaliation` にも `retaliation_terms()`（`("fixed", 10)`）を加えました。
  - 不変条件（`engine._retaliation_problems`）は、v0.12 の「`DamageAndRetaliation` で量が同じ」を、「登録された実装の `retaliation_terms()` が効果の `(basis, amount)` と同じ」に広げました。
  - ログの監査も同じ考えで照らします。
- おうふくびんたは既存の `CoinFlipDamage(coins=2, damage_per_heads=10)`、こうらアタックは `DAMAGE_ONLY` です。

## 5. 保存形式（B8）

形式 9 のままです（[variable-retaliation-v0.13.md](variable-retaliation-v0.13.md) 8 章）。

- `persistent_effects` の種類に `"retaliation_received_damage"` を加えました。項目は `attack_index` だけで、`amount` は書きません。
- 種類の値を加えただけで、項目の意味を変えていないので、形式 10 は要りません。
- 監査の `LATEST_FORMAT` も 9 のままです。

## 6. 処理の順番（B4）

[variable-retaliation-v0.13.md](variable-retaliation-v0.13.md) 4 章のとおりです。v0.12 の時点（`finish_damage_elements`）を変えていません。

## 7. 連鎖（B5）

`_apply_retaliation` は、返すダメージの要素のあとに `fire_use.retaliations` が残っていたら RuntimeError で止めます。

- 返すダメージで別の効果がはたらくことは、番の進み方からありません（S45）。
- 回数の上限で止めるのではなく、起こらないはずのことが起きたらエンジンの不具合として止めます。

## 8. 未解決の裁定の停止（B6・Phase E）

- S37 は W24 と同じ問いなので、`retaliation_double_knockout_problem` を、ダメージの組ごとに返す量を計算する形にしました。
  - v0.12 は返す量を組の外で 1 回だけ計算していました。
  - `found.base_damage(final)` → `preview_attack_damage`。
- 固定の量（ほのおのかべ）の判定は、v0.12 と同じ結果です。
  - 組の外で計算していた 10 の最終ダメージを、組ごとに同じ値で計算するだけです。
  - 返すダメージが 0 になる組は、止めずに次の組を見ます。v0.12 は、その場合すぐに止めない（None を返す）としていました。固定の量では、どの組でも同じ値なので、結果は同じです。
- 理由の文の効果の名前は、決め方から書きます（ほのおのかべ／こうらがえし）。

既存の 22 件の未解決の裁定（v0.12 までの 22 件。コードのある 17 件と、コードのない T27・C34/C35・G40・P19・P32）は変えていません。新しい裁定 ID・コードも加えていません。

- エンジンが止める `UNRESOLVED_…` は 17 件のままです。
- S37 は W24 に、S7 は C34/C35 に含めました（同じ問い）。
- 止める範囲の確認:
  - 止めすぎていないこと（片方だけきぜつするなら止めない）: `test_not_stopped_when_only_one_is_knocked_out`・`test_per_coin_outcome`。止める範囲を広げる変異 32 は、`test_per_coin_outcome`・わるいカメールだけがきぜつするテスト・自然な対戦の数で見つかる。
  - 足りなくないこと: 自然な対戦・ストレス実行で、止めたワザは必ず効果がはたらく相手のときだけだった。不変条件・監査も通る。

## 9. ログ（B9）

[shell-attack-v0.13.md](shell-attack-v0.13.md) 6 章のとおりです。

- 新しいイベントはありません。
- `retaliation` に `basis`・`received_damage` を加えました（こうらがえしのときだけ。ほのおのかべは v0.12 と同じ形）。

## 10. 原子性

- こうらがえしは乱数を使いません。
- S37 の判定は、状態を変えない計算（`preview_attack_damage`）だけを使います。
- 不正な操作は、`apply_command` が clone してから処理するので、状態・ログ・乱数が変わりません。
- エンジンの不具合として止まる RuntimeError（S7・S45）でも、渡した状態は変わりません（`test_two_damage_elements_are_refused_without_a_partial_state`・`test_chain_is_refused_even_in_a_broken_state`）。

## 11. 不変条件

| 確認 | 変更 |
|---|---|
| `_retaliation_problems` | 登録された実装の `retaliation_terms()` と `(basis, amount)` を照らす（v0.12 は `DamageAndRetaliation` の量だけ） |
| `_persistent_effect_problems` | 変えていない。種類（`kind`）が決め方で変わるので、同じ種類の重なり・ログとの対応はそのまま当てはまる |
| `_counter_knocked_out_attacker_awaiting` | 変えていない（返すダメージのログ `damage` の `retaliation` で確かめるので、こうらがえしにも当てはまる） |

## 12. ログの監査（tests/log_audit.py）

v0.13 で加えた確認:

- `retaliation` の決め方が登録と合う。
  - 固定: 量 = 登録の値で、`basis`・`received_damage` を書かない。
  - 受けたダメージ: `basis`・`received_damage` が、きっかけのダメージのログの最終ダメージと同じで、`amount` も同じ。
- 効果の種類が、効果を与えたワザの登録と合う。
- 状態の持続する効果の種類が、ログで与えた種類と同じ（保存・復元で効果が変わったのを見つける）。
- はたらいている効果の組み立て直しに、種類 `retaliation_received_damage` を含める。
- 監査の文の「ほのおのかべ」を「「ほのおのかべ」・「こうらがえし」」にした。v0.12 のテストは文の一部に頼っていない。

ログだけで確かめられないこと:

- 決定の中身（v0.11 と同じ）。
- わるいカメールの受けたダメージが p.321 のどの段階を含むか。ログの `steps` にはあるが、監査は最終ダメージとの一致だけを見る。

## 13. 変えたもの

| ファイル | 変更 |
|---|---|
| kyuura_engine/state.py | `Retaliation` の `basis`・`kind`（property）・`base_damage`・`__post_init__`。`RETALIATION_FIXED`・`RETALIATION_RECEIVED`・`RETALIATION_KINDS` |
| kyuura_engine/effects.py | `PendingRetaliation.received`・`base_damage`、`deal_attack_damage` の記録、`_apply_retaliation`（基本となるダメージ・ログ・連鎖のガード）、`retaliation_double_knockout_problem`（組ごと）、`DamageAndRetaliation.retaliation_terms`、`ReturnReceivedDamage`、登録（id `kyuura-engine-0.13`。こうらアタック・おうふくびんた・こうらがえし）、docstring |
| kyuura_engine/engine.py | `_retaliation_problems`（`retaliation_terms`） |
| kyuura_engine/persistent.py | docstring だけ |
| kyuura_engine/serialize.py | `retaliation_received_damage` の書き出し |
| kyuura_engine/cards.py・scripts/extract_kyuura_cards.py・data | `pool_v0_13`（PMCG4-018・PMCG4-021）。写しを作り直した |
| kyuura_engine/data/card_verification.json | PMCG4-018・PMCG4-021 |
| kyuura_engine/__init__.py・pyproject.toml | 版 0.13.0 |
| tests/log_audit.py | 12 章 |
| tests/helpers.py | `ROCKET_SQUIRTLE`・`DARK_WARTORTLE`。`build_test_state` の `"retaliation_received"` |
| tools/stress_engine.py | 組 `wartortle`・`wartortle_mixed`（最後に加えた）。`_observe_shell`。`_observe_moltres` は「ほのおのかべ」のログだけを数える。W24 で止めたときの確認に「こうらがえし」を加えた |

## 14. 変えなかったもの

- 比較の駆動（tools/compat_driver.py）と参照データ（tests/fixtures/compat_base_4bd97bf.json・tests/fixtures/v0_1_reference.json）。
- 既存の未解決の裁定のコード・止める条件（8 章）。
- 書き出しの形式（9 のまま）。決定・段階・コマンドの種類。
- `POWER_USERS`（わるいカメールはポケモンパワーを持たない）。ほかの組の乱数の使い方は v0.12 と同じ。組ごとの乱数は組の名前から作る。
- 参照する kyuura のコミット（`ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`）。kyuura は変更していない。

## 15. 変えた既存のテストと理由

| テスト | 理由 |
|---|---|
| 自然な対戦の固定値のテスト（v0.4a〜v0.12 の `…_games_…`）・tests/test_rng_and_serialize.py・tests/test_trainers.py・tests/test_chemical_gas_v0_8.py・tests/test_rain_dance_v0_6.py・tests/test_damage_swap_v0_7.py | 登録表の id が `kyuura-engine-0.13` になった（固定値の指紋は変わらない） |
| tests/test_cards.py・tests/test_effects.py | 対応カード・ワザの一覧に第4弾のゼニガメ・わるいカメールを加えた（ワザの登録 62 → 65） |
| tests/test_effect_preflight_v0_3d.py | `ATTACKS` に 3 つのワザ、`EVOLVED_FROM`・`COIN_DAMAGE` にわるいカメールを加えた（CLAUDE.md の約束） |

## 16. 次の版への提案（実装していない）

- 同じタイプのワザ「クロスカウンター」（R団のエビワラー。p.203。コインと 2 倍）を加えるなら、次の 2 つを照合して決めます。
  - `basis` の値を加える（[variable-retaliation-v0.13.md](variable-retaliation-v0.13.md) 10 章）
  - コインを投げる時点と、S37 と同じ問いの判定（コインのすべての結果）
- カスミのヒトデマン（スターブーメラン）を加えるなら、次の 2 つを原典で確かめてから実装します。模擬のワザのテスト（`StarBoomerangMockTest`）は、その実装に置きかえられます。
  - 手札にもどす処理
  - バトル場の補充（ワザを使ったポケモンが場をはなれたとき）
- 1 つのワザで効果を持つポケモンが 2 回以上ダメージを受けるワザ（S7）を加えるときは、宣言の前に止める処理を先に加えます。
