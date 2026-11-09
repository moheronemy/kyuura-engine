# v0.175: R-3 の U-R3a（本人のうらのカードの、宣言の段が 2〜3 段の特殊能力の構造の入力）

[R-3 の監査](legal-actions-r3-audit.md) 6.1 節の U-R3a を採用し、実装しました。合法手 API（`legal_actions.py`）の候補の作成だけを変えています。ゲームの合法性・裁定・
エンジンの処理（おもてにする処理・宣言の確かめ・受理・拒否・トラッシュ）は変えていません。版は 0.175.0 です。R-3 の全体は解消していません（6 章）。

## 0. 採用の記録と範囲

| 項目 | 値 |
|---|---|
| 基点 | `3e3b3619ce15cd47ef1af8dbf81dee35a5226fa6`（`claude/r3-face-down-power-audit`。監査・P6（`ac64d39`）・検証用 AI の P6 の追従（`443bc89`）を含む。`origin/main` には入っていない） |
| 作業ブランチ | `claude/u-r3a-face-down-multistage-power`（専用の worktree `C:\dev\kyuura-engine-vai`。利用者の `C:\dev\kyuura-engine` は触っていない） |
| 対象 | 本人のうらのカードの、本当のカードの印刷の特殊能力のうち、`POWER_INPUT_STAGES` の宣言が 2〜3 段で、どの段の場所も公開の値・本人の手札で作れるもの（`_face_down_staged_declaration`）。宣言から作る（型名・カード名で分けない） |
| 対象外 | 完成する組のない場面（選べるものが空の段。入力を返さないまま。項目を省いた送信にしない）、宣言のない型・登録のない力・知らない場所の段、常時・反応・ワザといっしょに使う力、R-2・R-4・R-5 の残り・PT-5e・UP-5t、GUI・検証用 AI の追従 |
| 今の登録で当てはまる型 | 監査 2 章の 7 つ: `TakeEnergyToSelf`（ロケット団のヒトカゲ。たね）、`EnergyTransfer`・`MoveEnergyAmongNamed`・`ConvertBasicEnergyColor`・`AttachEnergyFromHand`・`MoveDamageCounter`・`MoveOpponentDamageCounter`（進化カード） |

## 1. おもてにする処理の順番と、おもてにする前の拒否（実装で確かめた。変えていない）

`engine.apply_command` → `_apply`（`engine.py:603`）→ `_apply_checked`（`:626`）→ `_apply_once`（`:888`）→ `_reveal_for_action`（`:1075`）。

| 順 | 確かめ | 拒否のとき |
|---|---|---|
| 1 | `require_state_conventions`（状態の規約集合） | おもてにしない・状態は変わらない |
| 2 | 未対応のコマンド・知らないコマンド・`check_command_fields`（項目の型。`commands.py:360-369` の `BAD_COMMAND`） | 同上 |
| 3 | 段階: `GAME_OVER`・サドン・デス・停止（`HALTED`） | 同上 |
| 4 | `_require_supported_decision`（扱えない保留中の決定） | 同上 |
| 5 | 状態を複製し、使うポケモンがうらなら `checks.require_turn`（番・段階）と決定待ちでないこと（`DECISION_PENDING`） | 同上（複製を捨てる） |
| 6 | `reveal_face_down`（`zones.py:82`）。たねかは `_secret_plan_keeps`（`zones.py:130`）→ `effects.card_is_basic_in_text(printed_def, TEXT_PRE_NEO) is True`（`effects.py:15549`。たねポケモンカードは真、ベイビィはネオより前の説明なので真、ほかは偽） | — |
| 7a | たねでない: ついているカードといっしょにトラッシュし、受理（`resolution.after_power`）。`source`・`target`・`energy` は読まない | — |
| 7b | たね: `source`・`target`・`energy` のついているポケモンがうらなら `designate_face_down(can_lose=False)`、そのあと `check_use_pokemon_power`（型ごとの `check_usable`）と処理 | 拒否・停止はコマンドごと（状態・乱数・ログはもどり、おもてにしたことも公開されない） |

- 「進化カードなら必ずトラッシュ」は、1〜5 を通っておもてにする処理（6）に届いたときだけです（監査の文書もそう限定した）
- 相手のうらのカードがあるときの `_apply_checked` の、ありうるカードでの確かめ（`_identity_independent`）は、相手のうらのカードを使ったときだけ。7a は指定のうらのカードをおもてにする前に返るので当たらない

## 2. 候補と入力の作成

`_face_down_power_candidates`（`legal_actions.py`）に、2〜3 段の分岐を加えました。

- 宣言の段の並び（`POWER_INPUT_STAGES`）のまま、各段の選べるものを `_power_domain` で作る: 自分の場（場の並び）・選んだ `source` についているカード（ついている順）・本人の手札（手札の並び）・相手の場（公開の位置）。読むのは観測と同じ公開の値と本人の手札、本人が知る本当のカードの印刷の特殊能力と宣言だけ
- エンジンの確かめ（`check_use_pokemon_power`・`check_usable`・`_probe`）を呼ばない。おもてにしない・状態を複製して試さない・効果を仮に実行しない・乱数を使わない。相手の手札・山札・サイド・うらのカードの本当のカードを読まない
- 組は構造だけ: 受け付けるか（タイプ・同じポケモン・回数など）で絞らない。あとの段の選べるものがない前の段の選び方は、組が完成しないので含めない（構造の欠け）。完成する組が 1 つもなければ、今までどおり入力を返さない（R-3）
- 段・番号・`options_by_choice`・`depends_on_stage`・`upstream_stages`・`after` は、おもてのカードの U7-5e と同じ組み立て（`_staged_power_candidate` に分けて共用。おもてのカードの出力は変えない）。番号は前のすべての段の選び方ごとに別。`options_by_path` と新しい項目は加えていない
- 候補の `input_disclosure` は `confirmed`、候補・選べるもの・参照の `processability` はどれも `unverified`（`face_down_reveal_not_evaluated`）。たねでないこと（トラッシュ）を予告しない
- 1 段目の段に `note`（構造の組で、受け付けるかは確かめていない）。`guarantees` は `GUARANTEE_FACE_DOWN_POWER` の文を 0〜3 段に直した。residual の R-3 の `note` も直した（分類の値（id・kind・field・situation・status・reason・subject）は同じ）

### 2.1 入力の JSON の例

構築盤面（4 章）: 自分のバトル場は闘エネルギー 2 枚のエビワラー（場のポケモンの番号 1）、ベンチは炎・水エネルギーのコラッタ（2）と、うらのロケット団のヒトカゲ（4。何もついていない）。
本人の `inputs` の応答（説明の文は略）:

```json
{"candidate": "c…", "kind": "use_power",
 "stages": [
  {"stage": 1, "input": "choose_option", "role": "source", "meaning": "pokemon", "count": {"min": 1, "max": 1}, "order": "not_applicable", "note": "…",
   "options": [{"id": "o1", "pokemon": 1, "card": 0, "zone": "active", "card_id": "PMCG1-058", "eligible": true, "processability": "unverified", "reasons": ["face_down_reveal_not_evaluated"]},
               {"id": "o2", "pokemon": 2, "card": 3, "zone": "bench", "bench_index": 0, "card_id": "PMCG1-060", "eligible": true, "processability": "unverified", "reasons": ["face_down_reveal_not_evaluated"]}]},
  {"stage": 2, "input": "choose_option", "role": "energy", "meaning": "card", "count": {"min": 1, "max": 1}, "order": "not_applicable",
   "depends_on_stage": 1, "upstream_stages": [1], "note": "…",
   "options": [{"id": "o3", "card": 1, "card_id": "PMCG1-102", "after": "o1", "eligible": true, "processability": "unverified", "reasons": ["face_down_reveal_not_evaluated"]},
               {"id": "o4", "card": 2, "card_id": "PMCG1-102", "after": "o1", "…": "…"},
               {"id": "o5", "card": 4, "card_id": "PMCG1-098", "after": "o2", "…": "…"},
               {"id": "o6", "card": 5, "card_id": "PMCG1-099", "after": "o2", "…": "…"}],
   "options_by_choice": {"o1": [{"option": "o3", "eligible": true, "processability": "unverified", "reasons": ["face_down_reveal_not_evaluated"]}, {"option": "o4", "…": "…"}],
                         "o2": [{"option": "o5", "…": "…"}, {"option": "o6", "…": "…"}]}}]}
```

（uid・場のポケモンの番号は、この盤面で実際に返った値（証跡の `inputs_example.json`）。候補の `pokemon` は `{"pokemon": 4, "card": 7, "zone": "bench", "bench_index": 1, "face_down": true}`、`power` は `{"index": 0, "name_ja": "ほのおをもらう", "card": 7, "card_id": "PMCG4-012", "face_down": true}`（本人の応答だけ）。うらのヒトカゲ自身は何もついていないので 1 段目にない。ついていれば `face_down: true` でカード id なしに並ぶ）

3 段（フシギバナ）は `source`・`energy`・`target` で、3 段目は `depends_on_stage: 2`・`upstream_stages: [1, 2]`。同じ盤面で 2・4・12 の選べるもの（`(source, energy)` の 4 組 × 自分の場の 3 匹）。

## 3. check と submit

- check（`_power_input_problem`。変えていない）が確かめるのは、段の数、各段の番号が候補にありその段のものか、前の段との依存（`after` が直前の選び方。別の経路の番号を混ぜない）、番号の型。数は各段 1 なので、重なり・並びの誤りもここで断る（`CANDIDATE_INPUT_INVALID`）
- check の成功は、特殊能力を使えること・受理・完走の保証ではない（たねでなければトラッシュ、たねなら `check_usable` がおもてにしたあと決める）
- submit（`_command`。変えていない）は、段の順の値を `UsePokemonPower` の項目（宣言の項目名）に置いて既存のコマンドを送る。おもてにする処理・宣言の確かめ・受理・拒否・トラッシュ・受理のあとの決定はエンジンのまま
- 拒否では状態・乱数・ログがもどり、診断は送った本人にだけ返り、相手・観戦者に更新を作らない。取っ手は受理で失効し、拒否では失効しない（既存の契約）

## 4. 限定の検証

構築盤面だけです（new_game からの到達・seed 探索はしていません）。盤面は `tests/test_legal_actions_u_r3a_v0_175.py` の `placed` です。
既存の `tests/test_secret_plan_v0_67.py` の `board`（`build_test_state`。プレイヤー 0 の番の MAIN・3 番目の番）に、ベンチの炎・水エネルギーのコラッタを加え、`place`（マチスの秘策の
`PlayTrainer` と `ResolveDecision`。`apply_command` の合法な列）で本当のカードをうらにしてベンチに出しました。関数の中で、うらのカードに何もついていない・ダメージ 0・
決定待ちでない・番がプレイヤー 0 であることを確かめます。

実行の前に決めた代表（証跡の `plan.json`）:

| 例 | 本当のカード | 入力（段の順） | 確かめること |
|---|---|---|---|
| 受理 | ロケット団のヒトカゲ（たね・2 段） | コラッタ → 炎エネルギー | 受理。おもてにして特殊能力がおこる |
| 拒否 | ロケット団のヒトカゲ | エビワラー → 闘エネルギー | 形は合う。おもてにしたあと `TakeEnergyToSelf.check_usable` が `WRONG_ENERGY_TYPE`（`invalid_input`。`effects.py:9249-9250`）で拒否し、状態がもどる。盤面の不整合による failed ではない |
| トラッシュ | フシギバナ（2 進化・3 段） | エビワラー → 闘エネルギー → エビワラー（受け付けるかで絞らない構造の組） | 受理。おもてにしてトラッシュし、特殊能力はおこらない（入力は読まれない） |

## 5. 結果

### 5.1 受理・拒否・トラッシュと直接のコマンドとの一致

U7（`ActorSession`）・client_api（`ClientHub`）・直接のコマンド（`HostedGame.submit`）で、結果・本人への見え方・状態・乱数・ログ・決定の通し番号が同じでした（テストと、証跡の `reached_outcomes.json`）。

| 例 | 結果 | 新しいログ | 診断 | 到達した範囲 | 相手・観戦者への更新 |
|---|---|---|---|---|---|
| 受理 | accepted | `secret_plan_revealed`（`cause: power`）→ `pokemon_power` → `move_energy` | — | 同じ番の MAIN（決定なし）。炎エネルギーがヒトカゲへ | 各 1 件 |
| 拒否 | rejected | なし（状態・乱数・ログがもどる。うらのまま） | `invalid_input`・`WRONG_ENERGY_TYPE`（送った本人だけ） | 送る前と同じ。取っ手は有効なまま | 0 件 |
| トラッシュ | accepted | `secret_plan_revealed`（`cause: power`）→ `secret_plan_discarded` | — | 同じ番の MAIN（ベンチのカードなので交代の決定なし）。エネルギーは動かない | 各 1 件 |

### 5.2 公開されたカード id（相手と観戦者の観測とログ。保存した値）

| 例 | 前 | 後 |
|---|---|---|
| 受理 | 場のポケモン 4 は `face_down: true`・カード id なし | 場のポケモン 4 は `card_id: PMCG4-012`。ログの `secret_plan_revealed` は `PMCG4-012` |
| 拒否 | 同上 | 前と同じ（うらのまま。観測・ログに `PMCG4-012` がない） |
| トラッシュ | 同上 | 場のポケモン 4 はいない。トラッシュに `PMCG1-011`。ログの `secret_plan_revealed` は `PMCG1-011` |

うらの数の変化だけでなく、公開されたカード id そのものを保存して比べました。

### 5.3 構造の検査と無副作用

- check の断り（`CANDIDATE_INPUT_INVALID`）: 数の不足・余り、別の経路の 2 段目の番号（`after` が合わない）、段の並び、1 段目の番号を 2 段目に、存在しない番号、番号の型。形の合う組（闘エネルギーの組をふくむ）は valid
- 候補・inputs・check の前後で状態・乱数・ログ・決定の通し番号が同じ。相手・観戦者・ホストへの更新 0 件
- 段の依存の形の確かめ（`stage_dependency_problems`）は 2 段・3 段とも問題なし。3 段目の選べるものは 12（`(source, energy)` の 4 組 × 3 匹）
- 選べるものは、本人の観測（場・ついているカード）だけから作った参照と同じ
- 組が完成しない盤面（自分の場のどのポケモンにもついているカードがない）は、今までどおり入力を返さない（`unconfirmed`・R-3 の actor）
- 回帰: 0・1 段のうらのカードの特殊能力（`test_legal_actions_u7_5g_face_down_power`）、おもての複数段（`test_legal_actions_u7_5e`）、R-3 の分類（`test_legal_actions_u7_5g_residual`）、P6 のにげる

### 5.4 情報境界

- **相手の秘密だけが違う双子**: 本人の観測（`real` をふくむ）が同じで、相手の手札の中身（枚数は同じ）だけが違う 2 つの盤面で、本人の候補・inputs・check の答えが同じ
- **本人の本当のカードを変えた比べ**（ヒトカゲ・コラッタ・フシギバナ）: 本人の観測の `real` が違うので、本人の全知識が同じ双子ではありません。確かめたのは、相手・観戦者・ホストの候補・観測・ログ・client_api の見え方が、本人の本当のカードによらないこと（同じだった。カード id・能力の名前が出ない）
- 拒否のあと、本当のカードは相手・観戦者に公開されない（5.2 節）。受理のあとは既存の処理どおりに公開される

### 5.5 実行したテスト

1 モジュールずつ別のプロセスで、並列なしに流しました（証跡の `test_runs.txt`）。

| モジュール | 件数 | 結果 |
|---|---|---|
| `tests.test_legal_actions_u_r3a_v0_175`（新） | 10 | 1 回目で失敗 0 |
| `test_legal_actions_u7_5g_face_down_power`・`u7_5g_residual`・`u7_5e`・`test_secret_plan_v0_67`・`test_legal_actions_p6_face_down_retreat_v0_174`・`u7_1`・`test_client_api`・`test_distribution`・`u7_5_design`・`api_design` | 10・9・24・24・7・42・9・12・27・14 | どれも失敗 0 |
| `test_preset_decks_v0_20` | 15 | 1 回目はエラー 1（`test_example_script_reaches_the_first_turn`: 子プロセスの出力を cp932 で読めなかった。シェルに `PYTHONIOENCODING=utf-8:surrogateescape` があった環境の問題で、P6 のときと同じ）。その変数を外して、このモジュールだけ再実行して失敗 0 |

- 既存のテストの意図した差: `test_multi_stage_power_withholds_inputs` の、入力を返さない代表の盤面を、組が完成しない盤面（エネルギーのないエビワラー）に替えた
- lint（ruff）はこの環境に入っていないので流していません
- 全体のテスト・GUI・E2E・大きな対戦・lockstep・状態の監査・seed 探索・AI の実対戦は流していません

## 6. 残る R-3 と別の残件

- 残る R-3: 完成する組のない場面（1 段で選べるものが 0・2〜3 段でどの組も完成しない）、宣言のない型・登録のない力・知らない場所の段（今の登録では生成されない保守の経路。監査の E）
- R-2・R-4・R-5 の残り・PT-5e・UP-5t は別の課題
- 7 つの型のうち、うらから使って特殊能力がおこるのはロケット団のヒトカゲだけ。進化カードの 6 つは、おもてにする処理に届けばトラッシュ（`reveal_face_down` と同じ結果）

## 7. GUI・検証用 AI への影響（読んだだけ。どちらも変えていない）

形が既存と同じことは、実際の動作の互換を保証しません。下はコードを読んだだけの見込みです（実行していない）。

### 7.1 GUI

比べたのは `moheronemy/kyuura-engine-gui` の `feature/engine-p6-retreat-facedown` の `1b7d8c7b9ec392de056a4fdb98be8db371eb08e9` です。2026-11-09 の最新の公開ブランチで、`78c02a6` より 6 コミット新しいものです。
GitHub の API で読み取りだけをしました。固定しているエンジンは `f7bf450`（0.174.0）です。

| 確かめたこと | `1b7d8c7` の扱い（コードを読んだ） | 0.175.0 の応答で起こる見込み |
|---|---|---|
| うらの特殊能力の 2〜3 段 | `powerStages`（`web/src/api/validate.ts`）は、role の並びが `power_stage_shapes`（3 段・2 段をふくむ）にあれば、うらかどうかで段の数を分けない。契約の表の説明文は「うらは 0 段か 1 段だけ」と書くが、検査はそれを強制しない | 形の検査は通る見込み。説明文の直しが要る |
| 候補の pokemon・power | `face_down` は両方にそろって必要。うらの pokemon にカード id があれば止める | 0.175.0 も同じ形（変わらない） |
| 段の項目・依存 | `stage_keys` に `note`・`depends_on_stage`・`upstream_stages`・`options_by_choice` がある。`chainedStages` は `after` と `options_by_choice` の組を確かめる | 通る見込み |
| 前の段を変えたとき | `DecisionPanel` は k 段目を変えたら、依存するあとの段の選択を捨て、前の check の答えを使わない | おもてのカードと同じ動き |
| 送る前の check | `check_before_submit_kinds` に `use_power` がある | うらの 2〜3 段も check が要る |
| residual | 分類の値（id・kind など）だけを契約の表と比べ、`note` は文字列であることだけを見る | R-3 の `note` の変更では止まらない |
| 受理・拒否のあと | `outcome.ts` は outcome と `result.status`・`next` だけで表示する。拒否は本人だけ | トラッシュも受理として表示する。おもてにしたカードの画像は観測の `card_id` による見込み（実行していない） |
| エンジンの固定 | 導入元を `direct_url.json` の `commit_id` で確かめる（`docs/engine-contract.md`） | 0.175.0 を使うには固定の更新が要る |

GUI に要る追従（今回は着手しない）:

- 固定するエンジンを 0.175.0 の固定コミットにする
- 契約の表の `$power` の説明（うらは 0・1 段だけ）を直す
- うらの 2〜3 段を表示する（本人の画面だけ。受け付けるかは確かめていないことも示す）
- 受理（使った）・トラッシュ・拒否の表示と画像の切り替えを、実際に動かして確かめる

### 7.2 検証用 AI（同じ基点の `tools/verification_ai`。変えていない）

| 確かめたこと | 読んだ結果 |
|---|---|
| 形として入力を作れるか | `STAGE_KEYS` に段の項目がすべてある。`build_choices`・`enumerate_inputs` は `depends_on_stage`・`options_by_choice` で引く（`actions.py:181-185`） |
| `unverified` が方策の対象か | deep は `supported`・`may_stop_later` だけで、`unverified` はほかに候補がないときだけ（`FALLBACK_PROCESSABILITY`）。boundary は対象 |
| check のあとの正常な拒否 | 候補の理由に `face_down_reveal_not_evaluated` があるので、受け付ける前の確かめの保証の外（`judge.py:163-164`）。P6 の規則（`is_p6`）は `retreat` だけ。`WRONG_ENERGY_TYPE`（`invalid_input`）は `normal_rejection` になる見込みで、suspect にしない |
| 受理の「使った」と「トラッシュ」 | 区別しない。`judge_p6_accepted` は P6 の固定確認だけで使い、通常の判定は受理の中身を分けない |

追記: このあと検証用 AI を追従させた（[verification-ai-u-r3a.md](verification-ai-u-r3a.md)。判定の規則 5）。下は追従の前の読み取り。

AI に要る追従（今回は着手しない）:

- うらの特殊能力の受理の中身を分ける判定（`secret_plan_revealed` のあとが `pokemon_power` か `secret_plan_discarded` か）
- 構築盤面の固定確認で、実際の生成と判定を確かめる
- 判定の版を記録する

## 8. 版・識別・配布

- 版: 0.175.0（`kyuura_engine/__init__.py`・`pyproject.toml`・`tests/test_preset_decks_v0_20.py`）。識別方式は変えていない
- 実装の識別: `behavior_digest` は `cf279dc9…e129`（0.174.0）から `d1bcca17071feb62d9006d3aa133a638756e05777fefe6bfdbfdc11a6e659149` に変わった。`instrumentation_digest` は `e7d36df3…3034` のまま
- 互換: 0.174.0 の記録・スナップショットは 0.175.0 では再実行・復元できない（既存の設計）。過去の証跡は元の版のまま残し、識別を書き換えて使っていない。スモークのスナップショットは 0.175.0 で作った
- 配布用の固定コミット: `81e9e99f76c2a2071fbbc50f852d6c28a026d080`
  - 配布物の中のファイルは 62（`f7bf450` と同じ一覧）。`pyproject.toml` の差は版だけで、新しい依存はない
  - `git archive` から作った wheel（sha256 `8a378e32440c1405de4d477639c431342630407d3385c66fa1898572fc389414`）に `scripts/check_distribution.py` をかけた: required=62・problems=0
  - リポジトリの外の新しい venv に、Git の URL（`git+https://github.com/moheronemy/kyuura-engine.git@81e9e99…`）から通常のインストールをした。`direct_url.json` の `vcs_info.commit_id` が一致し、`dir_info.editable` はない。`site-packages` から読み込み、実装の識別がソースと一致した
  - スモーク（`-I`・リポジトリの外の作業ディレクトリ）: スナップショットを復元し、ClientHub で入力を取った。うらのヒトカゲは 2 段（選べるもの 2・4）、うらのフシギバナは 3 段（2・4・12）。check では、形の合う組が valid、別の経路・並び・不足・存在しない番号が `CANDIDATE_INPUT_INVALID`。相手・観戦者の応答に本当のカード id がなく、更新は 0 件。終了コードは 0

## 9. 証跡

保存先は `C:/dev/kyuura-engine-verification-vai/` です。

- `verifier/runs/u-r3a-v0.175/`:
  - 実行前の計画と採用の記録（`plan.json`）、コマンドと終了コード（`invocation.json`）
  - テストの出力、`reached_outcomes.json`（公開されたカード id）、`inputs_example.json`
  - 配布と導入の結果、スナップショット
- `public/runs/u-r3a-v0.175/summary.json`: 非機密の集計だけ
- マニフェストは 400 ファイルです。既存の 363 ファイルが変わっていないことを確かめてから更新しました
