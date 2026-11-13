# LOST_TARGET の根拠登録の設計（最初の対象: おもての特殊能力で本人のうらのカードを指定する経路）

2026-11-13。`UNSUPPORTED_SECRET_PLAN_LOST_TARGET` の拒否を judge の known_stop に登録するための根拠と条件を、経路を 1 つに限って決めます。

- 調査・設計・文書化だけです。judge・エンジン・runner の実装、テスト、ビルド、replay の再実行、対戦、seed の探索はしていません。
- `kyuura_engine`・`tools.verification_ai` は import していません。コード・文書・保存済みの JSON を読み、静的に調べました。補助のスクリプトは証跡の側にあります（12 章）。
- 今の undetermined を急いで known_stop に変えるための文書ではありません。根拠が足りなければ undetermined を続けることも、正式な選択肢です（10 章）。
- 前の監査: [verification-ai-batch-s1-rejection-audit.md](verification-ai-batch-s1-rejection-audit.md) 4 章と、証跡 `vai-batch-s1-reject-audit/judge_proposal_lost_target.md` の変更案。この文書は、その案の条件 5（本当のカードがたねでないこと）の扱いを決め、条件を実装できる粒度にします。

## 1. 基点

- 基点は `claude/f1-face-down-attack-guarantee` の `a042ba3` です（パッケージ 0.180.0、配布の固定コミット `27ba35d`）。
  - `git fetch` のあと origin と一致しています。`a042ba3` を含むリモートのブランチはこれだけで、新しい公開コミットはありません。
  - `origin/main`（`7b3d53c`）の祖先ではありません。main への取り込みは仮定しません。
  - `27ba35d` から `a042ba3` までの差は文書だけです（`kyuura_engine`・`tools`・`pyproject.toml` の差は空）。
- 作業ブランチ `claude/lost-target-own-face-down-design` を、専用の worktree で `a042ba3` から作りました。
- 保存済みのバッチ `vai-batch-s1` は、実行コミット `7ee54b7`（0.179.0）で作られました。
  - `7ee54b7` から `a042ba3` までの差は、`kyuura_engine/legal_actions.py`（F-1 の保証の文）と版だけです。
  - `engine.py`・`zones.py`・`effects.py`・`cards.py`・`data/`・`tools/verification_ai/judge.py`・`batch.py`・`runner.py` は同じです。
  - この文書の行番号は `a042ba3` のものです。

## 2. 経路（このコードに至る呼び出し）

コードは `kyuura_engine/zones.py:50` の `SECRET_PLAN_LOST_TARGET_CODE` です。どこから至っても、出すのは `zones.designate_face_down`（138〜158 行）です。

- うらのカードが「効果の対象として指定された」ときにおもてにします。
- 本当のカードが「たねポケモン」でなく、呼ぶ側が対象を失ったあとを扱えない（`can_lose=False`）なら、状態を変える前に `UnsupportedError` を出します（154〜157 行）。理由の文に本当のカードは書きません。
- 「たねポケモン」の判定は `_secret_plan_keeps`（130〜135 行）で、`effects.card_is_basic_in_text(printed_def, TEXT_PRE_NEO) is True` です（`effects.py:15549`）。
  - 印刷の段階がたねか、ベイビィポケモンカードなら真です（マチスの秘策はネオより前のカード。GR-2000-P325-PRE-NEO-BABY）。
  - ほか（1 進化・2 進化・トレーナー・エネルギー）は偽です。

| 経路 | 入口と処理順 | 持ち主と本当のカード | 既存のテスト | この設計 |
|---|---|---|---|---|
| **P1 本人のうらのカードを指定**（おもての使い手の特殊能力の source・target、energy のついているポケモン） | `engine._apply` → `_apply_once` → `_reveal_for_action`（1075 行）。使い手（`command.pokemon`）がうらなら先におもてにします（1095〜1101 行）。続けて source → target → `energy` のついているポケモンの順に `designate_face_down(can_lose=False)`（1102〜1110 行）。これは handler（`check_use_pokemon_power` 以下）より前です | 持ち主が送った主体なので、`IDENTITY_CONSULTED` には記録しません。指定したうらのカードの本当のカードがたねでなければ、必ずこのコードになります | なし | **対象** |
| P2 相手のうらのカードを指定 | 同じ入口です。`by_player` が持ち主でないので `IDENTITY_CONSULTED` に記録し、`_apply_checked`（626 行）が `_identity_independent`（802 行）で、ありうるカードのすべてで確かめます | 本当のカードによらず、同じコードと同じ理由になります。本当のカードがたねでも、このコードになりえます | `tests/test_secret_plan_v0_67.py:316〜333` | 対象外 |
| P3 決定への回答で指定 | `engine._designate_answer`（1137 行）。`can_lose` は効果の `ends_on_lost_target` と、指定が 1 匹かで決まります | 決定の主体と持ち主の関係は場面によります | 突風など（終わる効果の側） | 対象外 |
| P1u 使い手がうら（U-R3a の経路）で、指定にもうらがある | 使い手を先におもてにし、たねなら同じ入口の指定へ進みます | judge では `is_face_down_power` の経路（規則 5）です | — | 対象外 |
| P4 処理の中の指定（つけたときに効果のある特殊エネルギー `effects.py:10790`、トレーナーをつける `zones.py:798`、反応 `movement.py:182`） | 受け付けたあとの処理の途中です | 場面によります | — | 対象外 |

P1 の根拠を、P2〜P4 に同じ条件で広げません。受け付ける条件、本当のカードの読み方、止まる時点が違うからです。カードの名前・ID・コード名だけで一般化もしません。

## 3. 保存済みの 2 件（vai-batch-s1）と、同じコードの対照 1 件（vai-batch-r1）

局の識別・本当のカード・入力の中身は、非公開の証跡にあります（`correspondence.md`・`census_lost_target.json`）。ここでは S1-a・S1-b と呼びます。

| 項目 | S1-a・S1-b | 確かめ方 |
|---|---|---|
| 操作の主体 | 主体 0、自分の番の main | **直接**（trace の actor・turn、結果の stage turn_action） |
| 候補 | `use_power`、unverified、理由 `face_down_reveal_not_evaluated`、段は source（meaning pokemon）→ energy（meaning card） | **直接**（trace の candidate・stages） |
| 使い手がおもて | 候補の `pokemon` に `card_id` があり、`face_down` はありません。本人の観測でも主体の場のおもてのポケモンです | **直接**（trace と本人の観測） |
| 指定先がうら | 選んだ source の選べるものが `face_down: true`。energy に選んだカードは、本人の観測でその同じうらのポケモンについています（source と energy の持ち主が同じ 1 匹） | **直接**（trace の meaning と本人の観測） |
| 指定したカードの持ち主 | 主体 0（本人の観測の `players[0]` のベンチ） | **直接**（本人の観測）。選べるものに持ち主の項目はありません（4.3） |
| 本当のカード | 本人の観測の `real` で、2 件ともポケモンでないカードでした（たねでない） | **直接**（本人の観測）と、カードデータの印刷の分類（静的に読んだ） |
| 入力と参照 | 選んだ入力（番号）、trace の meaning（場のポケモンの番号・カードの uid）、完全な記録の command（`use_pokemon_power` の pokemon・source・energy）が同じものを指します | **直接**（3 つの記録の照合） |
| 生の診断・分類 | 検証者の `engine_code`・`diagnostic_id`、公開の結果の `diagnostic_id` がこのコードで、分類は unsupported です | **直接** |
| 拒否のあと | status in_progress・continuable true・next は同じ主体の turn_action・`refetch_required` false・halt なし | **直接** |
| judge の今の判定 | undetermined（`stop_condition_not_evidenced:UNSUPPORTED_SECRET_PLAN_LOST_TARGET`。規則 6） | **直接**（judge.json） |
| エンジンが拒否する条件と処理順 | 使い手はおもてなので、1095 行の分岐は通りません。source の指定（1106 行）で、本人のたねでないうらのカードとして 154 行で止まります | **コード上の根拠**（実行していない） |
| 状態が変わらないこと | runner の拒否ごとの比べで異常 0。replay_run は期待どおりでした（前の監査 3.2 節） | 前の監査の記録 |
| 裁定と未対応の根拠 | [secret-plan-preflight-v0.67.md](secret-plan-preflight-v0.67.md) 4 章・5 章（エンジンの未対応）、`docs/stop-policy-classification.json`（分類 A・P2・PF-RUNTIME-CONTINUATION）、[legal-actions-r3-audit.md](legal-actions-r3-audit.md):44 | 文書 |
| P1 のエンジンのテスト | 見つかりません。既存は P2 の 1 件だけです | **未確認**（8.1 で追加を計画） |

対照の vai-batch-r1 の 1 件は `answer_decision`（P3）でした。拒否のあとは同じ主体の決定待ちで、judge は同じく undetermined です。

保存済みの 2 バッチの、このコードの送信はこの 3 件だけです（P1 が 2、P3 が 1。`census_lost_target.json`）。

## 4. 今の undetermined の理由と、根拠として使える情報

### 4.1 判定の流れ（規則 6）

- `judge.judge_normal`（`tools/verification_ai/judge.py:166`）で、候補は `is_face_down_power` ではなく（使い手がおもて）、`is_p6` でもありません。
- `use_power` は `PRECHECK_KINDS` にありません。分類 unsupported は停止系なので、`_known_stop_or_undetermined`（285 行）へ進みます。
- コード表にあり、理由 `face_down_reveal_not_evaluated` もあります。しかし `KNOWN_STOP_EVIDENCE`（60 行）に登録がなく、`evidence` も渡されていません（`batch.judge_trace` の evidence は `recorded_stop_evidence`。ER9 だけ。302 行）。そのため undetermined です。
- バッチでは `undetermined_category` が理由の先頭で `evidence_missing_stop` と分類し、停止方針で続けます（`batch.py:482`）。

### 4.2 「指定先の本当のカードがたねでない」を確かめる情報の比べ

| 候補 | 条件を確定できるか | 既存の記録で使えるか | 新しい記録 | 単局とバッチで同じ入口か | 秘密と公開の集計 |
|---|---|---|---|---|---|
| A. 送信の記録（trace の candidate・stages・meaning・submit） | **できない**。本当のカードは送信の値にありません。経路の形（使い手がおもて・うらを指定）は分かりますが、持ち主の項目はありません | 使える | 不要 | 同じ（`judge_trace`） | 秘密を使わない |
| **B. 送信前の本人の観測**（runner がエピソードの初めに取り、方策にも渡した本人の view。`actors/<主体>.jsonl` の type=position） | **できる**。指定したうらのポケモンの持ち主と `real.card_id` があり、エンジンのカードデータの印刷の分類で、エンジンと同じ判定（4.4）をします | 使える。バッチは `actors/*.jsonl` が必須のファイルで（`batch.REQUIRED_FILES`）、s1 の 2 件とも 1 行ずつ対応しました | 不要 | 同じにできる。どちらも runner の `actor_logs` から引きます（6.2） | 送った本人の知識だけです。方策は同じ view をもう受け取っているので、新しい情報は渡りません（runner.py:321・357）。判定の行・集計に本当のカードを書かないことが条件です |
| C. 診断の構造化情報（検証者の診断・公開の結果） | **できない**。`engine_code`・`diagnostic_id`・分類だけで、理由の文にも本当のカードはありません | 使える | 足すにはエンジンの診断の変更が要ります（この設計ではしない） | — | — |
| D. 検証者用の完全記録（full_record.json）と replay | できる。ただし replay で状態を作り直す必要があります | 使える | 不要。ただし replay の実行が要ります | 判定の入口が replay を持つことになり、今の judge の外です | 両主体のすべての秘密を使う。必要以上の情報です |

**推奨: B**（本人の観測とエンジンのカードデータ）。条件を証明する最小の情報です。

- A だけでは、コードの原因が入口の指定なのか、受け付けたあとの処理（P4）なのかを区別できません。たねのうらのカードを指定した場合、エンジンはおもてにして handler へ進みます。
- D は replay に依存し、判定に使う秘密が増えます。完全な記録の command は、当て直しの単位で参照の照合（入力 → command）に使うだけにし、判定の入力には加えません。
- 判定に使ったのは、保存済みの trace だけではありません。本人の観測の記録（`actors/<主体>.jsonl`）とカードデータにも依存します。この依存は、文書・判定の理由・当て直しの記録に明示します。

### 4.3 API の値で分かる範囲と限界

- 選べるものに、持ち主・主体の項目はありません。`legal_actions._pokemon_option`（1012 行）と `_public_pokemon`（1652 行）は、本人のうらのカードには `card`（uid）を付け、相手のうらのカードには付けません。
  - これは実装の形で、契約の項目ではありません。持ち主は本人の観測で決め、`card` の有無は判定に使いません（補助の照合として記録だけします）。
- 段の `role`（source・target・energy）と `meaning`（pokemon・card）は、宣言の型（`effects.POWER_INPUT_STAGES`）から来ます。`meaning` は自分の場と相手の場を区別しません（`_POWER_MEANING`。1648 行）。
- 特殊能力の名前・カード ID で経路を決めません。経路は、種類 `use_power`・使い手がおもて・選んだ段の role・本人の観測の持ち主とうら、で決めます。

### 4.4 本当のカードの判定（エンジンと同じ意味）

- 判定はエンジンの `effects.card_is_basic_in_text(definition, TEXT_PRE_NEO)` を使います。`definition` は、`cards.load_card_pool()`（new_game の既定のカードの一覧。`engine.py:377`）の `real.card_id` の定義です。
  - judge が独自に段階を読み直すことはしません。`zones._secret_plan_keeps` と同じ関数・同じ版の説明です。
  - judge のテストで、両者が同じ答えになることを確かめます（8.2 の J9）。
- 答えが `False` のときだけ「たねでない」とします。`None`（決まらない）と、カードが一覧にないときは根拠なしとします。

## 5. 推奨する適用条件（規則 7）

判定は送信 1 件ごとです。次の L1〜L12 をすべて満たすときだけ、evidence = `UNSUPPORTED_SECRET_PLAN_LOST_TARGET` を `judge_normal` に渡します。1 つでも満たさない・読めない・矛盾するなら evidence は None で、判定は規則 6 と同じです。

| id | 条件（判定に使う値） | 採否と理由 |
|---|---|---|
| L1 | エンジンの拒否: `submit.outcome == "rejected"`、`ok is True`、`refusal is None`、`error is None` | 採る。ホストの refused・failed は `judge_normal` が先に suspect にします（変えない） |
| L2 | コードと分類: `verifier.engine_code == verifier.diagnostic_id == result.diagnostic_id == このコード`、`verifier.category == result.category == "unsupported"` | 採る。コード表の分類の食い違いは `judge_normal` が先に suspect にします（変えない） |
| L3 | 拒否のあと: `result.status == "in_progress"`、`continuable is True`、`next == [{"kind": "turn_action", "player": 主体}]`、`viewer == 主体`、`halt is None`、`submit.refetch_required is False` | 採る。入口で止まったこと（決定を残さない・番が続く）の形です |
| L4 | 候補の経路: `kind == "use_power"`。候補の `pokemon` に文字列の `card_id` があり、`face_down` が true でない。`power.face_down` が true でない。理由に `face_down_reveal_not_evaluated` がある | 採る。使い手がおもて（P1u を除く） |
| L5 | 選んだ入力: `meaning` が 1 つ以上で、選んだすべての段の role が source・target（meaning pokemon）か energy（meaning card） | 採る。入口で指定になる役割だけ（2 章の 1102〜1110 行） |
| L6 | 観測の時点: その主体の `actors` の type=position の行のうち、position と episode が送信と同じ行がちょうど 1 つ。その観測は viewer・current_player が主体、phase main、decision なし、turn が送信の番と同じ。さらに、trace の同じエピソードの、この送信より前の送信に受理がない | 採る。観測が送信の直前の状態と同じであること（拒否は状態を変えない。runner が拒否ごとに確かめる） |
| L7 | 使い手: 候補の `pokemon.pokemon` が観測の主体の場にちょうど 1 つあり、うらでない | 採る。L4 を観測で裏づける |
| L8 | 参照: source・target の番号は観測の場のポケモンにちょうど 1 つ一致する。energy のカード（uid）は、ついている場のポケモンがちょうど 1 つ。選べるものの `face_down` と観測の `face_down` が同じ | 採る。参照の欠け・重複・食い違いを除く |
| L9 | 持ち主: 指定（L8 で引いた場のポケモン）にうらが 1 つ以上あり、うらのものはすべて主体の場（観測の `players[主体]`）にある | 採る。相手のうらが 1 つでもあれば P2（混在をふくむ）なので除く |
| L10 | 根拠がそろう: 指定したうらのすべてに、観測の `real.card_id` があり、カードの一覧にあり、4.4 の答えが True か False | 採る。欠ければ判定できない |
| L11 | 本当のカード: 指定したうらのうち 1 つ以上で、4.4 の答えが False（たねでない） | 採る。エンジンが入口で止める十分条件です（どのうらから指定しても、たねでないものに当たると止まる） |
| L12 | 判定の基礎: 4.4 の判定に使うカードデータと関数が、記録を作ったエンジンと同じ。実行中の判定（runner・バッチ）では同じプロセスなので満たします。保存済みの記録の当て直しでは、記録の `header.engine.git_commit` と判定のエンジンで、`kyuura_engine/data/kyuura_cards.json`・`cards.py`・`effects.py` が同じであることを、当て直しの単位が先に確かめます | 採る。旧記録へ当てるときの取り違えを防ぐ |
| — | 完全な記録の command と入力の一致 | 判定の入力には加えない。当て直しの単位の照合で確かめる（実行中の判定では、同じ入力から command を作るので冗長） |
| — | 選べるものの `card` の有無 | 加えない（実装の形。4.3） |

**満たさないときの扱い**（規則 6 と同じ。上書きしない）

| 状況 | 判定 |
|---|---|
| L1・L2 の外（refused・failed・コードの食い違い） | `judge_normal` の既存の規則のまま（suspect など） |
| このコードだが L3〜L12 のどれかを満たさない（P2・P3・P1u・混在・参照の欠け・古い観測・根拠の欠けを含む） | undetermined。理由は今と同じ `stop_condition_not_evidenced:<code>` を先頭に置きます。規則 7 の失敗の理由は判定の行に足さず、当て直しの記録に残します |
| L1〜L10 を満たし、指定したうらがすべてたね（L11 だけ偽）: 根拠の矛盾 | undetermined（同じ理由）。入口ではおもてにして handler へ進むので、そのあとの処理の P4 でこのコードになることを否定できないためです（suspect にはしません）。当て直しの記録では「根拠の矛盾」として人の確認へ回します |
| 別のコード・通常の受理と拒否 | 既存のまま |

- 理由の先頭を変えないので、`undetermined_category` の分類（`evidence_missing_stop`）と停止方針は変わりません。
  - 新しい理由を先頭に置くと unclassified になり、バッチが止まります。それは避けます。
- known_stop の理由は `["unsupported", <code>, "face_down_reveal_not_evaluated", "evidence:" + 条件の文]` とします（`_known_stop_or_undetermined` の既存の形）。
  - 理由・集計には、場のポケモンの番号・カードの uid・`card_id`・`real` を書きません。条件の文は固定の文字列です。

## 6. インターフェース・記録・互換性への影響

### 6.1 judge（規則 6 → 7）

- 新しい関数（名前は案）`own_face_down_lost_target_evidence(entry, own_view, *, pool=None) -> str | None` を作ります。
  - 引数は trace の送信の行 1 つと、L6 で引いた本人の観測です。L1〜L11 を確かめ、満たせばコードを返します。
- 本人の観測を引く補助（案）`own_view_for(actor_logs, entry)` を作ります。L6 の照合と同じ規則で、ちょうど 1 つでなければ None を返します。
- `KNOWN_STOP_EVIDENCE` にこのコードを加えます。
  - 条件の文は「P1 だけ」と書きます。
  - source には、エンジンのテスト（8.1）・`zones.designate_face_down`・`engine._reveal_for_action`・secret-plan-preflight-v0.67.md 4 章・5 章を挙げます。
- `RECORDED_STOP_CONDITIONS`・`recorded_stop_evidence`（ER9）は変えません。
- `judge_normal`・`_known_stop_or_undetermined` は変えません。evidence は今の引数で渡します。
- `JUDGE_RULES_VERSION` を 7 にし、ヘッダの来歴の注記に規則 7 を足します。

### 6.2 呼ぶ側（runner・バッチ。単局とバッチで同じ入口）

- `batch.judge_trace(result)`: 今は `result["trace"]` だけを使います。`result["actor_logs"]` から `own_view_for` で観測を引き、`recorded_stop_evidence(...) or own_face_down_lost_target_evidence(e, view)` を evidence にします。
  - `actor_logs` は runner の結果に今もあります（runner.py:185）。記録の形は変わりません。
- runner の単局の変異の判定（runner.py:478。`negative` があるとき）: 同じ 2 つの関数を、`self.actor_logs` と送信の行で呼びます。どちらも同じ関数なので、単局とバッチで同じ判定になります。
- runner・記録・バッチの記録の形・ファイルは変わりません。新しい記録は要りません。本人の観測は今も保存しています。

### 6.3 版と識別

- エンジンの版（0.180.0）・behavior_digest・instrumentation_digest は変わりません。
  - 実装識別は、パッケージの `kyuura_engine` の .py と `data/*.json` だけを対象にします（`replay_record.package_files`）。
  - エンジンのテストの追加（8.1）だけでは版を上げません（前例: `2366714` はテストだけで版を変えていない）。
- judge の変更で、道具の識別（`batch.tool_digest`。`tools/verification_ai/*.py`）が変わります。
  - **`TOOL_VERSION` を 8 → 9 にする**ことを推奨します（前例: 規則 6 は TOOL_VERSION 4）。
  - 計画の形式（`kyuura-vai-batch-plan/6`）と完了の形式（`/6`）は、項目が変わらないので変えません。
- 既存の計画（TOOL_VERSION 8・規則 6）は、道具の識別の違いで再開しません（既存の設計のまま）。移行・上書きはしません。
- 検証用 AI の行動・契約の指紋（v2_repeat）は judge を使わないので、変わらない見込みです（実装の単位で `test_verification_ai_v2_repeat` を実行して確かめる）。

### 6.4 旧記録への当て直し（実装のあとの別の単位）

- 新しい証跡の単位で、保存済みの trace・`actors/*.jsonl`・judge.json を読み、規則 7 の judge を当てて、別のファイルに書きます。元の trace・judge.json・集計・完了マーカーは変えません（前後の sha256 で確かめる）。
- 先に L12 を確かめます。s1 の記録（`7ee54b7`）と `a042ba3` で、3 つのファイルが同じことは確かめ済みです（1 章）。実装のコミットでも確かめ直します。
- 受け入れ条件:
  - 判定が変わるのは s1 の 2 行（undetermined → known_stop）だけ
  - ほかの行（判定・理由）は規則 6 とすべて同じ。r1 の P3 の 1 件も含みます
  - 局ごとの undetermined の分類・停止方針の結果は、その 2 件のほかは同じ
  - 集計し直した件数の差は、undetermined −2・known_stop +2 だけ
  - 完全な記録の command と入力の参照の照合が一致する
- この設計の静的な事前評価（11 章）は、その見込みと合っています。ただし、規則 7 の judge を実行した結果ではありません。

## 7. 推奨案と採用判断が残る事項

**推奨案**: B（本人の観測とエンジンのカードデータ）で L1〜L12 を確かめ、P1 だけを規則 7 で known_stop に登録します。順序は 9 章のとおりです。

採用の判断が要る事項（推奨値）:

| id | 事項 | 推奨値 | 理由 |
|---|---|---|---|
| A1 | judge の入力を、送信の値だけ（規則 6）から「送った本人の、送信前の観測とエンジンのカードデータ」へ広げるか | **広げる**（P1 の条件だけ） | 本当のカードの条件を確かめる最小の情報です。方策へ新しい情報は渡りません |
| A2 | evidence の鍵をコード単位（今の仕組み）にするか、経路単位にするか | **コード単位のまま**（条件の文で P1 に限る） | `_known_stop_or_undetermined` を変えずに済みます。P2・P3 を登録するときに経路単位の鍵へ移す（その単位で判断する） |
| A3 | 根拠の矛盾（L11 だけ偽）の判定 | **undetermined**（理由は今と同じ） | P4 を否定できないためです。人の確認は当て直しの記録で行う |
| A4 | 道具の版 | **TOOL_VERSION 9**、計画・完了の形式は 6 のまま | 判定の結果が変わるため。項目は変わらない |
| A5 | s1 への当て直し | 実装とテストのあと、**別の単位で行う** | 元の証跡を上書きしないため |
| A6 | 登録しない（undetermined を続ける） | A1 を採らないなら、この選択にする | 送信の値だけでは十分な根拠がないため（4.2 の A） |

## 8. テストと受け入れ条件

### 8.1 エンジン側（先に行う。エンジンの動作・裁定は変えない。テストだけを足し、版は上げない）

| id | 内容 | 期待 |
|---|---|---|
| E1 | 本人のたねでないうらのカードを、おもての使い手（ロケット団のヒトカゲなど source・energy の 2 段の特殊能力）の source に指定する | `UnsupportedError`（このコード）。状態・乱数・ログが変わらない。理由の文に本当のカードの名前・ID がない |
| E2 | source はおもて、energy だけを本人のたねでないうらのカードについたカードにする | E1 と同じ（energy のついているポケモンの指定。1107〜1110 行） |
| E3 | 本人のうらのカードがたね（E1 と同じ指定） | このコードにならない。おもてにして特殊能力の確かめへ進む（エネルギーのタイプが合わなければ WRONG_ENERGY_TYPE で拒否し、状態はもどる。合えば受理） |
| E4 | 本人のうらのカードがベイビィポケモン | たねと同じく、このコードにならない（GR-2000-P325-PRE-NEO-BABY） |
| E5 | 相手の場にも別のうらのカードがあるが、指定は本人のうらのカードだけ | E1 と同じコード・同じ状態（`_apply_checked` の確かめは記録がないので、元の例外のまま） |
| E6 | 指定のなかに、本人のたね（先）とたねでない（後）のうらのカードがある | このコード。状態は変わらない（先におもてにしたものも複製ごと捨てる） |

これらのテストを `KNOWN_STOP_EVIDENCE` の source に挙げます。E1〜E6 のどれかが期待と違えば、judge の登録へ進みません（10 章）。

### 8.2 judge 側（エンジン側のあと。規則 7）

正のテスト（構築した送信の行と観測。保存済みの記録の形を写す）:

| id | 内容 | 期待 |
|---|---|---|
| J1 | s1 と同じ形（source と energy が同じ本人のたねでないうらのポケモン） | known_stop。理由は 5 章の形 |
| J2 | energy だけがうらの指定（E2 の形） | known_stop |
| J3 | 本人のたね（観測）とたねでない（観測）のうらを両方指定 | known_stop（L11 は 1 つ以上） |
| J9 | 4.4 の判定とエンジンの `zones._secret_plan_keeps` が、カードの一覧のすべてのカードで同じ答え（`printed_def` だけを持つ代わりの状態で呼ぶ） | 一致 |
| J10 | `own_view_for` が runner の `actor_logs` と、保存した `actors/*.jsonl` の読み込みで同じ行を返す | 一致（単局とバッチで同じ入口） |

負のテスト（どれも known_stop にならない。下の「期待」は規則 6 と同じ判定）:

| id | 内容 | 期待 |
|---|---|---|
| N1 | 同じコードで、指定したうらが相手の場（P2） | undetermined（`stop_condition_not_evidenced:`） |
| N2 | 同じコードで、本人と相手のうらを両方指定（混在） | undetermined |
| N3 | 同じコードで `answer_decision`（P3） | undetermined |
| N4 | 同じコードで、使い手がうら（P1u。`is_face_down_power`） | undetermined |
| N5 | 同じコードで、指定したうらがすべてたね（観測。根拠の矛盾） | undetermined |
| N6 | 同じコードで、うらを指定していない（指定がすべておもて） | undetermined |
| N7 | 観測の行がない・2 つある・episode が違う・番が違う・decision がある | undetermined |
| N8 | 同じエピソードで、この送信の前に受理がある（古い観測） | undetermined |
| N9 | 参照の欠け・食い違い（番号が観測にない、energy のカードがどこにもついていない・2 か所、選べるものと観測の face_down が違う） | undetermined |
| N10 | `real` がない・`card_id` がカードの一覧にない | undetermined |
| N11 | 拒否のあとの形が違う（status・next・viewer・refetch_required・halt） | undetermined |
| N12 | 同じ形で、コードが別（WRONG_ENERGY_TYPE など） | 既存の判定のまま |
| N13 | refused・failed・コードの分類の食い違い | 既存の suspect のまま |
| N14 | 通常の受理・通常の拒否 | 既存の判定のまま |
| N15 | 理由・`judge_trace` の行・集計に、場のポケモンの番号・uid・`card_id`・`real` が入らない | 入らない |
| N16 | N1〜N11 の undetermined の分類が `evidence_missing_stop` のまま（停止方針が変わらない） | 同じ |

受け入れ条件:
- E1〜E6・J1〜J3・J9・J10・N1〜N16 がすべて通る
- 既存の judge のテスト（規則 3〜6）と v2_repeat の指紋が変わらない
- 6.4 の当て直しで、変わるのが対象の 2 行だけ

## 9. 最小の実装・検証の順序（次の単位以降）

1. **エンジンのテストの追加**（8.1）。動作・裁定・パッケージは変えず、版は 0.180.0 のままです。関係するモジュールだけを 1 つずつ実行します。
2. **judge の規則 7**（6.1・6.2・8.2）。`TOOL_VERSION` 9 と、来歴の注記を加えます。
   - 関係するテスト（judge・batch・runner の判定・v2_repeat）を実行します。
   - 新しい計画の作り直しは要りません。既存の計画は再開しません。
3. **当て直し**（6.4）。新しい証跡の単位で行い、元の証跡を変えません。
4. （任意）規則 7 で新しいバッチを実行するかは、別に判断します。

## 10. undetermined を維持する条件

次のどれかなら、P1 も undetermined のまま（規則 6）にします。

- A1（本人の観測とカードデータを判定に使う）を採らない
- エンジン側の E1〜E6 のどれかが期待と違う（入口で止まるという前提が崩れる）
- 当て直しで、対象の 2 行のほかに判定・理由・分類が変わる行がある
- L12（カードデータと関数の同一）を、当て直す記録で確かめられない
- 本人の観測の記録（`actors/*.jsonl`）が、当て直す局で欠けている

## 11. 静的な事前評価（予測。規則 7 の判定ではない）

L1〜L11 を、保存済みの s1・r1 のすべての送信（8,904 件。s1 7,184・r1 1,720）に、記録の JSON だけで当てました（`evaluate_conditions.py`）。

- 本当のカードの判定は、カードデータの JSON の印刷の分類で近似しました（たね・ベイビィなら真）。実装では 4.4 のエンジンの関数を使います。

| 結果 | 件数 |
|---|---|
| L1〜L11 をすべて満たす | 2（S1-a・S1-b。どちらも今は undetermined） |
| このコードだが満たさない | 1（r1 の P3。L3 で外れる。拒否のあとが決定待ち） |
| このコードでないのに満たす | 0 |
| 受理（L1 で外れる） | 8,895 |
| ほかのコードの拒否（L2 で外れる） | 6 |

この結果は、当て直しで変わる行が対象の 2 行だけになる見込みと合っています。ただし、規則 7 の judge を実行した結果ではありません。

## 12. 実施しなかったこと・未確認・証跡

- 実施しなかったこと:
  - judge・エンジン・runner の実装
  - テストの追加と実行、ビルド
  - replay、対戦、seed の探索
  - `kyuura_engine`・`tools.verification_ai` の import
- 未確認:
  - P1 のエンジンの動作は、コードを読んだ根拠と保存済みの 2 件の記録だけです（P1 のテストはまだない。8.1）
  - P4 の経路が実際の対戦で起きるかは調べていません
  - vai-batch-s1・r1 のほかのバッチの同じコードは数えていません
- 証跡: `C:\dev\kyuura-engine-verification-vai\verifier\runs\lost-target-own-face-down-design\`
  - 事前計画
  - 調査スクリプト（`census_lost_target.py`・`evaluate_conditions.py`）と出力・終了コード
  - 対応表 `correspondence.md`（非公開。局・本当のカード・入力を含む）
  - コマンドと失敗
- 公開用は `public/runs/lost-target-own-face-down-design/summary.json`（件数と分類だけ）です。

## 13. 実装の結果（2026-11-14。エンジンの根拠テスト・judge の規則 7・単局とバッチの共通の接続）

この章は、上の推奨案（A1 広げる・A2 コード単位・A3 矛盾は undetermined・A4 TOOL_VERSION 9）を実装した結果です。保存済みの s1 への当て直し、P2・P3 の登録、新しい対戦はしていません。

### 13.1 基点・ブランチ

- 基点は `claude/lost-target-own-face-down-design` の `eb1c201`（origin と一致。`origin/main` の祖先ではない。main への取り込みは仮定しない）。
- 専用の worktree で、新しいブランチ `claude/lost-target-p1-judge-rule7` を `eb1c201` から作りました。

### 13.2 エンジン側の根拠テスト（E1〜E6）

`tests/test_lost_target_own_face_down_v0_180.py`（6 件）。盤面は `tests/test_secret_plan_v0_67.py` の `place`・`full`・`face_down`・`uid_of`・`opponent_turn` と `build_test_state` で作ります。使い手はロケット団のヒトカゲ（［ほのおをもらう］。段は source → energy）です。

| id | 内容 | 結果 |
|---|---|---|
| E1 | source に本人のたねでないうら（エネルギー 2 種・1 進化。energy もそのうらについている） | このコード。状態（ログ・決定・番・場）・乱数・相手と観戦者の観測とログが変わらない。理由の文に本当のカードの ID・名前がない。`IDENTITY_CONSULTED` を残さない |
| E2 | source はおもて、energy だけが本人のたねでないうらについている | E1 と同じ |
| E3 | 本人のうらがたね | このコードにならない。おもてにして特殊能力を使う（炎）。合わないタイプなら `WRONG_ENERGY_TYPE` で状態は変わらない |
| E4 | 本人のうらがベイビィ（ネオより前の説明の「たねポケモン」） | E3 と同じ |
| E5 | 相手の場にも別のうらがあり、指定は本人のうらだけ | E1 と同じ。本当のカードによらない確かめ（`_identity_independent`）を呼ばない |
| E6 | 本人のたねのうら（source。先に指定）と、たねでないうら（energy のついているポケモン。後に指定） | このコード。先におもてにしたたねもふくめ、状態は変わらない |

- 6 件とも期待どおりでした。エンジンの動作・裁定・カードデータは変えていません。
- 相手のうらの指定（P2）は、既存の `tests/test_secret_plan_v0_67.py` の `test_power_target_on_a_face_down_card_is_refused_for_every_identity` のままです（変えていない）。
- テストの追加の前後で、パッケージの版 0.180.0・`behavior_digest`（`08038e06…`）・`instrumentation_digest`（`d3436748…`）は同じでした。

### 13.3 judge の規則 7

`tools/verification_ai/judge.py` に次を加えました。`judge_normal`・`_known_stop_or_undetermined`・`recorded_stop_evidence`（ER9）は変えていません。

- `own_view_for(actor_logs, entry)`: 送信の主体の、type=position・position・episode（番号と主体）が同じ観測の行がちょうど 1 つのときだけ、その view を返します。`actor_logs` は runner の結果の値でも、保存した `actors/<主体>.jsonl` を読んだ辞書でも同じ行を返します。
- `lost_target_failure(entry, *, trace, actor_logs, header, basis=None)`: L1〜L12 を順に確かめ、満たさない最初の条件の id（`L1`〜`L12`）か None を返します。返す値は条件の id だけで、場のポケモンの番号・uid・カード ID・本当のカードを持ちません。
- `own_face_down_lost_target_evidence`・`submit_evidence`: 単局とバッチの共通の入口です。`submit_evidence` は規則 6（ER9）か規則 7（P1）の条件をすべて満たしたときだけコードを返します。
- `KNOWN_STOP_EVIDENCE` に `UNSUPPORTED_SECRET_PLAN_LOST_TARGET` を加えました。条件の文は P1 だけ（固定の文字列）で、source に E1〜E6・`zones.designate_face_down`・`engine._reveal_for_action`・secret-plan-preflight-v0.67.md を挙げます。
- `JUDGE_RULES_VERSION = 7`。
- たねの判定は `effects.card_is_basic_in_text(定義, TEXT_PRE_NEO)` をそのまま呼びます（judge に段階の読み直しを複製しない）。定義は `cards.load_card_pool()` です。

実装で詳しくした点（設計 5 章との差）:

- **L4 の理由の範囲**: 設計は「候補の理由に `face_down_reveal_not_evaluated`」としていました。本物の runner に構築盤面を通すと、候補がおもてだけの組（おもてのポケモンを source にする組）もふくむ場合、候補の理由は `continuation_not_evaluated` になり、`face_down_reveal_not_evaluated` は選んだうらの選べるものの側にだけ付きました（s1 の 2 件は候補の側にもありました）。そこで L4 の理由は「候補か、選んだ選べるもの」にあることとしました。これは `_known_stop_or_undetermined` が理由を集める範囲と同じです。記録の形式は変えていません。うらの指定そのものは L8・L9（観測）で確かめます。
- **L12 の確かめ方**: 記録の header（`engine` と `dependencies`）を読みます。既定のカードプール（`card_pool == "default"`）で、カードデータの出どころ（repository・commit・path）が今のカードプールと同じことが前提です。そのうえで、次の (a) か (b) のどちらかが要ります。
  - (a) 記録の `behavior_digest`・方式が今の実装と同じ（実行中の runner・バッチはこれで満たす）
  - (b) 呼ぶ側が、記録を作ったエンジンの基礎のファイル（`cards.py`・`data/kyuura_cards.json`・`effects.py`・`engine.py`・`zones.py`）から同じ方式（`kyuura-lost-target-basis-sha256/1`。実装の識別と同じ正規化）で計算した値 `basis` を渡し、それが今の値と同じ
  - header がない対戦（記録を持たない fixture など）や、どちらも確かめられないときは L12 で外れ、undetermined のままです。
  - s1 の記録は 0.179.0（`behavior_digest` が今と違う）なので、当て直しでは (b) が要ります。`batch.judge_trace(result, basis=...)` で渡します。
- **根拠が成り立たないとき**: evidence は None で、判定・理由・分類は規則 6 と同じです（先頭は `stop_condition_not_evidenced:`、分類 `evidence_missing_stop`、停止方針は続ける）。規則 7 の失敗の条件の id は判定の行に足しません。refused・failed・分類の食い違いは、`judge_normal` が先に suspect にします（上書きしない）。

### 13.4 単局とバッチの接続と情報の境界

- `batch.judge_trace(result, *, basis=None)`: 送信ごとに `submit_evidence(e, trace=result["trace"], actor_logs=result.get("actor_logs"), header=記録の header, basis=basis)` を evidence にします。header は `batch.record_header(result["record"])` で、L12 を確かめるときだけ読みます（操作の記録は読まない）。
- runner の単局の判定（`negative` があるときだけ）: 同じ `submit_evidence` に `self.trace`・`self.actor_logs`・`self._record_header`（`self.game.record()` の header。記録を持たない対戦では None）を渡します。これまでこの判定は evidence を渡していなかったので、ER9 の条件を満たす送信も、ここで known_stop になります（逐次バッチと同じになる）。
- 判定のための observe・candidates・inputs・check・submit はしません。本人の観測は、runner がエピソードの初めに取って方策にも渡した値を再利用します。完全な記録の操作・相手の観測・replay へは進みません。
- 方策・行動生成・乱数・記録の形式・公開の API の応答は変えていません。方策・行動生成・変異・集計・記録の部品は規則 7 の部品を使いません（テストで確かめる）。
- 判定の行・理由・集計に、場のポケモンの番号・uid・card_id・本当のカードを入れません。

### 13.5 テスト

新しいモジュール `tests/test_verification_ai_lost_target_p1.py`（31 件）:

- 正: J1（s1 と同じ形）・J2（energy だけがうら）・J3（たねとたねでないうらの両方）・target の段・候補でなく選べるものにだけ理由がある形・J9（カードの一覧のすべてで、規則 7 の判定とエンジンの `zones._secret_plan_keeps` が同じ答え）
- 負: N1（相手のうら）・N2（本人と相手の混在）・N3（決定への回答。拒否のあとの形が同じでも種類で外れる）・N4（うらの使い手）・理由がどこにもない・N5（すべてたね・ベイビィ）・N6（うらの指定なし）・N7（観測の欠け・重複・別のエピソード・別の位置・別の番・決定・番の主体でない・段階・失敗の応答・actor_logs なし）・N8（同じエピソードの前の受理）・N9（参照の欠け・食い違い・重複、role・meaning・段の欠け）・N10（real・card_id・カードの一覧）・N11（拒否のあとの形 6 種）・N12（同じ形の別のコード）・N13（refused・failed・分類の食い違いは suspect のまま）・N14（通常の受理・拒否）・N15（理由・行・要約に秘密がない）・N16（分類と停止方針）
- L12: header の有無・関数の header・実装の違い・basis の一致と不一致・方式の違い・カードデータの違い・カードプールの違い、`batch.judge_trace` への basis の受け渡し
- 本物の runner（構築盤面。new_game からの対戦の実績には数えない）: たねでないうらで、バッチの入口と単局の判定が同じ known_stop・同じ理由。単局の判定を有効にしても要求の回数と行動の列が同じ（判定のための要求がない）。J10（runner の actor_logs と、保存する形の actors/*.jsonl で同じ観測と同じ判定）。たねのうらは受理（expected）、header のない対戦は L12 で undetermined（単局とバッチで同じ）
- 境界: 方策・行動生成・変異・集計・記録・reach・observe の部品に規則 7 の部品がない。runner が呼ぶのは `submit_evidence` 1 か所だけ

既存のテストは、版の数の期待値だけを規則 7・TOOL_VERSION 9 に更新しました（er9_evidence・p6・u_r3a・v0178_follow・v0179_follow・v3_3・reach・reach_v2）。判定の中身の期待値は変えていません。実行の結果は 13.7 です。

### 13.6 版・識別・形式・旧計画

| 項目 | 前 | 後 |
|---|---|---|
| パッケージの版 | 0.180.0 | 0.180.0（同じ） |
| `behavior_digest` | `08038e06…` | 同じ |
| `instrumentation_digest` | `d3436748…` | 同じ |
| `TOOL_VERSION` | 8 | 9 |
| 道具の識別（`tool_digest`） | `dbca28bd…`（26 ファイル） | `383e30c4…`（26 ファイル。変わった） |
| 判定の規則 | 6 | 7 |
| 計画・完了の形式 | `kyuura-vai-batch-plan/6`・`kyuura-vai-batch-complete/6` | 同じ |

- TOOL_VERSION 8 の計画は、道具の識別の違いで再開しません（既存の設計。移行・上書きしない）。既存の judge.json・集計・COMPLETE・台帳は変えていません。
- 検証用 AI の行動・契約の値の指紋（`test_verification_ai_v2_repeat`）は固定値のままです（13.7）。

### 13.7 実行したテストと結果

テストは 1 モジュールずつ別のプロセスで実行し、出力・終了コード・JUnit を証跡に保存しました。

| 実行 | 内容 | 結果 |
|---|---|---|
| run1-engine | E1〜E6 の最初の実行 | 失敗（エラー 5）。テストの側の誤り（カードの定義の属性名を `name` と書いた。正しくは `name_ja`）。拒否のコードと状態の比べは、その前の行までで通っていた |
| run2-engine | 属性名だけを直して再実行 | 6 件すべて成功 |
| run3-judge | 規則 7 のテストの最初の実行 | 失敗 5。(1) 停止方針の戻り値の 2 つ目（続ける理由の一覧）を空と期待したテストの誤り 2。(2) 本物の runner の候補で L4 が外れた 3（13.3 の「L4 の理由の範囲」。候補の理由に `face_down_reveal_not_evaluated` がなく、選べるものの側にだけあった） |
| run4-judge | テストの期待を直し、L4 を「候補か選んだ選べるもの」に直して再実行 | 31 件すべて成功 |
| run5-related | 新しい 2 モジュールと関係する 14 モジュール（secret_plan_v0_67・er9_evidence・batch_judge・batch・u_r3a・p6・p6_accepted・v3_1・v3_3・v0178_follow・v0179_follow・reach・reach_v2・v2_repeat） | 16 モジュール・256 件すべて成功（失敗・エラー・skip 0）。v2_repeat の行動・契約の値の指紋は固定値のまま |

判定例（証跡の `judge_examples.json`。構築盤面）:

- 本物の runner に通した構築盤面: たねでないうら → known_stop、たねのうら → 受理（expected。L1 で外れる）、header のない対戦 → undetermined（L12）。3 例とも、バッチの入口と単局の判定が同じ値
- 人工の負の例: 相手のうら L9・決定待ちの形 L3・うらの使い手 L4・すべてたね L11・観測なし L6・一覧にないカード L10。どれも undetermined で分類は evidence_missing_stop

全体のテスト・GUI・E2E・新しいバッチ・seed の探索・保存済み s1 への当て直しはしていません。

### 13.8 未確認

- 保存済みの s1 の 2 件に規則 7 を当てた結果（別の単位）。0.179.0 の記録なので、当て直しの単位が `7ee54b7` の基礎のファイルから `basis` を計算して渡す必要があります。
- 本物の new_game からの対戦で、規則 7 が known_stop を出すこと（今回は構築盤面だけ）。
- P4（受理後の処理の中の指定）が実際の対戦で起きるか。s1・r1 以外のバッチの同じコード。
- L4 の範囲を広げたので、s1・r1 の 8,904 送信への静的な事前評価（11 章。候補の理由だけで見た）と同じ結果になるかは、当て直しで確かめます。

### 13.9 保存済み s1 への当て直しに要る作業（次の単位）

1. 新しい証跡の単位で、s1 の 2 局と、同じ batch の全局の trace・`actors/*.jsonl`・`full_record.json` の header・judge.json を読む（元のファイルは書かない。前後の sha256 で確かめる）
2. `7ee54b7` の `kyuura_engine` の基礎のファイル（`cards.py`・`data/kyuura_cards.json`・`effects.py`・`engine.py`・`zones.py`）を `git show` で取り出し、`judge.lost_target_basis(root)` と同じ方式で値を計算する。今の値と同じことを確かめてから `basis` として渡す
3. 各局に `batch.judge_trace({"trace", "actor_logs", "record", "termination"}, basis=...)` を当て、規則 6 の judge.json と比べる。受け入れ条件は 6.4 節のとおり（変わるのは s1 の 2 行だけ、undetermined −2・known_stop +2、r1 の P3 は変わらない、完全な記録の command と入力の参照の一致）
4. 結果を別のファイルに書き、文書に記録する（集計・COMPLETE・台帳は変えない）

### 13.10 証跡

- `C:\dev\kyuura-engine-verification-vai\verifier\runs\lost-target-p1-judge-rule7\`: 事前計画、識別の前後（`identity_before.json`・`identity_after_engine_tests.json`・`identity_after.json`）、テストの出力・終了コード・JUnit（`tests/run1-engine`〜`run5-related`）、判定例、コマンドと失敗の記録
- 公開用は `public/runs/lost-target-p1-judge-rule7/summary.json`（件数と分類だけ）

## 14. 保存済みの s1・r1 への当て直し（2026-11-14。判定・比較・文書化だけ）

規則 7（実装 `38bf379`）を、保存済みの `vai-batch-s1`（30 局）と `vai-batch-r1`（4 局）の全局に当て直しました。保存済みの記録を規則 7 で再評価した結果です。新しい対戦の実績や、当時のバッチが known_stop として実行された証拠には数えません。判定が変わっても、当時の停止・続行・行動が変わったわけではありません（当時は規則 6 で判定し、undetermined の evidence_missing_stop は続ける方針でした）。

- 基点は `claude/lost-target-p1-judge-rule7` の `26e82b8`。専用の worktree で、新しいブランチ `claude/lost-target-p1-rejudge-s1` を作りました。
- 当て直しの時のエンジン・道具: 0.180.0（`behavior_digest` `08038e06…`）・TOOL_VERSION 9・`tool_digest` `383e30c4…`・判定の規則 7・形式 6。
- エンジン・judge・runner・方策・テストは変えていません。ゲーム・replay・API への要求はしていません。

### 14.1 元の証跡の保護

- 両バッチの全ファイル（s1 364・r1 72）の sha256 を、当て直しの前・後・限定確認の後に一覧にしました。3 つとも同じでした。
- 新しい判定は、証跡の `rejudged/` に別のファイルで書きました。trace・主体別の記録・完全な記録・judge.json・aggregate・COMPLETE・台帳・計画・マニフェストは書いていません。
- 旧計画の再開・バッチの再確定・旧ツールの集計の置き換えではありません。

### 14.2 判定の基礎（L12）の照合

| 項目 | s1 | r1 |
|---|---|---|
| 実行コミット（header.json の `engine.git_commit`） | `7ee54b7791c68e6246f55f1926b03e0ffc32f015` | `de81f642ec6b3ace9b748cc0c0a9e2f9727bc598` |
| 記録の `behavior_digest` | `67c4c15b…`（0.179.0。今と違う） | 同じ |
| 基礎の識別 `basis`（記録時） | `a871823d…` | `a871823d…` |
| 今の `lost_target_basis()` | `a871823d…` | 同じ |
| カードプールの前提（`card_pool` default・`card_data` が今の出どころと同じ） | 30 局とも一致 | 4 局とも一致 |

- 記録時のファイルは、公開のリモートのブランチに含まれるコミットから `git show <commit>:kyuura_engine/<file>` で取り出しました（実行していない）。
- それを `judge.lost_target_basis(root)` にそのまま渡しました。方式は `replay_record._digest`・`_normalized` と同じで、対象・並びは `LOST_TARGET_BASIS_FILES` です。
- 5 ファイル（cards.py・data/kyuura_cards.json・effects.py・engine.py・zones.py）は、どれも正規化 sha256 が今と同じでした。
- そのため、34 局すべてに `basis` を渡しました。basis を渡さなければ、対象の 2 件は L12 で外れます（undetermined のまま）。

### 14.3 結果

| | s1 規則 6 | s1 規則 7 | r1 規則 6 | r1 規則 7 |
|---|---|---|---|---|
| 送信 | 7,184 | 7,184 | 1,720 | 1,720 |
| expected | 7,176 | 7,176 | 1,719 | 1,719 |
| normal_rejection | 6 | 6 | 0 | 0 |
| undetermined | 2 | 0 | 1 | 1 |
| known_stop | 0 | 2 | 0 | 0 |

- 判定が変わった送信の行は 2 行だけでした。s1 の P1 の 2 件（S1-a・S1-b）が `use_power` で undetermined → known_stop になり、変わった項目は verdict と reasons だけです。
  - 新しい理由: `unsupported`・コード・`face_down_reveal_not_evaluated`・`evidence:`（固定の条件の文）
- 種類ごとの件数の差は、s1 の `use_power` の undetermined −2・known_stop +2 だけでした。
- 受理の中身の判定・終わり方の判定は 34 局とも同じでした。ほかの送信の行も同じです。
- undetermined の一覧から消えたのは、その 2 件（分類 evidence_missing_stop）だけです。加わったものは 0 です。
- r1 の P3（`answer_decision`）は undetermined のままです。L3（拒否のあとが決定待ち）で外れ、理由の先頭 `stop_condition_not_evidenced:` と分類 evidence_missing_stop も同じです。
- ほかの経路の対照: s1・r1 で、このコードの送信はこの 3 件だけでした。ほかのコードの拒否（s1 の normal_rejection 6）と受理は変わりません。
- メタデータの差は `rules_version` 6 → 7（34 局）だけで、judge.json の項目の並びは同じでした。判定の結果の差（上の 2 行）とは分けて数えています。
- 対象 2 件の照合（判定には使っていない）: 完全な記録の operations で、同じ operation_id の command（`use_pokemon_power`。rejected・同じ診断）の使い手・source・target・energy は、trace の候補と選んだ意味の参照と同じでした。本人の観測でも、source は主体の場のうらで、energy はその source についていました。

### 14.4 限定確認（人工の入力と、対象の記録のメモリ上の写し）

リポジトリのテストとコードは変えていません。証跡のスクリプトから、実際の判定関数に入力を渡しました（16 件すべて期待どおり）。

- L4 の実装は、候補の `reasons` と、選んだ意味（`meaning[].option`）の `reasons` だけを集めます。段の選べるもの（`stages[].options`）は読みません。
  - 選ばなかった選べるものだけに `face_down_reveal_not_evaluated` がある入力は L4 で外れ、undetermined のままでした。
  - 選んだ選べるものにあれば known_stop でした。
- basis の欠け・不一致: L12 で外れ、undetermined です。一致すれば known_stop です。
- 本人の観測の欠け・同じエピソードの前の受理（古い観測）・別の番・参照の不一致: L6・L8 で外れ、undetermined です。
- P3 の形: L3 で外れます。拒否のあとの形を P1 と同じにしても、種類で L4 に外れます。
- 保存済みの対象の行: basis ありで known_stop、basis なしで L12。観測の行を除くか重ねると L6、参照を変えると L8 です。
- 根拠が成り立たないときは、どれも理由の先頭が `stop_condition_not_evidenced:` で、分類は evidence_missing_stop でした。

### 14.5 前の実装の 2 つの変更の区別

規則 7 の実装（`38bf379`）には、性質の違う変更が 2 つあります。

1. **P1 の新しい根拠の登録**（規則 7 の本体）。この章の当て直しで、保存済みの s1・r1 への効果を確かめたのはこれです。
2. **単局の runner の判定（変異の実行の中）に、既存の ER9 の根拠（規則 6）を渡す接続の補完**。前は単局の判定に evidence を渡していませんでした。
   - この当て直しは逐次バッチの入口（`batch.judge_trace`）だけを使いました。バッチの入口は、もともと ER9 の根拠を渡していました。
   - そのため、単局の ER9 の判定の変化は、ここでは新たに確かめていません。

### 14.6 未確認と残件

- 未確認:
  - new_game からの対戦で、規則 7 が known_stop を出すこと
  - s1・r1 以外の保存済みのバッチの同じコード
  - 単局の runner での ER9 の根拠の受け渡しの変化（14.5）
  - P4（受理後の処理の中の指定）の実際の発生
- 残件:
  - P2（相手のうら）・P3（決定への回答）の根拠の登録（経路単位の鍵の判断を含む）
  - 規則 7 での新しいバッチを実行するか（別の判断）
- 証跡: `C:\dev\kyuura-engine-verification-vai\verifier\runs\lost-target-p1-rejudge-s1\`
  - 事前計画、識別、basis の取り出しと照合、前後の sha256、当て直しのスクリプトと出力、規則 6 と 7 の行の差、限定確認、コマンド
- 公開用は `public/runs/lost-target-p1-rejudge-s1/summary.json`（件数と分類だけ）です。
