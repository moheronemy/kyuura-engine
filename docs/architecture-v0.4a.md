# v0.4a のアーキテクチャ（進化: たねポケモン → 1 進化ポケモン）

v0.4a は、`EvolvePokemon` を対応にし、1 匹の場のポケモンが複数の物理カード（たねポケモンと 1 進化ポケモン）で構成される状態を扱えるようにした版です。対応カードはパラセクト（PMCG2-010。パラスから進化）とジュゴン（PMCG1-030。パウワウから進化）です。

- 進化のルールの原典照合: [evolution-rules-v0.4a.md](evolution-rules-v0.4a.md)
- カードの照合: [evolution-cards-v0.4a.md](evolution-cards-v0.4a.md)
- 状態の持ち方・総合テスト・負荷テスト: [evolution-state-v0.4a.md](evolution-state-v0.4a.md)
- v0.3d での準備の調査: [evolution-readiness-v0.4.md](evolution-readiness-v0.4.md)

v0.3d の設計（[architecture-v0.3d.md](architecture-v0.3d.md)）の上に作っています。

## 1. 目的と範囲

- `EvolvePokemon` を、公式ルールの進化の条件（p.309・p.310）で検査して処理する。
- 進化したポケモンのカードの重なりを状態に持ち、カードの保存則を保つ。
- ダメージ・エネルギー・ついているトレーナー・場のポケモンの番号を受け継ぎ、特殊状態・にげるの失敗の記録を消す。
- いちばん上のカードの定義（ワザ・HP・タイプ・弱点・抵抗力・にげる）を使う。
- 進化したポケモンのきぜつで、重なったカードをすべてトラッシュし、サイドは 1 枚。
- 進化カードを使わない既存の対戦の結果を変えない（9 章の比較）。

作らなかったもの: 2 進化・退化・ベイビィポケモンの進化・進化に関わるポケモンパワー・トレーナー・持続する効果、ゲーム状態全体の読み込み、汎用のカード効果の仕組み。

## 2. v0.3d からの変更

| 項目 | v0.3d | v0.4a |
|---|---|---|
| `EvolvePokemon(player, card, target)` | `UnsupportedError`（`UNSUPPORTED_ACTION`） | 処理する。`target` は場のポケモンの番号（`pokemon_id`）。`UNSUPPORTED_COMMANDS` は `UsePokemonPower` だけ |
| `PokemonInPlay` | `card`（カード 1 枚） | `evolution_stack`（下のカード）・`played_turn`（場に出た番）・`evolved_turn`（進化した番）を加えた。`current_form_turn`・`cards()` |
| `CardDefinition` | — | `evolves_from`（「○○から進化」の名前）・`is_stage1_pokemon` |
| カードの分類 | たねポケモン以外は未対応 | 1 進化（進化元の名前がある）を対応にした。2 進化・ベイビィは未対応のまま |
| `_enter_play` | 番号だけ付ける | 場に出た番も記録する |
| `_knock_out` | トップのカード・エネルギー・トレーナーをトラッシュ | 重なったカードもトラッシュ。ログに `evolution_stack`（進化していれば） |
| 特殊状態を消す理由 | `retreat`・`switch`・`sleep_coin`・`paralysis_end`・`replaced` | `evolve` を加えた |
| ログ | — | `evolve`・`retreat_failure_cleared` を加えた |
| エラーコード | — | `NOT_EVOLUTION_CARD`・`FIRST_TURN_EVOLUTION`・`EVOLUTION_NAME_MISMATCH`・`PLAYED_THIS_TURN`・`EVOLVED_THIS_TURN`（`IllegalActionError`）、`UNSUPPORTED_EVOLUTION`・`UNRESOLVED_EVOLUTION_HP`（`UnsupportedError`） |
| 不変条件 | — | 重なったカードの保存則、重なりの形、場に出た番・進化した番、進化のあとの特殊状態、進化のあとのにげるの失敗の記録 |
| 状態の書き出し | 形式 1〜6 | 形式 7（場のポケモンごとに `evolution_stack`・`played_turn`・`evolved_turn`）。形式 1〜6 は進化したポケモンがいれば `ValueError` |
| 効果の登録表 | id `kyuura-engine-0.3c`、ワザ 22 | id `kyuura-engine-0.4a`、ワザ 26（パラセクト 2・ジュゴン 2）。トレーナーは同じ 5 枚 |
| カードデータの写し | `pool_v0_3c` まで | `pool_v0_4a`（PMCG2-010・PMCG1-030）。作り直して `--check` で一致 |
| ルールの根拠の一覧（`RULE_REFERENCES`） | — | `evolution`・`evolved_pokemon` を加えた |
| 版 | `0.3.0d0` | `0.4.0a0` |

コマンドの種類・段階（`Phase`）・決定の種類は増やしていません。

## 3. PokemonInPlay とカードの重なり

[evolution-state-v0.4a.md](evolution-state-v0.4a.md) 3・4 章。要点:

- `card` はいちばん上のカードのまま（v0.1 からの処理がそのまま正しい）。下のカードは `evolution_stack`（下から順のタプル）。
- 場のポケモンの番号は進化しても変えない。ルールの上の「別のポケモン」は、いちばん上のカード・`evolved_turn`・特殊状態・失敗の記録で表す。
- 場に出た番・進化した番は明示的な項目（ログからは求めない）。

## 4. EvolvePokemon の検査と状態遷移

```
EvolvePokemon(player, card, target)
  → 項目の型（BAD_COMMAND）→ 終わった・止めた対戦（GAME_OVER など）
  → 自分の番（WRONG_PHASE・INVALID_PLAYER・NOT_YOUR_TURN。決定を待つ間は WRONG_PHASE）
  → 手札（CARD_NOT_IN_HAND）→ 進化カード（NOT_EVOLUTION_CARD）→ 対応している 1 進化（UNSUPPORTED_EVOLUTION）
  → 自分の場のポケモンの番号（TARGET_NOT_YOURS・TARGET_NOT_IN_PLAY）
  → 最初の番（FIRST_TURN_EVOLUTION）→ 名前（EVOLUTION_NAME_MISMATCH）
  → その番の最初から場にいた（EVOLVED_THIS_TURN・PLAYED_THIS_TURN）
  → 進化したあとの HP がダメージより大きい（UNRESOLVED_EVOLUTION_HP）
  ── ここまで状態も乱数も変えない ──
  → 手札から出し、重ねる（card ← 進化カード、evolution_stack に前のトップ、evolved_turn ← 今の番）→ ログ evolve
  → 特殊状態を消す（clear_special_conditions(EVOLVE)）
  → にげるの失敗の記録を消す（retreat_failure_cleared）
  → 番は続く（MAIN）
```

- 決定を出さず、乱数を使わない。1 つのコマンドの中で終わる（p.310「進化させている最中は…他のことはできません」）。
- `apply_command` は複製で処理し、返す状態を `check_invariants` で確かめる（v0.1 から）。

## 5. カードの定義

進化したポケモンは、いちばん上のカードの定義（`state.card_def(pokemon.card)`）だけを使います。v0.1 から、ワザ（`UseAttack.attack_index` はいちばん上のカードのワザの位置）・HP（きぜつの判定）・タイプと弱点・抵抗力（ダメージ計算）・にげるエネルギー・書き出しの `hp` は、どれもいちばん上のカードを見ているので、処理は変えていません。効果の登録表はカード id とワザの位置で引くので、パラスとパラセクトの同じ名前のワザ（キノコのほうし）は別の登録です。

v0.1 からのコマンドが場のポケモンを指す uid（`AttachEnergy.target`・`Retreat.new_active`・`PromoteActive.pokemon`）は、いちばん上のカードの uid です。下のカードの uid では指せません（`TARGET_NOT_IN_PLAY`・`NOT_ON_BENCH`）。v0.2a の移行の方針では「重なりのどのカードの uid でも、そのポケモンを指す」案を挙げていましたが、そのポケモンを表すのはいちばん上のカード（p.310）なので、いちばん上のカードだけにしました（あいまいさをなくすため）。

## 6. きぜつ・サイド

[evolution-state-v0.4a.md](evolution-state-v0.4a.md) 6 章。`_knock_out` は `pokemon.cards()`（下のカード → いちばん上）・エネルギー・ついているトレーナーをトラッシュします。サイドの数（`_after_knockouts`）は、きぜつ 1 匹につき 1 枚のまま変えていません。

## 7. 保留中の決定・乱数

- 進化は決定を出しません。決定を待つ間（サイド・交代・トレーナー・ワザの効果の途中）は、進化のコマンドを受け付けません。
- 進化は乱数を使いません。拒否された進化も乱数を使いません（`apply_command` の原子性。総合テスト・負荷テストのすべての拒否で確かめた）。

## 8. 状態の書き出し（形式 7）・不変条件

[evolution-state-v0.4a.md](evolution-state-v0.4a.md) 7・8 章。形式 7 は形式 6 に項目を加えただけで、進化していない状態では、形式 6 に `evolution_stack: []`・`played_turn`・`evolved_turn: None` を加えたものと同じです（テストで確かめた）。

## 9. 互換性と検査

### v0.3d（`3654be2`）との比較

v0.3d のコードを `git archive` で取り出し、同じ入力で次を動かしました。終わった状態（形式 6。登録表の id を除く）・ログ・乱数の状態・結果・止めた理由・拒否のコードの列が、**すべて同じ**でした。

1. 既存のデッキ（特殊状態のない 7 組 × 40 seed、ビードル 40、キャタピーだけ・パラスだけ 30 ずつ、v0.3b の混ぜたデッキ 60 + 300、ビードルのミラー 400、v0.3c のこんらんのデッキ 100 + 100）: 1,340 局・121,420 コマンド。ビードル・混ぜたデッキ・こんらんのデッキの seed 0〜19 は、途中のすべての状態（ポケモンチェックの中の決定を含む）も同じ。
2. でたらめな操作を混ぜた 32 局（8,162 コマンドのうち 4,437 回の拒否）: 拒否のコードの列と終わった状態が同じ。
3. v0.3d の 4 種類の特殊状態を混ぜたデッキの 300 局（44,122 コマンド）: 途中のすべての状態が同じ。

止まった局（`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`・サドン・デスなど）も同じ局・同じ状態です。v0.1 の参照データ・乱数とコインの固定値（test_reproducibility.py・test_coins.py・test_coin_games.py・test_pikachu_games.py・test_weedle_games.py・test_sleep_paralysis_games.py・test_confusion_games.py・test_status_games_v0_3d.py の `GOLDEN_DIGEST`・`EXPECTED_COUNTS`）は変えていません。新しく加えた `played_turn`・`evolved_turn` は形式 1〜6 に出ないので、既存の書き出しは変わりません。

### v0.3d のテストを v0.4a のコードで実行した結果

v0.3d のテスト 726 件のうち、714 件が通り、11 件（下の表。subTest で数えると 22）が失敗し、1 件が skip でした（skip は、比較用のディレクトリの位置で `../kyuura` がないため）。失敗は、どれも「進化は未対応」「登録表の内容」「形式の一覧」を確かめていたものです。

### 変更した既存のテスト

| テスト | 変更 | 理由・保証が弱くなっていない理由 |
|---|---|---|
| test_compat_v0_1.py `test_replay_gives_the_same_results_as_v0_1` | `NOW_SUPPORTED` に `evolve_pokemon` | v0.1 の参照データの 43 回の進化のコマンドが、ルールによる拒否（`CARD_NOT_IN_HAND` 4・`INVALID_PLAYER` 16・`NOT_YOUR_TURN` 8・`WRONG_PHASE` 15）に変わる。どれも許したコードの集合の中で、最後の状態の完全な一致は同じように確かめる。参照データは変えていない |
| test_state_integrity.py `test_every_command_in_every_phase` | MAIN で `EvolvePokemon` を受け付ける。ほかの段階では `WRONG_PHASE`（`GAME_OVER`・止めた理由） | 段階とコマンドの表を確かめる性質は同じ。`EvolvePokemon` の対象は場のポケモンの番号にした |
| test_turns.py `UnsupportedActionsTest.test_unsupported_commands` | `UsePokemonPower` だけを未対応として確かめ、`EvolvePokemon` は手札にないカードで `CARD_NOT_IN_HAND` | 未対応の操作を黙って無視しない性質は同じ |
| test_turns.py `test_failed_commands_leave_state_unchanged` | コメントだけ（「未対応」→「手札にない」） | 不正な操作で状態が変わらない確認は同じ |
| test_coin_attacks.py `test_rejections_in_main` | 手札のエネルギーでの進化は `NOT_EVOLUTION_CARD` | 不正な操作で乱数を使わない確認は同じ |
| test_trainer_games.py `test_only_resolve_decision_is_accepted` | トレーナーの決定を待つ間の進化は `WRONG_PHASE` | 決定を待つ間はほかの操作を受け付けない確認は同じ |
| test_effects.py `test_attacks_with_text_follow_the_verified_latest_description` | 説明文のあるワザにれいとうビーム（PMCG1-030#1）・パラセクトのキノコのほうし（PMCG2-010#0） | 一覧をちょうど確かめる性質は同じ。加えたワザも照合の記録と比べる |
| test_effects.py `RegistryImmutabilityTest.test_with_and_without_do_not_change_the_original` | 登録したワザの数 22 → 26 | 登録表が変わらないことを確かめる性質は同じ |
| test_cards.py `test_v0_1_pool_is_ten_basic_pokemon_and_six_basic_energy` | `pool_v0_4a` とパラセクト・ジュゴンが使えることを確かめ、v0.1 の組の数から除く | v0.1 の組（たねポケモン 10・基本エネルギー 6）の確認は同じ |
| test_rng_and_serialize.py `test_format_2_adds_only_documented_fields` | 登録表の id `kyuura-engine-0.4a` | 同上 |
| test_rng_and_serialize.py `test_unknown_format_is_rejected` | 形式の一覧に 7、知らない形式の例を 7 → 8 | 知らない形式を拒否する性質は同じ |
| test_trainers.py `test_default_registry_has_exactly_the_registered_cards` | 登録表の id | トレーナーの一覧と実装の一覧は同じまま |

tests/helpers.py に `PARASECT`・`DEWGONG` と、`build_test_state` のポケモンの指定に `"evolved_from"`・`"evolved_turn"`・`"played_turn"` を加えました（既存の盤面は変わらない。`played_turn` の既定は 0）。

### 加えたテスト

| モジュール | 件数 | 内容 |
|---|---|---|
| tests/test_evolution_v0_4a.py | 43 | カード・進化の条件（最初の番・今の番に出した・同じ番の 2 回目・名前・相手のポケモン・番号と uid・決定を待つ間・終わった対戦・未対応のカード・直接出せない）・受け継ぐもの（ダメージ・エネルギー・プラスパワー・ディフェンダー）・8 つの特殊状態・にげるの失敗の記録・進化したあとのワザ・HP・にげる・きぜつ（ワザ・こんらん・どく）・複製・形式 7・不変条件・原子性 |
| tests/test_evolution_games_v0_4a.py | 7 | 進化を含むデッキの新しい対戦から勝敗まで 40 局・固定値・サイドの数・乱数・でたらめな進化 12 局 |

合わせて 726 → 776 件。Python 3.11・3.12・3.13 で通ることを確かめました。負荷テスト・変異テストは [evolution-state-v0.4a.md](evolution-state-v0.4a.md) 11 章。

## 10. 将来の拡張（2 進化・退化）

| 事項 | v0.4a の土台 | 加えるときに見直すこと |
|---|---|---|
| 2 進化 | `evolution_stack`（下から順）、`evolved_turn`（同じ番の 2 回目の禁止）、名前の確認 | 不変条件の「1 枚まで」を「2 枚まで」に。重なりの各段（たね → 1 進化 → 2 進化）の名前の確認。1 進化を飛ばす進化（ふしぎなアメなど）は指示があるカードだけ（v0.4c 注: この表のとおり、土台を変えずに不変条件を 2 枚まで・各段の段階と名前の確認に広げ、ログ `evolve` との対応を加えた。[architecture-v0.4c.md](architecture-v0.4c.md)） |
| 退化 | `evolution_stack` の最後を戻す | p.324 の退化の手順（特殊状態・持続する効果・マーカー）。`evolved_turn` をどうするか（退化したポケモンが同じ番にまた進化できるか）を原典で照合する |
| 進化に関わるポケモンパワー・トレーナー | `_evolve_pokemon` | 手順 5（進化によって引き起こされる特殊なことがら）。進化の条件を変える効果 |
| 持続する効果 | なし | 進化（手順 3）・ベンチに戻る・場をはなれるで消す処理。ついているカードの効果とは分ける |
| 「同じポケモン」「進化前のポケモン」を参照する効果 | `pokemon_id`・`evolved_turn` | `pokemon_id` だけで裁定しない |
| マーカー・カウンター | なし | 手順 4 で取りのぞく |

## 11. 設計上のトレードオフ

| 判断 | 理由 | 代償 |
|---|---|---|
| `pokemon_id` を変えない | 受け継ぐもの・決定・ログを番号でそのまま追える | 「別のポケモン」の帰結を 1 つずつ処理する必要がある（不変条件・変異テストで確かめた） |
| 場に出た番・進化した番を明示的に持つ | 検査が直接。不変条件で確かめられる | 状態の項目が増える。形式 7 が要る |
| 形式 1〜6 には番を書き出さない | 進化していない状態の書き出しを変えない（v0.1 の参照データと比べられる）。番はログから分かる | 形式 6 だけを読むクライアントは、進化の可否をログから求める必要がある |
| ついているトレーナーの効果を進化で消さない | p.310・p.321・p.322 から導ける（SUPPORTED） | 別の資料で違う扱いが見つかれば見直す（今は見つかっていない） |
| HP がダメージ以下になる進化は止める | きぜつの扱いが原典で決められない | 対応カードでは起こらない（HP が増える）。そのようなカードを加えるときに照合する |
