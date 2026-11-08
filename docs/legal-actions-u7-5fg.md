# U7-5f・U7-5g: おもての山札の確かめの表示・coverage の残り・カツラの 2 枚目・本人のうらのカードの特殊能力（v0.172）

U7-5 の残る 2 つの単位（U7-5f・U7-5g）の実装の記録です。仕様と監査は [legal-actions-u7-5fg-spec](legal-actions-u7-5fg-spec.md)、計画は [legal-actions-u7-5-design](legal-actions-u7-5-design.md)・[legal-actions-u7-5-implementation-plan](legal-actions-u7-5-implementation-plan.md) です。

- 基点: main の `88ad4d9`（`be1e29d` の U7-5f・g の仕様を取り込んだ PR #38 のマージ。U7-5e の `6413638` を含む）。作業ブランチ `claude/u7-5fg-impl`
- 変えたのは合法手 API（`kyuura_engine/legal_actions.py`）と、その回帰テスト・文書・生成した仕様だけです。エンジンの動作（`engine.py`・`resolution/`・`effects.py`）、識別の方式、3 つの規約集合（ID・版・内容・照合値）、kyuura、カードデータ、固定デッキ、過去の参照データは変えていません
- 実装の単位（どれも別のコミット）: U7-5f → U7-5g-3（coverage の residual）→ U7-5g-1（カツラの 2 枚目）→ U7-5g-2（本人のうらのカードの特殊能力）
- R-2（自分のうらのバトル場のポケモンの、ワザといっしょに選ぶもの）は、今回も未対応のまま残します

## 0. 採用した判断と範囲（2026-11-08 の依頼）

| 判断 | 採用の内容 | 実装 |
|---|---|---|
| D-U75-FACE-UP-ACTORS | 初版の U7 では、CheckFaceUpDeckCard を番のプレイヤー（MAIN）だけに表示する。コマンドの主体の制約ではなく、API の対応の範囲として記録する | 1 章・2 章の R-4 |
| D-U75-ENERGY2-SCHEMA | カツラの 2 枚目は attach_energy の任意の 3 段目。1・2 段目の組で引く `options_by_path` で示す | 3 章 |
| D-U75-FACE-DOWN-POWER | 本人が知る印刷の情報だけから安全に作れる特殊能力を候補にする。`unverified` だけを理由に公開を許さない | 4 章 |
| D-U75-R2 | R-2 は未対応のまま残す | 2 章の R-2 |
| D-U7-COMPLETENESS | residual を機械で読める形で返す。未対応の宣言の経路が残るあいだ MAIN は partial のまま。候補の取得の網羅と、全部の操作の完走を分ける | 2 章 |

この採用を、未裁定の解決、停止の解除、R-2 の実装、識別の方式の移行には広げていません。記録は生成した仕様の `adoption_record.adopted`（`scripts/build_legal_actions_u7_5_design.py`）にあります。

## 1. U7-5f: CheckFaceUpDeckCard の表示だけの候補

エンジン（`engine._check_face_up_deck_card`）はどの指定も受け付けないので、ゲームの処理は加えていません。候補の表示に対応したことは、ゲームの処理が実装済みという意味ではありません（coverage の `display_only_kinds`）。

- 表示する主体と段階: 番のプレイヤーの MAIN だけ（`_face_up_candidate`）。エンジンのコマンドの段階・主体の確かめ（番・段階を確かめない）は変えていません
- 表示する条件: 相手の山札のおもての枚数（観測の `face_up_count`。全員に公開）が 2 以上
- 選べるもの: `owner`（相手）と `position`（1〜`face_up_count`−1。0 がいちばん上）だけ。おもてのカードはいつも山札の上から続く並び（`faceup.prefix_problems` の不変条件）なので、位置は公開の枚数だけから決まります。カード id・uid・名前は返しません
- 出さないもの: 自分の山札（`ALREADY_KNOWN`）、いちばん上（`ALREADY_VISIBLE`）、おもてでない位置（`NOT_FACE_UP`）。どれもゲーム上できない区分です
- 処理可能性: 候補・選べるものとも `unresolved_ruling`（FU2 の診断のコード表の分類。`eligible: false`）
- 送信: 形の合う入力（`["o1"]` など）は、エンジンに渡す前に `CANDIDATE_NOT_EXECUTABLE`（未裁定で送れない）。知らない番号・数・重なりは `CANDIDATE_INPUT_INVALID`（ふつうの不正な入力）。どちらも状態・取っ手を変えず、公開の更新を作りません
- 続けられない状態（`state_not_supported`）では、示す位置があるときだけ、ほかの種類と同じ形の実行できない候補にします

```json
{"id": "c2", "kind": "check_face_up_deck", "processability": "unresolved_ruling", "reasons": ["stops_before_acceptance"], "input_disclosure": "confirmed",
 "input_stages": [{"stage": 1, "input": "choose_option"}]}
inputs → {"stages": [{"stage": 1, "input": "choose_option", "role": "face_up_position", "meaning": "deck_position", "count": {"min": 1, "max": 1}, "order": "not_applicable",
  "options": [{"id": "o1", "owner": 1, "position": 1, "eligible": false, "processability": "unresolved_ruling", "reasons": ["stops_before_acceptance"]}, ...]}]}
check / submit（["o1"]）→ CANDIDATE_NOT_EXECUTABLE ／（["o9"]）→ CANDIDATE_INPUT_INVALID
```

## 2. U7-5g-3: coverage の残り（residual）と完了の判定

### 2.1 応答の項目（形式 1 への追加）

| 項目 | 意味 |
|---|---|
| `display_only_kinds` | 表示だけの種類（今は `check_face_up_deck`）。評価した種類のうち、送ればエンジンに渡す前に断るもの |
| `residual.classes` | API 全体で決まった残りの分類。どの応答（プレイヤー 0・1・ホスト、どの段階）でも同じ値。状態・カードによらず、該当するカードがあるときだけ出す方式にしていません |
| `residual.present` | その応答の状況で当てはまる残り。`scope` が `public` なら公開の状態だけから、`actor` なら本人の候補（本人の知識）から決まります |
| `partial_residual` | `scope_kinds` の種類にある、`not_offered` の分類の id（completeness を partial にする理由） |
| `completeness_basis` | complete の意味の説明（下の 2.3 節） |
| `unverified_paths` | 処理可能性が `unverified` の候補・選べるもの・組の理由ごとの候補（送るまで受理が分からない経路）。completeness とは別の軸です |

### 2.2 残りの分類（`RESIDUAL_CLASSES`）

| id | 種類 | 状況 | 区分 | 中身 |
|---|---|---|---|---|
| R-2 | `use_attack` | 番のプレイヤーの MAIN | `not_offered` | 自分のうらのバトル場のポケモンのワザといっしょに選ぶもの（D-U75-R2。未対応のまま） |
| R-3 | `use_power` | 番のプレイヤーの MAIN | `input_withheld` | 自分のうらのカードの特殊能力のうち、入力を本人の知識だけで作れないもの（4 章） |
| R-4 | `check_face_up_deck` | 番のプレイヤーの MAIN のほか | `out_of_scope` | 相手の山札の 2 枚目より下のおもてのカードの確かめ（エンジンは番・段階を確かめず FU2 で止める。U7 は表示しない。D-U75-FACE-UP-ACTORS） |
| R-5 | （どの種類も） | どの状況も | `input_withheld` | 情報境界を確かめていない入力（決定の種類・宣言のない特殊能力の型・自分のうらのバトル場のポケモンのにげるなど） |

- R-1（カツラの 2 枚目）は 3 章で示すので、分類にありません（番号は欠番のまま）
- 区分の意味: `not_offered` は「種類の候補は出すが、この経路の入力を示さない」、`input_withheld` は「候補は出すが入力を返さない（`INPUT_BOUNDARY_UNCONFIRMED`）」、`out_of_scope` は「その状況では API が種類を評価しない」

### 2.3 completeness

- complete は、`scope_kinds` の種類の候補の取得が網羅していること（対応しない種類がなく、`scope_kinds` の種類に `not_offered` の分類がない）だけを言います。全部の操作が受理・完走すること、U7 全体で「すべての対戦が完走する」ことではありません（処理可能性と `unverified_paths` は別の軸）
- MAIN の partial を決め打ちせず、対応しない種類と `partial_residual` から決めます。今は R-2 が残るので、番のプレイヤーの MAIN はいつも partial です（`partial_residual: ["R-2"]`）
- 番のプレイヤーの MAIN のほか（番でないプレイヤー・決定の回答者・準備）で、相手の山札のおもてが 2 枚以上のとき（公開）は、R-4 を `present` に加え、`check_face_up_deck` を `not_covered_kinds` に加えて partial にします。候補がなければ `empty_reason` は `kinds_not_covered` です（未対応のコマンドを、理由なく「合法な操作なし」と断定しない）
- 決定の回答者の応答は、入力を返さない決定があっても種類の網羅は complete のまま（R-5 を `present` に示す）
- 表示だけの候補（未裁定。`unresolved_ruling`）と、評価していない・実装していない候補の作成（`not_covered_kinds`・`not_offered`）は、別の項目で示します

### 2.4 情報の境界

- `classes` は固定、`present` の `public` は公開の状態（うらのカードがあること・カツラを使ったこと・おもての枚数）だけから決まります。`actor` の項目は本人の候補から作り、本人の応答にだけ現れます
- 相手・観戦者の応答・観測・ログ・公開の更新は、本人の手札・本人のうらのカードの本当のカードを変えた双子で同じです（`tests/test_legal_actions_u7_5g_residual.py`・`test_legal_actions_u7_5g_face_down_power.py` の双子）。観戦者の入口には候補の要求がありません

### 2.5 既存の coverage の意味の変更と互換

- 番のプレイヤーの MAIN の `not_covered_kinds` は `["check_face_up_deck"]` から `[]` になりました（U7-5f で評価した種類にしたため。completeness は partial のまま）
- 番でないプレイヤー・決定の回答者の応答は、相手の山札のおもてが 2 枚以上のときだけ、`complete` から `partial`（`not_covered_kinds: ["check_face_up_deck"]`）になります
- ほかの項目の意味は変えていません。新しい項目はどれも追加です。形式の版は 1 のままです

## 3. U7-5g-1: カツラの 2 枚目（AttachEnergy.energy2）と options_by_path

### 3.1 条件（既存の登録と共通の確かめから得る）

- 3 段目を加えるのは、カツラの効果がこの番にはたらくとき（`effects.blaine_effects`。登録されたトレーナーの効果の記録。使ったトレーナーは公開のログにある）だけです
- 選べるものは、1・2 段目の組ごとに、本人の手札のほかのエネルギーカードで、`engine.check_attach_energy` に 3 枚の組（`AttachEnergy(energy, target, energy2=…)`）を渡した確かめが、ゲーム上できない（`IllegalActionError`）としなかったもの。コマンドの処理と同じ関数・同じ順番なので、次はどれもエンジンの確かめのままです
  - カツラの効果がある・つける先が「カツラのポケモン」・2 枚とも「炎」エネルギーカード（`double_attach_check`。ほかは `DOUBLE_ATTACH_NOT_ALLOWED`・`NOT_FIRE_ENERGY` で出さない）
  - 同じカードの 2 回の指定（`DUPLICATE_CHOICE`。組を作らない）
  - 回数（2 枚のあとは `ENERGY_ALREADY_ATTACHED` で attach_energy の候補ごとない。1 枚のあとの 2 回目の操作は BL1 で、1 枚・2 枚とも実行できない区分）
  - レインボーエネルギー（RB2。実行できない区分）・ミラクルエネルギーのつける先・クリスタルビーム・あまごいのあと
- 付与の順と反応はエンジンのまま（つけたカードの順に 1 枚ずつの事実。`reactions.attach_steps`）。受理のあとは評価していないので、選べるものは `may_stop_later`（`reactions_not_evaluated`）です
- 候補を作るために `apply_command` を呼びません。費用・付与の条件の裁定を新しく決めていません。カード名・カード ID で分けていません

### 3.2 options_by_path の契約

| 項目 | 決めたこと |
|---|---|
| 経路で引く段 | `path_stages`（整数の並び）と `options_by_path`（オブジェクト）を組で持つ。`options_by_choice`・`depends_on_stage`・`upstream_stages` と併用しない（どちらで引くかは段ごとに 1 つ） |
| `path_stages` | この段より前の段の番号の、増える並び（自分・あとの段を指さない。循環しない）。attach_energy の 3 段目は `[1, 2]` |
| 鍵 | `path_stages` の段の選ぶものの番号を、段の順に `/` でつないだ文字列（`"o1/o4"`）。どの番号もその段にあり、前の段どうしの組はその段の `options_by_choice` にある組 |
| 値 | 参照の並び（`option`・`eligible`・`processability`・`reasons`。U7-3 の `options_by_choice` の参照と同じ形）。1 つの鍵の中で重ならない。並びは手札の並び |
| 鍵がない組 | その組では 3 段目を選べない（1 枚だけ） |
| 選ぶものの番号 | 3 段目の番号は、1・2 段目の番号のあとに続く（手札のカードごとに 1 つ。1 段目と同じカードでも別の番号） |
| 任意の段 | `count` は `{"min": 0, "max": 1}`・`decline: true`。入力は `[energy, target]`（1 枚）か `[energy, target, energy2]`（2 枚） |
| 1 枚の入力 | 3 段目がない今の形と同じ意味（`AttachEnergy(energy, target)`）。カツラの効果がない番は、段も 2 つのまま |
| 拒否 | 知らない番号・段の並びの誤り・鍵にない組の 3 段目（1 段目か 2 段目を変えた古い 3 段目を含む）・同じカード・4 つ以上は `CANDIDATE_INPUT_INVALID`。組が実行できない区分なら `CANDIDATE_NOT_EXECUTABLE` |
| 無効にする範囲 | 1 段目か 2 段目のどちらかを変えたら、3 段目の選び方と、その組の入力の検査（check）の結果は無効。サーバの入力の検査が、鍵にない組を拒否する |

段の形の確かめ `legal_actions.stage_dependency_problems` が、知らない鍵・鍵の段の数の違い・存在しない参照・重なり・自分やあとの段を指す `path_stages`（循環）・逆の並び・`options_by_choice` や `depends_on_stage` との併用・`path_stages` のない段・2 段目にない組を見つけます（`tests/test_legal_actions_u7_5g_energy2.py` の `StageCheckTest`）。

```json
{"stage": 3, "input": "choose_option", "role": "energy2", "meaning": "card", "count": {"min": 0, "max": 1}, "decline": true, "order": "not_applicable",
 "path_stages": [1, 2],
 "options": [{"id": "o6", "card": 3, "card_id": "PMCG1-098", "special": false, "eligible": true, "processability": "may_stop_later", "reasons": ["reactions_not_evaluated"]},
             {"id": "o7", "card": 4, "card_id": "PMCG1-098", "special": false, "eligible": true, "processability": "may_stop_later", "reasons": ["reactions_not_evaluated"]}],
 "options_by_path": {"o1/o4": [{"option": "o7", "eligible": true, "processability": "may_stop_later", "reasons": ["reactions_not_evaluated"]}],
                     "o2/o4": [{"option": "o6", "eligible": true, "processability": "may_stop_later", "reasons": ["reactions_not_evaluated"]}]}}
```

（1 段目 `o1`・`o2` は炎エネルギー、`o3` は水エネルギー。2 段目 `o4` はカツラのガーディ、`o5` はベンチのガーディ。2 段目の `options_by_choice` は U7-3 のまま、1 段目のどの番号にも `o4`・`o5` が続きます）

## 4. U7-5g-2: 本人のうらのカードの特殊能力

### 4.1 候補にするもの

- 本人のうらのカード（マチスの秘策）の、本人が知る本当のカード（`state.printed_def`。観測の `real` と同じ値で、本人の応答にだけ出す）の印刷の特殊能力のうち、登録があり、使用を宣言して UsePokemonPower で使う力（`effects.power_by_command`）
- 入力を作るのは、選べるもの・数・制約・理由が本人の知識だけで決まる型だけです
  - 宣言の段が 0 段: 入力なし（`input_disclosure: no_input`）
  - 前の段によらない場所の 1 段（自分の場・相手の場・相手のベンチ・本人の手札）: 選べるものは宣言の場所の並び（場の公開の値・本人の手札）。数は宣言で 1
- どの候補・選べるものも `unverified`（`face_down_reveal_not_evaluated`）。エンジンの確かめ（`check_use_pokemon_power`）は呼びません。`unverified` は公開の許可ではなく、入力を返すかは上の条件だけで決めます
- 入力を返さないもの（`not_implemented`・`unconfirmed`。`residual.present` に R-3 を `scope: actor` で示す）: 宣言の段が 2 段以上の型（2 段目の選べるものは 1 段目の確かめのあとで決まり、確かめを呼ばずに並べると全部の組をそのまま示すことになる）、宣言のない型、登録のない力、選べるもののない段
- 候補にしないもの: 宣言しない力・UsePokemonPower で使わない力（おもてのカードと同じ）、本当のカードがポケモンでないもの

### 4.2 情報の境界

- 候補・inputs・check は、カードをおもてにしません。状態の複製の上でおもてにして効果を試すこともしません。候補の作成はエンジンの確かめを呼ばず、状態・乱数・ログを変えません
- 能力の名前・件数・カード id は、本人の応答にだけ現れます。相手・観戦者の候補・観測・ログ・公開の更新は、本当のカードだけが違う双子（特殊能力がある・ない）で同じです
- うらのままのカードにエンジンの確かめを直接呼んでも、状態・ログを変えず、おもてにしません（`tests/test_legal_actions_u7_5g_face_down_power.py`。候補の作成はこれを呼ばない）
- コイン・受理のあとの決定は、宣言の前に移していません

### 4.3 送ったとき（既存のエンジンの入口のまま）

`_reveal_for_action` の、表にする処理と確かめの順番は変えていません。

| 本当のカード | エンジンの処理 | 結果 | 公開 |
|---|---|---|---|
| 「たねポケモン」で、確かめを通る | 番・決定待ちでないことを確かめ → おもてにする → `check_use_pokemon_power` → 特殊能力の処理 | 受理（受理のあとの決定・コインは answer_decision の候補で答える） | おもてにしたカード・特殊能力の使用が全員に公開 |
| 「たねポケモン」で、確かめを通らない | 同じ順でおもてにしたあと拒否 | 拒否（状態・ログはもどる） | 公開されない（拒否は相手・観戦者に知らせない） |
| 「たねポケモン」でない | おもてにして、ついているカードといっしょにトラッシュ | 受理（特殊能力はおこらない） | おもてにしたこと・トラッシュしたことが全員に公開 |
| 未裁定・未対応に当たる | エンジンの停止の扱いのまま | 拒否か停止（診断のコード表の分類） | エンジンの既存の扱い |

候補では、おもてにした結果（残るか・トラッシュか）を予告しません（D-U75-REVEAL-OUTCOME）。

### 4.4 広げないこと

- R-2（うらのバトル場のポケモンのワザといっしょに選ぶもの）は扱いません。うらのカードの特殊能力を加えたことを、うらのワザの任意の指定まで対応したとは扱いません
- 1 段の選べるものの中に別のうらのカード（自分・相手）があっても、U7-5e と同じく公開の位置だけで示します

## 5. 既存のエンジンとの一致と、意図した API の差

| 経路 | 一致の確かめ |
|---|---|
| CheckFaceUpDeckCard | 示す位置はどれもエンジンが FU2（未裁定）で止め、示さない位置（自分の山札・いちばん上・おもてでない位置）はどれもエンジンが `IllegalActionError` にする（全部の位置で照らした） |
| カツラの 2 枚目 | 1 枚・2 枚の入力の送信が、同じコマンドを直接送った結果・状態と同じ（構築盤面と new_game からの列。3 つの規約集合） |
| うらのカードの特殊能力 | 受理・拒否・トラッシュの 3 つの結果が、同じコマンドを直接送った結果・状態と同じ |

意図した API の差（エンジンの動作は同じ）:

- 番のプレイヤーの MAIN に `check_face_up_deck` の表示だけの候補が加わる。`not_covered_kinds` が空になる
- 番でないプレイヤー・決定の回答者で、相手の山札のおもてが 2 枚以上なら partial（R-4）
- カツラの効果がはたらく番の `attach_energy` に 3 段目がある
- 本人のうらのカードの特殊能力の候補が加わる
- coverage に `display_only_kinds`・`residual`・`partial_residual`・`completeness_basis`・`unverified_paths`

## 6. テスト・検査・配布

この作業の検証は限定の検証だけです（1 モジュールずつ別のプロセス・並列なし。結果の記録は 6.2 節）。

### 6.1 新しいテスト

| ファイル | 中身 |
|---|---|
| `tests/test_legal_actions_u7_5f.py` | フラッシュの合法な列（おもて 5・4 枚）と構築盤面（0・1・2・4 枚）、相手・本人の山札、番でないプレイヤー、おもてのカードだけが違う双子、エンジンとの一致、送信の区別、状態の不変、取っ手、client_api |
| `tests/test_legal_actions_u7_5g_residual.py` | 固定の分類がどの応答でも同じ、new_game からの準備・MAIN・番でないプレイヤー・ホスト、R-2 が残るあいだの partial、R-4、決定の回答者、unverified_paths、隠れたカードだけを変えた双子 |
| `tests/test_legal_actions_u7_5g_energy2.py` | 段の形、1 枚・2 枚・省略、組ごとの 3 段目、違う付け先、BL1・2 枚のあと、レインボー・無色 2 個、不正な経路の混在、取っ手と遅れた入力、client_api、壊した options_by_path、new_game からの列（3 つの規約集合） |
| `tests/test_legal_actions_u7_5g_face_down_power.py` | 入力なし・1 段・2 段の型、候補の取得でおもてにしない、相手・観戦者・更新への非公開（双子）、受理のあとの決定・拒否・トラッシュ、エンジンの確かめを直接呼んでも変わらない、不正な入力・取っ手 |

構築盤面（`build_test_state` の値を直接置いたもの。U7-5f の 0・1・2・4 枚）、補助関数の確かめ（段の形の確かめ・unverified_paths の集め方）、`build_test_state` の盤面から `apply_command` で進めた合法な列、new_game からの合法な列を、各テストの冒頭で分けて書いています。

### 6.2 実行した検証（2026-11-08）

1 モジュール（またはテストの方法 1 つ）ずつ別のプロセスで、並列なしに流しました。開始・終了・件数・終了コードは作業用の記録（summary.jsonl）に残しています。資源不足の停止はありませんでした。

| 対象 | モジュール | 件数 | 結果 |
|---|---|---|---|
| 新しい U7-5f・g のテスト | `test_legal_actions_u7_5f`・`u7_5g_residual`・`u7_5g_energy2`・`u7_5g_face_down_power` | 8・9・11・10 | どれも終了コード 0 |
| U7・client_api の既存のテスト | `test_legal_actions_u7_1`・`u7_2`・`u7_3`・`u7_4`・`u7_5ab`・`u7_5c`・`u7_5d`・`u7_5e`・`u7_5_design`・`u7_5fg_spec`・`api_design`・`decision_audit`・`test_client_api` | 42・17・29・27・27・32・25・24・27・9・13・15・9 | どれも終了コード 0 |
| 直接関係する既存のテスト | `test_distribution`・`test_preset_decks_v0_20`（版）・`test_energy_control_power_suppression_v0_59`（カツラ）・`test_secret_plan_v0_67`（うらのカード） | 12・15・27・24 | どれも終了コード 0 |
| README・実装状況を読むテストの方法 | 14 の方法（`DocumentTest` など。1 つずつ） | 14 | どれも終了コード 0 |

- 合わせて 21 モジュール・412 件（`test_secret_plan_v0_67` は U7-5g-2 の実装のあと、legal_actions.py を変えていない木で流した）（ほかに文書を読む方法 14 件）。全体のテスト、状態の監査、全 108 バッチ、4,356 局、lockstep、広いストレステストは流していません
- 仕様・台帳・生成物の検査: `scripts/build_legal_actions_u7_5_design.py --check`（problems=0）、`scripts/build_stop_policy_classification.py --check`（終了コード 0。停止の台帳は変わらない）、`scripts/check_implementation_assumptions.py --check`（problems=0）、`scripts/check_normalization_revalidation.py --check`（problems=0）
- lint: 変えたファイルに ruff 0.17.2（指摘なし）
- エンジン: `88ad4d9` からの `kyuura_engine/` の差は `legal_actions.py` と版の文字列（`__init__.py`）だけです
- 配布: コミット `e26df79cc6dec913c1d15b5d8203df066334d65d`（版 0.172.0）の `git archive` から作った wheel・sdist に、既存の配布物の中身の検査（`scripts/check_distribution.py`）をかけた（required=62・problems=0）。クリーンな仮想環境に、Git の URL（`git+https://github.com/moheronemy/kyuura-engine@e26df79cc6dec913c1d15b5d8203df066334d65d`）から通常のインストールをし（`-e`・PYTHONPATH は使わない）、リポジトリの外を作業ディレクトリにして、`-I` で client_api のスモークテストを流した（終了コード 0・problems なし）
  - カツラの 2 枚目: 3 段の入力（`path_stages: [1, 2]`・`count` 0〜1）で 2 枚をつけて受理。同じカードの 3 段目は `CANDIDATE_INPUT_INVALID`
  - 本人のうらのカードの特殊能力（マンキーの［スパイ］）: `unverified`・入力なし。検査のあとも相手・観戦者の公開の更新は 0 件で、相手の候補の応答に能力の名前・カード id がない。送信は受理され、おもてにしたあとに受理のあとの決定がある
  - フラッシュのあとの `check_face_up_deck`: 位置 1〜4（項目は `owner`・`position` と区分だけ）、送信は `CANDIDATE_NOT_EXECUTABLE`。相手（番でないプレイヤー）の応答は R-4 で partial
  - 既存の経路（初期配置・番の基本の操作・ワザ・場の操作・錯乱ジム・トレーナー・スタジアム・特殊能力）も通った。3 つの規約集合の照合値は固定の値と同じ
  - `behavior_digest` は `07a189c9bd196c489a9a59b247ff23681d78d7cd1edc666516f966ed1e3a6c18` で、ソースの木（`e26df79`）の値と同じ
- 確かめていないこと: GUI の実行（画面での動作）、全体のテストと大きな対戦、名前で解決できない呼び出しの先（UP-5t の限界のまま）

## 7. GUI への引き継ぎ

GUI は読み取りだけで確かめました（GitHub の API。GUI のリポジトリに fetch も書き込みもしていません。GUI と renderer は変えていません）。

- 比べた GUI: `kyuura-engine-gui` の `main` の `088822c58628fbf366363bcaaa713b1370125e86`（`e3bb682` を取り込んだ PR #2 のマージ）。固定するエンジンは `74c8e1f8ca03d017d5c0a8a79e6fdaa33d25b7f8`（0.171.0）。公開のブランチは `main` だけでした
- GUI が知らない項目で止まることと、機能の互換は別です。下の「今の GUI」は、`088822c` の契約の表（`contract/kyuura-client-api-v1.json`）から読んだ予想で、GUI を実行して確かめてはいません

| 追加 | 今の GUI（088822c の契約の表から） | GUI が要る対応 |
|---|---|---|
| `check_face_up_deck` の候補 | `implemented_kinds`・`gui_operable_kinds` にない種類（表示だけで選べない扱い）。`turn_kinds_not_covered` は `["check_face_up_deck"]` のまま | 表示だけ（送信のボタンを出さない）。`not_covered_kinds` が空になることを受ける |
| attach_energy の 3 段目 | `stage_keys` に `path_stages`・`options_by_path` がない（カツラの効果の番だけ「不明な応答」で止まる。安全な側の失敗） | 3 段目の任意の選択、`options_by_path` の鍵の作り方、1・2 段目を変えたら 3 段目と check を捨てる |
| うらのカードの特殊能力 | `power_keys` に `face_down` がなく、`power_candidate_pokemon_keys` にも `face_down` がない（その候補で止まる。安全な側の失敗） | `power.face_down`・`pokemon.face_down` の表示（本人の画面だけ）。入力なし・1 段だけ |
| coverage の新しい項目 | coverage の項目の表はない | `residual`・`partial_residual`・`unverified_paths`・`display_only_kinds` の表示 |

- 導入を確かめたエンジン: `e26df79cc6dec913c1d15b5d8203df066334d65d`（版 0.172.0。Git の URL からの通常のインストールで確かめた。6.2 節）。形式の版は client_api・合法手 API とも 1 のまま
- 種類・role・追加の項目: `check_face_up_deck`（role `face_up_position`・meaning `deck_position`・選べるものの項目 `owner`・`position`）、attach_energy の 3 段目（role `energy2`・meaning `card`・段の項目 `path_stages`・`options_by_path`）、use_power の `power.face_down`
- 無効にする範囲: attach_energy は 1 段目か 2 段目を変えたら 3 段目と check を捨てる。use_power の 0・1 段のうらのカードの特殊能力は U7-5e と同じ
- residual と coverage の表示: `partial_residual` がある応答は「一部の経路を示していない」と表示し、`complete` を「全部の操作が完走する」と表示しない。`residual.present` の `scope: actor` は本人の画面だけのもの
- FU2: `check_face_up_deck` は送れない（送れば `CANDIDATE_NOT_EXECUTABLE`）。未裁定の表示
- うらのカードの特殊能力: 本人の画面だけ。相手・観戦者の画面には出ない（サーバが出さない）。送れば、エンジンがおもてにしてから決める（受理・拒否・トラッシュ）
- 残る未対応: R-2（うらのバトル場のポケモンのワザといっしょに選ぶもの）、R-3 のうち入力を返さない型、R-4（番のプレイヤーの MAIN のほかの CheckFaceUpDeckCard）、R-5（入力を返さない決定など）

## 8. 残る未対応と、U7 の総合の検証

- 残る未対応は 2.2 節の分類のとおりです。PT-5e（山札から引いて試すトレーナー 5 つ）は直していません（`unverified_paths` の `use_condition_not_evaluated` で示す）
- U7-5 のすべての単位を実装しました。U7 の総合の検証（全体のテスト・状態の監査・lockstep・大きな対戦）と GUI の追従は、別の作業です
