# LOST_TARGET の P2・P3o（相手のうらのカードを指定する経路）の根拠条件の設計

2026-11-16。調査・設計・文書化だけです。判定の規則・エンジン・検証用 AI・GUI・basis・版・形式は変えていません。テスト・ビルド・対戦・judge・replay はしていません。旧記録は書き換えていません。

- 基点: `claude/vai-batch-tr3n1` の `4aa5c07`（origin と一致。main `b1e4430` の子孫で main に入っていない）。コードは配布の固定 `d562ec1` と差 0。エンジン 0.187.0・`TOOL_VERSION` 11・判定の規則 8・計画と完了の形式 7（識別を測って確かめた）。作業は worktree `C:\dev\kyuura-engine-lt48`・ブランチ `claude/lost-target-p2-p3o-design`。
- 前の設計: [P1（本人のうら・特殊能力）](verification-ai-lost-target-own-face-down-design.md)・[P3（決定への回答）](verification-ai-lost-target-p3-decision-design.md)。P1（規則 7）・P3s（規則 8）は確認済みの範囲として変えません。
- 証跡: `kyuura-engine-verification-vai/verifier/runs/lost-target-p2-p3o-design/`（条件と根拠の対応表 `out/conditions.json`）。

## 0. 結論

| 経路 | 結論 | 理由（要約） |
|---|---|---|
| **P2**（おもての使い手の特殊能力の source・target に、相手のうらを 1 匹だけ指定） | **A**（今の記録だけで、限定した known_stop の条件を登録できる） | エンジンは相手のうらを入口で `can_lose=False` で指定すると、ありうるカードの「たねでない」代表の試しで必ずこのコードを出す（本当のカードによらない）。経路の形は送信の記録と本人の観測（公開の値）だけで確かめられ、相手の `real` を使わない |
| **P3o**（決定への回答で相手のうらを指定） | **C**（今は undetermined を維持） | 決定の再開先・効果（`can_lose`）が記録にない。効果によって、たねの代表の試しが先に別のコードで拒否する（エネルギー・リムーブは `UNRESOLVED_KEEP_PROTECTED_TARGET`）。保存例も、P3o でこのコードになることを示すエンジンのテストもない。登録するなら B の追加（4 章）が要る |

推奨する最小の 1 経路: **P2 のうち「使い手がおもて・選んだ段は source・target（場のポケモン）だけ・指定したうらはちょうど 1 匹で相手の場・本人のうらを指定しない」**（P2-min）。energy の段・2 匹以上の相手のうら・本人のうらとの混在・P3o は入れません。

known_stop を増やすことを目的にしていません。P2-min の外は、今と同じ undetermined です。

## 1. 経路と情報の区別（静的に読んだ。行は 0.187.0）

### 1.1 P2: 特殊能力の宣言で相手のうらを指定

1. `engine._apply` → `_apply_checked`（`engine.py` 626 行）。
   - 送る主体の相手のうらが場にあると、`zones.IDENTITY_CONSULTED` を空にして 1 回処理を試します。
2. `_reveal_for_action`（1075 行）。
   - 使い手がおもてなら、`command.source`・`command.target` のうらのポケモンと、`command.energy` のついているポケモンを、`designate_face_down(by_player=送る主体, can_lose=False)` で指定します。handler（`check_use_pokemon_power` 以下）より前です。
3. `zones.designate_face_down`（138 行）。
   - 持ち主が送る主体でなければ、`IDENTITY_CONSULTED` に持ち主を加えます。
   - 本当のカードがたねでなく `can_lose=False` なら、状態を変える前に `UnsupportedError(UNSUPPORTED_SECRET_PLAN_LOST_TARGET)` を出します。
4. 記録があれば `_identity_independent`（802 行）。
   - 公開のカードの一覧（`_public_pool`。デッキ・手札を使わない）から、たね・ベイビィの代表ごとに試し、次に「たねでない」の代表 `_NONBASIC` を試します。
   - 最初に拒否した試しの種類とコードで拒否し、理由の文を「ありうるカードのどれかのとき…」に置きかえます。
   - `_NONBASIC` の試しは、入口の指定（`can_lose=False`）で必ずこのコードになります。そのため、たねの代表が別のコードで先に拒否しない限り、このコードになります。
   - どちらにしても結果は本当のカードによりません。既存のテスト `tests/test_secret_plan_v0_67.py` の `IdentityIndependenceTest.test_power_target_on_a_face_down_card_is_refused_for_every_identity` が、ゲンガーの［のろい］の移動先で、本当のカードがたねでもたねでなくても同じコード・同じ文になることを確かめています。

### 1.2 P3o: 決定への回答で相手のうらを指定

- `_answer_decision_once` → 再開先ごとに `_designate_answer`（1137 行）。
  - `can_lose` は効果の `ends_on_lost_target` が真で、指定が 1 匹のときだけ真です。
  - 特殊能力・スタジアム・反応の再開先は `effect=None` なので偽、ワザの途中（`resolution.RESUMES`）は `_designate_answer` を呼びません。
- 相手のうらを指定すると `_identity_independent` を通るので、結果は本当のカードによりません。ただし、出るコードは効果ごとに試しの順で決まります。
  - 突風（`ends_on_lost_target` 真）: たねでなければトラッシュして終わる（このコードにならない）。
  - エネルギー・リムーブ: ［KEEP］のたねの代表（481 回目）が `_NONBASIC`（548 回目）より先に拒否し、`UNRESOLVED_KEEP_PROTECTED_TARGET` になる（[v0.181](keep-designated-energy-removal-v0.181.md) 4 章）。
  - そのほかの効果: 調べていない。

### 1.3 受理の前と後・情報の区分・診断の宛先・記録

| 項目 | P2 | P3o |
|---|---|---|
| 到達 | `use_power`（使い手がおもて）の宣言の段 source・target・energy。候補の作成は、うらを指定する選べるものを `unverified`・`face_down_reveal_not_evaluated` にする（`legal_actions._power_verdict`）。boundary の方式などで方策が選びうる | `answer_decision`（相手の場のポケモン・カードを選べる決定）。決定を出す効果は場面による |
| 指定の時点 | 受理の判定の中（入口。handler より前） | 答えの処理の中（`_designate_answer`） |
| 受理の前に確かめる条件 | 公開の値（番・段階・使い手・宣言の段）と、ありうるカードのすべてでの試し | 同じく試し。ほかに決定の選べるもの |
| 受理の後に分かる条件 | なし（拒否は状態を変えない。番は続く） | なし（拒否は同じ決定を残す） |
| 公開・本人の情報 | 相手のうらは、本人の観測で `pokemon_id`・`face_down`・エネルギー・ダメージなどだけ（`observation._face_down_pokemon`。`real` は持ち主だけ）。選べるものは `pokemon`・`zone`・`face_down`（`_public_pokemon`。uid・カード ID なし） | 同じ（観測）。決定の観測に再開先・効果の型はない（`trainer_in_use` はトレーナーの再開先だけ） |
| エンジンだけの情報 | 相手のうらの本当のカード・試しの順と結果 | 同じ。加えて再開先・`effect`・`can_lose` |
| 受理が相手の秘密によらない仕組み | `_identity_independent`（公開の一覧で試す） | 同じ |
| 診断の宛先 | 送った本人に診断の結果（`DiagnosticResult`、role actor。コード・分類・公開の文）。ほかの見る人は状態の知らせだけ（拒否を持たない）。検証者の報告（元のコード・生の文）はホストだけ | 同じ |
| 保存記録 | trace の送信の行（候補・段・選んだ意味・submit。`verifier` は `category`・`diagnostic_id`・`engine_code` だけで、生の文は保存しない）・`actors/<主体>.jsonl`（本人の送信前の観測・試みの行）・完全な記録（検証者用。判定に使わない） | 同じ |

**judge が受け取れる証拠**（P2・P3o で同じ）:

| 区分 | 中身 | 判定への使い方 |
|---|---|---|
| 公開ログ | 拒否は公開の出来事を作らない | 使わない |
| 本人の観測 | 送信前の本人の view（runner の `actor_logs`。方策が受け取ったものと同じ） | 経路の形（持ち主・うら・番号）に使う。相手の `real` はない |
| 選んだ入力 | 候補・段・`meaning`・`choices` | 経路の形に使う |
| 診断 | 本人の結果と、検証者の 3 項目 | コード・分類・拒否のあとの形に使う |
| ほかの記録 | 完全な記録（両主体の秘密・command）・相手の観測・replay | **使わない**（検証者が読めることと、判定の根拠にしてよいことは別。P1・P3s と同じ境界） |

記録にない値（相手の本当のカード・再開先）を、後の公開・既知のデッキ・同名の別個体から補いません。

## 2. P2-min の条件（規則 9 の案。すべて満たしたときだけ根拠を返す）

送信の行 `entry`、同じ `trace`、`actor_logs`、記録の header、P2 用の basis（任意）から確かめます。満たさない最初の条件の id を返し、すべて満たせば None。返す値は条件の id だけで、場のポケモンの番号・uid・カード ID を持ちません。

| id | 条件 | P1 との関係 |
|---|---|---|
| Q1 | エンジンの拒否: `outcome` が `rejected`・`ok` 真・`refusal`・`error` が null | L1 と同じ |
| Q2 | コードと分類: 検証者の `engine_code`・`diagnostic_id`・公開の `diagnostic_id` が `UNSUPPORTED_SECRET_PLAN_LOST_TARGET`、分類が `unsupported` でコード表と同じ | L2 と同じ |
| Q3 | 拒否のあとも同じ主体の番: `status` `in_progress`・`continuable` 真・`next` が本人の `turn_action` だけ・`viewer` が主体・`halt` null・`refetch_required` 偽 | L3 と同じ |
| Q4 | 候補: `kind` が `use_power`。使い手（候補の `pokemon`）に文字列の `card_id` があり `face_down` が真でない。`power.face_down` が真でない。理由 `face_down_reveal_not_evaluated` が、候補か選んだ選べるものにある | L4 と同じ（P1u・ほかの種類を除く） |
| Q5 | 選んだ段: 1 つ以上で、すべて role が `source` か `target`、`meaning` が `pokemon`（**energy の段を選んだら外す**） | L5 より狭い |
| Q6 | 送信前の本人の観測がちょうど 1 つで、送信の時点と同じ（viewer・current_player が主体、phase main、決定なし、番が同じ、同じエピソードの前の送信に受理がない、場の行の形が正しい） | L6 と同じ |
| Q7 | 使い手が観測の主体の場にちょうど 1 つあり、うらでない | L7 と同じ |
| Q8 | 参照: 選んだ各 `pokemon` が観測の場の行（両主体）にちょうど 1 つ合い、選べるものの `face_down` と観測の `face_down` が同じ | L8 と同じ（pokemon の段だけ） |
| Q9 | 持ち主: 指定した場のポケモンのうち、うらは**ちょうど 1 つ**で、それは相手の場（観測の `players[1 − 主体]`）にある。本人のうらを指定していない | L9 の逆（相手のうらだけ） |
| Q10 | 情報の境界の整合: 指定した相手のうらの観測の行に `real` がない（ある記録は、観測の境界と矛盾するので外す） | 新しい |
| Q11 | 判定の基礎: (a) 実装の識別（`behavior_digest`）が記録と同じか、(b) 呼ぶ側が渡した P2 の basis が今の P2 の基礎の識別と同じ | L12・D12 と同じ型 |

- 相手の本当のカード（たねかどうか）の条件は**置きません**。エンジンの結果は本当のカードによらないからです（1.1）。P1 の L10・L11 を相手の側へ広げることはしません。
- 判定のたびに確かめない静的な前提（エンジンのテストで確かめる。3 章）:
  - S1: `_reveal_for_action` は source・target を `can_lose=False` で指定する。
  - S2: 相手のうらがある送信は `_apply_checked` → `_identity_independent` を通り、`_NONBASIC` の試しがある。
  - S3: 公開のカードの一覧に、たねでもベイビィでもないカードが 1 つ以上ある。
- 根拠の鍵は `UNSUPPORTED_SECRET_PLAN_LOST_TARGET#P2`（`code` が元のコード。P3 と同じ方式）です。
- 理由は `[unsupported, UNSUPPORTED_SECRET_PLAN_LOST_TARGET, face_down_reveal_not_evaluated, "evidence:" + P2 の条件の文]`（固定の文。番号・カードを書かない）です。

**満たさないとき**: 今と同じ undetermined（理由の先頭 `stop_condition_not_evidenced:<code>`）です。

- `undetermined_category` の分類 `evidence_missing_stop` と停止方針は変わりません。
- 規則 9 の失敗の id は判定の行に足さず、当て直しの記録にだけ残します。

**複数の経路の区別**:

- P1（L9: うらはすべて本人）と P2-min（Q9: うらは相手の 1 つだけ・本人のうらなし）と P3s（D4: `answer_decision`）は、同時には成り立ちません。
- 実装では 3 つの判定を順に呼び、根拠を返すものが 2 つ以上なら（起こらないはず）undetermined にします。

**対象外（undetermined のまま）**:

- energy の段を選んだ指定
- 相手のうら 2 匹以上（2 枚目の割り当てで `UNSUPPORTED_SECRET_PLAN_IDENTITIES` もありうる）
- 本人のうらとの混在
- うらの使い手（P1u）
- 受理の後の処理の中の指定（P4）
- P3o
- 別のコード（`UNSUPPORTED_SECRET_PLAN_IDENTITIES`・［KEEP］など）

## 3. 実装のときのテストの案（今回は追加・実行しない）

**エンジン側**（`tests/` に足すだけ。エンジンの動作・版は変えない）:

| id | 内容 |
|---|---|
| E-P2-1 | 既存の `test_power_target_on_a_face_down_card_is_refused_for_every_identity` に、ベイビィの本当のカードを足しても同じコード・同じ文（S2） |
| E-P2-2 | source の段で相手のうらを指定しても同じ（S1） |
| E-P2-3 | 拒否のあとの状態がバイトまで同じ・番が続く（Q3 の形） |
| E-P2-4 | 公開のカードの一覧に、たねでもベイビィでもないカードがある（S3） |

**judge 側**（正）:

| id | 内容 |
|---|---|
| J-P2-1 | 構築盤面（ゲンガーの［のろい］の移動先に相手のうら・たねでない本当のカード）を本物の runner に通すと known_stop、理由は固定の文 |
| J-P2-2 | 同じ盤面で相手の本当のカードだけをたね・ベイビィに変えても、同じ判定・同じ理由（判定は相手の正体を読まない） |
| J-P2-3 | 単局とバッチの入口で同じ判定。保存した `actors/*.jsonl` から読み直しても同じ |

**judge 側**（負。どれも undetermined。失敗の id を確かめる）:

| id | 内容 | 外れる条件 |
|---|---|---|
| J-P2-N1 | 本人の観測の行がない・2 つある | Q6 |
| J-P2-N2 | 同じエピソードの前の送信に受理がある（古い観測） | Q6 |
| J-P2-N3 | 本人のうらを指定（P1 の行） | Q9（規則 7 が扱う） |
| J-P2-N4 | 本人のうらと相手のうらの混在 | Q9 |
| J-P2-N5 | 相手のうら 2 匹 | Q9 |
| J-P2-N6 | energy の段を選んだ | Q5 |
| J-P2-N7 | `answer_decision`（P3o）・`play_trainer`（P4）の同じコード | Q4 |
| J-P2-N8 | うらの使い手（P1u） | Q4 |
| J-P2-N9 | 選べるものは `face_down` 真なのに観測の行がおもて（状態の矛盾） | Q8 |
| J-P2-N10 | 相手のうらの観測の行に `real` がある（境界の矛盾） | Q10 |
| J-P2-N11 | コードが `UNSUPPORTED_SECRET_PLAN_IDENTITIES`・`UNRESOLVED_KEEP_PROTECTED_TARGET` | Q2 |
| J-P2-N12 | 拒否のあとの `status` が `in_progress` でない | Q3 |
| J-P2-N13 | basis が違う（許可リストで通さない） | Q11 |
| J-P2-N14 | ホストの断り・failed | Q1（既存の suspect などのまま） |

## 4. P3o を登録するなら（B。今回は設計だけ）

**要る追加**:

1. **検証者用の決定の文脈**: 回答の時点の決定の再開先の分類（trainer・power・stadium・reaction・resolution）と、効果の `implementation_id`・`ends_on_lost_target`。
   - 取得元: エンジンの決定（`decision.resume`・`entry.effect`）。
   - 保存先: 検証者の報告（ホストだけ）か trace の検証者の項目。方策・API・観測へは渡しません。
   - 秘密への影響: 再開先と効果の型は、使ったカード（公開）から決まるので、新しい秘密は出ません。ただし観測・公開の結果には足しません。
   - 識別・形式への影響: エンジンの検証者の報告の項目が増える（エンジンの版が上がる）。検証用 AI の記録の項目が増える（`TOOL_VERSION`・完了の形式が変わる）。
2. **効果ごとのエンジンのテスト**: 相手のうらを答えたときに出るコードが、試しの順で `UNSUPPORTED_SECRET_PLAN_LOST_TARGET` になる効果を決める。エネルギー・リムーブのように別のコードになる効果は登録しません。
3. **保存例**: new_game で P3o が出た記録（今は見つかっていない）。

これらがそろうまで、P3o は undetermined のままにします。

## 5. 既存記録と互換性

**当時の記録で確認できる事実**:

- P2・P3o の保存例は、既存の文書には見つかりませんでした。
  - [棚卸し](verification-ai-coverage-inventory-next-batch.md)・状態台帳では「対戦で未出現」です。
  - その後の x1・TR3 確認バッチのこのコードの拒否 4 件は、どれも P1（規則 7 で known_stop）で、undetermined は 0 でした。
- 本人の観測の形は、TR3 確認バッチの 1 局で確かめました（相手のうらは `pokemon_id`・`face_down`・ダメージなどだけで `real` なし。対戦準備の番 0 は `{"face_down": true}` だけ）。全バッチは走査していません。

**今のコードから静的に確かめた事実**: 1 章のすべて（実行していない）。

**新しい条件を旧記録に当てられるか**:

- 保存例がないので、当て直しの対象はありません。
- 将来の記録に当てるときは、Q11 の basis で判定の基礎の同じを確かめます。旧記録の basis の違いを例外にしたり、許可リストで通したりしません。

**P2 用 basis の案**:

- 方式 `kyuura-lost-target-p2-basis-sha256/1`。
- ファイル `cards.py`・`data/kyuura_cards.json`・`effects.py`・`engine.py`・`zones.py`・`observation.py`（入口の指定・ありうるカードの試し・公開の一覧・観測の相手のうらの形）。
- P1・P3 の basis は変えません。

## 6. 判定の規則・版・形式への想定の影響（実装したとき）

| 項目 | 今 | 実装のあと（想定） |
|---|---|---|
| エンジン | 0.187.0 | 変えない（テストを足すだけ。版は上げない） |
| 判定の規則 | 8 | 9（P2-min） |
| `TOOL_VERSION`・道具の識別 | 11・`6e0616cc…` | 12・変わる（`TOOL_VERSION` 11 の計画は再開しない） |
| 計画・完了の形式 | 7・7 | 変えない（記録の項目は増えない） |
| P1・P3 の basis | `2ed8732f…`・`9499db41…` | 同じ |
| P2 の basis | なし | 新しい（5 章） |

## 7. 次の最小の単位

1. P2-min の実装（エンジン側のテスト E-P2-1〜4 → judge の規則 9・`TOOL_VERSION` 12 → judge の正負のテスト → 構築盤面での単局とバッチの一致）。
2. 実装のあとに、P2 が出うる条件（boundary の方式・相手の場にマチスの秘策のうら・相手を指定する特殊能力のあるデッキ）の小規模バッチを計画する（別の単位）。
3. P3o は、B の追加を採るかを利用者が決めたあとの単位です。

## 8. 失敗・未確認

- 失敗: なし（読み取りだけ）。
- 未確認:
  - P2・P3o の new_game での出現
  - P3o でこのコードになる効果の一覧（エネルギー・リムーブ以外を調べていない）
  - 相手を指定する特殊能力の一覧（ゲンガーの［のろい］以外の具体の型を調べていない。条件はカードではなく段の role で決める）
  - energy の段・2 匹以上の指定の試しの回数

## 9. 実装の結果（2026-11-16。判定の規則 9・`TOOL_VERSION` 12。P2-min をゲンガーの［のろい］に限定）

- 基点は `claude/lost-target-p2-p3o-design` の `b585d0d` です（origin と一致。main `b1e4430` の子孫で main に入っていない。コードは配布の固定 `d562ec1` と差 0）。
- 作業は worktree `C:\dev\kyuura-engine-lt49`・ブランチ `claude/lost-target-p2-min` です。
- コミット:
  - `d698cbb`: エンジンの前提テストだけ
  - `b780981`: judge の規則 9・`TOOL_VERSION` 12・正負のテスト・版の期待
  - この文書のコミット
- 証跡: `kyuura-engine-verification-vai/verifier/runs/lost-target-p2-min-impl/`

**登録したのは P2 の全体ではなく、確かめた限定の経路だけです。** P3o は未登録です。確認は構築盤面だけで、new_game からの到達の実績ではありません。旧記録への判定の当て直しはしていません（P2 の保存例は、調べた範囲では見つかっていない。5 章）。

### 9.1 初回の効果の限定（Q12）と、その根拠

**対象の実装:**

- 効果の型 `effects.MoveOpponentDamageCounter`（`implementation_id` `move_opponent_damage_counter`）だけです。
- エンジンの登録でこの型を持つ力は、［のろい］（`PMCG3-031` の 0 番目）の 1 つだけでした（テストで登録表から数えた）。
- 宣言の段は source・target で、どちらも相手の場のポケモンです。
- 判定は、カード ID・名前の文字列ではなく、候補の力（`power.card_id`・`index`）からエンジンの登録（`DEFAULT_EFFECTS.power_entry`）を引き、効果の型で照らします。
- 写した力は外します。候補の力のカードが、使い手のカードと同じことを求めます。

**source を外す理由**（実装を照らして分かったこと。設計の P2-min より狭い）:

- 入口の指定は source → target の順で、どちらも handler の `check_usable` より前です。
- source に相手のうらを指定すると、たねの代表の試しは、おもてにしたあと `check_usable` の `NO_DAMAGE_COUNTERS`（うらのあいだはダメージ 0）で先に拒否します。結果はこのコードになりません（本当のカードによらない）。
- そのため、P2-min は「**target が相手のうら・source は相手のおもて**」に限ります（Q9）。

**S1〜S3 と、実装の照合**（`tests/test_lost_target_p2_min_v0_187.py`。8 テスト。エンジンは変えていない）:

| 確かめたこと | 結果 |
|---|---|
| 登録 | 型 `MoveOpponentDamageCounter` は［のろい］だけ。段は source・target（相手の場のポケモン） |
| S2・相手の正体によらない | target に相手のうらを指定すると、本当のカードがたね・ベイビィ・1 進化・エネルギー 2 種・トレーナーのどれでも、同じコード・同じ文で拒否（文は「ありうるカードのどれかのとき」の形。判定には使わない）。状態（形式 22 の写し）・乱数・ログの長さ・決定・次の決定の番号は変わらない |
| 受理が相手の real によらない | ありうるカードの確かめを外す（テストだけの置きかえ）と、たねの本当のカードは受け付ける。本物の経路は拒否する |
| source の指定 | 本当のカードによらず `NO_DAMAGE_COUNTERS`（このコードにならない） |
| S1 | 入口の指定は 1 回だけで、`(持ち主 0, cause power, can_lose False)` |
| S3 | 公開のカードの一覧（`_public_pool` の代表）に、たねでもベイビィでもないカードがある |
| 公開の入口 | `adapter.submit` で、本人への診断（コード・分類 `unsupported`・`in_progress`・`next` は本人の `turn_action`・`continuable`）・相手と観戦者への知らせ・検証者のコードが、本当のカードによらず同じ |
| 観測と入力 | 本人の観測の相手のうらの行は `pokemon_id`・`face_down` だけで `real` がない。候補 `use_power`（使い手はおもてのゲンガー・力は写した力でない）の target の段に同じ番号の選べるものがあり、`face_down` 真・`card`・`card_id` なし・理由 `face_down_reveal_not_evaluated` |

テストの中で内部の値（`state.cards` の本当のカード・`designate_face_down` の呼び出し）を読んだのは、盤面の準備と前提の確かめだけです。判定の根拠（本人の観測・選んだ入力・診断）とは別にしました。既存の動作の問題は見つかりませんでした。

### 9.2 judge の規則 9

- `judge.opponent_face_down_lost_target_failure` が、次の順で確かめます。
  - Q1（拒否）・Q2（コードと分類）・Q3（拒否のあとも同じ主体の番・`refetch_required` 偽）
  - Q4（おもての使い手の `use_power`・理由 `face_down_reveal_not_evaluated`）・**Q12（効果の限定）**
  - Q5（選んだ段は source・target がちょうど 1 つずつ。energy・ほかの段を外す）・Q6（送信前の本人の観測がちょうど 1 つで同じ時点・前に受理がない）
  - Q7（使い手）・Q8（参照・`face_down` の一致）・Q9（target は相手のうら・source は相手のおもて）・Q10（相手のうらの行に `real` がない）・Q11（P2 用 basis）
- 満たさない最初の条件の id を返し、すべて満たせば根拠の鍵 `UNSUPPORTED_SECRET_PLAN_LOST_TARGET#P2`（`code` は元のコード）です。
- 理由は `[unsupported, <code>, <候補と選んだ選べるものの説明の理由>, "evidence:" + 固定の条件の文]` です。
- 使わないもの: 相手の `real`、相手の観測（相手の主体の記録の値を変えても判定は同じことをテストした）、完全な記録、replay、後の公開、既知のデッキ、選ばなかった選べるもの、診断の生の文。
- `submit_evidence`（単局の runner とバッチの共通の入口）:
  - ER9 を先に見るのは今までと同じです。
  - 次に P1・P2・P3s を確かめ、根拠を返すものが**ちょうど 1 つ**のときだけその鍵を返します。2 つ以上は矛盾として None です。
  - 条件は互いに重ならないので、既存の記録の判定は変わりません（P1・P3s のテストは版の期待のほか変えずに成功）。
- 満たさないときは今と同じ undetermined（`stop_condition_not_evidenced:<code>`）で、分類 `evidence_missing_stop` と停止方針も同じです。

### 9.3 P2 用 basis（Q11）

- 方式 `kyuura-lost-target-p2-basis-sha256/1`。
- ファイルは `cards.py`・`data/kyuura_cards.json`・`effects.py`・`engine.py`・`zones.py`・`observation.py`・**`state.py`** です。
  - `state.py` は、設計の 6 ファイルに実装のときに足しました。入口の指定が「うらか」を決める値（`is_face_down`・`find_pokemon`）が S1 の前提に入るためです。
  - 対象を減らしたり、旧 basis の違いを許可リストで通したりはしていません。
- 今の値は `720f4641…` です。P1（`2ed8732f…`）・P3（`9499db41…`）は変えていません。
- P1・P3 の basis を渡しても Q11 は通りません（テストで確かめた）。

### 9.4 テスト

| 段階 | 結果 |
|---|---|
| エンジンの前提（8） | 1 回目は 1 誤り（テストの側: 観戦者への知らせが None の場合）→ 直して 8 成功 |
| judge の新しいテスト（18）の修正の前 | 3 失敗・39 誤り（どれも規則 9 の関数・版がまだないため） |
| 実装のあと | 1 回目は 4 失敗（どれもテストの組み立て: P1 の形を規則 7 が正しく known_stop にした・確かめたい条件より前の条件で外れた）→ 直して 18 成功 |
| 関連（25 モジュール。対象と理由は証跡の `out/related_tests_plan.md`） | すべて成功（固定の指紋 `test_verification_ai_v2_repeat` をふくむ。期待は変えていない） |
| basis に `state.py` を足したあと | 規則 9・P1・P3・バッチ・固定の指紋を再実行して成功 |
| コミット `b780981` で 25 モジュールをもう一度 | 24 成功・1 失敗。失敗は `tests.test_verification_ai_prestop` の `test_row_too_big_after_request_is_not_written_and_stops_requests` で、記録の行の所要時間（実際の時計・小数 6 桁）の文字列の長さが、試しの行と本番の行で違うと上限の 1 バイトの差が崩れる、時間に依存する既存の不安定さ。prestop のコードとテストは基点と差 0。同じモジュールを別のプロセスで 3 回実行してすべて成功。テストは直していない（今回の範囲の外。報告だけ） |

版の期待を更新したのは、判定の規則と `TOOL_VERSION` を読む 10 モジュールだけです（旧の期待は注記に残した）。

### 9.5 構築盤面での単局とバッチ

- 盤面は `curse_board`（プレイヤー 0 のうら、プレイヤー 1 のゲンガー、source はダメージ 10 のエビワラー）です。
- 本物の runner（`FixtureRunner`。boundary・操作 1）に通し、相手の正体の 5 区分（たね・ベイビィ・1 進化・エネルギー・トレーナー）で比べました。
  - バッチの入口（`batch.judge_trace`）と単局の判定（変異の実行の中）が、5 区分とも同じ known_stop で、判定の行も 5 区分で同じでした。
  - 保存の形（trace・actors の JSONL・record の header）に書き、読み直して判定しても同じです。
  - 本人の観測の相手の行に `real` はありません。P1 の規則は L9 で外れます。
- 最終のコードで作り直した証拠は、判定の行が同じでした。保存したファイルの違いは、ホストのランダムな取っ手（`game`・`revision`）だけです。
- runner の通常の対戦・new_game からの到達はしていません。

### 9.6 識別

| 項目 | 前（`b585d0d`） | 後（`b780981`） |
|---|---|---|
| エンジンの版・behavior・instrumentation | 0.187.0・`ae974fff…`・`13c773a8…` | 同じ |
| P1・P3 の basis | `2ed8732f…`・`9499db41…` | 同じ |
| P2 の basis | なし | `720f4641…`（7 ファイル） |
| 判定の規則 | 8 | 9 |
| `TOOL_VERSION`・道具の識別 | 11・`6e0616cc…` | 12・`8cfa17bb…` |
| 計画・完了の形式 | 7・7 | 同じ |

`TOOL_VERSION` 11 の計画は、道具の識別の違いで再開しません。既存の識別の検査のままで、回避の処理は足していません。

### 9.7 未確認と次の単位

- **未確認:**
  - new_game からの P2-min の到達（ゲンガーと相手のマチスの秘策のうらが同時にある局・方策が target にうらを選ぶ）
  - ［のろい］のほかの力の型
  - P3o
  - 旧記録（保存例が見つかっていない）
  - 全体のテスト
- **new_game での確認へ進む最小の次の単位:** P2-min が出うる条件の小規模確認バッチの計画（計画だけ）です。
  - 片方のデッキにゲンガー（と進化の元）、もう片方にマチスの秘策が要ります。今の L67-U どうしでは、ゲンガーがないので出ません。
  - boundary の方式（候補が `unverified` の力も範囲に入る）が要ります。
  - 出現を保証しないこと、デッキの選定の根拠、P2-min の出現（直接）・undetermined・判定の行の集計を受け入れ条件にします。
