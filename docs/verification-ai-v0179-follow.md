# 検証用 AI の 0.179.0（PT-5t-C1）への追従

[PT-5t-C1](legal-actions-up5t-d-trainer-audit.md)（v0.179.0。監査の文書の 12 章）では、トレーナーの候補の確かめが相手のうらのカードの本当のカードを使った場合、その結果を候補に使わず、その選べるものを `unverified`（`face_down_reveal_not_evaluated`）にするようにしました。

これは、確認された秘密依存の判定を候補の側で採用しない補強です。修正の前の構築盤面でも外へ出る差は再現しておらず、情報漏れを再現して直したものではありません。

検証用 AI（`tools/verification_ai`）をこの版に追従させました。変えたのは、テストの固定値と新しいテストだけです。

- 変えていないもの: AI のコード（方策・入力生成・範囲・判定）、エンジン、GUI、renderer、kyuura、カードデータ、固定デッキ、規約集合、裁定、識別方式
- パッケージの版: 0.179.0 のまま

## 0. 基点と範囲

| 項目 | 値 |
|---|---|
| 基点 | `c157c7b84846b1e66ef036dadbbc27b58a8953e5`（`origin/claude/pt5t-c1`）。PT-5t-C1 の実装 `57c03d2`、版 0.179.0 の `4b6e3fe`、文書と、既存の AI（0.178.0 への追従を含む）が入っている。`origin/main` には入っていない |
| 配布を確かめたコミット | `4b6e3fea9212c50622dcfea7142dcc76fd14b09d`（PT-5t-C1 の作業で、Git の URL から通常のインストールをしてスモークをした） |
| 作業ブランチ | `claude/vai-0179-follow`（専用の worktree `C:\dev\kyuura-engine-up5td`）。利用者の `C:\dev\kyuura-engine` は触っていない |
| テストのコミット | `2366714`（テストは、このコミットと同じ内容の作業ツリーで実行した） |
| 実行の前の計画 | 証跡の `verifier/runs/vai-0179-follow/PLAN.md`。差の調べやテストを実行する前に書いた |
| 証跡 | `C:/dev/kyuura-engine-verification-vai/verifier/runs/vai-0179-follow/`（計画・指紋の差と更新の来歴 `contract_diff.json`・`fingerprint_update.json`・テストの出力・コマンド・実装の識別）、非機密の集計 `public/runs/vai-0179-follow/summary.json`。マニフェストは既存の 693 件の照らし（不一致 0）のあと 714 ファイルで書き直した（`sha256.json` は `082ef6dbf4271af4f7d5904f10299de88e0fe34d0bedaa750bd546cb515a3dfa`） |
| 対象外 | GUI の追従、UP-5t の D、おもての山札の位置を読むトレーナー 7 型の前提の監査、ほかの残件 |

## 1. 指紋のテストの 4 件の失敗

`tests/test_verification_ai_v2_repeat.py` の `UnchangedTest` は、上限 80 の操作の小さな対戦 4 つで、2 つの指紋をそれぞれの固定値と照らします。

- 行動の列: 形式 `action-meaning/v2`、固定値 `ACTION_GOLDEN`
- API の契約の値の列: 形式 `candidate-contract/v1`、固定値 `CONTRACT_GOLDEN_0178`（追従の前）

0.179.0 では、4 つの対戦のすべてで、契約の値の指紋が失敗しました（PT-5t-C1 の証跡 `pt5t-c1/tests/run4-ai-impact/`）。行動の列は通りました。

## 2. 原因の確かめ

既存の証跡 `pt5t-c1/ai_contract_probe.json` で、次のことは確かめてありました。

- トレーナーの保証の文だけを 0.178.0 の文に戻すと、4 つとも `CONTRACT_GOLDEN_0178` に一致する
- 行動の列は、どちらの文でも固定値と同じ

行・項目・反復の鍵までは記録していなかったので、0.178.0 の追従と同じ方法の `contract_diff.py`（証跡）で補いました。

- 4 つの対戦を、0.179.0 の文のままと、play_trainer の保証の文だけを同じプロセスの中で一時的に 0.178.0 の文に戻した場合の 2 通りで実行した
- 行ごと・項目ごとに比べた
- 旧い文への置きかえは原因の調べのプロセスの中だけで、応答を書きかえてテストを通すことはしていない

| 確かめたこと | 結果 |
|---|---|
| 行動の列（`action-meaning/v2`） | 4 つの対戦とも、2 つの文で同じ。`ACTION_GOLDEN` とも一致した |
| 契約の値の列で違う項目 | `candidate.guarantees.preconditions` だけ |
| 違う行 | play_trainer の行のすべてで、ほかの行に差はない。<br>・uniform-stage-s12: 87 行のうち 10 行<br>・uniform-tuple-s12: 88 行のうち 12 行<br>・rules-v1-s13: 106 行のうち 7 行<br>・mixed-v1-s13: 96 行のうち 16 行<br>どれも `may_stop_later`（`continuation_not_evaluated`・`preflight_not_evaluated`）で、今回のガードが働く選べるもの（相手のバトル場がうら）ではない |
| 行の数 | 同じ |
| trace 全体（保証の文と時間を除く） | 4 つの対戦とも同じ（行動・入力・送信の結果・方策の選び方の記録を含む）。終わり方も同じ |
| 反復の抑制の鍵（`policies.action_key`） | すべての試行（87・88・106・96）で、2 つの文で同じ。鍵は評価の値（`guarantees`・`processability`・`reasons` など）を除いて作る |
| 方策の乱数の消費 | 方策と行動生成は保証の文を読まない。trace の選び方（picks）の記録が同じ |
| 0.178.0 の文に戻した場合 | 4 つとも `CONTRACT_GOLDEN_0178` に一致した |

加わった文は「v0.179: 確かめが相手のうらのカードの本当のカードを使ったら、その結果（受け付ける・拒否・停止）を使わない（unverified。そのあとの公開の確かめの拒否も示さない）」です。

### 2.1 固定値の更新

`CONTRACT_GOLDEN_0179` を加え、`UnchangedTest` はこれと照らします。

- 根拠（変更の理由・差のある行と項目・確かめの方法）は、コードの注記とこの章に書きました
- `CONTRACT_GOLDEN_0178`・`CONTRACT_GOLDEN_0176` は来歴として残しました
- `ACTION_GOLDEN` は変えていません
- 来歴のテストに、4 つとも 0.178.0 の値と違うこと・行の数が同じことを加えました

| 対戦 | 0.178.0（来歴） | 0.179.0 |
|---|---|---|
| uniform-stage-s12 | 87 行 `0316ba75…b4f8` | 87 行 `11e6d2568ea2b8535b341c830d89dc29cc27eb27255a2e462a13dad4dc61e809` |
| uniform-tuple-s12 | 88 行 `b1fb93db…92e9` | 88 行 `f24f672abc34e5e02c686950357a9240ad986283160c873930b9774ef3fffde2` |
| rules-v1-s13 | 106 行 `240da53e…faf4c` | 106 行 `62dbe81fd8c6bc7b9a4566be598d29cc5f607b394f793cef649fe7f5b2d36a55` |
| mixed-v1-s13 | 96 行 `5fac889d…6f37` | 96 行 `57ae781c0d07f96117cd85a083be0e4d147f5803ad5a937cf40ede22a10f12d1` |

## 3. 候補・選べるもの・完成入力の区分

play_trainer は手札のトレーナーカードごとの選べるものを持ち、一部だけが `unverified` になりえます。AI では、次の 3 つの区分を分けて扱います（どれも既存のコード）。

| 区分 | 値 | 使う所 |
|---|---|---|
| 候補 | 候補の `processability`。エンジンは選べるものの中でいちばん進めやすい区分にする | ランナーの `_scope`（deep・boundary の範囲・代替） |
| 選べるもの | 選べるもの自身の `eligible`・`processability` | `actions.option_allowed`・`build_choices`・`build_choices_tuple`・`enumerate_inputs`。deep では `DEEP_PROCESSABILITY`、代替・boundary では `FALLBACK_PROCESSABILITY` |
| 完成入力 | 選んだものの中でいちばん進めにくい区分 | `actions.input_processability`（記録の値。候補の区分とは別） |

構築盤面（エンジンのテスト `tests/test_legal_actions_pt5t_c1_v0_179.py`）と、実際の応答の写しから作った小さな JSON 例で確かめました（`tests/test_verification_ai_v0179_follow.py`）。

| 場合 | 結果 |
|---|---|
| 相手のバトル場がうら（2 型 × 本当のカード 3 種） | 選べるものは `unverified`・`face_down_reveal_not_evaluated`・`eligible` 真。本当のカードによらない。選べるものがそれだけなら候補も `unverified` |
| おもての対照 | 使うための条件を評価する（`may_stop_later`） |
| 本人のうらだけを読む対照（イマクニ？） | `face_down_reveal_not_evaluated` にしない |
| 公開の条件で使えない（［アレルギーかふん］） | play_trainer の候補が出ない（AI は選べない） |
| 混在（同じ候補に、イマクニ？の `may_stop_later` とねむれ!ねむれ!の `unverified`） | 候補は `may_stop_later` で、deep の範囲に残る（候補全体を一律に除かない）。deep は段ごと・組の列挙のどちらでも、`unverified` の選べるものだけを選ばない。boundary は両方を選べる。完成入力の区分は、選んだものに応じて `unverified` か `may_stop_later`（候補は `may_stop_later` のまま） |
| deep で `unverified` の選べるものしかない候補 | 候補の区分が `unverified` なので、deep の範囲の外。ほかに範囲の候補があれば代替は起きない |
| 代替 | deep の範囲に候補が 1 つもないときだけ。`FALLBACK_PROCESSABILITY` で選び直し、`deep_fallback_unverified` を数える。そのとき `unverified` の選べるものも選べる。deep の allowed のままでは、その候補の入力は作れない（`Unbuildable`） |
| 表示だけ・入力を返さない・実行できない区分 | deep・boundary とも候補を選ばない。`eligible` 偽・実行できない区分の選べるものは、どちらの allowed でも選ばない |
| カード名・カード ID | 範囲・選べるものの判定はカード ID を書きかえても同じ（読まない） |
| 元の API の応答 | 範囲・入力の組み立ての前後で同じ（書きかえない） |
| check・submit の共通の経路 | 選べるものごとに、check（構造の検査だけ）→ 同じ取っ手・同じ入力で submit。受理なら判定は `expected`、公開の更新は受理のときだけ |

## 4. 判定（judge）

判定のコードは変えていません（`JUDGE_RULES_VERSION` は 5 のまま）。既存の規則で足りる根拠は次のとおりです。

- `play_trainer` は事前確認の種類（`PRECHECK_KINDS`）ではありません。check の成功は構造の検査だけで、受理・完走の保証として扱いません（check のあとの拒否を、それだけで suspect にしない）
- ホストの段の断り（`refused`）は suspect、エンジンの拒否（`rejected`）は診断の区分で読みます。2 つを分けています
- `unverified` だからといって、すべての拒否を正常にはしません
  - 区分の合わない拒否（`unsupported` の `INSUFFICIENT_CARDS_IN_HAND` など）・写しのない拒否（`unmapped`）は suspect
  - 知らない結果・根拠（代表の条件の宣言）のない停止・診断の表にない停止は undetermined で、`known_stop` にしません
- 記録のあとの公開の拒否が候補の側で `unverified` に覆われても、送ればエンジンが今までどおり拒否します
  - 判定はエンジンの拒否として読みます（`invalid_input` の `INSUFFICIENT_CARDS_IN_HAND` は `normal_rejection`）
  - 候補の側の評価を弱めたことと、ゲームの合法性を緩めたことは別です。エンジンの合法性は緩めていません
  - 今の登録のねむれ!ねむれ!・トロピカルウインドでは、記録のあとの公開の拒否は起こりません（監査の 12.4 節）
- P6・U-R3a・PT-5e の規則は変えていません

## 5. 限定の検証

1 つずつ別のプロセスで実行しました。出力は証跡の `tests/run1/`・`tests/run2/` にあります。

| 実行 | モジュール | 結果 |
|---|---|---|
| run1 | `tests.test_verification_ai_v0179_follow`（新しい 11 件） | OK（1 回目） |
| run1 | `tests.test_verification_ai_v2_repeat`（16 件。固定値の更新のあと） | OK |
| run2 | `tests.test_verification_ai_v0178_follow`（UP-5t-C1） | OK |
| run2 | `tests.test_verification_ai_v0176_follow`（PT-5e） | OK |
| run2 | `tests.test_verification_ai_p6` | OK |
| run2 | `tests.test_verification_ai_u_r3a` | OK |
| run2 | `tests.test_verification_ai_judge` | 終了コード 1。存在しないモジュールの名前を指定した誤りで、読み込みのエラー（テストの失敗ではない）。判定の確かめは新しいモジュールと `v0178_follow` が受け持つので、取り直していない |

- 合計は約 40 秒です
- 固定の対戦の追加、V0〜V3 の再実行、全体のテスト、GUI、E2E、seed の探索、大量の対戦、lockstep、状態の監査はしていません

## 6. 版・実装の識別

- パッケージの版は、AI の変更の前後で 0.179.0 のままです
- 実装の識別（`behavior_digest` `67c4c15bafcf00b81f7abe7ef2396742181d27744b2af7efd1657f4c90767fca`・`instrumentation_digest` `d3436748…146d`・方式 `kyuura-package-files-sha256/1`）は、PT-5t-C1 の配布の確かめのソースの識別と同じでした（`identity_check.py`・`identity_after.json`）
- 0.178.0 以前の記録・スナップショットは、元の実装と対応付けたまま証跡に残しています。識別を書きかえて流用していません

## 7. GUI の追従へ渡すこと

- 固定するエンジン: `4b6e3fea9212c50622dcfea7142dcc76fd14b09d`（0.179.0）
- 値の語彙は増えていません（`unverified`・`face_down_reveal_not_evaluated` は契約の表にある）。play_trainer の選べるものの単位の `unverified` は、U7-5c から既存の扱いです
- 見込み（GUI では確かめていない）: 固定のコミット・契約の engine の値・版のテスト・固定例の compatibility（play_trainer の保証の文の 1 文の差）の更新で足ります

## 8. 未確認

- 実際の対戦（V0〜V3 など）で、ガードが働く選べるものに出会う頻度・代替の回数は計っていません（相手のバトル場がうらの盤面は、固定デッキの対戦では起こりにくい）
- 差の出る盤面（本当のカードで候補が変わる盤面）は再現していません（エンジン側の 12.8 節）
