# U7-3: 番の基本の操作（v0.165）

合法手 API（`kyuura_engine.legal_actions`）とクライアント向けのアダプタ（`kyuura_engine.client_api`。契約 `kyuura-client-api`・形式の版 1）に、自分の番の基本の操作 4 種類の候補・入力・検査・送信を加えました。仕様案は [legal-actions-api-design.md](legal-actions-api-design.md)、計画は [legal-actions-api-implementation-plan.md](legal-actions-api-implementation-plan.md) の `U7-3` です。ワザ・トレーナー・特殊能力・スタジアムなどは対応していない種類のまま（`not_covered_kinds`）で、番の候補の完全性は `partial` です。

採用の記録（`scripts/build_legal_actions_api_design.py` の `ADOPTION_U7_3` から作る）:

<!-- generated:turn-adoption begin -->
- `ADOPT-U7-3`（2026-11-07・利用者）: U7-3（番の基本の操作。手札からベンチに出す・手札からエネルギーをつける・手札から進化させる・にげる）の実装だけ。既存のコマンドの意味・受け付ける条件・状態の移り変わり・乱数・ログ・観測・続行規約・停止の扱いは変えない。ワザ（U7-4）・トレーナー・特殊能力・スタジアム（U7-5）・識別の方式の移行・GUI の変更の承認ではない。実装: v0.165（docs/legal-actions-u7-3.md）
  - 方針:
    - 4 種類の範囲はコマンドと処理で決める（PlayBasicToBench・AttachEnergy（energy2 なし）・EvolvePokemon・Retreat）。カードの名前から似た効果を含めない
    - 候補の作成と入力の検査は、エンジンのコマンドの処理の前半と同じ関数（engine.check_*。状態を変えない）を使い、apply_command を試さない。秘密の状態・乱数を読む先読みを使わない
    - ゲーム上できない選べるもの・組は出さず、未裁定・未対応は消さずに実行できない区分で示す。受理のあとの反応を評価していないものを supported にしない
    - にげるの費用は組を並べず、出すエネルギーの個数の条件で示す（カードの枚数と個数を分ける。費用不足と判定の未確定を分ける）
    - U7-1・U7-2 の取っ手・結果・coverage・client_api の契約を使う（番の候補は partial）
  - 判断事項: なし（新しく採用した判断事項はない）
  - 実装単位: U7-3
<!-- generated:turn-adoption end -->

## 1. 基本の契約

- 候補は本人の知識（自分の手札・自分のうらのカードの本当のカード）と公開の情報（場・数）から作る。相手の手札・山札・サイド・相手のうらのカードの本当のカードを読まない（相手のうらのカードは `card_def` がうらの定義を返す）
- 候補・入力・検査は状態・乱数・ログを変えない。候補を作るために `apply_command` を試さない。宣言の前の先読み（`resolution.preflight`。秘密の山札・乱数を読む）を使わない
- 選べるもの・組の確かめは、エンジンのコマンドの処理と**同じ関数**（v0.165 で `engine.py` の処理の前半を関数にした。同じ順番・同じコード・同じ文。状態を変えない）:
  `check_play_basic`・`check_attach_energy`・`check_evolve`・`check_retreat_declaration`・`check_retreat`
- `IllegalActionError`（ゲーム上できない）になる選べるもの・組は候補に出さない。`UnsupportedError`（未裁定・未対応）は消さずに示し、実行できない区分にする（処理可能性は診断のコード表の分類。`stops_before_acceptance`）
- 実行は包んだ対戦の `submit`（U2 のアダプタ）だけで、最終の判定は `apply_command`。候補の表示は受理のあとの全分岐の完走の保証ではない
- 取っ手・失効・拒否の扱いは U7-1・U7-2 と同じ（受理ですべて失効、拒否では失効しない、古い・別の主体・別の対戦の取っ手を拒否）

## 2. 対応表（範囲はコマンドと処理で決める）

| 種類 | コマンド | 段（入力の順） | 受け付ける前の確かめ（エンジンの関数） | 主な拒否・停止 | 情報源 |
|---|---|---|---|---|---|
| `play_basic` | `PlayBasicToBench(player, card)` | 1. 手札のカード | `check_play_basic`: 番・手札・たね／ベイビィ・ベンチの空き（`stadiums.bench_limit`） | NOT_BASIC_POKEMON・BENCH_FULL（候補に出さない） | 本人の手札・自分のベンチの数・場のスタジアム |
| `attach_energy` | `AttachEnergy(player, energy, target)`（`energy2` なし） | 1. 手札のエネルギーカード → 2. 自分の場のポケモン | `check_attach_energy`: 番・つけた数・つける先・ミラクルエネルギーの先・クリスタルビーム・特殊能力でつけたあと（R13）・カツラの 2 回目（BL1）・特殊エネルギーのつけたときの効果（RB1・RB4） | ENERGY_ALREADY_ATTACHED など（出さない）・停止（示す） | 本人の手札・場・その番の記録 |
| `evolve` | `EvolvePokemon(player, card, target)` | 1. 手札の進化カード → 2. 自分の場のポケモン | `check_evolve`: 番・手札・進化カードか・ベイビィからの進化・対応・`evolution.evolution_block`（進化を止める特殊能力・説明の禁止・最初の番・名前・その番に出した・進化した・退化した（DV2）・段階）・ヒートプレート（HP2）・進化したあとの HP・かならずはたらく特殊能力 | 名前・段階・その番の制限（出さない）・DV2 など（示す） | 本人の手札・場（場に出た番・進化した番・退化した番） |
| `retreat` | `Retreat(player, discard, new_active)` | 1. 入れ替える控え → 2. トラッシュするエネルギー（0 枚以上） | 宣言: `check_retreat_declaration`（控え・ねむり・マヒ・化石と人形（PF2）・はなれられない・にげられない効果・とおせんぼ・こんらんで失敗した番）。組: 入力の検査で `check_retreat`（控えの位置・重なり・ついているか・出すエネルギーの個数・おいしげる・余る個数（RT1）・下限の読み方（CP2）・最大HP・おとしあな・CHASE とおいうち・つるでひっぱる・ふうせんのみ（BB1）） | ねむり・マヒなど（出さない）・WRONG_RETREAT_COST（入力の拒否）・RT1 など（実行できない） | 本人の場・相手の場（公開）・にげるエネルギーの数（`effects.retreat_cost`） |

対象外（別のコマンド・別の機能）:

- 化石・人形をポケモンとして場に出す（手札ではトレーナー。`PlayTrainer`。U7-5）
- 特殊能力でエネルギーをつける（あまごいなど。`UsePokemonPower`。U7-5）・カツラの効果の 2 枚目（`AttachEnergy.energy2`）
- トレーナーで進化させる（ポケモン育て屋さん。`PlayTrainer`）・ワザ・特殊能力で山札から進化させる
- にげる以外の入れ替え（ポケモンいれかえ・ワザの効果）
- うらのカードをおもてにする（`RevealFaceDown`。U7-5）

## 3. 候補と入力の形

候補は種類ごとに 1 つ（`c1` は番を終える。続けて `MAIN_KINDS` の順）。ゲーム上できない種類は候補を作らない（`scope_kinds` には入り、`offered_kinds` には入らない）。選ぶものは不透明な番号（`o1`, `o2`, …。段をまたいで重ならない）で、`choices` は段の順に並べる（並べかえない）。カードの名前から uid を推測しない（選べるものの `card` はその候補の中の値）。

- 1 段の操作（`play_basic`）: `choices = [手札のカードの番号]`。段に `bench`（`count`・`limit`）
- 2 段の操作（`attach_energy`・`evolve`）: `choices = [1 段目の番号, 2 段目の番号]`。2 段目の `options` は組のどれかにある場のポケモン、`options_by_choice` が 1 段目の番号ごとの組（`option`・`eligible`・`processability`・`reasons`）。組の条件（ミラクルエネルギーの先・進化の名前など）は 2 段目の選べるものだけでは表せないので、この最小の拡張を加えた（段の `depends_on_stage: 1`）
- にげる（`retreat`）: `choices = [入れ替える控えの番号, トラッシュするエネルギーの番号, ...]`。全部の組を並べず、2 段目に `total_units`（出すエネルギーの個数の範囲）と、選べるものごとの `units`（1 枚が出す個数。無色2個エネルギーは 2）・`special` を示す。**カードの枚数と出すエネルギーの個数は別**（`count` は枚数、`total_units` は個数）。トラッシュの並びは選んだ順（`order: significant`）。こんらんなら `confused: true`（受理のあとにコイン。候補の作成では投げない）。費用不足・余計なカードは `CANDIDATE_INPUT_INVALID`、余る個数（RT1）・読み方で変わる数（CP2）などの決まらない場合は `CANDIDATE_NOT_EXECUTABLE`（費用不足と判定の未確定を分ける）

選べるもの（場のポケモン）: `pokemon`（場のポケモンの番号）・`card`（いちばん上のカードの uid）・`zone`（`active`・`bench`）・`bench_index`・`card_id`。自分のうらのカードは `face_down: true`（`card_id` を出さない）。手札のカード: `card`・`card_id`・`special`（エネルギーカード）。

## 4. 処理可能性・保証・情報境界

| 区分 | 意味（U7-3） |
|---|---|
| `supported` | 受け付ける前の確かめが通り、受理のあとの反応・決定・停止のもとが場にないことを公開の情報で確かめた（特殊能力・ついているトレーナー・スタジアム・マーカー・持続する効果・特殊エネルギー・うらのカード・番の効果がない）。全分岐の完走の保証ではない（こんらんのコインなど乱数で決まる続きを含む） |
| `may_stop_later` | 受け付ける前の確かめは通る。受理のあとの反応・決定・停止を評価していない（`reactions_not_evaluated`） |
| `unverified` | 自分のうらのカードがする操作（進化・にげる）。エンジンがおもてにしてから確かめる（`face_down_reveal_not_evaluated`） |
| `unresolved_ruling`・`not_implemented`・`technical_limit` | エンジンが受け付ける前に止める（`stops_before_acceptance`）。ゲーム上の禁止ではない。送れない（`CANDIDATE_NOT_EXECUTABLE`） |

- 処理可能性（`processability`）と入力を示して安全か（`input_disclosure`）は別の軸。U7-3 の入力はどれも本人の手札・場・公開の数だけなので `confirmed`
- 候補の `guarantees` に、確かめた前提・受理の保証の範囲・受理のあとを書く（`GUARANTEE_TURN_ACTION`）
- 双子（本人の知識と公開の情報が同じで、相手の手札・おたがいの山札とサイドの配分だけが違う）で、候補の数・並び・制約・理由・不正な入力への答えが同じ（`tests/test_legal_actions_u7_3.py` の `TwinTest`）
- 決定の生成箇所・情報源は加えていない（U7-3 は決定を作らない。受理のあとの決定は既存の箇所。決定の監査の一覧は変わらない）

## 5. client_api（GUI への契約）

- 契約の識別・形式の版は変えない（`kyuura-client-api`・1、`kyuura_legal_actions_format` 1）。要求の形も同じ（`candidates`・`inputs`・`check`・`submit` の汎用の転送）。応答への追加（新しい `kind` の値・段の `depends_on_stage`・`options_by_choice`・`total_units`・`units`・`bench`・`confused`・選べるものの `pokemon`・`zone` など）は加える方向だけで、既存の項目の意味は変えていない
- 拒否の応答と公開の更新の分離・主体の固定・ホストの操作の分離は v0.164 のまま（拒否は送り手だけ、受理のあとにだけ閲覧者ごとの更新）
- 既存の GUI（kyuura-engine-gui）の実行時の検証は、知らない項目を読み飛ばし、選べるものごとに `processability` を求める（U7-3 の選べるもの・組はすべて持つ）。ただし、新しい種類の入力画面（2 段目を `options_by_choice` で絞る・`total_units` で個数を数える）は GUI 側にない。GUI を動かして確かめていないので、既存の GUI がこれらの操作を扱えるとは保証しない

例（エネルギーをつける）:

```json
{"contract": "kyuura-client-api", "format": 1, "type": "inputs", "game": "…", "revision": "…", "candidate": "c3"}
```

```json
{"candidate": "c3", "kind": "attach_energy", "stages": [
  {"stage": 1, "input": "choose_option", "role": "energy", "meaning": "card", "count": {"min": 1, "max": 1}, "order": "not_applicable",
   "options": [{"id": "o1", "card": 4, "card_id": "PMCG1-098", "special": false, "eligible": true, "processability": "supported"}]},
  {"stage": 2, "input": "choose_option", "role": "target", "meaning": "pokemon", "count": {"min": 1, "max": 1}, "order": "not_applicable", "depends_on_stage": 1,
   "options": [{"id": "o2", "pokemon": 1, "card": 0, "zone": "active", "card_id": "PMCG1-014", "eligible": true, "processability": "supported"}],
   "options_by_choice": {"o1": [{"option": "o2", "eligible": true, "processability": "supported"}]}}]}
```

```json
{"contract": "kyuura-client-api", "format": 1, "type": "submit", "game": "…", "revision": "…", "candidate": "c3", "choices": ["o1", "o2"]}
```

例（にげる。無色2個エネルギーと水エネルギーがついたラプラス。にげるエネルギー 2）:

```json
{"stage": 2, "input": "choose_option", "role": "discard", "meaning": "card", "count": {"min": 0, "max": 2}, "total_units": {"min": 2, "max": 2},
 "order": "significant", "order_preserved": true, "distinct": true,
 "options": [{"id": "o2", "card": 7, "card_id": "PMCG1-096", "special": true, "units": 2, "processability": "may_stop_later"},
             {"id": "o3", "card": 8, "card_id": "PMCG1-099", "special": false, "units": 1, "processability": "may_stop_later"}]}
```

`["o1", "o2"]`（無色2個エネルギー 1 枚で 2 個）は受け付ける。`["o1", "o3"]`（1 個）・`["o1", "o2", "o3"]`（余計なカード）は `CANDIDATE_INPUT_INVALID`。

## 6. GUI 側の追従（GUI リポジトリは変更していない）

- 型: `Candidate.kind` に `play_basic`・`attach_energy`・`evolve`・`retreat`。段に `role`・`depends_on_stage`・`options_by_choice`・`total_units`・`bench`・`confused`、選べるものに `units`・`special`・`pokemon`・`zone`・`bench_index`・`face_down`・`reasons`
- 検証: `options_by_choice` の各組の `option` が 2 段目の `options` の番号であること・`processability` が知っている値であること。`total_units` の `min ≤ max`
- 入力画面: 2 段目は 1 段目で選んだ番号の `options_by_choice` だけを選べるようにする。にげるは控えを 1 つ選び、エネルギーを `units` の合計で数える（枚数で数えない）。並びは選んだ順に送る。`check` で確かめてから送る
- 表示: `processability` ごとに表示し、`unresolved_ruling` などを「ゲーム上できない」と表示しない。`supported` を受理のあとの完走の保証と表示しない
- 依存: この版を含むコミットに固定して入れ直す（通常のインストール。[installation.md](installation.md)）

## 7. 制限・引き継ぎ

- ワザ（U7-4）・トレーナー・特殊能力・スタジアム・その他（U7-5）は対応していない種類。番の候補は `partial`
- `supported` の条件は十分条件（場に特殊能力を持つポケモンが 1 匹でもいれば `may_stop_later`）。受理のあとの反応の評価は U7-4・U7-5 で必要になれば別に設計する
- 自分のうらのカードの進化・にげるは `unverified`（本当のカードでの確かめを候補の作成で行っていない）
- U7-4 への引き継ぎ: ワザの宣言の前の確かめ（`checks.attack_request`）は、この版と同じく「処理の前半の関数」を候補の作成に使える。宣言の前の先読み（秘密の山札・乱数）は候補の作成に使わない（v0.147〜v0.151 の持ち主の知識の関数を使う）
