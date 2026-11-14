# LOST_TARGET の P3（決定への回答でうらのカードを指定する経路）の根拠登録の設計

2026-11-14。調査・設計・文書化だけ。エンジン・judge・runner の実装、テスト、判定の当て直し、新しい対戦、replay の再実行はしていない。
`kyuura_engine`・`tools.verification_ai` の import、テスト、judge の実行もしていない。読んだのはコード・文書・保存済みの JSON だけ。

P1（おもての特殊能力で本人のうらのカードを指定する経路）の設計と実装は [verification-ai-lost-target-own-face-down-design.md](verification-ai-lost-target-own-face-down-design.md)（以下「P1 文書」）。
この文書の条件 D1〜D12 は、P1 の L1〜L12 と同じ考え方で作り、P1 の条件・判定・理由は変えない。

## 1. 基点

| 項目 | 値（確かめた方法） |
|---|---|
| 基点 | `origin/claude/lost-target-p1-rejudge-s1` = `dd110a5`。未コミット 0。`origin/main` の祖先ではない（`merge-base --is-ancestor` が 1）。`dd110a5` を含むリモートのブランチはこれだけ |
| P1 の実装 | `38bf379`（judge の規則 7） |
| 作業 | worktree `C:\dev\kyuura-engine-lt4`、新しいブランチ `claude/lost-target-p3-design`（`dd110a5` から） |
| 識別（ソースの定数を読んだ） | エンジン 0.180.0（`kyuura_engine/__init__.py`）、`TOOL_VERSION` 9、`JUDGE_RULES_VERSION` 7、計画・完了の形式 6 |
| main | 取り込みは仮定しない。利用者の作業ツリー（main `7b3d53c`）は触っていない |

## 2. 対象の経路（静的に追った結果）

### 2.1 answer_decision からコードまで

1. `engine._apply`（入口）→ `_apply_checked`。
   - コマンドを出したプレイヤー（決定への答えは決めるプレイヤー。`_acting_player`）の相手のうらのカードが場にあるときだけ、`zones.IDENTITY_CONSULTED` を空にして処理を 1 回試す。
2. `_answer_decision` → `_answer_decision_once`。決定の再開先（`decision.resume`）で分かれる。

| 再開先 | うらの指定 | 拒否になるか |
|---|---|---|
| `reactions.RESUME`（反応の順番・使う機会など） | `_designate_answer(..., effect=None)` | `can_lose=False`。たねでないうらを指定すると拒否 |
| `resolution.RESUMES`（ワザの途中・きぜつ・サイド・バトル場に出す） | `_designate_answer` を呼ばない。ワザの要素は `resolution.kernel.designate`（`can_lose=True`） | このコードにならない（トラッシュして続ける） |
| `power`（特殊能力の決定） | `_designate_answer(..., None)` | `can_lose=False`。拒否 |
| `stadium` | `_designate_answer(..., None)` | `can_lose=False`。拒否 |
| `trainer`（文脈 `chaos`・`stadium_cost`・`trainer_reaction` のどれもない） | `_designate_answer(..., entry.effect)` | `can_lose` は `effect.ends_on_lost_target` が真で、指定が 1 つのときだけ真 |
| `trainer`（上の文脈のどれかがある） | `_designate_answer` を呼ばない | 決定の種類は `ACCEPT_REQUEST`（錯乱ジム）・`DISCARD_FROM_HAND`（リモーブ禁止ジム）など。そのあとの効果の処理（`zones.attach_trainer` など。`can_lose=False`）で指定がおこることはある |

3. `engine._designate_answer`（`engine.py`）。
   - 決定の種類の意味は `observation.OPTION_MEANINGS` から取る。
   - `pokemon` なら選んだ場のポケモン、`card` なら選んだカードがついている場のポケモンが指定になる。
   - うらのものごとに `zones.designate_face_down(..., by_player=decision.player, cause="effect", can_lose=...)` を呼ぶ。
4. `zones.designate_face_down`。
   - 本当のカードが「たねポケモン」（`_secret_plan_keeps` → `effects.card_is_basic_in_text(..., TEXT_PRE_NEO)`。ベイビィをふくむ）なら、おもてにして続ける。
   - たねでなく `can_lose=False` なら、状態を変える前に `UnsupportedError(UNSUPPORTED_SECRET_PLAN_LOST_TARGET)` を出す。
   - `by_player` が持ち主でなければ、`IDENTITY_CONSULTED` に持ち主を加える。
5. 拒否のあとの決定。
   - `apply_command` は渡した状態を変えない（`_apply_once` は複製で処理する）。
   - だから拒否のあとも同じ決定が残り、同じ主体が答え直せる。

### 2.2 本人のうらと相手のうら（下位経路の分け方）

| 下位経路 | 条件 | 拒否が本当のカードによるか |
|---|---|---|
| **P3s**（本人のうら） | 指定したうらの持ち主 = 決めるプレイヤー | よる。<br>`IDENTITY_CONSULTED` に加えないので、本当のカードの 1 回の処理で決まる（たね・ベイビィなら受理、たねでなければ拒否）。<br>決めるプレイヤーは自分のうらの本当のカードを知っている（観測の `real`） |
| **P3o**（相手のうら） | 指定したうらの持ち主 ≠ 決めるプレイヤー | よらない。<br>`IDENTITY_CONSULTED` に加わり、`_identity_independent` が公開のカードの一覧（`_public_pool`）から、たね・ベイビィの代表ごとと「たねでない」の代表（`_NONBASIC`）を試す。<br>`can_lose=False` なら `_NONBASIC` の試しが同じコードで拒否するので、本当のカードがたねでも同じコード・同じ文で拒否する |

- P2（特殊能力で相手のうらを指定）の調査で見た「本当のカードによらず同じコード」は、P3o には同じくある。P3s にはない（独立に確かめた）。
- P3o で、たねの代表の試しが先に別のコードで拒否すれば、そのコードになる（試す順はたね → `_NONBASIC`）。

### 2.3 同じコードになるほかの経路との違い

| 経路 | 候補の種類 | 指定の時点 | P3 との見分け |
|---|---|---|---|
| P1 | `use_power`（使い手がおもて） | 入口 `_reveal_for_action` | 候補の種類 |
| P2 | `use_power`（相手のうら） | 同上 | 候補の種類 |
| うらの使い手 | `use_power` などで使い手がうら | 入口でおもてにする（たねでなければトラッシュして受理） | 候補の種類。このコードにはならない |
| 受理の後の処理の中の指定 | `play_trainer`・ワザ・ほか | 手札から使う処理の中（`attach_trainer`・特殊エネルギーのつけたときの効果・反応の `movement.designate`） | 候補の種類が `answer_decision` でない |
| **P3** | `answer_decision` | 答えの処理（`_designate_answer`） | この文書の対象 |

- 決定への答えでも、答えの処理の続き（`_resume_trainer` の中の `attach_trainer`、反応の `movement.designate` など）で、選んだもの以外を指定して同じコードになる道は、コードの上ではありうる。
- これは選んだ参照と指定が一致しない形で、記録からは区別できない。登録の範囲に入れず、4.3 の条件で外す。

## 3. 保存済みの 1 件（vai-batch-r1）の対応

証跡 `verifier/runs/lost-target-p3-design/p3_r1_extract.json`（局の識別・参照の値はここにだけ置く）。

**直接の記録**（trace・`actors/<主体>.jsonl`・`judge.json`・`header.json`）

| 項目 | 記録の値 |
|---|---|
| 決定が出た操作 | 同じ主体の直前の受理。`play_trainer`、結果は `awaiting_decision`、`next` は本人の `answer_decision` |
| 決定待ちの観測 | 送信と同じ position・episode の行がちょうど 1 つ。<br>`phase` は `decision`、`current_player` は本人。<br>`decision` は種類 `select_pokemon`、意味 `pokemon`、最小・最大 1、選べるもの 2 つ（本人のバトル場とベンチの並びと同じ）。<br>`trainer_in_use` は本人が使い、本人が使う手札のトレーナー |
| 候補・段・選んだもの | 候補 `answer_decision`、理由は `continuation_not_evaluated` だけ（候補の側）。<br>段は 1 つで、`decision_kind` `select_pokemon`、`meaning` `pokemon`。<br>選べるものは `value` だけで、`face_down` の印はない。選んだのは 2 つ目 |
| 選んだ参照 | 観測の場にちょうど 1 つ。持ち主は本人、`face_down` は真、本人にだけ見える `real` がある |
| 本当のカード | `real` のカードはカードデータでポケモンでない（たねポケモンでない）。具体のカードは証跡だけに置く |
| 応答 | `rejected`、`ok` 真、ホストの断り・エラーなし。<br>検証者の診断・公開の結果・`case_id` がどれも `UNSUPPORTED_SECRET_PLAN_LOST_TARGET`。分類 `unsupported`。<br>`status` は `awaiting_decision`、`continuable` 真、`next` は本人の `answer_decision` だけ、`halt` なし、`refetch_required` 偽 |
| 拒否のあと | 同じエピソードの次の送信が、同じ候補・同じ段で 1 つ目を答えて受理（`in_progress`、本人の番へ） |
| 規則 6 の判定 | `undetermined`、理由 `stop_condition_not_evidenced:UNSUPPORTED_SECRET_PLAN_LOST_TARGET`、分類 `evidence_missing_stop` |
| 規則 7 の判定 | 同じ（P1 の L3 で外れる。P1 文書 14 章） |
| header | 記録のエンジン 0.179.0（`de81f642…`）。依存は既定のカードプール・カードデータ kyuura `71d1728…`・効果の登録 `kyuura-engine-0.13` |

**完全な記録での対応確認**（判定には使わない）

- 拒否した操作の command は `resolve_decision` で、決定の番号・プレイヤー・選択は trace の選んだ値と同じ。
- 次の受理の操作も同じ決定の番号に答えている。
- 直前の操作の command は `play_trainer` で、`check` の決定は同じ番号の `select_pokemon`。

**コード上の根拠**（記録ではなく、静的に読んだもの）

- 使ったトレーナーの登録は `effects.AttachedDamageReduction`（`implementation_id` `attached_damage_reduction`）。
  - `resolve` は本人の場のポケモン（バトル場 → ベンチ）を選べるものにした `select_pokemon` を `push_trainer_decision` で出す。再開先 `trainer`、文脈なし。
  - `ends_on_lost_target` は偽（既定）。
- この決定への答えは `_designate_answer(..., entry.effect)` に入り、`can_lose=False` で指定する。
- 決める人と持ち主が同じなので `IDENTITY_CONSULTED` に加わらない（P3s）。相手の場のうらがあっても試しの分岐に入らない。
- 選べるものは `decision_problems` が本人の場に限るので、この効果では P3o はおこらない。

**未確認**

- 決定の再開先・文脈は観測にも trace にもない（判定ではコード上の根拠と、4 章の D7・D8 の形の一致で補う）。
- new_game からの対戦で、規則 8 の判定が known_stop を出すこと。
- s1・r1 以外のバッチ。
- P3o・ほかの効果の型の実例。

**数**: s1・r1 で、このコードの送信は 3 件（s1 は `use_power` 2 件 = P1、r1 は `answer_decision` 1 件 = この P3s）。

## 4. 判定に必要な情報と、推奨する適用条件（規則 8 の案）

### 4.1 必要な情報と取得元

| 確かめること | 取得元 | 既存の記録で足りるか |
|---|---|---|
| 回答権（決めるのが本人） | 観測の `decision.player`・`current_player`、応答の `viewer` | 足りる |
| 該当の決定へ送った | 段の `decision_kind`・選べるものと、観測の `decision` の一致。拒否のあと `refetch_required` 偽（ホストが状態の変化なしと示す） | 足りる（決定の番号は完全な記録にだけあり、判定には要らない） |
| 選んだ参照が決定の選べるもの | `choices` の id → 段の選べるもの → `meaning` の `value` | 足りる |
| 参照の持ち主と face_down | 観測の場（`players[].active/bench` の `pokemon_id`・`face_down`） | 足りる（選べるものに `face_down` の印はない） |
| 本当のカードの条件 | 本人の観測の `real.card_id` と、エンジンのカードデータ・`card_is_basic_in_text`（P1 の L10 と同じ関数） | 足りる（P3s。本人が知っている値。相手の秘密は使わない） |
| 回答時点との対応 | `own_view_for`（P1 と同じ。position・episode が同じ行がちょうど 1 つ）、同じエピソードの前に受理がない | 足りる |
| 拒否のあとも同じ決定 | 応答の `status`・`next`・`continuable`・`halt`・`refetch_required` と、`apply_command` が渡した状態を変えないこと（コード） | 足りる |
| 効果が対象の消失を扱えない | 観測の `trainer_in_use.card_id` → エンジンの効果の登録の型と `ends_on_lost_target` | 足りる（判定の中でエンジンの登録を読む） |
| 記録時と判定時の同じ処理・データ | header の依存と実装の識別、または保存済みの記録の当て直しで渡す basis | 足りる |

- 記録の追加は要らない。
- 将来の拡張（ほかの再開先・P3o）で、再開先と文脈を区別したくなったときに限り、API の決定の観測へ再開先の分類を足す案を残す。今回は追加しない。
- 完全な記録は対応確認だけに使い、判定は依存しない（P1 と同じ情報の境界）。

### 4.2 条件 D1〜D12（すべて満たしたときだけ根拠を返す）

送信の行 `entry`、同じ `trace`、`actor_logs`、記録の header、P3 用の basis（任意）から確かめる。
満たさない最初の条件の id を返し、すべて満たせば None。返す値は条件の id だけで、場のポケモンの番号・uid・カード ID・本当のカードを持たない。

| id | 条件（どれか 1 つでも満たさなければ、その id） |
|---|---|
| D1 | エンジンの拒否。`outcome` が `rejected`、`ok` 真、`refusal`・`error` が null（P1 の L1 と同じ） |
| D2 | コードと分類。検証者の `engine_code`・`diagnostic_id`、公開の `diagnostic_id` が `UNSUPPORTED_SECRET_PLAN_LOST_TARGET`。分類はどちらも `unsupported` でコード表と同じ（L2 と同じ） |
| D3 | 拒否のあとも同じ主体の決定待ち。<br>`status` が `awaiting_decision`、`continuable` 真、`next` が `[{"kind": "answer_decision", "player": actor}]` だけ、`viewer` が actor、`halt` が null、`refetch_required` 偽 |
| D4 | 候補の `kind` が `answer_decision`。<br>理由 `continuation_not_evaluated` が、候補の `reasons` か、選んだ `meaning[].option.reasons` にある（段の未選択の選べるものは読まない） |
| D5 | 段の形。<br>段はちょうど 1 つ：番号 1、`input` は `choose_option`、`decision_kind` は `select_pokemon`、`meaning` は `pokemon`、`count` は最小 1・最大 1。<br>選べるものの `value` は整数で重なりがない。<br>`choices` はちょうど 1 つで、段の選べるものの id に一度だけある。<br>`meaning` はちょうど 1 つで、段 1 の `option.value` がその選べるものの `value` と同じ |
| D6 | 送信前の本人の観測（`own_view_for`）がちょうど 1 つで、送信の時点と同じ。<br>`ok` 真、`viewer` と観測の `viewer` が actor、`phase` が `decision`、`current_player` が actor。<br>`decision` は `player` が actor、`kind` が段の `decision_kind`、`meaning` が `pokemon`、最小・最大 1、選べるものの `value` の並びが段と同じ。<br>`turn_of(view)` が送信の `turn` と同じ。同じエピソードの前の送信に受理がない。場の値の形が正しい（`_field_rows`） |
| D7 | 使っているトレーナー。<br>観測の `trainer_in_use` があり、`player` と `user` が actor、`card_id` が文字列。<br>エンジンの効果の登録（`DEFAULT_EFFECTS.trainer_entry`）にあり、効果の `implementation_id` が登録の表 `LOST_TARGET_DECISION_EFFECTS`（今は `attached_damage_reduction` だけ）にあり、`ends_on_lost_target` が偽 |
| D8 | 決定の形が効果の `resolve` と同じ。選べるものの `value` の並びが、観測の本人の場（バトル場 → ベンチ）の `pokemon_id` の並びと同じ |
| D9 | 参照。<br>選んだ `value` が観測の場にちょうど 1 つあり、持ち主が actor（相手なら P3o なので外す）、`face_down` が真（おもてなら外す） |
| D10 | その行の `real.card_id` がカードプールにあり、`card_is_basic_in_text(definition, TEXT_PRE_NEO)` が真か偽に決まる（L10 と同じ関数。複製しない） |
| D11 | たねポケモンでない（偽）。真（たね・ベイビィ）なら、エンジンはおもてにして続けるはずなので根拠の矛盾として外す |
| D12 | 判定の基礎が記録と同じ。<br>header の依存が既定のカードプール・今のカードデータ、効果の登録の id が今の `DEFAULT_EFFECTS.id`。<br>さらに、(a) 実装の識別（`behavior_digest`）が今と同じか、(b) 呼ぶ側が渡した P3 の basis が今の P3 の基礎の識別と同じ |

**根拠の値**: すべて満たせば `LOST_TARGET_P3_EVIDENCE`（5.1）を返す。
その場合、`judge_normal` は known_stop と次の理由を返す。

`[unsupported, UNSUPPORTED_SECRET_PLAN_LOST_TARGET, continuation_not_evaluated, "evidence:" + P3 の条件の文]`

`continuation_not_evaluated` は `_known_stop_or_undetermined` の `EXPLAINING_REASONS` で、候補と選んだ選べるものから集める（今の範囲のまま）。

### 4.3 P1 や他の経路を誤って拾わない

- P1・P2・うらの使い手は D4（候補の種類）で外れる。P3 の行は P1 の L3・L4 で外れる。両方の条件を同時に満たす行はない。
- 受理の後の処理の中の指定（`play_trainer` などの拒否）は D4 で外れる。
- `resolution.RESUMES` の決定（ワザの途中など）は D7（`trainer_in_use` がない・型が表にない）と D5・D8 の形で外れる。
- 反応・特殊能力・スタジアムの決定、文脈のあるトレーナーの決定（錯乱ジムの `ACCEPT_REQUEST`、リモーブ禁止ジムの `DISCARD_FROM_HAND` など）は、D5（種類）・D7・D8 のどれかで外れる。
- 答えの続きの中で、選んだもの以外を指定した形は D8・D9 で外れる。
  - D8 は、選べるものが本人の場の全体で効果の `resolve` が出す形であることを求める。
  - D9 は、選んだものが本人のうらであることを求める。
- 相手のうら（P3o）は D9 で外れる。

## 5. 登録方式と互換性

### 5.1 比べた案

| 案 | 中身 | P1 への影響 | 評価 |
|---|---|---|---|
| A. コード単位の入口のまま、P3 の項目を別の鍵で 1 つ足す（推奨） | `KNOWN_STOP_EVIDENCE` に `"UNSUPPORTED_SECRET_PLAN_LOST_TARGET#P3"` を足す（`code`: 元のコード、`condition`: P3 の文、`source`）。<br>`submit_evidence` は ER9 → P1 → P3 の順に明示的に呼ぶ。<br>`_known_stop_or_undetermined` は根拠の項目の `code`（なければ鍵そのもの）が元のコードと同じときだけ known_stop にし、理由にはその項目の `condition` を使う | なし。P1 の鍵・項目・根拠の値・理由の文は同じ | 足すのは 1 項目と、照合の 1 行。既存の項目では、照合は今と同じ式になる |
| B. コード単位の項目の中で経路ごとに分ける | `KNOWN_STOP_EVIDENCE[CODE]` に `paths: {P1, P3}` を持たせる | 項目の形が変わる。P1 のテストが `KNOWN_STOP_EVIDENCE[CODE]["condition"]` を理由の期待値に使っているので、P1 の理由かテストが変わる | 受け入れ条件（P1 の理由を維持）に反する |
| C. 経路単位の登録へ全部を変える | すべての項目を経路の鍵に置きかえる | DU1・ER9・P1 の鍵が変わる | 今必要な範囲を超える汎用化。採らない |

- A の照合の式は次のとおり。今の `code not in KNOWN_STOP_EVIDENCE or evidence != code` と、既存の 3 項目では同じ結果になる。
  - `entry = KNOWN_STOP_EVIDENCE.get(evidence)`
  - `entry is None or entry.get("code", evidence) != code` なら undetermined（理由の先頭は今と同じ `stop_condition_not_evidenced:<code>`）
- `RECORDED_STOP_CONDITIONS` の鍵が `KNOWN_STOP_EVIDENCE` の鍵にふくまれるという既存のテストは、そのまま通る。

### 5.2 judge のインターフェース（実装の段階の案）

- **追加の定数**
  - `LOST_TARGET_P3_EVIDENCE = "UNSUPPORTED_SECRET_PLAN_LOST_TARGET#P3"`
  - `LOST_TARGET_DECISION_EFFECTS = frozenset({"attached_damage_reduction"})`
  - `LOST_TARGET_P3_CONDITIONS = ("D1", …, "D12")`
  - `LOST_TARGET_P3_BASIS_METHOD = "kyuura-lost-target-p3-basis-sha256/1"`
  - `LOST_TARGET_P3_BASIS_FILES`（5.4）
- **追加の関数**
  - `decision_lost_target_failure(entry, *, trace, actor_logs, header, basis_p3=None) -> str | None`（D1〜D12）
  - `own_face_down_decision_lost_target_evidence(...)`（満たせば `LOST_TARGET_P3_EVIDENCE`）
  - `lost_target_p3_basis(root=None)`（`lost_target_basis` と同じ正規化・要約の方式で、ファイルの組だけが違う）
- **共通の入口**: `submit_evidence(entry, *, trace, actor_logs, header, basis=None, basis_p3=None)`。順番は次のとおり。
  1. `recorded_stop_evidence`（ER9）
  2. `own_face_down_lost_target_evidence`（P1。`basis` だけを使う）
  3. `own_face_down_decision_lost_target_evidence`（P3。`basis_p3` だけを使う）
  - P1 の関数・引数・L1〜L12 は変えない。
- **部品の共有**: `own_view_for`・`_field_rows`・`_header_value`・カードプールとたねの判定の呼び方は P1 と同じものを使う（複製しない）。
  - D12 の依存の確かめは、P1 の `_basis_matches` の依存の部分を関数に分けて共有してよい。ただし P1 の L12 の結果は変えない。

### 5.3 単局・バッチ・runner・記録形式

- **単局の runner**: 変更なし。今の `submit_evidence(entry, trace=self.trace, actor_logs=self.actor_logs, header=self._record_header)` のまま。
  - 実行中の記録は今のエンジンが作るので、D12 は (a) で決まる。
- **バッチ**: `batch.judge_trace(result, *, basis=None, basis_p3=None)` に引数を 1 つ足し、そのまま `submit_evidence` に渡す。
  - 保存済みの記録の当て直しだけが渡す。
- **記録・計画・完了の形式**: 変えない（6 のまま）。trace・`actors`・header に追加する値はない。
- 情報の境界は P1 と同じ。判定は送信の行・trace・本人の観測・header・エンジンのカードデータと効果の登録だけを読む。完全な記録・相手の観測・replay は読まない。

### 5.4 basis のファイル（P3 の呼び出し経路から）

P3 の判定が依存するエンジンの処理と、そのファイル。

| ファイル | 依存する処理 |
|---|---|
| `engine.py` | `_answer_decision_once`・`_designate_answer`・`_apply_checked` |
| `zones.py` | `designate_face_down`・`_secret_plan_keeps` |
| `effects.py` | `AttachedDamageReduction` の `resolve`・`ends_on_lost_target`・`DEFAULT_EFFECTS`・`card_is_basic_in_text` |
| `cards.py`・`data/kyuura_cards.json` | カードの定義 |
| `decisions.py` | `push_trainer_decision`（再開先 `trainer`、文脈なし） |
| `observation.py` | `OPTION_MEANINGS`（`_designate_answer` が決定の種類から指定を作る）と、観測の `real`・`trainer_in_use`・`decision` |

- P1 の 5 ファイルでは、`decisions.py` と `observation.py` の経路が足りない。
- 推奨: P3 の basis は 7 ファイル（P1 の 5 ＋ `decisions.py`・`observation.py`）を別の方式の名前で要約する。P1 の `LOST_TARGET_BASIS_FILES`・方式・L12 は変えない（s1 の当て直しの照合をそのまま保つ）。
- 静的な確認（git の blob の比べだけ。正規化の要約は計算していない）:
  - r1 を記録したコミット `de81f642…` と `dd110a5` で、7 ファイルとも同じ blob（`checks.py`・`reactions.py`・`state.py` も同じ）。
  - 差は `__init__.py` と `legal_actions.py` だけ。
  - 当て直しで basis は一致する見込み（実装の段階で `lost_target_p3_basis` で確かめる）。

### 5.5 版・識別・旧記録

| 項目 | 推奨 |
|---|---|
| 判定の規則 | `JUDGE_RULES_VERSION` 7 → 8（送信の行の判定が変わる） |
| `TOOL_VERSION` | 9 → 10（judge が道具の識別にふくまれ、要約が変わる。9 の計画は道具の識別の違いで再開しない。8 → 9 と同じ扱い） |
| 計画・完了の形式 | 6 のまま |
| エンジン | 0.180.0 のまま。エンジン側はテストを足すだけで、動作・裁定・識別を変えない |
| 旧計画・保存済みの記録 | 書きかえない。当て直しは別の証跡に新しい判定を書く（P1 文書 14 章と同じ方法） |

## 6. テストと当て直しの計画（受け入れ条件の案。今回は実行していない）

### 6.1 段階

| 段階 | 中身 | 受け入れ条件 |
|---|---|---|
| S1 エンジンの根拠テスト（版は上げない） | E7〜E12（6.2） | エンジンの動作を変えずに通る |
| S2 judge の規則 8 | D1〜D12、登録 A、`submit_evidence`・`batch.judge_trace` の引数、正負のテスト（6.3）、既存テストの版の期待値の更新（判定の中身の期待値は変えない） | P1 の正負テスト 31 件が理由の期待値ごと変わらずに通る |
| S3 保存済みの記録への当て直し（別の単位） | s1・r1 に規則 8 を当てる（6.4） | 6.4 の条件 |

各段階は別のコミット・別の報告にする。fixture・人工の入力は new_game からの到達の実績に数えない。

### 6.2 エンジン側（E7〜E12。`tests/` に足すだけ）

| id | 場面 | 期待 |
|---|---|---|
| E7 | ディフェンダー系の効果（`AttachedDamageReduction`）の決定で、本人のたねでないうら（トレーナー・エネルギー・進化カード）を答える | `UNSUPPORTED_SECRET_PLAN_LOST_TARGET`。状態・乱数・ログ・決定・相手と観戦者の観測が変わらない。同じ決定に答え直せる |
| E8 | 同じ決定で、本人のたね・ベイビィのうら | おもてにしてつける（受理）。ベイビィも残る |
| E9 | 同じ決定で、おもてのポケモン | 受理。うらの指定はない |
| E10 | 相手の場にうらがあり、本人のたねでないうらを答える | E7 と同じコード。`IDENTITY_CONSULTED` の試しに入らない（本人のうらだけの指定） |
| E11 | 対照: `ends_on_lost_target` が真の入れ替えの効果で、本人のたねでないうら | 受理してトラッシュ（このコードにならない） |
| E12 | 対照: 相手のうらを答えに選べる効果がある場合（P3o。テストでの到達ができる効果があるときだけ） | 本当のカードによらず同じコード・同じ文（既存の `IdentityIndependenceTest` と同じ確かめ方） |

E12 は P3o の性質の記録で、登録はしない。

2026-11-14 の追記: E12 をエネルギー・リムーブで組むと、期待した LOST_TARGET ではなく内部の `RuntimeError` になった。
- 原因は、［KEEP］を持つたねを指定でおもてにしたときの確かめの漏れ（エンジンの不具合）。
- E12 の期待値は直し方で変わる（未確定）。
- P3s（E7〜E11・D1〜D12）には影響しない。
- 詳細は [E12 の調査](verification-ai-e12-energy-removal-keep-investigation.md)。
- 0.181.0 で直した（[v0.181 の修正](keep-designated-energy-removal-v0.181.md)）。
  - E12 の期待値は、元の「どの本当のカードでも `UNSUPPORTED_SECRET_PLAN_LOST_TARGET`」から「どの本当のカードでも `UNRESOLVED_KEEP_PROTECTED_TARGET`」に変わる。
  - 理由は、置きかえの試しの順で［KEEP］のたねが `_NONBASIC` より先に拒否するため。本当のカードによらないという性質は同じ。
  - P3s を再開するときの基点・basis の注意は、同じ文書の 9 章。

### 6.3 judge 側の正負テスト

- **正（保存済み P3 の形の fixture）**: 1 件が D1〜D12 を満たし、known_stop になる。
  - 理由の期待値は 4.2 の 4 項目。
  - 単局の入口（runner の変異の実行の中の判定）とバッチの入口（`batch.judge_trace`）が、同じ送信・同じ trace・同じ観測・同じ header で同じ根拠・同じ判定になる。
- **負（すべて undetermined。理由の先頭 `stop_condition_not_evidenced:` と分類 `evidence_missing_stop` が変わらない）**

| 対象 | 期待する条件 |
|---|---|
| 相手のうらを選んだ（P3o） | D9 |
| おもての対象・うらの指定なし | D9 |
| 本当のカードがたね・ベイビィ（根拠の矛盾） | D11 |
| たね・非たね・ベイビィごとの対照（エンジンと同じ答え） | D10・D11 で、エンジンの `card_is_basic_in_text` と同じ答え（P1 の J9 と同じ確かめ方） |
| 別の決定の種類（`select_pokemon` 以外・`meaning` が `card`） | D5 |
| 段が 2 つ・選んだものが 2 つ・`choices` と `meaning` の不一致 | D5 |
| 別の回答者（`decision.player`・`current_player` が別） | D6 |
| 観測の欠け・重複・古さ（同じエピソードの前に受理）・別の番 | D6 |
| 観測の決定と段の不一致 | D6 |
| `trainer_in_use` がない・別の主体・登録の表にない効果の型・`ends_on_lost_target` が真 | D7 |
| 選べるものが本人の場の並びと違う | D8 |
| 参照が場にない・2 つある | D9 |
| 未選択の選べるものにだけ `continuation_not_evaluated` がある | D4 |
| 候補の種類が `use_power`・`play_trainer` | D4 |
| basis の欠け（実装の識別が違い、basis なし）・不一致・カードプールやカードデータや効果の登録の id が違う | D12 |
| 別のコード | D2 |
| `refused`・`failed`・通常の受理・通常の拒否 | 今の判定のまま（D1 で外れ、`judge_normal` の結果も規則 7 と同じ） |
| 拒否のあと決定待ちでない（`in_progress`・`halt`・`refetch_required` 真） | D3 |

- **P1 の不変**: P1 の 2 件の形は P1 の根拠で known_stop のまま、P3 の関数では D4 で外れる。P3 の形は P1 の関数で L3 のまま。既存の ER9・DU1 の判定も同じ。
- **秘密の混入なし**: 判定の理由・行・集計・公開の要約に、場のポケモンの番号・uid・カード ID・本当のカード・選んだ値が入らない（D の id と条件の文だけ）。
- **境界**: 方策・行動生成・変異・集計・記録の部品が P3 の部品を使わない。runner の `submit_evidence(` の呼び出しは 1 つのまま。

### 6.4 当て直しの受け入れ条件（S3）

- 元の trace・`actors`・完全な記録・judge.json・集計・COMPLETE・台帳・計画・マニフェストを書きかえない（前後の全ファイルのハッシュが同じ）。
- r1 を記録したコミットから P3 の 7 ファイルを `git show` で取り出し（実行しない）、`lost_target_p3_basis` の値が今と同じことを確かめてから渡す。カードプールの前提も全局で確かめる。
- 結果の条件。
  - r1 の対象 1 行だけが undetermined → known_stop（判定と理由だけが変わる）。
  - s1 の P1 の 2 行は、規則 7 の当て直しの結果（`lost-target-p1-rejudge-s1/rejudged/`）と同じ判定・理由。
  - ほかの行・受理の中身・終わり方・undetermined の分類は規則 7 と同じ。
  - メタデータの差は `rules_version` 7 → 8 だけ。
- basis を渡さなければ、対象の行は D12 で undetermined のまま。

## 7. undetermined を維持する条件

次のどれかなら登録せず、規則 7 と同じ undetermined のまま（理由の先頭 `stop_condition_not_evidenced:UNSUPPORTED_SECRET_PLAN_LOST_TARGET`、分類 `evidence_missing_stop`、停止方針も同じ）。

- D1〜D12 のどれかを満たさない（欠け・重複・古さ・不一致・矛盾をふくむ）
- 相手のうら（P3o）、うらとおもての混在で相手のうらがある、2 つ以上を選ぶ決定
- 登録の表にない効果の型、`ends_on_lost_target` が真の効果、反応・特殊能力・スタジアム・文脈のあるトレーナーの決定、ワザの途中の決定
- 本当のカードがたね・ベイビィ（エンジンは受理するはずなので、根拠の矛盾）
- basis の欠け・不一致、カードプールやカードデータや効果の登録の違い

根拠の矛盾を suspect にしない（P1 の L11 と同じ。疑いの判定には別の根拠が要る）。

## 8. 採用判断が必要な点と推奨値

| 点 | 推奨 | ほかの案 |
|---|---|---|
| 登録の範囲 | P3s で、効果の型 `attached_damage_reduction` の `select_pokemon` だけ（保存済みの実例と、静的に確かめた経路に限る） | 再開先 `trainer` の全部・反応・特殊能力・スタジアムまで広げる（それぞれの形の根拠とテストが要る） |
| P3o | 登録しない（実例がなく、今の登録の効果では選べない）。性質だけを E12 で記録 | 本当のカードを読まない条件（公開のカードの一覧にたねでないカードがあること）で登録する |
| 登録方式 | 案 A（コード単位の入口のまま P3 の項目を別の鍵で 1 つ足す） | 案 B・C（5.1） |
| basis | P3 用の 7 ファイルを別の方式の名前で要約。P1 の 5 ファイルは変えない | P1 のファイルの組を広げる（P1 の L12 の意味が変わる） |
| 判定でエンジンの効果の登録を読む | 読む（`DEFAULT_EFFECTS.trainer_entry`。カード ID の分岐を judge に書かない。表は効果の型の id） | judge にカード ID の表を持つ（採らない） |
| 根拠の矛盾 | undetermined | suspect |
| 版 | 規則 8・`TOOL_VERSION` 10・形式 6 のまま | — |

採らない判断なら、P3 は undetermined のままで構わない（今の判定・停止方針と同じ）。

## 9. 実施しなかったこと・証跡

**実施しなかったこと**

- 根拠登録の実装、エンジン・judge・runner の変更、テストの追加と実行、判定の当て直し
- 新しい対戦、replay の再実行、seed の探索
- P2 の登録、GUI・方策・データの変更

**証跡** `C:\dev\kyuura-engine-verification-vai\verifier\runs\lost-target-p3-design\`

| ファイル | 中身 |
|---|---|
| `PLAN.md` | 事前計画 |
| `commands.txt` | 手順と終了コード |
| `extract_p3.py` → `p3_r1_extract.json` | 保存済みの 1 件の対応 |
| `availability.py` → `availability.json` | D1〜D12 の取得元の有無。s1・r1 のこのコードの候補の種類ごとの数 |
| `hashes_before*.json`・`hashes_after*.json` | r1・s1 の読む前後のハッシュ |

公開用の要約 `public/runs/lost-target-p3-design/summary.json` は件数と分類だけ。

## 10. 実装の結果（2026-11-14。規則 8・エンジン 0.181.0）

この章は、4〜6 章の推奨案（登録方式 A、P3 用 basis 7 ファイル、規則 8、`TOOL_VERSION` 10、形式 6）を、E12 を直したエンジン 0.181.0 を基点に実装した結果です。
保存済みの s1・r1 への当て直し、P2・P3o の登録、新しい対戦、GUI の追従はしていません。

### 10.1 基点

- ブランチは `claude/lost-target-p3s-judge-rule8-v0181`。基点は `claude/e12-keep-energy-removal-fix` の `acde830` で、エンジンは 0.181.0（配布の確かめは `a2b29e9`）。
- 0.180.0 で止めた作業（`claude/lost-target-p3s-judge-rule8`・`1eed4d1`・未追跡のテスト）は使わず、変えていない。
  - エンジンの根拠テストは、その証跡の写し（SHA-256 `79d45767…`）から取り込んだ。
- エンジン（動作・裁定・カードデータ・実装の識別）は変えていない。

### 10.2 エンジンの根拠テスト（6.2 節）

| id | 0.181.0 のテスト | 結果 |
|---|---|---|
| E7〜E11 | `tests/test_lost_target_p3_decision_v0_181.py`（写しから E12 のクラスを除いたもの） | 5 件とも成功（期待どおり） |
| E12 | 0.181.0 の `tests/test_keep_designated_energy_removal_v0_181.py` を再利用（`EnergyRemovalDesignatedKeepTest.test_opponent_face_down_energy_is_kp1_for_every_identity`・`ClientApiTwinTest`） | 同じ場面を確かめているので、新しいテストは足していない |

**E12 の期待値の変更**:

- 元の期待: どの本当のカードでも `UNSUPPORTED_SECRET_PLAN_LOST_TARGET`。
- 0.181.0 の期待: どの本当のカードでも `UNRESOLVED_KEEP_PROTECTED_TARGET`（KP1）。内部のエラーにならず、通常の拒否になる。
- 理由（[v0.181](keep-designated-energy-removal-v0.181.md) 4 章）: 置きかえの試しの順で、［KEEP］のたねが `_NONBASIC` より先に拒否するため。
- E12 は相手のうら（P3o）の対照と、v0.180 の内部の例外の回帰の確かめで、P3s の正の根拠ではない。

### 10.3 judge（規則 8）

**登録**:

- `KNOWN_STOP_EVIDENCE` に鍵 `LOST_TARGET_P3_EVIDENCE` = `"UNSUPPORTED_SECRET_PLAN_LOST_TARGET#P3"` を足した。項目は `code`（元の診断コード）・`condition`・`source`。
  - 鍵は経路の名前で、生の診断コードではない。
  - 判定の行の `engine_code`・`diagnostic_id` は元のコードのまま。診断のコード表には何も足していない。
- `_known_stop_or_undetermined` の照合を変えた。`entry = KNOWN_STOP_EVIDENCE.get(evidence)` で、`entry is None or entry.get("code", evidence) != code` なら undetermined。
  - 既存の 3 項目（DU1・ER9・P1）は `code` を持たないので、規則 7 と同じ式になる。

**条件**: `decision_lost_target_failure(entry, *, trace, actor_logs, header, basis_p3=None)` が D1〜D12（4.2 節）を順に確かめ、満たさない最初の id を返す。

- D7 は、観測の `trainer_in_use`（`player`・`user` が本人）の `card_id` から、エンジンの `DEFAULT_EFFECTS.trainer_entry` を読む。
  - 効果が `AttachedDamageReduction` で、`implementation_id` が `LOST_TARGET_DECISION_EFFECTS` にあり、`ends_on_lost_target` が偽のときだけ通る。カード ID の一覧は持たない。
- D10・D11 は P1 の L10 と同じ `effects.card_is_basic_in_text(definition, TEXT_PRE_NEO)` を使う。
- D12 は次の 2 つをどちらも満たすときだけ通る。
  - header の依存が今と同じ（既定のカードプール・カードデータの出どころ・効果の登録の id `DEFAULT_EFFECTS.id`）。
  - (a) `behavior_digest` が今と同じか、(b) 呼ぶ側の `basis_p3` が今の P3 の basis と同じ（方式・ファイルの並び・要約のすべて）。
  - P1 の `basis` は読まない。
- 判定のために効果を実行・再開しない。内部の状態を復元しない。
- 返す値は条件の id だけ。

**共通の入口**: `submit_evidence(..., basis=None, basis_p3=None)` は、ER9 → P1（`basis` だけ）→ P3s（`basis_p3` だけ）の順に呼ぶ。

**P1 は変えていない**: L1〜L12、`LOST_TARGET_BASIS_FILES`・方式、理由の文、`_basis_matches` の結果。依存の確かめを `_recorded_pool_matches`・`_same_behavior` に分けて共有したが、P1 の結果は同じ。

**根拠が成り立つときの理由**: `[unsupported, UNSUPPORTED_SECRET_PLAN_LOST_TARGET, continuation_not_evaluated, "evidence:" + P3 の条件の文]`。

**成り立たないとき**: 規則 7 と同じ判定・理由・分類で、停止方針も同じ。

- 理由の先頭は `stop_condition_not_evidenced:`、分類は `evidence_missing_stop`。
- 経路の理由がなければ、既存の `stop_not_explained_by_path`。
- refused・failed・分類の食い違いは、既存の suspect のまま。

### 10.4 P3 用 basis

- 方式は `kyuura-lost-target-p3-basis-sha256/1`。
- ファイルはこの順: `cards.py`・`data/kyuura_cards.json`・`effects.py`・`engine.py`・`zones.py`・`decisions.py`・`observation.py`。
- 正規化と要約は `replay_record._digest` と同じ（P1 の `lost_target_basis` と同じ関数）。
  - 並べたファイルの順に、パッケージの中の相対パスと、改行を LF にそろえた内容から sha256 を作る。

| | 0.181.0（今） | 旧 r1 を記録したエンジン（`de81f642`・0.179.0） |
|---|---|---|
| P3 の basis | `bb6d1730…` | 違う |
| P1 の basis | `d1729754…` | 違う |
| 7 ファイルの blob | — | `effects.py` だけが違う（v0.181 の修正） |

### 10.5 単局・バッチの共通の接続

- 単局の runner は変えていない。今の `submit_evidence(entry, trace=self.trace, actor_logs=self.actor_logs, header=self._record_header)` のまま。
  - 実行中の記録は今のエンジンが作るので、D12 は (a) で決まる。
- バッチは `batch.judge_trace(result, *, basis=None, basis_p3=None)`。`basis_p3` は保存済みの記録の当て直しだけが渡す。
- 判定のための observe・candidates・inputs・check・submit はしない。方策に新しい値を渡さない。完全な記録・相手の秘密は読まない。
- 構築盤面を本物の runner に通し、次を確かめた。
  - バッチの入口と単局の入口で同じ判定・同じ理由になる。
  - 要求の回数と行動の列が同じ。
  - 保存した `actors/*.jsonl` を読んでも同じ行になる。
  - たねのうらは受理（expected）、header のない対戦は D12 で undetermined。
- 記録・計画・完了の形式は変えていない（6 のまま）。runner の新しい取得は要らなかった。

### 10.6 識別

| 項目 | 前（`acde830`） | 後 |
|---|---|---|
| エンジン版・behavior・instrumentation | 0.181.0・`5e0cb4ac…`・`d3436748…` | 同じ |
| `TOOL_VERSION`・道具の識別 | 9・`383e30c4…` | 10・`7b56ed5a…` |
| 判定の規則・計画の形式・完了の形式 | 7・6・6 | 8・6・6 |
| P1 の basis | `d1729754…` | 同じ |
| P3 の basis | なし | `bb6d1730…` |

`TOOL_VERSION` 9 の計画は、道具の識別の違いで再開しない（移行・上書きしない）。

### 10.7 旧 r1 を直接当て直せない理由と、互換性の案（実装しない）

**直接当て直せない理由**:

- r1 は 0.179.0（`de81f642`）で記録した。
  - header の `behavior_digest` は 0.181.0 と違うので、D12 の (a) は通らない。
  - 7 ファイルのうち `effects.py` が違うので、(b) の P3 の basis も一致しない。
- 規則 8 を r1 に当てても、P3 の行は D12 で undetermined のまま。
- 今回、この不一致を例外にしたり、変更が P3 の経路と無関係だと推測して通したりはしていない。
  - しないこと: ファイルの除外、部分一致、新しい basis の旧記録への流用、記録時の識別の書き換え。

**互換性を個別に評価する仕組みの案**（どれも実装していない。採るかは別の判断）:

| 案 | 中身 | 影響 |
|---|---|---|
| A | 旧記録用の basis の許容リスト。記録したエンジンの basis と、その差が P3 の経路に関係しないことを人が監査した記録を、鍵つきで判定に渡す | 監査の記録と、その誤りの扱いが要る。判定の条件が緩む方向なので、根拠の出どころを証跡に固定する必要がある |
| B | 関数単位の basis。ファイル全体ではなく、経路の関数のソースだけを要約する | 方式が変わる（P1 と揃わない）。抽出の誤りで同じ処理を違うと判定する・違う処理を同じと判定するおそれがある |
| C | 再現での確かめ。旧記録の完全な記録を、今のエンジンで決定の時点まで再現して同じ拒否になることを確かめる | 0.180.0 以前の記録は 0.181.0 で再実行・復元できない（既存の設計）。実装の範囲が大きい |

推奨は、旧 r1 は undetermined のまま残し、0.181.0 以降の新しい記録で P3s の到達を確かめること。

### 10.8 テスト

**新しいテスト** `tests/test_verification_ai_lost_target_p3.py`（27 件）:

- 登録と照合: 鍵と生のコードの区別、既存の項目の照合が同じ、P3 の鍵を別のコードに渡しても通らない。
- 正: 保存済みの r1 の形、選んだ選べるものだけに理由がある形、たねでない本当のカードの種類。
- 負: 6.3 節の条件。
  - 相手のうら、おもての対象、たね・ベイビィ、real の欠け、決定の形と複数選択、別の回答者と観測の欠け・重複・古さ。
  - `trainer_in_use` の欠け・借りて使う・表にない効果・`ends_on_lost_target` が真、選べるものが本人の場と違う、参照の欠け・重複。
  - 未選択の選べるものだけの理由、候補の種類、拒否のあとの形、別のコード・refused・failed・通常の受理と拒否、停止方針、秘密の混入なし。
- P1 の不変、basis（P1 の basis だけ・P3 の basis の欠け・旧値・ファイルの不足・方式の違い・依存の違い）、batch の `basis_p3`。
- 本物の runner で単局とバッチが一致すること、方策などの部品が規則 8 を使わない境界。

**既存のテスト**:

- 規則・道具の版の期待値だけを更新した（9 ファイル。判定の中身の期待値は変えていない）。
- P1 の 31 件は、規則の版の期待値を除いて同じまま通った。

**関連**（1 モジュールずつ別プロセスで実行し、すべて成功）:

- ER9、P6（受理をふくむ）、U-R3a、batch、batch_judge、v3_1、v3_3、0.178・0.179 の追従、decklist_boundary、reach・reach_v2、v2_repeat。
- 検証用 AI の行動・契約の指紋は固定値のまま通った。

fixture・構築盤面は、new_game からの到達の実績に数えない。

### 10.9 残る作業

1. 0.181.0 以降の新しい記録（new_game からの対戦）で、P3s の場面に到達して規則 8 の判定を確かめる（今回は構築盤面だけ）。
2. 旧 r1 の扱い。10.7 節の案を採るか、undetermined のまま残すか。
3. P3o・ほかの効果の型・ほかの再開先の登録と、P2 の登録。
4. GUI の追従（規則 8 は検証者の側だけなので、API・GUI の契約は変わらない）。
