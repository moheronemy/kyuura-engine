# 検証用 AI の 0.178.0（UP-5t-C1）への追従

[UP-5t-C1](legal-actions-up5t-audit.md)（v0.178.0。監査の文書の 11 章）では、特殊能力の候補の確かめが相手のうらのカードの本当のカードを使った場合、その結果を候補に使わず、`unverified`（`face_down_reveal_not_evaluated`）にするようにしました。

これは、確認された秘密依存の判定を候補の側で採用しない補強です。修正の前の構築盤面でも外へ出る差は再現しておらず、情報漏れを再現して直したものではありません。

検証用 AI（`tools/verification_ai`）をこの版に追従させました。変えたのはテストの固定値と、新しいテストだけです。AI のコード（方策・入力生成・範囲・判定）、エンジン、GUI、renderer、kyuura、カードデータ、固定デッキ、規約集合、裁定、識別方式は変えていません。パッケージの版は 0.178.0 のままです。

## 0. 基点と範囲

| 項目 | 値 |
|---|---|
| 基点 | `7ef45be70401d3a3fd167b4575a767ccdc665deb`（`claude/up5t-c1`）。UP-5t-C1 の実装 `c01c1b5`、版 0.178.0 の `8f5329d`、文書と、既存の AI（0.176.0 への追従を含む）が入っている。`origin/main` には入っていない |
| 配布を確かめたコミット | `8f5329d6fb9eeeb783f3d6f57128069ffc0d98a0`（UP-5t-C1 の作業で、Git の URL から通常のインストールをしてスモークをした） |
| 作業ブランチ | `claude/vai-0178-follow`（専用の worktree `C:\dev\kyuura-engine-vai`）。利用者の `C:\dev\kyuura-engine` は触っていない |
| テストのコミット | `b64fc82`（テストはこのコミットと同じ作業ツリーで実行した） |
| 実行の前の計画 | 証跡の `verifier/runs/vai-0178-follow/plan.json`。コードを変える前、差の調べやテストを実行する前に書いた |
| 対象外 | GUI の追従、UP-5t の D の監査、トレーナーの候補（`play_trainer`）への拡張、ほかの残件 |

## 1. 指紋のテストの 2 件の失敗の原因

`tests/test_verification_ai_v2_repeat.py` の `UnchangedTest` は、上限 80 の操作の小さな対戦 4 つで、2 つの指紋をそれぞれの固定値と照らします。

- 行動の列: 形式 `action-meaning/v2`、固定値 `ACTION_GOLDEN`
- API の契約の値の列: 形式 `candidate-contract/v1`、固定値 `CONTRACT_GOLDEN_0176`

0.178.0 では、rules-v1-s13 と mixed-v1-s13 の契約の値の指紋 2 つが失敗しました。調べには、証跡の `contract_diff.py` を使いました。4 つの対戦を、0.178.0 の文のままと、use_power の保証の文だけを同じプロセスの中で一時的に 0.177.0 の文に戻した場合の 2 通りで実行し、行ごと・項目ごとに比べました。

| 確かめたこと | 結果 |
|---|---|
| 行動の列（`action-meaning/v2`） | 4 つの対戦とも、2 つの文で同じ。`ACTION_GOLDEN` とも一致した |
| 契約の値の列（`candidate-contract/v1`）で違う項目 | `candidate.guarantees.preconditions` だけ |
| 違う行 | use_power の行のすべて（rules-v1-s13 で 106 行のうち 46 行、mixed-v1-s13 で 96 行のうち 22 行）。どれも `may_stop_later`・`continuation_not_evaluated` で、今回のガードが働く候補ではない |
| use_power の行のない 2 つの対戦（uniform-stage-s12・uniform-tuple-s12） | 契約の値の指紋は 0.176.0 の値のまま |
| trace 全体（保証の文と時間を除く） | 4 つの対戦とも同じ。終わり方も同じ |
| 0.177.0 の文に戻した場合 | 4 つとも `CONTRACT_GOLDEN_0176` に一致した（0.177.0 の契約の値は 0.176.0 と同じ） |
| 方策・入力生成・乱数の消費・反復の抑制 | 変わっていない。方策と行動生成は保証の文を読まない。反復の抑制の鍵（`policies.action_key`）は評価の値（`guarantees` を含む）を除く。新しいテストでも、文だけを変えた候補で鍵と行動の列が同じことを確かめた |

加わった文は「v0.178: 確かめが相手のうらのカードの本当のカードを使ったら（状態の複製の上の試行でおもてにした）、その結果を使わない（unverified）」です。

0.177.0 の文に戻したのは原因を調べる証拠のためで、応答の文を書きかえてテストを通す修正にはしていません。

### 1.1 更新

| 固定値 | 扱い |
|---|---|
| `CONTRACT_GOLDEN_0178`（新しく加えた） | 0.176.0 の値に、rules-v1-s13 `240da53e…faf4c`（106 行）と mixed-v1-s13 `5fac889d…6f37`（96 行）の 2 つだけを上書きした。来歴（版・原因・差のある行と項目）をコメントに書いた。`UnchangedTest` はこの値と比べる |
| `CONTRACT_GOLDEN_0176` | 0.176.0（と 0.177.0）の値の来歴として、値を変えずに残した |
| `ACTION_GOLDEN`・`LEGACY_MEANING_V1_AT_0175` | 変えていない |
| 一括の更新の防止 | `test_legacy_fingerprints_are_kept_as_history` で、0.176.0 から 0.178.0 で変わった値が 2 つだけであること、行の数が同じであることを確かめる |

## 2. 選択の範囲

新しいテスト `tests/test_verification_ai_v0178_follow.py` では、エンジンのテスト `tests/test_legal_actions_up5t_c1_v0_178.py` の構築盤面を使いました。new_game から到達した盤面ではありません。

- 2 つの特殊能力: わるいクサイハナ［くさいかふん］、スリープ［えんかくさいみん］
- 双子 3 つ: 相手のうらのカードの本当のカードだけが違う（たねポケモン、たねポケモンでないカード、メタモン）
- 対照: 相手のバトル場がおもて、使う人がこんらん

範囲の確かめには、既存の関数（ランナーの `_scope`、`actions.option_allowed`、`build_choices`）をそのまま使いました。

| 場面 | API の値 | deep | boundary |
|---|---|---|---|
| 相手のバトル場がうら（ガードが働く） | `unverified`・`[face_down_reveal_not_evaluated]`・`no_input`・段なし。本当のカードによらず同じ | 通常の範囲から除く（理由 `processability:unverified`）。盤面には `end_turn`・`attach_energy` があるので、代替（`deep_fallback_unverified`）は起きない | 含む |
| 同じ候補だけを残した応答の写し（小さな JSON の例） | 同上 | 既存の代替で選ぶ（`fallback_unverified` が真、数は 1）。代替が起きるのは、deep の範囲に何もないときだけ | 含む |
| 相手のバトル場がおもて（対照） | `may_stop_later`・`[continuation_not_evaluated]` | 含む | 含む |
| 公開の条件で使えない（こんらん） | 候補に出ない | 選べない | 選べない |

ほかに、次のことも確かめました。

- 表示だけの種類、入力を返さない候補（`input_disclosure` が `unconfirmed`）、実行できない区分は、deep・boundary・代替のどれでも選ばない。
- `_scope` は元の API の応答を変えない（実行の前後で同じ）。
- 候補の特殊能力の名前とポケモンのカード ID を書きかえても、範囲は同じ。範囲はカード名・カード ID でなく、API の値だけで決まる。

## 3. 判定

judge は変えていません（`JUDGE_RULES_VERSION` は 5 のまま）。既存の規則で足りることを、次の表のとおり確かめました。

| 確かめたこと | 結果 |
|---|---|
| 入力なしの check→submit | `inputs` は段なし、`build_choices` は空、check は valid（構造の検査だけ）。送信は 2 つの特殊能力 × 3 つの双子で受理（受け付けるかは本当のカードによらない）。`judge_normal` は `expected` |
| 規則 5（本人のうらのカードの特殊能力）・P6 の対象か | 対象ではない。使うポケモンはおもてなので `is_face_down_power` は偽。にげるではないので `is_p6` も偽 |
| 事前の確かめの種類（`PRECHECK_KINDS`）か | use_power は入っていない（check の成功を受理の保証として扱わない） |
| ホストの断り（refused） | `suspect` |
| failed | `suspect` |
| 知らない結果 | `undetermined` |
| 対応のない診断（unmapped）・コード表と分類の違い | `suspect` |
| エンジンの通常の拒否（コード表と分類が一致する invalid_input） | `normal_rejection` |
| 停止の分類の拒否 | 代表の条件の根拠がない、またはコード表にないなら `undetermined`。根拠（場面の宣言）があるときだけ `known_stop` で、理由 `face_down_reveal_not_evaluated` が経路の説明に使われる |
| 受理のあとの停止 | `judge_halt_after_accept` で別に読む（対応のない停止は `suspect`、根拠のない停止は `undetermined`） |

この表のとおり、`unverified` だからすべてを正常にする、check の成功のあとの拒否だからすべてを suspect にする、という判定にはなっていません。

P6、本人のうらのカードの特殊能力（U-R3a）、PT-5e の判定は変えていません。

## 4. 限定の検証

関連する AI のモジュールだけを、1 つずつ別のプロセスで実行しました（証跡の `tests/`）。

| モジュール | 結果 |
|---|---|
| `tests.test_verification_ai_v0178_follow`（新しい。9 件） | 1 回目: 失敗 1・エラー 1。どちらもテストの作り方の誤りだった（下に記す）。直して 2 回目は 9 件 OK |
| `tests.test_verification_ai_v2_repeat` | 1 回目で OK（更新した固定値） |
| `tests.test_verification_ai_v0176_follow`（PT-5e の範囲と判定を含む） | OK（11 件） |
| `tests.test_verification_ai_p6` | OK（16 件） |
| `tests.test_verification_ai_u_r3a` | OK（12 件） |
| `tests.test_verification_ai_v3_3` | OK（9 件） |

1 回目のテストの作り方の誤り:

- 断りのコードの名前を `CANDIDATE_STALE` と書いていた。正しくは `CANDIDATES_STALE`。
- 行動の列を比べる 2 つの盤面で、特殊能力のカードの番号がそろっていなかった。対象をそろえ、違う項目が処理可能性・理由だけであることも確かめるようにした。

1 回目の失敗の出力は `tests/run1` に残しました。成功したモジュールは繰り返して実行していません。

差の調べ（`contract_diff.py`）は、v2_repeat の既存の小さな対戦 4 つだけを 2 通りの文で実行しました。そのほかの固定の対戦の実行、V0〜V3 の再実行、全体のテスト、GUI、E2E、seed の探索、大量の対戦、lockstep、状態の監査はしていません。

## 5. 版と識別

- パッケージの版は 0.178.0 のまま。実装の識別（`kyuura-package-files-sha256/1`）も、AI の変更の前（UP-5t-C1 の証跡の `source_identity.json`）と後で同じ: `behavior_digest` `140f4a096d304290d82b6b825531732fe9d112dd54703589690a36526bf038b7`、`instrumentation_digest` `d34367481dd69bd72c715e1977feb93b3c19596a01f3b53a104eca2e7e06146d`（証跡の `identity_after.json`）。
- 変えたのは `tests/` だけで、`kyuura_engine/`・`tools/`・`pyproject.toml` に差はない（証跡の `code_diff_stat.txt`）。
- 0.177.0 以前の完全な記録・スナップショットは、元の実装と対応づけたまま残している。識別を書きかえて新しい版に流用していない。

## 6. GUI の追従へ渡すこと

- 固定するエンジンは、配布を確かめた完全なコミット `8f5329d6fb9eeeb783f3d6f57128069ffc0d98a0`（0.178.0）。
- 値の語彙は増えていない（`unverified`・`face_down_reveal_not_evaluated` は既存）。変わるのは、use_power の保証の文（preconditions に 1 文）と、相手のバトル場がうらのときに［くさいかふん］・［えんかくさいみん］の候補が `unverified` になることだけ。
- AI の側の固定値の差（契約の値の 2 つ）は、保証の文の変更だけによる。行動の列は変わっていない。
- GUI では確かめていない。

## 7. 未確認と残り

- 通常の対戦で、ガードが働く盤面（相手のバトル場がうらで、使う人が［くさいかふん］か［えんかくさいみん］を持つ）に到達する場面は確かめていない。v2_repeat の 4 つの対戦の use_power の行は、どれもガードが働かない `may_stop_later` だった。
- GUI の追従、UP-5t の D（静的な監査だけ）、トレーナーの候補への拡張は、別の作業として残している。
