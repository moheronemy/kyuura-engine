# v0.196: エナジーへんかんの 0 枚の答えのプレイ用の続行規約（開発用の集合 CS-KYUURA-PLAY-TR6@1）

2026-11-21。利用者が採用した[設計](h4-recover-zero-design.md)の案 B「0 枚を受理して、何も手札に加えずにワザの続きへ進む」を実装しました。

- **プレイ用の取り決めです。** 史実の裁定は確定していません。停止コード `UNRESOLVED_RECOVER_ZERO_ENERGY`（H4）は、厳密側・既存の集合・対象の外の経路で active のままです。kyuura の論点 `UQ-ENERGY-CONVERSION-ZERO` も解決にしていません。
- **既定では有効になりません。** 省略したときの集合は `CS-KYUURA-CURRENT@1` のままです。`new_game(..., conventions="CS-KYUURA-PLAY-TR6@1")` のように明示的に選んだ対戦だけで当たります。
- CURRENT@1・LEGACY@1・S2A@1・PO@1・TR3@1・TR4@1 の ID・版・中身・照合値は変えていません（TR3@1 は `sha256:a7b800cf…`、TR4@1 は `sha256:15af975a…` のまま）。
- 集合の名前は TR6 です。TR5 は ER10 の設計（[er10-energy-retrieval-without-target-design.md](er10-energy-retrieval-without-target-design.md)）で案として使った名前なので、混同を避けて使いません。登録の前に、規約 ID・集合 ID がコードとどのブランチの履歴にもないことを確かめました。
- 範囲は、エンジンの実装と構築盤面での検証までです。GUI の追従と、規約採用後の比較対戦は別の単位です。
- 依頼の文面の `docs/h4-recover-zero-energy-design.md` は、基点では `docs/h4-recover-zero-design.md`（と `.json`）です。その文書の案 B を実装しました。
- 証跡: `kyuura-engine-verification-vai/verifier/runs/h4-zero-v0196/`（事前計画・前提の確かめ・識別・テストの結果・判定・旧記録の当て直し・配布の確かめ・失敗と未確認）。

## 1. 基点・コミット・識別

| 項目 | 値 |
|---|---|
| 基点 | `claude/h4-recover-zero-design` の `4caa8b1`（`4caa8b1049af526dfa4e5b71c8b66d0077d8cb6f`。origin と一致。版 0.195.0）。公開の全ブランチの `pyproject.toml` に 0.196 以上はなく、タグもなかった |
| 作業 | worktree `C:\dev\kyuura-engine-lt84`、ブランチ `claude/h4-zero-v0196` |
| コミット | `cd69bc7`（実装と新しいテスト）・`2738acc`（生成物）・`7f7712a`（版を 0.196.0 にする。**配布の確かめの固定コミット** `7f7712acebd022ac5c9a7d5a346b89d3a2ab9690`）・文書のコミット |

**識別の前後**（実測。証跡の `out/identity_before_4caa8b1.json`・`identity_after_fix.json`・`identity_after_version.json`・`dist/identity_installed*.json`）

| 項目 | 前（0.195.0） | 修正のあと（版の前） | 後（0.196.0） |
|---|---|---|---|
| パッケージの版 | 0.195.0 | 0.195.0 | 0.196.0 |
| behavior_digest | `5cbd40af…` | `70ca5ba9…` | `4a8edcf0…`（導入物も同じ） |
| instrumentation_digest | `13c773a8…` | 同じ | 同じ |
| P1・P3・P2 の basis | `e1d389e7…`・`89d12d2e…`・`d652db24…` | 同じ | 同じ |
| 規則 10（H4）の basis | `6d41f57f…` | `b3864eca…` | `b3864eca…` |
| `TOOL_VERSION`・道具の識別・判定の規則 | 13・`be95aa1e…`・10 | 同じ | 同じ |
| 計画・完了の形式・状態の書き出しの形式 | `kyuura-vai-batch-plan/7`・`-complete/7`・形式 35 | 同じ | 同じ |
| 規約集合 | 6（CURRENT・LEGACY・S2A・PO・TR3・TR4） | 7（+ TR6 `sha256:aa53bc52…`） | 7 |

規則 10 の basis は `resolution/programs.py` を読むので変わりました（判定の規則・道具は変えていません）。旧記録の扱いは 5.2 節です。

## 2. 前提の確かめ（実装の前。構築盤面）

修正の前のエンジンで、対象の経路が同じ回収の決定と再開先を使い、メタモンの［へんしん］と区別できることを確かめました（証跡の `out/probe_premise_before.json`）。

| 経路 | 決定 | 再開先 | `copied` | ワザを使ったポケモンの印刷のカード | 0 枚（修正の前） | 1 枚 |
|---|---|---|---|---|---|---|
| ゴース（PMCG3-029）自身の［エナジーへんかん］ | `recover_energy`・最小 0・最大 2 | `attack` | なし | PMCG3-029（ワザのカード） | H4・状態は同じ | `recover_energy` → 自分に 10 → 番の終わり |
| ピッピ（PMCG1-067）の［ゆびをふる］→ 相手のゴースのワザ | 同じ | 同じ | `(PMCG3-029, 1)` | PMCG1-067（宣言したワザのカード。効果の型 `CopyOpponentAttackEffect`） | 同じ | 同じ |
| ピクシー（PMCG2-044）の［ゆびをふる］→ 相手のゴースのワザ | 同じ | 同じ | `(PMCG3-029, 1)` | PMCG2-044（同上） | 同じ | 同じ |
| メタモン（PMCG3-042）の［へんしん］で持つ［エナジーへんかん］ | 同じ | 同じ | なし | **PMCG3-042**（ワザのカードではない） | 同じ | 同じ |
| トラッシュにエネルギーなし（H5） | 決定なし | — | — | — | — | 自分に 10 |

決定の形と再開先は 3 経路で同じでした。区別は状態の値だけで決まります。宣言したワザと処理しているワザの組、宣言したワザの効果の型、ワザを使ったポケモンの印刷のカードを見れば足ります。前提が成り立ったので、範囲を変えずに実装しました。

## 3. 実装

| 箇所 | 変更 |
|---|---|
| `conventions.py` | 続行規約 `PC-ENERGY-CONVERSION-ZERO@1`（層 continuation・user_agreed・場面 H4 の 1 つ。照合値 `sha256:6a35ebb8…`）と集合 `CS-KYUURA-PLAY-TR6@1`（usage development・halts_at_undecided。TR4@1 の 24 規約 + 1。照合値 `sha256:aa53bc52…`）。`IMPLEMENTED_CONTINUATIONS` に加えた |
| `resolution/programs.py` | `RecoverEnergy._zero_convention_path`（状態を変えない。カード ID の定数で分けない）と、`RecoverEnergy.resume` の空の答えの分岐。H4 の例外を作り、対象の経路なら `continuation_for(state, H4)` を引く。あれば `record_application(player, available)` を書いて戻り、なければ作った例外を投げる（今と同じ H4） |
| `tests/log_audit.py` | `s2a_problems` に TR6 の表（規約・場面・項目 `player`・`available`。エナジーへんかんのワザの一覧 `PMCG3-029#1` を監査が独立に持つ）と記録の場所の確かめ |
| `tests/test_recover_zero_energy_premise_v0_187.py` | H4 の定数の箇所に `conventions.py` の場面の登録を 1 つ加えた（その定数を場面に持つ規約は TR6 の 1 件だけであることも確かめる）。投げる箇所は `RecoverEnergy.resume` の 1 つのままで、例外を作る呼び出しが 1 つ・規約が当たらないときに投げる |

**対象の経路**（`_zero_convention_path`。決定を再開する時点の状態で決める）:

1. 元のワザ: 宣言したワザと処理しているワザが同じで、ワザを使ったポケモンの印刷のカードがそのワザのカード
2. ゆびをふる: 宣言したワザの効果の登録の型が `CopyOpponentAttackEffect`（ピッピ・ピクシー）で、ワザを使ったポケモンの印刷のカードが宣言したワザのカード、処理しているワザ（`copied`）のカードが相手のバトル場のポケモンの印刷のカード

**対象の外**（今と同じ H4）:

- メタモンの［へんしん］で持つワザ（印刷のカードがワザのカードでない）
- ほかのワザのコピー（カスミのコダックのちょうのうりょくなど。効果の型が違う）
- ゆびをふるで、相手が［へんしん］などで持つワザを選んだとき

**変えないもの:**

- 候補・入力・`check`（`answer_decision`・`may_stop_later`・`continuation_not_evaluated`、数 0〜2・`decline` 真、空の答えは有効）
- 1 枚以上の答え・先読み（1 枚以上だけを試す）
- H5（決定なし）・ポケモンタワー・［アレルギーほうし］（要素を処理しない）
- ER9・ER10、ほかの回収のワザ（最小 1 以上の `RecoverEnergyByHeads`・`RecoverSpecialEnergy` は H4 を投げない）
- API と保存形式。`engine.py`・`legal_actions.py`・judge は変えていません

### 3.1 0 枚を受理したときの状態とログ（TR6）

- 何も手札に加えません。手札とトラッシュは回収の答えの前と同じで、選べたエネルギーはトラッシュのままです。ワザの費用でエネルギーをトラッシュしないので、費用で変わるものもありません。
- 決定は閉じ、既存の続きで次の要素（ワザを使った、またはコピーしたポケモンに 10 ダメージ）を処理します。そのあとのきぜつの確かめと番の進行も既存の処理で、1 枚の答えのときと同じ出来事が続きます（番の終わり → 相手の番）。
- 自分へのダメージできぜつする盤面（ダメージ 40・HP 50）でも、自分へのダメージのあとの出来事と決定は 1 枚の答えと同じでした。
- 公開ログは `convention_applied`（`convention`・`version`・`scene`・`code`・`player`・`available`）を 1 回書き、すぐあとに `damage`（`target: self`）が続きます。`recover_energy` は書きません。どの見る人（本人・相手・観戦者）にも同じに見えます。乱数は使いません。
- 厳密側（CURRENT@1・TR3@1・TR4@1）では、同じ盤面の同じ答えが今と同じ H4 の拒否です。状態・乱数・ログ・決定は変わらず、どの見る人の観測も変わらず、同じ決定に 1 枚以上で答え直せます。

## 4. 生成物

- 停止の方針の台帳（`docs/stop-policy-classification.json`）:
  - 採用の記録 `AGR-PLAY-TR6-SET`・`AGR-PLAY-TR6-ENERGY-CONVERSION-ZERO` を加えました。
  - `DEC-UP-TO-ZERO` の partly_agreed に H4 の 1 場面を加えました（PF-UP-TO-ZERO の残りは 11 件）。
  - `UPDATES` に 0.196.0 を加えました。
  - そのほかの差は、実装の前に作り直した値との比べで、次の 3 つだけでした（証跡の `out/ledger_diff_impl.json`。56 項目）:
    - `programs.py`・`conventions.py` の編集で動いた停止箇所と内部ガードの行番号
    - 新しいテストの参照
    - H4 の `implementation_sites`・`current_stop` に加わった `conventions.py` の場面の登録（TR4 の前例と同じ）
- 共通規約の設計案（`docs/play-policy-family-plan.json`）: 別の仕様案の採用 `PC-ENERGY-CONVERSION-ZERO`（関連の候補 `PC-UP-TO-ZERO` は proposal のまま）と、H4 の場面の採用の印を加えました。
- 実行時の場面の索引・同梱の記録（`convention_records.json`）・診断のカタログは変わっていません（`--check` が exit 0）。

## 5. テストと検証（設計 6 章の S1〜S9）

新しいテスト `tests/test_play_convention_tr6_v0_196.py`（16 件。構築盤面と本物の runner）。

- 登録だけを入れた段階では、0 枚の受理を期待する件が H4 で失敗しました。厳密側・へんしん・H5・タワー・アレルギーほうし・ほかの場面・厳密側の判定は通りました（証跡の `out/tests_before_fix/`）。
- この段階でテストの誤り（送信の結果の診断の読み方）が 1 つ見つかり、直しました。

| id | 結果 |
|---|---|
| S1 厳密側 | CURRENT@1・TR3@1・TR4@1 × 元のワザ・ピッピ・ピクシーで H4（`unresolved_ruling`）。状態・乱数・ログ・決定は同じで、同じ決定に 1 枚で答え直して受理 |
| S2 規約有効の 0 枚 | TR6 の元のワザで受理。`convention_applied` 1 つ（`player` 0・`available` 2）・自分に 10・`recover_energy` なし・手札とトラッシュは同じ・決定なし・相手の番。不変条件とログの監査は問題 0 |
| S3 1 枚以上の対照 | 両方の集合で 1 枚・2 枚のログ・手札・トラッシュが同じ。規約の記録なし。重なり・数の超過は今と同じコードで拒否され、そのあと 0 枚が受理される |
| S4 コピーの経路 | ピッピ・ピクシーの［ゆびをふる］で S2 と同じ形（コピーした側に 10・コピーした側の手札とトラッシュは同じ）。回収の決定までは厳密側と同じログ・乱数・決定（`copied` あり）。メタモンの［へんしん］は TR6 でも H4 で、状態は同じ |
| S5 対象 0 枚 | トラッシュにエネルギーなし（H5）・ポケモンタワー・［アレルギーほうし］は、両方の集合で決定なし・`convention_applied` なし |
| S6 自分へのダメージできぜつ | ダメージ 40 のゴースで、0 枚（TR6）と 1 枚の、自分へのダメージのあとの出来事・決定が同じ（`knock_out` をふくむ） |
| S7 旧記録との互換 | 既存の集合の照合値は同じ。保存記録の判定は下の 5.2 |
| S8 ほかの場面 | TR6 でもエネルギー回収の 0 枚は TR4 の規約で受理、ER10 は使う前の停止（TR4 と同じ）。ほかの「最大N」のコード・SR2 は TR6 に規約がない。最小が 1 以上の回収の要素は、既存の前提のテスト（`test_only_recover_energy_suspends_with_min_zero`）で、0 枚の決定を出さないことを静的に確かめた（構築盤面では確かめていない） |
| S9 合法手 API とログの監査 | 3 経路とも、候補・入力・`check` は両方の集合で同じ値（`recover_energy`・数 0〜2・`decline` 真・有効）。`submit` は TR6 が accepted（どの見る人のログにも `convention_applied`・`damage` が増える）、厳密側が rejected（H4・決定待ち。どの見る人のログも変わらない）。ログの監査は、項目の追加・プレイヤーの違い・`available` 0・自分へのダメージのあとへの移動を問題として出す |

### 5.1 judge（本物の runner と judge_trace）

構築盤面のスナップショットを本物の runner（`RecordedFixtureRunner`。記録の header あり）で復元し、0 枚を 1 回答える選び手で送りました。元のワザ・ピッピ・ピクシーの 3 経路です。

- **TR6:** 受理。逐次バッチの入口 `batch.judge_trace` の行は `expected`（コードなし・undetermined 0・known_stop なし）。単局の runner の判定（変異の実行の中）も `expected` です。
- **厳密側（CURRENT@1）:** 拒否。`judge_trace` と単局の判定は既存の規則 10 の `known_stop`（根拠の条件 `KNOWN_STOP_EVIDENCE` の H4）で、今と同じです。
- 判定の規則・`TOOL_VERSION` は変えていません。期待と違う判定はありませんでした。

### 5.2 保存済みの TR3 の 5 件（旧記録）

TR3 の先行（`-p3` g001。4 件）と本実行（`-m3` g003。1 件）の保存記録に、判定を当て直しました（`batch.judge_trace`。別の出力だけに書き、原本は変えていない。記録のファイルは前後で同じで、局の `files.sha256.json` とも一致）。

| 評価のソース | 規則 10 の R11 の道 | H4 の 5 行 | ほかの行 |
|---|---|---|---|
| 記録を作ったソース（実行コミット `891e1fb`。0.194.0。識別が記録と同じ） | (b) 記録の behavior_digest が評価のソースと同じ | 5 行とも `known_stop`（保存した行と同じ） | 差 0 |
| 基点 0.195.0（`4caa8b1`。この版の変更の前） | (b) は不成立（behavior が違う） | 5 行とも `undetermined`（R11） | 差 0 |
| 0.196.0（`7f7712a` の木） | (b) は不成立 | 5 行とも `undetermined`（R11） | 差 0 |
| 0.196.0 に `basis_r`（`891e1fb` のファイルから計算した `aecf097e…`）を渡す | (a) は不成立（今の基礎 `b3864eca…` と違う） | 5 行とも `undetermined`（R11） | 差 0 |

- **既存の手順（記録時の識別と basis。[判定の規則 10 の設計](verification-ai-recover-zero-energy-design.md) 9.2 節）では、5 件とも `known_stop` が保たれます。**
- 今のエンジンで当て直すと R11 で `undetermined` になります。ただし基点の 0.195.0 ですでにそうでした。理由は、v0.195 で `effects.py`（規則 10 の基礎のファイル）が変わったことです。この版の変更が起こしたことではありません。
- 規則 10 は「基礎が今と同じときだけ根拠にする」設計なので、judge は緩めていません。今のエンジンでも旧記録を `known_stop` として当て直すには、基礎の変化を扱う別の判断（今回の範囲外）が要ります。

### 5.3 そのほかのテスト・検査

- 標準の 15 モジュールと関連の 35 モジュールは、50 モジュール・1,423 テストがすべて成功しました（1 モジュール 1 プロセス）。関連のモジュールは、新しいテスト・規約・集合・台帳・設計案・エネルギー回収・H4・規則 10・スタジアム・合法手・判定・観測などです。
- 生成の検査 15（`--check`・`--sites`）は、すべて exit 0 でした。`--sites` の出力は基点と同じ（`ABE1CBFA…`）で、前後で git status は同じでした。
- 上の 50 モジュールと生成の検査は、生成物のコミット `2738acc` の木（版 0.195.0）で実行しました（約 1,680 秒）。
- 版を上げたあと（`7f7712a`）は、版を確かめる `test_preset_decks_v0_20` と、規約・識別・サイドの順番・TR6 の 4 モジュール、生成の検査 14 を実行し直しました。すべて成功です。
- 文書のコミットのあと（`358fd17`）にも同じ 50 モジュール・生成の検査を実行し、すべて成功しました（約 1,670 秒）。`--sites` の差 1 つは 8 章の 7 で直しました。
- 全体のテストは実行していません。

## 6. 配布の確かめ（固定コミット `7f7712a`）

1. `git ls-tree` の `kyuura_engine` の数は 62 で、基点と同じでした。パッケージの差は `__init__.py`・`conventions.py`・`resolution/programs.py` です。`pyproject.toml` の差は版の 1 行で、依存は増えていません。
2. `git archive` で固め、Python の `tarfile`（`filter='data'`）でリポジトリの外に展開しました。`pip wheel --no-deps` は exit 0 で、`kyuura_engine-0.196.0-py3-none-any.whl`（sha256 `236df5f5…`）ができました。`scripts/check_distribution.py --wheel` も exit 0 です（required=62・problems=0）。
3. スモーク用のスナップショット 7 つは、同じ展開から作りました（厳密側の元のワザ・ゆびをふる、TR4 の元のワザ、TR6 の元のワザ・ピッピ・ピクシー・メタモン）。旧版のスナップショットは使っていません。
4. リポジトリの外の新しい venv 2 つに、その wheel を editable でなく導入しました。どちらも入ったのは kyuura-engine 0.196.0 と pip だけで、62 ファイルです。
   - 1 つ目: `pip install --no-deps <wheel>`。導入の記録 `direct_url.json` の `archive_info.hash` が wheel の完全な sha256 と同じでした。
   - 2 つ目: 完全なハッシュを書いた要求ファイルで `pip install --no-deps --require-hashes -r`
5. スモーク（`smoke_v0196.py`。tests を使わない）:
   - 厳密側・TR4・TR6 のメタモンは、0 枚で H4（状態は同じ）でした。
   - TR6 の元のワザ・ピッピ・ピクシーは、0 枚を受理しました（`convention_applied` → 自分に 10・`recover_energy` なし・手札とトラッシュは同じ・決定なし・相手の番）。
   - どれも 1 枚は受理されました（`recover_energy` → `damage`）。候補・入力・check は同じで、submit だけが違います。
   - ソースの木と 2 つの導入物で、結果（`result_sha256` `76909cd2…`）と識別（behavior `4a8edcf0…`・instrumentation `13c773a8…`）が同じでした。

## 7. 残る作業

- **GUI**（別の単位）: 集合の選択に `CS-KYUURA-PLAY-TR6@1` を加えることと、受理した 0 枚の答えの表示（`convention_applied` の表示）です。応答の形は変えていません（候補・入力・`check` は同じ）。
- **比較対戦**（別の単位）: 同じデッキ・seed・方策で TR6 を選んだ対戦の、0 枚の答えの受理の数・その後の進み方・終わり方・時間・量。
  - 2026-11-21: 旧 TR3 で H4 が出た C3 の 2 局（seed 9006・9009）で、TR4@1 と TR6@1 を比べました（4 局完了・2 組とも MATCHED）。TR4 の H4 の拒否が、TR6 では受理され、回収せずに自分への 10 ダメージと後続の処理へ進むことを確かめました: [H4 の TR4／TR6 比較対戦](history/h4-tr4-tr6-comparison.md)
- 今のエンジンで旧記録を規則 10 の `known_stop` として当て直す扱い（5.2 節。基点ですでに起きていた）は、判断が要る事項として残ります。
- 共通の案 PC-UP-TO-ZERO（ほかの 11 場面）は proposal のままです。

## 8. 失敗・修正・再実行・未確認

- 失敗と修正（製品のコードの期待を変えて通したものはありません。前の出力は証跡に残した）:
  1. 前提の確かめの道具の 1 回目・2 回目: 書き出しの形式 9 では［へんしん］の状態を表せずに例外になりました。形式を最新に直したところ、括弧の誤りで構文の誤りになりました。どちらも出力を書く前で、直して実行しました。
  2. 新しいテストの 1 回目（登録だけ）: 送信の結果の診断を `ActionResult` から直接読んでいました（正しくは `view`）。テストを直しました。
  3. 新しいテストの 2 回目（実装のあと）: きぜつの出来事の名前を `knockout` と書いていました（正しくは `knock_out`）。テストを直しました。
  4. 既存の前提のテスト `test_the_code_is_raised_at_exactly_one_site` が、`conventions.py` の場面の登録を 2 つ目の箇所として数えて失敗しました。場面の登録だけを許すように直しました（投げる箇所が 1 つであることは同じに確かめる）。
  5. 生成の検査: 実装のあとに台帳と設計案の `--check` が exit 1 になりました（基点では 0）。採用の記録を入力に加え、`--write` で作り直しました。
  6. 道具の写しの書き換え（シェルの置換・Python の文字列のエスケープ）が 2 回うまく当たらず、書き直しました（どちらも実行の前）。
  7. 文書のコミットのあとの最後の確かめ（50 モジュール・1,423 テストと生成の検査はすべて成功）で、`--sites` の新しい候補箇所が 280 から 281 に増えました。設計文書 8.1 節の D4 の行の語が候補の語に当たったためで、意味を変えずに言いかえ、`--sites` が基点と同じ（`ABE1CBFA…`）にもどったことを確かめました（証跡の `out/checks_final/`・`out/checks_sites_after_fix/`）。
- 未確認:
  - `new_game` からの回収の決定への到達（構築盤面だけ）と、対戦の初めからのログの監査（`log_problems`）
  - メタモン以外のコピーの経路の全体（ちょうのうりょく・思い出させるなど。対象の外として H4 のまま）
  - 最小が 1 以上の回収の要素の構築盤面
  - GUI の画面
  - 全体のテスト
  - 拒否の直後のエンジンの内部状態の照合値（保存記録にない）
