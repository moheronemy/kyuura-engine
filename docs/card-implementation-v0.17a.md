# 既存のワザの要素だけで実装したカード（v0.17a）

[card-selection-v0.17a.md](card-selection-v0.17a.md) で選んだ 2 枚を、解決の基盤（KERNEL）の既存の要素だけで加えた記録です。
2 枚は次のとおりです。

- モンジャラ（PMCG1-007。p.55）
- サカキのニャース（PMCG6-063。p.229）

仮説 H1（既存の要素で足りる。`engine.py`・`resolution/kernel.py` を変えず、新しい共通の関数も加えない）を確かめます。

## 1. 結論

**H1 は成り立った。**

- モンジャラは登録だけで加えた。v0.13 の 24 種類のうちの `ParalyzeOnHeads`・`PoisonOpponent` を使う。
- サカキのニャースの「ねこノミ」は、既存の要素 `Status(CONFUSION, local_coin=HEADS)` だけの並びで加えた。
  - 加えたものは、実装の型 `ConfuseOnHeadsWithoutDamage` と、`programs.BUILDERS` の 1 行。
  - 「ねこキック」は `DamageOnly`。

変えなかったもの・変えたもの:

- 変えなかった:
  - `engine.py`・`resolution/kernel.py`・`resolution/catalog.py`・`resolution/flow.py`・`resolution/preflight.py`
  - `resolution/contract.py`・`resolution/v013_checks.py`
  - 状態の型・書き出しの形式 9・ログのイベントの種類
- 新しい共通の関数・新しい裁定・新しい `UNRESOLVED_…` は加えていない。

| 区分 | ファイル | 変更 |
|---|---|---|
| 登録・実装の型 | `kyuura_engine/effects.py` | +56 行。`ConfuseOnHeadsWithoutDamage`（30 行。`check` と説明）と、登録表の 4 件（ワザ 3 件と説明文のないワザ 1 件） |
| 要素の並び | `kyuura_engine/resolution/programs.py` | +3／−1 行（`BUILDERS` の 1 行・注釈・見出しの注釈） |
| カードの組 | `kyuura_engine/cards.py`・`scripts/extract_kyuura_cards.py` | 対戦用の組 `pool_v0_17a` |
| データ | `kyuura_engine/data/kyuura_cards.json` | 写しの作り直し（`python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura`。手で編集していない） |
| データ | `kyuura_engine/data/card_verification.json` | 照合の記録 2 件 |
| テスト | `tests/test_existing_elements_v0_17a.py`（新規）・`tests/v017_games.py`（新規。v0.17 の対戦の共通の手順） | 4 章 |
| テスト（一覧の更新） | 5 章 | 登録の数・実装の型の数など、一覧を数えるテストの期待値を、加えたカードの分だけ更新した |

新しいカードは、v0.13 の約束（`AttackEffect.resolve`・`resume`）に依存していません。

- `ConfuseOnHeadsWithoutDamage` は `resolve`・`resume` を上書きしない。
- 解決の基盤は、要素の並び（`compile_attack`）で処理する。
- `contract.program_for` がアダプタ（`Contract`）を選ばないことを、テストで確かめた。

## 2. 処理の順番の確認

どの順番も、要素の並びと解決の基盤の窓が決める既存の順番です。カードごとの `finish_damage_elements` にあたる処理は作っていません。

| 確かめた点 | しめつける（ダメージ → コイン → マヒ） | どくのこな（ダメージ → どく） | ねこノミ（コイン → こんらん） | 根拠 |
|---|---|---|---|---|
| ダメージと効果の順番 | ダメージ → ワザのコイン → マヒ | ダメージ → どく | ダメージの要素なし | p.320（要素は書かれた順）・p.309 |
| ダメージを受けたときの自動的な効果 | ダメージ → 「はんげき」の 10 → コイン → マヒ | ダメージ → 「はんげき」→ どく | ダメージがないので、はたらかない | p.89（ダメージの処理のあと、ダメージ以外の効果の前）・v0.10 |
| 「とうめい」 | ダメージで「おもて」になりうると、ワザのコインが決まらない（T19b）ので、宣言の前に `UNRESOLVED_EVADED_EFFECT_COIN` | 「とうめい」のコイン 1 回（T4）。「おもて」ならダメージもどくも受けない | ワザのコイン（ニャース側）→「おもて」のときだけ「とうめい」のコイン（ゴースト側） | p.159・p.160・T4・T19・T19b・T22・T33 |
| 相手がきぜつする | コインを投げない（効果の対象がいない） | どくにしない | ダメージがないので起こらない | p.309・p.323 |
| 自分がきぜつする（はんげき） | そろってきぜつしうるなら C18 で宣言の前に止める | 同じ | 起こらない | v0.10 の C18 |
| ダメージが 0（ディフェンダー） | コインを投げ、「おもて」ならマヒ | どくにする | 関係しない | p.321（効果の要素は有効）・v0.3c |
| 「ダメージを受けない」状態（かたまる） | 効果の要素は有効（T19b の対象外。ダメージの要素は無効） | 同じ | こんらんにする | p.321 |
| コインの使い方 | ワザのコイン 1 枚（マヒの再付与の確認はコインの前） | なし | ワザのコイン 1 枚（+「とうめい」1 枚） | p.309・v0.3b |
| 対象がいない（控えがない等） | 関係しない | 関係しない | 関係しない | — |
| 宣言の前の先読み | `derived`（コインのすべての結果を試す。上限の 4,096 に届かない） | 同じ | 同じ | v0.15c・v0.16c |

## 3. 裁定の扱い

新しい裁定は加えていません。当てはめた既存の裁定:

- v0.3a〜v0.3c の特殊状態（重なり・置きかわり・どくはほかと重なる）
- v0.3b のマヒの再付与の確認
  - しめつけるは `reparalysis_check` つき。
  - 相手のワザでは、回復する番が変わる場合は起こらない（v0.3b の説明）。
- v0.9 の T4・T19・T19b・T22・T33
- v0.10 の C18・p.89 の時点

サカキのニャースの「ねこノミ」の「とうめい」との順番（ワザのコイン → 「とうめい」のコイン）について:

- 新しい問いではない。
- T19（要素の順番どおり。SUPPORTED）と T22（ダメージのない特殊状態のワザは、効果を受けるときにコイン。CONFIRMED）の当てはめ。
- ワザのコインが「うら」なら効果を与えないので、ゴーストは受けない（「とうめい」のコインはない）。

## 4. テスト

`tests/test_existing_elements_v0_17a.py`（29 件）:

- `RegistrationTest`（5）
  - 分類（対応・対戦で使える）、登録と最新の説明・出典・照合の記録
  - 要素の並び（既存の要素だけ。アダプタでない）
  - 新しい型が v0.13 の約束を持たないこと・`VERIFIED` に入っていないこと
  - 登録の照合（`check`）
- `TangelaTest`（11）
  - 通常の使用（「おもて」「うら」）・どくのこな（コインなし）
  - エネルギー不足（`INSUFFICIENT_ENERGY`。状態・乱数・ログが変わらない）
  - ねむり・マヒでワザを宣言できない（`POKEMON_ASLEEP`・`POKEMON_PARALYZED`）
  - 弱点（ディグダ。40 できぜつしてコインを投げない）
  - プラスパワー（30）・ディフェンダー（0 でもマヒ・どく）
  - 「とうめい」（しめつけるは T19b で止まる・どくのこなは 1 回のコイン）
  - 「はんげき」の時点・C18 で止まる
  - マヒの再付与（回復する番が変わらない）
- `GiovannisMeowthTest`（8）
  - 「おもて」「うら」（ダメージのログがない）
  - ねむり → こんらん・どくはそのまま
  - 「とうめい」のコインの順番（3 通り）
  - 「ダメージを受けない」状態の相手にもこんらん
  - ダメージがないので「はんげき」はない
  - こんらんのニャース（自分に 20。「おもて」ならねこノミ）
  - ニャースの弱点（闘 40）・抵抗力（超 50 − 30 = 20）
  - 不正なコマンドの原子性
- `NaturalGamesTest`（4）: `new_game` から 80 局。4 つのワザを使い、次が起こることを確かめる（1 回も起こらない試験を成功と数えない）。
  - 起こること:
    - マヒ・どく・こんらんを与える
    - 「とうめい」の評価（どくのこなのダメージ・ねこノミのこんらん）
    - 新しいカードのワザでの「はんげき」
    - T19b の停止
  - 確かめること:
    - 不変条件・ログの監査・書き出しの監査
    - 乱数はコインだけ
    - 同じ seed・同じ操作の列で同じ結果
    - 新しいカードのワザの直前に保存（pickle）して再開しても同じ
  - 止まった 2 局（seed 14・27）は、対戦準備の既存の未解決の裁定（`UNRESOLVED_MULLIGAN_COMPENSATION`。v0.1 から）。
- `GoldenGameTest`（1）
  - seed 3（4 つのワザをすべて使う）の結果の固定値（3.11・3.12・3.13 で同じ）。

`tests/v017_games.py`:

- v0.13 の対戦の手順（`tests/test_dark_wartortle_games_v0_13.py` の `policy_command`。v0.4e〜v0.13 の手順を重ねたもの）を、デッキを引数にして使う共通の手順。
- 拒否された操作は、場から確かめてから数える（知らない拒否は失敗）。
- v0.17b で、宣言しない特殊能力・止める理由を引数で加える。

## 5. 既存のテストの更新（一覧を数えるテスト）

カードと実装の型を加えたので、登録表・カードの組・実装の型の一覧を数えるテストの期待値を、加えた分だけ更新しました。

- どのテストも、確かめる性質は変えていません。
- 新しいカードも同じ確認を受けます（期待を弱めていない）。

| テスト | 更新 | 理由 |
|---|---|---|
| `tests/test_effects.py` `test_attacks_with_text_follow_the_verified_latest_description` | 説明文のあるワザの一覧に 3 件（PMCG1-007#0・#1、PMCG6-063#0） | 新しい登録も、照合の記録の最新の説明と合うことを確かめる |
| 同 `test_with_and_without_do_not_change_the_original` | 登録の数 65 → 69 | 4 件の登録 |
| `tests/test_cards.py` | `pool_v0_17a` の確認を加え、「v0.1 の組」の数から除く | 対戦用の組を加えた |
| `tests/test_event_kernel_v0_14.py` `CatalogTest` | 実装の型の数を「v0.13 の 24 種類 + v0.17 から加えた型」に | 新しい型も要素の並びの対応表にある |
| `tests/test_preflight_v0_15c.py` `test_verified_implementations_are_the_v0_13_ones` | `VERIFIED` = 登録された型 − v0.17 から加えた型（24 種類のまま） | v0.13 の止める関数の型に新しい型を自動では加えない（v0.16c） |
| `tests/test_guts_v0_11.py` `G37Test` | 相手に効果を与える型の数 9 → 10 | 新しい型も宣言（`opponent_effect_elements`）と要素の並びが一致する |
| `tests/test_transparency_v0_9.py` `EvadedEffectCoinTest` | T19b で止めるワザの一覧に「しめつける」 | 新しい登録も宣言の前に止まることを確かめる |
| `tests/test_effect_preflight_v0_3d.py` `CoinIndependenceTest` | `ATTACKS` にねこノミ | 受け付けるかがコインの結果で変わらない（CLAUDE.md の約束） |

v0.17 から加えた型の一覧（`tests/helpers.py` の `ATTACK_TYPES_SINCE_V0_17`）を 1 か所に置き、上のテストはそこから数えます。
