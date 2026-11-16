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
| 対象バッチ | vai-batch-p2n1（[P2-min の new_game 小規模確認バッチ](p2-min-batch-plan.md) 10 章） |
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
