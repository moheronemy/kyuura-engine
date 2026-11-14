# v0.181: 回答の指定でおもてにした［KEEP］とエネルギー・リムーブ（E12 の修正）

2026-11-14。版 0.181.0。調査は [E12 の調査](verification-ai-e12-energy-removal-keep-investigation.md)。

## 1. 基点とコミット

- 基点は `claude/e12-energy-removal-keep-investigation`（`8b41238`）。作業ブランチは `claude/e12-keep-energy-removal-fix`。
- コミットは 3 つ。
  - 実装とテスト: `c537f08`
  - 版 0.181.0: `a2b29e9`（配布の確かめの固定コミット）
  - 文書: このコミット
- 停止中の P3s の作業は変えていない。
  - ブランチ `claude/lost-target-p3s-judge-rule8`（`1eed4d1`）と、その未追跡のテスト（SHA-256 `79d45767…`）。
  - 関連の確かめには、証跡の写しを使った。

## 2. 裁定との対応

**KP1**: `UNRESOLVED_KEEP_PROTECTED_TARGET`（[v0.101](counter-keep-energy-protection-v0.101.md) 4.3・8 章）。

- 中身は、［KEEP］で効果がなくなるカード・ポケモンを、トレーナーの「はがしてすてる」対象に選べるかという問い。
- 記録で決まらない研究上の未解決で、kyuura の UQ-TARGET-WITHOUT-EFFECT と同じ形。
- 扱いは「選べるが、選ぶと `UnsupportedError` で止める」（決定の `unresolved_choices`）。
  - 超エネルギーリムーブでは、段階 2 のポケモンごとに止める（`unresolved_detail`）。

**今回の場面**: うらのカードは特殊能力を持たないので、決定を出す時点では［KEEP］を数えない。

- 答えで指定しておもてにした本当のカードが［KEEP］を持つたねなら、そこで初めてトラッシュの効果がなくなる。
- これは「効果がなくなる対象を選んだ」ことで、KP1 と同じ問い。既存の裁定・未対応の記録と矛盾しない。
- そのため、KP1 と同じ通常の拒否にした。効果なしで受理する新しい裁定は入れていない。
- v0.101 の 4.1 節には「うらのカードにエネルギーカードをつけるとおもてにするので、つかない」とあるが、これは誤り。
  - 基本エネルギーは、つけたときの効果がないので、うらのままつく（[調査](verification-ai-e12-energy-removal-keep-investigation.md) 5 章）。
  - この前提のずれが、確かめが漏れた理由。

**しなかったこと**:

- `RuntimeError` を広く捕まえること。
- 置きかえの試しから［KEEP］のカードを除くこと。
- ほかの特殊能力・スタジアム・ワザへ広げること。

## 3. 修正（`effects.DiscardAttachedEnergyTrainer`）

新しい `_require_not_keep_voided` で、選んだ相手のポケモンについて既存の `energy_discard_void` を今の場で確かめる。当たれば `UnsupportedError(KEEP_TARGET_CODE, KEEP_TARGET_REASON)` にする。この文は決定の時点の KP1 と同じで、本当のカードを書かない。

| 段階 | 処理 | v0.181 |
| --- | --- | --- |
| 1（超エネルギーリムーブの自分のエネルギー） | 自分の効果なので［KEEP］は当たらない | 変えない |
| 2（超エネルギーリムーブの相手のポケモン） | `_designate_answer` がうらをおもてにしたあと、段階 3 の決定を出す | 決定を出す前に確かめる |
| 3（相手のエネルギーをトラッシュ） | エネルギー・リムーブは `_designate_answer` がついているうらをおもてにしたあと、トラッシュする | トラッシュの前に確かめる |

- 処理の順は変えていない。
  - 指定でたねでないカードがトラッシュされる場合（LOST_TARGET。`can_lose=False`）は、指定の時点で今までどおり止まる。
  - 選べないものの拒否と、FC1 の確かめも今までどおり先に来る。
- 段階 3 の確かめは、超エネルギーリムーブでは守りの役（段階 2 で止まるので、入口からは来ない）。
- 状態は `_apply_once` の複製の上で変わるので、拒否しても呼び出し元は変わらない。

## 4. 秘密によらない結果（E12 の期待値の変更）

**エネルギー・リムーブ**: 相手のうらについたエネルギーを選んだときの結果。

- 本当のカードがたね・たねでない・［KEEP］を持つたねのどれでも、同じ `UnsupportedError`（`UNRESOLVED_KEEP_PROTECTED_TARGET`）。理由の文も同じ。
- 置きかえの確かめ（`_identity_independent`）は、v0.180 と同じ順で試す。
  - たねの代表は［KEEP］のたねより前はすべて受理し、［KEEP］のたねで KP1 になる。それが最初の拒否になる。

**超エネルギーリムーブ**:

- 段階 2 で相手のうら（エネルギー 2 枚）を選ぶと、同じく KP1。
- エネルギー 2 枚のポケモンが相手のうらだけなら、使う時点の答えの続きの確かめ（v0.49 の `_trainer_dead_end`）で、どの本当のカードでも FC1（`UNRESOLVED_STATED_CARDS_SHORT`）。
  - 最初に見つかる止め方が、エネルギーの足りないバトル場だから。
  - v0.180 は、どちらの場面でも内部の例外だった。

**E12 の期待値**:

- [P3 の設計](verification-ai-lost-target-p3-decision-design.md) 6.2 の E12 は、どの本当のカードでも `UNSUPPORTED_SECRET_PLAN_LOST_TARGET` を期待していた。
- 修正後は、どの本当のカードでも `UNRESOLVED_KEEP_PROTECTED_TARGET` になる。本当のカードによらない（同じコード・同じ文）という性質は保たれる。
- コードが変わった理由は、置きかえの試しの順で［KEEP］のたね（481 回目）が `_NONBASIC`（548 回目）より先に拒否するため。
- 停止中のテストの E12 は、この期待値で直す必要がある（P3s の実装を再開するときに扱う。9 章）。

## 5. テスト

**新しいテスト** `tests/test_keep_designated_energy_removal_v0_181.py`（9 件）。

- エネルギー・リムーブ
  - うらの 3 通り（たね・たねでない・［KEEP］）が同じ KP1。
  - ［KEEP］のうらは、試しのない本物の処理でも KP1 になり、拒否のあとに別のエネルギーで受理する。
  - おもての［KEEP］（決定の時点の KP1）と［KEEP］のないおもて（受理）。
  - おもての［KEEP］と別のうらのエネルギー（使う時点の FD1）。
- 超エネルギーリムーブ
  - 段階 2 のうらの 3 通り（KP1）。
  - うらだけが対象の場合（使う時点の FC1）。
  - 段階 2・3 の通常のトラッシュと、おもての［KEEP］の段階 2。
- LOST_TARGET の対照: 本人のうらでディフェンダー（LOST_TARGET）と、入れ替え（対象を失ったら終える）。
- 拒否するたびに、状態・乱数・ログ・決定・相手と観戦者の観測とログ・`IDENTITY_CONSULTED`・`IDENTITY_ORACLE` が変わらないことと、理由の文に本当のカードがないことを確かめる。
- `ClientHub` の双子
  - 本人と観戦者の観測が同じことを確かめてから、候補・inputs・check・submit・更新を比べた。
  - check は valid、submit は `rejected`（`failed`・`INTERNAL_ERROR` ではない）。
  - 拒否で本人・相手・観戦者への更新はない。同じ決定に別の答えを出せば受理する。

**修正の前後**: 同じテストを修正の前のソース（`8b41238`）で実行し、修正の対象の 5 件が失敗することを確かめた（内部の `RuntimeError` 10 か所ほか）。対照の 4 件は前でも成功した。

**関連**（1 モジュールずつ別プロセスで実行。17 モジュールはすべて成功）:

- KEEP、マチスの秘策（v0.67・v0.68・v0.117）、P1 のエンジンの根拠、トレーナー（v0.55・v0.82・v0.4e・trainers）
- 候補と決定（u7_5c・decision_audit）、client_api（cn1 をふくむ）、from_state、錯乱ジム
- P1 の judge、実装の識別の設計
- 補足: v0.55 は、この端末の既定の文字コード（cp932）でデータの JSON を読むテストが 2 件エラーになった。UTF-8 モードでもう一度実行して成功した（修正とは関係しない）。

**指紋と版**: 検証用 AI の行動・契約の指紋（`test_verification_ai_v2_repeat`）は固定値のまま通った。版のテスト（preset_decks・distribution）も通った。

**P3s**: 停止中の E7〜E12 の証跡の写しをこの版で実行した。E7〜E11 は成功。E12 は、どの本当のカードでも同じ結果（KP1）で、期待した LOST_TARGET とコードだけが違って失敗（4 章）。

## 6. 版・識別・basis

| 項目 | 0.180.0（`8b41238`） | 0.181.0（`a2b29e9`） |
| --- | --- | --- |
| パッケージ版 | 0.180.0 | 0.181.0 |
| behavior_digest | `08038e06…` | `5e0cb4ac…` |
| instrumentation_digest | `d3436748…` | 同じ |
| 検証用 AI の `TOOL_VERSION`・道具の識別・判定の規則・形式 | 9・`383e30c4…`・7・6 | 同じ（judge・runner・batch・方策は変えていない） |
| P1 の basis（5 ファイル） | `a871823d…` | `d1729754…`（`effects.py` が変わった） |
| P3 の設計の 7 ファイル | — | `effects.py` だけが変わった（ほかの 6 ファイルの blob は同じ） |

- **P1 の basis の意味**: 規則 7 は、記録の basis と今の basis が一致したときだけ P1 を known_stop にする。
  - 0.180.0 までの記録（s1・r1 など）を 0.181.0 の道具で読むと basis が一致しない。P1 の行は undetermined のまま（判定を緩めない）。
  - 旧記録に新しい basis は使わない。旧計画の移行・再開・識別の書き換えはしていない。
  - 0.180.0 の記録・スナップショットは 0.181.0 では再実行・復元できない（既存の設計）。

## 7. 配布

- 配布ファイルは 62 で、0.180.0（`27ba35d`）と同じ一覧。`pyproject.toml` の差は版の 1 行だけ。
- `a2b29e9` の展開から wheel を作った（`kyuura_engine-0.181.0-py3-none-any.whl`、sha256 `d6d4b823…`）。`scripts/check_distribution.py --wheel` は problems 0。
- リポジトリの外の新しい venv に、`git+https://github.com/moheronemy/kyuura-engine.git@a2b29e9…` から通常の pip install をした。
  - 依存は追加されていない。
  - site-packages から読み込み、direct_url の commit は `a2b29e9`（vcs。editable でない）。
  - 版と実装の識別はソースと一致した。
- この版で作ったスナップショット 5 つ（うらの 3 通りと、おもての 2 つの対照）を導入先で復元し、`ClientHub` の結果がテストと同じことを確かめた。
  - うらの 3 通りは同じ応答（submit `rejected`・KP1、更新なし、別の答えで受理）。
  - おもての［KEEP］は check で `CANDIDATE_NOT_EXECUTABLE`。［KEEP］のないおもては受理。
  - 旧版のスナップショットは使っていない。

## 8. GUI・検証用 AI への追従

**GUI**:

- 相手のうらについたエネルギーをエネルギー・リムーブで選ぶと、submit が `rejected`（KP1）になりうる。check は valid のまま。
- 候補・check の成功は受理の保証ではない（既存の契約、`may_stop_later`）。拒否の表示を確かめる。GUI は今回確かめていない。

**検証用 AI**:

- 行動・契約の指紋は変わらない。この場面の submit は、`failed`（内部の例外）から通常の `rejected` になる。
- 判定は既存の規則で読む。KP1 の根拠登録はない（`undetermined`）。

## 9. P3s の実装を再開するときの注意

- **基点**: 0.181.0 のエンジン（このブランチ）から始めるか、`1eed4d1`（0.180.0）のままにするかを決める。
  - P3 用 basis（7 ファイル）の値は、エンジンの版で変わる（`effects.py`）。
  - 保存済みの r1 の P3 の行は 0.180.0 の記録。0.181.0 の basis とは一致しない。
- **E12 の期待値**: 0.181.0 では `UNRESOLVED_KEEP_PROTECTED_TARGET`（本当のカードによらない）。停止中のテストの期待値は直す必要がある。
  - E12 は P3o の性質の記録で、P3s の条件 D1〜D12 には影響しない。
- judge の規則 8 と P3s の根拠登録は、まだしていない。

## 10. 未確認

- new_game からの到達（構築盤面とスナップショットだけ）。
- ほかの特殊能力・スタジアム・ワザで、指定でおもてにした［KEEP］がトラッシュの効果をなくす場面（調査の 10 章のまま）。
- GUI。
- 全体テスト。
- 保存済みのバッチへの当て直し。

## 11. 証跡

- 非公開: `kyuura-engine-verification-vai/verifier/runs/e12-keep-energy-removal-fix/`
  - 事前計画、裁定との対応、修正の前後の実行、双子の比べ、テストの出力・JUnit、識別、配布、コマンドの記録。
- 公開: `public/runs/e12-keep-energy-removal-fix/summary.json`（件数と分類だけ）。
