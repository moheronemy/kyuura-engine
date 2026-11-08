# U7-5f・U7-5g の残件の監査と実装の仕様（v0.171 のあと。調査と仕様だけ）

U7-5 の計画（[legal-actions-u7-5-design](legal-actions-u7-5-design.md)・[legal-actions-u7-5-implementation-plan](legal-actions-u7-5-implementation-plan.md)）の残る 2 つの単位（U7-5f・U7-5g）の実装の仕様と完了の基準です。

- 今回は調査と仕様だけです。残る経路の実装、coverage の complete 化、既存の裁定の変更はしていません
- v0.172 で、判断待ちの 5 つを採用し、U7-5f・U7-5g を実装しました（[legal-actions-u7-5fg](legal-actions-u7-5fg.md)）。この文書の「判断待ち」「推奨」は、採用の前の記録のままです
- エンジンの動作、候補・入力の処理、識別の方式、3 つの規約集合、カードデータ、固定デッキ、参照データは変えていません
- 基点: `6413638`（U7-5e の最終コミット。main は `0c00b56` のまま）。作業ブランチ `claude/u7-5fg-spec`
- 判断を表す 3 つの区分: **採用済み**（利用者が採用した原則。ADOPT-U7-5AB と各単位の依頼）／**推奨**（今回の推奨案）／**判断待ち**（利用者の採用が要る）
- 判断待ちの一覧と推奨は、生成した仕様の「採用が要る判断」（`adoption_needed`）に置き、この文書には根拠と例だけを書きます（表の二重管理をしない）

## 0. 最初の訂正と確認

### 0.1 GUI の比べる相手

2026-11-08 に、GitHub の API（`gh api`）で読み取りだけをして確かめました。GUI のリポジトリには fetch も書き込みもしていません。GUI の作業ツリーには利用者の未コミットの変更があり、触れていません。

| | GUI のコミット | 固定するエンジン |
|---|---|---|
| 最新の公開の作業ブランチ `feature/engine-u7-5-trainers-stadium` | `9c36a8fe033f32b589cd57721725fdcc13c318f3` | `0885d664913bc8e57279ed9e44ac51cc97d5a6bf`（0.170.0） |
| `main` | `7660ab4d4c4064334952b2d3c9a01ede33c4973b` | `d0c5cfa9483aacae0cce2fd8d28166b1d8465500`（v0.164） |

- U7-5e の文書（7 章）と仕様の `gui_ref` は、古い `3649946`（エンジン 0.166.0）を今の GUI として書いていました。`gui_ref` を `9c36a8f` に直しました（CORR-3）
- `9c36a8f` の契約の表（`contract/kyuura-client-api-v1.json`）の状態
  - `implemented_kinds`・`gui_operable_kinds` は U7-5a〜U7-5d の種類まで
  - `turn_kinds_not_covered` は `use_power`・`check_face_up_deck`
  - 段の role の表は `play_trainer`・`use_stadium` まで
  - `stage_keys` に `upstream_stages` がなく、選ぶものの項目の表に `after` がない

### 0.2 3 段の入力の互換性（U7-5e の説明の訂正）

U7-5e の文書 3.2 節の「新しい項目を無視するクライアントは、直前の段の番号で引けば正しい組だけを選べます」は、小さな既知の入力（エナジートランスの盤面。正しい組は 6 つ）で確かめると、次の条件つきでだけ成り立ちます（`tests/test_legal_actions_u7_5fg_spec.py` の `ThreeStageCompatibilityTest`）。

| 旧クライアントの作り | 結果 | 意味 |
|---|---|---|
| 各段の `depends_on_stage` が指す段の選ぶもので `options_by_choice` を引く | たどれる組は 6 つで、どれも検査を通る（正しい組の集合と同じ） | 機能の互換が成り立つ |
| U7-3 の 2 段を前提に、いつも 1 段目の選ぶもので引く | 組が 1 つもできない | 閉じた側の失敗（誤った組を作らない） |
| `options_by_choice` を使わず、段の `options` から選ぶ | 36 の組のうち、検査を通るのは同じ 6 つだけ | 安全はサーバの入力の検査による（クライアントの互換ではない） |

- 根拠: 2 段目以降の選ぶものの番号は、前のすべての段の選び方ごとに別なので、直前の段の番号が上流の選び方を決めます（`depends_on_stage`・`options_by_choice` の意味は U7-3 のまま）
- 知らない項目で止める GUI（`9c36a8f` の `stage_keys`）は、`upstream_stages`・`after` のある段を「不明な応答」として止めます。これは安全な側の失敗で、機能の互換ではありません
- 互換のために今の処理は変えていません

## 1. U7-5f: CheckFaceUpDeckCard

### 1.1 今のコード（`engine._check_face_up_deck_card`）

- 項目は `player`・`owner`（山札の持ち主）・`position`（山札の上からの位置。0 がいちばん上）の 3 つ
- 番・段階を確かめません。どの場合も受け付けず、状態を変えません
  - 持ち主・プレイヤーが 0・1 でない: `BAD_PLAYER`
  - 位置のカードがおもてでない: `NOT_FACE_UP`
  - いちばん上: `ALREADY_VISIBLE`（観測の `face_up_top` に出ている）
  - 自分の山札: `ALREADY_KNOWN`（観測の `known_face_up` に出ている）
  - それ以外（相手の山札の 2 枚目より下のおもてのカード）: FU2（`UNRESOLVED_…`。未裁定）
- おもてのカードは、いつも山札の上から続く並びです（`faceup.prefix_problems` の不変条件）。全員に公開の `face_up_count` から、おもての位置（0〜`face_up_count`−1）が決まります

### 1.2 仕様

- **採用済み**（D-U75-FACE-UP）: FU2 による未対応として表示し、送れないようにする
- **推奨**
  - 表示する主体と段階: 番のプレイヤーの `MAIN` だけ（D-U75-FACE-UP の推奨のまま）。どの場合も受け付けないコマンドなので、ほかの段階・主体に出さなくても、実行できる経路は減らない
  - 候補を表示する条件: 相手の山札の `face_up_count` が 2 以上（2 枚目より下におもてのカードがある）
  - 入力: 1 段の `choose_option`（`role: "face_up_position"`・`meaning: "deck_position"`）。選べるものは `owner`（相手）と `position`（1〜`face_up_count`−1）
    - カード id・カードの uid は出しません（位置は公開の枚数だけから決まる。おもてのカードの中身は、2 枚目より下を確かめる処理がない）
  - 処理可能性: 候補・選べるものとも `unresolved_ruling`（`eligible: false`）。送る前に `CANDIDATE_NOT_EXECUTABLE`（エンジンに渡さない）
  - 自分の山札（`ALREADY_KNOWN`）・いちばん上（`ALREADY_VISIBLE`）・おもてでない位置（`NOT_FACE_UP`）は、ゲーム上できない区分として候補・選べるものに出しません
  - coverage: `check_face_up_deck` を評価した種類に入れます。「評価し表示に対応した」ことで、ゲームの処理が実装済みという意味ではありません（5 章の `residual` で、送れない種類として機械で読める形に示す）
- **判断待ち**: 番でない主体（相手の番に、自分から見て相手の山札）にも表示するか（D-U75-FACE-UP-ACTORS）

```json
{"id": "c5", "kind": "check_face_up_deck", "processability": "unresolved_ruling", "reasons": ["stops_before_acceptance"], "input_disclosure": "confirmed",
 "input_stages": [{"stage": 1, "input": "choose_option"}]}
inputs → {"stages": [{"stage": 1, "input": "choose_option", "role": "face_up_position", "meaning": "deck_position", "count": {"min": 1, "max": 1}, "order": "not_applicable",
  "options": [{"id": "o1", "owner": 1, "position": 1, "eligible": false, "processability": "unresolved_ruling", "reasons": ["stops_before_acceptance"]},
              {"id": "o2", "owner": 1, "position": 2, "eligible": false, "processability": "unresolved_ruling", "reasons": ["stops_before_acceptance"]}]}]}
check / submit（["o1"]）→ refusal CANDIDATE_NOT_EXECUTABLE（エンジンに渡さない）
```

## 2. R-1: カツラの 2 枚目（AttachEnergy.energy2）

### 2.1 今のコード（`engine.check_attach_energy`・`effects.double_attach_check`）

- `energy2` は任意です（None なら 1 枚。v0.58 までの形のまま）
- 2 枚目を指定してよいのは、次の 3 つがそろうとき（`double_attach_check`。カードを動かす前）
  - カツラの効果がこの番にはたらいている（`blaine_effects`。登録されたトレーナーの効果の記録から決める。カード名・カード ID で分けない）
  - つける先が「カツラのポケモン」（`_blaine_pokemon`）
  - 2 枚とも「炎」エネルギーカード（レインボーエネルギーは RB2 で止める。`double_attach_rainbow_check`）
- 同じカードの 2 回の指定は `DUPLICATE_CHOICE`。どちらも本人の手札にあること
- 回数: 2 枚つけたら `energy_attachments_this_turn` が 2 増えます。この番の 2 回目の操作は BL1（未裁定）
- ログ `attach_energy` に `energy2`・`trainer_card` が加わります。反応は、つけたカードの順に 1 枚ずつ（`reactions.attach_steps`）

### 2.2 スキーマ案

- **採用済み**（D-U75-ENERGY2）: R-1 は U7-5g に含める。U7-3 の `attach_energy` に任意の段を足す（追加だけ）
- **推奨**: 3 段目 `energy2` を、カツラの効果がこの番にはたらいているとき（公開のログで決まる）だけ加えます
  - 1・2 段目（`energy` → `target`）は U7-3 のまま（`options_by_choice` も、1 段目の番号で引く今の形のまま）
  - 3 段目は `count` 0〜1（任意）。選べるものは、1・2 段目の組ごとに、本人の手札の別のエネルギーカードで、エンジンの確かめ（`check_attach_energy` に 3 枚の組を渡す）を通ったもの
  - U7-3 の 2 段目の番号は、1 段目の選び方によらず同じ番号です（U7-5e と違う）。そのため、3 段目を 2 段目の番号だけで引けません。3 段目は、1・2 段目の組で引く新しい項目 `options_by_path`（鍵は `"o1/o4"` の形。`path_stages: [1, 2]`）で示します
  - 入力の順: `[energy, target]`（1 枚）か `[energy, target, energy2]`（2 枚）。1 枚だけの入力は、3 段目がない今の形と同じに受け付けます
  - 無効にする範囲: 1 段目か 2 段目を変えたら、3 段目の選び方と検査の結果は無効です
- **判断待ち**（D-U75-ENERGY2-SCHEMA）
  - 3 段目の引き方: 推奨の `options_by_path`（今の 2 段を変えない）か、`attach_energy` の 2 段目を U7-5e の形（選び方ごとに別の番号・`after`）に変えるか
  - 後の案は、今の GUI（`9c36a8f`）の `attach_energy` の画面と番号の意味が変わります

```json
{"stage": 3, "input": "choose_option", "role": "energy2", "meaning": "card", "count": {"min": 0, "max": 1}, "decline": true, "order": "not_applicable",
 "path_stages": [1, 2],
 "options": [{"id": "o9", "card": 41, "card_id": "PMCG1-098", "eligible": true, "processability": "may_stop_later", "reasons": ["reactions_not_evaluated"]}],
 "options_by_path": {"o1/o4": [{"option": "o9", "eligible": true, "processability": "may_stop_later", "reasons": ["reactions_not_evaluated"]}]}}
```

## 3. R-2 と自分のうらのカードの特殊能力

### 3.1 今のコード

- **自分のうらのバトル場のポケモンのワザ**（U7-4）
  - 本人が知る本当のカードの印刷のワザ（`printed_def`。観測の `real` は本人にだけ見える）を、`unverified`（理由 `face_down_reveal_not_evaluated`）で示します
  - 宣言といっしょに選ぶもの（クチバシティジムのコイン・ワザといっしょに使う特殊能力）の段は空（R-2）です
- **自分のうらのカードの特殊能力**: U7-5e は候補にしていません
- **エンジン**: コマンドの入口（`_reveal_for_action`）で、番の確かめのあと、使うポケモンをおもてにします（`UseAttack`・`UsePokemonPower` のどちらも）
  - 本当のカードが「たねポケモン」なら、おもてにしたあとふつうに確かめ、受け付けなければコマンドごと拒否します（状態はもどる）
  - 「たねポケモン」でなければ、ついているカードといっしょにトラッシュし、コマンドを受け付けたことにします（ワザ・特殊能力はおこらない）
  - 受理のあと、おもてにしたカードは全員に公開されます

### 3.2 情報の境界

| 情報 | 本人 | 相手・観戦者 |
|---|---|---|
| うらのカードの本当のカード（`real`） | 知っている（観測の `real`） | 知らない（受理のあとのおもてにした結果で知る） |
| 本当のカードの印刷のワザ・特殊能力 | 知っている | 知らない |
| 宣言といっしょに選ぶものの確かめの結果（おもてにした状態で決まる） | 本当のカードから求められるが、エンジンの確かめはおもてにした状態の上でしか呼べない | — |

- 候補の作成で `_reveal_for_action` を呼んだり、状態の複製の上でおもてにして確かめたりしません（D の試行。カードを表にする処理の先読みになる）
- 本人にだけ入力を示せる条件（**推奨**）
  - 本当のカードの印刷の情報だけで決まり、エンジンの確かめを呼ばない選べるもの（印刷のワザ・印刷の特殊能力と、その型の宣言の段）
  - 応答は本人の入口にだけ返します。相手・観戦者への応答・候補の数・更新には出しません
- 安全に判断できない条件
  - おもてにしたあとの確かめで決まる、宣言といっしょに選ぶもの（R-2）。おもてにした状態の消す効果・回数・クチバシティジムのコインの条件は、本当のカードとほかの場で決まり、候補の作成では確かめられない
  - おもてにした結果「たねポケモン」でなければワザ・特殊能力がおこらないことの予告（D-U75-REVEAL-OUTCOME で予告しない）

### 3.3 仕様

- **推奨**（自分のうらのカードの特殊能力）: U7-4 のワザと同じ形で、本人にだけ、本当のカードの印刷の宣言する特殊能力を候補にします
  - 候補は `unverified`（理由 `face_down_reveal_not_evaluated`）
  - 段は型の宣言（`POWER_INPUT_STAGES`）から作り、選べるものは場の公開の値・本人の手札だけで並べます（エンジンの確かめを呼ばない）
  - 宣言のない型・本当のカードの型が判断できないときは、入力を返しません（`unconfirmed`）
- **判断待ち**（D-U75-FACE-DOWN-POWER）: 上の推奨で候補にするか、R-2 と同じく残す（候補にしない）か
- **推奨**（R-2）: 宣言といっしょに選ぶものは、理由つきの未対応のまま残します（段を空にし、5 章の `residual` で機械で読める形に示す）。`unverified` を付けて公開することはしません
- **判断待ち**（D-U75-R2）: R-2 を扱うには、おもてにしたあとの確かめを候補の作成でどう扱うかの採用（たとえば「本人が知る本当のカードだけで決まる確かめ」の型ごとの宣言）が要ります。採用までは未対応です

## 4. 山札から引いて試すトレーナー 5 つ（PT-5e）の、U7 の保証への影響

- 今回は直しません（別の監査の課題）
- 影響: その 5 つのトレーナーの候補の選べるものは `unverified`（`use_condition_not_evaluated`）です。入力（手札のカード）は公開してよい値ですが、使えるかは送るまで分かりません
- complete の判定（5 章）では、「処理可能性が `unverified` の選べるものが残る」ことを、判定と別の軸（`unverified_paths`）として示す推奨です（complete を、全部が実行できるという意味にしない）

## 5. coverage と U7 の完了の条件

### 5.1 軸

| 軸 | 意味 | 今の表し方 |
|---|---|---|
| 段階と主体 | 準備（初期配置・補償）・番（MAIN）・決定・ホスト（先攻・延長戦）・終局／停止 × 番のプレイヤー・番でないプレイヤー・ホスト | `situation`・`actor` |
| コマンドの種類 | 候補の種類（`kind`） | `scope_kinds`・`not_covered_kinds` |
| 宣言の経路・任意の項目 | 種類の中の、示していない経路（R-1・R-2・自分のうらのカードの特殊能力） | 文書だけ |
| 入力の公開 | `input_disclosure`（confirmed・unconfirmed・no_input） | 候補ごと |
| 処理可能性 | 6 区分 | 候補・選べるものごと |
| 意図した未対応と未確認 | 未裁定・未実装で送れない（FU2 など）・確かめていない（PT-5e など） | 処理可能性と文書 |

- 「候補の取得が対応の範囲を網羅すること（coverage）」と「全部の操作を完走できること（処理可能性）」は別です。complete は前者だけを言います

### 5.2 段階・主体ごとの判定案（推奨）

| 段階 | 主体 | 判定 |
|---|---|---|
| 準備（初期配置・補償） | 置く・引くプレイヤー | complete（今のまま） |
| 準備 | もう置いた・補償のないプレイヤー | 操作なし（complete。`not_actor`） |
| 先攻を決める・延長戦の開始 | ホスト | complete（今のまま） |
| 決定 | 決める人 | 種類は complete。入力を返さない決定（`unconfirmed`）は 5.3 節の `residual` で示す |
| 決定 | 決めない主体 | 操作なし |
| 番（MAIN） | 番のプレイヤー | U7-5f のあとも partial。complete にするのは、全部の種類を評価し、`residual`（R-1・R-2・自分のうらのカードの特殊能力）が空のときだけ |
| 番（MAIN） | 番でないプレイヤー | 操作なし（CheckFaceUpDeckCard はどの場合も受け付けないので、出さなくても実行できる経路は減らない。D-U75-FACE-UP-ACTORS） |
| 終局・停止 | 全員 | 操作なし |

### 5.3 機械で読める残り（推奨）

既存の種類の中に残る未対応を、文書だけでなく応答の coverage で示します（形式 1 への追加。GUI の契約の表は知らない項目で止めるので、表を直すまで安全な側の失敗）。

```json
"coverage": {..., "completeness": "partial",
  "residual": [
    {"id": "R-1", "kind": "attach_energy", "field": "energy2", "status": "not_offered", "reason": "input_not_offered"},
    {"id": "R-2", "kind": "use_attack", "field": "declaration_options", "status": "not_offered", "reason": "face_down_reveal_not_evaluated"},
    {"id": "R-3", "kind": "use_power", "field": "pokemon", "status": "not_offered", "reason": "face_down_reveal_not_evaluated"}],
  "unverified_paths": ["use_condition_not_evaluated"]}
```

- `residual` は、その応答の状況で起こりうる経路だけを書きます。たとえば R-1 は、カツラの効果がはたらく番だけです
- 文書だけの制限（GUI に示さない）: 外部の呼び出しの深い部分の未確認（UP-5t の限界）・PT-5e の監査
- API で返す制限（推奨）: `residual` と `unverified_paths`
- **判断待ち**（D-U7-COMPLETENESS）
  - `residual` を応答に加えるか（文書だけにするか）
  - complete の条件を「全部の種類を評価し `residual` が空」にするか

## 6. 実装の単位・テスト・完了の基準

| 単位 | 内容 | テスト | 完了の基準 |
|---|---|---|---|
| U7-5f | `check_face_up_deck` の表示だけの候補（1 章） | おもての枚数だけで位置が決まる双子（おもてのカードの中身を変える）・自分の山札とおもてでない位置を出さない・送る前の `CANDIDATE_NOT_EXECUTABLE`・状態の不変・番でない主体（採用に合わせて）・client_api | 双子が通り、エンジンに一度も渡さない |
| U7-5g-1 | R-1 の 3 段目（2 章。D-U75-ENERGY2-SCHEMA の採用のあと） | 1 枚の入力の今の形との互換・2 枚の組・同じカード・炎でない・カツラのポケモンでない・RB2・BL1・前段を変えた古い 3 段目の拒否・直接のコマンドとの一致・new_game からの列（カツラ） | 1 枚・2 枚の両方で直接と一致 |
| U7-5g-2 | 自分のうらのカードの特殊能力（3.3 節。D-U75-FACE-DOWN-POWER の採用のあと） | 本当のカードだけが違う双子で、相手・観戦者の応答が同じ・本人の候補は本当のカードの印刷・確かめを呼ばない・おもてにした結果の予告なし | 双子が通る |
| U7-5g-3 | coverage の `residual`・判定（5 章。D-U7-COMPLETENESS の採用のあと） | 状況ごとの `residual` の中身・complete の条件の否定テスト（residual が残れば partial） | 段階・主体の表どおり |

- 順番の推奨: U7-5f → U7-5g-3（残りを機械で読める形にする）→ U7-5g-1 → U7-5g-2。R-2 は D-U75-R2 の採用まで未対応
- どの単位も、実装のあとに限定の検証（新しいテスト・U7・client_api・直接関係する既存のテスト・生成物の検査・lint・配布）を 1 モジュールずつ流します

## 7. この作業で確かめたこと

- 仕様と今のコードの参照の整合（生成した仕様の検査 `scripts/build_legal_actions_u7_5_design.py --check`）
- 3 段の入力の互換性の小さな既知の入力（0.2 節）と、GUI の契約の表の `stage_keys` に対する否定テスト
- この文書・生成した仕様を直接読むテスト（`tests/test_legal_actions_u7_5fg_spec.py`）
- 全体のテスト・状態の監査・lockstep・大きな対戦・広い探索は流していません
