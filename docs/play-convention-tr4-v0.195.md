# v0.195: エネルギー回収の 0 枚の答えのプレイ用の続行規約（開発用の集合 CS-KYUURA-PLAY-TR4@1）

2026-11-21。利用者が採用した[設計](er9-energy-retrieval-zero-design.md)の案 B「0 枚を受理して、エネルギー回収の使用を終える」を実装しました。

- **プレイ用の取り決めです。** 史実の裁定は確定していません。停止コード `UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE`（ER9）は、厳密側・既存の集合・初回の範囲の外の経路で active のままです。kyuura の論点 `UQ-ENERGY-RETRIEVAL-ZERO-CHOICE` も解決にしていません。
- **既定では有効になりません。** 省略したときの集合は `CS-KYUURA-CURRENT@1` のままです。`new_game(..., conventions="CS-KYUURA-PLAY-TR4@1")` のように明示的に選んだ対戦だけで当たります。
- CURRENT@1・LEGACY@1・S2A@1・PO@1・TR3@1 の ID・版・中身・照合値は変えていません（TR3@1 は `sha256:a7b800cf…` のまま）。
- 範囲は、エンジンの実装と構築盤面での検証までです。GUI の追従と、同じデッキ・seed・方策での規約採用後の比較対戦は別の単位です。
- 証跡: `kyuura-engine-verification-vai/verifier/runs/er9-zero-choice-v0195/`（事前計画・経路の確かめ・識別・テストの結果・判定・配布の確かめ・失敗と未確認）。

## 1. 基点・コミット・識別

| 項目 | 値 |
|---|---|
| 基点 | `claude/er9-zero-choice-design` の `a4863dc`（origin と一致。版 0.194.0。main に未取り込み）。公開の全ブランチの `pyproject.toml` に 0.195 以上はなかった |
| 作業 | worktree `C:\dev\kyuura-engine-lt79`、ブランチ `claude/er9-zero-choice-v0195` |
| コミット | `f521227`（実装と新しいテスト）・`93a9689`（生成物）・`fafbb83`（版を 0.195.0 にする。配布の確かめの固定コミット）・文書のコミット |

**識別の前後**（実測。証跡の `out/identity_before.json`・`identity_after_fix_93a9689.json`・`identity_after_version.json`・`dist/identity_installed.json`）

| 項目 | 前（0.194.0） | 修正のあと（版の前） | 後（0.195.0） |
|---|---|---|---|
| パッケージの版 | 0.194.0 | 0.194.0 | 0.195.0 |
| behavior_digest | `b636dd94…` | `b77f274b…` | `5cbd40af…`（導入物も同じ） |
| instrumentation_digest | `13c773a8…` | 同じ | 同じ |
| P1・P3・P2・規則 10 の basis | `341af16e…`・`e7ad631c…`・`cc467268…`・`aecf097e…` | `e1d389e7…`・`89d12d2e…`・`d652db24…`・`6d41f57f…` | 修正のあとと同じ |
| `TOOL_VERSION`・道具の識別・判定の規則 | 13・`be95aa1e…`・10 | 同じ | 同じ |
| 規約集合 | 5（CURRENT・LEGACY・S2A・PO・TR3） | 6（+ TR4 `sha256:15af975a…`） | 6 |

basis は `effects.py` を読むので変わりました（判定の規則・道具は変えていません）。保存済みの記録の当て直しは、記録の側の basis を渡す今までの方式のままです。

## 2. 使用の経路の見分け方（実装の前提の確かめ）

回収の決定を再開する時点の状態を構築盤面で調べました（証跡の `out/probe_paths.json`。観測の「使ったプレイヤー」や答えの時点のスタジアムは使っていません）。

| 経路 | `TrainerInUse` の user・via | `trainer_stack` | このカードの `play_trainer` のあとの出来事 | 扱い |
|---|---|---|---|---|
| 手札からの通常の使用（PMCG1-076・再録の版 4 つ） | None・None | 空 | `discard_from_hand` だけ | **規約を当てる** |
| 錯乱ジムの「おもて」（持ち主が使う） | None・None | 空 | `coin_flip`・`chaos_check`・`discard_from_hand` | ER9 のまま |
| 錯乱ジムの「うら」で相手がかわりに使う | None・**1** | 空 | `chaos_check`・`chaos_answered`… | ER9 のまま |
| サイキックコントロールで相手のトラッシュから使う | **0**・**外側のカード** | **1** | （`play_trainer` に `via`・`source_zone`） | ER9 のまま |
| ［ちえくらべ］を使うかを聞いたあと | None・None | 空 | `trainer_reaction_answered`… | ER9 のまま（初回の範囲の外） |
| リムーブ禁止ジムが場にある | None・None | 空 | `discard_from_hand` だけ | **通常の使用**（規約を当てる） |

- 錯乱ジムの「おもて」は、使用中の記録が通常の使用と同じです。区別は状態のログのこの使用の `chaos_check` で、書き出し・復元のあとも同じ結果になることを確かめました。
- **設計の訂正:** リムーブ禁止ジムの追加の条件は、印刷の文面のとおり「エネルギーリムーブ」「超エネルギーリムーブ」だけに当たり、エネルギー回収には当たりません（`stadium_trainer_cost` が名前で決める）。設計 3.3 の「リムーブ禁止ジムの追加の条件のあと」の経路はエネルギー回収にはなく、場にあっても通常の使用です。設計 4 章の適用条件の「リムーブ禁止ジムが場にない」は採らず、使用の時点の出来事（スタジアムの追加の条件のトラッシュ `stadium_card`）で決めました。
- 既存の情報（状態の使用中の記録とログ）で経路を特定できたので、保存形式は変えていません。

判定は `effects.retrieval_from_hand(state, use)`（状態を変えない）:

1. `state.trainer_in_use` がこのカードで、持ち主が使っている（`user` が None）・`via` が None・`trainer_stack` が空
2. このカードの最後の `play_trainer` が、使うプレイヤーの手札から（`via`・`source_zone` がない）
3. そのあとに `chaos_check`・`chaos_answered`・`trainer_reaction_answered`・`stadium_card` の付いた `discard_from_hand` がない

## 3. 実装

| 箇所 | 変更 |
|---|---|
| `conventions.py` | 続行規約 `PC-ENERGY-RETRIEVAL-ZERO@1`（層 continuation・user_agreed・場面 ER9 の 1 つ。照合値 `sha256:42427e75…`）と集合 `CS-KYUURA-PLAY-TR4@1`（usage development・halts_at_undecided。TR3@1 の 23 規約 + 1）。`IMPLEMENTED_CONTINUATIONS` に加えた |
| `effects.py` | `DiscardFromHandThenRetrieveEnergy.resume` の空の答えで、`retrieval_from_hand` が真なら `continuation_for(state, self.ZERO_CHOICE[0])` を引き、あれば `record_application(player, available)` を書いて戻る。なければ今と同じ `UnsupportedError`（ER9） |
| `tests/log_audit.py` | `s2a_problems` に TR4 の表（規約・場面・項目 `player`・`available`）と記録の場所の確かめ |

- 超エネルギー回収は同じ `resume` を通りますが、停止コードが SR2 で、どの集合にもその場面の規約がないので、今と同じ SR2 で止まります。
- 候補・入力・`check` は変えていません（`answer_decision`・`may_stop_later`・`continuation_not_evaluated`、数 0〜min(2, 数)・`decline` 真、空の答えは有効）。`engine.py`・`resolution/`・`legal_actions.py` は変えていません。カード ID の分岐はありません。

### 3.1 0 枚を受理したときの状態とログ（TR4）

- 費用でトラッシュしたカードはトラッシュのままです。手札は回収の答えの前と同じで、選べたエネルギーもトラッシュのままです。
- 使ったエネルギー回収は、既存の使い終える処理（`_finish_trainer`）で持ち主のトラッシュに置かれます。トラッシュはこの 1 枚だけ増えます。
- 決定はなくなり、`trainer_in_use` は空、段階は同じ番の MAIN です。その番にまだつけていないエネルギーをつけられることも確かめました。乱数は使いません。
- 公開ログは `convention_applied`（`convention`・`version`・`scene`・`code`・`player`・`available`）と `discard_trainer` が 1 回ずつで、`retrieve_energy` はありません。どの見る人（本人・相手・観戦者）にも同じ 2 つが見えます。
- 厳密側（CURRENT@1・TR3@1）では、同じ盤面の同じ答えが今と同じ ER9 の拒否で、状態・乱数・ログは変わりません。

## 4. 生成物

- 停止の方針の台帳（`docs/stop-policy-classification.json`）: 採用の記録 `AGR-PLAY-TR4-SET`・`AGR-PLAY-TR4-ENERGY-RETRIEVAL-ZERO`、`DEC-UP-TO-ZERO` を partly_agreed（ER9 の 1 場面の手札からの使用だけ）、`UPDATES` の 0.195.0。そのほかの差は、`effects.py` の編集で動いた停止箇所の行番号と新しいテストの参照です。
- 共通規約の設計案（`docs/play-policy-family-plan.json`）: 別の仕様案の採用 `PC-ENERGY-RETRIEVAL-ZERO`（関連の候補 `PC-UP-TO-ZERO` は proposal のまま）と、ER9 の場面の採用の印。
- TR3 のときは採用の記録が後の単位で入力に写されました（[台帳の差の調査](stop-ledger-drift-audit.md) 8 章）。今回は同じ単位で入れました。
- 実行時の場面の索引・同梱の記録（`convention_records.json`）・診断のカタログは変わっていません（`--check` が exit 0）。

## 5. テストと検証（設計 5 章の V1〜V12）

新しいテスト `tests/test_play_convention_tr4_v0_195.py`（19 件。構築盤面）。登録だけを入れた段階では、0 枚の受理を期待する 8 件だけが ER9 で失敗し、ほかは通りました（証跡の `out/tests_before_fix/`）。

| id | 結果 |
|---|---|
| V1 厳密側 | CURRENT@1・TR3@1 で ER9（`unresolved_ruling`）。決定は待ったまま、状態・乱数・ログは変わらず、費用のトラッシュは残る |
| V2 規約有効の 0 枚 | TR4 で受理。`convention_applied` 1 つ（`player`・`available`）・`discard_trainer`。`retrieve_energy` なし・決定なし・MAIN・同じ番にエネルギーをつけられる |
| V3 費用・移動 | 費用はトラッシュのまま。手札は答えの前と同じ。トラッシュはこのカードの分だけ増える |
| V4 1 枚・2 枚 | 両方の集合で同じログ・手札・トラッシュ・乱数。規約の記録なし |
| V5 答え直し | 上限を超える数・重複・費用のカード・手札・相手のトラッシュ・相手の答えは今と同じコードで拒否、状態は変わらず、そのあと 0 枚が受理される（厳密側は ER9） |
| V6 合法手 API | 候補・入力・`check` は両方の集合で同じ値。`submit` は TR4 が accepted（全員のログに 2 つ増える）、厳密側が rejected（どの見る人のログも変わらない） |
| V7 ER10・ポケモンタワー | 両方の集合で今と同じ使う前の停止 |
| V8 H4・SR2 | 両方の集合で今と同じ停止 |
| V9 手札以外の経路 | 錯乱ジムの「おもて」・「うら」でかわりに使う・サイキックコントロール・［ちえくらべ］を聞いた使用は、両方の集合で ER9。1 枚以上は今まで通り。リムーブ禁止ジムが場にあるときは通常の使用として受理 |
| V10 再録の版 | GD1-014・GD4-014・GD6-014・QSG-047 は PMCG1-076 と同じ（カードのほかは同じ出来事・枚数） |
| V11 集合と旧記録・judge | 下の 5.1 |
| V12 ログの監査 | `s2a_problems` が記録を通し、項目の追加・プレイヤーの違い・`available` 0・`discard_trainer` のあとへの移動を問題として出す |

### 5.1 judge（V11）

- **単局・バッチ:** 構築盤面のスナップショットを本物の runner（既存の `FixtureRunner` の方式）で復元し、0 枚を答える選び手で 1 回送りました。
  - TR4: 受理。逐次バッチの入口 `batch.judge_trace` は `expected` 1 件（理由なし・undetermined 0・known_stop なし）。`recorded_stop_evidence` は None で、ER9 の既知の停止に数えません。単局の runner の判定（変異の実行の中の判定）も `expected`。
  - 厳密側: 拒否。`judge_trace` と単局の判定は `known_stop`（根拠は規則 6 の ER9）で、今と同じです。
- **旧記録:** TR3 の本実行で ER9 が返った 3 局（C2）の保存記録に、今の判定を当て直しました（証跡の `out/rejudge_old_er9.json`。記録のファイルは前後で同じ）。3 件とも保存した行と同じ `known_stop`（根拠 ER9）で、3 局のほかの行も 1 つも変わっていません。
- 判定の規則（`RECORDED_STOP_CONDITIONS`・`JUDGE_RULES_VERSION` 10）は変えていません。追加の変更が要る点は見つかりませんでした。受理した 0 枚の答えは、受理の送信の通常の判定（`expected`）になります。

### 5.2 そのほかのテスト・検査

- 標準の 15 モジュールと関連の 34 モジュール（新しいテスト・規約・集合・台帳・設計案・エネルギー回収・超エネルギー回収・再録・H4・スタジアム・ちえくらべ・合法手・判定・観測など）: 49 モジュール・1,407 テストがすべて成功（1 モジュール 1 プロセス）。
- 生成の検査 15（`--check`・`--sites`）: すべて exit 0。`--sites` の出力は基点と同じ（`ABE1CBFA…`）。前後で git status は同じ。
- 上の 49 モジュールと生成の検査は、生成物のコミット `93a9689` の木（版 0.194.0）で実行しました。版を上げたあと（`fafbb83`）は、版を確かめる `test_preset_decks_v0_20` と、版を読む生成の検査 6 つ（台帳・設計案・識別・診断と再生の API・状態のスナップショット・同梱の記録）を実行し直し、すべて成功しました。
- 全体のテストは実行していません。

## 6. 配布の確かめ（固定コミット `fafbb83`）

1. `git ls-tree` の `kyuura_engine` の数は 62 で、基点と同じでした。パッケージの差は `__init__.py`・`conventions.py`・`effects.py` です。`pyproject.toml` の差は版の 1 行で、依存は増えていません。
2. `git archive --format=tar -o` で固め、Python の `tarfile`（`filter='data'`）でリポジトリの外に展開しました。`pip wheel --no-deps` は exit 0 で、`kyuura_engine-0.195.0-py3-none-any.whl` ができました。`scripts/check_distribution.py --wheel` も exit 0 です（required=62・problems=0）。
3. スモーク用のスナップショットは、同じ展開から作りました（厳密側・TR3・TR4・TR4 の錯乱ジムの「おもて」・TR4 の再録の版の 5 つ）。旧版のスナップショットは使っていません。
4. リポジトリの外の新しい venv に、その wheel を `pip install --no-deps` で導入しました（editable でない。入ったのは kyuura-engine 0.195.0 と pip だけ。62 ファイル）。
5. スモーク（`smoke_v0195.py`。tests を使わない）: 厳密側・TR3・TR4 の錯乱ジムの「おもて」は 0 枚で ER9、TR4・再録の版は受理（`convention_applied`・`discard_trainer`）。どれも 1 枚は受理（`retrieve_energy`・`discard_trainer`）、候補・入力・check は同じで、submit だけが違います。ソースの木と導入物で、結果（`result_sha256` `f36de15c…`）と識別が同じでした。

## 7. 残る作業

- **GUI**（別の単位）: 集合の選択に `CS-KYUURA-PLAY-TR4@1` を加えること、受理した 0 枚の答えの表示（`convention_applied` の表示）。応答の形は変えていません（候補・入力・`check` は同じ）。
- **比較対戦**（別の単位）: 同じデッキ・seed・方策で TR4 を選んだ対戦の、0 枚の答えの受理の数・その後の進み方・終わり方・完走の割合・時間・量。
- 初回の範囲の外の経路（錯乱ジム・サイキックコントロール・［ちえくらべ］を聞いた使用）を含めるかは、未決のままです（設計の D4）。
- 共通の案 PC-UP-TO-ZERO（ほかの 12 場面）は proposal のままです。

## 8. 失敗・修正・再実行・未確認

- 失敗と修正（製品のコードの期待を変えて通したものはありません。前の出力は証跡に残した）:
  1. 新しいテストの 1 回目（修正の前）: TR4 を知らない 19 件の失敗のほか、構築盤面に対戦の初めからログを組み立てる `log_problems` を当てた 2 件が失敗しました。テストの側を、規約の記録の監査 `s2a_problems` と不変条件に直しました。
  2. 経路の判定の 1 回目の編集: ログの項目名を `stadium` と書いていました（正しくは `stadium_card`）。コミットの前に直し、規約の文も直して照合値を計算し直しました。同じ編集で `@dataclass` の下に関数を入れてしまい、構文の誤りになったので直しました。
  3. 新しいテストの 1 回目: `AttachEnergy` の対象にポケモンの番号を渡していました（正しくはカードの uid）。テストを直しました。
  4. 生成の検査: 実装のあとに台帳と設計案の `--check` が exit 1（基点では 0）。採用の記録を入力に加え、`--write` で作り直しました。
  5. コミット: PowerShell のヒアストリングを `git commit -F -` に渡せず、何もコミットされませんでした。メッセージのファイルで入れ直しました。
  6. 配布の確かめの 1 回目: スモークの道具が、鍵が組の辞書を JSON にできず exit 1。道具を直して最初から実行し直しました（1 回目の出力は `out/dist_attempt1/`。wheel の sha256 は作るたびに違う）。
- 未確認:
  - `new_game` からの回収の決定への到達（構築盤面だけ）と、対戦の初めからのログの監査（`log_problems`）
  - GUI の画面
  - 全体のテスト
  - 拒否の直後のエンジンの内部状態の照合値（保存記録にない）
