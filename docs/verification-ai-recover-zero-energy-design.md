# UNRESOLVED_RECOVER_ZERO_ENERGY の判定の根拠の条件の設計（調査・設計だけ）

2026-11-16。vai-batch-p2n1 の 2 局目にあった `UNRESOLVED_RECOVER_ZERO_ENERGY` の拒否 1 件（判定は undetermined・`evidence_missing_stop`）について、known_stop として扱える根拠があるかを、保存記録と実行のときのコードで調べ、条件を設計しました。

- この文書は設計だけです。judge・エンジン・検証用 AI・GUI・裁定・規約は変えていません。
- テスト・ビルド・対戦・seed 探索・judge・replay・旧記録への再判定はしていません。
- 機械可読の対応表: [verification-ai-recover-zero-energy-design.json](verification-ai-recover-zero-energy-design.json)（条件・コード・文書・保存例の対応）。
- 証跡: `kyuura-engine-verification-vai/verifier/runs/recover-zero-energy-design/`。

## 1. 基点

| 項目 | 値 |
|---|---|
| 基点 | `claude/p2n1-secret-plan-trace` = `1dfc124`（origin と一致。main `b1e4430` の子孫で、main に入っていない） |
| 作業 | worktree `kyuura-engine-lt53`、ブランチ `claude/recover-zero-energy-design` |
| 対象バッチ | vai-batch-p2n1（[P2-min の new_game 小規模確認バッチ](history/p2-min-batch-plan.md) 10 章） |
| 実行コミット | `00690294c64ad99e7ca43c83bcb22e8cc2be02e3`。エンジン 0.187.0・`TOOL_VERSION` 12・判定の規則 9・形式 7 |
| コードの差 | 基点と実行コミットで `kyuura_engine`・`tools`・`tests`・`scripts`・`pyproject.toml` の差 0。以下のコードの位置は、実行のときと今で同じ |
| 記録の実装の識別 | 記録の header の behavior_digest `ae974fff…` = 今のエンジン |

## 2. 保存済みの 1 件

### 2.1 特定

対象は、2 局目（試行 1）の trace で、検証者の診断の `engine_code` が `UNRESOLVED_RECOVER_ZERO_ENERGY` の試みです。trace にちょうど 1 件あります。

次の記録が、同じ operation_id・試みの番号・position で 1 行ずつ結びつきました。

- 本人（主体 0。P42）の actors の試みの行
- 同じ position の局面の行
- 観測の送信の行（observe/rows）
- 保存済みの判定の undetermined の行

| 識別 | 値 |
|---|---|
| operation_id | 局の 191 番目の操作 |
| trace の試みの番号 | 200 |
| 主体 | 0（P42。boundary 方策） |
| position・episode | 190・191 |

### 2.2 記録で確かめたこと

いずれも本人の当時の記録で、後の状態は使っていません。

| 項目 | 記録の値 |
|---|---|
| 決定を出した操作 | 同じ主体の直前の受理（試みの番号 199・position 189）。`use_attack` で、本人のゴースの「エナジーへんかん」（attack_index 1）を宣言した。応答は `status: awaiting_decision`・`next: [answer_decision（本人）]` |
| 決定の種類 | `recover_energy` |
| 本人に示された入力の形 | 候補は `answer_decision` 1 つで、理由は `continuation_not_evaluated`、`processability` は `may_stop_later`。段は 1 つで、`choose_option`・`meaning: card`・`count {min 0, max 2}`・`decline: true`・`distinct: true`・`order: significant`。選べるものは 4 つ（どれも `may_stop_later`） |
| 本人の観測の決定 | 同じ position の局面の観測でも `recover_energy`・最小 0・最大 2・選べるもの 4。選べるものの並びは段と同じ |
| 実際に選んだ回答 | 0 枚（`choices: []`）。方策は数の段で 0〜2 の 3 通りから 0 を均等に選んだ |
| check | 送信の前に呼んだ。`valid: true`・`refusal: null` |
| submit の応答 | `outcome: rejected`・`refusal: null`・`refetch_required: false` |
| コード・分類 | 検証者の診断と公開の結果で、`diagnostic_id`・`engine_code`・`case_id` がそろって `UNRESOLVED_RECOVER_ZERO_ENERGY`。分類は `unresolved_ruling`・`case_status: identified`・`continuable: true` |
| 拒否のあとの状態 | `status: awaiting_decision`・`stage: decision_answer`・`next: [answer_decision（本人）]`・`halt: null` |
| 拒否の前後の証拠 | 観測の送信の行で、閲覧者 0・1・観戦者の観測の sha256 とログの範囲が、前後で同じ。本人には `own_rejection` の表示だけが届き、ほかの閲覧者には更新がない。`accepted_index: null` |
| 保存済みの判定 | 規則 9 で `undetermined`。理由は `stop_condition_not_evidenced:UNRESOLVED_RECOVER_ZERO_ENERGY`、分類は `evidence_missing_stop`。コード表の分類が一致し、経路の理由（`continuation_not_evaluated`）もあったが、代表の条件の根拠（`KNOWN_STOP_EVIDENCE` の登録と、それを渡す道）がない（`judge._known_stop_or_undetermined`） |

- **記録の事実として残すが、根拠には使わないこと:** 同じ position で、次の試み（番号 201）が同じ決定に 1 枚を答えて受理されました。同じ決定が残っていたことと合いますが、後の出来事なので、停止の条件の根拠には使いません。
- **記録にない項目:** 拒否の時点のエンジンの内部の状態・乱数は、記録に直接はありません。観測の sha256 とログの範囲が変わっていないことだけが記録の証拠です。

## 3. エンジンの停止の条件（実行のときのコード）

| 問い | 答え（コードの位置） |
|---|---|
| このコードを投げる箇所 | **1 か所。** `kyuura_engine/resolution/programs.py:2903`（`RecoverEnergy.resume`）だけ。`effects.py:2095` 付近は、`RecoverEnergyAndSelfDamage` の説明文の中の名前で、投げる箇所ではない（停止の方針の台帳 `docs/stop-policy-classification.json` は、文字列の静的な位置として 2 か所を数えている。台帳は変えない） |
| 要素の登録 | `RecoverEnergy` は `E.RecoverEnergyAndSelfDamage` から作る（`programs.py:10340`）。登録は化石の秘密のゴースの「エナジーへんかん」1 つだけ（`effects.py:23529`。`max_cards=2`・`self_damage=10`） |
| 対象の 1 件の箇所 | 同じ 1 か所（コードが一致し、決定の種類 `recover_energy` で最小 0 を出すのはこの要素だけ。下の行） |
| `recover_energy` で最小 0 の決定を出す箇所 | `RecoverEnergy.run`（`programs.py:2897`。`min_choices=0`・`max_choices=min(max_cards, 選べるもの)`）だけ。`RecoverEnergyByHeads`（`programs.py:6449`）は最小と最大が「おもて」の数（1 以上。0 なら決定を出さない）、`RecoverSpecialEnergy`（`programs.py:14600`）は既定の 1〜1 |
| 止まる時点 | ワザの途中の決定への回答のとき（受理の前）。宣言（`use_attack`）は受理済みで、決定を待っている状態に `ResolveDecision` で答えたときの拒否。受理のあとの停止ではない |
| 0 枚の回答を入力として許す理由 | H4（[haunter-line-v0.9.md](haunter-line-v0.9.md)）。「最大2枚」が 0 枚を含むかは原典で決められない。そのため、決定は 0 枚も受け付ける形（`min_choices` 0）にして、受け付ける（手札に加えずに終える）とも、形の不正（`INVALID_CHOICE_COUNT`）とも決めない。0 枚を答えたときだけ、未裁定として止める |
| 0 枚を拒否する条件 | 決定の確認（`checks.decision_choices` → `decisions.check_choices`: 決定の番・決める人・決定の番号・数 0〜最大・重なり・選べるもの・`unresolved_choices`）を通ったあと、解決の基盤の再開（`engine._answer_decision_once` → `resolution.resume_decision` → `RecoverEnergy.resume`）の最初に `choices` が空なら投げる |
| ほかの拒否との順序 | 決定の確認の拒否（`IllegalActionError`。数・重なり・選べないもの）が先。0 枚は数の範囲の中なので、確認を通り、再開で H4 になる。選べるものの検査（`RuntimeError`。エンジンの不具合）は 1 枚以上のときだけ |
| 拒否のときの扱い | 状態を変える前に投げる。`apply_command` は複製の上で処理し、拒否なら渡された状態・乱数・ログは変わらない。決定は待ったままで、1 枚以上を選び直せる（`tests/test_haunter_line_v0_9.py: test_zero_cards_is_unresolved` が、状態・乱数の指紋・ログの同一と、選び直しの受理を確かめる） |
| 先読み | `RecoverEnergy.dry_choices` は 1 枚以上だけを試す（`all_answers(minimum=1)`）。0 枚は宣言を止める理由にしない（[preflight-optimization-v0.15c.md](preflight-optimization-v0.15c.md)） |
| 同じコードで別の根拠が要る経路 | **今のコードにはない。** ただし、ほかのワザをコピーするワザ（相手のワザを自分のワザとして使う）でエナジーへんかんを使う経路は、同じ要素・同じ決定・同じ条件になる（使い手のカードが違うだけ）。条件は要素と決定の形で決め、カードでは限定しない（5 章の R4） |

**未裁定の問いと、実装の保守的な停止の区別**

| 種類 | 内容 | 記録 |
|---|---|---|
| 研究上の未裁定（問い） | 「最大2枚選び出し」が 0 枚を含むか（H4）。原典（p.158）から決められない | 規則の文書 [rules-2000-02-14.md](rules-2000-02-14.md) の H4 の行。kyuura の `UQ-ENERGY-CONVERSION-ZERO`（disposition `issue`）。研究への対応 `research_links.json` |
| 実装の保守的な停止（扱い） | 0 枚の回答を、状態を変える前に `UnsupportedError` で拒否し、決定を残す。受け付けも形の不正もしない | 診断のコード表: 分類 `unresolved_ruling`・`raised_as: unsupported`・`case_status: identified`。停止の方針の台帳: `research_stop_code`・分類 C・P2・族 `PF-UP-TO-ZERO`・`current_stop` は `answer_rejection`・`mode_policy_status: decision_required`。規約の記録 `convention_records.json` には `research_stop_code` の項目として載る（ER9 と同じ扱い） |
| 実装の選択（停止の外） | 先読みで 0 枚を試さない（宣言は止めない） | `dry_choices` の注記 |

原典の読み直しや、新しい裁定の調査はしていません。停止の方針の台帳の「公式資料に記述がないことの再確認」は、未確認のままです。

## 4. ER9 との比較

ER9（`UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE`）は、判定の規則 6（`judge.RECORDED_STOP_CONDITIONS`・`recorded_stop_evidence`）で、記録した送信の API の値だけを確かめて根拠にしています。

| 比べるもの | ER9（既存） | 今回（H4） | 共通／個別 |
|---|---|---|---|
| 効果・再開先 | エネルギー回収（トレーナー）の 2 段階目。再開先 `trainer`（`effects.DiscardFromHandThenRetrieveEnergy.resume`。文脈 `discarded`） | ゴースのワザの途中（解決の基盤の再開。`RecoverEnergy.resume`） | 個別 |
| 決定・入力の種類 | `retrieve_energy`・`answer_decision`・段 1 つ・`choose_option` | `recover_energy`・`answer_decision`・段 1 つ・`choose_option` | 形は共通、種類は個別 |
| 0 枚を許す構造 | `min_choices` 0。最大は min(2, 選べるもの) | `min_choices` 0。最大は min(`max_cards`=2, 選べるもの) | 共通 |
| 0 枚を拒否する位置 | 決定の確認のあと、トレーナーの再開の中 | 決定の確認のあと、解決の基盤の再開の最初 | 個別（どちらも状態を変える前） |
| 選んだ対象と参照の検証 | 選んだ意味が空であることだけ（対象の参照はない） | 同じ。加えて本人の観測の決定と段の一致（R10）を足す | 空の回答の検査は共通。観測との照合は今回だけ |
| 停止の条件に要る公開の情報 | 送信の応答（拒否・コード・分類・決定待ち・`next`）。公開の情報だけで足りる | 同じ | 共通 |
| 停止の条件に要る本人向けの情報 | 段（選べるものの数・最小・最大）。本人の inputs の応答 | 同じ。加えて、送信前の本人の観測の決定（actors の局面の行） | 共通＋今回だけ |
| 拒否のあとの状態と再回答 | 決定は待ったまま。1 枚以上を選び直せる（`test_zero_cards_is_unresolved_and_keeps_the_decision`） | 同じ（`test_zero_cards_is_unresolved`）。保存例でも同じ position で回答し直して受理（根拠には使わない） | 共通 |
| 根拠を固定する basis | **なし**（コード名・決定の種類・API の値だけ） | **要る**（R11。決定の種類 `recover_energy` と最小 0 から、要素と投げる箇所が 1 つに決まることを、ファイルの識別で固定する） | 個別 |
| 単局・バッチの受け渡し | 単局の runner と逐次バッチが `submit_evidence` を呼び、最初に規則 6 を見る | 同じ入口。規則 6 のあと、P1・P2・P3s の前に見る（下の 5.4） | 入口は共通 |

**共通にできる証拠の処理**（規則 6 の本体を、種類の引数で使う形に分けられる）:

- 拒否で、検証者の診断と公開の結果のコードがそろう
- 候補が `answer_decision` で、段が 1 つ
- 選んだ意味が空
- 最小 0・最大が整数で 1 以上・選べるものが 1 つ以上
- 拒否のあとも同じ主体の決定待ちで、`next` が本人の `answer_decision` だけ
- 取り直しが要らない

**個別に確かめる停止の条件:**

- 決定の種類 `recover_energy`
- 最大が選べるものの数以下（R5）
- 本人の観測の決定との一致（R10）
- basis（R11）

ER9 の表（`RECORDED_STOP_CONDITIONS`）に `recover_energy` を足すだけの拡張はしません。名前と「0 枚で拒否」が似ていても、再開先・要素・basis の要否が違います。ER9 の条件・理由・判定は変えない前提です。

## 5. 設計の結論: A（限定した known_stop の条件を登録できる）

### 5.1 根拠

- 保存記録だけで、停止の代表の条件（選べるものが 1 つ以上ある `recover_energy` の決定に 0 枚を答え、受理の前に拒否され、同じ決定が残った）を直接確かめられる。後の状態・完全な記録・相手の情報は要らない。
- 実行のときのコードで、投げる箇所は 1 つ。最小 0 の `recover_energy` を出すのも 1 つの要素だけで、記録の値とコードの経路が 1 対 1 に結びつく。
- 拒否の前後で、閲覧者すべての観測とログが変わっていない（記録）。エンジンの拒否は状態を変えない（既存のテスト）。
- 保存例は、5.2 の R1〜R11 を記録の値ですべて満たす（`out/saved_case.json` の `conditions_on_record`。R11 は、記録の behavior_digest が実行のときのエンジン＝今のエンジンと同じこと）。R12 はコードが違うことからの静的な判断で、judge を走らせて確かめてはいない。どれも読み取りだけで、judge は当て直していない。

追加の API・記録の項目は要りません（B ではない）。根拠が不足してもいません（C ではない）。

### 5.2 最初に登録する範囲と条件

- **範囲:** 解決の基盤の要素 `RecoverEnergy`（ワザの途中の決定 `recover_energy`。最小 0）への回答だけ。今の登録ではゴースの「エナジーへんかん」で、ワザのコピーの経路も同じ要素なのでふくむ。
- **鍵:** `UNRESOLVED_RECOVER_ZERO_ENERGY`（コード名そのもの。経路の名前の鍵は要らない。このコードの経路は 1 つ）。

| 番号 | 条件 | 記録の出所 |
|---|---|---|
| R1 | 送信の `outcome` が `rejected`。検証者の診断の `engine_code`・`diagnostic_id` と、公開の結果の `diagnostic_id` が、どれも `UNRESOLVED_RECOVER_ZERO_ENERGY` | trace の submit |
| R2 | 分類が、診断・結果・コード表で `unresolved_ruling`（既存の `_known_stop_or_undetermined` の照合と同じ） | submit・コード表 |
| R3 | 候補が `answer_decision` で、候補の理由に `EXPLAINING_REASONS` のどれかがある（記録では `continuation_not_evaluated`） | trace の candidate |
| R4 | 段がちょうど 1 つで、`decision_kind` が `recover_energy`、`input` が `choose_option`、`meaning` が `card` | trace の stages |
| R5 | `count.min` が 0、`count.max` が整数で 1 以上、選べるものの数以下 | trace の stages |
| R6 | 選べるものが 1 つ以上で、`id` が重ならない | trace の stages |
| R7 | 選んだ意味が空（`meaning == []`）で、本人の試みの `choice.choices` も空 | trace・actors の試み |
| R8 | 送信の前の check が `valid: true`・`refusal: null`（check がない・不正なら根拠にしない） | trace の check |
| R9 | 拒否のあとも `status: awaiting_decision`・`stage: decision_answer`・`next == [{answer_decision, player: viewer}]`、`viewer` が送った主体、`refetch_required: false` | submit |
| R10 | 送信前の本人の観測（同じ position の局面の行がちょうど 1 つ）の決定が、`recover_energy`・最小 0・最大が段と同じ・選べるものの数と並びが段と同じ。本人の試みの inputs が `refetch_required: false` で、同じ position | actor_logs（本人の観測）・actors の試み |
| R11 | 判定の基礎が記録と同じ: 記録の behavior_digest が今と同じか、記録を作ったエンジンの同じファイルから同じ方式で計算した `basis_r` が今の基礎の識別と同じ（`_basis_matches` と同じ式。カードプールの照合をふくむ） | 記録の header・呼ぶ側の basis |
| R12 | 規則 6（ER9）・規則 7（P1）・規則 8（P3s）・規則 9（P2-min）のどれも根拠を返していない（コードが違うので、重ならないはず。重なれば矛盾として根拠にしない） | `submit_evidence` |

**対象の外**（どれも undetermined のまま。今と同じ）:

- `recover_energy` で最小が 1 以上の決定（`RecoverEnergyByHeads`・`RecoverSpecialEnergy`）
- ER9・超エネルギー回収などのほかの「0 枚」のコード
- 受理のあとの停止（`halt`）
- `refused`（API が送信を断った）
- `failed`・例外
- 1 枚以上を選んだ回答の拒否（この経路では `RuntimeError` か決定の確認の `IllegalActionError`。正常な拒否の規則で扱う）
- 宣言（`use_attack`）の拒否

**欠落・矛盾・古い観測・参照の不一致の扱い:**

- **欠落:** stages・check・actor_logs・局面の行・header がない、または必要な項目がない。根拠にしない（None）。
- **矛盾:** 診断と結果のコード・分類が違う、本人の観測の決定と段が違う、局面の行が 2 つ以上ある、`choice.choices` と `meaning` が食い違う。根拠にしない。
- **古い観測:** inputs・submit の `refetch_required` が真、または局面の position が試みと違う。根拠にしない。
- **参照の不一致:** basis が合わない（R11）。根拠にしない。旧記録の basis の不一致を例外として扱う道は作らない。

### 5.3 basis（案）

- **方式:** `kyuura-recover-zero-basis-sha256/1`。`replay_record._digest` と同じ正規化・要約で、下の 4 ファイルだけを要約する。
- **参考値:** 実行コミットの各ファイルの sha256 は `out/saved_case.json` の `basis_candidate` にあります。実装の値は `_digest` で計算します。

| ファイル | 要る理由 |
|---|---|
| `resolution/programs.py` | 投げる箇所が 1 つ（`RecoverEnergy.resume`）であること。最小 0 の `recover_energy` を出すのがこの要素だけであること（ほかの `recover_energy` の要素の最小）。要素の作り方（`RecoverEnergyAndSelfDamage` から） |
| `decisions.py` | 決定の確認（`check_choices`）が、数の範囲の中の 0 枚を通し、再開より先に形の不正を拒否する順序。決定の種類の定数 |
| `engine.py` | `_answer_decision_once` の再開先の振り分け（解決の基盤）と、`apply_command` が複製の上で処理して、拒否のときに状態を変えないこと |
| `legal_actions.py` | API の段の値（`decision_kind`・`count`・選べるもの）が、エンジンの決定の種類・最小・最大・選べるものから作られること。R4〜R6 が決定を写したものであること |

`effects.py`（登録）は入れません。条件は要素と決定の形で決め、カードの登録には依存しないからです。登録が変わって別のカードがこの要素を使っても、同じ条件・同じ停止です。

### 5.4 ほかの根拠の規則との重なり

- `submit_evidence` の順は、規則 6（ER9）→ 新しい規則（H4）→ P1・P2・P3s（ちょうど 1 つ）。
- H4 はコードが違うので、ER9・LOST_TARGET の規則とは重ならない。重なりの検査（R12）は、矛盾の検出のためだけに置く。
- `KNOWN_STOP_EVIDENCE` に `UNRESOLVED_RECOVER_ZERO_ENERGY` の項目（condition・source）を 1 つ足す。`_known_stop_or_undetermined` の式（鍵 = 元のコード）は変えない。

## 6. テストの計画と互換性（実装するとき。今回は足さない・走らせない）

### 6.1 正負のテスト

| 区分 | テスト |
|---|---|
| 正 | 保存例と同じ形の送信の行（段 1・`recover_energy`・0〜2・選べるもの 4・空の回答・拒否・決定待ち・本人の観測が一致・basis が一致）で鍵を返し、`judge_normal` が known_stop |
| 正 | 最大が 1（トラッシュのエネルギーカードが 1 枚）でも同じ |
| 負: 回答 | 1 枚・2 枚の回答（意味が空でない） → None |
| 負: 別の決定 | `retrieve_energy`（ER9 は ER9 の鍵のまま）・`recover_energy` で最小 1 → None |
| 負: 別のコード | 同じ形で `INVALID_CHOICE_COUNT`・ほかの `UNRESOLVED_…` → None |
| 負: 欠落 | stages・check・actor_logs・局面の行・header・選べるものがない → None |
| 負: 古さ | inputs・submit の `refetch_required` が真、局面の position が違う → None |
| 負: 矛盾 | 診断と結果のコード・分類が違う、本人の観測の最小・最大・選べるものが段と違う、局面の行が 2 つ → None |
| 負: 拒否のあと | `status` が `in_progress`・`halted`、`next` がほかの主体・ほかの種類 → None |
| 区別 | `refused`（API の断り）・`failed`（例外）・受理のあとの停止（`judge_halt_after_accept`）では鍵を使わない |
| 負: basis | behavior_digest が違い、basis がない・違う → None。basis が同じ → 鍵 |
| 非干渉 | ER9 の既存の正負のテストは同じ結果。P1・P2-min・P3s の正の送信で、H4 の鍵を返さない。H4 の正の送信で、P1・P2・P3s は None |
| 一致 | 同じ送信の行で、単局の runner の入口・逐次バッチ（`batch.judge_trace`）・保存した記録からの読み直し（basis を渡す）の 3 つが同じ鍵・同じ判定 |
| エンジンの前提 | 既存の `test_zero_cards_is_unresolved`・`RecoverZeroEnergyBoundaryTest` に加え、静的な前提（投げる箇所 1 つ・最小 0 の `recover_energy` は 1 要素）を確かめるテスト（P2-min の S1〜S3 と同じ考え） |

### 6.2 想定の影響

| 項目 | 想定 |
|---|---|
| 判定の規則 | `JUDGE_RULES_VERSION` を 9 から 10 へ |
| `TOOL_VERSION` | 12 から 13 へ（judge の規則と、`submit_evidence`・`judge_trace` に `basis_r` を渡す引数が加わる。P2-min のときと同じ形） |
| 計画・完了の形式 | 7 のまま（計画に新しい項目は要らない） |
| basis | 新しい方式 1 つ（5.3） |
| エンジンの版・旧記録の識別 | 変えない前提（エンジンのコードは変えない） |
| 保存済みの判定 | 書き換えない。規則 9 の判定のまま残る |

**今回の保存例への当てはめ:** 記録の behavior_digest が今と同じなので、新しい規則を当てれば R11 は満たす見込みです。記録の値では R1〜R10 も満たします（5.1。R12 は静的な判断）。当て直しは別の作業として依頼があったときだけ行い、元の判定・COMPLETE は書き換えません。

**ほかの旧記録への一般化:**

- 記録の behavior_digest が今と同じ記録には、そのまま当てはまる。
- 違う記録は、その記録を作ったエンジンの 4 ファイルから計算した basis が今と同じときだけ当てはまる。
- basis が合わない記録は undetermined のまま。例外としては扱わない。
- 実際に旧記録を調べて当てはまる数を出すことはしていない（未確認）。

## 7. 未確認・失敗

- **未確認:**
  - 原典に記述がないことの再確認（台帳の `unverified_scope`。今回の範囲の外）
  - ER9 の規則 6 の前提（`retrieve_energy` で最小 0 を出す要素の数）。今回は ER9 の条件を読んだだけ
  - ほかの旧記録への当てはまり
  - basis の値を `_digest` で計算すること（実装のとき）
- **失敗と直したこと:** 抽出スクリプトの 1 回目は、本人の観測の決定の項目名を読み違え（`decision` を `pending_decision` として読んだ）、R10 が偽になった。出力は `out/saved_case_attempt1_wrong_key.json` として残した。直そうとしたコマンドが引用の誤りで失敗し、直していないスクリプトがもう一度走った（`out/saved_case_attempt2_rerun_unedited.json`。中身は 1 回目と同じ）。ファイルを編集して直した 3 回目で、R10 を含むすべての条件が真になった。

## 8. 実装の結果（2026-11-16。判定の規則 10・TOOL_VERSION 13）

- 実装と、構築盤面での限定の確認だけを行いました。
- 保存済みのバッチ（vai-batch-p2n1）の正式な再判定はしていません。元の judge.json・trace・COMPLETE は変えていません。
- 新しい対戦、エンジンの処理・裁定・規約の変更もしていません。
- 証跡: `kyuura-engine-verification-vai/verifier/runs/recover-zero-judge-r10/`。

### 8.1 エンジンの前提（テストで確認。エンジンは変えていない）

[tests/test_recover_zero_energy_premise_v0_187.py](../tests/test_recover_zero_energy_premise_v0_187.py)（6 件）で次を確認しました。

- **投げる箇所:** 構文木の文字列の定数で数えると、`UNRESOLVED_RECOVER_ZERO_ENERGY` は `resolution/programs.py` の `RecoverEnergy.resume` の 1 か所だけです。`raise UnsupportedError(...)` の最初の引数で、説明文の中の名前は別の、より長い文字列なので数えません。
- **最小 0 の決定:** `kind=RECOVER_ENERGY` で決定を作る `suspend` は 3 要素あります。
  - `RecoverEnergy`: 最小 0
  - `RecoverEnergyByHeads`: 最小は「おもて」の数で、0 なら決定を出さない
  - `RecoverSpecialEnergy`: 既定の 1
  - 要素を作る効果 `RecoverEnergyAndSelfDamage` の登録は、ゴースのエナジーへんかんだけです。
- **0 枚の回答:** 決定の確認（`checks.decision_choices`）を通り、そのあと状態を変える前に対象のコードで拒否されます。状態・乱数の指紋・ログ・決定（同じオブジェクト・番号・本人）は変わりません。
- **1 枚以上の回答:** 1 枚は受理されます。重なり（`DUPLICATE_CHOICE`）と数の超過（`INVALID_CHOICE_COUNT`）は別のコードです。
- **ワザのコピーの経路:**
  - ピッピ（PMCG1-067）とピクシー（PMCG2-044）の「ゆびをふる」（`CopyOpponentAttackEffect`。登録はこの 2 枚だけ）で相手のゴースのエナジーへんかんを選ぶと、同じ決定の種類・最小・再開先（`attack`）・拒否になります（文脈 `copied`）。この 2 つの経路だけを対象にふくめました。
  - メタモンの［へんしん］でも同じコードに届くことを構築盤面で見ましたが、決定を出したワザがバトル場の印刷のカードのワザではないので、対象の外です（R13。下の 8.2）。
  - 思い出させる・サイコリンク・ものまね・げんしのきおく・にんぎょうつかい・カスミのコダックの「ちょうのうりょく」などは確かめておらず、対象の外です。

前提はすべて成り立ちました。エンジンの同時の修正はしていません。

### 8.2 判定（`tools/verification_ai/judge.py`）

- **規則:** ER9 とは別の根拠の項目（`KNOWN_STOP_EVIDENCE["UNRESOLVED_RECOVER_ZERO_ENERGY"]`。鍵は元のコードそのもの）と、判定の関数 `recover_zero_energy_failure`・`recover_zero_energy_evidence` を足しました。ER9 の表（`RECORDED_STOP_CONDITIONS`）は変えていません。
- **確かめる順:** R1〜R10 → R13 → R11（`RECOVER_ZERO_CONDITIONS`）。最初に満たさない条件の id を返します。

| 条件 | 実装 |
|---|---|
| R1 | rejected・ok・refusal なし・error なしで、診断の engine_code・diagnostic_id と結果の diagnostic_id がそろって対象のコード |
| R2 | 分類が診断・結果・コード表で `unresolved_ruling` |
| R3 | 候補が `answer_decision` で、候補の理由に `EXPLAINING_REASONS` のどれか |
| R4 | 段がちょうど 1 つ（stage 1・`recover_energy`・`choose_option`・`card`） |
| R5 | 最小が整数 0、最大が整数で 1 以上・選べるものの数以下 |
| R6 | 選べるものが 1 つ以上、id・card が重ならない |
| R7 | `meaning == []` かつ `choices == []` |
| R8 | check が ok・取り直し不要・valid・断りなし |
| R9 | 拒否のあとも `awaiting_decision`・`decision_answer`・continuable・`next` が本人の `answer_decision` だけ・viewer が本人・halt なし・取り直し不要 |
| R10 | 送信前の本人の観測がちょうど 1 つで、決定待ち・本人の番・同じ番。観測の決定が `recover_energy`・本人・`card`・最小 0・最大と選べるものの数と値の並びが段と同じ。同じエピソードで送信より前の受理がない（古くない） |
| R13（実装で追加） | 決定を出した経路が確かめた経路: 同じ trace の、送信より前の受理の最後が (a) 本人の印刷のカードのワザ（route `form`・選べるものの card と card_id が送信前の本人の観測のバトル場と同じ・登録の効果が `RecoverEnergyAndSelfDamage`）の `use_attack` で本人の決定待ちになった、または (b) `select_attack` への本人の 1 つの答え（選んだワザの登録の効果が `RecoverEnergyAndSelfDamage`）で、その前の受理が本人の印刷のカードの `CopyOpponentAttackEffect` の `use_attack` |
| R11 | 専用の basis（8.3） |
| R12 | `submit_evidence` が確かめる（下） |

- **共通の入口と重なり（R12）:** `submit_evidence` は、規則 6（ER9）・規則 10・規則 7（P1）・規則 9（P2-min）・規則 8（P3s）をすべて評価し、根拠を返すものがちょうど 1 つのときだけその鍵を返します。2 つ以上なら矛盾として None です。規則 9 までの「ER9 が根拠を返せば、ほかを見ずに返す」をやめ、呼ぶ順で重なりを隠しません（重ならない入力の結果は同じ）。
- **単局とバッチ:** 単局の runner（`runner.py`。変異の実行の中の判定）と逐次バッチ（`batch.judge_trace`）は、同じ `submit_evidence` を呼びます。`judge_trace` に `basis_r` を足しました。runner は記録の header の識別で判定し、basis を渡しません。
- **対象の外（undetermined のまま）:** 欠落・矛盾・古い観測・対象外の決定・効果・経路、basis の不一致。refused・failed（`judge_normal` が suspect にする）と、受理のあとの停止（`judge_halt_after_accept` は根拠を受け取らず、`halt_condition_not_evidenced`）には使いません。
- **回答し直しの受理:** 構築盤面のテストで補足として確かめていますが、条件には使いません。

### 8.3 専用の basis と旧記録

- **方式:** `kyuura-recover-zero-basis-sha256/1`。`replay_record._digest` と同じ正規化・要約で、次の 8 ファイルを要約します。
- **ファイル:** 設計の 4 ファイル（`resolution/programs.py`・`decisions.py`・`engine.py`・`legal_actions.py`）に、実装で 4 ファイルを足しました。

| 足したファイル | 理由 |
|---|---|
| `resolution/flow.py` | 決定への答えを要素の resume に渡す `resume_decision` があるのは、`engine.py` ではなくここ |
| `checks.py` | 決定の確認の入口 `decision_choices` |
| `observation.py` | R10 の観測の決定と、R13 のバトル場の card・card_id の形 |
| `effects.py` | R13 が引く効果の登録（設計 5.3 節では入れない予定だったが、経路の限定を足したので要る） |

- **一致の条件**（`_r_basis_matches`）: 記録の依存（カードプール・カードデータの出どころ・効果の登録）が今と同じで、次のどちらか。
  - (a) 呼ぶ側が渡した `basis_r` が、今の基礎と方式・ファイルの並び・要約まで同じ。
  - (b) `basis_r` を渡さず、記録の実装の識別（方式・behavior_digest）が今のエンジンと同じ。かつ、基礎のファイルがすべて behavior のファイル（instrumentation でない）にふくまれる。behavior_digest が基礎のファイルの中身を覆うので、今のファイルが記録を作ったファイルと同じだと確かめられます。

**旧記録の扱い:**

- 記録・header・計画に basis を後付けしません。
- `basis_r` を渡して合わなければ、(b) が成り立っても一致としません。
- 実装の識別が違う記録は、記録を作ったエンジンのパッケージから `recover_zero_basis(root)` で計算した値を渡したときだけ一致します。対応するソースを示せなければ undetermined のままです。
- 許可リスト・例外はありません。P1・P2・P3 の basis は読みません。

### 8.4 テストと単局・バッチの一致

[tests/test_verification_ai_recover_zero_r10.py](../tests/test_verification_ai_recover_zero_r10.py)（20 件）。実装の前に走らせて失敗することを確かめ（65 のエラー・2 つの失敗）、実装のあとで通りました。

- **正:**
  - 保存例と同じ形（0〜2・選べるもの 4）
  - 最大 1
  - ゆびをふる（ピッピ・ピクシー）
  - 起点と送信のあいだに拒否があっても通る
- **負:**
  - 1・2 枚の答え、`choices` と `meaning` の食い違い
  - 別の決定（`retrieve_energy`）・最小 1・別のコード（ER9・超エネルギー回収・`INVALID_CHOICE_COUNT`）・公開のコードの違い・分類の違い・別のワザの起点
  - 段の欠落・空・2 つ・入力や意味の違い・最大 0・最大の超過・最大が文字列・選べるものなし・card の重なり・id の重なり・card のない選べるもの
  - 候補の種類・理由なし
  - check の欠落・invalid・断り・取り直し
  - 拒否のあとの status・next（ほかの主体・番の操作）・viewer・取り直し・halt・stage
  - refused・failed・error、受理のあとの停止
  - 観測の欠落・重なり・viewer・ok でない・番でない・段階・決定なし・番の違い・種類・最小・最大・値の並び・数・決定の本人、同じエピソードの前の受理
  - 経路（起点なし・あいだのほかの主体の受理・起点が決定待ちでない・route・ワザの位置・メタモン・起点の観測なし・ゆびをふるのない選択・選んだワザの違い）
  - basis（同じ・同じで正しい basis・同じで違う basis・header なし・識別の違い・識別が違い正しい basis・違う要約・違うファイルの並び・P2 の basis・効果の登録の違い・方式の違い）
  - ほかの規則との重なり（4 つの規則それぞれが根拠を返すと None）
  - ER9 の送信は ER9 のまま
- **構築盤面:**
  - ゴース・ピッピ・ピクシーの盤面を本物の runner に通しました。逐次バッチの入口・単局の runner の判定・保存した形（trace・`actors/*.jsonl`）からの読み直しが、同じ known_stop の行になりました。
  - メタモンの盤面は R13 で undetermined でした。
  - header なしは、両方の入口で undetermined（`evidence_missing_stop`）でした。
  - 識別を変えた記録は、`basis_r` を渡したときだけ known_stop で、P2 の basis では undetermined でした。
  - 停止の方針では止めず、判定の行にカード ID はありません。

**関連のテスト:** 対象と理由を実行前に `spec/test_selection.md` に記録し、1 モジュールずつ別のプロセスで走らせました（結果は 8.5）。版の期待は 11 モジュールで、規則 9→10・TOOL_VERSION 12→13 に更新しました（旧の期待を注記に残しています。そのうち 1 行は再実行のあとに直しました）。固定の指紋は更新していません。

### 8.5 規則・識別の前後（実測）

| 項目 | 前（fe4e405） | 後 |
|---|---|---|
| 判定の規則 | 9 | 10 |
| TOOL_VERSION | 12 | 13 |
| 道具の要約（tools/verification_ai） | 8cfa17bb… | be95aa1e… |
| 計画・完了の形式 | kyuura-vai-batch-plan/7・kyuura-vai-batch-complete/7 | kyuura-vai-batch-plan/7・kyuura-vai-batch-complete/7 |
| エンジンの版 | 0.187.0 | 0.187.0 |
| behavior_digest | ae974fff… | ae974fff… |
| instrumentation_digest | 13c773a8… | 13c773a8… |
| P1 の basis | 2ed8732f… | 2ed8732f… |
| P3 の basis | 9499db41… | 9499db41… |
| P2 の basis | 720f4641… | 720f4641… |
| 規則 10 の basis | （なし） | a3a9c84c… |

- 旧の計画（TOOL_VERSION 12）は、既存の道具の識別の照合で再開しません。再開を通す回避の処理は足していません。
- 形式の変更は要りませんでした。

**関連のテストの結果:** 23 モジュール中、1 回目に 22 が終了コード 0、`tests.test_verification_ai_lost_target_p3` が 1 つの失敗でした。原因は、版の期待のタプルの形の 1 行（`(9, 12)`）を更新し忘れたことです。その行を `(10, 13)` にして、同じモジュールだけ再実行し、通りました（1 回目の出力は `tests_out/tests.test_verification_ai_lost_target_p3_attempt1_failed.txt` に残しています）。既知の時間に依存する prestop のテストも、今回は通りました。全体のテストはしていません。

### 8.6 保存例と、次の単位

- この実装で、vai-batch-p2n1 の 2 局目の 1 件を正式に再判定してはいません。保存済みの判定（規則 9 の undetermined）はそのままです。
- **当て直す場合の最小の単位:** 保存済みの 2 局の記録から、新しい作業の場所で `batch.judge_trace` を読み直しの形（trace・actors・記録の header）で当て直します。結果は新しいファイルに書き、元の judge.json・COMPLETE は変えません。
  - 記録の header の behavior_digest は今と同じなので、basis は (b) の条件で確かめる見込みです。
  - ほかの判定の行が変わらないこと（差分は対象の 1 行だけ）も照らします。

## 9. 保存済みの vai-batch-p2n1 の 2 局への派生評価（2026-11-16）

8.6 節の次の単位として、判定の規則 10 を保存済みの 2 局に派生評価として当てました。

- **元の判定はそのまま:** 元のバッチの規則 9 の判定（judge.json・COMPLETE・aggregate・ledger・計画・ハッシュの表）は保存したまま変えていません。
- **派生評価の保存先:** 元のバッチの外の `kyuura-engine-verification-vai/verifier/runs/p2n1-rule10-derived/derived-1/` です。
- **評価に使ったもの:** コミット `9a64f8e`（実装 `824c555` とコードの差 0）と、評価用の worktree `kyuura-engine-lt55` です。
- **使わなかった手段:** batch run・resume・`--acknowledge-stop`・unlock・テスト・対戦・replay は使っていません。

### 9.1 渡した証拠

渡したのは、今の `batch.judge_trace` に、`batch.play` が渡すのと同じ種類の値です。

- trace（`trace.jsonl`）
- 本人の観測（`actors/0.jsonl`・`1.jsonl`・`host.jsonl`）
- 記録の header のうち、判定が読む識別と依存（`engine`・`dependencies`）
- 終了の情報（`result.json` の `termination`）

どの入力も、局の `files.sha256.json` と照らしてから使いました。完全な記録の操作・初期の状態・replay は使っていません。

### 9.2 識別と basis の確かめ方

- **記録と評価のソース:** 2 局の記録の header の behavior_digest（`ae974fff…`）・instrumentation_digest（`13c773a8…`）・依存（既定のカードプール・カードデータの出どころ・効果の登録）は、評価のソースの識別と同じでした。
- **規則と道具の版:** 記録時は判定の規則 9・TOOL_VERSION 12（計画の識別）、評価時は規則 10・TOOL_VERSION 13 です。局の header の `tool.version` の `v1` は、局の道具の名前の版で、TOOL_VERSION ではありません。
- **basis の 8 ファイル:** どれも behavior のファイル（instrumentation でない）にふくまれます。実行コミット `0069029` の同じファイルとも、バイト単位で同じでした。
- **basis の渡し方:** `basis_r` は渡していません。実装の (b) の道（記録の behavior_digest が今と同じで、基礎のファイルを覆う）で確かめ、`_r_basis_matches` は 2 局とも真でした。
- **後付けなし:** 記録・header・計画に basis や新しい識別を書き足していません。

### 9.3 結果

**行の対応:** 送信行は 457 行（1 局目 218・2 局目 239）です。試みの番号で 1 対 1 に対応し、欠落・重複・対応不能はありませんでした。trace の送信の数とも同じで、並びも同じです。

**差の分類:**

| 種類 | 1 局目 | 2 局目 |
|---|---|---|
| 正規化していない全差分の箇所 | 1 | 9 |
| メタデータの差 | `rules_version` 9→10 | `rules_version` 9→10 |
| 判定内容の差（行） | 0 | 1 行（試み 200） |
| 判定内容の差（行の差から決まる集計） | 0 | `counts`・`by_kind.answer_decision` の undetermined 1→0・known_stop 0→1、`undetermined` の一覧から試み 200 が外れ、`known_stop` に試み 200 |
| 終わり方の判定 | 同じ | 同じ |

**変わった 1 行:**

- 2 局目の `UNRESOLVED_RECOVER_ZERO_ENERGY`（`answer_decision`・rejected）の行が、undetermined（`stop_condition_not_evidenced`）から known_stop に変わりました。
- 理由は `unresolved_ruling`・コード・`continuation_not_evaluated`・規則 10 の根拠の条件です。
- 規則 10 の条件（R1〜R11・R13）の確かめは、最初に満たさない条件なし（None）でした。根拠は対象のコードの 1 つだけで、R12 の重なりもありません。

**変わらなかったもの:**

- ほかの 456 行の判定・理由・診断は、まったく同じでした。
- 受理の中身の判定と、終わり方の判定も同じです。
- 無視した項目はありません（全差分・メタデータの差・判定内容の差を `compare.json` に分けて保存）。

**単局・バッチ・再生成:**

- 対象の 1 行に、同じ証拠で単局の入口（runner と同じ `submit_evidence` → `judge_normal`）を当てると、バッチの行と判定・理由が同じでした。
- 同じ入力から `derived-2/` に作り直すと、6 ファイルすべてがバイト単位で同じでした（非決定的な項目なし）。

### 9.4 言えること・言えないこと

**言えること:**

- 規則 10 は、保存例の 1 件を設計どおり known_stop と判定します。ほかの判定の内容は変えません。
- P2-min が new_game で未出現という結果（[P2-min の new_game 小規模確認バッチ](history/p2-min-batch-plan.md) 10 章）は変わりません。

**言えないこと・していないこと:**

- 元のバッチの終わり方・停止の方針・完了の状態は変えていません。新しい規則なら当時どう進んだかという、反実仮想の対戦の結果も推測していません。
- この派生評価は、`UNRESOLVED_RECOVER_ZERO_ENERGY` の未裁定（H4。「最大2枚」が 0 枚を含むか）そのものを解決したものではありません。エンジンは今も 0 枚の答えを止めます。
- ほかの旧バッチには当てていません。
