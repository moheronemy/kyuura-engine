# v0.186: 突風・ポケモンいれかえ・きずぐすりのプレイ用の続行規約（開発用の集合 CS-KYUURA-PLAY-TR3@1）

2026-11-15。利用者が採用した方針を実装しました。3 つの未裁定の条件では、使えない・カードを消費しない、という扱いです。[判断一覧](play-convention-three-trainers.md)の推奨値に従っています。

- **プレイ用の取り決めです。** 史実の裁定は確定していません。厳密側の停止コード（GW5 の `UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH`・`UNRESOLVED_SWITCH_WITHOUT_BENCH`・`UNRESOLVED_POTION_WITHOUT_DAMAGE`）は active のままで、kyuura の論点も解決にしていません。
- **既定では有効になりません。** 省略したときの集合は `CS-KYUURA-CURRENT@1` のままです。`new_game(..., conventions="CS-KYUURA-PLAY-TR3@1")` のように明示的に選んだ対戦だけで当たります。
- 厳密モード（CURRENT@1）と既存の集合（LEGACY@1・S2A@1・PO@1）の ID・版・中身・照合値は変えていません。
- GUI の集合の選択と表示の確かめは、別の単位です（6 章）。新しい対戦のバッチ・seed の探索・judge・replay はしていません。
- 証跡: `kyuura-engine-verification-vai/verifier/runs/play-convention-tr3-impl/`（事前計画・7 項目・識別・差分・テストの結果と JUnit・配布の確かめ・失敗と未確認）。

## 1. 基点・コミット・識別

| 項目 | 値 |
|---|---|
| 基点 | `claude/play-convention-three-trainers` の `6df781f`（origin と一致・変更 0・main に未取り込み。版 0.185.0） |
| 作業 | worktree `C:\dev\kyuura-engine-lt39`、ブランチ `claude/play-convention-tr3-impl` |
| コミット | `121e1e6`（実装と新しいテスト）・`ff7720c`（生成物）・`a1b7659`（版を 0.186.0 にする。配布の確かめの固定コミット） |

**識別の前後**（実測。`out/identity_before_6df781f.json`・`identity_after_fix_121e1e6.json`・`identity_after_a1b7659.json`）

| 項目 | 前（0.185.0） | 修正のあと（版の前） | 後（0.186.0） |
|---|---|---|---|
| パッケージの版 | 0.185.0 | 0.185.0 | 0.186.0 |
| behavior_digest | `a3b65dbe…` | `d6e8a51c…` | `3871f75a…` |
| instrumentation_digest | `d3436748…` | 同じ | `13c773a8…` |
| P1 の basis | `06ec1daf…` | `2ed8732f…` | `2ed8732f…` |
| P3 の basis | `6a8287f9…` | `9499db41…` | `9499db41…` |
| `TOOL_VERSION`・道具の識別 | 11・`6e0616cc…` | 同じ | 同じ |
| 判定の規則・計画と完了の形式 | 8・`kyuura-vai-batch-plan/7`・`kyuura-vai-batch-complete/7` | 同じ | 同じ |

- instrumentation_digest は、`ff7720c` で作り直した診断のカタログ（`data/diagnostic_catalog.json`。`replay_record.INSTRUMENTATION_FILES` の 1 つ）の分だけ変わりました。
- P1・P3 の basis の変化は、`effects.py` の変更によります（どちらの basis の対象にも `effects.py` がある）。basis の範囲は変えていません。
- 書き出しの形式の番号・合法手 API の形式（`FORMAT` 1）・client_api の契約の番号は変えていません。集合の識別の形は既存のものです。
- 旧記録・snapshot・検証用 AI の計画は、それを作った版と集合に結び付いたままです。状態はそれぞれの集合の識別を持つので、後から TR3 は当たりません。

## 2. 採用した設計の 7 項目

| # | 項目 | 採った値 |
|---|---|---|
| D1 | 拒否のコード | 既存の `NO_OPPONENT_BENCH`（突風）・`NO_BENCH`（ポケモンいれかえ）・`NO_DAMAGE_COUNTERS`（きずぐすり）。理由の文に `（規約 ID@1: プレイ用の取り決めで使えない。カードは手札のまま）`。例外の属性 `convention` に `"ID@1"` |
| D2 | 候補での示し方 | 選択肢に残し、`eligible: false`・`convention: "ID@1"`。`processability` は書かない（v0.143 の配置の `excluded_by_convention` と同じく、処理可能性の区分ではない） |
| D3 | 拒否のログ | 書かない（`convention_applied` も書かない。受理の前の拒否は状態の複製の上） |
| D4 | 名前 | 規約 `PC-GUST-WITHOUT-OPPONENT-BENCH@1`・`PC-SWITCH-WITHOUT-BENCH@1`・`PC-POTION-WITHOUT-DAMAGE@1`、集合 `CS-KYUURA-PLAY-TR3@1` |
| D5 | 承認の記録 | 各規約の `content.adoption`（2026-11-15 の利用者の採用。公式の裁定・エラッタ・kyuura の研究上の解決ではない） |
| D6 | 版 | 0.186.0（origin のどのブランチにも 0.186 以降はない）。書き出しの形式は変えていない |
| D7 | 生成するデータ | 診断のカタログと共通規約の設計案を作り直した。停止の方針の台帳は作り直していない（4 章） |

## 3. 実装

| 箇所 | 変更 |
|---|---|
| `conventions.py` | 続行規約 3 件（層 continuation・承認 user_agreed・場面は停止コード 1 つ）と、集合 `CS-KYUURA-PLAY-TR3@1`（区分 development・完全性 halts_at_undecided。PO@1 の 20 規約に 3 件を足した 23 件）。固定した照合値に規約 3・集合 1 を足した。`IMPLEMENTED_CONTINUATIONS` に 3 件を足した |
| `effects.py` | `unresolved_or_convention_rejection`: `continuation_for(state, 停止コード)` があれば規約による `IllegalActionError`、なければ `stop_without_continuation` のあとで今の `UnsupportedError`（コード・文は今と同じ）。`SwitchOpponentWithBench`・`SwitchWithBench`・`RemoveDamageCounters` の `check_playable` の最初の分岐だけが呼ぶ |
| `legal_actions.py` | トレーナーの候補で、規約による拒否のカードを選べるものに残す（D2）。候補全体の区分には数えない。選べるものが規約の除外だけなら、候補は `not_implemented`・`no_eligible_card`（v0.143 の配置の前例と同じ） |

**照合値**（固定した値。`PINNED_*`）

| 項目 | 照合値 |
|---|---|
| `PC-GUST-WITHOUT-OPPONENT-BENCH@1` | `sha256:1e6d415e…` |
| `PC-SWITCH-WITHOUT-BENCH@1` | `sha256:734c11c8…` |
| `PC-POTION-WITHOUT-DAMAGE@1` | `sha256:ed5f64a1…` |
| `CS-KYUURA-PLAY-TR3@1` | `sha256:a7b800cf…` |
| 既存（変えていない） | CURRENT@1 `9a9b95c6…`・LEGACY@1 `abf39e6d…`・S2A@1 `b317a3f0…`・PO@1 `06d51219…` |

`engine.py`・`resolution/` は変えていません。カード ID・モードの名前による分岐はありません。場面は停止コードで、同じ型の再録の版にも同じ規約が当たります。

### 3.1 厳密側と TR3 側の動き

| 場面 | 厳密側（CURRENT@1・S2A@1・PO@1） | TR3 側 |
|---|---|---|
| 手札から使う（エンジンへの直接の操作・`HostedGame.submit`） | `UnsupportedError`（今のコード）。状態は変わらない | `IllegalActionError`（D1）。状態・乱数・カード・ログ・決定の通し番号は変わらない。カードは手札のまま |
| 候補の選択肢 | `processability: unresolved_ruling`・`eligible: false` | `eligible: false`・`convention`（`processability` なし） |
| check・submit（公開の入口） | `CANDIDATE_NOT_EXECUTABLE` | `CANDIDATE_NOT_EXECUTABLE`（エンジンに渡す前に断る） |
| 方策（検証用 AI の `option_allowed`） | 範囲の外 | `eligible` が偽なので選ばない |
| 対象がいる場合 | 今の処理 | 同じ（ログ・乱数・決定が厳密側と同じ） |

### 3.2 代用の使用と、対象外の条件

| 経路・条件 | TR3 側 |
|---|---|
| 錯乱ジムの「うら」でかわりに使う | 使う人（相手）から見た同じ条件。決定は出る。「使う」の答えは拒否（D1 のコードと規約 ID。状態は変わらない）、「使わない」は受け付ける。厳密側は「選ぶと止める」選択のまま。カードは錯乱ジムの「うら」の処理でトラッシュに行く（規約による消費ではない） |
| サイキックコントロール | 相手のトラッシュの対象のカードは選べるものに残り、選ぶと拒否（D1）。厳密側は選ぶと未裁定で止める |
| AL2（はなれられない） | 相手・自分の控えがいれば、今までどおり止める（規約の除外にしない） |
| MG1（錯乱ジムと［ちえくらべ］） | 対象があれば、今までどおり止める。対象がなければ、厳密側と同じく 3 条件の確かめが先 |
| ダメージのないポケモンを選ぶ（`UNRESOLVED_POTION_UNDAMAGED_TARGET`） | 今までどおり止める（受理のあとの未裁定） |
| 受理のあとに対象がいなくなった場合 | 今の処理のまま |
| ほかのカードの同じ形の問い | 止めるまま（規約の対象ではない） |

- 判定は、ベンチの数と場のダメージ（公開の値）だけです。秘密の手札やうらのカードの本当のカードを、新たに読みません。相手の手札・山札だけが違う双子で、候補が同じことを確かめました。
- この 3 条件を決めても、対戦全体が止まらなくなるわけではありません。対象外の未裁定は、TR3 でも今までどおり止まります。

## 4. 生成物

| 生成物 | 結果 |
|---|---|
| 診断のカタログ（`build_diagnostic_catalog.py`） | `DYNAMIC_SITES` に新しい呼び出し箇所を足し、`--write` で作り直した。差は 3 コードの `basis` の呼び出しの数だけ（`NO_BENCH` 2→3・`NO_DAMAGE_COUNTERS` 5→6・`NO_OPPONENT_BENCH` 7→8）。`--check` 0 |
| 共通規約の設計案（`build_play_policy_family_plan.py`） | `SPEC_ADOPTIONS` に 3 規約を足した（`related_candidate` は `PC-USE-WITHOUT-TARGET`。この案そのものは proposal のまま）。差は 3 場面の `adopted_convention` だけ。`--check` 0 |
| 場面の索引（`convention_records.json`） | 変更なし（`--check` 0） |
| 停止の方針の台帳（`docs/stop-policy-classification.json`） | **作り直していない**。基点（`6df781f`）ですでに `--check` が合わない（PROBLEM「現行コードから作り直した台帳と、書き出した台帳が違う」）。版の文書で `--check` を記録した最後は v0.151 でした。今の生成の道具で作り直すと、行番号のほかに 97 項目の差が出ます（`out/ledger_diff_unchanged_generator.json`）。そのうち多くは v0.152〜v0.185 の変更（テストのファイルの数・項目 `UNRESOLVED_NOT_IN_TABLE` などの追加・`active` 407→411）で、今回の規約と関係がありません。続行規約の採用の記録（`continuation_agreements`・DEC-USE-WITHOUT-EFFECT の状態・`UPDATES`）は、台帳を揃える単位でまとめて加えます（7 章） |

## 5. テスト

1 モジュールずつ別のプロセスで実行しました（`scripts/run_tests.py`。PowerShell・`MSYS=noglob`・`PYTHONIOENCODING` を外す）。全体のテストはしていません。

| 段 | モジュール | 結果 |
|---|---|---|
| 修正の前の新しいテスト | 1（16 テスト） | 期待どおりの失敗だけ（25 の誤りがどれも「TR3 を知らない」。厳密側と既存の集合のテストは成功） |
| 実装のあと | 新しいテスト 1 | 16 成功 |
| 関連（実装のあと） | 27（653 テスト） | すべて成功。検証用 AI の行動・契約の固定の指紋（`test_verification_ai_v2_repeat`）は変えずに成功 |
| 生成物のあと | 6（94 テスト。台帳・診断・総数・設計案・仕様） | すべて成功 |
| 版のあと | 3（43 テスト。版の期待・配布の形・新しいテスト） | すべて成功 |
| 最終のコード（版のあと） | 7（162 テスト。固定の指紋・規約集合・client_api・候補・錯乱ジム・再現用記録・診断） | すべて成功 |
| 文書のあと | 15（README・実装状況を読む各版のテストと配布の形。証跡の `scripts/tests/docs`） | すべて成功 |

- 新しいテスト（`tests/test_play_convention_tr3_v0_186.py`）の盤面は、構築盤面です（`build_test_state` で作った盤面の規約集合だけを置きかえる）。`new_game` で確かめたのは、TR3 を明示して対戦を作れることと、既定の集合が変わらないことだけです。3 条件の場面に対戦の中で到達した実績ではありません。
- 設計の V1〜V8 との対応: V1 は `StrictTest`。V2・V3 は `Tr3Test.test_rejected_by_convention_without_change`。V4 は `test_targets_present_are_unchanged`。V5 は `SubstituteTest`。V6 は `test_other_unresolved_are_not_hidden`・`test_mind_games_chaos_gym_is_not_hidden`・`CandidateTest.test_other_reasons_are_not_converted`。V7 は `CandidateTest`（混在・規約の除外だけ・秘密への非依存）。V8 は `RecordTest`・`RegistrationTest`。

## 6. 配布の確かめ（固定コミット `a1b7659`）

1. `git ls-tree` の `kyuura_engine` の数は 62 で、基点と同じでした。パッケージの差は `__init__.py`・`conventions.py`・`effects.py`・`legal_actions.py`・`data/diagnostic_catalog.json` です。`pyproject.toml` の差は版の 1 行で、依存は増えていません。
2. `git archive --format=tar -o` で固めたものを、Python の `tarfile`（`filter='data'`）でリポジトリの外に展開しました。`pip wheel --no-deps`（隔離あり）は exit 0 で、`kyuura_engine-0.186.0-py3-none-any.whl` ができました（sha256 `390d64ae…`）。`scripts/check_distribution.py --wheel` も exit 0 です（required=62・problems=0）。
3. スモーク用のスナップショットは、同じ展開から作りました。3 条件 × 3（厳密側・TR3 側・TR3 で対象あり）の 9 つです。旧版のスナップショットは使っていません。
4. リポジトリの外の新しい venv に、`pip install git+https://github.com/moheronemy/kyuura-engine.git@a1b765918dc8e0f8ff326fa732d2c8220edab8e2` で導入しました（exit 0）。入ったのは kyuura-engine 0.186.0 と pip だけです。
5. スモーク（`scripts/smoke_v0186.py`。tests を使わない）の結果:
   - 導入物は site-packages から読み込まれました。direct_url は vcs の commit `a1b7659…` で、editable ではありません。`requires` はなく、ファイルは 62 で、識別はソースと一致しました。
   - 厳密側: 直接の操作は今の未裁定のコードで止まります。候補は `unresolved_ruling`、check・submit は `CANDIDATE_NOT_EXECUTABLE` です。
   - TR3 側: 直接の操作は D1 のコードと規約 ID で拒否され、状態は変わりません。候補は `eligible: false`・`convention` で、`processability` はありません。全体は `not_implemented`・`no_eligible_card`、check・submit は `CANDIDATE_NOT_EXECUTABLE` です。
   - TR3 で対象あり: 受け付けて決定が出ます。check は有効で、submit は accepted です。
   - ソースの木と導入物で、結果（`result_sha256` `bd005340…`）と識別が同じでした。

## 7. 残る作業と GUI への引き継ぎ

- **停止の方針の台帳を揃える**（別の単位。→ 2026-11-15 に差を調べて分類した: [停止の方針の台帳の生成の差の調査](stop-ledger-drift-audit.md)。台帳はまだ作り直していない）: v0.151 のあとの版の差をまとめて作り直し、差を分類します。TR3 の採用の記録（`continuation_agreements` の AGR-PLAY-TR3-*・DEC-USE-WITHOUT-EFFECT を partly_agreed・`UPDATES` の 0.186.0）も、そこで加えます。今回は、台帳の生成の道具も JSON も変えていません。
- **GUI**（別の単位）: GUI の契約の表（`contract/kyuura-client-api-v1.json` の `trainer_option_keys`）に `convention` がないので、TR3 の対戦の候補を「不明な応答」として止めます。既定の集合の対戦は影響を受けません（`convention` は TR3 でだけ出る）。最小の追従は次の 3 つです。
  - 集合の選択に `CS-KYUURA-PLAY-TR3@1` を加える
  - `trainer_option_keys` に `convention` を加える
  - 規約による除外の表示（配置の `excluded_by_convention` の表示「規約による扱い」と同じ形）を加える
- 錯乱ジムの「使う」・サイキックコントロールの選べるものは、v0.168 の既存の設計（使うための条件を満たせないことを決定の選べるものに示さない）のままです。規約による除外の印は付けていません。答えたときの拒否の理由に、規約 ID が出ます。

## 8. 失敗・修正・再実行・未確認

- 失敗と修正（製品のコードの期待を変えて通したものはありません。前の出力は証跡の `scripts/tests/attempt*`）:
  1. 新しいテストの 1 回目: 旧状態用の集合を新しい状態に置こうとした。送信の結果の `refusal` を辞書として読んだ。テストの側を直しました。
  2. 新しいテストの 2 回目: 旧状態用の集合の照合値を `identity_of` で作ろうとしました（作れない集合）。固定の値と中身で確かめる形に直しました。
  3. 実装のあとの 1 回目: 書き出しの規約集合の鍵を `conventions` と書いていました（正しくは `convention_set`）。テストを直しました。
  4. 生成の道具の 1 回目の編集: ファイルを読む前に編集しようとして拒否されました。`--write` も exit 1 で、何も書いていません。読んでから編集し直しました。
  5. 停止の方針の台帳: 生成の道具を変えずに `--write` して差を調べ、基点からの不一致を確かめたあと、JSON を元にもどしました（コミットしていない）。
- 未確認:
  - GUI の画面
  - `new_game` からの 3 条件の場面への到達
  - 全体のテスト
  - 停止の方針の台帳を揃えたときの差の全部の分類
  - 錯乱ジムの「うら」のコインを投げたあとの公開の観測の比較（構築盤面でエンジンの結果だけを確かめた）
